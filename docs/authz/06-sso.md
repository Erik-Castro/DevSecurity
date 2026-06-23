# Capítulo 6 — Single Sign-On (SSO)

## Introdução

Single Sign-On (SSO) é um mecanismo de autenticação que permite ao usuário se autenticar uma única vez e obter acesso a múltiplas aplicações e sistemas sem necessidade de autenticar novamente para cada um deles. SSO é uma das arquiteturas de identidade mais importantes na infraestrutura corporativa moderna — sem ela, organizações com dezenas ou centenas de aplicações enfrentariam uma crise de produtividade e segurança gerenciando credenciais independentes para cada sistema.

O SSO resolve dois problemas fundamentais simultaneamente: **experiência do usuário** (reduzir a fadiga de senhas e o número de autenticações) e **segurança** (centralizar controle de acesso, facilitar revogação, e impor políticas de autenticação consistentes). Quando implementado corretamente, SSO reduz a superfície de ataque, melhora a auditoria, e simplifica a gestão de identidades.

O caso Misantropi4 contra o IDAP exemplifica exatamente o oposto do SSO: um sistema isolado onde credenciais eram gerenciadas individualmente, sem camada centralizada de controle. Se o IDAP tivesse integrado-se a um SSO federado com MFA centralizado, os ataques de credential stuffing teriam sido significativamente mais difíceis porque as credenciais estariam sob gestão de um provedor de identidade robusto com proteções como rate limiting, anomalias, e MFA.

Este capítulo cobre os fundamentos de SSO, os dois grandes protocolos (SAML 2.0 e OIDC), comparação detalhada, provedores de identidade (Keycloak, Okta, Azure AD), federação, provisioning, gerenciamento de sessões cross-domain, segurança, e implementação completa.

---

## 6.1 Conceitos de SSO

### 6.1.1 O problema que SSO resolve

Em ambientes corporativos modernos, um usuário típico interage com dezenas de sistemas: e-mail, CRM, ERP, ferramentas de gestão de projetos, repositórios de código, ferramentas de CI/CD, sistemas de monitoramento, e mais. Sem SSO, cada um desses sistemas mantém sua própria base de credenciais, criando:

**Sobrecarga cognitiva**: O usuário deve lembrar múltiplas senhas. Estudos mostram que o usuário médio corporativo possui entre 25 e 50 credenciais, levando a reutilização de senhas e comportamentos inseguros.

**Fadiga de senhas**: Autenticar repetidamente para cada aplicação é frustrante e improdutivo. Estima-se que um funcionário perde 10-15 minutos por dia apenas com processos de autenticação.

**Insegurança**: Múltiplas credenciais significam múltiplos pontos de falha. Se uma senha é comprometida em um sistema, ela pode ser reutilizada em outros (credential stuffing — o mesmo vetor do Misantropi4).

**Dificuldade de gestão**: Quando um funcionário sai da organização, é necessário revogar acesso em cada sistema individualmente. Isso é propenso a erros e atrasos.

**Falta de auditoria**: Com credenciais descentralizadas, não há visibilidade centralizada sobre quem acessa o quê.

### 6.1.2 Modelo de SSO

O modelo SSO introduz três entidades:

1. **Identity Provider (IdP)**: O servidor centralizado que autentica o usuário e emite tokens de identidade (SAML assertions ou OIDC tokens). O IdP é o "fonte da verdade" para autenticação.

2. **Service Provider (SP)**: Cada aplicação que o usuário deseja acessar. O SP delega a autenticação ao IdP e aceita tokens de identidade emitidos por ele.

3. **Usuário (Principal)**: A pessoa que se autentica no IdP e acessa os SPs.

**Fluxo básico de SSO:**

1. O usuário tenta acessar um SP (ex: o CRM)
2. O SP verifica que o usuário não está autenticado
3. O SP redireciona o usuário para o IdP
4. O usuário autentica-se no IdP (uma única vez)
5. O IdP emite um token de identidade
6. O token é redirecionado de volta ao SP
7. O SP valida o token e cria uma sessão local
8. Para acessar outro SP, o processo repete a partir do passo 1, mas o IdP já reconhece a sessão e NÃO solicita autenticação novamente

### 6.1.3 Tipos de SSO

**Enterprise SSO (eSSO)**: SSO para aplicações corporativas internas. Tipicamente usando SAML ou OIDC, integrado a diretórias corporativas (Active Directory, LDAP).

**Social SSO**: Login usando credenciais de redes sociais (Google, Facebook, GitHub). Baseado em OAuth 2.0/OIDC.

**Federated SSO**: SSO entre organizações diferentes. Um usuário de uma organização pode acessar serviços de outra usando credenciais de sua própria organização. Baseado em SAML Federation ou OIDC Federation.

**Cross-Domain SSO (CDSSO)**: SSO entre aplicações em domínios diferentes. Requer mecanismos especiais como cookies de terceiros (terceiro-party cookies), iframes, ou protocolos específicos.

---

## 6.2 SAML 2.0

Security Assertion Markup Language (SAML) 2.0 é um padrão XML-based para troca de dados de autenticação e autorização entre entidades. Publicado como OASIS Standard em 2005, SAML é o protocolo de SSO mais maduro e amplamente implementado em ambientes corporativos.

### 6.2.1 Arquitetura SAML

SAML define três roles principais:

1. **Principal**: O usuário que solicita acesso
2. **Identity Provider (IdP)**: Autentica o Principal e emite assertions
3. **Service Provider (SP)**: Protege recursos e confia nas assertions do IdP

SAML também define dois componentes críticos:
- **SAML Bindings**: Como as mensagens SAML são transportadas (HTTP Redirect, HTTP POST, Artifact)
- **SAML Profiles**: Como SAML assertions são usadas em cenários específicos (SSO, Single Logout, Attribute)

### 6.2.2 SAML Assertions

Uma SAML Assertion é o documento XML que contém as declarações de autenticação, atributos, e autorização do Principal. Existem três tipos de assertions:

**Authentication Statement**: Declara que o Principal foi autenticado, quando, e usando que método.

```xml
<saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="_abc123"
                IssueInstant="2024-01-15T10:30:00Z"
                Version="2.0">
    <saml:Issuer>https://idp.example.com</saml:Issuer>
    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <!-- Assinatura digital do IdP -->
    </ds:Signature>

    <saml:Subject>
        <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
            usuario@example.com
        </saml:NameID>
        <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
            <saml:SubjectConfirmationData
                NotOnOrAfter="2024-01-15T10:35:00Z"
                Recipient="https://crm.example.com/saml/acs"
                InResponseTo="_request123"/>
        </saml:SubjectConfirmation>
    </saml:Subject>

    <saml:Conditions NotBefore="2024-01-15T10:30:00Z"
                      NotOnOrAfter="2024-01-15T11:00:00Z">
        <saml:AudienceRestriction>
            <saml:Audience>https://crm.example.com</saml:Audience>
        </saml:AudienceRestriction>
    </saml:Conditions>

    <saml:AuthnStatement AuthnInstant="2024-01-15T10:30:00Z"
                          SessionIndex="_session123">
        <saml:AuthnContext>
            <saml:AuthnContextClassRef>
                urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
            </saml:AuthnContextClassRef>
        </saml:AuthnContext>
    </saml:AuthnStatement>

    <saml:AttributeStatement>
        <saml:Attribute Name="urn:oid:2.5.4.3"
                         NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <saml:AttributeValue>João da Silva</saml:AttributeValue>
        </saml:Attribute>
        <saml:Attribute Name="urn:oid:0.9.2342.19200300.100.1.3"
                         NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri">
            <saml:AttributeValue>joao@example.com</saml:AttributeValue>
        </saml:Attribute>
        <saml:Attribute Name="role"
                         NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
            <saml:AttributeValue>admin</saml:AttributeValue>
        </saml:Attribute>
    </saml:AttributeStatement>
</saml:Assertion>
```

**Attribute Statement**: Declara atributos do Principal (nome, e-mail, cargo, roles, etc.).

**Authorization Decision Statement**: Declara se o Principal está autorizado a acessar um recurso específico.

### 6.2.3 Assinatura Digital e Criptografia

A segurança das SAML Assertions depende fundamentalmente de assinatura digital XML (XML-DSig). O IdP assina cada assertion com sua chave privada, e o SP valida a assinatura usando a chave pública do IdP.

**Estrutura de uma assinatura SAML:**

```xml
<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
    <ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:CanonicalizationMethod
            Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        <ds:SignatureMethod
            Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        <ds:Reference URI="#_abc123">
            <ds:Transforms>
                <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
            </ds:Transforms>
            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
            <ds:DigestValue>...</ds:DigestValue>
        </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>...</ds:SignatureValue>
    <ds:KeyInfo>
        <ds:X509Data>
            <ds:X509Certificate>...</ds:X509Certificate>
        </ds:X509Data>
    </ds:KeyInfo>
</ds:Signature>
```

**Validação de assinatura:**

```python
from lxml import etree
from signxml import XMLSigner, XMLVerifier
import hashlib

class SAMLAssertionValidator:
    def __init__(self, idp_certificate: str, sp_certificate: str):
        self.idp_cert = idp_certificate
        self.sp_cert = sp_certificate

    def validate_assertion(self, assertion_xml: str) -> dict:
        # Parse XML
        root = etree.fromstring(assertion_xml.encode())

        # Validar assinatura
        try:
            verified_root = XMLVerifier().verify(
                root,
                x509_cert=self.idp_cert
            ).verified_xml
        except Exception as e:
            raise SAMLError(f"Signature validation failed: {e}")

        # Extrair e validar assertions
        assertions = verified_root.findall(
            './/{urn:oasis:names:tc:SAML:2.0:assertion}Assertion'
        )

        if not assertions:
            raise SAMLError("No assertions found")

        results = []
        for assertion in assertions:
            result = self._validate_single_assertion(assertion)
            results.append(result)

        return results

    def _validate_single_assertion(self, assertion) -> dict:
        # Validar Issuer
        issuer = assertion.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}Issuer'
        )
        if issuer is None or issuer.text != self.idp_entity_id:
            raise SAMLError("Invalid issuer")

        # Validar Conditions
        conditions = assertion.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}Conditions'
        )
        if conditions is not None:
            self._validate_conditions(conditions)

        # Extrair Subject
        subject = assertion.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}Subject'
        )
        name_id = subject.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}NameID'
        )

        # Extrair AuthnStatement
        authn_statement = assertion.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}AuthnStatement'
        )

        # Extrair AttributeStatement
        attribute_statement = assertion.find(
            '{urn:oasis:names:tc:SAML:2.0:assertion}AttributeStatement'
        )
        attributes = {}
        if attribute_statement is not None:
            for attr in attribute_statement.findall(
                '{urn:oasis:names:tc:SAML:2.0:assertion}Attribute'
            ):
                name = attr.get('Name')
                values = [
                    v.text for v in attr.findall(
                        '{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue'
                    )
                ]
                attributes[name] = values if len(values) > 1 else values[0]

        return {
            'name_id': name_id.text if name_id is not None else None,
            'session_index': authn_statement.get('SessionIndex')
                if authn_statement is not None else None,
            'authn_instant': authn_statement.get('AuthnInstant')
                if authn_statement is not None else None,
            'attributes': attributes
        }

    def _validate_conditions(self, conditions):
        not_before = conditions.get('NotBefore')
        not_on_or_after = conditions.get('NotOnOrAfter')

        now = datetime.utcnow()

        if not_before:
            not_before_dt = parse_saml_time(not_before)
            if now < not_before_dt:
                raise SAMLError("Assertion not yet valid")

        if not_on_or_after:
            not_on_or_after_dt = parse_saml_time(not_on_or_after)
            if now >= not_on_or_after_dt:
                raise SAMLError("Assertion expired")
```

### 6.2.4 SAML Bindings

SAML define diferentes métodos de transporte para mensagens entre IdP e SP:

**HTTP Redirect Binding**: Mensagens SAML são codificadas na URL e transmitidas via redirect HTTP. Adequado para requests pequenos.

```
GET /saml2/sso?SAMLRequest=hNldbsIwEET%2F... HTTP/1.1
Host: sp.example.com
```

**HTTP POST Binding**: Mensagens SAML são transmitidas como dados de formulário HTTP POST. Adequado para responses maiores e assertions.

```html
<form method="POST" action="https://sp.example.com/saml/acs">
    <input type="hidden" name="SAMLResponse" value="PHNhbWwycDp..."/>
    <input type="hidden" name="RelayState" value="https://crm.example.com/app"/>
</form>
<script>document.forms[0].submit()</script>
```

**HTTP Artifact Binding**: Um artifact curto é transmitido via redirect, e o SP faz uma chamada SOAP back-channel para obter a assertion completa. Útil quando o SP não pode receber a assertion diretamente.

**SOAP Binding**: Comunicação direta via SOAP sobre HTTP. Usado em cenários back-channel.

### 6.2.5 SAML Profiles

**Browser SSO Profile**: O profile mais comum. Define como um browser interage com IdP e SP para obter SSO.

Fluxo SP-Initiated (o mais comum):

```
1. Usuario -> SP: Acessa https://crm.example.com
2. SP -> Usuario: Redireciona para IdP com AuthnRequest
3. Usuario -> IdP: Apresenta AuthnRequest
4. IdP -> Usuario: Exibe tela de login (se necessário)
5. Usuario -> IdP: Fornece credenciais
6. IdP -> Usuario: Redireciona para SP com Response (contendo Assertion)
7. Usuario -> SP: Apresenta Response
8. SP: Valida Assertion e cria sessão
```

Fluxo IdP-Initiated:

```
1. Usuario -> IdP: Acessa https://idp.example.com/dashboard
2. IdP -> Usuario: Exibe dashboard com links para SPs
3. Usuario -> IdP: Clica em link para CRM
4. IdP -> Usuario: Redireciona para SP com Response (IdP-Initiated)
5. SP: Valida Assertion e cria sessão
```

**Single Logout Profile**: Permite que o logout em um SP seja propagado para outros SPs via IdP.

**Enhanced Client/Proxy (ECP) Profile**: Para clientes que não são browsers (aplicações mobile, SOAP clients).

### 6.2.6 Metadata SAML

Cada entidade SAML (IdP e SP) publica um documento XML de metadata que descreve seus endpoints, chaves públicas, e capacidades.

**Metadata do SP:**

```xml
<EntityDescriptor entityID="https://crm.example.com"
                  xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
    <SPSSODescriptor
        AuthnRequestsSigned="true"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>
                        MIICpDCCAYwCCQDU+...
                    </ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </KeyDescriptor>
        <KeyDescriptor use="encryption">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>
                        MIICpDCCAYwCCQDU+...
                    </ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </KeyDescriptor>
        <NameIDFormat>
            urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
        </NameIDFormat>
        <AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://crm.example.com/saml/acs"
            index="1"
            isDefault="true"/>
        <AttributeConsumingService index="1">
            <ServiceName xml:lang="pt">CRM Application</ServiceName>
            <RequestedAttribute
                Name="urn:oid:2.5.4.3"
                NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
                FriendlyName="Nome"/>
            <RequestedAttribute
                Name="urn:oid:0.9.2342.19200300.100.1.3"
                NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
                FriendlyName="Email"/>
        </AttributeConsumingService>
    </SPSSODescriptor>
</EntityDescriptor>
```

**Metadata do IdP:**

```xml
<EntityDescriptor entityID="https://idp.example.com"
                  xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
    <IDPSSODescriptor
        WantAuthnRequestsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <KeyDescriptor use="signing">
            <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                <ds:X509Data>
                    <ds:X509Certificate>
                        MIICpDCCAYwCCQDU+...
                    </ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </KeyDescriptor>
        <SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="https://idp.example.com/saml/slo"/>
        <SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://idp.example.com/saml/slo"/>
        <SingleSignOnService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="https://idp.example.com/saml/sso"/>
        <SingleSignOnService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="https://idp.example.com/saml/sso"/>
        <NameIDFormat>
            urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
        </NameIDFormat>
    </IDPSSODescriptor>
</EntityDescriptor>
```

---

## 6.3 OIDC-based SSO

OIDC é o protocolo moderno para SSO, construído sobre OAuth 2.0 e com benefícios significativos sobre SAML para muitos cenários.

### 6.3.1 SSO com OIDC

O SSO com OIDC utiliza o Authorization Code Flow (com PKCE) para autenticar o usuário no IdP e obter um ID Token. O ID Token é então usado pelo SP para criar uma sessão local.

**Fluxo OIDC SSO:**

```
1. Usuario -> SP: Acessa https://crm.example.com
2. SP -> Usuario: Redireciona para IdP com authorization request
3. Usuario -> IdP: Apresenta request (scope=openid profile email)
4. IdP -> Usuario: Verifica sessão existente
   - Se sessão ativa: Emite ID Token sem pedir credenciais
   - Se sessão inativa: Exibe tela de login
5. IdP -> Usuario: Redireciona para SP com authorization code
6. SP -> IdP: Troca code por tokens (server-side)
7. IdP -> SP: Retorna ID Token + Access Token + Refresh Token
8. SP: Valida ID Token e cria sessão local
```

**Implementação OIDC SSO:**

```python
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import secrets
import hashlib
import base64
import httpx
import jwt

app = FastAPI()

class OIDCSSO:
    def __init__(self, issuer: str, client_id: str, client_secret: str):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self._discovery = None

    async def get_discovery(self):
        if self._discovery is None:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.issuer}/.well-known/openid-configuration"
                )
                self._discovery = resp.json()
        return self._discovery

    async def get_jwks(self):
        discovery = await self.get_discovery()
        async with httpx.AsyncClient() as client:
            resp = await client.get(discovery["jwks_uri"])
            return resp.json()

    async def create_login_url(self, redirect_uri: str, state: str, nonce: str):
        discovery = await self.get_discovery()

        # Gerar PKCE
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = (
            f"{discovery['authorization_endpoint']}"
            f"?{requests.compat.urlencode(params)}"
        )

        return auth_url, code_verifier

    async def exchange_code(self, code: str, code_verifier: str,
                            redirect_uri: str):
        discovery = await self.get_discovery()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                discovery["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code_verifier": code_verifier
                }
            )
            return resp.json()

    async def validate_id_token(self, id_token: str, nonce: str):
        # Decodificar header
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")

        # Obter chave pública
        jwks = await self.get_jwks()
        key = None
        for jwk in jwks.get("keys", []):
            if jwk["kid"] == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise ValueError(f"Key not found: {kid}")

        # Validar
        payload = jwt.decode(
            id_token, key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer
        )

        # Verificar nonce
        if payload.get("nonce") != nonce:
            raise ValueError("Nonce mismatch")

        return payload

sso = OIDCSSO(
    issuer="https://auth.example.com",
    client_id="my-spa",
    client_secret=None  # SPA = client público
)

@app.get("/login")
async def login(request: Request):
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)

    request.session["state"] = state
    request.session["nonce"] = nonce

    auth_url, code_verifier = await sso.create_login_url(
        redirect_uri=str(request.url_for("callback")),
        state=state,
        nonce=nonce
    )

    request.session["pkce_verifier"] = code_verifier

    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback(request: Request, code: str, state: str):
    # Validar state
    if state != request.session.get("state"):
        return JSONResponse(
            {"error": "State mismatch"},
            status_code=403
        )

    # Trocar código
    tokens = await sso.exchange_code(
        code=code,
        code_verifier=request.session["pkce_verifier"],
        redirect_uri=str(request.url_for("callback"))
    )

    # Validar ID Token
    id_token_claims = await sso.validate_id_token(
        tokens["id_token"],
        request.session["nonce"]
    )

    # Criar sessão
    request.session["user_id"] = id_token_claims["sub"]
    request.session["user_info"] = {
        "email": id_token_claims.get("email"),
        "name": id_token_claims.get("name"),
    }

    return RedirectResponse(url="/dashboard")
```

### 6.3.2 SSO com múltiplos SPs usando OIDC

Quando múltiplos SPs usam o mesmo IdP OIDC, o SSO funciona naturalmente — o IdP mantém uma sessão do usuário e emite tokens para cada SP sem solicitar reautenticação.

```python
class MultiSPSSOManager:
    def __init__(self, oidc_provider):
        self.provider = oidc_provider
        self.registered_sps = {}

    def register_sp(self, sp_id: str, redirect_uris: list):
        """Registrar um Service Provider."""
        self.registered_sps[sp_id] = {
            "redirect_uris": redirect_uris,
            "sessions": {}  # sp_session_id -> user_info
        }

    async def handle_sp_request(self, sp_id: str, redirect_uri: str):
        """SP solicita autenticação."""
        if sp_id not in self.registered_sps:
            raise ValueError(f"Unknown SP: {sp_id}")

        # Verificar se usuário já tem sessão ativa
        existing_session = self._get_active_session(sp_id)
        if existing_session:
            # SSO — usuário já autenticado
            # Emitir novo ID Token para este SP
            return await self._issue_token_for_sp(
                sp_id, redirect_uri, existing_session
            )

        # Primeira vez — redirecionar para IdP
        return await self._initiate_auth(sp_id, redirect_uri)

    def _get_active_session(self, sp_id: str):
        """Verificar se há sessão ativa para o SP."""
        sp = self.registered_sps.get(sp_id)
        if sp:
            for session_id, session_data in sp["sessions"].items():
                if self._is_session_valid(session_data):
                    return session_data
        return None

    async def _initiate_auth(self, sp_id: str, redirect_uri: str):
        """Iniciar novo fluxo de autenticação."""
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        # Armazenar contexto
        session_data = {
            "sp_id": sp_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "pkce_verifier": secrets.token_urlsafe(32)
        }

        # Gerar URL de autorização
        auth_url = await self.provider.create_login_url(
            redirect_uri=redirect_uri,
            state=state,
            nonce=nonce
        )

        return auth_url, session_data

    async def _issue_token_for_sp(self, sp_id: str, redirect_uri: str,
                                   session_data: dict):
        """Emitir token para um SP quando o usuário já está autenticado."""
        # Criar novo authorization code para este SP
        code = secrets.token_urlsafe(32)

        # Armazenar code com referência à sessão existente
        await self.provider.store_auth_code(
            code=code,
            client_id=sp_id,
            redirect_uri=redirect_uri,
            user_id=session_data["user_id"],
            nonce=session_data["nonce"]
        )

        # Redirecionar com code
        return f"{redirect_uri}?code={code}&state={session_data['state']}"
```

---

## 6.4 SAML vs OIDC — Comparação Detalhada

### 6.4.1 Comparação técnica

| Critério | SAML 2.0 | OIDC |
|---|---|---|
| **Ano de publicação** | 2005 | 2014 |
| **Base** | XML | JSON/JWT |
| **Protocolo base** | HTTP + SOAP | HTTP + REST |
| **Formato de tokens** | XML Assertions | JWT (JSON) |
| **Tamanho dos tokens** | Grande (XML verbose) | Pequeno (JSON compacto) |
| **Assinatura** | XML-DSig (complexo) | JWS (simples) |
| **Criptografia** | XML-Enc | JWE (opcional) |
| **Discovery** | Metadata XML | .well-known/openid-configuration |
| **Client Registration** | Manual (metadata exchange) | Dynamic (RFC 7591) |
| **Mobilidade** | Difícil (XML processing) | Nativa (JSON) |
| **APIs** | SOAP-based (ECP) | RESTful |
| **Single Logout** | Sim (SAML SLO) | Sim (back-channel, front-channel) |
| **Session Management** | Limitado | Especificado |
| **PKCE** | Não aplicável | Suportado |
| **Token Lifetime** | Curto (configurável) | Curto (configurável) |
| **Refresh Token** | Não | Sim |
| **MFA** | Via AuthnContext | Via ACR/AMR claims |
| **Federated Identity** | Nativo | Via OIDC Federation |
| **Complexidade de implementação** | Alta (XML processing) | Média (JSON processing) |

### 6.4.2 Quando usar SAML

SAML é a escolha preferida quando:

- **Infraestrutura legada**: Organizações com investimento em infraestrutura SAML existente (ADFS, Shibboleth, etc.)
- **Requisitos regulatórios**: Alguns setores regulados (governo, educação, saúde) ainda exigem SAML
- **Enterprise SSO maduro**: Ambientes corporativos onde SAML já está consolidado
- **Integração com diretórias**: Deep integration com Active Directory e LDAP
- **Complexidade de atributos**: Quando é necessário transportar atributos complexos ou customizados
- **Federação entre organizações**: SAML Federation é maduro e amplamente suportado

### 6.4.3 Quando usar OIDC

OIDC é a escolha preferida quando:

- **Aplicações modernas**: SPAs, mobile apps, microserviços
- **APIs RESTful**: Integração com APIs que usam tokens JWT
- **Mobilidade**: Suporte nativo a dispositivos móveis
- **Developer experience**: JSON é mais fácil de trabalhar que XML
- **Consumidores**: Aplicações B2C com milhões de usuários
- **Cloud-native**: Integração com serviços cloud (AWS, Azure, GCP)
- **Futuro**: OIDC é o padrão emergente; SAML é considerado legacy

### 6.4.4 Migração de SAML para OIDC

Muitas organizações estão migrando gradualmente de SAML para OIDC. A migração pode ser incremental:

```python
class HybridSSOProxy:
    """Proxy que suporta tanto SAML quanto OIDC."""

    def __init__(self, saml_idp, oidc_provider):
        self.saml_idp = saml_idp
        self.oidc_provider = oidc_provider
        self.sp_protocols = {}  # sp_id -> "saml" ou "oidc"

    async def authenticate(self, sp_id: str):
        protocol = self.sp_protocols.get(sp_id, "saml")

        if protocol == "saml":
            return await self._saml_authenticate(sp_id)
        elif protocol == "oidc":
            return await self._oidc_authenticate(sp_id)
        else:
            raise ValueError(f"Unknown protocol: {protocol}")

    async def _saml_authenticate(self, sp_id: str):
        """Autenticação via SAML."""
        authn_request = self.saml_idp.create_authn_request(sp_id)
        return RedirectResponse(
            url=f"{self.saml_idp.sso_url}?SAMLRequest={authn_request}"
        )

    async def _oidc_authenticate(self, sp_id: str):
        """Autenticação via OIDC."""
        auth_url = await self.oidc_provider.create_login_url(
            client_id=sp_id,
            redirect_uri=self._get_redirect_uri(sp_id),
            scope="openid profile email"
        )
        return RedirectResponse(url=auth_url)

    async def migrate_sp(self, sp_id: str):
        """Migrar um SP de SAML para OIDC."""
        # Registrar novo client no OIDC provider
        await self.oidc_provider.register_client(
            client_id=sp_id,
            redirect_uris=self._get_redirect_uris(sp_id)
        )

        # Atualizar protocolo
        self.sp_protocols[sp_id] = "oidc"

        # Notificar SP sobre mudança
        await self._notify_sp_migration(sp_id, "oidc")
```

---

## 6.5 Identity Providers

### 6.5.1 Keycloak

Keycloak é um IdP open-source desenvolvido pela Red Hat. É a solução open-source mais completa para SSO e gerenciamento de identidades.

**Características principais:**
- Suporta OIDC, SAML 2.0, OAuth 2.0
- User Federation (LDAP, Active Directory)
- Social Login (Google, Facebook, GitHub)
- MFA (TOTP, WebAuthn, SMS)
- Authorization Services (policy engine baseado em Atributos)
- Admin Console e Account Console
- REST API para administração
- Clustering para alta disponibilidade

**Configuração Keycloak para SSO:**

```yaml
# docker-compose.yml para Keycloak
version: '3.8'
services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KC_HTTP_RELATIVE_PATH: /auth
      KC_PROXY: edge
      KC_HOSTNAME: auth.example.com
    ports:
      - "8443:8443"
    volumes:
      - keycloak_data:/opt/keycloak/data
    command: start

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: keycloak
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  keycloak_data:
  postgres_data:
```

**Criação de realm e client via API:**

```python
import httpx

class KeycloakAdmin:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.token = self._get_admin_token(username, password)

    def _get_admin_token(self, username: str, password: str) -> str:
        response = httpx.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": username,
                "password": password
            }
        )
        return response.json()["access_token"]

    def create_realm(self, realm_name: str):
        response = httpx.post(
            f"{self.base_url}/admin/realms",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "realm": realm_name,
                "enabled": True,
                "sslRequired": "external",
                "registrationAllowed": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
                "permanentLockout": False,
                "maxFailureWaitSeconds": 900,
                "minimumQuickLoginWaitSeconds": 60,
                "waitIncrementSeconds": 60,
                "quickLoginCheckMilliSeconds": 1000,
                "maxDeltaTimeSeconds": 43200,
                "failureFactor": 5,
                "passwordPolicy": "length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)"
            }
        )
        response.raise_for_status()

    def create_oidc_client(self, realm: str, client_id: str,
                           redirect_uris: list):
        response = httpx.post(
            f"{self.base_url}/admin/realms/{realm}/clients",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "clientId": client_id,
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "redirectUris": redirect_uris,
                "webOrigins": redirect_uris,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "frontchannelLogoutEnabled": True,
                "attributes": {
                    "pkce.code.challenge.method": "S256"
                }
            }
        )
        response.raise_for_status()
        return response.json()

    def create_saml_client(self, realm: str, client_id: str,
                           assertion_consumer_service_url: str):
        response = httpx.post(
            f"{self.base_url}/admin/realms/{realm}/clients",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "clientId": client_id,
                "enabled": True,
                "protocol": "saml",
                "publicClient": False,
                "attributes": {
                    "saml.assertion.signature": "true",
                    "saml.force.post.binding": "true",
                    "saml.multivalued.roles": "false",
                    "saml.onetimeuse.condition": "true",
                    "saml.server.signature.keyinfo.ext.keyUsage": "true",
                    "signing.algorithm": "RSA_SHA256"
                },
                "defaultClientScopes": [],
                "redirectUris": [],
                "webOrigins": [],
                "fullScopeAllowed": True
            }
        )
        response.raise_for_status()

        # Configurar SAML endpoints
        client_uuid = response.json()["id"]
        httpx.put(
            f"{self.base_url}/admin/realms/{realm}/clients/{client_uuid}",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "attributes": {
                    "saml.assertion.signature": "true",
                    "saml.single.logout.service.url": f"https://auth.example.com/realms/{realm}/protocol/saml/logout",
                    "saml.single.sign.on.service.url": f"https://auth.example.com/realms/{realm}/protocol/saml",
                    "saml_name_id_format": "email"
                }
            }
        )
```

### 6.5.2 Okta

Okta é uma plataforma IdP comercial (SaaS) focada em enterprise. É uma das soluções mais maduras e bem suportadas do mercado.

**Características principais:**
- OIDC, SAML 2.0, OAuth 2.0
- Universal Directory (gestão centralizada de identidades)
- Adaptive MFA (baseado em risco)
- Lifecycle Management (provisioning e deprovisioning)
- API Access Management
- Bot protection (Okta ThreatInsight)
- Integrações com 6000+ aplicativos
- SDKs para todas as plataformas

**Configuração Okta:**

```python
import okta
from okta_jwt.verifier import AccessTokenVerifier, IDTokenVerifier

class OktaSSO:
    def __init__(self, org_url: str, client_id: str, client_secret: str):
        self.org_url = org_url
        self.client_id = client_id
        self.client_secret = client_secret

        self.access_verifier = AccessTokenVerifier(
            issuer=f"{org_url}/oauth2/default",
            audience="api://default"
        )

        self.id_token_verifier = IDTokenVerifier(
            issuer=f"{org_url}/oauth2/default",
            client_id=client_id
        )

    async def validate_token(self, token: str) -> dict:
        """Validar access token do Okta."""
        return await self.access_verifier.verify(token)

    async def validate_id_token(self, id_token: str, nonce: str) -> dict:
        """Validar ID token do Okta."""
        claims = await self.id_token_verifier.verify(id_token)

        if claims.get("nonce") != nonce:
            raise ValueError("Nonce mismatch")

        return claims

    def get_authorization_url(self, redirect_uri: str, state: str,
                               nonce: str) -> str:
        """Construir URL de autorização Okta."""
        import secrets
        import hashlib
        import base64

        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        return f"{self.org_url}/oauth2/default/v1/authorize?{requests.compat.urlencode(params)}"
```

### 6.5.3 Azure AD (Entra ID)

Azure AD (agora Microsoft Entra ID) é o serviço de identidade da Microsoft, profundamente integrado ao ecossistema Microsoft 365 e Azure.

**Características principais:**
- OIDC, OAuth 2.0, SAML 2.0, WS-Federation
- Azure AD B2B (federating between organizations)
- Azure AD B2C (consumer identity)
- Conditional Access Policies
- Identity Protection (ML-based risk detection)
- Privileged Identity Management
- Integration nativa com Microsoft 365 e Azure
- Device-based access control
- Continuous Access Evaluation (CAE)

**Configuração Azure AD:**

```python
import msal
import requests

class AzureADSSO:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        self.msal_app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority
        )

    def get_authorization_url(self, redirect_uri: str, scopes: list,
                               state: str) -> str:
        """Obter URL de autorização Azure AD."""
        auth_url = self.msal_app.get_authorization_request_url(
            scopes=scopes,
            redirect_uri=redirect_uri,
            state=state,
            prompt="select_account"
        )
        return auth_url

    def acquire_token_by_code(self, code: str, scopes: list,
                               redirect_uri: str) -> dict:
        """Trocar código por token."""
        result = self.msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=scopes,
            redirect_uri=redirect_uri
        )

        if "error" in result:
            raise AzureADAuthError(result["error_description"])

        return result

    def get_user_info(self, access_token: str) -> dict:
        """Obter informações do usuário via Microsoft Graph."""
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["id"],
                "name": data.get("displayName"),
                "email": data.get("mail") or data.get("userPrincipalName"),
                "department": data.get("department"),
                "jobTitle": data.get("jobTitle"),
                "officeLocation": data.get("officeLocation")
            }

        raise AzureADAPIError(f"Failed to get user info: {response.text}")

    def validate_token(self, token: str) -> dict:
        """Validar token JWT do Azure AD."""
        # Azure AD usa JWKS do tenant
        jwks_url = (
            f"https://login.microsoftonline.com/"
            f"{self.tenant_id}/discovery/v2.0/keys"
        )

        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Obter chave pública
        jwks = requests.get(jwks_url).json()
        key = None
        for jwk in jwks.get("keys", []):
            if jwk["kid"] == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise ValueError(f"Key not found: {kid}")

        # Validar
        payload = jwt.decode(
            token, key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        )

        return payload
```

### 6.5.4 Comparação de Identity Providers

| Critério | Keycloak | Okta | Azure AD |
|---|---|---|---|
| **Tipo** | Open-source | SaaS | SaaS |
| **Preço** | Gratuito | Por usuário/mês | Por usuário/mês |
| **Deploy** | Self-hosted | Cloud only | Cloud (hybrid) |
| **OIDC** | Sim | Sim | Sim |
| **SAML** | Sim | Sim | Sim |
| **MFA** | TOTP, WebAuthn | TOTP, WebAuthn, Push, SMS | TOTP, WebAuthn, Push, SMS |
| **LDAP** | Sim (User Federation) | Sim (Directory) | Sim (Azure AD DS) |
| **Social Login** | Sim | Sim | Sim |
| **Lifecycle Mgmt** | Limitado | Completo | Completo |
| **Conditional Access** | Limitado | Completo | Completo |
| **Risk Detection** | Não | ThreatInsight | Identity Protection |
| **Integrações** | Múltiplas | 6000+ | Microsoft ecosystem |
| **Suporte** | Comunidade / Red Hat | Enterprise | Enterprise |
| **Ideal para** | DevOps, self-hosted | Enterprise SaaS | Microsoft shops |

---

## 6.6 Service Providers

Um Service Provider (SP) é qualquer aplicação que delega autenticação a um IdP. A implementação de um SP varia dependendo do protocolo (SAML ou OIDC) e do framework utilizado.

### 6.6.1 SP com OIDC

```python
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import secrets
import hashlib
import base64

app = FastAPI()

class OIDCServiceProvider:
    def __init__(self, issuer: str, client_id: str, client_secret: str,
                 redirect_uri: str):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._config = None

    async def get_config(self):
        if self._config is None:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.issuer}/.well-known/openid-configuration"
                )
                self._config = resp.json()
        return self._config

    async def authenticate(self, request: Request):
        """Iniciar autenticação OIDC."""
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        # Armazenar na sessão
        request.session["state"] = state
        request.session["nonce"] = nonce
        request.session["pkce_verifier"] = code_verifier

        # Redirect para IdP
        config = await self.get_config()
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = f"{config['authorization_endpoint']}?{requests.compat.urlencode(params)}"
        return RedirectResponse(url=auth_url)

    async def handle_callback(self, request: Request, code: str, state: str):
        """Processar callback do IdP."""
        # Validar state
        if state != request.session.get("state"):
            return JSONResponse({"error": "CSRF detected"}, status_code=403)

        config = await self.get_config()

        # Trocar código por tokens
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                config["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code_verifier": request.session["pkce_verifier"]
                }
            )

        if token_resp.status_code != 200:
            return JSONResponse({"error": "Token exchange failed"},
                              status_code=400)

        tokens = token_resp.json()

        # Validar ID Token
        id_token_claims = await self._validate_id_token(
            tokens["id_token"],
            config,
            request.session["nonce"]
        )

        # Criar sessão local
        request.session["authenticated"] = True
        request.session["user"] = {
            "sub": id_token_claims["sub"],
            "email": id_token_claims.get("email"),
            "name": id_token_claims.get("name"),
        }
        request.session["access_token"] = tokens["access_token"]
        request.session["refresh_token"] = tokens.get("refresh_token")
        request.session["token_expires_at"] = (
            time.time() + tokens.get("expires_in", 3600)
        )

        return RedirectResponse(url="/dashboard")

    async def _validate_id_token(self, id_token: str, config: dict,
                                  expected_nonce: str):
        """Validar ID Token."""
        import jwt as pyjwt

        header = pyjwt.get_unverified_header(id_token)
        kid = header.get("kid")

        # Obter JWKS
        async with httpx.AsyncClient() as client:
            jwks_resp = await client.get(config["jwks_uri"])
            jwks = jwks_resp.json()

        key = None
        for jwk in jwks.get("keys", []):
            if jwk["kid"] == kid:
                key = pyjwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise ValueError(f"Key not found: {kid}")

        claims = pyjwt.decode(
            id_token, key,
            algorithms=["RS256"],
            audience=self.client_id,
            issuer=self.issuer
        )

        if claims.get("nonce") != expected_nonce:
            raise ValueError("Nonce mismatch")

        return claims

    async def logout(self, request: Request):
        """RP-Initiated Logout."""
        id_token_hint = request.session.get("id_token_hint")
        request.session.clear()

        if id_token_hint:
            config = await self.get_config()
            logout_url = (
                f"{config.get('end_session_endpoint', '')}"
                f"?id_token_hint={id_token_hint}"
                f"&post_logout_redirect_uri={self.redirect_uri}/logged-out"
            )
            return RedirectResponse(url=logout_url)

        return RedirectResponse(url="/")

oidc_sp = OIDCServiceProvider(
    issuer="https://auth.example.com",
    client_id="my-app",
    client_secret="my-secret",
    redirect_uri="https://myapp.example.com/callback"
)

@app.get("/login")
async def login(request: Request):
    return await oidc_sp.authenticate(request)

@app.get("/callback")
async def callback(request: Request, code: str, state: str):
    return await oidc_sp.handle_callback(request, code, state)

@app.get("/logout")
async def logout(request: Request):
    return await oidc_sp.logout(request)
```

### 6.6.2 SP com SAML

```python
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
import json

class SAMLServiceProvider:
    def __init__(self, settings: dict):
        self.settings = settings

    def _prepare_request(self, request):
        """Preparar request para OneLogin."""
        return {
            "https": "on" if request.url.scheme == "https" else "off",
            "http_host": request.headers.get("host", "localhost"),
            "script_name": request.url.path,
            "server_port": request.headers.get("x-forwarded-port", "443"),
            "get_data": request.query_params,
            "post_data": request.form if request.method == "POST" else {},
        }

    def login(self, request):
        """Iniciar login SAML."""
        auth = OneLogin_Saml2_Auth(self._prepare_request(request),
                                   self.settings)
        return RedirectResponse(
            url=auth.login(return_to=str(request.url)),
            status_code=302
        )

    def process_response(self, request):
        """Processar Response do IdP."""
        auth = OneLogin_Saml2_Auth(self._prepare_request(request),
                                   self.settings)
        auth.process_response()
        errors = auth.get_errors()

        if errors:
            raise SAMLError(f"SAML error: {errors}")

        if not auth.is_authenticated():
            raise SAMLError("User not authenticated")

        # Obter atributos
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        session_index = auth.get_session_index()

        return {
            "name_id": name_id,
            "attributes": attributes,
            "session_index": session_index
        }

    def logout(self, request, name_id, session_index):
        """Iniciar logout SAML."""
        auth = OneLogin_Saml2_Auth(self._prepare_request(request),
                                   self.settings)
        return RedirectResponse(
            url=auth.logout(name_id=name_id,
                          session_index=session_index),
            status_code=302
        )

# Configuração
saml_settings = {
    "sp": {
        "entityId": "https://crm.example.com/metadata",
        "assertionConsumerService": {
            "url": "https://crm.example.com/saml/acs",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        },
        "singleLogoutService": {
            "url": "https://crm.example.com/saml/slo",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        "x509cert": "",
        "privateKey": ""
    },
    "idp": {
        "entityId": "https://idp.example.com/metadata",
        "singleSignOnService": {
            "url": "https://idp.example.com/saml/sso",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "singleLogoutService": {
            "url": "https://idp.example.com/saml/slo",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        "x509cert": "MIICpDCCAYwCCQDU+..."
    },
    "security": {
        "authnRequestsSigned": True,
        "wantAssertionsSigned": True,
        "wantMessageSigned": True,
        "wantNameId": True,
        "wantNameIdEncrypted": False,
        "signMetadata": True,
        "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
        "rejectUnsolicitedResponsesWithInResponseTo": True,
        "wantAttributeStatement": True
    }
}

saml_sp = SAMLServiceProvider(saml_settings)
```

---

## 6.7 Federação

### 6.7.1 Conceitos de Federação

Federação é o mecanismo que permite que organizações diferentes compartilhem identidades e autorizações. Em um modelo federado:

1. Cada organização mantém seu próprio Identity Provider
2. Os Identity Providers estabelecem relações de confiança entre si
3. Usuários de uma organização podem acessar serviços de outra usando suas próprias credenciais

**Exemplo**: Um funcionário da Empresa A pode acessar o portal de parceiros da Empresa B usando sua conta da Empresa A. A Empresa B confia na autenticação feita pela Empresa A.

### 6.7.2 SAML Federation

SAML Federation é o mecanismo mais maduro para federação cross-organização. Funciona através da troca e configuração manual (ou semi-automática) de metadata entre os participantes.

**Modelos de Federação SAML:**

1. **Bilateral Federation**: Duas organizações estabelecem confiança diretamente. Cada uma configura a metadata da outra.

2. **Hub-and-Spoke**: Uma entidade central (hub)Mediação entre múltiplos participantes. Cada participante confia no hub, e o hub encaminha assertions entre participantes.

3. **Federation Registry**: Um registro central de participantes que facilita a descoberta e configuração de relações de confiança. Exemplos: InCommon (educação), GÉANT (pesquisa na Europa), CAFe (Brasil).

**Implementação de Federação SAML:**

```python
class SAMLFederation:
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.trusted_idps = {}

    async def register_sp(self, sp_entity_id: str, sp_metadata: str):
        """Registrar SP no registry de federação."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.registry_url}/register/sp",
                data={
                    "entity_id": sp_entity_id,
                    "metadata": sp_metadata
                }
            )
            return resp.json()

    async def discover_idps(self):
        """Descobrir IdPs disponíveis na federação."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.registry_url}/idps")
            return resp.json()

    async def establish_trust(self, idp_entity_id: str):
        """Estabelecer relação de confiança com um IdP."""
        # Baixar metadata do IdP
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.registry_url}/idps/{idp_entity_id}/metadata"
            )
            idp_metadata = resp.json()

        # Validar metadata
        self._validate_metadata(idp_metadata)

        # Armazenar como IdP confiável
        self.trusted_idps[idp_entity_id] = {
            "metadata": idp_metadata,
            "certificate": idp_metadata["certificate"],
            "sso_url": idp_metadata["sso_url"],
            "entity_id": idp_entity_id
        }

    def _validate_metadata(self, metadata: dict):
        """Validar metadata de um IdP."""
        required_fields = [
            "entity_id", "sso_url", "certificate"
        ]
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field: {field}")

        # Validar certificado
        cert = metadata["certificate"]
        if not self._is_valid_certificate(cert):
            raise ValueError("Invalid certificate")

    def _is_valid_certificate(self, cert_pem: str) -> bool:
        """Validar certificado X.509."""
        try:
            from cryptography import x509
            x509.load_pem_x509_certificate(cert_pem.encode())
            return True
        except Exception:
            return False
```

### 6.7.3 OIDC Federation

OIDC Federation é um mecanismo mais recente e moderno para federação, baseado em trust chains e automatic metadata.

**Conceitos:**

1. **Trust Chain**: Cadeia de confiança que conecta um Entity a um Trust Anchor. Cada elo da cadeia é uma assinatura que valida o próximo.

2. **Entity Statement**: Documento JWT que descreve uma entidade e suas capacidades, assinado por sua chave privada.

3. **Federation Discovery**: As entidades descobrem umas às outras através de endpoints `.well-known/openid-federation`.

```python
class OIDCFederation:
    def __init__(self, entity_id: str, private_key: str):
        self.entity_id = entity_id
        self.private_key = private_key

    def create_entity_statement(self, subject: str, iss: str,
                                 aud: str) -> str:
        """Criar Entity Statement JWT."""
        import jwt

        payload = {
            "iss": iss,
            "sub": subject,
            "aud": aud,
            "iat": time.time(),
            "exp": time.time() + 3600,
            "jti": secrets.token_urlsafe(16),
            "metadata": {
                "openid_provider": {
                    "issuer": self.entity_id,
                    "authorization_endpoint": f"{self.entity_id}/authorize",
                    "token_endpoint": f"{self.entity_id}/token",
                    "jwks_uri": f"{self.entity_id}/.well-known/jwks.json"
                }
            },
            "trust_mark_issuer": self.entity_id
        }

        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def fetch_entity_statement(self, entity_url: str) -> dict:
        """Buscar Entity Statement de uma entidade."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{entity_url}/.well-known/openid-federation"
            )
            return resp.json()

    def validate_trust_chain(self, chain: list) -> bool:
        """Validar cadeia de confiança."""
        import jwt

        for i in range(len(chain) - 1):
            statement = chain[i]
            issuer_statement = chain[i + 1]

            # Decodificar sem validar assinatura
            unverified = jwt.decode(
                statement, options={"verify_signature": False}
            )

            # Obter chave pública do issuer
            issuer_entity = self._parse_entity_id(
                unverified["iss"]
            )

            # Validar assinatura
            try:
                jwt.decode(
                    statement,
                    issuer_entity["public_key"],
                    algorithms=["RS256"],
                    audience=issuer_entity["entity_id"]
                )
            except Exception:
                return False

        return True

    def _parse_entity_id(self, entity_id: str) -> dict:
        """Resolver entity_id para informações da entidade."""
        # Em produção, buscar do registry ou cache
        # Simplificado aqui
        return {
            "entity_id": entity_id,
            "public_key": "...",
            "metadata": {}
        }
```

---

## 6.8 Just-In-Time (JIT) Provisioning

### 6.8.1 Conceito

JIT Provisioning é o mecanismo de criar automaticamente contas de usuário no Service Provider quando o usuário faz login pela primeira vez via IdP. Em vez de pré-criar contas para cada usuário em cada SP, o SP cria a conta sob demanda com base nas informações recebidas do IdP.

### 6.8.2 Benefícios

- **Eliminação de provisioning manual**: Não é necessário criar contas manualmente em cada SP
- **Redução de custos operacionais**: Menos trabalho administrativo
- **Consistencia de dados**: Informações do usuário são sincronizadas do IdP
- **Revogação automática**: Quando um usuário é desabilitado no IdP, ele não pode mais acessar os SPs (embora JIT não cubra desprovisioning — para isso, use SCIM)

### 6.8.3 Implementação

```python
class JITProvisioning:
    def __init__(self, user_repository, attribute_mapping: dict):
        self.user_repo = user_repository
        self.mapping = attribute_mapping

    async def provision_or_update(self, idp_claims: dict) -> dict:
        """Provisionar ou atualizar usuário baseado em claims do IdP."""
        # Extrair identificador único
        external_id = idp_claims.get("sub")
        email = idp_claims.get("email")

        if not external_id:
            raise JITError("Missing 'sub' claim")

        # Verificar se usuário já existe
        user = await self.user_repo.find_by_external_id(external_id)

        if user:
            # Atualizar dados existentes
            user = await self._update_user(user, idp_claims)
        else:
            # Criar novo usuário
            user = await self._create_user(idp_claims)

        return user

    async def _create_user(self, claims: dict) -> dict:
        """Criar novo usuário."""
        # Mapear atributos do IdP para atributos locais
        user_data = self._map_attributes(claims)

        # Validações
        if not user_data.get("email"):
            raise JITError("Email is required for provisioning")

        # Verificar se email já está em uso (por outro método de login)
        existing = await self.user_repo.find_by_email(user_data["email"])
        if existing:
            # Vincular conta existente
            await self._link_accounts(existing, claims)
            return existing

        # Criar usuário
        user = await self.user_repo.create({
            "external_id": claims.get("sub"),
            "email": user_data["email"],
            "name": user_data.get("name"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "avatar_url": user_data.get("picture"),
            "locale": user_data.get("locale"),
            "idp_issuer": claims.get("iss"),
            "idp_created_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow(),
            "status": "active"
        })

        # Criar permissões iniciais baseadas em roles do IdP
        await self._assign_initial_permissions(user, claims)

        return user

    async def _update_user(self, user: dict, claims: dict) -> dict:
        """Atualizar dados do usuário existente."""
        updates = self._map_attributes(claims)
        updates["last_login_at"] = datetime.utcnow()

        # Só atualizar se houver mudanças
        changed = False
        for key, value in updates.items():
            if user.get(key) != value:
                user[key] = value
                changed = True

        if changed:
            await self.user_repo.update(user["id"], user)

        return user

    async def _link_accounts(self, existing_user: dict,
                              claims: dict):
        """Vincular conta existente com identity do IdP."""
        await self.user_repo.add_external_identity(
            user_id=existing_user["id"],
            provider=claims["iss"],
            external_id=claims["sub"],
            email=claims.get("email")
        )

    def _map_attributes(self, claims: dict) -> dict:
        """Mapear atributos do IdP para formato local."""
        result = {}
        for idp_attr, local_attr in self.mapping.items():
            if idp_attr in claims:
                result[local_attr] = claims[idp_attr]
        return result

    async def _assign_initial_permissions(self, user: dict,
                                           claims: dict):
        """Atribuir permissões iniciais baseadas em roles do IdP."""
        idp_roles = claims.get("roles", claims.get("groups", []))

        # Mapear roles do IdP para roles locais
        role_mapping = {
            "admin": ["read", "write", "delete", "admin"],
            "editor": ["read", "write"],
            "viewer": ["read"],
            "guest": ["read:limited"]
        }

        permissions = set()
        for role in idp_roles:
            if role in role_mapping:
                permissions.update(role_mapping[role])

        if permissions:
            await self.user_repo.set_permissions(
                user["id"], list(permissions)
            )
```

---

## 6.9 Gerenciamento de Sessões Cross-Domain

### 6.9.1 O problema

Em SSO, o usuário pode estar autenticado em múltiplos domínios diferentes. Gerenciar sessões nesses cenários é um dos desafios mais complexos de SSO.

**Cenário típico**:
- `auth.example.com` — Identity Provider
- `app1.example.com` — Service Provider 1
- `app2.example.org` — Service Provider 2 (domínio diferente)
- `app3.example.com` — Service Provider 3

Quando o usuário faz logout no `app1.example.com`, os outros SPs também devem ser notificados.

### 6.9.2 Estratégias

**Cookies de terceiros (Third-party cookies)**:
- O IdP define um cookie no domínio dele
- Um iframe em cada SP carrega o domínio do IdP e verifica o cookie
- **Problema**: Browsers modernos bloqueiam third-party cookies (Chrome, Firefox, Safari)

**Back-channel notification**:
- O IdP mantém uma lista de SPs autenticados
- No logout, o IdP envia notificação via HTTP POST para cada SP
- **Vantagem**: Funciona independentemente do browser
- **Desvantagem**: Requer conectividade direta IdP-SP

**Front-channel notification via iframes**:
- O IdP renderiza iframes invisíveis para cada SP no logout
- Cada iframe carrega um URL de logout no SP
- **Funciona** mesmo sem third-party cookies (o iframe é first-party para o SP)

**Session Management com PKCE e refresh tokens**:
- Cada SP mantém sua própria sessão
- O IdP mantém uma sessão central
- Logout no IdP invalida a sessão central
- SPs verificam periodicamente com o IdP se a sessão ainda está ativa

### 6.9.3 Implementação de Session Management cross-domain

```python
class CrossDomainSessionManager:
    def __init__(self, idp_url: str):
        self.idp_url = idp_url
        self.registered_sps = {}  # sp_id -> callback_url
        self.user_sessions = {}   # user_id -> set of sp_ids

    def register_sp(self, sp_id: str, callback_url: str,
                    logout_url: str):
        """Registrar SP para notificações de sessão."""
        self.registered_sps[sp_id] = {
            "callback_url": callback_url,
            "logout_url": logout_url
        }

    async def notify_login(self, user_id: str, sp_id: str):
        """Notificar que um usuário fez login em um SP."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(sp_id)

    async def notify_logout(self, user_id: str, sp_id: str):
        """Notificar logout e propagar para outros SPs."""
        if user_id not in self.user_sessions:
            return

        # Notificar todos os outros SPs
        other_sps = self.user_sessions[user_id] - {sp_id}

        for other_sp_id in other_sps:
            sp_info = self.registered_sps.get(other_sp_id)
            if sp_info:
                await self._send_logout_notification(
                    sp_info["logout_url"],
                    user_id=user_id,
                    sp_id=other_sp_id
                )

        # Limpar sessão
        del self.user_sessions[user_id]

    async def _send_logout_notification(self, logout_url: str,
                                         user_id: str, sp_id: str):
        """Enviar notificação de logout via HTTP POST."""
        import jwt

        # Criar logout token
        logout_token = jwt.encode(
            {
                "iss": self.idp_url,
                "sub": user_id,
                "aud": sp_id,
                "exp": time.time() + 300,
                "iat": time.time(),
                "jti": secrets.token_urlsafe(16),
                "events": {
                    "http://schemas.openid.net/event/backchannel-logout": {}
                }
            },
            self.idp_private_key,
            algorithm="RS256"
        )

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    logout_url,
                    data={"logout_token": logout_token},
                    timeout=10
                )
        except Exception as e:
            # Log error but don't fail — SP pode estar offline
            logging.error(
                f"Failed to notify SP {sp_id} about logout: {e}"
            )

    async def check_session(self, user_id: str, sp_id: str) -> bool:
        """Verificar se a sessão de um usuário em um SP está ativa."""
        if user_id not in self.user_sessions:
            return False
        return sp_id in self.user_sessions[user_id]
```

---

## 6.10 Considerações de Segurança

### 6.10.1 Ataques contra SSO

**Session Hijacking**: Um atacante sequestra a sessão do usuário em um SP. Mitigação: tokens de curta duração, TLS, secure cookies.

**Token Replay**: Um atacante reutiliza um token roubado. Mitigação: nonce, state, tokens one-time-use.

**IdP Impersonation**: Um atacante impersona o IdP. Mitigação: validação de certificados, metadata signing, trust chains.

**Session Fixation**: Um atacante força um session ID conhecido. Mitigação: regenerar session ID após autenticação.

**SAML Assertion Injection**: Injeção de assertions maliciosas. Mitigação: InResponseTo validation, audience restriction, validação de assinatura.

**Open Redirect**: Redirecionamento para URL maliciosa após login. Mitigação: validar redirect URIs, whitelist de domínios.

### 6.10.2 Checklist de Segurança para SSO

```
[x] TLS obrigatório em todos os endpoints
[x] Validação rigorosa de tokens/assertions
[x] Nonce e state em todos os fluxos
[x] Redirect URIs validadas (comparação exata)
[x] Tokens de curta duração
[x] Refresh tokens com rotation
[x] MFA suportado e configurável
[x] Rate limiting em endpoints de autenticação
[x] Auditoria de eventos de autenticação
[x] Logout cooperativo implementado
[x] Session management configurado
[x] Certificados com rotação programada
[x] Metadata assinada
[x] Proteção contra timing attacks
[x] Validação de audience em todos os SPs
[x] Bloqueio de contas após múltiplas falhas
[x] Monitoramento de atividade suspeita
[x] Backup de chaves criptográficas
[x] Testes de penetração regulares
```

### 6.10.3 Conformidade e Regulamentação

- **LGPD (Brasil)**: Proteção de dados pessoais; identidade é dado pessoal sensível
- **GDPR (Europa)**: Regulamentação similar com foco em consentimento
- **SOC 2**: Auditoria de controles de segurança
- **ISO 27001**: Gestão de segurança da informação
- **PCI DSS**: Para sistemas que processam dados de cartão de crédito

---

## 6.11 Implementação Completa de SSO

### 6.11.1 Arquitetura do sistema

```
                    +-------------------+
                    |  Identity Provider|
                    |  (Keycloak)       |
                    |  auth.example.com |
                    +--------+----------+
                             |
                    +--------+----------+
                    |  Federation Layer |
                    |  (SAML + OIDC)    |
                    +--------+----------+
                             |
          +------------------+------------------+
          |                  |                  |
+---------+-------+ +-------+---------+ +------+--------+
|  CRM             | |  ERP             | |  Portal        |
|  crm.example.com | |  erp.example.com | |  portal.example|
|  (OIDC SP)       | |  (SAML SP)       | |  (OIDC SP)     |
+------------------+ +------------------+ +-----------------+
```

### 6.11.2 Deploy com Docker Compose

```yaml
version: '3.8'

services:
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
      KC_DB_USERNAME: keycloak
      KC_DB_PASSWORD: ${KC_DB_PASSWORD}
      KC_HOSTNAME: auth.example.com
      KC_HTTPS_CERTIFICATE_FILE: /certs/tls.crt
      KC_HTTPS_CERTIFICATE_KEY_FILE: /certs/tls.key
      KC_PROXY: edge
      KC_HEALTH_ENABLED: "true"
      KC_METRICS_ENABLED: "true"
    ports:
      - "443:8443"
    volumes:
      - ./certs:/certs:ro
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "https://localhost:8443/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: keycloak
      POSTGRES_USER: keycloak
      POSTGRES_PASSWORD: ${KC_DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak"]
      interval: 10s
      timeout: 5s
      retries: 5

  crm-app:
    build: ./crm-app
    environment:
      OIDC_ISSUER: https://auth.example.com/realms/crm-realm
      OIDC_CLIENT_ID: crm-client
      OIDC_CLIENT_SECRET: ${CRM_CLIENT_SECRET}
      OIDC_REDIRECT_URI: https://crm.example.com/callback
    ports:
      - "8080:8080"

  erp-app:
    build: ./erp-app
    environment:
      SAML_IDP_METADATA_URL: https://auth.example.com/realms/erp-realm/saml/descriptor
      SAML_SP_ENTITY_ID: https://erp.example.com/metadata
      SAML_SP_ACS_URL: https://erp.example.com/saml/acs
    ports:
      - "8081:8081"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/certs:ro
    depends_on:
      - keycloak
      - crm-app
      - erp-app

volumes:
  postgres_data:
```

### 6.11.3 Nginx Reverse Proxy

```nginx
upstream keycloak {
    server keycloak:8443;
}

upstream crm {
    server crm-app:8080;
}

upstream erp {
    server erp-app:8081;
}

server {
    listen 80;
    server_name auth.example.com crm.example.com erp.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name auth.example.com;

    ssl_certificate /certs/auth.example.com.crt;
    ssl_certificate_key /certs/auth.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass https://keycloak;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name crm.example.com;

    ssl_certificate /certs/crm.example.com.crt;
    ssl_certificate_key /certs/crm.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://crm;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name erp.example.com;

    ssl_certificate /certs/erp.example.com.crt;
    ssl_certificate_key /certs/erp.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://erp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6.11.4 Script de Setup

```bash
#!/bin/bash
set -euo pipefail

echo "=== Configurando SSO com Keycloak ==="

# Gerar senhas seguras
KC_DB_PASSWORD=$(openssl rand -base64 32)
CRM_CLIENT_SECRET=$(openssl rand -base64 32)

# Salvar em .env
cat > .env << EOF
KC_DB_PASSWORD=${KC_DB_PASSWORD}
CRM_CLIENT_SECRET=${CRM_CLIENT_SECRET}
EOF

# Iniciar serviços
docker-compose up -d postgres keycloak

echo "Aguardando Keycloak iniciar..."
sleep 30

# Configurar realm e clients
python3 scripts/setup_keycloak.py \
    --realm crm-realm \
    --crm-client-secret "${CRM_CLIENT_SECRET}" \
    --erp-realm erp-realm

echo "=== SSO Configurado com sucesso ==="
echo "Keycloak: https://auth.example.com"
echo "CRM: https://crm.example.com"
echo "ERP: https://erp.example.com"
```

---

## 6.12 Caso de Estudo: SSO e o Misantropi4

### 6.12.1 Como SSO teria protegido o IDAP

O ataque Misantropi4 explorou a ausência de mecanismos centralizados de controle de acesso. Se o IDAP tivesse implementado SSO com as seguintes características, o ataque teria sido significativamente mitigado:

**SSO com MFA centralizado**: Todos os logins passariam por um IdP que exigiria MFA. Credenciais de username/password sozinhas seriam insuficientes.

**Rate limiting centralizado**: O IdP implementaria rate limiting robusto — bloqueio progressivo de IPs, contas, e dispositivos após múltiplas tentativas falhas.

**Detecção de anomalias**: O IdP poderia detectar padrões de credential stuffing (múltiplos logins falhos de IPs diferentes, logins de geolocalização incomum, acesso fora do horário comercial) e bloquear automaticamente.

**Session management**: Quando o ataque fosse detectado, o IdP poderia forçar logout de todas as sessões ativas, imediatamente invalidando acessos comprometidos.

**JIT Provisioning com SCIM**: Quando um funcionário fosse desligado, sua conta seria automaticamente desabilitada em todos os SPs, eliminando contas órfãs que poderiam ser exploradas.

**Auditoria centralizada**: Todas as tentativas de autenticação seriam logadas em um local centralizado, facilitando detecção e investigação.

### 6.12.2 Plano de implementação recomendado

Para organizações governamentais similares ao IDAP:

1. **Fase 1 — IdP Centralizado**: Implementar Keycloak ou solução equivalente como ponto central de autenticação
2. **Fase 2 — MFA**: Configurar MFA obrigatória (TOTP + WebAuthn como segunda camada)
3. **Fase 3 — SSO**: Integrar todos os sistemas existentes ao IdP via OIDC ou SAML
4. **Fase 4 — Monitoring**: Implementar monitoramento avançado com detecção de anomalias
5. **Fase 5 — Lifecycle**: Implementar provisioning e deprovisioning automático via SCIM
6. **Fase 6 — Federation**: Se necessário, implementar federação com outros órgãos

---

## 6.13 Referências

- SAML 2.0 Core Specification (OASIS)
- SAML 2.0 Bindings (OASIS)
- SAML 2.0 Profiles (OASIS)
- OpenID Connect Core 1.0
- OpenID Connect Discovery 1.0
- OpenID Connect Session Management 1.0
- SCIM 2.0 (System for Cross-domain Identity Management)
- RFC 7591 — OAuth 2.0 Dynamic Client Registration
- RFC 8414 — OAuth 2.0 Authorization Server Metadata
- Keycloak Documentation
- Okta Developer Documentation
- Microsoft Entra ID Documentation
- OWASP Single Sign-On Cheat Sheet
- NIST SP 800-63C — Digital Identity Guidelines (Federation)
- Kantara Initiative — Federation Specifications
- InCommon Federation Documentation
- GÉANT eduGAIN Federation

---

## 6.14 SCIM — System for Cross-domain Identity Management

SCIM (RFC 7643, 7644) é o protocolo padrão para provisioning e deprovisioning automático de identidades entre sistemas. Enquanto JIT provisioning cria contas sob demanda, SCIM mantém sincronização contínua entre o IdP e os SPs.

### 6.14.1 Por que SCIM é necessário

JIT provisioning resolve a criação de contas, mas não resolve:
- **Atualização de dados**: Quando o nome ou cargo de um usuário muda no IdP, a mudança deve ser propagada para todos os SPs
- **Desabilitação de contas**: Quando um funcionário é desligado, sua conta deve ser desabilitada em todos os SPs
- **Remoção de atributos**: Quando uma permissão é removida, ela deve ser removida nos SPs
- **Sincronização de grupos**: Mudanças em grupos e roles devem ser refletidas nos SPs

SCIM resolve isso com um protocolo RESTful padronizado para CRUD de identidades.

### 6.14.2 Recursos SCIM

SCIM define os seguintes recursos:

**User Resource:**

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "id": "user-12345",
  "externalId": "idp-user-67890",
  "userName": "joao.silva@example.com",
  "name": {
    "formatted": "João da Silva",
    "familyName": "da Silva",
    "givenName": "João"
  },
  "displayName": "João da Silva",
  "emails": [
    {
      "value": "joao@example.com",
      "type": "work",
      "primary": true
    }
  ],
  "phoneNumbers": [
    {
      "value": "+5511999998888",
      "type": "mobile"
    }
  ],
  "active": true,
  "groups": [
    {
      "value": "group-admins",
      "$ref": "https://scim.example.com/Groups/group-admins",
      "display": "Administrators"
    }
  ],
  "locale": "pt-BR",
  "timezone": "America/Sao_Paulo"
}
```

**Group Resource:**

```json
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
  "id": "group-admins",
  "externalId": "idp-group-admins",
  "displayName": "Administrators",
  "members": [
    {
      "value": "user-12345",
      "$ref": "https://scim.example.com/Users/user-12345",
      "display": "João da Silva"
    }
  ]
}
```

### 6.14.3 Implementação do SCIM Server

```python
from fastapi import FastAPI, HTTPException, Request, Query
from typing import Optional

app = FastAPI()

class SCIMServer:
    def __init__(self, user_store, group_store):
        self.users = user_store
        self.groups = group_store

    async def list_users(
        self,
        filter_query: Optional[str] = None,
        startIndex: int = 1,
        count: int = 100
    ) -> dict:
        """Listar usuários com paginação e filtro."""
        if filter_query:
            users = await self._apply_filter(filter_query)
        else:
            users = await self.users.list_all()

        # Paginação
        total = len(users)
        start = startIndex - 1  # SCIM é 1-indexed
        end = min(start + count, total)
        page = users[start:end]

        return {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": total,
            "startIndex": startIndex,
            "itemsPerPage": count,
            "Resources": [
                self._format_user(user) for user in page
            ]
        }

    async def get_user(self, user_id: str) -> dict:
        """Obter usuário por ID."""
        user = await self.users.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return self._format_user(user)

    async def create_user(self, user_data: dict) -> dict:
        """Criar novo usuário."""
        # Validar schema
        if "urn:ietf:params:scim:schemas:core:2.0:User" not in user_data.get("schemas", []):
            raise HTTPException(status_code=400, detail="Invalid schema")

        # Extrair dados
        user = {
            "external_id": user_data.get("externalId"),
            "username": user_data["userName"],
            "name": {
                "formatted": user_data.get("name", {}).get("formatted"),
                "family_name": user_data.get("name", {}).get("familyName"),
                "given_name": user_data.get("name", {}).get("givenName")
            },
            "emails": [
                {"value": e["value"], "type": e.get("type", "work"), "primary": e.get("primary", False)}
                for e in user_data.get("emails", [])
            ],
            "active": user_data.get("active", True),
            "locale": user_data.get("locale"),
            "timezone": user_data.get("timezone")
        }

        # Criar no store
        created = await self.users.create(user)

        # Atribuir a grupos
        if "groups" in user_data:
            for group_ref in user_data["groups"]:
                await self.groups.add_member(
                    group_ref["value"], created["id"]
                )

        return self._format_user(created)

    async def update_user(self, user_id: str, user_data: dict) -> dict:
        """Atualizar usuário (PATCH ou PUT)."""
        existing = await self.users.find_by_id(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        # Atualizar campos
        if "userName" in user_data:
            existing["username"] = user_data["userName"]

        if "name" in user_data:
            existing["name"].update(user_data["name"])

        if "active" in user_data:
            existing["active"] = user_data["active"]
            # Se desabilitado, desabilitar em todos os SPs
            if not user_data["active"]:
                await self._deactivate_all_sessions(user_id)

        if "emails" in user_data:
            existing["emails"] = user_data["emails"]

        # Salvar
        updated = await self.users.update(user_id, existing)

        # Notificar SPs sobre mudança
        await self._notify_change(user_id, "update", updated)

        return self._format_user(updated)

    async def delete_user(self, user_id: str) -> None:
        """Deletar usuário."""
        user = await self.users.find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Remover de todos os grupos
        await self.groups.remove_user_from_all_groups(user_id)

        # Deletar usuário
        await self.users.delete(user_id)

        # Notificar SPs sobre remoção
        await self._notify_change(user_id, "delete", None)

    async def _apply_filter(self, filter_query: str) -> list:
        """Aplicar filtro SCIM (suporte básico)."""
        # Parse filter: eq, co, sw, ew
        import re

        match = re.match(r'(\w+)\s+(eq|co|sw|ew)\s+"([^"]+)"', filter_query)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid filter")

        attribute, operator, value = match.groups()

        all_users = await self.users.list_all()
        result = []

        for user in all_users:
            user_value = self._get_attribute(user, attribute)
            if user_value is None:
                continue

            if operator == "eq" and user_value == value:
                result.append(user)
            elif operator == "co" and value in user_value:
                result.append(user)
            elif operator == "sw" and user_value.startswith(value):
                result.append(user)
            elif operator == "ew" and user_value.endswith(value):
                result.append(user)

        return result

    def _format_user(self, user: dict) -> dict:
        """Formatar usuário para SCIM response."""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user["id"],
            "externalId": user.get("external_id"),
            "userName": user["username"],
            "name": {
                "formatted": user.get("name", {}).get("formatted"),
                "familyName": user.get("name", {}).get("family_name"),
                "givenName": user.get("name", {}).get("given_name")
            },
            "emails": user.get("emails", []),
            "active": user.get("active", True),
            "locale": user.get("locale"),
            "timezone": user.get("timezone")
        }

# Endpoints SCIM
scim = SCIMServer(user_store, group_store)

@app.get("/scim/v2/Users")
async def list_users(
    filter: Optional[str] = Query(None),
    startIndex: int = Query(1),
    count: int = Query(100)
):
    return await scim.list_users(filter, startIndex, count)

@app.get("/scim/v2/Users/{user_id}")
async def get_user(user_id: str):
    return await scim.get_user(user_id)

@app.post("/scim/v2/Users")
async def create_user(request: Request):
    data = await request.json()
    return await scim.create_user(data)

@app.put("/scim/v2/Users/{user_id}")
async def update_user(user_id: str, request: Request):
    data = await request.json()
    return await scim.update_user(user_id, data)

@app.delete("/scim/v2/Users/{user_id}")
async def delete_user(user_id: str):
    await scim.delete_user(user_id)
    return Response(status_code=204)

@app.get("/scim/v2/Groups")
async def list_groups(
    filter: Optional[str] = Query(None),
    startIndex: int = Query(1),
    count: int = Query(100)
):
    return await scim.groups.list_all(filter, startIndex, count)

@app.post("/scim/v2/Groups")
async def create_group(request: Request):
    data = await request.json()
    return await scim.groups.create(data)
```

### 6.14.4 Implementação do SCIM Client (Service Provider)

```python
class SCIMClient:
    def __init__(self, scim_url: str, auth_token: str):
        self.scim_url = scim_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/scim+json",
            "Accept": "application/scim+json"
        }

    async def provision_user(self, user_data: dict) -> dict:
        """Provisionar usuário via SCIM."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.scim_url}/Users",
                json=user_data,
                headers=self.headers
            )

            if response.status_code == 201:
                return response.json()
            elif response.status_code == 409:
                # Usuário já existe — atualizar
                existing = response.json()
                return await self.update_user(
                    existing["id"], user_data
                )
            else:
                raise SCIMError(
                    f"Provisioning failed: {response.status_code}"
                )

    async def update_user(self, user_id: str, user_data: dict) -> dict:
        """Atualizar usuário via SCIM."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.scim_url}/Users/{user_id}",
                json=user_data,
                headers=self.headers
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise SCIMError(
                    f"Update failed: {response.status_code}"
                )

    async def deprovision_user(self, user_id: str) -> None:
        """Desabilitar usuário via SCIM (soft delete)."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.scim_url}/Users/{user_id}",
                json={
                    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
                    "Operations": [
                        {
                            "op": "replace",
                            "path": "active",
                            "value": False
                        }
                    ]
                },
                headers=self.headers
            )

            if response.status_code not in (200, 204):
                raise SCIMError(
                    f"Deprovisioning failed: {response.status_code}"
                )

    async def sync_users(self) -> dict:
        """Sincronizar todos os usuários do IdP."""
        users = []
        startIndex = 1
        count = 100

        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.scim_url}/Users",
                    params={"startIndex": startIndex, "count": count},
                    headers=self.headers
                )

            if response.status_code != 200:
                raise SCIMError("Sync failed")

            data = response.json()
            users.extend(data.get("Resources", []))

            total = data.get("totalResults", 0)
            if startIndex + count > total:
                break
            startIndex += count

        return {
            "total": len(users),
            "users": users
        }
```

---

## 6.15 Padrões de Segurança Avançados

### 6.15.1 Zero Trust Architecture com SSO

Zero Trust é um modelo de segurança que assume que NENHUMA rede, dispositivo, ou usuário é inerentemente confiável. Cada acesso deve ser verificado, independentemente de sua origem.

**Integração de SSO com Zero Trust:**

```python
class ZeroTrustSSO:
    def __init__(self, idp, policy_engine, risk_engine):
        self.idp = idp
        self.policies = policy_engine
        self.risk = risk_engine

    async def evaluate_access(self, user_id: str, resource: str,
                               context: dict) -> dict:
        """Avaliar acesso sob modelo Zero Trust."""
        # 1. Verificar autenticação
        auth_status = await self.idp.verify_authentication(user_id)
        if not auth_status.is_authenticated:
            return {"allowed": False, "reason": "not_authenticated"}

        # 2. Avaliar risco
        risk_score = await self.risk.assess_risk(
            user_id=user_id,
            resource=resource,
            ip_address=context.get("ip"),
            device_id=context.get("device_id"),
            geolocation=context.get("geo"),
            timestamp=datetime.utcnow()
        )

        # 3. Verificar políticas
        policy_decision = await self.policies.evaluate(
            user_id=user_id,
            resource=resource,
            risk_score=risk_score,
            context=context
        )

        # 4. Decisão final
        if not policy_decision.allowed:
            return {
                "allowed": False,
                "reason": policy_decision.reason,
                "action": "block"
            }

        # 5. Concessão com restrições
        return {
            "allowed": True,
            "session_lifetime": self._calculate_lifetime(risk_score),
            "required_claims": policy_decision.required_claims,
            "mfa_required": risk_score > 0.7,
            "step_up_auth": risk_score > 0.5
        }

    def _calculate_lifetime(self, risk_score: float) -> int:
        """Calcular tempo de sessão baseado no risco."""
        if risk_score > 0.8:
            return 300   # 5 minutos
        elif risk_score > 0.5:
            return 1800  # 30 minutos
        elif risk_score > 0.3:
            return 3600  # 1 hora
        else:
            return 7200  # 2 horas
```

### 6.15.2 Conditional Access Policies

Conditional Access é um mecanismo que aplica regras baseadas em contexto para decidir se concede, nega, ou exige autenticação adicional.

```python
class ConditionalAccessEngine:
    def __init__(self):
        self.policies = []

    def add_policy(self, policy: dict):
        """Adicionar política de acesso condicional."""
        self.policies.append(policy)

    async def evaluate(self, context: dict) -> dict:
        """Avaliar todas as políticas contra o contexto."""
        results = []

        for policy in self.policies:
            if self._matches_conditions(policy, context):
                result = {
                    "policy": policy["name"],
                    "action": policy["action"],
                    "controls": policy.get("controls", [])
                }
                results.append(result)

        # Determinar decisão final (política mais restritiva vence)
        if any(r["action"] == "block" for r in results):
            return {"decision": "block", "reasons": results}

        if any(r["action"] == "require_mfa" for r in results):
            controls = []
            for r in results:
                if r["action"] == "require_mfa":
                    controls.extend(r["controls"])
            return {"decision": "require_mfa", "controls": controls}

        if any(r["action"] == "grant_with_restrictions" for r in results):
            return {"decision": "grant_with_restrictions", "results": results}

        return {"decision": "grant"}

    def _matches_conditions(self, policy: dict, context: dict) -> bool:
        """Verificar se o contexto corresponde às condições da política."""
        conditions = policy.get("conditions", {})

        # Verificar cada condição
        for key, expected in conditions.items():
            actual = context.get(key)

            if actual is None:
                return False

            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, dict):
                if "includes" in expected:
                    if actual not in expected["includes"]:
                        return False
                if "excludes" in expected:
                    if actual in expected["excludes"]:
                        return False
            else:
                if actual != expected:
                    return False

        return True

# Exemplo de políticas
engine = ConditionalAccessEngine()

# Bloquear acesso de fora do país
engine.add_policy({
    "name": "block_outside_country",
    "conditions": {
        "geo_country": {"excludes": ["BR"]}
    },
    "action": "block"
})

# Exigir MFA para acessos sensíveis
engine.add_policy({
    "name": "mfa_for_sensitive",
    "conditions": {
        "resource_class": "sensitive"
    },
    "action": "require_mfa",
    "controls": ["totp", "webauthn"]
})

# Sessão curta para dispositivos não gerenciados
engine.add_policy({
    "name": "short_session_unmanaged",
    "conditions": {
        "device_managed": False
    },
    "action": "grant_with_restrictions",
    "session_lifetime": 1800
})
```

### 6.15.3 Continuous Access Evaluation (CAE)

CAE é um mecanismo que permite ao IdP revogar acessos em tempo real, sem depender da expiração natural dos tokens. O IdP pode notificar os SPs sobre mudanças de estado do usuário imediatamente.

```python
class ContinuousAccessEvaluation:
    def __init__(self, idp_url: str):
        self.idp_url = idp_url
        self.registered_sps = {}  # sp_id -> webhook_url

    def register_sp(self, sp_id: str, webhook_url: str):
        """Registrar SP para notificações CAE."""
        self.registered_sps[sp_id] = webhook_url

    async def evaluate_and_notify(self, event: dict):
        """Avaliar evento e notificar SPs afetados."""
        user_id = event.get("user_id")
        event_type = event.get("type")

        # Determinar quais SPs são afetados
        affected_sps = await self._find_affected_sps(user_id)

        # Enviar notificações
        for sp_id, webhook_url in affected_sps.items():
            await self._send_cae_notification(
                webhook_url=webhook_url,
                event_type=event_type,
                user_id=user_id,
                event_details=event
            )

    async def _send_cae_notification(
        self, webhook_url: str, event_type: str,
        user_id: str, event_details: dict
    ):
        """Enviar notificação CAE via webhook."""
        notification = {
            "iss": self.idp_url,
            "iat": int(time.time()),
            "jti": secrets.token_urlsafe(16),
            "event_type": event_type,
            "user_id": user_id,
            "details": event_details
        }

        # Assinar notificação
        signed_notification = jwt.encode(
            notification,
            IDP_PRIVATE_KEY,
            algorithm="RS256"
        )

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook_url,
                    json={"notification": signed_notification},
                    timeout=10
                )
        except Exception as e:
            logging.error(
                f"CAE notification failed for {webhook_url}: {e}"
            )

    async def _find_affected_sps(self, user_id: str) -> dict:
        """Encontrar SPs com sessões ativas para o usuário."""
        # Em produção, consultar banco de sessões
        # Simplificado aqui
        affected = {}
        for sp_id, webhook_url in self.registered_sps.items():
            if await self._user_has_active_session(user_id, sp_id):
                affected[sp_id] = webhook_url
        return affected
```

---

## 6.16 Referências Adicionais

- RFC 7643 — SCIM Core Schema
- RFC 7644 — SCIM Protocol
- RFC 8414 — OAuth 2.0 Authorization Server Metadata
- RFC 9207 — OAuth 2.0 Authorization Server Issuer Identification
- NIST SP 800-63C — Digital Identity Guidelines
- Zero Trust Architecture (NIST SP 800-207)
- Kantara Initiative — Federation Standards
- IEEE 802.1AR — DevID (Device Identity)
- Trusted Computing Group — TPM Standards
- OpenID Foundation — Shared Signals Framework
- CAEP — Continuous Access Evaluation Protocol
- SCIM Provisioning Profile

---

## Resumo

Single Sign-On é uma arquitetura fundamental para segurança e experiência do usuário em ambientes corporativos. Este capítulo cobriu:

- **Conceitos de SSO**: O problema que resolve, modelo de atores, tipos de SSO
- **SAML 2.0**: Assertions, assinatura digital, bindings, profiles, metadata
- **OIDC-based SSO**: Fluxo OIDC SSO, SSO com múltiplos SPs
- **SAML vs OIDC**: Comparação detalhada com recomendações de uso
- **Identity Providers**: Keycloak, Okta, Azure AD — características, configuração, comparação
- **Service Providers**: Implementação com OIDC e SAML
- **Federação**: SAML Federation, OIDC Federation, trust chains
- **JIT Provisioning**: Criação automática de contas baseada em claims do IdP
- **Session Management cross-domain**: Estratégias e implementação
- **Segurança**: Ataques, mitigações, checklist de conformidade
- **Implementação completa**: Arquitetura, Docker Compose, Nginx, scripts de setup
- **Caso Misantropi4**: Lições de como SSO teria protegido o IDAP
- **SCIM**: Provisioning e deprovisioning automático de identidades
- **Zero Trust**: Integração de SSO com modelo Zero Trust
- **Conditional Access**: Políticas de acesso baseadas em contexto
- **Continuous Access Evaluation**: Revogação em tempo real

Com estes três capítulos (OAuth 2.0, OpenID Connect, e SSO), o Livro 10 oferece uma cobertura completa de autenticação, autorização e controle de acesso, desde fundamentos até implementação prática, com sempre o foco na perspectiva de segurança que o projeto DevSecurity demanda.
