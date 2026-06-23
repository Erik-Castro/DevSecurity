# Capítulo 8 — WebAuthn e FIDO2

## Introdução

WebAuthn (Web Authentication API) e FIDO2 representam a evolução mais significativa na autenticação de usuários desde a invenção da senha. Juntos, eles definem um padrão aberto que permite autenticação baseada em criptografia de chave pública, eliminando a dependência de senhas compartilhadas e tornando phishing praticamente impossível.

Enquanto senhas confiam em um segredo que o usuário e o servidor compartilham (e que pode ser interceptado, reutilizado, ou roubado), WebAuthn/FIDO2 usa pares de chaves criptográficas onde a chave privada nunca sai do dispositivo do usuário. O servidor armazena apenas a chave pública, e a autenticação é feita provando posse da chave privada via assinatura digital.

O impacto é profundo: credential stuffing se torna impossível (não há credencial para testar), phishing se torna impraticável (a chave é bound ao domínio do site), e brute force se torna irrelevante (assinar com chave privada é deterministic — uma única tentativa basta).

Para o caso Misantropi4, se o IDAP tivesse implementado FIDO2/WebAuthn, o ataque de credential stuffing teria sido completamente inviável. Não haveria senhas para testar, não haveria credenciais para comprometer, não haveria base de dados com senhas para vazar.

Este capítulo cobre a WebAuthn API, passkeys, fluxos de registro e autenticação, authenticators (platform e roaming), resident keys, cross-device authentication, enterprise attestation, backup e sync, o modelo de segurança, e implementação completa em JavaScript e Python.

---

## 8.1 A WebAuthn API

### 8.1.1 O que é WebAuthn

WebAuthn é uma API padronizada pelo W3C (World Wide Web Consortium) em colaboração com a FIDO Alliance. Ela permite que aplicações web registrem e autentiquem usuários usando autenticadores seguros — hardware tokens (YubiKey, Titan), biometria (Touch ID, Face ID, Windows Hello), ou combinações dessas.

A API WebAuthn é implementada em todos os navegadores modernos:

| Navegador | Suporte | Disponível desde |
|-----------|---------|-----------------|
| Chrome | Completo | v67 (2018) |
| Firefox | Completo | v60 (2018) |
| Safari | Completo | v13 (2019) |
| Edge | Completo | v79 (2020) |
| Opera | Completo | v54 (2018) |
| Samsung Internet | Completo | v12.0 (2019) |

### 8.1.2 Componentes do WebAuthn

WebAuthn define três entidades principais:

1. **Relying Party (RP)**: O servidor da aplicação web que deseja autenticar usuários. O RP é equivalente ao "Service Provider" em OAuth/OIDC.

2. **Authenticator**: O dispositivo ou software que gera e armazena chaves criptográficas. Pode ser um hardware token (YubiKey), um sensor biométrico (Touch ID), ou uma combinação (Windows Hello).

3. **Client**: O browser e o dispositivo do usuário que mediada a comunicação entre o RP e o authenticator.

**Fluxo geral:**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     RP       │<--->│    Client    │<--->│ Authenticator│
│   (Server)   │     │   (Browser)  │     │  (Device)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 8.1.3 Chaves criptográficas

WebAuthn usa criptografia de chave pública (asymmetric cryptography):

- **Chave privada**: Armazenada no authenticator (nunca sai do dispositivo)
- **Chave pública**: Armazenada no servidor do RP

Durante a autenticação, o authenticator assina um desafio (challenge) com a chave privada, e o servidor verifica a assinatura com a chave pública armazenada.

**Algoritmos suportados:**

| Algoritmo | OID | Uso |
|-----------|-----|-----|
| ES256 | -7 | P-256 com SHA-256 (recomendado) |
| ES384 | -35 | P-384 com SHA-384 |
| ES512 | -36 | P-521 com SHA-512 |
| RS256 | -257 | RSASSA-PKCS1-v1_5 com SHA-256 |
| RS384 | -258 | RSASSA-PKCS1-v1_5 com SHA-384 |
| RS512 | -259 | RSASSA-PKCS1-v1_5 com SHA-512 |
| EdDSA | -8 | EdDSA com Ed25519 |

---

## 8.2 Passkeys

### 8.2.1 O que são passkeys

Passkeys são o nome comercial para credenciais WebAuthn descobríveis (discoverable credentials) que podem ser sincronizadas entre dispositivos. Elas representam a evolução do WebAuthn de "segundo fator" para "autenticação passwordless completa".

Passkeys resolvem o maior problema original do WebAuthn: se você perde seu dispositivo (YubiKey, laptop com Touch ID), perde o acesso à sua conta. Passkeys sincronizam chaves entre dispositivos via contas de nuvem (iCloud Keychain, Google Password Manager), eliminando esse risco.

**Passkeys sincronizadas vs passkeys não-sincronizadas:**

| Característica | Sincronizadas | Não-sincronizadas |
|----------------|---------------|-------------------|
| Armazenamento | iCloud/Google | Dispositivo físico |
| Backup | Automático (nuvem) | Manual (YubiKey extra) |
| Sync entre dispositivos | Automático | Não |
| Segurança | Alta (criptografia E2E) | Mais alta (hardware) |
| Uso principal | Consumer/日常 | Enterprise/alto risco |
| Exemplo | iCloud Keychain | YubiKey Bio |

### 8.2.2 Passkey Discovery

Quando um usuário visita um site que suporta passkeys, o browser pode descobrir automaticamente se existe uma passkey disponível:

```javascript
// Passkey discovery — verificação automática
async function checkPasskeyAvailability() {
    // Check if platform authenticator is available
    const available = await PublicKeyCredential
        .isUserVerifyingPlatformAuthenticatorAvailable();
    
    if (available) {
        // Platform authenticator (Touch ID, Windows Hello) is available
        showPasskeyLoginOption();
    }
    
    // Check for hybrid transport (cross-device)
    const hybridAvailable = await PublicKeyCredential
        .isConditionalMediationAvailable();
    
    if (hybridAvailable) {
        // Show passkey login with hybrid transport option
        showHybridTransportOption();
    }
}
```

### 8.2.3 Hybrid Transport

Hybrid transport permite usar uma passkey de um dispositivo (ex: iPhone) para autenticar em outro (ex: laptop). O fluxo usa Bluetooth para comunicação proximity-based:

```
1. Usuário visita site no laptop
2. Site solicita autenticação via passkey
3. Browser mostra QR code
4. Usuário escaneia QR code com iPhone
5. iPhone verifica biometria (Face ID/Touch ID)
6. iPhone assina o challenge via Bluetooth
7. Laptop recebe a assinatura e completa autenticação
```

**Vantagens do hybrid transport:**
- Cross-device: passkey do iPhone funciona no laptop
- Proximity-based: Bluetooth garante que os dispositivos estão próximos
- Sem necessidade de conta de nuvem compartilhada

**Requisitos:**
- Bluetooth ativado em ambos os dispositivos
- iOS 16+ ou Android 9+
- Browser suportado em ambos os dispositivos

---

## 8.3 Fluxo de Registro

### 8.3.1 Visão geral do registro

O fluxo de registro WebAuthn cria uma nova chave par (privada + pública) associada ao usuário:

```
┌──────────┐          ┌──────────┐          ┌──────────────┐
│  User    │          │  RP      │          │ Authenticator│
│          │          │ (Server) │          │  (Device)    │
└────┬─────┘          └────┬─────┘          └──────┬───────┘
     │                     │                      │
     │  Click "Register"   │                      │
     │────────────────────>│                      │
     │                     │                      │
     │                     │  Generate challenge  │
     │                     │  (random bytes)      │
     │                     │                      │
     │                     │  Create user record  │
     │                     │  Store challenge     │
     │                     │                      │
     │  navigator          │                      │
     │  .credentials       │                      │
     │  .create(options)   │                      │
     │────────────────────>│                      │
     │                     │                      │
     │                     │  Forward to           │
     │                     │  authenticator       │
     │                     │─────────────────────>│
     │                     │                      │
     │                     │                      │  User verification
     │                     │                      │  (biometric/PIN)
     │                     │                      │
     │                     │                      │  Generate key pair
     │                     │                      │  Sign challenge
     │                     │                      │
     │                     │  Receive attestation │
     │                     │<─────────────────────│
     │                     │                      │
     │                     │  Verify attestation  │
     │                     │  Store public key    │
     │                     │                      │
     │  Success            │                      │
     │<────────────────────│                      │
     │                     │                      │
```

### 8.3.2 Options de registro (servidor)

```javascript
// Server — generate registration options
const {
    generateRegistrationOptions,
} = require('@simplewebauthn/server');

async function generateRegistrationOpts(user) {
    // Get existing credentials for this user
    const userCredentials = await db.getCredentialsByUserId(user.id);
    
    const options = await generateRegistrationOptions({
        rpName: 'Meu App',
        rpID: 'exemplo.com',
        userID: user.id,
        userName: user.email,
        userDisplayName: user.name,
        
        // Exclude existing credentials (prevent duplicates)
        excludeCredentials: userCredentials.map(cred => ({
            id: cred.credentialID,
            type: 'public-key',
            transports: cred.transports,
        })),
        
        // Authenticator selection
        authenticatorSelection: {
            // Require resident key for passwordless
            residentKey: 'preferred',
            
            // Platform authenticator (Touch ID, Windows Hello)
            // or roaming (YubiKey)
            authenticatorAttachment: 'platform',
            
            // Require user verification (biometric/PIN)
            userVerification: 'preferred',
        },
        
        // Preferred algorithms
        supportedAlgorithmIDs: [
            -7,   // ES256
            -257, // RS256
        ],
        
        // Timeout (60 seconds)
        timeout: 60000,
        
        // Attestation preference
        attestationType: 'none', // 'direct' for enterprise
    });
    
    // Store challenge in session for verification
    await db.storeChallenge(user.id, options.challenge);
    
    return options;
}
```

### 8.3.3 Options de registro (client)

```javascript
// Client — create credential
async function registerPasskey() {
    // Get options from server
    const options = await fetch('/api/webauthn/register/options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    }).then(r => r.json());
    
    // Create credential
    try {
        const credential = await navigator.credentials.create({
            publicKey: {
                challenge: base64ToBuffer(options.challenge),
                
                rp: {
                    name: options.rpName,
                    id: options.rpID,
                },
                
                user: {
                    id: base64ToBuffer(options.user.id),
                    name: options.user.name,
                    displayName: options.user.displayName,
                },
                
                pubKeyCredParams: options.pubKeyCredParams,
                
                authenticatorSelection: options.authenticatorSelection,
                
                timeout: options.timeout,
                
                attestation: options.attestation,
                
                excludeCredentials: options.excludeCredentials.map(cred => ({
                    ...cred,
                    id: base64ToBuffer(cred.id),
                })),
            },
        });
        
        // Send credential to server for verification
        const result = await fetch('/api/webauthn/register/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: credential.id,
                rawId: bufferToBase64(credential.rawId),
                type: credential.type,
                response: {
                    attestationObject: bufferToBase64(
                        credential.response.attestationObject
                    ),
                    clientDataJSON: bufferToBase64(
                        credential.response.clientDataJSON
                    ),
                },
                authenticatorAttachment: credential.authenticatorAttachment,
                clientExtensionResults: credential.getClientExtensionResults(),
            }),
        });
        
        if (result.ok) {
            showSuccess('Passkey registered successfully!');
        } else {
            showError('Registration failed');
        }
    } catch (error) {
        if (error.name === 'NotAllowedError') {
            showError('User cancelled registration');
        } else {
            showError('Registration error: ' + error.message);
        }
    }
}
```

### 8.3.4 Verificação de registro (servidor)

```javascript
// Server — verify registration
const {
    verifyRegistrationResponse,
} = require('@simplewebauthn/server');

async function verifyRegistration(userId, credential) {
    // Retrieve stored challenge
    const expectedChallenge = await db.getChallenge(userId);
    
    if (!expectedChallenge) {
        throw new Error('No challenge found for user');
    }
    
    // Verify the attestation
    const verification = await verifyRegistrationResponse({
        response: credential,
        expectedChallenge,
        expectedOrigin: 'https://exemplo.com',
        expectedRPID: 'exemplo.com',
    });
    
    if (!verification.verified) {
        throw new Error('Registration verification failed');
    }
    
    const { credentialPublicKey, credentialID, counter } = 
        verification.registrationInfo;
    
    // Store credential in database
    await db.storeCredential({
        userId,
        credentialID: bufferToBase64(credentialID),
        credentialPublicKey: bufferToBase64(credentialPublicKey),
        counter,
        transports: credential.response.transports || [],
        createdAt: new Date(),
    });
    
    // Delete used challenge
    await db.deleteChallenge(userId);
    
    return { verified: true };
}
```

---

## 8.4 Fluxo de Autenticação

### 8.4.1 Visão geral da autenticação

O fluxo de autenticação usa a chave privada armazenada no authenticator para provar posse:

```
┌──────────┐          ┌──────────┐          ┌──────────────┐
│  User    │          │  RP      │          │ Authenticator│
│          │          │ (Server) │          │  (Device)    │
└────┬─────┘          └────┬─────┘          └──────┬───────┘
     │                     │                      │
     │  Click "Login"      │                      │
     │────────────────────>│                      │
     │                     │                      │
     │                     │  Generate challenge  │
     │                     │  (random bytes)      │
     │                     │                      │
     │                     │  Get user credentials│
     │                     │  (allowCredentials)  │
     │                     │                      │
     │                     │  Store challenge     │
     │                     │                      │
     │  navigator          │                      │
     │  .credentials       │                      │
     │  .get(options)      │                      │
     │────────────────────>│                      │
     │                     │                      │
     │                     │  Forward to           │
     │                     │  authenticator       │
     │                     │─────────────────────>│
     │                     │                      │
     │                     │                      │  User verification
     │                     │                      │  (biometric/PIN)
     │                     │                      │
     │                     │                      │  Sign challenge
     │                     │                      │  Update counter
     │                     │                      │
     │                     │  Receive assertion   │
     │                     │<─────────────────────│
     │                     │                      │
     │                     │  Verify assertion    │
     │                     │  Check counter       │
     │                     │  Create session      │
     │                     │                      │
     │  Success            │                      │
     │<────────────────────│                      │
     │                     │                      │
```

### 8.4.2 Options de autenticação (servidor)

```javascript
// Server — generate authentication options
const {
    generateAuthenticationOptions,
} = require('@simplewebauthn/server');

async function generateAuthOptions(userId = null) {
    let allowCredentials = [];
    
    if (userId) {
        // Specific user — allow only their credentials
        const credentials = await db.getCredentialsByUserId(userId);
        allowCredentials = credentials.map(cred => ({
            id: cred.credentialID,
            type: 'public-key',
            transports: cred.transports,
        }));
    }
    // If no userId, allowCredentials is empty
    // This enables passkey discovery (resident keys)
    
    const options = await generateAuthenticationOptions({
        rpID: 'exemplo.com',
        allowCredentials,
        userVerification: 'preferred',
        timeout: 60000,
    });
    
    // Store challenge
    await db.storeAuthChallenge(userId || 'anonymous', options.challenge);
    
    return options;
}
```

### 8.4.3 Options de autenticação (client)

```javascript
// Client — get credential
async function authenticatePasskey() {
    // Get options from server
    const options = await fetch('/api/webauthn/authenticate/options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: currentUser?.id }),
    }).then(r => r.json());
    
    try {
        const credential = await navigator.credentials.get({
            publicKey: {
                challenge: base64ToBuffer(options.challenge),
                rpId: options.rpId,
                allowCredentials: options.allowCredentials.map(cred => ({
                    ...cred,
                    id: base64ToBuffer(cred.id),
                })),
                userVerification: options.userVerification,
                timeout: options.timeout,
            },
        });
        
        // Send assertion to server
        const result = await fetch('/api/webauthn/authenticate/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: credential.id,
                rawId: bufferToBase64(credential.rawId),
                type: credential.type,
                response: {
                    authenticatorData: bufferToBase64(
                        credential.response.authenticatorData
                    ),
                    clientDataJSON: bufferToBase64(
                        credential.response.clientDataJSON
                    ),
                    signature: bufferToBase64(
                        credential.response.signature
                    ),
                    userHandle: credential.response.userHandle
                        ? bufferToBase64(credential.response.userHandle)
                        : null,
                },
                clientExtensionResults: credential.getClientExtensionResults(),
            }),
        });
        
        if (result.ok) {
            window.location.href = '/dashboard';
        } else {
            showError('Authentication failed');
        }
    } catch (error) {
        if (error.name === 'NotAllowedError') {
            showError('Authentication cancelled or timed out');
        } else {
            showError('Authentication error: ' + error.message);
        }
    }
}
```

### 8.4.4 Verificação de autenticação (servidor)

```javascript
// Server — verify authentication
const {
    verifyAuthenticationResponse,
} = require('@simplewebauthn/server');

async function verifyAuthentication(credential) {
    // Retrieve stored challenge
    const expectedChallenge = await db.getAuthChallenge(
        credential.userHandle || 'anonymous'
    );
    
    // Get stored credential
    const storedCredential = await db.getCredentialById(credential.id);
    
    if (!storedCredential) {
        throw new Error('Credential not found');
    }
    
    // Verify the assertion
    const verification = await verifyAuthenticationResponse({
        response: credential,
        expectedChallenge,
        expectedOrigin: 'https://exemplo.com',
        expectedRPID: 'exemplo.com',
        authenticator: {
            credentialPublicKey: base64ToBuffer(
                storedCredential.credentialPublicKey
            ),
            credentialID: base64ToBuffer(storedCredential.credentialID),
            counter: storedCredential.counter,
        },
    });
    
    if (!verification.verified) {
        throw new Error('Authentication verification failed');
    }
    
    // Update counter to prevent replay attacks
    await db.updateCredentialCounter(
        storedCredential.id,
        verification.authenticationInfo.newCounter
    );
    
    // Delete used challenge
    await db.deleteAuthChallenge(
        credential.userHandle || 'anonymous'
    );
    
    // Create session
    const session = await createSession(storedCredential.userId);
    
    return { verified: true, session };
}
```

---

## 8.5 Platform vs Roaming Authenticators

### 8.5.1 Platform authenticators

Platform authenticators são autenticadores integrados ao dispositivo do usuário. Eles estão sempre disponíveis e não requerem dispositivo externo.

**Exemplos:**
- Touch ID (MacBook, iPhone)
- Face ID (iPhone, iPad)
- Windows Hello (webcam, leitor de impressão digital)
- Android Biometric (leitor de impressão digital, rosto)
- Samsung Biometric

**Vantagens:**
- Sempre disponível (não precisa carregar dispositivo)
- Integrado ao fluxo do usuário
- Custo zero (já vem no dispositivo)
- Usabilidade alta (biometria é rápida)

**Desvantagens:**
- Não é portável (limitado ao dispositivo)
- Sem backup automático (a menos que use passkeys sync)
- Depende da segurança do dispositivo
- Pode ser comprometido se o dispositivo for perdido/roubado

```javascript
// Detecção de platform authenticator
async function hasPlatformAuthenticator() {
    try {
        // Check if platform authenticator is available
        const available = await PublicKeyCredential
            .isUserVerifyingPlatformAuthenticatorAvailable();
        
        if (available) {
            console.log('Platform authenticator available');
            
            // Try to create a credential with platform authenticator
            const credential = await navigator.credentials.create({
                publicKey: {
                    // ... other options
                    authenticatorSelection: {
                        authenticatorAttachment: 'platform',
                        userVerification: 'required',
                    },
                },
            });
            
            return credential !== null;
        }
        
        return false;
    } catch (error) {
        console.error('Platform authenticator check failed:', error);
        return false;
    }
}
```

### 8.5.2 Roaming authenticators

Roaming authenticators são dispositivos externos conectados via USB, NFC, ou Bluetooth. Eles são portáveis e podem ser usados em múltiplos dispositivos.

**Exemplos:**
- YubiKey 5 (USB-A, USB-C, NFC)
- Google Titan Security Key
- Feitian ePass
- SoloKeys
- Thetis

**Vantagens:**
- Portável (funciona em qualquer dispositivo)
- Hardware seguro (chave nunca sai do chip)
- Múltiplos dispositivos (backup com chave extra)
- Não depende de biometria (funciona com PIN)

**Desvantagens:**
- Custo (R$ 100-500 por token)
- Precisa ser carregado
- Risco de perda (backup é essencial)
- Conectividade (USB pode não estar disponível)

```javascript
// Uso de roaming authenticator
async function registerWithRoamingAuthenticator() {
    try {
        const credential = await navigator.credentials.create({
            publicKey: {
                // ... other options
                authenticatorSelection: {
                    authenticatorAttachment: 'cross-platform',
                    residentKey: 'preferred',
                    userVerification: 'preferred',
                },
            },
        });
        
        return credential;
    } catch (error) {
        if (error.name === 'SecurityError') {
            // User may have plugged in token after prompt
            console.log('Security error — check token connection');
        }
        throw error;
    }
}
```

### 8.5.3 Comparação detalhada

| Aspecto | Platform | Roaming |
|---------|----------|---------|
| Form factor | Integrado ao dispositivo | Dispositivo externo |
| Conexão | Interna | USB/NFC/Bluetooth |
| Custo | Incluído no dispositivo | R$ 100-500 |
| Portabilidade | Baixa | Alta |
| Backup | Via passkey sync | Chave extra |
| Biometria | Sim (Touch ID, etc.) | Opcional (YubiKey Bio) |
| Segurança física | Média (dispositivo roubado) | Alta (token dedicado) |
| Enterprise | Bom para dispositivos gerenciados | Ideal paraBYOD |

---

## 8.6 Resident Keys (Discoverable Credentials)

### 8.6.1 O que são resident keys

Resident keys (ou discoverable credentials) são credenciais WebAuthn armazenadas no authenticator que podem ser listadas sem que o servidor forneça `allowCredentials`. Isso permite login sem e-mail/senha — o browser descobre automaticamente quais credenciais estão disponíveis no dispositivo.

**Como funciona:**

```
1. Usuário visita site
2. Site solicita autenticação (sem allowCredentials)
3. Browser pergunta ao authenticator: "quais credenciais existem para este site?"
4. Authenticator lista as credenciais armazenadas
5. Usuário escolhe qual usar (se houver múltiplas)
6. Usuário verifica (biometria/PIN)
7. Authenticator assina o challenge
8. Browser envia para o servidor
```

### 8.6.2 Limitações de storage

Os authenticators têm storage limitada. Resident keys ocupam espaço valioso:

| Authenticator | Capacidade resident keys |
|---------------|------------------------|
| YubiKey 5 | ~25 |
| Google Titan | ~25 |
| Touch ID (macOS) | Ilimitado (software) |
| Windows Hello | Ilimitado (software) |
| Chrome (Android) | Ilimitado (Google Password Manager) |
| iCloud Keychain | Ilimitado (Apple) |

Para authenticators de hardware com storage limitada, o RP pode usar `largeBlob` extension para armazenar dados adicionais:

```javascript
// Large blob extension para storage adicional
const credential = await navigator.credentials.create({
    publicKey: {
        // ... other options
        extensions: {
            largeBlob: {
                read: true,
                write: true,
            },
        },
    },
});
```

### 8.6.3 Resident keys no servidor

```python
# Python — gerenciamento de resident keys
class ResidentKeyManager:
    """Manage discoverable credentials on the server side."""
    
    def __init__(self, db):
        self.db = db
    
    def register_resident_key(self, user_id: str, credential_data: dict):
        """Store a resident key for a user."""
        self.db.execute("""
            INSERT INTO resident_keys (
                user_id, credential_id, public_key, 
                counter, sign_count, created_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            credential_data['credential_id'],
            credential_data['public_key'],
            credential_data['counter'],
            credential_data['sign_count']
        ))
    
    def get_resident_keys_for_user(self, user_id: str) -> list:
        """Get all resident keys for a user."""
        return self.db.query("""
            SELECT credential_id, public_key, counter, 
                   sign_count, created_at
            FROM resident_keys
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
    
    def delete_resident_key(self, credential_id: str):
        """Delete a resident key (e.g., when device is lost)."""
        self.db.execute("""
            DELETE FROM resident_keys 
            WHERE credential_id = %s
        """, (credential_id,))
    
    def update_counter(self, credential_id: str, new_counter: int):
        """Update the signature counter after authentication."""
        self.db.execute("""
            UPDATE resident_keys 
            SET counter = %s, last_used = NOW()
            WHERE credential_id = %s
        """, (new_counter, credential_id))
```

---

## 8.7 Cross-Device Authentication

### 8.8.1 Scenario

Cross-device authentication permite que um usuário use uma passkey armazenada em um dispositivo para autenticar em outro dispositivo. Isso é útil quando:

- O usuário está em um computador público
- O dispositivo não tem platform authenticator
- O usuário prefere usar a passkey do celular

### 8.8.2 Hybrid Transport (formerly CTAP2 Hybrid)

O hybrid transport usa comunicação proximity-based (Bluetooth LE) para autenticar cross-device:

```
┌──────────────┐          ┌──────────────┐
│   Laptop     │          │   iPhone     │
│  (Browser)   │          │  (Passkey)   │
└──────┬───────┘          └──────┬───────┘
       │                         │
       │  1. Request auth        │
       │  2. Show QR code        │
       │────────────────────────>│
       │                         │
       │  3. Scan QR code        │
       │<────────────────────────│
       │                         │
       │  4. BLE connection      │
       │<═══════════════════════>│
       │                         │
       │  5. Challenge via BLE   │
       │<═══════════════════════>│
       │                         │
       │  6. Biometric verify    │
       │  7. Sign challenge      │
       │<═══════════════════════>│
       │                         │
       │  8. Complete auth       │
       │<────────────────────────│
```

### 8.8.3 Implementação

```javascript
// Hybrid transport — client side
async function authenticateWithHybridTransport() {
    try {
        // Request authentication with hybrid transport
        const credential = await navigator.credentials.get({
            publicKey: {
                challenge: serverChallenge,
                rpId: 'exemplo.com',
                userVerification: 'preferred',
                // Allow hybrid transport
                extensions: {
                    credProps: true,
                },
            },
        });
        
        // Browser will show QR code for cross-device auth
        // User scans with phone, authenticates, and
        // the assertion is sent back to the browser
        
        return credential;
    } catch (error) {
        if (error.name === 'NotAllowedError') {
            // User cancelled or QR code expired
            console.log('Cross-device auth cancelled');
        }
        throw error;
    }
}
```

---

## 8.8 Enterprise Attestation

### 8.8.1 O que é enterprise attestation

Enterprise attestation permite que o servidor receba informações detalhadas sobre o authenticator usado, incluindo fabricante, modelo, e firmware. Isso é usado em cenários enterprise para:

- Verificar que o dispositivo é aprovado pela organização
- Garantir que o firmware está atualizado
- Auditar quais dispositivos estão sendo usados
- Exigir hardware token em vez de software

### 8.8.2 Tipos de attestation

**None**: Sem informações sobre o authenticator (padrão para consumer).

**Indirect**: O authenticator pode fornecer informações, mas o browser pode filtrar.

**Direct**: O authenticator fornece informações diretamente ao servidor.

```python
# Python — verificação de enterprise attestation
class EnterpriseAttestationVerifier:
    """Verify enterprise attestation from authenticators."""
    
    # Known enterprise authenticators
    TRUSTED_AUTHENTICATORS = {
        'yubico': {
            'aaguid': '01020304-0506-0708-090a-0b0c0d0e0f10',
            'name': 'YubiKey 5',
            'trusted': True,
        },
        'google': {
            'aaguid': '00000000-0000-0000-0000-000000000001',
            'name': 'Google Titan',
            'trusted': True,
        },
    }
    
    def verify_attestation(self, attestation_object: bytes) -> dict:
        """Verify attestation and extract authenticator info."""
        # Parse attestation object
        attestation = cbor2.loads(attestation_object)
        
        # Extract AAGUID
        auth_data = attestation['authData']
        aaguid = auth_data[:16].hex()
        
        # Check against trusted list
        trusted = self.TRUSTED_AUTHENTICATORS.get(aaguid)
        
        if not trusted:
            return {
                'verified': False,
                'error': 'Unknown authenticator',
                'aaguid': aaguid,
            }
        
        # Verify attestation certificate chain
        if attestation['fmt'] == 'packed':
            # Verify using attestation certificate
            cert_chain = attestation['attStmt']['x5c']
            if not self.verify_cert_chain(cert_chain):
                return {
                    'verified': False,
                    'error': 'Invalid certificate chain',
                }
        
        return {
            'verified': True,
            'authenticator': trusted['name'],
            'aaguid': aaguid,
        }
```

---

## 8.9 Backup e Sync

### 8.9.1 Passkey synchronization

A grande vantagem das passkeys é a sincronização automática entre dispositivos:

**Apple (iCloud Keychain):**
- Passkeys são sincronizadas entre todos os dispositivos Apple
- Criptografadas end-to-end com iCloud Keychain
- Acessíveis via iCloud.com como fallback
- Requer autenticação Apple ID

**Google (Google Password Manager):**
- Passkeys são sincronizadas entre dispositivos Android e Chrome
- Criptografadas com a conta Google
- Acessíveis via passwords.google.com
- Requer autenticação Google

**Samsung (Samsung Pass):**
- Sincronização entre dispositivos Samsung
- Integrado com Samsung Account
- Criptografado com Samsung Knox

### 8.9.2 Backup strategy

Para organizações, a estratégia de backup de passkeys deve considerar:

```python
# Passkey backup management
class PasskeyBackupManager:
    """Manage passkey backup and recovery."""
    
    def __init__(self, db):
        self.db = db
    
    def register_backup_strategy(self, user_id: str):
        """Set up backup strategy for a user's passkeys."""
        # Get all passkeys for user
        passkeys = self.get_user_passkeys(user_id)
        
        strategies = {
            'platform_sync': self.check_platform_sync(user_id),
            'hardware_backup': self.check_hardware_backup(user_id),
            'recovery_codes': self.generate_recovery_codes(user_id),
        }
        
        return strategies
    
    def check_platform_sync(self, user_id: str) -> dict:
        """Check if platform sync is configured."""
        # Check if user has platform authenticator
        passkeys = self.get_user_passkeys(user_id)
        platform_keys = [
            p for p in passkeys 
            if p['authenticator_type'] == 'platform'
        ]
        
        return {
            'configured': len(platform_keys) > 0,
            'count': len(platform_keys),
            'devices': [p['device_name'] for p in platform_keys],
        }
    
    def check_hardware_backup(self, user_id: str) -> dict:
        """Check if hardware backup key exists."""
        passkeys = self.get_user_passkeys(user_id)
        hardware_keys = [
            p for p in passkeys 
            if p['authenticator_type'] == 'cross-platform'
        ]
        
        return {
            'configured': len(hardware_keys) > 0,
            'count': len(hardware_keys),
        }
    
    def generate_recovery_codes(self, user_id: str) -> list:
        """Generate one-time recovery codes."""
        codes = []
        for _ in range(10):
            code = secrets.token_hex(4).upper()
            code_formatted = f"{code[:4]}-{code[4:]}"
            codes.append(code_formatted)
        
        # Store hashed codes
        for code in codes:
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            self.db.execute("""
                INSERT INTO recovery_codes (user_id, code_hash)
                VALUES (%s, %s)
            """, (user_id, code_hash))
        
        return codes
```

### 8.9.3 Account recovery

Quando um usuário perde acesso a todas as suas passkeys, o processo de recuperação deve ser seguro:

```python
# Account recovery flow
class AccountRecoveryManager:
    """Secure account recovery for passkey-only accounts."""
    
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service
    
    def initiate_recovery(self, user_id: str, email: str) -> dict:
        """Start account recovery process."""
        # Verify email matches user
        user = self.db.query(
            "SELECT id FROM users WHERE id = %s AND email = %s",
            (user_id, email)
        )
        
        if not user:
            return {'error': 'Invalid recovery request'}
        
        # Generate recovery token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store with long expiry (72 hours for recovery)
        self.db.execute("""
            INSERT INTO recovery_tokens 
            (user_id, token_hash, expires_at)
            VALUES (%s, %s, NOW() + INTERVAL '72 hours')
        """, (user_id, token_hash))
        
        # Send recovery email
        recovery_url = f"https://exemplo.com/recover?token={token}"
        self.email_service.send(
            to=email,
            subject='Account Recovery',
            body=f'Use this link to recover your account: {recovery_url}'
        )
        
        return {'message': 'Recovery email sent'}
    
    def complete_recovery(self, token: str, new_passkey: dict) -> dict:
        """Complete account recovery with new passkey."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        record = self.db.query("""
            SELECT user_id FROM recovery_tokens 
            WHERE token_hash = %s AND expires_at > NOW()
        """, (token_hash,))
        
        if not record:
            return {'error': 'Invalid or expired recovery token'}
        
        user_id = record['user_id']
        
        # Register new passkey
        self.db.execute("""
            INSERT INTO passkeys 
            (user_id, credential_id, public_key, counter)
            VALUES (%s, %s, %s, %s)
        """, (
            user_id,
            new_passkey['credential_id'],
            new_passkey['public_key'],
            new_passkey['counter']
        ))
        
        # Invalidate recovery token
        self.db.execute("""
            DELETE FROM recovery_tokens 
            WHERE token_hash = %s
        """, (token_hash,))
        
        # Invalidate all other recovery tokens
        self.db.execute("""
            DELETE FROM recovery_tokens 
            WHERE user_id = %s
        """, (user_id,))
        
        # Log recovery event
        self.log_security_event(user_id, 'account_recovery_completed')
        
        return {'success': True, 'message': 'Account recovered'}
```

---

## 8.10 Modelo de Segurança

### 8.10.1 Origem-bound

A chave privada em WebAuthn é "origin-bound" — ela só pode ser usada no domínio para a qual foi registrada. Se um atacante criar um site phishing em `exemplo-phishing.com`, a passkey não funcionará porque o domínio não corresponde.

```javascript
// O browser verifica o origin automaticamente
// Quando navigator.credentials.get() é chamado:
// 1. Browser extrai o origin da URL atual
// 2. Browser verifica que o origin corresponde ao rpId
// 3. Se não corresponder, a operação falha
// 4. O origin é incluído no clientDataJSON
// 5. O servidor verifica o origin na validação
```

Isso é fundamental: mesmo que o atacante obtenha cópia da chave privada (impossível em hardware, mas teoricamente possível em software), ela não funcionaria em outro domínio.

### 8.10.2 Proteção contra replay

Cada autenticação incrementa um contador no authenticator. O servidor verifica que o contador aumentou desde a última autenticação:

```python
# Replay protection via counter
def verify_counter(stored_counter: int, received_counter: int) -> bool:
    """Verify that the counter has incremented.
    
    If counter is 0, authenticator doesn't support counters.
    If counter > stored_counter, authentication is valid.
    If counter <= stored_counter, possible replay attack.
    """
    if received_counter == 0:
        # Authenticator doesn't use counters
        # Fall back to other replay protection
        return True
    
    if received_counter > stored_counter:
        return True
    
    # Counter didn't increment — possible replay
    return False
```

### 8.10.3 Attestation privacy

Para proteger a privacidade do usuário, a attestation pode ser:

**None (padrão)**: Nenhuma informação sobre o authenticator. Mais privacidade.

**Indirect**: O browser pode filtrar informações sensíveis. Equilíbrio.

**Direct**: Informações completas do authenticator. Menos privacidade, mais auditoria.

**Enterprise**: Informações completas para dispositivos gerenciados. Para cenários corporativos.

### 8.10.4 Resistência a phishing

WebAuthn é considerado "phishing-resistant" porque:

1. A chave privada é armazenada no authenticator e nunca exposta
2. O browser verifica o origin antes de assinar
3. O servidor verifica o origin na validação
4. O challenge é único por autenticação (não reutilizável)
5. O authenticator requer verificação do usuário (biometria/PIN)

Um atacante phishing não pode:
- Obter a chave privada (nunca sai do authenticator)
- Usar a chave em outro domínio (origin-bound)
- Reutilizar uma assinatura (challenge único)
- Assinar sem o usuário saber (verificação obrigatória)

---

## 8.11 Implementação Completa

### 8.11.1 Backend em Python (Flask)

```python
# webauthn_service.py — implementação completa
from flask import Flask, request, jsonify, session
from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity
from fido2.cose import ES256
import cbor2
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# --- Configuration ---
RP_ID = 'exemplo.com'
RP_NAME = 'Meu App'
ORIGIN = f'https://{RP_ID}'

# --- FIDO2 Server Setup ---
rp = PublicKeyCredentialRpEntity(id=RP_ID, name=RP_NAME)
server = Fido2Server(rp)

# --- Database ---
def get_db():
    return psycopg2.connect(
        host='localhost',
        database='authdb',
        user='authuser',
        password='securepassword'
    )


# --- Registration ---
@app.route('/api/webauthn/register/options', methods=['POST'])
def registration_options():
    """Generate registration options."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get user info
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, email, name FROM users WHERE id = %s",
        (user_id,)
    )
    user = cur.fetchone()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get existing credentials
    cur.execute(
        "SELECT credential_id, public_key, counter FROM passkeys WHERE user_id = %s",
        (user_id,)
    )
    credentials = cur.fetchall()
    
    # Build credentials list
    registered_keys = []
    for cred_id, pub_key, counter in credentials:
        registered_keys.append({
            'id': cred_id,
            'type': 'public-key',
        })
    
    # Generate options
    user_dict = {
        'id': user[0].encode(),
        'name': user[1],
        'displayName': user[2],
    }
    
    registration_data, state = server.register_begin(
        user_dict,
        registered_keys,
        user_verification='preferred',
        authenticator_attachment='platform',
    )
    
    # Store state in session
    session['webauthn_registration_state'] = state
    
    cur.close()
    db.close()
    
    return jsonify({
        'rp': registration_data.rp,
        'user': {
            'id': user[0],
            'name': user[1],
            'displayName': user[2],
        },
        'pubKeyCredParams': [
            {'type': 'public-key', 'alg': -7},  # ES256
            {'type': 'public-key', 'alg': -257},  # RS256
        ],
        'timeout': 60000,
        'attestation': 'none',
        'excludeCredentials': registered_keys,
        'authenticatorSelection': {
            'residentKey': 'preferred',
            'userVerification': 'preferred',
        },
    })


@app.route('/api/webauthn/register/verify', methods=['POST'])
def registration_verify():
    """Verify registration response."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Get registration state
    state = session.get('webauthn_registration_state')
    
    if not state:
        return jsonify({'error': 'No registration state'}), 400
    
    # Parse credential
    credential = {
        'id': data['id'],
        'rawId': base64_to_bytes(data['rawId']),
        'type': data['type'],
        'response': {
            'attestationObject': base64_to_bytes(
                data['response']['attestationObject']
            ),
            'clientDataJSON': base64_to_bytes(
                data['response']['clientDataJSON']
            ),
        },
    }
    
    # Verify
    try:
        auth_data = server.register_complete(state, credential)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    # Store credential
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        INSERT INTO passkeys 
        (user_id, credential_id, public_key, counter, 
         sign_count, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (
        user_id,
        auth_data.credential_data.credential_id,
        bytes(auth_data.credential_data.public_key),
        auth_data.counter,
        auth_data.sign_count,
    ))
    
    db.commit()
    cur.close()
    db.close()
    
    # Clear registration state
    session.pop('webauthn_registration_state', None)
    
    return jsonify({'verified': True})


# --- Authentication ---
@app.route('/api/webauthn/authenticate/options', methods=['POST'])
def authentication_options():
    """Generate authentication options."""
    data = request.get_json()
    user_id = data.get('userId')
    
    db = get_db()
    cur = db.cursor()
    
    # Get credentials for user (or all if no user_id)
    if user_id:
        cur.execute(
            "SELECT credential_id FROM passkeys WHERE user_id = %s",
            (user_id,)
        )
    else:
        cur.execute("SELECT credential_id FROM passkeys")
    
    credentials = cur.fetchall()
    
    allow_credentials = [
        {'id': cred[0], 'type': 'public-key'}
        for cred in credentials
    ]
    
    # Generate challenge
    challenge = secrets.token_bytes(32)
    
    # Store challenge
    session['webauthn_auth_challenge'] = challenge
    
    cur.close()
    db.close()
    
    return jsonify({
        'challenge': bytes_to_base64(challenge),
        'rpId': RP_ID,
        'allowCredentials': allow_credentials,
        'userVerification': 'preferred',
        'timeout': 60000,
    })


@app.route('/api/webauthn/authenticate/verify', methods=['POST'])
def authentication_verify():
    """Verify authentication response."""
    data = request.get_json()
    
    # Get challenge from session
    challenge = session.get('webauthn_auth_challenge')
    
    if not challenge:
        return jsonify({'error': 'No challenge'}), 400
    
    # Parse credential
    credential = {
        'id': data['id'],
        'rawId': base64_to_bytes(data['rawId']),
        'type': data['type'],
        'response': {
            'authenticatorData': base64_to_bytes(
                data['response']['authenticatorData']
            ),
            'clientDataJSON': base64_to_bytes(
                data['response']['clientDataJSON']
            ),
            'signature': base64_to_bytes(
                data['response']['signature']
            ),
        },
    }
    
    # Get stored credential
    db = get_db()
    cur = db.cursor()
    
    cur.execute("""
        SELECT user_id, public_key, counter 
        FROM passkeys WHERE credential_id = %s
    """, (data['id'],))
    
    stored = cur.fetchone()
    
    if not stored:
        return jsonify({'error': 'Credential not found'}), 404
    
    user_id, public_key, stored_counter = stored
    
    # Create credential object for verification
    server_credential = {
        'id': data['id'],
        'public_key': public_key,
        'counter': stored_counter,
    }
    
    # Verify
    try:
        auth_data = server.authenticate_complete(
            server_credential,
            credential,
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    # Update counter
    cur.execute("""
        UPDATE passkeys 
        SET counter = %s, last_used = NOW()
        WHERE credential_id = %s
    """, (auth_data.counter, data['id']))
    
    db.commit()
    cur.close()
    db.close()
    
    # Clear challenge
    session.pop('webauthn_auth_challenge', None)
    
    # Create session
    session['user_id'] = user_id
    session['authenticated'] = True
    session['auth_method'] = 'webauthn'
    
    return jsonify({'verified': True})


# --- Utility functions ---
def base64_to_bytes(b64: str) -> bytes:
    """Decode URL-safe base64 to bytes."""
    import base64
    padding = 4 - len(b64) % 4
    if padding != 4:
        b64 += '=' * padding
    return base64.urlsafe_b64decode(b64)


def bytes_to_base64(data: bytes) -> str:
    """Encode bytes to URL-safe base64."""
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


if __name__ == '__main__':
    app.run(debug=False)
```

### 8.11.2 Frontend completo

```javascript
// webauthn-client.js — cliente completo
class WebAuthnClient {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
    }

    /**
     * Check if WebAuthn is supported in this browser.
     */
    isSupported() {
        return window.PublicKeyCredential !== undefined;
    }

    /**
     * Check if platform authenticator is available.
     */
    async hasPlatformAuthenticator() {
        if (!this.isSupported()) return false;
        return PublicKeyCredential
            .isUserVerifyingPlatformAuthenticatorAvailable();
    }

    /**
     * Register a new passkey.
     */
    async register() {
        // Get options from server
        const optionsResponse = await fetch(
            `${this.apiBaseUrl}/api/webauthn/register/options`,
            { method: 'POST' }
        );
        const options = await optionsResponse.json();

        if (!optionsResponse.ok) {
            throw new Error(options.error || 'Failed to get options');
        }

        // Create credential
        const credential = await navigator.credentials.create({
            publicKey: {
                challenge: this.base64ToBuffer(options.challenge),
                rp: options.rp,
                user: {
                    id: this.base64ToBuffer(options.user.id),
                    name: options.user.name,
                    displayName: options.user.displayName,
                },
                pubKeyCredParams: options.pubKeyCredParams,
                timeout: options.timeout,
                attestation: options.attestation,
                authenticatorSelection: options.authenticatorSelection,
                excludeCredentials: options.excludeCredentials.map(cred => ({
                    ...cred,
                    id: this.base64ToBuffer(cred.id),
                })),
            },
        });

        // Verify with server
        const verifyResponse = await fetch(
            `${this.apiBaseUrl}/api/webauthn/register/verify`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: credential.id,
                    rawId: this.bufferToBase64(credential.rawId),
                    type: credential.type,
                    response: {
                        attestationObject: this.bufferToBase64(
                            credential.response.attestationObject
                        ),
                        clientDataJSON: this.bufferToBase64(
                            credential.response.clientDataJSON
                        ),
                    },
                }),
            }
        );

        const result = await verifyResponse.json();
        if (!verifyResponse.ok) {
            throw new Error(result.error || 'Verification failed');
        }

        return result;
    }

    /**
     * Authenticate with an existing passkey.
     */
    async authenticate(userId = null) {
        // Get options from server
        const optionsResponse = await fetch(
            `${this.apiBaseUrl}/api/webauthn/authenticate/options`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId }),
            }
        );
        const options = await optionsResponse.json();

        if (!optionsResponse.ok) {
            throw new Error(options.error || 'Failed to get options');
        }

        // Get credential
        const credential = await navigator.credentials.get({
            publicKey: {
                challenge: this.base64ToBuffer(options.challenge),
                rpId: options.rpId,
                allowCredentials: options.allowCredentials.map(cred => ({
                    ...cred,
                    id: this.base64ToBuffer(cred.id),
                })),
                userVerification: options.userVerification,
                timeout: options.timeout,
            },
        });

        // Verify with server
        const verifyResponse = await fetch(
            `${this.apiBaseUrl}/api/webauthn/authenticate/verify`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: credential.id,
                    rawId: this.bufferToBase64(credential.rawId),
                    type: credential.type,
                    response: {
                        authenticatorData: this.bufferToBase64(
                            credential.response.authenticatorData
                        ),
                        clientDataJSON: this.bufferToBase64(
                            credential.response.clientDataJSON
                        ),
                        signature: this.bufferToBase64(
                            credential.response.signature
                        ),
                        userHandle: credential.response.userHandle
                            ? this.bufferToBase64(credential.response.userHandle)
                            : null,
                    },
                }),
            }
        );

        const result = await verifyResponse.json();
        if (!verifyResponse.ok) {
            throw new Error(result.error || 'Verification failed');
        }

        return result;
    }

    /**
     * Check available authenticators.
     */
    async getAvailableAuthenticators() {
        const authenticators = {
            platform: false,
            roaming: false,
            hybrid: false,
        };

        if (!this.isSupported()) return authenticators;

        // Platform authenticator
        authenticators.platform = await this.hasPlatformAuthenticator();

        // Conditional UI (passkey discovery)
        if (PublicKeyCredential.isConditionalMediationAvailable) {
            authenticators.hybrid = await PublicKeyCredential
                .isConditionalMediationAvailable();
        }

        return authenticators;
    }

    // --- Utility methods ---
    base64ToBuffer(base64) {
        const padding = '='.repeat((4 - base64.length % 4) % 4);
        const b64 = (base64 + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        const binary = atob(b64);
        const buffer = new ArrayBuffer(binary.length);
        const view = new Uint8Array(buffer);
        for (let i = 0; i < binary.length; i++) {
            view[i] = binary.charCodeAt(i);
        }
        return buffer;
    }

    bufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    }
}

// --- Usage example ---
document.addEventListener('DOMContentLoaded', async () => {
    const client = new WebAuthnClient('https://exemplo.com');

    // Check support
    if (!client.isSupported()) {
        showError('WebAuthn is not supported in this browser');
        return;
    }

    // Check available authenticators
    const authenticators = await client.getAvailableAuthenticators();
    console.log('Available authenticators:', authenticators);

    // Registration button
    document.getElementById('register-btn')
        .addEventListener('click', async () => {
            try {
                await client.register();
                showSuccess('Passkey registered successfully!');
            } catch (error) {
                showError('Registration failed: ' + error.message);
            }
        });

    // Authentication button
    document.getElementById('auth-btn')
        .addEventListener('click', async () => {
            try {
                await client.authenticate();
                window.location.href = '/dashboard';
            } catch (error) {
                showError('Authentication failed: ' + error.message);
            }
        });
});
```

---

## 8.12 Misantropi4 e WebAuthn/FIDO2

### 8.12.1 Como FIDO2 teria prevenido o ataque

Se o IDAP tivesse implementado WebAuthn/FIDO2, o ataque Misantropi4 teria sido completamente inviável:

**Não há credencial para comprometer**: FIDO2 usa pares de chaves criptográficas. A chave privada está no dispositivo do cidadão (YubiKey, Touch ID) e nunca sai de lá. A chave pública no servidor do IDAP é inútil sem a chave privada correspondente.

**Não há base de dados com senhas**: Se o IDAP não armazenasse senhas (apenas chaves públicas), o comprometimento da base de dados não exporia credenciais utilizáveis.

**Phishing é impossível**: Mesmo se o atacante criasse um site phishing idêntico ao IDAP, a passkey não funcionaria porque é bound ao domínio correto. O atacante não poderia redirecionar a autenticação.

**Credential stuffing é impossível**: Não há credencial para testar em massa. Cada autenticação requer a chave privada física no dispositivo do cidadão.

**Implementação no IDAP:**

```python
# IDAP — autenticação com FIDO2
class IDAPFIDO2Auth:
    """FIDO2 authentication for IDAP government system."""
    
    def __init__(self):
        self.rp_id = 'idap.gov.br'
        self.rp_name = 'IDAP - Identidade Digital'
        self.origin = f'https://{self.rp_id}'
    
    def setup_registration(self, cpf: str) -> dict:
        """Setup FIDO2 registration for a citizen."""
        # Look up citizen
        citizen = self.db.query(
            "SELECT id, cpf, nome FROM cidadaos WHERE cpf = %s",
            (cpf,)
        )
        
        if not citizen:
            return {'error': 'CPF nao encontrado'}
        
        # Generate registration options
        user = {
            'id': citizen['cpf'].encode(),
            'name': citizen['cpf'],
            'displayName': citizen['nome'],
        }
        
        options, state = self.fido_server.register_begin(
            user,
            [],  # No existing credentials
            user_verification='required',
            authenticator_attachment='platform',
        )
        
        # Store state
        self.store_registration_state(citizen['id'], state)
        
        return options
    
    def verify_registration(self, user_id: str, credential: dict) -> dict:
        """Verify FIDO2 registration."""
        state = self.get_registration_state(user_id)
        
        if not state:
            return {'error': 'Sessao expirada'}
        
        try:
            auth_data = self.fido_server.register_complete(
                state, credential
            )
        except Exception as e:
            return {'error': str(e)}
        
        # Store credential
        self.db.execute("""
            INSERT INTO fido2_credentials 
            (user_id, credential_id, public_key, counter)
            VALUES (%s, %s, %s, %s)
        """, (
            user_id,
            auth_data.credential_data.credential_id,
            bytes(auth_data.credential_data.public_key),
            auth_data.counter,
        ))
        
        return {'success': True, 'message': 'Chave FIDO2 registrada'}
    
    def setup_authentication(self, cpf: str = None) -> dict:
        """Setup FIDO2 authentication."""
        if cpf:
            # Specific citizen
            citizen = self.db.query(
                "SELECT id FROM cidadaos WHERE cpf = %s",
                (cpf,)
            )
            user_id = citizen['id'] if citizen else None
        else:
            user_id = None  # Discoverable credentials
        
        # Get credentials
        if user_id:
            credentials = self.db.query(
                "SELECT credential_id FROM fido2_credentials WHERE user_id = %s",
                (user_id,)
            )
        else:
            credentials = []
        
        # Generate options
        challenge = secrets.token_bytes(32)
        self.store_auth_challenge(user_id or 'anonymous', challenge)
        
        return {
            'challenge': base64_encode(challenge),
            'rpId': self.rp_id,
            'allowCredentials': [
                {'id': c['credential_id'], 'type': 'public-key'}
                for c in credentials
            ],
            'userVerification': 'required',
            'timeout': 60000,
        }
    
    def verify_authentication(self, credential: dict, ip: str) -> dict:
        """Verify FIDO2 authentication."""
        challenge = self.get_auth_challenge('anonymous')
        
        if not challenge:
            return {'error': 'Sessao expirada'}
        
        # Get stored credential
        stored = self.db.query(
            "SELECT user_id, public_key, counter FROM fido2_credentials WHERE credential_id = %s",
            (credential['id'],)
        )
        
        if not stored:
            return {'error': 'Chave nao encontrada'}
        
        # Verify
        try:
            auth_data = self.fido_server.authenticate_complete(
                stored,
                credential,
            )
        except Exception as e:
            return {'error': str(e)}
        
        # Update counter
        self.db.execute("""
            UPDATE fido2_credentials 
            SET counter = %s, last_used = NOW()
            WHERE credential_id = %s
        """, (auth_data.counter, credential['id']))
        
        # Log authentication
        self.log_auth_event(
            user_id=stored['user_id'],
            method='fido2',
            ip=ip,
            success=True
        )
        
        return {
            'success': True,
            'user_id': stored['user_id'],
        }
```

### 8.12.2 Comparação de segurança

| Aspecto | Senhas (IDAP atual) | FIDO2/Passkeys |
|---------|---------------------|----------------|
| Credential stuffing | Possível | Impossível |
| Brute force | Possível | Impossível |
| Phishing | Possível | Impossível |
| Password spray | Possível | Impossível |
| Reutilização | Comum | Impossível |
| Base de dados comprometida | Crítica (senhas expostas) | Inútil (chaves públicas) |
| Keylogging | Possível | Impossível |
| SIM swapping | N/A | N/A |
| Hardware requirement | Não | Sim (YubiKey/Touch ID) |

### 8.12.3 Trade-offs para o IDAP

**Vantagens de FIDO2 para o IDAP:**
- Segurança máxima: elimina todos os vetores de credential-based attack
- Compliance: atende NIST SP 800-63 AAL3
- Usabilidade: biometria é rápida e natural
- Durabilidade: chaves de hardware duram anos

**Desafios para o IDAP:**
- Distribuição de tokens: 200+ milhões de cidadãos precisariam de dispositivos compatíveis
- Custo: hardware tokens custam R$ 100-500 cada
- Acessibilidade: cidadãos sem smartphones ou computadores modernos
- Suporte: help desk para cidadãos que perdem dispositivos
- Migração: transição gradual de senhas para FIDO2

**Recomendação para o IDAP:**
1. **Curto prazo**: Implementar magic links (capítulo anterior) como autenticação primária
2. **Médio prazo**: Adicionar suporte a passkeys para cidadãos com dispositivos compatíveis
3. **Longo prazo**: Migrar para FIDO2 como único fator, com fallback presencial para cidadãos sem dispositivos

---

## 8.13 WebAuthn na prática: cenários avançados

### 8.13.1 Autenticação condicional (Conditional UI)

Conditional UI permite que o browser mostre automaticamente passkeys disponíveis no campo de login, sem que o usuário precise clicar em um botão específico. Isso é chamado de "autenticação condicional" porque o browser só mostra a opção se houver passkeys disponíveis.

```javascript
// Conditional UI — autenticação passiva
class ConditionalUIManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.credentials = [];
    }

    /**
     * Initialize conditional UI for login form.
     * This makes passkeys appear automatically in the
     * username/email input field.
     */
    async initializeConditionalUI() {
        // Check if conditional mediation is available
        if (!PublicKeyCredential.isConditionalMediationAvailable) {
            console.log('Conditional UI not supported');
            return false;
        }

        const isAvailable = await PublicKeyCredential
            .isConditionalMediationAvailable();

        if (!isAvailable) {
            console.log('Conditional mediation not available');
            return false;
        }

        // Get authentication options from server
        const options = await fetch(
            `${this.apiBaseUrl}/api/webauthn/authenticate/options/conditional`,
            { method: 'POST' }
        ).then(r => r.json());

        // Start conditional authentication
        try {
            const credential = await navigator.credentials.get({
                publicKey: {
                    challenge: this.base64ToBuffer(options.challenge),
                    rpId: options.rpId,
                    userVerification: 'preferred',
                    // This enables conditional UI
                    // The browser will show passkeys in the input field
                },
                // Signal to browser that this is conditional
                mediation: 'conditional',
            });

            // User selected a passkey from the autofill dropdown
            return await this.verifyCredential(credential);
        } catch (error) {
            if (error.name === 'NotAllowedError') {
                // User chose to type password instead
                console.log('User declined passkey, falling back to password');
                return null;
            }
            throw error;
        }
    }

    /**
     * Set up form for conditional UI.
     * The input must have autocomplete="webauthn" attribute.
     */
    setupForm() {
        const form = document.getElementById('login-form');
        const emailInput = document.getElementById('email');

        // Set autocomplete attribute for conditional UI
        emailInput.setAttribute('autocomplete', 'webauthn username');

        // Initialize conditional UI when form is visible
        this.initializeConditionalUI();
    }

    async verifyCredential(credential) {
        const response = await fetch(
            `${this.apiBaseUrl}/api/webauthn/authenticate/verify`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: credential.id,
                    rawId: this.bufferToBase64(credential.rawId),
                    type: credential.type,
                    response: {
                        authenticatorData: this.bufferToBase64(
                            credential.response.authenticatorData
                        ),
                        clientDataJSON: this.bufferToBase64(
                            credential.response.clientDataJSON
                        ),
                        signature: this.bufferToBase64(
                            credential.response.signature
                        ),
                    },
                }),
            }
        );

        if (response.ok) {
            window.location.href = '/dashboard';
            return true;
        }
        return false;
    }

    base64ToBuffer(base64) {
        const padding = '='.repeat((4 - base64.length % 4) % 4);
        const b64 = (base64 + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        const binary = atob(b64);
        const buffer = new ArrayBuffer(binary.length);
        const view = new Uint8Array(buffer);
        for (let i = 0; i < binary.length; i++) {
            view[i] = binary.charCodeAt(i);
        }
        return buffer;
    }

    bufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    }
}
```

### 8.13.2 Gerenciamento de múltiplas passkeys

Usuários podem ter múltiplas passkeys (Touch ID no MacBook, Face ID no iPhone, YubiKey). O sistema deve gerenciar todas de forma coesa:

```python
# Gerenciamento de múltiplas passkeys
class PasskeyManager:
    """Manage multiple passkeys per user."""
    
    def __init__(self, db):
        self.db = db
    
    def register_passkey(self, user_id: str, credential_data: dict,
                        device_info: dict) -> dict:
        """Register a new passkey with device metadata."""
        # Check if user already has passkeys of this type
        existing = self.db.query("""
            SELECT COUNT(*) as count FROM passkeys 
            WHERE user_id = %s AND authenticator_type = %s
        """, (user_id, device_info.get('type', 'platform')))
        
        # Limit passkeys per type
        MAX_PASSKEYS_PER_TYPE = 5
        if existing[0]['count'] >= MAX_PASSKEYS_PER_TYPE:
            return {
                'error': f'Maximum {MAX_PASSKEYS_PER_TYPE} '
                         f'passkeys of this type allowed'
            }
        
        # Store passkey with device metadata
        self.db.execute("""
            INSERT INTO passkeys (
                user_id, credential_id, public_key, counter,
                authenticator_type, device_name, device_type,
                aaguid, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id,
            credential_data['credential_id'],
            credential_data['public_key'],
            credential_data['counter'],
            device_info.get('type', 'platform'),
            device_info.get('name', 'Unknown device'),
            device_info.get('device_type', 'unknown'),
            device_info.get('aaguid', ''),
        ))
        
        return {'success': True, 'message': 'Passkey registered'}
    
    def list_passkeys(self, user_id: str) -> list:
        """List all passkeys for a user."""
        passkeys = self.db.query("""
            SELECT id, authenticator_type, device_name, 
                   device_type, aaguid, created_at, last_used,
                   (SELECT COUNT(*) FROM passkeys WHERE user_id = %s) as total
            FROM passkeys 
            WHERE user_id = %s
            ORDER BY last_used DESC NULLS LAST, created_at DESC
        """, (user_id, user_id))
        
        return [{
            'id': p['id'],
            'type': p['authenticator_type'],
            'device': p['device_name'],
            'device_type': p['device_type'],
            'registered': p['created_at'].isoformat(),
            'last_used': p['last_used'].isoformat() if p['last_used'] else None,
            'is_primary': p == passkeys[0],  # Most recently used
        } for p in passkeys]
    
    def rename_passkey(self, passkey_id: str, user_id: str,
                      new_name: str) -> bool:
        """Rename a passkey (user-initiated)."""
        result = self.db.execute("""
            UPDATE passkeys 
            SET device_name = %s 
            WHERE id = %s AND user_id = %s
        """, (new_name, passkey_id, user_id))
        
        return result.rowcount > 0
    
    def delete_passkey(self, passkey_id: str, user_id: str) -> dict:
        """Delete a passkey."""
        # Check if this is the last passkey
        remaining = self.db.query("""
            SELECT COUNT(*) as count FROM passkeys 
            WHERE user_id = %s AND id != %s
        """, (user_id, passkey_id))
        
        if remaining[0]['count'] == 0:
            return {
                'error': 'Cannot delete last passkey. '
                         'Add another passkey first.'
            }
        
        self.db.execute("""
            DELETE FROM passkeys WHERE id = %s AND user_id = %s
        """, (passkey_id, user_id))
        
        return {'success': True, 'message': 'Passkey deleted'}
    
    def get_passkey_stats(self, user_id: str) -> dict:
        """Get statistics about user's passkeys."""
        stats = self.db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN authenticator_type = 'platform' THEN 1 ELSE 0 END) as platform,
                SUM(CASE WHEN authenticator_type = 'cross-platform' THEN 1 ELSE 0 END) as roaming,
                SUM(CASE WHEN last_used IS NOT NULL THEN 1 ELSE 0 END) as active,
                MIN(created_at) as first_registered,
                MAX(last_used) as last_authentication
            FROM passkeys 
            WHERE user_id = %s
        """, (user_id,))
        
        return stats[0] if stats else {}
```

### 8.13.3 Migração de senhas para passkeys

Migrar de autenticação baseada em senhas para passkeys requer um plano cuidadoso:

```python
# Migração progressiva para passkeys
class PasswordToPasskeyMigration:
    """Progressive migration from passwords to passkeys."""
    
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service
    
    def get_migration_status(self, user_id: str) -> dict:
        """Check user's migration status."""
        user = self.db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        passkeys = self.db.query(
            "SELECT COUNT(*) as count FROM passkeys WHERE user_id = %s",
            (user_id,)
        )
        
        return {
            'has_password': user.get('password_hash') is not None,
            'has_passkey': passkeys[0]['count'] > 0,
            'migration_phase': self._get_phase(user, passkeys[0]['count']),
        }
    
    def _get_phase(self, user: dict, passkey_count: int) -> str:
        """Determine migration phase."""
        has_password = user.get('password_hash') is not None
        has_passkey = passkey_count > 0
        
        if has_password and not has_passkey:
            return 'eligible'  # Can register passkey
        elif has_password and has_passkey:
            return 'hybrid'  # Has both, can deprecate password
        elif not has_password and has_passkey:
            return 'complete'  # Fully migrated
        else:
            return 'no_credentials'  # Should not happen
    
    def prompt_passkey_registration(self, user_id: str) -> dict:
        """Prompt user to register a passkey."""
        status = self.get_migration_status(user_id)
        
        if status['migration_phase'] == 'complete':
            return {'message': 'Already using passkeys'}
        
        if status['migration_phase'] == 'eligible':
            return {
                'message': 'Register a passkey for faster, '
                          'more secure login',
                'action': 'register_passkey',
                'show_prompt': True,
            }
        
        if status['migration_phase'] == 'hybrid':
            return {
                'message': 'You have a passkey. Consider removing '
                          'your password for enhanced security.',
                'action': 'deprecate_password',
                'show_prompt': True,
            }
        
        return {'message': 'Setup required'}
    
    def deprecate_password(self, user_id: str) -> dict:
        """Remove password after passkey is registered."""
        # Verify user has at least one active passkey
        passkeys = self.db.query(
            "SELECT COUNT(*) as count FROM passkeys WHERE user_id = %s",
            (user_id,)
        )
        
        if passkeys[0]['count'] == 0:
            return {'error': 'Cannot remove password without a passkey'}
        
        # Soft-delete password (keep hash for recovery period)
        self.db.execute("""
            UPDATE users 
            SET password_hash = NULL,
                password_deprecated_at = NOW(),
                auth_method = 'passkey'
            WHERE id = %s
        """, (user_id,))
        
        # Notify user
        self.email_service.send(
            to=self.db.query(
                "SELECT email FROM users WHERE id = %s",
                (user_id,)
            )[0]['email'],
            subject='Senha removida — voce agora usa passkeys',
            body='Sua senha foi removida. Voce agora se autentica '
                 'apenas com passkeys.'
        )
        
        return {
            'success': True,
            'message': 'Password removed. '
                      'Authentication now requires a passkey.'
        }
    
    def create_migration_campaign(self) -> dict:
        """Create a migration campaign for all password users."""
        users_without_passkey = self.db.query("""
            SELECT u.id, u.email
            FROM users u
            LEFT JOIN passkeys p ON u.id = p.user_id
            WHERE p.id IS NULL
            AND u.password_hash IS NOT NULL
            AND u.active = TRUE
        """)
        
        results = {'sent': 0, 'failed': 0}
        
        for user in users_without_passkey:
            try:
                self.email_service.send(
                    to=user['email'],
                    subject='Melhore sua seguranca com passkeys',
                    body='Registre uma passkey para login mais '
                         'rapido e seguro. Acesse sua conta para '
                         'configurar.'
                )
                results['sent'] += 1
            except Exception:
                results['failed'] += 1
        
        return results
```

### 8.13.4 WebAuthn em ambientes enterprise

Em ambientes enterprise, WebAuthn requer considerações adicionais:

```python
# Enterprise WebAuthn management
class EnterpriseWebAuthnManager:
    """Enterprise WebAuthn management for organizations."""
    
    def __init__(self, db, policy_engine):
        self.db = db
        self.policy_engine = policy_engine
    
    def enforce_policy(self, user_id: str, action: str) -> dict:
        """Enforce enterprise authentication policy."""
        user = self.db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        org = self.db.query(
            "SELECT * FROM organizations WHERE id = %s",
            (user[0]['org_id'],)
        )
        
        # Check organization policy
        policy = self.policy_engine.get_policy(org[0]['id'])
        
        if policy.get('require_hardware_token'):
            # Must use hardware token (YubiKey, Titan)
            passkeys = self.db.query("""
                SELECT * FROM passkeys 
                WHERE user_id = %s 
                AND authenticator_type = 'cross-platform'
            """, (user_id,))
            
            if not passkeys:
                return {
                    'error': 'Hardware token required by policy',
                    'policy': 'require_hardware_token'
                }
        
        if policy.get('require_attestation'):
            # Must provide attestation
            passkeys = self.db.query("""
                SELECT * FROM passkeys 
                WHERE user_id = %s 
                AND attestation_verified = TRUE
            """, (user_id,))
            
            if not passkeys:
                return {
                    'error': 'Attested passkey required by policy',
                    'policy': 'require_attestation'
                }
        
        if policy.get('max_passkeys'):
            # Limit number of passkeys
            count = self.db.query(
                "SELECT COUNT(*) as count FROM passkeys WHERE user_id = %s",
                (user_id,)
            )
            
            if count[0]['count'] >= policy['max_passkeys']:
                return {
                    'error': f"Maximum {policy['max_passkeys']} "
                            f"passkeys allowed",
                    'policy': 'max_passkeys'
                }
        
        return {'passed': True}
    
    def get_org_passkey_stats(self, org_id: str) -> dict:
        """Get passkey adoption statistics for an organization."""
        stats = self.db.query("""
            SELECT 
                COUNT(DISTINCT u.id) as total_users,
                COUNT(DISTINCT p.user_id) as users_with_passkeys,
                COUNT(p.id) as total_passkeys,
                SUM(CASE WHEN p.authenticator_type = 'platform' THEN 1 ELSE 0 END) as platform_passkeys,
                SUM(CASE WHEN p.authenticator_type = 'cross-platform' THEN 1 ELSE 0 END) as roaming_passkeys
            FROM users u
            LEFT JOIN passkeys p ON u.id = p.user_id
            WHERE u.org_id = %s AND u.active = TRUE
        """, (org_id,))
        
        result = stats[0]
        result['adoption_rate'] = (
            result['users_with_passkeys'] / result['total_users'] * 100
            if result['total_users'] > 0 else 0
        )
        
        return result
    
    def generate_compliance_report(self, org_id: str) -> dict:
        """Generate compliance report for enterprise auth."""
        stats = self.get_org_passkey_stats(org_id)
        
        policy = self.policy_engine.get_policy(org_id)
        
        compliance = {
            'organization': org_id,
            'generated_at': datetime.utcnow().isoformat(),
            'adoption': {
                'total_users': stats['total_users'],
                'users_with_passkeys': stats['users_with_passkeys'],
                'adoption_rate': f"{stats['adoption_rate']:.1f}%",
            },
            'policy_compliance': {},
            'recommendations': [],
        }
        
        # Check policy compliance
        if policy.get('require_hardware_token'):
            hardware_users = self.db.query("""
                SELECT COUNT(DISTINCT p.user_id) as count
                FROM passkeys p
                JOIN users u ON p.user_id = u.id
                WHERE u.org_id = %s
                AND p.authenticator_type = 'cross-platform'
            """, (org_id,))
            
            compliance['policy_compliance']['hardware_token'] = {
                'required': True,
                'compliant_users': hardware_users[0]['count'],
                'compliance_rate': (
                    hardware_users[0]['count'] / stats['total_users'] * 100
                    if stats['total_users'] > 0 else 0
                ),
            }
        
        # Recommendations
        if stats['adoption_rate'] < 50:
            compliance['recommendations'].append(
                'Passkey adoption below 50%. '
                'Consider running a migration campaign.'
            )
        
        if stats['roaming_passkeys'] == 0:
            compliance['recommendations'].append(
                'No hardware tokens registered. '
                'Consider distributing YubiKeys for high-security roles.'
            )
        
        return compliance
```

---

## 8.14 Checklist de Implementação

### Backend:
- [ ] Usar biblioteca FIDO2 confiável (simplewebauthn, py_webauthn)
- [ ] Validar origin e rpId em todas as verificações
- [ ] Armazenar chaves públicas, nunca privadas
- [ ] Verificar e atualizar counter após cada autenticação
- [ ] Implementar cleanup de challenges expirados
- [ ] Rate limiting em endpoints de registro/autenticação
- [ ] Logging de eventos de segurança

### Frontend:
- [ ] Verificar suporte a WebAuthn antes de mostrar opções
- [ ] Detectar platform e roaming authenticators
- [ ] Usar Conditional UI para passkey discovery
- [ ] Implementar fallback para browsers antigos
- [ ] Tratar erros específicos (NotAllowedError, etc.)
- [ ] Mostrar status de autenticadores disponíveis

### Segurança:
- [ ] Usar challenges de pelo menos 32 bytes
- [ ] Expirar challenges após 60 segundos
- [ ] Verificar attestation apenas quando necessário
- [ ] Implementar backup strategy para passkeys
- [ ] Account recovery seguro
- [ ] Proteção contra replay via counter

### Operacional:
- [ ] Monitoramento de registros e autenticações
- [ ] Alertas para atividades suspeitas
- [ ] Documentação para desenvolvedores
- [ ] Testes automatizados de segurança
- [ ] Compatibilidade cross-browser testada

---

## 8.14 Resumo

WebAuthn e FIDO2 representam o futuro da autenticação. Ao usar criptografia de chave pública com authenticators seguros, eles eliminam todas as classes de ataques baseados em credenciais: credential stuffing, brute force, phishing, e password spray.

Passkeys são a evolução do WebAuthn para o consumidor final, resolvendo o problema de backup e portabilidade com sincronização entre dispositivos. Elas combinam a segurança de hardware com a usabilidade de magic links.

Para o caso Misantropi4, FIDO2 teria sido a solução definitiva. Se o IDAP tivesse implementado WebAuthn com passkeys, o ataque de credential stuffing teria sido impossível — não haveria senhas para comprometer, não haveria base de dados com credenciais para vazar, e não haveria como testar credenciais em massa.

A migração de senhas para FIDO2 é um processo gradual. Magic links (capítulo anterior) são um primeiro passo, passkeys são o próximo nível, e FIDO2 com hardware tokens é o padrão ouro para sistemas de alta segurança. O importante é começar — cada passo na direção passwordless reduz a superfície de ataque.

## 8.14 WebAuthn e conformidade regulatória

### 8.14.1 NIST SP 800-63 e WebAuthn

O NIST Digital Identity Guidelines (SP 800-63) define níveis de assurance para autenticação. WebAuthn pode atender todos os níveis:

| Nível | Requisito | WebAuthn Solution |
|-------|-----------|-------------------|
| AAL1 | Autenticação de 1 fator | Passkey (platform) |
| AAL2 | MFA ou 2 fatores | Passkey + PIN ou biometria |
| AAL3 | Hardware token + MFA | YubiKey + biometria |

```python
# NIST AAL compliance checker
class NISTComplianceChecker:
    """Check WebAuthn compliance with NIST SP 800-63."""
    
    AAL_REQUIREMENTS = {
        'AAL1': {
            'min_factors': 1,
            'allowed_authenticators': ['platform', 'cross-platform'],
            'reauthentication': '30 days',
            'threats_mitigated': ['phishing', 'replay'],
        },
        'AAL2': {
            'min_factors': 2,
            'allowed_authenticators': [
                'platform_with_biometric',
                'cross-platform_with_pin'
            ],
            'reauthentication': '12 hours',
            'threats_mitigated': [
                'phishing', 'replay', 'credential_stuffing'
            ],
        },
        'AAL3': {
            'min_factors': 2,
            'allowed_authenticators': [
                'hardware_token_with_biometric'
            ],
            'reauthentication': '12 hours',
            'threats_mitigated': [
                'phishing', 'replay', 'credential_stuffing',
                'verifier_impersonation'
            ],
        },
    }
    
    def check_compliance(self, user_id: str, 
                        target_aal: str) -> dict:
        """Check if user meets NIST AAL requirements."""
        requirements = self.AAL_REQUIREMENTS.get(target_aal)
        
        if not requirements:
            return {'error': f'Unknown AAL level: {target_aal}'}
        
        # Get user's authenticators
        authenticators = self.db.query("""
            SELECT authenticator_type, user_verification,
                   attestation_format
            FROM passkeys WHERE user_id = %s
        """, (user_id,))
        
        # Check factor count
        factors = self._count_factors(authenticators)
        
        if factors < requirements['min_factors']:
            return {
                'compliant': False,
                'reason': f'Insufficient factors: '
                         f'{factors}/{requirements["min_factors"]}',
                'current_factors': factors,
                'required_factors': requirements['min_factors'],
            }
        
        # Check authenticator types
        authenticator_types = {
            a['authenticator_type'] for a in authenticators
        }
        
        if not any(
            at in requirements['allowed_authenticators']
            for at in authenticator_types
        ):
            return {
                'compliant': False,
                'reason': 'No allowed authenticator type found',
                'current_types': list(authenticator_types),
                'allowed_types': requirements['allowed_authenticators'],
            }
        
        return {
            'compliant': True,
            'aal_level': target_aal,
            'threats_mitigated': requirements['threats_mitigated'],
        }
    
    def _count_factors(self, authenticators: list) -> int:
        """Count authentication factors."""
        factors = set()
        
        for auth in authenticators:
            if auth['authenticator_type'] == 'cross-platform':
                factors.add('something_you_have')
            
            if auth['user_verification'] in ['required', 'preferred']:
                factors.add('something_you_are')
        
        return len(factors)
```

### 8.14.2 PCI DSS e WebAuthn

PCI DSS (Payment Card Industry Data Security Standard) requer controles de acesso fortes para acessar dados de cartão de pagamento. WebAuthn atende a esses requisitos:

```python
# PCI DSS compliance com WebAuthn
class PCIDSSCompliance:
    """PCI DSS compliance for WebAuthn authentication."""
    
    PCI_REQUIREMENTS = {
        'Req_8_3': {
            'description': 'Multi-factor authentication for '
                         'CDE access',
            'webauthn_solution': 'Cross-platform authenticator '
                               'with biometric verification',
        },
        'Req_8_2_2': {
            'description': 'Group/shared accounts not permitted',
            'webauthn_solution': 'One passkey per user, '
                               'bound to individual identity',
        },
        'Req_8_3_1': {
            'description': 'MFA for all CDE access',
            'webauthn_solution': 'WebAuthn with user_verification '
                               '= required',
        },
    }
    
    def validate_pci_access(self, user_id: str, 
                           resource: str) -> dict:
        """Validate PCI DSS compliance for CDE access."""
        # Check if accessing cardholder data environment
        if not self._is_cde_resource(resource):
            return {'compliant': True, 'reason': 'Not CDE resource'}
        
        # Check MFA
        auth_method = self._get_last_auth_method(user_id)
        
        if auth_method != 'webauthn_hardware':
            return {
                'compliant': False,
                'reason': 'PCI DSS Req 8.3: MFA required for CDE',
                'current_method': auth_method,
                'required_method': 'webauthn_hardware',
            }
        
        # Check authentication recency
        last_auth = self._get_last_auth_time(user_id)
        
        if last_auth and (datetime.utcnow() - last_auth).seconds > 900:
            return {
                'compliant': False,
                'reason': 'Session too old for CDE access',
                'last_auth': last_auth.isoformat(),
                'max_session': '15 minutes',
            }
        
        return {'compliant': True}
    
    def _is_cde_resource(self, resource: str) -> bool:
        """Check if resource is in Cardholder Data Environment."""
        cde_resources = [
            'payment_cards', 'transactions',
            'cardholder_data', 'cvv', 'track_data'
        ]
        return any(cde in resource for cde in cde_resources)
    
    def _get_last_auth_method(self, user_id: str) -> str:
        """Get the last authentication method used."""
        result = self.db.query("""
            SELECT auth_method FROM auth_logs 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        
        return result[0]['auth_method'] if result else 'unknown'
    
    def _get_last_auth_time(self, user_id: str):
        """Get timestamp of last authentication."""
        result = self.db.query("""
            SELECT created_at FROM auth_logs 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        
        return result[0]['created_at'] if result else None
```

### 8.14.3 LGPD e passkeys

A Lei Geral de Proteção de Dados (LGPD) brasileira requer proteção de dados pessoais. Passkeys podem ajudar na conformidade:

```python
# LGPD compliance com passkeys
class LGPDCompliance:
    """LGPD compliance for passkey-based authentication."""
    
    def __init__(self, db):
        self.db = db
    
    def handle_data_subject_request(self, user_id: str,
                                    request_type: str) -> dict:
        """Handle LGPD data subject requests."""
        if request_type == 'access':
            return self._handle_access_request(user_id)
        elif request_type == 'deletion':
            return self._handle_deletion_request(user_id)
        elif request_type == 'portability':
            return self._handle_portability_request(user_id)
        elif request_type == 'correction':
            return self._handle_correction_request(user_id)
        
        return {'error': f'Unknown request type: {request_type}'}
    
    def _handle_access_request(self, user_id: str) -> dict:
        """Handle data access request (Art. 18, I LGPD)."""
        # Return all data about the user, including passkeys
        user_data = self.db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        passkeys = self.db.query(
            "SELECT * FROM passkeys WHERE user_id = %s",
            (user_id,)
        )
        
        auth_logs = self.db.query(
            "SELECT * FROM auth_logs WHERE user_id = %s",
            (user_id,)
        )
        
        return {
            'user': user_data[0] if user_data else None,
            'passkeys': [{
                'device_name': p['device_name'],
                'created_at': p['created_at'].isoformat(),
                'last_used': p['last_used'].isoformat() 
                    if p['last_used'] else None,
                # Don't expose credential_id or public_key
            } for p in passkeys],
            'auth_logs': [{
                'method': l['auth_method'],
                'timestamp': l['created_at'].isoformat(),
                'ip_address': l['ip_address'],
            } for l in auth_logs],
        }
    
    def _handle_deletion_request(self, user_id: str) -> dict:
        """Handle data deletion request (Art. 18, VI LGPD)."""
        # Delete passkeys
        self.db.execute(
            "DELETE FROM passkeys WHERE user_id = %s",
            (user_id,)
        )
        
        # Delete auth logs
        self.db.execute(
            "DELETE FROM auth_logs WHERE user_id = %s",
            (user_id,)
        )
        
        # Anonymize user (don't delete to maintain referential integrity)
        self.db.execute("""
            UPDATE users 
            SET email = CONCAT('deleted_', id, '@anonymized'),
                name = 'DELETED',
                active = FALSE,
                deleted_at = NOW()
            WHERE id = %s
        """, (user_id,))
        
        return {
            'success': True,
            'message': 'Dados deletados conforme LGPD Art. 18, VI'
        }
    
    def _handle_portability_request(self, user_id: str) -> dict:
        """Handle data portability request (Art. 18, V LGPD)."""
        user_data = self.db.query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        
        # Export user data (passkeys cannot be exported)
        export = {
            'user': {
                'email': user_data[0]['email'],
                'name': user_data[0]['name'],
                'created_at': user_data[0]['created_at'].isoformat(),
            },
            'note': 'Passkeys cannot be exported due to '
                   'security design. Register new passkeys '
                   'after import.',
        }
        
        return {'export': export, 'format': 'JSON'}
    
    def audit_passkey_data_retention(self) -> dict:
        """Audit passkey data retention compliance."""
        # Check for passkeys with no activity in 2+ years
        stale_passkeys = self.db.query("""
            SELECT user_id, device_name, created_at, last_used
            FROM passkeys 
            WHERE last_used < NOW() - INTERVAL '2 years'
            OR (last_used IS NULL AND created_at < NOW() - INTERVAL '1 year')
        """)
        
        return {
            'stale_passkeys': [{
                'user_id': p['user_id'],
                'device': p['device_name'],
                'created': p['created_at'].isoformat(),
                'last_used': p['last_used'].isoformat() 
                    if p['last_used'] else 'never',
            } for p in stale_passkeys],
            'recommendation': 'Consider prompting users to '
                            'review and clean up unused passkeys'
        }
```

---

*No próximo capítulo: RBAC (Role-Based Access Control) — controlando quem pode fazer o quê no sistema.*
---

*[Capítulo anterior: 07 — Magic Links](07-magic-links.md)*
*[Próximo capítulo: 09 — Rbac](09-rbac.md)*
