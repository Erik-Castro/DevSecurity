# Capítulo 16 — Padrões Seguros de Implementação

## Introdução

Implementar autenticação e autorização de forma segura é notoriamente difícil. A maioria dos incidentes de segurança não resulta de criptografia quebrada ou de algoritmos vulneráveis — resulta de implementações incorretas, fluxos mal projetados, e decisões de design que parecem inofensivas mas criam vetores de ataque devastadores. O caso Misantropi4 contra o IDAP ilustra isso com clareza: o sistema governamental brasileiro não falhou por falta de controles de acesso, mas por controles de acesso implementados de forma insegura.

Este capítulo é um guia definitivo de padrões seguros para implementação de autenticação, autorização, e controle de acesso. Cada padrão é apresentado com o contexto do problema que resolve, a implementação correta, os anti-patterns associados, e a relação com o caso Misantropi4. Ao final deste capítulo, você terá um catálogo completo de soluções testadas para os problemas mais comuns em sistemas de identidade.

---

## 16.1 Anti-Patterns Críticos em Autenticação

### 16.1.1 O que é um anti-pattern

Um anti-pattern é uma solução que parece funcional mas que introduz problemas graves — frequentemente invisíveis até que um atacante os exploite. Em autenticação, os anti-patterns são particularmente perigosos porque violam invariantes de segurança que os desenvolvedores dão por garantidos.

### 16.1.2 Catálogo de 20 anti-patterns

O catálogo a seguir documenta os anti-patterns mais comuns e perigosos em sistemas de autenticação. Cada um é classificado por severidade (Crítica, Alta, Média) e inclui o padrão seguro correspondente.

**Anti-Pattern 1: Senhas em texto plano no banco de dados**

```
ANTI-PATTERN (Severidade: Cria)
// Armazenamento incorreto
INSERT INTO users (email, password) VALUES ('user@example.com', 'minha_senha_123');

// OU pior — MD5 sem sal
INSERT INTO users (email, password_hash) VALUES ('user@example.com', MD5('minha_senha_123'));
```

```
PADRÃO SEGURO
// Argon2id com sal único por usuário
const hash = await argon2.hash(password, {
  type: argon2.argon2id,
  memoryCost: 65536,
  timeCost: 3,
  parallelism: 4,
  salt: crypto.randomBytes(16)
});
await db.query('INSERT INTO users (email, password_hash) VALUES ($1, $2)', [email, hash]);
```

**Anti-Pattern 2: Mensagens de erro que revelam existência de usuário**

```
ANTI-PATTERN (Severidade: Alta)
if (!user) {
  throw new Error('Usuário não encontrado');
}
if (!await verifyPassword(password, user.hash)) {
  throw new Error('Senha incorreta');
}
// Atacante pode diferenciar: "não existe" vs "senha errada"
```

```
PADRÃO SEGURO
if (!user || !await verifyPassword(password, user.hash)) {
  throw new AuthError('Credenciais inválidas');
  // Mesma mensagem para ambos os casos
}
```

**Anti-PATTERN 3: Tokens JWT sem data de expiração**

```
ANTI-PATTERN (Severidade: Crítica)
const token = jwt.sign({ userId: user.id }, SECRET_KEY);
// Token válido para sempre — serourou, Comprometeu para sempre
```

```
PADRÃO SEGURO
const token = jwt.sign(
  { userId: user.id, type: 'access' },
  SECRET_KEY,
  { expiresIn: '15m', issuer: 'meu-app', audience: 'api' }
);
```

**Anti-PATTERN 4: Senhas fracas sem política de força**

```
ANTI-PATTERN (Severidade: Alta)
// Aceita qualquer senha, incluindo "123456" e "password"
await createUser({ email, password: req.body.password });
```

```
PADRÃO SEGURO
const passwordPolicy = {
  minLength: 12,
  requireUppercase: true,
  requireLowercase: true,
  requireNumbers: true,
  requireSpecialChars: true,
  maxAge: 90,  // dias
  historyCount: 12  // não reutilizar últimas 12 senhas
};

function validatePassword(password, policy) {
  const errors = [];
  if (password.length < policy.minLength) {
    errors.push(`Mínimo de ${policy.minLength} caracteres`);
  }
  if (policy.requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('Requer ao menos uma letra maiúscula');
  }
  if (policy.requireLowercase && !/[a-z]/.test(password)) {
    errors.push('Requer ao menos uma letra minúscula');
  }
  if (policy.requireNumbers && !/[0-9]/.test(password)) {
    errors.push('Requer ao menos um número');
  }
  if (policy.requireSpecialChars && !/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
    errors.push('Requer ao menos um caractere especial');
  }
  return errors;
}
```

**Anti-PATTERN 5: Rate limiting inexistente no login**

```
ANTI-PATTERN (Severidade: Crítica)
// Sem limite de tentativas — brute force é trivial
app.post('/login', async (req, res) => {
  const user = await findUser(req.body.email);
  if (user && await checkPassword(req.body.password, user.hash)) {
    res.json({ token: generateToken(user) });
  } else {
    res.status(401).json({ error: 'Credenciais inválidas' });
  }
});
```

```
PADRÃO SEGURO
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutos
  max: 5,  // 5 tentativas por IP
  message: 'Muitas tentativas. Tente novamente em 15 minutos.',
  standardHeaders: true,
  legacyHeaders: false,
  handler: (req, res) => {
    logger.warn('Rate limit exceeded', { ip: req.ip, email: req.body.email });
    res.status(429).json({ error: 'Muitas tentativas de login' });
  }
});

// Rate limit adicional por email (protege contra distribuído)
const emailLimiter = new Map();

function checkEmailRateLimit(email) {
  const key = email.toLowerCase();
  const now = Date.now();
  const attempts = emailLimiter.get(key) || [];
  const recentAttempts = attempts.filter(t => now - t < 15 * 60 * 1000);
  if (recentAttempts.length >= 5) {
    return false;
  }
  recentAttempts.push(now);
  emailLimiter.set(key, recentAttempts);
  return true;
}
```

**Anti-PATTERN 6: Sessões que não expiram**

```
ANTI-PATTERN (Severidade: Alta)
// Cookie de sessão sem expiração
res.cookie('session', sessionId, {
  httpOnly: true,
  secure: true
  // Sem expires ou maxAge — dura para sempre
});
```

```
PADRÃO SEGURO
res.cookie('session', sessionId, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 30 * 60 * 1000,  // 30 minutos
  path: '/'
});

// E invalidar no servidor após inatividade
await db.query(
  'UPDATE sessions SET invalidated = true WHERE user_id = $1 AND last_active < NOW() - INTERVAL \'30 minutes\'',
  [userId]
);
```

**Anti-PATTERN 7: Credentials compartilhadas entre ambientes**

```
ANTI-PATTERN (Severidade: Crítica)
// Mesma chave JWT em dev, staging, e produção
JWT_SECRET=minha_chave_secreta_123
// Se dev é comprometido, produção também está
```

```
PADRÃO SEGURO
// Ambiente de desenvolvimento
JWT_SECRET_DEV=dev-only-secret-not-for-production

// Staging
JWT_SECRET_STAGING=staging-only-secret-not-for-production

// Produção — gerada aleatoriamente, armazenada em vault
JWT_SECRET_PROD=$(openssl rand -hex 32)
# Em produção, usar HashiCorp Vault ou AWS Secrets Manager
```

**Anti-PATTERN 8: Session fixation**

```
ANTI-PATTERN (Severidade: Alta)
// ID de sessão não muda após login
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (user) {
    // Reutiliza o mesmo session ID — atacante pode fixation
    req.session.userId = user.id;
    res.redirect('/dashboard');
  }
});
```

```
PADRÃO SEGURO
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (user) {
    // Regenerar sessão após autenticação bem-sucedida
    req.session.regenerate((err) => {
      if (err) {
        logger.error('Session regeneration failed', { error: err.message });
        return res.status(500).json({ error: 'Erro interno' });
      }
      req.session.userId = user.id;
      req.session.loginTime = Date.now();
      res.redirect('/dashboard');
    });
  }
});
```

**Anti-PATTERN 9: Token de reset de senha com duração longa**

```
ANTI-PATTERN (Severidade: Alta)
// Token válido por 7 dias
const resetToken = crypto.randomBytes(32).toString('hex');
await db.query(
  'INSERT INTO password_resets (user_id, token, expires_at) VALUES ($1, $2, $3)',
  [user.id, resetToken, new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)]
);
```

```
PADRÃO SEGURO
// Token válido por 15 minutos, uso único
const resetToken = crypto.randomBytes(32).toString('hex');
const hashedToken = crypto.createHash('sha256').update(resetToken).digest('hex');

await db.query(
  'INSERT INTO password_resets (user_id, token_hash, expires_at, used) VALUES ($1, $2, $3, false)',
  [user.id, hashedToken, new Date(Date.now() + 15 * 60 * 1000)]
);

// Após uso, marcar como usado
await db.query(
  'UPDATE password_resets SET used = true WHERE token_hash = $1 AND used = false',
  [hashedToken]
);
```

**Anti-Pattern 10: Autorização baseada apenas no client-side**

```
ANTI-PATTERN (Severidade: Crítica)
// Permissões verificadas apenas no frontend
function isAdmin() {
  return localStorage.getItem('userRole') === 'admin';
}

// Atacante pode alterar localStorage — acesso total
```

```
PADRÃO SEGURO
// Verificação server-side obrigatória
async function requireAdmin(req, res, next) {
  const user = await getUserFromSession(req);
  if (!user || user.role !== 'admin') {
    return res.status(403).json({ error: 'Acesso negado' });
  }
  next();
}

// Front-end pode mostrar/esconder UI, mas NUNCA confie nele
app.get('/admin/users', requireAdmin, listUsers);
```

**Anti-Pattern 11: Secrets hardcoded no código**

```
ANTI-PATTERN (Severidade: Crítica)
const API_KEY = 'sk-1234567890abcdef';
const DB_PASSWORD = 'super_secret_123';
const JWT_SECRET = 'my_jwt_secret_key';
// Commitados no repositório — git history exposta
```

```
PADRÃO SEGURO
// Usar variáveis de ambiente + vault
const API_KEY = process.env.API_KEY;  // Nunca log, nunca expor
const DB_PASSWORD = await vault.getSecret('db/password');

// Em CI/CD, usar OIDC ou secrets management
// GitHub Actions:
// - secrets: GitHub Encrypted Secrets
// - OIDC: short-lived tokens via workload identity
```

**Anti-Pattern 12: Cookie sem flags de segurança**

```
ANTI-PATTERN (Severidade: Alta)
res.cookie('session', sessionId);  // Sem httpOnly, sem secure, sem sameSite
// Vulnerável a XSS, MITM, CSRF
```

```
PADRÃO SEGURO
res.cookie('session', sessionId, {
  httpOnly: true,     // Impede acesso via JavaScript
  secure: true,       // Apenas HTTPS
  sameSite: 'strict', // Previne CSRF
  path: '/',          // Escopo mínimo
  maxAge: 1800000     // 30 minutos
});
```

**Anti-PATTERN 13: Logging de credenciais**

```
ANTI-PATTERN (Severidade: Alta)
logger.info('Login attempt', {
  email: req.body.email,
  password: req.body.password,  // LOG DA SENHA!
  ip: req.ip
});
```

```
PADRÃO SEGURO
logger.info('Login attempt', {
  email: req.body.email,
  ip: req.ip,
  userAgent: req.headers['user-agent'],
  timestamp: new Date().toISOString()
  // NUNCA logar senha, token, ou credenciais
});
```

**Anti-PATTERN 14: Tokens de refresh armazenados no localStorage**

```
ANTI-PATTERN (Severidade: Crítica)
localStorage.setItem('refreshToken', refreshToken);
// localStorage é acessível via JavaScript — XSS rouba o token
```

```
PADRÃO SEGURO
// Refresh token em cookie HttpOnly,Secure, SameSite=strict
res.cookie('refreshToken', refreshToken, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 7 * 24 * 60 * 60 * 1000,  // 7 dias
  path: '/auth/refresh'  // Escopo mínimo
});

// Access token em memory (não persistido)
let accessToken = null;  // Variável em memória, não em storage
```

**Anti-Pattern 15: Autorização por obscuridade**

```
ANTI-PATTERN (Severidade: Alta)
// "Seguro" porque ninguém sabe a URL
app.get('/api/a1b2c3d4/users', (req, res) => {
  // Endpoint secreto — qualquer um com a URL acessa
});
```

```
PADRÃO SEGURO
// Autorização explícita, não obscuridade
app.get('/api/v1/users', requireAuth, requireRole('admin'), listUsers);
// A segurança vem da autorização, não da URL ser difícil de adivinhar
```

**Anti-Pattern 16: Falta de lockout após múltiplas falhas**

```
ANTI-PATTERN (Severidade: Alta)
// Usuário pode tentar infinitamente
// Ataque de brute force funciona eventualmente
```

```
PADRÃO SEGURO
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_DURATION = 30 * 60 * 1000;  // 30 minutos

async function handleFailedLogin(userId) {
  const attempts = await db.query(
    'SELECT COUNT(*) as count FROM login_attempts WHERE user_id = $1 AND created_at > NOW() - INTERVAL \'15 minutes\'',
    [userId]
  );

  if (parseInt(attempts.rows[0].count) >= MAX_FAILED_ATTEMPTS) {
    await db.query(
      'UPDATE users SET locked_until = $1 WHERE id = $2',
      [new Date(Date.now() + LOCKOUT_DURATION), userId]
    );
    logger.warn('Account locked', { userId, reason: 'Too many failed attempts' });
    await sendLockoutNotification(userId);
  }
}
```

**Anti-Pattern 17: MFA como opção, não obrigação**

```
ANTI-PATTERN (Severidade: Média)
// MFA é opcional — maioria dos usuários não ativa
if (user.wantsMFA) {
  return verifyMFA(req.body.mfaCode);
}
return loginSuccess(user);
```

```
PADRÃO SEGURO
// MFA obrigatório para contas privilegiadas
if (user.role === 'admin' || user.role === 'operator') {
  if (!user.mfaEnabled) {
    return res.status(403).json({
      error: 'MFA obrigatório para esta conta',
      setupUrl: '/auth/mfa/setup'
    });
  }
  return verifyMFA(user, req.body.mfaCode);
}
```

**Anti-Pattern 18: Confiança cega no header X-Forwarded-For**

```
ANTI-PATTERN (Severidade: Alta)
const clientIP = req.headers['x-forwarded-for'];  // Fácil de forjar
// Rate limiting baseado em IP spoofável
```

```
PADRÃO SEGURO
// Configurar proxy de confiança no framework
const app = express();
app.set('trust proxy', 1);  // Confiar em 1 proxy à frente

// Usar IP real do socket quando possível
const clientIP = req.socket.remoteAddress;

// Rate limit combina IP + outras heurísticas
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  keyGenerator: (req) => {
    return `${req.ip}:${req.headers['user-agent']}`;
  }
});
```

**Anti-Pattern 19: Falta de invalidação de token no logout**

```
ANTI-PATTERN (Severidade: Alta)
app.post('/logout', (req, res) => {
  // Remove cookie mas token JWT continua válido
  res.clearCookie('session');
  res.json({ message: 'Logout realizado' });
  // Token ainda funciona por horas
});
```

```
PADRÃO SEGURO
app.post('/logout', async (req, res) => {
  const sessionId = req.cookies.session;

  // Invalidar sessão no banco de dados
  await db.query(
    'UPDATE sessions SET invalidated = true, invalidated_at = NOW() WHERE id = $1',
    [sessionId]
  );

  // Adicionar token à blacklist (se usando JWT)
  const token = req.headers.authorization?.split(' ')[1];
  if (token) {
    const decoded = jwt.decode(token);
    await redis.setex(`blacklist:${token}`, decoded.exp - Math.floor(Date.now() / 1000), '1');
  }

  // Limpar cookie
  res.clearCookie('session', { path: '/' });
  res.json({ message: 'Logout realizado' });
});
```

**Anti-Pattern 20: Falta de audit trail**

```
ANTI-PATTERN (Severidade: Média)
// Nenhum log de quem acessou o quê
// Incapaz de detectar comportamento anômalo
// Impossível de auditar em caso de incidente
```

```
PADRÃO SEGURO
async function auditLog(event) {
  await db.query(
    `INSERT INTO audit_logs (user_id, action, resource, resource_id, ip, user_agent, timestamp, metadata)
     VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7)`,
    [
      event.userId,
      event.action,
      event.resource,
      event.resourceId,
      event.ip,
      event.userAgent,
      JSON.stringify(event.metadata)
    ]
  );
}

// Exemplo de uso
await auditLog({
  userId: req.user.id,
  action: 'user.login',
  resource: 'session',
  resourceId: sessionId,
  ip: req.ip,
  userAgent: req.headers['user-agent'],
  metadata: { method: 'password+mfa' }
});
```

---

## 16.2 Padrões de Autenticação Segura

### 16.2.1 Fluxo de login seguro

Um fluxo de login seguro deve seguir etapas rigorosas para proteger tanto o servidor quanto o usuário. O fluxo completo inclui:

1. **Recebimento das credenciais**: O servidor recebe email e senha via HTTPS
2. **Rate limiting**: Verificar se o IP ou email excedeu o limite de tentativas
3. **Busca do usuário**: Localizar o usuário pelo email (case-insensitive)
4. **Verificação da senha**: Comparar com Argon2id (nunca MD5, SHA-1, ou SHA-256 simples)
5. **Verificação de lockout**: Checar se a conta está bloqueada
6. **Verificação de MFA**: Se habilitado, solicitar código
7. **Geração de tokens**: Criar access token (curto) e refresh token (longo)
8. **Registro de auditoria**: Logar o evento de login com metadados
9. **Envio de resposta**: Retornar tokens de forma segura

```
// Fluxo completo de login seguro
async function secureLogin(req, res) {
  const { email, password, mfaCode } = req.body;
  const startTime = Date.now();

  // 1. Rate limiting por IP
  if (!checkIPRateLimit(req.ip)) {
    logger.warn('IP rate limited', { ip: req.ip });
    return res.status(429).json({ error: 'Muitas tentativas' });
  }

  // 2. Rate limiting por email
  if (!checkEmailRateLimit(email)) {
    logger.warn('Email rate limited', { email });
    return res.status(429).json({ error: 'Muitas tentativas' });
  }

  // 3. Buscar usuário
  const user = await db.findUserByEmail(email.toLowerCase());
  if (!user) {
    // Tempo constante para prevenir timing attack
    await argon2.hash(password);
    await auditLog({ action: 'login.failed', email, reason: 'user_not_found', ip: req.ip });
    return res.status(401).json({ error: 'Credenciais inválidas' });
  }

  // 4. Verificar lockout
  if (user.locked_until && user.locked_until > new Date()) {
    await auditLog({ action: 'login.failed', userId: user.id, reason: 'account_locked', ip: req.ip });
    return res.status(423).json({ error: 'Conta bloqueada temporariamente' });
  }

  // 5. Verificar senha
  const passwordValid = await argon2.verify(user.password_hash, password);
  if (!passwordValid) {
    await handleFailedLogin(user.id);
    await auditLog({ action: 'login.failed', userId: user.id, reason: 'invalid_password', ip: req.ip });
    return res.status(401).json({ error: 'Credenciais inválidas' });
  }

  // 6. Verificar MFA (se habilitado)
  if (user.mfa_enabled) {
    if (!mfaCode) {
      return res.status(200).json({ requiresMFA: true });
    }
    const mfaValid = verifyTOTP(user.mfa_secret, mfaCode);
    if (!mfaValid) {
      await auditLog({ action: 'login.failed', userId: user.id, reason: 'invalid_mfa', ip: req.ip });
      return res.status(401).json({ error: 'Código MFA inválido' });
    }
  }

  // 7. Resetar contador de falhas
  await resetFailedAttempts(user.id);

  // 8. Criar sessão e tokens
  const session = await createSession(user.id, req);
  const accessToken = generateAccessToken(user, session.id);
  const refreshToken = generateRefreshToken(user, session.id);

  // 9. Audit log de sucesso
  await auditLog({
    action: 'login.success',
    userId: user.id,
    ip: req.ip,
    userAgent: req.headers['user-agent'],
    duration: Date.now() - startTime
  });

  // 10. Enviar resposta
  res.cookie('refreshToken', refreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
    path: '/auth/refresh'
  });

  return res.json({
    accessToken,
    expiresIn: 900,
    user: { id: user.id, email: user.email, role: user.role }
  });
}
```

### 16.2.2 Gerenciamento de sessões

O gerenciamento de sessões é um dos aspectos mais críticos e frequentemente mal implementados de qualquer sistema de autenticação. Uma sessão segura requer consideração cuidadosa de armazenamento, expiração, invalidação, e renovação.

**Princípios fundamentais:**

1. **Identificadores de sessão devem ser aleatórios e imprevisíveis**: Use `crypto.randomBytes(32)` ou equivalente. Nunca use UUIDs v4 (previsíveis) ou timestamps
2. **Armazenamento seguro**: Cookies HttpOnly+Secure+SameSite para web. Tokens em memória para SPAs
3. **Expiração dupla**: Tempo absoluto (máximo 24h) + tempo de inatividade (máximo 30min)
4. **Invalidação completa**: Logout deve invalidar a sessão no servidor, não apenas no client
5. **Rotação de sessões**: Regenerar ID de sessão após login e após operações sensíveis

```
class SessionManager {
  constructor(db, redis) {
    this.db = db;
    this.redis = redis;
    this.MAX_ABSOLUTE_AGE = 24 * 60 * 60 * 1000;  // 24 horas
    this.MAX_INACTIVE_AGE = 30 * 60 * 1000;  // 30 minutos
  }

  async create(userId, req) {
    const sessionId = crypto.randomBytes(32).toString('hex');
    const sessionData = {
      userId,
      ip: req.ip,
      userAgent: req.headers['user-agent'],
      createdAt: Date.now(),
      lastActiveAt: Date.now(),
      rotated: false
    };

    // Armazenar em Redis com TTL
    await this.redis.setex(
      `session:${sessionId}`,
      this.MAX_ABSOLUTE_AGE / 1000,
      JSON.stringify(sessionData)
    );

    // Persistir no banco para auditoria
    await this.db.query(
      'INSERT INTO sessions (id, user_id, ip, user_agent, created_at) VALUES ($1, $2, $3, $4, NOW())',
      [sessionId, userId, req.ip, req.headers['user-agent']]
    );

    return sessionId;
  }

  async validate(sessionId) {
    const data = await this.redis.get(`session:${sessionId}`);
    if (!data) return null;

    const session = JSON.parse(data);
    const now = Date.now();

    // Verificar idade absoluta
    if (now - session.createdAt > this.MAX_ABSOLUTE_AGE) {
      await this.destroy(sessionId);
      return null;
    }

    // Verificar inatividade
    if (now - session.lastActiveAt > this.MAX_INACTIVE_AGE) {
      await this.destroy(sessionId);
      return null;
    }

    // Atualizar último acesso
    session.lastActiveAt = now;
    await this.redis.setex(
      `session:${sessionId}`,
      this.MAX_ABSOLUTE_AGE / 1000,
      JSON.stringify(session)
    );

    return session;
  }

  async destroy(sessionId) {
    await this.redis.del(`session:${sessionId}`);
    await this.db.query(
      'UPDATE sessions SET invalidated = true, invalidated_at = NOW() WHERE id = $1',
      [sessionId]
    );
  }

  async rotate(sessionId, req) {
    const session = await this.validate(sessionId);
    if (!session) return null;

    await this.destroy(sessionId);
    return this.create(session.userId, req);
  }

  async destroyAllForUser(userId) {
    // Invalidar todas as sessões de um usuário (ex: após mudança de senha)
    const sessions = await this.db.query(
      'SELECT id FROM sessions WHERE user_id = $1 AND invalidated = false',
      [userId]
    );

    for (const row of sessions.rows) {
      await this.destroy(row.id);
    }
  }
}
```

### 16.2.3 Fluxo de refresh token seguro

O refresh token permite renovar access tokens sem que o usuário precise fazer login novamente. O fluxo deve ser seguro contra roubo de tokens e deve suportar rotação.

```
// Fluxo de refresh token com rotação
async function refreshAccessToken(req, res) {
  const refreshToken = req.cookies.refreshToken;

  if (!refreshToken) {
    return res.status(401).json({ error: 'Refresh token não fornecido' });
  }

  // 1. Verificar se o token está na blacklist
  const isBlacklisted = await redis.get(`blacklist:${refreshToken}`);
  if (isBlacklisted) {
    // Possível roubo de token — invalidar todas as sessões do usuário
    const decoded = jwt.decode(refreshToken);
    await sessionManager.destroyAllForUser(decoded.userId);
    await auditLog({
      action: 'refresh_token.reuse_detected',
      userId: decoded.userId,
      ip: req.ip
    });
    return res.status(401).json({ error: 'Token comprometido' });
  }

  // 2. Verificar validade do token
  let decoded;
  try {
    decoded = jwt.verify(refreshToken, REFRESH_SECRET, {
      issuer: 'meu-app',
      audience: 'api'
    });
  } catch (err) {
    return res.status(401).json({ error: 'Token inválido' });
  }

  // 3. Verificar se a sessão ainda é válida
  const session = await sessionManager.validate(decoded.sessionId);
  if (!session) {
    return res.status(401).json({ error: 'Sessão expirada' });
  }

  // 4. Rotação: invalidar o refresh token atual
  await redis.setex(`blacklist:${refreshToken}`, 7 * 24 * 60 * 60, '1');

  // 5. Gerar novos tokens
  const user = await db.findUserById(decoded.userId);
  const newAccessToken = generateAccessToken(user, decoded.sessionId);
  const newRefreshToken = generateRefreshToken(user, decoded.sessionId);

  // 6. Audit log
  await auditLog({
    action: 'token.refreshed',
    userId: user.id,
    ip: req.ip,
    sessionId: decoded.sessionId
  });

  // 7. Enviar novos tokens
  res.cookie('refreshToken', newRefreshToken, {
    httpOnly: true,
    secure: true,
    sameSite: 'strict',
    maxAge: 7 * 24 * 60 * 60 * 1000,
    path: '/auth/refresh'
  });

  return res.json({
    accessToken: newAccessToken,
    expiresIn: 900
  });
}
```

---

## 16.3 Padrões de Autorização Segura

### 16.3.1 Princípio do menor privilege (Least Privilege)

O princípio do menor privilege é o fundamento da autorização segura: cada entidade (usuário, serviço, processo) deve ter apenas as permissões mínimas necessárias para realizar sua função. No contexto do caso Misantropi4, se os operadores do IDAP tivessem apenas as permissões necessárias para sua função específica, o dano teria sido significativamente menor.

**Implementação em Python com decorator:**

```python
from functools import wraps
from enum import Enum

class Permission(Enum):
    READ_OWN_DATA = "read:own_data"
    READ_ALL_DATA = "read:all_data"
    WRITE_OWN_DATA = "write:own_data"
    WRITE_ALL_DATA = "write:all_data"
    DELETE_USER = "delete:user"
    MANAGE_SYSTEM = "manage:system"
    VIEW_AUDIT_LOGS = "view:audit_logs"

# Mapeamento de roles para permissões
ROLE_PERMISSIONS = {
    "viewer": [Permission.READ_OWN_DATA],
    "operator": [Permission.READ_OWN_DATA, Permission.WRITE_OWN_DATA],
    "admin": [
        Permission.READ_ALL_DATA,
        Permission.WRITE_ALL_DATA,
        Permission.DELETE_USER,
        Permission.VIEW_AUDIT_LOGS
    ],
    "superadmin": [p for p in Permission]  # Todas as permissões
}

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            user = request.state.user
            if not user:
                return {"error": "Não autenticado"}, 401

            user_permissions = ROLE_PERMISSIONS.get(user.role, [])
            if permission not in user_permissions:
                await audit_log(
                    user_id=user.id,
                    action="authorization.denied",
                    resource=permission.value,
                    ip=request.client.host
                )
                return {"error": "Acesso negado"}, 403

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Uso
@app.get("/api/users/{user_id}")
@require_permission(Permission.READ_ALL_DATA)
async def get_user(request, user_id: int):
    user = await db.get_user(user_id)
    return user
```

### 16.3.2 Deny-by-default

Deny-by-default é o padrão mais importante em autorização: todas as ações são negadas por padrão, e apenas as permissões explicitamente concedidas são permitidas. Isso inverte a lógica tradicional (onde tudo é permitido menos o que é bloqueado) e cria uma postura de segurança muito mais forte.

```
// Padrão deny-by-default em Go
type AuthorizationEngine struct {
    policies map[string][]Policy
}

type Policy struct {
    Effect    string   // "allow" ou "deny"
    Resource  string
    Action    string
    Conditions []Condition
}

func (ae *AuthorizationEngine) IsAllowed(user User, resource string, action string) bool {
    // DENY por padrão — nenhuma política = acesso negado
    effectivePolicies := ae.policies[user.Role]

    // Verificar deny policies primeiro (sempre vence)
    for _, policy := range effectivePolicies {
        if policy.Effect == "deny" &&
           matchResource(policy.Resource, resource) &&
           matchAction(policy.Action, action) {
            return false
        }
    }

    // Verificar allow policies
    for _, policy := range effectivePolicies {
        if policy.Effect == "allow" &&
           matchResource(policy.Resource, resource) &&
           matchAction(policy.Action, action) &&
           checkConditions(policy.Conditions, user) {
            return true
        }
    }

    // DEFAULT: Negado
    return false
}

// Exemplo de uso
engine := NewAuthorizationEngine()

// Política explícita necessária
engine.AddPolicy("operator", Policy{
    Effect:   "allow",
    Resource: "document",
    Action:   "read",
    Conditions: []Condition{
        {Field: "owner", Operator: "equals", Value: "self"},
    },
})

// Negado por padrão — sem política = sem acesso
allowed := engine.IsAllowed(operatorUser, "document", "delete")  // false
```

### 16.3.3 Verificação de autorização em cada ponto de acesso

A autorização deve ser verificada em cada camada da aplicação, não apenas no endpoint da API. Isso inclui camadas de serviço, acesso a banco de dados, e chamadas entre microserviços.

```
// Padrão: Authorization middleware chain
class AuthorizationPipeline {
  constructor() {
    this.checks = [];
  }

  addCheck(checkFn) {
    this.checks.push(checkFn);
    return this;
  }

  async evaluate(context) {
    for (const check of this.checks) {
      const result = await check(context);
      if (!result.allowed) {
        return { allowed: false, reason: result.reason };
      }
    }
    return { allowed: true };
  }
}

// Uso: pipeline de autorização
const authzPipeline = new AuthorizationPipeline()
  .addCheck(checkAuthentication)      // 1. Está autenticado?
  .addCheck(checkRole)                // 2. Tem a role necessária?
  .addCheck(checkResourceOwnership)   // 3. É dono do recurso?
  .addCheck(checkTimeConstraint)      // 4. Está no horário permitido?
  .addCheck(checkIPWhitelist);        // 5. IP permitido?

app.get('/api/sensitive-data', async (req, res) => {
  const context = {
    user: req.user,
    resource: 'sensitive-data',
    action: 'read',
    ip: req.ip,
    timestamp: new Date()
  };

  const result = await authzPipeline.evaluate(context);
  if (!result.allowed) {
    return res.status(403).json({ error: result.reason });
  }

  const data = await getSensitiveData();
  res.json(data);
});
```

### 16.3.4 Separation of Duty (SoD)

Separation of Duty é um controle de segurança que requer que múltiplas pessoas ou roles sejam necessárias para completar uma operação crítica. Isso previne que um único usuário comprometido possa causar danos significativos.

```
// Exemplo: transferência bancária requer 2 aprovações
class SeparationOfDuty {
  constructor(db) {
    this.db = db;
  }

  async requestApproval(operationId, approverId, approverRole) {
    const operation = await this.db.getOperation(operationId);
    if (!operation) {
      throw new Error('Operação não encontrada');
    }

    // Verificar se o aprovador é diferente do solicitante
    if (operation.requestedBy === approverId) {
      throw new Error('Separation of Duty: aprovador não pode ser o solicitante');
    }

    // Verificar se o aprovador tem a role necessária
    if (!operation.requiredRoles.includes(approverRole)) {
      throw new Error('Role insuficiente para aprovação');
    }

    // Registrar aprovação
    await this.db.addApproval(operationId, approverId, approverRole);

    // Verificar se todas as aprovações foram coletadas
    const approvals = await this.db.getApprovals(operationId);
    if (approvals.length >= operation.requiredApprovals) {
      await this.db.executeOperation(operationId);
      await this.auditLog('operation.executed', operationId, approvals);
    }
  }
}

// Uso
const sod = new SeparationOfDuty(db);

// Solicitante inicia a transferência
const operation = await sod.createOperation({
  type: 'transfer',
  amount: 50000,
  requestedBy: 'operator-123',
  requiredApprovals: 2,
  requiredRoles: ['manager', 'compliance']
});

// Dois aprovadores diferentes devem aprovar
await sod.requestApproval(operation.id, 'manager-456', 'manager');
await sod.requestApproval(operation.id, 'compliance-789', 'compliance');
// Só então a transferência é executada
```

---

## 16.4 Autenticação Segura de APIs

### 16.4.1 Padrões de autenticação para APIs

As APIs modernas requerem autenticação robusta que suporte múltiplos clientes (web, mobile, serviços). Os padrões incluem:

**Bearer Tokens (JWT):**

```
// Padrão: Bearer token no header Authorization
GET /api/resource HTTP/1.1
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

// Validação no servidor
function authenticateBearer(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Token não fornecido' });
  }

  const token = authHeader.substring(7);
  try {
    const decoded = jwt.verify(token, PUBLIC_KEY, {
      algorithms: ['RS256'],
      issuer: 'auth.example.com',
      audience: 'api.example.com'
    });

    req.user = decoded;
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token expirado', code: 'TOKEN_EXPIRED' });
    }
    return res.status(401).json({ error: 'Token inválido' });
  }
}
```

**API Keys (para serviços machine-to-machine):**

```
// Padrão: API key em header customizado ou query parameter
GET /api/data HTTP/1.1
X-API-Key: ak_live_abc123def456...

// Validação com hash no banco
async function authenticateAPIKey(req, res, next) {
  const apiKey = req.headers['x-api-key'];
  if (!apiKey) {
    return res.status(401).json({ error: 'API key não fornecida' });
  }

  // Hash da API key para lookup (nunca armazenar em texto plano)
  const keyHash = crypto.createHash('sha256').update(apiKey).digest('hex');
  const keyRecord = await db.findAPIKey(keyHash);

  if (!keyRecord || keyRecord.revoked) {
    return res.status(401).json({ error: 'API key inválida' });
  }

  // Verificar escopo
  const requiredScope = getRequiredScope(req.method, req.path);
  if (!keyRecord.scopes.includes(requiredScope)) {
    return res.status(403).json({ error: 'Escopo insuficiente' });
  }

  // Verificar rate limit da API key
  if (!checkAPIKeyRateLimit(keyRecord.id, keyRecord.rateLimit)) {
    return res.status(429).json({ error: 'Rate limit excedido' });
  }

  req.apiKey = keyRecord;
  next();
}
```

**OAuth 2.0 Client Credentials (serviço para serviço):**

```
// Fluxo Client Credentials
async function getServiceToken() {
  const response = await fetch('https://auth.example.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: process.env.SERVICE_CLIENT_ID,
      client_secret: process.env.SERVICE_CLIENT_SECRET,
      scope: 'read:data write:data'
    })
  });

  const data = await response.json();
  // data.access_token — usar em chamadas subsequentes
  return data.access_token;
}
```

### 16.4.2 Validação de tokens em microserviços

Em arquiteturas de microserviços, a validação de tokens deve ser distribuída e eficiente. Cada microserviço deve ser capaz de validar tokens sem chamar o servidor de autorização central.

```
// Padrão: Validação local com JWKS
class TokenValidator {
  constructor(jwksUri, options = {}) {
    this.jwksUri = jwksUri;
    this.cache = new Map();
    this.cacheTTL = options.cacheTTL || 600000;  // 10 minutos
  }

  async getSigningKey(kid) {
    const cached = this.cache.get(kid);
    if (cached && Date.now() - cached.fetchedAt < this.cacheTTL) {
      return cached.key;
    }

    const response = await fetch(this.jwksUri);
    const jwks = await response.json();
    const key = jwks.keys.find(k => k.kid === kid);

    if (!key) {
      throw new Error(`Key not found for kid: ${kid}`);
    }

    const publicKey = jwt.decode(key);

    this.cache.set(kid, {
      key: publicKey,
      fetchedAt: Date.now()
    });

    return publicKey;
  }

  async validate(token) {
    const decoded = jwt.decode(token, { complete: true });
    if (!decoded) {
      throw new Error('Invalid token format');
    }

    const publicKey = await this.getSigningKey(decoded.header.kid);

    return jwt.verify(token, publicKey, {
      algorithms: ['RS256', 'ES256'],
      issuer: process.env.AUTH_ISSUER,
      audience: process.env.API_AUDIENCE
    });
  }
}

// Middleware de validação
function authMiddleware(validator) {
  return async (req, res, next) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
      return res.status(401).json({ error: 'Token required' });
    }

    try {
      const payload = await validator.validate(token);
      req.user = payload;
      req.scopes = payload.scope ? payload.scope.split(' ') : [];
      next();
    } catch (err) {
      return res.status(401).json({ error: 'Invalid token' });
    }
  };
}
```

---

## 16.5 Padrões de Rate Limiting

### 16.5.1 Estratégias de rate limiting

O rate limiting é uma defesa essencial contra brute force, credential stuffing, e abuso de APIs. Existem múltiplas estratégias que podem ser combinadas:

**Rate limiting por IP:**

```
class IPRateLimiter {
  constructor(redis, options = {}) {
    this.redis = redis;
    this.windowMs = options.windowMs || 900000;  // 15 minutos
    this.maxRequests = options.maxRequests || 100;
  }

  async checkLimit(ip) {
    const key = `ratelimit:ip:${ip}`;
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Remover entradas antigas
    await this.redis.zremrangebyscore(key, 0, windowStart);

    // Contar requisições na janela atual
    const count = await this.redis.zcard(key);

    if (count >= this.maxRequests) {
      const oldest = await this.redis.zrange(key, 0, 0, 'WITHSCORES');
      const retryAfter = oldest.length > 0
        ? Math.ceil((parseInt(oldest[1]) + this.windowMs - now) / 1000)
        : Math.ceil(this.windowMs / 1000);

      return {
        allowed: false,
        remaining: 0,
        resetAt: now + retryAfter * 1000,
        retryAfter
      };
    }

    // Adicionar requisição atual
    await this.redis.zadd(key, now, `${now}-${crypto.randomBytes(4).toString('hex')}`);
    await this.redis.expire(key, Math.ceil(this.windowMs / 1000));

    return {
      allowed: true,
      remaining: this.maxRequests - count - 1,
      resetAt: now + this.windowMs
    };
  }
}
```

**Rate limiting por usuário (sliding window):**

```
class UserRateLimiter {
  constructor(redis, options = {}) {
    this.redis = redis;
    this.windowMs = options.windowMs || 60000;  // 1 minuto
    this.maxRequests = options.maxRequests || 60;
  }

  async checkLimit(userId, endpoint) {
    const key = `ratelimit:user:${userId}:${endpoint}`;
    const now = Date.now();
    const windowStart = now - this.windowMs;

    // Sliding window log approach
    const pipeline = this.redis.pipeline();
    pipeline.zremrangebyscore(key, 0, windowStart);
    pipeline.zadd(key, now, `${now}`);
    pipeline.zcard(key);
    pipeline.expire(key, Math.ceil(this.windowMs / 1000));

    const results = await pipeline.exec();
    const count = results[2][1];

    if (count > this.maxRequests) {
      return { allowed: false, remaining: 0 };
    }

    return { allowed: true, remaining: this.maxRequests - count };
  }
}
```

**Rate limiting para login (com escalação):**

```
class LoginRateLimiter {
  constructor(redis) {
    this.redis = redis;
    this.attempts = [5, 10, 25, 50];  // Limite cresce após cada lockout
    this.lockoutDurations = [300, 900, 3600, 86400];  // 5min, 15min, 1h, 24h
  }

  async checkAndRecordAttempt(email, ip) {
    const emailKey = `login:attempts:email:${email.toLowerCase()}`;
    const ipKey = `login:attempts:ip:${ip}`;

    const [emailCount, ipCount, lockout] = await Promise.all([
      this.redis.incr(emailKey),
      this.redis.incr(ipKey),
      this.redis.get(`login:lockout:${email.toLowerCase()}`)
    ]);

    // Configurar expiração
    await Promise.all([
      this.redis.expire(emailKey, 900),  // 15 minutos
      this.redis.expire(ipKey, 900)
    ]);

    if (lockout) {
      return {
        allowed: false,
        reason: 'account_locked',
        retryAfter: parseInt(lockout)
      };
    }

    const attemptLevel = await this.redis.get(`login:level:${email.toLowerCase()}`) || 0;
    const maxAttempts = this.attempts[attemptLevel] || this.attempts[this.attempts.length - 1];

    if (emailCount > maxAttempts) {
      const lockoutDuration = this.lockoutDurations[attemptLevel] || this.lockoutDurations[this.lockoutDurations.length - 1];

      await this.redis.setex(
        `login:lockout:${email.toLowerCase()}`,
        lockoutDuration,
        lockoutDuration.toString()
      );

      await this.redis.incr(`login:level:${email.toLowerCase()}`);
      await this.redis.expire(`login:level:${email.toLowerCase()}`, 86400);

      return {
        allowed: false,
        reason: 'too_many_attempts',
        retryAfter: lockoutDuration
      };
    }

    return {
      allowed: true,
      remaining: maxAttempts - emailCount
    };
  }
}
```

### 16.5.2 Headers de rate limiting

Os headers de rate limiting comunicam ao cliente o estado atual e quando pode tentar novamente:

```
// Headers padrão (RFC 6585, draft-ietf-httpapi-ratelimit-headers)
function setRateLimitHeaders(res, limit, remaining, resetAt) {
  res.set('X-RateLimit-Limit', limit.toString());
  res.set('X-RateLimit-Remaining', remaining.toString());
  res.set('X-RateLimit-Reset', Math.ceil(resetAt / 1000).toString());

  // Header mais recente (draft)
  res.set('RateLimit', `limit=${limit}, remaining=${remaining}, reset=${Math.ceil(resetAt / 1000)}`);
}

// Quando rate limited
function setRateLimitExceeded(res, retryAfter) {
  res.set('Retry-After', retryAfter.toString());
  res.set('X-RateLimit-Remaining', '0');
}
```

---

## 16.6 Fluxo de Reset de Senha

### 16.6.1 Fluxo seguro completo

O fluxo de reset de senha é um dos vetores de ataque mais comuns. Um fluxo seguro deve proteger contra timing attacks, enumeration, e replay attacks.

```
// Fluxo completo de reset de senha
async function requestPasswordReset(req, res) {
  const { email } = req.body;

  // 1. Rate limiting
  if (!checkPasswordResetRateLimit(email)) {
    // Retornar mesma resposta para prevenir enumeration
    return res.json({ message: 'Se o email existir, você receberá um link de reset' });
  }

  // 2. Buscar usuário (case-insensitive)
  const user = await db.findUserByEmail(email.toLowerCase());

  // 3. SEMPRE retornar a mesma mensagem (prevenir enumeration)
  if (!user) {
    // Tempo constante para prevenir timing attack
    await argon2.hash('dummy');
    return res.json({ message: 'Se o email existir, você receberá um link de reset' });
  }

  // 4. Verificar se há reset pendente recente (prevenir spam)
  const recentReset = await db.findRecentPasswordReset(user.id, 15);  // últimos 15 min
  if (recentReset) {
    return res.json({ message: 'Se o email existir, você receberá um link de reset' });
  }

  // 5. Gerar token seguro
  const resetToken = crypto.randomBytes(32).toString('urlsafebase64');
  const hashedToken = crypto.createHash('sha256').update(resetToken).digest('hex');

  // 6. Armazenar hash do token (nunca o token em texto plano)
  await db.createPasswordReset({
    userId: user.id,
    tokenHash: hashedToken,
    expiresAt: new Date(Date.now() + 15 * 60 * 1000),  // 15 minutos
    used: false,
    ip: req.ip,
    userAgent: req.headers['user-agent']
  });

  // 7. Enviar email com token
  const resetUrl = `${process.env.APP_URL}/auth/reset-password?token=${resetToken}`;
  await emailService.send({
    to: user.email,
    subject: 'Redefinição de Senha',
    template: 'password-reset',
    data: { resetUrl, expiresIn: '15 minutos' }
  });

  // 8. Audit log
  await auditLog({
    action: 'password_reset.requested',
    userId: user.id,
    ip: req.ip
  });

  // 9. Retornar mensagem genérica
  return res.json({ message: 'Se o email existir, você receberá um link de reset' });
}

async function completePasswordReset(req, res) {
  const { token, newPassword } = req.body;

  // 1. Validar nova senha
  const passwordErrors = validatePassword(newPassword, passwordPolicy);
  if (passwordErrors.length > 0) {
    return res.status(400).json({ errors: passwordErrors });
  }

  // 2. Hash do token recebido
  const hashedToken = crypto.createHash('sha256').update(token).digest('hex');

  // 3. Buscar reset válido
  const reset = await db.findValidPasswordReset(hashedToken);
  if (!reset) {
    return res.status(400).json({ error: 'Token inválido ou expirado' });
  }

  // 4. Verificar se não foi usado
  if (reset.used) {
    // Possível replay attack — invalidar todos os resets do usuário
    await db.invalidateAllPasswordResets(reset.userId);
    await auditLog({
      action: 'password_reset.replay_detected',
      userId: reset.userId,
      ip: req.ip
    });
    return res.status(400).json({ error: 'Token já utilizado' });
  }

  // 5. Verificar expiração
  if (reset.expiresAt < new Date()) {
    return res.status(400).json({ error: 'Token expirado' });
  }

  // 6. Hash da nova senha
  const newHash = await argon2.hash(newPassword, {
    type: argon2.argon2id,
    memoryCost: 65536,
    timeCost: 3,
    parallelism: 4
  });

  // 7. Atualizar senha e invalidar resets
  await db.transaction(async (trx) => {
    await trx.updatePassword(reset.userId, newHash);
    await trx.invalidateAllPasswordResets(reset.userId);
    await trx.invalidateAllSessions(reset.userId);
  });

  // 8. Audit log
  await auditLog({
    action: 'password_reset.completed',
    userId: reset.userId,
    ip: req.ip
  });

  // 9. Notificar usuário por email
  await emailService.send({
    to: reset.userEmail,
    subject: 'Senha redefinida com sucesso',
    template: 'password-changed',
    data: { timestamp: new Date().toISOString() }
  });

  return res.json({ message: 'Senha redefinida com sucesso' });
}
```

### 16.6.2 Proteção contra enumeration

A proteção contra enumeration é crítica: um atacante não deve ser capaz de descobrir se um email existe no sistema através de diferentes respostas.

```
// Padrão: Respostas idênticas para cenários distintos
const GENERIC_RESPONSE = {
  message: 'Se o email existir em nossa base, você receberá instruções em breve'
};

// Para login
if (!user || !validPassword) {
  return res.status(401).json({ error: 'Credenciais inválidas' });
  // Mesma mensagem para "usuário não existe" e "senha incorreta"
}

// Para registro
if (await db.emailExists(email)) {
  return res.json(GENERIC_RESPONSE);
  // Não diz "email já cadastrado"
}

// Para reset de senha
if (!user) {
  return res.json(GENERIC_RESPONSE);
  // Não diz "email não encontrado"
}

// Para verificação de conta
return res.json(GENERIC_RESPONSE);
// Sempre a mesma resposta, independente do estado
```

---

## 16.7 Recovery de Conta

### 16.7.1 Múltiplos canais de recuperação

Um sistema robusto oferece múltiplos caminhos de recuperação para diferentes cenários:

**Cenário 1: Usuário perdeu acesso ao email**

```
// Recovery via perguntas de segurança (com limitações)
async function accountRecoverySecurityQuestions(req, res) {
  const { email, answers } = req.body;

  const user = await db.findUserByEmail(email);
  if (!user) {
    return res.json({ message: 'Se o email existir, você receberá instruções' });
  }

  // Verificar rate limiting
  if (!checkRecoveryRateLimit(user.id)) {
    return res.status(429).json({ error: 'Muitas tentativas' });
  }

  // Verificar respostas (hash comparado, não texto plano)
  const answersValid = await verifySecurityAnswers(user.id, answers);
  if (!answersValid) {
    await recordFailedRecoveryAttempt(user.id);
    return res.status(401).json({ error: 'Respostas incorretas' });
  }

  // Gerar token de recovery temporário
  const recoveryToken = generateRecoveryToken(user.id, 'security_questions', 60);  // 60 minutos

  return res.json({
    message: 'Respostas verificadas',
    recoveryToken,
    expiresIn: 3600
  });
}
```

**Cenário 2: Usuário perdeu acesso ao dispositivo MFA**

```
// Recovery via codes de backup
async function accountRecoveryBackupCodes(req, res) {
  const { email, backupCode } = req.body;

  const user = await db.findUserByEmail(email);
  if (!user) {
    return res.json({ message: 'Se o email existir, você receberá instruções' });
  }

  // Verificar code de backup (hash armazenado)
  const codeHash = crypto.createHash('sha256').update(backupCode).digest('hex');
  const validCode = await db.findAndConsumeBackupCode(user.id, codeHash);

  if (!validCode) {
    return res.status(401).json({ error: 'Code de backup inválido' });
  }

  // Gerar sessão temporária para reconfigurar MFA
  const tempSession = await createTemporarySession(user.id, {
    expiresIn: 30 * 60 * 1000,  // 30 minutos
    allowedActions: ['mfa.setup', 'mfa.disable'],
    requirePassword: true
  });

  // Notificar usuário
  await notifyUser(user.id, 'backup_code_used', {
    ip: req.ip,
    timestamp: new Date()
  });

  return res.json({
    message: 'Code de backup aceito. Reconfigure seu MFA.',
    tempSessionToken: tempSession.token,
    expiresIn: 1800
  });
}
```

**Cenário 3: Conta comprometida (takeover)**

```
// Recuperação de conta comprometida
async function accountTakeoverRecovery(req, res) {
  const { email, identityProof } = req.body;

  // Esta funcionalidade requer verificação manual ou identity verification
  // Não deve ser 100% automatizada para contas de alto risco

  const user = await db.findUserByEmail(email);
  if (!user) {
    return res.status(404).json({ error: 'Conta não encontrada' });
  }

  // Criar ticket de suporte
  const ticket = await support.createTicket({
    type: 'account_takeover',
    userId: user.id,
    evidence: identityProof,
    priority: 'critical',
    assignedTo: 'security_team'
  });

  // Congelar conta imediatamente
  await db.freezeAccount(user.id, 'Account takeover recovery in progress');

  // Invalidar todas as sessões
  await sessionManager.destroyAllForUser(user.id);

  // Notificar todos os canais do usuário
  await notifyUserAllChannels(user.id, 'account_frozen', {
    reason: 'Possível comprometimento detectado',
    ticketId: ticket.id
  });

  return res.json({
    message: 'Conta congelada. Um agente de segurança entrará em contato.',
    ticketId: ticket.id
  });
}
```

---

## 16.8 Padrões de Integração MFA

### 16.8.1 TOTP (Time-based One-Time Password)

TOTP é o padrão mais comum para MFA, baseado em HMAC e tempo. A implementação correta requer consideração de janela de tolerância, sincronização de relógio, e proteção contra replay.

```python
import hmac
import hashlib
import struct
import time
import base64

class TOTPGenerator:
    def __init__(self, secret, digits=6, period=30, algorithm='sha1'):
        self.secret = secret
        self.digits = digits
        self.period = period
        self.algorithm = algorithm

    def generate(self, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        # Calcular counter baseado no tempo
        counter = int(timestamp) // self.period

        # Converter counter para bytes (big-endian, 8 bytes)
        counter_bytes = struct.pack('>Q', counter)

        # Calcular HMAC
        if self.algorithm == 'sha1':
            hash_func = hashlib.sha1
        elif self.algorithm == 'sha256':
            hash_func = hashlib.sha256
        else:
            hash_func = hashlib.sha512

        mac = hmac.new(
            base64.b32decode(self.secret),
            counter_bytes,
            hash_func
        ).digest()

        # Dynamic truncation
        offset = mac[-1] & 0x0F
        code = struct.unpack('>I', mac[offset:offset + 4])[0]
        code &= 0x7FFFFFFF

        # Gerar código com dígitos especificados
        code = code % (10 ** self.digits)
        return str(code).zfill(self.digits)

    def verify(self, code, tolerance=1):
        """Verificar código com tolerância de janela."""
        current_time = time.time()

        # Verificar janela de tolerância (-1, 0, +1)
        for offset in range(-tolerance, tolerance + 1):
            timestamp = current_time + (offset * self.period)
            expected = self.generate(timestamp)
            if hmac.compare_digest(code, expected):
                return True

        return False


def setup_totp(user_id):
    """Configurar TOTP para um usuário."""
    secret = base64.b32encode(secrets.token_bytes(20)).decode()

    # Armazenar secret (encriptado)
    encrypted_secret = encrypt(secret, user_id)
    db.store_totp_secret(user_id, encrypted_secret)

    # Gerar QR code para apps autenticadores
    issuer = "MeuApp"
    otpauth_url = f"otpauth://totp/{issuer}:{user_id}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

    return {
        "secret": secret,
        "qr_code_url": otpauth_url,
        "backup_codes": generate_backup_codes(user_id)
    }


def generate_backup_codes(user_id, count=10):
    """Gerar codes de backup de uso único."""
    codes = []
    for _ in range(count):
        code = secrets.token_hex(4)  # 8 caracteres hexadecimais
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        db.store_backup_code(user_id, code_hash)
        codes.append(code)
    return codes
```

### 16.8.2 WebAuthn/FIDO2

WebAuthn é o padrão moderno para autenticação sem senha, utilizando chaves criptográficas hardware. A implementação requer consideração cuidadosa de challenge-response e armazenamento de credenciais.

```javascript
// Registro de credencial WebAuthn
async function registerWebAuthn(req, res) {
  const user = req.user;

  // Gerar challenge
  const challenge = crypto.randomBytes(32);

  // Criar opções de registro
  const publicKeyCredentialCreationOptions = {
    challenge,
    rp: {
      name: "MeuApp",
      id: process.env.RP_ID
    },
    user: {
      id: Buffer.from(user.id.toString()),
      name: user.email,
      displayName: user.name
    },
    pubKeyCredParams: [
      { alg: -7, type: "public-key" },   // ES256
      { alg: -257, type: "public-key" }  // RS256
    ],
    authenticatorSelection: {
      authenticatorAttachment: "platform",
      userVerification: "required",
      residentKey: "preferred"
    },
    timeout: 60000,
    attestation: "direct"
  };

  // Armazenar challenge para verificação posterior
  await redis.setex(
    `webauthn:challenge:${user.id}`,
    60,
    challenge.toString('hex')
  );

  return res.json(publicKeyCredentialCreationOptions);
}

// Verificar registro
async function verifyWebAuthnRegistration(req, res) {
  const user = req.user;
  const { credential } = req.body;

  // Recuperar challenge
  const storedChallenge = await redis.get(`webauthn:challenge:${user.id}`);
  if (!storedChallenge) {
    return res.status(400).json({ error: 'Challenge expirado' });
  }

  // Verificar challenge
  if (credential.response.clientDataJSON.challenge !== storedChallenge) {
    return res.status(400).json({ error: 'Challenge inválido' });
  }

  // Verificar origin
  const expectedOrigin = process.env.APP_URL;
  if (credential.response.clientDataJSON.origin !== expectedOrigin) {
    return res.status(400).json({ error: 'Origin inválido' });
  }

  // Verificar attestation
  const attestation = parseAttestation(credential.response.attestationObject);
  if (!attestation) {
    return res.status(400).json({ error: 'Attestation inválida' });
  }

  // Armazenar credencial
  await db.storeWebAuthnCredential({
    userId: user.id,
    credentialId: credential.rawId,
    publicKey: attestation.credentialPublicKey,
    signCount: attestation.signCount,
    aaguid: attestation.aaguid,
    createdAt: new Date()
  });

  // Limpar challenge
  await redis.del(`webauthn:challenge:${user.id}`);

  // Audit log
  await auditLog({
    action: 'webauthn.registered',
    userId: user.id,
    ip: req.ip
  });

  return res.json({ success: true });
}

// Autenticação
async function webauthnAuthenticate(req, res) {
  const { email } = req.body;

  const user = await db.findUserByEmail(email);
  if (!user) {
    return res.status(401).json({ error: 'Credenciais inválidas' });
  }

  // Buscar credenciais do usuário
  const credentials = await db.getWebAuthnCredentials(user.id);
  if (credentials.length === 0) {
    return res.status(400).json({ error: 'Nenhuma credencial registrada' });
  }

  // Gerar challenge
  const challenge = crypto.randomBytes(32);

  const publicKeyCredentialRequestOptions = {
    challenge,
    timeout: 60000,
    rpId: process.env.RP_ID,
    allowCredentials: credentials.map(cred => ({
      id: cred.credentialId,
      type: 'public-key',
      transports: ['internal']
    })),
    userVerification: "required"
  };

  await redis.setex(
    `webauthn:auth:${user.id}`,
    60,
    challenge.toString('hex')
  );

  return res.json(publicKeyCredentialRequestOptions);
}
```

---

## 16.9 Padrões de Audit Logging

### 16.9.1 Eventos que devem ser logados

O audit logging é essencial para detecção de incidentes, compliance, e forense digital. Nem todo evento precisa ser logado, mas eventos críticos de segurança NUNCA devem ser omitidos.

```
// Categorias de eventos de auditoria

// 1. Autenticação
const AUTH_EVENTS = {
  LOGIN_SUCCESS: 'auth.login.success',
  LOGIN_FAILED: 'auth.login.failed',
  LOGOUT: 'auth.logout',
  PASSWORD_CHANGED: 'auth.password.changed',
  PASSWORD_RESET_REQUESTED: 'auth.password_reset.requested',
  PASSWORD_RESET_COMPLETED: 'auth.password_reset.completed',
  MFA_ENABLED: 'auth.mfa.enabled',
  MFA_DISABLED: 'auth.mfa.disabled',
  MFA_CODE_USED: 'auth.mfa.code_used',
  MFA_BACKUP_CODE_USED: 'auth.mfa.backup_code_used',
  ACCOUNT_LOCKED: 'auth.account.locked',
  ACCOUNT_UNLOCKED: 'auth.account.unlocked',
  ACCOUNT_CREATED: 'auth.account.created',
  ACCOUNT_DELETED: 'auth.account.deleted'
};

// 2. Autorização
const AUTHZ_EVENTS = {
  ACCESS_GRANTED: 'authz.access.granted',
  ACCESS_DENIED: 'authz.access.denied',
  ROLE_ASSIGNED: 'authz.role.assigned',
  ROLE_REVOKED: 'authz.role.revoked',
  PERMISSION_CHANGED: 'authz.permission.changed'
};

// 3. Dados
const DATA_EVENTS = {
  DATA_ACCESSED: 'data.access',
  DATA_MODIFIED: 'data.modified',
  DATA_DELETED: 'data.deleted',
  DATA_EXPORTED: 'data.exported',
  DATA_SHARED: 'data.shared'
};

// 4. Sistema
const SYSTEM_EVENTS = {
  CONFIG_CHANGED: 'system.config.changed',
  USER_CREATED: 'system.user.created',
  USER_MODIFIED: 'system.user.modified',
  USER_DELETED: 'system.user.deleted',
  API_KEY_CREATED: 'system.api_key.created',
  API_KEY_REVOKED: 'system.api_key.revoked'
};
```

### 16.9.2 Estrutura de log de auditoria

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(64),
    ip_address INET,
    user_agent TEXT,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    action VARCHAR(50),
    result VARCHAR(20) CHECK (result IN ('success', 'failure', 'error')),
    metadata JSONB,
    checksum VARCHAR(64) NOT NULL  -- Integridade do registro
);

-- Índices para consultas comuns
CREATE INDEX idx_audit_logs_timestamp ON audit_logs (timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs (event_type);
CREATE INDEX idx_audit_logs_ip_address ON audit_logs (ip_address);

-- Partitioning por mês para performance
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- Imutabilidade: trigger para prevenir UPDATE/DELETE
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs cannot be modified or deleted';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_modification();
```

### 16.9.3 Integridade de logs

A integridade dos logs de auditoria é crítica — se um atacante puder modificar logs, poderá esconder seus rastros. A solução é usar chains de hash.

```python
import hashlib
import json
from datetime import datetime

class AuditLogger:
    def __init__(self, db):
        self.db = db
        self.previous_hash = None

    async def log(self, event):
        # Buscar hash anterior
        if self.previous_hash is None:
            last_log = await self.db.fetchrow(
                "SELECT checksum FROM audit_logs ORDER BY id DESC LIMIT 1"
            )
            self.previous_hash = last_log['checksum'] if last_log else '0' * 64

        # Criar registro
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event['type'],
            'user_id': event.get('user_id'),
            'ip_address': event.get('ip'),
            'resource_type': event.get('resource_type'),
            'resource_id': event.get('resource_id'),
            'action': event.get('action'),
            'result': event.get('result', 'success'),
            'metadata': event.get('metadata'),
            'previous_hash': self.previous_hash
        }

        # Calcular checksum
        content = json.dumps(log_entry, sort_keys=True, default=str)
        checksum = hashlib.sha256(content.encode()).hexdigest()
        log_entry['checksum'] = checksum

        # Inserir
        await self.db.execute(
            """INSERT INTO audit_logs
               (timestamp, event_type, user_id, ip_address, resource_type,
                resource_id, action, result, metadata, checksum)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
            log_entry['timestamp'], log_entry['event_type'], log_entry['user_id'],
            log_entry['ip_address'], log_entry['resource_type'], log_entry['resource_id'],
            log_entry['action'], log_entry['result'], json.dumps(log_entry['metadata']),
            log_entry['checksum']
        )

        self.previous_hash = checksum
        return checksum

    async def verify_chain(self, start_id=None, end_id=None):
        """Verificar integridade da cadeia de logs."""
        query = "SELECT * FROM audit_logs"
        params = []

        if start_id:
            query += " WHERE id >= $1"
            params.append(start_id)
        if end_id:
            query += " AND id <= $2" if start_id else " WHERE id <= $2"
            params.append(end_id)

        query += " ORDER BY id ASC"
        rows = await self.db.fetch(query, *params)

        previous_hash = '0' * 64
        tampered = []

        for row in rows:
            expected_hash = row['checksum']

            # Reconstruir conteúdo
            entry = {
                'timestamp': row['timestamp'].isoformat(),
                'event_type': row['event_type'],
                'user_id': row['user_id'],
                'ip_address': str(row['ip_address']) if row['ip_address'] else None,
                'resource_type': row['resource_type'],
                'resource_id': row['resource_id'],
                'action': row['action'],
                'result': row['result'],
                'metadata': row['metadata'],
                'previous_hash': previous_hash
            }

            content = json.dumps(entry, sort_keys=True, default=str)
            computed_hash = hashlib.sha256(content.encode()).hexdigest()

            if computed_hash != expected_hash:
                tampered.append(row['id'])

            previous_hash = expected_hash

        return {
            'total_checked': len(rows),
            'tampered': tampered,
            'valid': len(tampered) == 0
        }
```

---

## 16.10 Referência Completa de Implementação Segura

### 16.10.1 Checklist de implementação

A referência a seguir consolida todos os padrões discutidos neste capítulo em um checklist acionável. Cada item deve ser verificado antes do deploy em produção.

**Autenticação:**

1. Senhas armazenadas com Argon2id (não MD5, SHA-1, SHA-256, bcrypt)
2. Sal único por usuário, gerado com CSPRNG
3. Rate limiting em endpoints de login (IP + email)
4. Conta bloqueada após 5 tentativas失败
5. Mensagens de erro genéricas (não revelam existência de usuário)
6. MFA obrigatório para contas privilegiadas
7. Tokens JWT com expiração curta (15 min para access, 7 dias para refresh)
8. Refresh tokens em cookies HttpOnly+Secure+SameSite
9. Rotação de refresh tokens
10. Invalidação de sessões no logout
11. Regeneração de sessão após login
12. Timeout de inatividade (30 minutos)
13. Timeout absoluto (24 horas)

**Autorização:**

14. Deny-by-default em todas as políticas
15. Least privilege para todas as roles
16. Verificação de autorização em cada camada (API, serviço, banco)
17. Separation of Duty para operações críticas
18. Sem autorização client-side
19. Sem autorização por obscuridade
20. Auditoria de todas as decisões de autorização

**API Security:**

21. HTTPS obrigatório (HSTS com max-age >= 31536000)
22. Autenticação em cada requisição
23. Rate limiting por endpoint
24. Validação de JWT com algoritmo fixo (não "none")
25. JWKS rotation suportado
26. Scopes最小权限

**Rate Limiting:**

27. Rate limiting em endpoints sensíveis
28. Headers X-RateLimit-* retornados
29. Retry-After header em 429
30. Rate limiting escalonado para login

**Password Reset:**

31. Token de reset com 15 minutos de expiração
32. Token de uso único
33. Hash do token armazenado (não texto plano)
34. Respostas genéricas (prevenir enumeration)
35. Invalidação de todas as sessões após reset
36. Notificação ao usuário por email

**Recovery:**

37. Múltiplos canais de recovery
38. Codes de backup para MFA
39. Verificação manual para contas comprometidas
40. Notificação de security events

**MFA:**

41. TOTP com tolerância de 1 janela
42. Codes de backup de uso único
43. WebAuthn/FIDO2 para passwordless
44. Storage seguro de secrets MFA

**Audit Logging:**

45. Logs de todos os eventos de autenticação
46. Logs de todas as decisões de autorização
47. Logs imutáveis (trigger prevent UPDATE/DELETE)
48. Chain de hash para integridade
49. Retenção mínima de 1 ano
50. Alertas para eventos anômalos

**Infraestrutura:**

51. Secrets em vault (não hardcoded)
52. Environment segregation (dev/staging/prod)
53. Monitoring e alerting configurados
54. Incident response plan documentado
55. Penetration testing anual

### 16.10.2 Árvore de decisão para seleção de padrão

Ao implementar autenticação em um novo sistema, a seguinte árvore de decisão ajuda a selecionar o padrão correto:

```
O sistema requer autenticação de usuários?
├── SIM
│   ├── Os usuários são humanos?
│   │   ├── SIM
│   │   │   ├── Requer passwordless?
│   │   │   │   ├── SIM → WebAuthn/FIDO2
│   │   │   │   └── NÃO → Password + MFA
│   │   │   │       ├── Qual MFA?
│   │   │   │       │   ├── TOTP (padrão)
│   │   │   │       │   ├── SMS (menos seguro)
│   │   │   │       │   └── Push notification
│   │   │   │       └── Requer SSO?
│   │   │   │           ├── SIM → OIDC/SAML
│   │   │   │           └── NÃO → JWT sessions
│   │   │   └── Requer recuperação de conta?
│   │   │       ├── SIM → Email reset + backup codes
│   │   │       └── NÃO → (não recomendado)
│   │   └── NÃO (serviço)
│   │       ├── Client Credentials OAuth 2.0
│   │       └── API Keys + mTLS
│   └── Requer autorização?
│       ├── SIM
│       │   ├── Roles fixas? → RBAC
│       │   ├── Regras dinâmicas? → ABAC
│       │   ├── Baseada em relações? → ReBAC
│       │   └── Combinação? → Policy Engine (OPA/Cedar)
│       └── NÃO → (não recomendado)
└── NÃO
    └── Reconsider — todo sistema precisa de autenticação
```

### 16.10.3 Tabela comparativa de tecnologias

| Tecnologia | Uso Recomendado | Segurança | Complexidade | User Experience |
|------------|-----------------|-----------|--------------|-----------------|
| Password + TOTP | Aplicação geral | Alta | Média | Boa |
| WebAuthn/FIDO2 | Alta segurança | Muito Alta | Alta | Excelente |
| Magic Links | MVP, passwordless | Média | Baixa | Boa |
| OAuth 2.0 + OIDC | SSO, federation | Alta | Média | Excelente |
| SAML 2.0 | Enterprise SSO | Alta | Alta | Média |
| API Keys | M2M, serviços | Média | Baixa | N/A |
| Client Credentials | M2M OAuth | Alta | Média | N/A |
| JWT + Refresh | APIs modernas | Alta | Média | Boa |
| Session Cookies | Apps server-rendered | Alta | Baixa | Boa |

### 16.10.4 Relação com o caso Misantropi4

O caso Misantropi4 contra o IDAP demonstra falhas em múltiplos padrões descritos neste capítulo:

1. **Anti-Pattern 1 (Senhas fracas)**: O IDAP provavelmente não impôs políticas de senha adequadas, permitindo credenciais fracas
2. **Anti-Pattern 5 (Sem rate limiting)**: A ausência de rate limiting permitiu brute force ou credential stuffing em larga escala
3. **Anti-Pattern 10 (Autorização client-side)**: Se existia verificação de permissão apenas no frontend, o bypass era trivial
4. **Anti-Pattern 20 (Sem audit trail)**: A incapacidade de detectar o ataque rapidamente sugere falta de logs de auditoria
5. **Ausência de MFA**: Um sistema governamental com dados sensíveis deveria obrigatório MFA
6. **Ausência de least privilege**: O dano massivo sugere que credenciais comprometidas tinham acesso excessivo
7. **Ausência de monitoring**: O ataque prolongado sugere falta de alertas para comportamento anômalo

Se o IDAP tivesse implementado apenas metade dos padrões deste capítulo, o impacto do Misantropi4 teria sido drasticamente reduzido. Autenticação e autorização seguras não são luxos — são requisitos fundamentais para qualquer sistema que processe dados sensíveis.

---

## Resumo

Este capítulo apresentou um catálogo abrangente de padrões seguros para implementação de autenticação, autorização, e controle de acesso. Os 20 anti-patterns documentados representam as falhas mais comuns e perigosas em sistemas reais. Os padrões de autenticação segura cobrem desde fluxos de login até gerenciamento de sessões e refresh tokens. Os padrões de autorização incluem least privilege, deny-by-default, separation of duty, e verificação em cada camada. A seção de APIs cobre autenticação para múltiplos cenários (web, mobile, machine-to-machine). Rate limiting, password reset, account recovery, MFA, e audit logging foram tratados com implementações completas e seguras. A referência final consolida tudo em um checklist acionável e uma árvore de decisão para seleção de padrão. O caso Misantropi4 serve como lembrete constante de que a implementação incorreta de autenticação e autorização pode ter consequências devastadoras para organizações e seus usuários.

---

## 16.11 Armazenamento Seguro de Credenciais

### 16.11.1 Comparação de algoritmos de hash

A escolha do algoritmo de hash para senhas é uma das decisões mais importantes em segurança de autenticação. A tabela a seguir compara os algoritmos mais comuns:

| Algoritmo | Tipo | Memória | CPU | Segurança Recomendada | Status |
|-----------|------|---------|-----|----------------------|--------|
| MD5 | Hash genérico | 0 | Muito baixa | N/A | PROIBIDO |
| SHA-1 | Hash genérico | 0 | Baixa | N/A | PROIBIDO |
| SHA-256 | Hash genérico | 0 | Média | N/A | PROIBIDO para senhas |
| bcrypt | Password hash | 4KB | Média | cost=12 | Aceitável |
| scrypt | Password hash | Configurável | Configurável | N=2^14, r=8, p=1 | Bom |
| Argon2id | Password hash | Configurável | Configurável | 64MB, 3 iterações | ÓTIMO |
| PBKDF2 | Password hash | 0 | Configurável | 600.000 iterações | Aceitável |

**Por que não usar hashes genéricos (MD5, SHA-1, SHA-256)?**

Hashes genéricos são projetados para velocidade — isso é uma vulnerabilidade em senhas. Um atacante com uma GPU moderna pode calcular bilhões de hashes MD5 por segundo. Hashes de senha são projetados para serem lentos intencionalmente:

```
// Velocidade aproximada (hashes por segundo em GPU moderna)
// MD5:       ~50.000.000.000/s (50 bilhões)
// SHA-256:   ~10.000.000.000/s (10 bilhões)
// bcrypt:    ~30.000/s (com cost=12)
// Argon2id:  ~1.000/s (64MB, 3 iterações)
```

### 16.11.2 Implementação de Argon2id

Argon2id é o vencedor do Password Hashing Competition (PHC) e é recomendado pelo OWASP e NIST. Ele resiste a ataques de GPU e side-channel simultaneamente:

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

class SecurePasswordStorage:
    def __init__(self):
        self.hasher = PasswordHasher(
            time_cost=3,        # 3 iterações
            memory_cost=65536,  # 64 MB
            parallelism=4,      # 4 threads
            hash_len=32,        # 32 bytes de hash
            salt_len=16,        # 16 bytes de sal
            type=argon2.Type.ID  # Argon2id
        )

    def hash_password(self, password: str) -> str:
        """Hash de senha com Argon2id."""
        return self.hasher.hash(password)

    def verify_password(self, stored_hash: str, password: str) -> bool:
        """Verificar senha contra hash armazenado."""
        try:
            self.hasher.verify(stored_hash, password)
            return True
        except VerifyMismatchError:
            return False
        except VerificationError:
            # Hash corrompido ou formato inválido
            return False

    def needs_rehash(self, stored_hash: str) -> bool:
        """Verificar se o hash precisa ser re-hashado (parâmetros atualizados)."""
        return self.hasher.check_needs_rehash(stored_hash)

    def migrate_hash(self, old_hash: str, password: str) -> str:
        """Migrar hash antigo para Argon2id."""
        if self.needs_rehash(old_hash):
            return self.hash_password(password)
        return old_hash
```

### 16.11.3 Política de rehash

Quando os parâmetros de hash mudam (por atualização de segurança ou hardware), hashes existentes devem ser migrados silenciosamente:

```
// Padrão: rehash silencioso no login
async function loginWithRehash(email, password) {
  const user = await db.findUserByEmail(email);
  if (!user) return null;

  const valid = await verifyPassword(user.password_hash, password);
  if (!valid) return false;

  // Rehash silencioso se parâmetros mudaram
  if (needsRehash(user.password_hash)) {
    const newHash = await hashPassword(password);
    await db.updatePasswordHash(user.id, newHash);
    logger.info('Password rehashed', { userId: user.id });
  }

  return user;
}
```

---

## 16.12 Gerenciamento de Ciclo de Vida de Tokens

### 16.12.1 Estados de um token

Um token seguro passa por múltiplos estados durante seu ciclo de vida. Cada transição deve ser controlada e auditada:

```
 Estados do Token:
 ┌─────────┐   emissão   ┌──────────┐   uso     ┌──────────┐
 │  NULL   │ ──────────> │  ACTIVE  │ ────────> │  USED    │
 └─────────┘             └──────────┘           └──────────┘
                              │                      │
                              │ expiração            │ rotação
                              v                      v
                         ┌──────────┐           ┌──────────┐
                         │ EXPIRED  │           │ ROTATED  │
                         └──────────┘           └──────────┘
                              │                      │
                              │                      │ invalidação
                              v                      v
                         ┌──────────┐           ┌──────────┐
                         │REVOKED   │           │BLACKLIST │
                         └──────────┘           └──────────┘
```

### 16.12.2 Blacklist de tokens

A blacklist é necessária para invalidar tokens antes de sua expiração natural (logout, compromise, mudança de senha):

```python
class TokenBlacklist:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def revoke(self, token: str, expires_at: datetime):
        """Adicionar token à blacklist."""
        ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            await self.redis.setex(
                f"token:blacklist:{token}",
                ttl,
                "revoked"
            )

    async def is_revoked(self, token: str) -> bool:
        """Verificar se token está na blacklist."""
        return await self.redis.exists(f"token:blacklist:{token}")

    async def revoke_all_for_user(self, user_id: str):
        """Invalidar todos os tokens de um usuário (comprometimento de conta)."""
        # Em produção, usar scan para encontrar todos os tokens
        pattern = f"token:user:{user_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern)
            for key in keys:
                await self.redis.delete(key)
            if cursor == 0:
                break

        # Marcar usuário para invalidação
        await self.redis.setex(
            f"token:user_revoked:{user_id}",
            86400,  # 24 horas
            "true"
        )
```

### 16.12.3 Validação completa de JWT

A validação de JWT deve verificar múltiplos aspectos para prevenir ataques:

```javascript
function validateJWT(token, options = {}) {
  const {
    requiredIssuer = process.env.AUTH_ISSUER,
    requiredAudience = process.env.API_AUDIENCE,
    requiredClaims = [],
    clockTolerance = 30  // 30 segundos de tolerância
  } = options;

  // 1. Decodificar header para obter kid
  const decoded = jwt.decode(token, { complete: true });
  if (!decoded) {
    throw new JWTError('Formato de token inválido');
  }

  // 2. Verificar algoritmo (prevenir alg=none attack)
  const allowedAlgorithms = ['RS256', 'ES256', 'PS256'];
  if (!allowedAlgorithms.includes(decoded.header.alg)) {
    throw new JWTError('Algoritmo não permitido');
  }

  // 3. Buscar chave pública
  const publicKey = getPublicKey(decoded.header.kid);
  if (!publicKey) {
    throw new JWTError('Chave pública não encontrada');
  }

  // 4. Verificar assinatura e claims
  const payload = jwt.verify(token, publicKey, {
    algorithms: allowedAlgorithms,
    issuer: requiredIssuer,
    audience: requiredAudience,
    clockTolerance
  });

  // 5. Verificar claims customizados
  for (const claim of requiredClaims) {
    if (payload[claim] === undefined) {
      throw new JWTError(`Claim obrigatório ausente: ${claim}`);
    }
  }

  // 6. Verificar se não está na blacklist
  if (isRevoked(payload.jti)) {
    throw new JWTError('Token revogado');
  }

  // 7. Verificar se o usuário não está bloqueado
  if (await isUserBlocked(payload.sub)) {
    throw new JWTError('Usuário bloqueado');
  }

  return payload;
}
```

---

## 16.13 Configuração Segura de Cookies

### 16.13.1 Flags de segurança para cookies de sessão

Cada flag de cookie tem um propósito específico de segurança. A ausência de qualquer uma delas cria uma vulnerabilidade:

```
// Comparação: cookie inseguro vs seguro

// INSEGURO
Set-Cookie: session=abc123
// - Sem HttpOnly: JavaScript pode acessar (XSS rouba sessão)
// - Sem Secure: Enviado em HTTP (MITM intercepta)
// - Sem SameSite: Enviado em requests cross-origin (CSRF)
// - Sem path: Disponível em todas as rotas
// - Sem maxAge: Dura para sempre

// SEGURO
Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=1800; Domain=.example.com
```

### 16.13.2 Implementação completa de cookie manager

```python
from datetime import datetime, timedelta
from typing import Optional

class SecureCookieManager:
    def __init__(self, config):
        self.config = config

    def set_session_cookie(
        self,
        response,
        session_id: str,
        max_age: int = 1800,  # 30 minutos
        domain: Optional[str] = None,
        path: str = '/',
        secure: bool = True,
        httponly: bool = True,
        samesite: str = 'Strict'
    ):
        """Configurar cookie de sessão seguro."""
        response.set_cookie(
            key='session',
            value=session_id,
            max_age=max_age,
            domain=domain or self.config.COOKIE_DOMAIN,
            path=path,
            secure=secure,
            httponly=httponly,
            samesite=samesite
        )

        # Header adicional para browsers modernos
        response.headers['Set-Cookie'] = (
            f'session={session_id}; '
            f'Max-Age={max_age}; '
            f'Path={path}; '
            f'Domain={domain or self.config.COOKIE_DOMAIN}; '
            f'{"Secure; " if secure else ""}'
            f'{"HttpOnly; " if httponly else ""}'
            f'SameSite={samesite}'
        )

    def set_refresh_cookie(
        self,
        response,
        refresh_token: str,
        max_age: int = 604800  # 7 dias
    ):
        """Configurar cookie de refresh token."""
        self.set_session_cookie(
            response,
            refresh_token,
            max_age=max_age,
            path='/auth/refresh',  # Escopo mínimo
            samesite='Strict'
        )

    def clear_session_cookie(self, response):
        """Limpar cookie de sessão (logout)."""
        response.delete_cookie(
            key='session',
            path='/',
            domain=self.config.COOKIE_DOMAIN,
            samesite='Strict'
        )

    def clear_refresh_cookie(self, response):
        """Limpar cookie de refresh token."""
        response.delete_cookie(
            key='refreshToken',
            path='/auth/refresh',
            domain=self.config.COOKIE_DOMAIN,
            samesite='Strict'
        )
```

---

## 16.14 Headers de Segurança para Autenticação

### 16.14.1 Headers essenciais

Headers HTTP de segurança complementam autenticação e autorização ao proteger contra XSS, clickjacking, e outros ataques:

```
# Headers de segurança obrigatórios
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0  # Desabilitar — Use CSP em vez disso
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store, no-cache, must-revalidate
Pragma: no-cache
```

### 16.14.2 Implementação de security headers middleware

```python
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message['type'] == 'http.response.start':
                headers = message.get('headers', [])

                security_headers = [
                    (b'strict-transport-security', b'max-age=31536000; includeSubDomains; preload'),
                    (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'),
                    (b'x-xss-protection', b'0'),
                    (b'referrer-policy', b'strict-origin-when-cross-origin'),
                    (b'permissions-policy', b'camera=(), microphone=(), geolocation=()'),
                    (b'cache-control', b'no-store, no-cache, must-revalidate'),
                    (b'pragma', b'no-cache'),
                ]

                # CSP para endpoints de autenticação
                csp = (
                    "default-src 'self'; "
                    "script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "form-action 'self'"
                )
                security_headers.append((b'content-security-policy', csp.encode()))

                message['headers'] = headers + security_headers

            return await send(message)

        return await self.app(scope, receive, send_with_headers)
```

---

## 16.15 Validação de Input em Endpoints de Autenticação

### 16.15.1 Validação de email

A validação de email deve ser robusta mas não excessivamente restritiva. Use normalização antes de armazenar:

```python
import re
import unicodedata
from typing import Optional

class EmailValidator:
    # RFC 5322 simplified pattern
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )

    @staticmethod
    def normalize(email: str) -> Optional[str]:
        """Normalizar email para comparação case-insensitive."""
        if not email or not isinstance(email, str):
            return None

        email = email.strip().lower()
        email = unicodedata.normalize('NFKC', email)

        # Remover pontos antes do @ (Gmail-specific)
        if '@gmail.com' in email or '@googlemail.com' in email:
            local, domain = email.rsplit('@', 1)
            local = local.replace('.', '')
            email = f'{local}@{domain}'

        return email

    @classmethod
    def validate(cls, email: str) -> tuple[bool, Optional[str]]:
        """Validar e normalizar email."""
        normalized = cls.normalize(email)
        if not normalized:
            return False, None

        if len(normalized) > 254:  # RFC 5321
            return False, None

        if not cls.EMAIL_REGEX.match(normalized):
            return False, None

        # Verificar domínio (lookup MX record opcional)
        return True, normalized


# Uso
def handle_registration(email: str):
    valid, normalized = EmailValidator.validate(email)
    if not valid:
        return {"error": "Email inválido"}

    # Usar email normalizado para busca e armazenamento
    existing = db.find_user_by_email(normalized)
    if existing:
        return {"error": "Email já cadastrado"}

    return {"normalized_email": normalized}
```

### 16.15.2 Proteção contra timing attacks

Timing attacks podem revelar informações sobre credenciais através do tempo de resposta. Todas as comparações sensíveis devem usar comparação de tempo constante:

```python
import hmac
import secrets

class TimingSafeComparator:
    @staticmethod
    def compare(a: str, b: str) -> bool:
        """Comparação de tempo constante."""
        return hmac.compare_digest(a.encode(), b.encode())

    @staticmethod
    def compare_hashes(stored_hash: str, computed_hash: str) -> bool:
        """Comparação segura de hashes."""
        if len(stored_hash) != len(computed_hash):
            # Ainda retornar False em tempo constante
            hmac.compare_digest(b'\x00' * len(stored_hash), b'\x00' * len(computed_hash))
            return False
        return hmac.compare_digest(stored_hash.encode(), computed_hash.encode())


class TimingSafeAuth:
    @staticmethod
    async def login(email: str, password: str):
        """Login com proteção contra timing attacks."""
        user = await db.find_user_by_email(email)

        if user is None:
            # Executar hash mesmo se usuário não existe
            # para manter tempo constante
            dummy_hash = '$argon2id$v=19$m=65536,t=3,p=4$' + 'x' * 43
            argon2.verify(dummy_hash, password)
            return None

        # Verificar senha
        if not argon2.verify(user.password_hash, password):
            return None

        return user
```

### 16.15.3 Validação de tokens de refresh

```python
import jwt
from datetime import datetime

class RefreshTokenValidator:
    def __init__(self, secret_key: str, issuer: str, audience: str):
        self.secret_key = secret_key
        self.issuer = issuer
        self.audience = audience

    def validate(self, token: str) -> dict:
        """Validar refresh token com todas as verificações."""
        try:
            # 1. Decodificar e verificar assinatura
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256'],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    'require': ['exp', 'iat', 'sub', 'jti', 'type'],
                    'verify_exp': True,
                    'verify_iat': True,
                    'verify_iss': True,
                    'verify_aud': True
                }
            )

            # 2. Verificar tipo de token
            if payload.get('type') != 'refresh':
                raise InvalidTokenError('Tipo de token inválido')

            # 3. Verificar se não está revogado
            if self.is_revoked(payload['jti']):
                raise InvalidTokenError('Token revogado')

            # 4. Verificar se o usuário está ativo
            user = db.find_user_by_id(payload['sub'])
            if not user or user.status != 'active':
                raise InvalidTokenError('Usuário inativo')

            # 5. Verificar se a sessão é válida
            session = session_manager.validate(payload.get('session_id'))
            if not session:
                raise InvalidTokenError('Sessão expirada')

            return payload

        except jwt.ExpiredSignatureError:
            raise InvalidTokenError('Token expirado')
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f'Token inválido: {str(e)}')
```

---

## Exercícios

1. **Implementação de fluxo de login**: Implemente o fluxo completo de login seguro descrito na seção 16.2.1, incluindo rate limiting, lockout, e audit logging. Teste com cenários de brute force e enumeração

2. **Sistema de rate limiting**: Implemente o `LoginRateLimiter` com escalação (seção 16.5.1). Teste com diferentes padrões de ataque e meça a eficácia

3. **Audit logging com integridade**: Implemente o `AuditLogger` com chain de hash (seção 16.9.3). Verifique a integridade e simule uma tentativa de adulteração

4. **Anti-pattern identification**: Analise um projeto open-source real e identifique quantos dos 20 anti-patterns estão presentes. Documente cada ocorrência e proponha a correção

5. **WebAuthn implementation**: Implemente o fluxo completo de WebAuthn (registro e autenticação) descrito na seção 16.8.2. Teste com um authenticator virtual

6. **Comparação de MFA**: Implemente TOTP e WebAuthn para o mesmo usuário. Compare experiência do usuário, segurança, e complexidade de implementação

7. **Recovery flow design**: Projete um fluxo completo de account recovery que suporte email perdido, MFA perdido, e conta comprometida. Documente as tradeoffs de cada cenário

---

## Referências

1. NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management
2. OWASP ASVS v4.0 — Application Security Verification Standard
3. RFC 6749 — The OAuth 2.0 Authorization Framework
4. RFC 7636 — PKCE (Proof Key for Code Exchange)
5. RFC 7519 — JSON Web Token (JWT)
6. RFC 6238 — TOTP (Time-Based One-Time Password Algorithm)
7. FIDO Alliance — WebAuthn Level 3 Specification
8. NIST SP 800-63C — Digital Identity Guidelines: Federation and Assertions
9. OWASP Cheat Sheet Series — Authentication Cheat Sheet
10. OWASP Cheat Sheet Series — Session Management Cheat Sheet
11. Auth0 Architecture — Secure Authentication Architecture
12. Google Cloud — Authentication Best Practices
13. AWS — IAM Best Practices
14. Misantropi4 Case Study — Análise de incidente de segurança governamental (Capítulo 15)
15. LastPass Breach Analysis (2022) — Falhas em criptografia e autenticação
16. Colonial Pipeline Incident (2021) — VPN credential compromise
17. Okta/Lapsus$ Incident (2022) — Social engineering e session hijacking
18. Uber MFA Fatigue Attack (2022) — Bypass de MFA via spam de notificações
---

*[Capítulo anterior: 15 — Caso Misantropi4](15-caso-misantropi4.md)*
*[Próximo capítulo: 17 — Compliance](17-compliance.md)*
