---
layout: default
title: "01-introducao-sql-avancado"
---

# Capítulo 1: Introdução ao SQL Avancado

## Sumário

- [1.1 Historia do SQL](#11-historia-do-sql)
- [1.2 SQL Padrão (ANSI/ISO)](#12-sql-padrão-ansiiso)
- [1.3 Dialectos Principais](#13-dialectos-principais)
- [1.4 DDL/DML/DCL/TCL](#14-ddldmldcltcl)
- [1.5 Variáveis e Variáveis Temporárias](#15-variáveis-e-variáveis-temporárias)
- [1.6 Funções de Janela (Window Functions)](#16-funções-de-janela-window-functions)
- [1.7 Common Table Expressions (CTEs)](#17-common-table-expressions-ctes)
- [1.8 PIVOT e UNPIVOT](#18-pivot-e-unpivot)
- [1.9 LATERAL Joins](#19-lateral-joins)
- [1.10 FILTER Clause](#110-filter-clause)
- [1.11 GROUPING SETS, ROLLUP e CUBE](#111-grouping-sets-rollup-e-cube)
- [1.12 EXPLAIN e Query Plans](#112-explain-e-query-plans)
- [1.13 Dicas de Produtividade](#113-dicas-de-produtividade)
- [1.14 SQL e Seguranca: Primeiros Principios](#114-sql-e-seguranca-primeiros-principios)

---

## 1.1 Historia do SQL

### Origens Acadêmicas: O Modelo Relacional

A historia do SQL comeca em 1970, quando Edgar F. Codd, um cientista da computacao britanico trabalhando no IBM San Jose Research Laboratory, publicou o artigo seminal "A Relational Model of Data for Large Shared Data Banks". Nesse artigo, Codd propôs uma abordagem fundamentalmente nova para organizar e acessar dados: o modelo relacional.

Antes de Codd, os sistemas de gerenciamento de bancos de dados utilizavam modelagens hierarquicas e em rede. Esses modelos exigiam que os programadores conhecessem a estrutura fisica dos dados para navegar entre registros. Um erro na traversia da estrutura podia corromper toda a consulta. O modelo relacional eliminou essa complexidade ao representar todos os dados como tuples (linhas) organizadas em relações (tabelas).

Codd definiu 12 regras para um sistema verdadeiramente relacional, embora na pratica nenhuma implementacao atenda a todas elas de forma completa. As regras incluiam garantias sobre a representacao de informacao, acesso garantido, ausencia de ponteiros, linguagem de consulta de uso geral, suporte a visoes, insercao e atualizacao seguras, independencia fisica dos dados, independencia logica dos dados, integridade de dados, autonomia distribuida e tolerancia a falhas. As regras incluiam garantias sobre a representacao de informacao, acesso garantido, ausencia de ponteiros, linguagem de consulta de uso geral, suporte a visoes, insercao e atualizacao seguras, independencia fisica dos dados, independencia logica dos dados, integridade de dados, autonomia distribuida e tolerancia a falhas.

O artigo original de Codd gerou controversa dentro da propria IBM. Donald Chamberlin e Raymond Boyce desenvolveram uma linguagem chamada SEQUEL (Structured English Query Language) como uma implementacao pratica das ideias de Codd. Essa linguagem evoluiria para se tornar o SQL que conhecemos hoje.

### System R: A Primeira Implementacao

Em 1974, o projeto System R foi iniciado no IBM Research em San Jose. O objetivo era demonstrar que o modelo relacional podia ser implementado de forma eficiente e util. A equipe do System R incluia Chamberlin, Boyce, Jim Gray, Bruce Lindsay, e outros pioneiros.

O System R introduziu varios conceitos que se tornaram fundamentais no SQL: o otimizador de consultas baseado em custo, transacoes ACID, e o mecanismo de bloqueio para concorrencia. Esses conceitos, embora basicos hoje, representaram avancos enormes na epoca.

O nome "SEQUEL" sofreu uma mudanca por questoes de marca registrada. O nome original fazia referencia a uma marca de avioes Hawker Siddeley, e a IBM precisou abreviar para SQL. A pronuncia "sequel" persistiu no uso cotidiano ate os dias atuais.

### SQL-86 e SQL-89: Primeiros Padroes

O primeiro padrao SQL foi publicado em 1986 como SQL-86, tambem conhecido como SQL-87 quando formalmente adotado pelo ISO. Esse padrao definia o nucleo da linguagem: comandos DDL (CREATE, ALTER, DROP), DML (SELECT, INSERT, UPDATE, DELETE), e regras basicas de integridade.

SQL-86 foi seguido por SQL-89, que adicionou regras de integridade referencial e regras de seguranca. O SQL-89 introduziu a clausula FOREIGN KEY, que formalizou o conceito de relacoes entre tabelas de forma declarativa.

### SQL-92: A Grande Consolidacao

SQL-92 representou um marco significativo na evolucao da linguagem. Foi o primeiro padrao amplamente implementado por multiplos vendors e introduziu muitas funcionalidades que consideramos fundamentais hoje:

- Subqueries correlacionadas
- JOINs explicitos (INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN)
- CASE expressions
- COALESCE e NULLIF
- UNION e INTERSECT
- Controle de transacoes (COMMIT, ROLLBACK)
- Cast de tipos (CAST)

```sql
-- Exemplo de SQL-92: JOIN explicito com CASE
SELECT
    e.employee_name,
    CASE
        WHEN e.salary > 80000 THEN 'Senior'
        WHEN e.salary > 50000 THEN 'Mid-level'
        ELSE 'Junior'
    END AS seniority_level,
    d.department_name
FROM employees e
INNER JOIN departments d ON e.dept_id = d.dept_id
WHERE e.hire_date > CAST('1995-01-01' AS DATE);
```

### SQL:1999 (SQL3): O Paradigma de Objetos

SQL:1999 introduziu suporte a programacao procedural e tipos de dados complexos. As principais adicoes foram:

- Stored procedures e funcoes definidas pelo usuario
- Triggers
- Tipos de dados estruturados (ROW, ARRAY)
- Suporte a heranca de tipos
- CTEs (Common Table Expressions) nao-recursive
- Funcoes de janela (window functions)
- Regexpressao integrada (SIMILAR TO)

```sql
-- SQL:1999 introduziu CTEs e funcoes de janela
WITH regional_sales AS (
    SELECT
        region,
        SUM(amount) AS total_sales
    FROM orders
    GROUP BY region
)
SELECT
    region,
    total_sales,
    ROW_NUMBER() OVER (ORDER BY total_sales DESC) AS rank
FROM regional_sales;
```

### SQL:2003 e a Evolucao Analitica

SQL:2003 adicionou funcionalidades orientadas a analise de dados:

- XML type
- Sequences (GENERATED ALWAYS AS IDENTITY)
- Funcoes de janela expandidas (frames, LAG, LEAD)
- MERGE statement (upsert)
- Funcoes de aggregate definidas pelo usuario

O MERGE statement merece atencao especial por ser uma das adicoes mais util e, ao mesmo tempo, mais propensas a erros de implementacao entre os dialectos:

```sql
-- MERGE: upsert padrao SQL
MERGE INTO inventory i
USING shipments s
    ON i.product_id = s.product_id
WHEN MATCHED AND s.quantity > 0 THEN
    UPDATE SET
        i.quantity = i.quantity + s.quantity,
        i.last_restocked = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (product_id, quantity, last_restocked)
    VALUES (s.product_id, s.quantity, CURRENT_TIMESTAMP);
```

### SQL:2006, SQL:2008, SQL:2011

Cada versao subsequente refinou a linguagem:

**SQL:2006** formalizou o suporte a XML com XPath e XQuery integrados. Isso permitiu consultas a documentos XML armazenados diretamente nas colunas do banco de dados.

**SQL:2008** adicionou o TRUNCATE statement como alternativa eficiente ao DELETE sem WHERE. Tambem introduziu FETCH FIRST (antecipando o LIMIT dos dialectos) e padronizou FETCH FIRST ... ROWS ONLY.

**SQL:2011** adicionou suporte a temporal data (PERIOD FOR), permitindo armazenar e consultar dados historicos de forma nativa. Isso foi particularmente importante para aplicacoes que precisavam de audit trails e time travel.

```sql
-- SQL:2011: temporal tables
CREATE TABLE employees (
    employee_id INTEGER,
    name VARCHAR(100),
    salary DECIMAL(10,2),
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    PERIOD FOR validity (valid_from, valid_to)
);
```

### SQL:2016 e SQL:2023: O Moderno

**SQL:2016** introduziu JSON nativo na linguagem padrao com JSON_VALUE, JSON_QUERY, JSON_TABLE, e JSON_EXISTS. Tambem adicionou row-level security (ALTER TABLE ... ADD ROW LEVEL SECURITY) e GRAPH_TABLE para consultas em grafos.

**SQL:2023**, a versao mais recente, adiciona:

- Property Graph Queries (SQL/PGQ)
- JSON semantics refinadas
- Vector similarity search (DISTANCE function)
- ML integracao basica
- Semantic JSON com schema validation

```sql
-- SQL:2023: property graph queries (sintaxe conceitual)
CREATE PROPERTY GRAPH customer_graph
    VERTEX TABLES (
        customers AS Customer
            KEY (customer_id)
        SET { name = customer_name }
    )
    EDGE TABLES (
        orders AS Places
            FROM Customer TO Customer
            KEY (order_id)
        SET { order_date = placed_at }
    );
```

### Linha do Tempo Resumida

| Ano | Versao | Contribuicao Principal |
|-----|--------|----------------------|
| 1970 | Artigo de Codd | Modelo relacional teorico |
| 1974 | SEQUEL | Primeira linguagem de consulta |
| 1979 | Oracle V2 | Primeiro produto comercial SQL |
| 1983 | IBM DB2 | Implementacao IBM do SQL |
| 1986 | SQL-86 | Primeiro padrao ISO |
| 1989 | SQL-89 | Integridade referencial |
| 1992 | SQL-92 | JOINs, CASE, subqueries |
| 1996 | PostgreSQL 6.0 | Open source, extensivel |
| 1999 | SQL:1999 | CTEs, janelas, procedural |
| 2003 | SQL:2003 | MERGE, XML, frames |
| 2010 | PostgreSQL 9.0 | JSON support iniciado |
| 2016 | SQL:2016 | JSON padrao, row security |
| 2023 | SQL:2023 | Graphs, vectors, ML |

---

## 1.2 SQL Padrão (ANSI/ISO)

### Organismos de Padronizacao

O SQL padrao e mantido conjuntamente pela ISO (International Organization for Standardization) e pelo IEC (International Electrotechnical Commission). O comite tecnico responsavel e o ISO/IEC JTC 1/SC 32 (Data management and interchange).

Diferente do que muitos imaginam, o padrao SQL nao e ditado por uma unica empresa. Embora gigantes como Oracle, IBM e Microsoft participem ativamente do comite, o processo e baseado em consenso e votacao entre os membros nacionais.

### Niveis de Conformidade

O padrao SQL define tres niveis de conformidade:

**Entry SQL** — O nivel minimo. Inclui operacoes basicas de SELECT, INSERT, UPDATE, DELETE, e CREATE TABLE. Qualquer banco de dados moderno atende a esse nivel.

**Intermediate SQL** — Adiciona JOINs explicitos, subqueries, transacoes, e controle de acesso. A maioria dos bancos comerciais atende a esse nivel.

**Full SQL** — Inclui todas as funcionalidades do padrao: CTEs, funcoes de janela, XML, JSON, stored procedures padrao, e operacoes temporais. Poucos bancos implementam o Full SQL completo.

Na pratica, nenhum dos principais SGBDR implementa 100% do padrao. Cada vendor adiciona extensoes proprias e, em alguns casos, implementa funcionalidades antes do padrao formaliza-las.

### Estrutura do Padrao SQL:2023

O padrao SQL e organizado em multiplos documentos:

- **Part 1: Framework** — Definicoes gerais e estrutura do padrao
- **Part 2: Foundation** — O nucleo da linguagem SQL (DDL, DML, Expressions)
- **Part 4: Persistent Stored Modules (SQL/PSM)** — Stored procedures, funcoes, triggers
- **Part 9: XML (SQL/XML)** — Operacoes com XML
- **Part 11: Schema Definition (SQL/Schemata)** — Definicao de esquemas
- **Part 13: Routines and Types (SQL/MED)** — Funcoes definidas pelo usuario
- **Part 14: XML-Related Specifications** — XPath, XQuery integrados
- **Part 15: JSON (SQL/JSON)** — Operacoes com JSON
- **Part 16: Property Graph Queries (SQL/PGQ)** — Consultas em grafos
- **Part 17: JSON (SQL/JSON) Revision** — Refinamentos JSON

### Como o Padrao Afeta o Desenvolvimento

O padrao SQL e importante para o desenvolvedor porque define um contrato de compatibilidade. Quando voce escreve uma consulta SQL que obedece ao padrao, essa consulta deve funcionar em qualquer banco de dados que implemente o padrao em相应的 nivel.

Na pratica, a realidade e mais complicada. Cada banco de dados tem extensoes proprias que tornam as consultas especificas de um dialect. O desafio do desenvolvedor e escrever codigo que aproveite o padrao sempre que possivel, e use extensoes do vendor apenas quando necessario.

```sql
-- Codigo padrao SQL:2016 que funciona na maioria dos bancos
SELECT
    customer_id,
    customer_name,
    SUM(order_amount) AS total_spent
FROM customers
JOIN orders USING (customer_id)
WHERE order_date >= CURRENT_DATE - INTERVAL '1' YEAR
GROUP BY customer_id, customer_name
HAVING SUM(order_amount) > 1000
ORDER BY total_spent DESC
FETCH FIRST 10 ROWS ONLY;
```

```sql
-- Mesma consulta com extensao PostgreSQL (LIMIT)
SELECT
    customer_id,
    customer_name,
    SUM(order_amount) AS total_spent
FROM customers
JOIN orders USING (customer_id)
WHERE order_date >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY customer_id, customer_name
HAVING SUM(order_amount) > 1000
ORDER BY total_spent DESC
LIMIT 10;
```

### Seguranca e o Padrao SQL

O padrao SQL define mecanismos de seguranca que nem sempre sao implementados por todos os vendors. Row-Level Security (RLS), definido no SQL:2016, e um exemplo. O PostgreSQL implementa RLS desde a versao 9.5, enquanto outros bancos podem ter implementacoes proprias ou ausentes.

A conformidade parcial com o padrao cria riscos de seguranca quando consultas escritas para um banco sao migradas para outro sem revisao adequada. Uma funcao de validacao que funciona corretamente em PostgreSQL pode se comportar de forma diferente em MySQL, criando brechas potenciais.

---

## 1.3 Dialectos Principais

### PostgreSQL

O PostgreSQL e um SGBDR open source com heranca do Berkeley Postgres Project. Comecou como POSTGRES em 1986 na Universidade de California, Berkeley, e foi renomeado para PostgreSQL em 1996 quando o padrao SQL foi incorporado.

**Versao e Edicoes:** O PostgreSQL segue um ciclo de versoes com lancamentos anuais (9.5, 9.6, 10, 11, ..., 17). Nao existe edicao "enterprise" — todas as funcionalidades estao disponiveis em todas as versoes.

**Caracteristicas Unicas:**

- Extensibilidade: CREATE FUNCTION em multiplos linguagens (PL/pgSQL, PL/Python, PL/V8)
- Tipos de dados customizados: CREATE TYPE, CREATE DOMAIN
- Heranca de tabelas
- Table Partitioning declarativo (desde 10)
- Logical Replication
- Full-text search nativo (tsvector, tsquery)
- JSONB com indexacao GIN
- Row-Level Security (RLS)
- Materialized Views com REFRESH CONCURRENTLY

```sql
-- PostgreSQL: extensibilidade com funcoes customizadas
CREATE OR REPLACE FUNCTION validate_cpf(cpf TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    digits INTEGER[];
    sum_val INTEGER := 0;
    remainder INTEGER;
BEGIN
    -- Remove non-numeric characters
    cpf := regexp_replace(cpf, '[^0-9]', '', 'g');

    IF LENGTH(cpf) != 11 THEN
        RETURN FALSE;
    END IF;

    -- Convert to integer array
    digits := ARRAY(SELECT CAST(digit AS INTEGER)
                    FROM regexp_split_to_table(cpf, '') AS digit);

    -- First check digit
    FOR i IN 1..9 LOOP
        sum_val := sum_val + digits[i] * (11 - i);
    END LOOP;
    remainder := sum_val % 11;
    IF remainder < 2 THEN remainder := 0;
    ELSE remainder := 11 - remainder;
    END IF;
    IF digits[10] != remainder THEN
        RETURN FALSE;
    END IF;

    -- Second check digit
    sum_val := 0;
    FOR i IN 1..10 LOOP
        sum_val := sum_val + digits[i] * (12 - i);
    END LOOP;
    remainder := sum_val % 11;
    IF remainder < 2 THEN remainder := 0;
    ELSE remainder := 11 - remainder;
    END IF;
    RETURN digits[11] = remainder;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Uso em constraints
ALTER TABLE customers
    ADD CONSTRAINT chk_cpf CHECK (validate_cpf(cpf));
```

**Diferencas de Sintaxe:**

| Feature | PostgreSQL | MySQL | SQL Server |
|---------|-----------|-------|------------|
| Limitar resultados | LIMIT n | LIMIT n | TOP n |
| Concatenar strings | \|\| ou CONCAT() | CONCAT() | + ou CONCAT() |
| Auto-incremento | SERIAL / GENERATED | AUTO_INCREMENT | IDENTITY |
| Upsert | ON CONFLICT ... DO | INSERT ... ON DUPLICATE | MERGE |
| Comentario de coluna | COMMENT ON | COMMENT | sp_addextendedproperty |
| Booleano | BOOLEAN | TINYINT(1) | BIT |

### MySQL

MySQL e o SGBDR open source mais utilizado no mundo, particularmente no ecossistema web. Foi criado por Michael Widenius e David Axmark em 1995, originalmente para uso com o MyISAM storage engine.

**Versao e Edicoes:** MySQL segue um modelo de versao dupla: Community Edition (gratuita) e Enterprise Edition (paga). O MariaDB e um fork open source criado em 2009 em preocupacao com a aquisicao da Sun Microsystems pela Oracle.

**Caracteristicas Unicas:**

- Storage Engine Architecture: InnoDB (padrao), MyISAM, Memory, Archive
- Replicacao nativa (async, semi-sync, group replication)
- MySQL Cluster (NDB) para alta disponibilidade
- Full-text search em InnoDB (desde 5.6)
- JSON type (desde 5.7)
- Window functions (desde 8.0)
- CTEs (desde 8.0)
- LATERAL derived tables (desde 8.0.14)

```sql
-- MySQL: INSERT com ON DUPLICATE KEY UPDATE
INSERT INTO product_inventory (product_id, quantity, last_updated)
VALUES (101, 50, NOW())
ON DUPLICATE KEY UPDATE
    quantity = quantity + VALUES(quantity),
    last_updated = NOW();

-- MySQL: JSON type com operadores
SELECT
    product_name,
    JSON_EXTRACT(attributes, '$.color') AS color,
    JSON_EXTRACT(attributes, '$.size') AS size,
    attributes->>'$.dimensions.weight' AS weight
FROM products
WHERE JSON_EXTRACT(attributes, '$.color') = 'red';
```

### SQLite

SQLite e um banco de dados serverless, embutido, e de uso livre. Criado por D. Richard Hipp em 2000, e provavelmente o banco de dados mais distribuido do mundo — presente em praticamente todos os smartphones, navegadores, e sistemas operacionais.

**Versao e Edicoes:** SQLite nao tem edicoes separadas. A unica versao e a biblioteca unica, tipicamente compilada como uma unica arquivo C.

**Caracteristicas Unicas:**

- Zero configuration: sem servidor, sem processo separado
- Single-file database
- Tipos flexiveis (type affinity, nao tipos estritos)
- Virtual tables (FTS5 para full-text search)
- JSON functions (desde 3.9.0)
- Window functions (desde 3.25.0)
- Recursive CTEs (desde 3.8.3)
- Amalgamation build (um unico arquivo .c)

```sql
-- SQLite: type affinity e flexibilidade
CREATE TABLE flexible_data (
    id INTEGER PRIMARY KEY,
    text_col TEXT,
    num_col REAL,
    blob_col BLOB
);

-- SQLite aceita qualquer tipo em qualquer coluna
INSERT INTO flexible_data VALUES (1, 'hello', 42, NULL);
INSERT INTO flexible_data VALUES (2, 3.14, 'world', X'DEADBEEF');
INSERT INTO flexible_data VALUES (3, NULL, NULL, NULL);

-- SQLite: JSON functions (3.9.0+)
SELECT
    json_extract(config, '$.theme') AS theme,
    json_extract(config, '$.notifications.email') AS email_notify
FROM user_preferences
WHERE json_type(config, '$.settings') = 'object';
```

### SQL Server

Microsoft SQL Server e um SGBDR comercial desenvolvido pela Microsoft desde 1989 (originalmente como Sybase SQL Server).

**Versao e Edicoes:** Express (gratuita), Standard, Enterprise, Developer (gratuita para desenvolvimento). Versoes anuais desde 2016 (2016, 2017, 2019, 2022).

**Caracteristicas Unicas:**

- T-SQL (Transact-SQL): extensao proprietaria com variaveis, controle de fluxo, tratamento de erros
- CLR integration: funcoes em C# e .NET
- Columnstore indexes para analytics
- Always Encrypted para encriptacao no cliente
- Dynamic Data Masking
- Temporal Tables (desde 2016)
- Adaptive Query Processing
- Intelligent Query Processing (desde 2019)

```sql
-- SQL Server: T-SQL com tratamento de erros
BEGIN TRY
    BEGIN TRANSACTION;

    UPDATE accounts
    SET balance = balance - @transfer_amount
    WHERE account_id = @from_account
    AND balance >= @transfer_amount;

    IF @@ROWCOUNT = 0
    BEGIN
        THROW 50001, 'Insufficient funds', 1;
    END

    UPDATE accounts
    SET balance = balance + @transfer_amount
    WHERE account_id = @to_account;

    INSERT INTO transaction_log (from_account, to_account, amount, created_at)
    VALUES (@from_account, @to_account, @transfer_amount, GETUTCDATE());

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    THROW;
END CATCH;
```

### Oracle

Oracle Database e o SGBDR comercial mais utilizado em empresas de grande porte. Criado por Larry Ellison, Bob Miner e Ed Oates em 1979 (originalmente como Software Development Laboratories).

**Versao e Edicoes:** XE (gratuita, limitada), Standard Edition, Enterprise Edition. Versoes principais seguem numeracao como 19c, 21c, 23c.

**Caracteristicas Unicas:**

- PL/SQL: linguagem procedural proprietaria robusta
- Automatic Workload Repository (AWR)
- Real Application Clusters (RAC) para alta disponibilidade
- Partitioning avancado (range, list, hash, composite)
- Advanced Queuing
- Flashback queries e tables
- Query Result Cache
- In-Memory Column Store

```sql
-- Oracle: PL/SQL com bulk operations
DECLARE
    TYPE t_employee_ids IS TABLE OF employees.employee_id%TYPE;
    l_ids t_employee_ids;

    TYPE t_salary_records IS RECORD (
        emp_id employees.employee_id%TYPE,
        old_salary employees.salary%TYPE,
        new_salary employees.salary%TYPE
    );
    TYPE t_salary_log IS TABLE OF t_salary_records;
    l_changes t_salary_log := t_salary_log();
BEGIN
    SELECT employee_id
    BULK COLLECT INTO l_ids
    FROM employees
    WHERE department_id = 10
    FOR UPDATE;

    FORALL i IN 1..l_ids.COUNT
        UPDATE employees
        SET salary = salary * 1.10
        WHERE employee_id = l_ids(i)
        RETURNING employee_id, salary - salary / 1.10, salary
        BULK COLLECT INTO l_changes;

    FORALL i IN 1..l_changes.COUNT
        INSERT INTO salary_audit (emp_id, old_sal, new_sal, changed_at)
        VALUES (l_changes(i).emp_id, l_changes(i).old_salary,
                l_changes(i).new_salary, SYSTIMESTAMP);

    COMMIT;
END;
/
```

### Comparacao Seguranca entre Dialectos

| Aspecto | PostgreSQL | MySQL | SQL Server | Oracle |
|---------|-----------|-------|------------|--------|
| Row-Level Security | Nativo (9.5+) | LIMITADO | Nativo (2016+) | VPDA/RLS |
| Encriptacao at rest | pgcrypto/PG 16+ | InnoDB tablespace | TDE nativo | TDE nativo |
| Encriptacao em transito | SSL/TLS nativo | SSL/TLS | Force Encryption | Native Network Encryption |
| Auditing | pgAudit extensão | Enterprise only | C2/Audit | Unified Auditing |
| Default user perms | Restrictivo | Relativamente aberto | Configuravel | Muito aberto |
| SQL Injection protection | Parametrizacao forte | Parametrizacao | Parametrizacao | Bind variables |

---

## 1.4 DDL/DML/DCL/TCL

### DDL: Data Definition Language

O DDL e responsavel por definir e modificar a estrutura dos dados no banco de dados. Cada comando DDL modifica o catalogo do banco de dados (data dictionary).

#### CREATE TABLE

```sql
-- DDL completa: CREATE TABLE com todas as opcoes
CREATE TABLE orders (
    order_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    order_number    VARCHAR(20) NOT NULL UNIQUE,
    order_date      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','processing','shipped',
                                      'delivered','cancelled','returned')),
    subtotal        DECIMAL(10,2) NOT NULL CHECK (subtotal >= 0),
    tax_amount      DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    total_amount    DECIMAL(10,2) GENERATED ALWAYS AS (subtotal + tax_amount) STORED,
    shipping_address_id BIGINT,
    billing_address_id  BIGINT,
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_orders_shipping_address
        FOREIGN KEY (shipping_address_id) REFERENCES addresses(address_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_orders_billing_address
        FOREIGN KEY (billing_address_id) REFERENCES addresses(address_id)
        ON DELETE SET NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date DESC);
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date DESC);
```

#### ALTER TABLE

```sql
-- Adicionar coluna
ALTER TABLE orders
    ADD COLUMN discount_code VARCHAR(50);

-- Modificar tipo de dado (com conversao)
ALTER TABLE orders
    ALTER COLUMN notes TYPE TEXT;

-- Adicionar constraint
ALTER TABLE orders
    ADD CONSTRAINT chk_discount CHECK (discount_code ~ '^[A-Z0-9]{4,10}$');

-- Adicionar constraint de unique
ALTER TABLE orders
    ADD CONSTRAINT uq_order_number UNIQUE (order_number);

-- Renomear coluna
ALTER TABLE orders RENAME COLUMN notes TO internal_notes;

-- Adicionar default
ALTER TABLE orders
    ALTER COLUMN status SET DEFAULT 'pending';
```

#### CREATE INDEX

```sql
-- Indice B-tree padrao
CREATE INDEX idx_customers_email ON customers(email);

-- Indice unico
CREATE UNIQUE INDEX idx_customers_cpf ON customers(cpf);

-- Indice parcial
CREATE INDEX idx_orders_pending ON orders(order_date)
    WHERE status = 'pending';

-- Indice composto com ordem especifica
CREATE INDEX idx_products_category_price ON products(category_id, price DESC);

-- Indice para full-text search (PostgreSQL)
CREATE INDEX idx_products_search ON products
    USING GIN(to_tsvector('portuguese', product_name || ' ' || description));

-- Indice para JSONB (PostgreSQL)
CREATE INDEX idx_products_attrs ON products
    USING GIN(attributes jsonb_path_ops);
```

### DML: Data Manipulation Language

O DML e responsavel por manipular os dados dentro das tabelas definidas pelo DDL.

#### SELECT Avancado

```sql
-- SELECT com CTE, window functions e aggregates
WITH monthly_revenue AS (
    SELECT
        date_trunc('month', order_date) AS month,
        status,
        COUNT(*) AS order_count,
        SUM(total_amount) AS revenue
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY date_trunc('month', order_date), status
),
ranked_months AS (
    SELECT
        month,
        status,
        order_count,
        revenue,
        SUM(revenue) OVER (
            PARTITION BY status
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,
        RANK() OVER (
            PARTITION BY status
            ORDER BY revenue DESC
        ) AS revenue_rank
    FROM monthly_revenue
)
SELECT * FROM ranked_months WHERE revenue_rank <= 3;
```

#### INSERT Avancado

```sql
-- INSERT com CTE (PostgreSQL, SQL Server)
WITH new_customer AS (
    INSERT INTO customers (name, email, created_at)
    VALUES ('Joao Silva', 'joao@example.com', CURRENT_TIMESTAMP)
    RETURNING customer_id
)
INSERT INTO addresses (customer_id, street, city, state, zip_code)
SELECT customer_id, 'Rua A, 123', 'Sao Paulo', 'SP', '01234-567'
FROM new_customer;

-- INSERT em massa (PostgreSQL)
INSERT INTO products (name, category_id, price, stock)
VALUES
    ('Widget A', 1, 29.99, 150),
    ('Widget B', 1, 39.99, 200),
    ('Gadget X', 2, 99.99, 50),
    ('Gadget Y', 2, 149.99, 30),
    ('Tool Z', 3, 19.99, 500);

-- INSERT ... SELECT
INSERT INTO order_summary (customer_id, total_orders, total_spent, last_order_date)
SELECT
    customer_id,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_spent,
    MAX(order_date) AS last_order_date
FROM orders
WHERE status != 'cancelled'
GROUP BY customer_id;
```

#### UPDATE Avancado

```sql
-- UPDATE com CTE
WITH price_adjustment AS (
    SELECT
        p.product_id,
        p.price AS old_price,
        p.price * (1 + COALESCE(c.adjustment_pct, 0)) AS new_price
    FROM products p
    LEFT JOIN category_adjustments c ON p.category_id = c.category_id
    WHERE c.effective_date <= CURRENT_DATE
)
UPDATE products
SET price = pa.new_price,
    price_updated_at = CURRENT_TIMESTAMP
FROM price_adjustment pa
WHERE products.product_id = pa.product_id
AND products.price != pa.new_price;

-- DELETE com subquery
DELETE FROM order_items
WHERE order_id IN (
    SELECT order_id
    FROM orders
    WHERE created_at < CURRENT_DATE - INTERVAL '7' YEAR
    AND status = 'cancelled'
);
```

#### MERGE (UPSERT)

```sql
-- MERGE padrao PostgreSQL (ON CONFLICT)
INSERT INTO product_reviews (product_id, user_id, rating, review_text)
VALUES (101, 42, 5, 'Excelente produto!')
ON CONFLICT (product_id, user_id) DO UPDATE SET
    rating = EXCLUDED.rating,
    review_text = EXCLUDED.review_text,
    updated_at = CURRENT_TIMESTAMP;

-- MySQL: INSERT ... ON DUPLICATE KEY UPDATE
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (101, 1, 50)
ON DUPLICATE KEY UPDATE
    quantity = quantity + VALUES(quantity),
    last_counted = NOW();

-- SQL Server: MERGE padrao
MERGE INTO target_table AS target
USING source_table AS source
    ON target.id = source.id
WHEN MATCHED THEN
    UPDATE SET
        target.col1 = source.col1,
        target.col2 = source.col2,
        target.updated_at = GETUTCDATE()
WHEN NOT MATCHED BY TARGET THEN
    INSERT (id, col1, col2, created_at)
    VALUES (source.id, source.col1, source.col2, GETUTCDATE())
WHEN NOT MATCHED BY SOURCE THEN
    DELETE;
```

### DCL: Data Control Language

O DCL controla o acesso aos dados e aos objetos do banco de dados.

```sql
-- Criar roles
CREATE ROLE app_readonly;
CREATE ROLE app_readwrite;
CREATE ROLE app_admin;

-- Conceder privilegios
GRANT CONNECT ON DATABASE myapp TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

GRANT CONNECT, CREATE ON DATABASE myapp TO app_readwrite;
GRANT USAGE, CREATE ON SCHEMA public TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;

-- Privilegios futuros
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO app_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_readwrite;

-- Revogar privilegios
REVOKE DELETE ON orders FROM app_readwrite;

-- Row-Level Security (PostgreSQL)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY orders_tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::INTEGER);

CREATE POLICY orders_own_data ON orders
    FOR SELECT
    USING (
        customer_id = current_setting('app.current_user_id')::INTEGER
        OR current_setting('app.current_user_role') = 'admin'
    );
```

### TCL: Transaction Control Language

O TCL gerencia as transacoes, garantindo propriedades ACID.

```sql
-- Transacao basica
BEGIN;
    UPDATE accounts SET balance = balance - 500 WHERE account_id = 1;
    UPDATE accounts SET balance = balance + 500 WHERE account_id = 2;
COMMIT;

-- Transacao com SAVEPOINT
BEGIN;
    INSERT INTO orders (customer_id, order_number) VALUES (1, 'ORD-001');

    SAVEPOINT after_order;

    INSERT INTO order_items (order_id, product_id, quantity)
    VALUES (currval('orders_order_id_seq'), 101, 5);

    -- Se o item invalido, podemos voltar ao savepoint
    -- ROLLBACK TO after_order;

    INSERT INTO order_items (order_id, product_id, quantity)
    VALUES (currval('orders_order_id_seq'), 102, 3);
COMMIT;

-- Configuracao de isolamento
BEGIN ISOLATION LEVEL SERIALIZABLE;
    -- Leitura consistente, phantom reads prevenidos
    SELECT SUM(balance) FROM accounts WHERE account_id IN (1, 2);
    -- Atualizacoes baseadas nessa leitura
COMMIT;

-- SET TRANSACTION (PostgreSQL)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED DEFERRABLE;
-- A transacao leitura sera consistente, mas nao bloqueira escritas

-- Transacao distribuida (2PC - Two-Phase Commit)
-- SQL Server
BEGIN DISTRIBUTED TRANSACTION;
    -- Operacoes em databases remotos
    EXEC sp_addlinkedserver @server = 'REMOTE_DB';
    UPDATE remote_db.dbo.accounts SET balance = balance - 500 WHERE id = 1;
    UPDATE local_accounts SET balance = balance + 500 WHERE id = 2;
COMMIT;

-- Isolation levels e seus comportamentos
-- READ UNCOMMITTED: le "sujo" (dirty reads permitidos)
-- READ COMMITTED: le apenas dados confirmados (default na maioria)
-- REPEATABLE READ: leitura consistente na transacao
-- SERIALIZABLE: execucao serializavel, maxima隔离
-- SNAPSHOT: leitura baseada em versao do dado

-- PostgreSQL: ver configuracao atual
SHOW transaction_isolation;

-- MySQL: verificar isolation level
SELECT @@transaction_isolation;

-- SQL Server: configurar para uma sessao
SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
```

---

## 1.5 Variáveis e Variáveis Temporárias

### Variaveis Definidas pelo Usuario

Cada dialecto de SQL implementa variaveis de forma diferente. Entender essas diferencas e crucial para escrever codigo portavel e seguro.

#### PostgreSQL: Variaveis de Sessao

PostgreSQL nao tem variaveis de usuario no sentido tradicional. Em vez disso, usa-se `SET` e `current_setting()`:

```sql
-- Definir variavel de sessao
SET app.current_tenant = '42';
SET app.user_role = 'admin';
SET search_path TO production, public;

-- Usar variavel
SELECT current_setting('app.current_tenant')::INTEGER;

-- Em funcoes PL/pgSQL
CREATE OR REPLACE FUNCTION get_tenant_orders()
RETURNS SETOF orders AS $$
DECLARE
    tenant_id INTEGER;
    rec RECORD;
BEGIN
    tenant_id := current_setting('app.current_tenant')::INTEGER;

    FOR rec IN
        SELECT * FROM orders WHERE tenant_id = tenant_id
    LOOP
        RETURN NEXT rec;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Variaveis internas do servidor
SHOW server_version;
SHOW work_mem;
SHOW current_setting('statement_timeout');
```

#### MySQL: Variaveis de Usuario e de Sistema

MySQL suporta variaveis de sessao e de usuario com prefixo @:

```sql
-- Variavel de sessao (prefixo @)
SET @total_revenue = 0;
SET @current_date = CURDATE();

-- Uso em queries
SELECT @total_revenue := SUM(total_amount)
FROM orders
WHERE order_date >= @current_date;

SELECT * FROM orders WHERE total_amount > @total_revenue / 100;

-- Variavel de sistema
SET SESSION max_connections = 200;
SET GLOBAL sql_mode = 'STRICT_TRANS_TABLES';

-- Em stored procedures
DELIMITER //
CREATE PROCEDURE calculate_bonus(IN emp_id INT, OUT bonus DECIMAL(10,2))
BEGIN
    DECLARE emp_salary DECIMAL(10,2);
    DECLARE years_worked INT;

    SELECT salary, TIMESTAMPDIFF(YEAR, hire_date, CURDATE())
    INTO emp_salary, years_worked
    FROM employees
    WHERE employee_id = emp_id;

    SET bonus = emp_salary * years_worked * 0.05;
END //
DELIMITER ;
```

#### SQL Server: Variaveis Locais

SQL Server usa DECLARE para variaveis locais:

```sql
-- Variaveis locais
DECLARE @current_date DATE = GETDATE();
DECLARE @max_salary DECIMAL(10,2);
DECLARE @employee_count INT;
DECLARE @department_name VARCHAR(100);

-- Atribuicao
SELECT @max_salary = MAX(salary)
FROM employees;

SELECT @employee_count = COUNT(*)
FROM employees
WHERE department_id = 5;

-- Variaveis de sistema
SELECT @@VERSION AS server_version;
SELECT @@ROWCOUNT AS rows_affected;
SELECT @@IDENTITY AS last_identity;
SELECT SCOPE_IDENTITY() AS scope_identity;
SELECT IDENT_CURRENT('employees') AS current_identity;

-- Variavel de tabela
DECLARE @processed_orders TABLE (
    order_id BIGINT,
    processed_at DATETIME2
);

INSERT INTO @processed_orders
SELECT order_id, GETUTCDATE()
FROM orders
WHERE status = 'processing';

SELECT * FROM @processed_orders;
```

#### T-SQL: Blocos e Escopo

```sql
-- Blocos BEGIN...END com variaveis
BEGIN
    DECLARE @result TABLE (
        metric_name VARCHAR(50),
        metric_value DECIMAL(10,2)
    );

    INSERT INTO @result
    SELECT 'avg_salary', AVG(salary) FROM employees
    UNION ALL
    SELECT 'max_salary', MAX(salary) FROM employees
    UNION ALL
    SELECT 'min_salary', MIN(salary) FROM employees;

    SELECT * FROM @result;
END;

-- Variaveis de tabela para operacoes em lote
DECLARE @batch_size INT = 1000;
DECLARE @processed INT = 1;

WHILE @processed > 0
BEGIN
    UPDATE TOP (@batch_size) orders
    SET status = 'processed'
    WHERE status = 'pending';

    SET @processed = @@ROWCOUNT;
END;
```

### Variaveis Temporarias (Tabelas Temporarias)

Tabelas temporarias sao tabelas existentes apenas durante a sessao ou transacao:

```sql
-- PostgreSQL: tabelas temporarias
CREATE TEMPORARY TABLE temp_sales_summary (
    region VARCHAR(50),
    total_revenue DECIMAL(12,2),
    order_count INTEGER
) ON COMMIT PRESERVE ROWS;

INSERT INTO temp_sales_summary
SELECT
    region,
    SUM(total_amount),
    COUNT(*)
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY region;

-- SQL Server: tabelas temporarias
CREATE TABLE #temp_results (
    product_id INT,
    score DECIMAL(5,2)
);

INSERT INTO #temp_results
SELECT product_id, AVG(rating) AS score
FROM product_reviews
GROUP BY product_id;

SELECT * FROM #temp_results WHERE score > 4.0;
DROP TABLE #temp_results;

-- SQL Server: tabelas de tabela de variavel (melhor performance)
DECLARE @results TABLE (
    product_id INT,
    score DECIMAL(5,2)
);

INSERT INTO @results
SELECT product_id, AVG(rating)
FROM product_reviews
GROUP BY product_id;
```

---

## 1.6 Funções de Janela (Window Functions)

### Conceito Fundamental

Funcoes de janela permitem executar calculos sobre conjuntos de linhas relacionadas a linha atual, sem colapsar os resultados em uma unica linha (como GROUP BY faz). Cada linha de entrada continua sendo uma linha de saida, mas com valores calculados a partir do "janela" definida.

### Sintaxe Base

A sintaxe geral de uma funcao de janela e:

```
funcao_janela( ) OVER (
    [PARTITION BY col1, col2, ...]
    [ORDER BY col3 [ASC|DESC] [NULLS FIRST|LAST], ...]
    [frame_clause]
)
```

Os tres componentes principais sao:

1. **PARTITION BY**: Divide os dados em grupos (particoes). Similar ao GROUP BY, mas nao colapsa as linhas.
2. **ORDER BY**: Define a ordem das linhas dentro de cada particao.
3. **frame_clause**: Define quais linhas da particao sao incluidas no calculo da janela.

### ROW_NUMBER, RANK e DENSE_RANK

Essas sao as funcoes de numeracao mais utilizadas:

```sql
-- Dados de exemplo: vendas por vendedor
CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    salesperson VARCHAR(50),
    region VARCHAR(20),
    sale_amount DECIMAL(10,2),
    sale_date DATE
);

INSERT INTO sales (salesperson, region, sale_amount, sale_date) VALUES
('Alice', 'North', 5000.00, '2024-01-15'),
('Alice', 'North', 3000.00, '2024-02-10'),
('Alice', 'North', 7000.00, '2024-03-05'),
('Bob', 'North', 4500.00, '2024-01-20'),
('Bob', 'North', 8000.00, '2024-02-15'),
('Bob', 'North', 4500.00, '2024-03-10'),
('Carol', 'South', 6000.00, '2024-01-25'),
('Carol', 'South', 9000.00, '2024-02-20'),
('Carol', 'South', 6000.00, '2024-03-15'),
('Dave', 'South', 3500.00, '2024-01-30'),
('Dave', 'South', 7500.00, '2024-02-25'),
('Eve', 'South', 5500.00, '2024-03-20');
```

```sql
-- ROW_NUMBER: numeracao unica, sem empates
SELECT
    salesperson,
    region,
    sale_amount,
    sale_date,
    ROW_NUMBER() OVER (
        PARTITION BY region
        ORDER BY sale_amount DESC
    ) AS row_num,
    -- Diferencas entre numeracoes:
    RANK() OVER (
        PARTITION BY region
        ORDER BY sale_amount DESC
    ) AS rank_val,
    DENSE_RANK() OVER (
        PARTITION BY region
        ORDER BY sale_amount DESC
    ) AS dense_rank_val
FROM sales;
```

Resultado:

```
 salesperson | region | sale_amount | sale_date  | row_num | rank_val | dense_rank_val
-------------+--------+-------------+------------+---------+----------+---------------
 Bob         | North  |     8000.00 | 2024-02-15 |       1 |        1 |             1
 Alice       | North  |     7000.00 | 2024-03-05 |       2 |        2 |             2
 Alice       | North  |     5000.00 | 2024-01-15 |       3 |        3 |             3
 Bob         | North  |     4500.00 | 2024-01-20 |       4 |        4 |             4
 Bob         | North  |     4500.00 | 2024-03-10 |       5 |        4 |             4
 Alice       | North  |     3000.00 | 2024-02-10 |       6 |        6 |             5
 Carol       | South  |     9000.00 | 2024-02-20 |       1 |        1 |             1
 Dave        | South  |     7500.00 | 2024-02-25 |       2 |        2 |             2
 Carol       | South  |     6000.00 | 2024-01-25 |       3 |        3 |             3
 Carol       | South  |     6000.00 | 2024-03-15 |       4 |        3 |             3
 Eve         | South  |     5500.00 | 2024-03-20 |       5 |        5 |             4
 Dave        | South  |     3500.00 | 2024-01-30 |       6 |        6 |             5
```

A diferenca critica:

- **ROW_NUMBER**: Sempre atribui numeros unicos (1, 2, 3, 4, 5, 6). Mesmo empates recebem numeros diferentes.
- **RANK**: Empates recebem o mesmo numero, e o proximo numero e saltado. Veja como 4500.00 recebe rank 4, e o proximo (3000.00) recebe rank 6.
- **DENSE_RANK**: Empates recebem o mesmo numero, mas o proximo numero nao e saltado. 4500.00 recebe dense_rank 4, e o proximo recebe dense_rank 5.

### LAG e LEAD

LAG e LEAD permitem acessar valores de linhas anteriores ou posteriores na particao:

```sql
-- Calculo de variacao mes a mes
WITH monthly_revenue AS (
    SELECT
        date_trunc('month', sale_date)::DATE AS month,
        SUM(sale_amount) AS revenue
    FROM sales
    GROUP BY date_trunc('month', sale_date)
)
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) AS prev_month_revenue,
    revenue - LAG(revenue, 1) OVER (ORDER BY month) AS absolute_change,
    ROUND(
        (revenue - LAG(revenue, 1) OVER (ORDER BY month))
        / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100,
        2
    ) AS pct_change,
    LEAD(revenue, 1) OVER (ORDER BY month) AS next_month_revenue
FROM monthly_revenue
ORDER BY month;
```

Resultado:

```
    month     | revenue | prev_month_revenue | absolute_change | pct_change | next_month_revenue
--------------+---------+--------------------+-----------------+------------+--------------------
 2024-01-01   | 27000.0 |               NULL |            NULL |       NULL |            38000.0
 2024-02-01   | 38000.0 |            27000.0 |         11000.0 |      40.74 |            33000.0
 2024-03-01   | 33000.0 |            38000.0 |         -5000.0 |     -13.16 |               NULL
```

### NTILE

NTILE divide os dados em N grupos aproximadamente iguais:

```sql
-- Dividir clientes em quartis de gasto
SELECT
    c.customer_id,
    c.customer_name,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    NTILE(4) OVER (
        ORDER BY COALESCE(SUM(o.total_amount), 0) DESC
    ) AS spending_quartile
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name;
```

### Funcoes de Janela Agregadas

```sql
-- Media movel de 3 meses
WITH monthly_data AS (
    SELECT
        date_trunc('month', order_date)::DATE AS month,
        SUM(total_amount) AS revenue
    FROM orders
    GROUP BY date_trunc('month', order_date)
)
SELECT
    month,
    revenue,
    AVG(revenue) OVER (
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS moving_avg_3m,
    SUM(revenue) OVER (
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_revenue,
    COUNT(*) OVER (
        PARTITION BY EXTRACT(MONTH FROM month)
        ORDER BY month
    ) AS months_in_year_so_far
FROM monthly_data;
```

### Frame Specifications

As especificacoes de frame definem o "alcance" da janela:

```sql
-- Demonstracao de frames
SELECT
    sale_date,
    sale_amount,
    -- Frame padrao: RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    SUM(sale_amount) OVER (
        ORDER BY sale_date
    ) AS cumulative_default,
    -- Frame explicito: ROWS
    SUM(sale_amount) OVER (
        ORDER BY sale_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS sum_last_3_rows,
    -- Frame: todos os anteriores
    SUM(sale_amount) OVER (
        ORDER BY sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS sum_all_previous,
    -- Frame: todos
    SUM(sale_amount) OVER (
        ORDER BY sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS sum_all,
    -- Primeiro e ultimo valor da particao
    FIRST_VALUE(sale_amount) OVER (
        ORDER BY sale_date
    ) AS first_sale,
    LAST_VALUE(sale_amount) OVER (
        ORDER BY sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_sale,
    -- Nth valor
    NTH_VALUE(sale_amount, 2) OVER (
        ORDER BY sale_amount DESC
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS second_highest_sale
FROM sales
ORDER BY sale_date;
```

---

## 1.7 Common Table Expressions (CTEs)

### Conceito e Sintaxe

CTEs sao resultados temporarios nomeados que existem apenas durante a execucao de uma unica query. Elas facilitam a leitura de consultas complexas ao quebrar o problema em partes logicas.

```sql
-- CTE basica:分解 uma consulta complexa
WITH active_customers AS (
    SELECT customer_id, customer_name, email
    FROM customers
    WHERE account_status = 'active'
    AND last_login >= CURRENT_DATE - INTERVAL '90' DAY
),
customer_orders AS (
    SELECT
        ac.customer_id,
        ac.customer_name,
        ac.email,
        COUNT(o.order_id) AS total_orders,
        SUM(o.total_amount) AS total_spent,
        AVG(o.total_amount) AS avg_order_value,
        MAX(o.order_date) AS last_order_date
    FROM active_customers ac
    LEFT JOIN orders o ON ac.customer_id = o.customer_id
    GROUP BY ac.customer_id, ac.customer_name, ac.email
),
customer_segments AS (
    SELECT
        *,
        CASE
            WHEN total_spent >= 10000 THEN 'VIP'
            WHEN total_spent >= 5000 THEN 'Premium'
            WHEN total_spent >= 1000 THEN 'Regular'
            ELSE 'New'
        END AS customer_segment
    FROM customer_orders
)
SELECT
    customer_segment,
    COUNT(*) AS segment_count,
    ROUND(AVG(total_spent), 2) AS avg_spending,
    ROUND(AVG(total_orders), 1) AS avg_orders
FROM customer_segments
GROUP BY customer_segment
ORDER BY avg_spending DESC;
```

### CTEs Recursivos: Exemplos Praticos

CTEs recursivos sao uma das ferramentas mais poderosas do SQL moderno. Eles permitem resolver problemas que, de outra forma, exigiriam programacao imperativa em loops.

```sql
-- Exemplo 1: Gerar serie de datas
WITH RECURSIVE date_series AS (
    SELECT '2024-01-01'::DATE AS date
    UNION ALL
    SELECT date + 1
    FROM date_series
    WHERE date < '2024-12-31'::DATE
)
SELECT
    date,
    EXTRACT(DOW FROM date) AS day_of_week,
    EXTRACT(WEEK FROM date) AS week_number
FROM date_series;

-- Exemplo 2: Exploracao de bill of materials (BOM)
WITH RECURSIVE parts_explosion AS (
    -- Anchor: partes finais
    SELECT
        p.part_id,
        p.part_name,
        1 AS quantity,
        0 AS level,
        p.part_name AS path
    FROM parts p
    WHERE p.part_id IN (SELECT DISTINCT parent_part_id FROM bill_of_materials)

    UNION ALL

    -- Recursive: sub-partes
    SELECT
        child.part_id,
        child.part_name,
        bom.quantity * parent.quantity,
        parent.level + 1,
        parent.path || ' > ' || child.part_name
    FROM bill_of_materials bom
    JOIN parts child ON bom.child_part_id = child.part_id
    JOIN parts_explosion parent ON bom.parent_part_id = parent.part_id
    WHERE parent.level < 5
)
SELECT
    part_id,
    part_name,
    SUM(quantity) AS total_quantity_needed,
    level,
    path
FROM parts_explosion
GROUP BY part_id, part_name, level, path
ORDER BY path;

-- Exemplo 3: Achar caminho entre nodos em grafo
WITH RECURSIVE graph_path AS (
    SELECT
        source_node,
        target_node,
        ARRAY[source_node, target_node] AS path,
        1 AS depth
    FROM edges
    WHERE source_node = 'A'

    UNION ALL

    SELECT
        gp.source_node,
        e.target_node,
        gp.path || e.target_node,
        gp.depth + 1
    FROM graph_path gp
    JOIN edges e ON gp.target_node = e.source_node
    WHERE e.target_node != ALL(gp.path)
    AND gp.depth < 10
)
SELECT DISTINCT
    source_node,
    target_node,
    path,
    depth
FROM graph_path
WHERE target_node = 'Z'
ORDER BY depth, path;
```

---

## 1.8 PIVOT e UNPIVOT

### PIVOT em SQL Server

```sql
-- PIVOT: transformar linhas em colunas
SELECT *
FROM (
    SELECT
        product_category,
        EXTRACT(YEAR FROM order_date) AS order_year,
        total_amount
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
) AS source_data
PIVOT (
    SUM(total_amount)
    FOR order_year IN ([2022], [2023], [2024])
) AS pivot_table;
```

Resultado:

```
 product_category |    2022     |    2023     |    2024
------------------+-------------+-------------+------------
 Electronics      |  150000.00  |  200000.00  |  180000.00
 Clothing         |   80000.00  |   95000.00  |  110000.00
 Home & Garden    |   45000.00  |   55000.00  |   62000.00
 Sports           |   30000.00  |   38000.00  |   42000.00
```

### PIVOT em MySQL (workaround com CASE)

```sql
-- MySQL: PIVOT manual com CASE + GROUP BY
SELECT
    product_category,
    SUM(CASE WHEN EXTRACT(YEAR FROM order_date) = 2022 THEN total_amount ELSE 0 END) AS year_2022,
    SUM(CASE WHEN EXTRACT(YEAR FROM order_date) = 2023 THEN total_amount ELSE 0 END) AS year_2023,
    SUM(CASE WHEN EXTRACT(YEAR FROM order_date) = 2024 THEN total_amount ELSE 0 END) AS year_2024
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY product_category;
```

### PIVOT em PostgreSQL (crosstab)

```sql
-- PostgreSQL: funcao crosstab do modulo tablefunc
CREATE EXTENSION IF NOT EXISTS tablefunc;

SELECT *
FROM crosstab(
    'SELECT product_category,
            EXTRACT(YEAR FROM order_date)::INTEGER AS order_year,
            SUM(total_amount)
     FROM orders o
     JOIN products p ON o.product_id = p.product_id
     GROUP BY product_category, order_year
     ORDER BY 1, 2',
    'SELECT DISTINCT EXTRACT(YEAR FROM order_date)::INTEGER
     FROM orders ORDER BY 1'
) AS ct (
    product_category VARCHAR(50),
    year_2022 DECIMAL(12,2),
    year_2023 DECIMAL(12,2),
    year_2024 DECIMAL(12,2)
);
```

### UNPIVOT

```sql
-- SQL Server: UNPIVOT
SELECT *
FROM (
    SELECT product_category, year_2022, year_2023, year_2024
    FROM category_sales_pivot
) AS p
UNPIVOT (
    total_amount FOR order_year IN (year_2022, year_2023, year_2024)
) AS unpvt;

-- PostgreSQL: UNPIVOT com CROSS JOIN LATERAL
SELECT
    p.product_category,
    v.order_year,
    v.total_amount
FROM category_sales_pivot p
CROSS JOIN LATERAL (
    VALUES
        ('2022', p.year_2022),
        ('2023', p.year_2023),
        ('2024', p.year_2024)
) AS v(order_year, total_amount);
```

---

## 1.9 LATERAL Joins

### Conceito

LATERAL JOIN permite que a subquery a direita referencie colunas da tabela ou subquery a esquerda. Isso e fundamental para Top-N por grupo e operacoes que dependem de cada linha da tabela externa.

```sql
-- Top 3 vendas por regiao usando LATERAL
SELECT
    r.region_name,
    top_sales.*
FROM regions r
CROSS JOIN LATERAL (
    SELECT
        s.salesperson,
        s.sale_amount,
        s.sale_date
    FROM sales s
    WHERE s.region = r.region_name
    ORDER BY s.sale_amount DESC
    LIMIT 3
) AS top_sales;
```

### LATERAL com Funcoes

```sql
-- LATERAL com funcao que gera dados
SELECT
    d.day,
    daily_count.count
FROM generate_series(
    '2024-01-01'::DATE,
    '2024-01-31'::DATE,
    '1 day'::INTERVAL
) AS d(day)
CROSS JOIN LATERAL (
    SELECT COUNT(*) AS count
    FROM orders
    WHERE order_date::DATE = d.day
) AS daily_count;
```

### LEFT JOIN LATERAL

```sql
-- LEFT JOIN LATERAL para manter todas as linhas da tabela externa
SELECT
    c.customer_id,
    c.customer_name,
    last_order.*
FROM customers c
LEFT JOIN LATERAL (
    SELECT
        o.order_id,
        o.order_date,
        o.total_amount
    FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.order_date DESC
    LIMIT 1
) AS last_order ON TRUE;
```

---

## 1.10 FILTER Clause

### Sintaxe e Uso

A clausula FILTER permite aplicar uma condicao a uma funcao de agregacao:

```sql
-- FILTER clause: aggregates condicionais
SELECT
    product_category,
    COUNT(*) AS total_reviews,
    COUNT(*) FILTER (WHERE rating >= 4) AS positive_reviews,
    COUNT(*) FILTER (WHERE rating <= 2) AS negative_reviews,
    ROUND(AVG(rating), 2) AS avg_rating,
    ROUND(AVG(rating) FILTER (WHERE rating >= 4), 2) AS avg_positive_rating,
    SUM(total_amount) FILTER (WHERE order_date >= CURRENT_DATE - INTERVAL '30' DAY) AS revenue_last_30d,
    SUM(total_amount) FILTER (WHERE order_date >= CURRENT_DATE - INTERVAL '7' DAY) AS revenue_last_7d
FROM product_reviews pr
JOIN products p ON pr.product_id = p.product_id
JOIN orders o ON pr.order_id = o.order_id
GROUP BY product_category;
```

### Comparacao com CASE WHEN

```sql
-- Usando FILTER (mais limpo e frequentemente mais rapido)
SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
    COUNT(*) FILTER (WHERE status = 'pending') AS pending
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;

-- Equivalente com CASE WHEN (mais verboso)
SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS cancelled,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending
FROM orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;
```

---

## 1.11 GROUPING SETS, ROLLUP e CUBE

### GROUPING SETS

GROUPING SETS permite especificar multiplos grupos de agregacao em uma unica query:

```sql
-- GROUPING SETS: multiplas dimensoes de agregacao
SELECT
    COALESCE(region, '(All Regions)') AS region,
    COALESCE(product_category, '(All Categories)') AS category,
    SUM(total_amount) AS total_revenue,
    COUNT(*) AS order_count
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY GROUPING SETS (
    (region, product_category),  -- regiao + categoria
    (region),                     -- apenas regiao
    (product_category),           -- apenas categoria
    ()                            -- total geral
)
ORDER BY
    GROUPING(region),
    GROUPING(product_category),
    region,
    product_category;
```

### ROLLUP

ROLLUP gera subtotais hierarquicos:

```sql
-- ROLLUP: totais por ano, mes e dia (hierarquicos)
SELECT
    EXTRACT(YEAR FROM order_date) AS order_year,
    EXTRACT(MONTH FROM order_date) AS order_month,
    EXTRACT(DAY FROM order_date) AS order_day,
    SUM(total_amount) AS revenue
FROM orders
GROUP BY ROLLUP (
    EXTRACT(YEAR FROM order_date),
    EXTRACT(MONTH FROM order_date),
    EXTRACT(DAY FROM order_date)
)
ORDER BY
    EXTRACT(YEAR FROM order_date),
    EXTRACT(MONTH FROM order_date),
    EXTRACT(DAY FROM order_date);
```

### CUBE

CUBE gera todas as combinacoes possiveis:

```sql
-- CUBE: todas as combinacoes possiveis
SELECT
    COALESCE(region, 'ALL') AS region,
    COALESCE(product_category, 'ALL') AS category,
    COALESCE(EXTRACT(QUARTER FROM order_date)::TEXT, 'ALL') AS quarter,
    SUM(total_amount) AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY CUBE (
    region,
    product_category,
    EXTRACT(QUARTER FROM order_date)
)
ORDER BY region NULLS LAST, product_category NULLS LAST;
```

### GROUPING() Function

```sql
-- GROUPING() para identificar linhas de subtotal
SELECT
    CASE
        WHEN GROUPING(region) = 1 AND GROUPING(product_category) = 1
            THEN '--- GRAND TOTAL ---'
        WHEN GROUPING(region) = 1
            THEN '--- Category Total: ' || product_category || ' ---'
        WHEN GROUPING(product_category) = 1
            THEN '--- Region Total: ' || region || ' ---'
        ELSE region || ' / ' || product_category
    END AS grouping_level,
    SUM(total_amount) AS revenue,
    GROUPING(region) AS grp_region,
    GROUPING(product_category) AS grp_category
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY GROUPING SETS (
    (region, product_category),
    (region),
    (product_category),
    ()
);
```

---

## 1.12 EXPLAIN e Query Plans

### EXPLAIN ANALYZE no PostgreSQL

```sql
-- EXPLAIN ANALYZE: analise completa de execucao
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    c.customer_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_name
HAVING SUM(o.total_amount) > 5000
ORDER BY total_spent DESC
LIMIT 10;
```

Saida tipica do PostgreSQL:

```
Limit  (cost=15234.56..15234.59 rows=10 width=48) (actual time=45.123..45.125 rows=10 loops=1)
  ->  Sort  (cost=15234.56..15260.34 rows=859 width=48) (actual time=45.121..45.122 rows=10 loops=1)
        Sort Key: (SUM(o.total_amount)) DESC
        Sort Method: top-N heapsort  Memory: 25kB
        ->  HashAggregate  (cost=14980.12..15174.56 rows=859 width=48) (actual time=43.890..44.876 rows=652 loops=1)
              Group Key: c.customer_name
              Filter: (SUM(o.total_amount) > 5000)
              Batches: 1  Memory Usage: 213kB
              ->  Hash Join  (cost=345.00..12456.78 rows=168456 width=44) (actual time=2.345..30.123 rows=168456 loops=1)
                    Hash Cond: (o.customer_id = c.customer_id)
                    ->  Seq Scan on orders o  (cost=0.00..11234.56 rows=168456 width=20) (actual time=0.012..15.678 rows=168456 loops=1)
                          Filter: (order_date >= '2024-01-01'::date)
                          Rows Removed by Filter: 31544
                    ->  Hash  (cost=210.00..210.00 rows=10000 width=36) (actual time=2.100..2.101 rows=10000 loops=1)
                          Buckets: 16384  Batches: 1  Memory Usage: 641kB
                          ->  Seq Scan on customers c  (cost=0.00..210.00 rows=10000 width=36) (actual time=0.005..1.023 rows=10000 loops=1)
Planning Time: 0.234 ms
Execution Time: 45.345 ms
```

### Interpretacao do Plano

**No PostgreSQL**, os operadores principais sao:

- **Seq Scan**: Leitura sequencial de toda a tabela. Indice de ausencia de indice para filtragem.
- **Index Scan**: Uso de indice para localizar registros especificos. Mais rapido que Seq Scan para subconjuntos pequenos.
- **Index Only Scan**: Todos os dados necessarios estao no indice, sem necessidade de acessar a tabela.
- **Hash Join**: Cria uma tabela hash de uma tabela e faz probing com a outra. Eficiente para joins sem indice.
- **Nested Loop**: Para cada linha da tabela externa, busca linhas correspondentes na interna. Eficiente quando a tabela externa e pequena.
- **Merge Join**: Junta duas tabelas ordenadas. Eficiente quando os dados ja estao ordenados.
- **Sort**: Ordenacao dos dados. Pode usar disco se nao couber em memoria.
- **HashAggregate**: Agregacao usando hash. Eficiente para GROUP BY.

### EXPLAIN no MySQL

```sql
-- MySQL: EXPLAIN basico
EXPLAIN SELECT
    c.customer_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-01-01'
GROUP BY c.customer_name
HAVING SUM(o.total_amount) > 5000;

-- MySQL: EXPLAIN FORMAT=JSON para detalhes
EXPLAIN FORMAT=JSON SELECT ...
WHERE o.order_date >= '2024-01-01';

-- MySQL: EXPLAIN ANALYZE (8.0.18+)
EXPLAIN ANALYZE SELECT ...
WHERE o.order_date >= '2024-01-01';
```

### Sinais de Alerta nos Query Plans

**Cost alto em Seq Scan em tabela grande**: Indice ausente ou seletividade baixa.

```sql
-- Verificar indices existentes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'orders';

-- Criar indice para coluna filtrada
CREATE INDEX idx_orders_date ON orders(order_date);
```

**Nested Loop com muitas iteracoes**: A tabela externa e grande demais para esse tipo de join.

**Sort com disco (external merge)**: work_mem insuficiente ou muitos dados para ordenar.

**Rows estimadas muito diferentes das reais**: Estatisticas desatualizadas.

```sql
-- Atualizar estatisticas (PostgreSQL)
ANALYZE orders;

-- Forcar atualizacao completa
VACUUM ANALYZE orders;
```

### Comparacao de Planos entre Dialectos

```sql
-- PostgreSQL: formato textual detalhado
EXPLAIN (ANALYZE, COSTS, VERBOSE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE customer_id = 42;

-- PostgreSQL: formato JSON para parsing programatico
EXPLAIN (ANALYZE, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 42;

-- MySQL: formato basico
EXPLAIN SELECT * FROM orders WHERE customer_id = 42;

-- MySQL: formato JSON com detalhes de custo
EXPLAIN FORMAT=JSON SELECT * FROM orders WHERE customer_id = 42;

-- MySQL: EXPLAIN ANALYZE (8.0.18+)
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 42;

-- SQL Server: execution plan XML
SET STATISTICS XML ON;
SELECT * FROM orders WHERE customer_id = 42;
SET STATISTICS XML OFF;

-- SQL Server: include actual execution plan
SET STATISTICS PROFILE ON;
SELECT * FROM orders WHERE customer_id = 42;
SET STATISTICS PROFILE OFF;
```

### Otimizacao Comum baseada em Planos

```sql
-- Problema: Index Scan lento por falta de indice composto
-- Query original
SELECT * FROM orders
WHERE customer_id = 42 AND status = 'pending'
ORDER BY order_date DESC;

-- Solucao: indice composto cobrindo a query
CREATE INDEX idx_orders_customer_status_date
ON orders(customer_id, status, order_date DESC);

-- Problema: Sort caro em GROUP BY
-- Query com many groups
SELECT customer_id, COUNT(*), SUM(total_amount)
FROM orders
GROUP BY customer_id;

-- Solucao: indice no GROUP BY + colunas selecionadas
CREATE INDEX idx_orders_cust_agg
ON orders(customer_id) INCLUDE (total_amount);

-- Problema: Join com tabela grande sem indice
-- Antes do plano
-- Hash Join  (cost=50000.00..75000.00 rows=1000000)
--   -> Seq Scan on orders  (cost=0.00..50000.00)
--   -> Hash  (cost=200.00..200.00 rows=10000)
--       -> Seq Scan on customers

-- Solucao: criar indice na foreign key
CREATE INDEX idx_orders_customer_fk ON orders(customer_id);
-- Agora o planner pode usar Index Scan no lado do orders
```

### pg_stat_statements: Monitoramento Continuo

```sql
-- Instalar extensao (requer configuracao no postgresql.conf)
-- shared_preload_libraries = 'pg_stat_statements'
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Resetar estatisticas periodicamente
SELECT pg_stat_statements_reset();

-- Queries mais lentas (media)
SELECT
    queryid,
    LEFT(query, 80) AS query_preview,
    calls,
    ROUND(total_exec_time::numeric / calls, 2) AS avg_ms,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_ms,
    rows / NULLIF(calls, 0) AS avg_rows
FROM pg_stat_statements
WHERE calls > 10
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Queries que mais consomem I/O
SELECT
    LEFT(query, 80) AS query_preview,
    calls,
    shared_blks_read,
    shared_blks_hit,
    ROUND(100.0 * shared_blks_hit /
        NULLIF(shared_blks_hit + shared_blks_read, 0), 1) AS cache_hit_pct
FROM pg_stat_statements
ORDER BY shared_blks_read DESC
LIMIT 10;

-- Queries que mais bloqueiam
SELECT
    LEFT(query, 80) AS query_preview,
    calls,
    blk_read_time,
    blk_write_time
FROM pg_stat_statements
WHERE blk_read_time > 0 OR blk_write_time > 0
ORDER BY blk_read_time DESC
LIMIT 10;
```

---

## 1.13 Dicas de Produtividade

### Gerar Series de Datas

```sql
-- PostgreSQL: generate_series para criar datas
SELECT
    day::DATE,
    EXTRACT(DOW FROM day) AS day_of_week,
    EXTRACT(WEEK FROM day) AS week_number
FROM generate_series(
    '2024-01-01'::DATE,
    '2024-12-31'::DATE,
    '1 day'::INTERVAL
) AS day;
```

### Sequencias de Numeros

```sql
-- Gerar numeros de 1 a 100
SELECT generate_series(1, 100) AS num;

-- Gerar com intervalo
SELECT generate_series(0, 100, 5) AS num;
```

### Agregacao de Arrays

```sql
-- PostgreSQL: agregar valores em array
SELECT
    customer_id,
    ARRAY_AGG(DISTINCT product_category ORDER BY product_category) AS categories_purchased,
    ARRAY_AGG(DISTINCT DATE_TRUNC('month', order_date) ORDER BY 1) AS purchase_months
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY customer_id;
```

### UNNEST para Expandir Arrays

```sql
-- Expandir array em linhas
SELECT
    c.customer_id,
    c.customer_name,
    unnest(ARRAY['email', 'phone', 'sms']) AS preferred_channel
FROM customers c
WHERE c.receive_notifications;
```

### EXCEPT e INTERSECT

```sql
-- Encontrar clientes que nao fizeram pedidos
SELECT customer_id, customer_name
FROM customers
EXCEPT
SELECT c.customer_id, c.customer_name
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id;

-- Encontrar categorias presentes em ambos os periodos
SELECT product_category
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_date >= '2024-01-01' AND o.order_date < '2024-07-01'
INTERSECT
SELECT product_category
FROM orders o
JOIN products p ON o.product_id = p.product_id
WHERE o.order_date >= '2024-07-01' AND o.order_date < '2025-01-01';
```

### Dicas de Seguranca ao Escrever SQL

```sql
-- SEMPRE use parameterized queries
-- ERRADO (vulneravel a SQL injection):
-- query = "SELECT * FROM users WHERE name = '" + user_input + "'"

-- CORRETO (parametrizado):
PREPARE safe_query AS
SELECT * FROM users WHERE name = $1;
EXECUTE safe_query('valor_do_usuario');

-- Use ALWAYS funcoes de validacao no banco
-- Criar funcao de validacao de email
CREATE OR REPLACE FUNCTION is_valid_email(email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Usar em constraints
ALTER TABLE customers
    ADD CONSTRAINT chk_email CHECK (is_valid_email(email));

-- Nunca armazene senhas em texto plano
-- Use bcrypt via extensao pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Armazenar hash
INSERT INTO users (username, password_hash)
VALUES ('admin', crypt('minha_senha', gen_salt('bf', 12)));

-- Verificar senha
SELECT EXISTS (
    SELECT 1 FROM users
    WHERE username = 'admin'
    AND password_hash = crypt('minha_senha', password_hash)
) AS is_valid;
```

### Gerenciamento de Sessoes

```sql
-- PostgreSQL: informacoes da sessao atual
SELECT
    pg_backend_pid() AS process_id,
    current_user AS username,
    session_user AS session_user,
    current_database() AS database,
    inet_client_addr() AS client_ip,
    pg_postmaster_start_time() AS server_start,
    NOW() - pg_postmaster_start_time() AS uptime;

-- Listar todas as sessoes ativas
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    client_port,
    backend_start,
    state,
    query_start,
    state_change,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE backend_type = 'client backend'
ORDER BY state_change DESC;

-- Matar uma sessao longa (use com cuidado!)
SELECT pg_terminate_backend(12345);

-- MySQL: sessoes ativas
SHOW PROCESSLIST;

-- SQL Server: sessoes ativas
SELECT
    s.session_id,
    s.login_name,
    s.host_name,
    s.program_name,
    c.client_net_address,
    s.status,
    r.command,
    r.start_time,
    LEFT(t.text, 100) AS query_preview
FROM sys.dm_exec_sessions s
JOIN sys.dm_exec_connections c ON s.session_id = c.session_id
LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE s.status != 'sleeping'
ORDER BY r.start_time ASC;
```

### Trabalhando com CTEs Avancadas

```sql
-- CTE mutavel (PostgreSQL 12+)
WITH RECURSIVE tree AS (
    -- Anchor: niveis da hierarquia
    SELECT
        employee_id,
        manager_id,
        employee_name,
        1 AS depth,
        employee_name AS path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive: subordinados
    SELECT
        e.employee_id,
        e.manager_id,
        e.employee_name,
        t.depth + 1,
        t.path || ' -> ' || e.employee_name
    FROM employees e
    JOIN tree t ON e.manager_id = t.employee_id
    WHERE t.depth < 10  -- protecao contra loop infinito
)
SELECT
    employee_id,
    employee_name,
    depth,
    path
FROM tree
ORDER BY path;

-- CTE para pivot dinamico
WITH source_data AS (
    SELECT
        product_category,
        EXTRACT(MONTH FROM order_date) AS month,
        SUM(total_amount) AS revenue
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    GROUP BY product_category, EXTRACT(MONTH FROM order_date)
)
SELECT
    product_category,
    SUM(CASE WHEN month = 1 THEN revenue ELSE 0 END) AS jan,
    SUM(CASE WHEN month = 2 THEN revenue ELSE 0 END) AS feb,
    SUM(CASE WHEN month = 3 THEN revenue ELSE 0 END) AS mar,
    SUM(CASE WHEN month = 4 THEN revenue ELSE 0 END) AS apr,
    SUM(CASE WHEN month = 5 THEN revenue ELSE 0 END) AS may,
    SUM(CASE WHEN month = 6 THEN revenue ELSE 0 END) AS jun,
    SUM(CASE WHEN month = 7 THEN revenue ELSE 0 END) AS jul,
    SUM(CASE WHEN month = 8 THEN revenue ELSE 0 END) AS aug,
    SUM(CASE WHEN month = 9 THEN revenue ELSE 0 END) AS sep,
    SUM(CASE WHEN month = 10 THEN revenue ELSE 0 END) AS oct,
    SUM(CASE WHEN month = 11 THEN revenue ELSE 0 END) AS nov,
    SUM(CASE WHEN month = 12 THEN revenue ELSE 0 END) AS dec
FROM source_data
GROUP BY product_category;
```

### Trabalhando com Timestamps de Forma Segura

```sql
-- SEMPRE use TIMESTAMPTZ para armazenar
-- TIMESTAMP WITHOUT TIME ZONE e propenso a erros de timezone

-- Conversoes seguras
SELECT
    NOW() AS current_utc,
    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS utc_time,
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Sao_Paulo' AS sp_time,
    CURRENT_TIMESTAMP AT TIME ZONE 'America/New_York' AS ny_time;

-- Diferenca entre timestamps
SELECT
    order_id,
    order_date,
    shipped_date,
    shipped_date - order_date AS processing_time,
    EXTRACT(EPOCH FROM (shipped_date - order_date)) / 3600 AS hours_to_ship
FROM orders
WHERE shipped_date IS NOT NULL;
```

### Geração de Dados de Teste

```sql
-- PostgreSQL: gerar dados de teste realistas
CREATE OR REPLACE FUNCTION generate_test_orders(n INTEGER)
RETURNS VOID AS $$
BEGIN
    INSERT INTO orders (customer_id, order_number, status, subtotal, tax_amount, order_date)
    SELECT
        (random() * 999 + 1)::INTEGER,
        'ORD-' || LPAD(i::TEXT, 6, '0'),
        (ARRAY['pending','processing','shipped','delivered','cancelled'])[1 + (random() * 4)::INTEGER],
        ROUND((random() * 5000 + 10)::NUMERIC, 2),
        ROUND((random() * 500 + 1)::NUMERIC, 2),
        CURRENT_TIMESTAMP - (random() * 365)::INTEGER * INTERVAL '1 day'
    FROM generate_series(1, n) AS i;
END;
$$ LANGUAGE plpgsql;

-- Gerar 10.000 pedidos de teste
SELECT generate_test_orders(10000);
```

### Expressoes de Tabela Derivadas (Subquery no FROM)

```sql
-- Subquery no FROM (derived table)
SELECT
    d.department_name,
    dept_stats.avg_salary,
    dept_stats.headcount,
    ROUND(dept_stats.total_payroll / NULLIF(headcount, 0), 2) AS cost_per_employee
FROM departments d
JOIN (
    SELECT
        department_id,
        AVG(salary) AS avg_salary,
        COUNT(*) AS headcount,
        SUM(salary) AS total_payroll
    FROM employees
    GROUP BY department_id
) dept_stats ON d.department_id = dept_stats.department_id
WHERE dept_stats.headcount > 5
ORDER BY dept_stats.avg_salary DESC;

-- LATERAL vs derived table
-- Derived table: executada uma vez
-- LATERAL: executada para cada linha da tabela externa
SELECT
    c.customer_id,
    top_orders.*
FROM customers c,
LATERAL (
    SELECT order_id, total_amount, order_date
    FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY order_date DESC
    LIMIT 3
) top_orders;
```

### Verificacao de Integridade de Dados

```sql
-- Verificar chaves estrangeiras quebradas
SELECT
    o.order_id,
    o.customer_id,
    'Missing customer' AS issue
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- Verificar valores duplicados indesejados
SELECT
    email,
    COUNT(*) AS duplicate_count
FROM customers
GROUP BY email
HAVING COUNT(*) > 1;

-- Verificar colunas com muitos NULLs
SELECT
    column_name,
    ROUND(
        100.0 * SUM(CASE WHEN column_value IS NULL THEN 1 ELSE 0 END)
        / COUNT(*), 2
    ) AS null_percentage
FROM information_schema.columns
JOIN (
    SELECT customer_id, cpf AS column_value FROM customers
) data ON TRUE
GROUP BY column_name;

-- Verificar distribuicao de dados (histograma simples)
SELECT
    NTILE(10) AS decile,
    MIN(total_amount) AS min_amount,
    MAX(total_amount) AS max_amount,
    COUNT(*) AS row_count
FROM orders
GROUP BY NTILE(10)
ORDER BY decile;
```

### Resumo das Diferencas de Sintaxe

Para rapida referencia, esta tabela consolida as principais diferencas de sintaxe entre os dialectos discutidos neste capitulo:

| Feature | PostgreSQL | MySQL | SQLite | SQL Server | Oracle |
|---------|-----------|-------|--------|------------|--------|
| Top N | LIMIT n | LIMIT n | LIMIT n | TOP n | FETCH FIRST n ROWS ONLY |
| Concat | \|\| ou CONCAT() | CONCAT() | \|\| | + | \|\| |
| Auto-incremento | GENERATED AS IDENTITY | AUTO_INCREMENT | ROWID/INTEGER PK | IDENTITY(1,1) | GENERATED AS IDENTITY |
| UPSERT | ON CONFLICT DO UPDATE | ON DUPLICATE KEY UPDATE | INSERT OR REPLACE | MERGE | MERGE |
| Booleano | BOOLEAN | TINYINT(1) | INTEGER (0/1) | BIT | NUMBER(1) |
| Texto longo | TEXT | LONGTEXT | TEXT | VARCHAR(MAX) / NVARCHAR(MAX) | CLOB / NCLOB |
| Data atual | CURRENT_DATE | CURDATE() | date('now') | GETDATE() | SYSDATE |
| Timestamp | NOW() / CURRENT_TIMESTAMP | NOW() / CURRENT_TIMESTAMP | datetime('now') | GETUTCDATE() | SYSTIMESTAMP |
| Intervalo | INTERVAL '1' DAY | DATE_ADD/DATE_SUB | N/A | DATEADD | ADD_MONTHS |
| Group concat | STRING_AGG() | GROUP_CONCAT() | GROUP_CONCAT() | STRING_AGG() | LISTAGG() |
| Comentario | COMMENT ON | COMMENT ON TABLE/COLUMN | N/A | sp_addextendedproperty | COMMENT ON TABLE/COLUMN |

Essas diferencas reforcam a importancia de conhecer o dialecto que voce esta usando. Uma consulta perfeitamente funcional em PostgreSQL pode gerar erros incomprensiveis em MySQL ou SQL Server. O conhecimento das diferencas de sintaxe e uma habilidade essencial para qualquer desenvolvedor que trabalhe com bancos de dados de forma profissional.

No proximo capitulo, aprofundaremos nos tipos de dados e esquemas, explorando como a escolha adequada de tipos e a modelagem de esquemas afetam diretamente a seguranca e performance dos sistemas.

---

## 1.14 SQL e Seguranca: Primeiros Principios

### O Principio do Menor Privilegio

O principio do menor privilegio e o alicate da seguranca em bancos de dados. Cada usuario, funcao, e aplicacao deve ter apenas os privilegios minimos necessarios para realizar sua tarefa. Esse principio se aplica em multiplos niveis:

```sql
-- Nivel 1: Usuario dedicado por aplicacao
CREATE USER app_web WITH PASSWORD 'senha_forte_aqui';
CREATE USER app_api WITH PASSWORD 'outra_senha_forte';
CREATE USER app_reports WITH PASSWORD 'senha_para_relatorios';

-- Cada usuario recebe apenas o que precisa
GRANT CONNECT ON DATABASE myapp TO app_web;
GRANT USAGE ON SCHEMA public TO app_web;
GRANT SELECT, INSERT, UPDATE ON customers TO app_web;
GRANT SELECT, INSERT, UPDATE, DELETE ON orders TO app_web;
GRANT SELECT, INSERT ON order_items TO app_web;
-- NENHUM acesso a tabelas de audit ou configuracao

GRANT CONNECT ON DATABASE myapp TO app_reports;
GRANT USAGE ON SCHEMA public TO app_reports;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_reports;
-- APENAS leitura, sem escrita

-- Nivel 2: Permissao por coluna (quando necessario)
GRANT SELECT (customer_id, customer_name, email) ON customers TO app_web;
-- app_web NAO pode acessar cpf, password_hash, ou dados sensiveis

-- Nivel 3: Funcoes de seguranca
CREATE OR REPLACE FUNCTION get_safe_customer_data(p_customer_id BIGINT)
RETURNS TABLE (
    customer_id BIGINT,
    customer_name VARCHAR(100),
    city VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.customer_id, c.customer_name, a.city
    FROM customers c
    LEFT JOIN addresses a ON c.customer_id = a.customer_id
    WHERE c.customer_id = p_customer_id
    AND c.account_status = 'active';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- A funcao roda com privilegios do owner, nao do chamador
GRANT EXECUTE ON FUNCTION get_safe_customer_data TO app_web;
```

### Parametrizacao: A Regra de Ouro

SQL injection continua sendo a vulnerabilidade mais perigosa e mais evitavel em sistemas de banco de dados. A solucao e sempre, sem excecao, usar queries parametrizadas:

```sql
-- PERIGO: Concatenacao de strings (NUNCA faca isso)
-- query = "SELECT * FROM users WHERE username = '" + username + "'"
-- Se username = "'; DROP TABLE users; --"
-- A query se torna: SELECT * FROM users WHERE username = ''; DROP TABLE users; --'
-- Resultado: deleta toda a tabela de usuarios

-- SEGURO: Queries parametrizadas
-- PostgreSQL
PREPARE safe_login AS
SELECT user_id, username, password_hash
FROM users
WHERE username = $1
AND account_status = 'active';
EXECUTE safe_login('valor_do_usuario');

-- MySQL
-- use Prepared Statements no driver da linguagem de programacao
PREPARE safe_login FROM
'SELECT user_id, username, password_hash
FROM users WHERE username = ? AND account_status = ?';
SET @user = 'valor_do_usuario';
SET @status = 'active';
EXECUTE safe_login USING @user, @status;

-- SQL Server
-- use sp_executesql
DECLARE @sql NVARCHAR(500) = N'
    SELECT user_id, username, password_hash
    FROM users
    WHERE username = @username
    AND account_status = @status';
DECLARE @username NVARCHAR(100) = N'valor_do_usuario';
DECLARE @status NVARCHAR(20) = N'active';
EXEC sp_executesql @sql, N'@username NVARCHAR(100), @status NVARCHAR(20)',
    @username = @username, @status = @status;
```

### Protecao contra Time-Based Attacks

Time-based SQL injection e uma tecnica onde o atacante infere informacoes baseado no tempo de resposta:

```sql
-- Exemplo de ataque time-based (conceitual)
-- O atacante envia: ' OR (SELECT CASE WHEN (SELECT password FROM users
-- WHERE username='admin' AND SUBSTRING(password,1,1)='a')
-- IS NOT NULL THEN pg_sleep(5) ELSE pg_sleep(0) END) = '1' --

-- Defesa: limitar tempo de execucao
SET statement_timeout = '5s';  -- PostgreSQL
SET SESSION max_execution_time = 5000;  -- MySQL

-- Defesa: usar LIMIT em queries que retornam dados
SELECT customer_id, customer_name
FROM customers
WHERE email = $1
LIMIT 1;
-- Mesmo que a query seja manipulada, LIMIT 1 restringe o resultado
```

### Views de Seguranca

Views podem ser usadas para abstrair a estrutura real das tabelas e controlar o que cada usuario ve:

```sql
-- View de seguranca para dados de clientes
CREATE VIEW v_customer_safe AS
SELECT
    customer_id,
    customer_name,
    -- CPF mascarado: mostra apenas os 3 ultimos digitos
    CONCAT('***.***.', RIGHT(cpf, 4)) AS cpf_masked,
    -- Email mascarado
    CONCAT(
        LEFT(email, 2),
        REPEAT('*', POSITION('@' IN email) - 3),
        SUBSTRING(email FROM POSITION('@' IN email))
    ) AS email_masked,
    city,
    state
FROM customers
WHERE account_status = 'active';

-- A view NAO expoe: password_hash, cpf completo,
-- telefone, endereco completo, data de nascimento

GRANT SELECT ON v_customer_safe TO app_web;

-- View de auditoria apenas para admins
CREATE VIEW v_audit_admin AS
SELECT
    audit_id,
    table_name,
    operation,
    old_values,
    new_values,
    performed_by,
    performed_at
FROM audit_log
WHERE performed_at >= CURRENT_DATE - INTERVAL '90' DAY;

GRANT SELECT ON v_audit_admin TO role_admin;
```

### Encriptacao de Dados Sensiveis

```sql
-- PostgreSQL: encriptacao com pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encriptar dados antes de armazenar (Application-Level Encryption)
INSERT INTO customers (customer_name, encrypted_cpf, encrypted_phone)
VALUES (
    'Joao Silva',
    pgp_sym_encrypt('123.456.789-00', 'chave_secreta_sistema'),
    pgp_sym_encrypt('(11) 98765-4321', 'chave_secreta_sistema')
);

-- Desencriptar para uso
SELECT
    customer_name,
    pgp_sym_decrypt(encrypted_cpf::bytea, 'chave_secreta_sistema') AS cpf,
    pgp_sym_decrypt(encrypted_phone::bytea, 'chave_secreta_sistema') AS phone
FROM customers
WHERE customer_id = 1;

-- PostgreSQL 16+: encriptacao transparente (Transparent Data Encryption)
-- Configurado via pg_basebackup com --encryption-algorithm
```

### Auditoria de Acesso

```sql
-- Tabela de auditoria completa
CREATE TABLE security_audit_log (
    audit_id        BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type      VARCHAR(20) NOT NULL CHECK (event_type IN (
                        'LOGIN', 'LOGOUT', 'QUERY', 'DDL', 'DCL',
                        'PERMISSION_DENIED', 'CONSTRAINT_VIOLATION'
                    )),
    username        VARCHAR(100) NOT NULL DEFAULT current_user,
    client_ip       INET,
    database_name   VARCHAR(100) NOT NULL DEFAULT current_database(),
    query_text      TEXT,
    query_duration  INTERVAL,
    rows_affected   INTEGER,
    error_message   TEXT,
    session_id      VARCHAR(100)
);

-- Index para buscas rapidas
CREATE INDEX idx_audit_timestamp ON security_audit_log(event_timestamp DESC);
CREATE INDEX idx_audit_username ON security_audit_log(username, event_timestamp DESC);
CREATE INDEX idx_audit_type ON security_audit_log(event_type, event_timestamp DESC);

-- Trigger automatica de auditoria
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO security_audit_log (event_type, query_text)
    VALUES (
        TG_OP,
        current_query()
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em tabelas sensiveis
CREATE TRIGGER audit_customers
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH STATEMENT
    EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH STATEMENT
    EXECUTE FUNCTION audit_trigger_func();

-- Relatorio de acessos recentes
SELECT
    username,
    event_type,
    COUNT(*) AS event_count,
    MIN(event_timestamp) AS first_event,
    MAX(event_timestamp) AS last_event
FROM security_audit_log
WHERE event_timestamp >= CURRENT_TIMESTAMP - INTERVAL '24' HOUR
GROUP BY username, event_type
ORDER BY event_count DESC;
```

### Soft Delete e Recuperacao de Dados

Soft delete e um padrao que preserva registros deletados, permitindo recuperacao e auditoria:

```sql
-- Implementacao de soft delete
ALTER TABLE customers
    ADD COLUMN deleted_at TIMESTAMP NULL,
    ADD COLUMN deleted_by VARCHAR(100) NULL;

-- View que esconde registros deletados
CREATE VIEW v_customers_active AS
SELECT * FROM customers WHERE deleted_at IS NULL;

-- Funcao de soft delete
CREATE OR REPLACE FUNCTION soft_delete_customer(
    p_customer_id BIGINT,
    p_reason TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE customers
    SET
        deleted_at = CURRENT_TIMESTAMP,
        deleted_by = current_user
    WHERE customer_id = p_customer_id
    AND deleted_at IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer % not found or already deleted', p_customer_id;
    END IF;

    INSERT INTO deletion_log (table_name, record_id, reason, deleted_by, deleted_at)
    VALUES ('customers', p_customer_id, p_reason, current_user, CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- Funcao de recuperacao
CREATE OR REPLACE FUNCTION restore_customer(p_customer_id BIGINT)
RETURNS VOID AS $$
BEGIN
    UPDATE customers
    SET deleted_at = NULL, deleted_by = NULL
    WHERE customer_id = p_customer_id
    AND deleted_at IS NOT NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Customer % not found or not deleted', p_customer_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

### Monitoramento e Alertas

```sql
-- Queries lentas (PostgreSQL: pg_stat_statements)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 queries mais lentas
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS avg_time_ms,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_ms,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Top 10 queries que mais consomem tempo total
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(100.0 * total_exec_time / sum(total_exec_time) OVER(), 2) AS pct_total
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Conexoes ativas
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    NOW() - query_start AS query_duration,
    LEFT(query, 100) AS query_preview
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start ASC;

-- Verificar tabelas sem audit trail
SELECT
    schemaname,
    tablename,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT LIKE 'pg_%'
AND tablename NOT LIKE '%audit%'
ORDER BY tablename;
```

### Checklist de Seguranca para SQL

| Item | Descricao | Criticidade |
|------|-----------|-------------|
| Parametrizacao | Todas as queries usam prepared statements | Critica |
| Menor privilegio | Cada usuario tem permissao minima | Critica |
| Senhas fortes | Todas as contas usam senhas complexas | Critica |
| Encriptacao em transito | SSL/TLS habilitado para todas as conexoes | Alta |
| Encriptacao em repouso | Dados sensiveis encriptografados no disco | Alta |
| Auditoria | Logs de acesso configurados e monitorados | Alta |
| Backup encriptografado | Backups sao encriptografados e testados | Alta |
| Soft delete | Registros sensiveis usam soft delete | Media |
| Views de seguranca | Exposicao controlada de dados | Media |
| Limites de taxa | Rate limiting em queries expostas | Media |
| Timeout de queries | statement_timeout configurado | Media |
| Atualizacao de versao | SGBDR atualizado com patches de seguranca | Alta |

### CVEs Relacionadas a SQL

Ao longo da historia, varias vulnerabilidades criticas afetaram sistemas de banco de dados:

- **CVE-2012-2122 (MySQL)**: Falha de autenticacao onde bytes incorretos na senha eram aceitos. A taxa de erro de comparacao de 1 em 256 permitia bypass de autenticacao com brute force.

- **CVE-2017-3506 (Oracle WebLogic)**: XML External Entity (XXE) que permitia leitura de arquivos e executacao remota via componentes conectados a bancos Oracle.

- **CVE-2019-2725 (Oracle WebLogic)**: Deserialization insegura que permitia executacao remota em sistemas com acesso a Oracle Database.

- **CVE-2020-2555 (Oracle Coherence)**: Deserialization via JDBC que afetava sistemas usando Oracle Coherence como cache.

- **CVE-2021-44228 (Log4Shell)**: Embora nao seja SQL, sistemas que usavam Log4j para logging de queries SQL foram afetados, potencialmente expondo dados de audit em bancos de dados.

- **CVE-2023-34362 (MOVEit)**: SQL injection que afetou mais de 2.500 organizacoes. O vetor de ataque exploitava uma vulnerabilidade em uma stored procedure nao parametrizada.

Essas CVEs demonstram que a seguranca de bancos de dados vai alem da parametrizacao de queries. Envolve atualizacoes de software, configuracao segura, auditoria, e monitoramento continuo.

---

## Resumo

Este capitulo estabeleceu as bases para o estudo avancado de SQL. Cobrimos a historia da linguagem desde o modelo relacional de Codd, passando pelos padroes ANSI/ISO, ate as implementacoes modernas. Exploramos os dialectos principais — PostgreSQL, MySQL, SQLite, SQL Server, e Oracle — com suas diferencas sintaticas e de funcionalidade.

Dominamos o DDL, DML, DCL e TCL com exemplos praticos. Avancamos para funcionalidades modernas como funcoes de janela, CTEs, PIVOT/UNPIVOT, e LATERAL joins. Aprendemos a interpretar query plans com EXPLAIN para otimizar consultas.

Cada topic foi apresentado com seguranca em mente. As diferencas entre dialectos podem criar brechas quando consultas sao migradas entre bancos. A escolha correta de tipos de dados, o uso de validacao em constraints, e a parametrizacao de queries sao pilares fundamentais da seguranca de dados.

Estabelecemos os principios de seguranca em banco de dados: menor privilegio, parametrizacao obrigatoria, encriptacao, auditoria, e monitoramento continuo. Esses principios serao reforçados ao longo de todo o livro.

No proximo capitulo, aprofundaremos nos tipos de dados e esquemas, explorando como a escolha adequada de tipos e a modelagem de esquemas afetam diretamente a seguranca e performance dos sistemas.

---

*[Proximo capitulo: 02 — Tipos de Dados e Esquemas](02-tipos-dados-esquemas.md)*
