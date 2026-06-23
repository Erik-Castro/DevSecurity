---
layout: default
title: "02-metodos-autenticacao"
---

# Capítulo 2 — Métodos de Autenticação

> *"A segurança da sua autenticação é definida pelo seu elo mais fraco. Se um método é opcional, ele não existe."*

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Avaliar criticamente** cada método de autenticação disponível — senhas, MFA, biometria, tokens hardware, certificados — identificando riscos, custos e adequação para cada cenário.
2. **Implementar autenticação multi-fator (MFA)** incluindo TOTP (RFC 6238), SMS, push notifications e códigos de backup, com foco na experiência do usuário e segurança.
3. **Projetar sistemas de autenticação baseada em risco (Risk-Based Authentication)** que adaptam os requisitos de autenticação ao contexto de cada requisição.
4. **Compor uma estratégia de autenticação** que combine múltiplos métodos de acordo com o nível de sensibilidade da operação e o perfil de risco do usuário.
5. **Analisar o caso Misantropi4** demonstrando como a ausência de MFA foi o fator decisivo que permitiu o ataque, e como diferentes métodos teriam impedido cada etapa.

---

## 2.1 Autenticação Baseada em Senha

### 2.1.1 O Estado Atual das Senhas

A senha continua sendo o método de autenticação mais utilizado no mundo, apesar de ser também o mais vulnerável. Pesquisas recentes revelam estatísticas preocupantes:

- **81%** das violações de dados envolvem credenciais comprometidas (Verizon DBIR 2025)
- **65%** das pessoas reutilizam senhas entre múltiplos serviços
- **23%** dos usuários usam senhas com menos de 8 caracteres
- **10%** das senhas mais comuns são usadas por mais de 3% da população

Essas estatísticas não são apenas números — representam sistemas inteiros que dependem de uma barreira que a maioria dos usuários não consegue manter adequadamente.

### 2.1.2 Pontos Fortes das Senhas

| Vantagem | Descricao |
|----------|-----------|
| Universalidade | Funciona em qualquer dispositivo com entrada de texto |
| Baixo custo | Nenhuma infraestrutura adicional necessaria |
| Familiaridade | Usuarios ja conhecem o conceito |
| Portabilidade | Nao depende de hardware ou software especifico |
| Recuperacao | Pode ser resetada via canais alternativos |

### 2.1.3 Pontos Fracos das Senhas

| Fraqueza | Descricao | Impacto |
|----------|-----------|---------|
| Reuso | Mesma senha em multiplos servicos | Vazamento em um afeta todos |
| Forca bruta | Adivinhacao automatizada | Contas com senhas fracas comprometidas |
| Phishing | Engenharia social para roubo de senhas | Credenciais entregues voluntariamente |
| Keylogging | Captura de teclas pelo malware | Senhas roubadas em tempo real |
| Memoria | Dificuldade de lembrar senhas complexas | Usuarios escolhem senhas fracas |
| Compartilhamento | Senhas transmitidas por canais inseguros | Interceptacao durante transmissao |

### 2.1.4 Política de Senhas Baseada em Evidências

O NIST SP 800-63B (2017, atualizado 2024) revolucionou as recomendações de senhas, abandonando requisitos de complexidade arbitrários em favor de evidências empíricas:

```
┌──────────────────────────────────────────────────────────────────────┐
│              POLITICA DE SENHA - NIST SP 800-63B                     │
│                                                                      │
│  REQUISITOS OBRIGATORIOS:                                            │
│  ├── Comprimento minimo: 8 caracteres (recomendado: 12+)            │
│  ├── Comprimento maximo: 64 caracteres (ou mais)                     │
│  ├── Aceitar todos os caracteres imprimiveis incluindo espacos       │
│  ├── Nao forcar troca periodica de senha                             │
│  ├── Nao exigir complexidade arbitraria (maiuscula+numero+especial) │
│  └── Verificar contra listas de senhas vazadas (HIBP, etc.)          │
│                                                                      │
│  RESTRICOES:                                                         │
│  ├── Bloquear senhas que aparecem em vazamentos conhecidos           │
│  ├── Bloquear senhas que contem o nome de usuario ou e-mail          │
│  ├── Bloquear senhas com padroes comuns (123456, password, etc.)    │
│  └── Limitar tentativas de login (max 100 por hora por conta)       │
│                                                                      │
│  RECOMENDACOES:                                                      │
│  ├── Usar MFA sempre que possivel                                    │
│  ├── Oferecer gerenciador de senhas integrado                        │
│  ├── Enviar notificacoes em caso de login suspeito                   │
│  └── Usar Argon2id para hashing (ou bcrypt/scrypt)                   │
└──────────────────────────────────────────────────────────────────────┘
```

**Por que não forçar troca periódica?**

Estudos mostram que forçar a troca de senhas a cada 90 dias leva a comportamentos prejudiciais:
- Usuários adicionam um número no final da senha (ex: "MinhaSenha1" → "MinhaSenha2")
- Usuários anotam senhas em locais inseguros
- Aumento de chamadas de suporte para redefinição de senha
- Senhas geradas aleatoriamente são frequentemente substituídas por variantes fracas

A recomendação atual é: **não trocar senhas periodicamente, mas trocar imediatamente quando houver evidência de comprometimento.**

### 2.1.5 Implementação de Validação de Senha

```python
import re
import hashlib
import requests
from typing import Tuple, List

class NISTPasswordValidator:
    """Password validator following NIST SP 800-63B guidelines."""

    HIBP_API = "https://api.pwnedpasswords.com/range/"

    COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123",
        "monkey", "master", "dragon", "login", "princess",
        "football", "shadow", "sunshine", "trustno1", "iloveyou",
        "batman", "access", "hello", "charlie", "letmein",
        "welcome", "password1", "password123", "admin", "passw0rd",
    }

    def validate(
        self, password: str, email: str = "", username: str = ""
    ) -> Tuple[bool, List[str]]:
        """
        Validate password against NIST SP 800-63B.

        Returns (is_valid, list_of_violations).
        """
        violations = []

        # Length requirements
        if len(password) < 8:
            violations.append("Senha deve ter no minimo 8 caracteres")
        if len(password) > 64:
            violations.append("Senha deve ter no maximo 64 caracteres")

        # Check against breached passwords
        if self._is_breached(password):
            violations.append(
                "Esta senha aparece em vazamentos de dados conhecidos"
            )

        # Check against common passwords
        if password.lower() in self.COMMON_PASSWORDS:
            violations.append("Esta senha e muito comum")

        # Check if password contains user context
        if email and email.split("@")[0].lower() in password.lower():
            violations.append(
                "Senha nao deve conter partes do seu e-mail"
            )
        if username and username.lower() in password.lower():
            violations.append(
                "Senha nao deve conter seu nome de usuario"
            )

        # Check for repeating characters (4+ same char)
        if re.search(r'(.)\1{3,}', password):
            violations.append(
                "Senha nao deve conter 4 ou mais caracteres repetidos"
            )

        # Check for sequential characters
        if self._has_sequential(password, 4):
            violations.append(
                "Senha nao deve conter sequencias longas (ex: abcde, 1234)"
            )

        return (len(violations) == 0, violations)

    def _is_breached(self, password: str) -> bool:
        """Check password against Have I Been Pwned API using k-anonymity."""
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        try:
            response = requests.get(
                self.HIBP_API + prefix,
                timeout=5,
                headers={"Add-Padding": "true"}
            )
            if response.status_code == 200:
                for line in response.text.splitlines():
                    hash_suffix, count = line.split(":")
                    if hash_suffix == suffix:
                        return int(count) > 0
        except requests.RequestException:
            # If API is unavailable, skip check (fail open for UX)
            pass

        return False

    def _has_sequential(self, password: str, length: int) -> bool:
        """Check for sequential characters."""
        for i in range(len(password) - length + 1):
            substring = password[i:i + length]
            # Check ascending
            if all(
                ord(substring[j]) == ord(substring[j-1]) + 1
                for j in range(1, len(substring))
            ):
                return True
            # Check descending
            if all(
                ord(substring[j]) == ord(substring[j-1]) - 1
                for j in range(1, len(substring))
            ):
                return True
        return False
```

---

## 2.2 Autenticação Multi-Fator (MFA)

### 2.2.1 Por Que MFA é Essencial

MFA é a prática de exigir dois ou mais fatores de autenticação antes de conceder acesso. É a defesa mais eficaz contra credenciais comprometidas.

De acordo com a Microsoft, MFA bloqueia **99.9%** dos ataques de comprometimento de contas. No caso do IDAP/Misantropi4, se MFA tivesse sido obrigatório, o atacante não teria conseguido acessar o sistema mesmo com as credenciais vazadas — porque não teria acesso ao segundo fator.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EFICACIA DO MFA                                    │
│                                                                      │
│  Sem MFA:                                                            │
│  ├── Credenciais vazadas → Acesso completo                           │
│  ├── Phishing → Acesso completo                                      │
│  ├── Forca bruta → Acesso potencial                                  │
│  └── Keylogger → Acesso completo                                     │
│                                                                      │
│  Com MFA:                                                            │
│  ├── Credenciais vazadas → BLOQUEADO (segundo fator necessario)      │
│  ├── Phishing → BLOQUEADO (segundo fator nao roubado)                │
│  ├── Forca bruta → BLOQUEADO (segundo fator necessario)              │
│  └── Keylogger → BLOQUEADO (segundo fator dinamico)                  │
│                                                                      │
│  Taxa de comprometimento com MFA: 0.1%                               │
│  Taxa de comprometimento sem MFA: ~16%                               │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2.2 TOTP: Time-based One-Time Password (RFC 6238)

TOTP é o método MFA mais widely deployed. Gera códigos de uso único baseados no tempo, sincronizados entre cliente e servidor.

**Como funciona:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                    COMO TOTP FUNCIONA                                 │
│                                                                      │
│  Registro:                                                           │
│  1. Servidor gera segredo aleatorio (160+ bits)                      │
│  2. Servidor armazena segredo (hash)                                 │
│  3. Servidor envia segredo ao cliente (QR code ou URI)               │
│  4. Cliente armazena segredo no app autenticador                      │
│                                                                      │
│  Geracao de Codigo:                                                  │
│  1. Tempo atual / 30 segundos = contador T                           │
│  2. HMAC-SHA1(segredo, T) = hash                                     │
│  3. Dynamic truncation = codigo de 6 digitos                          │
│                                                                      │
│  Verificacao:                                                        │
│  1. Servidor calcula TOTP para T-1, T, T+1                           │
│  2. Compara com codigo fornecido pelo usuario                         │
│  3. Se corresponder a qualquer um → valido                           │
│  4. Janela de tolerancia: ±1 periodo (±30 segundos)                  │
│                                                                      │
│  Fórmula:                                                            │
│  TOTP = HOTP(K, T)                                                   │
│  T = floor(unix_time / time_step)                                    │
│  HOTP(K, C) = Truncate(HMAC-SHA1(K, C))                             │
└──────────────────────────────────────────────────────────────────────┘
```

**Parâmetros recomendados:**

| Parametro | Valor Minimo | Valor Recomendado | Descricao |
|-----------|-------------|-------------------|-----------|
| Segredo | 128 bits | 160+ bits | Chave compartilhada HMAC |
| Digitos | 6 | 6 | Comprimento do codigo |
| Periodo | 30s | 30s | Intervalo entre codigos |
| Janela | ±1 | ±1 | Tolerancia de tempo |
| Algoritmo | SHA1 | SHA256 | Algoritmo HMAC |

```python
import hmac
import hashlib
import struct
import time
import base64
import secrets
from urllib.parse import quote

class TOTPService:
    """RFC 6238 compliant TOTP implementation."""

    DEFAULT_PERIOD = 30
    DEFAULT_DIGITS = 6
    DEFAULT_ALGORITHM = "sha1"
    WINDOW = 1  # ±1 period tolerance

    def __init__(self):
        self._period = self.DEFAULT_PERIOD
        self._digits = self.DEFAULT_DIGITS
        self._algorithm = self.DEFAULT_ALGORITHM

    def generate_secret(self, length: int = 20) -> str:
        """Generate a cryptographically secure secret."""
        return base64.b32encode(
            secrets.token_bytes(length)
        ).decode("utf-8").rstrip("=")

    def generate_code(self, secret: str, timestamp: float = None) -> str:
        """Generate TOTP code for given timestamp."""
        if timestamp is None:
            timestamp = time.time()

        # Calculate time counter
        counter = int(timestamp) // self._period

        # Decode secret
        secret_bytes = base64.b32decode(secret + "=" * (8 - len(secret) % 8))

        # HMAC calculation
        counter_bytes = struct.pack(">Q", counter)

        hash_func = getattr(hashlib, self._algorithm)
        hmac_result = hmac.new(
            secret_bytes, counter_bytes, hash_func
        ).digest()

        # Dynamic truncation
        offset = hmac_result[-1] & 0x0F
        truncated = struct.unpack(
            ">I",
            hmac_result[offset:offset + 4]
        )[0]
        truncated &= 0x7FFFFFFF

        # Generate code with specified digits
        code = truncated % (10 ** self._digits)
        return str(code).zfill(self._digits)

    def verify_code(self, secret: str, code: str,
                    timestamp: float = None) -> bool:
        """Verify a TOTP code with time window tolerance."""
        if timestamp is None:
            timestamp = time.time()

        # Check current and adjacent periods
        for offset in range(-self.WINDOW, self.WINDOW + 1):
            adjusted_time = timestamp + (offset * self._period)
            expected = self.generate_code(secret, adjusted_time)

            # Constant-time comparison
            if hmac.compare_digest(code, expected):
                return True

        return False

    def generate_uri(self, secret: str, account_name: str,
                     issuer: str = "DevSecurity") -> str:
        """Generate otpauth:// URI for QR code scanning."""
        params = {
            "secret": secret,
            "issuer": issuer,
            "algorithm": self._algorithm.upper(),
            "digits": str(self._digits),
            "period": str(self._period),
        }
        param_string = "&".join(
            f"{k}={quote(v)}" for k, v in params.items()
        )
        return f"otpauth://totp/{quote(issuer)}:{quote(account_name)}?{param_string}"

    def generate_qr_code_svg(self, uri: str) -> str:
        """Generate SVG QR code for TOTP URI."""
        # In production, use a QR code library
        return f'<svg><!-- QR code for: {uri} --></svg>'


class TOTPEnrollment:
    """Handle TOTP enrollment flow."""

    def __init__(self, totp_service: TOTPService, user_store):
        self.totp = totp_service
        self.user_store = user_store

    def initiate_enrollment(self, user_id: str) -> dict:
        """Start TOTP enrollment: generate secret and QR code URI."""
        secret = self.totp.generate_secret()
        user = self.user_store.get(user_id)

        uri = self.totp.generate_uri(
            secret,
            account_name=user["email"],
            issuer="DevSecurity"
        )

        # Store pending secret (not yet active)
        self.user_store.save_pending_mfa(user_id, {
            "secret": secret,
            "created_at": time.time(),
            "verified": False,
        })

        return {
            "secret": secret,
            "uri": uri,
            "manual_entry_key": secret,
        }

    def verify_and_activate(self, user_id: str,
                           code: str) -> dict:
        """Verify first code and activate TOTP for user."""
        pending = self.user_store.get_pending_mfa(user_id)
        if not pending:
            return {"success": False, "error": "No pending enrollment"}

        # Check enrollment not expired (10 minutes)
        if time.time() - pending["created_at"] > 600:
            self.user_store.delete_pending_mfa(user_id)
            return {"success": False, "error": "Enrollment expired"}

        # Verify the code
        if not self.totp.verify_code(pending["secret"], code):
            return {"success": False, "error": "Invalid code"}

        # Generate backup codes
        backup_codes = self._generate_backup_codes()

        # Activate MFA
        self.user_store.activate_mfa(user_id, {
            "secret": pending["secret"],
            "activated_at": time.time(),
            "backup_codes": [
                self._hash_code(c) for c in backup_codes
            ],
            "used_backup_codes": [],
        })

        self.user_store.delete_pending_mfa(user_id)

        return {
            "success": True,
            "backup_codes": backup_codes,
            "message": "MFA activated. Save backup codes securely.",
        }

    def _generate_backup_codes(self, count: int = 10) -> list:
        """Generate one-time backup codes."""
        codes = []
        for _ in range(count):
            code = secrets.token_hex(5).upper()
            formatted = f"{code[:5]}-{code[5:]}"
            codes.append(formatted)
        return codes

    def _hash_code(self, code: str) -> str:
        """Hash a backup code for storage."""
        return hashlib.sha256(code.encode()).hexdigest()
```

### 2.2.3 SMS-Based MFA

SMS é o método MFA mais acessível, mas também o mais vulnerável a ataques específicos.

**Vantagens:**
- Não requer instalação de aplicativo
- Funciona em qualquer telefone
- Familiaridade do usuário

**Riscos:**
- SIM swapping (atacante transfere número para novo chip)
- SS7 attacks (interceptação na rede telefônica)
- Malware em dispositivos móveis
- Atraso na entrega (SMS pode ser lento)

```python
import secrets
import time
from typing import Optional

class SMSMFAService:
    """SMS-based MFA with security controls."""

    CODE_LENGTH = 6
    CODE_TTL = 300  # 5 minutes
    MAX_ATTEMPTS = 3
    COOLDOWN = 60  # 1 minute between SMS

    def __init__(self, sms_provider, user_store, rate_limiter):
        self.sms = sms_provider
        self.user_store = user_store
        self.rate_limiter = rate_limiter

    def send_code(self, phone_number: str) -> dict:
        """Send MFA code via SMS with rate limiting."""
        # Rate limit check
        if self.rate_limiter.is_rate_limited(phone_number):
            return {
                "success": False,
                "error": "Too many requests. Try again later."
            }

        # Cooldown check
        last_sent = self.user_store.get_last_sms_time(phone_number)
        if last_sent and (time.time() - last_sent) < self.COOLDOWN:
            remaining = self.COOLDOWN - (time.time() - last_sent)
            return {
                "success": False,
                "error": f"Wait {int(remaining)} seconds"
            }

        # Generate code
        code = self._generate_code()

        # Store code with metadata
        self.user_store.store_mfa_code(phone_number, {
            "code_hash": hashlib.sha256(code.encode()).hexdigest(),
            "created_at": time.time(),
            "attempts": 0,
            "verified": False,
        })

        # Send SMS
        self.sms.send(
            to=phone_number,
            message=f"Seu codigo de verificacao e: {code}"
        )

        # Update rate limiting
        self.rate_limiter.record(phone_number)
        self.user_store.set_last_sms_time(phone_number, time.time())

        return {
            "success": True,
            "message": "Código enviado via SMS"
        }

    def verify_code(self, phone_number: str, code: str) -> dict:
        """Verify SMS code with attempt limiting."""
        stored = self.user_store.get_mfa_code(phone_number)
        if not stored:
            return {"success": False, "error": "No active code"}

        # Check expiration
        if time.time() - stored["created_at"] > self.CODE_TTL:
            self.user_store.delete_mfa_code(phone_number)
            return {"success": False, "error": "Code expired"}

        # Check attempts
        if stored["attempts"] >= self.MAX_ATTEMPTS:
            self.user_store.delete_mfa_code(phone_number)
            return {
                "success": False,
                "error": "Too many attempts. Request new code."
            }

        # Increment attempts
        self.user_store.increment_mfa_attempts(phone_number)

        # Verify code (constant-time comparison)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if hmac.compare_digest(code_hash, stored["code_hash"]):
            self.user_store.delete_mfa_code(phone_number)
            return {"success": True, "message": "Código verificado"}

        return {
            "success": False,
            "error": f"Código inválido ({self.MAX_ATTEMPTS - stored['attempts'] - 1} tentativas restantes)"
        }

    def _generate_code(self) -> str:
        """Generate numeric code."""
        return "".join(
            str(secrets.randbelow(10)) for _ in range(self.CODE_LENGTH)
        )
```

### 2.2.4 Push Notification MFA

Push MFA envia uma notificação para o dispositivo do usuário, que pode aprovar ou negar o acesso com um toque.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FLUXO DE PUSH MFA                                  │
│                                                                      │
│  1. Usuario faz login no desktop                                     │
│  │                                                                   │
│  2. Servidor envia push para smartphone do usuario                   │
│  │   "Alguem esta tentando acessar sua conta. Aprovar?"              │
│  │                                                                   │
│  3. Usuario aprova no smartphone                                     │
│  │                                                                   │
│  4. Servidor verifica a resposta e concede acesso                    │
│                                                                      │
│  RISCO: MFA Fatigue Attack                                           │
│  ├── Atacante envia multiplas requisicoes de push                    │
│  ├── Usuario, irritado, aprova uma "para parar"                      │
│  └── Prevencao: Mostrar contexto (IP, localizacao, dispositivo)     │
└──────────────────────────────────────────────────────────────────────┘
```

```python
import time
import secrets
import hashlib

class PushMFAService:
    """Push notification MFA with anti-fatigue protections."""

    def __init__(self, push_provider, user_store):
        self.push = push_provider
        self.user_store = user_store
        self.MAX_PENDING = 3
        self.REQUEST_TTL = 120  # 2 minutes
        self.COOLDOWN = 30  # 30 seconds between pushes

    def send_push_request(self, user_id: str, context: dict) -> dict:
        """Send push notification with rich context for approval."""
        # Anti-fatigue: limit pending requests
        pending = self.user_store.get_pending_pushes(user_id)
        if len(pending) >= self.MAX_PENDING:
            return {
                "success": False,
                "error": "Too many pending requests. Approve or deny existing ones."
            }

        # Cooldown between pushes
        last_push = self.user_store.get_last_push_time(user_id)
        if last_push and (time.time() - last_push) < self.COOLDOWN:
            return {
                "success": False,
                "error": "Wait before requesting another push"
            }

        # Generate request with rich context
        request_id = secrets.token_urlsafe(16)
        push_data = {
            "request_id": request_id,
            "user_id": user_id,
            "created_at": time.time(),
            "status": "pending",
            "context": {
                "ip_address": context.get("ip_address"),
                "user_agent": context.get("user_agent"),
                "location": context.get("location", "Unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "action": context.get("action", "Login"),
                "device": context.get("device_type", "Web Browser"),
            },
            # Geographic coordinates for distance check
            "lat": context.get("lat"),
            "lon": context.get("lon"),
        }

        self.user_store.store_push_request(request_id, push_data)
        self.user_store.set_last_push_time(user_id, time.time())

        # Send push with full context
        self.push.send(
            user_id=user_id,
            title="Solicitacao de Acesso",
            body=(
                f"Alguem esta tentando acessar sua conta.\n"
                f"IP: {context.get('ip_address')}\n"
                f"Localizacao: {context.get('location')}\n"
                f"Dispositivo: {context.get('device_type')}\n"
                f"Hora: {push_data['context']['timestamp']}"
            ),
            data=push_data,
            actions=["approve", "deny"],
            # Anti-fatigue: require biometric on device
            require_biometric=True,
        )

        return {
            "success": True,
            "request_id": request_id,
            "message": "Push notification sent"
        }

    def handle_response(self, request_id: str,
                        approved: bool, device_context: dict) -> dict:
        """Handle push response with context verification."""
        request = self.user_store.get_push_request(request_id)
        if not request:
            return {"success": False, "error": "Request not found"}

        if request["status"] != "pending":
            return {"success": False, "error": "Request already processed"}

        if time.time() - request["created_at"] > self.REQUEST_TTL:
            self.user_store.update_push_request(
                request_id, {"status": "expired"}
            )
            return {"success": False, "error": "Request expired"}

        # Verify response came from same device
        if device_context.get("device_id") != request["context"].get("device_id"):
            self.user_store.update_push_request(
                request_id, {"status": "device_mismatch"}
            )
            return {
                "success": False,
                "error": "Response from different device"
            }

        # Update status
        status = "approved" if approved else "denied"
        self.user_store.update_push_request(
            request_id,
            {"status": status, "responded_at": time.time()}
        )

        return {
            "success": approved,
            "message": "Acesso aprovado" if approved else "Acesso negado"
        }

    def cleanup_expired(self):
        """Clean up expired push requests."""
        expired = self.user_store.get_expired_pushes(self.REQUEST_TTL)
        for request in expired:
            self.user_store.update_push_request(
                request["request_id"], {"status": "expired"}
            )
```

### 2.2.5 Códigos de Backup

Códigos de backup são senhas de uso único geradas durante o registro de MFA, projetadas para recuperação em caso de perda do dispositivo.

```python
import secrets
import hashlib
import time

class BackupCodeService:
    """Backup codes for MFA recovery."""

    CODE_COUNT = 10
    CODE_PREFIX = "DS"  # DevSecurity prefix

    def __init__(self, user_store):
        self.user_store = user_store

    def generate_codes(self, user_id: str) -> list:
        """Generate backup codes and store hashed versions."""
        codes = []
        hashed_codes = []

        for _ in range(self.CODE_COUNT):
            raw = secrets.token_hex(5).upper()
            code = f"{self.CODE_PREFIX}-{raw[:5]}-{raw[5:]}"
            codes.append(code)
            hashed_codes.append({
                "hash": hashlib.sha256(code.encode()).hexdigest(),
                "used": False,
                "used_at": None,
            })

        self.user_store.store_backup_codes(user_id, hashed_codes)
        return codes

    def verify_code(self, user_id: str, code: str) -> dict:
        """Verify and consume a backup code."""
        stored_codes = self.user_store.get_backup_codes(user_id)
        if not stored_codes:
            return {"success": False, "error": "No backup codes"}

        code_hash = hashlib.sha256(code.upper().encode()).hexdigest()

        for i, stored in enumerate(stored_codes):
            if stored["used"]:
                continue
            if hmac.compare_digest(code_hash, stored["hash"]):
                # Mark as used
                self.user_store.mark_backup_code_used(user_id, i)
                remaining = sum(
                    1 for c in stored_codes if not c["used"]
                ) - 1  # -1 for current code

                return {
                    "success": True,
                    "remaining_codes": remaining,
                    "warning": (
                        "Re generating backup codes recommended"
                        if remaining < 3
                        else None
                    ),
                }

        return {"success": False, "error": "Invalid backup code"}

    def regenerate_codes(self, user_id: str) -> dict:
        """Regenerate all backup codes (invalidates old ones)."""
        # Invalidate old codes
        self.user_store.delete_backup_codes(user_id)

        # Generate new ones
        new_codes = self.generate_codes(user_id)

        return {
            "success": True,
            "codes": new_codes,
            "message": "Old codes invalidated. Save new codes securely."
        }
```

---

## 2.3 Biometria

### 2.3.1 Tipos de Biometria

A biometria usa características físicas ou comportamentais do usuário para autenticação. É o fator "algo que você é."

| Tipo | Descricao | Precisao | Custo | Spoofing |
|------|-----------|---------|-------|----------|
| Impressao digital | Padroes unicos dos dedos | Alta | Baixo-Medio | Medio (latext molds) |
| Reconhecimento facial | Geometria do rosto | Alta | Medio | Medio (fotos/3D masks) |
| Reconhecimento de iris | Padroes da iris | Muito Alta | Alto | Baixo |
| Reconhecimento de voz | Padroes vocais | Media | Baixo | Alto (deepfakes) |
| Reconhecimento de veina | Padroes vasculares | Muito Alta | Alto | Muito Baixo |
| Dinamica de digitacao | Ritmo e padrao de teclado | Media | Baixo | Medio |
| Assinatura | Padrao de escrita | Media | Baixo | Medio |

### 2.3.2 Biometria no Dispositivo (FIDO2/WebAuthn)

O modelo moderno de biometria não armazena dados biométricos no servidor. Em vez disso, o processamento ocorre inteiramente no dispositivo do usuário, e o servidor apenas verifica uma assinatura criptográfica.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    BIOMETRIA MODERNA (FIDO2)                         │
│                                                                      │
│  ┌──────────┐       ┌──────────────┐       ┌────────────┐           │
│  │ Usuario  │       │   Dispositivo│       │   Servidor │           │
│  └────┬─────┘       └──────┬───────┘       └─────┬──────┘           │
│       │                    │                     │                    │
│       │  1. Touch no sensor                    │                    │
│       │───────────────────▶│                     │                    │
│       │                    │                     │                    │
│       │  2. Leitura biométrica                  │                    │
│       │  (processada LOCALMENTE)                │                    │
│       │                    │                     │                    │
│       │  3. Verificacao biometrica              │                    │
│       │  (NO DISPOSITIVO)                       │                    │
│       │                    │                     │                    │
│       │                    │  4. Assinatura      │                    │
│       │                    │  criptografica      │                    │
│       │                    │────────────────────▶│                    │
│       │                    │                     │                    │
│       │                    │  5. Verificar       │                    │
│       │                    │  assinatura         │                    │
│       │                    │  (chave publica)    │                    │
│       │                    │                     │                    │
│       │                    │  6. Acesso          │                    │
│       │                    │  concedido          │                    │
│       │◀───────────────────│                     │                    │
│                                                                      │
│  SEGURANCA:                                                          │
│  ├── Dados biometricos NUNCA saem do dispositivo                     │
│  ├── Servidor so armazena chave publica                              │
│  ├── Chave privada fica no secure enclave do dispositivo             │
│  └── Clonagem fisica nao compromete o servidor                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3.3 Riscos da Biometria

| Risco | Descricao | Mitigacao |
|-------|-----------|-----------|
| Spoofing fisico | Fotos, molds, mascaras | Liveness detection, multimodal |
| Irreversibilidade | Se comprometida, nao pode ser "resetada" | Armazenamento no dispositivo, nao no servidor |
| Falsos positivos | Autenticacao indevida | Threshold ajustavel, MFA complementar |
| Falsos negativos | Negacao indevida | Multiplos fatores, fallback para codigo |
| Privacidade | Dados biometricos sensiveis | Processamento local, criptografia |
| Envelhecimento | Mudancas corporais ao longo do tempo | Re-treinamento periodico |
| Deepfakes | Videos sinteticos para spoofing facial | Liveness detection ativa |

### 2.3.4 Implementação de Biometria Complementar

```python
class BiometricAuthService:
    """Biometric authentication as a complementary factor."""

    def __init__(self, device_registry, audit_log):
        self.devices = device_registry
        self.audit = audit_log
        self.FIDO2_ATTESTATION = "fido2"

    def register_biometric_device(self, user_id: str,
                                  device_attestation: dict) -> dict:
        """Register a FIDO2-compatible biometric device."""
        # Verify attestation from device
        if not self._verify_attestation(device_attestation):
            return {"success": False, "error": "Invalid device attestation"}

        device_id = secrets.token_urlsafe(16)
        self.devices.register(user_id, {
            "device_id": device_id,
            "public_key": device_attestation["public_key"],
            "attestation": device_attestation["attestation"],
            "aaguid": device_attestation.get("aaguid"),
            "sign_count": device_attestation.get("sign_count", 0),
            "registered_at": time.time(),
            "last_used": None,
        })

        self.audit.log("biometric_device_registered", {
            "user_id": user_id,
            "device_id": device_id,
        })

        return {
            "success": True,
            "device_id": device_id,
            "message": "Dispositivo biometrico registrado"
        }

    def authenticate(self, user_id: str,
                     device_id: str, assertion: dict) -> dict:
        """Verify biometric assertion from registered device."""
        device = self.devices.get(user_id, device_id)
        if not device:
            return {"success": False, "error": "Unknown device"}

        # Verify assertion signature
        if not self._verify_assertion(device, assertion):
            self.audit.log("biometric_auth_failed", {
                "user_id": user_id,
                "device_id": device_id,
                "reason": "invalid_assertion",
            })
            return {"success": False, "error": "Authentication failed"}

        # Check sign count (clone detection)
        if assertion.get("sign_count", 0) <= device.get("sign_count", 0):
            self.audit.log("biometric_clone_detected", {
                "user_id": user_id,
                "device_id": device_id,
            })
            return {
                "success": False,
                "error": "Possible device clone detected"
            }

        # Update sign count and last used
        self.devices.update(user_id, device_id, {
            "sign_count": assertion.get("sign_count", 0),
            "last_used": time.time(),
        })

        self.audit.log("biometric_auth_success", {
            "user_id": user_id,
            "device_id": device_id,
        })

        return {
            "success": True,
            "message": "Autenticacao biometrica bem-sucedida"
        }

    def _verify_attestation(self, attestation: dict) -> bool:
        """Verify device attestation."""
        # Simplified: verify attestation signature
        # Real implementation uses FIDO2 metadata
        required_fields = ["public_key", "attestation", "aaguid"]
        return all(f in attestation for f in required_fields)

    def _verify_assertion(self, device: dict,
                         assertion: dict) -> bool:
        """Verify assertion signature using device's public key."""
        # Simplified: verify HMAC signature
        # Real implementation uses COSE/ES256 verification
        required_fields = ["authenticator_data", "client_data", "signature"]
        return all(f in assertion for f in required_fields)
```

---

## 2.4 Tokens de Hardware (YubiKey)

### 2.4.1 O que é um Token de Hardware?

Tokens de hardware como YubiKey são dispositivos físicos que armazenam chaves criptográficas e geram autenticação. Eles representam o fator "algo que você possui" de forma mais segura que um smartphone.

| Caracteristica | YubiKey 5 | Titan Security Key | Feitian BioPass |
|---------------|-----------|-------------------|-----------------|
| Formato | USB-A/C, NFC | USB-A/C, NFC | USB-A/C |
| Protocols | FIDO2, FIDO U2F, TOTP, OTP | FIDO2, FIDO U2F | FIDO2, FIDO U2F |
| Biometria | Nao | Nao | Sim (impressao digital) |
| Preco (USD) | $45-75 | $30-50 | $40-60 |
| Durabilidade | Resistente a agua, choque | Resistente a agua | Resistente a agua |
| Bateria | Nao necessaria | Nao necessaria | Nao necessaria |
| Multi-device | Sim (chaves redundantes) | Sim | Nao |

### 2.4.2 Como YubiKey Funciona

```
┌──────────────────────────────────────────────────────────────────────┐
│                    YUBIKEY - FLUXO DE AUTENTICACAO                    │
│                                                                      │
│  Registro:                                                           │
│  ┌──────────┐       ┌──────────────┐       ┌────────────┐           │
│  │ Usuario  │       │   YubiKey    │       │   Servidor │           │
│  └────┬─────┘       └──────┬───────┘       └─────┬──────┘           │
│       │                    │                     │                    │
│       │  1. Inserir YubiKey                    │                    │
│       │───────────────────▶│                     │                    │
│       │                    │                     │                    │
│       │  2. Touch no botao │                     │                    │
│       │───────────────────▶│                     │                    │
│       │                    │  3. Gerar par       │                    │
│       │                    │  de chaves          │                    │
│       │                    │  (internamente)     │                    │
│       │                    │                     │                    │
│       │                    │  4. Enviar creden.  │                    │
│       │                    │  + chave publica    │                    │
│       │                    │────────────────────▶│                    │
│       │                    │                     │                    │
│       │                    │  5. Armazenar       │                    │
│       │                    │  chave publica      │                    │
│       │                    │                     │                    │
│       │  6. Registro       │                     │                    │
│       │  concluido         │                     │                    │
│       │◀───────────────────│                     │                    │
│                                                                      │
│  Autenticacao:                                                       │
│  ┌──────────┐       ┌──────────────┐       ┌────────────┐           │
│  │ Usuario  │       │   YubiKey    │       │   Servidor │           │
│  └────┬─────┘       └──────┬───────┘       └─────┬──────┘           │
│       │                    │                     │                    │
│       │  1. Login com      │                     │                    │
│       │  senha             │                     │                    │
│       │────────────────────────────────────────▶│                    │
│       │                    │                     │                    │
│       │  2. Desafio        │                     │                    │
│       │◀────────────────────────────────────────│                    │
│       │                    │                     │                    │
│       │  3. Inserir YubiKey                     │                    │
│       │───────────────────▶│                     │                    │
│       │                    │                     │                    │
│       │  4. Touch no botao │                     │                    │
│       │───────────────────▶│                     │                    │
│       │                    │  5. Assinar desafio │                    │
│       │                    │  com chave privada  │                    │
│       │                    │                     │                    │
│       │                    │  6. Resposta        │                    │
│       │                    │────────────────────▶│                    │
│       │                    │                     │                    │
│       │                    │  7. Verificar       │                    │
│       │                    │  com chave publica  │                    │
│       │                    │                     │                    │
│       │  8. Acesso         │                     │                    │
│       │  concedido         │                     │                    │
│       │◀───────────────────│                     │                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.4.3 Implementação com WebAuthn

```python
import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class WebAuthnCredential:
    credential_id: bytes
    public_key: bytes
    sign_count: int
    aaguid: bytes
    user_id: str
    created_at: float
    last_used: Optional[float] = None

class WebAuthnService:
    """WebAuthn/FIDO2 server-side implementation."""

    RP_NAME = "DevSecurity"
    RP_ID = "devsecurity.com"
    ORIGIN = "https://devsecurity.com"

    def __init__(self, credential_store, audit_log):
        self.credentials = credential_store
        self.audit = audit_log
        self.challenges = {}  # Temporary challenge storage

    def start_registration(self, user_id: str,
                           username: str) -> dict:
        """Start WebAuthn registration ceremony."""
        challenge = secrets.token_bytes(32)

        # Store challenge for verification
        self.challenges[user_id] = {
            "challenge": challenge,
            "created_at": time.time(),
        }

        # Get existing credentials for user (for exclusion list)
        existing = self.credentials.get_all(user_id)
        exclude_credentials = [
            {"type": "public-key", "id": c.credential_id}
            for c in existing
        ]

        return {
            "rp": {
                "name": self.RP_NAME,
                "id": self.RP_ID,
            },
            "user": {
                "id": user_id.encode(),
                "name": username,
                "displayName": username,
            },
            "challenge": challenge,
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},   # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "authenticatorSelection": {
                "authenticatorAttachment": "cross-platform",
                "userVerification": "required",
                "residentKey": "preferred",
            },
            "timeout": 60000,
            "attestation": "direct",
            "excludeCredentials": exclude_credentials,
        }

    def complete_registration(self, user_id: str,
                             attestation_response: dict) -> dict:
        """Complete WebAuthn registration."""
        stored_challenge = self.challenges.get(user_id)
        if not stored_challenge:
            return {"success": False, "error": "No challenge found"}

        # Verify challenge
        if attestation_response["challenge"] != stored_challenge["challenge"]:
            return {"success": False, "error": "Challenge mismatch"}

        # Verify origin
        if attestation_response.get("origin") != self.ORIGIN:
            return {"success": False, "error": "Origin mismatch"}

        # Verify RP ID
        if attestation_response.get("rpId") != self.RP_ID:
            return {"success": False, "error": "RP ID mismatch"}

        # Parse attestation
        credential = WebAuthnCredential(
            credential_id=attestation_response["credential"]["id"],
            public_key=attestation_response["credential"]["publicKey"],
            sign_count=0,
            aaguid=attestation_response.get("aaguid", b""),
            user_id=user_id,
            created_at=time.time(),
        )

        self.credentials.save(credential)
        del self.challenges[user_id]

        self.audit.log("webauthn_registered", {
            "user_id": user_id,
            "credential_id": credential.credential_id.hex(),
        })

        return {
            "success": True,
            "credential_id": credential.credential_id.hex(),
        }

    def start_authentication(self, user_id: str) -> dict:
        """Start WebAuthn authentication ceremony."""
        challenge = secrets.token_bytes(32)

        self.challenges[user_id] = {
            "challenge": challenge,
            "created_at": time.time(),
        }

        # Get user's registered credentials
        existing = self.credentials.get_all(user_id)
        allow_credentials = [
            {"type": "public-key", "id": c.credential_id}
            for c in existing
        ]

        return {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": self.RP_ID,
            "allowCredentials": allow_credentials,
            "userVerification": "required",
        }

    def complete_authentication(self, user_id: str,
                                assertion_response: dict) -> dict:
        """Complete WebAuthn authentication."""
        stored_challenge = self.challenges.get(user_id)
        if not stored_challenge:
            return {"success": False, "error": "No challenge found"}

        # Verify challenge
        if assertion_response["challenge"] != stored_challenge["challenge"]:
            return {"success": False, "error": "Challenge mismatch"}

        # Find credential
        credential = self.credentials.get(
            user_id, assertion_response["credential"]["id"]
        )
        if not credential:
            return {"success": False, "error": "Unknown credential"}

        # Verify sign count (clone detection)
        new_count = assertion_response.get("sign_count", 0)
        if new_count <= credential.sign_count:
            self.audit.log("webauthn_clone_detected", {
                "user_id": user_id,
                "credential_id": credential.credential_id.hex(),
            })
            return {
                "success": False,
                "error": "Possible credential clone"
            }

        # Update sign count
        credential.sign_count = new_count
        credential.last_used = time.time()
        self.credentials.update(credential)

        del self.challenges[user_id]

        self.audit.log("webauthn_auth_success", {
            "user_id": user_id,
            "credential_id": credential.credential_id.hex(),
        })

        return {
            "success": True,
            "credential_id": credential.credential_id.hex(),
        }
```

---

## 2.5 Autenticação Baseada em Certificados

### 2.5.1 Mutual TLS (mTLS)

Em TLS padrão, apenas o servidor apresenta um certificado. Em Mutual TLS, o cliente também apresenta um certificado, autenticando-se ao servidor.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    MUTUAL TLS (mTLS)                                  │
│                                                                      │
│  TLS Normal:                                                         │
│  ├── Cliente verifica identidade do servidor                         │
│  └── Servidor confia no certificado da CA                            │
│                                                                      │
│  Mutual TLS:                                                         │
│  ├── Cliente verifica identidade do servidor                         │
│  ├── Servidor verifica identidade do cliente                         │
│  ├── Ambos verificam cadeia de certificados                          │
│  └── Autenticacao baseada em PKI (Public Key Infrastructure)        │
│                                                                      │
│  Fluxo:                                                              │
│  1. Cliente envia ClientHello                                        │
│  2. Servidor responde com ServerHello + ServerCertificate            │
│  3. Servidor envia CertificateRequest (solicitando cert. do cliente) │
│  4. Cliente envia ClientCertificate                                  │
│  5. Cliente envia CertificateVerify (assinatura do handshake)        │
│  6. Ambos verificam e estabelecem conexao                            │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.5.2 Casos de Uso

| Caso de Uso | Descricao | Alternativa |
|-------------|-----------|-------------|
| Servico-a-servico | Microservicos comunicando internamente | API Keys + mTLS |
| IoT | Dispositivos conectando a infraestrutura | Tokens de dispositivo |
| VPN corporativa | Acesso remoto a rede | Certificados + MFA |
| PKI interno | Infraestrutura de certificacao propria | HSM + CA interna |

### 2.5.3 Implementação Básica de mTLS

```python
import ssl
import socket
import hashlib

class MutualTLSService:
    """Mutual TLS configuration for server and client."""

    @staticmethod
    def create_server_context(
        certfile: str,
        keyfile: str,
        ca_certfile: str,
        check_client_cert: bool = True
    ) -> ssl.SSLContext:
        """Create server-side mTLS context."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        context.load_verify_locations(ca_certfile)

        if check_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = False  # Client cert has no hostname
        else:
            context.verify_mode = ssl.CERT_OPTIONAL

        # Minimum TLS 1.2
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Strong cipher suites
        context.set_ciphers(
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20"
        )

        return context

    @staticmethod
    def create_client_context(
        certfile: str,
        keyfile: str,
        ca_certfile: str,
        server_hostname: str
    ) -> ssl.SSLContext:
        """Create client-side mTLS context."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_cert_chain(certfile, keyfile)
        context.load_verify_locations(ca_certfile)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context

    @staticmethod
    def extract_client_identity(ssl_socket) -> dict:
        """Extract client identity from mTLS session."""
        cert = ssl_socket.getpeercert()
        if not cert:
            return {"authenticated": False}

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))

        return {
            "authenticated": True,
            "subject": subject.get("commonName", ""),
            "organization": subject.get("organizationName", ""),
            "issuer": issuer.get("commonName", ""),
            "serial": cert.get("serialNumber", ""),
            "not_before": cert.get("notBefore", ""),
            "not_after": cert.get("notAfter", ""),
        }
```

---

## 2.6 Autenticação Baseada em Risco (Risk-Based)

### 2.6.1 O que é Autenticação Baseada em Risco?

A autenticação baseada em risco adapta os requisitos de autenticação ao contexto de cada requisição. Em vez de exigir o mesmo nível de autenticação sempre, ela ajusta dinamicamente baseada em fatores de risco.

```
┌──────────────────────────────────────────────────────────────────────┐
│              AUTENTICACAO BASEADA EM RISCO                           │
│                                                                      │
│  Baixo Risco:                                                        │
│  ├── Mesmo dispositivo de sempre                                     │
│  ├── Mesma localizacao geografica                                    │
│  ├── Horario normal de uso                                           │
│  └── Acao nao sensivel                                               │
│  → Apenas senha (ou sessao existente)                                │
│                                                                      │
│  Medio Risco:                                                        │
│  ├── Novo dispositivo                                                 │
│  ├── Localizacao incomum                                             │
│  ├── Horario atipico                                                 │
│  └── Muitas tentativas recentes                                      │
│  → Senha + MFA (TOTP ou Push)                                        │
│                                                                      │
│  Alto Risco:                                                         │
│  ├── IP de TOR ou VPN conhecida                                      │
│  ├── Localizacao impossivel (viagem impossivel)                      │
│  ├── Tentativas de brute force detectadas                            │
│  ├── Operacao altamente sensivel                                     │
│  └── Padrao de acesso anomalo                                        │
│  → Senha + MFA + Verificacao adicional + Notificacao                 │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.6.2 Implementação

```python
import time
import math
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class RiskFactors:
    ip_address: str
    user_agent: str
    timestamp: float
    latitude: float = 0.0
    longitude: float = 0.0
    is_known_device: bool = False
    is_known_location: bool = False
    failed_attempts_recent: int = 0
    operation_sensitivity: str = "low"  # low, medium, high

class RiskEngine:
    """Calculate authentication risk score."""

    def __init__(self, geo_service, device_registry, audit_log):
        self.geo = geo_service
        self.devices = device_registry
        self.audit = audit_log

    def calculate_risk(self, user_id: str,
                       factors: RiskFactors) -> float:
        """Calculate risk score from 0.0 (safe) to 1.0 (dangerous)."""
        score = 0.0
        weights = []

        # Factor 1: Known device (0.0 - 0.3)
        device_risk = 0.0 if factors.is_known_device else 0.3
        score += device_risk * 0.25
        weights.append(("known_device", device_risk, 0.25))

        # Factor 2: Geographic location (0.0 - 0.4)
        geo_risk = self._calculate_geo_risk(user_id, factors)
        score += geo_risk * 0.3
        weights.append(("geo_risk", geo_risk, 0.3))

        # Factor 3: Time-based patterns (0.0 - 0.2)
        time_risk = self._calculate_time_risk(user_id, factors)
        score += time_risk * 0.15
        weights.append(("time_risk", time_risk, 0.15))

        # Factor 4: Failed attempts (0.0 - 0.3)
        attempt_risk = min(factors.failed_attempts_recent / 10, 1.0) * 0.3
        score += attempt_risk * 0.15
        weights.append(("attempt_risk", attempt_risk, 0.15))

        # Factor 5: Operation sensitivity (0.0 - 0.2)
        sensitivity_map = {"low": 0.0, "medium": 0.1, "high": 0.2}
        sensitivity_risk = sensitivity_map.get(
            factors.operation_sensitivity, 0.0
        )
        score += sensitivity_risk * 0.15
        weights.append(("sensitivity", sensitivity_risk, 0.15))

        # Log risk calculation
        self.audit.log("risk_score_calculated", {
            "user_id": user_id,
            "score": round(score, 3),
            "factors": weights,
        })

        return min(score, 1.0)

    def _calculate_geo_risk(self, user_id: str,
                           factors: RiskFactors) -> float:
        """Calculate geographic risk based on impossible travel."""
        last_location = self.devices.get_last_location(user_id)
        if not last_location:
            return 0.5  # Unknown location = medium risk

        distance = self._haversine(
            last_location["lat"], last_location["lon"],
            factors.latitude, factors.longitude
        )
        time_diff = factors.timestamp - last_location["timestamp"]

        if time_diff <= 0:
            return 1.0

        speed_kmh = (distance / time_diff) * 3600

        if speed_kmh > 1000:  # Faster than commercial flight
            return 1.0
        elif speed_kmh > 500:
            return 0.7
        elif distance > 500:  # Different country/region
            return 0.4
        elif factors.is_known_location:
            return 0.0
        else:
            return 0.2

    def _calculate_time_risk(self, user_id: str,
                            factors: RiskFactors) -> float:
        """Calculate risk based on time patterns."""
        hour = time.gmtime(factors.timestamp).tm_hour

        # Get user's typical usage hours
        typical_hours = self.devices.get_typical_hours(user_id)
        if not typical_hours:
            return 0.3

        if hour in typical_hours:
            return 0.0
        elif hour in [h for h in range(6, 23)]:  # Normal waking hours
            return 0.2
        else:  # Late night / very early morning
            return 0.5

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in km."""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        return R * 2 * math.asin(math.sqrt(a))


class AdaptiveAuthPolicy:
    """Determine authentication requirements based on risk score."""

    # Risk thresholds
    LOW_RISK = 0.3
    MEDIUM_RISK = 0.6
    HIGH_RISK = 0.8

    def determine_requirements(self, risk_score: float,
                               user_mfa_enabled: bool) -> dict:
        """Determine what authentication is required."""
        if risk_score < self.LOW_RISK:
            return {
                "level": "low",
                "requires_password": True,
                "requires_mfa": False,
                "requires_additional_verification": False,
                "session_duration": 3600,
                "description": "Login normal",
            }
        elif risk_score < self.MEDIUM_RISK:
            return {
                "level": "medium",
                "requires_password": True,
                "requires_mfa": user_mfa_enabled,
                "requires_additional_verification": False,
                "session_duration": 1800,
                "description": "MFA recomendado" if user_mfa_enabled else "MFA necessario",
            }
        elif risk_score < self.HIGH_RISK:
            return {
                "level": "high",
                "requires_password": True,
                "requires_mfa": True,
                "requires_additional_verification": True,
                "session_duration": 900,
                "description": "Verificacao adicional necessaria",
            }
        else:
            return {
                "level": "critical",
                "requires_password": True,
                "requires_mfa": True,
                "requires_additional_verification": True,
                "requires_admin_review": True,
                "session_duration": 300,
                "description": "Acesso bloqueado, revisao manual necessaria",
                "alert_admin": True,
            }
```

---

## 2.7 Autenticação Adaptativa

### 2.7.1 Autenticação Adaptativa vs Baseada em Risco

Embora relacionados, estes conceitos são distintos:

| Aspecto | Baseada em Risco | Adaptativa |
|---------|-----------------|------------|
| Base de decisao | Analise de contexto atual | Historico do usuario + contexto |
| Granularidade | Por requisicao | Por sessao |
| Dados usados | IP, dispositivo, localizacao | Aprendizado de padroes ao longo do tempo |
| Evolucao | Estatica (regras fixas) | Dinamica (aprende com o usuario) |
| Complexidade | Media | Alta (requer ML/analytics) |

### 2.7.2 Sistema Adaptativo Completo

```python
import statistics
from collections import defaultdict

class AdaptiveAuthService:
    """Authentication service that adapts to user behavior patterns."""

    def __init__(self, user_store, risk_engine, notification_service):
        self.user_store = user_store
        self.risk_engine = risk_engine
        self.notifications = notification_service
        self.behavior_store = defaultdict(lambda: {
            "locations": [],
            "devices": [],
            "hours": [],
            "ips": [],
            "browsers": [],
        })

    def should_require_mfa(self, user_id: str,
                          context: dict) -> dict:
        """Determine if MFA should be required based on adaptive analysis."""
        behavior = self.behavior_store[user_id]

        checks = []

        # Check 1: Is this a known device?
        device_fingerprint = self._fingerprint_device(context)
        known_device = device_fingerprint in behavior["devices"]
        checks.append({
            "check": "known_device",
            "passed": known_device,
            "weight": 0.3,
        })

        # Check 2: Is this a familiar IP range?
        ip_known = context.get("ip") in behavior["ips"]
        checks.append({
            "check": "known_ip",
            "passed": ip_known,
            "weight": 0.25,
        })

        # Check 3: Is this a typical login hour?
        hour = time.gmtime().tm_hour
        typical_hours = behavior["hours"]
        hour_is_typical = (
            len(typical_hours) == 0 or
            hour in [h for h in range(
                max(0, min(typical_hours) - 2),
                min(23, max(typical_hours) + 2)
            )]
        )
        checks.append({
            "check": "typical_hour",
            "passed": hour_is_typical,
            "weight": 0.2,
        })

        # Check 4: Is this a familiar location?
        location = self._geolocate(context.get("ip"))
        location_known = any(
            self._locations_match(location, loc)
            for loc in behavior["locations"]
        )
        checks.append({
            "check": "known_location",
            "passed": location_known,
            "weight": 0.25,
        })

        # Calculate decision
        failed_weight = sum(
            c["weight"] for c in checks if not c["passed"]
        )

        result = {
            "require_mfa": failed_weight > 0.3,
            "checks": checks,
            "confidence": 1.0 - failed_weight,
            "reason": self._generate_reason(checks),
        }

        # Update behavior profile
        self._update_behavior(user_id, context)

        return result

    def _fingerprint_device(self, context: dict) -> str:
        """Create device fingerprint from context."""
        components = [
            context.get("user_agent", ""),
            context.get("screen_resolution", ""),
            context.get("timezone", ""),
            context.get("language", ""),
        ]
        return hashlib.sha256(
            "|".join(components).encode()
        ).hexdigest()[:16]

    def _geolocate(self, ip: str) -> dict:
        """Get location from IP address."""
        # Simplified: in production use MaxMind or similar
        return {"lat": 0, "lon": 0, "country": "unknown"}

    def _locations_match(self, loc1: dict, loc2: dict,
                        threshold_km: float = 50) -> bool:
        """Check if two locations are within threshold."""
        distance = self.risk_engine._haversine(
            loc1["lat"], loc1["lon"],
            loc2["lat"], loc2["lon"]
        )
        return distance <= threshold_km

    def _update_behavior(self, user_id: str, context: dict):
        """Update user behavior profile."""
        behavior = self.behavior_store[user_id]
        behavior["devices"].append(
            self._fingerprint_device(context)
        )
        behavior["ips"].append(context.get("ip"))
        behavior["hours"].append(time.gmtime().tm_hour)
        location = self._geolocate(context.get("ip"))
        behavior["locations"].append(location)

        # Keep only recent entries (last 100)
        for key in behavior:
            if len(behavior[key]) > 100:
                behavior[key] = behavior[key][-100:]

    def _generate_reason(self, checks: list) -> str:
        """Generate human-readable reason for MFA decision."""
        failed = [c["check"] for c in checks if not c["passed"]]
        if not failed:
            return "Padrao de acesso familiar"
        reasons = {
            "known_device": "Dispositivo nao reconhecido",
            "known_ip": "Endereco IP unfamiliar",
            "typical_hour": "Horario atipico de acesso",
            "known_location": "Localizacao nao reconhecida",
        }
        return "; ".join(reasons.get(f, f) for f in failed)
```

---

## 2.8 Tabela Comparativa de Todos os Métodos

| Metodo | Fator | Seguranca | Custo | UX | Spoofing | Revocacao | Maturidade |
|--------|-------|-----------|-------|-----|----------|-----------|------------|
| Senha | Sabe | Baixa-Media | Muito Baixo | Medio | Facil | Facil | Maxima |
| TOTP | Possui | Media-Alta | Baixo | Medio | Medio | Facil | Alta |
| SMS OTP | Possui | Media | Medio | Alto | Medio | Facil | Alta |
| Push MFA | Possui | Alta | Medio | Muito Alto | Medio-Dificil | Facil | Alta |
| Codigo de backup | Sabe | Media | Baixo | Baixo | Medio | Facil | Alta |
| Biometria (dispositivo) | E | Muito Alta | Baixo | Muito Alto | Baixo | Dificil | Alta |
| YubiKey | Possui | Muito Alta | Alto | Medio | Muito Baixo | Facil | Alta |
| WebAuthn/Passkey | Possui+E | Muito Alta | Baixo | Alto | Muito Baixo | Facil | Media-Alta |
| Certificado (mTLS) | Possui | Muito Alta | Alto | Baixo | Muito Baixo | Media | Alta |
| Risk-Based | Contexto | Variavel | Alto | Alto | Variavel | Variavel | Media |
| Adaptive | Contexto+Historico | Alta | Muito Alto | Alto | Baixo | Variavel | Media |

---

## 2.9 Níveis de Segurança

### 2.9.1 Matriz de Autenticação por Nível

```
┌──────────────────────────────────────────────────────────────────────┐
│              NIVEIS DE SEGURANCA vs METODOS                           │
│                                                                      │
│  Nivel 1 - Publico:                                                  │
│  ├── Leitura de conteudo publico                                     │
│  ├── Nenhuma autenticacao necessaria                                 │
│  └── Metodos: N/A                                                    │
│                                                                      │
│  Nivel 2 - Basico:                                                   │
│  ├── Acesso a perfil proprio                                         │
│  ├── Operacoes nao sensiveis                                         │
│  └── Metodos: Senha OU Passkey                                       │
│                                                                      │
│  Nivel 3 - Intermediario:                                            │
│  ├── Acesso a dados pessoais                                         │
│  ├── Operacoes com efeito real                                       │
│  └── Metodos: Senha + MFA (TOTP/SMS/Push)                           │
│                                                                      │
│  Nivel 4 - Avancado:                                                 │
│  ├── Acesso a dados sensiveis de terceiros                           │
│  ├── Operacoes financeiras                                           │
│  └── Metodos: Senha + MFA forte (YubiKey/WebAuthn)                   │
│                                                                      │
│  Nivel 5 - Critico:                                                  │
│  ├── Acesso administrativo total                                     │
│  ├── Mudanca de configuracoes de seguranca                           │
│  ├── Operacoes irreversiveis em massa                                │
│  └── Metodos: mTLS + MFA forte + Revisao humana + Session curta     │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.9.2 Implementação de Niveis

```python
class AuthenticationLevelPolicy:
    """Map operation sensitivity to authentication requirements."""

    LEVELS = {
        1: {
            "name": "public",
            "methods": [],
            "description": "Acesso publico",
        },
        2: {
            "name": "basic",
            "methods": ["password", "passkey"],
            "mfa_required": False,
            "session_max_hours": 24,
            "description": "Autenticacao basica",
        },
        3: {
            "name": "standard",
            "methods": ["password", "passkey"],
            "mfa_required": True,
            "mfa_methods": ["totp", "sms", "push"],
            "session_max_hours": 8,
            "description": "Autenticacao com MFA",
        },
        4: {
            "name": "elevated",
            "methods": ["password", "passkey"],
            "mfa_required": True,
            "mfa_methods": ["webauthn", "yubikey"],
            "session_max_hours": 4,
            "require_fresh_auth": True,
            "description": "Autenticacao forte",
        },
        5: {
            "name": "critical",
            "methods": ["password"],
            "mfa_required": True,
            "mfa_methods": ["webauthn", "yubikey"],
            "require_mtls": True,
            "session_max_hours": 1,
            "require_admin_approval": True,
            "description": "Autenticacao critica",
        },
    }

    def get_requirements(self, level: int) -> dict:
        """Get authentication requirements for a security level."""
        if level not in self.LEVELS:
            raise ValueError(f"Invalid security level: {level}")
        return self.LEVELS[level]

    def check_access(self, user_auth: dict,
                     required_level: int) -> dict:
        """Check if user's authentication meets required level."""
        requirements = self.get_requirements(required_level)

        # Check primary authentication
        if user_auth.get("method") not in requirements.get("methods", []):
            return {
                "allowed": False,
                "reason": "Metodo de autenticacao nao aceito para este nivel"
            }

        # Check MFA
        if requirements.get("mfa_required"):
            if not user_auth.get("mfa_verified"):
                return {
                    "allowed": False,
                    "reason": "MFA obrigatorio para este nivel"
                }
            if requirements.get("mfa_methods"):
                if user_auth.get("mfa_method") not in requirements["mfa_methods"]:
                    return {
                        "allowed": False,
                        "reason": f"MFA deve ser: {', '.join(requirements['mfa_methods'])}"
                    }

        # Check session freshness
        if requirements.get("require_fresh_auth"):
            auth_age = user_auth.get("auth_age_seconds", 0)
            max_age = requirements.get("session_max_hours", 1) * 3600
            if auth_age > max_age:
                return {
                    "allowed": False,
                    "reason": "Re-autenticacao necessaria (sessao antiga)"
                }

        return {"allowed": True}
```

---

## 2.10 Caso Misantropi4: Por Que MFA Teria Prevenido o Ataque

### 2.10.1 Análise Detalhada

O ataque Misantropi4 ao IDAP é um caso de estudo perfeito para demonstrar por que MFA não é opcional em sistemas de alto impacto.

**Cenário do ataque:**

```
┌──────────────────────────────────────────────────────────────────────┐
│              ANALISE: COMO MFA BLOQUEARIA O ATAQUE                    │
│                                                                      │
│  ETAPA 1: Acesso as credenciais                                      │
│  ├── Atacante obtem email/senha de funcionario publico               │
│  ├── Credenciais vazadas de servidor publico sem criptografia        │
│  └── Senha nunca rotacionada (mesma ha anos)                         │
│                                                                      │
│  SEM MFA: Acesso imediato ao sistema                                 │
│  COM MFA: Atacante bloqueado — nao possui segundo fator               │
│                                                                      │
│  ETAPA 2: Bypass do captcha                                           │
│  ├── Captcha: "2 + 2 = ?"                                            │
│  ├── Script automatizado resolve em milissegundos                    │
│  └── Sem limite de tentativas por IP                                 │
│                                                                      │
│  SEM MFA: Captcha trivialmente bypassado                             │
│  COM MFA: Captcha irrelevante — segundo fator necessario             │
│                                                                      │
│  ETAPA 3: Acesso ao painel                                           │
│  ├── Sistema nao exigia MFA para operacoes sensiveis                 │
│  ├── Nenhuma verificacao de contexto (IP, dispositivo)               │
│  └── Sessao criada sem restricoes                                    │
│                                                                      │
│  SEM MFA: Acesso completo ao painel de alertas                       │
│  COM MFA: Mesmo com credenciais, sem TOTP/YubiKey, acesso negado    │
│                                                                      │
│  ETAPA 4: Envio de alertas falsos                                    │
│  ├── Atacante envia alertas de emergencia para regioes inteiras      │
│  ├── Sem verificacao de permissao por regiao                         │
│  └── Sem validacao de autoridade para envio                          │
│                                                                      │
│  SEM MFA: Alertas enviados com sucesso                               │
│  COM MFA: Atacante nunca teria chegado a esta etapa                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.10.2 Qual MFA Teria Sido Mais Eficaz?

| Metodo MFA | Eficacia contra Misantropi4 | Viabilidade no IDAP | Custo |
|-----------|---------------------------|---------------------|-------|
| TOTP | Alta — teria bloqueado o atacante | Alta — func. publicos ja usam smartphones | Baixo |
| SMS OTP | Alta — teria bloqueado o atacante | Alta — numero de telefone ja cadastrado | Medio |
| Push MFA | Muito Alta — teria bloqueado + notificado | Media — requer app instalado | Medio |
| YubiKey | Muito Alta — teria bloqueado absolutamente | Baixa — custo por funcionario | Alto |
| Biometria | Muito Alta — impossivel de spoofar remotamente | Baixa — requer hardware | Alto |

### 2.10.3 Recomendação Final

Para sistemas governamentais como o IDAP, a recomendação é:

1. **Mínimo absoluto**: TOTP obrigatório para todos os operadores
2. **Ideal**: YubiKey ou WebAuthn para operadores de envio de alertas
3. **Complementar**: Push MFA com geolocalização para detecção de anomalias
4. **Essencial**: Re-autenticação para cada operação de envio de alerta

O custo de implementar MFA teria sido uma fração do dano causado pelo ataque — tanto em termos financeiros quanto em termos de confiança pública no sistema.

---

## 2.11 Resumo e Próximos Passos

Neste capítulo, exploramos em profundidade cada método de autenticação disponível:

- **Senhas** continuam sendo o método mais usado, mas são o mais vulnerável. Políticas baseadas em evidências (NIST) são superiores a requisitos de complexidade arbitrários.
- **MFA** é a defesa mais eficaz contra credenciais comprometidas. TOTP, SMS, Push e códigos de backup oferecem diferentes tradeoffs de segurança e usabilidade.
- **Biometria** moderna (FIDO2/WebAuthn) processa dados no dispositivo, nunca no servidor, oferecendo segurança máxima sem comprometer privacidade.
- **Tokens de hardware** (YubiKey) são o gold standard para autenticação, mas exigem investimento em hardware.
- **Certificados (mTLS)** são ideais para comunicação servico-a-servico.
- **Autenticação baseada em risco e adaptativa** ajustam dinamicamente os requisitos de autenticação ao contexto.
- **Níveis de segurança** permitem mapear operações a métodos de autenticação apropriados.
- O **caso Misantropi4** demonstra conclusivamente que MFA teria prevenido o ataque em todas as suas etapas.

No próximo capítulo, mergulharemos na **segurança de senhas** — hashing, salting, pepper, algoritmos comparados, políticas de recuperação, e como proteger credenciais contra comprometimento.

---

## 2.12 Exercícios

1. **Seleção de Método**: Para um banco online que precisa autenticar clientes para transferências acima de R$ 10.000, qual combinação de métodos você recomendaria? Justifique.
2. **Análise de Risco**: Implemente um Risk Engine que calcule score de risco baseado em 5 fatores e determine se MFA deve ser exigido.
3. **Comparações**: Crie uma tabela comparativa entre TOTP, Push e SMS MFA considerando: custo, usabilidade, segurança contra ataques específicos, e requisitos de infraestrutura.
4. **Caso Misantropi4**: Descreva em detalhes como cada tipo de MFA (TOTP, SMS, Push, YubiKey) teria impedido o ataque em cada etapa.
5. **Implementação**: Implemente um sistema de autenticação adaptativa que mude os requisitos de autenticação baseado no histórico de comportamento do usuário.

---

## 2.13 Autenticação Passwordless

### 2.13.1 O Movimento Passwordless

A indústria está migrando para autenticação sem senhas (passwordless), onde o usuário se autentica usando fatores que não envolvem memorização de credenciais textuais.

```
┌──────────────────────────────────────────────────────────────────────┐
│              EVOLUCAO DA AUTENTICACAO                                │
│                                                                      │
│  Passado:                                                            │
│  ├── Senha unica (fator unico)                                       │
│  ├── Senha + OTP via SMS (2FA fraco)                                 │
│  └── Problemas: phishing, credential stuffing, reuso                 │
│                                                                      │
│  Presente:                                                           │
│  ├── Senha + TOTP/Push (MFA)                                         │
│  ├── Passkeys/WebAuthn (passwordless)                                │
│  └── Melhorias: resistencia a phishing                               │
│                                                                      │
│  Futuro:                                                             │
│  ├── Passkeys como metodo primario                                   │
│  ├── Biometria continua                                              │
│  ├── Verificacao de contexto continuo                                │
│  └── Zero trust (nunca confiar, sempre verificar)                    │
│                                                                      │
│  PASSKEYS:                                                           │
│  ├── Credenciais criptograficas pareadas com o dispositivo           │
│  ├── Chave privada nunca sai do dispositivo                          │
│  ├── Servidor so armazena chave publica                              │
│  ├── Resistente a phishing (vinculada ao dominio)                    │
│  └── Sincronizadas entre dispositivos (via iCloud/Google)            │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.13.2 Implementação de Passkeys

```python
import secrets
import hashlib
import time
from typing import Dict, List, Optional

class PasskeyService:
    """Passkey/WebAuthn passwordless authentication service."""

    RP_NAME = "DevSecurity"
    RP_ID = "devsecurity.com"
    ORIGIN = "https://devsecurity.com"

    def __init__(self, credential_store, audit_log):
        self.credentials = credential_store
        self.audit = audit_log
        self.challenges = {}

    def start_registration(self, user_id: str,
                           username: str) -> dict:
        """Start passkey registration (create)."""
        challenge = secrets.token_bytes(32)
        self.challenges[user_id] = {
            "challenge": challenge,
            "created_at": time.time(),
        }

        existing = self.credentials.get_all(user_id)
        exclude = [{"type": "public-key", "id": c.credential_id}
                   for c in existing]

        return {
            "rp": {"name": self.RP_NAME, "id": self.RP_ID},
            "user": {
                "id": user_id.encode(),
                "name": username,
                "displayName": username,
            },
            "challenge": challenge,
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "userVerification": "required",
                "residentKey": "required",
            },
            "timeout": 60000,
            "attestation": "none",
            "excludeCredentials": exclude,
        }

    def complete_registration(self, user_id: str,
                             attestation: dict) -> dict:
        """Complete passkey registration."""
        stored = self.challenges.get(user_id)
        if not stored:
            return {"success": False, "error": "No challenge"}

        if attestation["challenge"] != stored["challenge"]:
            return {"success": False, "error": "Challenge mismatch"}

        credential = {
            "credential_id": attestation["credential"]["id"],
            "public_key": attestation["credential"]["publicKey"],
            "sign_count": 0,
            "user_id": user_id,
            "created_at": time.time(),
            "type": "passkey",
        }

        self.credentials.save(credential)
        del self.challenges[user_id]

        self.audit.log("passkey_registered", {
            "user_id": user_id,
            "credential_id": credential["credential_id"].hex(),
        })

        return {"success": True}

    def start_authentication(self,
                            username: Optional[str] = None) -> dict:
        """Start passkey authentication (get)."""
        challenge = secrets.token_bytes(32)

        # Store challenge temporarily
        challenge_id = secrets.token_urlsafe(16)
        self.challenges[challenge_id] = {
            "challenge": challenge,
            "created_at": time.time(),
        }

        result = {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": self.RP_ID,
            "userVerification": "required",
        }

        if username:
            user = self.credentials.get_user_by_username(username)
            if user:
                existing = self.credentials.get_all(user["id"])
                result["allowCredentials"] = [
                    {"type": "public-key", "id": c.credential_id}
                    for c in existing
                ]

        return result

    def complete_authentication(self, assertion: dict) -> dict:
        """Complete passkey authentication."""
        # Find matching credential
        credential = self.credentials.get_by_id(
            assertion["credential"]["id"]
        )
        if not credential:
            return {"success": False, "error": "Unknown credential"}

        # Verify assertion
        # (simplified - real implementation verifies COSE signature)
        new_count = assertion.get("sign_count", 0)
        if new_count <= credential.get("sign_count", 0):
            self.audit.log("passkey_clone_detected", {
                "user_id": credential["user_id"],
            })
            return {
                "success": False,
                "error": "Possible clone detected"
            }

        # Update credential
        credential["sign_count"] = new_count
        credential["last_used"] = time.time()
        self.credentials.update(credential)

        self.audit.log("passkey_auth_success", {
            "user_id": credential["user_id"],
        })

        return {
            "success": True,
            "user_id": credential["user_id"],
        }
```

---

## 2.14 Single Sign-On (SSO) e Federação

### 2.14.1 Conceitos de SSO

Single Sign-On permite que o usuário se autentique uma vez e tenha acesso a múltiplos sistemas sem precisar fazer login novamente.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    SSO - SINGLE SIGN-ON                               │
│                                                                      │
│  SEM SSO:                                                            │
│  ├── Login no Email: user@email.com / senha1                         │
│  ├── Login no CRM: user@crm.com / senha2                             │
│  ├── Login no ERP: user@erp.com / senha3                             │
│  ├── Login no Slack: user@slack.com / senha4                         │
│  └── 4 logins, 4 senhas, 4 riscos                                    │
│                                                                      │
│  COM SSO:                                                            │
│  ├── Login no Identity Provider (Google/Azure AD/Keycloak)           │
│  ├── Acesso ao Email: automatico                                     │
│  ├── Acesso ao CRM: automatico                                       │
│  ├── Acesso ao ERP: automatico                                       │
│  ├── Acesso ao Slack: automatico                                     │
│  └── 1 login, 1 identidade, controle centralizado                    │
│                                                                      │
│  BENEFICIOS:                                                         │
│  ├── Menos senhas = menos riscos                                     │
│  ├── Provisionamento centralizado                                    │
│  ├── Desprovisionamento imediato (desligamento)                      │
│  ├── Auditoria centralizada                                          │
│  └── MFA unificado                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.14.2 SAML 2.0 vs OpenID Connect

| Aspecto | SAML 2.0 | OpenID Connect |
|---------|---------|----------------|
| Protocolo | XML-based | JSON/REST-based |
| Complexidade | Alta | Media |
| Performance | Mais lento (XML parsing) | Mais rapido (JSON) |
| Mobile support | Limitado | Nativo |
| Web SSO | Excelente | Excelente |
| API auth | Nao suporta | Suporta |
| Adoption | Enterprise legado | Moderno |
| Tokens | SAML Assertion | JWT (ID Token) |

---

## 2.15 Autenticação em Dispositivos Móveis

### 2.15.1 Desafios Específicos

A autenticação em dispositivos móveis enfrenta desafios únicos que não existem em desktop:

| Desafio | Descricao | Mitigacao |
|---------|-----------|-----------|
| Tela pequena | Digitacao dificil, UX ruim | Biometria, passkeys |
| Conexao instavel | Timeouts, retries | Tokens offline, caching |
| App compartilhado | Mesmo dispositivo, multiplos usuarios | Biometria por usuario |
| Jailbreak/Root | Controles de seguranca comprometidos | Detecao de jailbreak |
| Keylogger | Captura de teclado | Biometria, tokens hardware |
| App cloning | Apps falsos interceptando credenciais | Certificate pinning |
| Screen recording | Captura de tela com senhas | Blindagem de tela |

### 2.15.2 Implementação Mobile Segura

```python
class MobileAuthService:
    """Mobile-specific authentication service."""

    def __init__(self, device_registry, push_service):
        self.devices = device_registry
        self.push = push_service

    def authenticate_mobile(self, device_id: str,
                           context: dict) -> dict:
        """Mobile authentication with device binding."""
        # Verify device is registered
        device = self.devices.get(device_id)
        if not device:
            return {
                "success": False,
                "error": "Device not registered"
            }

        # Check device integrity
        if not self._verify_device_integrity(device, context):
            self._flag_suspicious_device(device_id)
            return {
                "success": False,
                "error": "Device integrity check failed"
            }

        # Check for jailbreak/root
        if context.get("is_jailbroken"):
            return {
                "success": False,
                "error": "Jailbroken/rooted devices not allowed"
            }

        # Use biometric if available
        if context.get("biometric_available"):
            return self._auth_with_biometric(device_id, context)

        # Fall back to push notification
        return self._auth_with_push(device_id, context)

    def _verify_device_integrity(self, device: dict,
                                context: dict) -> bool:
        """Verify device hasn't been tampered with."""
        # Check device fingerprint matches
        expected_fingerprint = device.get("fingerprint")
        actual_fingerprint = context.get("device_fingerprint")

        if expected_fingerprint != actual_fingerprint:
            return False

        # Check for emulator/simulator
        if context.get("is_emulator"):
            return False

        # Check OS version (not too old)
        os_version = context.get("os_version", "0")
        if self._is_os_too_old(os_version):
            return False

        return True

    def _auth_with_biometric(self, device_id: str,
                            context: dict) -> dict:
        """Authenticate using device biometric."""
        # Request biometric from device
        return {
            "method": "biometric",
            "device_id": device_id,
            "challenge": secrets.token_urlsafe(32),
        }

    def _auth_with_push(self, device_id: str,
                       context: dict) -> dict:
        """Authenticate using push notification."""
        return self.push.send_push_request(
            user_id=device_id,
            context=context,
        )

    def _flag_suspicious_device(self, device_id: str):
        """Flag device as suspicious."""
        self.devices.update(device_id, {
            "flagged": True,
            "flagged_at": time.time(),
            "flag_reason": "integrity_check_failed",
        })

    def _is_os_too_old(self, version: str) -> bool:
        """Check if OS version is too old for security."""
        # Simplified: in production, check against known vulnerable versions
        try:
            major = int(version.split(".")[0])
            return major < 12  # iOS 12+ / Android 12+
        except (ValueError, IndexError):
            return True
```

---

## 2.16 Autenticação em APIs: Padrões e Boas Práticas

### 2.16.1 Autenticação para APIs Públicas

```python
class PublicAPIService:
    """Authentication for public APIs with multiple methods."""

    def __init__(self, api_key_store, jwt_verifier):
        self.api_keys = api_key_store
        self.jwt = jwt_verifier

    def authenticate(self, request) -> dict:
        """Authenticate API request."""
        # Method 1: API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return self._authenticate_api_key(api_key)

        # Method 2: Bearer Token (JWT)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self._authenticate_jwt(token)

        # Method 3: HMAC Signature (for webhooks)
        signature = request.headers.get("X-Hub-Signature-256")
        if signature:
            return self._authenticate_hmac(
                request.body, signature, request.headers
            )

        return {"authenticated": False, "error": "No credentials provided"}

    def _authenticate_api_key(self, key: str) -> dict:
        """Authenticate using API key."""
        key_data = self.api_keys.validate(key)
        if not key_data["valid"]:
            return {"authenticated": False, "error": "Invalid API key"}

        return {
            "authenticated": True,
            "method": "api_key",
            "service": key_data["service_name"],
            "scopes": key_data["scopes"],
            "rate_limit": key_data["rate_limit"],
        }

    def _authenticate_jwt(self, token: str) -> dict:
        """Authenticate using JWT."""
        result = self.jwt.verify(token)
        if not result["valid"]:
            return {"authenticated": False, "error": result["error"]}

        return {
            "authenticated": True,
            "method": "jwt",
            "user_id": result["payload"]["sub"],
            "scopes": result["payload"].get("scopes", []),
        }

    def _authenticate_hmac(self, body: bytes,
                          signature: str,
                          headers: dict) -> dict:
        """Authenticate using HMAC signature."""
        secret = self._get_webhook_secret(
            headers.get("X-GitHub-Event")
        )
        if not secret:
            return {"authenticated": False, "error": "No webhook secret"}

        expected = "sha256=" + hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return {"authenticated": False, "error": "Invalid signature"}

        return {
            "authenticated": True,
            "method": "hmac",
            "source": "webhook",
        }

    def _get_webhook_secret(self, event_type: str) -> str:
        """Get webhook secret for event type."""
        import os
        return os.environ.get(f"WEBHOOK_SECRET_{event_type}", "")
```

### 2.16.2 Autenticação para APIs Internas

```python
class InternalAPIService:
    """Authentication for internal microservice APIs."""

    def __init__(self, service_registry, mtls_config):
        self.services = service_registry
        self.mtls = mtls_config

    def authenticate_service(self, request) -> dict:
        """Authenticate service-to-service communication."""
        # Verify mTLS client certificate
        client_cert = request.environ.get("SSL_CLIENT_CERT")
        if not client_cert:
            return {
                "authenticated": False,
                "error": "No client certificate"
            }

        service_identity = self._extract_service_identity(client_cert)
        if not service_identity:
            return {
                "authenticated": False,
                "error": "Invalid client certificate"
            }

        # Verify service is registered
        service = self.services.get(service_identity["name"])
        if not service:
            return {
                "authenticated": False,
                "error": "Unknown service"
            }

        # Verify certificate matches registered certificate
        if service["cert_fingerprint"] != service_identity["fingerprint"]:
            return {
                "authenticated": False,
                "error": "Certificate mismatch"
            }

        return {
            "authenticated": True,
            "method": "mtls",
            "service": service_identity["name"],
            "scopes": service.get("scopes", []),
        }

    def _extract_service_identity(self, cert_pem: str) -> dict:
        """Extract service identity from client certificate."""
        # Simplified: in production use cryptography library
        return {
            "name": "payment-service",
            "fingerprint": hashlib.sha256(cert_pem.encode()).hexdigest(),
        }
```

---

## 2.17 Gestão de Identidade em Escala

### 2.17.1 Provisionamento e Desprovisionamento

```python
class IdentityLifecycleManager:
    """Manage user identity lifecycle at scale."""

    def __init__(self, user_store, notification_service,
                 audit_log):
        self.users = user_store
        self.notifications = notification_service
        self.audit = audit_log

    def onboarding(self, user_data: dict) -> dict:
        """Process new user onboarding."""
        # Create user account
        user = self.users.create({
            "email": user_data["email"],
            "name": user_data["name"],
            "department": user_data.get("department"),
            "role": user_data.get("role", "viewer"),
            "status": "pending_activation",
            "created_at": time.time(),
        })

        # Send activation email
        self.notifications.send_activation_email(
            user["email"],
            activation_token=secrets.token_urlsafe(32),
        )

        # Assign default roles
        self._assign_default_roles(user["id"], user_data)

        # Audit
        self.audit.log("user_onboarded", {
            "user_id": user["id"],
            "department": user_data.get("department"),
        })

        return {"user_id": user["id"], "status": "pending_activation"}

    def offboarding(self, user_id: str, reason: str,
                   admin_id: str) -> dict:
        """Process user offboarding."""
        user = self.users.get(user_id)
        if not user:
            return {"success": False, "error": "User not found"}

        # Step 1: Disable account immediately
        self.users.update(user_id, {"status": "disabled"})

        # Step 2: Invalidate all sessions
        self.users.delete_all_sessions(user_id)

        # Step 3: Revoke all tokens
        self.users.revoke_all_tokens(user_id)

        # Step 4: Remove all roles
        self.users.clear_roles(user_id)

        # Step 5: Archive user data
        self.users.archive(user_id)

        # Step 6: Notify relevant parties
        self.notifications.send_offboarding_notification(
            user["email"],
            admin_id=admin_id,
            reason=reason,
        )

        # Step 7: Audit
        self.audit.log("user_offboarded", {
            "user_id": user_id,
            "admin_id": admin_id,
            "reason": reason,
        })

        return {"success": True, "status": "disabled"}

    def _assign_default_roles(self, user_id: str,
                             user_data: dict):
        """Assign default roles based on department."""
        role_map = {
            "engineering": ["developer", "viewer"],
            "security": ["analyst", "developer", "viewer"],
            "support": ["support_agent", "viewer"],
            "admin": ["admin", "viewer"],
        }
        department = user_data.get("department", "")
        roles = role_map.get(department, ["viewer"])

        for role in roles:
            self.users.assign_role(user_id, role)
```

---

## 2.18 Referências Adicionais

1. FIDO Alliance - Passkeys: https://fidoalliance.org/passkeys/
2. W3C WebAuthn Level 3 - https://www.w3.org/TR/webauthn-3/
3. NIST SP 800-63C - Federated Identity
4. OAuth 2.0 Security Best Current Practice (RFC 9700)
5. OpenID Connect Core 1.0
6. SAML 2.0 Specification
7. OWASP Mobile Security Verification Standard
8. Apple App Store Review Guidelines - Authentication
9. Google Play Protect - Security Requirements
10. CSA Cloud Controls Matrix

---

## 2.19 Glossário

| Termo | Definicao |
|-------|-----------|
| MFA | Multi-Factor Authentication - Autenticacao multi-fator |
| TOTP | Time-based One-Time Password - Senha de uso unico baseada no tempo |
| HOTP | HMAC-based One-Time Password - Senha de uso unico baseada em HMAC |
| FIDO2 | Fast Identity Online - Padrao de autenticacao sem senha |
| WebAuthn | Web Authentication API - API padrao para FIDO2 na web |
| Passkey | Credencial FIDO2 pareada com dispositivo |
| YubiKey | Token de hardware para autenticacao |
| mTLS | Mutual TLS - TLS bidirecional com certificados |
| SSO | Single Sign-On - Autenticacao unificada |
| SAML | Security Assertion Markup Language - Protocolo de federacao |
| OIDC | OpenID Connect - Camada de autenticacao sobre OAuth 2.0 |
| ABAC | Attribute-Based Access Control - Controle baseado em atributos |
| RBAC | Role-Based Access Control - Controle baseado em papeis |
| Risk-Based Auth | Autenticacao baseada em analise de risco |
| Adaptive Auth | Autenticacao adaptativa baseada em comportamento |
| Session | Sessao autenticada entre cliente e servidor |
| JWT | JSON Web Token - Token autocontido |
| API Key | Chave de API para autenticacao de servicos |
| HIBP | Have I Been Pwned - Servico de verificacao de vazamentos |

---

## 2.20 Autenticação em Ambientes Corporativos

### 2.20.1 Active Directory e LDAP

Em ambientes corporativos, a autenticação frequentemente depende de diretórios centralizados como Active Directory (AD) ou LDAP.

```python
class CorporateAuthService:
    """Authentication against Active Directory/LDAP."""

    def __init__(self, ldap_server, base_dn):
        self.server = ldap_server
        self.base_dn = base_dn

    def authenticate(self, username: str,
                    password: str) -> dict:
        """Authenticate user against LDAP."""
        import ldap

        # Bind with user credentials
        user_dn = f"CN={username},{self.base_dn}"
        try:
            conn = ldap.initialize(self.server)
            conn.simple_bind_s(user_dn, password)

            # Get user attributes
            attrs = conn.search_s(
                self.base_dn,
                ldap.SCOPE_SUBTREE,
                f"(sAMAccountName={username})",
                ["memberOf", "mail", "displayName"]
            )

            conn.unbind_s()

            if attrs:
                groups = self._extract_groups(attrs[0][1].get("memberOf", []))
                return {
                    "authenticated": True,
                    "user": {
                        "username": username,
                        "email": attrs[0][1].get("mail", [""])[0],
                        "display_name": attrs[0][1].get("displayName", [""])[0],
                        "groups": groups,
                    },
                }

            return {"authenticated": True, "user": {"username": username}}

        except ldap.INVALID_CREDENTIALS:
            return {"authenticated": False, "error": "Invalid credentials"}
        except ldap.LDAPError as e:
            return {"authenticated": False, "error": str(e)}

    def _extract_groups(self, member_of: list) -> list:
        """Extract group names from LDAP memberOf attribute."""
        groups = []
        for dn in member_of:
            # CN=Group Name,OU=Users,DC=example,DC=com
            match = dn.split(",")[0].replace("CN=", "")
            groups.append(match)
        return groups
```

### 2.20.2 Integração com Identity Providers

```python
class IdentityProviderIntegration:
    """Integrate with external identity providers."""

    PROVIDERS = {
        "google": {
            "auth_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        },
        "microsoft": {
            "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        },
        "github": {
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
        },
    }

    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_auth_url(self, provider: str,
                    state: str) -> str:
        """Generate authorization URL."""
        config = self.PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"Unknown provider: {provider}")

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": "openid email profile",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{config['auth_url']}?{query}"

    def exchange_code(self, provider: str,
                     code: str) -> dict:
        """Exchange authorization code for tokens."""
        import requests

        config = self.PROVIDERS.get(provider)
        if not config:
            return {"error": "Unknown provider"}

        response = requests.post(
            config["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            return {"error": "Token exchange failed"}

        tokens = response.json()

        # Get user info
        user_response = requests.get(
            config["userinfo_url"],
            headers={
                "Authorization": f"Bearer {tokens['access_token']}"
            },
        )

        if user_response.status_code == 200:
            user_info = user_response.json()
            return {
                "access_token": tokens["access_token"],
                "user": user_info,
            }

        return {"error": "Failed to get user info"}
```

---

## 2.21 Resumo Executivo de Métodos de Autenticação

### 2.21.1 Matriz de Decisão

| Cenario | Metodo Recomendado | Alternativa | Evitar |
|---------|-------------------|-------------|--------|
| App mobile para consumidores | Passkeys + Biometria | TOTP + Push | SMS OTP como unico MFA |
| API publica | API Key + OAuth 2.0 | JWT + HMAC | Basic Auth sem TLS |
| Sistema bancario | mTLS + YubiKey | TOTP + Biometria | Senha como unico fator |
| Sistema governamental | TOTP + Senha forte | WebAuthn | Captcha como MFA |
| Startup SaaS | Passkeys | TOTP + Email magic link | SMS OTP como padrao |
| IoT device | Certificado X.509 | API Key + HMAC | Senha hardcoded |
| Microservicos internos | mTLS + JWT | Service mesh | API Key sem rotacao |

### 2.21.2 Fator de Decisão

Ao escolher um método de autenticação, considere:

1. **Nível de segurança necessário**: Dados financeiros exigem MFA forte; leitura pública não exige autenticação
2. **Experiência do usuário**: Consumidores preferem biometria; desenvolvedores aceitam YubiKey
3. **Custo de implementação**: Passkeys são grátis; YubiKey custa USD 45+
4. **Conformidade regulatória**: PCI DSS exige MFA; LGPD recomenda criptografia
5. **Base de usuários**: Usuários idosos podem ter dificuldade com TOTP
6. **Disponibilidade de rede**: Apps offline precisam de autenticação offline
7. **Ameaças específicas**: Phishing é ameaça? State-sponsored attacks?

---

*[Próximo capítulo: 03 — Segurança de Senhas](03-seguranca-senhas.md)*
