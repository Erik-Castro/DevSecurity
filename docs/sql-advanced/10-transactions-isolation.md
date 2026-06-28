# Transactions e Isolation

## Visão Geral

Transações são a espinha dorsal da integridade dos dados em qualquer sistema de banco de dados relacional. Sem transações, operações concorrentes podem corromper dados, criar inconsistências e causar perdas financeiras irreparáveis. Este capítulo explora profundamente o mecanismo de transações, seus níveis de isolamento, problemas de concorrência e padrões avançados de controle de acesso concorrente.

## ACID em Detalhe

### Atomicidade

Atomicidade garante que uma transação seja executada como uma unidade indivisível. Ou todas as operações dentro da transação são concluídas com sucesso, ou nenhuma delas é aplicada ao banco de dados. Não existe estado parcial.

Considere uma transferência bancária entre duas contas:

```sql
BEGIN TRANSACTION;

-- Debita da conta origem
UPDATE accounts
SET balance = balance - 500.00
WHERE account_id = 1001
AND balance >= 500.00;

-- Credita na conta destino
UPDATE accounts
SET balance = balance + 500.00
WHERE account_id = 2002;

-- Se qualquer operação falhar, ROLLBACK desfaz tudo
-- Se ambas funcionarem, COMMIT aplica permanentemente

COMMIT;
```

Se o sistema falhar após o débito mas antes do crédito, o ROLLBACK restaura o saldo original da conta 1001. Sem atomicidade, 500 reais desapareceriam do sistema.

### Consistência

Consistência assegura que uma transação leva o banco de dados de um estado válido para outro estado válido. Restrições como chaves primárias, chaves estrangeiras, verificações NOT NULL e regras de negócio CHECK devem ser satisfeitas após o COMMIT.

```sql
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id)
        ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0)
);
```

A restrição de chave estrangeira entre `order_items` e `orders` garante que não existam itens órfãos. Se uma transação tentar inserir um item com `order_id` inexistente, o banco rejeita a operação.

### Isolamento

Isolamento controla o grau em que transações concorrentes enxergam umas às outras. Transações isoladas parecem executar sequencialmente, mesmo quando executam concorrentemente. O nível de isolamento determina quais efeitos colaterais (dirty reads, phantom reads, lost updates) são permitidos.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT balance FROM accounts WHERE account_id = 1001;
-- Retorna 1000.00

-- Sessão 2 (executando concorrentemente)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT balance FROM accounts WHERE account_id = 1001;
-- Também retorna 1000.00

-- Sessão 1
UPDATE accounts SET balance = balance - 200 WHERE account_id = 1001;
COMMIT;

-- Sessão 2
-- Tenta atualizar a mesma linha
UPDATE accounts SET balance = balance - 300 WHERE account_id = 1001;
-- Bloqueada até Sessão 1 fazer COMMIT ou ROLLBACK
-- Após COMMIT da Sessão 1, Sessão 2 pode seguir
COMMIT;
```

### Durabilidade

Durabilidade garante que uma vez feito COMMIT, os dados persistem mesmo em caso de falha do sistema. Mecanismos como Write-Ahead Logging (WAL) garantem que antes de qualquer modificação ser visível, o registro correspondente seja escrito em log persistente.

```sql
-- PostgreSQL: verificando configuração de WAL
SHOW wal_level;
-- Resultado esperado: "replica" ou "logical"

-- Forçando persistência de dados em disco
SET synchronous_commit = on;

-- Verificando se o COMMIT foi sincronizado
SELECT pg_current_wal_lsn();
```

## Transaction Lifecycle

### BEGIN

O comando `BEGIN` inicia uma nova transação. Todas as operações seguintes até `COMMIT` ou `ROLLBACK` fazem parte dessa transação.

```sql
BEGIN;

-- Operações dentro da transação
INSERT INTO customers (name, email)
VALUES ('João Silva', 'joao@example.com');

UPDATE inventory
SET stock = stock - 1
WHERE product_id = 42
AND stock > 0;

-- Verificar se a operação anterior afetou alguma linha
GET DIAGNOSTICS row_count = ROW_COUNT;
IF row_count = 0 THEN
    RAISE EXCEPTION 'Product out of stock';
END IF;
```

### COMMIT

`COMMIT` persiste todas as modificações feitas durante a transação. Após o COMMIT, as alterações são visíveis para outras transações (dependendo do nível de isolamento).

```sql
BEGIN;

-- Transferência bancária
UPDATE accounts SET balance = balance - 1000 WHERE account_id = 1;
UPDATE accounts SET balance = balance + 1000 WHERE account_id = 2;

-- Registrar a transação
INSERT INTO transactions (from_account, to_account, amount, type)
VALUES (1, 2, 1000, 'transfer');

-- Persistir tudo
COMMIT;
```

### ROLLBACK

`ROLLBACK` desfaz todas as modificações feitas durante a transação, restaurando o banco ao estado anterior ao `BEGIN`.

```sql
BEGIN;

-- Tentar atualização
UPDATE products SET price = price * 1.10 WHERE category = 'electronics';

-- Descobrir que o aumento é maior que o permitido
-- Desfazer tudo
ROLLBACK;
-- Todas as alterações de preço são desfeitas
```

### SAVEPOINT

SAVEPOINT cria pontos de salvamento dentro de uma transação, permitindo rollback parcial sem desfazer toda a transação.

```sql
BEGIN;

-- Primeira operação
INSERT INTO orders (customer_id, total) VALUES (100, 250.00)
    RETURNING order_id INTO new_order_id;

-- Criar savepoint antes da segunda operação
SAVEPOINT after_order;

-- Inserir itens do pedido
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
VALUES (new_order_id, 1, 2, 50.00);

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
VALUES (new_order_id, 2, 1, 150.00);

-- Se houver erro na inserção de um item específico
SAVEPOINT after_items;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
VALUES (new_order_id, 3, 5, 30.00);
-- Esta inserção pode falhar se produto 3 não existir

-- Em caso de erro, fazer rollback apenas até o savepoint anterior
ROLLBACK TO after_items;
-- A ordem e os dois primeiros itens ainda existem

-- Continuar com a transação principal
COMMIT;
-- A ordem é criada com apenas 2 itens
```

### COMMIT e ROLLBACK Parciais com SAVEPOINT

```sql
BEGIN;

INSERT INTO audit_log (action, details) VALUES ('start_batch', 'Processing batch 12345');

SAVEPOINT batch_start;

-- Processar lote de 1000 registros
INSERT INTO processed_data (original_id, result)
SELECT id, expensive_function(data)
FROM raw_data
WHERE batch_id = 12345;

-- Se ultrapassar limite de memória ou tempo
-- ROLLBACK apenas este lote
-- ROLLBACK TO batch_start;

-- Se tudo OK, continuar
SAVEPOINT batch_done;

-- Atualizar estatísticas
UPDATE batch_stats SET rows_processed = rows_processed + 1000
WHERE batch_id = 12345;

COMMIT;
```

## Isolation Levels

### READ UNCOMMITTED

O nível mais baixo de isolamento. Transações podem ler dados modificados por outras transações que ainda não fizeram COMMIT. Permite dirty reads.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

UPDATE accounts SET balance = 999999 WHERE account_id = 1;
-- NÃO fez COMMIT ainda

-- Sessão 2 (com READ UNCOMMITTED)
BEGIN TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT balance FROM accounts WHERE account_id = 1;
-- Retorna 999999 (dirty read - dados não confirmados)

-- Sessão 1
ROLLBACK; -- Desfaz a alteração

-- Sessão 2 agora enxerga o valor antigo inconsistente
-- Dados temporários e incorretos foram processados
```

**Quando usar**: Apenas para relatórios aproximados onde exatidão não é crítica. Nunca para operações financeiras ou de negócio.

### READ COMMITTED

Cada statement dentro da transação enxerga apenas dados que foram COMMITados antes do início do statement. Não permite dirty reads, mas permite non-repeatable reads.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT balance FROM accounts WHERE account_id = 1;
-- Retorna 1000.00

-- Sessão 2 (concorrente)
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;
UPDATE accounts SET balance = 1500 WHERE account_id = 1;
COMMIT;

-- Sessão 1 (continuando)
SELECT balance FROM accounts WHERE account_id = 1;
-- Retorna 1500.00 (non-repeatable read - valor mudou entre leituras)

-- Isso pode causar lógica incorreta em aplicações que esperam consistência entre leituras
COMMIT;
```

### REPEATABLE READ

Garante que se uma linha for lida duas vezes na mesma transação, os valores serão idênticos. Previne dirty reads e non-repeatable reads, mas permite phantom reads (no PostgreSQL, previne phantoms via MVCC).

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;

SELECT COUNT(*) FROM orders WHERE customer_id = 100;
-- Retorna 5

-- Sessão 2 (concorrente)
BEGIN TRANSACTION;
INSERT INTO orders (customer_id, total) VALUES (100, 99.99);
COMMIT;

-- Sessão 1 (continuando)
SELECT COUNT(*) FROM orders WHERE customer_id = 100;
-- Retorna 5 (REPEATABLE READ: contagem não muda)
-- No PostgreSQL com MVCC, phantoms também são prevenidos

-- Mas se tentar inserir com customer_id 100
INSERT INTO orders (customer_id, total) VALUES (100, 149.99);
-- Pode falhar com serialization_failure dependendo da implementação
COMMIT;
```

### SERIALIZABLE

O nível mais alto de isolamento. Executa transações como se fossem serializadas (uma após a outra). Previne dirty reads, non-repeatable reads e phantom reads.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT SUM(amount) FROM transactions
WHERE account_id = 1
AND created_at >= '2024-01-01';

-- Retorna 5000.00

-- Sessão 2 (concorrente)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

INSERT INTO transactions (account_id, amount, created_at)
VALUES (1, 1000, '2024-06-15');
COMMIT;

-- Sessão 1 (continuando)
SELECT SUM(amount) FROM transactions
WHERE account_id = 1
AND created_at >= '2024-01-01';
-- Retorna 5000.00 (mesmo valor, serializable)

-- Ao tentar COMMIT, pode receber:
-- ERROR: could not serialize access due to read/write dependencies
-- Solução: retry da transação inteira
COMMIT;
```

### Comparação dos Níveis

| Isolamento | Dirty Read | Non-Repeatable Read | Phantom Read | Performance |
|---|---|---|---|---|
| READ UNCOMMITTED | Sim | Sim | Sim | Máxima |
| READ COMMITTED | Não | Sim | Sim | Alta |
| REPEATABLE READ | Não | Não | Sim* | Média |
| SERIALIZABLE | Não | Não | Não | Baixa |

*No PostgreSQL com MVCC, REPEATABLE READ previne phantom reads.

## Problemas de Concorrência

### Dirty Reads

Leitura de dados modificados por outra transação que ainda não foi COMMITada. Se a transação fonte fizer ROLLBACK, a transação leitora terá processado dados que nunca existiram oficialmente.

```sql
-- Cenário de dirty read
-- Conta do usuário tem saldo R$ 1000.00

-- Sessão A: Transferência de R$ 800
BEGIN;
UPDATE accounts SET balance = balance - 800 WHERE id = 1;
-- Saldo agora é R$ 200 (não COMMITado)

-- Sessão B: Verificação de saldo (READ UNCOMMITTED)
BEGIN;
SELECT balance FROM accounts WHERE id = 1;
-- Retorna R$ 200 (dirty read!)
-- Sistema aprova um empréstimo baseado在这个虚假的低余额

-- Sessão A
ROLLBACK; -- Transferência cancelada
-- Saldo real é R$ 1000.00

-- Sessão B agora tem decisão incorreta baseada em dados fantasma
-- Usuário deveria ter R$ 1000 mas sistema acreditou que tinha R$ 200
```

### Non-Repeatable Reads

Uma linha lida duas vezes na mesma transação retorna valores diferentes porque outra transação modificou e COMMITou os dados entre as leituras.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT price FROM products WHERE product_id = 42;
-- Retorna 99.99

-- Sessão 2
BEGIN;
UPDATE products SET price = 79.99 WHERE product_id = 42;
COMMIT; -- Preço alterado e persistido

-- Sessão 1
SELECT price FROM products WHERE product_id = 42;
-- Retorna 79.99 (non-repeatable read)
-- Cálculos baseados no primeiro preço estão incorretos
COMMIT;
```

### Phantom Reads

Uma transação executa a mesma query duas vezes e obtém conjuntos de resultados diferentes porque outra transação inseriu ou删除 linhas entre as execuções.

```sql
-- Sessão 1
BEGIN TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT COUNT(*) FROM orders
WHERE status = 'pending'
AND created_at < '2024-06-01';
-- Retorna 150 pedidos pendentes

-- Processar pedidos pendentes...
-- Tempo passa...

SELECT COUNT(*) FROM orders
WHERE status = 'pending'
AND created_at < '2024-06-01';
-- Retorna 163 pedidos (13 novos phantom reads)
-- Relatório de processamento está inconsistente
COMMIT;
```

### Lost Updates

Duas transações leem a mesma linha, modificam com base no valor lido, e uma sobrescreve a outra. A primeira atualização é perdida.

```sql
-- Sessão 1
BEGIN;
SELECT stock FROM inventory WHERE product_id = 42;
-- Retorna 10

-- Sessão 2
BEGIN;
SELECT stock FROM inventory WHERE product_id = 42;
-- Também retorna 10

-- Sessão 1: vende 3 unidades
UPDATE inventory SET stock = stock - 3 WHERE product_id = 42;
-- stock agora é 7
COMMIT;

-- Sessão 2: vende 2 unidades (baseado no stock antigo de 10)
UPDATE inventory SET stock = stock - 2 WHERE product_id = 42;
-- stock agora é 8 (sobrescreveu o 7!)
-- Perda de 3 unidades de estoque sem registro

-- Resultado: estoque real deveria ser 5 (10 - 3 - 2)
-- mas está 8
```

## MVCC (Multi-Version Concurrency Control)

### Conceito Fundamental

MVCC mantém múltiplas versões de cada linha do banco de dados. Quando uma transação modifica uma linha, em vez de sobrescrever a versão antiga, o sistema cria uma nova versão. Leitores acessam a versão que era válida quando sua transação começou, sem serem bloqueados por escritores.

No PostgreSQL, cada tupla possui campos ocultos:

```sql
-- Criar tabela de exemplo
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    content TEXT,
    version INTEGER DEFAULT 1
);

-- Inserir dados iniciais
INSERT INTO documents (title, content, version)
VALUES ('Manual', 'Versão inicial do manual', 1);

-- Verificar campos MVCC (xmin, xmax) via system columns
SELECT xmin, xmax, ctid, id, title, version
FROM documents;
-- xmin: ID da transação que criou esta versão
-- xmax: ID da transação que deletou/obsoleceu esta versão (0 se ainda ativa)
-- ctid: localização física da tupla na página

-- Sessão 1: atualiza o documento
BEGIN;
UPDATE documents SET content = 'Versão 2', version = 2 WHERE id = 1;
-- PostgreSQL cria uma NOVA versão da linha
-- A versão antiga recebe um xmax igual ao ID da transação atual

-- Sessão 2 (concorrente, começou antes da atualização)
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT version, content FROM documents WHERE id = 1;
-- Retorna version=1, content='Versão inicial'
-- MVCC garante que a versão antiga ainda seja visível

-- Sessão 1
COMMIT;

-- Sessão 2
SELECT version, content FROM documents WHERE id = 1;
-- Ainda retorna version=1 (REPEATABLE READ preserva a visão)
COMMIT;

-- Nova sessão
SELECT version, content FROM documents WHERE id = 1;
-- Retorna version=2, content='Versão 2' (nova transação vê o COMMIT mais recente)
```

### visibility_map

PostgreSQL mantém um mapa de visibilidade para cada página de dados. Este mapa acelera a verificação de quais tuplas são visíveis para uma transação específica.

```sql
-- Verificar visibility map
SELECT relname, relfrozenxid,
       pg_size_pretty(pg_total_relation_size(oid)) as size
FROM pg_class
WHERE relname = 'documents';

-- Forçar limpeza de tuplas obsoletas
VACUUM documents;

-- Analisar estatísticas da tabela
ANALYZE documents;

-- Verificar se VACUUM removeu tuplas mortas
SELECT n_live_tup, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'documents';
```

### Transaction ID Wraparound

IDs de transação no PostgreSQL são armazenados como 32-bit integers, o que significa que após aproximadamente 4 bilhões de transações, o contador "dá a volta" para zero. Isso pode causar perda de dados se tuplas antigas não forem limpas.

```sql
-- Verificar idade da transação mais antiga
SELECT datname,
       age(datfrozenxid) as xid_age,
       2^31 - age(datfrozenxid) as transactions_until_wraparound
FROM pg_database
WHERE datname = current_database();

-- Monitorar wraparound
SELECT relname,
       age(relfrozenxid) as table_age,
       pg_size_pretty(pg_total_relation_size(oid)) as size
FROM pg_class
WHERE relkind = 'r'
AND age(relfrozenxid) > 1000000
ORDER BY age(relfrozenxid) DESC;

-- Configurar alertas de wraparound
ALTER SYSTEM SET autovacuum_freeze_max_age = 200000000;
SELECT pg_reload_conf();
```

## Deadlock Detection e Resolution

### O que é Deadlock

Deadlock ocorre quando duas ou mais transações ficam bloqueadas indefinidamente, cada uma esperando que a outra libere um recurso.

```sql
-- Sessão 1
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- Trava a linha id=1

-- Sessão 2 (concorrente)
BEGIN;
UPDATE accounts SET balance = balance - 200 WHERE id = 2;
-- Trava a linha id=2

-- Sessão 1 (tenta acessar linha que Sessão 2 mantém)
UPDATE accounts SET balance = balance + 50 WHERE id = 2;
-- BLOQUEADA: Sessão 2 ainda não fez COMMIT na linha id=2

-- Sessão 2 (tenta acessar linha que Sessão 1 mantém)
UPDATE accounts SET balance = balance + 100 WHERE id = 1;
-- DEADLOCK DETECTED!
-- PostgreSQL detecta o deadlock e escolhe uma vítima
-- Uma das transações recebe ERROR: deadlock detected
```

### Configuração de Detecção

```sql
-- Verificar configurações de deadlock
SHOW deadlock_timeout;
-- Padrão: 1s (tempo para esperar antes de verificar deadlock)

-- Reduzir timeout para detecção mais rápida
SET deadlock_timeout = '500ms';

-- Verificar se deadlock está sendo monitorado
SHOW log_lock_waits;
-- Habilitar logging de waits de lock
SET log_lock_waits = on;

-- Configurar log detalhado
SET log_min_duration_statement = 0;
SET log_statement = 'all';
```

### Estratégias de Prevenção

```sql
-- 1. Acessar linhas na mesma ordem sempre
-- CORRETO: sempre ordem crescente de id
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = LEAST(1, 2);
UPDATE accounts SET balance = balance + 100 WHERE id = GREATEST(1, 2);
COMMIT;

-- 2. Usar timeouts de lock
SET lock_timeout = '5s'; -- Falha após 5 segundos em vez de bloquear indefinidamente

BEGIN;
SET LOCAL lock_timeout = '3s';
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
-- Se não conseguir lock em 3 segundos, retorna erro

-- 3. Usar NOWAIT para falhar imediatamente se não conseguir lock
BEGIN;
SELECT * FROM accounts WHERE id = 1 FOR UPDATE NOWAIT;
-- Se a linha estiver bloqueada, retorna erro imediatamente

-- 4. Usar SKIP LOCKED para ignorar linhas bloqueadas
BEGIN;
SELECT * FROM orders
WHERE status = 'pending'
ORDER BY created_at
LIMIT 10
FOR UPDATE SKIP LOCKED;
-- Pega até 10 pedidos pendentes ignorando os que estão sendo processados
```

### Tratamento de Deadlock na Aplicação

```sql
-- Função com retry automático
CREATE OR REPLACE FUNCTION safe_transfer(
    p_from_id INTEGER,
    p_to_id INTEGER,
    p_amount DECIMAL
) RETURNS BOOLEAN AS $$
DECLARE
    v_max_retries INTEGER := 3;
    v_retry INTEGER := 0;
    v_success BOOLEAN := FALSE;
BEGIN
    WHILE v_retry < v_max_retries AND NOT v_success LOOP
        BEGIN
            -- Tentar a transação
            UPDATE accounts
            SET balance = balance - p_amount
            WHERE id = p_from_id
            AND balance >= p_amount;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Insufficient funds';
            END IF;

            UPDATE accounts
            SET balance = balance + p_amount
            WHERE id = p_to_id;

            v_success := TRUE;

        EXCEPTION
            WHEN deadlock_detected THEN
                v_retry := v_retry + 1;
                RAISE NOTICE 'Deadlock detected, retry % of %', v_retry, v_max_retries;
                -- Espera aleatória antes de retry
                PERFORM pg_sleep(random() * 0.1);
            WHEN lock_not_available THEN
                v_retry := v_retry + 1;
                RAISE NOTICE 'Lock timeout, retry % of %', v_retry, v_max_retries;
        END;
    END LOOP;

    RETURN v_success;
END;
$$ LANGUAGE plpgsql;
```

## Optimistic vs Pessimistic Locking

### Pessimistic Locking

Assume que conflitos vão acontecer e bloqueia linhas antecipadamente para prevenir conflitos.

```sql
-- Pessimistic locking com FOR UPDATE
BEGIN;

-- Bloquear a linha para escrita
SELECT balance INTO v_balance
FROM accounts
WHERE id = 1001
FOR UPDATE;
-- Qualquer outra transação que tentar FOR UPDATE nesta linha será bloqueada

-- Modificar com base no valor bloqueado
UPDATE accounts
SET balance = balance - 500
WHERE id = 1001
AND balance >= 500;

IF NOT FOUND THEN
    RAISE EXCEPTION 'Insufficient funds or concurrent modification';
END IF;

COMMIT;
```

### FOR UPDATE com variantes

```sql
-- FOR UPDATE: bloqueia a linha até o fim da transação
SELECT * FROM products WHERE id = 42 FOR UPDATE;

-- FOR UPDATE NOWAIT: falha imediatamente se não conseguir lock
SELECT * FROM products WHERE id = 42 FOR UPDATE NOWAIT;

-- FOR UPDATE SKIP LOCKED: ignora linhas bloqueadas
SELECT * FROM task_queue
WHERE status = 'pending'
ORDER BY priority DESC
LIMIT 5
FOR UPDATE SKIP LOCKED;

-- FOR NO KEY UPDATE: bloqueio mais leve (não impede updates em chaves)
SELECT * FROM documents WHERE id = 42 FOR NO KEY UPDATE;

-- FOR SHARE: bloqueio compartilhado (leitura)
SELECT * FROM products WHERE id = 42 FOR SHARE;

-- FOR KEY SHARE: bloqueio compartilhado mais leve
SELECT * FROM products WHERE id = 42 FOR KEY SHARE;
```

### Optimistic Locking

Assume que conflitos são raros e verifica na hora do COMMIT se houve modificação concorrente. Usa um campo de versão ou timestamp.

```sql
-- Criar tabela com campo de versão
CREATE TABLE products_optimistic (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    stock INTEGER,
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Função com optimistic locking
CREATE OR REPLACE FUNCTION update_product_price(
    p_id INTEGER,
    p_new_price DECIMAL,
    p_expected_version INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_rows_affected INTEGER;
BEGIN
    UPDATE products_optimistic
    SET price = p_new_price,
        version = version + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_id
    AND version = p_expected_version;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

    IF v_rows_affected = 0 THEN
        -- Versão mudou durante o processamento
        RAISE EXCEPTION 'Concurrent modification detected';
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Uso na aplicação
BEGIN;
-- Ler versão atual
SELECT version, price FROM products_optimistic WHERE id = 42;
-- Retorna version=5, price=99.99

-- Processar...
-- Atualizar com verificação de versão
SELECT update_product_price(42, 109.99, 5);
-- Retorna TRUE se sucesso, FALSE se conflito
COMMIT;
```

### Optimistic Locking com Timestamp

```sql
-- Usando timestamp para optimistic locking
CREATE OR REPLACE FUNCTION update_with_timestamp(
    p_id INTEGER,
    p_new_value TEXT,
    p_last_update TIMESTAMP
) RETURNS BOOLEAN AS $$
DECLARE
    v_rows_affected INTEGER;
BEGIN
    UPDATE documents
    SET content = p_new_value,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_id
    AND updated_at = p_last_update;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;
    RETURN v_rows_affected > 0;
END;
$$ LANGUAGE plpgsql;

-- Leitura
SELECT id, content, updated_at FROM documents WHERE id = 1;
-- Retorna updated_at = '2024-06-15 10:30:00'

-- Atualização
SELECT update_with_timestamp(1, 'Novo conteúdo', '2024-06-15 10:30:00');
-- TRUE se nenhum outro processo modificou desde 10:30:00
-- FALSE se houve modificação concorrente
```

## Row-Level Locking

### Como Funciona

Row-level locking permite que múltiplas transações acessem diferentes linhas da mesma tabela simultaneamente, desde que não estejam acessando a mesma linha.

```sql
-- Transação 1: trava linha id=1
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
-- Apenas a linha id=1 está bloqueada

-- Transação 2: pode acessar linha id=2 livremente
BEGIN;
UPDATE accounts SET balance = balance + 200 WHERE id = 2;
-- Sucesso! Linha id=2 não está bloqueada

-- Transação 3: tenta acessar linha id=1
BEGIN;
UPDATE accounts SET balance = balance + 50 WHERE id = 1;
-- BLOQUEADA: Transação 1 ainda não fez COMMIT

-- Transação 1
COMMIT; -- Libera lock na linha id=1

-- Transação 3 agora pode prosseguir
UPDATE accounts SET balance = balance + 50 WHERE id = 1;
COMMIT;
```

### Monitoramento de Locks

```sql
-- Ver locks ativos no momento
SELECT
    l.pid,
    l.locktype,
    l.relation::regclass,
    l.mode,
    l.granted,
    a.usename,
    a.query,
    a.query_start,
    NOW() - a.query_start AS duration
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.relation IS NOT NULL
ORDER BY l.pid;

-- Verificar locks de tabela
SELECT
    relation::regclass,
    mode,
    granted,
    COUNT(*)
FROM pg_locks
WHERE relation IS NOT NULL
GROUP BY relation, mode, granted
ORDER BY relation, mode;

-- Identificar transações que estão segurando locks há muito tempo
SELECT
    a.pid,
    a.usename,
    a.state,
    a.query,
    a.query_start,
    NOW() - a.query_start AS lock_duration,
    l.locktype,
    l.relation::regclass,
    l.mode
FROM pg_stat_activity a
JOIN pg_locks l ON a.pid = l.pid
WHERE l.granted = TRUE
AND NOW() - a.query_start > INTERVAL '5 minutes'
ORDER BY lock_duration DESC;
```

## Advisory Locks

Advisory locks são locks application-level que não estão ligados a nenhuma tabela ou linha específica. São úteis para coordenar acesso a recursos que não são representados como tabelas.

```sql
-- Advisory lock exclusivo (baseado em integer)
SELECT pg_advisory_lock(12345);
-- Bloqueia o "recurso" 12345

-- Tentar adquirir o mesmo lock (bloqueia até ser liberado)
SELECT pg_advisory_lock(12345);
-- BLOQUEADO: outro processo já detém este lock

-- Liberar o lock
SELECT pg_advisory_unlock(12345);

-- Advisory lock com chave composta (dois integers)
SELECT pg_advisory_lock(1, 42);
-- Utiliza dois valores para formar a chave

-- Lock não bloqueante
SELECT pg_try_advisory_lock(12345);
-- Retorna TRUE se conseguiu, FALSE se já estava bloqueado

-- Uso prático: evitar execução concorrente de tarefas
CREATE OR REPLACE FUNCTION run_daily_report() RETURNS void AS $$
BEGIN
    -- Tentar adquirir lock exclusivo
    IF NOT pg_try_advisory_lock(1001) THEN
        RAISE NOTICE 'Report already running, skipping';
        RETURN;
    END IF;

    -- Executar o relatório
    PERFORM generate_daily_sales_report();

    -- Liberar lock
    PERFORM pg_advisory_unlock(1001);
END;
$$ LANGUAGE plpgsql;

-- Lock baseado em chave textual (via hashtext)
SELECT pg_advisory_lock(hashtext('export_queue'));
-- Mais legível para debugging

-- Verificar quais advisory locks estão ativos
SELECT
    pid,
    objid AS lock_id,
    mode,
    granted
FROM pg_locks
WHERE locktype = 'advisory';
```

## Transaction Patterns

### Saga Pattern

Saga é um padrão que decompone uma transação distribuída em uma sequência de transações locais, cada uma com uma operação de compensação em caso de falha.

```sql
-- Tabela de saga
CREATE TABLE saga_log (
    saga_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_number INTEGER,
    step_name VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    payload JSONB,
    compensation_payload JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Tabela de eventos de saga
CREATE TABLE saga_events (
    event_id SERIAL PRIMARY KEY,
    saga_id UUID REFERENCES saga_log(saga_id),
    event_type VARCHAR(30),
    event_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Função para registrar início de step
CREATE OR REPLACE FUNCTION saga_begin_step(
    p_saga_id UUID,
    p_step_name VARCHAR
) RETURNS void AS $$
BEGIN
    UPDATE saga_log
    SET status = 'in_progress',
        started_at = CURRENT_TIMESTAMP
    WHERE saga_id = p_saga_id
    AND step_name = p_step_name;

    INSERT INTO saga_events (saga_id, event_type, event_data)
    VALUES (p_saga_id, 'step_started', jsonb_build_object('step', p_step_name));
END;
$$ LANGUAGE plpgsql;

-- Função para completar step
CREATE OR REPLACE FUNCTION saga_complete_step(
    p_saga_id UUID,
    p_step_name VARCHAR
) RETURNS void AS $$
BEGIN
    UPDATE saga_log
    SET status = 'completed',
        completed_at = CURRENT_TIMESTAMP
    WHERE saga_id = p_saga_id
    AND step_name = p_step_name;

    INSERT INTO saga_events (saga_id, event_type, event_data)
    VALUES (p_saga_id, 'step_completed', jsonb_build_object('step', p_step_name));
END;
$$ LANGUAGE plpgsql;

-- Função para falhar step e iniciar compensação
CREATE OR REPLACE FUNCTION saga_fail_step(
    p_saga_id UUID,
    p_step_name VARCHAR,
    p_error TEXT
) RETURNS void AS $$
BEGIN
    UPDATE saga_log
    SET status = 'failed',
        completed_at = CURRENT_TIMESTAMP
    WHERE saga_id = p_saga_id
    AND step_name = p_step_name;

    INSERT INTO saga_events (saga_id, event_type, event_data)
    VALUES (p_saga_id, 'step_failed', jsonb_build_object('step', p_step_name, 'error', p_error));

    -- Iniciar compensação dos steps anteriores
    PERFORM saga_compensate(p_saga_id);
END;
$$ LANGUAGE plpgsql;

-- Função de compensação
CREATE OR REPLACE FUNCTION saga_compensate(p_saga_id UUID) RETURNS void AS $$
DECLARE
    v_step RECORD;
BEGIN
    -- Compensar steps em ordem reversa
    FOR v_step IN
        SELECT * FROM saga_log
        WHERE saga_id = p_saga_id
        AND status = 'completed'
        ORDER BY step_number DESC
    LOOP
        UPDATE saga_log
        SET status = 'compensated',
            completed_at = CURRENT_TIMESTAMP
        WHERE saga_id = p_saga_id
        AND step_number = v_step.step_number;

        INSERT INTO saga_events (saga_id, event_type, event_data)
        VALUES (p_saga_id, 'step_compensated', jsonb_build_object('step', v_step.step_name));

        RAISE NOTICE 'Compensated step: %', v_step.step_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Exemplo de uso: pedido de e-commerce
BEGIN;

-- Step 1: Criar registro da saga
INSERT INTO saga_log (step_number, step_name, compensation_payload)
VALUES
    (1, 'reserve_inventory', '{"product_id": 42, "quantity": 2}'),
    (2, 'process_payment', '{"amount": 299.99, "card_token": "tok_xxx"}'),
    (3, 'create_shipment', '{"address_id": 100}');

-- Step 1: Reservar estoque
UPDATE inventory
SET reserved = reserved + 2
WHERE product_id = 42
AND stock - reserved >= 2;

-- Se falhar, ROLLBACK a transação inteira (saga local)

-- Step 2: Processar pagamento
-- (chamada API externa, registro local)

-- Step 3: Criar envio

COMMIT;
```

### TCC Pattern (Try-Confirm-Cancel)

TCC é um padrão que separa a reserva de recursos (Try), a confirmação (Confirm) e o cancelamento (Cancel) em operações distintas.

```sql
-- Tabela de pedidos TCC
CREATE TABLE orders_tcc (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'trying',
    total DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    cancelled_at TIMESTAMP
);

-- Tabela de reservas de estoque
CREATE TABLE inventory_reservations (
    reservation_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders_tcc(order_id),
    product_id INTEGER,
    quantity INTEGER,
    reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

-- Função TRY: Reservar recursos
CREATE OR REPLACE FUNCTION tcc_try(
    p_order_id INTEGER,
    p_product_id INTEGER,
    p_quantity INTEGER,
    p_ttl_seconds INTEGER DEFAULT 300
) RETURNS BOOLEAN AS $$
DECLARE
    v_available INTEGER;
BEGIN
    -- Verificar disponibilidade
    SELECT stock - reserved INTO v_available
    FROM inventory
    WHERE product_id = p_product_id
    FOR UPDATE;

    IF v_available < p_quantity THEN
        RETURN FALSE;
    END IF;

    -- Criar reserva
    INSERT INTO inventory_reservations (order_id, product_id, quantity, expires_at)
    VALUES (p_order_id, p_product_id, p_quantity,
            CURRENT_TIMESTAMP + (p_ttl_seconds || ' seconds')::INTERVAL);

    -- Atualizar estoque reservado
    UPDATE inventory
    SET reserved = reserved + p_quantity
    WHERE product_id = p_product_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Função CONFIRM: Confirmar a operação
CREATE OR REPLACE FUNCTION tcc_confirm(p_order_id INTEGER) RETURNS BOOLEAN AS $$
DECLARE
    v_reservation RECORD;
BEGIN
    -- Confirmar cada reserva
    FOR v_reservation IN
        SELECT * FROM inventory_reservations
        WHERE order_id = p_order_id
        AND status = 'active'
    LOOP
        -- Deduzir do estoque real
        UPDATE inventory
        SET stock = stock - v_reservation.quantity,
            reserved = reserved - v_reservation.quantity
        WHERE product_id = v_reservation.product_id;

        -- Marcar reserva como confirmada
        UPDATE inventory_reservations
        SET status = 'confirmed'
        WHERE reservation_id = v_reservation.reservation_id;
    END LOOP;

    -- Atualizar status do pedido
    UPDATE orders_tcc
    SET status = 'confirmed',
        confirmed_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Função CANCEL: Cancelar e liberar recursos
CREATE OR REPLACE FUNCTION tcc_cancel(p_order_id INTEGER) RETURNS BOOLEAN AS $$
DECLARE
    v_reservation RECORD;
BEGIN
    -- Liberar cada reserva
    FOR v_reservation IN
        SELECT * FROM inventory_reservations
        WHERE order_id = p_order_id
        AND status = 'active'
    LOOP
        -- Devolver ao estoque
        UPDATE inventory
        SET reserved = reserved - v_reservation.quantity
        WHERE product_id = v_reservation.product_id;

        -- Marcar reserva como cancelada
        UPDATE inventory_reservations
        SET status = 'cancelled'
        WHERE reservation_id = v_reservation.reservation_id;
    END LOOP;

    -- Atualizar status do pedido
    UPDATE orders_tcc
    SET status = 'cancelled',
        cancelled_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Função para limpar reservas expiradas (cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_reservations() RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE inventory_reservations
    SET status = 'expired'
    WHERE status = 'active'
    AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    -- Liberar estoque das reservas expiradas
    UPDATE inventory i
    SET reserved = reserved - er.quantity
    FROM inventory_reservations er
    WHERE i.product_id = er.product_id
    AND er.status = 'expired'
    AND er.expires_at < CURRENT_TIMESTAMP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
```

## Exemplo Prático: Deadlock e Resolução

### Cenário Completo

Vamos criar um cenário realista de deadlock em um sistema bancário e implementar a resolução completa.

```sql
-- Schema do sistema bancário
CREATE TABLE bank_accounts (
    account_id SERIAL PRIMARY KEY,
    holder_name VARCHAR(100) NOT NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT positive_balance CHECK (balance >= 0)
);

CREATE TABLE bank_transactions (
    transaction_id SERIAL PRIMARY KEY,
    from_account INTEGER REFERENCES bank_accounts(account_id),
    to_account INTEGER REFERENCES bank_accounts(account_id),
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE bank_audit_log (
    log_id SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES bank_transactions(transaction_id),
    action VARCHAR(50),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados de teste
INSERT INTO bank_accounts (holder_name, balance) VALUES
    ('Alice', 5000.00),
    ('Bob', 3000.00),
    ('Charlie', 7500.00),
    ('Diana', 1200.00);

-- Função de transferência COM deadlock detection
CREATE OR REPLACE FUNCTION bank_transfer_safe(
    p_from_id INTEGER,
    p_to_id INTEGER,
    p_amount DECIMAL
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_max_retries INTEGER := 3;
    v_retry INTEGER := 0;
    v_success BOOLEAN := FALSE;
    v_from_balance DECIMAL;
    v_tx_id INTEGER;
BEGIN
    WHILE v_retry < v_max_retries AND NOT v_success LOOP
        BEGIN
            -- Criar registro da transação
            INSERT INTO bank_transactions (from_account, to_account, amount, status)
            VALUES (p_from_id, p_to_id, p_amount, 'processing')
            RETURNING transaction_id INTO v_tx_id;

            -- Usar NOWAIT para falhar imediatamente em caso de lock
            -- Acessar contas em ordem crescente para evitar deadlock
            IF p_from_id < p_to_id THEN
                SELECT balance INTO v_from_balance
                FROM bank_accounts
                WHERE account_id = p_from_id
                FOR UPDATE NOWAIT;

                IF v_from_balance < p_amount THEN
                    UPDATE bank_transactions
                    SET status = 'failed'
                    WHERE transaction_id = v_tx_id;
                    RETURN QUERY SELECT FALSE, 'Insufficient funds'::TEXT;
                    RETURN;
                END IF;

                UPDATE bank_accounts
                SET balance = balance - p_amount,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = p_from_id;

                UPDATE bank_accounts
                SET balance = balance + p_amount,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = p_to_id;
            ELSE
                -- Ordem inversa para manter consistência
                SELECT balance INTO v_from_balance
                FROM bank_accounts
                WHERE account_id = p_from_id
                FOR UPDATE NOWAIT;

                IF v_from_balance < p_amount THEN
                    UPDATE bank_transactions
                    SET status = 'failed'
                    WHERE transaction_id = v_tx_id;
                    RETURN QUERY SELECT FALSE, 'Insufficient funds'::TEXT;
                    RETURN;
                END IF;

                UPDATE bank_accounts
                SET balance = balance + p_amount,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = p_to_id;

                UPDATE bank_accounts
                SET balance = balance - p_amount,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = p_from_id;
            END IF;

            -- Registrar sucesso
            UPDATE bank_transactions
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE transaction_id = v_tx_id;

            INSERT INTO bank_audit_log (transaction_id, action, details)
            VALUES (v_tx_id, 'transfer_completed',
                jsonb_build_object('from', p_from_id, 'to', p_to_id, 'amount', p_amount));

            v_success := TRUE;

        EXCEPTION
            WHEN deadlock_detected THEN
                v_retry := v_retry + 1;
                RAISE NOTICE 'Deadlock detected on attempt %, retrying...', v_retry;
                -- Espera aleatória para evitar thundering herd
                PERFORM pg_sleep(random() * 0.1 + 0.01);
            WHEN lock_not_available THEN
                v_retry := v_retry + 1;
                RAISE NOTICE 'Lock timeout on attempt %, retrying...', v_retry;
                PERFORM pg_sleep(random() * 0.05);
            WHEN OTHERS THEN
                -- Erro inesperado, abortar
                UPDATE bank_transactions
                SET status = 'error'
                WHERE transaction_id = v_tx_id;
                RAISE;
        END;
    END LOOP;

    IF NOT v_success THEN
        UPDATE bank_transactions
        SET status = 'failed'
        WHERE transaction_id = v_tx_id;
        RETURN QUERY SELECT FALSE, 'Max retries exceeded'::TEXT;
    ELSE
        RETURN QUERY SELECT TRUE, 'Transfer completed'::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Monitoramento de transações
CREATE OR REPLACE VIEW transaction_monitor AS
SELECT
    bt.transaction_id,
    ba_from.holder_name AS from_holder,
    ba_to.holder_name AS to_holder,
    bt.amount,
    bt.status,
    bt.created_at,
    bt.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(bt.completed_at, NOW()) - bt.created_at)) AS duration_seconds
FROM bank_transactions bt
JOIN bank_accounts ba_from ON bt.from_account = ba_from.account_id
JOIN bank_accounts ba_to ON bt.to_account = ba_to.account_id
ORDER BY bt.created_at DESC;

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_bank_accounts_updated
    BEFORE UPDATE ON bank_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Índices para performance
CREATE INDEX idx_bank_transactions_from ON bank_transactions(from_account);
CREATE INDEX idx_bank_transactions_to ON bank_transactions(to_account);
CREATE INDEX idx_bank_transactions_status ON bank_transactions(status);
CREATE INDEX idx_bank_accounts_balance ON bank_accounts(balance);
CREATE INDEX idx_audit_log_transaction ON bank_audit_log(transaction_id);
```

### Teste de Deadlock

```sql
-- Script de teste: simular 10 transferências concorrentes
-- Executar em duas sessões simultaneamente

-- Sessão 1
BEGIN;
SELECT bank_transfer_safe(1, 2, 100);
-- Pode deadlock com sessão 2 se acessar contas em ordem diferente

-- Sessão 2 (executar ao mesmo tempo)
BEGIN;
SELECT bank_transfer_safe(2, 1, 200);
-- deadlock detected! Retry automático resolve o problema

-- Verificar resultado
SELECT * FROM transaction_monitor LIMIT 10;
-- Todas as transações devem estar 'completed' ou 'failed' (nunca 'processing')

-- Verificar saldos
SELECT account_id, holder_name, balance
FROM bank_accounts;
-- Saldos devem ser consistentes (soma total inalterada)

-- Verificar logs de auditoria
SELECT * FROM bank_audit_log ORDER BY created_at DESC LIMIT 10;
```

## Configurações Avançadas de Transação

### Configurações do PostgreSQL

```sql
-- Nível de isolamento padrão
SHOW default_transaction_isolation;
-- Padrão: read committed

-- Modificar para a sessão
SET default_transaction_isolation = 'repeatable read';

-- Transação somente leitura
SET TRANSACTION READ ONLY;
-- Útil para relatórios que não devem modificar dados

-- Definir timeout de transação
SET statement_timeout = '30s'; -- Falha após 30 segundos
SET idle_in_transaction_session_timeout = '60s'; -- Fecha sessões ociosas

-- Configurações de lock
SET lock_timeout = '5s';
SET deadlock_timeout = '1s';

-- Logging de transações
SET log_statement = 'all';
SET log_min_duration_statement = 100; -- Log queries > 100ms
SET log_lock_waits = on;
SET log_temp_files = 0; -- Log todas as operações temporárias

-- Verificar configurações ativas
SELECT
    name,
    setting,
    unit,
    category
FROM pg_settings
WHERE name IN (
    'default_transaction_isolation',
    'statement_timeout',
    'lock_timeout',
    'deadlock_timeout',
    'log_lock_waits'
);
```

### Transações Prepared (2PC)

Two-Phase Commit permite coordenar transações que envolvem múltiplos recursos (como bancos de dados diferentes).

```sql
-- Fase 1: PREPARE
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE remote_accounts SET balance = balance + 100 WHERE id = 2;

-- Preparar a transação (não confirma ainda)
PREPARE TRANSACTION 'transfer_12345';
-- A transação está pronta mas não foi commitada

-- Fase 2: COMMIT ou ROLLBACK
-- Se todos os participantes estiverem prontos
COMMIT PREPARED 'transfer_12345';

-- Se algum participante falhar
ROLLBACK PREPARED 'transfer_12345';

-- Verificar transações prepared pendentes
SELECT * FROM pg_prepared_xacts;
```

## Transaction Timeout e Resource Management

### Statement Timeout

```sql
-- Configurar timeout global para statements
SET statement_timeout = '30s';
-- Qualquer query que execute mais de 30 segundos será cancelada

-- Configurar timeout por sessão
SET LOCAL statement_timeout = '10s';
-- Afeta apenas a transação atual

-- Configurar timeout por tabela
ALTER TABLE orders SET (statement_timeout = '5s');
-- Queries na tabela orders têm timeout de 5 segundos

-- Verificar configuração atual
SHOW statement_timeout;

-- Exemplo de tratamento de timeout
DO $$
BEGIN
    SET LOCAL statement_timeout = '5s';

    -- Operação que pode demorar
    PERFORM complex_aggregation();

EXCEPTION
    WHEN query_canceled THEN
        RAISE NOTICE 'Query was cancelled due to timeout';
        -- Tratar o timeout adequadamente
END;
$$;
```

### Idle Transaction Timeout

```sql
-- Fechar sessões que ficam ociosas dentro de uma transação
SET idle_in_transaction_session_timeout = '60s';
-- Se uma transação ficar idle por 60 segundos, a sessão é fechada

-- Verificar configuração
SHOW idle_in_transaction_session_timeout;

-- Monitorar transações idle há muito tempo
SELECT
    pid,
    usename,
    state,
    query,
    query_start,
    NOW() - query_start AS duration,
    state_change,
    NOW() - state_change AS idle_duration
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND NOW() - state_change > INTERVAL '5 minutes'
ORDER BY idle_duration DESC;

-- Matar transações idle há muito tempo
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
AND NOW() - state_change > INTERVAL '10 minutes';
```

### Lock Timeout

```sql
-- Configurar timeout para aquisição de locks
SET lock_timeout = '5s';
-- Se não conseguir o lock em 5 segundos, retorna erro

-- Tratamento de lock timeout
DO $$
BEGIN
    SET LOCAL lock_timeout = '3s';

    -- Tentar adquirir lock exclusivo
    LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;

    -- Se não conseguir em 3 segundos, erro será lançado

EXCEPTION
    WHEN lock_not_available THEN
        RAISE NOTICE 'Could not acquire lock within timeout';
        -- Retry ou abortar operação
END;
$$;

-- Verificar locks ativos e tempo de espera
SELECT
    l.pid,
    l.locktype,
    l.relation::regclass,
    l.mode,
    l.granted,
    a.usename,
    a.query,
    NOW() - a.query_start AS lock_duration
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.granted = false
ORDER BY l.wait_start;
```

## Transaction Logging e Audit Trail

### pgAudit

```sql
-- Instalar extensão pgAudit
-- CREATE EXTENSION pgaudit;

-- Configurar logging no postgresql.conf
-- shared_preload_libraries = 'pgaudit'
-- pgaudit.log = 'read, write, function'
-- pgaudit.log_parameter = on
-- pgaudit.log_statement_once = off

-- Configurar por.role
ALTER ROLE app_user SET pgaudit.log = 'write';
ALTER ROLE admin SET pgaudit.log = 'all';

-- Exemplo de log gerado
-- AUDIT: SESSION,1,1,WRITE,INSERT,,,"INSERT INTO orders (customer_id, total) VALUES (42, 150.00);",<none>
```

### Tabela de Auditoria Manual

```sql
-- Criar tabela de auditoria
CREATE TABLE audit_trail (
    audit_id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100) DEFAULT current_user,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_ip INET DEFAULT inet_client_addr(),
    application_name VARCHAR(100) DEFAULT current_setting('application_name')
);

-- Função de auditoria genérica
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_trail (table_name, operation, new_data)
        VALUES (TG_TABLE_NAME, 'INSERT', row_to_json(NEW)::JSONB);
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_trail (table_name, operation, old_data, new_data)
        VALUES (TG_TABLE_NAME, 'UPDATE', row_to_json(OLD)::JSONB, row_to_json(NEW)::JSONB);
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_trail (table_name, operation, old_data)
        VALUES (TG_TABLE_NAME, 'DELETE', row_to_json(OLD)::JSONB);
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Criar triggers de auditoria
CREATE TRIGGER audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_customers
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Consultar auditoria
SELECT
    table_name,
    operation,
    changed_by,
    changed_at,
    old_data,
    new_data
FROM audit_trail
WHERE table_name = 'orders'
AND operation = 'UPDATE'
AND changed_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY changed_at DESC;

-- Relatório de atividade por usuário
SELECT
    changed_by,
    table_name,
    operation,
    COUNT(*) as count,
    MIN(changed_at) as first_change,
    MAX(changed_at) as last_change
FROM audit_trail
WHERE changed_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY changed_by, table_name, operation
ORDER BY count DESC;
```

## Savepoints Avançados

### Savepoints com Procedures

```sql
-- Procedimento complexo com múltiplos savepoints
CREATE OR REPLACE FUNCTION process_order_batch(
    p_batch_id INTEGER
) RETURNS TABLE(
    processed INTEGER,
    failed INTEGER,
    errors TEXT[]
) AS $$
DECLARE
    v_order RECORD;
    v_processed INTEGER := 0;
    v_failed INTEGER := 0;
    v_errors TEXT[] := ARRAY[]::TEXT[];
    v_savepoint_name TEXT;
BEGIN
    FOR v_order IN
        SELECT order_id, customer_id, total
        FROM orders
        WHERE batch_id = p_batch_id
        AND status = 'pending'
    LOOP
        v_savepoint_name := 'order_' || v_order.order_id;

        BEGIN
            -- Criar savepoint para cada pedido
            EXECUTE 'SAVEPOINT ' || v_savepoint_name;

            -- Processar pedido
            UPDATE orders
            SET status = 'processing'
            WHERE order_id = v_order.order_id;

            -- Debitar estoque
            UPDATE inventory
            SET stock = stock - 1
            WHERE product_id = (
                SELECT product_id FROM order_items
                WHERE order_id = v_order.order_id
                LIMIT 1
            );

            -- Se chegou aqui, sucesso
            v_processed := v_processed + 1;

        EXCEPTION
            WHEN OTHERS THEN
                -- Rollback apenas este pedido
                EXECUTE 'ROLLBACK TO ' || v_savepoint_name;
                v_failed := v_failed + 1;
                v_errors := array_append(v_errors,
                    v_order.order_id || ': ' || SQLERRM);

                -- Marcar pedido como erro
                UPDATE orders
                SET status = 'error',
                    error_message = SQLERRM
                WHERE order_id = v_order.order_id;
        END;
    END LOOP;

    RETURN QUERY SELECT v_processed, v_failed, v_errors;
END;
$$ LANGUAGE plpgsql;
```

### Nested Savepoints

```sql
-- Savepoints aninhados
BEGIN;

    -- Operação principal
    INSERT INTO orders (customer_id, total) VALUES (1, 100)
        RETURNING order_id INTO v_order_id;

    SAVEPOINT after_order;

        -- Primeiro nível de operações
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES (v_order_id, 1, 2, 25);

        SAVEPOINT after_item1;

            -- Operação que pode falhar
            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES (v_order_id, 999, 1, 50);
            -- Erro: produto 999 não existe

        -- Rollback para savepoint anterior
        ROLLBACK TO after_item1;
        -- order_items com produto 999 é desfeito
        -- order_items com produto 1 permanece

    -- Operação alternativa
    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
    VALUES (v_order_id, 2, 1, 50);

    -- Rollback completo se necessário
    -- ROLLBACK TO after_order;
    -- Tudo após after_order é desfeito

COMMIT;
-- Apenas as operações válidas são persistidas
```

## Transaction Patterns Avançados

### Outbox Pattern

```sql
-- Tabela outbox para garantir delivery de mensagens
CREATE TABLE outbox (
    outbox_id BIGSERIAL PRIMARY KEY,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

-- Função para processar pedido e publicar evento atomicamente
CREATE OR REPLACE FUNCTION place_order_with_outbox(
    p_customer_id INTEGER,
    p_items JSONB
) RETURNS BIGINT AS $$
DECLARE
    v_order_id BIGINT;
    v_total DECIMAL := 0;
    v_item JSONB;
BEGIN
    -- Criar pedido
    INSERT INTO orders (customer_id, total, status)
    VALUES (p_customer_id, 0, 'pending')
    RETURNING order_id INTO v_order_id;

    -- Processar itens
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES (
            v_order_id,
            (v_item ->> 'product_id')::INTEGER,
            (v_item ->> 'quantity')::INTEGER,
            (v_item ->> 'price')::DECIMAL
        );

        v_total := v_total +
            (v_item ->> 'quantity')::INTEGER *
            (v_item ->> 'price')::DECIMAL;
    END LOOP;

    -- Atualizar total
    UPDATE orders SET total = v_total WHERE order_id = v_order_id;

    -- Publicar evento na outbox (mesma transação!)
    INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload)
    VALUES (
        'order',
        v_order_id::TEXT,
        'OrderPlaced',
        jsonb_build_object(
            'order_id', v_order_id,
            'customer_id', p_customer_id,
            'total', v_total,
            'items', p_items
        )
    );

    RETURN v_order_id;
END;
$$ LANGUAGE plqlpgsql;

-- Processador de outbox (executa periodicamente)
CREATE OR REPLACE FUNCTION process_outbox()
RETURNS INTEGER AS $$
DECLARE
    v_record RECORD;
    v_count INTEGER := 0;
BEGIN
    FOR v_record IN
        SELECT * FROM outbox
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT 100
        FOR UPDATE SKIP LOCKED
    LOOP
        BEGIN
            -- Publicar mensagem (simulado)
            -- Na prática: enviar para Kafka, RabbitMQ, etc.
            PERFORM pg_notify('outbox_channel',
                jsonb_build_object(
                    'event_type', v_record.event_type,
                    'payload', v_record.payload
                )::TEXT
            );

            -- Marcar como publicado
            UPDATE outbox
            SET status = 'published',
                published_at = CURRENT_TIMESTAMP
            WHERE outbox_id = v_record.outbox_id;

            v_count := v_count + 1;

        EXCEPTION
            WHEN OTHERS THEN
                UPDATE outbox
                SET status = 'failed',
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'),
                        '{error}',
                        to_jsonb(SQLERRM)
                    )
                WHERE outbox_id = v_record.outbox_id;
        END;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
```

### Event Sourcing

```sql
-- Tabela de eventos para Event Sourcing
CREATE TABLE events (
    event_id BIGSERIAL PRIMARY KEY,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB,
    version INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (aggregate_id, version)
);

-- Tabela de projeções (read model)
CREATE TABLE order_projections (
    order_id BIGINT PRIMARY KEY,
    customer_id INTEGER,
    status VARCHAR(20),
    total DECIMAL(12,2),
    items_count INTEGER,
    last_updated TIMESTAMP,
    version INTEGER
);

-- Função para aplicar evento e atualizar projeção
CREATE OR REPLACE FUNCTION apply_event(
    p_aggregate_id UUID,
    p_event_type VARCHAR,
    p_event_data JSONB
) RETURNS void AS $$
DECLARE
    v_version INTEGER;
BEGIN
    -- Obter versão atual
    SELECT COALESCE(MAX(version), 0) + 1 INTO v_version
    FROM events
    WHERE aggregate_id = p_aggregate_id;

    -- Inserir evento
    INSERT INTO events (aggregate_id, aggregate_type, event_type, event_data, version)
    VALUES (p_aggregate_id, 'order', p_event_type, p_event_data, v_version);

    -- Atualizar projeção baseado no tipo de evento
    CASE p_event_type
        WHEN 'OrderCreated' THEN
            INSERT INTO order_projections (order_id, customer_id, status, total, items_count, last_updated, version)
            VALUES (
                (p_event_data ->> 'order_id')::BIGINT,
                (p_event_data ->> 'customer_id')::INTEGER,
                'created',
                0,
                0,
                CURRENT_TIMESTAMP,
                v_version
            );

        WHEN 'ItemAdded' THEN
            UPDATE order_projections
            SET total = total + (p_event_data ->> 'amount')::DECIMAL,
                items_count = items_count + 1,
                last_updated = CURRENT_TIMESTAMP,
                version = v_version
            WHERE order_id = (p_event_data ->> 'order_id')::BIGINT;

        WHEN 'OrderConfirmed' THEN
            UPDATE order_projections
            SET status = 'confirmed',
                last_updated = CURRENT_TIMESTAMP,
                version = v_version
            WHERE order_id = (p_event_data ->> 'order_id')::BIGINT;

        WHEN 'OrderShipped' THEN
            UPDATE order_projections
            SET status = 'shipped',
                last_updated = CURRENT_TIMESTAMP,
                version = v_version
            WHERE order_id = (p_event_data ->> 'order_id')::BIGINT;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Reconstituir estado a partir de eventos
CREATE OR REPLACE FUNCTION get_aggregate_state(p_aggregate_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_event RECORD;
    v_state JSONB := '{}';
BEGIN
    FOR v_event IN
        SELECT event_type, event_data
        FROM events
        WHERE aggregate_id = p_aggregate_id
        ORDER BY version
    LOOP
        CASE v_event.event_type
            WHEN 'OrderCreated' THEN
                v_state := v_event.event_data;
            WHEN 'ItemAdded' THEN
                v_state := jsonb_set(
                    v_state,
                    '{items}',
                    COALESCE(v_state -> 'items', '[]'::JSONB) ||
                    jsonb_build_array(v_event.event_data)
                );
            WHEN 'OrderConfirmed' THEN
                v_state := jsonb_set(v_state, '{status}', '"confirmed"');
            WHEN 'OrderShipped' THEN
                v_state := jsonb_set(v_state, '{status}', '"shipped"');
        END CASE;
    END LOOP;

    RETURN v_state;
END;
$$ LANGUAGE plpgsql;
```

## Transaction Isolation em Bancos Diferentes

### MySQL/InnoDB

```sql
-- MySQL: verificar nível de isolamento
SELECT @@transaction_isolation;
-- Padrão: REPEATABLE READ (diferente do PostgreSQL que usa READ COMMITTED)

-- Configurar nível de isolamento
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- MySQL: deadlock detection
SHOW ENGINE INNODB STATUS;
-- Seção LATEST DETECTED DEADLOCK mostra detalhes

-- MySQL: locks
SELECT * FROM information_schema.INNODB_LOCKS;
SELECT * FROM information_schema.INNODB_LOCK_WAITS;
SELECT * FROM information_schema.INNODB_TRX;
```

### SQL Server

```sql
-- SQL Server: níveis de isolamento
SET TRANSACTION ISOLATION LEVEL SNAPSHOT;
-- Equivalente ao MVCC do PostgreSQL

-- SQL Server: snapshot isolation
ALTER DATABASE MyDatabase SET ALLOW_SNAPSHOT_ISOLATION ON;
ALTER DATABASE MyDatabase SET READ_COMMITTED_SNAPSHOT ON;

-- SQL Server: row versioning
SELECT
    transaction_id,
    transaction_status,
    transaction_description
FROM sys.dm_tran_active_snapshot_database_transactions;
```

## Transaction Monitoring e Observability

### Métricas de Transação

```sql
-- View para monitorar transações ativas
CREATE OR REPLACE VIEW active_transactions AS
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    query_start,
    state_change,
    NOW() - query_start AS query_duration,
    NOW() - state_change AS state_duration,
   /backend_type,
    backend_start,
    xact_start
FROM pg_stat_activity
WHERE state != 'idle'
AND backend_type = 'client backend'
ORDER BY query_start;

-- View para transações longas
CREATE OR REPLACE VIEW long_running_transactions AS
SELECT
    pid,
    usename,
    state,
    LEFT(query, 100) AS query_preview,
    query_start,
    NOW() - query_start AS duration,
    backend_type
FROM pg_stat_activity
WHERE state = 'active'
AND NOW() - query_start > INTERVAL '5 minutes'
ORDER BY duration DESC;

-- View de locks ativos
CREATE OR REPLACE VIEW active_locks AS
SELECT
    l.pid,
    l.locktype,
    l.relation::regclass AS table_name,
    l.mode,
    l.granted,
    l.page,
    l.tuple,
    a.usename,
    a.query,
    a.query_start,
    NOW() - a.query_start AS lock_duration
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE l.relation IS NOT NULL
ORDER BY l.pid, l.locktype;

-- Alertas de transações problemáticas
DO $$
DECLARE
    v_tx RECORD;
BEGIN
    -- Transações abertas há muito tempo
    FOR v_tx IN
        SELECT * FROM long_running_transactions
        WHERE duration > INTERVAL '10 minutes'
    LOOP
        RAISE WARNING 'Long transaction (pid: %): % running for %',
            v_tx.pid,
            LEFT(v_tx.query_preview, 50),
            v_tx.duration;
    END LOOP;

    -- Transações idle in transaction
    FOR v_tx IN
        SELECT
            pid,
            usename,
            state,
            LEFT(query, 100) AS query_preview,
            state_change,
            NOW() - state_change AS idle_duration
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
        AND NOW() - state_change > INTERVAL '5 minutes'
    LOOP
        RAISE WARNING 'Idle transaction (pid: %): idle for %',
            v_tx.pid,
            v_tx.idle_duration;
    END LOOP;
END;
$$;
```

### Performance Tuning de Transações

```sql
-- Configurações de performance para transações
-- Batch inserts para reduzir overhead de transação
CREATE OR REPLACE FUNCTION batch_insert_orders(
    p_orders JSONB
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
    v_order JSONB;
    v_batch_size INTEGER := 1000;
    v_batch JSONB;
BEGIN
    -- Processar em lotes para evitar transações longas
    FOR i IN 0..jsonb_array_length(p_orders) - 1 BY v_batch_size LOOP
        v_batch := p_orders -> i || ']' || '[' || p_orders -> (i + v_batch_size - 1);

        BEGIN
            -- Cada lote é uma transação separada
            INSERT INTO orders (customer_id, total, status)
            SELECT
                (value ->> 'customer_id')::INTEGER,
                (value ->> 'total')::DECIMAL,
                (value ->> 'status')::VARCHAR
            FROM jsonb_array_elements(v_batch);

            v_count := v_count + jsonb_array_length(v_batch);

        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Batch starting at % failed: %', i, SQLERRM;
                -- Continuar com próximo lote
        END;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Otimização de locks para alta concorrência
CREATE OR REPLACE FUNCTION high_concurrency_update(
    p_table_name TEXT,
    p_id INTEGER,
    p_column TEXT,
    p_value TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_max_retries INTEGER := 5;
    v_retry INTEGER := 0;
    v_success BOOLEAN := FALSE;
BEGIN
    WHILE v_retry < v_max_retries AND NOT v_success LOOP
        BEGIN
            -- Usar NOWAIT para falhar imediatamente
            EXECUTE format(
                'UPDATE %I SET %I = $1 WHERE id = $2',
                p_table_name, p_column
            ) USING p_value, p_id;

            v_success := TRUE;

        EXCEPTION
            WHEN lock_not_available THEN
                v_retry := v_retry + 1;
                -- Backoff exponencial
                PERFORM pg_sleep(power(2, v_retry) * 0.01);
            WHEN deadlock_detected THEN
                v_retry := v_retry + 1;
                PERFORM pg_sleep(random() * 0.05);
        END;
    END LOOP;

    RETURN v_success;
END;
$$ LANGUAGE plpgsql;
```

### Transaction Isolation Testing

```sql
-- Função para testar comportamento de isolamento
CREATE OR REPLACE FUNCTION test_isolation_behavior()
RETURNS void AS $$
DECLARE
    v_result RECORD;
BEGIN
    -- Setup: criar tabela de teste
    CREATE TEMPORARY TABLE test_isolation (
        id INTEGER PRIMARY KEY,
        value INTEGER
    );

    INSERT INTO test_isolation VALUES (1, 100);

    -- Teste 1: Dirty Read
    RAISE NOTICE '=== Test 1: Dirty Read ===';

    -- Sessão A (simulada com dblink)
    PERFORM dblink_exec(
        'host=localhost dbname=testdb',
        'BEGIN; UPDATE test_isolation SET value = 200 WHERE id = 1;'
    );

    -- Sessão B lê (com READ UNCOMMITTED deveria ver 200)
    RAISE NOTICE 'Value read by session B: %',
        (SELECT value FROM test_isolation WHERE id = 1);

    -- Sessão A faz rollback
    PERFORM dblink_exec('host=localhost dbname=testdb', 'ROLLBACK;');

    -- Limpar
    DROP TABLE test_isolation;
END;
$$ LANGUAGE plpgsql;
```

## Best Practices de Transações

### Padrões Recomendados

```sql
-- Padrão 1: Transação curta
-- ERRADO: transação longa com operações externas
BEGIN;
SELECT * FROM accounts WHERE id = 1;
-- Chamar API externa (segundos...)
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;

-- CORRETO: transação curta
BEGIN;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
-- Verificar saldo antes
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;
-- Chamar API externa DEPOIS do commit

-- Padrão 2: Uso adequado de isolamento
-- Para relatórios: READ COMMITTED é suficiente
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
SELECT COUNT(*) FROM orders WHERE created_at >= CURRENT_DATE;

-- Para transferências financeiras: REPEATABLE READ ou SERIALIZABLE
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;
SELECT balance FROM accounts WHERE id = 1;
-- Verificar e processar
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;

-- Padrão 3: Retry automático para deadlocks
CREATE OR REPLACE FUNCTION safe_update(
    p_table TEXT,
    p_id INTEGER,
    p_column TEXT,
    p_value TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_max_retries INTEGER := 3;
    v_retry INTEGER := 0;
    v_success BOOLEAN := FALSE;
BEGIN
    WHILE v_retry < v_max_retries AND NOT v_success LOOP
        BEGIN
            EXECUTE format(
                'UPDATE %I SET %I = %L WHERE id = %L',
                p_table, p_column, p_value, p_id
            );
            v_success := TRUE;
        EXCEPTION
            WHEN deadlock_detected THEN
                v_retry := v_retry + 1;
                PERFORM pg_sleep(random() * 0.1);
            WHEN lock_not_available THEN
                v_retry := v_retry + 1;
                PERFORM pg_sleep(0.05);
        END;
    END LOOP;
    RETURN v_success;
END;
$$ LANGUAGE plpgsql;
```

### Anti-Padrões

```sql
-- Anti-padrão 1: Transação muito longa
-- NÃO FAÇA:
BEGIN;
-- 1000 inserts
INSERT INTO logs SELECT * FROM huge_table;
-- Processamento complexo
-- ... 5 minutos depois ...
UPDATE statistics SET last_run = NOW();
COMMIT;
-- Problema: locks mantidos por muito tempo, MVCC acumula tuplas mortas

-- Anti-padrão 2: SELECT FOR UPDATE desnecessário
-- NÃO FAÇA:
BEGIN;
SELECT * FROM accounts WHERE id = 1 FOR UPDATE; -- Lock desnecessário
-- Apenas ler saldo
SELECT balance FROM accounts WHERE id = 1;
COMMIT;
-- Problema: lock mantido sem necessidade

-- Anti-padrão 3: COMMIT em loop
-- NÃO FAÇA:
FOR i IN 1..10000 LOOP
    BEGIN;
    INSERT INTO logs (message) VALUES ('log ' || i);
    COMMIT;
END LOOP;
-- Problema: overhead de 10000 transações

-- CORRETO: batch com commit periódico
FOR i IN 1..10000 LOOP
    INSERT INTO logs (message) VALUES ('log ' || i);
    IF i % 1000 = 0 THEN
        COMMIT;
        BEGIN;
    END IF;
END LOOP;
COMMIT;
```

## Transaction Patterns Avançados

### CQRS (Command Query Responsibility Segregation)

```sql
-- Separar model de escrita (command) do model de leitura (query)
-- Tabela de escrita (normalized)
CREATE TABLE orders_write (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items_write (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders_write(order_id),
    product_id INTEGER,
    quantity INTEGER,
    unit_price DECIMAL(10,2)
);

-- Tabela de leitura (denormalized para performance)
CREATE TABLE orders_read (
    order_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(100),
    customer_email VARCHAR(255),
    status VARCHAR(20),
    total DECIMAL(12,2),
    items_count INTEGER,
    items_summary TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Sincronizar write para read via triggers ou CDC
CREATE OR REPLACE FUNCTION sync_order_to_read()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO orders_read (
        order_id, customer_name, customer_email,
        status, total, items_count, items_summary, created_at
    )
    SELECT
        NEW.order_id,
        c.name,
        c.email,
        NEW.status,
        NEW.total,
        (SELECT COUNT(*) FROM order_items_write WHERE order_id = NEW.order_id),
        (SELECT string_agg(p.name || ' x' || oi.quantity, ', ')
         FROM order_items_write oi
         JOIN products p ON oi.product_id = p.product_id
         WHERE oi.order_id = NEW.order_id),
        NEW.created_at
    FROM customers c
    WHERE c.customer_id = NEW.customer_id
    ON CONFLICT (order_id) DO UPDATE SET
        status = EXCLUDED.status,
        total = EXCLUDED.total,
        items_count = EXCLUDED.items_count,
        items_summary = EXCLUDED.items_summary,
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_order
    AFTER INSERT OR UPDATE ON orders_write
    FOR EACH ROW EXECUTE FUNCTION sync_order_to_read();
```

### Domain Events Pattern

```sql
-- Tabela de eventos de domínio
CREATE TABLE domain_events (
    event_id BIGSERIAL PRIMARY KEY,
    aggregate_type VARCHAR(50) NOT NULL,
    aggregate_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published BOOLEAN DEFAULT false
);

-- Função para publicar evento após mudança de estado
CREATE OR REPLACE FUNCTION publish_order_event()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO domain_events (aggregate_type, aggregate_id, event_type, event_data)
        VALUES (
            'Order',
            NEW.order_id::TEXT,
            'OrderStatusChanged',
            jsonb_build_object(
                'order_id', NEW.order_id,
                'old_status', OLD.status,
                'new_status', NEW.status,
                'customer_id', NEW.customer_id,
                'total', NEW.total
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_order_events
    AFTER UPDATE ON orders_write
    FOR EACH ROW EXECUTE FUNCTION publish_order_event();

-- Processador de eventos (CDC - Change Data Capture)
CREATE OR REPLACE FUNCTION process_domain_events()
RETURNS INTEGER AS $$
DECLARE
    v_event RECORD;
    v_count INTEGER := 0;
BEGIN
    FOR v_event IN
        SELECT * FROM domain_events
        WHERE published = false
        ORDER BY occurred_at
        LIMIT 100
        FOR UPDATE SKIP LOCKED
    LOOP
        -- Publicar evento (simulado)
        PERFORM pg_notify('domain_events',
            jsonb_build_object(
                'event_id', v_event.event_id,
                'event_type', v_event.event_type,
                'aggregate_id', v_event.aggregate_id,
                'event_data', v_event.event_data
            )::TEXT
        );

        -- Marcar como publicado
        UPDATE domain_events
        SET published = true
        WHERE event_id = v_event.event_id;

        v_count := v_count + 1;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql;
```

### Optimistic Concurrency Control Avançado

```sql
-- Implementação completa de OCC com versionamento
CREATE TABLE products_occ (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    price DECIMAL(10,2),
    stock INTEGER,
    version INTEGER DEFAULT 1,
    last_updated_by VARCHAR(100),
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Função de atualização com OCC
CREATE OR REPLACE FUNCTION update_product_occ(
    p_product_id INTEGER,
    p_name VARCHAR,
    p_price DECIMAL,
    p_stock INTEGER,
    p_expected_version INTEGER,
    p_user VARCHAR
) RETURNS TABLE(
    success BOOLEAN,
    message TEXT,
    new_version INTEGER
) AS $$
DECLARE
    v_current_version INTEGER;
    v_rows_affected INTEGER;
BEGIN
    -- Verificar versão atual
    SELECT version INTO v_current_version
    FROM products_occ
    WHERE product_id = p_product_id;

    IF v_current_version IS NULL THEN
        RETURN QUERY SELECT false, 'Product not found'::TEXT, 0;
        RETURN;
    END IF;

    IF v_current_version != p_expected_version THEN
        RETURN QUERY SELECT false,
            format('Concurrent modification detected. Expected version %s, found %s',
                   p_expected_version, v_current_version),
            v_current_version;
        RETURN;
    END IF;

    -- Atualizar com verificação de versão
    UPDATE products_occ
    SET name = COALESCE(p_name, name),
        price = COALESCE(p_price, price),
        stock = COALESCE(p_stock, stock),
        version = version + 1,
        last_updated_by = p_user,
        last_updated_at = CURRENT_TIMESTAMP
    WHERE product_id = p_product_id
    AND version = p_expected_version;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

    IF v_rows_affected = 0 THEN
        RETURN QUERY SELECT false, 'Update failed - version mismatch'::TEXT, 0;
        RETURN;
    END IF;

    RETURN QUERY SELECT true, 'Updated successfully'::TEXT, p_expected_version + 1;
END;
$$ LANGUAGE plpgsql;

-- Exemplo de uso
SELECT * FROM update_product_occ(1, 'New Name', 99.99, 100, 5, 'admin');
-- success: true, message: 'Updated successfully', new_version: 6
```

## Transaction Testing

### Testes de Isolamento

```sql
-- Função para testar comportamento de concorrência
CREATE OR REPLACE FUNCTION test_concurrent_updates()
RETURNS void AS $$
DECLARE
    v_initial_balance DECIMAL;
    v_final_balance DECIMAL;
BEGIN
    -- Setup
    CREATE TEMPORARY TABLE test_accounts (
        id INTEGER PRIMARY KEY,
        balance DECIMAL
    );

    INSERT INTO test_accounts VALUES (1, 1000);

    -- Simular duas transações concorrentes
    -- Sessão 1: debit 100
    -- Sessão 2: debit 200
    -- Resultado esperado: balance = 700 (se serializável)

    SELECT balance INTO v_initial_balance FROM test_accounts WHERE id = 1;

    -- Executar transações concorrentes (simplificado)
    UPDATE test_accounts SET balance = balance - 100 WHERE id = 1;
    UPDATE test_accounts SET balance = balance - 200 WHERE id = 1;

    SELECT balance INTO v_final_balance FROM test_accounts WHERE id = 1;

    IF v_final_balance = 700 THEN
        RAISE NOTICE 'Test PASSED: balance is % (expected 700)', v_final_balance;
    ELSE
        RAISE WARNING 'Test FAILED: balance is % (expected 700)', v_final_balance;
    END IF;

    DROP TABLE test_accounts;
END;
$$ LANGUAGE plpgsql;

-- Executar teste
SELECT test_concurrent_updates();
```

### Load Testing de Transações

```sql
-- Função para testar carga de transações
CREATE OR REPLACE FUNCTION load_test_transations(
    p_num_transactions INTEGER DEFAULT 1000,
    p_concurrency INTEGER DEFAULT 10
) RETURNS TABLE(
    metric TEXT,
    value NUMERIC
) AS $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_duration INTERVAL;
    v_success_count INTEGER := 0;
    v_error_count INTEGER := 0;
    v_deadlock_count INTEGER := 0;
BEGIN
    v_start := clock_timestamp();

    -- Simular transações concorrentes
    FOR i IN 1..p_num_transactions LOOP
        BEGIN
            -- Simular operação de transferência
            UPDATE accounts SET balance = balance - 1 WHERE id = (i % 100) + 1;
            UPDATE accounts SET balance = balance + 1 WHERE id = ((i + 1) % 100) + 1;
            v_success_count := v_success_count + 1;

        EXCEPTION
            WHEN deadlock_detected THEN
                v_deadlock_count := v_deadlock_count + 1;
            WHEN OTHERS THEN
                v_error_count := v_error_count + 1;
        END;
    END LOOP;

    v_end := clock_timestamp();
    v_duration := v_end - v_start;

    -- Retornar métricas
    metric := 'total_transactions';
    value := p_num_transactions;
    RETURN NEXT;

    metric := 'successful';
    value := v_success_count;
    RETURN NEXT;

    metric := 'errors';
    value := v_error_count;
    RETURN NEXT;

    metric := 'deadlocks';
    value := v_deadlock_count;
    RETURN NEXT;

    metric := 'duration_seconds';
    value := EXTRACT(EPOCH FROM v_duration);
    RETURN NEXT;

    metric := 'transactions_per_second';
    value := p_num_transactions / EXTRACT(EPOCH FROM v_duration);
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Executar load test
SELECT * FROM load_test_transations(1000, 10);
```

## Resumo

Este capítulo cobriu os fundamentos e aspectos avançados de transações em bancos de dados relacionais. Os conceitos de ACID, níveis de isolamento, MVCC, deadlock detection e padrões como Saga e TCC são essenciais para construir sistemas robustos e escaláveis. A escolha correta da estratégia de locking e isolamento depende dos requisitos específicos de cada aplicação, equilibrando consistência, performance e complexidade de implementação.

## Referências

- PostgreSQL Documentation: Transaction Processing
- Database System Concepts (Silberschatz, Korth, Sudarsha)
- Designing Data-Intensive Applications (Martin Kleppmann)
- PostgreSQL 16 Release Notes - MVCC Improvements
- ISO/IEC 9075:2023 SQL Standard - Transaction Management
- MySQL 8.0 Reference Manual - InnoDB Transaction Model
- SQL Server Books Online - Transaction Isolation Levels
- Enterprise Integration Patterns (Hohpe, Woolf) - Saga Pattern
- Microservices Patterns (Chris Richardson) - Saga and TCC
- PostgreSQL High Performance (Gregory Smith)
- Database Reliability Engineering (Laine Campbell, Charity Majors)
- Building Microservices (Sam Newman) - CQRS Pattern
- Domain-Driven Design (Eric Evans) - Domain Events
