# Capítulo 8: Stored Procedures e Segurança

## Introdução

Stored procedures são blocos de código SQL armazenados e executados diretamente no servidor de banco de dados. Quando implementadas corretamente, representam uma das camadas de segurança mais poderosas para proteção contra SQL injection, controle de acesso granular e centralização de lógica de negócio. Este capítulo explora como stored procedures funcionam, seus benefícios de segurança, riscos associados e padrões de implementação segura nos principais SGBDR.

---

## O que são Stored Procedures

### Definição e Conceito

Uma stored procedure é uma coleção de instruções SQL que pode ser armazenada no servidor de banco de dados e executada sob demanda. Diferente de consultas simples, stored procedures podem conter:

- Variáveis locais
- Estruturas de controle (IF/ELSE, WHILE, FOR)
- Tratamento de erros (TRY/CATCH)
- Parâmetros de entrada e saída
- Cursores para iteração
- Transações embutidas

### Exemplo Básico

```sql
-- PostgreSQL: Procedimento simples
CREATE OR REPLACE PROCEDURE update_salary(
    emp_id INTEGER,
    raise_percent NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE employees
    SET salary = salary * (1 + raise_percent / 100)
    WHERE employee_id = emp_id;
    
    COMMIT;
END;
$$;

-- Execução
CALL update_salary(1001, 10.0);
```

```sql
-- SQL Server: Procedimento simples
CREATE PROCEDURE UpdateSalary
    @EmployeeID INT,
    @RaisePercent DECIMAL(5,2)
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE Employees
    SET Salary = Salary * (1 + @RaisePercent / 100)
    WHERE EmployeeID = @EmployeeID;
END;
GO

-- Execução
EXEC UpdateSalary @EmployeeID = 1001, @RaisePercent = 10.0;
```

```sql
-- Oracle: Procedimento simples
CREATE OR REPLACE PROCEDURE update_salary(
    p_emp_id IN NUMBER,
    p_raise_percent IN NUMBER
)
AS
BEGIN
    UPDATE employees
    SET salary = salary * (1 + p_raise_percent / 100)
    WHERE employee_id = p_emp_id;
    
    COMMIT;
END update_salary;
/

-- Execução
BEGIN
    update_salary(1001, 10.0);
END;
/
```

### Diferença entre Procedures e Functions

| Aspecto | Stored Procedure | Function |
|---------|------------------|----------|
| Retorno | Pode retornar múltiplos resultados | Retorna um valor único |
| Uso em queries | CALL/EXEC | Pode ser usada em SELECT |
| Transações | Pode conter COMMIT/ROLLBACK | Não pode modificar estado |
| Parâmetros IN/OUT | Suporta parâmetros IN, OUT, INOUT | Apenas parâmetros IN |
| Uso principal | Lógica de negócio, DML | Cálculos, expressões |

---

## Vantagens de Segurança

### 1. Prevenção contra SQL Injection

A principal vantagem de segurança das stored procedures é a separação entre código SQL e dados. Quando os parâmetros são passados corretamente, o motor do banco de dados trata automaticamente a sanitização.

**Sem stored procedures (vulnerável):**

```python
# Python - VULNERAVEL
def get_user_vulnerable(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# Se username = "admin' OR '1'='1"
# Query se torna: SELECT * FROM users WHERE username = 'admin' OR '1'='1'
```

**Com stored procedures (seguro):**

```sql
-- Stored procedure segura
CREATE PROCEDURE GetUser
    @Username NVARCHAR(50)
AS
BEGIN
    -- Parâmetros são tratados como valores, não como código SQL
    SELECT * FROM users WHERE username = @Username;
END;
```

```python
# Python - SEGURO
def get_user_secure(username):
    cursor.execute("EXEC GetUser @Username = ?", (username,))
    return cursor.fetchone()

# Mesmo se username = "admin' OR '1'='1"
# A query procuraria literalmente por "admin' OR '1'='1"
```

### 2. Controle de Acesso Granular

Stored procedures permitem conceder permissões de execução sem conceder acesso direto às tabelas.

```sql
-- Conceder apenas EXECUTE na procedure, não nas tabelas
GRANT EXECUTE ON GetUser TO app_user;
GRANT EXECUTE ON UpdateSalary TO hr_manager;

-- O usuário NÃO pode acessar diretamente:
-- SELECT * FROM employees (negado)
-- Mas PODE executar:
-- EXEC GetUser @Username = 'john' (permitido)
```

### 3. Centralização de Lógica de Negócio

A lógica fica armazenada no banco, garantindo consistência e facilitando auditoria e manutenção.

### 4. Encapsulamento de Operações Complexas

```sql
-- Procedure que encapsula múltiplas operações
CREATE PROCEDURE TransferFunds
    @FromAccount INT,
    @ToAccount INT,
    @Amount DECIMAL(18,2)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Debitar da origem
        UPDATE Accounts
        SET Balance = Balance - @Amount
        WHERE AccountID = @FromAccount AND Balance >= @Amount;
        
        IF @@ROWCOUNT = 0
        BEGIN
            RAISERROR('Insufficient funds or account not found', 16, 1);
            ROLLBACK;
            RETURN;
        END
        
        -- Creditar no destino
        UPDATE Accounts
        SET Balance = Balance + @Amount
        WHERE AccountID = @ToAccount;
        
        -- Registrar transação
        INSERT INTO Transactions (FromAccount, ToAccount, Amount, CreatedAt)
        VALUES (@FromAccount, @ToAccount, @Amount, GETDATE());
        
        COMMIT;
    END TRY
    BEGIN CATCH
        ROLLBACK;
        THROW;
    END CATCH
END;
```

---

## Dynamic SQL

### O que é Dynamic SQL

Dynamic SQL permite construir e executar consultas SQL como strings em tempo de execução. É necessário quando a estrutura da consulta depende de parâmetros que só estão disponíveis durante a execução.

### Quando usar Dynamic SQL

- Nomes de tabelas ou colunas que variam
- Número dinâmico de parâmetros
- Construção de queries de relatório
- Migração de dados com estruturas variáveis

### Riscos de Dynamic SQL

Dynamic SQL é um dos vetores mais perigosos de SQL injection quando implementado incorretamente.

**Exemplo perigoso:**

```sql
-- SQL Server: Dynamic SQL INSEGURA
CREATE PROCEDURE SearchEmployees
    @SearchColumn NVARCHAR(50),
    @SearchValue NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    
    -- VULNERAVEL: interpolação direta
    SET @sql = 'SELECT * FROM Employees WHERE ' + @SearchColumn + ' = ''' + @SearchValue + '''';
    
    EXEC(@sql);
END;
```

```sql
-- Injeção via @SearchColumn: "1=1; DROP TABLE Employees;--"
-- Injeção via @SearchValue: "'; DROP TABLE Employees;--"
```

### sp_executesql (SQL Server)

`sp_executesql` é a forma segura de executar Dynamic SQL no SQL Server porque suporta parâmetros.

**Exemplo seguro:**

```sql
-- SQL Server: Dynamic SQL SEGURO com sp_executesql
CREATE PROCEDURE SearchEmployeesSafe
    @SearchColumn NVARCHAR(50),
    @SearchValue NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    DECLARE @params NVARCHAR(100);
    
    -- Validar nome da coluna contra whitelist
    IF @SearchColumn NOT IN ('FirstName', 'LastName', 'Email', 'Department')
    BEGIN
        RAISERROR('Invalid column name', 16, 1);
        RETURN;
    END
    
    -- Construir query com parâmetro seguro
    SET @sql = N'SELECT * FROM Employees WHERE ' + QUOTENAME(@SearchColumn) + N' = @SearchValue';
    SET @params = N'@SearchValue NVARCHAR(100)';
    
    -- Executar com sp_executesql
    EXEC sp_executesql @sql, @params, @SearchValue = @SearchValue;
END;
```

**Por que sp_executesql é mais seguro:**

```sql
-- 1. Separação entre código e dados
DECLARE @sql NVARCHAR(MAX) = N'SELECT * FROM Users WHERE Username = @Username';
DECLARE @params NVARCHAR(100) = N'@Username NVARCHAR(50)';
DECLARE @username NVARCHAR(50) = N'admin'' OR ''1''=''1';

-- sp_executesql trata o valor como DADO, não como código
EXEC sp_executesql @sql, @params, @Username = @username;

-- Resultado: SELECT * FROM Users WHERE Username = 'admin'' OR ''1''=''1'
-- O motor do banco NÃO executa a injeção
```

### EXECUTE IMMEDIATE (Oracle)

`EXECUTE IMMEDIATE` é o equivalente do Oracle para Dynamic SQL.

**Exemplo inseguro:**

```sql
-- Oracle: Dynamic SQL INSEGURA
CREATE OR REPLACE PROCEDURE search_employee_safe(
    p_search_column IN VARCHAR2,
    p_search_value IN VARCHAR2
)
AS
    v_sql VARCHAR2(1000);
BEGIN
    -- VULNERAVEL: interpolação direta
    v_sql := 'SELECT * FROM employees WHERE ' || p_search_column || ' = ''' || p_search_value || '''';
    
    EXECUTE IMMEDIATE v_sql;
END;
```

**Exemplo seguro com BIND variables:**

```sql
-- Oracle: Dynamic SQL SEGURA
CREATE OR REPLACE PROCEDURE search_employee_safe(
    p_search_column IN VARCHAR2,
    p_search_value IN VARCHAR2
)
AS
    v_sql VARCHAR2(1000);
    v_cursor SYS_REFCURSOR;
    v_result employees%ROWTYPE;
BEGIN
    -- Validar coluna contra whitelist
    IF p_search_column NOT IN ('FIRST_NAME', 'LAST_NAME', 'EMAIL', 'DEPARTMENT_ID') THEN
        RAISE_APPLICATION_ERROR(-20001, 'Invalid column name');
    END IF;
    
    -- Construir query com BIND variables
    v_sql := 'SELECT * FROM employees WHERE ' || p_search_column || ' = :search_value';
    
    -- EXECUTE IMMEDIATE com USING para passar valores de forma segura
    EXECUTE IMMEDIATE v_sql INTO v_cursor USING p_search_value;
    
    -- Processar resultados
    LOOP
        FETCH v_cursor INTO v_result;
        EXIT WHEN v_cursor%NOTFOUND;
        -- Processar v_result
    END LOOP;
    
    CLOSE v_cursor;
END;
```

### PL/pgSQL Dynamic SQL (PostgreSQL)

**Exemplo seguro:**

```sql
-- PostgreSQL: Dynamic SQL SEGURO
CREATE OR REPLACE PROCEDURE search_employee_safe(
    p_search_column TEXT,
    p_search_value TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sql TEXT;
    v_result RECORD;
BEGIN
    -- Validar coluna contra whitelist
    IF p_search_column NOT IN ('first_name', 'last_name', 'email', 'department_id') THEN
        RAISE EXCEPTION 'Invalid column name: %', p_search_column;
    END IF;
    
    -- Construir query com formato seguro
    v_sql := format(
        'SELECT * FROM employees WHERE %I = $1',
        p_search_column  -- %I formata como identificador seguro
    );
    
    -- EXECUTE com USING para parâmetros seguros
    FOR v_result IN EXECUTE v_sql USING p_search_value
    LOOP
        RAISE NOTICE 'Found: % %', v_result.first_name, v_result.last_name;
    END LOOP;
END;
$$;
```

### Formatação Segura no PostgreSQL

```sql
-- PostgreSQL: Funções de formatação seguras
-- %I: Identificador (escaped corretamente)
-- %L: Literal (escaped corretamente)
-- %s: String (perigoso - NÃO usar para nomes de colunas)

-- SEGURO: usando %I para identificadores
v_sql := format('SELECT %I FROM %I WHERE %I = %L', 
    column_name, table_name, filter_column, filter_value);

-- SEGURO: usando %L para literais
v_sql := format('SELECT * FROM users WHERE username = %L', user_input);

-- PERIGOSO: usando %s (NÃO usar)
v_sql := format('SELECT * FROM users WHERE username = %s', user_input);
```

---

## Permission Model (EXECUTE Permission)

### Modelo de Permissões

O modelo de permissões em stored procedures é uma das camadas de segurança mais importantes. Em vez de conceder acesso direto às tabelas, concede-se apenas a capacidade de executar procedures específicas.

### Hierarquia de Permissões

```
Server Level
    └── Database Level
            └── Schema Level
                    └── Object Level (Tables, Procedures, Functions)
```

### Concessão de Permissões

**SQL Server:**

```sql
-- Criar roles específicas
CREATE ROLE db_executor;
CREATE ROLE db_reader;
CREATE ROLE db_writer;
CREATE ROLE db_admin;

-- Conceder EXECUTE em procedures
GRANT EXECUTE ON SCHEMA::dbo TO db_executor;
GRANT EXECUTE ON GetUser TO app_user;
GRANT EXECUTE ON UpdateSalary TO hr_manager;

-- Negar acesso direto às tabelas
DENY SELECT ON Employees TO app_user;
DENY INSERT ON Employees TO app_user;
DENY UPDATE ON Employees TO app_user;
DENY DELETE ON Employees TO app_user;

-- Conceder apenas via procedures
GRANT EXECUTE ON CreateEmployee TO db_writer;
GRANT EXECUTE ON GetEmployeeReport TO db_reader;
```

**PostgreSQL:**

```sql
-- Criar roles
CREATE ROLE app_role;
CREATE ROLE hr_role;
CREATE ROLE readonly_role;

-- Conceder EXECUTE em functions/procedures
GRANT USAGE ON SCHEMA public TO app_role;
GRANT EXECUTE ON FUNCTION get_user(VARCHAR) TO app_role;
GRANT EXECUTE ON FUNCTION update_salary(INT, NUMERIC) TO hr_role;

-- Negar acesso direto
REVOKE ALL ON employees FROM app_role;
REVOKE ALL ON salaries FROM app_role;

-- Conceder apenas o necessário
GRANT SELECT ON employees TO readonly_role;
```

**Oracle:**

```sql
-- Criar roles
CREATE ROLE app_role;
CREATE ROLE hr_role;

-- Conceder EXECUTE
GRANT EXECUTE ON get_employee TO app_role;
GRANT EXECUTE ON update_salary TO hr_role;

-- Negar acesso direto
REVOKE SELECT, INSERT, UPDATE, DELETE ON employees FROM app_role;

-- Usar VPD (Virtual Private Database) para acesso granular
CREATE OR REPLACE FUNCTION employee_security(
    p_schema VARCHAR2,
    p_table VARCHAR2
)
RETURN VARCHAR2
AS
BEGIN
    RETURN 'department_id = SYS_CONTEXT(''USERENV'', ''CLIENT_INFO'')';
END;
/

BEGIN
    DBMS_RLS.ADD_POLICY(
        object_schema   => 'HR',
        object_name     => 'EMPLOYEES',
        policy_name     => 'EMPLOYEE_SECURITY',
        function_schema => 'HR',
        policy_function => 'EMPLOYEE_SECURITY',
        statement_types => 'SELECT, UPDATE, DELETE'
    );
END;
/
```

### Principio do Menor Privilegio

```sql
-- Criar procedures com permissões mínimas necessárias

-- Procedure para leitura (apenas SELECT)
CREATE PROCEDURE GetEmployeeInfo
    @EmployeeID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Apenas SELECT - não precisa de permissões de INSERT/UPDATE/DELETE
    SELECT 
        EmployeeID,
        FirstName,
        LastName,
        Email,
        DepartmentName,
        HireDate
    FROM Employees e
    JOIN Departments d ON e.DepartmentID = d.DepartmentID
    WHERE e.EmployeeID = @EmployeeID;
END;

-- Procedure para escrita (INSERT/UPDATE)
CREATE PROCEDURE UpdateEmployeeContact
    @EmployeeID INT,
    @Email NVARCHAR(100),
    @Phone NVARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE Employees
    SET Email = @Email,
        Phone = @Phone,
        UpdatedAt = GETDATE()
    WHERE EmployeeID = @EmployeeID;
END;

-- Conceder permissões específicas
GRANT EXECUTE ON GetEmployeeInfo TO readonly_role;
GRANT EXECUTE ON UpdateEmployeeContact TO editor_role;
```

---

## SQL Injection em Stored Procedures

### Vetores de Ataque

Mesmo com stored procedures, SQL injection pode ocorrer em três cenários:

1. **Dynamic SQL interno** — a procedure usa EXEC/sp_executesql incorretamente
2. **Parâmetros de metadados** — nomes de tabelas/colunas são parâmetros
3. **Uso incorreto de parâmetros** — parâmetros são concatenados em vez de passados como valores

### Vetor 1: Dynamic SQL Interno

```sql
-- SQL Server: Procedure VULNERAVEL
CREATE PROCEDURE SearchUsers
    @SearchTerm NVARCHAR(100)
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    
    -- VULNERAVEL: interpolação direta
    SET @sql = 'SELECT * FROM Users WHERE Username LIKE ''%' + @SearchTerm + '%''';
    
    EXEC(@sql);
END;
```

```python
# Exploitation
import requests

def exploit_sql_injection():
    # Injeção via SearchTerm
    payload = {
        "search": "'; DROP TABLE Users;--"
    }
    
    # Ou extrair dados
    payload = {
        "search": "' UNION SELECT username, password, NULL, NULL FROM Users--"
    }
    
    response = requests.get(
        "http://target.com/api/search",
        params=payload
    )
    
    return response.json()
```

### Vetor 2: Parâmetros de Metadados

```sql
-- SQL Server: Procedure VULNERAVEL com parâmetro de coluna
CREATE PROCEDURE GetColumnValue
    @TableName NVARCHAR(100),
    @ColumnName NVARCHAR(100),
    @ID INT
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    
    -- VULNERAVEL: parâmetros de metadados interpolados
    SET @sql = 'SELECT ' + @ColumnName + ' FROM ' + @TableName + ' WHERE ID = ' + CAST(@ID AS NVARCHAR);
    
    EXEC(@sql);
END;
```

```sql
-- Exploitation: enumerar bancos de dados
EXEC GetColumnValue 
    @TableName = 'sys.databases',
    @ColumnName = 'name',
    @ID = 1;

-- Exploitation: ler dados de outras tabelas
EXEC GetColumnValue 
    @TableName = 'INFORMATION_SCHEMA.TABLES',
    @ColumnName = 'TABLE_NAME',
    @ID = 1;
```

### Vetor 3: Uso Incorreto de Parâmetros

```sql
-- Oracle: Procedure VULNERAVEL
CREATE OR REPLACE PROCEDURE get_user_safe(
    p_username IN VARCHAR2
)
AS
    v_result VARCHAR2(4000);
BEGIN
    -- VULNERAVEL: usando USING incorretamente
    EXECUTE IMMEDIATE 
        'SELECT password FROM users WHERE username = ''' || p_username || ''''
    INTO v_result;
END;
```

### Exemplo Completo de Exploitation

```sql
-- SQL Server: Cenário completo de exploração

-- 1. Criar procedure vulnerable
CREATE PROCEDURE sp_SearchProducts
    @SearchTerm NVARCHAR(200),
    @Category NVARCHAR(50) = NULL
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    
    SET @sql = 'SELECT * FROM Products WHERE Name LIKE ''%' + @SearchTerm + '%''';
    
    IF @Category IS NOT NULL
        SET @sql = @sql + ' AND Category = ''' + @Category + '''';
    
    EXEC(@sql);
END;

-- 2. Exploitation via SearchTerm
-- Input: '; SELECT * FROM Users;--
-- Query resultante: SELECT * FROM Products WHERE Name LIKE '%'; SELECT * FROM Users;--%'

-- 3. Exploitation via Category
-- Input: ' OR 1=1;--
-- Query resultante: SELECT * FROM Products WHERE Name LIKE '%search%' AND Category = '' OR 1=1;--'

-- 4. Exploitation avançada com UNION
-- Input: ' UNION SELECT Username, Password, NULL, NULL FROM Users;--
-- Query resultante: SELECT * FROM Products WHERE Name LIKE '%'; UNION SELECT Username, Password, NULL, NULL FROM Users;--%'
```

### Script de Detecção

```python
#!/usr/bin/env python3
"""
Detector de SQL Injection em Stored Procedures
"""

import re
from typing import List, Dict, Tuple

class SPInjectionDetector:
    def __init__(self):
        self.vulnerabilities = []
        self.dangerous_patterns = [
            # SQL Server
            (r"EXEC\s*\(", "EXEC with dynamic string"),
            (r"EXEC\s*\@", "EXEC with variable"),
            (r"sp_executesql\s+@", "sp_executesql with variable"),
            
            # Oracle
            (r"EXECUTE\s+IMMEDIATE\s+'", "EXECUTE IMMEDIATE with string literal"),
            (r"EXECUTE\s+IMMEDIATE\s+\|\|", "EXECUTE IMMEDIATE with concatenation"),
            
            # PostgreSQL
            (r"EXECUTE\s+USING\s+", "EXECUTE without USING"),
            (r"format\s*\(\s*'SELECT", "format with SELECT (check for %s)"),
            
            # General
            (r"CONCAT\s*\(.*SELECT", "CONCAT in SELECT"),
            (r"'\s*\|\|.*SELECT", "String concatenation in SELECT"),
            (r"SET\s+@\w+\s*=\s*'.*SELECT", "Variable assignment with SELECT"),
        ]
    
    def analyze_procedure(self, procedure_name: str, procedure_body: str) -> List[Dict]:
        """Analisa uma procedure para vulnerabilidades"""
        findings = []
        lines = procedure_body.split('\n')
        
        for i, line in enumerate(lines, 1):
            for pattern, description in self.dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        'procedure': procedure_name,
                        'line': i,
                        'code': line.strip(),
                        'vulnerability': description,
                        'severity': self._assess_severity(line)
                    })
        
        return findings
    
    def _assess_severity(self, line: str) -> str:
        """Avalia severidade da vulnerabilidade"""
        high_risk = ['EXEC', 'EXECUTE IMMEDIATE', 'sp_executesql']
        medium_risk = ['CONCAT', 'SET @']
        
        for keyword in high_risk:
            if keyword in line.upper():
                return 'HIGH'
        
        for keyword in medium_risk:
            if keyword in line.upper():
                return 'MEDIUM'
        
        return 'LOW'
    
    def generate_report(self, procedures: Dict[str, str]) -> str:
        """Gera relatório de vulnerabilidades"""
        report = "=" * 80 + "\n"
        report += "SQL INJECTION ANALYSIS REPORT - STORED PROCEDURES\n"
        report += "=" * 80 + "\n\n"
        
        all_findings = []
        
        for name, body in procedures.items():
            findings = self.analyze_procedure(name, body)
            all_findings.extend(findings)
        
        if not all_findings:
            report += "No vulnerabilities found.\n"
            return report
        
        # Ordenar por severidade
        severity_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        all_findings.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        for finding in all_findings:
            report += f"Procedure: {finding['procedure']}\n"
            report += f"Line: {finding['line']}\n"
            report += f"Severity: {finding['severity']}\n"
            report += f"Vulnerability: {finding['vulnerability']}\n"
            report += f"Code: {finding['code']}\n"
            report += "-" * 80 + "\n\n"
        
        return report

# Exemplo de uso
detector = SPInjectionDetector()

procedures = {
    "sp_SearchProducts": """
        CREATE PROCEDURE sp_SearchProducts
            @SearchTerm NVARCHAR(200)
        AS
        BEGIN
            DECLARE @sql NVARCHAR(MAX);
            SET @sql = 'SELECT * FROM Products WHERE Name LIKE ''%' + @SearchTerm + '%''';
            EXEC(@sql);
        END;
    """,
    "sp_GetUser": """
        CREATE PROCEDURE sp_GetUser
            @UserID INT
        AS
        BEGIN
            SELECT * FROM Users WHERE UserID = @UserID;
        END;
    """
}

report = detector.generate_report(procedures)
print(report)
```

---

## Granting Least Privilege

### Princípio do Menor Privilegio

O princípio do menor privilégio estabelece que cada elemento do sistema deve operar com o conjunto mínimo de privilégios necessários para completar sua tarefa legítima.

### Implementação em SQL Server

```sql
-- Criar database roles granulares
CREATE ROLE role_employee_read;
CREATE ROLE role_employee_write;
CREATE ROLE role_salary_manage;
CREATE ROLE role_report_generate;

-- Conceder permissões mínimas por role

-- role_employee_read: apenas leitura de dados básicos
GRANT SELECT ON Employees (EmployeeID, FirstName, LastName, Email, DepartmentID) TO role_employee_read;
GRANT SELECT ON Departments TO role_employee_read;

-- role_employee_write: leitura + atualização de contato
GRANT SELECT ON Employees TO role_employee_write;
GRANT UPDATE ON Employees (Email, Phone, Address) TO role_employee_write;

-- role_salary_manage: acesso limitado a salários
GRANT SELECT ON Employees (EmployeeID, FirstName, LastName) TO role_salary_manage;
GRANT SELECT ON Salaries TO role_salary_manage;
GRANT EXECUTE ON UpdateSalary TO role_salary_manage;

-- role_report_generate: apenas execução de procedures de relatório
GRANT EXECUTE ON GenerateMonthlyReport TO role_report_generate;
GRANT EXECUTE ON GenerateDepartmentReport TO role_report_generate;

-- Negar acessos perigosos
DENY DELETE ON Employees TO role_employee_read;
DENY DELETE ON Employees TO role_employee_write;
DENY INSERT ON Salaries TO role_salary_manage;

-- Atribuir roles a usuários
ALTER ROLE role_employee_read ADD MEMBER app_user_readonly;
ALTER ROLE role_employee_write ADD MEMBER app_user_editor;
ALTER ROLE role_salary_manage ADD MEMBER hr_manager;
ALTER ROLE role_report_generate ADD MEMBER report_service;
```

### Implementação em PostgreSQL

```sql
-- Criar schemas para isolar funcionalidades
CREATE SCHEMA app_readonly;
CREATE SCHEMA app_write;
CREATE SCHEMA hr_module;

-- Criar roles
CREATE ROLE app_readonly_role;
CREATE ROLE app_write_role;
CREATE ROLE hr_role;

-- Conceder permissões de schema
GRANT USAGE ON SCHEMA app_readonly TO app_readonly_role;
GRANT USAGE ON SCHEMA app_write TO app_write_role;
GRANT USAGE ON SCHEMA hr_module TO hr_role;

-- Criar views de leitura
CREATE VIEW app_readonly.active_employees AS
SELECT employee_id, first_name, last_name, email, department_id
FROM employees
WHERE status = 'ACTIVE';

-- Conceder apenas SELECT nas views
GRANT SELECT ON app_readonly.active_employees TO app_readonly_role;

-- Criar functions de escrita
CREATE FUNCTION app_write.update_employee_contact(
    p_employee_id INT,
    p_email VARCHAR,
    p_phone VARCHAR
)
RETURNS VOID AS $$
BEGIN
    UPDATE employees
    SET email = p_email, phone = p_phone, updated_at = CURRENT_TIMESTAMP
    WHERE employee_id = p_employee_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Conceder EXECUTE na function
GRANT EXECUTE ON FUNCTION app_write.update_employee_contact TO app_write_role;
REVOKE ALL ON employees FROM app_write_role;

-- Negar acesso direto
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_readonly_role;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_write_role;
```

### Implementação em Oracle

```sql
-- Criar roles
CREATE ROLE app_readonly_role;
CREATE ROLE app_write_role;
CREATE ROLE hr_role;

-- Conceder permissões granulares
GRANT SELECT ON hr.employees_v TO app_readonly_role;
GRANT SELECT ON hr.departments TO app_readonly_role;

GRANT SELECT, UPDATE ON hr.employees_v TO app_write_role;
GRANT EXECUTE ON hr.update_employee_contact TO app_write_role;

GRANT SELECT, UPDATE ON hr.salary_history TO hr_role;
GRANT EXECUTE ON hr.calculate_raise TO hr_role;

-- Usar VPD para acesso condicional
CREATE OR REPLACE FUNCTION department_access_policy (
    p_schema IN VARCHAR2,
    p_table  IN VARCHAR2
)
RETURN VARCHAR2
AS
    v_dept_id NUMBER;
BEGIN
    -- Obter departamento do usuário atual
    SELECT department_id INTO v_dept_id
    FROM employees
    WHERE employee_id = SYS_CONTEXT('USERENV', 'SESSION_USER_ID');
    
    RETURN 'department_id = ' || v_dept_id;
END;
/

BEGIN
    DBMS_RLS.ADD_POLICY(
        object_schema   => 'HR',
        object_name     => 'EMPLOYEES',
        policy_name     => 'DEPT_ACCESS',
        function_schema => 'HR',
        policy_function => 'DEPARTMENT_ACCESS_POLICY',
        statement_types => 'SELECT, UPDATE, DELETE',
        update_check    => TRUE
    );
END;
/
```

### Auditoria de Permissões

```sql
-- SQL Server: Verificar permissões concedidas
SELECT 
    pr.name AS Principal,
    pr.type_desc AS PrincipalType,
    p.permission_name,
    p.state_desc AS PermissionState,
    OBJECT_NAME(p.major_id) AS ObjectName,
    p.class_desc AS PermissionClass
FROM sys.database_permissions p
JOIN sys.database_principals pr ON p.grantee_principal_id = pr.principal_id
WHERE pr.name IN ('app_user', 'hr_manager')
ORDER BY pr.name, p.permission_name;

-- PostgreSQL: Verificar permissões
SELECT 
    grantee,
    table_schema,
    table_name,
    privilege_type,
    grantable
FROM information_schema.table_privileges
WHERE grantee IN ('app_readonly_role', 'app_write_role')
ORDER BY grantee, table_name;

-- Oracle: Verificar permissões
SELECT 
    grantee,
    owner,
    table_name,
    privilege,
    grantable
FROM dba_tab_privs
WHERE grantee IN ('APP_READONLY_ROLE', 'APP_WRITE_ROLE')
ORDER BY grantee, table_name;
```

---

## Cursor Security

### O que são Cursores

Cursores permitem iteração linha a linha sobre conjuntos de resultados. Embora úteis, apresentam riscos de segurança e performance.

### Riscos de Segurança com Cursores

1. **SQL injection via cursor declarations** — Dynamic SQL em cursores
2. **Resource exhaustion** — Cursores abertos consomem memória
3. **Lock escalation** — Cursores podem manter locks por muito tempo
4. **Data exposure** — Cursores podem expor dados em memória

### Exemplo de Vulnerabilidade

```sql
-- SQL Server: Cursor VULNERAVEL
CREATE PROCEDURE ProcessUserData
    @UserID INT
AS
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    DECLARE @ColumnName NVARCHAR(100);
    
    -- VULNERAVEL: Dynamic SQL em cursor
    SET @sql = 'DECLARE user_cursor CURSOR FOR SELECT ' + 
               (SELECT TOP 1 ColumnName FROM UserInputs WHERE UserID = @UserID) +
               ' FROM Users WHERE UserID = ' + CAST(@UserID AS NVARCHAR);
    
    EXEC(@sql);
    
    OPEN user_cursor;
    -- ...
    CLOSE user_cursor;
    DEALLOCATE user_cursor;
END;
```

### Padrão Seguro com Cursor

```sql
-- SQL Server: Cursor SEGURO
CREATE PROCEDURE ProcessUserDataSafe
    @UserID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @FirstName NVARCHAR(50);
    DECLARE @LastName NVARCHAR(50);
    DECLARE @Email NVARCHAR(100);
    
    -- Cursor estático e somente leitura para performance e segurança
    DECLARE user_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT FirstName, LastName, Email
        FROM Employees
        WHERE EmployeeID = @UserID;
    
    OPEN user_cursor;
    
    FETCH NEXT FROM user_cursor INTO @FirstName, @LastName, @Email;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        -- Processar dados
        PRINT 'Processing: ' + @FirstName + ' ' + @LastName;
        
        FETCH NEXT FROM user_cursor INTO @FirstName, @LastName, @Email;
    END
    
    CLOSE user_cursor;
    DEALLOCATE user_cursor;
END;
```

### Alternativas a Cursores

```sql
-- SQL Server: Usar JOINs ao invés de cursores
-- INSEGURO (cursor):
DECLARE @product_id INT;
DECLARE product_cursor CURSOR FOR SELECT ProductID FROM Products;
OPEN product_cursor;
FETCH NEXT FROM product_cursor INTO @product_id;
WHILE @@FETCH_STATUS = 0
BEGIN
    UPDATE Products SET Price = Price * 1.1 WHERE ProductID = @product_id;
    FETCH NEXT FROM product_cursor INTO @product_id;
END
CLOSE product_cursor;
DEALLOCATE product_cursor;

-- SEGURO (set-based):
UPDATE Products SET Price = Price * 1.1;

-- Se precisar de lógica complexa, usar CTEs ou funções
WITH PriceUpdate AS (
    SELECT 
        ProductID,
        Price,
        CASE 
            WHEN Category = 'Electronics' THEN Price * 1.1
            WHEN Category = 'Clothing' THEN Price * 1.05
            ELSE Price * 1.02
        END AS NewPrice
    FROM Products
)
UPDATE p
SET p.Price = pu.NewPrice
FROM Products p
JOIN PriceUpdate pu ON p.ProductID = pu.ProductID;
```

### Gestão Segura de Cursores

```sql
-- PostgreSQL: CURSOR SEGURO
CREATE OR REPLACE PROCEDURE process_orders_safe()
LANGUAGE plpgsql
AS $$
DECLARE
    order_record RECORD;
    order_cursor CURSOR FOR
        SELECT order_id, customer_id, total_amount
        FROM orders
        WHERE status = 'PENDING'
        ORDER BY created_at;
BEGIN
    -- Abrir cursor com opções de segurança
    OPEN order_cursor;
    
    LOOP
        FETCH order_cursor INTO order_record;
        EXIT WHEN NOT FOUND;
        
        -- Processar cada pedido
        BEGIN
            UPDATE orders
            SET status = 'PROCESSING',
                processed_at = CURRENT_TIMESTAMP
            WHERE order_id = order_record.order_id;
            
            -- Log da operação
            INSERT INTO order_logs (order_id, action, details)
            VALUES (order_record.order_id, 'PROCESSING', 
                    'Order marked for processing');
                    
        EXCEPTION WHEN OTHERS THEN
            -- Log do erro sem expor detalhes sensíveis
            INSERT INTO order_logs (order_id, action, details)
            VALUES (order_record.order_id, 'ERROR', 
                    'Processing failed');
        END;
    END LOOP;
    
    CLOSE order_cursor;
END;
$$;
```

---

## Package Security (Oracle)

### O que são Packages

Packages no Oracle são contêineres que agrupam procedimentos, funções, variáveis e cursores. Oferecem encapsulamento e controle de visibilidade.

### Estrutura de um Package

```sql
-- Package Specification (visível publicamente)
CREATE OR REPLACE PACKAGE employee_pkg AS
    -- Variáveis públicas (não recomendado para dados sensíveis)
    g_company_name VARCHAR2(100) := 'ACME Corp';
    
    -- Tipos públicos
    TYPE t_employee_record IS RECORD (
        employee_id NUMBER,
        first_name VARCHAR2(50),
        last_name VARCHAR2(50),
        email VARCHAR2(100)
    );
    
    -- Procedures/functions públicas
    PROCEDURE get_employee(
        p_employee_id IN NUMBER,
        p_employee OUT t_employee_record
    );
    
    FUNCTION calculate_bonus(
        p_employee_id IN NUMBER,
        p_performance IN VARCHAR2
    ) RETURN NUMBER;
    
    PROCEDURE update_salary(
        p_employee_id IN NUMBER,
        p_new_salary IN NUMBER
    );
    
END employee_pkg;
/

-- Package Body (implementação)
CREATE OR REPLACE PACKAGE BODY employee_pkg AS
    
    -- Variáveis privadas
    v_session_id VARCHAR2(50);
    
    -- Procedures/functions privadas (não visíveis fora do package)
    PROCEDURE log_change(
        p_table_name VARCHAR2,
        p_operation VARCHAR2,
        p_old_value VARCHAR2,
        p_new_value VARCHAR2
    )
    IS
    BEGIN
        INSERT INTO audit_log (
            table_name, operation, old_value, new_value,
            changed_by, changed_at
        ) VALUES (
            p_table_name, p_operation, p_old_value, p_new_value,
            USER, SYSDATE
        );
    END log_change;
    
    -- Implementação de procedures públicas
    PROCEDURE get_employee(
        p_employee_id IN NUMBER,
        p_employee OUT t_employee_record
    )
    IS
    BEGIN
        SELECT employee_id, first_name, last_name, email
        INTO p_employee
        FROM employees
        WHERE employee_id = p_employee_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20001, 'Employee not found');
    END get_employee;
    
    FUNCTION calculate_bonus(
        p_employee_id IN NUMBER,
        p_performance IN VARCHAR2
    ) RETURN NUMBER
    IS
        v_salary NUMBER;
        v_bonus_pct NUMBER;
    BEGIN
        SELECT salary INTO v_salary
        FROM employees
        WHERE employee_id = p_employee_id;
        
        v_bonus_pct := CASE p_performance
            WHEN 'EXCELLENT' THEN 0.20
            WHEN 'GOOD' THEN 0.10
            WHEN 'AVERAGE' THEN 0.05
            ELSE 0
        END;
        
        RETURN v_salary * v_bonus_pct;
    END calculate_bonus;
    
    PROCEDURE update_salary(
        p_employee_id IN NUMBER,
        p_new_salary IN NUMBER
    )
    IS
        v_old_salary NUMBER;
    BEGIN
        -- Registrar valor antigo
        SELECT salary INTO v_old_salary
        FROM employees
        WHERE employee_id = p_employee_id;
        
        -- Atualizar
        UPDATE employees
        SET salary = p_new_salary,
            updated_at = SYSDATE
        WHERE employee_id = p_employee_id;
        
        -- Log da mudança
        log_change('EMPLOYEES', 'UPDATE', 
                   TO_CHAR(v_old_salary), TO_CHAR(p_new_salary));
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20001, 'Employee not found');
    END update_salary;
    
END employee_pkg;
/
```

### Controle de Acesso em Packages

```sql
-- Conceder apenas EXECUTE no package (não nas procedures individuais)
GRANT EXECUTE ON employee_pkg TO app_role;

-- Revogar acesso direto às tabelas
REVOKE SELECT, INSERT, UPDATE, DELETE ON employees FROM app_role;

-- Usar GRANT OPTION para delegação controlada
GRANT EXECUTE ON employee_pkg TO manager_role WITH GRANT OPTION;

-- Package com pragmas de restrição
CREATE OR REPLACE PACKAGE employee_pkg AS
    -- Procedure pode ser chamada apenas por determinados usuários
    PROCEDURE terminate_employee(
        p_employee_id IN NUMBER,
        p_reason IN VARCHAR2
    );
    
    PRAGMA RESTRICT_REFERENCES(terminate_employee, WNDS, WNPS);
END employee_pkg;
/
```

### Injecao em Packages

```sql
-- Oracle: Package VULNERAVEL
CREATE OR REPLACE PACKAGE search_pkg AS
    PROCEDURE search_employees(p_search VARCHAR2);
END search_pkg;
/

CREATE OR REPLACE PACKAGE BODY search_pkg AS
    PROCEDURE search_employees(p_search VARCHAR2)
    IS
        v_sql VARCHAR2(1000);
    BEGIN
        -- VULNERAVEL: interpolação direta
        v_sql := 'SELECT * FROM employees WHERE first_name LIKE ''%' || p_search || '%''';
        
        EXECUTE IMMEDIATE v_sql;
    END search_employees;
END search_pkg;
/

-- Exploitation
BEGIN
    search_pkg.search_employees("' OR 1=1;--");
END;
/
```

```sql
-- Oracle: Package SEGURO
CREATE OR REPLACE PACKAGE search_pkg AS
    PROCEDURE search_employees(p_search VARCHAR2);
END search_pkg;
/

CREATE OR REPLACE PACKAGE BODY search_pkg AS
    PROCEDURE search_employees(p_search VARCHAR2)
    IS
        v_cursor SYS_REFCURSOR;
        v_result employees%ROWTYPE;
        v_sql VARCHAR2(1000);
    BEGIN
        -- SEGURO: usando BIND variables
        v_sql := 'SELECT * FROM employees WHERE first_name LIKE :search';
        
        OPEN v_cursor FOR v_sql USING '%' || p_search || '%';
        
        LOOP
            FETCH v_cursor INTO v_result;
            EXIT WHEN v_cursor%NOTFOUND;
            -- Processar resultado
        END LOOP;
        
        CLOSE v_cursor;
    END search_employees;
END search_pkg;
/
```

---

## Exemplo: Procedure Segura em PostgreSQL

### Setup Completo

```sql
-- Criar banco de dados e extensões
CREATE DATABASE secure_app;
\c secure_app

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Criar schema para isolamento
CREATE SCHEMA app;
CREATE SCHEMA audit;

-- Criar tabelas
CREATE TABLE app.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock INTEGER DEFAULT 0,
    category VARCHAR(50),
    created_by UUID REFERENCES app.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES app.users(id),
    total_amount DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES app.orders(id),
    product_id UUID REFERENCES app.products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL
);

-- Tabela de auditoria
CREATE TABLE audit.activity_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50),
    record_id UUID,
    action VARCHAR(20),
    old_values JSONB,
    new_values JSONB,
    performed_by UUID,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);
```

### Funções de Segurança

```sql
-- Função para hash de senhas
CREATE OR REPLACE FUNCTION app.hash_password(password TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN crypt(password, gen_salt('bf', 12));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Função para verificar senhas
CREATE OR REPLACE FUNCTION app.verify_password(password TEXT, hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN crypt(password, hash) = hash;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Função para log de auditoria
CREATE OR REPLACE FUNCTION app.log_audit(
    p_table_name VARCHAR,
    p_record_id UUID,
    p_action VARCHAR,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit.activity_log (
        table_name, record_id, action,
        old_values, new_values, performed_by
    ) VALUES (
        p_table_name, p_record_id, p_action,
        p_old_values, p_new_values,
        COALESCE(
            (SELECT id FROM app.users WHERE username = current_user),
            '00000000-0000-0000-0000-000000000000'::UUID
        )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Procedures de Negócio

```sql
-- Procedure: Registrar novo usuário
CREATE OR REPLACE PROCEDURE app.register_user(
    p_username VARCHAR,
    p_email VARCHAR,
    p_password VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Validações
    IF LENGTH(p_username) < 3 OR LENGTH(p_username) > 50 THEN
        RAISE EXCEPTION 'Username must be between 3 and 50 characters';
    END IF;
    
    IF p_email !~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN
        RAISE EXCEPTION 'Invalid email format';
    END IF;
    
    IF LENGTH(p_password) < 8 THEN
        RAISE EXCEPTION 'Password must be at least 8 characters';
    END IF;
    
    -- Verificar se usuário já existe
    IF EXISTS (SELECT 1 FROM app.users WHERE username = p_username) THEN
        RAISE EXCEPTION 'Username already exists';
    END IF;
    
    IF EXISTS (SELECT 1 FROM app.users WHERE email = p_email) THEN
        RAISE EXCEPTION 'Email already exists';
    END IF;
    
    -- Inserir usuário
    INSERT INTO app.users (username, email, password_hash)
    VALUES (p_username, p_email, app.hash_password(p_password))
    RETURNING id INTO v_user_id;
    
    -- Log de auditoria
    PERFORM app.log_audit(
        'users',
        v_user_id,
        'CREATE',
        NULL,
        jsonb_build_object('username', p_username, 'email', p_email)
    );
    
    COMMIT;
END;
$$;

-- Procedure: Login
CREATE OR REPLACE PROCEDURE app.login_user(
    p_username VARCHAR,
    p_password VARCHAR,
    OUT p_user_id UUID,
    OUT p_success BOOLEAN,
    OUT p_message VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user RECORD;
    v_failed_attempts INTEGER;
BEGIN
    -- Verificar tentativas falhas recentes
    SELECT COUNT(*) INTO v_failed_attempts
    FROM audit.activity_log
    WHERE table_name = 'users'
    AND action = 'LOGIN_FAILED'
    AND performed_at > NOW() - INTERVAL '15 minutes'
    AND new_values->>'username' = p_username;
    
    IF v_failed_attempts >= 5 THEN
        p_success := FALSE;
        p_message := 'Account temporarily locked due to too many failed attempts';
        RETURN;
    END IF;
    
    -- Buscar usuário
    SELECT id, password_hash, is_active INTO v_user
    FROM app.users
    WHERE username = p_username;
    
    -- Verificar se usuário existe
    IF NOT FOUND THEN
        p_success := FALSE;
        p_message := 'Invalid credentials';
        
        -- Log de tentativa falha (sem expor se usuário existe)
        PERFORM app.log_audit(
            'users',
            NULL,
            'LOGIN_FAILED',
            NULL,
            jsonb_build_object('username', p_username)
        );
        RETURN;
    END IF;
    
    -- Verificar se conta está ativa
    IF NOT v_user.is_active THEN
        p_success := FALSE;
        p_message := 'Account is disabled';
        RETURN;
    END IF;
    
    -- Verificar senha
    IF NOT app.verify_password(p_password, v_user.password_hash) THEN
        p_success := FALSE;
        p_message := 'Invalid credentials';
        
        PERFORM app.log_audit(
            'users',
            v_user.id,
            'LOGIN_FAILED',
            NULL,
            jsonb_build_object('username', p_username)
        );
        RETURN;
    END IF;
    
    -- Login bem-sucedido
    p_user_id := v_user.id;
    p_success := TRUE;
    p_message := 'Login successful';
    
    PERFORM app.log_audit(
        'users',
        v_user.id,
        'LOGIN',
        NULL,
        jsonb_build_object('username', p_username)
    );
END;
$$;

-- Procedure: Criar produto (apenas admin)
CREATE OR REPLACE PROCEDURE app.create_product(
    p_name VARCHAR,
    p_description TEXT,
    p_price DECIMAL,
    p_stock INTEGER,
    p_category VARCHAR
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_product_id UUID;
    v_user_role VARCHAR;
BEGIN
    -- Verificar permissão (assumindo contexto de sessão)
    SELECT role INTO v_user_role
    FROM app.users
    WHERE username = current_user;
    
    IF v_user_role != 'admin' THEN
        RAISE EXCEPTION 'Insufficient permissions';
    END IF;
    
    -- Validações
    IF p_price <= 0 THEN
        RAISE EXCEPTION 'Price must be positive';
    END IF;
    
    IF p_stock < 0 THEN
        RAISE EXCEPTION 'Stock cannot be negative';
    END IF;
    
    -- Inserir produto
    INSERT INTO app.products (name, description, price, stock, category, created_by)
    VALUES (p_name, p_description, p_price, p_stock, p_category,
            (SELECT id FROM app.users WHERE username = current_user))
    RETURNING id INTO v_product_id;
    
    -- Log de auditoria
    PERFORM app.log_audit(
        'products',
        v_product_id,
        'CREATE',
        NULL,
        jsonb_build_object(
            'name', p_name,
            'price', p_price,
            'stock', p_stock
        )
    );
END;
$$;

-- Procedure: Criar pedido
CREATE OR REPLACE PROCEDURE app.create_order(
    p_user_id UUID,
    p_items JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id UUID;
    v_total DECIMAL := 0;
    v_item JSONB;
    v_product RECORD;
    v_stock_available INTEGER;
BEGIN
    -- Criar pedido
    INSERT INTO app.orders (user_id, status)
    VALUES (p_user_id, 'pending')
    RETURNING id INTO v_order_id;
    
    -- Processar itens
    FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
    LOOP
        -- Verificar produto e estoque
        SELECT id, price, stock INTO v_product
        FROM app.products
        WHERE id = (v_item->>'product_id')::UUID
        FOR UPDATE;
        
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Product not found: %', v_item->>'product_id';
        END IF;
        
        IF v_product.stock < (v_item->>'quantity')::INTEGER THEN
            RAISE EXCEPTION 'Insufficient stock for product %', v_product.id;
        END IF;
        
        -- Adicionar item
        INSERT INTO app.order_items (order_id, product_id, quantity, unit_price)
        VALUES (
            v_order_id,
            v_product.id,
            (v_item->>'quantity')::INTEGER,
            v_product.price
        );
        
        -- Atualizar estoque
        UPDATE app.products
        SET stock = stock - (v_item->>'quantity')::INTEGER
        WHERE id = v_product.id;
        
        -- Calcular total
        v_total := v_total + (v_product.price * (v_item->>'quantity')::INTEGER);
    END LOOP;
    
    -- Atualizar total do pedido
    UPDATE app.orders
    SET total_amount = v_total
    WHERE id = v_order_id;
    
    -- Log de auditoria
    PERFORM app.log_audit(
        'orders',
        v_order_id,
        'CREATE',
        NULL,
        jsonb_build_object('total', v_total, 'items', p_items)
    );
    
    COMMIT;
END;
$$;

-- Procedure: Relatório de vendas (apenas para roles autorizadas)
CREATE OR REPLACE PROCEDURE app.generate_sales_report(
    p_start_date DATE,
    p_end_date DATE,
    p_category VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_role VARCHAR;
    v_report JSONB;
BEGIN
    -- Verificar permissão
    SELECT role INTO v_user_role
    FROM app.users
    WHERE username = current_user;
    
    IF v_user_role NOT IN ('admin', 'manager') THEN
        RAISE EXCEPTION 'Insufficient permissions for reports';
    END IF;
    
    -- Gerar relatório
    SELECT jsonb_build_object(
        'period', jsonb_build_object('start', p_start_date, 'end', p_end_date),
        'total_orders', COUNT(DISTINCT o.id),
        'total_revenue', SUM(oi.quantity * oi.unit_price),
        'avg_order_value', AVG(o.total_amount),
        'top_products', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', p.name,
                    'total_sold', SUM(oi.quantity),
                    'revenue', SUM(oi.quantity * oi.unit_price)
                )
            )
            FROM app.order_items oi
            JOIN app.products p ON oi.product_id = p.id
            JOIN app.orders o ON oi.order_id = o.id
            WHERE o.created_at BETWEEN p_start_date AND p_end_date
            AND (p_category IS NULL OR p.category = p_category)
            GROUP BY p.name
            ORDER BY SUM(oi.quantity) DESC
            LIMIT 10
        )
    ) INTO v_report
    FROM app.orders o
    JOIN app.order_items oi ON o.id = oi.order_id
    WHERE o.created_at BETWEEN p_start_date AND p_end_date;
    
    -- Log de auditoria
    PERFORM app.log_audit(
        'reports',
        NULL,
        'GENERATE_SALES_REPORT',
        NULL,
        jsonb_build_object('start_date', p_start_date, 'end_date', p_end_date)
    );
    
    RAISE NOTICE '%', v_report;
END;
$$;
```

### Triggers de Auditoria

```sql
-- Trigger para auditoria automática em users
CREATE OR REPLACE FUNCTION app.audit_users()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM app.log_audit(
            'users',
            NEW.id,
            'CREATE',
            NULL,
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM app.log_audit(
            'users',
            NEW.id,
            'UPDATE',
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM app.log_audit(
            'users',
            OLD.id,
            'DELETE',
            to_jsonb(OLD),
            NULL
        );
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_users
AFTER INSERT OR UPDATE OR DELETE ON app.users
FOR EACH ROW EXECUTE FUNCTION app.audit_users();

-- Trigger para auditoria em products
CREATE OR REPLACE FUNCTION app.audit_products()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM app.log_audit(
            'products',
            NEW.id,
            'CREATE',
            NULL,
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        PERFORM app.log_audit(
            'products',
            NEW.id,
            'UPDATE',
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM app.log_audit(
            'products',
            OLD.id,
            'DELETE',
            to_jsonb(OLD),
            NULL
        );
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_products
AFTER INSERT OR UPDATE OR DELETE ON app.products
FOR EACH ROW EXECUTE FUNCTION app.audit_products();
```

### Controle de Acesso

```sql
-- Criar roles de aplicação
CREATE ROLE app_readonly;
CREATE ROLE app_user;
CREATE ROLE app_admin;

-- Conceder permissões por role

-- app_readonly: apenas leitura
GRANT USAGE ON SCHEMA app TO app_readonly;
GRANT SELECT ON app.users TO app_readonly;
GRANT SELECT ON app.products TO app_readonly;
GRANT SELECT ON app.orders TO app_readonly;
GRANT SELECT ON app.order_items TO app_readonly;

-- app_user: leitura + escrita limitada
GRANT USAGE ON SCHEMA app TO app_user;
GRANT SELECT, INSERT ON app.users TO app_user;
GRANT SELECT ON app.products TO app_user;
GRANT SELECT, INSERT ON app.orders TO app_user;
GRANT SELECT, INSERT ON app.order_items TO app_user;
GRANT EXECUTE ON PROCEDURE app.register_user TO app_user;
GRANT EXECUTE ON PROCEDURE app.create_order TO app_user;

-- app_admin: acesso total ao schema app
GRANT ALL ON SCHEMA app TO app_admin;
GRANT ALL ON ALL TABLES IN SCHEMA app TO app_admin;
GRANT ALL ON ALL PROCEDURES IN SCHEMA app TO app_admin;

-- Negar acesso a schemas sensíveis
REVOKE ALL ON SCHEMA audit FROM app_readonly;
REVOKE ALL ON SCHEMA audit FROM app_user;

-- Conceder apenas visualização de logs para admins
GRANT USAGE ON SCHEMA audit TO app_admin;
GRANT SELECT ON audit.activity_log TO app_admin;

-- Conectar roles a usuários do banco
GRANT app_readonly TO readonly_user;
GRANT app_user TO app_service;
GRANT app_admin TO admin_user;
```

---

## Exemplo: Procedure Segura em SQL Server

### Setup Completo

```sql
-- Criar banco de dados
CREATE DATABASE SecureApp;
GO

USE SecureApp;
GO

-- Criar tabelas
CREATE TABLE dbo.Users (
    UserID INT PRIMARY KEY IDENTITY(1,1),
    Username NVARCHAR(50) UNIQUE NOT NULL,
    Email NVARCHAR(100) UNIQUE NOT NULL,
    PasswordHash NVARCHAR(255) NOT NULL,
    Salt NVARCHAR(50) NOT NULL,
    Role NVARCHAR(20) DEFAULT 'User',
    IsActive BIT DEFAULT 1,
    FailedLoginAttempts INT DEFAULT 0,
    LastFailedLogin DATETIME NULL,
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE dbo.Products (
    ProductID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX),
    Price DECIMAL(18,2) NOT NULL,
    Stock INT DEFAULT 0,
    Category NVARCHAR(50),
    CreatedBy INT REFERENCES Users(UserID),
    CreatedAt DATETIME DEFAULT GETDATE(),
    UpdatedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE dbo.Orders (
    OrderID INT PRIMARY KEY IDENTITY(1,1),
    UserID INT REFERENCES Users(UserID),
    TotalAmount DECIMAL(18,2),
    Status NVARCHAR(20) DEFAULT 'Pending',
    CreatedAt DATETIME DEFAULT GETDATE()
);

CREATE TABLE dbo.OrderItems (
    OrderItemID INT PRIMARY KEY IDENTITY(1,1),
    OrderID INT REFERENCES Orders(OrderID),
    ProductID INT REFERENCES Products(ProductID),
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(18,2) NOT NULL
);

-- Tabela de auditoria
CREATE TABLE dbo.AuditLog (
    AuditID BIGINT PRIMARY KEY IDENTITY(1,1),
    TableName NVARCHAR(50),
    RecordID INT,
    Action NVARCHAR(20),
    OldValues NVARCHAR(MAX),
    NewValues NVARCHAR(MAX),
    PerformedBy NVARCHAR(50),
    PerformedAt DATETIME DEFAULT GETDATE(),
    IPAddress NVARCHAR(50)
);
```

### Procedures de Segurança

```sql
-- Função para hash de senhas
CREATE FUNCTION dbo.HashPassword(@Password NVARCHAR(100), @Salt NVARCHAR(50))
RETURNS NVARCHAR(255)
AS
BEGIN
    DECLARE @Hash NVARCHAR(255);
    SET @Hash = HASHBYTES('SHA2_256', @Password + @Salt);
    RETURN @Hash;
END;
GO

-- Procedimento de registro
CREATE PROCEDURE dbo.RegisterUser
    @Username NVARCHAR(50),
    @Email NVARCHAR(100),
    @Password NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @Salt NVARCHAR(50);
    DECLARE @PasswordHash NVARCHAR(255);
    DECLARE @UserID INT;
    
    -- Validações
    IF LEN(@Username) < 3 OR LEN(@Username) > 50
    BEGIN
        RAISERROR('Username must be between 3 and 50 characters', 16, 1);
        RETURN;
    END
    
    IF @Email NOT LIKE '%_@__%.__%'
    BEGIN
        RAISERROR('Invalid email format', 16, 1);
        RETURN;
    END
    
    IF LEN(@Password) < 8
    BEGIN
        RAISERROR('Password must be at least 8 characters', 16, 1);
        RETURN;
    END
    
    -- Verificar se usuário já existe
    IF EXISTS (SELECT 1 FROM Users WHERE Username = @Username)
    BEGIN
        RAISERROR('Username already exists', 16, 1);
        RETURN;
    END
    
    IF EXISTS (SELECT 1 FROM Users WHERE Email = @Email)
    BEGIN
        RAISERROR('Email already exists', 16, 1);
        RETURN;
    END
    
    -- Gerar salt e hash
    SET @Salt = CONVERT(NVARCHAR(50), NEWID());
    SET @PasswordHash = dbo.HashPassword(@Password, @Salt);
    
    -- Inserir usuário
    INSERT INTO Users (Username, Email, PasswordHash, Salt)
    VALUES (@Username, @Email, @PasswordHash, @Salt);
    
    SET @UserID = SCOPE_IDENTITY();
    
    -- Log de auditoria
    INSERT INTO AuditLog (TableName, RecordID, Action, NewValues)
    VALUES ('Users', @UserID, 'CREATE', 
            '{"username":"' + @Username + '","email":"' + @Email + '"}');
END;
GO

-- Procedimento de login
CREATE PROCEDURE dbo.LoginUser
    @Username NVARCHAR(50),
    @Password NVARCHAR(100),
    @UserID INT OUTPUT,
    @Success BIT OUTPUT,
    @Message NVARCHAR(100) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @StoredHash NVARCHAR(255);
    DECLARE @Salt NVARCHAR(50);
    DECLARE @IsActive BIT;
    DECLARE @FailedAttempts INT;
    DECLARE @LastFailed DATETIME;
    
    -- Verificar tentativas falhas recentes
    SELECT @FailedAttempts = FailedLoginAttempts,
           @LastFailed = LastFailedLogin
    FROM Users
    WHERE Username = @Username;
    
    IF @FailedAttempts >= 5 AND DATEDIFF(MINUTE, @LastFailed, GETDATE()) < 15
    BEGIN
        SET @Success = 0;
        SET @Message = 'Account temporarily locked';
        RETURN;
    END
    
    -- Buscar dados do usuário
    SELECT @StoredHash = PasswordHash,
           @Salt = Salt,
           @IsActive = IsActive,
           @UserID = UserID
    FROM Users
    WHERE Username = @Username;
    
    -- Verificar se usuário existe
    IF @UserID IS NULL
    BEGIN
        SET @Success = 0;
        SET @Message = 'Invalid credentials';
        
        INSERT INTO AuditLog (TableName, Action, NewValues)
        VALUES ('Users', 'LOGIN_FAILED', '{"username":"' + @Username + '"}');
        RETURN;
    END
    
    -- Verificar se conta está ativa
    IF @IsActive = 0
    BEGIN
        SET @Success = 0;
        SET @Message = 'Account is disabled';
        RETURN;
    END
    
    -- Verificar senha
    IF dbo.HashPassword(@Password, @Salt) != @StoredHash
    BEGIN
        -- Incrementar tentativas falhas
        UPDATE Users
        SET FailedLoginAttempts = FailedLoginAttempts + 1,
            LastFailedLogin = GETDATE()
        WHERE UserID = @UserID;
        
        SET @Success = 0;
        SET @Message = 'Invalid credentials';
        
        INSERT INTO AuditLog (TableName, RecordID, Action, NewValues)
        VALUES ('Users', @UserID, 'LOGIN_FAILED', 
                '{"username":"' + @Username + '"}');
        RETURN;
    END
    
    -- Login bem-sucedido - resetar tentativas
    UPDATE Users
    SET FailedLoginAttempts = 0,
        LastFailedLogin = NULL
    WHERE UserID = @UserID;
    
    SET @Success = 1;
    SET @Message = 'Login successful';
    
    INSERT INTO AuditLog (TableName, RecordID, Action, NewValues)
    VALUES ('Users', @UserID, 'LOGIN', 
            '{"username":"' + @Username + '"}');
END;
GO

-- Procedimento para criar produto (apenas admin)
CREATE PROCEDURE dbo.CreateProduct
    @Name NVARCHAR(200),
    @Description NVARCHAR(MAX),
    @Price DECIMAL(18,2),
    @Stock INT,
    @Category NVARCHAR(50),
    @CreatedBy INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @UserRole NVARCHAR(20);
    DECLARE @ProductID INT;
    
    -- Verificar permissão
    SELECT @UserRole = Role FROM Users WHERE UserID = @CreatedBy;
    
    IF @UserRole != 'Admin'
    BEGIN
        RAISERROR('Insufficient permissions', 16, 1);
        RETURN;
    END
    
    -- Validações
    IF @Price <= 0
    BEGIN
        RAISERROR('Price must be positive', 16, 1);
        RETURN;
    END
    
    IF @Stock < 0
    BEGIN
        RAISERROR('Stock cannot be negative', 16, 1);
        RETURN;
    END
    
    -- Inserir produto
    INSERT INTO Products (Name, Description, Price, Stock, Category, CreatedBy)
    VALUES (@Name, @Description, @Price, @Stock, @Category, @CreatedBy);
    
    SET @ProductID = SCOPE_IDENTITY();
    
    -- Log de auditoria
    INSERT INTO AuditLog (TableName, RecordID, Action, NewValues)
    VALUES ('Products', @ProductID, 'CREATE', 
            '{"name":"' + @Name + '","price":' + CAST(@Price AS NVARCHAR) + 
            ',"stock":' + CAST(@Stock AS NVARCHAR) + '}');
END;
GO

-- Procedimento para criar pedido
CREATE PROCEDURE dbo.CreateOrder
    @UserID INT,
    @Items NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @OrderID INT;
    DECLARE @TotalAmount DECIMAL(18,2) = 0;
    DECLARE @ProductID INT;
    DECLARE @Quantity INT;
    DECLARE @UnitPrice DECIMAL(18,2);
    DECLARE @StockAvailable INT;
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- Criar pedido
        INSERT INTO Orders (UserID, Status)
        VALUES (@UserID, 'Pending');
        
        SET @OrderID = SCOPE_IDENTITY();
        
        -- Processar itens (simplificado - em produção usar JSON parsing)
        DECLARE item_cursor CURSOR FOR
            SELECT ProductID, Quantity FROM OPENJSON(@Items)
            WITH (ProductID INT, Quantity INT);
        
        OPEN item_cursor;
        FETCH NEXT FROM item_cursor INTO @ProductID, @Quantity;
        
        WHILE @@FETCH_STATUS = 0
        BEGIN
            -- Verificar produto e estoque
            SELECT @UnitPrice = Price, @StockAvailable = Stock
            FROM Products
            WHERE ProductID = @ProductID;
            
            IF @UnitPrice IS NULL
            BEGIN
                RAISERROR('Product not found', 16, 1);
                ROLLBACK;
                RETURN;
            END
            
            IF @StockAvailable < @Quantity
            BEGIN
                RAISERROR('Insufficient stock', 16, 1);
                ROLLBACK;
                RETURN;
            END
            
            -- Adicionar item
            INSERT INTO OrderItems (OrderID, ProductID, Quantity, UnitPrice)
            VALUES (@OrderID, @ProductID, @Quantity, @UnitPrice);
            
            -- Atualizar estoque
            UPDATE Products
            SET Stock = Stock - @Quantity
            WHERE ProductID = @ProductID;
            
            -- Calcular total
            SET @TotalAmount = @TotalAmount + (@UnitPrice * @Quantity);
            
            FETCH NEXT FROM item_cursor INTO @ProductID, @Quantity;
        END
        
        CLOSE item_cursor;
        DEALLOCATE item_cursor;
        
        -- Atualizar total do pedido
        UPDATE Orders
        SET TotalAmount = @TotalAmount
        WHERE OrderID = @OrderID;
        
        -- Log de auditoria
        INSERT INTO AuditLog (TableName, RecordID, Action, NewValues)
        VALUES ('Orders', @OrderID, 'CREATE', 
                '{"total":' + CAST(@TotalAmount AS NVARCHAR) + '}');
        
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK;
        
        -- Log do erro
        INSERT INTO AuditLog (TableName, Action, NewValues)
        VALUES ('Orders', 'ERROR', 
                '{"error":"' + ERROR_MESSAGE() + '"}');
        
        THROW;
    END CATCH
END;
GO

-- Procedimento de relatório de vendas
CREATE PROCEDURE dbo.GenerateSalesReport
    @StartDate DATE,
    @EndDate DATE,
    @Category NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @UserRole NVARCHAR(20);
    
    -- Verificar permissão (assumindo contexto de sessão)
    SELECT @UserRole = Role 
    FROM Users 
    WHERE Username = SYSTEM_USER;
    
    IF @UserRole NOT IN ('Admin', 'Manager')
    BEGIN
        RAISERROR('Insufficient permissions for reports', 16, 1);
        RETURN;
    END
    
    -- Resumo geral
    SELECT 
        COUNT(DISTINCT o.OrderID) AS TotalOrders,
        SUM(oi.Quantity * oi.UnitPrice) AS TotalRevenue,
        AVG(o.TotalAmount) AS AvgOrderValue
    FROM Orders o
    JOIN OrderItems oi ON o.OrderID = oi.OrderID
    WHERE o.CreatedAt BETWEEN @StartDate AND @EndDate;
    
    -- Top produtos
    SELECT TOP 10
        p.Name,
        SUM(oi.Quantity) AS TotalSold,
        SUM(oi.Quantity * oi.UnitPrice) AS Revenue
    FROM OrderItems oi
    JOIN Products p ON oi.ProductID = p.ProductID
    JOIN Orders o ON oi.OrderID = o.OrderID
    WHERE o.CreatedAt BETWEEN @StartDate AND @EndDate
    AND (@Category IS NULL OR p.Category = @Category)
    GROUP BY p.Name
    ORDER BY SUM(oi.Quantity) DESC;
    
    -- Log de auditoria
    INSERT INTO AuditLog (TableName, Action, NewValues)
    VALUES ('Reports', 'GENERATE_SALES_REPORT', 
            '{"start":"' + CAST(@StartDate AS NVARCHAR) + 
            '","end":"' + CAST(@EndDate AS NVARCHAR) + '"}');
END;
GO
```

### Controle de Acesso

```sql
-- Criar roles
CREATE ROLE db_executor;
CREATE ROLE db_reader;
CREATE ROLE db_writer;
CREATE ROLE db_admin;

-- Conceder permissões

-- db_executor: executar procedures específicas
GRANT EXECUTE ON dbo.RegisterUser TO db_executor;
GRANT EXECUTE ON dbo.LoginUser TO db_executor;
GRANT EXECUTE ON dbo.CreateOrder TO db_executor;

-- db_reader: leitura de dados
GRANT SELECT ON dbo.Users TO db_reader;
GRANT SELECT ON dbo.Products TO db_reader;
GRANT SELECT ON dbo.Orders TO db_reader;
GRANT SELECT ON dbo.OrderItems TO db_reader;

-- db_writer: escrita de dados
GRANT INSERT, UPDATE ON dbo.Users TO db_writer;
GRANT INSERT, UPDATE ON dbo.Products TO db_writer;
GRANT INSERT, UPDATE ON dbo.Orders TO db_writer;
GRANT INSERT, UPDATE ON dbo.OrderItems TO db_writer;
GRANT EXECUTE ON dbo.CreateProduct TO db_writer;

-- db_admin: acesso administrativo
GRANT ALL ON dbo.Users TO db_admin;
GRANT ALL ON dbo.Products TO db_admin;
GRANT ALL ON dbo.Orders TO db_admin;
GRANT ALL ON dbo.OrderItems TO db_admin;
GRANT ALL ON dbo.AuditLog TO db_admin;
GRANT EXECUTE ON dbo.GenerateSalesReport TO db_admin;

-- Negar acessos perigosos
DENY DELETE ON dbo.Users TO db_writer;
DENY DELETE ON dbo.Products TO db_writer;
DENY DELETE ON dbo.Orders TO db_writer;

-- Atribuir roles a usuários
ALTER ROLE db_executor ADD MEMBER app_service;
ALTER ROLE db_reader ADD MEMBER readonly_user;
ALTER ROLE db_writer ADD MEMBER editor_user;
ALTER ROLE db_admin ADD MEMBER admin_user;
GO
```

---

## Auditing de Procedures

### Por que Auditar Stored Procedures

1. **Detecção de alterações não autorizadas** — mudanças em procedures podem indicar comprometimento
2. **Conformidade regulatória** — muitos frameworks exigem auditoria de código executável
3. **Rastreabilidade** — saber quem alterou o quê e quando
4. **Debug e troubleshooting** — histórico de mudanças para resolver problemas

### Auditoria de Alterações em Procedures

**SQL Server:**

```sql
-- Trigger de auditoria para procedures
CREATE TRIGGER trg_AuditStoredProcedures
ON sys.procedures
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @Action NVARCHAR(10);
    DECLARE @ProcedureName NVARCHAR(256);
    DECLARE @Definition NVARCHAR(MAX);
    
    IF EXISTS (SELECT 1 FROM inserted)
    BEGIN
        IF EXISTS (SELECT 1 FROM deleted)
            SET @Action = 'MODIFY';
        ELSE
            SET @Action = 'CREATE';
        
        SELECT @ProcedureName = name
        FROM inserted;
        
        SELECT @Definition = OBJECT_DEFINITION(object_id)
        FROM inserted;
    END
    ELSE
    BEGIN
        SET @Action = 'DROP';
        
        SELECT @ProcedureName = name
        FROM deleted;
    END
    
    INSERT INTO AuditLog (TableName, Action, NewValues, PerformedBy)
    VALUES ('sys.procedures', @Action,
            '{"procedure":"' + @ProcedureName + '"}',
            SYSTEM_USER);
END;
GO
```

**PostgreSQL:**

```sql
-- Extensão para auditoria
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- Configurar auditoria
ALTER SYSTEM SET pgaudit.log = 'ddl, role, write';
ALTER SYSTEM SET pgaudit.log_catalog = on;
ALTER SYSTEM SET pgaudit.log_level = 'log';

-- Reiniciar para aplicar
-- pg_ctl reload

-- Verificar logs
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_catalog.pg_stat_activity;
```

**Oracle:**

```sql
-- Habilitar auditing
AUDIT ALTER SYSTEM BY ACCESS;
AUDIT SYSTEM AUDIT BY ACCESS;

-- Auditar alterações em objetos
AUDIT CREATE TABLE, ALTER TABLE, DROP TABLE BY ACCESS;
AUDIT CREATE PROCEDURE, ALTER PROCEDURE, DROP PROCEDURE BY ACCESS;

-- Auditar execuções
AUDIT EXECUTE ON hr.employee_pkg BY ACCESS;

-- Verificar audit trail
SELECT * FROM DBA_AUDIT_TRAIL
WHERE OBJECT_NAME = 'EMPLOYEE_PKG'
ORDER BY TIMESTAMP DESC;

-- Relatório de auditoria
SELECT 
    USERNAME,
    TIMESTAMP,
    ACTION_NAME,
    OBJECT_NAME,
    SQL_TEXT
FROM DBA_AUDIT_TRAIL
WHERE OBJECT_NAME LIKE '%PKG%'
AND TIMESTAMP > SYSDATE - 30
ORDER BY TIMESTAMP DESC;
```

### Verificação de Integridade

```sql
-- SQL Server: Verificar integridade das procedures
CREATE PROCEDURE dbo.VerifyProcedureIntegrity
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        name AS ProcedureName,
        create_date,
        modify_date,
        OBJECT_DEFINITION(object_id) AS Definition,
        LEN(OBJECT_DEFINITION(object_id)) AS DefinitionLength
    FROM sys.procedures
    WHERE is_ms_shipped = 0
    ORDER BY modify_date DESC;
END;
GO

-- PostgreSQL: Verificar integridade
CREATE OR REPLACE FUNCTION audit.verify_procedure_integrity()
RETURNS TABLE (
    procedure_name TEXT,
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    definition TEXT,
    definition_length INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.proname::TEXT,
        pg_catalog.pg_stat_get_last_autoanalyze_time(p.oid),
        pg_catalog.pg_stat_get_last_analyze_time(p.oid),
        pg_catalog.pg_get_functiondef(p.oid),
        LENGTH(pg_catalog.pg_get_functiondef(p.oid))
    FROM pg_catalog.pg_proc p
    WHERE p.pronamespace = 'app'::regnamespace
    ORDER BY p.proname;
END;
$$;
```

### Dashboard de Auditoria

```sql
-- SQL Server: Dashboard de auditoria
CREATE VIEW vw_AuditDashboard
AS
SELECT 
    CAST(PerformedAt AS DATE) AS AuditDate,
    TableName,
    Action,
    COUNT(*) AS ChangeCount,
    MIN(PerformedAt) AS FirstChange,
    MAX(PerformedAt) AS LastChange
FROM AuditLog
WHERE PerformedAt > DATEADD(DAY, -30, GETDATE())
GROUP BY CAST(PerformedAt AS DATE), TableName, Action;
GO

-- Relatório de procedures mais alteradas
CREATE VIEW vw_MostChangedProcedures
AS
SELECT TOP 10
    TableName AS ProcedureName,
    COUNT(*) AS ChangeCount,
    MIN(PerformedAt) AS FirstChange,
    MAX(PerformedAt) AS LastChange
FROM AuditLog
WHERE TableName LIKE '%Procedure%'
OR TableName LIKE '%Function%'
OR TableName LIKE '%Package%'
GROUP BY TableName
ORDER BY COUNT(*) DESC;
GO

-- Relatório de usuários mais ativos
CREATE VIEW vw_MostActiveUsers
AS
SELECT TOP 10
    PerformedBy,
    COUNT(*) AS ActionCount,
    COUNT(DISTINCT TableName) AS ObjectsChanged,
    MIN(PerformedAt) AS FirstAction,
    MAX(PerformedAt) AS LastAction
FROM AuditLog
WHERE PerformedAt > DATEADD(DAY, -30, GETDATE())
GROUP BY PerformedBy
ORDER BY COUNT(*) DESC;
GO
```

---

## Resumo

### Pontos-Chave

1. **Stored procedures são uma defesa poderosa contra SQL injection** quando implementadas corretamente
2. **Dynamic SQL é necessário mas perigoso** — sempre usar sp_executesql, EXECUTE IMMEDIATE ou EXECUTE com parâmetros
3. **Least privilege é fundamental** — conceder apenas EXECUTE nas procedures, não acesso direto às tabelas
4. **Packages no Oracle oferecem encapsulamento** — procedures privadas não são acessíveis externamente
5. **Cursores devem ser evitados quando possível** — usar operações baseadas em conjuntos
6. **Auditoria é obrigatória** — rastrear alterações em procedures e logs de execução

### Checklist de Segurança

- [ ] Procedures usam parâmetros (não interpolação)
- [ ] Dynamic SQL usa sp_executesql/EXECUTE IMMEDIATE com BIND variables
- [ ] Least privilege implementado (apenas EXECUTE)
- [ ] Validação de entrada em todas as procedures
- [ ] Tratamento de erros adequado (TRY/CATCH)
- [ ] Auditoria de alterações habilitada
- [ ] Triggers de auditoria em procedures críticas
- [ ] Verificação de integridade periódica
- [ ] Senhas nunca armazenadas em texto plano
- [ ] Roles de aplicação separadas de usuários administrativos

### Referências

- OWASP SQL Injection Prevention Cheat Sheet
- Microsoft: Using sp_executesql
- Oracle: EXECUTE IMMEDIATE
- PostgreSQL: Dynamic SQL
- NIST SP 800-53: System and Information Integrity

---

## Testes de Segurança para Stored Procedures

### Metodologia de Teste

O teste de segurança para stored procedures requer abordagem específica que considere a natureza do código executado no servidor de banco de dados.

**Fase 1: Análise Estática**

```python
class SPStaticAnalyzer:
    """Analisador estático para stored procedures"""
    
    def __init__(self):
        self.vulnerabilities = []
        self.patterns = {
            'dynamic_sql': [
                r'EXEC\s*\(',
                r'EXEC\s*@',
                r'sp_executesql\s+@',
                r'EXECUTE\s+IMMEDIATE\s+\'',
                r'EXECUTE\s+IMMEDIATE\s+\|\|'
            ],
            'string_concatenation': [
                r'CONCAT\s*\(.*SELECT',
                r"'\s*\|\|.*SELECT",
                r'SET\s+@\w+\s*=\s*\'.*SELECT'
            ],
            'sensitive_data': [
                r'password',
                r'secret',
                r'token',
                r'credential',
                r'private_key'
            ]
        }
    
    def analyze_procedure(self, name, body):
        """Analisa uma procedure"""
        findings = []
        lines = body.split('\n')
        
        for i, line in enumerate(lines, 1):
            for vuln_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            'procedure': name,
                            'line': i,
                            'type': vuln_type,
                            'code': line.strip(),
                            'severity': self._get_severity(vuln_type)
                        })
        
        return findings
    
    def _get_severity(self, vuln_type):
        """Retorna severidade baseado no tipo"""
        severity_map = {
            'dynamic_sql': 'HIGH',
            'string_concatenation': 'HIGH',
            'sensitive_data': 'MEDIUM'
        }
        return severity_map.get(vuln_type, 'LOW')
```

**Fase 2: Teste Dinâmico**

```python
class SPDynamicTester:
    """Testador dinâmico para stored procedures"""
    
    def __init__(self, db_connection):
        self.conn = db_connection
    
    def test_sql_injection(self, procedure_name, params):
        """Testa SQL injection em procedures"""
        test_payloads = [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "'; EXEC xp_cmdshell('whoami');--",
            "1; SELECT * FROM sensitive_table--",
            "' UNION SELECT username, password FROM users--"
        ]
        
        results = []
        
        for param_name, param_value in params.items():
            for payload in test_payloads:
                test_params = params.copy()
                test_params[param_name] = payload
                
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(f"EXEC {procedure_name}", test_params)
                    result = cursor.fetchone()
                    
                    if result:
                        results.append({
                            'procedure': procedure_name,
                            'param': param_name,
                            'payload': payload,
                            'status': 'VULNERABLE',
                            'result': str(result)
                        })
                    else:
                        results.append({
                            'procedure': procedure_name,
                            'param': param_name,
                            'payload': payload,
                            'status': 'SAFE'
                        })
                        
                except Exception as e:
                    if 'conversion' in str(e).lower():
                        results.append({
                            'procedure': procedure_name,
                            'param': param_name,
                            'payload': payload,
                            'status': 'SAFE',
                            'note': 'Parameter validation working'
                        })
                    else:
                        results.append({
                            'procedure': procedure_name,
                            'param': param_name,
                            'payload': payload,
                            'status': 'ERROR',
                            'error': str(e)
                        })
        
        return results
    
    def test_permission_escalation(self, procedure_name, low_priv_user):
        """Testa escalonamento de privilégios"""
        try:
            cursor = self.conn.cursor()
            
            # Conectar com usuário de baixo privilégio
            cursor.execute(f"EXECUTE AS USER = '{low_priv_user}'")
            
            # Tentar executar procedure
            cursor.execute(f"EXEC {procedure_name}")
            
            # Verificar se pode acessar dados sensíveis
            cursor.execute("SELECT * FROM sensitive_table")
            result = cursor.fetchone()
            
            if result:
                return {
                    'procedure': procedure_name,
                    'status': 'VULNERABLE',
                    'note': 'Low-privilege user accessed sensitive data'
                }
            
            return {
                'procedure': procedure_name,
                'status': 'SAFE'
            }
            
        except Exception as e:
            return {
                'procedure': procedure_name,
                'status': 'BLOCKED',
                'note': str(e)
            }
```

### Automação de Testes

```python
# Script completo de teste de stored procedures
import pyodbc
import json
from datetime import datetime

class SPTestSuite:
    """Suite completa de testes para stored procedures"""
    
    def __init__(self, connection_string):
        self.conn = pyodbc.connect(connection_string)
        self.results = []
    
    def run_full_test_suite(self):
        """Executa suite completa de testes"""
        
        # 1. Listar todas as procedures
        procedures = self.list_all_procedures()
        
        # 2. Analisar staticamente
        print("[*] Running static analysis...")
        for proc in procedures:
            analysis = self.analyze_procedure_static(proc)
            self.results.extend(analysis)
        
        # 3. Testar dynamicamente
        print("[*] Running dynamic tests...")
        for proc in procedures:
            tests = self.test_procedure_dynamically(proc)
            self.results.extend(tests)
        
        # 4. Verificar permissões
        print("[*] Checking permissions...")
        permission_issues = self.check_permissions()
        self.results.extend(permission_issues)
        
        # 5. Gerar relatório
        report = self.generate_report()
        
        return report
    
    def list_all_procedures(self):
        """Lista todas as stored procedures"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                SCHEMA_NAME(schema_id) AS SchemaName,
                name AS ProcedureName,
                create_date,
                modify_date
            FROM sys.procedures
            WHERE is_ms_shipped = 0
            ORDER BY SchemaName, ProcedureName
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def generate_report(self):
        """Gera relatório de testes"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'passed': len([r for r in self.results if r.get('status') == 'PASS']),
            'failed': len([r for r in self.results if r.get('status') == 'FAIL']),
            'vulnerabilities': len([r for r in self.results if r.get('status') == 'VULNERABLE']),
            'results': self.results
        }
        
        # Salvar relatório
        with open(f'sp_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report

# Executar testes
if __name__ == "__main__":
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SecureApp;UID=readonly;PWD=readonly_password"
    
    tester = SPTestSuite(connection_string)
    report = tester.run_full_test_suite()
    
    print(f"\nTestes concluídos: {report['total_tests']}")
    print(f"Aprovados: {report['passed']}")
    print(f"Reprovados: {report['failed']}")
    print(f"Vulnerabilidades: {report['vulnerabilities']}")
```

---

## Referências e Recursos Adicionais

### Documentação Oficial

- **SQL Server Stored Procedures**: https://docs.microsoft.com/en-us/sql/relational-databases/stored-procedures/
- **PostgreSQL Procedures**: https://www.postgresql.org/docs/current/sql-createprocedure.html
- **Oracle Procedures**: https://docs.oracle.com/en/database/oracle/oracle-database/19/lnpls/
- **MySQL Stored Procedures**: https://dev.mysql.com/doc/refman/8.0/en/stored-programs.html

### OWASP Resources

- **OWASP SQL Injection Prevention**: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- **OWASP Stored Procedure Injection**: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection

### Best Practices

- **Least Privilege**: Conceder apenas permissões necessárias
- **Parameterized Queries**: Sempre usar parâmetros em Dynamic SQL
- **Input Validation**: Validar todos os parâmetros de entrada
- **Error Handling**: Implementar tratamento de erros robusto
- **Audit Logging**: Registrar todas as alterações em procedures
- **Code Review**: Revisar procedures regularmente

---

*Este capítulo demonstrou como implementar stored procedures seguras nos principais SGBDR. No próximo capítulo, veremos Triggers e Auditing em detalhes.*
