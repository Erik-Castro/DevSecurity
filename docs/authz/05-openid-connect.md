# Capítulo 5 — OpenID Connect

## Introdução

OpenID Connect (OIDC) é uma camada de identidade construída sobre o OAuth 2.0. Enquanto o OAuth 2.0 é exclusivamente um protocolo de autorização — dizendo "o que você pode acessar" — o OIDC adiciona autenticação, dizendo "quem você é". Essa distinção é fundamental: OAuth 2.0 por si só não fornece ao Client informações sobre a identidade do Resource Owner. O OIDC resolve isso introduzindo o **ID Token**, um token JWT que carrega informações de identidade do usuário.

O OIDC foi publicado como specification OpenID Foundation em 2014 e desde tornou-se o padrão dominante para autenticação em aplicações web e mobile. Toda vez que você usa "Login com Google", "Login com Microsoft", ou "Login com GitHub", está utilizando OIDC (ou sua variante mais simples, o OAuth 2.0 com endpoints de userinfo).

A relevância do OIDC no contexto de segurança é profunda. O caso Misantropi4 demonstra como a ausência de uma camada de identidade robusta pode ser explorada. Se o IDAP tivesse implementado OIDC com PKCE, MFA, e session management adequado, o credential stuffing teria sido significativamente mais difícil — não apenas porque os tokens expirariam rapidamente, mas porque o fluxo de autenticação teria incluído verificações adicionais de identidade.

Este capítulo cobre OIDC em profundidade: sua relação com OAuth 2.0, a estrutura de ID Tokens, Discovery, logout, session management, PKCE para OIDC, segurança, e implementação completa.

---

## 5.1 OIDC vs OAuth 2.0

### 5.1.1 A confusão fundamental

A confusão mais comum no ecossistema de identidade é tratar OAuth 2.0 como um protocolo de autenticação. NÃO é. O OAuth 2.0 é um protocolo de autorização que delega acesso a recursos. Ele NÃO diz ao Client quem é o usuário — diz apenas que o usuário autorizou o acesso.

Para ilustrar, considere este cenário:

1. Uma aplicação usa OAuth 2.0 para acessar o perfil do usuário no Google
2. O token de acesso é válido e tem scope `profile`
3. O Client acessa o Google e obtém o nome do usuário
4. **Mas**: O Client não tem certeza de que o nome retornado é do usuário correto

Sem OIDC, o Client está "assumindo" que o Resource Server retornou os dados corretos. Com OIDC, o Client recebe um ID Token assinado que garante a identidade do usuário de forma criptograficamente verificável.

### 5.1.2 O que OIDC adiciona ao OAuth 2.0

OIDC introduz os seguintes componentes ao OAuth 2.0:

1. **ID Token**: Um JWT que carrega informações de identidade do usuário, emitido pelo Authorization Server e assinado criptograficamente. O Client pode validar a assinatura e confiar no conteúdo.

2. **UserInfo Endpoint**: Um endpoint REST que retorna informações adicionais do perfil do usuário, acessível usando o access token.

3. **Discovery Document**: Um documento JSON (`.well-known/openid-configuration`) que descreve os endpoints, capabilities, e configurações do provedor OIDC. Isso permite configuração automática do Client.

4. **Scopes padronizados**: `openid`, `profile`, `email`, `address`, `phone` — scopes que o Client pode solicitar para obter informações específicas do usuário.

5. **Session Management**: Mecanismos para gerenciar sessões de login entre o Client e o Authorization Server, incluindo logout cooperativo.

6. **Dynamic Client Registration**: Protocolo para registro automático de novos clients no Authorization Server.

### 5.1.3 Comparação detalhada

| Aspecto | OAuth 2.0 | OpenID Connect |
|---|---|---|
| Propósito | Autorização (o que acessar) | Autenticação (quem é o usuário) + Autorização |
| Token principal | Access Token | ID Token + Access Token |
| Identidade do usuário | Não garantida pelo protocolo | Garantida pelo ID Token (JWT assinado) |
| Scopes | Customizados por provedor | Padronizados (openid, profile, email) |
| Discovery | Não padronizado | `.well-known/openid-configuration` |
| Session Management | Não definido | Especificado (front-channel, back-channel) |
| Logout | Não padronizado | RP-initiated, back-channel, front-channel |
| ID Token claims | Não existem | sub, iss, aud, exp, iat, nonce, etc. |
| Flow obrigatório | Qualquer grant type | Authorization Code Flow (recomendado) |

### 5.1.4 Quando usar cada um

**Use OAuth 2.0 puro quando:**
- O Client precisa acessar dados de terceiros (ex: ler e-mails do Gmail)
- Não há necessidade de saber quem é o usuário
- A autorização é para machine-to-machine (Client Credentials)

**Use OIDC quando:**
- O Client precisa autenticar o usuário (login)
- O Client precisa de informações de identidade (nome, e-mail, etc.)
- É necessário session management entre o Client e o provedor
- É necessário logout cooperativo
- É necessário Discovery e configuração dinâmica

**Na prática**: Se você está implementando login, use OIDC. Se você está implementando acesso a APIs de terceiros, use OAuth 2.0. Na maioria dos casos, OIDC é a escolha correta porque ele é OAuth 2.0 com autenticação adicionada.

---

## 5.2 ID Tokens — Estrutura JWT

O ID Token é o coração do OpenID Connect. Ele é um JSON Web Token (JWT) que carrega informações sobre o evento de autenticação. O ID Token é emitido pelo Authorization Server, assinado com a chave privada do servidor, e pode ser verificado pelo Client sem contato adicional com o servidor.

### 5.2.1 Estrutura de um ID Token

Um ID Token JWT consiste em três partes separadas por pontos: header, payload, e signature.

**Header:**

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "key-2024-01"
}
```

- `alg`: Algoritmo de assinatura (RS256 é o mais comum e recomendado)
- `typ`: Tipo do token (JWT)
- `kid`: Identificador da chave usada para assinar (permite rotação de chaves)

**Payload (Claims):**

```json
{
  "iss": "https://auth.example.com",
  "sub": "user123456",
  "aud": "my-client-app",
  "exp": 1700003600,
  "iat": 1699996400,
  "auth_time": 1699996380,
  "nonce": "n-0S6_WzA2Mj",
  "at_hash": "LDktKdoQak3Pk0cnXCYltz",
  "acr": "urn:mace:incommon:iap:silver",
  "amr": ["pwd", "mfa"],
  "azp": "my-client-app"
}
```

### 5.2.2 Claims obrigatórias

O ID Token DEVE conter as seguintes claims conforme o OIDC Core Specification:

**`iss` (Issuer)**: Identifica o Authorization Server que emitiu o token. O Client DEVE validar que este valor corresponde ao issuer configurado. Exemplo: `https://auth.example.com`.

**`sub` (Subject)**: Identificador único do usuário no Authorization Server. Este é o identificador permanente do usuário — não deve ser alterado. O Client DEVE armazenar este valor para identificar o usuário em requisições futuras.

**`aud` (Audience)**: Identifica o(s) Client(s) para quem o token foi emitido. Deve conter o `client_id` do Client que solicitou o token. Se houver múltiplos audiences, a claim pode ser um array. O Client DEVE validar que seu `client_id` está presente.

**`exp` (Expiration)**: Timestamp Unix indicando quando o token expira. O Client NÃO DEVE confiar em tokens expirados. Recomendação: ID Tokens devem expirar em 5-15 minutos.

**`iat` (Issued At)**: Timestamp Unix indicando quando o token foi emitido. Usado para detectar tokens antigos.

### 5.2.3 Claims opcionais recomendadas

**`auth_time`**: Timestamp de quando a autenticação do usuário ocorreu. Diferente de `iat` (quando o token foi emitido), `auth_time` indica quando o usuário efetivamente digitou suas credenciais. Útil para verificar se a autenticação é recente o suficiente para a operação.

```python
def validate_auth_time(token, max_age=3600):
    auth_time = token.get("auth_time")
    if auth_time is None:
        raise ValueError("auth_time claim missing")

    current_time = time.time()
    if current_time - auth_time > max_age:
        raise ValueError(
            f"Authentication too old: {current_time - auth_time}s > {max_age}s"
        )
```

**`nonce`**: Um valor aleatório fornecido pelo Client no request de autorização e retornado no ID Token. Previne replay de tokens — o Client deve gerar um nonce único por sessão e verificar sua presença no ID Token.

```python
import secrets

def initiate_authentication():
    nonce = secrets.token_urlsafe(32)
    # Armazenar na sessão
    session["oidc_nonce"] = nonce
    return nonce

def validate_id_token(token, expected_nonce):
    actual_nonce = token.get("nonce")
    if actual_nonce != expected_nonce:
        raise ValueError("Nonce mismatch — possible replay attack")
```

**`at_hash` (Access Token Hash)**: Hash do access token que acompanha o ID Token. Permite ao Client verificar que o access token foi emitido pelo mesmo Authorization Server. Calculado como:

```python
import hashlib
import base64

def compute_at_hash(access_token: str, alg: str = "RS256") -> str:
    if alg in ("RS256", "ES256"):
        digest = hashlib.sha256(access_token.encode("ascii")).digest()
    elif alg in ("RS384", "ES384"):
        digest = hashlib.sha384(access_token.encode("ascii")).digest()
    elif alg in ("RS512", "ES512"):
        digest = hashlib.sha512(access_token.encode("ascii")).digest()
    else:
        raise ValueError(f"Unsupported algorithm: {alg}")

    # Usar metade dos bytes do hash
    half = len(digest) // 2
    truncated = digest[:half]

    return base64.urlsafe_b64encode(truncated).rstrip(b"=").decode("ascii")
```

**`acr` (Authentication Context Class Reference)**: Identifica o contexto de autenticação usado. Por exemplo, `urn:mace:incommon:iap:silver` indica autenticação com MFA. O Client pode usar esta claim para verificar se o nível de autenticação é suficiente.

**`amr` (Authentication Methods References)**: Lista dos métodos de autenticação utilizados. Valores comuns:
- `pwd`: Senha
- `otp`: One-time password (TOTP, HOTP)
- `sms`: SMS
- `mfa`: Autenticação multifator
- `bi`: Biometria

**`azp` (Authorized Party)**: O Client que foi autorizado. Diferente de `aud` (que pode conter múltiplos audiences), `azp` identifica especificamente o Client que solicitou o token.

### 5.2.4 Validação completa do ID Token

```python
import jwt
import time
from typing import Optional

class IDTokenValidator:
    def __init__(self, issuer: str, audience: str, jwks_uri: str):
        self.issuer = issuer
        self.audience = audience
        self.jwks_uri = jwks_uri
        self.jwk_client = jwt.PyJWKClient(jwks_uri)

    def validate(
        self,
        id_token: str,
        nonce: Optional[str] = None,
        max_auth_age: Optional[int] = None,
        access_token: Optional[str] = None
    ) -> dict:
        # Decodificar header para obter kid
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        # Obter chave pública
        signing_key = self.jwk_client.get_signing_key(kid)

        # Validar assinatura e claims obrigatórias
        payload = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={
                "require": ["iss", "sub", "aud", "exp", "iat"],
                "verify_exp": True,
                "verify_aud": True,
                "verify_iss": True
            }
        )

        # Validar nonce (se fornecido)
        if nonce is not None:
            token_nonce = payload.get("nonce")
            if token_nonce != nonce:
                raise ValueError(
                    "Nonce mismatch — possible token replay"
                )

        # Validar auth_time (se max_auth_age especificado)
        if max_auth_age is not None:
            auth_time = payload.get("auth_time")
            if auth_time is None:
                raise ValueError(
                    "auth_time claim required when max_age is specified"
                )
            auth_age = time.time() - auth_time
            if auth_age > max_auth_age:
                raise ValueError(
                    f"Authentication too old: {auth_age:.0f}s "
                    f"> {max_auth_age}s"
                )

        # Validar at_hash (se access_token fornecido)
        if access_token is not None:
            expected_at_hash = compute_at_hash(
                access_token,
                unverified_header.get("alg", "RS256")
            )
            actual_at_hash = payload.get("at_hash")
            if actual_at_hash and actual_at_hash != expected_at_hash:
                raise ValueError(
                    "at_hash mismatch — token integrity compromised"
                )

        return payload
```

### 5.2.5 Segurança dos ID Tokens

**NUNCA confie em ID Tokens não validados.** O ID Token é um JWT assinado, mas a assinatura só é verificada se o Client realizar a validação. Um ID Token forjado ou modificado é indistinguível de um legítimo sem verificação de assinatura.

**ID Tokens não devem ser usados para acessar APIs.** O ID Token é destinado ao Client, não ao Resource Server. O access token é que deve ser usado para acessar APIs. O ID Token contém informações sobre a autenticação do usuário, não autorização.

**Armazenamento seguro de ID Tokens.** Se o Client armazena o ID Token para referência futura, deve armazená-lo de forma segura (memória do servidor, não localStorage). O ID Token pode conter informações sensíveis (e-mail, telefone, endereço).

**Validação de audience obrigatória.** Sempre verifique que o `aud` do ID Token corresponde ao seu `client_id`. Isso previne que tokens emitidos para outro Client sejam usados na sua aplicação.

---

## 5.3 UserInfo Endpoint

O UserInfo Endpoint é um endpoint REST protegido que retorna informações adicionais sobre o usuário autenticado. Ele complementa o ID Token, fornecendo dados que podem não estar no token (para manter o token enxuto) ou que podem mudar com o tempo.

### 5.3.1 Requisição ao UserInfo

```
GET /userinfo HTTP/1.1
Host: auth.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

Ou via POST:

```
POST /userinfo HTTP/1.1
Host: auth.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

### 5.3.2 Resposta do UserInfo

```json
{
  "sub": "user123456",
  "name": "João da Silva",
  "given_name": "João",
  "family_name": "da Silva",
  "preferred_username": "joaosilva",
  "email": "joao@example.com",
  "email_verified": true,
  "picture": "https://example.com/photos/joaosilva.jpg",
  "locale": "pt-BR",
  "updated_at": 1699996400,
  "phone_number": "+5511999998888",
  "phone_number_verified": false,
  "address": {
    "formatted": "Rua Exemplo, 123 - São Paulo, SP 01234-567",
    "street_address": "Rua Exemplo, 123",
    "locality": "São Paulo",
    "region": "SP",
    "postal_code": "01234-567",
    "country": "BR"
  }
}
```

### 5.3.3 Claims retornadas pelo UserInfo

As claims retornadas dependem dos scopes solicitados:

| Scope | Claims retornadas |
|---|---|
| `openid` | `sub` (obrigatório via ID Token) |
| `profile` | `name`, `family_name`, `given_name`, `middle_name`, `nickname`, `preferred_username`, `profile`, `picture`, `website`, `gender`, `birthdate`, `zoneinfo`, `locale`, `updated_at` |
| `email` | `email`, `email_verified` |
| `address` | `address` (objeto com formatted, street_address, locality, region, postal_code, country) |
| `phone` | `phone_number`, `phone_number_verified` |

### 5.3.4 Segurança do UserInfo Endpoint

**OUserInfo Endpoint DEVE exigir TLS.** Todas as comunicações devem ser criptografadas.

**O access token deve ser validado.** O UserInfo Endpoint deve verificar o access token antes de retornar dados. Isso inclui validação de assinatura, expiração, e scope.

**Rate limiting é essencial.** O UserInfo Endpoint pode ser abusado para enumeration de usuários. Implementar rate limiting por IP e por token.

**Retornar 401 para tokens inválidos.** Se o access token for inválido, retornar HTTP 401 com `WWW-Authenticate: Bearer`.

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer

app = FastAPI()
security = HTTPBearer()

@app.get("/userinfo")
async def userinfo(credentials = Depends(security)):
    token = credentials.credentials

    # Validar access token
    try:
        payload = validate_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verificar scope
    scopes = payload.get("scope", "").split()
    if "openid" not in scopes:
        raise HTTPException(status_code=403, detail="openid scope required")

    # Buscar dados do usuário
    user = await get_user(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Construir resposta baseada nos scopes
    response = {"sub": user.id}

    if "profile" in scopes:
        response.update({
            "name": user.full_name,
            "given_name": user.first_name,
            "family_name": user.last_name,
            "preferred_username": user.username,
            "picture": user.avatar_url,
            "locale": user.locale,
            "updated_at": int(user.updated_at.timestamp())
        })

    if "email" in scopes:
        response.update({
            "email": user.email,
            "email_verified": user.email_verified
        })

    if "phone" in scopes:
        response.update({
            "phone_number": user.phone,
            "phone_number_verified": user.phone_verified
        })

    if "address" in scopes and user.address:
        response["address"] = {
            "formatted": user.address.formatted,
            "street_address": user.address.street,
            "locality": user.address.city,
            "region": user.address.state,
            "postal_code": user.address.zip_code,
            "country": user.address.country
        }

    return response
```

### 5.3.5 UserInfo vs ID Token: quando usar cada um

| Critério | ID Token | UserInfo Endpoint |
|---|---|---|
| Dados retornados | Informações da autenticação | Informações do perfil do usuário |
| Formato | JWT (assinado, self-contained) | JSON (requer validação adicional) |
| Atualização | Snapshot no momento da emissão | Dados sempre atualizados |
| Armazenamento | Pode ser armazenado pelo Client | Deve ser consultado a cada uso |
| Performance | Sem chamada de rede adicional | Requer chamada de rede |
| Uso recomendado | Identificação do usuário | Dados de perfil detalhados |

Na prática, a maioria das aplicações usa ambos: o ID Token para autenticar e identificar o usuário, e o UserInfo Endpoint para obter dados de perfil completos e atualizados.

---

## 5.4 Discovery Document

O Discovery Document é um ponto crucial do OIDC que permite a configuração automática de Clients. Ele é um JSON publicado em um URL padronizado (`.well-known/openid-configuration`) que descreve todos os endpoints e capabilities do provedor OIDC.

### 5.4.1 Estrutura do Discovery Document

```
GET /.well-known/openid-configuration HTTP/1.1
Host: auth.example.com
```

Resposta:

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "userinfo_endpoint": "https://auth.example.com/userinfo",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "registration_endpoint": "https://auth.example.com/register",
  "scopes_supported": [
    "openid", "profile", "email", "address",
    "phone", "offline_access"
  ],
  "response_types_supported": ["code", "code id_token"],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "client_credentials"
  ],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256", "ES256"],
  "token_endpoint_auth_methods_supported": [
    "client_secret_basic",
    "client_secret_post",
    "private_key_jwt"
  ],
  "claims_supported": [
    "sub", "iss", "aud", "exp", "iat",
    "auth_time", "nonce", "at_hash",
    "acr", "amr", "azp",
    "name", "given_name", "family_name",
    "email", "email_verified",
    "picture", "locale"
  ],
  "code_challenge_methods_supported": ["S256"],
  "revocation_endpoint": "https://auth.example.com/revoke",
  "introspection_endpoint": "https://auth.example.com/introspect",
  "end_session_endpoint": "https://auth.example.com/logout",
  "backchannel_logout_supported": true,
  "backchannel_logout_session_supported": true,
  "frontchannel_logout_supported": true,
  "frontchannel_logout_session_supported": true,
  "request_parameter_supported": true,
  "request_uri_parameter_supported": false,
  "dpop_signing_alg_values_supported": ["ES256"]
}
```

### 5.4.2 Campos obrigatórios

O Discovery Document DEVE conter pelo menos:

- `issuer`: O issuer do provedor OIDC
- `authorization_endpoint`: URL do Authorization Endpoint
- `jwks_uri`: URL do JWKS (JSON Web Key Set) com as chaves públicas
- `response_types_supported`: Lista de response types suportados
- `subject_types_supported`: Lista de subject types suportados
- `id_token_signing_alg_values_supported`: Algoritmos de assinatura suportados

### 5.4.3 JWKS (JSON Web Key Set)

O JWKS é um documento JSON contendo as chaves públicas usadas para validar tokens assinados. É essencial para a verificação de assinatura de ID Tokens e access tokens JWT.

```
GET /.well-known/jwks.json HTTP/1.1
Host: auth.example.com
```

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "key-2024-01",
      "use": "sig",
      "alg": "RS256",
      "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "key-2024-02",
      "use": "sig",
      "alg": "RS256",
      "n": "yK1zNz5Cv8eOj4Gx7DdP2XfL9mB6rA8sT5vY3wQ1kH...",
      "e": "AQAB"
    }
  ]
}
```

### 5.4.4 Uso de Discovery na prática

```python
import httpx
from functools import lru_cache

class OIDCClient:
    def __init__(self, issuer: str):
        self.issuer = issuer
        self._discovery = None

    @property
    def discovery(self) -> dict:
        if self._discovery is None:
            self._discovery = self._fetch_discovery()
        return self._discovery

    def _fetch_discovery(self) -> dict:
        url = f"{self.issuer}/.well-known/openid-configuration"
        response = httpx.get(url, timeout=10)

        if response.status_code != 200:
            raise OIDCDiscoveryError(
                f"Failed to fetch discovery document: {response.status_code}"
            )

        config = response.json()

        # Validar issuer
        if config.get("issuer") != self.issuer:
            raise OIDCDiscoveryError(
                "Issuer mismatch in discovery document"
            )

        return config

    @property
    def authorization_endpoint(self) -> str:
        return self.discovery["authorization_endpoint"]

    @property
    def token_endpoint(self) -> str:
        return self.discovery["token_endpoint"]

    @property
    def userinfo_endpoint(self) -> str:
        return self.discovery["userinfo_endpoint"]

    @property
    def jwks_uri(self) -> str:
        return self.discovery["jwks_uri"]

    @property
    def end_session_endpoint(self) -> str:
        return self.discovery.get("end_session_endpoint")

    @property
    def supports_pkce(self) -> bool:
        methods = self.discovery.get("code_challenge_methods_supported", [])
        return "S256" in methods

    @property
    def supports_logout(self) -> bool:
        return "end_session_endpoint" in self.discovery

    @property
    def supports_backchannel_logout(self) -> bool:
        return self.discovery.get("backchannel_logout_supported", False)

    @property
    def supports_frontchannel_logout(self) -> bool:
        return self.discovery.get("frontchannel_logout_supported", False)

    def get_signing_algorithms(self) -> list:
        return self.discovery.get(
            "id_token_signing_alg_values_supported", []
        )

    def get_auth_methods(self) -> list:
        return self.discovery.get(
            "token_endpoint_auth_methods_supported", []
        )

# Uso
oidc = OIDCClient("https://auth.example.com")
print(f"Auth endpoint: {oidc.authorization_endpoint}")
print(f"PKCE support: {oidc.supports_pkce}")
print(f"Algorithms: {oidc.get_signing_algorithms()}")
```

### 5.4.5 Cache e rotação de JWKS

O JWKS pode mudar quando o Authorization Server rotaciona suas chaves de assinatura. O Client DEVE implementar cache com invalidação:

```python
import time
import httpx
from threading import Lock

class JWKSManager:
    def __init__(self, jwks_uri: str, cache_ttl: int = 3600):
        self.jwks_uri = jwks_uri
        self.cache_ttl = cache_ttl
        self._keys = {}
        self._last_fetch = 0
        self._lock = Lock()

    def get_signing_key(self, kid: str):
        # Verificar cache
        if time.time() - self._last_fetch < self.cache_ttl:
            if kid in self._keys:
                return self._keys[kid]

        # Buscar JWKS atualizado
        self._refresh_keys()

        if kid not in self._keys:
            # Chave não encontrada — pode ser nova
            # Tentar buscar novamente
            self._refresh_keys(force=True)

        if kid not in self._keys:
            raise KeyError(f"Key not found: {kid}")

        return self._keys[kid]

    def _refresh_keys(self, force: bool = False):
        with self._lock:
            if not force and time.time() - self._last_fetch < self.cache_ttl:
                return

            response = httpx.get(self.jwks_uri, timeout=10)
            if response.status_code == 200:
                jwks = response.json()
                self._keys = {}
                for key_data in jwks.get("keys", []):
                    kid = key_data.get("kid")
                    if kid:
                        self._keys[kid] = self._parse_key(key_data)
                self._last_fetch = time.time()

    def _parse_key(self, key_data: dict):
        # Parse RSA key from JWK format
        from jwt.algorithms import RSAAlgorithm
        return RSAAlgorithm.from_jwk(key_data)
```

---

## 5.5 Dynamic Client Registration

Dynamic Client Registration (OIDC Dynamic Client Registration, RFC 7591) permite que Clients se registrem automaticamente no Authorization Server sem intervenção manual. Isso é particularmente útil para desenvolvimento, testing, e para provedores OIDC públicos.

### 5.5.1 Requisição de Registro

```
POST /register HTTP/1.1
Host: auth.example.com
Content-Type: application/json

{
  "client_name": "My Application",
  "redirect_uris": [
    "https://myapp.example.com/callback",
    "https://myapp.example.com/silent-callback"
  ],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "scope": "openid profile email",
  "token_endpoint_auth_method": "client_secret_basic",
  "contacts": ["admin@example.com"],
  "logo_uri": "https://myapp.example.com/logo.png",
  "client_uri": "https://myapp.example.com",
  "policy_uri": "https://myapp.example.com/privacy",
  "tos_uri": "https://myapp.example.com/terms",
  "jwks_uri": "https://myapp.example.com/.well-known/jwks.json"
}
```

### 5.5.2 Resposta de Registro

```json
{
  "client_id": "dynamic-client-abc123",
  "client_secret": "super-secret-value-xyz789",
  "client_id_issued_at": 1699996400,
  "client_secret_expires_at": 1702588400,
  "redirect_uris": [
    "https://myapp.example.com/callback",
    "https://myapp.example.com/silent-callback"
  ],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "scope": "openid profile email",
  "token_endpoint_auth_method": "client_secret_basic",
  "client_name": "My Application",
  "registration_access_token": "reg-token-abc123",
  "registration_client_uri": "https://auth.example.com/register"
}
```

### 5.5.3 Segurança do Dynamic Client Registration

O Dynamic Client Registration pode ser perigoso se não for protegido adequadamente:

**Registro aberto**: Se qualquer um pode registrar clients, um atacante pode criar clients maliciosos com redirect URIs de sua escolha, potencialmente para phishing ou interceptação de tokens.

**Mitigações:**
1. **Restringir domínios permitidos**: Apenas aceitar redirect URIs em domínios pré-aprovados
2. **Rate limiting**: Limitar a taxa de registros por IP
3. **Aprovação manual**: Para produção, usar registro com aprovação manual
4. **Validação de redirect URIs**: Verificar que URIs são HTTPS, não usam IPs, e apontam para domínios controlados
5. **Monitoring**: Alertar sobre registros incomuns ou em massa

```python
ALLOWED_DOMAINS = ["example.com", "example.org"]

def validate_registration_request(request: dict) -> bool:
    # Validar redirect URIs
    for uri in request.get("redirect_uris", []):
        parsed = urlparse(uri)

        # Exigir HTTPS
        if parsed.scheme != "https":
            raise RegistrationError(
                "Only HTTPS redirect URIs are allowed"
            )

        # Verificar domínio permitido
        domain = parsed.hostname
        if not any(domain.endswith(d) for d in ALLOWED_DOMAINS):
            raise RegistrationError(
                f"Domain {domain} not in allowed list"
            )

        # NÃO aceitar localhost ou IPs (exceto em dev)
        if domain in ("localhost", "127.0.0.1", "::1"):
            raise RegistrationError(
                "Localhost redirect URIs not allowed"
            )

    return True
```

---

## 5.6 Logout Flows

O logout em OIDC é mais complexo que em sistemas tradicionais porque existem múltiplas sessões: a sessão no Client, a sessão no Authorization Server, e potencialmente sessões em outros Clients que usam o mesmo Authorization Server.

### 5.6.1 RP-Initiated Logout

O RP (Relying Party, ou Client) inicia o logout redirecionando o usuário para o `end_session_endpoint` do Authorization Server.

**Parâmetros do logout:**

```
GET /logout?
  id_token_hint=eyJhbGciOiJSUzI1NiIs...&
  post_logout_redirect_uri=https://myapp.example.com/logged-out&
  state=logout-state-123
HTTP/1.1
Host: auth.example.com
```

Parâmetros:
- `id_token_hint`: O ID Token emitido durante o login (ajuda o Authorization Server a identificar a sessão)
- `post_logout_redirect_uri`: URI para onde redirecionar após o logout (deve corresponder a uma URI registrada)
- `state`: Valor opaco para proteção CSRF (opcional mas recomendado)

**Fluxo de logout:**

1. O Client redireciona o usuário para `end_session_endpoint` com os parâmetros
2. O Authorization Server invalida a sessão do usuário
3. O Authorization Server opcionalmente exibe uma confirmação de logout
4. O Authorization Server redireciona o usuário de volta para `post_logout_redirect_uri`

```python
@app.get("/logout")
def initiate_logout():
    id_token_hint = session.get("id_token")
    session.clear()

    if not id_token_hint:
        return redirect("/")

    logout_url = (
        f"{AUTH_SERVER}/logout"
        f"?id_token_hint={id_token_hint}"
        f"&post_logout_redirect_uri={REDIRECT_URI}/logged-out"
        f"&state={secrets.token_urlsafe(16)}"
    )

    return redirect(logout_url)

@app.get("/logged-out")
def logged_out():
    state = request.args.get("state")
    expected_state = session.get("logout_state")

    # Verificar state (se implementado)
    # O estado pode ter sido perdido se o session foi limpo

    return "Você saiu com sucesso."
```

### 5.6.2 Back-Channel Logout

O Back-Channel Logout é o mecanismo mais confiável para logout cooperativo. O Authorization Server envia um request HTTP direto ao Client (sem passar pelo browser do usuário) para notificar sobre o logout.

**Mecanismo:**

1. O usuário faz logout em qualquer Client (ou no Authorization Server diretamente)
2. O Authorization Server envia um POST request para cada Client registrado com back-channel logout
3. O request contém um `logout_token` (JWT assinado) com informações sobre o usuário
4. O Client valida o logout_token e invalida a sessão local

**Logout Token:**

```json
{
  "iss": "https://auth.example.com",
  "sub": "user123456",
  "aud": "my-client-app",
  "exp": 1700000000,
  "iat": 1699996400,
  "jti": "unique-logout-id-123",
  "events": {
    "http://schemas.openid.net/event/backchannel-logout": {}
  },
  "sid": "session-id-from-id-token"
}
```

**Implementação do Back-Channel Logout:**

```python
@app.post("/backchannel-logout")
async def backchannel_logout(request: Request):
    form_data = await request.form()
    logout_token = form_data.get("logout_token")

    if not logout_token:
        raise HTTPException(status_code=400, detail="Missing logout_token")

    try:
        # Validar logout_token
        payload = validate_logout_token(logout_token)

        # Verificar claims obrigatórias
        if "http://schemas.openid.net/event/backchannel-logout" not in payload.get("events", {}):
            raise ValueError("Invalid events claim")

        # Invalidar sessão do usuário
        user_id = payload["sub"]
        session_id = payload.get("sid")

        if session_id:
            # Invalidar sessão específica
            await invalidate_session(user_id, session_id)
        else:
            # Invalidar todas as sessões do usuário
            await invalidate_all_sessions(user_id)

        return Response(status_code=200)

    except Exception as e:
        # Retornar 200 mesmo em erro (conforme spec)
        # para evitar leaking de informação
        return Response(status_code=200)

def validate_logout_token(token: str) -> dict:
    # Validar assinatura, issuer, audience
    payload = jwt.decode(
        token,
        get_signing_key(),
        algorithms=["RS256"],
        audience="my-client-app",
        issuer="https://auth.example.com"
    )

    # Verificar expiração
    if payload.get("exp", 0) < time.time():
        raise ValueError("Logout token expired")

    # Verificar events claim
    events = payload.get("events", {})
    if "http://schemas.openid.net/event/backchannel-logout" not in events:
        raise ValueError("Missing backchannel-logout event")

    return payload
```

### 5.6.3 Front-Channel Logout

O Front-Channel Logout é uma abordagem baseada em browser que usa iframes para notificar Client sobre logout. É menos confiável que o Back-Channel mas não requer conectividade direta do Authorization Server ao Client.

**Mecanismo:**

1. O Authorization Server renderiza uma página com iframes para cada Client que suporta front-channel logout
2. Cada iframe carrega um URL de logout específico do Client
3. O Client detecta o iframe e invalida a sessão

```html
<!-- Página de logout do Authorization Server -->
<html>
<body>
  <h1>Logout em andamento...</h1>

  <!-- Front-channel logout para cada Client -->
  <iframe src="https://client1.example.com/frontchannel-logout?iss=https://auth.example.com&sid=abc123"
          style="display:none"></iframe>
  <iframe src="https://client2.example.com/frontchannel-logout?iss=https://auth.example.com&sid=abc123"
          style="display:none"></iframe>

  <script>
    // Redirecionar após todos os iframes carregarem
    setTimeout(function() {
      window.location.href = '/logout-complete';
    }, 2000);
  </script>
</body>
</html>
```

**Implementação no Client:**

```python
@app.get("/frontchannel-logout")
def frontchannel_logout():
    iss = request.args.get("iss")
    sid = request.args.get("sid")

    # Validar issuer
    if iss != AUTH_SERVER:
        return Response(status_code=400)

    # Invalidar sessão local
    if sid and session.get("sid") == sid:
        session.clear()

    # Retornar HTML vazio (o iframe vai carregar isto)
    return Response(
        content="<html><body></body></html>",
        media_type="text/html"
    )
```

### 5.6.4 Comparação dos tipos de logout

| Característica | RP-Initiated | Back-Channel | Front-Channel |
|---|---|---|---|
| Iniciado por | Client | Authorization Server | Authorization Server |
| Conectividade | Via browser (redirect) | Direta (server-to-server) | Via browser (iframe) |
| Confiabilidade | Alta (usuário presente) | Alta (comunicação direta) | Média (depende de browser) |
| Requer browser | Sim | Não | Sim |
| Latência | Baixa | Baixa | Média |
| Caso de uso | Logout do Client atual | Logout cooperativo cross-client | Compatibilidade com browsers antigos |
| Suporte a sessão específica | Sim (sid) | Sim (sid) | Sim (sid) |

---

## 5.7 Session Management

O OIDC Session Management define como Client e Authorization Server coordenam sessões de login. Isso é crucial em cenários multi-Client onde um usuário pode estar logado em múltiplas aplicações usando o mesmo Authorization Server.

### 5.7.1 Conceito de Session

No OIDC, existem dois tipos de sessão:

1. **Session do Authorization Server**: A sessão do usuário no Authorization Server. Quando o usuário faz login, uma sessão é criada. Enquanto esta sessão estiver ativa, o usuário não precisa autenticar novamente para autorizar outros Clients.

2. **Session do Client (RP Session)**: A sessão do usuário no Client. Começa quando o Client recebe um ID Token válido e termina quando o usuário faz logout ou a sessão expira.

### 5.7.2 Session State

O OIDC inclui uma claim `sid` (Session ID) no ID Token que identifica a sessão no Authorization Server. Esta claim permite que Client associe suas sessões locais à sessão no Authorization Server.

```python
def process_id_token(id_token_payload: dict):
    # Armazenar sid para uso em logout
    session["sid"] = id_token_payload.get("sid")
    session["sub"] = id_token_payload.get("sub")
    session["iss"] = id_token_payload.get("iss")

    # Criar sessão local
    create_user_session(
        user_id=id_token_payload["sub"],
        session_id=session["sid"],
        issuer=session["iss"]
    )
```

### 5.7.3 Check Session Endpoint

O OIDC define um mecanismo de "check_session" que permite ao Client verificar se sua sessão no Authorization Server ainda está ativa. Existem duas abordagens:

**Check Session via iframe (Front-Channel):**

O Client inclui um iframe invisível que carrega uma página do Authorization Server. Esta página pode acessar um cookie de sessão e retornar o status.

```html
<!-- Check Session Iframe -->
<iframe id="op-check-session"
        src="https://auth.example.com/check_session"
        style="display:none"
        width="0"
        height="0">
</iframe>

<script>
  // Enviar mensagem para o iframe verificar a sessão
  function checkSession() {
    const iframe = document.getElementById('op-check-session');
    const message = JSON.stringify({
      iss: 'https://auth.example.com',
      client_id: 'my-client-app',
      session_state: currentSessionState
    });

    iframe.contentWindow.postMessage(message, 'https://auth.example.com');
  }

  // Receber resposta do iframe
  window.addEventListener('message', function(event) {
    if (event.origin !== 'https://auth.example.com') return;

    const sessionState = event.data;
    if (sessionState === 'changed') {
      // Sessão mudou no Authorization Server — fazer re-login
      window.location.href = '/login';
    }
  });

  // Verificar sessão a cada 5 segundos
  setInterval(checkSession, 5000);
</script>
```

**Check Session via API (Back-Channel):**

O Client faz uma chamada direta ao Authorization Server para verificar o status da sessão.

```python
async def check_session(sid: str) -> bool:
    """Verificar se a sessão ainda está ativa no Authorization Server."""
    response = await httpx.AsyncClient().get(
        f"{AUTH_SERVER}/session/check",
        params={"sid": sid},
        headers={
            "Authorization": f"Bearer {client_access_token}"
        }
    )

    if response.status_code == 200:
        result = response.json()
        return result.get("active", False)

    return False

async def session_monitor():
    """Monitorar sessão periodicamente."""
    while True:
        sid = session.get("sid")
        if not sid:
            break

        is_active = await check_session(sid)
        if not is_active:
            # Sessão expirada no Authorization Server
            session.clear()
            redirect_to_login()
            break

        await asyncio.sleep(300)  # Verificar a cada 5 minutos
```

### 5.7.4 Gerenciamento de sessão cross-domain

Em cenários onde múltiplos Client rodam em domínios diferentes, o gerenciamento de sessão se torna mais complexo. Cada Client mantém sua própria sessão, e a coordenação ocorre via Authorization Server.

```python
class MultiClientSessionManager:
    def __init__(self, auth_server: str):
        self.auth_server = auth_server
        self.clients = {}  # client_id -> session_info

    async def register_client(
        self, client_id: str, session_id: str, user_id: str
    ):
        """Registrar sessão de um Client."""
        self.clients[client_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }

    async def check_all_sessions(self, user_id: str) -> dict:
        """Verificar status de todas as sessões do usuário."""
        results = {}
        for client_id, info in self.clients.items():
            if info["user_id"] == user_id:
                is_active = await self._check_session(
                    client_id, info["session_id"]
                )
                results[client_id] = {
                    "active": is_active,
                    "created_at": info["created_at"].isoformat()
                }
        return results

    async def logout_all(self, user_id: str):
        """Logout de todas as sessões do usuário."""
        for client_id, info in self.clients.items():
            if info["user_id"] == user_id:
                await self._notify_logout(client_id, info["session_id"])
                del self.clients[client_id]
```

---

## 5.8 Hybrid Flow

O Hybrid Flow é um dos três fluxos de autenticação definidos pelo OIDC (junto com Authorization Code Flow e Implicit Flow). Ele combina elementos do Authorization Code e do Implicit Flow, permitindo que o ID Token seja retornado diretamente no authorization endpoint enquanto o access token é obtido via token endpoint.

### 5.8.1 Response Types no Hybrid Flow

O Hybrid Flow é ativado usando `response_type` combinado:

```
response_type=code id_token
response_type=code token
response_type=code id_token token
```

O parâmetro `response_type` deve conter `code` mais um ou ambos: `id_token` e `token`.

### 5.8.2 Fluxo code id_token

Este é o Hybrid Flow mais comum e recomendado:

```
GET /authorize?
  response_type=code id_token&
  client_id=CLIENT_ID&
  redirect_uri=https://myapp.example.com/callback&
  scope=openid profile&
  state=abc123&
  nonce=xyz789
```

Resposta (fragmento da URL):

```
https://myapp.example.com/callback#
  code=SplxlOBeZQQYbYS6WxSbIA&
  id_token=eyJhbGciOiJSUzI1NiIs...&
  state=abc123
```

O ID Token é retornado no fragmento (#), acessível apenas pelo JavaScript do Client. O código de autorização também está no fragmento e deve ser processado server-side.

### 5.8.3 Processamento do Hybrid Flow

```python
@app.get("/callback")
def hybrid_callback():
    # Extrair parâmetros do fragmento
    # (em SPA, processado via JavaScript antes de chegar ao servidor)

    code = request.args.get("code")
    id_token_raw = request.args.get("id_token")
    state = request.args.get("state")

    # Validar state
    if state != session.get("oauth_state"):
        return "State mismatch", 403

    # Validar ID Token imediatamente
    id_token_payload = validate_id_token(id_token_raw)

    # Verificar nonce
    if id_token_payload.get("nonce") != session.get("oidc_nonce"):
        return "Nonce mismatch", 403

    # Verificar que o ID Token contém o code hash (c_hash)
    expected_hash = compute_code_hash(code, id_token_payload.get("c_hash"))
    if not verify_code_hash(code, id_token_payload.get("c_hash")):
        return "Invalid code hash", 403

    # Agora trocar o código por tokens via token endpoint
    token_response = requests.post(
        f"{AUTH_SERVER}/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code_verifier": session.get("pkce_verifier")
        }
    )

    tokens = token_response.json()

    # Comparar ID Token do authorization endpoint com o do token endpoint
    # (devem ter o mesmo sub, aud, iss)

    return process_login(tokens)
```

### 5.8.4 Hybrid Flow vs Authorization Code Flow

| Critério | Authorization Code | Hybrid (code id_token) |
|---|---|---|
| ID Token | Via token endpoint (server-side) | Via authorization endpoint (fragment) |
| Access Token | Via token endpoint | Via token endpoint |
| Code troca | Obrigatória | Obrigatória |
| Segurança | Mais segura (tudo server-side) | Ligeiramente menos segura |
| Caso de uso | Padrão para todas as aplicações | Quando é necessário validar identidade imediatamente |
| PKCE | Recomendado | Recomendado |

**Recomendação**: Use Authorization Code Flow para a maioria dos casos. Hybrid Flow é útil quando o Client precisa de verificação imediata da identidade do usuário (por exemplo, para exibir informações de perfil no browser antes do processamento server-side).

---

## 5.9 PKCE para OIDC

PKCE (Proof Key for Code Exchange) é especialmente importante no contexto do OIDC porque o fluxo de autenticação é mais sensível que o fluxo de autorização puro — um token comprometido revela identidade, não apenas acesso a dados.

### 5.9.1 Por que PKCE é essencial para OIDC

1. **Prevenção de authorization code injection**: PKCE impede que um atacante injete um código de autorização roubado em uma sessão legítima. No contexto do OIDC, isso é especialmente perigoso porque o atacante poderia assumir a identidade do usuário.

2. **Proteção de SPAs**: Single Page Applications não conseguem armazenar secrets, tornando-as particularmente vulneráveis a interceptação de códigos. PKCE protege mesmo sem client_secret.

3. **Conformidade com boas práticas**: O OIDC FAPI (Financial-grade API) Profile requer PKCE para todos os clients, independentemente do tipo.

### 5.9.2 Implementação completa

```python
class OIDCPKCEFlow:
    def __init__(self, issuer: str, client_id: str, redirect_uri: str):
        self.issuer = issuer
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.discovery = self._load_discovery()

    def _load_discovery(self) -> dict:
        response = httpx.get(
            f"{self.issuer}/.well-known/openid-configuration"
        )
        return response.json()

    def create_authorization_url(
        self, scope: str = "openid profile email"
    ) -> tuple[str, str, str]:
        """Retorna (auth_url, state, nonce)."""
        # Gerar PKCE
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        # Gerar state e nonce
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        # Armazenar valores para verificação posterior
        session["pkce_code_verifier"] = code_verifier
        session["oauth_state"] = state
        session["oidc_nonce"] = nonce

        # Construir URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = (
            f"{self.discovery['authorization_endpoint']}"
            f"?{requests.compat.urlencode(params)}"
        )

        return auth_url, state, nonce

    def exchange_code(self, code: str, state: str) -> dict:
        """Trocar código por tokens, validando tudo."""
        # Validar state
        expected_state = session.get("oauth_state")
        if state != expected_state:
            raise OIDCError("State mismatch — possible CSRF")

        # Recuperar PKCE verifier
        code_verifier = session.get("pkce_code_verifier")
        if not code_verifier:
            raise OIDCError("PKCE verifier not found in session")

        # Trocar código
        response = httpx.post(
            self.discovery["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "code_verifier": code_verifier
            }
        )

        if response.status_code != 200:
            raise OIDCError(
                f"Token exchange failed: {response.text}"
            )

        tokens = response.json()

        # Validar ID Token
        id_token_payload = validate_id_token(
            tokens["id_token"],
            nonce=session.get("oidc_nonce"),
            access_token=tokens.get("access_token")
        )

        # Limpar dados temporários
        session.pop("pkce_code_verifier", None)
        session.pop("oauth_state", None)
        session.pop("oidc_nonce", None)

        return {
            "access_token": tokens["access_token"],
            "id_token": tokens["id_token"],
            "id_token_claims": id_token_payload,
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in")
        }
```

---

## 5.10 Considerações de Segurança

### 5.10.1 Ataques e Mitigações

**Authorization Code Injection:**
- Mitigação: PKCE obrigatório
- PKCE vincula o código ao Client que o solicitou

**Token Substitution:**
- Mitigação: Validação de audience no ID Token
- Verificar `aud` contém o `client_id`

**Token Leakage via Referer:**
- Mitigação: `Referrer-Policy: no-referrer` no callback
- Nunca incluir tokens em URLs clicáveis

**OpenID Provider Impersonation:**
- Mitigação: Validar issuer contra discovery document
- Nunca confiar em tokens de issuer não conhecido

**Mix-Up Attack:**
- Mitigação: Verificar `iss` no ID Token e `iss` no Authorization Server
- Em multi-issuer, usar `state` para associar requests a responses

**Session Fixation:**
- Mitigação: Gerar `nonce` único por sessão
- Verificar `nonce` no ID Token

### 5.10.2 Checklist de Segurança

```
[x] PKCE obrigatório para todos os clients
[x] Authorization Code Flow como padrão (sem Implicit Flow)
[x] Validação de ID Token (assinatura, issuer, audience, expiry)
[x] Nonce verificado no ID Token
[x] State verificado no callback
[x] at_hash verificado quando access token está disponível
[x] Redirect URIs validadas (comparação exata)
[x] TLS em todas as comunicações
[x] Refresh tokens com rotation
[x] Logout cooperativo implementado
[x] Session management implementado
[x] Rate limiting em todos os endpoints
[x] Auditoria de autenticação e autorização
[x] MFA suportado e opcionalmente obrigatório
```

### 5.10.3 OIDC FAPI (Financial-grade API)

O OIDC FAPI é um profile de segurança do OIDC projetado para APIs de alta segurança (banca, finanças). Ele impõe requisitos mais rigorosos que o OIDC padrão:

- PKCE obrigatório
- Token binding (DPoP ou MTLS)
- Filtro de request (request signing)
- Sender-constrained tokens
- Token introspection obrigatória
- Jarm (JWT Secured Authorization Response Mode) recomendado

```python
# Configuração de OIDC FAPI
FAPI_CONFIG = {
    "require_pkce": True,
    "require_pkce_s256": True,
    "require_sender_constrained_tokens": True,
    "require_signed_request": True,
    "require_token_binding": True,
    "allow_implicit_flow": False,
    "allow_hybrid_flow": False,
    "require_nonce": True,
    "max_token_lifetime": 300,  # 5 minutos
    "require_token_introspection": True,
    "require_jarm": True
}
```

---

## 5.11 Integração com OAuth 2.0

### 5.11.1 OIDC como camada sobre OAuth 2.0

OIDC é compatível com OAuth 2.0 porque é uma camada de identidade construída sobre ele. Qualquer provedor OIDC é simultaneamente um Authorization Server OAuth 2.0. As principais integrações são:

**OIDCDiscovery para OAuth 2.0**: O Discovery Document fornece informações sobre endpoints OAuth 2.0 além dos OIDC.

**Token Exchange**: Um access token OIDC pode ser trocado por tokens de serviços downstream usando OAuth 2.0 Token Exchange (RFC 8693).

**Token Introspection**: O Resource Server pode verificar tokens OIDC usando o Introspection Endpoint OAuth 2.0.

### 5.11.2 Multi-Protocol Support

Muitos sistemas suportam OIDC e OAuth 2.0 simultaneamente:

```python
class MultiProtocolAuthServer:
    def __init__(self):
        self.oidc_provider = OIDCProvider()
        self.oauth2_provider = OAuth2Provider()

    async def handle_authorize(self, request):
        scope = request.get("scope", "")

        # OIDC request (contém openid scope)
        if "openid" in scope.split():
            return await self.oidc_provider.handle_authorize(request)

        # OAuth 2.0 request (sem openid scope)
        return await self.oauth2_provider.handle_authorize(request)

    async def handle_token(self, request):
        grant_type = request.get("grant_type")

        # Client Credentials é sempre OAuth 2.0
        if grant_type == "client_credentials":
            return await self.oauth2_provider.handle_token(request)

        # Authorization Code pode ser OIDC ou OAuth 2.0
        if grant_type == "authorization_code":
            code_data = await self._get_code_data(request.get("code"))
            if code_data and "openid" in code_data.get("scope", "").split():
                return await self.oidc_provider.handle_token(request)
            return await self.oauth2_provider.handle_token(request)

        # Refresh token — verificar o que foi emitido originalmente
        if grant_type == "refresh_token":
            refresh_data = await self._get_refresh_data(
                request.get("refresh_token")
            )
            if refresh_data and "openid" in refresh_data.get("scope", ""):
                return await self.oidc_provider.handle_token(request)
            return await self.oauth2_provider.handle_token(request)

        raise HTTPException(400, "Unsupported grant type")
```

---

## 5.12 Exemplos de Implementação

### 5.12.1 OIDC Client com Python (Authlib)

```python
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import secrets

app = FastAPI()

oauth = OAuth()
oauth.register(
    name='oidc_provider',
    client_id='my-client-id',
    client_secret='my-client-secret',
    server_metadata_url='https://auth.example.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_basic'
    }
)

@app.get('/login')
async def login(request: Request):
    # Gerar state e nonce
    state = secrets.token_urlsafe(16)
    request.session['oauth_state'] = state

    # Redirecionar para autorização
    redirect_uri = request.url_for('callback')
    return await oauth.oidc_provider.authorize_redirect(
        request,
        redirect_uri,
        state=state
    )

@app.get('/callback')
async def callback(request: Request):
    # Validar state
    state = request.query_params.get('state')
    if state != request.session.get('oauth_state'):
        return {'error': 'State mismatch'}, 403

    # Trocar código por tokens
    token = await oauth.oidc_provider.authorize_access_token(request)

    # Obter informações do usuário
    userinfo = await oauth.oidc_provider.userinfo(
        token=token['access_token']
    )

    # Armazenar na sessão
    request.session['user'] = dict(userinfo)
    request.session['id_token'] = token.get('id_token')

    return RedirectResponse(url='/')

@app.get('/profile')
async def profile(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login')
    return user

@app.get('/logout')
async def logout(request: Request):
    id_token = request.session.get('id_token')
    request.session.clear()

    if id_token:
        # RP-Initiated Logout
        end_session_url = oauth.oidc_provider.server_metadata.get(
            'end_session_endpoint'
        )
        logout_url = (
            f"{end_session_url}"
            f"?id_token_hint={id_token}"
            f"&post_logout_redirect_uri={request.url_for('logged_out')}"
        )
        return RedirectResponse(url=logout_url)

    return RedirectResponse(url='/')

@app.get('/logged-out')
async def logged_out():
    return {'message': 'Você saiu com sucesso'}
```

### 5.12.2 Authorization Server OIDC com Node.js (oidc-provider)

```javascript
const { Provider } = require('oidc-provider');
const express = require('express');

const configuration = {
  claims: {
    openid: ['sub'],
    profile: [
      'name', 'family_name', 'given_name',
      'preferred_username', 'picture', 'locale'
    ],
    email: ['email', 'email_verified'],
    phone: ['phone_number', 'phone_number_verified']
  },
  scopes: [
    'openid', 'profile', 'email',
    'phone', 'address', 'offline_access'
  ],
  features: {
    devInteractions: { enabled: false },
    resourceIndicators: {
      enabled: true,
      defaultResource: () => 'urn:my-api',
      getResourceServerInfo: () => ({
        scope: 'openid profile email',
        audience: 'urn:my-api',
        accessTokenTTL: 60 * 60,
        accessTokenFormat: 'jwt'
      })
    },
    revocation: { enabled: true },
    introspection: { enabled: true },
    backchannelLogout: {
      enabled: true,
      logoutSource: async (ctx, form) => {
        // Customizar logout page
        ctx.body = `
          <html>
          <body>
            <h1>Logout em andamento...</h1>
            ${form}
            <script>document.forms[0].submit()</script>
          </body>
          </html>
        `;
      }
    }
  },
  findAccount: async (ctx, id) => {
    const user = await db.users.findById(id);
    if (!user) return undefined;
    return {
      accountId: id,
      async claims(use, scope) {
        const claims = { sub: id };
        if (scope.includes('profile')) {
          claims.name = user.name;
          claims.given_name = user.firstName;
          claims.family_name = user.lastName;
          claims.preferred_username = user.username;
          claims.picture = user.avatarUrl;
          claims.locale = user.locale;
        }
        if (scope.includes('email')) {
          claims.email = user.email;
          claims.email_verified = user.emailVerified;
        }
        return claims;
      }
    };
  },
  clients: [
    {
      client_id: 'my-spa-client',
      client_secret: undefined, // SPA = client público
      redirect_uris: ['https://myapp.example.com/callback'],
      grant_types: ['authorization_code', 'refresh_token'],
      response_types: ['code'],
      scope: 'openid profile email',
      token_endpoint_auth_method: 'none'
    },
    {
      client_id: 'my-server-client',
      client_secret: 'server-secret-123',
      redirect_uris: ['https://server-app.example.com/callback'],
      grant_types: ['authorization_code', 'refresh_token', 'client_credentials'],
      response_types: ['code'],
      scope: 'openid profile email',
      token_endpoint_auth_method: 'client_secret_basic'
    }
  ]
};

const app = express();
const oidc = new Provider('https://auth.example.com', configuration);

app.use(oidc.app);

app.get('/.well-known/openid-configuration', (req, res) => {
  // O oidc-provider gera automaticamente
  oidc.app(req, res);
});

app.listen(3000, () => {
  console.log('OIDC Provider running on port 3000');
});
```

### 5.12.3 Validador de ID Token em Rust

```rust
use jwt::{decode, decode_header, Algorithm, Validation, DecodingKey};
use reqwest;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Jwk {
    kty: String,
    kid: String,
    use_: Option<String>,
    alg: String,
    n: Option<String>,
    e: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Jwks {
    keys: Vec<Jwk>,
}

#[derive(Debug)]
struct OidcValidator {
    issuer: String,
    audience: String,
    jwks_uri: String,
    jwks_cache: Arc<RwLock<Option<(Jwks, std::time::Instant)>>>,
}

impl OidcValidator {
    fn new(issuer: &str, audience: &str, jwks_uri: &str) -> Self {
        Self {
            issuer: issuer.to_string(),
            audience: audience.to_string(),
            jwks_uri: jwks_uri.to_string(),
            jwks_cache: Arc::new(RwLock::new(None)),
        }
    }

    async fn validate(&self, token: &str) -> Result<serde_json::Value, String> {
        // Decodificar header sem validar
        let header = decode_header(token)
            .map_err(|e| format!("Invalid header: {}", e))?;

        let kid = header.kid
            .ok_or("Missing kid in token header")?;

        // Obter chave pública
        let decoding_key = self.get_decoding_key(&kid).await?;

        // Configurar validação
        let mut validation = Validation::new(
            Self::algorithm_from_str(header.alg.as_ref())
        );
        validation.set_issuer(&[&self.issuer]);
        validation.set_audience(&[&self.audience]);
        validation.validate_exp = true;
        validation.validate_nbf = true;

        // Decodificar e validar
        let token_data = decode::<serde_json::Value>(
            token,
            &decoding_key,
            &validation
        )
        .map_err(|e| format!("Token validation failed: {}", e))?;

        Ok(token_data.claims)
    }

    async fn get_decoding_key(&self, kid: &str) -> Result<DecodingKey, String> {
        // Verificar cache
        {
            let cache = self.jwks_cache.read().await;
            if let Some((jwks, age)) = cache.as_ref() {
                if age.elapsed() < std::time::Duration::from_secs(3600) {
                    if let Some(key) = jwks.keys.iter().find(|k| k.kid == kid) {
                        return Self::jwk_to_decoding_key(key);
                    }
                }
            }
        }

        // Buscar JWKS
        let jwks = self.fetch_jwks().await?;

        // Salvar no cache
        {
            let mut cache = self.jwks_cache.write().await;
            *cache = Some((jwks.clone(), std::time::Instant::now()));
        }

        // Buscar chave
        let key = jwks.keys.iter()
            .find(|k| k.kid == kid)
            .ok_or_else(|| format!("Key not found: {}", kid))?;

        Self::jwk_to_decoding_key(key)
    }

    async fn fetch_jwks(&self) -> Result<Jwks, String> {
        let response = reqwest::get(&self.jwks_uri).await
            .map_err(|e| format!("Failed to fetch JWKS: {}", e))?;

        response.json::<Jwks>().await
            .map_err(|e| format!("Failed to parse JWKS: {}", e))
    }

    fn jwk_to_decoding_key(jwk: &Jwk) -> Result<DecodingKey, String> {
        match jwk.kty.as_str() {
            "RSA" => {
                let n = jwk.n.as_ref()
                    .ok_or("Missing 'n' in RSA key")?;
                let e = jwk.e.as_ref()
                    .ok_or("Missing 'e' in RSA key")?;

                DecodingKey::from_rsa_components(n, e)
                    .map_err(|e| format!("Invalid RSA key: {}", e))
            }
            _ => Err(format!("Unsupported key type: {}", jwk.kty))
        }
    }

    fn algorithm_from_str(alg: &str) -> Algorithm {
        match alg {
            "RS256" => Algorithm::RS256,
            "RS384" => Algorithm::RS384,
            "RS512" => Algorithm::RS512,
            "ES256" => Algorithm::ES256,
            "ES384" => Algorithm::ES384,
            "ES512" => Algorithm::ES512,
            _ => panic!("Unsupported algorithm: {}", alg)
        }
    }
}
```

---

## 5.13 Caso de Estudo: OIDC e o Misantropi4

### 5.13.1 Como OIDC teria adicionado defesa em profundidade

O ataque Misantropi4 utilizou credential stuffing contra o IDAP. Se o IDAP tivesse implementado OIDC como camada de identidade, as seguintes proteções teriam dificultado o ataque:

**ID Tokens com nonce**: Cada tentativa de autenticação teria um nonce único. Mesmo que credenciais fossem comprometidas, o atacante não poderia reutilizar tokens anteriores sem o nonce correto.

**MFA via Authorization Server**: O OIDC Authorization Server poderia exigir MFA como condição para emitir um ID Token com `acr` e `amr` indicando autenticação forte.

**Session Management**: O sistema poderia detectar e invalidar sessões quando um login anômalo fosse detectado em outro Client.

**Logout cooperativo**: Se o IDAP detectasse o ataque, poderia forçar logout de todas as sessões ativas via back-channel logout, imediatamente invalidando todas as sessões comprometidas.

**Token de curta duração**: ID Tokens de 5-15 minutos limitariam a janela de exploração, mesmo que o atacante obtivesse tokens.

**Auditoria granular**: Cada ID Token emitido teria `jti`, `iat`, e metadata detalhada, permitindo detecção de padrões anômalos (múltiplos logins de IPs diferentes, tentativas de access em horários incomuns, etc.).

### 5.13.2 Lições para sistemas de identidade governamental

O caso Misantropi4 reforça que sistemas de identidade governamental devem:

1. Implementar OIDC como protocolo de autenticação padrão
2. Exigir PKCE para todos os clients
3. Implementar MFA obrigatória via Authorization Server
4. Usar ID Tokens de curta duração com claims de autenticação
5. Implementar session management e logout cooperativo
6. Monitorar padrões de autenticação para detecção de anomalias
7. ManterDiscovery document atualizado com capacidades de segurança

---

## 5.14 Referências

- OpenID Connect Core 1.0 Specification
- OpenID Connect Discovery 1.0 Specification
- OpenID Connect Dynamic Client Registration 1.0
- OpenID Connect Session Management 1.0
- OpenID Connect Front-Channel Logout 1.0
- OpenID Connect Back-Channel Logout 1.0
- OpenID Connect RP-Initiated Logout 1.0
- OIDC FAPI 2.0 Security Profile
- RFC 7636 — PKCE
- JWT Best Current Practices (RFC 8725)
- Authlib Documentation
- oidc-provider Documentation
- OWASP OpenID Connect Security Cheat Sheet

---

## Resumo

## 5.15 Request Objects

Request Objects (OIDC Core §6.1) permitem que o Client envie um JWT assinado contendo todos os parâmetros de autorização em vez de enviá-los como query parameters individuais. Isso adiciona segurança porque os parâmetros não ficam expostos na URL e não podem ser modificados pelo browser.

### 5.15.1 Estrutura de um Request Object

```python
import jwt
import time
import secrets

def create_request_object(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    nonce: str,
    code_challenge: str,
    code_challenge_method: str,
    client_private_key: str,
    issuer: str
) -> str:
    """Criar Request Object JWT assinado pelo Client."""
    now = int(time.time())

    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": issuer,
        "exp": now + 300,  # 5 minutos
        "iat": now,
        "jti": secrets.token_urlsafe(16),
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method
    }

    # Assinar com chave privada do Client
    return jwt.encode(
        payload, client_private_key,
        algorithm="RS256",
        headers={
            "typ": "jwt",
            "alg": "RS256"
        }
    )
```

### 5.15.2 Uso do Request Object

Em vez de enviar parâmetros individuais na URL:

```
GET /authorize?
  response_type=code&
  client_id=my-client&
  redirect_uri=https://app.example.com/callback&
  scope=openid profile&
  state=abc123&
  nonce=xyz789
```

O Client envia o Request Object como um parâmetro:

```
GET /authorize?
  request=eyJhbGciOiJSUzI1NiIs...&
  client_id=my-client
```

Ou via `request_uri`:

```
GET /authorize?
  request_uri=urn:ietf:params:oauth:request_uri:req-abc123&
  client_id=my-client
```

### 5.15.3 Validação do Request Object no Authorization Server

```python
def validate_request_object(request_jwt: str, expected_client_id: str) -> dict:
    """Validar Request Object recebido do Client."""
    # Decodificar header sem validar
    header = jwt.get_unverified_header(request_jwt)

    # Verificar que é um Request Object
    if header.get("typ") != "jwt":
        raise ValueError("Invalid Request Object type")

    # Obter chave pública do Client (via JWKS do Client)
    kid = header.get("kid")
    client_key = get_client_signing_key(expected_client_id, kid)

    # Validar assinatura
    claims = jwt.decode(
        request_jwt, client_key,
        algorithms=["RS256"],
        audience=get_authorization_server_url(),
        issuer=expected_client_id
    )

    # Validar campos obrigatórios
    required_fields = [
        "iss", "aud", "exp", "iat",
        "response_type", "client_id", "redirect_uri",
        "scope", "state"
    ]
    for field in required_fields:
        if field not in claims:
            raise ValueError(f"Missing required field: {field}")

    # Verificar que client_id no request matches
    if claims["client_id"] != expected_client_id:
        raise ValueError("client_id mismatch")

    # Verificar que redirect_uri não foi modificado
    if not is_redirect_uri_registered(claims["client_id"], claims["redirect_uri"]):
        raise ValueError("Invalid redirect_uri")

    return claims
```

### 5.15.4 Benefícios de segurança do Request Object

1. **Parâmetros não expostos na URL**: O Request Object é um JWT compacto, não uma longa query string. Parâmetros sensíveis como `scope` não ficam visíveis na barra de endereços.

2. **Integridade garantida**: O Client assina o Request Object, garantindo que os parâmetros não foram modificados em trânsito.

3. **Prevenção de parameter injection**: Um atacante não pode adicionar parâmetros maliciosos ao Request Object porque ele é assinado.

4. **Suporte a client_secret_jwt e private_key_jwt**: O Authorization Server pode validar que o Client é quem diz ser usando a chave privada do Request Object.

5. **Necessário para OIDC FAPI**: O FAPI Security Profile requer Request Objects para alta segurança.

---

## 5.16 JARM — JWT Secured Authorization Response Mode

JARM (JWT Secured Authorization Response Mode, FAPI spec) protege a resposta de autorização retornando-a como um JWT assinado em vez de parâmetros plaintext na query string.

### 5.16.1 Por que JARM é necessário

Sem JARM, a resposta de autorização (o código ou token retornado ao Client) é transmitida como parâmetros de query ou fragmento na URL. Isso cria riscos:

- Logs do servidor podem capturar o código
- O browser pode expor a URL em Referer headers
- Um proxy ou CDN pode armazenar a URL
- Extensões maliciosas do browser podem ler a URL

JARM protege a resposta assinando-a com a chave do Authorization Server. O Client valida a assinatura antes de processar a resposta.

### 5.16.2 Implementação de JARM

**No Authorization Server:**

```python
def create_jarm_response(
    response_params: dict,
    response_mode: str,
    signing_key: str,
    signing_alg: str = "RS256"
) -> str:
    """Criar resposta JARM (JWT assinado)."""
    now = int(time.time())

    payload = {
        "iss": AUTH_SERVER_ISSUER,
        "iat": now,
        "exp": now + 300,
        "jti": secrets.token_urlsafe(16),
        "response_mode": response_mode
    }

    # Adicionar parâmetros de resposta ao payload
    payload.update(response_params)

    return jwt.encode(
        payload, signing_key,
        algorithm=signing_alg
    )

# Exemplo de uso no callback
@app.get("/authorize")
async def authorize(request):
    # ... validar request ...

    # Criar código de autorização
    code = secrets.token_urlsafe(32)
    store_auth_code(code, request)

    if request.response_mode == "jwt":
        # JARM response
        response_jwt = create_jarm_response(
            response_params={
                "code": code,
                "state": request.state
            },
            response_mode="jwt",
            signing_key=AUTH_SIGNING_KEY
        )

        # Retornar como fragmento JWT
        return RedirectResponse(
            f"{request.redirect_uri}#response={response_jwt}"
        )
    else:
        # Resposta padrão (não-JARM)
        return RedirectResponse(
            f"{request.redirect_uri}?code={code}&state={request.state}"
        )
```

**No Client:**

```python
def process_jarm_response(response_jwt: str, auth_server_jwks: dict) -> dict:
    """Processar e validar resposta JARM."""
    # Decodificar header para obter kid
    header = jwt.get_unverified_header(response_jwt)
    kid = header.get("kid")

    # Obter chave pública do Authorization Server
    signing_key = None
    for jwk in auth_server_jwks.get("keys", []):
        if jwk["kid"] == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            break

    if not signing_key:
        raise ValueError("JARM signing key not found")

    # Validar assinatura
    payload = jwt.decode(
        response_jwt, signing_key,
        algorithms=["RS256"],
        issuer=AUTH_SERVER_ISSUER,
        audience=CLIENT_ID
    )

    # Verificar expiração (já verificada pelo jwt.decode)
    # Verificar jti para prevenir replay
    jti = payload.get("jti")
    if is_jti_used(jti):
        raise ValueError("JAR response replay detected")
    mark_jti_used(jti)

    return payload
```

---

## 5.17 OIDC Conformance e Certificação

### 5.17.1 OpenID Certification

A OpenID Foundation oferece programa de certificação para implantações OIDC. A certificação garante que a implementação segue fielmente a especificação e interopera corretamente com outros provedores e clientes certificados.

**Níveis de certificação:**
- **Basic**: Fluxos básicos de autenticação
- **Implicit**: Suporte a Implicit Flow (legado)
- **Hybrid**: Suporte a Hybrid Flow
- **Config**: Suporte a Discovery e Dynamic Registration
- **Form Post**: Response mode via POST form
- **Self-Issued**: Suporte a Self-Issued OP

### 5.17.2 Testes de conformidade

```python
class OIDCConformanceTester:
    def __init__(self, op_metadata_url: str, client_config: dict):
        self.op_url = op_metadata_url
        self.config = client_config
        self.results = []

    async def run_all_tests(self):
        """Executar suite completa de testes de conformidade."""
        tests = [
            self.test_discovery_document,
            self.test_jwks_accessible,
            self.test_authorization_endpoint,
            self.test_token_endpoint,
            self.test_userinfo_endpoint,
            self.test_id_token_signature,
            self.test_id_token_claims,
            self.test_pkce_s256,
            self.test_state_parameter,
            self.test_nonce_parameter,
            self.test_redirect_uri_validation,
            self.test_scope_validation,
            self.test_error_responses,
            self.test_token_expiration,
            self.test_audience_validation,
            self.test_issuer_validation
        ]

        for test in tests:
            try:
                result = await test()
                self.results.append({
                    "test": test.__name__,
                    "status": "PASS" if result else "FAIL",
                    "details": result
                })
            except Exception as e:
                self.results.append({
                    "test": test.__name__,
                    "status": "ERROR",
                    "error": str(e)
                })

        return self.results

    async def test_discovery_document(self) -> bool:
        """Verificar que o discovery document é válido."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.op_url + "/.well-known/openid-configuration")

        if resp.status_code != 200:
            return False

        metadata = resp.json()

        required_fields = [
            "issuer", "authorization_endpoint", "token_endpoint",
            "jwks_uri", "response_types_supported",
            "subject_types_supported",
            "id_token_signing_alg_values_supported"
        ]

        return all(field in metadata for field in required_fields)

    async def test_id_token_signature(self) -> bool:
        """Verificar que ID Tokens são validamente assinados."""
        # Fluxo completo de autenticação
        tokens = await self._perform_authentication()

        id_token = tokens.get("id_token")
        if not id_token:
            return False

        # Validar assinatura
        try:
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")

            async with httpx.AsyncClient() as client:
                jwks_resp = await client.get(
                    (await self._get_metadata())["jwks_uri"]
                )
                jwks = jwks_resp.json()

            key = None
            for jwk in jwks.get("keys", []):
                if jwk["kid"] == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break

            if not key:
                return False

            claims = jwt.decode(
                id_token, key,
                algorithms=["RS256"],
                audience=self.config["client_id"],
                issuer=(await self._get_metadata())["issuer"]
            )

            return "sub" in claims and "iss" in claims

        except Exception:
            return False

    async def test_pkce_s256(self) -> bool:
        """Verificar que PKCE S256 funciona corretamente."""
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        # Iniciar fluxo com PKCE
        auth_url = await self._build_auth_url(
            code_challenge=code_challenge,
            code_challenge_method="S256"
        )

        # Obter código
        code = await self._get_auth_code(auth_url)

        # Trocar código com code_verifier
        token_response = await self._exchange_code(
            code, code_verifier
        )

        return "access_token" in token_response
```

---

## 5.18 OIDC para APIs — Resource Indicators

Resource Indicators (RFC 8707) permitem que o Client especifique para quais Resource Servers o token deve ser válido. Isso é fundamental em arquiteturas com múltiplas APIs.

### 5.18.1 Por que Resource Indicators são necessários

Em sistemas com múltiplas APIs, o access token emitido deve ser válido apenas para a API específica. Sem Resource Indicators, um token emitido para "ler perfil" pode ser usado indevidamente para acessar "pagamentos".

### 5.18.2 Implementação

**No Authorization Request:**

```
GET /authorize?
  response_type=code&
  client_id=my-client&
  redirect_uri=https://app.example.com/callback&
  scope=openid profile&
  resource=https://api.example.com&
  resource=https://payments.example.com&
  state=abc123
```

**No Authorization Server:**

```python
def validate_and_issue_token(request, auth_code):
    """Validar resource indicators e emitir token."""
    resources = request.get("resources", [])

    if not resources:
        raise ValueError("At least one resource indicator required")

    # Validar que os recursos são registrados
    for resource in resources:
        if not is_registered_resource(resource):
            raise ValueError(f"Unknown resource: {resource}")

    # Verificar que o client tem acesso aos recursos solicitados
    client = get_client(request.client_id)
    for resource in resources:
        if resource not in client.allowed_resources:
            raise ValueError(
                f"Client not authorized for resource: {resource}"
            )

    # Emitir token com audience restrita
    access_token = jwt.encode(
        {
            "sub": auth_code.user_id,
            "iss": AUTH_SERVER_ISSUER,
            "aud": resources,  # Lista de audiences
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "scope": auth_code.scope,
            "client_id": request.client_id,
            "resource_indicators": resources
        },
        signing_key,
        algorithm="RS256"
    )

    return {"access_token": access_token, "token_type": "Bearer"}
```

**No Resource Server:**

```python
def validate_api_token(token: str, expected_resource: str) -> dict:
    """Validar token com verificação de resource indicator."""
    # Decodificar
    claims = jwt.decode(
        token, signing_key,
        algorithms=["RS256"],
        issuer=AUTH_SERVER_ISSUER
    )

    # Verificar que o token foi emitido para este Resource Server
    audience = claims.get("aud", [])
    if isinstance(audience, str):
        audience = [audience]

    if expected_resource not in audience:
        raise HTTPException(
            status_code=403,
            detail=f"Token not valid for this resource"
        )

    return claims
```

---

## 5.19 OIDC Security Patterns Avançados

### 5.19.1 Token Exchange (RFC 8693)

Token Exchange permite que um Client troque um token por outro com diferentes claims ou scopes. Isso é útil em cenários de delegação.

```python
# Token Exchange: Service A obtém token para acessar Service B
# em nome do usuário

async def exchange_token(
    subject_token: str,
    subject_token_type: str,
    audience: str,
    scope: str,
    requested_token_type: str
) -> dict:
    """Trocar token via RFC 8693."""
    response = await httpx.AsyncClient().post(
        f"{AUTH_SERVER}/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "audience": audience,
            "scope": scope,
            "requested_token_type": requested_token_type
        },
        headers={
            "Authorization": f"Bearer {service_token}"
        }
    )

    if response.status_code != 200:
        raise TokenExchangeError(response.text)

    return response.json()
```

### 5.19.2 Pushed Authorization Requests (PAR)

PAR (RFC 9126) permite que o Client envie os parâmetros de autorização via HTTP POST ao Authorization Server em vez de incluí-los na URL. O Authorization Server retorna um `request_uri` que o Client usa no redirect.

```python
async def pushed_authorization_request(params: dict) -> str:
    """Enviar PAR e obter request_uri."""
    response = await httpx.AsyncClient().post(
        f"{AUTH_SERVER}/par",
        data=params,
        headers={
            "Authorization": f"Basic {base64_encode(client_id + ':' + client_secret)}"
        }
    )

    if response.status_code != 201:
        raise ValueError("PAR failed")

    result = response.json()
    return result["request_uri"]

# Uso
request_uri = await pushed_authorization_request({
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "openid profile email",
    "state": generate_state(),
    "nonce": generate_nonce(),
    "code_challenge": code_challenge,
    "code_challenge_method": "S256"
})

# Redirect com request_uri em vez de parâmetros individuais
auth_url = (
    f"{AUTH_SERVER}/authorize"
    f"?client_id={CLIENT_ID}"
    f"&request_uri={request_uri}"
)
```

### 5.19.3 JWT Authorization Response Mode (JARM) com PAR

A combinação de PAR + JARM oferece máxima segurança: os parâmetros não são expostos na URL (PAR) e a resposta também é assinada (JARM).

```python
async def secure_authorization_flow():
    """Fluxo completo com PAR + JARM."""
    # 1. Enviar PAR
    request_uri = await pushed_authorization_request({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "response_mode": "jwt"  # JARM
    })

    # 2. Redirect para authorize com request_uri
    auth_url = (
        f"{AUTH_SERVER}/authorize"
        f"?client_id={CLIENT_ID}"
        f"&request_uri={request_uri}"
    )

    # 3. Após autorização, receber response JWT
    # (processado no callback)

    return auth_url
```

---

## 5.20 Referências Adicionais

- OpenID Connect Request Object (Core §6.1)
- JWT Secured Authorization Response Mode (JARM)
- OAuth 2.0 Pushed Authorization Requests (RFC 9126)
- OAuth 2.0 Resource Indicators (RFC 8707)
- OAuth 2.0 Token Exchange (RFC 8693)
- OpenID Connect Federation
- OpenID Certification Program
- FAPI 2.0 Security Profile
- FAPI 2.0 Message Signing
- PAR + JARM Security Analysis
- OAuth 2.0 for Browser-Based Applications (BCP)

---

## Resumo

OpenID Connect é a camada de identidade que completa OAuth 2.0 para autenticação. Este capítulo cobriu:

- **OIDC vs OAuth 2.0**: A diferença fundamental entre autorização e autenticação
- **ID Tokens**: Estrutura JWT, claims obrigatórias e opcionais, validação completa
- **UserInfo Endpoint**: Dados de perfil complementares ao ID Token
- **Discovery Document**: Configuração automática e JWKS
- **Dynamic Client Registration**: Registro automático com proteções de segurança
- **Logout Flows**: RP-Initiated, Back-Channel, e Front-Channel logout
- **Session Management**: Coordenação de sessões entre Client e Authorization Server
- **Hybrid Flow**: Quando e como usar, com recomendações de segurança
- **PKCE para OIDC**: Por que é essencial e como implementar
- **Segurança**: Ataques comuns, mitigações, e OIDC FAPI
- **Integração com OAuth 2.0**: Multi-protocol support
- **Implementação completa**: Exemplos em Python (Authlib), Node.js (oidc-provider), e Rust
- **Caso Misantropi4**: Lições de defesa em profundidade
- **Request Objects**: Parâmetros assinados para máxima segurança
- **JARM**: Respostas JWT assinadas
- **OIDC Conformance**: Certificação e testes
- **Resource Indicators**: Tokens para múltiplas APIs
- **Security Patterns avançados**: Token Exchange, PAR, e combinações

---

## 5.21 OIDC para Enterprise — Padrões Avançados

### 5.21.1 OIDC Provider Discovery para Enterprise

Em ambientes enterprise, múltiplos provedores OIDC podem coexistir. O Discovery Document permite que Client encontre automaticamente o provider correto.

```python
class EnterpriseOIDCDiscovery:
    def __init__(self, trust_registry_url: str):
        self.registry_url = trust_registry_url
        self.providers = {}
        self._load_registry()

    def _load_registry(self):
        """Carregar registry de provedores confiáveis."""
        response = httpx.get(self.registry_url)
        registry = response.json()

        for provider in registry["providers"]:
            issuer = provider["issuer"]
            self.providers[issuer] = {
                "metadata_url": provider["metadata_url"],
                "trust_level": provider.get("trust_level", "basic"),
                "certification": provider.get("certification"),
                "supported_flows": provider.get("supported_flows", [])
            }

    def find_provider(self, issuer: str) -> dict:
        """Encontrar provider por issuer."""
        if issuer not in self.providers:
            raise ProviderNotFoundError(
                f"Provider not found: {issuer}"
            )
        return self.providers[issuer]

    async def validate_provider(self, issuer: str) -> bool:
        """Validar que um provider é confiável."""
        provider = self.find_provider(issuer)

        # Verificar certificação
        if provider["trust_level"] == "certified":
            if not provider.get("certification"):
                return False

        # Verificar discovery document
        async with httpx.AsyncClient() as client:
            resp = await client.get(provider["metadata_url"])

        if resp.status_code != 200:
            return False

        metadata = resp.json()

        # Verificar que issuer confere
        if metadata.get("issuer") != issuer:
            return False

        # Verificar capacidades mínimas
        required_capabilities = [
            "token_endpoint",
            "jwks_uri",
            "id_token_signing_alg_values_supported"
        ]

        return all(cap in metadata for cap in required_capabilities)

    async def get_provider_metadata(self, issuer: str) -> dict:
        """Obter metadata de um provider."""
        provider = self.find_provider(issuer)

        async with httpx.AsyncClient() as client:
            resp = await client.get(provider["metadata_url"])

        if resp.status_code != 200:
            raise MetadataError(
                f"Failed to fetch metadata: {resp.status_code}"
            )

        return resp.json()
```

### 5.21.2 Multi-Tenant OIDC

Em aplicações multi-tenant, cada tenant pode ter seu próprio provedor OIDC. O Client deve descobrir e autenticar com o provider correto baseado no tenant.

```python
class MultiTenantOIDC:
    def __init__(self, tenant_config_store):
        self.tenants = tenant_config_store
        self.providers = {}  # tenant_id -> OIDCProvider

    async def get_provider(self, tenant_id: str):
        """Obter provider OIDC para um tenant."""
        if tenant_id not in self.providers:
            config = await self.tenants.get_config(tenant_id)
            if not config:
                raise TenantNotFoundError(tenant_id)

            self.providers[tenant_id] = OIDCProvider(
                issuer=config["issuer"],
                client_id=config["client_id"],
                client_secret=config.get("client_secret")
            )

        return self.providers[tenant_id]

    async def authenticate_tenant(self, tenant_id: str,
                                   redirect_uri: str) -> str:
        """Iniciar autenticação para um tenant específico."""
        provider = await self.get_provider(tenant_id)

        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        # Armazenar contexto do tenant
        store_tenant_context(tenant_id, state, nonce)

        auth_url = await provider.create_login_url(
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce,
            prompt="login"  # Forçar login no tenant
        )

        return auth_url

    async def handle_callback(self, tenant_id: str, code: str,
                               state: str) -> dict:
        """Processar callback para um tenant."""
        provider = await self.get_provider(tenant_id)

        # Validar state
        expected_state = get_tenant_state(tenant_id)
        if state != expected_state:
            raise ValueError("State mismatch")

        # Trocar código por tokens
        tokens = await provider.exchange_code(code)

        # Validar ID Token
        nonce = get_tenant_nonce(tenant_id)
        id_token_claims = await provider.validate_id_token(
            tokens["id_token"], nonce
        )

        # Verificar que o tenant do ID Token corresponde
        token_issuer = id_token_claims.get("iss")
        expected_issuer = (await self.get_provider(tenant_id)).issuer

        if token_issuer != expected_issuer:
            raise ValueError("Issuer mismatch — possible cross-tenant attack")

        return {
            "tenant_id": tenant_id,
            "user_id": id_token_claims["sub"],
            "email": id_token_claims.get("email"),
            "name": id_token_claims.get("name"),
            "access_token": tokens["access_token"],
            "id_token": tokens["id_token"]
        }
```

### 5.21.3 OIDC para B2B (Business-to-Business)

Em cenários B2B, uma organização concede acesso a sua aplicação para usuários de outra organização. Cada organização tem seu próprio IdP.

```python
class OIDCB2B:
    def __init__(self, app_issuer: str, app_client_id: str):
        self.issuer = app_issuer
        self.client_id = app_client_id
        self.trusted_partners = {}  # org_id -> partner_config

    async def register_partner(self, org_id: str, metadata_url: str):
        """Registrar um partner organização."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(metadata_url)

        metadata = resp.json()

        self.trusted_partners[org_id] = {
            "issuer": metadata["issuer"],
            "jwks_uri": metadata["jwks_uri"],
            "authorization_endpoint": metadata["authorization_endpoint"],
            "token_endpoint": metadata["token_endpoint"],
            "scopes_supported": metadata.get("scopes_supported", []),
            "registered_at": datetime.utcnow()
        }

    async def authenticate_partner_user(self, org_id: str) -> str:
        """Redirecionar para o IdP do partner."""
        partner = self.trusted_partners.get(org_id)
        if not partner:
            raise PartnerNotFoundError(org_id)

        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        # Armazenar contexto
        store_b2b_context(org_id, state, nonce, code_verifier)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": f"{self.issuer}/b2b/callback/{org_id}",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        return (
            f"{partner['authorization_endpoint']}"
            f"?{requests.compat.urlencode(params)}"
        )

    async def handle_b2b_callback(self, org_id: str, code: str,
                                   state: str) -> dict:
        """Processar callback de partner."""
        partner = self.trusted_partners[org_id]

        # Validar state
        expected_state = get_b2b_state(org_id)
        if state != expected_state:
            raise ValueError("State mismatch")

        # Obter código do partner
        code_verifier = get_b2b_code_verifier(org_id)

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                partner["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{self.issuer}/b2b/callback/{org_id}",
                    "client_id": self.client_id,
                    "code_verifier": code_verifier
                }
            )

        tokens = token_resp.json()

        # Validar ID Token contra o JWKS do partner
        id_token_claims = await self._validate_partner_id_token(
            tokens["id_token"],
            partner,
            get_b2b_nonce(org_id)
        )

        return {
            "partner_org": org_id,
            "user_id": id_token_claims["sub"],
            "email": id_token_claims.get("email"),
            "name": id_token_claims.get("name"),
            "partner_issuer": partner["issuer"]
        }

    async def _validate_partner_id_token(self, id_token: str,
                                          partner: dict,
                                          expected_nonce: str) -> dict:
        """Validar ID Token do partner."""
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")

        async with httpx.AsyncClient() as client:
            jwks_resp = await client.get(partner["jwks_uri"])
            jwks = jwks_resp.json()

        key = None
        for jwk in jwks.get("keys", []):
            if jwk["kid"] == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise ValueError("Partner signing key not found")

        claims = jwt.decode(
            id_token, key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=partner["issuer"]
        )

        if claims.get("nonce") != expected_nonce:
            raise ValueError("Nonce mismatch")

        return claims
```

---

## 5.22 OIDC Security Best Practices — Checklist Detalhado

### 5.22.1 Implementação do Provider

```
[x] Discovery document publicado e acessível via HTTPS
[x] JWKS com chaves RSA >= 2048 bits ou EC P-256+
[x] Rotação de chaves programada (recomendado: a cada 90 dias)
[x] ID Tokens com expiração curta (5-15 minutos)
[x] Access tokens com expiração apropriada (5-60 minutos)
[x] Refresh tokens com rotation obrigatória
[x] PKCE aceito e obrigatório (S256 apenas)
[x] Redirect URIs validadas por comparação exata
[x] State parameter obrigatório e validado
[x] Nonce parameter obrigatório para OIDC
[x] Scope validation (não aceitar scopes desconhecidos)
[x] Audience validation em todos os endpoints
[x] Rate limiting em todos os endpoints
[x] Bloqueio progressivo após falhas de autenticação
[x] MFA suportado e configurável
[x] Token revocation endpoint implementado
[x] Token introspection endpoint implementado
[x] Back-channel logout suportado
[x] Front-channel logout suportado
[x] Auditoria de eventos de autenticação
[x] Monitoring de endpoints de segurança
```

### 5.22.2 Implementação do Client (Relying Party)

```
[x] Authorization Code Flow com PKCE (S256)
[x] Implicit Flow desabilitado
[x] Hybrid Flow evitado (usar Authorization Code quando possível)
[x] State parameter gerado e validado
[x] Nonce parameter gerado e validado
[x] ID Token validado (assinatura, issuer, audience, expiry)
[x] at_hash verificado quando access token disponível
[x] Redirect URIs configuradas exatamente (sem curingas)
[x] Tokens armazenados de forma segura
[x] Refresh tokens com rotation habilitada
[x] Logout cooperativo implementado
[x] Sessão local invalidada no logout
[x] TLS verificado em todas as comunicações
[x] Erros tratados sem expor detalhes internos
[x] Logging de eventos de autenticação
```

### 5.22.3 Operações e Monitoring

```
[x] Alertas para falhas de autenticação em massa
[x] Alertas para tokens reutilizados
[x] Alertas para accessos de geolocalização incomum
[x] Dashboard de métricas de autenticação
[x] Logs centralizados com retenção adequada
[x] Backup de chaves criptográficas
[x] Plano de recuperação de desastres
[x] Testes de penetração regulares
[x] Auditoria de conformidade periódica
[x] Atualização de dependências de segurança
```

---

## 5.23 Referências Adicionais

- OpenID Connect Request Object (Core §6.1)
- JWT Secured Authorization Response Mode (JARM)
- OAuth 2.0 Pushed Authorization Requests (RFC 9126)
- OAuth 2.0 Resource Indicators (RFC 8707)
- OAuth 2.0 Token Exchange (RFC 8693)
- OpenID Connect Federation
- OpenID Certification Program
- FAPI 2.0 Security Profile
- FAPI 2.0 Message Signing
- PAR + JARM Security Analysis
- OAuth 2.0 for Browser-Based Applications (BCP)
- OpenID Connect for Identity Assurance
- Shared Signals Framework (SSF)
- Continuous Access Evaluation Protocol (CAEP)

---

## Resumo

OpenID Connect é a camada de identidade que completa OAuth 2.0 para autenticação. Este capítulo cobriu:

- **OIDC vs OAuth 2.0**: A diferença fundamental entre autorização e autenticação
- **ID Tokens**: Estrutura JWT, claims obrigatórias e opcionais, validação completa
- **UserInfo Endpoint**: Dados de perfil complementares ao ID Token
- **Discovery Document**: Configuração automática e JWKS
- **Dynamic Client Registration**: Registro automático com proteções de segurança
- **Logout Flows**: RP-Initiated, Back-Channel, e Front-Channel logout
- **Session Management**: Coordenação de sessões entre Client e Authorization Server
- **Hybrid Flow**: Quando e como usar, com recomendações de segurança
- **PKCE para OIDC**: Por que é essencial e como implementar
- **Segurança**: Ataques comuns, mitigações, e OIDC FAPI
- **Integração com OAuth 2.0**: Multi-protocol support
- **Implementação completa**: Exemplos em Python (Authlib), Node.js (oidc-provider), e Rust
- **Caso Misantropi4**: Lições de defesa em profundidade
- **Request Objects**: Parâmetros assinados para máxima segurança
- **JARM**: Respostas JWT assinadas
- **OIDC Conformance**: Certificação e testes
- **Resource Indicators**: Tokens para múltiplas APIs
- **Security Patterns avançados**: Token Exchange, PAR, e combinações
- **OIDC para Enterprise**: Multi-tenant, B2B, e federation
- **Security Best Practices**: Checklist detalhado para Provider e Client

O próximo capítulo explora Single Sign-On (SSO), o padrão que permite aos usuários autenticar uma vez e acessar múltiplas aplicações, com foco em SAML e OIDC.
---

*[Capítulo anterior: 04 — Oauth2](04-oauth2.md)*
*[Próximo capítulo: 06 — Sso](06-sso.md)*
