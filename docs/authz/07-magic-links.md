# Capítulo 7 — Magic Links e Passwordless

## Introdução

Magic links representam uma das abordagens mais elegantes para autenticação passwordless: o usuário fornece apenas seu endereço de e-mail, recebe um link criptograficamente assinado, e clica nele para ser autenticado. Não há senha para lembrar, roubar, ou reutilizar. Não há campo de senha para ser keyloggered. Não há credencial estática para sofrer credential stuffing.

O conceito não é novo — sistemas como Slack e Medium popularizaram magic links há anos — mas sua adoção cresceu dramaticamente com a maturação de padrões como FIDO2/WebAuthn e a crescente frustração do usuário com senhas. Empresas como Basecamp, Discord, e GitHub oferecem magic links como alternativa primária ou complementar ao login por senha.

Para o caso Misantropi4, magic links teriam eliminado completamente o vetor de credential stuffing contra o IDAP. Se o sistema não aceitasse senhas estáticas — apenas links temporários enviados por e-mail — um atacante que obtivesse million de credenciais vazadas não teria absolutamente nada com o que trabalhar. Não haveria credencial para testar, não haveria senha para reutilizar. O ataque inteiro se tornaria inviável.

Este capítulo explora magic links em profundidade: conceitos, implementação, segurança, rate limiting, formatação de links, comparação com outros métodos, e análise de como passwordless authentication previne os vetores de ataque mais comuns contra sistemas de identidade.

---

## 7.1 Conceito de Magic Link

### 7.1.1 O que é um magic link

Um magic link é um URL contendo um token criptograficamente seguro que, quando acessado, autentica o usuário associado ao token. O termo "magic" refere-se à experiência do usuário: basta clicar no link para entrar, sem senhas, MFA, ou qualquer outro credential.

O fluxo fundamental é simples:

1. O usuário fornece seu e-mail (ou outro identificador público)
2. O sistema gera um token único, associado ao e-mail
3. O token é enviado ao usuário via e-mail (ou outro canal seguro)
4. O usuário clica no link
5. O sistema valida o token e cria uma sessão autenticada

A segurança do modelo depende de dois princípios:

1. **O canal de entrega é seguro**: Se o e-mail for comprometido, o magic link também será. A segurança do magic link é tão boa quanto a segurança do canal de entrega.
2. **O token é de uso único e tempo-limitado**: Mesmo se interceptado, o token expira rapidamente e só pode ser usado uma vez.

### 7.1.2 Por que magic links são seguros

Magic links eliminam several classes inteiras de ataques:

**Credential stuffing**: Impossível. Não existe credencial estática para testar em massa. Cada "credencial" é um link único, gerado sob demanda, válido por minutos.

**Brute force**: Impossível. Não há campo de senha para tentar combinações. O token é um valor de alta entropia (256+ bits) gerado criptograficamente.

**Phishing de senhas**: Significativamente reduzido. Um atacante pode criar um phishing page que solicita o e-mail do usuário, mas precisa comprometer o canal de e-mail para obter o magic link. O ataque requer compor mais etapas.

**Keylogging**: Significativamente reduzido. Não há senha sendo digitada. O e-mail é um valor público — digitá-lo em uma página phishing não compromete a autenticação.

**Reutilização de senhas**: Eliminada. Não há senha para reutilizar entre serviços.

**Rainbow table**: Eliminada. Não há hash de senha para atacar offline.

### 7.1.3 Limitações do modelo

Magic links não são perfeitos:

**Dependência do canal de e-mail**: Se o e-mail for comprometido, o magic link também. Isso torna a segurança do e-mail um ponto crítico.

**Latência**: O usuário precisa trocar de contexto (app de e-mail, browser), encontrar o e-mail, e clicar no link. Isso é mais lento que digitar uma senha.

**Experiência mobile**: Em dispositivos móveis, o app de e-mail pode estar em um perfil diferente do browser, complicando a troca de contexto.

**E-mail não é universal**: Nem todos os usuários têm e-mail, e nem todos os e-mails são seguros.

**Não é MFA**: Magic links são single-factor (algo que você tem — o e-mail). Devem ser combinados com outros fatores em cenários de alta segurança.

---

## 7.2 Magic Links Baseados em E-mail

### 7.2.1 Arquitetura geral

A arquitetura de um sistema de magic links baseado em e-mail envolve vários componentes:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────>│   Backend    │────>│ Email Service│
│  (Browser)   │     │   (API)      │     │  (SMTP/SES)  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────┴───────┐
                     │   Database   │
                     │  (Tokens)    │
                     └──────────────┘
```

O fluxo detalhado:

1. **Frontend**: Formulário com campo de e-mail, botão "Enviar link"
2. **Backend**: Valida e-mail, gera token, salva no banco, envia e-mail
3. **Email Service**: Envia e-mail com link formatado
4. **Usuário**: Clica no link, abre no browser
5. **Backend**: Valida token, marca como usado, cria sessão
6. **Frontend**: Redireciona para dashboard autenticado

### 7.2.2 Fluxo de autenticação detalhado

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│  User    │          │  Server  │          │  Email   │
│          │          │          │          │ Service  │
└────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │
     │  POST /auth/magic   │                     │
     │  {email: "..."}     │                     │
     │────────────────────>│                     │
     │                     │                     │
     │                     │  Generate token     │
     │                     │  Store in DB        │
     │                     │                     │
     │                     │  Send email with    │
     │                     │  magic link         │
     │                     │────────────────────>│
     │                     │                     │
     │  202 Accepted       │                     │
     │  "Link enviado"     │                     │
     │<────────────────────│                     │
     │                     │                     │
     │                     │          User receives email
     │                     │          Clicks link
     │                     │                     │
     │  GET /auth/verify   │                     │
     │  ?token=abc123      │                     │
     │────────────────────>│                     │
     │                     │                     │
     │                     │  Validate token     │
     │                     │  Check expiry       │
     │                     │  Check used         │
     │                     │  Mark as used       │
     │                     │                     │
     │                     │  Create session     │
     │  302 → Dashboard    │                     │
     │  Set-Cookie: ...    │                     │
     │<────────────────────│                     │
     │                     │                     │
```

### 7.2.3 Geração de token

O token de magic link deve ser criptograficamente seguro. A geração correta é crítica — um token previsível ou fraco compromete todo o sistema.

**Comprimento mínimo**: O token deve ter pelo menos 32 bytes (256 bits) de entropia criptográfica. Menos que isso permite ataques de força bruta.

**Gerador seguro**: Nunca use `random()`, `Math.random()`, ou `rand()` do C. Use geradores de entropia criptográfica.

```python
# Python — geração segura de token
import secrets
import hashlib

def generate_magic_token() -> str:
    """Generate a cryptographically secure magic link token.
    
    Uses 32 bytes of random data from the OS CSPRNG,
    encoded as URL-safe base64 (43 characters).
    """
    raw_token = secrets.token_urlsafe(32)
    return raw_token

def hash_token(token: str) -> str:
    """Hash the token for storage.
    
    Store the hash, not the plaintext token.
    When user clicks the link, hash the provided token
    and compare against the stored hash.
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# Example usage
token = generate_magic_token()
token_hash = hash_token(token)

# Send `token` in the email link
# Store `token_hash` in the database
print(f"Token: {token}")
print(f"Hash:  {token_hash}")
print(f"URL:   https://example.com/auth/verify?token={token}")
```

```javascript
// JavaScript (Node.js) — geração segura de token
const crypto = require('crypto');

function generateMagicToken() {
    // Generate 32 random bytes using Node's CSPRNG
    const buffer = crypto.randomBytes(32);
    // Encode as URL-safe base64 (no padding)
    return buffer.toString('base64url');
}

function hashToken(token) {
    // SHA-256 hash for storage
    return crypto.createHash('sha256')
        .update(token, 'utf-8')
        .digest('hex');
}

const token = generateMagicToken();
const tokenHash = hashToken(token);

console.log(`Token: ${token}`);
console.log(`Hash:  ${tokenHash}`);
console.log(`URL:   https://example.com/auth/verify?token=${token}`);
```

**Por que armazenar o hash e não o token?**

Se o banco de dados for comprometido, armazenar o hash impede que o atacante use os tokens diretamente. Mesmo que o atacante obtenha os hashes, ele precisaria de cada token específico para gerar o hash correspondente — e cada token é de uso único. Isso é análogo ao armazenamento seguro de senhas: nunca armazene a credencial em texto claro.

### 7.2.4 Envio de e-mail

O envio de e-mails com magic links requer atenção a vários aspectos:

**Service provider**: Use um serviço de e-mail profissional (Amazon SES, SendGrid, Mailgun, Postmark) em vez de configurar SMTP diretamente. Serviços profissionais oferecem deliverability, rate limiting, bounce handling, e compliance.

**Template do e-mail**: O e-mail deve ser claro, informativo, e não parecer phishing. Inclua:
- Identificação do serviço que enviou
- Quando o link foi solicitado
- Quanto tempo o link é válido
- Instrução para ignorar se não solicitou
- Link como fallback caso o botão não funcione

```html
<!-- Template de e-mail para magic link -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>Seu link de acesso</h2>
    
    <p>Você solicitou um link de acesso para <strong>exemplo.com</strong>.</p>
    
    <p style="margin: 30px 0;">
        <a href="https://exemplo.com/auth/verify?token=TOKEN_AQUI"
           style="background-color: #0066cc; color: white; 
                  padding: 12px 24px; text-decoration: none; 
                  border-radius: 4px; display: inline-block;">
            Clique aqui para entrar
        </a>
    </p>
    
    <p>Este link expira em <strong>15 minutos</strong> e pode ser 
       utilizado apenas uma vez.</p>
    
    <p>Se você não solicitou este link, ignore este e-mail. 
       Sua conta continua segura.</p>
    
    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
    <p style="color: #666; font-size: 12px;">
        Não consegue clicar? Copie e cole este link no navegador:<br>
        https://exemplo.com/auth/verify?token=TOKEN_AQUI
    </p>
</body>
</html>
```

**Proteção contra injeção**: Nunca insira dados do usuário diretamente no template de e-mail sem sanitização. Um atacante pode injetar HTML ou scripts no campo de e-mail, resultando em e-mails de phishing que parecem legítimos.

```python
# Python — envio seguro de magic link
from flask import Flask, request, jsonify
import secrets
import hashlib
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

def send_magic_link(email: str) -> None:
    """Send a magic link to the user's email."""
    # Validate email format
    if not is_valid_email(email):
        raise ValueError("Invalid email format")
    
    # Generate token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Store in database with expiry
    store_token(
        email=email,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        used=False
    )
    
    # Build the magic link URL
    magic_url = f"https://exemplo.com/auth/verify?token={token}"
    
    # Compose email
    msg = MIMEText(f"""
    Seu link de acesso:
    
    Clique no link abaixo para entrar (valido por 15 minutos):
    
    {magic_url}
    
    Se voce nao solicitou este link, ignore este e-mail.
    """)
    
    msg['Subject'] = 'Seu link de acesso para exemplo.com'
    msg['From'] = 'noreply@exemplo.com'
    msg['To'] = email
    
    # Send via SMTP
    with smtplib.SMTP('smtp.exemplo.com', 587) as server:
        server.starttls()
        server.login('user', 'password')
        server.send_message(msg)
```

### 7.2.5 Validação do token

A validação do token é a parte mais crítica do fluxo. Cada aspecto de segurança deve ser verificado:

```python
# Python — validação de magic link token
from datetime import datetime
from flask import request, redirect, session
import hashlib

def verify_magic_token(token: str) -> dict:
    """Verify a magic link token.
    
    Returns:
        dict with 'valid' bool and 'email' if valid
        
    Security checks:
        1. Token format validation
        2. Hash lookup in database
        3. Expiry check
        4. Single-use check
        5. IP binding (optional)
    """
    # 1. Token format: must be non-empty string
    if not token or not isinstance(token, str):
        return {'valid': False, 'error': 'Invalid token format'}
    
    # 2. Hash the provided token and look up in database
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    record = db.query(
        "SELECT * FROM magic_tokens WHERE token_hash = %s",
        [token_hash]
    )
    
    if not record:
        return {'valid': False, 'error': 'Token not found'}
    
    # 3. Expiry check
    if record.expires_at < datetime.utcnow():
        db.execute(
            "DELETE FROM magic_tokens WHERE token_hash = %s",
            [token_hash]
        )
        return {'valid': False, 'error': 'Token expired'}
    
    # 4. Single-use check
    if record.used:
        # Token was already used — possible replay attack
        db.execute(
            "DELETE FROM magic_tokens WHERE token_hash = %s",
            [token_hash]
        )
        return {'valid': False, 'error': 'Token already used'}
    
    # 5. IP binding (optional, for high-security)
    if record.ip_address and record.ip_address != request.remote_addr:
        # Log suspicious activity
        log_security_event(
            'magic_link_ip_mismatch',
            email=record.email,
            expected_ip=record.ip_address,
            actual_ip=request.remote_addr
        )
        return {'valid': False, 'error': 'IP mismatch'}
    
    # 6. Mark as used (single-use enforcement)
    db.execute(
        "UPDATE magic_tokens SET used = TRUE, used_at = NOW() "
        "WHERE token_hash = %s",
        [token_hash]
    )
    
    # 7. Delete all other unused tokens for this email
    db.execute(
        "DELETE FROM magic_tokens "
        "WHERE email = %s AND used = FALSE AND token_hash != %s",
        [record.email, token_hash]
    )
    
    return {'valid': True, 'email': record.email}
```

```javascript
// JavaScript — validação de magic link token
const crypto = require('crypto');
const db = require('./database');

async function verifyMagicToken(token, requestIp) {
    // 1. Token format validation
    if (!token || typeof token !== 'string') {
        return { valid: false, error: 'Invalid token format' };
    }
    
    // 2. Hash and lookup
    const tokenHash = crypto.createHash('sha256')
        .update(token, 'utf-8')
        .digest('hex');
    
    const record = await db.query(
        'SELECT * FROM magic_tokens WHERE token_hash = $1',
        [tokenHash]
    );
    
    if (!record) {
        return { valid: false, error: 'Token not found' };
    }
    
    // 3. Expiry check
    if (new Date(record.expires_at) < new Date()) {
        await db.query(
            'DELETE FROM magic_tokens WHERE token_hash = $1',
            [tokenHash]
        );
        return { valid: false, error: 'Token expired' };
    }
    
    // 4. Single-use check
    if (record.used) {
        await db.query(
            'DELETE FROM magic_tokens WHERE token_hash = $1',
            [tokenHash]
        );
        return { valid: false, error: 'Token already used' };
    }
    
    // 5. IP binding (optional)
    if (record.ip_address && record.ip_address !== requestIp) {
        await logSecurityEvent('magic_link_ip_mismatch', {
            email: record.email,
            expectedIp: record.ip_address,
            actualIp: requestIp
        });
        return { valid: false, error: 'IP mismatch' };
    }
    
    // 6. Mark as used
    await db.query(
        'UPDATE magic_tokens SET used = true, used_at = NOW() WHERE token_hash = $1',
        [tokenHash]
    );
    
    // 7. Invalidate other tokens for this email
    await db.query(
        'DELETE FROM magic_tokens WHERE email = $1 AND used = false AND token_hash != $2',
        [record.email, tokenHash]
    );
    
    return { valid: true, email: record.email };
}
```

---

## 7.3 Implementação Completa

### 7.3.1 Estrutura do banco de dados

A tabela de tokens deve suportar todas as verificações de segurança:

```sql
-- Tabela de tokens de magic link
CREATE TABLE magic_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    token_hash      VARCHAR(64) NOT NULL UNIQUE,
    expires_at      TIMESTAMP NOT NULL,
    used            BOOLEAN DEFAULT FALSE,
    used_at         TIMESTAMP,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    request_id      UUID
);

-- Indices para performance
CREATE INDEX idx_magic_tokens_email ON magic_tokens(email);
CREATE INDEX idx_magic_tokens_hash ON magic_tokens(token_hash);
CREATE INDEX idx_magic_tokens_expiry ON magic_tokens(expires_at);

-- Cleanup job: delete expired tokens
-- Executar periodicamente via cron ou scheduler
DELETE FROM magic_tokens WHERE expires_at < NOW() - INTERVAL '1 hour';

-- Cleanup: delete old used tokens
DELETE FROM magic_tokens 
WHERE used = TRUE AND used_at < NOW() - INTERVAL '24 hours';
```

### 7.3.2 Backend completo (Python/Flask)

```python
# magic_link_service.py — implementação completa
from flask import Flask, request, jsonify, redirect, session, make_response
import secrets
import hashlib
import psycopg2
from datetime import datetime, timedelta
from functools import wraps
import logging
import re

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

logger = logging.getLogger(__name__)

# --- Configuration ---
MAGIC_TOKEN_EXPIRY_MINUTES = 15
MAX_TOKENS_PER_EMAIL = 3
RATE_LIMIT_WINDOW = 3600  # 1 hour
MAX_REQUESTS_PER_WINDOW = 5
IP_BINDING_ENABLED = False  # Set True for high-security

# --- Database ---
def get_db():
    return psycopg2.connect(
        host='localhost',
        database='authdb',
        user='authuser',
        password='securepassword'
    )

# --- Token Generation ---
def generate_token() -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash token for secure storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# --- Rate Limiting ---
def check_rate_limit(email: str, ip: str) -> bool:
    """Check if the email/IP has exceeded rate limit."""
    conn = get_db()
    cur = conn.cursor()
    
    # Check by email
    cur.execute("""
        SELECT COUNT(*) FROM magic_tokens 
        WHERE email = %s 
        AND created_at > NOW() - INTERVAL '%s seconds'
    """, (email, RATE_LIMIT_WINDOW))
    
    email_count = cur.fetchone()[0]
    
    # Check by IP
    cur.execute("""
        SELECT COUNT(*) FROM magic_tokens 
        WHERE ip_address = %s 
        AND created_at > NOW() - INTERVAL '%s seconds'
    """, (ip, RATE_LIMIT_WINDOW))
    
    ip_count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return email_count < MAX_REQUESTS_PER_WINDOW and ip_count < MAX_REQUESTS_PER_WINDOW

# --- Email Validation ---
def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# --- Routes ---
@app.route('/auth/magic', methods=['POST'])
def request_magic_link():
    """Request a magic link for the given email."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # Validate email
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    
    # Rate limiting
    if not check_rate_limit(email, ip):
        logger.warning(f"Rate limit exceeded for {email} from {ip}")
        return jsonify({'error': 'Too many requests'}), 429
    
    # Check if user exists
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    
    if not user:
        # Don't reveal whether email exists
        # Return success even if email doesn't exist
        return jsonify({
            'message': 'If an account exists with this email, '
                       'a magic link has been sent.'
        }), 202
    
    # Invalidate existing unused tokens for this email
    cur.execute("""
        DELETE FROM magic_tokens 
        WHERE email = %s AND used = FALSE
    """, (email,))
    
    # Check token count limit
    cur.execute("""
        SELECT COUNT(*) FROM magic_tokens 
        WHERE email = %s AND used = FALSE
    """, (email,))
    
    active_tokens = cur.fetchone()[0]
    
    if active_tokens >= MAX_TOKENS_PER_EMAIL:
        return jsonify({'error': 'Too many active tokens'}), 429
    
    # Generate new token
    token = generate_token()
    token_hash = hash_token(token)
    expires_at = datetime.utcnow() + timedelta(minutes=MAGIC_TOKEN_EXPIRY_MINUTES)
    
    # Store token
    cur.execute("""
        INSERT INTO magic_tokens 
        (email, token_hash, expires_at, ip_address, user_agent, request_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        email, token_hash, expires_at,
        ip, user_agent, str(secrets.token_uuid())
    ))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Send magic link email
    magic_url = f"https://exemplo.com/auth/verify?token={token}"
    
    send_magic_link_email(
        to_email=email,
        magic_url=magic_url,
        expiry_minutes=MAGIC_TOKEN_EXPIRY_MINUTES
    )
    
    logger.info(f"Magic link sent to {email} from {ip}")
    
    return jsonify({
        'message': 'If an account exists with this email, '
                   'a magic link has been sent.'
    }), 202


@app.route('/auth/verify', methods=['GET'])
def verify_magic_link():
    """Verify a magic link token and create a session."""
    token = request.args.get('token', '')
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    if not token:
        return jsonify({'error': 'Missing token'}), 400
    
    # Hash the provided token
    token_hash = hash_token(token)
    
    # Look up token
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, email, expires_at, used, ip_address 
        FROM magic_tokens 
        WHERE token_hash = %s
    """, (token_hash,))
    
    record = cur.fetchone()
    
    if not record:
        cur.close()
        conn.close()
        logger.warning(f"Invalid token attempt from {ip}")
        return jsonify({'error': 'Invalid token'}), 401
    
    record_id, email, expires_at, used, stored_ip = record
    
    # Check expiry
    if expires_at < datetime.utcnow():
        cur.execute("DELETE FROM magic_tokens WHERE id = %s", (record_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'error': 'Token expired'}), 401
    
    # Check single-use
    if used:
        cur.execute("DELETE FROM magic_tokens WHERE id = %s", (record_id,))
        conn.commit()
        cur.close()
        conn.close()
        logger.warning(f"Reused token attempt from {ip} for {email}")
        return jsonify({'error': 'Token already used'}), 401
    
    # Check IP binding (optional)
    if IP_BINDING_ENABLED and stored_ip and stored_ip != ip:
        logger.warning(
            f"IP mismatch for {email}: "
            f"expected {stored_ip}, got {ip}"
        )
        cur.execute("DELETE FROM magic_tokens WHERE id = %s", (record_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'error': 'Token invalid for this IP'}), 401
    
    # Mark token as used
    cur.execute("""
        UPDATE magic_tokens 
        SET used = TRUE, used_at = NOW() 
        WHERE id = %s
    """, (record_id,))
    
    # Invalidate other tokens for this email
    cur.execute("""
        DELETE FROM magic_tokens 
        WHERE email = %s AND used = FALSE AND id != %s
    """, (email, record_id))
    
    # Get user ID
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user_row = cur.fetchone()
    
    conn.commit()
    cur.close()
    conn.close()
    
    if not user_row:
        return jsonify({'error': 'User not found'}), 404
    
    user_id = user_row[0]
    
    # Create session
    session['user_id'] = user_id
    session['email'] = email
    session['authenticated'] = True
    session['auth_method'] = 'magic_link'
    session['auth_time'] = datetime.utcnow().isoformat()
    
    # Log authentication
    logger.info(f"Magic link auth success: {email} from {ip}")
    
    # Redirect to dashboard
    response = make_response(redirect('/dashboard'))
    return response


@app.route('/auth/magic/status', methods=['GET'])
def magic_link_status():
    """Check if a magic link request is pending for the current email."""
    email = request.args.get('email', '').strip().lower()
    
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) FROM magic_tokens 
        WHERE email = %s 
        AND used = FALSE 
        AND expires_at > NOW()
    """, (email,))
    
    count = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return jsonify({'pending': count > 0, 'count': count})


# --- Email Sending ---
def send_magic_link_email(to_email: str, magic_url: str, expiry_minutes: int):
    """Send the magic link email."""
    # In production, use SendGrid, SES, Postmark, etc.
    import smtplib
    from email.mime.text import MIMEText
    
    body = f"""
    Seu link de acesso foi solicitado.
    
    Clique no link abaixo para entrar:
    
    {magic_url}
    
    Este link expira em {expiry_minutes} minutos e so pode ser utilizado uma vez.
    
    Se voce nao solicitou este link, ignore este e-mail.
    Sua conta continua segura.
    """
    
    msg = MIMEText(body)
    msg['Subject'] = 'Seu link de acesso'
    msg['From'] = 'noreply@exemplo.com'
    msg['To'] = to_email
    
    with smtplib.SMTP('localhost', 25) as server:
        server.send_message(msg)


if __name__ == '__main__':
    app.run(debug=False)
```

### 7.3.3 Frontend (JavaScript)

```javascript
// magic-link-auth.js — frontend para magic link
class MagicLinkAuth {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.email = null;
        this.pollInterval = null;
    }

    /**
     * Request a magic link for the given email.
     */
    async requestMagicLink(email) {
        this.email = email;
        
        const response = await fetch(`${this.apiBaseUrl}/auth/magic`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();

        if (response.ok) {
            this.showLinkSentUI();
            this.startPolling();
        } else {
            this.showError(data.error || 'Failed to send link');
        }

        return data;
    }

    /**
     * Poll for authentication status.
     * Useful when user opens email on different device.
     */
    startPolling() {
        this.pollInterval = setInterval(async () => {
            const status = await this.checkStatus();
            if (!status.pending) {
                // Token was used — user authenticated
                window.location.href = '/dashboard';
            }
        }, 3000); // Poll every 3 seconds
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    async checkStatus() {
        const response = await fetch(
            `${this.apiBaseUrl}/auth/magic/status?email=${encodeURIComponent(this.email)}`
        );
        return await response.json();
    }

    showLinkSentUI() {
        document.getElementById('auth-form').innerHTML = `
            <div class="magic-link-sent">
                <h2>Link enviado!</h2>
                <p>Verifique sua caixa de entrada em <strong>${this.email}</strong></p>
                <p class="hint">Clique no link no e-mail para entrar.</p>
                <p class="expiry">O link expira em 15 minutos.</p>
            </div>
        `;
    }

    showError(message) {
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }
}

// Usage
document.addEventListener('DOMContentLoaded', () => {
    const auth = new MagicLinkAuth('https://exemplo.com');
    
    document.getElementById('auth-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        await auth.requestMagicLink(email);
    });
});
```

---

## 7.4 Considerações de Segurança

### 7.4.1 Expiração do token

A expiração é a primeira linha de defesa. Tokens de magic link devem expirar em no máximo 15 minutos para uso geral, e menos para cenários de alta segurança.

**Configurações recomendadas:**

| Cenário | Expiração | Justificativa |
|---------|-----------|---------------|
| Login geral | 15 minutos | Balance entre conveniência e segurança |
| Password reset | 10 minutos | Mais sensível que login |
| Alto risco (financeiro) | 5 minutos | Máxima proteção |
| Admin/sistema crítico | 3 minutos | Exigência de uso imediato |

**Implementação de expiração:**

```python
# Verificação de expiração com grace period
from datetime import datetime, timedelta

def check_token_expiry(token_record, grace_period_seconds=30):
    """Check if a token is expired with optional grace period.
    
    Grace period accounts for clock skew between servers.
    """
    now = datetime.utcnow()
    
    # Primary expiry check
    if token_record.expires_at < now:
        return False, 'expired'
    
    # Warn if close to expiry (for logging)
    time_remaining = token_record.expires_at - now
    if time_remaining < timedelta(seconds=60):
        logger.warning(
            f"Token used with only {time_remaining.seconds}s remaining"
        )
    
    return True, 'valid'
```

### 7.4.2 Uso único

Cada token só pode ser usado uma vez. Após uso, deve ser marcado como "used" e imediatamente deletado ou arquivado.

**Por que uso único é crítico:**

- Se um token puder ser reutilizado, um atacante que intercepta o e-mail pode usá-lo múltiplas vezes
- Tokens reutilizáveis criam uma janela de ataque permanente
- Mesmo com expiração, reutilização permite ataques dentro da janela

**Implementação robusta de uso único:**

```python
# Atualização atômica para garantir uso único
def consume_token(token_hash: str, ip: str) -> dict:
    """Atomically consume a token (mark as used).
    
    Uses SELECT ... FOR UPDATE to prevent race conditions
    where two requests try to use the same token.
    """
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Lock the row to prevent concurrent use
        cur.execute("""
            SELECT id, email, expires_at, used 
            FROM magic_tokens 
            WHERE token_hash = %s 
            FOR UPDATE
        """, (token_hash,))
        
        record = cur.fetchone()
        
        if not record:
            return {'success': False, 'error': 'Token not found'}
        
        record_id, email, expires_at, used = record
        
        # Verify not expired
        if expires_at < datetime.utcnow():
            return {'success': False, 'error': 'Token expired'}
        
        # Verify not already used
        if used:
            logger.warning(
                f"Token replay attempt: {email} from {ip}"
            )
            return {'success': False, 'error': 'Token already used'}
        
        # Mark as used atomically
        cur.execute("""
            UPDATE magic_tokens 
            SET used = TRUE, used_at = NOW() 
            WHERE id = %s
        """, (record_id,))
        
        # Invalidate all other tokens for this email
        cur.execute("""
            DELETE FROM magic_tokens 
            WHERE email = %s AND id != %s
        """, (email, record_id))
        
        conn.commit()
        
        return {'success': True, 'email': email}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Token consumption error: {e}")
        return {'success': False, 'error': 'Internal error'}
    finally:
        cur.close()
        conn.close()
```

### 7.4.3 Binding por IP

Para cenários de alta segurança, o token pode ser vinculado ao endereço IP do usuário no momento da solicitação. Se o IP de uso for diferente do IP de solicitação, o token é rejeitado.

**Vantagens:**
- Impede que um atacante use o token de uma máquina diferente
- Reduz a superfície de ataque para interceptação de e-mail

**Desvantagens:**
- Usuários móveis mudam de rede frequentemente
- NAT e proxies podem mudar o IP entre solicitação e uso
- VPNs podem causar falsos positivos

**Implementação com tolerance:**

```python
# IP binding com tolerância para redes móveis
def check_ip_binding(token_record, current_ip: str) -> bool:
    """Check IP binding with tolerance for common network changes.
    
    Uses /24 subnet matching (same /24 = same network)
    rather than exact IP matching, to accommodate:
    - DHCP renewals
    - Mobile network switches
    - Corporate NAT
    """
    if not token_record.ip_address:
        return True  # No IP binding configured
    
    stored_ip = token_record.ip_address
    current_ip_obj = ipaddress.ip_address(current_ip)
    stored_ip_obj = ipaddress.ip_address(stored_ip)
    
    # Exact match
    if current_ip == stored_ip:
        return True
    
    # /24 subnet match (accommodate DHCP, NAT)
    if isinstance(current_ip_obj, ipaddress.IPv4Address):
        stored_network = ipaddress.IPv4Network(f"{stored_ip}/24", strict=False)
        if current_ip_obj in stored_network:
            return True
    
    # Log for security review
    logger.warning(
        f"IP binding mismatch: stored={stored_ip}, "
        f"current={current_ip}"
    )
    
    return False
```

### 7.4.4 Proteção contra enumeração

Magic links não devem revelar se um e-mail existe no sistema. Se um atacante pudesse determinar quais e-mails estão registrados, ele poderia usar essa informação para phishing direcionado.

```python
# Resposta genérica para evitar enumeração
@app.route('/auth/magic', methods=['POST'])
def request_magic_link():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    # Sempre retorna a mesma mensagem, independente
    # de o email existir ou não
    generic_response = {
        'message': 'Se uma conta existir com este email, '
                   'um link foi enviado.'
    }
    
    # Valida formato do email
    if not is_valid_email(email):
        return jsonify({'error': 'Email invalido'}), 400
    
    # Verifica rate limit (sem revelar se email existe)
    if not check_rate_limit(email, request.remote_addr):
        return jsonify(generic_response), 202  # Mesmo status code
    
    # Verifica se usuario existe
    user = db.query("SELECT id FROM users WHERE email = %s", (email,))
    
    if user:
        # Gera e envia magic link
        token = generate_token()
        store_token(email, token)
        send_magic_link_email(email, token)
    
    # Sempre retorna 202 com a mesma mensagem
    return jsonify(generic_response), 202
```

---

## 7.5 Rate Limiting

Rate limiting em magic links é essencial para prevenir abuso, mas deve ser implementado cuidadosamente para não impedir usuários legítimos.

### 7.5.1 Estratégias de rate limiting

**Rate limiting por e-mail**: Limita quantas vezes o mesmo e-mail pode solicitar magic links. Geralmente 3-5 por hora.

**Rate limiting por IP**: Limita quantas solicitações um mesmo IP pode fazer. Geralmente 10-20 por hora para contas diferentes.

**Rate limiting por usuário autenticado**: Usuários autenticados podem ter limites diferentes (mais altos).

**Rate limiting global**: Limita o total de solicitações do sistema por minuto/hora para prevenir ataques DDoS.

```python
# Rate limiting multi-dimensional
from collections import defaultdict
import time

class RateLimiter:
    """Multi-dimensional rate limiter for magic link requests."""
    
    def __init__(self):
        # Sliding window counters
        self.email_windows = defaultdict(list)
        self.ip_windows = defaultdict(list)
        self.global_window = []
    
    def is_allowed(
        self, 
        email: str, 
        ip: str,
        max_per_email: int = 5,
        max_per_ip: int = 20,
        max_global: int = 1000,
        window_seconds: int = 3600
    ) -> tuple[bool, str]:
        """Check if request is allowed.
        
        Returns (allowed, reason) tuple.
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean old entries
        self.email_windows[email] = [
            t for t in self.email_windows[email] if t > cutoff
        ]
        self.ip_windows[ip] = [
            t for t in self.ip_windows[ip] if t > cutoff
        ]
        self.global_window = [
            t for t in self.global_window if t > cutoff
        ]
        
        # Check email limit
        if len(self.email_windows[email]) >= max_per_email:
            return False, f"Email rate limit: {max_per_email}/hour"
        
        # Check IP limit
        if len(self.ip_windows[ip]) >= max_per_ip:
            return False, f"IP rate limit: {max_per_ip}/hour"
        
        # Check global limit
        if len(self.global_window) >= max_global:
            return False, "System rate limit reached"
        
        # All checks passed — record the request
        self.email_windows[email].append(now)
        self.ip_windows[ip].append(now)
        self.global_window.append(now)
        
        return True, "allowed"


# Usage
rate_limiter = RateLimiter()

@app.route('/auth/magic', methods=['POST'])
def request_magic_link():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    ip = request.remote_addr
    
    allowed, reason = rate_limiter.is_allowed(email, ip)
    
    if not allowed:
        logger.warning(f"Rate limit denied: {reason} for {email} from {ip}")
        # Always return same response to prevent enumeration
        return jsonify({
            'message': 'Se uma conta existir com este email, '
                       'um link foi enviado.'
        }), 202
    
    # Proceed with magic link generation...
```

### 7.5.2 Backoff exponencial

Para usuários que atingem o rate limit, implemente backoff exponencial em vez de bloqueio permanente:

```python
# Backoff exponencial para rate limiting
import math

def get_backoff_seconds(attempt_count: int) -> int:
    """Calculate exponential backoff delay.
    
    Attempt 1: 0s (first try)
    Attempt 2: 30s
    Attempt 3: 120s (2 minutes)
    Attempt 4: 300s (5 minutes)
    Attempt 5: 900s (15 minutes)
    Attempt 6+: blocked
    """
    if attempt_count <= 1:
        return 0
    
    delay = min(30 * (2 ** (attempt_count - 2)), 900)
    return delay

def check_with_backoff(email: str, ip: str) -> dict:
    """Check rate limit with exponential backoff."""
    attempts = get_recent_attempts(email, ip)
    
    if attempts >= 6:
        return {
            'allowed': False,
            'retry_after': None,  # Permanently blocked
            'message': 'Too many attempts. Try again later.'
        }
    
    backoff = get_backoff_seconds(attempts)
    last_attempt = get_last_attempt_time(email, ip)
    
    if backoff > 0 and last_attempt:
        elapsed = time.time() - last_attempt
        if elapsed < backoff:
            remaining = int(backoff - elapsed)
            return {
                'allowed': False,
                'retry_after': remaining,
                'message': f'Try again in {remaining} seconds'
            }
    
    return {'allowed': True, 'retry_after': 0}
```

---

## 7.6 Formato e Entrega de Links

### 7.6.1 Formato do URL

O magic link deve ser um URL simples, claro, e fácil de copiar/colar:

**Boas práticas:**
- Use HTTPS obrigatoriamente
- Domínio curto e reconhecível
- Path claro (`/auth/verify`, `/login/verify`)
- Token como query parameter (`?token=...`)
- Não use fragment (`#`) — fragmentos não são enviados ao servidor

```
BOM:   https://exemplo.com/auth/verify?token=abc123def456...
RUIM:  https://exemplo.com/auth#token=abc123def456...
RUIM:  https://sub1.sub2.sub3.exemplo.com/auth/verify?token=abc...
RUIM:  http://exemplo.com/auth/verify?token=abc123...
```

**Evite caracteres problemáticos:**

```python
# Geração de URL segura
from urllib.parse import quote

def build_magic_url(token: str, base_url: str = 'https://exemplo.com') -> str:
    """Build a secure magic link URL."""
    # Token is already URL-safe from secrets.token_urlsafe()
    # But we add an extra layer of safety
    safe_token = quote(token, safe='')
    return f"{base_url}/auth/verify?token={safe_token}"
```

### 7.6.2 Entrega por múltiplos canais

Além de e-mail, magic links podem ser entregues por:

**E-mail**: Canal primário. Mais confiável, melhor suporte, funciona em todos os dispositivos.

**SMS**: Alternativa para usuários sem e-mail confiável. Mais custoso, menos seguro (SIM swapping), menos confiável.

**Push notification**: Para apps mobile. Instantâneo, mas requer app instalado.

**Deep link**: Para apps nativos. Redireciona diretamente para o app.

```python
# Entrega multi-canal
def deliver_magic_link(
    user_id: str,
    channels: list[str] = None
) -> dict:
    """Deliver magic link via multiple channels."""
    if channels is None:
        channels = ['email']  # Default channel
    
    results = {}
    token = generate_token()
    token_hash = hash_token(token)
    
    # Store token
    store_token(user_id, token_hash)
    
    for channel in channels:
        if channel == 'email':
            email = get_user_email(user_id)
            send_magic_link_email(email, token)
            results['email'] = 'sent'
        
        elif channel == 'sms':
            phone = get_user_phone(user_id)
            if phone:
                send_magic_link_sms(phone, token)
                results['sms'] = 'sent'
            else:
                results['sms'] = 'no_phone'
        
        elif channel == 'push':
            device_tokens = get_user_devices(user_id)
            for device in device_tokens:
                send_magic_link_push(device, token)
            results['push'] = f'sent_to_{len(device_tokens)}'
    
    return results
```

### 7.6.3 E-mail fallback

Quando o e-mail não chega (filtros de spam, atrasos, problemas de deliverability), é importante oferecer um fallback:

```python
# Fallback para e-mail não entregue
def handle_magic_link_request(email: str):
    """Handle magic link request with delivery tracking."""
    token = generate_token()
    token_hash = hash_token(token)
    
    # Store with delivery tracking
    record_id = store_token(
        email=email,
        token_hash=token_hash,
        delivery_status='pending'
    )
    
    # Try email delivery
    try:
        send_magic_link_email(email, token)
        update_delivery_status(record_id, 'sent')
    except DeliveryException as e:
        logger.error(f"Email delivery failed: {e}")
        update_delivery_status(record_id, 'failed')
        
        # Try SMS fallback if phone is verified
        phone = get_verified_phone(email)
        if phone:
            try:
                send_magic_link_sms(phone, token)
                update_delivery_status(record_id, 'sms_fallback')
            except Exception as sms_error:
                logger.error(f"SMS fallback failed: {sms_error}")
    
    # Always return generic response
    return jsonify({
        'message': 'Se uma conta existir com este email, '
                   'um link foi enviado.'
    }), 202
```

---

## 7.7 Comparação com Outros Métodos

### 7.7.1 Magic links vs senhas

| Aspecto | Senhas | Magic Links |
|---------|--------|-------------|
| Credential stuffing | Vulnerável | Imune |
| Brute force | Vulnerável | Imune |
| Phishing | Vulnerável | Menos vulnerável |
| Reutilização | Comum | Impossível |
| Memória do usuário | Nenhuma | Nenhuma |
| Velocidade de login | Rápido | Mais lento (troca de contexto) |
| Experiência mobile | Bom | Médio (troca de app) |
| Requer app/serviço | Não | Sim (e-mail/SMS) |
| Custo operacional | Baixo | Médio (envio de e-mails) |
| offline login | Sim | Não |

### 7.7.2 Magic links vs OTP (One-Time Password)

| Aspecto | OTP (TOTP/HOTP) | Magic Links |
|---------|------------------|-------------|
| Requer app | Sim (TOTP) | Não |
| Requer hardware | Sim (HOTP) | Não |
| Phishing | Vulnerável | Menos vulnerável |
| Usabilidade | Média (digitar código) | Alta (clicar link) |
| Entrega | App local | E-mail/SMS |
| Custo | Zero (após setup) | Por envio |
| Disponibilidade | Sempre | Depende do canal |

### 7.7.3 Magic links vs WebAuthn/Passkeys

| Aspecto | WebAuthn/Passkeys | Magic Links |
|---------|-------------------|-------------|
| Phishing resistant | Sim | Parcialmente |
| Requer hardware | Sim (chave/biometria) | Não |
| Velocidade | Rápida | Mais lenta |
| Custo | Alto (hardware tokens) | Baixo |
| Usabilidade | Alta | Alta |
| Resiliência | Alta (chave física) | Depende do canal |
| Maturidade | Crescente | Madura |

### 7.7.4 Quando usar cada método

**Senhas**: Apenas quando compatibilidade é essencial e recursos são limitados. Sempre com MFA.

**Magic links**: Quando usabilidade e segurança contra credential stuffing são prioridades. Bem para SaaS, apps consumer, e sistemas onde MFA completa não é viável.

**WebAuthn/Passkeys**: Quando phishing resistance é crítica. Bem para empresas, governos, e sistemas financeiros.

**OTP**: Quando compatibilidade com sistemas existentes é necessária. Útil como segundo fator.

---

## 7.8 Magic Links por SMS

### 7.8.1 SMS como canal de entrega

SMS pode ser usado como canal alternativo para magic links, especialmente em regiões onde e-mail não é universal ou quando o usuário está em dispositivo móvel sem acesso a e-mail.

**Vantagens do SMS:**
- Alta taxa de entrega (>98%)
- Funciona em qualquer telefone (não precisa de smartphone)
- Mais rápido que e-mail em muitos casos
- Não requer app de e-mail

**Desvantagens do SMS:**
- SIM swapping (ataque que compromete o número de telefone)
- Interceptação por SS7 vulnerabilities
- Custo por mensagem
- Limitações de comprimento (160 caracteres)
- Menor suporte para HTML/branding

```python
# SMS magic link delivery
import twilio
from twilio.rest import Client

def send_magic_link_sms(phone_number: str, token: str):
    """Send magic link via SMS."""
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    
    magic_url = f"https://exemplo.com/auth/verify?token={token}"
    
    # SMS is limited to 160 chars — keep message short
    message_body = (
        f"Seu link de acesso: {magic_url} "
        f"(expira em 15 min)"
    )
    
    # Ensure message fits in SMS limit
    if len(message_body) > 160:
        # Use short URL or just the token
        short_url = create_short_url(magic_url)
        message_body = f"Seu link: {short_url}"
    
    client.messages.create(
        body=message_body,
        from_='+1234567890',
        to=phone_number
    )
```

### 7.8.2 SIM swapping e proteção

SIM swapping é um ataque onde o atacante convence a operadora a transferir o número de telefone da vítima para um novo chip. Isso compromete magic links enviados por SMS.

**Proteções contra SIM swapping:**
- Usar e-mail como canal primário, SMS como fallback
- Implementar delay antes de ativar novo chip (24-48h)
- Notificar o usuário quando o número de telefone é alterado
- Usar App-based OTP como fator adicional

---

## 7.9 Deep Linking

### 7.9.1 Deep links para apps nativos

Quando o usuário está em um dispositivo móvel com o app instalado, o magic link pode ser direcionado diretamente para o app em vez de abrir o browser.

**Universal Links (iOS) e App Links (Android):**

```xml
<!-- Android — AndroidManifest.xml -->
<activity android:name=".AuthActivity"
          android:exported="true">
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        <data
            android:scheme="https"
            android:host="exemplo.com"
            android:pathPrefix="/auth/verify" />
    </intent-filter>
</activity>
```

```xml
<!-- iOS — Associated Domains -->
<!-- Entitlements -->
<key>com.apple.developer.associated-domains</key>
<array>
    <string>applinks:exemplo.com</string>
</array>
```

```json
// iOS — Apple App Site Association
{
    "applinks": {
        "apps": [],
        "details": [
            {
                "appIDs": ["TEAMID.com.exemplo.app"],
                "paths": ["/auth/verify*"]
            }
        ]
    }
}
```

### 7.9.2 Fluxo de deep link

```
1. Usuário clica magic link no e-mail (iOS)
2. iOS verifica Associated Domain
3. iOS abre o app diretamente (se instalado)
4. App recebe o token via universal link
5. App valida token e cria sessão

Se o app NÃO está instalado:
1. iOS abre o browser
2. Browser carrega a página web
3. Usuário pode baixar o app ou continuar no browser
```

### 7.9.3 Fallback para browser

Sempre implemente fallback para quando o app não está instalado:

```python
# Detecção de app instalado via User-Agent
def should_use_deep_link(user_agent: str) -> bool:
    """Determine if deep linking should be attempted."""
    # Check for app-specific user agent
    if 'ExemploApp' in user_agent:
        return True
    
    # Check for mobile device
    mobile_indicators = ['Mobile', 'Android', 'iPhone', 'iPad']
    is_mobile = any(ind in user_agent for ind in mobile_indicators)
    
    # Use deep link only if app might be installed
    return is_mobile
```

---

## 7.10 Misantropi4: Como Passwordless Authentication Preveniria o Ataque

### 7.10.1 Vetor de ataque no IDAP

O ataque Misantropi4 contra o sistema IDAP utilizou credential stuffing. O fluxo do ataque foi:

1. Comprometimento de base de dados com credenciais (e-mail + senha)
2. Validação das credenciais contra o login do IDAP
3. Acesso aos dados pessoais dos cidadãos

O ponto crítico de falha foi a aceitação de senhas estáticas como único fator de autenticação. Senhas são:
- Reutilizáveis (credential stuffing funciona)
- Trocáveis (phishing funciona)
- Digítaveis (keylogging funciona)
- Memoráveis (força o usuário a escolher senhas fracas)

### 7.10.2 Por que magic links eliminariam o ataque

Se o IDAP utilizasse magic links em vez de senhas, o ataque Misantropi4 teria sido inviável:

**Não há credencial para testar**: O credential stuffing requer um par (e-mail, senha) para testar. Com magic links, cada tentativa de login gera um token único, temporário, e de uso único. Não existe "senha" para testar em million de contas.

**Não há base de dados de credenciais para vazar**: Se o IDAP não armazenasse senhas, a base de dados comprometida conteria apenas e-mails — informação pública que não permite acesso.

**Rate limiting efetivo**: Cada tentativa requer envio de e-mail e clique no link. O atacante não pode automatizar isso em escala.

**Fator adicional implícito**: O atacante precisaria comprometer o e-mail da vítima, não apenas obter uma senha vazada.

**Implementação no IDAP:**

```python
# IDAP — autenticação passwordless
class IDAPPasswordlessAuth:
    """Passwordless authentication for IDAP system.
    
    Replaces password-based auth with magic links.
    """
    
    def __init__(self):
        self.token_expiry = 10  # 10 minutes for government system
        self.max_attempts = 3   # Per email per hour
        self.ip_binding = True  # Enable for government systems
    
    def authenticate(self, cpf: str) -> dict:
        """Start passwordless authentication flow."""
        # Validate CPF format
        if not self.validate_cpf(cpf):
            return {'error': 'CPF invalido'}
        
        # Look up email by CPF
        email = self.get_email_by_cpf(cpf)
        if not email:
            # Don't reveal if CPF exists
            return {
                'message': 'Se uma conta existir com este CPF, '
                           'um link foi enviado.'
            }
        
        # Rate limit check
        if self.is_rate_limited(cpf):
            return {
                'message': 'Se uma conta existir com este CPF, '
                           'um link foi enviado.'
            }
        
        # Generate and send magic link
        token = self.generate_token()
        self.store_token(cpf, token)
        self.send_magic_link(email, token)
        
        return {
            'message': 'Se uma conta existir com este CPF, '
                       'um link foi enviado.'
        }
    
    def verify(self, token: str, ip: str) -> dict:
        """Verify magic link token."""
        # Same verification flow as standard magic links
        # with IP binding enabled
        record = self.get_token_record(token)
        
        if not record:
            return {'error': 'Token invalido'}
        
        if record.expires_at < datetime.utcnow():
            return {'error': 'Token expirado'}
        
        if record.used:
            return {'error': 'Token ja utilizado'}
        
        if self.ip_binding and record.ip_address != ip:
            return {'error': 'Token invalido para este endereco'}
        
        # Mark as used and create session
        self.consume_token(record)
        session = self.create_session(record.cpf)
        
        return {'success': True, 'session': session}
```

### 7.10.3 Comparação de segurança

**Com senhas (atual do IDAP):**
- Credential stuffing: Possivel
- Brute force: Possível
- Phishing: Possível
- Password spray: Possível
- Reutilização: Possível
- Comprometimento da base: Crítico (senhas expostas)

**Com magic links (proposta):**
- Credential stuffing: Impossível
- Brute force: Impossível
- Phishing: Significativamente mais difícil
- Password spray: Impossível
- Reutilização: Impossível
- Comprometimento da base: Menos crítico (apenas e-mails expostos)

### 7.10.4 Trade-offs para o IDAP

Magic links não são perfeitos para o IDAP:

**Acessibilidade**: Cidadãos sem e-mail ou com e-mail inacessível precisam de alternativa. O IDAP deveria oferecer múltiplos canais (e-mail, SMS, presencial).

**Velocidade**: Cidadãos que acessam o IDAP frequentemente podem achar o fluxo de e-mail lento. Uma solução híbrida (magic link para primeiro acesso, session persistente para acessos subsequentes) pode mitigar.

**Dependência de infraestrutura de e-mail**: O governo precisa garantir alta disponibilidade do serviço de e-mail.

**Custo**: Envio de e-mails e SMS tem custo operacional, mas é menor que o custo de um ataque de credential stuffing.

**Recomendação para o IDAP**: Implementar magic links como autenticação primária, com FIDO2/WebAuthn como opção para cidadãos com dispositivos compatíveis, e atendimento presencial como fallback para casos excepcionais.

---

## 7.11 Padrões e Especificações

### 7.11.1 WebAuthn Level 3 e Passkeys

O padrão WebAuthn Level 3 (W3C Recommendation) formaliza o suporte a passkeys, que são essencialmente magic links melhorados — credenciais criptograficamente seguras armazenadas no dispositivo ou sincronizadas entre dispositivos.

Passkeys combinam a usabilidade de magic links com a segurança de WebAuthn:
- Sem senha para lembrar
- Phishing resistant (origin-bound)
- Sincronização entre dispositivos
- Backup e recuperação

### 7.11.2 FIDO Alliance CTAP2

CTAP2 (Client to Authenticator Protocol) define como o browser se comunica com autenticadores (hardware tokens, biometria) para WebAuthn/passkeys.

### 7.11.3 OWASP ASVS

O OWASP Application Security Verification Standard (ASVS) categoriza magic links em V2.1.10:
- Tokens devem ter entropia mínima de 128 bits
- Tokens devem expirar em no máximo 24 horas
- Tokens devem ser de uso único
- Tokens devem ser invalidados após uso

### 7.11.4 NIST SP 800-63B

O NIST Digital Identity Guidelines (SP 800-63B) classifica magic links como "possession-based authentication" e recomenda:
- Entrega via canal seguro
- Tokens de uso único
- Expiração máxima de 24 horas
- Rate limiting robusto

---

## 7.12 Implementação Avançada

### 7.12.1 Token com claims

Para cenários avançados, o token pode conter informações adicionais (claims):

```python
# Token com claims
import json
import base64
import hmac
import hashlib

def create_magic_token_with_claims(
    email: str,
    action: str = 'login',
    ip_address: str = None,
    user_agent: str = None
) -> str:
    """Create a magic token with embedded claims.
    
    Claims are signed (not encrypted) to prevent tampering.
    The token itself is random; claims provide context.
    """
    claims = {
        'email': email,
        'action': action,
        'iat': int(time.time()),
        'exp': int(time.time()) + 600,  # 10 minutes
        'jti': str(secrets.token_uuid())  # Unique token ID
    }
    
    if ip_address:
        claims['ip'] = ip_address
    if user_agent:
        # Store hash, not full user agent (privacy)
        claims['ua_hash'] = hashlib.sha256(
            user_agent.encode()
        ).hexdigest()[:16]
    
    # Encode claims
    claims_b64 = base64.urlsafe_b64encode(
        json.dumps(claims).encode()
    ).decode().rstrip('=')
    
    # Sign with server secret
    signature = hmac.new(
        SECRET_KEY.encode(),
        claims_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{claims_b64}.{signature}"

def verify_magic_token_with_claims(token: str) -> dict:
    """Verify a magic token with claims."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return {'valid': False, 'error': 'Invalid format'}
        
        claims_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            claims_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return {'valid': False, 'error': 'Invalid signature'}
        
        # Decode claims
        padding = 4 - len(claims_b64) % 4
        claims_b64 += '=' * padding
        claims = json.loads(base64.urlsafe_b64decode(claims_b64))
        
        # Check expiry
        if claims['exp'] < time.time():
            return {'valid': False, 'error': 'Expired'}
        
        return {'valid': True, 'claims': claims}
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}
```

### 7.12.2 Token revocation

Para revogar tokens antes da expiração (logout, segurança):

```python
# Token revocation
class TokenRevocationList:
    """In-memory token revocation list.
    
    For distributed systems, use Redis or similar.
    """
    
    def __init__(self):
        self.revoked_tokens = set()
    
    def revoke(self, token_id: str):
        """Add a token to the revocation list."""
        self.revoked_tokens.add(token_id)
    
    def is_revoked(self, token_id: str) -> bool:
        """Check if a token has been revoked."""
        return token_id in self.revoked_tokens
    
    def cleanup(self, max_age_seconds: int = 3600):
        """Remove old entries (tokens that expired anyway)."""
        # In production, use a TTL-based store
        pass

# Global revocation list
revocation_list = TokenRevocationList()

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Revoke the current session's token."""
    token_id = session.get('token_id')
    if token_id:
        revocation_list.revoke(token_id)
    
    session.clear()
    return jsonify({'message': 'Logged out'})
```

### 7.12.3 Multi-tenant magic links

Para sistemas multi-tenant, magic links devem ser isolados por tenant:

```python
# Multi-tenant magic link
def generate_tenant_magic_link(
    tenant_id: str,
    email: str
) -> str:
    """Generate a magic link scoped to a specific tenant."""
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    
    # Store with tenant scope
    store_token(
        tenant_id=tenant_id,
        email=email,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    
    # Include tenant in URL
    return f"https://{tenant_id}.exemplo.com/auth/verify?token={token}"
```

---

## 7.13 Testes e Validação

### 7.13.1 Testes de segurança

```python
# Testes de segurança para magic links
import pytest
from datetime import datetime, timedelta

class TestMagicLinkSecurity:
    """Security tests for magic link implementation."""
    
    def test_token_is_cryptographically_secure(self):
        """Token must have sufficient entropy."""
        token = generate_token()
        # Token should be at least 32 bytes encoded
        assert len(token) >= 43  # 32 bytes base64url = 43 chars
    
    def test_token_is_single_use(self):
        """Token can only be used once."""
        token = create_magic_link('user@test.com')
        result1 = verify_magic_token(token)
        assert result1['valid'] is True
        
        result2 = verify_magic_token(token)
        assert result2['valid'] is False
    
    def test_token_expires(self):
        """Token must expire after configured time."""
        token = create_magic_link('user@test.com', expiry_seconds=1)
        time.sleep(2)
        
        result = verify_magic_token(token)
        assert result['valid'] is False
        assert result['error'] == 'expired'
    
    def test_used_token_is_deleted(self):
        """Used token should be removed from database."""
        token = create_magic_link('user@test.com')
        verify_magic_token(token)
        
        # Token should not exist in database
        db_token = db.query(
            "SELECT * FROM magic_tokens WHERE token = %s",
            (token,)
        )
        assert db_token is None
    
    def test_rate_limiting_works(self):
        """Rate limiting prevents excessive requests."""
        for i in range(6):  # More than limit of 5
            response = client.post('/auth/magic', json={
                'email': 'user@test.com'
            })
        
        # Last request should be rate limited
        # But still returns 202 to prevent enumeration
        assert response.status_code == 202
    
    def test_email_enumeration_prevented(self):
        """Cannot determine if email exists."""
        # Existing user
        response1 = client.post('/auth/magic', json={
            'email': 'existing@test.com'
        })
        
        # Non-existing user
        response2 = client.post('/auth/magic', json={
            'email': 'nonexistent@test.com'
        })
        
        # Same response for both
        assert response1.json == response2.json
        assert response1.status_code == response2.status_code
    
    def test_ip_binding_works(self):
        """IP binding prevents cross-IP token use."""
        token = create_magic_link(
            'user@test.com',
            ip_address='192.168.1.1'
        )
        
        # Try from different IP
        result = verify_magic_token(
            token,
            ip_address='10.0.0.1'
        )
        assert result['valid'] is False
    
    def test_token_hash_matches(self):
        """Stored hash must match token."""
        token = 'test-token-abc123'
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        
        stored_hash = hash_token(token)
        assert stored_hash == expected_hash
```

### 7.13.2 Testes de integração

```python
# Testes de integração
class TestMagicLinkIntegration:
    """Integration tests for magic link flow."""
    
    def test_full_magic_link_flow(self):
        """Test complete magic link authentication flow."""
        # 1. Request magic link
        response = client.post('/auth/magic', json={
            'email': 'user@test.com'
        })
        assert response.status_code == 202
        
        # 2. Get the token from email (mock)
        token = get_last_sent_token('user@test.com')
        assert token is not None
        
        # 3. Verify the token
        response = client.get(f'/auth/verify?token={token}')
        assert response.status_code == 302  # Redirect to dashboard
        
        # 4. Check session is created
        with client.session_transaction() as sess:
            assert sess['authenticated'] is True
            assert sess['email'] == 'user@test.com'
    
    def test_concurrent_token_requests(self):
        """Multiple token requests should invalidate previous tokens."""
        # Request 1
        client.post('/auth/magic', json={'email': 'user@test.com'})
        token1 = get_last_sent_token('user@test.com')
        
        # Request 2 (invalidates token1)
        client.post('/auth/magic', json={'email': 'user@test.com'})
        token2 = get_last_sent_token('user@test.com')
        
        # Token 1 should be invalid
        response = client.get(f'/auth/verify?token={token1}')
        assert response.status_code == 401
        
        # Token 2 should be valid
        response = client.get(f'/auth/verify?token={token2}')
        assert response.status_code == 302
```

---

## 7.14 Padrões de e-mail e deliverability

### 7.14.1 Configuração de e-mail para deliverability

O sucesso de magic links depende criticamente da entrega dos e-mails. E-mails que não chegam significam usuários bloqueados. A configuração correta de DNS e protocolos de e-mail é essencial.

**Registros DNS obrigatórios:**

```dns
; SPF — autoriza servidores de e-mail a enviar em seu nome
exemplo.com.  IN TXT  "v=spf1 include:amazonses.com ~all"

; DKIM — assinatura digital dos e-mails
selector._domainkey.exemplo.com.  IN TXT  "v=DKIM1; k=rsa; p=MIGfMA0GCS..."

; DMARC — política de tratamento de e-mails falhos
_dmarc.exemplo.com.  IN TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@exemplo.com"

; MX — registros de Mail Exchange (para.receive)
exemplo.com.  IN MX  10  inbound-smtp.us-east-1.amazonaws.com
```

**Configuração Amazon SES:**

```python
# SES — envio de magic links com alta deliverability
import boto3
from botocore.exceptions import ClientError

class MagicLinkEmailService:
    """Email service for magic links with deliverability tracking."""
    
    def __init__(self):
        self.ses = boto3.client('ses', region_name='us-east-1')
        self.sender = 'noreply@exemplo.com'
    
    def send_magic_link(self, to_email: str, magic_url: str, 
                        expiry_minutes: int) -> dict:
        """Send magic link email with tracking."""
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                     Roboto, sans-serif; max-width: 600px; margin: 0 auto; 
                     padding: 20px;">
            <div style="background: #f8f9fa; border-radius: 8px; padding: 30px;">
                <h1 style="color: #333; font-size: 24px;">
                    Seu link de acesso
                </h1>
                <p style="color: #555; font-size: 16px; line-height: 1.6;">
                    Voce solicitou um link de acesso para 
                    <strong>exemplo.com</strong>.
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{magic_url}"
                       style="background-color: #0066cc; color: white; 
                              padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; display: inline-block;
                              font-size: 16px; font-weight: bold;">
                        Entrar agora
                    </a>
                </div>
                <p style="color: #666; font-size: 14px;">
                    Este link expira em <strong>{expiry_minutes} minutos</strong> 
                    e pode ser utilizado apenas uma vez.
                </p>
                <p style="color: #999; font-size: 13px;">
                    Se voce nao solicitou este link, ignore este e-mail. 
                    Sua conta continua segura.
                </p>
            </div>
            <div style="text-align: center; padding: 20px; color: #aaa; 
                        font-size: 12px;">
                <p>Copia e cole este link no navegador:</p>
                <p style="word-break: break-all;">{magic_url}</p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Seu link de acesso foi solicitado.
        
        Clique no link abaixo para entrar (valido por {expiry_minutes} minutos):
        
        {magic_url}
        
        Se voce nao solicitou este link, ignore este e-mail.
        """
        
        try:
            response = self.ses.send_email(
                Source=self.sender,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {
                        'Data': 'Seu link de acesso para exemplo.com',
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                },
                ConfigurationSetName='MagicLinkTracking',
                Tags=[
                    {'Name': 'Type', 'Value': 'magic-link'},
                    {'Name': 'Expiry', 'Value': str(expiry_minutes)}
                ]
            )
            
            return {
                'success': True,
                'message_id': response['MessageId']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'MailFromDomainNotVerifiedException':
                return {'success': False, 'error': 'Domain not verified'}
            elif error_code == 'MessageRejected':
                return {'success': False, 'error': 'Message rejected'}
            elif error_code == 'TooManyRequestsException':
                return {'success': False, 'error': 'Rate limited by SES'}
            else:
                return {'success': False, 'error': str(e)}
    
    def send_batch_magic_links(self, recipients: list) -> dict:
        """Send magic links to multiple recipients."""
        results = {'sent': 0, 'failed': 0, 'errors': []}
        
        for recipient in recipients:
            result = self.send_magic_link(
                to_email=recipient['email'],
                magic_url=recipient['magic_url'],
                expiry_minutes=15
            )
            
            if result['success']:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'email': recipient['email'],
                    'error': result['error']
                })
        
        return results
```

**Monitoramento de delivery:**

```python
# Delivery monitoring
class EmailDeliveryMonitor:
    """Monitor email delivery rates and bounce handling."""
    
    def __init__(self, db, alert_service):
        self.db = db
        self.alert_service = alert_service
    
    def process_bounce(self, email: str, bounce_type: str):
        """Handle email bounces."""
        if bounce_type == 'Permanent':
            # Mark email as invalid
            self.db.execute("""
                UPDATE users 
                SET email_valid = FALSE, 
                    email_invalidated_at = NOW()
                WHERE email = %s
            """, (email,))
            
            # Alert admin
            self.alert_service.send(
                'email_bounce_permanent',
                f'Email {email} permanently bounced'
            )
        
        elif bounce_type == 'Transient':
            # Temporary failure — retry later
            self.db.execute("""
                INSERT INTO email_retry_queue 
                (email, retry_count, next_retry_at)
                VALUES (%s, 0, NOW() + INTERVAL '5 minutes')
                ON CONFLICT (email) 
                DO UPDATE SET retry_count = retry_count + 1,
                             next_retry_at = NOW() + INTERVAL '5 minutes'
            """, (email,))
    
    def get_delivery_stats(self, hours: int = 24) -> dict:
        """Get delivery statistics."""
        stats = self.db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'bounced' THEN 1 ELSE 0 END) as bounced,
                SUM(CASE WHEN status = 'complained' THEN 1 ELSE 0 END) as complained
            FROM email_sends
            WHERE created_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        
        result = stats[0]
        result['delivery_rate'] = (
            result['delivered'] / result['total'] * 100 
            if result['total'] > 0 else 0
        )
        result['bounce_rate'] = (
            result['bounced'] / result['total'] * 100 
            if result['total'] > 0 else 0
        )
        
        return result
    
    def check_delivery_health(self):
        """Check if delivery rates are healthy."""
        stats = self.get_delivery_stats(hours=1)
        
        if stats['bounce_rate'] > 5:
            self.alert_service.send(
                'high_bounce_rate',
                f"Bounce rate: {stats['bounce_rate']:.1f}% "
                f"(threshold: 5%)"
            )
        
        if stats['delivery_rate'] < 95:
            self.alert_service.send(
                'low_delivery_rate',
                f"Delivery rate: {stats['delivery_rate']:.1f}% "
                f"(threshold: 95%)"
            )
```

### 7.14.2 Handling de e-mails que não chegam

Quando o e-mail não chega, o usuário fica bloqueado. O sistema deve oferecer múltiplos caminhos:

```python
# Fallback strategy para e-mails não entregues
class MagicLinkFallbackStrategy:
    """Strategy for handling undelivered magic links."""
    
    def __init__(self, db, email_service, sms_service):
        self.db = db
        self.email_service = email_service
        self.sms_service = sms_service
    
    def handle_delivery_failure(self, user_id: str, 
                                 error: str) -> dict:
        """Handle email delivery failure with fallbacks."""
        user = self.db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        if not user:
            return {'error': 'User not found'}
        
        # Strategy 1: Retry email with different provider
        if 'ses' in error.lower():
            result = self.retry_with_backup_provider(user)
            if result['success']:
                return result
        
        # Strategy 2: SMS fallback
        if user.get('phone_verified'):
            result = self.send_sms_fallback(user)
            if result['success']:
                return result
        
        # Strategy 3: In-app notification
        if user.get('push_enabled'):
            result = self.send_push_notification(user)
            if result['success']:
                return result
        
        # Strategy 4: Offer manual code
        return self.generate_manual_code(user)
    
    def retry_with_backup_provider(self, user: dict) -> dict:
        """Retry email with backup provider (Mailgun, SendGrid)."""
        try:
            # Try SendGrid as backup
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email='noreply@exemplo.com',
                to_emails=user['email'],
                subject='Seu link de acesso',
                html_content=self.build_email_html(user)
            )
            
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
            
            return {'success': True, 'provider': 'sendgrid'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_sms_fallback(self, user: dict) -> dict:
        """Send magic link via SMS."""
        token = self.generate_fallback_token(user['id'])
        magic_url = f"https://exemplo.com/auth/verify?token={token}"
        
        result = self.sms_service.send(
            phone=user['phone'],
            message=f"Seu link: {magic_url} (15 min)"
        )
        
        return {'success': result, 'channel': 'sms'}
    
    def generate_manual_code(self, user: dict) -> dict:
        """Generate a manual verification code."""
        code = secrets.token_hex(3).upper()  # 6 chars
        
        self.db.execute("""
            INSERT INTO manual_codes 
            (user_id, code_hash, expires_at)
            VALUES (%s, %s, NOW() + INTERVAL '10 minutes')
        """, (user['id'], hashlib.sha256(code.encode()).hexdigest()))
        
        return {
            'success': True,
            'method': 'manual_code',
            'instructions': (
                f'Um codigo de verificacao foi gerado. '
                f'Acesse https://exemplo.com/auth/manual '
                f'e insira o codigo: {code}'
            )
        }
```

### 7.14.3 Proteção contra abuso de envio

Magic links podem ser abusados para spam (enviar e-mails indesejados em nome do sistema). Proteções:

```python
# Anti-abuse para envio de magic links
class MagicLinkAbuseProtection:
    """Protect against abuse of magic link sending."""
    
    def __init__(self, db):
        self.db = db
    
    def check_abuse(self, email: str, ip: str, 
                    user_agent: str) -> dict:
        """Comprehensive abuse check before sending."""
        checks = {
            'rate_limit': self.check_rate_limit(email, ip),
            'Disposable email': self.check_disposable_email(email),
            'Known spam': self.check_known_spam_email(email),
            'Bot detection': self.check_bot(user_agent),
            'Geographic anomaly': self.check_geo_anomaly(email, ip),
        }
        
        # If any check fails, block
        for check_name, result in checks.items():
            if not result['passed']:
                return {
                    'allowed': False,
                    'reason': check_name,
                    'details': result
                }
        
        return {'allowed': True}
    
    def check_disposable_email(self, email: str) -> dict:
        """Check if email is from a disposable provider."""
        disposable_domains = [
            'tempmail.com', 'throwaway.email', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com', 'trashmail.com',
            'guerrillamailblock.com', 'sharklasers.com',
            'grr.la', 'dispostable.com', '10minutemail.com',
        ]
        
        domain = email.split('@')[1].lower()
        is_disposable = domain in disposable_domains
        
        return {
            'passed': not is_disposable,
            'domain': domain,
            'is_disposable': is_disposable
        }
    
    def check_bot(self, user_agent: str) -> dict:
        """Basic bot detection via user agent."""
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'python-requests', 'curl', 'wget', 'httpclient'
        ]
        
        is_bot = any(
            pattern in user_agent.lower() 
            for pattern in bot_patterns
        )
        
        return {
            'passed': not is_bot,
            'user_agent': user_agent,
            'is_bot': is_bot
        }
    
    def check_geo_anomaly(self, email: str, ip: str) -> dict:
        """Check for geographic anomalies."""
        # Get last known IP for this email
        last_ip = self.db.query("""
            SELECT ip_address FROM magic_tokens 
            WHERE email = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (email,))
        
        if not last_ip:
            return {'passed': True, 'reason': 'no_history'}
        
        # Simple geolocation check
        last_country = self.get_country(last_ip[0]['ip_address'])
        current_country = self.get_country(ip)
        
        # If countries differ, flag as potential anomaly
        anomaly = last_country != current_country
        
        return {
            'passed': not anomaly,
            'last_country': last_country,
            'current_country': current_country,
            'is_anomaly': anomaly
        }
    
    def get_country(self, ip: str) -> str:
        """Get country from IP address."""
        # In production, use MaxMind GeoIP or similar
        try:
            import geoip2.database
            reader = geoip2.database.Reader('/path/to/GeoLite2-Country.mmdb')
            response = reader.country(ip)
            return response.country.iso_code
        except Exception:
            return 'unknown'
```

---

## 7.15 Checklist de Implementação

### Segurança obrigatória:
- [ ] Token de pelo menos 256 bits de entropia
- [ ] Token armazenado como hash (não texto claro)
- [ ] Expiração de no máximo 15 minutos
- [ ] Uso único (token deletado após uso)
- [ ] Rate limiting por e-mail e IP
- [ ] Resposta genérica (anti-enumeração)
- [ ] HTTPS obrigatório
- [ ] Limpeza periódica de tokens expirados

### Segurança recomendada:
- [ ] IP binding para sistemas de alta segurança
- [ ] Backoff exponencial para rate limiting
- [ ] Logging de eventos de segurança
- [ ] Notificação ao usuário quando link é solicitado
- [ ] Token revocation para logout
- [ ] Multi-canal (e-mail + SMS fallback)

### Usabilidade:
- [ ] Template de e-mail claro e informativo
- [ ] Link como fallback no e-mail
- [ ] Instruções para ignorar se não solicitou
- [ ] Indicação de quanto tempo o link é válido
- [ ] Deep linking para apps mobile
- [ ] Fallback para browser quando app não está instalado

### Operacional:
- [ ] Monitoramento de delivery rate
- [ ] Alertas para falhas de envio
- [ ] Cleanup automático de tokens antigos
- [ ] Métricas de uso e taxa de sucesso
- [ ] Documentação do API para clientes

---

## 7.15 Resumo

Magic links são uma alternativa segura e elegante a senhas para autenticação. Ao eliminar credenciais estáticas, eles tornam credential stuffing, brute force, e password spray impossíveis. A segurança depende de tokens criptograficamente seguros, expiração curta, uso único, e rate limiting robusto.

Para o caso Misantropi4, magic links teriam eliminado completamente o vetor de ataque. Se o IDAP não aceitasse senhas estáticas, o comprometimento de million de credenciais teria sido inútil — não haveria "senha" para testar contra o login.

Magic links não são perfeitos: dependem do canal de entrega (e-mail/SMS), são mais lentos que senhas, e requerem infraestrutura de e-mail confiável. Para sistemas de alta segurança, magic links devem ser combinados com outros fatores (FIDO2, biometria) ou usados como parte de uma arquitetura de autenticação passwordless mais ampla.

O futuro da autenticação é passwordless. Magic links são um passo nessa direção, e WebAuthn/Passkeys (capítulo seguinte) são o próximo nível — combinando a usabilidade de magic links com a segurança de autenticadores criptográficos hardware.

## 7.16 Casos de uso avançados

### 7.16.1 Magic links para onboarding de usuários

Magic links são ideais para onboarding porque eliminam a necessidade de o usuário criar uma senha imediatamente. O fluxo de onboarding pode usar magic links para o primeiro acesso:

```python
# Onboarding flow com magic link
class UserOnboardingService:
    """Onboard new users with magic links."""
    
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service
    
    def invite_user(self, email: str, role: str, 
                   invited_by: str) -> dict:
        """Invite a new user with magic link."""
        # Check if user already exists
        existing = self.db.query(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )
        
        if existing:
            return {'error': 'User already exists'}
        
        # Create user (inactive until magic link is used)
        user_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO users (id, email, active, invited_by, invited_at)
            VALUES (%s, %s, FALSE, %s, NOW())
        """, (user_id, email, invited_by))
        
        # Generate magic link for onboarding
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self.db.execute("""
            INSERT INTO magic_tokens 
            (user_id, email, token_hash, expires_at, purpose)
            VALUES (%s, %s, %s, NOW() + INTERVAL '7 days', 'onboarding')
        """, (user_id, email, token_hash))
        
        # Send invitation email
        magic_url = f"https://exemplo.com/onboard?token={token}"
        
        self.email_service.send(
            to=email,
            subject=f'Convite para {INVITE_ORG_NAME}',
            body=f'''
            Voce foi convidado para {INVITE_ORG_NAME}.
            
            Clique no link abaixo para criar sua conta:
            {magic_url}
            
            Este link expira em 7 dias.
            '''
        )
        
        # Assign initial role
        self.db.execute("""
            INSERT INTO user_roles (user_id, role_id, granted_by)
            VALUES (%s, (SELECT id FROM roles WHERE name = %s), %s)
        """, (user_id, role, invited_by))
        
        return {'success': True, 'user_id': user_id}
    
    def complete_onboarding(self, token: str, 
                           user_data: dict) -> dict:
        """Complete onboarding after magic link is used."""
        # Verify token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        record = self.db.query("""
            SELECT * FROM magic_tokens 
            WHERE token_hash = %s 
            AND purpose = 'onboarding'
            AND used = FALSE
            AND expires_at > NOW()
        """, (token_hash,))
        
        if not record:
            return {'error': 'Invalid or expired token'}
        
        user_id = record[0]['user_id']
        
        # Update user with profile data
        self.db.execute("""
            UPDATE users 
            SET name = %s, 
                active = TRUE,
                onboarded_at = NOW()
            WHERE id = %s
        """, (user_data.get('name', ''), user_id))
        
        # Mark token as used
        self.db.execute("""
            UPDATE magic_tokens SET used = TRUE, used_at = NOW()
            WHERE token_hash = %s
        """, (token_hash,))
        
        return {'success': True, 'user_id': user_id}
```

### 7.16.2 Magic links para autenticação de APIs

Magic links também podem ser usados para autenticar chamadas de API em contextos específicos:

```python
# API authentication com magic links
class APIMagicLinkAuth:
    """Magic link authentication for API endpoints."""
    
    def __init__(self, db):
        self.db = db
    
    def generate_api_magic_link(self, api_key: str, 
                                scopes: list) -> str:
        """Generate a magic link for API access."""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self.db.execute("""
            INSERT INTO api_magic_tokens 
            (api_key_hash, token_hash, scopes, expires_at)
            VALUES (%s, %s, %s, NOW() + INTERVAL '5 minutes')
        """, (
            hashlib.sha256(api_key.encode()).hexdigest(),
            token_hash,
            json.dumps(scopes)
        ))
        
        return f"https://api.exemplo.com/auth/verify?token={token}"
    
    def verify_api_magic_link(self, token: str) -> dict:
        """Verify API magic link and return access token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        record = self.db.query("""
            SELECT * FROM api_magic_tokens 
            WHERE token_hash = %s 
            AND used = FALSE
            AND expires_at > NOW()
        """, (token_hash,))
        
        if not record:
            return {'error': 'Invalid token'}
        
        # Mark as used
        self.db.execute("""
            UPDATE api_magic_tokens 
            SET used = TRUE 
            WHERE token_hash = %s
        """, (token_hash,))
        
        # Generate access token
        access_token = self.generate_access_token(
            api_key_hash=record[0]['api_key_hash'],
            scopes=json.loads(record[0]['scopes'])
        )
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scopes': json.loads(record[0]['scopes'])
        }
```

### 7.16.3 Magic links para recuperação de conta

Quando o usuário perde acesso a todos os fatores de autenticação, magic links podem servir como mecanismo de recuperação:

```python
# Account recovery com magic links
class AccountRecoveryService:
    """Account recovery via magic links."""
    
    def __init__(self, db, email_service, audit_log):
        self.db = db
        self.email_service = email_service
        self.audit_log = audit_log
    
    def initiate_recovery(self, identifier: str, 
                         recovery_method: str) -> dict:
        """Start account recovery process."""
        # Find user by email, phone, or username
        user = self._find_user(identifier)
        
        if not user:
            # Don't reveal if user exists
            return {
                'message': 'Se uma conta existir com este '
                          'identificador, um link de recuperacao '
                          'foi enviado.'
            }
        
        # Check cooldown (prevent abuse)
        if self._is_in_cooldown(user['id']):
            return {
                'message': 'Se uma conta existir com este '
                          'identificador, um link de recuperacao '
                          'foi enviado.'
            }
        
        # Generate recovery token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self.db.execute("""
            INSERT INTO recovery_tokens 
            (user_id, token_hash, method, expires_at)
            VALUES (%s, %s, %s, NOW() + INTERVAL '1 hour')
        """, (user['id'], token_hash, recovery_method))
        
        # Send via selected method
        if recovery_method == 'email':
            recovery_url = f"https://exemplo.com/recover?token={token}"
            self.email_service.send(
                to=user['email'],
                subject='Recuperacao de conta',
                body=f'Use este link para recuperar sua conta: '
                     f'{recovery_url}\n\nExpira em 1 hora.'
            )
        elif recovery_method == 'sms':
            self.sms_service.send(
                phone=user['phone'],
                message=f'Codigo de recuperacao: {token[:6].upper()}'
            )
        
        # Audit log
        self.audit_log.log(
            'account_recovery_initiated',
            user_id=user['id'],
            method=recovery_method
        )
        
        # Set cooldown
        self._set_cooldown(user['id'])
        
        return {
            'message': 'Se uma conta existir com este '
                      'identificador, um link de recuperacao '
                      'foi enviado.'
        }
    
    def complete_recovery(self, token: str, 
                         new_credentials: dict) -> dict:
        """Complete account recovery."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        record = self.db.query("""
            SELECT * FROM recovery_tokens 
            WHERE token_hash = %s 
            AND used = FALSE
            AND expires_at > NOW()
        """, (token_hash,))
        
        if not record:
            return {'error': 'Invalid or expired recovery token'}
        
        user_id = record[0]['user_id']
        
        # Update user credentials
        if 'password' in new_credentials:
            password_hash = self.hash_password(new_credentials['password'])
            self.db.execute("""
                UPDATE users SET password_hash = %s WHERE id = %s
            """, (password_hash, user_id))
        
        # Mark token as used
        self.db.execute("""
            UPDATE recovery_tokens SET used = TRUE WHERE token_hash = %s
        """, (token_hash,))
        
        # Invalidate all existing sessions
        self.db.execute("""
            DELETE FROM sessions WHERE user_id = %s
        """, (user_id,))
        
        # Audit log
        self.audit_log.log(
            'account_recovery_completed',
            user_id=user_id
        )
        
        return {'success': True, 'message': 'Conta recuperada'}
```

### 7.16.4 Magic links para consentimento de dados

Em sistemas que precisam de consentimento explícito do usuário (LGPD, GDPR), magic links podem ser usados para validar o consentimento:

```python
# Consentimento via magic link
class DataConsentService:
    """Data consent management via magic links."""
    
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service
    
    def request_consent(self, user_id: str, 
                       data_categories: list) -> dict:
        """Request data processing consent."""
        user = self.db.query(
            "SELECT email FROM users WHERE id = %s",
            (user_id,)
        )
        
        if not user:
            return {'error': 'User not found'}
        
        # Generate consent token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        self.db.execute("""
            INSERT INTO consent_tokens 
            (user_id, token_hash, data_categories, expires_at)
            VALUES (%s, %s, %s, NOW() + INTERVAL '30 days')
        """, (user_id, token_hash, json.dumps(data_categories)))
        
        # Send consent email
        consent_url = f"https://exemplo.com/consent?token={token}"
        
        categories_text = ', '.join(data_categories)
        
        self.email_service.send(
            to=user[0]['email'],
            subject='Consentimento para processamento de dados',
            body=f'''
            Precisamos do seu consentimento para processar '
            dados categorias: {categories_text}
            
            Clique no link abaixo para dar seu consentimento:
            {consent_url}
            
            Este link expira em 30 dias.
            '''
        )
        
        return {'success': True, 'message': 'Consent request sent'}
    
    def grant_consent(self, token: str) -> dict:
        """Grant consent via magic link."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        record = self.db.query("""
            SELECT * FROM consent_tokens 
            WHERE token_hash = %s 
            AND granted IS NULL
            AND expires_at > NOW()
        """, (token_hash,))
        
        if not record:
            return {'error': 'Invalid or expired token'}
        
        # Record consent
        self.db.execute("""
            UPDATE consent_tokens 
            SET granted = TRUE, granted_at = NOW()
            WHERE token_hash = %s
        """, (token_hash,))
        
        # Update user consent status
        self.db.execute("""
            UPDATE users 
            SET data_consent = TRUE, 
                data_consent_at = NOW()
            WHERE id = %s
        """, (record[0]['user_id'],))
        
        return {
            'success': True,
            'message': 'Consentimento registrado',
            'categories': json.loads(record[0]['data_categories'])
        }
    
    def revoke_consent(self, user_id: str) -> dict:
        """Revoke data processing consent."""
        self.db.execute("""
            UPDATE users 
            SET data_consent = FALSE, 
                data_consent_revoked_at = NOW()
            WHERE id = %s
        """, (user_id,))
        
        # Invalidate all consent tokens
        self.db.execute("""
            UPDATE consent_tokens 
            SET granted = FALSE
            WHERE user_id = %s AND granted = TRUE
        """, (user_id,))
        
        return {'success': True, 'message': 'Consentimento revogado'}
```

---

*No próximo capítulo: WebAuthn e FIDO2 — o padrão que transforma dispositivos físicos e biometria em autenticadores phishing-resistant.*
---

*[Capítulo anterior: 06 — Sso](06-sso.md)*
*[Próximo capítulo: 08 — Webauthn Fido2](08-webauthn-fido2.md)*
