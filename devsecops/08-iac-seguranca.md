# Capítulo 8 — Infrastructure as Code: Segurança

## Sumario

1. IaC e Seguranca
2. Terraform Seguro
3. Checkov
4. tfsec
5. Ansible Seguro
6. CloudFormation Security
7. Pulumi Security
8. Kubernetes IaC Security
9. State File Security
10. Exemplo Completo: IaC Security Pipeline
11. Referencias

---

## 1. IaC e Seguranca

### 1.1 Por Que IaC Transforma a Seguranca

Infrastructure as Code (IaC) nao e apenas uma ferramenta de automacao — ela representa uma mudanca fundamental na forma como pensamos sobre seguranca de infraestrutura. Quando a infraestrutura e declarada em codigo, ela herda todas as capacidades do ciclo de vida do software: versionamento, revisao, testes automatizados e auditoria completa.

Antes do IaC, configuracoes de infraestrutura eram documentadas em wikis, spreadsheets ou simplesmente na memoria de quem as configurava. Um administrador conectava-se via SSH a um servidor, editava arquivos de configuracao manualmente e rezava para que nenhuma mudanca indevida passasse despercebida. Hoje, cada recurso — cada VPC, cada bucket S3, cada instancia EC2 — e descrito em um arquivo de texto que pode ser revisado, versionado e validado automaticamente.

No entanto, essa transformacao traz novos vetores de ataque. O codigo de infraestrutura se torna o proprio ativo a ser protegido. Se um atacante conseguir injetar codigo malicioso em um arquivo Terraform, ele pode provisionar recursos perigosos, abrir portas de acesso ou drenar dados de buckets S3 sem que ninguem perceba imediatamente.

### 1.2 Superficie de Ataque do IaC

A superficie de ataque em ambientes IaC abrange varios vetores criticos:

**Codigo-fonte**: Repositorios Git contendo definicoes de infraestrutura podem ser comprometidos. Um commit malicioso que altera uma regra de Security Group pode abrir portas sensíveis para a internet.

**Dependencias**: Providers e modulos de terceiros podem conter vulnerabilidades ou codigo malicioso. Um provider Terraform desatualizado pode conter CVEs conhecidos que permitem execucao remota de codigo.

**Dados de estado**: Arquivos de estado do Terraform contem informacoes sensiveis como IDs de recursos, valores de atributos e, em alguns casos, secrets que foram interpolados em configuracoes. Um estado exposto em um bucket S3 publico pode revelar toda a topologia da infraestrutura.

**Pipelines de CI/CD**: Um pipeline que aplica mudancas de infraestrutura sem os devidos controles de acesso e validacoes pode se tornar um vetor de ataque. Credenciais armazenadas em pipelines podem ser extraidas e usadas para acessar ambientes de producao.

**Secrets e credenciais**: Chaves de API, tokens de acesso e senhas injetados em configuracoes de infraestrutura representam um risco significativo se nao forem gerenciados adequadamente.

### 1.3 Seguranca do Arquivo de Estado

O arquivo de estado do Terraform (`terraform.tfstate`) e uma das piecas mais sensiveis de qualquer ambiente IaC. Ele contem o mapeamento entre as definicoes no codigo e os recursos reais na nuvem, incluindo atributos que podem conter dados sensiveis.

Um estado exposto pode revelar:

- Enderecos IP privados e configuracoes de rede
- Identificadores de recursos que podem ser explorados
- Valores interpolados que podem conter secrets nao criptografados
- Configuracoes de IAM e permissoes
- Dados de conexao de bancos de dados

### 1.4 Seguranca de Providers

Providers Terraform interagem diretamente com APIs de cloud providers e servicos externos. Um provider desatualizado pode conter vulnerabilidades que permitam:

- Execucao de codigo arbitrario
- Escalacao de privilegios
- Acesso nao autorizado a recursos
- Intercepsao de dados em transito

Manter providers atualizados e usar apenas providers de fontes confiaveis e uma pratica basica de seguranca que muitas equipes ignoram.

### 1.5 Caso Real: Capital One (2019)

Em julho de 2019, a Capital One sofreu um dos maiores vazamentos de dados da historia de instituicoes financeiras dos Estados Unidos. Um atacante exploraou uma configuracao incorreta no Web Application Firewall (WAF) da empresa para acessar dados de mais de 100 milhoes de clientes.

**O que aconteceu**: A Capital One estava usando servicos AWS e tinha configurado um WAF para proteger seus aplicativos. No entanto, uma configuracao incorreta de IAM (Identity and Access Management) permitiu que um atacante que ja tinha acesso a uma instancia EC2 acessasse metadados da instancia via Server-Side Request Forgery (SSRF). Com isso, o atacante assumiu um papel IAM que tinha permissao excessiva para acessar dados no S3.

**Vetor de ataque**: O atacante explorou uma vulnerabilidade de SSRF em um aplicativo web executado em uma instancia EC2. Atraves dessa vulnerabilidade, ele acessou o endpoint de metadados da instancia (169.254.169.254) e obteve as credenciais do papel IAM associado a instancia. Esse papel IAM tinha permissao para listar e baixar dados de buckets S3 que continham informacoes pessoais sensiveis.

**Dados comprometidos**: Nomes completos, enderecos, numeros de seguro social, numeros de conta bancaria e cartoes de credito de aproximadamente 100 milhoes de pessoas.

**Licoes de IaC**: Se a configuracao do WAF e do IAM tivessem sido definidas como codigo e validadas automaticamente, a permissao excessiva do papel IAM teria sido detectada antes da implantacao. Ferramentas como Checkov e tfsec teriam sinalizado a configuracao incorreta do WAF como uma violacao de seguranca.

**Configuracao perigosa (o que NAO se deve fazer)**:

```hcl
# CONFIGURACAO INSEGURA - NAO USE EM PRODUCAO
resource "aws_iam_role" "ec2_webapp_role" {
  name = "ec2-webapp-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Permissao excessiva - acesso a TODOS os buckets S3
resource "aws_iam_role_policy" "ec2_webapp_s3_policy" {
  name = "ec2-webapp-s3-policy"
  role = aws_iam_role.ec2_webapp_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:Get*",
        "s3:List*",
        "s3:Put*"
      ]
      Effect   = "Allow"
      Resource = "*"  # Perigoso: acesso irrestrito a todos os buckets
    }]
  })
}
```

**Configuracao corrigida**:

```hcl
# CONFIGURACAO SEGURO
resource "aws_iam_role" "ec2_webapp_role" {
  name = "ec2-webapp-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Condition = {
        StringEquals = {
          "aws:RequestedRegion" = "us-east-1"
        }
      }
    }]
  })

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Permissao com least privilege - acesso restrito ao bucket especifico
resource "aws_iam_role_policy" "ec2_webapp_s3_policy" {
  name = "ec2-webapp-s3-policy"
  role = aws_iam_role.ec2_webapp_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Effect = "Allow"
      Resource = [
        "arn:aws:s3:::my-webapp-data",
        "arn:aws:s3:::my-webapp-data/*"
      ]
    }]
  })
}
```

### 1.6 Caso Real: Vazamento de Arquivos de Estado Terraform

Varios incidentes publicos envolveram a exposicao indevida de arquivos de estado Terraform em buckets S3:

**Incidentes documentados**:

- Em 2020, pesquisadores de seguranca encontraram milhares de arquivos `terraform.tfstate` acessiveis publicamente em buckets S3. Muitos continham credenciais de banco de dados, chaves de API e tokens de acesso.

- Uma empresa de tecnologia teve seu ambiente AWS comprometido apos um arquivo de estado ser armazenado em um bucket S3 sem criptografia e com politicas de acesso publico. O arquivo continha credenciais de acesso a RDS que nao estavam rotacionadas.

- Um provedor de servicos financeiros expôs dados de configuracao de sua infraestrutura por meio de um estado Terraform publico, revelando a topologia completa da rede e endpoints internos.

**Como prevenir**:

```hcl
# Backend S3 configurado com seguranca
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"

    # Forcar uso de TLS 1.2+
    force_path_style = false
  }
}
```

**Politica de acesso ao bucket de estado**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowTerraformStateAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:role/TerraformExecutionRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::my-terraform-state-bucket/*"
    },
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::my-terraform-state-bucket/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::my-terraform-state-bucket",
        "arn:aws:s3:::my-terraform-state-bucket/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

---

## 2. Terraform Seguro

### 2.1 Praticas Fundamentais

Tornar o Terraform seguro envolve adotar praticas que protegem tanto o codigo quanto a infraestrutura que ele provisiona. Estas praticas formam a base de qualquer estrategia de seguranca para IaC:

1. **Least privilege**: Cada recurso Terraform deve ter apenas as permissoes estritamente necessarias
2. **Criptografia em repouso e em transito**: Todos os dados sensiveis devem ser criptografados
3. **Segregacao de ambientes**: Cada ambiente deve ter seu proprio estado e suas proprias credenciais
4. **Revisao de codigo**: Nenhuma mudanca de infraestrutura deve ser aplicada sem revisao humana
5. **Automacao de validacao**: Ferramentas de escaneamento devem rodar automaticamente no pipeline

### 2.2 VPC com Subnets Privadas

Uma VPC bem configurada e a base da seguranca de rede em qualquer ambiente cloud:

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "production-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false
  one_nat_gateway_per_az = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  # Habilitar flow logs para auditoria
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_iam_role             = true
  flow_log_max_aggregation_interval    = 60

  # Tags de seguranca
  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
    SecurityLevel = "high"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
}

# Network ACLs restrictivas
resource "aws_network_acl" "private" {
  vpc_id = module.vpc.vpc_id

  # Permitir trafego interno
  egress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "10.0.0.0/16"
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "10.0.0.0/16"
    from_port  = 0
    to_port    = 0
  }

  # Negar todo o resto
  egress {
    protocol   = -1
    rule_no    = 999
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  ingress {
    protocol   = -1
    rule_no    = 999
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "private-nacl"
  }
}
```

### 2.3 S3 com Criptografia e Bloqueio de Acesso Publico

```hcl
resource "aws_s3_bucket" "secure_bucket" {
  bucket = "my-secure-data-bucket"

  tags = {
    Environment = "production"
    DataClass   = "confidential"
  }
}

resource "aws_s3_bucket_versioning" "secure_bucket_versioning" {
  bucket = aws_s3_bucket.secure_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secure_bucket_encryption" {
  bucket = aws_s3_bucket.secure_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_key.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "secure_bucket_pab" {
  bucket = aws_s3_bucket.secure_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "secure_bucket_lifecycle" {
  bucket = aws_s3_bucket.secure_bucket.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

resource "aws_s3_bucket_policy" "secure_bucket_policy" {
  bucket = aws_s3_bucket.secure_bucket.id

  depends_on = [aws_s3_bucket_public_access_block.secure_bucket_pab]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.secure_bucket.arn,
          "${aws_s3_bucket.secure_bucket.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "DenyUnencryptedUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.secure_bucket.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid       = "RestrictToVPCEndpoint"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.secure_bucket.arn,
          "${aws_s3_bucket.secure_bucket.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:sourceVpce" = "vpce-1234567890abcdef0"
          }
        }
      }
    ]
  })
}

resource "aws_kms_key" "s3_key" {
  description             = "KMS key for S3 bucket encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnableRootAccountAccess"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = {
    Purpose = "s3-encryption"
  }
}
```

### 2.4 RDS com Criptografia e Controle de Acesso

```hcl
resource "aws_db_subnet_group" "secure_db_subnet" {
  name       = "secure-db-subnet-group"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Name = "Secure DB Subnet Group"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Security group for RDS instance"
  vpc_id      = module.vpc.vpc_id

  # Regra para permitir acesso apenas de subnets privadas
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
    description     = "PostgreSQL access from application SG"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "rds-security-group"
  }
}

resource "aws_db_instance" "secure_database" {
  identifier = "secure-production-db"

  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.rds_key.arn

  db_name  = "productiondb"
  username = "dbadmin"
  password = aws_secretsmanager_secret_version.db_password.secret_string

  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.secure_db_subnet.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  multi_az                = true
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "production-db-final-snapshot"

  performance_insights_enabled    = true
  monitoring_interval             = 60
  monitoring_role_arn            = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Environment = "production"
    DataClass   = "confidential"
  }
}

resource "aws_kms_key" "rds_key" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

# Gerenciamento seguro de senha do banco de dados
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}|:?"
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "production/database/password"
  recovery_window_in_days = 30
  kms_key_id             = aws_kms_key.rds_key.arn
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# Rotacao automatica de senha
resource "aws_secretsmanager_secret_rotation" "db_password_rotation" {
  secret_id           = aws_secretsmanager_secret.db_password.id
  rotation_lambda_arn = aws_lambda_function.secret_rotation.arn

  rotation_rules {
    automatically_after_days = 30
  }
}
```

### 2.5 IAM com Least Privilege

```hcl
# Politica base para todos os servicos
data "aws_iam_policy_document" "deny_insecure_transport" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:*"]
    resources = [
      "arn:aws:s3:::*",
      "arn:aws:s3:::*/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

# Role para aplicacao web com permissao minima
module "app_iam_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  name = "webapp-role"

  attach_vpc_cni_policy = false

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["default:webapp-sa"]
    }
  }

  role_policy_arns = {
    s3_read = aws_iam_policy.app_s3_read.arn
    secrets = aws_iam_policy.app_secrets_read.arn
  }
}

resource "aws_iam_policy" "app_s3_read" {
  name        = "webapp-s3-read"
  description = "Policy for webapp to read specific S3 bucket"

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
          "arn:aws:s3:::my-app-data",
          "arn:aws:s3:::my-app-data/*"
        ]
        Condition = {
          StringEquals = {
            "s3:ExistingObjectTag/Environment" = "production"
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "app_secrets_read" {
  name        = "webapp-secrets-read"
  description = "Policy for webapp to read application secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:*:*:secret:production/webapp/*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = "us-east-1"
          }
        }
      }
    ]
  })
}

# Role de assumcao restrita com MFA
resource "aws_iam_role" "breakglass_role" {
  name = "breakglass-admin"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      }
      Action = "sts:AssumeRole"
      Condition = {
        Bool = {
          "aws:MultiFactorAuthPresent" = "true"
        }
        NumericLessThan = {
          "aws:MultiFactorAuthAge" = "3600"
        }
      }
    }]
  })
}
```

### 2.6 Security Groups com Portas Minimas

```hcl
# Security Group para aplicacao web
resource "aws_security_group" "app_sg" {
  name        = "app-security-group"
  description = "Security group for web application"
  vpc_id      = module.vpc.vpc_id

  # Entrada: apenas HTTPS de ALB
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
    description     = "HTTPS from ALB"
  }

  # Saida: apenas para necessario
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound"
  }

  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds_sg.id]
    description     = "PostgreSQL to RDS"
  }

  tags = {
    Name = "app-security-group"
  }
}

# Security Group para ALB
resource "aws_security_group" "alb_sg" {
  name        = "alb-security-group"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id

  # Entrada: HTTP e HTTPS da internet
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from internet"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }

  # Saida: apenas para a aplicacao
  egress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
    description     = "HTTPS to application"
  }

  tags = {
    Name = "alb-security-group"
  }
}

# Security Group para banco de dados (acesso apenas via SG de app)
resource "aws_security_group" "rds_sg" {
  name        = "rds-security-group"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
    description     = "PostgreSQL from app"
  }

  tags = {
    Name = "rds-security-group"
  }
}

# Regra de egress padrao: negar tudo
# Os egress acima sao as unicas regras de saida permitidas
```

---

## 3. Checkov

### 3.1 Instalacao e Uso

Checkov e uma ferramenta de escaneamento de IaC desenvolvida pela Bridgecrew que verifica configuracoes contra politicas de seguranca pre-definidas. Suporta Terraform, CloudFormation, Kubernetes, Azure ARM e outros formatos.

**Instalacao**:

```bash
# Instalacao via pip
pip install checkov

# Instalacao via Docker
docker pull bridgecrew/checkov:latest

# Verificacao de versao
checkov --version
```

**Uso basico**:

```bash
# Escanear um diretorio Terraform
checkov -d .

# Escanear com direcionamento especifico
checkov -d . --framework terraform

# Escanear um unico arquivo
checkov -f main.tf

# Escanear apenas verificacoes especificas
checkov -d . --check CKV_AWS_18

# Escanear e excluir verificacoes especificas
checkov -d . --skip-check CKV_AWS_18

# Output em formato JSON
checkov -d . -o json

# Output em formato JUnit
checkov -d . -o junitxml
```

### 3.2 Frameworks Suportados

Checkov suporta diverse frameworks e linguagens:

| Framework | Tipo | Descricao |
|-----------|------|-----------|
| Terraform | AWS, Azure, GCP | Verificacoes de recursos cloud |
| CloudFormation | AWS | Templates AWS native |
| Kubernetes | YAML, JSON | Manifestos de deploy |
| Helm | Chart | Graficos Helm para K8s |
| Azure ARM | Azure | Templates ARM |
| Dockerfile | Docker | Imagens Docker |
| GitHub Actions | CI/CD | Workflows GitHub |
| Terraform Plan | AWS, Azure, GCP | Planos de execucao |

### 3.3 Politicas Customizadas em Python

Checkov permite criar politicas customizadas usando Python para validar regras especificas da sua organizacao:

```python
# custom_policies/check_s3_bucket_name.py
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck
from typing import Any, Dict, List


class S3BucketNameCompliance(BaseResourceCheck):
    """
    Verifica se o nome do bucket S3 segue o padrao corporativo.
    O nome deve comecar com o nome do ambiente e nao pode conter
    caracteres especiais alem de hifens.
    """

    def __init__(self) -> None:
        name = "S3BucketNameCompliance"
        id = "CKV_CUSTOM_1"
        supported_resources = ["aws_s3_bucket"]
        categories = [CheckCategories.GENERAL_SECURITY]
        super().__init__(name, id, categories)

    def scan_resource_conf(self, conf: Dict[str, List[Any]]) -> CheckResult:
        """
        Verifica se o nome do bucket S3 atende aos padroes de nomenclatura.
        """
        bucket_name = conf.get("bucket", [[]])

        if isinstance(bucket_name, list):
            if isinstance(bucket_name[0], list):
                bucket_name = bucket_name[0][0] if bucket_name[0] else ""
            else:
                bucket_name = bucket_name[0] if bucket_name else ""

        if not bucket_name:
            return CheckResult.FAILED

        # Regra 1: Deve comecar com nome do ambiente
        valid_prefixes = ["prod-", "staging-", "dev-", "sandbox-"]
        has_valid_prefix = any(bucket_name.startswith(prefix) for prefix in valid_prefixes)

        if not has_valid_prefix:
            return CheckResult.FAILED

        # Regra 2: Apenas hifens como caracteres especiais
        import re
        if re.search(r'[^a-z0-9-]', bucket_name):
            return CheckResult.FAILED

        # Regra 3: Comprimento maximo de 63 caracteres
        if len(bucket_name) > 63:
            return CheckResult.FAILED

        return CheckResult.PASSED


check = S3BucketNameCompliance()
```

```python
# custom_policies/check_ami_encryption.py
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck
from typing import Any, Dict, List


class AMIEncryptionCheck(BaseResourceCheck):
    """
    Verifica se AMIs usadas em instancias EC2 estao criptografadas.
    Previne uso de AMIs publicas que podem conter vulnerabilidades.
    """

    def __init__(self) -> None:
        name = "AMIEncryptionCheck"
        id = "CKV_CUSTOM_2"
        supported_resources = ["aws_instance"]
        categories = [CheckCategories.ENCRYPTION]
        super().__init__(name, id, categories)

    def scan_resource_conf(self, conf: Dict[str, List[Any]]) -> CheckResult:
        # Verificar se root_block_device esta configurado com criptografia
        root_block = conf.get("root_block_device", [])
        if isinstance(root_block, list) and len(root_block) > 0:
            if isinstance(root_block[0], dict):
                encrypted = root_block[0].get("encrypted", [])
                if isinstance(encrypted, list):
                    if encrypted[0] is True:
                        return CheckResult.PASSED

        return CheckResult.FAILED


check = AMIEncryptionCheck()
```

```python
# custom_policies/check_rds_backup.py
from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck
from typing import Any, Dict, List


class RDSBackupCheck(BaseResourceCheck):
    """
    Verifica se instancias RDS tem backup habilitado com retencao minima.
    Producoes devem ter pelo menos 7 dias de retencao de backup.
    """

    def __init__(self) -> None:
        name = "RDSBackupRetentionCheck"
        id = "CKV_CUSTOM_3"
        supported_resources = ["aws_db_instance"]
        categories = [CheckCategories.BACKUP_RECOVERY]
        super().__init__(name, id, categories)

    def scan_resource_conf(self, conf: Dict[str, List[Any]]) -> CheckResult:
        backup_retention = conf.get("backup_retention_period", [0])
        multi_az = conf.get("multi_az", [False])

        if isinstance(backup_retention, list):
            retention_days = int(backup_retention[0])
        else:
            retention_days = int(backup_retention)

        if isinstance(multi_az, list):
            is_multi_az = multi_az[0]
        else:
            is_multi_az = multi_az

        # Para producao (multi_az=True), exigir pelo menos 7 dias
        if is_multi_az and retention_days < 7:
            return CheckResult.FAILED

        # Para nao-producao, pelo menos 1 dia
        if retention_days < 1:
            return CheckResult.FAILED

        return CheckResult.PASSED


check = RDSBackupCheck()
```

### 3.4 Integracao com CI/CD

**Pipeline GitHub Actions com Checkov**:

```yaml
# .github/workflows/terraform-checkov.yml
name: Terraform Security Scan

on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'terraform/**'
      - '.terraform.lock.hcl'

jobs:
  checkov-scan:
    name: Checkov Security Scan
    runs-on: ubuntu-latest

    permissions:
      contents: read
      security-events: write
      pull-requests: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: terraform/
          framework: terraform
          output_format: sarif
          output_file_path: results.sarif
          soft_fail: false
          download_external_modules: true
          compact: true
          quiet: true
          log_level: WARNING

      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif

      - name: Checkov Results
        if: failure()
        run: |
          echo "Checkov found security issues!"
          echo "Review the SARIF report for details."
          exit 1
```

**Pipeline GitLab CI com Checkov**:

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - security
  - plan
  - apply

variables:
  TF_ROOT: terraform/
  TF_IN_AUTOMATION: "true"

checkov-scan:
  stage: security
  image:
    name: bridgecrew/checkov:latest
    entrypoint: [""]
  script:
    - cd $TF_ROOT
    - checkov -d . --output junitxml --output-file checkov-results.xml
    - checkov -d . --output sarif --output-file checkov-results.sarif
    - checkov -d . --compact --quiet --framework terraform
  artifacts:
    reports:
      junit: $TF_ROOT/checkov-results.xml
    paths:
      - $TF_ROOT/checkov-results.sarif
    expire_in: 30 days
  rules:
    - if: '$CI_MERGE_REQUEST_ID'
    - if: '$CI_COMMIT_BRANCH == "main"'
```

### 3.5 Pipeline Completo com Checkov

```bash
#!/bin/bash
# scripts/security-scan.sh
# Pipeline completa de seguranca para IaC

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TF_DIR="${PROJECT_ROOT}/terraform"
REPORT_DIR="${PROJECT_ROOT}/security-reports"

mkdir -p "$REPORT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Iniciando pipeline de seguranca para IaC ==="

# Fase 1: Formatacao
echo -e "\n--- Fase 1: Verificando formatacao ---"
if terraform fmt -check -recursive "$TF_DIR"; then
    echo -e "${GREEN}Formatacao OK${NC}"
else
    echo -e "${YELLOW}Corrigindo formatacao...${NC}"
    terraform fmt -recursive "$TF_DIR"
fi

# Fase 2: Inicializacao e validacao
echo -e "\n--- Fase 2: Validando Terraform ---"
cd "$TF_DIR"
terraform init -backend=false -input=false
terraform validate
cd "$PROJECT_ROOT"

# Fase 3: Checkov
echo -e "\n--- Fase 3: Executando Checkov ---"
checkov -d "$TF_DIR" \
    --output json \
    --output-file "$REPORT_DIR/checkov-results.json" \
    --compact \
    --quiet

checkov -d "$TF_DIR" \
    --output junitxml \
    --output-file "$REPORT_DIR/checkov-results.xml" \
    --compact \
    --quiet

# Fase 4: tfsec
echo -e "\n--- Fase 4: Executando tfsec ---"
tfsec "$TF_DIR" \
    --format json \
    --out "$REPORT_DIR/tfsec-results.json" \
    --minimum-severity MEDIUM

# Fase 5: Resumo
echo -e "\n=== Resumo da verificacao ==="

CHECKOV_ERRORS=$(jq '[.results.failed_checks | length] | .[0]' "$REPORT_DIR/checkov-results.json" 2>/dev/null || echo "0")
TFSEC_ERRORS=$(jq '[.results | length] | .[0]' "$REPORT_DIR/tfsec-results.json" 2>/dev/null || echo "0")

echo "Checkov violacoes: $CHECKOV_ERRORS"
echo "tfsec violacoes: $TFSEC_ERRORS"

if [ "$CHECKOV_ERRORS" -gt 0 ] || [ "$TFSEC_ERRORS" -gt 0 ]; then
    echo -e "${RED}Falha na verificacao de seguranca!${NC}"
    exit 1
else
    echo -e "${GREEN}Todas as verificacoes de seguranca passaram!${NC}"
fi
```

---

## 4. tfsec

### 4.1 Personalizacao de Regras

tfsec e uma ferramenta de analise de seguranca para Terraform desenvolvida pela Aqua Security. Ele verifica configuracoes contra regras de seguranca especificas para cada cloud provider.

**Instalacao**:

```bash
# Via Homebrew (macOS/Linux)
brew install tfsec

# Via Go
go install github.com/aquasecurity/tfsec/cmd/tfsec@latest

# Via Docker
docker run --rm -v "$(pwd):/workspace" aquasec/tfsec /workspace
```

### 4.2 Filtragem por Severidade

```bash
# Executar tfsec com nivel minimo de severidade
tfsec . --minimum-severity MEDIUM

# Excluir regras especificas
tfsec . --exclude aws-s3-enable-bucket-policy

# Incluir apenas regras de um modulo
tfsec . --include aws-s3

# Output em formato JSON para integracao
tfsec . --format json --out results.json

# Output em formato SARIF para GitHub
tfsec . --format sarif --out results.sarif

# Verificacao com detalhes
tfsec . --verbose

# Verificacao silenciosa (apenas falhas)
tfsec . --concise
```

### 4.3 Arquivo de Configuracao tfsec

```yaml
# .tfsec.yml
minimum_severity: MEDIUM

exclude:
  - aws-s3-enable-bucket-policy
  - aws-vpc-no-public-ingress-sgr

exclude_downloaded_modules: true

# Regras customizadas
custom_checks:
  - code: CUSTOM001
    description: "Verifica se todos os recursos tem tags obrigatorias"
    requiredTypes:
      - resource
    requiredLabels:
      - "*"
    severity: MEDIUM
    matchSpec:
      name: tags
      action: notEquals
      value: null
```

### 4.4 Integracao com CI/CD

**GitHub Actions**:

```yaml
# .github/workflows/tfsec.yml
name: tfsec

on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  tfsec:
    name: tfsec Security Analysis
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run tfsec
        uses: aquasecurity/tfsec-action@v1.0.3
        with:
          working_directory: terraform/
          soft_fail: false
          format: sarif
          sarif_file: tfsec-results.sarif

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: tfsec-results.sarif

      - name: Annotate PR
        uses: reviewdog/action-tfsec@v1
        if: always()
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          filter_mode: nofilter
          tfsec_args: --minimum-severity MEDIUM
          level: warning
```

**GitLab CI**:

```yaml
# .gitlab-ci.yml
tfsec:
  stage: security
  image:
    name: aquasec/tfsec:latest
    entrypoint: [""]
  script:
    - cd terraform/
    - tfsec . --format json --out ../tfsec-results.json --minimum-severity MEDIUM
    - tfsec . --format table
  artifacts:
    paths:
      - tfsec-results.json
    expire_in: 30 days
  rules:
    - if: '$CI_MERGE_REQUEST_ID'
```

---

## 5. Ansible Seguro

### 5.1 ansible-lint para Seguranca

O ansible-lint verifica playbooks Ansible contra padroes de seguranca e boas praticas:

```bash
# Instalacao
pip install ansible-lint

# Execucao basica
ansible-lint

# Verificacao especifica de seguranca
ansible-lint -x yaml[line-length] -t security

# Formato de saida
ansible-lint -f pep8
ansible-lint -f parsesable
ansible-lint -f json
```

**Arquivo de configuracao**:

```yaml
# .ansible-lint
profile: min

skip_list:
  - yaml[line-length]

warn_list:
  - experimental
  - yaml[truthy]

exclude_paths:
  - .cache/
  - .git/

# Regras de seguranca especificas
enable_list:
  - no-same-owner
  - secure-temp

# Configuracao de regras customizadas
mock_modules:
  - docker_container_info

mock_roles:
  - monitoring
```

### 5.2 Ansible Vault para Secrets

```yaml
# playbook-seguro.yml
---
- name: Configurar servidores de producao
  hosts: production
  become: true

  vars_files:
    - vars/secrets.yml  # Arquivo criptografado com ansible-vault

  vars:
    # Variaveis que devem ser gerenciadas via vault
    db_password: "{{ vault_db_password }}"
    api_key: "{{ vault_api_key }}"
    ssh_private_key: "{{ vault_ssh_private_key }}"

  tasks:
    - name: Configurar SSH com chaves
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ lookup('file', 'keys/deploy.pub') }}"
        state: present
        exclusive: true

    - name: Remover acesso SSH por senha
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^PasswordAuthentication'
        line: 'PasswordAuthentication no'
        state: present
      notify: restart sshd

    - name: Configurar firewall
      ansible.builtin.iptables:
        chain: INPUT
        in_interface: eth0
        protocol: tcp
        destination_port: "{{ item }}"
        jump: DROP
      loop:
        - 22
        - 3306
        - 5432
        - 6379
      when: ansible_default_ipv4.address != '10.0.0.0/8'

    - name: Garantir que servicos criticos nao estejam expostos
      ansible.builtin.lineinfile:
        path: "/etc/{{ item }}/bind.conf"
        regexp: "^\\s*bind-address"
        line: "bind-address 127.0.0.1"
      loop:
        - mysql
        - redis
      notify: "restart {{ item }}"

    - name: Configurar audit logging
      ansible.builtin.lineinfile:
        path: /etc/audit/rules.d/security.rules
        line: "{{ item }}"
        state: present
        create: true
        mode: '0640'
      loop:
        - "-w /etc/passwd -p wa -k identity"
        - "-w /etc/shadow -p wa -k identity"
        - "-w /etc/sudoers -p wa -k sudoers"
        - "-w /var/log/auth.log -p wa -k auth_log"
      notify: restart auditd

  handlers:
    - name: restart sshd
      ansible.builtin.systemd:
        name: sshd
        state: restarted

    - name: restart mysql
      ansible.builtin.systemd:
        name: mysql
        state: restarted

    - name: restart redis
      ansible.builtin.systemd:
        name: redis-server
        state: restarted

    - name: restart auditd
      ansible.builtin.systemd:
        name: auditd
        state: restarted
```

**Criptografando secrets**:

```bash
# Criptografar arquivo de secrets
ansible-vault create vars/secrets.yml

# Criptografar arquivo existente
ansible-vault encrypt vars/secrets.yml

# Descriptografar para edicao
ansible-vault edit vars/secrets.yml

# Executar playbook com vault
ansible-playbook playbook-seguro.yml --ask-vault-pass

# Usar arquivo de senha
ansible-playbook playbook-seguro.yml --vault-password-file ~/.vault_pass

# Verificar se criptografia esta funcionando
ansible-vault view vars/secrets.yml
```

### 5.3 Galaxy Security Scanning

```yaml
# requirements.yml
---
roles:
  - name: geerlingguy.docker
    version: "6.1.0"
    src: https://galaxy.ansible.com
    type: galaxy

  - name: geerlingguy.security
    version: "1.5.0"
    src: https://galaxy.ansible.com
    type: galaxy

collections:
  - name: ansible.posix
    version: ">=1.5.0"

  - name: community.general
    version: ">=7.0.0"
```

```bash
# Instalar roles e collections
ansible-galaxy install -r requirements.yml
ansible-galaxy collection install -r requirements.yml

# Verificar assinaturas
ansible-galaxy role list --verify
```

### 5.4 Playbook Seguro Completo

```yaml
# hardening-server.yml
---
- name: Hardening de servidor Linux
  hosts: all
  become: true

  vars:
    ssh_port: 2222
    allowed_users:
      - deploy
      - admin
    fail2ban_maxretry: 3
    fail2ban_bantime: 3600

  tasks:
    - name: Atualizar pacotes do sistema
      ansible.builtin.apt:
        upgrade: dist
        update_cache: true
        cache_valid_time: 3600
      when: ansible_os_family == "Debian"

    - name: Configurar SSH hardening
      ansible.builtin.lineinfile:
        path: /etc/ssh/sshd_config
        regexp: "{{ item.regexp }}"
        line: "{{ item.line }}"
        validate: '/usr/sbin/sshd -t -f %s'
      loop:
        - { regexp: '^#?Port', line: 'Port {{ ssh_port }}' }
        - { regexp: '^#?PermitRootLogin', line: 'PermitRootLogin no' }
        - { regexp: '^#?PasswordAuthentication', line: 'PasswordAuthentication no' }
        - { regexp: '^#?X11Forwarding', line: 'X11Forwarding no' }
        - { regexp: '^#?MaxAuthTries', line: 'MaxAuthTries 3' }
        - { regexp: '^#?Protocol', line: 'Protocol 2' }
        - { regexp: '^#?ClientAliveInterval', line: 'ClientAliveInterval 300' }
        - { regexp: '^#?ClientAliveCountMax', line: 'ClientAliveCountMax 2' }
      notify: restart sshd

    - name: Configurar PermitUsers
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^#?PermitUsers'
        line: 'PermitUsers {{ allowed_users | join(" ") }}'
      notify: restart sshd

    - name: Instalar e configurar fail2ban
      ansible.builtin.apt:
        name: fail2ban
        state: present

    - name: Configurar fail2ban jail
      ansible.builtin.template:
        src: templates/jail.local.j2
        dest: /etc/fail2ban/jail.local
        owner: root
        group: root
        mode: '0644'
      notify: restart fail2ban

    - name: Configurar iptables
      ansible.builtin.iptables:
        chain: INPUT
        in_interface: eth0
        protocol: tcp
        destination_port: "{{ item.port }}"
        jump: ACCEPT
        source: "{{ item.source }}"
      loop:
        - { port: '{{ ssh_port }}', source: '10.0.0.0/8' }
        - { port: '80', source: '0.0.0.0/0' }
        - { port: '443', source: '0.0.0.0/0' }

    - name: Bloquear todas as outras portas
      ansible.builtin.iptables:
        chain: INPUT
        in_interface: eth0
        jump: DROP

    - name: Configurar logrotate
      ansible.builtin.copy:
        content: |
          /var/log/auth.log {
            daily
            missingok
            rotate 90
            compress
            delaycompress
            notifempty
            create 0640 root adm
            postrotate
              /usr/lib/rsyslog/rsyslog-rotate
            endscript
          }
        dest: /etc/logrotate.d/auth-security
        owner: root
        group: root
        mode: '0644'

  handlers:
    - name: restart sshd
      ansible.builtin.systemd:
        name: sshd
        state: restarted

    - name: restart fail2ban
      ansible.builtin.systemd:
        name: fail2ban
        state: restarted
```

---

## 6. CloudFormation Security

### 6.1 cfn-nag

O cfn-nag verifica templates CloudFormation contra regras de seguranca:

```bash
# Instalacao
gem install cfn-nag

# Execucao basica
cfn_nag_scan --input-path templates/

# Com output especifico
cfn_nag_scan --input-path templates/ --output-format json

# Ignorar regras especificas
cfn_nag_scan --input-path templates/ --ignore-checks W92

# Verificar arquivos especificos
cfn_nag --input-path template.json
```

**Template CloudFormation seguro**:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Stack seguro com best practices de seguranca'

Parameters:
  EnvironmentName:
    Type: String
    AllowedValues:
      - production
      - staging
      - development

  DBPassword:
    Type: String
    NoEcho: true
    MinLength: 12
    Description: Senha do banco de dados (minimo 12 caracteres)

Resources:
  # S3 Bucket com seguranca
  SecureBucket:
    Type: 'AWS::S3::Bucket'
    Properties:
      BucketName: !Sub '${EnvironmentName}-secure-bucket'
      VersioningConfiguration:
        Status: Enabled
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: aws:kms
              KMSMasterKeyID: !Ref BucketKMSKey
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: TransitionToGlacier
            Status: Enabled
            Transitions:
              - StorageClass: GLACIER
                TransitionInDays: 90

  # KMS Key para criptografia
  BucketKMSKey:
    Type: 'AWS::KMS::Key'
    Properties:
      Description: !Sub 'KMS key for ${EnvironmentName} bucket'
      EnableKeyRotation: true
      KeyPolicy:
        Version: '2012-10-17'
        Statement:
          - Sid: EnableRootAccountAccess
            Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${AWS::AccountId}:root'
            Action: 'kms:*'
            Resource: '*'

  # Security Group
  AppSecurityGroup:
    Type: 'AWS::EC2::SecurityGroup'
    Properties:
      GroupDescription: Security group for application
      VpcId: !Ref VPCId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      SecurityGroupEgress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
      Tags:
        - Key: Name
          Value: !Sub '${EnvironmentName}-app-sg'

  # RDS Instance
  Database:
    Type: 'AWS::RDS::DBInstance'
    Properties:
      DBInstanceIdentifier: !Sub '${EnvironmentName}-database'
      Engine: postgres
      EngineVersion: '15.4'
      DBInstanceClass: db.r6g.large
      AllocatedStorage: 100
      StorageEncrypted: true
      KmsKeyId: !Ref DatabaseKMSKey
      MasterUsername: dbadmin
      MasterUserPassword: !Ref DBPassword
      VPCSecurityGroups:
        - !Ref DatabaseSecurityGroup
      BackupRetentionPeriod: 7
      MultiAZ: true
      DeletionProtection: true
      EnablePerformanceInsights: true
      MonitoringInterval: 60
      MonitoringRoleArn: !GetAtt RDSMonitoringRole.Arn

  DatabaseSecurityGroup:
    Type: 'AWS::EC2::SecurityGroup'
    Properties:
      GroupDescription: Security group for database
      VpcId: !Ref VPCId
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 5432
          ToPort: 5432
          SourceSecurityGroupId: !Ref AppSecurityGroup
      SecurityGroupEgress: []

  DatabaseKMSKey:
    Type: 'AWS::KMS::Key'
    Properties:
      Description: !Sub 'KMS key for ${EnvironmentName} database'
      EnableKeyRotation: true

  RDSMonitoringRole:
    Type: 'AWS::IAM::Role'
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: monitoring.rds.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole'

Outputs:
  BucketArn:
    Value: !GetAtt SecureBucket.Arn
  DatabaseEndpoint:
    Value: !GetAtt Database.Endpoint.Address
```

### 6.2 cfn-lint

```bash
# Instalacao
pip install cfn-lint

# Verificacao basica
cfn-lint template.yaml

# Verificacao com regras especificas
cfn-lint template.yaml -r E3012

# Verificacao com ignore
cfn-lint template.yaml -i E3012

# Output em formato JSON
cfn-lint template.yaml -f json

# Verificar todos os templates
cfn-lint templates/**/*.yaml
```

**Integracao com CI/CD**:

```yaml
# .github/workflows/cfn-security.yml
name: CloudFormation Security

on:
  pull_request:
    branches: [main]
    paths:
      - 'cloudformation/**'

jobs:
  cfn-lint:
    name: cfn-lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: scottbrenner/cfn-lint-action@v2
        with:
          args: cloudformation/**/*.yaml

  cfn-nag:
    name: cfn-nag
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install cfn-nag
        run: gem install cfn-nag
      - name: Run cfn-nag
        run: |
          cfn_nag_scan \
            --input-path cloudformation/ \
            --output-format json \
            --exclude-checks W92 W92_1
```

---

## 7. Pulumi Security

### 7.1 Policy as Code com CrossGuard

Pulumi fornece CrossGuard, um framework de politicas que permite definir regras de seguranca como codigo:

```python
# __main__.py
import pulumi
import pulumi_aws as aws
from pulumi_policy import (
    EnforcementLevel,
    ResourceValidationPolicy,
    StackValidationPolicy,
    AdmissionReviewOptions,
)

# Politica para exigir criptografia em S3
require_s3_encryption = ResourceValidationPolicy(
    name="require-s3-encryption",
    description="Exige que todos os buckets S3 tenham criptografia habilitada",
    enforcement_level=EnforcementLevel.MANDATORY,
    resource_types=["aws:s3:Bucket"],
    validate_resource=lambda args, report_violation: _check_s3_encryption(args, report_violation),
)

def _check_s3_encryption(args, report_violation):
    server_side_encryption = args.props.get("serverSideEncryptionConfiguration")
    if not server_side_encryption:
        report_violation(
            "Bucket S3 nao tem configuracao de criptografia. "
            "Configure serverSideEncryptionConfiguration."
        )

# Politica para negar instancias publicas
deny_public_ec2 = ResourceValidationPolicy(
    name="deny-public-ec2",
    description="Nega instancias EC2 com IP publico",
    enforcement_level=EnforcementLevel.MANDATORY,
    resource_types=["aws:ec2:Instance"],
    validate_resource=lambda args, report_violation: _deny_public_ec2(args, report_violation),
)

def _deny_public_ec2(args, report_violation):
    associate_public_ip = args.props.get("associatePublicIpAddress")
    if associate_public_ip:
        report_violation(
            "Instancia EC2 com IP publico associado. "
            "Use NAT Gateway ou ALB para acesso externo."
        )

# Politica para exigir tags obrigatorias
require_tags = ResourceValidationPolicy(
    name="require-tags",
    description="Exige tags Environment e ManagedBy em todos os recursos",
    enforcement_level=EnforcementLevel.MANDATORY,
    resource_types=["*"],
    validate_resource=lambda args, report_violation: _check_tags(args, report_violation),
)

def _check_tags(args, report_violation):
    tags = args.props.get("tags", {})
    required_tags = ["Environment", "ManagedBy"]
    missing = [tag for tag in required_tags if tag not in tags]
    if missing:
        report_violation(
            f"Tags obrigatorias ausentes: {', '.join(missing)}"
        )

# Registro de politicas
pulumi.register_resource_policies([
    require_s3_encryption,
    deny_public_ec2,
    require_tags,
])

# Infraestrutura segura
bucket = aws.s3.Bucket(
    "secure-bucket",
    server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
        rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
            apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                sse_algorithm="aws:kms",
            ),
            bucket_key_enabled=True,
        ),
    ),
    versioning=aws.s3.BucketVersioningArgs(
        status="Enabled",
    ),
    tags={
        "Environment": "production",
        "ManagedBy": "pulumi",
    },
)

instance = aws.ec2.Instance(
    "app-instance",
    instance_type="t3.medium",
    ami="ami-0c55b159cbfafe1f0",
    tags={
        "Environment": "production",
        "ManagedBy": "pulumi",
    },
)
```

### 7.2 Stack Validation

```python
# stack_policy.py
from pulumi_policy import StackValidationPolicy, EnforcementLevel
import pulumi

# Validacao a nivel de stack
stack_policy = StackValidationPolicy(
    name="production-stack-validation",
    description="Valida configuracoes de seguranca a nivel de stack",
    enforcement_level=EnforcementLevel.MANDATORY,
    validate_stack=lambda stack, report_violation: _validate_stack(stack, report_violation),
)

def _validate_stack(stack, report_violation):
    # Verificar se ha instancias com IP publico
    for resource in stack.resources:
        if resource.resource_type == "aws:ec2:Instance":
            public_ip = resource.props.get("publicIp")
            if public_ip:
                report_violation(
                    f"Recurso {resource.name} tem IP publico: {public_ip}"
                )

        # Verificar se S3 buckets tem versionamento
        if resource.resource_type == "aws:s3:Bucket":
            versioning = resource.props.get("versioning")
            if not versioning or versioning.get("status") != "Enabled":
                report_violation(
                    f"Bucket {resource.name} nao tem versionamento habilitado"
                )
```

---

## 8. Kubernetes IaC Security

### 8.1 OPA/Gatekeeper

Open Policy Agent (OPA) com Gatekeeper fornece admission control para Kubernetes:

```yaml
# constraint-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        violation[{"msg": msg}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Label obrigatorio ausente: %v", [missing])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-environment-label
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod", "Service"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
    namespaces:
      - production
      - staging
  parameters:
    labels:
      - environment
      - team
      - managed-by
```

```yaml
# disallow-privileged.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sdisallowprivileged
spec:
  crd:
    spec:
      names:
        kind: K8sDisallowPrivileged
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sdisallowprivileged

        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.privileged == true
          msg := sprintf("Container %v nao pode rodar em modo privilegiado", [container.name])
        }

        violation[{"msg": msg}] {
          container := input.review.object.spec.initContainers[_]
          container.securityContext.privileged == true
          msg := sprintf("Init container %v nao pode rodar em modo privilegiado", [container.name])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sDisallowPrivileged
metadata:
  name: disallow-privileged-containers
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
```

### 8.2 Kyverno Policies

Kyverno e uma engine de politicas Kubernetes-native que usa YAML para definir regras:

```yaml
# require-labels.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
  annotations:
    policies.kyverno.io/title: Require Labels
    policies.kyverno.io/category: Best Practices
    policies.kyverno.io/severity: medium
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-for-labels
      match:
        any:
          - resources:
              kinds:
                - Pod
                - Deployment
                - StatefulSet
                - Service
      validate:
        message: "Recurso {{request.object.kind}}/{{request.object.metadata.name}} requer as labels: environment, team, managed-by"
        pattern:
          metadata:
            labels:
              environment: "?*"
              team: "?*"
              managed-by: "?*"

---
# restrict-image-registries.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
  annotations:
    policies.kyverno.io/title: Restrict Image Registries
    policies.kyverno.io/category: Supply Chain Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: validate-registries
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Imagem deve vir de um registro aprovado"
        pattern:
          spec:
            containers:
              - image: "registry.company.com/* | docker.io/library/*"
            initContainers:
              - image: "registry.company.com/* | docker.io/library/*"

---
# require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: Require Resource Limits
    policies.kyverno.io/category: Best Practices
    policies.kyverno.io/severity: medium
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-container-resources
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Containers devem ter resource limits configurados"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    cpu: "?*"
                    memory: "?*"
                  requests:
                    cpu: "?*"
                    memory: "?*"

---
# disallow-host-namespaces.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-host-namespaces
  annotations:
    policies.kyverno.io/title: Disallow Host Namespaces
    policies.kyverno.io/category: Pod Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: disallow-host-network
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Host network nao e permitido"
        pattern:
          spec:
            =(hostNetwork): false

    - name: disallow-host-pid
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Host PID namespace nao e permitido"
        pattern:
          spec:
            =(hostPID): false

    - name: disallow-host-ipc
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Host IPC namespace nao e permitido"
        pattern:
          spec:
            =(hostIPC): false
```

### 8.3 Setup Completo de Admission Controllers

```yaml
# gatekeeper-installation.yaml
# Instalacao do Gatekeeper via Helm
# helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
# helm install gatekeeper gatekeeper/gatekeeper -n gatekeeper-system --create-namespace

# Configuracao de audit
apiVersion: config.gatekeeper.sh/v1alpha1
kind: Config
metadata:
  name: config
  namespace: gatekeeper-system
spec:
  match:
    - excludedNamespaces:
        - kube-system
        - gatekeeper-system
        - kube-public
      kinds:
        - apiGroups: [""]
          kinds: ["Pod"]
        - apiGroups: ["apps"]
          kinds: ["Deployment", "StatefulSet", "DaemonSet"]
  audit: true
  auditInterval: 60
  constraintCacheLimits:
    size: 1000

---
# Configuracao de mutacao
apiVersion: mutations.gatekeeper.sh/v1
kind: AssignMetadata
metadata:
  name: add-managed-by-label
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces:
      - production
      - staging
  location: "metadata.labels.managed-by"
  value: "gatekeeper"

---
# Pod Security Standards enforcement
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8spspprivilegedcontainer
spec:
  crd:
    spec:
      names:
        kind: K8sPSPPrivilegedContainer
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8spspprivileged

        violation[{"msg": msg}] {
          c := input_containers[_]
          c.securityContext.privileged == true
          msg := sprintf("Container %v nao pode rodar em modo privilegiado", [c.name])
        }

        input_containers[c] {
          c := input.review.object.spec.containers[_]
        }

        input_containers[c] {
          c := input.review.object.spec.initContainers[_]
        }

        input_containers[c] {
          c := input.review.object.spec.ephemeralContainers[_]
        }

---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sPSPPrivilegedContainer
metadata:
  name: psp-privileged-container
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces:
      - kube-system
```

### 8.4 Pod Security Standards Enforcement

```yaml
# pod-security-standards.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    # PSS: restricted level
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest

---
# Deployment que atende ao PSS restricted
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure-app
  template:
    metadata:
      labels:
        app: secure-app
        environment: production
        team: backend
        managed-by: terraform
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry.company.com/secure-app:1.0.0
          ports:
            - containerPort: 8080
              protocol: TCP
          resources:
            limits:
              cpu: "500m"
              memory: "256Mi"
            requests:
              cpu: "100m"
              memory: "128Mi"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: database-url
          volumeMounts:
            - name: tmp
              mountPath: /tmp
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
      volumes:
        - name: tmp
          emptyDir: {}
      serviceAccountName: app-service-account
```

---

## 9. State File Security

### 9.1 Criptografia de State Remoto

A seguranca do arquivo de estado do Terraform e critica. Configuracoes inseguras podem expor dados sensiveis, credenciais e a topologia completa da infraestrutura.

**Backend S3 com KMS encryption**:

```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "production/network/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
    kms_key_id     = "alias/terraform-state-key"
  }
}

# Configuracao da chave KMS para o estado
resource "aws_kms_key" "terraform_state" {
  description             = "KMS key for Terraform state encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowRootAccountAccess"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid       = "AllowTerraformRoleAccess"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/terraform-role"
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_kms_alias" "terraform_state" {
  name          = "alias/terraform-state-key"
  target_key_id = aws_kms_key.terraform_state.key_id
}
```

### 9.2 State Locking com DynamoDB

```hcl
# Tabela DynamoDB para lock de estado
resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-state-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.terraform_state.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name      = "Terraform State Lock"
    ManagedBy = "terraform"
  }
}

# Politica de acesso a DynamoDB
resource "aws_iam_policy" "terraform_dynamodb" {
  name        = "terraform-dynamodb-access"
  description = "Politica de acesso ao DynamoDB para lock de estado Terraform"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.terraform_lock.arn
      }
    ]
  })
}
```

### 9.3 Controle de Acesso ao Estado

```hcl
# Bucket de estado com politicas de acesso
resource "aws_s3_bucket" "terraform_state" {
  bucket = "company-terraform-state"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.terraform_state.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
  }
}

# Bucket policy com MFA Delete e restricoes de acesso
resource "aws_s3_bucket_policy" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  depends_on = [aws_s3_bucket_public_access_block.terraform_state]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid       = "RestrictToVPCE"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*"
        ]
        Condition = {
          StringNotEquals = {
            "aws:sourceVpce" = "vpce-1234567890abcdef0"
          }
        }
      },
      {
        Sid       = "DenyUnencryptedUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.terraform_state.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      },
      {
        Sid       = "RestrictStateAccess"
        Effect    = "Deny"
        Principal = "*"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.terraform_state.arn}/*"
        Condition = {
          StringNotLike = {
            "aws:PrincipalArn" = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/terraform-*"
          }
        }
      }
    ]
  })
}

# IAM Role para Terraform
resource "aws_iam_role" "terraform_role" {
  name = "terraform-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:PrincipalTag/Role" = "terraform"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "terraform_s3_access" {
  name = "terraform-s3-access"
  role = aws_iam_role.terraform_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.terraform_lock.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.terraform_state.arn
      }
    ]
  })
}
```

### 9.4 Backend Completo com State Isolation

```hcl
# configuracao-deploy.sh
#!/bin/bash
# Script de deploy com isolamento de estado por ambiente

set -euo pipefail

ENVIRONMENT="${1:-dev}"
PROJECT="myapp"

# Validar ambiente
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    echo "Ambiente invalido: $ENVIRONMENT"
    echo "Uso: $0 <dev|staging|production>"
    exit 1
fi

echo "=== Deploy para ambiente: $ENVIRONMENT ==="

# Copiar backend.tf para o ambiente
cat > "terraform/backend-${ENVIRONMENT}.tf" << EOF
terraform {
  backend "s3" {
    bucket         = "company-terraform-state-${ENVIRONMENT}"
    key            = "${PROJECT}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock-${ENVIRONMENT}"
    kms_key_id     = "alias/terraform-state-${ENVIRONMENT}"
  }
}
EOF

# Inicializar Terraform com o backend correto
cd terraform/
terraform init -backend-config="backend-${ENVIRONMENT}.tf"

# Verificar alteracoes
terraform plan -out=tfplan

# Perguntar confirmacao antes de aplicar
read -p "Aplicar mudancas para $ENVIRONMENT? (sim/nao): " confirm
if [ "$confirm" = "sim" ]; then
    terraform apply tfplan
    echo "Deploy concluido para $ENVIRONMENT"
else
    echo "Deploy cancelado"
    exit 0
fi
```

---

## 10. Exemplo Completo: IaC Security Pipeline

### 10.1 Pipeline Terraform com Gates de Seguranca

Este exemplo demonstra uma pipeline completa que incorpora todas as ferramentas de seguranca discutidas neste capitulo:

```yaml
# .github/workflows/terraform-security-pipeline.yml
name: IaC Security Pipeline

on:
  push:
    branches: [main, develop]
    paths:
      - 'terraform/**'
      - 'ansible/**'
      - 'kubernetes/**'
  pull_request:
    branches: [main]
    paths:
      - 'terraform/**'
      - 'ansible/**'
      - 'kubernetes/**'

permissions:
  contents: read
  security-events: write
  pull-requests: write
  id-token: write

env:
  TF_VERSION: "1.6.0"
  CHECKOV_VERSION: "3.1.0"
  TFSEC_VERSION: "1.28.0"
  TF_ROOT: "terraform/"

jobs:
  # ============================================
  # Fase 1: Validacao Basica
  # ============================================
  validate:
    name: Validacao Basica
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Format Check
        run: terraform fmt -check -recursive ${{ env.TF_ROOT }}
        working-directory: .

      - name: Terraform Init
        run: terraform init -backend=false -input=false
        working-directory: ${{ env.TF_ROOT }}

      - name: Terraform Validate
        run: terraform validate
        working-directory: ${{ env.TF_ROOT }}

      - name: Terraform Taint Check
        run: |
          # Verificar se ha recursos taintados nao intencionais
          terraform state list | head -1 || echo "Sem estado (init)"
        working-directory: ${{ env.TF_ROOT }}

  # ============================================
  # Fase 2: Security Scanning
  # ============================================
  security-scan:
    name: Security Scanning
    needs: validate
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        scanner: [checkov, tfsec, cfn-nag]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Checkov
        if: matrix.scanner == 'checkov'
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: ${{ env.TF_ROOT }}
          framework: terraform
          output_format: sarif
          output_file_path: checkov-results.sarif
          soft_fail: false
          download_external_modules: true
          compact: true
          quiet: true

      - name: Run tfsec
        if: matrix.scanner == 'tfsec'
        uses: aquasecurity/tfsec-action@v1.0.3
        with:
          working_directory: ${{ env.TF_ROOT }}
          soft_fail: false
          format: sarif
          sarif_file: tfsec-results.sarif

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always() && (matrix.scanner == 'checkov' || matrix.scanner == 'tfsec')
        with:
          sarif_file: ${{ matrix.scanner }}-results.sarif

      - name: Upload Security Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: ${{ matrix.scanner }}-results
          path: |
            checkov-results.sarif
            tfsec-results.sarif
          retention-days: 30

  # ============================================
  # Fase 3: Secret Scanning
  # ============================================
  secret-scan:
    name: Secret Scanning
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Scan for secrets with truffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

      - name: Check for hardcoded secrets in Terraform
        run: |
          echo "Verificando secrets hardcoded no Terraform..."
          PATTERN='(password|secret|api_key|token)\s*=\s*"[^"]*"'
          if grep -rP "$PATTERN" ${{ env.TF_ROOT }} --include="*.tf"; then
            echo "ERRO: Secrets hardcoded encontrados!"
            echo "Por favor, use variaveis de ambiente, Vault ou AWS Secrets Manager."
            exit 1
          fi
          echo "Nenhum secret hardcoded encontrado."

  # ============================================
  # Fase 4: Plan e Security Gate
  # ============================================
  plan:
    name: Terraform Plan
    needs: [security-scan, secret-scan]
    runs-on: ubuntu-latest
    environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/terraform-github-actions
          aws-region: us-east-1

      - name: Terraform Init
        run: terraform init
        working-directory: ${{ env.TF_ROOT }}

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan -out=tfplan -detailed-exitcode || EXIT_CODE=$?

          # Codigo 2 = mudancas detectadas
          if [ "${EXIT_CODE:-0}" -eq 2 ]; then
            echo "changes_detected=true" >> $GITHUB_OUTPUT
          else
            echo "changes_detected=false" >> $GITHUB_OUTPUT
          fi

          # Verificar se ha mudancas perigosas
          DANGEROUS_CHANGES=$(terraform show -json tfplan | jq -r '
            [.resource_changes[] |
             select(.change.actions[] | test("create|update|delete")) |
             select(.type | test("aws_security_group|aws_iam|aws_s3_bucket")) |
             .address] | length
          ')

          echo "Mudancas em recursos criticos: $DANGEROUS_CHANGES"

          if [ "$DANGEROUS_CHANGES" -gt 5 ]; then
            echo "ERRO: Mais de 5 mudancas em recursos criticos detectadas!"
            echo "Requer aprovacao manual."
            echo "requires_approval=true" >> $GITHUB_OUTPUT
          else
            echo "requires_approval=false" >> $GITHUB_OUTPUT
          fi
        working-directory: ${{ env.TF_ROOT }}

      - name: Plan Summary
        if: steps.plan.outputs.changes_detected == 'true'
        run: |
          echo "## Resumo do Terraform Plan" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          terraform show -no-color tfplan >> $GITHUB_STEP_SUMMARY
        working-directory: ${{ env.TF_ROOT }}

      - name: Upload Plan Artifact
        uses: actions/upload-artifact@v4
        with:
          name: terraform-plan
          path: ${{ env.TF_ROOT }}/tfplan
          retention-days: 7

      - name: Require Approval
        if: steps.plan.outputs.requires_approval == 'true'
        uses: trstringer/manual-approval@v1
        with:
          secret: ${{ secrets.GITHUB_TOKEN }}
          approvers: admin1,admin2
          minimum-approvals: 1
          issue-title: "Terraform Plan - Multiplas mudancas em recursos criticos"
          issue-body: "Por favor, revise e aprove as mudancas de infraestrutura."

  # ============================================
  # Fase 5: Apply (apenas no merge para main)
  # ============================================
  apply:
    name: Terraform Apply
    needs: plan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT_ID:role/terraform-github-actions
          aws-region: us-east-1

      - name: Download Plan
        uses: actions/download-artifact@v4
        with:
          name: terraform-plan
          path: ${{ env.TF_ROOT }}

      - name: Terraform Init
        run: terraform init
        working-directory: ${{ env.TF_ROOT }}

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: ${{ env.TF_ROOT }}

      - name: Post-Apply Security Validation
        run: |
          echo "Executando validacao de seguranca pos-apply..."
          
          # Verificar se nenhum recurso inseguro foi criado
          # Exemplo: verificar buckets S3 publicos
          BUCKETS=$(aws s3api list-buckets --query 'Buckets[].Name' --output text)
          
          for BUCKET in $BUCKETS; do
            PUBLIC_ACCESS=$(aws s3api get-public-access-block \
              --bucket "$BUCKET" \
              --query 'PublicAccessBlockConfiguration.BlockPublicAcls' \
              --output text 2>/dev/null || echo "None")
            
            if [ "$PUBLIC_ACCESS" != "True" ]; then
              echo "AVISO: Bucket $BUCKET pode nao ter bloqueio de acesso publico!"
            fi
          done
          
          echo "Validacao pos-apply concluida."

      - name: Create Notification
        if: success()
        run: |
          echo "## Terraform Apply Concluido" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Ambiente**: production" >> $GITHUB_STEP_SUMMARY
          echo "**Branch**: ${{ github.ref_name }}" >> $GITHUB_STEP_SUMMARY
          echo "**Commit**: ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
          echo "**Autor**: ${{ github.actor }}" >> $GITHUB_STEP_SUMMARY
```

### 10.2 Script de Deploy Local

```bash
#!/bin/bash
# scripts/iac-security-pipeline.sh
# Pipeline local de seguranca para IaC

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TF_DIR="${PROJECT_ROOT}/terraform"
REPORT_DIR="${PROJECT_ROOT}/security-reports"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
ERRORS=0
WARNINGS=0

mkdir -p "$REPORT_DIR"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; WARNINGS=$((WARNINGS + 1)); }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; ERRORS=$((ERRORS + 1)); }

echo "============================================"
echo "  IaC Security Pipeline"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# ============================================
# Fase 1: Formatacao e Validacao
# ============================================
log_info "Fase 1: Formatacao e Validacao do Terraform"

if terraform fmt -check -recursive "$TF_DIR" > /dev/null 2>&1; then
    log_success "Formatacao OK"
else
    log_warn "Formatando arquivos Terraform..."
    terraform fmt -recursive "$TF_DIR"
fi

cd "$TF_DIR"
terraform init -backend=false -input=false > /dev/null 2>&1
if terraform validate > /dev/null 2>&1; then
    log_success "Validacao Terraform OK"
else
    log_error "Validacao Terraform falhou"
fi
cd "$PROJECT_ROOT"

# ============================================
# Fase 2: Checkov
# ============================================
log_info "Fase 2: Executando Checkov"

if command -v checkov &> /dev/null; then
    checkov -d "$TF_DIR" \
        --output json \
        --output-file "$REPORT_DIR/checkov-results.json" \
        --compact \
        --quiet \
        --framework terraform \
        --download-external-modules true 2>/dev/null

    CHECKOV_ERRORS=$(jq '[.results.failed_checks | length] | .[0]' \
        "$REPORT_DIR/checkov-results.json" 2>/dev/null || echo "0")

    if [ "$CHECKOV_ERRORS" -gt 0 ]; then
        log_error "Checkov encontrou $CHECKOV_ERRORS violacoes"
        jq '.results.failed_checks[] | "\(.check_id): \(.check_name) [\(.severity)]"' \
            "$REPORT_DIR/checkov-results.json" 2>/dev/null | head -20
    else
        log_success "Checkov: nenhuma violacao encontrada"
    fi
else
    log_warn "Checkov nao encontrado, pulando..."
fi

# ============================================
# Fase 3: tfsec
# ============================================
log_info "Fase 3: Executando tfsec"

if command -v tfsec &> /dev/null; then
    tfsec "$TF_DIR" \
        --format json \
        --out "$REPORT_DIR/tfsec-results.json" \
        --minimum-severity MEDIUM \
        --concise 2>/dev/null

    TFSEC_ERRORS=$(jq '[.results | length] | .[0]' \
        "$REPORT_DIR/tfsec-results.json" 2>/dev/null || echo "0")

    if [ "$TFSEC_ERRORS" -gt 0 ]; then
        log_error "tfsec encontrou $TFSEC_ERRORS violacoes"
        jq '.results[] | "\(.rule_id): \(.long_id) [\(.severity)]"' \
            "$REPORT_DIR/tfsec-results.json" 2>/dev/null | head -20
    else
        log_success "tfsec: nenhuma violacao encontrada"
    fi
else
    log_warn "tfsec nao encontrado, pulando..."
fi

# ============================================
# Fase 4: Verificacao de Secrets
# ============================================
log_info "Fase 4: Verificando secrets hardcoded"

PATTERN='(password|secret|api_key|token|access_key)\s*=\s*"[^"]*"'
if grep -rP "$PATTERN" "$TF_DIR" --include="*.tf" 2>/dev/null; then
    log_error "Secrets hardcoded encontrados no codigo Terraform!"
else
    log_success "Nenhum secret hardcoded encontrado"
fi

# Verificar arquivos .tfstate
if find "$PROJECT_ROOT" -name "*.tfstate" -not -path "*/.git/*" 2>/dev/null | grep -q .; then
    log_warn "Arquivos .tfstate encontrados no repositorio"
else
    log_success "Nenhum arquivo .tfstate no repositorio"
fi

# ============================================
# Fase 5: Verificacao de Imagens (se houver)
# ============================================
log_info "Fase 5: Verificando Dockerfiles"

if find "$PROJECT_ROOT" -name "Dockerfile*" 2>/dev/null | grep -q .; then
    log_info "Dockerfiles encontrados, verificando seguranca..."

    # Verificar se ha imagens base desatualizadas ou inseguras
    if command -v hadolint &> /dev/null; then
        find "$PROJECT_ROOT" -name "Dockerfile*" -not -path "*/.git/*" | while read -r dockerfile; do
            log_info "Analisando: $dockerfile"
            hadolint "$dockerfile" 2>/dev/null || log_warn "Problemas encontrados em $dockerfile"
        done
    else
        log_warn "hadolint nao encontrado, pulando verificacao de Dockerfiles"
    fi
else
    log_success "Nenhum Dockerfile encontrado"
fi

# ============================================
# Fase 6: Kubernetes (se houver)
# ============================================
log_info "Fase 6: Verificando manifests Kubernetes"

K8S_DIR="${PROJECT_ROOT}/kubernetes"
if [ -d "$K8S_DIR" ]; then
    if command -v kube-score &> /dev/null; then
        find "$K8S_DIR" -name "*.yaml" -o -name "*.yml" | while read -r manifest; do
            log_info "Analisando: $manifest"
            kube-score score "$manifest" 2>/dev/null || log_warn "Problemas encontrados em $manifest"
        done
    else
        log_warn "kube-score nao encontrado"
    fi
else
    log_success "Nenhum diretorio Kubernetes encontrado"
fi

# ============================================
# Relatorio Final
# ============================================
echo ""
echo "============================================"
echo "  Relatorio Final"
echo "============================================"
echo ""
echo "Erros: $ERRORS"
echo "Avisos: $WARNINGS"
echo ""
echo "Relatorios salvos em: $REPORT_DIR"

if [ "$ERRORS" -gt 0 ]; then
    echo -e "${RED}Pipeline de seguranca FALHOU!${NC}"
    echo "Corrija os erros antes de prosseguir."
    exit 1
else
    echo -e "${GREEN}Pipeline de seguranca APROVADA!${NC}"
    if [ "$WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}Avisos devem ser revisados.${NC}"
    fi
    exit 0
fi
```

### 10.3 GitLab CI Completo

```yaml
# .gitlab-ci.yml
# Pipeline completa de IaC com seguranca

stages:
  - validate
  - security
  - plan
  - apply

variables:
  TF_ROOT: terraform/
  TF_IN_AUTOMATION: "true"
  TF_CLI_ARGS: "-no-color"
  CHECKOV_VERSION: "3.1.0"

# Cache comum para modulos Terraform
.cache_terraform: &cache_terraform
  cache:
    key: terraform-${CI_COMMIT_REF_SLUG}
    paths:
      - ${TF_ROOT}/.terraform/

# ============================================
# Fase 1: Validacao
# ============================================
terraform-validate:
  stage: validate
  image: hashicorp/terraform:${TF_VERSION:-1.6.0}
  <<: *cache_terraform
  script:
    - cd ${TF_ROOT}
    - terraform init -backend=false -input=false
    - terraform fmt -check -recursive .
    - terraform validate
  rules:
    - if: '$CI_MERGE_REQUEST_ID'
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_COMMIT_BRANCH == "develop"'

# ============================================
# Fase 2: Security Scanning
# ============================================
checkov-scan:
  stage: security
  image: bridgecrew/checkov:${CHECKOV_VERSION}
  script:
    - cd ${TF_ROOT}
    - checkov -d . --output json --output-file ../checkov-results.json --compact --quiet
    - checkov -d . --output junitxml --output-file ../checkov-results.xml --compact --quiet
    - |
      # Verificar resultados
      ERRORS=$(cat ../checkov-results.json | jq '[.results.failed_checks | length] | .[0]')
      echo "Checkov errors: $ERRORS"
      if [ "$ERRORS" -gt 0 ]; then
        echo "Falha na verificacao Checkov!"
        exit 1
      fi
  artifacts:
    reports:
      junit: checkov-results.xml
    paths:
      - checkov-results.json
    expire_in: 30 days
  rules:
    - if: '$CI_MERGE_REQUEST_ID'
    - if: '$CI_COMMIT_BRANCH == "main"'

tfsec-scan:
  stage: security
  image: aquasec/tfsec:latest
  script:
    - cd ${TF_ROOT}
    - tfsec . --format json --out ../tfsec-results.json --minimum-severity MEDIUM
    - |
      ERRORS=$(cat ../tfsec-results.json | jq '[.results | length] | .[0]')
      echo "tfsec errors: $ERRORS"
      if [ "$ERRORS" -gt 0 ]; then
        echo "Falha na verificacao tfsec!"
        exit 1
      fi
  artifacts:
    paths:
      - tfsec-results.json
    expire_in: 30 days
  rules:
    - if: '$CI_MERGE_REQUEST_ID'
    - if: '$CI_COMMIT_BRANCH == "main"'

secret-scan:
  stage: security
  image: python:3.11-slim
  script:
    - pip install detect-secrets
    - detect-secrets scan ${TF_ROOT}/ > .secrets.json
    - |
      NEW_SECRETS=$(cat .secrets.json | jq '[.results | to_entries[] | select(.value.type != "Hashed password")] | length')
      echo "Secrets encontrados: $NEW_SECRETS"
      if [ "$NEW_SECRETS" -gt 0 ]; then
        echo "Possiveis secrets hardcoded encontrados!"
        cat .secrets.json | jq '.results'
        exit 1
      fi
  rules:
    - if: '$CI_MERGE_REQUEST_ID'

# ============================================
# Fase 3: Plan
# ============================================
terraform-plan:
  stage: plan
  image: hashicorp/terraform:${TF_VERSION:-1.6.0}
  <<: *cache_terraform
  script:
    - cd ${TF_ROOT}
    - terraform init
    - terraform plan -out=tfplan -detailed-exitcode || EXIT_CODE=$?
    - |
      if [ "${EXIT_CODE:-0}" -eq 0 ]; then
        echo "Sem mudancas"
      elif [ "${EXIT_CODE:-0}" -eq 2 ]; then
        echo "Mudancas detectadas"
        terraform show -no-color tfplan > ../plan-output.txt
      else
        echo "Erro no plan"
        exit 1
      fi
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
      - plan-output.txt
    expire_in: 7 days
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
    - if: '$CI_MERGE_REQUEST_ID'

# ============================================
# Fase 4: Apply
# ============================================
terraform-apply:
  stage: apply
  image: hashicorp/terraform:${TF_VERSION:-1.6.0}
  <<: *cache_terraform
  script:
    - cd ${TF_ROOT}
    - terraform init
    - terraform apply -auto-approve tfplan
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
    expire_in: 1 day
  dependencies:
    - terraform-plan
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual
      allow_failure: false
  environment:
    name: production
```

---

## 11. Referencias

### Documentacao Oficial

1. **Terraform**: https://www.terraform.io/docs/language/state/sensitive-data.html - Documentacao sobre dados sensiveis no estado do Terraform.

2. **AWS Security Best Practices**: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html - Guia de seguranca da AWS Well-Architected Framework.

3. **Checkov Documentation**: https://www.checkov.io/1.Welcome/What%20is%20Checkov.html - Documentacao oficial do Checkov.

4. **tfsec**: https://aquasecurity.github.io/tfsec/latest/ - Documentacao do tfsec.

5. **OPA Gatekeeper**: https://open-policy-agent.github.io/gatekeeper/ - Documentacao do OPA Gatekeeper.

6. **Kyverno**: https://kyverno.io/docs/ - Documentacao oficial do Kyverno.

7. **Pulumi CrossGuard**: https://www.pulumi.com/docs/guides/crossguard/ - Documentacao de Policy as Code do Pulumi.

### Casos Reais e Incidentes

8. **Capital One Breach (2019)**: https://aws.amazon.com/blogs/security/capital-one-incident-and-aws/ - Analise do incidente da Capital One pela AWS.

9. **S3 Bucket Misconfigurations**: https://www.invicti.com/blog/cloud-security/aws-s3-bucket-vulnerabilities/ - Analise de vulnerabilidades comuns em buckets S3.

10. **Terraform State Security**: https://developer.hashicorp.com/terraform/language/state/sensitive-data - Guias de seguranca para estado do Terraform.

### Ferramentas Adicionais

11. **cfn-nag**: https://github.com/stelligent/cfn_nag - Ferramenta de verificacao de seguranca para CloudFormation.

12. **cfn-lint**: https://github.com/aws-cloudformation/cfn-lint - Linter para templates CloudFormation.

13. **Kube-score**: https://github.com/zegl/kube-score - Analise de seguranca para manifests Kubernetes.

14. **detect-secrets**: https://github.com/Yelp/detect-secrets - Ferramenta de deteccao de secrets em codigo.

15. **TruffleHog**: https://github.com/trufflesecurity/trufflehog - Scanner de secrets em repositorios.

### Guias e Artigos

16. **Terraform Security Best Practices**: https://www.env0.com/blog/terraform-security-best-practices - Melhores praticas de seguranca em Terraform.

17. **Infrastructure as Code Security**: https://bridgecrew.io/blog/infrastructure-as-code-security/ - Guia de seguranca para IaC.

18. **Kubernetes Security Guide**: https://kubernetes.io/docs/concepts/security/ - Guia oficial de seguranca do Kubernetes.

19. **Cloud Security Alliance**: https://cloudsecurityalliance.org/ - Recursos e guias de seguranca em nuvem.

20. **NIST SP 800-190**: https://csrc.nist.gov/publications/detail/sp/800-190/final - Guia de seguranca para aplicacoes em container.

---

*Capitulo 8 — Infrastructure as Code: Seguranca*
*DevSecOps na Pratica — Edicao 2024*
