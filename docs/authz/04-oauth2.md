# Capítulo 4 — OAuth 2.0

## Introdução

OAuth 2.0 é o padrão de autorização mais amplamente adotado na internet moderna. Publicado como RFC 6749 em outubro de 2012, ele substituiu o OAuth 1.0 (RFC 5849) ao introduzir um modelo mais flexível e simplificado para delegação de acesso a recursos protegidos. Diferentemente de protocolos de autenticação, o OAuth 2.0 é estritamente um protocolo de **autorização**: ele permite que um aplicativo obtenha acesso limitado a recursos de um servidor em nome de um usuário, sem expor as credenciais desse usuário ao aplicativo cliente.

A relevância do OAuth 2.0 no contexto de segurança moderna é impossível de superestimar. Todo serviço que integra login com Google, GitHub, Facebook ou qualquer outro provedor de identidade está, por baixo dos panos, utilizando OAuth 2.0 (ou seu derivado, o OpenID Connect). A falha em implementar corretamente este protocolo pode levar a exposição de dados sensíveis, sequestro de contas, e violações de privacidade em escala massiva.

O caso Misantropi4 contra o IDAP (Instituto de Identificação Digital do Brasil) demonstra como a ausência de mecanismos robustos de autenticação — incluindo MFA e controle de acesso baseado em tokens — pode resultar em comprometimento massivo de credenciais. Embora o Misantropi4 tenha se baseado primariamente em credential stuffing, um sistema que utilizasse OAuth 2.0 com PKCE, refresh tokens revogáveis e scopes granulares teria significativamente reduzido a superfície de ataque disponível aos adversários.

Este capítulo cobre os fundamentos do OAuth 2.0 em profundidade, desde os fluxos básicos até considerações avançadas de segurança, implementação em Python e Node.js, e vulnerabilidades conhecidas.

---

## 4.1 Fundamentos do OAuth 2.0

### 4.1.1 O modelo de atores

O OAuth 2.0 define quatro papéis fundamentais:

1. **Resource Owner** (Proprietário do Recurso): A entidade — tipicamente um usuário humano — que possui os dados protegidos e pode conceder acesso a eles. O Resource Owner é quem autoriza o Client a acessar seus recursos.

2. **Client** (Aplicativo Cliente): A aplicação que deseja acessar os recursos protegidos em nome do Resource Owner. O Client pode ser uma aplicação web, mobile, desktop ou até mesmo um serviço backend. O Client deve ser registrado previamente no Authorization Server para obter seus identificadores (client_id e, opcionalmente, client_secret).

3. **Authorization Server** (Servidor de Autorização): O servidor que autentica o Resource Owner e emite tokens de acesso após obter a autorização adequada. Este servidor é responsável por validar as credenciais do usuário, aplicar políticas de autorização (incluindo MFA quando configurado), e gerenciar o ciclo de vida dos tokens emitidos.

4. **Resource Server** (Servidor de Recursos): O servidor que hospeda os recursos protegidos. Ele aceita e valida tokens de acesso emitidos pelo Authorization Server para autorizar o acesso aos recursos. O Resource Server deve validar o token recebido — verificar assinatura, expiração, scopes, e audience.

### 4.1.2 O fluxo básico

A interação padrão segue este padrão:

1. O Client redireciona o Resource Owner para o Authorization Server
2. O Resource Owner autentica-se e concede autorização
3. O Authorization Server emite um código de autorização ou token diretamente
4. O Client troca o código por um token de acesso (quando aplicável)
5. O Client apresenta o token de acesso ao Resource Server
6. O Resource Server valida o token e retorna os dados solicitados

Esta separação é fundamental: o Client nunca obtém as credenciais do Resource Owner. Em vez disso, recebe um **token** com escopo limitado, tempo de vida controlado, e permissões específicas. Este é o princípio de **least privilege** em ação.

### 4.1.3 Por que não apenas Basic Auth?

Uma pergunta comum é por que não simplesmente enviar o nome de usuário e senha do Resource Owner ao Client. As razões são múltiplas e fundamentais:

- **Exposição de credenciais**: Se o Client armazena ou transmite credenciais, qualquer violação do Client compromete as credenciais do usuário em outros serviços.
- **Escopo ilimitado**: Credenciais de login tipicamente concedem acesso total à conta. Tokens OAuth podem ser restritos a escopos específicos.
- **Sem controle temporal**: Senhas permanecem válidas até serem explicitamente alteradas. Tokens podem expirar automaticamente.
- **Sem possibilidade de revogação granular**: Revogar uma senha afeta todos os acessos. Revogar um token afeta apenas aquele específico.
- **Auditoria impossível**: Senhas são compartilhadas e reutilizadas. Tokens são rastreáveis e vinculados a sessões específicas.

### 4.1.4 O Authorization Server

O Authorization Server é o componente central do ecossistema OAuth 2.0. Ele é responsável por:

- **Autenticação do Resource Owner**: Verificar a identidade do usuário antes de conceder autorização. Este processo pode incluir autenticação por senha, MFA, biometria, ou qualquer outro mecanismo de autenticação suportado.
- **Exibição da tela de consentimento**: Apresentar ao Resource Owner quais scopes estão sendo solicitados e por qual aplicação. O usuário deve ter visibilidade clara do que está autorizando.
- **Emissão de tokens**: Gerar tokens de acesso, refresh tokens, e potencialmente tokens de identidade (no caso de OpenID Connect).
- **Validação de tokens**: Verificar tokens apresentados pelo Client ou pelo Resource Server, incluindo validação de assinatura, expiração, scopes, e audience.
- **Gestão de autorizações**: Registrar quais autorizações foram concedidas, permitindo ao usuário revisar e revogar acessos.
- **Gestão de clients**: Registrar e gerenciar aplicações clientes, atribuindo client_id e client_secret, e configurando URIs de redirecionamento permitidos.

### 4.1.5 O Resource Server

O Resource Server é o ponto de verificação de acesso. Suas responsabilidades incluem:

- **Validação de tokens**: Verificar a integridade, validade e autorização do token apresentado. Para tokens JWT assinados localmente, o Resource Server precisa de chave pública do Authorization Server. Para tokens introspect, faz chamada ao Authorization Server.
- **Aplicação de escopos**: Garantir que o token tenha os scopes necessários para a operação solicitada. Um token com scope `read:profile` não deve permitir `write:profile`.
- **Rate limiting baseado em token**: Limitar a taxa de requisições por token para prevenir abuso.
- **Auditoria**: Registrar acessos realizados com cada token para fins de auditoria e conformidade.

### 4.1.6 O Client

O Client representa a aplicação que busca acessar recursos. Os clientes são classificados em dois tipos fundamentais:

**Clients Confidenciais (Confidential)**: Aplicações que conseguem manter suas credenciais em segredo. Exemplos incluem aplicações server-side (backends) onde o client_secret é armazenado em variáveis de ambiente ou cofres de segredos. Estes clientes podem utilizar qualquer grant type.

**Clients Públicos (Public)**: Aplicações que não conseguem manter segredos. Exemplos incluem aplicações mobile (onde o binário pode ser descompilado), SPAs (Single Page Applications), e aplicações desktop. Estes clientes NÃO devem utilizar client_secret e devem usar PKCE para mitigar riscos de interception.

A distinção entre clientes confidenciais e públicos é um dos aspectos mais críticos de segurança no OAuth 2.0. O Client Credentials flow, por exemplo, é exclusivo para clients confidenciais porque requer o envio do client_secret diretamente ao Authorization Server.

### 4.1.7 Endpoints

O Authorization Server expõe normalmente três endpoints HTTP:

1. **Authorization Endpoint**: Ponto de entrada para o Resource Owner autorizar o acesso. Aceita parâmetros como `client_id`, `redirect_uri`, `scope`, `state`, `response_type`, e `code_challenge` (para PKCE). Retorna o código de autorização ou redireciona com erro.

2. **Token Endpoint**: Usado pelo Client para trocar o código de autorização por tokens. Aceita parâmetros como `grant_type`, `code`, `redirect_uri`, `client_id`, `client_secret`, e `code_verifier`. Retorna um JSON com access_token, token_type, expires_in, e opcionalmente refresh_token.

3. **Revocation Endpoint** (RFC 7009): Permite ao Client revogar tokens específicos. Aceita `token` e `token_type_hint`. Implementação obrigatória para conformidade com boas práticas.

4. **Introspection Endpoint** (RFC 7662): Permite ao Resource Server verificar se um token está ativo. Aceita `token` e opcionalmente `token_type_hint`. Retorna metadados do token.

5. **Device Authorization Endpoint**: Usado no fluxo de autorização por dispositivo (RFC 8628).

### 4.1.8 Erros e tratamento

O Authorization Server deve retornar erros conforme especificado no RFC 6749, Seção 5.2. Os códigos de erro padronizados incluem:

- `invalid_request`: O request está malformado ou falta um parâmetro obrigatório.
- `unauthorized_client`: O client não está autorizado a usar esse grant type.
- `access_denied`: O Resource Owner ou o Authorization Server negou a solicitação.
- `unsupported_response_type`: O Authorization Server não suporta o response_type solicitado.
- `invalid_scope`: O scope solicitado é inválido, desconhecido, ou excede os scopes permitidos para o client.
- `server_error`: Erro interno no Authorization Server.
- `temporarily_unavailable`: O Authorization Server está temporariamente sobrecarregado.

Cada endpoint também deve retornar HTTP 400 para erros de request malformado e HTTP 401 para falhas de autenticação do client. Erros de segurança nunca devem expor detalhes internos — uma resposta genérica de "credenciais inválidas" é preferível a "usuário não encontrado", que permite enumeration de contas.

---

## 4.2 Authorization Code Flow

O Authorization Code Flow é o fluxo mais recomendado e mais utilizado do OAuth 2.0. Ele é projetado para clientes confidenciais que executam em um servidor seguro (back-end). O fluxo é composto por duas fases distintas: obtenção do código de autorização e troca do código por tokens.

### 4.2.1 Passo a passo do fluxo

**Passo 1 — Redirect para Autorização**

O Client constrói uma URL de autorização e redireciona o Resource Owner:

```
GET /authorize?
  response_type=code&
  client_id=CLIENT_ID&
  redirect_uri=https://app.example.com/callback&
  scope=read:profile write:messages&
  state=xyzRandom123
```

Parâmetros obrigatórios:
- `response_type=code`: Indica que o fluxo é Authorization Code.
- `client_id`: Identificador do client registrado no Authorization Server.
- `redirect_uri`: URI para onde o Resource Owner será redirecionado após a autorização. Deve corresponder exatamente a uma das URIs registradas para o client.
- `scope`: Espaço separado dos scopes solicitados.
- `state`: Um valor opaco, único, e imprevisível usado para prevenir CSRF. O client deve armazenar este valor associado à sessão e verificar no callback.

Parâmetros opcionais:
- `code_challenge` e `code_challenge_method`: Para PKCE (recomendado para TODOS os clients).
- `prompt`: Controla o comportamento de exibição (login, consent, none).
- `login_hint`: Sugere o identifier do usuário ao Authorization Server.

**Passo 2 — Autenticação e Consentimento**

O Authorization Server autentica o Resource Owner (via formulário de login, MFA, etc.) e exibe a tela de consentimento mostrando:
- O nome do aplicativo que está solicitando acesso
- Os scopes específicos que estão sendo concedidos
- Informações sobre como revogar o acesso futuramente

O Resource Owner pode aprovar ou negar a solicitação.

**Passo 3 — Redirecionamento com Código**

Se aprovado, o Authorization Server redireciona o Resource Owner de volta ao `redirect_uri` com o código de autorização:

```
HTTP/1.1 302 Found
Location: https://app.example.com/callback?code=SplxlOBeZQQYbYS6WxSbIA&state=xyzRandom123
```

O client DEVE verificar que o parâmetro `state` retornado corresponde ao valor enviado originalmente. Esta é a proteção contra ataques CSRF — sem verificação do state, um atacante pode injetar um código de autorização malicioso na sessão do usuário.

**Passo 4 — Troca do Código por Tokens**

O Client faz uma requisição server-side ao Token Endpoint:

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=SplxlOBeZQQYbYS6WxSbIA&
redirect_uri=https://app.example.com/callback&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET
```

Esta requisição é feita pelo back-end do Client, NUNCA pelo browser do usuário. O client_secret deve estar no body da requisição, NÃO no header Authorization Basic (embora Basic auth seja aceito pela RFC, o body é preferível para clareza de implementação).

**Passo 5 — Resposta com Tokens**

O Authorization Server valida o código e retorna:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read:profile write:messages"
}
```

O Client agora pode usar o `access_token` para acessar recursos protegidos no Resource Server.

### 4.2.2 Requisitos de segurança do Authorization Code Flow

**Validação obrigatória do state**: O Client deve gerar um `state` criptograficamente aleatório, armazená-lo na sessão do usuário, e verificar correspondência exata no callback. A ausência desta verificação expõe o fluxo a ataques CSRF onde um atacante pode associar sua própria conta de autorização à sessão da vítima.

**Restrição de redirect_uri**: O redirect_uri no request DEVE corresponder exatamente a uma das URIs registradas para o client. Se o Authorization Server não validar esta correspondência, um atacante pode usar uma redirect_uri maliciosa para capturar o código de autorização.

**Expiração do código**: O código de autorização DEVE expirar em um tempo curto (recomendação: 30 segundos a 5 minutos). Códigos que nunca expiram permanecem válidos indefinidamente, ampliando a janela de ataque.

**Uso único do código**: O código DEVE ser utilizável apenas uma vez. O Authorization Server deve rejeitar tentativas de reuso do mesmo código, o que mitiga ataques onde um código é interceptado e usado por múltiplos atores.

**Obrigação de TLS**: Toda comunicação entre Client, Authorization Server e Resource Server DEVE utilizar TLS. Transmissão de tokens ou códigos de autorização sobre canais não criptografados expõe dados sensíveis a interceptação.

### 4.2.3 Vazamento de código no Referer Header

Um vetor de ataque frequentemente subestimado é o vazamento de códigos de autorização através do header HTTP `Referer`. Quando o callback do Authorization Server redireciona para o Client, e o Client em seguida carrega recursos externos (imagens, scripts, iframes), o navegador inclui o código de autorização na URL do Referer.

Mitigações:
- Utilizar `Referrer-Policy: no-referrer` no callback
- Nunca incluir o código em URLs de links clicáveis
- Processar o código imediatamente no callback e redirecionar para uma URL limpa
- Utilizar fragmentos (#) em vez de query strings para transmissão de tokens

### 4.2.4 Vazamento de código via logs

Servidores web frequentemente registram URLs completas em logs de acesso. Se o Authorization Server inclui o código na query string do redirect, este código será registrado nos logs do servidor de aplicação. Qualquer pessoa com acesso aos logs pode recuperar e usar o código.

Mitigações:
- Configurar o servidor web para excluir query strings sensíveis dos logs
- Processar o código imediatamente e redirecionar antes que qualquer request subsequente seja feito
- Utilizar POST para o callback em vez de GET (exige implementação customizada)

### 4.2.5 Prevenção de authorization code injection

Um atacante que intercepta um código de autorização (por qualquer vetor — logs, Referer, rede, etc.) pode tentar injetá-lo em uma sessão legítima do usuário. Sem proteção adicional, o Authorization Server não consegue distinguir entre uma troca legítima e uma injetada.

PKCE (Proof Key for Code Exchange) é a mitigação padrão para este ataque, discutido detalhadamente na Seção 4.3.

---

## 4.3 PKCE — Proof Key for Code Exchange

PKCE (pronunciado "pixie") é uma extensão ao Authorization Code Flow definida no RFC 7636. Originalmente projetado para clientes móveis e SPA, é agora recomendado para **todos** os clientes, independentemente do tipo.

### 4.3.1 O problema que PKCE resolve

Sem PKCE, qualquer pessoa que obtenha o código de autorização pode trocá-lo por tokens. O Authorization Server não consegue verificar se quem está trocando o código é o mesmo que iniciou o fluxo. Isso é particularmente perigoso em:

- **Dispositivos móveis**: Apps podem ser interceptados por ferramentas de proxy, apps maliciosos com deep linking, ou manipulação de redirect URIs.
- **SPAs**: O código passa pelo browser, onde extensões maliciosas ou XSS podem capturá-lo.
- **Redes não confiáveis**: Em redes públicas, intermediários podem interceptar o tráfego (embora TLS mitigue isso, há vetores de ataque sofisticados).

### 4.3.2 Mecanismo do PKCE

PKCE introduz dois novos parâmetros no fluxo:

1. **code_verifier**: Uma string aleatória de 43-128 caracteres, composta apenas de caracteres alfanuméricos, hífens, underscores, pontos, til (~), e underline (_). Deve ter entropia criptográfica suficiente (recomendação: 32 bytes de entropia, codificados em base64url).

2. **code_challenge**: O code_verifier transformado. Pode ser:
   - `plain`: O code_verifier idêntico ao code_challenge (NÃO recomendado)
   - `S256`: `BASE64URL(SHA256(code_verifier))` (RECOMENDADO)

**Fluxo com PKCE:**

Passo 1 — O Client gera o code_verifier e calcula o code_challenge:

```python
import secrets
import hashlib
import base64

# Gerar code_verifier com 32 bytes de entropia
code_verifier = secrets.token_urlsafe(32)
# Resultado: ~43 caracteres aleatórios seguros

# Calcular code_challenge usando SHA-256
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode('ascii')).digest()
).rstrip(b'=').decode('ascii')
# Resultado: 43 caracteres em base64url
```

Passo 2 — O Client inclui o code_challenge no request de autorização:

```
GET /authorize?
  response_type=code&
  client_id=CLIENT_ID&
  redirect_uri=https://app.example.com/callback&
  scope=read:profile&
  state=abc123&
  code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&
  code_challenge_method=S256
```

Passo 3 — O Authorization Server armazena o code_challenge associado ao código de autorização.

Passo 4 — Na troca do código por token, o Client envia o code_verifier:

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=SplxlOBeZQQYbYS6WxSbIA&
redirect_uri=https://app.example.com/callback&
client_id=CLIENT_ID&
code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

Passo 5 — O Authorization Server calcula `SHA256(code_verifier)` e compara com o `code_challenge` armazenado. Se corresponder, emite os tokens.

### 4.3.3 Por que PKCE protege contra interception

Se um atacante intercepta o código de autorização (o `code`), ele não tem o `code_verifier` correspondente. O code_verifier NUNCA é transmitido durante o fluxo de autorização — ele permanece apenas no client. Sem o code_verifier correto, o Authorization Server rejeita a tentativa de troca.

Mesmo que o atacante intercepte o código E tente gerar seu próprio code_verifier, ele não terá o code_challenge que foi associado ao código original no Authorization Server.

### 4.3.4 Implementação em Node.js com PKCE

```javascript
const crypto = require('crypto');

// Gerar code_verifier
function generateCodeVerifier() {
  return crypto.randomBytes(32)
    .toString('base64url');
}

// Gerar code_challenge a partir do verifier
function generateCodeChallenge(verifier) {
  return crypto.createHash('sha256')
    .update(verifier)
    .digest('base64url');
}

// Fluxo completo de autorização com PKCE
function initiateAuth(clientId, redirectUri, scope) {
  const codeVerifier = generateCodeVerifier();
  const codeChallenge = generateCodeChallenge(codeVerifier);

  // Armazenar codeVerifier na sessão
  session.set('pkce_code_verifier', codeVerifier);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: scope,
    state: generateSecureState(),
    code_challenge: codeChallenge,
    code_challenge_method: 'S256'
  });

  return `https://auth.example.com/authorize?${params.toString()}`;
}

// Troca de código por token com code_verifier
async function exchangeCodeForTokens(code, redirectUri, clientId) {
  const codeVerifier = session.get('pkce_code_verifier');
  session.delete('pkce_code_verifier'); // Usar uma única vez

  const response = await fetch('https://auth.example.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: redirectUri,
      client_id: clientId,
      code_verifier: codeVerifier
    })
  });

  if (!response.ok) {
    throw new Error('Token exchange failed');
  }

  return await response.json();
}
```

### 4.3.5 Validação server-side do PKCE

O Authorization Server DEVE implementar validação rigorosa:

```python
import hashlib
import base64
from fastapi import FastAPI, HTTPException

app = FastAPI()

def validate_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method == 'S256':
        computed = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('ascii')).digest()
        ).rstrip(b'=').decode('ascii')
        return secrets.compare_digest(computed, code_challenge)
    elif method == 'plain':
        return secrets.compare_digest(code_verifier, code_challenge)
    else:
        raise ValueError(f"Unsupported method: {method}")

@app.post("/token")
async def token_endpoint(request: TokenRequest):
    authorization_code = get_code(request.code)

    if authorization_code.used:
        raise HTTPException(status_code=400, detail="Code already used")

    if authorization_code.expired:
        raise HTTPException(status_code=400, detail="Code expired")

    if authorization_code.code_challenge:
        if not request.code_verifier:
            raise HTTPException(
                status_code=400,
                detail="code_verifier required"
            )

        if not validate_pkce(
            request.code_verifier,
            authorization_code.code_challenge,
            authorization_code.code_challenge_method
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid code_verifier"
            )

    # Marcar código como usado
    authorization_code.used = True

    # Emitir tokens
    access_token = create_access_token(
        sub=authorization_code.subject,
        scope=authorization_code.scope,
        client_id=authorization_code.client_id
    )

    refresh_token = create_refresh_token(
        sub=authorization_code.subject,
        client_id=authorization_code.client_id
    )

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
        "scope": authorization_code.scope
    }
```

---

## 4.4 Client Credentials Flow

O Client Credentials Flow é o mais simples dos fluxos OAuth 2.0. Ele é utilizado quando o Client é um serviço backend que precisa acessar recursos protegidos em seu próprio nome — sem a participação de um Resource Owner humano. Casos de uso incluem microserviços comunicando entre si, integrações com APIs administrativas, e automações de backend.

### 4.4.1 O fluxo

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=SERVICE_CLIENT_ID&
client_secret=SERVICE_CLIENT_SECRET&
scope=service:read service:write
```

Resposta:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "service:read service:write"
}
```

### 4.4.2 Características importantes

- **Sem refresh tokens**: O Client Credentials flow tipicamente não emite refresh tokens. O Client pode simplesmente solicitar um novo token quando o atual expira.
- **Sem interação humana**: Não há tela de consentimento porque não há Resource Owner. O Client é simultaneamente o solicitante e o autorizador.
- **Client confidencial obrigatório**: Apenas clients confidenciais (com client_secret válido) podem usar este fluxo. Clients públicos NÃO devem usar Client Credentials.
- **Sem scopes de consentimento**: Os scopes são determinados pelo registro do client no Authorization Server, não por um usuário.

### 4.4.3 Segurança do Client Credentials

O client_secret é o ativo mais sensível neste fluxo. Se comprometido, qualquer pessoa pode gerar tokens de acesso.

**Práticas recomendadas:**
- Armazenar o client_secret em cofres de segredos (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- Nunca incluir client_secret em código-fonte, variáveis de ambiente em repositórios, ou configurações commitadas
- Implementar rotação regular de client_secret
- Restringir os scopes do client ao mínimo necessário
- Implementar rate limiting no Token Endpoint
- Registrar o IP de origem permitido para o client

**Exemplo de armazenamento seguro:**

```python
import os
from vault import VaultClient

vault = VaultClient(url=os.environ['VAULT_ADDR'])

def get_client_credentials():
    secret = vault.read_secret('secret/oauth2/service-client')
    return {
        'client_id': secret['data']['client_id'],
        'client_secret': secret['data']['client_secret']
    }

# Nunca logar ou expor o client_secret
# Nunca commitar em repositórios
# Nunca transmitir sem TLS
```

---

## 4.5 Device Authorization Flow

O Device Authorization Flow (RFC 8628) foi projetado para dispositivos com entrada de dados limitada ou nenhuma — Smart TVs, consoles de jogos, dispositivos IoT, terminais públicos. O fluxo permite que o usuário autorize o dispositivo usando um segundo dispositivo (geralmente um smartphone ou computador) com capacidade de entrada de dados completa.

### 4.5.1 Casos de uso

- **Smart TVs**: O usuário digita um código de 8 caracteres no navegador do smartphone para autorizar o TV a acessar conteúdo Netflix, YouTube, etc.
- **Consoles de jogos**: PlayStation, Xbox, Nintendo Switch usam este fluxo para autenticação de serviços streaming.
- **Dispositivos IoT**: Termostatos, assistentes virtuais, e outros dispositivos que não possuem teclado completo.
- **Terminais públicos**: Quiosques, caixas eletrônicos, e outros dispositivos onde digitar credenciais diretamente é inseguro.

### 4.5.2 Passo a passo

**Passo 1 — Solicitação do dispositivo:**

O Client (dispositivo) solicita um device_code e user_code:

```
POST /device/code HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

client_id=DEVICE_CLIENT_ID&
scope=read:content
```

Resposta:

```json
{
  "device_code": "GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS",
  "user_code": "WDJB-MJHT",
  "verification_uri": "https://auth.example.com/device",
  "verification_uri_complete": "https://auth.example.com/device?user_code=WDJB-MJHT",
  "expires_in": 600,
  "interval": 5
}
```

**Passo 2 — Exibição do user_code:**

O dispositivo exibe ao usuário:
- O user_code (`WDJB-MJHT`)
- A verification_uri (`https://auth.example.com/device`)
- Instruções: "Acesse https://auth.example.com/device e digite o código: WDJB-MJHT"

**Passo 3 — Autorização pelo usuário:**

O usuário acessa a verification_uri em um dispositivo secundário (smartphone), autentica-se, e digita o user_code. O Authorization Server valida o user_code e solicita consentimento.

**Passo 4 — Polling do dispositivo:**

Enquanto o usuário autoriza, o dispositivo faz polling periódico ao Token Endpoint:

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:device_code&
device_code=GmRhmhcxhwAzkoEqiMEg_DnyEysNkuNhszIySk9eS&
client_id=DEVICE_CLIENT_ID
```

Respostas possíveis durante o polling:
- `authorization_pending`: O usuário ainda não completou a autorização
- `slow_down`: O intervalo entre requests está muito curto (aumentar o intervalo)
- `expired_token`: O device_code expirou (solicitar novo device_code)
- `access_denied`: O usuário negou a autorização
- Token response: O usuário autorizou com sucesso

**Passo 5 — Recebimento do token:**

Quando o usuário autoriza, o polling retorna os tokens normalmente:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read:content"
}
```

### 4.5.3 Segurança do Device Authorization Flow

**Intervalo de polling**: O intervalo mínimo entre requests de polling é tipicamente 5 segundos. Responder com `slow_down` quando o client polls mais rápido previne abuso.

**Expiração do device_code**: O device_code deve expirar em tempo razoável (5-15 minutos). Se o usuário não completar a autorização dentro deste prazo, o device_code é invalidado.

**Limitação de attempts**: O Authorization Server deve limitar o número de tentativas de inserção do user_code para prevenir brute force.

**Vinculação ao dispositivo**: O device_code deve ser vinculado ao IP ou outra identificação do dispositivo que o solicitou, para prevenir que outro dispositivo responda ao polling.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/device/code")
async def device_code_endpoint(client_id: str, scope: str):
    # Validar client_id
    client = await get_client(client_id)
    if not client or not client.is_device_client:
        raise HTTPException(status_code=400, detail="Invalid client")

    # Gerar device_code e user_code
    device_code = secrets.token_urlsafe(32)
    user_code = generate_user_code()  # Formato: XXXX-XXXX

    # Armazenar com expiração
    await store_device_code(
        device_code=device_code,
        user_code=user_code,
        client_id=client_id,
        scope=scope,
        expires_in=600
    )

    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": "https://auth.example.com/device",
        "verification_uri_complete": (
            f"https://auth.example.com/device?user_code={user_code}"
        ),
        "expires_in": 600,
        "interval": 5
    }

@app.post("/token")
async def device_token_poll(device_code: str, client_id: str, grant_type: str):
    if grant_type != "urn:ietf:params:oauth:grant-type:device_code":
        raise HTTPException(status_code=400, detail="Unsupported grant type")

    stored = await get_device_code(device_code)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid device_code")

    if stored.is_expired():
        await delete_device_code(device_code)
        return {"error": "expired_token"}

    if not stored.is_authorized():
        return {"error": "authorization_pending"}

    if stored.is_denied():
        await delete_device_code(device_code)
        return {"error": "access_denied"}

    # Emite tokens
    access_token = create_access_token(
        sub=stored.user_id,
        scope=stored.scope,
        client_id=client_id
    )

    await delete_device_code(device_code)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": stored.scope
    }
```

---

## 4.6 Resource Owner Password Credentials (ROPC) — Deprecado

O Resource Owner Password Credentials grant (também chamado de "password grant") permite que o Client solicite o nome de usuário e senha do Resource Owner diretamente, e os envie ao Authorization Server para autenticação.

### 4.6.1 O fluxo

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=password&
username=user@example.com&
password=secretPassword123&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET&
scope=read:profile
```

### 4.6.2 Por que está deprecado

O ROPC grant é oficialmente descontinuado (draft-ietf-oauth-native-apps, RFC 9700). As razões são técnicas e irrefutáveis:

1. **Exposição total de credenciais**: O Client vê e transmite as credenciais de login do usuário. Isso viola o princípio fundamental do OAuth de não expor credenciais ao Client.

2. **Incompatibilidade com MFA**: O protocolo ROPC não suporta fluxos de autenticação multifator. Quando o Authorization Server exige MFA, o ROPC falha porque o Client não consegue apresentar uma tela de MFA adequada.

3. **Incompatibilidade com SSO**: Organizações que utilizam Single Sign-On não podem usar ROPC porque o fluxo assume autenticação direta com credenciais de usuário.

4. **Incompatível com protocolos modernos de autenticação**: WebAuthn, passkeys, biometria, e outros mecanismos modernos são incompatíveis com o modelo de envio de senha.

5. **Violação de Termos de Serviço**: Muitos provedores de identidade (Google, Microsoft, Facebook) proíbem explicitamente o uso de ROPC em seus termos de serviço.

### 4.6.3 Substitutos

Para cada caso de uso do ROPC, existe uma alternativa adequada:

| Caso de uso | Substituto recomendado |
|---|---|
| Aplicação mobile nativa | Authorization Code + PKCE |
| Script automatizado | Client Credentials (se possível) ou Device Authorization |
| Migração de sistema legado | Authorization Code + PKCE com login embutido |
| Integração entre serviços | Client Credentials |

### 4.6.4 Migrando de ROPC para Authorization Code + PKCE

A migração requer que o Client implemente um fluxo de redirecionamento:

```python
# ANTES: ROPC (INSEGURO)
def login_with_ropc(username, password, client_id, client_secret):
    response = requests.post("https://auth.example.com/token", data={
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "openid profile"
    })
    return response.json()

# DEPOIS: Authorization Code + PKCE (SEGURO)
def initiate_auth_code_flow(client_id, redirect_uri, scope):
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode()

    # Armazenar code_verifier na sessão do usuário
    store_in_session("pkce_verifier", code_verifier)

    auth_url = (
        f"https://auth.example.com/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={generate_state()}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    return auth_url
```

---

## 4.7 Tipos de Token

### 4.7.1 Access Token

O Access Token é o token principal do OAuth 2.0. Ele autoriza o Client a acessar recursos protegidos no Resource Server.

**Formato**: O OAuth 2.0 RFC não especifica o formato do access token. Na prática, existem duas abordagens principais:

1. **Tokens opacos**: Strings aleatórias sem estrutura interna visível. Exemplo: `dGhpcyBpcyBhIHRva2Vu`. O Resource Server deve chamar o Introspection Endpoint para validar.

2. **Tokens JWT (JSON Web Token)**: Tokens autocontidos que carregam informações estruturadas. O Resource Server pode validar localmente sem chamar o Authorization Server.

**Estrutura de um JWT de access token:**

```json
{
  "header": {
    "alg": "RS256",
    "typ": "at+jwt",
    "kid": "key-2024-01"
  },
  "payload": {
    "iss": "https://auth.example.com",
    "sub": "user123",
    "aud": "https://api.example.com",
    "exp": 1700000000,
    "iat": 1699996400,
    "scope": "read:profile write:messages",
    "client_id": "my-app",
    "jti": "unique-token-id-123"
  }
}
```

**Claims padrão do JWT:**
- `iss` (issuer): O Authorization Server que emitiu o token
- `sub` (subject): O Resource Owner (usuário) que autorizou
- `aud` (audience): O Resource Server destinatário
- `exp` (expiration): Timestamp de expiração
- `iat` (issued at): Timestamp de emissão
- `nbf` (not before): Timestamp a partir do qual o token é válido
- `jti` (JWT ID): Identificador único do token
- `scope`: Scopes autorizados

**Validação do Access Token no Resource Server:**

```python
import jwt
from jwt import PyJWKClient

# Cache de chaves públicas do Authorization Server
jwk_client = PyJWKClient("https://auth.example.com/.well-known/jwks.json")

def validate_access_token(token: str) -> dict:
    try:
        # Obter chave pública para o kid do token
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Validar e decodificar
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="https://api.example.com",
            issuer="https://auth.example.com",
            options={
                "require": ["exp", "iss", "sub", "aud", "iat"]
            }
        )

        # Verificar se não está na blocklist (para revogação)
        if is_token_revoked(payload["jti"]):
            raise TokenRevokedError()

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=403, detail="Invalid audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=403, detail="Invalid issuer")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 4.7.2 Refresh Token

O Refresh Token é um token de longa duração usado para obter novos access tokens sem exigir nova autorização do Resource Owner.

**Características:**
- Maior tempo de vida que o access tipicamente (dias, semanas, ou meses)
- Deve ser armazenado de forma segura no Client (armazenamento criptografado no servidor)
- Transmitido apenas ao Token Endpoint, nunca ao Resource Server
- Deve ser usável apenas uma vez (rotation de refresh token)

**Emissão de refresh token:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "read:profile"
}
```

**Renovação do access token:**

```
POST /token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token=tGzv3JOkF0XG5Qx2TlKWIA&
client_id=CLIENT_ID&
client_secret=CLIENT_SECRET
```

Resposta:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...NOVO_TOKEN",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "nEwR3Fr3sHtOk3n",
  "scope": "read:profile"
}
```

**Rotação de Refresh Token**: O Authorization Server deve emitir um NOVO refresh token a cada utilização e invalidar o anterior. Se um refresh token for usado mais de uma vez, isso indica possível comprometimento — todos os tokens emitidos a partir do refresh token comprometido devem ser invalidados.

```python
async def refresh_token_endpoint(request):
    old_refresh = await get_refresh_token(request.refresh_token)

    if not old_refresh or old_refresh.is_revoked:
        # Possível comprometimento — revogar toda a família
        if old_refresh and old_refresh.family_id:
            await revoke_token_family(old_refresh.family_id)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if old_refresh.is_expired():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    if old_refresh.used_count > 0:
        # Token reutilizado — comprometimento detectado
        await revoke_token_family(old_refresh.family_id)
        alert_security_team(
            f"Refresh token reuse detected for user {old_refresh.user_id}"
        )
        raise HTTPException(status_code=401, detail="Token reuse detected")

    # Marcar como usado
    old_refresh.used_count += 1
    old_refresh.used_at = datetime.utcnow()
    await save_refresh_token(old_refresh)

    # Emitir novos tokens
    new_access = create_access_token(
        sub=old_refresh.user_id,
        scope=old_refresh.scope,
        client_id=old_refresh.client_id
    )

    new_refresh = create_refresh_token(
        user_id=old_refresh.user_id,
        scope=old_refresh.scope,
        client_id=old_refresh.client_id,
        family_id=old_refresh.family_id
    )

    return {
        "access_token": new_access,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": new_refresh.token,
        "scope": old_refresh.scope
    }
```

### 4.7.3 Comparação entre tipos de token

| Característica | Access Token | Refresh Token |
|---|---|---|
| Duração | Curta (minutos a horas) | Longa (dias a meses) |
| Uso | Apresentado ao Resource Server | Usado apenas no Token Endpoint |
| Armazenamento | Memória do Client (frontend) | Armazenamento persistente e seguro no backend |
| Formato | JWT ou opaco | Tipicamente opaco |
| Revogação | Via expiração ou blocklist | Via revogação explícita |
| Rotação | Não (renovado via refresh) | Sim (novo token a cada uso) |

---

## 4.8 Scopes e Permissões

Scopes são o mecanismo do OAuth 2.0 para controlar o nível de acesso concedido ao Client. Eles representam permissões granulares que o Resource Owner pode conceder.

### 4.8.1 Princípios dos Scopes

**Least Privilege**: O Client deve solicitar apenas os scopes necessários para sua funcionalidade. Um aplicativo de leitura não deve solicitar `write` ou `delete`.

**Granularidade**: Scopes devem ser suficientemente granulares para permitir controle preciso, mas não a ponto de criar complexidade desnecessária. Um equilíbrio prático é scopes por recurso e ação: `read:users`, `write:users`, `read:orders`, `write:orders`.

**Nomenclatura consistente**: Scopes devem seguir um padrão claro e previsível. Formatos comuns incluem:
- `resource:action` (ex: `users:read`, `orders:write`)
- `scope.resource.action` (ex: `api.users.read`)
- `resource/action` (ex: `users/read`)

**Documentação**: Todos os scopes disponíveis devem ser documentados publicamente, incluindo sua descrição e quais dados ou ações autorizam.

### 4.8.2 Scopes comuns

Para um sistema de identidade genérico:

```
openid          — Acesso ao ID Token (necessário para OIDC)
profile         — Informações básicas do perfil (nome, sobrenome, foto)
email           — Endereço de e-mail do usuário
address         — Endereço postal do usuário
phone           — Número de telefone do usuário
offline_access  — Emissão de refresh token
```

Para APIs de negócios:

```
read:users      — Leitura de dados de usuários
write:users     — Criação e atualização de usuários
delete:users    — Exclusão de usuários
read:reports    — Geração e leitura de relatórios
admin:system    — Administração do sistema
```

### 4.8.3 Validação de Scopes

```python
from functools import wraps

def require_scope(*required_scopes):
    """Decorator para validar scopes necessários."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token = kwargs.get('token') or args[0]
            token_scopes = set(token['scope'].split(' '))
            required = set(required_scopes)

            if not required.issubset(token_scopes):
                missing = required - token_scopes
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required scopes: {missing}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

@app.get("/api/users")
@require_scope("read:users")
async def list_users(token: dict):
    users = await db.users.find()
    return users

@app.post("/api/users")
@require_scope("write:users")
async def create_user(token: dict, user_data: UserCreate):
    user = await db.users.insert(user_data)
    return user

@app.delete("/api/users/{user_id}")
@require_scope("delete:users")
async def delete_user(token: dict, user_id: str):
    await db.users.delete(user_id)
    return {"status": "deleted"}
```

### 4.8.4 Dynamic Scopes

Em sistemas avançados, scopes podem ser dinâmicos — incluindo identificadores específicos de recursos:

```
user:123:read           — Leitura do usuário com ID 123
order:456:write         — Escrita na ordem 456
org:789:admin           — Administração da organização 789
```

```python
import re

DYNAMIC_SCOPE_PATTERN = re.compile(
    r'^(\w+):([a-f0-9-]+):(\w+)$'
)

def parse_dynamic_scope(scope: str) -> dict:
    match = DYNAMIC_SCOPE_PATTERN.match(scope)
    if match:
        return {
            "resource": match.group(1),
            "resource_id": match.group(2),
            "action": match.group(3)
        }
    return {"scope": scope}

def authorize_scope(token_scopes: list, required_resource: str,
                    required_id: str, required_action: str) -> bool:
    for scope in token_scopes:
        parsed = parse_dynamic_scope(scope)

        if "scope" in parsed:
            continue

        if (parsed["resource"] == required_resource and
            parsed["action"] == required_action and
            (parsed["resource_id"] == "*" or
             parsed["resource_id"] == required_id)):
            return True

    return False
```

---

## 4.9 Ciclo de Vida dos Tokens

### 4.9.1 Emissão (Issuance)

O ciclo de vida começa com a emissão do token pelo Authorization Server. Durante a emissão:

1. **Validação do request**: O Authorization Server valida todos os parâmetros (client_id, redirect_uri, scopes, code_verifier para PKCE).
2. **Autenticação**: Verifica a identidade do solicitante (Resource Owner ou Client).
3. **Autorização**: Verifica se os scopes solicitados são permitidos para o client.
4. **Geração**: Cria o token com as claims necessárias e atribui tempo de vida.
5. **Armazenamento**: Registra o token (ou metadados para JWT) para fins de revogação e auditoria.
6. **Entrega**: Retorna o token ao Client via HTTPS seguro.

### 4.9.2 Uso (Usage)

O Client utiliza o access token apresentando-o em requisições HTTP ao Resource Server. O token é tipicamente transmitido no header `Authorization`:

```
GET /api/resource HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

Ou como parâmetro de query (menos seguro, evitar):

```
GET /api/resource?access_token=eyJhbGciOiJSUzI1NiIs... HTTP/1.1
```

Ou em cookies para fluxos baseados em browser (requer configuração adicional de segurança):

```
Cookie: access_token=eyJhbGciOiJSUzI1NiIs...
```

### 4.9.3 Validação (Validation)

O Resource Server valida o token a cada request. A validação inclui:

1. **Formato**: Verificar se o token é um JWT válido ou um token opaco.
2. **Assinatura**: Verificar a assinatura do JWT usando a chave pública do Authorization Server.
3. **Expiração**: Verificar se o token não expirou (claim `exp`).
4. **Issuer**: Verificar se o emissor é o Authorization Server confiável.
5. **Audience**: Verificar se o token foi emitido para este Resource Server.
6. **Scopes**: Verificar se o token tem os scopes necessários para a operação.
7. **Revogação**: Verificar se o token não foi revogado (para tokens JWT, consulta à blocklist; para tokens opacos, consulta ao Introspection Endpoint).

### 4.9.4 Renovação (Renewal)

Quando o access token expira, o Client utiliza o refresh token para obter um novo access token. Este processo deve ser transparente ao usuário e ao Resource Server.

```python
class TokenManager:
    def __init__(self, auth_server: str, client_id: str, client_secret: str):
        self.auth_server = auth_server
        self.client_id = client_id
        self.client_secret = client_secret

    async def get_valid_token(self, token_data: dict) -> str:
        """Retorna um access token válido, renovando se necessário."""
        if not self.is_expired(token_data["expires_at"]):
            return token_data["access_token"]

        # Token expirado — renovar
        new_tokens = await self.refresh(token_data["refresh_token"])

        # Atualizar dados armazenados
        token_data["access_token"] = new_tokens["access_token"]
        token_data["refresh_token"] = new_tokens["refresh_token"]
        token_data["expires_at"] = (
            datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
        )

        await save_token_data(token_data)

        return new_tokens["access_token"]

    async def refresh(self, refresh_token: str) -> dict:
        response = await httpx.AsyncClient().post(
            f"{self.auth_server}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )

        if response.status_code != 200:
            raise TokenRefreshError("Failed to refresh token")

        return response.json()

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        # Renovar 60 segundos antes da expiração
        return datetime.utcnow() >= (expires_at - timedelta(seconds=60))
```

### 4.9.5 Revogação (Revocation)

A revogação é o processo de invalidação antecipada de um token. O RFC 7009 define o protocolo de revogação de tokens.

**Quando revogar:**
- Usuário solicita logout
- Usuário revoga acesso de um aplicativo
- Suspeita de comprometimento de token
- Mudança de permissões do usuário
- Remoção de conta do usuário

**Protocolo de Revogação (RFC 7009):**

```
POST /revoke HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

token=45ghiukldjahdnhzdauz&
token_type_hint=access_token
```

O `token_type_hint` é opcional mas recomendado — ajuda o Authorization Server a encontrar o token mais rapidamente.

**Resposta:**

```
HTTP/1.1 200 OK
```

O Authorization Server deve retornar 200 mesmo se o token não existir, para evitar leaking de informação.

```python
@app.post("/revoke")
async def revoke_token(
    token: str,
    token_type_hint: Optional[str] = None
):
    # Buscar o token (por hint ou por busca completa)
    if token_type_hint == "access_token":
        token_record = await find_access_token(token)
    elif token_type_hint == "refresh_token":
        token_record = await find_refresh_token(token)
    else:
        token_record = await find_token(token)

    if token_record:
        # Invalidar o token
        token_record.revoked = True
        token_record.revoked_at = datetime.utcnow()
        await save_token(token_record)

        # Invalidar familia de refresh tokens se aplicável
        if token_record.type == "refresh" and token_record.family_id:
            await revoke_token_family(token_record.family_id)

    # Sempre retornar 200 (conforme RFC 7009)
    return Response(status_code=200)
```

**Revogação em cascade**: Quando um refresh token é revogado, todos os access tokens emitidos a partir dele também devem ser invalidados. A implementação de "família de tokens" facilita isso: cada refresh token carrega um `family_id` que agrupa todos os tokens emitidos na mesma cadeia.

---

## 4.10 Melhores Práticas de Segurança

### 4.10.1 Implementação segura

1. **Usar Authorization Code + PKCE para todos os clients**: Nunca usar Implicit Flow. PKCE é obrigatório para clientes públicos e recomendado para confidenciais.

2. **Validar rigorosamente redirect_uri**: Comparação exata, sem normalização permissiva. Um redirect URI como `https://app.example.com/callback` é diferente de `https://APP.EXAMPLE.COM/callback`. Configure o Authorization Server para comparação case-sensitive.

3. **Implementar state parametrizado**: Gerar state com entropia criptográfica, associar à sessão, e verificar no callback. Não usar contadores sequenciais ou valores previsíveis.

4. **Utilizar TLS em todas as comunicações**: Sem exceções. Apenas HTTPS em todos os endpoints.

5. **Implementar validação de audience**: O Resource Server deve verificar se o token foi destinado a ele. Isso impede que tokens emitidos para um serviço sejam usados em outro.

6. **Definir tempos de vida apropriados**:
   - Access tokens: 5-15 minutos para APIs, 1 hora para sessões web
   - Refresh tokens: 7-30 dias para apps web, mais curto para mobile
   - Códigos de autorização: 30 segundos a 5 minutos

7. **Implementar rotation de refresh tokens**: Novo refresh token a cada uso. Invalidação em cascade se reutilizado.

8. **Implementar token binding**: Vincular tokens ao client que os solicitou. O `client_id` deve ser verificado durante a validação.

### 4.10.2 Armazenamento seguro no Client

**Aplicações Web (SPA)**:
- Access token: Armazenar em memória JavaScript (variável, não localStorage)
- Refresh token: HttpOnly, Secure, SameSite=Strict cookie
- NUNCA armazenar em localStorage ou sessionStorage (XSS pode ler)

**Aplicações Mobile**:
- Usar Keychain (iOS) ou Keystore (Android)
- NUNCA armazenar em SharedPreferences (Android) ou UserDefaults (iOS) sem criptografia
- Considerar use of Secure Enclave / StrongBox para high-security

**Aplicações Server-side**:
- Armazenar em banco de dados criptografado
- Usar cofres de segredos para client_secret
- Nunca em variáveis de ambiente em repositórios

### 4.10.3 Proteção contra ataques comuns

**CSRF**:
- Verificar parâmetro `state` no callback
- Usar PKCE como proteção adicional
- Vincular tokens a sessões específicas

**Token Injection**:
- PKCE previne injection de código de autorização
- Validação de audience impede uso cross-service
- Token binding (DPoP) impede uso por terceiros

**Replay Attacks**:
- JTI (JWT ID) único para cada token
- Curto tempo de vida dos access tokens
- One-time use para códigos de autorização

**Token Leakage**:
- NUNCA transmitir tokens em URLs
- NUNCA logar tokens em logs de aplicação
- Usar tokens de curta duração
- Implementar revogação imediata

**Confused Deputy**:
- Validar issuer em todos os endpoints
- Verificar audience em cada Resource Server
- Não confiar em tokens de proveniência desconhecida

---

## 4.11 Vulnerabilidades Comuns

### 4.11.1 Open Redirect via redirect_uri

**Vulnerabilidade**: O Authorization Server aceita redirect URIs com curingas ou normalização permissiva, permitindo que um atacante registre uma URI que captura o código de autorização.

**Exemplo**:
```
# URI registrada:
https://app.example.com/callback

# URI maliciosa aceita:
https://app.example.com.callback.evil.com/steal
# ou
https://app.example.com/callback/../evil/
```

**Impacto**: Roubo do código de autorização e subsequente obtenção dos tokens de acesso.

**Mitigação**: Validação exata do redirect_uri, sem curingas, sem normalização de path, sem aceitação de domínios similares.

### 4.11.2 Token Substitution

**Vulnerabilidade**: Um atacante obtém um token legítimo de um contexto e o usa em outro onde seria aceito.

**Exemplo**: Tokens emitidos para o endpoint `/api/read-only` são aceitos no endpoint `/api/admin` porque a validação de audience não está implementada.

**Mitigação**: Validação de audience obrigatória em todos os Resource Servers. Cada API deve verificar que o token foi emitido especificamente para ela.

### 4.11.3 Insufficient Entropy no State

**Vulnerabilidade**: O parâmetro `state` é previsível (timestamp, counter, hash de dados conhecidos), permitindo que um atacante forge um state válido.

**Exemplo**:
```python
# INSEGURO — state previsível
state = f"{session_id}_{int(time.time())}"

# SEGURO — state criptograficamente aleatório
state = secrets.token_urlsafe(32)
```

**Impacto**: CSRF no fluxo OAuth, permitindo que o atacante vincule sua conta de autorização à sessão da vítima.

### 4.11.4 Lack of Token Binding

**Vulnerabilidade**: Tokens não são vinculados ao client ou dispositivo que os solicitou. Um token interceptado pode ser usado por qualquer um.

**Mitigação**: DPoP (Demonstrating Proof-of-Possession, RFC 9449) vincula tokens ao holder通过 challenge-response. Client gera um par de chaves, inclui o public key no token request, e o Authorization Server emite o token vinculado àquela chave.

### 4.11.5 Refresh Token Theft

**Vulnerabilidade**: O refresh token é roubado (via XSS, MITM, ou comprometimento do servidor) e usado por um atacante para manter acesso contínuo.

**Mitigação**:
- Rotation de refresh tokens (novo token a cada uso)
- Detecção de reuso (se um refresh token é usado mais de uma vez, revogar toda a família)
- Binding de refresh token ao client_id
- Armazenamento seguro (HttpOnly cookies, Keychain/Keystore)
- Uso de sender-constrained tokens

### 4.11.6 Missing Code Expiration

**Vulnerabilidade**: O código de autorização não expira, permitindo que um atacante que tenha obtido o código em algum momento do passado o use indefinidamente.

**Mitigação**: Expiração obrigatória de códigos de autorização (máximo 5 minutos, recomendado 30 segundos a 2 minutos).

---

## 4.12 Exemplos de Implementação

### 4.12.1 Authorization Server com Python (FastAPI)

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

class AuthorizationRequest(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    scope: str
    state: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = "S256"

class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

# Simulação de banco de dados
clients_db = {}
auth_codes_db = {}
tokens_db = {}

@app.get("/authorize")
async def authorize(request: AuthorizationRequest):
    if request.response_type != "code":
        raise HTTPException(400, "Unsupported response_type")

    client = clients_db.get(request.client_id)
    if not client:
        raise HTTPException(400, "Invalid client_id")

    if request.redirect_uri not in client["redirect_uris"]:
        raise HTTPException(400, "Invalid redirect_uri")

    # Gerar código de autorização
    code = secrets.token_urlsafe(32)
    auth_codes_db[code] = {
        "client_id": request.client_id,
        "redirect_uri": request.redirect_uri,
        "scope": request.scope,
        "state": request.state,
        "code_challenge": request.code_challenge,
        "code_challenge_method": request.code_challenge_method,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
        "used": False
    }

    # Redirecionar com código
    separator = "&"
    return RedirectResponse(
        f"{request.redirect_uri}?code={code}&state={request.state}"
    )

@app.post("/token")
async def token(request: TokenRequest):
    if request.grant_type == "authorization_code":
        return await handle_auth_code_grant(request)
    elif request.grant_type == "refresh_token":
        return await handle_refresh_grant(request)
    else:
        raise HTTPException(400, "Unsupported grant_type")

async def handle_auth_code_grant(request: TokenRequest):
    code_data = auth_codes_db.get(request.code)
    if not code_data:
        raise HTTPException(400, "Invalid code")

    if code_data["used"]:
        # Código reutilizado — possível ataque
        del auth_codes_db[request.code]
        raise HTTPException(400, "Code already used")

    if datetime.utcnow() > code_data["expires_at"]:
        del auth_codes_db[request.code]
        raise HTTPException(400, "Code expired")

    if code_data["client_id"] != request.client_id:
        raise HTTPException(400, "Client mismatch")

    if code_data["redirect_uri"] != request.redirect_uri:
        raise HTTPException(400, "Redirect URI mismatch")

    # Validar PKCE se aplicável
    if code_data["code_challenge"]:
        if not request.code_verifier:
            raise HTTPException(400, "code_verifier required")

        if not verify_pkce(
            request.code_verifier,
            code_data["code_challenge"],
            code_data["code_challenge_method"]
        ):
            raise HTTPException(400, "Invalid code_verifier")

    # Marcar código como usado
    code_data["used"] = True

    # Gerar tokens
    access_token = create_jwt(
        sub=code_data.get("user_id", "user123"),
        client_id=request.client_id,
        scope=code_data["scope"],
        expires_in=3600
    )

    refresh_token = secrets.token_urlsafe(64)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,
        "scope": code_data["scope"]
    }

def verify_pkce(verifier: str, challenge: str, method: str) -> bool:
    if method == "S256":
        computed = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        return secrets.compare_digest(computed, challenge)
    elif method == "plain":
        return secrets.compare_digest(verifier, challenge)
    return False
```

### 4.12.2 Resource Server com Node.js (Express)

```javascript
const express = require('express');
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

const app = express();
const PORT = 3000;

// Cliente JWKS para obter chaves públicas
const client = jwksClient({
  jwksUri: 'https://auth.example.com/.well-known/jwks.json',
  cache: true,
  rateLimit: true,
  jwksRequestsPerMinute: 10
});

// Middleware de verificação de token
function verifyToken(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'No token provided' });
  }

  const token = authHeader.split(' ')[1];

  const decoded = jwt.decode(token, { complete: true });
  if (!decoded) {
    return res.status(401).json({ error: 'Invalid token format' });
  }

  // Obter chave pública pelo kid
  client.getSigningKey(decoded.header.kid, (err, key) => {
    if (err) {
      return res.status(401).json({ error: 'Unable to verify token' });
    }

    const signingKey = key.getPublicKey();

    jwt.verify(token, signingKey, {
      algorithms: ['RS256'],
      issuer: 'https://auth.example.com',
      audience: 'https://api.example.com'
    }, (err, payload) => {
      if (err) {
        return res.status(401).json({ error: 'Token verification failed' });
      }

      // Verificar se o token não foi revogado
      if (isTokenRevoked(payload.jti)) {
        return res.status(401).json({ error: 'Token revoked' });
      }

      req.token = payload;
      next();
    });
  });
}

// Middleware de verificação de scopes
function requireScope(...scopes) {
  return (req, res, next) => {
    const tokenScopes = (req.token.scope || '').split(' ');
    const hasAllScopes = scopes.every(scope =>
      tokenScopes.includes(scope)
    );

    if (!hasAllScopes) {
      return res.status(403).json({
        error: 'Insufficient scope',
        required: scopes,
        provided: tokenScopes
      });
    }

    next();
  };
}

// Rotas protegidas
app.get('/api/users',
  verifyToken,
  requireScope('read:users'),
  async (req, res) => {
    const users = await db.users.find();
    res.json(users);
  }
);

app.post('/api/users',
  verifyToken,
  requireScope('write:users'),
  async (req, res) => {
    const user = await db.users.create(req.body);
    res.status(201).json(user);
  }
);

app.delete('/api/users/:id',
  verifyToken,
  requireScope('delete:users'),
  async (req, res) => {
    await db.users.delete(req.params.id);
    res.status(204).send();
  }
);

// Rota de introspect (para tokens opacos)
app.post('/oauth2/introspect', async (req, res) => {
  const { token, token_type_hint } = req.body;

  // Validar autenticação do Resource Server
  const authResult = authenticateResourceServer(req);
  if (!authResult.authenticated) {
    return res.status(401).json({ error: 'Invalid client' });
  }

  try {
    const decoded = jwt.decode(token);
    if (!decoded) {
      return res.json({ active: false });
    }

    const isExpired = decoded.exp < Math.floor(Date.now() / 1000);
    const isRevoked = isTokenRevoked(decoded.jti);

    if (isExpired || isRevoked) {
      return res.json({ active: false });
    }

    return res.json({
      active: true,
      sub: decoded.sub,
      client_id: decoded.client_id,
      scope: decoded.scope,
      token_type: 'Bearer',
      exp: decoded.exp,
      iat: decoded.iat,
      iss: decoded.iss
    });
  } catch (error) {
    return res.json({ active: false });
  }
});

app.listen(PORT, () => {
  console.log(`Resource Server running on port ${PORT}`);
});
```

### 4.12.3 Client com Python (Flask)

```python
from flask import Flask, redirect, request, session, jsonify
import requests
import secrets
import hashlib
import base64
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configuração
AUTH_SERVER = os.environ.get('AUTH_SERVER', 'https://auth.example.com')
CLIENT_ID = os.environ.get('CLIENT_ID', 'my-client-id')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET', 'my-client-secret')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')
API_SERVER = os.environ.get('API_SERVER', 'https://api.example.com')

@app.route('/')
def index():
    if 'access_token' in session:
        return jsonify({
            'authenticated': True,
            'user': session.get('user_info')
        })
    return jsonify({'authenticated': False})

@app.route('/login')
def login():
    # Gerar PKCE
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')

    # Armazenar na sessão
    session['pkce_code_verifier'] = code_verifier
    session['oauth_state'] = secrets.token_urlsafe(16)

    # Construir URL de autorização
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid profile email',
        'state': session['oauth_state'],
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }

    auth_url = f"{AUTH_SERVER}/authorize?{requests.compat.urlencode(auth_params)}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Verificar state
    if request.args.get('state') != session.get('oauth_state'):
        return 'State mismatch — possible CSRF attack', 403

    code = request.args.get('code')
    if not code:
        return 'No authorization code received', 400

    # Trocar código por tokens
    token_response = requests.post(f"{AUTH_SERVER}/token", data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code_verifier': session.get('pkce_code_verifier')
    })

    if token_response.status_code != 200:
        return 'Token exchange failed', 400

    tokens = token_response.json()

    # Armazenar tokens na sessão
    session['access_token'] = tokens['access_token']
    session['refresh_token'] = tokens.get('refresh_token')
    session['token_expires_at'] = (
        time.time() + tokens.get('expires_in', 3600)
    )

    # Limpar dados temporários
    session.pop('pkce_code_verifier', None)
    session.pop('oauth_state', None)

    # Buscar informações do usuário
    if 'openid' in tokens.get('scope', ''):
        userinfo_response = requests.get(
            f"{AUTH_SERVER}/userinfo",
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        if userinfo_response.status_code == 200:
            session['user_info'] = userinfo_response.json()

    return redirect('/')

@app.route('/api/<path:path>')
def proxy_api(path):
    if 'access_token' not in session:
        return redirect('/login')

    # Verificar expiração
    if time.time() > session.get('token_expires_at', 0):
        # Renovar token
        refresh_response = requests.post(f"{AUTH_SERVER}/token", data={
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        })

        if refresh_response.status_code == 200:
            tokens = refresh_response.json()
            session['access_token'] = tokens['access_token']
            session['refresh_token'] = tokens.get('refresh_token')
            session['token_expires_at'] = (
                time.time() + tokens.get('expires_in', 3600)
            )
        else:
            session.clear()
            return redirect('/login')

    # Fazer request à API
    api_response = requests.get(
        f"{API_SERVER}/{path}",
        headers={'Authorization': f"Bearer {session['access_token']}"}
    )

    return jsonify(api_response.json()), api_response.status_code

@app.route('/logout')
def logout():
    # Revogar tokens
    if 'access_token' in session:
        requests.post(f"{AUTH_SERVER}/revoke", data={
            'token': session['access_token'],
            'token_type_hint': 'access_token'
        })

    if 'refresh_token' in session:
        requests.post(f"{AUTH_SERVER}/revoke", data={
            'token': session['refresh_token'],
            'token_type_hint': 'refresh_token'
        })

    # Limpar sessão
    session.clear()

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=False, port=5000)
```

### 4.12.4 Validação de JWT em Go

```go
package main

import (
	"crypto/rsa"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type TokenValidator struct {
	JWKSURL     string
	Issuer      string
	Audience    string
	keyCache    map[string]*rsa.PublicKey
	cacheExpiry time.Time
}

type JWKS struct {
	Keys []JWK `json:"keys"`
}

type JWK struct {
	Kid string `json:"kid"`
	Kty string `json:"kty"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	N   string `json:"n"`
	E   string `json:"e"`
}

func NewTokenValidator(jwksURL, issuer, audience string) *TokenValidator {
	return &TokenValidator{
		JWKSURL:  jwksURL,
		Issuer:   issuer,
		Audience: audience,
		keyCache: make(map[string]*rsa.PublicKey),
	}
}

func (tv *TokenValidator) Validate(tokenString string) (*jwt.Token, error) {
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
		// Verificar algoritmo
		if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}

		// Obter kid do header
		kid, ok := token.Header["kid"].(string)
		if !ok {
			return nil, fmt.Errorf("missing kid in token header")
		}

		// Buscar chave pública (com cache)
		return tv.getPublicKey(kid)
	},
		jwt.WithIssuer(tv.Issuer),
		jwt.WithAudience(tv.Audience),
		jwt.WithExpirationRequired(),
	)

	if err != nil {
		return nil, fmt.Errorf("token validation failed: %w", err)
	}

	return token, nil
}

func (tv *TokenValidator) getPublicKey(kid string) (*rsa.PublicKey, error) {
	// Verificar cache
	if key, ok := tv.keyCache[kid]; ok && time.Now().Before(tv.cacheExpiry) {
		return key, nil
	}

	// Buscar JWKS
	resp, err := http.Get(tv.JWKSURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch JWKS: %w", err)
	}
	defer resp.Body.Close()

	var jwks JWKS
	if err := json.NewDecoder(resp.Body).Decode(&jwks); err != nil {
		return nil, fmt.Errorf("failed to decode JWKS: %w", err)
	}

	// Atualizar cache
	for _, jwk := range jwks.Keys {
		if jwk.Use == "sig" && jwk.Alg == "RS256" {
			key, err := parseRSAPublicKey(jwk)
			if err == nil {
				tv.keyCache[jwk.Kid] = key
			}
		}
	}

	tv.cacheExpiry = time.Now().Add(1 * time.Hour)

	key, ok := tv.keyCache[kid]
	if !ok {
		return nil, fmt.Errorf("key not found for kid: %s", kid)
	}

	return key, nil
}

// Middleware de autorização
func RequireScope(validScopes ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			authHeader := r.Header.Get("Authorization")
			if !strings.HasPrefix(authHeader, "Bearer ") {
				http.Error(w, "Missing authorization header", http.StatusUnauthorized)
				return
			}

			tokenString := strings.TrimPrefix(authHeader, "Bearer ")

			token, err := validator.Validate(tokenString)
			if err != nil {
				http.Error(w, "Invalid token", http.StatusUnauthorized)
				return
			}

			claims, ok := token.Claims.(jwt.MapClaims)
			if !ok {
				http.Error(w, "Invalid token claims", http.StatusUnauthorized)
				return
			}

			// Verificar scopes
			scopeStr, _ := claims["scope"].(string)
			tokenScopes := strings.Split(scopeStr, " ")

			for _, required := range validScopes {
				found := false
				for _, have := range tokenScopes {
					if have == required {
						found = true
						break
					}
				}
				if !found {
					http.Error(w, "Insufficient scope", http.StatusForbidden)
					return
				}
			}

			next.ServeHTTP(w, r)
		})
	}
}
```

---

## 4.13 Caso de Estudo: OAuth 2.0 e o Misantropi4

O ataque Misantropi4 ao IDAP (Instituto de Identificação Digital do Brasil) expôs milhões de credenciais brasileiras através de credential stuffing. Embora o ataque tenha se baseado em credenciais de login direto, a perspectiva do OAuth 2.0 oferece lições valiosas sobre defesa em profundidade.

### 4.13.1 Como OAuth 2.0 teria mitigado o ataque

Se o IDAP tivesse implementado OAuth 2.0 como camada intermediária de autenticação, os seguintes mecanismos teriam dificultado o ataque:

1. **MFA no Authorization Server**: O Authorization Server poderia exigir MFA antes de emitir tokens, tornando credenciais roubadas insuficientes para acesso.

2. **Rate limiting no Authorization Endpoint**: Controle rigoroso de tentativas de autenticação, com bloqueio progressivo de IPs e contas após múltiplas falhas.

3. **Tokens de curta duração**: Mesmo que credenciais fossem comprometidas, tokens de curta duração limitariam a janela de exploração.

4. **Detecção de anomalias**: O Authorization Server poderia detectar logins de localizações incomuns, dispositivos desconhecidos, ou padrões de acesso anômalos.

5. **Revogação imediata**: Quando o ataque fosse detectado, tokens poderiam ser revogados instantaneamente, removendo acesso não autorizado.

6. **Client binding**: Tokens vinculados a clients específicos impediriam que credenciais comprometidas fossem usadas por qualquer aplicação.

### 4.13.2 Lições aprendidas

O caso Misantropi4 reforça que:

- **Autenticação direta com credenciais é frágil**: Credenciais podem ser vazadas, reutilizadas, e credential-stuffed. OAuth 2.0 adiciona uma camada de abstração que limita o impacto.

- **MFA não é opcional**: Para serviços governamentais e de identidade, MFA é obrigatória. OAuth 2.0 facilita a integração com provedores de MFA.

- **Monitoramento é essencial**: OAuth 2.0 permite auditoria granular — cada token é rastreável a uma sessão específica de autorização, facilitando detecção de atividade maliciosa.

- **Defesa em profundidade funciona**: Não existe uma única solução mágica. A combinação de OAuth 2.0 + PKCE + MFA + rate limiting + monitoramento cria múltiplas camadas de defesa.

---

## 4.14 Referências

- RFC 6749 — The OAuth 2.0 Authorization Framework
- RFC 6750 — Bearer Token Usage
- RFC 7009 — Token Revocation
- RFC 7636 — Proof Key for Code Exchange (PKCE)
- RFC 7662 — Token Introspection
- RFC 8628 — OAuth 2.0 Device Authorization Grant
- RFC 8705 — OAuth 2.0 Mutual-TLS Client Authentication
- RFC 9449 — OAuth 2.0 Demonstrating Proof-of-Possession (DPoP)
- RFC 9700 — OAuth 2.0 Security Best Current Practice
- OAuth 2.0 Threat Model and Security Considerations (RFC 6819)
- OWASP OAuth Security Cheat Sheet
- Auth0 Best Practices Documentation
- Authlib — Python OAuth Library
- node-openid-client — Node.js OIDC/OAuth Client

---

## 4.15 OAuth 2.1 — A Evolução do Padrão

OAuth 2.1 é uma proposta de consolidação das melhores práticas e extensões mais importantes do OAuth 2.0 em um único documento. Publicado como draft-ietf-oauth-v2-1, ele NÃO é um protocolo novo — é uma refinamento que incorpora RFCs adicionais e remove opções inseguras.

### 4.15.1 Mudanças principais do OAuth 2.1

1. **PKCE obrigatório**: O PKCE é exigido para todos os clients, eliminando a opção de usar Authorization Code sem PKCE. Isso mitiga authorization code injection e interception.

2. **Implicit Flow removido**: O Implicit Flow (response_type=token) é oficialmente removido. Nunca deve ser usado em novas implementações.

3. **ROPC removido**: O Resource Owner Password Credentials grant é oficialmente removido.

4. **Redirect URI validação rígida**: Comparação exata de redirect URIs, sem normalização permissiva. Sem curingas.

5. **Refresh token sender-constraining**: Refresh tokens devem ser vinculados ao client que os solicitou.

6. **Bearer token usage refinado**: Regras mais precisas sobre como e onde tokens podem ser transmitidos.

### 4.15.2 Implicações para implementações existentes

```python
# Verificação de conformidade com OAuth 2.1
class OAuth21ComplianceChecker:
    def __init__(self, authorization_server_config: dict):
        self.config = authorization_server_config
        self.violations = []

    def check_all(self) -> list:
        self.violations = []
        self._check_pkce_required()
        self._check_implicit_flow_disabled()
        self._check_ropc_disabled()
        self._check_redirect_uri_exact_match()
        self._check_refresh_token_binding()
        self._check_token_lifetime()
        self._check_tls_required()
        return self.violations

    def _check_pkce_required(self):
        """PKCE deve ser obrigatório para todos os clients."""
        if not self.config.get("pkce_required", False):
            self.violations.append({
                "rule": "PKCE-OBLIGATORIO",
                "severity": "CRITICAL",
                "description": (
                    "PKCE não é obrigatório. OAuth 2.1 exige PKCE "
                    "para TODOS os clients, incluindo confidenciais."
                ),
                "remediation": (
                    "Habilitar pkce_required=true e aceitar apenas "
                    "code_challenge_method=S256."
                )
            })

    def _check_implicit_flow_disabled(self):
        """Implicit Flow deve estar desabilitado."""
        if "implicit" in self.config.get("allowed_grant_types", []):
            self.violations.append({
                "rule": "IMPLICIT-REMOTION",
                "severity": "CRITICAL",
                "description": (
                    "Implicit Flow ainda está habilitado. "
                    "OAuth 2.1 remove completamente este grant type."
                ),
                "remediation": (
                    "Remover implicit do allowed_grant_types. "
                    "Migrar clients para Authorization Code + PKCE."
                )
            })

    def _check_ropc_disabled(self):
        """ROPC deve estar desabilitado."""
        if "password" in self.config.get("allowed_grant_types", []):
            self.violations.append({
                "rule": "ROPC-REMOTION",
                "severity": "CRITICAL",
                "description": (
                    "ROPC (password grant) ainda está habilitado. "
                    "OAuth 2.1 remove completamente este grant type."
                ),
                "remediation": (
                    "Remover password do allowed_grant_types. "
                    "Migrar para Authorization Code + PKCE."
                )
            })

    def _check_redirect_uri_exact_match(self):
        """Redirect URIs devem ser comparadas exatamente."""
        if self.config.get("redirect_uri_matching", "exact") != "exact":
            self.violations.append({
                "rule": "REDIRECT-URI-EXACT",
                "severity": "HIGH",
                "description": (
                    "A validação de redirect_uri não está configurada "
                    "para comparação exata."
                ),
                "remediation": (
                    "Configurar redirect_uri_matching=exact. "
                    "NÃO usar curingas ou normalização permissiva."
                )
            })

    def _check_refresh_token_binding(self):
        """Refresh tokens devem ser vinculados ao client."""
        if not self.config.get("refresh_token_sender_constraining", False):
            self.violations.append({
                "rule": "REFRESH-TOKEN-BINDING",
                "severity": "HIGH",
                "description": (
                    "Refresh tokens não estão vinculados ao client. "
                    "OAuth 2.1 exige sender-constraining."
                ),
                "remediation": (
                    "Implementar binding de refresh token ao client_id. "
                    "Rejeitar refresh tokens de clients diferentes."
                )
            })

    def _check_token_lifetime(self):
        """Verificar tempos de vida dos tokens."""
        max_access = self.config.get("max_access_token_lifetime", 0)
        if max_access > 3600:  # Mais de 1 hora
            self.violations.append({
                "rule": "TOKEN-LIFETIME",
                "severity": "MEDIUM",
                "description": (
                    f"Access token lifetime máximo é {max_access}s "
                    f"(>{3600}s). Recomenda-se no máximo 1 hora."
                ),
                "remediation": (
                    "Reduzir max_access_token_lifetime para 3600s ou menos."
                )
            })

    def _check_tls_required(self):
        """TLS deve ser obrigatório em todos os endpoints."""
        if not self.config.get("tls_required", True):
            self.violations.append({
                "rule": "TLS-OBIGATORIO",
                "severity": "CRITICAL",
                "description": "TLS não é obrigatório em todos os endpoints.",
                "remediation": (
                    "Configurar tls_required=true. Rejeitar requests HTTP."
                )
            })
```

### 4.15.3 Timeline de migração para OAuth 2.1

Organizações devem planejar a migração para OAuth 2.1 gradualmente:

**Fase 1 (Imediato)**:
- Habilitar PKCE para todos os novos clients
- Desabilitar Implicit Flow para novos clients
- Implementar redirect URI matching exato
- Implementar refresh token rotation

**Fase 2 (3-6 meses)**:
- Migrar clients existentes do Implicit Flow para Authorization Code + PKCE
- Migrar clients do ROPC para Authorization Code + PKCE
- Implementar refresh token sender-constraining
- Configurar tempos de vida apropriados

**Fase 3 (6-12 meses)**:
- Remover suporte a Implicit Flow do Authorization Server
- Remover suporte a ROPC do Authorization Server
- Auditoria de conformidade completa
- Testes de penetração focados em OAuth 2.1

---

## 4.16 Token Binding e DPoP

### 4.16.1 O problema de tokens não vinculados

Em OAuth 2.0 tradicional, tokens são "bearer tokens" — qualquer um que possua o token pode usá-lo. Se um token é interceptado (via MITM, XSS, ou vazamento de logs), o atacante pode usá-lo normalmente. O Authorization Server e o Resource Server não conseguem distinguir entre o uso legítimo e o uso fraudulento.

DPoP (Demonstrating Proof-of-Possession, RFC 9449) resolve isso exigindo que o Client prove que possui uma chave privada específica. O token é vinculado à chave pública, e cada request deve incluir uma prova de posse.

### 4.16.2 Como DPoP funciona

**Passo 1 — Client gera par de chaves:**

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import base64

# Gerar par de chaves RSA
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

public_key = private_key.public_key()

# Exportar chave pública em formato JWK
public_numbers = public_key.public_numbers()

def int_to_base64url(n: int) -> str:
    byte_length = (n.bit_length() + 7) // 8
    n_bytes = n.to_bytes(byte_length, byteorder='big')
    return base64.urlsafe_b64encode(n_bytes).rstrip(b'=').decode('ascii')

jwk = {
    "kty": "RSA",
    "n": int_to_base64url(public_numbers.n),
    "e": int_to_base64url(public_numbers.e),
    "alg": "RS256",
    "use": "sig"
}
```

**Passo 2 — Client gera DPoP proof para cada request:**

```python
import jwt
import time
import hashlib
import httpx

def create_dpop_proof(
    private_key,
    http_method: str,
    http_uri: str,
    access_token: str = None,
    jti_claims: dict = None
) -> str:
    """Criar DPoP proof JWT."""
    now = int(time.time())

    header = {
        "typ": "dpop+jwt",
        "alg": "RS256",
        "jwk": get_jwk_from_private_key(private_key)
    }

    payload = {
        "htm": http_method.upper(),
        "htu": http_uri,
        "iat": now,
        "jti": secrets.token_urlsafe(16)
    }

    if access_token:
        # Hash do access token para binding
        payload["ath"] = base64.urlsafe_b64encode(
            hashlib.sha256(access_token.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

    return jwt.encode(payload, private_key, algorithm="RS256",
                      headers=header)

# Uso em requisições
async def request_with_dpop(
    url: str,
    method: str,
    access_token: str,
    private_key
):
    # Criar DPoP proof para esta request
    dpop_proof = create_dpop_proof(
        private_key=private_key,
        http_method=method,
        http_uri=url,
        access_token=access_token
    )

    headers = {
        "Authorization": f"DPoP {access_token}",
        "DPoP": dpop_proof
    }

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method, url, headers=headers
        )
        return response
```

**Passo 3 — Authorization Server emite token vinculado:**

```python
# No Authorization Server, durante o token request
async def issue_dpop_bound_token(request):
    # Validar DPoP proof do client
    dpop_proof = request.headers.get("DPoP")
    if not dpop_proof:
        raise HTTPException(400, "DPoP proof required")

    # Validar DPoP proof
    dpop_header = jwt.get_unverified_header(dpop_proof)
    if dpop_header.get("typ") != "dpop+jwt":
        raise HTTPException(400, "Invalid DPoP proof type")

    # Extrair chave pública do DPoP proof
    client_jwk = dpop_header.get("jwk")
    client_key = parse_jwk(client_jwk)

    # Validar assinatura
    dpop_claims = jwt.decode(dpop_proof, client_key, algorithms=["RS256"])

    # Verificar htm e htu
    if dpop_claims["htm"] != "POST":
        raise HTTPException(400, "Invalid HTTP method in DPoP")
    if dpop_claims["htu"] != token_endpoint_url:
        raise HTTPException(400, "Invalid HTTP URI in DPoP")

    # Gerar token vinculado à DPoP key
    thumbprint = compute_jwk_thumbprint(client_jwk)

    access_token = jwt.encode(
        {
            "sub": user_id,
            "iss": issuer,
            "aud": audience,
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "cnf": {
                "jkt": thumbprint  # Confirmation key thumbprint
            }
        },
        signing_key,
        algorithm="RS256"
    )

    return {"access_token": access_token, "token_type": "DPoP"}
```

**Passo 4 — Resource Server valida DPoP:**

```python
def validate_dpop_bound_token(
    access_token: str,
    dpop_proof: str,
    expected_http_method: str,
    expected_http_uri: str
) -> dict:
    """Validar access token DPoP-bound com proof."""

    # Decodificar access token (sem validar assinatura ainda)
    token_header = jwt.get_unverified_header(access_token)
    token_claims = jwt.decode(
        access_token, options={"verify_signature": False}
    )

    # Verificar DPoP confirmation
    cnf = token_claims.get("cnf")
    if not cnf or "jkt" not in cnf:
        raise HTTPException(401, "Token not DPoP-bound")

    expected_jkt = cnf["jkt"]

    # Validar DPoP proof
    dpop_header = jwt.get_unverified_header(dpop_proof)
    if dpop_header.get("typ") != "dpop+jwt":
        raise HTTPException(401, "Invalid DPoP proof type")

    dpop_jwk = dpop_header.get("jwk")
    dpop_key = parse_jwk(dpop_jwk)

    # Verificar que DPoP key corresponde ao token
    actual_jkt = compute_jwk_thumbprint(dpop_jwk)
    if actual_jkt != expected_jkt:
        raise HTTPException(401, "DPoP key mismatch")

    # Validar assinatura do DPoP proof
    dpop_claims = jwt.decode(dpop_proof, dpop_key, algorithms=["RS256"])

    # Verificar htm e htu
    if dpop_claims["htm"] != expected_http_method:
        raise HTTPException(401, "DPoP HTTP method mismatch")
    if dpop_claims["htu"] != expected_http_uri:
        raise HTTPException(401, "DPoP HTTP URI mismatch")

    # Verificar ath (access token hash)
    expected_ath = base64.urlsafe_b64encode(
        hashlib.sha256(access_token.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    if dpop_claims.get("ath") != expected_ath:
        raise HTTPException(401, "DPoP access token hash mismatch")

    # Validar assinatura do access token
    signing_key = get_signing_key(token_header["kid"])
    final_claims = jwt.decode(
        access_token, signing_key,
        algorithms=["RS256"],
        audience=expected_audience,
        issuer=expected_issuer
    )

    return final_claims
```

### 4.16.3 Mutual TLS (mTLS) para OAuth 2.0

MTLS (RFC 8705) é uma alternativa a DPoP que usa certificados de cliente TLS para vincular tokens ao client. É mais adequado para ambientes enterprise com infraestrutura PKI existente.

**Como mTLS funciona:**

1. O client apresenta um certificado de cliente durante o handshake TLS
2. O Authorization Server valida o certificado contra uma trust chain conhecida
3. O Authorization Server emite tokens vinculados ao thumbprint do certificado
4. O Resource Server valida que o certificado apresentado corresponde ao token

```python
# Configuração de mTLS no Authorization Server
MTLS_CONFIG = {
    "trusted_ca_certificates": [
        "/certs/ca-corporate.pem",
        "/certs/ca-client.pem"
    ],
    "mtls_endpoint_aliases": {
        "token_endpoint": "https://mtls.auth.example.com/token",
        "revocation_endpoint": "https://mtls.auth.example.com/revoke"
    },
    "require_client_certificate": True,
    "allow_self_signed_certificates": False,
    "certificate_binding_required": True
}

# Validação de certificado de cliente
def validate_client_certificate(cert_pem: bytes) -> dict:
    """Validar certificado de cliente TLS."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    cert = x509.load_pem_x509_certificate(cert_pem)

    # Verificar chain de confiança
    for ca_cert_path in MTLS_CONFIG["trusted_ca_certificates"]:
        ca_cert = load_ca_certificate(ca_cert_path)
        try:
            ca_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                cert.signature_hash_algorithm,
                cert.issuer.public_bytes()
            )
            # Certificado válido
            break
        except Exception:
            continue
    else:
        raise ValueError("Certificate not trusted")

    # Calcular thumbprint
    thumbprint = cert.fingerprint(hashes.SHA256).hex()

    return {
        "x5t#S256": thumbprint,
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_before": cert.not_valid_before,
        "not_after": cert.not_valid_after,
        "serial_number": str(cert.serial_number)
    }
```

---

## 4.17 Auditoria e Monitoramento de OAuth 2.0

### 4.17.1 Eventos que devem ser auditados

Todo Authorization Server e Resource Server devem registrar eventos de segurança:

**Eventos de Autenticação:**
- Tentativa de autenticação (sucesso e falha)
- Autenticação com MFA (sucesso e falha)
- Bloqueio de conta
- Desbloqueio de conta
- Alteração de senha

**Eventos de Autorização:**
- Emissão de código de autorização
- Troca de código por token (sucesso e falha)
- Emissão de refresh token
- Renovação de refresh token
- Revogação de token
- Uso de token (access token introspection)

**Eventos de Segurança:**
- State mismatch detectado (possível CSRF)
- PKCE validation failed
- Token reuse detected (possível comprometimento)
- Audience mismatch
- Issuer mismatch
- Token expirado utilizado
- Rate limit exceeded
- Redirect URI mismatch

### 4.17.2 Implementação de auditoria

```python
import json
from datetime import datetime
from enum import Enum

class AuthEvent(Enum):
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_MFA_REQUIRED = "auth.mfa_required"
    AUTH_MFA_SUCCESS = "auth.mfa_success"
    AUTH_MFA_FAILURE = "auth.mfa_failure"
    AUTH_LOCKED = "auth.locked"
    TOKEN_ISSUED = "token.issued"
    TOKEN_EXCHANGE = "token.exchange"
    TOKEN_EXCHANGE_FAILED = "token.exchange_failed"
    TOKEN_REFRESH = "token.refresh"
    TOKEN_REVOKED = "token.revoked"
    TOKEN_REUSE_DETECTED = "token.reuse_detected"
    TOKEN_INTROSPECT = "token.introspect"
    STATE_MISMATCH = "security.state_mismatch"
    PKCE_FAILED = "security.pkce_failed"
    AUDIENCE_MISMATCH = "security.audience_mismatch"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"
    REDIRECT_URI_MISMATCH = "security.redirect_uri_mismatch"

class OAuthAuditLogger:
    def __init__(self, logger_name: str = "oauth2.audit"):
        self.logger = logging.getLogger(logger_name)

    def log_event(
        self,
        event: AuthEvent,
        details: dict = None,
        request_metadata: dict = None
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event.value,
            "details": details or {},
            "request": request_metadata or {},
            "severity": self._get_severity(event)
        }

        self.logger.info(json.dumps(entry))

        # Alertar sobre eventos críticos
        if entry["severity"] == "CRITICAL":
            self._send_alert(entry)

    def _get_severity(self, event: AuthEvent) -> str:
        critical_events = {
            AuthEvent.TOKEN_REUSE_DETECTED,
            AuthEvent.AUTH_LOCKED,
            AuthEvent.PKCE_FAILED,
            AuthEvent.REDIRECT_URI_MISMATCH
        }
        high_events = {
            AuthEvent.AUTH_FAILURE,
            AuthEvent.TOKEN_EXCHANGE_FAILED,
            AuthEvent.STATE_MISMATCH,
            AuthEvent.AUDIENCE_MISMATCH,
            AuthEvent.RATE_LIMIT_EXCEEDED
        }

        if event in critical_events:
            return "CRITICAL"
        elif event in high_events:
            return "HIGH"
        else:
            return "INFO"

    def _send_alert(self, entry: dict):
        """Enviar alerta para equipe de segurança."""
        # Implementar notificação (email, Slack, PagerDuty, etc.)
        pass

# Uso no fluxo OAuth
audit = OAuthAuditLogger()

@app.get("/authorize")
async def authorize(request: AuthorizationRequest):
    client = validate_client(request.client_id)
    if not client:
        audit.log_event(
            AuthEvent.AUTH_FAILURE,
            details={"reason": "invalid_client", "client_id": request.client_id},
            request_metadata=get_request_meta(request)
        )
        raise HTTPException(400, "Invalid client")

    # ... restante do fluxo ...

    audit.log_event(
        AuthEvent.AUTH_SUCCESS,
        details={
            "client_id": request.client_id,
            "scope": request.scope,
            "response_type": request.response_type
        },
        request_metadata=get_request_meta(request)
    )
```

---

## 4.18 Referências Adicionais

- RFC 9700 — OAuth 2.0 Security Best Current Practice
- draft-ietf-oauth-v2-1 — OAuth 2.1
- RFC 9449 — OAuth 2.0 DPoP
- RFC 8705 — OAuth 2.0 Mutual-TLS
- RFC 7591 — Dynamic Client Registration
- RFC 8414 — Authorization Server Metadata
- OAuth Threat Model (RFC 6819)
- OWASP OAuth Security Cheat Sheet
- Auth0 Architecture: Token Design
- Okta OAuth 2.0 Best Practices
- Google OAuth 2.0 Security Best Practices
- Microsoft Identity Platform Documentation

---

## 4.19 OAuth 2.0 para Aplicações Mobile

Aplicações mobile apresentam desafios únicos para OAuth 2.0. O binário do app pode ser descompilado, o armazenamento local pode ser acessado por outros apps, e o browser embutido pode ser manipulado.

### 4.19.1 Desafios específicos do mobile

1. **Client secret inseguro**: O client_secret não pode ser armazenado de forma segura em apps mobile — o binário pode ser descompilado e o segredo extraído. Apps mobile são classificados como clients públicos.

2. **Redirect URIs customizadas**: Apps mobile não têm URLs HTTP tradicionais. Eles usam custom URL schemes (ex: `myapp://callback`), Universal Links (iOS), ou App Links (Android).

3. **Browser embutido vs system browser**: Usar um browser embutido (WebView) é inseguro porque o app pode interceptar credenciais. O sistema browser (Chrome Custom Tabs, SFSafariViewController) é preferido.

4. **Armazenamento de tokens**: O armazenamento local do mobile é menos seguro que o de um servidor. Keychain (iOS) e Keystore (Android) devem ser usados.

### 4.19.2 Padrão OAuth para Native Apps (RFC 8252)

O RFC 8252 define o padrão oficial para OAuth 2.0 em apps nativos:

```python
# Configuração para app mobile
MOBILE_OAUTH_CONFIG = {
    # Usar sistema browser (NÃO WebView)
    "use_custom_tabs": True,  # Android: Chrome Custom Tabs
    "use_sfsafari": True,     # iOS: SFSafariViewController

    # Redirect URIs para apps
    "redirect_uris": [
        "com.myapp://oauth2/callback",
        "https://myapp.example.com/.well-known/apple-app-site-association"
    ],

    # PKCE obrigatório
    "require_pkce": True,
    "code_challenge_method": "S256",

    # Client público (sem client_secret)
    "public_client": True,

    # Token storage
    "token_storage": "keychain"
}
```

### 4.19.3 Implementação para app mobile

```python
@app.get("/mobile/login")
async def mobile_login(request: Request):
    """Iniciar login para app mobile."""
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")

    request.session["state"] = state
    request.session["nonce"] = nonce
    request.session["pkce_verifier"] = code_verifier

    redirect_uri = "com.myapp://oauth2/callback"

    params = {
        "response_type": "code",
        "client_id": MOBILE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    auth_url = f"{AUTH_SERVER}/authorize?{requests.compat.urlencode(params)}"

    return {"auth_url": auth_url, "redirect_uri": redirect_uri}

@app.post("/mobile/token")
async def mobile_token(request: Request):
    """Trocar código por token para app mobile."""
    body = await request.json()
    code = body.get("code")
    state = body.get("state")
    code_verifier = body.get("code_verifier")

    if state != request.session.get("state"):
        raise HTTPException(400, "State mismatch")

    token_response = requests.post(
        f"{AUTH_SERVER}/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "com.myapp://oauth2/callback",
            "client_id": MOBILE_CLIENT_ID,
            "code_verifier": code_verifier
        }
    )

    if token_response.status_code != 200:
        raise HTTPException(400, "Token exchange failed")

    return token_response.json()
```

### 4.19.4 Secure Storage em iOS e Android

```swift
// iOS Keychain
func saveToken(_ token: String, forKey key: String) {
    let data = token.data(using: .utf8)!
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: key,
        kSecValueData as String: data,
        kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
    ]
    SecItemDelete(query as CFDictionary)
    SecItemAdd(query as CFDictionary, nil)
}
```

```kotlin
// Android Keystore
fun saveToken(context: Context, key: String, token: String) {
    val keyStore = KeyStore.getInstance("AndroidKeyStore")
    keyStore.load(null)
    val secretKey = keyStore.getKey(key, null) as SecretKey?
    val cipher = Cipher.getInstance("AES/GCM/NoPadding")
    cipher.init(Cipher.ENCRYPT_MODE, secretKey ?: generateKey(key))
    val encrypted = cipher.doFinal(token.toByteArray())
    val iv = cipher.iv
    val prefs = context.getSharedPreferences("secure_storage", Context.MODE_PRIVATE)
    prefs.edit()
        .putString("${key}_encrypted", Base64.encodeToString(encrypted, Base64.NO_WRAP))
        .putString("${key}_iv", Base64.encodeToString(iv, Base64.NO_WRAP))
        .apply()
}
```

### 4.19.5 App-to-App OAuth

```python
@app.get("/app-auth/authorize")
async def app_auth_authorize(client_id: str, redirect_uri: str,
                              state: str, scope: str):
    """Autorizar app B a acessar dados do app A."""
    if not is_registered_app(client_id):
        raise HTTPException(400, "Unknown client app")

    if not validate_app_redirect(client_id, redirect_uri):
        raise HTTPException(400, "Invalid redirect URI")

    return await show_consent_screen(
        app_name=get_app_name(client_id),
        scopes=scope.split(),
        state=state,
        redirect_uri=redirect_uri
    )
```

---

## 4.20 Referências Adicionais

- RFC 9700 — OAuth 2.0 Security Best Current Practice
- draft-ietf-oauth-v2-1 — OAuth 2.1
- RFC 9449 — OAuth 2.0 DPoP
- RFC 8705 — OAuth 2.0 Mutual-TLS
- RFC 8252 — OAuth 2.0 for Native Apps
- RFC 7591 — Dynamic Client Registration
- RFC 8414 — Authorization Server Metadata
- OAuth Threat Model (RFC 6819)
- OWASP OAuth Security Cheat Sheet
- Auth0 Architecture: Token Design
- Google OAuth 2.0 Security Best Practices
- Apple App Store Review Guidelines (Security)

---

## Resumo

OAuth 2.0 é o pilar da autorização moderna na web. Este capítulo cobriu:

- **Fundamentos**: O modelo de quatro atores, endpoints, e a razão de ser do protocolo
- **Authorization Code Flow**: O fluxo mais recomendado, com todos os detalhes de segurança
- **PKCE**: Extensão obrigatória que previne interceptação e injeção de código
- **Client Credentials**: Para comunicação máquina-a-máquina
- **Device Authorization**: Para dispositivos com entrada limitada
- **ROPC (deprecado)**: Por que não usar e como migrar
- **Tipos de token**: Access tokens (JWT e opacos) e refresh tokens com rotation
- **Scopes**: Controle granular de permissões com exemplos dinâmicos
- **Ciclo de vida**: Emissão, uso, validação, renovação, e revogação
- **Segurança**: Melhores práticas, vulnerabilidades comuns, e mitigações
- **Implementação**: Exemplos completos em Python (FastAPI, Flask) e Node.js (Express)
- **Caso Misantropi4**: Lições de como OAuth 2.0 teria mitigado o ataque
- **OAuth 2.1**: A evolução do padrão e plano de migração
- **Token Binding**: DPoP e mTLS para vincular tokens ao holder
- **Auditoria**: Monitoramento e logging de eventos de segurança

O próximo capítulo explora OpenID Connect, a camada de identidade construída sobre OAuth 2.0 que adiciona autenticação ao protocolo de autorização.
