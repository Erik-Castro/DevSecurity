# Capítulo 11: Supply Chain de Plugins

## 11.1 Introdução a Supply Chain de Plugins

Supply chain de plugins é o ecossistema completo que envolve o desenvolvimento, distribuição, instalação e execução de componentes de software de terceiros dentro de uma plataforma. No contexto de WebAssembly, esse conceito ganha uma complexidade adicional devido à natureza portátil e sandboxed dos módulos Wasm, que podem ser distribuídos como binários compactos e executados em múltiplos ambientes sem recompilação.

A segurança da supply chain de plugins abrange desde a origem do código-fonte até o momento em que o plugin é executado em runtime. Cada etapa — compilação, assinatura, distribuição, verificação, instalação e execução — representa um ponto potencial de comprometimento. Um atacante que consiga injetar código malicioso em qualquer ponto dessa cadeia pode comprometer todo o sistema que carrega o plugin.

### 11.1.1 O que é Segurança de Supply Chain de Plugins

Segurança de supply chain de plugins refere-se ao conjunto de práticas, ferramentas e processos projetados para garantir a integridade, autenticidade e não-repúdio de componentes de software de terceiros ao longo de toda a sua cadeia de distribuição. Isso inclui:

- **Integridade**: O plugin que chega ao runtime é idêntico ao que foi publicado pelo desenvolvedor original.
- **Autenticidade**: O plugin foi realmente publicado pelo autor declarado.
- **Não-repúdio**: O desenvolvedor não pode negar ter publicado o plugin.
- **Disponibilidade**: Plugins legítimos estão acessíveis quando necessários.
- **Confidencialidade**: Se aplicável, o código proprietário do plugin não é exposto a terceiros não autorizados.

Diferentemente de bibliotecas tradicionais, plugins Wasm possuem características únicas que afetam a segurança da supply chain:

```text
+-------------------------------------------------------------------+
|                  Caracteristicas Unicas de Plugins Wasm            |
+-------------------------------------------------------------------+
|                                                                   |
|  Binarios compactos  --->  Facil distribuicao, dificil auditoria  |
|  Portabilidade       --->  Mesmo binario em multiplas plataformas |
|  Sandbox nativo      --->  Isolamento, mas tambem ofuscacao       |
|  Component Model     --->  Interfaces ricas, superficie de ataque  |
|  WASI capabilities   --->  Permissoes granulares, complexidade     |
|  Hot-loading         --->  Atualizacao dinamica, risco temporal    |
|  Marketplace         --->  Distribuicao centralizada, confianca    |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.1.2 Por que Plugins Wasm representam um Desafio Único

WebAssembly introduz desafios específicos para a segurança de supply chain que não existem em ecossistemas de plugins tradicionais:

**Binários opacos**: Diferentemente de scripts JavaScript que podem ser lidos e auditados, módulos Wasm são bytecode compilado. A análise direta requer ferramentas especializadas como `wasm-tools`, `wasm-objdump` ou decompiladores como `wasm-decompile`. Isso dificulta a auditoria manual e torna a verificação automatizada essencial.

**Execução multi-runtime**: Um módulo Wasm pode ser executado em Wasmer, Wasmtime, WasmEdge, V8 ou qualquer outro runtime compatível. Cada runtime pode ter comportamentos sutis diferentes, tornando o teste de segurança mais complexo.

**Component Model**: O novo modelo de componentes do Wasm permite composição dinâmica de módulos, onde um plugin pode depender de outros componentes. Isso cria uma cadeia de dependências similar à do npm, mas com menos maturidade em ferramentas de auditoria.

**Capacidades WASI**: Plugins Wasm podem solicitar acesso a capacidades específicas (sistema de arquivos, rede, variáveis de ambiente) via WASI. A composição dessas capacidades pode criar vetores de ataque inesperados.

```text
+--------------------------------------------------------------------+
|             Diferenca: Plugins Tradicionais vs Wasm                 |
+--------------------------------------------------------------------+
|                                                                    |
|  Tradicionais (JS, Python):                                        |
|  - Codigo-fonte legivel, auditavel manualmente                     |
|  - Runtime conhecido e documentado                                  |
|  - Dependencias via package manager (npm, pip)                     |
|  - Ferramentas maduras de audit (npm audit, safety)                |
|                                                                    |
|  Wasm Plugins:                                                     |
|  - Binarios compilados, requerem ferramentas especiais              |
|  - Multi-runtime, comportamento pode variar                        |
|  - Dependencias via Component Model ou WASI                        |
|  - Ferramentas de audit em fase inicial de maturidade              |
|  - Portabilidade binaria facilita distribuicao massiva             |
|                                                                    |
+--------------------------------------------------------------------+
```

### 11.1.3 Vetores de Ataque em Ecossistemas de Plugins

Os vetores de ataque em ecossistemas de plugins podem ser categorizados em diferentes fases da supply chain:

**Fase de Desenvolvimento**:
- Comprometimento do ambiente de desenvolvimento do autor
- Injeção de código malicioso via dependências (dependency confusion)
- Comprometimento de credenciais de acesso ao repositório
- Manipulação do código-fonte antes da compilação

**Fase de Build**:
- Comprometimento do pipeline de CI/CD
- Injeção durante a compilação para Wasm
- Modificação dos artefatos de build
- Comprometimento de chaves de assinatura

**Fase de Distribuição**:
- Ataque man-in-the-middle no download do plugin
- Comprometimento do marketplace ou registry
- Typosquatting (nomes similares ao plugin legítimo)
- Squatting (registro antecipado de nomes populares)
- Bumping de versão (inserção em cadeia de dependências)

**Fase de Instalação e Execução**:
- Verificação de integridade insuficiente
- Permissões WASI excedentes
- Cadeia de confiança quebrada
- Atualização maliciosa de versão

```text
+------------------------------------------------------------------+
|                  Vetores de Ataque na Supply Chain                |
+------------------------------------------------------------------+
|                                                                  |
|  DESenvolvimento  --->  Build  --->  Distribuicao  --->  Runtime |
|       |                 |               |                   |    |
|   [Comprometimento  [CI/CD hack]   [MITM, marketplace   [WASI   |
|    do autor,        [Injecao no    [Typosquatting,       permis- |
|    dependencia      compilador]    version bumping]      soes]  |
|    confusion]                                                       |
|                                                                  |
+------------------------------------------------------------------+
```

### 11.1.4 Ataques Reais de Supply Chain em Ecossistemas de Plugins

Embora a ecossistema Wasm seja relativamente jovem, ataques de supply chain em ecossistemas similares oferecem lições valiosas:

**EventStream (2018)**: O pacote npm `event-stream`, com milhões de downloads semanais, teve código malicioso injetado através de uma transferência de manutenção para um novo maintainer. O código malicioso visava roubar criptomoedas de usuários do aplicativo Copay.

**UA-parser-js (2021)**: Pacotes populares no npm foram comprometidos e tiveram dependências maliciosas injetadas. O pacote atingiu cerca de 8 milhões de downloads por semana, potencialmente expondo dados de criptomoedas.

**SolarWinds (2020)**: Embora não seja um ecossistema de plugins tradicional, o ataque ao SolarWinds demonstra como um comprometimento na cadeia de build pode ser devastador. O malware Orion foi injetado durante o processo de build e distribuído como atualização legítima.

**Codecov (2021)**: O script de upload de cobertura do Codecov foi modificado, comprometendo dados de build de milhares de empresas por dois meses.

Esses incidentes demonstram que a segurança de supply chain não é teórica — é uma ameaça real que requer mitigação ativa.

### 11.1.5 O Problema da Confiança em Marketplaces Distribuídos

Marketplaces de plugins criam um modelo de confiança onde o marketplace atua como intermediário entre desenvolvedores e usuários. Isso cria plusieurs problemas:

**Concentração de confiança**: O marketplace se torna um único ponto de falha. Se comprometido, todos os plugins distribuídos através dele podem ser afetados.

**Escala de distribuição**: Um plugin popular pode ser instalado milhões de vezes antes de uma vulnerabilidade ser descoberta. A velocidade de distribuição supera a capacidade de auditoria.

**Incentivos desalinhados**: Marketplaces frequentemente priorizam conveniência e velocidade de publicação sobre verificação de segurança, criando uma tensão entre usabilidade e segurança.

**Falta de transparência**: Usuários frequentemente não têm visibilidade sobre as dependências, processo de build ou história de segurança de um plugin.

**Modelo de confiança em cascata**: Um plugin confiável pode depender de bibliotecas não confiáveis, criando uma cadeia de confiança difícil de auditar.

```text
+-------------------------------------------------------------------+
|         Problema da Confianca em Marketplaces de Plugins           |
+-------------------------------------------------------------------+
|                                                                   |
|  +----------+     +-------------+     +------------+              |
|  | Desenvol-|     |  Marketplace|     |   Usuario  |              |
|  | vedor    |---->|  (trusted)  |---->|  (final)   |              |
|  +----------+     +------+------+     +------------+              |
|                         |                                        |
|                    +----+----+                                    |
|                    |  Build  |                                    |
|                    | Pipeline|                                    |
|                    +----+----+                                    |
|                         |                                        |
|                    +----+----+     +------------+                 |
|                    |Dependenc.|---->| Outros     |                 |
|                    | (Nivel 2)|     | Desenvolv. |                 |
|                    +----+----+     +------------+                 |
|                         |                                        |
|                    +----+----+     +------------+                 |
|                    |Dependenc.|---->| Outros     |                 |
|                    | (Nivel 3)|     | Desenvolv. |                 |
|                    +---------+     +------------+                 |
|                                                                   |
|  PROBLEMA: Cada nivel adiciona risco. O usuario final nao tem    |
|  visibilidade sobre os niveis inferiores da cadeia.               |
|                                                                   |
+-------------------------------------------------------------------+
```

---

## 11.2 Modelo de Confiança de Plugins

O modelo de confiança de plugins define as relações de confiança entre todos os participantes do ecossistema: desenvolvedores, distribuidores, host (aplicação que carrega o plugin) e usuários finais. Um modelo de confiança bem desenhado é a base para qualquer sistema seguro de plugins.

### 11.2.1 Limites de Confiança em Sistemas de Plugins Wasm

Limites de confiança (trust boundaries) são pontos onde o nível de confiança muda. Em sistemas de plugins Wasm, os principais limites incluem:

**Desenvolvedor <-> Marketplace**: O marketplace precisa verificar a identidade do desenvolvedor e a integridade do plugin publicado. Isso inclui autenticação, autorização e verificação de assinatura.

**Marketplace <-> Host**: O host precisa verificar a integridade e autenticidade do plugin baixado do marketplace. Isso requer verificação de assinatura e hash.

**Host <-> Plugin**: O host executa o plugin em um sandbox, mas precisa confiar que o plugin respeita as APIs e permissões declaradas. O sandbox do Wasm fornece isolamento, mas não elimina a necessidade de verificação.

**Plugin <-> Outros Plugins**: Se múltiplos plugins interagem, cada um precisa confiar minimamente nos outros. O Component Model fornece interfaces tipadas que ajudam a isolar plugins.

```text
+-------------------------------------------------------------------+
|                 Limites de Confianca (Trust Boundaries)            |
+-------------------------------------------------------------------+
|                                                                   |
|  [Desenvolvedor]                                                  |
|       |                                                           |
|       v  (Boundary 1: autenticacao + assinatura)                  |
|  +----+----+                                                      |
|  |Marketplace|                                                    |
|  +----+----+                                                      |
|       |                                                           |
|       v  (Boundary 2: download + verificacao de hash)             |
|  +----+----+                                                      |
|  |   Host    |                                                    |
|  |  (App)    |                                                    |
|  +----+----+                                                      |
|       |                                                           |
|       v  (Boundary 3: sandbox + WASI capabilities)                |
|  +----+----+    +----+----+                                       |
|  | Plugin A  |--->| Plugin B|  (se interacao permitida)           |
|  +----------+    +----------+                                     |
|                                                                   |
|  Cada boundary requer seu proprio mecanismo de verificacao.       |
|  A falha em qualquer boundary pode comprometer todo o sistema.    |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.2.2 Relação de Confiança Host-Plugin

A relação entre o host (aplicação que carrega plugins) e o plugin é fundamental para a segurança. O host deve assumir que todo plugin é potencialmente malicioso e implementar defesas em profundidade:

**Verificação pré-execução**: Antes de carregar o plugin, o host deve verificar:
- Assinatura criptográfica do plugin
- Hash de integridade
- Versão e metadados
- Permissões WASI solicitadas
- Atestações de build e proveniência

**Restrição durante execução**: Durante a execução, o host deve:
- Conceder apenas as permissões WASI estritamente necessárias
- Monitorar comportamento do plugin
- Impor limites de recursos (CPU, memória, I/O)
- Implementar timeout para operações

**Reação pós-execução**: Após a execução:
- Auditar logs de comportamento
- Verificar se o plugin acessou recursos não autorizados
- Atualizar políticas de confiança baseado no comportamento

```rust
// Exemplo de configuração de confiança host-plugin em Rust
// Usando Wasmtime como runtime

use wasmtime::*;
use wasmtime_wasi::WasiCtxBuilder;

fn configure_plugin_trust(engine: &Engine) -> Result<Module> {
    // Carregar módulo Wasm do disco
    let wasm_bytes = std::fs::read("plugin.wasm")?;
    
    // Verificar assinatura antes de compilar
    verify_plugin_signature(&wasm_bytes)?;
    
    // Verificar hash de integridade
    verify_plugin_integrity(&wasm_bytes, "expected_hash_sha256")?;
    
    // Compilar o módulo
    let module = Module::new(engine, &wasm_bytes)?;
    
    // Verificar permissões WASI solicitadas
    let requested_caps = extract_wasi_capabilities(&module)?;
    validate_capabilities(&requested_caps)?;
    
    Ok(module)
}

fn validate_capabilities(caps: &WasiCapabilities) -> Result<()> {
    // Apenas capacidades explicitamente permitidas
    let allowed = AllowedCapabilities {
        filesystem: Some(vec!["/tmp/plugin-data".to_string()]),
        networking: false,
        environment_variables: Some(vec!["PLUGIN_ID".to_string()]),
        clocks: false,
    };
    
    if caps.filesystem.contains(&"/etc".to_string()) {
        return Err(anyhow!("Acesso a /etc nao permitido"));
    }
    
    if caps.networking && !allowed.networking {
        return Err(anyhow!("Acesso a rede nao permitido"));
    }
    
    Ok(())
}
```

### 11.2.3 Limites de Confiança Plugin-Plugin

Quando múltiplos plugins interagem dentro de um host, é necessário definir limites de confiança entre eles. O Component Model do Wasm fornece uma base para isso:

**Interfaces tipadas**: Cada componente declara explicitamente as interfaces que expõe e consome, permitindo verificação estática de compatibilidade.

**Isolamento de memória**: Componentes não compartilham memória linear, impedindo que um plugin acesse a memória de outro.

**WASI capability-based**: Cada componente pode ter seu próprio conjunto de permissões WASI, evitando que um plugin malicioso Use permissões concedidas a outro.

**Limitação de interação**: O host pode mediar todas as interações entre plugins, implementando firewall entre componentes.

```text
+-------------------------------------------------------------------+
|             Isolamento entre Plugins via Component Model           |
+-------------------------------------------------------------------+
|                                                                   |
|  +-----------+          +-----------+                              |
|  | Plugin A  |          | Plugin B  |                              |
|  |           |          |           |                              |
|  | [WASI:    |          | [WASI:    |                              |
|  |  fs-read, |          |  net,     |                              |
|  |  fs-write]|          |  env]     |                              |
|  +-----+-----+          +-----+-----+                             |
|        |                      |                                    |
|        |    +---------+      |                                    |
|        +--->|  Host   |<-----+                                    |
|             | (Media) |                                            |
|             +----+----+                                            |
|                  |                                                 |
|             +----+----+                                            |
|             | Guest   |                                            |
|             | Wasm    |                                            |
|             | Sandbox |                                            |
|             +---------+                                            |
|                                                                   |
|  Cada plugin so ve suas proprias permissoes.                      |
|  O host media toda interacao entre plugins.                       |
|  Memoria e isolada por componente.                                |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.2.4 Modelo de Confiança Usuário-Plugin

O usuário final precisa confiar que o plugin que está instalando é legítimo e seguro. Isso requer:

**Transparência**: O usuário deve ter acesso a informações sobre:
- Autor do plugin e histórico de publicações
- Permissões solicitadas pelo plugin
- Dependências de terceiros
- Histórico de vulnerabilidades e correções
- Avaliações e reviews da comunidade

**Controle granular**: O usuário deve poder:
- Conceder ou negar permissões específicas
- Definir limites de recursos
- Exigir atualizações apenas de fontes verificadas
- Revogar acesso a qualquer momento

**Auditoria**: O usuário deve poder:
- Monitorar comportamento do plugin em tempo real
- Revisar logs de acesso a recursos
- Verificar se o plugin está遵守 as permissões declaradas

### 11.2.5 Confiança Baseada em Capacidades (WASI Permissions)

O modelo de permissões WASI implementa confiança baseada em capacidades (capability-based trust), onde cada plugin recebe apenas as capacidades necessárias para sua função:

```text
+-------------------------------------------------------------------+
|         Confianca Baseada em Capacidades (WASI)                   |
+-------------------------------------------------------------------+
|                                                                   |
|  Capacidade              Permissoes                               |
|  ---------------------------------------------------------------  |
|  wasi:filesystem         Leitura/escrita em caminhos especificos |
|  wasi:sockets            Conexao em hosts/portas especificos     |
|  wasi:environment        Acesso a variaveis de ambiente           |
|  wasi:clocks             Acesso a relogios monotonicos/wall       |
|  wasi:random             Geracao de numeros aleatorios            |
|  wasi:process            Spawn de processos filhos                |
|  wasi:preopens           Diretorios pre-abertos                   |
|                                                                   |
|  Princípio: MENOR PRIVILÉGIO POSSÍVEL                            |
|  - Cada plugin recebe APENAS as capacidades que precisa           |
|  - Capacidades sao explicitamente documentadas                    |
|  - Capacidades podem ser revogadas                                |
|  - Composicao de capacidades e auditavel                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.2.6 Arquitetura de Confiança Zero para Plugins

Zero-trust para plugins significa que NENHUM plugin é confiável por padrão. Todo plugin deve ser verificado continuamente:

```rust
// Arquitetura zero-trust para plugins Wasm
// Cada verificacao e independente e reavaliada continuamente

struct ZeroTrustPluginManager {
    verification_policies: Vec<Box<dyn VerificationPolicy>>,
    behavioral_monitors: Vec<Box<dyn BehavioralMonitor>>,
    runtime_enforcers: Vec<Box<dyn RuntimeEnforcer>>,
    audit_logger: Box<dyn AuditLogger>,
}

impl ZeroTrustPluginManager {
    fn new() -> Self {
        Self {
            verification_policies: vec![
                Box::new(SignatureVerification::new()),
                Box::new(HashVerification::new()),
                Box::new(CapabilityVerification::new()),
                Box::new(ProvenanceVerification::new()),
                Box::new(ReputationVerification::new()),
            ],
            behavioral_monitors: vec![
                Box::new(ResourceUsageMonitor::new()),
                Box::new(SyscallMonitor::new()),
                Box::new(NetworkAccessMonitor::new()),
            ],
            runtime_enforcers: vec![
                Box::new(ResourceLimiter::new()),
                Box::new(SyscallFilter::new()),
                Box::new(NetworkPolicy::new()),
            ],
            audit_logger: Box::new(AuditLogger::new()),
        }
    }
    
    async fn load_plugin(&self, plugin_bytes: &[u8]) -> Result<PluginInstance> {
        // Fase 1: Verificacao estatica (pre-execucao)
        for policy in &self.verification_policies {
            policy.verify(plugin_bytes)?;
            self.audit_logger.log_verification(
                policy.name(),
                "passed",
                plugin_bytes,
            );
        }
        
        // Fase 2: Configurar monitores de comportamento
        let monitors: Vec<_> = self.behavioral_monitors
            .iter()
            .map(|m| m.create_monitor(plugin_bytes))
            .collect();
        
        // Fase 3: Configurar restricoes de runtime
        let enforcers: Vec<_> = self.runtime_enforcers
            .iter()
            .map(|e| e.create_enforcer(plugin_bytes))
            .collect();
        
        // Fase 4: Carregar e executar com supervision
        let instance = PluginInstance::new(
            plugin_bytes,
            monitors,
            enforcers,
        )?;
        
        self.audit_logger.log_plugin_loaded(
            instance.id(),
            instance.capabilities(),
        );
        
        Ok(instance)
    }
    
    async fn monitor_plugin(
        &self,
        instance: &PluginInstance,
    ) -> Result<()> {
        // Verificacao continua durante execucao
        loop {
            for monitor in &self.behavioral_monitors {
                if let Some(violation) = monitor.check(instance)? {
                    self.audit_logger.log_violation(
                        instance.id(),
                        &violation,
                    );
                    
                    // Reacao imediata a violacoes
                    match violation.severity {
                        Severity::Critical => {
                            instance.terminate();
                            return Err(anyhow!(
                                "Plugin terminado por violacao critica"
                            ));
                        }
                        Severity::High => {
                            instance.revoke_capability(
                                violation.capability,
                            );
                        }
                        Severity::Medium | Severity::Low => {
                            // Log e continuar
                        }
                    }
                }
            }
            
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }
}
```

### 11.2.7 Cadeia de Confiança do Desenvolvedor ao Usuário Final

A cadeia de confiança completa do desenvolvedor ao usuário final inclui múltiplos passos, cada um com seu próprio mecanismo de verificação:

```text
+-------------------------------------------------------------------+
|        Cadeia de Confianca Completa: Dev -> Usuario                |
+-------------------------------------------------------------------+
|                                                                   |
|  1. DESENVOLVEDOR                                                 |
|     +-- Identidade verificada (GPG key, email confirmado)         |
|     +-- Ambiente de build auditado (hermetic build)               |
|     +-- Codigo-fonte versionado (git signed commits)              |
|     |                                                             |
|     v                                                             |
|  2. BUILD PIPELINE                                                |
|     +-- Pipeline reprodutivel (deterministic build)               |
|     +-- Artefatos assinados (cosign, sigstore)                    |
|     +-- Atestacao de proveniencia (in-toto)                       |
|     +-- SBOM gerado                                               |
|     |                                                             |
|     v                                                             |
|  3. REGISTRY / MARKETPLACE                                        |
|     +-- Verificacao de identidade do publicador                   |
|     +-- Escaneamento de vulnerabilidades automatico               |
|     +-- Review de politicas de permissao                          |
|     +-- Registro em log de transparencia (rekor)                   |
|     |                                                             |
|     v                                                             |
|  4. DISTRIBUICAO                                                  |
|     +-- Transporte criptografado (TLS)                            |
|     +-- Verificacao de integridade no download                    |
|     +-- Mirror verification (se aplicavel)                        |
|     |                                                             |
|     v                                                             |
|  5. INSTALACAO NO HOST                                            |
|     +-- Verificacao de assinatura contra chave publica            |
|     +-- Verificacao de hash contra valor esperado                 |
|     +-- Verificacao de atestacao de build                         |
|     +-- Verificacao de SBOM contra vulnerabilidades               |
|     |                                                             |
|     v                                                             |
|  6. EXECUCAO                                                      |
|     +-- Permissoes WASI restritas                                 |
|     +-- Monitoramento de comportamento                            |
|     +-- Limites de recursos impostos                              |
|     +-- Auditoria continua                                        |
|     |                                                             |
|     v                                                             |
|  7. USUARIO FINAL                                                 |
|     +-- Visibilidade sobre permissoes do plugin                   |
|     +-- Controle sobre concessao de permissoes                    |
|     +-- Capacidade de revogar acesso                              |
|     +-- Relatorios de comportamento                               |
|                                                                   |
+-------------------------------------------------------------------+
```

---

## 11.3 Assinatura de Código com Cosign e Sigstore

Assinatura de código é o processo de vincular uma assinatura criptográfica a um artefato de software, permitindo que qualquer pessoa verifique a autenticidade e integridade do artefato. No contexto de plugins Wasm, a assinatura de código é uma camada fundamental de segurança.

### 11.3.1 Introdução à Assinatura de Código

Assinatura de código resolve três problemas fundamentais:

**Autenticidade**: Quem criou este artefato? A assinatura vincula o artefato a uma chave pública específica, que por sua vez pode ser vinculada a uma identidade (pessoa ou organização).

**Integridade**: O artefato foi alterado desde que foi assinado? A assinatura criptográfica garante que qualquer modificação no artefato será detectada.

**Não-repúdio**: O autor pode provar que assinou o artefato. A assinatura serve como evidência criptográfica de autoria.

O fluxo básico de assinatura e verificação é:

```text
+-------------------------------------------------------------------+
|               Fluxo de Assinatura e Verificacao                    |
+-------------------------------------------------------------------+
|                                                                   |
|  ASSINATURA:                                                      |
|  +------------+    +-----------+    +------------+                 |
|  | Artefato   |--->|  Hash     |--->|  Assina    |                 |
|  | (plugin.w  |    | (SHA-256) |    | (chave     |                 |
|  |   asm)     |    +-----------+    |  privada)  |                 |
|  +------------+                     +-----+------+                 |
|                                      |                            |
|                                      v                            |
|                              +-------+--------+                   |
|                              | plugin.wasm    |                   |
|                              | + signature    |                   |
|                              +----------------+                   |
|                                                                   |
|  VERIFICACAO:                                                     |
|  +------------+    +-----------+    +------------+                 |
|  | Artefato   |--->|  Hash     |--->| Verifica   |                 |
|  | + assinat. |    | (SHA-256) |    | (chave     |                 |
|  |            |    +-----------+    |  publica)  |                 |
|  +------------+                     +-----+------+                 |
|                                      |                            |
|                                      v                            |
|                              +-------+--------+                   |
|                              | VALIDO /       |                   |
|                              | INVALIDO       |                   |
|                              +----------------+                   |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.3.2 Cosign: Arquitetura e Uso

Cosign é uma ferramenta da Projeto Sigstore para assinatura e verificação de artefatos de software. Originalmente projetado para imagens de container, foi expandido para suportar qualquer tipo de artefato, incluindo módulos Wasm.

**Arquitetura do Cosign**:

```text
+-------------------------------------------------------------------+
|                  Arquitetura do Cosign                              |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+                                             |
|  |     cosign       |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|     +-----+------+                                                |
|     |            |                                                |
|     v            v                                                |
|  +------+   +--------+                                            |
|  |Sign  |   |Verify  |                                            |
|  |      |   |        |                                            |
|  +--+---+   +---+----+                                            |
|     |           |                                                  |
|     v           v                                                  |
|  +------+   +--------+    +------------+                          |
|  |Fulcio|   |Rekor   |    |OCI Registry|                          |
|  |(cert) |   |(transp)|    |            |                          |
|  +------+   +--------+    +------------+                          |
|                                                                   |
|  Componentes:                                                     |
|  - Fulcio: Emite certificados de curta duracao                    |
|  - Rekor: Log de transparencia imutavel                           |
|  - OCI Registry: Armazena assinaturas como OCI artifacts          |
|  - cosign: CLI principal para assinatura/verificacao              |
|                                                                   |
+-------------------------------------------------------------------+
```

**Instalação do Cosign**:

```bash
# Instalar cosign via binario pre-compilado
wget https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# Ou via go install
go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# Verificar instalacao
cosign version

# Instalar via npm (para integracao em pipelines)
npm install -g @sigstore/cosign
```

### 11.3.3 Assinatura Keyless com Sigstore/Fulcio

O modelo keyless do Sigstore/Fulcio elimina a necessidade de gerenciar chaves criptográficas de longa duração. Em vez disso, o Fulcio emite certificados de curta duração baseados em identidade (email, OIDC token):

```text
+-------------------------------------------------------------------+
|           Assinatura Keyless com Fulcio                             |
+-------------------------------------------------------------------+
|                                                                   |
|  1. O desenvolvedor autentica com um OIDC provider                |
|     (GitHub, Google, GitLab, etc.)                                 |
|                                                                   |
|  2. O Fulcio emite um certificado X.509 de curta duracao          |
|     (10 minutos) vinculado a identidade OIDC                      |
|                                                                   |
|  3. O artefato e assinado com a chave privada temporaria          |
|                                                                   |
|  4. A assinatura e registrada no Rekor transparency log           |
|                                                                   |
|  5. O certificado expira, mas a verificacao continua              |
|     funcional via Rekor                                            |
|                                                                   |
|  VANTAGENS:                                                       |
|  - Nenhuma chave para gerenciar ou proteger                       |
|  - Identidade verificada por OIDC provider confiavel              |
|  - Transparencia via log imutavel                                 |
|  - Certificados de curta duracao reduzem risco de roubo           |
|                                                                   |
+-------------------------------------------------------------------+
```

**Fluxo de assinatura keyless**:

```bash
# Assinatura keyless com Fulcio/Rekor
# O cosign detecta automaticamente o OIDC provider

# GitHub Actions (automatico)
cosign sign-blob \
    --bundle plugin.wasm.bundle \
    plugin.wasm

# Manualmente com Google OIDC
export OIDC_TOKEN=$(gcloud auth print-identity-token \
    --audiences=sigstore \
    --include-email)

cosign sign-blob \
    --oidc-issuer="https://accounts.google.com" \
    --oidc-identity-token="$OIDC_TOKEN" \
    --bundle plugin.wasm.bundle \
    plugin.wasm
```

### 11.3.4 Log de Transparência Rekor

O Rekor é um log de transparencia imutável que registra todas as assinaturas de artefatos. Ele fornece evidência criptográfica de que um artefato foi assinado em um determinado momento por uma determinada identidade.

**Propriedades do Rekor**:

- **Imutabilidade**: Entradas não podem ser alteradas ou removidas após inserção.
- **Auditoria pública**: Qualquer pessoa pode verificar a integridade do log.
- **Timestamping**: Cada entrada é temporalmente ordenada.
- **Inclusividade**: O log prova que uma entrada específica foi incluída.

```bash
# Verificar uma entrada no Rekor
cosign verify-blob \
    --bundle plugin.wasm.bundle \
    --certificate-identity="developer@example.com" \
    --certificate-oidc-issuer="https://accounts.google.com" \
    plugin.wasm

# Buscar entrada no Rekor por hash
rekor-cli search --hash "$(sha256sum plugin.wasm | cut -d' ' -f1)"

# Verificar integridade do log
rekor-cli verify --rekor_server https://rekor.sigstore.dev \
    --uuid=<entry-uuid>
```

**Formato de entrada do Rekor**:

```json
{
  "apiVersion": "0.0.1",
  "kind": "hashedrekord",
  "metadata": {
    "createdAt": "2024-01-15T10:30:00Z"
  },
  "spec": {
    "data": {
      "hash": {
        "algorithm": "sha256",
        "value": "a1b2c3d4e5f6..."
      }
    },
    "signature": {
      "content": "MEUCIQD...",
      "publicKey": {
        "content": "LS0tLS1C..."
      }
    }
  }
}
```

### 11.3.5 Assinatura de Módulos Wasm Passo a Passo

**Passo 1: Preparar o ambiente**

```bash
# Configurar ambiente para assinatura
export COSIGN_YES=true
export COSIGN_EXPERIMENTAL=1  # Para assinatura keyless

# Verificar se cosign esta configurado corretamente
cosign version
```

**Passo 2: Compilar o plugin Wasm**

```bash
# Compilar plugin em Rust para Wasm
cargo build --target wasm32-wasi --release

# Obinario resultante esta em target/wasm32-wasi/release/plugin.wasm
ls -la target/wasm32-wasi/release/plugin.wasm

# Verificar informacoes do modulo Wasm
wasm-tools target metadata target/wasm32-wasi/release/plugin.wasm
```

**Passo 3: Assinar o módulo**

```bash
# Assinar com cosign keyless
cosign sign-blob \
    --bundle plugin.wasm.bundle \
    target/wasm32-wasi/release/plugin.wasm

# Output esperado:
# Uploading to rekor.sigstore.dev
# ...
# Signed OK
# Bundle written to plugin.wasm.bundle
```

**Passo 4: Verificar a assinatura**

```bash
# Verificar assinatura
cosign verify-blob \
    --bundle plugin.wasm.bundle \
    --certificate-identity="developer@company.com" \
    --certificate-oidc-issuer="https://github.com/login" \
    target/wasm32-wasi/release/plugin.wasm

# Output esperado:
# Verified OK
```

### 11.3.6 Gerenciamento de Chaves

Para cenários onde a assinatura keyless não é adequada (ex: sistemas offline, organizações com PKI própria), o cosign suporta chaves de longa duração:

```bash
# Gerar par de chaves cosign
cosign generate-key-pair

# Isso cria:
# cosign.key (chave privada)
# cosign.pub (chave publica)

# Proteger a chave privada com senha
# (o cosign pede senha interativamente)

# Assinar com chave privada
cosign sign-blob \
    --key cosign.key \
    --bundle plugin.wasm.bundle \
    target/wasm32-wasi/release/plugin.wasm

# Verificar com chave publica
cosign verify-blob \
    --key cosign.pub \
    --bundle plugin.wasm.bundle \
    target/wasm32-wasi/release/plugin.wasm
```

**Estratégias de gerenciamento de chaves**:

```text
+-------------------------------------------------------------------+
|          Estrategias de Gerenciamento de Chaves                    |
+-------------------------------------------------------------------+
|                                                                   |
|  1. Chaves de Curta Duracao (Fulcio/Sigstore)                     |
|     - Certificados expiram em minutos                             |
|     - Nenhuma chave para gerenciar                                |
|     - Identidade verificada via OIDC                              |
|     - IDEAL para maioria dos casos                                |
|                                                                   |
|  2. HSM (Hardware Security Module)                                |
|     - Chaves nunca saem do hardware                               |
|     - Protecao contra extracao                                    |
|     - Custo significativo                                         |
|     - IDEAL para organizacoes grandes                             |
|                                                                   |
|  3. KMS (Key Management Service)                                  |
|     - Chaves gerenciadas por servico cloud                        |
|     - Integracao com IAM                                          |
|     - Audit logging automatico                                    |
|     - IDEAL para cloud-native                                     |
|                                                                   |
|  4. Chaves Locais (cosign.key)                                    |
|     - Chave armazenada localmente                                 |
|     - Facil de usar                                               |
|     - Risco de roubo/extracao                                     |
|     - IDEAL para desenvolvimento                                  |
|                                                                   |
|  5. Threshold Signatures                                         |
|     - Requer N de M assinaturas                                   |
|     - Distribuicao de confianca                                   |
|     - Complexidade adicional                                      |
|     - IDEAL para governanca critica                               |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.3.7 Fluxo Completo de Assinatura com Cosign

```bash
#!/bin/bash
# Fluxo completo de assinatura para plugins Wasm
# Este script deve ser executado no pipeline de build

set -euo pipefail

PLUGIN_NAME="my-plugin"
WASM_FILE="target/wasm32-wasi/release/${PLUGIN_NAME}.wasm"
BUNDLE_FILE="${PLUGIN_NAME}.wasm.bundle"
MANIFEST_FILE="${PLUGIN_NAME}.manifest.json"

echo "=== Etapa 1: Compilar o plugin ==="
cargo build --target wasm32-wasi --release
echo "Build concluido: ${WASM_FILE}"

echo "=== Etapa 2: Gerar hash de integridade ==="
HASH_SHA256=$(sha256sum "${WASM_FILE}" | cut -d' ' -f1)
HASH_BLAKE3=$(b3sum "${WASM_FILE}" | cut -d' ' -f1)
echo "SHA-256: ${HASH_SHA256}"
echo "BLAKE3: ${HASH_BLAKE3}"

echo "=== Etapa 3: Gerar SBOM ==="
syft "${WASM_FILE}" -o spdx-json > "${PLUGIN_NAME}.sbom.json"
echo "SBOM gerado"

echo "=== Etapa 4: Assinar o plugin ==="
cosign sign-blob \
    --bundle "${BUNDLE_FILE}" \
    "${WASM_FILE}"
echo "Assinatura concluida: ${BUNDLE_FILE}"

echo "=== Etapa 5: Verificar a assinatura ==="
cosign verify-blob \
    --bundle "${BUNDLE_FILE}" \
    --certificate-identity="${GITHUB_ACTOR}@users.noreply.github.com" \
    --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
    "${WASM_FILE}"
echo "Verificacao concluida com sucesso"

echo "=== Etapa 6: Criar manifest ==="
cat > "${MANIFEST_FILE}" << EOF
{
  "name": "${PLUGIN_NAME}",
  "version": "$(cargo metadata --format-version 1 | jq -r '.packages[0].version')",
  "hashes": {
    "sha256": "${HASH_SHA256}",
    "blake3": "${HASH_BLAKE3}"
  },
  "signature_bundle": "${BUNDLE_FILE}",
  "sbom": "${PLUGIN_NAME}.sbom.json",
  "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "built_by": "${GITHUB_ACTOR}",
  "workflow": "${GITHUB_WORKFLOW}",
  "repository": "${GITHUB_REPOSITORY}",
  "commit": "${GITHUB_SHA}"
}
EOF
echo "Manifest criado: ${MANIFEST_FILE}"

echo "=== Fluxo completo finalizado ==="
```

### 11.3.8 Integração Sigstore com CI/CD

**GitHub Actions**:

```yaml
# .github/workflows/sign-plugin.yml
name: Sign Wasm Plugin

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read
  id-token: write  # Necessario para OIDC

jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Rust toolchain
        uses: actions-rust-lang/setup-rust-toolchain@v1
        with:
          targets: wasm32-wasi
      
      - name: Build plugin
        run: cargo build --target wasm32-wasi --release
      
      - name: Install cosign
        uses: sigstore/cosign-installer@v3
      
      - name: Install syft (SBOM)
        uses: anchore/sbom-action/download-syft@v0
      
      - name: Generate SBOM
        run: syft ./target/wasm32-wasi/release/plugin.wasm \
             -o spdx-json > plugin.sbom.json
      
      - name: Sign plugin
        run: cosign sign-blob \
             --bundle plugin.wasm.bundle \
             ./target/wasm32-wasi/release/plugin.wasm
        env:
          COSIGN_YES: "true"
      
      - name: Verify signature
        run: cosign verify-blob \
             --bundle plugin.wasm.bundle \
             --certificate-identity="${{ github.actor }}@users.noreply.github.com" \
             --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
             ./target/wasm32-wasi/release/plugin.wasm
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: signed-plugin
          path: |
            target/wasm32-wasi/release/plugin.wasm
            plugin.wasm.bundle
            plugin.sbom.json
```

---

## 11.4 Verificação de Módulos

Verificação de módulos é o processo de confirmar que um módulo Wasm é autêntico, íntegro e não foi adulterado. Isso envolve múltiplas técnicas, desde verificação de hash simples até infraestrutura de chaves públicas completa.

### 11.4.1 Verificação Criptográfica de Módulos Wasm

A verificação criptográfica usa primitivas criptográficas para garantir integridade e autenticidade:

**Assinatura digital**: O autor assina o módulo com sua chave privada. Qualquer pessoa com a chave pública pode verificar que o módulo foi assinado pelo autor.

**HMAC**: Usado quando autor e verificador compartilham um segredo. Útil para comunicação entre sistemas controlados pela mesma organização.

**Commitments**: O autor publica um hash do módulo antes da distribuição. Isso permite verificação posterior sem expor o módulo antecipadamente.

```rust
// Verificacao criptографica de modulo Wasm
use sha2::{Sha256, Digest};
use ed25519_dalek::{VerifyingKey, VerifyingKey, Signature};

fn verify_wasm_module(
    module_bytes: &[u8],
    expected_hash: &[u8; 32],
    public_key: &VerifyingKey,
    signature: &Signature,
) -> Result<bool, VerificationError> {
    // 1. Verificar hash de integridade
    let computed_hash = Sha256::digest(module_bytes);
    if computed_hash.as_slice() != expected_hash {
        return Err(VerificationError::HashMismatch {
            expected: *expected_hash,
            computed: computed_hash.into(),
        });
    }
    
    // 2. Verificar assinatura digital
    match public_key.verify(module_bytes, signature) {
        Ok(_) => Ok(true),
        Err(_) => Err(VerificationError::InvalidSignature),
    }
}

#[derive(Debug)]
enum VerificationError {
    HashMismatch { expected: [u8; 32], computed: [u8; 32] },
    InvalidSignature,
    ExpiredCertificate,
    RevokedKey,
}
```

### 11.4.2 Verificação Baseada em Hash (SHA-256, BLAKE3)

Hashes são a forma mais básica e mais eficiente de verificação de integridade. Um hash é um resumo criptográfico do conteúdo que muda completamente se qualquer byte do conteúdo for alterado.

**SHA-256**: Algoritmo amplamente utilizado, padronizado pelo NIST. Produz um hash de 256 bits (32 bytes).

**BLAKE3**: Algoritmo mais rápido que SHA-256, com suporte a hashing paralelo. Produz hash de 256 bits. Cada vez mais adotado em ferramentas de build.

```bash
# Gerar e verificar hashes
# SHA-256
sha256sum plugin.wasm
# Output: a1b2c3d4e5f6...  plugin.wasm

# BLAKE3
b3sum plugin.wasm
# Output: f6e5d4c3b2a1...  plugin.wasm

# Verificar hash contra valor esperado
echo "a1b2c3d4e5f6...  plugin.wasm" | sha256sum -c
# Output: plugin.wasm: OK
```

**Comparação de algoritmos**:

```text
+-------------------------------------------------------------------+
|           Comparacao de Algoritmos de Hash                         |
+-------------------------------------------------------------------+
|                                                                   |
|  Algoritmo  | Tamanho | Velocidade  | Seguranca | Uso Recomendado  |
|  -----------+---------+-------------+-----------+----------------- |
|  SHA-256    | 256 bit | ~600 MB/s   | Alta      | Compatibilidade |
|  SHA-512    | 512 bit | ~800 MB/s   | Muito alta| Documentacao    |
|  BLAKE3     | 256 bit | ~3 GB/s     | Alta      | Performance     |
|  SHA-3      | Variavel| ~400 MB/s   | Muito alta| FIPS compliance |
|  MD5        | 128 bit | ~700 MB/s   | BAIXA     | NAO USAR        |
|                                                                   |
|  RECOMENDACAO:                                                   |
|  - SHA-256 para compatibilidade maxima                           |
|  - BLAKE3 para performance                                       |
|  - Usar AMBOS quando possivel (defense in depth)                  |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.4.3 Infraestrutura de Chaves Públicas para Wasm

Uma PKI (Public Key Infrastructure) para módulos Wasm gerencia chaves públicas, certificados e CAs (Certificate Authorities) para verificar identidade:

```text
+-------------------------------------------------------------------+
|              PKI para Modulos Wasm                                  |
+-------------------------------------------------------------------+
|                                                                   |
|  Root CA                                                          |
|  (Organizacao)                                                    |
|      |                                                            |
|      +-- Intermediate CA (Equipe de Seguranca)                    |
|      |       |                                                    |
|      |       +-- Certificado: Dev Team Lead                       |
|      |       +-- Certificado: Senior Developer A                  |
|      |       +-- Certificado: Senior Developer B                  |
|      |                                                            |
|      +-- Intermediate CA (CI/CD Pipeline)                         |
|              |                                                    |
|              +-- Certificado: GitHub Actions                      |
|              +-- Certificado: Jenkins Agent                       |
|              +-- Certificado: Build Server                        |
|                                                                   |
|  Fluxo:                                                           |
|  1. Desenvolvedor gera par de chaves                              |
|  2. Envia CSR (Certificate Signing Request) para CA               |
|  3. CA verifica identidade e emite certificado                    |
|  4. Desenvolvedor assina plugins com chave privada                |
|  5. Verificador usa certificado para validar assinatura           |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.4.4 Certificados X.509 para Assinatura de Módulos

Certificados X.509 são o padrão da indústria para vincular identidades a chaves públicas:

```bash
# Gerar chave privada e certificado auto-assinado
openssl ecparam -genkey -name prime256v1 -out plugin-signer.key
openssl req -new -x509 -key plugin-signer.key -out plugin-signer.crt \
    -days 365 -subj "/CN=Plugin Signer/O=My Company/C=BR"

# Assinar o módulo Wasm com a chave
openssl dgst -sha256 -sign plugin-signer.key \
    -out plugin.wasm.sig target/wasm32-wasi/release/plugin.wasm

# Verificar a assinatura
openssl dgst -sha256 -verify plugin-signer.crt \
    -signature plugin.wasm.sig target/wasm32-wasi/release/plugin.wasm
# Output: Verified OK
```

### 11.4.5 Formato de Manifest de Módulos Wasm

Um manifest documenta metadados essenciais para verificação:

```json
{
  "schema_version": "1.0.0",
  "module": {
    "name": "my-plugin",
    "version": "1.2.3",
    "description": "Plugin de processamento de dados",
    "author": {
      "name": "Developer Name",
      "email": "dev@company.com",
      "key_id": "SHA256:abcdef1234567890..."
    }
  },
  "integrity": {
    "sha256": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
    "blake3": "f6e5d4c3b2a10987654321fedcba9876543210fedcba9876543210fedcba9876"
  },
  "signature": {
    "algorithm": "ed25519",
    "key_id": "SHA256:abcdef1234567890...",
    "bundle_path": "plugin.wasm.bundle"
  },
  "build": {
    "toolchain": "rustc 1.75.0",
    "target": "wasm32-wasi",
    "profile": "release",
    "features": ["default"],
    "reproducible": true,
    "reproduction_command": "cargo build --target wasm32-wasi --release"
  },
  "wasi_capabilities": {
    "filesystem": ["/tmp/plugin-data"],
    "networking": false,
    "environment_variables": ["PLUGIN_CONFIG"],
    "clocks": false
  },
  "dependencies": [],
  "sbom": {
    "format": "spdx-json",
    "path": "plugin.sbom.json"
  },
  "attestation": {
    "provenance": "plugin.provenance.json",
    "build": "plugin.build.att.json"
  }
}
```

### 11.4.6 Verificação em Runtime

A verificação em runtime é a última defesa antes da execução do plugin:

```rust
// Verificacao completa em runtime
use sha2::{Sha256, Digest};
use serde::Deserialize;

#[derive(Deserialize)]
struct PluginManifest {
    module: ModuleInfo,
    integrity: IntegrityInfo,
    signature: Option<SignatureInfo>,
    wasi_capabilities: WasiCapabilities,
}

struct RuntimeVerifier {
    trusted_keys: Vec<VerifyingKey>,
    allowed_capabilities: WasiCapabilities,
    max_module_size: usize,
}

impl RuntimeVerifier {
    fn verify_plugin(
        &self,
        module_bytes: &[u8],
        manifest: &PluginManifest,
    ) -> Result<(), Vec<VerificationFailure>> {
        let mut failures = Vec::new();
        
        // 1. Verificar tamanho
        if module_bytes.len() > self.max_module_size {
            failures.push(VerificationFailure::ModuleTooLarge {
                size: module_bytes.len(),
                max: self.max_module_size,
            });
        }
        
        // 2. Verificar hash SHA-256
        let sha256 = Sha256::digest(module_bytes);
        if hex::encode(sha256) != manifest.integrity.sha256 {
            failures.push(VerificationFailure::HashMismatch {
                algorithm: "sha256".to_string(),
                expected: manifest.integrity.sha256.clone(),
                computed: hex::encode(sha256),
            });
        }
        
        // 3. Verificar assinatura
        if let Some(sig_info) = &manifest.signature {
            let sig_bytes = std::fs::read(&sig_info.bundle_path)?;
            let signature = Signature::from_bytes(&sig_bytes)?;
            
            let key = self.trusted_keys.iter()
                .find(|k| k.fingerprint() == sig_info.key_id)
                .ok_or(VerificationFailure::UnknownKey)?;
            
            if key.verify(module_bytes, &signature).is_err() {
                failures.push(VerificationFailure::InvalidSignature);
            }
        } else {
            failures.push(VerificationFailure::NoSignature);
        }
        
        // 4. Verificar permissoes WASI
        if !self.allowed_capabilities.superset_of(
            &manifest.wasi_capabilities
        ) {
            failures.push(VerificationFailure::UnauthorizedCapabilities);
        }
        
        if failures.is_empty() {
            Ok(())
        } else {
            Err(failures)
        }
    }
}

#[derive(Debug)]
enum VerificationFailure {
    ModuleTooLarge { size: usize, max: usize },
    HashMismatch { algorithm: String, expected: String, computed: String },
    InvalidSignature,
    NoSignature,
    UnknownKey,
    UnauthorizedCapabilities,
    ExpiredCertificate,
}
```

### 11.4.7 Política de Verificação Deny-by-Default

A política deny-by-default garante que apenas plugins explicitamente aprovados são carregados:

```rust
// Politica deny-by-default
struct DenyByDefaultPolicy {
    allowlist: HashSet<String>,  // hashes de plugins permitidos
    keyring: Keyring,           // chaves publicas confiaveis
    audit_log: AuditLog,
}

impl DenyByDefaultPolicy {
    fn should_load(&self, plugin: &Plugin) -> PolicyDecision {
        // Verificar se o plugin esta na allowlist
        let hash = plugin.compute_hash();
        
        if !self.allowlist.contains(&hash) {
            self.audit_log.record(Decision::Denied, plugin, 
                "Plugin nao esta na allowlist");
            return PolicyDecision::Deny(
                "Plugin nao esta na allowlist de plugins permitidos"
            );
        }
        
        // Verificar se a chave e confiavel
        if let Some(key_id) = plugin.signing_key_id() {
            if !self.keyring.is_trusted(&key_id) {
                self.audit_log.record(Decision::Denied, plugin,
                    "Chave de assinatura nao confiavel");
                return PolicyDecision::Deny(
                    "Chave de assinatura nao esta na keyring confiavel"
                );
            }
        }
        
        // Verificar se o manifesto e valido
        if let Some(manifest) = plugin.manifest() {
            if !self.validate_manifest(manifest) {
                self.audit_log.record(Decision::Denied, plugin,
                    "Manifesto invalido");
                return PolicyDecision::Deny("Manifesto invalido");
            }
        }
        
        self.audit_log.record(Decision::Allowed, plugin, "Todas as verificacoes passaram");
        PolicyDecision::Allow
    }
}

enum PolicyDecision {
    Allow,
    Deny(String),
    RequiresApproval(String),
}
```

### 11.4.8 Pipeline Completa de Verificação

```yaml
# Pipeline de verificacao completa (GitHub Actions)
name: Verify Plugin

on:
  pull_request:
    paths:
      - 'plugins/**'

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install verification tools
        run: |
          # cosign para verificacao de assinatura
          curl -sSfL https://raw.githubusercontent.com/sigstore/cosign/main/install.sh | sh -s --
          
          # syft para SBOM
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
          
          # grype para vulnerabilidades
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s --
      
      - name: Find Wasm plugins
        id: find-plugins
        run: |
          PLUGINS=$(find plugins/ -name "*.wasm" -type f)
          echo "plugins<<EOF" >> $GITHUB_OUTPUT
          echo "$PLUGINS" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
      
      - name: Verify each plugin
        run: |
          for PLUGIN in ${{ steps.find-plugins.outputs.plugins }}; do
            echo "=== Verificando: ${PLUGIN} ==="
            
            # 1. Verificar hash
            echo "Verificando hash..."
            if [ -f "${PLUGIN}.sha256" ]; then
              sha256sum -c "${PLUGIN}.sha256"
            else
              echo "AVISO: Arquivo de hash nao encontrado"
            fi
            
            # 2. Verificar assinatura
            echo "Verificando assinatura..."
            if [ -f "${PLUGIN}.bundle" ]; then
              cosign verify-blob \
                --bundle "${PLUGIN}.bundle" \
                --certificate-identity="${{ github.actor }}@users.noreply.github.com" \
                --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
                "${PLUGIN}"
            else
              echo "AVISO: Bundle de assinatura nao encontrado"
            fi
            
            # 3. Gerar e verificar SBOM
            echo "Gerando SBOM..."
            syft "${PLUGIN}" -o spdx-json > "${PLUGIN}.sbom.json"
            
            # 4. Verificar vulnerabilidades
            echo "Verificando vulnerabilidades..."
            grype "sbom:${PLUGIN}.sbom.json" --fail-on high
            
            echo "=== Verificacao concluida: ${PLUGIN} ==="
          done
```

---

## 11.5 Versionamento e Pinning

Versionamento e pinning são práticas essenciais para garantir que plugins sejam distribuídos e consumidos de forma previsível e segura. Sem versionamento adequado, sistemas podem ser expostos a versões maliciosas ou incompatíveis.

### 11.5.1 Versionamento Semântico para Plugins Wasm

Semantic Versioning (SemVer) fornece um padrão para comunicar mudanças em versões:

```text
+-------------------------------------------------------------------+
|              Semantic Versioning para Plugins Wasm                  |
+-------------------------------------------------------------------+
|                                                                   |
|  Formato: MAJOR.MINOR.PATCH                                       |
|                                                                   |
|  MAJOR: Mudancas incompativeis com versoes anteriores             |
|         Ex: v1.0.0 -> v2.0.0                                      |
|         - Mudanca na ABI do plugin                                 |
|         - Mudanca nas permissoes WASI                              |
|         - Remocao de funcionalidade                               |
|                                                                   |
|  MINOR: Funcionalidade nova, compativel com versoes anteriores    |
|         Ex: v1.0.0 -> v1.1.0                                      |
|         - Nova funcionalidade opcional                             |
|         - Novas permissoes WASI (opt-in)                          |
|         - Performance improvements                                |
|                                                                   |
|  PATCH: Correcao de bugs, compativel com versoes anteriores       |
|         Ex: v1.0.0 -> v1.0.1                                      |
|         - Correcao de vulnerabilidades                             |
|         - Correcao de comportamento incorreto                      |
|         - Documentacao                                            |
|                                                                   |
|  PRE-RELEASE:                                                      |
|         Ex: v1.0.0-alpha.1, v1.0.0-beta.2                        |
|         - Nao e considerado estavel                                |
|         - Pode conter bugs                                        |
|         - Nao deve ser usado em producao                          |
|                                                                   |
+-------------------------------------------------------------------+
```

```toml
# Cargo.toml - versionamento semantico em Rust
[package]
name = "my-plugin"
version = "1.2.3"  # MAJOR.MINOR.PATCH
edition = "2021"
description = "Plugin Wasm para processamento de dados"

# Metadados para o registry de plugins
[package.metadata.wasm-plugin]
min_host_version = "0.1.0"
wasi_capabilities = ["filesystem", "environment"]
target = "wasm32-wasi"
```

### 11.5.2 Lock Files e Builds Reprodutíveis

Lock files garantem que builds subsequentes produzam o mesmo resultado:

```toml
# Cargo.lock - pinning de dependencias
# Este arquivo e gerenciado automaticamente pelo Cargo

[[package]]
name = "my-plugin"
version = "1.2.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
dependencies = [
 "serde 1.0.193 (registry+https://github.com/rust-lang/crates.io-index)",
 "wasm-bindgen 0.2.89 (registry+https://github.com/rust-lang/crates.io-index)",
]

[[package]]
name = "serde"
version = "1.0.193"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "bb5e7b9e5d8eb15e23e8d8e9f0e2334d94d39b1e8f6c194e19f5d4b4e5c3f6d7"
```

**Configuração para builds reprodutíveis**:

```bash
# Configurar build reprodutivel para Wasm
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export CARGO_INCREMENTAL=0
export RUSTFLAGS="--remap-cfg-prefix_table=${SOURCE_DATE_EPOCH}"

# Compilar com profile release otimizado para reproducibilidade
cargo build --target wasm32-wasi --release

# Verificar que o binario e identico entre builds
sha256sum target/wasm32-wasi/release/plugin.wasm
```

### 11.5.3 Armazenamento Content-Addressable para Módulos

Content-addressable storage (CAS) usa o hash do conteúdo como identificador, garantindo que o mesmo conteúdo sempre produza o mesmo identificador:

```text
+-------------------------------------------------------------------+
|          Content-Addressable Storage para Plugins                  |
+-------------------------------------------------------------------+
|                                                                   |
|  hash(conteudo) -> endereco_unico                                 |
|                                                                   |
|  Exemplo:                                                         |
|  sha256:ab12cd34... -> /store/ab/12/cd/34/.../plugin.wasm        |
|  sha256:ef56gh78... -> /store/ef/56/gh/78/.../other.wasm         |
|                                                                   |
|  VANTAGENS:                                                       |
|  - Deduplicacao automatica                                       |
|  - Verificacao de integridade implicita                           |
|  - Cache eficiente                                               |
|  - Imutabilidade por construcao                                  |
|                                                                   |
|  IMPLEMENTACAO:                                                   |
|  - IPFS (InterPlanetary File System)                             |
|  - Nix store                                                     |
|  - Git LFS                                                       |
|  - OCI registry (com content digest)                             |
|  - Custom storage com SHA-256                                    |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Implementacao simples de CAS para plugins Wasm
use sha2::{Sha256, Digest};
use std::path::PathBuf;

struct PluginStore {
    base_path: PathBuf,
}

impl PluginStore {
    fn new(base_path: PathBuf) -> Self {
        Self { base_path }
    }
    
    fn store(&self, plugin_bytes: &[u8]) -> Result<String, StoreError> {
        let hash = Sha256::digest(plugin_bytes);
        let hash_hex = hex::encode(hash);
        
        // Criar estrutura de diretorio baseada no hash
        let dir = self.base_path
            .join(&hash_hex[0..2])
            .join(&hash_hex[2..4]);
        
        std::fs::create_dir_all(&dir)?;
        
        let file_path = dir.join(&hash_hex);
        
        // Verificar se ja existe (deduplicacao)
        if file_path.exists() {
            return Ok(hash_hex);
        }
        
        // Armazenar o plugin
        std::fs::write(&file_path, plugin_bytes)?;
        
        Ok(hash_hex)
    }
    
    fn retrieve(&self, hash: &str) -> Result<Vec<u8>, StoreError> {
        let dir = self.base_path
            .join(&hash[0..2])
            .join(&hash[2..4]);
        
        let file_path = dir.join(hash);
        
        if !file_path.exists() {
            return Err(StoreError::NotFound(hash.to_string()));
        }
        
        let bytes = std::fs::read(&file_path)?;
        
        // Verificar integridade
        let computed_hash = Sha256::digest(&bytes);
        if hex::encode(computed_hash) != hash {
            std::fs::remove_file(&file_path)?;
            return Err(StoreError::IntegrityFailure(hash.to_string()));
        }
        
        Ok(bytes)
    }
    
    fn exists(&self, hash: &str) -> bool {
        let dir = self.base_path
            .join(&hash[0..2])
            .join(&hash[2..4]);
        dir.join(hash).exists()
    }
}

#[derive(Debug)]
enum StoreError {
    IoError(std::io::Error),
    NotFound(String),
    IntegrityFailure(String),
}

impl From<std::io::Error> for StoreError {
    fn from(e: std::io::Error) -> Self {
        StoreError::IoError(e)
    }
}
```

### 11.5.4 Pin por Hash vs Pin por Versão

```text
+-------------------------------------------------------------------+
|         Pin por Hash vs Pin por Versao                             |
+-------------------------------------------------------------------+
|                                                                   |
|  PIN POR VERSAO:                                                  |
|  Ex: "plugin@1.2.3"                                               |
|                                                                   |
|  + Vantagens:                                                     |
|  - Legivel, facil de entender                                     |
|  - Atualizacoes automaticas possiveis                             |
|  - Compatibilidade com package managers                          |
|                                                                   |
|  - Riscos:                                                        |
|  - Versao pode ser sobrescrita no registry                        |
|  - Ataque de versao (version bumping)                             |
|  - Build nao e reprodutivel sem lock file                         |
|                                                                   |
|  PIN POR HASH:                                                    |
|  Ex: "plugin@sha256:a1b2c3d4..."                                 |
|                                                                   |
|  + Vantagens:                                                     |
|  - Garante exatamente qual versao e executada                     |
|  - Imune a manipulacao do registry                                |
|  - Build reprodutivel por construcao                              |
|                                                                   |
|  - Riscos:                                                        |
|  - Atualizacoes requerem mudanca manual                          |
|  - Dificil de ler e gerenciar                                     |
|  - Pode perder patches de seguranca                               |
|                                                                   |
|  RECOMENDACAO:                                                    |
|  - Usar AMBOS: pin por hash com fallback para versao              |
|  - Atualizacoes devem ser auditadas antes de aplicar              |
|  - Usar lock files que combinam hash + versao                     |
|                                                                   |
+-------------------------------------------------------------------+
```

```json
{
  "plugins": {
    "analytics": {
      "source": "registry://plugins.example.com/analytics",
      "version": "2.1.0",
      "pinned_hash": "sha256:a1b2c3d4e5f67890abcdef1234567890abcdef12",
      "integrity": "sha512:abc123...",
      "permissions": ["read:metrics", "write:logs"],
      "last_verified": "2024-01-15T10:00:00Z"
    },
    "auth": {
      "source": "registry://plugins.example.com/auth",
      "version": "1.0.2",
      "pinned_hash": "sha256:f6e5d4c3b2a10987654321fedcba9876543210fe",
      "integrity": "sha512:def456...",
      "permissions": ["read:users", "write:sessions"],
      "last_verified": "2024-01-10T08:00:00Z"
    }
  }
}
```

### 11.5.5 Estratégias de Atualização e Rollback

```rust
// Estrategias de atualizacao de plugins
enum UpdateStrategy {
    // Atualizacao automatica para versoes menores e patches
    AutoPatch,
    // Atualizacao automatica apenas para patches
    AutoMinor,
    // Nenhuma atualizacao automatica
    Manual,
    // Atualizacao com janela de teste
    Canary {
        test_duration: Duration,
        rollback_threshold: f64,  // % de erros para rollback
    },
}

struct PluginUpdater {
    strategy: UpdateStrategy,
    current_versions: HashMap<String, Version>,
    update_log: Vec<UpdateEvent>,
}

impl PluginUpdater {
    fn check_updates(&self) -> Vec<AvailableUpdate> {
        let mut updates = Vec::new();
        
        for (plugin_name, current_version) in &self.current_versions {
            if let Some(latest) = self.fetch_latest_version(plugin_name) {
                if latest > *current_version {
                    let compatibility = self.check_compatibility(
                        plugin_name,
                        current_version,
                        &latest,
                    );
                    
                    updates.push(AvailableUpdate {
                        plugin: plugin_name.clone(),
                        from: current_version.clone(),
                        to: latest,
                        compatibility,
                        security_fix: self.has_security_fix(
                            plugin_name,
                            current_version,
                            &latest,
                        ),
                    });
                }
            }
        }
        
        updates
    }
    
    fn apply_update(
        &mut self,
        update: &AvailableUpdate,
    ) -> Result<RollbackInfo, UpdateError> {
        // 1. Backup da versao atual
        let backup = self.create_backup(&update.plugin)?;
        
        // 2. Baixar nova versao
        let new_plugin = self.download_plugin(
            &update.plugin,
            &update.to,
        )?;
        
        // 3. Verificar integridade
        self.verify_plugin(&new_plugin)?;
        
        // 4. Testar em ambiente isolado
        let test_result = self.test_plugin(&new_plugin)?;
        
        if test_result.passed {
            // 5. Instalar
            self.install_plugin(&update.plugin, &new_plugin)?;
            
            // 6. Log da atualizacao
            self.update_log.push(UpdateEvent::Applied {
                plugin: update.plugin.clone(),
                from: update.from.clone(),
                to: update.to.clone(),
                timestamp: Utc::now(),
            });
            
            Ok(backup)
        } else {
            // Rollback
            self.restore_backup(&backup)?;
            
            self.update_log.push(UpdateEvent::RolledBack {
                plugin: update.plugin.clone(),
                reason: test_result.failure_reason,
                timestamp: Utc::now(),
            });
            
            Err(UpdateError::TestFailed(test_result))
        }
    }
    
    fn rollback(
        &mut self,
        plugin: &str,
        backup: &RollbackInfo,
    ) -> Result<(), UpdateError> {
        self.restore_backup(backup)?;
        
        self.update_log.push(UpdateEvent::ManualRollback {
            plugin: plugin.to_string(),
            target_version: backup.version.clone(),
            timestamp: Utc::now(),
        });
        
        Ok(())
    }
}

struct RollbackInfo {
    plugin: String,
    version: Version,
    backup_path: PathBuf,
    backup_hash: String,
    created_at: DateTime<Utc>,
}
```

### 11.5.6 Resolução de Versão de Dependências

```rust
// Resolucao de versao de dependencias para plugins Wasm
struct DependencyResolver {
    registry: PluginRegistry,
    constraint_solver: ConstraintSolver,
}

impl DependencyResolver {
    fn resolve(
        &self,
        root: &PluginSpec,
    ) -> Result<DependencyGraph, ResolutionError> {
        let mut graph = DependencyGraph::new();
        let mut queue = VecDeque::new();
        
        // Adicionar o plugin raiz
        queue.push_back((root.clone(), VersionConstraint::Any));
        
        while let Some((spec, constraint)) = queue.pop_front() {
            // Buscar versoes disponiveis
            let versions = self.registry.available_versions(&spec.name)?;
            
            // Resolver constraint
            let resolved = self.constraint_solver.resolve(
                &constraint,
                &versions,
            )?;
            
            // Adicionar ao grafo
            graph.add_node(&spec.name, &resolved);
            
            // Carregar dependencias
            let manifest = self.registry.get_manifest(
                &spec.name,
                &resolved,
            )?;
            
            for dep in &manifest.dependencies {
                if !graph.contains(&dep.name) {
                    queue.push_back((
                        dep.clone(),
                        dep.version_constraint.clone(),
                    ));
                    
                    graph.add_edge(&spec.name, &dep.name);
                }
            }
        }
        
        Ok(graph)
    }
    
    fn check_compatibility(
        &self,
        graph: &DependencyGraph,
    ) -> Result<(), CompatibilityError> {
        // Verificar conflitos
        for node in graph.nodes() {
            for other in graph.nodes() {
                if node != other {
                    if !node.is_compatible_with(other) {
                        return Err(CompatibilityError::Conflict {
                            a: node.clone(),
                            b: other.clone(),
                        });
                    }
                }
            }
        }
        
        // Verificar circularidade
        if graph.has_cycle() {
            return Err(CompatibilityError::CircularDependency);
        }
        
        Ok(())
    }
}
```

### 11.5.7 Formatos e Gerenciamento de Lock Files

```yaml
# plugin.lock - Formato de lock file para plugins Wasm
# Este arquivo e gerenciado automaticamente pelo plugin manager

version: 1
generated_at: "2024-01-15T10:30:00Z"
generated_by: "wasm-plugin-manager v0.5.0"

plugins:
  analytics:
    name: analytics
    version: "2.1.0"
    source: "registry://plugins.example.com/analytics"
    resolved_url: "https://plugins.example.com/analytics-2.1.0.wasm"
    integrity:
      sha256: "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
      blake3: "f6e5d4c3b2a10987654321fedcba9876543210fedcba9876543210fedcba9876"
    dependencies: []
    metadata:
      author: "Analytics Team"
      license: "MIT"
      wasm_target: "wasm32-wasi"
      
  auth:
    name: auth
    version: "1.0.2"
    source: "registry://plugins.example.com/auth"
    resolved_url: "https://plugins.example.com/auth-1.0.2.wasm"
    integrity:
      sha256: "b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a1"
      blake3: "e5d4c3b2a10987654321fedcba9876543210fedcba9876543210fedcba9876f6"
    dependencies:
      - name: "crypto-utils"
        version: "0.3.1"
        source: "registry://plugins.example.com/crypto-utils"
        integrity:
          sha256: "c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a1b2"
    metadata:
      author: "Security Team"
      license: "Apache-2.0"
      wasm_target: "wasm32-wasi"

  crypto-utils:
    name: crypto-utils
    version: "0.3.1"
    source: "registry://plugins.example.com/crypto-utils"
    resolved_url: "https://plugins.example.com/crypto-utils-0.3.1.wasm"
    integrity:
      sha256: "d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a1b2c3"
    dependencies: []
    metadata:
      author: "Crypto Team"
      license: "MIT"
      wasm_target: "wasm32-wasi"
```

---

## 11.6 Análise de Dependências

Análise de dependências é o processo de identificar, catalogar e avaliar todas as dependências de um módulo Wasm, incluindo dependências transitivas. Isso é essencial para identificar vulnerabilidades, problemas de licenciamento e riscos de supply chain.

### 11.6.1 Análise de Dependências Transitivas para Wasm

Dependências transitivas são dependências das dependências diretas. Um plugin pode ter apenas 3 dependências diretas, mas centenas de dependências transitivas:

```text
+-------------------------------------------------------------------+
|           Dependencias Transitivas em Plugins Wasm                  |
+-------------------------------------------------------------------+
|                                                                   |
|  plugin.wasm (raiz)                                               |
|  |-- auth.wasm (direta)                                           |
|  |   |-- crypto-utils.wasm (transitiva nivel 1)                   |
|  |   |   |-- sha2.wasm (transitiva nivel 2)                       |
|  |   |   |-- hmac.wasm (transitiva nivel 2)                       |
|  |   |   |-- rand.wasm (transitiva nivel 2)                       |
|  |   |-- jwt.wasm (transitiva nivel 1)                            |
|  |       |-- base64.wasm (transitiva nivel 2)                     |
|  |       |-- serde.wasm (transitiva nivel 2)                      |
|  |-- analytics.wasm (direta)                                      |
|  |   |-- serde.wasm (transitiva - compartilhada)                  |
|  |   |-- http-client.wasm (transitiva nivel 1)                    |
|  |       |-- dns-resolver.wasm (transitiva nivel 2)               |
|  |       |-- tls.wasm (transitiva nivel 2)                        |
|  |-- logging.wasm (direta)                                        |
|      |-- time.wasm (transitiva nivel 1)                           |
|                                                                   |
|  Total: 3 diretas + 10 transitivas = 13 componentes               |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Analise de dependencias para plugins Wasm
use std::collections::{HashMap, HashSet};
use petgraph::graph::{DiGraph, NodeIndex};

struct DependencyAnalyzer {
    registry: PluginRegistry,
    graph: DiGraph<PluginNode, DependencyEdge>,
    node_indices: HashMap<String, NodeIndex>,
}

#[derive(Debug)]
struct PluginNode {
    name: String,
    version: String,
    source: String,
    hash: String,
    license: String,
    vulnerabilities: Vec<Vulnerability>,
}

#[derive(Debug)]
struct DependencyEdge {
    version_constraint: String,
    is_optional: bool,
    feature_flags: Vec<String>,
}

impl DependencyAnalyzer {
    fn new(registry: PluginRegistry) -> Self {
        Self {
            registry,
            graph: DiGraph::new(),
            node_indices: HashMap::new(),
        }
    }
    
    fn analyze(&mut self, root: &str) -> Result<DependencyReport, AnalysisError> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        
        // Adicionar no raiz
        let root_node = self.registry.get_plugin(root)?;
        let root_idx = self.add_node(root_node);
        queue.push_back((root_idx, root.to_string()));
        visited.insert(root.to_string());
        
        // BFS para descobrir todas as dependencias
        while let Some((parent_idx, parent_name)) = queue.pop_front() {
            let manifest = self.registry.get_manifest(&parent_name)?;
            
            for dep in &manifest.dependencies {
                if !visited.contains(&dep.name) {
                    visited.insert(dep.name.clone());
                    
                    let dep_node = self.registry.get_plugin(&dep.name)?;
                    let dep_idx = self.add_node(dep_node);
                    
                    // Adicionar aresta
                    self.graph.add_edge(
                        parent_idx,
                        dep_idx,
                        DependencyEdge {
                            version_constraint: dep.version_constraint.clone(),
                            is_optional: dep.optional,
                            feature_flags: dep.features.clone(),
                        },
                    );
                    
                    queue.push_back((dep_idx, dep.name.clone()));
                }
            }
        }
        
        // Analisar vulnerabilidades
        let vulnerabilities = self.scan_vulnerabilities()?;
        
        // Analisar licencas
        let license_issues = self.check_licenses()?;
        
        // Analisar duplicatas
        let duplicates = self.find_duplicates()?;
        
        // Gerar relatorio
        Ok(DependencyReport {
            total_dependencies: self.graph.node_count(),
            direct_dependencies: self.count_direct(root_idx),
            transitive_dependencies: self.graph.node_count() - 1 - self.count_direct(root_idx),
            vulnerabilities,
            license_issues,
            duplicates,
            depth: self.calculate_depth(root_idx),
            graph: self.graph.clone(),
        })
    }
    
    fn scan_vulnerabilities(&self) -> Result<Vec<DependencyVulnerability>, AnalysisError> {
        let mut vulns = Vec::new();
        
        for node_idx in self.graph.node_indices() {
            let node = &self.graph[node_idx];
            
            // Consultar base de dados de vulnerabilidades
            let known_vulns = self.registry.check_vulnerabilities(
                &node.name,
                &node.version,
            )?;
            
            for vuln in known_vulns {
                vulns.push(DependencyVulnerability {
                    dependency: node.name.clone(),
                    version: node.version.clone(),
                    vulnerability: vuln,
                });
            }
        }
        
        Ok(vulns)
    }
    
    fn check_licenses(&self) -> Result<Vec<LicenseIssue>, AnalysisError> {
        let mut issues = Vec::new();
        
        let policy = LicensePolicy {
            allowed: vec![
                "MIT".to_string(),
                "Apache-2.0".to_string(),
                "BSD-2-Clause".to_string(),
                "BSD-3-Clause".to_string(),
            ],
            restricted: vec![
                "GPL-2.0".to_string(),
                "GPL-3.0".to_string(),
            ],
            denied: vec![
                "AGPL-3.0".to_string(),
            ],
        };
        
        for node_idx in self.graph.node_indices() {
            let node = &self.graph[node_idx];
            
            if policy.denied.contains(&node.license) {
                issues.push(LicenseIssue::Denied {
                    dependency: node.name.clone(),
                    license: node.license.clone(),
                });
            } else if policy.restricted.contains(&node.license) {
                issues.push(LicenseIssue::Restricted {
                    dependency: node.name.clone(),
                    license: node.license.clone(),
                });
            }
        }
        
        Ok(issues)
    }
    
    fn find_duplicates(&self) -> Result<Vec<DuplicateDependency>, AnalysisError> {
        let mut version_map: HashMap<String, Vec<String>> = HashMap::new();
        
        for node_idx in self.graph.node_indices() {
            let node = &self.graph[node_idx];
            version_map
                .entry(node.name.clone())
                .or_default()
                .push(node.version.clone());
        }
        
        let duplicates = version_map.into_iter()
            .filter(|(_, versions)| versions.len() > 1)
            .map(|(name, versions)| DuplicateDependency {
                name,
                versions,
            })
            .collect();
        
        Ok(duplicates)
    }
}

#[derive(Debug)]
struct DependencyReport {
    total_dependencies: usize,
    direct_dependencies: usize,
    transitive_dependencies: usize,
    vulnerabilities: Vec<DependencyVulnerability>,
    license_issues: Vec<LicenseIssue>,
    duplicates: Vec<DuplicateDependency>,
    depth: usize,
    graph: DiGraph<PluginNode, DependencyEdge>,
}

#[derive(Debug)]
struct DependencyVulnerability {
    dependency: String,
    version: String,
    vulnerability: Vulnerability,
}

#[derive(Debug)]
enum LicenseIssue {
    Denied { dependency: String, license: String },
    Restricted { dependency: String, license: String },
}

#[derive(Debug)]
struct DuplicateDependency {
    name: String,
    versions: Vec<String>,
}
```

### 11.6.2 Bases de Dados de Vulnerabilidades para Wasm

```text
+-------------------------------------------------------------------+
|       Bases de Dados de Vulnerabilidades para Wasm                 |
+-------------------------------------------------------------------+
|                                                                   |
|  Base              | Cobertura      | Acesso     | Formato         |
|  ------------------+----------------+------------+---------------- |
|  NVD (NIST)        | Geral (CVEs)   | Publico    | API, JSON       |
|  GitHub Advisory   | GitHub repos    | Publico    | API, GraphQL    |
|  RustSec           | Rust/Cargo      | Publico    | Advisory DB     |
|  OSV               | Multi-ecossistema| Publico   | API, JSON       |
|  wasm漏洞DB        | Wasm especifico | Parcial   | Custom          |
|  OSS-Fuzz          | Fuzzing results | Publico    | Bug tracker     |
|                                                                   |
|  INTEGRACAO:                                                      |
|  - OSV.dev: API unificada multi-ecossistema                      |
|  - cargo-audit: integracao Rust/RustSec                           |
|  - grype: scanner multi-formato                                  |
|  - snyk: plataforma comercial com cobertura Wasm                  |
|                                                                   |
+-------------------------------------------------------------------+
```

```bash
# Usar OSV para verificar vulnerabilidades em plugins Wasm
# Consultar API do OSV
curl -X POST https://api.osv.dev/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.2.3",
    "package": {
      "name": "my-plugin",
      "ecosystem": "crates.io"
    }
  }'

# Usar cargo-audit para plugins Rust->Wasm
cargo install cargo-audit
cargo audit

# Usar grype para analisar SBOM gerado
grype sbom:plugin.sbom.json

# Usar snyk para analise detalhada
snyk test --file=plugin.sbom.json
```

### 11.6.3 Conformidade de Licenciamento

```bash
#!/bin/bash
# Script de verificacao de licencas para plugins Wasm

set -euo pipefail

PLUGIN_FILE="$1"

# Extrair informacoes de licenca do binario Wasm
# (requer metadados embutidos no plugin)

# Usando syft para gerar SBOM com informacoes de licenca
syft "${PLUGIN_FILE}" -o spdx-json | jq '{
  packages: [.packages[] | {
    name: .name,
    version: .versionInfo.version,
    license: .licenseDeclared
  }]
}'

# Verificar contra politica de licenciamento
ALLOWED_LICENSES="MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC"
RESTRICTED_LICENSES="GPL-2.0,GPL-3.0,LGPL-2.1,LGPL-3.0"
DENIED_LICENSES="AGPL-3.0,SSPL-1.0,BSL-1.1"

syft "${PLUGIN_FILE}" -o spdx-json | \
  jq -r '.packages[] | .licenseDeclared' | \
  sort -u | while read license; do
    if echo "${DENIED_LICENSES}" | grep -q "${license}"; then
      echo "ERRO: Licenca negada encontrada: ${license}"
      exit 1
    elif echo "${RESTRICTED_LICENSES}" | grep -q "${license}"; then
      echo "AVISO: Licenca restrita encontrada: ${license}"
    elif ! echo "${ALLOWED_LICENSES}" | grep -q "${license}"; then
      echo "AVISO: Licenca nao classificada: ${license}"
    fi
  done

echo "Verificacao de licencas concluida"
```

### 11.6.4 Auditoria Automatizada de Dependências

```yaml
# Configuracao de auditoria automatizada de dependencias
# .wasm-plugin-audit.yml

plugins:
  - name: auth-plugin
    path: plugins/auth/plugin.wasm
    version: "1.2.3"
    
audit:
  # Escaneamento de vulnerabilidades
  vulnerability_scanning:
    enabled: true
    tools:
      - name: grype
        severity_threshold: high
        fail_on: critical
      - name: osv-scanner
        severity_threshold: medium
        fail_on: high
    
  # Verificacao de licencas
  license_compliance:
    enabled: true
    allowed:
      - MIT
      - Apache-2.0
      - BSD-2-Clause
      - BSD-3-Clause
    restricted:
      - GPL-2.0
      - GPL-3.0
    denied:
      - AGPL-3.0
    
  # Analise de dependencias
  dependency_analysis:
    enabled: true
    max_depth: 10
    check_circular: true
    check_duplicates: true
    check_outdated: true
    
  # Verificacao de integridade
  integrity_check:
    enabled: true
    verify_signatures: true
    verify_hashes: true
    verify_sbom: true

# Relatorio
reporting:
  format:
    - json
    - sarif
    - markdown
  destination:
    - stdout
    - file:audit-report.json
    - github_security_tab: true

# Acoes automaticas
actions:
  on_critical_vulnerability:
    - create_issue: true
    - notify_slack: true
    - block_deployment: true
  on_high_vulnerability:
    - create_issue: true
    - notify_slack: false
    - block_deployment: false
  on_license_violation:
    - create_issue: true
    - notify_slack: true
    - block_deployment: true
```

---

## 11.7 SBOM para Módulos Wasm

Software Bill of Materials (SBOM) é um inventário estruturado de todos os componentes, bibliotecas e dependências que compõem um software. Para módulos Wasm, o SBOM é particularmente importante devido à natureza opaca do bytecode compilado.

### 11.7.1 O que é um SBOM

Um SBOM documenta:
- Todos os pacotes e componentes incluídos
- Versões exatas de cada componente
- Relações de dependência entre componentes
- Licenças de cada componente
- Metadados de proveniência
- Informações de build

```text
+-------------------------------------------------------------------+
|                    Estrutura de um SBOM                             |
+-------------------------------------------------------------------+
|                                                                   |
|  SBOM                                                              |
|  |-- Meta-dados do documento                                      |
|  |   |-- Versao do formato                                        |
|  |   |-- Data de geracao                                          |
|  |   |-- Ferramenta geradora                                      |
|  |   |-- Componente principal (plugin.wasm)                       |
|  |                                                                   |
|  |-- Componentes                                                   |
|  |   |-- auth-plugin.wasm                                          |
|  |   |   |-- Versao: 1.2.3                                        |
|  |   |   |-- Licenca: MIT                                          |
|  |   |   |-- Hash: sha256:abc123...                                |
|  |   |   |-- Dependencias: [crypto-utils, jwt]                     |
|  |   |-- crypto-utils.wasm                                         |
|  |   |   |-- Versao: 0.3.1                                        |
|  |   |   |-- Licenca: Apache-2.0                                   |
|  |   |   |-- Dependencias: []                                      |
|  |   |-- jwt.wasm                                                  |
|  |   |   |-- Versao: 2.0.0                                        |
|  |   |   |-- Licenca: MIT                                          |
|  |   |   |-- Dependencias: [base64, serde]                         |
|  |                                                                   |
|  |-- Relacoes de dependencia                                       |
|  |   |-- auth-plugin -> crypto-utils                               |
|  |   |-- auth-plugin -> jwt                                        |
|  |   |-- jwt -> base64                                             |
|  |   |-- jwt -> serde                                              |
|  |                                                                   |
+-------------------------------------------------------------------+
```

### 11.7.2 Formato SPDX para Módulos Wasm

SPDX (Software Package Data Exchange) é um padrão ISO para SBOMs:

```json
{
  "spdxVersion": "SPDX-2.3",
  "dataLicense": "CC0-1.0",
  "SPDXID": "SPDXRef-DOCUMENT",
  "name": "plugin.wasm",
  "documentNamespace": "https://company.com/sbom/plugin-wasm-2024",
  "creationInfo": {
    "created": "2024-01-15T10:30:00Z",
    "creators": [
      "Tool: syft-0.100.0",
      "Organization: My Company"
    ],
    "licenseListVersion": "3.22"
  },
  "packages": [
    {
      "SPDXID": "SPDXRef-Package-plugin",
      "name": "my-plugin",
      "versionInfo": "1.2.3",
      "downloadLocation": "https://registry.example.com/plugin/1.2.3",
      "filesAnalyzed": false,
      "checksums": [
        {
          "algorithm": "SHA256",
          "checksumValue": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
        },
        {
          "algorithm": "BLAKE3",
          "checksumValue": "f6e5d4c3b2a10987654321fedcba9876543210fedcba9876543210fedcba9876"
        }
      ],
      "licenseConcluded": "MIT",
      "licenseDeclared": "MIT",
      "copyrightText": "Copyright (c) 2024 My Company",
      "externalRefs": [
        {
          "referenceCategory": "PACKAGE-MANAGER",
          "referenceType": "purl",
          "referenceLocator": "pkg:wasm/my-plugin@1.2.3"
        }
      ]
    },
    {
      "SPDXID": "SPDXRef-Package-auth",
      "name": "auth-plugin",
      "versionInfo": "1.0.2",
      "downloadLocation": "https://registry.example.com/auth/1.0.2",
      "filesAnalyzed": false,
      "checksums": [
        {
          "algorithm": "SHA256",
          "checksumValue": "b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a1"
        }
      ],
      "licenseConcluded": "Apache-2.0",
      "licenseDeclared": "Apache-2.0",
      "externalRefs": [
        {
          "referenceCategory": "PACKAGE-MANAGER",
          "referenceType": "purl",
          "referenceLocator": "pkg:wasm/auth-plugin@1.0.2"
        }
      ]
    }
  ],
  "relationships": [
    {
      "spdxElementId": "SPDXRef-Package-plugin",
      "relationshipType": "DEPENDS_ON",
      "relatedSpdxElement": "SPDXRef-Package-auth"
    }
  ]
}
```

### 11.7.3 Formato CycloneDX para Wasm

CycloneDX é outro formato popular de SBOM, mantenido pela OWASP:

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "version": 1,
  "metadata": {
    "timestamp": "2024-01-15T10:30:00.000Z",
    "tools": {
      "components": [
        {
          "name": "syft",
          "version": "0.100.0",
          "type": "application"
        }
      ]
    },
    "component": {
      "type": "application",
      "bom-ref": "my-plugin-1.2.3",
      "name": "my-plugin",
      "version": "1.2.3",
      "description": "Plugin Wasm para processamento de dados",
      "hashes": [
        {
          "alg": "SHA-256",
          "value": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
        }
      ],
      "licenses": [
        {
          "license": {
            "id": "MIT"
          }
        }
      ]
    }
  },
  "components": [
    {
      "type": "library",
      "bom-ref": "auth-plugin-1.0.2",
      "name": "auth-plugin",
      "version": "1.0.2",
      "description": "Plugin de autenticacao",
      "hashes": [
        {
          "alg": "SHA-256",
          "value": "b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890a1"
        }
      ],
      "licenses": [
        {
          "license": {
            "id": "Apache-2.0"
          }
        }
      ],
      "purl": "pkg:wasm/auth-plugin@1.0.2",
      "properties": [
        {
          "name": "wasm:target",
          "value": "wasm32-wasi"
        },
        {
          "name": "wasm:capabilities",
          "value": "filesystem,networking"
        }
      ]
    }
  ],
  "dependencies": [
    {
      "ref": "my-plugin-1.2.3",
      "dependsOn": [
        "auth-plugin-1.0.2"
      ]
    }
  ]
}
```

### 11.7.4 Geração de SBOMs a partir de Wasm Compilado

```bash
# Gerar SBOM usando syft
# SPDX format
syft target/wasm32-wasi/release/plugin.wasm \
    -o spdx-json > plugin.spdx.json

# CycloneDX format
syft target/wasm32-wasi/release/plugin.wasm \
    -o cyclonedx-json > plugin.cdx.json

# Gerar SBOM com metadados adicionais
syft target/wasm32-wasi/release/plugin.wasm \
    -o spdx-json \
    --name my-plugin \
    --version 1.2.3 \
    --output-all-artifacts-with-licenses \
    > plugin.spdx.json

# Verificar SBOM gerado
cat plugin.spdx.json | jq '.packages | length'
# Output: 5 (numero de componentes detectados)
```

**Script de geração completo**:

```bash
#!/bin/bash
# Gerar SBOM completo para plugin Wasm

set -euo pipefail

PLUGIN_NAME="${1:?Uso: $0 <nome-plugin>}"
WASM_FILE="target/wasm32-wasi/release/${PLUGIN_NAME}.wasm"
VERSION=$(cargo metadata --format-version 1 | jq -r '.packages[0].version')

echo "=== Gerando SBOM para ${PLUGIN_NAME} v${VERSION} ==="

# 1. Gerar SBOM SPDX
echo "Gerando SBOM SPDX..."
syft "${WASM_FILE}" \
    -o spdx-json \
    --name "${PLUGIN_NAME}" \
    --version "${VERSION}" \
    > "${PLUGIN_NAME}.spdx.json"

# 2. Gerar SBOM CycloneDX
echo "Gerando SBOM CycloneDX..."
syft "${WASM_FILE}" \
    -o cyclonedx-json \
    --name "${PLUGIN_NAME}" \
    --version "${VERSION}" \
    > "${PLUGIN_NAME}.cdx.json"

# 3. Extrair informacoes de licenca
echo "Extraindo informacoes de licenca..."
jq -r '.packages[] | "\(.name)@\(.versionInfo): \(.licenseDeclared)"' \
    "${PLUGIN_NAME}.spdx.json" > "${PLUGIN_NAME}.licenses.txt"

# 4. Verificar vulnerabilidades no SBOM
echo "Verificando vulnerabilidades..."
grype "sbom:${PLUGIN_NAME}.spdx.json" \
    --output json \
    > "${PLUGIN_NAME}.vulnerabilities.json"

# 5. Resumo
COMPONENTS=$(jq '.packages | length' "${PLUGIN_NAME}.spdx.json")
VULNS=$(jq '.matches | length' "${PLUGIN_NAME}.vulnerabilities.json" 2>/dev/null || echo "0")

echo ""
echo "=== Resumo ==="
echo "Componentes: ${COMPONENTS}"
echo "Vulnerabilidades: ${VULNS}"
echo "SBOM SPDX: ${PLUGIN_NAME}.spdx.json"
echo "SBOM CycloneDX: ${PLUGIN_NAME}.cdx.json"
echo "Licencas: ${PLUGIN_NAME}.licenses.txt"
```

### 11.7.5 Rastreamento de Dependências e Proveniência

```rust
// Rastreamento de proveniencia para plugins Wasm
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct ProvenanceRecord {
    source: SourceInfo,
    build: BuildInfo,
    artifacts: Vec<ArtifactInfo>,
    attestations: Vec<AttestationInfo>,
}

#[derive(Serialize, Deserialize)]
struct SourceInfo {
    repository: String,
    commit: String,
    branch: String,
    timestamp: DateTime<Utc>,
    author: String,
    signed_commits: bool,
}

#[derive(Serialize, Deserialize)]
struct BuildInfo {
    builder: String,
    build_id: String,
    environment: BuildEnvironment,
    inputs: Vec<BuildInput>,
    reproducible: bool,
    hermetic: bool,
}

#[derive(Serialize, Deserialize)]
struct ArtifactInfo {
    name: String,
    path: String,
    hash_sha256: String,
    hash_blake3: String,
    size: u64,
    mime_type: String,
    signed: bool,
    signature_bundle: Option<String>,
}

impl ProvenanceRecord {
    fn verify(&self) -> Result<(), ProvenanceError> {
        // 1. Verificar que o source e autentico
        if !self.source.signed_commits {
            return Err(ProvenanceError::UnsignedCommits);
        }
        
        // 2. Verificar que o build e reprodutivel
        if !self.build.reproducible {
            return Err(ProvenanceError::NonReproducibleBuild);
        }
        
        // 3. Verificar que todos os artefatos estao assinados
        for artifact in &self.artifacts {
            if !artifact.signed {
                return Err(ProvenanceError::UnsignedArtifact {
                    name: artifact.name.clone(),
                });
            }
        }
        
        // 4. Verificar que as atestacoes sao validas
        for attestation in &self.attestations {
            attestation.verify()?;
        }
        
        Ok(())
    }
    
    fn to_sbom_extension(&self) -> serde_json::Value {
        serde_json::json!({
            "provenance": {
                "source": {
                    "repository": self.source.repository,
                    "commit": self.source.commit,
                    "branch": self.source.branch,
                    "timestamp": self.source.timestamp,
                    "signed_commits": self.source.signed_commits
                },
                "build": {
                    "builder": self.build.builder,
                    "reproducible": self.build.reproducible,
                    "hermetic": self.build.hermetic
                },
                "artifacts": self.artifacts.iter().map(|a| {
                    serde_json::json!({
                        "name": a.name,
                        "hash_sha256": a.hash_sha256,
                        "signed": a.signed
                    })
                }).collect::<Vec<_>>()
            }
        })
    }
}
```

### 11.7.6 SBOM em Pipelines de CI/CD

```yaml
# Pipeline completa de SBOM para plugins Wasm
name: SBOM Generation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  generate-sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: actions-rust-lang/setup-rust-toolchain@v1
        with:
          targets: wasm32-wasi
      
      - name: Build plugin
        run: cargo build --target wasm32-wasi --release
      
      - name: Install SBOM tools
        run: |
          # syft para geracao de SBOM
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
          # grype para verificacao de vulnerabilidades
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s --
      
      - name: Generate SBOM
        run: |
          syft ./target/wasm32-wasi/release/plugin.wasm \
            -o spdx-json > plugin.spdx.json
          syft ./target/wasm32-wasi/release/plugin.wasm \
            -o cyclonedx-json > plugin.cdx.json
      
      - name: Validate SBOM
        run: |
          # Validar formato SPDX
          jq '.spdxVersion' plugin.spdx.json
          # Validar numero de componentes
          COMPONENTS=$(jq '.packages | length' plugin.spdx.json)
          echo "Componentes detectados: ${COMPONENTS}"
      
      - name: Check vulnerabilities
        run: |
          grype "sbom:plugin.spdx.json" \
            --fail-on critical \
            --output table
      
      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            plugin.spdx.json
            plugin.cdx.json
      
      - name: Publish SBOM to registry
        if: github.ref == 'refs/heads/main'
        run: |
          # Publicar SBOM junto com o plugin
          syft publish \
            --registry https://sbom.example.com \
            plugin.spdx.json
```

### 11.7.7 Consumindo SBOMs para Decisões de Segurança

```rust
// Consumir SBOM para decisoes de seguranca
struct SBOMConsumer {
    vulnerability_db: VulnerabilityDatabase,
    license_policy: LicensePolicy,
    risk_calculator: RiskCalculator,
}

impl SBOMConsumer {
    fn analyze_sbom(&self, sbom: &SBOM) -> SecurityReport {
        let mut report = SecurityReport::new();
        
        // 1. Analisar cada componente
        for component in &sbom.components {
            // Verificar vulnerabilidades
            let vulns = self.vulnerability_db.query(
                &component.name,
                &component.version,
            );
            
            if !vulns.is_empty() {
                report.add_vulnerability(VulnerabilityFinding {
                    component: component.clone(),
                    vulnerabilities: vulns,
                });
            }
            
            // Verificar licenca
            if let Some(license) = &component.license {
                match self.license_policy.evaluate(license) {
                    LicenseDecision::Allowed => {}
                    LicenseDecision::Restricted(reason) => {
                        report.add_license_warning(
                            component.clone(),
                            reason,
                        );
                    }
                    LicenseDecision::Denied(reason) => {
                        report.add_license_violation(
                            component.clone(),
                            reason,
                        );
                    }
                }
            }
            
            // Calcular risco
            let risk = self.risk_calculator.calculate(component);
            report.add_risk_assessment(component.clone(), risk);
        }
        
        // 2. Analisar profundidade da cadeia de dependencias
        let depth = sbom.calculate_depth();
        if depth > 5 {
            report.add_warning(format!(
                "Cadeia de dependencias profunda: {} niveis",
                depth
            ));
        }
        
        // 3. Verificar duplicatas
        let duplicates = sbom.find_duplicates();
        if !duplicates.is_empty() {
            report.add_info(format!(
                "Dependencias duplicadas: {} pacotes",
                duplicates.len()
            ));
        }
        
        // 4. Gerar recomendacoes
        report.recommendations = self.generate_recommendations(&report);
        
        report
    }
    
    fn generate_recommendations(
        &self,
        report: &SecurityReport,
    ) -> Vec<Recommendation> {
        let mut recs = Vec::new();
        
        if report.has_critical_vulnerabilities() {
            recs.push(Recommendation {
                priority: Priority::Critical,
                action: "Atualizar componentes vulneraveis imediatamente".to_string(),
                impact: "Correcao de seguranca critica".to_string(),
            });
        }
        
        if report.has_denied_licenses() {
            recs.push(Recommendation {
                priority: Priority::High,
                action: "Substituir componentes com licencas negadas".to_string(),
                impact: "Conformidade de licenciamento".to_string(),
            });
        }
        
        if report.deep_dependency_chain() {
            recs.push(Recommendation {
                priority: Priority::Medium,
                action: "Revisar e simplificar cadeia de dependencias".to_string(),
                impact: "Reducao de superficie de ataque".to_string(),
            });
        }
        
        recs
    }
}
```

---

## 11.8 Atestação

Atestação é o processo de criar declarações criptográficas verificáveis sobre como um artefato foi criado, o que contém e quem o criou. No contexto de plugins Wasm, a atestação fornece evidência de que o plugin foi construído em um ambiente confiável e não foi adulterado.

### 11.8.1 Framework SLSA (Supply-chain Levels for Software Artifacts)

SLSA define quatro níveis de segurança de supply chain:

```text
+-------------------------------------------------------------------+
|                    Niveis SLSA                                      |
+-------------------------------------------------------------------+
|                                                                   |
|  Nivel 0: Sem garantias                                           |
|  - Artefato pode ter sido construido de qualquer forma            |
|  - Sem verificacao de proveniencia                                |
|                                                                   |
|  Nivel 1: Processo de build documentado                           |
|  - Artefato e gerado por um processo de build identificavel       |
|  - Proveniencia gerada, mas nao verificada                        |
|  - Ex: build manual com script documentado                        |
|                                                                   |
|  Nivel 2: Build hospedado e com proveniencia assinada             |
|  - Build roda em plataforma de build hospedada (CI/CD)            |
|  - Proveniencia gerada e assinada pela plataforma                 |
|  - Ex: GitHub Actions com attestations                             |
|                                                                   |
|  Nivel 3: Build com protecao anti-tampering                       |
|  - Build e reprodutivel ou hermetico                              |
|  - Dependencias resolve por hash                                  |
|  - Proveniencia e atestacao verificaveis                          |
|  - Ex: Build com SLSA verifier                                    |
|                                                                   |
|  Nivel 4: Build com fontes verificadas                            |
|  - Toda a cadeia de proveniencia e verificada                     |
|  - Source e build sao verificados contra plataformas confiaveis   |
|  - Ex: Two-party review + hermetic build                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.8.2 Atestação In-toto para Wasm

In-toto é um framework para garantir a integridade de toda a cadeia de software:

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "subject": [
    {
      "name": "plugin.wasm",
      "digest": {
        "sha256": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
      }
    }
  ],
  "predicate": {
    "builder": {
      "id": "https://github.com/actions/runner"
    },
    "buildType": "https://github.com/actions/workflow@v1",
    "invocation": {
      "configSource": {
        "uri": "git+https://github.com/org/repo@refs/heads/main",
        "digest": {
          "sha1": "abc123def456..."
        },
        "entryPoint": ".github/workflows/build.yml"
      },
      "parameters": {
        "target": "wasm32-wasi",
        "profile": "release",
        "features": ["default"]
      }
    },
    "metadata": {
      "buildInvocationId": "12345",
      "buildStartedOn": "2024-01-15T10:00:00Z",
      "buildFinishedOn": "2024-01-15T10:05:00Z",
      "completeness": {
        "environment": false,
        "materials": true,
        "parameters": true
      },
      "reproducible": false
    },
    "materials": [
      {
        "uri": "git+https://github.com/org/repo@refs/heads/main",
        "digest": {
          "sha1": "abc123def456..."
        }
      }
    ]
  }
}
```

### 11.8.3 Atestação de Proveniência

```rust
// Gerar atestacao de proveniencia para plugins Wasm
use sha2::{Sha256, Digest};
use serde::Serialize;

#[derive(Serialize)]
struct ProvenanceAttestation {
    #[serde(rename = "_type")]
    statement_type: String,
    #[serde(rename = "predicateType")]
    predicate_type: String,
    subject: Vec<Subject>,
    predicate: ProvenancePredicate,
}

#[derive(Serialize)]
struct Subject {
    name: String,
    digest: DigestInfo,
}

#[derive(Serialize)]
struct DigestInfo {
    sha256: String,
}

#[derive(Serialize)]
struct ProvenancePredicate {
    builder: BuilderInfo,
    #[serde(rename = "buildType")]
    build_type: String,
    invocation: InvocationInfo,
    metadata: MetadataInfo,
    materials: Vec<Material>,
}

#[derive(Serialize)]
struct BuilderInfo {
    id: String,
}

#[derive(Serialize)]
struct InvocationInfo {
    #[serde(rename = "configSource")]
    config_source: ConfigSource,
    parameters: BuildParameters,
}

#[derive(Serialize)]
struct ConfigSource {
    uri: String,
    digest: DigestInfo,
    #[serde(rename = "entryPoint")]
    entry_point: String,
}

#[derive(Serialize)]
struct BuildParameters {
    target: String,
    profile: String,
    features: Vec<String>,
}

#[derive(Serialize)]
struct MetadataInfo {
    #[serde(rename = "buildInvocationId")]
    build_invocation_id: String,
    #[serde(rename = "buildStartedOn")]
    build_started_on: String,
    #[serde(rename = "buildFinishedOn")]
    build_finished_on: String,
    completeness: CompletenessInfo,
    reproducible: bool,
}

#[derive(Serialize)]
struct CompletenessInfo {
    environment: bool,
    materials: bool,
    parameters: bool,
}

#[derive(Serialize)]
struct Material {
    uri: String,
    digest: DigestInfo,
}

impl ProvenanceAttestation {
    fn generate(
        wasm_bytes: &[u8],
        build_info: &BuildInfo,
    ) -> Self {
        let hash = Sha256::digest(wasm_bytes);
        
        Self {
            statement_type: "https://in-toto.io/Statement/v0.1".to_string(),
            predicate_type: "https://slsa.dev/provenance/v0.2".to_string(),
            subject: vec![Subject {
                name: "plugin.wasm".to_string(),
                digest: DigestInfo {
                    sha256: hex::encode(hash),
                },
            }],
            predicate: ProvenancePredicate {
                builder: BuilderInfo {
                    id: "https://github.com/actions/runner".to_string(),
                },
                build_type: "https://github.com/actions/workflow@v1".to_string(),
                invocation: InvocationInfo {
                    config_source: ConfigSource {
                        uri: format!(
                            "git+{}@refs/heads/{}",
                            build_info.repository,
                            build_info.branch,
                        ),
                        digest: DigestInfo {
                            sha1: build_info.commit.clone(),
                        },
                        entry_point: ".github/workflows/build.yml".to_string(),
                    },
                    parameters: BuildParameters {
                        target: "wasm32-wasi".to_string(),
                        profile: "release".to_string(),
                        features: build_info.features.clone(),
                    },
                },
                metadata: MetadataInfo {
                    build_invocation_id: build_info.build_id.clone(),
                    build_started_on: build_info.start_time.to_rfc3339(),
                    build_finished_on: build_info.end_time.to_rfc3339(),
                    completeness: CompletenessInfo {
                        environment: false,
                        materials: true,
                        parameters: true,
                    },
                    reproducible: build_info.reproducible,
                },
                materials: vec![Material {
                    uri: format!(
                        "git+{}@refs/heads/{}",
                        build_info.repository,
                        build_info.branch,
                    ),
                    digest: DigestInfo {
                        sha1: build_info.commit.clone(),
                    },
                }],
            },
        }
    }
    
    fn sign(&self, key: &SigningKey) -> Result<Vec<u8>, SigningError> {
        let json = serde_json::to_vec(self)?;
        let signature = key.sign(&json)?;
        Ok(signature)
    }
    
    fn verify(
        &self,
        public_key: &VerifyingKey,
        signature: &[u8],
    ) -> Result<bool, VerificationError> {
        let json = serde_json::to_vec(self)?;
        public_key.verify(&json, signature)
            .map(|_| true)
            .map_err(|_| VerificationError::InvalidSignature)
    }
}
```

### 11.8.4 Atestação de Build

```rust
// Atestacao de build completa
#[derive(Serialize)]
struct BuildAttestation {
    builder: BuildBuilder,
    build_config: BuildConfig,
    build_provenance: BuildProvenance,
    resource_descriptor: ResourceDescriptor,
}

#[derive(Serialize)]
struct BuildBuilder {
    uri: String,
    version: String,
}

#[derive(Serialize)]
struct BuildConfig {
    engine: BuildEngine,
    steps: Vec<BuildStep>,
    timeout: String,
}

#[derive(Serialize)]
struct BuildEngine {
    name: String,
    url: String,
    version: String,
}

#[derive(Serialize)]
struct BuildStep {
    image: String,
    command: Vec<String>,
    env: Vec<EnvVar>,
}

#[derive(Serialize)]
struct EnvVar {
    name: String,
    value: String,
}

#[derive(Serialize)]
struct BuildProvenance {
    invocado_at: String,
    finished_at: String,
    build_definition: BuildDefinition,
    run_details: RunDetails,
}

#[derive(Serialize)]
struct BuildDefinition {
    build_type: String,
    external_parameters: ExternalParameters,
    internal_parameters: serde_json::Value,
    resolved_dependencies: Vec<ResolvedDependency>,
}

#[derive(Serialize)]
struct ExternalParameters {
    workflow: WorkflowRef,
    runner: RunnerRef,
}

#[derive(Serialize)]
struct WorkflowRef {
    repository: String,
    ref_name: String,
    path: String,
    sha: String,
}

#[derive(Serialize)]
struct RunnerRef {
    uri: String,
}

#[derive(Serialize)]
struct ResolvedDependency {
    uri: String,
    digest: DigestInfo,
}

#[derive(Serialize)]
struct RunDetails {
    builder: BuildBuilder,
    invoked_at: String,
    metadata: RunMetadata,
}

#[derive(Serialize)]
struct RunMetadata {
    invocation_id: String,
    started_on: String,
    finished_on: String,
}

#[derive(Serialize)]
struct ResourceDescriptor {
    name: String,
    uri: String,
    digest: DigestInfo,
}

impl BuildAttestation {
    fn from_github_actions(
        wasm_hash: &str,
        workflow_run: &WorkflowRun,
    ) -> Self {
        Self {
            builder: BuildBuilder {
                uri: "https://github.com/actions/runner".to_string(),
                version: "v2.310.0".to_string(),
            },
            build_config: BuildConfig {
                engine: BuildEngine {
                    name: "GitHub Actions".to_string(),
                    url: format!(
                        "https://github.com/{}/actions/runs/{}",
                        workflow_run.repository,
                        workflow_run.run_id,
                    ),
                    version: "v2".to_string(),
                },
                steps: vec![
                    BuildStep {
                        image: "actions/checkout@v4".to_string(),
                        command: vec!["checkout".to_string()],
                        env: vec![],
                    },
                    BuildStep {
                        image: "actions-rust-lang/setup-rust-toolchain@v1".to_string(),
                        command: vec!["setup".to_string()],
                        env: vec![EnvVar {
                            name: "targets".to_string(),
                            value: "wasm32-wasi".to_string(),
                        }],
                    },
                    BuildStep {
                        image: "ubuntu-latest".to_string(),
                        command: vec![
                            "cargo".to_string(),
                            "build".to_string(),
                            "--target".to_string(),
                            "wasm32-wasi".to_string(),
                            "--release".to_string(),
                        ],
                        env: vec![],
                    },
                ],
                timeout: "30m".to_string(),
            },
            build_provenance: BuildProvenance {
                invocado_at: workflow_run.created_at.to_rfc3339(),
                finished_at: workflow_run.updated_at.to_rfc3339(),
                build_definition: BuildDefinition {
                    build_type: "https://slsa.dev/build/v1".to_string(),
                    external_parameters: ExternalParameters {
                        workflow: WorkflowRef {
                            repository: workflow_run.repository.clone(),
                            ref_name: workflow_run.branch.clone(),
                            path: ".github/workflows/build.yml".to_string(),
                            sha: workflow_run.commit.clone(),
                        },
                        runner: RunnerRef {
                            uri: "https://github.com/actions/runner".to_string(),
                        },
                    },
                    internal_parameters: serde_json::json!({}),
                    resolved_dependencies: vec![],
                },
                run_details: RunDetails {
                    builder: BuildBuilder {
                        uri: "https://github.com/actions/runner".to_string(),
                        version: "v2.310.0".to_string(),
                    },
                    invoked_at: workflow_run.created_at.to_rfc3339(),
                    metadata: RunMetadata {
                        invocation_id: workflow_run.run_id.clone(),
                        started_on: workflow_run.created_at.to_rfc3339(),
                        finished_on: workflow_run.updated_at.to_rfc3339(),
                    },
                },
            },
            resource_descriptor: ResourceDescriptor {
                name: "plugin.wasm".to_string(),
                uri: format!(
                    "https://github.com/{}/releases/download/{}/plugin.wasm",
                    workflow_run.repository,
                    workflow_run.tag,
                ),
                digest: DigestInfo {
                    sha256: wasm_hash.to_string(),
                },
            },
        }
    }
}
```

### 11.8.5 Atestação de Código-Fonte

```rust
// Atestacao de codigo-fonte - vincula o binario ao repositorio
struct SourceAttestation {
    repository_url: String,
    repository_hash: String,
    commit_hash: String,
    branch: String,
    tags: Vec<String>,
    signed_commits: bool,
    branch_protection: bool,
    code_review: bool,
    ci_passing: bool,
}

impl SourceAttestation {
    fn verify(
        &self,
        expected_repository: &str,
        expected_commit: &str,
    ) -> Result<(), SourceVerificationError> {
        // Verificar repositorio
        if self.repository_url != expected_repository {
            return Err(SourceVerificationError::RepositoryMismatch);
        }
        
        // Verificar commit
        if self.commit_hash != expected_commit {
            return Err(SourceVerificationError::CommitMismatch);
        }
        
        // Verificar protecoes
        if !self.signed_commits {
            return Err(SourceVerificationError::UnsignedCommits);
        }
        
        if !self.branch_protection {
            return Err(SourceVerificationError::NoBranchProtection);
        }
        
        if !self.code_review {
            return Err(SourceVerificationError::NoCodeReview);
        }
        
        if !self.ci_passing {
            return Err(SourceVerificationError::CIFailing);
        }
        
        Ok(())
    }
    
    fn generate_from_github(
        owner: &str,
        repo: &str,
        commit: &str,
    ) -> Result<Self, GitHubAPIError> {
        // Verificar se commits sao signed via GitHub API
        let signed_commits = check_signed_commits(owner, repo, commit)?;
        
        // Verificar branch protection
        let branch_protection = check_branch_protection(owner, repo)?;
        
        // Verificar code review
        let code_review = check_code_review(owner, repo, commit)?;
        
        // Verificar CI status
        let ci_passing = check_ci_status(owner, repo, commit)?;
        
        Ok(Self {
            repository_url: format!(
                "https://github.com/{}/{}.git",
                owner,
                repo,
            ),
            repository_hash: compute_repo_hash(owner, repo)?,
            commit_hash: commit.to_string(),
            branch: get_default_branch(owner, repo)?,
            tags: get_tags(owner, repo, commit)?,
            signed_commits,
            branch_protection,
            code_review,
            ci_passing,
        })
    }
}

#[derive(Debug)]
enum SourceVerificationError {
    RepositoryMismatch,
    CommitMismatch,
    UnsignedCommits,
    NoBranchProtection,
    NoCodeReview,
    CIFailing,
}
```

### 11.8.6 Atestação de Ambiente

```rust
// Atestacao de ambiente - documenta o ambiente de build
struct EnvironmentAttestation {
    os: String,
    arch: String,
    runner: String,
    toolchain: ToolchainInfo,
    dependencies: Vec<ToolDependency>,
    network_access: bool,
    hermetic: bool,
}

#[derive(Serialize)]
struct ToolchainInfo {
    rustc_version: String,
    cargo_version: String,
    wasm_target: String,
    wasm_tools_version: Option<String>,
}

#[derive(Serialize)]
struct ToolDependency {
    name: String,
    version: String,
    source: String,
    hash: String,
}

impl EnvironmentAttestation {
    fn capture() -> Self {
        Self {
            os: std::env::consts::OS.to_string(),
            arch: std::env::consts::ARCH.to_string(),
            runner: std::env::var("RUNNER_NAME")
                .unwrap_or_else(|_| "unknown".to_string()),
            toolchain: ToolchainInfo {
                rustc_version: get_rustc_version(),
                cargo_version: get_cargo_version(),
                wasm_target: "wasm32-wasi".to_string(),
                wasm_tools_version: get_wasm_tools_version(),
            },
            dependencies: capture_tool_dependencies(),
            network_access: check_network_access(),
            hermetic: check_hermetic_build(),
        }
    }
    
    fn verify(&self, expected: &EnvironmentAttestation) -> Result<(), EnvironmentError> {
        if self.os != expected.os {
            return Err(EnvironmentError::OSMismatch);
        }
        
        if self.arch != expected.arch {
            return Err(EnvironmentError::ArchMismatch);
        }
        
        if self.toolchain.rustc_version != expected.toolchain.rustc_version {
            return Err(EnvironmentError::ToolchainMismatch);
        }
        
        if self.network_access && !expected.network_access {
            return Err(EnvironmentError::UnexpectedNetworkAccess);
        }
        
        Ok(())
    }
}

#[derive(Debug)]
enum EnvironmentError {
    OSMismatch,
    ArchMismatch,
    ToolchainMismatch,
    UnexpectedNetworkAccess,
}
```

### 11.8.7 Verificação de Atestações em Runtime

```rust
// Verificacao de atestacoes em runtime
struct AttestationVerifier {
    trusted_builders: Vec<String>,
    trusted_sources: Vec<String>,
    min_slsa_level: u8,
}

impl AttestationVerifier {
    fn verify_plugin(
        &self,
        plugin_bytes: &[u8],
        attestations: &[Attestation],
    ) -> Result<VerificationResult, VerificationError> {
        let mut result = VerificationResult::new();
        
        // 1. Verificar proveniencia
        let provenance = attestations.iter()
            .find(|a| a.is_provenance())
            .ok_or(VerificationError::MissingAttestation("provenance"))?;
        
        if !self.verify_provenance(provenance)? {
            result.add_failure("Proveniencia invalida");
        } else {
            result.add_success("Proveniencia verificada");
        }
        
        // 2. Verificar build
        let build = attestations.iter()
            .find(|a| a.is_build())
            .ok_or(VerificationError::MissingAttestation("build"))?;
        
        if !self.verify_build(build)? {
            result.add_failure("Build invalido");
        } else {
            result.add_success("Build verificado");
        }
        
        // 3. Verificar source
        if let Some(source) = attestations.iter()
            .find(|a| a.is_source())
        {
            if !self.verify_source(source)? {
                result.add_failure("Source invalido");
            } else {
                result.add_success("Source verificado");
            }
        }
        
        // 4. Verificar ambiente
        if let Some(env) = attestations.iter()
            .find(|a| a.is_environment())
        {
            if !self.verify_environment(env)? {
                result.add_failure("Ambiente invalido");
            } else {
                result.add_success("Ambiente verificado");
            }
        }
        
        // 5. Calcular nivel SLSA
        result.slsa_level = self.calculate_slsa_level(attestations);
        
        if result.slsa_level < self.min_slsa_level {
            result.add_failure(format!(
                "Nivel SLSA {} insuficiente (minimo: {})",
                result.slsa_level,
                self.min_slsa_level,
            ));
        }
        
        Ok(result)
    }
    
    fn verify_provenance(
        &self,
        attestation: &Attestation,
    ) -> Result<bool, VerificationError> {
        let provenance: ProvenanceAttestation = 
            serde_json::from_slice(&attestation.payload)?;
        
        // Verificar builder confiavel
        if !self.trusted_builders.contains(
            &provenance.predicate.builder.id
        ) {
            return Ok(false);
        }
        
        // Verificar source confiavel
        for material in &provenance.predicate.materials {
            if !self.trusted_sources.iter()
                .any(|s| material.uri.starts_with(s))
            {
                return Ok(false);
            }
        }
        
        // Verificar assinatura
        attestation.verify_signature()?;
        
        Ok(true)
    }
    
    fn calculate_slsa_level(
        &self,
        attestations: &[Attestation],
    ) -> u8 {
        let has_provenance = attestations.iter()
            .any(|a| a.is_provenance());
        let has_build = attestations.iter()
            .any(|a| a.is_build());
        let has_source = attestations.iter()
            .any(|a| a.is_source());
        let has_environment = attestations.iter()
            .any(|a| a.is_environment());
        
        if has_provenance && has_build && has_source && has_environment {
            4
        } else if has_provenance && has_build && has_source {
            3
        } else if has_provenance && has_build {
            2
        } else if has_provenance {
            1
        } else {
            0
        }
    }
}

#[derive(Debug)]
struct VerificationResult {
    successes: Vec<String>,
    failures: Vec<String>,
    slsa_level: u8,
}

impl VerificationResult {
    fn new() -> Self {
        Self {
            successes: Vec::new(),
            failures: Vec::new(),
            slsa_level: 0,
        }
    }
    
    fn is_valid(&self) -> bool {
        self.failures.is_empty()
    }
    
    fn add_success(&mut self, msg: String) {
        self.successes.push(msg);
    }
    
    fn add_failure(&mut self, msg: String) {
        self.failures.push(msg);
    }
}

#[derive(Debug)]
enum VerificationError {
    MissingAttestation(String),
    InvalidSignature,
    DeserializationError,
    BuilderNotTrusted,
    SourceNotTrusted,
}
```

### 11.8.8 Pipeline Completa de Atestação

```yaml
# Pipeline completa de atestacao para plugins Wasm
name: Attest Plugin

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  id-token: write
  attestations: write

jobs:
  build-and-attest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Historico completo para atestacao
      
      - name: Setup Rust
        uses: actions-rust-lang/setup-rust-toolchain@v1
        with:
          targets: wasm32-wasi
      
      - name: Build plugin
        run: cargo build --target wasm32-wasi --release
      
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: ./target/wasm32-wasi/release/plugin.wasm
          format: spdx-json
          output-file: plugin.spdx.json
      
      - name: Generate attestation
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: ./target/wasm32-wasi/release/plugin.wasm
      
      - name: Sign plugin
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign-blob \
            --bundle plugin.wasm.bundle \
            ./target/wasm32-wasi/release/plugin.wasm
        env:
          COSIGN_YES: "true"
      
      - name: Upload all artifacts
        uses: actions/upload-artifact@v4
        with:
          name: attested-plugin
          path: |
            target/wasm32-wasi/release/plugin.wasm
            plugin.wasm.bundle
            plugin.spdx.json
            .attestations/*
```

---

## 11.9 Segurança de Marketplace

Marketplaces de plugins são pontos centrais de distribuição que requerem segurança robusta para proteger tanto desenvolvedores quanto usuários finais.

### 11.9.1 Arquitetura de Marketplace de Plugins

```text
+-------------------------------------------------------------------+
|           Arquitetura Segura de Marketplace de Plugins             |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+                                             |
|  |   Desenvolvedor   |                                            |
|  +--------+---------+                                             |
|           |                                                       |
|           v (1. autenticacao + upload)                            |
|  +--------+---------+                                             |
|  |    API Gateway    |                                             |
|  |    (rate limit,   |                                             |
|  |     auth)         |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v (2. verificacao)                                      |
|  +--------+---------+                                             |
|  |  Validation       |                                             |
|  |  Service          |                                             |
|  |  - assinatura     |                                             |
|  |  - hash           |                                             |
|  |  - formato Wasm   |                                             |
|  |  - metadados      |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v (3. escaneamento)                                     |
|  +--------+---------+                                             |
|  |  Security Scan    |                                             |
|  |  - vulnerabilid.  |                                             |
|  |  - licencas       |                                             |
|  |  - malware        |                                             |
|  |  - permissoes     |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v (4. review)                                           |
|  +--------+---------+                                             |
|  |  Review Queue     |                                             |
|  |  (auto + manual)  |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v (5. publicacao)                                       |
|  +--------+---------+                                             |
|  |  Artifact Store   |                                             |
|  |  (content-        |                                             |
|  |   addressable)    |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           v (6. distribuicao)                                     |
|  +--------+---------+                                             |
|  |  CDN / Registry   |                                             |
|  +------------------+                                             |
|           |                                                       |
|           v                                                       |
|  +--------+---------+                                             |
|  |   Usuario Final   |                                             |
|  +------------------+                                             |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.9.2 Processos de Review para Plugins Publicados

```rust
// Sistema de review para plugins
struct PluginReviewPipeline {
    auto_checks: Vec<Box<dyn AutoCheck>>,
    manual_reviewers: Vec<Reviewer>,
    approval_threshold: usize,
}

trait AutoCheck {
    fn name(&self) -> &str;
    fn check(&self, plugin: &PluginSubmission) -> CheckResult;
}

struct SignatureCheck;
impl AutoCheck for SignatureCheck {
    fn name(&self) -> &str { "signature-verification" }
    
    fn check(&self, plugin: &PluginSubmission) -> CheckResult {
        match verify_signature(&plugin.wasm_bytes, &plugin.signature) {
            Ok(true) => CheckResult::Passed,
            Ok(false) => CheckResult::Failed(
                "Assinatura invalida".to_string()
            ),
            Err(e) => CheckResult::Error(e.to_string()),
        }
    }
}

struct VulnerabilityCheck;
impl AutoCheck for VulnerabilityCheck {
    fn name(&self) -> &str { "vulnerability-scan" }
    
    fn check(&self, plugin: &PluginSubmission) -> CheckResult {
        let sbom = generate_sbom(&plugin.wasm_bytes);
        let vulns = scan_vulnerabilities(&sbom);
        
        let critical = vulns.iter()
            .filter(|v| v.severity == Severity::Critical)
            .count();
        let high = vulns.iter()
            .filter(|v| v.severity == Severity::High)
            .count();
        
        if critical > 0 {
            CheckResult::Failed(format!(
                " {} vulnerabilidades criticas encontradas",
                critical
            ))
        } else if high > 0 {
            CheckResult::Warning(format!(
                " {} vulnerabilidades altas encontradas",
                high
            ))
        } else {
            CheckResult::Passed
        }
    }
}

struct PermissionCheck;
impl AutoCheck for PermissionCheck {
    fn name(&self) -> &str { "permission-audit" }
    
    fn check(&self, plugin: &PluginSubmission) -> CheckResult {
        let requested = extract_wasi_permissions(&plugin.wasm_bytes);
        let declared = &plugin.declared_permissions;
        
        // Verificar que permissoes reais == declaradas
        if requested != *declared {
            return CheckResult::Failed(format!(
                "Permissoes reais ({:?}) nao correspondem as declaradas ({:?})",
                requested,
                declared,
            ));
        }
        
        // Verificar permissoes perigosas
        let dangerous = vec![
            "wasi:filesystem.*",
            "wasi:network.*",
            "wasi:process.*",
        ];
        
        for perm in &requested {
            if dangerous.iter().any(|d| perm.matches_pattern(d)) {
                return CheckResult::Warning(format!(
                    "Permissao potencialmente perigosa: {:?}",
                    perm
                ));
            }
        }
        
        CheckResult::Passed
    }
}

struct MalwareCheck;
impl AutoCheck for MalwareCheck {
    fn name(&self) -> &str { "malware-detection" }
    
    fn check(&self, plugin: &PluginSubmission) -> CheckResult {
        // Analise de pads conhecidos de malware
        let suspicious_patterns = detect_suspicious_patterns(
            &plugin.wasm_bytes,
        );
        
        if !suspicious_patterns.is_empty() {
            return CheckResult::Failed(format(
                "Padroes suspeitos detectados: {:?}",
                suspicious_patterns,
            ));
        }
        
        // Verificar against YARA rules
        let yara_matches = scan_yara(&plugin.wasm_bytes);
        if !yara_matches.is_empty() {
            return CheckResult::Failed(format!(
                "YARA rules correspondem: {:?}",
                yara_matches,
            ));
        }
        
        CheckResult::Passed
    }
}

impl PluginReviewPipeline {
    fn review(
        &self,
        plugin: &PluginSubmission,
    ) -> ReviewResult {
        let mut results = Vec::new();
        let mut all_passed = true;
        
        // Executar checks automaticos
        for check in &self.auto_checks {
            let result = check.check(plugin);
            results.push(CheckEntry {
                checker: check.name().to_string(),
                result: result.clone(),
            });
            
            match &result {
                CheckResult::Failed(_) => all_passed = false,
                CheckResult::Warning(_) => {} // Warnings nao bloqueiam
                CheckResult::Passed => {}
                CheckResult::Error(_) => all_passed = false,
            }
        }
        
        // Se todos os checks automaticos passaram, enviar para review manual
        if all_passed {
            ReviewResult::PendingManualReview {
                auto_results: results,
                reviewers: self.manual_reviewers
                    .iter()
                    .map(|r| r.id.clone())
                    .collect(),
            }
        } else {
            ReviewResult::AutoRejected {
                results,
            }
        }
    }
}

enum CheckResult {
    Passed,
    Warning(String),
    Failed(String),
    Error(String),
}

enum ReviewResult {
    AutoRejected { results: Vec<CheckEntry> },
    PendingManualReview {
        auto_results: Vec<CheckEntry>,
        reviewers: Vec<String>,
    },
    Approved { approvals: Vec<String> },
    Rejected { reason: String },
}
```

### 11.9.3 Escaneamento Automatizado na Publicação

```yaml
# Pipeline de escaneamento automatizado para marketplace
name: Plugin Security Scan

on:
  repository_dispatch:
    types: [plugin-published]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        check: [signature, vulnerability, malware, license, permissions]
    
    steps:
      - name: Download plugin
        run: |
          PLUGIN_URL="${{ github.event.client_payload.plugin_url }}"
          PLUGIN_HASH="${{ github.event.client_payload.plugin_hash }}"
          curl -L -o plugin.wasm "$PLUGIN_URL"
          
          # Verificar hash
          echo "${PLUGIN_HASH}  plugin.wasm" | sha256sum -c
      
      - name: Run security check
        run: |
          case "${{ matrix.check }}" in
            signature)
              cosign verify-blob \
                --bundle plugin.wasm.bundle \
                --certificate-identity="${{ github.event.client_payload.author }}" \
                plugin.wasm
              ;;
            vulnerability)
              syft plugin.wasm -o spdx-json > plugin.spdx.json
              grype "sbom:plugin.spdx.json" --fail-on critical
              ;;
            malware)
              # YARA scan
              yara -r rules/ plugin.wasm
              # Entropy analysis
              python scripts/entropy_analysis.py plugin.wasm
              ;;
            license)
              syft plugin.wasm -o json | \
                jq -r '.packages[].licenseDeclared' | \
                python scripts/check_licenses.py
              ;;
            permissions)
              wasm-tools validate plugin.wasm
              python scripts/check_permissions.py plugin.wasm
              ;;
          esac
      
      - name: Report results
        if: failure()
        run: |
          curl -X POST "${{ secrets.WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d '{
              "plugin": "${{ github.event.client_payload.plugin_name }}",
              "check": "${{ matrix.check }}",
              "status": "failed",
              "details": "See workflow run for details"
            }'
```

### 11.9.4 Reputação e Ratings de Usuários

```rust
// Sistema de reputacao para desenvolvedores de plugins
struct ReputationSystem {
    reviews: Vec<PluginReview>,
    downloads: HashMap<String, DownloadStats>,
    security_events: Vec<SecurityEvent>,
}

#[derive(Debug)]
struct PluginReview {
    plugin_id: String,
    user_id: String,
    rating: u8,  // 1-5
    comment: String,
    verified_purchase: bool,
    timestamp: DateTime<Utc>,
}

#[derive(Debug)]
struct DownloadStats {
    plugin_id: String,
    total_downloads: u64,
    unique_users: u64,
    downloads_last_30d: u64,
    platforms: HashMap<String, u64>,
}

#[derive(Debug)]
enum SecurityEvent {
    VulnerabilityReported {
        plugin_id: String,
        severity: Severity,
        reported_at: DateTime<Utc>,
        fixed: bool,
    },
    MalwareDetected {
        plugin_id: String,
        detected_at: DateTime<Utc>,
        removed: bool,
    },
    PolicyViolation {
        plugin_id: String,
        violation_type: String,
        detected_at: DateTime<Utc>,
    },
}

impl ReputationSystem {
    fn calculate_reputation(&self, developer_id: &str) -> ReputationScore {
        let mut score = ReputationScore::new();
        
        // Fator 1: Qualidade dos plugins (ratings)
        let avg_rating = self.reviews.iter()
            .filter(|r| r.author_id == developer_id)
            .map(|r| r.rating as f64)
            .sum::<f64>()
            / self.reviews.iter()
                .filter(|r| r.author_id == developer_id)
                .count() as f64;
        
        score.quality = avg_rating / 5.0;  // Normalizar 0-1
        
        // Fator 2: Popularidade (downloads)
        let total_downloads: u64 = self.downloads.values()
            .filter(|d| d.author_id == developer_id)
            .map(|d| d.total_downloads)
            .sum();
        score.popularity = (total_downloads as f64).log10() / 10.0;
        
        // Fator 3: Seguranca (eventos negativos)
        let security_issues = self.security_events.iter()
            .filter(|e| e.author_id == developer_id)
            .filter(|e| !e.resolved())
            .count();
        score.security = 1.0 - (security_issues as f64 * 0.1);
        
        // Fator 4: Recencia (atividade recente)
        let last_update = self.get_last_update(developer_id);
        let days_since = Utc::now()
            .signed_duration_since(last_update)
            .num_days();
        score.recency = 1.0 - (days_since as f64 / 365.0).min(1.0);
        
        // Calcular score final (media ponderada)
        score.final_score = 
            score.quality * 0.4 +
            score.popularity * 0.2 +
            score.security * 0.3 +
            score.recency * 0.1;
        
        score
    }
    
    fn get_trust_level(&self, developer_id: &str) -> TrustLevel {
        let score = self.calculate_reputation(developer_id);
        
        match score.final_score {
            s if s >= 0.9 => TrustLevel::Trusted,
            s if s >= 0.7 => TrustLevel::Established,
            s if s >= 0.5 => TrustLevel::Regular,
            s if s >= 0.3 => TrustLevel::New,
            _ => TrustLevel::Unverified,
        }
    }
}

#[derive(Debug)]
struct ReputationScore {
    quality: f64,
    popularity: f64,
    security: f64,
    recency: f64,
    final_score: f64,
}

#[derive(Debug)]
enum TrustLevel {
    Trusted,       // Plugins publicados sem review manual
    Established,   // Review rapido (24h)
    Regular,       // Review padrao (48h)
    New,           // Review detalhada (72h)
    Unverified,    // Review completa + restrictions
}
```

### 11.9.5 Detecção de Malware em Repositórios

```rust
// Sistema de deteccao de malware para plugins Wasm
struct MalwareDetector {
    yara_rules: Vec<YaraRule>,
    entropy_analyzer: EntropyAnalyzer,
    pattern_detector: PatternDetector,
    behavioral_analyzer: BehavioralAnalyzer,
}

impl MalwareDetector {
    fn scan(&self, plugin: &[u8]) -> MalwareReport {
        let mut report = MalwareReport::new();
        
        // 1. Escaneamento YARA
        let yara_matches = self.yara_rules.iter()
            .filter(|rule| rule.matches(plugin))
            .map(|rule| YaraMatch {
                rule_name: rule.name.clone(),
                severity: rule.severity.clone(),
                description: rule.description.clone(),
            })
            .collect::<Vec<_>>();
        
        if !yara_matches.is_empty() {
            report.add_yara_matches(yara_matches);
        }
        
        // 2. Analise de entropia
        let high_entropy_sections = self.entropy_analyzer
            .analyze(plugin);
        
        for section in high_entropy_sections {
            if section.entropy > 7.5 {  // Entropia proxima de 8 = possivel ofuscacao/criptografia
                report.add_entropy_warning(section);
            }
        }
        
        // 3. Deteccao de padroes
        let suspicious_patterns = self.pattern_detector
            .detect(plugin);
        
        if !suspicious_patterns.is_empty() {
            report.add_pattern_matches(suspicious_patterns);
        }
        
        // 4. Analise comportamental (se executavel)
        if let Some(behavior) = self.behavioral_analyzer.analyze(plugin) {
            if behavior.has_suspicious_behavior() {
                report.add_behavioral_findings(behavior);
            }
        }
        
        report
    }
}

struct EntropyAnalyzer;

impl EntropyAnalyzer {
    fn analyze(&self, wasm_bytes: &[u8]) -> Vec<HighEntropySection> {
        let mut sections = Vec::new();
        
        // Analisar entropia por secao do Wasm
        // (Implementacao simplificada)
        let chunk_size = 1024;
        for (i, chunk) in wasm_bytes.chunks(chunk_size).enumerate() {
            let entropy = self.calculate_entropy(chunk);
            
            if entropy > 7.0 {
                sections.push(HighEntropySection {
                    offset: i * chunk_size,
                    length: chunk.len(),
                    entropy,
                });
            }
        }
        
        sections
    }
    
    fn calculate_entropy(&self, data: &[u8]) -> f64 {
        let mut freq = [0u64; 256];
        
        for &byte in data {
            freq[byte as usize] += 1;
        }
        
        let len = data.len() as f64;
        let mut entropy = 0.0;
        
        for &count in &freq {
            if count > 0 {
                let p = count as f64 / len;
                entropy -= p * p.log2();
            }
        }
        
        entropy
    }
}

#[derive(Debug)]
struct HighEntropySection {
    offset: usize,
    length: usize,
    entropy: f64,
}

#[derive(Debug)]
struct MalwareReport {
    yara_matches: Vec<YaraMatch>,
    entropy_warnings: Vec<HighEntropySection>,
    pattern_matches: Vec<PatternMatch>,
    behavioral_findings: Option<BehavioralAnalysis>,
    risk_score: f64,
    is_malicious: bool,
}

impl MalwareReport {
    fn new() -> Self {
        Self {
            yara_matches: Vec::new(),
            entropy_warnings: Vec::new(),
            pattern_matches: Vec::new(),
            behavioral_findings: None,
            risk_score: 0.0,
            is_malicious: false,
        }
    }
    
    fn calculate_risk_score(&mut self) {
        let mut score = 0.0;
        
        // YARA matches contribuem muito
        score += self.yara_matches.len() as f64 * 0.3;
        
        // Entropia alta contribui moderadamente
        score += self.entropy_warnings.len() as f64 * 0.1;
        
        // Padroes suspeitos contribuem
        score += self.pattern_matches.len() as f64 * 0.2;
        
        // Comportamento suspeito contribui muito
        if let Some(ref behavior) = self.behavioral_findings {
            if behavior.suspicious_syscalls > 0 {
                score += 0.4;
            }
        }
        
        self.risk_score = score.min(1.0);
        self.is_malicious = score > 0.7;
    }
}
```

### 11.9.6 Execução Sandbox de Plugins

```rust
// Execucao sandbox de plugins no marketplace para analise
struct PluginSandbox {
    runtime: WasmtimeRuntime,
    resource_limits: ResourceLimits,
    syscall_filter: SyscallFilter,
    network_policy: NetworkPolicy,
    monitor: BehaviorMonitor,
}

impl PluginSandbox {
    fn analyze_plugin(
        &self,
        plugin_bytes: &[u8],
    ) -> Result<SandboxAnalysis, SandboxError> {
        // 1. Configurar sandbox com restricoes maximas
        let config = Config::new()
            .epoch_interruption(true)
            .max_wasm_stack(1024 * 1024)  // 1MB stack
            .consume_fuel(true);
        
        let engine = Engine::new(&config)?;
        let module = Module::new(&engine, plugin_bytes)?;
        
        // 2. Configurar WASI com permissoes minimas
        let wasi = WasiCtxBuilder::new()
            .stdin(NullInputPipe::new())
            .stdout(NullOutputPipe::new())
            .stderr(NullOutputPipe::new())
            .build();
        
        let mut store = Store::new(&engine, wasi);
        store.limiter(|_| &mut StoreLimitsWithState {
            memory_limit: 10 * 1024 * 1024,  // 10MB
            table_elements: 1000,
        });
        
        store.set_fuel(1_000_000)?;  // Limitar computacao
        
        // 3. Carregar e instanciar
        let instance = Instance::new(&mut store, &module, &[])?;
        
        // 4. Monitorar comportamento
        let mut monitor = BehaviorMonitor::new();
        
        // 5. Executar com timeout
        let result = tokio::time::timeout(
            Duration::from_secs(30),
            self.run_instance(&mut store, &instance),
        ).await;
        
        // 6. Coletar metricas
        let metrics = SandboxMetrics {
            execution_time: monitor.execution_time,
            memory_used: monitor.memory_used,
            syscalls_made: monitor.syscalls_called,
            fuel_consumed: store.get_fuel()?,
            errors: monitor.errors,
        };
        
        Ok(SandboxAnalysis {
            result: result?,
            metrics,
            behavior: monitor.get_behavior_profile(),
        })
    }
}

struct BehaviorMonitor {
    syscalls_called: Vec<String>,
    files_accessed: Vec<String>,
    network_attempts: Vec<String>,
    errors: Vec<String>,
    execution_time: Duration,
    memory_used: usize,
}

impl BehaviorMonitor {
    fn new() -> Self {
        Self {
            syscalls_called: Vec::new(),
            files_accessed: Vec::new(),
            network_attempts: Vec::new(),
            errors: Vec::new(),
            execution_time: Duration::default(),
            memory_used: 0,
        }
    }
    
    fn get_behavior_profile(&self) -> BehaviorProfile {
        BehaviorProfile {
            suspicious_syscalls: self.detect_suspicious_syscalls(),
            unexpected_file_access: self.detect_unexpected_file_access(),
            network_activity: self.detect_network_activity(),
            overall_risk: self.calculate_risk(),
        }
    }
    
    fn detect_suspicious_syscalls(&self) -> Vec<String> {
        let suspicious = vec![
            "wasi:filesystem/open",
            "wasi:filesystem/write",
            "wasi:sockets/network",
            "wasi:process/spawn",
        ];
        
        self.syscalls_called.iter()
            .filter(|s| suspicious.iter().any(|sp| s.contains(sp)))
            .cloned()
            .collect()
    }
}
```

### 11.9.7 Resposta a Incidentes para Plugins Maliciosos

```rust
// Sistema de resposta a incidentes para plugins maliciosos
struct IncidentResponseSystem {
    alert_channel: AlertChannel,
    plugin_store: PluginStore,
    user_registry: UserRegistry,
    audit_log: AuditLog,
}

impl IncidentResponseSystem {
    async fn handle_malicious_plugin(
        &self,
        report: MalwareReport,
        plugin_id: &str,
    ) -> Result<IncidentResponse, IncidentError> {
        // 1. Registrar incidente
        let incident = self.create_incident(plugin_id, &report).await?;
        
        // 2. Remover plugin imediatamente
        self.plugin_store.remove_plugin(plugin_id).await?;
        
        // 3. Invalidar cache
        self.plugin_store.invalidate_cache(plugin_id).await?;
        
        // 4. Notificar usuarios afetados
        let affected_users = self.user_registry
            .get_users_with_plugin(plugin_id)
            .await?;
        
        for user in &affected_users {
            self.alert_channel.send(Alert {
                user_id: user.id.clone(),
                severity: AlertSeverity::Critical,
                title: "Plugin Malicioso Removido".to_string(),
                message: format!(
                    "O plugin '{}' foi removido por motivos de seguranca. \
                     Por favor, remova-o do seu sistema.",
                    plugin_id
                ),
                action_required: true,
            }).await?;
        }
        
        // 5. Revogar chaves de assinatura se necessario
        if report.is_key_compromised() {
            self.revoke_signing_keys(plugin_id).await?;
        }
        
        // 6. Atualizar listas de blocklist
        self.update_blocklist(plugin_id).await?;
        
        // 7. Gerar relatorio para audit
        self.generate_incident_report(&incident).await?;
        
        Ok(IncidentResponse {
            incident_id: incident.id,
            actions_taken: vec![
                "Plugin removido".to_string(),
                format!("{} usuarios notificados", affected_users.len()),
                "Cache invalidado".to_string(),
                "Blocklist atualizada".to_string(),
            ],
            timeline: incident.timeline,
        })
    }
    
    async fn handle_vulnerability_report(
        &self,
        report: VulnerabilityReport,
    ) -> Result<VulnerabilityResponse, IncidentError> {
        // 1. Validar report
        self.validate_vulnerability_report(&report).await?;
        
        // 2. Avaliar severidade
        let severity = self.assess_severity(&report).await?;
        
        match severity {
            Severity::Critical => {
                // Acao imediata
                self.plugin_store quarantine_plugin(
                    &report.plugin_id
                ).await?;
                
                self.alert_channel.broadcast(Alert {
                    severity: AlertSeverity::Critical,
                    title: "Vulnerabilidade Critica".to_string(),
                    message: report.summary.clone(),
                }).await?;
            }
            Severity::High => {
                // Notificar desenvolvedor
                self.notify_developer(
                    &report.plugin_id,
                    &report,
                ).await?;
                
                // Dar prazo de 48h para correcao
                self.schedule_deadline(
                    &report.plugin_id,
                    Duration::from_hours(48),
                ).await?;
            }
            Severity::Medium | Severity::Low => {
                // Criar issue para track
                self.create_issue(&report).await?;
            }
        }
        
        Ok(VulnerabilityResponse {
            severity,
            actions_taken: Vec::new(),
        })
    }
}
```

### 11.9.8 Modelos de Governança de Marketplace

```text
+-------------------------------------------------------------------+
|          Modelos de Governanca de Marketplace                       |
+-------------------------------------------------------------------+
|                                                                   |
|  MODELO 1: Centralizado (Apple App Store)                         |
|  - Review manual obrigatorio                                      |
|  - Controle total sobre publicacoes                               |
|  - Alta seguranca, baixa agilidade                                |
|  - Adequado para: ecossistemas criticos                           |
|                                                                   |
|  MODELO 2: Comunitario (npm)                                      |
|  - Publicacao aberta, verificacao a posteriori                     |
|  - Alta agilidade, seguranca variavel                             |
|  - Adequado: ecossistemas maduros com ferramentas de audit        |
|                                                                   |
|  MODELO 3: Hibrido (VS Code Marketplace)                          |
|  - Publicacao verificada para publishers confiaveis               |
|  - Review manual para novos publishers                            |
|  - Balance entre seguranca e agilidade                            |
|  - Adequado: maioria dos ecossistemas                             |
|                                                                   |
|  MODELO 4: Descentralizado (IPFS + assinatura)                    |
|  - Sem centralizacao de confianca                                 |
|  - Confianca baseada em reputacao e criptografia                  |
|  - Maxima descentralizacao                                        |
|  - Adequado: ecossistemas Web3/blockchain                         |
|                                                                   |
|  RECOMENDACAO:                                                    |
|  - Comecar com Modelo 3 (hibrido)                                 |
|  - Evoluir para Modelo 4 conforme maturidade                      |
|  - Investir em automatizacao de verificacao                        |
|                                                                   |
+-------------------------------------------------------------------+
```

---

## 11.10 Estratégias de Atualização

Estratégias de atualização definem como novas versões de plugins são distribuídas e instaladas. Uma estratégia adequada deve equilibrar segurança, estabilidade e conveniência.

### 11.10.1 Atualização Automática vs Manual

```text
+-------------------------------------------------------------------+
|          Atualizacao Automatica vs Manual                          |
+-------------------------------------------------------------------+
|                                                                   |
|  ATUALIZACAO AUTOMATICA:                                          |
|                                                                   |
|  + Vantagens:                                                     |
|  - Correcoes de seguranca aplicadas rapidamente                   |
|  - Menos trabalho para o administrador                            |
|  - Mantem plugins atualizados                                     |
|                                                                   |
|  - Riscos:                                                        |
|  - Atualizacao pode quebrar funcionalidade                        |
|  - Atualizacao maliciosa pode ser aplicada                        |
|  - Perda de controle sobre versoes                                |
|  - Dificil de audit                                               |
|                                                                   |
|  ATUALIZACAO MANUAL:                                              |
|                                                                   |
|  + Vantagens:                                                     |
|  - Controle total sobre versoes                                   |
|  - Capacidade de testar antes de aplicar                          |
|  - Facil de audit e rollback                                      |
|                                                                   |
|  - Riscos:                                                        |
|  - Correcoes de seguranca podem ser atrasadas                     |
|  - Plugins podem ficar desatualizados                             |
|  - Trabalho administrativo                                        |
|                                                                   |
|  RECOMENDACAO:                                                    |
|  - Atualizacao AUTOMATICA para patches de seguranca               |
|  - Atualizacao SEMI-AUTOMATICA para minor versions                |
|  - Atualizacao MANUAL para major versions                         |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Configuracao de politica de atualizacao
struct UpdatePolicy {
    security_updates: UpdateMode,
    minor_updates: UpdateMode,
    major_updates: UpdateMode,
    notification_channels: Vec<NotificationChannel>,
    test_before_apply: bool,
    rollback_window: Duration,
}

enum UpdateMode {
    Automatic,        // Aplica sem intervencao
    SemiAutomatic,    // Notifica e aplica apos delay
    Manual,           // Notifica, espera aprovacao
    Disabled,         // Nao atualiza automaticamente
}

impl UpdatePolicy {
    fn default() -> Self {
        Self {
            security_updates: UpdateMode::Automatic,
            minor_updates: UpdateMode::SemiAutomatic,
            major_updates: UpdateMode::Manual,
            notification_channels: vec![
                NotificationChannel::Email,
                NotificationChannel::Slack,
            ],
            test_before_apply: true,
            rollback_window: Duration::from_hours(24),
        }
    }
    
    fn should_update(
        &self,
        current: &Version,
        latest: &Version,
        is_security_fix: bool,
    ) -> UpdateDecision {
        if is_security_fix {
            return match &self.security_updates {
                UpdateMode::Automatic => UpdateDecision::ApplyNow,
                UpdateMode::SemiAutomatic => UpdateDecision::ApplyAfterDelay(
                    Duration::from_minutes(30),
                ),
                UpdateMode::Manual => UpdateDecision::WaitForApproval,
                UpdateMode::Disabled => UpdateDecision::Skip,
            };
        }
        
        let change = current.major_change(latest);
        
        match change {
            VersionChange::Major => match &self.major_updates {
                UpdateMode::Automatic => UpdateDecision::ApplyNow,
                UpdateMode::SemiAutomatic => UpdateDecision::ApplyAfterDelay(
                    Duration::from_hours(24),
                ),
                UpdateMode::Manual => UpdateDecision::WaitForApproval,
                UpdateMode::Disabled => UpdateDecision::Skip,
            },
            VersionChange::Minor => match &self.minor_updates {
                UpdateMode::Automatic => UpdateDecision::ApplyNow,
                UpdateMode::SemiAutomatic => UpdateDecision::ApplyAfterDelay(
                    Duration::from_hours(1),
                ),
                UpdateMode::Manual => UpdateDecision::WaitForApproval,
                UpdateMode::Disabled => UpdateDecision::Skip,
            },
            VersionChange::Patch => UpdateDecision::ApplyNow,
        }
    }
}

enum UpdateDecision {
    ApplyNow,
    ApplyAfterDelay(Duration),
    WaitForApproval,
    Skip,
}
```

### 11.10.2 Canais de Atualização (Stable, Beta, Nightly)

```yaml
# Configuracao de canais de atualizacao
update_channels:
  stable:
    description: "Versoes testadas e aprovadas para producao"
    source: "registry://plugins.example.com/stable"
    auto_update: true
    security_auto_update: true
    requires_approval: false
    
  beta:
    description: "Versoes em teste, podem conter bugs"
    source: "registry://plugins.example.com/beta"
    auto_update: false
    security_auto_update: true
    requires_approval: true
    
  nightly:
    description: "Builds diarios, nao estaveis"
    source: "registry://plugins.example.com/nightly"
    auto_update: false
    security_auto_update: false
    requires_approval: true

# Configuracao por plugin
plugins:
  auth-plugin:
    channel: stable
    pinned_version: "1.2.3"
    allow_channel_change: false
    
  analytics-plugin:
    channel: beta
    allow_channel_change: true
    
  experimental-plugin:
    channel: nightly
    allow_channel_change: true
```

### 11.10.3 Canary Deployments para Plugins

```rust
// Canary deployment para plugins
struct CanaryDeployment {
    plugin_id: String,
    new_version: String,
    canary_percentage: f64,
    metrics_threshold: CanaryThreshold,
    duration: Duration,
}

#[derive(Debug)]
struct CanaryThreshold {
    max_error_rate: f64,      // 0.01 = 1%
    max_latency_increase: f64, // 0.5 = 50% increase
    max_memory_increase: f64,  // 0.3 = 30% increase
}

impl CanaryDeployment {
    async fn execute(
        &self,
        plugin_manager: &PluginManager,
    ) -> Result<CanaryResult, DeploymentError> {
        // 1. Iniciar canary com percentual baixo
        let initial_percentage = 5.0;  // 5% dos usuarios
        
        plugin_manager.update_canary_percentage(
            &self.plugin_id,
            initial_percentage,
        ).await?;
        
        // 2. Monitorar metricas
        let metrics = self.monitor_metrics(
            plugin_manager,
            self.duration,
        ).await?;
        
        // 3. Avaliar metricas
        if metrics.error_rate > self.metrics_threshold.max_error_rate {
            // Rollback imediato
            plugin_manager.rollback_canary(&self.plugin_id).await?;
            
            return Ok(CanaryResult::Failed {
                reason: format!(
                    "Error rate {}% excede threshold {}%",
                    metrics.error_rate * 100.0,
                    self.metrics_threshold.max_error_rate * 100.0,
                ),
                metrics,
            });
        }
        
        // 4. Aumentar percentual gradualmente
        let stages = [10.0, 25.0, 50.0, 75.0, 100.0];
        
        for &percentage in &stages {
            plugin_manager.update_canary_percentage(
                &self.plugin_id,
                percentage,
            ).await?;
            
            let stage_metrics = self.monitor_metrics(
                plugin_manager,
                Duration::from_hours(1),
            ).await?;
            
            if stage_metrics.error_rate > self.metrics_threshold.max_error_rate {
                plugin_manager.rollback_canary(&self.plugin_id).await?;
                
                return Ok(CanaryResult::Failed {
                    reason: format!(
                        "Falha no estagio {}%",
                        percentage,
                    ),
                    metrics: stage_metrics,
                });
            }
        }
        
        // 5. Promover para 100%
        plugin_manager.promote_canary(&self.plugin_id).await?;
        
        Ok(CanaryResult::Success {
            final_percentage: 100.0,
            metrics,
        })
    }
    
    async fn monitor_metrics(
        &self,
        plugin_manager: &PluginManager,
        duration: Duration,
    ) -> Result<CanaryMetrics, MonitoringError> {
        let start = Utc::now();
        let mut metrics = CanaryMetrics::new();
        
        while Utc::now() - start < duration {
            let snapshot = plugin_manager.get_metrics(&self.plugin_id).await?;
            
            metrics.update(snapshot);
            
            // Verificar thresholds
            if metrics.error_rate > self.metrics_threshold.max_error_rate {
                return Ok(metrics);
            }
            
            tokio::time::sleep(Duration::from_secs(30)).await;
        }
        
        Ok(metrics)
    }
}
```

### 11.10.4 Mecanismos de Rollback

```rust
// Sistema de rollback para plugins
struct RollbackManager {
    snapshots: HashMap<String, Vec<PluginSnapshot>>,
    max_snapshots: usize,
}

#[derive(Clone)]
struct PluginSnapshot {
    plugin_id: String,
    version: String,
    wasm_bytes: Vec<u8>,
    hash: String,
    created_at: DateTime<Utc>,
    reason: SnapshotReason,
}

enum SnapshotReason {
    PreUpdate,          // Snapshot antes de atualizacao
    PostUpdate,         // Snapshot apos atualizacao (para rollback)
    Scheduled,          // Snapshot programado
    Manual,             // Snapshot manual
}

impl RollbackManager {
    fn create_snapshot(
        &mut self,
        plugin_id: &str,
        reason: SnapshotReason,
    ) -> Result<PluginSnapshot, RollbackError> {
        let plugin = self.load_plugin(plugin_id)?;
        let snapshot = PluginSnapshot {
            plugin_id: plugin_id.to_string(),
            version: plugin.version.clone(),
            wasm_bytes: plugin.wasm_bytes.clone(),
            hash: plugin.hash.clone(),
            created_at: Utc::now(),
            reason,
        };
        
        // Armazenar snapshot
        self.snapshots
            .entry(plugin_id.to_string())
            .or_default()
            .push(snapshot.clone());
        
        // Manter apenas os N snapshots mais recentes
        if let Some(snapshots) = self.snapshots.get_mut(plugin_id) {
            if snapshots.len() > self.max_snapshots {
                snapshots.drain(0..snapshots.len() - self.max_snapshots);
            }
        }
        
        Ok(snapshot)
    }
    
    fn rollback(
        &mut self,
        plugin_id: &str,
        target_version: Option<&str>,
    ) -> Result<RollbackResult, RollbackError> {
        let snapshots = self.snapshots.get(plugin_id)
            .ok_or(RollbackError::NoSnapshots)?;
        
        let snapshot = match target_version {
            Some(version) => snapshots.iter()
                .rev()
                .find(|s| s.version == version)
                .ok_or(RollbackError::VersionNotFound)?,
            None => snapshots.last()
                .ok_or(RollbackError::NoSnapshots)?,
        };
        
        // Restaurar plugin
        self.restore_plugin(plugin_id, snapshot)?;
        
        // Criar snapshot do estado atual (antes do rollback)
        self.create_snapshot(plugin_id, SnapshotReason::PreUpdate)?;
        
        Ok(RollbackResult {
            plugin_id: plugin_id.to_string(),
            rolled_back_to: snapshot.version.clone(),
            rolled_back_from: self.get_current_version(plugin_id)?,
            timestamp: Utc::now(),
        })
    }
    
    fn restore_plugin(
        &self,
        plugin_id: &str,
        snapshot: &PluginSnapshot,
    ) -> Result<(), RollbackError> {
        // Verificar integridade do snapshot
        let hash = Sha256::digest(&snapshot.wasm_bytes);
        if hex::encode(hash) != snapshot.hash {
            return Err(RollbackError::SnapshotCorrupted);
        }
        
        // Restaurar bytes do plugin
        std::fs::write(
            self.get_plugin_path(plugin_id),
            &snapshot.wasm_bytes,
        )?;
        
        Ok(())
    }
    
    fn list_rollback_points(
        &self,
        plugin_id: &str,
    ) -> Vec<RollbackPoint> {
        self.snapshots.get(plugin_id)
            .map(|snapshots| snapshots.iter()
                .rev()
                .map(|s| RollbackPoint {
                    version: s.version.clone(),
                    timestamp: s.created_at,
                    reason: format!("{:?}", s.reason),
                })
                .collect()
            )
            .unwrap_or_default()
    }
}

#[derive(Debug)]
struct RollbackResult {
    plugin_id: String,
    rolled_back_to: String,
    rolled_back_from: String,
    timestamp: DateTime<Utc>,
}

#[derive(Debug)]
struct RollbackPoint {
    version: String,
    timestamp: DateTime<Utc>,
    reason: String,
}

#[derive(Debug)]
enum RollbackError {
    NoSnapshots,
    VersionNotFound,
    SnapshotCorrupted,
    IoError(std::io::Error),
}
```

### 11.10.5 Atualização Delta para Módulos Wasm

```rust
// Delta updates para módulos Wasm
// Reduz o tamanho da atualizacao enviando apenas as diferencas

struct DeltaUpdateSystem {
    chunk_size: usize,
    compression: CompressionAlgorithm,
}

enum CompressionAlgorithm {
    Zstd,
    Lz4,
    Gzip,
}

impl DeltaUpdateSystem {
    fn compute_delta(
        &self,
        old_module: &[u8],
        new_module: &[u8],
    ) -> DeltaUpdate {
        // Usar algoritmo de diff binario (bsdiff/xdelta)
        let delta = compute_bsdiff(old_module, new_module);
        
        // Comprimir o delta
        let compressed = self.compress(&delta);
        
        DeltaUpdate {
            old_hash: sha256_hex(old_module),
            new_hash: sha256_hex(new_module),
            delta_data: compressed,
            delta_size: compressed.len(),
            full_size: new_module.len(),
            compression_ratio: compressed.len() as f64 / new_module.len() as f64,
        }
    }
    
    fn apply_delta(
        &self,
        old_module: &[u8],
        delta: &DeltaUpdate,
    ) -> Result<Vec<u8>, DeltaError> {
        // Verificar hash do modulo antigo
        let old_hash = sha256_hex(old_module);
        if old_hash != delta.old_hash {
            return Err(DeltaError::HashMismatch {
                expected: delta.old_hash.clone(),
                actual: old_hash,
            });
        }
        
        // Descomprimir o delta
        let delta_data = self.decompress(&delta.delta_data)?;
        
        // Aplicar delta
        let new_module = apply_bsdiff(old_module, &delta_data)?;
        
        // Verificar hash do modulo novo
        let new_hash = sha256_hex(&new_module);
        if new_hash != delta.new_hash {
            return Err(DeltaError::IntegrityFailure);
        }
        
        Ok(new_module)
    }
    
    fn compress(&self, data: &[u8]) -> Vec<u8> {
        match self.compression {
            CompressionAlgorithm::Zstd => {
                zstd::encode_all(data, 3).unwrap()
            }
            CompressionAlgorithm::Lz4 => {
                lz4_flex::compress_prepend_size(data)
            }
            CompressionAlgorithm::Gzip => {
                let mut encoder = GzEncoder::new(
                    Vec::new(),
                    Compression::default(),
                );
                encoder.write_all(data).unwrap();
                encoder.finish().unwrap()
            }
        }
    }
    
    fn decompress(&self, data: &[u8]) -> Result<Vec<u8>, DeltaError> {
        match self.compression {
            CompressionAlgorithm::Zstd => {
                zstd::decode_all(data).map_err(|e| DeltaError::DecompressionFailed(e.to_string()))
            }
            CompressionAlgorithm::Lz4 => {
                lz4_flex::decompress_size_prepended(data)
                    .map_err(|e| DeltaError::DecompressionFailed(e.to_string()))
            }
            CompressionAlgorithm::Gzip => {
                let mut decoder = GzDecoder::new(data);
                let mut output = Vec::new();
                decoder.read_to_end(&mut output)
                    .map_err(|e| DeltaError::DecompressionFailed(e.to_string()))?;
                Ok(output)
            }
        }
    }
}

#[derive(Debug)]
struct DeltaUpdate {
    old_hash: String,
    new_hash: String,
    delta_data: Vec<u8>,
    delta_size: usize,
    full_size: usize,
    compression_ratio: f64,
}

#[derive(Debug)]
enum DeltaError {
    HashMismatch { expected: String, actual: String },
    IntegrityFailure,
    DecompressionFailed(String),
    PatchFailed(String),
}
```

### 11.10.6 Pipeline de Verificação de Atualização

```rust
// Pipeline de verificacao antes de aplicar atualizacao
struct UpdateVerificationPipeline {
    signature_verifier: SignatureVerifier,
    vulnerability_scanner: VulnerabilityScanner,
    compatibility_checker: CompatibilityChecker,
    sandbox_tester: SandboxTester,
}

impl UpdateVerificationPipeline {
    async fn verify_update(
        &self,
        current: &Plugin,
        update: &PluginUpdate,
    ) -> Result<VerificationResult, UpdateVerificationError> {
        let mut result = VerificationResult::new();
        
        // 1. Verificar assinatura da atualizacao
        match self.signature_verifier.verify(
            &update.wasm_bytes,
            &update.signature,
        ).await {
            Ok(true) => result.add_passed("Assinatura verificada"),
            Ok(false) => return Err(UpdateVerificationError::InvalidSignature),
            Err(e) => return Err(UpdateVerificationError::SignatureError(e)),
        }
        
        // 2. Verificar vulnerabilidades
        let vulns = self.vulnerability_scanner.scan(&update.wasm_bytes).await;
        let critical_vulns: Vec<_> = vulns.iter()
            .filter(|v| v.severity == Severity::Critical)
            .collect();
        
        if !critical_vulns.is_empty() {
            return Err(UpdateVerificationError::CriticalVulnerability {
                count: critical_vulns.len(),
            });
        }
        
        result.add_passed(format!(
            "{} vulnerabilidades (0 criticas)",
            vulns.len()
        ));
        
        // 3. Verificar compatibilidade
        let compat = self.compatibility_checker.check(
            current,
            update,
        ).await?;
        
        if !compat.is_compatible() {
            return Err(UpdateVerificationError::Incompatible {
                reasons: compat.incompatibility_reasons(),
            });
        }
        
        result.add_passed("Compatibilidade verificada");
        
        // 4. Testar em sandbox
        let test_result = self.sandbox_tester.test(
            &update.wasm_bytes,
            &update.test_config,
        ).await?;
        
        if !test_result.all_passed() {
            return Err(UpdateVerificationError::SandboxTestFailed {
                failures: test_result.failures(),
            });
        }
        
        result.add_passed("Testes sandbox passaram");
        
        Ok(result)
    }
}

#[derive(Debug)]
struct VerificationResult {
    passed: Vec<String>,
    warnings: Vec<String>,
}

impl VerificationResult {
    fn add_passed(&mut self, msg: String) {
        self.passed.push(msg);
    }
    
    fn add_warning(&mut self, msg: String) {
        self.warnings.push(msg);
    }
}

#[derive(Debug)]
enum UpdateVerificationError {
    InvalidSignature,
    SignatureError(anyhow::Error),
    CriticalVulnerability { count: usize },
    Incompatible { reasons: Vec<String> },
    SandboxTestFailed { failures: Vec<String> },
}
```

---

## 11.11 Pipeline Segura Completa de Plugins

Esta seção apresenta uma pipeline completa e integrada para desenvolvimento, distribuição e execução segura de plugins Wasm.

### 11.11.1 Arquitetura da Pipeline End-to-End

```text
+-------------------------------------------------------------------+
|        Pipeline Segura Completa de Plugins Wasm                     |
+-------------------------------------------------------------------+
|                                                                   |
|  ESTACAO DE DESENVOLVIMENTO                                       |
|  +-------------------------------------------------------------+ |
|  | 1. Codigo-fonte versionado (git signed commits)             | |
|  | 2. Hooks pre-commit (lint, test, format)                    | |
|  | 3. Branch protection + code review                          | |
|  +-----------------------------+-------------------------------+ |
|                                |                                 |
|                                v                                 |
|  AMBIENTE DE BUILD                                            |
|  +-------------------------------------------------------------+ |
|  | 4. Build hermetico (sem rede)                               | |
|  | 5. Build reprodutivel (deterministic)                       | |
|  | 6. SBOM gerado automaticamente                              | |
|  | 7. Atestacao de proveniencia                                | |
|  | 8. Assinatura com cosign/sigstore                           | |
|  +-----------------------------+-------------------------------+ |
|                                |                                 |
|                                v                                 |
|  REGISTRY / MARKETPLACE                                       |
|  +-------------------------------------------------------------+ |
|  | 9. Verificacao de assinatura                                | |
|  | 10. Escaneamento de vulnerabilidades                        | |
|  | 11. Verificacao de licencas                                 | |
|  | 12. Deteccao de malware                                     | |
|  | 13. Review automatico + manual                              | |
|  | 14. Registro em log de transparencia                        | |
|  +-----------------------------+-------------------------------+ |
|                                |                                 |
|                                v                                 |
|  DISTRIBUICAO                                                  |
|  +-------------------------------------------------------------+ |
|  | 15. CDN com TLS                                            | |
|  | 16. Mirror verification                                    | |
|  | 17. Content-addressable storage                             | |
|  +-----------------------------+-------------------------------+ |
|                                |                                 |
|                                v                                 |
|  HOST (APLICACAO)                                            |
|  +-------------------------------------------------------------+ |
|  | 18. Verificacao pre-execucao                               | |
|  | 19. Configuracao de permissoes WASI                         | |
|  | 20. Carregamento em sandbox                                | |
|  | 21. Monitoramento de comportamento                          | |
|  | 22. Auditoria continua                                     | |
|  +-----------------------------+-------------------------------+ |
|                                |                                 |
|                                v                                 |
|  RESPONSA A INCIDENTES                                        |
|  +-------------------------------------------------------------+ |
|  | 23. Deteccao de comportamento anormal                       | |
|  | 24. Isolamento automatico                                   | |
|  | 25. Notificacao de usuarios                                 | |
|  | 26. Rollback automatico                                    | |
|  | 27. Analise forense                                         | |
|  +-------------------------------------------------------------+ |
|                                                                   |
+-------------------------------------------------------------------+
```

### 11.11.2 Segurança da Estação de Desenvolvimento

```bash
#!/bin/bash
# Setup de estacao de desenvolvimento segura para plugins Wasm

set -euo pipefail

echo "=== Configurando estacao de desenvolvimento segura ==="

# 1. Configurar git para commits assinados
git config --global commit.gpgsign true
git config --global tag.gpgsign true
git config --global user.signingkey "YOUR_GPG_KEY_ID"

# 2. Instalar hooks de pre-commit
cat > .git/hooks/pre-commit << 'HOOKEOF'
#!/bin/bash
# Pre-commit hook para plugins Wasm

set -euo pipefail

echo "=== Executando pre-commit checks ==="

# Verificar se nao ha secrets hardcoded
echo "Verificando secrets..."
if grep -rn "password\|secret\|api_key\|token" \
    --include="*.rs" --include="*.toml" --include="*.yaml" \
    | grep -v "test\|example\|placeholder"; then
    echo "ERRO: Possivel secret encontrado no codigo"
    exit 1
fi

# Verificar formato
echo "Verificando formato..."
cargo fmt -- --check

# Verificar lint
echo "Verificando lint..."
cargo clippy -- -D warnings

# Rodar testes
echo "Rodando testes..."
cargo test

echo "=== Pre-commit checks passaram ==="
HOOKEOF
chmod +x .git/hooks/pre-commit

# 3. Configurar build reprodutivel
cat > .cargo/config.toml << 'TOMLEOF'
[target.wasm32-wasi]
# Flags de seguranca para Wasm
rustflags = [
    "-C", "link-arg=-zstack-size=1048576",
    "-C", "link-arg=--initial-memory=65536",
    "-C", "link-arg=--max-memory=16777216",
]
TOMLEOF

# 4. Configurar dependencias fixas
cat > rust-toolchain.toml << 'TOOLCHaineof'
[toolchain]
channel = "1.75.0"
targets = ["wasm32-wasi"]
components = ["rustfmt", "clippy"]
TOOLCHaineof

echo "=== Estacao de desenvolvimento configurada ==="
```

### 11.11.3 Endurecimento do Ambiente de Build

```yaml
# GitHub Actions: Build environment hardening
name: Secure Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  attestations: write

jobs:
  secure-build:
    runs-on: ubuntu-latest
    container:
      image: rust:1.75.0-slim-bookworm
      options: --read-only --tmpfs /tmp:size=1G --security-opt no-new-privileges
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false  # Nao persistir credenciais
      
      - name: Verify commit signature
        run: |
          git log --format='%H %G?' -1 | read hash status
          if [ "$status" != "G" ] && [ "$status" != "U" ]; then
            echo "ERRO: Commit nao assinado"
            exit 1
          fi
      
      - name: Build in hermetic environment
        run: |
          # Build sem acesso a rede
          cargo build --target wasm32-wasi --release \
            --frozen  # Usar cargo.lock congelado
      
      - name: Generate SBOM
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
          syft ./target/wasm32-wasi/release/plugin.wasm \
            -o spdx-json > plugin.spdx.json
      
      - name: Generate attestation
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: ./target/wasm32-wasi/release/plugin.wasm
      
      - name: Sign with cosign
        run: |
          curl -sSfL https://raw.githubusercontent.com/sigstore/cosign/main/install.sh | sh -s --
          cosign sign-blob --bundle plugin.wasm.bundle \
            ./target/wasm32-wasi/release/plugin.wasm
        env:
          COSIGN_YES: "true"
      
      - name: Run vulnerability scan
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s --
          grype sbom:plugin.spdx.json --fail-on critical
      
      - name: Verify reproducibility
        run: |
          # Verificar que o build e reprodutivel
          sha256sum ./target/wasm32-wasi/release/plugin.wasm > plugin.sha256
          echo "Hash do build: $(cat plugin.sha256)"
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: secure-build
          path: |
            target/wasm32-wasi/release/plugin.wasm
            plugin.wasm.bundle
            plugin.spdx.json
            plugin.sha256
          retention-days: 90
```

### 11.11.4 Integração de Assinatura e Atestação

```rust
// Pipeline integrada de assinatura e atestacao
struct SecureBuildPipeline {
    source_verifier: SourceVerifier,
    build_executor: BuildExecutor,
    sbom_generator: SBOMGenerator,
    attestation_generator: AttestationGenerator,
    signer: PluginSigner,
    publisher: PluginPublisher,
}

impl SecureBuildPipeline {
    async fn execute(
        &self,
        source: &SourceRepository,
        config: &BuildConfig,
    ) -> Result<PublishedPlugin, PipelineError> {
        // 1. Verificar source
        let source_info = self.source_verifier.verify(source).await?;
        
        // 2. Executar build
        let build_result = self.build_executor.build(
            source,
            config,
        ).await?;
        
        // 3. Gerar SBOM
        let sbom = self.sbom_generator.generate(
            &build_result.wasm_bytes,
        ).await?;
        
        // 4. Gerar atestacoes
        let attestations = self.attestation_generator.generate(
            &build_result,
            &sbom,
            &source_info,
        ).await?;
        
        // 5. Assinar
        let signature = self.signer.sign(
            &build_result.wasm_bytes,
            &attestations,
        ).await?;
        
        // 6. Publicar
        let published = self.publisher.publish(
            &build_result.wasm_bytes,
            &sbom,
            &attestations,
            &signature,
        ).await?;
        
        Ok(published)
    }
}

struct PublishedPlugin {
    plugin_id: String,
    version: String,
    wasm_url: String,
    wasm_hash: String,
    sbom_url: String,
    attestations_url: String,
    signature_url: String,
    published_at: DateTime<Utc>,
}
```

### 11.11.5 Segurança do Canal de Distribuição

```rust
// Seguranca do canal de distribuicao
struct SecureDistribution {
    cdn_config: CDNConfig,
    mirrror_verifier: MirrorVerifier,
    content_store: ContentAddressableStore,
}

struct CDNConfig {
    base_url: String,
    require_tls: bool,
    min_tls_version: TlsVersion,
    certificate_pinning: Option<CertificatePin>,
    rate_limiting: RateLimit,
}

impl SecureDistribution {
    async fn distribute(
        &self,
        plugin: &PublishedPlugin,
    ) -> Result<DistributionResult, DistributionError> {
        // 1. Verificar TLS
        if self.cdn_config.require_tls {
            self.verify_tls_connection().await?;
        }
        
        // 2. Verificar certificate pinning
        if let Some(pin) = &self.cdn_config.certificate_pinning {
            self.verify_certificate_pin(pin).await?;
        }
        
        // 3. Upload para CDN
        let cdn_result = self.upload_to_cdn(plugin).await?;
        
        // 4. Verificar em mirrors
        for mirror in &self.mirrors {
            let mirror_result = self.verify_mirror(
                mirror,
                plugin,
            ).await?;
            
            if !mirror_result.verified {
                return Err(DistributionError::MirrorVerificationFailed {
                    mirror: mirror.url.clone(),
                });
            }
        }
        
        // 5. Armazenar em CAS
        self.content_store.store(
            &plugin.wasm_bytes,
            &plugin.wasm_hash,
        ).await?;
        
        Ok(DistributionResult {
            cdn_url: cdn_result.url,
            mirrors_verified: self.mirrors.len(),
            cas_stored: true,
        })
    }
}
```

### 11.11.6 Verificação em Runtime

```rust
// Verificacao completa em runtime
struct RuntimeVerifier {
    signature_verifier: SignatureVerifier,
    hash_verifier: HashVerifier,
    attestation_verifier: AttestationVerifier,
    permission_enforcer: PermissionEnforcer,
    behavior_monitor: BehaviorMonitor,
}

impl RuntimeVerifier {
    async fn verify_and_load(
        &self,
        plugin_source: &PluginSource,
        config: &RuntimeConfig,
    ) -> Result<VerifiedPlugin, VerificationError> {
        // 1. Baixar plugin
        let plugin_bytes = self.download_plugin(plugin_source).await?;
        
        // 2. Verificar hash
        self.hash_verifier.verify(
            &plugin_bytes,
            &plugin_source.expected_hash,
        )?;
        
        // 3. Verificar assinatura
        self.signature_verifier.verify(
            &plugin_bytes,
            &plugin_source.signature,
            &plugin_source.signing_key,
        )?;
        
        // 4. Verificar atestacoes
        self.attestation_verifier.verify(
            &plugin_bytes,
            &plugin_source.attestations,
        )?;
        
        // 5. Configurar permissoes
        let permissions = self.permission_enforcer.configure(
            &plugin_bytes,
            &config.allowed_permissions,
        )?;
        
        // 6. Configurar monitoramento
        let monitor = self.behavior_monitor.setup(
            &plugin_bytes,
            &config.monitoring_config,
        )?;
        
        Ok(VerifiedPlugin {
            bytes: plugin_bytes,
            permissions,
            monitor,
            verified_at: Utc::now(),
        })
    }
}
```

### 11.11.7 Monitoramento e Resposta a Incidentes

```rust
// Sistema de monitoramento e resposta a incidentes
struct MonitoringSystem {
    metrics_collector: MetricsCollector,
    alert_manager: AlertManager,
    incident_responder: IncidentResponder,
    audit_logger: AuditLogger,
}

impl MonitoringSystem {
    async fn monitor_plugin(
        &self,
        plugin: &VerifiedPlugin,
    ) -> Result<(), MonitoringError> {
        loop {
            // 1. Coletar metricas
            let metrics = self.metrics_collector.collect(plugin).await?;
            
            // 2. Verificar anomalias
            let anomalies = self.detect_anomalies(&metrics).await?;
            
            for anomaly in &anomalies {
                // 3. Classificar severidade
                let severity = self.classify_severity(anomaly);
                
                // 4. Responder
                match severity {
                    Severity::Critical => {
                        // Isolamento imediato
                        self.incident_responder.isolate_plugin(
                            plugin,
                        ).await?;
                        
                        // Notificar usuarios
                        self.alert_manager.notify_critical(
                            plugin,
                            anomaly,
                        ).await?;
                        
                        // Iniciar investigacao
                        self.incident_responder.investigate(
                            plugin,
                            anomaly,
                        ).await?;
                    }
                    Severity::High => {
                        // Notificar administradores
                        self.alert_manager.notify_high(
                            plugin,
                            anomaly,
                        ).await?;
                        
                        // Aumentar monitoramento
                        self.metrics_collector.increase_frequency(
                            plugin,
                        ).await?;
                    }
                    Severity::Medium | Severity::Low => {
                        // Log para analise posterior
                        self.audit_logger.log_anomaly(
                            plugin,
                            anomaly,
                        ).await?;
                    }
                }
            }
            
            // 5. Aguardar proximo ciclo
            tokio::time::sleep(Duration::from_secs(30)).await;
        }
    }
    
    async fn detect_anomalies(
        &self,
        metrics: &PluginMetrics,
    ) -> Result<Vec<Anomaly>, MonitoringError> {
        let mut anomalies = Vec::new();
        
        // Verificar uso de memoria
        if metrics.memory_usage > metrics.expected_memory * 2.0 {
            anomalies.push(Anomaly::MemorySpike {
                current: metrics.memory_usage,
                expected: metrics.expected_memory,
            });
        }
        
        // Verificar chamadas de sistema
        if metrics.suspicious_syscalls > 0 {
            anomalies.push(Anomaly::SuspiciousSyscalls {
                count: metrics.suspicious_syscalls,
                details: metrics.syscall_details.clone(),
            });
        }
        
        // Verificar tentativas de rede
        if metrics.network_attempts > metrics.expected_network {
            anomalies.push(Anomaly::NetworkAnomaly {
                attempts: metrics.network_attempts,
                expected: metrics.expected_network,
            });
        }
        
        // Verificar erros
        if metrics.error_rate > 0.1 {  // > 10% erro
            anomalies.push(Anomaly::HighErrorRate {
                rate: metrics.error_rate,
            });
        }
        
        Ok(anomalies)
    }
}
```

### 11.11.8 Diagrama Completo da Pipeline

```text
+===================================================================+
|                    PIPELINE SEGURA COMPLETA                         |
|                    Plugins WebAssembly                              |
+===================================================================+
|                                                                   |
|  +-----------+     +-----------+     +-----------+                 |
|  |  DESENVOL |     |  BUILD    |     | REGISTRY  |                 |
|  | VEDOR     |     | PIPELINE  |     | /MARKET   |                 |
|  +-----+-----+     +-----+-----+     +-----+-----+               |
|        |                 |                 |                       |
|  [1] Git commit    [4] Hermetic     [9] Signature verify          |
|      (signed)          build        [10] Vuln scan                |
|  [2] Pre-commit    [5] Reproducible [11] License check            |
|      hooks              build       [12] Malware detection         |
|  [3] Code review   [6] SBOM gen     [13] Auto + manual review     |
|      (required)     [7] Attestation [14] Rekor transparency log   |
|                     [8] Cosign sign                                |
|        |                 |                 |                       |
|        v                 v                 v                       |
|  +-----------+     +-----------+     +-----------+                 |
|  | SOURCE    |     | ARTIFACTS |     | DISTRIB  |                 |
|  | REPO      |     | STORE     |     | UITION   |                 |
|  +-----------+     +-----------+     +-----+-----+               |
|                                          |                       |
|                                          v                       |
|                                    +-----------+                 |
|                                    | HOST APP  |                 |
|                                    |           |                 |
|                                    | [18] Pre-exec verify        |
|                                    | [19] WASI permissions       |
|                                    | [20] Sandbox load           |
|                                    | [21] Behavior monitor       |
|                                    | [22] Audit log              |
|                                    +-----+-----+                 |
|                                          |                       |
|                                          v                       |
|                                    +-----------+                 |
|                                    | INCIDENT  |                 |
|                                    | RESPONSE  |                 |
|                                    |           |                 |
|                                    | [23] Anomaly detect         |
|                                    | [24] Auto-isolate           |
|                                    | [25] User notification      |
|                                    | [26] Auto-rollback          |
|                                    | [27] Forensic analysis      |
|                                    +-----------------+           |
|                                                                   |
+===================================================================+
```

### 11.11.9 Exemplo Completo de Pipeline Funcional

```yaml
# Pipeline completa e funcional para plugins Wasm
name: Complete Secure Plugin Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  PLUGIN_NAME: my-plugin
  WASM_TARGET: wasm32-wasi
  REGISTRY: plugins.example.com

jobs:
  # ==================== FASE 1: VERIFICACAO ====================
  verify-source:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Verify commit signatures
        run: |
          FAILED=0
          for commit in $(git log --format='%H' -20); do
            STATUS=$(git log -1 --format='%G?' $commit)
            if [ "$STATUS" != "G" ] && [ "$STATUS" != "U" ]; then
              echo "Commit $commit nao assinado (status: $STATUS)"
              FAILED=1
            fi
          done
          if [ "$FAILED" -eq 1 ]; then
            echo "ERRO: Commits nao assinados encontrados"
            exit 1
          fi
      
      - name: Verify branch protection
        run: |
          BRANCH=$(git rev-parse --abbrev-ref HEAD)
          PROTECTION=$(gh api repos/${{ github.repository }}/branches/${BRANCH}/protection 2>/dev/null || echo "null")
          if [ "$PROTECTION" = "null" ]; then
            echo "AVISO: Branch protection nao configurado"
          fi

  # ==================== FASE 2: BUILD SEGURO ====================
  secure-build:
    needs: verify-source
    runs-on: ubuntu-latest
    container:
      image: rust:1.75.0-slim-bookworm
      options: |
        --read-only
        --tmpfs /tmp:size=1G
        --security-opt no-new-privileges
        --cap-drop ALL
        --cap-add SYS_CHROOT
    
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      
      - name: Build plugin (hermetic)
        run: |
          cargo build --target ${{ env.WASM_TARGET }} --release --frozen
      
      - name: Verify build reproducibility
        run: |
          HASH1=$(sha256sum target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm | cut -d' ' -f1)
          echo "Build hash: $HASH1"
          echo "BUILD_HASH=$HASH1" >> $GITHUB_ENV
      
      - name: Generate SBOM
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
          syft target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm \
            -o spdx-json > plugin.spdx.json
          syft target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm \
            -o cyclonedx-json > plugin.cdx.json
      
      - name: Generate attestation
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm
      
      - name: Sign plugin
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign-blob \
            --bundle plugin.wasm.bundle \
            target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm
        env:
          COSIGN_YES: "true"
      
      - name: Create manifest
        run: |
          VERSION=$(cargo metadata --format-version 1 | jq -r '.packages[0].version')
          cat > plugin.manifest.json << EOF
          {
            "name": "${{ env.PLUGIN_NAME }}",
            "version": "$VERSION",
            "hash_sha256": "${{ env.BUILD_HASH }}",
            "wasm_target": "${{ env.WASM_TARGET }}",
            "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "built_by": "${{ github.actor }}",
            "commit": "${{ github.sha }}",
            "workflow": "${{ github.workflow_run.id }}"
          }
          EOF
      
      - name: Upload all artifacts
        uses: actions/upload-artifact@v4
        with:
          name: secure-build
          path: |
            target/${{ env.WASM_TARGET }}/release/${{ env.PLUGIN_NAME }}.wasm
            plugin.wasm.bundle
            plugin.spdx.json
            plugin.cdx.json
            plugin.manifest.json
            .attestations/*
          retention-days: 90

  # ==================== FASE 3: VERIFICACAO POST-BUILD ====================
  security-scan:
    needs: secure-build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: secure-build
      
      - name: Install security tools
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s --
          curl -sSfL https://raw.githubusercontent.com/sigstore/cosign/main/install.sh | sh -s --
      
      - name: Verify signature
        run: |
          cosign verify-blob \
            --bundle plugin.wasm.bundle \
            --certificate-identity="${{ github.actor }}@users.noreply.github.com" \
            --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
            ${{ env.PLUGIN_NAME }}.wasm
      
      - name: Scan vulnerabilities
        run: |
          grype sbom:plugin.spdx.json \
            --fail-on critical \
            --output table
      
      - name: Verify permissions
        run: |
          python3 -c "
          import json
          manifest = json.load(open('plugin.manifest.json'))
          print('Manifest verified:', manifest['name'], manifest['version'])
          "

  # ==================== FASE 4: PUBLICACAO ====================
  publish:
    needs: security-scan
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: secure-build
      
      - name: Publish to registry
        run: |
          # Publicar plugin
          VERSION=$(jq -r '.version' plugin.manifest.json)
          curl -X POST "https://${{ env.REGISTRY }}/api/v1/plugins" \
            -H "Authorization: Bearer ${{ secrets.REGISTRY_TOKEN }}" \
            -F "wasm=@${{ env.PLUGIN_NAME }}.wasm" \
            -F "bundle=@plugin.wasm.bundle" \
            -F "sbom=@plugin.spdx.json" \
            -F "manifest=@plugin.manifest.json"
          
          echo "Plugin publicado: ${{ env.PLUGIN_NAME }} v$VERSION"
      
      - name: Create GitHub Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v1
        with:
          files: |
            ${{ env.PLUGIN_NAME }}.wasm
            plugin.wasm.bundle
            plugin.spdx.json
            plugin.cdx.json
            plugin.manifest.json
          generate_release_notes: true
```

---

## 11.12 Casos Reais e Incidentes

Estudar incidentes reais é essencial para entender as ameaças reais e projetar defesas eficazes. Esta seção analisa ataques de supply chain notáveis e as lições que podem ser aplicadas a ecossistemas de plugins Wasm.

### 11.12.1 Ataques de Supply Chain npm e Lições para Wasm

O ecossistema npm sofreu múltiplos ataques de supply chain que oferecem lições diretamente aplicáveis a plugins Wasm:

**EventStream (Novembro 2018)**:

O pacote `event-stream` era amplamente utilizado com milhões de downloads semanais. O mantenedor original transferiu a manutenção para um novo desenvolvedor (`right9ctrl`) que injetou código malicioso visando roubar criptomoedas de usuários do aplicativo Copay.

```text
Cronologia do ataque:
- 2015: event-stream publicado, ganha popularidade
- 2018-09: Mantenedor original transfere para right9ctrl
- 2018-10: right9ctrl adiciona dependencia maliciosa (flatmap-stream)
- 2018-11: Ataque descoberto pela comunidade
- Dano: ~2.3M USD em criptomoedas roubadas

LIÇÃO PARA WASM:
- Plugins Wasm podem ter dependencias transitivas maliciosas
- Transferencia de manutencao e um vetor de ataque critico
- Verificacao de dependencias e essencial
```

**UA-parser-js (Outubro 2021)**:

Pacotes populares no npm foram comprometidos com código malicioso que visava roubar dados de criptomoedas. O pacote atingia cerca de 8 milhões de downloads por semana.

```text
Cronologia do ataque:
- 2021-10-22: Pacotes UA-parser-js, coa e rc comprometidos
- Versoes maliciosas publicadas: UA-parser-js 0.7.29, 1.0.0
- Codigo malicioso: keylogger + cryptominer
- Dano: Potencial exposicao de dados de criptomoedas

LIÇÃO PARA WASM:
- Plugins populares sao alvos atrativos
- Versoes comprometidas podem rodar em sandbox Wasm
- Monitoramento continuo de versoes e necessario
```

**colors.js (Janeiro 2022)**:

O mantenedor do pacote `colors.js` intencionalmente corrompeu suas proprias versoes como protesto, adicionando loop infinito e mensagem ofensiva. Isso demonstrou que autores podem ser adversarios.

```text
Cronologia do ataque:
- 2022-01-07: colors.js v1.4.1 corrompida intencionalmente
- Codigo malicioso: loop infinito com mensagem "LIBERTA"
- Versao 6.0.0 tambem corrompida
- Dano: milhoes de builds quebrados globalmente

LIÇÃO PARA WASM:
- Autores podem ser insiders adversarios
- Versionamento estrito e essencial
- Pin por hash previne atualizacoes maliciosas
```

```rust
// Defesa baseada nas lições npm para Wasm
struct NPMInspiredDefense {
    // Baseado em EventStream: verificacao de transferencia de manutencao
    maintainer_change_detection: bool,
    
    // Baseado em UA-parser: verificacao de dependencias transita
    transitive_dependency_audit: bool,
    
    // Baseado em colors.js: pin por hash
    hash_pinning: bool,
    
    // Geral: verificao de assinatura
    signature_verification: bool,
}

impl NPMInspiredDefense {
    fn verify_plugin(&self, plugin: &Plugin) -> Result<(), DefenseError> {
        // 1. Verificar se houve mudanca de mantenedor
        if self.maintainer_change_detection {
            let history = plugin.get_maintainer_history()?;
            if let Some(recent_change) = history.last_change() {
                if recent_change.age() < Duration::from_days(90) {
                    return Err(DefenseError::RecentMaintainerChange {
                        changed_by: recent_change.maintainer.clone(),
                        changed_at: recent_change.date,
                    });
                }
            }
        }
        
        // 2. Verificar dependencias transita
        if self.transitive_dependency_audit {
            let deps = plugin.get_transitive_dependencies()?;
            for dep in &deps {
                if dep.has_recent_version_change() {
                    return Err(DefenseError::SuspiciousDependencyUpdate {
                        dependency: dep.name.clone(),
                    });
                }
            }
        }
        
        // 3. Verificar pin por hash
        if self.hash_pinning {
            if !plugin.is_hash_pinned() {
                return Err(DefenseError::NotHashPinned);
            }
        }
        
        // 4. Verificar assinatura
        if self.signature_verification {
            if !plugin.is_signed() {
                return Err(DefenseError::UnsignedPlugin);
            }
        }
        
        Ok(())
    }
}
```

### 11.12.2 SolarWinds-style Attack em Sistemas de Plugins

O ataque ao SolarWinds (2020) é um dos mais significativos ataques de supply chain da historia. Embora não tenha sido um ecossistema de plugins tradicional, seus vetores de ataque são diretamente aplicáveis:

```text
+-------------------------------------------------------------------+
|           SolarWinds Attack: Analise para Plugins Wasm             |
+-------------------------------------------------------------------+
|                                                                   |
|  ATACANTE SOLARWINDS:                                             |
|  1. Comprometeu ambiente de build da SolarWinds                   |
|  2. Injetou backdoor no codigo-fonte do Orion                     |
|  3. Backdoor incluido em builds legitimos                         |
|  4. Atualizacao distribuida como legítima                         |
|  5. Backdoor ativado em alvos especificos                         |
|                                                                   |
|  ANALOGIA EM PLUGINS WASM:                                        |
|  1. Atacante compromete CI/CD do desenvolvedor                    |
|  2. Injeta codigo malicioso no source antes do build              |
|  3. Build hermetico gera binario comprometido                     |
|  4. Assinatura valida porque build roda no pipeline legitimo      |
|  5. Plugin distribuido via registry como legitimo                 |
|                                                                   |
|  DIFERENCA CRITICA:                                               |
|  - Em Wasm, o binario e opaco (dificil deteccao visual)          |
|  - Component Model permite composicao dinamica                    |
|  - WASI capabilities podem ser exploradas                        |
|                                                                   |
|  MITIGACOES:                                                      |
|  - Build reprodutivel (qualquer pessoa pode reproduzir)          |
|  - SBOM detalhado (visibilidade total de componentes)            |
|  - Atestacao de proveniencia (evidencia de como foi construido)  |
|  - Verificacao de source vs binario (deteccao de adulteracao)    |
|  - Monitoramento de comportamento (deteccao de backdoor)         |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Defesa anti-SolarWinds para plugins Wasm
struct AntiSolarWindsDefense {
    reproducible_build_verifier: ReproducibleBuildVerifier,
    source_binary_comparator: SourceBinaryComparator,
    behavior_anomaly_detector: BehaviorAnomalyDetector,
}

impl AntiSolarWindsDefense {
    fn defend(&self, plugin: &Plugin) -> Result<(), DefenseError> {
        // 1. Verificar build reprodutivel
        // Se o build nao for reprodutivel, nao e possivel
        // verificar que o binario corresponde ao source
        let reproducible = self.reproducible_build_verifier
            .verify(plugin)?;
        
        if !reproducible.is_reproducible {
            return Err(DefenseError::NonReproducibleBuild {
                details: reproducible.details,
            });
        }
        
        // 2. Comparar source vs binario
        // Em Wasm, isso e possivel usando WASM tools para
        // analisar a estrutura do binario
        let comparison = self.source_binary_comparator
            .compare(plugin)?;
        
        if !comparison.matches {
            return Err(DefenseError::SourceBinaryMismatch {
                differences: comparison.differences,
            });
        }
        
        // 3. Detectar anomalias comportamentais
        // Um backdoor pode se manifestar em comportamento
        // anomalo durante execucao
        let anomalies = self.behavior_anomaly_detector
            .detect(plugin)?;
        
        if !anomalies.is_empty() {
            return Err(DefenseError::BehavioralAnomaly {
                anomalies,
            });
        }
        
        Ok(())
    }
}

struct ReproducibleBuildVerifier;

impl ReproducibleBuildVerifier {
    fn verify(&self, plugin: &Plugin) -> Result<ReproducibilityResult, VerifierError> {
        // Verificar se o build pode ser reproduzido
        // usando as mesmas ferramentas e configuracao
        
        // 1. Baixar source code do commit especificado
        let source = self.download_source(plugin.source_commit())?;
        
        // 2. Configurar ambiente identico
        let env = self.setup_identical_environment(plugin.build_env())?;
        
        // 3. Executar build
        let build_result = self.execute_build(&source, &env)?;
        
        // 4. Comparar resultado
        let match = build_result.hash == plugin.hash();
        
        Ok(ReproducibilityResult {
            is_reproducible: match,
            expected_hash: plugin.hash().to_string(),
            computed_hash: build_result.hash,
            details: if match {
                "Build reprodutivel verificado".to_string()
            } else {
                "Build NAO e reprodutivel - possivel adulteracao".to_string()
            },
        })
    }
}
```

### 11.12.3 Typosquatting em Repositórios de Plugins

Typosquatting é o registro de nomes similares a pacotes populares para enganar usuários:

```text
+-------------------------------------------------------------------+
|                    Typosquatting em Plugins                         |
+-------------------------------------------------------------------+
|                                                                   |
|  PLUGIN LEGITIMO:         PLUGIN MALICIOSO:                       |
|  -------------------------  ---------------------------           |
|  analytics                 analitics                              |
|  auth-service              auth-servise                           |
|  crypto-utils              crypto-utilz                           |
|  image-resize              image-resizer                          |
|  data-parser               data-parsr                             |
|                                                                   |
|  TECNICAS COMUNS:                                                  |
|  - Erro de digitacao (analitics vs analytics)                     |
|  - Caracteres visualmente similares (l vs 1, O vs 0)             |
|  - Nomes invertidos (utils-crypto vs crypto-utils)               |
|  - Prefixo/sufixo adicional (my-analytics)                       |
|  - Nomes de plugins descontinuados                                |
|                                                                   |
|  DEFESAS:                                                         |
|  - Verificacao de nome exato no manifesto                        |
|  - Allowlist de plugins permitidos                                |
|  - Verificacao de autor/conhecidor                               |
|  - Alertas para nomes similares                                   |
|  - Busca fuzzy no registry                                        |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Deteccao de typosquatting
struct TyposquattingDetector {
    known_plugins: Vec<String>,
    similarity_threshold: f64,
}

impl TyposquattingDetector {
    fn check(&self, plugin_name: &str) -> Vec<TyposquattingMatch> {
        let mut matches = Vec::new();
        
        for known in &self.known_plugins {
            let distance = self.levensstein_distance(plugin_name, known);
            let similarity = 1.0 - (distance as f64 / known.len() as f64);
            
            if similarity > self.similarity_threshold 
                && plugin_name != known
            {
                matches.push(TyposquattingMatch {
                    potential_target: known.clone(),
                    similarity,
                    distance,
                    risk_level: self.assess_risk(similarity, known),
                });
            }
        }
        
        // Ordenar por similaridade (maior primeiro)
        matches.sort_by(|a, b| 
            b.similarity.partial_cmp(&a.similarity).unwrap()
        );
        
        matches
    }
    
    fn levensstein_distance(&self, a: &str, b: &str) -> usize {
        let a_len = a.len();
        let b_len = b.len();
        let mut matrix = vec![vec![0usize; b_len + 1]; a_len + 1];
        
        for i in 0..=a_len { matrix[i][0] = i; }
        for j in 0..=b_len { matrix[0][j] = j; }
        
        for i in 1..=a_len {
            for j in 1..=b_len {
                let cost = if a.as_bytes()[i-1] == b.as_bytes()[j-1] {
                    0
                } else {
                    1
                };
                matrix[i][j] = (matrix[i-1][j] + 1)
                    .min(matrix[i][j-1] + 1)
                    .min(matrix[i-1][j-1] + cost);
            }
        }
        
        matrix[a_len][b_len]
    }
    
    fn assess_risk(&self, similarity: f64, target: &str) -> RiskLevel {
        match similarity {
            s if s > 0.9 => RiskLevel::Critical,
            s if s > 0.8 => RiskLevel::High,
            s if s > 0.7 => RiskLevel::Medium,
            _ => RiskLevel::Low,
        }
    }
}

#[derive(Debug)]
struct TyposquattingMatch {
    potential_target: String,
    similarity: f64,
    distance: usize,
    risk_level: RiskLevel,
}
```

### 11.12.4 Ambientes de Build Comprometidos

```text
+-------------------------------------------------------------------+
|         Comprometimento de Ambientes de Build                       |
+-------------------------------------------------------------------+
|                                                                   |
|  VETORES DE ATAQUE NO BUILD:                                      |
|                                                                   |
|  1. Comprometimento de credenciais CI/CD                          |
|     - Tokens GitHub Actions roubados                              |
|     - Secrets do pipeline expostos                                |
|     - Chaves de assinatura comprometidas                          |
|                                                                   |
|  2. Injecao no pipeline                                           |
|     - Scripts de build modificados                                |
|     - Dependencias maliciosas no build                            |
|     - Hooks de build comprometidos                                |
|                                                                   |
|  3. Comprometimento do runner                                     |
|     - Runner self-hosted comprometido                             |
|     - VM do build com backdoor                                    |
|     - Dependencias do sistema comprometidas                       |
|                                                                   |
|  4. Injecao de codigo-fonte                                       |
|     - Git server comprometido                                     |
|     - Branch protection bypass                                    |
|     - Commit signing bypass                                       |
|                                                                   |
|  MITIGACOES:                                                      |
|  - Build hermetico (sem rede)                                     |
|  - Runner efemero (descartavel)                                   |
|  - Build reprodutivel (verificavel por terceiros)                 |
|  - Atestacao de build (evidencia criptografica)                   |
|  - SBOM detalhado (visibilidade total)                           |
|  - Branch protection + commit signing obrigatorio                 |
|  - Secrets management robusto                                     |
|                                                                   |
+-------------------------------------------------------------------+
```

```yaml
# Defesas contra build compromise
name: Anti-Build-Compromise

on:
  push:
    branches: [main]

jobs:
  hardened-build:
    runs-on: ubuntu-latest
    # Usar runner efemero (GitHub-hosted)
    # Nao usar self-hosted runners para builds criticos
    
    permissions:
      contents: read  # Minimo necessario
      id-token: write  # Para OIDC
    
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      
      - name: Verify no secrets in source
        run: |
          # Verificar que nenhum segredo foi injetado
          git diff HEAD~1 --name-only | while read file; do
            if [[ "$file" == *.env ]] || [[ "$file" == *secret* ]]; then
              echo "AVISO: Arquivo sensivel modificado: $file"
              exit 1
            fi
          done
      
      - name: Build in isolated container
        run: |
          docker run --rm \
            --read-only \
            --tmpfs /tmp:size=1G \
            --network none \
            --security-opt no-new-privileges \
            -v ${{ github.workspace }}:/workspace:ro \
            rust:1.75.0-slim-bookworm \
            bash -c "cd /workspace && cargo build --target wasm32-wasi --release --frozen"
      
      - name: Verify build integrity
        run: |
          # Verificar hash do resultado
          HASH=$(sha256sum target/wasm32-wasi/release/plugin.wasm | cut -d' ' -f1)
          echo "Build hash: $HASH"
          
          # Comparar com hash anterior (se existir)
          if [ -f .build-hash ]; then
            PREV_HASH=$(cat .build-hash)
            if [ "$HASH" != "$PREV_HASH" ]; then
              echo "AVISO: Build hash diferente do anterior"
            fi
          fi
          echo "$HASH" > .build-hash
```

### 11.12.5 Mitigações Reais que Funcionaram

```text
+-------------------------------------------------------------------+
|           Mitigacoes Reais que Funcionaram                          |
+-------------------------------------------------------------------+
|                                                                   |
|  1. GOOGLE: OSV (Open Source Vulnerabilities)                     |
|     - Base de dados unificada de vulnerabilidades                 |
|     - API para consultas automatizadas                            |
|     - Suporte a multi-ecossistemas                                |
|     - RESULTADO: Deteccao rapida de vulnerabilidades             |
|                                                                   |
|  2. SIGSTORE: Assinatura keyless                                  |
|     - Eliminacao de gerenciamento de chaves                       |
|     - Certificados de curta duracao via OIDC                      |
|     - Log de transparencia Rekor                                  |
|     - RESULTADO: Assinatura acessivel para todos                  |
|                                                                   |
|  3. SLSA: Framework de attestacao                                 |
|     - Niveis claros de seguranca de supply chain                  |
|     - Atestacao de proveniencia padronizada                       |
|     - Verificacao automatizada                                    |
|     - RESULTADO: Padrao para attestacao de build                  |
|                                                                   |
|  4. ENDPA: Sigstore para packages                                 |
|     - Integracao com package managers                             |
|     - Verificacao automatica de assinatura                        |
|     - BLOCK de pacotes nao assinados                              |
|     - RESULTADO: Adocao crescente em ecossistemas                 |
|                                                                   |
|  5. DEPENDABOT/RENOVATE: Atualizacao automatizada                 |
|     - PRs automaticos para atualizacoes de seguranca              |
|     - Verificacao de compatibilidade                              |
|     - Testes automaticos                                          |
|     - RESULTADO: Reducao de tempo de exposicao a vulnerabilidades |
|                                                                   |
|  6. NIX/GUIX: Builds reprodutiveis                                |
|     - Ambientes de build deterministicos                          |
|     - Dependencias fixadas por hash                               |
|     - Verificacao por terceiros                                   |
|     - RESULTADO: Eliminacao de build compromise                   |
|                                                                   |
|  RECOMENDACAO PARA WASM:                                          |
|  - Combinar OSV + Sigstore + SLSA                                |
|  - Implementar builds reprodutiveis                               |
|  - Usar Dependabot/Renovate para atualizacoes                    |
|  - SBOM automatico em todo pipeline                               |
|                                                                   |
+-------------------------------------------------------------------+
```

```rust
// Implementando as melhores mitigacoes
struct BestPracticesDefense {
    osv_client: OSVClient,
    sigstore_verifier: SigstoreVerifier,
    slsa_verifier: SLSAVerifier,
    sbom_validator: SBOMValidator,
    reproducibility_checker: ReproducibilityChecker,
}

impl BestPracticesDefense {
    async fn comprehensive_check(
        &self,
        plugin: &Plugin,
    ) -> Result<ComprehensiveResult, CheckError> {
        let mut result = ComprehensiveResult::new();
        
        // 1. OSV: Verificar vulnerabilidades
        let vulns = self.osv_client.query(
            &plugin.name,
            &plugin.version,
            "crates.io",
        ).await?;
        
        result.vulnerabilities = vulns;
        
        // 2. Sigstore: Verificar assinatura
        let sig_valid = self.sigstore_verifier.verify(
            &plugin.wasm_bytes,
            &plugin.signature,
            &plugin.certificate,
        ).await?;
        
        result.signature_valid = sig_valid;
        
        // 3. SLSA: Verificar atestacao
        let slsa_level = self.slsa_verifier.verify(
            &plugin.attestation,
        ).await?;
        
        result.slsa_level = slsa_level;
        
        // 4. SBOM: Validar
        let sbom_valid = self.sbom_validator.validate(
            &plugin.sbom,
        ).await?;
        
        result.sbom_valid = sbom_valid;
        
        // 5. Reprodutibilidade: Verificar
        let reproducible = self.reproducibility_checker.check(
            &plugin,
        ).await?;
        
        result.reproducible = reproducible;
        
        // Calcular score geral
        result.overall_score = self.calculate_score(&result);
        
        Ok(result)
    }
    
    fn calculate_score(&self, result: &ComprehensiveResult) -> f64 {
        let mut score = 0.0;
        
        if result.signature_valid { score += 0.25; }
        if result.slsa_level >= 3 { score += 0.25; }
        if result.sbom_valid { score += 0.15; }
        if result.reproducible { score += 0.20; }
        if result.vulnerabilities.is_empty() { score += 0.15; }
        
        score
    }
}

#[derive(Debug)]
struct ComprehensiveResult {
    vulnerabilities: Vec<Vulnerability>,
    signature_valid: bool,
    slsa_level: u8,
    sbom_valid: bool,
    reproducible: bool,
    overall_score: f64,
}

impl ComprehensiveResult {
    fn new() -> Self {
        Self {
            vulnerabilities: Vec::new(),
            signature_valid: false,
            slsa_level: 0,
            sbom_valid: false,
            reproducible: false,
            overall_score: 0.0,
        }
    }
}
```

---

## 11.13 Considerações Finais

A segurança de supply chain de plugins Wasm é um campo complexo e em rápida evolução. Ao longo deste capítulo, exploramos as múltiplas camadas de segurança necessárias para proteger ecossistemas de plugins contra ataques de supply chain. As principais lições e recomendações são apresentadas a seguir.

### 11.13.1 Pontos-Chave

A segurança de supply chain de plugins Wasm requer uma abordagem em camadas, onde cada camada fornece uma defesa independente. Nenhuma única ferramenta ou técnica é suficiente por si só.

**Confiança zero é o padrão**: Nenhum plugin deve ser confiável por padrão. Todo plugin deve ser verificado continuamente, desde a origem até a execução. O modelo de confiança baseada em capacidades do WASI fornece uma base sólida para isso.

**Assinatura e verificação são obrigatórias**: Cosign/Sigstore tornaram a assinatura de código acessível e sem a necessidade de gerenciar chaves de longa duração. Toda distribuição de plugins deve exigir assinatura verificável.

**SBOMs dão visibilidade**: Um SBOM completo permite entender exatamente o que está em um plugin, suas dependências e licenças. Isso é essencial para decisões de segurança e conformidade.

**Atestações provam proveniência**: Atestações de build e proveniência fornecem evidência criptográfica de como um plugin foi construído. SLSA fornece um framework claro para isso.

**Builds reprodutíveis são a defesa final**: Se um build não for reprodutível, não é possível verificar que o binário corresponde ao source. Investir em builds reprodutíveis é fundamental.

**Monitoramento contínuo é essencial**: Ataques de supply chain podem ser difíceis de detectar. Monitoramento de comportamento, anomaly detection e auditoria contínua são necessários.

### 11.13.2 Construindo uma Cultura de Segurança em Plugins

A segurança de supply chain não é apenas技术和工具的问题 - é um problema cultural. Organizações precisam cultivar uma cultura onde a segurança é prioridade em cada etapa do desenvolvimento e distribuição de plugins.

**Responsabilidade compartilhada**: Desenvolvedores, mantenedores de marketplaces e usuários finais compartilham responsabilidade pela segurança. Cada parte tem um papel a desempenhar.

**Transparência**: Processos de build, distribuição e verificação devem ser transparentes e auditáveis. Segredo em segurança geralmente cria vulnerabilidades.

**Automação**: Verificação manual não escala. Ferramentas automatizadas de verificação, escaneamento e monitoramento são essenciais.

**Educação**: Desenvolvedores precisam entender os riscos de supply chain e como mitigá-los. Treinamento regular e simulações de ataque ajudam a manter a vigilância.

**Incentivos alinhados**: Marketplaces devem incentivar práticas seguras, não apenas conveniência. Plugins seguros devem ter visibilidade e prioridade.

### 11.13.3 O Futuro da Segurança de Supply Chain em Wasm

O ecossistema Wasm está evoluindo rapidamente, e a segurança de supply chain evoluirá junto:

**Component Model maduro**: O Component Model do Wasm proporcionará composição segura de plugins, com interfaces tipadas e verificação estática de compatibilidade.

**WASI capabilities expandidas**: Novas capacidades WASI serão adicionadas com controle granular, permitindo políticas de segurança mais refinadas.

**Ferramentas maduras**: Ferramentas de verificação, SBOM e attestation para Wasm atingirão maturidade similar às de ecossistemas estabelecidos como npm e crates.io.

**Integração nativa**: Runtimes Wasm integrarão verificação de assinatura e attestation nativamente, tornando a segurança transparente para desenvolvedores e usuários.

**Regulação**: Regulações como a EO do Biden sobre cibersegurança e a EU Cyber Resilience Act exigirão SBOMs e attestations para software, incluindo plugins Wasm.

**Zero-trust padrão**: A arquitetura zero-trust se tornará o padrão para ecossistemas de plugins, com verificação contínua e minimização de privilégios.

### 11.13.4 Recomendações

**Para desenvolvedores de plugins**:
- Assine todos os plugins com Cosign/Sigstore
- Gere SBOMs para cada versão
- Implemente builds reprodutíveis
- Documente dependências e permissões WASI
- Participe de programas de disclosure responsible

**Para mantenedores de marketplaces**:
- Implemente verificação automatizada na publicação
- Exija SBOMs e attestations
- Execute escaneamento de vulnerabilidades contínuo
- Implemente sistema de reputação
- Tenha plano de resposta a incidentes

**Para usuários finais**:
- Verifique assinaturas antes de instalar plugins
- Revise permissões WASI solicitadas
- Mantenha plugins atualizados
- Monitore comportamento de plugins
- Reporte comportamento suspeito

**Para organizações**:
- Implemente pipeline de segurança completa
- Invista em ferramentas de verificação automatizada
- Treine equipes em segurança de supply chain
- Implemente monitoramento e resposta a incidentes
- Participe da comunidade de segurança Wasm

A segurança de supply chain de plugins Wasm é uma jornada contínua, não um destino. À medida que o ecossistema amadurece, novas ameaças e defesas surgirão. Manter-se informado, adaptável e comprometido com a segurança é essencial para construir ecossistemas de plugins seguros e confiáveis.
---

*[Capítulo anterior: 10 — Side Channels](10-side-channels.md)*
*[Próximo capítulo: 12 — Fuzzing](12-fuzzing.md)*
