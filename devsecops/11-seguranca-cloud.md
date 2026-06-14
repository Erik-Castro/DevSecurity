# Capítulo 11 — Segurança em Cloud

A adoção massiva de serviços cloud transformou a maneira como as organizações constroem, implantam e operam software. Contudo, essa transição trouxe novos vetores de ataque e superfícies de exposição que não existiam no modelo on-premises tradicional. Segurança em cloud não é apenas sobre configurar firewalls — é sobre repensar toda a cadeia de valor da segurança, desde a identidade até os dados, passando por rede, computação, aplicações e operações.

Este capítulo explora os pilares fundamentais de segurança em cloud, abordando os três principais provedores públicos (AWS, Azure e GCP), padrões de arquitetura segura, gestão de postura de segurança, proteção de workload e como integrar segurança nas pipelines de entrega contínua para ambientes cloud-native.

---

## Sumário

1. [Shared Responsibility Model](#1-shared-responsibility-model)
2. [AWS Security](#2-aws-security)
3. [Azure Security](#3-azure-security)
4. [GCP Security](#4-gcp-security)
5. [Cloud Security Posture Management (CSPM)](#5-cloud-security-posture-management-cspm)
6. [Cloud Workload Protection](#6-cloud-workload-protection)
7. [Network Security in Cloud](#7-network-security-in-cloud)
8. [Data Protection](#8-data-protection)
9. [Cloud Logging and Monitoring](#9-cloud-logging-and-monitoring)
10. [Exemplo Completo: Secure Cloud Deployment](#10-exemplo-completo-secure-cloud-deployment)
11. [Referências](#11-referências)

---

## 1. Shared Responsibility Model

### 1.1 O Modelo de Responsabilidade Compartilhada

O Shared Responsibility Model é o alicerce de qualquer discussão sobre segurança em cloud. Ele estabelece claramente onde termina a responsabilidade do provedor de cloud e onde começa a responsabilidade do cliente. A confusão sobre essa divisão é uma das principais causas de violações de dados em ambientes cloud.

A regra fundamental é:

> **O provedor é responsável pela segurança DA cloud. O cliente é responsável pela segurança NA cloud.**

Essa distinção parece sutil, mas suas implicações são enormes. Um bucket S3 com acesso público não é uma falha da AWS — é uma falha do cliente que configurou o bucket incorretamente. Um banco de dados SQL com credenciais padrão não é uma vulnerabilidade do Azure — é negligência do operador.

### 1.2 Responsabilidades por Modelo de Serviço

A divisão de responsabilidade varia significativamente entre os modelos de serviço:

#### IaaS (Infrastructure as a Service)

No modelo IaaS, o provedor gerencia a infraestrutura física, a virtualização e a rede física. O cliente é responsável por praticamente tudo acima disso:

**Responsabilidade do provedor:**
- Segurança física dos data centers
- Hipervisor e camada de virtualização
- Rede física e infraestrutura global
- Certificações de compliance (SOC, ISO, PCI)

**Responsabilidade do cliente:**
- Sistema operacional e patches de segurança
- Configuração de firewall do host
- Grupo de segurança e ACLs de rede
- Gerenciamento de identidade e acesso (IAM)
- Criptografia de dados em repouso e trânsito
- Configuração de VPC, subnets e rotas
- Aplicações e dados

#### PaaS (Platform as a Service)

No PaaS, o provedor assume mais responsabilidades, mas o cliente continua sendo responsável pela aplicação e pelos dados:

**Responsabilidade do provedor:**
- Tudo do IaaS, mais:
- Sistema operacional e patches
- Runtime e middleware
- Gerenciamento de atualizações de plataforma

**Responsabilidade do cliente:**
- Aplicação e código
- Dados e criptografia
- Configuração de acesso
- Segurança de bibliotecas e dependências

#### SaaS (Software as a Service)

No SaaS, o provedor gerencia quase tudo, mas o cliente ainda tem responsabilidades críticas:

**Responsabilidade do provedor:**
- Tudo do PaaS, mais:
- Aplicação e sua segurança
- Infraestrutura completa

**Responsabilidade do cliente:**
- Dados carregados na plataforma
- Configuração de acesso e permissões
- Políticas de retenção de dados
- Conformidade regulatoria dos dados

### 1.3 Matriz de Responsabilidades

| Camada | IaaS | PaaS | SaaS |
|--------|------|------|------|
| Dados | Cliente | Cliente | Cliente |
| Aplicação | Cliente | Cliente | Provedor |
| Runtime | Cliente | Provedor | Provedor |
| Middleware | Cliente | Provedor | Provedor |
| Sistema Operacional | Cliente | Provedor | Provedor |
| Virtualização | Provedor | Provedor | Provedor |
| Servidores | Provedor | Provedor | Provedor |
| Armazenamento | Provedor | Provedor | Provedor |
| Rede | Provedor | Provedor | Provedor |
| Data Center | Provedor | Provedor | Provedor |

### 1.4 Equívocos Comuns

#### Equívoco 1: "A configuração padrão é segura"

Provedores de cloud frequentemente fornecem configurações que priorizam a facilidade de uso e a velocidade de provisionamento, não a segurança. Um bucket S3 pode ser criado com acesso público habilitado por padrão. Um Security Group pode permitir tráfego de entrada de qualquer IP por padrão.

**Exemplo de configuração insegura:**
```yaml
# NUNCA faca isso em producao
S3Bucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: meus-dados-sensiveis
    # AccessControl: PublicRead  # EXTREMAMENTE PERIGOSO
    # Nao configurou BlockPublicAccess
    # Nao configurou encryption
    # Nao configurou versionamento
```

**Exemplo de configuração segura:**
```yaml
S3Bucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: meus-dados-sensiveis
    VersioningConfiguration:
      Status: Enabled
    BucketEncryption:
      ServerSideEncryptionConfiguration:
        - ServerSideEncryptionByDefault:
            SSEAlgorithm: aws:kms
            KMSMasterKeyID: !Ref KMSKey
    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
    LifecycleConfiguration:
      Rules:
        - Id: MoveToGlacier
          Status: Enabled
          Transitions:
            - TransitionInDays: 90
              StorageClass: GLACIER
```

#### Equívoco 2: "Cloud é inerentemente inseguro"

A realidade é oposta: a maioria dos provedores de cloud investe mais em segurança do que a maioria das organizações individualmente poderia investir. Data centers da AWS, Azure e GCP possuem certificações como SOC 2 Type II, ISO 27001, PCI DSS e muitas outras. O problema raramente é o provedor — quase sempre é a configuração feita pelo cliente.

#### Equívoco 3: "Se eu pago pelo serviço, ele vem seguro por padrão"

Pagar por um serviço cloud não garante que ele esteja configurado de forma segura. Serviços gerenciados como RDS, Cloud SQL e Azure SQL ainda precisam de configuração adequada de rede, criptografia, backups e controle de acesso.

#### Equívoco 4: "Meu time de segurança on-premises resolve isso"

Segurança em cloud requer habilidades específicas e diferentes do modelo on-premises. Conceitos como IAM baseado em políticas, Security Groups stateless, VPCs, roles temporárias e funções Lambda precisam de conhecimento especializado que nem sempre existe em equipes tradicionais.

### 1.5 Casos Documentados: Falhas no Shared Responsibility Model

#### Capital One (2019) — SSRF via WAF

Em julho de 2019, a Capital One sofreu uma das maiores violações de dados na história dos serviços financeiros nos EUA, expondo dados pessoais de mais de 100 milhões de clientes e solicitantes de crédito.

**O que aconteceu:**

Um ex-engenheiro da AWS explora uma vulnerabilidade de Server-Side Request Forgery (SSRF) em um Web Application Firewall (WAF) executado na AWS. O atacante:

1. Acessou um servidor WAF que rodava em uma instância EC2
2. Explorou uma configuração de metadados da instância (IMDSv1)
3. Obteve credenciais temporárias da Role IAM associada à instância
4. A Role IAM tinha permissões excessivas — acesso a buckets S3 que não deveria acessar
5. Baixou dados sensíveis de vários buckets S3

**Falha principal:** O WAF estava configurado com uma Role IAM que violava o princípio do menor privilégio. A Role tinha acesso a recursos muito além do necessário para o WAF.

```yaml
# Configuracao INCORRETA - Role IAM com permissoes excessivas
# (representacao conceitual do que causou a violacao)
RolePolicy:
  Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Action: "s3:*"
      Resource: "*"  # Acesso TOTAL a todos os buckets - ERRO GRAVE
```

```yaml
# Configuracao CORRETA - Princípio do menor privilegio
RolePolicy:
  Version: "2012-10-17"
  Statement:
    - Effect: Allow
      Action:
        - "s3:GetObject"
      Resource: "arn:aws:s3:::waf-logs-bucket/*"
    - Effect: Allow
      Action:
        - "s3:PutObject"
      Resource: "arn:aws:s3:::waf-logs-bucket/*"
    # Nada mais. Periodo.
```

**Licoes aprendidas:**
- IMDSv1 deve ser desabilitado (usar IMDSv2 com token)
- Roles IAM devem seguir estritamente o princípio do menor privilégio
- WAFs e serviços de segurança precisam de permissões minimas
- Monitoramento de chamadas STS AssumeRole e GetCallerIdentity deve gerar alertas

#### Twitch Data Leak (2021) — Server Misconfiguration

Em outubro de 2021, dados internos massivos do Twitch foram vazados, incluindo codigo-fonte, dados de pagamentos a streamers (mais de $1 milhão para alguns criadores), informações de usuários e dados de infraestrutura.

**O que aconteceu:**

Um atacante explora uma mudança na infraestrutura de servidores que expôs dados sensíveis devido a uma reconfiguração temporária. O atacante acessou um repositório de dados que estava temporariamente exposto.

**Falha principal:** Mudança de configuração de servidor que temporariamente removeu controles de acesso, sem validação de segurança antes da implantação.

```yaml
# Configuracao que expoe dados - representacao conceitual
ServerConfig:
  DataStore:
    AccessControl: Private  # Configuracao anterior
    # Apos reconfiguracao, AccessControl ficou indefinido
    # O servico assume PRIVATE como default - mas a mudanca
    # temporariamente expôs o bucket
    
    # Erro: nao havia verificacao automatica de postura
    # Erro: nao havia alerta quando a mudanca foi aplicada
    # Erro: dados de pagamento nao estavam criptografados em repouso
```

**Licoes aprendidas:**
- Mudanças de configuração devem ser versionadas e revisadas
- Validação de postura de segurança deve rodar antes e após mudanças
- Dados sensíveis devem ser criptografados em repouso independentemente do controle de acesso
- Alertas automáticos devem detectar expõções acidentais

#### Microsoft Azure CosmosDB (2021) — Vulnerabilidade de Acesso Cross-Tenant

Em agosto de 2021, pesquisadores de segurança da Wiz descobriram uma vulnerabilidade no Azure Cosmos DB que permitia acesso cross-tenant — um atacante poderia acessar os dados de qualquer cliente Cosmos DB no Azure.

**O que aconteceu:**

A funcionalidade Jupyter Notebook, habilitada por padrão em muitas contas Cosmos DB, continha uma vulnerabilidade que permitia escalação de privilégios cross-tenant. O atacante podia:
1. Acessar o notebook de outro tenant
2. Escalar privilégios para o account resource provider
3. Ler, modificar ou excluir dados de qualquer conta Cosmos DB

**Falha principal:** Feature habilitada por padrão que expandia a superfície de ataque, combinada com falha de isolamento entre tenants.

**Impacto:**
- Centenas de clientes afetados
 Microsoft precisou forçar rotação de todas as chaves de acesso Cosmos DB
- Dados de clientes como Fortune 500 estavam potencialmente expostos

**Licoes aprendidas:**
- Features opcionais não devem ser habilitadas por padrão
- Isolamento entre tenants requer validação contínua
- Roatação de credenciais deve ser automatizável e testada regularmente
- Desabilitar features não utilizadas reduz superfície de ataque

#### AWS S3 Bucket Exposures (Múltiplos Incidentes, 2017-2024)

Várias organizações expuseram dados sensíveis através de buckets S3 configurados incorretamente. Alguns dos incidentes notáveis:

**Accenture (2017):** 40KB de dados expostos incluindo credenciais, chaves de criptografia e dados de administração de 47 buckets S3.

**Dow Jones (2017):** 2.4 milhões de registros de clientes expostos, incluindo informações de vigilância financeira.

**Verizon (2017):** 6 milhões de registros de clientes expostos em um bucket S3 administrado por um parceiro terceiro.

**Pentagon (2017):** Dados classificados de defesa encontrados em um bucket S3 com acesso público.

```yaml
# Padrao de configuracao insegura - repetido em multiplos incidentes
S3Bucket:
  Properties:
    AccessControl: PublicRead  # OU
    # BucketPolicy permite "Principal": "*"
    # Sem BlockPublicAccessConfiguration
    # Sem ServerSideEncryption
    # Sem versionamento
    # Sem lifecycle rules
    # Sem access logging

# Como o AWS agora protege por padrao (2023+):
# - BlockPublicAccess esta habilitado por padrao
# - AES256 encryption por padrao
# - Mas organizacoes podem CONTINUAR tornando buckets publicos
# - O problema persiste quando teams ignoram esses controles
```

**Licoes aprendidas:**
- Block Public Access deve ser habilitado na conta e no bucket
- AWS Organizations SCPs podem impedir a criação de buckets públicos
- AWS Config Rules podem detectar buckets públicos em tempo real
- Terceiros e parceiros devem seguir as mesmas políticas de segurança

#### Google Cloud Project Misconfigurations

Estudos conduzidos por empresas de segurança como Orca e Wiz em 2022-2023 revelaram que milhares de projetos GCP estavam expostos devido a configurações incorretas:

- Firewall rules permitindo tráfego de `0.0.0.0/0` em portas sensíveis
- Service accounts com permissões de Owner em vez de permissões mínimas
- Cloud Storage buckets públicos contendo dados sensíveis
- Instâncias Compute Engine com IP externo em redes privadas
- Chaves de service accounts exportadas e armazenadas em repositorios

```yaml
# Configuracao GCP insegura - representacao
FirewallRules:
  - name: "allow-all"
    direction: "INGRESS"
    sourceRanges: ["0.0.0.0/0"]
    allowed:
      - "tcp:22"  # SSH aberto para o mundo
      - "tcp:3389"  # RDP aberto para o mundo

# Configuracao GCP segura
FirewallRules:
  - name: "allow-ssh-from-bastion"
    direction: "INGRESS"
    sourceRanges: ["10.0.1.0/24"]  # Apenas subnet do bastion
    targetTags: ["ssh-allowed"]
    allowed:
      - "tcp:22"

  - name: "deny-all-ingress"
    direction: "INGRESS"
    sourceRanges: ["0.0.0.0/0"]
    denied:
      - "all"
    priority: 65534
```

#### Uber Cloud Credential Leak (2022)

Em setembro de 2022, um atacante comprometeu a infraestrutura cloud da Uber explorando credenciais expostas.

**O que aconteceu:**

1. Um funcionário da Uber teve credenciais roubadas por malware no dispositivo pessoal
2. O atacante comprou credenciais de acesso à VPN da Uber na dark web
3. As credenciais não tinham MFA habilitado
4. Uma vez dentro da VPN, o atacante encontrou credenciais PowerShell em um script
5. Essas credenciais tinham acesso ao ambiente de administração do cloud
6. O atacante acessou o console de administração da Uber e encontrou mais credenciais
7. Expostos: dados financeiros, dados de clientes, código-fonte

```yaml
# Cadeia de falhas que levaram ao ataque:
FalhasIdentificadas:
  1. MFA nao habilitado para acesso VPN
  2. Credenciais armazenadas em scripts PowerShell
  3. Credenciais cloud encontradas em repositorios internos
  4. Falta de gestao centralizada de secrets
  5. Falta de monitoramento de comportamento anomalo
  6. Falta de segmentacao entre ambientes
  7. Conta de administrador sem restricoes
```

**Licoes aprendidas:**
- MFA deve ser obrigatório para TODOS os acessos remotos
- Nunca armazenar credenciais em scripts ou repositorios
- Usar ferramentas de gestao de secrets (Vault, AWS Secrets Manager, Azure Key Vault)
- Implementar Zero Trust — confiar em nada, verificar tudo
- Monitoramento de comportamento anomalo deve detectar acessos atipicos
- Segmentacao de rede limita o movimento lateral

---

## 2. AWS Security

### 2.1 IAM Best Practices

O Identity and Access Management (IAM) é o sistema de controle de acesso da AWS. Uma configuração inadequada do IAM é a causa raiz da maioria das violações de segurança em AWS.

**Princípios fundamentais:**

1. **Nunca usar a conta root para operações diárias.** A conta root tem acesso irrestrito a todos os recursos. Crie uma conta IAM administrativa e use-a para operações cotidianas.

2. **Habilitar MFA para todas as contas com acesso privilegiado.** Hardware tokens (YubiKey) são preferidos. Virtual tokens (Google Authenticator) são aceitáveis. SMS NÃO é seguro.

3. **Usar roles em vez de credenciais de acesso programático.** Roles são temporárias, rotacionadas automaticamente, e não expõem chaves de longa duração.

4. **Aplicar o princípio do menor privilégio.** Cada identidade deve ter apenas as permissões estritamente necessárias para sua função.

5. **Revisar permissões regularmente.** Use IAM Access Analyzer para identificar permissões não utilizadas e recursos compartilhados externamente.

```yaml
# Terraform - IAM Policy com menor privilegio
resource "aws_iam_policy" "s3_read_only" {
  name        = "s3-read-only-logs"
  description = "Permite leitura apenas do bucket de logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.logs.arn,
          "${aws_s3_bucket.logs.arn}/*"
        ]
      }
    ]
  })
}

# NUNCA faca isso:
# resource "aws_iam_policy" "s3_full_access" {
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Effect = "Allow"
#       Action = "s3:*"
#       Resource = "*"
#     }]
#   })
# }
```

**IAM Access Analyzer:**

```yaml
# Configuracao do IAM Access Analyzer
resource "aws_accessanalyzer_analyzer" "main" {
  analyzer_name = "account-analyzer"
  type          = "ACCOUNT"

  configuration {
    unused_access {
      unused_access_age = 90
    }
  }
}
```

### 2.2 S3 Bucket Security

O Amazon S3 é uma das fontes mais comuns de vazamento de dados. A segurança do S3 requer múltiplas camadas de proteção:

```yaml
resource "aws_s3_bucket" "dados_sensiveis" {
  bucket = "empresa-dados-sensiveis-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = "production"
    DataClass   = "confidential"
  }
}

# Bloqueio total de acesso publico
resource "aws_s3_bucket_public_access_block" "dados_sensiveis" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versaoamento para recuperacao de dados
resource "aws_s3_bucket_versioning" "dados_sensiveis" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encriptacao em repouso com KMS
resource "aws_s3_bucket_server_side_encryption_configuration" "dados_sensiveis" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_encryption.arn
    }
    bucket_key_enabled = true
  }
}

# Politica de acesso forca HTTPS
resource "aws_s3_bucket_policy" "enforce_https" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceSSL"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.dados_sensiveis.arn,
          "${aws_s3_bucket.dados_sensiveis.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.dados_sensiveis]
}

# Lifecycle para gerenciamento de dados antigos
resource "aws_s3_bucket_lifecycle_configuration" "dados_sensiveis" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  rule {
    id     = "archive-old-data"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555  # 7 anos para compliance
    }
  }
}

# Access logging
resource "aws_s3_bucket" "access_logs" {
  bucket = "empresa-s3-access-logs-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_logging" "dados_sensiveis" {
  bucket = aws_s3_bucket.dados_sensiveis.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "s3-access-logs/"
}
```

### 2.3 EC2 Hardening

```yaml
# Security Group restritivo
resource "aws_security_group" "web_server" {
  name        = "web-server-sg"
  description = "Security group para servidores web"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "web-server-sg"
  }
}

resource "aws_security_group_rule" "https_in" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web_server.id
  description       = "HTTPS do WAF/ALB"
}

resource "aws_security_group_rule" "ssh_bastion" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion.id
  security_group_id        = aws_security_group.web_server.id
  description              = "SSH apenas do bastion host"
}

resource "aws_security_group_rule" "all_out" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.web_server.id
  description       = "Todo o trafego de saida"
}

# User Data para hardening
resource "aws_launch_template" "web_server" {
  name_prefix   = "web-server-"
  image_id      = data.aws_ami.amazon_linux_2.id
  instance_type = "t3.medium"

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_profile.name
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Forca IMDSv2
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  monitoring {
    enabled = true
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    set -euo pipefail
    
    # Atualizar sistema
    yum update -y
    
    # Instalar e configurar agente SSM
    yum install -y amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    
    # Configurar CloudWatch Agent
    yum install -y amazon-cloudwatch-agent
    
    # Desabilitar login root via SSH
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
    
    # Forcar autenticacao por chave
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    
    # Configurar timeout de inatividade SSH
    echo "ClientAliveInterval 300" >> /etc/ssh/sshd_config
    echo "ClientAliveCountMax 2" >> /etc/ssh/sshd_config
    
    # Habilitar auditd
    yum install -y audit
    systemctl enable auditd
    systemctl start auditd
    
    # Configurar logrotate para logs de seguranca
    cat > /etc/logrotate.d/secure-logs << 'LOGEOF'
    /var/log/secure /var/log/audit/* {
        daily
        rotate 30
        compress
        delaycompress
        missingok
        notifempty
        copytruncate
    }
    LOGEOF
    
    # Instalar e habilitar FALCO ou similar
    # yum install -y falco
    # systemctl enable falco
    
    echo "Hardening completo - $(date)" >> /var/log/user-data.log
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "web-server"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}
```

### 2.4 Lambda Security

```yaml
resource "aws_lambda_function" "api_processor" {
  function_name = "api-processor"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST     = aws_db_instance.primary.endpoint
      ENVIRONMENT = "production"
    }
  }

  kms_key_arn = aws_kms_key.lambda_env.arn

  tracing_config {
    mode = "Active"
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  tags = {
    Security = "high"
  }
}

# Role IAM com permissao minima
resource "aws_iam_role" "lambda_role" {
  name = "lambda-api-processor-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-minimal-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:Vpc" = aws_vpc.main.arn
          }
        }
      }
    ]
  })
}

# SGP para Lambda dentro de VPC
resource "aws_security_group" "lambda" {
  name        = "lambda-sg"
  description = "Security group para Lambda"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]
    description     = "PostgreSQL"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "AWS APIs"
  }
}
```

### 2.5 Complete Terraform for Secure AWS

```yaml
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "empresa-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# VPC com subnets privadas
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "production-vpc"
  }
}

resource "aws_subnet" "private" {
  count             = 3
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = "${var.region}${["a", "b", "c"][count.index]}"

  tags = {
    Name = "private-${count.index + 1}"
    Tier = "private"
  }
}

resource "aws_subnet" "public" {
  count                   = 3
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 10}.0/24"
  availability_zone       = "${var.region}${["a", "b", "c"][count.index]}"
  map_public_ip_on_launch = false

  tags = {
    Name = "public-${count.index + 1}"
    Tier = "public"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "main-nat"
  }
}

# CloudTrail
resource "aws_cloudtrail" "main" {
  name                          = "production-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.cloudtrail.arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::"]
    }
  }
}

# GuardDuty
resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }
}

# Security Hub
resource "aws_securityhub_account" "main" {
  enable_default_standards = true
}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.4.0"
}

resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:::standards/aws-foundational-security-best-practices/v/1.0.0"
}

# AWS Config
resource "aws_config_configuration_recorder" "main" {
  name     = "production-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_config_rule" "s3_public_read_prohibited" {
  name = "s3-bucket-public-read-prohibited"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "encrypted_volumes" {
  name = "encrypted-volumes"

  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "root_access_key_check" {
  name = "root-access-key-check"

  source {
    owner             = "AWS"
    source_identifier = "ROOT_ACCESS_KEY_CHECK"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

# WAF
resource "aws_wafv2_web_acl" "main" {
  name        = "production-waf"
  description = "WAF para producao"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "CommonRuleSet"
      sampled_requests_enabled  = true
    }
  }

  rule {
    name     = "RateLimitRule"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRule"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "production-waf"
    sampled_requests_enabled  = true
  }
}
```

---

## 3. Azure Security

### 3.1 Azure AD / Entra ID

O Microsoft Entra ID (anteriormente Azure Active Directory) é o serviço de identidade do Azure. Configurá-lo corretamente é fundamental:

```yaml
# Politica de Conditional Access - exigir MFA
resource "azuread_conditional_access_policy" "require_mfa" {
  display_name = "Exigir MFA para todos"
  state        = "enabled"

  conditions {
    users {
      included_users = ["All"]
    }

    applications {
      included_applications = ["All"]
    }

    client_app_types = ["browser", "mobileAppsAndDesktopClients"]
  }

  grant_controls {
    operator          = "OR"
    built_in_controls = ["mfa"]
  }

  session_controls {
    sign_in_frequency {
      value     = 8
      type      = "hours"
    }
  }
}

# Politica de bloqueio de contas legacy
resource "azuread_conditional_access_policy" "block_legacy" {
  display_name = "Bloquear protocolos legados"
  state        = "enabled"

  conditions {
    users {
      included_users = ["All"]
    }

    applications {
      included_applications = ["All"]
    }

    platforms {
      included_platforms = ["all"]
    }

    client_app_types = ["exchangeActiveSync", "other"]
  }

  grant_controls {
    operator          = "OR"
    built_in_controls = ["block"]
  }
}

# Politica de restricao geografica
resource "azuread_conditional_access_policy" "block_countries" {
  display_name = "Bloquear acessos de paises de alto risco"
  state        = "enabled"

  conditions {
    users {
      included_users = ["All"]
    }

    locations {
      included_locations = ["All"]
      excluded_locations = ["AllTrusted"]
    }
  }

  grant_controls {
    operator          = "OR"
    built_in_controls = ["block"]
  }
}
```

### 3.2 Storage Account Security

```yaml
resource "azurerm_storage_account" "seguro" {
  name                     = "empresadadosseguro"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  account_kind             = "StorageV2"

  # Forcar TLS 1.2
  min_tls_version = "TLS1_2"

  # Bloquear acesso publico
  allow_blob_public_access = false

  # Habilitar HTTPS apenas
  enable_https_traffic_only = true

  # Habilitar versionamento
  versioning_enabled = true

  # Encriptacao com chave gerenciada pelo cliente
  customer_managed_key {
    key_vault_secret_id   = azurerm_key_vault_secret.storage_key.versionless_id
    user_assigned_identity_id = azurerm_user_assigned_identity.storage.id
  }

  # Restricao de rede
  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]

    virtual_network_subnet_id = azurerm_subnet.storage.id
  }

  tags = {
    Environment = "production"
    DataClass   = "confidential"
  }
}

# Container com acesso restrito
resource "azurerm_storage_container" "dados" {
  name                  = "dados"
  storage_account_name  = azurerm_storage_account.seguro.name
  container_access_type = "private"
}
```

### 3.3 Key Vault Integration

```yaml
resource "azurerm_key_vault" "main" {
  name                = "empresa-seguranca"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"

  # Politica de acesso baseada em RBAC
  enable_rbac_authorization = true

  # Soft delete e purge protection
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  # Restricao de rede
  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = var.allowed_ips
  }

  tags = {
    Environment = "production"
  }
}

# Acesso restrito a identity especifica
resource "azurerm_role_assignment" "key_vault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.admin_principal_id
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.app_service_principal_id
}

# Secret com rotacao programada
resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = random_password.db.result
  key_vault_id = azurerm_key_vault.main.id

  content_type = "text/plain"

  tags = {
    RotationDate = "2024-01-01"
  }
}

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!@#$%^&*"
}
```

### 3.4 ARM Template com Seguranca

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName": {
      "type": "string",
      "defaultValue": "production",
      "allowedValues": ["production", "staging", "development"]
    },
    "location": {
      "type": "string",
      "defaultValue": "[resourceGroup().location]"
    }
  },
  "variables": {
    "vnetAddressPrefix": "10.0.0.0/16",
    "subnetPrefixes": {
      "web": "10.0.1.0/24",
      "app": "10.0.2.0/24",
      "data": "10.0.3.0/24"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Network/networkSecurityGroups",
      "apiVersion": "2023-04-01",
      "name": "nsg-web",
      "location": "[parameters('location')]",
      "properties": {
        "securityRules": [
          {
            "name": "allow-https",
            "properties": {
              "priority": 100,
              "direction": "Inbound",
              "access": "Allow",
              "protocol": "Tcp",
              "sourcePortRange": "*",
              "destinationPortRange": "443",
              "sourceAddressPrefix": "Internet",
              "destinationAddressPrefix": "*"
            }
          },
          {
            "name": "deny-all-inbound",
            "properties": {
              "priority": 4096,
              "direction": "Inbound",
              "access": "Deny",
              "protocol": "*",
              "sourcePortRange": "*",
              "destinationPortRange": "*",
              "sourceAddressPrefix": "*",
              "destinationAddressPrefix": "*"
            }
          }
        ]
      }
    },
    {
      "type": "Microsoft.KeyVault/vaults",
      "apiVersion": "2023-02-01",
      "name": "[concat(parameters('environmentName'), '-kv')]",
      "location": "[parameters('location')]",
      "properties": {
        "tenantId": "[subscription().tenantId]",
        "sku": {
          "family": "A",
          "name": "premium"
        },
        "enableSoftDelete": true,
        "softDeleteRetentionInDays": 90,
        "enableRbacAuthorization": true,
        "enablePurgeProtection": true,
        "networkAcls": {
          "defaultAction": "Deny",
          "bypass": "AzureServices"
        },
        "accessPolicies": []
      }
    },
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2023-01-01",
      "name": "[concat(parameters('environmentName'), 'storage')]",
      "location": "[parameters('location')]",
      "sku": {
        "name": "Standard_GRS"
      },
      "kind": "StorageV2",
      "properties": {
        "minimumTlsVersion": "TLS1_2",
        "supportsHttpsTrafficOnly": true,
        "allowBlobPublicAccess": false,
        "networkAcls": {
          "defaultAction": "Deny",
          "bypass": "AzureServices"
        },
        "encryption": {
          "services": {
            "blob": { "enabled": true },
            "file": { "enabled": true }
          },
          "keySource": "Microsoft.Keyvault",
          "keyVaultProperties": {
            "keyName": "storage-encryption-key",
            "keyVaultUri": "[concat('https://', parameters('environmentName'), '-kv.vault.azure.net/')]"
          }
        }
      }
    }
  ],
  "outputs": {
    "keyVaultUri": {
      "type": "string",
      "value": "[reference(resourceId('Microsoft.KeyVault/vaults', concat(parameters('environmentName'), '-kv'))).vaultUri]"
    }
  }
}
```

---

## 4. GCP Security

### 4.1 IAM and Service Accounts

No GCP, o IAM é baseado em hierarquia de recursos: Organization > Folder > Project > Resource. Cada nível pode herdar ou sobrescrever permissões.

```yaml
# Terraform - Service Account segura
resource "google_service_account" "app_service" {
  account_id   = "app-service"
  display_name = "Application Service Account"
  description  = "Service account para aplicacao em producao"
}

# Apenas as permissoes necessarias
resource "google_project_iam_member" "app_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

# Workload Identity para GKE
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.app_service.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[default/app]"
}
```

### 4.2 GCS Bucket Security

```yaml
resource "google_storage_bucket" "secure_bucket" {
  name          = "${var.project_id}-secure-data"
  location      = "US"
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  logging {
    log_bucket        = google_storage_bucket.access_logs.name
    log_object_prefix = "access-logs/"
  }

  labels = {
    environment = "production"
    security    = "high"
  }
}

# Impedir acesso publico via IAM
resource "google_storage_bucket_iam_binding" "public_access_block" {
  bucket = google_storage_bucket.secure_bucket.name
  role   = "roles/storage.objectViewer"
  members = []  # Nenhum membro - impede acesso publico
}
```

### 4.3 Cloud Functions Security

```yaml
resource "google_cloudfunctions2_function" "secure_function" {
  name        = "secure-function"
  location    = var.region
  description = "Cloud Function segura"

  build_config {
    runtime     = "python311"
    entry_point = "main"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    available_memory      = "256M"
    timeout_seconds       = 60
    service_account_email = google_service_account.function_sa.email
    vpc_connector         = google_vpc_access_connector.connector.id
    vpc_connector_egress_settings = "PRIVATE_RANGES_ONLY"
  }
}

# Service Account com permissao minima
resource "google_service_account" "function_sa" {
  account_id   = "function-sa"
  display_name = "Cloud Function Service Account"
}

resource "google_project_iam_member" "function_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.function_sa.email}"
}
```

### 4.4 Complete Terraform for Secure GCP

```yaml
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC com subnets privadas
resource "google_compute_network" "main" {
  name                    = "main-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name          = "private-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.main.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud NAT para acesso a internet
resource "google_compute_router" "router" {
  name    = "cloud-router"
  network = google_compute_network.main.name
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  name                               = "cloud-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall - negar tudo por padrao
resource "google_compute_firewall" "deny_all" {
  name    = "deny-all-ingress"
  network = google_compute_network.main.name

  direction = "INGRESS"
  priority  = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

# KMS para encriptacao
resource "google_kms_key_ring" "main" {
  name     = "main-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "storage" {
  name            = "storage-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s"  # 90 dias

  lifecycle {
    prevent_destroy = true
  }
}

# Cloud SQL segura
resource "google_sql_database_instance" "main" {
  name             = "production-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-custom-2-8192"

    disk_encryption_configuration {
      kms_key_name = google_kms_crypto_key.sql.id
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
    }

    backup_configuration {
      enabled          = true
      start_time       = "03:00"
      point_in_time_recovery_enabled = true
    }

    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }

    database_flags {
      name  = "log_connections"
      value = "on"
    }

    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }

  deletion_protection = true
}

# Security Command Center
resource "google_security_center_notification_config" "main" {
  config_id    = "high-severity-alerts"
  organization = var.organization_id

  pubsub_topic = google_pubsub_topic.security_findings.id

  filtering = "severity = \"HIGH\" OR severity = \"CRITICAL\""
}

resource "google_pubsub_topic" "security_findings" {
  name = "security-findings"
}
```

---

## 5. Cloud Security Posture Management (CSPM)

### 5.1 AWS Config Rules

```yaml
# Regras de conformidade
resource "aws_config_config_rule" "s3_bucket_encryption" {
  name = "s3-bucket-server-side-encryption-enabled"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "rds_encryption" {
  name = "rds-storage-encrypted"

  source {
    owner             = "AWS"
    source_identifier = "RDS_STORAGE_ENCRYPTED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "sg_open_to_rdp" {
  name = "restricted-ssh"

  source {
    owner             = "AWS"
    source_identifier = "INCOMING_SSH_DISABLED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_config_rule" "iam_no_user_policies" {
  name = "iam-user-no-policies-check"

  source {
    owner             = "AWS"
    source_identifier = "IAM_USER_NO_POLICIES_CHECK"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

# Custom rule com Lambda
resource "aws_config_config_rule" "custom_s3_check" {
  name = "s3-custom-security-check"

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = aws_lambda_function.config_s3_check.arn

    source_detail {
      message_type = "ConfigurationItemChangeNotification"
    }
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_lambda_permission" "config_s3_check" {
  statement_id  = "AllowConfigInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.config_s3_check.function_name
  principal     = "config.amazonaws.com"
}
```

### 5.2 Azure Policy

```yaml
# Policy para exigir encriptacao
resource "azurerm_policy_definition" "require_encryption" {
  name         = "require-storage-encryption"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Exigir encriptacao em Storage Accounts"

  policy_rule = jsonencode({
    if = {
      allOf = [
        {
          field = "type"
          equals = "Microsoft.Storage/storageAccounts"
        }
      ]
    }
    then = {
      effect = "deny"
      details = {
        message = "Storage Accounts devem ter encriptacao habilitada"
      }
    }
  })
}

# Policy para bloquear IPs publicos
resource "azurerm_policy_definition" "block_public_ip" {
  name         = "block-public-ip"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Bloquear IP Publico em VMs"

  policy_rule = jsonencode({
    if = {
      allOf = [
        {
          field = "type"
          equals = "Microsoft.Network/publicIPAddresses"
        }
      ]
    }
    then = {
      effect = "deny"
    }
  })
}
```

### 5.3 GCP Security Command Center

```yaml
# SCC Notification Config
resource "google_security_center_notification_config" "main" {
  config_id    = "production-alerts"
  organization = var.organization_id

  pubsub_topic = google_pubsub_topic.security_findings.id

  filtering = "severity = \"HIGH\" OR severity = \"CRITICAL\""

  event_config {
    resource_types = [
      "google.compute.Firewall",
      "google.storage.Bucket",
      "google.cloudsql.Instance",
      "google.compute.Instance"
    ]
  }
}

# Custom SCC Findings via API
resource "google_cloudfunctions2_function" "scc_finding_creator" {
  name        = "scc-finding-creator"
  location    = var.region

  build_config {
    runtime     = "python311"
    entry_point = "create_finding"
    source {
      storage_source {
        bucket = google_storage_bucket.functions_bucket.name
        object = google_storage_bucket_object.scc_function.name
      }
    }
  }

  service_config {
    service_account_email = google_service_account.scc_sa.email
  }
}
```

### 5.4 Third-party CSPM Tools

Ferramentas CSPM de terceiros oferecem visibilidade multi-cloud e capacidades avançadas de detecção de ameaças:

- **Prisma Cloud (Palo Alto):** Proteção completa em AWS, Azure e GCP
- **Wiz:** Análise agentless, graph-based, sem impacto em performance
- **Lacework:** Foco em anomalias de comportamento e machine learning
- **Orca Security:** SideScanning, visão unificada de segurança
- **Snyk Cloud:** Foco em desenvolvedores e IaC

**Configuracao tipica de integração CSPM:**

```yaml
# Exemplo: Service Account para ferramenta CSPM
resource "google_project_iam_member" "cspm_reader" {
  for_each = toset([
    "roles/cloudsecurityscanner.viewer",
    "roles/cloudasset.viewer",
    "roles/securitycenter.admin",
    "roles/viewer"
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${var.cspm_service_account}"
}

# Exemplo: Role IAM para ferramenta CSPM no AWS
resource "aws_iam_role" "cspm_role" {
  name = "cspm-security-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = var.cspm_aws_account_arn
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = var.cspm_external_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cspm_security_audit" {
  role       = aws_iam_role.cspm_role.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}
```

---

## 6. Cloud Workload Protection

### 6.1 Container Security in Cloud

```yaml
# Pod Security Standards (Kubernetes)
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
# Security Context para Pods
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 3000
        fsGroup: 2000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: api
          image: empresa/api-server:v1.0.0
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          resources:
            limits:
              cpu: "500m"
              memory: "256Mi"
            requests:
              cpu: "250m"
              memory: "128Mi"
          ports:
            - containerPort: 8080
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
```

### 6.2 Serverless Security

```python
# Exemplo de Lambda segura
import os
import json
import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    """
    Handler de exemplo com praticas de seguranca.
    """
    # 1. Validação de entrada
    if not validate_event(event):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid input'})
        }
    
    # 2. Uso de variaveis de ambiente para credenciais
    db_host = os.environ.get('DB_HOST')
    api_key = os.environ.get('API_KEY')
    
    if not db_host or not api_key:
        raise ValueError("Missing required environment variables")
    
    # 3. Chamadas seguras a AWS services
    try:
        client = boto3.client('dynamodb')
        response = client.get_item(
            TableName=os.environ.get('TABLE_NAME'),
            Key={'id': {'S': event['pathParameters']['id']}},
            ConsistentRead=True
        )
    except ClientError as e:
        print(f"DynamoDB error: {e.response['Error']['Code']}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal error'})
        }
    
    # 4. Resposta sem expor dados sensiveis
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        },
        'body': json.dumps({'data': 'response'})
    }

def validate_event(event):
    """Valida e sanitiza entrada."""
    required = ['pathParameters', 'httpMethod']
    return all(k in event for k in required)
```

### 6.3 VM Agent-based Protection

```yaml
# Cloud Security Agent Configuration
# Exemplo: AWS Systems Manager Agent
resource "aws_ssm_association" "security_baseline" {
  name = "AWS-RunPatchBaseline"

  schedule_expression = "rate(7 days)"

  targets {
    key    = "tag:Environment"
    values = ["production"]
  }

  parameters = {
    Operation    = ["Scan"]
    RebootOption = ["RebootIfNeeded"]
  }
}

# CloudWatch Agent para monitoramento de seguranca
resource "aws_ssm_parameter" "cloudwatch_config" {
  name  = "AmazonCloudWatch-linux-security"
  type  = "String"
  value = jsonencode({
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path = "/var/log/secure"
              log_group_name = "/var/log/secure"
              log_stream_name = "{instance_id}"
              timestamp_format = "%Y-%m-%d %H:%M:%S"
              multi_line_start_pattern = "^\\w{3}\\s+\\d+"
            },
            {
              file_path = "/var/log/audit/audit.log"
              log_group_name = "/var/log/audit"
              log_stream_name = "{instance_id}"
            }
          ]
        }
      }
    }
    metrics = {
      namespace = "SecurityAgent"
      metrics_collected = {
        disk = {
          metrics_collection_interval = 60
          resources = ["*"]
        }
        mem = {
          metrics_collection_interval = 60
        }
      }
    }
  })
}
```

---

## 7. Network Security in Cloud

### 7.1 Security Groups and NACLs

```yaml
# Security Group - camada de instancia (stateful)
resource "aws_security_group" "app_tier" {
  name        = "app-tier-sg"
  description = "Security group para camada de aplicacao"
  vpc_id      = aws_vpc.main.id

  # Entrada: apenas do ALB
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Trafego do ALB"
  }

  # Saida: apenas para o banco de dados
  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.database.id]
    description     = "PostgreSQL"
  }

  # Saida: apenas HTTPS para APIs externas
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS externo"
  }
}

# NACL - camada de subnet (stateless)
resource "aws_network_acl" "private" {
  vpc_id = aws_vpc.main.id

  # Regras de entrada
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "10.0.0.0/16"
    from_port  = 8080
    to_port    = 8080
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 200
    action     = "allow"
    cidr_block = "10.0.0.0/16"
    from_port  = 1024
    to_port    = 65535
  }

  ingress {
    protocol   = "tcp"
    rule_no    = 300
    action     = "allow"
    cidr_block = "10.0.10.0/24"
    from_port  = 22
    to_port    = 22
  }

  # Negar tudo mais
  ingress {
    protocol   = "all"
    rule_no    = 999
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  # Saida: permitir tudo (NACLs sao stateless)
  egress {
    protocol   = "all"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "private-nacl"
  }
}
```

### 7.2 VPC Design Patterns

```yaml
# Hub and Spoke com Transit Gateway
resource "aws_ec2_transit_gateway" "main" {
  description = "Production Transit Gateway"

  default_association_route_table_id = aws_ec2_transit_gateway_route_table.main.id

  tags = {
    Name = "production-tgw"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "hub" {
  vpc_id             = aws_vpc.hub.id
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  subnet_ids         = aws_subnet.hub_transit[*].id
}

resource "aws_ec2_transit_gateway_vpc_attachment" "spoke" {
  count              = 3
  vpc_id             = aws_vpc.spoke[count.index].id
  transit_gateway_id = aws_ec2_transit_gateway.main.id
  subnet_ids         = aws_subnet.spoke_transit[count.index][*].id
}

# Seguranca: TGW Route Table com filtros
resource "aws_ec2_transit_gateway_route_table" "main" {
  transit_gateway_id = aws_ec2_transit_gateway.main.id

  tags = {
    Name = "production-rt"
  }
}

# NAO permitir comunicacao direta entre spokes
# Cada spoke deve passar pelo hub para inspecao de seguranca
```

### 7.3 Private Endpoints

```yaml
# VPC Endpoint para S3 (Gateway)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.region}.s3"

  route_table_ids = [
    aws_route_table.private.id
  ]
}

# VPC Endpoint para DynamoDB (Gateway)
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.region}.dynamodb"

  route_table_ids = [
    aws_route_table.private.id
  ]
}

# VPC Endpoint para SSM (Interface)
resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true
}

resource "aws_security_group" "vpc_endpoints" {
  name        = "vpc-endpoints-sg"
  description = "SG para VPC Endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }
}
```

### 7.4 WAF Configuration

```yaml
resource "aws_wafv2_web_acl" "main" {
  name        = "production-waf"
  description = "WAF para producao"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Regra: AWS Managed Rules - Common Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "CommonRuleSet"
      sampled_requests_enabled  = true
    }
  }

  # Regra: SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "SQLiRuleSet"
      sampled_requests_enabled  = true
    }
  }

  # Regra: Rate Limiting
  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRule"
      sampled_requests_enabled  = true
    }
  }

  # Regra: Geoblocking
  rule {
    name     = "GeoBlockRule"
    priority = 4

    action {
      block {}
    }

    statement {
      geo_match_statement {
        country_codes = ["CN", "RU", "KP"]
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "GeoBlockRule"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "production-waf"
    sampled_requests_enabled  = true
  }
}

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}
```

---

## 8. Data Protection

### 8.1 Encryption at Rest

```yaml
# KMS Key com rotacao automatica
resource "aws_kms_key" "main" {
  description             = "Chave principal de encriptacao"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowRootAccount"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowKeyAdministration"
        Effect    = "Allow"
        Principal = { AWS = aws_iam_role.key_admin.arn }
        Action = [
          "kms:Create*",
          "kms:Describe*",
          "kms:Enable*",
          "kms:List*",
          "kms:Put*",
          "kms:Update*",
          "kms:Revoke*",
          "kms:Disable*",
          "kms:Get*",
          "kms:Delete*",
          "kms:ScheduleKeyDeletion",
          "kms:CancelKeyDeletion"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/production"
  target_key_id = aws_kms_key.main.key_id
}

# EBS encryption por padrao
resource "aws_ebs_encryption_by_default" "main" {
  enabled = true
}

# S3 Bucket com encriptacao
resource "aws_s3_bucket" "encrypted" {
  bucket = "encrypted-bucket-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encrypted" {
  bucket = aws_s3_bucket.encrypted.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
    bucket_key_enabled = true
  }
}
```

### 8.2 Encryption in Transit

```yaml
# ALB com TLS 1.3
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Redirect HTTP para HTTPS
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# RDS com SSL obrigatorio
resource "aws_db_instance" "main" {
  # ... configuracao base ...
  
  # Forcar SSL
  iam_database_authentication_enabled = true
  
  # Criptografia em repouso
  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn

  # Backup criptografado
  backup_encrypted = true
}
```

### 8.3 Key Management in Cloud

```python
# Exemplo: rotacao automatica de chaves
import boto3
from datetime import datetime, timedelta

class KeyRotationManager:
    def __init__(self, region='us-east-1'):
        self.kms = boto3.client('kms', region_name=region)
    
    def rotate_key(self, key_id):
        """Forca rotacao de chave KMS."""
        try:
            self.kms.rotate_key(KeyId=key_id)
            print(f"Key {key_id} rotated successfully")
            return True
        except Exception as e:
            print(f"Error rotating key: {e}")
            return False
    
    def check_rotation_status(self, key_id):
        """Verifica status de rotacao."""
        response = self.kms.get_key_rotation_status(KeyId=key_id)
        return response['KeyRotationEnabled']
    
    def list_keys_needing_rotation(self, max_age_days=365):
        """Lista chaves que precisam de rotacao."""
        keys = self.kms.list_keys()['Keys']
        old_keys = []
        
        for key in keys:
            try:
                key_metadata = self.kms.describe_key(KeyId=key['KeyId'])
                creation_date = key_metadata['KeyMetadata']['CreationDate']
                
                if datetime.now(creation_date.tzinfo) - creation_date > timedelta(days=max_age_days):
                    old_keys.append(key['KeyId'])
            except:
                continue
        
        return old_keys
```

### 8.4 Backup Security

```yaml
# Backup Plan com encriptacao
resource "aws_backup_vault" "main" {
  name        = "production-vault"
  kms_key_arn = aws_kms_key.backup.arn

  tags = {
    Environment = "production"
  }
}

resource "aws_backup_plan" "main" {
  name = "production-backup-plan"

  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 2 * * ? *)"

    lifecycle {
      delete_after = 35
    }

    copy_action {
      destination_vault_arn = aws_backup_vault.cross_region.arn
      lifecycle {
        delete_after = 90
      }
    }
  }

  rule {
    rule_name         = "monthly-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 3 1 * ? *)"

    lifecycle {
      delete_after = 365
    }
  }
}

resource "aws_backup_selection" "main" {
  name         = "production-selection"
  plan_id      = aws_backup_plan.main.id
  iam_role_arn = aws_iam_role.backup.arn

  resources = [
    aws_db_instance.main.arn,
    aws_s3_bucket.encrypted.arn
  ]

  condition {
    string_equals {
      key   = "aws:ResourceTag/Backup"
      value = "true"
    }
  }
}
```

---

## 9. Cloud Logging and Monitoring

### 9.1 CloudTrail / Activity Log / Audit Log

```yaml
# CloudTrail multi-region com validacao
resource "aws_cloudtrail" "main" {
  name                          = "production-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.cloudtrail.arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::"]
    }

    data_resource {
      type   = "AWS::Lambda::Function"
      values = ["arn:aws:lambda"]
    }
  }

  insight_selector {
    insight_type = "ApiCallRateInsight"
  }

  insight_selector {
    insight_type = "ApiErrorRateInsight"
  }
}

# S3 bucket para logs com lifecycle
resource "aws_s3_bucket" "cloudtrail" {
  bucket = "cloudtrail-logs-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  rule {
    id     = "archive-and-expire"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
```

### 9.2 SIEM Integration

```python
# Integracao com SIEM via AWS Security Hub
import boto3
import json

class SIEMIntegration:
    def __init__(self):
        self.securityhub = boto3.client('securityhub')
        self.events = []
    
    def send_finding(self, title, severity, description, resources):
        """Envia finding para Security Hub."""
        finding = {
            'SchemaVersion': '2018-10-08',
            'Id': f"{title}-{hash(title)}",
            'ProductArn': 'arn:aws:securityhub:::product/custom/siem',
            'GeneratorId': 'SIEM-Integration',
            'AwsAccountId': boto3.client('sts').get_caller_identity()['Account'],
            'Types': ['Software and Configuration Checks'],
            'CreatedAt': datetime.utcnow().isoformat() + 'Z',
            'UpdatedAt': datetime.utcnow().isoformat() + 'Z',
            'Severity': {'Label': severity},
            'Title': title,
            'Description': description,
            'Resources': resources,
            'Compliance': {
                'Status': 'FAILED'
            }
        }
        
        self.events.append(finding)
    
    def batch_send(self):
        """Envia findings em lote."""
        if self.events:
            self.securityhub.batch_import_findings(Findings=self.events[:100])
            sent = len(self.events[:100])
            self.events = self.events[100:]
            return sent
        return 0

# Exemplo de uso
siem = SIEMIntegration()
siem.send_finding(
    title='S3 Bucket Public',
    severity='CRITICAL',
    description='S3 bucket found with public access',
    resources=[{
        'Type': 'AwsS3Bucket',
        'Id': 'arn:aws:s3:::public-bucket',
        'Region': 'us-east-1'
    }]
)
siem.batch_send()
```

### 9.3 Alert Configurations

```yaml
# CloudWatch Alarm para atividade suspeita
resource "aws_cloudwatch_metric_alarm" "root_login" {
  alarm_name          = "root-user-login"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RootUserLogin"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Root user logged in"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "unauthorized_api" {
  alarm_name          = "unauthorized-api-calls"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "AuthorizationFailures"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Multiple unauthorized API calls"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "console_login_mfa_disabled" {
  alarm_name          = "console-login-no-mfa"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ConsoleLoginWithoutMFA"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Console login without MFA"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
}

# SNS Topic para alertas
resource "aws_sns_topic" "security_alerts" {
  name = "security-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "email"
  endpoint  = "security@empresa.com"
}

resource "aws_sns_topic_subscription" "pagerduty" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "https"
  endpoint  = "https://events.pagerduty.com/integration/xxx/enqueue"
}
```

---

## 10. Exemplo Completo: Secure Cloud Deployment

### 10.1 Multi-account Strategy

```yaml
# AWS Organizations
resource "aws_organizations_organization" "main" {
  feature_set = "ALL"

  aws_service_access_principals = [
    "cloudtrail.amazonaws.com",
    "config.amazonaws.com",
    "guardduty.amazonaws.com",
    "sso.amazonaws.com",
    "securityhub.amazonaws.com"
  ]

  enabled_policy_types = [
    "SERVICE_CONTROL_POLICY",
    "TAG_POLICY"
  ]
}

# OU de Producao
resource "aws_organizations_ou" "production" {
  name      = "Production"
  parent_id = aws_organizations_organization.main.roots[0].id
}

# SCP para negar acesso root
resource "aws_organizations_policy" "deny_root" {
  name        = "DenyRootAccess"
  description = "Impedir acesso root"
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyRoot"
      Effect    = "Deny"
      Action    = "*"
      Resource  = "*"
      Condition = {
        StringLike = {
          "aws:PrincipalArn" = "arn:aws:iam::*:root"
        }
      }
    }]
  })
}

# SCP para forcar MFA
resource "aws_organizations_policy" "require_mfa" {
  name        = "RequireMFA"
  description = "Exigir MFA para todas as contas"
  type        = "SERVICE_CONTROL_POLICY"

  content = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "EnforceMFA"
      Effect    = "Deny"
      Action    = "*"
      Resource  = "*"
      Condition = {
        BoolIfExists = {
          "aws:MultiFactorAuthPresent" = "false"
        }
      }
    }]
  })
}

resource "aws_organizations_policy_attachment" "deny_root_prod" {
  policy_id = aws_organizations_policy.deny_root.id
  target_id = aws_organizations_ou.production.id
}

resource "aws_organizations_policy_attachment" "require_mfa_all" {
  policy_id = aws_organizations_policy.require_mfa.id
  target_id = aws_organizations_organization.main.roots[0].id
}
```

### 10.2 Complete Terraform with Security

```yaml
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-seguro"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# Variaveis
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "environment" {
  type    = string
  default = "production"
}

# VPC Segura
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "production-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b", "${var.region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Flow logs para auditoria
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_iam_role             = true
  flow_log_max_aggregation_interval    = 60

  tags = {
    Environment = var.environment
    Security    = "high"
  }
}

# Security Hub
resource "aws_securityhub_account" "main" {
  enable_default_standards = true
}

# GuardDuty
resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
  }
}

# Config Rules
resource "aws_config_configuration_recorder" "main" {
  name     = "recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_config_rule" "s3_public_read" {
  name = "s3-bucket-public-read-prohibited"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }

  depends_on = [aws_config_configuration_recorder.main]
}
```

### 10.3 CI/CD Pipeline for Cloud Deployment

```yaml
# .github/workflows/secure-deploy.yml
name: Secure Cloud Deployment

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1

jobs:
  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: terraform/
          framework: terraform
          soft_fail: false

      - name: Run tfsec
        uses: aquasecurity/tfsec-action@v1.0.3
        with:
          working_directory: terraform/

  deploy-staging:
    name: Deploy to Staging
    needs: security-scan
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.5.0"

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Plan
        run: terraform plan -var-file=staging.tfvars -out=tfplan
        working-directory: terraform/

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: terraform/

  deploy-production:
    name: Deploy to Production
    needs: security-scan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_PROD_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.5.0"

      - name: Terraform Init
        run: terraform init
        working-directory: terraform/

      - name: Terraform Plan
        run: terraform plan -var-file=production.tfvars -out=tfplan
        working-directory: terraform/

      - name: Manual Approval
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ secrets.GITHUB_TOKEN }}
          minimum-approvals: 2

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: terraform/
```

---

## 11. Referências

### Documentacao Oficial

1. AWS Well-Architected Framework - Security Pillar
2. Microsoft Azure Security Best Practices and Patterns
3. Google Cloud Security Best Practices
4. AWS IAM Best Practices
5. Azure Security Benchmark
6. Google Cloud Security Command Center Documentation

### Casos Documentados

7. Capital One Data Breach (2019) - AWS Post-Incident Summary
8. Twitch Data Leak (2021) - Twitch Blog Postmortem
9. Microsoft Azure CosmosDB Vulnerability (2021) - Wiz Research
10. AWS S3 Bucket Security Incidents (2017-2024)
11. Google Cloud Project Misconfigurations - Orca Security Research
12. Uber Cloud Credential Leak (2022) - BleepingComputer Report

### Frameworks e Padroes

13. CIS Benchmarks para AWS, Azure e GCP
14. NIST Cybersecurity Framework
15. Cloud Security Alliance (CSA) Cloud Controls Matrix
16. ISO/IEC 27017:2015 - Cloud Security Controls
17. SOC 2 Type II para Cloud Service Providers

### Ferramentas

18. Terraform AWS/Azure/GCP Providers
19. Checkov - Infrastructure as Code Security Scanner
20. tfsec - Terraform Security Scanner
21. Prowler - AWS Security Assessment
22. ScoutSuite - Multi-Cloud Security Auditing
23. CloudSploit - Cloud Security Posture Management

### Artigos e Publicacoes

24. OWASP Cloud Security Project
25. ENISA Cloud Computing Security Risk Assessment
26. Gartner Cloud Security Posture Management Market Guide
27. Forrester Cloud Security Strategy Report

---

**Status**: success
**Summary**: Arquivo 11-seguranca-cloud.md criado com 866 linhas, cobrindo todos os 11 topicos solicitados incluindo os 6 casos documentados de seguranca em cloud.

**Files touched**: /home/Projetos/DevSecurity/devsecops/11-seguranca-cloud.md
**Findings worth promoting**: 
- O Shared Responsibility Model e a causa raiz da maioria das violacoes em cloud
- Casos documentados (Capital One, Twitch, Azure CosmosDB, AWS S3, GCP, Uber) demonstram padroes repetidos de falhas
- IAM e a camada mais critica de seguranca em qualquer provedor cloud
- CSPM, CWPP e WAF sao componentes essenciais de uma estrategia de seguranca em cloud