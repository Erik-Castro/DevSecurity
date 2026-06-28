# Database Hardening

## Visao Geral

Database hardening e o processo de proteger um banco de dados contra ameacas e vulnerabilidades. Inclui configuracao segura, criptografia, gerenciamento de acesso, auditoria e monitoramento. Este capitulo explora as melhores praticas para endurecer bancos de dados PostgreSQL e MySQL, desde a instalacao segura ate configuracoes avancadas de seguranca.

## Instalacao Segura

### Preparacao do Ambiente

```bash
# Antes de instalar o banco de dados, preparar o ambiente

# 1. Criar usuario dedicado para o banco de dados
sudo useradd -r -s /bin/false postgresql
sudo useradd -r -s /bin/false mysql

# 2. Criar diretorios com permissoes adequadas
sudo mkdir -p /var/lib/postgresql/data
sudo chown postgresql:postgresql /var/lib/postgresql/data
sudo chmod 700 /var/lib/postgresql/data

sudo mkdir -p /var/lib/mysql
sudo chown mysql:mysql /var/lib/mysql
sudo chmod 700 /var/lib/mysql

# 3. Configurar firewall
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 10.0.0.0/8 to any port 3306
sudo ufw deny 5432
sudo ufw deny 3306

# 4. Configurar SELinux/AppArmor
# PostgreSQL
sudo setsebool -P postgresql_can_rsync on
sudo semanage port -a -t postgresql_port_t -p tcp 5432

# MySQL
sudo aa-enforce /etc/apparmor.d/usr.sbin.mysqld

# 5. Desabilitar servicos desnecessarios
sudo systemctl disable avahi-daemon
sudo systemctl disable cups
sudo systemctl disable bluetooth
```

### Instalacao Segura do PostgreSQL

```bash
# Instalar PostgreSQL de forma segura

# Ubuntu/Debian
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y postgresql-15 postgresql-client-15

# Configurar pg_hba.conf para acesso restrito
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Formato: TYPE  DATABASE  USER  ADDRESS  METHOD
# Permitir apenas de rede interna
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             128.127.0.0/24          scram-sha-256
host    all             all             10.0.0.0/8              scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
host    all             all             192.168.0.0/16          scram-sha-256
host    replication     replica_user    10.0.0.0/8              scram-sha-256

# Negar todos os outros acessos
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject

# Configurar postgresql.conf
sudo nano /etc/postgresql/15/main/postgresql.conf

# Configuracoes de seguranca
listen_addresses = 'localhost,10.0.1.50'  # Escutar apenas em IPs especificos
port = 5432
max_connections = 100
superuser_reserved_connections = 3

# Autenticacao
password_encryption = scram-sha-256

# Criptografia
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
ssl_ca_file = '/etc/ssl/certs/ca.crt'

# Logging
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %q%u@%d '
log_statement = 'ddl'
log_min_duration_statement = 1000  # Log queries > 1s

# Protecoes
shared_preload_libraries = 'pg_stat_statements'
track_activities = on
track_counts = on
track_functions = all
track_io_timing = on

# Reload configuracao
sudo systemctl reload postgresql
```

### Instalacao Segura do MySQL

```bash
# Instalar MySQL de forma segura

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y mysql-server mysql-client

# Executar secure installation
sudo mysql_secure_installation

# Responder as perguntas:
# - Remove anonymous users? Y
# - Disallow root login remotely? Y
# - Remove test database? Y
# - Reload privilege tables now? Y

# Configurar my.cnf
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

[mysqld]
# Configuracoes de seguranca
bind-address = 127.0.0.1  # Apenas localhost
# bind-address = 10.0.1.50  # Ou IP especifico
port = 3306
skip-networking = 0  # Manter ligado para conexoes locais

# Autenticacao
default_authentication_plugin = mysql_native_password
validate_password.policy = MEDIUM
validate_password.length = 12
validate_password.mixed_case_count = 1
validate_password.number_count = 1
validate_password.special_char_count = 1

# Criptografia
require_secure_transport = ON
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem

# Logging
general_log = 0  # Desabilitar geral log (sensiveis)
general_log_file = /var/log/mysql/general.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
log_error = /var/log/mysql/error.log
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW
expire_logs_days = 14

# Protecoes
local_infile = 0
symbolic-links = 0
max_connect_errors = 10
wait_timeout = 600
interactive_timeout = 600

# Reiniciar MySQL
sudo systemctl restart mysql
```

## Configuracao de Rede

### Bind Address e Portas

```bash
# Configurar bind address para restringir acesso

# PostgreSQL: postgresql.conf
listen_addresses = 'localhost'  # Apenas local
# listen_addresses = 'localhost,10.0.1.50'  # Local + IP especifico
# listen_addresses = '*'  # Todos (NAO RECOMENDADO)

# MySQL: my.cnf
bind-address = 127.0.0.1  # Apenas local
# bind-address = 10.0.1.50  # IP especifico
# bind-address = 0.0.0.0  # Todos (NAO RECOMENDADO)

# Portas padrao
# PostgreSQL: 5432
# MySQL: 3306

# Mudar porta (obscurity, nao seguranca)
# PostgreSQL: port = 5433
# MySQL: port = 3307

# Verificar portas em uso
sudo netstat -tlnp | grep postgres
sudo netstat -tlnp | grep mysql

# Verificar bind address
ss -tlnp | grep postgres
ss -tlnp | grep mysql
```

### Configuracao de Firewall

```bash
# Configurar UFW para PostgreSQL
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.0.0/8 to any port 5432 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 5432 proto tcp
sudo ufw deny 5432
sudo ufw enable

# Configurar UFW para MySQL
sudo ufw allow from 10.0.0.0/8 to any port 3306 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 3306 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 3306 proto tcp
sudo ufw deny 3306

# Configurar iptables (alternativa)
sudo iptables -A INPUT -p tcp --dport 5432 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5432 -s 172.16.0.0/12 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5432 -s 192.168.0.0/16 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5432 -j DROP

sudo iptables -A INPUT -p tcp --dport 3306 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -s 172.16.0.0/12 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -s 192.168.0.0/16 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3306 -j DROP

# Verificar regras
sudo iptables -L -n | grep -E '(5432|3306)'
```

### SSH Tunneling

```bash
# Usar SSH tunnel para acesso seguro

# PostgreSQL via SSH tunnel
ssh -L 5432:localhost:5432 user@db-server
# Acessar localmente: psql -h localhost -p 5432 -U user dbname

# MySQL via SSH tunnel
ssh -L 3306:localhost:3306 user@db-server
# Acessar localmente: mysql -h localhost -P 3306 -u user -p

# SSH tunnel com chave publica
ssh-keygen -t ed25519 -C "db-access"
ssh-copy-id user@db-server

# Configurar SSH tunnel persistente com autossh
autossh -M 0 -f -N -L 5432:localhost:5432 user@db-server
# -M 0: desabilitar monitoramento
# -f: background
# -N: sem comando remoto
# -L: local forwarding

# Verificar tunnel
ps aux | grep ssh | grep 5432
netstat -tlnp | grep 5432
```

## Autenticacao

### Password Policies

```sql
-- Configurar politicas de senha fortes

-- PostgreSQL: criar usuario com senha forte
CREATE USER app_user WITH
    PASSWORD 'V3ry$tr0ngP@ssw0rd!2024'
    LOGIN
    CONNECTION LIMIT 10
    VALID UNTIL '2025-12-31';

-- PostgreSQL: plugins de validacao de senha
-- Usar extensao passwordcheck
CREATE EXTENSION IF NOT EXISTS passwordcheck;

-- Configurar em postgresql.conf
-- shared_preload_libraries = 'passwordcheck'

-- MySQL: criar usuario com politicas
CREATE USER 'app_user'@'10.0.1.50' IDENTIFIED BY 'V3ry$tr0ngP@ssw0rd!2024'
    PASSWORD EXPIRE INTERVAL 90 DAY
    FAILED_LOGIN_ATTEMPTS 3
    PASSWORD_LOCK_TIME 1;

-- MySQL: validar politicas de senha
-- Configurar em my.cnf:
-- validate_password.policy = MEDIUM
-- validate_password.length = 12
-- validate_password.mixed_case_count = 1
-- validate_password.number_count = 1
-- validate_password.special_char_count = 1

-- Verificar politicas atuais
SHOW VARIABLES LIKE 'validate_password%';

-- PostgreSQL: funcao para verificar forca da senha
CREATE OR REPLACE FUNCTION check_password_strength(password TEXT)
RETURNS INTEGER AS $$
DECLARE
    strength INTEGER := 0;
BEGIN
    -- Comprimento minimo
    IF LENGTH(password) >= 8 THEN strength := strength + 1; END IF;
    IF LENGTH(password) >= 12 THEN strength := strength + 1; END IF;
    
    -- Letras maiusculas
    IF password ~ '[A-Z]' THEN strength := strength + 1; END IF;
    
    -- Letras minusculas
    IF password ~ '[a-z]' THEN strength := strength + 1; END IF;
    
    -- Numeros
    IF password ~ '[0-9]' THEN strength := strength + 1; END IF;
    
    -- Caracteres especiais
    IF password ~ '[!@#$%^&*(),.?":{}|<>]' THEN strength := strength + 1; END IF;
    
    -- Sem padroes comuns
    IF password !~ '(123|abc|password|qwerty)' THEN strength := strength + 1; END IF;
    
    RETURN strength;
END;
$$ LANGUAGE plpgsql;

-- Usar funcao
SELECT check_password_strength('MinhaSenhaForte!2024');
-- Retorna: 7 (forte)
```

### SSL/TLS Authentication

```sql
-- Configurar autenticacao via SSL/TLS

-- PostgreSQL: gerar certificados
-- 1. Gerar CA (Certificate Authority)
openssl req -new -x509 -days 365 -nodes -text \
    -out ca.crt -keyout ca.key \
    -subj "/CN=PostgreSQL-CA"

# 2. Gerar certificado do servidor
openssl req -new -nodes -text \
    -out server.csr -keyout server.key \
    -subj "/CN=db-server"
openssl x509 -req -in server.csr -days 365 \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt

# 3. Gerar certificado do cliente
openssl req -new -nodes -text \
    -out client.csr -keyout client.key \
    -subj "/CN=app-user"
openssl x509 -req -in client.csr -days 365 \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt

# 4. Configurar permissoes
chmod 600 ca.key server.key client.key
chmod 644 ca.crt server.crt client.crt

# 5. Configurar PostgreSQL
# postgresql.conf:
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
ssl_ca_file = '/etc/ssl/certs/ca.crt'
ssl_crl_file = ''
ssl_prefer_server_ciphers = on
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
ssl_min_protocol_version = 'TLSv1.2'

# 6. Configurar pg_hba.conf para exigir SSL
hostssl all all 10.0.0.0/8 scram-sha-256
hostnossl all all 10.0.0.0/8 reject

-- MySQL: gerar certificados
# Mesmo processo do PostgreSQL

# Configurar MySQL
# my.cnf:
[mysqld]
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem
require_secure_transport = ON
ssl-cipher = 'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256'
tls_version = 'TLSv1.2,TLSv1.3'

# Criar usuario que exige SSL
CREATE USER 'secure_user'@'%' IDENTIFIED BY 'password'
    REQUIRE SSL;

# Verificar SSL ativo
SHOW VARIABLES LIKE '%ssl%';

-- Conexao com SSL
psql "sslmode=verify-full sslcert=/path/to/client.crt sslkey=/path/to/client.key sslrootcert=/path/to/ca.crt host=db-server dbname=mydb user=app_user"
```

### Multi-Factor Authentication

```sql
-- Configurar MFA para acesso ao banco

-- PostgreSQL: usar extensao ou integracao externa
-- 1. Usar LDAP para autenticacao
-- Configurar em pg_hba.conf:
-- host all all 10.0.0.0/8 ldap ldapserver=ldap.example.com ldapprefix="cn=" ldapsuffix=",ou=users,dc=example,dc=com"

-- 2. Usar RADIUS
-- Instalar extensao radius
-- CREATE EXTENSION radius;
-- Configurar autenticacao via RADIUS

-- 3. Usar certificados de cliente (2FA via certificado)
-- Configurar em pg_hba.conf:
-- hostssl all all 10.0.0.0/8 cert

-- MySQL: usar plugins de autenticacao
-- 1. LDAP authentication
-- Instalar plugin: INSTALL PLUGIN authLDAP SONAME 'authLDAP.so';
-- Configurar: CREATE USER 'user'@'%' IDENTIFIED WITH authLDAP AS 'ldap://ldap.example.com, cn=, ou=users, dc=example, dc=com';

-- 2. PAM authentication
-- Instalar plugin: INSTALL PLUGIN auth_pam SONAME 'auth_pam.so';
-- Configurar: CREATE USER 'user'@'%' IDENTIFIED WITH auth_pam;

-- 3. Two-factor authentication via application
-- Implementar na aplicacao: primeira senha + segundo fator (TOTP, SMS)
```

## Encryption at Rest

### Transparent Data Encryption (TDE)

```sql
-- TDE criptografa dados em disco automaticamente

-- PostgreSQL: usar extensao ou filesystem encryption
-- 1. pgcrypto extensao para criptografia de colunas
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Criptografar dados sensiveis
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    credit_card BYTEA,  -- Armazenar criptografado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados criptografados
INSERT INTO customers (name, email, credit_card)
VALUES (
    'Joao Silva',
    'joao@email.com',
    pgp_sym_encrypt('1234-5678-9012-3456', 'senha_forte_aqui')
);

-- Ler dados descriptografados
SELECT
    name,
    email,
    pgp_sym_decrypt(credit_card, 'senha_forte_aqui') as credit_card
FROM customers;

-- 2. Criptografia de tabela inteira
CREATE TABLE customers_encrypted (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    credit_card_encrypted BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Funcao para criptografar antes de inserir
CREATE OR REPLACE FUNCTION encrypt_credit_card()
RETURNS TRIGGER AS $$
BEGIN
    NEW.credit_card_encrypted = pgp_sym_encrypt(NEW.credit_card, current_setting('app.encryption_key'));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER encrypt_before_insert
BEFORE INSERT ON customers_encrypted
FOR EACH ROW
EXECUTE FUNCTION encrypt_credit_card();

-- 3. Usar filesystem encryption (LUKS/dm-crypt)
-- Criptografar volume inteiro
sudo cryptsetup luksFormat /dev/sdb1
sudo cryptsetup luksOpen /dev/sdb1 encrypted_data
sudo mkfs.ext4 /dev/mapper/encrypted_data
sudo mount /dev/mapper/encrypted_data /var/lib/postgresql

-- MySQL: TDE nativo (Enterprise)
-- 1. MySQL Enterprise Edition tem TDE nativo
-- Configurar encription_key_id
-- ALTER TABLE customers ENCRYPTION='Y';

-- 2. Usar InnoDB tablespace encryption
-- Configurar em my.cnf:
-- default_table_encryption=ON
-- innodb_encrypt_tables=ON

-- 3. Criptografia de binlog
-- binlog_encryption=ON
```

### Backup Encryption

```sql
-- Criptografar backups

-- PostgreSQL: backup criptografado com pg_dump
pg_dump -h localhost -U postgres mydb | \
    openssl enc -aes-256-cbc -salt -out backup.sql.enc \
    -pass pass:senha_forte_backup

# Restaurar backup criptografado
openssl enc -aes-256-cbc -d -in backup.sql.enc | \
    psql -h localhost -U postgres mydb

# Usar GPG para criptografia
pg_dump -h localhost -U postgres mydb | \
    gpg --encrypt --recipient user@email.com > backup.sql.gpg

# Restaurar backup GPG
gpg --decrypt backup.sql.gpg | \
    psql -h localhost -U postgres mydb

# MySQL: backup criptografado com mysqldump
mysqldump -h localhost -u root -p mydb | \
    openssl enc -aes-256-cbc -salt -out backup.sql.enc \
    -pass pass:senha_forte_backup

# Restaurar backup MySQL criptografado
openssl enc -aes-256-cbc -d -in backup.sql.enc | \
    mysql -h localhost -u root -p mydb

# Backup com permissao restrita
chmod 600 backup.sql.enc
chown postgres:postgres backup.sql.enc
```

## Encryption in Transit

### Configuracao SSL/TLS

```sql
-- Configurar criptografia em transito

-- PostgreSQL: forcar conexoes SSL
-- Em pg_hba.conf:
-- hostssl all all 10.0.0.0/8 scram-sha-256
-- hostnossl all all 10.0.0.0/8 reject

-- Verificar se SSL esta ativo
SELECT
    datname,
    usename,
    client_addr,
    ssl,
    version,
    cipher,
    bits
FROM pg_stat_ssl s
JOIN pg_stat_activity a ON s.pid = a.pid;

-- Forcar SSL em conexoes especificas
ALTER USER app_user WITH PASSWORD 'new_password';
-- Conexao deve usar sslmode=require ou sslmode=verify-full

-- MySQL: forcar SSL
-- Em my.cnf:
-- require_secure_transport = ON
-- ssl-ca = /etc/mysql/ssl/ca.pem
-- ssl-cert = /etc/mysql/ssl/server-cert.pem
-- ssl-key = /etc/mysql/ssl/server-key.pem

-- Criar usuario que exige SSL
CREATE USER 'secure_user'@'%' IDENTIFIED BY 'password'
    REQUIRE SSL;

-- Verificar SSL ativo
SHOW VARIABLES LIKE '%ssl%';
SHOW STATUS LIKE 'Ssl_cipher';

-- Conexao com SSL
mysql -h db-server -u secure_user -p --ssl-ca=/path/to/ca.pem --ssl-cert=/path/to/client-cert.pem --ssl-key=/path/to/client-key.pem
```

### Certificados e Chaves

```bash
# Gerar e gerenciar certificados SSL

# 1. Gerar CA (Certificate Authority)
openssl genrsa -aes256 -out ca.key 4096
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
    -subj "/CN=Database-CA"

# 2. Gerar certificado do servidor
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/CN=db-server.example.com"
openssl x509 -req -days 365 -in server.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt

# 3. Gerar certificado do cliente
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
    -subj "/CN=app-user"
openssl x509 -req -days 365 -in client.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt

# 4. Configurar permissoes
chmod 600 ca.key server.key client.key
chmod 644 ca.crt server.crt client.crt

# 5. Mover para diretorios seguros
sudo cp ca.crt server.crt client.crt /etc/ssl/certs/
sudo cp ca.key server.key client.key /etc/ssl/private/

# 6. Configurar PostgreSQL
# postgresql.conf:
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
ssl_ca_file = '/etc/ssl/certs/ca.crt'

# 7. Configurar MySQL
# my.cnf:
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem

# 8. Renovar certificados antes de expirar
# Configurar lembretes com certbot ou monitoring
```

## User Management

### Least Privilege

```sql
-- Implementar principio de menor privilegio

-- PostgreSQL: criar roles com privilegios minimos
-- 1. Role de leitura
CREATE ROLE readonly_role;
GRANT CONNECT ON DATABASE mydb TO readonly_role;
GRANT USAGE ON SCHEMA public TO readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO readonly_role;

-- 2. Role de escrita
CREATE ROLE writeonly_role;
GRANT CONNECT ON DATABASE mydb TO writeonly_role;
GRANT USAGE ON SCHEMA public TO writeonly_role;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO writeonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT INSERT, UPDATE, DELETE ON TABLES TO writeonly_role;

-- 3. Role de administracao limitada
CREATE ROLE admin_role;
GRANT CONNECT ON DATABASE mydb TO admin_role;
GRANT USAGE ON SCHEMA public TO admin_role;
GRANT CREATE ON SCHEMA public TO admin_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO admin_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO admin_role;

-- 4. Criar usuarios e atribuir roles
CREATE USER app_readonly WITH PASSWORD 'senha_forte';
GRANT readonly_role TO app_readonly;

CREATE USER app_readwrite WITH PASSWORD 'senha_forte';
GRANT writeonly_role TO app_readwrite;

CREATE USER app_admin WITH PASSWORD 'senha_forte';
GRANT admin_role TO app_admin;

-- MySQL: criar usuarios com privilegios minimos
-- 1. Usuario somente leitura
CREATE USER 'readonly_user'@'10.0.1.50' IDENTIFIED BY 'senha_forte';
GRANT SELECT ON mydb.* TO 'readonly_user'@'10.0.1.50';

-- 2. Usuario de escrita
CREATE USER 'writeonly_user'@'10.0.1.50' IDENTIFIED BY 'senha_forte';
GRANT INSERT, UPDATE, DELETE ON mydb.* TO 'writeonly_user'@'10.0.1.50';

-- 3. Usuario administrador limitado
CREATE USER 'admin_user'@'10.0.1.50' IDENTIFIED BY 'senha_forte';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER ON mydb.* TO 'admin_user'@'10.0.1.50';

-- 4. Revogar privilegios desnecessarios
REVOKE ALL PRIVILEGES ON mydb.* FROM 'app_user'@'%';
GRANT SELECT, INSERT, UPDATE ON mydb.customers TO 'app_user'@'%';
GRANT SELECT ON mydb.products TO 'app_user'@'%';
```

### Role-Based Access Control (RBAC)

```sql
-- Implementar RBAC completo

-- PostgreSQL: criar hierarquia de roles
-- 1. Roles base
CREATE ROLE base_role;
GRANT CONNECT ON DATABASE mydb TO base_role;
GRANT USAGE ON SCHEMA public TO base_role;

-- 2. Roles de funcao
CREATE ROLE viewer_role;
CREATE ROLE editor_role;
CREATE ROLE admin_role;

-- 3. Hierarquia
GRANT base_role TO viewer_role;
GRANT viewer_role TO editor_role;
GRANT editor_role TO admin_role;

-- 4. Privilegios por role
GRANT SELECT ON ALL TABLES IN SCHEMA public TO viewer_role;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO editor_role;
GRANT CREATE, DROP, ALTER ON SCHEMA public TO admin_role;

-- 5. Atribuir roles a usuarios
CREATE USER joao WITH PASSWORD 'senha';
CREATE USER maria WITH PASSWORD 'senha';
CREATE USER pedro WITH PASSWORD 'senha';

GRANT viewer_role TO joao;
GRANT editor_role TO maria;
GRANT admin_role TO pedro;

-- 6. Revogar roles
REVOKE editor_role FROM maria;
GRANT viewer_role TO maria;

-- MySQL: implementar RBAC
-- 1. Criar roles
CREATE ROLE 'viewer_role', 'editor_role', 'admin_role';

-- 2. Atribuir privilegios as roles
GRANT SELECT ON mydb.* TO 'viewer_role';
GRANT SELECT, INSERT, UPDATE, DELETE ON mydb.* TO 'editor_role';
GRANT ALL PRIVILEGES ON mydb.* TO 'admin_role';

-- 3. Criar usuarios e atribuir roles
CREATE USER 'joao'@'%' IDENTIFIED BY 'senha';
CREATE USER 'maria'@'%' IDENTIFIED BY 'senha';
CREATE USER 'pedro'@'%' IDENTIFIED BY 'senha';

GRANT 'viewer_role' TO 'joao'@'%';
GRANT 'editor_role' TO 'maria'@'%';
GRANT 'admin_role' TO 'pedro'@'%';

-- 4. Verificar privilegios
SHOW GRANTS FOR 'joao'@'%';
SHOW GRANTS FOR 'maria'@'%';
SHOW GRANTS FOR 'pedro'@'%';
```

### Password Rotation

```sql
-- Implementar rotacao de senhas

-- PostgreSQL: rotacao de senhas
-- 1. Criar funcao para rotacionar senhas
CREATE OR REPLACE FUNCTION rotate_password(
    p_username TEXT,
    p_new_password TEXT
) RETURNS VOID AS $$
BEGIN
    -- Verificar se usuario existe
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = p_username) THEN
        RAISE EXCEPTION 'Usuario % nao existe', p_username;
    END IF;
    
    -- Atualizar senha
    EXECUTE format('ALTER USER %I WITH PASSWORD %L', p_username, p_new_password);
    
    -- Log da rotacao
    INSERT INTO password_rotation_log (username, rotated_at)
    VALUES (p_username, CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- 2. Criar tabela de log
CREATE TABLE password_rotation_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    rotated_at TIMESTAMP NOT NULL,
    rotated_by VARCHAR(100) DEFAULT CURRENT_USER
);

-- 3. Criar job para rotacao periodica
-- Usar pg_cron ou cron externo
-- Exemplo: rotacionar senhas a cada 90 dias
SELECT rotate_password('app_user', 'NovaSenhaForte!2024');

-- MySQL: rotacao de senhas
-- 1. Criar procedure para rotacionar
DELIMITER //
CREATE PROCEDURE rotate_password(
    IN p_username VARCHAR(100),
    IN p_new_password VARCHAR(100)
)
BEGIN
    -- Verificar se usuario existe
    IF NOT EXISTS (SELECT 1 FROM mysql.user WHERE user = p_username) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Usuario nao existe';
    END IF;
    
    -- Atualizar senha
    SET @sql = CONCAT('ALTER USER ''', p_username, '''@''%'' IDENTIFIED BY ''', p_new_password, '''');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
    
    -- Log da rotacao
    INSERT INTO password_rotation_log (username, rotated_at)
    VALUES (p_username, NOW());
END //
DELIMITER ;

-- 2. Criar tabela de log
CREATE TABLE password_rotation_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    rotated_at DATETIME NOT NULL,
    rotated_by VARCHAR(100) DEFAULT CURRENT_USER
);

-- 3. Usar procedure
CALL rotate_password('app_user', 'NovaSenhaForte!2024');

-- Automatizar com Event Scheduler
CREATE EVENT rotate_passwords_event
ON SCHEDULE EVERY 90 DAY
DO
BEGIN
    -- Rotacionar senhas de usuarios especificos
    CALL rotate_password('app_user', CONCAT('Senha', DATE_FORMAT(NOW(), '%Y%m%d'), '!'));
END;
```

## Audit Logging

### Configuracao de Auditoria

```sql
-- Implementar auditoria completa

-- PostgreSQL: usar pgAudit
-- 1. Instalar extensao
CREATE EXTENSION pgaudit;

-- 2. Configurar em postgresql.conf
-- shared_preload_libraries = 'pgaudit'
-- pgaudit.log = 'ddl, role, write'
-- pgaudit.log_catalog = on
-- pgaudit.log_level = 'log'
-- pgaudit.log_parameter = on
-- pgaudit.log_statement_once = off

-- 3. Configurar por role
ALTER ROLE app_user SET pgaudit.log = 'read, write';
ALTER ROLE admin_role SET pgaudit.log = 'all';

-- 4. Verificar logs
-- Os logs aparecem no log do PostgreSQL
-- Formato: AUDIT: SESSION,1,1,WRITE,INSERT,,,"INSERT INTO customers (name) VALUES ('Joao');"

-- MySQL: usar audit plugin
-- 1. Instalar plugin
INSTALL PLUGIN audit_log SONAME 'audit_log.so';

-- 2. Configurar em my.cnf
-- [mysqld]
-- audit_log_policy = ALL
-- audit_log_format = JSON
-- audit_log_file = /var/log/mysql/audit.log
-- audit_log_rotations = 10
-- audit_log_rotate_on_size = 10M

-- 3. Verificar logs
SHOW VARIABLES LIKE 'audit_log%';

-- 4. Logs aparecem em formato JSON
-- {"timestamp":"2024-01-15T10:30:00Z","user":"app_user","query":"INSERT INTO customers (name) VALUES ('Joao')"}

-- Tabela de auditoria personalizada
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100) DEFAULT CURRENT_USER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para auditoria
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, new_data)
        VALUES (TG_TABLE_NAME, 'INSERT', row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, old_data, new_data)
        VALUES (TG_TABLE_NAME, 'UPDATE', row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, old_data)
        VALUES (TG_TABLE_NAME, 'DELETE', row_to_json(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em tabelas criticas
CREATE TRIGGER audit_customers
AFTER INSERT OR UPDATE OR DELETE ON customers
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_orders
AFTER INSERT OR UPDATE OR DELETE ON orders
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

### Monitoramento e Alertas

```sql
-- Configurar monitoramento e alertas

-- PostgreSQL: monitorar atividade
-- 1. Conexoes ativas
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    client_port,
    backend_start,
    state,
    query,
    query_start
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;

-- 2. Queries lentas
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active';

-- 3. Tabelas com mais acesso
SELECT
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables
ORDER BY seq_scan + idx_scan DESC
LIMIT 10;

-- 4. Indices nao utilizados
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND pg_relation_size(indexrelid) > 1024 * 1024  -- > 1MB
ORDER BY pg_relation_size(indexrelid) DESC;

-- MySQL: monitorar atividade
-- 1. Conexoes ativas
SHOW PROCESSLIST;

-- 2. Queries lentas
SELECT
    id,
    user,
    host,
    db,
    command,
    time,
    state,
    info
FROM information_schema.processlist
WHERE command != 'Sleep'
AND time > 300;

-- 3. InnoDB status
SHOW ENGINE INNODB STATUS;

-- 4. Variaveis de performance
SHOW GLOBAL STATUS LIKE 'Slow_queries';
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Threads_running';
SHOW GLOBAL STATUS LIKE 'Queries';
SHOW GLOBAL VARIABLES LIKE 'max_connections';
```

## Vulnerability Scanning

### Nessus e Qualys

```bash
# Configurar scan de vulnerabilidades

# 1. Nessus para bancos de dados
# Instalar Nessus
wget https://www.tenable.com/downloads/api/nessus/nessus-10.6.3-x86_64.rpm
sudo rpm -ivh nessus-10.6.3-x86_64.rpm
sudo systemctl start nessusd

# Acessar https://localhost:8834
# Configurar scan de banco de dados
# - Criar novo scan
# - Selecionar "Database" template
# - Configurar IP/porta do banco
# - Executar scan

# 2. Qualys para bancos de dados
# Usar Qualys Cloud Platform
# - Configurar scan de banco de dados
# - Selecionar "Database Assessment"
# - Configurar credenciais
# - Executar scan

# 3. Scripts de verificacao manual
# Verificar versao do PostgreSQL
psql -h localhost -U postgres -c "SELECT version();"

# Verificar versao do MySQL
mysql -h localhost -u root -p -e "SELECT version();"

# Verificar configuracoes de seguranca
# PostgreSQL
psql -h localhost -U postgres -c "SHOW ssl;"
psql -h localhost -U postgres -c "SHOW password_encryption;"
psql -h localhost -U postgres -c "SHOW log_connections;"

# MySQL
mysql -h localhost -u root -p -e "SHOW VARIABLES LIKE '%ssl%';"
mysql -h localhost -u root -p -e "SHOW VARIABLES LIKE '%validate_password%';"
mysql -h localhost -u root -p -e "SHOW VARIABLES LIKE '%local_infile%';"

# Verificar usuarios com privilegios excessivos
# PostgreSQL
psql -h localhost -U postgres -c "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolsuper = true;"

# MySQL
mysql -h localhost -u root -p -e "SELECT user, Super_priv, Create_priv, Drop_priv FROM mysql.user WHERE Super_priv = 'Y';"
```

### CIS Benchmarks

```bash
# Implementar CIS Benchmarks para bancos de dados

# 1. PostgreSQL CIS Benchmark
# Baixar benchmark: https://www.cisecurity.org/benchmark/postgresql

# Itens principais:
# 1.1. Instalacao e configuracao
# - Verificar versao
# - Configurar diretorios
# - Configurar permissoes

# 1.2. Configuracao
# - Configurar postgresql.conf
# - Configurar pg_hba.conf
# - Configurar SSL

# 1.3. Autenticacao
# - Politicas de senha
# - MFA
# - Timeout de sessao

# 1.4. Autorizacao
# - Least privilege
# - RBAC
# - Revocar privilegios

# 1.5. Auditoria
# - Logging
# - Monitoramento
# - Alertas

# Script de verificacao:
#!/bin/bash
echo "=== PostgreSQL CIS Benchmark Check ==="

# 1.1.1 Verificar versao
echo "1.1.1 Verificar versao:"
psql -U postgres -c "SELECT version();"

# 1.2.1 Verificar permissoes do diretorio
echo "1.2.1 Verificar permissoes:"
ls -la /var/lib/postgresql/

# 1.2.2 Verificar configuracao
echo "1.2.2 Verificar configuracao:"
psql -U postgres -c "SHOW ssl;"
psql -U postgres -c "SHOW password_encryption;"
psql -U postgres -c "SHOW log_connections;"
psql -U postgres -c "SHOW log_disconnections;"

# 1.3.1 Verificar autenticacao
echo "1.3.1 Verificar autenticacao:"
cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#" | grep -v "^$"

# 1.4.1 Verificar privilegios
echo "1.4.1 Verificar privilegios:"
psql -U postgres -c "SELECT rolname, rolsuper, rolcreaterole, rolcreatedb FROM pg_roles;"

# 1.5.1 Verificar auditoria
echo "1.5.1 Verificar auditoria:"
psql -U postgres -c "SHOW shared_preload_libraries;"

# 2. MySQL CIS Benchmark
# Baixar benchmark: https://www.cisecurity.org/benchmark/mysql

# Script de verificacao:
#!/bin/bash
echo "=== MySQL CIS Benchmark Check ==="

# 2.1.1 Verificar versao
echo "2.1.1 Verificar versao:"
mysql -u root -p -e "SELECT version();"

# 2.2.1 Verificar configuracao
echo "2.2.1 Verificar configuracao:"
mysql -u root -p -e "SHOW VARIABLES LIKE '%ssl%';"
mysql -u root -p -e "SHOW VARIABLES LIKE '%validate_password%';"
mysql -u root -p -e "SHOW VARIABLES LIKE '%local_infile%';"

# 2.3.1 Verificar autenticacao
echo "2.3.1 Verificar autenticacao:"
mysql -u root -p -e "SELECT user, host, authentication_string FROM mysql.user;"

# 2.4.1 Verificar privilegios
echo "2.4.1 Verificar privilegios:"
mysql -u root -p -e "SELECT user, Super_priv, Create_priv, Drop_priv FROM mysql.user;"

# 2.5.1 Verificar auditoria
echo "2.5.1 Verificar auditoria:"
mysql -u root -p -e "SHOW VARIABLES LIKE '%audit_log%';"
```

## Exemplo: PostgreSQL Hardening Completo

```bash
#!/bin/bash
# Script de hardening completo para PostgreSQL

echo "=== PostgreSQL Hardening Completo ==="

# 1. Instalacao segura
echo "1. Instalacao segura..."
sudo apt-get update
sudo apt-get install -y postgresql-15 postgresql-client-15

# 2. Configurar usuario dedicado
echo "2. Configurar usuario dedicado..."
sudo usermod -d /var/lib/postgresql postgres

# 3. Configurar permissoes
echo "3. Configurar permissoes..."
sudo chmod 700 /var/lib/postgresql
sudo chown -R postgres:postgres /var/lib/postgresql

# 4. Configurar pg_hba.conf
echo "4. Configurar pg_hba.conf..."
sudo tee /etc/postgresql/15/main/pg_hba.conf > /dev/null <<EOF
# PostgreSQL Client Authentication Configuration File
# TYPE  DATABASE  USER  ADDRESS  METHOD

# Local connections
local   all             postgres                                peer
local   all             all                                     peer

# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256

# IPv4 internal network connections:
host    all             all             10.0.0.0/8              scram-sha-256
host    all             all             172.16.0.0/12           scram-sha-256
host    all             all             192.168.0.0/16          scram-sha-256

# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256

# Replication connections
host    replication     replica_user    10.0.0.0/8              scram-sha-256

# Deny all other connections
host    all             all             0.0.0.0/0               reject
host    all             all             ::/0                    reject
EOF

# 5. Configurar postgresql.conf
echo "5. Configurar postgresql.conf..."
sudo tee /etc/postgresql/15/main/postgresql.conf > /dev/null <<EOF
# PostgreSQL Configuration

# Connection Settings
listen_addresses = 'localhost,10.0.1.50'
port = 5432
max_connections = 100
superuser_reserved_connections = 3

# Security Settings
password_encryption = scram-sha-256
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
ssl_ca_file = '/etc/ssl/certs/ca.crt'

# Logging Settings
log_connections = on
log_disconnections = on
log_line_prefix = '%m [%p] %q%u@%d '
log_statement = 'ddl'
log_min_duration_statement = 1000

# Performance Settings
shared_buffers = '4GB'
effective_cache_size = '12GB'
work_mem = '64MB'
maintenance_work_mem = '1GB'

# Extensions
shared_preload_libraries = 'pg_stat_statements,pgaudit'

# Monitoring
track_activities = on
track_counts = on
track_functions = all
track_io_timing = on
EOF

# 6. Gerar certificados SSL
echo "6. Gerar certificados SSL..."
sudo mkdir -p /etc/ssl/certs /etc/ssl/private

# Gerar CA
sudo openssl req -new -x509 -days 365 -nodes -text \
    -out /etc/ssl/certs/ca.crt -keyout /etc/ssl/private/ca.key \
    -subj "/CN=PostgreSQL-CA"

# Gerar certificado do servidor
sudo openssl req -new -nodes -text \
    -out /tmp/server.csr -keyout /etc/ssl/private/server.key \
    -subj "/CN=db-server"
sudo openssl x509 -req -in /tmp/server.csr -days 365 \
    -CA /etc/ssl/certs/ca.crt -CAkey /etc/ssl/private/ca.key -CAcreateserial \
    -out /etc/ssl/certs/server.crt

# Configurar permissoes
sudo chmod 600 /etc/ssl/private/ca.key /etc/ssl/private/server.key
sudo chmod 644 /etc/ssl/certs/ca.crt /etc/ssl/certs/server.crt
sudo chown postgres:postgres /etc/ssl/private/*

# 7. Configurar firewall
echo "7. Configurar firewall..."
sudo ufw allow from 10.0.0.0/8 to any port 5432 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 5432 proto tcp
sudo ufw deny 5432

# 8. Criar roles de seguranca
echo "8. Criar roles de seguranca..."
sudo -u postgres psql -c "
-- Role de leitura
CREATE ROLE readonly_role;
GRANT CONNECT ON DATABASE mydb TO readonly_role;
GRANT USAGE ON SCHEMA public TO readonly_role;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_role;

-- Role de escrita
CREATE ROLE writeonly_role;
GRANT CONNECT ON DATABASE mydb TO writeonly_role;
GRANT USAGE ON SCHEMA public TO writeonly_role;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO writeonly_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT INSERT, UPDATE, DELETE ON TABLES TO writeonly_role;

-- Role de administracao limitada
CREATE ROLE admin_role;
GRANT CONNECT ON DATABASE mydb TO admin_role;
GRANT USAGE ON SCHEMA public TO admin_role;
GRANT CREATE ON SCHEMA public TO admin_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO admin_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO admin_role;
"

# 9. Configurar auditoria
echo "9. Configurar auditoria..."
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS pgaudit;"
sudo -u postgres psql -c "ALTER SYSTEM SET pgaudit.log = 'ddl, role, write';"
sudo -u postgres psql -c "ALTER SYSTEM SET pgaudit.log_catalog = on;"

# 10. Configurar monitoramento
echo "10. Configurar monitoramento..."
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
sudo -u postgres psql -c "ALTER SYSTEM SET pg_stat_statements.track = all;"

# 11. Reiniciar PostgreSQL
echo "11. Reiniciar PostgreSQL..."
sudo systemctl restart postgresql

# 12. Verificar configuracao
echo "12. Verificar configuracao..."
sudo -u postgres psql -c "SHOW ssl;"
sudo -u postgres psql -c "SHOW password_encryption;"
sudo -u postgres psql -c "SHOW log_connections;"
sudo -u postgres psql -c "SHOW shared_preload_libraries;"

echo "=== Hardening completo! ==="
```

## Exemplo: MySQL Hardening Completo

```bash
#!/bin/bash
# Script de hardening completo para MySQL

echo "=== MySQL Hardening Completo ==="

# 1. Instalacao segura
echo "1. Instalacao segura..."
sudo apt-get update
sudo apt-get install -y mysql-server mysql-client

# 2. Executar secure installation
echo "2. Executar secure installation..."
sudo mysql_secure_installation <<EOF
y
y
y
y
y
EOF

# 3. Configurar my.cnf
echo "3. Configurar my.cnf..."
sudo tee /etc/mysql/mysql.conf.d/mysqld.cnf > /dev/null <<EOF
[mysqld]
# Connection Settings
bind-address = 127.0.0.1
port = 3306
max_connections = 100
wait_timeout = 600
interactive_timeout = 600

# Security Settings
default_authentication_plugin = mysql_native_password
validate_password.policy = MEDIUM
validate_password.length = 12
validate_password.mixed_case_count = 1
validate_password.number_count = 1
validate_password.special_char_count = 1
local_infile = 0
symbolic-links = 0

# SSL Settings
require_secure_transport = ON
ssl-ca = /etc/mysql/ssl/ca.pem
ssl-cert = /etc/mysql/ssl/server-cert.pem
ssl-key = /etc/mysql/ssl/server-key.pem

# Logging Settings
general_log = 0
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
log_error = /var/log/mysql/error.log
log_bin = /var/log/mysql/mysql-bin.log
binlog_format = ROW
expire_logs_days = 14

# Performance Settings
innodb_buffer_pool_size = 4G
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT
EOF

# 4. Gerar certificados SSL
echo "4. Gerar certificados SSL..."
sudo mkdir -p /etc/mysql/ssl

# Gerar CA
sudo openssl req -new -x509 -days 365 -nodes -text \
    -out /etc/mysql/ssl/ca.pem -keyout /etc/mysql/ssl/ca-key.pem \
    -subj "/CN=MySQL-CA"

# Gerar certificado do servidor
sudo openssl req -new -nodes -text \
    -out /tmp/server.csr -keyout /etc/mysql/ssl/server-key.pem \
    -subj "/CN=db-server"
sudo openssl x509 -req -in /tmp/server.csr -days 365 \
    -CA /etc/mysql/ssl/ca.pem -CAkey /etc/mysql/ssl/ca-key.pem -CAcreateserial \
    -out /etc/mysql/ssl/server-cert.pem

# Configurar permissoes
sudo chmod 600 /etc/mysql/ssl/ca-key.pem /etc/mysql/ssl/server-key.pem
sudo chmod 644 /etc/mysql/ssl/ca.pem /etc/mysql/ssl/server-cert.pem
sudo chown mysql:mysql /etc/mysql/ssl/*

# 5. Configurar firewall
echo "5. Configurar firewall..."
sudo ufw allow from 127.0.0.1 to any port 3306 proto tcp
sudo ufw allow from 10.0.0.0/8 to any port 3306 proto tcp
sudo ufw allow from 172.16.0.0/12 to any port 3306 proto tcp
sudo ufw allow from 192.168.0.0/16 to any port 3306 proto tcp
sudo ufw deny 3306

# 6. Criar usuarios de seguranca
echo "6. Criar usuarios de seguranca..."
sudo mysql -u root -p <<EOF
-- Usuario somente leitura
CREATE USER 'readonly_user'@'10.0.1.50' IDENTIFIED BY 'SenhaForte!2024';
GRANT SELECT ON mydb.* TO 'readonly_user'@'10.0.1.50';

-- Usuario de escrita
CREATE USER 'writeonly_user'@'10.0.1.50' IDENTIFIED BY 'SenhaForte!2024';
GRANT INSERT, UPDATE, DELETE ON mydb.* TO 'writeonly_user'@'10.0.1.50';

-- Usuario administrador limitado
CREATE USER 'admin_user'@'10.0.1.50' IDENTIFIED BY 'SenhaForte!2024';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER ON mydb.* TO 'admin_user'@'10.0.1.50';

-- Usuario que exige SSL
CREATE USER 'secure_user'@'%' IDENTIFIED BY 'SenhaForte!2024';
GRANT SELECT, INSERT, UPDATE ON mydb.* TO 'secure_user'@'%';
REQUIRE SSL;

-- Revogar privilegios excessivos
REVOKE ALL PRIVILEGES ON *.* FROM 'app_user'@'%';
GRANT SELECT, INSERT, UPDATE ON mydb.customers TO 'app_user'@'%';
GRANT SELECT ON mydb.products TO 'app_user'@'%';
EOF

# 7. Configurar auditoria
echo "7. Configurar auditoria..."
sudo tee /etc/mysql/conf.d/audit.cnf > /dev/null <<EOF
[mysqld]
plugin-load-add = audit_log.so
audit_log_policy = ALL
audit_log_format = JSON
audit_log_file = /var/log/mysql/audit.log
audit_log_rotations = 10
audit_log_rotate_on_size = 10M
EOF

# 8. Configurar monitoramento
echo "8. Configurar monitoramento..."
sudo tee /etc/mysql/conf.d/monitoring.cnf > /dev/null <<EOF
[mysqld]
performance_schema = ON
show_compatibility_56 = ON
EOF

# 9. Reiniciar MySQL
echo "9. Reiniciar MySQL..."
sudo systemctl restart mysql

# 10. Verificar configuracao
echo "10. Verificar configuracao..."
sudo mysql -u root -p -e "SHOW VARIABLES LIKE '%ssl%';"
sudo mysql -u root -p -e "SHOW VARIABLES LIKE '%validate_password%';"
sudo mysql -u root -p -e "SHOW VARIABLES LIKE '%local_infile%';"
sudo mysql -u root -p -e "SHOW VARIABLES LIKE '%audit_log%';"

echo "=== Hardening completo! ==="
```

## Network Security

### VPN para Acesso ao Banco

```bash
# Configurar VPN para acesso seguro ao banco de dados

# 1. OpenVPN para acesso remoto
# Instalar OpenVPN
sudo apt-get install -y openvpn easy-rsa

# Configurar PKI
cd /etc/openvpn
sudo cp -r /usr/share/easy-rsa/ .
cd easy-rsa
sudo ./easyrsa init-pki
sudo ./easyrsa build-ca
sudo ./easyrsa gen-req server nopass
sudo ./easyrsa sign-req server server
sudo ./easyrsa gen-req client1 nopass
sudo ./easyrsa sign-req client client1

# Configurar servidor
sudo tee /etc/openvpn/server.conf > /dev/null <<EOF
port 1194
proto udp
dev tun
ca ca.crt
cert server.crt
key server.key
dh dh2048.pem
topology subnet
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
keepalive 10 120
cipher AES-256-GCM
user nobody
group nogroup
persist-key
persist-tun
status /var/log/openvpn-status.log
verb 3
EOF

# Iniciar servidor
sudo systemctl start openvpn@server
sudo systemctl enable openvpn@server

# 2. WireGuard (mais moderno e rapido)
# Instalar WireGuard
sudo apt-get install -y wireguard

# Gerar chaves
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key

# Configurar servidor
sudo tee /etc/wireguard/wg0.conf > /dev/null <<EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = $(cat /etc/wireguard/client_public.key)
AllowedIPs = 10.0.0.2/32
EOF

# Iniciar WireGuard
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0

# 3. Configurar firewall para VPN
sudo ufw allow 1194/udp  # OpenVPN
sudo ufw allow 51820/udp # WireGuard
sudo ufw allow from 10.8.0.0/24 to any port 5432  # PostgreSQL via VPN
sudo ufw allow from 10.8.0.0/24 to any port 3306  # MySQL via VPN
```

### Network Segmentation

```bash
# Implementar segmentacao de rede

# 1. VLANs para isolar bancos de dados
# Configurar switch para VLANs
# VLAN 10: Rede de producao
# VLAN 20: Rede de desenvolvimento
# VLAN 30: Rede de banco de dados

# 2. Configurar router/firewall
# Regras para isolar VLANs
sudo iptables -A FORWARD -i eth1 -o eth2 -s 10.10.0.0/24 -d 10.20.0.0/24 -j ACCEPT
sudo iptables -A FORWARD -i eth2 -o eth1 -s 10.20.0.0/24 -d 10.10.0.0/24 -j ACCEPT
sudo iptables -A FORWARD -i eth1 -o eth3 -s 10.10.0.0/24 -d 10.30.0.0/24 -j ACCEPT
sudo iptables -A FORWARD -i eth3 -o eth1 -s 10.30.0.0/24 -d 10.10.0.0/24 -j ACCEPT
sudo iptables -A FORWARD -s 10.20.0.0/24 -d 10.30.0.0/24 -j DROP
sudo iptables -A FORWARD -s 10.30.0.0/24 -d 10.20.0.0/24 -j DROP

# 3. Configurar sub-redes para bancos de dados
# Sub-rede dedicada para PostgreSQL
# Sub-rede dedicada para MySQL
# Sub-rede dedicada para backups

# 4. Configurar NAT e routing
sudo iptables -t nat -A POSTROUTING -s 10.30.0.0/24 -o eth0 -j MASQUERADE
sudo ip route add 10.10.0.0/24 via 10.30.0.1
sudo ip route add 10.20.0.0/24 via 10.30.0.1

# 5. Monitorar trafego entre segmentos
sudo tcpdump -i eth3 -n port 5432 or port 3306
```

## Data Masking

### Tipos de Mascaramento

```sql
-- Implementar mascaramento de dados

-- PostgreSQL: mascaramento de dados
-- 1. Mascaramento completo
CREATE OR REPLACE FUNCTION mask_email(email TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LEFT(email, 2) || '***' || SUBSTRING(email FROM POSITION('@' IN email));
END;
$$ LANGUAGE plpgsql;

-- 2. Mascaramento parcial
CREATE OR REPLACE FUNCTION mask_credit_card(card TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN '****-****-****-' || RIGHT(card, 4);
END;
$$ LANGUAGE plpgsql;

-- 3. Mascaramento de CPF
CREATE OR REPLACE FUNCTION mask_cpf(cpf TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN '***.***.***-' || RIGHT(cpf, 2);
END;
$$ LANGUAGE plpgsql;

-- 4. Usar mascaramento em views
CREATE VIEW customers_masked AS
SELECT
    id,
    mask_email(email) as email,
    mask_credit_card(credit_card) as credit_card,
    mask_cpf(cpf) as cpf,
    created_at
FROM customers;

-- 5. Mascaramento dinamico baseado em papel
CREATE OR REPLACE FUNCTION mask_data_dynamic(
    data TEXT,
    user_role TEXT,
    data_type TEXT
) RETURNS TEXT AS $$
BEGIN
    CASE user_role
        WHEN 'admin' THEN RETURN data;
        WHEN 'manager' THEN
            CASE data_type
                WHEN 'email' THEN RETURN LEFT(data, 2) || '***' || SUBSTRING(data FROM POSITION('@' IN data));
                WHEN 'credit_card' THEN RETURN '****-****-****-' || RIGHT(data, 4);
                ELSE RETURN data;
            END CASE;
        WHEN 'viewer' THEN RETURN '***MASKED***';
        ELSE RETURN '***MASKED***';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- MySQL: mascaramento de dados
-- 1. Mascaramento de email
DELIMITER //
CREATE FUNCTION mask_email(email VARCHAR(100))
RETURNS VARCHAR(100)
DETERMINISTIC
BEGIN
    RETURN CONCAT(LEFT(email, 2), '***', SUBSTRING(email, LOCATE('@', email)));
END //
DELIMITER ;

-- 2. Mascaramento de cartao de credito
DELIMITER //
CREATE FUNCTION mask_credit_card(card VARCHAR(20))
RETURNS VARCHAR(20)
DETERMINISTIC
BEGIN
    RETURN CONCAT('****-****-****-', RIGHT(card, 4));
END //
DELIMITER ;

-- 3. Usar mascaramento em views
CREATE VIEW customers_masked AS
SELECT
    id,
    mask_email(email) as email,
    mask_credit_card(credit_card) as credit_card,
    created_at
FROM customers;
```

### Dynamic Data Masking

```sql
-- Implementar mascaramento dinamico

-- PostgreSQL: mascaramento baseado em sessao
CREATE OR REPLACE FUNCTION set_masking_level(level TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.masking_level', level, false);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_masking_level()
RETURNS TEXT AS $$
BEGIN
    RETURN current_setting('app.masking_level', true);
END;
$$ LANGUAGE plpgsql;

-- Funcao de mascaramento que verifica nivel
CREATE OR REPLACE FUNCTION mask_value(
    value TEXT,
    mask_type TEXT
) RETURNS TEXT AS $$
DECLARE
    masking_level TEXT;
BEGIN
    masking_level := get_masking_level();
    
    IF masking_level = 'full' THEN
        RETURN value;
    ELSIF masking_level = 'partial' THEN
        CASE mask_type
            WHEN 'email' THEN RETURN LEFT(value, 2) || '***' || SUBSTRING(value FROM POSITION('@' IN value));
            WHEN 'credit_card' THEN RETURN '****-****-****-' || RIGHT(value, 4);
            WHEN 'cpf' THEN RETURN '***.***.***-' || RIGHT(value, 2);
            ELSE RETURN value;
        END CASE;
    ELSE -- 'hidden'
        RETURN '***MASKED***';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- View que usa mascaramento dinamico
CREATE VIEW customers_dynamic_masked AS
SELECT
    id,
    mask_value(email, 'email') as email,
    mask_value(credit_card, 'credit_card') as credit_card,
    mask_value(cpf, 'cpf') as cpf,
    created_at
FROM customers;

-- Usar mascaramento
SET app.masking_level = 'full';
SELECT * FROM customers_dynamic_masked;  -- Mostra tudo

SET app.masking_level = 'partial';
SELECT * FROM customers_dynamic_masked;  -- Mascara parcialmente

SET app.masking_level = 'hidden';
SELECT * FROM customers_dynamic_masked;  -- Esconde tudo
```

## Database Activity Monitoring (DAM)

### Configuracao de Monitoramento

```sql
-- Implementar monitoramento de atividade do banco

-- PostgreSQL: usar pg_stat_statements
CREATE EXTENSION pg_stat_statements;

-- Configurar em postgresql.conf:
-- shared_preload_libraries = 'pg_stat_statements'
-- pg_stat_statements.max = 10000
-- pg_stat_statements.track = all
-- pg_stat_statements.track_utility = on
-- pg_stat_statements.track_planning = on

-- Queries para monitoramento
-- 1. Queries mais lentas
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 2. Queries mais frequentes
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 10;

-- 3. Queries com mais tempo total
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- 4. Queries que retornam mais linhas
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements
ORDER BY rows DESC
LIMIT 10;

-- MySQL: usar performance_schema
-- 1. Queries mais lentas
SELECT
    digest_text,
    count_star,
    sum_timer_wait,
    avg_timer_wait,
    sum_rows_examined
FROM performance_schema.events_statements_summary_by_digest
ORDER BY avg_timer_wait DESC
LIMIT 10;

-- 2. Queries mais frequentes
SELECT
    digest_text,
    count_star,
    sum_timer_wait,
    avg_timer_wait
FROM performance_schema.events_statements_summary_by_digest
ORDER BY count_star DESC
LIMIT 10;

-- 3. Tabelas com mais acesso
SELECT
    object_schema,
    object_name,
    count_star,
    count_read,
    count_write,
    count_fetch
FROM performance_schema.table_io_waits_summary_by_table
ORDER BY count_star DESC
LIMIT 10;

-- 4. Indices nao utilizados
SELECT
    object_schema,
    object_name,
    index_name,
    count_star,
    count_read
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE count_star = 0
AND index_name IS NOT NULL
ORDER BY object_name;
```

### Alertas e Notificacoes

```sql
-- Configurar alertas de seguranca

-- PostgreSQL: criar sistema de alertas
CREATE TABLE security_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100)
);

-- Funcao para gerar alertas
CREATE OR REPLACE FUNCTION create_alert(
    p_alert_type VARCHAR,
    p_severity VARCHAR,
    p_message TEXT,
    p_details JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO security_alerts (alert_type, severity, message, details)
    VALUES (p_alert_type, p_severity, p_message, p_details);
    
    -- Enviar notificacao (usar pg_notify ou extensao)
    PERFORM pg_notify('security_alert', json_build_object(
        'type', p_alert_type,
        'severity', p_severity,
        'message', p_message
    )::text);
END;
$$ LANGUAGE plpgsql;

-- Trigger para alertas de login falho
CREATE OR REPLACE FUNCTION check_failed_logins()
RETURNS TRIGGER AS $$
BEGIN
    -- Verificar se ha muitos logins falhos recentes
    IF (
        SELECT COUNT(*)
        FROM pg_stat_activity
        WHERE state = 'authentication'
        AND query_start < NOW() - INTERVAL '5 minutes'
    ) > 10 THEN
        PERFORM create_alert(
            'brute_force',
            'critical',
            'Possivel ataque de forca bruta detectado',
            json_build_object('failed_attempts', 10)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- MySQL: criar sistema de alertas
CREATE TABLE security_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    details JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    resolved_by VARCHAR(100)
);

-- Evento para verificar logins falhos
DELIMITER //
CREATE EVENT check_failed_logins_event
ON SCHEDULE EVERY 5 MINUTE
DO
BEGIN
    DECLARE failed_count INT;
    
    SELECT COUNT(*) INTO failed_count
    FROM performance_schema.events_statements_summary_by_digest
    WHERE digest_text LIKE '%LOGIN%'
    AND sum_errors > 10;
    
    IF failed_count > 10 THEN
        INSERT INTO security_alerts (alert_type, severity, message, details)
        VALUES ('brute_force', 'critical', 'Possivel ataque de forca bruta detectado',
                JSON_OBJECT('failed_attempts', failed_count));
    END IF;
END //
DELIMITER ;
```

## Incident Response

### Plano de Resposta a Incidentes

```sql
-- Criar plano de resposta a incidentes de banco de dados

-- 1. Tabela de incidentes
CREATE TABLE security_incidents (
    id SERIAL PRIMARY KEY,
    incident_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    description TEXT NOT NULL,
    affected_systems TEXT[],
    reported_by VARCHAR(100),
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    post_mortem TEXT
);

-- 2. Tabela de acoes de resposta
CREATE TABLE incident_actions (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER REFERENCES security_incidents(id),
    action_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    performed_by VARCHAR(100) NOT NULL,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'completed'
);

-- 3. Funcao para registrar incidente
CREATE OR REPLACE FUNCTION report_incident(
    p_incident_type VARCHAR,
    p_severity VARCHAR,
    p_description TEXT,
    p_affected_systems TEXT[],
    p_reported_by VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    incident_id INTEGER;
BEGIN
    INSERT INTO security_incidents (
        incident_type, severity, description, affected_systems, reported_by
    ) VALUES (
        p_incident_type, p_severity, p_description, p_affected_systems, p_reported_by
    ) RETURNING id INTO incident_id;
    
    -- Criar alerta
    PERFORM create_alert(
        p_incident_type,
        p_severity,
        p_description,
        json_build_object('incident_id', incident_id)
    );
    
    RETURN incident_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Funcao para registrar acao de resposta
CREATE OR REPLACE FUNCTION log_incident_action(
    p_incident_id INTEGER,
    p_action_type VARCHAR,
    p_description TEXT,
    p_performed_by VARCHAR
) RETURNS VOID AS $$
BEGIN
    INSERT INTO incident_actions (
        incident_id, action_type, description, performed_by
    ) VALUES (
        p_incident_id, p_action_type, p_description, p_performed_by
    );
END;
$$ LANGUAGE plpgsql;

-- 5. Exemplo de uso
-- Reportar incidente
INSERT INTO security_incidents (incident_type, severity, description, affected_systems, reported_by)
VALUES ('sql_injection', 'critical', 'Tentativa de SQL injection detectada no endpoint /api/users', ARRAY['api', 'database'], 'monitoring');

-- Registrar acoes de resposta
INSERT INTO incident_actions (incident_id, action_type, description, performed_by)
VALUES (1, 'containment', 'Bloqueio de IP atacante no firewall', 'admin');

INSERT INTO incident_actions (incident_id, action_type, description, performed_by)
VALUES (1, 'investigation', 'Analise de logs de acesso', 'security_team');

INSERT INTO incident_actions (incident_id, action_type, description, performed_by)
VALUES (1, 'eradication', 'Correcao de vulnerabilidade no codigo', 'dev_team');

INSERT INTO incident_actions (incident_id, action_type, description, performed_by)
VALUES (1, 'recovery', 'Restauracao de dados afetados', 'dba');

-- Atualizar status
UPDATE security_incidents
SET status = 'resolved',
    resolved_at = CURRENT_TIMESTAMP,
    resolution_notes = 'Vulnerabilidade corrigida, dados restaurados'
WHERE id = 1;
```

### Playbooks de Resposta

```sql
-- Criar playbooks de resposta a incidentes

-- 1. Playbook para SQL Injection
CREATE TABLE response_playbooks (
    id SERIAL PRIMARY KEY,
    incident_type VARCHAR(50) NOT NULL,
    playbook_name VARCHAR(100) NOT NULL,
    steps JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO response_playbooks (incident_type, playbook_name, steps)
VALUES (
    'sql_injection',
    'Playbook de Resposta a SQL Injection',
    '[
        {"step": 1, "action": "Contencao", "description": "Bloquear IP atacante no firewall", "responsible": "admin", "timeout": "15min"},
        {"step": 2, "action": "Investigacao", "description": "Coletar logs e evidencias", "responsible": "security_team", "timeout": "1hour"},
        {"step": 3, "action": "Avaliacao", "description": "Determinar impacto e dados afetados", "responsible": "security_team", "timeout": "2hours"},
        {"step": 4, "action": "Erradicacao", "description": "Corrigir vulnerabilidade no codigo", "responsible": "dev_team", "timeout": "4hours"},
        {"step": 5, "action": "Recuperacao", "description": "Restaurar dados se necessario", "responsible": "dba", "timeout": "2hours"},
        {"step": 6, "action": "Pos-incidente", "description": "Documentar lições aprendidas", "responsible": "team_lead", "timeout": "24hours"}
    ]'
);

-- 2. Funcao para buscar playbook
CREATE OR REPLACE FUNCTION get_playbook(p_incident_type VARCHAR)
RETURNS JSONB AS $$
DECLARE
    playbook JSONB;
BEGIN
    SELECT steps INTO playbook
    FROM response_playbooks
    WHERE incident_type = p_incident_type
    ORDER BY updated_at DESC
    LIMIT 1;
    
    RETURN playbook;
END;
$$ LANGUAGE plpgsql;

-- 3. Usar playbook
SELECT get_playbook('sql_injection');

-- 4. Tabela de lições aprendidas
CREATE TABLE lessons_learned (
    id SERIAL PRIMARY KEY,
    incident_id INTEGER REFERENCES security_incidents(id),
    lesson TEXT NOT NULL,
    category VARCHAR(50),
    action_required TEXT,
    assigned_to VARCHAR(100),
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Registrar lições aprendidas
INSERT INTO lessons_learned (incident_id, lesson, category, action_required, assigned_to)
VALUES (1, 'Validacao de entrada insuficiente no endpoint /api/users', 'prevention', 'Implementar WAF e validacao de entrada', 'dev_team');
```

## Compliance

### PCI DSS

```sql
-- Implementar conformidade com PCI DSS

-- 1. Requisitos de criptografia
-- Dados de cartao de credito devem ser criptografados

-- Criptografar dados de cartao
CREATE TABLE credit_cards (
    id SERIAL PRIMARY KEY,
    card_number_encrypted BYTEA NOT NULL,
    card_holder VARCHAR(100) NOT NULL,
    expiry_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Funcao para criptografar cartao
CREATE OR REPLACE FUNCTION encrypt_card_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.card_number_encrypted = pgp_sym_encrypt(
        NEW.card_number,
        current_setting('app.encryption_key')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Requisitos de acesso
-- Acesso restrito por necessidade de negocio

-- Criar roles especificas para PCI
CREATE ROLE pci_readonly;
CREATE ROLE pci_analyst;

-- Apenas campos necessarios
GRANT SELECT (id, card_holder, expiry_date) ON credit_cards TO pci_readonly;
GRANT SELECT ON credit_cards_view_masked TO pci_analyst;

-- 3. Requisitos de auditoria
-- Todas as acessos devem ser auditados

-- Configurar auditoria especifica para PCI
CREATE TABLE pci_audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    client_ip INET,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Trigger para auditoria PCI
CREATE OR REPLACE FUNCTION pci_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO pci_audit_log (table_name, operation, user_name, client_ip, details)
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        current_user,
        inet_client_addr(),
        json_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Requisitos de teste
-- Testes de penetracao periodicos

-- Registrar testes
CREATE TABLE pci_penetration_tests (
    id SERIAL PRIMARY KEY,
    test_date DATE NOT NULL,
    tester_name VARCHAR(100) NOT NULL,
    scope TEXT NOT NULL,
    findings JSONB,
    remediation_status VARCHAR(20) DEFAULT 'open',
    next_test_date DATE
);

-- 5. Requisitos de monitoramento
-- Monitoramento continuo de acesso

-- Views para monitoramento PCI
CREATE VIEW pci_access_monitor AS
SELECT
    user_name,
    COUNT(*) as access_count,
    MAX(access_time) as last_access,
    array_agg(DISTINCT operation) as operations
FROM pci_audit_log
WHERE access_time >= NOW() - INTERVAL '24 hours'
GROUP BY user_name;
```

### HIPAA

```sql
-- Implementar conformidade com HIPAA

-- 1. Protected Health Information (PHI)
-- Dados de saude devem ser protegidos

-- Tabela com dados de saude
CREATE TABLE patient_records (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    diagnosis_code VARCHAR(10) NOT NULL,
    treatment_description TEXT NOT NULL,
    treating_physician VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Controle de acesso baseado em funcao
CREATE ROLE phi_provider;
CREATE ROLE phi_researcher;
CREATE ROLE phi_admin;

-- Provedores acessam apenas seus pacientes
GRANT SELECT ON patient_records WHERE treating_physician = current_user TO phi_provider;

-- Pesquisadores acessam dados anonimizados
CREATE VIEW patient_records_anonymized AS
SELECT
    id,
    diagnosis_code,
    treatment_description,
    created_at
FROM patient_records;

GRANT SELECT ON patient_records_anonymized TO phi_researcher;

-- 3. Auditoria de acesso
CREATE TABLE phi_audit_log (
    id BIGSERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    accessor_role VARCHAR(100) NOT NULL,
    access_type VARCHAR(20) NOT NULL,
    access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    ip_address INET
);

-- 4. Criptografia de dados em repouso
-- Usar pgcrypto para criptografar campos sensiveis
CREATE EXTENSION pgcrypto;

-- Funcao para criptografar diagnostico
CREATE OR REPLACE FUNCTION encrypt_diagnosis()
RETURNS TRIGGER AS $$
BEGIN
    NEW.diagnosis_code = pgp_sym_encrypt(
        NEW.diagnosis_code,
        current_setting('app.phi_encryption_key')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Retencao e descarte seguro
-- Politica de retencao de registros
CREATE TABLE retention_policies (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    retention_period INTERVAL NOT NULL,
    disposal_method VARCHAR(50) NOT NULL,
    last_disposal TIMESTAMP
);

INSERT INTO retention_policies (table_name, retention_period, disposal_method)
VALUES ('patient_records', INTERVAL '10 years', 'secure_delete');

-- Funcao para descarte seguro
CREATE OR REPLACE FUNCTION secure_dispose_records()
RETURNS VOID AS $$
DECLARE
    policy RECORD;
BEGIN
    FOR policy IN SELECT * FROM retention_policies WHERE last_disposal < NOW() - INTERVAL '1 year'
    LOOP
        EXECUTE format(
            'DELETE FROM %I WHERE created_at < NOW() - %L',
            policy.table_name,
            policy.retention_period
        );
        
        UPDATE retention_policies
        SET last_disposal = NOW()
        WHERE id = policy.id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

### GDPR

```sql
-- Implementar conformidade com GDPR

-- 1. Direito ao esquecimento
-- Funcao para deletar dados pessoais
CREATE OR REPLACE FUNCTION delete_personal_data(p_user_id INTEGER)
RETURNS VOID AS $$
BEGIN
    -- Deletar de todas as tabelas que contem dados pessoais
    DELETE FROM customer_orders WHERE user_id = p_user_id;
    DELETE FROM customer_preferences WHERE user_id = p_user_id;
    DELETE FROM customer_addresses WHERE user_id = p_user_id;
    DELETE FROM customers WHERE id = p_user_id;
    
    -- Registrar a delecao
    INSERT INTO gdpr_deletions (user_id, deleted_at, deleted_by)
    VALUES (p_user_id, CURRENT_TIMESTAMP, CURRENT_USER);
END;
$$ LANGUAGE plpgsql;

-- Tabela para registrar delecoes
CREATE TABLE gdpr_deletions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    deleted_at TIMESTAMP NOT NULL,
    deleted_by VARCHAR(100) NOT NULL
);

-- 2. Direito de acesso
-- Funcao para exportar dados pessoais
CREATE OR REPLACE FUNCTION export_personal_data(p_user_id INTEGER)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT json_build_object(
        'customer', (SELECT row_to_json(c) FROM customers c WHERE id = p_user_id),
        'orders', (SELECT json_agg(row_to_json(o)) FROM customer_orders o WHERE user_id = p_user_id),
        'preferences', (SELECT row_to_json(p) FROM customer_preferences p WHERE user_id = p_user_id),
        'addresses', (SELECT json_agg(row_to_json(a)) FROM customer_addresses a WHERE user_id = p_user_id)
    ) INTO result;
    
    -- Registrar acesso
    INSERT INTO gdpr_access_logs (user_id, accessed_at, accessed_by, purpose)
    VALUES (p_user_id, CURRENT_TIMESTAMP, CURRENT_USER, 'data_export');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 3. Consentimento
CREATE TABLE gdpr_consents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMP,
    revoked_at TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Funcao para registrar consentimento
CREATE OR REPLACE FUNCTION record_consent(
    p_user_id INTEGER,
    p_consent_type VARCHAR,
    p_granted BOOLEAN,
    p_ip_address INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO gdpr_consents (user_id, consent_type, granted, granted_at, ip_address, user_agent)
    VALUES (p_user_id, p_consent_type, p_granted, 
            CASE WHEN p_granted THEN CURRENT_TIMESTAMP ELSE NULL END,
            p_ip_address, p_user_agent);
    
    -- Se revogado, atualizar registro
    IF NOT p_granted THEN
        UPDATE gdpr_consents
        SET revoked_at = CURRENT_TIMESTAMP
        WHERE user_id = p_user_id 
        AND consent_type = p_consent_type 
        AND granted = true 
        AND revoked_at IS NULL;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 4. Portabilidade de dados
CREATE TABLE gdpr_data_portability (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    data_format VARCHAR(10) DEFAULT 'json'
);

-- 5. Registro de atividades
CREATE TABLE gdpr_processing_activities (
    id SERIAL PRIMARY KEY,
    activity_name VARCHAR(100) NOT NULL,
    purpose TEXT NOT NULL,
    legal_basis VARCHAR(50) NOT NULL,
    data_categories TEXT[] NOT NULL,
    retention_period INTERVAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Registrar atividades de processamento
INSERT INTO gdpr_processing_activities (activity_name, purpose, legal_basis, data_categories, retention_period)
VALUES (
    'customer_management',
    'Gerenciamento de clientes e pedidos',
    'contract_performance',
    ARRAY['name', 'email', 'phone', 'address'],
    INTERVAL '7 years'
);
```

## Database Security Testing

### Testes de Seguranca

```sql
-- Realizar testes de seguranca no banco de dados

-- 1. Teste de SQL Injection
-- Simular tentativas de SQL injection
SELECT * FROM users WHERE username = '' OR '1'='1';
SELECT * FROM users WHERE username = 'admin'--';
SELECT * FROM users WHERE username = 'admin' UNION SELECT * FROM sensitive_data;

-- Verificar se protecoes estao funcionando
-- Deveria retornar erro ou conjunto vazio

-- 2. Teste de acesso nao autorizado
-- Tentar acessar tabelas sem permissao
SET ROLE unauthorized_user;
SELECT * FROM customers;  -- Deveria falhar
RESET ROLE;

-- 3. Teste de brute force
-- Simular tentativas de login
-- Verificar se bloqueio de conta funciona
-- Verificar se alertas sao gerados

-- 4. Teste de injecao de dados
-- Tentar inserir dados maliciosos
INSERT INTO customers (name, email) VALUES ('<script>alert("xss")</script>', 'test@test.com');
INSERT INTO customers (name, email) VALUES ('"; DROP TABLE customers; --', 'test@test.com');

-- Verificar se dados sao sanitizados

-- 5. Teste de vazamento de informacao
-- Verificar se informacoes sensiveis estao expostas
-- Em mensagens de erro
-- Em logs
-- Em metadados

-- 6. Teste de configuracao
-- Verificar configuracoes de seguranca
SHOW ssl;
SHOW password_encryption;
SHOW log_connections;
SHOW log_statement;
```

### Vulnerability Assessment

```sql
-- Avaliar vulnerabilidades do banco de dados

-- 1. Verificar usuarios com privilegios excessivos
-- PostgreSQL
SELECT
    rolname,
    rolsuper,
    rolcreaterole,
    rolcreatedb,
    rolcanlogin,
    rolconnlimit
FROM pg_roles
WHERE rolsuper = true
OR rolcreaterole = true
OR rolcreatedb = true;

-- MySQL
SELECT
    user,
    host,
    Super_priv,
    Create_priv,
    Drop_priv,
    Grant_priv
FROM mysql.user
WHERE Super_priv = 'Y'
OR Create_priv = 'Y'
OR Grant_priv = 'Y';

-- 2. Verificar senhas fracas
-- PostgreSQL (se passwordcheck instalado)
-- Tentar criar usuario com senha fraca
-- Deveria falhar

-- MySQL
SHOW VARIABLES LIKE 'validate_password%';

-- 3. Verificar configuracoes de rede
-- Verificar bind address
SHOW VARIABLES LIKE 'bind_address';

-- Verificar portas
SHOW VARIABLES LIKE 'port';

-- Verificar SSL
SHOW VARIABLES LIKE '%ssl%';

-- 4. Verificar patches e versoes
-- PostgreSQL
SELECT version();

-- MySQL
SELECT version();

-- 5. Verificar permissoes de arquivos
-- Verificar permissoes dos arquivos de configuracao
ls -la /etc/postgresql/*/main/
ls -la /etc/mysql/

-- 6. Verificar logs de auditoria
-- Verificar se logs estao sendo coletados
SHOW VARIABLES LIKE '%log%';
```

## Encryption Key Management

### Gerenciamento de Chaves de Criptografia

```sql
-- Gerenciar chaves de criptografia de forma segura

-- 1. Tabela de chaves de criptografia
CREATE TABLE encryption_keys (
    id SERIAL PRIMARY KEY,
    key_name VARCHAR(100) NOT NULL UNIQUE,
    key_value BYTEA NOT NULL,
    key_type VARCHAR(20) NOT NULL,  -- 'aes', 'rsa', 'pgp'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(100) NOT NULL
);

-- 2. Funcao para criar chave de criptografia
CREATE OR REPLACE FUNCTION create_encryption_key(
    p_key_name VARCHAR,
    p_key_type VARCHAR,
    p_validity_days INTEGER DEFAULT 365
) RETURNS TEXT AS $$
DECLARE
    new_key TEXT;
    key_id INTEGER;
BEGIN
    -- Gerar chave aleatoria
    CASE p_key_type
        WHEN 'aes' THEN
            new_key := encode(gen_random_bytes(32), 'hex');
        WHEN 'rsa' THEN
            -- Para RSA, usar extensao pgcrypto ou ferramenta externa
            new_key := encode(gen_random_bytes(256), 'hex');
        ELSE
            RAISE EXCEPTION 'Tipo de chave nao suportado: %', p_key_type;
    END CASE;
    
    -- Armazenar chave criptografada
    INSERT INTO encryption_keys (key_name, key_value, key_type, expires_at, created_by)
    VALUES (
        p_key_name,
        pgp_sym_encrypt(new_key, current_setting('app.master_key')),
        p_key_type,
        CURRENT_TIMESTAMP + (p_validity_days || ' days')::INTERVAL,
        current_user
    ) RETURNING id INTO key_id;
    
    -- Log de seguranca
    INSERT INTO security_log (event_type, details)
    VALUES ('key_creation', json_build_object('key_name', p_key_name, 'key_type', p_key_type));
    
    RETURN new_key;
END;
$$ LANGUAGE plpgsql;

-- 3. Funcao para obter chave ativa
CREATE OR REPLACE FUNCTION get_encryption_key(p_key_name VARCHAR)
RETURNS TEXT AS $$
DECLARE
    key_value TEXT;
BEGIN
    SELECT pgp_sym_decrypt(ek.key_value, current_setting('app.master_key'))
    INTO key_value
    FROM encryption_keys ek
    WHERE ek.key_name = p_key_name
    AND ek.is_active = true
    AND (ek.expires_at IS NULL OR ek.expires_at > CURRENT_TIMESTAMP);
    
    IF key_value IS NULL THEN
        RAISE EXCEPTION 'Chave nao encontrada ou expirada: %', p_key_name;
    END IF;
    
    RETURN key_value;
END;
$$ LANGUAGE plpgsql;

-- 4. Funcao para rotacionar chave
CREATE OR REPLACE FUNCTION rotate_encryption_key(p_key_name VARCHAR)
RETURNS TEXT AS $$
DECLARE
    new_key TEXT;
BEGIN
    -- Desativar chave antiga
    UPDATE encryption_keys
    SET is_active = false
    WHERE key_name = p_key_name;
    
    -- Criar nova chave
    new_key := create_encryption_key(p_key_name, 'aes', 365);
    
    -- Log de seguranca
    INSERT INTO security_log (event_type, details)
    VALUES ('key_rotation', json_build_object('key_name', p_key_name));
    
    RETURN new_key;
END;
$$ LANGUAGE plpgsql;

-- 5. Tabela de log de seguranca
CREATE TABLE security_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    details JSONB,
    user_name VARCHAR(100) DEFAULT current_user,
    ip_address INET DEFAULT inet_client_addr(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Verificar chaves expiradas
SELECT
    key_name,
    key_type,
    created_at,
    expires_at,
    CASE
        WHEN expires_at < CURRENT_TIMESTAMP THEN 'EXPIRADA'
        WHEN expires_at < CURRENT_TIMESTAMP + INTERVAL '30 days' THEN 'EXPIRA EM BREVE'
        ELSE 'ATIVA'
    END as status
FROM encryption_keys
WHERE is_active = true
ORDER BY expires_at;

-- 7. Politica de rotacao automatica
CREATE OR REPLACE FUNCTION auto_rotate_keys()
RETURNS VOID AS $$
DECLARE
    key_record RECORD;
BEGIN
    FOR key_record IN
        SELECT key_name, expires_at
        FROM encryption_keys
        WHERE is_active = true
        AND expires_at < CURRENT_TIMESTAMP + INTERVAL '30 days'
    LOOP
        PERFORM rotate_encryption_key(key_record.key_name);
        
        INSERT INTO security_log (event_type, details)
        VALUES ('auto_key_rotation', json_build_object(
            'key_name', key_record.key_name,
            'expires_at', key_record.expires_at
        ));
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## Security Monitoring Dashboards

### Criar Dashboards de Monitoramento

```sql
-- Criar views para dashboards de seguranca

-- 1. Dashboard de acessos
CREATE VIEW security_dashboard_access AS
SELECT
    DATE_TRUNC('hour', access_time) as hour,
    user_name,
    COUNT(*) as access_count,
    array_agg(DISTINCT operation) as operations,
    array_agg(DISTINCT client_ip) as ip_addresses
FROM pci_audit_log
WHERE access_time >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', access_time), user_name
ORDER BY hour DESC, access_count DESC;

-- 2. Dashboard de tentativas de login
CREATE VIEW security_dashboard_logins AS
SELECT
    DATE_TRUNC('hour', login_time) as hour,
    user_name,
    COUNT(*) as login_attempts,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
    array_agg(DISTINCT client_ip) as ip_addresses
FROM login_attempts
WHERE login_time >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', login_time), user_name
ORDER BY hour DESC;

-- 3. Dashboard de queries suspeitas
CREATE VIEW security_dashboard_suspicious AS
SELECT
    DATE_TRUNC('hour', query_time) as hour,
    user_name,
    COUNT(*) as suspicious_queries,
    array_agg(DISTINCT query_type) as query_types,
    array_agg(DISTINCT client_ip) as ip_addresses
FROM security_queries
WHERE query_time >= NOW() - INTERVAL '24 hours'
AND risk_level IN ('high', 'critical')
GROUP BY DATE_TRUNC('hour', query_time), user_name
ORDER BY hour DESC, suspicious_queries DESC;

-- 4. Dashboard de violacoes de seguranca
CREATE VIEW security_dashboard_violations AS
SELECT
    DATE_TRUNC('day', created_at) as day,
    violation_type,
    COUNT(*) as violation_count,
    array_agg(DISTINCT user_name) as users_involved,
    array_agg(DISTINCT client_ip) as ip_addresses,
    MAX(severity) as max_severity
FROM security_violations
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('day', created_at), violation_type
ORDER BY day DESC, violation_count DESC;

-- 5. Dashboard de configuracao de seguranca
CREATE VIEW security_dashboard_config AS
SELECT
    'ssl_enabled' as config_name,
    CASE WHEN current_setting('ssl') = 'on' THEN 'enabled' ELSE 'disabled' END as status,
    'CRITICAL' as severity
UNION ALL
SELECT
    'password_encryption',
    current_setting('password_encryption'),
    'HIGH'
UNION ALL
SELECT
    'log_connections',
    current_setting('log_connections'),
    'MEDIUM'
UNION ALL
SELECT
    'max_connections',
    current_setting('max_connections'),
    'LOW';

-- 6. Dashboard de indices nao utilizados
CREATE VIEW security_dashboard_unused_indexes AS
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan as times_used,
    CASE
        WHEN idx_scan = 0 AND pg_relation_size(indexrelid) > 1024 * 1024 THEN 'REMOVER'
        WHEN idx_scan < 10 AND pg_relation_size(indexrelid) > 10 * 1024 * 1024 THEN 'CONSIDERAR REMOVER'
        ELSE 'MANTER'
    END as recommendation
FROM pg_stat_user_indexes
WHERE pg_relation_size(indexrelid) > 1024 * 1024
ORDER BY pg_relation_size(indexrelid) DESC;
```

## Automated Security Scanning

### Scripts de Escaneamento Automatico

```bash
#!/bin/bash
# Script de escaneamento de seguranca automatico

# Configuracao
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="mydb"
DB_USER="security_scanner"
LOG_DIR="/var/log/db_security"
REPORT_DIR="/var/log/db_security/reports"
DATE=$(date +%Y%m%d_%H%M%S)

# Criar diretorios
mkdir -p $LOG_DIR $REPORT_DIR

# Funcao para log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_DIR/scan_$DATE.log
}

# 1. Verificar versao do banco
log "Verificando versao do banco de dados..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > $REPORT_DIR/version_$DATE.txt

# 2. Verificar usuarios com privilegios excessivos
log "Verificando usuarios com privilegios excessivos..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin
FROM pg_roles
WHERE rolsuper = true OR rolcreaterole = true OR rolcreatedb = true
ORDER BY rolname;
" > $REPORT_DIR/privileged_users_$DATE.txt

# 3. Verificar configuracao de seguranca
log "Verificando configuracao de seguranca..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    'ssl' as config_name,
    current_setting('ssl') as value,
    CASE WHEN current_setting('ssl') = 'on' THEN 'OK' ELSE 'CRITICAL' END as status
UNION ALL
SELECT
    'password_encryption',
    current_setting('password_encryption'),
    CASE WHEN current_setting('password_encryption') = 'scram-sha-256' THEN 'OK' ELSE 'WARNING' END
UNION ALL
SELECT
    'log_connections',
    current_setting('log_connections'),
    CASE WHEN current_setting('log_connections') = 'on' THEN 'OK' ELSE 'WARNING' END
UNION ALL
SELECT
    'log_disconnections',
    current_setting('log_disconnections'),
    CASE WHEN current_setting('log_disconnections') = 'on' THEN 'OK' ELSE 'WARNING' END
UNION ALL
SELECT
    'log_statement',
    current_setting('log_statement'),
    CASE WHEN current_setting('log_statement') IN ('ddl', 'mod', 'all') THEN 'OK' ELSE 'WARNING' END;
" > $REPORT_DIR/security_config_$DATE.txt

# 4. Verificar tabelas sem criptografia
log "Verificando tabelas com dados sensiveis..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    schemaname,
    tablename,
    column_name,
    data_type,
    CASE
        WHEN column_name LIKE '%password%' OR column_name LIKE '%secret%' OR column_name LIKE '%key%'
        THEN 'REQUIRES_ENCRYPTION'
        ELSE 'OK'
    END as encryption_status
FROM information_schema.columns
WHERE table_schema = 'public'
AND (column_name LIKE '%password%' OR column_name LIKE '%secret%' OR column_name LIKE '%key%'
     OR column_name LIKE '%credit%' OR column_name LIKE '%ssn%')
ORDER BY schemaname, tablename, column_name;
" > $REPORT_DIR/sensitive_data_$DATE.txt

# 5. Verificar indices nao utilizados
log "Verificando indices nao utilizados..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan as times_used,
    CASE
        WHEN idx_scan = 0 THEN 'UNUSED - CONSIDER REMOVING'
        WHEN idx_scan < 10 THEN 'LOW USAGE - REVIEW'
        ELSE 'OK'
    END as recommendation
FROM pg_stat_user_indexes
WHERE pg_relation_size(indexrelid) > 1024 * 1024
ORDER BY pg_relation_size(indexrelid) DESC;
" > $REPORT_DIR/unused_indexes_$DATE.txt

# 6. Verificar queries lentas
log "Verificando queries lentas..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- Mais de 1 segundo
ORDER BY mean_exec_time DESC
LIMIT 10;
" > $REPORT_DIR/slow_queries_$DATE.txt

# 7. Verificar conexoes ativas
log "Verificando conexoes ativas..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    client_port,
    backend_start,
    state,
    query_start,
    state_change
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY query_start;
" > $REPORT_DIR/active_connections_$DATE.txt

# 8. Verificar espaco em disco
log "Verificando espaco em disco..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) as table_size,
    pg_size_pretty(pg_indexes_size((schemaname || '.' || tablename)::regclass)) as index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 10;
" > $REPORT_DIR/disk_usage_$DATE.txt

# 9. Gerar relatorio consolidado
log "Gerando relatorio consolidado..."
cat > $REPORT_DIR/consolidated_report_$DATE.md <<EOF
# Relatorio de Seguranca do Banco de Dados
Data: $(date)
Banco: $DB_NAME@$DB_HOST:$DB_PORT

## Resumo

- Versao do banco: $(cat $REPORT_DIR/version_$DATE.txt | tail -1)
- Usuarios privilegiados: $(wc -l < $REPORT_DIR/privileged_users_$DATE.txt)
- Configuracoes criticas: $(grep -c "CRITICAL" $REPORT_DIR/security_config_$DATE.txt)
- Dados sensiveis: $(grep -c "REQUIRES_ENCRYPTION" $REPORT_DIR/sensitive_data_$DATE.txt)
- Indices nao utilizados: $(grep -c "UNUSED" $REPORT_DIR/unused_indexes_$DATE.txt)
- Queries lentas: $(wc -l < $REPORT_DIR/slow_queries_$DATE.txt)
- Conexoes ativas: $(grep -c "active" $REPORT_DIR/active_connections_$DATE.txt)

## Acoes Recomendadas

1. Corrigir configuracoes criticas de seguranca
2. Implementar criptografia para dados sensiveis
3. Remover indices nao utilizados
4. Otimizar queries lentas
5. Revisar privilegios de usuarios

## Arquivos de Relatorio

$(ls -la $REPORT_DIR/*_$DATE.txt)
EOF

log "Escaneamento concluido. Relatorios salvos em $REPORT_DIR"
```

## Security Hardening Checklist

### Checklist de Hardening

```sql
-- Checklist de hardening para bancos de dados

-- 1. INSTALACAO E CONFIGURACAO
-- [ ] Banco instalado de forma segura
-- [ ] Diretorios com permissoes adequadas (700/750)
-- [ ] Usuario dedicado para o banco de dados
-- [ ] Servicos desnecessarios desabilitados
-- [ ] Firewall configurado
-- [ ] SELinux/AppArmor habilitado

-- 2. AUTENTICACAO
-- [ ] Politicas de senha fortes implementadas
-- [ ] Senhas criptografadas (scram-sha-256 ou superior)
-- [ ] MFA habilitado para acessos criticos
-- [ ] Contas de padrao removidas ou renomeadas
-- [ ] Limite de tentativas de login configurado
-- [ ] Contas de usuario expiradas bloqueadas

-- 3. AUTORIZACAO
-- [ ] Princípio de menor privilegio implementado
-- [ ] Roles baseadas em funcoes criadas
-- [ ] Privilegios minimos atribuidos
-- [ ] Acesso de superusuario restrito
-- [ ] Acesso de rede restrito
-- [ ] Revogacao de privilegios automatizada

-- 4. CRIPTOGRAFIA
-- [ ] SSL/TLS habilitado para conexoes
-- [ ] Certificados validos e atualizados
-- [ ] Dados sensiveis criptografados em repouso
-- [ ] Chaves de criptografia gerenciadas de forma segura
-- [ ] Backup criptografado
-- [ ] Rotacao de chaves implementada

-- 5. LOGGING E AUDITORIA
-- [ ] Logs de conexao habilitados
-- [ ] Logs de desconexao habilitados
-- [ ] Logs de DDL habilitados
-- [ ] Logs de DML habilitados (para tabelas criticas)
-- [ ] Logs de erros habilitados
-- [ ] Logs armazenados em local seguro
-- [ ] Retencao de logs definida

-- 6. MONITORAMENTO
-- [ ] Monitoramento de conexoes ativas
-- [ ] Monitoramento de queries lentas
-- [ ] Monitoramento de uso de recursos
-- [ ] Alertas configurados para eventos criticos
-- [ ] Dashboard de seguranca implementado
-- [ ] Relatorios automaticos gerados

-- 7. BACKUP E RECUPERACAO
-- [ ] Backups automaticos configurados
-- [ ] Backups criptografados
-- [ ] Backups testados regularmente
-- [ ] Plano de recuperacao documentado
-- [ ] Tempo de recuperacao (RTO) definido
-- [ ] Ponto de recuperacao (RPO) definido

-- 8. COMPLIANCE
-- [ ] Requisitos de compliance identificados
-- [ ] Controles de compliance implementados
-- [ ] Auditorias de compliance realizadas
-- [ ] Documentacao de compliance mantida
-- [ ] Treinamento de compliance realizado
-- [ ] Revisoes periodicas de compliance

-- 9. SEGURANCA DA REDE
-- [ ] VPN configurada para acessos remotos
-- [ ] Segmentacao de rede implementada
-- [ ] Acesso restrito por IP
-- [ ] Monitoramento de trafego
-- [ ] Protecao contra DDoS
-- [ ] DNS seguro configurado

-- 10. MANUTENCAO
-- [ ] Patches de seguranca aplicados regularmente
-- [ ] Atualizacoes de versao planejadas
-- [ ] Revisoes de seguranca periodicas
-- [ ] Testes de penetracao realizados
-- [ ] Avaliacao de vulnerabilidades continua
-- [ ] Plano de resposta a incidentes atualizado
```

## Conclusao

Database hardening e essencial para proteger dados sensiveis contra ameacas. Este capitulo cobriu:

- Instalacao segura de PostgreSQL e MySQL
- Configuracao de rede (bind address, portas, firewall, VPN)
- Autenticacao (politicas de senha, SSL/TLS, MFA)
- Encryption at rest (TDE, backup encryption)
- Encryption in transit (SSL/TLS, certificados)
- User management (least privilege, RBAC, password rotation)
- Audit logging (pgAudit, audit plugin, triggers)
- Vulnerability scanning (Nessus, Qualys, CIS Benchmarks)
- Network security (VPN, segmentacao de rede)
- Data masking (mascaramento de dados)
- Database Activity Monitoring (DAM)
- Incident response (playbooks, lições aprendidas)
- Compliance (PCI DSS, HIPAA, GDPR)
- Database security testing
- Encryption key management
- Security monitoring dashboards
- Automated security scanning
- Security hardening checklist
- Exemplos completos de hardening para PostgreSQL e MySQL

Seguranca de bancos de dados e uma camada continua de protecao. Implementar essas praticas reduz drasticamente o risco de incidentes de seguranca e garante conformidade com regulamentacoes. A chave e adotar uma abordagem em camadas (defense in depth) e manter vigilancia constante. Use o checklist de hardening como guia para garantir que todas as medidas de seguranca estejam implementadas.