---
layout: default
title: "03-joins-ctes-subqueries"
---

# Capítulo 3: Joins, CTEs e Subqueries

## Sumário

- [3.1 Fundamentos de JOIN](#31-fundamentos-de-join)
- [3.2 INNER JOIN](#32-inner-join)
- [3.3 LEFT OUTER JOIN](#33-left-outer-join)
- [3.4 RIGHT OUTER JOIN](#34-right-outer-join)
- [3.5 FULL OUTER JOIN](#35-full-outer-join)
- [3.6 CROSS JOIN](#36-cross-join)
- [3.7 Self Joins](#37-self-joins)
- [3.8 Natural Joins e USING](#38-natural-joins-e-using)
- [3.9 Subqueries Escalares](#39-subqueries-escalares)
- [3.10 Subqueries IN e EXISTS](#310-subqueries-in-e-exists)
- [3.11 Subqueries Correlacionadas](#311-subqueries-correlacionadas)
- [3.12 CTEs Simples (Non-Recursive)](#312-ctes-simples-non-recursive)
- [3.13 CTEs Recursivos](#313-ctes-recursivos)
- [3.14 LATERAL Joins Avancados](#314-lateral-joins-avancados)
- [3.15 Window Functions Detalhadas](#315-window-functions-detalhadas)
- [3.16 Performance: JOINs vs Subqueries](#316-performance-joins-vs-subqueries)
- [3.17 Exemplos com Dados Reais](#317-exemplos-com-dados-reais)

---

## 3.1 Fundamentos de JOIN

### O Que e um JOIN?

Um JOIN combina linhas de duas ou mais tabelas baseado em uma condicao logica chamada join predicate. A operacao basica e o produto cartesiano (CROSS JOIN), que combina cada linha de uma tabela com cada linha de outra. O filtro ON reduz esse resultado para apenas as combinacoes relevantes.

### Semantica de JOIN

```sql
-- Produto cartesiano: todas as combinacoes possiveis
-- Tabela A com 3 linhas x Tabela B com 4 linhas = 12 linhas

-- O filtro ON restringe o resultado
SELECT *
FROM table_a a
JOIN table_b b ON a.id = b.a_id;

-- A diferenca entre ON e WHERE em JOINs nao-equi:
-- ON: filtra ANTES da juncao (afeta a semantica do JOIN)
-- WHERE: filtra DEPOIS da juncao (afeta o resultado final)

-- Exemplo critico com LEFT JOIN:
-- LEFT JOIN com ON: preserva linhas da esquerda mesmo com filtro na direita
-- LEFT JOIN com WHERE: pode eliminar linhas preservadas pelo LEFT JOIN
```

### Tabela de Dados de Exemplo

```sql
-- Tabelas de exemplo para todos os JOINs deste capitulo
CREATE TABLE departments (
    dept_id INTEGER PRIMARY KEY,
    dept_name VARCHAR(50),
    location VARCHAR(50),
    budget DECIMAL(12,2)
);

CREATE TABLE employees (
    emp_id INTEGER PRIMARY KEY,
    emp_name VARCHAR(100),
    dept_id INTEGER,
    salary DECIMAL(10,2),
    hire_date DATE,
    manager_id INTEGER
);

INSERT INTO departments VALUES
(1, 'Engineering', 'São Paulo', 500000.00),
(2, 'Marketing', 'Rio de Janeiro', 200000.00),
(3, 'Sales', 'Belo Horizonte', 300000.00),
(4, 'HR', 'São Paulo', 150000.00),
(5, 'Finance', 'Curitiba', 400000.00);

INSERT INTO employees VALUES
(101, 'Alice', 1, 9500.00, '2020-01-15', NULL),
(102, 'Bob', 1, 8500.00, '2020-03-20', 101),
(103, 'Carol', 1, 7500.00, '2021-06-10', 101),
(104, 'Dave', 2, 6500.00, '2019-09-01', NULL),
(105, 'Eve', 3, 7000.00, '2021-02-14', NULL),
(106, 'Frank', 3, 5500.00, '2022-07-01', 105),
(107, 'Grace', NULL, 8000.00, '2020-11-30', NULL),  -- sem departamento
(108, 'Heidi', 5, 9000.00, '2018-05-15', NULL);
```

---

## 3.2 INNER JOIN

### Sintaxe e Semantica

```sql
-- INNER JOIN: apenas linhas com correspondencia em AMBAS as tabelas
SELECT
    e.emp_name,
    e.salary,
    d.dept_name,
    d.location
FROM employees e
INNER JOIN departments d ON e.dept_id = d.dept_id;
```

Resultado:

```
 emp_name | salary | dept_name   | location
----------+--------+-------------+-----------
 Alice    | 9500.0 | Engineering | São Paulo
 Bob      | 8500.0 | Engineering | São Paulo
 Carol    | 7500.0 | Engineering | São Paulo
 Dave     | 6500.0 | Marketing   | Rio de Janeiro
 Eve      | 7000.0 | Sales       | Belo Horizonte
 Frank    | 5500.0 | Sales       | Belo Horizonte
 Heidi    | 9000.0 | Finance     | Curitiba
```

Note que Grace (dept_id = NULL) e department 4 (HR) nao aparecem — nao ha correspondencia.

### Multi-Table INNER JOIN

```sql
-- Join de 3 tabelas
SELECT
    e.emp_name,
    d.dept_name,
    m.emp_name AS manager_name
FROM employees e
INNER JOIN departments d ON e.dept_id = d.dept_id
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY d.dept_name, e.emp_name;
```

Resultado:

```
 emp_name | dept_name   | manager_name
----------+-------------+--------------
 Alice    | Engineering |
 Bob      | Engineering | Alice
 Carol    | Engineering | Alice
 Heidi    | Finance     |
 Dave     | Marketing   |
 Eve      | Sales       |
 Frank    | Sales       | Eve
```

### ANSI-89 vs ANSI-92

```sql
-- ANSI-89: WHERE clause implicit join (DEPRECATED)
SELECT e.emp_name, d.dept_name
FROM employees e, departments d
WHERE e.dept_id = d.dept_id;

-- ANSI-92: JOIN explicito (RECOMENDADO)
SELECT e.emp_name, d.dept_name
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id;

-- Diferenca critica: com ANSI-89, e facil esquecer o WHERE
-- e gerar um produto cartesiano acidental
SELECT e.emp_name, d.dept_name
FROM employees e, departments d;  -- PRODUTO CARTESIANO! 7x5 = 35 linhas

-- Com ANSI-92, JOIN sem ON gera erro de sintaxe
-- SELECT e.emp_name, d.dept_name
-- FROM employees e JOIN departments d;  -- ERRO!
```

---

## 3.3 LEFT OUTER JOIN

### Preservacao da Tabela Esquerda

```sql
-- LEFT JOIN: preserva TODAS as linhas da tabela esquerda
SELECT
    e.emp_name,
    e.dept_id,
    d.dept_name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.dept_id;
```

Resultado:

```
 emp_name | dept_id | dept_name
----------+---------+--------------
 Alice    |       1 | Engineering
 Bob      |       1 | Engineering
 Carol    |       1 | Engineering
 Dave     |       2 | Marketing
 Eve      |       3 | Sales
 Frank    |       3 | Sales
 Grace    |         |              -- NULL: sem departamento
 Heidi    |       5 | Finance
```

### Encontrar Registros Sem Correspondencia

```sql
-- Encontrar employees sem departamento
SELECT
    e.emp_id,
    e.emp_name,
    e.dept_id
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.dept_id
WHERE d.dept_id IS NULL;
```

Resultado:

```
 emp_id | emp_name | dept_id
--------+----------+---------
    107 | Grace    |
```

### Encontrar Departamentos Sem Employees

```sql
-- Departamentos sem employees
SELECT
    d.dept_id,
    d.dept_name
FROM departments d
LEFT JOIN employees e ON d.dept_id = e.dept_id
WHERE e.emp_id IS NULL;
```

Resultado:

```
 dept_id | dept_name
---------+-----------
       4 | HR
```

### SECURITY: LEFT JOIN em Autenticacao

```sql
-- PADRAO PERIGOSO: LEFT JOIN para verificar permissao
-- Se a tabela de permissao estiver vazia, todos passam!

-- ERRADO:
SELECT u.username, p.permission
FROM users u
LEFT JOIN user_permissions p ON u.user_id = p.user_id
WHERE u.username = 'admin'
AND p.permission = 'delete_users';

-- Problema: se user_permissions nao tem registro para admin,
-- LEFT JOIN retorna NULL para permission, WHERE p.permission = 'delete_users'
-- retorna 0 linhas. Parece seguro, mas...

-- PERIGO: se o WHERE fosse:
-- AND (p.permission = 'delete_users' OR p.permission IS NULL)
-- Ai sim seria vulneravel!

-- CORRETO: usar INNER JOIN para verificacao de permissao
SELECT u.username
FROM users u
INNER JOIN user_permissions p ON u.user_id = p.user_id
WHERE u.username = 'admin'
AND p.permission = 'delete_users';
-- Se nao tem permissao, retorna 0 linhas. Seguro.
```

---

## 3.4 RIGHT OUTER JOIN

### Simetria com LEFT JOIN

```sql
-- RIGHT JOIN: preserva TODAS as linhas da tabela direita
SELECT
    d.dept_name,
    e.emp_name
FROM employees e
RIGHT JOIN departments d ON e.dept_id = d.dept_id;
```

Resultado:

```
 dept_name   | emp_name
-------------+----------
 Engineering | Alice
 Engineering | Bob
 Engineering | Carol
 Marketing   | Dave
 Sales       | Eve
 Sales       | Frank
 HR          |              -- NULL: departamento sem employees
 Finance     | Heidi
```

### Convertendo RIGHT para LEFT

```sql
-- RIGHT JOIN e equivalente a LEFT JOIN com tabelas invertidas
-- Estas duas queries produzem o mesmo resultado:

-- Forma 1: RIGHT JOIN
SELECT d.dept_name, e.emp_name
FROM employees e
RIGHT JOIN departments d ON e.dept_id = d.dept_id;

-- Forma 2: LEFT JOIN (equivalente)
SELECT d.dept_name, e.emp_name
FROM departments d
LEFT JOIN employees e ON d.dept_id = e.dept_id;

-- RECOMENDACAO: prefira LEFT JOIN
-- A maioria dos programadores le de cima para baixo
-- LEFT JOIN e mais intuitivo: "pegue esta tabela e adicione dados dela"
```

---

## 3.5 FULL OUTER JOIN

### Preservacao de Ambos os Lados

```sql
-- FULL OUTER JOIN: preserva linhas de AMBAS as tabelas
SELECT
    e.emp_name,
    e.dept_id AS emp_dept,
    d.dept_id AS dept_id,
    d.dept_name
FROM employees e
FULL OUTER JOIN departments d ON e.dept_id = d.dept_id;
```

Resultado:

```
 emp_name | emp_dept | dept_id | dept_name
----------+----------+---------+--------------
 Alice    |        1 |       1 | Engineering
 Bob      |        1 |       1 | Engineering
 Carol    |        1 |       1 | Engineering
 Dave     |        2 |       2 | Marketing
 Eve      |        3 |       3 | Sales
 Frank    |        3 |       3 | Sales
 Grace    |          |         |              -- sem dept, dept sem emp
 Heidi    |        5 |       5 | Finance
          |          |       4 | HR
```

### FULL OUTER JOIN em MySQL

```sql
-- MySQL NAO suporta FULL OUTER JOIN diretamente
-- Workaround: UNION de LEFT e RIGHT JOIN

SELECT
    e.emp_name,
    e.dept_id AS emp_dept,
    d.dept_id AS dept_id,
    d.dept_name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.dept_id

UNION

SELECT
    e.emp_name,
    e.dept_id AS emp_dept,
    d.dept_id AS dept_id,
    d.dept_name
FROM employees e
RIGHT JOIN departments d ON e.dept_id = d.dept_id;
```

### Reconciliacao de Dados

```sql
-- FULL OUTER JOIN para reconciliacao entre sistemas
-- Sistema A e Sistema B devem ter os mesmos clientes

WITH sistema_a AS (
    SELECT customer_id, customer_name, email
    FROM sistema_a_customers
),
sistema_b AS (
    SELECT customer_id, customer_name, email
    FROM sistema_b_customers
)
SELECT
    COALESCE(a.customer_id, b.customer_id) AS customer_id,
    a.customer_name AS name_a,
    b.customer_name AS name_b,
    a.email AS email_a,
    b.email AS email_b,
    CASE
        WHEN a.customer_id IS NULL THEN 'ONLY_IN_B'
        WHEN b.customer_id IS NULL THEN 'ONLY_IN_A'
        WHEN a.customer_name != b.customer_name OR a.email != b.email
            THEN 'MISMATCH'
        ELSE 'MATCH'
    END AS sync_status
FROM sistema_a a
FULL OUTER JOIN sistema_b b ON a.customer_id = b.customer_id
WHERE a.customer_id IS NULL
   OR b.customer_id IS NULL
   OR a.customer_name != b.customer_name
   OR a.email != b.email;
```

---

## 3.6 CROSS JOIN

### Produto Cartesiano Intencional

```sql
-- CROSS JOIN: cada linha de A combinada com cada linha de B
-- Util quando precisa gerar combinacoes

-- Exemplo: gerar todas as combinacoes de produto x mes
SELECT
    p.product_name,
    m.month_name
FROM products p
CROSS JOIN (
    VALUES ('January'), ('February'), ('March'),
           ('April'), ('May'), ('June')
) AS m(month_name)
ORDER BY p.product_name, m.month_name;
```

### Gerar Calendario

```sql
-- Gerar serie de datas com CROSS JOIN
SELECT
    d.day_date,
    EXTRACT(DOW FROM d.day_date) AS day_of_week,
    EXTRACT(WEEK FROM d.day_date) AS week_number
FROM generate_series(
    '2024-01-01'::DATE,
    '2024-12-31'::DATE,
    '1 day'::INTERVAL
) AS d(day_date);
```

### Matriz de Combinacoes

```sql
-- Gerar matriz de distancias entre cidades
SELECT
    a.city AS city_from,
    b.city AS city_to,
    ST_Distance(
        a.geom::geography,
        b.geom::geography
    ) / 1000 AS distance_km
FROM cities a
CROSS JOIN cities b
WHERE a.city_id < b.city_id  -- evita duplicatas e diagonal
ORDER BY distance_km;
```

### SECURITY: Explosao Cartesian

```sql
-- PERIGO: CROSS JOIN acidental
-- Query original
SELECT o.order_id, p.product_name, c.customer_name
FROM orders o, products p, customers c
WHERE o.product_id = p.product_id
AND o.customer_id = c.customer_id;
-- Funciona, mas se esquecer um WHERE, gera produto cartesiano

-- SEGURO: JOIN explicito
SELECT o.order_id, p.product_name, c.customer_name
FROM orders o
JOIN products p ON o.product_id = p.product_id
JOIN customers c ON o.customer_id = c.customer_id;
-- Mesmo sem WHERE, o JOIN sem ON gera erro de sintaxe
```

---

## 3.7 Self Joins

### Tabela com ela mesma

```sql
-- Self join: employees e seus managers
SELECT
    e.emp_name AS employee,
    m.emp_name AS manager,
    e.salary AS emp_salary,
    m.salary AS mgr_salary,
    m.salary - e.salary AS salary_diff
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY e.emp_name;
```

Resultado:

```
 employee | manager | emp_salary | mgr_salary | salary_diff
----------+---------+------------+------------+-------------
 Alice    |         |     9500.0 |            |
 Bob      | Alice   |     8500.0 |     9500.0 |      1000.0
 Carol    | Alice   |     7500.0 |     9500.0 |      2000.0
 Dave     |         |     6500.0 |            |
 Eve      |         |     7000.0 |            |
 Frank    | Eve     |     5500.0 |     7000.0 |      1500.0
 Grace    |         |     8000.0 |            |
 Heidi    |         |     9000.0 |            |
```

### Encontrar Duplicatas

```sql
-- Encontrar pares de registros duplicados
-- (mesma nome + mesmo email, IDs diferentes)
SELECT
    a.customer_id AS id_1,
    b.customer_id AS id_2,
    a.customer_name,
    a.email
FROM customers a
JOIN customers b
    ON a.customer_name = b.customer_name
    AND a.email = b.email
    AND a.customer_id < b.customer_id;  -- evita duplicatas
```

### Comparar Linhas Vizinhas

```sql
-- Comparar salario com o proximo employee no mesmo departamento
SELECT
    e1.emp_name,
    e1.salary,
    e2.emp_name AS next_emp,
    e2.salary AS next_salary,
    e2.salary - e1.salary AS salary_diff
FROM employees e1
JOIN employees e2
    ON e1.dept_id = e2.dept_id
    AND e2.emp_id > e1.emp_id
WHERE e1.dept_id = 1
ORDER BY e1.emp_id, e2.emp_id;
```

---

## 3.8 Natural Joins e USING

### NATURAL JOIN

```sql
-- NATURAL JOIN: junta por colunas com o mesmo nome
SELECT emp_name, dept_name
FROM employees
NATURAL JOIN departments;
-- Equivalente a: JOIN ON employees.dept_id = departments.dept_id

-- PERIGO: NATURAL JOIN e fragil a mudancas de schema
-- Se voce adicionar uma coluna "budget" a employees
-- o NATURAL JOIN muda silenciosamente!
-- RECOMENDACAO: NAO use NATURAL JOIN em producao
```

### USING Clause

```sql
-- USING: junta por colunas especificas com mesmo nome
SELECT
    e.emp_name,
    d.dept_name
FROM employees e
JOIN departments d USING (dept_id);
-- Nao precisa de alias na coluna de juncao

-- USING com multiplas colunas
SELECT *
FROM table_a
JOIN table_b USING (col1, col2);
-- Equivalente a: ON table_a.col1 = table_b.col1 AND table_a.col2 = table_b.col2

-- SECURITY: NATURAL JOIN pode expor dados sensiveis
-- Se a tabela A tem coluna "password_hash" e tabela B tambem
-- NATURAL JOIN pode filtrar incorretamente
-- Ou pior: retornar dados inesperados
```

---

## 3.9 Subqueries Escalares

### Conceito

Uma subquery escalar retorna uma unica linha e uma unica coluna. Pode ser usada em qualquer lugar que uma expressao scalar e aceita.

```sql
-- Subquery escalar no SELECT
SELECT
    e.emp_name,
    e.salary,
    (SELECT AVG(salary) FROM employees) AS company_avg_salary,
    e.salary - (SELECT AVG(salary) FROM employees) AS diff_from_avg
FROM employees e;

-- Subquery escalar no WHERE
SELECT emp_name, salary
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);

-- Subquery escalar no FROM (derived table)
SELECT
    d.dept_name,
    dept_avg.avg_salary
FROM departments d
JOIN (
    SELECT dept_id, AVG(salary) AS avg_salary
    FROM employees
    GROUP BY dept_id
) dept_avg ON d.dept_id = dept_avg.dept_id;
```

### Subquery com Multiplas Linhas (ERRO)

```sql
-- ERRO: subquery escalar retorna mais de uma linha
-- SELECT emp_name FROM employees
-- WHERE salary > (SELECT AVG(salary) FROM employees GROUP BY dept_id);
-- ERROR: more than one row returned by a subquery used as an expression

-- SOLUCAO: usar ANY, ALL, ou IN
SELECT emp_name, salary
FROM employees
WHERE salary > ALL (SELECT AVG(salary) FROM employees GROUP BY dept_id);
```

---

## 3.10 Subqueries IN e EXISTS

### IN vs EXISTS

```sql
-- IN: verifica se o valor esta no conjunto retornado
SELECT emp_name, salary
FROM employees
WHERE dept_id IN (1, 3);

-- IN com subquery
SELECT emp_name, salary
FROM employees
WHERE dept_id IN (
    SELECT dept_id FROM departments WHERE location = 'São Paulo'
);

-- EXISTS: verifica se a subquery retorna alguma linha
SELECT e.emp_name, e.salary
FROM employees e
WHERE EXISTS (
    SELECT 1 FROM departments d
    WHERE d.dept_id = e.dept_id
    AND d.budget > 300000
);
```

### Performance: IN vs EXISTS

```sql
-- Regra geral:
-- EXISTS: melhor quando a subquery tem muitas linhas e poucos resultados
-- IN: melhor quando a subquery tem poucas linhas

-- EXISTS com correlated subquery (executada por linha)
SELECT e.emp_name
FROM employees e
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = e.emp_id
);

-- IN com subquery simples (executada uma vez)
SELECT e.emp_name
FROM employees e
WHERE e.dept_id IN (
    SELECT dept_id FROM departments WHERE location = 'São Paulo'
);
```

### NOT IN e NOT EXISTS

```sql
-- NOT IN: problematico com NULLs!
-- Se o subquery retorna qualquer NULL, NOT IN retorna 0 linhas

-- PERIGO:
SELECT emp_name FROM employees
WHERE dept_id NOT IN (SELECT dept_id FROM departments WHERE dept_id IS NOT NULL);
-- Funciona se todos os dept_id sao NOT NULL

-- Se houver NULL:
SELECT emp_name FROM employees
WHERE dept_id NOT IN (SELECT dept_id FROM departments);
-- departments tem dept_id NULL? NAO retorna NENHUM employee!

-- SEGURO: usar NOT EXISTS
SELECT e.emp_name
FROM employees e
WHERE NOT EXISTS (
    SELECT 1 FROM departments d WHERE d.dept_id = e.dept_id
);
-- Funciona corretamente mesmo com NULLs
```

### ANY, SOME e ALL

```sql
-- ANY/SOME: verdadeiro se pelo menos um valor do conjunto satisfaz
SELECT emp_name, salary
FROM employees
WHERE salary > ANY (
    SELECT salary FROM employees WHERE dept_id = 2
);
-- Maior que pelo menos um employee do dept 2

-- ALL: verdadeiro se todos os valores do conjunto satisfazem
SELECT emp_name, salary
FROM employees
WHERE salary > ALL (
    SELECT salary FROM employees WHERE dept_id = 3
);
-- Maior que TODOS os employees do dept 3

-- SECURITY: subqueries IN podem ser usadas em bypass
-- Se a aplicacao injeta valores no IN sem sanitizacao
-- E possivel manipular a query para retornar dados extras
-- Defesa: SEMPRE usar parametrizacao
```

---

## 3.11 Subqueries Correlacionadas

### Conceito

Uma subquery correlacionada referencia colunas da query externa. Ela e executada uma vez para cada linha da query externa.

```sql
-- Subquery correlacionada: salario acima da media do departamento
SELECT
    e1.emp_name,
    e1.dept_id,
    e1.salary,
    (SELECT AVG(e2.salary)
     FROM employees e2
     WHERE e2.dept_id = e1.dept_id) AS dept_avg_salary
FROM employees e1;
```

Resultado:

```
 emp_name | dept_id | salary | dept_avg_salary
----------+---------+--------+-----------------
 Alice    |       1 | 9500.0 |        8500.000
 Bob      |       1 | 8500.0 |        8500.000
 Carol    |       1 | 7500.0 |        8500.000
 Dave     |       2 | 6500.0 |        6500.000
 Eve      |       3 | 7000.0 |        6250.000
 Frank    |       3 | 5500.0 |        6250.000
 Grace    |         | 8000.0 |
 Heidi    |       5 | 9000.0 |        9000.000
```

### EXISTS Correlacionado

```sql
-- Employees que tem subordinados
SELECT e1.emp_name
FROM employees e1
WHERE EXISTS (
    SELECT 1 FROM employees e2
    WHERE e2.manager_id = e1.emp_id
);

-- Employees que NAO tem pedidos
SELECT c.customer_name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.customer_id
);
```

### SECURITY: Timing Attack via Subquery Correlacionada

```sql
-- CENARIO: ataque time-based via subquery correlacionada
-- Se o atacante pode injetar condicoes na subquery:

-- Conceitual:
-- Entrada: ' OR (SELECT CASE WHEN (SELECT password
--   FROM users WHERE username='admin'
--   AND SUBSTRING(password,1,1)='a') IS NOT NULL
--   THEN pg_sleep(5) ELSE pg_sleep(0) END)::text = '1'

-- DEFESA:
-- 1. Parametrizacao obrigatoria
-- 2. statement_timeout para limitar tempo de execucao
-- 3. NUNCA retornar erros detalhados ao usuario
SET statement_timeout = '5s';

-- 4. Usar funcoes seguras com LIMIT
CREATE OR REPLACE FUNCTION check_password(
    p_username TEXT,
    p_password TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    stored_hash TEXT;
BEGIN
    SELECT password_hash INTO stored_hash
    FROM users
    WHERE username = p_username
    LIMIT 1;

    IF stored_hash IS NULL THEN
        RETURN FALSE;
    END IF;

    RETURN stored_hash = crypt(p_password, stored_hash);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## 3.12 CTEs Simples (Non-Recursive)

### Conceito e Sintaxe

```sql
-- CTE basica:分解 consulta complexa em partes logicas
WITH active_orders AS (
    SELECT
        order_id,
        customer_id,
        total_amount,
        order_date
    FROM orders
    WHERE status = 'confirmed'
    AND order_date >= CURRENT_DATE - INTERVAL '30 days'
),
customer_totals AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS total_spent
    FROM active_orders
    GROUP BY customer_id
)
SELECT
    c.customer_name,
    ct.order_count,
    ct.total_spent,
    CASE
        WHEN ct.total_spent >= 1000 THEN 'VIP'
        WHEN ct.total_spent >= 500 THEN 'Regular'
        ELSE 'New'
    END AS customer_tier
FROM customer_totals ct
JOIN customers c ON ct.customer_id = c.customer_id
ORDER BY ct.total_spent DESC;
```

### Multiplas CTEs

```sql
-- Multiplas CTEs que constroem uma analise completa
WITH monthly_orders AS (
    SELECT
        date_trunc('month', order_date)::DATE AS month,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS revenue,
        COUNT(DISTINCT customer_id) AS unique_customers
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY 1
),
monthly_growth AS (
    SELECT
        month,
        total_orders,
        revenue,
        unique_customers,
        LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
        ROUND(
            (revenue - LAG(revenue) OVER (ORDER BY month))
            / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100, 2
        ) AS growth_pct
    FROM monthly_orders
)
SELECT
    month,
    total_orders,
    revenue,
    unique_customers,
    prev_month_revenue,
    growth_pct,
    CASE
        WHEN growth_pct > 10 THEN 'Strong Growth'
        WHEN growth_pct > 0 THEN 'Moderate Growth'
        WHEN growth_pct = 0 THEN 'Flat'
        ELSE 'Decline'
    END AS trend
FROM monthly_growth
ORDER BY month;
```

### CTE para Pivot Dinamico

```sql
-- Pivot sem usar PIVOT keyword
WITH source_data AS (
    SELECT
        product_category,
        EXTRACT(MONTH FROM order_date) AS month,
        SUM(total_amount) AS revenue
    FROM orders o
    JOIN products p ON o.product_id = p.product_id
    GROUP BY 1, 2
)
SELECT
    product_category,
    SUM(CASE WHEN month = 1 THEN revenue ELSE 0 END) AS jan,
    SUM(CASE WHEN month = 2 THEN revenue ELSE 0 END) AS feb,
    SUM(CASE WHEN month = 3 THEN revenue ELSE 0 END) AS mar,
    SUM(CASE WHEN month = 4 THEN revenue ELSE 0 END) AS apr,
    SUM(CASE WHEN month = 5 THEN revenue ELSE 0 END) AS may,
    SUM(CASE WHEN month = 6 THEN revenue ELSE 0 END) AS jun
FROM source_data
GROUP BY product_category
ORDER BY product_category;
```

---

## 3.13 CTEs Recursivos

### Sintaxe e Componentes

CTEs recursivos tem dois membros:

1. **Anchor member**: query inicial que nao referencia o CTE
2. **Recursive member**: query que referencia o CTE ( UNION ALL com anchor)

```sql
-- CTE recursivo: gerar serie de datas
WITH RECURSIVE date_series AS (
    -- Anchor: primeiro dia
    SELECT '2024-01-01'::DATE AS day
    UNION ALL
    -- Recursive: proximo dia
    SELECT day + 1
    FROM date_series
    WHERE day < '2024-01-31'::DATE
)
SELECT day FROM date_series;
```

### Hierarquias Organizacionais

```sql
-- Organizacao: arvore de employees
WITH RECURSIVE org_chart AS (
    -- Anchor: employees sem manager (raizes)
    SELECT
        emp_id,
        emp_name,
        manager_id,
        1 AS level,
        emp_name::TEXT AS path,
        emp_name::TEXT AS root_manager
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive: subordinados
    SELECT
        e.emp_id,
        e.emp_name,
        e.manager_id,
        oc.level + 1,
        oc.path || ' -> ' || e.emp_name,
        oc.root_manager
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.emp_id
    WHERE oc.level < 10  -- protecao contra loops
)
SELECT
    emp_id,
    emp_name,
    level,
    path,
    root_manager
FROM org_chart
ORDER BY path;
```

Resultado:

```
 emp_id | emp_name | level | path                    | root_manager
--------+----------+-------+-------------------------+--------------
    101 | Alice    |     1 | Alice                   | Alice
    102 | Bob      |     2 | Alice -> Bob            | Alice
    103 | Carol    |     2 | Alice -> Carol          | Alice
    104 | Dave     |     1 | Dave                    | Dave
    105 | Eve      |     1 | Eve                     | Eve
    106 | Frank    |     2 | Eve -> Frank            | Eve
    107 | Grace    |     1 | Grace                   | Grace
    108 | Heidi    |     1 | Heidi                   | Heidi
```

### Bill of Materials (BOM)

```sql
-- Cenarios: explosao de BOM em fabricacao
CREATE TABLE parts (
    part_id SERIAL PRIMARY KEY,
    part_name VARCHAR(100),
    unit_cost DECIMAL(10,2)
);

CREATE TABLE bill_of_materials (
    bom_id SERIAL PRIMARY KEY,
    parent_part_id INTEGER REFERENCES parts(part_id),
    child_part_id INTEGER REFERENCES parts(part_id),
    quantity DECIMAL(10,4)
);

-- Inserir dados
INSERT INTO parts VALUES
(1, 'Widget Assembly', 0),
(2, 'Housing', 15.00),
(3, 'Screw Pack', 2.50),
(4, 'PCB Board', 45.00),
(5, 'Chip A', 12.00),
(6, 'Capacitor', 0.50),
(7, 'Resistor', 0.25),
(8, 'Connector', 3.00);

INSERT INTO bill_of_materials VALUES
(1, 1, 2, 1),   -- Widget Assembly -> Housing x1
(2, 1, 4, 1),   -- Widget Assembly -> PCB Board x1
(3, 2, 3, 4),   -- Housing -> Screw Pack x4
(4, 4, 5, 2),   -- PCB Board -> Chip A x2
(5, 4, 6, 10),  -- PCB Board -> Capacitor x10
(6, 4, 7, 20),  -- PCB Board -> Resistor x20
(7, 4, 8, 3);   -- PCB Board -> Connector x3

-- Explodir BOM
WITH RECURSIVE bom_explosion AS (
    -- Anchor: componentes diretos
    SELECT
        bom.parent_part_id,
        bom.child_part_id,
        c.part_name AS child_name,
        bom.quantity,
        bom.quantity * p.unit_cost AS total_cost,
        1 AS level,
        p.part_name::TEXT AS path
    FROM bill_of_materials bom
    JOIN parts c ON bom.child_part_id = c.part_id
    JOIN parts p ON bom.child_part_id = p.part_id
    WHERE bom.parent_part_id = 1

    UNION ALL

    -- Recursive: sub-componentes
    SELECT
        bom.parent_part_id,
        bom.child_part_id,
        c.part_name,
        be.quantity * bom.quantity,
        be.quantity * bom.quantity * c.unit_cost,
        be.level + 1,
        be.path || ' > ' || c.part_name
    FROM bill_of_materials bom
    JOIN bom_explosion be ON bom.parent_part_id = be.child_part_id
    JOIN parts c ON bom.child_part_id = c.part_id
    WHERE be.level < 5
)
SELECT
    child_name,
    quantity,
    total_cost,
    level,
    path
FROM bom_explosion
ORDER BY path;
```

### Graph Traversal

```sql
-- Grafo: encontrar caminho entre dois nodos
CREATE TABLE edges (
    source_node VARCHAR(10),
    target_node VARCHAR(10),
    weight DECIMAL(5,2)
);

INSERT INTO edges VALUES
('A', 'B', 1.0),
('A', 'C', 3.0),
('B', 'C', 1.0),
('B', 'D', 2.0),
('C', 'D', 1.0),
('D', 'E', 2.0),
('A', 'E', 10.0);

-- Encontrar todos os caminhos de A ate E
WITH RECURSIVE paths AS (
    SELECT
        source_node,
        target_node,
        ARRAY[source_node, target_node] AS path,
        weight AS total_weight,
        1 AS depth
    FROM edges
    WHERE source_node = 'A'

    UNION ALL

    SELECT
        p.source_node,
        e.target_node,
        p.path || e.target_node,
        p.total_weight + e.weight,
        p.depth + 1
    FROM paths p
    JOIN edges e ON p.target_node = e.source_node
    WHERE e.target_node != ALL(p.path)  -- evitar ciclos
    AND p.depth < 5  -- limite de profundidade
)
SELECT
    path,
    total_weight,
    depth
FROM paths
WHERE target_node = 'E'
ORDER BY total_weight;
```

Resultado:

```
    path     | total_weight | depth
-------------+--------------+-------
 {A,E}       |        10.00 |     1
 {A,B,D,E}   |         5.00 |     3
 {A,B,C,D,E} |         5.00 |     4
 {A,C,D,E}   |         5.00 |     3
```

### SECURITY: Recursion Attack

```sql
-- PERIGO: CTE recursivo sem limite de profundidade
-- Se houver um ciclo no grafo, a recursao e infinita
-- e causa estouro de memoria

-- Dados com ciclo:
INSERT INTO edges VALUES ('E', 'A', 1.0);  -- cria ciclo!

-- CTE sem protecao (PERIGO):
-- WITH RECURSIVE paths AS (...)
-- ... WHERE e.target_node != ALL(p.path)  -- PREVINE ciclos

-- DEFESA OBRIGATORIA: SEMPRE adicionar limite de profundidade
WITH RECURSIVE paths AS (
    SELECT ...
    UNION ALL
    SELECT ...
    FROM paths p
    JOIN edges e ON p.target_node = e.source_node
    WHERE p.depth < 10  -- LIMITE OBRIGATORIO
    -- E tambem:
    AND e.target_node != ALL(p.path)  -- PREVENIR CICLOS
)
SELECT * FROM paths;
```

### Geracao de Dados com CTE Recursivos

```sql
-- Gerar numeros de 1 a 1000
WITH RECURSIVE nums AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM nums WHERE n < 1000
)
SELECT n FROM nums;

-- Gerar serie temporal com horarios
WITH RECURSIVE hourly AS (
    SELECT
        '2024-01-01 00:00:00'::TIMESTAMP AS hour_ts
    UNION ALL
    SELECT hour_ts + INTERVAL '1 hour'
    FROM hourly
    WHERE hour_ts < '2024-01-01 23:00:00'::TIMESTAMP
)
SELECT
    hour_ts,
    EXTRACT(HOUR FROM hour_ts) AS hour_of_day,
    TO_CHAR(hour_ts, 'YYYY-MM-DD HH24:00') AS formatted
FROM hourly;

-- Gerar Fibonacci
WITH RECURSIVE fibonacci AS (
    SELECT 0 AS n, 0 AS fib_current, 1 AS fib_next
    UNION ALL
    SELECT n + 1, fib_next, fib_current + fib_next
    FROM fibonacci
    WHERE n < 20
)
SELECT n, fib_current AS fibonacci FROM fibonacci;

-- Gerar numeros primos (ate 100)
WITH RECURSIVE nums AS (
    SELECT 2 AS n
    UNION ALL
    SELECT n + 1 FROM nums WHERE n < 100
),
is_prime AS (
    SELECT n
    FROM nums n1
    WHERE NOT EXISTS (
        SELECT 1 FROM nums n2
        WHERE n2.n > 1 AND n2.n < n1.n
        AND n1.n % n2.n = 0
    )
)
SELECT n FROM is_prime ORDER BY n;
```

### CTE Recursivos com Agregacao

```sql
-- Arvore com agregacao acumulada
WITH RECURSIVE org_costs AS (
    -- Anchor: custo direto de cada employee
    SELECT
        emp_id,
        emp_name,
        manager_id,
        salary AS total_cost,
        1 AS depth,
        emp_name::TEXT AS path
    FROM employees

    UNION ALL

    -- Recursive: acumular custos dos subordinados
    SELECT
        m.emp_id,
        m.emp_name,
        m.manager_id,
        m.salary + oc.total_cost,
        oc.depth + 1,
        oc.path || ' < ' || m.emp_name
    FROM org_costs oc
    JOIN employees m ON oc.manager_id = m.emp_id
    WHERE oc.depth < 5
)
SELECT
    emp_id,
    emp_name,
    MAX(total_cost) AS total_team_cost,
    MAX(depth) AS max_depth
FROM org_costs
GROUP BY emp_id, emp_name
ORDER BY total_team_cost DESC;
```

### Caminhos Mais Curtos (Dijkstra via SQL)

```sql
-- Encontrar caminho mais curto em grafo nao-ponderado
WITH RECURSIVE shortest_paths AS (
    SELECT
        'A' AS source,
        'A' AS target,
        ARRAY['A'] AS path,
        0 AS distance
    UNION ALL
    SELECT
        sp.source,
        e.target_node,
        sp.path || e.target_node,
        sp.distance + 1
    FROM shortest_paths sp
    JOIN edges e ON sp.target = e.source_node
    WHERE e.target_node != ALL(sp.path)
    AND sp.distance < 10
),
-- Pegar o caminho mais curto para cada destino
ranked_paths AS (
    SELECT
        source,
        target,
        path,
        distance,
        ROW_NUMBER() OVER (PARTITION BY target ORDER BY distance) AS rn
    FROM shortest_paths
)
SELECT source, target, path, distance
FROM ranked_paths
WHERE rn = 1
ORDER BY target;
```

---

## 3.14 LATERAL Joins Avancados

### Top-N por Grupo com LATERAL

```sql
-- Top 3 vendas por funcionario
SELECT
    e.emp_name,
    top_sales.*
FROM employees e
CROSS JOIN LATERAL (
    SELECT
        o.order_id,
        o.total_amount,
        o.order_date
    FROM orders o
    WHERE o.salesperson_id = e.emp_id
    ORDER BY o.total_amount DESC
    LIMIT 3
) AS top_sales;
```

### LATERAL com Funcao de Geracao

```sql
-- Gerar numeros aleatorios por categoria
SELECT
    c.category_name,
    random_vals.*
FROM categories c
CROSS JOIN LATERAL (
    SELECT
        generate_series(1, 5) AS sample_num,
        (random() * 100)::DECIMAL(5,2) AS random_value
) AS random_vals;
```

### LEFT JOIN LATERAL

```sql
-- Ultimo pedido por cliente (mantendo clientes sem pedidos)
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

### LATERAL como Oracle de Dados

```sql
-- SECURITY: LATERAL pode ser usado para extrair dados
-- Se uma query usa LATERAL com input do usuario:

-- PERIGO:
SELECT u.username, pw.*
FROM users u
CROSS JOIN LATERAL (
    SELECT *
    FROM passwords p
    WHERE p.user_id = u.user_id
) AS pw;
-- Se a query e modificada para incluir condicoes do usuario
-- pode expor dados sensiveis

-- DEFESA: validar permissoes antes do LATERAL
-- Usar RLS (Row-Level Security) nas tabelas acessadas via LATERAL
```

---

## 3.15 Window Functions Detalhadas

### ROW_NUMBER

```sql
-- ROW_NUMBER: numeracao unica e deterministica
-- Util para deduplicacao
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY created_at DESC
        ) AS rn
    FROM orders
)
SELECT *
FROM ranked
WHERE rn = 1;  -- ultimo pedido por cliente
```

### RANK e DENSE_RANK

```sql
-- Comparacao detalhada
SELECT
    emp_name,
    salary,
    RANK() OVER (ORDER BY salary DESC) AS rank_val,
    DENSE_RANK() OVER (ORDER BY salary DESC) AS dense_rank_val,
    ROW_NUMBER() OVER (ORDER BY salary DESC) AS row_num
FROM employees;
```

Resultado:

```
 emp_name | salary | rank_val | dense_rank_val | row_num
----------+--------+----------+----------------+--------
 Alice    | 9500.0 |        1 |              1 |      1
 Heidi    | 9000.0 |        2 |              2 |      2
 Bob      | 8500.0 |        3 |              3 |      3
 Grace    | 8000.0 |        4 |              4 |      4
 Carol    | 7500.0 |        5 |              5 |      5
 Eve      | 7000.0 |        6 |              6 |      6
 Dave     | 6500.0 |        7 |              7 |      7
 Frank    | 5500.0 |        8 |              8 |      8
```

Se dois employees tivessem o mesmo salario, RANK pularia numeros e DENSE_RANK nao.

### NTILE Detalhado

```sql
-- NTILE: divide os dados em N grupos aproximadamente iguais
-- Funciona mesmo quando o numero de linhas nao e divisivel por N

-- Dividir employees em quintis por salario
SELECT
    emp_name,
    salary,
    NTILE(5) OVER (ORDER BY salary DESC) AS quintile,
    CASE NTILE(5) OVER (ORDER BY salary DESC)
        WHEN 1 THEN 'Top 20%'
        WHEN 2 THEN '20-40%'
        WHEN 3 THEN '40-60%'
        WHEN 4 THEN '60-80%'
        WHEN 5 THEN 'Bottom 20%'
    END AS quintile_label
FROM employees;

-- NTILE para distribuicao de clientes por gasto
WITH customer_spending AS (
    SELECT
        customer_id,
        SUM(total_amount) AS total_spent
    FROM orders
    WHERE order_date >= '2024-01-01'
    GROUP BY customer_id
)
SELECT
    customer_id,
    total_spent,
    NTILE(10) OVER (ORDER BY total_spent DESC) AS decile,
    NTILE(4) OVER (ORDER BY total_spent DESC) AS quartile,
    CASE NTILE(4) OVER (ORDER BY total_spent DESC)
        WHEN 1 THEN 'Platinum'
        WHEN 2 THEN 'Gold'
        WHEN 3 THEN 'Silver'
        WHEN 4 THEN 'Bronze'
    END AS customer_tier
FROM customer_spending;
```

### NTILE

```sql
-- Dividir employees em quartis por salario
SELECT
    emp_name,
    salary,
    NTILE(4) OVER (ORDER BY salary DESC) AS salary_quartile,
    CASE NTILE(4) OVER (ORDER BY salary DESC)
        WHEN 1 THEN 'Top 25%'
        WHEN 2 THEN '25-50%'
        WHEN 3 THEN '50-75%'
        WHEN 4 THEN 'Bottom 25%'
    END AS quartile_label
FROM employees;
```

### LAG e LEAD

```sql
-- Variacao de salario mes a mes
WITH monthly_salaries AS (
    SELECT
        date_trunc('month', hire_date)::DATE AS month,
        SUM(salary) AS total_salaries
    FROM employees
    GROUP BY 1
)
SELECT
    month,
    total_salaries,
    LAG(total_salaries, 1) OVER (ORDER BY month) AS prev_month,
    LEAD(total_salaries, 1) OVER (ORDER BY month) AS next_month,
    total_salaries - LAG(total_salaries, 1) OVER (ORDER BY month) AS change,
    ROUND(
        (total_salaries - LAG(total_salaries, 1) OVER (ORDER BY month))
        / NULLIF(LAG(total_salaries, 1) OVER (ORDER BY month), 0) * 100
    , 2) AS pct_change
FROM monthly_salaries
ORDER BY month;
```

### SUM e AVG OVER com Frames

```sql
-- Media movel de 3 meses
WITH monthly_revenue AS (
    SELECT
        date_trunc('month', order_date)::DATE AS month,
        SUM(total_amount) AS revenue
    FROM orders
    GROUP BY 1
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
    revenue - AVG(revenue) OVER (
        ORDER BY month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS deviation_from_avg
FROM monthly_revenue
ORDER BY month;
```

### FIRST_VALUE e LAST_VALUE

```sql
-- Primeiro e ultimo salario de cada departamento
SELECT
    emp_name,
    dept_id,
    salary,
    FIRST_VALUE(salary) OVER (
        PARTITION BY dept_id
        ORDER BY hire_date
    ) AS first_hired_salary,
    LAST_VALUE(salary) OVER (
        PARTITION BY dept_id
        ORDER BY hire_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_hired_salary
FROM employees
WHERE dept_id IS NOT NULL
ORDER BY dept_id, hire_date;
```

### SECURITY: Window Function Injection

```sql
-- CENARIO: se a aplicacao injeta valores em PARTITION BY ou ORDER BY

-- PERIGO:
-- Se o usuario controla a coluna de ORDER BY na window function:
-- user_input = 'salary; DROP TABLE employees; --'
-- Isso e impossivel diretamente em SQL, mas em dynamic SQL...

-- DEFESA: NUNCA construir window functions com input do usuario
-- Usar apenas colunas fixas e conhecidas

-- CORRETO:
SELECT
    emp_name,
    salary,
    ROW_NUMBER() OVER (ORDER BY salary DESC) AS rank
FROM employees;

-- ERRADO (dynamic SQL):
-- query = 'SELECT emp_name, ROW_NUMBER() OVER (ORDER BY ' + user_input + ') FROM employees';
```

---

## 3.16 Performance: JOINs vs Subqueries

### Quando o Otimizador Transforma

```sql
-- PostgreSQL: CTE inlining (desde 12)
-- CTEs sao inlined por padrao (podem ser materializados com MATERIALIZED)

-- CTE inlined (comportamento padrao)
WITH active_customers AS (
    SELECT customer_id, customer_name
    FROM customers
    WHERE status = 'active'
)
SELECT ac.customer_name, COUNT(o.order_id)
FROM active_customers ac
JOIN orders o ON ac.customer_id = o.customer_id
GROUP BY ac.customer_name;

-- CTE materializado (forcar materializacao)
WITH active_customers AS MATERIALIZED (
    SELECT customer_id, customer_name
    FROM customers
    WHERE status = 'active'
)
SELECT ac.customer_name, COUNT(o.order_id)
FROM active_customers ac
JOIN orders o ON ac.customer_id = o.customer_id
GROUP BY ac.customer_name;

-- SQL Server: CTEs sempre sao inlined
-- PostgreSQL < 12: CTEs sempre sao materializadas
```

### EXISTS vs IN Performance

```sql
-- EXISTS: melhoria de performance com indexacao
-- A subquery correlacionada pode usar indice na tabela interna
SELECT e.emp_name
FROM employees e
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = e.emp_id
);
-- Orders(customer_id) deve ser indexada para performance

-- IN: subquery executada uma vez, resultado armazenado
SELECT e.emp_name
FROM employees e
WHERE e.emp_id IN (
    SELECT customer_id FROM orders
);

-- Ambos podem produzir o mesmo plano de execucao
-- mas o otimizador pode escolher abordagens diferentes
```

### Exemplo de EXPLAIN

```sql
-- Comparar planos
EXPLAIN (ANALYZE, BUFFERS)
SELECT e.emp_name, d.dept_name
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.salary > 7000;

-- vs equivalente com subquery
EXPLAIN (ANALYZE, BUFFERS)
SELECT emp_name,
    (SELECT dept_name FROM departments d WHERE d.dept_id = e.dept_id)
FROM employees e
WHERE salary > 7000;
-- A subquery escalar pode ser mais lenta que o JOIN
-- pois executa uma busca por linha
```

---

## 3.17 Exemplos com Dados Reais

### Analise Completa de Vendas

```sql
-- Query completa combinando CTEs, window functions, e joins
WITH
-- CTE 1: metricas basicas por pedido
order_metrics AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_date,
        o.total_amount,
        COUNT(oi.order_item_id) AS item_count,
        SUM(oi.quantity) AS total_quantity
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_date >= '2024-01-01'
    AND o.status != 'cancelled'
    GROUP BY o.order_id, o.customer_id, o.order_date, o.total_amount
),

-- CTE 2: metricas por cliente
customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS lifetime_value,
        AVG(total_amount) AS avg_order_value,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date
    FROM order_metrics
    GROUP BY customer_id
),

-- CTE 3: ranking de clientes
ranked_customers AS (
    SELECT
        cm.*,
        RANK() OVER (ORDER BY lifetime_value DESC) AS value_rank,
        NTILE(5) OVER (ORDER BY lifetime_value DESC) AS value_quintile,
        CASE
            WHEN lifetime_value >= 10000 THEN 'VIP'
            WHEN lifetime_value >= 5000 THEN 'Gold'
            WHEN lifetime_value >= 1000 THEN 'Silver'
            ELSE 'Bronze'
        END AS tier
    FROM customer_metrics cm
)

-- Query final
SELECT
    c.customer_name,
    rc.total_orders,
    rc.lifetime_value,
    rc.avg_order_value,
    rc.first_order_date,
    rc.last_order_date,
    rc.value_rank,
    rc.tier,
    r.region_name
FROM ranked_customers rc
JOIN customers c ON rc.customer_id = c.customer_id
JOIN regions r ON c.region_id = r.region_id
WHERE rc.tier IN ('VIP', 'Gold')
ORDER BY rc.lifetime_value DESC
LIMIT 50;
```

### Analise de Funil de Vendas

```sql
-- Funil de conversao: visitas -> carrinho -> checkout -> compra
WITH visitas AS (
    SELECT user_id, MIN(visited_at) AS first_visit
    FROM page_views
    WHERE page = 'product'
    GROUP BY user_id
),
carrinho AS (
    SELECT user_id, MIN(added_at) AS first_add
    FROM cart_additions
    GROUP BY user_id
),
checkout AS (
    SELECT user_id, MIN(started_at) AS first_checkout
    FROM checkout_starts
    GROUP BY user_id
),
compra AS (
    SELECT user_id, MIN(order_date) AS first_purchase
    FROM orders
    WHERE status = 'completed'
    GROUP BY user_id
)
SELECT
    'Visitas' AS stage,
    COUNT(DISTINCT v.user_id) AS users,
    100.0 AS pct_of_total
FROM visitas v

UNION ALL

SELECT
    'Adicionou ao Carrinho',
    COUNT(DISTINCT c.user_id),
    ROUND(100.0 * COUNT(DISTINCT c.user_id) / (SELECT COUNT(DISTINCT user_id) FROM visitas), 1)
FROM carrinho c
WHERE c.user_id IN (SELECT user_id FROM visitas)

UNION ALL

SELECT
    'Iniciou Checkout',
    COUNT(DISTINCT ch.user_id),
    ROUND(100.0 * COUNT(DISTINCT ch.user_id) / (SELECT COUNT(DISTINCT user_id) FROM visitas), 1)
FROM checkout ch
WHERE ch.user_id IN (SELECT user_id FROM visitas)

UNION ALL

SELECT
    'Comprou',
    COUNT(DISTINCT p.user_id),
    ROUND(100.0 * COUNT(DISTINCT p.user_id) / (SELECT COUNT(DISTINCT user_id) FROM visitas), 1)
FROM compra p
WHERE p.user_id IN (SELECT user_id FROM visitas)

ORDER BY users DESC;
```

### Deteccao de Anomalias com Window Functions

```sql
-- Detectar transacoes suspeitas (fora do padrao)
WITH customer_patterns AS (
    SELECT
        customer_id,
        AVG(total_amount) AS avg_amount,
        STDDEV(total_amount) AS stddev_amount,
        COUNT(*) AS total_transactions
    FROM orders
    WHERE order_date >= CURRENT_DATE - INTERVAL '90 day'
    AND status = 'completed'
    GROUP BY customer_id
    HAVING COUNT(*) >= 5  -- pelo menos 5 transacoes para ter padrao
),
flagged_transactions AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.total_amount,
        o.order_date,
        cp.avg_amount,
        cp.stddev_amount,
        ROUND(
            (o.total_amount - cp.avg_amount) / NULLIF(cp.stddev_amount, 0)
        , 2) AS z_score
    FROM orders o
    JOIN customer_patterns cp ON o.customer_id = cp.customer_id
    WHERE o.order_date >= CURRENT_DATE - INTERVAL '30 day'
)
SELECT
    ft.order_id,
    c.customer_name,
    ft.total_amount,
    ft.avg_amount,
    ft.z_score,
    CASE
        WHEN ft.z_score > 3 THEN 'CRITICAL: 3+ desvios acima da media'
        WHEN ft.z_score > 2 THEN 'WARNING: 2+ desvios acima da media'
        WHEN ft.z_score < -3 THEN 'ANOMALY: valor muito abaixo do esperado'
        ELSE 'Normal'
    END AS risk_level
FROM flagged_transactions ft
JOIN customers c ON ft.customer_id = c.customer_id
WHERE ABS(ft.z_score) > 2
ORDER BY ABS(ft.z_score) DESC;
```

### Analise de Cohort com CTEs

```sql
-- Cohort de retencao mensal
WITH first_purchase AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(order_date))::DATE AS cohort_month
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
customer_activity AS (
    SELECT
        fp.customer_id,
        fp.cohort_month,
        DATE_TRUNC('month', o.order_date)::DATE AS order_month
    FROM first_purchase fp
    JOIN orders o ON fp.customer_id = o.customer_id
    WHERE o.status = 'completed'
),
cohort_data AS (
    SELECT
        ca.cohort_month,
        (EXTRACT(YEAR FROM ca.order_month) - EXTRACT(YEAR FROM ca.cohort_month)) * 12
        + (EXTRACT(MONTH FROM ca.order_month) - EXTRACT(MONTH FROM ca.cohort_month)) AS month_number,
        COUNT(DISTINCT ca.customer_id) AS active_customers
    FROM customer_activity ca
    GROUP BY 1, 2
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
)
SELECT
    cd.cohort_month,
    cs.cohort_size,
    cd.month_number,
    cd.active_customers,
    ROUND(100.0 * cd.active_customers / cs.cohort_size, 1) AS retention_rate
FROM cohort_data cd
JOIN cohort_sizes cs ON cd.cohort_month = cs.cohort_month
WHERE cd.cohort_month >= '2024-01-01'
ORDER BY cd.cohort_month, cd.month_number;
```

### Otimizacao de Queries com CTEs

```sql
-- CTE materializado vs inlined

-- PostgreSQL 12+: CTEs sao inlined por padrao
-- Isso melhora performance para CTEs simples

-- Forcar materializacao quando necessario
WITH expensive_calc AS MATERIALIZED (
    SELECT
        customer_id,
        SUM(total_amount) AS lifetime_value,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY customer_id
)
SELECT * FROM expensive_calc WHERE lifetime_value > 1000;

-- Para CTEs que sao referenciados multiplas vezes:
-- Materializacao evita re-execucao
WITH customer_stats AS MATERIALIZED (
    SELECT
        customer_id,
        AVG(total_amount) AS avg_order,
        MAX(order_date) AS last_order
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_name,
    cs.avg_order,
    cs.last_order,
    CASE
        WHEN cs.avg_order > 1000 THEN 'High Value'
        ELSE 'Standard'
    END AS tier
FROM customers c
JOIN customer_stats cs ON c.customer_id = cs.customer_id
WHERE cs.last_order >= CURRENT_DATE - INTERVAL '30 day';
```

### JOINs Avancados: Anti-Join e Semi-Join

```sql
-- Semi-Join: retorna linhas da tabela esquerda que tem correspondencia
-- (similar a EXISTS)
SELECT DISTINCT e.emp_name
FROM employees e
JOIN orders o ON e.emp_id = o.salesperson_id;
-- Vs:
SELECT e.emp_name
FROM employees e
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.salesperson_id = e.emp_id);

-- Anti-Join: retorna linhas da tabela esquerda que NAO tem correspondencia
-- (similar a NOT EXISTS)
SELECT e.emp_name
FROM employees e
LEFT JOIN orders o ON e.emp_id = o.salesperson_id
WHERE o.order_id IS NULL;
-- Vs:
SELECT e.emp_name
FROM employees e
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.salesperson_id = e.emp_id);

-- PERFORMANCE: Anti-join com LEFT JOIN pode ser mais rapido que NOT EXISTS
-- em alguns SGBDRs, especialmente com indices
-- Mas NOT EXISTS e mais legivel e portavel
```

### Window Functions: Frames Detalhados

```sql
-- ROWS vs RANGE vs GROUPS

-- ROWS: baseado na posicao fisica da linha
SELECT
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        ORDER BY order_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS sum_last_3_rows
FROM orders;

-- RANGE: baseado no VALOR da coluna de ORDER BY
-- Inclui todas as linhas com valor igual ao intervalo
SELECT
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        ORDER BY order_date
        RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
    ) AS sum_last_7_days
FROM orders;

-- GROUPS: baseado em grupos de valores iguais
SELECT
    salary,
    COUNT(*) OVER (
        ORDER BY salary
        GROUPS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ) AS count_nearby_salaries
FROM employees;

-- UNBOUNDED PRECEDING: desde o inicio da particao
-- UNBOUNDED FOLLOWING: ate o final da particao
-- CURRENT ROW: apenas a linha atual

-- Exemplo completo de frame
SELECT
    emp_name,
    salary,
    SUM(salary) OVER (
        ORDER BY salary
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_sum,
    AVG(salary) OVER (
        ORDER BY hire_date
        ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
    ) AS moving_avg_5,
    MAX(salary) OVER (
        PARTITION BY dept_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS dept_max_salary
FROM employees
WHERE dept_id IS NOT NULL
ORDER BY dept_id, hire_date;
```

### WINDOW Clause Reutilizacao

```sql
-- PostgreSQL: WINDOW clause para reutilizar definicoes de janela
SELECT
    emp_name,
    salary,
    dept_id,
    ROW_NUMBER() OVER w AS row_num,
    RANK() OVER w AS rank_val,
    SUM(salary) OVER w AS running_total,
    AVG(salary) OVER w AS running_avg
FROM employees
WHERE dept_id IS NOT NULL
WINDOW w AS (
    PARTITION BY dept_id
    ORDER BY salary DESC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
ORDER BY dept_id, salary DESC;
```

### Performance: JOINs vs Subqueries

```sql
-- Quando usar JOIN vs Subquery

-- CASO 1: Subquery para filtrar
-- EXISTS geralmente e mais rapido que IN para subqueries correlacionadas
-- porque pode parar na primeira correspondencia

-- LENTO (scan completo da subquery):
SELECT * FROM products
WHERE category_id IN (
    SELECT category_id FROM categories WHERE is_active = true
);

-- RAPIDO (para na primeira correspondencia):
SELECT * FROM products p
WHERE EXISTS (
    SELECT 1 FROM categories c
    WHERE c.category_id = p.category_id
    AND c.is_active = true
);

-- CASO 2: JOIN para agregar
-- JOIN + GROUP BY geralmente e mais rapido que subquery no SELECT
-- Subquery no SELECT executa uma vez por linha

-- LENTO (subquery por linha):
SELECT
    c.customer_name,
    (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS order_count
FROM customers c;

-- RAPIDO (JOIN + GROUP BY):
SELECT
    c.customer_name,
    COUNT(o.order_id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name;
```

### EXPLAIN ANALYZE: Comparando Planos

```sql
-- Verificar plano de execucao
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT e.emp_name, d.dept_name
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.salary > 7000;

-- Saida esperada (PostgreSQL):
-- Hash Join  (cost=4.15..8.18 rows=5 width=32) (actual time=0.045..0.047 rows=5 loops=1)
--   Hash Cond: (e.dept_id = d.dept_id)
--   ->  Seq Scan on employees e  (cost=0.00..8.00 rows=8 width=28) (actual time=0.008..0.010 rows=8 loops=1)
--         Filter: (salary > '7000'::numeric)
--         Rows Removed by Filter: 0
--   ->  Hash  (cost=3.05..3.05 rows=5 width=12) (actual time=0.028..0.028 rows=4 loops=1)
--         Buckets: 1024  Batches: 1  Memory Usage: 9kB
--         ->  Seq Scan on departments d  (cost=0.00..3.05 rows=5 width=12) (actual time=0.005..0.006 rows=4 loops=1)
-- Planning Time: 0.125 ms
-- Execution Time: 0.082 ms

-- Interpretacao:
-- Hash Join: eficiente para joins sem indice
-- Seq Scan: leitura sequencial (tabelas pequenas)
-- Se a tabela for grande, veria Index Scan ou Bitmap Scan
-- Se houvesse sort caro, veria Sort node
```

### Dicas de Performance

```sql
-- 1. SEMPRE criar indice nas colunas de JOIN
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_product ON orders(product_id);

-- 2. Usar覆盖索covers (INCLUDE) para queries frequentes
CREATE INDEX idx_orders_covering ON orders(customer_id, order_date)
INCLUDE (total_amount, status);

-- 3. Evitar SELECT * em JOINs (puxa dados desnecessarios)
-- LENTO:
SELECT * FROM orders o JOIN customers c ON o.customer_id = c.customer_id;
-- RAPIDO:
SELECT o.order_id, o.total_amount, c.customer_name
FROM orders o JOIN customers c ON o.customer_id = c.customer_id;

-- 4. Filtrar antes de joinar (quando possivel)
-- LENTO:
SELECT e.emp_name, d.dept_name
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
WHERE e.salary > 7000;
-- RAPIDO (se salary > 7000 e altamente seletivo):
WITH high_earners AS (
    SELECT emp_id, emp_name, dept_id
    FROM employees WHERE salary > 7000
)
SELECT he.emp_name, d.dept_name
FROM high_earners he
JOIN departments d ON he.dept_id = d.dept_id;

-- 5. Evitar funcoes nas colunas de JOIN
-- LENTO (impede uso de indice):
SELECT * FROM orders o
JOIN customers c ON LOWER(o.customer_email) = LOWER(c.email);
-- RAPIDO:
SELECT * FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;
```

### Seguranca em JOINs e Subqueries

```sql
-- SECURITY: JOIN injection
-- Se a coluna de JOIN vem de input do usuario:

-- PERIGO: dynamic SQL com JOIN
-- query = 'SELECT * FROM orders o JOIN ' + user_input + ' c ON o.customer_id = c.id';
-- Isso permite SQL injection via UNION

-- DEFESA: NUNCA usar input do usuario em nomes de tabelas ou colunas
-- Usar parametrizacao para valores, nao para estrutura

-- SECURITY: informacao em erro de JOIN
-- Se o erro detalha a estrutura da tabela:
-- "relation 'nonexistent_table' does not exist"
-- Isso revela nomes de tabelas ao atacante

-- DEFESA: nao expor erros detalhados ao usuario
-- Usar mensagens genericas de erro
BEGIN
    -- query que pode falhar
    PERFORM 1;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Database error occurred';
    -- NAO: RAISE EXCEPTION '%', SQLERRM;
END;

-- SECURITY: UNION injection via JOIN
-- Se uma query usa JOIN com input nao sanitizado:
-- Entrada: ' UNION SELECT username, password FROM users --'
-- Isso pode unir dados de tabela sensiveis

-- DEFESA: tipo de retorno consistente
-- Se a query retorna tipagem fixa, UNION injection e bloqueada
-- PostgreSQL: casts explicitos nas colunas
SELECT
    o.order_id::TEXT,
    o.total_amount::TEXT,
    c.customer_name::TEXT
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;
```

### CTEs Avancadas: Materializacao Condicional

```sql
-- CTE com condicoes de materializacao
-- PostgreSQL 12+ permite controlar quando materializar

-- Padrao (inlined): boa para CTEs simples
WITH simple_filter AS (
    SELECT * FROM orders WHERE status = 'active'
)
SELECT * FROM simple_filter WHERE total_amount > 100;

-- Materializado: necessario quando:
-- 1. CTE e referenciado multiplas vezes
-- 2. CTE e custoso de executar
-- 3. Precisa garantir consistencia dos dados

WITH expensive_report AS MATERIALIZED (
    SELECT
        c.customer_id,
        c.customer_name,
        COUNT(o.order_id) AS total_orders,
        SUM(o.total_amount) AS lifetime_value,
        AVG(o.total_amount) AS avg_order,
        MAX(o.order_date) AS last_order,
        MIN(o.order_date) AS first_order
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name
),
tiered_customers AS (
    SELECT
        *,
        CASE
            WHEN lifetime_value >= 10000 THEN 'Platinum'
            WHEN lifetime_value >= 5000 THEN 'Gold'
            WHEN lifetime_value >= 1000 THEN 'Silver'
            ELSE 'Bronze'
        END AS tier
    FROM expensive_report
)
SELECT
    tier,
    COUNT(*) AS customer_count,
    AVG(lifetime_value) AS avg_ltv,
    AVG(total_orders) AS avg_orders
FROM tiered_customers
GROUP BY tier
ORDER BY avg_ltv DESC;
```

### CTEs para Data Transformation

```sql
-- Pipeline de transformacao de dados usando CTEs

-- ETL basico: extrair, transformar, carregar
WITH
-- Extrair: dados brutos
raw_data AS (
    SELECT
        customer_id,
        order_date,
        total_amount,
        status
    FROM orders
    WHERE order_date >= '2024-01-01'
),

-- Transformar 1: filtrar e limpar
cleaned_data AS (
    SELECT
        customer_id,
        order_date,
        total_amount,
        status,
        EXTRACT(MONTH FROM order_date) AS month,
        EXTRACT(YEAR FROM order_date) AS year
    FROM raw_data
    WHERE status IN ('completed', 'shipped')
    AND total_amount > 0
    AND total_amount < 100000  -- outliers
),

-- Transformar 2: agregar por mes
monthly_metrics AS (
    SELECT
        year,
        month,
        COUNT(*) AS order_count,
        COUNT(DISTINCT customer_id) AS unique_customers,
        SUM(total_amount) AS revenue,
        AVG(total_amount) AS avg_order_value
    FROM cleaned_data
    GROUP BY year, month
),

-- Transformar 3: calcular metricas derivadas
with_calculations AS (
    SELECT
        *,
        LAG(revenue) OVER (ORDER BY year, month) AS prev_month_revenue,
        revenue - LAG(revenue) OVER (ORDER BY year, month) AS revenue_change,
        ROUND(
            (revenue - LAG(revenue) OVER (ORDER BY year, month))
            / NULLIF(LAG(revenue) OVER (ORDER BY year, month), 0) * 100
        , 2) AS growth_pct
    FROM monthly_metrics
)

-- Carregar: resultado final
SELECT
    year,
    month,
    order_count,
    unique_customers,
    revenue,
    avg_order_value,
    prev_month_revenue,
    revenue_change,
    growth_pct,
    CASE
        WHEN growth_pct > 20 THEN 'Strong Growth'
        WHEN growth_pct > 5 THEN 'Moderate Growth'
        WHEN growth_pct > -5 THEN 'Flat'
        ELSE 'Decline'
    END AS trend
FROM with_calculations
ORDER BY year, month;
```

### Window Functions Avancadas: NTILE para Analytics

```sql
-- Distribuicao de vendas por regiao com percentis
WITH regional_sales AS (
    SELECT
        r.region_name,
        o.order_id,
        o.total_amount
    FROM orders o
    JOIN regions r ON o.region_id = r.region_id
    WHERE o.status = 'completed'
),
ranked_sales AS (
    SELECT
        region_name,
        order_id,
        total_amount,
        NTILE(100) OVER (PARTITION BY region_name ORDER BY total_amount) AS percentile,
        PERCENT_RANK() OVER (PARTITION BY region_name ORDER BY total_amount) AS pct_rank,
        CUME_DIST() OVER (PARTITION BY region_name ORDER BY total_amount) AS cumulative_dist
    FROM regional_sales
)
SELECT
    region_name,
    MIN(total_amount) AS min_sale,
    MAX(total_amount) AS max_sale,
    AVG(total_amount) AS avg_sale,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_amount) AS median_sale,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_amount) AS p95_sale,
    COUNT(*) AS total_orders
FROM regional_sales
GROUP BY region_name;
```

### JOINs Condicional e Dinamico

```sql
-- JOIN condicional: unir com tabela diferentes baseado em condicao
SELECT
    o.order_id,
    o.total_amount,
    CASE
        WHEN o.order_type = 'online' THEN ot.gateway_name
        WHEN o.order_type = 'store' THEN st.store_name
    END AS source_name
FROM orders o
LEFT JOIN online_transactions ot ON o.order_id = ot.order_id
    AND o.order_type = 'online'
LEFT JOIN store_transactions st ON o.order_id = st.order_id
    AND o.order_type = 'store';

-- CROSS JOIN LATERAL para lookup condicional
SELECT
    o.order_id,
    o.total_amount,
    lookup.result
FROM orders o
CROSS JOIN LATERAL (
    SELECT
        CASE
            WHEN o.total_amount >= 1000 THEN 'premium'
            WHEN o.total_amount >= 500 THEN 'standard'
            ELSE 'basic'
        END AS result
) AS lookup;
```

### Seguranca: Timing Attack via JOIN

```sql
-- SECURITY: timing attack via join complexo
-- Se a query usa join com condicoes que dependem de dados sensiveis
-- o tempo de execucao pode revelar informacoes

-- CENARIO:
-- Se existe indice em password_hash e a query faz JOIN
-- baseado em hash comparison, o tempo pode variar

-- DEFESA:
-- 1. Usar comparacao constante-tempo (via funcao no banco)
-- 2. Evitar JOINs baseados em dados sensiveis
-- 3. Usar rate limiting

-- Funcao segura de verificacao de senha
CREATE OR REPLACE FUNCTION verify_login(
    p_username TEXT,
    p_password TEXT
) RETURNS TABLE (
    user_id BIGINT,
    username TEXT,
    is_valid BOOLEAN
) AS $$
DECLARE
    stored_hash TEXT;
    uid BIGINT;
BEGIN
    -- Busca com timeout
    SET LOCAL statement_timeout = '2s';

    SELECT u.user_id, u.password_hash
    INTO uid, stored_hash
    FROM users u
    WHERE u.username = p_username
    LIMIT 1;

    IF stored_hash IS NULL THEN
        -- Execute dummy hash para manter tempo constante
        PERFORM crypt('dummy', gen_salt('bf'));
        RETURN QUERY SELECT NULL::BIGINT, p_username, FALSE;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        uid,
        p_username,
        stored_hash = crypt(p_password, stored_hash);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Padroes de Consulta Complexa

```sql
-- Padrao: Top-N por grupo com desempate
WITH ranked AS (
    SELECT
        department_id,
        employee_name,
        salary,
        hire_date,
        ROW_NUMBER() OVER (
            PARTITION BY department_id
            ORDER BY salary DESC, hire_date ASC  -- desempate por data de contratacao
        ) AS rn
    FROM employees
)
SELECT * FROM ranked WHERE rn <= 3;

-- Padrao: Running total com reset por grupo
SELECT
    department_id,
    employee_name,
    salary,
    SUM(salary) OVER (
        PARTITION BY department_id
        ORDER BY hire_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_dept_salary
FROM employees
WHERE department_id IS NOT NULL;

-- Padrao: Gap and Islands (encontrar sequencias consecutivas)
WITH numbered AS (
    SELECT
        order_date,
        order_date - ROW_NUMBER() OVER (ORDER BY order_date)::INTEGER AS group_id
    FROM orders
    WHERE status = 'completed'
)
SELECT
    MIN(order_date) AS streak_start,
    MAX(order_date) AS streak_end,
    COUNT(*) AS streak_length
FROM numbered
GROUP BY group_id
HAVING COUNT(*) > 1
ORDER BY streak_length DESC;
```

### Recapitulacao: Tabela de Decisao

```sql
-- Quando usar cada tecnica

-- JOIN: quando precisa combinar dados de 2+ tabelas
-- e a correspondencia e bem definida
SELECT e.emp_name, d.dept_name
FROM employees e JOIN departments d ON e.dept_id = d.dept_id;

-- Subquery escalar: quando precisa de um unico valor
SELECT emp_name, salary - (SELECT AVG(salary) FROM employees) AS diff
FROM employees;

-- Subquery IN: quando o conjunto de valores e pequeno
SELECT * FROM employees WHERE dept_id IN (1, 2, 3);

-- EXISTS: quando o conjunto de correspondencia e grande
-- e precisa de performance
SELECT e.emp_name FROM employees e
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = e.emp_id);

-- NOT EXISTS: para anti-join seguro com NULLs
SELECT e.emp_name FROM employees e
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.salesperson_id = e.emp_id);

-- CTE: para consultas complexas que precisam de legibilidade
-- e reutilizacao de sub-resultados
WITH stats AS (
    SELECT dept_id, AVG(salary) AS avg_sal
    FROM employees GROUP BY dept_id
)
SELECT e.emp_name, e.salary, s.avg_sal
FROM employees e JOIN stats s ON e.dept_id = s.dept_id;

-- CTE recursivo: para dados hierarquicos ou em grafo
WITH RECURSIVE tree AS (
    SELECT emp_id, emp_name, manager_id, 1 AS level
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.emp_id, e.emp_name, e.manager_id, t.level + 1
    FROM employees e JOIN tree t ON e.manager_id = t.emp_id
)
SELECT * FROM tree ORDER BY level;

-- Window functions: para analises que precisam de contexto
-- de linhas vizinhas sem colapsar resultados
SELECT emp_name, salary,
    AVG(salary) OVER (PARTITION BY dept_id) AS dept_avg,
    ROW_NUMBER() OVER (ORDER BY salary DESC) AS global_rank
FROM employees;

-- LATERAL: para Top-N por grupo ou operacoes dependentes
SELECT e.emp_name, top3.*
FROM employees e
CROSS JOIN LATERAL (
    SELECT order_id, total_amount FROM orders
    WHERE customer_id = e.emp_id
    ORDER BY total_amount DESC LIMIT 3
) top3;
```

### Cenarios Reais: Dashboard de E-commerce

```sql
-- Query completa para dashboard executivo
WITH
-- Metricas do dia
daily_metrics AS (
    SELECT
        COUNT(DISTINCT o.order_id) AS orders_today,
        COUNT(DISTINCT o.customer_id) AS customers_today,
        COALESCE(SUM(o.total_amount), 0) AS revenue_today,
        COALESCE(AVG(o.total_amount), 0) AS avg_order_today
    FROM orders o
    WHERE o.order_date::DATE = CURRENT_DATE
    AND o.status NOT IN ('cancelled', 'refunded')
),

-- Metricas do mes
monthly_metrics AS (
    SELECT
        COUNT(DISTINCT o.order_id) AS orders_month,
        COUNT(DISTINCT o.customer_id) AS customers_month,
        COALESCE(SUM(o.total_amount), 0) AS revenue_month
    FROM orders o
    WHERE o.order_date >= DATE_TRUNC('month', CURRENT_DATE)
    AND o.status NOT IN ('cancelled', 'refunded')
),

-- Top produtos
top_products AS (
    SELECT
        p.product_name,
        SUM(oi.quantity) AS units_sold,
        SUM(oi.quantity * oi.unit_price) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date >= CURRENT_DATE - INTERVAL '7 day'
    AND o.status NOT IN ('cancelled', 'refunded')
    GROUP BY p.product_id, p.product_name
    ORDER BY revenue DESC
    LIMIT 5
),

-- Pedidos recentes
recent_orders AS (
    SELECT
        o.order_id,
        c.customer_name,
        o.total_amount,
        o.status,
        o.created_at
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    ORDER BY o.created_at DESC
    LIMIT 10
),

-- Alertas de estoque baixo
stock_alerts AS (
    SELECT
        p.product_name,
        p.stock_quantity,
        p.reorder_point,
        CASE
            WHEN p.stock_quantity = 0 THEN 'OUT OF STOCK'
            WHEN p.stock_quantity <= p.reorder_point THEN 'LOW STOCK'
            ELSE 'OK'
        END AS stock_status
    FROM products p
    WHERE p.stock_quantity <= p.reorder_point
    AND p.is_active = true
)

-- Dashboard final
SELECT 'daily' AS section, jsonb_build_object(
    'orders', dm.orders_today,
    'customers', dm.customers_today,
    'revenue', dm.revenue_today,
    'avg_order', ROUND(dm.avg_order_today, 2)
) AS data
FROM daily_metrics dm

UNION ALL

SELECT 'monthly', jsonb_build_object(
    'orders', mm.orders_month,
    'customers', mm.customers_month,
    'revenue', mm.revenue_month
)
FROM monthly_metrics mm

UNION ALL

SELECT 'top_products', jsonb_agg(
    jsonb_build_object('name', tp.product_name, 'revenue', tp.revenue)
)
FROM top_products tp

UNION ALL

SELECT 'recent_orders', jsonb_agg(
    jsonb_build_object(
        'id', ro.order_id,
        'customer', ro.customer_name,
        'amount', ro.total_amount,
        'status', ro.status
    )
)
FROM recent_orders ro

UNION ALL

SELECT 'stock_alerts', jsonb_agg(
    jsonb_build_object(
        'product', sa.product_name,
        'stock', sa.stock_quantity,
        'status', sa.stock_status
    )
)
FROM stock_alerts sa;
```

### Verificacao de Integridade Referencial

```sql
-- Encontrar chaves estrangeiras quebradas em todo o banco
-- (util para auditoria de integridade)

-- PostgreSQL: encontrar FKs quebradas
DO $$
DECLARE
    r RECORD;
    broken_count INTEGER;
BEGIN
    FOR r IN
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS ref_table,
            ccu.column_name AS ref_column
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
    LOOP
        EXECUTE format(
            'SELECT COUNT(*) FROM %I t
             LEFT JOIN %I r ON t.%I = r.%I
             WHERE t.%I IS NOT NULL AND r.%I IS NULL',
            r.table_name, r.ref_table,
            r.column_name, r.ref_column,
            r.column_name, r.ref_column
        ) INTO broken_count;

        IF broken_count > 0 THEN
            RAISE WARNING 'FK broken: %.%.% -> %.%.% (% rows)',
                'public', r.table_name, r.column_name,
                'public', r.ref_table, r.ref_column,
                broken_count;
        END IF;
    END LOOP;
END $$;
```

---

## Resumo

Este capitulo cobriu as ferramentas fundamentais para consultar e manipular dados complexos em SQL. Comecamos com os tipos basicos de JOIN — INNER, LEFT, RIGHT, FULL, e CROSS — e exploramos Self Joins e Natural Joins com suas armadilhas de seguranca.

Estudamos subqueries em todas as suas formas: escalares, IN, EXISTS, e correlacionadas. Aprendemos a diferenca critica entre NOT IN (problematico com NULLs) e NOT EXISTS (seguro). Vimos como ANY, SOME e ALL expandem as opcoes de filtragem.

CTEs simples e recursivos foram explorados em detalhe. CTEs recursivos resolvem problemas complexos como hierarquias, BOM, e traversal de grafos — mas exigem protecao contra ciclos e profundidade infinita.

LATERAL joins permitem Top-N por grupo e operacoes dependentes de cada linha. Window functions fornecem analises sophisticated sem colapsar linhas, com ROW_NUMBER, RANK, DENSE_RANK, NTILE, LAG, LEAD, e funcoes de frame.

Combinamos todas essas tecnicas em exemplos com dados reais: analises de vendas, deteccao de anomalias, cohort analysis, e pipelines de transformacao. Cada funcionalidade foi apresentada com seguranca em mente.

No proximo capitulo, cruzaremos esses conceitos com SQL injection — a vulnerabilidade mais perigosa e mais evitavel em sistemas de banco de dados.

---

*[Proximo capitulo: 04 — SQL Injection - Fundamentos](04-sqli-fundamentos.md)*
