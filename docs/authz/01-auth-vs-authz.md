---
layout: default
title: "01-auth-vs-authz"
---

# Capítulo 1 — Autenticacao vs Autorizacao

> *"Autenticacao e a porta de entrada; autorizacao e a cerca que define ate onde voce pode ir dentro de casa."*

---

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. **Distinguir com precisão** autenticação de autorização, entendendo por que confundi-las é uma das causas raiz de falhas de segurança em sistemas reais.
2. **Desenhar fluxos completos de autenticação e autorização** usando diagramas de sequência que documentam cada passo, desde o pedido HTTP até a concessão de acesso.
3. **Implementar gerenciamento de sessões seguro** incluindo criação, validação, renovação e invalidação de sessões com proteção contra ataques comuns.
4. **Analisar mecanismos de autenticação HTTP** (Basic, Bearer, API Keys) e compreender suas vantagens, limitações e riscos em cada cenário de uso.
5. **Aplicar o ciclo de vida completo da identidade** desde o registro até o descarte, garantindo que cada etapa respeite princípios de segurança.
6. **Diagnosticar falhas reais** usando o caso Misantropi4 como referência concreta de como falhas em autenticação e autorização se combinam para produzir ataques devastadores.

---

## 1.1 Definições Fundamentais

### 1.1.1 Autenticação: Quem é Você?

Autenticação é o processo de **verificar a identidade** de uma entidade — seja ela um humano, um dispositivo, um serviço ou uma aplicação. Quando você insere sua senha e o sistema confirma que você é quem diz ser, está ocorrendo autenticação.

A autenticação responde a uma pergunta simples e absoluta: **"Quem está pedindo?"** Não importa o que o solicitante queira fazer; importa apenas se ele é, de fato, quem afirma ser.

Na prática, a autenticação opera sobre fatores que podem ser agrupados em categorias fundamentais:

| Fator | Descrição | Exemplos Concretos | Fraqueza Conhecida |
|-------|-----------|-------------------|-------------------|
| Algo que voce sabe | Conhecimento secreto compartilhado | Senhas, PINs, respostas a perguntas secretas | Reuso, adivinhação, phishing |
| Algo que voce possui | Objeto físico ou digital | Token hardware, smartphone, smart card, YubiKey | Roubo, clonagem, perda |
| Algo que voce e | Característica biometrica inerente | Impressao digital, iris, reconhecimento facial, voz | Spoofing, irreversibilidade em caso de comprometimento |

Um sistema que usa apenas um desses fatores é chamado de **autenticação de fator único (SFA)**. Quando combina dois ou mais, temos **autenticação multi-fator (MFA)** ou **autenticação de dois fatores (2FA)**.

A distinção é crítica: MFA não significa "dois métodos do mesmo fator." Usar senha + pergunta secreta é apenas autenticação de fator único porque ambos são "algo que você sabe." Senha + TOTP no celular é MFA porque combina "algo que você sabe" com "algo que você possui."

### 1.1.2 Autorização: O Que Você Pode Fazer?

Autorização é o processo de **determinar o que uma entidade autenticada tem permissão para fazer**. Ela não se preocupa com identidade — assume que a identidade já foi verificada — e sim com **escopo de acesso**.

Quando um usuário autenticado tenta acessar um recurso, a autorização responde: **"Esse usuário tem permissão para realizar essa ação nesse recurso?"**

Autorização opera sobre modelos conceituais que definem regras de acesso:

| Modelo | Descrição | Complexidade | Caso de Uso |
|--------|-----------|-------------|-------------|
| DAC (Discretionary) | O proprietário do recurso define quem acessa | Baixa | Sistemas de arquivos |
| MAC (Mandatory) | Políticas centralizadas, inegociáveis | Alta | Militar, governamental |
| RBAC (Role-Based) | Acesso baseado em papéis atribuídos | Média | Aplicações empresariais |
| ABAC (Attribute-Based) | Acesso baseado em atributos do sujeito, recurso e ambiente | Alta | Sistemas complexos |
| ReBAC (Relationship-Based) | Acesso baseado em relações entre entidades | Média-Alta | Redes sociais, grafos |

### 1.1.3 A Diferença Crucial

A confusão entre autenticação e autorização é uma das fontes mais comuns de vulnerabilidades em sistemas de software. Para entender por que, considere esta analogia:

**Autenticação** é como mostrar seu documento de identidade na reception de um prédio. O segurança verifica se o documento é válido e se a foto corresponde a você. Ele confirma quem você é.

**Autorização** é como o crachá de acesso que o segurança entrega após verificar sua identidade. Esse crachá define quais andares você pode acessar, quais salas pode entrar, e quais equipamentos pode usar.

O erro mais comum é assumir que, se alguém passou pela recepção (autenticou-se), ele pode ir a qualquer lugar do prédio (está autorizado a tudo). Isso seria como entregar um crachá de acesso total a todo funcionário apenas porque ele tem um documento válido.

Em termos técnicos:

| Aspecto | Autenticacao | Autorizacao |
|---------|-------------|-------------|
| Pergunta-chave | Quem e voce? | O que voce pode fazer? |
| Quando ocorre | Sempre ANTES da autorizacao | Sempre DEPOIS da autenticacao |
| Saidas | Identidade verificada (ou rejeitada) | Permissao concedida (ou negada) |
| Modelos | Fatores de autenticacao, MFA | RBAC, ABAC, ReBAC, DAC, MAC |
| Dados de entrada | Credenciais do usuario | Identidade + Recurso + Acao |
| Armazenamento | Credenciais, hashes, segredos MFA | Políticas, papéis, permissões |
| Falha resultante | Acesso não autorizado total | Escalada de privilegios |

---

## 1.2 O Ciclo de Vida da Identidade

A identidade de um usuário não é estática — ela nasce, evolui, pode ser comprometida e eventualmente é descartada. Compreender esse ciclo é essencial para projetar sistemas seguros.

### 1.2.1 Registro e Provisionamento

O ciclo começa quando um novo usuário se registra no sistema. Esta é a primeira oportunidade — e frequentemente a última — de estabelecer controles de segurança adequados.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA DA IDENTIDADE                       │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Registro │───▶│ Verific. │───▶│ Ativacao │───▶│   Uso    │       │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘       │
│                                                       │              │
│                                              ┌────────┼────────┐    │
│                                              │        │        │    │
│                                        ┌─────▼──┐ ┌──▼────┐ ┌─▼──┐ │
│                                        │Reauten.│ │Troca  │ │MFA │ │
│                                        │  MFA   │ │Senha  │ │Step │ │
│                                        └─────┬──┘ └──┬────┘ └─┬──┘ │
│                                              │        │        │    │
│                                              └────────┼────────┘    │
│                                                       │              │
│                                              ┌────────▼────────┐    │
│                                              │  Suspensão /    │    │
│                                              │  Bloqueio       │    │
│                                              └────────┬────────┘    │
│                                                       │              │
│                                              ┌────────▼────────┐    │
│                                              │   Descarte /    │    │
│                                              │   Anonimização  │    │
│                                              └─────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

**Durante o registro, o sistema deve:**

1. **Validar a identidade** — O e-mail é real? O telefone pertence ao usuário? Isso parece óbvio, mas sistemas como o IDAP não validavam endereços de e-mail antes de permitir o acesso.
2. **Forçar uma senha forte** — Aplicar políticas de senha que sigam as diretrizes do NIST SP 800-63B (discutidas no Capítulo 3).
3. **Exigir verificação em etapas** — O registro deve ser um processo multi-etapa, não um único formulário.
4. **Logar o evento** — Data, hora, IP, dispositivo e método de registro devem ser registrados para auditoria.
5. **Notificar o usuário** — Enviar confirmação do registro para o canal verificado (e-mail, SMS).

```python
# Exemplo de registro seguro com verificacao de identidade
import hashlib
import secrets
import datetime

class SecureRegistration:
    def __init__(self, db, email_verifier, sms_verifier):
        self.db = db
        self.email_verifier = email_verifier
        self.sms_verifier = sms_verifier

    def initiate_registration(self, email, phone, password):
        """Step 1: Create pending account with verification tokens."""
        validation_errors = self._validate_registration_data(
            email, phone, password
        )
        if validation_errors:
            return {"status": "error", "errors": validation_errors}

        email_token = secrets.token_urlsafe(32)
        phone_token = secrets.token_urlsafe(6)

        self.db.save_pending_registration({
            "email": email,
            "phone": phone,
            "password_hash": self._hash_password(password),
            "email_token": self._hash_token(email_token),
            "phone_token": phone_token,
            "created_at": datetime.datetime.utcnow(),
            "expires_at": datetime.datetime.utcnow()
                        + datetime.timedelta(hours=24),
            "verified": False,
            "email_verified": False,
            "phone_verified": False,
        })

        self.email_verifier.send_verification(email, email_token)
        self.sms_verifier.send_verification(phone, phone_token)

        return {
            "status": "pending",
            "message": "Verifique seu e-mail e telefone para continuar"
        }

    def verify_email(self, email, token):
        """Step 2a: Verify email address."""
        pending = self.db.get_pending_registration(email)
        if not pending:
            return {"status": "error", "message": "Registro nao encontrado"}

        if pending["expires_at"] < datetime.datetime.utcnow():
            self.db.delete_pending_registration(email)
            return {"status": "error", "message": "Token expirado"}

        if self._hash_token(token) == pending["email_token"]:
            self.db.update_pending_registration(email, {
                "email_verified": True
            })
            return {"status": "ok", "message": "E-mail verificado"}

        return {"status": "error", "message": "Token invalido"}

    def verify_phone(self, phone, token):
        """Step 2b: Verify phone number."""
        pending = self.db.get_pending_by_phone(phone)
        if not pending:
            return {"status": "error", "message": "Registro nao encontrado"}

        if pending["phone_token"] == token:
            all_verified = pending["email_verified"]  # Assume email done
            if all_verified:
                return self._activate_account(pending)
            else:
                self.db.update_pending_registration(pending["email"], {
                    "phone_verified": True
                })
                return {"status": "pending",
                        "message": "Telefone verificado, aguardando e-mail"}
        return {"status": "error", "message": "Codigo invalido"}

    def _activate_account(self, pending):
        """Step 3: Activate the account after all verifications."""
        self.db.create_user({
            "email": pending["email"],
            "phone": pending["phone"],
            "password_hash": pending["password_hash"],
            "created_at": datetime.datetime.utcnow(),
            "status": "active",
            "mfa_enabled": False,
            "login_attempts": 0,
            "locked_until": None,
        })
        self.db.delete_pending_registration(pending["email"])
        return {"status": "ok", "message": "Conta ativada com sucesso"}

    def _validate_registration_data(self, email, phone, password):
        errors = []
        if not email or "@" not in email:
            errors.append("E-mail invalido")
        if not phone or len(phone) < 10:
            errors.append("Telefone invalido")
        if len(password) < 12:
            errors.append("Senha deve ter no minimo 12 caracteres")
        return errors

    def _hash_password(self, password):
        salt = secrets.token_bytes(32)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, 600000
        )
        return salt.hex() + ":" + dk.hex()

    def _hash_token(self, token):
        return hashlib.sha256(token.encode()).hexdigest()
```

### 1.2.2 Autenticação no Dia a Dia

Após o registro, o usuário entra repetidamente no sistema. Cada interação de login é uma oportunidade para o sistema verificar se a identidade continua válida.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    FLUXO DE AUTENTICACAO DIARIO                            │
│                                                                            │
│  Usuario                Sistema                   Servidor de             │
│    │                      │                       Identidade              │
│    │  POST /login         │                          │                     │
│    │  {email, password}   │                          │                     │
│    │─────────────────────▶│                          │                     │
│    │                      │  Verificar credenciais   │                     │
│    │                      │─────────────────────────▶│                     │
│    │                      │                          │                     │
│    │                      │  Credenciais validas     │                     │
│    │                      │◀─────────────────────────│                     │
│    │                      │                          │                     │
│    │                      │  Verificar MFA           │                     │
│    │  302 /mfa            │  (se habilitado)         │                     │
│    │◀─────────────────────│                          │                     │
│    │                      │                          │                     │
│    │  POST /mfa           │                          │                     │
│    │  {code: "123456"}    │                          │                     │
│    │─────────────────────▶│                          │                     │
│    │                      │  Validar TOTP            │                     │
│    │                      │─────────────────────────▶│                     │
│    │                      │                          │                     │
│    │                      │  MFA validado            │                     │
│    │                      │◀─────────────────────────│                     │
│    │                      │                          │                     │
│    │                      │  Criar sessao segura     │                     │
│    │  Set-Cookie: SID=... │                          │                     │
│    │  302 /dashboard      │                          │                     │
│    │◀─────────────────────│                          │                     │
│    │                      │                          │                     │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.2.3 Renovação e Manutenção

Sessões não devem durar para sempre. Mesmo que um usuário esteja autenticado, o sistema deve periodicamente:

1. **Renovar tokens** antes que expirem, usando refresh tokens
2. **Re-verificar sensibilidade** — operações críticas podem exigir re-autenticação
3. **Atualizar o contexto** — mudanças de IP ou dispositivo podem indicar comprometimento
4. **Expirar sessões ociosas** — sessões sem atividade devem ser encerradas

```python
class SessionLifecycle:
    def __init__(self, session_store, audit_log):
        self.session_store = session_store
        self.audit_log = audit_log
        self.IDLE_TIMEOUT = 900       # 15 minutes
        self.ABSOLUTE_TIMEOUT = 3600  # 1 hour
        self.SENSITIVE_TIMEOUT = 300  # 5 minutes for sensitive ops

    def validate_session(self, session_id, request_context):
        """Validate session with contextual risk assessment."""
        session = self.session_store.get(session_id)
        if not session:
            return None

        now = datetime.datetime.utcnow()
        elapsed = (now - session["last_activity"]).total_seconds()
        total = (now - session["created_at"]).total_seconds()

        # Absolute timeout: session expires regardless of activity
        if total > self.ABSOLUTE_TIMEOUT:
            self._invalidate(session_id, "absolute_timeout")
            return None

        # Idle timeout: no activity for too long
        if elapsed > self.IDLE_TIMEOUT:
            self._invalidate(session_id, "idle_timeout")
            return None

        # Risk-based: detect anomalies
        risk_score = self._assess_risk(session, request_context)
        if risk_score > 0.7:
            self.audit_log.log("high_risk_session", {
                "session_id": session_id,
                "risk_score": risk_score,
                "context": request_context,
            })
            return self._require_reauth(session_id)

        # Update last activity
        session["last_activity"] = now
        self.session_store.update(session_id, session)
        return session

    def _assess_risk(self, session, context):
        """Calculate risk score based on contextual changes."""
        risk = 0.0

        # IP address changed
        if session.get("ip_address") != context.get("ip_address"):
            risk += 0.4

        # User agent changed (different browser/device)
        if session.get("user_agent") != context.get("user_agent"):
            risk += 0.3

        # Impossible travel: too fast between distant locations
        if self._detect_impossible_travel(session, context):
            risk += 0.5

        # Accessing sensitive resource
        if context.get("resource_sensitivity") == "high":
            risk += 0.2

        return min(risk, 1.0)

    def _detect_impossible_travel(self, session, context):
        """Detect if user appears to be in two far-apart locations."""
        # Simplified: check if IP geolocation suggests impossible travel
        prev_ip = session.get("ip_address")
        curr_ip = context.get("ip_address")
        prev_loc = self._geolocate(prev_ip)
        curr_loc = self._geolocate(curr_ip)
        elapsed = (datetime.datetime.utcnow()
                   - session["last_activity"]).total_seconds()

        if prev_loc and curr_loc and elapsed > 0:
            distance_km = self._haversine(prev_loc, curr_loc)
            speed_kmh = (distance_km / elapsed) * 3600
            # Commercial flights max ~900 km/h
            if speed_kmh > 1000:
                return True
        return False

    def _invalidate(self, session_id, reason):
        """Securely invalidate a session."""
        self.session_store.delete(session_id)
        self.audit_log.log("session_invalidated", {
            "session_id": session_id,
            "reason": reason,
        })

    def _require_reauth(self, session_id):
        """Mark session as requiring re-authentication."""
        return {"status": "reauth_required", "session_id": session_id}

    def _geolocate(self, ip_address):
        """Lookup geolocation for IP address."""
        # Implementation depends on geolocation service
        return None

    def _haversine(self, loc1, loc2):
        """Calculate distance between two geographic points."""
        import math
        R = 6371  # Earth's radius in km
        dlat = math.radians(loc2["lat"] - loc1["lat"])
        dlon = math.radians(loc2["lon"] - loc1["lon"])
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(loc1["lat"])) *
             math.cos(math.radians(loc2["lat"])) *
             math.sin(dlon/2)**2)
        return R * 2 * math.asin(math.sqrt(a))
```

### 1.2.4 Suspensão e Bloqueio

Quando o sistema detecta comportamento suspeito ou quando um administrador intervém, a identidade pode ser suspensa ou bloqueada:

- **Suspensão temporária**: Conta bloqueada por tempo determinado (após N tentativas falhas de login)
- **Suspensão por investigação**: Conta bloqueada até revisão manual
- **Bloqueio permanente**: Conta encerrada por violação de termos ou comprometimento confirmado

```python
class AccountLockoutManager:
    def __init__(self, db, notification_service):
        self.db = db
        self.notification_service = notification_service
        self.MAX_FAILED_ATTEMPTS = 5
        self.LOCKOUT_DURATION = datetime.timedelta(minutes=30)
        self.PROGRESSIVE_DELAYS = [
            0,           # 1st failure: no delay
            5,           # 2nd failure: 5 seconds
            30,          # 3rd failure: 30 seconds
            300,         # 4th failure: 5 minutes
            1800,        # 5th failure: 30 minutes (lockout)
        ]

    def record_failed_attempt(self, email, ip_address):
        """Record a failed login attempt with progressive delay."""
        user = self.db.get_user_by_email(email)
        if not user:
            # Still record to prevent user enumeration timing attacks
            self._record_generic_failure(ip_address)
            return {"status": "rejected", "delay": 0}

        failed_count = user.get("failed_attempts", 0) + 1
        self.db.update_user(email, {"failed_attempts": failed_count})

        self.notification_service.log_security_event("failed_login", {
            "email": email,
            "ip": ip_address,
            "attempt_number": failed_count,
        })

        if failed_count >= self.MAX_FAILED_ATTEMPTS:
            lockout_until = (
                datetime.datetime.utcnow() + self.LOCKOUT_DURATION
            )
            self.db.update_user(email, {
                "locked_until": lockout_until,
                "failed_attempts": 0,
            })
            self.notification_service.send_lockout_notification(email)
            return {
                "status": "locked",
                "lockout_until": lockout_until.isoformat()
            }

        delay_index = min(failed_count - 1,
                         len(self.PROGRESSIVE_DELAYS) - 1)
        delay = self.PROGRESSIVE_DELAYS[delay_index]
        return {"status": "rejected", "delay": delay}

    def check_lockout(self, email):
        """Check if account is currently locked."""
        user = self.db.get_user_by_email(email)
        if not user:
            return False

        locked_until = user.get("locked_until")
        if locked_until and locked_until > datetime.datetime.utcnow():
            return True

        # Auto-unlock if lockout period has passed
        if locked_until:
            self.db.update_user(email, {
                "locked_until": None,
                "failed_attempts": 0,
            })
        return False

    def _record_generic_failure(self, ip_address):
        """Record failure for non-existent email (timing attack prevention)."""
        # Use constant-time operations to prevent timing attacks
        import time
        time.sleep(0.05)  # Consistent delay regardless of user existence
        self.notification_service.log_security_event(
            "failed_login_generic", {"ip": ip_address}
        )
```

### 1.2.5 Descarte e Anonimização

O ciclo termina quando a identidade não é mais necessária. Isso pode ocorrer por:

- **Exclusão voluntária**: Usuário solicita remoção (obrigatório sob LGPD/ GDPR)
- **Exclusão por inatividade**: Contas não utilizadas por longo período
- **Exclusão por violação**: Usuário que violou termos de uso
- **Exclusão por compliance**: Retenção de dados expirou

```python
class IdentityDisposition:
    """Handle identity lifecycle end: deletion, anonymization, archival."""

    RETENTION_PERIODS = {
        "financial_records": 365 * 5,    # 5 years
        "audit_logs": 365 * 7,           # 7 years
        "user_data": 365 * 2,           # 2 years
        "session_data": 30,              # 30 days
        "mfa_secrets": 0,               # Delete immediately
    }

    def __init__(self, db, audit_log, backup_service):
        self.db = db
        self.audit_log = audit_log
        self.backup_service = backup_service

    def process_account_deletion(self, user_id, reason="user_request"):
        """Process account deletion with data protection."""
        user = self.db.get_user(user_id)
        if not user:
            return {"status": "not_found"}

        self.audit_log.log("account_deletion_initiated", {
            "user_id": user_id,
            "reason": reason,
        })

        # Step 1: Invalidate all sessions immediately
        self.db.delete_all_sessions(user_id)

        # Step 2: Revoke all active tokens
        self.db.revoke_all_tokens(user_id)

        # Step 3: Delete MFA secrets (highest sensitivity)
        self.db.delete_mfa_secrets(user_id)

        # Step 4: Anonymize PII but retain statistical data
        anonymized = self._anonymize_user_data(user)
        self.db.save_anonymized_record(anonymized)

        # Step 5: Delete original records
        self.db.delete_user_records(user_id)

        # Step 6: Log completion (this log entry is retained)
        self.audit_log.log("account_deletion_completed", {
            "user_id": user_id,
            "anonymized_id": anonymized["id"],
        })

        return {"status": "deleted", "anonymized_id": anonymized["id"]}

    def _anonymize_user_data(self, user):
        """Anonymize PII while preserving data for analytics."""
        import hashlib
        import secrets

        salt = secrets.token_hex(16)
        anon_id = hashlib.sha256(
            f"{user['id']}:{salt}".encode()
        ).hexdigest()[:16]

        return {
            "id": anon_id,
            "created_year": user["created_at"].year,
            "country": user.get("country_code", "unknown"),
            "account_age_days": (
                datetime.datetime.utcnow() - user["created_at"]
            ).days,
            "mfa_was_enabled": user.get("mfa_enabled", False),
            "total_logins": user.get("total_logins", 0),
        }

    def cleanup_expired_data(self):
        """Remove data that has exceeded retention period."""
        now = datetime.datetime.utcnow()

        for data_type, retention_days in self.RETENTION_PERIODS.items():
            cutoff = now - datetime.timedelta(days=retention_days)
            expired = self.db.get_expired_data(data_type, cutoff)
            for record in expired:
                self.db.delete_record(data_type, record["id"])
                self.audit_log.log("data_expired_deletion", {
                    "data_type": data_type,
                    "record_id": record["id"],
                })
```

---

## 1.3 Fluxos de Autenticação: Diagramas de Sequência

### 1.3.1 Fluxo Básico: Usuário e Senha

O fluxo mais elementar de autenticação envolve apenas credenciais. Embora seja o ponto de partida, raramente é suficiente para sistemas modernos.

```
┌──────────┐       ┌──────────────┐       ┌────────────┐       ┌──────────┐
│ Browser  │       │   Servidor   │       │   Banco    │       │  Log de  │
│          │       │   Web        │       │   Dados    │       │ Auditoria│
└────┬─────┘       └──────┬───────┘       └─────┬──────┘       └────┬─────┘
     │                    │                     │                    │
     │  GET /login        │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │                     │                    │
     │  200 OK (form)     │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
     │  POST /login       │                     │                    │
     │  email=...         │                     │                    │
     │  password=...      │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │                     │                    │
     │                    │  Buscar usuario     │                    │
     │                    │────────────────────▶│                    │
     │                    │                     │                    │
     │                    │  Retornar hash      │                    │
     │                    │◀────────────────────│                    │
     │                    │                     │                    │
     │                    │  Verificar senha    │                    │
     │                    │  (Argon2id)         │                    │
     │                    │                     │                    │
     │                    │  Registrar tentativa                   │
     │                    │────────────────────────────────────────▶│
     │                    │                     │                    │
     │                    │  Gerar sessao       │                    │
     │                    │  (token aleatorio)  │                    │
     │                    │                     │                    │
     │  Set-Cookie:       │                     │                    │
     │  SID=abc123...;    │                     │                    │
     │  HttpOnly;Secure;  │                     │                    │
     │  SameSite=Strict   │                     │                    │
     │                    │                     │                    │
     │  302 /dashboard    │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
```

### 1.3.2 Fluxo com MFA (TOTP)

```
┌──────────┐       ┌──────────────┐       ┌────────────┐
│ Browser  │       │   Servidor   │       │   Banco    │
└────┬─────┘       └──────┬───────┘       └─────┬──────┘
     │                    │                     │
     │  POST /login       │                     │
     │  {email, password} │                     │
     │───────────────────▶│                     │
     │                    │  Verificar credenc.  │
     │                    │────────────────────▶│
     │                    │◀────────────────────│
     │                    │                     │
     │                    │  [Credenciais OK]   │
     │                    │  Verificar se MFA    │
     │                    │  esta habilitado     │
     │                    │────────────────────▶│
     │                    │◀────────────────────│
     │                    │                     │
     │                    │  Criar sessao        │
     │                    │  parcial (pre-MFA)   │
     │                    │                     │
     │  302 /mfa          │                     │
     │◀───────────────────│                     │
     │                    │                     │
     │  GET /mfa          │                     │
     │───────────────────▶│                     │
     │  200 (MFA form)    │                     │
     │◀───────────────────│                     │
     │                    │                     │
     │  POST /mfa         │                     │
     │  {totp_code}       │                     │
     │───────────────────▶│                     │
     │                    │  Validar TOTP        │
     │                    │  (janela ±30s)       │
     │                    │                     │
     │                    │  Atualizar sessao    │
     │                    │  -> completa         │
     │                    │────────────────────▶│
     │                    │◀────────────────────│
     │                    │                     │
     │  302 /dashboard    │                     │
     │◀───────────────────│                     │
     │                    │                     │
```

### 1.3.3 Fluxo de Autorização (RBAC)

```
┌──────────┐       ┌──────────────┐       ┌────────────┐       ┌──────────┐
│ Requisi- │       │   Servidor   │       │  Servico   │       │  Motor   │
│ ciente   │       │   Web        │       │  de AuthZ  │       │  de      │
│          │       │              │       │            │       │  Regras  │
└────┬─────┘       └──────┬───────┘       └─────┬──────┘       └────┬─────┘
     │                    │                     │                    │
     │  GET /api/users    │                     │                    │
     │  Cookie: SID=...   │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │                     │                    │
     │                    │  Extrair user_id     │                    │
     │                    │  da sessao           │                    │
     │                    │                     │                    │
     │                    │  Verificar permissao │                    │
     │                    │  "user:list"         │                    │
     │                    │────────────────────▶│                    │
     │                    │                     │                    │
     │                    │                     │  Consultar          │
     │                    │                     │  papel do usuario   │
     │                    │                     │───────────────────▶│
     │                    │                     │                    │
     │                    │                     │  Avaliar regra:     │
     │                    │                     │  role="admin"       │
     │                    │                     │  perm="user:list"   │
     │                    │                     │  -> ALLOW           │
     │                    │                     │◀───────────────────│
     │                    │                     │                    │
     │                    │  Autorizado          │                    │
     │                    │◀────────────────────│                    │
     │                    │                     │                    │
     │                    │  Buscar usuarios    │                    │
     │                    │────────────────────▶│                    │
     │                    │◀────────────────────│                    │
     │                    │                     │                    │
     │  200 OK (list)     │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
```

### 1.3.4 Fluxo de Token-Based Auth (OAuth 2.0)

```
┌──────────┐       ┌──────────────┐       ┌────────────┐       ┌──────────┐
│ Cliente  │       │   Servidor   │       │  Identity  │       │  Servico │
│ (App)    │       │   Recurso    │       │  Provider  │       │  OAuth   │
└────┬─────┘       └──────┬───────┘       └─────┬──────┘       └────┬─────┘
     │                    │                     │                    │
     │  GET /api/data     │                     │                    │
     │  (sem token)       │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │                     │                    │
     │  401 Unauthorized  │                     │                    │
     │  WWW-Authenticate: │                     │                    │
     │  Bearer            │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
     │  POST /oauth/token │                     │                    │
     │  grant_type=       │                     │                    │
     │  authorization_code│                     │                    │
     │  code=abc123...    │                     │                    │
     │  redirect_uri=...  │                     │                    │
     │  client_id=...     │                     │                    │
     │  client_secret=... │                     │                    │
     │──────────────────────────────────────────▶│                    │
     │                    │                     │                    │
     │                    │                     │  Validar code       │
     │                    │                     │  Verificar          │
     │                    │                     │  client_secret      │
     │                    │                     │                    │
     │                    │                     │  Gerar tokens       │
     │                    │                     │  (access + refresh) │
     │                    │                     │                    │
     │  {                 │                     │                    │
     │    "access_token": │                     │                    │
     │    "eyJhbGci...",  │                     │                    │
     │    "token_type":   │                     │                    │
     │    "Bearer",       │                     │                    │
     │    "expires_in":   │                     │                    │
     │    3600,           │                     │                    │
     │    "refresh_token":│                     │                    │
     │    "dGhpcyBpc..."  │                     │                    │
     │  }                 │                     │                    │
     │◀──────────────────────────────────────────│                    │
     │                    │                     │                    │
     │  GET /api/data     │                     │                    │
     │  Authorization:    │                     │                    │
     │  Bearer eyJhbGci..│                     │                    │
     │───────────────────▶│                     │                    │
     │                    │  Validar JWT         │                    │
     │                    │  Verificar assinatura│                    │
     │                    │  Verificar expiracao │                    │
     │                    │  Extrair scopes      │                    │
     │                    │                     │                    │
     │  200 OK (dados)    │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
```

---

## 1.4 Gerenciamento de Sessões

### 1.4.1 O que é uma Sessão?

Uma sessão é um **estado temporário** mantido entre o cliente e o servidor que permite ao sistema "lembrar" que o usuário está autenticado. Sem sessões, o usuário teria que fornecer suas credenciais em cada requisição — uma prática insegura e impraticável.

Uma sessão típica contém:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| ID da sessao | Token unico e aleatorio | `a1b2c3d4e5f6...` (256 bits) |
| ID do usuario | Identificador do usuario autenticado | `usr_123456` |
| Endereco IP | IP do cliente na criacao da sessao | `203.0.113.42` |
| User-Agent | Navegador/dispositivo do cliente | `Mozilla/5.0...` |
| Data de criacao | Quando a sessao foi iniciada | `2026-06-15T10:30:00Z` |
| Ultimo acesso | Ultima atividade registrada | `2026-06-15T11:45:00Z` |
| Expiracao | Quando a sessao invalida | `2026-06-15T12:30:00Z` |
| Status MFA | Se MFA foi verificado | `true` / `false` |
| Nivel de confianca | Score de risco da sessao | `0.2` (0.0 a 1.0) |

### 1.4.2 Geração Segura de Token de Sessão

O token de sessão deve ser gerado usando um CSPRNG (Cryptographically Secure Pseudo-Random Number Generator) com no mínimo 128 bits de entropia. Tokens previsíveis ou de baixa entropia permitem ataques de adivinhação (session prediction).

```python
import secrets
import hashlib
import os

class SecureSessionTokenGenerator:
    """Generate cryptographically secure session tokens."""

    TOKEN_BYTES = 32  # 256 bits of entropy

    @staticmethod
    def generate():
        """Generate a new secure session token."""
        raw_token = secrets.token_bytes(SecureSessionTokenGenerator.TOKEN_BYTES)
        return raw_token.hex()

    @staticmethod
    def generate_url_safe():
        """Generate URL-safe token for use in query parameters."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token):
        """Hash token for storage (never store raw tokens)."""
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def validate_token_format(token):
        """Validate token format without checking database."""
        if not token:
            return False
        # Hex tokens should be even length
        if len(token) != SecureSessionTokenGenerator.TOKEN_BYTES * 2:
            return False
        # Must contain only hex characters
        try:
            int(token, 16)
            return True
        except ValueError:
            return False
```

### 1.4.3 Armazenamento de Sessões

Sessões podem ser armazenadas de várias maneiras, cada uma com tradeoffs de segurança:

| Metodo | Descrição | Vantagens | Riscos |
|--------|-----------|-----------|--------|
| Server-side (memory) | Sessoes em RAM do servidor | Rapido, controle total | Perda em restart, nao escala horizontalmente |
| Server-side (database) | Sessoes em banco relacional | Persistente, auditavel | Latencia, overhead de I/O |
| Server-side (Redis) | Sessoes em Redis/Memcached | Rapido, distribuido | Requer infraestrutura extra |
| Cookie-based (stateless) | Dados da sessao no cookie | Stateless, escala horizontalmente | Dados visiveis (encriptados), tamanho limitado |
| JWT-based | Sessao como JWT assinado | Stateless, interoperavel | Nao pode ser revogado facilmente, tamanho |

```python
class SessionStore:
    """Server-side session store with Redis backend."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.PREFIX = "session:"
        self.DEFAULT_TTL = 3600  # 1 hour

    def create(self, user_id, context, ttl=None):
        """Create a new session and store it."""
        token = SecureSessionTokenGenerator.generate()
        token_hash = SecureSessionTokenGenerator.hash_token(token)

        session_data = {
            "user_id": user_id,
            "token_hash": token_hash,
            "ip_address": context.get("ip_address"),
            "user_agent": context.get("user_agent"),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "last_activity": datetime.datetime.utcnow().isoformat(),
            "mfa_verified": context.get("mfa_verified", False),
            "risk_score": 0.0,
        }

        effective_ttl = ttl or self.DEFAULT_TTL
        self.redis.setex(
            self.PREFIX + token_hash,
            effective_ttl,
            json.dumps(session_data)
        )

        return token  # Return raw token to client, store hash

    def get(self, token):
        """Retrieve session by token."""
        token_hash = SecureSessionTokenGenerator.hash_token(token)
        raw = self.redis.get(self.PREFIX + token_hash)
        if raw:
            return json.loads(raw)
        return None

    def update(self, token, updates):
        """Update session data."""
        token_hash = SecureSessionTokenGenerator.hash_token(token)
        current = self.get(token)
        if not current:
            return False
        current.update(updates)
        current["last_activity"] = datetime.datetime.utcnow().isoformat()
        ttl = self.redis.ttl(self.PREFIX + token_hash)
        self.redis.setex(
            self.PREFIX + token_hash,
            ttl,
            json.dumps(current)
        )
        return True

    def delete(self, token):
        """Delete a session."""
        token_hash = SecureSessionTokenGenerator.hash_token(token)
        self.redis.delete(self.PREFIX + token_hash)

    def delete_all_for_user(self, user_id):
        """Delete all sessions for a user (e.g., after password change)."""
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(
                cursor, match=self.PREFIX + "*", count=100
            )
            for key in keys:
                raw = self.redis.get(key)
                if raw:
                    data = json.loads(raw)
                    if data.get("user_id") == user_id:
                        self.redis.delete(key)
            if cursor == 0:
                break

    def cleanup_expired(self):
        """Redis handles TTL-based expiration automatically."""
        # Additional cleanup for edge cases if needed
        pass
```

### 1.4.4 Proteção Contra Ataques em Sessões

| Ataque | Descrição | Contra-Medida |
|--------|-----------|---------------|
| Session Fixation | Atacante define ID de sessao antes do login | Regenerar token apos login |
| Session Hijacking | Roubo de token via XSS ou sniffing | HttpOnly, Secure, SameSite cookies |
| Session Prediction | Adivinhar token de sessao | CSPRNG com 256+ bits de entropia |
| Session Replay | Reutilizar token capturado | Tokens de uso unico para operacoes criticas |
| CSRF | Forcar acoes autenticadas via requests falsos | CSRF tokens, SameSite cookies |

```python
class SessionSecurityMiddleware:
    """Middleware to enforce session security best practices."""

    def __init__(self, session_store):
        self.session_store = session_store

    def on_login(self, old_session_id, user_id, context):
        """Regenerate session on login to prevent fixation."""
        # Delete old session
        if old_session_id:
            self.session_store.delete(old_session_id)

        # Create new session with fresh token
        new_token = self.session_store.create(
            user_id=user_id,
            context=context,
            ttl=3600
        )

        # Log the session creation
        self._log_event("session_created", {
            "user_id": user_id,
            "ip": context.get("ip_address"),
            "ua": context.get("user_agent"),
        })

        return new_token

    def on_password_change(self, user_id):
        """Invalidate all sessions on password change."""
        self.session_store.delete_all_for_user(user_id)
        self._log_event("all_sessions_invalidated", {
            "user_id": user_id,
            "reason": "password_change",
        })

    def validate_request(self, token, request_context):
        """Validate session for incoming request."""
        session = self.session_store.get(token)
        if not session:
            return {"valid": False, "reason": "session_not_found"}

        # Check session binding
        if session.get("ip_address") != request_context.get("ip_address"):
            self._log_event("session_ip_mismatch", {
                "user_id": session["user_id"],
                "expected_ip": session["ip_address"],
                "actual_ip": request_context.get("ip_address"),
            })
            return {"valid": False, "reason": "ip_binding_violation"}

        if session.get("user_agent") != request_context.get("user_agent"):
            self._log_event("session_ua_mismatch", {
                "user_id": session["user_id"],
            })
            return {"valid": False, "reason": "ua_binding_violation"}

        return {"valid": True, "session": session}

    def set_cookie_attributes(self):
        """Return secure cookie attributes."""
        return {
            "httponly": True,
            "secure": True,
            "samesite": "Strict",
            "path": "/",
            "max_age": 3600,
        }

    def _log_event(self, event_type, data):
        """Log security event for audit trail."""
        print(f"[SESSION] {event_type}: {json.dumps(data)}")
```

---

## 1.5 Autenticação Baseada em Tokens

### 1.5.1 Visão Geral de Tokens

Tokens são o mecanismo predominante de autenticação em sistemas modernos. Eles substituem o modelo de sessão tradicional (baseado em cookies) por tokens autocontidos que viajam com cada requisição.

Existem dois tipos principais:

| Tipo | Descrição | Persistencia | Revogacao |
|------|-----------|-------------|-----------|
| Access Token | Credencial de curta vida para acessar recursos | Stateless (JWT) ou stateful | Dificil (stateless) ou facil (stateful) |
| Refresh Token | Credencial de longa vida para obter novos access tokens | Stateful (armazenado no servidor) | Facil (deletar do servidor) |

### 1.5.2 JWT: Estrutura e Uso

JSON Web Token (RFC 7519) é o formato mais usado para access tokens. Consiste em três partes:

```
eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS5leGFtcGxlLmNvbSIs
InN1YiI6InVzZXJfMTIzNDU2Iiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzE4NTIxNjAw
LCJpYXQiOjE3MTg0OTI4MDAsInNjb3BlIjoiZm9vIGJhciJ9.signature_here
```

| Parte | Conteudo | Formato |
|-------|----------|---------|
| Header | Algoritmo de assinatura, tipo do token | JSON Base64URL |
| Payload | Claims (dados do usuario, permissoes, expiracao) | JSON Base64URL |
| Signature | Assinatura criptografica | RSA, ECDSA, ou HMAC |

**Claims importantes:**

| Claim | Nome | Descricao |
|-------|------|-----------|
| iss | Issuer | Quem emitiu o token |
| sub | Subject | Identidade do usuario |
| aud | Audience | Servico destinatario |
| exp | Expiration Time | Quando o token expira |
| nbf | Not Before | Quando o token comeca a valer |
| iat | Issued At | Quando o token foi emitido |
| jti | JWT ID | Identificador unico do token |
| scopes | Scopes | Permissoes concedidas |

```python
import jwt
import datetime
import secrets
from typing import Dict, Optional

class JWTTokenService:
    """Secure JWT token management."""

    def __init__(self, signing_key: str, algorithm: str = "RS256"):
        self.signing_key = signing_key
        self.algorithm = algorithm
        self.ACCESS_TOKEN_TTL = 900      # 15 minutes
        self.REFRESH_TOKEN_TTL = 604800  # 7 days

    def create_access_token(
        self,
        user_id: str,
        scopes: list,
        additional_claims: Optional[Dict] = None
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.datetime.utcnow()

        payload = {
            "iss": "devsecurity-api",
            "sub": user_id,
            "iat": now,
            "exp": now + datetime.timedelta(seconds=self.ACCESS_TOKEN_TTL),
            "jti": secrets.token_urlsafe(16),
            "scopes": scopes,
            "token_type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.signing_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a long-lived refresh token."""
        now = datetime.datetime.utcnow()

        payload = {
            "iss": "devsecurity-api",
            "sub": user_id,
            "iat": now,
            "exp": now + datetime.timedelta(seconds=self.REFRESH_TOKEN_TTL),
            "jti": secrets.token_urlsafe(16),
            "token_type": "refresh",
        }

        return jwt.encode(payload, self.signing_key, algorithm=self.algorithm)

    def validate_token(
        self, token: str, expected_type: str = "access"
    ) -> Dict:
        """Validate a JWT token with full security checks."""
        try:
            payload = jwt.decode(
                token,
                self.signing_key,
                algorithms=[self.algorithm],
                options={
                    "require": ["exp", "iss", "sub", "jti", "iat"],
                }
            )
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "token_expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"invalid_token: {str(e)}"}

        # Verify token type
        if payload.get("token_type") != expected_type:
            return {"valid": False, "error": "wrong_token_type"}

        # Verify issuer
        if payload.get("iss") != "devsecurity-api":
            return {"valid": False, "error": "invalid_issuer"}

        # Check if token is revoked (requires token store lookup)
        if self._is_token_revoked(payload["jti"]):
            return {"valid": False, "error": "token_revoked"}

        return {"valid": True, "payload": payload}

    def rotate_refresh_token(
        self, old_refresh_token: str
    ) -> Dict:
        """Rotate refresh token: issue new pair, revoke old refresh."""
        # Validate old refresh token
        validation = self.validate_token(
            old_refresh_token, expected_type="refresh"
        )
        if not validation["valid"]:
            return {"error": validation["error"]}

        user_id = validation["payload"]["sub"]

        # Revoke old refresh token
        self._revoke_token(validation["payload"]["jti"])

        # Issue new pair
        new_access = self.create_access_token(user_id, ["read", "write"])
        new_refresh = self.create_refresh_token(user_id)

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "Bearer",
            "expires_in": self.ACCESS_TOKEN_TTL,
        }

    def _is_token_revoked(self, jti: str) -> bool:
        """Check if token has been revoked."""
        # Implementation depends on storage backend
        return False

    def _revoke_token(self, jti: str):
        """Revoke a token by its JTI."""
        # Implementation depends on storage backend
        pass
```

### 1.5.3 Segurança de Tokens

| Vulnerabilidade | Descricao | Prevencoes |
|----------------|-----------|-----------|
| Algoritmo 'none' | Atacante muda header para "none" e remove assinatura | Validar algoritmo explicitamente, nunca confiar no header |
| Confusao de chave | Usar chave publica onde era esperada chave privada | Validar tipo de chave por algoritmo |
| Token sem expiracao | Access token que nunca expira | Definir TTL curto (15 min), usar refresh tokens |
| Armazenamento inseguro | Token em localStorage (vulneravel a XSS) | Usar cookies HttpOnly ou memory |
| Token na URL | Token em query string (visivel em logs) | Usar header Authorization |
| Revogacao ausente | Impossivel invalidar token comprometido | Usar jti + token revocation list |

```python
class TokenSecurityValidator:
    """Additional security checks for JWT tokens."""

    ALLOWED_ALGORITHMS = ["RS256", "ES256"]
    MIN_KEY_SIZE = 2048  # RSA minimum
    MAX_TOKEN_SIZE = 8192  # Prevent DoS via huge tokens

    @classmethod
    def validate_token_security(cls, token: str) -> dict:
        """Perform security-focused token validation."""
        errors = []

        # 1. Token size check (prevent memory exhaustion)
        if len(token.encode()) > cls.MAX_TOKEN_SIZE:
            errors.append("token_too_large")

        # 2. Basic format check
        parts = token.split(".")
        if len(parts) != 3:
            errors.append("invalid_format")
            return {"valid": False, "errors": errors}

        # 3. Check for 'none' algorithm in header
        import base64
        try:
            header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
            header_json = base64.urlsafe_b64decode(header_b64)
            if b'"none"' in header_json or b'"None"' in header_json:
                errors.append("none_algorithm_detected")
        except Exception:
            errors.append("malformed_header")

        # 4. Check for suspicious payload content
        try:
            payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64)
            if len(payload_json) > 4096:
                errors.append("payload_too_large")
        except Exception:
            errors.append("malformed_payload")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
```

---

## 1.6 Mecanismos HTTP de Autenticação

### 1.6.1 HTTP Basic Authentication

Basic Authentication é o mecanismo mais simples de autenticação HTTP. As credenciais são codificadas em Base64 e enviadas no header `Authorization`.

```
GET /api/resource HTTP/1.1
Host: api.example.com
Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

**Decodificação:**
- `dXNlcm5hbWU6cGFzc3dvcmQ=` = `username:password` em Base64

**Características:**

| Aspecto | Detalhes |
|---------|----------|
| Seguranca | Nenhuma (Base64 nao e criptografia) |
| Requer HTTPS | SIM — sempre, sem excecao |
| Suporte a MFA | Nao |
| Revogacao | Via expiracao HTTP (sem mecanismo nativo) |
| Credenciais | Enviadas a CADA requisicao |
| Estado | Stateless |

**Quando usar:**
- Servicos internos com TLS obrigatório
- APIs simples de uso interno
- Debugging temporário

**Quando NÃO usar:**
- Aplicações públicas
- Sistemas sem TLS
- Qualquer cenário que exija MFA

```python
import base64
from functools import wraps

class BasicAuthMiddleware:
    """HTTP Basic Authentication middleware."""

    def __init__(self, user_lookup_func):
        self.user_lookup = user_lookup_func

    def __call__(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response(
                'Basic realm="devsecurity-api"'
            )

        if not auth_header.startswith("Basic "):
            return self._unauthorized_response(
                'Basic realm="devsecurity-api"'
            )

        try:
            encoded = auth_header[6:]
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return self._unauthorized_response(
                'Basic realm="devsecurity-api"'
            )

        user = self.user_lookup(username, password)
        if not user:
            return self._unauthorized_response(
                'Basic realm="devsecurity-api"'
            )

        request.user = user
        return None  # Continue to next handler

    def _unauthorized_response(self, realm):
        from werkzeug import Response
        return Response(
            "Authentication required",
            status=401,
            headers={"WWW-Authenticate": realm}
        )
```

### 1.6.2 Bearer Token Authentication

Bearer Authentication é o mecanismo padrão para OAuth 2.0 e JWT. O token é enviado no header `Authorization` com o prefixo `Bearer`.

```
GET /api/users HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Características:**

| Aspecto | Detalhes |
|---------|----------|
| Seguranca | Depende do transport (HTTPS) e da qualidade do token |
| Requer HTTPS | SIM — obrigatoria |
| Suporte a MFA | Sim (token reflete nivel de autenticacao) |
| Revogacao | Via blacklist de tokens ou expiracao |
| Tamanho | Tokens JWT podem ser grandes (~1KB) |
| Estado | Stateless (JWT) ou Stateful (reference token) |

**Tradeoffs entre JWT e Reference Token:**

| Aspecto | JWT (Stateless) | Reference Token (Stateful) |
|---------|----------------|---------------------------|
| Validacao | Local (verificar assinatura) | Remota (buscar no servidor) |
| Velocidade | Rapido (sem I/O) | Mais lento (I/O por requisicao) |
| Revogacao | Dificil (requer blacklist) | Facil (deletar do armazenamento) |
| Tamanho | Grande (~500 bytes a 1KB) | Pequeno (~32 bytes) |
| Escalabilidade | Excelente (horizontal) | Depende do armazenamento |

### 1.6.3 API Keys

API Keys são tokens de longa vida usados para autenticação de servicos e automatizacoes. Diferente de tokens de usuário, API keys não representam um humano — representam um aplicativo ou integração.

```
GET /api/data HTTP/1.1
Host: api.example.com
X-API-Key: ak_live_a1b2c3d4e5f6g7h8i9j0
```

**Características:**

| Aspecto | Detalhes |
|---------|----------|
| Seguranca | Media — token de longa vida, reutilizavel |
| Uso principal | Autenticacao server-to-server |
| Vida util | Longa (meses ou anos) |
| Escopo | Geralmente limitado ao que o servico precisa |
| Rotacao | Deve ser periodicamente rotacionada |

**Boas práticas para API Keys:**

1. NUNCA expor em código do lado do cliente (frontend)
2. Usar prefixos identificáveis (ex: `sk_live_`, `ak_prod_`)
3. Implementar revogação imediata
4. Associar a scopes específicos (princípio do menor privilégio)
5. Logar uso para auditoria

```python
import secrets
import hashlib
import datetime

class APIKeyManager:
    """Secure API key generation and management."""

    KEY_PREFIXES = {
        "production": "sk_live_",
        "development": "sk_test_",
        "internal": "ak_int_",
    }

    def __init__(self, db):
        self.db = db

    def generate_key(
        self, service_name: str, environment: str,
        scopes: list, rate_limit: int = 1000
    ) -> dict:
        """Generate a new API key with metadata."""
        prefix = self.KEY_PREFIXES.get(environment, "sk_")
        raw_key = secrets.token_urlsafe(32)
        full_key = prefix + raw_key

        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        self.db.save_api_key({
            "key_hash": key_hash,
            "service_name": service_name,
            "environment": environment,
            "scopes": scopes,
            "rate_limit": rate_limit,
            "created_at": datetime.datetime.utcnow(),
            "last_used": None,
            "expires_at": None,  # Or set a maximum lifetime
            "revoked": False,
        })

        return {
            "key": full_key,  # Show ONCE, then only hash is stored
            "service_name": service_name,
            "scopes": scopes,
        }

    def validate_key(self, api_key: str) -> dict:
        """Validate an API key and return its permissions."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        stored = self.db.get_api_key_by_hash(key_hash)

        if not stored:
            return {"valid": False, "error": "invalid_key"}

        if stored.get("revoked"):
            return {"valid": False, "error": "key_revoked"}

        if stored.get("expires_at"):
            if stored["expires_at"] < datetime.datetime.utcnow():
                return {"valid": False, "error": "key_expired"}

        # Update last used timestamp
        self.db.update_api_key(key_hash, {
            "last_used": datetime.datetime.utcnow()
        })

        return {
            "valid": True,
            "service_name": stored["service_name"],
            "scopes": stored["scopes"],
            "rate_limit": stored["rate_limit"],
        }

    def revoke_key(self, api_key: str):
        """Revoke an API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.db.update_api_key(key_hash, {"revoked": True})

    def rotate_key(self, old_key: str) -> dict:
        """Rotate an API key: generate new, revoke old."""
        old_key_data = self.validate_key(old_key)
        if not old_key_data["valid"]:
            return {"error": "invalid_old_key"}

        self.revoke_key(old_key)

        return self.generate_key(
            service_name=old_key_data["service_name"],
            environment="production",
            scopes=old_key_data["scopes"],
        )
```

### 1.6.4 Tabela Comparativa: Protocolos de Autenticação

| Protocolo | Seguranca | Complexidade | MFA | Revogacao | Uso Recomendado |
|-----------|-----------|-------------|-----|-----------|-----------------|
| HTTP Basic | Baixa | Muito Baixa | Nao | Nao nativa | Servicos internos com TLS |
| HTTP Digest | Media | Baixa | Nao | Nao nativa | Legado |
| Bearer Token (JWT) | Alta | Media | Sim | Dificil (blacklist) | APIs publicas |
| Bearer Token (Ref) | Alta | Media-Alta | Sim | Facil | APIs com controle centralizado |
| API Key | Media | Baixa | Nao | Facil | Integracoes server-to-server |
| OAuth 2.0 | Muito Alta | Alta | Sim | Sim | Aplicacoes de terceiros |
| OpenID Connect | Muito Alta | Muito Alta | Sim | Sim | SSO, federacao |
| Mutual TLS | Muito Alta | Alta | N/A (certificado e fator) | Via CRL/OCSP | Comunicacao servico-a-servico |
| HMAC Signature | Alta | Media | N/A | N/A | Webhooks, APIs assinadas |

---

## 1.7 Erros Comuns em Autenticação

### 1.7.1 Os Dez Maiores Erros (OWASP Top 10 - Authentication Failures)

1. **Permitir força bruta** — Sem limitação de tentativas de login
2. **Permitir credenciais padrão** — Senhas default em instalações
3. **Métodos de recuperação de senha fracos** — Perguntas secretas adivinháveis
4. **Credenciais expostas em logs** — Senhas em logs de servidor ou aplicação
5. **Dados de autenticação em texto plano** — Senhas sem hash ou com hash fraco
6. **Missing MFA** — Autenticação de fator único em sistemas críticos
7. **Sessão não expirada** — Sessões que duram indefinidamente
8. **Cookie sem flags de segurança** — Sem HttpOnly, Secure, ou SameSite
9. **Token previsível** — IDs de sessão com baixa entropia
10. **Credenciais reutilizadas** — Usuários usando mesma senha em múltiplos sistemas

### 1.7.2 Anti-Padrões Detalhados

**Anti-Padrão: Senha no URL**

```python
# VULNERAVEL: Senha em query string
# Aparece em logs do servidor, historico do navegador, e headers Referer
# NUNCA faca isso
@app.route("/login")
def login_vulnerable():
    username = request.args.get("username")
    password = request.args.get("password")  # Em texto plano na URL!
    # ...
```

**Padrão Correto: Senha no body**

```python
# SEGURO: Senha no corpo da requisicao POST
@app.route("/login", methods=["POST"])
def login_secure():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")  # No body, nao na URL
    # ...
```

**Anti-Padrão: Mensagem de erro que revela existência do usuário**

```python
# VULNERAVEL: Mensagem diferente para usuario existente vs inexistente
# Permite enumeracao de usuarios
@app.route("/login", methods=["POST"])
def login_vulnerable():
    user = db.find_user(request.json["email"])
    if not user:
        return {"error": "Usuario nao encontrado"}, 404
    if not verify_password(user, request.json["password"]):
        return {"error": "Senha incorreta"}, 401
    # ...
```

**Padrão Correto: Mensagem genérica**

```python
# SEGURO: Mensagem identica para ambos os casos
@app.route("/login", methods=["POST"])
def login_secure():
    data = request.get_json()
    user = db.find_user(data["email"])
    if not user or not verify_password(user, data["password"]):
        # Registrar tentativa para auditoria, mas nao revelar detalhes
        audit_log.record_login_attempt(
            data["email"], success=False, ip=request.remote_addr
        )
        return {"error": "Credenciais invalidas"}, 401
    # ...
```

**Anti-Padrão: Armazenar senha em texto plano**

```python
# VULNERAVEL: Senha em texto plano no banco de dados
def store_password_plaintext(email, password):
    db.execute(
        "UPDATE users SET password = %s WHERE email = %s",
        (password, email)  # NUNCA faca isso!
    )
```

**Padrão Correto: Hash com Argon2id**

```python
# SEGURO: Hash com Argon2id
import argon2

hasher = argon2.PasswordHasher(
    time_cost=3,        # 3 iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,      # 4 threads
    hash_len=32,
    salt_len=16,
)

def store_password_secure(email, password):
    password_hash = hasher.hash(password)
    db.execute(
        "UPDATE users SET password_hash = %s WHERE email = %s",
        (password_hash, email)
    )
```

---

## 1.8 Caso Misantropi4: O Que Deu Errado com Autenticação

### 1.8.1 Resumo do Ataque

Em junho de 2026, o sistema brasileiro IDAP (Interface de Divulgação de Alertas Públicos) foi comprometido por um atacante conhecido como "Misantropi4". O atacante utilizou credenciais vazadas de servidores públicos para acessar o sistema e enviar alertas de emergência falsos para milhares de cidadãos em São Paulo, Rio de Janeiro, Paraná, Mato Grosso do Sul e Distrito Federal durante a Copa do Mundo.

### 1.8.2 Falhas de Autenticação Identificadas

```
┌──────────────────────────────────────────────────────────────────────┐
│              ARVORE DE CAUSAS - CASO MISANTROPI4                     │
│                                                                      │
│  CAUSA RAIZ: Falha de Autenticacao                                   │
│  ├── 1. Credenciais Vazadas                                          │
│  │   ├── Senhas reutilizadas entre sistemas                          │
│  │   ├── Nenhuma rotacao de credenciais em anos                      │
│  │   └── Servidores publicos sem criptografia adequada               │
│  ├── 2. Ausencia de MFA                                              │
│  │   ├── Login apenas com email/senha                                │
│  │   ├── Nenhum segundo fator exigido                                │
│  │   └── MFA nao era opcao, era ausente do sistema                   │
│  ├── 3. Captcha Ineficaz                                             │
│  │   ├── Contas de matematica simples (2+2, 5+5)                     │
│  │   ├── Respostas em intervalo de 0-9                               │
│  │   └── Sem limite de tentativas por IP                             │
│  ├── 4. Sem Bloqueio de Conta                                        │
│  │   ├── Tentativas ilimitadas                                       │
│  │   ├── Sem delay progressivo                                       │
│  │   └── Sem notificacao ao usuario                                  │
│  ├── 5. Privilegios Excessivos                                       │
│  │   ├── Credenciais com acesso a regioes inteiras                   │
│  │   ├── Sem principio do menor privilegio                           │
│  │   └── Sem segmentacao por regiao                                  │
│  └── 6. Sem Auditoria Adequada                                       │
│      ├── Logs insuficientes                                          │
│      ├── Sem alertas de anomalia                                     │
│      └── Sem monitoramento de access patterns                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.8.3 Fluxo do Ataque

```
┌──────────┐       ┌──────────────┐       ┌────────────┐       ┌──────────┐
│ Atacante │       │   IDAP Web   │       │  Banco IDAP│       │ CIDADOS  │
│ (Misant.)│       │   Portal     │       │            │       │ (vítimas)│
└────┬─────┘       └──────┬───────┘       └─────┬──────┘       └────┬─────┘
     │                    │                     │                    │
     │  1. Acessar credenciais vazadas          │                    │
     │  (de outro servidor publico)             │                    │
     │                    │                     │                    │
     │  2. POST /login    │                     │                    │
     │  {email, password} │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │  3. Verificar        │                    │
     │                    │  (APENAS senha)     │                    │
     │                    │────────────────────▶│                    │
     │                    │  4. Senha confere   │                    │
     │                    │◀────────────────────│                    │
     │                    │                     │                    │
     │  5. Captcha: "2+2" │                     │                    │
     │  Resposta: "4"     │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │  6. Captcha validado │                    │
     │                    │  (fraco, trivial)   │                    │
     │                    │                     │                    │
     │  7. 302 /painel    │                     │                    │
     │◀───────────────────│                     │                    │
     │                    │                     │                    │
     │  8. Acessar painel │                     │                    │
     │  de alertas        │                     │                    │
     │───────────────────▶│                     │                    │
     │                    │  9. Sem verificacao  │                    │
     │                    │  de MFA (inexistente)│                    │
     │                    │                     │                    │
     │  10. Criar alerta  │                     │                    │
     │  falso de emergencia                     │                    │
     │───────────────────▶│                     │                    │
     │                    │  11. Sem validacao   │                    │
     │                    │  de permissao por    │                    │
     │                    │  regiao              │                    │
     │                    │────────────────────▶│                    │
     │                    │                     │  12. Alerta         │
     │                    │                     │  enviado a milhares│
     │                    │                     │───────────────────▶│
     │                    │                     │                    │
```

### 1.8.4 O Que Poderia Ter Sido Diferente

Se o IDAP tivesse implementado práticas básicas de autenticação, o ataque teria sido prevenido ou significativamente mitigado:

| Controle Ausente | Efeito no Ataque | Implementacao Minima |
|------------------|-----------------|---------------------|
| MFA obrigatorio | Atacante teria precisado do segundo fator | TOTP com Google Authenticator ou SMS |
| Captcha robusto | Script automatizado teria falhado | reCAPTCHA v3 ou similar |
| Bloqueio de conta | Conta teria sido bloqueada apos N tentativas | Bloqueio apos 5 falhas, delay progressivo |
| Rotacao de senhas | Credenciais vazadas teriam expirado | Forcar troca a cada 90 dias |
| Rate limiting | Ataque automatizado teria sido limitado | 5 tentativas/minuto por IP |
| Logs de auditoria | Atividade anomala teria sido detectada | Log de todos os logins com IP e timestamp |
| Least privilege | Dano teria sido limitado a uma regiao | Contas regionais com escopo restrito |
| Network segmentation | Acesso ao sistema teria sido dificultado | WAF, VPN, zero trust |

### 1.8.5 Lições Aprendidas

1. **Autenticação não é opcional em sistemas governamentais.** O IDAP processava alertas que afetavam milhões de pessoas. A ausência de MFA em um sistema com esse impacto é uma negligência grave.

2. **Credenciais vazadas são o vetor de ataque mais comum.** Estudos mostram que mais de 80% das violações envolvem credenciais. Rotação de senhas e verificação contra databases de vazamentos são barreiras básicas.

3. **Captcha não é substituto para MFA.** Captchas servem para impedir bots, não para autenticar humanos. Um captcha com operações matemáticas de dois dígitos é trivial para qualquer script.

4. **O princípio do menor privilégio deve ser aplicado desde o início.** Uma única credencial com acesso a múltiplas regiões transforma uma violação pontual em um desastre nacional.

5. **Monitoramento e auditoria são a última linha de defesa.** Mesmo com falhas de autenticação, logs adequados e alertas de anomalia poderiam ter detectado o ataque em minutos, não em horas.

---

## 1.9 Resumo e Próximos Passos

Neste capítulo, estabelecemos as fundações teóricas e práticas de autenticação e autorização:

- **Autenticação** responde "quem é você" — é o processo de verificação de identidade
- **Autorização** responde "o que você pode fazer" — é o controle de acesso baseado na identidade
- O **ciclo de vida da identidade** vai do registro ao descarte, passando por uso, renovação e suspensão
- **Fluxos de autenticação** devem ser documentados com diagramas de sequência claros
- **Gerenciamento de sessões** exige tokens seguros, validação contextual e invalidação adequada
- **Mecanismos HTTP** (Basic, Bearer, API Keys) têm tradeoffs específicos para cada cenário
- **Erros comuns** são evitáveis com boas práticas e conscientização
- O **caso Misantropi4** demonstra como falhas básicas de autenticação podem ter consequências devastadoras

No próximo capítulo, exploraremos os **métodos de autenticação** em profundidade — senhas, MFA, biometria, tokens hardware e autenticação baseada em certificados — analisando as vantagens e riscos de cada abordagem.

---

## 1.10 Exercícios

1. **Análise de Vulnerabilidade**: Identifique pelo menos 5 falhas de autenticação em um sistema de login hipotético que usa apenas senha.
2. **Projeto de Fluxo**: Desenhe um diagrama de sequência completo para um fluxo de login com MFA usando TOTP e recuperação de conta.
3. **Comparação de Protocolos**: Compare OAuth 2.0 e OpenID Connect em termos de segurança, complexidade e casos de uso.
4. **Caso Misantropi4**: Escreva um relatório de 500 palavras analisando como cada falha identificada poderia ter sido prevenida com um controle específico.
5. **Implementação**: Implemente um middleware de autenticação que suporte Basic Auth, Bearer Token e API Keys, com rate limiting e logging de auditoria.

---

## 1.11 Padrões de Autenticação e Autorização em Microserviços

### 1.11.1 O Desafio da Identidade em Arquiteturas Distribuídas

Em arquiteturas monolíticas, a autenticação e autorização eram processos centralizados — um único banco de dados, um único servidor de sessão, uma única política. Com microserviços, cada serviço precisa verificar identidade e autorização de forma independente, sem consultar um serviço central a cada requisição.

```
┌──────────────────────────────────────────────────────────────────────┐
│              AUTENTICACAO EM MICROSERVICOS                            │
│                                                                      │
│  MONOLITO:                                                           │
│  ┌─────────────────────────────────────────┐                         │
│  │  App Monolitica                         │                         │
│  │  ├── Auth centralizado                  │                         │
│  │  ├── Sessao em memoria                  │                         │
│  │  ├── Verificacao local                  │                         │
│  │  └── Autorizacao centralizada           │                         │
│  └─────────────────────────────────────────┘                         │
│                                                                      │
│  MICROSERVICOS:                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Servico  │  │ Servico  │  │ Servico  │  │ Servico  │            │
│  │ Auth     │  │ Pedidos  │  │ Pagamento│  │ Notific. │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │              │              │              │                  │
│       │    JWT assinado pelo Auth    │              │                  │
│       │◄────────────────────────────▶│              │                  │
│       │              │              │              │                  │
│       │    JWT propagado entre servicos            │                  │
│       │              │────────────────────────────▶│                  │
│       │              │              │              │                  │
│       └──────────────┴──────────────┴──────────────┘                  │
│                                                                      │
│  CADA SERVIDOR:                                                      │
│  ├── Valida JWT localmente (assinatura + expiracao)                  │
│  ├── Extrai claims (user_id, roles, scopes)                         │
│  ├── Avalia autorizacao localmente                                   │
│  └── NAO consulta Auth Service a cada requisicao                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.11.2 Padrão: API Gateway com JWT Propagation

```python
class MicroserviceAuthMiddleware:
    """Auth middleware for microservices architecture."""

    def __init__(self, jwt_verifier, policy_engine):
        self.jwt_verifier = jwt_verifier
        self.policy_engine = policy_engine

    def process_request(self, request, service_name):
        """Process authentication and authorization for a request."""
        # Step 1: Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._reject("Missing Authorization header")

        token = self._extract_token(auth_header)
        if not token:
            return self._reject("Invalid Authorization format")

        # Step 2: Verify JWT (local verification, no network call)
        verification = self.jwt_verifier.verify(token)
        if not verification["valid"]:
            return self._reject(f"Invalid token: {verification['error']}")

        claims = verification["payload"]

        # Step 3: Check token freshness
        auth_time = claims.get("auth_time", 0)
        max_age = self._get_max_age_for_operation(request.path)
        if time.time() - auth_time > max_age:
            return self._reject("Token too old for this operation")

        # Step 4: Check service-level authorization
        required_scope = self._get_required_scope(
            request.method, request.path
        )
        if required_scope and required_scope not in claims.get("scopes", []):
            return self._reject(
                f"Missing required scope: {required_scope}"
            )

        # Step 5: Check resource-level authorization
        resource_auth = self.policy_engine.evaluate(
            subject=claims["sub"],
            action=request.method,
            resource=request.path,
            context={
                "roles": claims.get("roles", []),
                "scopes": claims.get("scopes", []),
                "ip": request.remote_addr,
            }
        )

        if not resource_auth["allowed"]:
            return self._reject(
                f"Not authorized: {resource_auth['reason']}"
            )

        # Step 6: Attach identity to request context
        request.user = {
            "id": claims["sub"],
            "roles": claims.get("roles", []),
            "scopes": claims.get("scopes", []),
            "auth_time": auth_time,
        }

        return None  # Continue to handler

    def _extract_token(self, auth_header):
        """Extract token from Authorization header."""
        parts = auth_header.split()
        if len(parts) == 2 and parts[0] == "Bearer":
            return parts[1]
        return None

    def _get_max_age_for_operation(self, path):
        """Get maximum token age based on operation sensitivity."""
        if "/admin/" in path:
            return 300     # 5 minutes for admin operations
        elif "/payment/" in path:
            return 900     # 15 minutes for financial operations
        elif "/user/" in path:
            return 3600    # 1 hour for user operations
        else:
            return 86400   # 24 hours for read-only operations

    def _get_required_scope(self, method, path):
        """Determine required scope for operation."""
        scope_map = {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
            "ADMIN": "admin",
        }
        return scope_map.get(method, "read")

    def _reject(self, reason):
        """Generate rejection response."""
        return {
            "allowed": False,
            "status": 401,
            "error": reason,
        }
```

### 1.11.3 Padrão: Service-to-Service Communication

```python
class ServiceToServiceAuth:
    """Handle authentication between microservices."""

    def __init__(self, service_name, private_key, public_keys):
        self.service_name = service_name
        self.private_key = private_key
        self.public_keys = public_keys  # {service_name: public_key}

    def create_service_token(self, target_service: str,
                            scopes: list) -> str:
        """Create JWT for service-to-service communication."""
        payload = {
            "iss": self.service_name,
            "sub": self.service_name,
            "aud": target_service,
            "scopes": scopes,
            "iat": time.time(),
            "exp": time.time() + 300,  # 5 minutes
            "jti": secrets.token_urlsafe(16),
            "token_type": "service",
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def verify_service_token(self, token: str,
                            expected_issuer: str) -> dict:
        """Verify a service-to-service token."""
        try:
            # Get public key for the issuer
            public_key = self.public_keys.get(expected_issuer)
            if not public_key:
                return {"valid": False, "error": "Unknown service"}

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.service_name,
            )

            # Additional validation
            if payload.get("token_type") != "service":
                return {"valid": False, "error": "Not a service token"}

            return {"valid": True, "payload": payload}

        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": str(e)}

    def propagate_identity(self, original_token: str,
                          target_service: str) -> str:
        """Propagate user identity to another service."""
        # Decode original token to extract user identity
        original_claims = jwt.decode(
            original_token,
            options={"verify_signature": False}
        )

        # Create new token for target service
        payload = {
            "iss": self.service_name,
            "sub": original_claims["sub"],
            "aud": target_service,
            "scopes": original_claims.get("scopes", []),
            "roles": original_claims.get("roles", []),
            "iat": time.time(),
            "exp": time.time() + 300,
            "jti": secrets.token_urlsafe(16),
            "token_type": "propagated",
            "original_iss": original_claims.get("iss"),
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")
```

---

## 1.12 Padrões de Autorização Detalhados

### 1.12.1 Implementação RBAC Completa

Role-Based Access Control (RBAC) é o modelo de autorização mais utilizado em aplicações empresariais. Cada usuário é atribuído a um ou mais papéis, e cada papel define um conjunto de permissões.

```python
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
import time

@dataclass
class Permission:
    """Represents a single permission."""
    resource: str      # e.g., "user", "order", "invoice"
    action: str        # e.g., "create", "read", "update", "delete"
    scope: str = "*"   # e.g., "*", "own", "department", "all"

    def __str__(self):
        return f"{self.resource}:{self.action}:{self.scope}"

@dataclass
class Role:
    """Represents a role with assigned permissions."""
    name: str
    description: str
    permissions: List[Permission] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    max_users: Optional[int] = None
    requires_mfa: bool = False

@dataclass
class User:
    """User with assigned roles."""
    id: str
    email: str
    roles: List[str] = field(default_factory=list)
    department: str = ""
    is_active: bool = True

class RBACEngine:
    """Complete RBAC authorization engine."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self.audit_log = []

    def define_role(self, name: str, description: str,
                   permissions: List[Permission],
                   parent_roles: List[str] = None,
                   requires_mfa: bool = False) -> Role:
        """Define a new role with permissions."""
        role = Role(
            name=name,
            description=description,
            permissions=permissions,
            parent_roles=parent_roles or [],
            requires_mfa=requires_mfa,
        )
        self.roles[name] = role
        return role

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user."""
        user = self.users.get(user_id)
        if not user:
            return False

        role = self.roles.get(role_name)
        if not role:
            return False

        # Check max users limit
        if role.max_users:
            current_count = sum(
                1 for u in self.users.values()
                if role_name in u.roles
            )
            if current_count >= role.max_users:
                return False

        if role_name not in user.roles:
            user.roles.append(role_name)
            self._log_event("role_assigned", {
                "user_id": user_id,
                "role": role_name,
            })
        return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """Revoke a role from a user."""
        user = self.users.get(user_id)
        if not user:
            return False

        if role_name in user.roles:
            user.roles.remove(role_name)
            self._log_event("role_revoked", {
                "user_id": user_id,
                "role": role_name,
            })
            return True
        return False

    def check_permission(self, user_id: str, resource: str,
                        action: str, context: dict = None) -> dict:
        """Check if user has permission for an action."""
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return {"allowed": False, "reason": "User inactive or not found"}

        # Collect all permissions from all roles (including parent roles)
        all_permissions = self._get_all_permissions(user)

        # Check each permission
        for perm in all_permissions:
            if (perm.resource == resource or perm.resource == "*"):
                if (perm.action == action or perm.action == "*"):
                    # Check scope
                    if perm.scope == "*":
                        return {"allowed": True, "matched_permission": str(perm)}
                    elif perm.scope == "own" and context:
                        if context.get("owner_id") == user_id:
                            return {"allowed": True, "matched_permission": str(perm)}
                    elif perm.scope == "department" and context:
                        if context.get("department") == user.department:
                            return {"allowed": True, "matched_permission": str(perm)}
                    elif perm.scope == "all":
                        return {"allowed": True, "matched_permission": str(perm)}

        return {
            "allowed": False,
            "reason": f"No permission for {resource}:{action}",
        }

    def _get_all_permissions(self, user: User) -> List[Permission]:
        """Get all permissions including inherited from parent roles."""
        all_permissions = []
        visited = set()

        def collect_permissions(role_name: str):
            if role_name in visited:
                return
            visited.add(role_name)

            role = self.roles.get(role_name)
            if not role:
                return

            all_permissions.extend(role.permissions)

            # Recurse into parent roles
            for parent in role.parent_roles:
                collect_permissions(parent)

        for role_name in user.roles:
            collect_permissions(role_name)

        return all_permissions

    def requires_mfa(self, user_id: str) -> bool:
        """Check if any of user's roles require MFA."""
        user = self.users.get(user_id)
        if not user:
            return False

        for role_name in user.roles:
            role = self.roles.get(role_name)
            if role and role.requires_mfa:
                return True
        return False

    def _log_event(self, event_type: str, data: dict):
        """Log authorization event."""
        self.audit_log.append({
            "timestamp": time.time(),
            "event": event_type,
            "data": data,
        })


# Example setup
def setup_rbac():
    """Set up a typical RBAC configuration."""
    engine = RBACEngine()

    # Define permissions
    user_read = Permission("user", "read", "department")
    user_write = Permission("user", "write", "department")
    user_delete = Permission("user", "delete", "all")
    order_read = Permission("order", "read", "own")
    order_write = Permission("order", "write", "own")
    invoice_read = Permission("invoice", "read", "all")
    admin_all = Permission("*", "*", "all")

    # Define roles
    engine.define_role(
        "viewer", "Read-only access",
        permissions=[user_read, order_read],
    )
    engine.define_role(
        "operator", "Standard operations",
        permissions=[user_read, user_write, order_read, order_write],
        parent_roles=["viewer"],
    )
    engine.define_role(
        "manager", "Management access",
        permissions=[invoice_read],
        parent_roles=["operator"],
        requires_mfa=True,
    )
    engine.define_role(
        "admin", "Full access",
        permissions=[admin_all, user_delete],
        parent_roles=["manager"],
        requires_mfa=True,
    )

    return engine
```

### 1.12.2 Implementação ABAC

Attribute-Based Access Control (ABAC) é mais granular que RBAC, avaliando atributos do sujeito, recurso, ação e ambiente.

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Callable
import time
import re

@dataclass
class ABACPolicy:
    """Single ABAC policy rule."""
    name: str
    description: str
    subject_conditions: Dict[str, Any]   # User attributes
    resource_conditions: Dict[str, Any]  # Resource attributes
    action_conditions: str                # Action pattern
    environment_conditions: Dict[str, Any] = None  # Time, IP, etc.
    effect: str = "permit"  # permit or deny
    priority: int = 0  # Higher = evaluated first

class ABACEngine:
    """Attribute-Based Access Control engine."""

    def __init__(self):
        self.policies: List[ABACPolicy] = []
        self.attribute_providers = {}

    def add_policy(self, policy: ABACPolicy):
        """Add an ABAC policy."""
        self.policies.append(policy)
        self.policies.sort(key=lambda p: p.priority, reverse=True)

    def register_attribute_provider(self, entity_type: str,
                                   provider: Callable):
        """Register a function that provides attributes for an entity."""
        self.attribute_providers[entity_type] = provider

    def evaluate(self, subject_id: str, resource_id: str,
                action: str, environment: dict = None) -> dict:
        """Evaluate access request against all policies."""
        # Gather attributes
        subject_attrs = self._get_attributes("subject", subject_id)
        resource_attrs = self._get_attributes("resource", resource_id)
        env_attrs = environment or {}

        # Evaluate policies in priority order
        for policy in self.policies:
            result = self._evaluate_policy(
                policy, subject_attrs, resource_attrs,
                action, env_attrs
            )
            if result is not None:
                return {
                    "allowed": result == "permit",
                    "policy": policy.name,
                    "reason": policy.description,
                }

        # Default deny
        return {"allowed": False, "reason": "No matching policy"}

    def _evaluate_policy(self, policy: ABACPolicy,
                        subject_attrs: dict, resource_attrs: dict,
                        action: str, env_attrs: dict) -> str:
        """Evaluate a single policy against attributes."""
        # Check subject conditions
        if not self._match_conditions(
            subject_attrs, policy.subject_conditions
        ):
            return None

        # Check resource conditions
        if not self._match_conditions(
            resource_attrs, policy.resource_conditions
        ):
            return None

        # Check action
        if not self._match_action(action, policy.action_conditions):
            return None

        # Check environment conditions
        if policy.environment_conditions:
            if not self._match_conditions(
                env_attrs, policy.environment_conditions
            ):
                return None

        return policy.effect

    def _match_conditions(self, actual: dict,
                         expected: dict) -> bool:
        """Match actual attributes against expected conditions."""
        for key, condition in expected.items():
            value = actual.get(key)
            if value is None:
                return False

            if isinstance(condition, dict):
                if not self._match_complex(value, condition):
                    return False
            elif isinstance(condition, list):
                if value not in condition:
                    return False
            else:
                if value != condition:
                    return False
        return True

    def _match_complex(self, value: Any,
                      condition: dict) -> bool:
        """Match against complex conditions (operators)."""
        if "eq" in condition and value != condition["eq"]:
            return False
        if "neq" in condition and value == condition["neq"]:
            return False
        if "gt" in condition and value <= condition["gt"]:
            return False
        if "gte" in condition and value < condition["gte"]:
            return False
        if "lt" in condition and value >= condition["lt"]:
            return False
        if "lte" in condition and value > condition["lte"]:
            return False
        if "in" in condition and value not in condition["in"]:
            return False
        if "contains" in condition and condition["contains"] not in str(value):
            return False
        if "regex" in condition and not re.match(condition["regex"], str(value)):
            return False
        return True

    def _match_action(self, action: str, pattern: str) -> bool:
        """Match action against pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern == action:
            return True
        # Regex matching
        try:
            return bool(re.match(pattern, action))
        except re.error:
            return False

    def _get_attributes(self, entity_type: str,
                       entity_id: str) -> dict:
        """Get attributes for an entity."""
        provider = self.attribute_providers.get(entity_type)
        if provider:
            return provider(entity_id)
        return {}


# Example ABAC policies
def setup_abac():
    """Set up example ABAC policies."""
    engine = ABACEngine()

    # Policy 1: Users can read their own data
    engine.add_policy(ABACPolicy(
        name="read_own_data",
        description="Users can read their own data",
        subject_conditions={"id": {"eq": {"resource": "owner_id"}}},
        resource_conditions={},
        action_conditions="read",
        effect="permit",
        priority=10,
    ))

    # Policy 2: Managers can read department data
    engine.add_policy(ABACPolicy(
        name="manager_read_department",
        description="Managers can read data in their department",
        subject_conditions={
            "role": "manager",
            "department": {"eq": {"resource": "department"}},
        },
        resource_conditions={},
        action_conditions="read",
        effect="permit",
        priority=20,
    ))

    # Policy 3: Admin access during business hours only
    engine.add_policy(ABACPolicy(
        name="admin_business_hours",
        description="Admin access restricted to business hours",
        subject_conditions={"role": "admin"},
        resource_conditions={},
        action_conditions="*",
        environment_conditions={
            "hour": {"gte": 8, "lte": 20},
            "weekday": {"in": [1, 2, 3, 4, 5]},
        },
        effect="permit",
        priority=30,
    ))

    # Policy 4: Deny all access from TOR
    engine.add_policy(ABACPolicy(
        name="deny_tor",
        description="Deny access from TOR exit nodes",
        subject_conditions={},
        resource_conditions={},
        action_conditions="*",
        environment_conditions={"is_tor": True},
        effect="deny",
        priority=100,  # Highest priority
    ))

    return engine
```

---

## 1.13 Auditoria e Monitoramento de Autenticação

### 1.13.1 Eventos de Auditoria Essenciais

Todo sistema de autenticação deve registrar eventos específicos para detecção de incidentes e conformidade regulatória.

```python
import time
import json
import hashlib
from typing import Optional, Dict, Any
from enum import Enum

class AuditEventType(Enum):
    """Authentication and authorization audit events."""
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGIN_LOCKED = "auth.login.locked"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"
    PASSWORD_RESET_REQUESTED = "auth.password.reset.requested"
    PASSWORD_RESET_COMPLETED = "auth.password.reset.completed"
    MFA_ENABLED = "auth.mfa.enabled"
    MFA_DISABLED = "auth.mfa.disabled"
    MFA_CHALLENGE = "auth.mfa.challenge"
    MFA_SUCCESS = "auth.mfa.success"
    MFA_FAILURE = "auth.mfa.failure"
    SESSION_CREATED = "auth.session.created"
    SESSION_INVALIDATED = "auth.session.invalidated"
    ROLE_ASSIGNED = "authz.role.assigned"
    ROLE_REVOKED = "authz.role.revoked"
    PERMISSION_DENIED = "authz.permission.denied"
    ACCOUNT_LOCKED = "auth.account.locked"
    ACCOUNT_UNLOCKED = "auth.account.unlocked"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    CREDENTIAL_STUFFING = "security.credential_stuffing"
    BRUTE_FORCE = "security.brute_force"

class AuthAuditLogger:
    """Structured audit logging for authentication events."""

    def __init__(self, storage_backend):
        self.storage = storage_backend

    def log_login_success(self, user_id: str, ip: str,
                         user_agent: str, method: str,
                         mfa_used: bool):
        """Log successful login."""
        self._log(AuditEventType.LOGIN_SUCCESS, {
            "user_id": user_id,
            "ip_address": ip,
            "user_agent": user_agent,
            "auth_method": method,
            "mfa_used": mfa_used,
            "risk_score": self._calculate_risk(ip, user_agent),
        })

    def log_login_failure(self, email: str, ip: str,
                         reason: str):
        """Log failed login attempt."""
        self._log(AuditEventType.LOGIN_FAILURE, {
            "email": email,
            "ip_address": ip,
            "failure_reason": reason,
            "timestamp": time.time(),
        })

    def log_suspicious_activity(self, user_id: str,
                               activity_type: str,
                               details: dict):
        """Log suspicious activity."""
        self._log(AuditEventType.SUSPICIOUS_ACTIVITY, {
            "user_id": user_id,
            "activity_type": activity_type,
            "details": details,
            "severity": "high",
        })

    def log_permission_denied(self, user_id: str,
                             resource: str, action: str,
                             ip: str):
        """Log denied access attempt."""
        self._log(AuditEventType.PERMISSION_DENIED, {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "ip_address": ip,
        })

    def _log(self, event_type: AuditEventType,
            data: Dict[str, Any]):
        """Store audit event."""
        event = {
            "event_type": event_type.value,
            "timestamp": time.time(),
            "data": data,
            "event_id": secrets.token_urlsafe(16),
        }

        # Hash for integrity verification
        event["checksum"] = hashlib.sha256(
            json.dumps(event, sort_keys=True).encode()
        ).hexdigest()

        self.storage.store(event)

    def _calculate_risk(self, ip: str, user_agent: str) -> float:
        """Calculate basic risk score."""
        risk = 0.0
        # Check for known bad IPs (simplified)
        # Check for unusual user agent
        return risk

    def query_events(self, event_type: Optional[str] = None,
                    user_id: Optional[str] = None,
                    start_time: Optional[float] = None,
                    end_time: Optional[float] = None,
                    limit: int = 100) -> list:
        """Query audit events with filters."""
        return self.storage.query(
            event_type=event_type,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def generate_report(self, start_time: float,
                       end_time: float) -> dict:
        """Generate security audit report."""
        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        report = {
            "period": {
                "start": start_time,
                "end": end_time,
            },
            "total_events": len(events),
            "login_successes": 0,
            "login_failures": 0,
            "suspicious_activities": 0,
            "permission_denials": 0,
            "unique_users": set(),
            "unique_ips": set(),
        }

        for event in events:
            et = event["event_type"]
            data = event["data"]

            if et == AuditEventType.LOGIN_SUCCESS.value:
                report["login_successes"] += 1
                report["unique_users"].add(data.get("user_id"))
                report["unique_ips"].add(data.get("ip_address"))
            elif et == AuditEventType.LOGIN_FAILURE.value:
                report["login_failures"] += 1
                report["unique_ips"].add(data.get("ip_address"))
            elif et == AuditEventType.SUSPICIOUS_ACTIVITY.value:
                report["suspicious_activities"] += 1
            elif et == AuditEventType.PERMISSION_DENIED.value:
                report["permission_denials"] += 1

        # Convert sets to counts
        report["unique_users"] = len(report["unique_users"])
        report["unique_ips"] = len(report["unique_ips"])

        # Calculate failure rate
        total_logins = (
            report["login_successes"] + report["login_failures"]
        )
        report["failure_rate"] = (
            report["login_failures"] / total_logins
            if total_logins > 0
            else 0
        )

        return report
```

### 1.13.2 Detecção de Anomalias

```python
import statistics
from collections import defaultdict

class AuthenticationAnomalyDetector:
    """Detect anomalous authentication patterns."""

    def __init__(self, audit_logger):
        self.audit = audit_logger
        self.baseline = defaultdict(lambda: {
            "login_hours": [],
            "login_ips": [],
            "login_countries": [],
            "failed_attempts": [],
        })
        self.ANOMALY_THRESHOLD = 2.0  # Standard deviations

    def analyze_login(self, user_id: str, ip: str,
                     timestamp: float, success: bool) -> dict:
        """Analyze a login event for anomalies."""
        anomalies = []

        # Get user baseline
        baseline = self.baseline[user_id]

        # Check 1: Time anomaly
        hour = time.gmtime(timestamp).tm_hour
        if baseline["login_hours"]:
            mean_hour = statistics.mean(baseline["login_hours"])
            stdev_hour = statistics.stdev(baseline["login_hours"]) or 1
            if abs(hour - mean_hour) > self.ANOMALY_THRESHOLD * stdev_hour:
                anomalies.append({
                    "type": "unusual_hour",
                    "severity": "medium",
                    "details": f"Login at hour {hour}, typical: {mean_hour:.0f}",
                })

        # Check 2: IP anomaly
        if baseline["login_ips"] and ip not in baseline["login_ips"]:
            anomalies.append({
                "type": "new_ip",
                "severity": "medium",
                "details": f"New IP address: {ip}",
            })

        # Check 3: Impossible travel
        if baseline["login_ips"]:
            last_ip = baseline["login_ips"][-1]
            # Check if IP changed impossibly fast
            # (simplified check)

        # Check 4: Failed attempt pattern
        if not success:
            baseline["failed_attempts"].append(timestamp)
            # Check for brute force pattern
            recent_failures = [
                t for t in baseline["failed_attempts"]
                if timestamp - t < 300  # Last 5 minutes
            ]
            if len(recent_failures) >= 5:
                anomalies.append({
                    "type": "brute_force_detected",
                    "severity": "high",
                    "details": f"{len(recent_failures)} failures in 5 minutes",
                })

        # Update baseline with successful login
        if success:
            baseline["login_hours"].append(hour)
            baseline["login_ips"].append(ip)
            # Keep only recent data
            if len(baseline["login_hours"]) > 1000:
                baseline["login_hours"] = baseline["login_hours"][-500:]
            if len(baseline["login_ips"]) > 100:
                baseline["login_ips"] = baseline["login_ips"][-50:]

        # Log anomalies
        if anomalies:
            self.audit.log_suspicious_activity(
                user_id,
                "login_anomaly",
                {"anomalies": anomalies, "ip": ip}
            )

        return {
            "anomalies": anomalies,
            "risk_level": self._calculate_risk_level(anomalies),
            "recommended_action": self._recommend_action(anomalies),
        }

    def _calculate_risk_level(self, anomalies: list) -> str:
        """Calculate overall risk level from anomalies."""
        if not anomalies:
            return "low"
        severities = [a["severity"] for a in anomalies]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _recommend_action(self, anomalies: list) -> str:
        """Recommend action based on anomalies."""
        if not anomalies:
            return "none"
        risk_level = self._calculate_risk_level(anomalies)
        if risk_level == "high":
            return "require_mfa_and_notify"
        elif risk_level == "medium":
            return "require_mfa"
        else:
            return "log_and_monitor"
```

---

## 1.14 Conformidade e Regulamentações

### 1.14.1 Requisitos Regulatórios para Autenticação

Diferentes regulamentações impõem requisitos específicos sobre autenticação e autorização:

| Regulamentacao | Jurisdicao | Requisitos de Auth | Multa Maxima |
|----------------|-----------|-------------------|-------------|
| LGPD | Brasil | MFA para dados sensiveis, criptografia | 2% faturamento, max R$ 50M |
| GDPR | UE | MFA recomendado, criptografia obrigatoria | 4% faturamento, max EUR 20M |
| PCI DSS 4.0 | Global | MFA para acesso ao CDE, senhas fortes | Perda de capacidade de processar cartoes |
| HIPAA | EUA | Controles de acesso, criptografia, auditoria | USD 1.5M por categoria |
| SOC 2 | Global | Controles de autenticacao e autorizacao | Perda de certificacao |
| ISO 27001 | Global | Gestao de identidade e acesso | Perda de certificacao |

### 1.14.2 Checklist de Conformidade

```python
class ComplianceChecker:
    """Check authentication setup against compliance requirements."""

    def __init__(self):
        self.checks = {
            "lgpd": self._lgpd_checks,
            "pci_dss": self._pci_dss_checks,
            "hipaa": self._hipaa_checks,
            "soc2": self._soc2_checks,
        }

    def run_compliance_check(self, framework: str,
                            auth_config: dict) -> dict:
        """Run compliance checks for specified framework."""
        checker = self.checks.get(framework)
        if not checker:
            return {"error": f"Unknown framework: {framework}"}

        results = checker(auth_config)
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        total = len(results)

        return {
            "framework": framework,
            "timestamp": time.time(),
            "results": results,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "compliance_score": passed / total if total > 0 else 0,
            },
        }

    def _lgpd_checks(self, config: dict) -> list:
        """LGPD compliance checks for authentication."""
        return [
            {
                "check": "MFA for sensitive data access",
                "status": "pass" if config.get("mfa_enabled") else "fail",
                "requirement": "LGPD Art. 46 - Security measures",
                "recommendation": "Enable MFA for all users accessing personal data",
            },
            {
                "check": "Password hashing",
                "status": "pass" if config.get("password_hashing") in ["argon2id", "bcrypt"] else "fail",
                "requirement": "LGPD Art. 46 - Technical measures",
                "recommendation": "Use Argon2id or bcrypt for password storage",
            },
            {
                "check": "Session timeout",
                "status": "pass" if config.get("session_timeout", 0) <= 3600 else "fail",
                "requirement": "LGPD Art. 46 - Access control",
                "recommendation": "Set session timeout to 1 hour or less",
            },
            {
                "check": "Audit logging",
                "status": "pass" if config.get("audit_logging_enabled") else "fail",
                "requirement": "LGPD Art. 37 - Records of processing",
                "recommendation": "Enable comprehensive audit logging",
            },
            {
                "check": "Account lockout",
                "status": "pass" if config.get("account_lockout_enabled") else "fail",
                "requirement": "LGPD Art. 46 - Security measures",
                "recommendation": "Enable account lockout after failed attempts",
            },
            {
                "check": "Password reset flow",
                "status": "pass" if config.get("secure_password_reset") else "fail",
                "requirement": "LGPD Art. 46 - Security measures",
                "recommendation": "Implement secure password reset with time-limited tokens",
            },
        ]

    def _pci_dss_checks(self, config: dict) -> list:
        """PCI DSS 4.0 compliance checks."""
        return [
            {
                "check": "MFA for CDE access",
                "status": "pass" if config.get("mfa_for_cde") else "fail",
                "requirement": "PCI DSS 8.4.2",
                "recommendation": "MFA required for all access to cardholder data environment",
            },
            {
                "check": "Password minimum 12 characters",
                "status": "pass" if config.get("min_password_length", 0) >= 12 else "fail",
                "requirement": "PCI DSS 8.3.4",
                "recommendation": "Minimum password length of 12 characters",
            },
            {
                "check": "Password complexity",
                "status": "pass" if config.get("password_complexity") else "fail",
                "requirement": "PCI DSS 8.3.2",
                "recommendation": "Require both numeric and alphabetic characters",
            },
            {
                "check": "Account lockout after 10 attempts",
                "status": "pass" if config.get("max_login_attempts", 100) <= 10 else "fail",
                "requirement": "PCI DSS 8.3.4",
                "recommendation": "Lock account after maximum 10 failed attempts",
            },
            {
                "check": "Session timeout 15 minutes",
                "status": "pass" if config.get("session_timeout", 3600) <= 900 else "fail",
                "requirement": "PCI DSS 8.2.8",
                "recommendation": "Session timeout of 15 minutes or less for CDE",
            },
        ]

    def _hipaa_checks(self, config: dict) -> list:
        """HIPAA compliance checks."""
        return [
            {
                "check": "Unique user identification",
                "status": "pass" if config.get("unique_user_ids") else "fail",
                "requirement": "HIPAA 164.312(a)(2)(i)",
                "recommendation": "Assign unique user identification",
            },
            {
                "check": "Automatic logoff",
                "status": "pass" if config.get("session_timeout", 0) <= 1800 else "fail",
                "requirement": "HIPAA 164.312(a)(2)(iii)",
                "recommendation": "Automatic session termination after 30 minutes",
            },
            {
                "check": "Encryption of PHI",
                "status": "pass" if config.get("encryption_at_rest") else "fail",
                "requirement": "HIPAA 164.312(a)(2)(iv)",
                "recommendation": "Encrypt PHI at rest and in transit",
            },
        ]

    def _soc2_checks(self, config: dict) -> list:
        """SOC 2 compliance checks."""
        return [
            {
                "check": "Multi-factor authentication",
                "status": "pass" if config.get("mfa_enabled") else "fail",
                "requirement": "CC6.1 - Logical access security",
                "recommendation": "MFA for all system access",
            },
            {
                "check": "Password management",
                "status": "pass" if config.get("password_policy_enabled") else "fail",
                "requirement": "CC6.1 - Password controls",
                "recommendation": "Enforce password policy (length, complexity, rotation)",
            },
            {
                "check": "Access review",
                "status": "pass" if config.get("access_review_enabled") else "fail",
                "requirement": "CC6.2 - Access authorization",
                "recommendation": "Regular access reviews and deprovisioning",
            },
            {
                "check": "Audit logging",
                "status": "pass" if config.get("audit_logging_enabled") else "fail",
                "requirement": "CC7.2 - Monitoring",
                "recommendation": "Comprehensive audit logging of all access",
            },
        ]
```

---

## 1.15 Exercícios Adicionais

6. **RBAC Implementation**: Implemente um sistema RBAC completo com herança de papéis, verificação de permissões por escopo, e logging de auditoria.
7. **ABAC Policy**: Crie 5 políticas ABAC que cubram diferentes cenários: acesso próprio, acesso departamental, acesso baseado em horário, acesso baseado em localização, e denegação automática.
8. **Audit System**: Implemente um sistema de auditoria que registre todos os eventos de autenticação e gere relatórios de conformidade.
9. **Anomaly Detection**: Implemente um detector de anomalias que identifique logins fora do padrão, brute force, e credential stuffing.
10. **Compliance Report**: Usando o ComplianceChecker, gere um relatório de conformidade LGPD para um sistema de autenticação hipotético.

---

## 1.16 Referências

1. NIST SP 800-63B - Digital Identity Guidelines
2. OWASP ASVS - Application Security Verification Standard
3. RFC 7519 - JSON Web Token (JWT)
4. RFC 6749 - OAuth 2.0 Authorization Framework
5. RFC 6238 - TOTP: Time-Based One-Time Password Algorithm
6. OWASP Top 10 - Broken Authentication
7. CIS Controls v8 - Identity and Access Management
8. ISO 27001:2022 - Information Security Management
9. LGPD (Lei Geral de Protecao de Dados)
10. PCI DSS v4.0 - Payment Card Industry Data Security Standard
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Metodos Autenticacao](02-metodos-autenticacao.md)*
