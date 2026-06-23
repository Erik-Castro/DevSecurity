# Capítulo 14 — Ataques a Identidade

## 14.1 Credential Stuffing

### 14.1.1 Definição e mecânica

Credential stuffing é um ataque automatizado onde o agressor utiliza pares de credenciais (usuário/senha) vazados de um serviço para tentar autenticar em outros serviços. O ataque se baseia na premissa estatística de que aproximadamente 65% das pessoas reutilizam senhas em múltiplos sites (conforme estudo da Google/Fireworks, 2019).

Diferente do brute force — que tenta combinações aleatórias — o credential stuffing usa credenciais reais, já validadas em outro contexto. Isso torna o ataque muito mais eficiente: cada tentativa tem uma probabilidade significativamente maior de sucesso, e os padrões de comportamento (como taxa de erro e tempo de resposta) são difíceis de distinguir de um usuário legítimo.

O caso Misantropi4 é um exemplo paradigmático de credential stuffing em escala governamental. O atacante utilizou credenciais de operadores vazadas em outros sistemas (possivelmente de órgãos municipais ou estaduais) para acessar o IDAP — o sistema de Identificação Digital do cidadão brasileiro. A ausência de MFA e a falta de verificação de origem transformaram essas credenciais reutilizadas em uma chave de acesso a milhões de registros pessoais.

### 14.1.2 O pipeline de um ataque de credential stuffing

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 1. Coleta   │───>│ 2. Refinamento│───>│ 3. Distribuicao│
│  de dumps   │    │  de dados    │    │  de proxies   │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            v
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 6. Monetiza-│<───│ 5. Escala-  │<───│ 4. Testing  │
│  cao        │    │  cao        │    │  (login)     │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Fase 1 — Coleta**: O atacante obtém credenciais de fontes diversas:
- Dumps de bases de dados vazadas (dark web, Telegram, pastebins).
- Phishing em massa (campanhas de email).
- Malware de roubo de credenciais (infostealers como RedLine, Raccoon).
- Engenharia social (ligações telefônicas, mensagens).
- Scraping de credenciais expostas em repositórios públicos (GitHub, GitLab).

**Fase 2 — Refinamento**: As credenciais brutas são filtradas:
- Remoção de duplicatas.
- Verificação de formato (email válido, CPF válido, etc.).
- Enriquecimento com dados adicionais (nome, departamento, cargo).
- Segmentação por dominio/alvo (todas as credenciais @governo.sp.gov.br).

**Fase 3 — Distribuição**: As tentativas são distribuídas através de:
- Redes de proxies residenciais (rotating residential proxies).
- Tor exit nodes.
- VPNs com IPs rotativos.
- Serviços de proxy corporativos comprometidos.
- Infraestrutura cloud (AWS, GCP, Azure) com contas comprometidas.

**Fase 4 — Testing**: O atacante testa cada par de credenciais no alvo:
- Envio automatizado de requisições de login.
- Parse da resposta para determinar sucesso/falha.
- Diferenciação entre "senha incorreta", "conta bloqueada", "conta inexistente".

**Fase 5 — Escalação**: Credenciais bem-sucedidas são exploradas:
- Acesso inicial ao sistema.
- Enumeração de permissões e dados acessíveis.
- Escalação de privilegios (se possível).
- Movimentação lateral (acesso a outros sistemas com as mesmas credenciais).

**Fase 6 — Monetização**: O acesso é convertido em valor:
- Venda de credenciais validadas na dark web.
- Venda dos dados pessoais acessados.
- Uso para fraude financeira.
- Uso para chantagem ou extorsão.
- Uso para espionagem corporativa ou governamental.

### 14.1.3 Ferramentas de credential stuffing

Ferramentas conhecidas (para fins defensivos):

| Ferramenta | Descrição | Características |
|-----------|-----------|-----------------|
| Sentry MBA | Automação de login | Suporte a múltiplos alvos, proxies rotativos |
| OpenBullet | Framework de cracking | Extensível via plugins, suporte a captchas |
| SilverBullet | Fork do OpenBullet | Mais rápido, suporte a mais sites |
| Account Checker | Verificação de contas | Verifica múltiplos sites simultaneamente |
| Custom scripts | Scripts Python/Node | Controle total, baixa detecção |

### 14.1.4 Indicadores de credential stuffing

Detecção baseada em padrões de tráfego:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import math

@dataclass
class LoginAttempt:
    timestamp: datetime
    ip_address: str
    user_agent: str
    username: str
    success: bool
    response_time_ms: float
    geo_country: str
    geo_city: str

class CredentialStuffingDetector:
    def __init__(self):
        self.attempts = []
        self.alerts = []
    
    def analyze(self, attempts: List[LoginAttempt],
                window_minutes: int = 15) -> Dict:
        self.attempts = sorted(attempts, key=lambda a: a.timestamp)
        
        alerts = []
        
        alerts.extend(self._detect_high_failure_rate(window_minutes))
        alerts.extend(self._detect_distributed_attempts(window_minutes))
        alerts.extend(self._detect_uniform_timing())
        alerts.extend(self._detect_geographic_anomalies())
        alerts.extend(self._detect_credential_reuse())
        alerts.extend(self._detect_ua_anomalies())
        
        self.alerts = alerts
        
        return {
            "total_attempts": len(attempts),
            "unique_ips": len(set(a.ip_address for a in attempts)),
            "unique_users": len(set(a.username for a in attempts)),
            "success_rate": sum(1 for a in attempts if a.success) / len(attempts) if attempts else 0,
            "alerts": alerts,
            "risk_score": self._calculate_risk_score(alerts),
        }
    
    def _detect_high_failure_rate(self, window_minutes: int) -> List[Dict]:
        alerts = []
        ip_failures = defaultdict(list)
        
        for attempt in self.attempts:
            if not attempt.success:
                ip_failures[attempt.ip_address].append(attempt)
        
        for ip, failures in ip_failures.items():
            recent = [f for f in failures 
                     if f.timestamp > datetime.utcnow() - timedelta(minutes=window_minutes)]
            
            if len(recent) > 20:
                alerts.append({
                    "type": "high_failure_rate",
                    "severity": "HIGH",
                    "ip": ip,
                    "failures_in_window": len(recent),
                    "window_minutes": window_minutes,
                    "message": f"IP {ip} has {len(recent)} failures in {window_minutes}min",
                })
        
        return alerts
    
    def _detect_distributed_attempts(self, window_minutes: int) -> List[Dict]:
        alerts = []
        user_attempts = defaultdict(list)
        
        for attempt in self.attempts:
            user_attempts[attempt.username].append(attempt)
        
        for user, attempts in user_attempts.items():
            unique_ips = set(a.ip_address for a in attempts)
            
            if len(unique_ips) > 10:
                alerts.append({
                    "type": "distributed_attack",
                    "severity": "CRITICAL",
                    "username": user,
                    "unique_ips": len(unique_ips),
                    "total_attempts": len(attempts),
                    "message": f"User {user} targeted from {len(unique_ips)} IPs",
                })
        
        return alerts
    
    def _detect_uniform_timing(self) -> List[Dict]:
        alerts = []
        user_attempts = defaultdict(list)
        
        for attempt in self.attempts:
            user_attempts[attempt.username].append(attempt)
        
        for user, attempts in user_attempts.items():
            if len(attempts) < 5:
                continue
            
            intervals = []
            for i in range(1, len(attempts)):
                delta = (attempts[i].timestamp - attempts[i-1].timestamp).total_seconds()
                intervals.append(delta)
            
            if not intervals:
                continue
            
            mean_interval = sum(intervals) / len(intervals)
            if mean_interval == 0:
                continue
            
            variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
            cv = math.sqrt(variance) / mean_interval
            
            if cv < 0.1:
                alerts.append({
                    "type": "uniform_timing",
                    "severity": "MEDIUM",
                    "username": user,
                    "cv_coefficient": round(cv, 4),
                    "mean_interval_seconds": round(mean_interval, 2),
                    "message": f"User {user} has unnaturally uniform timing (CV={cv:.4f})",
                })
        
        return alerts
    
    def _detect_geographic_anomalies(self) -> List[Dict]:
        alerts = []
        user_countries = defaultdict(set)
        
        for attempt in self.attempts:
            user_countries[attempt.username].add(attempt.geo_country)
        
        for user, countries in user_countries.items():
            if len(countries) > 3:
                alerts.append({
                    "type": "geographic_anomaly",
                    "severity": "HIGH",
                    "username": user,
                    "countries": list(countries),
                    "message": f"User {user} accessed from {len(countries)} countries",
                })
        
        return alerts
    
    def _detect_credential_reuse(self) -> List[Dict]:
        alerts = []
        success_by_user = defaultdict(list)
        
        for attempt in self.attempts:
            if attempt.success:
                success_by_user[attempt.username].append(attempt)
        
        for user, successes in success_by_user.items():
            unique_ips = set(a.ip_address for a in successes)
            if len(unique_ips) > 3:
                alerts.append({
                    "type": "credential_reuse",
                    "severity": "CRITICAL",
                    "username": user,
                    "unique_ips": len(unique_ips),
                    "message": f"Successful login for {user} from {len(unique_ips)} IPs",
                })
        
        return alerts
    
    def _detect_ua_anomalies(self) -> List[Dict]:
        alerts = []
        user_agents = defaultdict(set)
        
        for attempt in self.attempts:
            user_agents[attempt.username].add(attempt.user_agent)
        
        for user, uas in user_agents.items():
            if len(uas) > 5:
                alerts.append({
                    "type": "user_agent_rotation",
                    "severity": "MEDIUM",
                    "username": user,
                    "unique_uas": len(uas),
                    "message": f"User {user} has {len(uas)} different user agents",
                })
        
        return alerts
    
    def _calculate_risk_score(self, alerts: List[Dict]) -> float:
        severity_weights = {
            "CRITICAL": 1.0,
            "HIGH": 0.7,
            "MEDIUM": 0.4,
            "LOW": 0.2,
        }
        
        if not alerts:
            return 0.0
        
        total_weight = sum(severity_weights.get(a["severity"], 0) for a in alerts)
        max_possible = len(alerts) * 1.0
        
        return min(1.0, total_weight / max_possible)
```

### 14.1.5 Defesas contra credential stuffing

**Defesa 1 — MFA (Multi-Factor Authentication)**

MFA é a defesa mais eficaz contra credential stuffing. Mesmo que o atacante possua usuário e senha válidos, ele não possui o segundo fator.

```python
class MFAEnforcement:
    def __init__(self, mfa_provider):
        self.provider = mfa_provider
    
    def require_mfa_for_login(self, user_id: str, password: str,
                               context: dict) -> dict:
        # 1. Verificar credenciais basicas
        if not self.verify_password(user_id, password):
            return {"allowed": False, "reason": "invalid_password"}
        
        # 2. Verificar se MFA esta configurado
        mfa_setup = self.provider.get_mfa_setup(user_id)
        
        if not mfa_setup.configured:
            # Forcar setup de MFA antes de permitir acesso
            return {
                "allowed": False,
                "reason": "mfa_required",
                "setup_url": f"/mfa/setup/{user_id}",
            }
        
        # 3. Verificar se MFA foi completado nesta sessao
        mfa_verified = context.get("mfa_verified", False)
        
        if not mfa_verified:
            # Enviar codigo MFA
            self.provider.send_mfa_code(user_id, mfa_setup.method)
            return {
                "allowed": False,
                "reason": "mfa_pending",
                "mfa_method": mfa_setup.method,
            }
        
        # 4. Verificar tentativas MFA
        mfa_attempts = self.provider.get_mfa_attempts(user_id)
        if mfa_attempts > 3:
            return {
                "allowed": False,
                "reason": "mfa_locked",
                "lockout_minutes": 15,
            }
        
        return {"allowed": True, "mfa_verified": True}
```

**Defesa 2 — Bot detection e CAPTCHA**

```python
class BotDetection:
    def __init__(self):
        self.score_threshold = 0.7
    
    def analyze_request(self, request_context: dict) -> dict:
        score = 0.0
        signals = []
        
        # Verificar User-Agent
        ua = request_context.get("user_agent", "")
        if self._is_headless_browser(ua):
            score += 0.3
            signals.append("headless_browser")
        
        # Verificar padrao de JavaScript
        js_fingerprint = request_context.get("js_fingerprint")
        if js_fingerprint and self._is_bot_fingerprint(js_fingerprint):
            score += 0.2
            signals.append("bot_fingerprint")
        
        # Verificar padrao de mouse/teclado
        input_patterns = request_context.get("input_patterns")
        if input_patterns and self._is_automated_input(input_patterns):
            score += 0.3
            signals.append("automated_input")
        
        # Verificar tempo de preenchimento
        form_fill_time = request_context.get("form_fill_time_ms", 0)
        if form_fill_time < 500:  # Muito rapido para humano
            score += 0.2
            signals.append("fast_form_fill")
        
        # Verificar TLS fingerprint
        ja3_hash = request_context.get("ja3_hash")
        if ja3_hash and self._is_known_bot_ja3(ja3_hash):
            score += 0.2
            signals.append("bot_ja3")
        
        return {
            "risk_score": min(1.0, score),
            "signals": signals,
            "blocked": score >= self.score_threshold,
        }
    
    def _is_headless_browser(self, ua: str) -> bool:
        bot_indicators = [
            "HeadlessChrome", "PhantomJS", "Selenium",
            "Puppeteer", "playwright", "node-fetch",
        ]
        return any(indicator.lower() in ua.lower() for indicator in bot_indicators)
    
    def _is_bot_fingerprint(self, fingerprint: dict) -> bool:
        return (
            fingerprint.get("webdriver") == True or
            fingerprint.get("languages", []) == [] or
            fingerprint.get("plugins_count", 0) == 0
        )
    
    def _is_automated_input(self, patterns: dict) -> bool:
        return (
            patterns.get("keystroke_variance", 0) < 0.1 or
            patterns.get("mouse_movement_linear", False) or
            patterns.get("human_delay_ms", 1000) < 100
        )
    
    def _is_known_bot_ja3(self, ja3_hash: str) -> bool:
        known_bot_ja3s = [
            "e7d705a3286e19ea42f587b344ee6865",
            "b32309a26951912be7dba376398abc3b",
        ]
        return ja3_hash in known_bot_ja3s
```

**Defesa 3 — Rate limiting adaptativo**

```python
import time
from collections import defaultdict

class AdaptiveRateLimiter:
    def __init__(self):
        self.ip_limits = {}
        self.user_limits = {}
        self.global_limits = {}
    
    def check(self, ip: str, username: str, timestamp: float) -> dict:
        # Rate limit global (todas as tentativas)
        global_count = self._count_in_window(
            self.global_limits, "global", timestamp, window=60
        )
        if global_count > 10000:
            return {"allowed": False, "reason": "global_rate_limit"}
        
        # Rate limit por IP
        ip_count = self._count_in_window(
            self.ip_limits, ip, timestamp, window=900  # 15 min
        )
        if ip_count > 100:
            return {"allowed": False, "reason": "ip_rate_limit"}
        
        # Rate limit por usuario (across IPs)
        user_count = self._count_in_window(
            self.user_limits, username, timestamp, window=900
        )
        if user_count > 20:
            return {"allowed": False, "reason": "user_rate_limit"}
        
        # Se ha muitas falhas recentes, aumentar restricao
        recent_failures = self._count_failures(ip, username, timestamp)
        if recent_failures > 5:
            # Forcar CAPTCHA
            return {"allowed": True, "captcha_required": True}
        
        return {"allowed": True}
    
    def _count_in_window(self, store: dict, key: str,
                         timestamp: float, window: int) -> int:
        if key not in store:
            store[key] = []
        
        store[key] = [t for t in store[key] if t > timestamp - window]
        store[key].append(timestamp)
        return len(store[key])
    
    def _count_failures(self, ip: str, username: str,
                        timestamp: float) -> int:
        # Implementacao simplificada - em producao, usar Redis ou similar
        return 0
```

**Defesa 4 — Password breach detection**

```python
import hashlib
import requests

class PasswordBreachChecker:
    def __init__(self):
        self.hibp_api = "https://api.pwnedpasswords.com/range/"
    
    def check_password(self, password: str) -> dict:
        sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        try:
            response = requests.get(f"{self.hibp_api}{prefix}", timeout=5)
            
            for line in response.text.splitlines():
                hash_suffix, count = line.split(":")
                if hash_suffix == suffix:
                    return {
                        "breached": True,
                        "count": int(count),
                        "severity": self._classify_breach_count(int(count)),
                    }
            
            return {"breached": False, "count": 0}
        
        except requests.RequestException:
            return {"breached": None, "error": "api_unavailable"}
    
    def _classify_breach_count(self, count: int) -> str:
        if count > 1000000:
            return "CRITICAL"
        elif count > 100000:
            return "HIGH"
        elif count > 1000:
            return "MEDIUM"
        else:
            return "LOW"
```

### 14.1.6 Mitigação específica para o caso Misantropi4

O IDAP poderia ter bloqueado o ataque de credential stuffing com:

```python
class IDAPLoginProtection:
    def __init__(self, mfa_provider, rate_limiter, bot_detector):
        self.mfa = mfa_provider
        self.rate_limiter = rate_limiter
        self.bot_detector = bot_detector
    
    def process_login(self, username: str, password: str,
                      context: dict) -> dict:
        # 1. Verificar rate limit
        rate_check = self.rate_limiter.check(
            context["ip"], username, time.time()
        )
        if not rate_check["allowed"]:
            return {"success": False, "reason": "rate_limited"}
        
        # 2. Verificar se e bot
        bot_check = self.bot_detector.analyze_request(context)
        if bot_check["blocked"]:
            return {"success": False, "reason": "bot_detected"}
        
        # 3. Verificar geolocalizacao
        if context.get("country") != "BR":
            self._alert("foreign_login_attempt", username, context)
            return {"success": False, "reason": "geo_restricted"}
        
        # 4. Verificar credenciais
        if not self._verify_credentials(username, password):
            return {"success": False, "reason": "invalid_credentials"}
        
        # 5. OBRIGATORIAMENTE exigir MFA
        mfa_check = self.mfa.require_mfa(username, context)
        if not mfa_check["verified"]:
            return {"success": False, "reason": "mfa_required"}
        
        # 6. Verificar se a sessao e normal
        session_check = self._check_session_anomaly(username, context)
        if session_check["anomaly"]:
            self._alert("session_anomaly", username, context)
            return {"success": False, "reason": "anomaly_detected"}
        
        return {"success": True, "session_id": self._create_session(username, context)}
    
    def _verify_credentials(self, username: str, password: str) -> bool:
        # Verificacao com protecao contra timing attack
        import hmac
        stored_hash = self._get_password_hash(username)
        computed_hash = self._hash_password(password, stored_hash[:29])
        return hmac.compare_digest(stored_hash, computed_hash)
    
    def _check_session_anomaly(self, username: str, context: dict) -> dict:
        # Verificar se ja existe sessao ativa de outro IP
        active_sessions = self._get_active_sessions(username)
        for session in active_sessions:
            if session["ip"] != context["ip"]:
                return {
                    "anomaly": True,
                    "reason": "concurrent_session_different_ip",
                    "existing_ip": session["ip"],
                }
        
        # Verificar se o horario e incomum
        hour = context.get("hour", 12)
        if hour < 6 or hour > 23:
            return {
                "anomaly": True,
                "reason": "unusual_hour",
                "hour": hour,
            }
        
        return {"anomaly": False}
    
    def _alert(self, alert_type: str, username: str, context: dict):
        # Enviar alerta para SIEM
        pass
```

---

## 14.2 Brute Force Attacks

### 14.2.1 Definição e tipos

Brute force é um ataque de tentativa e erro onde o agressor testa sistematicamente todas as combinações possíveis de credenciais até encontrar a correta. Diferente do credential stuffing — que usa credenciais reais — o brute force gera combinações algoritmicamente.

**Tipos de brute force:**

| Tipo | Descrição | Eficiência |
|------|-----------|-----------|
| Simple brute force | Testa cada senha da lista | Baixa |
| Dictionary attack | Usa lista de palavras comuns | Média |
| Hybrid brute force | Combina dicionário com mutações | Alta |
| Rainbow table | Usa tabelas pré-computadas de hash | Alta (sem salt) |
| Reverse brute force | Usa senha fixa com múltiplos usuários | Média |

### 14.2.2 Velocidade de cracking

A velocidade de brute force depende do algoritmo de hash usado e do hardware disponível:

| Algoritmo | CPU (cores) | GPU (RTX 4090) | Hashes/segundo |
|-----------|-------------|-----------------|----------------|
| MD5 | 50M | 150B | Velocíssimo |
| SHA-1 | 25M | 60B | Muito rápido |
| SHA-256 | 10M | 20B | Rápido |
| bcrypt (cost 10) | 17K | 170K | Lento |
| bcrypt (cost 12) | 4K | 42K | Muito lento |
| Argon2id | 1K | N/A | Extremamente lento |
| PBKDF2 (100K iter) | 5K | N/A | Lento |

Com GPUs modernas, senhas com menos de 12 caracteres em MD5 ou SHA-1 podem ser crackeadas em minutos. Isso reforça a importância de usar algoritmos de hash lentos (Argon2, bcrypt) e senhas longas.

### 14.2.3 Proteção contra brute force

**Lockout de conta:**

```python
class AccountLockout:
    def __init__(self, max_attempts=5, lockout_minutes=15,
                 progressive_lockout=True):
        self.max_attempts = max_attempts
        self.lockout_minutes = lockout_minutes
        self.progressive = progressive_lockout
        self.attempts = {}
    
    def check_and_record(self, username: str, success: bool,
                         timestamp: float) -> dict:
        if username not in self.attempts:
            self.attempts[username] = {
                "failures": [],
                "lockout_until": 0,
                "total_lockouts": 0,
            }
        
        user_data = self.attempts[username]
        
        # Verificar se esta bloqueado
        if user_data["lockout_until"] > timestamp:
            remaining = user_data["lockout_until"] - timestamp
            return {
                "allowed": False,
                "locked": True,
                "remaining_seconds": int(remaining),
                "lockout_count": user_data["total_lockouts"],
            }
        
        if success:
            # Limpar historico apos sucesso
            user_data["failures"] = []
            return {"allowed": True, "locked": False}
        
        # Registrar falha
        user_data["failures"].append(timestamp)
        
        # Limpar falhas antigas (fora da janela)
        window = self.lockout_minutes * 60
        user_data["failures"] = [
            f for f in user_data["failures"]
            if f > timestamp - window
        ]
        
        # Verificar se excedeu o limite
        if len(user_data["failures"]) >= self.max_attempts:
            lockout_duration = self._calculate_lockout_duration(user_data)
            user_data["lockout_until"] = timestamp + lockout_duration
            user_data["total_lockouts"] += 1
            
            return {
                "allowed": False,
                "locked": True,
                "lockout_duration_seconds": int(lockout_duration),
                "lockout_count": user_data["total_lockouts"],
            }
        
        return {
            "allowed": True,
            "locked": False,
            "attempts_remaining": self.max_attempts - len(user_data["failures"]),
        }
    
    def _calculate_lockout_duration(self, user_data: dict) -> float:
        if not self.progressive:
            return self.lockout_minutes * 60
        
        # Lockout progressivo: 15min, 30min, 1h, 2h, 4h...
        base = self.lockout_minutes * 60
        multiplier = 2 ** min(user_data["total_lockouts"], 5)
        return base * multiplier
    
    def reset_lockout(self, username: str):
        if username in self.attempts:
            self.attempts[username]["failures"] = []
            self.attempts[username]["lockout_until"] = 0
```

**Account lockout com CAPTCHA progressivo:**

```python
class ProgressiveProtection:
    def __init__(self):
        self.stages = [
            {"failures": 0, "captcha": False, "delay_ms": 0},
            {"failures": 3, "captcha": True, "delay_ms": 1000},
            {"failures": 5, "captcha": True, "delay_ms": 5000},
            {"failures": 10, "lockout": True, "lockout_minutes": 15},
            {"failures": 20, "lockout": True, "lockout_minutes": 60},
        ]
    
    def get_protection_level(self, failure_count: int) -> dict:
        level = self.stages[0]
        for stage in self.stages:
            if failure_count >= stage["failures"]:
                level = stage
            else:
                break
        return level
    
    def apply_protection(self, username: str, failure_count: int,
                         context: dict) -> dict:
        level = self.get_protection_level(failure_count)
        
        if level.get("lockout"):
            return {
                "allowed": False,
                "reason": "account_locked",
                "lockout_minutes": level["lockout_minutes"],
                "message": "Conta bloqueada por excesso de tentativas",
            }
        
        if level.get("captcha"):
            captcha_token = context.get("captcha_token")
            if not captcha_token or not self._verify_captcha(captcha_token):
                return {
                    "allowed": False,
                    "reason": "captcha_required",
                    "message": "Complete o captcha para continuar",
                }
        
        if level.get("delay_ms", 0) > 0:
            time.sleep(level["delay_ms"] / 1000)
        
        return {"allowed": True}
    
    def _verify_captcha(self, token: str) -> bool:
        # Verificar com servico de captcha (reCAPTCHA, hCaptcha, etc.)
        return True
```

---

## 14.3 Password Spraying

### 14.3.1 Definição

Password spraying é um ataque onde o agressor testa uma pequena quantidade de senhas comuns em um grande número de contas. Enquanto o brute force tenta muitas senhas em poucas contas, o password spraying tenta poucas senhas em muitas contas.

O objetivo é evitar lockout de conta: como cada conta recebe poucas tentativas, o sistema de proteção contra brute force não é acionado.

Exemplos de senhas comuns usadas em spraying:
- `Company123!` (padrão da empresa + número + caractere especial)
- `Summer2026!` (estação + ano + caractere especial)
- `Welcome1!` (mensagem de boas-vindas + número)
- `Password1!` (a senha mais comum do mundo)
- `Admin123!` (cargo + número + caractere especial)

### 14.3.2 Detecção de password spraying

```python
class PasswordSprayDetector:
    def __init__(self):
        self.login_attempts = {}
    
    def record_attempt(self, ip: str, username: str,
                       success: bool, timestamp: float):
        key = f"{ip}:{username}"
        if key not in self.login_attempts:
            self.login_attempts[key] = []
        
        self.login_attempts[key].append({
            "timestamp": timestamp,
            "success": success,
        })
    
    def detect_spray(self, window_minutes: int = 60) -> list:
        alerts = []
        ip_user_counts = {}
        
        for key, attempts in self.login_attempts.items():
            ip = key.split(":")[0]
            username = key.split(":")[1]
            
            recent = [a for a in attempts
                     if a["timestamp"] > time.time() - window_minutes * 60]
            
            if ip not in ip_user_counts:
                ip_user_counts[ip] = set()
            
            if recent:
                ip_user_counts[ip].add(username)
        
        for ip, users in ip_user_counts.items():
            if len(users) > 50:
                alerts.append({
                    "type": "password_spray",
                    "severity": "HIGH",
                    "ip": ip,
                    "unique_users_targeted": len(users),
                    "message": f"IP {ip} attempted login to {len(users)} accounts",
                })
        
        return alerts
```

### 14.3.3 Defesas contra password spraying

1. **MFA**: A defesa mais eficaz. Senhas comuns não importam se o segundo fator é obrigatório.
2. **Senhas fortes**: Forçar senhas com entropia mínima (12+ caracteres, complexidade variada).
3. **Password breach checking**: Verificar senhas contra bancos de dados de vazamento (HIBP).
4. **Rate limiting por account**: Limitar tentativas por conta, não apenas por IP.
5. **Análise de padrões**: Detectar quando um IP tenta logar em muitas contas diferentes.

```python
class SprayDefense:
    def __init__(self):
        self.breach_checker = PasswordBreachChecker()
        self.mfa_provider = None
        self.password_policy = PasswordPolicy(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True,
            max_age_days=90,
            check_breach=True,
        )
    
    def validate_password_strength(self, password: str) -> dict:
        errors = []
        
        if len(password) < self.password_policy.min_length:
            errors.append(f"Minimo {self.password_policy.min_length} caracteres")
        
        if self.password_policy.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Requer pelo menos uma maiuscula")
        
        if self.password_policy.require_lowercase and not any(c.islower() for c in password):
            errors.append("Requer pelo menos uma minuscula")
        
        if self.password_policy.require_digit and not any(c.isdigit() for c in password):
            errors.append("Requer pelo menos um digito")
        
        if self.password_policy.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?" for c in password):
            errors.append("Requer pelo menos um caractere especial")
        
        # Verificar contra senhas comuns
        if self._is_common_password(password):
            errors.append("Senha muito comum")
        
        # Verificar contra vazamentos
        if self.password_policy.check_breach:
            breach = self.breach_checker.check_password(password)
            if breach.get("breached"):
                errors.append(
                    f"Senha encontrada em {breach['count']} vazamentos"
                )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    
    def _is_common_password(self, password: str) -> bool:
        common_passwords = {
            "password", "123456", "12345678", "qwerty",
            "abc123", "monkey", "1234567", "letmein",
            "trustno1", "dragon", "baseball", "iloveyou",
            "master", "sunshine", "ashley", "bailey",
            "passw0rd", "shadow", "123123", "654321",
            "superman", "qazwsx", "michael", "football",
            "password1", "password123", "welcome1",
            "company123", "summer2026", "admin123",
        }
        return password.lower() in common_passwords
```

---

## 14.4 MFA Fatigue / Push Bombing

### 14.4.1 Definição

MFA fatigue (ou push bombing) é um ataque onde o agressor, tendo obtido o nome de usuário e senha, envia repetidamente solicitações de aprovação MFA para o dispositivo da vítima. A premissa é que, após dezenas ou centenas de notificações, a vítima cansa e aprova uma solicitação acidentalmente, ou por frustração, ou por confusão.

O ataque Uber de 2022 é o caso mais conhecido. O atacante da Lapsus$ obteve credenciais de um funcionário da Uber via engenharia social e depois enviou mais de 20 solicitações de push MFA até que o funcionário aceitasse uma.

### 14.4.2 Mecânica do ataque

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Atacante    │────>│  Servico MFA │────>│  Vítima      │
│  (credentials│     │  (push       │     │  (notificacão│
│   + password)│     │   requests)  │     │   no celular)│
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       │                    │                     │
       │                    │                     v
       │                    │              ┌──────────────┐
       │                    │              │  Vítima      │
       │                    │              │  aprova      │
       │                    │              │  (desistencia│
       │                    │              │   ou erro)   │
       │                    │              └──────────────┘
       │                    │                     │
       │<───────────────────│<────────────────────┘
       │    Token MFA       │
       │    comprometido    │
```

### 14.4.3 Defesas contra MFA fatigue

**Defesa 1 — Número de contexto no push:**

```python
class MFAFatigueDefense:
    def __init__(self):
        self.max_push_per_hour = 3
        self.context_verification = True
    
    def send_mfa_request(self, user_id: str, context: dict) -> dict:
        # Verificar quantos pushes foram enviados
        recent_pushes = self._count_recent_pushes(user_id)
        
        if recent_pushes >= self.max_push_per_hour:
            # Bloquear e alertar
            self._alert_mfa_fatigue(user_id, context)
            return {
                "sent": False,
                "reason": "rate_limit_exceeded",
                "alert_sent": True,
            }
        
        # Gerar codigo numerico para verificacao de contexto
        verification_code = self._generate_context_code()
        
        # Enviar push com codigo de verificacao
        push_payload = {
            "type": "mfa_approval",
            "user_id": user_id,
            "context": {
                "ip": context.get("ip"),
                "location": context.get("location"),
                "time": context.get("time"),
                "device": context.get("device"),
                "app": context.get("app"),
                "verification_code": verification_code,
            },
            "message": (
                f"Tentativa de login de {context.get('location', 'desconhecido')} "
                f"as {context.get('time')}. "
                f"Codigo de verificacao: {verification_code}. "
                f"Apenas aprove se VOCE fez esta requisicao."
            ),
        }
        
        self._send_push(user_id, push_payload)
        
        return {"sent": True, "push_id": push_payload["push_id"]}
    
    def verify_mfa_approval(self, user_id: str, push_id: str,
                            verification_code: str) -> dict:
        # Verificar se o codigo de verificacao confere
        stored_code = self._get_stored_code(push_id)
        
        if stored_code != verification_code:
            return {
                "verified": False,
                "reason": "invalid_verification_code",
                "alert": True,
            }
        
        # Verificar se o usuario digitou o codigo corretamente
        # (prova que leu a notificacao em vez de apenas clicar)
        return {"verified": True}
    
    def _alert_mfa_fatigue(self, user_id: str, context: dict):
        alert = {
            "type": "mfa_fatigue_attack",
            "severity": "CRITICAL",
            "user_id": user_id,
            "ip": context.get("ip"),
            "pushes_sent": self._count_recent_pushes(user_id),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Enviar alerta para SOC
        self._send_soc_alert(alert)
        
        # Bloquear conta temporariamente
        self._temporarily_lock_account(user_id, minutes=30)
    
    def _generate_context_code(self) -> str:
        import random
        return str(random.randint(100000, 999999))
```

**Defesa 2 — Número-hash (number matching):**

Em vez de apenas aprovar/rejeitar, o usuário deve digitar um número exibido na tela de login. Isso garante que o usuário está olhando para a tela de login e não apenas clicando no push.

```python
class NumberMatchingMFA:
    def __init__(self):
        self.code_length = 2
    
    def generate_challenge(self, user_id: str,
                           login_context: dict) -> dict:
        # Gerar numero de 2 digitos
        import random
        challenge_number = random.randint(10, 99)
        
        # Armazenar com contexto
        self._store_challenge(user_id, challenge_number, login_context)
        
        # Enviar para dispositivo do usuario
        self._send_to_device(user_id, {
            "type": "number_match",
            "number": challenge_number,
            "context": {
                "ip": login_context.get("ip"),
                "location": login_context.get("location"),
                "time": login_context.get("time"),
            },
        })
        
        # Enviar para tela de login
        return {
            "challenge_sent": True,
            "display_number": challenge_number,
        }
    
    def verify_response(self, user_id: str, entered_number: int) -> dict:
        stored = self._get_stored_challenge(user_id)
        
        if not stored:
            return {"verified": False, "reason": "no_challenge"}
        
        if entered_number == stored["number"]:
            return {"verified": True}
        
        return {"verified": False, "reason": "wrong_number"}
```

**Defesa 3 — Limitação de push e alertas:**

```python
class PushRateLimiter:
    def __init__(self):
        self.max_per_hour = 3
        self.max_per_day = 10
    
    def can_send_push(self, user_id: str) -> dict:
        hourly = self._count_pushes(user_id, hours=1)
        daily = self._count_pushes(user_id, hours=24)
        
        if hourly >= self.max_per_hour:
            return {
                "allowed": False,
                "reason": "hourly_limit",
                "count": hourly,
                "limit": self.max_per_hour,
            }
        
        if daily >= self.max_per_day:
            return {
                "allowed": False,
                "reason": "daily_limit",
                "count": daily,
                "limit": self.max_per_day,
            }
        
        return {"allowed": True}
```

---

## 14.5 Session Hijacking

### 14.5.1 Tipos de session hijacking

Session hijacking é o ataque onde o agressor assume o controle de uma sessão legítima do usuário. Existem múltiplas variantes:

**Cookie theft**: O agressor obtém o cookie de sessão do usuário via XSS, malware, ou interceptação de rede.

**Session fixation**: O agressor força o usuário a usar um ID de sessão conhecido. Quando o usuário faz login, o agressor já conhece o session ID.

**Session sidejacking**: Interceptação de cookies em tráfego HTTP não criptografado (rede WiFi pública).

**Man-in-the-middle (MITM)**: Interceptação e modificação de tráfego entre cliente e servidor.

### 14.5.2 Session fixation

```python
class SessionFixationDefense:
    def __init__(self):
        self.regenerate_on_login = True
        self.session_timeout = 3600  # 1 hora
    
    def create_session(self, user_id: str, context: dict) -> str:
        import secrets
        import hashlib
        
        # Gerar session ID cryptograficamente seguro
        raw_token = secrets.token_bytes(32)
        session_id = hashlib.sha256(raw_token).hexdigest()
        
        # associar a sessao ao contexto
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "ip_address": context.get("ip"),
            "user_agent": context.get("user_agent"),
            "fingerprint": self._generate_fingerprint(context),
            "login_completed": False,
            "mfa_verified": False,
        }
        
        self._store_session(session_data)
        
        return session_id
    
    def on_login_success(self, session_id: str):
        """Regenerar session ID apos login bem-sucedido."""
        if self.regenerate_on_login:
            old_session = self._get_session(session_id)
            
            import secrets
            import hashlib
            new_raw = secrets.token_bytes(32)
            new_session_id = hashlib.sha256(new_raw).hexdigest()
            
            new_session = old_session.copy()
            new_session["session_id"] = new_session_id
            new_session["login_completed"] = True
            new_session["regenerated_at"] = time.time()
            
            self._delete_session(session_id)
            self._store_session(new_session)
            
            return new_session_id
        
        return session_id
    
    def validate_session(self, session_id: str, context: dict) -> dict:
        session = self._get_session(session_id)
        
        if not session:
            return {"valid": False, "reason": "session_not_found"}
        
        # Verificar timeout
        if time.time() - session["last_activity"] > self.session_timeout:
            self._delete_session(session_id)
            return {"valid": False, "reason": "session_expired"}
        
        # Verificar IP binding
        if session["ip_address"] != context.get("ip"):
            self._alert("session_ip_mismatch", session, context)
            self._delete_session(session_id)
            return {"valid": False, "reason": "ip_mismatch"}
        
        # Verificar User-Agent
        if session["user_agent"] != context.get("user_agent"):
            self._alert("session_ua_mismatch", session, context)
            return {"valid": False, "reason": "ua_mismatch"}
        
        # Verificar fingerprint
        current_fingerprint = self._generate_fingerprint(context)
        if session["fingerprint"] != current_fingerprint:
            self._alert("session_fingerprint_mismatch", session, context)
            return {"valid": False, "reason": "fingerprint_mismatch"}
        
        # Verificar se a sessao esta sendo usada de multiple IPs simultaneamente
        concurrent = self._check_concurrent_sessions(session["user_id"], session_id)
        if concurrent:
            self._alert("concurrent_sessions", session, context)
            return {"valid": False, "reason": "concurrent_session_detected"}
        
        # Atualizar last_activity
        session["last_activity"] = time.time()
        self._store_session(session)
        
        return {"valid": True}
    
    def _generate_fingerprint(self, context: dict) -> str:
        import hashlib
        fingerprint_data = "|".join([
            context.get("user_agent", ""),
            context.get("accept_language", ""),
            context.get("screen_resolution", ""),
            context.get("timezone", ""),
            context.get("platform", ""),
        ])
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def _check_concurrent_sessions(self, user_id: str,
                                    current_session: str) -> bool:
        sessions = self._get_all_sessions(user_id)
        active = [
            s for s in sessions
            if s["session_id"] != current_session
            and time.time() - s["last_activity"] < 300
            and s["ip_address"] != sessions[0].get("ip_address")
        ]
        return len(active) > 0
```

### 14.5.3 Cookie security

```python
class SecureCookieConfig:
    def __init__(self):
        self.config = {
            "session_cookie": {
                "name": "__Host-session",
                "secure": True,
                "httponly": True,
                "samesite": "Strict",
                "path": "/",
                "max_age": 3600,
            },
            "csrf_cookie": {
                "name": "__Host-csrf",
                "secure": True,
                "httponly": False,  # JS precisa ler
                "samesite": "Strict",
                "path": "/",
                "max_age": 3600,
            },
        }
    
    def set_session_cookie(self, response, session_id: str):
        config = self.config["session_cookie"]
        response.set_cookie(
            key=config["name"],
            value=session_id,
            secure=config["secure"],
            httponly=config["httponly"],
            samesite=config["samesite"],
            path=config["path"],
            max_age=config["max_age"],
        )
    
    def set_csrf_cookie(self, response, csrf_token: str):
        config = self.config["csrf_cookie"]
        response.set_cookie(
            key=config["name"],
            value=csrf_token,
            secure=config["secure"],
            httponly=config["httponly"],
            samesite=config["samesite"],
            path=config["path"],
            max_age=config["max_age"],
        )
```

### 14.5.4 Defesa contra sidejacking

```python
class AntiSidejacking:
    def __init__(self):
        self.enforce_https = True
        self.hsts_max_age = 31536000  # 1 ano
        self.hsts_include_subdomains = True
        self.hsts_preload = True
    
    def add_security_headers(self, response):
        # HSTS - força HTTPS
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        
        response.headers["Strict-Transport-Security"] = hsts_value
        
        # Previne clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Previne MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # CSP basico
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=()"
        )
    
    def enforce_https_redirect(self, request):
        if self.enforce_https and request.scheme != "https":
            https_url = request.url.replace("http://", "https://")
            return {"redirect": True, "url": https_url}
        return {"redirect": False}
```

---

## 14.6 Token Theft

### 14.6.1 Tipos de tokens e vetores de roubo

**JWT (JSON Web Token)**:
- Roubo via XSS (access token armazenado em localStorage).
- Roubo via MITM (access token em tráfego HTTP).
- Roubo via logs (token impresso em logs de servidor).

**Refresh Token**:
- Roubo via XSS (se armazenado no client-side).
- Roubo via malware (infostealers).
- Roubo via device compromise.

**API Keys**:
- Roubo via repositórios públicos (GitHub).
- Roubo via variáveis de ambiente expostas.
- Roubo via config files commitados.

### 14.6.2 Detecção de token theft

```python
class TokenTheftDetector:
    def __init__(self):
        self.token_bindings = {}
    
    def bind_token(self, token_id: str, context: dict):
        self.token_bindings[token_id] = {
            "created_at": time.time(),
            "ip": context.get("ip"),
            "user_agent": context.get("user_agent"),
            "fingerprint": context.get("fingerprint"),
            "geo": context.get("geo"),
        }
    
    def validate_token(self, token_id: str, context: dict) -> dict:
        binding = self.token_bindings.get(token_id)
        
        if not binding:
            return {"valid": True, "warning": "no_binding"}
        
        # Verificar se o token esta sendo usado de um contexto diferente
        mismatches = []
        
        if binding["ip"] != context.get("ip"):
            mismatches.append({
                "field": "ip",
                "original": binding["ip"],
                "current": context.get("ip"),
            })
        
        if binding["user_agent"] != context.get("user_agent"):
            mismatches.append({
                "field": "user_agent",
                "original": binding["user_agent"][:50],
                "current": context.get("user_agent", "")[:50],
            })
        
        if binding["geo"] != context.get("geo"):
            mismatches.append({
                "field": "geo",
                "original": binding["geo"],
                "current": context.get("geo"),
            })
        
        if mismatches:
            severity = self._assess_severity(mismatches)
            
            if severity == "CRITICAL":
                # Token possivelmente roubado - invalidar
                self._revoke_token(token_id)
                self._alert_token_theft(token_id, context, mismatches)
                return {
                    "valid": False,
                    "reason": "possible_token_theft",
                    "revoked": True,
                }
            
            return {
                "valid": True,
                "warning": "context_mismatch",
                "mismatches": mismatches,
            }
        
        return {"valid": True}
    
    def _assess_severity(self, mismatches: list) -> str:
        fields = [m["field"] for m in mismatches]
        
        if "ip" in fields and "user_agent" in fields:
            return "CRITICAL"
        if "ip" in fields:
            return "HIGH"
        if "user_agent" in fields:
            return "MEDIUM"
        return "LOW"
```

### 14.6.3 Proteção de tokens

```python
class TokenProtection:
    def __init__(self):
        self.access_token_ttl = 900  # 15 minutos
        self.refresh_token_ttl = 86400  # 24 horas
        self.rotate_refresh_on_use = True
    
    def create_token_pair(self, user_id: str, context: dict) -> dict:
        import secrets
        import hashlib
        import jwt
        from datetime import datetime, timedelta
        
        # Access token (curta duracao)
        access_payload = {
            "sub": user_id,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.access_token_ttl),
            "jti": secrets.token_hex(16),
            "ip_hash": hashlib.sha256(
                context.get("ip", "").encode()
            ).hexdigest()[:8],
        }
        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm="HS256")
        
        # Refresh token (longa duracao, rotacionado)
        refresh_payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.refresh_token_ttl),
            "jti": secrets.token_hex(16),
            "family": secrets.token_hex(8),
        }
        refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm="HS256")
        
        # Bind token ao contexto
        self.bind_token(access_payload["jti"], context)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.access_token_ttl,
            "token_type": "Bearer",
        }
    
    def refresh_access_token(self, refresh_token: str,
                             context: dict) -> dict:
        import jwt
        from datetime import datetime, timedelta
        
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return {"error": "invalid_token"}
        
        if payload["type"] != "refresh":
            return {"error": "wrong_token_type"}
        
        # Verificar se o refresh token nao foi reutilizado
        # (token theft detection via token family)
        if self._is_refresh_token_used(payload["jti"]):
            # Token possivelmente roubado - invalidar toda a familia
            self._revoke_token_family(payload["family"])
            self._alert_refresh_token_reuse(payload, context)
            return {"error": "token_reuse_detected", "family_revoked": True}
        
        # Marcar refresh token como usado
        self._mark_refresh_token_used(payload["jti"])
        
        # Criar novos tokens
        return self.create_token_pair(payload["sub"], context)
```

---

## 14.7 OAuth/OIDC Attacks

### 14.7.1 Open Redirect

Open redirect é uma vulnerabilidade onde o servidor redireciona o usuário para uma URL arbitrária controlada pelo atacante. Em OAuth/OIDC, isso permite roubar authorization codes ou tokens.

**Fluxo do ataque:**

```
1. Atacante gera URL maliciosa:
   https://legit.com/auth?redirect=https://evil.com/callback

2. Vítima clica no link (via phishing)

3. Servidor redireciona para login:
   https://legit.com/login?redirect=https://evil.com/callback

4. Vítima faz login

5. Servidor redireciona para callback do atacante:
   https://evil.com/callback?code=AUTH_CODE_AQUI

6. Atacante troca o code por tokens
```

**Defesa:**

```python
class OAuthRedirectValidator:
    def __init__(self, allowed_domains: list):
        self.allowed_domains = allowed_domains
        self.allowed_schemes = ["https"]
    
    def validate_redirect_uri(self, redirect_uri: str) -> dict:
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(redirect_uri)
        except Exception:
            return {"valid": False, "reason": "malformed_uri"}
        
        # Verificar scheme
        if parsed.scheme not in self.allowed_schemes:
            return {
                "valid": False,
                "reason": "invalid_scheme",
                "scheme": parsed.scheme,
            }
        
        # Verificar dominio
        domain = parsed.hostname
        if domain not in self.allowed_domains:
            return {
                "valid": False,
                "reason": "unauthorized_domain",
                "domain": domain,
            }
        
        # Verificar se nao ha path traversal
        if ".." in parsed.path or "//" in parsed.path:
            return {"valid": False, "reason": "path_traversal"}
        
        # Verificar se nao ha fragmentos (pode conter code)
        if parsed.fragment:
            return {"valid": False, "reason": "fragment_present"}
        
        return {"valid": True}
    
    def validate_state_parameter(self, state: str,
                                  session_state: str) -> dict:
        import hmac
        
        if not state:
            return {"valid": False, "reason": "missing_state"}
        
        if not hmac.compare_digest(state, session_state):
            return {"valid": False, "reason": "state_mismatch"}
        
        return {"valid": True}
```

### 14.7.2 Token Leakage

**Via logs:**

```python
class SafeTokenLogger:
    def __init__(self):
        self.sensitive_fields = [
            "access_token", "refresh_token", "id_token",
            "password", "secret", "api_key", "authorization",
        ]
    
    def sanitize_log_entry(self, entry: dict) -> dict:
        sanitized = {}
        for key, value in entry.items():
            if key.lower() in self.sensitive_fields:
                sanitized[key] = self._mask(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_log_entry(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def _mask(self, value: str) -> str:
        if not value or len(value) < 8:
            return "***"
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
```

**Via referrer header:**

```python
class AntiReferrerLeak:
    def add_referrer_policy(self, response):
        # Previne que tokens sejam vazados via Referrer header
        response.headers["Referrer-Policy"] = "no-referrer"
```

### 14.7.3 PKCE (Proof Key for Code Exchange)

PKCE previne que authorization codes sejam interceptados e trocados por tokens:

```python
import hashlib
import base64
import secrets

class PKCEHandler:
    def __init__(self):
        self.verifier_length = 128
    
    def generate_challenge(self) -> dict:
        # Gerar code verifier (aleatorio)
        code_verifier = base64.urlsafe_b64encode(
            secrets.token_bytes(self.verifier_length)
        ).rstrip(b"=").decode()
        
        # Gerar code challenge (SHA-256 do verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        
        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    
    def verify(self, code_verifier: str,
               stored_challenge: str) -> bool:
        # Recalcular challenge a partir do verifier
        computed_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        
        import hmac
        return hmac.compare_digest(computed_challenge, stored_challenge)
```

---

## 14.8 Social Engineering para Credenciais

### 14.8.1 Técnicas de engenharia social

Social engineering é a manipulação psicológica para obter informações confidenciais. No contexto de credenciais, as técnicas incluem:

**Phishing**: Emails ou mensagens que imitam fontes legítimas para induzir o usuário a fornecer credenciais.

**Vishing**: Phishing por voz (ligações telefônicas).

**Smishing**: Phishing por SMS.

**Spear phishing**: Phishing direcionado a indivíduos específicos com informações personalizadas.

**Whaling**: Spear phishing direcionado a executivos de alto nível.

**Pretexting**: Criação de um cenário falso (pretexto) para justificar a solicitação de credenciais.

**Baiting**: Uso de mídias físicas (USB, CDs) infectadas para roubar credenciais.

### 14.8.2 Defesas contra engenharia social

```python
class AntiPhishingDefense:
    def __init__(self):
        self.dmARC_policy = "quarantine"
        self.dkim_selector = "default"
        self.spf_allowed_senders = []
    
    def verify_email_auth(self, email_headers: dict) -> dict:
        checks = {
            "spf": self._check_spf(email_headers),
            "dkim": self._check_dkim(email_headers),
            "dmarc": self._check_dmarc(email_headers),
        }
        
        all_pass = all(checks.values())
        
        return {
            "authenticated": all_pass,
            "checks": checks,
            "action": "allow" if all_pass else "quarantine",
        }
    
    def detect_phishing_indicators(self, email_content: dict) -> dict:
        indicators = []
        
        # Verificar URLs suspeitas
        urls = self._extract_urls(email_content.get("body", ""))
        for url in urls:
            if self._is_suspicious_url(url):
                indicators.append({"type": "suspicious_url", "url": url})
        
        # Verificar dominio spoofed
        from_domain = email_content.get("from", "")
        if self._is_spoofed_domain(from_domain):
            indicators.append({"type": "spoofed_domain", "domain": from_domain})
        
        # Verificar urgencia
        urgency_words = ["urgente", "imediato", "bloqueado", "suspendido",
                        "acao necessaria", "verifique sua conta"]
        body = email_content.get("body", "").lower()
        for word in urgency_words:
            if word in body:
                indicators.append({"type": "urgency_language", "word": word})
        
        # Verificar solicitacao de credenciais
        credential_words = ["senha", "password", "credenciais", "login",
                          "usuario", "token", "chave"]
        for word in credential_words:
            if word in body:
                indicators.append({"type": "credential_request", "word": word})
        
        return {
            "phishing_risk": len(indicators) > 0,
            "indicators": indicators,
            "risk_level": self._assess_risk_level(indicators),
        }
    
    def _extract_urls(self, text: str) -> list:
        import re
        return re.findall(r'https?://[^\s<>"]+', text)
    
    def _is_suspicious_url(self, url: str) -> bool:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        suspicious_tlds = [".xyz", ".top", ".club", ".buzz", ".tk"]
        suspicious_patterns = [
            "login", "verify", "secure", "account",
            "update", "confirm", "banking",
        ]
        
        if any(parsed.netloc.endswith(tld) for tld in suspicious_tlds):
            return True
        
        if any(pattern in parsed.netloc.lower() for pattern in suspicious_patterns):
            return True
        
        return False
    
    def _is_spoofed_domain(self, from_domain: str) -> bool:
        legitimate_domains = ["gov.br", "serpro.gov.br", "id.gov.br"]
        return not any(from_domain.endswith(d) for d in legitimate_domains)
    
    def _assess_risk_level(self, indicators: list) -> str:
        if len(indicators) >= 3:
            return "CRITICAL"
        elif len(indicators) >= 2:
            return "HIGH"
        elif len(indicators) >= 1:
            return "MEDIUM"
        return "LOW"
```

### 14.8.3 Proteção contra spear phishing para operadores do IDAP

```python
class IDAPOperatorProtection:
    def __init__(self):
        self.allowed_email_domains = ["gov.br", "sp.gov.br"]
        self.required_training = True
        self.simulation_interval_days = 90
    
    def validate_operator_access(self, operator_id: str,
                                  context: dict) -> dict:
        # 1. Verificar se o operador completou treinamento
        training = self._check_training(operator_id)
        if not training["current"]:
            return {
                "allowed": False,
                "reason": "training_required",
                "training_due": training["due_date"],
            }
        
        # 2. Verificar se o operador passou no simulado recente
        simulation = self._check_simulation(operator_id)
        if not simulation["passed"]:
            return {
                "allowed": False,
                "reason": "simulation_failed",
                "score": simulation["score"],
            }
        
        # 3. Verificar se o operador esta usando dispositivo registrado
        device = self._check_device(operator_id, context)
        if not device["registered"]:
            return {
                "allowed": False,
                "reason": "unregistered_device",
            }
        
        return {"allowed": True}
    
    def simulate_phishing(self, operator_id: str) -> dict:
        # Enviar email de phishing simulado
        import secrets
        tracking_id = secrets.token_hex(8)
        
        self._send_simulated_phishing(
            operator_id=operator_id,
            tracking_id=tracking_id,
            template="credential_harvest",
        )
        
        return {
            "simulation_sent": True,
            "tracking_id": tracking_id,
        }
    
    def report_simulation_result(self, tracking_id: str,
                                  clicked: bool, submitted: bool) -> dict:
        result = {
            "tracking_id": tracking_id,
            "clicked": clicked,
            "submitted": submitted,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._store_simulation_result(result)
        
        if clicked or submitted:
            # Forcar retreinamento
            self._force_retraining(tracking_id)
        
        return result
```

---

## 14.9 SIM Swapping

### 14.9.1 Definição

SIM swapping (ou SIM hijacking) é um ataque onde o agressor convence (ou suborna) um funcionário de operadora de telefonia a transferir o número de telefone da vítima para um novo SIM controlado pelo atacante. Com isso, o atacante recebe as chamadas e SMS da vítima, incluindo códigos MFA enviados por SMS.

### 14.9.2 Impacto no IDAP

No contexto do IDAP, se o sistema utilizasse SMS como segundo fator MFA, um atacante com SIM swapping poderia:
1. Receber códigos de verificação SMS enviados ao operador.
2. Completar a autenticação MFA usando o código recebido.
3. Acessar o sistema com credenciais e MFA legítimos.

### 14.9.3 Defesas contra SIM swapping

```python
class AntiSIMSwap:
    def __init__(self):
        self.preferred_mfa_methods = [
            "hardware_key",    # YubiKey, etc.
            "authenticator_app",  # TOTP (Google Authenticator, etc.)
            "push_notification",  # App dedicada
            "biometric",       # Reconhecimento facial/fingerprint
            "sms",             # Ultima opcao
        ]
    
    def get_mfa_method_priority(self, user_risk_level: str) -> list:
        if user_risk_level == "HIGH":
            # Para usuarios de alto risco, apenas metodos seguros
            return ["hardware_key", "biometric"]
        
        if user_risk_level == "MEDIUM":
            return ["hardware_key", "authenticator_app", "biometric"]
        
        return self.preferred_mfa_methods
    
    def detect_sim_swap(self, phone_number: str,
                        recent_events: list) -> dict:
        # Verificar se houve mudanca recente de SIM
        sim_changes = [
            e for e in recent_events
            if e["type"] == "sim_change"
            and e["timestamp"] > time.time() - 86400  # ultimas 24h
        ]
        
        if sim_changes:
            return {
                "sim_swap_detected": True,
                "change_time": sim_changes[0]["timestamp"],
                "action": "block_mfa_sms",
                "require_alternative_mfa": True,
            }
        
        return {"sim_swap_detected": False}
    
    def enforce_secure_mfa(self, user_id: str) -> dict:
        user_mfa = self._get_user_mfa_setup(user_id)
        
        # Se usuario usa apenas SMS, forcar upgrade
        if user_mfa["methods"] == ["sms"]:
            return {
                "upgrade_required": True,
                "current_methods": ["sms"],
                "recommended_methods": ["authenticator_app", "hardware_key"],
                "deadline_days": 30,
            }
        
        return {"upgrade_required": False}
```

---

## 14.10 Defesas Gerais e Estratégias de Detecção

### 14.10.1 Framework de detecção de ataques a identidade

```python
class IdentityAttackDetector:
    def __init__(self):
        self.detectors = {
            "credential_stuffing": CredentialStuffingDetector(),
            "brute_force": BruteForceDetector(),
            "password_spray": PasswordSprayDetector(),
            "mfa_fatigue": MFADetector(),
            "session_hijack": SessionHijackDetector(),
            "token_theft": TokenTheftDetector(),
        }
        self.alert_threshold = 0.7
    
    def analyze_event(self, event: dict) -> dict:
        detections = {}
        
        for name, detector in self.detectors.items():
            result = detector.analyze(event)
            if result.get("detected"):
                detections[name] = result
        
        # Calcular score geral de risco
        risk_score = self._calculate_overall_risk(detections)
        
        # Determinar acao
        action = self._determine_action(risk_score, detections)
        
        return {
            "event_id": event.get("event_id"),
            "timestamp": datetime.utcnow().isoformat(),
            "detections": detections,
            "risk_score": risk_score,
            "action": action,
        }
    
    def _calculate_overall_risk(self, detections: dict) -> float:
        if not detections:
            return 0.0
        
        weights = {
            "credential_stuffing": 0.9,
            "brute_force": 0.7,
            "password_spray": 0.8,
            "mfa_fatigue": 0.95,
            "session_hijack": 0.85,
            "token_theft": 0.8,
        }
        
        total = sum(
            weights.get(name, 0.5) * d.get("confidence", 0.5)
            for name, d in detections.items()
        )
        
        return min(1.0, total / len(detections))
    
    def _determine_action(self, risk_score: float,
                          detections: dict) -> str:
        if risk_score > 0.9:
            return "BLOCK_AND_ALERT"
        elif risk_score > 0.7:
            return "CHALLENGE_MFA"
        elif risk_score > 0.5:
            return "RATE_LIMIT"
        elif risk_score > 0.3:
            return "LOG_AND_MONITOR"
        else:
            return "ALLOW"
```

### 14.10.2 Resposta a incidentes de identidade

```python
class IdentityIncidentResponse:
    def __init__(self):
        self.playbooks = {
            "credential_compromise": self._playbook_credential_compromise,
            "session_hijack": self._playbook_session_hijack,
            "mfa_bypass": self._playbook_mfa_bypass,
            "account_takeover": self._playbook_account_takeover,
        }
    
    def respond(self, incident_type: str, context: dict) -> dict:
        playbook = self.playbooks.get(incident_type)
        
        if not playbook:
            return {"error": f"No playbook for {incident_type}"}
        
        return playbook(context)
    
    def _playbook_credential_compromise(self, context: dict) -> dict:
        actions = []
        
        # 1. Invalidar todas as sessoes do usuario
        self._invalidate_all_sessions(context["user_id"])
        actions.append("sessions_invalidated")
        
        # 2. Forcar reset de senha
        self._force_password_reset(context["user_id"])
        actions.append("password_reset_forced")
        
        # 3. Invalidar todos os tokens
        self._revoke_all_tokens(context["user_id"])
        actions.append("tokens_revoked")
        
        # 4. Verificar atividade recente
        activity = self._audit_recent_activity(context["user_id"])
        actions.append(f"activity_audited_{len(activity)}_events")
        
        # 5. Notificar usuario
        self._notify_user(context["user_id"], "credential_compromise")
        actions.append("user_notified")
        
        # 6. Reportar a autoridade (se LGPD)
        if context.get("data_exposed"):
            self._report_to_anpd(context)
            actions.append("anpd_reported")
        
        return {
            "incident_type": "credential_compromise",
            "actions_taken": actions,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _playbook_session_hijack(self, context: dict) -> dict:
        actions = []
        
        # 1. Invalidar sessao suspeita
        self._invalidate_session(context["session_id"])
        actions.append("suspicious_session_invalidated")
        
        # 2. Invalidar todas as sessoes do mesmo usuario
        self._invalidate_all_sessions(context["user_id"])
        actions.append("all_sessions_invalidated")
        
        # 3. Analisar IP e User-Agent
        analysis = self._analyze_attack_source(context)
        actions.append(f"source_analyzed_{analysis['country']}")
        
        # 4. Bloquear IP se necessario
        if analysis["risk"] > 0.8:
            self._block_ip(context["ip"], duration_hours=24)
            actions.append("ip_blocked")
        
        return {
            "incident_type": "session_hijack",
            "actions_taken": actions,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _playbook_account_takeover(self, context: dict) -> dict:
        actions = []
        
        # 1. Bloquear conta imediatamente
        self._lock_account(context["user_id"])
        actions.append("account_locked")
        
        # 2. Invalidar tudo (sessoes, tokens, MFA)
        self._invalidate_all_sessions(context["user_id"])
        self._revoke_all_tokens(context["user_id"])
        self._reset_mfa(context["user_id"])
        actions.append("all_credentials_revoked")
        
        # 3. Verificar dados acessados
        accessed_data = self._audit_data_access(context["user_id"])
        actions.append(f"data_access_audited_{len(accessed_data)}_records")
        
        # 4. Notificar usuario e admin
        self._notify_user(context["user_id"], "account_takeover")
        self._notify_admin(context)
        actions.append("notifications_sent")
        
        # 5. Se dados sensiveis foram acessados, reportar
        if any(d["classification"] == "sensitive" for d in accessed_data):
            self._report_to_anpd(context)
            actions.append("anpd_reported")
        
        return {
            "incident_type": "account_takeover",
            "actions_taken": actions,
            "timestamp": datetime.utcnow().isoformat(),
            "data_exposed": accessed_data,
        }
```

### 14.10.3 Monitoramento contínuo

```python
class IdentityMonitor:
    def __init__(self):
        self.metrics = {}
        self.baselines = {}
    
    def track_metric(self, metric_name: str, value: float,
                     timestamp: float):
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": timestamp,
        })
        
        # Manter apenas ultimas 24h
        cutoff = timestamp - 86400
        self.metrics[metric_name] = [
            m for m in self.metrics[metric_name]
            if m["timestamp"] > cutoff
        ]
    
    def detect_anomalies(self, metric_name: str) -> dict:
        if metric_name not in self.metrics:
            return {"anomaly": False}
        
        values = [m["value"] for m in self.metrics[metric_name]]
        
        if len(values) < 10:
            return {"anomaly": False}
        
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        current = values[-1]
        z_score = (current - mean) / std_dev if std_dev > 0 else 0
        
        return {
            "anomaly": abs(z_score) > 3,
            "metric": metric_name,
            "current_value": current,
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "z_score": round(z_score, 2),
            "severity": "HIGH" if abs(z_score) > 4 else "MEDIUM" if abs(z_score) > 3 else "LOW",
        }
    
    def get_dashboard(self) -> dict:
        return {
            "total_login_attempts_24h": len(self.metrics.get("login_attempts", [])),
            "failed_logins_24h": len([
                m for m in self.metrics.get("login_attempts", [])
                if m["value"] == 0
            ]),
            "mfa_completions_24h": len(self.metrics.get("mfa_completions", [])),
            "session_count": len(self.metrics.get("active_sessions", [])),
            "anomalies_detected": [
                self.detect_anomalies(m) for m in self.metrics
                if self.detect_anomalies(m).get("anomaly")
            ],
        }
```

### 14.10.4 Referências

- OWASP. "Credential Stuffing Prevention Cheat Sheet" (2023)
- OWASP. "Brute Force Attack Prevention" (2023)
- OWASP. "Session Management Cheat Sheet" (2023)
- OWASP. "MFA Fatigue / Push Bombing" (2023)
- NIST SP 800-63B: Digital Identity Guidelines (2020)
- NIST SP 800-63C: Federation and Assertions (2020)
- Google/Fireworks. "Password Reuse Study" (2019)
- Uber/Lapsus$ Incident Report (2022)
- Have I Been Pwned (HIBP) API Documentation
- RFC 6749: OAuth 2.0 Authorization Framework
- RFC 7636: PKCE for OAuth 2.0
- RFC 7519: JSON Web Token (JWT)
- RFC 6265: HTTP State Management (Cookies)
- MITRE ATT&CK: T1110 (Brute Force)
- MITRE ATT&CK: T1539 (Steal Web Session Cookie)
- MITRE ATT&CK: T1557 (Adversary-in-the-Middle)
- MITRE ATT&CK: T1621 (Multi-Factor Authentication Request Generation)
- LGPD. "Lei Geral de Protecao de Dados" (2020)
- LGPD. "Art. 48 — Comunicacao de incidentes" (2020)
- ISO/IEC 27001: Information Security Management (2022)
- Bishop, M. "Computer Security: Art and Science" (2003)
- Anderson, R. "Security Engineering" (2008)
- Pfleeger, C., Pfleeger, S. "Security in Computing" (2006)

---

## 14.11 Vulnerabilidades de Implementação Comuns

### 14.11.1 Timing attacks em comparação de senhas

Timing attacks exploram diferenças no tempo de execução de comparações. Se o sistema compara senhas usando `==` ou `string.equals()` em vez de comparação constante-tempo, o atacante pode medir o tempo de resposta para deduzir caracteres da senha correta.

```python
# VULNERAVEL: timing attack
def verify_password_vulnerable(input_password: str,
                                stored_hash: str) -> bool:
    computed_hash = hash_password(input_password)
    # == compara byte a byte e retorna False no primeiro mismatch
    # Isso revela quantos bytes estao corretos
    return computed_hash == stored_hash

# SEGURO: comparacao constante-tempo
import hmac

def verify_password_secure(input_password: str,
                           stored_hash: str) -> bool:
    computed_hash = hash_password(input_password)
    # hmac.compare_digest compara TODOS os bytes
    # Tempo constante independente de onde ha mismatch
    return hmac.compare_digest(computed_hash, stored_hash)
```

A diferença é sutil mas crítica. Com `==`, se a primeira letra está correta, a comparação continua para a segunda letra, levando ~10ns a mais. Com `hmac.compare_digest`, o tempo é sempre o mesmo (~50ns), independentemente de quantos bytes coincidem.

### 14.11.2 Session fixation detalhado

Session fixation ocorre quando o atacante pode definir o session ID antes do login da vítima:

```python
# VULNERAVEL: session fixation
class VulnerableSessionHandler:
    def handle_request(self, request):
        # Se ja existe session_id no cookie, reutiliza
        session_id = request.cookies.get("session_id")
        
        if not session_id:
            session_id = self.generate_session_id()
        
        # Nao regenera apos login!
        return session_id

# SEGURO: regeneracao apos login
class SecureSessionHandler:
    def handle_request(self, request):
        session_id = request.cookies.get("session_id")
        
        if not session_id:
            session_id = self.generate_session_id()
        
        return session_id
    
    def on_login_success(self, session_id: str):
        """Regenerar session ID apos login bem-sucedido."""
        # Gerar NOVO session ID
        new_session_id = self.generate_session_id()
        
        # Copiar dados da sessao antiga para a nova
        old_session = self.get_session(session_id)
        self.store_session(new_session_id, old_session)
        
        # Deletar sessao antiga
        self.delete_session(session_id)
        
        return new_session_id
```

### 14.11.3 JWT vulnerabilities

```python
# VULNERAVEL: JWT com algorithm confusion
import jwt

def verify_jwt_vulnerable(token: str, secret: str) -> dict:
    # Permite que o atacante mude o algoritmo para 'none'
    # Ou de HS256 para RS256 (confusion attack)
    return jwt.decode(token, secret, algorithms=["HS256", "RS256", "none"])

# SEGURO: algoritmos explicitos e whitelist
def verify_jwt_secure(token: str, public_key: str) -> dict:
    # Apenas algoritmos explicitamente permitidos
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],  # Apenas RS256
        options={
            "require": ["exp", "iss", "sub", "aud"],
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": True,
        }
    )

# VULNERAVEL: JWT sem validacao de claims
def verify_jwt_weak(token: str, secret: str) -> dict:
    # Decodifica mas nao valida claims
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    # Falta: verificar exp, iss, aud, sub
    return payload

# SEGUAR: JWT com validacao completa
def verify_jwt_strong(token: str, secret: str,
                      expected_issuer: str,
                      expected_audience: str) -> dict:
    payload = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=expected_issuer,
        audience=expected_audience,
        options={
            "require": ["exp", "iss", "sub", "aud", "iat"],
        }
    )
    
    # Verificar se nao foi revogado
    if self.is_token_revoked(payload["jti"]):
        raise jwt.InvalidTokenError("Token revoked")
    
    return payload
```

### 14.11.4 Password reset vulnerabilities

```python
# VULNERAVEL: reset token previsivel
class VulnerablePasswordReset:
    def generate_reset_token(self, user_id: str) -> str:
        # Token baseado em timestamp - previsivel
        import time
        return str(int(time.time())) + str(user_id)

# VULNERAVEL: reset token sem expiracao
class VulnerablePasswordReset2:
    def generate_reset_token(self, user_id: str) -> str:
        import secrets
        return secrets.token_urlsafe(32)
    # Token nunca expira!

# SEGURO: reset token seguro
class SecurePasswordReset:
    def __init__(self):
        self.token_ttl = 3600  # 1 hora
        self.max_uses = 1
    
    def generate_reset_token(self, user_id: str) -> str:
        import secrets
        import hashlib
        
        # Token aleatorio e criptograficamente seguro
        raw_token = secrets.token_urlsafe(32)
        
        # Hash para armazenar (nao o token bruto)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        # Armazenar com metadados
        self.store_token(
            user_id=user_id,
            token_hash=token_hash,
            created_at=time.time(),
            expires_at=time.time() + self.token_ttl,
            uses=0,
            max_uses=self.max_uses,
        )
        
        # Retornar token bruto (o usuario recebe isso)
        return raw_token
    
    def verify_reset_token(self, user_id: str,
                           token: str) -> dict:
        import hashlib
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored = self.get_token(user_id, token_hash)
        
        if not stored:
            return {"valid": False, "reason": "invalid_token"}
        
        if time.time() > stored["expires_at"]:
            self.delete_token(user_id, token_hash)
            return {"valid": False, "reason": "token_expired"}
        
        if stored["uses"] >= stored["max_uses"]:
            self.delete_token(user_id, token_hash)
            return {"valid": False, "reason": "token_used"}
        
        # Incrementar uso
        stored["uses"] += 1
        self.update_token(user_id, token_hash, stored)
        
        return {"valid": True}
    
    def invalidate_all_tokens(self, user_id: str):
        """Invalidar todos os tokens de reset do usuario."""
        self.delete_all_tokens(user_id)
```

---

## 14.12 Autenticação em Sistemas Legados

### 14.12.1 Desafios de modernizar autenticação legada

Muitos sistemas governamentais (incluindo o IDAP) foram desenvolvidos com tecnologias antigas e não suportam nativamente MFA, tokens modernos, ou autenticação passwordless. A modernização precisa equilibrar segurança com continuidade operacional.

**Abordagem incremental — proxy de autenticação:**

```python
# Proxy que adiciona MFA a sistemas legados sem modificacao do legado
# O proxy intercepta o login, adiciona MFA, e passa para o legado

class AuthenticationProxy:
    def __init__(self, legacy_system_url: str):
        self.legacy_url = legacy_system_url
        self.mfa_provider = MFAProvider()
        self.session_store = SessionStore()
    
    def handle_login(self, request) -> dict:
        """
        Fluxo:
        1. Recebe username + password
        2. Verifica com sistema legado
        3. Se OK, exige MFA
        4. Se MFA OK, cria sessao no proxy
        5. Proxy injeta headers de autenticacao no legado
        """
        username = request.get("username")
        password = request.get("password")
        
        # Passo 1: Verificar com legado
        legacy_check = self._verify_legacy(username, password)
        if not legacy_check["valid"]:
            return {"success": False, "reason": "invalid_credentials"}
        
        # Passo 2: Iniciar MFA
        mfa_session = self.mfa_provider.initiate(username)
        
        # Passo 3: Armazenar progresso
        self.session_store.store_pending_mfa(
            username=username,
            legacy_token=legacy_check["token"],
            mfa_session_id=mfa_session["id"],
        )
        
        return {
            "success": None,
            "mfa_required": True,
            "mfa_method": mfa_session["method"],
        }
    
    def verify_mfa_and_complete(self, username: str,
                                mfa_code: str) -> dict:
        pending = self.session_store.get_pending_mfa(username)
        
        if not pending:
            return {"success": False, "reason": "no_pending_mfa"}
        
        # Verificar MFA
        mfa_valid = self.mfa_provider.verify(
            pending["mfa_session_id"], mfa_code
        )
        
        if not mfa_valid:
            return {"success": False, "reason": "invalid_mfa"}
        
        # Criar sessao proxy
        proxy_session = self.session_store.create_session(
            username=username,
            legacy_token=pending["legacy_token"],
        )
        
        return {
            "success": True,
            "session_id": proxy_session["id"],
            "proxy_cookie": proxy_session["cookie"],
        }
    
    def proxy_request(self, request, session_id: str) -> dict:
        """Proxificar requisicoes autenticadas para o legado."""
        session = self.session_store.get_session(session_id)
        
        if not session or session["expired"]:
            return {"error": "session_expired"}
        
        # Injetar headers de autenticacao no legado
        headers = {
            "X-Auth-User": session["username"],
            "X-Auth-Token": session["legacy_token"],
            "X-Forwarded-For": request["ip"],
        }
        
        # Forward para legado
        response = requests.request(
            method=request["method"],
            url=f"{self.legacy_url}{request['path']}",
            headers=headers,
            data=request.get("body"),
        )
        
        return {
            "status": response.status_code,
            "body": response.json(),
        }
```

### 14.12.2 Migracao gradual de autenticacao

```
Fase 1 (0-30 dias): Proxy de autenticacao
  - Proxy na frente do legado
  - MFA obrigatorio via proxy
  - Legado continua inalterado

Fase 2 (30-90 dias): Sincronizacao de credenciais
  - Novo identity provider (Keycloak/Auth0)
  - Sincronizacao de credenciais com legado
  - MFA configurado no IdP

Fase 3 (90-180 dias): Migracao de endpoints
  - Endpoints criticos migram para novo IdP
  - Legado mantido para endpoints nao criticos
  - SSO entre novo e legado

Fase 4 (180+ dias): Decomissionamento
  - Legado desligado gradualmente
  - Todos os endpoints no novo IdP
  - Monitoramento de migracao
```

---

## 14.13 Autenticação de Serviço a Serviço

### 14.13.1 Ataques em comunicação inter-service

Em arquiteturas de microsserviços, a autenticação entre serviços é frequentemente negligenciada. Serviços confiam uns nos outros implicitamente, o que cria riscos se um serviço for comprometido.

**mTLS (mutual TLS):**

```python
# Configuracao de mTLS para comunicacao entre servicos
import ssl
import http.server

class MutualTLSServer:
    def __init__(self):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(
            certfile="server.crt",
            keyfile="server.key"
        )
        # Verificar certificado do cliente
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.load_verify_locations("ca.crt")
    
    def start(self, host: str, port: int):
        server = http.server.HTTPServer(
            (host, port),
            RequestHandler
        )
        server.socket = self.context.wrap_socket(
            server.socket, server_side=True
        )
        server.serve_forever()
```

**Service mesh (Istio/Linkerd):**

```yaml
# Istio AuthorizationPolicy - comunicacao entre servicos
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: idap-service-authz
  namespace: idap
spec:
  selector:
    matchLabels:
      app: idap-api
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/idap/sa/idap-web"]
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/v1/*"]
```

### 14.13.2 SPIFFE/SPIRE para identidade de serviço

```python
# SPIFFE workload identity para servicos
# Cada servico recebe uma identidade unica (SPIFFE ID)

class SPIFFEIdentity:
    def __init__(self):
        self.spiffe_id = "spiffe://idap.gov.br/service/idap-api"
        self.svid = self._load_svid()
    
    def _load_svid(self):
        """Carregar SVID (SPIFFE Verifiable Identity Document)."""
        import json
        
        with open("/run/secrets/spiffe/svid.json") as f:
            return json.load(f)
    
    def get_mtls_context(self):
        """Retornar contexto mTLS com SPIFFE ID."""
        return {
            "cert_chain": self.svid["cert_chain"],
            "private_key": self.svid["private_key"],
            "spiffe_id": self.spiffe_id,
        }
    
    def verify_peer(self, peer_spiffe_id: str) -> bool:
        """Verificar se o peer e um servico autorizado."""
        allowed_peers = [
            "spiffe://idap.gov.br/service/idap-web",
            "spiffe://idap.gov.br/service/idap-worker",
            "spiffe://idap.gov.br/service/idap-report",
        ]
        return peer_spiffe_id in allowed_peers
```

---

## 14.14 Autenticação em Ambientes de Alto Risco

### 14.14.1 Sistemas governamentais — requisitos especiais

Sistemas governamentais como o IDAP possuem requisitos de autenticação que vão além de sistemas corporativos:

1. **Non-repudiation**: Cada ação deve ser rastreada a um indivíduo específico (não apenas a uma conta).
2. **Hardware tokens**: Para operações sensíveis, hardware tokens (smart cards, HSM) são necessários.
3. **Multisig**: Operações críticas (como acesso a dados biométricos) requerem aprovação de múltiplos operadores.
4. **Audit trails imutáveis**: Logs de auditoria não podem ser alterados ou deletados.

```python
# Sistema de autenticacao para operacoes criticas do IDAP
# Implementa multisig e non-repudiation

class HighSecurityAuthentication:
    def __init__(self):
        self.hardware_token_provider = HardwareTokenProvider()
        self.multisig_provider = MultisigProvider()
        self.audit_log = ImmutableAuditLog()
    
    def authenticate_critical_operation(self,
                                        operation: str,
                                        context: dict) -> dict:
        """
        Autenticacao para operacoes criticas.
        
        Requer:
        1. Hardware token do operador
        2. MFA adicional
        3. Aprovacao de supervisor
        4. Justificativa detalhada
        """
        user_id = context["user_id"]
        
        # 1. Verificar hardware token
        token_valid = self.hardware_token_provider.verify(
            user_id,
            context.get("token_signature")
        )
        if not token_valid:
            return {"success": False, "reason": "invalid_hardware_token"}
        
        # 2. Verificar MFA adicional
        mfa_valid = self._verify_mfa(user_id, context)
        if not mfa_valid:
            return {"success": False, "reason": "mfa_required"}
        
        # 3. Verificar justificativa
        justification = context.get("justification", "")
        if len(justification) < 50:
            return {
                "success": False,
                "reason": "justification_too_short",
                "message": "Minimo de 50 caracteres na justificativa.",
            }
        
        # 4. Multisig: aprovação de supervisor
        if operation in ["biometric_access", "bulk_export", "data_deletion"]:
            supervisor_approval = self.multisig_provider.request_approval(
                operation=operation,
                requester=user_id,
                context=context,
            )
            
            if not supervisor_approval["approved"]:
                return {
                    "success": False,
                    "reason": "supervisor_approval_required",
                    "approval_id": supervisor_approval["id"],
                }
        
        # 5. Registrar com non-repudiation
        self.audit_log.log_operation(
            user_id=user_id,
            operation=operation,
            context=context,
            justification=justification,
            digital_signature=self._sign_operation(user_id, operation, context),
        )
        
        return {"success": True}
    
    def _sign_operation(self, user_id: str, operation: str,
                        context: dict) -> str:
        """Assinar operacao com chave privada do usuario."""
        import hashlib
        
        operation_data = f"{user_id}:{operation}:{context}:{time.time()}"
        signature = hashlib.sha256(operation_data.encode()).hexdigest()
        
        return signature
```

### 14.14.2 Zero Trust para autenticação

```python
# Implementacao de Zero Trust para autenticacao
# Nao confia em nada, verifica tudo

class ZeroTrustAuthentication:
    def __init__(self):
        self.risk_engine = RiskEngine()
        self.device_trust = DeviceTrustProvider()
        self.network_trust = NetworkTrustProvider()
        self.identity_trust = IdentityTrustProvider()
    
    def evaluate_access(self, request: dict) -> dict:
        """
        Avaliacao Zero Trust completa.
        
        Cada dimensao gera um score de confianca.
        Score final determina nivel de acesso.
        """
        # 1. Confianca na identidade
        identity_score = self.identity_trust.evaluate(
            user_id=request["user_id"],
            authentication_method=request["auth_method"],
            mfa_verified=request.get("mfa_verified", False),
            password_age_days=request.get("password_age", 0),
        )
        
        # 2. Confianca no dispositivo
        device_score = self.device_trust.evaluate(
            device_id=request.get("device_id"),
            device_compliant=request.get("device_compliant", False),
            os_version=request.get("os_version"),
            antivirus_active=request.get("antivirus_active", False),
            disk_encrypted=request.get("disk_encrypted", False),
        )
        
        # 3. Confianca na rede
        network_score = self.network_trust.evaluate(
            ip_address=request["ip"],
            is_corporate_network=request.get("is_corporate", False),
            is_vpn=request.get("is_vpn", False),
            geolocation=request.get("geo"),
            ip_reputation=request.get("ip_reputation", "unknown"),
        )
        
        # 4. Confianca no contexto
        context_score = self.risk_engine.evaluate(
            time_of_day=request.get("hour"),
            day_of_week=request.get("day_of_week"),
            unusual_location=request.get("unusual_location", False),
            concurrent_sessions=request.get("concurrent_sessions", 0),
            recent_password_change=request.get("recent_password_change", False),
        )
        
        # Score composto
        overall_score = (
            identity_score * 0.4 +
            device_score * 0.25 +
            network_score * 0.2 +
            context_score * 0.15
        )
        
        # Determinar nivel de acesso
        if overall_score >= 0.9:
            access_level = "full"
        elif overall_score >= 0.7:
            access_level = "standard"
        elif overall_score >= 0.5:
            access_level = "limited"
        else:
            access_level = "denied"
        
        return {
            "access_level": access_level,
            "overall_score": round(overall_score, 3),
            "scores": {
                "identity": round(identity_score, 3),
                "device": round(device_score, 3),
                "network": round(network_score, 3),
                "context": round(context_score, 3),
            },
            "restrictions": self._get_restrictions(access_level),
        }
    
    def _get_restrictions(self, access_level: str) -> dict:
        restrictions = {
            "full": {
                "max_records": 10000,
                "allowed_actions": ["read", "write", "delete", "export"],
                "session_timeout_minutes": 60,
                "mfa_required": True,
            },
            "standard": {
                "max_records": 1000,
                "allowed_actions": ["read", "write"],
                "session_timeout_minutes": 30,
                "mfa_required": True,
            },
            "limited": {
                "max_records": 100,
                "allowed_actions": ["read"],
                "session_timeout_minutes": 15,
                "mfa_required": True,
            },
            "denied": {
                "max_records": 0,
                "allowed_actions": [],
                "session_timeout_minutes": 0,
                "mfa_required": True,
            },
        }
        return restrictions.get(access_level, restrictions["denied"])
```

---

*No próximo capítulo: Caso Misantropi4 — Análise completa do ataque ao IDAP, incluindo timeline, vetores de ataque, impacto, e lições aprendidas.*
---

*[Capítulo anterior: 13 — Policy Engines](13-policy-engines.md)*
*[Próximo capítulo: 15 — Caso Misantropi4](15-caso-misantropi4.md)*
