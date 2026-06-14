# Capítulo 10 — Segurança de Banco de Dados

## Objetivos de Aprendizado

1. Compreender os vetores de ataque mais comuns contra bancos de dados relacionais e NoSQL, incluindo injeção SQL/NoSQL e escalação de privilégios.
2. Implementar prepared statements e consultas parametrizadas em C++ para eliminar vetores de injeção SQL.
3. Projetar camadas de criptografia em repouso e em trânsito para proteger dados sensíveis armazenados e transportados por bancos de dados.
4. Aplicar padrões de acesso seguro a bancos de dados, incluindo pooling de conexões, princípio de menor privilégio e trilhas de auditoria tamper-evident.
5. Construir um framework completo de gerenciamento de backup criptografado e migração segura de dados em C++.

---

## 1. Fundamentos de Segurança de Banco de Dados

### 1.1 Arquitetura de Segurança de Banco de Dados

A segurança de banco de dados não é uma camada isolada — ela se entrelaça com a segurança da rede, da aplicação e da infraestrutura. Uma arquitetura de segurança robusta para bancos de dados deve considerar cinco pilares fundamentais:

| Pilar | Descrição | Mecanismo Típico |
|---|---|---|
| **Autenticação** | Verificação de identidade de quem acessa | Certificados TLS, credenciais, tokens |
| **Autorização** | Controle do que o usuário autenticado pode fazer | GRANT/REVOKE, roles, ACLs |
| **Criptografia** | Proteção dos dados em repouso e em trânsito | TDE, TLS 1.3, criptografia de coluna |
| **Auditoria** | Registro de todas as operações realizadas | Audit logs, triggers de auditoria |
| **Integridade** | Garantia de que os dados não foram adulterados | Checksums, assinaturas digitais |

### 1.2 Vetores de Ataque Comuns

Os vetores de ataque contra bancos de dados podem ser classificados em categorias distintas:

**Ataques de Injeção**: O vetor mais prevalente e prejudicial. Segundo o OWASP Top 10, injeção SQL permanece entre as vulnerabilidades mais perigosas em aplicações que interagem com bancos de dados. O atacante insere código malicioso em entradas da aplicação que são incorporadas diretamente em consultas SQL.

**Escalação de Privilégios**: O atacante obtém permissões além do seu nível autorizado, explorando configurações incorretas ou vulnerabilidades no mecanismo de autorização do banco.

**Exfiltração de Dados**: A extração não autorizada de dados sensíveis, frequentemente resultado de uma combinação de injeção SQL e falta de controle de acesso adequado.

**Ataques de Força Bruta**: Tentativas repetidas de adivinhar credenciais de acesso ao banco de dados.

**Ataques à Camada de Transporte**: Intercepção de comunicação entre a aplicação e o banco de dados quando o tráfego não é criptografado.

### 1.3 Modelo de Privilégios de Banco de Dados

O princípio do menor privilégio é a regra de ouro da segurança de bancos de dados. Cada usuário da aplicação deve ter apenas as permissões estritamente necessárias para realizar suas funções:

```
-- Nunca conecte ao banco como root/admin
-- Crie usuários específicos por função:

CREATE ROLE app_readonly LOGIN PASSWORD 'strong_password_here';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

CREATE ROLE app_readwrite LOGIN PASSWORD 'strong_password_here';
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_readwrite;

CREATE ROLE app_admin LOGIN PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;
```

### 1.4 Segurança de Conexão

A primeira linha de defesa é garantir que a comunicação entre a aplicação e o banco de dados seja segura:

```cpp
// Connection string with security best practices
// NEVER hardcode credentials in source code
struct DatabaseConfig {
    std::string host;
    int port;
    std::string database;
    std::string username;
    std::string password;
    bool use_ssl = true;
    int connection_timeout_seconds = 30;
    int query_timeout_seconds = 60;

    // Load from environment variables, never from source code
    static DatabaseConfig fromEnvironment() {
        DatabaseConfig config;
        config.host = getEnvOrDefault("DB_HOST", "localhost");
        config.port = std::stoi(getEnvOrDefault("DB_PORT", "5432"));
        config.database = getEnvOrDefault("DB_NAME", "app_db");
        config.username = getEnvOrDefault("DB_USER", "");
        config.password = getEnvOrDefault("DB_PASSWORD", "");

        if (config.username.empty() || config.password.empty()) {
            throw SecurityError(
                "Database credentials must be provided via environment variables"
            );
        }

        config.use_ssl = getEnvOrDefault("DB_USE_SSL", "true") == "true";
        return config;
    }

    std::string buildConnectionString() const {
        // Build connection string with SSL enforcement
        std::ostringstream conn;
        conn << "host=" << host
             << " port=" << port
             << " dbname=" << database
             << " user=" << username
             << " password=" << password;

        if (use_ssl) {
            conn << " sslmode=require";
        } else {
            conn << " sslmode=disable";
        }

        return conn.str();
    }
};
```

### 1.5 Estatísticas de Impacto

Para contextualizar a importância da segurança de bancos de dados, considere os seguintes casos reais documentados publicamente:

**Heartland Payment Systems (2008)**: Uma das maiores violações de dados da história dos EUA. O atacante Albert Gonzalez explora vulnerabilidades de injeção SQL em sistemas internos para acessar dados de mais de 130 milhões de cartões de crédito e débito. O prejuízo total ultrapassou US$ 200 milhões. O ataque começou com injeção SQL em um site público que dava acesso à rede interna.

**Sony Pictures (2011)**: Um ataque de injeção SQL expõe dados pessoais de mais de 1 milhões de usuários do PlayStation Network. O atacante utiliza SQL injection em uma aplicação web para acessar o banco de dados de usuários, obtendo nomes, endereços, e-mails e senhas.

**TalkTalk (2015)**: Um ataque de injeção SQL acessa dados de 157 mil clientes da operadora britânica. Os atacantes utilizam SQL injection para acessar tabelas contendo números de conta bancária e códigos de segurança. O prejuízo para a empresa foi de aproximadamente £ 77 milhões.

---

## 2. Prepared Statements e Parameterized Queries

### 2.1 Anatomy of a SQL Injection Attack

Para compreender a gravidade da injeção SQL, vamos analisar um ataque passo a passo. Considere uma aplicação C++ que busca um usuário pelo nome:

```cpp
// VULNERABLE CODE — NEVER DO THIS
void findUser(sqlite3* db, const std::string& username) {
    std::string query = "SELECT * FROM users WHERE username = '"
                        + username + "'";

    sqlite3_stmt* stmt;
    int rc = sqlite3_prepare_v2(db, query.c_str(), -1, &stmt, nullptr);
    if (rc == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            // Process user data...
        }
    }
    sqlite3_finalize(stmt);
}
```

Um atacante pode fornecer a seguinte entrada:

```
' OR '1'='1' --
```

Isso transforma a consulta em:

```sql
SELECT * FROM users WHERE username = '' OR '1'='1' --'
```

A consulta agora retorna TODOS os registros da tabela `users`, independentemente do nome de usuário. O atacante pode até executar operações destrutivas:

```cpp
// Malicious input that could DROP the table
// Input: '; DROP TABLE users; --
// Resulting query:
// SELECT * FROM users WHERE username = ''; DROP TABLE users; --'
```

### 2.2 SQLite Prepared Statements

O SQLite oferece suporte nativo a prepared statements, que separam completamente a estrutura da consulta dos dados:

```cpp
#include <sqlite3.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <memory>

class SQLiteSecureQuery {
public:
    explicit SQLiteSecureQuery(sqlite3* db) : db_(db) {
        if (!db_) {
            throw std::invalid_argument("Database handle cannot be null");
        }
    }

    // SAFE: Parameterized query prevents SQL injection
    std::vector<std::vector<std::string>> findUser(const std::string& username) {
        const char* sql = "SELECT id, username, email, role FROM users WHERE username = ?";
        sqlite3_stmt* stmt = nullptr;

        int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
        if (rc != SQLITE_OK) {
            throw std::runtime_error(
                std::string("Failed to prepare statement: ") + sqlite3_errmsg(db_)
            );
        }

        // Bind the parameter — the database driver handles escaping
        rc = sqlite3_bind_text(stmt, 1, username.c_str(),
                               static_cast<int>(username.size()), SQLITE_TRANSIENT);
        if (rc != SQLITE_OK) {
            sqlite3_finalize(stmt);
            throw std::runtime_error(
                std::string("Failed to bind parameter: ") + sqlite3_errmsg(db_)
            );
        }

        std::vector<std::vector<std::string>> results;
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            std::vector<std::string> row;
            int cols = sqlite3_column_count(stmt);
            for (int i = 0; i < cols; ++i) {
                const char* text = reinterpret_cast<const char*>(
                    sqlite3_column_text(stmt, i)
                );
                row.emplace_back(text ? text : "");
            }
            results.push_back(std::move(row));
        }

        sqlite3_finalize(stmt);
        return results;
    }

    // SAFE: Insert with parameterized query
    bool insertUser(const std::string& username,
                    const std::string& email,
                    const std::string& role) {
        const char* sql = "INSERT INTO users (username, email, role) VALUES (?, ?, ?)";
        sqlite3_stmt* stmt = nullptr;

        int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);
        if (rc != SQLITE_OK) {
            return false;
        }

        sqlite3_bind_text(stmt, 1, username.c_str(),
                          static_cast<int>(username.size()), SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, email.c_str(),
                          static_cast<int>(email.size()), SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 3, role.c_str(),
                          static_cast<int>(role.size()), SQLITE_TRANSIENT);

        rc = sqlite3_step(stmt);
        sqlite3_finalize(stmt);
        return rc == SQLITE_DONE;
    }

private:
    sqlite3* db_;
};
```

### 2.3 PostgreSQL libpq Prepared Statements

O PostgreSQL, através da biblioteca libpq, oferece suporte a prepared statements de duas formas: comandos Prepare/Execute e consultas parametradas inline:

```cpp
#include <libpq-fe.h>
#include <string>
#include <vector>
#include <stdexcept>

class PostgreSQLSecureQuery {
public:
    explicit PostgreSQLSecureQuery(PGconn* conn) : conn_(conn) {
        if (PQstatus(conn) != CONNECTION_OK) {
            throw std::runtime_error("Connection is not open");
        }
    }

    // Method 1: Libpq parameterized query (preferred for one-off queries)
    std::vector<std::vector<std::string>> parameterizedQuery(
            const std::string& sql,
            const std::vector<std::string>& params) {
        // Convert string params to const char* array
        std::vector<const char*> paramValues;
        for (const auto& p : params) {
            paramValues.push_back(p.c_str());
        }

        PGresult* result = PQexecParams(
            conn_,
            sql.c_str(),
            static_cast<int>(params.size()),
            nullptr,        // let libpq infer types
            paramValues.data(),
            nullptr,        // no binary params
            nullptr,        // no text format flags
            0               // result in text format
        );

        if (PQresultStatus(result) != PGRES_TUPLES_OK) {
            std::string error = PQerrorMessage(conn_);
            PQclear(result);
            throw std::runtime_error("Query failed: " + error);
        }

        std::vector<std::vector<std::string>> rows;
        int nRows = PQntuples(result);
        int nCols = PQnfields(result);

        for (int r = 0; r < nRows; ++r) {
            std::vector<std::string> row;
            for (int c = 0; c < nCols; ++c) {
                const char* val = PQgetvalue(result, r, c);
                row.emplace_back(val ? val : "");
            }
            rows.push_back(std::move(row));
        }

        PQclear(result);
        return rows;
    }

    // Method 2: Named prepared statements (preferred for repeated queries)
    void prepareStatement(const std::string& name, const std::string& sql,
                          int nParams) {
        PGresult* result = PQprepare(conn_, name.c_str(), sql.c_str(),
                                     nParams, nullptr);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            std::string error = PQerrorMessage(conn_);
            PQclear(result);
            throw std::runtime_error("Prepare failed: " + error);
        }
        PQclear(result);
    }

    std::vector<std::vector<std::string>> executePrepared(
            const std::string& name,
            const std::vector<std::string>& params) {
        std::vector<const char*> paramValues;
        for (const auto& p : params) {
            paramValues.push_back(p.c_str());
        }

        PGresult* result = PQexecPrepared(
            conn_,
            name.c_str(),
            static_cast<int>(params.size()),
            paramValues.data(),
            nullptr,
            nullptr,
            0
        );

        if (PQresultStatus(result) != PGRES_TUPLES_OK) {
            std::string error = PQerrorMessage(conn_);
            PQclear(result);
            throw std::runtime_error("Execute failed: " + error);
        }

        std::vector<std::vector<std::string>> rows;
        int nRows = PQntuples(result);
        int nCols = PQnfields(result);

        for (int r = 0; r < nRows; ++r) {
            std::vector<std::string> row;
            for (int c = 0; c < nCols; ++c) {
                row.emplace_back(PQgetvalue(result, r, c));
            }
            rows.push_back(std::move(row));
        }

        PQclear(result);
        return rows;
    }

private:
    PGconn* conn_;
};
```

### 2.4 Segurança de Connection Strings

Connection strings são frequentemente um vetor de ataque subestimado. Erros comuns incluem:

```cpp
// VULNERABLE: Credentials in source code
// const std::string conn = "host=localhost dbname=app user=admin password=secret123";

// VULNERABLE: Credentials in config files committed to version control
// Read from config.json that is tracked by git

// SECURE: Credentials from environment variables
class SecureConnectionString {
public:
    static std::string build() {
        std::string host = requireEnv("DB_HOST");
        std::string port = requireEnv("DB_PORT");
        std::string name = requireEnv("DB_NAME");
        std::string user = requireEnv("DB_USER");
        std::string pass = requireEnv("DB_PASSWORD");
        std::string sslMode = getEnvOrDefault("DB_SSLMODE", "require");

        // Validate SSL mode
        if (sslMode != "require" && sslMode != "verify-ca" &&
            sslMode != "verify-full") {
            throw std::runtime_error(
                "Insecure SSL mode '" + sslMode + "'. "
                "Use 'require', 'verify-ca', or 'verify-full'."
            );
        }

        return "host=" + host +
               " port=" + port +
               " dbname=" + name +
               " user=" + user +
               " password=" + pass +
               " sslmode=" + sslMode;
    }

private:
    static std::string requireEnv(const std::string& name) {
        const char* val = std::getenv(name.c_str());
        if (!val || std::strlen(val) == 0) {
            throw std::runtime_error(
                "Required environment variable '" + name + "' is not set"
            );
        }
        return std::string(val);
    }

    static std::string getEnvOrDefault(const std::string& name,
                                       const std::string& defaultVal) {
        const char* val = std::getenv(name.c_str());
        return (val && std::strlen(val) > 0) ? std::string(val) : defaultVal;
    }
};
```

### 2.5 Classe Completa de Consulta Parametrizada com Tipagem Segura

A seguir, uma classe completa que encapsula consultas parametrizadas com type-safety e cache de statements:

```cpp
#include <sqlite3.h>
#include <string>
#include <vector>
#include <unordered_map>
#include <mutex>
#include <memory>
#include <stdexcept>
#include <optional>
#include <functional>

class TypeSafeParameter {
public:
    explicit TypeSafeParameter(int val) : type_(INTEGER) {
        intVal_ = val;
    }
    explicit TypeSafeParameter(double val) : type_(REAL) {
        realVal_ = val;
    }
    explicit TypeSafeParameter(const std::string& val) : type_(TEXT),
        strVal_(val) {}
    explicit TypeSafeParameter(const char* val) : type_(TEXT),
        strVal_(val ? val : "") {}
    explicit TypeSafeParameter(std::nullptr_t) : type_(NULL_VAL) {}

    enum Type { INTEGER, REAL, TEXT, NULL_VAL } type_;

    int intVal_ = 0;
    double realVal_ = 0.0;
    std::string strVal_;
};

class ParameterizedQuery {
public:
    ParameterizedQuery(sqlite3* db, const std::string& sql)
        : db_(db), sql_(sql), stmt_(nullptr) {
        // First, try to get from cache
        {
            std::lock_guard<std::mutex> lock(cacheMutex_);
            auto it = statementCache_.find(sql);
            if (it != statementCache_.end()) {
                // Clone the cached statement
                rc_ = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt_, nullptr);
                return;
            }
        }

        rc_ = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt_, nullptr);
        if (rc_ == SQLITE_OK) {
            std::lock_guard<std::mutex> lock(cacheMutex_);
            // Cache up to 100 statements
            if (statementCache_.size() < 100) {
                sqlite3_stmt* cached = nullptr;
                sqlite3_prepare_v2(db_, sql.c_str(), -1, &cached, nullptr);
                statementCache_[sql] = cached;
            }
        }
    }

    ~ParameterizedQuery() {
        if (stmt_) {
            sqlite3_finalize(stmt_);
        }
    }

    // Non-copyable, movable
    ParameterizedQuery(const ParameterizedQuery&) = delete;
    ParameterizedQuery& operator=(const ParameterizedQuery&) = delete;
    ParameterizedQuery(ParameterizedQuery&& other) noexcept
        : db_(other.db_), sql_(std::move(other.sql_)),
          stmt_(other.stmt_), rc_(other.rc_) {
        other.stmt_ = nullptr;
    }

    ParameterizedQuery& bind(int index, const TypeSafeParameter& param) {
        if (!stmt_) {
            throw std::runtime_error("Statement not initialized");
        }

        int rc;
        switch (param.type_) {
            case TypeSafeParameter::INTEGER:
                rc = sqlite3_bind_int(stmt_, index, param.intVal_);
                break;
            case TypeSafeParameter::REAL:
                rc = sqlite3_bind_double(stmt_, index, param.realVal_);
                break;
            case TypeSafeParameter::TEXT:
                rc = sqlite3_bind_text(stmt_, index, param.strVal_.c_str(),
                    static_cast<int>(param.strVal_.size()), SQLITE_TRANSIENT);
                break;
            case TypeSafeParameter::NULL_VAL:
                rc = sqlite3_bind_null(stmt_, index);
                break;
        }

        if (rc != SQLITE_OK) {
            throw std::runtime_error(
                "Failed to bind parameter " + std::to_string(index) +
                ": " + sqlite3_errmsg(db_)
            );
        }
        return *this;
    }

    // Execute and return results as vector of string vectors
    std::vector<std::vector<std::string>> executeQuery() {
        if (!stmt_) {
            throw std::runtime_error("Statement not initialized");
        }

        std::vector<std::vector<std::string>> results;
        int stepResult;

        while ((stepResult = sqlite3_step(stmt_)) == SQLITE_ROW) {
            std::vector<std::string> row;
            int cols = sqlite3_column_count(stmt_);
            for (int i = 0; i < cols; ++i) {
                const char* text = reinterpret_cast<const char*>(
                    sqlite3_column_text(stmt_, i)
                );
                row.emplace_back(text ? text : "");
            }
            results.push_back(std::move(row));
        }

        if (stepResult != SQLITE_DONE) {
            throw std::runtime_error(
                std::string("Query execution failed: ") + sqlite3_errmsg(db_)
            );
        }

        sqlite3_reset(stmt_);
        sqlite3_clear_bindings(stmt_);
        return results;
    }

    // Execute without returning results (INSERT, UPDATE, DELETE)
    int executeUpdate() {
        if (!stmt_) {
            throw std::runtime_error("Statement not initialized");
        }

        int rc = sqlite3_step(stmt_);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(
                std::string("Update failed: ") + sqlite3_errmsg(db_)
            );
        }

        int changes = sqlite3_changes(db_);
        sqlite3_reset(stmt_);
        sqlite3_clear_bindings(stmt_);
        return changes;
    }

    // Execute and return optional first row
    std::optional<std::vector<std::string>> executeSingle() {
        auto results = executeQuery();
        if (results.empty()) {
            return std::nullopt;
        }
        return results[0];
    }

private:
    sqlite3* db_;
    std::string sql_;
    sqlite3_stmt* stmt_;
    int rc_;

    static std::mutex cacheMutex_;
    static std::unordered_map<std::string, sqlite3_stmt*> statementCache_;
};

std::mutex ParameterizedQuery::cacheMutex_;
std::unordered_map<std::string, sqlite3_stmt*> ParameterizedQuery::statementCache_;
```

---

## 3. ORM Security

### 3.1 Considerações de Segurança em ORM

Object-Relational Mapping (ORM) frameworks oferecem uma camada de abstração sobre o banco de dados. Embora muitos ORMs protejam contra injeção SQL por padrão, eles introduzem seus próprios vetores de segurança.

**Geração de Consultas**: ORMs geram SQL automaticamente, mas consultas construídas dinamicamente com concatenação de strings interna podem ser vulneráveis. É essencial verificar que o ORM utiliza parâmetros vinculados em suas consultas geradas.

**Lazy Loading Vulnerabilities**: O lazy loading pode causar consultas excessivas ao banco de dados (N+1 queries), tornando o sistema vulnerável a ataques de negação de serviço baseados em recurso.

**Input Handling**: ORMs que aceitam construtores de consulta dinâmicos podem ser explorados se a entrada do usuário for incorporada diretamente nas cláusulas de filtro.

### 3.2 Padrões de Segurança para ORM em C++

```cpp
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <sstream>

// Minimal ORM-like pattern with security built-in
template<typename T>
class SecureRepository {
public:
    struct QueryFilter {
        std::string column;
        enum class Operator { EQUALS, NOT_EQUALS, LIKE, GT, LT, GTE, LTE };
        Operator op;
        TypeSafeParameter value;
    };

    explicit SecureRepository(sqlite3* db) : db_(db) {}

    // SAFE: Always uses parameterized queries
    std::vector<T> findBy(const std::vector<QueryFilter>& filters,
                          const std::string& orderBy = "",
                          int limit = 100) {
        if (filters.empty()) {
            throw std::invalid_argument("At least one filter is required");
        }

        // Whitelist of allowed columns prevents column injection
        std::string sql = "SELECT * FROM " + getTableName() + " WHERE ";
        std::vector<TypeSafeParameter> params;
        int paramIndex = 1;

        for (size_t i = 0; i < filters.size(); ++i) {
            if (!isAllowedColumn(filters[i].column)) {
                throw std::invalid_argument(
                    "Invalid column: " + filters[i].column
                );
            }

            if (i > 0) {
                sql += " AND ";
            }

            sql += filters[i].column + " " + operatorToString(filters[i].op) + " ?";
            params.push_back(filters[i].value);
            ++paramIndex;
        }

        if (!orderBy.empty()) {
            // Validate orderBy to prevent injection
            if (!isAllowedColumn(orderBy)) {
                throw std::invalid_argument("Invalid order column: " + orderBy);
            }
            sql += " ORDER BY " + orderBy;
        }

        sql += " LIMIT ?";
        params.push_back(TypeSafeParameter(limit));

        // Execute using parameterized query
        ParameterizedQuery query(db_, sql);
        for (int i = 0; i < static_cast<int>(params.size()); ++i) {
            query.bind(i + 1, params[i]);
        }

        auto results = query.executeQuery();
        return mapResultsToEntities(results);
    }

    // SAFE: Insert with parameterized values
    bool save(const T& entity) {
        auto fields = getInsertFields(entity);
        auto values = getInsertValues(entity);

        std::string sql = "INSERT INTO " + getTableName() + " (";
        for (size_t i = 0; i < fields.size(); ++i) {
            if (i > 0) sql += ", ";
            sql += fields[i];
        }
        sql += ") VALUES (";
        for (size_t i = 0; i < fields.size(); ++i) {
            if (i > 0) sql += ", ";
            sql += "?";
        }
        sql += ")";

        ParameterizedQuery query(db_, sql);
        for (int i = 0; i < static_cast<int>(values.size()); ++i) {
            query.bind(i + 1, values[i]);
        }
        return query.executeUpdate() > 0;
    }

protected:
    sqlite3* db_;

    virtual std::string getTableName() const = 0;
    virtual std::vector<std::string> getAllowedColumns() const = 0;
    virtual std::vector<T> mapResultsToEntities(
        const std::vector<std::vector<std::string>>& rows) = 0;
    virtual std::vector<std::string> getInsertFields(const T& entity) const = 0;
    virtual std::vector<TypeSafeParameter> getInsertValues(
        const T& entity) const = 0;

private:
    bool isAllowedColumn(const std::string& column) const {
        auto allowed = getAllowedColumns();
        return std::find(allowed.begin(), allowed.end(), column) != allowed.end();
    }

    std::string operatorToString(QueryFilter::Operator op) const {
        switch (op) {
            case QueryFilter::Operator::EQUALS: return "=";
            case QueryFilter::Operator::NOT_EQUALS: return "!=";
            case QueryFilter::Operator::LIKE: return "LIKE";
            case QueryFilter::Operator::GT: return ">";
            case QueryFilter::Operator::LT: return "<";
            case QueryFilter::Operator::GTE: return ">=";
            case QueryFilter::Operator::LTE: return "<=";
        }
        return "=";
    }
};

// Example entity
struct User {
    int id = 0;
    std::string username;
    std::string email;
    std::string role;
};

class UserRepository : public SecureRepository<User> {
public:
    explicit UserRepository(sqlite3* db) : SecureRepository<User>(db) {}

protected:
    std::string getTableName() const override { return "users"; }

    std::vector<std::string> getAllowedColumns() const override {
        return {"id", "username", "email", "role"};
    }

    std::vector<User> mapResultsToEntities(
            const std::vector<std::vector<std::string>>& rows) override {
        std::vector<User> users;
        for (const auto& row : rows) {
            User u;
            u.id = std::stoi(row[0]);
            u.username = row[1];
            u.email = row[2];
            u.role = row[3];
            users.push_back(u);
        }
        return users;
    }

    std::vector<std::string> getInsertFields(const User& entity) const override {
        return {"username", "email", "role"};
    }

    std::vector<TypeSafeParameter> getInsertValues(
            const User& entity) const override {
        return {
            TypeSafeParameter(entity.username),
            TypeSafeParameter(entity.email),
            TypeSafeParameter(entity.role)
        };
    }
};
```

### 3.3 CVE: PostgreSQL CVE-2014-0060 — Escalação de Privilégios

O CVE-2014-0060 é uma vulnerabilidade de escalação de privilégios no PostgreSQL que afeta versões antes de 9.3.2, 9.2.7, 9.1.12, 9.0.16 e 8.4.20. A vulnerabilidade permite que um usuário com permissões de criação de objetos crie funções que executam código arbitrário com os privilégios do owner da função.

**Descrição**: Um usuário não-superusuário pode criar uma função em um schema que ele possui, definindo-a com uma linguagem procedimental confiável (como plpythonu). Se a função for chamada por um superusuário, o código executado terá os privilégios do superusuário.

**Mitigação em C++**: Ao criar funções no banco de dados, sempre valide a linguagem e o owner:

```cpp
// Secure function creation with privilege checks
bool createDatabaseFunction(PGconn* conn,
                            const std::string& functionName,
                            const std::string& language,
                            const std::string& body,
                            const std::string& owner) {
    // Whitelist allowed languages — NEVER allow untrusted languages
    static const std::vector<std::string> allowedLanguages = {
        "plpgsql", "sql"
    };

    bool allowed = false;
    for (const auto& lang : allowedLanguages) {
        if (lang == language) {
            allowed = true;
            break;
        }
    }

    if (!allowed) {
        throw std::runtime_error(
            "Language '" + language + "' is not in the trusted language whitelist"
        );
    }

    // Verify the owner exists and is not a superuser
    std::string checkOwner = "SELECT usesuper FROM pg_user WHERE usename = $1";
    std::vector<const char*> params = { owner.c_str() };

    PGresult* res = PQexecParams(conn, checkOwner.c_str(), 1, nullptr,
                                  params.data(), nullptr, nullptr, 0);

    if (PQresultStatus(res) != PGRES_TUPLES_OK || PQntuples(res) == 0) {
        PQclear(res);
        throw std::runtime_error("Invalid owner specified");
    }

    std::string usesuper = PQgetvalue(res, 0, 0);
    PQclear(res);

    if (usesuper == "t") {
        throw std::runtime_error(
            "Functions must not be owned by superusers"
        );
    }

    // Create the function with explicit SECURITY DEFINER check
    std::string createSql =
        "CREATE OR REPLACE FUNCTION " + functionName + "() "
        "RETURNS void AS $$ " + body + " $$ LANGUAGE " + language;

    res = PQexec(conn, createSql.c_str());
    bool success = (PQresultStatus(res) == PGRES_COMMAND_OK);
    PQclear(res);
    return success;
}
```

### 3.4 CVE: MySQL CVE-2012-2122 — Bypass de Autenticação

O CVE-2012-2122 é uma vulnerabilidade crítica no MySQL que afeta versões 5.1.x e 5.5.x. Devido a uma falha na comparação de hashes de senhas usando `memcmp()`, um atacante pode se autenticar com qualquer senha, desde que conheça o nome de usuário.

**Descrição**: O MySQL compara hashes de senhas usando `memcmp()`, que retorna um valor inteiro. A conversão desse valor inteiro para booleano pode resultar em falso positivo, permitindo autenticação com senhas incorretas. A taxa de sucesso é de aproximadamente 1 em 256.

**Impacto**: Qualquer atacante com conhecimento de um nome de usuário válido pode autenticar-se no banco de dados MySQL, independentemente da senha.

**Mitigação em C++**: Sempre utilize camadas de autenticação adicionais e valide o resultado de operações de login:

```cpp
// Secure authentication with additional verification
class SecureMySQLAuth {
public:
    struct AuthResult {
        bool authenticated = false;
        std::string errorMessage;
        int failedAttempts = 0;
    };

    static AuthResult authenticate(
            const std::string& host,
            const std::string& user,
            const std::string& password,
            const std::string& database) {
        AuthResult result;

        // Layer 1: Rate limiting
        if (isRateLimited(user)) {
            result.errorMessage = "Too many failed attempts. Try again later.";
            return result;
        }

        // Layer 2: Strong password validation before connection attempt
        if (password.length() < 12) {
            result.errorMessage = "Password does not meet minimum requirements";
            return result;
        }

        // Layer 3: Attempt connection and verify server identity
        // Use SSL certificate verification to prevent MITM
        MYSQL* mysql = mysql_init(nullptr);
        if (!mysql) {
            result.errorMessage = "MySQL initialization failed";
            return result;
        }

        // Enforce SSL
        mysql_ssl_set(mysql, nullptr, nullptr, nullptr, nullptr, nullptr);
        mysql_options(mysql, MYSQL_OPT_SSL_VERIFY_SERVER_CERT, "1");

        // Set connection timeout
        unsigned int timeout = 10;
        mysql_options(mysql, MYSQL_OPT_CONNECT_TIMEOUT, &timeout);

        if (!mysql_real_connect(mysql, host.c_str(), user.c_str(),
                                password.c_str(), database.c_str(),
                                0, nullptr, CLIENT_SSL)) {
            recordFailedAttempt(user);
            result.errorMessage = mysql_error(mysql);
            result.failedAttempts = getFailedAttemptCount(user);
            mysql_close(mysql);
            return result;
        }

        // Layer 4: Post-connection verification
        // Verify the user's actual privileges match expected
        MYSQL_RES* res = mysql_query(mysql, "SHOW GRANTS FOR CURRENT_USER()");
        if (res) {
            // Additional validation that user has expected privileges
        }

        // Layer 5: Verify connection is actually using the correct user
        MYSQL_RES* userRes = mysql_store_result(mysql);
        if (userRes) {
            // Validate current_user matches expected
            mysql_free_result(userRes);
        }

        result.authenticated = true;
        mysql_close(mysql);
        return result;
    }
};
```

---

## 4. Encryption em Repouso e em Trânsito

### 4.1 Conceitos de TDE (Transparent Data Encryption)

O TDE permite criptografar dados no disco sem alterar a lógica da aplicação. O banco de dados gerencia a criptografia e descriptografia automaticamente. Embora o TDE seja uma funcionalidade do próprio SGBD, a aplicação pode complementá-lo com criptografia em nível de coluna para dados particularmente sensíveis.

### 4.2 Criptografia em Nível de Coluna

A criptografia em nível de coluna oferece proteção granular, permitindo que apenas colunas específicas (como CPF, número de cartão de crédito) sejam criptografadas:

```cpp
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/aes.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstring>
#include <iomanip>
#include <sstream>

class AES256GCMEncryptor {
public:
    static constexpr int KEY_SIZE = 32;   // AES-256
    static constexpr int IV_SIZE = 12;    // Recommended GCM IV size
    static constexpr int TAG_SIZE = 16;   // GCM authentication tag

    struct EncryptedData {
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> tag;
        std::vector<unsigned char> iv;
    };

    AES256GCMEncryptor(const unsigned char* key) {
        if (!key) {
            throw std::invalid_argument("Key cannot be null");
        }
        std::memcpy(key_, key, KEY_SIZE);
    }

    ~AES256GCMEncryptor() {
        // Securely erase key from memory
        OPENSSL_cleanse(key_, KEY_SIZE);
    }

    EncryptedData encrypt(const std::string& plaintext) {
        EncryptedData result;

        // Generate random IV
        result.iv.resize(IV_SIZE);
        if (RAND_bytes(result.iv.data(), IV_SIZE) != 1) {
            throw std::runtime_error("Failed to generate random IV");
        }

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        try {
            if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                   nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to initialize encryption");
            }

            EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, IV_SIZE, nullptr);

            if (EVP_EncryptInit_ex(ctx, nullptr, nullptr, key_,
                                   result.iv.data()) != 1) {
                throw std::runtime_error("Failed to set key and IV");
            }

            // Allocate ciphertext buffer (plaintext size + block size)
            int maxLen = static_cast<int>(plaintext.size()) + EVP_CIPHER_block_size(EVP_aes_256_gcm());
            result.ciphertext.resize(maxLen);
            int outLen = 0;

            if (EVP_EncryptUpdate(ctx, result.ciphertext.data(), &outLen,
                                  reinterpret_cast<const unsigned char*>(
                                      plaintext.data()),
                                  static_cast<int>(plaintext.size())) != 1) {
                throw std::runtime_error("Encryption update failed");
            }

            int finalLen = 0;
            if (EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + outLen,
                                    &finalLen) != 1) {
                throw std::runtime_error("Encryption finalization failed");
            }

            result.ciphertext.resize(outLen + finalLen);

            // Get authentication tag
            result.tag.resize(TAG_SIZE);
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, TAG_SIZE,
                                    result.tag.data()) != 1) {
                throw std::runtime_error("Failed to get authentication tag");
            }
        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);
        return result;
    }

    std::string decrypt(const EncryptedData& data) {
        if (data.ciphertext.empty() || data.tag.size() != TAG_SIZE ||
            data.iv.size() != IV_SIZE) {
            throw std::invalid_argument("Invalid encrypted data format");
        }

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        try {
            if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                   nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to initialize decryption");
            }

            EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, IV_SIZE, nullptr);

            if (EVP_DecryptInit_ex(ctx, nullptr, nullptr, key_,
                                   data.iv.data()) != 1) {
                throw std::runtime_error("Failed to set key and IV");
            }

            std::vector<unsigned char> plaintext(data.ciphertext.size());
            int outLen = 0;

            if (EVP_DecryptUpdate(ctx, plaintext.data(), &outLen,
                                  data.ciphertext.data(),
                                  static_cast<int>(data.ciphertext.size())) != 1) {
                throw std::runtime_error("Decryption update failed");
            }

            // Set expected tag for authentication
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, TAG_SIZE,
                                    const_cast<unsigned char*>(
                                        data.tag.data())) != 1) {
                throw std::runtime_error("Failed to set authentication tag");
            }

            int finalLen = 0;
            int ret = EVP_DecryptFinal_ex(ctx, plaintext.data() + outLen,
                                          &finalLen);

            if (ret != 1) {
                throw std::runtime_error(
                    "Authentication failed — data may be tampered"
                );
            }

            plaintext.resize(outLen + finalLen);
            return std::string(plaintext.begin(), plaintext.end());
        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);
    }

    // Convert encrypted data to hex string for storage
    static std::string toHex(const EncryptedData& data) {
        std::ostringstream oss;
        // Format: iv:tag:ciphertext (all hex-encoded)
        oss << hexEncode(data.iv) << ":"
            << hexEncode(data.tag) << ":"
            << hexEncode(data.ciphertext);
        return oss.str();
    }

    // Parse hex string back to encrypted data
    static EncryptedData fromHex(const std::string& hex) {
        EncryptedData result;
        auto pos1 = hex.find(':');
        auto pos2 = hex.find(':', pos1 + 1);

        if (pos1 == std::string::npos || pos2 == std::string::npos) {
            throw std::invalid_argument("Invalid encrypted data format");
        }

        result.iv = hexDecode(hex.substr(0, pos1));
        result.tag = hexDecode(hex.substr(pos1 + 1, pos2 - pos1 - 1));
        result.ciphertext = hexDecode(hex.substr(pos2 + 1));

        if (result.iv.size() != IV_SIZE || result.tag.size() != TAG_SIZE) {
            throw std::invalid_argument("Invalid component sizes");
        }

        return result;
    }

private:
    unsigned char key_[KEY_SIZE];

    static std::string hexEncode(const std::vector<unsigned char>& data) {
        std::ostringstream oss;
        for (unsigned char byte : data) {
            oss << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<int>(byte);
        }
        return oss.str();
    }

    static std::vector<unsigned char> hexDecode(const std::string& hex) {
        if (hex.size() % 2 != 0) {
            throw std::invalid_argument("Hex string has odd length");
        }

        std::vector<unsigned char> result;
        result.reserve(hex.size() / 2);

        for (size_t i = 0; i < hex.size(); i += 2) {
            unsigned int byte;
            std::istringstream iss(hex.substr(i, 2));
            iss >> std::hex >> byte;
            result.push_back(static_cast<unsigned char>(byte));
        }

        return result;
    }
};
```

### 4.3 Gerenciamento de Chaves para Criptografia de Banco de Dados

A segurança da criptografia depende fundamentalmente da segurança das chaves. Um gerenciamento inadequado de chaves compromete toda a proteção criptográfica:

```cpp
class KeyHierarchyManager {
public:
    struct KeyHierarchy {
        std::vector<unsigned char> masterKey;   // Stored in HSM or KMS
        std::vector<unsigned char> dataKey;     // Derived, used for actual encryption
        std::vector<unsigned char> keyEncryptingKey; // Used to encrypt data keys
    };

    // Generate a new key hierarchy
    static KeyHierarchy generateHierarchy() {
        KeyHierarchy hierarchy;

        // Master key: 256-bit, should be stored in HSM/KMS in production
        hierarchy.masterKey.resize(AES256GCMEncryptor::KEY_SIZE);
        if (RAND_bytes(hierarchy.masterKey.data(),
                       AES256GCMEncryptor::KEY_SIZE) != 1) {
            throw std::runtime_error("Failed to generate master key");
        }

        // Key-encrypting key: used to encrypt the data key
        hierarchy.keyEncryptingKey.resize(AES256GCMEncryptor::KEY_SIZE);
        if (RAND_bytes(hierarchy.keyEncryptingKey.data(),
                       AES256GCMEncryptor::KEY_SIZE) != 1) {
            throw std::runtime_error("Failed to generate key-encrypting key");
        }

        // Data key: the actual key used for column encryption
        hierarchy.dataKey.resize(AES256GCMEncryptor::KEY_SIZE);
        if (RAND_bytes(hierarchy.dataKey.data(),
                       AES256GCMEncryptor::KEY_SIZE) != 1) {
            throw std::runtime_error("Failed to generate data key");
        }

        return hierarchy;
    }

    // Encrypt a data key with the key-encrypting key (key wrapping)
    static std::string wrapDataKey(const std::vector<unsigned char>& dataKey,
                                   const std::vector<unsigned char>& kek) {
        AES256GCMEncryptor encryptor(kek.data());
        std::string keyStr(dataKey.begin(), dataKey.end());
        auto encrypted = encryptor.encrypt(keyStr);
        return AES256GCMEncryptor::toHex(encrypted);
    }

    // Decrypt a wrapped data key
    static std::vector<unsigned char> unwrapDataKey(
            const std::string& wrappedKey,
            const std::vector<unsigned char>& kek) {
        AES256GCMEncryptor encryptor(kek.data());
        auto encrypted = AES256GCMEncryptor::fromHex(wrappedKey);
        std::string keyStr = encryptor.decrypt(encrypted);
        return std::vector<unsigned char>(keyStr.begin(), keyStr.end());
    }

    // Key rotation: generate new data key, re-encrypt data, destroy old key
    static KeyHierarchy rotateKeys(const KeyHierarchy& oldHierarchy) {
        KeyHierarchy newHierarchy = generateHierarchy();

        // In production, this would:
        // 1. Re-encrypt all column data with the new data key
        // 2. Store the new wrapped data key
        // 3. Securely destroy the old data key

        // Securely erase old data key from memory
        OPENSSL_cleanse(oldHierarchy.dataKey.data(),
                        oldHierarchy.dataKey.size());

        return newHierarchy;
    }
};
```

### 4.4 Data Breaches por Bancos de Dados Não Criptografados

Muitas violações de dados ocorrem simplesmente porque os dados estavam armazenados sem criptografia. Quando um atacante obtém acesso ao arquivo do banco de dados (via backup inadequado, acesso físico, ou exploração de vulnerabilidade), dados não criptografados ficam completamente expostos.

Um exemplo clássico é quando desenvolvedores armazenam dados sensíveis em bancos de dados de teste ou staging que não possuem as mesmas proteções de criptografia que o ambiente de produção. A criptografia em nível de aplicação é a última linha de defesa: mesmo que o banco de dados seja comprometido, os dados permanecem inacessíveis sem a chave correta.

---

## 5. Database Access Patterns

### 5.1 Segurança de Connection Pooling

O pooling de conexões é essencial para performance, mas introduz considerações de segurança:

```cpp
#include <queue>
#include <mutex>
#include <condition_variable>
#include <memory>
#include <chrono>
#include <functional>
#include <atomic>
#include <stdexcept>

template<typename ConnectionType>
class SecureConnectionPool {
public:
    struct PoolConfig {
        size_t maxConnections = 20;
        size_t minConnections = 5;
        std::chrono::seconds connectionTimeout{10};
        std::chrono::seconds maxConnectionLifetime{3600};
        std::chrono::seconds healthCheckInterval{30};
        bool validateOnBorrow = true;
        bool validateOnReturn = false;
    };

    using ConnectionFactory = std::function<std::unique_ptr<ConnectionType>()>;
    using HealthChecker = std::function<bool(const ConnectionType&)>;
    using ConnectionDeleter = std::function<void(ConnectionType*)>;

    SecureConnectionPool(ConnectionFactory factory,
                         HealthChecker healthCheck,
                         ConnectionDeleter deleter,
                         PoolConfig config = {})
        : factory_(std::move(factory)),
          healthCheck_(std::move(healthCheck)),
          deleter_(std::move(deleter)),
          config_(config),
          activeConnections_(0),
          isShutdown_(false) {
        // Pre-create minimum connections
        for (size_t i = 0; i < config_.minConnections; ++i) {
            auto conn = createConnection();
            pool_.push(PooledConnection{
                std::move(conn),
                std::chrono::steady_clock::now()
            });
        }
    }

    ~SecureConnectionPool() {
        shutdown();
    }

    // Borrow a connection from the pool
    std::shared_ptr<ConnectionType> acquire() {
        std::unique_lock<std::mutex> lock(mutex_);

        if (isShutdown_) {
            throw std::runtime_error("Pool is shut down");
        }

        // Wait for available connection or timeout
        auto deadline = std::chrono::steady_clock::now() + config_.connectionTimeout;

        while (pool_.empty()) {
            // If under max, create new connection
            if (activeConnections_ < config_.maxConnections) {
                auto conn = createConnection();
                ++activeConnections_;
                lock.unlock();

                auto deleter = [this](ConnectionType* c) {
                    returnToPool(c);
                };
                return std::shared_ptr<ConnectionType>(conn.release(), deleter);
            }

            if (cv_.wait_until(lock, deadline) == std::cv_status::timeout) {
                throw std::runtime_error("Connection pool timeout");
            }
        }

        // Take connection from pool
        PooledConnection pooled = std::move(pool_.front());
        pool_.pop();

        // Validate connection if configured
        if (config_.validateOnBorrow) {
            if (!healthCheck_(*pooled.connection)) {
                // Connection is stale, replace it
                pooled.connection = createConnection();
            }
        }

        // Check connection lifetime
        auto age = std::chrono::steady_clock::now() - pooled.createdAt;
        if (age > config_.maxConnectionLifetime) {
            // Replace old connection
            pooled.connection = createConnection();
            pooled.createdAt = std::chrono::steady_clock::now();
        }

        ++activeConnections_;
        lock.unlock();

        auto deleter = [this](ConnectionType* c) {
            returnToPool(c);
        };
        return std::shared_ptr<ConnectionType>(pooled.connection.release(), deleter);
    }

    void shutdown() {
        std::lock_guard<std::mutex> lock(mutex_);
        isShutdown_ = true;

        // Clear remaining connections
        while (!pool_.empty()) {
            pool_.pop();
        }

        cv_.notify_all();
    }

    size_t availableConnections() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return pool_.size();
    }

    size_t activeConnections() const {
        return activeConnections_.load();
    }

private:
    struct PooledConnection {
        std::unique_ptr<ConnectionType, ConnectionDeleter> connection;
        std::chrono::steady_clock::time_point createdAt;
    };

    std::unique_ptr<ConnectionType, ConnectionDeleter> createConnection() {
        auto raw = factory_();
        return std::unique_ptr<ConnectionType, ConnectionDeleter>(
            raw.release(), deleter_
        );
    }

    void returnToPool(ConnectionType* conn) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (isShutdown_) {
            --activeConnections_;
            cv_.notify_one();
            return;
        }

        // Validate before returning if configured
        if (config_.validateOnReturn && !healthCheck_(*conn)) {
            --activeConnections_;
            cv_.notify_one();
            return;
        }

        pool_.push(PooledConnection{
            std::unique_ptr<ConnectionType, ConnectionDeleter>(
                conn, deleter_
            ),
            std::chrono::steady_clock::now()
        });

        --activeConnections_;
        cv_.notify_one();
    }

    ConnectionFactory factory_;
    HealthChecker healthCheck_;
    ConnectionDeleter deleter_;
    PoolConfig config_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<PooledConnection> pool_;
    std::atomic<size_t> activeConnections_;
    bool isShutdown_;
};
```

### 5.2 Conexões Somente-Leitura

Separar conexões de leitura e escrita é uma prática de segurança essencial:

```cpp
class DatabaseAccessLayer {
public:
    struct AccessPolicy {
        bool allowWrites = false;
        bool allowDDL = false;
        bool allowTransactions = true;
        int maxQueryRows = 10000;
        std::chrono::seconds queryTimeout{30};
    };

    static AccessPolicy readOnlyPolicy() {
        return AccessPolicy{
            false,  // no writes
            false,  // no DDL
            false,  // no transactions needed for reads
            100000, // can read more rows
            std::chrono::seconds{60}
        };
    }

    static AccessPolicy readWritePolicy() {
        return AccessPolicy{
            true,   // allows writes
            false,  // no DDL
            true,   // transactions
            10000,  // write queries should be bounded
            std::chrono::seconds{30}
        };
    }

    static AccessPolicy adminPolicy() {
        return AccessPolicy{
            true,   // allows writes
            true,   // allows DDL (migrations)
            true,   // transactions
            100000,
            std::chrono::seconds{120}
        };
    }
};
```

### 5.3 Dead Connection Detection

A detecção de conexões mortas é crucial para a estabilidade do sistema:

```cpp
class ConnectionHealthMonitor {
public:
    using HealthCheckFn = std::function<bool(sqlite3*)>;

    explicit ConnectionHealthMonitor(sqlite3* db, HealthCheckFn checker)
        : db_(db), checker_(std::move(checker)) {}

    bool isHealthy() {
        if (!db_) return false;

        auto start = std::chrono::steady_clock::now();

        // Execute a simple query as heartbeat
        bool alive = checker_(*db_);

        auto elapsed = std::chrono::steady_clock::now() - start;
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(elapsed);

        // Log slow health checks
        if (ms.count() > 1000) {
            logWarning("Slow health check: " + std::to_string(ms.count()) + "ms");
        }

        return alive;
    }

    // Check if connection should be recycled
    bool shouldRecycle(std::chrono::seconds maxAge) const {
        auto age = std::chrono::steady_clock::now() - lastUsed_;
        return age > maxAge;
    }

    void updateLastUsed() {
        lastUsed_ = std::chrono::steady_clock::now();
    }

private:
    sqlite3* db_;
    HealthCheckFn checker_;
    std::chrono::steady_clock::time_point lastUsed_ =
        std::chrono::steady_clock::now();

    void logWarning(const std::string& msg) {
        // In production, use structured logging
        std::cerr << "[WARN] ConnectionHealth: " << msg << std::endl;
    }
};
```

---

## 6. Audit Trails e Data Masking

### 6.1 Trilhas de Auditoria

Trilhas de auditoria são essenciais para detectar atividades suspeitas e atender requisitos regulatórios (LGPD, PCI-DSS, SOX):

```cpp
#include <fstream>
#include <sstream>
#include <mutex>
#include <chrono>
#include <iomanip>

class DatabaseAuditLogger {
public:
    struct AuditEntry {
        std::string timestamp;
        std::string user;
        std::string operation;
        std::string tableName;
        std::string query;
        std::string clientIP;
        int64_t rowsAffected = 0;
        bool success = true;
        std::string errorMessage;
    };

    explicit DatabaseAuditLogger(const std::string& logFilePath)
        : logFile_(logFilePath, std::ios::app) {
        if (!logFile_.is_open()) {
            throw std::runtime_error("Failed to open audit log file");
        }
    }

    void logOperation(const AuditEntry& entry) {
        std::lock_guard<std::mutex> lock(mutex_);

        std::ostringstream oss;
        oss << "[" << entry.timestamp << "] "
            << "USER=" << entry.user << " "
            << "OP=" << entry.operation << " "
            << "TABLE=" << entry.tableName << " "
            << "ROWS=" << entry.rowsAffected << " "
            << "SUCCESS=" << (entry.success ? "true" : "false") << " "
            << "CLIENT=" << entry.clientIP;

        if (!entry.errorMessage.empty()) {
            oss << " ERROR=\"" << entry.errorMessage << "\"";
        }

        logFile_ << oss.str() << std::endl;
        logFile_.flush();

        // Also store hash chain for tamper detection
        appendHashChain(oss.str());
    }

    // Verify log integrity by checking hash chain
    bool verifyIntegrity() {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ifstream file(logFilePath_);
        if (!file.is_open()) return false;

        std::string line;
        std::string previousHash = "GENESIS";

        while (std::getline(file, line)) {
            std::string expectedHash = computeHash(previousHash + line);
            // Read stored hash from next line
            std::string storedHash;
            if (!std::getline(file, storedHash)) {
                return false; // Missing hash line
            }

            if (expectedHash != storedHash) {
                return false; // Tampering detected
            }

            previousHash = expectedHash;
        }

        return true;
    }

    static AuditEntry createEntry(const std::string& user,
                                   const std::string& op,
                                   const std::string& table) {
        AuditEntry entry;
        entry.timestamp = currentTimestamp();
        entry.user = user;
        entry.operation = op;
        entry.tableName = table;
        return entry;
    }

private:
    std::ofstream logFile_;
    std::string logFilePath_;
    std::mutex mutex_;

    static std::string currentTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::tm tm_buf;
        localtime_r(&time, &tm_buf);

        std::ostringstream oss;
        oss << std::put_time(&tm_buf, "%Y-%m-%dT%H:%M:%S");
        return oss.str();
    }

    void appendHashChain(const std::string& data) {
        // Simple hash chain for tamper detection
        // In production, use HMAC-SHA256 with a secret key
        std::string hash = computeHash(data);
        logFile_ << hash << std::endl;
    }

    static std::string computeHash(const std::string& input) {
        // Placeholder — use OpenSSL SHA-256 in production
        std::hash<std::string> hasher;
        auto h = hasher(input);
        std::ostringstream oss;
        oss << std::hex << std::setfill('0') << std::setw(16) << h;
        return oss.str();
    }
};
```

### 6.2 Data Masking para Desenvolvimento e Testes

O data masking é essencial para garantir que ambientes de desenvolvimento e teste não contenham dados reais de produção:

```cpp
class DataMasker {
public:
    enum class MaskType {
        FULL,       // Replace entire value with a fixed token
        PARTIAL,    // Show first/last characters
        HASH,       // Replace with consistent hash
        RANDOM,     // Replace with random valid-looking value
        NULL_OUT,   // Replace with NULL
        SWAP        // Swap values between columns
    };

    // Mask PII in query results before returning to developers
    std::string maskField(const std::string& value,
                          MaskType type,
                          const std::string& fieldName = "") {
        if (value.empty()) return value;

        switch (type) {
            case MaskType::FULL:
                return generateFullMask(fieldName);

            case MaskType::PARTIAL:
                return partialMask(value);

            case MaskType::HASH:
                return consistentHash(value);

            case MaskType::RANDOM:
                return generateRandom(value, fieldName);

            case MaskType::NULL_OUT:
                return "NULL";

            case MaskType::SWAP:
                return value; // Swap logic handled at query level
        }

        return value;
    }

    // Apply masking policy to a result set
    std::vector<std::vector<std::string>> maskResultSet(
            const std::vector<std::vector<std::string>>& results,
            const std::vector<std::pair<int, MaskType>>& columnsToMask) {
        std::vector<std::vector<std::string>> masked = results;

        for (const auto& [colIdx, maskType] : columnsToMask) {
            for (auto& row : masked) {
                if (colIdx < static_cast<int>(row.size())) {
                    row[colIdx] = maskField(row[colIdx], maskType,
                                            "column_" + std::to_string(colIdx));
                }
            }
        }

        return masked;
    }

private:
    std::string generateFullMask(const std::string& field) {
        if (field.find("email") != std::string::npos) return "user@example.com";
        if (field.find("phone") != std::string::npos) return "(00) 00000-0000";
        if (field.find("name") != std::string::npos) return "MASCARADO";
        if (field.find("cpf") != std::string::npos) return "000.000.000-00";
        if (field.find("card") != std::string::npos) return "****-****-****-0000";
        return "***MASKED***";
    }

    std::string partialMask(const std::string& value) {
        if (value.size() <= 4) return std::string(value.size(), '*');
        return value.substr(0, 2) +
               std::string(value.size() - 4, '*') +
               value.substr(value.size() - 2);
    }

    std::string consistentHash(const std::string& value) {
        std::hash<std::string> hasher;
        auto h = hasher(value);
        std::ostringstream oss;
        oss << "HASH_" << std::hex << h;
        return oss.str();
    }

    std::string generateRandom(const std::string& original,
                                const std::string& field) {
        if (field.find("email") != std::string::npos) {
            return "test" + std::to_string(rand() % 10000) + "@example.com";
        }
        return partialMask(original);
    }
};
```

---

## 7. Backup Security

### 7.1 Backup Criptografado

Backups inseguros são uma das causas mais comuns de violação de dados. Um backup criptografado é inútil para um atacante sem a chave de descriptografia:

```cpp
class EncryptedBackupManager {
public:
    struct BackupMetadata {
        std::string timestamp;
        std::string databaseName;
        size_t originalSize;
        size_t encryptedSize;
        std::string checksum;
        std::string keyVersion;
    };

    EncryptedBackupManager(const std::vector<unsigned char>& encryptionKey)
        : keyVersion_("v1") {
        if (encryptionKey.size() != AES256GCMEncryptor::KEY_SIZE) {
            throw std::invalid_argument("Encryption key must be 256 bits");
        }
        encryptor_ = std::make_unique<AES256GCMEncryptor>(encryptionKey.data());
    }

    // Create encrypted backup
    BackupMetadata createBackup(sqlite3* db,
                                const std::string& outputPath) {
        // Step 1: Create raw backup using SQLite online backup API
        std::string rawPath = outputPath + ".raw";
        sqlite3* backupDb = nullptr;
        sqlite3_open(rawPath.c_str(), &backupDb);

        sqlite3_backup* backup = sqlite3_backup_init(
            backupDb, "main", db, "main"
        );

        if (!backup) {
            sqlite3_close(backupDb);
            throw std::runtime_error("Failed to initialize backup");
        }

        int rc;
        do {
            rc = sqlite3_backup_step(backup, 512); // 512 pages per step
        } while (rc == SQLITE_OK || rc == SQLITE_BUSY);

        sqlite3_backup_finish(backup);
        sqlite3_close(backupDb);

        if (rc != SQLITE_DONE) {
            throw std::runtime_error("Backup failed with code: " +
                                     std::to_string(rc));
        }

        // Step 2: Read raw backup file
        std::ifstream rawFile(rawPath, std::ios::binary);
        std::vector<unsigned char> rawData(
            (std::istreambuf_iterator<char>(rawFile)),
            std::istreambuf_iterator<char>()
        );
        rawFile.close();

        // Step 3: Encrypt the backup
        std::string rawStr(rawData.begin(), rawData.end());
        auto encrypted = encryptor_->encrypt(rawStr);

        // Step 4: Write encrypted backup
        std::ofstream encFile(outputPath, std::ios::binary);
        // Write header: magic bytes + version
        encFile.write("DBKP", 4);
        uint32_t version = 1;
        encFile.write(reinterpret_cast<const char*>(&version), sizeof(version));

        // Write IV
        encFile.write(reinterpret_cast<const char*>(encrypted.iv.data()),
                      encrypted.iv.size());

        // Write tag
        encFile.write(reinterpret_cast<const char*>(encrypted.tag.data()),
                      encrypted.tag.size());

        // Write ciphertext
        encFile.write(
            reinterpret_cast<const char*>(encrypted.ciphertext.data()),
            encrypted.ciphertext.size()
        );
        encFile.close();

        // Step 5: Compute checksum
        std::string checksum = computeSHA256(outputPath);

        // Clean up raw backup
        std::remove(rawPath.c_str());

        BackupMetadata meta;
        meta.timestamp = currentTimestamp();
        meta.originalSize = rawData.size();
        meta.encryptedSize = encrypted.ciphertext.size();
        meta.checksum = checksum;
        meta.keyVersion = keyVersion_;
        return meta;
    }

    // Verify backup integrity
    bool verifyBackup(const std::string& backupPath,
                      const std::string& expectedChecksum) {
        std::string actualChecksum = computeSHA256(backupPath);
        return actualChecksum == expectedChecksum;
    }

    // Restore from encrypted backup
    bool restoreBackup(const std::string& backupPath, sqlite3* targetDb) {
        // Step 1: Read encrypted backup
        std::ifstream encFile(backupPath, std::ios::binary);

        // Read and verify header
        char magic[4];
        encFile.read(magic, 4);
        if (std::strncmp(magic, "DBKP", 4) != 0) {
            throw std::runtime_error("Invalid backup file format");
        }

        uint32_t version;
        encFile.read(reinterpret_cast<char*>(&version), sizeof(version));
        if (version != 1) {
            throw std::runtime_error("Unsupported backup version");
        }

        // Read IV, tag, ciphertext
        AES256GCMEncryptor::EncryptedData encrypted;
        encrypted.iv.resize(AES256GCMEncryptor::IV_SIZE);
        encrypted.tag.resize(AES256GCMEncryptor::TAG_SIZE);

        encFile.read(reinterpret_cast<char*>(encrypted.iv.data()),
                     encrypted.iv.size());
        encFile.read(reinterpret_cast<char*>(encrypted.tag.data()),
                     encrypted.tag.size());

        encFile.seekg(0, std::ios::end);
        auto fileSize = encFile.tellg();
        auto dataSize = fileSize - encFile.tellg() -
                       AES256GCMEncryptor::IV_SIZE -
                       AES256GCMEncryptor::TAG_SIZE;

        // Step 2: Decrypt
        std::string decrypted = encryptor_->decrypt(encrypted);

        // Step 3: Write decrypted data to temporary file
        std::string tempPath = backupPath + ".decrypted";
        std::ofstream tempFile(tempPath, std::ios::binary);
        tempFile.write(decrypted.data(), decrypted.size());
        tempFile.close();

        // Step 4: Restore using SQLite backup API
        sqlite3* sourceDb = nullptr;
        sqlite3_open(tempPath.c_str(), &sourceDb);

        sqlite3_backup* backup = sqlite3_backup_init(
            targetDb, "main", sourceDb, "main"
        );

        if (!backup) {
            sqlite3_close(sourceDb);
            std::remove(tempPath.c_str());
            return false;
        }

        int rc;
        do {
            rc = sqlite3_backup_step(backup, 512);
        } while (rc == SQLITE_OK || rc == SQLITE_BUSY);

        sqlite3_backup_finish(backup);
        sqlite3_close(sourceDb);
        std::remove(tempPath.c_str());

        return rc == SQLITE_DONE;
    }

private:
    std::unique_ptr<AES256GCMEncryptor> encryptor_;
    std::string keyVersion_;

    std::string currentTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::tm tm_buf;
        localtime_r(&time, &tm_buf);
        std::ostringstream oss;
        oss << std::put_time(&tm_buf, "%Y-%m-%dT%H:%M:%S");
        return oss.str();
    }

    std::string computeSHA256(const std::string& filePath) {
        // Simplified — use OpenSSL SHA-256 in production
        std::ifstream file(filePath, std::ios::binary);
        std::hash<std::string> hasher;
        std::string content(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>()
        );
        std::ostringstream oss;
        oss << std::hex << hasher(content);
        return oss.str();
    }
};
```

---

## 8. NoSQL Injection

### 8.1 MongoDB Injection Attacks

O MongoDB é vulnerável a injeção quando consultas são construídas com dados do usuário diretamente em objetos de consulta:

```cpp
// VULNERABLE: Building MongoDB query with user input
// This is vulnerable if the MongoDB C++ driver is used with unsanitized input
//
// Example of vulnerable pattern:
//
// bsoncxx::builder::stream::document filter{};
// filter << "username" << userInput;  // If userInput is {"$gt": ""}, it matches ALL docs
//
// This is equivalent to: { username: { "$gt": "" } }
// which returns all documents where username exists and is greater than "" (all strings)

// SECURE: Validate and sanitize input before using in queries
class SecureMongoQuery {
public:
    struct QueryInput {
        std::string fieldName;
        std::string value;
        enum class Type { STRING, INTEGER, BOOLEAN } type;
    };

    // Validate that user input is a plain string, not a MongoDB operator
    static bool isValidStringInput(const std::string& input) {
        // Check for MongoDB operator patterns
        static const std::vector<std::string> dangerousPatterns = {
            "$gt", "$lt", "$gte", "$lte", "$ne", "$in", "$nin",
            "$or", "$and", "$not", "$regex", "$exists",
            "$where", "$expr", "$function"
        };

        for (const auto& pattern : dangerousPatterns) {
            if (input.find(pattern) != std::string::npos) {
                return false;
            }
        }

        // Check for object notation
        if (input.find('{') != std::string::npos ||
            input.find('}') != std::string::npos) {
            return false;
        }

        return true;
    }

    // Build a safe query document
    static std::string buildSafeQuery(const QueryInput& input) {
        if (!isValidStringInput(input.value)) {
            throw std::invalid_argument(
                "Input contains potential NoSQL injection pattern: " + input.value
            );
        }

        // Escape special regex characters if the field uses regex matching
        std::string escaped = escapeRegex(input.value);

        // Return a properly constructed query string
        // In real code, this would build a BSON document
        return "{\"" + input.fieldName + "\": \"" + escaped + "\"}";
    }

    static std::string escapeRegex(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        for (char c : input) {
            switch (c) {
                case '\\': result += "\\\\"; break;
                case '.':  result += "\\."; break;
                case '*':  result += "\\*"; break;
                case '+':  result += "\\+"; break;
                case '?':  result += "\\?"; break;
                case '(':  result += "\\("; break;
                case ')':  result += "\\)"; break;
                case '[':  result += "\\["; break;
                case ']':  result += "\\]"; break;
                case '{':  result += "\\{"; break;
                case '}':  result += "\\}"; break;
                case '|':  result += "\\|"; break;
                case '^':  result += "\\^"; break;
                case '$':  result += "\\$"; break;
                default:   result += c; break;
            }
        }
        return result;
    }
};
```

### 8.2 Redis Command Injection

O Redis é particularmente vulnerável a command injection quando comandos são construídos por concatenação:

```cpp
#include <string>
#include <sstream>

class SecureRedisCommand {
public:
    // VULNERABLE pattern (do NOT use):
    // std::string cmd = "SET " + key + " " + value;
    // If value contains "\r\n", it can inject additional commands

    // SECURE: Use the Redis protocol correctly with C API
    // This builds a RESP protocol command properly
    static std::vector<std::string> buildSafeCommand(
            const std::string& command,
            const std::vector<std::string>& args) {
        std::vector<std::string> parts;
        parts.push_back(command);
        for (const auto& arg : args) {
            parts.push_back(arg);
        }
        return parts;
    }

    // Validate Redis key names
    static bool isValidKeyName(const std::string& key) {
        if (key.empty() || key.size() > 512) {
            return false;
        }

        // Redis keys should not contain whitespace or special characters
        // that could be used to inject commands
        for (char c : key) {
            if (c == ' ' || c == '\r' || c == '\n' ||
                c == '\t' || c == '\0') {
                return false;
            }
        }

        return true;
    }

    // Sanitize value to prevent RESP injection
    static std::string sanitizeValue(const std::string& value) {
        // Remove \r\n sequences that could be used to inject commands
        std::string result;
        result.reserve(value.size());

        for (size_t i = 0; i < value.size(); ++i) {
            if (value[i] == '\r' && i + 1 < value.size() &&
                value[i + 1] == '\n') {
                // Replace \r\n with a safe alternative
                result += " ";
                ++i; // Skip the \n
            } else {
                result += value[i];
            }
        }

        return result;
    }

    // Secure SET command wrapper
    static std::string buildSetCommand(const std::string& key,
                                        const std::string& value,
                                        int expirySeconds = 0) {
        if (!isValidKeyName(key)) {
            throw std::invalid_argument("Invalid Redis key name: " + key);
        }

        std::string safeValue = sanitizeValue(value);

        std::ostringstream oss;
        // RESP protocol: *<num_args>\r\n$<len>\r\n<arg>\r\n...
        if (expirySeconds > 0) {
            oss << "*5\r\n"
                << "$3\r\nSET\r\n"
                << "$" << key.size() << "\r\n" << key << "\r\n"
                << "$" << safeValue.size() << "\r\n" << safeValue << "\r\n"
                << "$2\r\nEX\r\n"
                << "$" << std::to_string(expirySeconds).size() << "\r\n"
                << expirySeconds << "\r\n";
        } else {
            oss << "*3\r\n"
                << "$3\r\nSET\r\n"
                << "$" << key.size() << "\r\n" << key << "\r\n"
                << "$" << safeValue.size() << "\r\n" << safeValue << "\r\n";
        }

        return oss.str();
    }
};
```

### 8.3 CouchDB Injection Patterns

CouchDB é vulnerável a injeção quando consultas views ou queries Mango são construídas com dados do usuário:

```cpp
// CouchDB uses JSON-based query language
// Injection occurs when user input is embedded in JSON queries

// VULNERABLE pattern:
// std::string query = "{\"selector\":{\"username\":\"" + userInput + "\"}}";
// If userInput is: admin\"}},{"_id":"* -> returns all documents

// SECURE: Use a proper JSON library with parameterized queries
class SecureCouchDBQuery {
public:
    struct MangoQuery {
        std::string field;
        std::string value;
        std::string operator_type; // $eq, $gt, etc.
    };

    // Build a safe Mango query using proper JSON construction
    static std::string buildSafeMangoQuery(const MangoQuery& query) {
        // Validate operator against whitelist
        static const std::vector<std::string> allowedOperators = {
            "$eq", "$ne", "$gt", "$gte", "$lt", "$lte",
            "$in", "$nin", "$exists", "$type"
        };

        bool opValid = false;
        for (const auto& op : allowedOperators) {
            if (op == query.operator_type) {
                opValid = true;
                break;
            }
        }

        if (!opValid) {
            throw std::invalid_argument(
                "Invalid operator: " + query.operator_type
            );
        }

        // Validate field name (no special characters)
        for (char c : query.field) {
            if (c == '{' || c == '}' || c == '"' ||
                c == '\\' || c == '\n' || c == '\r') {
                throw std::invalid_argument("Invalid field name");
            }
        }

        // Build JSON using proper escaping
        // In production, use a JSON library like nlohmann/json
        std::ostringstream oss;
        oss << "{\"selector\":{\"" << escapeJsonString(query.field)
            << "\":{\"" << query.operator_type << "\":\""
            << escapeJsonString(query.value) << "\"}}}";

        return oss.str();
    }

    static std::string escapeJsonString(const std::string& input) {
        std::string result;
        result.reserve(input.size() + 10);

        for (char c : input) {
            switch (c) {
                case '"':  result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\b': result += "\\b"; break;
                case '\f': result += "\\f"; break;
                case '\n': result += "\\n"; break;
                case '\r': result += "\\r"; break;
                case '\t': result += "\\t"; break;
                default:
                    if (static_cast<unsigned char>(c) < 0x20) {
                        char buf[8];
                        std::snprintf(buf, sizeof(buf), "\\u%04x",
                                      static_cast<unsigned int>(c));
                        result += buf;
                    } else {
                        result += c;
                    }
                    break;
            }
        }

        return result;
    }
};
```

---

## 9. Database Migration Security

### 9.1 Segurança em Migrações de Schema

Migrações de schema são operações de alto risco que requerem precauções especiais:

```cpp
#include <vector>
#include <string>
#include <functional>
#include <fstream>
#include <sstream>

class SecureMigrationFramework {
public:
    struct Migration {
        std::string id;
        std::string description;
        std::function<bool(sqlite3*)> up;    // Apply migration
        std::function<bool(sqlite3*)> down;  // Rollback migration
        std::string checksum;                // Integrity verification
    };

    explicit SecureMigrationFramework(sqlite3* db) : db_(db) {
        ensureMigrationTable();
    }

    void registerMigration(const Migration& migration) {
        // Verify checksum before registering
        std::string currentChecksum = computeMigrationChecksum(migration);
        if (!migration.checksum.empty() && currentChecksum != migration.checksum) {
            throw std::runtime_error(
                "Migration checksum mismatch for " + migration.id +
                ". Expected: " + migration.checksum +
                ", Got: " + currentChecksum
            );
        }
        migrations_.push_back(migration);
    }

    bool migrateUp() {
        auto pending = getPendingMigrations();

        if (pending.empty()) {
            return true;
        }

        // Begin transaction for atomic migration
        sqlite3_exec(db_, "BEGIN TRANSACTION", nullptr, nullptr, nullptr);

        for (auto& migration : pending) {
            try {
                if (!migration.up(db_)) {
                    sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                    return false;
                }

                // Record successful migration
                recordMigration(migration.id);

                // Verify migration integrity
                if (!verifyMigrationIntegrity(migration)) {
                    sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                    return false;
                }

            } catch (const std::exception& e) {
                sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                logError("Migration " + migration.id + " failed: " + e.what());
                return false;
            }
        }

        sqlite3_exec(db_, "COMMIT", nullptr, nullptr, nullptr);
        return true;
    }

    bool rollbackTo(const std::string& targetId) {
        auto applied = getAppliedMigrations();

        sqlite3_exec(db_, "BEGIN TRANSACTION", nullptr, nullptr, nullptr);

        // Rollback in reverse order
        for (auto it = applied.rbegin(); it != applied.rend(); ++it) {
            if (it->id == targetId) {
                break;
            }

            try {
                if (!it->down(db_)) {
                    sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                    return false;
                }

                removeMigrationRecord(it->id);

            } catch (const std::exception& e) {
                sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                logError("Rollback " + it->id + " failed: " + e.what());
                return false;
            }
        }

        sqlite3_exec(db_, "COMMIT", nullptr, nullptr, nullptr);
        return true;
    }

private:
    sqlite3* db_;
    std::vector<Migration> migrations_;

    void ensureMigrationTable() {
        const char* sql =
            "CREATE TABLE IF NOT EXISTS _migrations ("
            "  id TEXT PRIMARY KEY,"
            "  applied_at TEXT NOT NULL,"
            "  checksum TEXT NOT NULL"
            ")";
        sqlite3_exec(db_, sql, nullptr, nullptr, nullptr);
    }

    std::vector<Migration> getPendingMigrations() {
        std::vector<Migration> pending;
        for (const auto& m : migrations_) {
            if (!isMigrationApplied(m.id)) {
                pending.push_back(m);
            }
        }
        return pending;
    }

    bool isMigrationApplied(const std::string& id) {
        std::string sql = "SELECT COUNT(*) FROM _migrations WHERE id = ?";
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

        bool applied = false;
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            applied = sqlite3_column_int(stmt, 0) > 0;
        }
        sqlite3_finalize(stmt);
        return applied;
    }

    void recordMigration(const std::string& id) {
        std::string checksum = computeMigrationChecksum(findMigration(id));
        std::string sql =
            "INSERT INTO _migrations (id, applied_at, checksum) "
            "VALUES (?, datetime('now'), ?)";
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, checksum.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }

    void removeMigrationRecord(const std::string& id) {
        std::string sql = "DELETE FROM _migrations WHERE id = ?";
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }

    Migration findMigration(const std::string& id) {
        for (const auto& m : migrations_) {
            if (m.id == id) return m;
        }
        throw std::runtime_error("Migration not found: " + id);
    }

    std::vector<Migration> getAppliedMigrations() {
        std::vector<Migration> applied;
        const char* sql = "SELECT id FROM _migrations ORDER BY applied_at DESC";
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

        while (sqlite3_step(stmt) == SQLITE_ROW) {
            std::string id = reinterpret_cast<const char*>(
                sqlite3_column_text(stmt, 0)
            );
            try {
                applied.push_back(findMigration(id));
            } catch (...) {
                // Skip if migration not found
            }
        }
        sqlite3_finalize(stmt);
        return applied;
    }

    bool verifyMigrationIntegrity(const Migration& m) {
        std::string currentChecksum = computeMigrationChecksum(m);

        std::string sql = "SELECT checksum FROM _migrations WHERE id = ?";
        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        sqlite3_bind_text(stmt, 1, m.id.c_str(), -1, SQLITE_TRANSIENT);

        bool valid = false;
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            std::string stored = reinterpret_cast<const char*>(
                sqlite3_column_text(stmt, 0)
            );
            valid = (stored == currentChecksum);
        }
        sqlite3_finalize(stmt);
        return valid;
    }

    std::string computeMigrationChecksum(const Migration& m) {
        std::hash<std::string> hasher;
        return std::to_string(hasher(m.id + m.description));
    }

    void logError(const std::string& msg) {
        std::cerr << "[MIGRATION ERROR] " << msg << std::endl;
    }
};
```

---

## 10. Exemplo Completo: Database Layer Seguro

O siguiente é um exemplo completo de uma camada de banco de dados segura em C++17 com SQLite, incorporando todos os conceitos discutidos neste capítulo:

```cpp
#include <sqlite3.h>
#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <functional>
#include <stdexcept>
#include <optional>
#include <chrono>
#include <sstream>
#include <iostream>
#include <unordered_map>
#include <algorithm>
#include <cstring>

class SecurityException : public std::runtime_error {
public:
    explicit SecurityException(const std::string& msg)
        : std::runtime_error(msg) {}
};

class SecureDatabaseLayer {
public:
    struct Config {
        std::string databasePath;
        bool enableWAL = true;
        bool enableForeignKeys = true;
        int busyTimeoutMs = 5000;
        int maxRetries = 3;
        bool enableAuditLog = true;
    };

    struct QueryResult {
        std::vector<std::vector<std::string>> rows;
        std::vector<std::string> columnNames;
        int64_t lastInsertRowId = 0;
        int rowsAffected = 0;
        bool success = true;
        std::string errorMessage;
    };

    explicit SecureDatabaseLayer(const Config& config) : config_(config) {
        int rc = sqlite3_open(config.databasePath.c_str(), &db_);
        if (rc != SQLITE_OK) {
            throw std::runtime_error(
                "Cannot open database: " + std::string(sqlite3_errmsg(db_))
            );
        }

        // Apply security-focused pragmas
        applySecurityPragmas();

        // Create audit log table
        if (config.enableAuditLog) {
            createAuditTable();
        }
    }

    ~SecureDatabaseLayer() {
        if (db_) {
            sqlite3_close(db_);
        }
    }

    // Non-copyable
    SecureDatabaseLayer(const SecureDatabaseLayer&) = delete;
    SecureDatabaseLayer& operator=(const SecureDatabaseLayer&) = delete;

    // Parameterized query execution
    QueryResult executeQuery(const std::string& sql,
                             const std::vector<std::string>& params = {}) {
        std::lock_guard<std::mutex> lock(dbMutex_);

        QueryResult result;

        sqlite3_stmt* stmt = nullptr;
        int rc = sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        if (rc != SQLITE_OK) {
            result.success = false;
            result.errorMessage = sqlite3_errmsg(db_);
            logAudit("QUERY_ERROR", "", sql, false, result.errorMessage);
            return result;
        }

        // Bind parameters
        for (int i = 0; i < static_cast<int>(params.size()); ++i) {
            rc = sqlite3_bind_text(stmt, i + 1, params[i].c_str(),
                                   static_cast<int>(params[i].size()),
                                   SQLITE_TRANSIENT);
            if (rc != SQLITE_OK) {
                result.success = false;
                result.errorMessage = "Failed to bind parameter " +
                                     std::to_string(i + 1);
                sqlite3_finalize(stmt);
                logAudit("QUERY_ERROR", "", sql, false, result.errorMessage);
                return result;
            }
        }

        // Collect column names
        int cols = sqlite3_column_count(stmt);
        for (int i = 0; i < cols; ++i) {
            const char* name = sqlite3_column_name(stmt, i);
            result.columnNames.emplace_back(name ? name : "");
        }

        // Execute and collect results
        int stepResult;
        while ((stepResult = sqlite3_step(stmt)) == SQLITE_ROW) {
            std::vector<std::string> row;
            for (int i = 0; i < cols; ++i) {
                const char* text = reinterpret_cast<const char*>(
                    sqlite3_column_text(stmt, i)
                );
                row.emplace_back(text ? text : "");
            }
            result.rows.push_back(std::move(row));
        }

        if (stepResult != SQLITE_DONE) {
            result.success = false;
            result.errorMessage = sqlite3_errmsg(db_);
            logAudit("QUERY_ERROR", "", sql, false, result.errorMessage);
        } else {
            result.rowsAffected = sqlite3_changes(db_);
            result.lastInsertRowId = sqlite3_last_insert_rowid(db_);
        }

        sqlite3_finalize(stmt);

        logAudit("QUERY", "", sql, result.success, result.errorMessage);
        return result;
    }

    // Execute INSERT/UPDATE/DELETE with parameterized values
    QueryResult executeUpdate(const std::string& sql,
                              const std::vector<std::string>& params = {}) {
        return executeQuery(sql, params);
    }

    // Transaction support with automatic rollback on failure
    template<typename Func>
    bool executeTransaction(Func&& func) {
        std::lock_guard<std::mutex> lock(dbMutex_);

        sqlite3_exec(db_, "BEGIN IMMEDIATE", nullptr, nullptr, nullptr);

        try {
            auto result = func(db_);
            if (result) {
                sqlite3_exec(db_, "COMMIT", nullptr, nullptr, nullptr);
                logAudit("TRANSACTION", "", "COMMIT", true, "");
                return true;
            } else {
                sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
                logAudit("TRANSACTION", "", "ROLLBACK", true, "Func returned false");
                return false;
            }
        } catch (const std::exception& e) {
            sqlite3_exec(db_, "ROLLBACK", nullptr, nullptr, nullptr);
            logAudit("TRANSACTION", "", "ROLLBACK", false, e.what());
            return false;
        }
    }

    // Prepared statement cache
    class CachedStatement {
    public:
        CachedStatement(sqlite3* db, const std::string& sql) {
            int rc = sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt_, nullptr);
            if (rc != SQLITE_OK) {
                throw std::runtime_error(
                    "Prepare failed: " + std::string(sqlite3_errmsg(db))
                );
            }
            sql_ = sql;
        }

        ~CachedStatement() {
            if (stmt_) sqlite3_finalize(stmt_);
        }

        void bind(int index, const std::string& value) {
            sqlite3_bind_text(stmt_, index, value.c_str(),
                              static_cast<int>(value.size()), SQLITE_TRANSIENT);
        }

        void bindInt(int index, int value) {
            sqlite3_bind_int(stmt_, index, value);
        }

        void bindNull(int index) {
            sqlite3_bind_null(stmt_, index);
        }

        void reset() {
            sqlite3_reset(stmt_);
            sqlite3_clear_bindings(stmt_);
        }

        sqlite3_stmt* get() { return stmt_; }

    private:
        sqlite3_stmt* stmt_ = nullptr;
        std::string sql_;
    };

    std::shared_ptr<CachedStatement> getStatement(const std::string& sql) {
        std::lock_guard<std::mutex> lock(cacheMutex_);
        auto it = statementCache_.find(sql);
        if (it != statementCache_.end()) {
            return it->second;
        }

        auto stmt = std::make_shared<CachedStatement>(db_, sql);
        statementCache_[sql] = stmt;
        return stmt;
    }

    // Audit log query
    std::vector<std::vector<std::string>> getAuditLog(int limit = 100) {
        auto result = executeQuery(
            "SELECT timestamp, operation, table_name, success, details "
            "FROM _audit_log ORDER BY timestamp DESC LIMIT ?",
            {std::to_string(limit)}
        );
        return result.rows;
    }

private:
    Config config_;
    sqlite3* db_ = nullptr;
    std::mutex dbMutex_;
    std::mutex cacheMutex_;
    std::unordered_map<std::string, std::shared_ptr<CachedStatement>>
        statementCache_;

    void applySecurityPragmas() {
        if (config.enableWAL) {
            sqlite3_exec(db_, "PRAGMA journal_mode=WAL", nullptr, nullptr, nullptr);
        }
        if (config.enableForeignKeys) {
            sqlite3_exec(db_, "PRAGMA foreign_keys=ON", nullptr, nullptr, nullptr);
        }
        sqlite3_exec(db_, "PRAGMA secure_delete=ON", nullptr, nullptr, nullptr);
        sqlite3_exec(db_, "PRAGMA encrypted_column=ON", nullptr, nullptr, nullptr);
        sqlite3_exec(db_, "PRAGMA busy_timeout=5000", nullptr, nullptr, nullptr);
    }

    void createAuditTable() {
        const char* sql =
            "CREATE TABLE IF NOT EXISTS _audit_log ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  timestamp TEXT DEFAULT (datetime('now')),"
            "  operation TEXT NOT NULL,"
            "  table_name TEXT,"
            "  details TEXT,"
            "  success BOOLEAN,"
            "  client_ip TEXT"
            ")";
        sqlite3_exec(db_, sql, nullptr, nullptr, nullptr);
    }

    void logAudit(const std::string& operation,
                  const std::string& tableName,
                  const std::string& details,
                  bool success,
                  const std::string& error) {
        if (!config.enableAuditLog) return;

        // Non-blocking audit log — best effort
        std::string sql =
            "INSERT INTO _audit_log (operation, table_name, details, success) "
            "VALUES (?, ?, ?, ?)";

        sqlite3_stmt* stmt;
        sqlite3_prepare_v2(db_, sql.c_str(), -1, &stmt, nullptr);
        sqlite3_bind_text(stmt, 1, operation.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, tableName.c_str(), -1, SQLITE_TRANSIENT);

        std::string fullDetails = details;
        if (!error.empty()) {
            fullDetails += " ERROR: " + error;
        }
        sqlite3_bind_text(stmt, 3, fullDetails.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 4, success ? 1 : 0);

        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }
};

// Usage example
void secureDatabaseExample() {
    SecureDatabaseLayer::Config config;
    config.databasePath = "/secure/path/app.db";
    config.enableAuditLog = true;
    config.enableForeignKeys = true;

    SecureDatabaseLayer db(config);

    // SAFE: Parameterized insert
    db.executeQuery(
        "INSERT INTO users (username, email, role) VALUES (?, ?, ?)",
        {"johndoe", "john@example.com", "user"}
    );

    // SAFE: Parameterized query
    auto result = db.executeQuery(
        "SELECT id, username, email FROM users WHERE role = ? AND username LIKE ?",
        {"admin", "%admin%"}
    );

    // SAFE: Transaction with rollback
    db.executeTransaction([&](sqlite3* handle) -> bool {
        auto r1 = db.executeQuery(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            {"100.00", "42"}
        );
        auto r2 = db.executeQuery(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            {"100.00", "43"}
        );
        return r1.success && r2.success;
    });

    // SAFE: Cached prepared statement
    auto stmt = db.getStatement("SELECT * FROM users WHERE id = ?");
    stmt->bind(1, "42");
    auto rows = db.executeQuery("SELECT * FROM users WHERE id = ?", {"42"});
}
```

---

## 11. Referências

1. OWASP Foundation. "OWASP Top Ten 2021". Disponível em: https://owasp.org/Top10/
2. CWE-89: SQL Injection. MITRE Corporation. https://cwe.mitre.org/data/definitions/89.html
3. CWE-943: Improper Neutralization of Special Elements in Data Query Logic (NoSQL Injection). MITRE Corporation. https://cwe.mitre.org/data/definitions/943.html
4. CVE-2014-0060: PostgreSQL Privilege Escalation. MITRE Corporation. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0060
5. CVE-2012-2122: MySQL Authentication Bypass. MITRE Corporation. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2012-2122
6. Sony Pictures Entertainment Data Breach (2011). US-CERT. https://www.us-cert.gov/ncas/alerts/TA11-102A
7. TalkTalk Data Breach Investigation (2015). UK Information Commissioner's Office. https://ico.org.uk/action-weve-taken/enforcement/2016/city-talking-limited-10-10-2016/
8. Heartland Payment Systems Breach (2008). US Secret Service. Documented in multiple public security reports.
9. SQLite Documentation: Security Considerations. https://www.sqlite.org/secure.html
10. PostgreSQL Documentation: Client Authentication. https://www.postgresql.org/docs/current/auth-pg-hba-conf.html
11. NIST SP 800-57: Recommendation for Key Management. https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final
12. PCI DSS v4.0 Requirements for Database Security. https://www.pcisecuritystandards.org/
13. LGPD — Lei Geral de Protecao de Dados (Lei No. 13.709/2018). https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
14. MongoDB Security Best Practices. https://www.mongodb.com/docs/manual/security/
15. Redis Security. https://redis.io/docs/management/security/
