# Compliance e Normas

## Visao Geral

Compliance nao e opcional para organizacoes que manipulam dados sensiveis. Regulamentacoes como PCI DSS, LGPD, GDPR, HIPAA, SOC 2 e ISO 27001 definem requisitos especificos para protecao de dados, incluindo criptografia, controle de acesso, auditoria e retencao. Este capitulo explora como cada regulamentacao se aplica a databases, quais controles sao obrigatorios e como implementa-los em PostgreSQL e MySQL. Alem disso, abordamos classificacao de dados, gerenciamento de chaves, politicas de retencao, transferencia internacional de dados e automacao de compliance.

## PCI DSS Requirements para Databases

### Visao Geral do PCI DSS

O Payment Card Industry Data Security Standard (PCI DSS) e um conjunto de requisitos de seguranca para organizacoes que processam, armazenam ou transmitem dados de cartao de credito. Qualquer organizacao que aceita pagamentos com cartao de credito deve cumprir com o PCI DSS, independentemente de tamanho.

O PCI DSS e dividido em 12 requisitos agrupados em 6 objetivos. Para databases, os requisitos mais relevantes sao:

### Requisito 3: Proteger Dados de Titulares Armazenados

```sql
-- PCI DSS 3.4: Renderizar ilegiveis todos os dados de titulares armazenados
-- Os dados devem ser criptografados usando algoritmos fortes

-- Implementacao no PostgreSQL com pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Criar tabela com criptografia de colunas sensiveis
CREATE TABLE payment_cards (
    card_id SERIAL PRIMARY KEY,
    cardholder_name VARCHAR(255) NOT NULL,
    card_number_encrypted BYTEA NOT NULL,
    card_number_last_four CHAR(4) NOT NULL,  -- Para referencia
    card_number_masked VARCHAR(19) NOT NULL,  -- Para exibicao
    expiration_date_encrypted BYTEA NOT NULL,
    cvv_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Funcao para inserir dados criptografados
CREATE OR REPLACE FUNCTION insert_payment_card(
    p_cardholder_name VARCHAR,
    p_card_number VARCHAR,
    p_expiration_date VARCHAR,
    p_cvv VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_card_id INT;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    INSERT INTO payment_cards (
        cardholder_name,
        card_number_encrypted,
        card_number_last_four,
        card_number_masked,
        expiration_date_encrypted,
        cvv_encrypted
    )
    VALUES (
        p_cardholder_name,
        pgp_sym_encrypt(p_card_number, v_master_key),
        RIGHT(p_card_number, 4),
        '****-****-****-' || RIGHT(p_card_number, 4),
        pgp_sym_encrypt(p_expiration_date, v_master_key),
        pgp_sym_encrypt(p_cvv, v_master_key)
    )
    RETURNING card_id INTO v_card_id;
    
    RETURN v_card_id;
END;
$$ LANGUAGE plpgsql;

-- Funcao para descriptografar (apenas para uso autorizado)
CREATE OR REPLACE FUNCTION get_payment_card(
    p_card_id INT,
    p_requester VARCHAR
)
RETURNS TABLE(
    cardholder_name VARCHAR,
    card_number VARCHAR,
    expiration_date VARCHAR
) AS $$
DECLARE
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    -- Log de acesso (obrigatorio PCI DSS)
    INSERT INTO pci_access_log (card_id, requester, access_time, access_type)
    VALUES (p_card_id, p_requester, NOW(), 'DECRYPT');
    
    RETURN QUERY
    SELECT 
        pc.cardholder_name,
        pgp_sym_decrypt(pc.card_number_encrypted, v_master_key),
        pgp_sym_decrypt(pc.expiration_date_encrypted, v_master_key)
    FROM payment_cards pc
    WHERE pc.card_id = p_card_id;
END;
$$ LANGUAGE plpgsql;
```

### Requisito 3.5 e 3.6: Gerenciamento de Chaves

```sql
-- PCI DSS requer gerenciamento seguro de chaves de criptografia

-- Tabela de gestao de chaves
CREATE TABLE encryption_key_management (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name VARCHAR(255) NOT NULL,
    key_type VARCHAR(50) NOT NULL,  -- MASTER, DATA, TRANSPORT, WRAPPING
    key_algorithm VARCHAR(50) NOT NULL,
    key_length INT NOT NULL,
    key_material_encrypted BYTEA NOT NULL,
    created_by VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    rotated_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    hsm_slot VARCHAR(100),
    key_version INT DEFAULT 1
);

-- Funcao para rotacao de chaves (PCI DSS 3.6.4)
CREATE OR REPLACE FUNCTION rotate_encryption_key(
    p_key_name VARCHAR,
    p_new_key_material BYTEA
)
RETURNS UUID AS $$
DECLARE
    v_old_key_id UUID;
    v_new_key_id UUID;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    -- Marcar chave antiga como inativa
    UPDATE encryption_key_management
    SET is_active = FALSE,
        rotated_at = NOW()
    WHERE key_name = p_key_name
    AND is_active = TRUE
    RETURNING key_id INTO v_old_key_id;
    
    -- Criar nova chave
    INSERT INTO encryption_key_management (
        key_name, key_type, key_algorithm, key_length,
        key_material_encrypted, created_by, expires_at, key_version
    )
    VALUES (
        p_key_name, 'DATA', 'AES-256', 256,
        pgp_sym_encrypt(p_new_key_material::text, v_master_key),
        current_user,
        NOW() + INTERVAL '90 days',
        (SELECT COALESCE(MAX(key_version), 0) + 1 
         FROM encryption_key_management 
         WHERE key_name = p_key_name)
    )
    RETURNING key_id INTO v_new_key_id;
    
    -- Log de rotacao (obrigatorio PCI DSS)
    INSERT INTO key_rotation_log (old_key_id, new_key_id, rotated_by, rotated_at)
    VALUES (v_old_key_id, v_new_key_id, current_user, NOW());
    
    RETURN v_new_key_id;
END;
$$ LANGUAGE plpgsql;

-- Verificar chaves proximas do vencimento
SELECT 
    key_name,
    key_version,
    expires_at,
    EXTRACT(DAY FROM expires_at - NOW()) AS days_until_expiry,
    CASE 
        WHEN expires_at < NOW() THEN 'CRITICAL: Expired'
        WHEN expires_at < NOW() + INTERVAL '7 days' THEN 'HIGH: Expiring soon'
        WHEN expires_at < NOW() + INTERVAL '30 days' THEN 'MEDIUM: Plan rotation'
        ELSE 'OK'
    END AS status
FROM encryption_key_management
WHERE is_active = TRUE
ORDER BY expires_at;
```

### Requisito 8: Autenticacao

```sql
-- PCI DSS 8.3: Autenticacao robusta para acesso a dados de cartao

-- 1. Senhas fortes
CREATE TABLE password_policy (
    policy_id SERIAL PRIMARY KEY,
    min_length INT DEFAULT 12,
    require_uppercase BOOLEAN DEFAULT TRUE,
    require_lowercase BOOLEAN DEFAULT TRUE,
    require_numbers BOOLEAN DEFAULT TRUE,
    require_special_chars BOOLEAN DEFAULT TRUE,
    max_age_days INT DEFAULT 90,
    history_count INT DEFAULT 12,
    lockout_attempts INT DEFAULT 6,
    lockout_duration_minutes INT DEFAULT 30
);

-- Funcao para validar senha
CREATE OR REPLACE FUNCTION validate_password_strength(p_password TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_policy RECORD;
    v_valid BOOLEAN := TRUE;
BEGIN
    SELECT * INTO v_policy FROM password_policy WHERE policy_id = 1;
    
    IF LENGTH(p_password) < v_policy.min_length THEN
        v_valid := FALSE;
    END IF;
    
    IF v_policy.require_uppercase AND p_password !~ '[A-Z]' THEN
        v_valid := FALSE;
    END IF;
    
    IF v_policy.require_lowercase AND p_password !~ '[a-z]' THEN
        v_valid := FALSE;
    END IF;
    
    IF v_policy.require_numbers AND p_password !~ '[0-9]' THEN
        v_valid := FALSE;
    END IF;
    
    IF v_policy.require_special_chars AND p_password !~ '[!@#$%^&*(),.?":{}|<>]' THEN
        v_valid := FALSE;
    END IF;
    
    RETURN v_valid;
END;
$$ LANGUAGE plpgsql;

-- 2. MFA para todos os acessos a databases de cartao
-- (configurado via pg_hba.conf e extensao de autenticacao)

-- 3. Bloco de conta apos tentativas falhas
CREATE TABLE account_lockout (
    lockout_id SERIAL PRIMARY KEY,
    username VARCHAR(128),
    lockout_time TIMESTAMPTZ,
    unlock_time TIMESTAMPTZ,
    failed_attempts INT,
    reason VARCHAR(255)
);

-- Funcao de bloqueio automatico
CREATE OR REPLACE FUNCTION check_and_lock_account(p_username VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_failed_count INT;
    v_policy RECORD;
BEGIN
    SELECT * INTO v_policy FROM password_policy WHERE policy_id = 1;
    
    SELECT COUNT(*) INTO v_failed_count
    FROM login_attempts
    WHERE username = p_username
    AND success = FALSE
    AND attempt_time > NOW() - INTERVAL '15 minutes';
    
    IF v_failed_count >= v_policy.lockout_attempts THEN
        INSERT INTO account_lockout (username, lockout_time, failed_attempts, reason)
        VALUES (p_username, NOW(), v_failed_count, 'Exceeded failed login attempts');
        
        UPDATE users SET is_locked = TRUE WHERE username = p_username;
        
        RETURN TRUE;  -- Conta bloqueada
    END IF;
    
    RETURN FALSE;  -- Conta ainda ativa
END;
$$ LANGUAGE plpgsql;
```

### Requisito 10: Rastreamento e Monitoramento

```sql
-- PCI DSS 10: Monitorar e rastrear todos os acessos a dados de cartao

-- Implementacao de audit trail completo
CREATE TABLE pci_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    user_name VARCHAR(128),
    source_ip INET,
    database_name VARCHAR(128),
    table_name VARCHAR(256),
    operation VARCHAR(20),
    query_text TEXT,
    rows_affected BIGINT,
    success BOOLEAN,
    error_message TEXT
);

-- Indices para performance de queries de auditoria
CREATE INDEX idx_pci_audit_time ON pci_audit_log (event_time);
CREATE INDEX idx_pci_audit_user ON pci_audit_log (user_name);
CREATE INDEX idx_pci_audit_type ON pci_audit_log (event_type);

-- Funcao de auditoria automatica
CREATE OR REPLACE FUNCTION pci_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO pci_audit_log (
        event_type, user_name, source_ip, database_name,
        table_name, operation, rows_affected, success
    )
    VALUES (
        TG_OP,
        current_user,
        inet_client_addr(),
        current_database(),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        TG_OP,
        1,
        TRUE
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em todas as tabelas de dados de cartao
CREATE TRIGGER audit_payment_cards
    AFTER INSERT OR UPDATE OR DELETE ON payment_cards
    FOR EACH ROW
    EXECUTE FUNCTION pci_audit_trigger();

-- Relatorio de auditoria PCI DSS
SELECT 
    date_trunc('day', event_time) AS day,
    user_name,
    COUNT(*) AS total_events,
    COUNT(CASE WHEN event_type = 'INSERT' THEN 1 END) AS inserts,
    COUNT(CASE WHEN event_type = 'UPDATE' THEN 1 END) AS updates,
    COUNT(CASE WHEN event_type = 'DELETE' THEN 1 END) AS deletes,
    COUNT(CASE WHEN NOT success THEN 1 END) AS failures
FROM pci_audit_log
WHERE event_time > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', event_time), user_name
ORDER BY day DESC, total_events DESC;
```

## LGPD para Bancos de Dados

### Visao Geral da LGPD

A Lei Geral de Protecao de Dados (LGPD) e a legislacao brasileira de protecao de dados pessoais, vigente desde setembro de 2020. A LGPD se aplica a qualquer operacao de tratamento de dados pessoais realizada no territorio brasileiro ou que tenha como objetivo oferta ou fornecimento de bens ou servicos a titulares localizados no Brasil.

### Art. 46: Seguranca e Sigilo

```sql
-- LGPD Art. 46: Os agentes de tratamento devem adotar medidas de seguranca
-- tecnicas e administrativas aptas a proteger os dados pessoais

-- Implementacao de seguranca tecnica

-- 1. Criptografia de dados pessoais
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE personal_data_protected (
    id SERIAL PRIMARY KEY,
    full_name_encrypted BYTEA NOT NULL,
    cpf_encrypted BYTEA NOT NULL,
    email_encrypted BYTEA NOT NULL,
    phone_encrypted BYTEA,
    address_encrypted BYTEA,
    birth_date_encrypted BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMPTZ,
    data_source VARCHAR(100),
    retention_period_days INT DEFAULT 365,
    expires_at TIMESTAMPTZ GENERATED ALWAYS AS 
        (created_at + (retention_period_days || ' days')::INTERVAL) STORED
);

-- Funcao para inserir dados com consentimento
CREATE OR REPLACE FUNCTION insert_personal_data(
    p_full_name VARCHAR,
    p_cpf VARCHAR,
    p_email VARCHAR,
    p_phone VARCHAR,
    p_address VARCHAR,
    p_birth_date VARCHAR,
    p_consent BOOLEAN,
    p_data_source VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_id INT;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    -- Verificar consentimento (LGPD Art. 7)
    IF NOT p_consent THEN
        RAISE EXCEPTION 'Consentimento obrigatorio para tratamento de dados pessoais (LGPD Art. 7)';
    END IF;
    
    INSERT INTO personal_data_protected (
        full_name_encrypted, cpf_encrypted, email_encrypted,
        phone_encrypted, address_encrypted, birth_date_encrypted,
        consent_given, consent_date, data_source
    )
    VALUES (
        pgp_sym_encrypt(p_full_name, v_master_key),
        pgp_sym_encrypt(p_cpf, v_master_key),
        pgp_sym_encrypt(p_email, v_master_key),
        pgp_sym_encrypt(p_phone, v_master_key),
        pgp_sym_encrypt(p_address, v_master_key),
        pgp_sym_encrypt(p_birth_date, v_master_key),
        p_consent,
        NOW(),
        p_data_source
    )
    RETURNING id INTO v_id;
    
    -- Log de tratamento (obrigatorio LGPD)
    INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at)
    VALUES (v_id, 'COLLECTION', 'CONSENT', current_user, NOW());
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funcao para anonimizar dados (LGPD Art. 16)
CREATE OR REPLACE FUNCTION anonymize_personal_data(p_data_id INT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE personal_data_protected SET
        full_name_encrypted = pgp_sym_encrypt('ANONIMIZADO', current_setting('app.master_key')),
        cpf_encrypted = pgp_sym_encrypt('000.000.000-00', current_setting('app.master_key')),
        email_encrypted = pgp_sym_encrypt('anonimo@anonimo.com', current_setting('app.master_key')),
        phone_encrypted = pgp_sym_encrypt('00000000000', current_setting('app.master_key')),
        address_encrypted = pgp_sym_encrypt('ANONIMIZADO', current_setting('app.master_key')),
        birth_date_encrypted = pgp_sym_encrypt('01/01/1900', current_setting('app.master_key'))
    WHERE id = p_data_id;
    
    -- Log de anonimizacao
    INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at)
    VALUES (p_data_id, 'ANONYMIZATION', 'LEGAL_OBLIGATION', current_user, NOW());
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

### Art. 47: Direitos dos Titulares

```sql
-- LGPD Art. 47: Garantir direitos dos titulares

-- 1. Direito de acesso (Art. 18, II)
CREATE OR REPLACE FUNCTION get_personal_data_for_subject(
    p_cpf VARCHAR
)
RETURNS TABLE(
    data_field VARCHAR,
    data_value TEXT,
    consent_given BOOLEAN,
    consent_date TIMESTAMPTZ,
    data_source VARCHAR
) AS $$
DECLARE
    v_master_key TEXT := current_setting('app.master_key');
    v_data RECORD;
BEGIN
    -- Log da solicitacao
    INSERT INTO lgpd_access_log (cpf_hash, requester, access_time, access_type)
    VALUES (encode(sha256(p_cpf::bytea), 'hex'), current_user, NOW(), 'SUBJECT_ACCESS');
    
    FOR v_data IN 
        SELECT * FROM personal_data_protected 
        WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key)
    LOOP
        data_field := 'full_name';
        data_value := pgp_sym_decrypt(v_data.full_name_encrypted, v_master_key);
        consent_given := v_data.consent_given;
        consent_date := v_data.consent_date;
        data_source := v_data.data_source;
        RETURN NEXT;
        
        data_field := 'cpf';
        data_value := pgp_sym_decrypt(v_data.cpf_encrypted, v_master_key);
        RETURN NEXT;
        
        data_field := 'email';
        data_value := pgp_sym_decrypt(v_data.email_encrypted, v_master_key);
        RETURN NEXT;
        
        data_field := 'phone';
        data_value := pgp_sym_decrypt(v_data.phone_encrypted, v_master_key);
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 2. Direito de correcao (Art. 18, III)
CREATE OR REPLACE FUNCTION correct_personal_data(
    p_cpf VARCHAR,
    p_field VARCHAR,
    p_new_value VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_master_key TEXT := current_setting('app.master_key');
    v_affected_rows INT;
BEGIN
    -- Log da correcao
    INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at, details)
    VALUES (
        (SELECT id FROM personal_data_protected 
         WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key)),
        'CORRECTION',
        'LEGAL_OBLIGATION',
        current_user,
        NOW(),
        FORMAT('Field corrected: %s', p_field)
    );
    
    CASE p_field
        WHEN 'full_name' THEN
            UPDATE personal_data_protected 
            SET full_name_encrypted = pgp_sym_encrypt(p_new_value, v_master_key)
            WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
        WHEN 'email' THEN
            UPDATE personal_data_protected 
            SET email_encrypted = pgp_sym_encrypt(p_new_value, v_master_key)
            WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
        WHEN 'phone' THEN
            UPDATE personal_data_protected 
            SET phone_encrypted = pgp_sym_encrypt(p_new_value, v_master_key)
            WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
        WHEN 'address' THEN
            UPDATE personal_data_protected 
            SET address_encrypted = pgp_sym_encrypt(p_new_value, v_master_key)
            WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
        ELSE
            RAISE EXCEPTION 'Campo nao elegivel para correcao: %', p_field;
    END CASE;
    
    GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
    RETURN v_affected_rows > 0;
END;
$$ LANGUAGE plpgsql;

-- 3. Direito de eliminacao (Art. 18, VI)
CREATE OR REPLACE FUNCTION delete_personal_data(p_cpf VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_data_id INT;
    v_master_key TEXT := current_setting('app.master_key');
BEGIN
    SELECT id INTO v_data_id
    FROM personal_data_protected
    WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Verificar se ha obrigacao legal de manter os dados
    -- (ex: obrigatoriedade fiscal, contabil)
    IF EXISTS (
        SELECT 1 FROM legal_retention_requirements
        WHERE data_type = 'PERSONAL'
        AND expiry_date > NOW()
    ) THEN
        -- Em vez de deletar, anonimizar
        PERFORM anonymize_personal_data(v_data_id);
        
        INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at, details)
        VALUES (v_data_id, 'ANONYMIZATION_INSTEAD_OF_DELETION', 'LEGAL_OBLIGATION', current_user, NOW(),
                'Dados anonimizados em vez de deletados devido a obrigacao legal');
    ELSE
        -- Deletar permanentemente
        DELETE FROM personal_data_protected WHERE id = v_data_id;
        
        INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at)
        VALUES (v_data_id, 'DELETION', 'SUBJECT_REQUEST', current_user, NOW());
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 4. Direito de portabilidade (Art. 18, V)
CREATE OR REPLACE FUNCTION export_personal_data_portable(
    p_cpf VARCHAR
)
RETURNS JSON AS $$
DECLARE
    v_master_key TEXT := current_setting('app.master_key');
    v_data RECORD;
    v_result JSON;
BEGIN
    SELECT 
        pgp_sym_decrypt(full_name_encrypted, v_master_key) AS full_name,
        pgp_sym_decrypt(cpf_encrypted, v_master_key) AS cpf,
        pgp_sym_decrypt(email_encrypted, v_master_key) AS email,
        pgp_sym_decrypt(phone_encrypted, v_master_key) AS phone,
        pgp_sym_decrypt(address_encrypted, v_master_key) AS address,
        pgp_sym_decrypt(birth_date_encrypted, v_master_key) AS birth_date,
        consent_given,
        consent_date,
        data_source
    INTO v_data
    FROM personal_data_protected
    WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key);
    
    v_result := json_build_object(
        'personal_data', json_build_object(
            'full_name', v_data.full_name,
            'cpf', v_data.cpf,
            'email', v_data.email,
            'phone', v_data.phone,
            'address', v_data.address,
            'birth_date', v_data.birth_date
        ),
        'consent', json_build_object(
            'given', v_data.consent_given,
            'date', v_data.consent_date
        ),
        'metadata', json_build_object(
            'source', v_data.data_source,
            'export_date', NOW(),
            'format', 'LGPD_PORTABLE'
        )
    );
    
    -- Log de exportacao
    INSERT INTO lgpd_treatment_log (data_id, treatment_type, legal_basis, treated_by, treated_at)
    VALUES (
        (SELECT id FROM personal_data_protected 
         WHERE cpf_encrypted = pgp_sym_encrypt(p_cpf, v_master_key)),
        'PORTABILITY_EXPORT',
        'SUBJECT_REQUEST',
        current_user,
        NOW()
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
```

## GDPR Article 32 e Encryption

### Visao Geral do GDPR

O General Data Protection Regulation (GDPR) e a regulamentacao europeia de protecao de dados. O Artigo 32 especifica as medidas tecnicas e organizacionais de seguranca que devem ser implementadas.

### Article 32: Seguranca do Tratamento

```sql
-- GDPR Art. 32 exige:
-- a) Pseudonimizacao e criptografia de dados pessoais
-- b) Capacidade de garantir confidencialidade, integridade, disponibilidade
-- c) Capacidade de restaurar dados em tempo opportuno
-- d) Processo de testes, avaliacao e medicao regulares

-- Implementacao completa de Art. 32

-- 1. Pseudonimizacao
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE gdpr_pseudonymized (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pseudonym_id VARCHAR(64) NOT NULL UNIQUE,
    data_encrypted BYTEA NOT NULL,
    pseudonym_key_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data_controller VARCHAR(255),
    legal_basis VARCHAR(100),
    purpose VARCHAR(255)
);

-- Funcao de pseudonimizacao
CREATE OR REPLACE FUNCTION pseudonymize_data(
    p_real_id VARCHAR,
    p_data JSONB,
    p_purpose VARCHAR
)
RETURNS VARCHAR AS $$
DECLARE
    v_pseudonym VARCHAR;
    v_key_id UUID;
    v_encrypted_data BYTEA;
BEGIN
    -- Gerar pseudonimo deterministico (mas nao reversivel sem chave)
    v_pseudonym := encode(
        hmac_sha256(p_real_id::bytea, current_setting('app.pseudonym_key')::bytea),
        'hex'
    );
    
    -- Selecionar chave ativa
    SELECT key_id INTO v_key_id
    FROM encryption_key_management
    WHERE key_name = 'GDPR_PSEUDONYMIZATION'
    AND is_active = TRUE
    AND expires_at > NOW();
    
    -- Criptografar dados
    v_encrypted_data := pgp_sym_encrypt(
        p_data::text,
        (SELECT key_material_encrypted::text FROM encryption_key_management WHERE key_id = v_key_id)
    );
    
    INSERT INTO gdpr_pseudonymized (pseudonym_id, data_encrypted, pseudonym_key_id, legal_basis, purpose)
    VALUES (v_pseudonym, v_encrypted_data, v_key_id, 'CONSENT', p_purpose);
    
    RETURN v_pseudonym;
END;
$$ LANGUAGE plpgsql;

-- 2. Criptografia (Art. 32(1)(a))
-- Ja implementada nas secoes anteriores

-- 3. Capacidade de restauracao (Art. 32(1)(c))
CREATE TABLE backup_schedule (
    backup_id SERIAL PRIMARY KEY,
    backup_type VARCHAR(50),  -- FULL, INCREMENTAL, TRANSACTION_LOG
    frequency VARCHAR(50),    -- DAILY, HOURLY, REAL_TIME
    retention_days INT,
    last_backup_time TIMESTAMPTZ,
    next_backup_time TIMESTAMPTZ,
    backup_location VARCHAR(500),
    encrypted BOOLEAN DEFAULT TRUE,
    tested BOOLEAN DEFAULT FALSE,
    last_test_date DATE,
    rto_hours INT,  -- Recovery Time Objective
    rpo_minutes INT -- Recovery Point Objective
);

INSERT INTO backup_schedule VALUES
(1, 'FULL', 'DAILY', 90, NOW() - INTERVAL '1 day', NOW() + INTERVAL '1 day',
 '/backups/full/', TRUE, TRUE, CURRENT_DATE - 30, 4, 60),
(2, 'INCREMENTAL', 'HOURLY', 30, NOW() - INTERVAL '1 hour', NOW() + INTERVAL '1 hour',
 '/backups/incremental/', TRUE, TRUE, CURRENT_DATE - 7, 1, 15),
(3, 'TRANSACTION_LOG', 'REAL_TIME', 30, NOW() - INTERVAL '5 minutes', NOW() + INTERVAL '5 minutes',
 '/backups/wal/', TRUE, TRUE, CURRENT_DATE - 1, 0, 5);

-- Verificar conformidade de backups
SELECT 
    backup_type,
    frequency,
    last_backup_time,
    EXTRACT(EPOCH FROM (NOW() - last_backup_time)) / 3600 AS hours_since_backup,
    tested,
    last_test_date,
    CASE 
        WHEN last_test_date < CURRENT_DATE - INTERVAL '30 days' THEN 'WARNING: Backup not tested recently'
        WHEN EXTRACT(EPOCH FROM (NOW() - last_backup_time)) / 3600 > 25 THEN 'CRITICAL: Backup overdue'
        ELSE 'OK'
    END AS status
FROM backup_schedule;

-- 4. Testes e avaliacoes regulares (Art. 32(1)(d))
CREATE TABLE gdpr_security_assessments (
    assessment_id SERIAL PRIMARY KEY,
    assessment_type VARCHAR(100),
    assessment_date DATE,
    assessor VARCHAR(255),
    scope TEXT,
    findings INT,
    critical_findings INT,
    high_findings INT,
    remediation_plan TEXT,
    next_assessment_date DATE,
    status VARCHAR(20)
);

INSERT INTO gdpr_security_assessments VALUES
(1, 'Data Protection Impact Assessment', CURRENT_DATE - 90, 'Security Team',
 'All personal data processing activities', 15, 2, 5, 
 'Remediation plan documented', CURRENT_DATE + 90, 'COMPLETED'),
(2, 'Penetration Test - Database', CURRENT_DATE - 60, 'External Auditor',
 'Production databases with personal data', 8, 0, 3,
 'Critical issues fixed, high issues in progress', CURRENT_DATE + 180, 'IN_PROGRESS'),
(3, 'Access Control Review', CURRENT_DATE - 30, 'DBA Team',
 'All database user accounts', 22, 1, 8,
 'Unused accounts revoked, excessive permissions reduced', CURRENT_DATE + 90, 'COMPLETED');
```

## HIPAA para Dados de Saude

### Visao Geral do HIPAA

O Health Insurance Portability and Accountability Act (HIPAA) e a legislacao americana que protege dados de saude de pacientes (Protected Health Information - PHI). Organizacoes que lidam com PHI devem implementar controles especificos de seguranca.

### Controles de Seguranca para PHI

```sql
-- HIPAA exige protecao especifica para dados de saude (PHI)
-- Protected Health Information inclui: nomes, datas, numeros de telefone,
-- SSN, numeros de registro medico, diagnosticos, procedimentos, etc.

-- Implementacao de PHI protection

CREATE TABLE protected_health_info (
    phi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_mrn VARCHAR(50) NOT NULL,  -- Medical Record Number
    patient_name_encrypted BYTEA NOT NULL,
    dob_encrypted BYTEA NOT NULL,
    ssn_encrypted BYTEA NOT NULL,
    diagnosis_code VARCHAR(20),
    diagnosis_description_encrypted BYTEA,
    treatment_date DATE,
    provider VARCHAR(255),
    insurance_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data_classification VARCHAR(20) DEFAULT 'PHI',
    minimum_necessary BOOLEAN DEFAULT TRUE
);

-- HIPAA Minimum Necessary Rule
-- Apenas os dados minimos necessarios para a funcao devem ser acessados

-- View para profissionais de saude (acesso clinico)
CREATE VIEW phi_clinical_view AS
SELECT 
    phi_id,
    patient_mrn,
    pgp_sym_decrypt(patient_name_encrypted, current_setting('app.phi_key')) AS patient_name,
    pgp_sym_decrypt(dob_encrypted, current_setting('app.phi_key')) AS dob,
    diagnosis_code,
    pgp_sym_decrypt(diagnosis_description_encrypted, current_setting('app.phi_key')) AS diagnosis,
    treatment_date,
    provider
FROM protected_health_info;

-- View para faturamento (acesso limitado)
CREATE VIEW phi_billing_view AS
SELECT 
    phi_id,
    patient_mrn,
    diagnosis_code,
    treatment_date,
    insurance_id
FROM protected_health_info;
-- NAO inclui: nome, data de nascimento, SSN, diagnostico detalhado

-- Controle de acesso baseado em papel
CREATE ROLE phi_clinical_user;
CREATE ROLE phi_billing_user;
CREATE ROLE phi_admin_user;

GRANT SELECT ON phi_clinical_view TO phi_clinical_user;
GRANT SELECT ON phi_billing_view TO phi_billing_user;
GRANT SELECT ON protected_health_info TO phi_admin_user;

-- HIPAA Audit Trail (obrigatorio)
CREATE TABLE hipaa_audit_trail (
    audit_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    user_name VARCHAR(128),
    user_role VARCHAR(50),
    source_ip INET,
    action VARCHAR(50),
    phi_id UUID,
    table_accessed VARCHAR(256),
    fields_accessed TEXT[],
    justification VARCHAR(255),
    access_duration_ms INT
);

-- Trigger de auditoria para PHI
CREATE OR REPLACE FUNCTION hipaa_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO hipaa_audit_trail (
        user_name, user_role, source_ip, action, phi_id,
        table_accessed, fields_accessed
    )
    VALUES (
        current_user,
        (SELECT string_agg(role, ', ') FROM pg_roles WHERE pg_has_role(current_user, role, 'member')),
        inet_client_addr(),
        TG_OP,
        CASE WHEN TG_OP != 'DELETE' THEN NEW.phi_id ELSE OLD.phi_id END,
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        CASE TG_OP
            WHEN 'INSERT' THEN ARRAY(SELECT jsonb_object_keys(to_jsonb(NEW)))
            WHEN 'UPDATE' THEN ARRAY(SELECT jsonb_object_keys(to_jsonb(NEW)))
            WHEN 'DELETE' THEN ARRAY(SELECT jsonb_object_keys(to_jsonb(OLD)))
        END
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Relatorio de acesso HIPAA
SELECT 
    date_trunc('day', event_time) AS day,
    user_name,
    user_role,
    action,
    COUNT(*) AS access_count,
    array_agg(DISTINCT table_accessed) AS tables_accessed
FROM hipaa_audit_trail
WHERE event_time > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', event_time), user_name, user_role, action
ORDER BY day DESC, access_count DESC;
```

## SOC 2 Controls

### Visao Geral do SOC 2

SOC 2 (System and Organization Controls 2) e um framework de auditoria baseado em Cinco Trust Service Criteria: Seguranca, Disponibilidade, Integridade de Processamento, Confidencialidade e Privacidade.

### Controles para Databases

```sql
-- SOC 2 Trust Service Criteria para Databases

-- 1. Seguranca (CC6.1 - Logical and Physical Access Controls)
CREATE TABLE soc2_access_controls (
    control_id SERIAL PRIMARY KEY,
    control_name VARCHAR(255),
    trust_criteria VARCHAR(50),
    description TEXT,
    implementation_status VARCHAR(20),
    last_tested DATE,
    next_test_date DATE,
    evidence TEXT
);

INSERT INTO soc2_access_controls VALUES
(1, 'Multi-Factor Authentication', 'CC6.1',
 'MFA enabled for all database administrative access', 'IMPLEMENTED', CURRENT_DATE - 30, CURRENT_DATE + 90,
 'MFA enrollment records, login logs showing MFA usage'),
(2, 'Role-Based Access Control', 'CC6.1',
 'Database access controlled by RBAC with least privilege', 'IMPLEMENTED', CURRENT_DATE - 60, CURRENT_DATE + 90,
 'Role definitions, GRANT statements, access review records'),
(3, 'Encryption at Rest', 'CC6.1',
 'All sensitive data encrypted using AES-256', 'IMPLEMENTED', CURRENT_DATE - 90, CURRENT_DATE + 180,
 'Encryption configuration, key management records'),
(4, 'Encryption in Transit', 'CC6.1',
 'TLS 1.3 enforced for all database connections', 'IMPLEMENTED', CURRENT_DATE - 30, CURRENT_DATE + 90,
 'SSL certificate records, pg_hba.conf configuration'),
(5, 'Network Segmentation', 'CC6.1',
 'Databases isolated in dedicated network segment', 'IMPLEMENTED', CURRENT_DATE - 180, CURRENT_DATE + 365,
 'Network diagrams, firewall rules, VPC configuration');

-- 2. Disponibilidade (A1.1 - Capacity Planning)
CREATE TABLE availability_monitoring (
    metric_id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100),
    target_value DECIMAL(10,2),
    actual_value DECIMAL(10,2),
    measurement_date DATE,
    sla_compliant BOOLEAN
);

-- 3. Integridade de Processamento (PI1.1 - Data Validation)
-- Implementada via constraints e triggers

-- 4. Confidencialidade (C1.1 - Confidential Information)
-- Implementada via criptografia e access controls

-- 5. Privacidade (P1-P8 - Privacy)
-- Implementada via LGPD/GDPR controls acima
```

## ISO 27001 Annex A

### Controles de Seguranca de Informacao

```sql
-- ISO 27001:2022 Annex A - Controles de seguranca de informacao
-- Aplicacao especifica para databases

-- A.8.24 - Uso de criptografia
-- A.8.3 - Controle de acesso restrito
-- A.8.5 - Autenticacao segura
-- A.8.15 - Logging
-- A.8.16 - Atividades de monitoramento

-- Implementacao consolidada

CREATE TABLE iso27001_controls (
    control_id VARCHAR(10) PRIMARY KEY,
    control_name VARCHAR(255),
    category VARCHAR(100),
    description TEXT,
    implementation_details TEXT,
    responsible_party VARCHAR(255),
    review_frequency VARCHAR(50),
    last_review DATE,
    status VARCHAR(20)
);

INSERT INTO iso27001_controls VALUES
('A.8.24', 'Uso de criptografia', 'Organizational',
 'Dados sensiveis criptografados at-rest e in-transit',
 'AES-256 at-rest via pgcrypto, TLS 1.3 in-transit',
 'DBA Team', 'QUARTERLY', CURRENT_DATE - 45, 'IMPLEMENTED'),
('A.8.3', 'Controle de acesso restrito', 'People',
 'Acesso a databases controlado por RBAC com least privilege',
 'Roles hierarchy, GRANT/REVOKE, RLS policies',
 'Security Team', 'MONTHLY', CURRENT_DATE - 15, 'IMPLEMENTED'),
('A.8.5', 'Autenticacao segura', 'People',
 'MFA para acesso administrativo, senhas fortes',
 'FIDO2/WebAuthn, bcrypt hashing, password policy',
 'Security Team', 'MONTHLY', CURRENT_DATE - 10, 'IMPLEMENTED'),
('A.8.15', 'Logging', 'Technological',
 'Logs de auditoria completos e preservados',
 'pgaudit, custom audit tables, 1-year retention',
 'DBA Team', 'WEEKLY', CURRENT_DATE - 3, 'IMPLEMENTED'),
('A.8.16', 'Atividades de monitoramento', 'Technological',
 'Monitoramento em tempo real de atividades suspeitas',
 'DAM solution, SIEM integration, automated alerts',
 'SOC Team', 'DAILY', CURRENT_DATE - 1, 'IMPLEMENTED');

-- Verificar conformidade ISO 27001
SELECT 
    control_id,
    control_name,
    status,
    last_review,
    EXTRACT(DAY FROM CURRENT_DATE - last_review) AS days_since_review,
    CASE 
        WHEN last_review < CURRENT_DATE - INTERVAL '90 days' THEN 'WARNING: Review overdue'
        ELSE 'OK'
    END AS review_status
FROM iso27001_controls
ORDER BY control_id;
```

## FIPS 140-3 para Cryptographic Modules

### Visao Geral do FIPS 140-3

O Federal Information Processing Standard (FIPS) 140-3 e o padrao americano para modulos criptograficos. Organizacoes que processam dados do governo americano ou dados sensiveis devem usar modulos certificados FIPS 140-3.

### Implementacao

```sql
-- FIPS 140-3 requer:
-- 1. Algoritmos criptograficos aprovados (AES, SHA-256, RSA)
-- 2. Gerenciamento seguro de chaves
-- 3. Modulos de hardware (HSM) para operacoes criticas
-- 4. Validacao formal do modulo criptografico

-- Verificar se o PostgreSQL esta usando algoritmos FIPS-compliant
-- Configurar OpenSSL para modo FIPS

-- postgresql.conf:
-- ssl = on
-- ssl_ciphers = 'FIPS:!aNULL:!MD5'
-- ssl_min_protocol_version = 'TLSv1.3'

-- Verificar algoritmos em uso
SELECT 
    current_setting('ssl_cipher') AS cipher,
    current_setting('ssl_version') AS protocol,
    CASE 
        WHEN current_setting('ssl_version') = 'TLSv1.3' THEN 'FIPS-COMPLIANT'
        WHEN current_setting('ssl_version') = 'TLSv1.2' THEN 'CONDITIONALLY-COMPLIANT'
        ELSE 'NON-COMPLIANT'
    END AS fips_status;

-- Para criptografia at-rest, usar apenas algoritmos FIPS-approved:
-- AES-128, AES-192, AES-256 (modos CBC, GCM, CTR)
-- SHA-256, SHA-384, SHA-512
-- RSA 2048+, ECDSA P-256+

-- Gerenciamento de chaves FIPS-compliant
CREATE TABLE fips_key_management (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_label VARCHAR(255) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    key_length INT NOT NULL,
    key_type VARCHAR(50) NOT NULL,
    hsm_slot INT,
    exportable BOOLEAN DEFAULT FALSE,
    fips_certified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    rotation_policy VARCHAR(50) DEFAULT 'ANNUAL'
);

-- Verificar conformidade FIPS
SELECT 
    key_label,
    algorithm,
    key_length,
    fips_certified,
    expires_at,
    CASE 
        WHEN NOT fips_certified THEN 'CRITICAL: Non-FIPS key'
        WHEN expires_at < NOW() THEN 'CRITICAL: Expired key'
        WHEN expires_at < NOW() + INTERVAL '30 days' THEN 'WARNING: Expiring soon'
        ELSE 'OK'
    END AS compliance_status
FROM fips_key_management
WHERE exportable = FALSE
ORDER BY fips_certified, expires_at;
```

## Data Classification Frameworks

### Classificacao de Dados

```sql
-- Framework de classificacao de dados para compliance

CREATE TABLE data_classification_levels (
    level_id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL,
    description TEXT,
    examples TEXT,
    security_requirements TEXT,
    encryption_required BOOLEAN,
    audit_level VARCHAR(20),
    retention_max_days INT,
    access_approval_required BOOLEAN
);

INSERT INTO data_classification_levels VALUES
(1, 'PUBLIC', 
 'Dados publicamente disponiveis', 
 'Marketing materials, public documentation',
 'Basic access controls', FALSE, 'BASIC', 3650, FALSE),
(2, 'INTERNAL',
 'Dados para uso interno da organizacao',
 'Internal procedures, organizational charts',
 'Authentication required', FALSE, 'STANDARD', 1825, FALSE),
(3, 'CONFIDENTIAL',
 'Dados sensiveis que causariam dano se expostos',
 'Business plans, financial data, employee records',
 'Encryption at-rest and in-transit, RBAC', TRUE, 'ENHANCED', 1095, TRUE),
(4, 'RESTRICTED',
 'Dados altamente sensiveis sob regulamentacao',
 'PII, PHI, payment cards, SSN, credentials',
 'Strong encryption, MFA, DLP, audit trail', TRUE, 'COMPREHENSIVE', 365, TRUE),
(5, 'TOP SECRET',
 'Dados cuja exposicao causaria dano catastrofico',
 'Encryption keys, master passwords, trade secrets',
 'HSM storage, zero-trust access, real-time monitoring', TRUE, 'MAXIMUM', 365, TRUE);

-- Aplicar classificacao a tabelas de database
CREATE TABLE table_classification (
    table_id SERIAL PRIMARY KEY,
    schema_name VARCHAR(128),
    table_name VARCHAR(128),
    classification_level INT REFERENCES data_classification_levels(level_id),
    data_owner VARCHAR(255),
    last_reviewed DATE,
    review_frequency VARCHAR(50),
    compliance_requirements TEXT[]
);

-- Verificar tabelas nao classificadas
SELECT 
    t.table_schema,
    t.table_name,
    COALESCE(tc.classification_level, 0) AS classification,
    CASE 
        WHEN tc.classification_level IS NULL THEN 'UNCLASSIFIED: Must be classified'
        WHEN tc.classification_level >= 4 THEN 'RESTRICTED: Maximum controls required'
        ELSE 'OK'
    END AS status
FROM information_schema.tables t
LEFT JOIN table_classification tc 
    ON t.table_schema = tc.schema_name 
    AND t.table_name = tc.table_name
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY tc.classification_level DESC NULLS LAST;

-- Relatorio de conformidade por classificacao
SELECT 
    dcl.level_name,
    COUNT(tc.table_id) AS table_count,
    SUM(CASE WHEN tc.classification_level >= 4 THEN 1 ELSE 0 END) AS restricted_tables,
    SUM(CASE WHEN tc.last_reviewed < CURRENT_DATE - INTERVAL '90 days' THEN 1 ELSE 0 END) AS overdue_reviews
FROM data_classification_levels dcl
LEFT JOIN table_classification tc ON dcl.level_id = tc.classification_level
GROUP BY dcl.level_name
ORDER BY dcl.level_id;
```

## Encryption Key Management Compliance

### Gerenciamento de Chaves

```sql
-- Gerenciamento de chaves conforme NIST SP 800-57

-- Ciclo de vida da chave
CREATE TABLE key_lifecycle (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name VARCHAR(255) NOT NULL,
    key_state VARCHAR(20) NOT NULL,
    key_type VARCHAR(50) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    key_length INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    deactivated_at TIMESTAMPTZ,
    destroyed_at TIMESTAMPTZ,
    created_by VARCHAR(128) NOT NULL,
    approved_by VARCHAR(128),
    justification TEXT
);

-- Estados da chave: PRE_ACTIVE -> ACTIVE -> SUSPENDED -> DEACTIVE -> DESTROYED
ALTER TABLE key_lifecycle ADD CONSTRAINT valid_state_transition 
CHECK (key_state IN ('PRE_ACTIVE', 'ACTIVE', 'SUSPENDED', 'DEACTIVE', 'DESTROYED'));

-- Funcao para transicao segura de estado
CREATE OR REPLACE FUNCTION transition_key_state(
    p_key_id UUID,
    p_new_state VARCHAR,
    p_actor VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_current_state VARCHAR;
    v_valid_transitions TEXT[];
BEGIN
    SELECT key_state INTO v_current_state
    FROM key_lifecycle WHERE key_id = p_key_id;
    
    -- Definir transicoes validas
    v_valid_transitions := CASE v_current_state
        WHEN 'PRE_ACTIVE' THEN ARRAY['ACTIVE', 'DESTROYED']
        WHEN 'ACTIVE' THEN ARRAY['SUSPENDED', 'DEACTIVE', 'DESTROYED']
        WHEN 'SUSPENDED' THEN ARRAY['ACTIVE', 'DEACTIVE', 'DESTROYED']
        WHEN 'DEACTIVE' THEN ARRAY['DESTROYED']
        ELSE ARRAY[]::TEXT[]
    END;
    
    -- Verificar se transicao e valida
    IF NOT (p_new_state = ANY(v_valid_transitions)) THEN
        RAISE EXCEPTION 'Invalid state transition: % -> %', v_current_state, p_new_state;
    END IF;
    
    -- Atualizar estado
    UPDATE key_lifecycle SET
        key_state = p_new_state,
        activated_at = CASE WHEN p_new_state = 'ACTIVE' THEN NOW() ELSE activated_at END,
        suspended_at = CASE WHEN p_new_state = 'SUSPENDED' THEN NOW() ELSE suspended_at END,
        deactivated_at = CASE WHEN p_new_state = 'DEACTIVE' THEN NOW() ELSE deactivated_at END,
        destroyed_at = CASE WHEN p_new_state = 'DESTROYED' THEN NOW() ELSE destroyed_at END
    WHERE key_id = p_key_id;
    
    -- Log de transicao
    INSERT INTO key_state_transitions (key_id, from_state, to_state, transitioned_by, transitioned_at)
    VALUES (p_key_id, v_current_state, p_new_state, p_actor, NOW());
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
```

## Data Retention Policies

### Politicas de Retencao

```sql
-- Implementacao de politicas de retencao conforme regulamentacoes

CREATE TABLE data_retention_policies (
    policy_id SERIAL PRIMARY KEY,
    data_category VARCHAR(100),
    classification_level INT,
    retention_days INT NOT NULL,
    legal_basis VARCHAR(100),
    regulations TEXT[],
    auto_delete BOOLEAN DEFAULT TRUE,
    archive_before_delete BOOLEAN DEFAULT TRUE,
    approval_required BOOLEAN DEFAULT FALSE
);

INSERT INTO data_retention_policies VALUES
(1, 'Personal Data (LGPD)', 4, 365, 'CONSENT', ARRAY['LGPD'], TRUE, TRUE, FALSE),
(2, 'Personal Data (GDPR)', 4, 730, 'CONSENT', ARRAY['GDPR'], TRUE, TRUE, FALSE),
(3, 'Financial Records', 3, 2555, 'LEGAL_OBLIGATION', ARRAY['PCI DSS', 'SOX'], TRUE, TRUE, TRUE),
(4, 'Audit Logs', 5, 365, 'LEGAL_OBLIGATION', ARRAY['PCI DSS', 'SOC 2', 'ISO 27001'], TRUE, FALSE, FALSE),
(5, 'Health Records (HIPAA)', 4, 2190, 'LEGAL_OBLIGATION', ARRAY['HIPAA'], FALSE, FALSE, TRUE),
(6, 'Marketing Data', 2, 365, 'LEGITIMATE_INTEREST', ARRAY['LGPD'], TRUE, FALSE, FALSE);

-- Funcao de cleanup automatico
CREATE OR REPLACE FUNCTION enforce_data_retention()
RETURNS INT AS $$
DECLARE
    v_policy RECORD;
    v_deleted_count INT := 0;
    v_total_deleted INT := 0;
BEGIN
    FOR v_policy IN SELECT * FROM data_retention_policies WHERE auto_delete = TRUE
    LOOP
        -- Deletar dados expirados
        EXECUTE format(
            'DELETE FROM data_registry 
             WHERE data_category = %L 
             AND created_at < NOW() - INTERVAL ''%s days''
             AND classification_level = %s',
            v_policy.data_category,
            v_policy.retention_days,
            v_policy.classification_level
        );
        
        GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
        v_total_deleted := v_total_deleted + v_deleted_count;
        
        -- Log da limpeza
        INSERT INTO retention_cleanup_log (policy_id, records_deleted, cleanup_date)
        VALUES (v_policy.policy_id, v_deleted_count, NOW());
    END LOOP;
    
    RETURN v_total_total_deleted;
END;
$$ LANGUAGE plpgsql;

-- Verificar dados proximos do vencimento
SELECT 
    drp.data_category,
    drp.retention_days,
    COUNT(dr.data_id) AS total_records,
    MIN(dr.created_at) AS oldest_record,
    MAX(dr.created_at) AS newest_record,
    EXTRACT(DAY FROM MAX(dr.created_at) - NOW() + (drp.retention_days || ' days')::INTERVAL) AS days_until_expiry
FROM data_retention_policies drp
JOIN data_registry dr ON drp.data_category = dr.data_category
WHERE drp.auto_delete = TRUE
GROUP BY drp.data_category, drp.retention_days
ORDER BY days_until_expiry;
```

## Cross-Border Data Transfer

### Transferencia Internacional de Dados

```sql
-- Regras para transferencia internacional de dados

CREATE TABLE cross_border_transfer_rules (
    rule_id SERIAL PRIMARY KEY,
    source_country VARCHAR(2) NOT NULL,
    destination_country VARCHAR(2) NOT NULL,
    transfer_mechanism VARCHAR(100),
    adequacy_decision BOOLEAN,
    standard_contractual_clauses BOOLEAN,
    binding_corporate_rules BOOLEAN,
    additional_safeguards TEXT,
    regulations TEXT[],
    requires_dpia BOOLEAN DEFAULT FALSE
);

INSERT INTO cross_border_transfer_rules VALUES
(1, 'BR', 'EU', 'Adequacy Decision', TRUE, FALSE, FALSE,
 'None required - EU adequacy decision for Brazil pending',
 ARRAY['LGPD', 'GDPR'], FALSE),
(2, 'BR', 'US', 'Standard Contractual Clauses', FALSE, TRUE, FALSE,
 'SCC + supplementary measures required',
 ARRAY['LGPD'], TRUE),
(3, 'EU', 'US', 'Data Privacy Framework', TRUE, FALSE, FALSE,
 'EU-US Data Privacy Framework certified recipients',
 ARRAY['GDPR'], FALSE),
(4, 'BR', 'CN', 'Explicit Consent', FALSE, FALSE, FALSE,
 'Additional encryption and access controls required',
 ARRAY['LGPD'], TRUE);

-- Verificar transfers internacionais em andamento
SELECT 
    cbr.source_country,
    cbr.destination_country,
    cbr.transfer_mechanism,
    cbr.adequacy_decision,
    cbr.standard_contractual_clauses,
    cbr.requires_dpia,
    CASE 
        WHEN NOT cbr.adequacy_decision AND NOT cbr.standard_contractual_clauses 
        THEN 'CRITICAL: No transfer mechanism'
        WHEN cbr.requires_dpia 
        THEN 'WARNING: DPIA required'
        ELSE 'OK'
    END AS compliance_status
FROM cross_border_transfer_rules cbr
ORDER BY cbr.source_country, cbr.destination_country;
```

## Compliance Automation

### Automacao de Compliance

```sql
-- Automacao de verificacoes de compliance

CREATE TABLE compliance_checks (
    check_id SERIAL PRIMARY KEY,
    check_name VARCHAR(255),
    regulation VARCHAR(50),
    check_query TEXT,
    expected_result TEXT,
    severity VARCHAR(20),
    frequency VARCHAR(50),
    last_run TIMESTAMPTZ,
    last_result VARCHAR(20),
    last_details TEXT
);

INSERT INTO compliance_checks VALUES
(1, 'PCI: All card data encrypted', 'PCI DSS',
 'SELECT COUNT(*) FROM payment_cards WHERE card_number_encrypted IS NULL',
 '0', 'CRITICAL', 'DAILY'),
(2, 'LGPD: Consent records exist', 'LGPD',
 'SELECT COUNT(*) FROM personal_data_protected WHERE consent_given = FALSE AND consent_date IS NULL',
 '0', 'HIGH', 'DAILY'),
(3, 'HIPAA: PHI audit trail active', 'HIPAA',
 'SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_name = ''hipaa_audit_trigger''',
 '1', 'CRITICAL', 'WEEKLY'),
(4, 'SOC2: MFA enabled for admins', 'SOC 2',
 'SELECT COUNT(*) FROM users WHERE role = ''admin'' AND mfa_enabled = FALSE',
 '0', 'CRITICAL', 'DAILY'),
(5, 'ISO27001: Backup tested', 'ISO 27001',
 'SELECT COUNT(*) FROM backup_schedule WHERE last_test_date < CURRENT_DATE - INTERVAL ''30 days''',
 '0', 'WEEKLY');

-- Executar verificacoes de compliance
CREATE OR REPLACE FUNCTION run_compliance_checks()
RETURNS TABLE(check_name VARCHAR, regulation VARCHAR, result VARCHAR, status VARCHAR) AS $$
DECLARE
    v_check RECORD;
    v_result TEXT;
BEGIN
    FOR v_check IN SELECT * FROM compliance_checks ORDER BY severity DESC
    LOOP
        BEGIN
            EXECUTE v_check.check_query INTO v_result;
            
            compliance_checks.check_name := v_check.check_name;
            compliance_checks.regulation := v_check.regulation;
            compliance_checks.result := v_result;
            compliance_checks.status := CASE 
                WHEN v_result = v_check.expected_result THEN 'PASS'
                ELSE 'FAIL'
            END;
            
            -- Atualizar resultado
            UPDATE compliance_checks SET
                last_run = NOW(),
                last_result = compliance_checks.status,
                last_details = v_result
            WHERE check_id = v_check.check_id;
            
            -- Alertar se falha critica
            IF compliance_checks.status = 'FAIL' AND v_check.severity = 'CRITICAL' THEN
                PERFORM pg_notify('compliance_alert',
                    FORMAT('COMPLIANCE FAILURE: %s (%s) - Expected: %s, Got: %s',
                           v_check.check_name, v_check.regulation, v_check.expected_result, v_result));
            END IF;
            
            RETURN NEXT;
        EXCEPTION WHEN OTHERS THEN
            compliance_checks.check_name := v_check.check_name;
            compliance_checks.regulation := v_check.regulation;
            compliance_checks.result := 'ERROR: ' || SQLERRM;
            compliance_checks.status := 'ERROR';
            RETURN NEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Dashboard de compliance
SELECT 
    regulation,
    COUNT(CASE WHEN last_result = 'PASS' THEN 1 END) AS passed,
    COUNT(CASE WHEN last_result = 'FAIL' THEN 1 END) AS failed,
    COUNT(CASE WHEN last_result IS NULL THEN 1 END) AS not_tested,
    ROUND(COUNT(CASE WHEN last_result = 'PASS' THEN 1 END)::DECIMAL / 
          NULLIF(COUNT(*), 0) * 100, 1) AS compliance_rate
FROM compliance_checks
GROUP BY regulation
ORDER BY compliance_rate;
```

## Audit Preparation

### Preparacao para Auditorias

```sql
-- Checklist de preparacao para auditoria de compliance

CREATE TABLE audit_preparation (
    preparation_id SERIAL PRIMARY KEY,
    audit_type VARCHAR(100),
    scheduled_date DATE,
    auditor VARCHAR(255),
    scope TEXT,
    documents_required TEXT[],
    status VARCHAR(20),
    prepared_by VARCHAR(255),
    prepared_at TIMESTAMPTZ,
    notes TEXT
);

INSERT INTO audit_preparation VALUES
(1, 'PCI DSS QSA Audit', CURRENT_DATE + 60, 'Deloitte',
 'All systems that process, store, or transmit cardholder data',
 ARRAY['Network diagrams', 'Access control lists', 'Encryption configuration',
        'Audit logs (12 months)', 'Incident response plan', 'Vulnerability scan reports',
        'Penetration test results', 'Change management records'],
 'IN_PROGRESS', 'Security Team', CURRENT_DATE - 30, NULL),
(2, 'SOC 2 Type II', CURRENT_DATE + 90, 'KPMG',
 'All Trust Service Criteria',
 ARRAY['Control descriptions', 'Evidence of implementation',
        'Management assertions', 'Complementary user entity controls',
        'System descriptions', 'Risk assessment'],
 'PLANNING', 'Compliance Team', NULL, NULL),
(3, 'ISO 27001 Recertification', CURRENT_DATE + 120, 'BSI',
 'ISMS scope',
 ARRAY['ISMS documentation', 'Risk treatment plan',
        'Internal audit reports', 'Management review minutes',
        'Corrective action records', 'Competence records'],
 'NOT_STARTED', 'Quality Team', NULL, NULL);

-- Relatorio de prontidao para auditoria
SELECT 
    ap.audit_type,
    ap.scheduled_date,
    ap.auditor,
    ap.status,
    EXTRACT(DAY FROM ap.scheduled_date - CURRENT_DATE) AS days_until_audit,
    ap.documents_required,
    CASE 
        WHEN ap.status = 'READY' THEN 'GREEN'
        WHEN ap.status = 'IN_PROGRESS' THEN 'YELLOW'
        ELSE 'RED'
    END AS readiness_status
FROM audit_preparation ap
WHERE ap.scheduled_date > CURRENT_DATE
ORDER BY ap.scheduled_date;
```

## Resumo

Compliance nao e apenas uma questao legal — e uma estrategia de seguranca que protege tanto a organizacao quanto seus clientes. Cada regulamentacao (PCI DSS, LGPD, GDPR, HIPAA, SOC 2, ISO 27001, FIPS 140-3) traz requisitos especificos que se complementam para criar uma postura de seguranca robusta.

Os principios fundamentais que permeiam todas as regulamentacoes sao:

**Criptografia obrigatoria.** Dados sensiveis devem ser criptografados tanto em repouso quanto em transito. Chaves de criptografia devem ser gerenciadas em HSMs com rotacao regular.

**Controle de acesso granular.** Least privilege, RBAC, MFA e monitoring sao requisitos comuns a todas as regulamentacoes. Acesso a dados sensiveis deve ser rastreavel e auditavel.

**Retencao minima.** Armazenar apenas dados estritamente necessarios pelo tempo minimamente necessario. Politicas de retencao devem ser documentadas e automatizadas.

**Monitoramento continuo.** Audit trails completos, deteccao de anomalias e alertas em tempo real sao essenciais para atender requisitos de SOC 2, ISO 27001 e PCI DSS.

**Preparacao para auditorias.** Documentacao organizada, evidencias de implementacao e testes regulares sao chave para passar em auditorias com sucesso.

A automacao de compliance, implementada via queries SQL que verificam continuamente a conformidade, e a forma mais eficaz de manter a conformidade ao longo do tempo. Cada verificacao automatizada reduz o risco de nao conformidade e facilita a preparacao para auditorias.

## Estudo de Caso: Implementacao Completa de PCI DSS em PostgreSQL

### Arquitetura de Seguranca PCI DSS

```sql
-- Implementacao completa de PCI DSS para um ambiente PostgreSQL
-- que processa dados de cartao de credito

-- PASSO 1: Segmentacao de rede
-- Configurar PostgreSQL para escutar apenas em interfaces internas
-- postgresql.conf:
-- listen_addresses = '10.0.30.10'  -- Apenas VLAN de databases

-- PASSO 2: Autenticacao forte
-- pg_hba.conf configurado para exigir SSL e certificados
-- hostssl card_db app_user 10.0.20.0/24 cert clientcert=verify-full
-- hostssl card_db dba_user 10.0.10.0/24 scram-sha-256

-- PASSO 3: Criptografia de dados de cartao
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabela com criptografia em multiplas camadas
CREATE TABLE cardholder_data (
    chd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Dados criptografados com chave de dados (data encryption key)
    card_number_encrypted BYTEA NOT NULL,
    card_number_last_four CHAR(4) NOT NULL,
    card_number_masked VARCHAR(19) NOT NULL,
    expiration_month_encrypted BYTEA NOT NULL,
    expiration_year_encrypted BYTEA NOT NULL,
    cvv_encrypted BYTEA NOT NULL,
    
    -- Dados pseudonimizados para referencia
    cardholder_name_hash VARCHAR(64) NOT NULL,
    cardholder_name_masked VARCHAR(255) NOT NULL,
    
    -- Metadados obrigatorios
    data_encrypted_with_key_id UUID NOT NULL,
    encryption_algorithm VARCHAR(50) DEFAULT 'AES-256-GCM',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Controle de acesso
    last_accessed_by VARCHAR(128),
    last_accessed_at TIMESTAMPTZ,
    access_count INT DEFAULT 0
);

-- Funcao para inserir dados de cartao com validacao
CREATE OR REPLACE FUNCTION store_cardholder_data(
    p_card_number VARCHAR,
    p_expiration_month VARCHAR,
    p_expiration_year VARCHAR,
    p_cvv VARCHAR,
    p_cardholder_name VARCHAR
)
RETURNS UUID AS $$
DECLARE
    v_chd_id UUID;
    v_data_key_id UUID;
    v_data_key TEXT;
BEGIN
    -- Validar formato do cartao (Luhn algorithm check simplificado)
    IF LENGTH(p_card_number) NOT BETWEEN 13 AND 19 THEN
        RAISE EXCEPTION 'Invalid card number length';
    END IF;
    
    IF p_card_number !~ '^[0-9]+$' THEN
        RAISE EXCEPTION 'Card number must contain only digits';
    END IF;
    
    IF LENGTH(p_cvv) NOT BETWEEN 3 AND 4 THEN
        RAISE EXCEPTION 'Invalid CVV length';
    END IF;
    
    -- Obter chave de dados ativa
    SELECT key_id, pgp_sym_decrypt(key_material_encrypted, current_setting('app.master_key'))
    INTO v_data_key_id, v_data_key
    FROM encryption_key_management
    WHERE key_name = 'PCI_DATA_ENCRYPTION'
    AND is_active = TRUE
    AND expires_at > NOW();
    
    -- Inserir dados criptografados
    INSERT INTO cardholder_data (
        card_number_encrypted,
        card_number_last_four,
        card_number_masked,
        expiration_month_encrypted,
        expiration_year_encrypted,
        cvv_encrypted,
        cardholder_name_hash,
        cardholder_name_masked,
        data_encrypted_with_key_id
    )
    VALUES (
        pgp_sym_encrypt(p_card_number, v_data_key),
        RIGHT(p_card_number, 4),
        '****-****-****-' || RIGHT(p_card_number, 4),
        pgp_sym_encrypt(p_expiration_month, v_data_key),
        pgp_sym_encrypt(p_expiration_year, v_data_key),
        pgp_sym_encrypt(p_cvv, v_data_key),
        encode(sha256(p_cardholder_name::bytea), 'hex'),
        p_cardholder_name,
        v_data_key_id
    )
    RETURNING chd_id INTO v_chd_id;
    
    -- Log de criacao (obrigatorio PCI DSS)
    INSERT INTO pci_data_access_log (chd_id, action, performed_by, performed_at)
    VALUES (v_chd_id, 'CREATE', current_user, NOW());
    
    RETURN v_chd_id;
END;
$$ LANGUAGE plpgsql;

-- Funcao para descriptografar (apenas para processamento autorizado)
CREATE OR REPLACE FUNCTION retrieve_cardholder_data(
    p_chd_id UUID,
    p_requester VARCHAR,
    p_purpose VARCHAR
)
RETURNS TABLE(
    card_number VARCHAR,
    expiration_month VARCHAR,
    expiration_year VARCHAR,
    cardholder_name VARCHAR
) AS $$
DECLARE
    v_data_key TEXT;
    v_access_allowed BOOLEAN := FALSE;
BEGIN
    -- Verificar se solicitacao e autorizada
    IF p_purpose NOT IN ('PROCESSING', 'VERIFICATION', 'REFUND', 'DISPUTE') THEN
        RAISE EXCEPTION 'Unauthorized purpose: %', p_purpose;
    END IF;
    
    -- Obter chave de dados
    SELECT pgp_sym_decrypt(key_material_encrypted, current_setting('app.master_key'))
    INTO v_data_key
    FROM encryption_key_management
    WHERE key_id = (SELECT data_encrypted_with_key_id FROM cardholder_data WHERE chd_id = p_chd_id)
    AND is_active = TRUE;
    
    -- Log de acesso (obrigatorio PCI DSS)
    INSERT INTO pci_data_access_log (chd_id, action, performed_by, performed_at, purpose)
    VALUES (p_chd_id, 'READ', p_requester, NOW(), p_purpose);
    
    -- Retornar dados descriptografados
    RETURN QUERY
    SELECT 
        pgp_sym_decrypt(chd.card_number_encrypted, v_data_key),
        pgp_sym_decrypt(chd.expiration_month_encrypted, v_data_key),
        pgp_sym_decrypt(chd.expiration_year_encrypted, v_data_key),
        chd.cardholder_name_masked
    FROM cardholder_data chd
    WHERE chd.chd_id = p_chd_id;
    
    -- Atualizar estatisticas de acesso
    UPDATE cardholder_data
    SET last_accessed_by = p_requester,
        last_accessed_at = NOW(),
        access_count = access_count + 1
    WHERE chd_id = p_chd_id;
END;
$$ LANGUAGE plpgsql;
```

### Relatorios de Conformidade PCI DSS

```sql
-- Relatorio 1: Status de criptografia
SELECT 
    'Card Data Encryption' AS control,
    COUNT(*) AS total_records,
    COUNT(CASE WHEN card_number_encrypted IS NOT NULL THEN 1 END) AS encrypted,
    COUNT(CASE WHEN card_number_encrypted IS NULL THEN 1 END) AS unencrypted,
    ROUND(COUNT(CASE WHEN card_number_encrypted IS NOT NULL THEN 1 END)::DECIMAL / 
          NULLIF(COUNT(*), 0) * 100, 1) AS encryption_rate
FROM cardholder_data
WHERE deleted_at IS NULL;

-- Relatorio 2: Acesso a dados de cartao (ultimos 30 dias)
SELECT 
    pal.performed_by,
    COUNT(*) AS access_count,
    COUNT(DISTINCT pal.chd_id) AS distinct_cards_accessed,
    MIN(pal.performed_at) AS first_access,
    MAX(pal.performed_at) AS last_access,
    array_agg(DISTINCT pal.purpose) AS purposes
FROM pci_data_access_log pal
WHERE pal.performed_at > NOW() - INTERVAL '30 days'
AND pal.action = 'READ'
GROUP BY pal.performed_by
ORDER BY access_count DESC;

-- Relatorio 3: Chaves proximas do vencimento
SELECT 
    key_name,
    key_version,
    expires_at,
    EXTRACT(DAY FROM expires_at - NOW()) AS days_until_expiry,
    CASE 
        WHEN expires_at < NOW() THEN 'EXPIRED: Immediate rotation required'
        WHEN expires_at < NOW() + INTERVAL '30 days' THEN 'WARNING: Plan rotation soon'
        ELSE 'OK'
    END AS status
FROM encryption_key_management
WHERE key_name LIKE 'PCI_%'
AND is_active = TRUE
ORDER BY expires_at;

-- Relatorio 4: Atividade suspeita
SELECT 
    pal.performed_by,
    pal.performed_at,
    pal.purpose,
    COUNT(*) OVER (PARTITION BY pal.performed_by) AS total_access,
    CASE 
        WHEN COUNT(*) OVER (PARTITION BY pal.performed_by) > 100 THEN 'HIGH: Excessive access'
        WHEN pal.performed_at BETWEEN '02:00' AND '06:00' THEN 'MEDIUM: Unusual hour'
        ELSE 'NORMAL'
    END AS risk_indicator
FROM pci_data_access_log pal
WHERE pal.performed_at > NOW() - INTERVAL '24 hours'
ORDER BY pal.performed_at DESC;
```

## Estudo de Caso: LGPD Completa para E-commerce

### Implementacao LGPD para Plataforma de E-commerce

```sql
-- Implementacao completa de LGPD para e-commerce brasileiro

-- 1. Registro de atividades de tratamento (Art. 37)
CREATE TABLE lgpd_treatment_registry (
    registry_id SERIAL PRIMARY KEY,
    activity_name VARCHAR(255) NOT NULL,
    data_categories TEXT[] NOT NULL,
    legal_basis VARCHAR(100) NOT NULL,
    purpose TEXT NOT NULL,
    data_controller VARCHAR(255) NOT NULL,
    data_processor VARCHAR(255),
    retention_period_days INT NOT NULL,
    cross_border_transfer BOOLEAN DEFAULT FALSE,
    destination_countries TEXT[],
    security_measures TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_reviewed DATE,
    dpo_approved BOOLEAN DEFAULT FALSE
);

INSERT INTO lgpd_treatment_registry VALUES
(1, 'Cadastro de clientes', 
 ARRAY['nome', 'email', 'cpf', 'telefone', 'endereco'],
 'CONSENT', 'Execucao de contrato de compra e venda',
 'Empresa X Ltda', 'AWS (hosting)', 1825, FALSE, NULL,
 ARRAY['Criptografia AES-256', 'MFA', 'RBAC'],
 NOW(), CURRENT_DATE - 30, TRUE),
(2, 'Processamento de pagamentos',
 ARRAY['dados de cartao', 'endereco de cobranca'],
 'LEGAL_OBLIGATION', 'Cumprimento de obrigacao legal e regulatoria',
 'Empresa X Ltda', 'Stripe (processamento)', 2555, TRUE, ARRAY['US'],
 ARRAY['Tokenizacao PCI DSS', 'Criptografia TLS 1.3'],
 NOW(), CURRENT_DATE - 15, TRUE),
(3, 'Marketing e comunicacao',
 ARRAY['nome', 'email', 'preferencias'],
 'CONSENT', 'Marketing direto e comunicacoes promocionais',
 'Empresa X Ltda', NULL, 365, FALSE, NULL,
 ARRAY['Criptografia at-rest', 'Opt-in explicito'],
 NOW(), CURRENT_DATE - 45, TRUE),
(4, 'Analytics e metricas',
 ARRAY['dados de navegacao', 'historico de compras'],
 'LEGITIMATE_INTEREST', 'Melhoria da experiencia do usuario',
 'Empresa X Ltda', 'Google Analytics', 730, TRUE, ARRAY['US'],
 ARRAY['Anonimizacao', 'Pseudonimizacao'],
 NOW(), CURRENT_DATE - 60, TRUE);

-- 2. Gestao de consentimento (Art. 8)
CREATE TABLE lgpd_consent_management (
    consent_id SERIAL PRIMARY KEY,
    data_subject_cpf_hash VARCHAR(64) NOT NULL,
    activity_id INT REFERENCES lgpd_treatment_registry(registry_id),
    consent_given BOOLEAN NOT NULL,
    consent_date TIMESTAMPTZ,
    consent_method VARCHAR(50),
    consent_evidence TEXT,
    withdrawal_date TIMESTAMPTZ,
    withdrawal_reason TEXT,
    renewal_date TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT
);

-- Funcao para registrar consentimento
CREATE OR REPLACE FUNCTION record_consent(
    p_cpf VARCHAR,
    p_activity_id INT,
    p_consent BOOLEAN,
    p_method VARCHAR,
    p_ip INET,
    p_user_agent TEXT
)
RETURNS INT AS $$
DECLARE
    v_consent_id INT;
    v_cpf_hash VARCHAR(64);
BEGIN
    -- Gerar hash do CPF (nao armazenar CPF em texto plano)
    v_cpf_hash := encode(sha256(p_cpf::bytea), 'hex');
    
    -- Verificar se ja existe consentimento para esta atividade
    SELECT consent_id INTO v_consent_id
    FROM lgpd_consent_management
    WHERE data_subject_cpf_hash = v_cpf_hash
    AND activity_id = p_activity_id
    AND withdrawal_date IS NULL;
    
    IF FOUND THEN
        -- Atualizar consentimento existente
        UPDATE lgpd_consent_management SET
            consent_given = p_consent,
            consent_date = CASE WHEN p_consent THEN NOW() ELSE consent_date END,
            withdrawal_date = CASE WHEN NOT p_consent THEN NOW() ELSE NULL END,
            consent_method = p_method,
            ip_address = p_ip,
            user_agent = p_user_agent
        WHERE consent_id = v_consent_id;
    ELSE
        -- Criar novo consentimento
        INSERT INTO lgpd_consent_management (
            data_subject_cpf_hash, activity_id, consent_given,
            consent_date, consent_method, ip_address, user_agent
        )
        VALUES (
            v_cpf_hash, p_activity_id, p_consent,
            CASE WHEN p_consent THEN NOW() ELSE NULL END,
            p_method, p_ip, p_user_agent
        )
        RETURNING consent_id INTO v_consent_id;
    END IF;
    
    -- Log de consentimento
    INSERT INTO lgpd_audit_log (action, cpf_hash, activity_id, details)
    VALUES (
        CASE WHEN p_consent THEN 'CONSENT_GIVEN' ELSE 'CONSENT_WITHDRAWN' END,
        v_cpf_hash, p_activity_id,
        FORMAT('Method: %s, IP: %s', p_method, p_ip)
    );
    
    RETURN v_consent_id;
END;
$$ LANGUAGE plpgsql;

-- 3. Relatorio de conformidade LGPD
SELECT 
    ltr.activity_name,
    ltr.legal_basis,
    ltr.data_categories,
    ltr.retention_period_days,
    ltr.dpo_approved,
    COUNT(lcm.consent_id) AS total_consents,
    COUNT(CASE WHEN lcm.consent_given AND lcm.withdrawal_date IS NULL THEN 1 END) AS active_consents,
    COUNT(CASE WHEN NOT lcm.consent_given OR lcm.withdrawal_date IS NOT NULL THEN 1 END) AS withdrawn_consents,
    ROUND(COUNT(CASE WHEN lcm.consent_given AND lcm.withdrawal_date IS NULL THEN 1 END)::DECIMAL / 
          NULLIF(COUNT(*), 0) * 100, 1) AS consent_rate
FROM lgpd_treatment_registry ltr
LEFT JOIN lgpd_consent_management lcm ON ltr.registry_id = lcm.activity_id
GROUP BY ltr.registry_id, ltr.activity_name, ltr.legal_basis, 
         ltr.data_categories, ltr.retention_period_days, ltr.dpo_approved
ORDER BY ltr.activity_name;
```

## Estudo de Caso: HIPAA para Sistema de Saude

### Implementacao HIPAA para Hospital

```sql
-- Implementacao HIPAA completa para sistema hospitalar

-- 1. Protected Health Information (PHI) Protection
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE patient_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_mrn VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dados criptografados (PHI)
    patient_name_encrypted BYTEA NOT NULL,
    dob_encrypted BYTEA NOT NULL,
    ssn_encrypted BYTEA NOT NULL,
    address_encrypted BYTEA,
    phone_encrypted BYTEA,
    email_encrypted BYTEA,
    
    -- Dados clinicos criptografados
    diagnosis_codes_encrypted BYTEA,
    medications_encrypted BYTEA,
    allergies_encrypted BYTEA,
    
    -- Metadados (nao PHI)
    primary_provider VARCHAR(255),
    department VARCHAR(100),
    admission_date DATE,
    discharge_date DATE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    
    -- Controle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    data_classification VARCHAR(20) DEFAULT 'PHI'
);

-- 2. Minimum Necessary Rule Implementation
-- Views para diferentes papeis

-- Visao completa (medicos atendentes)
CREATE VIEW phi_full_clinical AS
SELECT 
    record_id,
    patient_mrn,
    pgp_sym_decrypt(patient_name_encrypted, current_setting('app.phi_key')) AS patient_name,
    pgp_sym_decrypt(dob_encrypted, current_setting('app.phi_key')) AS dob,
    pgp_sym_decrypt(ssn_encrypted, current_setting('app.phi_key')) AS ssn,
    pgp_sym_decrypt(address_encrypted, current_setting('app.phi_key')) AS address,
    pgp_sym_decrypt(phone_encrypted, current_setting('app.phi_key')) AS phone,
    pgp_sym_decrypt(diagnosis_codes_encrypted, current_setting('app.phi_key')) AS diagnosis_codes,
    pgp_sym_decrypt(medications_encrypted, current_setting('app.phi_key')) AS medications,
    pgp_sym_decrypt(allergies_encrypted, current_setting('app.phi_key')) AS allergies,
    primary_provider,
    admission_date
FROM patient_records
WHERE status = 'ACTIVE';

-- Visao para enfermagem (limitada)
CREATE VIEW phi_nursing_view AS
SELECT 
    record_id,
    patient_mrn,
    pgp_sym_decrypt(patient_name_encrypted, current_setting('app.phi_key')) AS patient_name,
    pgp_sym_decrypt(dob_encrypted, current_setting('app.phi_key')) AS dob,
    pgp_sym_decrypt(medications_encrypted, current_setting('app.phi_key')) AS medications,
    pgp_sym_decrypt(allergies_encrypted, current_setting('app.phi_key')) AS allergies,
    primary_provider
FROM patient_records
WHERE status = 'ACTIVE';
-- NAO inclui: SSN, endereco, telefone, diagnostico detalhado

-- Visao para faturamento (minima)
CREATE VIEW phi_billing_view AS
SELECT 
    record_id,
    patient_mrn,
    pgp_sym_decrypt(ssn_encrypted, current_setting('app.phi_key')) AS ssn,
    pgp_sym_decrypt(diagnosis_codes_encrypted, current_setting('app.phi_key')) AS diagnosis_codes,
    admission_date,
    discharge_date
FROM patient_records;
-- NAO inclui: nome, endereco, telefone, medicacoes, alergias

-- 3. Role-based access
CREATE ROLE phi_physician;
CREATE ROLE phi_nurse;
CREATE ROLE phi_billing;
CREATE ROLE phi_admin;

GRANT SELECT ON phi_full_clinical TO phi_physician;
GRANT SELECT ON phi_nursing_view TO phi_nurse;
GRANT SELECT ON phi_billing_view TO phi_billing;
GRANT SELECT ON patient_records TO phi_admin;

-- 4. HIPAA Audit Trail
CREATE TABLE hipaa_access_log (
    log_id BIGSERIAL PRIMARY KEY,
    access_time TIMESTAMPTZ DEFAULT NOW(),
    user_name VARCHAR(128),
    user_role VARCHAR(50),
    patient_mrn VARCHAR(50),
    access_type VARCHAR(50),
    data_accessed TEXT[],
    purpose VARCHAR(255),
    source_ip INET,
    access_duration_ms INT
);

-- Trigger de auditoria
CREATE OR REPLACE FUNCTION hipaa_phi_audit()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO hipaa_access_log (
        user_name, user_role, patient_mrn, access_type,
        data_accessed, source_ip
    )
    VALUES (
        current_user,
        (SELECT string_agg(rolname, ', ') FROM pg_roles WHERE pg_has_role(current_user, rolname, 'member')),
        COALESCE(NEW.patient_mrn, OLD.patient_mrn),
        TG_OP,
        ARRAY[TG_TABLE_NAME],
        inet_client_addr()
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 5. Relatorio HIPAA compliance
SELECT 
    date_trunc('day', access_time) AS day,
    user_name,
    user_role,
    COUNT(*) AS access_count,
    COUNT(DISTINCT patient_mrn) AS distinct_patients,
    array_agg(DISTINCT access_type) AS access_types
FROM hipaa_access_log
WHERE access_time > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', access_time), user_name, user_role
ORDER BY day DESC, access_count DESC;

-- 6. Deteccao de acesso anomalo
SELECT 
    hal.user_name,
    hal.user_role,
    COUNT(*) AS total_access,
    COUNT(DISTINCT hal.patient_mrn) AS distinct_patients,
    MIN(hal.access_time) AS first_access,
    MAX(hal.access_time) AS last_access,
    CASE 
        WHEN COUNT(DISTINCT hal.patient_mrn) > 50 THEN 'HIGH: Excessive patient access'
        WHEN EXTRACT(HOUR FROM MIN(hal.access_time)) BETWEEN 2 AND 5 THEN 'MEDIUM: Unusual hours'
        ELSE 'NORMAL'
    END AS risk_indicator
FROM hipaa_access_log hal
WHERE hal.access_time > NOW() - INTERVAL '24 hours'
GROUP BY hal.user_name, hal.user_role
HAVING COUNT(DISTINCT hal.patient_mrn) > 20
ORDER BY distinct_patients DESC;
```

## Estudo de Caso: SOC 2 para Startup SaaS

### Implementacao SOC 2 para SaaS

```sql
-- Implementacao SOC 2 para startup SaaS

-- 1. Trust Service Criteria Mapping
CREATE TABLE soc2_tsc_mapping (
    tsc_id VARCHAR(20) PRIMARY KEY,
    tsc_name VARCHAR(255),
    description TEXT,
    control_objectives TEXT,
    implementation_status VARCHAR(20),
    evidence_sources TEXT[]
);

INSERT INTO soc2_tsc_mapping VALUES
('CC6.1', 'Logical and Physical Access Controls',
 'The entity implements logical access security measures',
 'Role-based access, MFA, encryption, network segmentation',
 'IMPLEMENTED',
 ARRAY['pg_hba.conf', 'RBAC configuration', 'MFA enrollment', 'Network diagrams']),
('CC6.2', 'System Boundaries',
 'The entity restricts access to authorized users',
 'Firewall rules, VPN, access control lists',
 'IMPLEMENTED',
 ARRAY['Firewall rules', 'VPN configuration', 'IP whitelists']),
('CC6.3', 'Role-Based Access',
 'The entity authorizes, modifies, or removes access based on roles',
 'Regular access reviews, least privilege, RBAC',
 'IMPLEMENTED',
 ARRAY['Access review logs', 'Role definitions', 'GRANT/REVOKE history']),
('CC7.1', 'Vulnerability Management',
 'The entity monitors system components for vulnerabilities',
 'Vulnerability scanning, patch management',
 'IMPLEMENTED',
 ARRAY['Nessus reports', 'Patch records', 'CVE tracking']),
('CC7.2', 'Security Incident Response',
 'The entity monitors system components for anomalies',
 'SIEM, IDS/IPS, log monitoring',
 'IMPLEMENTED',
 ARRAY['SIEM dashboards', 'Alert rules', 'Incident tickets']),
('CC8.1', 'Change Management',
 'The entity authorizes, designs, develops, configures, documents, tests, approves, and implements changes',
 'Change approval process, testing, rollback procedures',
 'IMPLEMENTED',
 ARRAY['Change tickets', 'Approval records', 'Test results']),
('A1.1', 'Capacity Management',
 'The entity monitors and manages system capacity',
 'Resource monitoring, auto-scaling, capacity planning',
 'IMPLEMENTED',
 ARRAY['CloudWatch metrics', 'Auto-scaling policies', 'Capacity reports']),
('C1.1', 'Confidential Information',
 'The entity identifies and maintains confidential information',
 'Data classification, encryption, access controls',
 'IMPLEMENTED',
 ARRAY['Classification labels', 'Encryption config', 'Access logs']),
('P1-P8', 'Privacy',
 'The entity provides notice and obtains consent for personal data collection',
 'Privacy policy, consent management, data subject rights',
 'IMPLEMENTED',
 ARRAY['Privacy policy', 'Consent records', 'DPIA reports']);

-- 2. Control Evidence Collection
CREATE TABLE soc2_evidence (
    evidence_id SERIAL PRIMARY KEY,
    control_id VARCHAR(20) REFERENCES soc2_tsc_mapping(tsc_id),
    evidence_type VARCHAR(100),
    description TEXT,
    file_location VARCHAR(500),
    collection_date DATE,
    collected_by VARCHAR(255),
    valid_until DATE,
    status VARCHAR(20)
);

INSERT INTO soc2_evidence VALUES
(1, 'CC6.1', 'Configuration Export', 'PostgreSQL pg_hba.conf and postgresql.conf',
 '/evidence/cc6_1/db_config_2024.sql', CURRENT_DATE - 30, 'DBA Team', CURRENT_DATE + 90, 'VALID'),
(2, 'CC6.1', 'Access Control Report', 'Current database users and their roles',
 '/evidence/cc6_1/access_control_report.csv', CURRENT_DATE - 7, 'Security Team', CURRENT_DATE + 23, 'VALID'),
(3, 'CC6.3', 'Access Review Report', 'Q4 2024 access review results',
 '/evidence/cc6_3/access_review_q4_2024.pdf', CURRENT_DATE - 45, 'IT Manager', CURRENT_DATE + 45, 'VALID'),
(4, 'CC7.1', 'Vulnerability Scan', 'Monthly vulnerability scan results',
 '/evidence/cc7_1/nessus_jan_2024.pdf', CURRENT_DATE - 15, 'Security Team', CURRENT_DATE + 15, 'VALID'),
(5, 'CC7.2', 'Incident Report', 'Security incidents in review period',
 '/evidence/cc7_2/incident_report_2024.pdf', CURRENT_DATE - 1, 'SOC Team', CURRENT_DATE + 364, 'VALID');

-- 3. Compliance Dashboard
SELECT 
    tsc.tsc_id,
    tsc.tsc_name,
    tsc.implementation_status,
    COUNT(e.evidence_id) AS evidence_count,
    COUNT(CASE WHEN e.valid_until > CURRENT_DATE THEN 1 END) AS valid_evidence,
    COUNT(CASE WHEN e.valid_until <= CURRENT_DATE THEN 1 END) AS expired_evidence,
    CASE 
        WHEN COUNT(e.evidence_id) = 0 THEN 'NO EVIDENCE'
        WHEN COUNT(CASE WHEN e.valid_until <= CURRENT_DATE THEN 1 END) > 0 THEN 'EXPIRED EVIDENCE'
        ELSE 'COMPLIANT'
    END AS compliance_status
FROM soc2_tsc_mapping tsc
LEFT JOIN soc2_evidence e ON tsc.tsc_id = e.control_id
GROUP BY tsc.tsc_id, tsc.tsc_name, tsc.implementation_status
ORDER BY tsc.tsc_id;
```

## Estudo de Caso: ISO 27001 para Empresa de TI

### Implementacao ISO 27001

```sql
-- Implementacao ISO 27001:2022 para empresa de TI

-- 1. Statement of Applicability (SoA)
CREATE TABLE iso27001_soa (
    control_id VARCHAR(10) PRIMARY KEY,
    control_name VARCHAR(255),
    category VARCHAR(100),
    applicable BOOLEAN NOT NULL,
    justification TEXT,
    implementation_status VARCHAR(20),
    responsible_party VARCHAR(255),
    last_review DATE,
    next_review DATE
);

INSERT INTO iso27001_soa VALUES
('A.5.1', 'Policies for information security', 'Organizational', TRUE,
 'Base policy for all security controls', 'IMPLEMENTED', 'CISO', CURRENT_DATE - 30, CURRENT_DATE + 335),
('A.5.2', 'Information security roles and responsibilities', 'Organizational', TRUE,
 'Clear roles for security governance', 'IMPLEMENTED', 'HR Director', CURRENT_DATE - 60, CURRENT_DATE + 305),
('A.5.3', 'Segregation of duties', 'Organizational', TRUE,
 'Critical duties require multiple people', 'IMPLEMENTED', 'CISO', CURRENT_DATE - 90, CURRENT_DATE + 275),
('A.8.1', 'User endpoint devices', 'Technological', TRUE,
 'Endpoint protection and management', 'IMPLEMENTED', 'IT Operations', CURRENT_DATE - 15, CURRENT_DATE + 350),
('A.8.2', 'Privileged access rights', 'Technological', TRUE,
 'Restricted access to administrative functions', 'IMPLEMENTED', 'DBA Team', CURRENT_DATE - 7, CURRENT_DATE + 358),
('A.8.3', 'Information access restriction', 'Technological', TRUE,
 'RBAC and least privilege', 'IMPLEMENTED', 'Security Team', CURRENT_DATE - 14, CURRENT_DATE + 351),
('A.8.5', 'Secure authentication', 'Technological', TRUE,
 'MFA, strong passwords, certificate auth', 'IMPLEMENTED', 'Security Team', CURRENT_DATE - 30, CURRENT_DATE + 335),
('A.8.11', 'Data masking', 'Technological', TRUE,
 'Mask sensitive data in non-production', 'IN_PROGRESS', 'DBA Team', CURRENT_DATE - 45, CURRENT_DATE + 320),
('A.8.12', 'Data leakage prevention', 'Technological', TRUE,
 'DLP controls for sensitive data', 'IMPLEMENTED', 'Security Team', CURRENT_DATE - 20, CURRENT_DATE + 345),
('A.8.24', 'Use of cryptography', 'Technological', TRUE,
 'Encryption at-rest and in-transit', 'IMPLEMENTED', 'DBA Team', CURRENT_DATE - 30, CURRENT_DATE + 335);

-- 2. Risk Assessment
CREATE TABLE iso27001_risks (
    risk_id SERIAL PRIMARY KEY,
    risk_description TEXT,
    asset VARCHAR(255),
    threat VARCHAR(255),
    vulnerability VARCHAR(255),
    impact VARCHAR(20),
    likelihood VARCHAR(20),
    risk_level VARCHAR(20),
    controls_applied TEXT,
    residual_risk VARCHAR(20),
    risk_owner VARCHAR(255),
    review_date DATE,
    status VARCHAR(20)
);

INSERT INTO iso27001_risks VALUES
(1, 'SQL injection leading to data breach',
 'Customer databases', 'External attacker', 'Unparameterized queries',
 'CRITICAL', 'MEDIUM', 'HIGH',
 'Parameterized queries, WAF, input validation, RBAC',
 'LOW', 'DBA Team', CURRENT_DATE + 90, 'MITIGATED'),
(2, 'Ransomware attack on production data',
 'All production databases', 'Malware/Ransomware', 'Insufficient backups',
 'CRITICAL', 'LOW', 'MEDIUM',
 'Offline backups, network segmentation, EDR, incident response plan',
 'LOW', 'IT Operations', CURRENT_DATE + 90, 'MITIGATED'),
(3, 'Insider data theft',
 'Customer PII', 'Malicious insider', 'Excessive access rights',
 'HIGH', 'LOW', 'MEDIUM',
 'RBAC, DLP, audit logging, access reviews',
 'LOW', 'Security Team', CURRENT_DATE + 90, 'MITIGATED'),
(4, 'Cloud misconfiguration',
 'Cloud databases', 'Human error', 'Lack of IaC governance',
 'HIGH', 'MEDIUM', 'HIGH',
 'IaC scanning, CSPM, least privilege IAM, monitoring',
 'MEDIUM', 'Cloud Team', CURRENT_DATE + 60, 'IN_PROGRESS');

-- 3. Internal Audit
CREATE TABLE iso27001_internal_audits (
    audit_id SERIAL PRIMARY KEY,
    audit_date DATE,
    auditor VARCHAR(255),
    scope TEXT,
    findings INT,
    non_conformities INT,
    observations INT,
    opportunities_for_improvement INT,
    next_audit_date DATE,
    status VARCHAR(20)
);

INSERT INTO iso27001_internal_audits VALUES
(1, CURRENT_DATE - 90, 'Internal Audit Team',
 'ISMS scope - all database systems', 8, 2, 4, 2, CURRENT_DATE + 90, 'COMPLETED'),
(2, CURRENT_DATE - 30, 'Security Team',
 'Access control and encryption controls', 5, 0, 3, 2, CURRENT_DATE + 150, 'COMPLETED');

-- 4. Non-conformity tracking
CREATE TABLE iso27001_ncs (
    nc_id SERIAL PRIMARY KEY,
    audit_id INT REFERENCES iso27001_internal_audits(audit_id),
    control_id VARCHAR(10),
    nc_description TEXT,
    root_cause TEXT,
    corrective_action TEXT,
    responsible VARCHAR(255),
    deadline DATE,
    completion_date DATE,
    verified_by VARCHAR(255),
    verified_date DATE,
    status VARCHAR(20)
);

INSERT INTO iso27001_ncs VALUES
(1, 1, 'A.8.3', 'Excessive permissions found for 3 service accounts',
 'Lack of regular access reviews', 'Implement quarterly access reviews',
 'DBA Team', CURRENT_DATE + 30, CURRENT_DATE - 5, 'Security Lead', CURRENT_DATE - 1, 'CLOSED'),
(2, 1, 'A.8.11', 'Production data found in development environment',
 'No data masking in non-production', 'Implement dynamic data masking',
 'DBA Team', CURRENT_DATE + 60, NULL, NULL, NULL, 'OPEN'),
(3, 2, 'A.8.5', 'MFA not enforced for 2 administrative accounts',
 'Configuration drift', 'Enforce MFA via policy',
 'Security Team', CURRENT_DATE + 14, NULL, NULL, NULL, 'IN_PROGRESS');
```

## Cross-Border Data Transfer Detalhado

### Mecanismos de Transferencia

```sql
-- Mecanismos de transferencia internacional de dados

-- 1. Adequacy Decision (Art. 45 GDPR)
CREATE TABLE adequacy_decisions (
    decision_id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL,
    country_name VARCHAR(100),
    decision_date DATE,
    valid_until DATE,
    scope TEXT,
    regulations TEXT[]
);

INSERT INTO adequacy_decisions VALUES
(1, 'JP', 'Japan', '2019-01-23', NULL, 'Full adequacy', ARRAY['GDPR']),
(2, 'KR', 'South Korea', '2022-12-17', NULL, 'Full adequacy', ARRAY['GDPR']),
(3, 'GB', 'United Kingdom', '2021-06-28', NULL, 'Full adequacy', ARRAY['GDPR']),
(4, 'IL', 'Israel', '2011-07-04', NULL, 'Limited adequacy', ARRAY['GDPR']),
(5, 'UY', 'Uruguay', '2012-08-08', NULL, 'Full adequacy', ARRAY['GDPR']);

-- 2. Standard Contractual Clauses (SCCs)
CREATE TABLE scc_records (
    scc_id SERIAL PRIMARY KEY,
    controller_organization VARCHAR(255),
    processor_organization VARCHAR(255),
    data_categories TEXT[],
    transfer_purpose TEXT,
    destination_country VARCHAR(2),
    signing_date DATE,
    valid_until DATE,
    supplementary_measures TEXT,
    status VARCHAR(20)
);

INSERT INTO scc_records VALUES
(1, 'Empresa BR Ltda', 'AWS Inc.',
 ARRAY['PII', 'Business data', 'Analytics'],
 'Cloud hosting and processing',
 'US', CURRENT_DATE - 180, CURRENT_DATE + 540,
 'Encryption at-rest and in-transit, SCC v2021 module',
 'ACTIVE'),
(2, 'Empresa BR Ltda', 'Google LLC',
 ARRAY['PII', 'Analytics', 'Marketing'],
 'Analytics and advertising',
 'US', CURRENT_DATE - 90, CURRENT_DATE + 630,
 'Data Privacy Framework certified, SCC v2021 module',
 'ACTIVE');

-- 3. Verificacao de conformidade de transferencias
SELECT 
    cbr.source_country,
    cbr.destination_country,
    cbr.transfer_mechanism,
    cbr.adequacy_decision,
    cbr.standard_contractual_clauses,
    cbr.requires_dpia,
    CASE 
        WHEN cbr.adequacy_decision THEN 'ADEQUATE'
        WHEN cbr.standard_contractual_clauses THEN 'SCC IN PLACE'
        ELSE 'REQUIRES ADDITIONAL SAFEGUARDS'
    END AS compliance_status,
    CASE 
        WHEN cbr.requires_dpia THEN 'DPIA REQUIRED'
        ELSE 'DPIA NOT REQUIRED'
    END AS dpia_status
FROM cross_border_transfer_rules cbr
ORDER BY cbr.source_country, cbr.destination_country;
```

## Compliance Automation Avancado

### Automacao com CI/CD

```sql
-- Integracao de compliance com pipeline CI/CD

-- 1. Schema validation antes do deploy
CREATE TABLE schema_compliance_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(255),
    regulation VARCHAR(50),
    check_type VARCHAR(50),
    check_expression TEXT,
    severity VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE
);

INSERT INTO schema_compliance_rules VALUES
(1, 'No plaintext passwords', 'PCI DSS', 'COLUMN_CHECK',
 'SELECT column_name FROM information_schema.columns WHERE table_name = ''users'' AND column_name LIKE ''%password%'' AND data_type = ''text''',
 'CRITICAL', TRUE),
(2, 'Encryption columns present', 'PCI DSS', 'TABLE_CHECK',
 'SELECT table_name FROM information_schema.tables WHERE table_name = ''payment_cards''',
 'CRITICAL', TRUE),
(3, 'Audit trigger exists', 'SOC 2', 'TRIGGER_CHECK',
 'SELECT trigger_name FROM information_schema.triggers WHERE trigger_name = ''pci_audit_trigger''',
 'HIGH', TRUE),
(4, 'RLS enabled on sensitive tables', 'GDPR', 'RLS_CHECK',
 'SELECT schemaname, tablename FROM pg_tables WHERE tablename LIKE ''%personal%'' AND rowsecurity = FALSE',
 'HIGH', TRUE);

-- 2. Funcao de validacao de schema
CREATE OR REPLACE FUNCTION validate_schema_compliance()
RETURNS TABLE(rule_name VARCHAR, regulation VARCHAR, status VARCHAR, details TEXT) AS $$
DECLARE
    v_rule RECORD;
    v_result TEXT;
BEGIN
    FOR v_rule IN SELECT * FROM schema_compliance_rules WHERE enabled = TRUE
    LOOP
        BEGIN
            EXECUTE v_rule.check_expression INTO v_result;
            
            schema_compliance_rules.rule_name := v_rule.rule_name;
            schema_compliance_rules.regulation := v_rule.regulation;
            schema_compliance_rules.status := CASE 
                WHEN v_result IS NULL THEN 'PASS'
                ELSE 'FAIL: ' || v_result
            END;
            schema_compliance_rules.details := v_result;
            
            RETURN NEXT;
        EXCEPTION WHEN OTHERS THEN
            schema_compliance_rules.rule_name := v_rule.rule_name;
            schema_compliance_rules.regulation := v_rule.regulation;
            schema_compliance_rules.status := 'ERROR: ' || SQLERRM;
            schema_compliance_rules.details := SQLERRM;
            RETURN NEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 3. Dashboard de compliance em tempo real
CREATE OR REPLACE VIEW compliance_realtime_dashboard AS
SELECT 
    'PCI DSS' AS regulation,
    (SELECT COUNT(*) FROM payment_cards WHERE card_number_encrypted IS NOT NULL)::TEXT || '/' ||
    (SELECT COUNT(*) FROM payment_cards)::TEXT AS encrypted_cards,
    (SELECT COUNT(DISTINCT performed_by) FROM pci_data_access_log 
     WHERE performed_at > NOW() - INTERVAL '24 hours')::TEXT AS active_users,
    (SELECT COUNT(*) FROM encryption_key_management 
     WHERE is_active = TRUE AND expires_at > NOW() + INTERVAL '30 days')::TEXT AS valid_keys
UNION ALL
SELECT 
    'LGPD',
    (SELECT COUNT(*) FROM lgpd_consent_management 
     WHERE consent_given AND withdrawal_date IS NULL)::TEXT || '/' ||
    (SELECT COUNT(*) FROM lgpd_consent_management)::TEXT AS consent_rate,
    (SELECT COUNT(*) FROM lgpd_treatment_registry 
     WHERE dpo_approved)::TEXT AS approved_activities,
    (SELECT COUNT(*) FROM lgpd_treatment_registry 
     WHERE last_reviewed < CURRENT_DATE - INTERVAL '365 days')::TEXT AS overdue_reviews
UNION ALL
SELECT 
    'HIPAA',
    (SELECT COUNT(*) FROM patient_records 
     WHERE patient_name_encrypted IS NOT NULL)::TEXT || '/' ||
    (SELECT COUNT(*) FROM patient_records)::TEXT AS encrypted_phi,
    (SELECT COUNT(*) FROM hipaa_access_log 
     WHERE access_time > NOW() - INTERVAL '24 hours')::TEXT AS daily_accesses,
    (SELECT COUNT(DISTINCT user_name) FROM hipaa_access_log 
     WHERE access_time > NOW() - INTERVAL '7 days')::TEXT AS weekly_users;
```

## Audit Preparation Avancado

### Checklist de Preparacao para Auditoria

```sql
-- Checklist detalhado para preparacao de auditoria

CREATE TABLE audit_checklist (
    checklist_id SERIAL PRIMARY KEY,
    audit_type VARCHAR(100),
    item_category VARCHAR(100),
    item_description TEXT,
    responsible VARCHAR(255),
    deadline DATE,
    status VARCHAR(20),
    evidence_location VARCHAR(500),
    notes TEXT
);

-- PCI DSS Checklist
INSERT INTO audit_checklist VALUES
(1, 'PCI DSS', 'Network', 'Document network segmentation between cardholder data environment and other networks',
 'Network Team', CURRENT_DATE + 30, 'IN_PROGRESS', '/evidence/network/', NULL),
(2, 'PCI DSS', 'Encryption', 'Verify all card data encrypted at rest with AES-256',
 'DBA Team', CURRENT_DATE + 14, 'COMPLETED', '/evidence/encryption/', NULL),
(3, 'PCI DSS', 'Access Control', 'Complete access review for all users with access to card data',
 'Security Team', CURRENT_DATE + 21, 'NOT_STARTED', NULL, NULL),
(4, 'PCI DSS', 'Monitoring', 'Verify audit logs retained for 12 months with 3 months online',
 'DBA Team', CURRENT_DATE + 7, 'COMPLETED', '/evidence/logs/', NULL),
(5, 'PCI DSS', 'Testing', 'Complete vulnerability scan and penetration test',
 'Security Team', CURRENT_DATE + 45, 'SCHEDULED', NULL, 'QSA scheduled');

-- LGPD Checklist
INSERT INTO audit_checklist VALUES
(6, 'LGPD', 'Consent', 'Verify all consent records are properly documented',
 'Legal Team', CURRENT_DATE + 14, 'IN_PROGRESS', '/evidence/consent/', NULL),
(7, 'LGPD', 'Data Subject Rights', 'Test data subject access, correction, and deletion processes',
 'Engineering Team', CURRENT_DATE + 21, 'NOT_STARTED', NULL, NULL),
(8, 'LGPD', 'DPO', 'Verify DPO appointment and contact information is public',
 'Legal Team', CURRENT_DATE + 7, 'COMPLETED', NULL, NULL),
(9, 'LGPD', 'Breach Response', 'Test incident response plan with tabletop exercise',
 'Security Team', CURRENT_DATE + 30, 'SCHEDULED', NULL, NULL),
(10, 'LGPD', 'DPIA', 'Complete DPIA for high-risk processing activities',
 'Privacy Team', CURRENT_DATE + 45, 'IN_PROGRESS', '/evidence/dpia/', NULL);

-- Relatorio de status
SELECT 
    audit_type,
    item_category,
    COUNT(*) AS total_items,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) AS completed,
    COUNT(CASE WHEN status = 'IN_PROGRESS' THEN 1 END) AS in_progress,
    COUNT(CASE WHEN status = 'NOT_STARTED' THEN 1 END) AS not_started,
    COUNT(CASE WHEN status = 'SCHEDULED' THEN 1 END) AS scheduled,
    ROUND(COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END)::DECIMAL / 
          NULLIF(COUNT(*), 0) * 100, 1) AS completion_rate
FROM audit_checklist
GROUP BY audit_type, item_category
ORDER BY audit_type, completion_rate;
```

## Resumo

Compliance nao e apenas uma questao legal — e uma estrategia de seguranca que protege tanto a organizacao quanto seus clientes. Cada regulamentacao (PCI DSS, LGPD, GDPR, HIPAA, SOC 2, ISO 27001, FIPS 140-3) traz requisitos especificos que se complementam para criar uma postura de seguranca robusta.

Os principios fundamentais que permeiam todas as regulamentacoes sao:

**Criptografia obrigatoria.** Dados sensiveis devem ser criptografados tanto em repouso quanto em transito. Chaves de criptografia devem ser gerenciadas em HSMs com rotacao regular. Algoritmos devem ser FIPS-compliant quando aplicavel.

**Controle de acesso granular.** Least privilege, RBAC, MFA e monitoring sao requisitos comuns a todas as regulamentacoes. Acesso a dados sensiveis deve ser rastreavel e auditavel. Revisoes regulares de acesso sao obrigatorias.

**Retencao minima.** Armazenar apenas dados estritamente necessarios pelo tempo minimamente necessario. Politicas de retencao devem ser documentadas e automatizadas. Dados devem ser anonimizados ou deletados apos o periodo de retencao.

**Monitoramento continuo.** Audit trails completos, deteccao de anomalias e alertas em tempo real sao essenciais para atender requisitos de SOC 2, ISO 27001 e PCI DSS. Logs devem ser preservados por periodos minimos definidos por regulamentacao.

**Preparacao para auditorias.** Documentacao organizada, evidencias de implementacao e testes regulares sao chave para passar em auditorias com sucesso. Cada controle deve ter evidencias coletadas e validadas.

A automacao de compliance, implementada via queries SQL que verificam continuamente a conformidade, e a forma mais eficaz de manter a conformidade ao longo do tempo. Cada verificacao automatizada reduz o risco de nao conformidade e facilita a preparacao para auditorias.

A transferencia internacional de dados requer atencao especial. Adequacy decisions, SCCs e BCRs sao mecanismos que devem ser documentados e monitorados. DPIAs sao obrigatorias para transferencias de alto risco.

A classificacao de dados e o primeiro passo para compliance eficaz. Sem saber quais dados sao sensiveis e onde estao, e impossivel implementar controles adequados. Cada tabela de database deve ser classificada e ter seus controles documentados.

Compliance nao e um projeto com fim — e um processo continuo. Regulamentacoes evoluem, novos requisitos sao adicionados e a organizacao cresce. Automacao, monitoramento e melhoria continua sao as chaves para manter a conformidade ao longo do tempo.

## Estudo de Caso: Migracao de Dados Cross-Border

### Cenarios Comuns de Transferencia

```sql
-- Cenarios praticos de transferencia internacional de dados

-- CENARIO 1: Empresa brasileira usando AWS nos EUA
-- Dados de clientes brasileiros processados em servidores americanos

-- Requisitos:
-- 1. LGPD Art. 33: Transferencia internacional requer uma das bases
-- 2. Avaliacao de risco (DPIA equivalent)
-- 3. Clausulas contratuais padrao (SCCs)

-- Implementacao tecnica
CREATE TABLE cross_border_data_flows (
    flow_id SERIAL PRIMARY KEY,
    data_category VARCHAR(100),
    source_location VARCHAR(100),
    destination_location VARCHAR(100),
    transfer_mechanism VARCHAR(100),
    encryption_method VARCHAR(50),
    access_controls TEXT,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    last_review DATE,
    next_review DATE
);

INSERT INTO cross_border_data_flows VALUES
(1, 'Customer PII', 'Sao Paulo, BR', 'US-East-1, AWS',
 'SCCs + Supplementary Measures', 'AES-256-GCM + TLS 1.3',
 'IAM roles, VPC isolation, MFA', TRUE, CURRENT_DATE - 30, CURRENT_DATE + 335),
(2, 'Payment Data', 'Sao Paulo, BR', 'US-East-1, Stripe',
 'PCI DSS Tokenization + SCCs', 'Stripe tokenization',
 'Token-based processing, no raw card data', TRUE, CURRENT_DATE - 15, CURRENT_DATE + 350),
(3, 'Analytics Data', 'Sao Paulo, BR', 'Global CDN',
 'Anonymization before transfer', 'Data anonymized pre-transfer',
 'No PII in analytics data', TRUE, CURRENT_DATE - 45, CURRENT_DATE + 320);

-- Verificacao de conformidade de transferencias
SELECT 
    cdf.data_category,
    cdf.source_location,
    cdf.destination_location,
    cdf.transfer_mechanism,
    cdf.encryption_method,
    cdf.last_review,
    EXTRACT(DAY FROM cdf.next_review - CURRENT_DATE) AS days_until_review,
    CASE 
        WHEN cdf.next_review < CURRENT_DATE THEN 'OVERDUE: Review required'
        WHEN cdf.next_review < CURRENT_DATE + INTERVAL '30 days' THEN 'UPCOMING: Plan review'
        ELSE 'OK'
    END AS review_status
FROM cross_border_data_flows cdf
ORDER BY cdf.next_review;
```

## Estudo de Caso: Backup e Recovery Compliance

### Backup Seguro para Compliance

```sql
-- Backup strategy que atende multiplas regulamentacoes

-- PCI DSS requer backups criptografados e testados
-- LGPD requer ability para deletar dados de backups
-- HIPAA requer backups com audit trail
-- SOC 2 requer RTO/RPO documentados

CREATE TABLE compliance_backup_policies (
    policy_id SERIAL PRIMARY KEY,
    data_classification VARCHAR(20),
    backup_type VARCHAR(50),
    frequency VARCHAR(50),
    retention_days INT,
    encryption_required BOOLEAN DEFAULT TRUE,
    offsite_required BOOLEAN DEFAULT TRUE,
    test_frequency VARCHAR(50),
    rto_hours INT,
    rpo_minutes INT,
    regulations TEXT[]
);

INSERT INTO compliance_backup_policies VALUES
(1, 'RESTRICTED', 'FULL', 'DAILY', 90, TRUE, TRUE, 'MONTHLY', 4, 60,
 ARRAY['PCI DSS', 'HIPAA', 'SOC 2']),
(2, 'CONFIDENTIAL', 'INCREMENTAL', 'HOURLY', 30, TRUE, TRUE, 'WEEKLY', 1, 15,
 ARRAY['PCI DSS', 'SOC 2', 'ISO 27001']),
(3, 'INTERNAL', 'FULL', 'WEEKLY', 180, TRUE, FALSE, 'QUARTERLY', 24, 1440,
 ARRAY['SOC 2', 'ISO 27001']),
(4, 'PUBLIC', 'FULL', 'MONTHLY', 365, FALSE, FALSE, 'ANNUALLY', 72, 4320,
 ARRAY['ISO 27001']);

-- Funcao para executar backup compliance-aware
CREATE OR REPLACE FUNCTION execute_compliance_backup(
    p_data_classification VARCHAR,
    p_backup_type VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_policy RECORD;
    v_backup_id INT;
BEGIN
    -- Buscar politica aplicavel
    SELECT * INTO v_policy
    FROM compliance_backup_policies
    WHERE data_classification = p_data_classification
    AND backup_type = p_backup_type;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No backup policy found for classification: % and type: %', 
                         p_data_classification, p_backup_type;
    END IF;
    
    -- Registrar inicio do backup
    INSERT INTO backup_execution_log (
        policy_id, backup_type, started_by, started_at, status
    )
    VALUES (v_policy.policy_id, p_backup_type, current_user, NOW(), 'RUNNING')
    RETURNING backup_id INTO v_backup_id;
    
    -- Simular backup (em producao, aqui estaria o comando real de backup)
    -- pg_dump --compress=9 --format=custom --file=backup.sql
    
    -- Atualizar status
    UPDATE backup_execution_log SET
        status = 'COMPLETED',
        completed_at = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::INT,
        encrypted = v_policy.encryption_required,
        offsite = v_policy.offsite_required
    WHERE backup_id = v_backup_id;
    
    -- Log de auditoria
    INSERT INTO compliance_audit_log (action, details, performed_by, performed_at)
    VALUES ('BACKUP_COMPLETED', 
            FORMAT('Classification: %s, Type: %s, Policy: %s', 
                   p_data_classification, p_backup_type, v_policy.policy_id),
            current_user, NOW());
    
    RETURN v_backup_id;
END;
$$ LANGUAGE plpgsql;

-- Verificacao de conformidade de backups
SELECT 
    cbp.data_classification,
    cbp.backup_type,
    cbp.frequency,
    cbp.retention_days,
    cbp.rto_hours,
    cbp.rpo_minutes,
    bel.last_backup_time,
    EXTRACT(EPOCH FROM (NOW() - bel.last_backup_time)) / 3600 AS hours_since_backup,
    CASE 
        WHEN bel.last_backup_time IS NULL THEN 'CRITICAL: No backup found'
        WHEN EXTRACT(EPOCH FROM (NOW() - bel.last_backup_time)) / 3600 > cbp.rto_hours * 2 
             THEN 'CRITICAL: Backup overdue'
        WHEN bel.last_test_date < CURRENT_DATE - INTERVAL '30 days' THEN 'WARNING: Not tested recently'
        ELSE 'OK'
    END AS compliance_status
FROM compliance_backup_policies cbp
LEFT JOIN backup_execution_log bel ON cbp.policy_id = bel.policy_id
    AND bel.backup_id = (SELECT MAX(backup_id) FROM backup_execution_log WHERE policy_id = cbp.policy_id)
ORDER BY cbp.data_classification, cbp.backup_type;
```

## Estudo de Caso: Data Masking para Compliance

### Mascaramento de Dados em Ambientes Nao-Producao

```sql
-- Data masking e essencial para compliance
-- PCI DSS requer mascaramento em ambientes de teste
-- LGPD/GDPR requerem minimizacao de dados em nao-producao

-- 1. Dynamic Data Masking (PostgreSQL 15+)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Funcao de mascaramento dinamico
CREATE OR REPLACE FUNCTION mask_data(
    p_data TEXT,
    p_mask_type VARCHAR,
    p_preserve_format BOOLEAN DEFAULT TRUE
)
RETURNS TEXT AS $$
BEGIN
    CASE p_mask_type
        WHEN 'FULL' THEN
            RETURN REPEAT('*', LENGTH(p_data));
        WHEN 'PARTIAL' THEN
            IF p_preserve_format THEN
                RETURN LEFT(p_data, 2) || REPEAT('*', LENGTH(p_data) - 4) || RIGHT(p_data, 2);
            ELSE
                RETURN LEFT(p_data, 2) || REPEAT('*', LENGTH(p_data) - 2);
            END IF;
        WHEN 'EMAIL' THEN
            RETURN LEFT(p_data, 2) || '***@' || SPLIT_PART(p_data, '@', 2);
        WHEN 'CPF' THEN
            RETURN '***.***.***-' || RIGHT(p_data, 2);
        WHEN 'PHONE' THEN
            RETURN '(**) *****-' || RIGHT(p_data, 4);
        WHEN 'CREDIT_CARD' THEN
            RETURN '****-****-****-' || RIGHT(p_data, 4);
        WHEN 'RANDOM' THEN
            RETURN md5(random()::text);
        ELSE
            RETURN p_data;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- 2. Views com mascaramento para ambientes de teste
CREATE VIEW masked_customer_data AS
SELECT 
    id,
    mask_data(full_name, 'PARTIAL') AS full_name,
    mask_data(email, 'EMAIL') AS email,
    mask_data(cpf, 'CPF') AS cpf,
    mask_data(phone, 'PHONE') AS phone,
    mask_data(address, 'PARTIAL') AS address,
    created_at
FROM customers;

-- 3. Tabela de mascaramento por ambiente
CREATE TABLE masking_rules (
    rule_id SERIAL PRIMARY KEY,
    table_name VARCHAR(255),
    column_name VARCHAR(255),
    mask_type VARCHAR(50),
    preserve_format BOOLEAN DEFAULT TRUE,
    target_environment VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE
);

INSERT INTO masking_rules VALUES
(1, 'customers', 'full_name', 'PARTIAL', TRUE, 'DEVELOPMENT', TRUE),
(2, 'customers', 'email', 'EMAIL', TRUE, 'DEVELOPMENT', TRUE),
(3, 'customers', 'cpf', 'CPF', TRUE, 'DEVELOPMENT', TRUE),
(4, 'customers', 'phone', 'PHONE', TRUE, 'DEVELOPMENT', TRUE),
(5, 'payment_cards', 'card_number', 'CREDIT_CARD', TRUE, 'DEVELOPMENT', TRUE),
(6, 'payment_cards', 'cvv', 'FULL', FALSE, 'DEVELOPMENT', TRUE);

-- Funcao para mascarar tabela inteira
CREATE OR REPLACE FUNCTION mask_table_for_environment(
    p_table_name VARCHAR,
    p_environment VARCHAR
)
RETURNS INT AS $$
DECLARE
    v_rule RECORD;
    v_affected_rows INT := 0;
    v_total_rows INT := 0;
BEGIN
    FOR v_rule IN 
        SELECT * FROM masking_rules 
        WHERE table_name = p_table_name 
        AND target_environment = p_environment
        AND enabled = TRUE
    LOOP
        EXECUTE format(
            'UPDATE %I SET %I = mask_data(%I::text, %L, %L)',
            v_rule.table_name,
            v_rule.column_name,
            v_rule.column_name,
            v_rule.mask_type,
            v_rule.preserve_format
        );
        
        GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
        v_total_rows := v_total_rows + v_affected_rows;
    END LOOP;
    
    -- Log de mascaramento
    INSERT INTO compliance_audit_log (action, details, performed_by, performed_at)
    VALUES ('DATA_MASKING', 
            FORMAT('Table: %s, Environment: %s, Rows masked: %s', 
                   p_table_name, p_environment, v_total_rows),
            current_user, NOW());
    
    RETURN v_total_rows;
END;
$$ LANGUAGE plpgsql;

-- Verificacao de mascaramento
SELECT 
    mr.table_name,
    mr.column_name,
    mr.mask_type,
    mr.target_environment,
    mr.enabled,
    CASE 
        WHEN mr.enabled AND mr.target_environment = 'DEVELOPMENT' THEN 'ACTIVE: Data masked'
        WHEN NOT mr.enabled THEN 'DISABLED: Review required'
        ELSE 'CONFIGURED'
    END AS status
FROM masking_rules mr
ORDER BY mr.table_name, mr.column_name;
```