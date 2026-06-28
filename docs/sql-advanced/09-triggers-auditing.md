# Capítulo 9: Triggers e Auditing

## Introdução

Triggers são procedimentos executados automaticamente pelo SGBD em resposta a eventos de manipulação de dados (INSERT, UPDATE, DELETE). Quando implementados corretamente, são uma das ferramentas mais poderosas para auditoria, integridade de dados e conformidade regulatória. Este capítulo cobre tipos de triggers, design de tabelas de auditoria, Change Data Capture (CDC), temporal tables, soft deletes, logging patterns e exemplos completos nos principais SGBDR.

---

## Tipos de Triggers

### Classificação por Momento de Execução

**BEFORE Triggers (Row-level):**

Executados antes da operação DML ser aplicada ao banco de dados. Permitem modificar ou rejeitar valores antes da persistência.

```sql
-- PostgreSQL: BEFORE trigger para validação
CREATE OR REPLACE FUNCTION validate_employee_salary()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.salary < 0 THEN
        RAISE EXCEPTION 'Salary cannot be negative';
    END IF;
    
    IF NEW.salary > 1000000 THEN
        RAISE WARNING 'Salary exceeds maximum threshold';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_salary
BEFORE INSERT OR UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION validate_employee_salary();
```

**AFTER Triggers (Row-level):**

Executados após a operação DML ser aplicada. Usados para auditoria, atualização de tabelas relacionadas e logging.

```sql
-- PostgreSQL: AFTER trigger para auditoria
CREATE OR REPLACE FUNCTION audit_employee_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO employee_audit (
        employee_id,
        action,
        old_data,
        new_data,
        changed_by,
        changed_at
    ) VALUES (
        NEW.employee_id,
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION audit_employee_changes();
```

### Classificação por Granularidade

**Row-level Triggers:**

Executados uma vez para cada linha afetada pela operação DML.

```sql
-- SQL Server: Row-level trigger
CREATE TRIGGER trg_AuditProducts
ON Products
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Para INSERTs
    INSERT INTO ProductAudit (ProductID, Action, NewValues, ChangedBy, ChangedAt)
    SELECT 
        ProductID,
        'INSERT',
        (SELECT * FROM inserted i WHERE i.ProductID = ins.ProductID FOR JSON PATH),
        SYSTEM_USER,
        GETDATE()
    FROM inserted ins;
    
    -- Para DELETEs
    INSERT INTO ProductAudit (ProductID, Action, OldValues, ChangedBy, ChangedAt)
    SELECT 
        ProductID,
        'DELETE',
        (SELECT * FROM deleted d WHERE d.ProductID = del.ProductID FOR JSON PATH),
        SYSTEM_USER,
        GETDATE()
    FROM deleted del;
    
    -- Para UPDATEs
    INSERT INTO ProductAudit (ProductID, Action, OldValues, NewValues, ChangedBy, ChangedAt)
    SELECT 
        i.ProductID,
        'UPDATE',
        (SELECT * FROM deleted d WHERE d.ProductID = i.ProductID FOR JSON PATH),
        (SELECT * FROM inserted i2 WHERE i2.ProductID = i.ProductID FOR JSON PATH),
        SYSTEM_USER,
        GETDATE()
    FROM inserted i
    JOIN deleted d ON i.ProductID = d.ProductID;
END;
GO
```

**Statement-level Triggers:**

Executados uma vez para cada instrução DML, independente do número de linhas afetadas.

```sql
-- PostgreSQL: Statement-level trigger
CREATE OR REPLACE FUNCTION log_bulk_operation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO bulk_operation_log (
        table_name,
        operation,
        rows_affected,
        performed_by,
        performed_at
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        (SELECT COUNT(*) FROM inserted),
        current_user,
        CURRENT_TIMESTAMP
    );
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger statement-level
CREATE TRIGGER trg_log_bulk_operations
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH STATEMENT EXECUTE FUNCTION log_bulk_operation();
```

### Resumo dos Tipos

| Tipo | Execução | Uso Principal |
|------|----------|---------------|
| BEFORE Row | Antes de cada linha | Validação, modificação de valores |
| AFTER Row | Depois de cada linha | Auditoria, atualização de tabelas relacionadas |
| BEFORE Statement | Antes da instrução | Validação de integridade |
| AFTER Statement | Depois da instrução | Logging, notificações |

---

## Row-level vs Statement-level

### Quando Usar Cada Tipo

**Row-level é adequado quando:**
- Cada linha precisa de processamento individual
- Validação depende de valores específicos da linha
- Auditoria precisa do estado anterior e posterior de cada registro
- Atualização cascata em tabelas relacionadas

**Statement-level é adequado quando:**
- Ação depende apenas do número de linhas afetadas
- Logging agregado de operações em lote
- Notificações sobre atividade geral
- Validações de integridade global

### Exemplo Comparativo

```sql
-- ROW-LEVEL: Auditoria individual por linha
CREATE OR REPLACE FUNCTION audit_individual_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        action,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        TG_TABLE_NAME,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_row
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION audit_individual_changes();

-- STATEMENT-LEVEL: Log agregado da operação
CREATE OR REPLACE FUNCTION log_operation_summary()
RETURNS TRIGGER AS $$
DECLARE
    v_rows_affected INTEGER;
BEGIN
    -- Contar linhas afetadas
    IF TG_OP = 'INSERT' THEN
        SELECT COUNT(*) INTO v_rows_affected FROM inserted;
    ELSIF TG_OP = 'UPDATE' THEN
        SELECT COUNT(*) INTO v_rows_affected FROM inserted;
    ELSIF TG_OP = 'DELETE' THEN
        SELECT COUNT(*) INTO v_rows_affected FROM deleted;
    END IF;
    
    INSERT INTO operation_log (
        table_name,
        operation,
        rows_affected,
        executed_by,
        executed_at
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        v_rows_affected,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_statement
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH STATEMENT EXECUTE FUNCTION log_operation_summary();
```

### Performance: Row vs Statement

```sql
-- Row-level: Mais overhead (uma inserção por linha)
-- Para 10.000 linhas = 10.000 inserções na tabela de audit

-- Statement-level: Menos overhead (uma inserção por operação)
-- Para 10.000 linhas = 1 inserção na tabela de log

-- RECOMENDAÇÃO: Usar statement-level para logging geral,
-- row-level apenas quando necessário para auditoria detalhada
```

---

## Trigger Security Risks

### Riscos Associados a Triggers

1. **Execução de código arbitrário** — triggers podem executar procedures com permissões elevadas
2. **Bypass de controles de acesso** — triggers com SECURITY DEFINER executam com permissões do owner
3. **Injeção de código** — triggers com Dynamic SQL vulneráveis a injeção
4. **Performance degradation** — triggers podem causar locks e degradação de performance
5. **Cascata de triggers** — triggers que disparam outros triggers podem criar loops infinitos

### Exemplo de Vulnerabilidade

```sql
-- VULNERAVEL: Trigger com Dynamic SQL
CREATE OR REPLACE FUNCTION vulnerable_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    v_sql TEXT;
BEGIN
    -- VULNERAVEL: interpolação direta de dados do usuário
    v_sql := format(
        'INSERT INTO audit_log (data) VALUES (''%s'')',
        NEW.user_data  -- Dados do usuário diretamente na query
    );
    
    EXECUTE v_sql;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Atacante pode injetar SQL via user_data
-- user_data: "'); DROP TABLE important_data;--"
```

```sql
-- VULNERAVEL: Trigger com SECURITY DEFINER e permissões excessivas
CREATE OR REPLACE FUNCTION admin_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    -- Executa com permissões do owner (admin)
    -- Se o trigger estiver comprometido, pode executar qualquer coisa
    INSERT INTO sensitive_table (data) VALUES (NEW.data);
    
    -- Perigoso: pode ser explorado para elevar privilégios
    UPDATE users SET role = 'admin' WHERE username = NEW.username;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- SECURRITO: SECURITY DEFINER deve ser evitado quando possível
-- ou usado com extrema cautela
```

### Mitigação de Riscos

```sql
-- 1. SEMPRE validar dados antes de usar em Dynamic SQL
CREATE OR REPLACE FUNCTION safe_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    -- Validar que dados são seguros
    IF NEW.data ~ '[;''\\]' THEN
        RAISE EXCEPTION 'Invalid data contains dangerous characters';
    END IF;
    
    -- Usar parâmetros ao invés de interpolação
    INSERT INTO audit_log (data) VALUES (NEW.data);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Limitar permissões de triggers
CREATE ROLE trigger_role;
GRANT INSERT ON audit_log TO trigger_role;
REVOKE ALL ON sensitive_table FROM trigger_role;

-- 3. Usar SECURITY INVOKER (padrão) ao invés de SECURITY DEFINER
CREATE OR REPLACE FUNCTION safe_audit_func()
RETURNS TRIGGER AS $$
BEGIN
    -- Executa com permissões do usuário que executou a operação original
    INSERT INTO audit_log (data) VALUES (NEW.data);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER;

-- 4. Evitar cascata de triggers
-- Configurar limite de profundidade
-- PostgreSQL: não há limite configurável, mas triggers não causam cascata por padrão
-- SQL Server: limitar com SET RECURSIVE_TRIGGERS
```

---

## Audit Table Design

### Princípios de Design

Uma tabela de auditoria bem projetada deve:

1. **Ser imutável** — registros de auditoria nunca devem ser alterados ou excluídos
2. **Conter metadados completos** — quem, quando, onde, o quê
3. **Preservar estado anterior e posterior** — para comparação
4. **Ser indexada adequadamente** — para consultas de auditoria
5. **Suportar retenção de dados** — política de purge

### Schema de Tabela de Auditoria

```sql
-- PostgreSQL: Tabela de auditoria completa
CREATE TABLE audit.audit_log (
    -- Identificador único
    id BIGSERIAL PRIMARY KEY,
    
    -- Informações da tabela
    table_schema VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    
    -- Identificador do registro modificado
    record_id VARCHAR(100),
    
    -- Operação realizada
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    
    -- Dados antes e depois
    old_data JSONB,
    new_data JSONB,
    
    -- Metadados de contexto
    changed_by VARCHAR(100) NOT NULL DEFAULT current_user,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Informações de sessão
    session_id VARCHAR(100),
    client_ip INET,
    application_name VARCHAR(100),
    
    -- Informações adicionais
    change_reason TEXT,
    transaction_id BIGINT,
    
    -- Índices para consultas
    CONSTRAINT audit_log_no_update CHECK (TRUE)  -- Impede UPDATEs
);

-- Índices para performance
CREATE INDEX idx_audit_log_table ON audit.audit_log(table_name);
CREATE INDEX idx_audit_log_record ON audit.audit_log(record_id);
CREATE INDEX idx_audit_log_action ON audit.audit_log(action);
CREATE INDEX idx_audit_log_changed_by ON audit.audit_log(changed_by);
CREATE INDEX idx_audit_log_changed_at ON audit.audit_log(changed_at);
CREATE INDEX idx_audit_log_composite ON audit.audit_log(table_name, record_id, changed_at);

-- Particionar por data para performance
CREATE TABLE audit.audit_log (
    id BIGSERIAL,
    table_schema VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    action VARCHAR(20) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    session_id VARCHAR(100),
    client_ip INET,
    PRIMARY KEY (id, changed_at)
) PARTITION BY RANGE (changed_at);

-- Criar partições mensais
CREATE TABLE audit.audit_log_2024_01 PARTITION OF audit.audit_log
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit.audit_log_2024_02 PARTITION OF audit.audit_log
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Continuar para cada mês...
```

### SQL Server: Tabela de Auditoria

```sql
-- SQL Server: Tabela de auditoria com temporal tables
CREATE TABLE dbo.EmployeeAudit (
    AuditID BIGINT PRIMARY KEY IDENTITY(1,1),
    EmployeeID INT NOT NULL,
    Action NVARCHAR(10) NOT NULL,
    OldData NVARCHAR(MAX),  -- JSON
    NewData NVARCHAR(MAX),  -- JSON
    ChangedBy NVARCHAR(100) NOT NULL DEFAULT SYSTEM_USER,
    ChangedAt DATETIME2(7) NOT NULL DEFAULT SYSDATETIME(),
    ClientIP NVARCHAR(50),
    ApplicationName NVARCHAR(100),
    SessionID INT DEFAULT @@SPID
);

-- Índices
CREATE INDEX IX_EmployeeAudit_EmployeeID ON EmployeeAudit(EmployeeID);
CREATE INDEX IX_EmployeeAudit_ChangedAt ON EmployeeAudit(ChangedAt);
CREATE INDEX IX_EmployeeAudit_Action ON EmployeeAudit(Action);
```

### Oracle: Tabela de Auditoria

```sql
-- Oracle: Tabela de auditoria
CREATE TABLE audit.employee_audit (
    audit_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    employee_id NUMBER NOT NULL,
    action VARCHAR2(10) NOT NULL,
    old_data CLOB,  -- JSON
    new_data CLOB,  -- JSON
    changed_by VARCHAR2(100) DEFAULT SYS_CONTEXT('USERENV', 'SESSION_USER'),
    changed_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    client_ip VARCHAR2(50) DEFAULT SYS_CONTEXT('USERENV', 'IP_ADDRESS'),
    session_id NUMBER DEFAULT SYS_CONTEXT('USERENV', 'SESSION_ID')
);

-- Índices
CREATE INDEX idx_emp_audit_empid ON audit.employee_audit(employee_id);
CREATE INDEX idx_emp_audit_date ON audit.employee_audit(changed_at);
```

---

## Change Data Capture (CDC)

### O que é CDC

Change Data Capture é uma técnica que captura e registra todas as mudanças feitas em dados, permitindo rastrear o histórico completo de alterações.

### CDC com Triggers

```sql
-- PostgreSQL: CDC completo com triggers

-- 1. Tabela de origem
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    total_amount DECIMAL(10,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela CDC
CREATE TABLE orders_cdc (
    cdc_id BIGSERIAL PRIMARY KEY,
    operation CHAR(1) NOT NULL,  -- I=INSERT, U=UPDATE, D=DELETE
    order_id INTEGER NOT NULL,
    
    -- Snapshot do estado anterior (NULL para INSERT)
    old_customer_id INTEGER,
    old_total_amount DECIMAL(10,2),
    old_status VARCHAR(20),
    
    -- Snapshot do estado posterior (NULL para DELETE)
    new_customer_id INTEGER,
    new_total_amount DECIMAL(10,2),
    new_status VARCHAR(20),
    
    -- Metadados
    changed_by VARCHAR(100) DEFAULT current_user,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    transaction_id BIGINT DEFAULT txid_current(),
    
    -- Para identificar mudanças específicas
    changed_columns TEXT[]
);

-- 3. Função CDC
CREATE OR REPLACE FUNCTION capture_order_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data RECORD;
    v_new_data RECORD;
    v_changed_cols TEXT[];
BEGIN
    -- Determinar colunas alteradas
    IF TG_OP = 'UPDATE' THEN
        v_changed_cols := ARRAY[]::TEXT[];
        
        IF OLD.customer_id IS DISTINCT FROM NEW.customer_id THEN
            v_changed_cols := array_append(v_changed_cols, 'customer_id');
        END IF;
        
        IF OLD.total_amount IS DISTINCT FROM NEW.total_amount THEN
            v_changed_cols := array_append(v_changed_cols, 'total_amount');
        END IF;
        
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            v_changed_cols := array_append(v_changed_cols, 'status');
        END IF;
        
        -- Se nenhuma colha relevante mudou, não registrar
        IF array_length(v_changed_cols, 1) = 0 THEN
            RETURN NEW;
        END IF;
    END IF;
    
    -- Inserir registro CDC
    INSERT INTO orders_cdc (
        operation,
        order_id,
        old_customer_id, old_total_amount, old_status,
        new_customer_id, new_total_amount, new_status,
        changed_columns
    ) VALUES (
        CASE TG_OP
            WHEN 'INSERT' THEN 'I'
            WHEN 'UPDATE' THEN 'U'
            WHEN 'DELETE' THEN 'D'
        END,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN OLD.customer_id END,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN OLD.total_amount END,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN OLD.status END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN NEW.customer_id END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN NEW.total_amount END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN NEW.status END,
        v_changed_cols
    );
    
    -- Atualizar timestamp de modificação
    IF TG_OP = 'UPDATE' THEN
        NEW.updated_at := CURRENT_TIMESTAMP;
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 4. Criar trigger
CREATE TRIGGER trg_orders_cdc
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION capture_order_changes();

-- 5. Função para consultar mudanças
CREATE OR REPLACE FUNCTION get_order_changes(
    p_order_id INTEGER,
    p_start_date TIMESTAMP DEFAULT NULL,
    p_end_date TIMESTAMP DEFAULT NULL
)
RETURNS TABLE (
    cdc_id BIGINT,
    operation CHAR(1),
    changed_at TIMESTAMP,
    changed_by VARCHAR,
    old_data JSONB,
    new_data JSONB,
    changed_columns TEXT[]
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.cdc_id,
        c.operation,
        c.changed_at,
        c.changed_by,
        jsonb_build_object(
            'customer_id', c.old_customer_id,
            'total_amount', c.old_total_amount,
            'status', c.old_status
        ),
        jsonb_build_object(
            'customer_id', c.new_customer_id,
            'total_amount', c.new_total_amount,
            'status', c.new_status
        ),
        c.changed_columns
    FROM orders_cdc c
    WHERE c.order_id = p_order_id
    AND (p_start_date IS NULL OR c.changed_at >= p_start_date)
    AND (p_end_date IS NULL OR c.changed_at <= p_end_date)
    ORDER BY c.changed_at;
END;
$$;
```

### CDC em SQL Server

```sql
-- SQL Server: CDC habilitado
-- Habilitar CDC no banco
EXEC sys.sp_cdc_enable_db;

-- Habilitar CDC na tabela
EXEC sys.sp_cdc_enable_table
    @source_schema = N'dbo',
    @source_name = N'Orders',
    @role_name = N'cdc_reader',
    @supports_net_changes = 1;

-- Verificar se CDC está habilitado
SELECT name, is_cdc_enabled 
FROM sys.databases 
WHERE name = DB_NAME();

-- Consultar mudanças
DECLARE @from_lsn BINARY(10), @to_lsn BINARY(10);
SET @from_lsn = sys.fn_cdc_get_min_lsn('dbo_Orders');
SET @to_lsn = sys.fn_cdc_get_max_lsn();

SELECT * FROM cdc.fn_cdc_get_all_changes_dbo_Orders(
    @from_lsn, @to_lsn, 'all'
);

-- CDC com triggers para controle adicional
CREATE TRIGGER trg_orders_cdc_extended
ON Orders
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Dados adicionais que CDC padrão não captura
    DECLARE @AppName NVARCHAR(128) = APP_NAME();
    DECLARE @HostName NVARCHAR(128) = HOST_NAME();
    
    -- Registrar contexto adicional
    INSERT INTO ExtendedCDCLog (
        Table_name,
        Operation,
        AppName,
        HostName,
        ChangedAt
    ) VALUES (
        'Orders',
        CASE 
            WHEN EXISTS(SELECT 1 FROM inserted) AND EXISTS(SELECT 1 FROM deleted) THEN 'UPDATE'
            WHEN EXISTS(SELECT 1 FROM inserted) THEN 'INSERT'
            ELSE 'DELETE'
        END,
        @AppName,
        @HostName,
        GETDATE()
    );
END;
GO
```

---

## Temporal Tables

### O que são Temporal Tables

Temporal tables (tabelas temporais) são tabelas que mantêm histórico completo de todas as mudanças, permitindo consultas no tempo (time-travel queries).

### SQL Server: System-Versioned Temporal Tables

```sql
-- SQL Server: Criar tabela temporal
CREATE TABLE EmployeesTemporal (
    EmployeeID INT PRIMARY KEY,
    FirstName NVARCHAR(50),
    LastName NVARCHAR(50),
    Email NVARCHAR(100),
    Salary DECIMAL(18,2),
    DepartmentID INT,
    ValidFrom DATETIME2 GENERATED ALWAYS AS ROW START,
    ValidTo DATETIME2 GENERATED ALWAYS AS ROW END,
    PERIOD FOR SYSTEM_TIME (ValidFrom, ValidTo)
)
WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = dbo.EmployeesTemporalHistory));

-- Inserir dados
INSERT INTO EmployeesTemporal (EmployeeID, FirstName, LastName, Email, Salary, DepartmentID)
VALUES (1, 'John', 'Doe', 'john.doe@company.com', 75000, 1);

-- Atualizar dados
UPDATE EmployeesTemporal
SET Salary = 80000, DepartmentID = 2
WHERE EmployeeID = 1;

-- Consultar estado atual
SELECT * FROM EmployeesTemporal;

-- Consultar histórico
SELECT * FROM EmployeesTemporalHistory;

-- Consultar estado em momento específico
SELECT * FROM EmployeesTemporal
FOR SYSTEM_TIME AS OF '2024-01-15 10:00:00';

-- Consultarintervalo de tempo
SELECT * FROM EmployeesTemporal
FOR SYSTEM_TIME BETWEEN '2024-01-01' AND '2024-12-31';

-- Consultar todas as versões de um registro
SELECT * FROM EmployeesTemporal
FOR SYSTEM_TIME ALL
WHERE EmployeeID = 1;
```

### PostgreSQL: Temporal Tables com Triggers

```sql
-- PostgreSQL: Implementação de temporal tables

-- 1. Tabela principal
CREATE TABLE employees_temporal (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    salary DECIMAL(10,2),
    department_id INTEGER,
    
    -- Colunas temporais
    valid_from TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP DEFAULT '9999-12-31 23:59:59',
    
    -- Para versionamento
    version INTEGER DEFAULT 1
);

-- 2. Função para gerenciar versionamento
CREATE OR REPLACE FUNCTION manage_employee_versioning()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Primeira versão
        NEW.version := 1;
        NEW.valid_from := CURRENT_TIMESTAMP;
        NEW.valid_to := '9999-12-31 23:59:59';
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Fechar versão anterior
        UPDATE employees_temporal
        SET valid_to = CURRENT_TIMESTAMP
        WHERE employee_id = OLD.employee_id
        AND valid_to = '9999-12-31 23:59:59';
        
        -- Criar nova versão
        NEW.version := OLD.version + 1;
        NEW.valid_from := CURRENT_TIMESTAMP;
        NEW.valid_to := '9999-12-31 23:59:59';
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        -- Fechar versão atual
        UPDATE employees_temporal
        SET valid_to = CURRENT_TIMESTAMP
        WHERE employee_id = OLD.employee_id
        AND valid_to = '9999-12-31 23:59:59';
        
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 3. Criar trigger
CREATE TRIGGER trg_employee_versioning
BEFORE INSERT OR UPDATE OR DELETE ON employees_temporal
FOR EACH ROW EXECUTE FUNCTION manage_employee_versioning();

-- 4. Consultar estado em momento específico
CREATE OR REPLACE FUNCTION get_employee_as_of(
    p_employee_id INTEGER,
    p_as_of TIMESTAMP
)
RETURNS TABLE (
    employee_id INTEGER,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    salary DECIMAL,
    department_id INTEGER,
    version INTEGER,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.employee_id,
        e.first_name,
        e.last_name,
        e.email,
        e.salary,
        e.department_id,
        e.version,
        e.valid_from,
        e.valid_to
    FROM employees_temporal e
    WHERE e.employee_id = p_employee_id
    AND e.valid_from <= p_as_of
    AND e.valid_to > p_as_of;
END;
$$;

-- 5. Consultar histórico completo
CREATE OR REPLACE FUNCTION get_employee_history(
    p_employee_id INTEGER
)
RETURNS TABLE (
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    salary DECIMAL,
    department_id INTEGER,
    version INTEGER,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    duration INTERVAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.first_name,
        e.last_name,
        e.email,
        e.salary,
        e.department_id,
        e.version,
        e.valid_from,
        e.valid_to,
        e.valid_to - e.valid_from AS duration
    FROM employees_temporal e
    WHERE e.employee_id = p_employee_id
    ORDER BY e.valid_from;
END;
$$;

-- 6. Consultar mudanças em período
CREATE OR REPLACE FUNCTION get_changes_in_period(
    p_start TIMESTAMP,
    p_end TIMESTAMP
)
RETURNS TABLE (
    employee_id INTEGER,
    first_name VARCHAR,
    last_name VARCHAR,
    salary DECIMAL,
    department_id INTEGER,
    change_type VARCHAR,
    changed_at TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.employee_id,
        e.first_name,
        e.last_name,
        e.salary,
        e.department_id,
        CASE 
            WHEN e.valid_from = (SELECT MIN(valid_from) FROM employees_temporal WHERE employee_id = e.employee_id)
            THEN 'CREATED'
            WHEN e.valid_to < '9999-12-31 23:59:59'
            THEN 'DELETED'
            ELSE 'UPDATED'
        END AS change_type,
        e.valid_from AS changed_at
    FROM employees_temporal e
    WHERE e.valid_from BETWEEN p_start AND p_end
    OR (e.valid_to BETWEEN p_start AND p_end AND e.valid_to < '9999-12-31 23:59:59');
END;
$$;
```

---

## Soft Deletes

### O que são Soft Deletes

Soft deletes marcam registros como deletados sem removê-los fisicamente. Permite recuperação de dados, auditoria e manutenção de integridade referencial.

### Implementação Básica

```sql
-- PostgreSQL: Soft delete básico
ALTER TABLE employees ADD COLUMN deleted_at TIMESTAMP NULL;
ALTER TABLE employees ADD COLUMN deleted_by VARCHAR(100) NULL;

-- Função de soft delete
CREATE OR REPLACE FUNCTION soft_delete_employee(p_employee_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE employees
    SET deleted_at = CURRENT_TIMESTAMP,
        deleted_by = current_user
    WHERE employee_id = p_employee_id
    AND deleted_at IS NULL;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee not found or already deleted';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Função de restore
CREATE OR REPLACE FUNCTION restore_employee(p_employee_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE employees
    SET deleted_at = NULL,
        deleted_by = NULL
    WHERE employee_id = p_employee_id
    AND deleted_at IS NOT NULL;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Employee not found or not deleted';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Função de purge (delete físico)
CREATE OR REPLACE FUNCTION purge_deleted_employees(
    p_older_than INTERVAL DEFAULT '90 days'
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    DELETE FROM employees
    WHERE deleted_at IS NOT NULL
    AND deleted_at < CURRENT_TIMESTAMP - p_older_than;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### Views para Filtrar Deletados

```sql
-- View que exclui registros deletados
CREATE VIEW active_employees AS
SELECT *
FROM employees
WHERE deleted_at IS NULL;

-- View que inclui apenas deletados
CREATE VIEW deleted_employees AS
SELECT *
FROM employees
WHERE deleted_at IS NOT NULL;

-- View com informações de delete
CREATE VIEW employee_status AS
SELECT 
    employee_id,
    first_name,
    last_name,
    email,
    CASE 
        WHEN deleted_at IS NULL THEN 'ACTIVE'
        ELSE 'DELETED'
    END AS status,
    deleted_at,
    deleted_by,
    CASE 
        WHEN deleted_at IS NULL THEN NULL
        ELSE CURRENT_TIMESTAMP - deleted_at
    END AS deleted_duration
FROM employees;

-- Índices para performance
CREATE INDEX idx_employees_active ON employees(employee_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_deleted ON employees(deleted_at) WHERE deleted_at IS NOT NULL;
```

### Triggers para Soft Delete

```sql
-- Trigger para impedir DELETE físico (forçar soft delete)
CREATE OR REPLACE FUNCTION prevent_hard_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Hard delete not allowed. Use soft delete instead.';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_hard_delete
BEFORE DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION prevent_hard_delete();

-- Trigger para registrar soft delete
CREATE OR REPLACE FUNCTION log_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
        INSERT INTO audit_log (
            table_name, record_id, action,
            old_data, new_data, changed_by
        ) VALUES (
            'employees',
            NEW.employee_id,
            'SOFT_DELETE',
            to_jsonb(OLD),
            to_jsonb(NEW),
            current_user
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_soft_delete
AFTER UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION log_soft_delete();

-- Trigger para restaurar
CREATE OR REPLACE FUNCTION log_restore()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
        INSERT INTO audit_log (
            table_name, record_id, action,
            old_data, new_data, changed_by
        ) VALUES (
            'employees',
            NEW.employee_id,
            'RESTORE',
            to_jsonb(OLD),
            to_jsonb(NEW),
            current_user
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_restore
AFTER UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION log_restore();
```

### SQL Server: Soft Delete

```sql
-- SQL Server: Soft delete
ALTER TABLE Employees ADD DeletedAt DATETIME2 NULL;
ALTER TABLE Employees ADD DeletedBy NVARCHAR(100) NULL;

-- Função de soft delete
CREATE PROCEDURE dbo.SoftDeleteEmployee
    @EmployeeID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE Employees
    SET DeletedAt = SYSDATETIME(),
        DeletedBy = SYSTEM_USER
    WHERE EmployeeID = @EmployeeID
    AND DeletedAt IS NULL;
    
    IF @@ROWCOUNT = 0
        RAISERROR('Employee not found or already deleted', 16, 1);
END;
GO

-- View ativa
CREATE VIEW vw_ActiveEmployees
AS
SELECT *
FROM Employees
WHERE DeletedAt IS NULL;
GO

-- Índice filtrado
CREATE UNIQUE INDEX IX_Employees_Active 
ON Employees(EmployeeID) 
WHERE DeletedAt IS NULL;
GO
```

---

## Logging Patterns

### Padrões de Logging em Banco de Dados

**1. Audit Log (Mais completo)**

```sql
-- Tabela de audit log detalhado
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100),
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    client_ip INET,
    application_name VARCHAR(100),
    change_reason TEXT
);

-- Trigger genérico de auditoria
CREATE OR REPLACE FUNCTION generic_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name, record_id, action,
        old_values, new_values,
        changed_by, changed_at
    ) VALUES (
        TG_TABLE_NAME,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id::TEXT
            ELSE NEW.id::TEXT
        END,
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Aplicar a múltiplas tabelas
CREATE TRIGGER trg_audit_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION generic_audit_trigger();

CREATE TRIGGER trg_audit_orders
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION generic_audit_trigger();

CREATE TRIGGER trg_audit_products
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW EXECUTE FUNCTION generic_audit_trigger();
```

**2. Activity Log (Mais leve)**

```sql
-- Tabela de activity log (apenas metadados)
CREATE TABLE activity_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    action VARCHAR(20) NOT NULL,
    rows_affected INTEGER DEFAULT 1,
    performed_by VARCHAR(100) NOT NULL,
    performed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER
);

-- Trigger statement-level
CREATE OR REPLACE FUNCTION log_activity()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO activity_log (
        table_name, action, rows_affected, performed_by
    ) VALUES (
        TG_TABLE_NAME, TG_OP, 1, current_user
    );
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_activity
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH STATEMENT EXECUTE FUNCTION log_activity();
```

**3. Change Data Log (Focused)**

```sql
-- Tabela de change log (focado em mudanças específicas)
CREATE TABLE change_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para mudanças específicas
CREATE OR REPLACE FUNCTION log_specific_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Log apenas mudanças em colunas sensíveis
    IF OLD.salary IS DISTINCT FROM NEW.salary THEN
        INSERT INTO change_log (table_name, record_id, column_name, old_value, new_value, changed_by)
        VALUES ('employees', NEW.employee_id::TEXT, 'salary', OLD.salary::TEXT, NEW.salary::TEXT, current_user);
    END IF;
    
    IF OLD.department_id IS DISTINCT FROM NEW.department_id THEN
        INSERT INTO change_log (table_name, record_id, column_name, old_value, new_value, changed_by)
        VALUES ('employees', NEW.employee_id::TEXT, 'department_id', OLD.department_id::TEXT, NEW.department_id::TEXT, current_user);
    END IF;
    
    IF OLD.email IS DISTINCT FROM NEW.email THEN
        INSERT INTO change_log (table_name, record_id, column_name, old_value, new_value, changed_by)
        VALUES ('employees', NEW.employee_id::TEXT, 'email', OLD.email, NEW.email, current_user);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_sensitive_changes
AFTER UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION log_specific_changes();
```

---

## Compliance Logging

### Requisitos de Conformidade

Diferentes frameworks de conformidade exigem diferentes níveis de auditoria:

**PCI DSS:**
- Log de todas as alterações em dados de cartão de crédito
- Retenção mínima de 1 ano
- Logs não podem ser alterados ou excluídos

**HIPAA:**
- Log de acesso a dados de saúde
- Rastreamento de quem acessou o quê e quando
- Logs por 6 anos

**GDPR:**
- Log de processamento de dados pessoais
- Registro de consentimento
- Direito ao esquecimento (com preservação de logs)

**SOX:**
- Log de alterações em dados financeiros
- Controle de acesso segregado
- Logs por 7 anos

### Implementação de Compliance Logging

```sql
-- Tabela de compliance log
CREATE TABLE compliance_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    
    -- Dados
    subject_type VARCHAR(50),
    subject_id VARCHAR(100),
    subject_data JSONB,
    
    -- Ação
    action VARCHAR(50) NOT NULL,
    action_result VARCHAR(20) NOT NULL,
    
    -- Contexto
    performed_by VARCHAR(100) NOT NULL,
    performed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Compliance
    regulation VARCHAR(50),
    retention_days INTEGER,
    retention_until DATE,
    
    -- Integridade
    checksum VARCHAR(64) NOT NULL,
    previous_checksum VARCHAR(64)
);

-- Índices
CREATE INDEX idx_compliance_event ON compliance_log(event_type);
CREATE INDEX idx_compliance_subject ON compliance_log(subject_type, subject_id);
CREATE INDEX idx_compliance_date ON compliance_log(performed_at);
CREATE INDEX idx_compliance_regulation ON compliance_log(regulation);

-- Função para calcular checksum
CREATE OR REPLACE FUNCTION calculate_compliance_checksum(
    p_event_type VARCHAR,
    p_subject_id VARCHAR,
    p_action VARCHAR,
    p_performed_by VARCHAR,
    p_performed_at TIMESTAMP
)
RETURNS VARCHAR AS $$
BEGIN
    RETURN encode(
        digest(
            p_event_type || p_subject_id || p_action || 
            p_performed_by || p_performed_at::TEXT,
            'sha256'
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql;

-- Trigger de compliance logging
CREATE OR REPLACE FUNCTION compliance_audit_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_checksum VARCHAR(64);
    v_previous_checksum VARCHAR(64);
BEGIN
    -- Calcular checksum
    v_checksum := calculate_compliance_checksum(
        TG_OP,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id::TEXT
            ELSE NEW.id::TEXT
        END,
        TG_OP,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    -- Obter checksum anterior
    SELECT checksum INTO v_previous_checksum
    FROM compliance_log
    WHERE subject_type = TG_TABLE_NAME
    AND subject_id = CASE 
        WHEN TG_OP = 'DELETE' THEN OLD.id::TEXT
        ELSE NEW.id::TEXT
    END
    ORDER BY performed_at DESC
    LIMIT 1;
    
    -- Inserir log
    INSERT INTO compliance_log (
        event_type, event_category,
        subject_type, subject_id, subject_data,
        action, action_result,
        performed_by, performed_at,
        regulation, retention_days, retention_until,
        checksum, previous_checksum
    ) VALUES (
        TG_TABLE_NAME || '_' || TG_OP,
        'DATA_MODIFICATION',
        TG_TABLE_NAME,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id::TEXT
            ELSE NEW.id::TEXT
        END,
        CASE 
            WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE to_jsonb(NEW)
        END,
        TG_OP,
        'SUCCESS',
        current_user,
        CURRENT_TIMESTAMP,
        'GENERAL',
        365 * 7,  -- 7 anos de retenção
        CURRENT_TIMESTAMP + INTERVAL '7 years',
        v_checksum,
        v_previous_checksum
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

### Verificação de Integridade dos Logs

```sql
-- Função para verificar integridade da cadeia de logs
CREATE OR REPLACE FUNCTION verify_log_integrity(
    p_subject_type VARCHAR,
    p_subject_id VARCHAR
)
RETURNS TABLE (
    is_valid BOOLEAN,
    broken_at TIMESTAMP,
    expected_checksum VARCHAR,
    actual_checksum VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_prev_checksum VARCHAR(64);
    v_current RECORD;
BEGIN
    v_prev_checksum := NULL;
    
    FOR v_current IN 
        SELECT * FROM compliance_log
        WHERE subject_type = p_subject_type
        AND subject_id = p_subject_id
        ORDER BY performed_at
    LOOP
        -- Verificar se checksum anterior confere
        IF v_prev_checksum IS NOT NULL AND 
           v_current.previous_checksum != v_prev_checksum THEN
            RETURN QUERY SELECT 
                FALSE,
                v_current.performed_at,
                v_prev_checksum,
                v_current.previous_checksum;
            RETURN;
        END IF;
        
        v_prev_checksum := v_current.checksum;
    END LOOP;
    
    -- Se chegou aqui, tudo está íntegro
    RETURN QUERY SELECT 
        TRUE,
        NULL::TIMESTAMP,
        NULL::VARCHAR(64),
        NULL::VARCHAR(64);
END;
$$;

-- Relatório de conformidade
CREATE OR REPLACE FUNCTION generate_compliance_report(
    p_regulation VARCHAR,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    event_type VARCHAR,
    event_count BIGINT,
    unique_subjects BIGINT,
    first_event TIMESTAMP,
    last_event TIMESTAMP
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cl.event_type,
        COUNT(*) AS event_count,
        COUNT(DISTINCT cl.subject_id) AS unique_subjects,
        MIN(cl.performed_at) AS first_event,
        MAX(cl.performed_at) AS last_event
    FROM compliance_log cl
    WHERE cl.regulation = p_regulation
    AND cl.performed_at::DATE BETWEEN p_start_date AND p_end_date
    GROUP BY cl.event_type
    ORDER BY COUNT(*) DESC;
END;
$$;
```

---

## Exemplo: Audit Completo em PostgreSQL

### Setup do Sistema de Auditoria

```sql
-- 1. Criar schema de auditoria
CREATE SCHEMA IF NOT EXISTS audit;

-- 2. Tabela principal de auditoria
CREATE TABLE audit.audit_trail (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação do evento
    event_id UUID DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    
    -- Informações da tabela
    table_schema VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    
    -- Identificador do registro
    record_id VARCHAR(100),
    
    -- Dados
    old_data JSONB,
    new_data JSONB,
    changed_columns TEXT[],
    
    -- Metadados
    performed_by VARCHAR(100) NOT NULL DEFAULT current_user,
    performed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Contexto da sessão
    session_id VARCHAR(100),
    client_ip INET,
    application_name VARCHAR(100),
    client_info JSONB,
    
    -- Para compliance
    regulation VARCHAR(50),
    retention_until DATE,
    
    -- Integridade
    checksum VARCHAR(64) NOT NULL,
    previous_event_id UUID
);

-- 3. Índices
CREATE INDEX idx_audit_trail_event ON audit.audit_trail(event_type);
CREATE INDEX idx_audit_trail_table ON audit.audit_trail(table_name);
CREATE INDEX idx_audit_trail_record ON audit.audit_trail(record_id);
CREATE INDEX idx_audit_trail_performed ON audit.audit_trail(performed_at);
CREATE INDEX idx_audit_trail_performed_by ON audit.audit_trail(performed_by);
CREATE INDEX idx_audit_trail_composite ON audit.audit_trail(table_name, record_id, performed_at);

-- 4. Particionamento por data
CREATE TABLE audit.audit_trail (
    id BIGSERIAL,
    event_id UUID DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    table_schema VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    record_id VARCHAR(100),
    old_data JSONB,
    new_data JSONB,
    changed_columns TEXT[],
    performed_by VARCHAR(100) NOT NULL,
    performed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    session_id VARCHAR(100),
    client_ip INET,
    application_name VARCHAR(100),
    client_info JSONB,
    regulation VARCHAR(50),
    retention_until DATE,
    checksum VARCHAR(64) NOT NULL,
    previous_event_id UUID,
    PRIMARY KEY (id, performed_at)
) PARTITION BY RANGE (created_at);

-- Criar partições mensais automaticamente
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS TRIGGER AS $$
DECLARE
    v_partition_name TEXT;
    v_start_date DATE;
    v_end_date DATE;
BEGIN
    v_start_date := date_trunc('month', NEW.performed_at);
    v_end_date := v_start_date + INTERVAL '1 month';
    v_partition_name := 'audit_trail_' || to_char(v_start_date, 'YYYY_MM');
    
    -- Criar partição se não existir
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = v_partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF audit.audit_trail FOR VALUES FROM (%L) TO (%L)',
            v_partition_name,
            v_start_date,
            v_end_date
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Funções de Auditoria

```sql
-- 1. Função para calcular checksum
CREATE OR REPLACE FUNCTION audit.calculate_checksum(
    p_event_type VARCHAR,
    p_table_name VARCHAR,
    p_record_id VARCHAR,
    p_operation VARCHAR,
    p_performed_by VARCHAR,
    p_performed_at TIMESTAMP WITH TIME ZONE
)
RETURNS VARCHAR AS $$
BEGIN
    RETURN encode(
        digest(
            p_event_type || p_table_name || p_record_id || 
            p_operation || p_performed_by || p_performed_at::TEXT,
            'sha256'
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Função para obter último event_id
CREATE OR REPLACE FUNCTION audit.get_previous_event_id(
    p_table_name VARCHAR,
    p_record_id VARCHAR
)
RETURNS UUID AS $$
DECLARE
    v_previous_id UUID;
BEGIN
    SELECT event_id INTO v_previous_id
    FROM audit.audit_trail
    WHERE table_name = p_table_name
    AND record_id = p_record_id
    ORDER BY performed_at DESC
    LIMIT 1;
    
    RETURN v_previous_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Função principal de auditoria
CREATE OR REPLACE FUNCTION audit.log_change()
RETURNS TRIGGER AS $$
DECLARE
    v_event_id UUID;
    v_old_data JSONB;
    v_new_data JSONB;
    v_changed_columns TEXT[];
    v_previous_event_id UUID;
    v_checksum VARCHAR(64);
    v_record_id VARCHAR(100);
BEGIN
    -- Gerar event_id
    v_event_id := uuid_generate_v4();
    
    -- Determinar record_id
    IF TG_OP = 'DELETE' THEN
        v_record_id := OLD.id::TEXT;
    ELSE
        v_record_id := NEW.id::TEXT;
    END IF;
    
    -- Determinar dados baseado na operação
    IF TG_OP = 'INSERT' THEN
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        v_changed_columns := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        
        -- Determinar colunas alteradas
        SELECT array_agg(key) INTO v_changed_columns
        FROM jsonb_each(v_new_data)
        WHERE NOT v_old_data ? key
        OR v_old_data->key IS DISTINCT FROM v_new_data->key;
        
        -- Se nenhuma colha relevante mudou, não registrar
        IF v_changed_columns IS NULL OR array_length(v_changed_columns, 1) = 0 THEN
            RETURN NEW;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        v_changed_columns := NULL;
    END IF;
    
    -- Obter event_id anterior
    v_previous_event_id := audit.get_previous_event_id(TG_TABLE_NAME, v_record_id);
    
    -- Calcular checksum
    v_checksum := audit.calculate_checksum(
        TG_OP,
        TG_TABLE_NAME,
        v_record_id,
        TG_OP,
        current_user,
        CURRENT_TIMESTAMP
    );
    
    -- Inserir registro de auditoria
    INSERT INTO audit.audit_trail (
        event_id,
        event_type,
        event_category,
        table_schema,
        table_name,
        operation,
        record_id,
        old_data,
        new_data,
        changed_columns,
        performed_by,
        performed_at,
        session_id,
        client_ip,
        application_name,
        checksum,
        previous_event_id
    ) VALUES (
        v_event_id,
        TG_TABLE_NAME || '_' || TG_OP,
        'DATA_MODIFICATION',
        TG_TABLE_SCHEMA,
        TG_TABLE_NAME,
        TG_OP,
        v_record_id,
        v_old_data,
        v_new_data,
        v_changed_columns,
        current_user,
        CURRENT_TIMESTAMP,
        pg_backend_pid()::TEXT,
        inet_client_addr(),
        current_setting('application_name'),
        v_checksum,
        v_previous_event_id
    );
    
    -- Retornar dados apropriados
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Aplicar trigger de auditoria a tabelas
CREATE TRIGGER trg_audit_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER trg_audit_orders
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION audit.log_change();

CREATE TRIGGER trg_audit_products
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW EXECUTE FUNCTION audit.log_change();
```

### Funções de Consulta de Auditoria

```sql
-- 1. Consultar histórico de um registro
CREATE OR REPLACE FUNCTION audit.get_record_history(
    p_table_name VARCHAR,
    p_record_id VARCHAR
)
RETURNS TABLE (
    event_id UUID,
    operation VARCHAR,
    old_data JSONB,
    new_data JSONB,
    changed_columns TEXT[],
    performed_by VARCHAR,
    performed_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        at.event_id,
        at.operation,
        at.old_data,
        at.new_data,
        at.changed_columns,
        at.performed_by,
        at.performed_at
    FROM audit.audit_trail at
    WHERE at.table_name = p_table_name
    AND at.record_id = p_record_id
    ORDER BY at.performed_at;
END;
$$;

-- 2. Consultar estado em momento específico
CREATE OR REPLACE FUNCTION audit.get_record_as_of(
    p_table_name VARCHAR,
    p_record_id VARCHAR,
    p_as_of TIMESTAMP WITH TIME ZONE
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
BEGIN
    -- Reconstruir estado a partir dos logs
    SELECT new_data INTO v_result
    FROM audit.audit_trail
    WHERE table_name = p_table_name
    AND record_id = p_record_id
    AND performed_at <= p_as_of
    ORDER BY performed_at DESC
    LIMIT 1;
    
    RETURN v_result;
END;
$$;

-- 3. Comparar versões
CREATE OR REPLACE FUNCTION audit.compare_versions(
    p_table_name VARCHAR,
    p_record_id VARCHAR,
    p_version1 TIMESTAMP WITH TIME ZONE,
    p_version2 TIMESTAMP WITH TIME ZONE
)
RETURNS TABLE (
    column_name VARCHAR,
    old_value JSONB,
    new_value JSONB,
    is_changed BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_data1 JSONB;
    v_data2 JSONB;
    v_key TEXT;
BEGIN
    -- Obter dados das duas versões
    v_data1 := audit.get_record_as_of(p_table_name, p_record_id, p_version1);
    v_data2 := audit.get_record_as_of(p_table_name, p_record_id, p_version2);
    
    -- Comparar colunas
    FOR v_key IN SELECT jsonb_object_keys(v_data2)
    LOOP
        column_name := v_key;
        old_value := v_data1->v_key;
        new_value := v_data2->v_key;
        is_changed := v_data1->v_key IS DISTINCT FROM v_data2->v_key;
        
        RETURN NEXT;
    END LOOP;
END;
$$;

-- 4. Relatório de atividade
CREATE OR REPLACE FUNCTION audit.activity_report(
    p_start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    p_end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS TABLE (
    table_name VARCHAR,
    operation VARCHAR,
    event_count BIGINT,
    unique_users BIGINT,
    first_event TIMESTAMP WITH TIME ZONE,
    last_event TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        at.table_name,
        at.operation,
        COUNT(*) AS event_count,
        COUNT(DISTINCT at.performed_by) AS unique_users,
        MIN(at.performed_at) AS first_event,
        MAX(at.performed_at) AS last_event
    FROM audit.audit_trail at
    WHERE (p_start_date IS NULL OR at.performed_at >= p_start_date)
    AND (p_end_date IS NULL OR at.performed_at <= p_end_date)
    GROUP BY at.table_name, at.operation
    ORDER BY COUNT(*) DESC;
END;
$$;

-- 5. Verificar integridade da cadeia
CREATE OR REPLACE FUNCTION audit.verify_integrity(
    p_table_name VARCHAR,
    p_record_id VARCHAR
)
RETURNS TABLE (
    is_valid BOOLEAN,
    broken_at TIMESTAMP WITH TIME ZONE,
    expected_previous_event_id UUID,
    actual_previous_event_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_prev_event_id UUID;
    v_current RECORD;
BEGIN
    v_prev_event_id := NULL;
    
    FOR v_current IN 
        SELECT * FROM audit.audit_trail
        WHERE table_name = p_table_name
        AND record_id = p_record_id
        ORDER BY performed_at
    LOOP
        IF v_prev_event_id IS NOT NULL AND 
           v_current.previous_event_id != v_prev_event_id THEN
            RETURN QUERY SELECT 
                FALSE,
                v_current.performed_at,
                v_prev_event_id,
                v_current.previous_event_id;
            RETURN;
        END IF;
        
        v_prev_event_id := v_current.event_id;
    END LOOP;
    
    RETURN QUERY SELECT 
        TRUE,
        NULL::TIMESTAMP WITH TIME ZONE,
        NULL::UUID,
        NULL::UUID;
END;
$$;
```

---

## Exemplo: CDC com Triggers

### CDC Completo com PostgreSQL

```sql
-- 1. Tabela de CDC
CREATE TABLE cdc.change_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    change_id UUID DEFAULT uuid_generate_v4(),
    source_table VARCHAR(100) NOT NULL,
    
    -- Operação
    operation VARCHAR(10) NOT NULL,
    
    -- Dados
    key_column VARCHAR(50) NOT NULL,
    key_value VARCHAR(100) NOT NULL,
    
    -- Snapshot completo
    before_image JSONB,
    after_image JSONB,
    
    -- Metadados
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Para processamento assíncrono
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    processed_by VARCHAR(100),
    
    -- Integridade
    checksum VARCHAR(64) NOT NULL
);

-- 2. Índices
CREATE INDEX idx_cdc_source ON cdc.change_log(source_table);
CREATE INDEX idx_cdc_operation ON cdc.change_log(operation);
CREATE INDEX idx_cdc_key ON cdc.change_log(key_column, key_value);
CREATE INDEX idx_cdc_processed ON cdc.change_log(processed) WHERE processed = FALSE;
CREATE INDEX idx_cdc_changed_at ON cdc.change_log(changed_at);

-- 3. Função genérica de CDC
CREATE OR REPLACE FUNCTION cdc.capture_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_key_column VARCHAR(50);
    v_key_value VARCHAR(100);
    v_before_image JSONB;
    v_after_image JSONB;
    v_checksum VARCHAR(64);
BEGIN
    -- Determinar coluna chave (assumindo 'id' como padrão)
    v_key_column := 'id';
    
    -- Determinar valores baseado na operação
    IF TG_OP = 'INSERT' THEN
        v_key_value := NEW.id::TEXT;
        v_before_image := NULL;
        v_after_image := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_key_value := NEW.id::TEXT;
        v_before_image := to_jsonb(OLD);
        v_after_image := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        v_key_value := OLD.id::TEXT;
        v_before_image := to_jsonb(OLD);
        v_after_image := NULL;
    END IF;
    
    -- Calcular checksum
    v_checksum := encode(
        digest(
            TG_TABLE_NAME || TG_OP || v_key_value || 
            COALESCE(v_before_image::TEXT, '') || 
            COALESCE(v_after_image::TEXT, ''),
            'sha256'
        ),
        'hex'
    );
    
    -- Inserir no log CDC
    INSERT INTO cdc.change_log (
        source_table,
        operation,
        key_column,
        key_value,
        before_image,
        after_image,
        changed_by,
        checksum
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        v_key_column,
        v_key_value,
        v_before_image,
        v_after_image,
        current_user,
        v_checksum
    );
    
    -- Retornar dados apropriados
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Aplicar triggers CDC a tabelas
CREATE TRIGGER trg_cdc_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW EXECUTE FUNCTION cdc.capture_changes();

CREATE TRIGGER trg_cdc_orders
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION cdc.capture_changes();

CREATE TRIGGER trg_cdc_products
AFTER INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION cdc.capture_changes();

-- 5. Função para processar mudanças
CREATE OR REPLACE FUNCTION cdc.process_changes(
    p_batch_size INTEGER DEFAULT 100
)
RETURNS TABLE (
    change_id UUID,
    source_table VARCHAR,
    operation VARCHAR,
    key_value VARCHAR,
    processed_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_change RECORD;
    v_processed_count INTEGER := 0;
BEGIN
    FOR v_change IN 
        SELECT * FROM cdc.change_log
        WHERE processed = FALSE
        ORDER BY changed_at
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    LOOP
        -- Processar mudança (lógica específica por tabela)
        IF v_change.source_table = 'employees' THEN
            -- Exemplo: sincronizar com sistema externo
            PERFORM cdc.sync_employee_external(v_change);
        ELSIF v_change.source_table = 'orders' THEN
            -- Exemplo: notificar sistema de fulfillment
            PERFORM cdc.notify_order_fulfillment(v_change);
        END IF;
        
        -- Marcar como processado
        UPDATE cdc.change_log
        SET processed = TRUE,
            processed_at = CURRENT_TIMESTAMP,
            processed_by = current_user
        WHERE id = v_change.id;
        
        -- Retornar resultado
        change_id := v_change.change_id;
        source_table := v_change.source_table;
        operation := v_change.operation;
        key_value := v_change.key_value;
        processed_at := CURRENT_TIMESTAMP;
        RETURN NEXT;
        
        v_processed_count := v_processed_count + 1;
    END LOOP;
    
    RAISE NOTICE 'Processed % changes', v_processed_count;
END;
$$;

-- 6. Funções de sincronização (exemplos)
CREATE OR REPLACE FUNCTION cdc.sync_employee_external(p_change cdc.change_log)
RETURNS VOID AS $$
BEGIN
    -- Lógica de sincronização com sistema externo
    -- Por exemplo: chamar API, enviar mensagem, etc.
    RAISE NOTICE 'Syncing employee % to external system', p_change.key_value;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cdc.notify_order_fulfillment(p_change cdc.change_log)
RETURNS VOID AS $$
BEGIN
    -- Lógica de notificação
    RAISE NOTICE 'Notifying fulfillment for order %', p_change.key_value;
END;
$$ LANGUAGE plpgsql;

-- 7. View para monitoramento
CREATE VIEW cdc.change_log_summary AS
SELECT 
    source_table,
    operation,
    COUNT(*) AS total_changes,
    COUNT(CASE WHEN processed THEN 1 END) AS processed,
    COUNT(CASE WHEN NOT processed THEN 1 END) AS pending,
    MIN(changed_at) AS oldest_change,
    MAX(changed_at) AS newest_change
FROM cdc.change_log
GROUP BY source_table, operation;
```

---

## Performance Impact

### Impacto de Triggers na Performance

Triggers adicionam overhead a cada operação DML. O impacto depende de:

1. **Complexidade da lógica do trigger** — triggers complexos são mais lentos
2. **Número de triggers por tabela** — múltiplos triggers acumulam overhead
3. **Granularidade** — row-level triggers são mais lentos que statement-level
4. **Operações de I/O** — inserções em tabelas de auditoria consomem I/O
5. **Locks** — triggers podem causar locks adicionais

### Medição de Impacto

```sql
-- PostgreSQL: Medir tempo de triggers
CREATE OR REPLACE FUNCTION measure_trigger_impact()
RETURNS TABLE (
    table_name VARCHAR,
    operation VARCHAR,
    avg_duration_ms NUMERIC,
    total_operations BIGINT,
    total_duration INTERVAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        at.table_name,
        at.operation,
        AVG(EXTRACT(EPOCH FROM (at.performed_at - at.performed_at)) * 1000),
        COUNT(*),
        SUM(at.performed_at - at.performed_at)
    FROM audit.audit_trail at
    WHERE at.performed_at > CURRENT_TIMESTAMP - INTERVAL '1 day'
    GROUP BY at.table_name, at.operation;
END;
$$;

-- SQL Server: Medir impacto com DMVs
SELECT 
    OBJECT_NAME(object_id) AS TableName,
    trigger_name,
    is_disabled,
    is_instead_of_trigger,
    SUM(execution_count) AS TotalExecutions,
    SUM(total_elapsed_time) / 1000 AS TotalTimeMs,
    AVG(total_elapsed_time) / 1000 AS AvgTimeMs
FROM sys.dm_exec_trigger_stats
GROUP BY object_id, trigger_name, is_disabled, is_instead_of_trigger
ORDER BY TotalTimeMs DESC;
```

### Otimização de Performance

```sql
-- 1. Usar statement-level triggers quando possível
-- Em vez de row-level para cada linha
-- INSERT INTO millions_table VALUES (...); -- 1 trigger statement vs 1M row triggers

-- 2. Minimizar I/O em triggers
-- Usar variáveis para acumular dados e inserir em lote
CREATE OR REPLACE FUNCTION optimized_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Inserir diretamente sem operações complexas
    INSERT INTO audit_log (table_name, record_id, operation, data)
    VALUES (TG_TABLE_NAME, NEW.id, TG_OP, to_jsonb(NEW));
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Usar UNLOGGED tables para auditoria temporária
CREATE UNLOGGED TABLE audit_temp (
    -- Estrutura similar ao audit_log
);

-- 4. Particionar tabelas de auditoria
-- Já demonstrado anteriormente

-- 5. Índices filtrados (SQL Server)
CREATE INDEX IX_AuditLog_Pending 
ON AuditLog(ChangedAt)
WHERE Processed = 0;

-- 6. Limitar dados armazenados
-- Usar JSONB parcial ao invés de full snapshots
CREATE OR REPLACE FUNCTION minimal_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Apenas armazenar colunas que mudaram
    INSERT INTO audit_log (
        table_name, record_id, operation,
        changed_columns, new_values
    ) VALUES (
        TG_TABLE_NAME, NEW.id, TG_OP,
        ARRAY['column1', 'column2'],  -- Simplificado
        jsonb_build_object('column1', NEW.column1)
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Benchmarks

```sql
-- Script de benchmark para triggers
DO $$
DECLARE
    v_start TIMESTAMP;
    v_end TIMESTAMP;
    v_duration INTERVAL;
    v_iterations INTEGER := 10000;
BEGIN
    -- Teste sem trigger
    v_start := clock_timestamp();
    
    FOR i IN 1..v_iterations LOOP
        INSERT INTO test_table (data) VALUES ('test_' || i);
    END LOOP;
    
    v_end := clock_timestamp();
    v_duration := v_end - v_start;
    
    RAISE NOTICE 'Sem trigger: % iterações em %', v_iterations, v_duration;
    
    -- Limpar
    TRUNCATE test_table;
    
    -- Criar trigger
    CREATE TRIGGER trg_test_audit
    AFTER INSERT ON test_table
    FOR EACH ROW EXECUTE FUNCTION audit.log_change();
    
    -- Teste com trigger
    v_start := clock_timestamp();
    
    FOR i IN 1..v_iterations LOOP
        INSERT INTO test_table (data) VALUES ('test_' || i);
    END LOOP;
    
    v_end := clock_timestamp();
    v_duration := v_end - v_start;
    
    RAISE NOTICE 'Com trigger: % iterações em %', v_iterations, v_duration;
    
    -- Calcular overhead
    RAISE NOTICE 'Overhead estimado: %', 
        (v_duration / v_iterations) * 1000 || ' ms por operação';
END;
$$;
```

---

## Resumo

### Pontos-Chave

1. **Triggers são essenciais para auditoria** — mas devem ser implementados com cuidado
2. **Row-level vs Statement-level** — escolher baseado no caso de uso
3. **Security risks são reais** — Dynamic SQL em triggers pode ser explorado
4. **Audit table design é crítico** — imutabilidade, metadados, indexação
5. **CDC é poderoso** — captura completa de mudanças para sincronização e compliance
6. **Temporal tables** — permitem consultas no tempo (time-travel)
7. **Soft deletes** — preservam dados para auditoria e recuperação
8. **Compliance logging** — requisitos variam por regulamentação
9. **Performance impact** — triggers adicionam overhead; otimizar quando necessário

### Checklist de Implementação

- [ ] Triggers de auditoria em todas as tabelas sensíveis
- [ ] Audit log com metadados completos (quem, quando, onde)
- [ ] Índices adequados para consultas de auditoria
- [ ] Particionamento para performance e retenção
- [ ] Verificação de integridade dos logs
- [ ] Soft deletes em vez de hard deletes quando apropriado
- [ ] CDC para sincronização e compliance
- [ ] Monitoramento de performance dos triggers
- [ ] Política de retenção de logs definida
- [ ] Testes de segurança dos triggers

### Referências

- OWASP Logging Cheat Sheet
- NIST SP 800-92: Guide to Computer Security Log Management
- PCI DSS Requirements 10.x
- HIPAA Security Rule §164.312(b)
- GDPR Article 30: Records of Processing Activities

---

## Testes de Segurança para Triggers e Auditoria

### Metodologia de Teste

O teste de segurança para triggers e sistemas de auditoria requer validação de múltiplos aspectos: funcionalidade, integridade, performance e segurança.

**Fase 1: Teste de Funcionalidade**

```python
class TriggerFunctionalityTester:
    """Testador de funcionalidade de triggers"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def test_audit_trigger_captures_all_operations(self):
        """Testa se trigger captura todas as operações"""
        test_cases = [
            {
                'operation': 'INSERT',
                'sql': "INSERT INTO employees (name, email) VALUES ('Test User', 'test@example.com')",
                'expected_action': 'INSERT'
            },
            {
                'operation': 'UPDATE',
                "sql": "UPDATE employees SET email = 'updated@example.com' WHERE name = 'Test User'",
                'expected_action': 'UPDATE'
            },
            {
                'operation': 'DELETE',
                "sql": "DELETE FROM employees WHERE name = 'Test User'",
                'expected_action': 'DELETE'
            }
        ]
        
        results = []
        cursor = self.conn.cursor()
        
        for test in test_cases:
            # Limpar dados anteriores
            cursor.execute("DELETE FROM employees WHERE name = 'Test User'")
            cursor.execute("DELETE FROM audit_log WHERE table_name = 'employees'")
            self.conn.commit()
            
            # Executar operação
            cursor.execute(test['sql'])
            self.conn.commit()
            
            # Verificar se auditoria foi registrada
            cursor.execute("""
                SELECT action FROM audit_log 
                WHERE table_name = 'employees' 
                ORDER BY performed_at DESC 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            
            if result and result[0] == test['expected_action']:
                results.append({
                    'test': f"Audit {test['operation']}",
                    'status': 'PASS'
                })
            else:
                results.append({
                    'test': f"Audit {test['operation']}",
                    'status': 'FAIL',
                    'expected': test['expected_action'],
                    'actual': result[0] if result else None
                })
        
        return results
    
    def test_audit_data_completeness(self):
        """Testa se dados de auditoria estão completos"""
        cursor = self.conn.cursor()
        
        # Inserir registro de teste
        cursor.execute("""
            INSERT INTO employees (name, email, salary) 
            VALUES ('Audit Test', 'audit@test.com', 50000)
        """)
        self.conn.commit()
        
        # Atualizar registro
        cursor.execute("""
            UPDATE employees SET salary = 55000 
            WHERE name = 'Audit Test'
        """)
        self.conn.commit()
        
        # Verificar dados de auditoria
        cursor.execute("""
            SELECT 
                old_data,
                new_data,
                changed_by,
                changed_at,
                changed_columns
            FROM audit_log 
            WHERE table_name = 'employees' 
            AND record_id = (SELECT id FROM employees WHERE name = 'Audit Test')
            ORDER BY performed_at
        """)
        
        audit_records = cursor.fetchall()
        
        results = []
        
        # Verificar INSERT
        if len(audit_records) >= 1:
            insert_record = audit_records[0]
            if insert_record[1] and 'salary' in str(insert_record[1]):
                results.append({'test': 'INSERT audit data', 'status': 'PASS'})
            else:
                results.append({'test': 'INSERT audit data', 'status': 'FAIL'})
        
        # Verificar UPDATE
        if len(audit_records) >= 2:
            update_record = audit_records[1]
            if (update_record[0] and update_record[1] and 
                '50000' in str(update_record[0]) and '55000' in str(update_record[1])):
                results.append({'test': 'UPDATE audit data', 'status': 'PASS'})
            else:
                results.append({'test': 'UPDATE audit data', 'status': 'FAIL'})
        
        # Limpar
        cursor.execute("DELETE FROM employees WHERE name = 'Audit Test'")
        cursor.execute("DELETE FROM audit_log WHERE table_name = 'employees'")
        self.conn.commit()
        
        return results
```

**Fase 2: Teste de Segurança**

```python
class TriggerSecurityTester:
    """Testador de segurança de triggers"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def test_trigger_injection_vulnerability(self):
        """Testa vulnerabilidade de injeção em triggers"""
        cursor = self.conn.cursor()
        
        # Payload de teste para injeção
        malicious_payloads = [
            "'; DROP TABLE audit_log;--",
            "' OR '1'='1",
            "'; INSERT INTO users (role) VALUES ('admin');--",
            "1; EXEC xp_cmdshell('whoami');--"
        ]
        
        results = []
        
        for payload in malicious_payloads:
            try:
                # Tentar inserir dados maliciosos
                cursor.execute(
                    "INSERT INTO employees (name, email) VALUES (%s, %s)",
                    (payload, 'test@test.com')
                )
                self.conn.commit()
                
                # Verificar se dados foram inseridos corretamente
                cursor.execute("SELECT name FROM employees WHERE email = 'test@test.com'")
                result = cursor.fetchone()
                
                if result and result[0] == payload:
                    results.append({
                        'payload': payload,
                        'status': 'SAFE',
                        'note': 'Data stored as-is, no injection'
                    })
                else:
                    results.append({
                        'payload': payload,
                        'status': 'VULNERABLE',
                        'note': 'Data was modified or injection occurred'
                    })
                
                # Limpar
                cursor.execute("DELETE FROM employees WHERE email = 'test@test.com'")
                self.conn.commit()
                
            except Exception as e:
                results.append({
                    'payload': payload,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        return results
    
    def test_trigger_permission_escalation(self):
        """Testa escalonamento de privilégios via triggers"""
        cursor = self.conn.cursor()
        
        results = []
        
        # Verificar se trigger pode ser explorado para elevação
        try:
            # Criar usuário de teste com permissões limitadas
            cursor.execute("""
                CREATE USER test_user WITHOUT LOGIN
            """)
            
            # Conceder permissão apenas na tabela de auditoria
            cursor.execute("""
                GRANT SELECT ON audit_log TO test_user
            """)
            
            # Tentar executar operações como test_user
            cursor.execute("EXECUTE AS USER = 'test_user'")
            
            # Verificar se pode modificar dados
            try:
                cursor.execute("""
                    INSERT INTO audit_log (table_name, action) 
                    VALUES ('test', 'TEST')
                """)
                results.append({
                    'test': 'Audit table write access',
                    'status': 'VULNERABLE',
                    'note': 'Low-privilege user can write to audit log'
                })
            except Exception:
                results.append({
                    'test': 'Audit table write access',
                    'status': 'SAFE'
                })
            
            # Reverter para usuário original
            cursor.execute("REVERT")
            
            # Limpar
            cursor.execute("DROP USER test_user")
            self.conn.commit()
            
        except Exception as e:
            results.append({
                'test': 'Permission escalation',
                'status': 'ERROR',
                'error': str(e)
            })
        
        return results
    
    def test_trigger_bypass(self):
        """Testa bypass de triggers"""
        cursor = self.conn.cursor()
        
        results = []
        
        # Testar se é possível bypassar triggers usando bulk operations
        try:
            # Bulk insert pode bypassar triggers em alguns SGBDRs
            cursor.execute("""
                SELECT COUNT(*) FROM employees 
                WHERE name = 'Bulk Test'
            """)
            initial_count = cursor.fetchone()[0]
            
            # Executar bulk insert
            cursor.execute("""
                INSERT INTO employees (name, email)
                SELECT 'Bulk Test ' + CAST(number AS VARCHAR), 'bulk@test.com'
                FROM (VALUES (1), (2), (3), (4), (5)) AS numbers(number)
            """)
            self.conn.commit()
            
            # Verificar se auditoria foi registrada para todas as linhas
            cursor.execute("""
                SELECT COUNT(*) FROM audit_log 
                WHERE table_name = 'employees' 
                AND action = 'INSERT'
                AND new_data->>'name' LIKE 'Bulk Test%'
            """)
            audit_count = cursor.fetchone()[0]
            
            if audit_count == 5:
                results.append({
                    'test': 'Bulk insert audit',
                    'status': 'PASS',
                    'note': 'All rows audited'
                })
            else:
                results.append({
                    'test': 'Bulk insert audit',
                    'status': 'FAIL',
                    'note': f'Expected 5, got {audit_count}'
                })
            
            # Limpar
            cursor.execute("DELETE FROM employees WHERE name LIKE 'Bulk Test%'")
            cursor.execute("DELETE FROM audit_log WHERE table_name = 'employees' AND new_data->>'name' LIKE 'Bulk Test%'")
            self.conn.commit()
            
        except Exception as e:
            results.append({
                'test': 'Bulk insert audit',
                'status': 'ERROR',
                'error': str(e)
            })
        
        return results
```

**Fase 3: Teste de Performance**

```python
class TriggerPerformanceTester:
    """Testador de performance de triggers"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def measure_trigger_overhead(self, table_name, num_operations=1000):
        """Mede overhead dos triggers"""
        import time
        
        cursor = self.conn.cursor()
        
        # Teste sem trigger (se possível desabilitar)
        print(f"[*] Testing {num_operations} operations on {table_name}...")
        
        # Medir tempo de INSERT
        start_time = time.time()
        
        for i in range(num_operations):
            cursor.execute(f"""
                INSERT INTO {table_name} (name, email) 
                VALUES ('Test{i}', 'test{i}@example.com')
            """)
        
        self.conn.commit()
        insert_time = time.time() - start_time
        
        # Limpar
        cursor.execute(f"DELETE FROM {table_name} WHERE name LIKE 'Test%'")
        self.conn.commit()
        
        # Medir tempo de UPDATE
        # Primeiro inserir dados
        for i in range(num_operations):
            cursor.execute(f"""
                INSERT INTO {table_name} (name, email) 
                VALUES ('UpdateTest{i}', 'update{i}@example.com')
            """)
        self.conn.commit()
        
        start_time = time.time()
        
        for i in range(num_operations):
            cursor.execute(f"""
                UPDATE {table_name} 
                SET email = 'updated{i}@example.com' 
                WHERE name = 'UpdateTest{i}'
            """)
        
        self.conn.commit()
        update_time = time.time() - start_time
        
        # Limpar
        cursor.execute(f"DELETE FROM {table_name} WHERE name LIKE 'UpdateTest%'")
        self.conn.commit()
        
        results = {
            'table': table_name,
            'operations': num_operations,
            'insert_time_ms': (insert_time / num_operations) * 1000,
            'update_time_ms': (update_time / num_operations) * 1000,
            'insert_ops_per_sec': num_operations / insert_time,
            'update_ops_per_sec': num_operations / update_time
        }
        
        return results
    
    def compare_with_without_trigger(self, table_name, trigger_name, num_operations=500):
        """Compara performance com e sem trigger"""
        import time
        
        cursor = self.conn.cursor()
        
        # Medir COM trigger
        start_time = time.time()
        for i in range(num_operations):
            cursor.execute(f"""
                INSERT INTO {table_name} (name, email) 
                VALUES ('WithTrigger{i}', 'test@example.com')
            """)
        self.conn.commit()
        with_trigger_time = time.time() - start_time
        
        # Limpar
        cursor.execute(f"DELETE FROM {table_name} WHERE name LIKE 'WithTrigger%'")
        self.conn.commit()
        
        # Desabilitar trigger temporariamente
        cursor.execute(f"DISABLE TRIGGER {trigger_name} ON {table_name}")
        
        # Medir SEM trigger
        start_time = time.time()
        for i in range(num_operations):
            cursor.execute(f"""
                INSERT INTO {table_name} (name, email) 
                VALUES ('WithoutTrigger{i}', 'test@example.com')
            """)
        self.conn.commit()
        without_trigger_time = time.time() - start_time
        
        # Reabilitar trigger
        cursor.execute(f"ENABLE TRIGGER {trigger_name} ON {table_name}")
        
        # Limpar
        cursor.execute(f"DELETE FROM {table_name} WHERE name LIKE 'WithoutTrigger%'")
        self.conn.commit()
        
        overhead = ((with_trigger_time - without_trigger_time) / without_trigger_time) * 100
        
        return {
            'table': table_name,
            'trigger': trigger_name,
            'with_trigger_ms': with_trigger_time * 1000,
            'without_trigger_ms': without_trigger_time * 1000,
            'overhead_percent': overhead
        }
```

### Automação de Testes

```python
# Script completo de teste de triggers e auditoria
import json
from datetime import datetime

class TriggerAuditTestSuite:
    """Suite completa de testes para triggers e auditoria"""
    
    def __init__(self, connection_string):
        self.conn = pyodbc.connect(connection_string)
        self.results = []
    
    def run_full_test_suite(self):
        """Executa suite completa de testes"""
        
        print("=" * 60)
        print("TRIGGER & AUDIT SECURITY TEST SUITE")
        print("=" * 60)
        
        # 1. Testes de funcionalidade
        print("\n[1/4] Running functionality tests...")
        functionality_tester = TriggerFunctionalityTester(self.conn)
        
        self.results.extend(functionality_tester.test_audit_trigger_captures_all_operations())
        self.results.extend(functionality_tester.test_audit_data_completeness())
        
        # 2. Testes de segurança
        print("\n[2/4] Running security tests...")
        security_tester = TriggerSecurityTester(self.conn)
        
        self.results.extend(security_tester.test_trigger_injection_vulnerability())
        self.results.extend(security_tester.test_trigger_permission_escalation())
        self.results.extend(security_tester.test_trigger_bypass())
        
        # 3. Testes de performance
        print("\n[3/4] Running performance tests...")
        performance_tester = TriggerPerformanceTester(self.conn)
        
        self.results.append(performance_tester.measure_trigger_overhead('employees'))
        self.results.append(performance_tester.compare_with_without_trigger('employees', 'trg_audit_employees'))
        
        # 4. Verificação de integridade
        print("\n[4/4] Running integrity checks...")
        self.results.extend(self.check_audit_integrity())
        
        # Gerar relatório
        report = self.generate_report()
        
        return report
    
    def check_audit_integrity(self):
        """Verifica integridade dos logs de auditoria"""
        cursor = self.conn.cursor()
        results = []
        
        # Verificar se há gaps na sequência de IDs
        cursor.execute("""
            SELECT 
                MIN(id) as min_id,
                MAX(id) as max_id,
                COUNT(*) as total_records
            FROM audit_log
        """)
        
        stats = cursor.fetchone()
        
        if stats[2] > 0:
            expected_count = stats[1] - stats[0] + 1
            if stats[2] != expected_count:
                results.append({
                    'test': 'Audit log sequence integrity',
                    'status': 'WARNING',
                    'note': f'Expected {expected_count} records, found {stats[2]}'
                })
            else:
                results.append({
                    'test': 'Audit log sequence integrity',
                    'status': 'PASS'
                })
        
        # Verificar se há registros órfãos
        cursor.execute("""
            SELECT COUNT(*) 
            FROM audit_log a
            WHERE NOT EXISTS (
                SELECT 1 FROM employees e 
                WHERE e.id::text = a.record_id
            )
            AND a.table_name = 'employees'
        """)
        
        orphan_count = cursor.fetchone()[0]
        
        if orphan_count > 0:
            results.append({
                'test': 'Audit log orphan records',
                'status': 'WARNING',
                'note': f'Found {orphan_count} orphan records'
            })
        else:
            results.append({
                'test': 'Audit log orphan records',
                'status': 'PASS'
            })
        
        return results
    
    def generate_report(self):
        """Gera relatório completo"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len([r for r in self.results if 'status' in r]),
                'passed': len([r for r in self.results if r.get('status') == 'PASS']),
                'failed': len([r for r in self.results if r.get('status') == 'FAIL']),
                'warnings': len([r for r in self.results if r.get('status') == 'WARNING']),
                'errors': len([r for r in self.results if r.get('status') == 'ERROR'])
            },
            'results': self.results
        }
        
        # Salvar relatório
        filename = f'trigger_audit_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nReport saved to: {filename}")
        
        return report

# Executar testes
if __name__ == "__main__":
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SecureApp;UID=readonly;PWD=readonly_password"
    
    tester = TriggerAuditTestSuite(connection_string)
    report = tester.run_full_test_suite()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Warnings: {report['summary']['warnings']}")
    print(f"Errors: {report['summary']['errors']}")
```

### Relatório de Testes

```markdown
# Relatório de Testes - Triggers e Auditoria

## Resumo Executivo
- Total de testes: 45
- Aprovados: 38
- Reprovados: 3
- Avisos: 2
- Erros: 2

## Testes de Funcionalidade

### PASS: Audit INSERT captures
- Trigger registra todas as inserções corretamente
- Dados anteriores e posteriores são salvos

### PASS: Audit UPDATE captures
- Trigger registra todas as atualizações
- Colunas alteradas são identificadas

### FAIL: Audit DELETE captures
- Trigger não está registrando exclusões
- **Ação necessária**: Verificar trigger de DELETE

## Testes de Segurança

### PASS: SQL Injection resistance
- Triggers não são vulneráveis a injeção SQL
- Dados maliciosos são tratados como strings

### PASS: Permission escalation blocked
- Usuários de baixo privilégio não podem modificar audit_log
- Triggers usam SECURITY INVOKER

### WARNING: Bulk operation audit
- Alguns SGBDRs podem bypassar triggers em operações bulk
- **Recomendação**: Usar MERGE com tratamento explícito

## Testes de Performance

### PASS: Trigger overhead acceptable
- Overhead médio: 15ms por operação
- Dentro do limite aceitável (< 50ms)

### WARNING: High-volume impact
- Em operações > 10.000 linhas, overhead pode ser significativo
- **Recomendação**: Usar batch processing

## Recomendações
1. Corrigir trigger de DELETE
2. Implementar batch processing para operações em lote
3. Adicionar monitoramento de performance
4. Revisar política de retenção de logs
```

---

## Referências e Recursos Adicionais

### Documentação Oficial

- **PostgreSQL Triggers**: https://www.postgresql.org/docs/current/sql-createtrigger.html
- **SQL Server Triggers**: https://docs.microsoft.com/en-us/sql/relational-databases/triggers/
- **Oracle Triggers**: https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/
- **MySQL Triggers**: https://dev.mysql.com/doc/refman/8.0/en/create-trigger.html

### OWASP Resources

- **OWASP Logging Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- **OWASP Audit Guide**: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/

### Standards and Compliance

- **NIST SP 800-92**: Guide to Computer Security Log Management
- **PCI DSS v4.0**: Requirement 10 - Logging and Monitoring
- **HIPAA Security Rule**: §164.312(b) - Audit Controls
- **GDPR**: Article 30 - Records of Processing Activities
- **SOX Section 404**: Internal Control Assessment

### Books and Papers

- "Database Auditing" by Don Burleson
- "SQL Server Audit" by Microsoft
- "PostgreSQL Server Programming" by Hannu Krosing
- "Oracle Database 12c Security" by David Coffey

---

*Este capítulo demonstrou como implementar triggers e sistemas de auditoria robustos. Os conceitos aqui apresentados são fundamentais para conformidade regulatória e segurança de dados.*
