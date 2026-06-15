# Capítulo 07 — Autenticação e Gerenciamento de Sessão

> *"A autenticação é a primeira muralha de qualquer sistema. Quando ela cai, todas as outras defesas se tornam irrelevantes."*

---

## 7.1 Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Armazenar senhas de forma segura usando bcrypt, scrypt e Argon2id, entendendo as tradeoffs de cada algoritmo
- Implementar autenticação multifator com TOTP, WebAuthn/FIDO2 e avaliar a segurança de SMS como fator secundário
- Projetar fluxos OAuth 2.0 seguros incluindo Authorization Code com PKCE e Client Credentials
- Usar OpenID Connect para autenticação baseada em identidade com ID tokens e UserInfo endpoint
- Identificar e prevenir vulnerabilidades em JWT, incluindo confusão de algoritmos e rotação de chaves
- Gerenciar sessões de forma segura, prevenindo session fixation e ataques relacionados
- Distinguir tradeoffs entre autenticação baseada em cookies e baseada em tokens
- Implementar proteção contra brute force, credential stuffing e fluxos de reset de senha seguros
- Analisar CVEs reais de falhas de autenticação (CVE-2019-11510, CVE-2020-1472) e extrair lições aplicáveis
- Construir um sistema de autenticação completo em Express.js e Flask

### Conhecimento Prévio Necessário

| Conceito | Nível | Capítulo de Referência |
|----------|-------|----------------------|
| HTTP/HTTPS | Intermediário | Capítulo 04 — Introdução à Segurança Web |
| TLS/SSL | Básico | Capítulo 09 — Criptografia na Web |
| SQL injection | Intermediário | Capítulo 04 — Introdução à Segurança Web |
| XSS | Intermediário | Capítulo 05 — Cross-Site Scripting (XSS) |
| CORS | Básico | Capítulo 10 — Validação de Input |

### Mapeamento OWASP Top 10

Este capítulo aborda diretamente o **A07:2021 — Identification and Authentication Failures**, anteriormente conhecido como "Broken Authentication" no OWASP Top 10 de 2017. Essa categoria permanece consistentemente entre as vulnerabilidades mais exploradas em aplicações web.

Segundo o OWASP, falhas de autenticação permitem que atacantes comprometam bilhões de contas usando credenciais roubadas, credential stuffing, ou exploração de mecanismos de autenticação mal implementados. O Impacto médio de uma falha de autenticação é classificado como **alto** para confidencialidade, integridade e disponibilidade.

---

## 7.2 Armazenamento de Senhas: bcrypt, scrypt e Argon2id

### 7.2.1 O Problema Fundamental

Armazenar senhas em texto claro é o erro mais básico e mais catastrófico que uma aplicação web pode cometer. Quando o LinkedIn foi comprometido em 2012, 6.5 milhões de hashes MD5 sem salt foram expostos. Quando o Adobe foi comprometido em 2013, 153 milhões de senhas foram roubadas — todas criptografadas com 3DES em modo ECB, o que permitiu a recuperação de senhas em massa.

O problema do armazenamento de senhas é fundamentalmente diferente do armazenamento de dados sensíveis gerais. Enquente dados podem ser criptografados com chaves que o servidor conhece (permitindo decriptação), senhas devem ser armazenadas de forma **unidirecional** — é computacionalmente inviável inverter a operação. Isso é chamado de **hashing de senhas**.

### 7.2.2 Por Que Hashing Simples Não Basta

```javascript
// VULNERAVEL: MD5 para hashing de senhas
const crypto = require('crypto');

function hashPasswordUnsafe(password) {
    return crypto.createHash('md5').update(password).digest('hex');
}

// Um atacante pode fazer rainbow table attack em segundos
// MD5: ~100 bilhões de hashes/segundo em hardware moderno
const hash = hashPasswordUnsafe('minhaSenha123');
// Resultado: "5a105e8b9d40e13297ef0361635a6123"
```

MD5, SHA-1 e SHA-256 são projetados para serem **rápidos**. Essa é a característica errada para hashing de senhas. Um GPU moderno pode calcular bilhões de MD5 por segundo, tornando ataques de força bruta triviais para senhas fracas.

### 7.2.3 bcrypt

bcrypt foi projetado especificamente para hashing de senhas, incorporando uma **função de key derivation** (Eksblowfish) que permite ajustar o custo computacional.

```javascript
const bcrypt = require('bcrypt');

const SALT_ROUNDS = 12;

async function hashPassword(password) {
    const salt = await bcrypt.genSalt(SALT_ROUNDS);
    const hash = await bcrypt.hash(password, salt);
    return hash;
}

async function verifyPassword(password, storedHash) {
    return await bcrypt.compare(password, storedHash);
}

// Exemplo de uso
async function createUser(username, password) {
    const hash = await hashPassword(password);
    // Armazenar username e hash no banco
    // NUNCA armazenar a senha em texto claro
    return { username, hash };
}

async function authenticateUser(username, password, storedHash) {
    const isValid = await verifyPassword(password, storedHash);
    if (!isValid) {
        throw new Error('Invalid credentials');
    }
    return true;
}

// bcrypt formata o hash automaticamente: $2b$12$...
// O formato inclui: algoritmo, custo, salt e hash
// Exemplo: $2b$12$K8wLzO3xUqZ5gH2jN9vYKe8xQ3r5tY7uI0oP2aS4dF6gH8jK0l
```

**Parâmetros de custo do bcrypt:**

| Rodadas | Tempo Approximado (2024) | Segurança |
|---------|-------------------------|-----------|
| 8 | ~40ms | Mínimo aceitável |
| 10 | ~100ms | Aceitável |
| 12 | ~300ms | Recomendado |
| 14 | ~2s | Alto custo |
| 16 | ~15s | Apenas para high-security |

**Vantagens do bcrypt:**
- Algoritmo purpose-built para hashing de senhas
- Salt embutido no hash (não precisa de armazenamento separado)
- Custo ajustável via parâmetro de work factor
- Resistente a ataques de rainbow table

**Limitações do bcrypt:**
- Limite de 72 bytes na senha de entrada
- Não é memória-hard (vulnerável a ataques com GPU/ASIC)
- Work factor é linear no tempo de verificação

### 7.2.4 scrypt

scrypt foi projetado para ser **memória-hard**, tornando ataques com hardware especializado (GPUs, FPGAs, ASICs) significativamente mais caros.

```javascript
const scrypt = require('scrypt');

const SCRYPT_PARAMS = {
    N: 16384,    // CPU/memory cost parameter (deve ser potência de 2)
    r: 8,        // Block size
    p: 1,        // Parallelization parameter
    maxmem: 128 * 1024 * 1024  // 128MB limit
};

async function hashPasswordScrypt(password) {
    const salt = crypto.randomBytes(16).toString('hex');
    
    return new Promise((resolve, reject) => {
        crypto.scrypt(password, salt, 64, SCRYPT_PARAMS, (err, derivedKey) => {
            if (err) reject(err);
            resolve(salt + ':' + derivedKey.toString('hex'));
        });
    });
}

async function verifyPasswordScrypt(password, stored) {
    const [salt, hash] = stored.split(':');
    
    return new Promise((resolve, reject) => {
        crypto.scrypt(password, salt, 64, SCRYPT_PARAMS, (err, derivedKey) => {
            if (err) reject(err);
            resolve(derivedKey.toString('hex') === hash);
        });
    });
}
```

**Parâmetros de scrypt:**

| Parâmetro | Descrição | Valor Recomendado |
|-----------|-----------|-------------------|
| N | Custo CPU/memória | 16384 (2^14) |
| r | Tamanho do bloco | 8 |
| p | Paralelismo | 1 |
| keyLength | Tamanho da chave derivada | 64 bytes |

**Vantagens do scrypt:**
- Memória-hard: dificulta ataques com hardware paralelizado
- Parâmetros ajustáveis independentemente
- Resistente a ASICs e GPUs

**Limitações do scrypt:**
- Mais lento que bcrypt em hardware normal
- Parâmetros complexos de dimensionar
- Menos amplamente suportado que bcrypt

### 7.2.5 Argon2id — O Padrão Atual

Argon2 venceu o Password Hashing Competition (PHC) em 2015 e se tornou o padrão recomendado. **Argon2id** é a variante recomendada, combinando as vantagens de Argon2i (resistente a side-channel) e Argon2d (resistente a GPU cracking).

```python
# Python com argon2-cffi
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,        # Número de iterações
    memory_cost=65536,  # 64 MB de memória
    parallelism=4,      # 4 threads paralelas
    hash_len=32,        # Tamanho do hash em bytes
    salt_len=16,        # Tamanho do salt em bytes
)

def hash_password_argon2(password):
    return ph.hash(password)

def verify_password_argon2(password, stored_hash):
    try:
        ph.verify(stored_hash, password)
        return True
    except VerifyMismatchError:
        return False

def needs_rehash(stored_hash):
    # Retorna True se o hash precisa ser re-hashed
    # (útil quando os parâmetros de custo são atualizados)
    return ph.check_needs_rehash(stored_hash)
```

```javascript
// JavaScript/Node.js com argon2
const argon2 = require('argon2');

const ARGON2_OPTIONS = {
    type: argon2.argon2id,
    memoryCost: 65536,    // 64 MB
    timeCost: 3,          // 3 iterações
    parallelism: 4,       // 4 threads
    saltLength: 16,       // 16 bytes de salt
    hashLength: 32        // 32 bytes de hash
};

async function hashPasswordArgon2(password) {
    return await argon2.hash(password, ARGON2_OPTIONS);
}

async function verifyPasswordArgon2(password, storedHash) {
    return await argon2.verify(storedHash, password);
}

async function checkNeedsRehash(storedHash) {
    return await argon2.needsRehash(storedHash, ARGON2_OPTIONS);
}
```

### 7.2.6 Comparação Detalhada

| Característica | bcrypt | scrypt | Argon2id |
|----------------|--------|--------|----------|
| Ano de criação | 1999 | 2009 | 2015 |
| Autor | Provos, Mazieres | Percival | Diniz, et al. |
| Memória-hard | Não | Sim | Sim |
| Resistente a GPU | Parcial | Sim | Sim |
| Resistente a ASIC | Não | Parcial | Sim |
| Resistente a side-channel | Sim | Não | Sim (Argon2id) |
| Limite de senha | 72 bytes | Sem limite | Sem limite |
| Parâmetros | 1 (cost) | 3 (N, r, p) | 3 (time, mem, parallel) |
| Phc winner | Não | Não | Sim (2015) |
| Recomendação atual | Aceitável | Aceitável | **Recomendado** |

### 7.2.7 Migrando de Sistemas Legados

Um dos cenários mais comuns em produção é o legado de hashes inseguros. A estratégia correta é usar **hashing transparente** (também chamado de hash migration ou hash upgrade):

```javascript
const argon2 = require('argon2');
const bcrypt = require('bcrypt');
const crypto = require('crypto');

class PasswordStorage {
    constructor(argon2Options, bcryptRounds = 12) {
        this.argon2Options = argon2Options;
        this.bcryptRounds = bcryptRounds;
    }

    async hash(password) {
        // Sempre usar Argon2id para novos hashes
        return await argon2.hash(password, this.argon2Options);
    }

    async verify(password, storedHash) {
        // Detectar algoritmo pelo prefixo
        if (storedHash.startsWith('$argon2')) {
            return await argon2.verify(storedHash, password);
        }
        if (storedHash.startsWith('$2b$') || storedHash.startsWith('$2a$')) {
            return await bcrypt.compare(password, storedHash);
        }
        // Para hashes legados (SHA-256, MD5, etc.)
        // Extrair salt se disponível
        const parts = storedHash.split(':');
        if (parts.length === 2) {
            const [salt, hash] = parts;
            const computedHash = crypto
                .createHash('sha256')
                .update(salt + password)
                .digest('hex');
            if (computedHash === hash) {
                // Login bem-sucedido — re-hash com Argon2id
                return 'REHASH_NEEDED';
            }
        }
        return false;
    }

    async verifyAndUpgrade(password, storedHash, userId, db) {
        const result = await this.verify(password, storedHash);
        
        if (result === 'REHASH_NEEDED') {
            // Re-hash silenciosamente com o novo algoritmo
            const newHash = await this.hash(password);
            await db.updatePasswordHash(userId, newHash);
            return true;
        }
        
        return result;
    }
}

// Padrão de prefixo para detecção de algoritmo
const HASH_PREFIXES = {
    argon2id: '$argon2id$',
    argon2i: '$argon2i$',
    argon2d: '$argon2d$',
    bcrypt: '$2b$',
    bcrypt_a: '$2a$',
    scrypt: '$scrypt$',
    pbkdf2_sha256: '$pbkdf2-sha256$',
    pbkdf2_sha512: '$pbkdf2-sha512$'
};

function detectAlgorithm(hash) {
    for (const [name, prefix] of Object.entries(HASH_PREFIXES)) {
        if (hash.startsWith(prefix)) {
            return name;
        }
    }
    return 'unknown';
}
```

### 7.2.8 Erros Comuns no Armazenamento de Senhas

```javascript
// ERRO 1: Usar hash com salt insuficiente
// O salt deve ter pelo menos 16 bytes de entropia
function badSalt() {
    const salt = crypto.randomBytes(4).toString('hex'); // APENAS 4 bytes!
    // Entropia insufficiente — apenas 2^32 valores possíveis
    // Um atacante pode pré-computar rainbow tables para cada salt possível
}

// ERRO 2: Usar pepper fixo hardcoded
const PEPPER = 'minha-pepper-secreta'; // ERRADO: hardcoded no código-fonte
// Se o código-fonte for comprometido, o pepper é exposto

// CORRETO: pepper em variável de ambiente ou HSM
const PEPPER = process.env.PEPPER; // Em variável de ambiente
const HMAC_PEPPER = crypto.createHmac('sha256', process.env.PEPPER_SECRET);

function secureHash(password, salt) {
    // Pepper: valor secreto NÃO armazenado no banco de dados
    const peppered = HMAC_PEPPER.update(password).digest('hex');
    // Salt: valor único por senha, armazenado junto ao hash
    return argon2.hash(peppered + salt, ARGON2_OPTIONS);
}

// ERRO 3: Comparação de timing variável
function insecureCompare(a, b) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
        if (a[i] !== b[i]) return false; // Retorna imediatamente em mismatch
        // Timing attack: atacante pode inferir caracteres corretos
    }
    return true;
}

// CORRETO: Comparação em tempo constante
const crypto = require('crypto');
function secureCompare(a, b) {
    try {
        return crypto.timingSafeEqual(
            Buffer.from(a),
            Buffer.from(b)
        );
    } catch {
        return false;
    }
}

// ERRO 4: Hash de hash (não aumenta segurança)
function doubleHash(password) {
    const first = crypto.createHash('sha256').update(password).digest('hex');
    return crypto.createHash('sha256').update(first).digest('hex');
    // Isso NÃO aumenta significativamente a segurança
    // SHA-256 é rápido demais — mesmo 100 iterações são triviais para GPU
}

// ERRO 5: Armazenar hash reversível
function reversibleMistake(password) {
    // AES encryption NÃO é hashing!
    // Se a chave de criptografia for comprometida, TODAS as senhas são expostas
    const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
    let encrypted = cipher.update(password, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
}
```

### 7.2.9 Verificação de Força de Senha

```javascript
class PasswordStrengthValidator {
    constructor(options = {}) {
        this.minLength = options.minLength || 12;
        this.maxLength = options.maxLength || 128;
        this.commonPasswords = options.commonPasswords || [];
        this.breachedPasswords = options.breachedPasswords || [];
    }

    validate(password) {
        const issues = [];

        if (password.length < this.minLength) {
            issues.push(`Password must be at least ${this.minLength} characters`);
        }

        if (password.length > this.maxLength) {
            issues.push(`Password must be at most ${this.maxLength} characters`);
        }

        if (!/[A-Z]/.test(password)) {
            issues.push('Password must contain at least one uppercase letter');
        }

        if (!/[a-z]/.test(password)) {
            issues.push('Password must contain at least one lowercase letter');
        }

        if (!/[0-9]/.test(password)) {
            issues.push('Password must contain at least one digit');
        }

        if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
            issues.push('Password must contain at least one special character');
        }

        // Verificar senhas comuns (top 100k do HaveIBeenPwned)
        if (this.commonPasswords.includes(password.toLowerCase())) {
            issues.push('Password is too common');
        }

        // Verificar contra listas de senhas vazadas (k-anonymity API)
        // Implementação usa apenas os 5 primeiros caracteres do SHA-1
        // (o serviço retorna hashes que começam com esse prefixo)
        // Não envia a senha completa ao serviço externo

        // Verificar padrões fracos
        if (/(.)\1{2,}/.test(password)) {
            issues.push('Password contains repeated characters');
        }

        if (/^[a-zA-Z]+$/.test(password)) {
            issues.push('Password should contain numbers or special characters');
        }

        if (/^[0-9]+$/.test(password)) {
            issues.push('Password should not be entirely numeric');
        }

        // Verificar sequências
        if (/(?:abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)/i.test(password)) {
            issues.push('Password contains sequential characters');
        }

        return {
            isValid: issues.length === 0,
            issues,
            score: this.calculateEntropy(password)
        };
    }

    calculateEntropy(password) {
        const charsetSize = this.getCharsetSize(password);
        return Math.floor(password.length * Math.log2(charsetSize));
    }

    getCharsetSize(password) {
        let size = 0;
        if (/[a-z]/.test(password)) size += 26;
        if (/[A-Z]/.test(password)) size += 26;
        if (/[0-9]/.test(password)) size += 10;
        if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) size += 32;
        return size || 1;
    }
}

// Verificação k-anonymity contra HaveIBeenPwned
async function checkPwnedPassword(password) {
    const sha1 = crypto.createHash('sha1')
        .update(password)
        .digest('hex')
        .toUpperCase();

    const prefix = sha1.substring(0, 5);
    const suffix = sha1.substring(5);

    const response = await fetch(`https://api.pwnedpasswords.com/range/${prefix}`);
    const text = await response.text();
    const lines = text.split('\n');

    for (const line of lines) {
        const [hashSuffix, count] = line.split(':');
        if (hashSuffix.trim() === suffix) {
            return parseInt(count.trim(), 10);
        }
    }

    return 0;
}
```

---

## 7.3 Autenticação Multifator (MFA)

### 7.3.1 Fatores de Autenticação

A autenticação multifator combina pelo menos dois fatores de tipos diferentes:

| Fator | Exemplo | Tipo |
|-------|---------|------|
| Algo que você sabe | Senha, PIN, frase secreta | Conhecimento |
| Algo que você possui | Token físico, smartphone, smartcard | Posse |
| Algo que você é | Biometria (digital, rosto, iris) | Inerência |
| Algo que você faz | Comportamento, geolocalização | Comportamento |

### 7.3.2 TOTP (Time-based One-Time Password)

TOTP é o MFA mais amplamente suportado, definido na RFC 6238. Gera códigos de 6 dígitos válidos por 30 segundos.

```javascript
const speakeasy = require('speakeasy');
const qrcode = require('qrcode');

// Gerar secreta TOTP para novo usuário
function generateTOTPSecret(userEmail, issuerName = 'DevSecurity') {
    const secret = speakeasy.generateSecret({
        name: `${issuerName}:${userEmail}`,
        issuer: issuerName,
        length: 32  // 256 bits de entropia
    });

    return {
        secret: secret.base32,  // Armazenar no banco
        otpauth_url: secret.otpauth_url  // Para gerar QR code
    };
}

// Gerar QR code para o usuário escanear
async function generateQRCode(otpauthUrl) {
    return await qrcode.toDataURL(otpauthUrl);
}

// Verificar código TOTP
function verifyTOTP(token, secret, window = 1) {
    // window = permite ±1 step (±30 segundos)
    // Reduz falsos negativos por desvio de relógio
    return speakeasy.totp.verify({
        secret: secret,
        encoding: 'base32',
        token: token,
        window: window
    });
}

// Gerar códigos de backup (recovery codes)
function generateRecoveryCodes(count = 10) {
    const codes = [];
    for (let i = 0; i < count; i++) {
        const code = speakeasy.generateSecret({ length: 20 }).base32;
        // Formato amigável: XXXX-XXXX-XXXX-XXXX
        const formatted = code.match(/.{1,4}/g).join('-');
        codes.push(formatted);
    }
    return codes;
}

// Hash dos recovery codes para armazenamento
async function hashRecoveryCodes(codes) {
    const hashed = [];
    for (const code of codes) {
        const hash = await argon2.hash(code.replace(/-/g, ''), ARGON2_OPTIONS);
        hashed.push(hash);
    }
    return hashed;
}
```

```python
# Python com pyotp
import pyotp
import qrcode
import io
import base64

def generate_totp_secret(user_email, issuer_name="DevSecurity"):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, name=user_email, issuer=issuer_name)
    return {
        "secret": secret,
        "provisioning_uri": totp.provisioning_uri(name=user_email, issuer_name=issuer_name)
    }

def generate_qr_code(provisioning_uri):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def verify_totp(token, secret, valid_window=1):
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=valid_window)
```

### 7.3.3 WebAuthn/FIDO2

WebAuthn é o padrão moderno para autenticação sem senhas, suportado por todos os navegadores principais. Usa chaves criográficas armazenadas em hardware (YubiKey, Touch ID, Windows Hello).

```javascript
// Registro WebAuthn com FIDO2 Server Library
const { Fido2Lib } = require('fido2-lib');

const fido2 = new Fido2Lib({
    timeout: 60000,
    rpId: 'example.com',
    rpName: 'DevSecurity Platform',
    rpIcon: 'https://example.com/logo.png',
    challengeSize: 128,
    attestation: 'direct',
    cryptoParams: [-7, -257],  // ES256 and RS256
    authenticatorAttachment: 'platform',
    authenticatorRequireResidentKey: false,
    authenticatorUserVerification: 'preferred'
});

// Passo 1: Iniciar registro
async function startRegistration(user) {
    const registrationOptions = await fido2.attestationOptions();

    // Armazenar challenge temporariamente
    await storeChallenge(user.id, registrationOptions.challenge);

    return {
        challenge: registrationOptions.challenge,
        rp: registrationOptions.rp,
        user: {
            id: user.id,
            name: user.email,
            displayName: user.displayName,
            icon: user.avatarUrl
        },
        pubKeyCredParams: registrationOptions.pubKeyCredParams,
        timeout: registrationOptions.timeout,
        attestation: registrationOptions.attestation,
        authenticatorSelection: {
            authenticatorAttachment: 'platform',
            userVerification: 'preferred'
        }
    };
}

// Passo 2: Completar registro
async function completeRegistration(attestationResponse, userId) {
    const expectedChallenge = await getStoredChallenge(userId);
    
    const authnResult = await fido2.attestationResult(attestationResponse, {
        challenge: expectedChallenge,
        origin: 'https://example.com',
        factor: 'either'
    });

    // Armazenar a chave pública do autenticador
    const credential = {
        credentialId: authnResult.authnrData.get('credId'),
        publicKey: authnResult.authnrData.get('credentialPublicKey'),
        counter: authnResult.authnrData.get('counter'),
        fmt: authnResult.authnrData.get('fmt'),
        userId: userId
    };

    await storeCredential(credential);
    return true;
}

// Passo 1: Iniciar autenticação
async function startAuthentication(userId) {
    const credentials = await getCredentialsByUserId(userId);
    const challenge = await fido2.challengeOptions();

    await storeChallenge(userId, challenge.challenge);

    return {
        challenge: challenge.challenge,
        timeout: challenge.timeout,
        rpId: challenge.rpId,
        allowCredentials: credentials.map(cred => ({
            type: 'public-key',
            id: cred.credentialId,
            transports: ['internal']
        })),
        userVerification: 'preferred'
    };
}

// Passo 2: Completar autenticação
async function completeAuthentication(assertionResponse, userId) {
    const expectedChallenge = await getStoredChallenge(userId);
    const storedCredential = await getCredentialById(assertionResponse.id);

    const authnResult = await fido2.assertionResult(assertionResponse, {
        challenge: expectedChallenge,
        origin: 'https://example.com',
        factor: 'either',
        publicKey: storedCredential.publicKey,
        prevCounter: storedCredential.counter,
        userHandle: userId
    });

    // Atualizar counter para prevenir replay
    await updateCredentialCounter(
        storedCredential.credentialId,
        authnResult.authnrData.get('counter')
    );

    return true;
}
```

### 7.3.4 SMS como Fator Secundário

SMS é o MFA mais acessível, mas significativamente menos seguro que TOTP ou WebAuthn. Deve ser considerado um fallback, não a primeira opção.

```javascript
const twilio = require('twilio');

class SMSMFAService {
    constructor(accountSid, authToken, fromNumber) {
        this.client = twilio(accountSid, authToken);
        this.fromNumber = fromNumber;
        this.codeLength = 6;
        this.codeExpiration = 300; // 5 minutos
    }

    async sendCode(phoneNumber) {
        const code = this.generateCode();
        const codeHash = await this.hashCode(code);
        
        // Armazenar hash do código com expiração
        await storeMFACode(phoneNumber, codeHash, Date.now() + this.codeExpiration * 1000);

        // Enviar SMS
        await this.client.messages.create({
            body: `Seu código de verificação é: ${code}. Ele expira em 5 minutos.`,
            from: this.fromNumber,
            to: phoneNumber
        });
    }

    async verifyCode(phoneNumber, code) {
        const stored = await getMFACode(phoneNumber);
        
        if (!stored) return false;
        if (Date.now() > stored.expiresAt) {
            await deleteMFACode(phoneNumber);
            return false;
        }

        // Comparação em tempo constante
        const isValid = crypto.timingSafeEqual(
            Buffer.from(await this.hashCode(code)),
            Buffer.from(stored.codeHash)
        );

        if (isValid) {
            await deleteMFACode(phoneNumber);
        }

        return isValid;
    }

    generateCode() {
        return crypto.randomInt(0, Math.pow(10, this.codeLength))
            .toString()
            .padStart(this.codeLength, '0');
    }

    async hashCode(code) {
        return crypto.createHash('sha256')
            .update(code + process.env.SMS_CODE_SALT)
            .digest('hex');
    }
}
```

**Riscos de SMS como MFA:**

| Ataque | Descrição | Mitigação |
|--------|-----------|-----------|
| SIM swapping | Atacante obtém controle do número | Notificar mudanças de SIM |
| SS7 attacks | Interceptação em nível de rede | Usar TOTP como alternativa |
| Phishing | Usuário é enganado a fornecer código | WebAuthn é phishing-resistant |
| Malware | Interceptação no dispositivo | HardWARE tokens |
| Social engineering | Manipulação do suporte | Políticas de verificação |
| VoIP exploitation | Interceptação de chamadas | Não usar números VoIP |

### 7.3.5 Fluxo de Setup MFA Completo

```javascript
// Express.js — Fluxo completo de setup MFA
const express = require('express');
const router = express.Router();

// Middleware de autenticação (requer login)
router.use(requireAuth);

// GET /mfa/status — Verificar status do MFA
router.get('/mfa/status', async (req, res) => {
    const user = await User.findById(req.user.id);
    res.json({
        totp_enabled: !!user.totpSecret,
        webauthn_enabled: user.webauthnCredentials.length > 0,
        sms_enabled: !!user.phoneNumber && !!user.phoneVerified,
        recovery_codes_remaining: user.recoveryCodes.filter(c => !c.used).length
    });
});

// POST /mfa/setup/totp — Iniciar setup TOTP
router.post('/mfa/setup/totp', async (req, res) => {
    const { secret, otpauth_url } = generateTOTPSecret(req.user.email);
    
    // Armazenar temporariamente (será ativado após verificação)
    await storePendingMFA(req.user.id, { totpSecret: secret });
    
    const qrCode = await generateQRCode(otpauth_url);
    const recoveryCodes = generateRecoveryCodes(10);
    
    // Hash dos recovery codes para armazenamento seguro
    const hashedCodes = await hashRecoveryCodes(recoveryCodes);
    await storePendingRecoveryCodes(req.user.id, hashedCodes);
    
    res.json({
        qr_code: qrCode,
        secret: secret,  // Mostrar apenas no setup inicial
        recovery_codes: recoveryCodes
    });
});

// POST /mfa/verify/totp — Verificar código e ativar TOTP
router.post('/mfa/verify/totp', async (req, res) => {
    const { token } = req.body;
    const pending = await getPendingMFA(req.user.id);
    
    if (!pending || !pending.totpSecret) {
        return res.status(400).json({ error: 'No pending TOTP setup' });
    }
    
    if (!verifyTOTP(token, pending.totpSecret)) {
        return res.status(400).json({ error: 'Invalid token' });
    }
    
    // Ativar TOTP
    await User.update(req.user.id, {
        totpSecret: pending.totpSecret,
        mfaEnabled: true
    });
    
    // Mover recovery codes para uso ativo
    await activateRecoveryCodes(req.user.id);
    
    // Limpar dados temporários
    await deletePendingMFA(req.user.id);
    
    res.json({ success: true });
});
```

---

## 7.4 OAuth 2.0: Fluxos de Autorização

### 7.4.1 Visão Geral do OAuth 2.0

OAuth 2.0 é um protocolo de **autorização**, não de autenticação. Permite que um usuário autorize uma aplicação terceira a acessar seus recursos sem compartilhar suas credenciais.

```
+--------+                               +---------------+
|        |--(A)- Redirecionar Login ----->|               |
|        |                               |  Resource     |
|        |<--(B)-- Credenciais Recurso --|  Owner        |
|        |                               |               |
|        |--(C)-- Autorizar ------------->|               |
|        |                               +---------------+
|        |                                     |
|        |<--(D)-- Grant Authorization -------|
|        |
|        |---(E)-- Trocar Grant por Token -->|
+--------+                                  |
    |                                        |
    |    +---------------+                   |
    |    |               |                   |
    |----| Authorization |<-(F)-- Token Req -|
         |     Server    |                   |
         |               |                   |
         +---------------+                   |
                                             |
         +---------------+                   |
         |               |<-(G)-- Token ----+|
         |  Resource     |                   |
         |     Server    |<-(H)-- Access ----|
         |               |       Token       |
         +---------------+                   |
```

### 7.4.2 Authorization Code Flow (o mais seguro)

O Authorization Code é o fluxo recomendado para aplicações server-side. O código de autorização é trocado por token no backend, nunca exposto ao navegador.

```javascript
// Express.js — OAuth 2.0 Authorization Code Flow

const express = require('express');
const crypto = require('crypto');
const axios = require('axios');
const router = express.Router();

const OAUTH_CONFIG = {
    authorizationEndpoint: 'https://provider.example.com/authorize',
    tokenEndpoint: 'https://provider.example.com/token',
    clientId: process.env.OAUTH_CLIENT_ID,
    clientSecret: process.env.OAUTH_CLIENT_SECRET,
    redirectUri: 'https://myapp.example.com/callback',
    scopes: ['openid', 'profile', 'email']
};

// Passo 1: Iniciar fluxo OAuth
router.get('/auth/login', (req, res) => {
    const state = crypto.randomBytes(32).toString('hex');
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = generateCodeChallenge(codeVerifier);
    
    // Armazenar state e code_verifier na sessão
    req.session.oauthState = state;
    req.session.codeVerifier = codeVerifier;
    
    const params = new URLSearchParams({
        response_type: 'code',
        client_id: OAUTH_CONFIG.clientId,
        redirect_uri: OAUTH_CONFIG.redirectUri,
        scope: OAUTH_CONFIG.scopes.join(' '),
        state: state,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256'
    });

    res.redirect(`${OAUTH_CONFIG.authorizationEndpoint}?${params}`);
});

// Passo 2: Callback após autorização
router.get('/callback', async (req, res) => {
    const { code, state, error } = req.query;

    // Validar state para prevenir CSRF
    if (!state || state !== req.session.oauthState) {
        return res.status(403).json({ error: 'Invalid state parameter' });
    }

    if (error) {
        return res.status(400).json({ error });
    }

    // Limpar state da sessão
    delete req.session.oauthState;

    try {
        // Passo 3: Trocar código por token
        const tokenResponse = await axios.post(OAUTH_CONFIG.tokenEndpoint, 
            new URLSearchParams({
                grant_type: 'authorization_code',
                code: code,
                redirect_uri: OAUTH_CONFIG.redirectUri,
                client_id: OAUTH_CONFIG.clientId,
                client_secret: OAUTH_CONFIG.clientSecret,
                code_verifier: req.session.codeVerifier
            }),
            {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            }
        );

        const { access_token, refresh_token, expires_in, id_token } = tokenResponse.data;

        // Armazenar tokens de forma segura
        req.session.accessToken = access_token;
        req.session.refreshToken = refresh_token;
        req.session.tokenExpiry = Date.now() + (expires_in * 1000);

        // Se OpenID Connect, validar ID token
        if (id_token) {
            const userInfo = await validateIDToken(id_token);
            req.session.user = userInfo;
        }

        delete req.session.codeVerifier;
        res.redirect('/dashboard');
    } catch (err) {
        console.error('Token exchange failed:', err.message);
        res.status(500).json({ error: 'Authentication failed' });
    }
});
```

### 7.4.3 PKCE (Proof Key for Code Exchange)

PKCE é uma extensão do Authorization Code que protege contra ataques de interceptação do código de autorização, especialmente importante para SPAs e apps móveis.

```javascript
const crypto = require('crypto');

function generateCodeVerifier() {
    // 32 bytes = 256 bits de entropia
    return crypto.randomBytes(32)
        .toString('base64url');
}

function generateCodeChallenge(codeVerifier) {
    return crypto.createHash('sha256')
        .update(codeVerifier)
        .digest('base64url');
}

// Fluxo completo com PKCE
async function initiateOAuthWithPKCE(userId) {
    const codeVerifier = generateCodeVerifier();
    const codeChallenge = generateCodeChallenge(codeVerifier);
    
    // Armazenar code_verifier associado ao usuário
    await storeCodeVerifier(userId, codeVerifier, Date.now() + 600000); // 10 min expiry
    
    return {
        authorizationUrl: buildAuthorizationUrl(codeChallenge),
        state: crypto.randomBytes(16).toString('hex')
    };
}

async function exchangeCodeForToken(code, userId) {
    const codeVerifier = await getCodeVerifier(userId);
    
    if (!codeVerifier) {
        throw new Error('No code verifier found — possible PKCE replay');
    }
    
    // Usar code_verifier na troca
    const response = await fetch(TOKEN_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type: 'authorization_code',
            code: code,
            client_id: CLIENT_ID,
            code_verifier: codeVerifier
        })
    });
    
    // Limpar code_verifier após uso
    await deleteCodeVerifier(userId);
    
    return response.json();
}
```

### 7.4.4 Client Credentials Flow

O Client Credentials é usado para server-to-server authentication, sem envolvimento do usuário.

```javascript
// Serviço que precisa acessar API de outro serviço
async function getServiceToken() {
    const response = await fetch('https://auth.example.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            grant_type: 'client_credentials',
            client_id: process.env.SERVICE_CLIENT_ID,
            client_secret: process.env.SERVICE_CLIENT_SECRET,
            scope: 'api:read api:write'
        })
    });

    if (!response.ok) {
        throw new Error('Client credentials authentication failed');
    }

    const data = await response.json();
    return {
        accessToken: data.access_token,
        expiresIn: data.expires_in,
        tokenType: data.token_type
    };
}

// Implementação do servidor OAuth
async function handleClientCredentialsGrant(req, res) {
    const { client_id, client_secret, scope } = req.body;

    // Validar client credentials
    const client = await Client.findByClientId(client_id);
    
    if (!client) {
        return res.status(401).json({
            error: 'invalid_client',
            error_description: 'Client not found'
        });
    }

    // Verificar secreta com timing-safe comparison
    const isValidSecret = crypto.timingSafeEqual(
        Buffer.from(client.clientSecret),
        Buffer.from(client_secret)
    );

    if (!isValidSecret) {
        // Incrementar contador de tentativas
        await client.incrementFailedAttempts();
        
        if (client.failedAttempts >= 5) {
            await client.lock();
            return res.status(429).json({
                error: 'invalid_client',
                error_description: 'Client locked due to too many failed attempts'
            });
        }
        
        return res.status(401).json({
            error: 'invalid_client',
            error_description: 'Invalid client credentials'
        });
    }

    // Validar escopo solicitado
    const grantedScopes = validateScopes(scope, client.allowedScopes);
    
    // Gerar token
    const token = generateAccessToken({
        sub: client.clientId,
        scope: grantedScopes,
        iss: 'https://auth.example.com',
        exp: Math.floor(Date.now() / 1000) + 3600
    });

    // Reset tentativas após sucesso
    await client.resetFailedAttempts();

    res.json({
        access_token: token,
        token_type: 'Bearer',
        expires_in: 3600,
        scope: grantedScopes
    });
}
```

---

## 7.5 OpenID Connect

### 7.5.1 OpenID Connect vs OAuth 2.0

OpenID Connect (OIDC) é uma camada de identidade sobre OAuth 2.0. Enquanto OAuth 2.0 lida com **autorização**, OIDC lida com **autenticação** — dizendo quem é o usuário.

| Conceito | OAuth 2.0 | OpenID Connect |
|----------|-----------|----------------|
| Propósito | Autorização | Autenticação + Autorização |
| Token principal | Access Token | ID Token (JWT) |
| UserInfo | Não padronizado | Endpoint padronizado |
| Escopos | Livre | openid (obrigatório) |
| Discoverability | Não | Well-known configuration |

### 7.5.2 ID Tokens

ID tokens são JWTs que contêm informações sobre a autenticação do usuário.

```javascript
// Estrutura de um ID Token (JWT)
// Header: { "alg": "RS256", "typ": "JWT", "kid": "key-id-123" }
// Payload: {
//   "iss": "https://auth.example.com",
//   "sub": "user-123",
//   "aud": "my-client-id",
//   "exp": 1700000000,
//   "iat": 1699996400,
//   "auth_time": 1699996400,
//   "nonce": "abc123",
//   "at_hash": "xyz789",
//   "name": "João Silva",
//   "email": "joao@example.com",
//   "email_verified": true
// }

// Validação de ID Token
const jose = require('jose');

async function validateIDToken(idToken, expectedNonce) {
    // Descobrir JWKS do provider
    const wellKnown = await fetch(
        'https://auth.example.com/.well-known/openid-configuration'
    ).then(r => r.json());

    const jwks = await fetch(wellKnown.jwks_uri).then(r => r.json());
    const keyStore = await jose.importJWK(jwks.keys[0]);

    // Validar token
    const { payload } = await jose.jwtVerify(idToken, keyStore, {
        issuer: wellKnown.issuer,
        audience: process.env.OAUTH_CLIENT_ID,
        maxTokenAge: '10m'  // Token não deve ser muito antigo
    });

    // Validar nonce
    if (payload.nonce !== expectedNonce) {
        throw new Error('Invalid nonce in ID token');
    }

    // Validar auth_time se max_age configurado
    const maxAge = 86400; // 24 horas
    if (payload.auth_time) {
        const authAge = Math.floor(Date.now() / 1000) - payload.auth_time;
        if (authAge > maxAge) {
            throw new Error('Authentication too old');
        }
    }

    return payload;
}
```

### 7.5.3 UserInfo Endpoint

```javascript
async function getUserInfo(accessToken) {
    const response = await fetch('https://auth.example.com/userinfo', {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });

    if (!response.ok) {
        throw new Error('Failed to fetch user info');
    }

    const userInfo = await response.json();
    
    // Mapear campos OIDC para modelo de usuário
    return {
        id: userInfo.sub,
        email: userInfo.email,
        name: userInfo.name,
        picture: userInfo.picture,
        emailVerified: userInfo.email_verified
    };
}

// Configuração well-known completa
async function discoverOIDCConfig(issuer) {
    const response = await fetch(`${issuer}/.well-known/openid-configuration`);
    
    if (!response.ok) {
        throw new Error(`Failed to discover OIDC config for ${issuer}`);
    }

    const config = await response.json();
    
    // Validar campos obrigatórios
    const required = [
        'issuer', 'authorization_endpoint', 'token_endpoint',
        'jwks_uri', 'response_types_supported'
    ];
    
    for (const field of required) {
        if (!config[field]) {
            throw new Error(`Missing required OIDC config field: ${field}`);
        }
    }

    return config;
}
```

### 7.5.4 Login com Google (Implementação Completa)

```javascript
const express = require('express');
const router = express.Router();
const { Issuer, generators } = require('openid-client');

let googleClient;

async function initGoogleAuth() {
    googleClient = await Issuer.discover('https://accounts.google.com');
    
    return new googleClient.Client({
        client_id: process.env.GOOGLE_CLIENT_ID,
        client_secret: process.env.GOOGLE_CLIENT_SECRET,
        redirect_uris: ['https://myapp.example.com/auth/google/callback'],
        response_types: ['code']
    });
}

router.get('/auth/google', async (req, res) => {
    const codeVerifier = generators.codeVerifier();
    const codeChallenge = generators.codeChallenge(codeVerifier);
    const state = generators.state();
    
    req.session.codeVerifier = codeVerifier;
    req.session.oauthState = state;
    
    const authUrl = googleClient.authorizationUrl({
        scope: 'openid email profile',
        state: state,
        code_challenge: codeChallenge,
        code_challenge_method: 'S256'
    });
    
    res.redirect(authUrl);
});

router.get('/auth/google/callback', async (req, res) => {
    try {
        const params = googleClient.callbackParams(req);
        
        const tokenSet = await googleClient.callback(
            'https://myapp.example.com/auth/google/callback',
            params,
            {
                code_verifier: req.session.codeVerifier,
                state: req.session.oauthState
            }
        );
        
        const userInfo = await googleClient.userinfo(tokenSet.access_token);
        
        // Criar ou atualizar usuário local
        let user = await User.findByEmail(userInfo.email);
        if (!user) {
            user = await User.create({
                email: userInfo.email,
                name: userInfo.name,
                avatar: userInfo.picture,
                provider: 'google',
                providerId: userInfo.sub
            });
        }
        
        // Criar sessão
        req.session.userId = user.id;
        req.session.authMethod = 'google';
        
        delete req.session.codeVerifier;
        delete req.session.oauthState;
        
        res.redirect('/dashboard');
    } catch (err) {
        console.error('Google auth error:', err);
        res.redirect('/login?error=auth_failed');
    }
});
```

---

## 7.6 Segurança de JWT

### 7.6.1 Estrutura de um JWT

Um JSON Web Token (RFC 7519) tem três partes: header, payload e signature, separadas por pontos.

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.
eyJpc3MiOiJodHRwczovL2F1dGguZXhhbXBsZS5jb20iLCJzdWIiOiIxMjM0NTY3ODkwIiwiYXVkIjoibXktYXBwLWlkIiwiZXhwIjoxNzAwMDAwMDAwfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 7.6.2 Vulnerabilidades Comuns em JWT

#### Confusão de Algoritmo (Algorithm Confusion)

A vulnerabilidade mais perigosa em implementações JWT. O atacante manipula o header `alg` para forçar verificação com chave pública ou sem verificação.

```javascript
// VULNERAVEL: Não validar o algoritmo
const jwt = require('jsonwebtoken');

function vulnerableVerify(token, publicKey) {
    // O atacante pode mudar "alg" de RS256 para HS256
    // e usar a chave PÚBLICA como HMAC secret
    // Como a chave pública é pública, o atacante pode forjar tokens
    return jwt.verify(token, publicKey); // NÃO valida o algoritmo!
}

// SEGURANÇO: Sempre validar o algoritmo
function secureVerify(token, publicKey, allowedAlgorithms = ['RS256']) {
    return jwt.verify(token, publicKey, {
        algorithms: allowedAlgorithms,  // SEMPRE especificar algoritmos permitidos
        issuer: 'https://auth.example.com',
        audience: 'my-app-id'
    });
}
```

```javascript
// Demonstra o ataque de confusão de algoritmo
const jwt = require('jsonwebtoken');

function demonstrateAttack() {
    // Par de chaves RSA
    const { privateKey, publicKey } = jwt.sign({}, '', { algorithm: 'RS256' });

    // Token legítimo assinado com RSA
    const legitimateToken = jwt.sign(
        { sub: 'user-123', role: 'user' },
        privateKey,
        { algorithm: 'RS256' }
    );

    // Atacante cria payload malicioso
    const maliciousPayload = {
        sub: 'admin',
        role: 'admin'
    };

    // Atacante muda "alg" para HS256
    // E assina com a chave PÚBLICA (que é conhecida)
    const maliciousHeader = {
        alg: 'HS256',  // Mudança de RS256 para HS256
        typ: 'JWT'
    };

    // Assinar com a chave pública como HMAC secret
    const maliciousToken = jwt.sign(
        maliciousPayload,
        publicKey,  // Chave pública usada como HMAC secret!
        { algorithm: 'HS256' }
    );

    // Se o servidor NÃO valida o algoritmo,
    // ele aceita o token malicioso porque:
    // 1. Verifica HMAC com a chave pública (que é pública)
    // 2. A assinatura é válida para HS256

    return maliciousToken;
}
```

#### Kid (Key ID) Injection

```javascript
// VULNERAVEL: Kid parameter usado diretamente em query
function vulnerableKeyLookup(kid) {
    // Se o kid for "knock-knock" ou similar:
    // jwt.verify() pode tentar ler arquivo "/dev/null" (vazio)
    // Resultando em verificação com chave vazia
    const keyPath = `/keys/${kid}.pem`;
    return fs.readFileSync(keyPath, 'utf8');
}

// SEGURANÇO: Validar kid contra lista permitida
function secureKeyLookup(kid, keys) {
    const allowedKids = new Set(keys.map(k => k.kid));
    
    if (!allowedKids.has(kid)) {
        throw new Error(`Unknown key ID: ${kid}`);
    }
    
    const key = keys.find(k => k.kid === kid);
    return key.publicKey;
}
```

### 7.6.3 Rotação de Chaves e JWKS

```javascript
const jose = require('jose');

class JWTKeyManager {
    constructor() {
        this.keys = new Map();
        this.currentKid = null;
    }

    async generateNewKeyPair() {
        const { publicKey, privateKey } = await jose.generateKeyPair('RS256', {
            modulusLength: 2048
        });

        const kid = crypto.randomUUID();
        
        this.keys.set(kid, {
            publicKey,
            privateKey,
            createdAt: Date.now(),
            active: false
        });

        return kid;
    }

    async activateKey(kid) {
        if (!this.keys.has(kid)) {
            throw new Error(`Key ${kid} not found`);
        }

        // Desativar chave anterior (mas não remover)
        if (this.currentKid) {
            this.keys.get(this.currentKid).active = false;
        }

        this.keys.get(kid).active = true;
        this.currentKid = kid;
    }

    // JWKS endpoint
    getJWKS() {
        const keys = [];
        for (const [kid, keyData] of this.keys) {
            // Usar JWK export em vez de JWKS
            const jwk = jose.exportJWK(keyData.publicKey);
            keys.push({ ...jwk, kid, use: 'sig' });
        }
        return { keys };
    }

    // Rotacionar chaves periodicamente
    async rotateKeys() {
        const newKid = await this.generateNewKeyPair();
        await this.activateKey(newKid);
        
        // Remover chaves antigas (manter por 24h para refresh tokens)
        const oneDayAgo = Date.now() - 86400000;
        for (const [kid, keyData] of this.keys) {
            if (kid !== this.currentKid && keyData.createdAt < oneDayAgo) {
                this.keys.delete(kid);
            }
        }
    }
}

// Middleware para servir JWKS
app.get('/.well-known/jwks.json', (req, res) => {
    res.json(keyManager.getJWKS());
});
```

### 7.6.4 Expiração e Invalidação

```javascript
class JWTTokenService {
    constructor(keyManager, options = {}) {
        this.keyManager = keyManager;
        this.accessTokenTTL = options.accessTokenTTL || 900; // 15 minutos
        this.refreshTokenTTL = options.refreshTokenTTL || 604800; // 7 dias
        this.issuer = options.issuer || 'https://auth.example.com';
    }

    async generateTokenPair(userId, scopes) {
        const currentKey = this.keyManager.getCurrentKey();
        
        const accessToken = await new jose.SignJWT({
            sub: userId,
            scope: scopes,
            typ: 'at'
        })
        .setProtectedHeader({ alg: 'RS256', kid: currentKey.kid })
        .setIssuedAt()
        .setIssuer(this.issuer)
        .setExpirationTime(this.accessTokenTTL)
        .setJti(crypto.randomUUID())  // ID único para invalidação
        .sign(currentKey.privateKey);

        const refreshToken = await new jose.SignJWT({
            sub: userId,
            typ: 'rt',
            family: crypto.randomUUID()  // Família de refresh tokens
        })
        .setProtectedHeader({ alg: 'RS256', kid: currentKey.kid })
        .setIssuedAt()
        .setIssuer(this.issuer)
        .setExpirationTime(this.refreshTokenTTL)
        .setJti(crypto.randomUUID())
        .sign(currentKey.privateKey);

        // Armazenar refresh token para invalidação
        await storeRefreshToken(userId, refreshToken, {
            family: this.getRefreshTokenFamily(refreshToken),
            expiresAt: Date.now() + (this.refreshTokenTTL * 1000)
        });

        return { accessToken, refreshToken, expiresIn: this.accessTokenTTL };
    }

    async refreshAccessToken(refreshToken, userId) {
        // Verificar se o refresh token está na blacklist
        const isBlacklisted = await isTokenBlacklisted(refreshToken);
        if (isBlacklisted) {
            // Possível uso de refresh token comprometido
            // Invalidar TODA a família de tokens
            await blacklistTokenFamily(refreshToken);
            throw new Error('Refresh token reuse detected');
        }

        // Verificar se o refresh token existe no banco
        const storedToken = await getRefreshToken(refreshToken);
        if (!storedToken) {
            throw new Error('Refresh token not found');
        }

        // Gerar novo par de tokens
        const newTokens = await this.generateTokenPair(userId, storedToken.scopes);

        // Blacklistar refresh token antigo (usado)
        await blacklistRefreshToken(refreshToken);

        return newTokens;
    }

    async revokeAllUserTokens(userId) {
        await revokeAllRefreshTokens(userId);
        // Access tokens são de curta duração e expiram naturalmente
        // Para invalidação imediata, usar token introspection
    }
}
```

### 7.6.5 Tabela Comparativa: JWT vs Sessions

| Aspecto | JWT | Server Sessions |
|---------|-----|-----------------|
| Armazenamento | Cliente (localStorage, cookie) | Servidor (Redis, DB) |
| Escalabilidade | Stateless — horizontal | Stateful — precisa shared store |
| Revogação | Difícil (blacklist) | Imediata (deletar sessão) |
| Tamanho | Cresce com claims | Fixed (session ID) |
| Segurança XSS | Vulnerável em localStorage | Protegido (httpOnly cookie) |
| Performance | Sem lookup no server | Lookup a cada request |
| Uso cross-domain | Nativo (CORS) | Complexo |
| Mobile/IoT | Ideal | Complexo |

---

## 7.7 Gerenciamento de Sessões

### 7.7.1 Modelos de Sessão

```javascript
// Express.js com sessões seguras
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const { createClient } = require('redis');

const redisClient = createClient({
    url: process.env.REDIS_URL,
    socket: {
        tls: true,
        rejectUnauthorized: true
    }
});

redisClient.connect();

const sessionConfig = {
    store: new RedisStore({
        client: redisClient,
        prefix: 'sess:',
        ttl: 3600  // 1 hora
    }),
    secret: process.env.SESSION_SECRET,
    name: '__Host-sessionId',  // Cookie name com prefixo seguro
    resave: false,
    saveUninitialized: false,
    rolling: true,  // Renovar expiração a cada request
    cookie: {
        secure: true,      // Apenas HTTPS
        httpOnly: true,    // Sem acesso via JavaScript
        sameSite: 'strict', // Proteção contra CSRF
        maxAge: 3600000,   // 1 hora em milissegundos
        domain: 'example.com', // Especificar domínio
        path: '/'          // Path restrito
    }
};

app.use(session(sessionConfig));
```

### 7.7.2 Prevenção de Session Fixation

Session fixation ocorre quando o atacante define um session ID conhecido antes do login do usuário. Após o login, o atacante usa o mesmo session ID para acessar a conta.

```javascript
// Prevenção de session fixation: regenerar session ID após login
async function secureLogin(req, username, password) {
    const user = await User.findByUsername(username);
    if (!user) {
        // Rate limiting para prevenir enumeration
        await incrementLoginAttempts(req.ip);
        throw new Error('Invalid credentials');
    }

    const isValid = await verifyPassword(password, user.passwordHash);
    if (!isValid) {
        await incrementLoginAttempts(req.ip);
        throw new Error('Invalid credentials');
    }

    // REGENERAR session ID — passo crítico!
    // Isso invalida qualquer session ID que o atacante possa ter definido
    await new Promise((resolve, reject) => {
        req.session.regenerate((err) => {
            if (err) reject(err);
            resolve();
        });
    });

    // Armazenar dados do usuário na nova sessão
    req.session.userId = user.id;
    req.session.authenticatedAt = Date.now();
    req.session.authMethod = 'password';
    req.session.ip = req.ip;
    req.session.userAgent = req.headers['user-agent'];

    // Salvar explicitamente
    await new Promise((resolve, reject) => {
        req.session.save((err) => {
            if (err) reject(err);
            resolve();
        });
    });

    return user;
}

// Verificar integridade da sessão
function requireAuth(req, res, next) {
    if (!req.session.userId) {
        return res.status(401).json({ error: 'Authentication required' });
    }

    // Verificar se a sessão não foi comprometida
    if (req.session.ip !== req.ip) {
        // IP mudou durante a sessão — possível session hijacking
        console.warn(`Session IP mismatch: ${req.session.userId} from ${req.ip}`);
        req.session.destroy();
        return res.status(401).json({ error: 'Session invalidated' });
    }

    // Verificar User-Agent
    if (req.session.userAgent !== req.headers['user-agent']) {
        console.warn(`Session UA mismatch: ${req.session.userId}`);
        req.session.destroy();
        return res.status(401).json({ error: 'Session invalidated' });
    }

    // Verificar expiração de atividade
    const maxInactiveTime = 1800000; // 30 minutos
    if (Date.now() - req.session.lastActivity > maxInactiveTime) {
        req.session.destroy();
        return res.status(401).json({ error: 'Session expired' });
    }

    req.session.lastActivity = Date.now();
    next();
}
```

### 7.7.3 Session Fixation com OAuth

```javascript
// Prevenção de session fixation em fluxos OAuth
router.get('/auth/callback', async (req, res) => {
    // Validar state
    if (req.query.state !== req.session.oauthState) {
        return res.status(403).json({ error: 'CSRF detected' });
    }

    // Trocar código por token
    const tokens = await exchangeCodeForToken(req.query.code);
    const userInfo = await getUserInfo(tokens.access_token);

    // REGENERAR sessão — mesmo padrão do login normal
    await new Promise((resolve, reject) => {
        req.session.regenerate((err) => {
            if (err) reject(err);
            resolve();
        });
    });

    // Criar ou buscar usuário
    let user = await User.findByEmail(userInfo.email);
    if (!user) {
        user = await User.create({
            email: userInfo.email,
            name: userInfo.name,
            provider: 'oauth'
        });
    }

    // Configurar nova sessão
    req.session.userId = user.id;
    req.session.authenticatedAt = Date.now();
    req.session.authMethod = 'oauth';
    req.session.ip = req.ip;
    req.session.userAgent = req.headers['user-agent'];

    // Limpar dados temporários OAuth
    delete req.session.oauthState;
    delete req.session.codeVerifier;

    await req.session.save();
    res.redirect('/dashboard');
});
```

### 7.7.4 Invalidação de Sessão

```javascript
// Logout seguro
router.post('/logout', requireAuth, async (req, res) => {
    const sessionId = req.sessionID;
    
    // Destruir sessão
    await new Promise((resolve) => {
        req.session.destroy((err) => {
            if (err) console.error('Session destroy error:', err);
            resolve();
        });
    });

    // Limpar cookie
    res.clearCookie('__Host-sessionId', {
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'strict'
    });

    // Adicionar à blacklist (para invalidação de tokens)
    await blacklistSession(sessionId);

    res.json({ success: true });
});

// Logout de todas as sessões
router.post('/logout-all', requireAuth, async (req, res) => {
    const userId = req.session.userId;
    
    // Destruir todas as sessões do usuário
    await destroyAllUserSessions(userId);
    
    // Destruir sessão atual
    await new Promise((resolve) => {
        req.session.destroy(resolve);
    });

    res.clearCookie('__Host-sessionId', {
        path: '/',
        secure: true,
        httpOnly: true,
        sameSite: 'strict'
    });

    res.json({ success: true, message: 'All sessions invalidated' });
});
```

---

## 7.8 Cookie-based vs Token-based Authentication

### 7.8.1 Autenticação Baseada em Cookies

```javascript
// Configuração de cookies seguros para sessão
const secureCookieOptions = {
    httpOnly: true,      // Protege contra XSS
    secure: true,        // Apenas HTTPS
    sameSite: 'strict',  // Protege contra CSRF
    path: '/',
    maxAge: 3600000,     // 1 hora
    domain: 'example.com'
};

// Cookie prefix para garantir propriedades de segurança
// __Host-: força secure, httpOnly, path=/ e sem domain
// __Secure-: força secure (permite httpOnly e domain)
const cookieName = '__Host-session';

app.set('trust proxy', 1);  // Confiar em proxy reverso

// Configurar cookie com prefixo seguro
app.use(session({
    name: cookieName,
    secret: process.env.SESSION_SECRET,
    cookie: {
        secure: true,
        httpOnly: true,
        sameSite: 'strict',
        path: '/'
    }
}));
```

### 7.8.2 Autenticação Baseada em Tokens

```javascript
// Middleware para autenticação baseada em token
function tokenAuthMiddleware(req, res, next) {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Missing authorization header' });
    }

    const token = authHeader.substring(7);

    try {
        const decoded = jwt.verify(token, publicKey, {
            algorithms: ['RS256'],
            issuer: 'https://auth.example.com'
        });

        // Verificar blacklist
        if (isTokenBlacklisted(decoded.jti)) {
            return res.status(401).json({ error: 'Token revoked' });
        }

        req.user = {
            id: decoded.sub,
            scopes: decoded.scope ? decoded.scope.split(' ') : []
        };

        next();
    } catch (err) {
        if (err.name === 'TokenExpiredError') {
            return res.status(401).json({ error: 'Token expired' });
        }
        return res.status(401).json({ error: 'Invalid token' });
    }
}

// Refresh token endpoint
router.post('/token/refresh', async (req, res) => {
    const { refreshToken } = req.body;

    if (!refreshToken) {
        return res.status(400).json({ error: 'Missing refresh token' });
    }

    try {
        const decoded = jwt.verify(refreshToken, publicKey, {
            algorithms: ['RS256'],
            issuer: 'https://auth.example.com'
        });

        // Verificar se o refresh token não está na blacklist
        if (await isRefreshTokenBlacklisted(decoded.jti)) {
            // Token foi reutilizado — possível comprometimento
            await revokeRefreshTokenFamily(decoded.sub);
            return res.status(401).json({ error: 'Refresh token reuse detected' });
        }

        // Gerar novos tokens
        const newTokens = await generateTokenPair(decoded.sub, decoded.scope);

        // Blacklistar refresh token antigo
        await blacklistRefreshToken(decoded.jti);

        res.json(newTokens);
    } catch (err) {
        return res.status(401).json({ error: 'Invalid refresh token' });
    }
});
```

### 7.8.3 Comparação Completa

| Critério | Cookies | Tokens (Bearer) |
|----------|---------|-----------------|
| Proteção XSS | Excelente (httpOnly) | Ruim (localStorage) |
| Proteção CSRF | Necessário (SameSite) | Nativa |
| Mobile support | Complexo | Excelente |
| Cross-origin | Limitado | Nativo |
| Escalabilidade | Stateful | Stateless |
| Revogação | Imediata | Complexa |
| Complexidade | Baixa | Média |
| API-first | Não | Sim |

---

## 7.9 Proteção contra Brute Force

### 7.9.1 Rate Limiting

```javascript
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');

// Rate limiting global
const globalLimiter = rateLimit({
    store: new RedisStore({
        sendCommand: (...args) => redisClient.sendCommand(args),
    }),
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 100, // 100 requests por janela
    standardHeaders: true,
    legacyHeaders: false,
    message: {
        error: 'Too many requests',
        retryAfter: '15 minutes'
    }
});

// Rate limiting para login (mais restritivo)
const loginLimiter = rateLimit({
    store: new RedisStore({
        sendCommand: (...args) => redisClient.sendCommand(args),
    }),
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 5, // 5 tentativas por janela
    skipSuccessfulRequests: true, // Não contar logins bem-sucedidos
    keyGenerator: (req) => {
        // Rate limit por IP + username para prevenir distributed attacks
        return `login:${req.ip}:${req.body.username}`;
    },
    message: {
        error: 'Too many login attempts',
        retryAfter: '15 minutes'
    }
});

// Rate limiting para reset de senha
const passwordResetLimiter = rateLimit({
    store: new RedisStore({
        sendCommand: (...args) => redisClient.sendCommand(args),
    }),
    windowMs: 60 * 60 * 1000, // 1 hora
    max: 3, // 3 solicitações por hora
    keyGenerator: (req) => `reset:${req.ip}:${req.body.email}`,
    message: {
        error: 'Too many password reset requests',
        retryAfter: '1 hour'
    }
});

app.use(globalLimiter);
app.use('/auth/login', loginLimiter);
app.use('/auth/password-reset', passwordResetLimiter);
```

### 7.9.2 Account Lockout

```javascript
class AccountLockoutService {
    constructor(redisClient, options = {}) {
        this.redis = redisClient;
        this.maxAttempts = options.maxAttempts || 5;
        this.lockoutDuration = options.lockoutDuration || 900; // 15 minutos
        this.incrementWindow = options.incrementWindow || 300; // 5 minutos
    }

    async recordFailedAttempt(identifier) {
        const key = `lockout:${identifier}`;
        const attempts = await this.redis.incr(key);
        
        if (attempts === 1) {
            await this.redis.expire(key, this.incrementWindow);
        }

        return attempts;
    }

    async isLockedOut(identifier) {
        const key = `lockout:${identifier}`;
        const attempts = await this.redis.get(key);
        
        if (!attempts) return false;
        
        if (parseInt(attempts) >= this.maxAttempts) {
            const ttl = await this.redis.ttl(key);
            if (ttl <= 0) {
                await this.redis.del(key);
                return false;
            }
            return {
                locked: true,
                remainingTime: ttl,
                message: `Account locked. Try again in ${Math.ceil(ttl / 60)} minutes.`
            };
        }

        return false;
    }

    async resetAttempts(identifier) {
        await this.redis.del(`lockout:${identifier}`);
    }

    async manualLockout(identifier, duration) {
        const key = `lockout:${identifier}`;
        await this.redis.set(key, this.maxAttempts + 1, 'EX', duration || this.lockoutDuration);
    }

    async manualUnlock(identifier) {
        await this.redis.del(`lockout:${identifier}`);
    }
}

// Uso no fluxo de login
async function handleLogin(req, res) {
    const { username, password } = req.body;
    const identifier = `${req.ip}:${username}`;

    // Verificar lockout
    const lockoutStatus = await lockoutService.isLockedOut(identifier);
    if (lockoutStatus && lockoutStatus.locked) {
        return res.status(429).json({
            error: 'Account temporarily locked',
            message: lockoutStatus.message,
            retryAfter: lockoutStatus.remainingTime
        });
    }

    try {
        const user = await User.findByUsername(username);
        
        if (!user) {
            // Username não existe — usar timing constante
            // para prevenir user enumeration
            await bcrypt.hash(password, 12);
            await lockoutService.recordFailedAttempt(identifier);
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const isValid = await bcrypt.compare(password, user.passwordHash);
        
        if (!isValid) {
            const attempts = await lockoutService.recordFailedAttempt(identifier);
            
            if (attempts >= 5) {
                // Enviar notificação ao usuário
                await notifyAccountLockout(user);
                return res.status(429).json({
                    error: 'Account temporarily locked',
                    message: `Too many failed attempts. Account locked for ${this.lockoutDuration / 60} minutes.`
                });
            }

            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Login bem-sucedido — resetar tentativas
        await lockoutService.resetAttempts(identifier);
        
        // Criar sessão
        await createUserSession(req, user);

        res.json({ success: true });
    } catch (err) {
        console.error('Login error:', err);
        res.status(500).json({ error: 'Internal server error' });
    }
}
```

### 7.9.3 CAPTCHA

```javascript
// Integração com reCAPTCHA v3
const axios = require('axios');

async function verifyRecaptcha(token, remoteip) {
    const response = await axios.post('https://www.google.com/recaptcha/api/siteverify', 
        new URLSearchParams({
            secret: process.env.RECAPTCHA_SECRET_KEY,
            response: token,
            remoteip: remoteip
        })
    );

    const data = response.data;
    
    return {
        success: data.success,
        score: data.score, // 0.0 (bot) a 1.0 (human)
        action: data.action,
        errorCodes: data['error-codes'] || []
    };
}

// Middleware de CAPTCHA condicional
async function captchaMiddleware(req, res, next) {
    const identifier = req.ip;
    const attempts = await getLoginAttempts(identifier);

    // Mostrar CAPTCHA após 3 tentativas falhas
    if (attempts >= 3) {
        const captchaToken = req.headers['x-captcha-token'];
        
        if (!captchaToken) {
            return res.status(400).json({
                error: 'CAPTCHA required',
                captchaRequired: true
            });
        }

        const result = await verifyRecaptcha(captchaToken, req.ip);
        
        if (!result.success || result.score < 0.5) {
            return res.status(400).json({
                error: 'CAPTCHA verification failed'
            });
        }
    }

    next();
}
```

---

## 7.10 Prevenção de Credential Stuffing

### 7.10.1 Entendendo o Attack

Credential stuffing é um ataque automatizado onde atacantes usam credenciais vazadas de outros sites para tentar acessar contas. Funciona porque muitos usuários reutilizam senhas.

```
Vazamento Site A: usuario@email.com:senha123
                            |
                            v
Atacante cria listas de: email:senha
                            |
                            v
Script automatizado tenta login em Site B, Site C, Site D...
                            |
                            v
Taxa de sucesso: 0.1-3% (suficiente para milhares de contas)
```

### 7.10.2 Defesas

```javascript
class CredentialStuffingDefense {
    constructor(redisClient) {
        this.redis = redisClient;
    }

    // 1. Detecção de padrões de login anômalos
    async detectAnomalousLogin(userId, loginInfo) {
        const history = await this.getLoginHistory(userId);
        
        const anomalies = [];

        // Verificar se o IP é novo
        if (!history.knownIPs.includes(loginInfo.ip)) {
            anomalies.push('new_ip');
        }

        // Verificar se o User-Agent é novo
        if (!history.knownUserAgents.includes(loginInfo.userAgent)) {
            anomalies.push('new_user_agent');
        }

        // Verificar geolocalização impossível
        if (history.lastLogin) {
            const timeDiff = Date.now() - history.lastLogin.timestamp;
            const geoDiff = this.calculateGeoDistance(
                history.lastLogin.location,
                loginInfo.location
            );
            
            // Se a distância / tempo > 900 km/h, é fisicamente impossível
            if (geoDiff / (timeDiff / 3600000) > 900) {
                anomalies.push('impossible_travel');
            }
        }

        // Verificar padrão de horário
        const hour = new Date().getHours();
        const typicalHours = history.loginHours || [];
        if (typicalHours.length > 10 && !typicalHours.includes(hour)) {
            anomalies.push('unusual_hour');
        }

        return {
            isAnomalous: anomalies.length > 0,
            anomalies,
            riskScore: this.calculateRiskScore(anomalies)
        };
    }

    // 2. Bloqueio temporário por padrão de tentativas
    async detectCredentialStuffingPattern(identifier) {
        const pattern = await this.redis.get(`pattern:${identifier}`);
        
        if (!pattern) return null;

        const parsed = JSON.parse(pattern);
        
        // Se há muitas tentativas em pouco tempo com usernames diferentes
        if (parsed.uniqueUsernames > 50 && parsed.window < 300) {
            return {
                type: 'credential_stuffing',
                confidence: 'high',
                action: 'block_ip'
            };
        }

        // Se há tentativas com padrão de user-agent rotativo
        if (parsed.uniqueUserAgents > 10 && parsed.window < 60) {
            return {
                type: 'bot_activity',
                confidence: 'medium',
                action: 'require_captcha'
            };
        }

        return null;
    }

    // 3. Honeypot fields
    checkHoneypot(req) {
        // Campo invisível que preenchesse só bots
        if (req.body.website || req.body.fax_number) {
            return {
                isBot: true,
                action: 'silent_reject'
            };
        }
        return { isBot: false };
    }

    // 4. Verificação contra senhas vazadas
    async checkAgainstBreachedPasswords(password) {
        const sha1 = crypto.createHash('sha1')
            .update(password)
            .digest('hex')
            .toUpperCase();

        const prefix = sha1.substring(0, 5);
        const suffix = sha1.substring(5);

        const response = await fetch(
            `https://api.pwnedpasswords.com/range/${prefix}`
        );
        const text = await response.text();

        for (const line of text.split('\n')) {
            const [hash, count] = line.split(':');
            if (hash.trim() === suffix) {
                return parseInt(count.trim(), 10);
            }
        }

        return 0;
    }

    calculateRiskScore(anomalies) {
        const weights = {
            new_ip: 0.3,
            new_user_agent: 0.2,
            impossible_travel: 0.8,
            unusual_hour: 0.1
        };

        let score = 0;
        for (const anomaly of anomalies) {
            score += weights[anomaly] || 0.1;
        }

        return Math.min(score, 1.0);
    }

    calculateGeoDistance(loc1, loc2) {
        // Fórmula de Haversine
        const R = 6371; // Raio da Terra em km
        const dLat = (loc2.lat - loc1.lat) * Math.PI / 180;
        const dLon = (loc2.lon - loc1.lon) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
                  Math.cos(loc1.lat * Math.PI / 180) *
                  Math.cos(loc2.lat * Math.PI / 180) *
                  Math.sin(dLon / 2) ** 2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }
}
```

---

## 7.11 Fluxo de Reset de Senha Seguro

### 7.11.1 Requisitos de Segurança

```javascript
class PasswordResetService {
    constructor(options = {}) {
        this.tokenLength = options.tokenLength || 32;
        this.tokenExpiry = options.tokenExpiry || 3600000; // 1 hora
        this.maxRequests = options.maxRequests || 3;
        this.requestWindow = options.requestWindow || 3600000; // 1 hora
    }

    // Solicitar reset de senha
    async requestReset(email) {
        // 1. Rate limiting — prevenir enumeração e abuso
        const rateLimitKey = `reset_request:${email}`;
        const requests = await redis.incr(rateLimitKey);
        if (requests === 1) {
            await redis.expire(rateLimitKey, this.requestWindow / 1000);
        }

        if (requests > this.maxRequests) {
            // Retornar resposta genérica (não revelar se email existe)
            return {
                message: 'If an account with that email exists, a reset link has been sent.',
                // NÃO adicionar delay intencional aqui — revela existência
            };
        }

        // 2. Buscar usuário (silenciosamente)
        const user = await User.findByEmail(email);

        // 3. SEMPRE retornar a mesma mensagem
        const responseMessage = 'If an account with that email exists, a reset link has been sent.';

        if (!user) {
            // Email não existe — mas retornar mesma mensagem
            return { message: responseMessage };
        }

        // 4. Invalidar tokens anteriores do mesmo usuário
        await invalidateAllResetTokens(user.id);

        // 5. Gerar token criptograficamente seguro
        const token = crypto.randomBytes(this.tokenLength).toString('hex');
        
        // 6. Hash do token para armazenamento
        const tokenHash = crypto.createHash('sha256')
            .update(token)
            .digest('hex');

        // 7. Armazenar hash com expiração
        await storeResetToken(user.id, tokenHash, {
            expiresAt: Date.now() + this.tokenExpiry,
            ipAddress: null, // Será preenchido no uso
            userAgent: null,
            used: false
        });

        // 8. Enviar email com token (não o hash!)
        await sendPasswordResetEmail(user.email, token);

        // 9. Log de segurança (sem dados sensíveis)
        await logSecurityEvent('password_reset_requested', {
            userId: user.id,
            ip: null
        });

        return { message: responseMessage };
    }

    // Confirmar reset de senha
    async confirmReset(token, newPassword, requestInfo) {
        // 1. Hash do token recebido
        const tokenHash = crypto.createHash('sha256')
            .update(token)
            .digest('hex');

        // 2. Buscar token no banco
        const storedToken = await getResetToken(tokenHash);

        if (!storedToken) {
            return { success: false, error: 'Invalid or expired token' };
        }

        // 3. Verificar expiração
        if (Date.now() > storedToken.expiresAt) {
            await deleteResetToken(tokenHash);
            return { success: false, error: 'Token expired' };
        }

        // 4. Verificar se já foi usado
        if (storedToken.used) {
            // TOKEN REUTILIZADO — possivelmente comprometido!
            await invalidateAllResetTokens(storedToken.userId);
            await logSecurityEvent('password_reset_token_reuse', {
                userId: storedToken.userId,
                ip: requestInfo.ip
            });
            return { success: false, error: 'Token already used' };
        }

        // 5. Validar força da nova senha
        const validator = new PasswordStrengthValidator({
            minLength: 12,
            commonPasswords: await getCommonPasswords()
        });

        const validation = validator.validate(newPassword);
        if (!validation.isValid) {
            return {
                success: false,
                error: 'Password does not meet requirements',
                issues: validation.issues
            };
        }

        // 6. Verificar se a nova senha é diferente da atual
        const user = await User.findById(storedToken.userId);
        const isSamePassword = await bcrypt.compare(newPassword, user.passwordHash);
        if (isSamePassword) {
            return {
                success: false,
                error: 'New password must be different from current password'
            };
        }

        // 7. Atualizar senha
        const newHash = await bcrypt.hash(newPassword, 12);
        await User.updatePassword(user.id, newHash);

        // 8. Marcar token como usado
        await markTokenUsed(tokenHash, requestInfo);

        // 9. Invalidar todas as sessões do usuário
        await destroyAllUserSessions(user.id);

        // 10. Enviar email de notificação
        await sendPasswordChangedNotification(user.email, requestInfo.ip);

        // 11. Log de segurança
        await logSecurityEvent('password_reset_completed', {
            userId: user.id,
            ip: requestInfo.ip
        });

        return { success: true };
    }
}
```

### 7.11.2 Template de Email de Reset

```html
<!-- Nunca incluir a senha no email! -->
<!-- Token deve expirar em no máximo 24 horas -->
<!-- Usar HTTPS no link de reset -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redefinir Senha</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>Redefinir sua senha</h2>
    <p>Olá,</p>
    <p>Você solicitou a redefinição da sua senha no DevSecurity Platform.</p>
    <p>Clique no botão abaixo para criar uma nova senha:</p>
    
    <a href="https://app.example.com/reset-password?token={{TOKEN}}"
       style="display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px;">
        Redefinir Senha
    </a>
    
    <p style="margin-top: 20px; color: #666;">
        Este link expira em 1 hora. Se você não solicitou esta redefinição, 
        ignore este email — sua senha permanecerá segura.
    </p>
    
    <p style="color: #666;">
        <strong>Nunca compartilhe este link com ninguém.</strong>
    </p>
    
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
    <p style="font-size: 12px; color: #999;">
        DevSecurity Platform | Esta é uma mensagem automática
    </p>
</body>
</html>
```

---

## 7.12 Segurança de Remember-Me Tokens

### 7.12.1 Implementação Segura

```javascript
class RememberMeService {
    constructor(options = {}) {
        this.tokenLength = options.tokenLength || 64;
        this.tokenExpiry = options.tokenExpiry || 2592000000; // 30 dias
        this.maxTokens = options.maxTokens || 5; // Max tokens por usuário
    }

    async createRememberMeToken(userId, responseInfo) {
        // 1. Gerar token aleatório
        const token = crypto.randomBytes(this.tokenLength).toString('hex');
        
        // 2. Hash do token para armazenamento
        const tokenHash = crypto.createHash('sha256')
            .update(token)
            .digest('hex');

        // 3. Verificar limite de tokens ativos
        const activeTokens = await getActiveRememberMeTokens(userId);
        if (activeTokens.length >= this.maxTokens) {
            // Remover o mais antigo
            await revokeRememberMeToken(activeTokens[0].tokenHash);
        }

        // 4. Armazenar hash com metadados
        await storeRememberMeToken(userId, tokenHash, {
            expiresAt: Date.now() + this.tokenExpiry,
            userAgent: responseInfo.userAgent,
            ip: responseInfo.ip,
            createdAt: Date.now()
        });

        // 5. Retornar token para setar no cookie
        return token;
    }

    async verifyRememberMeToken(token, requestInfo) {
        // 1. Hash do token recebido
        const tokenHash = crypto.createHash('sha256')
            .update(token)
            .digest('hex');

        // 2. Buscar token
        const storedToken = await getRememberMeToken(tokenHash);

        if (!storedToken) {
            return { valid: false, reason: 'token_not_found' };
        }

        // 3. Verificar expiração
        if (Date.now() > storedToken.expiresAt) {
            await revokeRememberMeToken(tokenHash);
            return { valid: false, reason: 'token_expired' };
        }

        // 4. Verificar se o token não foi revogado
        if (storedToken.revoked) {
            // Possível uso indevido — revogar todos os tokens do usuário
            await revokeAllUserRememberMeTokens(storedToken.userId);
            await logSecurityEvent('remember_me_token_reuse', {
                userId: storedToken.userId,
                ip: requestInfo.ip
            });
            return { valid: false, reason: 'token_revoked' };
        }

        // 5. Verificar User-Agent (detecção de sequestro)
        if (storedToken.userAgent !== requestInfo.userAgent) {
            // User-Agent diferente — possivelmente comprometido
            await revokeRememberMeToken(tokenHash);
            await logSecurityEvent('remember_me_token_ua_mismatch', {
                userId: storedToken.userId,
                expectedUA: storedToken.userAgent,
                actualUA: requestInfo.userAgent
            });
            return { valid: false, reason: 'ua_mismatch' };
        }

        // 6. Rotacionar token (usar uma vez)
        await revokeRememberMeToken(tokenHash);

        return {
            valid: true,
            userId: storedToken.userId
        };
    }

    async revokeRememberMeToken(tokenHash) {
        await redis.del(`rememberme:${tokenHash}`);
    }

    async revokeAllUserRememberMeTokens(userId) {
        const tokens = await getActiveRememberMeTokens(userId);
        for (const token of tokens) {
            await revokeRememberMeToken(token.tokenHash);
        }
    }
}

// Configuração do cookie de remember-me
function setRememberMeCookie(res, token) {
    res.cookie('remember_me', token, {
        httpOnly: true,
        secure: true,
        sameSite: 'strict',
        maxAge: 2592000000, // 30 dias
        path: '/',
        signed: true
    });
}

// Middleware de remember-me
async function rememberMeMiddleware(req, res, next) {
    if (!req.session.userId && req.signedCookies.remember_me) {
        const result = await rememberMeService.verifyRememberMeToken(
            req.signedCookies.remember_me,
            { userAgent: req.headers['user-agent'], ip: req.ip }
        );

        if (result.valid) {
            // Criar nova sessão
            req.session.userId = result.userId;
            req.session.authenticatedAt = Date.now();
            req.session.authMethod = 'remember_me';

            // Gerar novo remember-me token
            const newToken = await rememberMeService.createRememberMeToken(
                result.userId,
                { userAgent: req.headers['user-agent'], ip: req.ip }
            );
            setRememberMeCookie(res, newToken);
        }
    }

    next();
}
```

---

## 7.13 CVE-2019-11510 — Pulse Secure VPN Authentication Bypass

### 7.13.1 Resumo da Vulnerabilidade

**CVE-2019-11510** é uma vulnerabilidade de severity **CRITICAL** (CVSS 10.0) no Pulse Secure SSL VPN que permite bypass completo de autenticação. Um atacante não autenticado pode acessar任意 arquivos no sistema, incluindo chaves de sessão e credenciais.

- **Produto afetado**: Pulse Secure SSL VPN (versions 8.2R1.1 a 8.2R11.3, 8.3R1.1 a 8.3R7.3, 9.0R1 a 9.0R3.5)
- **Data de disclosure**: Abril 2019
- **CVSS**: 10.0 (Critical)
- **Tipo**: Path Traversal resultando em Authentication Bypass

### 7.13.2 Mecanismo do Ataque

A vulnerabilidade é uma path traversal que permite leitura arbitrária de arquivos:

```
GET /dana-na/../dana/html5acc/guacamole/../../../../../../etc/passwd HTTP/1.1
Host: vpn.example.com

GET /dana-na/../dana/html5acc/guacamole/../../../../../../data/screenshots/ HTTP/1.1

GET /dana-na/../dana/html5acc/guacamole/../../../../../../data/logs/login%00log HTTP/1.1
```

O atacante pode ler:
- Arquivos de configuração do sistema
- Chaves de sessão de outros usuários
- Credenciais armazenadas em texto claro
- Certificados SSL VPN
- Logs de autenticação com senhas

### 7.13.3 Código Vulnerável e Correção

```python
# Código VULNERAVEL (conceitual) — Path traversal no处理 de autenticação
import os
from flask import Flask, request, abort

app = Flask(__name__)

@app.route('/dana-na/<path:resource>')
def handle_resource(resource):
    # VULNERAVEL: O path não é sanitizado
    # Um atacante pode usar ../ para acessar arquivos arbitrários
    base_dir = '/opt/pulse/secure/web-apps'
    file_path = os.path.join(base_dir, resource)
    
    # Sem verificação de path traversal!
    if os.path.exists(file_path):
        return send_file(file_path)
    abort(404)

# Exemplo de exploitação:
# /dana-na/../dana/html5acc/guacamole/../../../../../../etc/passwd
# Resolve para: /etc/passwd
```

```python
# Código CORRIGIDO
import os
from flask import Flask, request, abort, send_file
from pathlib import Path

app = Flask(__name__)

@app.route('/dana-na/<path:resource>')
def handle_resource(resource):
    base_dir = '/opt/pulse/secure/web-apps'
    
    # 1. Resolver o path completo e normalizar
    resolved = Path(base_dir) / resource
    resolved = resolved.resolve()
    
    # 2. Verificar que o path está dentro do diretório base
    base_resolved = Path(base_dir).resolve()
    if not str(resolved).startswith(str(base_resolved)):
        # Path traversal detectado!
        log_security_event('path_traversal_attempt', {
            'ip': request.remote_addr,
            'path': resource,
            'resolved': str(resolved)
        })
        abort(403)
    
    # 3. Verificar se o arquivo existe (sem revelar detalhes)
    if not resolved.exists() or not resolved.is_file():
        abort(404)
    
    # 4. Verificar se o arquivo não é symlink para fora do base
    if resolved.is_symlink():
        real_path = resolved.resolve()
        if not str(real_path).startswith(str(base_resolved)):
            abort(403)
    
    return send_file(resolved)

# Middleware adicional: rate limiting para paths suspeitos
@app.before_request
def check_suspicious_paths():
    if '../' in request.path or '%2e%2e' in request.path.lower():
        log_security_event('path_traversal_suspicious', {
            'ip': request.remote_addr,
            'path': request.path,
            'user_agent': request.headers.get('User-Agent')
        })
        abort(403)
```

### 7.13.4 Lições Aprendidas

| Lição | Aplicação |
|-------|-----------|
| Sanitização de path é crítica | Sempre resolver paths contra base directory |
| Autenticação deve ser verificada ANTES do acesso a recursos | Nunca permitir bypass via path manipulation |
| Logs de segurança são essenciais | Detectar tentativas de exploração |
| Atualizações devem ser aplicadas rapidamente | CVE públicos são explorados em horas |
| Defense in depth funciona | Múltiplas camadas de verificação |

### 7.13.5 Status de Exploração

- **Exploit público disponível**: Sim, desde abril 2019
- **Mass exploitation**: Confirmado — ransomware Maze explorou esta CVE em enterprises
- **CISA BOD 20-01**: Exigiu remoção de VPNs vulneráveis até abril de 2020
- **Shodan scans**: Centenas de dispositivos ainda vulneráveis em 2024

---

## 7.14 CVE-2020-1472 — Zerologon

### 7.14.1 Resumo da Vulnerabilidade

**CVE-2020-1472** (Zerologon) é uma vulnerabilidade **CRITICAL** (CVSS 10.0) no Netlogon Remote Protocol (MS-NRPC) do Windows Server. Permite que um atacante na rede local obtenha controle total do Active Directory sem credenciais.

- **Produto afetado**: Windows Server 2008 a 2019, Windows Server Core
- **Data de disclosure**: Agosto 2020
- **CVSS**: 10.0 (Critical)
- **Tipo**: Cryptographic flaw em autenticação RPC

### 7.14.2 Mecanismo do Ataque

O ataque explora uma falha na criptografia do Netlogon. O protocolo usa uma versão customizada de AES-CFB8 com um IV fixo de 16 bytes zero. O atacante pode:

1. Conectar-se ao DC via Netlogon
2. Fazer brute force da chave de sessão (devido ao IV fixo)
3. Estabelecer sessão com chave conhecida
4. Alterar a senha do computador do domain controller
5. Obter credenciais de administrador

```python
# Código VULNERAVEL (conceitual) — Autenticação Netlogon com IV fixo
import hashlib
import hmac

def vulnerable_netlogon_auth(client_challenge):
    """
    O problema: IV é sempre 16 bytes zero
    Isso permite que o atacante faça brute force da chave de sessão
    """
    IV = b'\x00' * 16  # VULNERAVEL: IV fixo!
    
    # Com IV fixo, o atacante pode testar chaves candidatas
    # e verificar se o primeiro bloco é válido
    # Em ~256 tentativas (2^8), o atacante encontra a chave
    
    # O atacante pode:
    # 1. Enviar challenge vazio (0x00 * 8)
    # 2. Receber response do servidor
    # 3. Fazer brute force da chave de sessão
    # 4. Usar a chave para modificar a senha do DC
    
    return IV  # IV fixo é a raiz do problema
```

### 7.14.3 Impacto no Active Directory

O Zerologon permite:

1. **Elevação de privilégios completa**: Qualquer usuário autenticado pode obter controle total
2. **Bypass de autenticação MFA**: O ataque não depende de credenciais do usuário
3. **Persistência**: O atacante pode criar backdoors no AD
4. **Movimentação lateral**: Controle total permite acessar qualquer sistema no domínio
5. **Exfiltração de dados**: Acesso irrestrito a todos os recursos

### 7.14.4 Mitigação

```powershell
# Mitigação via PowerShell — Habilitar enforcement mode
# Executar em cada Domain Controller

# Verificar versão atual
Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Services\Netlogon\Parameters" -Name "VulnerableChannelAllowList"

# Habilitar enforcement (após testes em ambiente de staging)
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Services\Netlogon\Parameters" -Name "RequireSeal" -Value 1

# Reiniciar o serviço Netlogon
Restart-Service Netlogon

# Verificar status
Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Services\Netlogon\Parameters" -Name "RequireSeal"
```

### 7.14.5 Defesas em Camadas

```python
# Defesa contra Zerologon — Monitoramento e resposta
class ZerologonDefense:
    def __init__(self, event_log_path):
        self.event_log_path = event_log_path
    
    def monitor_event_5829(self, event):
        """
        Event ID 5829: Netlogon security event
        Indica tentativa de conexão com Netlogon
        """
        if event.event_id == 5829:
            # Log detalhado
            log_security_event('netlogon_event', {
                'source_ip': event.ip_address,
                'account': event.account_name,
                'timestamp': event.timestamp
            })
            
            # Verificar se é padrão suspeito
            if self.is_suspicious_netlogon(event):
                self.block_ip(event.ip_address)
    
    def monitor_event_4624_type3(self, event):
        """
        Event ID 4624 Logon Type 3: Network logon
        Verificar se seguido de Netlogon events
        """
        if event.event_id == 4624 and event.logon_type == 3:
            # Registrar para correlação
            self.record_network_logon(event)
    
    def is_suspicious_netlogon(self, event):
        # Múltiplas tentativas em curto período
        recent_events = self.get_recent_events(
            event.ip_address, 
            minutes=5
        )
        
        netlogon_count = sum(
            1 for e in recent_events 
            if e.event_id == 5829
        )
        
        return netlogon_count > 10  # Threshold
    
    def block_ip(self, ip_address):
        # Adicionar IP a blacklist temporária
        # Notificar equipe de segurança
        # Registrar evento de bloqueio
        pass
```

### 7.14.6 Lições Aprendidas

| Lição | Aplicação |
|-------|-----------|
| Crypto customizada é perigosa | Usar primitivos padrão whenever possível |
| Autenticação RPC precisa de proteção adicional | Não depender apenas de autenticação RPC |
| Monitoramento de eventos é essencial | Event logs revelam tentativas de exploração |
| Patches devem ser aplicados rapidamente | Exploração em massa dias após disclosure |
| Defense in depth salva | Segmentação de rede limita blast radius |

---

## 7.15 Sistema de Autenticação Completo em Express.js

### 7.15.1 Estrutura do Projeto

```
auth-system-express/
├── src/
│   ├── config/
│   │   ├── database.js
│   │   ├── session.js
│   │   └── security.js
│   ├── middleware/
│   │   ├── auth.js
│   │   ├── rateLimit.js
│   │   └── validation.js
│   ├── models/
│   │   ├── User.js
│   │   ├── Session.js
│   │   └── Token.js
│   ├── routes/
│   │   ├── auth.js
│   │   ├── mfa.js
│   │   └── account.js
│   ├── services/
│   │   ├── password.js
│   │   ├── jwt.js
│   │   ├── session.js
│   │   └── email.js
│   └── utils/
│       ├── crypto.js
│       ├── logger.js
│       └── errors.js
├── tests/
│   ├── auth.test.js
│   ├── mfa.test.js
│   └── session.test.js
├── .env.example
├── package.json
└── server.js
```

### 7.15.2 Implementação Completa

```javascript
// src/config/database.js
const { Pool } = require('pg');

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000
});

module.exports = pool;
```

```javascript
// src/models/User.js
const pool = require('../config/database');
const argon2 = require('argon2');

const ARGON2_OPTIONS = {
    type: argon2.argon2id,
    memoryCost: 65536,
    timeCost: 3,
    parallelism: 4,
    saltLength: 16,
    hashLength: 32
};

class User {
    static async create({ email, password, name }) {
        const passwordHash = await argon2.hash(password, ARGON2_OPTIONS);
        
        const result = await pool.query(
            `INSERT INTO users (email, password_hash, name, created_at)
             VALUES ($1, $2, $3, NOW())
             RETURNING id, email, name, created_at`,
            [email.toLowerCase(), passwordHash, name]
        );
        
        return result.rows[0];
    }

    static async findByEmail(email) {
        const result = await pool.query(
            `SELECT id, email, password_hash, name, mfa_enabled, totp_secret,
                    failed_login_attempts, locked_until, created_at
             FROM users WHERE email = $1`,
            [email.toLowerCase()]
        );
        return result.rows[0] || null;
    }

    static async findById(id) {
        const result = await pool.query(
            `SELECT id, email, name, mfa_enabled, totp_secret,
                    created_at
             FROM users WHERE id = $1`,
            [id]
        );
        return result.rows[0] || null;
    }

    static async incrementFailedAttempts(userId) {
        await pool.query(
            `UPDATE users SET 
                failed_login_attempts = failed_login_attempts + 1,
                locked_until = CASE 
                    WHEN failed_login_attempts >= 4 THEN 
                        NOW() + INTERVAL '15 minutes'
                    ELSE locked_until 
                END
             WHERE id = $1`,
            [userId]
        );
    }

    static async resetFailedAttempts(userId) {
        await pool.query(
            `UPDATE users SET 
                failed_login_attempts = 0, 
                locked_until = NULL 
             WHERE id = $1`,
            [userId]
        );
    }

    static async updatePassword(userId, newPassword) {
        const hash = await argon2.hash(newPassword, ARGON2_OPTIONS);
        await pool.query(
            'UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
            [hash, userId]
        );
    }
}

module.exports = User;
```

```javascript
// src/services/jwt.js
const jose = require('jose');
const crypto = require('crypto');

class JWTService {
    constructor() {
        this.issuer = process.env.JWT_ISSUER || 'https://auth.example.com';
        this.accessTokenTTL = 900;      // 15 minutos
        this.refreshTokenTTL = 604800;  // 7 dias
        this.privateKey = null;
        this.publicKey = null;
        this.currentKid = null;
    }

    async initialize() {
        const { publicKey, privateKey } = await jose.generateKeyPair('RS256', {
            modulusLength: 2048
        });
        this.privateKey = privateKey;
        this.publicKey = publicKey;
        this.currentKid = crypto.randomUUID();
    }

    async generateTokenPair(userId, scopes = ['openid', 'profile']) {
        const accessToken = await new jose.SignJWT({
            sub: userId,
            scope: scopes.join(' '),
            typ: 'at'
        })
        .setProtectedHeader({ alg: 'RS256', kid: this.currentKid })
        .setIssuedAt()
        .setIssuer(this.issuer)
        .setExpirationTime(this.accessTokenTTL)
        .setJti(crypto.randomUUID())
        .sign(this.privateKey);

        const refreshToken = await new jose.SignJWT({
            sub: userId,
            typ: 'rt',
            family: crypto.randomUUID()
        })
        .setProtectedHeader({ alg: 'RS256', kid: this.currentKid })
        .setIssuedAt()
        .setIssuer(this.issuer)
        .setExpirationTime(this.refreshTokenTTL)
        .setJti(crypto.randomUUID())
        .sign(this.privateKey);

        return {
            accessToken,
            refreshToken,
            expiresIn: this.accessTokenTTL,
            tokenType: 'Bearer'
        };
    }

    async verifyAccessToken(token) {
        return jose.jwtVerify(token, this.publicKey, {
            algorithms: ['RS256'],
            issuer: this.issuer
        });
    }

    getJWKS() {
        const jwk = jose.exportJWK(this.publicKey);
        return {
            keys: [{
                ...jwk,
                kid: this.currentKid,
                use: 'sig'
            }]
        };
    }
}

module.exports = new JWTService();
```

```javascript
// src/middleware/auth.js
const jwtService = require('../services/jwt');
const User = require('../models/User');

async function requireAuth(req, res, next) {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({
            error: 'Authentication required',
            message: 'Missing or invalid Authorization header'
        });
    }

    const token = authHeader.substring(7);

    try {
        const { payload } = await jwtService.verifyAccessToken(token);

        // Verificar blacklist
        const isBlacklisted = await checkTokenBlacklist(payload.jti);
        if (isBlacklisted) {
            return res.status(401).json({ error: 'Token revoked' });
        }

        const user = await User.findById(payload.sub);
        if (!user) {
            return res.status(401).json({ error: 'User not found' });
        }

        req.user = {
            id: user.id,
            email: user.email,
            name: user.name,
            scopes: payload.scope ? payload.scope.split(' ') : []
        };

        next();
    } catch (err) {
        if (err.code === 'ERR_JWT_EXPIRED') {
            return res.status(401).json({ error: 'Token expired' });
        }
        return res.status(401).json({ error: 'Invalid token' });
    }
}

function requireScope(scope) {
    return (req, res, next) => {
        if (!req.user || !req.user.scopes.includes(scope)) {
            return res.status(403).json({
                error: 'Insufficient scope',
                required: scope
            });
        }
        next();
    };
}

module.exports = { requireAuth, requireScope };
```

```javascript
// src/routes/auth.js
const express = require('express');
const crypto = require('crypto');
const router = express.Router();
const User = require('../models/User');
const jwtService = require('../services/jwt');
const { requireAuth } = require('../middleware/auth');
const argon2 = require('argon2');

// POST /auth/register
router.post('/register', async (req, res) => {
    try {
        const { email, password, name } = req.body;

        // Validação de entrada
        if (!email || !password || !name) {
            return res.status(400).json({
                error: 'Missing required fields',
                required: ['email', 'password', 'name']
            });
        }

        // Verificar se email já existe
        const existing = await User.findByEmail(email);
        if (existing) {
            // Não revelar que o email já existe
            return res.status(201).json({
                message: 'Registration successful'
            });
        }

        // Verificar força da senha
        if (password.length < 12) {
            return res.status(400).json({
                error: 'Password must be at least 12 characters'
            });
        }

        // Criar usuário
        const user = await User.create({ email, password, name });

        // Gerar tokens
        const tokens = await jwtService.generateTokenPair(user.id);

        res.status(201).json({
            message: 'Registration successful',
            user: { id: user.id, email: user.email, name: user.name },
            ...tokens
        });
    } catch (err) {
        console.error('Registration error:', err);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /auth/login
router.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ error: 'Missing credentials' });
        }

        const user = await User.findByEmail(email);

        // Verificar lockout
        if (user && user.locked_until && new Date(user.locked_until) > new Date()) {
            return res.status(429).json({
                error: 'Account temporarily locked',
                retryAfter: user.locked_until
            });
        }

        // Verificar credenciais (com timing constante)
        let isValid = false;
        if (user) {
            isValid = await argon2.verify(user.password_hash, password);
        }

        if (!isValid) {
            // Incrementar tentativas (mesmo se usuário não existe)
            if (user) {
                await User.incrementFailedAttempts(user.id);
            }
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Login bem-sucedido
        await User.resetFailedAttempts(user.id);

        // Verificar MFA
        if (user.mfa_enabled) {
            // Criar sessão temporária para MFA
            const mfaToken = crypto.randomBytes(32).toString('hex');
            await storeMFASession(user.id, mfaToken);
            
            return res.json({
                mfaRequired: true,
                mfaToken: mfaToken
            });
        }

        // Gerar tokens
        const tokens = await jwtService.generateTokenPair(user.id);

        res.json({
            message: 'Login successful',
            user: { id: user.id, email: user.email, name: user.name },
            ...tokens
        });
    } catch (err) {
        console.error('Login error:', err);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// POST /auth/refresh
router.post('/refresh', async (req, res) => {
    try {
        const { refreshToken } = req.body;

        if (!refreshToken) {
            return res.status(400).json({ error: 'Missing refresh token' });
        }

        const { payload } = await jwtService.verifyAccessToken(refreshToken);

        // Verificar se não está na blacklist
        const isBlacklisted = await checkTokenBlacklist(payload.jti);
        if (isBlacklisted) {
            return res.status(401).json({ error: 'Refresh token reused' });
        }

        // Gerar novos tokens
        const tokens = await jwtService.generateTokenPair(payload.sub);

        // Blacklistar refresh token antigo
        await blacklistToken(payload.jti);

        res.json(tokens);
    } catch (err) {
        return res.status(401).json({ error: 'Invalid refresh token' });
    }
});

// POST /auth/logout
router.post('/logout', requireAuth, async (req, res) => {
    await blacklistToken(req.user.id);
    res.json({ message: 'Logged out successfully' });
});

module.exports = router;
```

---

## 7.16 Sistema de Autenticação Completo em Flask

### 7.16.1 Estrutura do Projeto

```
auth-system-flask/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── jwt_service.py
│   │   └── password.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── rate_limit.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── auth.py
│   └── utils/
│       ├── __init__.py
│       ├── crypto.py
│       └── errors.py
├── migrations/
├── tests/
├── .env.example
├── requirements.txt
└── run.py
```

### 7.16.2 Implementação Completa

```python
# app/config.py
import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = 'RS256'
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_LOGIN = "5/15minutes"
    
    # Session
    SESSION_TYPE = 'redis'
    SESSION_REDIS = os.environ.get('REDIS_URL')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
```

```python
# app/models/user.py
from datetime import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

class User:
    def __init__(self, id, email, name, password_hash=None,
                 mfa_enabled=False, totp_secret=None,
                 failed_login_attempts=0, locked_until=None,
                 created_at=None):
        self.id = id
        self.email = email.lower()
        self.name = name
        self.password_hash = password_hash
        self.mfa_enabled = mfa_enabled
        self.totp_secret = totp_secret
        self.failed_login_attempts = failed_login_attempts
        self.locked_until = locked_until
        self.created_at = created_at or datetime.utcnow()

    @classmethod
    def create(cls, email, password, name, db):
        password_hash = ph.hash(password)
        
        cursor = db.execute(
            """INSERT INTO users (email, password_hash, name, created_at)
               VALUES (%s, %s, %s, NOW())
               RETURNING id, email, name, created_at""",
            (email.lower(), password_hash, name)
        )
        
        row = cursor.fetchone()
        return cls(id=row[0], email=row[1], name=row[2], 
                   password_hash=password_hash, created_at=row[3])

    def verify_password(self, password):
        try:
            ph.verify(self.password_hash, password)
            
            # Re-hash se necessário (parâmetros de custo atualizados)
            if ph.check_needs_rehash(self.password_hash):
                new_hash = ph.hash(password)
                self._update_password_hash(new_hash)
            
            return True
        except VerifyMismatchError:
            return False

    def increment_failed_attempts(self, db):
        db.execute(
            """UPDATE users SET 
                failed_login_attempts = failed_login_attempts + 1,
                locked_until = CASE 
                    WHEN failed_login_attempts >= 4 THEN 
                        NOW() + INTERVAL '15 minutes'
                    ELSE locked_until 
                END
             WHERE id = %s""",
            (self.id,)
        )

    def reset_failed_attempts(self, db):
        db.execute(
            """UPDATE users SET 
                failed_login_attempts = 0, 
                locked_until = NULL 
             WHERE id = %s""",
            (self.id,)
        )

    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def _update_password_hash(self, new_hash, db):
        db.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_hash, self.id)
        )

    @classmethod
    def find_by_email(cls, email, db):
        cursor = db.execute(
            """SELECT id, email, name, password_hash, mfa_enabled,
                      totp_secret, failed_login_attempts, locked_until,
                      created_at
               FROM users WHERE email = %s""",
            (email.lower(),)
        )
        row = cursor.fetchone()
        if row:
            return cls(
                id=row[0], email=row[1], name=row[2],
                password_hash=row[3], mfa_enabled=row[4],
                totp_secret=row[5], failed_login_attempts=row[6],
                locked_until=row[7], created_at=row[8]
            )
        return None
```

```python
# app/services/jwt_service.py
import jwt
import uuid
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class JWTService:
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        self.issuer = 'https://auth.example.com'
        self.kid = str(uuid.uuid4())
    
    def generate_token_pair(self, user_id, scopes=None):
        scopes = scopes or ['openid', 'profile']
        now = int(time.time())
        
        access_payload = {
            'sub': str(user_id),
            'scope': ' '.join(scopes),
            'typ': 'at',
            'iss': self.issuer,
            'iat': now,
            'exp': now + 900,  # 15 minutos
            'jti': str(uuid.uuid4())
        }
        
        refresh_payload = {
            'sub': str(user_id),
            'typ': 'rt',
            'family': str(uuid.uuid4()),
            'iss': self.issuer,
            'iat': now,
            'exp': now + 604800,  # 7 dias
            'jti': str(uuid.uuid4())
        }
        
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        access_token = jwt.encode(
            access_payload, private_pem,
            algorithm='RS256',
            headers={'kid': self.kid}
        )
        
        refresh_token = jwt.encode(
            refresh_payload, private_pem,
            algorithm='RS256',
            headers={'kid': self.kid}
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 900,
            'token_type': 'Bearer'
        }
    
    def verify_token(self, token):
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return jwt.decode(
            token, public_pem,
            algorithms=['RS256'],
            issuer=self.issuer
        )
    
    def get_jwks(self):
        public_numbers = self.public_key.public_numbers()
        return {
            'keys': [{
                'kty': 'RSA',
                'use': 'sig',
                'kid': self.kid,
                'n': self._int_to_base64url(public_numbers.n),
                'e': self._int_to_base64url(public_numbers.e),
                'alg': 'RS256'
            }]
        }
    
    @staticmethod
    def _int_to_base64url(num):
        import base64
        byte_length = (num.bit_length() + 7) // 8
        num_bytes = num.to_bytes(byte_length, byteorder='big')
        return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode()
```

```python
# app/routes/auth.py
from flask import Blueprint, request, jsonify, session
from app.services.auth import AuthService
from app.services.jwt_service import JWTService
from app.middleware.auth import require_auth

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_service = AuthService()
jwt_service = JWTService()

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not all(k in data for k in ['email', 'password', 'name']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(data['password']) < 12:
        return jsonify({'error': 'Password must be at least 12 characters'}), 400
    
    user = auth_service.register(
        email=data['email'],
        password=data['password'],
        name=data['name']
    )
    
    tokens = jwt_service.generate_token_pair(user.id)
    
    return jsonify({
        'message': 'Registration successful',
        'user': {'id': user.id, 'email': user.email, 'name': user.name},
        **tokens
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not all(k in data for k in ['email', 'password']):
        return jsonify({'error': 'Missing credentials'}), 400
    
    result = auth_service.login(
        email=data['email'],
        password=data['password'],
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    if result.get('mfa_required'):
        return jsonify(result)
    
    if result.get('error'):
        return jsonify(result), 401
    
    return jsonify(result)

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json()
    
    if not data.get('refresh_token'):
        return jsonify({'error': 'Missing refresh token'}), 400
    
    try:
        result = jwt_service.refresh_tokens(data['refresh_token'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'Invalid refresh token'}), 401

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    # Blacklistar token atual
    auth_service.logout(request.user['id'])
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/.well-known/jwks.json')
def jwks():
    return jsonify(jwt_service.get_jwks())
```

```python
# app/services/auth.py
import secrets
from datetime import datetime
from app.models.user import User
from app.utils.redis import redis_client

class AuthService:
    def __init__(self):
        self.max_login_attempts = 5
        self.lockout_duration = 900  # 15 minutos

    def register(self, email, password, name):
        # Verificar rate limiting
        if self._is_rate_limited(email):
            raise ValueError('Too many registration attempts')
        
        # Criar usuário
        db = get_db_connection()
        user = User.create(email, password, name, db)
        db.commit()
        
        return user

    def login(self, email, password, ip, user_agent):
        db = get_db_connection()
        user = User.find_by_email(email, db)
        
        if not user:
            # Timing constante
            self._fake_verify()
            return {'error': 'Invalid credentials'}
        
        # Verificar lockout
        if user.is_locked():
            return {
                'error': 'Account temporarily locked',
                'retry_after': user.locked_until.isoformat()
            }
        
        # Verificar senha
        if not user.verify_password(password):
            user.increment_failed_attempts(db)
            db.commit()
            
            if user.failed_login_attempts >= self.max_login_attempts:
                self._notify_lockout(user)
            
            return {'error': 'Invalid credentials'}
        
        # Login bem-sucedido
        user.reset_failed_attempts(db)
        db.commit()
        
        # Verificar MFA
        if user.mfa_enabled:
            mfa_token = secrets.token_hex(32)
            self._store_mfa_session(user.id, mfa_token)
            return {'mfa_required': True, 'mfa_token': mfa_token}
        
        # Gerar tokens
        from app.services.jwt_service import JWTService
        jwt_service = JWTService()
        tokens = jwt_service.generate_token_pair(user.id)
        
        return {
            'message': 'Login successful',
            'user': {'id': user.id, 'email': user.email, 'name': user.name},
            **tokens
        }

    def logout(self, user_id):
        # Invalidar todas as sessões do usuário
        self._invalidate_user_sessions(user_id)

    def _is_rate_limited(self, identifier):
        key = f'rate_limit:register:{identifier}'
        count = redis_client.get(key)
        if count and int(count) >= 3:
            return True
        redis_client.incr(key)
        redis_client.expire(key, 3600)
        return False

    def _fake_verify(self):
        """Timing constante para prevenir user enumeration"""
        import hashlib
        hashlib.sha256(b'fake_password').hexdigest()

    def _store_mfa_session(self, user_id, mfa_token):
        redis_client.setex(
            f'mfa:{mfa_token}',
            300,  # 5 minutos
            str(user_id)
        )

    def _invalidate_user_sessions(self, user_id):
        # Implementar com Redis
        pass

    def _notify_lockout(self, user):
        # Enviar email de notificação
        pass
```

---

## 7.17 Exercícios

### Exercício 7.1 — Implementação de Password Hashing

**Objetivo**: Implementar e comparar bcrypt, scrypt e Argon2id em um cenário real.

**Tarefa**:
1. Implemente uma função que aceita uma senha e retorna hashes usando os três algoritmos
2. Meça o tempo de cada algoritmo com diferentes configurações de custo
3. Implemente um verificador que detecta automaticamente o algoritmo usado
4. Implemente migração transparente: login com qualquer algoritmo, re-hash com Argon2id

**Requisitos**:
- Usar Node.js ou Python
- Documentar tempos de execução em hardware padrão
- Implementar verificação de timing-safe
- Testar com 100.000 senhas do dataset rockyou

### Exercício 7.2 — Fluxo OAuth 2.0 com PKCE

**Objetivo**: Implementar um servidor OAuth 2.0 completo com PKCE.

**Tarefa**:
1. Implemente Authorization Server (issuer) com:
   - Discovery endpoint (`/.well-known/openid-configuration`)
   - JWKS endpoint (`/.well-known/jwks.json`)
   - Authorization endpoint com suporte a PKCE
   - Token endpoint com validação de code_verifier
2. Implemente Client que:
   - Gera code_verifier e code_challenge
   - Redireciona para autorização
   - Troca código por token com code_verifier
3. Implemente refresh tokens com rotação

**Requisitos**:
- Usar Express.js ou Flask
- Suporte a S256 code_challenge_method
- Validação completa de state parameter
- Rate limiting em todos os endpoints

### Exercício 7.3 — Sistema de Rate Limiting

**Objetivo**: Implementar proteção contra brute force com múltiplas estratégias.

**Tarefa**:
1. Implemente rate limiting por IP, por usuário e combinado
2. Implemente account lockout progressivo:
   - 5 falhas → lockout 15 minutos
   - 10 falhas → lockout 1 hora
   - 20 falhas → lockout 24 horas + notificação
3. Implemente CAPTCHA condicional após 3 tentativas
4. Implemente detecção de padrões de credential stuffing

**Requisitos**:
- Usar Redis para armazenamento
- Implementar janelas deslizantes
- Log de todos os eventos de segurança
- Dashboard de métricas de tentativas de login

### Exercício 7.4 — WebAuthn Registration e Authentication

**Objetivo**: Implementar autenticação sem senhas usando WebAuthn.

**Tarefa**:
1. Implemente registro de autenticador (platform e roaming)
2. Implemente autenticação com verificação de contadores
3. Implemente gestão de múltiplos autenticadores por usuário
4. Implemente recovery codes para acesso de emergência

**Requisitos**:
- Usar biblioteca fido2-lib (Node.js) ou py_webauthn (Python)
- Suporte a authenticatorAttachment: 'platform' e 'cross-platform'
- Verificação de contadores para detecção de clonagem
- Interface de fallback para dispositivos sem WebAuthn

### Exercício 7.5 — Análise de CVE-2019-11510

**Objetivo**: Analisar e reproduzir de forma segura a vulnerabilidade Pulse Secure VPN.

**Tarefa**:
1. Analise o vetor de ataque (path traversal → auth bypass)
2. Implemente uma aplicação web VULNERAVEL com path traversal similar
3. Implemente as defesas:
   - Path normalization
   - Base directory restriction
   - Rate limiting para paths suspeitos
   - WAF rules
4. Documente como detectar tentativas de exploração

**Requisitos**:
- Usar Docker para isolar a aplicação vulnerável
- Criar testes automatizados para cada defesa
- Documentar logs de segurança gerados
- Nunca executar em sistemas de produção

### Exercício 7.6 — Sistema Completo de Reset de Senha

**Objetivo**: Implementar fluxo de reset de senha seguro following best practices.

**Tarefa**:
1. Implemente geração de tokens criptograficamente seguros
2. Implemente envio de emails com templates seguros
3. Implemente validação de tokens com:
   - Expiração (1 hora)
   - Uso único
   - Detecção de reuso
4. Implemente notificações de segurança ao usuário

**Requisitos**:
- Usar argon2 para hash do token armazenado
- Rate limiting por email e por IP
- Mensagens genéricas para prevenir user enumeration
- Audit log completo

### Exercício 7.7 — MFA Setup e Recovery

**Objetivo**: Implementar fluxo completo de MFA com recuperação de conta.

**Tarefa**:
1. Implemente setup de TOTP com QR code
2. Implemente verificação de código com tolerance window
3. Implemente geração e armazenamento seguro de recovery codes
4. Implemente fluxo de desativação de MFA com verificação de identidade

**Requisitos**:
- Usar pyotp (Python) ou speakeasy (Node.js)
- Recovery codes com hash Argon2
- Verificação de identidade antes de desativar MFA
- Logs de todos os eventos de MFA

---

## 7.18 Referências

### RFCs e Padrões

1. RFC 6238 — TOTP: Time-Based One-Time Password Algorithm
2. RFC 6749 — The OAuth 2.0 Authorization Framework
3. RFC 7519 — JSON Web Token (JWT)
4. RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol
5. RFC 7636 — Proof Key for Code Exchange (PKCE)
6. RFC 8414 — OAuth 2.0 Authorization Server Metadata
7. RFC 8693 — OAuth 2.0 Token Exchange
8. FIDO U2F — Universal 2nd Factor Authentication
9. FIDO2/WebAuthn — W3C Web Authentication API

### Documentos de Segurança

10. OWASP Authentication Cheat Sheet
11. OWASP Session Management Cheat Sheet
12. OWASP OAuth Security Cheat Sheet
13. NIST SP 800-63B — Digital Identity Guidelines (Authentication)
14. CISA Known Exploited Vulnerabilities Catalog
15. CWE-287 — Improper Authentication
16. CWE-384 — Session Fixation

### CVEs e Vulnerabilidades

17. CVE-2019-11510 — Pulse Secure VPN Authentication Bypass
18. CVE-2020-1472 — Netlogon Elevation of Privilege (Zerologon)
19. CVE-2021-3449 — OpenSSL NULL pointer dereference
20. CVE-2014-0160 — Heartbleed
21. CVE-2011-4354 — Play Framework Session Fixation

### Livros e Artigos

22. "Bulletproof TLS and PKI" — Ivan Ristic
23. "OAuth 2 in Action" — Justin Richer, Antonio Sanso
24. "Modern Web Authentication" — Defending Against Password Attacks
25. "Secure Coding in C and C++" — Robert Seacord
26. "The Web Application Hacker's Handbook" — Stuttard, Pinto

### Ferramentas

27. Have I Been Pwned API — https://haveibeenpwned.com/API/v3
28. OAuth 2.0 Tester — https://oauth.net/2/
29. JWT.io — https://jwt.io/
30. WebAuthn.io — https://webauthn.io/
31. OWASP ZAP — https://www.zaproxy.org/
32. Burp Suite — https://portswigger.net/burp

---

## Resumo do Capítulo

Este capítulo cobriu os fundamentos e práticas avançadas de autenticação e gerenciamento de sessão em aplicações web. Os pontos-chave incluem:

1. **Armazenamento de senhas**: Argon2id é o padrão atual; bcrypt continua aceitável; scrypt é memória-hard mas menos adotado
2. **MFA**: WebAuthn é phishing-resistant e deve ser preferido; TOTP é amplamente suportado; SMS deve ser fallback apenas
3. **OAuth 2.0**: Authorization Code com PKCE é o fluxo recomendado; Client Credentials para server-to-server
4. **OpenID Connect**: ID tokens fornecem autenticação sobre OAuth 2.0; UserInfo endpoint para dados do usuário
5. **JWT**: Sempre validar algoritmos; usar JWKS para rotação de chaves; curta duração para access tokens
6. **Sessões**: Regenerar session ID após login; httpOnly + secure + sameSite cookies; invalidação imediata no logout
7. **Brute force**: Rate limiting + account lockout + CAPTCHA + monitoring
8. **CVEs**: CVE-2019-11510 (path traversal → auth bypass), CVE-2020-1472 (crypto flaw → AD compromise)
