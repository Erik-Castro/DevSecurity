# Partitioning e Sharding

## Visão Geral

À medida que bancos de dados crescem para milhões ou bilhões de registros, consultas que antes executavam em milissegundos começam a levar minutos ou horas. Partitioning divide tabelas grandes em pedaços menores e mais gerenciáveis dentro do mesmo banco, enquanto sharding distribui dados entre múltiplos servidores. Este capítulo explora as estratégias, configurações e padrões para escalar bancos de dados além das limitações de um único servidor.

## Por que Partitioning

### O Problema de Tabelas Grandes

Tabelas com centenas de milhões de linhas apresentam problemas específicos que o partitioning resolve:

```sql
-- Tabela de logs sem partitioning
CREATE TABLE access_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50),
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Inserir 500 milhões de registros
INSERT INTO access_logs (user_id, action, ip_address, created_at, details)
SELECT
    (random() * 1000000)::INTEGER,
    CASE (random() * 4)::INTEGER
        WHEN 0 THEN 'login'
        WHEN 1 THEN 'logout'
        WHEN 2 THEN 'purchase'
        WHEN 3 THEN 'view'
        WHEN 4 THEN 'search'
    END,
    inet_make_addr(
        (random() * 255)::INTEGER,
        (random() * 255)::INTEGER,
        (random() * 255)::INTEGER,
        (random() * 255)::INTEGER
    ),
    NOW() - (random() * 365 * 24 * 60 * 60 || ' seconds')::INTERVAL,
    jsonb_build_object(
        'session_id', gen_random_uuid(),
        'user_agent', 'Mozilla/5.0'
    )
FROM generate_series(1, 500000000);

-- Query de 30 dias: seq scan em 500M de linhas
EXPLAIN ANALYZE
SELECT action, COUNT(*)
FROM access_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY action;
-- Seq Scan: 45.000ms (45 segundos!)
-- Buffers: 7.500.000 shared hit

-- Índice ajuda mas ainda precisa varrer muitos registros
CREATE INDEX idx_logs_created
ON access_logs (created_at);

EXPLAIN ANALYZE
SELECT action, COUNT(*)
FROM access_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY action;
-- Index Scan: 12.000ms (12 segundos)
-- Ainda precisa ler milhões de registros do índice
```

### Benefícios do Partitioning

```sql
-- Com partitioning por mês, a query anterior acessa apenas 1 partição
-- Tempo: ~50ms (redução de 99.9%)
-- Buffers: ~5.000 (redução de 99.9%)
```

## Range Partitioning

### Criação de Tabela Particionada

```sql
-- Criar tabela principal particionada
CREATE TABLE logs_partitioned (
    log_id BIGSERIAL,
    user_id INTEGER,
    action VARCHAR(50),
    ip_address INET,
    created_at TIMESTAMP NOT NULL,
    details JSONB,
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

-- Criar partição para cada mês
CREATE TABLE logs_2024_01 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE logs_2024_02 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

CREATE TABLE logs_2024_03 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

CREATE TABLE logs_2024_04 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');

CREATE TABLE logs_2024_05 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');

CREATE TABLE logs_2024_06 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');

-- Índices em cada partição (ou na tabela pai para todos)
CREATE INDEX idx_logs_2024_01_user
ON logs_2024_01 (user_id, action);

CREATE INDEX idx_logs_2024_02_user
ON logs_2024_02 (user_id, action);

-- Ou criar na tabela pai (aplica a todas as partições)
CREATE INDEX idx_logs_partitioned_user
ON logs_partitioned (user_id, action);
```

### Inserção com Partitioning

```sql
-- Inserção automática: PostgreSQL direciona para partição correta
INSERT INTO logs_partitioned (user_id, action, ip_address, created_at)
VALUES (42, 'login', '192.168.1.1', '2024-03-15 10:30:00');
-- Vai automaticamente para logs_2024_03

-- Verificar em qual partição a linha foi inserida
SELECT tableoid::regclass, *
FROM logs_partitioned
WHERE created_at = '2024-03-15 10:30:00';
-- tableoid: logs_2024_03

-- Inserir fora do range configurado: ERRO
INSERT INTO logs_partitioned (user_id, action, created_at)
VALUES (1, 'login', '2023-01-01');
-- ERROR: no partition of relation "logs_partitioned" found for row
-- Detail: Partition key of the inserted row does not match any of the existing partitions
```

### Criação Automática de Partições

```sql
-- Função para criar partições futuras automaticamente
CREATE OR REPLACE FUNCTION create_monthly_partitions(
    p_table_name TEXT,
    p_schema TEXT DEFAULT 'public'
) RETURNS void AS $$
DECLARE
    v_start_date DATE;
    v_end_date DATE;
    v_partition_name TEXT;
    v_month TEXT;
BEGIN
    -- Criar partições para os próximos 3 meses
    FOR i IN 0..2 LOOP
        v_start_date := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        v_end_date := v_start_date + INTERVAL '1 month';
        v_month := TO_CHAR(v_start_date, 'YYYY_MM');
        v_partition_name := p_table_name || '_' || v_month;

        -- Verificar se partição já existe
        IF NOT EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = v_partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L)',
                p_schema, v_partition_name,
                p_schema, p_table_name,
                v_start_date, v_end_date
            );
            RAISE NOTICE 'Created partition: %', v_partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Executar criação de partições
SELECT create_monthly_partitions('logs_partitioned');

-- Agendar execução mensal via pg_cron
-- CREATE EXTENSION pg_cron;
-- SELECT cron.schedule('create-partitions', '0 0 1 * *',
--     $$SELECT create_monthly_partitions('logs_partitioned')$$);
```

### Partition Pruning

Partition pruning é a otimização onde o PostgreSQL acessa apenas as partições relevantes para uma query.

```sql
-- Query que benefit de partition pruning
EXPLAIN ANALYZE
SELECT action, COUNT(*)
FROM logs_partitioned
WHERE created_at >= '2024-03-01'
AND created_at < '2024-04-01'
GROUP BY action;
-- Append (cost=0.00..1234.56 rows=1000 width=12)
--   -> Seq Scan on logs_2024_03 (cost=0.00..1234.56 rows=1000 width=12)
-- Apenas logs_2024_03 é acessada!

-- Verificar partition pruning
EXPLAIN VERBOSE
SELECT * FROM logs_partitioned
WHERE created_at BETWEEN '2024-03-15' AND '2024-03-20';
-- Detalhes mostram qual partição foi selecionada

-- Configurar partition pruning
SET enable_partition_pruning = on; -- Padrão: on

-- Verificar se pruning está funcionando
EXPLAIN (ANALYZE, COSTS)
SELECT COUNT(*)
FROM logs_partitioned
WHERE created_at >= '2024-06-01';
-- Deve mostrar apenas logs_2024_06 sendo acessada
```

## List Partitioning

### Criação com LIST

```sql
-- Tabela particionada por lista de valores
CREATE TABLE sales_by_region (
    sale_id BIGSERIAL,
    region VARCHAR(20) NOT NULL,
    product_id INTEGER,
    amount DECIMAL(12,2),
    sale_date DATE,
    PRIMARY KEY (sale_id, region)
) PARTITION BY LIST (region);

-- Criar partição para cada região
CREATE TABLE sales_north PARTITION OF sales_by_region
    FOR VALUES IN ('north', 'northeast');

CREATE TABLE sales_south PARTITION OF sales_by_region
    FOR VALUES IN ('south', 'southeast');

CREATE TABLE sales_east PARTITION OF sales_by_region
    FOR VALUES IN ('east');

CREATE TABLE sales_west PARTITION OF sales_by_region
    FOR VALUES IN ('west', 'northwest');

CREATE TABLE sales_central PARTITION OF sales_by_region
    FOR VALUES IN ('central');

-- Partição default para valores não mapeados
CREATE TABLE sales_other PARTITION OF sales_by_region DEFAULT;

-- Inserir dados
INSERT INTO sales_by_region (region, product_id, amount, sale_date)
VALUES
    ('north', 1, 500.00, '2024-06-15'),
    ('southeast', 2, 750.00, '2024-06-16'),
    ('unknown_region', 3, 100.00, '2024-06-17');
-- unknown_region vai para sales_other

-- Query com partition pruning
EXPLAIN ANALYZE
SELECT SUM(amount)
FROM sales_by_region
WHERE region = 'north';
-- Seq Scan on sales_north
-- Apenas partição north é acessada
```

### List Partitioning Avançado

```sql
-- Particionamento por múltiplas colunas
CREATE TABLE audit_logs (
    log_id BIGSERIAL,
    service VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id, service, level)
) PARTITION BY LIST (service);

-- Partições por serviço
CREATE TABLE audit_auth PARTITION OF audit_logs
    FOR VALUES IN ('authentication', 'authorization');

CREATE TABLE audit_payments PARTITION OF audit_logs
    FOR VALUES IN ('payment', 'billing', 'invoice');

CREATE TABLE audit_inventory PARTITION OF audit_logs
    FOR VALUES IN ('inventory', 'warehouse', 'shipping');

CREATE TABLE audit_notifications PARTITION OF audit_logs
    FOR VALUES IN ('email', 'sms', 'push', 'webhook');

CREATE TABLE audit_other PARTITION OF audit_logs DEFAULT;

-- Sub-particionamento por nível de severidade (se suportado)
-- Ou criar índices específicos por partição
CREATE INDEX idx_audit_auth_level
ON audit_auth (level, created_at);

CREATE INDEX idx_audit_payments_level
ON audit_payments (level, created_at);

-- Query otimizada
EXPLAIN ANALYZE
SELECT *
FROM audit_logs
WHERE service = 'payment'
AND level = 'error'
AND created_at > NOW() - INTERVAL '24 hours';
-- Seq Scan on audit_payments
-- Apenas partição de pagamento é acessada
```

## Hash Partitioning

### Quando Usar Hash

Hash partitioning distribui dados uniformemente entre partições quando não existe uma chave natural para range ou list.

```sql
-- Tabela particionada por hash
CREATE TABLE sessions (
    session_id UUID DEFAULT gen_random_uuid(),
    user_id INTEGER,
    session_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    PRIMARY KEY (session_id)
) PARTITION BY HASH (session_id);

-- Criar 4 partições hash
CREATE TABLE sessions_p0 PARTITION OF sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE sessions_p1 PARTITION OF sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE sessions_p2 PARTITION OF sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE sessions_p3 PARTITION OF sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- Inserir dados: distribuído uniformemente
INSERT INTO sessions (user_id, session_data)
SELECT
    (random() * 100000)::INTEGER,
    jsonb_build_object('ip', '192.168.1.' || (random() * 255)::INTEGER)
FROM generate_series(1, 1000000);

-- Verificar distribuição
SELECT
    tableoid::regclass AS partition,
    COUNT(*)
FROM sessions
GROUP BY tableoid
ORDER BY tableoid;
-- Deve mostrar contagens aproximadamente iguais

-- Busca por session_id: acessa apenas 1 partição
EXPLAIN ANALYZE
SELECT * FROM sessions
WHERE session_id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';
-- Index Scan on sessions_p2
-- Hash calcula qual partição contém o registro
```

### Hash com Índices

```sql
-- Criar índices em cada partição
CREATE INDEX idx_sessions_p0_user
ON sessions_p0 (user_id);

CREATE INDEX idx_sessions_p1_user
ON sessions_p1 (user_id);

CREATE INDEX idx_sessions_p2_user
ON sessions_p2 (user_id);

CREATE INDEX idx_sessions_p3_user
ON sessions_p3 (user_id);

-- Ou criar na tabela pai (aplica a todas)
CREATE INDEX idx_sessions_user
ON sessions (user_id);

-- Query que usa o índice
EXPLAIN ANALYZE
SELECT * FROM sessions
WHERE user_id = 42
AND expires_at > CURRENT_TIMESTAMP;
-- Pode usar índice em todas as partições ou apenas uma (hash partitioning não suporta pruning eficiente para queries não baseadas na chave de partição)
```

## Sub-partitioning

### Hash + Range

```sql
-- Primeiro nível: hash por user_id
CREATE TABLE user_events (
    event_id BIGSERIAL,
    user_id INTEGER NOT NULL,
    event_type VARCHAR(50),
    payload JSONB,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (event_id, user_id, created_at)
) PARTITION BY HASH (user_id);

-- Criar partições hash
CREATE TABLE user_events_p0 PARTITION OF user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 0)
    PARTITION BY RANGE (created_at);

CREATE TABLE user_events_p1 PARTITION OF user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 1)
    PARTITION BY RANGE (created_at);

CREATE TABLE user_events_p2 PARTITION OF user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 2)
    PARTITION BY RANGE (created_at);

CREATE TABLE user_events_p3 PARTITION OF user_events
    FOR VALUES WITH (MODULUS 4, REMAINDER 3)
    PARTITION BY RANGE (created_at);

-- Criar sub-partições range para cada partição hash
CREATE TABLE user_events_p0_2024_01 PARTITION OF user_events_p0
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE user_events_p0_2024_02 PARTITION OF user_events_p0
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

CREATE TABLE user_events_p0_2024_03 PARTITION OF user_events_p0
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- ... criar sub-partições para cada mês em cada partição hash

-- Query que benefit de ambos os níveis
EXPLAIN ANALYZE
SELECT * FROM user_events
WHERE user_id = 42
AND created_at >= '2024-03-01'
AND created_at < '2024-04-01';
-- Hash calcula partição: p2
-- Range calcula sub-partição: p2_2024_03
-- Apenas 1 sub-partição é acessada
```

### List + Range

```sql
-- Tabela de transações financeiras
CREATE TABLE financial_transactions (
    tx_id BIGSERIAL,
    tx_type VARCHAR(20) NOT NULL,
    account_id INTEGER,
    amount DECIMAL(15,2),
    tx_date DATE NOT NULL,
    status VARCHAR(20),
    PRIMARY KEY (tx_id, tx_type, tx_date)
) PARTITION BY LIST (tx_type);

-- Partições por tipo de transação
CREATE TABLE tx_debits PARTITION OF financial_transactions
    FOR VALUES IN ('debit', 'withdrawal', 'transfer_out')
    PARTITION BY RANGE (tx_date);

CREATE TABLE tx_credits PARTITION OF financial_transactions
    FOR VALUES IN ('credit', 'deposit', 'transfer_in')
    PARTITION BY RANGE (tx_date);

CREATE TABLE tx_fees PARTITION OF financial_transactions
    FOR VALUES IN ('fee', 'interest', 'penalty')
    PARTITION BY RANGE (tx_date);

-- Sub-partições range
CREATE TABLE tx_debits_2024_q1 PARTITION OF tx_debits
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE tx_debits_2024_q2 PARTITION OF tx_debits
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE tx_credits_2024_q1 PARTITION OF tx_credits
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE tx_credits_2024_q2 PARTITION OF tx_credits
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE tx_fees_2024_q1 PARTITION OF tx_fees
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE tx_fees_2024_q2 PARTITION OF tx_fees
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- Query de relatório mensal
EXPLAIN ANALYZE
SELECT
    tx_type,
    SUM(amount) as total,
    COUNT(*) as count
FROM financial_transactions
WHERE tx_date >= '2024-01-01'
AND tx_date < '2024-04-01'
GROUP BY tx_type;
-- Acessa: tx_debits_2024_q1, tx_credits_2024_q1, tx_fees_2024_q1
-- 3 partições de ~100M cada em vez de 1 tabela de ~300M
```

## Partition Management

### ATTACH e DETACH

```sql
-- Criar tabela externa
CREATE TABLE logs_archive_2023 (
    log_id BIGSERIAL,
    user_id INTEGER,
    action VARCHAR(50),
    ip_address INET,
    created_at TIMESTAMP NOT NULL,
    details JSONB
);

-- Adicionar como partição (deve ter mesma estrutura)
ALTER TABLE logs_partitioned
ATTACH PARTITION logs_archive_2023
FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

-- Verificar anexo
SELECT
    parent.relname AS parent_table,
    child.relname AS partition
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'logs_partitioned';

-- Detach partição (PostgreSQL 12+: DETACH PARTITION ... FINALIZE)
ALTER TABLE logs_partitioned
DETACH PARTITION logs_2023_12;

-- Detach com CONCURRENTLY (PostgreSQL 14+: não bloqueia reads/writes)
ALTER TABLE logs_partitioned
DETACH PARTITION logs_2023_12 CONCURRENTLY;

-- Após detach, a tabela pode ser manipulada independentemente
-- Útil para arquivamento ou movimentação de dados
```

### Merge e Split

```sql
-- Merge: combinar duas partições em uma
-- Primeiro: detach ambas
ALTER TABLE logs_partitioned DETACH PARTITION logs_2024_01;
ALTER TABLE logs_partitioned DETACH PARTITION logs_2024_02;

-- Criar nova partição combinada
CREATE TABLE logs_2024_q1 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

-- Inserir dados das antigas na nova
INSERT INTO logs_2024_q1 SELECT * FROM logs_2024_01;
INSERT INTO logs_2024_q1 SELECT * FROM logs_2024_02;

-- Drop antigas
DROP TABLE logs_2024_01;
DROP TABLE logs_2024_02;

-- Split: dividir uma partição em duas
-- Primeiro: detach
ALTER TABLE logs_partitioned DETACH PARTITION logs_2024_q1;

-- Criar duas novas partições
CREATE TABLE logs_2024_01_02 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-03-01');

CREATE TABLE logs_2024_03 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- Inserir dados
INSERT INTO logs_2024_01_02
SELECT * FROM logs_2024_q1
WHERE created_at < '2024-03-01';

INSERT INTO logs_2024_03
SELECT * FROM logs_2024_q1
WHERE created_at >= '2024-03-01';

DROP TABLE logs_2024_q1;
```

### Reindexing Partições

```sql
-- Reindexar uma partição específica
REINDEX TABLE logs_2024_06;

-- Reindexar todas as partições
DO $$
DECLARE
    v_partition RECORD;
BEGIN
    FOR v_partition IN
        SELECT child.relname
        FROM pg_inherits
        JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE parent.relname = 'logs_partitioned'
    LOOP
        EXECUTE format('REINDEX TABLE CONCURRENTLY %I', v_partition.relname);
        RAISE NOTICE 'Reindexed: %', v_partition.relname;
    END LOOP;
END;
$$;
```

## Sharding Horizontal

### Conceito

Sharding horizontal distribui linhas de uma tabela entre múltiplos servidores (shards), onde cada shard contém um subconjunto dos dados.

```sql
-- Configuração de múltiplos servidores PostgreSQL
-- Shard 1: shard1.example.com:5432
-- Shard 2: shard2.example.com:5432
-- Shard 3: shard3.example.com:5432
-- Shard 4: shard4.example.com:5432

-- Cada shard contém a mesma estrutura de tabelas
-- Shard 1
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY, -- sem SERIAL, pois IDs vêm do coordinator
    name VARCHAR(100),
    email VARCHAR(255),
    shard_id INTEGER -- redundante para debug
);

-- Shard 2 (mesma estrutura)
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    shard_id INTEGER
);
```

### Distribuição por Hash

```sql
-- Função de sharding no coordinator
CREATE OR REPLACE FUNCTION get_shard_id(p_user_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
    -- Hash consistente: user_id % num_shards
    RETURN p_user_id % 4 + 1;
END;
$$ LANGUAGE plpgsql;

-- Mapeamento de shards
-- Shard 1: user_id % 4 = 0 (IDs: 4, 8, 12, 16, ...)
-- Shard 2: user_id % 4 = 1 (IDs: 1, 5, 9, 13, ...)
-- Shard 3: user_id % 4 = 2 (IDs: 2, 6, 10, 14, ...)
-- Shard 4: user_id % 4 = 3 (IDs: 3, 7, 11, 15, ...)

-- Exemplo de roteamento
SELECT get_shard_id(42);  -- Retorna 3 (shard 3)
SELECT get_shard_id(100); -- Retorna 1 (shard 1)
SELECT get_shard_id(7);   -- Retorna 4 (shard 4)
```

### Foreign Data Wrappers (FDW)

```sql
-- Configurar postgres_fdW para acessar shards remotas
CREATE EXTENSION postgres_fdw;

-- Criar servidor para cada shard
CREATE SERVER shard1_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'shard1.example.com', port '5432', dbname 'mydb');

CREATE SERVER shard2_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'shard2.example.com', port '5432', dbname 'mydb');

CREATE SERVER shard3_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'shard3.example.com', port '5432', dbname 'mydb');

CREATE SERVER shard4_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'shard4.example.com', port '5432', dbname 'mydb');

-- Criar mapeamento de usuários
CREATE USER MAPPING FOR app_user
    SERVER shard1_server
    OPTIONS (user 'app_user', password 'secure_password');

CREATE USER MAPPING FOR app_user
    SERVER shard2_server
    OPTIONS (user 'app_user', password 'secure_password');

-- Criar tabelas externas
CREATE FOREIGN TABLE users_shard1 (
    user_id INTEGER,
    name VARCHAR(100),
    email VARCHAR(255)
) SERVER shard1_server OPTIONS (table_name 'users');

CREATE FOREIGN TABLE users_shard2 (
    user_id INTEGER,
    name VARCHAR(100),
    email VARCHAR(255)
) SERVER shard2_server OPTIONS (table_name 'users');

CREATE FOREIGN TABLE users_shard3 (
    user_id INTEGER,
    name VARCHAR(100),
    email VARCHAR(255)
) SERVER shard3_server OPTIONS (table_name 'users');

CREATE FOREIGN TABLE users_shard4 (
    user_id INTEGER,
    name VARCHAR(100),
    email VARCHAR(255)
) SERVER shard4_server OPTIONS (table_name 'users');

-- Query que acessa todas as shards (scatter-gather)
SELECT * FROM users_shard1
UNION ALL
SELECT * FROM users_shard2
UNION ALL
SELECT * FROM users_shard3
UNION ALL
SELECT * FROM users_shard4;

-- Query específica por shard (pruning manual)
SELECT * FROM users_shard3
WHERE user_id = 42;
-- Apenas shard3 é acessada
```

### Query Router

```sql
-- Função de roteamento para queries
CREATE OR REPLACE FUNCTION shard_route_query(
    p_query TEXT,
    p_user_id INTEGER
) RETURNS TABLE(result JSONB) AS $$
DECLARE
    v_shard_id INTEGER;
    v_server_name TEXT;
BEGIN
    v_shard_id := get_shard_id(p_user_id);
    v_server_name := 'shard' || v_shard_id || '_server';

    -- Executar query no shard correto
    RETURN QUERY EXECUTE format(
        'SELECT row_to_json(t) FROM (%s) t',
        p_query
    ) USING v_server_name;
END;
$$ LANGUAGE plpgsql;

-- Exemplo de uso
SELECT * FROM shard_route_query(
    'SELECT * FROM users WHERE user_id = $1',
    42
);
-- Roteia automaticamente para shard3
```

## Sharding Vertical

### Conceito

Sharding vertical distribui colunas (não linhas) entre diferentes bancos de dados ou servidores.

```sql
-- Shard 1: Dados de perfil do usuário
CREATE TABLE user_profiles (
    user_id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP
);

-- Shard 2: Dados de conta financeira
CREATE TABLE user_accounts (
    user_id INTEGER PRIMARY KEY,
    balance DECIMAL(15,2),
    currency VARCHAR(3),
    credit_limit DECIMAL(15,2),
    updated_at TIMESTAMP
);

-- Shard 3: Dados de atividade
CREATE TABLE user_activities (
    user_id INTEGER PRIMARY KEY,
    last_login TIMESTAMP,
    login_count INTEGER,
    preferences JSONB,
    settings JSONB
);

-- Shard 4: Dados de sessão
CREATE TABLE user_sessions (
    user_id INTEGER,
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, session_id)
);
```

### Vantagens e Desvantagens

```sql
-- VANTAGENS:
-- 1. Cada shard pode ter configurações otimizadas para seu tipo de dado
-- 2. Backup e restore granulares
-- 3. Escala independente por tipo de dado
-- 4. Segregação de dados sensíveis

-- DESVANTAGENS:
-- 1. Queries que envolvem múltiplos shards requerem JOINs distribuídos
-- 2. Consistência transacional entre shards é complexa
-- 3. Manutenção de schema sincronizado em todos os shards

-- Exemplo de query que precisa de dados de múltiplos shards
-- (executada no coordinator)
WITH profile AS (
    SELECT * FROM dblink('shard1_server',
        'SELECT user_id, name, email FROM user_profiles WHERE user_id = 42')
    AS t(user_id INTEGER, name VARCHAR, email VARCHAR)
),
account AS (
    SELECT * FROM dblink('shard2_server',
        'SELECT user_id, balance FROM user_accounts WHERE user_id = 42')
    AS t(user_id INTEGER, balance DECIMAL)
)
SELECT p.name, p.email, a.balance
FROM profile p
JOIN account a ON p.user_id = a.user_id;
```

## Consistent Hashing

### Problema da Rehashing

```sql
-- Hash tradicional: user_id % num_shards
-- Se num_shards muda de 4 para 5:
-- Antes: user_id 42 → shard 2 (42 % 4 = 2)
-- Depois: user_id 42 → shard 2 (42 % 5 = 2)
-- Alguns IDs mudam de shard, causando migração massiva de dados

-- Consistent hashing resolve isso usando anel de hash
```

### Implementação com PostgreSQL

```sql
-- Tabela de mapeamento de consistent hashing
CREATE TABLE shard_ring (
    position INTEGER PRIMARY KEY,
    shard_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar anel com 256 posições distribuídas entre 4 shards
INSERT INTO shard_ring (position, shard_id)
SELECT
    i,
    (i / 64) + 1  -- 256 / 4 = 64 posições por shard
FROM generate_series(0, 255) AS i;

-- Função de consistent hashing
CREATE OR REPLACE FUNCTION consistent_hash(p_key TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_hash BIGINT;
    v_position INTEGER;
BEGIN
    -- Usar hash do PostgreSQL
    v_hash := hashtext(p_key);

    -- Mapear para posição no anel (0-255)
    v_position := (v_hash % 256)::INTEGER;

    -- Encontrar shard mais próximo no anel
    RETURN (
        SELECT shard_id
        FROM shard_ring
        WHERE position >= v_position
        ORDER BY position
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Exemplo de uso
SELECT consistent_hash('user_42');   -- Retorna shard_id
SELECT consistent_hash('user_100');  -- Retorna shard_id

-- Distribuição de dados no anel
SELECT
    shard_id,
    COUNT(*) as positions,
    ROUND(COUNT(*)::numeric / 256 * 100, 2) as percent
FROM shard_ring
GROUP BY shard_id
ORDER BY shard_id;
```

### Virtual Nodes (VNodes)

```sql
-- Adicionar virtual nodes para melhor distribuição
CREATE TABLE shard_ring_vnodes (
    vnode_id SERIAL PRIMARY KEY,
    position INTEGER NOT NULL,
    shard_id INTEGER NOT NULL,
    weight INTEGER DEFAULT 1
);

-- Criar 1024 virtual nodes distribuídos entre 4 shards
INSERT INTO shard_ring_vnodes (position, shard_id)
SELECT
    (hashtext('shard' || shard_id || '_vnode' || vnode_id) % 256)::INTEGER,
    shard_id
FROM generate_series(1, 4) AS shard_id,
     generate_series(1, 256) AS vnode_id;

-- Função de consistent hashing com virtual nodes
CREATE OR REPLACE FUNCTION consistent_hash_vnodes(p_key TEXT)
RETURNS INTEGER AS $$
DECLARE
    v_hash BIGINT;
    v_position INTEGER;
BEGIN
    v_hash := hashtext(p_key);
    v_position := (v_hash % 256)::INTEGER;

    RETURN (
        SELECT shard_id
        FROM shard_ring_vnodes
        WHERE position >= v_position
        ORDER BY position, vnode_id
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Verificar distribuição
SELECT
    shard_id,
    COUNT(DISTINCT vnode_id) as vnodes,
    ROUND(COUNT(DISTINCT vnode_id)::numeric / 1024 * 100, 2) as percent
FROM shard_ring_vnodes
GROUP BY shard_id
ORDER BY shard_id;
```

## Database Proxies

### PgBouncer

PgBouncer é um pooler de conexões leve para PostgreSQL.

```ini
# Configuração do PgBouncer
# pgbouncer.ini

[databases]
mydb = host=localhost port=5432 dbname=mydb
mydb_replica = host=replica.example.com port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pooling modes
pool_mode = transaction
# Modos disponíveis:
# session: conexão liberada apenas quando o cliente desconecta
# transaction: conexão liberada ao fim de cada transação
# statement: conexão liberada ao fim de cada statement (mais restritivo)

# Pool sizing
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 3
max_client_conn = 1000
max_db_connections = 100

# Timeouts
server_idle_timeout = 600
client_idle_timeout = 0
query_timeout = 120
query_wait_timeout = 120

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60

# Health check
server_check_delay = 30
server_check_query = SELECT 1
```

```sql
-- Conectar via PgBouncer
-- psql -h pgbouncer.example.com -p 6432 -U app_user mydb

-- Verificar estatísticas do pool
SHOW POOLS;
-- DATABASE | USER | CL | SV | SV_IDLE | CL_WAITING | CL_ACTIVE | SV_USED | SV_TESTED | SV_LOGIN | MAXWAIT | MAXWAIT_US

SHOW STATS;
-- Ver throughput e latência

SHOW CLIENTS;
-- Conexões de clientes ativas

SHOW SERVERS;
-- Conexões de servidores ativas

SHOW CONFIG;
-- Configuração atual

-- Reload config sem reconexões
RELOAD;

-- Pausar pool (para manutenção)
PAUSE mydb;

-- Resume pool
RESUME mydb;

-- Adicionar database dynamicamente
SET mydb = host=newserver.example.com port=5432 dbname=mydb;

-- Remover database
RESET mydb;
```

### ProxySQL

ProxySQL é um proxy de alto desempenho para MySQL.

```sql
-- Configuração do ProxySQL
-- Adicionar servidores MySQL
INSERT INTO mysql_servers (
    hostgroup_id, hostname, port, weight, max_connections, comment
) VALUES
    (10, 'primary.example.com', 3306, 1000, 200, 'Primary'),
    (20, 'replica1.example.com', 3306, 500, 100, 'Replica 1'),
    (20, 'replica2.example.com', 3306, 500, 100, 'Replica 2');

-- Configurar regras de roteamento
INSERT INTO mysql_query_rules (
    rule_id, active, match_pattern, destination_hostgroup, apply
) VALUES
    (1, 1, '^SELECT .* FOR UPDATE$', 10, 1),  -- Writes → primary
    (2, 1, '^SELECT', 20, 1),                   -- Reads → replicas
    (3, 1, '.*', 10, 1);                        -- Default → primary

-- Adicionar usuários
INSERT INTO mysql_users (username, password, default_hostgroup)
VALUES ('app_user', 'encrypted_password', 10);

-- Aplicar mudanças
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL QUERY RULES TO RUNTIME;
LOAD MYSQL USERS TO RUNTIME;

SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL QUERY RULES TO DISK;
SAVE MYSQL USERS TO DISK;

-- Monitoramento
SELECT * FROM mysql_servers;
SELECT * FROM mysql_query_rules;
SELECT * FROM stats_mysql_query_digest;
SELECT * FROM stats_mysql_connection_pool;
```

## Connection Pooling

### Pgpool-II

```ini
# Configuração do Pgpool-II
# pgpool.conf

# Configurações gerais
listen_addresses = '*'
port = 9999
socket_dir = '/var/run/pgpool'

# Pool de conexões
num_init_children = 32
child_life_time = 300
child_max_connections = 100
connection_life_time = 0
client_idle_limit = 0

# Backend servers
backend_hostname0 = 'primary.example.com'
backend_port0 = 5432
backend_weight0 = 1
backend_data_directory0 = '/var/lib/postgresql/data'
backend_flag0 = 'ALWAYS_PRIMARY'

backend_hostname1 = 'replica1.example.com'
backend_port1 = 5432
backend_weight1 = 1
backend_data_directory1 = '/var/lib/postgresql/data'

# Load balancing
load_balance_mode = on
read_only_traffic = on
statement_load_balance = on

# Replication
master_slave_mode = on
master_slave_sub_mode = 'stream'

# Health checking
health_check_period = 10
health_check_timeout = 20
health_check_user = 'pgpool'
health_check_password = 'password'

# Connection pooling
connection_cache = on
reset_query = 'DISCARD ALL'
reset_query_list = 'DISCARD ALL'

# Logging
log_connections = on
log_hostname = on
log_per_node_statement = on
```

### PgBouncer para Sharding

```ini
# Configuração multi-shard do PgBouncer
[databases]
# Shard 1
shard1 = host=shard1.example.com port=5432 dbname=mydb
shard1_replica = host=shard1-replica.example.com port=5432 dbname=mydb

# Shard 2
shard2 = host=shard2.example.com port=5432 dbname=mydb
shard2_replica = host=shard2-replica.example.com port=5432 dbname=mydb

# Shard 3
shard3 = host=shard3.example.com port=5432 dbname=mydb
shard3_replica = host=shard3-replica.example.com port=5432 dbname=mydb

# Shard 4
shard4 = host=shard4.example.com port=5432 dbname=mydb
shard4_replica = host=shard4-replica.example.com port=5432 dbname=mydb

# Wildcard para shards
shard* = host=shard*.example.com port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
pool_mode = transaction
default_pool_size = 25
max_client_conn = 2000

# Rotas por usuário
# app_user → shard específico via query routing
# admin_user → todos os shards
```

### Connection Pooling Patterns

```sql
-- Padrão 1: Pool per service
-- Auth service pool
-- Payment service pool
-- Notification service pool

-- Padrão 2: Pool per query type
-- Read pool (replicas)
-- Write pool (primary)
-- Analytics pool (read replicas com resources dedicados)

-- Padrão 3: Pool per tenant (multi-tenant)
-- Tenant A pool
-- Tenant B pool
-- Tenant C pool

-- Configuração no PgBouncer para multi-tenant
-- [databases]
-- tenant_a = host=tenant-a.example.com port=5432 dbname=tenant_a
-- tenant_b = host=tenant-b.example.com port=5432 dbname=tenant_b

-- Monitoramento de pools
SHOW POOLS;
-- DATABASE | USER | CL_ACTIVE | CL_WAITING | SV_ACTIVE | SV_IDLE | ...

-- Alertas para pool exhaustion
-- CL_WAITING > threshold → adicionar mais conexões
-- SV_IDLE > threshold → reduzir pool size
-- CL_ACTIVE > threshold → escalar horizontalmente
```

## Read Replicas

### Configuração de Replicação

```sql
-- Primary server config (postgresql.conf)
-- wal_level = replica
-- max_wal_senders = 10
-- synchronous_standby_names = ''  (async) ou 'replica1' (sync)

-- Criar usuário de replicação
CREATE USER replicator WITH REPLICATION LOGIN ENCRYPTED PASSWORD 'secure_password';

-- Configurar pg_hba.conf
-- host replication replicator replica1.example.com/32 md5

-- Replica server: criar backup do primary
-- pg_basebackup -h primary.example.com -D /var/lib/postgresql/data -U replicator -P

-- Criar standby.signal (PostgreSQL 12+)
-- touch /var/lib/postgresql/data/standby.signal

-- Configurar primary_conninfo (PostgreSQL 12+)
-- postgresql.auto.conf:
-- primary_conninfo = 'host=primary.example.com port=5432 user=replicator password=secure_password'
```

### Monitoramento de Replicação

```sql
-- No primary: verificar status de replicação
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS replication_lag_bytes,
    pg_size_pretty(pg_wal_lsn_diff(sent_lsn, replay_lsn)) AS replication_lag
FROM pg_stat_replication;

-- No replica: verificar status
SELECT
    status,
    received_lsn,
    latest_end_lsn,
    latest_end_time,
    conninfo
FROM pg_stat_wal_receiver;

-- Configurar lag monitoring
CREATE OR REPLACE FUNCTION check_replication_lag()
RETURNS TABLE(
    replica_ip INET,
    lag_bytes BIGINT,
    lag_pretty TEXT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.client_addr,
        pg_wal_lsn_diff(r.sent_lsn, r.replay_lsn),
        pg_size_pretty(pg_wal_lsn_diff(r.sent_lsn, r.replay_lsn)),
        CASE
            WHEN pg_wal_lsn_diff(r.sent_lsn, r.replay_lsn) > 104857600  -- 100MB
                THEN 'CRITICAL'
            WHEN pg_wal_lsn_diff(r.sent_lsn, r.replay_lsn) > 10485760   -- 10MB
                THEN 'WARNING'
            ELSE 'OK'
        END
    FROM pg_stat_replication r;
END;
$$ LANGUAGE plpgsql;

-- Executar verificação
SELECT * FROM check_replication_lag();
```

### Roteamento de Leitura

```sql
-- Função para rotear leituras para replica
CREATE OR REPLACE FUNCTION read_from_replica()
RETURNS TRIGGER AS $$
BEGIN
    -- Verificar se há replicas disponíveis
    IF (SELECT COUNT(*) FROM pg_stat_replication) > 0 THEN
        -- Conectar via dblink para replica
        -- Na prática, usar PgBouncer ou application-level routing
        RAISE NOTICE 'Read would be routed to replica';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Configuração no PgBouncer
-- [databases]
-- mydb = host=primary.example.com port=5432 dbname=mydb
-- mydb_ro = host=replica.example.com port=5432 dbname=mydb

-- Application routing
-- Para queries SELECT → mydb_ro
-- Para queries INSERT/UPDATE/DELETE → mydb
```

## Exemplo Prático: Partitioning de Tabela de Logs

### Schema Completo

```sql
-- Schema completo de logs particionados
CREATE TABLE application_logs (
    log_id BIGSERIAL,
    service VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL,
    message TEXT,
    stack_trace TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

-- Criar partições mensais para 2024
DO $$
DECLARE
    v_start DATE;
    v_end DATE;
    v_month TEXT;
BEGIN
    FOR i IN 0..11 LOOP
        v_start := DATE_TRUNC('month', DATE '2024-01-01' + (i || ' months')::INTERVAL);
        v_end := v_start + INTERVAL '1 month';
        v_month := TO_CHAR(v_start, 'YYYY_MM');

        EXECUTE format(
            'CREATE TABLE logs_%s PARTITION OF application_logs
             FOR VALUES FROM (%L) TO (%L)',
            v_month, v_start, v_end
        );

        -- Criar índices específicos para cada partição
        EXECUTE format(
            'CREATE INDEX idx_logs_%s_service_level
             ON logs_%s (service, level, created_at)',
            v_month, v_month
        );

        EXECUTE format(
            'CREATE INDEX idx_logs_%s_metadata
             ON logs_%s USING gin (metadata jsonb_path_ops)',
            v_month, v_month
        );

        RAISE NOTICE 'Created partition: logs_%', v_month;
    END LOOP;
END;
$$;

-- Configurar autovacuum otimizado para partições de log
ALTER TABLE application_logs SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_delay = 0,
    autovacuum_vacuum_cost_limit = 1000,
    toast_tuple_target = 128
);

-- Função para criar partições futuras automaticamente
CREATE OR REPLACE FUNCTION maintain_log_partitions(
    p_months_ahead INTEGER DEFAULT 3
) RETURNS void AS $$
DECLARE
    v_start DATE;
    v_end DATE;
    v_month TEXT;
BEGIN
    FOR i IN 0..p_months_ahead - 1 LOOP
        v_start := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        v_end := v_start + INTERVAL '1 month';
        v_month := TO_CHAR(v_start, 'YYYY_MM');

        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = 'logs_' || v_month
        ) THEN
            EXECUTE format(
                'CREATE TABLE logs_%s PARTITION OF application_logs
                 FOR VALUES FROM (%L) TO (%L)',
                v_month, v_start, v_end
            );

            EXECUTE format(
                'CREATE INDEX idx_logs_%s_service_level
                 ON logs_%s (service, level, created_at)',
                v_month, v_month
            );

            EXECUTE format(
                'CREATE INDEX idx_logs_%s_metadata
                 ON logs_%s USING gin (metadata jsonb_path_ops)',
                v_month, v_month
            );

            RAISE NOTICE 'Created partition: logs_%', v_month;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Função para arquivar partições antigas
CREATE OR REPLACE FUNCTION archive_old_logs(
    p_retention_months INTEGER DEFAULT 12
) RETURNS void AS $$
DECLARE
    v_cutoff DATE;
    v_partition RECORD;
BEGIN
    v_cutoff := DATE_TRUNC('month', CURRENT_DATE - (p_retention_months || ' months')::INTERVAL);

    FOR v_partition IN
        SELECT child.relname
        FROM pg_inherits
        JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE parent.relname = 'application_logs'
        AND child.relname < 'logs_' || TO_CHAR(v_cutoff, 'YYYY_MM')
    LOOP
        -- Detach partição
        EXECUTE format(
            'ALTER TABLE application_logs DETACH PARTITION %I',
            v_partition.relname
        );

        -- Mover para tabela de arquivo ou dropar
        EXECUTE format(
            'DROP TABLE %I',
            v_partition.relname
        );

        RAISE NOTICE 'Archived partition: %', v_partition.relname;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

### Inserção de Logs

```sql
-- Função para inserir log com batching
CREATE OR REPLACE FUNCTION insert_log(
    p_service VARCHAR,
    p_level VARCHAR,
    p_message TEXT,
    p_metadata JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO application_logs (service, level, message, metadata)
    VALUES (p_service, p_level, p_message, p_metadata)
    RETURNING log_id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Função para inserção em lote
CREATE OR REPLACE FUNCTION insert_logs_batch(
    p_logs JSONB
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_log JSONB;
BEGIN
    FOR v_log IN SELECT * FROM jsonb_array_elements(p_logs)
    LOOP
        INSERT INTO application_logs (service, level, message, metadata)
        VALUES (
            v_log ->> 'service',
            v_log ->> 'level',
            v_log ->> 'message',
            v_log -> 'metadata'
        );
        v_count := v_count + 1;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Exemplo de uso
SELECT insert_log(
    'auth-service',
    'INFO',
    'User login successful',
    jsonb_build_object('user_id', 42, 'ip', '192.168.1.1')
);
```

### Queries de Relatório

```sql
-- Relatório de erros por serviço (últimos 30 dias)
SELECT
    service,
    level,
    COUNT(*) as count,
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
FROM application_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
AND level IN ('ERROR', 'FATAL', 'CRITICAL')
GROUP BY service, level
ORDER BY count DESC;

-- Top 10 serviços com mais erros
SELECT
    service,
    COUNT(*) as error_count,
    pg_size_pretty(
        pg_total_relation_size(
            (SELECT child.relname
             FROM pg_inherits
             JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
             JOIN pg_class child ON pg_inherits.inhrelid = child.oid
             WHERE parent.relname = 'application_logs'
             AND child.relname LIKE 'logs_%'
             LIMIT 1)::regclass
        )
    ) as estimated_size
FROM application_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
AND level = 'ERROR'
GROUP BY service
ORDER BY error_count DESC
LIMIT 10;

-- Timeline de erros
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as error_count
FROM application_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '24 hours'
AND level = 'ERROR'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour;

-- Análise de padrões de erro
SELECT
    service,
    message,
    COUNT(*) as occurrences,
    array_agg(DISTINCT metadata ->> 'user_id') as affected_users
FROM application_logs
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
AND level = 'ERROR'
GROUP BY service, message
HAVING COUNT(*) > 10
ORDER BY occurrences DESC;
```

## Exemplo Prático: Sharding de E-commerce

### Arquitetura Completa

```sql
-- Schema de cada shard
-- Cada shard contém:
-- - customers (subset)
-- - orders (subset)
-- - order_items (subset)
-- - products (réplica completa em todos os shards)

-- Shard 1: customers 1-250000
-- Shard 2: customers 250001-500000
-- Shard 3: customers 500001-750000
-- Shard 4: customers 750001-1000000

-- Schema (mesmo em todos os shards)
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    address JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INTEGER DEFAULT 0,
    category_id INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    status VARCHAR(20) DEFAULT 'pending',
    total DECIMAL(12,2) NOT NULL,
    shipping_address JSONB,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Índices (mesmos em todos os shards)
CREATE INDEX idx_orders_customer ON orders (customer_id, created_at);
CREATE INDEX idx_orders_status ON orders (status, created_at);
CREATE INDEX idx_order_items_order ON order_items (order_id);
CREATE INDEX idx_order_items_product ON order_items (product_id);
CREATE INDEX idx_products_category ON products (category_id, price);
```

### Coordinator Layer

```sql
-- Coordinator: tabela de shard mapping
CREATE TABLE shard_mapping (
    shard_id INTEGER PRIMARY KEY,
    shard_name VARCHAR(50),
    host VARCHAR(100),
    port INTEGER DEFAULT 5432,
    min_customer_id INTEGER,
    max_customer_id INTEGER,
    is_active BOOLEAN DEFAULT true
);

INSERT INTO shard_mapping (shard_id, shard_name, host, port, min_customer_id, max_customer_id) VALUES
    (1, 'shard-1', 'shard1.example.com', 5432, 1, 250000),
    (2, 'shard-2', 'shard2.example.com', 5432, 250001, 500000),
    (3, 'shard-3', 'shard3.example.com', 5432, 500001, 750000),
    (4, 'shard-4', 'shard4.example.com', 5432, 750001, 1000000);

-- Função de roteamento
CREATE OR REPLACE FUNCTION get_shard_for_customer(p_customer_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT shard_id
        FROM shard_mapping
        WHERE p_customer_id BETWEEN min_customer_id AND max_customer_id
        AND is_active = true
    );
END;
$$ LANGUAGE plpgsql;

-- Função de roteamento por hash (para distribuição uniforme)
CREATE OR REPLACE FUNCTION get_shard_by_hash(p_customer_id INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN (p_customer_id % 4) + 1;
END;
$$ LANGUAGE plpgsql;

-- Função para executar query em shard específico
CREATE OR REPLACE FUNCTION exec_on_shard(
    p_shard_id INTEGER,
    p_query TEXT
) RETURNS SETOF RECORD AS $$
DECLARE
    v_shard shard_mapping%ROWTYPE;
BEGIN
    SELECT * INTO v_shard FROM shard_mapping WHERE shard_id = p_shard_id;

    RETURN QUERY EXECUTE format(
        'SELECT * FROM dblink(''host=%s port=%s dbname=mydb user=app_user password=secure_password'', %L) AS t(jsonb)',
        v_shard.host, v_shard.port, p_query
    );
END;
$$ LANGUAGE plpgsql;
```

### Queries Distribuídas

```sql
-- Query em shard específico (customer_id known)
CREATE OR REPLACE FUNCTION get_customer_orders(
    p_customer_id INTEGER
) RETURNS TABLE(order_data JSONB) AS $$
DECLARE
    v_shard_id INTEGER;
BEGIN
    v_shard_id := get_shard_for_customer(p_customer_id);

    RETURN QUERY
    SELECT * FROM dblink(
        format('host=%s port=%s dbname=mydb', 
               (SELECT host FROM shard_mapping WHERE shard_id = v_shard_id),
               (SELECT port FROM shard_mapping WHERE shard_id = v_shard_id)),
        format('SELECT row_to_json(t) FROM orders t WHERE customer_id = %s', p_customer_id)
    ) AS t(jsonb);
END;
$$ LANGUAGE plpgsql;

-- Query em todos os shards (scatter-gather)
CREATE OR REPLACE FUNCTION get_all_orders_by_status(
    p_status VARCHAR
) RETURNS TABLE(order_data JSONB) AS $$
DECLARE
    v_shard RECORD;
BEGIN
    FOR v_shard IN SELECT * FROM shard_mapping WHERE is_active = true
    LOOP
        RETURN QUERY
        SELECT * FROM dblink(
            format('host=%s port=%s dbname=mydb', v_shard.host, v_shard.port),
            format('SELECT row_to_json(t) FROM orders t WHERE status = %L', p_status)
        ) AS t(jsonb);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Agregação distribuída
CREATE OR REPLACE FUNCTION get_total_sales_by_shard()
RETURNS TABLE(shard_id INTEGER, total_sales DECIMAL) AS $$
DECLARE
    v_shard RECORD;
    v_result JSONB;
BEGIN
    FOR v_shard IN SELECT * FROM shard_mapping WHERE is_active = true
    LOOP
        SELECT row_to_json(t) INTO v_result
        FROM dblink(
            format('host=%s port=%s dbname=mydb', v_shard.host, v_shard.port),
            'SELECT COALESCE(SUM(total), 0) as total_sales FROM orders'
        ) AS t(total_sales DECIMAL);

        shard_id := v_shard.shard_id;
        total_sales := (v_result ->> 'total_sales')::DECIMAL;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

### Migração de Dados

```sql
-- Função para migrar customer entre shards
CREATE OR REPLACE FUNCTION migrate_customer(
    p_customer_id INTEGER,
    p_target_shard_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_source_shard INTEGER;
    v_target_shard RECORD;
    v_customer JSONB;
BEGIN
    -- Determinar shard atual
    v_source_shard := get_shard_for_customer(p_customer_id);

    IF v_source_shard = p_target_shard_id THEN
        RAISE EXCEPTION 'Customer already on target shard';
    END IF;

    -- Buscar dados do customer no shard origem
    SELECT row_to_json(c) INTO v_customer
    FROM dblink(
        format('host=%s port=%s dbname=mydb',
               (SELECT host FROM shard_mapping WHERE shard_id = v_source_shard),
               (SELECT port FROM shard_mapping WHERE shard_id = v_source_shard)),
        format('SELECT * FROM customers WHERE customer_id = %s', p_customer_id)
    ) AS c(jsonb);

    -- Inserir no shard destino
    INSERT INTO dblink(
        format('host=%s port=%s dbname=mydb',
               (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard_id),
               (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard_id)),
        format('INSERT INTO customers VALUES (%s)',
               (v_customer -> 'jsonb')::TEXT)
    );

    -- Migrar pedidos
    INSERT INTO dblink(
        format('host=%s port=%s dbname=mydb',
               (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard_id),
               (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard_id)),
        format('INSERT INTO orders SELECT * FROM orders WHERE customer_id = %s',
               p_customer_id)
    );

    -- Remover do shard origem
    PERFORM dblink_exec(
        format('host=%s port=%s dbname=mydb',
               (SELECT host FROM shard_mapping WHERE shard_id = v_source_shard),
               (SELECT port FROM shard_mapping WHERE shard_id = v_source_shard)),
        format('DELETE FROM orders WHERE customer_id = %s', p_customer_id)
    );

    PERFORM dblink_exec(
        format('host=%s port=%s dbname=mydb',
               (SELECT host FROM shard_mapping WHERE shard_id = v_source_shard),
               (SELECT port FROM shard_mapping WHERE shard_id = v_source_shard)),
        format('DELETE FROM customers WHERE customer_id = %s', p_customer_id)
    );

    RAISE NOTICE 'Customer % migrated from shard % to shard %',
        p_customer_id, v_source_shard, p_target_shard_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

### Monitoramento de Shards

```sql
-- View de status de todos os shards
CREATE OR REPLACE VIEW shard_status AS
SELECT
    sm.shard_id,
    sm.shard_name,
    sm.host,
    sm.min_customer_id,
    sm.max_customer_id,
    sm.is_active,
    (sm.max_customer_id - sm.min_customer_id + 1) as customer_capacity
FROM shard_mapping sm
ORDER BY sm.shard_id;

-- View de distribuição de dados
CREATE OR REPLACE VIEW shard_distribution AS
SELECT
    sm.shard_id,
    sm.shard_name,
    (SELECT COUNT(*) FROM dblink(
        format('host=%s port=%s dbname=mydb', sm.host, sm.port),
        'SELECT 1 FROM customers'
    ) AS t(x)) as customer_count,
    (SELECT COUNT(*) FROM dblink(
        format('host=%s port=%s dbname=mydb', sm.host, sm.port),
        'SELECT 1 FROM orders'
    ) AS t(x)) as order_count,
    (SELECT COALESCE(SUM(total), 0) FROM dblink(
        format('host=%s port=%s dbname=mydb', sm.host, sm.port),
        'SELECT total FROM orders'
    ) AS t(total DECIMAL)) as total_revenue
FROM shard_mapping sm
WHERE sm.is_active = true
ORDER BY sm.shard_id;

-- Alertas de balanceamento
DO $$
DECLARE
    v_avg NUMERIC;
    v_shard RECORD;
BEGIN
    SELECT AVG(customer_count) INTO v_avg FROM shard_distribution;

    FOR v_shard IN SELECT * FROM shard_distribution
    LOOP
        IF v_shard.customer_count > v_avg * 1.2 THEN
            RAISE WARNING 'Shard % has % customers (avg: %) - consider rebalancing',
                v_shard.shard_name, v_shard.customer_count, v_avg;
        END IF;
    END LOOP;
END;
$$;

-- Função para rebalancear shards
CREATE OR REPLACE FUNCTION rebalance_shards() RETURNS void AS $$
DECLARE
    v_avg NUMERIC;
    v_source RECORD;
    v_target RECORD;
    v_customers_to_move INTEGER;
BEGIN
    SELECT AVG(customer_count) INTO v_avg FROM shard_distribution;

    -- Encontrar shard com mais clientes que a média
    FOR v_source IN
        SELECT * FROM shard_distribution
        WHERE customer_count > v_avg * 1.2
    LOOP
        -- Encontrar shard com menos clientes que a média
        FOR v_target IN
            SELECT * FROM shard_distribution
            WHERE customer_count < v_avg * 0.8
        LOOP
            v_customers_to_move := (v_source.customer_count - v_avg) / 2;

            RAISE NOTICE 'Moving % customers from % to %',
                v_customers_to_move, v_source.shard_name, v_target.shard_name;

            -- Migrar clientes do shard fonte para shard destino
            -- (implementação depende da estratégia de roteamento)
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## Partitioning Performance Analysis

### Monitoramento de Partições

```sql
-- View detalhada de partições
CREATE OR REPLACE VIEW partition_info AS
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_size_pretty(pg_total_relation_size(child.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(child.oid)) AS table_size,
    pg_size_pretty(pg_indexes_size(child.oid)) AS index_size,
    pg_stat_get_live_tuples(child.oid) AS live_tuples,
    pg_stat_get_dead_tuples(child.oid) AS dead_tuples,
    CASE
        WHEN pg_stat_get_live_tuples(child.oid) > 0
        THEN ROUND(pg_stat_get_dead_tuples(child.oid)::numeric /
                    pg_stat_get_live_tuples(child.oid) * 100, 2)
        ELSE 0
    END AS dead_percent,
    pg_stat_get_last_autoanalyze_time(child.oid) AS last_autoanalyze
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'application_logs'
ORDER BY child.relname;

-- Estatísticas de acesso por partição
CREATE OR REPLACE VIEW partition_access_stats AS
SELECT
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname LIKE 'logs_%'
ORDER BY relname;

-- Alertas de partições com problemas
DO $$
DECLARE
    v_partition RECORD;
BEGIN
    FOR v_partition IN
        SELECT * FROM partition_info
        WHERE dead_percent > 20
        OR live_tuples < 1000
    LOOP
        IF v_partition.dead_percent > 20 THEN
            RAISE WARNING 'Partition % has % dead tuples (% percent)',
                v_partition.partition_name,
                v_partition.dead_tuples,
                v_partition.dead_percent;
        END IF;

        IF v_partition.live_tuples < 1000 THEN
            RAISE NOTICE 'Partition % has only % live tuples - consider merging',
                v_partition.partition_name,
                v_partition.live_tuples;
        END IF;
    END LOOP;
END;
$$;
```

### Partition Pruning Analysis

```sql
-- Verificar se partition pruning está funcionando
EXPLAIN (ANALYZE, COSTS)
SELECT COUNT(*)
FROM application_logs
WHERE created_at >= '2024-06-01'
AND created_at < '2024-07-01';
-- Deve mostrar apenas logs_2024_06 sendo acessada

-- Analisar eficiência do pruning
CREATE OR REPLACE FUNCTION analyze_partition_pruning()
RETURNS TABLE(
    query_text TEXT,
    partitions_accessed TEXT[],
    total_partitions INTEGER,
    pruning_ratio NUMERIC
) AS $$
DECLARE
    v_total_partitions INTEGER;
    v_partitions_accessed TEXT[];
BEGIN
    -- Contar total de partições
    SELECT COUNT(*) INTO v_total_partitions
    FROM pg_inherits
    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
    JOIN pg_class child ON pg_inherits.inhrelid = child.oid
    WHERE parent.relname = 'application_logs';

    -- Analisar queries recentes
    RETURN QUERY
    SELECT
        query,
        array_agg(DISTINCT relname),
        v_total_partitions,
        ROUND(array_length(array_agg(DISTINCT relname), 1)::numeric /
              v_total_partitions * 100, 2)
    FROM pg_stat_activity a
    JOIN pg_locks l ON a.pid = l.pid
    JOIN pg_class c ON l.relation = c.oid
    WHERE a.query LIKE '%application_logs%'
    AND c.relname LIKE 'logs_%'
    GROUP BY a.query;
END;
$$ LANGUAGE plpgsql;
```

## Sharding Management

### Shard Health Monitoring

```sql
-- View de saúde dos shards
CREATE OR REPLACE VIEW shard_health AS
SELECT
    sm.shard_id,
    sm.shard_name,
    sm.host,
    sm.is_active,
    (SELECT COUNT(*) FROM pg_stat_replication
     WHERE client_addr = sm.host::INET) as replication_slots,
    CASE
        WHEN (SELECT COUNT(*) FROM pg_stat_replication
              WHERE client_addr = sm.host::INET) > 0
        THEN 'healthy'
        ELSE 'no_replication'
    END as replication_status
FROM shard_mapping sm;

-- Função para verificar conectividade dos shards
CREATE OR REPLACE FUNCTION check_shard_connectivity()
RETURNS TABLE(
    shard_id INTEGER,
    shard_name VARCHAR,
    host VARCHAR,
    is_reachable BOOLEAN,
    response_time INTERVAL
) AS $$
DECLARE
    v_shard RECORD;
    v_start TIMESTAMP;
BEGIN
    FOR v_shard IN SELECT * FROM shard_mapping WHERE is_active = true
    LOOP
        v_start := clock_timestamp();

        BEGIN
            -- Tentar conectar ao shard
            PERFORM dblink_connect(
                format('host=%s port=%s dbname=mydb user=app_user password=secure_password',
                       v_shard.host, v_shard.port)
            );
            PERFORM dblink_disconnect();

            shard_id := v_shard.shard_id;
            shard_name := v_shard.shard_name;
            host := v_shard.host;
            is_reachable := true;
            response_time := clock_timestamp() - v_start;
            RETURN NEXT;

        EXCEPTION
            WHEN OTHERS THEN
                shard_id := v_shard.shard_id;
                shard_name := v_shard.shard_name;
                host := v_shard.host;
                is_reachable := false;
                response_time := clock_timestamp() - v_start;
                RETURN NEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Executar verificação
SELECT * FROM check_shard_connectivity();
```

### Shard Balancing

```sql
-- Função para balancear shards baseado em carga
CREATE OR REPLACE FUNCTION rebalance_shards_by_load()
RETURNS void AS $$
DECLARE
    v_avg_load NUMERIC;
    v_source RECORD;
    v_target RECORD;
    v_customers_to_move INTEGER;
BEGIN
    -- Calcular média de clientes por shard
    SELECT AVG(customer_count) INTO v_avg_load
    FROM shard_distribution;

    -- Encontrar shards desbalanceados
    FOR v_source IN
        SELECT * FROM shard_distribution
        WHERE customer_count > v_avg_load * 1.2
    LOOP
        FOR v_target IN
            SELECT * FROM shard_distribution
            WHERE customer_count < v_avg_load * 0.8
        LOOP
            -- Calcular quantos clientes mover
            v_customers_to_move := (v_source.customer_count - v_avg_load) / 2;

            IF v_customers_to_move > 0 THEN
                RAISE NOTICE 'Rebalancing: moving % customers from % to %',
                    v_customers_to_move, v_source.shard_name, v_target.shard_name;

                -- Mover clientes usando consistent hashing
                -- (implementação específica do domínio)
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Função para detectar hotspots
CREATE OR REPLACE FUNCTION detect_hotspots()
RETURNS TABLE(
    shard_id INTEGER,
    shard_name VARCHAR,
    customer_count BIGINT,
    order_count BIGINT,
    avg_orders_per_customer NUMERIC,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sd.shard_id,
        sd.shard_name,
        sd.customer_count,
        sd.order_count,
        CASE
            WHEN sd.customer_count > 0
            THEN ROUND(sd.order_count::numeric / sd.customer_count, 2)
            ELSE 0
        END,
        CASE
            WHEN sd.order_count::numeric / NULLIF(sd.customer_count, 0) > 10
            THEN 'hotspot'
            WHEN sd.customer_count > (SELECT AVG(customer_count) * 1.5 FROM shard_distribution)
            THEN 'overloaded'
            ELSE 'normal'
        END
    FROM shard_distribution sd
    ORDER BY sd.order_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Executar detecção de hotspots
SELECT * FROM detect_hotspots();
```

## Advanced Partitioning Patterns

### Multi-Tenant Partitioning

```sql
-- Tabela multi-tenant particionada por tenant
CREATE TABLE tenant_data (
    tenant_id INTEGER NOT NULL,
    data_id BIGSERIAL,
    data_type VARCHAR(50),
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, data_id)
) PARTITION BY LIST (tenant_id);

-- Criar partição para cada tenant
CREATE TABLE tenant_data_1 PARTITION OF tenant_data
    FOR VALUES IN (1);

CREATE TABLE tenant_data_2 PARTITION OF tenant_data
    FOR VALUES IN (2);

CREATE TABLE tenant_data_3 PARTITION OF tenant_data
    FOR VALUES IN (3);

-- Partição default para tenants novos
CREATE TABLE tenant_data_default PARTITION OF tenant_data DEFAULT;

-- Função para criar partição de novo tenant
CREATE OR REPLACE FUNCTION create_tenant_partition(
    p_tenant_id INTEGER
) RETURNS void AS $$
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS tenant_data_%s PARTITION OF tenant_data
         FOR VALUES IN (%s)',
        p_tenant_id, p_tenant_id
    );

    -- Criar índices específicos do tenant se necessário
    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_tenant_%s_data_type
         ON tenant_data_%s (data_type, created_at)',
        p_tenant_id, p_tenant_id
    );

    RAISE NOTICE 'Created partition for tenant %', p_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- Roteamento por tenant
CREATE OR REPLACE FUNCTION get_tenant_data(
    p_tenant_id INTEGER
) RETURNS TABLE(data JSONB) AS $$
BEGIN
    RETURN QUERY EXECUTE format(
        'SELECT row_to_json(t) FROM tenant_data_%s t',
        p_tenant_id
    );
END;
$$ LANGUAGE plpgsql;
```

### Time-Series Partitioning

```sql
-- Tabela de séries temporais com partitioning automático
CREATE TABLE metrics (
    metric_id BIGSERIAL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION,
    tags JSONB,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (metric_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Criar partições horárias para dados recentes
CREATE TABLE metrics_hourly_2024_06_28_10 PARTITION OF metrics
    FOR VALUES FROM ('2024-06-28 10:00:00') TO ('2024-06-28 11:00:00');

CREATE TABLE metrics_hourly_2024_06_28_11 PARTITION OF metrics
    FOR VALUES FROM ('2024-06-28 11:00:00') TO ('2024-06-28 12:00:00');

-- Função para criar partições horárias automaticamente
CREATE OR REPLACE FUNCTION create_hourly_partitions(
    p_hours_ahead INTEGER DEFAULT 24
) RETURNS void AS $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_partition_name TEXT;
BEGIN
    FOR i IN 0..p_hours_ahead - 1 LOOP
        v_start := DATE_TRUNC('hour', CURRENT_TIMESTAMP + (i || ' hours')::INTERVAL);
        v_end := v_start + INTERVAL '1 hour';
        v_partition_name := 'metrics_hourly_' || TO_CHAR(v_start, 'YYYY_MM_DD_HH');

        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = v_partition_name
        ) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF metrics
                 FOR VALUES FROM (%L) TO (%L)',
                v_partition_name, v_start, v_end
            );

            -- Índices otimizados para séries temporais
            EXECUTE format(
                'CREATE INDEX idx_%s_name_time ON %I (metric_name, timestamp DESC)',
                v_partition_name, v_partition_name
            );

            EXECUTE format(
                'CREATE INDEX idx_%s_tags ON %I USING gin (tags jsonb_path_ops)',
                v_partition_name, v_partition_name
            );

            RAISE NOTICE 'Created hourly partition: %', v_partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Função para arquivar partições antigas
CREATE OR REPLACE FUNCTION archive_old_metrics(
    p_retention_hours INTEGER DEFAULT 168  -- 7 dias
) RETURNS INTEGER AS $$
DECLARE
    v_cutoff TIMESTAMP;
    v_partition RECORD;
    v_count INTEGER := 0;
BEGIN
    v_cutoff := CURRENT_TIMESTAMP - (p_retention_hours || ' hours')::INTERVAL;

    FOR v_partition IN
        SELECT child.relname
        FROM pg_inherits
        JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE parent.relname = 'metrics'
        AND child.relname < 'metrics_hourly_' || TO_CHAR(v_cutoff, 'YYYY_MM_DD_HH')
    LOOP
        -- Detach e dropar partição antiga
        EXECUTE format('ALTER TABLE metrics DETACH PARTITION %I', v_partition.relname);
        EXECUTE format('DROP TABLE %I', v_partition.relname);

        v_count := v_count + 1;
        RAISE NOTICE 'Archived partition: %', v_partition.relname;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
```

## Connection Pooling Patterns

### PgBouncer Advanced Configuration

```ini
# Configuração avançada do PgBouncer para produção
[databases]
# Primary database
mydb = host=primary.example.com port=5432 dbname=mydb

# Read replicas com load balancing
mydb_ro = host=replica.example.com port=5432 dbname=mydb
    pool_size=50
    reserve_pool=10

# Database específica para analytics
mydb_analytics = host=analytics.example.com port=5432 dbname=mydb
    pool_size=20

# Wildcard para multi-database
* = host=localhost port=5432

[pgbouncer]
# Configurações de conexão
listen_addr = 0.0.0.0
listen_port = 6432
unix_socket_dir = /var/run/pgbouncer

# Autenticação
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
auth_query = SELECT usename, passwd FROM pg_shadow WHERE usename=$1

# Pool de conexões
pool_mode = transaction
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 10
reserve_pool_timeout = 3
max_client_conn = 2000
max_db_connections = 100
max_user_connections = 50

# Timeouts
server_idle_timeout = 300
server_lifetime = 3600
server_connect_timeout = 15
server_login_retry = 15
client_idle_timeout = 0
client_login_timeout = 60
query_timeout = 120
query_wait_timeout = 120
cancel_wait_timeout = 10

# Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
verbose = 0

# TLS/SSL
client_tls_sslmode = prefer
client_tls_key_file = /etc/pgbouncer/server.key
client_tls_cert_file = /etc/pgbouncer/server.crt
server_tls_sslmode = prefer
server_tls_key_file = /etc/pgbouncer/server.key
server_tls_cert_file = /etc/pgbouncer/server.crt
```

### Connection Pool Monitoring

```sql
-- Função para monitorar pools de conexão
CREATE OR REPLACE FUNCTION monitor_connection_pools()
RETURNS TABLE(
    database_name VARCHAR,
    user_name VARCHAR,
    cl_active INTEGER,
    cl_waiting INTEGER,
    sv_active INTEGER,
    sv_idle INTEGER,
    sv_used INTEGER,
    sv_tested INTEGER,
    sv_login INTEGER,
    maxwait NUMERIC,
    pool_mode VARCHAR
) AS $$
BEGIN
    -- Esta função requer acesso ao PgBouncer admin
    -- Na prática, usar dblink ou API do PgBouncer
    RETURN QUERY
    SELECT
        p.database,
        p."user",
        p.cl_active,
        p.cl_waiting,
        p.sv_active,
        p.sv_idle,
        p.sv_used,
        p.sv_tested,
        p.sv_login,
        p.maxwait,
        p.pool_mode
    FROM pgbouncer_pools p;
END;
$$ LANGUAGE plpgsql;

-- Alertas de pool exhaustion
DO $$
DECLARE
    v_pool RECORD;
BEGIN
    FOR v_pool IN
        SELECT * FROM monitor_connection_pools()
        WHERE cl_waiting > 5
        OR sv_active > 40
    LOOP
        IF v_pool.cl_waiting > 10 THEN
            RAISE WARNING 'Pool %: % clients waiting (possible exhaustion)',
                v_pool.database_name, v_pool.cl_waiting;
        END IF;

        IF v_pool.sv_active > 45 THEN
            RAISE WARNING 'Pool %: % active server connections (near limit)',
                v_pool.database_name, v_pool.sv_active;
        END IF;
    END LOOP;
END;
$$;
```

## Sharding Strategies

### Range-Based Sharding

```sql
-- Sharding baseado em range de IDs
CREATE TABLE orders_sharded (
    order_id BIGINT PRIMARY KEY,
    customer_id INTEGER,
    total DECIMAL(12,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (order_id);

-- Criar partições por range de IDs
CREATE TABLE orders_shard_1 PARTITION OF orders_sharded
    FOR VALUES FROM (1) TO (1000000);

CREATE TABLE orders_shard_2 PARTITION OF orders_sharded
    FOR VALUES FROM (1000000) TO (2000000);

CREATE TABLE orders_shard_3 PARTITION OF orders_sharded
    FOR VALUES FROM (2000000) TO (3000000);

CREATE TABLE orders_shard_4 PARTITION OF orders_sharded
    FOR VALUES FROM (3000000) TO (4000000);

-- Índices por partição
CREATE INDEX idx_orders_shard_1_customer ON orders_shard_1 (customer_id);
CREATE INDEX idx_orders_shard_2_customer ON orders_shard_2 (customer_id);
CREATE INDEX idx_orders_shard_3_customer ON orders_shard_3 (customer_id);
CREATE INDEX idx_orders_shard_4_customer ON orders_shard_4 (customer_id);

-- Query que benefit de partition pruning
EXPLAIN ANALYZE
SELECT * FROM orders_sharded
WHERE order_id BETWEEN 1500000 AND 1500100;
-- Apenas orders_shard_2 é acessada
```

### Geo-Based Sharding

```sql
-- Sharding baseado em localização geográfica
CREATE TABLE user_locations (
    user_id INTEGER PRIMARY KEY,
    region VARCHAR(20) NOT NULL,
    country_code VARCHAR(2),
    city VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY LIST (region);

-- Partições por região
CREATE TABLE users_americas PARTITION OF user_locations
    FOR VALUES IN ('north_america', 'south_america', 'central_america');

CREATE TABLE users_europe PARTITION OF user_locations
    FOR VALUES IN ('europe', 'western_europe', 'eastern_europe');

CREATE TABLE users_asia PARTITION OF user_locations
    FOR VALUES IN ('east_asia', 'southeast_asia', 'south_asia');

CREATE TABLE users_africa PARTITION OF user_locations
    FOR VALUES IN ('north_africa', 'sub_saharan_africa');

CREATE TABLE users_oceania PARTITION OF user_locations
    FOR VALUES IN ('australia', 'pacific_islands');

-- Índices por região
CREATE INDEX idx_users_americas_country ON users_americas (country_code, city);
CREATE INDEX idx_users_europe_country ON users_europe (country_code, city);
CREATE INDEX idx_users_asia_country ON users_asia (country_code, city);

-- Query de localização
EXPLAIN ANALYZE
SELECT * FROM user_locations
WHERE region = 'europe'
AND country_code = 'DE'
AND city LIKE 'Berlin%';
-- Apenas users_europe é acessada
```

## Data Migration Strategies

### Online Migration

```sql
-- Migração online de dados entre shards
CREATE OR REPLACE FUNCTION online_migrate_orders(
    p_source_shard INTEGER,
    p_target_shard INTEGER,
    p_batch_size INTEGER DEFAULT 1000
) RETURNS INTEGER AS $$
DECLARE
    v_migrated INTEGER := 0;
    v_batch_count INTEGER := 0;
    v_last_id BIGINT := 0;
BEGIN
    LOOP
        -- Ler lote do shard origem
        WITH batch AS (
            SELECT order_id
            FROM dblink(
                format('host=%s port=%s dbname=mydb', 
                       (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                       (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard)),
                format('SELECT order_id FROM orders WHERE order_id > %s ORDER BY order_id LIMIT %s',
                       v_last_id, p_batch_size)
            ) AS t(order_id BIGINT)
            ORDER BY order_id
        )
        SELECT MAX(order_id) INTO v_last_id FROM batch;

        EXIT WHEN v_last_id IS NULL;

        -- Inserir no shard destino
        PERFORM dblink_exec(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard)),
            format('INSERT INTO orders SELECT * FROM dblink(''host=%s port=%s dbname=mydb'', ''SELECT * FROM orders WHERE order_id > %s AND order_id <= %s'') AS t(order_id BIGINT, customer_id INTEGER, total DECIMAL, status VARCHAR, created_at TIMESTAMP)',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard),
                   v_last_id - p_batch_size, v_last_id)
        );

        v_migrated := v_migrated + p_batch_size;
        v_batch_count := v_batch_count + 1;

        -- Log de progresso
        IF v_batch_count % 10 = 0 THEN
            RAISE NOTICE 'Migrated % orders so far', v_migrated;
        END IF;

        -- Pausa para não sobrecarregar
        PERFORM pg_sleep(0.1);
    END LOOP;

    RETURN v_migrated;
END;
$$ LANGUAGE plpgsql;
```

### Data Verification

```sql
-- Verificar integridade após migração
CREATE OR REPLACE FUNCTION verify_migration(
    p_source_shard INTEGER,
    p_target_shard INTEGER
) RETURNS TABLE(
    check_name VARCHAR,
    source_count BIGINT,
    target_count BIGINT,
    is_valid BOOLEAN
) AS $$
BEGIN
    -- Verificar contagem de registros
    RETURN QUERY
    SELECT
        'row_count'::VARCHAR,
        (SELECT COUNT(*) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard)),
            'SELECT 1 FROM orders'
        ) AS t(x))::BIGINT,
        (SELECT COUNT(*) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard)),
            'SELECT 1 FROM orders'
        ) AS t(x))::BIGINT,
        (SELECT COUNT(*) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard)),
            'SELECT 1 FROM orders'
        ) AS t(x)) = (
            SELECT COUNT(*) FROM dblink(
                format('host=%s port=%s dbname=mydb',
                       (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard),
                       (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard)),
                'SELECT 1 FROM orders'
            ) AS t(x)
        );

    -- Verificar soma de totais
    RETURN QUERY
    SELECT
        'total_sum'::VARCHAR,
        (SELECT COALESCE(SUM(total), 0) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard)),
            'SELECT total FROM orders'
        ) AS t(total DECIMAL))::BIGINT,
        (SELECT COALESCE(SUM(total), 0) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard)),
            'SELECT total FROM orders'
        ) AS t(total DECIMAL))::BIGINT,
        (SELECT COALESCE(SUM(total), 0) FROM dblink(
            format('host=%s port=%s dbname=mydb',
                   (SELECT host FROM shard_mapping WHERE shard_id = p_source_shard),
                   (SELECT port FROM shard_mapping WHERE shard_id = p_source_shard)),
            'SELECT total FROM orders'
        ) AS t(total DECIMAL)) = (
            SELECT COALESCE(SUM(total), 0) FROM dblink(
                format('host=%s port=%s dbname=mydb',
                       (SELECT host FROM shard_mapping WHERE shard_id = p_target_shard),
                       (SELECT port FROM shard_mapping WHERE shard_id = p_target_shard)),
                'SELECT total FROM orders'
            ) AS t(total DECIMAL)
        );
END;
$$ LANGUAGE plpgsql;

-- Executar verificação
SELECT * FROM verify_migration(1, 2);
```

## Best Practices

### Partitioning Best Practices

```sql
-- 1. Escolher chave de partição baseada em padrões de acesso
-- Para dados temporais: RANGE em timestamp
-- Para multi-tenant: LIST em tenant_id
-- Para distribuição uniforme: HASH em primary key

-- 2. Manter tamanho de partição entre 1GB e 100GB
-- Verificar tamanho das partições
SELECT
    child.relname AS partition_name,
    pg_size_pretty(pg_total_relation_size(child.oid)) AS total_size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'application_logs'
ORDER BY child.relname;

-- 3. Criar partições futuras antecipadamente
SELECT maintain_log_partitions(6); -- Criar para os próximos 6 meses

-- 4. Arquivar partições antigas regularmente
SELECT archive_old_logs(12); -- Arquivar dados > 12 meses

-- 5. Configurar autovacuum por partição
ALTER TABLE logs_2024_06 SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);
```

### Sharding Best Practices

```sql
-- 1. Usar consistent hashing para distribuição uniforme
-- Evitar hotspots com virtual nodes

-- 2. Manter réplica completa de tabelas de referência
-- Produtos, categorias, configurações devem estar em todos os shards

-- 3. Implementar retry automático para falhas de conexão
CREATE OR REPLACE FUNCTION exec_on_shard_safe(
    p_shard_id INTEGER,
    p_query TEXT,
    p_max_retries INTEGER DEFAULT 3
) RETURNS SETOF RECORD AS $$
DECLARE
    v_retry INTEGER := 0;
    v_success BOOLEAN := FALSE;
BEGIN
    WHILE v_retry < p_max_retries AND NOT v_success LOOP
        BEGIN
            RETURN QUERY EXECUTE format(
                'SELECT * FROM dblink(''host=%s port=%s dbname=mydb'', %L) AS t(jsonb)',
                (SELECT host FROM shard_mapping WHERE shard_id = p_shard_id),
                (SELECT port FROM shard_mapping WHERE shard_id = p_shard_id),
                p_query
            );
            v_success := TRUE;
        EXCEPTION
            WHEN OTHERS THEN
                v_retry := v_retry + 1;
                PERFORM pg_sleep(power(2, v_retry) * 0.1);
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 4. Monitorar latência de cada shard
CREATE OR REPLACE FUNCTION monitor_shard_latency()
RETURNS TABLE(
    shard_id INTEGER,
    shard_name VARCHAR,
    avg_response_time INTERVAL,
    max_response_time INTERVAL,
    error_rate NUMERIC
) AS $$
DECLARE
    v_shard RECORD;
    v_start TIMESTAMP;
    v_errors INTEGER := 0;
    v_total INTEGER := 0;
BEGIN
    FOR v_shard IN SELECT * FROM shard_mapping WHERE is_active = true
    LOOP
        v_start := clock_timestamp();

        BEGIN
            PERFORM dblink_connect(
                format('host=%s port=%s dbname=mydb',
                       v_shard.host, v_shard.port)
            );
            PERFORM dblink_disconnect();
        EXCEPTION
            WHEN OTHERS THEN
                v_errors := v_errors + 1;
        END;

        v_total := v_total + 1;

        shard_id := v_shard.shard_id;
        shard_name := v_shard.shard_name;
        avg_response_time := clock_timestamp() - v_start;
        max_response_time := clock_timestamp() - v_start;
        error_rate := v_errors::NUMERIC / v_total * 100;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## Resumo

Este capítulo demonstrou como partitioning e sharding são essenciais para escalar bancos de dados além das limitações de um único servidor. Partitioning divide tabelas grandes em pedaços menores dentro do mesmo banco, enquanto sharding distribui dados entre múltiplos servidores. A escolha da estratégia correta (range, list, hash) depende dos padrões de acesso e requisitos de negócio. A combinação de partitioning com connection pooling e read replicas permite construir sistemas que escalam horizontalmente para bilhões de registros.

## Referências

- PostgreSQL Documentation: Table Partitioning
- PostgreSQL Documentation: Foreign Data Wrappers
- Designing Data-Intensive Applications (Martin Kleppmann)
- PgBouncer Documentation
- Pgpool-II Documentation
- PostgreSQL 16 Release Notes - Partitioning Improvements
- Database Sharding Patterns (Alex Petrov)
- PostgreSQL High Performance (Gregory Smith)
- Scaling PostgreSQL (Britt Crawford)
- Database Reliability Engineering (Laine Campbell, Charity Majors)
- MySQL High Availability (Charles Bell et al.)
- Cassandra: The Definitive Guide (Jeff Carpenter, Eben Hewitt)
