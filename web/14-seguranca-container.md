# Capitulo 14 — Seguranca de Containers e Deployment

> *"O container nao e um sandbox. E um processo com permissao de administrador esperando ser explorado."*

---

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Implementar Docker security best practices: image scanning, non-root users, read-only filesystems
2. Configurar Kubernetes RBAC, Pod Security Standards e Network Policies
3. Avaliar e aplicar container runtimes seguros: gVisor, Kata Containers, Firecracker
4. Construir image supply chain segura com Cosign, Notary e Sigstore
5. Gerenciar secrets em containers com Vault e Sealed Secrets
6. Projetar pipelines CI/CD seguras para aplica web
7. Auditar Infrastructure as Code com Terraform e Pulumi
8. Aplicar o OWASP Docker Security Top 10 em ambientes reais
9. Configurar vulnerability scanning com Trivy, Grype e Snyk
10. Prevenir supply chain attacks em deployment de aplica web
11. Criar Dockerfiles e docker-compose seguros
12. Configurar deployments Kubernetes com security best practices
13. Executar exercicios praticos de container security

---

## Visao Geral: O Problema de Seguranca em Containers

### Containers Nao Sao VMs

Uma das confusoes mais perigosas na industria e a equivalencia entre containers e maquinas virtuais. Containers compartilham o kernel do host. VMs isolam o hardware. Essa diferenca e fundamental para entender porque containers introduzem vetores de ataque unicos.

Um container roda como um processo privilegiado no host. Se um atacante escapa do namespace do container, ele ganha acesso direto ao kernel do host. Isso e chamado de **container escape** e e uma das ameacas mais criticas em ambientes containerizados.

```
Arquitetura de um container:

┌─────────────────────────────────────────────┐
│                   Host                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Container │  │Container │  │Container │  │
│  │  App A   │  │  App B   │  │  App C   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │        │
│  ┌────┴──────────────┴──────────────┴────┐  │
│  │          Container Runtime            │  │
│  │      (Docker, containerd, CRI-O)      │  │
│  └───────────────┬───────────────────────┘  │
│                  │                          │
│  ┌───────────────┴───────────────────────┐  │
│  │         Linux Kernel (shared)         │  │
│  │    Namespaces, cgroups, seccomp       │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### O CWE-400 e CWE-502

O CWE-400 (Improper Control of Generation of Code) e o CWE-502 (Deserialization of Untrusted Data) sao frequentemente encontrados em ambientes containerizados. Containers que executam codigo gerado dinamicamente ou que deserializam dados de fontes nao confiaveis representam riscos elevados de remote code execution (RCE).

### Historico de Vulnerabilidades em Containers

A historia de container security esta marcada por incidentes que moldaram as praticas atuais:

**CVE-2014-3153 (Towelroot)**: Vulnerabilidade no kernel Linux que permitia privilege escalation via futex. Containers sem namespaces adequados eram especialmente vulneraveis.

**CVE-2019-5736 (runc escape)**: Falha no runc que permitia arbitrary code execution no host a partir de um container. O atacante poderia sobrescrever o binario runc no host com um payload malicioso. Essa CVE afetou todas as distribuicoes Docker, Kubernetes, e CRI-O.

**CVE-2020-15257 (containerd)**: Vulnerabilidade no containerd que permitia container escape via network namespace. Containers que usavam --net=host estavam diretamente expostos.

**CVE-2022-0185 (filesystem escape)**: Falha no kernel que permitia escape de containers usando um bug no filesystem handler. Containers com privilégios reduzidos ainda eram vulneraveis.

**CVE-2022-0811 (cr8escape)**: Vulnerabilidade no CRI-O que permitia arbitrary code execution no host. Essa falha permaneceu nao corrigida por meses e afetou ambientes Kubernetes em producao.

### O CWE-250: Execution with Unnecessary Privileges

Muitos containers rodam com privilégios elevados desnecessariamente. O CWE-250 documenta essa pratica perigosa. Um container que roda como root dentro do container, mesmo sem --privileged, ainda tem acesso a mais recursos do que necessario.

```
Exemplo de container com privilégios excessivos (VULNERAVEL):

$ docker run --rm -it --privileged ubuntu:22.04 bash

Dentro do container:
$ cat /proc/1/status | grep Cap
CapPrm: 0000003fffffffff  (TODOS os capabilities)
CapEff: 0000003fffffffff

$ mount /dev/sda1 /mnt
$ chroot /mnt
# ls /etc/shadow
root:$6$...:18000:0:99999:7:::

Consequencia: O atacante tem acesso total ao filesystem do host.
```

---

## 1. Docker Security: Image Scanning, Non-Root Users e Read-Only Filesystems

### Image Scanning: A Primeira Linha de Defesa

O image scanning e o processo de analisar imagens Docker em busca de vulnerabilidades, configuracoes inseguras e dependencias obsoletas. Todo container que roda em producao deve ter sua imagem escaneada antes do deployment.

#### Tipos de Vulnerabilidades em Imagens

**Vulnerabilidades de Dependencia**: Bibliotecas e pacotes com CVEs conhecidos. O Ubuntu 22.04 base image contem centenas de pacotes, muitos dos quais possuem vulnerabilidades publicadas.

**Vulnerabilidades de Configuracao**: Imagens com configuracoes perigosas, como:
- Exposed ports desnecessarias
- Variaveis de ambiente com secrets hardcoded
- Binarios com SUID bits setados
- Arquivos de configuracao com permissoes inseguras

**Vulnerabilidades de Build**: Problemas introduzidos durante o build do Dockerfile:
- Copia de .git directory para a imagem
- Inclusao de arquivos de ambiente (.env)
- Use de --privileged durante build
- Multi-stage builds mal configuradas

**Malware e Backdoors**: Imagens de registry publico podem conter malware ou backdoors. Em 2018, pesquisadores da Aqua Security descobriram que imagens populares no Docker Hub continham cryptominers ocultos.

#### Ferramentas de Image Scanning

**Trivy** (Aqua Security):
Trivy e o scanner de vulnerabilidades mais popular para containers. Ele analisa imagens Docker, filesystems, e repositorios Git. O Trivy suporta múltiplos formatos de output e pode ser integrado facilmente em pipelines CI/CD.

```
Uso basico do Trivy para escanear uma imagem:

$ trivy image nginx:latest

Exemplo de output:
┌──────────────────────────────────────────────────┐
│ nginx:latest (debian 11.6)                       │
├──────────────────────────────────────────────────┤
│ Total: 156 (UNKNOWN: 0, LOW: 89, MEDIUM: 52,   │
│         HIGH: 14, CRITICAL: 1)                   │
├──────────────────────────────────────────────────┤
│ CRITICAL: CVE-2023-XXXXXX                        │
│   Package: openssl                               │
│   Installed: 1.1.1k-1+deb11u2                    │
│   Fixed: 1.1.1k-1+deb11u3                        │
│   Title: Buffer overflow in OpenSSL              │
│   Severity: CRITICAL                              │
│   CVSS: 9.8                                       │
│   Reference: https://nvd.nist.gov/...             │
└──────────────────────────────────────────────────┘
```

```
Escaneamento com nivel de severidade minimo:

$ trivy image --severity HIGH,CRITICAL nginx:latest

Escaneamento com formato JSON para integracao:

$ trivy image -f json -o results.json nginx:latest

Escaneamento em pipeline CI/CD com falha automatica:

$ trivy image --exit-code 1 --severity HIGH,CRITICAL nginx:latest
# Retorna exit code 1 se encontrar HIGH ou CRITICAL
```

**Grype** (Anchore):
Grype e uma ferramenta de escaneamento de vulnerabilidades focada em imagens container. Ele suporta multiple image sources e pode ser usado com o Syft para gerar SBOM (Software Bill of Materials).

```
Uso do Grype para escaneamento:

$ grype nginx:latest

Exemplo de output:
┌─────────────┬──────────────┬───────────┬───────────────────────┐
│  DATABASE   │   PACKAGE    │ INSTALLED │       VULNERABILITY   │
├─────────────┼──────────────┼───────────┼───────────────────────┤
│  Debian 11  │ openssl      │ 1.1.1k-1  │ CVE-2023-XXXXX (High) │
│  Debian 11  │ libcurl4     │ 7.74.0-1  │ CVE-2023-YYYYY (Med)  │
└─────────────┴──────────────┴───────────┴───────────────────────┘

Escaneamento com SBOM de entrada:

$ syft nginx:latest -o spdx-json > sbom.json
$ grype sbom:./sbom.json

Escaneamento de diretorio local:

$ grype dir:./my-app/
```

**Snyk Container**:
Snyk oferece escaneamento de containers com remediation advice e integracao com IDEs. A versao gratuita suporta escaneamento basico, enquanto a versao paga oferece profundidade de analise superior.

```
Uso do Snyk para containers:

$ snyk container test nginx:latest

Exemplo de output:
✗ Critical severity vulnerability found in openssl/libssl1.1
  Description: Buffer overflow in OpenSSL
  Info: https://snyk.io/vuln/SNYK-DEBIAN11-OPENSSL-XXXXXXX
  From: openssl/libssl1.1@1.1.1k-1+deb11u2
  Fix: Upgrade openssl to 1.1.1k-1+deb11u3 or higher

✗ Medium severity vulnerability found in curl/libcurl4
  Description: Use-after-free in libcurl
  Info: https://snyk.io/vuln/SNYK-DEBIAN11-CURL-YYYYYYY
  From: curl/libcurl4@7.74.0-1+deb11u1
  Fix: Upgrade curl to 7.74.0-1+deb11u2 or higher

Tested 186 dependencies for known issues, found 2 issues.
```

#### Configuracao de Image Scanning em CI/CD

```
GitHub Actions com Trivy:

name: Container Security Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif
```

### Non-Root Users: Eliminando Privilegios Excessivos

O principio de menor privilegio e fundamental para container security. Containers que rodam como root representam um risco significativo: se o atacante escapar do container, ele ganha privilegios de root no host.

#### O Problema do Root no Container

```
Demonstracao do risco de rodar como root:

$ docker run --rm -it alpine sh -c "whoami"
root

$ docker run --rm -it alpine sh -c "cat /proc/1/status | grep Cap"
CapPrm: 0000003fffffffff
CapEff: 0000003fffffffff

$ docker run --rm -it --cap-add=SYS_ADMIN alpine sh -c "mount -t tmpfs none /mnt && ls /mnt"
# Container com SYS_ADMIN pode montar filesystems

Impacto: Um container rodando como root pode:
- Montar filesystems do host
- Acessar dispositivos de bloco
- Modificar configuracoes de rede
- Executar syscalls perigosas
```

#### Implementacao de Non-Root Users

```
Dockerfile correto com non-root user:

FROM node:18-alpine

# Criar usuario nao-privilegiado
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Definir diretorio de trabalho
WORKDIR /app

# Copiar dependencias primeiro (cache de layers)
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copiar codigo da aplicacao
COPY --chown=appuser:appgroup . .

# Definir usuario para todos os comandos seguintes
USER appuser

# Container roda como usuario nao-privilegiado
CMD ["node", "server.js"]
```

```
Dockerfile com multi-stage build e non-root:

FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine

# Criar usuario nao-privilegiado
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copiar apenas artifacts de build necessarios
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

# Mover diretórios para locais com permissoes adequadas
RUN chown -R appuser:appgroup /app && \
    chmod -R 550 /app && \
    chmod 750 /app/dist

USER appuser

EXPOSE 3000
CMD ["node", "dist/server.js"]
```

```
Verificacao de que o container nao roda como root:

$ docker run --rm myapp:latest whoami
appuser

$ docker exec $(docker create myapp:latest) cat /proc/1/status | grep Cap
CapPrm: 0000000000000000
CapEff: 0000000000000000

# Resultado: Container roda sem privilegios de root
# Root dentro do container nao tem capabilities elevadas
```

#### Configuracao de Security no Docker Compose

```yaml
# docker-compose.yml seguro

version: '3.8'

services:
  webapp:
    build: .
    image: myapp:latest
    # Forcar usuario nao-privilegiado
    user: "1001:1001"
    # Remover todas as capabilities
    cap_drop:
      - ALL
    # Adicionar apenas capabilities necessarias
    cap_add:
      - NET_BIND_SERVICE
    # Sinal de终止
    stop_grace_period: 30s
    # Read-only filesystem
    read_only: true
    # Mounts temporarios
    tmpfs:
      - /tmp:size=100M,noexec,nosuid
      - /app/tmp:size=50M
    # Variaveis de ambiente sem secrets
    environment:
      - NODE_ENV=production
      - PORT=3000
    # Rede dedicada
    networks:
      - app-network
    # Health check
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # Limites de recursos
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    # Logging configurado
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        tag: "{{.Name}}/{{.ID}}"

networks:
  app-network:
    driver: bridge
    # Configuracao de rede segura
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
```

### Read-Only Filesystems: Prevenindo Modificacoes Maliciosas

Um filesystem read-only impede que processos dentro do container modifiquem arquivos criticos. Isso e uma defesa poderosa contra ataques que tentam modificar configuracoes ou instalar backdoors.

#### Configuracao de Read-Only Filesystem

```
Dockerfile com filesystem read-only:

FROM node:18-alpine

# Criar diretorios que precisam de escrita
RUN mkdir -p /app/tmp /app/logs && \
    chown -R appuser:appgroup /app/tmp /app/logs

# Configurar permissoes para read-only
COPY --chown=appuser:appgroup . /app/

WORKDIR /app

USER appuser

# O filesystem base sera read-only
# Diretorios temporarios serao montados como tmpfs
CMD ["node", "server.js"]
```

```yaml
# docker-compose.yml com filesystem read-only

version: '3.8'

services:
  webapp:
    build: .
    read_only: true
    tmpfs:
      - /tmp:size=100M,noexec,nosuid,nodev
      - /app/tmp:size=50M,noexec,nosuid
      - /var/cache:size=50M,noexec,nosuid
    volumes:
      # Mounts somente-leitura para dados persistentes
      - app-data:/app/data:ro
      # Mounts para configuracao
      - ./config:/app/config:ro

volumes:
  app-data:
    driver: local
```

```
Teste de filesystem read-only:

$ docker run --rm -it --read-only alpine sh

# Dentro do container:
$ touch /test.txt
touch: /test.txt: Read-only file system

# Diretorios tmpfs sao escritaveis:
$ echo "test" > /tmp/test.txt
$ cat /tmp/test.txt
test

# Vantagens:
# - Previne modificacao de binarios criticos
# - Impede instalacao de backdoors
# - Forca uso de diretorios temporarios controlados
```

### Security Profiles: Seccomp e AppArmor

#### Seccomp

Seccomp (Secure Computing Mode) limita as system calls que um container pode executar. O Docker fornece um perfil padrao que bloqueia cerca de 44 das 300+ system calls disponiveis no Linux.

```
Perfil seccomp customizado para Node.js:

{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_X86",
    "SCMP_ARCH_AARCH64"
  ],
  "syscalls": [
    {
      "names": [
        "accept", "access", "arch_prctl", "bind",
        "brk", "clone", "close", "connect", "dup",
        "dup2", "epoll_create", "epoll_ctl", "epoll_wait",
        "execve", "exit", "exit_group", "fcntl",
        "fstat", "futex", "getdents64", "getpid",
        "getsockname", "gettid", "ioctl", "listen",
        "lseek", "mmap", "mprotect", "munmap",
        "nanosleep", "newfstatat", "openat", "pipe",
        "poll", "prlimit64", "read", "recvfrom",
        "rt_sigaction", "rt_sigprocmask", "sendto",
        "set_robust_list", "set_tid_address", "setsockopt",
        "socket", "stat", "statfs", "tgkill",
        "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}

Uso:
$ docker run --security-opt seccomp=profile.json myapp:latest
```

#### AppArmor

AppArmor e um modulo de seguranca do Linux que restringe os capabilities de um programa individual. O Docker carrega um perfil AppArmor padrao chamado docker-default.

```
Perfil AppArmor customizado para Node.js:

#include <tunables/global>

profile docker-nodejs flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  # Negar acesso a diretorios sensiveis
  deny /proc/** w,
  deny /sys/** w,
  deny /dev/** w,

  # Permitir leitura de diretorios da aplicacao
  /app/** r,
  /app/node_modules/** r,

  # Permitir escrita em diretorios temporarios
  /tmp/** rw,
  /app/tmp/** rw,
  /app/logs/** rw,

  # Negar acesso a binarios do sistema
  deny /bin/** wx,
  deny /sbin/** wx,
  deny /usr/bin/** wx,
  deny /usr/sbin/** wx,

  # Negar criacao de novos arquivos executaveis
  deny /** m,
}
```

---

## 2. Kubernetes Security: RBAC, Pod Security Standards e Network Policies

### Role-Based Access Control (RBAC)

RBAC e o mecanismo de controle de acesso do Kubernetes. Ele define quem pode acessar quais recursos e quais acoes podem ser executadas. Uma configuracao RBAC inadequada e uma das causas mais comuns de breaches em clusters Kubernetes.

#### Componentes do RBAC

**Role**: Define permissoes em um namespace especifico. E um escopo limitado e deve ser a opcao padrao sempre que possivel.

**ClusterRole**: Define permissoes em todo o cluster. Deve ser usado apenas quando necessario.

**RoleBinding**: Associa um Role a usuarios, grupos ou service accounts.

**ClusterRoleBinding**: Associa um ClusterRole a usuarios, grupos ou service accounts.

```
Role basico para acesso a pods:

apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: production
subjects:
- kind: User
  name: jane.doe@company.com
  apiGroup: rbac.authorization.k8s.io
- kind: ServiceAccount
  name: monitoring-sa
  namespace: production
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

```
ClusterRole para monitoring (perigoso se usado incorretamente):

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-monitor
rules:
- apiGroups: [""]
  resources: ["nodes", "services", "endpoints"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["metrics.k8s.io"]
  resources: ["nodes", "pods"]
  verbs: ["get", "list"]

PERIGO: ClusterRole da acesso a TODOS os namespaces
NUNCA use ClusterRole para dados sensiveis

---
ClusterRole para admin - USAR COM EXTREMO CUIDADO:

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-admin
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
- nonResourceURLs: ["*"]
  verbs: ["*"]

PERIGO EXTREMO: Isso da acesso total ao cluster
NUNCA associe a usuarios finais
```

#### RBAC Best Practices

```
Principio do menor privilegio em RBAC:

1. NUNCA usar cluster-admin para aplicacoes
2. Criar Roles por namespace para cada servico
3. Usar Subjects com escopo limitado
4. Revisar permissoes regularmente
5. Auditar acessos com audit logs
6. Usar ServiceAccounts dedicadas por servico

Exemplo de ServiceAccount isolado:

apiVersion: v1
kind: ServiceAccount
metadata:
  name: webapp-sa
  namespace: production
automountServiceAccountToken: false

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: webapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["webapp-config"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["webapp-secrets"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: webapp-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: webapp-sa
  namespace: production
roleRef:
  kind: Role
  name: webapp-role
  apiGroup: rbac.authorization.k8s.io
```

### Pod Security Standards

Pod Security Standards (PSS) substituiu Pod Security Policies (PSP) no Kubernetes 1.25. PSS define tres niveis de restricao: Privileged, Baseline e Restricted.

#### Nivel Privileged

Sem restricoes. Equivalente ao antigo PSP privileged. Deve ser usado apenas para workloads do sistema que precisam de acesso total ao host.

#### Nivel Baseline

Bloqueia configuracoes claramente inseguras, mas permite flexibilidade para a maioria das aplica. Impede:
- Containers privilegiados
- Host networking
- Host PID namespace
- Host IPC namespace
- Host file system
- Privilege escalation

#### Nivel Restricted

Implementa restricoes rigorosas baseadas em hardening. Ideal para aplica criticas. Exige:
- Non-root user
- Read-only root filesystem
- Drop all capabilities
- Seccomp profile
- No privilege escalation

```
Namespace com Pod Security Standards:

apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

---
Pod compativel com nivel restricted:

apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: production
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
          - ALL
    ports:
    - containerPort: 3000
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: app-data
      mountPath: /app/data
    resources:
      limits:
        cpu: "1"
        memory: 256Mi
      requests:
        cpu: "0.5"
        memory: 128Mi
    livenessProbe:
      httpGet:
        path: /health
        port: 3000
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /ready
        port: 3000
      initialDelaySeconds: 5
      periodSeconds: 5
  volumes:
  - name: tmp
    emptyDir:
      sizeLimit: 100Mi
  - name: app-data
    emptyDir: {}
```

### Network Policies

Network Policies definem regras de trafego entre pods. Sem Network Policies, todos os pods do cluster podem se comunicar livremente. Isso e uma violacao do principio de menor privilegio.

```
Network Policy basica - negar todo trafego exceto o necessario:

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
Network Policy para o webapp - permitir apenas trafego necessario:

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: webapp-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: webapp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  # DNS
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53

---
Network Policy para o banco de dados - negar todo ingress externo:

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: webapp
    ports:
    - protocol: TCP
      port: 5432
  egress: []
```

---

## 3. Container Runtime Security: gVisor, Kata Containers

### O Problema com Runtimes Tradicionais

O container runtime padrao (runc) compartilha o kernel do host com todos os containers. Isso significa que uma vulnerabilidade no kernel pode ser explorada para escapar de qualquer container. Runtimes de seguranca como gVisor e Kata Containers adicionam camadas adicionais de isolamento.

### gVisor

gVisor e um container runtime desenvolvido pelo Google que implementa um sistema operacional em userspace. Ele intercepta system calls do container e as processa em um kernel sandboxed.

```
Arquitetura do gVisor:

┌─────────────────────────────────────────┐
│              Container                   │
│  ┌──────────────────────────────────┐  │
│  │           Application            │  │
│  └──────────────┬───────────────────┘  │
│                 │ syscalls              │
│  ┌──────────────┴───────────────────┐  │
│  │         Sentry (kernel)          │  │
│  │    Intercepta e processa         │  │
│  │    system calls em userspace     │  │
│  └──────────────┬───────────────────┘  │
│                 │                       │
│  ┌──────────────┴───────────────────┐  │
│  │         Gofer (filesystem)       │  │
│  │    Acesso limitado ao host       │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
                 │
┌─────────────────────────────────────────┐
│              Host Kernel                │
│    (reduzido superficie de ataque)      │
└─────────────────────────────────────────┘
```

```
Uso do gVisor com Docker:

# Instalacao do gVisor (runsc)
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list
sudo apt-get update && sudo apt-get install -y runsc

# Configuracao do Docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "runtimes": {
    "runsc": {
      "path": "/usr/bin/runsc"
    }
  }
}
EOF

sudo systemctl restart docker

# Executar container com gVisor
docker run --runtime=runsc -it alpine sh

# Verificacao
docker run --runtime=runsc -it alpine sh -c "uname -r"
# Output: 5.15.0 (gVisor kernel, nao o kernel do host)
```

```
Kubernetes com gVisor:

apiVersion: v1
kind: Pod
metadata:
  name: gvisor-pod
  annotations:
    io.gvisor.runtime.runsc: runsc
spec:
  runtimeClassName: runsc
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
          - ALL
```

### Kata Containers

Kata Containers usa Lightweight Virtual Machines (VMs) para isolar containers. Cada container roda dentro da sua propria VM, compartilhando apenas o hypervisor com o host.

```
Arquitetura do Kata Containers:

┌──────────────────────────────────────────────┐
│                   Host                        │
│  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Kata VM 1     │  │   Kata VM 2     │  │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │
│  │  │ Container │  │  │  │ Container │  │  │
│  │  │    App    │  │  │  │    App    │  │  │
│  │  └───────────┘  │  │  └───────────┘  │  │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │
│  │  │  Guest    │  │  │  │  Guest    │  │  │
│  │  │  Kernel   │  │  │  │  Kernel   │  │  │
│  │  └───────────┘  │  │  └───────────┘  │  │
│  └────────┬────────┘  └────────┬────────┘  │
│           │                    │             │
│  ┌────────┴────────────────────┴────────┐  │
│  │         Hypervisor (QEMU/Firecracker)│  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │              Host Kernel              │  │
│  └──────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

```
Kata Containers com Kubernetes:

apiVersion: v1
kind: Pod
metadata:
  name: kata-pod
  annotations:
    io.kata-containers.runtime_handler: kata-qemu
spec:
  runtimeClassName: kata-qemu
  containers:
  - name: app
    image: myapp:latest
    resources:
      limits:
        memory: "512Mi"
        cpu: "1"
```

### Comparacao de Container Runtimes

| Feature | runc (padrao) | gVisor | Kata Containers |
|---------|---------------|--------|-----------------|
| Isolamento | Namespace/cgroup | Userspace kernel | VM-based |
| Performance overhead | Baixo | Medio | Alto |
| Compatibilidade | Total | Limitada | Quase total |
| Seguranca | Basica | Intermediaria | Avancada |
| Memoria por container | ~10MB | ~50MB | ~130MB |
| Startup time | ~100ms | ~300ms | ~1s |
| Uso recomendado | Dev/test | Workloads web | Workloads criticos |

---

## 4. Image Supply Chain: Cosign, Notary e Sigstore

### O Problema da Supply Chain

Supply chain attacks em containers envolvem comprometer a imagem antes ou durante o processo de build. O atacante pode:
- Injetar malware em uma dependencia
- Comprometer o registry publico
- Sobrescrever uma tag existente
- Manipular o build pipeline

Em 2021, o ataque ao codecov bash uploader expôs credenciais de CI/CD de milhares de empresas. Em 2022, o ataque ao npm package colors.js causou downtime em milhares de aplica.

### Cosign (Sigstore)

Cosign e a ferramenta principal do projeto Sigstore para assinar e verificar imagens container. Ele fornece signing, verification e keyless signing.

```
Instalacao do Cosign:

# Via binario
wget https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# Via go
go install github.com/sigstore/cosign/v2/cmd/cosign@latest
```

```
Geracao de chave para assinatura:

# Gerar chave keyless (recomendado)
$ cosign generate-key-pair
Enter password for private key:
Enter again:
Private key written to cosign.key
Public key written to cosign.pub

# Converter para formato KMS
$ cosign generate-key-pair --kms hashivault://cosign-key

# Usar chave existente
$ export COSIGN_KEY="hashivault://cosign-key"
```

```
Assinatura de imagem com Cosign:

# Assinar imagem com chave local
$ cosign sign --key cosign.key myregistry.com/myapp:v1.0

# Assinatura keyless (usando OIDC identity)
$ cosign sign myregistry.com/myapp:v1.0

# Assinar com attestations
$ cosign attest --key cosign.key \
  --predicate cicd-data.json \
  --type cyclonedx \
  myregistry.com/myapp:v1.0

# Assinatura com annotations
$ cosign sign --key cosign.key \
  --annotations "com.myorg.build=https://ci.example.com/build/123" \
  --annotations "com.myorg.scan=https://trivy.example.com/scan/456" \
  myregistry.com/myapp:v1.0
```

```
Verificacao de assinatura:

# Verificar assinatura com chave
$ cosign verify --key cosign.pub \
  myregistry.com/myapp:v1.0

# Verificar com chave publica
$ cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  myregistry.com/myapp:v1.0

# Verificar attestations
$ cosign verify-attestation \
  --key cosign.pub \
  --type cyclonedx \
  myregistry.com/myapp:v1.0

# Verificacao em Kubernetes com Kyverno
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: Enforce
  background: false
  rules:
  - name: check-image-signature
    match:
      any:
      - resources:
          kinds:
          - Pod
    verifyImages:
    - imageReferences:
      - "myregistry.com/*"
      require:
        attestations:
        - type: https://cyclonedx.org/cyclonedx
          conditions:
          - all:
            - key: "{{ scanner.result }}"
              operator: Equals
              value: "passed"
```

### Notary

Notary e um projeto CNCF para assinatura de containers usando Content Trust. O Docker Content Trust (DCT) e baseado no Notary.

```
Configuracao do Docker Content Trust:

$ export DOCKER_CONTENT_TRUST=1

# Push com assinatura automatica
$ docker push myregistry.com/myapp:v1.0
# O Docker ira gerar chaves e assinar automaticamente

# Verificacao automatica
$ docker pull myregistry.com/myapp:v1.0
# O Docker verifica a assinatura antes de baixar

# Verificacao manual
$ docker trust inspect --pretty myregistry.com/myapp:v1.0

Exemplo de output:
Signers for myregistry.com/myapp:v1.0:
Name:          Repository Admin
  Key ID:      ABCDEF1234567890
  Role:        admin
  Fish-eye:    sha256:...

Administrative keys for myregistry.com/myapp:v1.0:
Repository Key:  ABCDEF1234567890
Root Key:        1234ABCD5678EFGH
```

### Sigstore Keyless Signing

Keyless signing usa identidade OIDC (OpenID Connect) em vez de chaves estaticas. Isso permite rastreabilidade: cada assinatura e vinculada a uma identidade verificavel (GitHub Actions, GitLab CI, etc.).

```
Keyless signing com Sigstore:

# Assinatura keyless usando OIDC
$ cosign sign \
  --oidc-issuer=https://token.actions.githubusercontent.com \
  --identity-token=$ACTIONS_ID_TOKEN \
  myregistry.com/myapp:v1.0

# Verificacao keyless
$ cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  myregistry.com/myapp:v1.0

# Integracao com GitHub Actions
name: Build and Sign
on:
  push:
    branches: [main]
jobs:
  build-sign:
    permissions:
      id-token: write
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Install Cosign
        uses: sigstore/cosign-installer@main
      - name: Build and Push
        run: |
          docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}:${{ github.sha }}
      - name: Sign Image
        env:
          COSIGN_EXPERIMENTAL: "true"
        run: |
          cosign sign ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 5. Secrets Management in Containers: Vault e Sealed Secrets

### O Problema dos Secrets em Containers

Secrets hardcoded em imagens Docker ou passados via variaveis de ambiente sao um dos vetores de ataque mais comuns. O CWE-798 (Use of Hard-coded Credentials) e o CWE-259 (Use of Hard-coded Password) documentam essas vulnerabilidades.

```
Exemplos de como secrets SAO expostos:

1. Dockerfile com secrets hardcoded:
FROM node:18
ENV DATABASE_URL=postgres://admin:password123@db:5432/prod
ENV AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
COPY . /app

$ docker history myapp:v1
# Mostra TODAS as variaveis de ambiente, incluindo secrets

2. Variaveis de ambiente via docker run:
$ docker run -e DATABASE_URL=postgres://admin:password123@db:5432/prod myapp:v1

$ docker inspect <container>
# Mostra todas as variaveis de ambiente

3. Build arguments expostos:
$ docker build --build-arg DB_PASSWORD=secret123 .
$ docker history myapp:v1
# Mostra o build argument
```

### HashiCorp Vault

Vault e uma solucao de gerenciamento de secrets que fornece secrets como um servico. Ele suporta multiple secrets engines e pode ser integrado com Kubernetes.

```
Configuracao do Vault com Kubernetes:

# Habilitar secrets engine para Kubernetes
$ vault secrets enable -path=secret kv-v2

# Configurar autenticacao Kubernetes
$ vault auth enable kubernetes
$ vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc"

# Criar policy para a aplicacao
$ vault policy write webapp-policy - <<EOF
path "secret/data/webapp/*" {
  capabilities = ["read", "list"]
}
path "secret/data/webapp/database" {
  capabilities = ["read"]
}
EOF

# Criar role para o service account
$ vault write auth/kubernetes/role/webapp \
    bound_service_account_names=webapp-sa \
    bound_service_account_namespaces=production \
    policies=webapp-policy \
    ttl=1h

# Armazenar secrets
$ vault kv put secret/webapp/database \
    username=appuser \
    password=S3cur3P@ssw0rd \
    host=postgres.production.svc \
    port=5432 \
    database=myapp

$ vault kv put secret/webapp/redis \
    password=R3d1sS3cur3 \
    host=redis.production.svc \
    port=6379
```

```
Sidecar container com Vault Agent:

apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: production
spec:
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      serviceAccountName: webapp-sa
      containers:
      - name: app
        image: myapp:latest
        env:
        - name: DATABASE_URL
          value: "postgres://$(VAULT_DB_USER):$(VAULT_DB_PASS)@postgres:5432/myapp"
        - name: VAULT_DB_USER
          valueFrom:
            secretKeyRef:
              name: vault-secrets
              key: db-username
        - name: VAULT_DB_PASS
          valueFrom:
            secretKeyRef:
              name: vault-secrets
              key: db-password
        volumeMounts:
        - name: vault-secrets
          mountPath: /vault/secrets
          readOnly: true
      - name: vault-agent
        image: hashicorp/vault:latest
        env:
        - name: VAULT_ADDR
          value: "http://vault:8200"
        - name: VAULT_ROLE
          value: "webapp"
        command: ["vault", "agent", "-config=/vault/config/config.hcl"]
        volumeMounts:
        - name: vault-config
          mountPath: /vault/config
          readOnly: true
        - name: vault-secrets
          mountPath: /vault/secrets
      volumes:
      - name: vault-config
        configMap:
          name: vault-agent-config
      - name: vault-secrets
        emptyDir:
          medium: Memory
```

```
Configuracao do Vault Agent:

vault {
  address = "http://vault:8200"
}

auto_auth {
  method "kubernetes" {
    config = {
      role = "webapp"
      token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    }
  }
}

template {
  source      = "/vault/templates/db-creds.ctmpl"
  destination = "/vault/secrets/db-credentials"
}

# Template para gerar credenciais dinamicas
# /vault/templates/db-creds.ctmpl:
# {{ with secret "secret/data/webapp/database" -}}
# DB_USER={{ .Data.data.username }}
# DB_PASS={{ .Data.data.password }}
# {{- end }}
```

### Sealed Secrets

Sealed Secrets e uma solucao para armazenar secrets seguros no Git. Ele criptografa secrets usando o public key do cluster, de forma que apenas o cluster pode descriptografar.

```
Instalacao do Sealed Secrets:

# Via Helm
$ helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
$ helm install sealed-secrets sealed-secrets/sealed-secrets \
    --namespace kube-system

# Instalacao do kubeseal
$ brew install kubeseal
```

```
Criacao de Sealed Secrets:

# Criar secret normal
$ kubectl create secret generic webapp-secrets \
    --from-literal=database-url=postgres://user:pass@db:5432/myapp \
    --from-literal=api-key=abc123 \
    --dry-run=secret -o yaml > secrets.yaml

# Selar o secret
$ kubeseal --format yaml < secrets.yaml > sealed-secrets.yaml

# Resultado: Secret criptografado que pode ser commitado no Git
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: webapp-secrets
  namespace: production
spec:
  encryptedData:
    database-url: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
    api-key: AgCU432h5eS9b2M8XK9vN1pQ7rT3wY...
  template:
    metadata:
      name: webapp-secrets
      namespace: production

# Aplicar o Sealed Secret
$ kubectl apply -f sealed-secrets.yaml

# O Sealed Secrets controller ira descriptografar e criar o Secret
$ kubectl get secrets webapp-secrets
```

```
Rotacao automatica de Sealed Secrets:

apiVersion: v1
kind: ConfigMap
metadata:
  name: sealed-secrets-rotation
  namespace: kube-system
data:
  rotate-keys.sh: |
    #!/bin/bash
    # Script para rotacionar chaves do Sealed Secrets
    
    # Gerar nova chave
    kubectl create secret generic \
      -n kube-system \
      sealed-secrets-key-$(date +%Y%m%d) \
      --from-literal=tls.key=$(openssl genrsa 4096 2>/dev/null) \
      --from-literal=tls.crt=$(openssl req -new -x509 -nodes \
        -days 365 -key /dev/stdin 2>/dev/null)
    
    # Remover chave antiga
    kubectl delete secret -n kube-system sealed-secrets-key-old
    
    # Re-selar todos os secrets
    for secret in $(kubectl get sealedsecrets --all-namespaces -o jsonpath='{.items[*].metadata.namespace}/{.items[*].metadata.name}'); do
      ns=$(echo $secret | cut -d/ -f1)
      name=$(echo $secret | cut -d/ -f2)
      kubeseal --format yaml -n $ns < <(kubectl get sealedsecret $name -n $ns -o yaml) | kubectl apply -f -
    done
```

---

## 6. CI/CD Pipeline Security for Web Apps

### O CWE-502 e Pipeline Security

O CWE-502 (Deserialization of Untrusted Data) e especialmente relevante em pipelines CI/CD que podem processar artefatos de fontes nao confiaveis. Pipelines comprometidas podem injetar malware em imagens container e distribui-lo para producao.

### Principios de Seguranca em CI/CD

1. **Immutable pipelines**: Pipelines devem ser versionadas e imutiveis
2. **Least privilege**: Cada etapa deve ter apenas as permissoes necessarias
3. **Secrets isolation**: Secrets nao devem ser logados ou expostos
4. **Artifact signing**: Todos os artefatos devem ser assinados e verificaveis
5. **Audit trail**: Todas as acoes devem ser logadas e rastreaveis

```
GitHub Actions com security hardening:

name: Secure CI/CD Pipeline
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 1
      
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ github.repository }}:${{ github.sha }}
          format: spdx-json
      
      - name: Build image
        run: |
          docker build \
            --no-cache \
            --label "org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}" \
            --label "org.opencontainers.image.revision=${{ github.sha }}" \
            --label "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
      
      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1
      
      - name: Sign image with Cosign
        uses: sigstore/cosign-installer@main
        env:
          COSIGN_EXPERIMENTAL: "true"
        run: |
          cosign sign ghcr.io/${{ github.repository }}:${{ github.sha }}
          cosign attest \
            --predicate sbom.spdx.json \
            --type spdxjson \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
      
      - name: Push image
        run: |
          docker push ghcr.io/${{ github.repository }}:${{ github.sha }}
          docker tag ghcr.io/${{ github.repository }}:${{ github.sha }} \
            ghcr.io/${{ github.repository }}:latest
          docker push ghcr.io/${{ github.repository }}:latest
```

```
GitLab CI com security hardening:

stages:
  - build
  - scan
  - sign
  - deploy

variables:
  DOCKER_TLS_CERTDIR: "/certs"

build:
  stage: build
  image: docker:24.0
  services:
    - docker:24.0-dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
    - merge_requests

scan:
  stage: scan
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --exit-code 1 --severity HIGH,CRITICAL
      $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  allow_failure: false

sign:
  stage: sign
  image: alpine:latest
  before_script:
    - apk add --no-cache cosign
  script:
    - cosign sign $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main

deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/webapp
      app=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  environment:
    name: production
  only:
    - main
```

### Dependabot e Renovate para Dependency Updates

```
Configuracao de Dependabot (.github/dependabot.yml):

version: 2
updates:
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "security"
    reviewers:
      - "security-team"
  
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "security"
    allow:
      - dependency-type: "production"
    review:
      - "security-team"
  
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "ci"
      - "security"
```

```
Configuracao de Renovate (renovate.json):

{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    "security:openssf-scorecard"
  ],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"]
  },
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true,
      "automergeType": "pr",
      "requiredStatusChecks": ["ci/test", "ci/security-scan"]
    },
    {
      "matchPackagePatterns": ["*"],
      "matchCurrentVersion": "< 1.0.0",
      "automerge": false
    }
  ],
  "schedule": ["every weekend"]
}
```

---

## 7. Infrastructure as Code Security: Terraform e Pulumi

### Terraform Security

O CWE-918 (Server-Side Request Forgery) e o CWE-284 (Improper Access Control) sao comuns em configuracoes Terraform que expoem endpoints internos ou configuram permissoes incorretamente.

```
Terraform com security best practices:

# Provider com configuracao segura
provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Environment = "production"
      ManagedBy   = "terraform"
      Security    = "high"
    }
  }
}

# State remoto com encriptacao
terraform {
  backend "s3" {
    bucket         = "myapp-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# VPC com flow logs
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "production-vpc"
  }
}

resource "aws_flow_log" "vpc_flow_log" {
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  log_destination      = aws_cloudwatch_log_group.flow_log.arn
  log_destination_type = "cloud-watch-logs"
  
  tags = {
    Name = "vpc-flow-log"
  }
}

# Security Group com restricoes
resource "aws_security_group" "webapp" {
  name        = "webapp-sg"
  description = "Security group for web application"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "webapp-sg"
  }
}

# RDS com encriptacao e backup
resource "aws_db_instance" "main" {
  identifier     = "webapp-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  
  db_name  = "webapp"
  username = "admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name    = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  deletion_protection = true
  skip_final_snapshot = false
  
  tags = {
    Name = "webapp-db"
  }
}
```

```
Terraform com Checkov para security scanning:

# Instalacao do Checkov
# pip install checkov

# Escaneamento do diretorio Terraform
$ checkov -d . --framework terraform

# Escaneamento com suppressao de falhas especificas
# checkov -d . --framework terraform --check CKV_AWS_18

# Output de exemplo:
# Check: CKV_AWS_16: "Ensure all data stored in the RDS 
#   instance is encrypted"
# PASSED for resource: aws_db_instance.main

# Check: CKV_AWS_145: "Ensure the RDS database is not 
#   accessible via public internet"
# FAILED for resource: aws_db_instance.main
#   Reason: DB instance has public accessibility enabled

# Checkov no Terraform Cloud
# block "terraform" {
#   required_providers {
#     checkov = {
#       source  = "bridgecrewio/checkov"
#       version = ">= 3.0.0"
#     }
#   }
# }
```

### Pulumi Security

Pulumi permite escrever infraestrutura como codigo usando linguagens de programacao convencionais. Isso permite usar ferramentas de seguranca existentes.

```
Pulumi com TypeScript e security best practices:

import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";
import * as docker from "@pulumi/docker";

// VPC com flow logs
const vpc = new aws.ec2.Vpc("main-vpc", {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    enableDnsSupport: true,
    tags: {
        Name: "production-vpc",
        Environment: "production",
    },
});

// Flow logs para auditoria
const flowLogGroup = new aws.cloudwatch.LogGroup("vpc-flow-logs", {
    retentionInDays: 90,
});

const flowLogRole = new aws.iam.Role("flow-log-role", {
    assumeRolePolicy: JSON.stringify({
        Version: "2012-10-17",
        Statement: [{
            Action: "sts:AssumeRole",
            Effect: "Allow",
            Principal: {
                Service: "vpc-flow-logs.amazonaws.com",
            },
        }],
    }),
});

const flowLog = new aws.ec2.FlowLog("vpc-flow-log", {
    vpcId: vpc.id,
    trafficType: "ALL",
    logDestination: flowLogGroup.arn,
    iamRoleArn: flowLogRole.arn,
});

// Security Group com restricoes
const webappSg = new aws.ec2.SecurityGroup("webapp-sg", {
    vpcId: vpc.id,
    description: "Security group for web application",
    ingress: [{
        description: "HTTPS",
        fromPort: 443,
        toPort: 443,
        protocol: "tcp",
        cidrBlocks: ["0.0.0.0/0"],
    }],
    egress: [{
        fromPort: 0,
        toPort: 0,
        protocol: "-1",
        cidrBlocks: ["0.0.0.0/0"],
    }],
    tags: {
        Name: "webapp-sg",
    },
});

// RDS com encriptacao
const dbPassword = new pulumi.dynamic.Resource("db-password", {});

const dbSubnetGroup = new aws.rds.SubnetGroup("db-subnet", {
    subnetIds: privateSubnetIds,
});

const db = new aws.rds.Instance("main-db", {
    identifier: "webapp-db",
    engine: "postgres",
    engineVersion: "15.4",
    instanceClass: "db.t3.medium",
    allocatedStorage: 20,
    maxAllocatedStorage: 100,
    storageEncrypted: true,
    dbName: "webapp",
    username: "admin",
    password: dbPassword.result,
    vpcSecurityGroupIds: [dbSg.id],
    dbSubnetGroupName: dbSubnetGroup.name,
    backupRetentionPeriod: 7,
    deletionProtection: true,
    skipFinalSnapshot: false,
    tags: {
        Name: "webapp-db",
    },
});
```

---

## 8. OWASP Docker Security Top 10

O OWASP Docker Security Top 10 lista as vulnerabilidades e configuracoes inseguras mais comuns em ambientes Docker. Este guia e baseado na versao mais recente e fornece orientacoes praticas para remediacoes.

### DSC01: Insecure Default Configuration

```
Configuracao padrao insegura vs configuracao segura:

INSEGURO - daemon Docker com configuracoes padrao:
{
  "hosts": ["unix:///var/run/docker.sock"],
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "userland-proxy": true,
  "live-restore": false
}

SEGURO - daemon Docker hardenado:
{
  "hosts": ["unix:///var/run/docker.sock"],
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "userland-proxy": false,
  "live-restore": true,
  "no-new-privileges": true,
  "userns-remap": "default",
  "icc": false,
  "userland-proxy": false,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65535,
      "Soft": 65535
    }
  },
  "default-address-pools": [
    {
      "base": "172.17.0.0/12",
      "size": 24
    }
  ]
}
```

### DSC02: Container Runtime Vulnerabilities

```
Atualizacao e hardening do runtime:

# Verificar versao do Docker
$ docker version

# Verificar versao do containerd
$ containerd --version

# Verificar versao do runc
$ runc --version

# Atualizar Docker
$ sudo apt-get update
$ sudo apt-get upgrade docker-ce docker-ce-cli containerd.io

# Verificar se ha containers rodando com privilegios excessivos
$ docker ps --format '{{.Names}} {{.Image}}' | while read name image; do
  caps=$(docker inspect --format '{{.HostConfig.Privileged}}' $name)
  if [ "$caps" = "true" ]; then
    echo "WARNING: $name is running with --privileged"
  fi
done
```

### DSC03: Excessive Container Capabilities

```
Remocao de capabilities desnecessarias:

# Listar capabilities padrao
$ docker run --rm alpine sh -c "cat /proc/1/status | grep Cap"

# Container com todas as capabilities (INSEGURO)
$ docker run --rm --cap-add=ALL alpine sh

# Container com apenas NET_BIND_SERVICE (SEGURO)
$ docker run --rm --cap-drop=ALL --cap-add=NET_BIND_SERVICE alpine sh

# Dockerfile com minimal capabilities
FROM alpine:3.18

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

USER appuser

CMD ["app"]
```

### DSC04: Vulnerable Container Images

```
Escaneamento de imagens com Trivy:

# Escanear imagem especifica
$ trivy image --severity HIGH,CRITICAL nginx:latest

# Escaneamento em lote
$ for image in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -v '<none>'); do
  echo "Scanning $image..."
  trivy image --exit-code 1 --severity HIGH,CRITICAL $image
done

# Integracao com Docker Hub
$ trivy image --download-db-only
$ trivy image --severity HIGH,CRITICAL myregistry.com/myapp:latest
```

### DSC05: Container Breakout

```
Prevencao de container breakout:

# 1. Nao usar --privileged
# 2. Usar non-root user
# 3. Usar read-only filesystem
# 4. Limitar capabilities
# 5. Usar AppArmor ou SELinux
# 6. Usar seccomp profiles
# 7. Usar namespaces de rede

# Exemplo de comando seguro
$ docker run \
  --rm \
  --read-only \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt=no-new-privileges \
  --security-opt apparmor=docker-default \
  --security-opt seccomp=profile.json \
  --user 1001:1001 \
  --tmpfs /tmp:size=100M \
  --tmpfs /var/run:size=10M \
  myapp:latest
```

### DSC06: Inadequate Logging and Monitoring

```
Configuracao de logging centralizado:

# Docker driver de logging
$ docker run -d \
  --log-driver=syslog \
  --log-opt syslog-address=tcp://logserver:514 \
  --log-opt syslog-facility=daemon \
  --log-opt tag="{{.ImageName}}/{{.Name}}/{{.ID}}" \
  myapp:latest

# Fluentd para agregacao de logs
$ docker run -d \
  --name fluentd \
  --log-driver=fluentd \
  --log-opt fluentd-address=localhost:24224 \
  myapp:latest
```

### DSC07: Inadequate Secrets Management

```
Gerenciamento seguro de secrets:

# NUNCA usar variaveis de ambiente para secrets
$ docker run -e DB_PASSWORD=secret123 myapp  # ERRADO

# Usar Docker secrets
$ echo "secret123" | docker secret create db_password -

# Usar arquivos montados como tmpfs
$ docker run \
  --mount type=tmpfs,target=/run/secrets \
  --tmpfs /run/secrets:size=10M \
  myapp:latest

# Usar Vault com sidecar
# (veja secao 5 para detalhes)
```

### DSC08: Network Misconfigurations

```
Configuracao de rede segura:

# Criar rede isolada
$ docker network create \
  --driver bridge \
  --internal \
  --subnet 172.28.0.0/16 \
  app-network

# Conectar containers apenas as redes necessarias
$ docker run --network app-network myapp:latest

# Verificar conectividade
$ docker network inspect app-network

# Configurar DNS customizado
$ docker run \
  --dns=8.8.8.8 \
  --dns-search=example.com \
  myapp:latest
```

### DSC09: Inadequate Resource Management

```
Limites de recursos para containers:

# Limitar CPU e memoria
$ docker run \
  --cpus=1.5 \
  --memory=512m \
  --memory-swap=512m \
  --pids-limit=100 \
  --ulimit nofile=1024:1024 \
  myapp:latest

# Docker Compose com limites
$ docker-compose up -d

# Verificar uso de recursos
$ docker stats --no-stream
```

### DSC10: Supply Chain Attacks

```
Protecao contra supply chain attacks:

# 1. Usar imagens oficiais
FROM node:18-alpine  # OFICIAL
FROM custom-node:18  # POTENCIALMENTE INSEGURO

# 2. Usar digest especifico
FROM node:18-alpine@sha256:abc123...

# 3. Verificar assinaturas com Cosign
$ cosign verify --key cosign.pub myregistry.com/myapp:v1.0

# 4. Gerar SBOM
$ syft myapp:latest -o spdx-json > sbom.json

# 5. Escanear SBOM
$ grype sbom:./sbom.json
```

---

## 9. Vulnerability Scanning: Trivy, Grype e Snyk

### Trivy em Profundidade

Trivy e a ferramenta mais completa para vulnerability scanning de containers. Ele suporta múltiplos targets e formatos de output.

```
Trivy para diferentes targets:

# Escanear imagem
$ trivy image nginx:latest

# Escanear filesystem
$ trivy fs --scanners vuln,misconfig,secret /path/to/app

# Escanear repositório Git
$ trivy repo https://github.com/user/repo

# Escanear configuration files
$ trivy config --scanners misconfig .

# Escanear SBOM
$ trivy sbom ./sbom.json
```

```
Trivy com configurações customizadas:

# Configuracao de escaneamento (.trivyignore)
# Ignorar CVEs especificos (usar com cuidado)
CVE-2023-XXXXX

# Configuracao de formato
$ trivy image \
  --format json \
  --output results.json \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  myapp:latest

# Trivy com cache
$ trivy image \
  --cache-dir /tmp/trivy-cache \
  myapp:latest

# Trivy com custom registries
$ trivy image \
  --username user \
  --password pass \
  myregistry.com/myapp:latest
```

```
Integracao de Trivy com Kubernetes:

# Scan Operator no Kubernetes
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trivy-operator
  namespace: trivy-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: trivy-operator
  template:
    metadata:
      labels:
        app: trivy-operator
    spec:
      containers:
      - name: trivy-operator
        image: aquasec/trivy-operator:latest
        env:
        - name: TRIVY_SEVERITY
          value: "HIGH,CRITICAL"
        - name: TRIVY_TIMEOUT
          value: "5m"
```

### Grype em Profundidade

Grype e uma ferramenta de scanning focada em vulnerabilidades. Ele suporta SBOM como input e pode ser integrado com Syft.

```
Grype para diferentes targets:

# Escanear imagem
$ grype nginx:latest

# Escanear com SBOM
$ syft nginx:latest -o spdx-json > sbom.json
$ grype sbom:./sbom.json

# Escanear diretorio
$ grype dir:./my-app/

# Escanear com ignore file
$ grype nginx:latest --ignore .grypeignore

# Formato de output
$ grype nginx:latest -o table
$ grype nginx:latest -o json
$ grype nginx:latest -o sarif
$ grype nginx:latest -o cyclonedx
```

```
Configuracao de Grype (.grype.yaml):

# Configuracao de escaneamento
output: table
fail-on-severity: high

# Configuracao de database
db:
  auto-update: true
  cache-dir: /tmp/grype-db

# Configuracao de match
match:
  vuln:
    paths:
      # Ignorar vulnerabilidades em paths especificos
      - excludes:
        - "**/test/**"
        - "**/tests/**"
  package:
    # Ignorar pacotes especificos
    - excludes:
      - name: "test-package"
```

### Snyk Container em Profundidade

Snyk oferece escaneamento com remediation advice e integracao com IDEs.

```
Snyk Container para diferentes targets:

# Escanear imagem
$ snyk container test nginx:latest

# Escanear com monitoramento continuo
$ snyk container monitor nginx:latest

# Escanear Dockerfile
$ snyk container test --file=Dockerfile .

# Escanear com base image
$ snyk container test --file=Dockerfile \
  --base-image=node:18-alpine .

# Formato de output
$ snyk container test --json nginx:latest
$ snyk container test --sarif nginx:latest
$ snyk container test --html nginx:latest
```

```
Snyk com GitHub Integration:

# Configuracao no .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"

# Configuracao de Snyk no GitHub
# Settings > Security > Code security and analysis
# - Dependabot alerts: Enabled
# - Dependabot security updates: Enabled
# - Secret scanning: Enabled
```

### Comparacao de Ferramentas

| Feature | Trivy | Grype | Snyk |
|---------|-------|-------|------|
| Tipo | Open source | Open source | Freemium |
| Velocidade | Rapido | Rapido | Medio |
| Cobertura | Imagem, FS, repo | Imagem, SBOM | Imagem, Dockerfile |
| Formatos | JSON, SARIF, table | JSON, SARIF, table | JSON, SARIF, HTML |
| SBOM | Suporta | Suporta | Suporta |
| Remediation | Limitada | Limitada | Detalhada |
| Integracao CI/CD | Excelente | Boa | Excelente |
| Custo | Gratuito | Gratuito | Pago para uso avancado |

---

## 10. Supply Chain Attacks in Web Deployment

### Vetores de Ataque na Supply Chain

Supply chain attacks envolvem comprometer um componente da cadeia de distribuicao de software. Em ambientes web, os principais vetores sao:

1. **Dependencias comprometidas**: Bibliotecas com malware injetado
2. **Imagens Docker comprometidas**: Imagens com backdoors
3. **Registry publico**: Comprometimento de registries
4. **Build pipeline**: Comprometimento de ferramentas CI/CD
5. **Artifact repositories**: Comprometimento de packages
6. **Developer machines**: Comprometimento de ambientes de desenvolvimento

### Casos Reais de Supply Chain Attacks

**EventStream (2018)**: O pacote npm event-stream, com mais de 2 milhoes de downloads por semana, teve malware injetado por um maintainer malicioso. O malware roubava criptomoedas de carteiras Copay.

**Codecov (2021)**: O atacante modificou o bash uploader do Codecov para exfiltrar variaveis de ambiente de pipelines CI/CD. Isso expôs credenciais de AWS, GitHub, e outros servicos.

**Log4Shell (2021)**: Embora nao seja um ataque de supply chain no sentido tradicional, a vulnerabilidade no Log4j afetou milhares de aplica que usavam a biblioteca.

**SolarWinds (2020)**: Um dos maiores ataques de supply chain da historia. O atacante comprometeu o build process do SolarWinds Orion, injetando backdoor em atualizacoes de software.

### Defesas Contra Supply Chain Attacks

```
Defesa em camadas:

1. DEPENDENCY MANAGEMENT:
   - Usar lock files (package-lock.json, yarn.lock)
   - Audit dependencies regularmente
   - Usar Dependabot ou Renovate
   - Verificar hashes de dependencias

2. IMAGE SECURITY:
   - Usar imagens oficiais ou verificadas
   - Usar digest especifico (nao apenas tags)
   - Assinar imagens com Cosign
   - Verificar assinaturas antes de deploy

3. BUILD SECURITY:
   - Usar multi-stage builds
   - Nao usar --privileged no build
   - Escanear imagens antes do push
   - Gerar SBOM para cada build

4. REGISTRY SECURITY:
   - Usar registries privados
   - Habilitar content trust
   - Usar autenticacao por tokens
   - Monitorar acessos ao registry

5. DEPLOYMENT SECURITY:
   - Verificar assinaturas antes do deploy
   - Usar admission controllers no Kubernetes
   - Implementar gitops com verificacao
   - Monitorar anomalias no deployment
```

```
Exemplo de pipeline com defesa em camadas:

name: Secure Supply Chain Pipeline
on:
  push:
    branches: [main]

jobs:
  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit dependencies
        run: |
          npm audit --audit-level=high
          npx better-npm-audit audit
      - name: Check for known vulnerabilities
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  build:
    needs: dependencies
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: |
          docker build \
            --label "org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}" \
            --label "org.opencontainers.image.revision=${{ github.sha }}" \
            -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
      - name: Generate SBOM
        run: |
          syft ghcr.io/${{ github.repository }}:${{ github.sha }} \
            -o spdx-json=sbom.json
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: 1

  sign:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      packages: write
    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@main
      - name: Sign image
        env:
          COSIGN_EXPERIMENTAL: "true"
        run: |
          cosign sign ghcr.io/${{ github.repository }}:${{ github.sha }}
          cosign attest \
            --predicate sbom.json \
            --type spdxjson \
            ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy:
    needs: sign
    runs-on: ubuntu-latest
    steps:
      - name: Verify signature
        uses: sigstore/cosign-installer@main
      - name: Verify image
        env:
          COSIGN_EXPERIMENTAL: "true"
        run: |
          cosign verify \
            --certificate-identity=you@example.com \
            --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
      - name: Deploy
        run: |
          kubectl set image deployment/webapp \
            app=ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 11. Complete Dockerfile and docker-compose Security

### Dockerfile Seguro Completo

```dockerfile
# Stage 1: Build
FROM node:18-alpine AS builder

# Instalar dependencias de build
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Copiar apenas arquivos necessarios para build
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copiar codigo fonte
COPY . .

# Compilar a aplicacao
RUN npm run build

# Stage 2: Production
FROM node:18-alpine

# Instalar pacotes de sistema minimos
RUN apk add --no-cache \
    tini \
    curl \
    && rm -rf /var/cache/apk/*

# Criar usuario nao-privilegiado
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Definir diretorio de trabalho
WORKDIR /app

# Copiar dependencias de production
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules

# Copiar artifacts de build
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

# Configurar permissoes
RUN chown -R appuser:appgroup /app && \
    chmod -R 550 /app && \
    chmod 750 /app/dist && \
    chmod 750 /app/node_modules

# Criar diretorio para dados temporarios
RUN mkdir -p /app/tmp /app/logs && \
    chown -R appuser:appgroup /app/tmp /app/logs && \
    chmod 770 /app/tmp /app/logs

# Definir variaveis de ambiente
ENV NODE_ENV=production
ENV PORT=3000

# Expor porta apenas internamente
EXPOSE 3000

# Definir usuario
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Usar tini como init
ENTRYPOINT ["/sbin/tini", "--"]

# Comando da aplicacao
CMD ["node", "dist/server.js"]
```

### docker-compose.yml Seguro Completo

```yaml
version: '3.8'

services:
  webapp:
    build:
      context: .
      dockerfile: Dockerfile
    image: myapp:latest
    container_name: webapp
    restart: unless-stopped
    user: "1001:1001"
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
    tmpfs:
      - /tmp:size=100M,noexec,nosuid,nodev
      - /app/tmp:size=50M,noexec,nosuid
      - /app/logs:size=50M,noexec,nosuid
      - /var/cache:size=50M,noexec,nosuid
    networks:
      - frontend
      - backend
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    env_file:
      - .env
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        tag: "{{.Name}}/{{.ID}}"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    restart: unless-stopped
    user: "999:999"
    read_only: true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
      - FOWNER
      - DAC_READ_SEARCH
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
    environment:
      - POSTGRES_DB=webapp
      - POSTGRES_USER=appuser
      - POSTGRES_PASSWORD_FILE=/run/secrets/db-password
    secrets:
      - db-password
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - /tmp:/tmp
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '1.0'
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d webapp"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    user: "999:999"
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
    command: >
      redis-server
      --maxmemory 128mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  frontend:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "false"
  backend:
    driver: bridge
    internal: true

volumes:
  postgres-data:
    driver: local

secrets:
  db-password:
    file: ./secrets/db-password.txt
```

### Docker Compose com Profiles para Diferentes Ambientes

```yaml
# docker-compose.override.yml (desenvolvimento)
version: '3.8'

services:
  webapp:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder
    volumes:
      - ./src:/app/src:ro
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - DEBUG=*
    ports:
      - "127.0.0.1:3000:3000"
      - "127.0.0.1:9229:9229"
    cap_add:
      - SYS_PTRACE

# docker-compose.prod.yml (producao)
version: '3.8'

services:
  webapp:
    image: myregistry.com/myapp:${VERSION:-latest}
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 30s
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
    logging:
      driver: fluentd
      options:
        fluentd-address: "localhost:24224"
        fluentd-async: "true"
```

---

## 12. Kubernetes Deployment com Security Best Practices

### Deployment Completo Seguro

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: webapp-sa
  namespace: production
automountServiceAccountToken: false

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: webapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
  resourceNames: ["webapp-config"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["webapp-secrets"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: webapp-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: webapp-sa
  namespace: production
roleRef:
  kind: Role
  name: webapp-role
  apiGroup: rbac.authorization.k8s.io

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: production
  labels:
    app: webapp
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: webapp-sa
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        runAsGroup: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: myregistry.com/webapp:v1.0@sha256:abc123...
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 3000
          protocol: TCP
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "3000"
        envFrom:
        - configMapRef:
            name: webapp-config
        - secretRef:
            name: webapp-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: app-data
          mountPath: /app/data
        - name: app-logs
          mountPath: /app/logs
        resources:
          limits:
            cpu: "1"
            memory: 256Mi
          requests:
            cpu: "0.5"
            memory: 128Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
          failureThreshold: 30
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 100Mi
      - name: app-data
        emptyDir: {}
      - name: app-logs
        emptyDir: {}
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: webapp

---
apiVersion: v1
kind: Service
metadata:
  name: webapp
  namespace: production
spec:
  selector:
    app: webapp
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: webapp-network-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: webapp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: webapp-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: webapp

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: webapp-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: webapp
            port:
              number: 80
```

---

## 13. Exercicios

### Exercicio 1: Dockerfile Security Audit

**Objetivo**: Identificar e corrigir vulnerabilidades em um Dockerfile.

**Dockerfile vulneravel para auditar**:

```dockerfile
FROM ubuntu:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    vim \
    net-tools \
    tcpdump

WORKDIR /app

COPY . .

RUN pip3 install flask psycopg2-binary redis

ENV DATABASE_URL=postgres://admin:password123@db:5432/prod
ENV AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
ENV FLASK_SECRET_KEY=my-super-secret-key

EXPOSE 5000

CMD python3 app.py
```

**Tarefa**: Identificar todas as vulnerabilidades e criar uma versao corrigida do Dockerfile.

**Vulnerabilidades a identificar**:
1. Imagem base usando tag `latest`
2. Pacotes desnecessarios instalados
3. Secrets hardcoded em variaveis de ambiente
4. Container roda como root
5. Arquivos de build (COPY . .) incluem arquivos desnecessarios
6. Sem multi-stage build
7. Sem health check
8. Sem definicao de usuario nao-privilegiado

### Exercicio 2: Kubernetes Network Policy

**Objetivo**: Criar Network Policies que isolem tres microservicos.

**Cenario**: Voce tem tres servicos:
- `frontend`: Recebe trafego externo e se comunica com `backend`
- `backend`: Se comunica com `frontend` e `database`
- `database`: Apenas recebe trafego do `backend`

**Tarefa**: Criar Network Policies que:
1. Neguem todo trafego por padrao
2. Permitam trafego HTTP externo para `frontend`
3. Permitam trafego de `frontend` para `backend` na porta 8080
4. Permitam trafego de `backend` para `database` na porta 5432
5. Permitam DNS (porta 53) para todos os pods

### Exercicio 3: RBAC Configuration

**Objetivo**: Configurar RBAC para tres profiles de usuario diferentes.

**Profiles**:
1. **Developer**: Acesso a pods, logs, e configmaps no namespace `development`
2. **Ops**: Acesso a pods, deployments, services em todos os namespaces (exceto `kube-system`)
3. **Auditor**: Acesso somente-leitura a todos os recursos em todos os namespaces

**Tarefa**: Criar Roles, ClusterRoles, RoleBindings e ClusterRoleBindings apropriados.

### Exercicio 4: Supply Chain Security Pipeline

**Objetivo**: Criar um pipeline CI/CD seguro que implemente defesa em camadas.

**Requisitos**:
1. Scan de dependencias com Snyk ou npm audit
2. Build de imagem com labels OCI
3. Scan de imagem com Trivy
4. Geracao de SBOM com Syft
5. Assinatura de imagem com Cosign
6. Verificacao de assinatura antes do deploy
7. Deploy apenas se todas as verificacoes passarem

**Tarefa**: Criar um GitHub Actions workflow que implemente todas as etapas.

### Exercicio 5: Vault Integration

**Objetivo**: Configurar gerenciamento de secrets com HashiCorp Vault.

**Tarefa**:
1. Configurar Vault server com Kubernetes auth method
2. Criar secrets engine para a aplicacao
3. Configurar policies de acesso
4. Criar sidecar container que injeta secrets na aplicacao
5. Implementar rotacao automatica de secrets

### Exercicio 6: Container Escape Prevention

**Objetivo**: Implementar todas as camadas de defesa contra container escape.

**Tarefa**: Criar um deployment Kubernetes que implemente:
1. Pod Security Standards nivel `restricted`
2. Security context completo (runAsNonRoot, readOnlyRootFilesystem, drop ALL capabilities)
3. Seccomp profile customizado
4. AppArmor profile customizado
5. Network policies de isolamento
6. Resource limits
7. Audit logging configurado

### Exercicio 7: Vulnerability Remediation

**Objetivo**: Remediar vulnerabilidades encontradas em uma imagem Docker.

**Cenario**: O Trivy encontrou 15 vulnerabilidades HIGH e 3 CRITICAL na imagem `myapp:latest`.

**Tarefa**:
1. Analisar cada vulnerabilidade e classificar por severidade e exploitabilidade
2. Criar plano de remediacao priorizado
3. Atualizar Dockerfile para corrigir vulnerabilidades
4. Re-escanear e documentar resultado
5. Criar processo de monitoramento continuo

---

## 14. Referencias

### Documentacao Oficial

1. Docker Security Documentation. https://docs.docker.com/engine/security/
2. Kubernetes Security Documentation. https://kubernetes.io/docs/concepts/security/
3. HashiCorp Vault Documentation. https://developer.hashicorp.com/vault/docs
4. Sigstore Documentation. https://docs.sigstore.dev/
5. Trivy Documentation. https://trivy.dev/latest/
6. Grype Documentation. https://github.com/anchore/grype
7. Snyk Container Documentation. https://docs.snyk.io/products/snyk-container
8. gVisor Documentation. https://gvisor.dev/docs/
9. Kata Containers Documentation. https://katacontainers.io/docs/
10. Sealed Secrets Documentation. https://sealed-secrets.netlify.app/

### OWASP Resources

11. OWASP Docker Security Top 10. https://owasp.org/www-project-docker-top-10/
12. OWASP Application Security Verification Standard (ASVS). https://owasp.org/www-project-application-security-verification-standard/
13. OWASP Software Component Verification Standard (SCVS). https://owasp.org/www-project-software-component-verification-standard/
14. OWASP Supply Chain Security. https://owasp.org/supply-chain-security/

### CWE References

15. CWE-798: Use of Hard-coded Credentials. https://cwe.mitre.org/data/definitions/798.html
16. CWE-250: Execution with Unnecessary Privileges. https://cwe.mitre.org/data/definitions/250.html
17. CWE-400: Uncontrolled Resource Consumption. https://cwe.mitre.org/data/definitions/400.html
18. CWE-502: Deserialization of Untrusted Data. https://cwe.mitre.org/data/definitions/502.html
19. CWE-284: Improper Access Control. https://cwe.mitre.org/data/definitions/284.html
20. CWE-918: Server-Side Request Forgery. https://cwe.mitre.org/data/definitions/918.html

### CVEs em Containers

21. CVE-2019-5736: runc container escape. https://nvd.nist.gov/vuln/detail/CVE-2019-5736
22. CVE-2020-15257: containerd network namespace escape. https://nvd.nist.gov/vuln/detail/CVE-2020-15257
23. CVE-2022-0185: Linux kernel filesystem escape. https://nvd.nist.gov/vuln/detail/CVE-2022-0185
24. CVE-2022-0811: CRI-O cr8escape. https://nvd.nist.gov/vuln/detail/CVE-2022-0811
25. CVE-2014-3153: Linux kernel futex exploit. https://nvd.nist.gov/vuln/detail/CVE-2014-3153

### Supply Chain Attacks

26. EventStream npm incident. https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident
27. Codecov bash uploader compromise. https://about.codecov.io/security-update/
28. SolarWinds supply chain attack. https://www.crowdstrike.com/blog/sunspot-malware-technical-analysis/
29. Log4Shell vulnerability. https://logging.apache.org/log4j/2.x/security.html
30. colors.js sabotage. https://github.com/Marak/colors.js/issues/193

### Ferramentas de Seguranca

31. Checkov: Infrastructure as Code scanning. https://www.checkov.io/
32. Syft: SBOM generation. https://github.com/anchore/syft
33. Kyverno: Kubernetes policy engine. https://kyverno.io/
34. OPA Gatekeeper: Kubernetes admission control. https://open-policy-agent.github.io/gatekeeper/
35. Falco: Runtime security. https://falco.org/

### Artigos e Papers

36. "Container Security" by Liz Rice (O'Reilly, 2021)
37. "Kubernetes Security and Observability" by Brendan Creane (O'Reilly, 2022)
38. "Docker Security" by Adrian Mouat (O'Reilly, 2021)
39. "Supply Chain Attacks: An Industry Perspective" (NIST, 2023)
40. "Building Secure and Reliable Systems" by Google SRE Team (O'Reilly, 2020)

### Normas e Padroes

41. NIST SP 800-190: Application Container Security Guide
42. CIS Docker Benchmark
43. CIS Kubernetes Benchmark
44. PCI DSS v4.0 Container Requirements
45. LGPD: Lei Geral de Protecao de Dados

---

## Resumo do Capitulo

Este capitulo cobriu os principais aspectos de seguranca em containers e deployment para aplica web. Os pontos-chave sao:

**Docker Security**: Sempre usar imagens oficiais ou verificadas, implementar non-root users, configurar read-only filesystems, e escanear imagens regularmente.

**Kubernetes Security**: Implementar RBAC com principio do menor privilegio, usar Pod Security Standards nivel restricted, configurar Network Policies de isolamento, e usar ServiceAccounts dedicadas.

**Container Runtimes**: Para workloads criticos, considerar gVisor ou Kata Containers para isolamento adicional.

**Supply Chain**: Assinar imagens com Cosign/Sigstore, gerar SBOMs, e verificar assinaturas antes do deployment.

**Secrets Management**: Nunca hardcode secrets, usar Vault ou Sealed Secrets, e implementar rotacao automatica.

**CI/CD Security**: Implementar pipelines seguras com scanning de dependencias, build de imagens, e verificacao de assinaturas.

**Infrastructure as Code**: Usar ferramentas como Checkov para auditar configuracoes Terraform e Pulumi.

**Monitoring**: Implementar logging centralizado, audit trails, e alertas de seguranca.

A seguranca de containers nao e um checkpoint, e um processo continuo. Atualize regularmente dependencias, escaneie imagens frequentemente, e revise configuracoes periodicamente.
