---
layout: default
title: "01-introducao-github-actions"
---

# Capitulo 1 — Introducao ao GitHub Actions

> *"Automatize o trivial, automatize o seguranca, automatize tudo que pode ser automatizado."*

---

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Explicar a historia e evolucao do CI/CD desde os primordios ate a era moderna
2. Compreender a arquitetura completa do GitHub Actions e seus componentes
3. Configurar e gerenciar diferentes tipos de runners com seguranca
4. Navegar e utilizar o Marketplace de actions de forma eficiente
5. Dominar environment variables, contexts e secrets
6. Implementar workflows completos de CI/CD
7. Comparar GitHub Actions com outras ferramentas do mercado
8. Avaliar custos, limits e otimizacoes de uso
9. Aplicar security basics em workflows de producao

---

## 1.1 Historia do CI/CD

### De Makefiles a Pipelines

A automacao de build e deploy evoluiu significativamente nas ultimas decadas, refletindo mudancas na forma como desenvolvemos e entregamos software. Entender essa evolucao e fundamental para apreciar por que o GitHub Actions se tornou a solucao dominante no mercado atual.

#### Epoca dos Makefiles (1976 - 1990)

Em 1976, Stuart Feldman criou o Make, um utilitario que revolucionou a compilacao de programas. Antes do Make, desenvolvedores compilavam seus programas manualmente, executando comandos de compilacao um a um. O Make trouxe a ideia de **dependencias** — se o arquivo fonte nao foi modificado, nao era necessario recompilar.

```
# Exemplo historico de Makefile
CC = gcc
CFLAGS = -Wall -O2

target: main.o utils.o
    $(CC) $(CFLAGS) -o target main.o utils.o

main.o: main.c
    $(CC) $(CFLAGS) -c main.c

utils.o: utils.c
    $(CC) $(CFLAGS) -c utils.c

clean:
    rm -f *.o target
```

Esse padrao de declarar dependencias e executar comandos sequenciais continua vivo hoje — o GitHub Actions herda essa filosofia fundamental.

#### Era dos Build Tools (1990 - 2000)

Na decada de 1990, ferramentas de build evoluiram para atender linguagens especificas:

| Ferramenta | Ano | Linguagem | Caracteristica Principal |
|-----------|-----|-----------|-------------------------|
| Make | 1976 | C | Dependencias e targets |
| Ant | 2000 | Java | XML declarativo, cross-platform |
| Maven | 2004 | Java | Convencao sobre configuracao |
| MSBuild | 2005 | .NET | Integracao Visual Studio |
| Grunt | 2012 | JavaScript | Task runner para web |
| Gulp | 2013 | JavaScript | Streaming, performance |
| Webpack | 2014 | JavaScript | Module bundler |
| Bazel | 2015 | Multi | Build reproducivel, escalavel |

O Apache Ant, lancado em 2000, trouxe a ideia de **arquivos de build declarativos** (build.xml) que descreviam o que fazer, nao como fazer. O Maven ampliou isso com **convencao sobre configuracao**, eliminando a necessidade de escrever build scripts extensos para projetos padrao.

#### Nascimento do CI Server (2001 - 2010)

O conceito de Integracao Continua nasceu comMartin Fowler em 2006, mas os primeiros servidores de CI ja existiam:

**CruiseControl (2001)**
O primeiro servidor de CI real. Executava builds em intervalos regulares (polling), verificando se havia novas mudancas no repositorio. Era pesado, complexo e exigia configuracao manual extensiva.

```
# Configuracao CruiseControl (2001)
<project name="meu-projeto" buildafterfailed="false">
    <modificationset quietperiod="30">
        <svn localworkingcopy="/var/svn/projeto"/>
    </modificationset>
    <schedule interval="60">
        <ant anthome="/usr/local/ant" buildfile="build.xml"/>
    </schedule>
    <log dir="/var/log/cruisecontrol"/>
    <publishers>
        <email mailhost="smtp.empresa.com"
               returnaddress="ci@empresa.com"
               defaultsuffix="@empresa.com">
            <always address="devs@empresa.com"/>
        </email>
    </publishers>
</project>
```

**Hudson/Jenkins (2004 - 2011)**

Kohsuke Kawaguchi criou o Hudson enquanto trabalhava na Sun Microsystems. Em 2011, a comunidade bifurcou o projeto devido a disputas de governance, criando o Jenkins. O Jenkins revolucionou o CI com:

- **Plugins**: Mais de 1800 plugins disponiveis
- **Pipelines as Code**: Jenkinsfile (declarative e scripted)
- **Distributed builds**: Agents remotos
- **Pipeline visualization**: Interface grafica de etapas

```
// Jenkinsfile declarative moderno
pipeline {
    agent any

    environment {
        APP_NAME = 'meu-app'
        VERSION = readMavenPom().getVersion()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh 'mvn clean package -DskipTests'
            }
        }

        stage('Unit Test') {
            steps {
                sh 'mvn test'
            }
            post {
                always {
                    junit 'target/surefire-reports/*.xml'
                }
            }
        }

        stage('Integration Test') {
            steps {
                sh 'mvn verify -Pintegration-test'
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                sh 'mvn deploy -Pstaging'
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
                beforeInput true
            }
            input {
                message 'Deploy para producao?'
                ok 'Sim, fazer deploy'
            }
            steps {
                sh 'mvn deploy -Pproduction'
            }
        }
    }

    post {
        success {
            slackSend channel: '#deployments',
                      message: "Deploy concluido: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
        failure {
            mail to: 'devs@empresa.com',
                 subject: "Build falhou: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "Verificar: ${env.BUILD_URL}"
        }
    }
}
```

**Travis CI (2011)**

O Travis CI popularizou o conceito de **CI como Servico** (CIaaS). Pela primeira vez, um servico de CI era gratuito para projetos open source e se integrava diretamente com o GitHub. A configuracao era simplificada:

```yaml
# .travis.yml
language: node_js
node_js:
  - "18"
  - "20"

cache:
  directories:
    - node_modules

before_install:
  - npm install -g yarn

install:
  - yarn install

script:
  - yarn test
  - yarn build

after_success:
  - yarn coverage

branches:
  only:
    - main
    - develop
```

#### GitHub Actions Nasce (2019)

Em 2019, o GitHub anunciou o GitHub Actions na Universe Conference. A diferencial era clara: **integracao nativa** com o ecossistema GitHub, **Marketplace** com milhares de actions reutilizaveis, e **workflows como codigo** no proprio repositorio.

O GitHub Actions nao foi o primeiro a oferecer CI/CD integrado — o GitLab CI ja existia desde 2014 — mas a combinacao do ecossistema GitHub com a flexibilidade do Actions criou uma proposta de valor irresistivel.

#### Era Moderna (2020 - Presente)

A evolucao continua rapida:

| Ano | Recurso | Impacto |
|-----|---------|---------|
| 2020 | GitHub Packages integrado | Deploy de packages privados |
| 2021 | OIDC para cloud providers | Credenciais sem secrets |
| 2022 | Reusable workflows | Compartilhamento de pipelines |
| 2023 | Attestation e SLSA | Supply chain security |
| 2024 | Copilot para Actions | Geracao assistida de workflows |
| 2024 | Larger runners | Runners com ate 64 cores |
| 2025 | Actions v2 | Performance e novos contexts |

### Por Que GitHub Actions Venceu

GitHub Actions se tornou o CI/CD mais usado porque：

1. **Integracao nativa**: Vem com GitHub, sem setup externo. Nao precisa de servidores dedicados, plugins ou configuracoes complexas. O workflow vive ao lado do codigo.

2. **Marketplace**: Milhares de actions prontas para tudo — desde checkout de codigo ate deploy em Kubernetes. Economiza semanas de desenvolvimento.

3. **Reusable workflows**: Compartilhar pipelines entre projetos da organizacao. Defina uma vez, use em centenas de repositorios.

4. **Matrix builds**: Testar multi-plataforma facilmente. Uma unica definicao de matrix gera dezenas de combinacoes automaticamente.

5. **OIDC**: Autenticacao sem secrets em cloud providers. O GitHub Actions fornece tokens automaticos para AWS, Azure, GCP, e outros.

6. **Copilot integration**: Assisted workflow creation. O Copilot sugere e gera workflows baseados em linguagem natural.

7. **Gratuito para open source**: 2.000 minutos por mes para repositorios publicos, sem custo adicional.

8. **Self-hosted runners**: Possibilidade de rodar em seu proprio hardware para workloads especializadas ou sensiveis.

---

## 1.2 Arquitetura Completa

### Visao Geral do Sistema

O GitHub Actions e composto por varios componentes que trabalham juntos para executar workflows de forma confiavel e escalavel:

```
+-----------------------------------------------------------------------+
|                          GitHub Cloud                                  |
|                                                                       |
|  +-------------------+    +-------------------+    +----------------+ |
|  | Event Queue       |    | Workflow Engine   |    | Runner Manager | |
|  |                   |    |                   |    |                | |
|  | - push events     |--->| - Parse YAML      |--->| - Allocate     | |
|  | - PR events       |    | - Evaluate rules  |    | - Lifecycle    | |
|  | - schedule events |    | - Dispatch jobs   |    | - Monitoring   | |
|  | - manual triggers |    | - Track status    |    | - Cleanup      | |
|  +-------------------+    +-------------------+    +----------------+ |
|           |                        |                       |           |
|           v                        v                       v           |
|  +-------------------+    +-------------------+    +----------------+ |
|  | Secret Store      |    | Artifact Store    |    | Log Aggregator | |
|  |                   |    |                   |    |                | |
|  | - Encrypted       |    | - Upload/download |    | - Real-time    | |
|  | - Per-repo/org    |    | - Retention       |    | - Searchable   | |
|  | - Environment     |    | - Compression     |    | - Exportable   | |
|  +-------------------+    +-------------------+    +----------------+ |
|                                                                       |
+-----------------------------------------------------------------------+
                                  |
                                  | HTTPS
                                  v
+-----------------------------------------------------------------------+
|                          Runners                                       |
|                                                                       |
|  +-----------------+  +-----------------+  +------------------------+ |
|  | GitHub-Hosted   |  | GitHub-Hosted   |  | Self-Hosted            | |
|  | Linux           |  | macOS/Windows   |  |                        | |
|  |                 |  |                 |  | - Sua infraestrutura   | |
|  | Ubuntu 22.04/24 |  | macOS 14/15     |  | - Hardware especial    | |
|  | 2-64 cores      |  | 3-12 cores      |  | - Controle total       | |
|  | 7-256 GB RAM    |  | 7-19 GB RAM     |  | - Sem custo por minuto | |
|  +-----------------+  +-----------------+  +------------------------+ |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Ciclo de Vida de um Workflow

Quando um evento dispara um workflow, o seguinte ciclo de vida e executado:

1. **Evento**: Um push, pull request, schedule, ou manual trigger e detectado
2. **Filtragem**: O GitHub verifica se o evento corresponde aos triggers definidos
3. **Queue**: O evento e colocado na fila de processamento
4. **Parse**: O YAML do workflow e validado e parseado
5. **Dispatch**: Os jobs sao criados e atribuidos a runners
6. **Allocation**: Runners sao alocados (GitHub-hosted ou self-hosted)
7. **Execution**: Os steps sao executados sequencialmente dentro de cada job
8. **Logging**: Saida e erros sao gravados em tempo real
9. **Artifacts**: Arquivos produzidos sao armazenados conforme politica de retencao
10. **Completion**: Status final e reportado (success, failure, cancelled)

### Componentes Detalhados

#### Workflow Engine

O Workflow Engine e o coracao do GitHub Actions. Ele e responsavel por:

- Parsear arquivos YAML e validar sintaxe
- Avaliar expressoes e condicoes (`if` statements)
- Resolver referencias cruzadas (outputs entre jobs)
- Gerenciar dependencias entre jobs
- Monitorar timeouts e cancelamentos
- Integrar com o sistema de secrets

```yaml
# O Workflow Engine resolve automaticamente essas dependencias
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.meta.outputs.version }}
      image: ${{ steps.meta.outputs.tags }}
    steps:
      - id: meta
        run: |
          echo "version=1.2.3" >> $GITHUB_OUTPUT
          echo "tags=myapp:1.2.3" >> $GITHUB_OUTPUT

  test:
    needs: build  # Engine espera build completar
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testing version ${{ needs.build.outputs.version }}"

  deploy:
    needs: [build, test]  # Engine espera AMBOS completarem
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.image }}"
```

#### Runner Manager

O Runner Manager gerencia a vida util dos runners:

- **Alocacao**: Seleciona o runner disponivel baseado em labels e requisitos
- **Preparacao**: Configura o ambiente (instala tools, limpa workspace)
- **Execucao**: Monitora a execucao dos steps
- **Cleanup**: Remove artefatos, reseta o estado, libera o runner
- **Retry**: Em caso de falha do runner, realoca automaticamente

#### Secret Store

O Secret Store gerencia dados sensiveis com criptografia em repouso e em transito:

```yaml
# Uso de secrets em workflows
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          aws s3 sync ./dist s3://my-bucket/
```

**Niveis de secrets disponiveis**:

| Nivel | Escopo | Quando usar |
|-------|--------|-------------|
| Repository secrets | Repositorio especifico | Credenciais do projeto |
| Environment secrets | Environment especifico | Credenciais por ambiente (staging/prod) |
| Organization secrets | Toda a organizacao | Credenciais compartilhadas |
| Dependabot secrets | Dependabot only | Atualizacoes automaticas |
| Codespaces secrets | Codespaces only | Desenvolvimento local |

#### Artifact Store

O Artifact Store permite compartilhar arquivos entre jobs e workflows:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
          retention-days: 7
          compression-level: 6

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/

      - name: Deploy
        run: deploy.sh dist/
```

#### Log Aggregator

O Log Aggregator coleta e indexa logs de todos os steps:

- **Streaming**: Logs sao exibidos em tempo real na interface do GitHub
- **Searchable**: Todo o output e indexado para busca
- **Retention**: Logs sao mantidos por 90 dias (Free) ou mais (Pro/Enterprise)
- **Masking**: Secrets e dados sensiveis sao automaticamente mascarados

### Estrutura de Diretorios

O GitHub Actions espera uma estrutura de diretorios especifica:

```
.github/
  workflows/
    ci.yml                    # Workflow principal de CI
    cd.yml                    # Workflow de deploy
    release.yml               # Workflow de release
    security.yml              # Workflow de seguranca
  actions/
    setup-env/
      action.yml              # Composite action local
      entrypoint.sh
    notify-slack/
      action.yml
      index.js
  dependabot.yml              # Configuracao do Dependabot
  CODEOWNERS                  # Owners de codigo
```

Cada arquivo YAML na pasta `workflows/` e um workflow independente. Eles podem ser disparados por eventos diferentes, ter jobs diferentes, e rodar em paralelo ou sequencia.

---

## 1.3 Runner Types Detalhados

### GitHub-Hosted Runners

Os runners hospedados pelo GitHub sao maquinas virtuais gerenciadas pela GitHub que executam seus jobs. Sao a opcao mais simples e escalavel.

#### Especificacoes por Plataforma

**Linux Runners**:

| Runner | SO | CPU | RAM | Disco | GPU |
|--------|-----|-----|-----|-------|-----|
| ubuntu-latest | Ubuntu 22.04/24.04 | 2 cores | 7 GB | 14 GB | Nao |
| ubuntu-24.04 | Ubuntu 24.04 LTS | 2 cores | 7 GB | 14 GB | Nao |
| ubuntu-22.04 | Ubuntu 22.04 LTS | 2 cores | 7 GB | 14 GB | Nao |
| ubuntu-20.04 | Ubuntu 20.04 LTS | 2 cores | 7 GB | 14 GB | Nao |

**macOS Runners**:

| Runner | SO | CPU | RAM | Disco |
|--------|-----|-----|-----|-------|
| macos-latest | macOS 15 (Sequoia) | 3 cores (M1) | 7 GB | 14 GB |
| macos-15 | macOS 15 Sequoia | 3 cores (M1) | 7 GB | 14 GB |
| macos-14 | macOS 14 Sonoma | 3 cores (M1) | 7 GB | 14 GB |
| macos-13 | macOS 13 Ventura | 3 cores (Intel) | 7 GB | 14 GB |

**Windows Runners**:

| Runner | SO | CPU | RAM | Disco |
|--------|-----|-----|-----|-------|
| windows-latest | Windows Server 2022 | 2 cores | 7 GB | 14 GB |
| windows-2022 | Windows Server 2022 | 2 cores | 7 GB | 14 GB |
| windows-2019 | Windows Server 2019 | 2 cores | 7 GB | 14 GB |

**Larger Runners (pago)**:

| Runner | CPU | RAM | Disco | Preco/min |
|--------|-----|-----|-------|-----------|
| linux-latest-4-cores | 4 cores | 16 GB | 150 GB | $0.08 |
| linux-latest-8-cores | 8 cores | 32 GB | 300 GB | $0.16 |
| linux-latest-16-cores | 16 cores | 64 GB | 600 GB | $0.32 |
| linux-latest-32-cores | 32 cores | 128 GB | 1 TB | $0.64 |
| linux-latest-64-cores | 64 cores | 256 GB | 2 TB | $1.28 |
| windows-latest-8-cores | 8 cores | 32 GB | 300 GB | $0.16 |
| macos-latest-xlarge | 6 cores (M1) | 19 GB | 200 GB | $0.16 |

#### Software Pre-instalado

Os runners GitHub-hosted vem com uma serie de ferramentas pre-instaladas:

**Ubuntu Runner**:
```bash
# Sistema
Kernel: 5.15.0-1053-azure
Architecture: x64

# Linguagens
Python: 3.10.x, 3.11.x, 3.12.x
Node.js: 18.x, 20.x, 22.x
Ruby: 3.1.x, 3.2.x, 3.3.x
Java: 11, 17, 21
Go: 1.20.x, 1.21.x, 1.22.x
Rust: 1.75.x
PHP: 8.1.x, 8.2.x, 8.3.x
.NET: 6.0, 7.0, 8.0

# Ferramentas de build
CMake: 3.28.x
GCC: 11.x, 12.x
Clang: 14.x, 15.x
Docker: 24.x
Podman: 3.x

# Cloud CLIs
AWS CLI: 2.x
Azure CLI: 2.x
gcloud CLI: 470.x
Terraform: 1.6.x

# Outros
Git: 2.x
GitHub CLI: 2.x
PostgreSQL: 14.x
MySQL: 8.x
Redis: 7.x
MongoDB: 7.x
```

**macOS Runner**:
```bash
# Sistema
SO: macOS 14/15 (Apple Silicon M1)
Architecture: arm64

# Linguagens (via Homebrew)
Python: 3.11.x, 3.12.x
Node.js: 18.x, 20.x, 22.x
Ruby: 3.2.x, 3.3.x
Java: 11, 17, 21
Go: 1.20.x, 1.21.x, 1.22.x
Swift: 5.9.x

# Ferramentas
Xcode: 14.x, 15.x, 16.x
CMake: 3.28.x
Docker Desktop: 4.x
```

**Windows Runner**:
```powershell
# Sistema
SO: Windows Server 2022
Architecture: x64

# Linguagens
Python: 3.9.x, 3.10.x, 3.11.x, 3.12.x
Node.js: 18.x, 20.x, 22.x
Ruby: 3.1.x, 3.2.x
Java: 11, 17, 21
Go: 1.20.x, 1.21.x, 1.22.x
.NET: 4.8.x, 6.0, 7.0, 8.0

# Ferramentas
Visual Studio: 2019, 2022
MSBuild: 17.x
CMake: 3.28.x
Docker: 24.x
```

#### Ambiente dos Runners

Os runners GitHub-hosted possuem um ambiente padrao que voce pode inspecionar:

```yaml
jobs:
  inspect-runner:
    runs-on: ubuntu-latest
    steps:
      - name: Show runner environment
        run: |
          echo "=== System Info ==="
          uname -a
          echo ""
          echo "=== CPU Info ==="
          lscpu | head -20
          echo ""
          echo "=== Memory ==="
          free -h
          echo ""
          echo "=== Disk ==="
          df -h
          echo ""
          echo "=== Network ==="
          ip addr show | grep -E "inet " | head -5
          echo ""
          echo "=== Docker ==="
          docker --version
          docker compose version
          echo ""
          echo "=== Installed Tools ==="
          echo "Node: $(node --version)"
          echo "NPM: $(npm --version)"
          echo "Python: $(python3 --version)"
          echo "Git: $(git --version)"
          echo "Docker: $(docker --version)"

      - name: Show environment variables
        run: env | sort
```

**Variaveis de ambiente padrao disponiveis**:

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `CI` | Sempre `true` em workflows | `true` |
| `GITHUB_ACTIONS` | Sempre `true` | `true` |
| `GITHUB_ACTION` | Nome do step atual | `actions/checkout@v4` |
| `GITHUB_ACTION_PATH` | Path da action atual | `/home/runner/work/_actions/...` |
| `GITHUB_ACTION_REPOSITORY` | Repo da action | `actions/checkout` |
| `GITHUB_ACTOR` | Quem disparou o evento | `usuario` |
| `GITHUB_API_URL` | URL da API do GitHub | `https://api.github.com` |
| `GITHUB_BASE_REF` | Branch base do PR | `main` |
| `GITHUB_ENV` | Path do arquivo de env | `/home/runner/work/_temp/...` |
| `GITHUB_EVENT_NAME` | Nome do evento | `push`, `pull_request` |
| `GITHUB_EVENT_PATH` | Path do JSON do evento | `/home/runner/work/_temp/...` |
| `GITHUB_GRAPHQL_URL` | URL do GraphQL | `https://api.github.com/graphql` |
| `GITHUB_HEAD_REF` | Branch head do PR | `feature-x` |
| `GITHUB_JOB` | ID do job | `build` |
| `GITHUB_OUTPUT` | Path do arquivo de output | `/home/runner/work/_temp/...` |
| `GITHUB_PATH` | Path do arquivo PATH | `/home/runner/work/_temp/...` |
| `GITHUB_REF` | Ref completa | `refs/heads/main` |
| `GITHUB_REF_NAME` | Nome da ref | `main` |
| `GITHUB_REF_PROTECTED` | Se branch e protegida | `true` |
| `GITHUB_REF_TYPE` | Tipo da ref | `branch` |
| `GITHUB_REPOSITORY` | Owner/repo | `user/repo` |
| `GITHUB_REPOSITORY_ID` | ID numerico do repo | `123456` |
| `GITHUB_REPOSITORY_OWNER` | Owner do repo | `user` |
| `GITHUB_RETENTION_DAYS` | Dias de retencao de logs | `90` |
| `GITHUB_RUN_ID` | ID unico da execucao | `567890` |
| `GITHUB_RUN_NUMBER` | Numero sequencial | `42` |
| `GITHUB_SERVER_URL` | URL do GitHub | `https://github.com` |
| `GITHUB_SHA` | Commit SHA | `abc123def456...` |
| `GITHUB_TOKEN` | Token de autenticacao | `***` |
| `GITHUB_WORKSPACE` | Diretorio de trabalho | `/home/runner/work/repo/repo` |
| `RUNNER_ARCH` | Arquitetura do runner | `X64`, `ARM64` |
| `RUNNER_ENVIRONMENT` | Ambiente do runner | `github-hosted` |
| `RUNNER_NAME` | Nome do runner | `fv-az123-456` |
| `RUNNER_OS` | SO do runner | `Linux`, `macOS`, `Windows` |
| `RUNNER_TEMP` | Diretorio temporario | `/home/runner/work/_temp` |
| `RUNNER_TOOL_CACHE` | Cache de tools | `/opt/hostedtoolcache` |

### Self-Hosted Runners

Os self-hosted runners sao maquinas que voce gerencia e configura para executar workflows do GitHub Actions.

#### Por Que Usar Self-Hosted Runners?

| Cenario | Motivacao |
|---------|-----------|
| Hardware especial | GPUs, muita RAM, SSDs rapidos |
| Software proprietario | Ferramentas que nao podem ser instaladas em runners publicos |
| Seguranca | Codigo sensivel nao pode sair da sua rede |
| Custo | Workloads longos sao mais baratos no proprio hardware |
| Performance | Executors personalizados para seu caso de uso |
| Compliance | Regulamentacoes que exigem infraestrutura propria |
| Acesso a rede | Acesso a bancos de dados internos, VPNs, etc. |

#### Configuracao de um Self-Hosted Runner

**Passo 1: Criar o runner no GitHub**

1. Acesse Settings > Actions > Runners do seu repositorio
2. Clique em "New self-hosted runner"
3. Selecione o SO (Linux, macOS, Windows)
4. Siga as instrucoes de download

**Passo 2: Instalar e configurar**

```bash
# Linux/macOS
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.321.0.tar.gz

# Configurar (substitua pelo seu token)
./config.sh --url https://github.com/OWNER/REPO --token YOUR_TOKEN

# Instalar como servico (Linux)
sudo ./svc.sh install
sudo ./svc.sh start
```

```powershell
# Windows
mkdir actions-runner; cd actions-runner
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-win-x64-2.321.0.zip -OutFile actions-runner-win-x64-2.321.0.zip
Expand-Archive -Path actions-runner-win-x64-2.321.0.zip -DestinationPath .

# Configurar
.\config.cmd --url https://github.com/OWNER/REPO --token YOUR_TOKEN

# Instalar como servico Windows
.\svc install
.\svc start
```

**Passo 3: Configurar o workflow**

```yaml
jobs:
  build:
    runs-on: self-hosted  # Usa o runner self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: echo "Rodando no meu runner!"
```

**Passo 4: Labels customizados**

```yaml
jobs:
  gpu-training:
    runs-on: [self-hosted, gpu, nvidia]  # Seleciona runners com essas labels
    steps:
      - run: nvidia-smi
      - run: python train.py

  big-memory:
    runs-on: [self-hosted, ram-256gb]
    steps:
      - run: process-large-dataset.sh
```

#### Seguranca dos Self-Hosted Runners

```yaml
# Configuracao segura do runner
# .github/workflows/secure-self-hosted.yml

name: Secure Self-Hosted Workflow

on:
  push:
    branches: [main]

jobs:
  secure-build:
    runs-on: [self-hosted, isolated]
    # Isso garante que o runner e isolado
    # e so executa um job por vez
    concurrency:
      group: self-hosted-${{ github.ref }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4

      - name: Validate runner environment
        run: |
          # Verificar se o runner e confiavel
          if [ "$RUNNER_ENVIRONMENT" != "self-hosted" ]; then
            echo "Runner nao e self-hosted! Abortando."
            exit 1
          fi

          # Verificar se o diretorio de trabalho e o esperado
          if [[ "$GITHUB_WORKSPACE" != /safe/workspace/* ]]; then
            echo "Workspace inesperado! Abortando."
            exit 1
          fi

      - name: Build
        run: make build

      - name: Cleanup
        if: always()
        run: |
          # Limpar apos cada execucao
          rm -rf $GITHUB_WORKSPACE/build
          docker system prune -f
```

#### Gerenciamento de Runners em Escala

Para organizacoes com muitos runners, use ferramentas de gerenciamento:

```yaml
# Exemplo de workflow que gerencia runners via Terraform
name: Manage Self-Hosted Runners

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Runner action'
        required: true
        type: choice
        options:
          - scale-up
          - scale-down
          - update
          - status

jobs:
  manage-runners:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Scale runners
        run: |
          case "${{ inputs.action }}" in
            scale-up)
              terraform apply -auto-approve -var="runner_count=10"
              ;;
            scale-down)
              terraform apply -auto-approve -var="runner_count=2"
              ;;
            update)
              # Atualizar AMI dos runners
              packer build runner-template.json
              terraform apply -auto-approve
              ;;
            status)
              aws ec2 describe-instances \
                --filters "Name=tag:Role,Values=github-runner" \
                --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PrivateIpAddress]' \
                --output table
              ;;
          esac
```

---

## 1.4 Marketplace de Actions

### O que e o Marketplace?

O GitHub Actions Marketplace e um repositorio central de actions reutilizaveis que a comunidade e empresas desenvolveram. Actualmente, existem mais de 20.000 actions disponiveis.

### Como Selecionar uma Action

Ao escolher uma action, considere:

| Criterio | O que verificar |
|----------|-----------------|
| Popularidade | Numero de estrelas, forks, uso |
| Manutencao | Ultimo commit, issues abertas, PRs pendentes |
| Seguranca | Verified creator, pinning de hash |
| Documentacao | README claro, exemplos de uso |
| Compatibilidade | Suporte a ultima versao do GitHub Actions |
| Licenca | Compativel com seu projeto |

### Actions Populares

#### Checkout

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history
    submodules: true  # Submodules
    token: ${{ secrets.GITHUB_TOKEN }}
    ref: ${{ github.head_ref }}  # Branch do PR
```

#### Setup Languages

```yaml
# Node.js
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
    registry-url: 'https://registry.npmjs.org'

# Python
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'

# Java
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'temurin'
    cache: 'maven'

# Go
- uses: actions/setup-go@v5
  with:
    go-version: '1.22'
    cache: true

# Rust
- uses: dtolnay/rust-toolchain@stable
  with:
    components: rustfmt, clippy

# Docker
- uses: docker/setup-buildx-action@v3
  with:
    driver-opts: network=host
```

#### Cache

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

#### Upload/Download Artifacts

```yaml
# Upload
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: |
      dist/
      *.exe
    retention-days: 7
    compression-level: 6

# Download
- uses: actions/download-artifact@v4
  with:
    name: build-output
    path: dist/
    merge-multiple: true  # Merge multiple artifacts
```

#### Cloud Providers

```yaml
# AWS
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/my-role
    aws-region: us-east-1

# Azure
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

# Google Cloud
- uses: google-github-actions/auth@v2
  with:
    credentials_json: ${{ secrets.GCP_SA_KEY }}
    project_id: my-project
```

#### Notifications

```yaml
# Slack
- uses: slackapi/slack-github-action@v1
  with:
    channel-id: 'C0123456789'
    slack-message: "Deploy: ${{ job.status }}"
  env:
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}

# Discord
- uses: Ilshidur/discord-notify@master
  with:
    webhook: ${{ secrets.DISCORD_WEBHOOK }}
    message: 'Build ${{ github.run_number }} completed!'

# Email (via SendGrid)
- uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.sendgrid.net
    server_port: 587
    username: apikey
    password: ${{ secrets.SENDGRID_API_KEY }}
    subject: 'Build ${{ github.run_number }} - ${{ job.status }}'
    to: devs@empresa.com
    from: CI <ci@empresa.com>
    body: 'Build completed with status: ${{ job.status }}'
```

### Criando Actions Proprias

Voce pode criar actions reutilizaveis para sua organizacao:

**Composite Action** (recomendado para logica simples):

```yaml
# .github/actions/setup-project/action.yml
name: 'Setup Project'
description: 'Setup project dependencies and tools'
branding:
  icon: 'package'
  color: 'blue'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'
  java-version:
    description: 'Java version'
    required: false
    default: ''
  python-version:
    description: 'Python version'
    required: false
    default: ''
  install-dependencies:
    description: 'Install dependencies'
    required: false
    default: 'true'

outputs:
  node-version:
    description: 'Installed Node.js version'
    value: ${{ steps.node.outputs.version }}

runs:
  using: 'composite'
  steps:
    - name: Setup Node.js
      if: inputs.node-version != ''
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - name: Setup Java
      if: inputs.java-version != ''
      uses: actions/setup-java@v4
      with:
        java-version: ${{ inputs.java-version }}
        distribution: 'temurin'
        cache: 'maven'

    - name: Setup Python
      if: inputs.python-version != ''
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
        cache: 'pip'

    - name: Install dependencies
      if: inputs.install-dependencies == 'true'
      shell: bash
      run: |
        if [ -f package.json ]; then
          npm ci
        fi
        if [ -f pom.xml ]; then
          mvn -B dependency:resolve
        fi
        if [ -f requirements.txt ]; then
          pip install -r requirements.txt
        fi

    - name: Output node version
      if: inputs.node-version != ''
      id: node
      shell: bash
      run: echo "version=$(node --version)" >> $GITHUB_OUTPUT
```

**JavaScript Action** (para logica complexa):

```yaml
# .github/actions/deploy-s3/action.yml
name: 'Deploy to S3'
description: 'Deploy files to S3 with invalidation'
inputs:
  bucket:
    description: 'S3 bucket name'
    required: true
  distribution-id:
    description: 'CloudFront distribution ID'
    required: false
  source:
    description: 'Source directory'
    required: false
    default: 'dist/'
outputs:
  url:
    description: 'Deployed URL'
    value: ${{ steps.deploy.outputs.url }}
runs:
  using: 'node20'
  main: 'dist/index.js'
```

```javascript
// .github/actions/deploy-s3/src/index.js
const core = require('@actions/core');
const github = require('@actions/github');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
const { CloudFrontClient, CreateInvalidationCommand } = require('@aws-sdk/client-cloudfront');

async function run() {
  try {
    const bucket = core.getInput('bucket');
    const distributionId = core.getInput('distribution-id');
    const source = core.getInput('source') || 'dist/';

    const s3Client = new S3Client({});
    const cfClient = new CloudFrontClient({});

    // Upload files to S3
    const files = await glob(`${source}/**/*`);
    for (const file of files) {
      const key = file.replace(source, '');
      const body = fs.readFileSync(file);
      await s3Client.send(new PutObjectCommand({
        Bucket: bucket,
        Key: key,
        Body: body,
        ContentType: getContentType(file),
      }));
    }

    // Invalidate CloudFront cache
    if (distributionId) {
      await cfClient.send(new CreateInvalidationCommand({
        DistributionId: distributionId,
        InvalidationBatch: {
          CallerReference: Date.now().toString(),
          Paths: {
            Quantity: 1,
            Items: ['/*'],
          },
        },
      }));
    }

    core.setOutput('url', `https://${bucket}.s3.amazonaws.com`);
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
```

### Usando Actions de Terceiros

```yaml
# Exemplo completo usando multiplas actions
name: CI/CD Pipeline

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Para OIDC
      packages: write  # Para GitHub Packages
    steps:
      - uses: actions/checkout@v4

      - name: Setup project
        uses: ./.github/actions/setup-project
        with:
          node-version: '20'

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: true

      - name: Build
        run: npm run build

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Deploy to AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ecs-task-def.json
          service: my-service
          cluster: my-cluster
          wait-for-service-stability: true
```

---

## 1.5 Environment Variables e Contexts

### Hierarquia de Variaveis

O GitHub Actions possui uma hierarquia de variaveis que determina prioridade e escopo:

```
Step-level env
    |
    v
Job-level env
    |
    v
Workflow-level env
    |
    v
Repository variables (vars)
    |
    v
Organization variables (vars)
    |
    v
System environment variables
```

### Definindo Variaveis

**Workflow-level**:

```yaml
name: My Workflow

env:
  APP_NAME: my-application
  NODE_VERSION: '20'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo $APP_NAME  # Disponivel aqui
```

**Job-level**:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    env:
      BUILD_ENV: production
    steps:
      - run: echo $BUILD_ENV  # Disponivel aqui
      - run: echo $APP_NAME   # Tambem disponivel (herda do workflow)

  test:
    runs-on: ubuntu-latest
    env:
      TEST_ENV: staging
    steps:
      - run: echo $TEST_ENV   # Disponivel aqui
      - run: echo $BUILD_ENV  # NAO disponivel (escopo de outro job)
```

**Step-level**:

```yaml
steps:
  - name: Step with custom env
    run: echo $CUSTOM_VAR
    env:
      CUSTOM_VAR: from-step
      ANOTHER_VAR: another-value
```

### Contexts Disponiveis

Os contexts sao objetos especiais que fornecem acesso a informacoes do workflow:

#### github

```yaml
# Dados do repositorio e evento
${{ github.repository }}           # owner/repo
${{ github.sha }}                  # Commit SHA
${{ github.ref }}                  # refs/heads/main
${{ github.ref_name }}             # main
${{ github.ref_type }}             # branch
${{ github.actor }}                # Quem disparou
${{ github.event_name }}           # push, pull_request
${{ github.event_path }}           # Path do JSON do evento
${{ github.run_id }}               # ID da execucao
${{ github.run_number }}           # Numero sequencial
${{ github.job }}                  # ID do job
${{ github.server_url }}           # https://github.com
${{ github.api_url }}              # https://api.github.com
${{ github.workspace }}            # Diretorio de trabalho

# Para pull requests
${{ github.event.pull_request.number }}
${{ github.event.pull_request.title }}
${{ github.event.pull_request.head.ref }}
${{ github.event.pull_request.base.ref }}
${{ github.event.pull_request.changed_files }}
${{ github.event.pull_request.additions }}
${{ github.event.pull_request.deletions }}
${{ github.event.pull_request.user.login }}

# Para push
${{ github.event.before }}         # SHA anterior
${{ github.event.head_commit.message }}
${{ github.event.head_commit.author.name }}
${{ github.event.commits }}        # Array de commits
```

#### env

```yaml
env:
  MY_VAR: hello
steps:
  - run: echo ${{ env.MY_VAR }}
```

#### vars (Repository/Organization Variables)

```yaml
# Definidas em Settings > Secrets and variables > Actions
steps:
  - run: echo ${{ vars.APP_NAME }}
  - run: echo ${{ vars.DEPLOY_CONFIG }}
```

#### secrets

```yaml
steps:
  - run: echo "Token: ${{ secrets.GITHUB_TOKEN }}"
  - run: echo "AWS Key: ${{ secrets.AWS_ACCESS_KEY_ID }}"
    # Secrets sao automaticamente mascarados nos logs
```

#### needs

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.meta.outputs.version }}
    steps:
      - id: meta
        run: echo "version=1.0.0" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Version: ${{ needs.build.outputs.version }}"
```

#### strategy

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - run: echo "OS: ${{ strategy.job-index }}"
```

#### matrix

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20]
    steps:
      - run: echo "Testing on ${{ matrix.os }} with Node ${{ matrix.node }}"
```

#### inputs

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploy to ${{ inputs.environment }}"
```

#### runner

```yaml
steps:
  - run: |
      echo "OS: ${{ runner.os }}"
      echo "Arch: ${{ runner.arch }}"
      echo "Name: ${{ runner.name }}"
      echo "Temp: ${{ runner.temp }}"
      echo "Tool Cache: ${{ runner.tool_cache }}"
```

### Expressoes e Operadores

O GitHub Actions suporta expressoesJavaScript-like:

```yaml
# Operadores de comparacao
if: github.event_name == 'push'
if: github.ref != 'refs/heads/main'
if: github.event.pull_request.merged == true

# Operadores logicos
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
if: github.event_name == 'push' || github.event_name == 'pull_request'
if: !(github.event_name == 'push')

# Funcoes de string
if: contains(github.event.pull_request.title, '[deploy]')
if: startsWith(github.ref, 'refs/tags/v')
if: endsWith(github.event.pull_request.head.ref, '-fix')
if: format('Deploying {0} to {1}', github.sha, inputs.environment)

# Funcoes de array
if: contains(join(github.event.pull_request.labels.*.name, ','), 'deploy')
if: length(github.event.pull_request.body) > 100

# Funcoes de hash
run: echo "${{ hashFiles('**/package-lock.json') }}"
run: echo "${{ hashFiles('requirements.txt', 'Pipfile.lock') }}"

# Funcoes de JSON
env:
  CONFIG: ${{ fromJSON(vars.BUILD_CONFIG) }}
run: echo "${{ toJSON(github.event) }}"

# Ternario operator
env:
  NODE_VERSION: ${{ github.ref == 'refs/heads/main' && '20' || '18' }}
```

### Funcoes de Expressao Detalhadas

| Funcao | Descricao | Exemplo |
|--------|-----------|---------|
| `contains(str, substr)` | Verifica se str contem substr | `contains('hello', 'ell')` = `true` |
| `startsWith(str, prefix)` | Verifica se str comeca com prefix | `startsWith('refs/tags/v', 'refs/tags/v')` = `true` |
| `endsWith(str, suffix)` | Verifica se str termina com suffix | `endsWith('file.txt', '.txt')` = `true` |
| `format(template, ...args)` | Formata string com placeholders | `format('{0} is {1}', 'a', 'b')` = `'a is b'` |
| `join(array, sep)` | Junta array com separador | `join(['a','b'], '-')` = `'a-b'` |
| `split(str, sep)` | Divide string em array | `split('a-b-c', '-')` = `['a','b','c']` |
| `length(array)` | Tamanho do array | `length(['a','b'])` = `2` |
| `fromJSON(str)` | Converte JSON para objeto | `fromJSON('{"a":1}')` = `{a: 1}` |
| `toJSON(obj)` | Converte objeto para JSON | `toJSON({a:1})` = `'{"a":1}'` |
| `hashFiles(...paths)` | Hash SHA256 dos arquivos | `hashFiles('**/*.js')` = `'abc123...'` |
| `always()` | Sempre true (pos-condicional) | `if: always()` |
| `success()` | Se todos anteriores foram sucesso | `if: success()` |
| `cancelled()` | Se workflow foi cancelado | `if: cancelled()` |
| `failure()` | Se algum anterior falhou | `if: failure()` |
| `steps.id.result` | Resultado de um step anterior | `if: steps.build.result == 'success'` |
| `needs.job.result` | Resultado de um job anterior | `if: needs.test.result == 'success'` |

---

## 1.6 Exemplo Completo

### Pipeline CI/CD Full-Stack

Este exemplo demonstra um workflow completo para uma aplicacao full-stack:

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

# Triggers
on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'package.json'
      - 'package-lock.json'
      - '.github/workflows/**'
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.vscode/**'

  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]

  workflow_dispatch:
    inputs:
      deploy_environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production
      skip_tests:
        description: 'Skip tests'
        type: boolean
        default: false

# Workflow-level environment variables
env:
  NODE_VERSION: '20'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

# Concurrency group
concurrency:
  group: ci-cd-${{ github.ref }}
  cancel-in-progress: true

# Jobs
jobs:
  # ============================================
  # LINT JOB
  # ============================================
  lint:
    name: Code Lint
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run Prettier check
        run: npm run format:check

      - name: Run TypeScript check
        run: npm run typecheck

  # ============================================
  # TEST JOB (Matrix)
  # ============================================
  test:
    name: Test (Node ${{ matrix.node-version }}, ${{ matrix.os }})
    needs: lint
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20

    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        node-version: [18, 20, 22]
        include:
          - os: ubuntu-latest
            node-version: 20
            primary: true
        exclude:
          - os: windows-latest
            node-version: 18
      fail-fast: false

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        if: ${{ !inputs.skip_tests }}
        run: npm run test:unit
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

      - name: Run integration tests
        if: ${{ !inputs.skip_tests && matrix.primary }}
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage
        if: matrix.primary
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/lcov.info
          flags: unittests
          fail_ci_if_error: false

  # ============================================
  # SECURITY SCAN
  # ============================================
  security:
    name: Security Scan
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      security-events: write
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run npm audit
        run: npm audit --audit-level=high

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  # ============================================
  # BUILD JOB
  # ============================================
  build:
    name: Build
    needs: [test, security]
    if: inputs.skip_tests || (needs.test.result == 'success' && needs.security.result == 'success')
    runs-on: ubuntu-latest
    timeout-minutes: 15

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/
          retention-days: 7

      - name: Docker meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  # ============================================
  # DEPLOY STAGING
  # ============================================
  deploy-staging:
    name: Deploy to Staging
    needs: build
    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      (inputs.deploy_environment == 'staging' || inputs.deploy_environment == '')
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment:
      name: staging
      url: https://staging.myapp.com

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_STAGING }}
          aws-region: us-east-1

      - name: Deploy to ECS (Staging)
        run: |
          aws ecs update-service \
            --cluster staging-cluster \
            --service myapp-staging \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster staging-cluster \
            --services myapp-staging

      - name: Run smoke tests
        run: |
          sleep 30
          curl -f https://staging.myapp.com/health || exit 1
          echo "Smoke tests passed!"

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: 'C0123456789'
          slack-message: |
            Deploy to staging: ${{ job.status }}
            Actor: ${{ github.actor }}
            Commit: ${{ github.sha }}
            URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}

  # ============================================
  # DEPLOY PRODUCTION
  # ============================================
  deploy-production:
    name: Deploy to Production
    needs: build
    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      inputs.deploy_environment == 'production'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment:
      name: production
      url: https://myapp.com

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PRODUCTION }}
          aws-region: us-east-1

      - name: Create deployment record
        run: |
          aws dynamodb put-item \
            --table-name deployments \
            --item '{
              "id": {"S": "${{ github.run_id }}"},
              "environment": {"S": "production"},
              "commit": {"S": "${{ github.sha }}"},
              "actor": {"S": "${{ github.actor }}"},
              "timestamp": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"},
              "status": {"S": "in_progress"}
            }'

      - name: Deploy to ECS (Production)
        run: |
          aws ecs update-service \
            --cluster production-cluster \
            --service myapp-production \
            --force-new-deployment

      - name: Wait for deployment
        run: |
          aws ecs wait services-stable \
            --cluster production-cluster \
            --services myapp-production

      - name: Health check
        run: |
          for i in {1..30}; do
            if curl -sf https://myapp.com/health; then
              echo "Health check passed!"
              exit 0
            fi
            echo "Attempt $i/30 - waiting..."
            sleep 10
          done
          echo "Health check failed!"
          exit 1

      - name: Update deployment status
        if: always()
        run: |
          STATUS="success"
          if [ "${{ job.status }}" != "success" ]; then
            STATUS="failed"
          fi
          aws dynamodb update-item \
            --table-name deployments \
            --key '{"id": {"S": "${{ github.run_id }}"}}' \
            --update-expression "SET #s = :s" \
            --expression-attribute-names '{"#s": "status"}' \
            --expression-attribute-values '{":s": {"S": "'$STATUS'"}}'
```

---

## 1.7 Comparacao com GitLab CI, Jenkins e Travis CI

### Tabela Comparativa Geral

| Caracteristica | GitHub Actions | GitLab CI | Jenkins | Travis CI |
|---------------|---------------|-----------|---------|-----------|
| **Tipo** | Servico integrado | Servico integrado | Self-hosted | Servico |
| **Setup** | Minimo | Minimo | Complexo | Facil |
| **Configuracao** | YAML no repo | `.gitlab-ci.yml` | Jenkinsfile/Interface | `.travis.yml` |
| **Marketplace** | 20K+ actions | 5K+ templates | 1.8K+ plugins | 100+ integrations |
| **Matrix builds** | Nativo | Nativo | Via plugins | Limitado |
| **Reusable pipelines** | Sim | Sim | Shared libraries | Nao |
| **OIDC** | Nativo | Nativo | Plugin | Nao |
| **Secrets management** | Nativo | Nativo | Plugins | Nativo |
| **Self-hosted runners** | Sim | Sim | Sim (obrigatorio) | Sim |
| **Container support** | Nativo | Nativo | Docker plugin | Sim |
| **Free tier** | 2.000 min/mes | 400 min/mes | Ilimitado (self-hosted) | 10K credits |
| **GitHub integration** | Nativa | Via API | Via plugins | Nativa |
| **GitLab integration** | Via API | Nativa | Via plugins | Limitado |
| **Pipeline visualization** | Sim | Sim (melhor) | Sim | Sim |
| **Environments** | Sim | Sim (melhor) | Via plugins | Nao |
| **Review apps** | Via actions | Nativo | Via plugins | Nao |
| **Package registry** | GH Packages | GitLab Registry | Nexus/Artifactory | Nao |
| **Container registry** | GHCR | GitLab | Nexus/Artifactory | Nao |
| **Security scanning** | Via actions | Nativo (SAST/DAST) | Plugins | Limitado |
| **Compliance** | Via actions | Nativo | Via plugins | Nao |
| **Multi-cloud** | AWS/Azure/GCP | AWS/Azure/GCP | Qualquer | AWS |
| **API** | REST/GraphQL | REST | REST | REST |
| **CLI** | GitHub CLI (`gh`) | GitLab CLI (`glab`) | Jenkins CLI | Travis CLI |

### GitHub Actions vs GitLab CI

#### Filosofia

- **GitHub Actions**: Marketplace-centric. A forca esta na reusabilidade de actions da comunidade e na integracao nativa com o GitHub.
- **GitLab CI**: All-in-one. Oferece SAST, DAST, container registry, package registry, e muito mais integrado.

#### Configuracao

```yaml
# GitHub Actions (.github/workflows/ci.yml)
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: echo "Deploying..."
```

```yaml
# GitLab CI (.gitlab-ci.yml)
stages:
  - test
  - deploy

variables:
  NODE_VERSION: "20"

test:
  stage: test
  image: node:${NODE_VERSION}
  cache:
    paths:
      - node_modules/
  script:
    - npm ci
    - npm test

deploy:
  stage: deploy
  script:
    - echo "Deploying..."
  only:
    - main
  environment:
    name: production
    url: https://myapp.com
```

#### Diferencas Principais

| Aspecto | GitHub Actions | GitLab CI |
|---------|---------------|-----------|
| **Variaveis pre-definidas** | ~40 variaveis | ~50 variaveis |
| **Cache** | Via actions/cache | Nativo com `cache:` |
| **Artifacts** | Via upload/download-artifact | Nativo com `artifacts:` |
| **Services** | Containers Docker | Containers Docker |
| **Includes** | Reusable workflows | `include:` keyword |
| **Rules de trigger** | `on:` block | `rules:` keyword |
| **Needs** | `needs:` keyword | `needs:` keyword |
| **Parallel** | Matrix strategy | `parallel:` keyword |
| **Environments** | Via config | Nativo com `environment:` |
| **Variables protegidas** | Secrets | Protected variables |
| **Variables de escopo** | Environments | Environments + deployment slots |

### GitHub Actions vs Jenkins

#### Filosofia

- **GitHub Actions**: Configuracao como codigo, minimalismo, integracao nativa.
- **Jenkins**: Flexibilidade total, plugin-based, steep learning curve.

#### Configuracao

```yaml
# GitHub Actions
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
```

```groovy
// Jenkinsfile
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'npm ci'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
    }
}
```

#### Diferencas Principais

| Aspecto | GitHub Actions | Jenkins |
|---------|---------------|---------|
| **Setup** | Instantaneo | Horas (setup + plugins) |
| **Manutencao** | Zero | Constante (atualizacoes, seguranca) |
| **Plugins** | Actions do Marketplace | 1.8K+ plugins |
| **Interface** | Moderna, nativa do GitHub | Desatualizada |
| **Pipeline como codigo** | YAML | Groovy (Jenkinsfile) |
| **Distributed builds** | Runners | Agents |
| **Credential management** | Secrets nativos | Credential plugin |
| **Multi-branch** | Configuravel | Multibranch plugin |
| **Pipeline visualization** | Basica | Blue Ocean (plugin) |
| **Elasticidade** | Automatica | Manual (agents) |
| **Custo** | Free tier + pago | Gratis (self-hosted) |
| **Escalabilidade** | Automatica | Manual |
| **Comunidade** | GitHub-centric | Independente |

### GitHub Actions vs Travis CI

#### Filosofia

- **GitHub Actions**: Evolucao do conceito que o Travis CI popularizou.
- **Travis CI**: Pioneer do CIaaS, agora em declinio.

#### Configuracao

```yaml
# GitHub Actions
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci && npm test
```

```yaml
# Travis CI
language: node_js
node_js:
  - "18"
  - "20"
  - "22"
cache:
  directories:
    - node_modules
script:
  - npm test
```

#### Diferencas Principais

| Aspecto | GitHub Actions | Travis CI |
|---------|---------------|-----------|
| **Status atual** | Crescimento rapido | Em declinio |
| **Pricing** | Free tier generoso | Credits limitados |
| **Features** | Mais completas | Mais basicas |
| **Marketplace** | 20K+ actions | 100+ integrations |
| **Matrix builds** | Completa | Basica |
| **Self-hosted** | Sim | Sim |
| **OIDC** | Sim | Nao |
| **Reusable workflows** | Sim | Nao |
| **Community** | Crescente | Estavel/declinio |

---

## 1.8 Custos e Limits

### Planos e Precos

| Recurso | Free | Team ($4/usuario/mes) | Enterprise ($21/usuario/mes) |
|---------|------|----------------------|------------------------------|
| GitHub-hosted Linux | 2.000 min/mes | 3.000 min/mes | 50.000 min/mes |
| GitHub-hosted macOS | 500 min/mes | 750 min/mes | 12.500 min/mes |
| GitHub-hosted Windows | 2.000 min/mes | 3.000 min/mes | 50.000 min/mes |
| Storage (artifacts) | 500 MB | 2 GB | 50 GB |
| Packages storage | 500 MB | 2 GB | 50 GB |
| Self-hosted runners | Ilimitado | Ilimitado | Ilimitado |
| Concurrency (repositorio) | 20 | 40 | 500 |
| Concurrency (organizacao) | 20 | 40 | 500 |
| Job timeout | 6 horas | 6 horas | 6 horas |

### Precos por Minuto (após exceder free tier)

| Runner | Preco/minuto | Preco/hora |
|--------|-------------|------------|
| Linux (2 cores) | $0.008 | $0.48 |
| Linux (4 cores) | $0.016 | $0.96 |
| Linux (8 cores) | $0.032 | $1.92 |
| Linux (16 cores) | $0.064 | $3.84 |
| Linux (32 cores) | $0.128 | $7.68 |
| Linux (64 cores) | $0.256 | $15.36 |
| macOS (M1, 3 cores) | $0.08 | $4.80 |
| macOS (M1, 6 cores) | $0.16 | $9.60 |
| Windows (2 cores) | $0.016 | $0.96 |

### Limites Importantes

| Limite | Valor | Descricao |
|--------|-------|-----------|
| Max workflow duration | 6 horas | Job timeout padrao |
| Max steps por job | 1,000 | Limite de steps |
| Max jobs por workflow | 256 | Limite de jobs |
| Max matrix combinations | 256 | Combinacoes de matrix |
| Max concurrency (Free) | 20 | Workflows simultaneos |
| Max artifact size | 10 GB | Tamanho total de artifacts |
| Max artifact retention | 90 dias | Para logs; artifacts seguem politica de billing |
| Max env variable size | 48 KB | Tamanho por variavel |
| Max secret size | 48 KB | Tamanho por secret |
| Max workflow file size | 1 MB | Tamanho do YAML |
| Max reusable workflow depth | 4 | Niveis de chamadas |

### Calculando Custos

**Exemplo 1: Projeto pequeno (open source)**

```yaml
# Supondo:
# - 100 builds por semana
# - 5 minutos por build
# - ubuntu-latest
# - Free tier

# Calculo:
# 100 builds/semana * 4 semanas = 400 builds/mes
# 400 builds * 5 min = 2,000 min/mes
#刚好 no free tier (2,000 min)
# Custo: $0
```

**Exemplo 2: Startup mediana**

```yaml
# Supondo:
# - 500 builds por semana
# - 8 minutos por build (media)
# - 60% ubuntu, 30% macOS, 10% windows
# - Team plan ($4 x 10 devs = $40/mes)

# Calculo:
# 500 * 4 = 2,000 builds/mes
# Media = 2,000 * 8 min = 16,000 min/mes
# Linux (60%): 9,600 min - 3,000 free = 6,600 min * $0.008 = $52.80
# macOS (30%): 4,800 min - 750 free = 4,050 min * $0.08 = $324.00
# Windows (10%): 1,600 min - 3,000 free = 0 min (dentro do free)
# Total: $52.80 + $324.00 + $40.00 = $416.80/mes
```

**Exemplo 3: Empresa grande**

```yaml
# Supondo:
# - 5,000 builds por semana
# - 12 minutos por build
# - 70% ubuntu, 20% macOS, 10% windows
# - Enterprise plan ($21 x 100 devs = $2,100/mes)
# - Uso de larger runners (8 cores para builds criticos)

# Calculo:
# 5,000 * 4 = 20,000 builds/mes
# Media = 20,000 * 12 min = 240,000 min/mes
# Linux (70%): 168,000 min - 50,000 free = 118,000 min * $0.008 = $944.00
# macOS (20%): 48,000 min - 12,500 free = 35,500 min * $0.08 = $2,840.00
# Windows (10%): 24,000 min - 50,000 free = 0 min (dentro do free)
# Larger runners (10% dos builds): 2,000 * 12 min = 24,000 min * $0.032 = $768.00
# Enterprise: $2,100.00
# Total: $944.00 + $2,840.00 + $768.00 + $2,100.00 = $6,652.00/mes
```

### Estrategias de Otimizacao de Custo

```yaml
# 1. Usar cache agressivamente
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{
 runner.os }}-node-

# 2. Usar concurrency groups para cancelar builds antigos
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# 3. Usar paths filters para nao rodar builds desnecessarios
on:
  push:
    paths:
      - 'src/**'  # So roda quando src/ muda

# 4. Usar conditional jobs
jobs:
  deploy:
    if: github.ref == 'refs/heads/main'  # So deploy na main

# 5. Usar self-hosted runners para workloads pesados
  big-build:
    runs-on: self-hosted  # Gratis no proprio hardware

# 6. Usar matrix strategy com fail-fast
  test:
    strategy:
      fail-fast: true  # Cancela outros se um falhar
```

---

## 1.9 Security Basics

### Principeios de Seguranca

O GitHub Actions segue o principio de **menor privilegio**: cada workflow, job, e step deve ter apenas as permissoes necessarias para completar sua tarefa.

### GITHUB_TOKEN

O `GITHUB_TOKEN` e um token automaticamente gerado para cada execucao de workflow:

```yaml
# Permissoes padrao do GITHUB_TOKEN
permissions:
  contents: read        # Ler repositorio
  issues: write         # Criar/comentar issues
  pull-requests: write  # Criar/comentar PRs
  packages: write       # Push para GH Packages
  actions: read         # Ler outros workflows

# Workflow-level (aplica a todos os jobs)
permissions:
  contents: read

# Job-level (sobrescreve o workflow-level)
jobs:
  build:
    permissions:
      contents: read
    steps:
      - run: echo "Pode ler o repo"

  deploy:
    permissions:
      contents: read
      id-token: write  # Para OIDC
      deployments: write
    steps:
      - run: echo "Pode fazer deploy"
```

### Secrets Management

```yaml
# Boas praticas para secrets
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Configure credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          # Usar OIDC em vez de access keys
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      # NUNCA faca isso:
      # - run: echo ${{ secrets.AWS_SECRET_KEY }}  # Expoe nos logs

      # NUNCA faca isso:
      # - run: export SECRET=${{ secrets.MY_SECRET }}  # Expoe em processos filhos

      # SIM, faca isso:
      - name: Use secret
        env:
          MY_SECRET: ${{ secrets.MY_SECRET }}
        run: |
          # A variavel so existe neste step
          # E automaticamente mascarada nos logs
          echo "Using secret..."
          use-secret.sh "$MY_SECRET"
```

### Protecao de Branches

```yaml
# Configuracao recomendada de branch protection
# (configurado em Settings > Branches)

# Protecoes para a branch main:
# - Require pull request before merging
# - Require approvals: 1
# - Dismiss stale reviews
# - Require review from code owners
# - Require status checks to pass
# - Require branches to be up to date
# - Require conversation resolution
# - Require signed commits
# - Require linear history
# - Include administrators
# - Restrict who can push to matching branches
# - Allow force pushes: false
# - Allow deletions: false
```

### Security Scanning no Workflow

```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira

permissions:
  contents: read
  security-events: write

jobs:
  codeql:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
          queries: security-and-quality
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3

  trivy:
    name: Trivy Scanner
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'results.sarif'
          severity: 'CRITICAL,HIGH'
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'results.sarif'

  dependency-review:
    name: Dependency Review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0
```

### Hardening de Runners

```yaml
# Configuracao segura para self-hosted runners
jobs:
  secure-build:
    runs-on: self-hosted
    timeout-minutes: 30
    steps:
      - name: Validate environment
        run: |
          # Verificar integridade do runner
          if [ "$RUNNER_ENVIRONMENT" != "self-hosted" ]; then
            echo "::error::Runner is not self-hosted!"
            exit 1
          fi

      - name: Checkout
        uses: actions/checkout@v4
        with:
          persist-credentials: false  # Nao persistir credenciais

      - name: Build
        run: |
          # Usar container para isolamento
          docker run --rm -v $GITHUB_WORKSPACE:/workspace alpine sh -c \
            "cd /workspace && make build"

      - name: Cleanup
        if: always()
        run: |
          # Limpar workspace apos cada execucao
          rm -rf $GITHUB_WORKSPACE/*
          docker system prune -f
          git -C $GITHUB_WORKSPACE clean -fdx
```

### OIDC para Cloud Providers

```yaml
# OIDC elimina a necessidade de long-lived credentials
jobs:
  deploy:
    permissions:
      id-token: write  # Necessario para OIDC
      contents: read
    steps:
      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1

      - name: Deploy
        run: aws s3 sync ./dist s3://my-bucket/

      # Nao e necessario armazenar AWS_ACCESS_KEY_ID ou AWS_SECRET_ACCESS_KEY
```

### Auditoria e Monitoring

```yaml
# Workflow de auditoria
name: Audit

on:
  schedule:
    - cron: '0 0 * * *'  # Diario

jobs:
  audit-secrets:
    name: Audit Secret Usage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: List repository secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh secret list --repo ${{ github.repository }}

  audit-runners:
    name: Audit Self-Hosted Runners
    runs-on: ubuntu-latest
    steps:
      - name: Check runner security
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # Verificar runners nao registrados
          gh api repos/${{ github.repository }}/actions/runners \
            --jq '.runners[] | select(.status == "online") | {name, labels}'
```

---

## 1.10 Exercicios

### Exercicio 1: Workflow Basico

Crie um workflow basico que imprima "Hello from GitHub Actions!" quando houver um push para a branch main.

**Dica**: Use `on: push: branches: [main]` e `run: echo "Hello from GitHub Actions!"`

### Exercicio 2: Multiplos Triggers

Modifique o workflow anterior para tambem rodar em pull requests para a branch main. Adicione um condicional que muda a mensagem baseado no tipo de evento.

**Dica**: Use `${{ github.event_name }}` para verificar o tipo de evento.

### Exercicio 3: Jobs com Dependencias

Crie um workflow com dois jobs:
1. Um job "build" que roda primeiro
2. Um job "deploy" que depende do "build" (usa `needs`)

O job "deploy" so deve rodar se o "build" foi bem-sucedido.

**Dica**: Use `needs: build` e `if: success()` ou `if: needs.build.result == 'success'`.

### Exercicio 4: Matrix Build

Configure um workflow que teste em:
- 3 sistemas operacionais (ubuntu, macos, windows)
- 2 versoes de Node.js (18, 20)
- Com `fail-fast: false`

**Dica**: Use `strategy.matrix` com arrays para os valores.

### Exercicio 5: Services

Crie um workflow que inicie um container PostgreSQL como service e execute um script que verifica a conexao com o banco.

**Dica**: Use `services.postgres` com `image`, `env`, `ports`, e `options` para health check.

### Exercicio 6: Secrets e Environment Variables

Crie um workflow que:
1. Use um secret do repositorio
2. Use uma variavel do repositorio (vars)
3. Defina variaveis no nivel workflow, job, e step
4. Demonstre a hierarquia de precedencia

### Exercicio 7: Concurrency

Configure um workflow que:
1. Use um concurrency group baseado no workflow e ref
2. Cancele execucoes anteriores quando uma nova e iniciada
3. So rode em pull requests

### Exercicio 8: Security

Crie um workflow de seguranca que:
1. Execute CodeQL analysis
2. Execute Trivy scanner
3. Verifique dependencias com dependency-review
4. Use permissoes minimas (least privilege)

### Exercicio 9: Custo Estimation

Estime o custo mensal para:
- 200 builds por dia
- 7 minutos de duracao media
- 80% ubuntu-latest, 20% macos-latest
- Plano Team com 5 usuarios
- Inclua o custo do plano

### Exercicio 10: Comparacao

Escreva um comparativo entre GitHub Actions e outra ferramenta de CI/CD da sua escolha. Considere: setup, curva de aprendizado, features, custo, e comunidade.

---

## 1.11 Referencias

### Documentacao Oficial

1. GitHub Actions Documentation: https://docs.github.com/en/actions
2. GitHub Actions Quickstart: https://docs.github.com/en/actions/quickstart
3. GitHub Actions Marketplace: https://github.com/marketplace?type=actions
4. GitHub Actions Billing: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions
5. GitHub Actions Security: https://docs.github.com/en/actions/security-for-github-actions
6. GitHub Actions Variables: https://docs.github.com/en/actions/learn-github-actions/variables
7. GitHub Actions Secrets: https://docs.github.com/en/actions/security-for-github-actions/using-secrets-in-github-actions
8. GitHub Actions Environments: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment

### Recursos Adicionais

9. GitHub Actions Cheat Sheet: https://docs.github.com/en/actions/learn-github-actions/cheat-sheet
10. GitHub Actions Workshop: https://github.com/githubtraining/github-actions-for-CI-CD
11. Awesome GitHub Actions: https://github.com/sdras/awesome-actions
12. GitHub Actions Security Best Practices: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

### Comparacoes

13. GitHub Actions vs GitLab CI: https://github.blog/2022-06-06-introduction-to-github-actions-vs-gitlab-ci/
14. GitHub Actions vs Jenkins: https://github.blog/2019-10-22-github-actions-vs-jenkins/
15. State of CI/CD 2024: https://github.blog/2024-01-state-of-the-octoverse-cicd/

### Comunidade

16. GitHub Actions Community: https://githubcommunity.com/t5/GitHub-Actions/bd-p/actions
17. GitHub Actions Discord: https://discord.gg/github
18. GitHub Actions Reddit: https://reddit.com/r/githubactions

---

## 1.12 Patronos e Estrutura de Diretorios Recomendada

Quando seu repositorio cresce e voce comeca a ter multiplos workflows, e importante estabelecer uma estrutura clara e consistente. A seguir, apresentamos as recomendacoes de patronos e estrutura de diretorios para projetos de qualquer porte.

### Estrutura de Diretorios Padrao

```
.github/
  workflows/
    ci.yml                  # Pipeline principal de CI (lint, test, build)
    cd-staging.yml          # Deploy automatico para staging
    cd-production.yml       # Deploy manual para production
    release.yml             # Criacao de release e changelog
    security.yml            # Escaneamento de seguranca (SAST, SCA)
    cron.yml                # Tarefas agendadas (cleanup, reports)
    reusable/
      lint.yml              # Workflow reutilizavel de lint
      test.yml              # Workflow reutilizavel de test
      deploy.yml            # Workflow reutilizavel de deploy
  actions/
    setup-project/
      action.yml            # Composite action para setup
    notify/
      action.yml            # Composite action para notificacoes
  dependabot.yml            # Configuracao do Dependabot
  CODEOWNERS                # Owners por diretorio
```

### Patronos de Nomenclatura

| Elemento | Formato | Exemplo |
|----------|---------|---------|
| Workflow files | `kebab-case.yml` | `ci.yml`, `deploy-staging.yml` |
| Workflow names | Title Case | `CI Pipeline`, `Deploy to Production` |
| Job names | `kebab-case` | `lint`, `unit-test`, `build`, `deploy-staging` |
| Step names | Title Case | `Checkout code`, `Install dependencies`, `Run tests` |
| Secret names | `UPPER_SNAKE_CASE` | `AWS_ACCESS_KEY_ID`, `DATABASE_URL` |
| Variable names | `UPPER_SNAKE_CASE` | `NODE_VERSION`, `DEPLOY_ENV` |
| Matrix keys | `kebab-case` | `os`, `node-version`, `java-version` |
| Artifact names | `kebab-case-{sha}` | `build-abc123def`, `coverage-main` |

### Patronos de Triggers

Use estes triggers de forma consistente em todos os seus workflows:

```yaml
# CI - roda em todo push e PR
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

# Deploy staging - roda automaticamente na main
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'Dockerfile'
      - 'package.json'

# Deploy production - roda apenas manualmente ou via release
on:
  workflow_dispatch:
  release:
    types: [published]

# Seguranca - roda em push, PR, e agendado
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'
```

### Patronos de Permissoes

```yaml
# Padrao: minimal permissions no workflow level
permissions:
  contents: read

# Override por job conforme necessidade
jobs:
  test:
    permissions:
      contents: read
    # herda contents: read do workflow

  deploy:
    permissions:
      contents: read
      id-token: write
      deployments: write
    # adiciona permissoes especificas do deploy

  release:
    permissions:
      contents: write
      packages: write
    # precisa escrever contents e packages
```

### Patronos de Seguranca

```yaml
# 1. Sempre pin actions por SHA, nao por tag
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1

# 2. Nunca usar pull_request_target com checkout do PR
# ERRADO:
on:
  pull_request_target:
steps:
  - uses: actions/checkout@v4  # Checkout do branch base, perigoso

# CORRETO:
on:
  pull_request:
steps:
  - uses: actions/checkout@v4  # Checkout do branch do PR

# 3. Usar environment para proteger deploys
jobs:
  deploy:
    environment:
      name: production
      url: https://myapp.com
    # Requer aprovacao manual se configurado

# 4. Usar GITHUB_TOKEN com permissoes minimas
permissions:
  contents: read
  # Nao adicionar write se nao necessario
```

### Patronos de Cache

```yaml
# Padrao: cache por runner OS + hash dos arquivos de lock
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-npm-

# Python: cache por versao + requirements
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

# Java: cache por versao + pom.xml
- uses: actions/cache@v4
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      ${{ runner.os }}-maven-

# Go: cache por versao + go.sum
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/go-build
      ~/go/pkg/mod
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-
```

### Patronos de Outputs

```yaml
# Use outputs para compartilhar dados entre jobs
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
      image: ${{ steps.meta.outputs.tags }}
    steps:
      - id: version
        run: echo "value=$(cat VERSION)" >> $GITHUB_OUTPUT
      - id: meta
        run: echo "tags=ghcr.io/app:$(cat VERSION)" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying version ${{ needs.build.outputs.version }}"
      - run: echo "Image ${{ needs.build.outputs.image }}"
```

---

## 1.13 Glossario

| Termo | Definicao |
|-------|-----------|
| **Action** | Componente reutilizavel que encapsula uma ou mais etapas de um workflow |
| **Artifact** | Arquivo ou conjunto de arquivos produzidos durante a execucao de um workflow |
| **Concurrency Group** | Grupo que controla execucoes simultaneas de workflows |
| **Context** | Objeto que fornece acesso a informacoes do workflow (github, env, secrets, etc.) |
| **Event** | Gatilho que dispara a execucao de um workflow (push, PR, schedule, etc.) |
| **Expression** | AvaliacaoJavaScript-like em contexts e condicoes |
| **Runner** | Maquina que executa um job (GitHub-hosted ou self-hosted) |
| **Secret** | Variavel criptografada usada para armazenar dados sensiveis |
| **Step** | Comando individual dentro de um job (pode ser uma action ou run) |
| **Trigger** | Evento que inicia a execucao de um workflow |
| **Variable** | Variavel de ambiente disponivel em workflows |
| **Workflow** | Arquivo YAML que define um pipeline de CI/CD |
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Syntax Workflows](02-syntax-workflows.md)*
