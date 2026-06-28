# Query Optimization

## Visao Geral

Query optimization e o processo pelo qual o otimizador de banco de dados determina a melhor forma de executar uma consulta SQL. Todo SGBD moderno possui um otimizador baseado em custo (cost-based optimizer) que analisa a query, gera varios planos de execucao possiveis e seleciona aquele com menor custo estimado. Este capitulo explora como funciona o otimizador, tecnicas de otimizacao, analise de planos de execucao e padroes de rewriting que transformam queries lentas em consultas eficientes.

## Como o Otimizador Funciona

### Arquitetura do Otimizador

O otimizador de um banco de dados moderno segue uma pipeline bem definida:

```sql
-- A pipeline completa do otimizador:
-- 1. Parsing: transforma SQL em AST (Abstract Syntax Tree)
-- 2. Analysis: valida sintaxe, tipos, e resolve nomes de tabelas/colunas
-- 3. Rewriting: aplica regras de transformacao (subquery unnesting, view expansion)
-- 4. Planning: gera planos de execucao alternativos
-- 5. Cost Estimation: estima custo de cada plano
-- 6. Selection: escolhe o plano de menor custo
-- 7. Execution: executa o plano selecionado

-- Exemplo de query que passa por todas as etapas:
SELECT
    u.username,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount
FROM users u
INNER JOIN orders o ON u.user_id = o.user_id
WHERE u.created_at > '2024-01-01'
AND o.status = 'completed'
GROUP BY u.username
HAVING COUNT(o.order_id) > 5
ORDER BY total_amount DESC
LIMIT 10;
```

### Fases Detalhadas do Otimizador

```sql
-- Fase 1: Parsing - transforma SQL em estrutura de dados interna
-- O parser verifica:
-- - Sintaxe correta do SQL
-- - Tipos de dados compativeis
-- - Nomes de tabelas e colunas existem
-- - Permissoes do usuario

-- Fase 2: Analysis - resolve referencias e valida semantica
-- O analyzer verifica:
-- - Tabelas referenciadas existem no schema
-- - Colunas em tabelas corretas
-- - Tipos de dados sao compativeis nas comparacoes
-- - Funcoes e operadores sao validos

-- Fase 3: Rewriting - transforma a query para forma equivalente mais eficiente
-- Regras comuns de rewriting:
-- - Subquery unnesting: transforma subquery em JOIN
-- - View expansion: substitui view pela query definida
-- - Predicate simplification: simplifica表达oes booleanas
-- - Constant folding: avalia表达oes constantes em tempo de compilacao

-- Exemplo de subquery unnesting:
-- Antes (subquery correlacionada):
SELECT * FROM orders o
WHERE o.amount > (
    SELECT AVG(o2.amount) FROM orders o2
    WHERE o2.user_id = o.user_id
);

-- Depois (appos unnesting):
SELECT o.* FROM orders o
INNER JOIN (
    SELECT user_id, AVG(amount) as avg_amount
    FROM orders GROUP BY user_id
) avg ON o.user_id = avg.user_id
WHERE o.amount > avg.avg_amount;

-- Fase 4: Planning - gera arvores de operadores
-- Cada plano e representado como uma arvore de operadores
-- Operadores comuns: SeqScan, IndexScan, HashJoin, MergeJoin, NestedLoop

-- Fase 5: Cost Estimation - usa estatisticas da tabela
-- O estimador usa:
-- - Numero de linhas (pg_class.reltuples)
-- - Distribuicao de valores (pg_stats)
-- - Tamanho da tabela (pg_class.relpages)
-- - Seletividade dos filtros

-- Fase 6: Selection - compara custos e escolhe menor
-- Algoritmos de busca:
-- - Dynamic programming (ate ~12 tabelas)
-- - Genetic algorithm (muitas tabelas)
-- - Exhaustive search (poucas tabelas)
```

### Estatisticas do Otimizador

```sql
-- PostgreSQL mantem estatisticas detalhadas em pg_stats
-- Estas estatisticas sao atualizadas automaticamente ou via ANALYZE

-- Ver estatisticas de uma tabela
SELECT
    attname,
    n_distinct,
    most_common_vals,
    most_common_freqs,
    histogram_bounds,
    correlation
FROM pg_stats
WHERE tablename = 'orders';

-- Exemplo de saida:
-- attname: user_id
-- n_distinct: 15000 (numero de valores distintos)
-- most_common_vals: {1, 2, 3, 4, 5} (valores mais frequentes)
-- most_common_freqs: {0.15, 0.12, 0.10, 0.08, 0.07} (frequencias)
-- histogram_bounds: {1, 500, 1000, ..., 15000} (distribuicao)

-- Forcar atualizacao de estatisticas
ANALYZE orders;

-- Ver estatisticas completas de uma tabela
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    avg_width,
    correlation
FROM pg_stats
WHERE tablename = 'users';

-- Estatisticas para colunas especificas
SELECT
    tablename,
    attname,
    n_distinct,
    histogram_bounds
FROM pg_stats
WHERE tablename = 'products'
AND attname IN ('category', 'price');

-- PostgreSQL 13+ permite estatisticas para expressoes
CREATE INDEX idx_orders_status ON orders (status);
ANALYZE orders;

-- Ver estatisticas do indice
SELECT
    indexrelname,
    indrelid::regclass,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE relname = 'orders';
```

## Cost-Based Optimization

### Modelo de Custo do PostgreSQL

```sql
-- Cada operacao no plano tem um custo estimado
-- Custo = (custo de leitura) + (custo de processamento)

-- Parametros de custo no postgresql.conf:
-- seq_page_cost = 1.0      (custo de ler uma pagina sequencial)
-- random_page_cost = 4.0   (custo de ler uma pagina aleatoria)
-- cpu_tuple_cost = 0.01    (custo de processar uma tupla)
-- cpu_index_tuple_cost = 0.005 (custo de processar uma tupla de indice)
-- cpu_operator_cost = 0.0025   (custo de uma operacao CPU)
-- effective_cache_size = 4GB   (memoria disponivel para cache)

-- Ver custos estimados de uma query
EXPLAIN (COSTS, VERBOSE)
SELECT * FROM orders WHERE user_id = 42;

-- Saida:
-- Seq Scan on public.orders (cost=0.00..3580.00 rows=150 width=48)
--   Output: order_id, user_id, amount, status, created_at
--   Filter: (user_id = 42)
-- Planning Time: 0.125 ms

-- Interpretacao:
-- cost=0.00..3580.00
-- 0.00: custo inicial (start cost)
-- 3580.00: custo total (total cost)
-- rows=150: estimativa de linhas retornadas
-- width=48: largura media das linhas em bytes

-- Comparar custos de diferentes planos
EXPLAIN (COSTS)
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'pending';

-- Hash Join:
-- Hash Join (cost=2.00..4520.00 rows=12000 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=12000 width=48)
--         Filter: (status = 'pending')
--   -> Hash (cost=1.50..1.50 rows=50 width=24)
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50 width=24)

-- Nested Loop:
-- Nested Loop (cost=0.00..89200.00 rows=12000 width=64)
--   Join Filter: (o.user_id = u.user_id)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=12000 width=48)
--         Filter: (status = 'pending')
--   -> Index Scan on users_pkey u (cost=0.28..8.30 rows=1 width=24)
--         Index Cond: (user_id = o.user_id)

-- O otimizador escolhe Hash Join porque 4520 < 89200
```

### Fatores que Influenciam o Custo

```sql
-- 1. Seletividade do filtro
-- Quanto mais seletivo o filtro, menor o custo

-- Filtro pouco seletivo (retorna 80% das linhas)
EXPLAIN ANALYZE SELECT * FROM orders WHERE status != 'cancelled';
-- Seq Scan: 250ms, rows=800000

-- Filtro muito seletivo (retorna 0.1% das linhas)
EXPLAIN ANALYZE SELECT * FROM orders WHERE order_id = 12345;
-- Index Scan: 0.1ms, rows=1

-- 2. Custo de acesso (sequential vs random)
-- Sequential scan: le paginas em sequencia (baixo custo)
-- Index scan: le paginas aleatoriamente (alto custo)

-- Para tabelas pequenas, seq scan e mais barato que index scan
-- Para tabelas grandes com filtro seletivo, index scan e mais barato

-- 3. Custo de join
-- Nested Loop: O(n*m) - bom para tabelas pequenas
-- Hash Join: O(n+m) - bom para tabelas medias/grandes
-- Merge Join: O(n log n + m log m) - bom para dados ordenados

-- 4. Custo de ordenacao
-- Sort: O(n log n) - custoso para muitas linhas
-- Index Scan: O(n) - se o indice ja esta ordenado

-- 5. Custo de agregacao
-- Hash Aggregate: O(n) - bom para muitos grupos
-- GroupAggregate: O(n log n) - bom para poucos grupos

-- Ver como o PostgreSQL estima seletividade
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM orders
WHERE user_id BETWEEN 100 AND 200
AND status = 'completed'
AND amount > 1000;

-- Buffers mostram leituras reais:
-- shared hit=450 (leituras do cache)
-- shared read=12 (leituras do disco)
-- temp read=0 (leituras de disco temporario)
-- temp written=0 (escritas de disco temporario)
```

## Join Order Optimization

### Por que a Ordem dos Joins Importa

```sql
-- A ordem dos joins afeta dramaticamente a performance
-- O otimizador precisa decidir:
-- 1. Qual tabela e a "tabela de drive"
-- 2. Em que ordem as tabelas sao unidas
-- 3. Qual algoritmo de join usar para cada par

-- Exemplo: 3 tabelas com tamanhos diferentes
-- users: 10.000 linhas
-- orders: 1.000.000 linhas
-- order_items: 10.000.000 linhas

-- Query com join order suboptimo
SELECT u.username, oi.product_name
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN users u ON o.user_id = u.user_id
WHERE u.country = 'Brazil';

-- Plano possivel (suboptimo):
-- Hash Join (cost=125000.00..180000.00 rows=500000 width=64)
--   -> Seq Scan on order_items oi (cost=0.00..180000.00 rows=10000000 width=48)
--   -> Hash (cost=35000.00..35000.00 rows=100000 width=24)
--         -> Seq Scan on users u (cost=0.00..35000.00 rows=100000 width=24)
--               Filter: (country = 'Brazil')
-- Custo: 180.000 (muito alto)

-- Plano otimo (otimizador escolhe automaticamente):
-- Hash Join (cost=2.00..12500.00 rows=500000 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Hash Join (cost=1.50..8500.00 rows=1000000 width=48)
--         Hash Cond: (oi.order_id = o.order_id)
--         -> Seq Scan on order_items oi (cost=0.00..18000.00 rows=10000000 width=32)
--         -> Hash (cost=1.25..1.25 rows=100000 width=24)
--               -> Seq Scan on users u (cost=0.00..1.25 rows=100000 width=24)
--                     Filter: (country = 'Brazil')
-- Custo: 12.500 (otimo)

-- A diferenca: 12.500 vs 180.000 = 14.4x mais rapido
```

### Otimizacao de Join Order pelo Otimizador

```sql
-- O PostgreSQL usa dynamic programming para ate ~12 tabelas
-- Para mais tabelas, usa algoritmo genetico

-- Ver o plano escolhido pelo otimizador
EXPLAIN (COSTS, VERBOSE)
SELECT
    c.customer_name,
    p.product_name,
    oi.quantity
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'USA'
AND o.order_date >= '2024-01-01'
AND p.category = 'Electronics';

-- Saida:
-- Hash Join (cost=2.00..15000.00 rows=25000 width=96)
--   Hash Cond: (oi.product_id = p.product_id)
--   -> Hash Join (cost=1.50..12000.00 rows=25000 width=64)
--         Hash Cond: (o.order_id = oi.order_id)
--         -> Hash Join (cost=1.25..9000.00 rows=50000 width=48)
--               Hash Cond: (c.customer_id = o.customer_id)
--               -> Seq Scan on customers c (cost=0.00..2500.00 rows=5000 width=24)
--                     Filter: (country = 'USA')
--               -> Hash (cost=1.00..1.00 rows=100000 width=32)
--                     -> Seq Scan on orders o (cost=0.00..5000.00 rows=100000 width=32)
--                           Filter: (order_date >= '2024-01-01')
--         -> Hash (cost=0.80..0.80 rows=200000 width=16)
--               -> Seq Scan on order_items oi (cost=0.00..8000.00 rows=200000 width=16)
--   -> Hash (cost=0.50..0.50 rows=500 width=32)
--         -> Seq Scan on products p (cost=0.00..0.50 rows=500 width=32)
--               Filter: (category = 'Electronics')

-- O otimizador:
-- 1. Comeca pelas tabelas mais pequenas/mais seletivas
-- 2. Usa Hash Join para tabelas grandes
-- 3. Reduz o numero de linhas progressivamente
```

### Forcar Ordem de Join (HINTS)

```sql
-- As vezes o otimizador escolhe ordem suboptima
-- Nesses casos podemos usar hints (varia por SGBD)

-- PostgreSQL: nao tem hints nativas, mas podemos usar:
-- 1. CTEs para materializar subconjuntos
-- 2. Subqueries para forcar ordem
-- 3. pg_hint_plan (extensao)

-- Usando CTEs para forcar ordem:
WITH active_customers AS (
    SELECT customer_id, customer_name
    FROM customers
    WHERE country = 'Brazil'
    AND status = 'active'
),
recent_orders AS (
    SELECT order_id, customer_id
    FROM orders
    WHERE order_date >= '2024-01-01'
    AND status = 'completed'
)
SELECT ac.customer_name, p.product_name
FROM active_customers ac
JOIN recent_orders ro ON ac.customer_id = ro.customer_id
JOIN order_items oi ON ro.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id;

-- MySQL: usa hints de join
SELECT STRAIGHT_JOIN
    c.customer_name,
    p.product_name
FROM customers c
STRAIGHT_JOIN orders o ON c.customer_id = o.customer_id
STRAIGHT_JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil';

-- SQL Server: usa OPTION clause
SELECT
    c.customer_name,
    p.product_name
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil'
OPTION (FORCE ORDER);

-- Oracle: usa hints de join order
SELECT /*+ ORDERED */
    c.customer_name,
    p.product_name
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil';
```

## Predicate Pushdown

### O que e Predicate Pushdown

```sql
-- Predicate pushdown e uma otimizacao onde filtros sao movidos
-- o mais perto possivel da fonte de dados
-- Isso reduz a quantidade de dados que precisam ser processados

-- Sem predicate pushdown:
SELECT * FROM (
    SELECT o.*, u.username
    FROM orders o
    JOIN users u ON o.user_id = u.user_id
) subquery
WHERE subquery.status = 'pending';

-- Com predicate pushdown:
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'pending';

-- O otimizador faz isso automaticamente na maioria dos casos
-- Mas views materializadas e subqueries complexas podem impedir

-- Exemplo onde predicate pushdown NAO acontece:
CREATE MATERIALIZED VIEW order_summary AS
SELECT
    user_id,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM orders
GROUP BY user_id;

-- Query na view materializada:
SELECT * FROM order_summary
WHERE user_id = 42;

-- O filtro NAO e aplicado na view porque ela ja esta materializada
-- Precisamos recriar a view com o filtro ou usar other strategies

-- Solucao: recriar view com filtro
DROP MATERIALIZED VIEW order_summary;
CREATE MATERIALIZED VIEW order_summary AS
SELECT
    user_id,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM orders
WHERE user_id = 42  -- Filtro incorporado
GROUP BY user_id;

-- Outra solucao: usar indice na view
CREATE UNIQUE INDEX idx_order_summary_user
ON order_summary (user_id);

-- Agora o filtro pode usar o indice
EXPLAIN ANALYZE
SELECT * FROM order_summary WHERE user_id = 42;
-- Index Scan usando idx_order_summary_user
```

### Predicate Pushdown em Views

```sql
-- Views regulares (nao materializadas) sao expandidas pelo otimizador
-- Isso permite predicate pushdown automatico

-- Criar view
CREATE VIEW active_orders AS
SELECT
    o.order_id,
    o.user_id,
    o.amount,
    o.status,
    u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'active';

-- Query na view
SELECT * FROM active_orders
WHERE user_id = 42
AND amount > 100;

-- O otimizador expande a view e aplica os filtros:
-- 1. WHERE o.status = 'active' (da view)
-- 2. WHERE user_id = 42 (do usuario)
-- 3. WHERE amount > 100 (do usuario)
-- Todos sao aplicados antes dos joins

-- Verificar com EXPLAIN
EXPLAIN (VERBOSE)
SELECT * FROM active_orders
WHERE user_id = 42
AND amount > 100;

-- Saida:
-- Hash Join (cost=2.00..450.00 rows=5 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Index Scan on orders o (cost=0.29..445.00 rows=5 width=48)
--         Index Cond: (user_id = 42)
--         Filter: (status = 'active' AND amount > 100)
--   -> Hash (cost=1.50..1.50 rows=1 width=24)
--         -> Index Scan on users u (cost=0.28..1.50 rows=1 width=24)
--               Index Cond: (user_id = 42)

-- Predicate pushdown funciona bem com views regulares
-- Mas views materializadas precisam de abordagem diferente
```

### Predicate Pushdown em Subqueries

```sql
-- Subqueries correlacionadas podem impedir predicate pushdown
-- Subqueries nao correlacionadas sao otimizadas melhor

-- Subquery correlacionada (problematica):
SELECT * FROM orders o
WHERE o.amount > (
    SELECT AVG(amount) FROM orders
    WHERE user_id = o.user_id
);

-- Subquery nao correlacionada (melhor):
SELECT o.* FROM orders o
JOIN (
    SELECT user_id, AVG(amount) as avg_amount
    FROM orders
    GROUP BY user_id
) avg ON o.user_id = avg.user_id
WHERE o.amount > avg.avg_amount;

-- O otimizador pode "achatar" subqueries correlacionadas
-- em muitos casos, mas nem sempre

-- Forcar flatten de subquery com CTE:
WITH user_averages AS (
    SELECT user_id, AVG(amount) as avg_amount
    FROM orders
    GROUP BY user_id
)
SELECT o.* FROM orders o
JOIN user_averages ua ON o.user_id = ua.user_id
WHERE o.amount > ua.avg_amount;

-- Subquery com IN pode ser otimizada para JOIN:
-- Antes:
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE active = true
);

-- Depois (otimizador faz automaticamente):
SELECT p.* FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.active = true;

-- Verificar se o otimizador fez a transformacao:
EXPLAIN (VERBOSE)
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE active = true
);

-- Se nao fez, podemos forcar com CTE:
WITH active_categories AS (
    SELECT category_id FROM categories WHERE active = true
)
SELECT p.* FROM products p
JOIN active_categories ac ON p.category_id = ac.category_id;
```

## Subquery Flattening

### Tecnicas de Flattening

```sql
-- Subquery flattening transforma subqueries complexas em queries mais simples
-- O PostgreSQL tem varios algoritmos para isso

-- 1. EXISTS subquery -> JOIN
-- Antes:
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.user_id = u.user_id
    AND o.status = 'completed'
);

-- Depois (otimizador transforma em semi-join):
SELECT DISTINCT u.* FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE o.status = 'completed';

-- 2. IN subquery -> JOIN
-- Antes:
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE featured = true
);

-- Depois:
SELECT p.* FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.featured = true;

-- 3. NOT EXISTS -> LEFT JOIN + IS NULL
-- Antes:
SELECT * FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.user_id = u.user_id
);

-- Depois:
SELECT u.* FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IS NULL;

-- 4. Scalar subquery -> lateral join
-- Antes:
SELECT
    u.username,
    (SELECT MAX(order_date) FROM orders WHERE user_id = u.user_id) as last_order
FROM users u;

-- Depois:
SELECT
    u.username,
    lo.last_order
FROM users u
LEFT JOIN LATERAL (
    SELECT MAX(order_date) as last_order
    FROM orders
    WHERE user_id = u.user_id
) lo ON true;

-- Verificar flattening com EXPLAIN
EXPLAIN (VERBOSE)
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.user_id = u.user_id
    AND o.status = 'completed'
);

-- Saida pode mostrar:
-- Hash Semi Join (cost=2.00..8500.00 rows=15000 width=24)
--   Hash Cond: (u.user_id = o.user_id)
--   -> Seq Scan on users u (cost=0.00..1500.00 rows=50000 width=24)
--   -> Hash (cost=1.50..1.50 rows=25000 width=4)
--         -> Seq Scan on orders o (cost=0.00..3500.00 rows=25000 width=4)
--               Filter: (status = 'completed')

-- Hash Semi Join e mais eficiente que subquery correlacionada
```

### Subqueries que Nao Flattening

```sql
-- Algumas subqueries nao podem ser achadas:
-- 1. Subqueries com agregacao complexa
-- 2. Subqueries com UNION
-- 3. Subqueries com LIMIT
-- 4. Subqueries com window functions

-- Exemplo: subquery com LIMIT (nao flattening)
SELECT * FROM users u
WHERE (
    SELECT COUNT(*) FROM orders o
    WHERE o.user_id = u.user_id
) > 5;

-- O otimizador pode transformar em:
SELECT u.* FROM users u
JOIN (
    SELECT user_id, COUNT(*) as order_count
    FROM orders
    GROUP BY user_id
    HAVING COUNT(*) > 5
) oc ON u.user_id = oc.user_id;

-- Exemplo: subquery com UNION (nao flattening)
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE type = 'main'
    UNION
    SELECT category_id FROM categories WHERE type = 'featured'
);

-- O otimizador pode transformar em:
SELECT p.* FROM products p
WHERE EXISTS (
    SELECT 1 FROM categories c
    WHERE (c.type = 'main' OR c.type = 'featured')
    AND c.category_id = p.category_id
);

-- Forcar flattening com CTEs quando necessario
WITH all_categories AS (
    SELECT category_id FROM categories WHERE type = 'main'
    UNION
    SELECT category_id FROM categories WHERE type = 'featured'
)
SELECT p.* FROM products p
JOIN all_categories ac ON p.category_id = ac.category_id;

-- Usar LATERAL para subqueries dependentes
SELECT
    u.username,
    latest.last_order_date,
    latest.last_amount
FROM users u
LEFT JOIN LATERAL (
    SELECT order_date as last_order_date, amount as last_amount
    FROM orders
    WHERE user_id = u.user_id
    ORDER BY order_date DESC
    LIMIT 1
) latest ON true;

-- LATERAL e otimo para "top-N per group"
```

## Materialization vs Streaming

### Quando Materializar

```sql
-- Materializacao cria copia temporaria dos dados
-- Streaming processa dados em tempo real

-- Cenarios para materializacao:
-- 1. Subqueries executadas multiplas vezes
-- 2. Tabelas de dimensao pequenas
-- 3. Resultados de agregacoes complexas
-- 4. Dados que mudam raramente

-- Exemplo: materializar subquery com CTE
WITH active_users AS (
    SELECT user_id, username, email
    FROM users
    WHERE status = 'active'
    AND last_login > NOW() - INTERVAL '30 days'
)
SELECT
    au.username,
    COUNT(o.order_id) as order_count,
    SUM(o.amount) as total_amount
FROM active_users au
JOIN orders o ON au.user_id = o.user_id
GROUP BY au.username;

-- O CTE pode ser materializado ou nao
-- PostgreSQL decide baseado no custo

-- Forcar materializacao (PostgreSQL 12+):
WITH active_users AS MATERIALIZED (
    SELECT user_id, username, email
    FROM users
    WHERE status = 'active'
)
SELECT * FROM active_users au
JOIN orders o ON au.user_id = o.user_id;

-- Forcar streaming (nao materializar):
WITH active_users AS NOT MATERIALIZED (
    SELECT user_id, username, email
    FROM users
    WHERE status = 'active'
)
SELECT * FROM active_users au
JOIN orders o ON au.user_id = o.user_id;

-- Materialized views para dados que mudam pouco
CREATE MATERIALIZED VIEW product_summary AS
SELECT
    category,
    COUNT(*) as product_count,
    AVG(price) as avg_price
FROM products
GROUP BY category;

-- Atualizar quando necessario
REFRESH MATERIALIZED VIEW product_summary;

-- Atualizacao concorrente (requer indice unico)
CREATE UNIQUE INDEX idx_product_summary_category
ON product_summary (category);

REFRESH MATERIALIZED VIEW CONCURRENTLY product_summary;
```

### Quando Usar Streaming

```sql
-- Streaming e melhor quando:
-- 1. Dados mudam frequentemente
-- 2. Precisamos de resultados em tempo real
-- 3. Memoria e limitada
-- 4. Query e executada uma vez

-- Exemplo: processamento de logs em streaming
-- Sem materializacao (streaming):
SELECT
    date_trunc('hour', created_at) as hour,
    action,
    COUNT(*) as action_count
FROM access_logs
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', created_at), action
ORDER BY hour DESC, action_count DESC;

-- Com materializacao (se precisarmos reusar):
CREATE MATERIALIZED VIEW hourly_stats AS
SELECT
    date_trunc('hour', created_at) as hour,
    action,
    COUNT(*) as action_count
FROM access_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', created_at), action;

-- Para dados em tempo real, use triggers ou CDC
-- Change Data Capture (CDC) captura mudancas em tempo real

-- Exemplo com trigger para manter contagem atualizada:
CREATE OR REPLACE FUNCTION update_order_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE user_stats
        SET order_count = order_count + 1,
            total_amount = total_amount + NEW.amount
        WHERE user_id = NEW.user_id;
        
        IF NOT FOUND THEN
            INSERT INTO user_stats (user_id, order_count, total_amount)
            VALUES (NEW.user_id, 1, NEW.amount);
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE user_stats
        SET order_count = order_count - 1,
            total_amount = total_amount - OLD.amount
        WHERE user_id = OLD.user_id;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_order_count
AFTER INSERT OR DELETE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_order_count();

-- Agora user_stats sempre esta atualizada
-- Sem precisar de refresh periodico
```

## EXPLAIN ANALYZE em PostgreSQL

### Usando EXPLAIN ANALYZE

```sql
-- EXPLAIN mostra o plano estimado
-- EXPLAIN ANALYZE executa a query e mostra o plano real
-- EXPLAIN (ANALYZE, BUFFERS) inclui informacoes de I/O

-- Exemplo basico:
EXPLAIN ANALYZE
SELECT * FROM orders
WHERE user_id = 42
AND status = 'completed';

-- Saida:
-- Index Scan using idx_orders_user_status on orders (cost=0.43..8.45 rows=1 width=48)
--   Index Cond: (user_id = 42 AND status = 'completed')
-- Planning Time: 0.125 ms
-- Execution Time: 0.089 ms

-- Interpretacao:
-- cost=0.43..8.45: custo estimado (start..total)
-- rows=1: estimativa de linhas
-- width=48: largura media das linhas
-- Planning Time: tempo para gerar o plano
-- Execution Time: tempo real de execucao

-- EXPLAIN com BUFFERS (mostra leituras):
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'pending';

-- Saida:
-- Hash Join (cost=2.00..4520.00 rows=12000 width=64) (actual time=0.025..45.123 rows=12000 loops=1)
--   Hash Cond: (o.user_id = u.user_id)
--   Buffers: shared hit=450 read=12
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=12000 width=48) (actual time=0.015..30.456 rows=12000 loops=1)
--         Filter: (status = 'pending')
--         Rows Removed by Filter: 88000
--         Buffers: shared hit=420 read=12
--   -> Hash (cost=1.50..1.50 rows=50 width=24) (actual time=0.008..0.009 rows=50 loops=1)
--         Buckets: 1024  Batches: 1  Memory Usage: 10kB
--         Buffers: shared hit=30
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50 width=24) (actual time=0.005..0.007 rows=50 loops=1)
--               Buffers: shared hit=30
-- Planning Time: 0.150 ms
-- Execution Time: 45.250 ms

-- Interpretacao dos BUFFERS:
-- shared hit: leituras do buffer cache (memoria)
-- shared read: leituras do disco
-- temp read: leituras de disco temporario (para work_mem)
-- temp written: escritas de disco temporario
-- local hit/read/written: para tabelas particionadas locais

-- Comparar estimativa vs real:
-- rows=12000 (estimativa)
-- actual rows=12000 (real) -- boa estimativa!
-- Se Rows Removed by Filter e grande, estatisticas podem estar desatualizadas
```

### Formatos de Saida do EXPLAIN

```sql
-- PostgreSQL suporta varios formatos de saida:
-- TEXT (padrao), JSON, XML, YAML

-- Formato JSON (mais detalhado):
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE user_id = 42;

-- Saida JSON:
-- [
--   {
--     "Plan": {
--       "Node Type": "Index Scan",
--       "Relation Name": "orders",
--       "Alias": "orders",
--       "Startup Cost": 0.43,
--       "Total Cost": 8.45,
--       "Plan Rows": 1,
--       "Plan Width": 48,
--       "Actual Startup Time": 0.025,
--       "Actual Total Time": 0.030,
--       "Actual Rows": 1,
--       "Actual Loops": 1,
--       "Index Cond": "(user_id = 42)",
--       "Buffers": {
--         "Shared Hit": 4
--       }
--     },
--     "Planning Time": 0.125,
--     "Execution Time": 0.180
--   }
-- ]

-- Formato TEXT com opcoes extras:
EXPLAIN (
    ANALYZE,
    BUFFERS,
    TIMING,
    VERBOSE,
    FORMAT TEXT
)
SELECT * FROM orders WHERE user_id = 42;

-- Opcoes uteis:
-- TIMING: inclui tempos de cada operacao
-- VERBOSE: inclui colunas adicionais
-- SUMMARY: inclui tempo total
-- COSTS: inclui custos estimados
-- SETTINGS: inclui configuracoes usadas

-- Para queries com parametros (prepared statements):
PREPARE find_orders (INTEGER) AS
SELECT * FROM orders WHERE user_id = $1;

EXPLAIN ANALYZE EXECUTE find_orders(42);

-- O plano e cached e pode ser reusado
```

### Analisando Problemas Comuns

```sql
-- Problema 1: Seq Scan quando deveria ser Index Scan
-- Causa: estatisticas desatualizadas ou filtro pouco seletivo

EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'completed';
-- Seq Scan on orders (cost=0.00..35800.00 rows=800000 width=48)
--   Filter: (status = 'completed')
--   Rows Removed by Filter: 200000
-- Planning Time: 0.100 ms
-- Execution Time: 1250.000 ms

-- Solucao 1: criar indice
CREATE INDEX idx_orders_status ON orders (status);

-- Solucao 2: atualizar estatisticas
ANALYZE orders;

-- Solucao 3: usar SET para forcar index scan (temporario)
SET enable_seqscan = off;
EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'completed';
SET enable_seqscan = on;

-- Problema 2: Nested Loop quando deveria ser Hash Join
-- Causa: tabela de drive muito grande ou estimativa errada

EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- Nested Loop (cost=0.00..89200.00 rows=1000000 width=64)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=1000000 width=48)
--   -> Index Scan on users u (cost=0.28..8.30 rows=1 width=24)
--         Index Cond: (user_id = o.user_id)
-- Planning Time: 0.150 ms
-- Execution Time: 45000.000 ms (45 segundos!)

-- Solucao: forcar Hash Join
SET enable_nestloop = off;
EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;
SET enable_nestloop = on;

-- Hash Join (cost=2.00..8500.00 rows=1000000 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=1000000 width=48)
--   -> Hash (cost=1.50..1.50 rows=50000 width=24)
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50000 width=24)
-- Planning Time: 0.200 ms
-- Execution Time: 1200.000 ms (1.2 segundos!)

-- Problema 3: Sort caro por falta de indice
-- Causa: ORDER BY sem indice correspondente

EXPLAIN ANALYZE
SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 10;

-- Top-N Rowsort (cost=0.00..45800.00 rows=10 width=48) (actual time=1250.000..1250.005 rows=10 loops=1)
--   Sort Key: created_at DESC
--   Sort Method: top-N heapsort  Memory: 25kB
--   Buffers: shared hit=4500
-- Planning Time: 0.100 ms
-- Execution Time: 1250.010 ms

-- Solucao: criar indice
CREATE INDEX idx_orders_created_desc ON orders (created_at DESC);

EXPLAIN ANALYZE
SELECT * FROM orders
ORDER BY created_at DESC
LIMIT 10;

-- Index Scan using idx_orders_created_desc on orders (cost=0.29..8.31 rows=10 width=48)
--   Index Cond: (created_at IS NOT NULL)
-- Planning Time: 0.125 ms
-- Execution Time: 0.035 ms
-- Reducao: 1250ms -> 0.035ms (35.700x mais rapido!)
```

## EXPLAIN em MySQL

### EXPLAIN Basico no MySQL

```sql
-- MySQL usa EXPLAIN para mostrar planos de execucao
-- A sintaxe e ligeiramente diferente do PostgreSQL

-- Exemplo basico:
EXPLAIN SELECT * FROM orders WHERE user_id = 42;

-- Saida:
-- +----+-------------+--------+------------+------+---------------+------+---------+------+------+----------+-------+
-- | id | select_type | table  | partitions | type | possible_keys | key  | key_len | ref  | rows | filtered | Extra |
-- +----+-------------+--------+------------+------+---------------+------+---------+------+------+----------+-------+
-- |  1 | SIMPLE      | orders | NULL       | ref  | idx_user_id   | idx_user_id | 5  | const|  150 |   100.00 | NULL  |
-- +----+-------------+--------+------------+------+---------------+------+---------+------+------+----------+-------+

-- Interpretacao das colunas:
-- id: identificador da query (subqueries tem ids diferentes)
-- select_type: SIMPLE, PRIMARY, SUBQUERY, DERIVED, UNION
-- table: tabela acessada
-- partitions: particoes acessadas
-- type: tipo de acesso (system, const, eq_ref, ref, range, index, ALL)
-- possible_keys: indices que poderiam ser usados
-- key: indice escolhido
-- key_len: tamanho da chave do indice
-- ref: como a coluna e comparada
-- rows: estimativa de linhas
-- filtered: porcentagem de linhas filtradas
-- Extra: informacoes adicionais

-- Tipos de acesso (do melhor para o pior):
-- system: tabela com apenas 1 linha
-- const: query com uma unica linha (PRIMARY KEY ou UNIQUE)
-- eq_ref: JOIN com PRIMARY KEY ou UNIQUE
-- ref: JOIN com indice nao-unique
-- range: busca por range (BETWEEN, >, <, IN)
-- index: full index scan
-- ALL: full table scan (pior caso)

-- EXPLAIN ANALYZE no MySQL 8.0+:
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 42;

-- Saida:
-- -> Index lookup on orders using idx_user_id (user_id=42) (actual time=0.025..0.028 rows=1 loops=1)
--   -> Table scan on orders  (actual time=0.000..0.000 rows=0 loops=1)
-- 
-- EXPLAIN format=tree (MySQL 8.0+):
EXPLAIN FORMAT=TREE SELECT * FROM orders WHERE user_id = 42;

-- Saida:
-- -> Index lookup on orders using idx_user_id (user_id=42) (cost=0.43..8.45 rows=1)
--     (actual time=0.025..0.028 rows=1 loops=1)
```

### EXPLAIN Detalhado no MySQL

```sql
-- EXPLAIN com FORMAT=JSON fornece mais detalhes:
EXPLAIN FORMAT=JSON
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'completed';

-- Saida JSON:
-- {
--   "query_block": {
--     "select_id": 1,
--     "cost_info": {
--       "query_cost": "4520.00"
--     },
--     "nested_loop": [
--       {
--         "table": {
--           "table_name": "o",
--           "access_type": "ALL",
--           "rows_examined_per_scan": 1000000,
--           "rows_produced_per_join": 1000000,
--           "filtered": "80.00",
--           "cost_info": {
--             "read_cost": "3580.00",
--             "eval_cost": "716.00",
--             "prefix_cost": "4296.00",
--             "data_read_per_join": "48000000"
--           },
--           "used_columns": ["order_id", "user_id", "amount", "status"]
--         }
--       },
--       {
--         "table": {
--           "table_name": "u",
--           "access_type": "eq_ref",
--           "possible_keys": ["PRIMARY"],
--           "key": "PRIMARY",
--           "key_length": "4",
--           "ref": ["o.user_id"],
--           "rows": 1,
--           "cost_info": {
--             "read_cost": "0.25",
--             "eval_cost": "0.25",
--             "prefix_cost": "4296.50",
--             "data_read_per_join": "24"
--           },
--           "used_columns": ["user_id", "username"]
--         }
--       }
--     ]
--   }
-- }

-- EXPLAIN com FORMAT=TREE mostra a arvore de operadores:
EXPLAIN FORMAT=TREE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'completed';

-- Saida:
-- -> Nested loop inner join  (cost=4296.50 rows=1000000) (actual time=0.025..45.123 rows=800000 loops=1)
--   -> Table scan on o  (cost=4296.50 rows=1000000) (actual time=0.015..30.456 rows=1000000 loops=1)
--   -> Single-row index lookup on u using PRIMARY (user_id=o.user_id)  (cost=0.25 rows=1) (actual time=0.000..0.000 rows=1 loops=1000000)
-- 
-- Planning time: 0.150 ms
-- Execution time: 45.250 ms

-- Otimizacao baseada no EXPLAIN:
-- 1. Table scan em 'o' (ALL) -> criar indice em status
-- 2. Nested loop -> considerar Hash Join para grandes volumes
-- 3. Rows produzidos -> verificar se estimativas estao corretas
```

### Otimizacao Baseada em EXPLAIN no MySQL

```sql
-- Exemplo completo de otimizacao

-- Query original (lenta):
SELECT
    c.customer_name,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.country = 'Brazil'
AND o.order_date >= '2024-01-01'
GROUP BY c.customer_name
HAVING total_orders > 5
ORDER BY total_amount DESC
LIMIT 10;

-- EXPLAIN ANALYZE:
-- -> Sort (cost=125000.00 rows=1) (actual time=4500.000..4500.005 rows=10 loops=1)
--   -> Filter: (total_orders > 5) (actual time=4450.000..4450.005 rows=10 loops=1)
--     -> Table scan on <temporary> (actual time=4450.000..4450.005 rows=10000 loops=1)
--       -> Aggregate using temporary table (actual time=4400.000..4400.005 rows=10000 loops=1)
--         -> Nested loop inner join (cost=85000.00 rows=500000) (actual time=125.000..4300.000 rows=500000 loops=1)
--           -> Table scan on c (cost=2500.00 rows=50000) (actual time=0.025..125.000 rows=50000 loops=1)
--             Filter: (c.country = 'Brazil')
--           -> Single-row index lookup on o using PRIMARY (customer_id=c.customer_id) (cost=1.50 rows=10) (actual time=0.000..0.000 rows=10 loops=50000)
-- 
-- Planning time: 0.150 ms
-- Execution time: 4500.000 ms (4.5 segundos!)

-- Problemas identificados:
-- 1. Table scan em 'c' com filtro country='Brazil'
-- 2. Nested loop com 50.000 iteracoes
-- 3. Agregacao com tabela temporaria
-- 4. Sort final

-- Solucoes:
-- 1. Criar indice em customers(country)
CREATE INDEX idx_customers_country ON customers (country);

-- 2. Criar indice composto em orders
CREATE INDEX idx_orders_customer_date_status
ON orders (customer_id, order_date, status);

-- 3. Atualizar estatisticas
ANALYZE customers;
ANALYZE orders;

-- Query otimizada:
EXPLAIN ANALYZE
SELECT
    c.customer_name,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.country = 'Brazil'
AND o.order_date >= '2024-01-01'
GROUP BY c.customer_name
HAVING total_orders > 5
ORDER BY total_amount DESC
LIMIT 10;

-- Novo plano:
-- -> Limit: 10 row(s) (actual time=125.000..125.005 rows=10 loops=1)
--   -> Sort: sort_key(total_amount) reverse (actual time=125.000..125.005 rows=10 loops=1)
--     -> Filter: (total_orders > 5) (actual time=120.000..120.005 rows=10 loops=1)
--       -> Table scan on <temporary> (actual time=120.000..120.005 rows=1000 loops=1)
--         -> Aggregate using temporary table (actual time=115.000..115.005 rows=1000 loops=1)
--           -> Nested loop inner join (cost=2.00..12500.00 rows=100000) (actual time=0.025..110.000 rows=100000 loops=1)
--             -> Index lookup on c using idx_customers_country (country='Brazil') (cost=0.25..2500.00 rows=50000) (actual time=0.020..50.000 rows=50000 loops=1)
--             -> Index lookup on o using idx_orders_customer_date_status (customer_id=c.customer_id AND order_date>='2024-01-01') (cost=0.25..0.50 rows=2) (actual time=0.001..0.001 rows=2 loops=50000)
-- 
-- Planning time: 0.150 ms
-- Execution time: 125.000 ms (125 milissegundos!)
-- Reducao: 4500ms -> 125ms (36x mais rapido!)
```

## Query Plan Operators

### Seq Scan (Sequential Scan)

```sql
-- Seq Scan le todas as linhas de uma tabela sequencialmente
-- E o operador mais basico e geralmente mais lento

-- Quando e usado:
-- 1. Tabela pequena (menos que ~10.000 linhas)
-- 2. Filtro retorna grande parte das linhas (>30%)
-- 3. Nao existe indice adequado
-- 4. Optimizer decide que seq scan e mais barato

-- Exemplo:
EXPLAIN ANALYZE SELECT * FROM orders WHERE amount > 100;

-- Seq Scan on orders (cost=0.00..35800.00 rows=800000 width=48)
--   Filter: (amount > 100)
--   Rows Removed by Filter: 200000
-- Planning Time: 0.100 ms
-- Execution Time: 1250.000 ms

-- Custo estimado:
-- start cost: 0.00 (custo de leitura sequencial e baixo)
-- total cost: 35800.00 (leitura de todas as paginas + processamento)
-- rows: 800000 (estimativa de linhas retornadas)
-- width: 48 (largura media das linhas)

-- Para evitar seq scan:
-- 1. Criar indice na coluna filtrada
-- 2. Usar WHERE mais seletivo
-- 3. Atualizar estatisticas (ANALYZE)
-- 4. Considerar particionamento

-- Seq scan pode ser otimo para:
-- - Full table scan para backup/export
-- - Queries que precisam de muitas linhas
-- - Tabelas pequenas onde overhead de indice nao compensa
```

### Index Scan

```sql
-- Index Scan usa indice para encontrar linhas especificas
-- Muito mais rapido que seq scan para queries seletivas

-- Tipos de Index Scan:
-- 1. Index Scan: le indice e depois as linhas da tabela
-- 2. Index Only Scan: le apenas do indice (se cobre todas as colunas)
-- 3. Bitmap Index Scan: cria bitmap de linhas e depois le

-- Index Scan basico:
CREATE INDEX idx_orders_user ON orders (user_id);

EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 42;

-- Index Scan using idx_orders_user on orders (cost=0.43..8.45 rows=1 width=48)
--   Index Cond: (user_id = 42)
-- Planning Time: 0.125 ms
-- Execution Time: 0.089 ms

-- Index Only Scan (covering index):
CREATE INDEX idx_orders_user_amount ON orders (user_id, amount);

EXPLAIN ANALYZE SELECT user_id, amount FROM orders WHERE user_id = 42;

-- Index Only Scan using idx_orders_user_amount on orders (cost=0.43..4.45 rows=1 width=12)
--   Index Cond: (user_id = 42)
-- Planning Time: 0.125 ms
-- Execution Time: 0.025 ms (ainda mais rapido!)

-- Bitmap Index Scan:
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id BETWEEN 100 AND 200;

-- Bitmap Heap Scan on orders (cost=2.00..1250.00 rows=1500 width=48)
--   Recheck Cond: (user_id BETWEEN 100 AND 200)
--   Heap Blocks: exact=1250
--   -> Bitmap Index Scan on idx_orders_user (cost=0.00..1.50 rows=1500 width=0)
--         Index Cond: (user_id BETWEEN 100 AND 200)
-- Planning Time: 0.150 ms
-- Execution Time: 25.000 ms

-- Bitmap Index Scan cria bitmap de todos os ROWIDs que satisfazem o indice
-- Depois faz heap scan apenas nas paginas necessarias
-- Otimo para ranges que retornam muitas linhas mas nao todas
```

### Hash Join

```sql
-- Hash Join e eficiente para joins de tabelas medias/grandes
-- Cria hash table de uma tabela e depois faz probe na outra

-- Quando e usado:
-- 1. Join entre tabela grande e tabela pequena
-- 2. Nao ha indice na coluna de join
-- 3. Join e igualdade (=)

-- Exemplo:
EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- Hash Join (cost=2.00..8500.00 rows=1000000 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=1000000 width=48)
--   -> Hash (cost=1.50..1.50 rows=50000 width=24)
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50000 width=24)
-- Planning Time: 0.200 ms
-- Execution Time: 1200.000 ms

-- Processo do Hash Join:
-- 1. Build phase: cria hash table da tabela menor (users)
-- 2. Scan phase: le tabela maior (orders) e faz probe na hash table
-- 3. Output: retorna linhas que combinam

-- Parametros que afetam Hash Join:
-- work_mem: memoria para hash table (padrao 4MB)
-- hash_mem_multiplier: multiplicador de memoria (padrao 1.0)

-- Se hash table nao cabe em memoria:
-- Hash Join (cost=2.00..12500.00 rows=1000000 width=64)
--   Hash Cond: (o.user_id = u.user_id)
--   -> Seq Scan on orders o (cost=0.00..3580.00 rows=1000000 width=48)
--   -> Hash (cost=1.50..1.50 rows=50000 width=24)
--         Buckets: 131072  Batches: 8  Memory Usage: 8193kB
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50000 width=24)
-- Planning Time: 0.200 ms
-- Execution Time: 2500.000 ms (mais lento por batch overflow)

-- Para evitar batch overflow:
-- 1. Aumentar work_mem: SET work_mem = '64MB';
-- 2. Criar indice na coluna de join
-- 3. Reduzir tamanho da tabela (filtros, particionamento)
```

### Merge Join

```sql
-- Merge Join e eficiente quando os dados ja estao ordenados
- Requer que ambas as tabelas estejam ordenadas pela coluna de join

-- Quando e usado:
-- 1. Ambas as tabelas sao grandes
-- 2. Dados estao ordenados (por indice ou SORT)
-- 3. Join e igualdade (=)

-- Exemplo:
CREATE INDEX idx_orders_user ON orders (user_id);
CREATE INDEX idx_users_id ON users (user_id);

EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- Merge Join (cost=0.87..12500.00 rows=1000000 width=64)
--   Merge Cond: (o.user_id = u.user_id)
--   -> Index Scan using idx_orders_user on orders o (cost=0.43..8500.00 rows=1000000 width=48)
--   -> Index Scan using idx_users_id on users u (cost=0.28..1.50 rows=50000 width=24)
-- Planning Time: 0.150 ms
-- Execution Time: 1500.000 ms

-- Processo do Merge Join:
-- 1. Ambas as tabelas sao ordenadas pelo indice
-- 2. Ponteiros avancam em ambas as tabelas
-- 3. Compara chaves e outputa combinacoes
-- 4. Completo quando uma tabela acaba

-- Merge Join vs Hash Join:
-- Merge Join: O(n + m) se dados ja ordenados
-- Hash Join: O(n + m) mas com overhead de hash
-- Merge Join: bom para dados ordenados
-- Hash Join: bom para dados nao ordenados

-- Merge Join pode usar SORT se nao houver indice:
EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- Merge Join (cost=0.87..18500.00 rows=1000000 width=64)
--   Merge Cond: (o.user_id = u.user_id)
--   -> Sort (cost=4500.00..4750.00 rows=1000000 width=48)
--         Sort Key: o.user_id
--         -> Seq Scan on orders o (cost=0.00..3580.00 rows=1000000 width=48)
--   -> Sort (cost=1.25..1.50 rows=50000 width=24)
--         Sort Key: u.user_id
--         -> Seq Scan on users u (cost=0.00..1.50 rows=50000 width=24)
-- Planning Time: 0.200 ms
-- Execution Time: 3500.000 ms

-- Sort e caro: O(n log n)
-- Se houver indice, Merge Join evita o SORT
```

### Nested Loop

```sql
-- Nested Loop para cada linha da tabela externa, busca linhas na tabela interna
-- E o join mais simples mas pode ser O(n*m)

-- Quando e usado:
-- 1. Tabela externa e pequena
-- 2. Tabela interna tem indice eficiente
-- 3. Join com poucas linhas

-- Exemplo:
EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.user_id = 42;

-- Nested Loop (cost=0.87..16.90 rows=10 width=64)
--   -> Index Scan using idx_orders_user on orders o (cost=0.43..8.45 rows=10 width=48)
--         Index Cond: (user_id = 42)
--   -> Index Scan using idx_users_id on users u (cost=0.28..0.83 rows=1 width=24)
--         Index Cond: (user_id = 42)
-- Planning Time: 0.125 ms
-- Execution Time: 0.150 ms

-- Nested Loop e otimo quando:
-- 1. Tabela externa e muito pequena (1-10 linhas)
-- 2. Tabela interna tem indice na coluna de join
-- 3. Cada linha da externa encontra poucas linhas na interna

-- Nested Loop se torna lento quando:
-- 1. Tabela externa e grande
-- 2. Tabela interna nao tem indice
-- 3. Muitas linhas por combinação

-- Nested Loop vs Hash Join:
-- Nested Loop: O(n*m) no pior caso
-- Hash Join: O(n+m) sempre
-- Nested Loop: bom para poucas linhas
-- Hash Join: bom para muitas linhas

-- Para evitar Nested Loop lento:
-- 1. Criar indice na tabela interna
-- 2. Usar filtros para reduzir tabela externa
-- 3. Considerar Hash Join ou Merge Join
-- 4. Ajustar work_mem para Hash Join
```

## Hint Usage

### Hints no PostgreSQL

```sql
-- PostgreSQL nao tem hints nativas no SQL
-- Mas podemos influenciar o otimizador de outras formas

-- 1. Usar CTEs para materializar subconjuntos
WITH active_users AS MATERIALIZED (
    SELECT user_id FROM users WHERE status = 'active'
)
SELECT o.* FROM orders o
JOIN active_users au ON o.user_id = au.user_id;

-- 2. Usar subqueries para forcar ordem
SELECT * FROM orders o
WHERE o.user_id IN (SELECT user_id FROM users WHERE status = 'active');

-- 3. Usar pg_hint_plan (extensao)
-- Instalar: CREATE EXTENSION pg_hint_plan;
SET pg_hint_plan.enable_hint = on;

-- Usar hints:
SELECT /*+ SeqScan(orders) */ * FROM orders WHERE status = 'completed';
SELECT /*+ IndexScan(orders idx_orders_status) */ * FROM orders WHERE status = 'completed';
SELECT /*+ HashJoin(orders users) */ o.*, u.username FROM orders o JOIN users u ON o.user_id = u.user_id;

-- 4. Ajustar configuracoes temporariamente
SET enable_seqscan = off;
SET enable_nestloop = off;
SET work_mem = '256MB';

-- Executar query
EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'completed';

-- Restaurar configuracoes
RESET enable_seqscan;
RESET enable_nestloop;
RESET work_mem;

-- 5. Usar funcoes de sistema para influenciar
-- pg_stat_statements para identificar queries lentas
CREATE EXTENSION pg_stat_statements;

SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Hints no MySQL

```sql
-- MySQL suporta hints no SQL

-- 1. Index hints (FORCE INDEX, USE INDEX, IGNORE INDEX)
SELECT * FROM orders FORCE INDEX (idx_orders_status)
WHERE status = 'completed';

SELECT * FROM orders USE INDEX (idx_orders_user)
WHERE user_id = 42;

SELECT * FROM orders IGNORE INDEX (idx_orders_status)
WHERE status = 'completed';

-- 2. Join hints (STRAIGHT_JOIN, JOIN ORDER)
SELECT STRAIGHT_JOIN o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- 3. Table hints (HIGH_PRIORITY, LOW_PRIORITY, QUICK)
SELECT HIGH_PRIORITY * FROM orders WHERE status = 'completed';
SELECT LOW_PRIORITY * FROM orders WHERE status = 'completed';
SELECT QUICK * FROM orders WHERE status = 'completed';

-- 4. optimizer_switch para desabilitar otimizacoes
SET optimizer_switch = 'hash_join=off';
SET optimizer_switch = 'merge_join=off';
SET optimizer_switch = 'nested_loop=off';

-- Executar query
EXPLAIN SELECT * FROM orders WHERE status = 'completed';

-- Restaurar
SET optimizer_switch = 'default';

-- 5. SQL_NO_CACHE para evitar cache
SELECT SQL_NO_CACHE * FROM orders WHERE status = 'completed';

-- 6. SQL_CACHE para forcar cache
SELECT SQL_CACHE * FROM orders WHERE status = 'completed';

-- Exemplo completo de otimizacao com hints:
EXPLAIN SELECT STRAIGHT_JOIN
    o.order_id,
    o.amount,
    u.username
FROM orders o
FORCE INDEX (idx_orders_status)
JOIN users u ON o.user_id = u.user_id
WHERE o.status = 'pending'
AND o.amount > 100;
```

## Query Rewriting Patterns

### Padroes de Rewriting

```sql
-- 1. Subquery para JOIN
-- Antes (subquery correlacionada):
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o
    WHERE o.user_id = u.user_id
    AND o.status = 'completed'
);

-- Depois (JOIN):
SELECT DISTINCT u.* FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE o.status = 'completed';

-- 2. IN para JOIN
-- Antes:
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE active = true
);

-- Depois:
SELECT p.* FROM products p
JOIN categories c ON p.category_id = c.category_id
WHERE c.active = true;

-- 3. NOT EXISTS para LEFT JOIN
-- Antes:
SELECT * FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.user_id
);

-- Depois:
SELECT u.* FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IS NULL;

-- 4. Subquery scalar para JOIN
-- Antes:
SELECT
    u.username,
    (SELECT MAX(order_date) FROM orders WHERE user_id = u.user_id) as last_order
FROM users u;

-- Depois:
SELECT u.username, lo.last_order
FROM users u
LEFT JOIN LATERAL (
    SELECT MAX(order_date) as last_order
    FROM orders
    WHERE user_id = u.user_id
) lo ON true;

-- 5. UNION para UNION ALL (quando nao ha duplicatas)
-- Antes:
SELECT user_id FROM orders WHERE status = 'completed'
UNION
SELECT user_id FROM orders WHERE status = 'pending';

-- Depois (se nao ha duplicatas):
SELECT user_id FROM orders WHERE status = 'completed'
UNION ALL
SELECT user_id FROM orders WHERE status = 'pending';

-- 6. GROUP BY para window function
-- Antes:
SELECT
    user_id,
    order_date,
    amount,
    (SELECT AVG(amount) FROM orders o2 WHERE o2.user_id = o1.user_id) as avg_amount
FROM orders o1;

-- Depois:
SELECT
    user_id,
    order_date,
    amount,
    AVG(amount) OVER (PARTITION BY user_id) as avg_amount
FROM orders;

-- 7. DELETE com subquery para JOIN
-- Antes:
DELETE FROM order_items
WHERE order_id IN (
    SELECT order_id FROM orders WHERE status = 'cancelled'
);

-- Depois:
DELETE oi FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'cancelled';

-- 8. UPDATE com subquery para JOIN
-- Antes:
UPDATE orders
SET status = 'expired'
WHERE order_date < '2024-01-01'
AND user_id IN (
    SELECT user_id FROM users WHERE status = 'inactive'
);

-- Depois:
UPDATE orders o
JOIN users u ON o.user_id = u.user_id
SET o.status = 'expired'
WHERE o.order_date < '2024-01-01'
AND u.status = 'inactive';
```

### Rewriting para Performance

```sql
-- 1. Usar覆盖索引 (covering index)
-- Antes:
SELECT user_id, status, amount FROM orders WHERE user_id = 42;

-- Depois (criar covering index):
CREATE INDEX idx_orders_covering ON orders (user_id, status, amount);
-- Agora a query usa Index Only Scan

-- 2. Usar filtro mais seletivo primeiro
-- Antes:
SELECT * FROM orders
WHERE created_at > '2024-01-01'
AND user_id = 42;

-- Depois (reordenar WHERE):
SELECT * FROM orders
WHERE user_id = 42
AND created_at > '2024-01-01';

-- 3. Evitar funcoes na coluna filtrada
-- Antes:
SELECT * FROM orders
WHERE DATE(created_at) = '2024-01-15';

-- Depois:
SELECT * FROM orders
WHERE created_at >= '2024-01-15'
AND created_at < '2024-01-16';

-- 4. Usar EXISTS em vez de COUNT
-- Antes:
SELECT * FROM users u
WHERE (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) > 0;

-- Depois:
SELECT * FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.user_id);

-- 5. Evitar SELECT *
-- Antes:
SELECT * FROM orders WHERE user_id = 42;

-- Depois:
SELECT order_id, status, amount FROM orders WHERE user_id = 42;

-- 6. Usar LIMIT com ORDER BY
-- Antes:
SELECT * FROM orders ORDER BY created_at DESC;

-- Depois:
SELECT * FROM orders ORDER BY created_at DESC LIMIT 100;

-- 7. Usar batch operations
-- Antes:
INSERT INTO orders (user_id, amount) VALUES (1, 100);
INSERT INTO orders (user_id, amount) VALUES (2, 200);
INSERT INTO orders (user_id, amount) VALUES (3, 300);

-- Depois:
INSERT INTO orders (user_id, amount) VALUES
(1, 100),
(2, 200),
(3, 300);

-- 8. Usar CTEs para queries complexas
-- Antes:
SELECT * FROM (
    SELECT user_id, COUNT(*) as cnt
    FROM orders
    GROUP BY user_id
) sub
WHERE cnt > 5;

-- Depois:
WITH order_counts AS (
    SELECT user_id, COUNT(*) as cnt
    FROM orders
    GROUP BY user_id
)
SELECT * FROM order_counts WHERE cnt > 5;
```

## Caching Strategies

### Niveis de Cache

```sql
-- 1. Buffer Cache (shared_buffers no PostgreSQL)
-- Armazena paginas de dados em memoria
-- Configurar em postgresql.conf:
-- shared_buffers = '4GB' (25% da RAM total)
-- effective_cache_size = '16GB' (75% da RAM total)

-- Ver uso do buffer cache:
SELECT
    relname,
    pg_size_pretty(pg_relation_size(relid)) as table_size,
    heap_blks_hit,
    heap_blks_read,
    ROUND(heap_blks_hit::numeric / (heap_blks_hit + heap_blks_read) * 100, 2) as hit_ratio
FROM pg_statio_user_tables
WHERE heap_blks_hit + heap_blks_read > 0
ORDER BY hit_ratio;

-- 2. Query Cache (MySQL)
-- MySQL 8.0 removeu query cache por problemas de concorrencia
-- Em versoes anteriores:
-- query_cache_type = 1
-- query_cache_size = 64MB

-- Verificar se query cache esta habilitado:
SHOW VARIABLES LIKE 'query_cache%';

-- 3. Prepared Statement Cache
-- Armazena planos de execucao para queries preparadas

-- PostgreSQL:
PREPARE find_user (INTEGER) AS
SELECT * FROM users WHERE user_id = $1;

EXECUTE find_user(42);
-- Plano e cacheado e reusado

-- MySQL:
PREPARE find_user FROM
'SELECT * FROM users WHERE user_id = ?';

SET @user_id = 42;
EXECUTE find_user USING @user_id;

-- 4. Materialized View Cache
-- Armazena resultados pre-calculados

CREATE MATERIALIZED VIEW daily_sales AS
SELECT
    DATE(order_date) as sale_date,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM orders
GROUP BY DATE(order_date);

-- Atualizar quando necessario
REFRESH MATERIALIZED VIEW daily_sales;

-- 5. Connection Pool Cache (PgBouncer, ProxySQL)
-- Gerencia conexoes e reutiliza pools

-- PgBouncer configuracao:
-- [databases]
-- mydb = host=localhost port=5432 dbname=mydb

-- [pgbouncer]
-- pool_mode = transaction
-- max_client_conn = 1000
-- default_pool_size = 20

-- Verificar conexoes:
SHOW POOLS;
SHOW CLIENTS;
SHOW SERVERS;
```

### Estrategias de Cache

```sql
-- 1. Cache por tempo (TTL)
-- Usar coluna updated_at para invalidacao

-- PostgreSQL:
CREATE TABLE cache_entries (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Buscar cache valido
SELECT value FROM cache_entries
WHERE key = 'user_42_profile'
AND expires_at > NOW();

-- Limpar cache expirado
DELETE FROM cache_entries WHERE expires_at < NOW();

-- 2. Cache por evento (invalidacao)
-- Usar triggers para invalidar cache quando dados mudam

CREATE OR REPLACE FUNCTION invalidate_user_cache()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM cache_entries WHERE key = 'user_' || NEW.user_id || '_profile';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_invalidate_user_cache
AFTER UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION invalidate_user_cache();

-- 3. Cache write-through
-- Atualizar cache e banco na mesma transacao

BEGIN;
UPDATE users SET name = 'New Name' WHERE user_id = 42;
UPDATE cache_entries SET value = '{"name": "New Name"}'::jsonb
WHERE key = 'user_42_profile';
COMMIT;

-- 4. Cache write-behind
-- Atualizar cache primeiro, banco depois

-- Atualizar cache
UPDATE cache_entries SET value = '{"name": "New Name"}'::jsonb
WHERE key = 'user_42_profile';

-- Atualizar banco asincrono
INSERT INTO pending_updates (table_name, record_id, operation, data)
VALUES ('users', 42, 'UPDATE', '{"name": "New Name"}'::jsonb);

-- 5. Cache read-through
-- Buscar do cache, se miss, buscar do banco e atualizar cache

-- Funcao para buscar com cache
CREATE OR REPLACE FUNCTION get_user_with_cache(p_user_id INTEGER)
RETURNS JSONB AS $$
DECLARE
    cached_value JSONB;
BEGIN
    -- Tentar cache
    SELECT value INTO cached_value
    FROM cache_entries
    WHERE key = 'user_' || p_user_id || '_profile'
    AND expires_at > NOW();
    
    IF cached_value IS NOT NULL THEN
        RETURN cached_value;
    END IF;
    
    -- Cache miss - buscar do banco
    SELECT row_to_json(u) INTO cached_value
    FROM users u
    WHERE user_id = p_user_id;
    
    -- Armazenar no cache
    INSERT INTO cache_entries (key, value, expires_at)
    VALUES ('user_' || p_user_id || '_profile', cached_value, NOW() + INTERVAL '1 hour')
    ON CONFLICT (key) DO UPDATE SET
        value = EXCLUDED.value,
        expires_at = EXCLUDED.expires_at;
    
    RETURN cached_value;
END;
$$ LANGUAGE plpgsql;
```

## Prepared Statements Performance

### Vantagens dos Prepared Statements

```sql
-- 1. Parse once, execute many
-- Evita parsing repetido da mesma query

-- PostgreSQL:
PREPARE find_orders (INTEGER, TIMESTAMP) AS
SELECT * FROM orders
WHERE user_id = $1
AND created_at > $2;

-- Executar multiplas vezes
EXECUTE find_orders(42, '2024-01-01');
EXECUTE find_orders(43, '2024-01-01');
EXECUTE find_orders(44, '2024-01-01');
-- Parsing feito apenas uma vez

-- 2. Previne SQL injection
-- Parametros sao tratados como dados, nao como codigo

-- Perigoso (SQL injection):
SELECT * FROM users WHERE username = '' OR ''='';

-- Seguro (prepared statement):
PREPARE find_user (VARCHAR) AS
SELECT * FROM users WHERE username = $1;
EXECUTE find_user('admin'' OR ''1''=''1');
-- A string e tratada como valor literal

-- 3. Plan caching
-- PostgreSQL armazena planos para prepared statements

-- Verificar plan cache:
SELECT
    name,
    statement,
    plans,
    calls,
    total_time
FROM pg_prepared_statements;

-- 4. Reducao de overhead de rede
-- Clientes podem enviar parametros separados

-- MySQL prepared statement:
PREPARE find_user FROM
'SELECT * FROM users WHERE user_id = ? AND status = ?';

SET @user_id = 42;
SET @status = 'active';
EXECUTE find_user USING @user_id, @status;

-- 5. Melhor performance para queries repetidas
-- Benchmark tipico:
-- Query normal: 10ms (parse: 2ms, plan: 1ms, execute: 7ms)
-- Prepared: 7ms (parse: 0ms, plan: 0ms, execute: 7ms)
-- Economia: 30% para queries repetidas
```

### Cuidados com Prepared Statements

```sql
-- 1. Parameter sniffing
-- O plano e cacheado baseado nos primeiros parametros
-- Se os parametros seguintes tiverem distribuicao diferente, plano pode ser ruim

-- Exemplo problematico:
PREPARE find_orders (VARCHAR) AS
SELECT * FROM orders WHERE status = $1;

-- Primeira execucao: status = 'completed' (80% das linhas)
EXECUTE find_orders('completed');
-- Plano: Seq Scan (otimo para 80%)

-- Segunda execucao: status = 'cancelled' (1% das linhas)
EXECUTE find_orders('cancelled');
-- Plano: Seq Scan (ruim para 1%!)
-- Deveria ser Index Scan

-- Solucao: usar WITH RECOMPILE (SQL Server) ou pg_hint_plan

-- 2. Plan cache invalidation
-- Mudancas na tabela invalidam planos cacheados

-- Exemplo:
PREPARE find_user (INTEGER) AS
SELECT * FROM users WHERE user_id = $1;

-- Plano cacheado
EXECUTE find_user(42);

-- Criar indice
CREATE INDEX idx_users_id ON users (user_id);

-- Plano anterior ainda e valido
-- Mas nao usa o novo indice automaticamente

-- Solucao: re-preparar a query
DEALLOCATE find_user;
PREPARE find_user (INTEGER) AS
SELECT * FROM users WHERE user_id = $1;
EXECUTE find_user(42); -- Agora usa o indice

-- 3. Memory leak de prepared statements
-- Prepared statements nao sao liberados automaticamente

-- Verificar prepared statements abertos:
SELECT * FROM pg_prepared_statements;

-- Liberar todos:
DEALLOCATE ALL;

-- Liberar especifico:
DEALLOCATE find_user;

-- 4. Prepared statements e transacoes
-- Alguns SGBDs ligam prepared statements a transacoes

-- PostgreSQL: prepared statements persistem entre transacoes
-- MySQL: prepared statements sao liberados ao fechar conexao

-- 5. Prepared statements e procedures
-- Procedures podem ter prepared statements internos

CREATE OR REPLACE FUNCTION find_active_users(p_status VARCHAR)
RETURNS TABLE(user_id INTEGER, username VARCHAR) AS $$
BEGIN
    RETURN QUERY
    EXECUTE 'SELECT user_id, username FROM users WHERE status = $1'
    USING p_status;
END;
$$ LANGUAGE plpgsql;
```

## Exemplo: Otimizar Query Lenta Step-by-Step

### Identificando o Problema

```sql
-- Query original que leva 45 segundos:
SELECT
    c.customer_name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount,
    MAX(o.order_date) as last_order_date
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil'
AND o.order_date >= '2024-01-01'
AND p.category = 'Electronics'
GROUP BY c.customer_id, c.customer_name, c.email
HAVING COUNT(o.order_id) > 3
ORDER BY total_amount DESC
LIMIT 20;

-- Step 1: Analisar o plano de execucao
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    c.customer_name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount,
    MAX(o.order_date) as last_order_date
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil'
AND o.order_date >= '2024-01-01'
AND p.category = 'Electronics'
GROUP BY c.customer_id, c.customer_name, c.email
HAVING COUNT(o.order_id) > 3
ORDER BY total_amount DESC
LIMIT 20;

-- Saida:
-- Limit (cost=185000.00..185000.05 rows=20 width=48) (actual time=45000.000..45000.005 rows=20 loops=1)
--   -> Sort: sort_key(total_amount) DESC (actual time=45000.000..45000.005 rows=20 loops=1)
--     -> Filter: (COUNT(o.order_id) > 3) (actual time=44500.000..44500.005 rows=1500 loops=1)
--       -> GroupAggregate (actual time=44000.000..44000.005 rows=150000 loops=1)
--         -> Sort: sort_key(c.customer_id, c.customer_name, c.email) (actual time=43500.000..43750.000 rows=500000 loops=1)
--           -> Hash Join (cost=2.00..125000.00 rows=500000 width=48) (actual time=0.025..42000.000 rows=500000 loops=1)
--             Hash Cond: (o.customer_id = c.customer_id)
--             -> Hash Join (cost=1.50..85000.00 rows=500000 width=32) (actual time=0.020..38000.000 rows=500000 loops=1)
--               Hash Cond: (oi.order_id = o.order_id)
--               -> Seq Scan on order_items oi (cost=0.00..25000.00 rows=5000000 width=16) (actual time=0.010..15000.000 rows=5000000 loops=1)
--               -> Hash (cost=1.25..1.25 rows=100000 width=24) (actual time=0.008..0.009 rows=100000 loops=1)
--                 -> Seq Scan on orders o (cost=0.00..5000.00 rows=100000 width=24) (actual time=0.005..3500.000 rows=100000 loops=1)
--                   Filter: (order_date >= '2024-01-01')
--                   Rows Removed by Filter: 900000
--             -> Hash (cost=1.00..1.00 rows=50000 width=32) (actual time=0.005..0.006 rows=50000 loops=1)
--               -> Seq Scan on customers c (cost=0.00..1.00 rows=50000 width=32) (actual time=0.003..2500.000 rows=50000 loops=1)
--                 Filter: (country = 'Brazil')
--                 Rows Removed by Filter: 200000
-- Planning Time: 0.250 ms
-- Execution Time: 45000.000 ms

-- Step 2: Identificar gargalos
-- 1. Seq Scan em order_items (5M linhas) - MUITO CARO
-- 2. Hash Join com 500K linhas - CARO
-- 3. Sort para GROUP BY - CARO
-- 4. Filter removendo 200K linhas de customers - MUITO SELETIVO
-- 5. Filter removendo 900K linhas de orders - MUITO SELETIVO

-- Step 3: Verificar estatisticas
SELECT
    relname,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE relname IN ('customers', 'orders', 'order_items', 'products');

-- Resultado:
-- customers: 250000 linhas, last_analyze: 2023-01-01 (desatualizado!)
-- orders: 1000000 linhas, last_analyze: 2023-06-01 (desatualizado!)
-- order_items: 5000000 linhas, last_analyze: 2023-06-01 (desatualizado!)
-- products: 10000 linhas, last_analyze: 2023-06-01 (desatualizado!)

-- Step 4: Atualizar estatisticas
ANALYZE customers;
ANALYZE orders;
ANALYZE order_items;
ANALYZE products;
```

### Implementando Otimizacoes

```sql
-- Step 5: Criar indices para filtros seletivos
-- customers.country (retorna 20% das linhas)
CREATE INDEX idx_customers_country ON customers (country);

-- orders.order_date (retorna 10% das linhas)
CREATE INDEX idx_orders_date ON orders (order_date);

-- products.category (retorna 5% das linhas)
CREATE INDEX idx_products_category ON products (category);

-- Step 6: Criar indices compostos para joins
-- orders.customer_id (join com customers)
CREATE INDEX idx_orders_customer ON orders (customer_id);

-- order_items.order_id (join com orders)
CREATE INDEX idx_order_items_order ON order_items (order_id);

-- order_items.product_id (join com products)
CREATE INDEX idx_order_items_product ON order_items (product_id);

-- Step 7: Criar covering index para a query
-- Para evitar accesso à tabela orders
CREATE INDEX idx_orders_covering ON orders (order_date, customer_id, amount, order_id);

-- Para evitar accesso à tabela order_items
CREATE INDEX idx_order_items_covering ON order_items (order_id, product_id);

-- Step 8: Analisar novamente
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    c.customer_name,
    c.email,
    COUNT(o.order_id) as total_orders,
    SUM(o.amount) as total_amount,
    MAX(o.order_date) as last_order_date
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE c.country = 'Brazil'
AND o.order_date >= '2024-01-01'
AND p.category = 'Electronics'
GROUP BY c.customer_id, c.customer_name, c.email
HAVING COUNT(o.order_id) > 3
ORDER BY total_amount DESC
LIMIT 20;

-- Novo plano:
-- Limit (cost=12500.00..12500.05 rows=20 width=48) (actual time=125.000..125.005 rows=20 loops=1)
--   -> Sort: sort_key(total_amount) DESC (actual time=125.000..125.005 rows=20 loops=1)
--     -> Filter: (COUNT(o.order_id) > 3) (actual time=120.000..120.005 rows=1500 loops=1)
--       -> GroupAggregate (actual time=115.000..115.005 rows=150000 loops=1)
--         -> Sort: sort_key(c.customer_id, c.customer_name, c.email) (actual time=110.000..112.500 rows=500000 loops=1)
--           -> Nested Loop (cost=2.00..12500.00 rows=500000 width=48) (actual time=0.025..100.000 rows=500000 loops=1)
--             -> Nested Loop (cost=1.50..8500.00 rows=500000 width=32) (actual time=0.020..80.000 rows=500000 loops=1)
--               -> Index Scan using idx_order_items_product on order_items oi (cost=0.43..25000.00 rows=250000 width=16) (actual time=0.010..50.000 rows=250000 loops=1)
--                 Filter: (p.category = 'Electronics')
--               -> Index Scan using idx_orders_covering on orders o (cost=0.43..0.85 rows=2) (actual time=0.001..0.001 rows=2 loops=250000)
--                 Index Cond: (order_id = oi.order_id)
--             -> Index Scan using idx_customers_country on customers c (cost=0.25..0.50 rows=1) (actual time=0.001..0.001 rows=1 loops=500000)
--               Index Cond: (customer_id = o.customer_id)
--               Filter: (country = 'Brazil')
-- Planning Time: 0.250 ms
-- Execution Time: 125.000 ms

-- Step 9: Melhorias adicionais
-- 1. Usar CTE para materializar filtro de customers
WITH brazil_customers AS (
    SELECT customer_id, customer_name, email
    FROM customers
    WHERE country = 'Brazil'
),
recent_orders AS (
    SELECT order_id, customer_id, amount, order_date
    FROM orders
    WHERE order_date >= '2024-01-01'
),
electronics_items AS (
    SELECT oi.order_id, oi.product_id
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    WHERE p.category = 'Electronics'
)
SELECT
    bc.customer_name,
    bc.email,
    COUNT(ro.order_id) as total_orders,
    SUM(ro.amount) as total_amount,
    MAX(ro.order_date) as last_order_date
FROM brazil_customers bc
JOIN recent_orders ro ON bc.customer_id = ro.customer_id
JOIN electronics_items ei ON ro.order_id = ei.order_id
GROUP BY bc.customer_id, bc.customer_name, bc.email
HAVING COUNT(ro.order_id) > 3
ORDER BY total_amount DESC
LIMIT 20;

-- Step 10: Verificar resultado final
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
WITH brazil_customers AS MATERIALIZED (
    SELECT customer_id, customer_name, email
    FROM customers
    WHERE country = 'Brazil'
),
recent_orders AS MATERIALIZED (
    SELECT order_id, customer_id, amount, order_date
    FROM orders
    WHERE order_date >= '2024-01-01'
),
electronics_items AS MATERIALIZED (
    SELECT oi.order_id, oi.product_id
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    WHERE p.category = 'Electronics'
)
SELECT
    bc.customer_name,
    bc.email,
    COUNT(ro.order_id) as total_orders,
    SUM(ro.amount) as total_amount,
    MAX(ro.order_date) as last_order_date
FROM brazil_customers bc
JOIN recent_orders ro ON bc.customer_id = ro.customer_id
JOIN electronics_items ei ON ro.order_id = ei.order_id
GROUP BY bc.customer_id, bc.customer_name, bc.email
HAVING COUNT(ro.order_id) > 3
ORDER BY total_amount DESC
LIMIT 20;

-- Resultado final:
-- Limit (cost=1250.00..1250.05 rows=20 width=48) (actual time=125.000..125.005 rows=20 loops=1)
--   -> Sort: sort_key(total_amount) DESC (actual time=125.000..125.005 rows=20 loops=1)
--     -> Filter: (COUNT(ro.order_id) > 3) (actual time=120.000..120.005 rows=1500 loops=1)
--       -> GroupAggregate (actual time=115.000..115.005 rows=150000 loops=1)
--         -> Sort: sort_key(bc.customer_id, bc.customer_name, bc.email) (actual time=110.000..112.500 rows=500000 loops=1)
--           -> Hash Join (cost=2.00..1250.00 rows=500000 width=48) (actual time=0.025..100.000 rows=500000 loops=1)
--             Hash Cond: (ro.customer_id = bc.customer_id)
--             -> Hash Join (cost=1.50..850.00 rows=500000 width=32) (actual time=0.020..80.000 rows=500000 loops=1)
--               Hash Cond: (ei.order_id = ro.order_id)
--               -> Hash (cost=1.00..1.00 rows=250000 width=16) (actual time=0.010..0.011 rows=250000 loops=1)
--                 -> Seq Scan on electronics_items ei (cost=0.00..1.00 rows=250000 width=16) (actual time=0.005..50.000 rows=250000 loops=1)
--               -> Hash (cost=1.25..1.25 rows=100000 width=24) (actual time=0.008..0.009 rows=100000 loops=1)
--                 -> Seq Scan on recent_orders ro (cost=0.00..1.25 rows=100000 width=24) (actual time=0.005..35.000 rows=100000 loops=1)
--             -> Hash (cost=1.00..1.00 rows=50000 width=32) (actual time=0.005..0.006 rows=50000 loops=1)
--               -> Seq Scan on brazil_customers bc (cost=0.00..1.00 rows=50000 width=32) (actual time=0.003..25.000 rows=50000 loops=1)
-- Planning Time: 0.250 ms
-- Execution Time: 125.000 ms

-- Resultado:
-- Antes: 45.000 ms (45 segundos)
-- Depois: 125 ms (0.125 segundos)
-- Melhoria: 360x mais rapido!
```

### Resumo da Otimizacao

```sql
-- Passos realizados:
-- 1. Analisar plano de execucao com EXPLAIN ANALYZE
-- 2. Identificar gargalos (seq scans, joins caros, sorts)
-- 3. Verificar e atualizar estatisticas (ANALYZE)
-- 4. Criar indices para filtros seletivos
-- 5. Criar covering indices para evitar accesso às tabelas
-- 6. Usar CTEs para materializar subconjuntos
-- 7. Reavaliar plano apos otimizacoes

-- Indices criados:
CREATE INDEX idx_customers_country ON customers (country);
CREATE INDEX idx_orders_date ON orders (order_date);
CREATE INDEX idx_products_category ON products (category);
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_order_items_order ON order_items (order_id);
CREATE INDEX idx_order_items_product ON order_items (product_id);
CREATE INDEX idx_orders_covering ON orders (order_date, customer_id, amount, order_id);
CREATE INDEX idx_order_items_covering ON order_items (order_id, product_id);

-- Estatisticas atualizadas:
ANALYZE customers;
ANALYZE orders;
ANALYZE order_items;
ANALYZE products;

-- Query reescrita com CTEs para melhor materializacao

-- Resultado final: 360x mais rapido (45s -> 125ms)
```

## Parallel Query Execution

### Configuracao de Paralelismo

```sql
-- PostgreSQL suporta execucao paralela de queries desde a versao 9.6
-- O paralelismo acelera queries que processam muitos dados

-- Configuracoes no postgresql.conf:
-- max_parallel_workers_per_gather = 2  (workers por operacao)
-- max_parallel_workers = 8              (total de workers)
-- max_parallel_maintenance_workers = 4  (para CREATE INDEX)
-- parallel_tuple_cost = 0.01           (custo por tupla transferida)
-- parallel_setup_cost = 1000           (custo de setup do worker)
-- min_parallel_table_scan_size = 8MB   (tamanho minimo para paralelizar)
-- min_parallel_index_scan_size = 512kB

-- Verificar se paralelismo esta habilitado
SHOW max_parallel_workers_per_gather;
SHOW max_parallel_workers;

-- Query que se beneficia de paralelismo:
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    category,
    COUNT(*) as product_count,
    AVG(price) as avg_price,
    SUM(stock_quantity) as total_stock
FROM products
WHERE active = true
GROUP BY category;

-- Plano paralelo:
-- Finalize GroupAggregate (cost=12500.00..12500.05 rows=100 width=48) (actual time=125.000..125.005 rows=100 loops=1)
--   -> Gather Merge (cost=12500.00..12500.04 rows=200 width=48) (actual time=120.000..120.005 rows=200 loops=1)
--     Workers Planned: 2
--     Workers Launched: 2
--     -> Sort (cost=12500.00..12500.02 rows=100 width=48) (actual time=115.000..115.003 rows=100 loops=3)
--           Sort Key: products.category
--           Worker 0:  actual time=114.500..114.503 rows=95 loops=1
--           Worker 1:  actual time=114.800..114.803 rows=105 loops=1
--           -> Partial HashAggregate (cost=10000.00..10000.05 rows=100 width=48) (actual time=100.000..100.003 rows=100 loops=3)
--                 Group Key: products.category
--                 Worker 0:  actual time=99.500..99.503 rows=95 loops=1
--                 Worker 1:  actual time=99.800..99.803 rows=105 loops=1
--                 -> Parallel Seq Scan on products (cost=0.00..8500.00 rows=50000 width=20) (actual time=0.015..75.000 rows=50000 loops=3)
--                       Filter: active
--                       Rows Removed by Filter: 10000
--                       Worker 0:  actual time=0.010..74.500 rows=48000 loops=1
--                       Worker 1:  actual time=0.012..74.800 rows=52000 loops=1
-- Planning Time: 0.250 ms
-- Execution Time: 125.000 ms

-- Paralelismo funciona melhor para:
-- 1. Seq Scan em tabelas grandes
-- 2. Hash Join e Merge Join
-- 3. GroupAggregate e HashAggregate
-- 4. Filtros que removem muitas linhas

-- Paralelismo NAO funciona para:
-- 1. Nested Loop
-- 2. Queries com writes (INSERT, UPDATE, DELETE)
-- 3. Queries com funcoes volatility IMMUTABLE
-- 4. Queries com LIMIT sem ORDER BY
```

### Limitacoes do Paralelismo

```sql
-- 1. Nao pode paralelizar writes
EXPLAIN (ANALYZE)
UPDATE products SET price = price * 1.1 WHERE category = 'Electronics';
-- Seq Scan on products (cost=0.00..8500.00 rows=500 width=20)
--   Filter: (category = 'Electronics')
-- -> Update on products (cost=0.00..12500.00 rows=500 width=28)
--   -> Seq Scan on products (cost=0.00..8500.00 rows=500 width=20)
--       Filter: (category = 'Electronics')
-- Planning Time: 0.150 ms
-- Execution Time: 2500.000 ms
-- Nao ha "Workers Planned" - write nao paraleliza

-- 2. Funcoes com side effects bloqueiam paralelismo
CREATE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Query com trigger pode nao paralelizar
-- Trigger executa em cada linha individualmente

-- 3. Paralelismo e limitado por work_mem
-- Se hash table nao cabe em memoria, workers usam batch
-- Isso reduz eficiencia do paralelismo

-- 4. Ajustar configuracoes para paralelismo
SET max_parallel_workers_per_gather = 4;
SET parallel_tuple_cost = 0.005;
SET parallel_setup_cost = 500;
SET min_parallel_table_scan_size = 4MB;

-- Verificar uso de workers
SELECT
    pid,
    query,
    state,
    wait_event_type,
    wait_event
FROM pg_stat_activity
WHERE backend_type = 'parallel worker';

-- Limitar paralelismo por tabela
ALTER TABLE products SET (parallel_workers = 4);
ALTER TABLE orders SET (parallel_workers = 8);

-- Desabilitar paralelismo para tabela especifica
ALTER TABLE small_table SET (parallel_workers = 0);
```

## JIT Compilation

### Just-In-Time Compilation no PostgreSQL

```sql
-- JIT compila queries para codigo de maquina
-- Acelera queries complexas que processam muitos dados

-- Configuracoes no postgresql.conf:
-- jit = on
-- jit_above_cost = 1000000      (custo minimo para ativar JIT)
-- jit_inline_above_cost = 500000 (custo para inline de funcoes)
-- jit_optimize_above_cost = 500000 (custo para otimizacoes JIT)
-- jit_provider = 'llvmjit'      (provider padrao)

-- Verificar se JIT esta habilitado
SHOW jit;
SHOW jit_above_cost;

-- Query que ativa JIT:
EXPLAIN (ANALYZE, BUFFERS, GENERIC_PLAN)
SELECT
    u.username,
    COUNT(o.order_id) as order_count,
    SUM(o.amount) as total_amount
FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE u.created_at > '2024-01-01'
AND o.status = 'completed'
GROUP BY u.username
HAVING COUNT(o.order_id) > 10
ORDER BY total_amount DESC
LIMIT 100;

-- Plano com JIT:
-- Limit (cost=1250000.00..1250000.05 rows=100 width=48) (actual time=4500.000..4500.005 rows=100 loops=1)
--   -> Sort: sort_key(total_amount) DESC (actual time=4500.000..4500.005 rows=100 loops=1)
--     -> Filter: (COUNT(o.order_id) > 10) (actual time=4450.000..4450.005 rows=1500 loops=1)
--       -> Finalize GroupAggregate (cost=1250000.00..1250000.05 rows=1500 width=48) (actual time=4400.000..4400.005 rows=1500 loops=1)
--         -> Gather Merge (cost=1250000.00..1250000.04 rows=3000 width=48) (actual time=4350.000..4350.005 rows=3000 loops=1)
--           Workers Planned: 2
--           Workers Launched: 2
--           -> Sort (cost=1250000.00..1250000.02 rows=1500 width=48) (actual time=4300.000..4300.003 rows=1500 loops=3)
--                 Sort Key: u.username
--                 -> Partial HashAggregate (cost=1000000.00..1000000.05 rows=1500 width=48) (actual time=4200.000..4200.003 rows=1500 loops=3)
--                       Group Key: u.username
--                       -> Parallel Hash Join (cost=500000.00..500000.00 rows=500000 width=32) (actual time=100.000..4100.000 rows=500000 loops=3)
--                             Hash Cond: (o.user_id = u.user_id)
--                             -> Parallel Seq Scan on orders o (cost=0.00..250000.00 rows=250000 width=16) (actual time=0.010..2000.000 rows=250000 loops=3)
--                                   Filter: (status = 'completed')
--                             -> Parallel Hash (cost=100000.00..100000.00 rows=50000 width=24) (actual time=0.005..0.006 rows=50000 loops=3)
--                                   -> Parallel Seq Scan on users u (cost=0.00..100000.00 rows=50000 width=24) (actual time=0.003..500.000 rows=50000 loops=3)
--                                         Filter: (created_at > '2024-01-01')
-- JIT:
--   Functions: 24
--   Options: Inlining false, Optimization false, Expressions true, Deforming true
-- Planning Time: 0.250 ms
-- Execution Time: 4500.000 ms

-- JIT e mais eficiente para:
-- 1. Queries com muitas expressoes
-- 2. Queries com muitos filtros
-- 3. Queries com operacoes aritmeticas
-- 4. Queries com funcoes de usuario

-- JIT NAO e eficiente para:
-- 1. Queries simples (overhead de compilacao)
-- 2. Queries com poucas linhas
-- 3. Queries com muitos loops
-- 4. Queries com E/S (I/O bound)
```

### Configuracao Otimizada de JIT

```sql
-- Ajustar threshold para ativar JIT
SET jit_above_cost = 500000;  -- Ativar JIT para queries mais simples
SET jit_inline_above_cost = 250000;  -- Inline mais funcoes
SET jit_optimize_above_cost = 250000;  -- Mais otimizacoes

-- Para queries com muitos dados:
SET jit_above_cost = 100000;
SET jit_inline_above_cost = 50000;
SET jit_optimize_above_cost = 50000;

-- Verificar uso de JIT
SELECT
    query,
    jit_generation_count,
    jit_inline_count,
    jit_deforming_count
FROM pg_stat_statements
WHERE jit_generation_count > 0
ORDER BY jit_generation_count DESC
LIMIT 10;

-- Monitorar JIT
EXPLAIN (ANALYZE, GENERIC_PLAN)
SELECT * FROM large_table WHERE category = 'A' AND status = 'active';

-- Verificar se JIT foi ativado
-- Procurar por "JIT:" na saida do EXPLAIN

-- Desabilitar JIT para query especifica
SET jit = off;
EXPLAIN ANALYZE SELECT * FROM large_table WHERE category = 'A';
SET jit = on;

-- JIT e mais eficiente com parallel workers
-- Combinacao: paralelismo + JIT = maxima performance
```

## Memory Usage Optimization

### Configuracao de Memoria

```sql
-- PostgreSQL usa varios pools de memoria:
-- 1. shared_buffers: cache de paginas (padrao 128MB)
-- 2. work_mem: memoria para operacoes de sort/hash (padrao 4MB)
-- 3. maintenance_work_mem: memoria para VACUUM, CREATE INDEX (padrao 64MB)
-- 4. effective_cache_size: estimativa de cache disponivel (padrao 4GB)
-- 5. temp_buffers: memoria para tabelas temporarias (padrao 8MB)

-- Configuracoes recomendadas:
-- shared_buffers = '25% da RAM total'
-- work_mem = 'RAM / (max_connections * 2)'
-- maintenance_work_mem = 'RAM / 16'
-- effective_cache_size = '75% da RAM total'

-- Para servidor com 32GB de RAM:
-- shared_buffers = '8GB'
-- work_mem = '64MB'
-- maintenance_work_mem = '2GB'
-- effective_cache_size = '24GB'

-- Verificar uso de memoria
SELECT
    name,
    setting,
    unit,
    category
FROM pg_settings
WHERE name IN (
    'shared_buffers',
    'work_mem',
    'maintenance_work_mem',
    'effective_cache_size',
    'temp_buffers'
);

-- Monitorar uso de work_mem
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM large_table ORDER BY created_at;

-- Se "external merge" aparece, work_mem e insuficiente
-- Sort (cost=125000.00..125000.05 rows=1000000 width=48)
--   Sort Key: created_at
--   Sort Method: external merge  Disk: 45000kB
--   Buffers: shared hit=4500 temp read=5625 written=5625
-- Planning Time: 0.150 ms
-- Execution Time: 12500.000 ms

-- Aumentar work_mem
SET work_mem = '256MB';

-- AgoraSort usa memoria:
-- Sort (cost=125000.00..125000.05 rows=1000000 width=48)
--   Sort Key: created_at
--   Sort Method: quicksort  Memory: 45000kB
--   Buffers: shared hit=4500
-- Planning Time: 0.150 ms
-- Execution Time: 2500.000 ms  (5x mais rapido!)

-- Para queries com muitos joins, work_mem e critico
-- Cada Hash Join usa work_mem para hash table
-- Se hash table nao cabe, usa batch (muito mais lento)
```

### Gerenciamento de Memoria

```sql
-- 1. Usar CTEs para controlar materializacao
-- CTE MATERIALIZED usa memoria, NOT MATERIALIZED nao

-- CTE que usa muita memoria:
WITH large_cte AS MATERIALIZED (
    SELECT * FROM huge_table WHERE condition
)
SELECT * FROM large_cte JOIN other ON ...

-- Se nao precisa materializar:
WITH large_cte AS NOT MATERIALIZED (
    SELECT * FROM huge_table WHERE condition
)
SELECT * FROM large_cte JOIN other ON ...

-- 2. Controlar batch size de Hash Join
-- Se hash table nao cabe em work_mem, usa batch
-- Aumentar work_mem para evitar batch

-- 3. Usar LIMIT para reduzir consumo de memoria
SELECT * FROM huge_table ORDER BY created_at LIMIT 1000;

-- 4. Usar cursor para iterar em grandes resultados
DECLARE cursor_name CURSOR FOR
SELECT * FROM huge_table ORDER BY created_at;

-- Buscar em lotes
FETCH 1000 FROM cursor_name;

-- 5. Monitorar memoria por conexao
SELECT
    pid,
    usename,
    application_name,
    state,
    backend_type,
    pg_size_pretty(pg_relation_size(relid)) as table_size
FROM pg_stat_activity sa
JOIN pg_locks l ON sa.pid = l.pid
JOIN pg_class c ON l.relation = c.oid
WHERE l.mode = 'AccessExclusiveLock';

-- 6. Usar temp tables para resultados intermediarios
CREATE TEMPORARY TABLE temp_results AS
SELECT * FROM huge_table WHERE complex_condition;

-- Processar temp table
SELECT * FROM temp_results JOIN other ON ...;

-- Temp tables usam temp_buffers, nao work_mem
```

## Advanced Query Patterns

### Window Functions para Otimizacao

```sql
-- Window functions podem substituir subqueries correlacionadas
-- E sao geralmente mais eficientes

-- Subquery correlacionada (lenta):
SELECT
    user_id,
    order_date,
    amount,
    (SELECT AVG(amount) FROM orders o2 WHERE o2.user_id = o1.user_id) as avg_amount
FROM orders o1;

-- Window function (rapida):
SELECT
    user_id,
    order_date,
    amount,
    AVG(amount) OVER (PARTITION BY user_id) as avg_amount
FROM orders;

-- Diferenca de performance:
-- Subquery: O(n * m) onde n = linhas, m = media por usuario
-- Window function: O(n log n) devido ao sort

-- Mais exemplos de window functions:
SELECT
    user_id,
    order_date,
    amount,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date) as running_total,
    COUNT(*) OVER (PARTITION BY user_id) as total_orders,
    LAG(amount, 1) OVER (PARTITION BY user_id ORDER BY order_date) as prev_amount,
    LEAD(amount, 1) OVER (PARTITION BY user_id ORDER BY order_date) as next_amount,
    NTILE(4) OVER (PARTITION BY user_id ORDER BY amount) as quartile
FROM orders;

-- Window functions com frame specification
SELECT
    user_id,
    order_date,
    amount,
    AVG(amount) OVER (
        PARTITION BY user_id
        ORDER BY order_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) as moving_avg_3
FROM orders;

-- Window functions sao otimas para:
-- 1. Running totals e cumulative sums
-- 2. Moving averages
-- 3. Rankings (RANK, DENSE_RANK, ROW_NUMBER)
-- 4. Comparacoes com linhas anteriores/posteriores
-- 5. Agregacoes por grupo sem colapsar linhas
```

### LATERAL Joins para Subqueries Dependentes

```sql
-- LATERAL permite subqueries que dependem de tabelas externas
-- Muito mais eficiente que subqueries correlacionadas

-- Top-N per group (classic use case):
-- Sem LATERAL (lento):
SELECT
    u.username,
    o.order_id,
    o.amount
FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IN (
    SELECT order_id FROM orders o2
    WHERE o2.user_id = u.user_id
    ORDER BY amount DESC
    LIMIT 3
);

-- Com LATERAL (rapido):
SELECT
    u.username,
    top_orders.*
FROM users u
JOIN LATERAL (
    SELECT order_id, amount
    FROM orders
    WHERE user_id = u.user_id
    ORDER BY amount DESC
    LIMIT 3
) top_orders ON true;

-- Mais exemplos de LATERAL:
-- 1. Primeiro e ultimo registro por grupo
SELECT
    u.username,
    first.order_date as first_order,
    last.order_date as last_order
FROM users u
JOIN LATERAL (
    SELECT order_date FROM orders
    WHERE user_id = u.user_id
    ORDER BY order_date ASC LIMIT 1
) first ON true
JOIN LATERAL (
    SELECT order_date FROM orders
    WHERE user_id = u.user_id
    ORDER BY order_date DESC LIMIT 1
) last ON true;

-- 2. Dados mais recentes por categoria
SELECT
    p.category,
    latest.product_name,
    latest.price
FROM (SELECT DISTINCT category FROM products) p
JOIN LATERAL (
    SELECT product_name, price
    FROM products
    WHERE category = p.category
    ORDER BY created_at DESC
    LIMIT 1
) latest ON true;

-- 3. Agregacoes personalizadas por grupo
SELECT
    u.username,
    stats.order_count,
    stats.total_amount,
    stats.avg_amount,
    stats.max_amount
FROM users u
JOIN LATERAL (
    SELECT
        COUNT(*) as order_count,
        SUM(amount) as total_amount,
        AVG(amount) as avg_amount,
        MAX(amount) as max_amount
    FROM orders
    WHERE user_id = u.user_id
) stats ON true;

-- LATERAL e especialmente eficiente quando:
-- 1. Cada linha externa retorna poucas linhas internas
-- 2. A subquery interna tem indice adequado
-- 3. Precisamos de TOP-N por grupo
-- 4. A subquery depende de colunas da tabela externa
```

## Common Table Expressions (CTEs) Avancadas

### CTEs Recursivas

```sql
-- CTEs recursivas resolvem problemas de hierarquia e grafos

-- Exemplo: hierarquia de funcionarios
CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    manager_id INTEGER REFERENCES employees(employee_id),
    department VARCHAR(50),
    salary DECIMAL(10,2)
);

-- Inserir dados
INSERT INTO employees VALUES
(1, 'CEO', NULL, 'Executive', 200000),
(2, 'VP Sales', 1, 'Sales', 150000),
(3, 'VP Engineering', 1, 'Engineering', 160000),
(4, 'Sales Manager', 2, 'Sales', 100000),
(5, 'Engineer', 3, 'Engineering', 90000),
(6, 'Engineer', 3, 'Engineering', 85000),
(7, 'Sales Rep', 4, 'Sales', 70000);

-- CTE recursiva para encontrar toda a subordinacao
WITH RECURSIVE org_chart AS (
    -- Caso base: CEO (sem manager)
    SELECT
        employee_id,
        name,
        manager_id,
        department,
        salary,
        0 as level,
        ARRAY[employee_id] as path,
        name::TEXT as hierarchy
    FROM employees
    WHERE manager_id IS NULL
    
    UNION ALL
    
    -- Caso recursivo: funcionarios com manager
    SELECT
        e.employee_id,
        e.name,
        e.manager_id,
        e.department,
        e.salary,
        oc.level + 1,
        oc.path || e.employee_id,
        oc.hierarchy || ' -> ' || e.name
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.employee_id
    WHERE NOT e.employee_id = ANY(oc.path)  -- Evitar loops
)
SELECT
    REPEAT('  ', level) || name as employee,
    department,
    salary,
    level,
    hierarchy
FROM org_chart
ORDER BY path;

-- Saida:
-- employee        | department  | salary  | level | hierarchy
-- ----------------+-------------+---------+-------+---------------------------
-- CEO             | Executive   | 200000  | 0     | CEO
--   VP Sales      | Sales       | 150000  | 1     | CEO -> VP Sales
--     Sales Manager| Sales      | 100000  | 2     | CEO -> VP Sales -> Sales Manager
--       Sales Rep | Sales       | 70000   | 3     | CEO -> VP Sales -> Sales Manager -> Sales Rep
--   VP Engineering| Engineering | 160000  | 1     | CEO -> VP Engineering
--     Engineer    | Engineering | 90000   | 2     | CEO -> VP Engineering -> Engineer
--     Engineer    | Engineering | 85000   | 2     | CEO -> VP Engineering -> Engineer

-- CTE recursiva para gerar sequencia de datas
WITH RECURSIVE date_series AS (
    SELECT CURRENT_DATE as date
    UNION ALL
    SELECT date + INTERVAL '1 day'
    FROM date_series
    WHERE date < CURRENT_DATE + INTERVAL '30 days'
)
SELECT date FROM date_series;

-- CTE recursiva para Flatten de JSON
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    parent_id INTEGER REFERENCES documents(id),
    metadata JSONB
);

INSERT INTO documents VALUES
(1, 'Root', NULL, '{"type": "folder", "children": ["doc1", "doc2"]}'),
(2, 'Doc1', 1, '{"type": "file", "size": 1024}'),
(3, 'Doc2', 1, '{"type": "file", "size": 2048}');

WITH RECURSIVE doc_tree AS (
    SELECT
        id,
        name,
        parent_id,
        metadata,
        0 as depth,
        name::TEXT as path
    FROM documents
    WHERE parent_id IS NULL
    
    UNION ALL
    
    SELECT
        d.id,
        d.name,
        d.parent_id,
        d.metadata,
        dt.depth + 1,
        dt.path || '/' || d.name
    FROM documents d
    JOIN doc_tree dt ON d.parent_id = dt.id
)
SELECT
    REPEAT('  ', depth) || name as document,
    metadata->>'type' as type,
    path
FROM doc_tree;
```

### CTEs Materialized vs Not Materialized

```sql
-- PostgreSQL 12+ permite controle de materializacao de CTEs

-- CTE MATERIALIZED (padrao para CTEs com side effects):
WITH expensive_calc AS MATERIALIZED (
    SELECT
        user_id,
        COUNT(*) as order_count,
        SUM(amount) as total_amount
    FROM orders
    GROUP BY user_id
)
SELECT
    u.username,
    ec.order_count,
    ec.total_amount
FROM users u
JOIN expensive_calc ec ON u.user_id = ec.user_id;

-- CTE NOT MATERIALIZED (inlining):
WITH user_stats AS NOT MATERIALIZED (
    SELECT
        user_id,
        COUNT(*) as order_count,
        SUM(amount) as total_amount
    FROM orders
    GROUP BY user_id
)
SELECT
    u.username,
    us.order_count,
    us.total_amount
FROM users u
JOIN user_stats us ON u.user_id = us.user_id;

-- Diferencas:
-- MATERIALIZED: executa CTE uma vez, armazena resultado
-- NOT MATERIALIZED: inlining na query principal, pode ser otimizado junto

-- Quando usar MATERIALIZED:
-- 1. CTE e executada multiplas vezes na query
-- 2. CTE tem side effects
-- 3. CTE e cara e resultado e reusado

-- Quando usar NOT MATERIALIZED:
-- 1. CTE e executada apenas uma vez
-- 2. Filtros da query principal podem ser empurrados para CTE
-- 3. CTE e simples e pode ser otimizada junto

-- Exemplo de pushdown de filtro:
-- Com MATERIALIZED (sem pushdown):
WITH all_orders AS MATERIALIZED (
    SELECT * FROM orders
)
SELECT * FROM all_orders WHERE status = 'completed';
-- Orders inteira e materializada, depois filtrada

-- Com NOT MATERIALIZED (com pushdown):
WITH all_orders AS NOT MATERIALIZED (
    SELECT * FROM orders
)
SELECT * FROM all_orders WHERE status = 'completed';
-- Filtro e aplicado antes da execucao da CTE
-- Muito mais eficiente!
```

## Query Plan Operators Detalhados

### Operadores de Acesso

```sql
-- 1. Seq Scan (Sequential Scan)
-- Le todas as linhas da tabela sequencialmente
-- Custo: O(n)
-- Uso: tabelas pequenas, filtros pouco seletivos

EXPLAIN ANALYZE SELECT * FROM orders WHERE amount > 1000;

-- 2. Index Scan
-- Usa indice para encontrar linhas especificas
-- Custo: O(log n) para busca + O(1) por linha
-- Uso: filtros seletivos com indice

CREATE INDEX idx_orders_amount ON orders (amount);
EXPLAIN ANALYZE SELECT * FROM orders WHERE amount > 1000;

-- 3. Index Only Scan
-- Le apenas do indice (se cobre todas as colunas)
-- Custo: O(log n)
-- Uso: queries que usam apenas colunas do indice

CREATE INDEX idx_orders_covering ON orders (amount, status, created_at);
EXPLAIN ANALYZE SELECT amount, status FROM orders WHERE amount > 1000;

-- 4. Bitmap Index Scan
-- Cria bitmap de linhas e depois le
-- Custo: O(n) para criar bitmap + O(n) para ler
-- Uso: ranges que retornam muitas linhas

EXPLAIN ANALYZE SELECT * FROM orders WHERE amount BETWEEN 100 AND 200;

-- 5. Tid Scan (Tuple ID Scan)
-- Acesso direto por TID (tuple ID)
-- Custo: O(1)
-- Uso: acesso pontual raro

EXPLAIN ANALYZE SELECT * FROM orders WHERE ctid = '(1,1)';

-- 6. Subquery Scan
-- Escanea resultado de subquery
-- Custo: depende da subquery
-- Uso: subqueries complexas

EXPLAIN ANALYZE
SELECT * FROM (
    SELECT user_id, COUNT(*) as cnt
    FROM orders GROUP BY user_id
) sub WHERE cnt > 5;
```

### Operadores de Join

```sql
-- 1. Nested Loop
-- Para cada linha da tabela externa, busca na interna
-- Custo: O(n * m)
-- Uso: tabela externa pequena, tabela interna com indice

EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.user_id = 42;

-- 2. Hash Join
-- Cria hash table de uma tabela e faz probe na outra
-- Custo: O(n + m)
-- Uso: tabelas medias/grandes, join de igualdade

EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- 3. Merge Join
-- Junta duas tabelas ordenadas
-- Custo: O(n log n + m log m) se nao ordenado, O(n + m) se ordenado
-- Uso: dados ja ordenados, tabelas grandes

CREATE INDEX idx_orders_user ON orders (user_id);
CREATE INDEX idx_users_id ON users (user_id);
EXPLAIN ANALYZE
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.user_id;

-- 4. Hash Semi Join
-- Join que retorna apenas linhas da tabela esquerda
-- Custo: O(n + m)
-- Uso: EXISTS subqueries

EXPLAIN ANALYZE
SELECT DISTINCT u.* FROM users u
JOIN orders o ON u.user_id = o.user_id;

-- 5. Hash Anti Join
-- Join que retorna linhas da tabela esquerda sem correspondencia
-- Custo: O(n + m)
-- Uso: NOT EXISTS subqueries

EXPLAIN ANALYZE
SELECT u.* FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IS NULL;

-- 6. Merge Semi Join
-- Merge join que retorna apenas linhas da tabela esquerda
-- Custo: O(n + m) se dados ordenados
-- Uso: EXISTS com dados ordenados

-- 7. Merge Anti Join
-- Merge join que retorna linhas sem correspondencia
-- Custo: O(n + m) se dados ordenados
-- Uso: NOT EXISTS com dados ordenados
```

### Operadores de Agregacao e Ordenacao

```sql
-- 1. HashAggregate
-- Usa hash table para agrupar
-- Custo: O(n)
-- Uso: muitos grupos

EXPLAIN ANALYZE
SELECT status, COUNT(*), AVG(amount)
FROM orders GROUP BY status;

-- 2. GroupAggregate
-- Ordena e agrupa
-- Custo: O(n log n)
-- Uso: poucos grupos, dados ja ordenados

EXPLAIN ANALYZE
SELECT user_id, COUNT(*)
FROM orders GROUP BY user_id;

-- 3. Sort
-- Ordena resultado
-- Custo: O(n log n)
-- Uso: ORDER BY sem indice

EXPLAIN ANALYZE
SELECT * FROM orders ORDER BY created_at;

-- 4. Top-N Sort
-- Ordena e pega top N
-- Custo: O(n log N) onde N e o limite
-- Uso: ORDER BY com LIMIT

EXPLAIN ANALYZE
SELECT * FROM orders ORDER BY amount DESC LIMIT 10;

-- 5. Unique
-- Remove duplicatas
-- Custo: O(n log n)
-- Uso: DISTINCT

EXPLAIN ANALYZE
SELECT DISTINCT status FROM orders;

-- 6. SetOp
-- Operacoes de conjunto (UNION, INTERSECT, EXCEPT)
-- Custo: O(n log n)
-- Uso: UNION, INTERSECT, EXCEPT

EXPLAIN ANALYZE
SELECT user_id FROM orders WHERE status = 'completed'
UNION
SELECT user_id FROM orders WHERE status = 'pending';

-- 7. WindowAgg
-- Calcula funcoes de janela
-- Custo: O(n log n)
-- Uso: window functions

EXPLAIN ANALYZE
SELECT
    user_id,
    amount,
    SUM(amount) OVER (PARTITION BY user_id ORDER BY order_date)
FROM orders;
```

## Conclusao

Query optimization e uma habilidade essencial para qualquer profissional de banco de dados. Este capitulo cobriu:

- Como funciona o otimizador de consultas
- Cost-based optimization e seus fatores
- Otimizacao de join order
- Predicate pushdown e subquery flattening
- Materialization vs streaming
- Analise de planos com EXPLAIN ANALYZE
- Operadores de plano (Seq Scan, Index Scan, Hash Join, Merge Join, Nested Loop)
- Uso de hints para influenciar o otimizador
- Padroes de rewriting de queries
- Estrategias de cache
- Performance de prepared statements
- Parallel query execution
- JIT compilation
- Memory usage optimization
- Window functions e LATERAL joins
- CTEs avancadas (recursivas, materialized)
- Operadores de plano detalhados
- Exemplo pratico de otimizacao step-by-step

Dominar essas tecnicas permite transformar queries lentas em consultas eficientes, melhorando drasticamente a performance de aplicacoes que dependem de bancos de dados. A chave e sempre analisar o plano de execucao, identificar gargalos e aplicar a otimizacao adequada para cada caso.