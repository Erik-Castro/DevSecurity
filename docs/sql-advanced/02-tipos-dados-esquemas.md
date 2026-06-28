---
layout: default
title: "02-tipos-dados-esquemas"
---

# Capítulo 2: Tipos de Dados e Esquemas

## Sumário

- [2.1 Tipos Numéricos](#21-tipos-numéricos)
- [2.2 Tipos de Texto](#22-tipos-de-texto)
- [2.3 Data e Hora](#23-data-e-hora)
- [2.4 BLOBs e Armazenamento Binário](#24-blobs-e-armazenamento-binário)
- [2.5 JSON e JSONB](#25-json-e-jsonb)
- [2.6 XML](#26-xml)
- [2.7 Tipos Geométricos](#27-tipos-geométricos)
- [2.8 Arrays](#28-arrays)
- [2.9 Enums e Domain Types](#29-enums-e-domain-types)
- [2.10 CHECK Constraints e Validação](#210-check-constraints-e-validação)
- [2.11 Materialized Views](#211-materialized-views)
- [2.12 Schema Design Patterns](#212-schema-design-patterns)
- [2.13 Naming Conventions](#213-naming-conventions)
- [2.14 Documentação de Schema](#214-documentação-de-schema)
- [2.15 Exemplo: Schema Completo de E-commerce](#215-exemplo-schema-completo-de-e-commerce)

---

## 2.1 Tipos Numéricos

### Tipos Inteiros

Os tipos inteiros sao a base de praticamente todo banco de dados relacional. A escolha do tipo correto impacta diretamente o uso de disco, performance de indexacao, e a capacidade de armazenamento.

```sql
-- PostgreSQL: tipos inteiros e seu alcance
CREATE TABLE integer_demo (
    col_smallint    SMALLINT,       -- -32768 a 32767 (2 bytes)
    col_integer     INTEGER,        -- -2^31 a 2^31-1 (4 bytes)
    col_bigint      BIGINT,         -- -2^63 a 2^63-1 (8 bytes)
    col_serial      SERIAL,         -- alias para INTEGER com sequence
    col_bigserial   BIGSERIAL       -- alias para BIGINT com sequence
);

-- MySQL: tipos inteiros
CREATE TABLE mysql_integer_demo (
    col_tinyint     TINYINT,        -- -128 a 127 (1 byte)
    col_tinyint_u   TINYINT UNSIGNED, -- 0 a 255 (1 byte)
    col_smallint    SMALLINT,       -- -32768 a 32767 (2 bytes)
    col_mediumint   MEDIUMINT,      -- -8388608 a 8388607 (3 bytes)
    col_integer     INT,            -- -2^31 a 2^31-1 (4 bytes)
    col_bigint      BIGINT          -- -2^63 a 2^63-1 (8 bytes)
);

-- SQL Server: tipos inteiros
CREATE TABLE sqlserver_integer_demo (
    col_tinyint     TINYINT,        -- 0 a 255 (1 byte)
    col_smallint    SMALLINT,       -- -32768 a 32767 (2 bytes)
    col_int         INT,            -- -2^31 a 2^31-1 (4 bytes)
    col_bigint      BIGINT          -- -2^63 a 2^63-1 (8 bytes)
);

-- Oracle: tipos numericos
CREATE TABLE oracle_integer_demo (
    col_number_5    NUMBER(5),      -- -99999 a 99999
    col_number_10   NUMBER(10),     -- -9999999999 a 9999999999
    col_integer     INTEGER         -- alias para NUMBER(38)
);
```

**Tabela de comparacao de capacidade:**

| Tipo | Bytes | PostgreSQL | MySQL | SQL Server | Oracle |
|------|-------|-----------|-------|------------|--------|
| 1 byte | 1 | SMALLINT | TINYINT | TINYINT | NUMBER(1,0) |
| 2 bytes | 2 | SMALLINT | SMALLINT | SMALLINT | NUMBER(2,0) |
| 3 bytes | 3 | N/A | MEDIUMINT | N/A | N/A |
| 4 bytes | 4 | INTEGER | INT | INT | NUMBER(10,0) |
| 8 bytes | 8 | BIGINT | BIGINT | BIGINT | NUMBER(19,0) |
| Serial | 4 | SERIAL | AUTO_INCREMENT | IDENTITY(1,1) | GENERATED AS IDENTITY |

**SECURITY: Overflow de inteiros**

```sql
-- CUIDADO: operacoes que podem causar overflow
-- PostgreSQL e SQLite: overflow silencioso (wrap-around para negativos)
-- MySQL com strict mode: erro

-- Exemplo de overflow
-- Se col_smallint = 32767 (maximo SMALLINT)
-- UPDATE t SET col = col + 1
-- PostgreSQL: resultado = -32768 (overflow silencioso!)
-- MySQL strict mode: ERROR 1264: Out of range value

-- Defesa: usar CONSTRAINT para validar limites
ALTER TABLE products
    ADD CONSTRAINT chk_price_positive CHECK (price > 0),
    ADD CONSTRAINT chk_quantity_valid CHECK (quantity >= 0 AND quantity <= 1000000);
```

### Tipos Decimais e de Ponto Flutuante

```sql
-- PostgreSQL: DECIMAL vs FLOAT vs NUMERIC
CREATE TABLE decimal_demo (
    -- DECIMAL/NUMERIC: exato, ideal para dinheiro
    price_exact     DECIMAL(10,2),     -- 10 digitos, 2 decimais
    -- FLOAT: aproximacao, rapido mas impreciso
    price_float     FLOAT(24),         -- single precision (~7 digitos)
    price_double    DOUBLE PRECISION,   -- double precision (~15 digitos)
    -- MONEY: tipo especifico (PostgreSQL)
    price_money     MONEY
);

-- Demonstracao de imprecisao
SELECT
    0.1 + 0.2 AS float_result,
    (0.1 + 0.2)::DECIMAL(10,2) AS decimal_result,
    0.1::DOUBLE PRECISION + 0.2::DOUBLE PRECISION AS double_result;

-- Resultado esperado:
-- float_result  | decimal_result | double_result
-- ---------------+----------------+--------------
-- 0.30000000000000004 | 0.30 | 0.30000000000000004

-- Dinheiro: SEMPRE use DECIMAL/NUMERIC
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL,   -- ex: 0.1250 para 12.5%
    tax_amount DECIMAL(12,4) GENERATED ALWAYS AS (
        ROUND(subtotal * tax_rate, 4)
    ) STORED,
    total DECIMAL(12,2) GENERATED ALWAYS AS (
        ROUND(subtotal + ROUND(subtotal * tax_rate, 4), 2)
    ) STORED
);

-- MySQL: DECIMAL e o unico tipo exato
CREATE TABLE mysql_orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    subtotal DECIMAL(12,2) NOT NULL,
    -- MySQL: NAO use FLOAT para dinheiro
    -- price FLOAT -- ERRO de design!
    price DECIMAL(10,2) NOT NULL
);

-- SQL Server: MONEY vs DECIMAL
CREATE TABLE sqlserver_orders (
    order_id INT IDENTITY PRIMARY KEY,
    -- MONEY: preciso para exibicao, mas pode ter rounding
    subtotal_money MONEY,
    -- DECIMAL: melhor para calculos
    subtotal_decimal DECIMAL(12,2)
);
```

**SECURITY: Imprecisao de ponto flutuante em autenticacao**

```sql
-- NUNCA compare floats com =
SELECT * FROM auth_tokens WHERE token_value = 0.1;
-- Pode falhar se o valor foi armazenado como FLOAT

-- SEMPRE use DECIMAL para tokens ou valores sensiveis
SELECT * FROM auth_tokens WHERE token_value = 0.1::DECIMAL(20,10);
```

### SERIAL, IDENTITY e Sequencias

```sql
-- PostgreSQL: SERIAL (conveniencia)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL
);
-- SERIAL cria: sequence + default value
-- equivalente a:
-- CREATE SEQUENCE users_user_id_seq;
-- CREATE TABLE users (
--     user_id INTEGER DEFAULT nextval('users_user_id_seq') PRIMARY KEY,
--     username VARCHAR(50) NOT NULL
-- );

-- PostgreSQL: GENERATED AS IDENTITY (SQL padrao, recomendado)
CREATE TABLE users_v2 (
    user_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL
);

-- MySQL: AUTO_INCREMENT
CREATE TABLE mysql_users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL
);

-- SQL Server: IDENTITY
CREATE TABLE sqlserver_users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) NOT NULL
);

-- Oracle: sequencias
CREATE SEQUENCE user_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE oracle_users (
    user_id NUMBER DEFAULT user_seq.NEXTVAL PRIMARY KEY,
    username VARCHAR2(50) NOT NULL
);
```

---

## 2.2 Tipos de Texto

### CHAR, VARCHAR e TEXT

```sql
-- Tabela comparativa dos tipos de texto
CREATE TABLE text_types_demo (
    -- CHAR: tamanho fixo, preenche com espacos
    fixed_char     CHAR(10),         -- sempre 10 bytes
    -- VARCHAR: tamanho variavel
    var_char       VARCHAR(100),     -- 1 byte overhead + conteudo
    -- TEXT: sem limite declarado (PostgreSQL)
    long_text      TEXT
);

-- Comportamento de CHAR com padding
INSERT INTO text_types_demo (fixed_char) VALUES ('hello');
SELECT LENGTH(fixed_char), OCTET_LENGTH(fixed_char) FROM text_types_demo;
-- LENGTH: 5 (remove espacos da direita)
-- OCTET_LENGTH: 10 (tamanho real em bytes)

-- MySQL: limites de VARCHAR
-- VARCHAR(n): n e o NUMERO DE CARACTERES (nao bytes) em InnoDB com utf8mb4
-- Maximo: 65535 bytes (incluindo overhead), efetivamente ~16383 chars utf8mb4

-- PostgreSQL: TEXT nao tem overhead de tamanho
-- VARCHAR(n) e TEXT sao funcionalmente equivalentes em PostgreSQL
-- VARCHAR(n) adiciona verificacao de tamanho
-- TEXT e ligeiramente mais rapido para operacoes de concatenacao
```

**SECURITY: Ataques de truncamento e encoding**

```sql
-- SECURITY: Truncamento silencioso em MySQL
-- MySQL com PAD CHAR_TO_FULL_LENGTH desabilitado:
INSERT INTO users (username) VALUES ('admin      ');
-- Pode criar usuario duplicado se unique index nao considera espacos

-- Defesa: TRIM antes de inserir
INSERT INTO users (username) VALUES (TRIM('admin      '));

-- SECURITY: Ataques de encoding (MySQL)
-- Se o banco usa latin1 mas recebe utf8mb4:
-- Caracteres multibyte podem ser truncados incorretamente
-- criando usernames duplicados ou bypass de validacao

-- Defesa: SEMPRE usar utf8mb4 em MySQL
ALTER DATABASE myapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- SECURITY: Null byte injection
-- Se a aplicacao nao valida null bytes:
-- username = 'admin\0password'
-- Em C/PHP com strcmp(), pode retornar 0 (equal)

-- Defesa: validar contra null bytes
ALTER TABLE users
    ADD CONSTRAINT chk_no_null_bytes CHECK (username NOT LIKE '%\0%');

-- PostgreSQL: protecao natural contra null bytes em TEXT
-- mas NAO em funcoes C customizadas
```

### Colation e Comparacao

```sql
-- PostgreSQL: colation afeta comparacao e ordenacao
CREATE TABLE collation_demo (
    name VARCHAR(100)
);

-- PostgreSQL: como colation afeta busca
SELECT * FROM collation_demo WHERE name = 'cafe';
-- Com collation 'C': so encontra exatamente 'cafe'
-- Com collation 'pt_BR': encontra 'cafe', 'café' (case-insensitive variante)

-- Criar tabela com colation especifica
CREATE TABLE customers (
    customer_name VARCHAR(100) COLLATE "pt_BR" NOT NULL
);

-- MySQL: colation impacta performance de index
-- utf8mb4_unicode_ci: busca case-insensitive (padrao recomendado)
-- utf8mb4_bin: busca case-sensitive (mais rapida)
-- utf8mb4_general_ci: mais rapida mas menos precisa
-- utf8mb4_0900_ai_ci: Unicode 9.0, case-insensitive, accent-insensitive

-- SQL Server: colation afeta sorting
CREATE DATABASE myapp COLLATE Latin1_General_CI_AS;
-- CI = Case Insensitive
-- AS = Accent Sensitive
```

---

## 2.3 Data e Hora

### Tipos de Data

```sql
-- PostgreSQL: todos os tipos de data/hora
CREATE TABLE datetime_demo (
    col_date            DATE,                          -- somente data
    col_time            TIME,                          -- somente hora
    col_time_tz         TIME WITH TIME ZONE,           -- hora com timezone
    col_timestamp       TIMESTAMP,                     -- data+hora, sem timezone
    col_timestamp_tz    TIMESTAMP WITH TIME ZONE,      -- data+hora COM timezone
    col_interval        INTERVAL                       -- duracao
);

-- A diferenca critica entre TIMESTAMP e TIMESTAMPTZ:
-- TIMESTAMP: armazena EXATAMENTE o valor fornecido, sem conversao
-- TIMESTAMPTZ: converte para UTC antes de armazenar, reconverte na leitura

-- Demonstacao
SET timezone = 'America/Sao_Paulo';

INSERT INTO datetime_demo (col_timestamp, col_timestamp_tz)
VALUES ('2024-06-15 14:30:00', '2024-06-15 14:30:00+00');

-- Mudar timezone da sessao
SET timezone = 'Asia/Tokyo';

SELECT col_timestamp, col_timestamp_tz FROM datetime_demo;
-- col_timestamp: 2024-06-15 14:30:00 (INALTERADO!)
-- col_timestamp_tz: 2024-06-15 23:30:00+09 (convertido de UTC para Tokyo)
```

**SECURITY: Bugs de timezone**

```sql
-- CENARIO CLASSICO DE BUG: fuso horario incorreto
-- Usuario envia: "2024-06-15 14:30:00" (horario de SP)
-- Aplicacao armazena como TIMESTAMP sem conversao
-- Servidor esta em UTC
-- Resultado: 3 horas de diferenca silenciosa!

-- Defesa 1: SEMPRE usar TIMESTAMPTZ
-- Defesa 2: Converter para UTC no aplicativo antes de enviar
-- Defesa 3: Usar NOW() ou CURRENT_TIMESTAMP em vez de timestamps manuais

-- MySQL: datetime vs timestamp
-- DATETIME: '1000-01-01' a '9999-12-31', 8 bytes, NAO converte timezone
-- TIMESTAMP: '1970-01-01' a '2038-01-19', 4 bytes, converte de/para UTC

-- MySQL: o bug classico de TIMESTAMP 2038
-- Em 19 de janeiro de 2038, TIMESTAMP de 32 bits atinge seu maximo
-- Solucao: usar DATETIME em vez de TIMESTAMP

-- SQL Server: sem suporte nativo a timezone
-- datetime2: '0001-01-01' a '9999-12-31' (recomendado)
-- datetimeoffset: datetime2 + offset de timezone
-- smalldatetime: '1900-01-01' a '2079-06-06', 4 bytes, 1 minuto de precisao
-- datetime: '1753-01-01' a '9999-12-31', 3.33ms de precisao (DEPRECATED)

-- Oracle: DATE inclui data E hora (diferente de outros SGBDRs)
-- TIMESTAMP com fracao de segundo
-- TIMESTAMP WITH TIME ZONE
-- TIMESTAMP WITH LOCAL TIME ZONE (converte para o fuso do servidor)
```

### Operacoes com Datas

```sql
-- PostgreSQL: operacoes de data
SELECT
    CURRENT_DATE AS today,
    CURRENT_DATE + INTERVAL '7 days' AS next_week,
    CURRENT_DATE - INTERVAL '1 month' AS last_month,
    DATE_TRUNC('month', CURRENT_DATE) AS first_of_month,
    DATE_TRUNC('quarter', CURRENT_DATE) AS first_of_quarter,
    AGE(CURRENT_DATE, DATE '1990-01-15') AS age,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, DATE '1990-01-15')) AS age_years,
    EXTRACT(DOW FROM CURRENT_DATE) AS day_of_week,  -- 0=Domingo
    EXTRACT(EPOCH FROM (
        TIMESTAMP '2024-12-31 23:59:59' -
        TIMESTAMP '2024-01-01 00:00:00'
    )) / 86400 AS days_in_year;

-- MySQL: operacoes de data
SELECT
    CURDATE() AS today,
    DATE_ADD(CURDATE(), INTERVAL 7 DAY) AS next_week,
    DATE_SUB(CURDATE(), INTERVAL 1 MONTH) AS last_month,
    LAST_DAY(CURDATE()) AS last_of_month,
    YEARWEEK(CURDATE()) AS year_week,
    DATEDIFF(CURDATE(), '1990-01-15') / 365 AS approx_age;

-- SQL Server: operacoes de data
SELECT
    GETDATE() AS today,
    DATEADD(DAY, 7, GETDATE()) AS next_week,
    DATEADD(MONTH, -1, GETDATE()) AS last_month,
    EOMONTH(GETDATE()) AS end_of_month,
    DATEDIFF(DAY, '1990-01-15', GETDATE()) AS days_alive,
    YEAR(GETDATE()) AS current_year;
```

### INTERVAL e Calculos de Tempo

```sql
-- PostgreSQL: INTERVALS poderosos
SELECT
    INTERVAL '1 year 2 months 3 days 4 hours 5 minutes 6 seconds' AS complex_interval,
    INTERVAL 'P1Y2M3DT4H5M6S' AS iso_interval,  -- formato ISO 8601
    EXTRACT(EPOCH FROM INTERVAL '1 day') AS seconds_in_day,
    EXTRACT(EPOCH FROM INTERVAL '1 hour') AS seconds_in_hour;

-- Gerar serie temporal com intervalos
SELECT generate_series(
    '2024-01-01'::TIMESTAMP,
    '2024-12-31 23:59:59'::TIMESTAMP,
    '1 month'::INTERVAL
) AS month_start;

-- Calcular media movel de 7 dias
WITH daily_metrics AS (
    SELECT
        DATE_TRUNC('day', order_date)::DATE AS day,
        SUM(total_amount) AS daily_revenue
    FROM orders
    GROUP BY DATE_TRUNC('day', order_date)
)
SELECT
    day,
    daily_revenue,
    AVG(daily_revenue) OVER (
        ORDER BY day
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg_7d
FROM daily_metrics
ORDER BY day;
```

---

## 2.4 BLOBs e Armazenamento Binário

### Tipos Binarios

```sql
-- PostgreSQL: BYTEA (Binary Array)
CREATE TABLE file_storage (
    file_id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    file_data BYTEA,
    file_size INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados binarios
INSERT INTO file_storage (filename, mime_type, file_data, file_size)
VALUES (
    'documento.pdf',
    'application/pdf',
    pg_read_file('/path/to/document.pdf'),  -- ou encode(data, 'base64')
    pg_stat_file('/path/to/document.pdf').size
);

-- MySQL: BLOB variants
CREATE TABLE mysql_file_storage (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255),
    file_data LONGBLOB,           -- ate 4GB
    file_size INT,
    -- Alternativas:
    -- TINYBLOB: 255 bytes
    -- BLOB: 65KB
    -- MEDIUMBLOB: 16MB
    -- LONGBLOB: 4GB
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- SQL Server: VARBINARY
CREATE TABLE sqlserver_file_storage (
    file_id INT IDENTITY PRIMARY KEY,
    filename NVARCHAR(255),
    file_data VARBINARY(MAX),     -- ate 2GB
    file_size BIGINT,
    uploaded_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Oracle: BLOB
CREATE TABLE oracle_file_storage (
    file_id NUMBER GENERATED AS IDENTITY PRIMARY KEY,
    filename VARCHAR2(255),
    file_data BLOB,
    file_size NUMBER,
    uploaded_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

**SECURITY: Riscos de armazenar binarios no banco**

```sql
-- PROBLEMA 1: Exfiltracao via BLOB
-- Um atacante com acesso de leitura pode baixar todos os binarios
-- Defesa: Row-Level Security nos BLOBs
ALTER TABLE file_storage ENABLE ROW LEVEL SECURITY;

CREATE POLICY file_access ON file_storage
    FOR SELECT
    USING (
        uploaded_by = current_setting('app.current_user_id')::INTEGER
        OR current_setting('app.current_user_role') IN ('admin', 'auditor')
    );

-- PROBLEMA 2: BLOBs inflam o tamanho do banco
-- Backups ficam enormes, replication fica lenta
-- Defesa: armazenar binarios em object storage (S3, MinIO)
-- e manter apenas a referencia no banco
ALTER TABLE file_storage
    DROP COLUMN file_data,
    ADD COLUMN storage_path VARCHAR(500),
    ADD COLUMN storage_bucket VARCHAR(100);

-- PROBLEMA 3: SQL injection via binarios
-- BLOBs podem conter payloads maliciosos que bypassam WAF
-- Defesa: validar mime_type e tamanho antes de armazenar
ALTER TABLE file_storage
    ADD CONSTRAINT chk_mime_type CHECK (
        mime_type IN ('application/pdf', 'image/jpeg', 'image/png',
                      'text/plain', 'text/csv')
    ),
    ADD CONSTRAINT chk_file_size CHECK (file_size <= 10485760);  -- 10MB max
```

---

## 2.5 JSON e JSONB

### JSON no PostgreSQL

```sql
-- PostgreSQL: JSON vs JSONB
-- JSON: armazena texto JSON exato, preserva formatacao
-- JSONB: armazena em formato binario, mais rapido para consultas, suporta indexacao

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::JSONB
);

-- Inserir dados JSON
INSERT INTO products (product_name, attributes) VALUES
('Smartphone XYZ', '{
    "brand": "TechCorp",
    "specs": {
        "screen": "6.5 inch",
        "ram": "8GB",
        "storage": "128GB",
        "battery": "4500mAh"
    },
    "colors": ["black", "white", "blue"],
    "price": 999.99,
    "in_stock": true
}'),
('Notebook ABC', '{
    "brand": "CompuTech",
    "specs": {
        "screen": "14 inch",
        "ram": "16GB",
        "storage": "512GB SSD",
        "processor": "Intel i7"
    },
    "colors": ["silver", "space_gray"],
    "price": 1499.99,
    "in_stock": true
}'),
('Fone de Ouvido DEF', '{
    "brand": "AudioMax",
    "specs": {
        "type": "over-ear",
        "wireless": true,
        "noise_cancelling": true
    },
    "colors": ["black"],
    "price": 299.99,
    "in_stock": false
}');

-- Operadores JSONB
SELECT
    product_name,
    attributes->'brand' AS brand,                   -- retorna JSON
    attributes->>'brand' AS brand_text,              -- retorna TEXT
    attributes->'specs'->>'ram' AS ram,              -- aninhamento
    attributes->'colors' AS all_colors,              -- array completo
    jsonb_array_length(attributes->'colors') AS color_count,
    attributes->'price' AS price
FROM products;

-- Resultado:
-- product_name     | brand       | brand_text | ram  | all_colors        | color_count | price
-- -----------------+-------------+------------+------+-------------------+-------------+-------
-- Smartphone XYZ   | "TechCorp"  | TechCorp   | 8GB  | ["black","w..."]  |           3 | 999.99
-- Notebook ABC     | "CompuTech" | CompuTech  | 16GB | ["silver","s..."] |           2 | 1499.99
-- Fone de Ouvido   | "AudioMax"  | AudioMax   | NULL | ["black"]         |           1 | 299.99
```

### Operadores de Containment e Busca

```sql
-- Busca por containment: @> (jsonb contem jsonb)
SELECT * FROM products
WHERE attributes @> '{"brand": "TechCorp"}';

SELECT * FROM products
WHERE attributes @> '{"specs": {"ram": "8GB"}}';

-- Busca por existencia: ? (chave existe), ?| (qualquer chave), ?& (todas chaves)
SELECT * FROM products WHERE attributes ? 'wireless';
SELECT * FROM products WHERE attributes ?| ARRAY['wireless', 'noise_cancelling'];
SELECT * FROM products WHERE attributes ?& ARRAY['type', 'wireless'];

-- Busca por caminho: @>, #>, #>>
SELECT * FROM products
WHERE attributes #>> '{specs,processor}' = 'Intel i7';

-- Filtro em array JSONB
SELECT * FROM products
WHERE attributes->'colors' @> '["blue"]';

-- Indexacao GIN para buscas eficientes
CREATE INDEX idx_products_attrs ON products USING GIN (attributes);
CREATE INDEX idx_products_attrs_path ON products USING GIN (attributes jsonb_path_ops);

-- jsonb_path_ops: mais compacto, mais rapido para containment
-- GIN padrao: mais flexivel, suporta todos os operadores
```

### JSON em MySQL

```sql
-- MySQL 5.7+: tipo JSON nativo
CREATE TABLE mysql_products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(200),
    attributes JSON NOT NULL
);

-- Funcoes JSON do MySQL
SELECT
    product_name,
    JSON_EXTRACT(attributes, '$.brand') AS brand,
    JSON_EXTRACT(attributes, '$.specs.ram') AS ram,
    JSON_LENGTH(JSON_EXTRACT(attributes, '$.colors')) AS color_count,
    attributes->>'$.price' AS price_text,       -- MySQL 8.0.21+
    attributes->'$.specs'->>'$.ram' AS ram_v2
FROM mysql_products;

-- Criar indice multikey para arrays
ALTER TABLE mysql_products
    ADD INDEX idx_colors ((CAST(attributes->'$.colors' AS UNSIGNED ARRAY)));

-- Buscar produtos com cor especifica
SELECT * FROM mysql_products
WHERE JSON_CONTAINS(attributes->'$.colors', '"black"');
```

### JSON no SQL Server

```sql
-- SQL Server: OPENJSON e funcoes JSON
DECLARE @json_data NVARCHAR(MAX) = '{
    "product": "Smartphone",
    "specs": {
        "screen": "6.5 inch",
        "ram": "8GB"
    },
    "colors": ["black", "white"]
}';

-- Parsear JSON
SELECT * FROM OPENJSON(@json_data);
-- key          | value                    | type
-- -------------+--------------------------+-----
-- product      | Smartphone               | 1
-- specs        | {"screen":"6.5 inch",...}| 4
-- colors       | ["black","white"]        | 4

-- Extrair valores especificos
SELECT
    JSON_VALUE(@json_data, '$.product') AS product_name,
    JSON_VALUE(@json_data, '$.specs.ram') AS ram,
    JSON_QUERY(@json_data, '$.specs') AS all_specs,
    JSON_QUERY(@json_data, '$.colors') AS all_colors;

-- OPENJSON com schema definido
SELECT *
FROM OPENJSON(@json_data, '$.specs')
WITH (
    screen NVARCHAR(50) '$.screen',
    ram NVARCHAR(20) '$.ram'
);

-- Buscar em colunas JSON (SQL Server 2016+)
SELECT *
FROM products
WHERE JSON_VALUE(attributes, '$.brand') = 'TechCorp';

-- Criar indice para consultas JSON
CREATE INDEX idx_products_brand
ON products (JSON_VALUE(attributes, '$.brand'));
```

### JSON no SQLite

```sql
-- SQLite: funcoes JSON (3.9.0+)
CREATE TABLE sqlite_products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    attributes TEXT CHECK (json_valid(attributes))
);

-- Inserir com validacao
INSERT INTO sqlite_products (product_name, attributes)
VALUES (
    'Smartphone',
    '{"brand":"TechCorp","specs":{"ram":"8GB"},"colors":["black","white"]}'
);

-- Extrair dados
SELECT
    product_name,
    json_extract(attributes, '$.brand') AS brand,
    json_extract(attributes, '$.specs.ram') AS ram,
    json_array_length(json_extract(attributes, '$.colors')) AS color_count
FROM sqlite_products;

-- Buscar em JSON
SELECT * FROM sqlite_products
WHERE json_extract(attributes, '$.brand') = 'TechCorp';

-- Expandir array JSON em linhas
SELECT
    sp.product_name,
    json_each.value AS color
FROM sqlite_products sp,
json_each(json_extract(sp.attributes, '$.colors'));
```

**SECURITY: NoSQL Injection via JSON**

```sql
-- CENARIO: ataque via campos JSON em autenticacao
-- Tabela de usuarios com dados em JSONB
CREATE TABLE users_json (
    user_id SERIAL PRIMARY KEY,
    credentials JSONB NOT NULL
);

INSERT INTO users_json (credentials) VALUES ('{
    "username": "admin",
    "password_hash": "$2b$12$hash_aqui",
    "role": "admin"
}');

-- PERIGO: se a aplicacao constrói a query JSON dinamicamente
-- Sem parametrizacao:
-- user_input = '{"username": "admin", "password": {"$ne": ""}}'
-- A query busca: WHERE credentials @> user_input
-- Resultado: retorna o usuario admin sem verificar senha!

-- DEFESA: validar estrutura do JSON antes de usar
CREATE OR REPLACE FUNCTION validate_credentials_json(data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Verificar que campos obrigatorios existem e sao strings
    RETURN (
        data ? 'username'
        AND data ? 'password'
        AND jsonb_typeof(data->'username') = 'string'
        AND jsonb_typeof(data->'password') = 'string'
        AND jsonb_array_length(jsonb_object_keys(data)) = 2
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- VALIDO: buscar por username exato
SELECT * FROM users_json
WHERE credentials @> '{"username": "admin"}';

-- SEGURO: extrair e comparar diretamente
SELECT * FROM users_json
WHERE credentials->>'username' = $1
AND credentials->>'password_hash' = crypt($2, credentials->>'password_hash');
```

---

## 2.6 XML

### XML no SQL Server

```sql
-- SQL Server: tipo XML nativo
CREATE TABLE product_catalog (
    catalog_id INT IDENTITY PRIMARY KEY,
    catalog_data XML NOT NULL
);

-- Inserir XML
INSERT INTO product_catalog (catalog_data) VALUES ('
<catalog>
    <product id="1">
        <name>Smartphone</name>
        <price currency="USD">999.99</price>
        <specs>
            <ram>8GB</ram>
            <storage>128GB</storage>
        </specs>
    </product>
    <product id="2">
        <name>Tablet</name>
        <price currency="USD">499.99</price>
        <specs>
            <ram>4GB</ram>
            <storage>64GB</storage>
        </specs>
    </product>
</catalog>
');

-- Consultar com XQuery
SELECT
    catalog_data.value('(/catalog/product/@id)[1]', 'INT') AS product_id,
    catalog_data.value('(/catalog/product/name)[1]', 'VARCHAR(100)') AS product_name,
    catalog_data.value('(/catalog/product/price)[1]', 'DECIMAL(10,2)') AS price
FROM product_catalog;

-- Extrair todos os produtos
SELECT
    p.product.value('@id', 'INT') AS product_id,
    p.product.value('name[1]', 'VARCHAR(100)') AS product_name,
    p.product.value('price[1]', 'DECIMAL(10,2)') AS price,
    p.product.value('specs/ram[1]', 'VARCHAR(10)') AS ram
FROM product_catalog
CROSS APPLY catalog_data.nodes('/catalog/product') AS p(product);
```

### XML no PostgreSQL

```sql
-- PostgreSQL: tipo XML
CREATE TABLE documents (
    doc_id SERIAL PRIMARY KEY,
    doc_content XML NOT NULL
);

-- Inserir XML
INSERT INTO documents (doc_content) VALUES ('
<order>
    <order_id>1001</order_id>
    <customer>Joao Silva</customer>
    <items>
        <item>
            <product>Widget A</product>
            <qty>5</qty>
            <price>29.99</price>
        </item>
        <item>
            <product>Widget B</product>
            <qty>3</qty>
            <price>39.99</price>
        </item>
    </items>
</order>
');

-- Extrair dados com xpath()
SELECT
    (xpath('//order_id/text()', doc_content))[1]::TEXT AS order_id,
    (xpath('//customer/text()', doc_content))[1]::TEXT AS customer,
    (xpath('sum(//item/qty * //item/price)', doc_content))[1]::NUMERIC AS total;

-- Expandir itens
SELECT
    d.doc_id,
    (item_xpath).*
FROM documents d,
LATERAL unnest(xpath('//item', doc_content)) AS item_xpath;
```

**SECURITY: XML External Entity (XXE)**

```sql
-- CENARIO: XXE via XML no banco de dados
-- Um atacante envia XML com entidade externa:
-- <?xml version="1.0"?>
-- <!DOCTYPE foo [
--   <!ENTITY xxe SYSTEM "file:///etc/passwd">
-- ]>
-- <data>&xxe;</data>

-- Se a funcao de parsing nao desabilita entidades externas:
-- O conteudo do arquivo /etc/passwd pode ser injetado no XML

-- DEFESA: validar e sanitizar XML antes de armazenar

-- PostgreSQL: usar funcoes de parsing seguras
-- NAO usar xmlparse() com entidades externas

-- SQL Server: configurar XML parser para bloquear XXE
-- Usar OPENXML com flag de parse seguro

-- Melhor defesa: NAO armazenar XML de fontes nao confiaveis
-- Se necessario, converter para JSONB (mais seguro, sem entidades)
```

---

## 2.7 Tipos Geometricos

### PostgreSQL: Geometric Types

```sql
-- PostgreSQL: tipos geometricos nativos
CREATE TABLE spatial_data (
    id SERIAL PRIMARY KEY,
    -- Ponto
    location POINT,
    -- Linha
    boundary LINE,
    -- Segmento de linha
    path_segment LSEG,
    -- Retangulo
    bounding_box BOX,
    -- Poligono
    polygon_area POLYGON,
    -- Circulo
    coverage CIRCLE
);

-- Inserir dados geometricos
INSERT INTO spatial_data (location, bounding_box, coverage) VALUES
('(42.3601, -71.0589)',  -- Boston (lat, lon)
 '((0,0),(100,100))',      -- retangulo
 '((50,50), 25)');          -- circulo centrada em (50,50) com raio 25

-- Consultar com operadores geometricos
SELECT
    id,
    location <-> POINT '(40.7128, -74.0060)' AS distance_to_nyc,
    bounding_box @> POINT '(50,50)' AS contains_point,
    coverage @> POINT '(50,50)' AS circle_contains
FROM spatial_data;

-- Introducao ao PostGIS (extensao geografica)
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE postgis_locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    geom GEOMETRY(Point, 4326)  -- SRID 4326 = WGS84 (GPS)
);

-- Inserir coordenadas GPS
INSERT INTO postgis_locations (name, geom) VALUES
('Sao Paulo', ST_SetSRID(ST_MakePoint(-46.6333, -23.5505), 4326)),
('Rio de Janeiro', ST_SetSRID(ST_MakePoint(-43.1729, -22.9068), 4326)),
('Belo Horizonte', ST_SetSRID(ST_MakePoint(-43.9386, -19.9167), 4326));

-- Calcular distancias em km
SELECT
    a.name AS city_a,
    b.name AS city_b,
    ROUND(ST_Distance(
        a.geom::geography,
        b.geom::geography
    )::NUMERIC, 2) AS distance_km
FROM postgis_locations a
CROSS JOIN postgis_locations b
WHERE a.id < b.id
ORDER BY distance_km;
```

---

## 2.8 Arrays

### Arrays no PostgreSQL

```sql
-- PostgreSQL: arrays nativos
CREATE TABLE student_courses (
    student_id SERIAL PRIMARY KEY,
    student_name VARCHAR(100),
    enrolled_courses TEXT[],           -- array de strings
    scores INTEGER[],                  -- array de inteiros
    schedule JSONB                     -- alternativa mais flexivel
);

-- Inserir com arrays
INSERT INTO student_courses (student_name, enrolled_courses, scores) VALUES
('Alice', ARRAY['SQL', 'Python', 'Statistics'], ARRAY[95, 88, 92]),
('Bob', ARRAY['SQL', 'Java', 'Web Dev'], ARRAY[78, 85, 90]),
('Carol', ARRAY['Python', 'Data Science'], ARRAY[90, 95]);

-- Operadores de array
SELECT
    student_name,
    enrolled_courses,
    array_length(enrolled_courses, 1) AS course_count,
    'SQL' = ANY(enrolled_courses) AS takes_sql,
    scores[1] AS first_score,
    scores[2:] AS rest_scores,
    array_append(enrolled_courses, 'ML') AS with_ml,
    array_cat(enrolled_courses, ARRAY['AI', 'Deep Learning']) AS expanded
FROM student_courses;

-- Buscar por valor no array
SELECT * FROM student_courses
WHERE 'SQL' = ANY(enrolled_courses);

SELECT * FROM student_courses
WHERE enrolled_courses @> ARRAY['Python', 'Statistics'];

-- Unnest: expandir array em linhas
SELECT
    sc.student_name,
    unnest(sc.enrolled_courses) AS course,
    unnest(sc.scores) AS score
FROM student_courses sc;

-- Agregar de volta em array
SELECT
    course,
    ARRAY_AGG(student_name ORDER BY student_name) AS students,
    ARRAY_AGG(score ORDER BY score DESC) AS scores
FROM (
    SELECT
        student_name,
        unnest(enrolled_courses) AS course,
        unnest(scores) AS score
    FROM student_courses
) expanded
GROUP BY course;
```

**SECURITY: Array Injection**

```sql
-- SECURITY: operacoes com arrays podem ser manipuladas
-- Se a aplicacao injeta valores no array sem sanitizacao

-- Exemplo de ataque conceitual:
-- Entrada do usuario: "{admin,true}" ou similar
-- Se usado em query: WHERE roles && ARRAY['{user_input}']

-- Defesa: validar valores antes de adicionar ao array
CREATE OR REPLACE FUNCTION safe_array_append(
    arr TEXT[],
    val TEXT
) RETURNS TEXT[] AS $$
BEGIN
    -- Validar que o valor nao contem caracteres perigosos
    IF val ~ '[{}();\-]' OR LENGTH(val) > 50 THEN
        RAISE EXCEPTION 'Invalid array element: %', val;
    END IF;
    RETURN array_append(arr, val);
END;
$$ LANGUAGE plpgsql;
```

---

## 2.9 Enums e Domain Types

### ENUM

```sql
-- PostgreSQL: CREATE TYPE AS ENUM
CREATE TYPE order_status AS ENUM (
    'pending',
    'processing',
    'shipped',
    'delivered',
    'cancelled',
    'returned'
);

CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'critical');

-- Usar em tabela
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    status order_status NOT NULL DEFAULT 'pending',
    priority priority_level NOT NULL DEFAULT 'medium'
);

-- Inserir valores
INSERT INTO tasks (title, status, priority) VALUES
('Setup database', 'completed', 'high'),  -- ERRO: 'completed' nao e valor valido!
('Write tests', 'processing', 'medium');

-- Consultar por enum
SELECT * FROM tasks WHERE status = 'processing';
SELECT * FROM tasks WHERE priority >= 'high';  -- Enums suportam comparacao ordinal

-- Listar valores do enum
SELECT enum_range(NULL::order_status);
-- {pending,processing,shipped,delivered,cancelled,returned}

-- Adicionar valor ao enum (nao remover sem CUIDADO)
ALTER TYPE order_status ADD VALUE 'refunded' AFTER 'returned';
```

### MySQL: ENUM

```sql
-- MySQL: ENUM inline
CREATE TABLE mysql_tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200),
    status ENUM('pending', 'processing', 'shipped', 'delivered',
                'cancelled', 'returned') NOT NULL DEFAULT 'pending',
    priority ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium'
);

-- MySQL ENUM: armazenado como inteiro interno (1 byte)
-- Indexado como inteiro, muito eficiente
-- Porem: adicionar/remover valores requer ALTER TABLE

-- MySQL: adicionar valor a ENUM existente
ALTER TABLE mysql_tasks
    MODIFY COLUMN status ENUM('pending', 'processing', 'shipped', 'delivered',
                              'cancelled', 'returned', 'refunded') NOT NULL;

-- MySQL: converter ENUM para VARCHAR (migracao)
-- CUIDADO: isso remove a validacao do banco
-- ALTER TABLE mysql_tasks MODIFY COLUMN status VARCHAR(20);
```

### Domain Types no PostgreSQL

```sql
-- Domains: tipos reutilizaveis com validacao embutida
CREATE DOMAIN email_t AS VARCHAR(255)
    CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN cpf_t AS CHAR(11)
    CHECK (VALUE ~ '^[0-9]{11}$');

CREATE DOMAIN positive_decimal AS DECIMAL(12,2)
    CHECK (VALUE > 0);

CREATE DOMAIN phone_br AS VARCHAR(15)
    CHECK (VALUE ~ '^\+?[0-9]{10,15}$');

-- Usar domains em tabelas
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email email_t NOT NULL,
    cpf cpf_t,
    phone phone_br,
    credit_limit positive_decimal DEFAULT 0
);

-- Domains garante consistencia em toda a tabela
-- E entre tabelas que compartilham o mesmo dominio

-- SECURITY: enum bypass
-- MySQL: se o application nao valida, ENUM pode ser bypassado via:
-- 1. INSERT direto com valor invalido em modo non-strict
-- SET sql_mode = ''; -- remove strict mode
-- INSERT INTO tasks (status) VALUES ('invalid_value');
-- Resultado: campo fica vazio, nao gera erro

-- Defesa: SEMPRE usar strict mode no MySQL
SET sql_mode = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- PostgreSQL: ENUM nao pode ser bypassado
-- Tentar inserir valor invalido gera erro imediato
-- Mas cuidado com CAST silencioso em funcoes
```

### Tipos Geometricos Avancados

```sql
-- PostgreSQL: tipos geometricos em detalhes
CREATE TABLE geometric_examples (
    id SERIAL PRIMARY KEY,
    ponto POINT,             -- (x,y) ou (longitude,latitude)
    linha LINE,              -- ax + by + c = 0
    segmento LSEG,          -- ((x1,y1),(x2,y2))
    retangulo BOX,          -- ((x1,y1),(x2,y2)) sempre normalizado
    poligono POLYGON,       -- ((x1,y1),...,(xn,yn))
    circulo CIRCLE          -- ((x,y),r)
);

-- Inserir dados geometricos
INSERT INTO geometric_examples (ponto, retangulo, circulo) VALUES
(POINT '(10, 20)',
 BOX '((0,0),(100,100))',
 CIRCLE '((50,50),25)');

-- Consultar com operadores
SELECT
    id,
    ponto,
    retangulo,
    -- O ponto esta dentro do retangulo?
    retangulo @> ponto AS ponto_dentro,
    -- Distancia entre pontos
    ponto <-> POINT '(15, 25)' AS distancia,
    -- Intersecao de circulos
    circulo,
    CIRCLE '((60,60),15)' AS outro_circulo,
    (circulo && CIRCLE '((60,60),15)') AS circulos_se_sobrepoe
FROM geometric_examples;

-- PostGIS: extensao para geodados
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    geom GEOMETRY(Point, 4326)
);

-- Inserir coordenadas GPS (longitude, latitude)
INSERT INTO locations (name, geom) VALUES
('Sao Paulo', ST_SetSRID(ST_MakePoint(-46.6333, -23.5505), 4326)),
('Rio de Janeiro', ST_SetSRID(ST_MakePoint(-43.1729, -22.9068), 4326)),
('Belo Horizonte', ST_SetSRID(ST_MakePoint(-43.9386, -19.9167), 4326)),
('Curitiba', ST_SetSRID(ST_MakePoint(-49.2733, -25.4287), 4326));

-- Criar indice geografico
CREATE INDEX idx_locations_geom ON locations USING GIST (geom);

-- Buscar locais proximos (raio de 500km)
SELECT
    a.name AS local_a,
    b.name AS local_b,
    ROUND(
        ST_Distance(a.geom::geography, b.geom::geography) / 1000
    , 1) AS distancia_km
FROM locations a
CROSS JOIN locations b
WHERE a.id < b.id
AND ST_DWithin(a.geom::geography, b.geom::geography, 500000)
ORDER BY distancia_km;
```

### Tipos de Array Avancados

```sql
-- PostgreSQL: arrays multidimensionais
CREATE TABLE matrix_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    matrix INTEGER[][]   -- array 2D
);

INSERT INTO matrix_data (name, matrix) VALUES
('transform_2d', ARRAY[[1,0,0],[0,1,0],[0,0,1]]);

-- Operacoes com arrays
SELECT
    name,
    matrix,
    array_ndims(matrix) AS dimensions,
    array_length(matrix, 1) AS rows,
    array_length(matrix, 2) AS cols,
    matrix[1][1] AS first_element
FROM matrix_data;

-- Array como parameter de funcoes
CREATE OR REPLACE FUNCTION process_batch(ids BIGINT[])
RETURNS TABLE (result_id BIGINT, status TEXT) AS $$
BEGIN
    FOREACH id IN ARRAY ids LOOP
        result_id := id;
        status := 'processed';
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Chamar a funcao
SELECT * FROM process_batch(ARRAY[1, 2, 3, 4, 5]);

-- Arrays e busca inversa
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    tags TEXT[]
);

INSERT INTO tags (name, tags) VALUES
('PostgreSQL Tips', ARRAY['database', 'sql', 'postgresql', 'performance']),
('Security Basics', ARRAY['security', 'sql', 'authentication']),
('Docker Guide', ARRAY['docker', 'containers', 'devops']);

-- Buscar por tag exata
SELECT * FROM tags WHERE 'postgresql' = ANY(tags);

-- Buscar por qualquer tag
SELECT * FROM tags WHERE tags && ARRAY['sql', 'database'];

-- Contar ocorrencias de cada tag
SELECT unnest(tags) AS tag, COUNT(*) AS frequency
FROM tags
GROUP BY tag
ORDER BY frequency DESC;

-- Array de objetos como JSONB (alternativa mais flexivel)
CREATE TABLE products_v2 (
    product_id SERIAL PRIMARY KEY,
    variants JSONB[]
);

INSERT INTO products_v2 (variants) VALUES (ARRAY[
    '{"color":"red","size":"M","stock":10}'::JSONB,
    '{"color":"blue","size":"L","stock":5}'::JSONB
]);
```

### JSONB Avancado: Agregacao e Transformacao

```sql
-- Agregar dados em JSONB
SELECT jsonb_build_object(
    'total_orders', COUNT(*),
    'total_revenue', SUM(total_amount),
    'avg_order', ROUND(AVG(total_amount), 2),
    'unique_customers', COUNT(DISTINCT customer_id)
) AS summary
FROM orders
WHERE created_at >= '2024-01-01';

-- JSONB_SET para atualizar valores aninhados
UPDATE products
SET attributes = jsonb_set(
    attributes,
    '{specs,ram}',
    '"16GB"'
)
WHERE product_id = 42;

-- JSONB_PATH_QUERY para extrair dados complexos
SELECT
    product_name,
    jsonb_path_query(attributes, '$.colors[*]') AS color
FROM products
WHERE attributes @> '{"specs":{"ram":"8GB"}}';

-- JSONB_AGG para criar arrays de objetos
SELECT
    category_name,
    jsonb_agg(
        jsonb_build_object(
            'product_name', p.product_name,
            'price', p.base_price,
            'stock', p.stock_quantity
        ) ORDER BY p.base_price
    ) AS products
FROM categories c
JOIN products p ON c.category_id = p.category_id
GROUP BY c.category_name;

-- Operador @> para containment
SELECT * FROM products
WHERE attributes @> '{"specs":{"wireless":true}}';

-- Operador ? para existencia de chave
SELECT * FROM products WHERE attributes ? 'discount';

-- GIN index para performance em buscas JSONB
CREATE INDEX idx_products_attrs_gin ON products USING GIN (attributes);
CREATE INDEX idx_products_attrs_path ON products USING GIN (attributes jsonb_path_ops);

-- Comparacao de performance
-- GIN padrao: mais flexivel, suporta todos os operadores (? ?| ?& @>)
-- jsonb_path_ops: mais compacto, mais rapido para @> mas NAO suporta ?
-- Para buscas por containment: jsonb_path_ops e melhor
-- Para busca por existencia de chave: GIN padrao e necessario
```

### XML Avancado

```sql
-- XML: tipos e operacoes detalhadas

-- SQL Server: XML com schema
CREATE XML SCHEMA COLLECTION product_schema AS '
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="product">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="name" type="xs:string"/>
        <xs:element name="price" type="xs:decimal"/>
        <xs:element name="category" type="xs:string"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:integer" use="required"/>
    </xs:complexType>
  </xs:element>
</xs:schema>';

-- Criar tabela com XML tipado
CREATE TABLE typed_products (
    id INT IDENTITY PRIMARY KEY,
    product_data XML (product_schema)
);

-- Inserir dados validados pelo schema
INSERT INTO typed_products (product_data) VALUES ('
<product id="1">
    <name>Smartphone</name>
    <price>999.99</price>
    <category>Electronics</category>
</product>
');

-- PostgreSQL: xpath e xmltable
SELECT
    xt.*
FROM documents,
LATERAL unnest(xpath('//product', doc_content)) AS product_node,
LATERAL xmltable(
    '/product' PASSING product_node
    COLUMNS
        product_id INT '@id',
        name TEXT 'name/text()',
        price DECIMAL 'price/text()'
) AS xt;

-- SQL Server: XQuery avancado
SELECT
    catalog_data.query('
        for $p in /catalog/product
        return <result>
            <id>{data($p/@id)}</id>
            <name>{data($p/name)}</name>
            <total>{sum($p/items/item/price * $p/items/item/qty)}</total>
        </result>
    ') AS product_summary
FROM product_catalog;
```

### Seguranca: Encoding e Charset

```sql
-- SECURITY: problemas de encoding

-- MySQL: encoding incorreta causa truncamento silencioso
-- Se o banco esta em latin1 mas os dados sao utf8mb4:
-- Caracteres como U+FFFF sao truncados, potencialmente bypassando
-- validacao baseada em comprimento

-- Defesa: configurar charset correto desde a criacao
CREATE DATABASE myapp
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- PostgreSQL: encoding na criacao do banco
CREATE DATABASE myapp
    ENCODING = 'UTF8'
    LC_COLLATE = 'pt_BR.UTF-8'
    LC_CTYPE = 'pt_BR.UTF-8';

-- Verificar encoding atual
-- PostgreSQL
SELECT datname, pg_encoding_to_char(encoding) AS encoding
FROM pg_database WHERE datname = current_database();

-- MySQL
SHOW VARIABLES LIKE 'character_set_database';
SHOW VARIABLES LIKE 'collation_database';

-- SQL Server
SELECT name, collation_name FROM sys.databases WHERE name = DB_NAME();
```

### Seguranca: BLOBs e Data Exfiltration

```sql
-- SECURITY: BLOBs como vetor de exfiltracao

-- CENARIO: atacante insere binario com dados sensiveis
-- que se parece com codigo legito mas contem reverse shell

-- DEFESA 1: validar mime type
ALTER TABLE file_uploads
    ADD COLUMN detected_mime VARCHAR(100),
    ADD COLUMN file_hash VARCHAR(64);

-- Defesa 2: limitar tamanho de uploads
ALTER TABLE file_uploads
    ADD CONSTRAINT chk_file_size CHECK (file_size <= 10485760);  -- 10MB

-- Defesa 3: scan de malware antes de armazenar
-- (integracao com ClamAV ou similar)

-- Defesa 4: NAO executar binarios do banco de dados
-- Se binarios precisam ser executados, armazenar em filesystem
-- com controle de acesso, NAO no banco de dados
```

### Seguranca: Tipos de Dados e Encriptacao

```sql
-- Estrategias de encriptacao baseadas em tipo de dado

-- 1. Encriptacao de campo a campo (Application-Level)
CREATE TABLE sensitive_data (
    id SERIAL PRIMARY KEY,
    -- Dados encriptografados (aplicacao encripta antes de salvar)
    encrypted_cpf BYTEA,
    encrypted_phone BYTEA,
    -- Hashes (irreversiveis, para verificacao)
    password_hash VARCHAR(255),
    -- Dados pseudonimizados (para analytics)
    pseudonym_email VARCHAR(255)
);

-- 2. Transparent Data Encryption (TDE) - nivel de disco
-- PostgreSQL 16+: pg_basebackup com --encryption-algorithm=aes-256
-- SQL Server: ALTER DATABASE mydb SET ENCRYPTION ON;
-- Oracle: ALTER TABLESPACE tbs1 ENCRYPTION USING 'AES256';

-- 3. Column-Level Encryption (SQL Server)
CREATE TABLE credit_cards (
    card_id INT IDENTITY PRIMARY KEY,
    card_number VARBINARY(256) NOT NULL,
    -- Encriptar com chave especifica
    -- INSERT INTO credit_cards (card_number)
    -- VALUES (EncryptByPassPhrase('chave_secreta', '4111111111111111'));
);

-- 4. Dynamic Data Masking (SQL Server)
CREATE TABLE masked_users (
    user_id INT IDENTITY PRIMARY KEY,
    full_name NVARCHAR(100),
    email NVARCHAR(255),
    ssn NVARCHAR(20)
);

-- Aplicar mascaramento
ALTER TABLE masked_users
    ALTER COLUMN full_name ADD MASKED WITH (FUNCTION = 'partial(1,"XXX",1)');

ALTER TABLE masked_users
    ALTER COLUMN email ADD MASKED WITH (FUNCTION = 'email()');

ALTER TABLE masked_users
    ALTER COLUMN ssn ADD MASKED WITH (FUNCTION = 'partial(0,"XXX-XX-",4)');

-- Usuarios sem permissao veem dados mascarados
-- full_name: "JXXXXXXXXXa"
-- email: "aXX@XXXX.com"
-- ssn: "XXX-XX-1234"
```

### Security: JSON Path Injection

```sql
-- CENARIO: ataque via JSON path injection
-- Se a aplicacao injeta path do usuario em jsonb_path_query

-- PERIGO:
-- user_input = '$.password'  (esperado: campo seguro)
-- user_input = '$.admin_credentials.password'  (campo que nao deveria ser acessado)

-- DEFESA 1: whitelist de paths permitidos
CREATE OR REPLACE FUNCTION safe_json_extract(
    data JSONB,
    path TEXT
) RETURNS TEXT AS $$
BEGIN
    -- Apenas paths permitidos
    IF path NOT IN ('$.name', '$.email', '$.phone') THEN
        RAISE EXCEPTION 'Access denied for path: %', path;
    END IF;
    RETURN data #>> string_to_array(path, '.');
END;
$$ LANGUAGE plpgsql;

-- DEFESA 2: usar funcoes de extracao seguras
-- NUNCA use dynamic SQL com paths de usuarios
SELECT
    attributes->>'name' AS name,
    attributes->>'email' AS email
FROM customers
WHERE customer_id = $1;
-- Campos fixos, sem injecao de path possivel
```

### CHECK Constraints Avancadas

```sql
-- CHECK constraints complexas para validacao de dados

-- Validacao de JSONB (PostgreSQL 14+)
CREATE TABLE validated_config (
    config_id SERIAL PRIMARY KEY,
    config_data JSONB NOT NULL CHECK (
        jsonb_typeof(config_data) = 'object'
        AND config_data ? 'name'
        AND config_data ? 'version'
        AND jsonb_typeof(config_data->'name') = 'string'
        AND jsonb_typeof(config_data->'version') = 'string'
    )
);

-- Validacao de ranges
CREATE TABLE availability (
    id SERIAL PRIMARY KEY,
    room_id INTEGER NOT NULL,
    booking_period TSTZRANGE NOT NULL,
    price_per_night DECIMAL(10,2) NOT NULL,

    -- Garantir que bookings nao se sobrepoem
    EXCLUDE USING gist (
        room_id WITH =,
        booking_period WITH &&
    )
);

-- Validacao de arrays
CREATE TABLE survey_responses (
    response_id SERIAL PRIMARY KEY,
    answers JSONB NOT NULL CHECK (
        jsonb_array_length(answers) BETWEEN 1 AND 50
    ),
    CHECK (
        -- Cada resposta deve ser um objeto com question_id e value
        jsonb_path_exists(
            answers,
            '$[*] ? (@.question_id && @.value)'
        )
    )
);

-- CHECK constraints com subqueries (PostgreSQL 9.6+)
CREATE TABLE project_assignments (
    assignment_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    hours_per_week INTEGER NOT NULL,

    -- Um funcionario nao pode ter mais de 40h/semana total
    CHECK (
        (SELECT COALESCE(SUM(hours_per_week), 0)
         FROM project_assignments pa2
         WHERE pa2.employee_id = project_assignments.employee_id
         AND pa2.assignment_id != project_assignments.assignment_id)
        + hours_per_week <= 40
    )
);
```

### Materialized Views Avancadas

```sql
-- Materialized views com dependencias
CREATE MATERIALIZED VIEW mv_dashboard_summary AS
WITH
active_customers AS (
    SELECT
        customer_id,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS lifetime_value
    FROM orders
    WHERE status NOT IN ('cancelled', 'refunded')
    AND created_at >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY customer_id
),
top_products AS (
    SELECT
        product_id,
        SUM(quantity) AS units_sold,
        SUM(total_amount) AS revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status NOT IN ('cancelled', 'refunded')
    GROUP BY product_id
)
SELECT
    (SELECT COUNT(*) FROM customers WHERE is_active) AS total_active_customers,
    (SELECT COUNT(*) FROM orders WHERE created_at >= CURRENT_DATE) AS orders_today,
    (SELECT SUM(total_amount) FROM orders WHERE created_at >= CURRENT_DATE) AS revenue_today,
    (SELECT AVG(lifetime_value) FROM active_customers) AS avg_customer_ltv,
    (SELECT COUNT(*) FROM products WHERE is_active AND stock_quantity > 0) AS in_stock_products;

-- Refresh programado
-- Em producao, usar pg_cron ou scheduler externo
-- SELECT cron.schedule('refresh-dashboard', '*/5 * * * *',
--     'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_summary');

-- Verificar status da MV
SELECT
    matviewname,
    ispopulated,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || matviewname)) AS size
FROM pg_matviews
WHERE schemaname = 'public';
```

---

## 2.10 CHECK Constraints e Validação

### CHECK Constraints Basicas

```sql
-- CHECK constraints: validacao declarativa
CREATE TABLE products_v2 (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0,
    stock_quantity INTEGER NOT NULL,
    sku VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,

    -- Validacao basica
    CHECK (price > 0),
    CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CHECK (stock_quantity >= 0),
    CHECK (status IN ('active', 'inactive', 'discontinued')),

    -- Constraint nomeada (IMPORTANTE para debugging)
    CONSTRAINT chk_sku_format CHECK (sku ~ '^[A-Z]{2,4}-[0-9]{4,8}$'),
    CONSTRAINT chk_price_after_discount CHECK (price * (1 - discount_percent/100) > 0)
);

-- CHECK com subquery (PostgreSQL 9.6+)
CREATE TABLE orders_v2 (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    credit_used DECIMAL(10,2) NOT NULL DEFAULT 0,

    -- Verificar limite de credito do cliente
    CHECK (
        credit_used <= (
            SELECT credit_limit
            FROM customers
            WHERE customer_id = orders_v2.customer_id
        )
    )
);
```

### Validacao de Dados Complexos

```sql
-- Validacao de email
CREATE OR REPLACE FUNCTION is_valid_email(e TEXT) RETURNS BOOLEAN AS $$
BEGIN
    RETURN e ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validacao de CPF brasileiro
CREATE OR REPLACE FUNCTION is_valid_cpf(cpf TEXT) RETURNS BOOLEAN AS $$
DECLARE
    digits INTEGER[];
    sum_val INTEGER := 0;
    remainder INTEGER;
BEGIN
    cpf := regexp_replace(cpf, '[^0-9]', '', 'g');
    IF LENGTH(cpf) != 11 THEN RETURN FALSE; END IF;
    IF cpf ~ '^(\d)\1{10}$' THEN RETURN FALSE; END IF;

    digits := ARRAY(SELECT CAST(digit AS INTEGER)
                    FROM regexp_split_to_table(cpf, '') AS digit);

    FOR i IN 1..9 LOOP
        sum_val := sum_val + digits[i] * (11 - i);
    END LOOP;
    remainder := sum_val % 11;
    IF remainder < 2 THEN remainder := 0;
    ELSE remainder := 11 - remainder; END IF;
    IF digits[10] != remainder THEN RETURN FALSE; END IF;

    sum_val := 0;
    FOR i IN 1..10 LOOP
        sum_val := sum_val + digits[i] * (12 - i);
    END LOOP;
    remainder := sum_val % 11;
    IF remainder < 2 THEN remainder := 0;
    ELSE remainder := 11 - remainder; END IF;
    RETURN digits[11] = remainder;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validacao de IP
CREATE OR REPLACE FUNCTION is_valid_ipv4(ip TEXT) RETURNS BOOLEAN AS $$
BEGIN
    RETURN ip ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Aplicar todas as validacoes
CREATE TABLE customers_v3 (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    cpf CHAR(11) NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_email CHECK (is_valid_email(email)),
    CONSTRAINT chk_cpf CHECK (is_valid_cpf(cpf)),
    CONSTRAINT chk_ip CHECK (ip_address IS NULL OR is_valid_ipv4(ip_address)),
    CONSTRAINT uq_email UNIQUE (email),
    CONSTRAINT uq_cpf UNIQUE (cpf)
);
```

### SECURITY: CHECK Constraint Bypass

```sql
-- CUIDADO: CHECK constraints podem ser bypassadas em certas condicoes

-- 1. MySQL antigo (< 8.0.16): CHECK era parsed mas NAO executado
-- MySQL 8.0.16+: CHECK constraints sao validadas
-- Verificar: SELECT version();

-- 2. PostgreSQL: DISABLE TRIGGER pode desabilitar CHECKs
-- Apenas superuser pode desabilitar triggers
-- Defesa: NAO dar superuser para aplicacoes

-- 3. SQL Server: CHECK constraints podem ser desabilitadas
-- ALTER TABLE t NOCHECK CONSTRAINT constraint_name
-- Defesa: monitorar alteracoes no schema

-- 4. Insercao via COPY/LOAD DATA pode ignorar CHECKs em alguns SGBDRs
-- PostgreSQL: COPY respeita CHECK constraints
-- MySQL: LOAD DATA pode ignorar com warnings

-- Melhor defesa: validacao em camadas
-- 1. CHECK constraints no banco (ultima linha de defesa)
-- 2. Validacao no ORM/model layer
-- 3. Validacao no frontend ( UX, nao seguranca)
```

---

## 2.11 Materialized Views

### Criacao e Gerenciamento

```sql
-- Materialized View: query pre-calculada armazenada fisicamente
CREATE MATERIALIZED VIEW mv_monthly_revenue AS
SELECT
    date_trunc('month', o.order_date)::DATE AS month,
    p.product_category,
    r.region_name,
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT o.customer_id) AS customer_count,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id
JOIN regions r ON o.region_id = r.region_id
WHERE o.status != 'cancelled'
GROUP BY 1, 2, 3;

-- Criar indice na materialized view
CREATE UNIQUE INDEX idx_mv_monthly_revenue
ON mv_monthly_revenue(month, product_category, region_name);

-- Consultar (rapido, dados pre-calculados)
SELECT * FROM mv_monthly_revenue
WHERE month >= '2024-01-01'
ORDER BY total_revenue DESC;

-- Atualizar (REFRESH)
REFRESH MATERIALIZED VIEW mv_monthly_revenue;

-- Atualizacao concorrente (PostgreSQL, requer unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_revenue;
-- Nao bloqueia leituras durante o refresh

-- Verificar ultima atualizacao
SELECT
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || matviewname)) AS size
FROM pg_matviews
WHERE schemaname = 'public';
```

### SECURITY: Stale Data e Materialized Views

```sql
-- PROBLEMA: dados desatualizados em MV
-- Se a MV nao e atualizada frequentemente, consultas podem retornar
-- dados incorretos que parecem confiaveis

-- Exemplo: MV usada para calculo de comissao
-- MV mostra receita de $100.000
-- Receita real: $95.000 (pedidos cancelados nao refletidos)
-- Comissao paga a mais: $500

-- DEFESA 1: atualizar MV antes de calculos criticos
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_revenue;

-- DEFESA 2: adicionar timestamp de atualizacao
CREATE MATERIALIZED VIEW mv_fresh_data AS
SELECT *, CURRENT_TIMESTAMP AS last_refreshed
FROM expensive_query
WITH DATA;

-- DEFESA 3: usar view normal quando fresh data e critico
CREATE VIEW v_fresh_data AS
SELECT *, CURRENT_TIMESTAMP AS computed_at
FROM expensive_query;
-- View normal: dados sempre frescos, mas mais lenta
```

---

## 2.12 Schema Design Patterns

### Star Schema

```sql
-- Star Schema: schema dimensional para data warehousing
-- Fato no centro, dimensoes ao redor

-- Dimensoes
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,  -- 20240101
    full_date DATE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN
);

CREATE TABLE dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    price DECIMAL(10,2)
);

CREATE TABLE dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    customer_name VARCHAR(100),
    segment VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50)
);

-- Tabela de fato
CREATE TABLE fact_sales (
    sale_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    product_key INTEGER REFERENCES dim_product(product_key),
    customer_key INTEGER REFERENCES dim_customer(customer_key),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(12,2),
    discount DECIMAL(10,2),
    tax DECIMAL(10,2)
);

-- Indices para performance analitica
CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_product ON fact_sales(product_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
```

### Snowflake Schema

```sql
-- Snowflake: dimensoes normalizadas
-- Mais normalizado, menos redundancia, mais joins

CREATE TABLE dim_category (
    category_key SERIAL PRIMARY KEY,
    category_name VARCHAR(100)
);

CREATE TABLE dim_brand (
    brand_key SERIAL PRIMARY KEY,
    brand_name VARCHAR(100)
);

-- Produto referencia category e brand (normalizado)
CREATE TABLE dim_product_snowflake (
    product_key SERIAL PRIMARY KEY,
    product_id INTEGER,
    product_name VARCHAR(200),
    category_key INTEGER REFERENCES dim_category(category_key),
    brand_key INTEGER REFERENCES dim_brand(brand_key)
);
```

### EAV (Entity-Attribute-Value)

```sql
-- EAV: flexivel mas complexo
CREATE TABLE eav_entity (
    entity_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE eav_attribute (
    attribute_id SERIAL PRIMARY KEY,
    attribute_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(20) NOT NULL CHECK (data_type IN (
        'string', 'integer', 'decimal', 'date', 'boolean'
    ))
);

CREATE TABLE eav_value (
    value_id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES eav_entity(entity_id),
    attribute_id INTEGER REFERENCES eav_attribute(attribute_id),
    value_string TEXT,
    value_integer INTEGER,
    value_decimal DECIMAL(12,4),
    value_date DATE,
    value_boolean BOOLEAN,
    UNIQUE (entity_id, attribute_id)
);

-- Inserir atributos
INSERT INTO eav_attribute (attribute_name, data_type) VALUES
('color', 'string'),
('weight_kg', 'decimal'),
('warranty_years', 'integer'),
('in_stock', 'boolean');

-- Consultar: pivoteamento manual
SELECT
    e.entity_id,
    MAX(CASE WHEN a.attribute_name = 'color' THEN v.value_string END) AS color,
    MAX(CASE WHEN a.attribute_name = 'weight_kg' THEN v.value_decimal::TEXT END) AS weight,
    MAX(CASE WHEN a.attribute_name = 'warranty_years' THEN v.value_integer::TEXT END) AS warranty,
    MAX(CASE WHEN a.attribute_name = 'in_stock' THEN v.value_boolean::TEXT END) AS in_stock
FROM eav_entity e
JOIN eav_value v ON e.entity_id = v.entity_id
JOIN eav_attribute a ON v.attribute_id = a.attribute_id
GROUP BY e.entity_id;
```

### Table Inheritance Patterns

```sql
-- Single Table Inheritance (STI): tudo em uma tabela
CREATE TABLE vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    vehicle_type VARCHAR(20) NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    -- Car-specific
    num_doors INTEGER,
    trunk_size DECIMAL,
    -- Truck-specific
    payload_capacity DECIMAL,
    num_axles INTEGER,
    -- Motorcycle-specific
    engine_cc INTEGER,
    has_sidecar BOOLEAN,
    -- Muitos NULLs possiveis
    CHECK (
        (vehicle_type = 'car' AND num_doors IS NOT NULL)
        OR (vehicle_type = 'truck' AND payload_capacity IS NOT NULL)
        OR (vehicle_type = 'motorcycle' AND engine_cc IS NOT NULL)
    )
);

-- Class Table Inheritance (CTI): tabelas separadas
CREATE TABLE vehicles_base (
    vehicle_id SERIAL PRIMARY KEY,
    vehicle_type VARCHAR(20) NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER
);

CREATE TABLE cars (
    vehicle_id INTEGER PRIMARY KEY REFERENCES vehicles_base(vehicle_id),
    num_doors INTEGER NOT NULL,
    trunk_size DECIMAL
);

CREATE TABLE trucks (
    vehicle_id INTEGER PRIMARY KEY REFERENCES vehicles_base(vehicle_id),
    payload_capacity DECIMAL NOT NULL,
    num_axles INTEGER NOT NULL
);

-- Concrete Table Inheritance: cada tipo e sua propria tabela
CREATE TABLE concrete_cars (
    car_id SERIAL PRIMARY KEY,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    num_doors INTEGER NOT NULL,
    trunk_size DECIMAL
);

CREATE TABLE concrete_trucks (
    truck_id SERIAL PRIMARY KEY,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    payload_capacity DECIMAL NOT NULL,
    num_axles INTEGER NOT NULL
);
```

---

## 2.13 Naming Conventions

```sql
-- CONVENCOES RECOMENDADAS

-- 1. snake_case para tudo (tabelas, colunas, indices, constraints)
CREATE TABLE order_items (       -- CORRETO
-- CREATE TABLE OrderItems (     -- ERRADO
-- CREATE TABLE ORDER_ITEMS (    -- aceitavel, mas nao padrao

-- 2. Singular para tabelas
CREATE TABLE customer (          -- CORRETO
-- CREATE TABLE customers (      -- padrao alternativa, ambos sao aceitos

-- 3. Prefijo para chaves estrangeiras
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customer(customer_id),  -- FK com nome claro
    shipping_address_id INTEGER REFERENCES address(address_id)
);

-- 4. Nomes descritivos para constraints
ALTER TABLE orders
    ADD CONSTRAINT fk_orders_customer          -- prefixo FK
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    ADD CONSTRAINT chk_orders_total_positive   -- prefixo CHK
        CHECK (total_amount > 0),
    ADD CONSTRAINT uq_orders_number            -- prefixo UQ
        UNIQUE (order_number);

-- 5. Indices: idx_tabela_colunas
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);

-- 6. Temporal columns: _at para timestamps, _at para dates
ALTER TABLE orders
    ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN deleted_at TIMESTAMP NULL;  -- soft delete

-- 7. Boolean columns: is_ ou has_
ALTER TABLE products
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN has_warranty BOOLEAN NOT NULL DEFAULT FALSE;
```

### Documentacao de Schema Avancada

```sql
-- PostgreSQL: documentacao completa com queries uteis
-- Gerar documentacao automatica do schema

-- Listar todas as tabelas com comentarios e tamanho
SELECT
    c.relname AS table_name,
    obj_description(c.oid) AS table_comment,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS table_size,
    (SELECT COUNT(*) FROM pg_attribute
     WHERE attrelid = c.oid AND attnum > 0 AND NOT attisdropped) AS column_count
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;

-- Listar todas as foreign keys com caminho completo
SELECT
    tc.table_name AS from_table,
    kcu.column_name AS from_column,
    ccu.table_name AS to_table,
    ccu.column_name AS to_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- Listar indices e seus tamanhos
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Gerar diagrama ER (texto simples)
SELECT
    tc.table_name || ' -> ' || ccu.table_name AS relationship,
    tc.constraint_name,
    kcu.column_name || ' = ' || ccu.column_name AS on_clause
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public';

-- MySQL: listar estrutura do schema
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS index_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
ORDER BY DATA_LENGTH DESC;
```

### Schema Patterns: Temporal Tables

```sql
-- Temporal Tables: historico automatico de mudancas

-- SQL Server 2016+: temporal tables nativas
CREATE TABLE products_temporal (
    product_id INT IDENTITY PRIMARY KEY,
    product_name NVARCHAR(200),
    price DECIMAL(10,2),
    valid_from DATETIME2 GENERATED ALWAYS AS ROW START,
    valid_to DATETIME2 GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (valid_from, valid_to)
)
WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.products_history));

-- Query temporal: ver estado em ponto no tempo
SELECT * FROM products_temporal
FOR SYSTEM_TIME AS OF '2024-01-15 10:00:00';

-- Query temporal: intervalo de tempo
SELECT * FROM products_temporal
FOR SYSTEM_TIME BETWEEN '2024-01-01' AND '2024-06-30';

-- PostgreSQL: simulacao com triggers
CREATE TABLE products_v2 (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(200),
    price DECIMAL(10,2),
    is_current BOOLEAN DEFAULT TRUE,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP
);

CREATE TABLE products_history (
    history_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER,
    product_name VARCHAR(200),
    price DECIMAL(10,2),
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    changed_by VARCHAR(100)
);

-- Trigger para historico
CREATE OR REPLACE FUNCTION track_product_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        -- Mover versao antiga para historico
        INSERT INTO products_history (product_id, product_name, price, valid_from, valid_to, changed_by)
        VALUES (OLD.product_id, OLD.product_name, OLD.price, OLD.valid_from, CURRENT_TIMESTAMP, current_user);
        -- Atualizar versao atual
        NEW.valid_from = CURRENT_TIMESTAMP;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO products_history (product_id, product_name, price, valid_from, valid_to, changed_by)
        VALUES (OLD.product_id, OLD.product_name, OLD.price, OLD.valid_from, CURRENT_TIMESTAMP, current_user);
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_temporal
    BEFORE UPDATE OR DELETE ON products_v2
    FOR EACH ROW
    EXECUTE FUNCTION track_product_changes();
```

### Schema Patterns: Multi-Tenancy

```sql
-- Multi-Tenancy com isolamento por tenant_id

-- Todas as tabelas de negocio incluem tenant_id
CREATE TABLE products_mt (
    product_id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    product_name VARCHAR(200),
    price DECIMAL(10,2)
);

CREATE TABLE orders_mt (
    order_id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    customer_id INTEGER,
    total DECIMAL(12,2)
);

-- Row-Level Security para isolamento
ALTER TABLE products_mt ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders_mt ENABLE ROW LEVEL SECURITY;

CREATE POLICY products_tenant ON products_mt
    USING (tenant_id = current_setting('app.tenant_id')::INTEGER);

CREATE POLICY orders_tenant ON orders_mt
    USING (tenant_id = current_setting('app.tenant_id')::INTEGER);

-- Indices compostos para performance
CREATE INDEX idx_products_mt_tenant ON products_mt(tenant_id, product_name);
CREATE INDEX idx_orders_mt_tenant ON orders_mt(tenant_id, customer_id);

-- Configurar tenant na sessao
SET app.tenant_id = '42';
-- Agora todas as queries retornam apenas dados deste tenant
SELECT * FROM products_mt;  -- Retorna apenas produtos do tenant 42
```

### Schema Patterns: Materialized Views para Cache

```sql
-- Materialized View com refresh programado

-- Criar MV para dashboard
CREATE MATERIALIZED VIEW mv_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM orders WHERE created_at >= CURRENT_DATE) AS orders_today,
    (SELECT SUM(total_amount) FROM orders WHERE created_at >= CURRENT_DATE) AS revenue_today,
    (SELECT COUNT(*) FROM customers WHERE created_at >= CURRENT_DATE) AS new_customers_today,
    (SELECT AVG(total_amount) FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL '30 day') AS avg_order_30d;

-- Atualizar periodicamente (usar pg_cron)
-- SELECT cron.schedule('refresh-kpis', '*/5 * * * *',
--     'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_kpis');

-- Verificar ultima atualizacao
SELECT
    matviewname,
    ispopulated,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || matviewname)) AS size
FROM pg_matviews
WHERE schemaname = 'public';
```

---

## 2.14 Documentação de Schema

```sql
-- PostgreSQL: COMMENT ON
COMMENT ON TABLE customers IS
    'Armazena informacoes de clientes ativos e inativos do sistema. '
    'Tabela central do dominio de vendas.';

COMMENT ON COLUMN customers.customer_id IS
    'Identificador unico do cliente. Gerado automaticamente via SERIAL.';

COMMENT ON COLUMN customers.email IS
    'Email unico do cliente. Usado para login e comunicacao. '
    'Validado por constraint CHECK com regex.';

COMMENT ON COLUMN customers.cpf IS
    'CPF do cliente (somente digitos). Armazenado encriptografado em producao.';

-- Listar documentacao
SELECT
    c.table_name,
    obj_description(c.table_name::regclass) AS table_comment
FROM information_schema.tables c
WHERE c.table_schema = 'public'
AND c.table_type = 'BASE TABLE';

SELECT
    column_name,
    col_description(
        (table_schema || '.' || table_name)::regclass,
        ordinal_position
    ) AS column_comment
FROM information_schema.columns
WHERE table_name = 'customers';

-- SQL Server: extended properties
EXEC sp_addextendedproperty
    @name = 'MS_Description',
    @value = 'Tabela de clientes ativos do sistema',
    @level0type = 'SCHEMA',
    @level0name = 'dbo',
    @level1type = 'TABLE',
    @level1name = 'customers';
```

---

## 2.15 Exemplo: Schema Completo de E-commerce

Este e um schema completo e funcional para um sistema de e-commerce, incorporando todos os topicos discutidos neste capitulo.

```sql
-- ============================================================
-- SCHEMA COMPLETO DE E-COMMERCE
-- PostgreSQL 15+
-- ============================================================

-- Dominios reutilizaveis
CREATE DOMAIN email_t AS VARCHAR(255)
    CHECK (VALUE ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

CREATE DOMAIN positive_decimal AS DECIMAL(12,2)
    CHECK (VALUE > 0);

CREATE DOMAIN phone_t AS VARCHAR(15)
    CHECK (VALUE ~ '^\+?[0-9]{10,15}$');

-- Enums
CREATE TYPE order_status AS ENUM (
    'pending', 'confirmed', 'processing', 'shipped',
    'delivered', 'cancelled', 'returned', 'refunded'
);

CREATE TYPE payment_status AS ENUM (
    'pending', 'authorized', 'captured', 'failed',
    'refunded', 'partially_refunded'
);

CREATE TYPE payment_method AS ENUM (
    'credit_card', 'debit_card', 'pix', 'boleto',
    'bank_transfer', 'wallet'
);

-- ============================================================
-- TABELAS DE IDENTIDADE E ACESSO
-- ============================================================

CREATE TABLE tenants (
    tenant_id SERIAL PRIMARY KEY,
    tenant_name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    email email_t NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,

    CONSTRAINT uq_users_email_tenant UNIQUE (tenant_id, email),
    CONSTRAINT chk_users_email CHECK (is_valid_email(email))
);

CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- DOMINIO DE PRODUTOS
-- ============================================================

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    parent_category_id INTEGER REFERENCES categories(category_id),
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_category_slug_tenant UNIQUE (tenant_id, slug)
);

CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    sku VARCHAR(50) NOT NULL,
    name VARCHAR(300) NOT NULL,
    slug VARCHAR(300) NOT NULL,
    description TEXT,
    short_description VARCHAR(500),
    base_price positive_decimal NOT NULL,
    compare_at_price positive_decimal,
    cost_price positive_decimal,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    weight_kg DECIMAL(8,3),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_digital BOOLEAN NOT NULL DEFAULT FALSE,
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_product_sku_tenant UNIQUE (tenant_id, sku),
    CONSTRAINT uq_product_slug_tenant UNIQUE (tenant_id, slug),
    CONSTRAINT chk_compare_price CHECK (
        compare_at_price IS NULL OR compare_at_price >= base_price
    ),
    CONSTRAINT chk_cost_price CHECK (
        cost_price IS NULL OR cost_price <= base_price
    )
);

CREATE TABLE product_images (
    image_id SERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    alt_text VARCHAR(200),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE product_variants (
    variant_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    sku VARCHAR(50) NOT NULL,
    name VARCHAR(200),
    price positive_decimal NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_variant_sku UNIQUE (product_id, sku),
    CONSTRAINT chk_variant_stock CHECK (stock_quantity >= 0)
);

-- ============================================================
-- DOMINIO DE CLIENTES E ENDERECOS
-- ============================================================

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    user_id BIGINT REFERENCES users(user_id),
    full_name VARCHAR(200) NOT NULL,
    email email_t NOT NULL,
    phone phone_t,
    document_number VARCHAR(20),
    document_type VARCHAR(10) CHECK (document_type IN ('cpf', 'cnpj', 'passport')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_customer_email_tenant UNIQUE (tenant_id, email)
);

CREATE TABLE addresses (
    address_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    address_type VARCHAR(20) NOT NULL CHECK (address_type IN ('billing', 'shipping', 'both')),
    recipient_name VARCHAR(200),
    street VARCHAR(300) NOT NULL,
    number VARCHAR(20),
    complement VARCHAR(100),
    neighborhood VARCHAR(100),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country CHAR(2) NOT NULL DEFAULT 'BR',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- DOMINIO DE PEDIDOS
-- ============================================================

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(tenant_id),
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    order_number VARCHAR(30) NOT NULL,
    status order_status NOT NULL DEFAULT 'pending',
    subtotal DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    shipping_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) GENERATED ALWAYS AS (
        subtotal - discount_amount + tax_amount + shipping_amount
    ) STORED,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    notes TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    shipping_address_id BIGINT REFERENCES addresses(address_id),
    billing_address_id BIGINT REFERENCES addresses(address_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,

    CONSTRAINT uq_order_number_tenant UNIQUE (tenant_id, order_number),
    CONSTRAINT chk_order_subtotal CHECK (subtotal >= 0),
    CONSTRAINT chk_order_discount CHECK (discount_amount >= 0),
    CONSTRAINT chk_order_tax CHECK (tax_amount >= 0),
    CONSTRAINT chk_order_shipping CHECK (shipping_amount >= 0)
);

CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    variant_id BIGINT REFERENCES product_variants(variant_id),
    product_name VARCHAR(300) NOT NULL,
    sku VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_price DECIMAL(12,2) GENERATED ALWAYS AS (
        (quantity * unit_price) - discount_amount + tax_amount
    ) STORED,

    CONSTRAINT chk_item_quantity CHECK (quantity > 0),
    CONSTRAINT chk_item_price CHECK (unit_price > 0)
);

-- ============================================================
-- DOMINIO DE PAGAMENTOS
-- ============================================================

CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    payment_method payment_method NOT NULL,
    status payment_status NOT NULL DEFAULT 'pending',
    amount DECIMAL(12,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'BRL',
    gateway_transaction_id VARCHAR(100),
    gateway_response JSONB,
    paid_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_payment_amount CHECK (amount > 0)
);

CREATE TABLE refunds (
    refund_id BIGSERIAL PRIMARY KEY,
    payment_id BIGINT NOT NULL REFERENCES payments(payment_id),
    amount DECIMAL(12,2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_refund_amount CHECK (amount > 0)
);

-- ============================================================
-- DOMINIO DE INVENTARIO
-- ============================================================

CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    variant_id BIGINT REFERENCES product_variants(variant_id),
    warehouse_code VARCHAR(20) NOT NULL,
    quantity_available INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    reorder_point INTEGER NOT NULL DEFAULT 10,
    reorder_quantity INTEGER NOT NULL DEFAULT 100,
    last_counted_at TIMESTAMP,

    CONSTRAINT chk_inventory_available CHECK (quantity_available >= 0),
    CONSTRAINT chk_inventory_reserved CHECK (quantity_reserved >= 0),
    CONSTRAINT chk_inventory_total CHECK (quantity_available >= quantity_reserved),
    CONSTRAINT uq_inventory_product_warehouse UNIQUE (product_id, variant_id, warehouse_code)
);

-- ============================================================
-- DOMINIO DE AVALIACOES
-- ============================================================

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(product_id),
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    order_id BIGINT REFERENCES orders(order_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(200),
    body TEXT,
    is_verified_purchase BOOLEAN NOT NULL DEFAULT FALSE,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    helpful_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_review_per_order UNIQUE (order_id, customer_id)
);

-- ============================================================
-- TABELA DE AUDITORIA
-- ============================================================

CREATE TABLE audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(tenant_id),
    table_name VARCHAR(100) NOT NULL,
    record_id BIGINT NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Indices para performance
CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_changed_at ON audit_log(changed_at DESC);
CREATE INDEX idx_audit_tenant ON audit_log(tenant_id, changed_at DESC);

-- ============================================================
-- MATERIALIZED VIEW PARA RELATORIOS
-- ============================================================

CREATE MATERIALIZED VIEW mv_sales_summary AS
SELECT
    o.tenant_id,
    date_trunc('month', o.created_at)::DATE AS month,
    p.category_id,
    c.name AS category_name,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(oi.quantity) AS total_units,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value,
    SUM(o.discount_amount) AS total_discounts
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
WHERE o.status NOT IN ('cancelled', 'refunded')
GROUP BY 1, 2, 3, 4;

CREATE UNIQUE INDEX idx_mv_sales_summary
ON mv_sales_summary(tenant_id, month, category_id);
```

---

## Resumo

Este capitulo explorou profundamente os tipos de dados disponiveis nos principais SGBDRs. Cada tipo de dados tem implicacoes de performance, seguranca, e portabilidade. A escolha errada de tipo pode levar a bugs dificeis de detectar, como overflow de inteiros, imprecisao de ponto flutuante em valores monetarios, e erros de timezone em datas.

Estudamos tipos numericos, de texto, data/hora, binarios, JSON/JSONB, XML, geometricos, arrays, enums, e domains. Cada tipo foi apresentado com exemplos praticos em multiplos dialectos e com notas de seguranca relevantes.

Exploramos CHECK constraints como mecanismo de validacao declarativa, materialized views para cache de queries, e padroes de design de esquemas como star schema, snowflake, EAV, e heranca de tabelas. Estabelecemos convencoes de nomenclatura e documentacao de schemas.

O schema completo de e-commerce demostra como todos esses topicos se integram em um sistema real e funcional. No proximo capitulo, aprofundaremos nos JOINs, CTEs e subqueries — as ferramentas fundamentais para consultar e manipular dados complexos.

---

*[Proximo capitulo: 03 — Joins, CTEs e Subqueries](03-joins-ctes-subqueries.md)*
