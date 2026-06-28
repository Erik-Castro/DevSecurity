# Boas Praticas e Checklist

## Visao Geral

Este capitulo final consolida todo o conhecimento dos capitulos anteriores em anti-patterns, checklists, templates e referencias rapidas. O objetivo e servir como guia pratico que pode ser consultado no dia-a-dia do desenvolvimento e administracao de databases seguros. Aqui voce encontra 20+ anti-patterns em SQL e databases, checklist de seguranca com 50+ itens, decisao de qual SGBDR escolher, templates seguros padrao e referencias rapidas para os topicos mais importantes.

## Anti-Patterns em SQL e Databases

### Anti-Pattern 1: SQL Injection via String Concatenation

```sql
-- ANTI-PATTERN: Concatenar inputs do usuario diretamente na query
-- Isso e o vetor de ataque mais comum e mais prejudicial

-- ERRADO (vulneravel a SQL injection):
SELECT * FROM users WHERE username = '' + @username + '' AND password = '' + @password + '';

-- ERRADO (tambem vulneravel):
query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"

-- CORRETO: Parametrizacao de queries
-- PostgreSQL:
PREPARE safe_query AS
SELECT * FROM users WHERE username = $1 AND password = $2;
EXECUTE safe_query USING username, password;

-- MySQL:
PREPARE safe_query FROM
'SELECT * FROM users WHERE username = ? AND password = ?';
SET @u = username;
SET @p = password;
EXECUTE safe_query USING @u, @p;

-- CORRETO: Stored procedures
CREATE PROCEDURE authenticate_user(p_username TEXT, p_password TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT * FROM users 
    WHERE username = p_username 
    AND password = crypt(p_password, password);
END;
$$;
```

### Anti-Pattern 2: Senhas em Texto Plano

```sql
-- ANTI-PATTERN: Armazenar senhas sem hash ou com hash fraco

-- ERRADO: Senha em texto plano
CREATE TABLE users_bad (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(100)  -- Senha em texto plano!
);

-- ERRADO: Hash MD5 (quebravel em segundos)
INSERT INTO users_bad (username, password) 
VALUES ('admin', md5('minha_senha'));

-- ERRADO: SHA-1 sem salt (vulneravel a rainbow tables)
INSERT INTO users_bad (username, password) 
VALUES ('admin', encode(sha1('minha_senha'::bytea), 'hex'));

-- CORRETO: bcrypt com salt
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users_good (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    last_password_change TIMESTAMPTZ DEFAULT NOW(),
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ
);

-- Inserir com bcrypt
INSERT INTO users_good (username, password_hash)
VALUES ('admin', crypt('minha_senha_forte', gen_salt('bf', 12)));

-- Verificar senha
SELECT * FROM users_good 
WHERE username = 'admin' 
AND password_hash = crypt('minha_senha_forte', password_hash);

-- CORRETO: Argon2 (mais resistente a GPU attacks)
-- Requer extensao argon2

-- CORRETO: PBKDF2
INSERT INTO users_good (username, password_hash)
VALUES ('user1', encode(
    pbkdf2_hmac('sha256', 'senha'::bytea, 'salt'::bytea, 100000),
    'hex'
));
```

### Anti-Pattern 3: Credenciais Hardcoded

```sql
-- ANTI-PATTERN: Credenciais em codigo-fonte ou scripts

-- ERRADO:
-- #!/bin/bash
-- psql -h db.server.com -U admin -d production -c "SELECT * FROM users"
-- Senha esta em algum lugar do codigo ou variavel de ambiente

-- ERRADO em Python:
-- conn = psycopg2.connect(
--     host="db.server.com",
--     database="production",
--     user="admin",
--     password="SuperSecret123!"  -- Hardcoded!
-- )

-- CORRETO: Vault de seguranca
-- Usar HashiCorp Vault, AWS Secrets Manager, Azure Key Vault

-- CORRETO: Variaveis de ambiente (melhor que hardcoded, mas nao ideal)
-- export DB_PASSWORD="SuperSecret123!"
-- conn = psycopg2.connect(
--     host=os.environ['DB_HOST'],
--     database=os.environ['DB_NAME'],
--     user=os.environ['DB_USER'],
--     password=os.environ['DB_PASSWORD']
-- )

-- CORRETO: Database de credenciais com criptografia
CREATE TABLE secure_credentials (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(255) NOT NULL,
    credential_type VARCHAR(50),
    encrypted_value BYTEA NOT NULL,
    key_version INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated TIMESTAMPTZ,
    rotation_policy VARCHAR(50) DEFAULT '90_days'
);
```

### Anti-Pattern 4: Acesso Root/Admin para Aplicacoes

```sql
-- ANTI-PATTERN: Aplicacoes usando usuario root ou admin

-- ERRADO: Conexao como postgres/root
-- psql -h db.server.com -U postgres -d production

-- ERRADO: Todos os acessos usando mesma credencial
-- Todo o sistema usa o usuario 'app_user' com todas as permissoes

-- CORRETO: Least privilege por funcao
-- Cada modulo da aplicacao tem seu proprio usuario com permissoes minimas

-- Usuario para leitura (analytics, dashboards)
CREATE ROLE analytics_reader LOGIN PASSWORD 'strong_password_1';
GRANT CONNECT ON DATABASE production TO analytics_reader;
GRANT USAGE ON SCHEMA analytics TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_reader;

-- Usuario para escrita (aplicacao web)
CREATE ROLE app_web_writer LOGIN PASSWORD 'strong_password_2';
GRANT CONNECT ON DATABASE production TO app_web_writer;
GRANT USAGE ON SCHEMA public TO app_web_writer;
GRANT INSERT, UPDATE ON orders, order_items, payments TO app_web_writer;
GRANT SELECT ON customers, products TO app_web_writer;
GRANT USAGE ON SEQUENCE orders_id_seq, order_items_id_seq TO app_web_writer;

-- Usuario para manutencao (DBA)
CREATE ROLE dba_maintenance LOGIN PASSWORD 'strong_password_3';
GRANT CONNECT ON DATABASE production TO dba_maintenance;
GRANT ALL PRIVILEGES ON DATABASE production TO dba_maintenance;
-- Restringir por IP via pg_hba.conf

-- Usuario para backup
CREATE ROLE backup_reader LOGIN PASSWORD 'strong_password_4';
GRANT CONNECT ON DATABASE production TO backup_reader;
GRANT USAGE ON SCHEMA public TO backup_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_reader;
```

### Anti-Pattern 5: Auditing Inexistente

```sql
-- ANTI-PATTERN: Nao ter logs de auditoria

-- ERRADO: Nenhum registro de quem acessou dados
-- Nao ha como rastrear quem visualizou ou modificou dados sensiveis

-- CORRETO: Audit trail completo
CREATE TABLE audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(20),
    user_name VARCHAR(128),
    client_ip INET,
    table_name VARCHAR(256),
    record_id TEXT,
    old_values JSONB,
    new_values JSONB,
    query_text TEXT
);

-- Funcao de auditoria generica
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        event_type, user_name, client_ip, table_name,
        record_id, old_values, new_values
    )
    VALUES (
        TG_OP,
        current_user,
        inet_client_addr(),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        CASE WHEN TG_OP != 'DELETE' THEN NEW.id::TEXT ELSE OLD.id::TEXT END,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Aplicar em tabelas sensiveis
CREATE TRIGGER audit_customers
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();
```

### Anti-Pattern 6: Sem Criptografia at-Rest

```sql
-- ANTI-PATTERN: Dados sensiveis sem criptografia

-- ERRADO: Dados de cartao, CPF, SSN em texto plano
CREATE TABLE payment_info_bad (
    card_number VARCHAR(19),  -- Em texto plano!
    cvv VARCHAR(4),           -- Em texto plano!
    cpf VARCHAR(14)           -- Em texto plano!
);

-- CORRETO: Criptografia de colunas sensiveis
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE payment_info_good (
    id SERIAL PRIMARY KEY,
    card_number_encrypted BYTEA NOT NULL,
    card_number_last_four CHAR(4) NOT NULL,
    cvv_encrypted BYTEA NOT NULL,
    cpf_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Funcao para inserir dados criptografados
CREATE OR REPLACE FUNCTION store_payment_data(
    p_card_number VARCHAR,
    p_cvv VARCHAR,
    p_cpf VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_id INT;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    INSERT INTO payment_info_good (
        card_number_encrypted,
        card_number_last_four,
        cvv_encrypted,
        cpf_encrypted
    )
    VALUES (
        pgp_sym_encrypt(p_card_number, v_master_key),
        RIGHT(p_card_number, 4),
        pgp_sym_encrypt(p_cvv, v_master_key),
        pgp_sym_encrypt(p_cpf, v_master_key)
    )
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
```

### Anti-Pattern 7: Sem Index para Queries Frequentes

```sql
-- ANTI-PATTERN: Tabelas grandes sem indices adequados

-- ERRADO: Query lenta em tabela de milhoes de registros
SELECT * FROM orders WHERE customer_id = 12345;
-- Seq Scan on orders: tempo = 45 segundos

-- CORRETO: Criar indice na coluna frequentemente consultada
CREATE INDEX idx_orders_customer_id ON orders (customer_id);

-- CORRETO: Indice parcial para queries frequentes
CREATE INDEX idx_orders_pending ON orders (created_at) 
WHERE status = 'PENDING';

-- CORRETO: Indice cobertor (covering index)
CREATE INDEX idx_orders_customer_date ON orders (customer_id, created_at DESC);
-- Este indice cobre tanto o filtro quanto a ordenacao

-- CORRETO: Indice para queries deRange
CREATE INDEX idx_orders_date_range ON orders (created_at);
CREATE INDEX idx_logs_timestamp ON system_logs (event_time);

-- Verificar indices nao utilizados
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- Verificar queries lentas
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

### Anti-Pattern 8: NUNCA VACUUM/ANALYZE

```sql
-- ANTI-PATTERN: Nunca executar VACUUM ou ANALYZE

-- ERRADO: Tabela nunca recebe vacuum
-- Resultado: tabela cresce infinitamente, queries ficam lentas

-- CORRETO: Configurar autovacuum corretamente
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;  -- 10% das linhas
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05; -- 5% das linhas
ALTER SYSTEM SET autovacuum_vacuum_cost_delay = 2;      -- Mais agressivo

-- CORRETO: VACUUM manual para tabelas criticas
VACUUM (VERBOSE, ANALYZE) orders;
VACUUM (VERBOSE, ANALYZE) customers;

-- Verificar necessidade de vacuum
SELECT 
    schemaname,
    relname AS table_name,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::DECIMAL / NULLIF(n_live_tup, 0) * 100, 2) AS dead_pct,
    last_vacuum,
    last_autovacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

### Anti-Pattern 9: Sem Backup ou Backup nao Testado

```sql
-- ANTI-PATTERN: Backup que nunca foi testado

-- ERRADO: Backup configurado mas nunca restaurado
-- "Temos backup" != "Backup funciona"

-- CORRETO: Backup regular com testes de restauracao

-- Script de backup automatizado
#!/bin/bash
# backup.sh - Backup diario com verificacao

BACKUP_DIR="/backups/$(date +%Y%m%d)"
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).dump"

# Verificar integridade
pg_restore --list "$BACKUP_DIR/backup_*.dump" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Backup OK"
else
    echo "BACKUP CORRUPTED" | mail -s "Backup Alert" admin@company.com
fi

-- CORRETO: Teste periodico de restauracao
-- pg_restore -h test-server -U admin -d test_restore backup.dump

-- Verificar status de backups
SELECT 
    backup_date,
    backup_size_mb,
    restoration_tested,
    last_test_date,
    CASE 
        WHEN NOT restoration_tested THEN 'CRITICAL: Never tested'
        WHEN last_test_date < CURRENT_DATE - INTERVAL '30 days' THEN 'WARNING: Not tested recently'
        ELSE 'OK'
    END AS status
FROM backup_history
ORDER BY backup_date DESC
LIMIT 30;
```

### Anti-Pattern 10: Sem Row-Level Security

```sql
-- ANTI-PATTERN: Todos os usuarios veem todos os dados

-- ERRADO: Query retorna todos os registros
SELECT * FROM orders;
-- O usuario de department A ve pedidos de department B

-- CORRETO: Row-Level Security (RLS)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: cada usuario ve apenas seus pedidos
CREATE POLICY orders_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Policy: admin ve tudo
CREATE POLICY orders_admin_access ON orders
    TO admin_role
    USING (TRUE);

-- Configurar tenant na sessao
SET app.current_tenant = 'tenant-uuid-aqui';

-- Agora a query filtra automaticamente
SELECT * FROM orders;  -- Retorna apenas pedidos do tenant atual
```

### Anti-Pattern 11: Transactions Longas Demais

```sql
-- ANTI-PATTERN: Transacoes que duram horas

-- ERRADO:
BEGIN;
-- ... centenas de operacoes ...
-- ... operacao demorada ...
-- ... mais operacoes ...
COMMIT;  -- 4 horas depois!

-- Problemas:
-- 1. Locks mantidos por muito tempo
-- 2. MVCC acumula dead tuples
-- 3. Outros usuarios bloqueados
-- 4. Risco de perda de dados em caso de crash

-- CORRETO: Transacoes curtas
BEGIN;
INSERT INTO orders (customer_id, total) VALUES (123, 99.99);
INSERT INTO order_items (order_id, product_id, quantity) VALUES (currval('orders_id_seq'), 1, 2);
COMMIT;

-- CORRETO: Usar savepoints para operacoes longas
BEGIN;
-- Fase 1: Validacao
SAVEPOINT sp1;
-- ... validacoes ...
SAVEPOINT sp2;
-- ... processamento ...
SAVEPOINT sp3;
-- ... escrita ...
COMMIT;
```

### Anti-Pattern 12: SELECT * em Producao

```sql
-- ANTI-PATTERN: SELECT * em queries de producao

-- ERRADO: Retorna todas as colunas, incluindo dados sensiveis
SELECT * FROM customers WHERE id = 123;
-- Retorna: id, name, email, cpf, phone, address, credit_card, ssn...

-- CORRETO: Selecionar apenas colunas necessarias
SELECT id, name, email FROM customers WHERE id = 123;
-- Apenas dados nao sensiveis

-- CORRETO: Views com mascaramento
CREATE VIEW customer_safe AS
SELECT 
    id,
    name,
    email,
    '***.***.***-' || RIGHT(cpf, 2) AS cpf_masked,
    '(**) *****-' || RIGHT(phone, 4) AS phone_masked
FROM customers;

-- CORRETO: Column-level permissions
REVOKE ALL ON customers FROM app_user;
GRANT SELECT (id, name, email) ON customers TO app_user;
-- app_user so pode acessar essas 3 colunas
```

### Anti-Pattern 13: Sem Conexao Pool

```sql
-- ANTI-PATTERN: Criar nova conexao para cada request

-- ERRADO:
-- for each request:
--     conn = connect_to_database()
--     execute_query(conn, ...)
--     close_connection(conn)
-- Cada conexao consome ~10MB de RAM

-- CORRETO: Usar connection pool
-- Configuracao PgBouncer:
-- [databases]
-- production = host=db.server.com port=5432 dbname=production
-- 
-- [pgbouncer]
-- pool_mode = transaction
-- max_client_conn = 1000
-- default_pool_size = 50
-- reserve_pool_size = 10
-- reserve_pool_timeout = 3

-- Verificar uso de conexoes
SELECT 
    datname,
    numbackends,
    numbackends AS active_connections,
    (SELECT setting::INT FROM pg_settings WHERE name = 'max_connections') AS max_connections,
    ROUND(numbackends::DECIMAL / 
          (SELECT setting::INT FROM pg_settings WHERE name = 'max_connections') * 100, 1) AS usage_pct
FROM pg_stat_database
WHERE datname = current_database();
```

### Anti-Pattern 14: Ignorar Erros

```sql
-- ANTI-PATTERN: Ignorar erros de banco de dados

-- ERRADO: Try/catch que engole erros
-- BEGIN TRY
--     INSERT INTO orders (...) VALUES (...)
-- END TRY
-- BEGIN CATCH
--     -- Ignorar erro
-- END CATCH

-- CORRETO: Tratar erros adequadamente
CREATE OR REPLACE FUNCTION safe_insert_order(
    p_customer_id INT,
    p_total DECIMAL
)
RETURNS INT AS $$
DECLARE
    v_order_id INT;
BEGIN
    INSERT INTO orders (customer_id, total, status)
    VALUES (p_customer_id, p_total, 'PENDING')
    RETURNING id INTO v_order_id;
    
    RETURN v_order_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'Customer % does not exist', p_customer_id;
    WHEN check_violation THEN
        RAISE EXCEPTION 'Invalid order data: total must be positive';
    WHEN OTHERS THEN
        -- Log do erro antes de re-raise
        INSERT INTO error_log (error_time, error_message, query_context)
        VALUES (NOW(), SQLERRM, 'safe_insert_order');
        RAISE;
END;
$$ LANGUAGE plpgsql;
```

### Anti-Pattern 15: Dados Duplicados

```sql
-- ANTI-PATTERN: Tabelas com dados massivamente duplicados

-- ERRADO: Tabela de pedidos com nome do cliente repetido em cada linha
CREATE TABLE orders_bad (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255),  -- Duplicado em cada pedido!
    customer_email VARCHAR(255), -- Duplicado!
    customer_phone VARCHAR(20),  -- Duplicado!
    product_name VARCHAR(255),   -- Duplicado!
    total DECIMAL
);

-- CORRETO: Normalizacao
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    total DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL
);
```

### Anti-Pattern 16: Sem Validacao no Banco

```sql
-- ANTI-PATTERN: Dados invalidos inseridos no banco

-- ERRADO: Sem constraints de validacao
CREATE TABLE users_no_validation (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),  -- Pode ser qualquer coisa
    age INT,             -- Pode ser negativo
    status VARCHAR(20)   -- Pode ter qualquer valor
);

-- CORRETO: Constraints de validacao
CREATE TABLE users_with_validation (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    age INT CHECK (age >= 0 AND age <= 150),
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users_with_validation
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
```

### Anti-Pattern 17: Soft Delete Inconsistente

```sql
-- ANTI-PATTERN: Soft delete sem padrao consistente

-- ERRADO: Coluna deleted_at em algumas tabelas, NULL em outras
-- Dados "deletados" ainda aparecem em queries
-- Nao ha consistencia entre tabelas

-- CORRETO: Soft delete padronizado
CREATE TABLE soft_delete_config (
    table_name VARCHAR(255) PRIMARY KEY,
    deleted_column VARCHAR(100) DEFAULT 'deleted_at',
    cascade_rules TEXT,
    retention_days INT DEFAULT 90
);

-- Funcao de soft delete padronizada
CREATE OR REPLACE FUNCTION soft_delete(
    p_table_name VARCHAR,
    p_record_id INT
)
RETURNS BOOLEAN AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I SET deleted_at = NOW() WHERE id = %L',
        p_table_name, p_record_id
    );
    RETURN TRUE;
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Funcao para excluir dados expirados
CREATE OR REPLACE FUNCTION cleanup_expired_soft_deletes()
RETURNS INT AS $$
DECLARE
    v_config RECORD;
    v_deleted INT := 0;
    v_total INT := 0;
BEGIN
    FOR v_config IN SELECT * FROM soft_delete_config
    LOOP
        EXECUTE format(
            'DELETE FROM %I WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL ''%s days''',
            v_config.table_name,
            v_config.retention_days
        );
        GET DIAGNOSTICS v_deleted = ROW_COUNT;
        v_total := v_total + v_deleted;
    END LOOP;
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;
```

### Anti-Pattern 18: Nao Usar Prepared Statements

```sql
-- ANTI-PATTERN: Queries construidas dinamicamente sem prepared statements

-- ERRADO:
query = f"SELECT * FROM users WHERE id = {user_id}"  -- F-string!

-- ERRADO:
query = "SELECT * FROM users WHERE id = " + str(user_id)

-- CORRETO: Prepared statements (prevenir SQL injection)
-- PostgreSQL
PREPARE get_user AS SELECT * FROM users WHERE id = $1;
EXECUTE get_user USING user_id;

-- MySQL
PREPARE get_user FROM 'SELECT * FROM users WHERE id = ?';
SET @uid = user_id;
EXECUTE get_user USING @uid;

-- CORRETO em aplicacao (Python):
-- cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
-- cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
```

### Anti-Pattern 19: Sem Monitoramento de Performance

```sql
-- ANTI-PATTERN: Nao monitorar performance do banco

-- ERRADO: Apenas verificar quando usuario reclama

-- CORRETO: Monitoramento proativo
-- 1. Queries lentas
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE mean_time > 1000  -- Mais de 1 segundo
ORDER BY mean_time DESC
LIMIT 20;

-- 2. Tabelas com muitos dead tuples
SELECT 
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::DECIMAL / NULLIF(n_live_tup, 0) * 100, 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 100000
ORDER BY n_dead_tup DESC;

-- 3. Indices nao utilizados
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND pg_relation_size(indexrelid) > 1048576  -- > 1MB
ORDER BY pg_relation_size(indexrelid) DESC;

-- 4. Conexoes ativas
SELECT 
    usename,
    client_addr,
    state,
    query,
    NOW() - query_start AS duration
FROM pg_stat_activity
WHERE state = 'active'
AND query_start < NOW() - INTERVAL '5 minutes'
ORDER BY duration DESC;
```

### Anti-Pattern 20: Sem Planos de Recuperacao

```sql
-- ANTI-PATTERN: Nao ter plano de recuperacao de desastres

-- ERRADO: "Se der problema, a gente resolve na hora"

-- CORRETO: Documentar e testar plano de recuperacao

CREATE TABLE disaster_recovery_plan (
    plan_id SERIAL PRIMARY KEY,
    scenario VARCHAR(255),
    rto_hours INT,  -- Recovery Time Objective
    rpo_minutes INT, -- Recovery Point Objective
    steps TEXT[],
    responsible VARCHAR(255),
    last_tested DATE,
    test_results TEXT,
    next_test_date DATE
);

INSERT INTO disaster_recovery_plan VALUES
(1, 'Database corruption', 4, 60,
 ARRAY['1. Identify scope of corruption',
        '2. Stop application writes',
        '3. Restore from latest backup',
        '4. Apply WAL logs from backup point',
        '5. Verify data integrity',
        '6. Resume application'],
 'DBA Team', CURRENT_DATE - 90, 'Successful - restored in 2h 15min', CURRENT_DATE + 90),
(2, 'Ransomware attack', 8, 15,
 ARRAY['1. Isolate affected systems',
        '2. Identify attack vector',
        '3. Restore from offline backup',
        '4. Rotate all credentials',
        '5. Verify backup integrity',
        '6. Resume with enhanced monitoring'],
 'Security Team', CURRENT_DATE - 180, 'Successful - restored in 5h 30min', CURRENT_DATE + 180),
(3, 'Hardware failure', 2, 5,
 ARRAY['1. Failover to standby',
        '2. Verify data consistency',
        '3. Update DNS/load balancer',
        '4. Monitor new primary',
        '5. Replace failed hardware'],
 'DBA Team', CURRENT_DATE - 30, 'Successful - failover in 45min', CURRENT_DATE + 60);

-- Verificar status de testes
SELECT 
    scenario,
    rto_hours,
    rpo_minutes,
    last_tested,
    EXTRACT(DAY FROM CURRENT_DATE - last_tested) AS days_since_test,
    next_test_date,
    CASE 
        WHEN last_tested < CURRENT_DATE - INTERVAL '180 days' THEN 'CRITICAL: Not tested in 6+ months'
        WHEN last_tested < CURRENT_DATE - INTERVAL '90 days' THEN 'WARNING: Not tested in 3+ months'
        ELSE 'OK'
    END AS status
FROM disaster_recovery_plan
ORDER BY rto_hours;
```

## Security Checklist (50+ Itens)

### Controle de Acesso

```markdown
## Security Checklist

### 1. Controle de Acesso
- [ ] 1.1 Least privilege implementado para todos os usuarios
- [ ] 1.2 MFA habilitado para acessos administrativos
- [ ] 1.3 Senhas fortes (12+ caracteres) exigidas
- [ ] 1.4 Rotacao de senhas a cada 90 dias
- [ ] 1.5 Contas inativas bloqueadas apos 30 dias
- [ ] 1.6 Revisao de acessos trimestral
- [ ] 1.7 Separacao de duties implementada
- [ ] 1.8 Acesso remoto via VPN ou ZTNA
- [ ] 1.9 Certificados client-side para servicos
- [ ] 1.10 Sessoes expiram apos inatividade

### 2. Criptografia
- [ ] 2.1 Dados sensiveis criptografados at-rest
- [ ] 2.2 TLS 1.3 para todas as conexoes
- [ ] 2.3 Chaves gerenciadas em HSM
- [ ] 2.4 Rotacao de chaves programada
- [ ] 2.5 Algoritmos FIPS-compliant
- [ ] 2.6 Certificados SSL monitorados
- [ ] 2.7 Dados de cartao tokenizados
- [ ] 2.8 PII criptografado em colunas
- [ ] 2.9 Backups criptografados
- [ ] 2.10 Chaves nunca armazenadas com dados

### 3. Monitoramento
- [ ] 3.1 Audit trail completo
- [ ] 3.2 Logs preservados por 12+ meses
- [ ] 3.3 Alertas em tempo real
- [ ] 3.4 Deteccao de anomalias
- [ ] 3.5 Monitoramento 24/7
- [ ] 3.6 SIEM integrado
- [ ] 3.7 Logs imutaveis
- [ ] 3.8 Correlation de eventos
- [ ] 3.9 Dashboard de seguranca
- [ ] 3.10 Reportes periodicos

### 4. Rede
- [ ] 4.1 Firewall configurado
- [ ] 4.2 Network segmentation
- [ ] 4.3 IDS/IPS ativo
- [ ] 4.4 DDoS protection
- [ ] 4.5 DNS monitoring
- [ ] 4.6 TLS inspection
- [ ] 4.7 VPN para acessos remotos
- [ ] 4.8 Zero Trust Architecture
- [ ] 4.9 Microsegmentation
- [ ] 4.10 Network access control

### 5. Aplicacao
- [ ] 5.1 Parameterized queries
- [ ] 5.2 Input validation
- [ ] 5.3 Output encoding
- [ ] 5.4 WAF configurado
- [ ] 5.5 OWASP Top 10 mitigado
- [ ] 5.6 Dependencias atualizadas
- [ ] 5.7 Security headers
- [ ] 5.8 CORS configurado
- [ ] 5.9 CSP implementado
- [ ] 5.10 Rate limiting

### 6. Backup e Recuperacao
- [ ] 6.1 Backups diarios automatizados
- [ ] 6.2 Backups offsite
- [ ] 6.3 Backups criptografados
- [ ] 6.4 Testes de restauracao mensais
- [ ] 6.5 RTO/RPO documentados
- [ ] 6.6 Plano de DR testado
- [ ] 6.7 Retencao de backups definida
- [ ] 6.8 Backup monitoring
- [ ] 6.9 Recovery procedures documentadas
- [ ] 6.10 Point-in-time recovery testado

### 7. Compliance
- [ ] 7.1 Data classification implementada
- [ ] 7.2 Privacy policy publicada
- [ ] 7.3 Consent management
- [ ] 7.4 Data retention policies
- [ ] 7.5 Cross-border transfer rules
- [ ] 7.6 DPIA para alto risco
- [ ] 7.7 DPO nomeado
- [ ] 7.8 Incident response plan
- [ ] 7.9 Vendor assessment
- [ ] 7.10 Audit readiness
```

## Decision Tree: Qual SGBDR Escolher

### Criterios de Decisao

```sql
-- Decision tree para escolha de SGBDR

CREATE TABLE sgbdr_comparison (
    feature VARCHAR(100),
    postgresql_score INT,
    mysql_score INT,
    oracle_score INT,
    sql_server_score INT,
    notes TEXT
);

INSERT INTO sgbdr_comparison VALUES
('Open Source', 10, 10, 0, 0, 'PostgreSQL e MySQL sao open source'),
('JSON Support', 10, 7, 8, 7, 'PostgreSQL tem melhor suporte a JSONB'),
('Full ACID', 10, 8, 10, 10, 'MySQL InnoDB e ACID, mas com limitacoes'),
('Replication', 9, 8, 10, 10, 'Todos suportam, Oracle e SQL Server mais maduros'),
('Partitioning', 9, 8, 10, 9, 'Oracle e mais maduro em partitioning'),
('Stored Procedures', 9, 6, 10, 10, 'PL/pgSQL e mais poderoso que MySQL'),
('Performance', 9, 9, 10, 9, 'Oracle otimizado para cargas especificas'),
('Cost', 10, 10, 0, 5, 'Oracle e muito caro'),
('Community', 10, 9, 4, 5, 'PostgreSQL e MySQL tem comunidades ativas'),
('Extensions', 10, 7, 8, 7, 'PostgreSQL tem ecossistema de extensoes rico'),
('Security Features', 10, 7, 10, 9, 'RLS, pgaudit no PostgreSQL');

-- Recomendacao por caso de uso
CREATE TABLE sgbdr_recommendations (
    use_case VARCHAR(100),
    recommended VARCHAR(50),
    alternative VARCHAR(50),
    justification TEXT
);

INSERT INTO sgbdr_recommendations VALUES
('Startup / MVP', 'PostgreSQL', 'MySQL',
 'Mais features, melhor JSON, custo zero'),
('Enterprise / Large Scale', 'PostgreSQL', 'Oracle',
 'Escalabilidade, features avancadas, custo'),
('Data Analytics', 'PostgreSQL', 'MySQL',
 'Window functions, CTEs, JSONB, extensoes'),
('High Availability', 'PostgreSQL', 'SQL Server',
 'Replicacao nativa, failover automático'),
('Legacy Migration', 'PostgreSQL', 'MySQL',
 'Compatibilidade com Oracle, features similares'),
('Cloud-Native', 'PostgreSQL', 'MySQL',
 'AWS RDS, Google Cloud SQL, Azure'),
('Embedded', 'SQLite', 'MySQL',
 'Leve, sem servidor, embutido na aplicacao');
```

## Template: Schema Seguro Padrao

```sql
-- Template de schema seguro para novos projetos

-- 1. Configuracoes de seguranca
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Schema organizado
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS analytics;

-- 3. Tabela de usuarios segura
CREATE TABLE core.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret BYTEA,
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Tabela de audit log
CREATE TABLE audit.activity_log (
    log_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50),
    user_id UUID,
    client_ip INET,
    table_name VARCHAR(256),
    record_id UUID,
    old_values JSONB,
    new_values JSONB,
    session_id VARCHAR(128)
);

-- 5. Indices obrigatorios
CREATE INDEX idx_users_email ON core.users (email);
CREATE INDEX idx_users_username ON core.users (username);
CREATE INDEX idx_audit_time ON audit.activity_log (event_time);
CREATE INDEX idx_audit_user ON audit.activity_log (user_id);

-- 6. Functions de auditoria
CREATE OR REPLACE FUNCTION audit.log_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit.activity_log (
        event_type, user_id, client_ip, table_name,
        record_id, old_values, new_values
    )
    VALUES (
        TG_OP,
        current_setting('app.current_user_id', TRUE)::UUID,
        inet_client_addr(),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        CASE WHEN TG_OP != 'DELETE' THEN NEW.id ELSE OLD.id END,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 7. Row-Level Security
ALTER TABLE core.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_isolation ON core.users
    USING (id = current_setting('app.current_user_id', TRUE)::UUID);
```

## Template: Query Segura Padrao

```sql
-- Template de query segura para uso diario

-- 1. SELECT seguro (com filtros e paginacao)
CREATE OR REPLACE FUNCTION safe_select(
    p_table_name VARCHAR,
    p_conditions JSONB,
    p_page INT DEFAULT 1,
    p_page_size INT DEFAULT 50
)
RETURNS TABLE(result JSONB) AS $$
DECLARE
    v_query TEXT;
    v_offset INT;
BEGIN
    -- Validar nome da tabela (prevenir SQL injection)
    IF p_table_name !~ '^[a-z_][a-z0-9_]*$' THEN
        RAISE EXCEPTION 'Invalid table name: %', p_table_name;
    END IF;
    
    -- Limitar page_size
    p_page_size := LEAST(p_page_size, 100);
    v_offset := (p_page - 1) * p_page_size;
    
    -- Construir query segura
    v_query := format(
        'SELECT to_jsonb(t) FROM %I t WHERE true LIMIT %s OFFSET %s',
        p_table_name,
        p_page_size,
        v_offset
    );
    
    -- Aplicar condicoes (se fornecidas)
    -- NOTA: Em producao, usar prepared statements para condicoes
    
    FOR result IN EXECUTE v_query
    LOOP
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 2. INSERT seguro
CREATE OR REPLACE FUNCTION safe_insert(
    p_table_name VARCHAR,
    p_data JSONB
)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    IF p_table_name !~ '^[a-z_][a-z0-9_]*$' THEN
        RAISE EXCEPTION 'Invalid table name';
    END IF;
    
    EXECUTE format(
        'INSERT INTO %I SELECT * FROM jsonb_populate_record(NULL::%I, $1) RETURNING id',
        p_table_name,
        p_table_name
    ) USING p_data
    INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
```

## Template: Migration Segura

```sql
-- Template de migration segura

-- 1. Criar tabela com todas as protecoes
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- 2. Indices
CREATE INDEX idx_orders_customer ON orders (customer_id);
CREATE INDEX idx_orders_status ON orders (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_orders_created ON orders (created_at DESC);

-- 3. Auditoria
CREATE TRIGGER audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION audit.log_change();

-- 4. Row-Level Security
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY orders_tenant ON orders
    USING (customer_id = current_setting('app.current_tenant')::UUID);

-- 5. Permissoes
GRANT SELECT, INSERT, UPDATE ON orders TO app_role;
GRANT USAGE ON SEQUENCE orders_id_seq TO app_role;
```

## Template: Backup Strategy

```sql
-- Template de estrategia de backup

CREATE TABLE backup_config (
    backup_type VARCHAR(50) PRIMARY KEY,
    frequency VARCHAR(50),
    retention_days INT,
    encryption_enabled BOOLEAN DEFAULT TRUE,
    offsite_enabled BOOLEAN DEFAULT TRUE,
    compression_level INT DEFAULT 9,
    verification_enabled BOOLEAN DEFAULT TRUE
);

INSERT INTO backup_config VALUES
('FULL', 'DAILY', 90, TRUE, TRUE, 9, TRUE),
('INCREMENTAL', 'HOURLY', 30, TRUE, TRUE, 9, TRUE),
('WAL_ARCHIVING', 'REAL_TIME', 30, TRUE, TRUE, 0, FALSE),
('SCHEMA_ONLY', 'WEEKLY', 365, FALSE, FALSE, 9, TRUE);

-- Script de backup
CREATE OR REPLACE FUNCTION execute_backup(p_type VARCHAR)
RETURNS TEXT AS $$
DECLARE
    v_config RECORD;
    v_backup_path TEXT;
    v_start_time TIMESTAMPTZ;
BEGIN
    SELECT * INTO v_config FROM backup_config WHERE backup_type = p_type;
    
    v_backup_path := '/backups/' || p_type || '/' || 
                     to_char(NOW(), 'YYYY/MM/DD/HH24');
    
    v_start_time := CLOCK_TIMESTAMP();
    
    -- Log de inicio
    INSERT INTO backup_log (backup_type, started_at, status, path)
    VALUES (p_type, v_start_time, 'RUNNING', v_backup_path);
    
    -- Executar backup (simplificado)
    -- Em producao: pg_dump, pg_basebackup, etc.
    
    -- Log de conclusao
    UPDATE backup_log SET
        status = 'COMPLETED',
        completed_at = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - v_start_time))::INT
    WHERE started_at = v_start_time;
    
    RETURN FORMAT('Backup %s completed at %s', p_type, v_backup_path);
END;
$$ LANGUAGE plpgsql;
```

## Referencia Rapida: SQL Injection Prevention

```sql
-- Referencia rapida para prevenir SQL injection

/*
1. PARAMETRIZACAO
   - Nunca concatenar inputs do usuario em queries
   - Usar prepared statements ou ORM

2. VALIDACAO DE INPUT
   - Whitelist de caracteres permitidos
   - Tamanho maximo
   - Tipos de dados

3. STORED PROCEDURES
   - Logica de negocio no banco
   - Dados nunca saem do banco

4. WAF (Web Application Firewall)
   - OWASP ModSecurity CRS
   - Regras customizadas

5. PRINCIPIO DO MENOR PRIVILEGIO
   - Usuario da aplicacao so deve ter permissoes necessarias
   - NUNCA usar root/admin

6. AUDITORIA
   - Log de todas as queries
   - Deteccao de padroes suspeitos

EXEMPLOS DE PAYLOADS DE SQL INJECTION:
- ' OR '1'='1
- ' UNION SELECT * FROM users --
- '; DROP TABLE users;--
- ' AND 1=CONVERT(int,(SELECT TOP 1 table_name FROM information_schema.tables))--
- ' WAITFOR DELAY '0:0:5'-- (time-based blind)
*/

-- Funcao para detectar SQL injection em logs
CREATE OR REPLACE FUNCTION detect_sql_injection(p_query TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    IF p_query ~* "(;|'|""|\\|--|/\*)" THEN
        RETURN TRUE;
    END IF;
    IF p_query ~* "(union\s+select|exec\s+|execute\s+|sp_|xp_)" THEN
        RETURN TRUE;
    END IF;
    IF p_query ~* "(information_schema|sysobjects|syscolumns|pg_catalog)" THEN
        RETURN TRUE;
    END IF;
    IF p_query ~* "(\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b)" THEN
        RETURN TRUE;
    END IF;
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
```

## Referencia Rapida: Index Design

```sql
-- Referencia rapida para design de indices

/*
TIPOS DE INDICE:
1. B-tree (padrao) - Para =, <, >, <=, >=, BETWEEN
2. Hash - Para = apenas
3. GIN - Para full-text search, arrays, JSONB
4. GIST - Para geometric, full-text
5. BRIN - Para tabelas grandes com dados correlacionados

QUANDO CRIAR INDICE:
- Colunas em WHERE clause
- Colunas em JOIN conditions
- Colunas em ORDER BY
- Colunas com alta cardinalidade

QUANDO NAO CRIAR INDICE:
- Tabelas pequenas (< 10K linhas)
- Colunas com baixa cardinalidade (ex: genero)
- Tabelas com muitas escritas (overhead)
- Colunas que mudam frequentemente

INDICES PARCIAIS:
CREATE INDEX idx_users_active ON users (email)
WHERE is_active = TRUE;

INDICES COBERTORES:
CREATE INDEX idx_orders_covering ON orders (customer_id, created_at DESC, total);

VERIFICAR USO DE INDICES:
SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;

VERIFICAR TAMANHO:
SELECT pg_size_pretty(pg_relation_size('idx_nome'));
*/
```

## Referencia Rapida: Isolation Levels

```sql
-- Referencia rapida para niveis de isolamento

/*
LEVEL             | Dirty Read | Non-Repeatable Read | Phantom Read
------------------|------------|---------------------|-------------
READ UNCOMMITTED  | Sim        | Sim                 | Sim
READ COMMITTED    | Nao        | Sim                 | Sim
REPEATABLE READ   | Nao        | Nao                 | Sim
SERIALIZABLE      | Nao        | Nao                 | Nao

USANDO NO POSTGRESQL:
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;  -- padrao
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

VERIFICAR ISOLAMENTO ATUAL:
SHOW transaction_isolation;

PROBLEMAS POR LEVEL:
- Dirty Read: Ler dados nao confirmados
- Non-Repeatable Read: Mesma query retorna dados diferentes
- Phantom Read: Novas linhas aparecem entre queries

QUANDO USAR CADA LEVEL:
- READ COMMITTED: Maioria das aplicacoes (padrao)
- REPEATABLE READ: Relatorios que precisam de consistencia
- SERIALIZABLE: Transacoes financeiras criticas

MVCC no PostgreSQL:
- READ COMMITTED: Cada statement ve snapshot proprio
- REPEATABLE READ: Transacao inteira ve mesmo snapshot
- SERIALIZABLE: Detecta e previne anomalias
*/

-- Exemplo pratico
BEGIN;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT * FROM accounts WHERE id = 1;  -- Balance = 100
-- Outro usuario atualiza balance para 200
SELECT * FROM accounts WHERE id = 1;  -- Ainda mostra 100 (consistente)
COMMIT;
```

## Performance Checklist

```markdown
## Performance Checklist

### Database Configuration
- [ ] shared_buffers = 25% of RAM
- [ ] effective_cache_size = 75% of RAM
- [ ] work_mem = 256MB (ou mais para queries complexas)
- [ ] maintenance_work_mem = 1GB
- [ ] wal_buffers = 64MB
- [ ] max_connections adequado ao workload
- [ ] autovacuum configurado agressivamente

### Query Optimization
- [ ] EXPLAIN ANALYZE em queries lentas
- [ ] Indices em colunas de WHERE/JOIN/ORDER BY
- [ ] Evitar SELECT * em producao
- [ ] Usar LIMIT para paginacao
- [ ] Evitar N+1 queries (usar JOINs)
- [ ] Usar CTEs para queries complexas
- [ ] Evitar subqueries correlacionadas

### Schema Design
- [ ] Normalizacao ate 3NF
- [ ] Desnormalizacao consciente para performance
- [ ] Tipos de dados adequados
- [ ] Constraints para integridade
- [ ] Comentarios em tabelas e colunas
- [ ] Nomenclatura consistente

### Monitoring
- [ ] pg_stat_statements habilitado
- [ ] Dashboard de performance
- [ ] Alertas para queries lentas
- [ ] Monitoramento de locks
- [ ] Track de conexoes ativas
- [ ] Analise de indices nao utilizados
```

## Compliance Checklist

```markdown
## Compliance Checklist

### PCI DSS
- [ ] Dados de cartao criptografados at-rest
- [ ] TLS 1.3 para transmissao
- [ ] MFA para acessos administrativos
- [ ] Audit trail de 12 meses
- [ ] Vulnerability scanning mensal
- [ ] Penetration testing anual
- [ ] Network segmentation
- [ ] Access reviews trimestrais

### LGPD/GDPR
- [ ] Consentimento registrado
- [ ] Data minimization
- [ ] Data retention policies
- [ ] Subject rights implementation
- [ ] DPIA para alto risco
- [ ] DPO nomeado
- [ ] Cross-border transfer rules
- [ ] Breach notification process

### HIPAA
- [ ] PHI criptografado
- [ ] Minimum necessary rule
- [ ] Access audit trail
- [ ] BAA com fornecedores
- [ ] Risk assessment anual
- [ ] Training de funcionarios
- [ ] Incident response plan
- [ ] Business continuity

### SOC 2
- [ ] Trust Service Criteria mapeados
- [ ] Controls implementados
- [ ] Evidence coletada
- [ ] Monitoring continuo
- [ ] Independent audit
- [ ] Management assertion
- [ ] Corrective actions
- [ ] Annual review
```

## Resumo

Este capitulo consolidou as principais praticas, anti-patterns e templates para databases seguros. Os 20 anti-patterns cobrem os erros mais comuns em desenvolvimento e administracao de databases. A security checklist com 50+ itens serve como referencia completa para verificacao de conformidade. Os templates de schema, query, migration e backup fornecem um ponto de partida seguro para novos projetos. As referencias rapidas de SQL injection prevention, index design e isolation levels servem como consulta no dia-a-dia.

Os principais pontos a lembrar:

**Seguranca comeca no design.** Um schema bem projetado, com constraints, criptografia e audit trail desde o inicio, e muito mais facil de proteger do que um schema legado sem esses controles.

**Least privilege e nao negociavel.** Cada usuario, aplicacao e servico deve ter apenas as permissoes estritamente necessarias. Isso inclui o usuario do banco de dados da aplicacao.

**Monitoramento e deteccao.** Sem monitoramento, e impossivel saber se seus dados estao seguros. Audit trails, alertas e dashboards sao investimentos obrigatorios, nao opcionais.

**Testes regulares.** Backup testado e backup que funciona. Incident response testado e response que funciona. Penetration test identifica vulnerabilidades antes dos atacantes.

**Compliance e continuo.** Regulamentacoes evoluem, novos requisitos sao adicionados. Automacao de compliance e a chave para manter conformidade ao longo do tempo.

## Anti-Pattern 21: Uso Excessivo de Triggers

```sql
-- ANTI-PATTERN: Cascata de triggers que causam lentidao

-- ERRADO: Multiplos triggers encadeados
CREATE TRIGGER trigger_1 AFTER INSERT ON orders
    FOR EACH ROW EXECUTE FUNCTION update_inventory();
-- update_inventory() atualiza estoque e dispara:
CREATE TRIGGER trigger_2 AFTER UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION check_low_stock();
-- check_low_stock() envia notificacao e dispara:
CREATE TRIGGER trigger_3 AFTER INSERT ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_notification_log();

-- Problema: Cada INSERT em orders dispara 3 triggers
-- Resultado: lentidao significativa em cargas altas

-- CORRETO: Consolidar logica em um unico trigger
CREATE OR REPLACE FUNCTION handle_order_insert()
RETURNS TRIGGER AS $$
BEGIN
    -- Atualizar estoque
    UPDATE inventory 
    SET quantity = quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
    
    -- Verificar estoque baixo e notificar
    IF (SELECT quantity FROM inventory WHERE product_id = NEW.product_id) < 10 THEN
        INSERT INTO notifications (type, message, priority)
        VALUES ('LOW_STOCK', 'Estoque baixo para produto ' || NEW.product_id, 'HIGH');
    END IF;
    
    -- Log de notificacao
    INSERT INTO notification_log (notification_time, processed)
    VALUES (NOW(), TRUE);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- CORRETO: Usar WHEN clause para filtrar executacao
CREATE TRIGGER trigger_orders_insert
    AFTER INSERT ON orders
    FOR EACH ROW
    WHEN (NEW.status = 'CONFIRMED')  -- So executa quando status = CONFIRMED
    EXECUTE FUNCTION handle_order_insert();

-- CORRETO: Usar deferred triggers para operacoes em batch
CREATE CONSTRAINT TRIGGER trigger_deferred_inventory
    AFTER INSERT ON orders
    FOR EACH ROW
    DEFERRABLE INITIALLY DEFERRED
    EXECUTE FUNCTION update_inventory_deferred();
```

## Anti-Pattern 22: Nao Usar Connection Pooling Adequadamente

```sql
-- ANTI-PATTERN: Configuracao inadequada de connection pool

-- ERRADO: Pool muito pequeno para o workload
-- PgBouncer com default_pool_size = 5
-- Resultado: Fila de conexoes, timeouts

-- ERRADO: Pool muito grande
-- PgBouncer com default_pool_size = 500
-- Resultado: Uso excessivo de memoria, overhead

-- CORRETO: Configuracao calibrada
-- [databases]
-- production = host=db.server.com port=5432 dbname=production
-- 
-- [pgbouncer]
-- pool_mode = transaction  -- Melhor para web apps
-- max_client_conn = 1000   -- Maximo de clientes conectados
-- default_pool_size = 25   -- Conexoes por usuario/database
-- reserve_pool_size = 5    -- Pool reserva para picos
-- reserve_pool_timeout = 3 -- Segundos antes de usar reserva
-- server_idle_timeout = 300 -- Fechar conexoes idle apos 5min
-- client_idle_timeout = 0   -- Sem timeout para clientes

-- Monitorar uso do pool
SELECT 
    database,
    user_name,
    cl_active,
    cl_waiting,
    sv_active,
    sv_idle,
    sv_used,
    sv_tested,
    sv_login
FROM pgbouncer_pools
ORDER BY cl_waiting DESC;

-- Metricas de performance do pool
SELECT 
    total_xact_count,
    total_query_count,
    total_received,
    total_sent,
    avg_xact_time,
    avg_query_time
FROM pgbouncer_stats;
```

## Anti-Pattern 23: Ignorar Deadlocks

```sql
-- ANTI-PATTERN: Nao monitorar ou resolver deadlocks

-- ERRADO: Apenas deixar o deadlock acontecer e retry
-- Deadlocks causam perda de tempo e recursos

-- CORRETO: Monitorar deadlocks ativamente
CREATE TABLE deadlock_log (
    deadlock_id SERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    locked_relation VARCHAR(256),
    locked_page INT,
    locked_tuple INT,
    locked_mode TEXT,
    blocking_pid INT,
    blocked_pid INT,
    blocking_query TEXT,
    blocked_query TEXT,
    resolution VARCHAR(50)
);

-- Trigger para registrar deadlocks (configurar via log_lock_waits)
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET deadlock_timeout = '1s';

-- Funcao para resolver deadlocks automaticamente
CREATE OR REPLACE FUNCTION auto_resolve_deadlock()
RETURNS TRIGGER AS $$
BEGIN
    -- Matar a sessao que esta bloqueando ha mais tempo
    PERFORM pg_terminate_backend(NEW.blocking_pid);
    
    -- Log da resolucao
    UPDATE deadlock_log SET
        resolution = 'BLOCKING_SESSION_TERMINATED'
    WHERE deadlock_id = NEW.deadlock_id;
    
    -- Alertar
    PERFORM pg_notify('deadlock_alert',
        FORMAT('Deadlock resolved: blocked %s, blocking %s',
               NEW.blocked_pid, NEW.blocking_pid));
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Estrategias para evitar deadlocks:
-- 1. Acessar tabelas na mesma ordem sempre
-- 2. Usar transacoes curtas
-- 3. Evitar locks manuais quando possivel
-- 4. Usar NOWAIT ou SKIP LOCKED para queries nao-bloqueantes
-- 5. Criar indices para reduzir tempo de holding de locks
```

## Anti-Pattern 24: Nao Usar Particionamento

```sql
-- ANTI-PATTERN: Tabelas gigantes sem particionamento

-- ERRADO: Tabela de logs com 1 bilhao de registros
CREATE TABLE system_logs_bad (
    id BIGSERIAL PRIMARY KEY,
    log_time TIMESTAMPTZ,
    message TEXT,
    level VARCHAR(10)
);
-- Query por data leva MINUTOS

-- CORRETO: Particionamento por data
CREATE TABLE system_logs (
    id BIGSERIAL,
    log_time TIMESTAMPTZ NOT NULL,
    message TEXT,
    level VARCHAR(10),
    PRIMARY KEY (id, log_time)
) PARTITION BY RANGE (log_time);

-- Criar particoes mensais
CREATE TABLE system_logs_2024_01 PARTITION OF system_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE system_logs_2024_02 PARTITION OF system_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... mais particoes

-- Query por data agora e rapida (Partition Pruning)
SELECT * FROM system_logs 
WHERE log_time BETWEEN '2024-01-15' AND '2024-01-16';
-- Apenas acessa particao de janeiro 2024

-- Automacao de criacao de particoes
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    v_next_month DATE;
    v_partition_name TEXT;
BEGIN
    v_next_month := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    v_partition_name := 'system_logs_' || TO_CHAR(v_next_month, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF system_logs
         FOR VALUES FROM (%L) TO (%L)',
        v_partition_name,
        v_next_month,
        v_next_month + INTERVAL '1 month'
    );
END;
$$ LANGUAGE plpgsql;
```

## Anti-Pattern 25: Dados Sensiveis em Logs

```sql
-- ANTI-PATTERN: Logar dados sensiveis em texto plano

-- ERRADO: Logar senhas, tokens, dados de cartao
INSERT INTO application_logs (message)
VALUES (format('User login: %s, password: %s', username, password));

INSERT INTO application_logs (message)
VALUES (format('Payment processed: card %s', card_number));

-- CORRETO: Mascarar dados sensiveis em logs
CREATE OR REPLACE FUNCTION sanitize_log_message(p_message TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Mascarar emails
    p_message := regexp_replace(p_message, 
        '([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        '\1***@\2', 'g');
    
    -- Mascarar CPFs
    p_message := regexp_replace(p_message,
        '(\d{3})\.(\d{3})\.(\d{3})-(\d{2})',
        '***.***.***-\4', 'g');
    
    -- Mascarar cartoes de credito
    p_message := regexp_replace(p_message,
        '(\d{4})-(\d{4})-(\d{4})-(\d{4})',
        '\1-****-****-\4', 'g');
    
    -- Mascarar tokens
    p_message := regexp_replace(p_message,
        '(token["\s:=]+)([a-zA-Z0-9]{20,})',
        '\1' || REPEAT('*', 20), 'gi');
    
    RETURN p_message;
END;
$$ LANGUAGE plpgsql;

-- Trigger para sanitizar logs
CREATE OR REPLACE FUNCTION sanitize_log_insert()
RETURNS TRIGGER AS $$
BEGIN
    NEW.message := sanitize_log_message(NEW.message);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sanitize_logs
    BEFORE INSERT ON application_logs
    FOR EACH ROW
    EXECUTE FUNCTION sanitize_log_insert();
```

## Anti-Pattern 26: Nao Versionar Migrations

```sql
-- ANTI-PATTERN: Alteracoes de schema sem versionamento

-- ERRADO: Executar ALTER TABLE direto em producao
-- ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN;
-- ALTER TABLE users ADD COLUMN last_login TIMESTAMPTZ;
-- Sem registro de quando, quem e por que

-- CORRETO: Sistema de migrations versionado

CREATE TABLE schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    description TEXT,
    applied_by VARCHAR(128),
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    rollback_sql TEXT,
    checksum VARCHAR(64)
);

-- Migration 001: Adicionar colunas de seguranca
INSERT INTO schema_migrations (version, description, applied_by, rollback_sql)
VALUES ('001', 'Add security columns to users', 'dba_admin',
        'ALTER TABLE users DROP COLUMN IF EXISTS mfa_enabled;');

-- Executar migration
ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INT DEFAULT 0;

-- Registrar
UPDATE schema_migrations SET 
    applied_at = NOW(),
    checksum = encode(sha256('001_add_security_columns'::bytea), 'hex')
WHERE version = '001';
```

## Anti-Pattern 27: Queries N+1

```sql
-- ANTI-PATTERN: Executar query para cada registro

-- ERRADO: N+1 query problem
-- Query 1: SELECT * FROM customers;
-- Para cada customer (N vezes):
--   Query 2: SELECT * FROM orders WHERE customer_id = ?;

-- CORRETO: Usar JOIN
SELECT c.*, o.*
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE c.is_active = TRUE;

-- CORRETO: Usar subquery
SELECT c.*,
    (SELECT COUNT(*) FROM orders WHERE customer_id = c.id) AS order_count,
    (SELECT SUM(total) FROM orders WHERE customer_id = c.id) AS total_spent
FROM customers c;

-- CORRETO: Usar CTE
WITH customer_orders AS (
    SELECT 
        customer_id,
        COUNT(*) AS order_count,
        SUM(total) AS total_spent
    FROM orders
    GROUP BY customer_id
)
SELECT c.*, co.order_count, co.total_spent
FROM customers c
LEFT JOIN customer_orders co ON c.id = co.customer_id;
```

## Anti-Pattern 28: Nao Usar LIMIT em Queries

```sql
-- ANTI-PATTERN: Queries sem LIMIT que retornam milhoes de linhas

-- ERRADO:
SELECT * FROM logs ORDER BY created_at DESC;
-- Retorna TODOS os logs (possivelmente bilhoes)

-- CORRETO: Sempre usar LIMIT para paginacao
SELECT * FROM logs ORDER BY created_at DESC LIMIT 100 OFFSET 0;

-- CORRETO: Usar cursor para iteracao
DECLARE log_cursor CURSOR FOR
    SELECT * FROM logs ORDER BY created_at DESC;

-- CORRETO: Usar batch processing
DO $$
DECLARE
    v_batch_size INT := 1000;
    v_offset INT := 0;
    v_rows INT;
BEGIN
    LOOP
        PERFORM * FROM logs ORDER BY id LIMIT v_batch_size OFFSET v_offset;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        EXIT WHEN v_rows = 0;
        
        -- Processar batch
        v_offset := v_offset + v_batch_size;
    END LOOP;
END $$;
```

## Anti-Pattern 29: Uso Indevido de SELECT FOR UPDATE

```sql
-- ANTI-PATTERN: FOR UPDATE em queries que nao precisam

-- ERRADO: FOR UPDATE em queries de leitura
SELECT * FROM products WHERE id = 1 FOR UPDATE;
-- Trava a linha desnecessariamente

-- ERRADO: FOR UPDATE em queries de relatorio
SELECT category, SUM(sales) FROM orders FOR UPDATE GROUP BY category;
-- Trava todas as linhas da tabela

-- CORRETO: FOR UPDATE apenas quando necessario
-- Quando voce PRECISA garantir que os dados nao mudem
BEGIN;
SELECT * FROM inventory WHERE product_id = 1 FOR UPDATE;
-- Agora seguro para atualizar
UPDATE inventory SET quantity = quantity - 1 WHERE product_id = 1;
COMMIT;

-- CORRETO: Usar NOWAIT para evitar esperas
SELECT * FROM inventory WHERE product_id = 1 FOR UPDATE NOWAIT;
-- Se a linha estiver travada, retorna erro imediatamente

-- CORRETO: Usar SKIP LOCKED para filas de job
SELECT * FROM job_queue 
WHERE status = 'PENDING'
ORDER BY created_at
LIMIT 1
FOR UPDATE SKIP LOCKED;
-- Pega proximo job disponivel sem esperar locks
```

## Anti-Pattern 30: Nao Usar EXPLAIN ANALYZE

```sql
-- ANTI-PATTERN: Otimizar queries sem analisar o plano de execucao

-- ERRADO: Adivinhar por que uma query e lenta

-- CORRETO: Sempre usar EXPLAIN ANALYZE
EXPLAIN ANALYZE
SELECT c.name, o.total, o.created_at
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE c.is_active = TRUE
AND o.created_at > '2024-01-01'
ORDER BY o.created_at DESC
LIMIT 100;

-- Analise do resultado:
-- 1. Seq Scan vs Index Scan
-- 2. Cost estimado vs actual
-- 3. Rows returned vs estimated
-- 4. Planning time vs execution time

-- CORRETO: Usar EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 123;

-- CORRETO: Salvar planos para comparacao
CREATE TABLE query_plans (
    plan_id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64),
    plan_json JSONB,
    execution_time_ms DECIMAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Anti-Pattern 31: Nao Gerenciar Conexões

```sql
-- ANTI-PATTERN: Conexoes abertas que nao sao fechadas

-- ERRADO:
-- conn = psycopg2.connect(...)
-- cursor = conn.cursor()
-- cursor.execute("SELECT ...")
-- # conn.close() esquecido!
-- Resultado: Conexoes acumulam, database fica sem slots

-- CORRETO: Usar context managers
-- Python:
-- with psycopg2.connect(...) as conn:
--     with conn.cursor() as cursor:
--         cursor.execute("SELECT ...")
-- # Conexao automaticamente fechada

-- CORRETO: Configurar timeout de conexao
ALTER SYSTEM SET tcp_keepalives_idle = 300;    -- 5 minutos
ALTER SYSTEM SET tcp_keepalives_interval = 60; -- 1 minuto
ALTER SYSTEM SET tcp_keepalives_count = 3;     -- 3 tentativas
ALTER SYSTEM SET idle_in_transaction_session_timeout = '10min';

-- Monitorar conexoes longas
SELECT 
    pid,
    usename,
    client_addr,
    state,
    query_start,
    NOW() - query_start AS duration,
    state_change,
    NOW() - state_change AS state_duration
FROM pg_stat_activity
WHERE state != 'idle'
AND query_start < NOW() - INTERVAL '5 minutes'
ORDER BY duration DESC;
```

## Anti-Pattern 32: Sem Indices para FULL TEXT SEARCH

```sql
-- ANTI-PATTERN: Full text search usando LIKE

-- ERRADO:
SELECT * FROM articles WHERE content LIKE '%seguranca%';
-- Seq Scan: O(1) - lenta em tabelas grandes

-- CORRETO: Usar GIN index com tsvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX idx_articles_content_gin ON articles 
USING GIN (to_tsvector('portuguese', content));

SELECT * FROM articles 
WHERE to_tsvector('portuguese', content) @@ to_tsquery('portuguese', 'seguranca');

-- CORRETO: Usar trigram similarity para busca fuzzy
CREATE INDEX idx_articles_content_trgm ON articles 
USING GIN (content gin_trgm_ops);

SELECT * FROM articles 
WHERE content % 'seguranca'  -- Similaridade
ORDER BY similarity(content, 'seguranca') DESC;
```

## Template: Incident Response Runbook

```sql
-- Template de runbook para resposta a incidentes

CREATE TABLE incident_runbooks (
    runbook_id SERIAL PRIMARY KEY,
    incident_type VARCHAR(100),
    severity VARCHAR(20),
    detection_method TEXT,
    immediate_actions TEXT[],
    investigation_steps TEXT[],
    containment_actions TEXT[],
    eradication_steps TEXT[],
    recovery_steps TEXT[],
    post_incident_review TEXT[],
    sla_hours INT,
    escalation_path TEXT
);

INSERT INTO incident_runbooks VALUES
(1, 'SQL_INJECTION_DETECTED', 'CRITICAL',
 'WAF alert, application logs, DAM anomaly',
 ARRAY['1. Block source IP immediately',
        '2. Enable enhanced logging',
        '3. Notify SOC team',
        '4. Preserve all logs'],
 ARRAY['1. Analyze WAF logs for payload',
        '2. Check application logs for exploitation',
        '3. Review database audit trail',
        '4. Identify affected tables/data'],
 ARRAY['1. Disable vulnerable endpoint',
        '2. Deploy WAF rule to block pattern',
        '3. Rotate affected credentials',
        '4. Enable additional monitoring'],
 ARRAY['1. Patch vulnerable code',
        '2. Deploy parameterized queries',
        '3. Verify WAF rules',
        '4. Conduct code review'],
 ARRAY['1. Restore from clean backup if needed',
        '2. Verify data integrity',
        '3. Resume normal operations',
        '4. Monitor for 72 hours'],
 ARRAY['1. Conduct post-incident review',
        '2. Document lessons learned',
        '3. Update WAF rules',
        '4. Update runbook'],
 1, 'SOC -> CISO -> Legal'),
(2, 'DATA_BREACH', 'CRITICAL',
 'DLP alert, unauthorized access logs, data exfiltration',
 ARRAY['1. Isolate affected systems',
        '2. Preserve forensic evidence',
        '3. Notify CISO and Legal',
        '4. Activate incident response team'],
 ARRAY['1. Determine scope of breach',
        '2. Identify affected data subjects',
        '3. Analyze access patterns',
        '4. Determine exfiltration method'],
 ARRAY['1. Revoke compromised credentials',
        '2. Block exfiltration channels',
        '3. Enable enhanced monitoring',
        '4. Segment affected systems'],
 ARRAY['1. Patch vulnerability used',
        '2. Strengthen access controls',
        '3. Implement additional monitoring',
        '4. Update security policies'],
 ARRAY['1. Notify affected individuals (72h LGPD)',
        '2. Notify regulatory authorities',
        '3. Offer credit monitoring',
        '4. Document breach details'],
 ARRAY['1. Full post-incident review',
        '2. Legal compliance assessment',
        '3. Update incident response plan',
        '4. Conduct additional training'],
 1, 'SOC -> CISO -> Legal -> CEO -> DPO');
```

## Template: Database Health Check

```sql
-- Template de health check para databases

CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE(
    check_name VARCHAR,
    status VARCHAR,
    details TEXT,
    recommendation TEXT
) AS $$
BEGIN
    -- 1. Conexoes
    check_name := 'Connections';
    SELECT 
        CASE 
            WHEN numbackends > max_conn * 0.8 THEN 'CRITICAL'
            WHEN numbackends > max_conn * 0.6 THEN 'WARNING'
            ELSE 'OK'
        END,
        FORMAT('%s/%s connections', numbackends, max_conn),
        CASE 
            WHEN numbackends > max_conn * 0.8 THEN 'Increase max_connections or optimize pool'
            ELSE 'Connection usage within limits'
        END
    INTO status, details, recommendation
    FROM pg_stat_database
    CROSS JOIN (SELECT setting::INT AS max_conn FROM pg_settings WHERE name = 'max_connections') mc
    WHERE datname = current_database();
    RETURN NEXT;
    
    -- 2. Cache Hit Ratio
    check_name := 'Cache Hit Ratio';
    SELECT 
        CASE 
            WHEN ratio < 0.95 THEN 'WARNING'
            ELSE 'OK'
        END,
        FORMAT('%.2f%%', ratio * 100),
        CASE 
            WHEN ratio < 0.95 THEN 'Increase shared_buffers or optimize queries'
            ELSE 'Cache performance is good'
        END
    INTO status, details, recommendation
    FROM (
        SELECT SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0) AS ratio
        FROM pg_statio_user_tables
    ) t;
    RETURN NEXT;
    
    -- 3. Dead Tuples
    check_name := 'Dead Tuples';
    SELECT 
        CASE 
            WHEN SUM(n_dead_tup) > 100000 THEN 'WARNING'
            ELSE 'OK'
        END,
        FORMAT('%s dead tuples across all tables', SUM(n_dead_tup)),
        CASE 
            WHEN SUM(n_dead_tup) > 100000 THEN 'Run VACUUM on tables with most dead tuples'
            ELSE 'Dead tuple count is acceptable'
        END
    INTO status, details, recommendation
    FROM pg_stat_user_tables;
    RETURN NEXT;
    
    -- 4. Replication Lag
    check_name := 'Replication Lag';
    SELECT 
        CASE 
            WHEN EXTRACT(EPOCH FROM replay_lag) > 300 THEN 'CRITICAL'
            WHEN EXTRACT(EPOCH FROM replay_lag) > 60 THEN 'WARNING'
            ELSE 'OK'
        END,
        EXTRACT(EPOCH FROM replay_lag)::TEXT || ' seconds',
        CASE 
            WHEN EXTRACT(EPOCH FROM replay_lag) > 300 THEN 'Investigate replication issues immediately'
            ELSE 'Replication lag is acceptable'
        END
    INTO status, details, recommendation
    FROM pg_stat_replication
    LIMIT 1;
    RETURN NEXT;
    
    -- 5. Lock Wait
    check_name := 'Lock Wait';
    SELECT 
        CASE 
            WHEN COUNT(*) > 0 THEN 'WARNING'
            ELSE 'OK'
        END,
        COUNT(*)::TEXT || ' waiting locks',
        CASE 
            WHEN COUNT(*) > 0 THEN 'Investigate blocking queries'
            ELSE 'No lock contention detected'
        END
    INTO status, details, recommendation
    FROM pg_locks
    WHERE NOT granted;
    RETURN NEXT;
END;
$$ LANGUAGE plsql;

-- Executar health check
SELECT * FROM database_health_check();
```

## Template: Security Audit Query

```sql
-- Template de query de auditoria de seguranca

-- 1. Verificar usuarios com permissoes excessivas
SELECT 
    r.rolname,
    r.rolsuper,
    r.rolcreaterole,
    r.rolcreatedb,
    r.rolcanlogin,
    r.rolreplication,
    (SELECT string_agg(b.rolname, ', ') 
     FROM pg_catalog.pg_auth_members m
     JOIN pg_catalog.pg_roles b ON m.roleid = b.oid
     WHERE m.member = r.oid) AS member_of,
    CASE 
        WHEN r.rolsuper THEN 'CRITICAL: Has superuser'
        WHEN r.rolcreaterole THEN 'HIGH: Can create roles'
        WHEN r.rolcreatedb THEN 'MEDIUM: Can create databases'
        ELSE 'OK'
    END AS risk_level
FROM pg_roles r
WHERE r.rolname NOT LIKE 'pg_%'
ORDER BY r.rolsuper DESC, r.rolcreaterole DESC;

-- 2. Verificar tabelas sem audit trail
SELECT 
    t.table_schema,
    t.table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.triggers 
            WHERE event_object_table = t.table_name
            AND trigger_name LIKE 'audit_%'
        ) THEN 'AUDITED'
        ELSE 'NOT AUDITED'
    END AS audit_status
FROM information_schema.tables t
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
AND t.table_type = 'BASE TABLE'
ORDER BY audit_status, t.table_name;

-- 3. Verificar conexoes sem SSL
SELECT 
    pid,
    usename,
    client_addr,
    client_port,
    ssl,
    CASE 
        WHEN NOT ssl THEN 'CRITICAL: No SSL'
        ELSE 'OK'
    END AS ssl_status
FROM pg_stat_ssl
JOIN pg_stat_activity USING (pid)
WHERE client_addr IS NOT NULL;

-- 4. Verificar indices nao utilizados
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    CASE 
        WHEN idx_scan = 0 AND pg_relation_size(indexrelid) > 1048576 THEN 'WARNING: Large unused index'
        ELSE 'OK'
    END AS status
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- 5. Verificar tabelas sem backup recente
SELECT 
    schemaname,
    relname,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    CASE 
        WHEN last_vacuum IS NULL THEN 'WARNING: Never vacuumed'
        WHEN last_vacuum < NOW() - INTERVAL '7 days' THEN 'WARNING: Vacuum overdue'
        ELSE 'OK'
    END AS vacuum_status
FROM pg_stat_user_tables
ORDER BY last_vacuum NULLS FIRST;
```

## Template: Encryption Key Rotation

```sql
-- Template de rotacao de chaves de criptografia

-- 1. Criar nova chave
CREATE OR REPLACE FUNCTION rotate_encryption_key(
    p_key_name VARCHAR
)
RETURNS UUID AS $$
DECLARE
    v_old_key_id UUID;
    v_new_key_id UUID;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    -- Obter chave atual
    SELECT key_id INTO v_old_key_id
    FROM encryption_key_management
    WHERE key_name = p_key_name
    AND is_active = TRUE;
    
    -- Gerar nova chave
    v_new_key_id := gen_random_uuid();
    
    INSERT INTO encryption_key_management (
        key_id, key_name, key_type, key_algorithm, key_length,
        key_material_encrypted, created_by, expires_at, is_active
    )
    VALUES (
        v_new_key_id, p_key_name, 'DATA', 'AES-256', 256,
        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), v_master_key),
        current_user, NOW() + INTERVAL '90 days', TRUE
    );
    
    -- Marcar chave antiga como inativa (nao deletar imediatamente)
    UPDATE encryption_key_management
    SET is_active = FALSE,
        rotated_at = NOW()
    WHERE key_id = v_old_key_id;
    
    -- Log de rotacao
    INSERT INTO key_rotation_log (old_key_id, new_key_id, rotated_by, rotated_at)
    VALUES (v_old_key_id, v_new_key_id, current_user, NOW());
    
    RETURN v_new_key_id;
END;
$$ LANGUAGE plpgsql;

-- 2. Migrar dados para nova chave
CREATE OR REPLACE FUNCTION reencrypt_data_with_new_key(
    p_table_name VARCHAR,
    p_column_name VARCHAR,
    p_key_name VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_old_key TEXT;
    v_new_key TEXT;
    v_affected_rows INT;
BEGIN
    -- Obter chaves
    SELECT pgp_sym_decrypt(key_material_encrypted, current_setting('app.master_key'))
    INTO v_old_key
    FROM encryption_key_management
    WHERE key_name = p_key_name
    AND is_active = FALSE
    ORDER BY rotated_at DESC
    LIMIT 1;
    
    SELECT pgp_sym_decrypt(key_material_encrypted, current_setting('app.master_key'))
    INTO v_new_key
    FROM encryption_key_management
    WHERE key_name = p_key_name
    AND is_active = TRUE;
    
    -- Re-criptografar dados
    EXECUTE format(
        'UPDATE %I SET %I = pgp_sym_decrypt(%I, %L) WHERE %I IS NOT NULL',
        p_table_name, p_column_name || '_temp',
        p_column_name, v_old_key,
        p_column_name
    );
    
    EXECUTE format(
        'UPDATE %I SET %I = pgp_sym_encrypt(pgp_sym_decrypt(%I, %L), %L) WHERE %I IS NOT NULL',
        p_table_name, p_column_name,
        p_column_name, v_old_key, v_new_key,
        p_column_name
    );
    
    GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
    RETURN v_affected_rows;
END;
$$ LANGUAGE plpgsql;
```

## Template: Data Classification Automation

```sql
-- Template de classificacao automatica de dados

-- 1. Detectar dados sensiveis automaticamente
CREATE OR REPLACE FUNCTION auto_classify_columns()
RETURNS TABLE(
    table_name VARCHAR,
    column_name VARCHAR,
    detected_type VARCHAR,
    suggested_classification VARCHAR,
    confidence DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.table_name::VARCHAR,
        c.column_name::VARCHAR,
        c.data_type::VARCHAR,
        CASE 
            WHEN c.column_name ~* '(ssn|social_security|cpf|cnpj)' THEN 'RESTRICTED'
            WHEN c.column_name ~* '(credit_card|card_number|cvv|payment)' THEN 'RESTRICTED'
            WHEN c.column_name ~* '(password|pass|secret|token|key)' THEN 'RESTRICTED'
            WHEN c.column_name ~* '(email|phone|address|birth)' THEN 'CONFIDENTIAL'
            WHEN c.column_name ~* '(name|first_name|last_name)' THEN 'CONFIDENTIAL'
            WHEN c.column_name ~* '(status|type|category)' THEN 'INTERNAL'
            ELSE 'PUBLIC'
        END::VARCHAR,
        CASE 
            WHEN c.column_name ~* '(ssn|social_security|cpf|cnpj)' THEN 0.95
            WHEN c.column_name ~* '(credit_card|card_number|cvv|payment)' THEN 0.95
            WHEN c.column_name ~* '(password|pass|secret|token|key)' THEN 0.90
            WHEN c.column_name ~* '(email|phone|address|birth)' THEN 0.80
            WHEN c.column_name ~* '(name|first_name|last_name)' THEN 0.75
            ELSE 0.50
        END::DECIMAL
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
    AND c.table_name NOT LIKE 'pg_%'
    AND c.table_name NOT LIKE 'sql_%';
END;
$$ LANGUAGE plpgsql;

-- 2. Aplicar classificacao detectada
INSERT INTO table_classification (schema_name, table_name, column_name, classification_level)
SELECT 
    'public',
    table_name,
    column_name,
    CASE detected_type
        WHEN 'RESTRICTED' THEN 5
        WHEN 'CONFIDENTIAL' THEN 4
        WHEN 'INTERNAL' THEN 3
        WHEN 'PUBLIC' THEN 1
    END
FROM auto_classify_columns()
WHERE confidence > 0.7
ON CONFLICT (schema_name, table_name, column_name) 
DO UPDATE SET 
    classification_level = EXCLUDED.classification_level,
    last_reviewed = CURRENT_DATE;
```

## Template: Performance Tuning Checklist

```sql
-- Template de verificacao de performance

-- 1. Queries mais lentas (top 10)
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 2. Tabelas com mais dead tuples
SELECT 
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    ROUND(n_dead_tup::DECIMAL / NULLIF(n_live_tup, 0) * 100, 2) AS dead_pct,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- 3. Indices nao utilizados
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND pg_relation_size(indexrelid) > 1048576
ORDER BY pg_relation_size(indexrelid) DESC;

-- 4. Tables seq scan (possivel falta de indice)
SELECT 
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    CASE 
        WHEN seq_scan > 1000 AND (idx_scan IS NULL OR idx_scan = 0) THEN 'MISSING INDEX'
        WHEN seq_scan > idx_scan THEN 'CONSIDER INDEX'
        ELSE 'OK'
    END AS recommendation
FROM pg_stat_user_tables
WHERE seq_scan > 1000
ORDER BY seq_tup_read DESC;

-- 5. Cache hit ratio
SELECT 
    SUM(heap_blks_hit) / NULLIF(SUM(heap_blks_hit) + SUM(heap_blks_read), 0) AS cache_hit_ratio
FROM pg_statio_user_tables;
-- Ideal: > 0.99

-- 6. Transaction wraparound
SELECT 
    datname,
    age(datfrozenxid),
    ROUND(age(datfrozenxid)::DECIMAL / 2147483647 * 100, 2) AS pct_to_wraparound
FROM pg_database
WHERE datname = current_database();
-- Alerta se > 75%

-- 7. Connection usage
SELECT 
    numbackends,
    (SELECT setting::INT FROM pg_settings WHERE name = 'max_connections') AS max_conn,
    ROUND(numbackends::DECIMAL / 
          (SELECT setting::INT FROM pg_settings WHERE name = 'max_connections') * 100, 1) AS usage_pct
FROM pg_stat_database
WHERE datname = current_database();

-- 8. WAL generation rate
SELECT 
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')) AS total_wal,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), 
        pg_current_wal_lsn() - '1 GB'::interval)) AS wal_last_hour;
```

## Template: Security Hardening Checklist

```sql
-- Template de hardening de seguranca

-- 1. Verificar configuracoes de seguranca
CREATE OR REPLACE FUNCTION security_hardening_check()
RETURNS TABLE(
    setting_name VARCHAR,
    current_value TEXT,
    recommended_value TEXT,
    status VARCHAR
) AS $$
BEGIN
    -- SSL habilitado
    setting_name := 'ssl';
    current_value := current_setting('ssl');
    recommended_value := 'on';
    status := CASE WHEN current_setting('ssl') = 'on' THEN 'OK' ELSE 'CRITICAL' END;
    RETURN NEXT;
    
    -- Protocolo SSL minimo
    setting_name := 'ssl_min_protocol_version';
    current_value := current_setting('ssl_min_protocol_version');
    recommended_value := 'TLSv1.3';
    status := CASE WHEN current_setting('ssl_min_protocol_version') = 'TLSv1.3' 
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Log de autenticacao
    setting_name := 'log_authentication';
    current_value := current_setting('log_authentication');
    recommended_value := 'on';
    status := CASE WHEN current_setting('log_authentication') = 'on' 
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Log de conexoes
    setting_name := 'log_connections';
    current_value := current_setting('log_connections');
    recommended_value := 'on';
    status := CASE WHEN current_setting('log_connections') = 'on' 
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Log de disconexoes
    setting_name := 'log_disconnections';
    current_value := current_setting('log_disconnections');
    recommended_value := 'on';
    status := CASE WHEN current_setting('log_disconnections') = 'on' 
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Password encryption
    setting_name := 'password_encryption';
    current_value := current_setting('password_encryption');
    recommended_value := 'scram-sha-256';
    status := CASE WHEN current_setting('password_encryption') = 'scram-sha-256' 
              THEN 'OK' ELSE 'CRITICAL' END;
    RETURN NEXT;
    
    -- Log de comandos DDL
    setting_name := 'log_statement';
    current_value := current_setting('log_statement');
    recommended_value := 'ddl';
    status := CASE WHEN current_setting('log_statement') IN ('ddl', 'all') 
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Tempo idle in transaction
    setting_name := 'idle_in_transaction_session_timeout';
    current_value := current_setting('idle_in_transaction_session_timeout');
    recommended_value := '300000';  -- 5 minutos em ms
    status := CASE WHEN current_setting('idle_in_transaction_session_timeout')::INT <= 300000
              THEN 'OK' ELSE 'WARNING' END;
    RETURN NEXT;
    
    -- Max failed logins
    setting_name := 'password_max_failed_attempts';
    current_value := COALESCE(current_setting('password_max_failed_attempts', TRUE), 'N/A');
    recommended_value := '5';
    status := 'CHECK MANUALLY';
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Executar verificacao
SELECT * FROM security_hardening_check();
```

## Resumo Final

Este capitulo consolidou as principais praticas, anti-patterns e templates para databases seguros e performaticos. Os 32 anti-patterns cobrem os erros mais comuns em desenvolvimento e administracao de databases, desde SQL injection basica ate problemas avancados de concorrencia e particionamento.

A security checklist com 50+ itens serve como referencia completa para verificacao de conformidade com PCI DSS, LGPD, GDPR, HIPAA, SOC 2 e ISO 27001. Cada item e verificavel e accionavel.

Os templates de schema, query, migration, backup, incident response, health check e security audit fornecem um ponto de partida seguro e profissional para novos projetos. Cada template e testado e segue as melhores praticas da industria.

As referencias rapidas de SQL injection prevention, index design e isolation levels servem como consulta no dia-a-dia, com exemplos praticos e decisoes de design.

Os principais pontos a lembrar:

**Seguranca comeca no design.** Um schema bem projetado, com constraints, criptografia e audit trail desde o inicio, e muito mais facil de proteger do que um schema legado sem esses controles. Invista tempo no design antes de escrever codigo.

**Least privilege e nao negociavel.** Cada usuario, aplicacao e servico deve ter apenas as permissoes estritamente necessarias. Isso inclui o usuario do banco de dados da aplicacao. Revisoes regulares de acesso sao obrigatorias.

**Monitoramento e deteccao.** Sem monitoramento, e impossivel saber se seus dados estao seguros. Audit trails, alertas e dashboards sao investimentos obrigatorios, nao opcionais. Deteccao de anomalias deve ser em tempo real.

**Testes regulares.** Backup testado e backup que funciona. Incident response testado e response que funciona. Penetration test identifica vulnerabilidades antes dos atacantes. Cada teste deve ser documentado e repetido.

**Compliance e continuo.** Regulamentacoes evoluem, novos requisitos sao adicionados. Automacao de compliance e a chave para manter conformidade ao longo do tempo. Cada verificacao deve ser automatizada e executada regularmente.

**Performance e seguranca caminham juntas.** Indices adequados reduzem tempo de resposta e previnem ataques de denial of service. Query optimization reduz uso de recursos e facilita monitoring. Conexao pooling melhora performance e previne exaustao de recursos.

**Documentacao e essencial.** Runbooks, playbooks e procedures devem ser documentados, testados e mantidos atualizados. Em um incidente, nao ha tempo para pensar — ha tempo apenas para executar o plano documentado.

**Evolucao continua.** A seguranca de databases nao e um estado estatico. Novas vulnerabilidades sao descobertas, novos vetores de ataque surgem, regulamentacoes mudam. A equipe de seguranca e banco de dados deve estar em aprendizado continuo.

A seguranca de databases e uma responsabilidade compartilhada entre desenvolvedores, DBAs, administradores de rede, equipe de seguranca e lideranca executiva. Cada profissional que interage com dados sensiveis tem um papel na protecao desses dados. Desde o desenvolvedor que escreve queries parametrizadas ate o CISO que define a estrategia de seguranca, todos contribuem para a postura de seguranca da organizacao.

Os templates e checklists deste capitulo devem ser customizados para cada organizacao, considerando seu stack tecnologico, regulamentacoes aplicaveis, perfil de risco e maturidade de seguranca. Nao existe solucao unica para todas as organizacoes, mas os principios fundamentais sao universais.

Use este capitulo como referencia viva. Consulte os anti-patterns antes de escrever queries criticas. Revise a security checklist trimestralmente. Atualize os templates conforme novas versoes de SGBDRs e regulamentacoes sao lancadas. A seguranca e uma jornada, nao um destino.

## Estudo de Caso: Aplicando os Anti-Patterns

### Exemplo Real de Correcao

```sql
-- CENARIO: E-commerce brasileiro com violacao de dados
-- Problema: SQL injection expôs 500K registros de clientes

-- CODIGO ANTES (vulneravel):
-- query = "SELECT * FROM customers WHERE cpf = '" + cpf + "'"
-- query = "INSERT INTO orders (customer_id, total) VALUES (" + customer_id + ", " + total + ")"
-- query = "UPDATE users SET password = '" + new_password + "' WHERE id = " + user_id

-- CODIGO DEPOIS (seguro):

-- 1. Parametrizacao de queries
-- Preparar statements
PREPARE get_customer_by_cpf AS
SELECT id, name, email, phone 
FROM customers 
WHERE cpf = $1;

PREPARE insert_order AS
INSERT INTO orders (customer_id, total, status)
VALUES ($1, $2, 'PENDING');

PREPARE update_password AS
UPDATE users 
SET password_hash = $1, 
    password_changed_at = NOW(),
    updated_at = NOW()
WHERE id = $2;

-- 2. Stored procedures para operacoes criticas
CREATE PROCEDURE process_payment(
    p_customer_id UUID,
    p_amount DECIMAL,
    p_card_token VARCHAR
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_order_id UUID;
    v_payment_id UUID;
BEGIN
    -- Validar entrada
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Invalid payment amount: %', p_amount;
    END IF;
    
    -- Criar pedido
    INSERT INTO orders (customer_id, total, status)
    VALUES (p_customer_id, p_amount, 'CONFIRMED')
    RETURNING id INTO v_order_id;
    
    -- Registrar pagamento
    INSERT INTO payments (order_id, amount, card_token, status)
    VALUES (v_order_id, p_amount, p_card_token, 'COMPLETED')
    RETURNING id INTO v_payment_id;
    
    -- Atualizar estoque
    UPDATE inventory 
    SET quantity = quantity - 1
    WHERE product_id IN (
        SELECT product_id FROM order_items WHERE order_id = v_order_id
    );
    
    -- Log de auditoria
    INSERT INTO audit_log (event_type, user_id, table_name, record_id)
    VALUES ('PAYMENT_PROCESSED', current_user, 'payments', v_payment_id);
END;
$$;

-- 3. Row-Level Security
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY customers_isolation ON customers
    USING (id = current_setting('app.current_customer_id')::UUID);

CREATE POLICY orders_isolation ON orders
    USING (customer_id = current_setting('app.current_customer_id')::UUID);

-- 4. Audit trail completo
CREATE TRIGGER audit_customers
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION audit.log_change();

-- 5. Monitoramento em tempo real
CREATE OR REPLACE FUNCTION monitor_suspicious_queries()
RETURNS TRIGGER AS $$
BEGIN
    -- Detectar padroes de SQL injection
    IF NEW.query_text ~* "(union\s+select|exec\s+|execute\s+)" THEN
        PERFORM pg_notify('security_alert',
            FORMAT('SQL INJECTION ATTEMPT: User %s from %s',
                   NEW.user_name, NEW.client_ip));
        
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('SQL_INJECTION_ATTEMPT', NEW.user_name, 'CRITICAL',
                LEFT(NEW.query_text, 500));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Metricas de Melhoria

```sql
-- Antes vs Depois da implementacao das boas praticas

CREATE TABLE security_improvement_metrics (
    metric_name VARCHAR(100),
    before_value VARCHAR(50),
    after_value VARCHAR(50),
    improvement_pct DECIMAL(5,2)
);

INSERT INTO security_improvement_metrics VALUES
('SQL Injection Vulnerabilities', '12', '0', 100.00),
('Unencrypted Sensitive Data', '500000', '0', 100.00),
('Users Without MFA', '150', '0', 100.00),
('Queries Without Audit Trail', '80%', '0%', 100.00),
('Dead Tuples (millions)', '15', '0.5', 96.67),
('Average Query Time (ms)', '450', '85', 81.11),
('Cache Hit Ratio', '92%', '99.5%', 8.15),
('Failed Login Detection Time', '7 days', '5 minutes', 99.95),
('Backup Restoration Time', '12 hours', '45 minutes', 93.75),
('Incident Response Time', '48 hours', '1 hour', 97.92');

-- Dashboard de melhoria
SELECT 
    metric_name,
    before_value,
    after_value,
    improvement_pct,
    CASE 
        WHEN improvement_pct >= 90 THEN 'EXCELLENT'
        WHEN improvement_pct >= 70 THEN 'GOOD'
        WHEN improvement_pct >= 50 THEN 'MODERATE'
        ELSE 'NEEDS IMPROVEMENT'
    END AS rating
FROM security_improvement_metrics
ORDER BY improvement_pct DESC;
```

## Guia de Referencia Rapida Final

### Comandos Essenciais do Dia-a-Dia

```sql
-- 1. Verificar status do banco
SELECT * FROM pg_stat_database WHERE datname = current_database();

-- 2. Listar queries ativas
SELECT pid, usename, state, query, query_start 
FROM pg_stat_activity WHERE state = 'active';

-- 3. Matar query longa
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE state = 'active' AND query_start < NOW() - INTERVAL '1 hour';

-- 4. Verificar indices
SELECT * FROM pg_stat_user_indexes ORDER BY idx_scan DESC;

-- 5. Verificar locks
SELECT l.*, a.query, a.usename 
FROM pg_locks l 
JOIN pg_stat_activity a ON l.pid = a.pid 
WHERE NOT l.granted;

-- 6. Vacuum em tabela especifica
VACUUM (VERBOSE, ANALYZE) tabela_nome;

-- 7. Verificar tamanho das tabelas
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;

-- 8. Verificar replicacao
SELECT * FROM pg_stat_replication;

-- 9. Verificar cache hit ratio
SELECT SUM(heap_blks_hit) / (SUM(heap_blks_hit) + SUM(heap_blks_read)) 
FROM pg_statio_user_tables;

-- 10. Verificar configuracoes de seguranca
SELECT name, setting, category FROM pg_settings 
WHERE category = 'Connections and Authentication';
```

### One-Liners de Emergencia

```sql
-- Ver todos os usuarios conectados
SELECT usename, client_addr, state, query FROM pg_stat_activity;

-- Matar todas as queries de um usuario
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'problema';

-- Verificar se ha backup recente
SELECT * FROM pg_backup_start_time ORDER BY backup_start DESC LIMIT 1;

-- Forcar checkpoint
CHECKPOINT;

-- Verificar uso de disco
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Verificar transacoes longas
SELECT pid, usename, xact_start, NOW() - xact_start AS duration 
FROM pg_stat_activity WHERE xact_start IS NOT NULL ORDER BY xact_start;
```