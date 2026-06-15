# Capítulo 11: Segurança de APIs (REST, GraphQL, gRPC)

> **Livro 6: Desenvolvimento Seguro na Web**
> **Projeto: DevSecurity**

---

## Sumário

1. Objetivos de Aprendizado
2. Fundamentos de Segurança de APIs
3. OWASP API Security Top 10 2023
4. Segurança em APIs GraphQL
5. Segurança em APIs gRPC
6. Versionamento e Descontinuação de APIs
7. Padrões de API Gateway
8. OAuth 2.0 para APIs
9. Rate Limiting Distribuído
10. Validação de Input com OpenAPI
11. Error Handling Seguro
12. Monitoramento e Detecção de Anomalias
13. APIs Seguras Completas (Express.js, Flask, Go)
14. Exercícios
15. Referências

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Compreender** os fundamentos de segurança de APIs, incluindo autenticação, autorização e rate limiting, identificando como cada camada contribui para a segurança geral do sistema.

2. **Aplicar** o OWASP API Security Top 10 2023 para avaliar e mitigar vulnerabilidades específicas de APIs REST, incluindo Broken Object Level Authorization (BOLA), Broken Authentication, e Security Misconfiguration.

3. **Implementar** controles de segurança específicos para GraphQL, incluindo proteção contra query depth attacks, complexity analysis, introspection abuse, e batching attacks.

4. **Configurar** segurança em APIs gRPC, incluindo TLS/mTLS, interceptors de autenticação, e proteção via metadata.

5. **Projetar** padrões de API gateway que implementem autenticação centralizada, rate limiting distribuído, e monitoramento de anomalias.

6. **Implementar** OAuth 2.0 para APIs, incluindo Bearer tokens, API keys, e fluxos de autorização seguros.

7. **Desenvolver** estratégias de rate limiting usando token bucket, sliding window, e implementações distribuídas.

8. **Validar** entrada de APIs usando schemas OpenAPI e implementar error handling que não vaze informações sensíveis.

9. **Monitorar** APIs para detecção de anomalias e implementar logging de segurança adequado.

10. **Construir** APIs seguras completas em Express.js, Flask e Go, aplicando todos os conceitos aprendidos.

---

## 2. Fundamentos de Segurança de APIs

### 2.1 O Modelo de Segurança em Camadas para APIs

A segurança de APIs modernas opera em múltiplas camadas interdependentes. Cada camada adiciona uma barreira de defesa, criando uma abordagem de defesa em profundidade que dificulta ataques mesmo quando uma camada individual é comprometida.

```
┌─────────────────────────────────────────────┐
│           Camada 7: Aplicação               │
│    (Validação de Input, Business Logic)     │
├─────────────────────────────────────────────┤
│           Camada 6: Autorização             │
│    (RBAC, ABAC, Object-Level Auth)         │
├─────────────────────────────────────────────┤
│           Camada 5: Autenticação            │
│    (OAuth 2.0, JWT, API Keys)              │
├─────────────────────────────────────────────┤
│           Camada 4: Rate Limiting           │
│    (Throttling, Quotas, Burst Protection)  │
├─────────────────────────────────────────────┤
│           Camada 3: Transporte              │
│    (TLS 1.3, mTLS, Certificate Pinning)   │
├─────────────────────────────────────────────┤
│           Camada 2: Rede                    │
│    (WAF, DDoS Protection, IP Filtering)    │
├─────────────────────────────────────────────┤
│           Camada 1: Infraestrutura          │
│    (Network Segmentation, Container Sec)   │
└─────────────────────────────────────────────┘
```

A maioria dos desenvolvedores foca apenas nas camadas 5 e 7, negligenciando o restante. Uma API pode ter autenticação perfeita mas ser vulnerável a ataques de negação de serviço se não implementar rate limiting adequado.

### 2.2 Autenticação: Quem é o Requisitante?

Autenticação em APIs responde à pergunta: "Quem está fazendo esta requisição?" Existem três mecanismos principais:

**Autenticação Baseada em Tokens (OAuth 2.0/JWT):**

```javascript
// Express.js middleware de autenticação JWT
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({
            error: 'Access token required',
            code: 'AUTH_TOKEN_MISSING'
        });
    }
    
    jwt.verify(token, process.env.JWT_SECRET, {
        algorithms: ['HS256', 'RS256'],
        issuer: 'https://api.example.com',
        audience: 'https://api.example.com'
    }, (err, decoded) => {
        if (err) {
            return res.status(403).json({
                error: 'Invalid or expired token',
                code: 'AUTH_TOKEN_INVALID'
            });
        }
        
        req.user = decoded;
        next();
    });
};
```

**Autenticação Baseada em Chaves (API Keys):**

```python
# Flask middleware de autenticação por API key
from functools import wraps
from flask import request, jsonify
import hashlib
import hmac

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'code': 'API_KEY_MISSING'
            }), 401
        
        # Verificar contra banco de dados usando comparação constante
        stored_hash = get_api_key_hash(api_key)
        if not stored_hash:
            return jsonify({
                'error': 'Invalid API key',
                'code': 'API_KEY_INVALID'
            }), 401
        
        # Rate limiting por API key
        rate_limit_key = f"api_key:{stored_hash}"
        if is_rate_limited(rate_limit_key):
            return jsonify({
                'error': 'Rate limit exceeded',
                'code': 'RATE_LIMIT_EXCEEDED'
            }), 429
        
        request.api_key_id = stored_hash
        return f(*args, **kwargs)
    
    return decorated
```

**Autenticação Mútua (mTLS):**

```go
// Go middleware de mTLS
package middleware

import (
    "crypto/tls"
    "crypto/x509"
    "net/http"
    "os"
)

func RequireMTLS(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.TLS == nil || len(r.TLS.PeerCertificates) == 0 {
            http.Error(w, "Client certificate required", http.StatusUnauthorized)
            return
        }
        
        // Verificar se o certificado foi assinado pela CA autorizada
        caCert, err := os.ReadFile("ca.crt")
        if err != nil {
            http.Error(w, "Internal server error", http.StatusInternalServerError)
            return
        }
        
        caCertPool := x509.NewCertPool()
        caCertPool.AppendCertsFromPEM(caCert)
        
        _, err = r.TLS.PeerCertificates[0].Verify(x509.VerifyOptions{
            Roots: caCertPool,
        })
        
        if err != nil {
            http.Error(w, "Invalid client certificate", http.StatusUnauthorized)
            return
        }
        
        // Extrair identidade do certificado
        r.Header.Set("X-Client-CN", r.TLS.PeerCertificates[0].Subject.CommonName)
        next.ServeHTTP(w, r)
    })
}
```

### 2.3 Autorização: O que o Requisitante pode fazer?

Autenticação identifica o usuário; autorização determina o que ele pode acessar. Em APIs, a autorização opera em dois níveis:

**Autorização Baseada em Papéis (RBAC):**

```javascript
// Sistema RBAC para APIs
const checkPermission = (requiredRole) => {
    return (req, res, next) => {
        const userRole = req.user.role;
        const userPermissions = roleHierarchy[userRole];
        
        if (!userPermissions || !userPermissions.includes(requiredRole)) {
            return res.status(403).json({
                error: 'Insufficient permissions',
                code: 'FORBIDDEN',
                required: requiredRole,
                current: userRole
            });
        }
        
        next();
    };
};

// Hierarquia de papéis
const roleHierarchy = {
    'admin': ['read', 'write', 'delete', 'manage_users', 'manage_api_keys'],
    'editor': ['read', 'write'],
    'viewer': ['read'],
    'api_consumer': ['read', 'write_own']
};

// Uso nas rotas
app.get('/api/users', authenticateToken, checkPermission('read'), listUsers);
app.delete('/api/users/:id', authenticateToken, checkPermission('delete'), deleteUser);
```

**Autorização Baseada em Atributos (ABAC):**

```python
# Sistema ABAC para APIs
from dataclasses import dataclass
from typing import List, Callable
from enum import Enum

class Action(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE = "manage"

@dataclass
class Resource:
    type: str
    owner_id: str
    classification: str
    department: str

@dataclass
class Subject:
    user_id: str
    roles: List[str]
    department: str
    clearance_level: int

class ABACPolicyEngine:
    def __init__(self):
        self.policies: List[Callable] = []
    
    def add_policy(self, policy: Callable):
        self.policies.append(policy)
    
    def evaluate(self, subject: Subject, resource: Resource, action: Action) -> bool:
        for policy in self.policies:
            if not policy(subject, resource, action):
                return False
        return True

# Definir políticas
def owner_policy(subject: Subject, resource: Resource, action: Action) -> bool:
    """Usuários podem acessar seus próprios recursos"""
    if subject.user_id == resource.owner_id:
        return True
    return False

def department_policy(subject: Subject, resource: Resource, action: Action) -> bool:
    """Usuários podem acessar recursos do mesmo departamento"""
    return subject.department == resource.department

def classification_policy(subject: Subject, resource: Resource, action: Action) -> bool:
    """Usuários só podem acessar recursos com classificação igual ou inferior"""
    classification_hierarchy = {'public': 0, 'internal': 1, 'confidential': 2, 'secret': 3}
    return classification_hierarchy[resource.classification] <= subject.clearance_level

# Uso
engine = ABACPolicyEngine()
engine.add_policy(owner_policy)
engine.add_policy(department_policy)
engine.add_policy(classification_policy)

subject = Subject(user_id="u123", roles=["analyst"], department="engineering", clearance_level=2)
resource = Resource(type="document", owner_id="u123", classification="confidential", department="engineering")

allowed = engine.evaluate(subject, resource, Action.READ)  # True
```

### 2.4 Rate Limiting: Proteção contra Abuso

Rate limiting previne abuso de APIs, protege contra ataques de força bruta, e garante disponibilidade para todos os usuários.

**Implementação Básica com Token Bucket:**

```javascript
// Token Bucket Rate Limiter
class TokenBucket {
    constructor(capacity, refillRate, refillInterval) {
        this.capacity = capacity;
        this.tokens = capacity;
        this.refillRate = refillRate;
        this.refillInterval = refillInterval;
        this.lastRefill = Date.now();
    }
    
    refill() {
        const now = Date.now();
        const timePassed = now - this.lastRefill;
        const tokensToAdd = Math.floor(timePassed / this.refillInterval) * this.refillRate;
        
        if (tokensToAdd > 0) {
            this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
            this.lastRefill = now;
        }
    }
    
    consume(tokens = 1) {
        this.refill();
        
        if (this.tokens >= tokens) {
            this.tokens -= tokens;
            return true;
        }
        
        return false;
    }
}

// Middleware de rate limiting
const rateLimitMiddleware = (req, res, next) => {
    const clientId = req.ip || req.headers['x-forwarded-for'];
    
    if (!rateLimitStore[clientId]) {
        rateLimitStore[clientId] = new TokenBucket(100, 10, 1000); // 100 tokens, 10/s refill
    }
    
    const bucket = rateLimitStore[clientId];
    
    if (!bucket.consume()) {
        return res.status(429).json({
            error: 'Rate limit exceeded',
            code: 'RATE_LIMIT_EXCEEDED',
            retryAfter: Math.ceil((bucket.refillInterval * (1 - bucket.tokens / bucket.refillRate)) / 1000)
        });
    }
    
    // Adicionar headers de rate limiting
    res.set({
        'X-RateLimit-Limit': bucket.capacity,
        'X-RateLimit-Remaining': bucket.tokens,
        'X-RateLimit-Reset': Math.ceil((bucket.lastRefill + bucket.refillInterval) / 1000)
    });
    
    next();
};
```

**Sliding Window Log:**

```python
# Sliding Window Rate Limiter com Redis
import redis
import time
from functools import wraps
from flask import request, jsonify

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def sliding_window_rate_limit(max_requests, window_seconds):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = f"rate_limit:{request.remote_addr}:{f.__name__}"
            now = time.time()
            window_start = now - window_seconds
            
            # Remover entradas antigas
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # Contar requisições na janela atual
            current_requests = redis_client.zcard(key)
            
            if current_requests >= max_requests:
                # Calcular tempo para próxima janela
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = oldest[0][1] + window_seconds - now
                else:
                    retry_after = window_seconds
                
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'retryAfter': max(0, int(retry_after))
                }), 429
            
            # Adicionar requisição atual
            redis_client.zadd(key, {f"{now}": now})
            redis_client.expire(key, window_seconds)
            
            # Headers de informação
            remaining = max_requests - current_requests - 1
            reset_time = int(now + window_seconds)
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator
```

---

## 3. OWASP API Security Top 10 2023

### 3.1 Visão Geral

O OWASP API Security Top 10 2023 lista as dez vulnerabilidades mais críticas em APIs. Diferente do OWASP Web Application Top 10, este foca especificamente em APIs, que apresentam superfícies de ataque únicas.

| Posição | Vulnerabilidade | Descrição |
|---------|----------------|-----------|
| API1 | Broken Object Level Authorization | Acesso não autorizado a objetos |
| API2 | Broken Authentication | Autenticação inadequada |
| API3 | Broken Object Property Level Authorization | Exposição de propriedades sensíveis |
| API4 | Unrestricted Resource Consumption | Consumo ilimitado de recursos |
| API5 | Broken Function Level Authorization | Acesso a funções não autorizadas |
| API6 | Unrestricted Access to Sensitive Business Flows | Acesso irrestrito a fluxos sensíveis |
| API7 | Server Side Request Forgery (SSRF) | Falsificação de requisições do lado do servidor |
| API8 | Security Misconfiguration | Configuração de segurança inadequada |
| API9 | Improper Inventory Management | Gestão inadequada de inventário |
| API10 | Unsafe Consumption of APIs | Consumo inseguro de APIs |

### 3.2 API1: Broken Object Level Authorization (BOLA)

BOLA é a vulnerabilidade mais comum em APIs, responsável por 40% dos incidentes de segurança em APIs. Ocorre quando um usuário pode acessar objetos que não deveria ter acesso, modificando IDs ou parâmetros na requisição.

**Exemplo de Vulnerabilidade:**

```javascript
// VULNERAVEL: Não verifica se o usuário owns o objeto
app.get('/api/invoices/:id', authenticateToken, async (req, res) => {
    const invoice = await Invoice.findById(req.params.id);
    
    if (!invoice) {
        return res.status(404).json({ error: 'Invoice not found' });
    }
    
    // PROBLEMA: Qualquer usuário autenticado pode acessar qualquer invoice
    res.json(invoice);
});

// ATAQUE: Usuário muda o ID na URL
// GET /api/invoices/123 -> GET /api/invoices/124 (invoice de outro usuario)
```

**Correção:**

```javascript
// SEGURO: Verifica ownership do objeto
app.get('/api/invoices/:id', authenticateToken, async (req, res) => {
    const invoice = await Invoice.findById(req.params.id);
    
    if (!invoice) {
        return res.status(404).json({ error: 'Invoice not found' });
    }
    
    // VERIFICACAO CRITICA: O usuario owns esta invoice?
    if (invoice.userId !== req.user.id && req.user.role !== 'admin') {
        return res.status(403).json({ 
            error: 'Access denied',
            code: 'FORBIDDEN'
        });
    }
    
    res.json(invoice);
});

// Abstracao reutilizavel para evitar repeticao
const authorizeOwnership = (model, ownerField = 'userId') => {
    return async (req, res, next) => {
        const resource = await model.findById(req.params.id);
        
        if (!resource) {
            return res.status(404).json({ error: 'Resource not found' });
        }
        
        if (resource[ownerField] !== req.user.id && req.user.role !== 'admin') {
            return res.status(403).json({ error: 'Access denied' });
        }
        
        req.resource = resource;
        next();
    };
};

// Uso
app.get('/api/invoices/:id', 
    authenticateToken, 
    authorizeOwnership(Invoice), 
    (req, res) => res.json(req.resource)
);
```

**Padrao de Prevencao com Repository Pattern:**

```python
# Padrao seguro com Repository Pattern
from typing import Optional, List
from sqlalchemy.orm import Session

class SecureInvoiceRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, invoice_id: int, user_id: int) -> Optional[Invoice]:
        """Busca invoice garantindo que o usuario e owner"""
        return self.db.query(Invoice).filter(
            Invoice.id == invoice_id,
            Invoice.user_id == user_id  # FILTRO DE SEGURANCA
        ).first()
    
    def list_for_user(self, user_id: int, page: int = 1, per_page: int = 20) -> List[Invoice]:
        """Lista invoices do usuario com paginacao"""
        return self.db.query(Invoice).filter(
            Invoice.user_id == user_id
        ).offset((page - 1) * per_page).limit(per_page).all()
    
    def update(self, invoice_id: int, user_id: int, data: dict) -> Optional[Invoice]:
        """Atualiza invoice com verificacao de ownership"""
        invoice = self.get_by_id(invoice_id, user_id)
        if not invoice:
            return None
        
        for key, value in data.items():
            setattr(invoice, key, value)
        
        self.db.commit()
        return invoice

# Uso no endpoint
@app.get('/api/invoices/<int:invoice_id>')
@require_auth
def get_invoice(invoice_id: int):
    repo = SecureInvoiceRepository(db)
    invoice = repo.get_by_id(invoice_id, g.user.id)
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    return jsonify(invoice.to_dict())
```

### 3.3 API2: Broken Authentication

Broken Authentication inclui falhas como tokens previsiveis, credenciais fracas, ou mecanismos de recuperacao de senha inseguros.

**Exemplo de Vulnerabilidade:**

```javascript
// VULNERAVEL: Token JWT com algoritmo fraco e sem expiracao
const generateToken = (user) => {
    return jwt.sign(
        { userId: user.id, role: user.role },
        'secret123',  // CHAVE FRACA
        { algorithm: 'HS256' }  // Sem expiracao!
    );
};

// VULNERAVEL: Reset de senha com token previsivel
const resetPassword = async (email) => {
    const user = await User.findOne({ email });
    if (!user) return;
    
    // Token previsivel baseado em timestamp
    const token = Date.now().toString(36) + Math.random().toString(36);
    
    await sendResetEmail(user.email, token);
};
```

**Correção:**

```javascript
// SEGURO: Token JWT robusto
const generateToken = (user) => {
    const privateKey = fs.readFileSync('private-key.pem');
    
    return jwt.sign(
        { 
            sub: user.id,
            iss: 'https://api.example.com',
            aud: 'https://api.example.com',
            scope: user.scopes.join(' '),
            jti: crypto.randomUUID()  // ID unico do token
        },
        privateKey,
        { 
            algorithm: 'RS256',
            expiresIn: '15m'  // Curta duracao
        }
    );
};

// SEGURO: Reset de senha com token criptografico
const resetPassword = async (email) => {
    const user = await User.findOne({ email });
    if (!user) return;  // Nao revelar se email existe
    
    // Token aleatorio de 32 bytes
    const resetToken = crypto.randomBytes(32).toString('hex');
    const resetTokenHash = crypto.createHash('sha256').update(resetToken).digest('hex');
    
    // Armazenar hash, nao o token
    await PasswordReset.create({
        userId: user.id,
        tokenHash: resetTokenHash,
        expiresAt: new Date(Date.now() + 60 * 60 * 1000)  // 1 hora
    });
    
    // Enviar token original (nao hash) por email
    await sendResetEmail(user.email, resetToken);
};
```

### 3.4 API3: Broken Object Property Level Authorization

Esta vulnerabilidade ocorre quando uma API permite que o cliente defina quais propriedades de um objeto podem ser lidas ou escritas, expondo dados sensiveis.

**Exemplo de Vulnerabilidade:**

```javascript
// VULNERAVEL: Mass Assignment - aceita qualquer campo
app.put('/api/users/:id', authenticateToken, async (req, res) => {
    const user = await User.findByIdAndUpdate(
        req.params.id,
        req.body,  // ACEITA QUALQUER CAMPO!
        { new: true }
    );
    
    res.json(user);
});

// ATAQUE: Usuario envia campos extras
// PUT /api/users/123
// Body: { "name": "Joao", "role": "admin", "salary": 100000 }
```

**Correcao:**

```javascript
// SEGURO: Whitelist de campos permitidos
const allowedUpdateFields = ['name', 'email', 'phone', 'address'];
const adminUpdateFields = [...allowedUpdateFields, 'role', 'department'];

app.put('/api/users/:id', authenticateToken, async (req, res) => {
    const allowedFields = req.user.role === 'admin' ? adminUpdateFields : allowedUpdateFields;
    
    // Filtrar apenas campos permitidos
    const filteredData = {};
    for (const field of allowedFields) {
        if (req.body[field] !== undefined) {
            filteredData[field] = req.body[field];
        }
    }
    
    const user = await User.findByIdAndUpdate(
        req.params.id,
        filteredData,
        { new: true, runValidators: true }
    );
    
    res.json(user);
});

// Middleware reutilizavel para sanitizacao
const sanitizeInput = (allowedFields) => {
    return (req, res, next) => {
        const sanitized = {};
        for (const field of allowedFields) {
            if (req.body[field] !== undefined) {
                sanitized[field] = req.body[field];
            }
        }
        req.body = sanitized;
        next();
    };
};
```

### 3.5 API4: Unrestricted Resource Consumption

APIs sem rate limiting ou validacao de tamanho permitem que atacantes consumam recursos excessivos, causando negacao de servico.

**Exemplo de Vulnerabilidade:**

```python
# VULNERAVEL: Sem limite de paginacao ou tamanho
@app.route('/api/products', methods=['GET'])
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)  # SEM LIMITE!
    
    products = Product.query.paginate(page=page, per_page=per_page)
    
    return jsonify([p.to_dict() for p in products.items])

# ATAQUE: Requisicao massiva
# GET /api/products?page=1&per_page=1000000
```

**Correcao:**

```python
# SEGURO: Limites estritos
@app.route('/api/products', methods=['GET'])
@require_auth
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # VALIDACOES
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:  # LIMITE RIGIDO
        per_page = 20
    
    products = Product.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'data': [p.to_dict() for p in products.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': products.total,
            'pages': products.pages
        }
    })
```

### 3.6 API5: Broken Function Level Authorization

Esta vulnerabilidade permite que usuarios acessem funcoes administrativas ou funcionalidades que nao deveriam ter acesso.

**Exemplo de Vulnerabilidade:**

```javascript
// VULNERAVEL: Rota admin sem verificacao de papel
app.delete('/api/users/:id', async (req, res) => {
    // Qualquer pessoa pode deletar usuarios!
    await User.findByIdAndDelete(req.params.id);
    res.json({ success: true });
});
```

**Correcao:**

```javascript
// SEGURO: Middleware de verificacao de papel
const requireRole = (...roles) => {
    return (req, res, next) => {
        if (!req.user || !roles.includes(req.user.role)) {
            return res.status(403).json({
                error: 'Insufficient permissions',
                code: 'FORBIDDEN'
            });
        }
        next();
    };
};

// Uso
app.delete('/api/users/:id', 
    authenticateToken, 
    requireRole('admin'), 
    async (req, res) => {
        await User.findByIdAndDelete(req.params.id);
        res.json({ success: true });
    }
);

// Padrao mais granular com permissoes
const requirePermission = (permission) => {
    return (req, res, next) => {
        const userPermissions = req.user.permissions || [];
        
        if (!userPermissions.includes(permission)) {
            return res.status(403).json({
                error: 'Permission denied',
                code: 'FORBIDDEN',
                required: permission
            });
        }
        
        next();
    };
};
```

### 3.7 API6: Unrestricted Access to Sensitive Business Flows

Esta vulnerabilidade permite que atacantes automatizem fluxos de negocio sensiveis, como compras, transferencias ou reservas.

**Exemplo de Vulnerabilidade:**

```javascript
// VULNERAVEL: Fluxo de compra sem protecao contra automacao
app.post('/api/orders', authenticateToken, async (req, res) => {
    const { productId, quantity, paymentMethod } = req.body;
    
    // Sem verificacao de comportamento suspeito
    const order = await createOrder({
        userId: req.user.id,
        productId,
        quantity,
        paymentMethod
    });
    
    res.json(order);
});
```

**Correcao:**

```javascript
// SEGURO: Multiplas camadas de protecao
const purchaseProtection = async (req, res, next) => {
    const userId = req.user.id;
    const { productId, quantity } = req.body;
    
    // 1. Rate limiting especifico para compras
    const purchaseKey = `purchases:${userId}`;
    const recentPurchases = await redis.get(purchaseKey);
    
    if (recentPurchases && parseInt(recentPurchases) >= 5) {
        return res.status(429).json({
            error: 'Too many purchase attempts',
            code: 'PURCHASE_RATE_LIMIT'
        });
    }
    
    // 2. Verificar comportamento suspeito
    const userHistory = await OrderHistory.findByUser(userId);
    const isSuspicious = detectSuspiciousBehavior(userHistory, { productId, quantity });
    
    if (isSuspicious) {
        await logSecurityEvent('suspicious_purchase', { userId, productId, quantity });
        return res.status(403).json({
            error: 'Purchase blocked for verification',
            code: 'PURCHASE_BLOCKED'
        });
    }
    
    // 3. Verificar estoque antes de processar
    const product = await Product.findById(productId);
    if (!product || product.stock < quantity) {
        return res.status(400).json({
            error: 'Insufficient stock',
            code: 'INSUFFICIENT_STOCK'
        });
    }
    
    // Incrementar contador
    await redis.incr(purchaseKey);
    await redis.expire(purchaseKey, 3600);  // 1 hora
    
    next();
};
```

### 3.8 API7: Server Side Request Forgery (SSRF)

SSRF ocorre quando uma API faz requisicoes para recursos internos baseado em input do usuario.

**Exemplo de Vulnerabilidade:**

```python
# VULNERAVEL: Fetch de URL sem validacao
import requests

@app.route('/api/fetch-image', methods=['POST'])
@require_auth
def fetch_image():
    url = request.json.get('url')
    
    # PROBLEMA: Aceita qualquer URL
    response = requests.get(url)  # Pode acessar servicos internos!
    
    return response.content

# ATAQUE: Usuario envia
# { "url": "http://169.254.169.254/latest/meta-data/" }  # AWS metadata
# { "url": "http://localhost:6379/" }  # Redis interno
```

**Correcao:**

```python
# SEGURO: Validacao rigorosa de URLs
from urllib.parse import urlparse
import ipaddress
import socket

ALLOWED_HOSTS = ['images.example.com', 'cdn.example.com']
BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local
    ipaddress.ip_network('127.0.0.0/8'),    # Loopback
]

def is_safe_url(url: str) -> bool:
    """Valida se uma URL e segura para requisicao"""
    try:
        parsed = urlparse(url)
        
        # Apenas HTTPS
        if parsed.scheme not in ('https',):
            return False
        
        # Verificar host permitido
        if parsed.hostname not in ALLOWED_HOSTS:
            return False
        
        # Resolver hostname e verificar se nao e rede interna
        ip = socket.gethostbyname(parsed.hostname)
        ip_obj = ipaddress.ip_address(ip)
        
        for network in BLOCKED_NETWORKS:
            if ip_obj in network:
                return False
        
        return True
        
    except Exception:
        return False

@app.route('/api/fetch-image', methods=['POST'])
@require_auth
def fetch_image():
    url = request.json.get('url')
    
    if not is_safe_url(url):
        return jsonify({'error': 'URL not allowed'}), 400
    
    try:
        response = requests.get(url, timeout=5, allow_redirects=False)
        return response.content
    except requests.RequestException:
        return jsonify({'error': 'Failed to fetch image'}), 500
```

### 3.9 API8: Security Misconfiguration

Configuracoes de seguranca inadequadas sao uma das vulnerabilidades mais comuns, frequentemente causadas por configuracoes padrao ou hardcoding.

```javascript
// VULNERAVEL: Configuracoes inseguras
const config = {
    jwt: {
        secret: 'super-secret-key',  // Hardcoded
        expiresIn: '7d'  // Muito longo
    },
    cors: {
        origin: '*',  // Permite qualquer origem
        credentials: true
    },
    debug: true,  // Debug em producao
    errorHandler: (err, req, res) => {
        res.status(500).json({
            error: err.message,
            stack: err.stack  // Vazamento de stack trace
        });
    }
};
```

**Correcao:**

```javascript
// SEGURO: Configuracao adequada
const config = {
    jwt: {
        secret: process.env.JWT_SECRET,  // Variavel de ambiente
        expiresIn: '15m'  // Curta duracao
    },
    cors: {
        origin: process.env.ALLOWED_ORIGINS.split(','),
        credentials: true,
        methods: ['GET', 'POST', 'PUT', 'DELETE'],
        allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
        maxAge: 86400
    },
    debug: process.env.NODE_ENV === 'development',
    errorHandler: (err, req, res) => {
        // Log detalhado para monitoramento
        console.error('Error:', {
            message: err.message,
            stack: err.stack,
            requestId: req.id,
            userId: req.user?.id
        });
        
        // Resposta generica para o cliente
        res.status(500).json({
            error: 'Internal server error',
            code: 'INTERNAL_ERROR',
            requestId: req.id
        });
    }
};
```

### 3.10 API9: Improper Inventory Management

APIs antigas ou nao documentadas criam superficies de ataque invisiveis.

```yaml
# Documentacao OpenAPI adequada
openapi: 3.0.3
info:
  title: Secure API
  version: 2.0.0
  description: API segura com versionamento adequado

servers:
  - url: https://api.example.com/v2
    description: Production (current)
  - url: https://api.example.com/v1
    description: Legacy (deprecated, sunset: 2024-12-31)

paths:
  /users:
    get:
      summary: List users
      tags: [Users]
      deprecated: false
      security:
        - bearerAuth: []
      
  /legacy/users:
    get:
      summary: List users (legacy)
      tags: [Users]
      deprecated: true
      x-sunset: "2024-12-31"
      x-migration-guide: "/docs/migration/v1-to-v2"
      security:
        - bearerAuth: []
```

### 3.11 API10: Unsafe Consumption of APIs

APIs que consomem outras APIs sem validacao podem ser exploradas para ataques em cadeia.

```python
# VULNERAVEL: Consumo de API externa sem validacao
import requests

@app.route('/api/exchange-rate', methods=['GET'])
def get_exchange_rate():
    currency = request.args.get('currency', 'USD')
    
    # PROBLEMA: Nao valida resposta da API externa
    response = requests.get(f'https://external-api.com/rate/{currency}')
    data = response.json()
    
    return jsonify(data)

# ATAQUE: API externa comprometida retorna dados maliciosos
```

**Correcao:**

```python
# SEGURO: Consumo validado
import requests
from pydantic import BaseModel, validator
from typing import Optional

class ExchangeRateResponse(BaseModel):
    currency: str
    rate: float
    timestamp: int
    
    @validator('rate')
    def validate_rate(cls, v):
        if v <= 0 or v > 1000000:
            raise ValueError('Rate out of valid range')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        if len(v) != 3 or not v.isalpha():
            raise ValueError('Invalid currency code')
        return v.upper()

@app.route('/api/exchange-rate', methods=['GET'])
@require_auth
def get_exchange_rate():
    currency = request.args.get('currency', 'USD')
    
    try:
        response = requests.get(
            f'https://external-api.com/rate/{currency}',
            timeout=5,
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        
        # Validar contra schema esperado
        data = ExchangeRateResponse(**response.json())
        
        return jsonify(data.dict())
        
    except requests.RequestException as e:
        app.logger.error(f'External API error: {e}')
        return jsonify({'error': 'Service temporarily unavailable'}), 503
    except ValueError as e:
        app.logger.error(f'Invalid response from external API: {e}')
        return jsonify({'error': 'Invalid data from upstream'}), 502
```

---

## 4. Seguranca em APIs GraphQL

### 4.1 Visao Geral de Seguranca GraphQL

GraphQL apresenta desafios unicos de seguranca diferentes de REST. Uma unica query pode acessar multiplos recursos, criar loops infinitos, ou consumir recursos excessivos.

### 4.2 Query Depth Limiting

Atacantes podem criar queries com alta profundidade para sobrecarregar o servidor.

```javascript
// Vulnerabilidade: Query infinitamente profunda
// query {
//   users {
//     posts {
//       author {
//         posts {
//           author {
//             posts { ... }
//           }
//         }
//       }
//     }
//   }
// }

// Solucao: Limitar profundidade
const depthLimit = require('graphql-depth-limit');

const server = new ApolloServer({
    typeDefs,
    resolvers,
    validationRules: [depthLimit(7)]  // Maximo 7 niveis
});
```

**Implementacao Customizada:**

```javascript
// Depth limiting customizado com logging
const createDepthLimitRule = (maxDepth) => {
    return (context) => {
        const depths = [];
        
        return {
            Document(node) {
                const depth = calculateDepth(node);
                depths.push(depth);
                
                if (depth > maxDepth) {
                    throw new GraphQLError(
                        `Query depth ${depth} exceeds maximum ${maxDepth}`,
                        { extensions: { code: 'QUERY_TOO_DEEP', depth, maxDepth } }
                    );
                }
            },
            OperationDefinition: {
                leave(node) {
                    // Log para monitoramento
                    console.log('Query depth:', {
                        operation: node.operation,
                        name: node.name?.value,
                        depth: depths[depths.length - 1]
                    });
                }
            }
        };
    };
};

function calculateDepth(node) {
    if (!node.selectionSet) return 0;
    
    let maxChildDepth = 0;
    for (const selection of node.selectionSet.selections) {
        const childDepth = calculateDepth(selection);
        maxChildDepth = Math.max(maxChildDepth, childDepth);
    }
    
    return 1 + maxChildDepth;
}
```

### 4.3 Query Complexity Analysis

Alem da profundidade, e necessario analisar a complexidade computacional das queries.

```javascript
// Analise de complexidade
const { getComplexity, simpleEstimator, fieldExtensionsEstimator } = require('graphql-query-complexity');

const complexityRule = createComplexityRule({
    maximumComplexity: 1000,
    estimators: [
        fieldExtensionsEstimator(),
        simpleEstimator({ defaultComplexity: 1 })
    ],
    onComplete: (complexity) => {
        console.log('Query complexity:', complexity);
    },
    createError: (max, complexity) => {
        return new GraphQLError(
            `Query too complex: ${complexity}. Maximum allowed: ${max}`,
            { extensions: { code: 'QUERY_TOO_COMPLEX', complexity, max } }
        );
    }
});

// Definir complexidade nos resolvers
const resolvers = {
    User: {
        posts: {
            extensions: {
                complexity: ({ args, childComplexity }) => 
                    childComplexity * 10  // Cada post custa 10
            }
        },
        followers: {
            extensions: {
                complexity: ({ args, childComplexity }) => 
                    childComplexity * (args.first || 10)
            }
        }
    }
};
```

### 4.4 Introspection Control

Introspection permite que clientes descubram todo o schema da API, o que pode revelar informacoes sensiveis.

```javascript
// Desabilitar introspection em producao
const server = new ApolloServer({
    typeDefs,
    resolvers,
    introspection: process.env.NODE_ENV !== 'production',
    plugins: [
        // Plugin para rate limiting
        {
            requestDidStart() {
                const start = Date.now();
                return {
                    willSendResponse() {
                        const duration = Date.now() - start;
                        if (duration > 5000) {
                            console.warn('Slow query detected:', { duration });
                        }
                    }
                };
            }
        }
    ]
});
```

**Introspection Segura (quando necessaria):**

```javascript
// Introspection apenas para usuarios autenticados e autorizados
const introspectionPlugin = {
    requestDidStart(requestContext) {
        const { request, contextValue } = requestContext;
        
        // Verificar se e introspection
        const isIntrospection = request.query?.includes('__schema') || 
                                request.query?.includes('__type');
        
        if (isIntrospection) {
            // Verificar autorizacao
            if (!contextValue.user || contextValue.user.role !== 'admin') {
                throw new GraphQLError('Introspection not allowed', {
                    extensions: { code: 'INTROSPECTION_FORBIDDEN' }
                });
            }
            
            // Log para auditoria
            console.log('Introspection query', {
                userId: contextValue.user.id,
                timestamp: new Date().toISOString()
            });
        }
        
        return {};
    }
};
```

### 4.5 Batching Attacks

GraphQL permite enviar multiplas queries em uma unica requisicao, o que pode ser explorado para ataques de forca bruta ou DoS.

```javascript
// Ataque: Batching para forca bruta
// [
//   { "query": "mutation { login(username: \"admin\", password: \"pass1\") { token } }" },
//   { "query": "mutation { login(username: \"admin\", password: \"pass2\") { token } }" },
//   ... centenas de queries
// ]

// Solucao: Limitar batch size
const { ApolloServer } = require('@apollo/server');
const { expressMiddleware } = require('@apollo/server/express4');

const server = new ApolloServer({
    typeDefs,
    resolvers,
    plugins: [
        {
            requestDidStart() {
                return {
                    didResolveOperation(requestContext) {
                        const { request } = requestContext;
                        
                        // Verificar se e batch
                        if (Array.isArray(request.query)) {
                            if (request.query.length > 10) {
                                throw new GraphQLError('Batch size exceeded', {
                                    extensions: { 
                                        code: 'BATCH_TOO_LARGE',
                                        batchSize: request.query.length,
                                        maxBatchSize: 10
                                    }
                                });
                            }
                        }
                    }
                };
            }
        }
    ]
});
```

**Rate Limiting por Query Type:**

```javascript
// Rate limiting granular para GraphQL
const queryRateLimits = {
    'Query': 100,      // 100 queries por minuto
    'Mutation': 20,    // 20 mutations por minuto
    'Subscription': 10 // 10 subscriptions por minuto
};

const graphqlRateLimit = async (resolve, root, args, context, info) => {
    const operationType = info.parentType.name;
    const limit = queryRateLimits[operationType] || 50;
    
    const key = `graphql:${context.user?.id}:${operationType}`;
    const current = await redis.incr(key);
    
    if (current === 1) {
        await redis.expire(key, 60);
    }
    
    if (current > limit) {
        throw new GraphQLError('Rate limit exceeded', {
            extensions: {
                code: 'RATE_LIMITED',
                operationType,
                limit,
                current
            }
        });
    }
    
    return resolve(root, args, context, info);
};
```

### 4.6 Persisted Queries

Persisted queries melhoram seguranca ao limitar queries a um conjunto pre-definido.

```javascript
// Configurar persisted queries
const { InMemoryLRUCache } = require('@apollo/utils.keyvaluecache');

const server = new ApolloServer({
    typeDefs,
    resolvers,
    persistedQueries: {
        cache: new InMemoryLRUCache(),
        ttl: 900  // 15 minutos
    },
    // Rejeitar queries nao persistidas
    allowBatchedHttpRequests: false
});

// Client-side: Usar APQ (Automatic Persisted Queries)
// Em vez de enviar query completa, envia apenas hash
const client = new ApolloClient({
    link: createPersistedQueryLink(),
    cache: new InMemoryCache()
});
```

---

## 5. Seguranca em APIs gRPC

### 5.1 Visao Geral de Seguranca gRPC

gRPC usa HTTP/2 e Protocol Buffers, apresentando consideracoes de seguranca unicas. A comunicacao binaria oferece alguma protecao natural, mas requer configuracao adequada de TLS e autenticacao.

### 5.2 TLS e mTLS em gRPC

```go
// Configuracao TLS para servidor gRPC
package main

import (
    "crypto/tls"
    "crypto/x509"
    "log"
    "net"
    "os"
    
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials"
    "google.golang.org/grpc/health"
    healthpb "google.golang.org/grpc/health/grpc_health_v1"
)

func main() {
    // Carregar certificado do servidor
    cert, err := tls.LoadX509KeyPair("server.crt", "server.key")
    if err != nil {
        log.Fatalf("Failed to load certificate: %v", err)
    }
    
    // Configurar TLS
    tlsConfig := &tls.Config{
        Certificates: []tls.Certificate{cert},
        ClientAuth:   tls.RequireAndVerifyClientCert,
        MinVersion:   tls.VersionTLS13,
        CipherSuites: []uint16{
            tls.TLS_AES_256_GCM_SHA384,
            tls.TLS_CHACHA20_POLY1305_SHA256,
        },
    }
    
    // Carregar CA para verificar certificados de clientes
    caCert, err := os.ReadFile("ca.crt")
    if err != nil {
        log.Fatalf("Failed to read CA certificate: %v", err)
    }
    
    caCertPool := x509.NewCertPool()
    if !caCertPool.AppendCertsFromPEM(caCert) {
        log.Fatalf("Failed to parse CA certificate")
    }
    
    tlsConfig.ClientCAs = caCertPool
    
    // Criar credentials TLS
    creds := credentials.NewTLS(tlsConfig)
    
    // Criar servidor gRPC
    server := grpc.NewServer(
        grpc.Creds(creds),
        grpc.UnaryInterceptor(authInterceptor),
        grpc.StreamInterceptor(streamAuthInterceptor),
    )
    
    // Registrar servicos
    RegisterServiceServer(server, &serviceImpl{})
    
    // Health check
    healthpb.RegisterHealthServer(server, health.NewServer())
    
    // Iniciar listener
    lis, err := net.Listen("tcp", ":443")
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }
    
    log.Println("Server starting on :443")
    if err := server.Serve(lis); err != nil {
        log.Fatalf("Failed to serve: %v", err)
    }
}
```

### 5.3 Interceptors de Autenticacao

```go
// Interceptor de autenticacao para gRPC
package middleware

import (
    "context"
    "strings"
    
    "google.golang.org/grpc"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/metadata"
    "google.golang.org/grpc/status"
)

type contextKey string

const (
    UserIDKey    contextKey = "user_id"
    UserRolesKey contextKey = "user_roles"
)

func authInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    // Extrair metadata
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.Unauthenticated, "missing metadata")
    }
    
    // Verificar token de autorizacao
    authHeaders := md.Get("authorization")
    if len(authHeaders) == 0 {
        return nil, status.Error(codes.Unauthenticated, "missing authorization header")
    }
    
    token := strings.TrimPrefix(authHeaders[0], "Bearer ")
    
    // Validar token
    claims, err := validateToken(token)
    if err != nil {
        return nil, status.Error(codes.Unauthenticated, "invalid token")
    }
    
    // Adicionar informacoes do usuario ao contexto
    ctx = context.WithValue(ctx, UserIDKey, claims.UserID)
    ctx = context.WithValue(ctx, UserRolesKey, claims.Roles)
    
    return handler(ctx, req)
}

func streamAuthInterceptor(
    srv interface{},
    ss grpc.ServerStream,
    info *grpc.StreamServerInfo,
    handler grpc.StreamHandler,
) error {
    // Mesma logica para streams
    md, ok := metadata.FromIncomingContext(ss.Context())
    if !ok {
        return status.Error(codes.Unauthenticated, "missing metadata")
    }
    
    authHeaders := md.Get("authorization")
    if len(authHeaders) == 0 {
        return status.Error(codes.Unauthenticated, "missing authorization header")
    }
    
    token := strings.TrimPrefix(authHeaders[0], "Bearer ")
    claims, err := validateToken(token)
    if err != nil {
        return status.Error(codes.Unauthenticated, "invalid token")
    }
    
    ctx := context.WithValue(ss.Context(), UserIDKey, claims.UserID)
    ctx = context.WithValue(ctx, UserRolesKey, claims.Roles)
    
    wrappedStream := &wrappedServerStream{ss, ctx}
    return handler(srv, wrappedStream)
}

type wrappedServerStream struct {
    grpc.ServerStream
    ctx context.Context
}

func (w *wrappedServerStream) Context() context.Context {
    return w.ctx
}
```

### 5.4 Metadata e Validacao

```go
// Validacao de input usando interceptors
func validationInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    // Validacao usando protobuf validators
    if validator, ok := req.(interface{ Validate() error }); ok {
        if err := validator.Validate(); err != nil {
            return nil, status.Errorf(codes.InvalidArgument, "validation failed: %v", err)
        }
    }
    
    return handler(ctx, req)
}

// Rate limiting para gRPC
func rateLimitInterceptor(limiter *RateLimiter) grpc.UnaryServerInterceptor {
    return func(
        ctx context.Context,
        req interface{},
        info *grpc.UnaryServerInfo,
        handler grpc.UnaryHandler,
    ) (interface{}, error) {
        // Identificar cliente
        md, _ := metadata.FromIncomingContext(ctx)
        clientIP := extractClientIP(md)
        
        if !limiter.Allow(clientIP, info.FullMethod) {
            return nil, status.Error(codes.ResourceExhausted, "rate limit exceeded")
        }
        
        return handler(ctx, req)
    }
}

// Logging de auditoria
func auditInterceptor(logger *zap.Logger) grpc.UnaryServerInterceptor {
    return func(
        ctx context.Context,
        req interface{},
        info *grpc.UnaryServerInfo,
        handler grpc.UnaryHandler,
    ) (interface{}, error) {
        start := time.Now()
        
        resp, err := handler(ctx, req)
        
        duration := time.Since(start)
        
        // Log estruturado
        logger.Info("gRPC request",
            zap.String("method", info.FullMethod),
            zap.Duration("duration", duration),
            zap.Error(err),
            zap.String("user_id", extractUserID(ctx)),
        )
        
        return resp, err
    }
}
```

---

## 6. Versionamento e Descontinuacao de APIs

### 6.1 Estrategias de Versionamento

O versionamento adequado e crucial para seguranca, pois permite descontinuar versoes vulneraveis sem quebrar clientes existentes.

```yaml
# Estrategias de versionamento

# 1. URL Path Versioning (recomendado)
/api/v1/users
/api/v2/users

# 2. Header Versioning
Accept: application/vnd.api+json;version=2
X-API-Version: 2

# 3. Query Parameter Versioning
/api/users?version=2
```

**Implementacao com Versionamento por URL:**

```javascript
// Express.js com versionamento
const express = require('express');
const app = express();

// Versao 1 (legada)
const v1Router = express.Router();
v1Router.get('/users', listUsersV1);

// Versao 2 (atual)
const v2Router = express.Router();
v2Router.get('/users', listUsersV2);

// Registrar versoes
app.use('/api/v1', v1Router);
app.use('/api/v2', v2Router);

// Middleware de depreciacao para v1
app.use('/api/v1', (req, res, next) => {
    res.set({
        'Sunset': 'Sat, 01 Jan 2025 00:00:00 GMT',
        'Deprecation': 'true',
        'Link': '</api/v2/docs>; rel="successor-version"'
    });
    
    // Log para metricas de migracao
    console.log('Deprecated API v1 used', {
        path: req.path,
        userId: req.user?.id,
        timestamp: new Date().toISOString()
    });
    
    next();
});
```

### 6.2 Descontinuacao Segura

```python
# Sistema de descontinuacao para APIs
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from dataclasses import dataclass

class DeprecationStatus(Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    REMOVED = "removed"

@dataclass
class APIVersion:
    version: str
    status: DeprecationStatus
    created_at: datetime
    deprecated_at: Optional[datetime]
    sunset_at: Optional[datetime]
    removed_at: Optional[datetime]
    migration_guide_url: Optional[str]

class VersionManager:
    def __init__(self):
        self.versions = {}
    
    def deprecate_version(self, version: str, sunset_days: int = 180):
        """Inicia processo de descontinuacao"""
        if version not in self.versions:
            raise ValueError(f"Version {version} not found")
        
        self.versions[version].status = DeprecationStatus.DEPRECATED
        self.versions[version].deprecated_at = datetime.utcnow()
        self.versions[version].sunset_at = datetime.utcnow() + timedelta(days=sunset_days)
    
    def check_sunset(self, version: str) -> bool:
        """Verifica se versao atingiu sunset"""
        if version not in self.versions:
            return True
        
        ver = self.versions[version]
        if ver.status == DeprecationStatus.REMOVED:
            return True
        
        if ver.sunset_at and datetime.utcnow() > ver.sunset_at:
            ver.status = DeprecationStatus.SUNSET
            return True
        
        return False

# Middleware de versionamento
def version_middleware(version_manager: VersionManager):
    def middleware(request, response, next):
        version = extract_version_from_path(request.path)
        
        if not version:
            next()
            return
        
        if version_manager.check_sunset(version):
            response.status(410).json({
                'error': 'API version has been sunset',
                'code': 'VERSION_SUNSET',
                'migration_guide': version_manager.versions.get(version, {}).migration_guide_url
            })
            return
        
        # Adicionar headers de depreciacao
        ver = version_manager.versions.get(version)
        if ver and ver.status == DeprecationStatus.DEPRECATED:
            response.headers['Sunset'] = ver.sunset_at.isoformat()
            response.headers['Deprecation'] = 'true'
            if ver.migration_guide_url:
                response.headers['Link'] = f'<{ver.migration_guide_url}>; rel="successor-version"'
        
        next()
    
    return middleware
```

---

## 7. Padroes de API Gateway

### 7.1 Arquitetura de API Gateway

API Gateways atuam como pontos de entrada unico para todas as chamadas de API, centralizando funcoes de seguranca.

```
+-----------------------------------------------------------+
|                    API Gateway                            |
+-----------------------------------------------------------+
|  +-----------+  +-----------+  +-----------+             |
|  |    SSL    |  |    Rate   |  |    Auth   |             |
|  |Termination|  | Limiting  |  |Validation |             |
|  +-----------+  +-----------+  +-----------+             |
|  +-----------+  +-----------+  +-----------+             |
|  |  Request  |  |    Load   |  |  Circuit  |             |
|  |Validation |  | Balancing |  |  Breaker  |             |
|  +-----------+  +-----------+  +-----------+             |
+-----------------------------------------------------------+
          |                |                |
          v                v                v
    +----------+    +----------+    +----------+
    | Service  |    | Service  |    | Service  |
    |    A     |    |    B     |    |    C     |
    +----------+    +----------+    +----------+
```

### 7.2 Implementacao com Kong

```yaml
# Kong API Gateway Configuration
_format_version: "3.0"

services:
  - name: user-service
    url: http://user-service:8080
    routes:
      - name: user-api
        paths:
          - /api/v2/users
        strip_path: false
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              policy: redis
              redis_host: redis
          - name: jwt
            config:
              key_claim_name: kid
          - name: cors
            config:
              origins:
                - https://app.example.com
              methods:
                - GET
                - POST
                - PUT
                - DELETE
              headers:
                - Authorization
                - Content-Type
              exposed_headers:
                - X-RateLimit-Limit
                - X-RateLimit-Remaining
          - name: request-validator
            config:
              verbose_response: false
              body_schema: |
                {
                  "type": "object",
                  "properties": {
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string", "minLength": 1, "maxLength": 100}
                  },
                  "required": ["email", "name"]
                }

  - name: legacy-service
    url: http://legacy-service:8080
    routes:
      - name: legacy-api
        paths:
          - /api/v1/
        plugins:
          - name: rate-limiting
            config:
              minute: 50
          - name: response-transformer
            config:
              add:
                headers:
                  - "Sunset: Sat, 01 Jan 2025 00:00:00 GMT"
                  - "Deprecation: true"
```

### 7.3 Implementacao com Express.js Gateway

```javascript
// API Gateway simples em Express.js
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const morgan = require('morgan');

const app = express();

// Security headers
app.use(helmet());

// CORS
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS.split(','),
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
    exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
    credentials: true,
    maxAge: 86400
}));

// Global rate limiting
const globalLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,  // 15 minutes
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
    handler: (req, res) => {
        res.status(429).json({
            error: 'Too many requests',
            code: 'RATE_LIMIT_EXCEEDED',
            retryAfter: Math.ceil(req.rateLimit.resetTime / 1000)
        });
    }
});
app.use(globalLimiter);

// Request logging
app.use(morgan('combined', {
    skip: (req, res) => res.statusCode < 400
}));

// Authentication middleware
const authenticate = async (req, res, next) => {
    const apiKey = req.headers['x-api-key'];
    const token = req.headers.authorization?.split(' ')[1];
    
    if (apiKey) {
        // API Key authentication
        const keyData = await validateApiKey(apiKey);
        if (!keyData) {
            return res.status(401).json({ error: 'Invalid API key' });
        }
        req.user = keyData.user;
        req.rateLimitKey = `apikey:${keyData.id}`;
    } else if (token) {
        // JWT authentication
        try {
            const decoded = await verifyToken(token);
            req.user = decoded;
            req.rateLimitKey = `user:${decoded.id}`;
        } catch (err) {
            return res.status(401).json({ error: 'Invalid token' });
        }
    } else {
        return res.status(401).json({ error: 'Authentication required' });
    }
    
    next();
};

// Service routes
const services = {
    '/api/users': {
        target: 'http://user-service:8080',
        rateLimit: { windowMs: 60000, max: 30 }
    },
    '/api/products': {
        target: 'http://product-service:8080',
        rateLimit: { windowMs: 60000, max: 100 }
    },
    '/api/orders': {
        target: 'http://order-service:8080',
        rateLimit: { windowMs: 60000, max: 20 }
    }
};

// Mount service proxies
Object.entries(services).forEach(([path, config]) => {
    const serviceLimiter = rateLimit(config.rateLimit);
    
    app.use(path, 
        authenticate,
        serviceLimiter,
        createProxyMiddleware({
            target: config.target,
            changeOrigin: true,
            pathRewrite: { [`^${path}`]: '' },
            onError: (err, req, res) => {
                console.error('Proxy error:', err);
                res.status(502).json({ error: 'Service unavailable' });
            }
        })
    );
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Error handler
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`API Gateway running on port ${PORT}`);
});
```

---

## 8. OAuth 2.0 para APIs

### 8.1 Visao Geral do OAuth 2.0

OAuth 2.0 e o padrao de autorizacao para APIs, permitindo que aplicacoes acessem recursos em nome do usuario sem expor credenciais.

### 8.2 Bearer Tokens

```javascript
// Implementacao de Bearer Token validation
const validateBearerToken = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({
            error: 'Bearer token required',
            code: 'INVALID_TOKEN'
        });
    }
    
    const token = authHeader.substring(7);
    
    try {
        // Decodificar e validar JWT
        const decoded = jwt.verify(token, publicKey, {
            algorithms: ['RS256', 'ES256'],
            issuer: process.env.AUTH_SERVER_URL,
            audience: process.env.API_IDENTIFIER
        });
        
        // Verificar se o token nao foi revogado
        if (await isTokenRevoked(decoded.jti)) {
            return res.status(401).json({
                error: 'Token has been revoked',
                code: 'TOKEN_REVOKED'
            });
        }
        
        // Verificar scopes necessarios
        const requiredScopes = getRequiredScopes(req.method, req.path);
        const tokenScopes = decoded.scope ? decoded.scope.split(' ') : [];
        
        if (!requiredScopes.every(scope => tokenScopes.includes(scope))) {
            return res.status(403).json({
                error: 'Insufficient scope',
                code: 'INSUFFICIENT_SCOPE',
                required: requiredScopes,
                provided: tokenScopes
            });
        }
        
        // Adicionar informacoes ao request
        req.user = {
            id: decoded.sub,
            scopes: tokenScopes,
            clientId: decoded.azp
        };
        
        next();
        
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({
                error: 'Token expired',
                code: 'TOKEN_EXPIRED'
            });
        }
        
        return res.status(401).json({
            error: 'Invalid token',
            code: 'INVALID_TOKEN'
        });
    }
};
```

### 8.3 API Keys

```python
# Sistema de API Keys seguro
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

@dataclass
class APIKey:
    id: str
    key_hash: str
    user_id: str
    name: str
    scopes: list
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

class APIKeyManager:
    def __init__(self, db):
        self.db = db
    
    def generate_key(self, user_id: str, name: str, scopes: list, 
                     expires_in_days: int = 90) -> tuple[str, APIKey]:
        """Gera nova API key"""
        # Gerar chave aleatoria
        raw_key = secrets.token_urlsafe(32)
        
        # Hash para armazenamento
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Criar registro
        api_key = APIKey(
            id=secrets.token_hex(16),
            key_hash=key_hash,
            user_id=user_id,
            name=name,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            last_used_at=None,
            is_active=True
        )
        
        self.db.store_api_key(api_key)
        
        # Retornar chave completa apenas uma vez
        return f"sk_{raw_key}", api_key
    
    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Valida API key"""
        # Hash da chave fornecida
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Buscar no banco
        api_key = self.db.get_api_key_by_hash(key_hash)
        
        if not api_key:
            return None
        
        # Verificar se esta ativa
        if not api_key.is_active:
            return None
        
        # Verificar expiracao
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Atualizar ultimo uso
        api_key.last_used_at = datetime.utcnow()
        self.db.update_api_key(api_key)
        
        return api_key
    
    def revoke_key(self, key_id: str, user_id: str) -> bool:
        """Revoga API key"""
        api_key = self.db.get_api_key(key_id)
        
        if not api_key or api_key.user_id != user_id:
            return False
        
        api_key.is_active = False
        self.db.update_api_key(api_key)
        
        return True
```

---

## 9. Rate Limiting Distribuido

### 9.1 Arquitetura Distribuida

Em ambientes com multiplas instancias, rate limiting requer coordenacao distribuida.

```
+-----------------------------------------------------------+
|                  Load Balancer                            |
+-----------------------------------------------------------+
          |                |                |
          v                v                v
    +----------+    +----------+    +----------+
    |  API     |    |  API     |    |  API     |
    |Instance 1|    |Instance 2|    |Instance 3|
    +----+-----+    +----+-----+    +----+-----+
         |                |                |
         +----------------+----------------+
                          |
                          v
                +------------------+
                |  Redis Cluster   |
                | (Rate Counters)  |
                +------------------+
```

### 9.2 Implementacao com Redis

```python
# Rate limiting distribuido com Redis
import redis
import time
from typing import Optional
from dataclasses import dataclass

class DistributedRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def token_bucket(self, key: str, capacity: int, refill_rate: float, 
                     requested_tokens: int = 1) -> bool:
        """Token bucket distribuido"""
        now = time.time()
        
        # Lua script para operacao atomica
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])
        
        local bucket = redis.call('hmget', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calcular tokens a adicionar
        local time_passed = now - last_refill
        local tokens_to_add = time_passed * refill_rate
        tokens = math.min(capacity, tokens + tokens_to_add)
        
        -- Verificar se ha tokens suficientes
        if tokens >= requested then
            tokens = tokens - requested
            redis.call('hmset', key, 'tokens', tokens, 'last_refill', now)
            redis.call('expire', key, math.ceil(capacity / refill_rate) * 2)
            return 1
        else
            return 0
        end
        """
        
        result = self.redis.eval(script, 1, key, capacity, refill_rate, now, requested_tokens)
        return result == 1
    
    def sliding_window(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Sliding window distribuido"""
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remover entradas antigas
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Contar requisicoes atuais
        pipe.zcard(key)
        
        results = pipe.execute()
        current_count = results[1]
        
        if current_count >= max_requests:
            return False
        
        # Adicionar requisicao atual
        self.redis.zadd(key, {f"{now}": now})
        self.redis.expire(key, window_seconds)
        
        return True
    
    def get_usage(self, key: str, window_seconds: int) -> dict:
        """Retorna uso atual"""
        now = time.time()
        window_start = now - window_seconds
        
        # Limpar entradas antigas
        self.redis.zremrangebyscore(key, 0, window_start)
        
        count = self.redis.zcard(key)
        
        return {
            'count': count,
            'window_seconds': window_seconds,
            'reset_at': now + window_seconds
        }

# Rate limiting por dimensoes
class MultiDimensionRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limiter = DistributedRateLimiter(redis_client)
    
    def check_rate_limit(self, user_id: str, endpoint: str, ip: str) -> dict:
        """Verifica rate limit em multiplas dimensoes"""
        limits = {
            'per_user': {'max': 100, 'window': 60},
            'per_endpoint': {'max': 1000, 'window': 60},
            'per_ip': {'max': 500, 'window': 60}
        }
        
        results = {}
        
        for dimension, config in limits.items():
            key = f"rate_limit:{dimension}:{self._get_dimension_key(dimension, user_id, endpoint, ip)}"
            
            allowed = self.limiter.sliding_window(
                key, 
                config['max'], 
                config['window']
            )
            
            usage = self.limiter.get_usage(key, config['window'])
            
            results[dimension] = {
                'allowed': allowed,
                'usage': usage
            }
        
        # Verificar se todas as dimensoes permitiram
        overall_allowed = all(r['allowed'] for r in results.values())
        
        return {
            'allowed': overall_allowed,
            'dimensions': results
        }
    
    def _get_dimension_key(self, dimension: str, user_id: str, endpoint: str, ip: str) -> str:
        if dimension == 'per_user':
            return user_id
        elif dimension == 'per_endpoint':
            return endpoint
        elif dimension == 'per_ip':
            return ip
        return user_id
```

### 9.3 Circuit Breaker Pattern

```javascript
// Circuit Breaker para protecao de APIs
class CircuitBreaker {
    constructor(options = {}) {
        this.failureThreshold = options.failureThreshold || 5;
        this.successThreshold = options.successThreshold || 3;
        this.timeout = options.timeout || 30000;  // 30 segundos
        this.state = 'CLOSED';
        this.failureCount = 0;
        this.successCount = 0;
        this.lastFailureTime = null;
        this.nextAttempt = null;
    }
    
    async execute(requestFn) {
        if (this.state === 'OPEN') {
            if (Date.now() < this.nextAttempt) {
                throw new CircuitBreakerError('Circuit breaker is OPEN');
            }
            this.state = 'HALF_OPEN';
        }
        
        try {
            const result = await requestFn();
            this.onSuccess();
            return result;
        } catch (error) {
            this.onFailure();
            throw error;
        }
    }
    
    onSuccess() {
        this.failureCount = 0;
        
        if (this.state === 'HALF_OPEN') {
            this.successCount++;
            if (this.successCount >= this.successThreshold) {
                this.state = 'CLOSED';
                this.successCount = 0;
            }
        }
    }
    
    onFailure() {
        this.failureCount++;
        this.lastFailureTime = Date.now();
        
        if (this.failureCount >= this.failureThreshold) {
            this.state = 'OPEN';
            this.nextAttempt = Date.now() + this.timeout;
            this.emit('open', { failureCount: this.failureCount });
        }
    }
    
    getState() {
        return {
            state: this.state,
            failureCount: this.failureCount,
            lastFailureTime: this.lastFailureTime,
            nextAttempt: this.nextAttempt
        };
    }
}

class CircuitBreakerError extends Error {
    constructor(message) {
        super(message);
        this.name = 'CircuitBreakerError';
    }
}

// Uso
const breaker = new CircuitBreaker({
    failureThreshold: 5,
    timeout: 30000
});

async function callExternalAPI(data) {
    return breaker.execute(async () => {
        const response = await fetch('https://external-api.com/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            timeout: 5000
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        return response.json();
    });
}
```

---

## 10. Validacao de Input com OpenAPI

### 10.1 Schema Validation

```javascript
// Validacao usando OpenAPI schema
const Ajv = require('ajv');
const addFormats = require('ajv-formats');

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

// Schema de request
const createUserSchema = {
    type: 'object',
    properties: {
        name: {
            type: 'string',
            minLength: 1,
            maxLength: 100,
            pattern: '^[a-zA-Z\\s]+$'
        },
        email: {
            type: 'string',
            format: 'email',
            maxLength: 255
        },
        age: {
            type: 'integer',
            minimum: 0,
            maximum: 150
        },
        role: {
            type: 'string',
            enum: ['user', 'editor', 'viewer']
        }
    },
    required: ['name', 'email'],
    additionalProperties: false
};

const validateRequest = ajv.compile(createUserSchema);

const validateMiddleware = (req, res, next) => {
    const valid = validateRequest(req.body);
    
    if (!valid) {
        return res.status(400).json({
            error: 'Validation failed',
            code: 'VALIDATION_ERROR',
            details: validateRequest.errors.map(err => ({
                field: err.instancePath,
                message: err.message,
                params: err.params
            }))
        });
    }
    
    next();
};

// Uso
app.post('/api/users', validateMiddleware, createUserHandler);
```

### 10.2 Response Validation

```python
# Validacao de response com Pydantic
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    created_at: datetime
    role: str = Field(..., pattern=r'^(user|editor|viewer)$')
    
    class Config:
        orm_mode = True

class UserListResponse(BaseModel):
    data: List[UserResponse]
    pagination: dict
    meta: Optional[dict] = None

# Serializer que valida responses
def serialize_user(user) -> dict:
    """Serializa usuario validando contra schema"""
    return UserResponse.from_orm(user).dict()

def serialize_user_list(users, pagination) -> dict:
    """Serializa lista de usuarios"""
    return UserListResponse(
        data=[UserResponse.from_orm(u) for u in users],
        pagination=pagination
    ).dict()

# Middleware de validacao de response
class ResponseValidator:
    def __init__(self):
        self.schemas = {}
    
    def register(self, endpoint: str, schema: type):
        self.schemas[endpoint] = schema
    
    def validate(self, endpoint: str, data: dict) -> dict:
        schema = self.schemas.get(endpoint)
        if not schema:
            return data
        
        try:
            return schema(**data).dict()
        except ValidationError as e:
            raise ValueError(f"Response validation failed: {e}")

validator = ResponseValidator()
validator.register('/api/users', UserResponse)
validator.register('/api/users/list', UserListResponse)
```

---

## 11. Error Handling Seguro

### 11.1 Principios de Error Handling

O error handling adequado evita vazamento de informacoes sensiveis while providing useful feedback.

```javascript
// Classes de erro customizadas
class AppError extends Error {
    constructor(message, code, statusCode, details = null) {
        super(message);
        this.code = code;
        this.statusCode = statusCode;
        this.details = details;
        this.isOperational = true;
    }
}

class ValidationError extends AppError {
    constructor(message, details) {
        super(message, 'VALIDATION_ERROR', 400, details);
    }
}

class AuthenticationError extends AppError {
    constructor(message = 'Authentication required') {
        super(message, 'AUTHENTICATION_ERROR', 401);
    }
}

class ForbiddenError extends AppError {
    constructor(message = 'Access denied') {
        super(message, 'FORBIDDEN', 403);
    }
}

class NotFoundError extends AppError {
    constructor(resource = 'Resource') {
        super(`${resource} not found`, 'NOT_FOUND', 404);
    }
}

class RateLimitError extends AppError {
    constructor(retryAfter) {
        super('Rate limit exceeded', 'RATE_LIMIT_EXCEEDED', 429);
        this.retryAfter = retryAfter;
    }
}

// Global error handler
const errorHandler = (err, req, res, next) => {
    // Log completo para monitoramento
    console.error('Error:', {
        name: err.name,
        message: err.message,
        code: err.code,
        statusCode: err.statusCode,
        stack: err.stack,
        requestId: req.id,
        userId: req.user?.id,
        path: req.path,
        method: req.method
    });
    
    // Erro operacional (esperado)
    if (err.isOperational) {
        return res.status(err.statusCode).json({
            error: err.message,
            code: err.code,
            details: err.details,
            requestId: req.id
        });
    }
    
    // Erro inesperado - nao vazar detalhes
    return res.status(500).json({
        error: 'Internal server error',
        code: 'INTERNAL_ERROR',
        requestId: req.id
    });
};

// Middleware para capturar erros async
const asyncHandler = (fn) => (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
};
```

**Padrao Seguro para Diferentes Ambientes:**

```python
# Error handling que adapta resposta ao ambiente
import os
import traceback
from flask import jsonify, request

class ErrorHandler:
    def __init__(self, app):
        self.app = app
        self.is_production = os.getenv('FLASK_ENV') == 'production'
        
        self.app.errorhandler(Exception)(self.handle_exception)
        self.app.errorhandler(400)(self.handle_bad_request)
        self.app.errorhandler(401)(self.handle_unauthorized)
        self.app.errorhandler(403)(self.handle_forbidden)
        self.app.errorhandler(404)(self.handle_not_found)
        self.app.errorhandler(429)(self.handle_rate_limit)
        self.app.errorhandler(500)(self.handle_internal_error)
    
    def format_error(self, code, message, details=None):
        response = {
            'error': message,
            'code': code,
            'requestId': request.id if hasattr(request, 'id') else None
        }
        
        if details and not self.is_production:
            response['details'] = details
        
        return response
    
    def handle_exception(self, e):
        # Log completo
        self.app.logger.error(f'Unhandled exception: {e}', exc_info=True)
        
        # Resposta generica
        return jsonify(self.format_error(
            'INTERNAL_ERROR',
            'An unexpected error occurred'
        )), 500
    
    def handle_bad_request(self, e):
        return jsonify(self.format_error(
            'BAD_REQUEST',
            str(e.description) if hasattr(e, 'description') else 'Bad request'
        )), 400
    
    def handle_unauthorized(self, e):
        return jsonify(self.format_error(
            'UNAUTHORIZED',
            'Authentication required'
        )), 401
    
    def handle_forbidden(self, e):
        return jsonify(self.format_error(
            'FORBIDDEN',
            'Access denied'
        )), 403
    
    def handle_not_found(self, e):
        return jsonify(self.format_error(
            'NOT_FOUND',
            'Resource not found'
        )), 404
    
    def handle_rate_limit(self, e):
        return jsonify(self.format_error(
            'RATE_LIMIT_EXCEEDED',
            'Too many requests',
            {'retryAfter': e.description if hasattr(e, 'description') else 60}
        )), 429
    
    def handle_internal_error(self, e):
        self.app.logger.error(f'Internal error: {e}', exc_info=True)
        return jsonify(self.format_error(
            'INTERNAL_ERROR',
            'An internal error occurred'
        )), 500
```

---

## 12. Monitoramento e Deteccao de Anomalias

### 12.1 Metricas de Seguranca

```javascript
// Sistema de metricas de seguranca API
class APISecurityMetrics {
    constructor() {
        this.metrics = {
            requests: new Map(),
            errors: new Map(),
            authFailures: new Map(),
            rateLimitHits: new Map(),
            suspiciousActivity: new Map()
        };
    }
    
    recordRequest(req, res, duration) {
        const key = `${req.method}:${req.path}`;
        const timestamp = Date.now();
        
        if (!this.metrics.requests.has(key)) {
            this.metrics.requests.set(key, []);
        }
        
        this.metrics.requests.get(key).push({
            timestamp,
            duration,
            statusCode: res.statusCode,
            userId: req.user?.id,
            ip: req.ip
        });
        
        // Limpar registros antigos (manter ultima hora)
        const oneHourAgo = timestamp - 3600000;
        const records = this.metrics.requests.get(key);
        const filtered = records.filter(r => r.timestamp > oneHourAgo);
        this.metrics.requests.set(key, filtered);
    }
    
    recordAuthFailure(req, reason) {
        const ip = req.ip;
        const userId = req.body?.username || req.headers['x-api-key'];
        
        const key = `auth_failure:${ip}:${userId}`;
        
        if (!this.metrics.authFailures.has(key)) {
            this.metrics.authFailures.set(key, []);
        }
        
        this.metrics.authFailures.get(key).push({
            timestamp: Date.now(),
            reason,
            path: req.path
        });
        
        // Detectar forca bruta
        const recentFailures = this.metrics.authFailures.get(key)
            .filter(f => f.timestamp > Date.now() - 300000);  // 5 minutos
        
        if (recentFailures.length >= 5) {
            this.flagSuspiciousActivity({
                type: 'BRUTE_FORCE_ATTEMPT',
                ip,
                userId,
                count: recentFailures.length
            });
        }
    }
    
    flagSuspiciousActivity(activity) {
        const key = `suspicious:${activity.type}:${activity.ip}`;
        
        this.metrics.suspiciousActivity.set(key, {
            ...activity,
            detectedAt: Date.now(),
            alerted: false
        });
        
        console.warn('Suspicious activity detected:', activity);
        
        // Aqui integraria com sistema de alertas
    }
    
    getMetricsSummary() {
        const now = Date.now();
        const oneHourAgo = now - 3600000;
        
        let totalRequests = 0;
        let errorRequests = 0;
        let slowRequests = 0;
        
        for (const [, records] of this.metrics.requests) {
            const recent = records.filter(r => r.timestamp > oneHourAgo);
            totalRequests += recent.length;
            errorRequests += recent.filter(r => r.statusCode >= 400).length;
            slowRequests += recent.filter(r => r.duration > 1000).length;
        }
        
        return {
            totalRequests,
            errorRate: totalRequests > 0 ? errorRequests / totalRequests : 0,
            slowRequestRate: totalRequests > 0 ? slowRequests / totalRequests : 0,
            authFailures: Array.from(this.metrics.authFailures.values())
                .flat()
                .filter(f => f.timestamp > oneHourAgo).length,
            suspiciousActivities: Array.from(this.metrics.suspiciousActivity.values())
                .filter(a => a.detectedAt > oneHourAgo).length
        };
    }
}
```

### 12.2 Logging Estruturado

```python
# Logging de seguranca estruturado
import logging
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

@dataclass
class SecurityEvent:
    event_type: str
    severity: str
    timestamp: datetime
    user_id: Optional[str]
    ip_address: str
    path: str
    method: str
    details: dict
    request_id: Optional[str] = None

class SecurityLogger:
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Handler JSON
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_security_event(self, event: SecurityEvent):
        """Log estruturado de eventos de seguranca"""
        log_entry = {
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type,
            'severity': event.severity,
            'user_id': event.user_id,
            'ip_address': event.ip_address,
            'path': event.path,
            'method': event.method,
            'request_id': event.request_id,
            'details': event.details
        }
        
        # Log baseado em severidade
        if event.severity == 'CRITICAL':
            self.logger.critical(json.dumps(log_entry))
        elif event.severity == 'HIGH':
            self.logger.error(json.dumps(log_entry))
        elif event.severity == 'MEDIUM':
            self.logger.warning(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
    
    def log_auth_failure(self, request, reason: str):
        """Log de falha de autenticacao"""
        event = SecurityEvent(
            event_type='AUTH_FAILURE',
            severity='MEDIUM',
            timestamp=datetime.utcnow(),
            user_id=request.json.get('username') if request.is_json else None,
            ip_address=request.remote_addr,
            path=request.path,
            request_id=getattr(request, 'id', None),
            method=request.method,
            details={'reason': reason}
        )
        self.log_security_event(event)
    
    def log_rate_limit_hit(self, request, limit: int, window: int):
        """Log de rate limit atingido"""
        event = SecurityEvent(
            event_type='RATE_LIMIT_HIT',
            severity='LOW',
            timestamp=datetime.utcnow(),
            user_id=getattr(request, 'user_id', None),
            ip_address=request.remote_addr,
            path=request.path,
            request_id=getattr(request, 'id', None),
            method=request.method,
            details={'limit': limit, 'window': window}
        )
        self.log_security_event(event)
    
    def log_suspicious_activity(self, request, activity_type: str, details: dict):
        """Log de atividade suspeita"""
        event = SecurityEvent(
            event_type='SUSPICIOUS_ACTIVITY',
            severity='HIGH',
            timestamp=datetime.utcnow(),
            user_id=getattr(request, 'user_id', None),
            ip_address=request.remote_addr,
            path=request.path,
            request_id=getattr(request, 'id', None),
            method=request.method,
            details={'activity_type': activity_type, **details}
        )
        self.log_security_event(event)

# Middleware de logging de seguranca
def security_logging_middleware(app, security_logger):
    @app.before_request
    def before_request():
        request.id = str(uuid.uuid4())
        request.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        duration = time.time() - getattr(request, 'start_time', time.time())
        
        # Log de requests lentos
        if duration > 5:
            security_logger.log_security_event(SecurityEvent(
                event_type='SLOW_REQUEST',
                severity='MEDIUM',
                timestamp=datetime.utcnow(),
                user_id=getattr(request, 'user_id', None),
                ip_address=request.remote_addr,
                path=request.path,
                request_id=getattr(request, 'id', None),
                method=request.method,
                details={'duration': duration, 'status_code': response.status_code}
            ))
        
        return response
    
    @app.errorhandler(401)
    def handle_unauthorized(e):
        security_logger.log_auth_failure(request, str(e))
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(429)
    def handle_rate_limit(e):
        security_logger.log_rate_limit_hit(request, 100, 60)
        return jsonify({'error': 'Rate limit exceeded'}), 429
```

---

## 13. APIs Seguras Completas

### 13.1 Express.js - API REST Segura

```javascript
// api-server.js - Express.js API completa e segura
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
const Joi = require('joi');

const app = express();

// ==================== MIDDLEWARE DE SEGURANCA ====================

// Headers de seguranca
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", "data:", "https:"],
            connectSrc: ["'self'"]
        }
    },
    hsts: {
        maxAge: 31536000,
        includeSubDomains: true,
        preload: true
    }
}));

// CORS configurado
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['https://app.example.com'],
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
    exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'],
    credentials: true,
    maxAge: 86400
}));

// Rate limiting global
const globalLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
    message: {
        error: 'Too many requests',
        code: 'RATE_LIMIT_EXCEEDED'
    }
});
app.use(globalLimiter);

// Parsing
app.use(express.json({ limit: '10kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Request ID
app.use((req, res, next) => {
    req.id = uuidv4();
    res.set('X-Request-ID', req.id);
    next();
});

// Logging
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(JSON.stringify({
            requestId: req.id,
            method: req.method,
            path: req.path,
            statusCode: res.statusCode,
            duration,
            ip: req.ip,
            userId: req.user?.id
        }));
    });
    next();
});

// ==================== MODELOS DE DADOS ====================

const users = new Map();
const refreshTokens = new Map();

// ==================== VALIDACAO ====================

const schemas = {
    register: Joi.object({
        name: Joi.string().min(1).max(100).required(),
        email: Joi.string().email().required(),
        password: Joi.string().min(8).max(128).required()
            .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])/)
    }),
    
    login: Joi.object({
        email: Joi.string().email().required(),
        password: Joi.string().required()
    }),
    
    updateUser: Joi.object({
        name: Joi.string().min(1).max(100),
        email: Joi.string().email()
    }).min(1),
    
    createPost: Joi.object({
        title: Joi.string().min(1).max(200).required(),
        content: Joi.string().min(1).max(10000).required(),
        published: Joi.boolean().default(false)
    })
};

const validate = (schema) => (req, res, next) => {
    const { error, value } = schema.validate(req.body, { abortEarly: false });
    
    if (error) {
        return res.status(400).json({
            error: 'Validation failed',
            code: 'VALIDATION_ERROR',
            details: error.details.map(d => ({
                field: d.path.join('.'),
                message: d.message
            }))
        });
    }
    
    req.body = value;
    next();
};

// ==================== AUTENTICACAO ====================

const generateTokens = (userId) => {
    const accessToken = jwt.sign(
        { sub: userId },
        process.env.JWT_ACCESS_SECRET,
        { expiresIn: '15m', issuer: 'api.example.com' }
    );
    
    const refreshToken = jwt.sign(
        { sub: userId, type: 'refresh' },
        process.env.JWT_REFRESH_SECRET,
        { expiresIn: '7d', issuer: 'api.example.com' }
    );
    
    // Armazenar refresh token
    refreshTokens.set(refreshToken, {
        userId,
        createdAt: Date.now(),
        expiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000
    });
    
    return { accessToken, refreshToken };
};

const authenticate = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({
            error: 'Access token required',
            code: 'AUTH_TOKEN_MISSING'
        });
    }
    
    const token = authHeader.substring(7);
    
    try {
        const decoded = jwt.verify(token, process.env.JWT_ACCESS_SECRET, {
            issuer: 'api.example.com'
        });
        
        req.user = { id: decoded.sub };
        next();
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
            return res.status(401).json({
                error: 'Token expired',
                code: 'TOKEN_EXPIRED'
            });
        }
        
        return res.status(401).json({
            error: 'Invalid token',
            code: 'TOKEN_INVALID'
        });
    }
};

const authorize = (...roles) => (req, res, next) => {
    const user = users.get(req.user.id);
    
    if (!user || !roles.includes(user.role)) {
        return res.status(403).json({
            error: 'Insufficient permissions',
            code: 'FORBIDDEN'
        });
    }
    
    next();
};

// ==================== ROTAS ====================

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Registro
app.post('/api/auth/register', validate(schemas.register), async (req, res) => {
    const { name, email, password } = req.body;
    
    // Verificar se email ja existe
    for (const user of users.values()) {
        if (user.email === email) {
            return res.status(409).json({
                error: 'Email already exists',
                code: 'EMAIL_EXISTS'
            });
        }
    }
    
    // Hash da senha
    const passwordHash = await bcrypt.hash(password, 12);
    
    // Criar usuario
    const user = {
        id: uuidv4(),
        name,
        email,
        passwordHash,
        role: 'user',
        createdAt: new Date()
    };
    
    users.set(user.id, user);
    
    // Gerar tokens
    const tokens = generateTokens(user.id);
    
    res.status(201).json({
        user: {
            id: user.id,
            name: user.name,
            email: user.email,
            role: user.role
        },
        ...tokens
    });
});

// Login
app.post('/api/auth/login', validate(schemas.login), async (req, res) => {
    const { email, password } = req.body;
    
    // Buscar usuario
    let foundUser = null;
    for (const user of users.values()) {
        if (user.email === email) {
            foundUser = user;
            break;
        }
    }
    
    if (!foundUser) {
        return res.status(401).json({
            error: 'Invalid credentials',
            code: 'AUTH_INVALID_CREDENTIALS'
        });
    }
    
    // Verificar senha
    const validPassword = await bcrypt.compare(password, foundUser.passwordHash);
    
    if (!validPassword) {
        return res.status(401).json({
            error: 'Invalid credentials',
            code: 'AUTH_INVALID_CREDENTIALS'
        });
    }
    
    // Gerar tokens
    const tokens = generateTokens(foundUser.id);
    
    res.json({
        user: {
            id: foundUser.id,
            name: foundUser.name,
            email: foundUser.email,
            role: foundUser.role
        },
        ...tokens
    });
});

// Refresh token
app.post('/api/auth/refresh', (req, res) => {
    const { refreshToken } = req.body;
    
    if (!refreshToken) {
        return res.status(400).json({
            error: 'Refresh token required',
            code: 'REFRESH_TOKEN_MISSING'
        });
    }
    
    // Verificar se token existe
    const stored = refreshTokens.get(refreshToken);
    if (!stored) {
        return res.status(401).json({
            error: 'Invalid refresh token',
            code: 'INVALID_REFRESH_TOKEN'
        });
    }
    
    // Verificar expiracao
    if (Date.now() > stored.expiresAt) {
        refreshTokens.delete(refreshToken);
        return res.status(401).json({
            error: 'Refresh token expired',
            code: 'REFRESH_TOKEN_EXPIRED'
        });
    }
    
    // Revogar refresh token antigo
    refreshTokens.delete(refreshToken);
    
    // Gerar novos tokens
    const tokens = generateTokens(stored.userId);
    
    res.json(tokens);
});

// Logout
app.post('/api/auth/logout', authenticate, (req, res) => {
    const { refreshToken } = req.body;
    
    if (refreshToken) {
        refreshTokens.delete(refreshToken);
    }
    
    res.json({ message: 'Logged out successfully' });
});

// Usuarios (protegido)
app.get('/api/users', authenticate, (req, res) => {
    const usersList = Array.from(users.values()).map(u => ({
        id: u.id,
        name: u.name,
        email: u.email,
        role: u.role,
        createdAt: u.createdAt
    }));
    
    res.json({ data: usersList });
});

app.get('/api/users/:id', authenticate, (req, res) => {
    const user = users.get(req.params.id);
    
    if (!user) {
        return res.status(404).json({
            error: 'User not found',
            code: 'NOT_FOUND'
        });
    }
    
    // Usuarios so podem ver seu proprio perfil (exceto admin)
    if (req.user.id !== user.id && req.user.role !== 'admin') {
        return res.status(403).json({
            error: 'Access denied',
            code: 'FORBIDDEN'
        });
    }
    
    res.json({
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt
    });
});

app.put('/api/users/:id', authenticate, validate(schemas.updateUser), (req, res) => {
    const user = users.get(req.params.id);
    
    if (!user) {
        return res.status(404).json({
            error: 'User not found',
            code: 'NOT_FOUND'
        });
    }
    
    // Verificar ownership
    if (req.user.id !== user.id) {
        return res.status(403).json({
            error: 'Access denied',
            code: 'FORBIDDEN'
        });
    }
    
    // Atualizar campos permitidos
    const allowedFields = ['name', 'email'];
    for (const field of allowedFields) {
        if (req.body[field] !== undefined) {
            user[field] = req.body[field];
        }
    }
    
    users.set(user.id, user);
    
    res.json({
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role
    });
});

// ==================== ERROR HANDLER ====================

app.use((err, req, res, next) => {
    console.error('Unhandled error:', {
        error: err.message,
        stack: err.stack,
        requestId: req.id
    });
    
    res.status(500).json({
        error: 'Internal server error',
        code: 'INTERNAL_ERROR',
        requestId: req.id
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({
        error: 'Not found',
        code: 'NOT_FOUND'
    });
});

// ==================== INICIALIZACAO ====================

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
    console.log(`Secure API server running on port ${PORT}`);
});

module.exports = app;
```

### 13.2 Flask - API Python Segura

```python
# app.py - Flask API completa e segura
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, validator
import redis

# ==================== CONFIGURACAO ====================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_SECRET'] = os.getenv('JWT_ACCESS_SECRET')
app.config['JWT_REFRESH_SECRET'] = os.getenv('JWT_REFRESH_SECRET')

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

# CORS
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', '').split(','),
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
        "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
        "max_age": 600
    }
})

# Redis para cache e rate limiting
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== MODELOS ====================

class UserRegistration(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '@$!%*?&' for c in v):
            raise ValueError('Password must contain special character')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None

# ==================== ARMAZENAMENTO ====================

users_db = {}
refresh_tokens_db = {}

# ==================== UTILITARIOS ====================

def generate_tokens(user_id: str) -> dict:
    """Gera tokens de acesso e refresh"""
    access_token = jwt.encode(
        {
            'sub': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=15),
            'iss': 'api.example.com'
        },
        app.config['JWT_ACCESS_SECRET'],
        algorithm='HS256'
    )
    
    refresh_token = jwt.encode(
        {
            'sub': user_id,
            'type': 'refresh',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=7),
            'iss': 'api.example.com'
        },
        app.config['JWT_REFRESH_SECRET'],
        algorithm='HS256'
    )
    
    # Armazenar refresh token
    refresh_tokens_db[refresh_token] = {
        'user_id': user_id,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + timedelta(days=7)
    }
    
    return {
        'accessToken': access_token,
        'refreshToken': refresh_token
    }

def get_user_by_email(email: str) -> Optional[dict]:
    """Busca usuario por email"""
    for user in users_db.values():
        if user['email'] == email:
            return user
    return None

# ==================== MIDDLEWARE ====================

def authenticate(f):
    """Middleware de autenticacao"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Access token required',
                'code': 'AUTH_TOKEN_MISSING'
            }), 401
        
        token = auth_header[7:]
        
        try:
            payload = jwt.decode(
                token,
                app.config['JWT_ACCESS_SECRET'],
                algorithms=['HS256'],
                issuer='api.example.com'
            )
            g.user_id = payload['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({
                'error': 'Token expired',
                'code': 'TOKEN_EXPIRED'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'error': 'Invalid token',
                'code': 'TOKEN_INVALID'
            }), 401
        
        return f(*args, **kwargs)
    return decorated

def authorize(*roles):
    """Middleware de autorizacao"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = users_db.get(g.user_id)
            
            if not user or user['role'] not in roles:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'code': 'FORBIDDEN'
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# ==================== ERROR HANDLERS ====================

@app.errorhandler(400)
def bad_request(e):
    return jsonify({
        'error': 'Bad request',
        'code': 'BAD_REQUEST'
    }), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({
        'error': 'Unauthorized',
        'code': 'UNAUTHORIZED'
    }), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({
        'error': 'Forbidden',
        'code': 'FORBIDDEN'
    }), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'Not found',
        'code': 'NOT_FOUND'
    }), 404

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({
        'error': 'Rate limit exceeded',
        'code': 'RATE_LIMIT_EXCEEDED'
    }), 429

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f'Internal error: {e}')
    return jsonify({
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500

# ==================== ROTAS ====================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    try:
        data = UserRegistration(**request.json)
    except ValueError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': str(e)
        }), 400
    
    # Verificar se email ja existe
    if get_user_by_email(data.email):
        return jsonify({
            'error': 'Email already exists',
            'code': 'EMAIL_EXISTS'
        }), 409
    
    # Criar usuario
    user_id = str(uuid.uuid4())
    password_hash = pwd_context.hash(data.password)
    
    users_db[user_id] = {
        'id': user_id,
        'name': data.name,
        'email': data.email,
        'password_hash': password_hash,
        'role': 'user',
        'created_at': datetime.utcnow()
    }
    
    # Gerar tokens
    tokens = generate_tokens(user_id)
    
    return jsonify({
        'user': {
            'id': user_id,
            'name': data.name,
            'email': data.email,
            'role': 'user'
        },
        **tokens
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per hour")
def login():
    try:
        data = UserLogin(**request.json)
    except ValueError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR'
        }), 400
    
    # Buscar usuario
    user = get_user_by_email(data.email)
    
    if not user or not pwd_context.verify(data.password, user['password_hash']):
        return jsonify({
            'error': 'Invalid credentials',
            'code': 'AUTH_INVALID_CREDENTIALS'
        }), 401
    
    # Gerar tokens
    tokens = generate_tokens(user['id'])
    
    return jsonify({
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        },
        **tokens
    })

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refreshToken')
    
    if not refresh_token:
        return jsonify({
            'error': 'Refresh token required',
            'code': 'REFRESH_TOKEN_MISSING'
        }), 400
    
    # Verificar se token existe
    stored = refresh_tokens_db.get(refresh_token)
    if not stored:
        return jsonify({
            'error': 'Invalid refresh token',
            'code': 'INVALID_REFRESH_TOKEN'
        }), 401
    
    # Verificar expiracao
    if datetime.utcnow() > stored['expires_at']:
        del refresh_tokens_db[refresh_token]
        return jsonify({
            'error': 'Refresh token expired',
            'code': 'REFRESH_TOKEN_EXPIRED'
        }), 401
    
    # Revogar refresh token antigo
    del refresh_tokens_db[refresh_token]
    
    # Gerar novos tokens
    tokens = generate_tokens(stored['user_id'])
    
    return jsonify(tokens)

@app.route('/api/auth/logout', methods=['POST'])
@authenticate
def logout():
    refresh_token = request.json.get('refreshToken')
    
    if refresh_token and refresh_token in refresh_tokens_db:
        del refresh_tokens_db[refresh_token]
    
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/users', methods=['GET'])
@authenticate
def list_users():
    users_list = [{
        'id': u['id'],
        'name': u['name'],
        'email': u['email'],
        'role': u['role'],
        'created_at': u['created_at'].isoformat()
    } for u in users_db.values()]
    
    return jsonify({'data': users_list})

@app.route('/api/users/<user_id>', methods=['GET'])
@authenticate
def get_user(user_id):
    user = users_db.get(user_id)
    
    if not user:
        return jsonify({
            'error': 'User not found',
            'code': 'NOT_FOUND'
        }), 404
    
    # Verificar ownership
    if g.user_id != user_id and users_db[g.user_id].get('role') != 'admin':
        return jsonify({
            'error': 'Access denied',
            'code': 'FORBIDDEN'
        }), 403
    
    return jsonify({
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'role': user['role'],
        'created_at': user['created_at'].isoformat()
    })

@app.route('/api/users/<user_id>', methods=['PUT'])
@authenticate
def update_user(user_id):
    user = users_db.get(user_id)
    
    if not user:
        return jsonify({
            'error': 'User not found',
            'code': 'NOT_FOUND'
        }), 404
    
    # Verificar ownership
    if g.user_id != user_id:
        return jsonify({
            'error': 'Access denied',
            'code': 'FORBIDDEN'
        }), 403
    
    try:
        data = UserUpdate(**request.json)
    except ValueError as e:
        return jsonify({
            'error': 'Validation failed',
            'code': 'VALIDATION_ERROR',
            'details': str(e)
        }), 400
    
    # Atualizar campos permitidos
    if data.name is not None:
        user['name'] = data.name
    if data.email is not None:
        user['email'] = data.email
    
    return jsonify({
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'role': user['role']
    })

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@authenticate
@authorize('admin')
def delete_user(user_id):
    user = users_db.get(user_id)
    
    if not user:
        return jsonify({
            'error': 'User not found',
            'code': 'NOT_FOUND'
        }), 404
    
    del users_db[user_id]
    
    return jsonify({'message': 'User deleted successfully'})

# ==================== INICIALIZACAO ====================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
```

### 13.3 Go - API Segura

```go
// main.go - Go API completa e segura
package main

import (
    "context"
    "crypto/rand"
    "encoding/hex"
    "encoding/json"
    "log"
    "net/http"
    "os"
    "strings"
    "sync"
    "time"
    
    "github.com/golang-jwt/jwt/v5"
    "github.com/google/uuid"
    "github.com/gorilla/mux"
    "golang.org/x/crypto/bcrypt"
)

// ==================== MODELOS ====================

type User struct {
    ID           string    `json:"id"`
    Name         string    `json:"name"`
    Email        string    `json:"email"`
    PasswordHash string    `json:"-"`
    Role         string    `json:"role"`
    CreatedAt    time.Time `json:"createdAt"`
}

type Tokens struct {
    AccessToken  string `json:"accessToken"`
    RefreshToken string `json:"refreshToken"`
}

type RefreshTokenStore struct {
    Token     string
    UserID    string
    ExpiresAt time.Time
}

// ==================== ARMAZENAMENTO ====================

type Storage struct {
    mu           sync.RWMutex
    users        map[string]*User
    refreshTokens map[string]*RefreshTokenStore
}

func NewStorage() *Storage {
    return &Storage{
        users:        make(map[string]*User),
        refreshTokens: make(map[string]*RefreshTokenStore),
    }
}

func (s *Storage) GetUser(id string) *User {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return s.users[id]
}

func (s *Storage) GetUserByEmail(email string) *User {
    s.mu.RLock()
    defer s.mu.RUnlock()
    for _, user := range s.users {
        if user.Email == email {
            return user
        }
    }
    return nil
}

func (s *Storage) CreateUser(user *User) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.users[user.ID] = user
}

func (s *Storage) DeleteUser(id string) bool {
    s.mu.Lock()
    defer s.mu.Unlock()
    if _, exists := s.users[id]; exists {
        delete(s.users, id)
        return true
    }
    return false
}

func (s *Storage) StoreRefreshToken(token *RefreshTokenStore) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.refreshTokens[token.Token] = token
}

func (s *Storage) GetRefreshToken(token string) *RefreshTokenStore {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return s.refreshTokens[token]
}

func (s *Storage) DeleteRefreshToken(token string) {
    s.mu.Lock()
    defer s.mu.Unlock()
    delete(s.refreshTokens, token)
}

// ==================== UTILITARIOS ====================

var (
    jwtAccessSecret  = []byte(os.Getenv("JWT_ACCESS_SECRET"))
    jwtRefreshSecret = []byte(os.Getenv("JWT_REFRESH_SECRET"))
)

func GenerateTokens(userID string) (*Tokens, error) {
    // Access token
    accessClaims := jwt.MapClaims{
        "sub": userID,
        "iat": time.Now().Unix(),
        "exp": time.Now().Add(15 * time.Minute).Unix(),
        "iss": "api.example.com",
    }
    
    accessToken := jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims)
    accessTokenStr, err := accessToken.SignedString(jwtAccessSecret)
    if err != nil {
        return nil, err
    }
    
    // Refresh token
    refreshToken := generateRandomToken()
    refreshClaims := jwt.MapClaims{
        "sub": userID,
        "type": "refresh",
        "iat": time.Now().Unix(),
        "exp": time.Now().Add(7 * 24 * time.Hour).Unix(),
        "iss": "api.example.com",
    }
    
    refreshTokenJWT := jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims)
    _, err = refreshTokenJWT.SignedString(jwtRefreshSecret)
    if err != nil {
        return nil, err
    }
    
    return &Tokens{
        AccessToken:  accessTokenStr,
        RefreshToken: refreshToken,
    }, nil
}

func generateRandomToken() string {
    b := make([]byte, 32)
    rand.Read(b)
    return hex.EncodeToString(b)
}

func HashPassword(password string) (string, error) {
    bytes, err := bcrypt.GenerateFromPassword([]byte(password), 12)
    return string(bytes), err
}

func CheckPassword(password, hash string) bool {
    err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))
    return err == nil
}

// ==================== HANDLERS ====================

type Server struct {
    storage *Storage
}

func NewServer() *Server {
    return &Server{
        storage: NewStorage(),
    }
}

func (s *Server) RegisterHandler(w http.ResponseWriter, r *http.Request) {
    var input struct {
        Name     string `json:"name"`
        Email    string `json:"email"`
        Password string `json:"password"`
    }
    
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        respondError(w, http.StatusBadRequest, "Invalid request body")
        return
    }
    
    // Validacao
    if input.Name == "" || input.Email == "" || input.Password == "" {
        respondError(w, http.StatusBadRequest, "Name, email, and password are required")
        return
    }
    
    if len(input.Password) < 8 {
        respondError(w, http.StatusBadRequest, "Password must be at least 8 characters")
        return
    }
    
    // Verificar se email ja existe
    if existingUser := s.storage.GetUserByEmail(input.Email); existingUser != nil {
        respondError(w, http.StatusConflict, "Email already exists")
        return
    }
    
    // Hash da senha
    passwordHash, err := HashPassword(input.Password)
    if err != nil {
        respondError(w, http.StatusInternalServerError, "Failed to process password")
        return
    }
    
    // Criar usuario
    user := &User{
        ID:           uuid.New().String(),
        Name:         input.Name,
        Email:        input.Email,
        PasswordHash: passwordHash,
        Role:         "user",
        CreatedAt:    time.Now(),
    }
    
    s.storage.CreateUser(user)
    
    // Gerar tokens
    tokens, err := GenerateTokens(user.ID)
    if err != nil {
        respondError(w, http.StatusInternalServerError, "Failed to generate tokens")
        return
    }
    
    respondJSON(w, http.StatusCreated, map[string]interface{}{
        "user": map[string]interface{}{
            "id":    user.ID,
            "name":  user.Name,
            "email": user.Email,
            "role":  user.Role,
        },
        "accessToken":  tokens.AccessToken,
        "refreshToken": tokens.RefreshToken,
    })
}

func (s *Server) LoginHandler(w http.ResponseWriter, r *http.Request) {
    var input struct {
        Email    string `json:"email"`
        Password string `json:"password"`
    }
    
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        respondError(w, http.StatusBadRequest, "Invalid request body")
        return
    }
    
    // Buscar usuario
    user := s.storage.GetUserByEmail(input.Email)
    if user == nil || !CheckPassword(input.Password, user.PasswordHash) {
        respondError(w, http.StatusUnauthorized, "Invalid credentials")
        return
    }
    
    // Gerar tokens
    tokens, err := GenerateTokens(user.ID)
    if err != nil {
        respondError(w, http.StatusInternalServerError, "Failed to generate tokens")
        return
    }
    
    respondJSON(w, http.StatusOK, map[string]interface{}{
        "user": map[string]interface{}{
            "id":    user.ID,
            "name":  user.Name,
            "email": user.Email,
            "role":  user.Role,
        },
        "accessToken":  tokens.AccessToken,
        "refreshToken": tokens.RefreshToken,
    })
}

func (s *Server) ListUsersHandler(w http.ResponseWriter, r *http.Request) {
    users := make([]map[string]interface{}, 0)
    
    for _, user := range s.storage.users {
        users = append(users, map[string]interface{}{
            "id":        user.ID,
            "name":      user.Name,
            "email":     user.Email,
            "role":      user.Role,
            "createdAt": user.CreatedAt,
        })
    }
    
    respondJSON(w, http.StatusOK, map[string]interface{}{
        "data": users,
    })
}

func (s *Server) GetUserHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    userID := vars["id"]
    
    user := s.storage.GetUser(userID)
    if user == nil {
        respondError(w, http.StatusNotFound, "User not found")
        return
    }
    
    // Verificar ownership
    currentUserID := r.Context().Value("userID").(string)
    if currentUserID != user.ID {
        respondError(w, http.StatusForbidden, "Access denied")
        return
    }
    
    respondJSON(w, http.StatusOK, map[string]interface{}{
        "id":        user.ID,
        "name":      user.Name,
        "email":     user.Email,
        "role":      user.Role,
        "createdAt": user.CreatedAt,
    })
}

func (s *Server) DeleteUserHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    userID := vars["id"]
    
    if !s.storage.DeleteUser(userID) {
        respondError(w, http.StatusNotFound, "User not found")
        return
    }
    
    respondJSON(w, http.StatusOK, map[string]interface{}{
        "message": "User deleted successfully",
    })
}

// ==================== MIDDLEWARE ====================

func (s *Server) AuthMiddleware(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        
        if !strings.HasPrefix(authHeader, "Bearer ") {
            respondError(w, http.StatusUnauthorized, "Access token required")
            return
        }
        
        tokenString := strings.TrimPrefix(authHeader, "Bearer ")
        
        token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
            if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
                return nil, jwt.ErrSignatureInvalid
            }
            return jwtAccessSecret, nil
        })
        
        if err != nil || !token.Valid {
            respondError(w, http.StatusUnauthorized, "Invalid token")
            return
        }
        
        claims, ok := token.Claims.(jwt.MapClaims)
        if !ok {
            respondError(w, http.StatusUnauthorized, "Invalid token claims")
            return
        }
        
        userID, ok := claims["sub"].(string)
        if !ok {
            respondError(w, http.StatusUnauthorized, "Invalid token subject")
            return
        }
        
        ctx := context.WithValue(r.Context(), "userID", userID)
        next.ServeHTTP(w, r.WithContext(ctx))
    }
}

func (s *Server) AdminMiddleware(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        userID := r.Context().Value("userID").(string)
        user := s.storage.GetUser(userID)
        
        if user == nil || user.Role != "admin" {
            respondError(w, http.StatusForbidden, "Admin access required")
            return
        }
        
        next.ServeHTTP(w, r)
    }
}

// ==================== UTILITARIOS HTTP ====================

func respondJSON(w http.ResponseWriter, status int, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(data)
}

func respondError(w http.ResponseWriter, status int, message string) {
    respondJSON(w, status, map[string]interface{}{
        "error": message,
        "code":  strings.ReplaceAll(strings.ToUpper(message), " ", "_"),
    })
}

// ==================== MAIN ====================

func main() {
    server := NewServer()
    
    router := mux.NewRouter()
    
    // Health check
    router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        respondJSON(w, http.StatusOK, map[string]interface{}{
            "status":    "healthy",
            "timestamp": time.Now(),
        })
    }).Methods("GET")
    
    // Auth routes
    router.HandleFunc("/api/auth/register", server.RegisterHandler).Methods("POST")
    router.HandleFunc("/api/auth/login", server.LoginHandler).Methods("POST")
    
    // User routes (protected)
    router.HandleFunc("/api/users", server.AuthMiddleware(server.ListUsersHandler)).Methods("GET")
    router.HandleFunc("/api/users/{id}", server.AuthMiddleware(server.GetUserHandler)).Methods("GET")
    
    // Admin routes
    router.HandleFunc("/api/admin/users/{id}", 
        server.AuthMiddleware(server.AdminMiddleware(server.DeleteUserHandler))).Methods("DELETE")
    
    // Middleware de logging
    loggingMiddleware := func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()
            
            next.ServeHTTP(w, r)
            
            log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
        })
    }
    
    // Middleware de CORS
    corsMiddleware := func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            w.Header().Set("Access-Control-Allow-Origin", os.Getenv("ALLOWED_ORIGINS"))
            w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE")
            w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
            
            if r.Method == "OPTIONS" {
                w.WriteHeader(http.StatusOK)
                return
            }
            
            next.ServeHTTP(w, r)
        })
    }
    
    // Aplicar middlewares
    handler := loggingMiddleware(corsMiddleware(router))
    
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }
    
    log.Printf("Server starting on port %s", port)
    log.Fatal(http.ListenAndServe(":"+port, handler))
}
```

---

## 14. Exercicios

### Exercicio 1: Implementacao de Rate Limiting (Nivel: Medio)

Implemente um sistema de rate limiting com as seguintes especificacoes:

1. **Token Bucket** com capacidade de 100 tokens e refill de 10 tokens/segundo
2. **Sliding Window** com limite de 1000 requisicoes por minuto
3. **Rate limiting por dimensoes**: por IP, por usuario, e por endpoint
4. **Headers HTTP** de rate limiting (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
5. **Distribuido** usando Redis para sincronizacao entre instancias

**Requisitos minimos:**
- Testes unitarios para cada algoritmo
- Benchmark comparando desempenho
- Documentacao do comportamento em cenarios de alta carga

### Exercicio 2: Implementacao de API Gateway Seguro (Nivel: Alto)

Construa um API Gateway em Node.js ou Go com:

1. **Autenticacao centralizada** (JWT + API Keys)
2. **Rate limiting distribuido** com Redis
3. **Circuit breaker** para chamadas a servicos upstream
4. **Validacao de requests** usando OpenAPI schemas
5. **Logging estruturado** com correlacao de requisicoes
6. **Health checks** e metrics para monitoramento
7. **Load balancing** round-robin com failover

**Requisitos minimos:**
- Minimo 3 servicos backend simulados
- Testes de integracao
- Simulacao de falhas e verificacao do circuit breaker
- Dashboard de monitoramento basico

### Exercicio 3: Seguranca GraphQL (Nivel: Medio)

Implemente uma API GraphQL segura com:

1. **Query depth limiting** (maximo 7 niveis)
2. **Query complexity analysis** com pesos configuraveis
3. **Introspection control** (desabilitada em producao)
4. **Persisted queries** para queries pre-definidas
5. **Rate limiting por tipo de operacao** (Query vs Mutation vs Subscription)
6. **Batch limiting** (maximo 10 queries por batch)
7. **Field-level authorization** baseada em roles

**Requisitos minimos:**
- Schema com minimo 10 tipos e 5 mutations
- Testes de seguranca (query depth, complexity, batching)
- Documentacao de cada controle implementado

### Exercicio 4: Sistema de Auditoria de APIs (Nivel: Alto)

Desenvolva um sistema completo de auditoria para APIs:

1. **Logging estruturado** com correlacao de requisicoes
2. **Deteccao de anomalias** baseada em regras
3. **Alertas** para atividades suspeitas
4. **Metricas** de performance e seguranca
5. **Retencao e rotacao** de logs
6. **Dashboard** para visualizacao de eventos
7. **Integracao** com sistemas externos (SIEM, Slack, etc.)

**Requisitos minimos:**
- Minimo 5 regras de deteccao de anomalias
- Testes de cada regra
- Documentacao do sistema de alertas
- Simulacao de ataques e verificacao da deteccao

### Exercicio 5: Migracao de API Legada (Nivel: Alto)

Simule a migracao de uma API REST legada para uma versao segura:

1. **Analise** da API legada identificando vulnerabilidades (use OWASP API Security Top 10)
2. **Planejamento** da migracao com versionamento (v1 -> v2)
3. **Implementacao** da nova versao com todos os controles de seguranca
4. **Depreciacao** da versao antiga com headers de sunset
5. **Testes** de regressao e seguranca
6. **Documentacao** do processo de migracao

**Requisitos minimos:**
- Documento de analise de vulnerabilidades
- Plano de migracao com timeline
- Implementacao funcional das duas versoes
- Testes automatizados
- Guia de migracao para desenvolvedores

### Exercicio 6: mTLS para Microservicos (Nivel: Alto)

Implemente comunicacao mTLS entre microservicos:

1. **Certificados** auto-assinados para desenvolvimento
2. **Certificate authority** interna
3. **Rotacao automatica** de certificados
4. **Validacao de certificados** em tempo de execucao
5. **Logging** de certificados utilizados
6. **Revogacao** de certificados comprometidos

**Requisitos minimos:**
- Minimo 3 microservicos comunicando via mTLS
- Script de geracao de certificados
- Testes de comunicacao com certificados validos e invalidos
- Documentacao do processo de rotacao

---

## 15. Referencias

### Documentacao e Especificacoes

1. **OWASP API Security Top 10 2023**
   - https://owasp.org/API-Security/
   - Top 10 vulnerabilidades especificas para APIs

2. **OAuth 2.0 RFC 6749**
   - https://datatracker.ietf.org/doc/html/rfc6749
   - Especificacao oficial do OAuth 2.0

3. **JWT RFC 7519**
   - https://datatracker.ietf.org/doc/html/rfc7519
   - JSON Web Token specification

4. **OpenAPI Specification 3.0**
   - https://swagger.io/specification/
   - Padrao para documentacao de APIs

5. **GraphQL Specification**
   - https://spec.graphql.org/
   - Especificacao oficial do GraphQL

6. **gRPC Documentation**
   - https://grpc.io/docs/
   - Documentacao completa do gRPC

### Livros e Artigos

7. **API Security in Action** - Neil Madden
   - Mukhopadhyay, M. (2019). *API Security in Action*. Manning Publications.
   - Guia pratico de seguranca de APIs

8. **The OAuth 2.0 Authorization Framework**
   - Hardt, D. (2012). RFC 6749. IETF.
   - Especificacao fundamental para autenticacao de APIs

9. **GraphQL Security Best Practices**
   - https://graphql.org/learn/security/
   - Boas praticas de seguranca para GraphQL

10. **OWASP API Security Project**
    - https://owasp.org/www-project-api-security/
    - Projeto OWASP dedicado a seguranca de APIs

### CVEs e Vulnerabilidades

11. **CVE-2023-34362: MOVEit SQL Injection**
    - https://nvd.nist.gov/vuln/detail/CVE-2023-34362
    - Injecao SQL em API MOVEit Transfer

12. **CVE-2021-44228: Log4Shell**
    - https://nvd.nist.gov/vuln/detail/CVE-2021-44228
    - Injecao JNDI via APIs que logging parameters

13. **CVE-2019-11510: Pulse Secure VPN**
    - https://nvd.nist.gov/vuln/detail/CVE-2019-11510
    - Exposicao de credenciais via API

14. **BOLA vulnerabilities in real-world APIs**
    - https://owasp.org/www-project-api-security/attacks/broken-object-level-authorization/
    - Analise de vulnerabilidades BOLA

15. **API Security Incidents Database**
    - https://apisecurity.io/incidents/
    - Banco de dados de incidentes de seguranca de APIs

### Ferramentas

16. **OWASP ZAP**
    - https://www.zaproxy.org/
    - Ferramenta de teste de seguranca para APIs

17. **Postman**
    - https://www.postman.com/
    - Ferramenta para testes e documentacao de APIs

18. **Insomnia**
    - https://insomnia.rest/
    - Cliente REST/GraphQL para testes

19. **grpcurl**
    - https://github.com/fullstorydev/grpcurl
    - CLI para testes de APIs gRPC

20. **Schemathesis**
    - https://schemathesis.readthedocs.io/
    - Testes automaticos baseados em OpenAPI

---

*[Proximo capitulo: 12 - Seguranca em JavaScript e Node.js](12-javascript-nodejs.md)*
