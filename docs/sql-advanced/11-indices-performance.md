# Indices e Performance

## Visão Geral

Indices são a ferramenta mais poderosa para otimizar consultas em bancos de dados. Sem indices adequados, o motor de banco de dados precisa varrer cada linha de cada tabela em busca de resultados — um processo chamado seq scan que degrada exponencialmente com o crescimento dos dados. Este capítulo explora os tipos de indices, suas estruturas internas, estratégias de manutenção e como analisar o plano de execução de queries.

## Por que Indices

### O Problema da Busca Sequencial

Quando uma tabela não possui índice adequado, o banco de dados executa um seq scan: lê cada linha da tabela para encontrar registros que correspondam à condição da query.

```sql
-- Tabela sem índice adequado
CREATE TABLE access_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50),
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir 10 milhões de registros
INSERT INTO access_logs (user_id, action, ip_address, created_at)
SELECT
    (random() * 100000)::INTEGER,
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
    NOW() - (random() * 365 * 24 * 60 * 60 || ' seconds')::INTERVAL
FROM generate_series(1, 10000000);

-- Query sem índice: seq scan completo
EXPLAIN ANALYZE
SELECT * FROM access_logs
WHERE user_id = 42
AND action = 'purchase'
AND created_at > NOW() - INTERVAL '7 days';
-- Seq Scan: 12.5s em 10M de linhas
-- Buffers: 450000 shared hit
```

### O Benefício do Índice

Com o índice correto, o banco de dados pode localizar as linhas desejadas diretamente, sem varrer a tabela inteira.

```sql
-- Criar índice adequado
CREATE INDEX idx_access_logs_user_action_date
ON access_logs (user_id, action, created_at);

-- Query com índice: index scan
EXPLAIN ANALYZE
SELECT * FROM access_logs
WHERE user_id = 42
AND action = 'purchase'
AND created_at > NOW() - INTERVAL '7 days';
-- Index Scan: 0.8ms em comparação com 12.5s
-- Buffers: 128 shared hit (redução de 99.7%)
-- Speedup: 15.600x mais rápido
```

### Custo de um Índice

Indices não são gratuitos. Cada índice adiciona overhead de escrita, consumo de espaço e manutenção.

```sql
-- Verificar tamanho dos índices
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE tablename = 'access_logs';

-- Verificar impacto de escrita
EXPLAIN ANALYZE
INSERT INTO access_logs (user_id, action, ip_address, created_at)
VALUES (42, 'login', '192.168.1.1', NOW());
-- Cada INSERT atualiza todos os índices da tabela
-- Com 5 índices, o INSERT faz 5 operações adicionais de índice
```

## B-Tree Index

### Estrutura B-Tree

B-Tree (Balance Tree) é o tipo de índice mais comum e versátil. Mantém os dados ordenados em uma estrutura de árvore balanceada, permitindo buscas, intervalos e ordenação com eficiência O(log n).

```sql
-- Índice B-Tree padrão (explícito)
CREATE INDEX idx_products_name
ON products USING btree (name);

-- Equivalente (B-Tree é o padrão)
CREATE INDEX idx_products_name
ON products (name);

-- Verificar tipo de índice
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'products';
-- indexdef: CREATE INDEX idx_products_name ON products USING btree (name)
```

### Operações Suportadas

```sql
-- Operações de igualdade
SELECT * FROM products WHERE id = 42;
SELECT * FROM products WHERE category = 'electronics';

-- Operações de intervalo (range)
SELECT * FROM products WHERE price BETWEEN 10 AND 50;
SELECT * FROM products WHERE created_at >= '2024-01-01';

-- Operações de ordenação
SELECT * FROM products ORDER BY name;
SELECT * FROM products ORDER BY price DESC;

-- Operações de prefixo
SELECT * FROM products WHERE name LIKE 'iPhone%';
SELECT * FROM products WHERE name ILIKE 'samsung%';

-- Operações de comparação
SELECT * FROM products WHERE price > 100;
SELECT * FROM products WHERE stock != 0;
```

### B-Tree com Múltiplas Colunas

```sql
-- Índice composto para queries com múltiplas condições
CREATE INDEX idx_orders_customer_date_status
ON orders (customer_id, created_at, status);

-- Esta query usa o índice completamente
SELECT * FROM orders
WHERE customer_id = 100
AND created_at > '2024-01-01'
AND status = 'completed';

-- Esta query usa apenas a primeira coluna do índice
SELECT * FROM orders
WHERE customer_id = 100;
-- Eficiente: faz seek direto no customer_id

-- Esta query NÃO usa o índice eficientemente
SELECT * FROM orders
WHERE created_at > '2024-01-01'
AND status = 'completed';
-- Precisaria de índice em (created_at, status)
```

### B-Tree com Ordenação Descendente

```sql
-- Índice com colunas em direções mistas
CREATE INDEX idx_events_type_time
ON events (event_type DESC, created_at ASC);

-- Query que aproveita completamente o índice
SELECT * FROM events
WHERE event_type = 'error'
ORDER BY created_at ASC;
-- O índice já está ordenado na direção exata da query

-- Alternativa: índices parciais para queries frequentes
CREATE INDEX idx_events_recent_errors
ON events (created_at)
WHERE event_type = 'error'
AND created_at > NOW() - INTERVAL '30 days';
```

## Hash Index

### Quando Usar Hash

Hash indexes são ideais para buscas de igualdade exata. Não suportam operações de intervalo, ordenação ou prefixo, mas são mais rápidos que B-Tree para igualdade.

```sql
-- Criar hash index
CREATE INDEX idx_users_email_hash
ON users USING hash (email);

-- Esta query usa o hash index eficientemente
SELECT * FROM users WHERE email = 'user@example.com';

-- Estas queries NÃO usam o hash index
SELECT * FROM users WHERE email LIKE 'user%';  -- Sem suporte a prefixo
SELECT * FROM users WHERE email > 'a';  -- Sem suporte a intervalo
SELECT * FROM users ORDER BY email;  -- Sem suporte a ordenação

-- Verificar tamanho do hash index
SELECT
    pg_size_pretty(pg_relation_size('idx_users_email_hash')) AS hash_size;

-- Comparar com B-Tree equivalente
CREATE INDEX idx_users_email_btree
ON users USING btree (email);

SELECT
    pg_size_pretty(pg_relation_size('idx_users_email_hash')) AS hash_size,
    pg_size_pretty(pg_relation_size('idx_users_email_btree')) AS btree_size;
-- Hash: ~80MB, B-Tree: ~120MB para mesma tabela
```

### Limitações

```sql
-- Hash indexes no PostgreSQL
-- 1. Não suportam UNIQUE constraint (antes do PostgreSQL 10)
-- 2. Não são replicados para standbys (antes do PostgreSQL 10)
-- 3. Não suportam index-only scans (antes do PostgreSQL 10)
-- 4. Não suportam operadores de texto LIKE, ILIKE
-- 5. Não suportam operadores de comparação

-- Verificar se o hash index está sendo usado
EXPLAIN ANALYZE
SELECT * FROM users WHERE email = 'test@example.com';
-- Hash Index Scan on idx_users_email_hash
```

## GIN/GiST (PostgreSQL)

### GIN (Generalized Inverted Index)

GIN é ideal para dados compostos como arrays, full-text search e JSONB. Cada valor de dado pode mapear para múltiplas linhas.

```sql
-- GIN para arrays
CREATE TABLE products_tags (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    tags TEXT[]
);

INSERT INTO products_tags (name, tags) VALUES
    ('iPhone 15', ARRAY['phone', 'apple', 'wireless', 'camera']),
    ('Galaxy S24', ARRAY['phone', 'samsung', 'wireless', 'ai']),
    ('MacBook Pro', ARRAY['laptop', 'apple', 'powerful', 'professional']),
    ('ThinkPad X1', ARRAY['laptop', 'lenovo', 'business', 'durable']);

-- Criar GIN index
CREATE INDEX idx_products_tags_gin
ON products_tags USING gin (tags);

-- Buscar produtos com tag específica
SELECT * FROM products_tags WHERE tags @> ARRAY['apple'];
-- GIN Index Scan

-- Buscar produtos com todas as tags especificadas
SELECT * FROM products_tags
WHERE tags @> ARRAY['phone', 'wireless'];

-- Buscar produtos com qualquer tag
SELECT * FROM products_tags
WHERE tags && ARRAY['laptop', 'phone'];

-- Buscar produtos sem tag específica
SELECT * FROM products_tags
WHERE NOT tags @> ARRAY['samsung'];

-- Verificar operadores GIN
SELECT
    am.amname AS index_type,
    a.opcname AS operator,
    a.opcdefault AS is_default
FROM pg_am am
JOIN pg_opclass a ON am.oid = a.opcmethod
WHERE am.amname = 'gin'
LIMIT 20;
```

### GIN para JSONB

```sql
-- Tabela com coluna JSONB
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar GIN index para JSONB
CREATE INDEX idx_documents_data_gin
ON documents USING gin (data);

-- Buscar por chave específica
SELECT * FROM documents
WHERE data @> '{"type": "invoice"}';

-- Buscar por valor aninhado
SELECT * FROM documents
WHERE data @> '{"customer": {"city": "São Paulo"}}';

-- Buscar por array dentro do JSON
SELECT * FROM documents
WHERE data @> '{"tags": ["urgent", "review"]}';

-- Operador ? para verificar existência de chave
SELECT * FROM documents
WHERE data ? 'priority';

-- Operador ?| para qualquer chave
SELECT * FROM documents
WHERE data ?| ARRAY['urgent', 'critical'];

-- Operador ?& para todas as chaves
SELECT * FROM documents
WHERE data ?& ARRAY['type', 'status'];

-- Criar GIN index com operador classe específico
CREATE INDEX idx_documents_data_jsonb_path
ON documents USING gin (data jsonb_path_ops);
-- jsonb_path_ops é mais eficiente para queries @> mas não suporta ?
```

### GIN para Full-Text Search

```sql
-- Tabela com dados de texto
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    content TEXT,
    search_vector TSVECTOR
);

-- Criar coluna de search vector
ALTER TABLE articles
ADD COLUMN search_vector TSVECTOR;

-- Preencher search vector
UPDATE articles
SET search_vector =
    setweight(to_tsvector('portuguese', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('portuguese', COALESCE(content, '')), 'B');

-- Criar GIN index para full-text search
CREATE INDEX idx_articles_search
ON articles USING gin (search_vector);

-- Buscar por texto
SELECT id, title,
       ts_rank(search_vector, query) AS rank
FROM articles, plainto_tsquery('portuguese', 'segurança de aplicações web') query
WHERE search_vector @@ query
ORDER BY rank DESC;

-- Buscar com phrase matching
SELECT * FROM articles,
     phraseto_tsquery('portuguese', 'injeção sql avançada') query
WHERE search_vector @@ query;
```

### GiST (Generalized Search Tree)

GiST é ideal para dados espaciais, range types e approximations.

```sql
-- GiST para range types
CREATE TABLE events_range (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    period TSRANGE
);

INSERT INTO events_range (name, period) VALUES
    ('Conferência', '[2024-06-01, 2024-06-05]'),
    ('Workshop', '[2024-06-03, 2024-06-04]'),
    ('Hackathon', '[2024-06-05, 2024-06-07]');

-- Criar GiST index
CREATE INDEX idx_events_range_period
ON events_range USING gist (period);

-- Buscar sobreposições
SELECT * FROM events_range
WHERE period && '[2024-06-02, 2024-06-06]';

-- Buscar containment
SELECT * FROM events_range
WHERE period @> '[2024-06-03, 2024-06-04]';

-- GiST para dados de extensão PostGIS
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    geom GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_locations_geom
ON locations USING gist (geom);

-- Buscar pontos dentro de um raio
SELECT name,
       ST_Distance(geom, ST_MakePoint(-46.6333, -23.5505)::geography) AS distance_meters
FROM locations
WHERE ST_DWithin(
    geom::geography,
    ST_MakePoint(-46.6333, -23.5505)::geography,
    1000  -- 1 km
)
ORDER BY distance_meters;
```

## Partial Indexes

Partial indices indexam apenas subconjuntos de linhas, reduzindo tamanho e overhead de manutenção.

```sql
-- Índice apenas para pedidos pendentes
CREATE INDEX idx_orders_pending
ON orders (created_at)
WHERE status = 'pending';

-- Query que usa o índice
SELECT * FROM orders
WHERE status = 'pending'
ORDER BY created_at;
-- Apenas pedidos pendentes são indexados

-- Índice para registros ativos
CREATE INDEX idx_users_active_email
ON users (email)
WHERE is_active = true;

-- Query eficiente
SELECT * FROM users
WHERE is_active = true
AND email = 'user@example.com';

-- Índice para valores não nulos
CREATE INDEX idx_orders_with_discount
ON orders (discount_amount)
WHERE discount_amount IS NOT NULL;

-- Análise de tamanho
SELECT
    pg_size_pretty(pg_relation_size('idx_orders_pending')) AS partial_size,
    pg_size_pretty(pg_relation_size('idx_orders_pending')) AS estimated_full_size
-- Partial: 5MB vs Full: 150MB (redução de 97%)
```

### Casos de Uso Avançados

```sql
-- Índice para valores únicos apenas em registros ativos
CREATE UNIQUE INDEX idx_users_unique_active_email
ON users (email)
WHERE is_active = true;

-- Previne emails duplicados apenas entre usuários ativos

-- Índice para valores específicos
CREATE INDEX idx_products_high_value
ON products (product_id, price)
WHERE price > 1000;

-- Índice condicional com expressão
CREATE INDEX idx_logs_recent_errors
ON logs (created_at, error_code)
WHERE level = 'error'
AND created_at > NOW() - INTERVAL '30 days';

-- Índice para validação de integridade
CREATE UNIQUE INDEX idx_unique_active_subscription
ON subscriptions (user_id)
WHERE status = 'active';
-- Garante que um usuário tenha no máximo uma assinatura ativa
```

## Covering Indexes (INCLUDE)

Covering indexes incluem colunas adicionais no índice para satisfazer queries inteiras sem acessar a tabela principal (index-only scan).

```sql
-- Índice cobridor
CREATE INDEX idx_orders_covering
ON orders (customer_id, created_at)
INCLUDE (total, status);

-- Esta query é respondida inteiramente pelo índice
SELECT customer_id, created_at, total, status
FROM orders
WHERE customer_id = 100
AND created_at > '2024-01-01';
-- Index Only Scan: não precisa acessar a tabela heap

-- Verificar se é index-only scan
EXPLAIN ANALYZE
SELECT customer_id, created_at, total, status
FROM orders
WHERE customer_id = 100
AND created_at > '2024-01-01';
-- Index Only Scan using idx_orders_covering on orders

-- Comparar com índice sem INCLUDE
CREATE INDEX idx_orders_without_covering
ON orders (customer_id, created_at);

EXPLAIN ANALYZE
SELECT customer_id, created_at, total, status
FROM orders
WHERE customer_id = 100
AND created_at > '2024-01-01';
-- Index Scan: precisa buscar total e status na tabela

-- Verificar tamanho dos índices
SELECT
    pg_size_pretty(pg_relation_size('idx_orders_covering')) AS covering_size,
    pg_size_pretty(pg_relation_size('idx_orders_without_covering')) AS regular_size;
-- Covering: 180MB vs Regular: 120MB
-- Trade-off: espaço extra por I/O reduzido
```

### INCLUDE vs Colunas da Chave

```sql
-- ERRADO: colocar colunas de seleção na chave do índice
CREATE INDEX idx_wrong
ON orders (customer_id, created_at, total, status);
-- total e status são usados apenas para consulta, não para busca
-- Isso aumenta desnecessariamente o tamanho e overhead

-- CORRETO: usar INCLUDE para colunas de cobertura
CREATE INDEX idx_correct
ON orders (customer_id, created_at)
INCLUDE (total, status);
-- Colunas INCLUDE não são ordenadas, apenas armazenadas no leaf node
-- Mais eficiente em espaço e manutenção

-- Verificar uso do índice
SELECT
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_orders_covering';
```

## Composite Indexes

### Regras de Composição

A ordem das colunas em um índice composto é crítica. O banco de dados pode usar o índice da esquerda para a direita, mas não pode pular colunas intermediárias.

```sql
-- Regra 1: Colunas de igualdade primeiro, depois intervalo
-- Query: WHERE status = 'active' AND created_at > '2024-01-01'
CREATE INDEX idx_correct_order
ON users (status, created_at);
-- Eficiente: faz seek em status, depois range em created_at

CREATE INDEX idx_wrong_order
ON users (created_at, status);
-- Ineficiente: não pode usar created_at para range sem primeiro filtrar status

-- Regra 2: Colunas mais seletivas primeiro (regra geral, não absoluta)
-- Se status tem 5 valores únicos e email tem 1M valores únicos
-- Índice: (email, status) é geralmente melhor que (status, email)

-- Regra 3: Considerar a cardinalidade das colunas
SELECT
    column_name,
    n_distinct,
    correlation
FROM pg_stats
WHERE tablename = 'users'
AND attname IN ('status', 'email', 'created_at');

-- Regra 4: Covering para queries frequentes
CREATE INDEX idx_users_covering
ON users (status, created_at)
INCLUDE (email, name, balance);
-- Responde queries completas sem acesso à tabela
```

### Padrões de Índices Compostos

```sql
-- Padrão 1: Índice para lookup frequentes
-- Query: SELECT * FROM orders WHERE customer_id = ? AND status = ?
CREATE INDEX idx_orders_lookup
ON orders (customer_id, status);

-- Padrão 2: Índice para range + sort
-- Query: SELECT * FROM logs WHERE user_id = ? AND created_at > ? ORDER BY created_at
CREATE INDEX idx_logs_range_sort
ON logs (user_id, created_at DESC);

-- Padrão 3: Índice para aggregate
-- Query: SELECT customer_id, SUM(total) FROM orders WHERE status = 'completed' GROUP BY customer_id
CREATE INDEX idx_orders_aggregate
ON orders (status, customer_id, total);
-- Index-only scan para agregação

-- Padrão 4: Índice para existência
-- Query: SELECT EXISTS(SELECT 1 FROM users WHERE email = ?)
CREATE INDEX idx_users_exists
ON users (email);
-- B-Tree simples é suficiente
```

## Expression Indexes

Expression indexes indexam o resultado de uma expressão, não o valor bruto da coluna.

```sql
-- Índice para lower()
CREATE INDEX idx_users_email_lower
ON users (LOWER(email));

-- Query case-insensitive que usa o índice
SELECT * FROM users
WHERE LOWER(email) = LOWER('User@Example.com');

-- Índice para funções de data
CREATE INDEX idx_orders_year_month
ON orders (DATE_TRUNC('month', created_at));

-- Query agrupada por mês
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*),
    SUM(total)
FROM orders
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month;

-- Índice para expressão matemática
CREATE INDEX idx_products_discounted_price
ON products (price * (1 - discount_rate));

-- Query por preço com desconto
SELECT * FROM products
WHERE price * (1 - discount_rate) < 100
ORDER BY price * (1 - discount_rate);

-- Índice para extração de dados JSON
CREATE INDEX idx_documents_type
ON documents ((data ->> 'type'));

-- Query por tipo extraído do JSON
SELECT * FROM documents
WHERE data ->> 'type' = 'invoice';

-- Índice para concatenação
CREATE INDEX idx_users_full_name
ON users ((first_name || ' ' || last_name));

-- Busca por nome completo
SELECT * FROM users
WHERE first_name || ' ' || last_name ILIKE '%silva%';
```

### Considerações

```sql
-- Expressão exata deve ser usada na query
-- Se o índice é: CREATE INDEX idx ON t (UPPER(col))
-- A query deve ser: WHERE UPPER(col) = 'VALUE'
-- WHERE upper(col) = 'VALUE' NÃO usa o índice (case-sensitive)

-- Verificar expression indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'users'
AND indexdef LIKE '%(%';

-- Índices parciais com expressões
CREATE INDEX idx_active_users_email_lower
ON users (LOWER(email))
WHERE is_active = true;
```

## Index Maintenance

### Autovacuum

Autovacuum é o mecanismo automático do PostgreSQL para limpar tuplas mortas e atualizar estatísticas.

```sql
-- Verificar status do autovacuum
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    n_dead_tup::float / NULLIF(n_live_tup, 0) AS dead_ratio,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Configurar autovacuum por tabela
ALTER TABLE access_logs SET (
    autovacuum_vacuum_scale_factor = 0.01,
    -- Vaciar quando 1% das linhas são mortas (padrão: 20%)
    autovacuum_analyze_scale_factor = 0.005,
    -- Analisar quando 0.5% das linhas mudaram (padrão: 10%)
    autovacuum_vacuum_cost_delay = 2,
    -- Reduzir delay para vacuums mais agressivos
    autovacuum_vacuum_cost_limit = 1000
    -- Aumentar limite de custo
);

-- Verificar configurações atuais
SHOW autovacuum_vacuum_scale_factor;
SHOW autovacuum_analyze_scale_factor;
SHOW autovacuum_vacuum_cost_delay;
SHOW autovacuum_max_workers;

-- Forçar vacuum manual
VACUUM (VERBOSE, ANALYZE) access_logs;

-- Vacuum completo (reclama espaço em disco)
VACUUM FULL access_logs;
-- ATENÇÃO: bloqueia a tabela durante a execução
```

### REINDEX

```sql
-- Reconstruir índice específico
REINDEX INDEX idx_access_logs_user_action_date;

-- Reconstruir todos os índices de uma tabela
REINDEX TABLE access_logs;

-- Reconstruir todos os índices do banco
REINDEX DATABASE my_database;

-- REINDEX concurrently (PostgreSQL 12+)
REINDEX INDEX CONCURRENTLY idx_access_logs_user_action_date;
-- Não bloqueia operações de leitura/escrita

-- Verificar fragmentação
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size,
    (
        SELECT COUNT(*)
        FROM pg_stat_user_indexes i
        WHERE i.indexrelname = pg_indexes.indexname
    ) AS index_scans
FROM pg_indexes
WHERE tablename = 'access_logs';
```

### Monitoramento de Índices

```sql
-- Verificar uso de índices
SELECT
    schemaname,
    relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Identificar índices não utilizados
SELECT
    indexrelname AS index_name,
    relname AS table_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Verificar duplicatas (índices com mesmas primeiras colunas)
SELECT
    a.indexrelname AS index_a,
    b.indexrelname AS index_b,
    pg_size_pretty(pg_relation_size(a.indexrelid)) AS size_a,
    pg_size_pretty(pg_relation_size(b.indexrelid)) AS size_b
FROM pg_stat_user_indexes a
JOIN pg_stat_user_indexes b
    ON a.relname = b.relname
    AND a.indexrelname < b.indexrelname
WHERE a.indexrelid IN (
    SELECT indexrelid FROM pg_index
    WHERE indkey::text LIKE (SELECT indkey::text FROM pg_index WHERE indexrelid = a.indexrelid)
);
```

## Fragmentation

### Tipos de Fragmentação

```sql
-- 1. Fragmentação interna (bloat)
-- Páginas de índice com espaço não utilizado

-- Detectar bloat de tabela
SELECT
    current_database(),
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS table_size,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 2) AS dead_percent
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- 2. Fragmentação de ordenação
-- Índices B-Tree que perderam ordenação após muitas inserções/deleções

-- Verificar ordenação do índice
SELECT
    indexrelname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE relname = 'access_logs';

-- 3. Fragmentação de pages
-- Páginas de dados espalhadas fisicamente

-- Usar extensão pgstattuple para análise detalhada
CREATE EXTENSION IF NOT EXISTS pgstattuple;

-- Analisar tabela
SELECT * FROM pgstattuple('access_logs');
-- dead_tuple_len: bytes de tuplas mortas
-- free_space: espaço livre nas páginas
-- dead_tuple_percent: percentual de tuplas mortas

-- Analisar índice
SELECT * FROM pgstatindex('idx_access_logs_user_action_date');
-- avg_leaf_density: densidade média das folhas (< 50% = muita fragmentação)
-- leaf_fragmentation: fragmentação das folhas (> 30% = problema)
```

### Resolver Fragmentação

```sql
-- Estratégia 1: VACUUM para limpar tuplas mortas
VACUUM access_logs;

-- Estratégia 2: VACUUM FULL para reescrever a tabela
-- (bloqueia a tabela, use em manutenção programada)
VACUUM FULL access_logs;

-- Estratégia 3: REINDEX para reconstruir índices
REINDEX TABLE access_logs;

-- Estratégia 4: REINDEX CONCURRENTLY (PostgreSQL 12+)
REINDEX TABLE CONCURRENTLY access_logs;
-- Não bloqueia operações

-- Estratégia 5: pg_repack (extensão, melhor opção para produção)
-- Instalar: CREATE EXTENSION pg_repack;
-- Executar: pg_repack -d my_database -t access_logs
-- Reconstrói tabela e índices sem bloqueio

-- Monitorar progresso
SELECT
    pid,
    query,
    state,
    wait_event_type,
    wait_event
FROM pg_stat_activity
WHERE query LIKE '%VACUUM%' OR query LIKE '%REINDEX%';
```

## Index-Only Scans

Index-only scans retornam resultados diretamente do índice, sem acessar a tabela heap. São a forma mais eficiente de leitura.

```sql
-- Verificar se um índice suporta index-only scans
EXPLAIN ANALYZE
SELECT customer_id, created_at
FROM orders
WHERE customer_id = 100;
-- Index Only Scan se o índice contiver todas as colunas necessárias

-- Criar índice para index-only scan
CREATE INDEX idx_orders_ionly
ON orders (customer_id)
INCLUDE (created_at, total);

-- Esta query faz index-only scan
EXPLAIN ANALYZE
SELECT customer_id, created_at, total
FROM orders
WHERE customer_id = 100;
-- Index Only Scan using idx_orders_ionly on orders

-- Verificar visibility map (afeta index-only scans)
SELECT
    relname,
    relallvisible,
    relpages,
    CASE
        WHEN relpages > 0
        THEN relallvisible::float / relpages * 100
        ELSE 0
    END AS visibility_percent
FROM pg_class
WHERE relname = 'orders';
-- relallvisible indica páginas onde todas as tuplas são visíveis

-- Forçar atualização do visibility map
VACUUM access_logs;

-- Analisar se o visibility map está atualizado
SELECT
    schemaname,
    relname,
    seq_scan,
    idx_scan,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
WHERE relname = 'orders';
```

## Query Plan Analysis com EXPLAIN

### EXPLAIN Básico

```sql
-- Plano de execução simples
EXPLAIN
SELECT * FROM orders WHERE customer_id = 100;

-- Plano com análise de performance
EXPLAIN ANALYZE
SELECT * FROM orders WHERE customer_id = 100;

-- Plano com BUFFERS (requer pg_stat_statements)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders WHERE customer_id = 100;

-- Plano completo
EXPLAIN (ANALYZE, BUFFERS, COSTS, TIMING, VERBOSE, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 100;
```

### Interpretando o Plano

```sql
-- Exemplo de plano de execução
EXPLAIN ANALYZE
SELECT o.order_id, o.total, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
AND o.created_at > '2024-01-01'
ORDER BY o.total DESC
LIMIT 10;

-- Componentes do plano:
-- 1. Seq Scan / Index Scan: como os dados são lidos
-- 2. Hash Join / Merge Join / Nested Loop: como tabelas são combinadas
-- 3. Sort: como dados são ordenados
-- 4. Limit: como resultados são limitados
-- 5. Cost: estimativa de custo (startup..total)
-- 6. Rows: estimativa de linhas
-- 7. Actual time: tempo real de execução

-- Índices para melhorar o plano
CREATE INDEX idx_orders_status_date
ON orders (status, created_at);

CREATE INDEX idx_orders_total_desc
ON orders (total DESC);

-- Plano após otimização
EXPLAIN ANALYZE
SELECT o.order_id, o.total, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
AND o.created_at > '2024-01-01'
ORDER BY o.total DESC
LIMIT 10;
-- Seq Scan → Index Scan
-- Merge Join → Hash Join (ou Nested Loop)
-- Sort → Index Scan (já ordenado)
```

### EXPLAIN com JSON

```sql
-- Formato JSON para análise programática
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 100;

-- Salvar plano em tabela
CREATE TABLE query_plans (
    plan_id SERIAL PRIMARY KEY,
    query_text TEXT,
    plan_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO query_plans (query_text, plan_json)
SELECT
    'SELECT * FROM orders WHERE customer_id = 100',
    (EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
     SELECT * FROM orders WHERE customer_id = 100)::JSONB;

-- Analisar planos armazenados
SELECT
    plan_id,
    query_text,
    plan_json -> 0 -> 'Plan' -> 'Node Type' AS node_type,
    plan_json -> 0 -> 'Plan' -> 'Total Cost' AS total_cost,
    plan_json -> 0 -> 'Plan' -> 'Actual Rows' AS actual_rows,
    plan_json -> 0 -> 'Plan' -> 'Actual Time' AS actual_time
FROM query_plans;
```

## Statistics

### Estatísticas do PostgreSQL

```sql
-- Verificar estatísticas de colunas
SELECT
    tablename,
    attname,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    histogram_bounds,
    correlation
FROM pg_stats
WHERE tablename = 'orders'
AND attname IN ('status', 'customer_id', 'created_at');

-- Configurar nível de estatísticas
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;
-- Padrão: 100. Valores mais altos = mais precisão, mais overhead

-- Atualizar estatísticas
ANALYZE orders;

-- Verificar quando estatísticas foram atualizadas
SELECT
    relname,
    last_analyze,
    last_autoanalyze,
    n_mod_since_analyze
FROM pg_stat_user_tables
WHERE relname = 'orders';
```

### pg_stat_statements

```sql
-- Instalar extensão
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configurar no postgresql.conf
-- shared_preload_libraries = 'pg_stat_statements'
-- pg_stat_statements.max = 10000
-- pg_stat_statements.track = all

-- Queries mais lentas
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Queries com mais I/O
SELECT
    query,
    calls,
    shared_blks_read,
    shared_blks_hit,
    ROUND(
        shared_blks_hit::numeric /
        NULLIF(shared_blks_hit + shared_blks_read, 0) * 100,
        2
    ) AS cache_hit_ratio
FROM pg_stat_statements
ORDER BY shared_blks_read DESC
LIMIT 10;

-- Resetar estatísticas
SELECT pg_stat_statements_reset();
```

## Autovacuum

### Configuração Detalhada

```sql
-- Configurações globais
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 3;
ALTER SYSTEM SET autovacuum_naptime = '1min';
ALTER SYSTEM SET autovacuum_vacuum_threshold = 50;
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.2;
ALTER SYSTEM SET autovacuum_analyze_threshold = 50;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.1;
ALTER SYSTEM SET autovacuum_vacuum_cost_delay = '2ms';
ALTER SYSTEM SET autovacuum_vacuum_cost_limit = 200;

-- Configurações por tabela (tabelas com escrita intensiva)
ALTER TABLE access_logs SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay = 0,
    autovacuum_vacuum_cost_limit = 1000
);

-- Verificar status do autovacuum
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    last_autovacuum,
    last_autoanalyze,
    autovacuum_count,
    autoanalyze_count
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Verificar workers ativos
SELECT
    pid,
    datname,
    relid::regclass,
    phase,
    heap_blks_total,
    heap_blks_scanned,
    heap_blks_vacuumed,
    index_vacuum_count,
    CASE
        WHEN heap_blks_total > 0
        THEN ROUND(heap_blks_vacuumed::numeric / heap_blks_total * 100, 2)
        ELSE 0
    END AS percent_complete
FROM pg_stat_progress_vacuum;
```

### Monitoramento Avançado

```sql
-- Criar view de monitoramento
CREATE OR REPLACE VIEW vacuum_monitor AS
SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    CASE
        WHEN n_live_tup > 0
        THEN ROUND(n_dead_tup::numeric / n_live_tup * 100, 2)
        ELSE 0
    END AS dead_percent,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    autovacuum_count,
    autoanalyze_count
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- Alertas de vacuum necessário
DO $$
DECLARE
    v_record RECORD;
BEGIN
    FOR v_record IN
        SELECT * FROM vacuum_monitor
        WHERE dead_percent > 20
    LOOP
        RAISE WARNING 'Table % needs vacuum: % dead tuples (% percent)',
            v_record.relname,
            v_record.n_dead_tup,
            v_record.dead_percent;
    END LOOP;
END;
$$;
```

## Exemplo: Schema com Índices Otimizados

```sql
-- Schema completo de e-commerce com índices otimizados
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    discount_rate DECIMAL(5,2) DEFAULT 0,
    category_id INTEGER,
    stock INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    search_vector TSVECTOR,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    status VARCHAR(20) DEFAULT 'pending',
    total DECIMAL(12,2) NOT NULL,
    shipping_address TEXT,
    payment_method VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- Índices para customers
CREATE UNIQUE INDEX idx_customers_email
ON customers (email)
WHERE is_active = true;

CREATE INDEX idx_customers_phone
ON customers (phone)
WHERE phone IS NOT NULL AND is_active = true;

CREATE INDEX idx_customers_created
ON customers (created_at);

-- Índices para products
CREATE INDEX idx_products_category_price
ON products (category_id, price)
WHERE is_active = true;

CREATE INDEX idx_products_price_discount
ON products (price * (1 - discount_rate))
WHERE is_active = true;

CREATE INDEX idx_products_search
ON products USING gin (search_vector);

CREATE INDEX idx_products_metadata
ON products USING gin (metadata jsonb_path_ops);

CREATE INDEX idx_products_active_stock
ON products (stock)
WHERE is_active = true AND stock > 0;

-- Índices para orders
CREATE INDEX idx_orders_customer_status
ON orders (customer_id, status);

CREATE INDEX idx_orders_status_created
ON orders (status, created_at);

CREATE INDEX idx_orders_created
ON orders (created_at);

CREATE INDEX idx_orders_pending
ON orders (created_at)
WHERE status = 'pending';

-- Índices para order_items
CREATE INDEX idx_order_items_order
ON order_items (order_id);

CREATE INDEX idx_order_items_product
ON order_items (product_id);

-- Índices compostos para queries frequentes
CREATE INDEX idx_orders_covering
ON orders (customer_id, created_at)
INCLUDE (total, status);

CREATE INDEX idx_products_covering
ON products (category_id, price)
INCLUDE (name, stock);

-- Triggers para atualizar timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_customers_updated
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_products_updated
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_orders_updated
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Função para atualizar search_vector
CREATE OR REPLACE FUNCTION update_product_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('portuguese', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('portuguese', COALESCE(NEW.description, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_search
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_product_search_vector();

-- Estatísticas para otimização de queries
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE products ALTER COLUMN category_id SET STATISTICS 1000;
```

## Benchmark de Query Performance

### Criar Dados de Teste

```sql
-- Função para gerar dados de teste
CREATE OR REPLACE FUNCTION generate_test_data()
RETURNS void AS $$
DECLARE
    v_batch_size INTEGER := 10000;
    v_total INTEGER := 1000000;
    v_i INTEGER := 0;
BEGIN
    RAISE NOTICE 'Generating % records...', v_total;

    -- Gerar customers
    INSERT INTO customers (name, email, phone)
    SELECT
        'Customer ' || i,
        'customer' || i || '@test.com',
        '+5511' || LPAD(i::TEXT, 8, '0')
    FROM generate_series(1, 100000) AS i;

    -- Gerar products
    INSERT INTO products (name, description, price, category_id, stock)
    SELECT
        'Product ' || i,
        'Description for product ' || i,
        (random() * 1000)::DECIMAL(10,2),
        (random() * 100 + 1)::INTEGER,
        (random() * 1000)::INTEGER
    FROM generate_series(1, 50000) AS i;

    -- Gerar orders (em lotes para performance)
    FOR v_i IN 0..(v_total / v_batch_size - 1) LOOP
        INSERT INTO orders (customer_id, status, total)
        SELECT
            (random() * 100000 + 1)::INTEGER,
            CASE (random() * 4)::INTEGER
                WHEN 0 THEN 'pending'
                WHEN 1 THEN 'confirmed'
                WHEN 2 THEN 'shipped'
                WHEN 3 THEN 'delivered'
                WHEN 4 THEN 'cancelled'
            END,
            (random() * 5000)::DECIMAL(12,2)
        FROM generate_series(1, v_batch_size);

        RAISE NOTICE 'Batch %/% completed', v_i + 1, v_total / v_batch_size;
    END LOOP;

    RAISE NOTICE 'Test data generation complete';
END;
$$ LANGUAGE plpgsql;

-- Executar geração de dados
SELECT generate_test_data();
```

### Benchmarks

```sql
-- Benchmark 1: Busca por email (B-Tree vs Hash)
\timing on

-- Sem índice
EXPLAIN ANALYZE
SELECT * FROM customers WHERE email = 'customer50000@test.com';
-- Seq Scan: ~800ms

-- Com B-Tree
CREATE INDEX idx_customers_email_btree
ON customers (email);
EXPLAIN ANALYZE
SELECT * FROM customers WHERE email = 'customer50000@test.com';
-- Index Scan: ~0.1ms

-- Com Hash
CREATE INDEX idx_customers_email_hash
ON customers USING hash (email);
EXPLAIN ANALYZE
SELECT * FROM customers WHERE email = 'customer50000@test.com';
-- Hash Index Scan: ~0.05ms

-- Benchmark 2: Range query
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE created_at BETWEEN '2024-01-01' AND '2024-06-30'
AND status = 'completed';
-- Seq Scan: ~1200ms

CREATE INDEX idx_orders_range
ON orders (status, created_at);
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE created_at BETWEEN '2024-01-01' AND '2024-06-30'
AND status = 'completed';
-- Index Scan: ~50ms

-- Benchmark 3: Full-text search
EXPLAIN ANALYZE
SELECT * FROM products
WHERE to_tsvector('portuguese', name || ' ' || description)
@@ plainto_tsquery('portuguese', 'product');
-- Seq Scan: ~2500ms

CREATE INDEX idx_products_fts
ON products USING gin (
    to_tsvector('portuguese', name || ' ' || description)
);
EXPLAIN ANALYZE
SELECT * FROM products
WHERE to_tsvector('portuguese', name || ' ' || description)
@@ plainto_tsquery('portuguese', 'product');
-- GIN Index Scan: ~5ms

-- Benchmark 4: Agregação com covering index
EXPLAIN ANALYZE
SELECT customer_id, COUNT(*), SUM(total)
FROM orders
WHERE status = 'completed'
GROUP BY customer_id;
-- Seq Scan + HashAggregate: ~1500ms

CREATE INDEX idx_orders_agg
ON orders (status, customer_id, total);
EXPLAIN ANALYZE
SELECT customer_id, COUNT(*), SUM(total)
FROM orders
WHERE status = 'completed'
GROUP BY customer_id;
-- Index Only Scan + GroupAggregate: ~200ms

-- Benchmark 5: JOIN performance
EXPLAIN ANALYZE
SELECT c.name, COUNT(o.order_id), SUM(o.total)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name
HAVING SUM(o.total) > 10000
ORDER BY SUM(o.total) DESC
LIMIT 20;
-- Nested Loop + Sort: ~3000ms (sem índices)
-- Hash Join + GroupAggregate: ~400ms (com índices)
```

### Relatório de Performance

```sql
-- Criar relatório de benchmark
CREATE OR REPLACE FUNCTION run_benchmark_report()
RETURNS TABLE(
    test_name TEXT,
    execution_time_ms NUMERIC,
    rows_returned BIGINT,
    buffers_hit BIGINT,
    buffers_read BIGINT,
    cache_hit_ratio NUMERIC
) AS $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_rows BIGINT;
    v_plan JSONB;
BEGIN
    -- Teste 1: Point lookup
    v_start := clock_timestamp();
    SELECT COUNT(*) INTO v_rows FROM customers WHERE email = 'customer50000@test.com';
    v_end := clock_timestamp();

    SELECT plan INTO v_plan
    FROM (EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
          SELECT * FROM customers WHERE email = 'customer50000@test.com') sub;

    test_name := 'Point Lookup (email)';
    execution_time_ms := EXTRACT(MILLISECONDS FROM v_end - v_start);
    rows_returned := v_rows;
    buffers_hit := (v_plan -> 0 -> 'Plan' -> 'Shared Hit Blocks')::BIGINT;
    buffers_read := COALESCE((v_plan -> 0 -> 'Plan' -> 'Shared Read Blocks')::BIGINT, 0);
    cache_hit_ratio := CASE
        WHEN buffers_hit + buffers_read > 0
        THEN ROUND(buffers_hit::NUMERIC / (buffers_hit + buffers_read) * 100, 2)
        ELSE 100
    END;
    RETURN NEXT;

    -- Teste 2: Range query
    v_start := clock_timestamp();
    SELECT COUNT(*) INTO v_rows FROM orders
    WHERE created_at BETWEEN '2024-01-01' AND '2024-06-30';
    v_end := clock_timestamp();

    test_name := 'Range Query (orders)';
    execution_time_ms := EXTRACT(MILLISECONDS FROM v_end - v_start);
    rows_returned := v_rows;
    RETURN NEXT;

    -- Teste 3: JOIN
    v_start := clock_timestamp();
    SELECT COUNT(*) INTO v_rows FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'completed';
    v_end := clock_timestamp();

    test_name := 'JOIN Query';
    execution_time_ms := EXTRACT(MILLISECONDS FROM v_end - v_start);
    rows_returned := v_rows;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Executar relatório
SELECT * FROM run_benchmark_report();
```

## Advanced EXPLAIN Techniques

### Custom Scan Nodes

```sql
-- EXPLAIN com opções detalhadas
EXPLAIN (
    ANALYZE,
    BUFFERS,
    COSTS,
    TIMING,
    VERBOSE,
    FORMAT TEXT
)
SELECT * FROM orders WHERE customer_id = 100;

-- Formato JSON para análise programática
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 100;

-- Salvar plano para comparação futura
CREATE TABLE explain_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    query_name VARCHAR(100),
    query_text TEXT,
    plan_json JSONB,
    execution_time_ms NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO explain_snapshots (query_name, query_text, plan_json, execution_time_ms)
SELECT
    'orders_by_customer',
    'SELECT * FROM orders WHERE customer_id = 100',
    (EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
     SELECT * FROM orders WHERE customer_id = 100)::JSONB,
    (EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
     SELECT * FROM orders WHERE customer_id = 100)::JSONB -> 0 -> 'Plan' -> 'Actual Total Time';

-- Comparar planos antes e depois de otimização
SELECT
    s1.snapshot_id,
    s1.execution_time_ms as before_ms,
    s2.execution_time_ms as after_ms,
    s1.execution_time_ms - s2.execution_time_ms as improvement_ms,
    ROUND((s1.execution_time_ms - s2.execution_time_ms) / s1.execution_time_ms * 100, 2) as improvement_percent
FROM explain_snapshots s1
JOIN explain_snapshots s2 ON s1.query_name = s2.query_name
WHERE s1.query_name = 'orders_by_customer'
AND s1.created_at < s2.created_at;
```

### Analyzing Query Plans

```sql
-- Identificar gargalos comuns no plano de execução

-- 1. Seq Scan em tabela grande
EXPLAIN ANALYZE
SELECT * FROM orders WHERE status = 'completed';
-- Seq Scan on orders (cost=0.00..1234567.89 rows=5000000 width=48)
-- Actual Time: 12345.678..12345.679 rows=5000000
-- Solução: criar índice na coluna filtrada

-- 2. Nested Loop com muitas iterações
EXPLAIN ANALYZE
SELECT o.*, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed';
-- Nested Loop (cost=0.00..9999999.99 rows=5000000 width=128)
-- Actual Time: 99999.999..99999.999 rows=5000000 loops=1
-- Solução: criar índice em orders(customer_id) ou usar Hash Join

-- 3. Sort sem índice
EXPLAIN ANALYZE
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;
-- Sort (cost=1234567.89..1234567.89 rows=5000000 width=48)
-- Sort Key: created_at DESC
-- Solução: criar índice em (created_at DESC)

-- 4. Hash Aggregate com alta cardinalidade
EXPLAIN ANALYZE
SELECT customer_id, COUNT(*)
FROM orders
GROUP BY customer_id;
-- HashAggregate (cost=1234567.89..1234567.89 rows=1000000 width=12)
-- Solução: criar índice em (customer_id) para Index Only Scan
```

### pg_stat_statements Analysis

```sql
-- Instalar extensão
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configurar no postgresql.conf
-- shared_preload_libraries = 'pg_stat_statements'
-- pg_stat_statements.max = 10000
-- pg_stat_statements.track = all

-- Queries mais lentas
SELECT
    query,
    calls,
    total_exec_time / 1000 as total_seconds,
    mean_exec_time,
    min_exec_time,
    max_exec_time,
    stddev_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Queries com mais I/O
SELECT
    query,
    calls,
    shared_blks_read,
    shared_blks_hit,
    ROUND(
        shared_blks_hit::numeric /
        NULLIF(shared_blks_hit + shared_blks_read, 0) * 100,
        2
    ) AS cache_hit_ratio,
    shared_blks_read * 8 AS read_kb
FROM pg_stat_statements
WHERE calls > 100
ORDER BY shared_blks_read DESC
LIMIT 20;

-- Queries que mais temporizam o sistema
SELECT
    query,
    calls,
    total_exec_time,
    rows,
    ROUND(total_exec_time / SUM(total_exec_time) OVER () * 100, 2) AS percent_total
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Resetar estatísticas periodicamente
SELECT pg_stat_statements_reset();
```

## Index Maintenance Automations

### Scripts de Manutenção

```sql
-- Script completo de manutenção de índices
CREATE OR REPLACE FUNCTION maintain_indexes()
RETURNS TABLE(
    action VARCHAR,
    index_name TEXT,
    table_name TEXT,
    size_before TEXT,
    size_after TEXT,
    duration INTERVAL
) AS $$
DECLARE
    v_index RECORD;
    v_start TIMESTAMP;
    v_size_before BIGINT;
    v_size_after BIGINT;
BEGIN
    -- 1. Analisar índices não utilizados
    FOR v_index IN
        SELECT
            i.indexrelname,
            i.relname as table_name,
            pg_relation_size(i.indexrelid) as index_size
        FROM pg_stat_user_indexes i
        WHERE i.idx_scan = 0
        AND i.indexrelname NOT LIKE '%_pkey'
        AND i.indexrelname NOT LIKE '%_unique'
        ORDER BY pg_relation_size(i.indexrelid) DESC
        LIMIT 10
    LOOP
        action := 'UNUSED';
        index_name := v_index.indexrelname;
        table_name := v_index.table_name;
        size_before := pg_size_pretty(v_index.index_size);
        size_after := 'N/A';
        duration := '0'::INTERVAL;
        RETURN NEXT;
    END LOOP;

    -- 2. Reindexar índices fragmentados
    FOR v_index IN
        SELECT
            i.indexrelname,
            i.relname as table_name,
            pg_relation_size(i.indexrelid) as index_size
        FROM pg_stat_user_indexes i
        JOIN pg_stat_user_tables t ON i.relid = t.relid
        WHERE t.n_dead_tup > 10000
        AND i.idx_scan > 0
        ORDER BY pg_relation_size(i.indexrelid) DESC
        LIMIT 5
    LOOP
        v_start := clock_timestamp();
        v_size_before := pg_relation_size(v_index.indexrelname::regclass);

        EXECUTE format('REINDEX INDEX CONCURRENTLY %I', v_index.indexrelname);

        v_size_after := pg_relation_size(v_index.indexrelname::regclass);

        action := 'REINDEXED';
        index_name := v_index.indexrelname;
        table_name := v_index.table_name;
        size_before := pg_size_pretty(v_size_before);
        size_after := pg_size_pretty(v_size_after);
        duration := clock_timestamp() - v_start;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Executar manutenção
SELECT * FROM maintain_indexes();
```

### Monitoramento de Performance

```sql
-- View de monitoramento de índices
CREATE OR REPLACE VIEW index_performance AS
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan AS scans,
    s.idx_tup_read AS tuples_read,
    s.idx_tup_fetch AS tuples_fetched,
    CASE
        WHEN s.idx_tup_read > 0
        THEN ROUND(s.idx_tup_fetch::numeric / s.idx_tup_read * 100, 2)
        ELSE 0
    END AS fetch_ratio,
    i.indisunique AS is_unique,
    i.indisprimary AS is_primary
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
ORDER BY s.idx_scan DESC;

-- Alertas de performance
DO $$
DECLARE
    v_record RECORD;
BEGIN
    -- Alerta para índices não utilizados há muito tempo
    FOR v_record IN
        SELECT * FROM index_performance
        WHERE scans = 0
        AND index_size::BIGINT > 104857600  -- > 100MB
    LOOP
        RAISE WARNING 'Unused index % on % is using %',
            v_record.index_name,
            v_record.table_name,
            v_record.index_size;
    END LOOP;

    -- Alerta para índices com muitas leituras mas poucos fetches
    FOR v_record IN
        SELECT * FROM index_performance
        WHERE tuples_read > 1000000
        AND fetch_ratio < 10
    LOOP
        RAISE WARNING 'Index % has low fetch ratio: % (read: %, fetched: %)',
            v_record.index_name,
            v_record.fetch_ratio,
            v_record.tuples_read,
            v_record.tuples_fetched;
    END LOOP;
END;
$$;
```

## Query Optimization Patterns

### Avoiding N+1 with Indexes

```sql
-- Problema N+1: queries que executam em loop
-- ERRADO: executar query para cada customer
DO $$
DECLARE
    v_customer RECORD;
    v_order_count INTEGER;
BEGIN
    FOR v_customer IN SELECT customer_id, name FROM customers LIMIT 100
    LOOP
        -- N+1 problem: esta query executa 100 vezes!
        SELECT COUNT(*) INTO v_order_count
        FROM orders
        WHERE customer_id = v_customer.customer_id;

        RAISE NOTICE '%: % orders', v_customer.name, v_order_count;
    END LOOP;
END;
$$;

-- CORRETO: usar JOIN ou subquery
SELECT
    c.name,
    COUNT(o.order_id) as order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
LIMIT 100;

-- Ou com subquery
SELECT
    c.name,
    (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) as order_count
FROM customers c
LIMIT 100;

-- Índices necessários
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_customers_name ON customers (name);
```

### Batch Processing Optimization

```sql
-- Processar dados em lotes para evitar locks longos
CREATE OR REPLACE FUNCTION process_batch(
    p_batch_size INTEGER DEFAULT 1000,
    p_max_batches INTEGER DEFAULT 10
) RETURNS INTEGER AS $$
DECLARE
    v_processed INTEGER := 0;
    v_batch_count INTEGER := 0;
    v_last_id INTEGER := 0;
BEGIN
    WHILE v_batch_count < p_max_batches LOOP
        BEGIN
            -- Processar lote com optimistic locking
            WITH batch AS (
                SELECT order_id
                FROM orders
                WHERE status = 'pending'
                AND order_id > v_last_id
                ORDER BY order_id
                LIMIT p_batch_size
                FOR UPDATE SKIP LOCKED
            )
            UPDATE orders
            SET status = 'processing'
            WHERE order_id IN (SELECT order_id FROM batch);

            GET DIAGNOSTICS v_processed = ROW_COUNT;

            IF v_processed = 0 THEN
                EXIT; -- Não há mais registros para processar
            END IF;

            -- Atualizar cursor
            SELECT MAX(order_id) INTO v_last_id
            FROM orders
            WHERE status = 'processing';

            v_batch_count := v_batch_count + 1;

            -- Log de progresso
            RAISE NOTICE 'Batch %: processed % records', v_batch_count, v_processed;

        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Error in batch %: %', v_batch_count, SQLERRM;
                -- Continuar com próximo lote
        END;
    END LOOP;

    RETURN v_batch_count * p_batch_size;
END;
$$ LANGUAGE plpgsql;
```

## Index Monitoring Dashboard

### Views de Monitoramento

```sql
-- View completa de status de índices
CREATE OR REPLACE VIEW index_status AS
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    s.idx_scan AS total_scans,
    s.idx_tup_read AS tuples_read,
    s.idx_tup_fetch AS tuples_fetched,
    CASE
        WHEN s.idx_tup_read > 0
        THEN ROUND(s.idx_tup_fetch::numeric / s.idx_tup_read * 100, 2)
        ELSE 0
    END AS efficiency_ratio,
    i.indisunique AS is_unique,
    i.indisprimary AS is_primary,
    pg_stat_get_last_autoanalyze_time(s.indexrelid) AS last_autoanalyze
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
ORDER BY s.idx_scan DESC;

-- View de tamanho de índices por tabela
CREATE OR REPLACE VIEW index_size_summary AS
SELECT
    schemaname,
    relname AS table_name,
    pg_size_pretty(SUM(pg_relation_size(indexrelid))) AS total_index_size,
    COUNT(*) AS index_count,
    pg_size_pretty(pg_total_relation_size(relid)) AS table_total_size
FROM pg_stat_user_indexes
JOIN pg_class ON pg_stat_user_indexes.relid = pg_class.oid
GROUP BY schemaname, relname, relid
ORDER BY SUM(pg_relation_size(indexrelid)) DESC;

-- View de índices não utilizados
CREATE OR REPLACE VIEW unused_indexes AS
SELECT
    s.schemaname,
    s.relname AS table_name,
    s.indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size,
    pg_size_pretty(pg_relation_size(s.relid)) AS table_size,
    i.indisunique,
    i.indisprimary
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
WHERE s.idx_scan = 0
AND NOT i.indisprimary
ORDER BY pg_relation_size(s.indexrelid) DESC;
```

### Alertas Automatizados

```sql
-- Sistema de alertas para problemas de índice
CREATE OR REPLACE FUNCTION check_index_health()
RETURNS TABLE(
    alert_type VARCHAR,
    severity VARCHAR,
    table_name TEXT,
    index_name TEXT,
    details TEXT
) AS $$
BEGIN
    -- Alerta 1: Índices não utilizados grandes
    RETURN QUERY
    SELECT
        'UNUSED_INDEX'::VARCHAR,
        'WARNING'::VARCHAR,
        ui.table_name::TEXT,
        ui.index_name::TEXT,
        format('Index %s on %s is %s and has never been used',
               ui.index_name, ui.table_name, ui.index_size)::TEXT
    FROM unused_indexes ui
    WHERE pg_relation_size(ui.index_name::regclass) > 10485760; -- > 10MB

    -- Alerta 2: Índices com baixa eficiência
    RETURN QUERY
    SELECT
        'LOW_EFFICIENCY'::VARCHAR,
        'INFO'::VARCHAR,
        is2.table_name::TEXT,
        is2.index_name::TEXT,
        format('Index %s has efficiency ratio of %s%%',
               is2.index_name, is2.efficiency_ratio)::TEXT
    FROM index_status is2
    WHERE is2.efficiency_ratio < 10
    AND is2.total_scans > 1000;

    -- Alerta 3: Tabelas sem índices em colunas frequentemente filtradas
    RETURN QUERY
    SELECT
        'MISSING_INDEX'::VARCHAR,
        'CRITICAL'::VARCHAR,
        st.relname::TEXT,
        'N/A'::TEXT,
        format('Table %s has %s seq scans but no suitable indexes',
               st.relname, st.seq_scan)::TEXT
    FROM pg_stat_user_tables st
    WHERE st.seq_scan > 10000
    AND st.idx_scan = 0
    AND st.n_live_tup > 100000;
END;
$$ LANGUAGE plpgsql;

-- Executar verificação de saúde
SELECT * FROM check_index_health();
```

## Advanced Query Optimization

### Subquery Optimization

```sql
-- Subquery correlada vs JOIN
-- SUBQUERY CORRELADA (pode ser lenta):
SELECT c.name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) as order_count
FROM customers c
WHERE c.is_active = true;

-- JOIN otimizado:
SELECT c.name, COUNT(o.order_id) as order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.is_active = true
GROUP BY c.customer_id, c.name;

-- Índices para otimizar JOINs
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_customers_active ON customers (is_active) WHERE is_active = true;

-- EXPLAIN para comparar planos
EXPLAIN ANALYZE
SELECT c.name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) as order_count
FROM customers c
WHERE c.is_active = true;

EXPLAIN ANALYZE
SELECT c.name, COUNT(o.order_id) as order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.is_active = true
GROUP BY c.customer_id, c.name;
```

### Window Functions Optimization

```sql
-- Window functions com índices adequados
-- Query com window function
SELECT
    order_id,
    customer_id,
    total,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) as rn,
    SUM(total) OVER (PARTITION BY customer_id) as customer_total
FROM orders
WHERE status = 'completed';

-- Índice para otimizar PARTITION BY e ORDER BY
CREATE INDEX idx_orders_customer_date
ON orders (customer_id, created_at DESC, total)
WHERE status = 'completed';

-- Index only scan para window functions
CREATE INDEX idx_orders_window
ON orders (customer_id, created_at DESC)
INCLUDE (total, status);

-- EXPLAIN ANALYZE para verificar uso do índice
EXPLAIN ANALYZE
SELECT
    order_id,
    customer_id,
    total,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) as rn
FROM orders
WHERE status = 'completed'
AND customer_id = 42;
```

### Lateral Join Optimization

```sql
-- Lateral join para top-N por grupo
-- Top 3 pedidos por cliente
SELECT c.customer_id, c.name, top_orders.*
FROM customers c
CROSS JOIN LATERAL (
    SELECT order_id, total, created_at
    FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY o.created_at DESC
    LIMIT 3
) top_orders
WHERE c.is_active = true;

-- Índice para otimizar lateral join
CREATE INDEX idx_orders_customer_date_top
ON orders (customer_id, created_at DESC, total);

-- Comparar com alternativa sem lateral
SELECT c.customer_id, c.name, o.order_id, o.total, o.created_at
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.is_active = true
AND (
    SELECT COUNT(*)
    FROM orders o2
    WHERE o2.customer_id = c.customer_id
    AND o2.created_at >= o.created_at
) <= 3;

-- O lateral join é significativamente mais rápido com o índice correto
```

## Index-Only Scan Optimization

### Visibility Map

```sql
-- Visibility map afeta index-only scans
-- Se visibility map não está atualizado, index-only scan precisa acessar heap

-- Verificar visibility map
SELECT
    relname,
    relallvisible,
    relpages,
    CASE
        WHEN relpages > 0
        THEN ROUND(relallvisible::numeric / relpages * 100, 2)
        ELSE 0
    END AS visibility_percent
FROM pg_class
WHERE relname = 'orders';

-- Forçar atualização do visibility map
VACUUM orders;

-- Verificar após vacuum
SELECT
    relname,
    relallvisible,
    relpages,
    ROUND(relallvisible::numeric / relpages * 100, 2) AS visibility_percent
FROM pg_class
WHERE relname = 'orders';

-- Index only scan depende de:
-- 1. Todas as colunas da query estarem no índice
-- 2. Visibility map estar atualizado
-- 3. Não haver colunas TOASTadas no resultado

-- Criar índice para index-only scan
CREATE INDEX idx_orders_ionly
ON orders (customer_id, created_at)
INCLUDE (total, status, payment_method);

-- Verificar se index-only scan está sendo usado
EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, created_at, total
FROM orders
WHERE customer_id = 42
AND created_at > '2024-01-01';
-- Deve mostrar "Index Only Scan"
```

## Partitioning Index Strategies

### Índices em Tabelas Particionadas

```sql
-- Tabela particionada
CREATE TABLE logs_partitioned (
    log_id BIGSERIAL,
    user_id INTEGER,
    action VARCHAR(50),
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (log_id, created_at)
) PARTITION BY RANGE (created_at);

-- Criar partições
CREATE TABLE logs_2024_01 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE logs_2024_02 PARTITION OF logs_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Índice na tabela pai (aplica a todas as partições)
CREATE INDEX idx_logs_user_date
ON logs_partitioned (user_id, created_at);

-- Índices específicos por partição (para otimizações locais)
CREATE INDEX idx_logs_2024_01_action
ON logs_2024_01 (action, created_at);

CREATE INDEX idx_logs_2024_02_action
ON logs_2024_02 (action, created_at);

-- Verificar uso de índices em partições
EXPLAIN ANALYZE
SELECT * FROM logs_partitioned
WHERE user_id = 42
AND created_at >= '2024-01-01'
AND created_at < '2024-03-01';
-- Index Scan em logs_2024_01 e logs_2024_02
```

## Index Compression

### TOAST e Compression

```sql
-- Colunas grandes podem ser comprimidas automaticamente
CREATE TABLE documents_compressed (
    doc_id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    content TEXT,  -- Armazenada em TOAST automaticamente
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verificar compressão TOAST
SELECT
    relname,
    pg_size_pretty(pg_relation_size(oid)) AS table_size,
    pg_size_pretty(pg_total_relation_size(oid)) AS total_size,
    pg_size_pretty(pg_total_relation_size(oid) - pg_relation_size(oid)) AS toast_size
FROM pg_class
WHERE relname = 'documents_compressed';

-- Configurar compressão por coluna
ALTER TABLE documents_compressed ALTER COLUMN content SET STORAGE EXTENDED;
-- EXTENDED (padrão): comprime automaticamente
-- MAIN: comprime apenas se necessário
-- EXTERNAL: nunca comprime
-- PLAIN: não comprime, não permite detoast

-- Índices em colunas comprimidas
CREATE INDEX idx_documents_title
ON documents_compressed (title);

-- GIN indexes para JSONB já comprimem internamente
CREATE INDEX idx_documents_metadata
ON documents_compressed USING gin (metadata);
```

### Page-Level Compression

```sql
-- Verificar compressão de páginas
SELECT
    relname,
    relpages,
    reltuples,
    CASE
        WHEN relpages > 0
        THEN ROUND(reltuples / relpages, 0)
        ELSE 0
    END AS tuples_per_page,
    pg_size_pretty(pg_relation_size(oid)) AS size
FROM pg_class
WHERE relname = 'orders'
AND relkind = 'r';

-- Usar pgstattuple para análise detalhada
CREATE EXTENSION IF NOT EXISTS pgstattuple;

SELECT
    table_len,
    tuple_count,
    tuple_len,
    tuple_percent,
    dead_tuple_count,
    dead_tuple_len,
    dead_tuple_percent,
    free_space,
    free_percent
FROM pgstattuple('orders');

-- Otimizar espaço com VACUUM FULL (bloqueia tabela)
-- VACUUM FULL orders;

-- Alternativa: pg_repack (online, sem bloqueio)
-- pg_repack -d mydatabase -t orders
```

## Index Advisor Tools

### pg_stat_user_indexes Analysis

```sql
-- Análise completa de uso de índices
CREATE OR REPLACE FUNCTION analyze_index_usage()
RETURNS TABLE(
    table_name TEXT,
    index_name TEXT,
    index_size TEXT,
    scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    efficiency NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.relname::TEXT,
        s.indexrelname::TEXT,
        pg_size_pretty(pg_relation_size(s.indexrelid))::TEXT,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        CASE
            WHEN s.idx_tup_read > 0
            THEN ROUND(s.idx_tup_fetch::numeric / s.idx_tup_read * 100, 2)
            ELSE 0
        END,
        CASE
            WHEN s.idx_scan = 0 THEN 'UNUSED - consider dropping'
            WHEN s.idx_tup_read > 1000000 AND s.idx_tup_fetch::numeric / s.idx_tup_read < 10
                THEN 'LOW EFFICIENCY - review index design'
            WHEN pg_relation_size(s.indexrelid) > 1073741824  -- 1GB
                THEN 'LARGE - consider if justified'
            ELSE 'OK'
        END::TEXT
    FROM pg_stat_user_indexes s
    ORDER BY s.idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Executar análise
SELECT * FROM analyze_index_usage();

-- Identificar índices que poderiam ser removidos
SELECT
    indexrelname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    idx_scan AS scans
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND indexrelname NOT LIKE '%_pkey'
AND indexrelname NOT LIKE '%_unique'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Missing Index Detection

```sql
-- Detectar queries que se beneficiariam de índices
CREATE OR REPLACE FUNCTION detect_missing_indexes()
RETURNS TABLE(
    query_pattern TEXT,
    seq_scans BIGINT,
    total_time NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        LEFT(query, 100)::TEXT,
        calls,
        total_exec_time,
        CASE
            WHEN calls > 1000 AND total_exec_time > 1000
                THEN 'HIGH PRIORITY - create index'
            WHEN calls > 100 AND total_exec_time > 100
                THEN 'MEDIUM PRIORITY - consider index'
            ELSE 'LOW PRIORITY'
        END::TEXT
    FROM pg_stat_statements
    WHERE query LIKE '%WHERE%'
    AND query NOT LIKE '%INDEX%'
    AND calls > 50
    ORDER BY total_exec_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgql;

-- Analisar colunas frequentemente filtradas
SELECT
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    CASE
        WHEN seq_scan > 10000 AND (idx_scan IS NULL OR idx_scan = 0)
        THEN 'NEEDS INDEX'
        WHEN seq_scan > idx_scan * 10
        THEN 'POSSIBLE MISSING INDEX'
        ELSE 'OK'
    END AS recommendation
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_tup_read DESC
LIMIT 20;
```

## Advanced Index Patterns

### Functional Indexes for Complex Queries

```sql
-- Índice para busca fuzzy
CREATE INDEX idx_products_name_trgm
ON products USING gin (name gin_trgm_ops);

-- Busca fuzzy
SELECT * FROM products
WHERE name % 'iphon';  -- Aproximação de 80%

-- Índice para busca fonética
CREATE EXTENSION pg_trgm;

CREATE INDEX idx_customers_name_trgm
ON customers USING gin (name gin_trgm_ops);

-- Busca por similaridade
SELECT name,
       similarity(name, 'João Silva') AS score
FROM customers
WHERE name % 'João Silva'
ORDER BY score DESC
LIMIT 10;

-- Índice para arrays
CREATE TABLE product_categories (
    product_id INTEGER PRIMARY KEY,
    categories TEXT[]
);

CREATE INDEX idx_product_categories
ON product_categories USING gin (categories);

-- Buscar produtos em múltiplas categorias
SELECT * FROM product_categories
WHERE categories @> ARRAY['electronics', 'sale'];

-- Índice para dados geoespaciais (com PostGIS)
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    geom GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_locations_geom
ON locations USING gist (geom);

-- Buscar pontos dentro de raio
SELECT name,
       ST_Distance(geom::geography, ST_MakePoint(-46.6333, -23.5505)::geography) AS distance
FROM locations
WHERE ST_DWithin(geom::geography, ST_MakePoint(-46.6333, -23.5505)::geography, 1000)
ORDER BY distance;
```

### Index Monitoring Automation

```sql
-- Script completo de monitoramento de índices
CREATE OR REPLACE FUNCTION daily_index_check()
RETURNS void AS $$
DECLARE
    v_record RECORD;
BEGIN
    -- 1. Verificar índices não utilizados
    FOR v_record IN
        SELECT * FROM unused_indexes
        WHERE index_size::BIGINT > 10485760  -- > 10MB
    LOOP
        RAISE NOTICE 'UNUSED INDEX: % on % (size: %)',
            v_record.index_name,
            v_record.table_name,
            v_record.index_size;
    END LOOP;

    -- 2. Verificar índices com baixa eficiência
    FOR v_record IN
        SELECT * FROM index_status
        WHERE efficiency_ratio < 10
        AND total_scans > 1000
    LOOP
        RAISE NOTICE 'LOW EFFICIENCY: % on % (efficiency: %%%)',
            v_record.index_name,
            v_record.table_name,
            v_record.efficiency_ratio;
    END LOOP;

    -- 3. Verificar fragmentação
    FOR v_record IN
        SELECT
            relname,
            n_dead_tup,
            n_live_tup,
            CASE
                WHEN n_live_tup > 0
                THEN ROUND(n_dead_tup::numeric / n_live_tup * 100, 2)
                ELSE 0
            END AS dead_percent
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 10000
    LOOP
        IF v_record.dead_percent > 20 THEN
            RAISE WARNING 'FRAGMENTED: % has % dead tuples (% percent)',
                v_record.relname,
                v_record.n_dead_tup,
                v_record.dead_percent;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Agendar verificação diária
-- SELECT cron.schedule('daily-index-check', '0 2 * * *',
--     'SELECT daily_index_check()');
```

## Index Performance Benchmarks

### Criar Dataset de Benchmark

```sql
-- Função para gerar dados de teste para benchmark
CREATE OR REPLACE FUNCTION generate_benchmark_data()
RETURNS void AS $$
DECLARE
    v_batch_size INTEGER := 10000;
    v_total INTEGER := 5000000;
BEGIN
    RAISE NOTICE 'Generating benchmark data...';

    -- Criar tabela de teste
    CREATE TEMPORARY TABLE benchmark_orders (
        order_id SERIAL PRIMARY KEY,
        customer_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price DECIMAL(10,2),
        status VARCHAR(20),
        created_at TIMESTAMP,
        metadata JSONB
    );

    -- Inserir dados em lotes
    FOR i IN 0..(v_total / v_batch_size - 1) LOOP
        INSERT INTO benchmark_orders (customer_id, product_id, quantity, price, status, created_at, metadata)
        SELECT
            (random() * 100000)::INTEGER,
            (random() * 10000)::INTEGER,
            (random() * 100 + 1)::INTEGER,
            (random() * 1000)::DECIMAL(10,2),
            CASE (random() * 4)::INTEGER
                WHEN 0 THEN 'pending'
                WHEN 1 THEN 'processing'
                WHEN 2 THEN 'completed'
                WHEN 3 THEN 'shipped'
                WHEN 4 THEN 'cancelled'
            END,
            NOW() - (random() * 365 * 24 * 60 * 60 || ' seconds')::INTERVAL,
            jsonb_build_object('session', gen_random_uuid())
        FROM generate_series(1, v_batch_size);

        RAISE NOTICE 'Batch %/% completed', i + 1, v_total / v_batch_size;
    END LOOP;

    ANALYZE benchmark_orders;
END;
$$ LANGUAGE plpgsql;

-- Executar geração de dados
SELECT generate_benchmark_data();
```

### Benchmark Comparativo

```sql
-- Função para benchmark de queries
CREATE OR REPLACE FUNCTION run_benchmark(
    p_query TEXT,
    p_iterations INTEGER DEFAULT 10
) RETURNS TABLE(
    avg_time_ms NUMERIC,
    min_time_ms NUMERIC,
    max_time_ms NUMERIC,
    rows_returned BIGINT
) AS $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_times NUMERIC[] := ARRAY[]::NUMERIC[];
    v_rows BIGINT;
    v_plan JSONB;
BEGIN
    FOR i IN 1..p_iterations LOOP
        v_start := clock_timestamp();

        EXECUTE p_query;

        v_end := clock_timestamp();
        v_times := array_append(v_times,
            EXTRACT(MILLISECONDS FROM v_end - v_start));
    END LOOP;

    -- Executar uma vez para obter contagem de rows
    EXECUTE p_query INTO v_rows;

    avg_time_ms := (SELECT AVG(unnest) FROM unnest(v_times));
    min_time_ms := (SELECT MIN(unnest) FROM unnest(v_times));
    max_time_ms := (SELECT MAX(unnest) FROM unnest(v_times));
    rows_returned := v_rows;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Benchmark 1: Point lookup sem índice
SELECT * FROM run_benchmark(
    'SELECT * FROM benchmark_orders WHERE customer_id = 50000'
);
-- Resultado: ~800ms

-- Criar índice e repetir benchmark
CREATE INDEX idx_bench_customer ON benchmark_orders (customer_id);

SELECT * FROM run_benchmark(
    'SELECT * FROM benchmark_orders WHERE customer_id = 50000'
);
-- Resultado: ~0.5ms (speedup: 1600x)

-- Benchmark 2: Range query
SELECT * FROM run_benchmark(
    'SELECT * FROM benchmark_orders WHERE created_at > NOW() - INTERVAL ''30 days'''
);
-- Resultado: ~1200ms

CREATE INDEX idx_bench_date ON benchmark_orders (created_at);

SELECT * FROM run_benchmark(
    'SELECT * FROM benchmark_orders WHERE created_at > NOW() - INTERVAL ''30 days'''
);
-- Resultado: ~50ms (speedup: 24x)

-- Benchmark 3: Agregação
SELECT * FROM run_benchmark(
    'SELECT customer_id, COUNT(*), SUM(price * quantity) FROM benchmark_orders WHERE status = ''completed'' GROUP BY customer_id'
);
-- Resultado: ~2000ms

CREATE INDEX idx_bench_status_customer ON benchmark_orders (status, customer_id, price, quantity);

SELECT * FROM run_benchmark(
    'SELECT customer_id, COUNT(*), SUM(price * quantity) FROM benchmark_orders WHERE status = ''completed'' GROUP BY customer_id'
);
-- Resultado: ~300ms (speedup: 6.7x)
```

## Index Design Patterns

### Pattern:覆盖查询

```sql
-- Pattern: cobrir queries frequentes com INCLUDE
-- Query frequente:
SELECT customer_id, created_at, total, status
FROM orders
WHERE customer_id = 42
AND status = 'completed'
ORDER BY created_at DESC
LIMIT 10;

-- Índice otimizado:
CREATE INDEX idx_orders_pattern_covering
ON orders (customer_id, status, created_at DESC)
INCLUDE (total);

-- Verificar Index Only Scan
EXPLAIN (ANALYZE, BUFFERS)
SELECT customer_id, created_at, total, status
FROM orders
WHERE customer_id = 42
AND status = 'completed'
ORDER BY created_at DESC
LIMIT 10;
-- Deve mostrar Index Only Scan
```

### Pattern: Índice Parcial para Valores Específicos

```sql
-- Pattern: indexar apenas registros ativos ou frequentes
-- 80% das queries são para pedidos pendentes
CREATE INDEX idx_orders_pending_only
ON orders (created_at, customer_id)
WHERE status = 'pending';

-- Tamanho: 20MB vs 150MB para índice completo
-- Performance: 2x mais rápido para queries de pending

-- Pattern: indexar apenas valores não-nulos
CREATE INDEX idx_orders_with_discount
ON orders (discount_amount, order_id)
WHERE discount_amount IS NOT NULL;
```

### Pattern: Índice para Ordenação

```sql
-- Pattern: índice na direção exata da query
-- Query: ORDER BY created_at DESC, id ASC
CREATE INDEX idx_orders_sort_pattern
ON orders (created_at DESC, id ASC);

-- Query que beneficia completamente
SELECT * FROM orders
ORDER BY created_at DESC, id ASC
LIMIT 100;
-- Sem sort adicional necessário

-- Pattern: índice para múltiplas ordenações
CREATE INDEX idx_products_multi_sort
ON products (category_id, price DESC, name ASC);

-- Queries que usam o índice
SELECT * FROM products WHERE category_id = 1 ORDER BY price DESC;
SELECT * FROM products WHERE category_id = 1 ORDER BY price DESC, name ASC;
```

## Resumo

Este capítulo demonstrou como indices são fundamentais para performance em bancos de dados. A escolha correta do tipo de índice (B-Tree, Hash, GIN, GiST), a composição adequada de colunas, o uso de covering indexes e a manutenção regular via autovacuum são essenciais para manter consultas rápidas mesmo com volumes massivos de dados. A análise cuidadosa de planos de execução com EXPLAIN permite identificar gargalos e validar que o otimizador está usando os índices corretamente.

## Referências

- PostgreSQL Documentation: Indexes
- PostgreSQL Documentation: Performance Optimization
- The Art of PostgreSQL (Dimitri Fontaine)
- Use The Index, Luke (Markus Winand)
- PostgreSQL 16 Release Notes - Index Improvements
- Database Internals (Alex Petrov)
- PostgreSQL High Performance (Gregory Smith)
- The PostgreSQL Query Planner (Jonathan Kaplan)
- Database Design for Mere Mortals (Michael Hernandez)
- SQL Performance Explained (Markus Winand)
- PostgreSQL 16 Documentation - pg_trgm Extension
- PostGIS Documentation - Spatial Indexes
- Database System Concepts (Silberschatz, Korth, Sudarsha)
