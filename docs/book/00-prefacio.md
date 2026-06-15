# Prefácio — Desenvolvimento Seguro orientado à Segurança

> "Segurança não é um produto, mas um processo." — Bruce Schneier

---

## 1. Por que este livro existe

### 1.1 A crise na segurança de software

A segurança de software atravessa uma crise silenciosa e persistente. A cada ano, o número de vulnerabilidades registradas cresce exponencialmente. O relatório 2023 do MITRE documentou mais de 25.000 CVEs (Common Vulnerabilities and Exposures) — um recorde histórico. O custo médio de uma violação de dados atingiu US$ 4,45 milhões em 2023, segundo o relatório anual da IBM. Esses números não são estatísticas abstratas: representam dados pessoais expostos, sistemas críticos comprometidos e confiança destruída.

O problema não é falta de ferramentas ou de conhecimento teórico. Existe uma lacuna profunda entre os profissionais de segurança, que compreendem os vetores de ataque, e os desenvolvedores, que escrevem o código que se torna o alvo. Essa lacuna é especialmente perigosa em linguagens como C++, onde o desenvolvedor assume controle direto sobre memória, ponteiros e recursos do sistema.

### 1.2 O impacto em C++

Desenvolvedores C++ operam em camadas críticas da infraestrutura digital: sistemas operacionais, bancos de dados, compiladores, drivers de hardware, softwares embarcados, motores de jogos e sistemas financeiros. Uma vulnerabilidade em C++ raramente afeta apenas uma aplicação — ela pode comprometer todo o ecossistema que depende daquele componente.

A manualidade na gestão de memória em C++ — alocar, desalocar, validar ponteiros, gerenciar escopo — cria uma superfície de ataque que linguagens com garbage collection simplesmente não expõem. Erros como buffer overflow, use-after-free e integer overflow são endemicos em código C++ mal escrito, e eles são exatamente os tipos de vulnerabilidade mais explorados em ataques reais.

### 1.3 Casos públicos documentados de falhas em C++

A história da segurança de software está repleta de incidentes que ilustram a importância do desenvolvimento seguro. Cada um desses casos demonstra como uma única falha pode ter consequências catastróficas em escala global.

#### Heartbleed (CVE-2014-0160) — OpenSSL

Heartbleed é uma das vulnerabilidades mais emblemáticas da história da segurança digital. Descoberta em abril de 2014, afetou a biblioteca OpenSSL, amplamente utilizada para comunicação segura em internet. A falha era um buffer over-read no manipulador do heartbeat TLS.

O problema estava na implementação da extensão heartbeat do TLS. O código permitia que um cliente enviasse um pacote heartbeat com um tamanho declarado maior que o payload real. O servidor respondia copiando memória para o buffer de resposta, incluindo dados além do limite do payload — expondo até 64 KB de memória do servidor a cada requisição maliciosa.

```cpp
/* Padrão vulnerável inspirado em Heartbleed */
/* O problema: o código confia cegamente no valor fornecido pelo cliente */

#include <cstdint>
#include <cstring>
#include <vector>

struct HeartbeatRequest {
    uint8_t type;
    uint16_t payload_length;  /* campo controlado pelo atacante */
    uint8_t payload[];
};

void process_heartbeat(const HeartbeatRequest* req, size_t received_len,
                       std::vector<uint8_t>& response) {
    /* ERRO CRÍTICO: não valida se payload_length é coerente com received_len */
    uint16_t claimed_length = req->payload_length;

    /* O atacante pode declarar payload_length = 65535, mas enviar apenas 4 bytes.
       O loop abaixo copia memória além do buffer real, expondo dados do servidor. */
    response.resize(1 + 2 + claimed_length);
    response[0] = req->type;
    response[1] = (claimed_length >> 8) & 0xFF;
    response[2] = claimed_length & 0xFF;

    for (uint16_t i = 0; i < claimed_length; ++i) {
        response[3 + i] = req->payload[i];  /* over-read: i pode exceder received_len */
    }
}
```

O impacto foi devastador. Aproximadamente 17% dos servidores SSL/TLS da internet foram afetados. Atacantes puderam extrair chaves privadas, tokens de sessão e credenciais de autenticação. A LGPD e regulamentações de proteção de dados posteriormente tornaram esse tipo de exposição passível de multas milionárias. A lição central: **validação de entrada nunca pode ser opcional**, especialmente quando dados de rede controlam índices de acesso a memória.

#### Shellshock (CVE-2014-6271) — Bash

Em setembro de 2014, uma vulnerabilidade foi descoberta no GNU Bash que permitia execução remota de código através de variáveis de ambiente. O Bash processava comandos dentro de definições de funções armazenadas em variáveis de ambiente, mesmo após o término da função.

```cpp
/*
 * O padrão de Shellshock: confiar em dados de entrada para construir
 * comandos de execução. Em C++, isso se manifesta quando construímos
 * comandos shell a partir de dados não confiáveis.
 *
 * Vulnerabilidade equivalente em C++ usando popen():
 */
#include <cstdlib>
#include <string>
#include <iostream>

std::string execute_user_command(const std::string& user_input) {
    /* PADRÃO VULNERÁVEL: construção de comando shell com input do usuário */
    std::string command = "echo " + user_input;  /* injection point */
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) return "";
    std::string result;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        result += buffer;
    }
    pclose(pipe);
    return result;
}

/*
 * Versão SEGURA: sanitização rigorosa de entrada e uso de execução segura
 */
#include <algorithm>
#include <cctype>

bool is_safe_input(const std::string& input) {
    return std::all_of(input.begin(), input.end(),
        [](unsigned char c) {
            return std::isalnum(c) || c == '_' || c == '-' || c == ' ';
        });
}

std::string execute_user_command_safe(const std::string& user_input) {
    if (!is_safe_input(user_input)) {
        throw std::invalid_argument("Input contains unsafe characters");
    }
    /* Usar lista de argumentos em vez de string de comando */
    std::string command = "/bin/echo";
    std::string safe_input = user_input;
    FILE* pipe = popen((command + " " + safe_input).c_str(), "r");
    if (!pipe) return "";
    std::string result;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe)) {
        result += buffer;
    }
    pclose(pipe);
    return result;
}
```

Shellshock afetou milhões de servidores, dispositivos IoT e sistemas embarcados. A lição: **nunca confie em dados de entrada para construir comandos de execução**. Qualquer ponto onde dados externos entram em contato com a camada de execução é um vetor de ataque potencial.

#### EternalBlue e WannaCry (CVE-2017-0144) — SMB/Microsoft Windows

EternalBlue é uma exploração do protocolo SMBv1 (Server Message Block) desenvolvida originalmente pela NSA e vazada pelo grupo Shadow Brokers em 2017. A vulnerabilidade era um buffer overflow no processamento de pacotes SMB, permitindo execução remota de código sem autenticação.

Em maio de 2017, o ransomware WannaCry explorou EternalBlue para se espalhar automaticamente entre sistemas Windows, infectando mais de 200.000 computadores em 150 países. Hospitais do NHS (Reino Unido), a fabricante Renault, a Telefônica espanhola e milhares de outras organizações foram afetadas.

```cpp
/*
 * O padrão EternalBlue: buffer overflow em parsing de protocolo de rede.
 * O SMBv1 processava mensagens com campos de tamanho controlados pelo cliente,
 * sem validação adequada antes de copiar dados para buffers fixos.
 *
 * Equivalent C++ pattern (simplified):
 */
#include <cstdint>
#include <cstring>
#include <stdexcept>

struct SmbPacketHeader {
    uint8_t protocol[4];
    uint8_t command;
    uint32_t status;
    uint16_t flags;
    uint16_t length;  /* campo controlado pelo atacante */
    /* ... mais campos */
};

void process_smb_packet(const uint8_t* raw_data, size_t data_len) {
    if (data_len < sizeof(SmbPacketHeader)) {
        throw std::runtime_error("Packet too small");
    }

    const auto* header = reinterpret_cast<const SmbPacketHeader*>(raw_data);
    uint16_t payload_length = header->length;

    /* PADRÃO VULNERÁVEL: payload_length é confiável apenas se validado contra data_len */
    uint8_t local_buffer[256];  /* buffer fixo */

    const uint8_t* payload = raw_data + sizeof(SmbPacketHeader);
    size_t available = data_len - sizeof(SmbPacketHeader);

    /* BUG: comparação incorreta entre tipos, ou falta de validação */
    if (payload_length > 0) {
        /* Se payload_length > available, copia dados além do buffer */
        memcpy(local_buffer, payload, payload_length);  /* BUFFER OVERFLOW */
    }
}

void process_smb_packet_safe(const uint8_t* raw_data, size_t data_len) {
    if (data_len < sizeof(SmbPacketHeader)) {
        throw std::runtime_error("Packet too small");
    }

    const auto* header = reinterpret_cast<const SmbPacketHeader*>(raw_data);
    uint16_t payload_length = header->length;

    const uint8_t* payload = raw_data + sizeof(SmbPacketHeader);
    size_t available = data_len - sizeof(SmbPacketHeader);

    /* VERSÃO SEGURA: validação rigorosa de limites */
    if (payload_length > available) {
        throw std::runtime_error("Payload length exceeds available data");
    }

    constexpr size_t BUFFER_SIZE = 256;
    if (payload_length > BUFFER_SIZE) {
        throw std::runtime_error("Payload exceeds buffer capacity");
    }

    uint8_t local_buffer[BUFFER_SIZE];
    memcpy(local_buffer, payload, payload_length);
    /* ... processamento seguro ... */
}
```

A lição de EternalBlue é que **vulnerabilidades em protocolos de rede são amplamente exploráveis** e podem ter impacto sistêmico. A correção da Microsoft (MS17-010) estava disponível meses antes do ataque WannaCry, mas muitos sistemas não foram atualizados. Segurança não é apenas código correto — é também operação responsable.

#### Log4Shell (CVE-2021-44228) — Apache Log4j

Em dezembro de 2021, uma vulnerabilidade de execução remota de código (RCE) foi descoberta no Apache Log4j, uma das bibliotecas de logging mais utilizadas do mundo Java. A falha permitia que um atacante injetasse uma string especial que, quando logada, resolvia uma referência JNDI e carregava código malicioso de um servidor remoto.

Apesar de Log4j ser uma biblioteca Java, o padrão subjacente é universal e se aplica diretamente a C++: **nunca confie em dados de entrada para realizar operações de resolução de nomes ou carregamento dinâmico de código**.

```cpp
/*
 * O padrão Log4Shell em C++: resolução de nomes ou carregamento dinâmico
 * baseado em dados de entrada não confiáveis.
 *
 * Vulnerabilidade equivalente: um sistema que resolve nomes de arquivo
 * ou carrega bibliotecas com base em input do usuário.
 */
#include <string>
#include <dlfcn.h>  /* dlopen, dlsym */
#include <iostream>

/* PADRÃO VULNERÁVEL: carregamento dinâmico baseado em input */
void load_plugin(const std::string& plugin_name) {
    /* Se plugin_name vier de input de rede, atacante pode injetar caminho arbitrário */
    std::string path = "/usr/lib/plugins/" + plugin_name + ".so";
    void* handle = dlopen(path.c_str(), RTLD_LAZY);
    if (handle) {
        auto init = reinterpret_cast<void(*)()>(dlsym(handle, "init"));
        if (init) init();  /* executa código arbitrário */
    }
}

/* Versão SEGURA: allowlist e validação rigorosa */
#include <filesystem>
#include <set>

bool is_plugin_allowed(const std::string& name) {
    static const std::set<std::string> allowed_plugins = {
        "logger", "auth", "metrics"
    };
    return allowed_plugins.count(name) > 0;
}

void load_plugin_safe(const std::string& plugin_name) {
    if (!is_plugin_allowed(plugin_name)) {
        throw std::invalid_argument("Plugin not in allowlist");
    }
    namespace fs = std::filesystem;
    fs::path plugin_dir = "/usr/lib/plugins";
    fs::path plugin_path = plugin_dir / (plugin_name + ".so");
    /* Verificar que o resolved path está dentro do diretório permitido */
    fs::path canonical = fs::canonical(plugin_path);
    if (canonical.parent_path() != fs::canonical(plugin_dir)) {
        throw std::invalid_argument("Path traversal detected");
    }
    void* handle = dlopen(canonical.c_str(), RTLD_LAZY);
    if (handle) {
        auto init = reinterpret_cast<void(*)()>(dlsym(handle, "init"));
        if (init) init();
    }
}
```

Log4Shell afetou milhares de organizações globalmente, incluindo Apple, Amazon, Twitter, Steam e agências governamentais. A CVE-2021-44228 teve severidade CVSS 10.0 — o máximo possível. A lição central: **dados de entrada nunca devem controlar operações que resolvem nomes ou carregam código dinamicamente**.

#### Spectre e Meltdown (CVE-2017-5753, CVE-2017-5715, CVE-2017-5754)

Em janeiro de 2018, três vulnerabilidades fundamentais foram reveladas nos processadores modernos: Spectre (variantes 1 e 2) e Meltdown. Essas falhas exploram otimizações de execução speculativa e cache de processadores para extrair dados de memória que deveriam estar protegidos pelo hardware.

Spectre (CVE-2017-5753, CVE-2017-5715) engana o processador para que execute instruções de forma speculativa, acessando memória que o código não deveria acessar. Meltdown (CVE-2017-5754) explora uma falha na separação entre modo usuário e modo kernel em certos processadores Intel.

```cpp
/*
 * Spectre v1: Bounds Check Bypass
 * O padrão em C++: branches dependientes de dados controlados pelo atacante
 * que afetam o cache do processador.
 *
 * O código abaixo demonstra o conceito (não é um exploit real, é uma ilustração
 * do padrão de código que pode ser vulnerável).
 */
#include <cstdint>
#include <array>
#include <chrono>
#include <iostream>

constexpr size_t CACHE_LINE_SIZE = 64;
constexpr size_t ARRAY_SIZE = 256;

std::array<uint8_t, ARRAY_SIZE * CACHE_LINE_SIZE> probe_array;

/*
 * Padrão VULNERÁVEL: branch speculativo baseado em índice controlado
 */
uint8_t speculative_access(const uint8_t* secret_data, size_t idx) {
    if (idx < ARRAY_SIZE) {  /* branch que o speculador pode "adivinhar" errado */
        return probe_array[secret_data[idx] * CACHE_LINE_SIZE];  /* access speculativo */
    }
    return 0;
}

/*
 * Padrão SEGURA: access sem branch dependente de dados sensíveis
 * Use constant-time comparison e access patterns que não variam com dados
 */
uint8_t safe_access(const uint8_t* data, size_t idx, size_t limit) {
    /* Always access the same cache line pattern, regardless of secret data */
    volatile uint8_t sink = probe_array[idx % ARRAY_SIZE * CACHE_LINE_SIZE];
    (void)sink;
    /* Use conditional moves (CMOV) instead of branches where possible */
    uint8_t result = 0;
    size_t mask = ~(static_cast<size_t>(-1)) * (idx < limit);
    result = data[idx & mask];
    return result;
}
```

Spectre e Meltdown afetaram praticamente todos os processadores fabricados nos últimos 20 anos. A mitigação exigiu alterações em compiladores, sistemas operacionais e, em alguns casos, no hardware. A lição para desenvolvedores C++: **a segurança não existe apenas no nível do código — ela se estende até o hardware**. Técnicas como constant-time programming e access patterns previsíveis são essenciais em código criptográfico.

#### SolarWinds — Ataque na cadeia de suprimentos (2020)

Em dezembro de 2020, foi descoberto que o SolarWinds Orion, uma plataforma de gerenciamento de rede, havia sido comprometida em um ataque sofisticado à cadeia de suprimentos. Os atacantes (atribuídos à SVR russa) injetaram código malicioso no processo de build do software, criando uma backdoor que se distribuía junto com atualizações legítimas.

O vetor de ataque foi o compilador e o pipeline de build. Os atacantes modificaram o processo de compilação para inserir código malicioso no binário final, sem alterar o código-fonte diretamente. Isso significa que auditorias de código-fonte não detectariam a comprometida.

```cpp
/*
 * O padrão SolarWinds: integração no pipeline de build.
 * Embora não possamos "proteger" contra um ataque que compromete o compilador,
 * podemos adotar práticas que tornam esse tipo de ataque mais difícil e detectável.
 */

/* 1. Reproducible Builds: garantir que o mesmo código-fonte produza o mesmo binário */
/* No CMakeLists.txt, use flags reproduzíveis: */

/* # Em CMakeLists.txt:
 * set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffile-prefix-map=${CMAKE_SOURCE_DIR}=/")
 * set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fmacro-prefix-map=${CMAKE_SOURCE_DIR}=/")
 * # Não incluir timestamps no binário:
 * set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -frandom-seed=0")
 */

/* 2. Verificação de integridade de dependências */
#include <string>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <openssl/sha.h>

std::string compute_sha256(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file) throw std::runtime_error("Cannot open file for hashing");

    SHA256_CTX ctx;
    SHA256_Init(&ctx);

    char buffer[8192];
    while (file.read(buffer, sizeof(buffer))) {
        SHA256_Update(&ctx, buffer, file.gcount());
    }
    SHA256_Update(&ctx, buffer, file.gcount());

    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_Final(hash, &ctx);

    std::ostringstream oss;
    for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(hash[i]);
    }
    return oss.str();
}

/* 3. Allowlist de dependências com hashes conhecidos */
bool verify_dependency(const std::string& path, const std::string& expected_hash) {
    std::string actual = compute_sha256(path);
    return actual == expected_hash;
}
```

A lição de SolarWinds: **a segurança da cadeia de suprimentos é responsabilidade de cada desenvolvedor**. Reproducible builds, verificação de integridade e auditoria de dependências não são opcionais em projetos sérios.

#### Qualcomm MSM — Vulnerabilidades no driver de GPU (CVE-2023-33106/33107)

Em 2023, vulnerabilidades críticas foram descobertas no driver MSM (Mobile Station Modem) da Qualcomm, que é usado em dispositivos Android com processadores Snapdragon. CVE-2023-33106 e CVE-2023-33107 eram vulnerabilidades de use-after-free e integer overflow que permitiam escalação de privilégios local.

O padrão de código vulnerável envolvia gestão inadequada de memória em drivers de kernel, onde objetos eram liberados enquanto referências ainda existiam, e valores de tamanho calculados pelo usuário causavam overflow em alocações de memória.

```cpp
/*
 * Padrão Qualcomm MSM: use-after-free em drivers de kernel.
 * Embora drivers de kernel usem C, o padrão se manifesta em qualquer
 * código C++ que gestiona memória de forma manual.
 */
#include <cstdint>
#include <cstring>

struct GpuBuffer {
    uint32_t size;
    uint8_t* data;
    uint32_t refcount;
};

/* PADRÃO VULNERÁVEL: use-after-free */
void process_gpu_command(GpuBuffer* buf, uint32_t user_size) {
    /* Integer overflow: se user_size é muito grande, a multiplica??o pode overflow */
    size_t alloc_size = static_cast<size_t>(buf->size) * user_size;  /* overflow */

    if (buf->refcount == 0) {
        free(buf->data);   /* libera o buffer */
        buf->data = nullptr;
    }

    buf->data = static_cast<uint8_t*>(malloc(alloc_size));
    if (!buf->data) return;

    /* Se alloc_size fez overflow e resultou em tamanho pequeno,
       o memcpy abaixo escreve além do buffer alocado */
    memcpy(buf->data, /* source */, alloc_size);
}

/* Versão SEGURA */
#include <limits>
#include <memory>

bool safe_process_gpu_command(GpuBuffer* buf, uint32_t user_size) {
    /* Verificar overflow antes da multiplica??o */
    if (buf->size != 0 && user_size > std::numeric_limits<size_t>::max() / buf->size) {
        return false;  /* overflow detectado */
    }

    size_t alloc_size = static_cast<size_t>(buf->size) * user_size;

    if (alloc_size > 1024 * 1024 * 1024) {  /* limite razoável de 1GB */
        return false;
    }

    if (buf->refcount > 0) {
        return false;  /* ainda em uso, não liberar */
    }

    auto new_data = static_cast<uint8_t*>(std::realloc(buf->data, alloc_size));
    if (!new_data) return false;

    buf->data = new_data;
    buf->size = alloc_size;
    return true;
}
```

A lição: **drivers de kernel e código de nível inferior precisam de validação obsessiva de limites**. Integer overflow em cálculos de tamanho de alocação é um dos padrões mais perigosos em C/C++.

#### Android Kernel — CVE-2021-1048

Em 2021, uma vulnerabilidade no kernel Android (CVE-2021-1048) permitia escalação de privilégios através de um use-after-free no subsistema epoll. O atacante poderia explorar um bug na referência de contagem do epoll para obter acesso root em dispositivos Android.

```cpp
/*
 * Padrão CVE-2021-1048: reference count management em código C/C++.
 * O bug estava no kernel, mas o padrão é igualmente relevante em C++ user-space.
 */
#include <atomic>
#include <cstdint>

struct EpollInstance {
    std::atomic<int32_t> refcount;
    /* ... otros campos ... */
};

/* PADRÃO VULNERÁVEL: race condition na gestao de referências */
void epoll_ctl_add(EpollInstance* inst) {
    inst->refcount++;  /* NAO ATOMICO se nao usar atomic corretamente */
    /* ... adicionar ao epoll ... */
}

void epoll_ctl_del(EpollInstance* inst) {
    if (inst->refcount > 0) {
        inst->refcount--;  /* race condition: pode diminuir abaixo de zero */
    }
    if (inst->refcount == 0) {
        /* libera memória, mas outra thread pode ainda estar usando inst */
        delete inst;  /* USE-AFTER-FREE */
    }
}

/* Versão SEGURA: reference counting com atomicos */
void epoll_ctl_add_safe(EpollInstance* inst) {
    inst->refcount.fetch_add(1, std::memory_order_acq_rel);
    /* ... */
}

void epoll_ctl_del_safe(EpollInstance* inst) {
    if (inst->refcount.fetch_sub(1, std::memory_order_acq_rel) == 1) {
        /* refcount chegou a 0, seguro liberar */
        delete inst;
    }
}
```

#### Stuxnet (2010) — O primeiro ciberguerra

Stuxnet é considerado o primeiro worm projetado para causar dano físico a infraestrutura industrial. Descoberto em 2010, atacou sistemas SCADA da rede nuclear iraniana, destruindo aproximadamente 1.000 centrífugas de urânio. O worm explorou quatro zero-days simultaneamente, incluindo vulnerabilidades em drivers Windows e no protocolo Siemens S7.

A lição de Stuxnet vai além do código: **sistemas críticos precisam de defesa em camadas**. Nenhuma única correção de código é suficiente quando o sistema controla infraestrutura física. Mas o ponto de entrada era software — e aquele software poderia ter sido escrito com práticas de segurança mais rigorosas.

#### macOS Gatekeeper — Bypasses de verificação

Diversos bypasses do Gatekeeper do macOS foram documentados ao longo dos anos. O Gatekeeper verifica a assinatura digital de aplicações antes de permitir sua execução, mas vulnerabilidades permitiram que aplicações não assinadas ou maliciosas contornassem essas verificações. Em 2021, um pesquisador demonstrou que qualquer aplicação baixada via HTTP (não HTTPS) era tratada como se tivesse sido baixada localmente, ignorando as verificações de assinatura.

```cpp
/*
 * Padrão Gatekeeper bypass: verificação de segurança que depende de metadados
 * em vez de conteúdo real.
 *
 * Em C++, isso aparece quando validamos baseados em extensão de arquivo
 * ou metadados em vez de conteúdo real.
 */
#include <string>
#include <filesystem>

/* PADRÃO VULNERÁVEL: confiar na extensão do arquivo */
bool is_safe_executable(const std::string& filepath) {
    namespace fs = std::filesystem;
    fs::path p(filepath);
    std::string ext = p.extension().string();
    /* Apenas nega extensões conhecidas como perigosas, mas ignora outras */
    return ext != ".exe" && ext != ".bat" && ext != ".sh";
}

/* Versão SEGURA: verificar o conteúdo real */
#include <array>
#include <fstream>

bool has_valid_elf_header(const std::string& filepath) {
    std::ifstream f(filepath, std::ios::binary);
    if (!f) return false;

    std::array<uint8_t, 4> magic{};
    f.read(reinterpret_cast<char*>(magic.data()), 4);
    /* ELF magic number: 0x7F 'E' 'L' 'F' */
    return magic[0] == 0x7F && magic[1] == 'E' && magic[2] == 'L' && magic[3] == 'F';
}

bool verify_code_signature(const std::string& filepath) {
    /* Na prática: usar codesign, osslsigncode ou similar */
    /* Nunca confiar apenas na extensão ou metadados */
    return has_valid_elf_header(filepath);
}
```

### 1.4 Filosofia deste livro

Segurança não é uma feature — é uma **propriedade** de um sistema. Não se adiciona "segurança" ao final de um projeto como se fosse um botão. Segurança emerge de decisões corretas tomadas consistentemente ao longo do ciclo de vida do software: desde o design até a operação.

Este livro adota o paradigma de **Desenvolvimento Orientado à Segurança** (Security-Driven Development), onde cada decisão de design, cada linha de código e cada escolha arquitetural é avaliada sob a ótica da segurança. Não se trata de transformar desenvolvedores em especialistas em segurança, mas de equipá-los com o conhecimento necessário para escrever código que resista aos vetores de ataque mais comuns e mais perigosos.

O público-alvo são desenvolvedores C++ que querem entender não apenas *como* proteger seu código, mas *por que* certas proteções são necessárias. A compreensão do mecanismo de um ataque é o primeiro passo para construir defesas eficazes.

---

## 2. Obrigação Ética do Desenvolvedor

### 2.1 O contrato social do software

Quando um desenvolvedor escreve software, assume implicitamente um contrato social com todos os usuários daquele software. Esse contrato implica que o código foi escrito com diligência razoável, que vulnerabilidades conhecidas foram corrigidas, e que os dados dos usuários são tratados com responsabilidade.

Esse contrato não é apenas moral — ele tem fundamento legal em diversas jurisdições. No Brasil, a Constituição Federal (art. 5, incisos X e XII), a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018), o Marco Civil da Internet (Lei nº 12.965/2014) e o Código de Defesa do Consumidor estabelecem obrigações concretas para quem desenvolve e disponibiliza software.

### 2.2 Responsabilidade profissional

AAssociação Brasileira de Engenharia de Software (ABES) e o Conselho Federal de Engenharia e Agronomia (CONFEA) estabelecem códigos de ética que se aplicam a engenharia de software. Embora o desenvolvimento de software não seja regulamentado da mesma forma que engenharia civil, existe uma tendência crescente de responsabilização profissional.

Desenvolvedores podem ser responsabilizados civilmente por negligência em segurança de software quando:
- Conheciam vulnerabilidades e não as corrigiram
- Não implementaram práticas de segurança padrão da indústria
- Coletaram dados sem consentimento adequado
- Não notificaram usuários sobre violações de dados

### 2.3 LGPD e implicações para desenvolvedores

A LGPD (Lei nº 13.709/2018) estabelece princípios e obrigações para o tratamento de dados pessoais. Para desenvolvedores C++, isso significa:

- **Privacy by Design**: segurança deve ser incorporada desde a concepção do sistema
- **Criptografia**: dados sensíveis devem ser criptografados em repouso e em trânsito
- **Minimização**: coletar apenas os dados estritamente necessários
- **Registro de operações**: manter logs de acesso a dados pessoais
- **Comunicação de incidentes**: notificar a ANPD e os titulares em caso de violação

```cpp
/*
 * Exemplo: tratamento seguro de dados pessoais sob LGPD
 */
#include <string>
#include <memory>
#include <chrono>

struct PersonalData {
    std::string name;
    std::string cpf;          /* dados sensíveis: CPF */
    std::string email;
    std::chrono::system_clock::time_point collection_date;
    bool consent_given;
};

/*
 * Validação de consentimento antes de processar dados pessoais.
 * Sob a LGPD, dados sem consentimento não devem ser processados.
 */
bool validate_consent(const PersonalData& data) {
    if (!data.consent_given) {
        return false;
    }
    /* Verificar se o consentimento não expirou (ex: 12 meses) */
    auto now = std::chrono::system_clock::now();
    auto elapsed = now - data.collection_date;
    auto twelve_months = std::chrono::hours(24 * 365);
    return elapsed < twelve_months;
}

/*
 * Criptografia de dados sensíveis antes de persistir em disco.
 */
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <vector>
#include <stdexcept>

struct EncryptedData {
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> iv;
    std::vector<uint8_t> tag;  /* para AES-GCM */
};

EncryptedData encrypt_pii(const std::string& plaintext,
                           const unsigned char key[32]) {
    EncryptedData result;
    result.iv.resize(12);  /* AES-GCM IV: 12 bytes */
    if (RAND_bytes(result.iv.data(), 12) != 1) {
        throw std::runtime_error("Failed to generate IV");
    }

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) throw std::runtime_error("Failed to create cipher context");

    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, key,
                           result.iv.data()) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to initialize encryption");
    }

    result.ciphertext.resize(plaintext.size() + EVP_MAX_BLOCK_LENGTH);
    int out_len = 0;

    if (EVP_EncryptUpdate(ctx, result.ciphertext.data(), &out_len,
                          reinterpret_cast<const unsigned char*>(plaintext.data()),
                          plaintext.size()) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Encryption failed");
    }

    int final_len = 0;
    if (EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + out_len,
                            &final_len) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Encryption finalization failed");
    }
    out_len += final_len;
    result.ciphertext.resize(out_len);

    result.tag.resize(16);
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16,
                            result.tag.data()) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Failed to get GCM tag");
    }

    EVP_CIPHER_CTX_free(ctx);
    return result;
}
```

### 2.4 Casos de responsabilização

Existem precedentes documentados de desenvolvedores e organizações responsabilizados por falhas de segurança:

- **Equifax (2017)**: breach afetou 147 milhões de pessoas. A empresa pagou US$ 700 milhões em acordo. O CVE-2017-5638 (Apache Struts) era conhecido e patches estavam disponíveis há meses
- **Uber (2016)**: breach de 57 milhões de contas. Executivos tentaram ocultar o incidente, resultando em acusações penais
- **TARGET (2013)**: breach de 40 milhões de cartões de crédito através de terceiro (fornecedor de refrigeração)

### 2.5 Casos públicos documentados — Impacto ético

#### Equifax (2017) — Falha de gestão de vulnerabilidades

O breach da Equifax é um dos exemplos mais claros de responsabilização por negligência em segurança. A vulnerabilidade CVE-2017-5638 no Apache Struts permitia execução remota de código. Um patch estava disponível desde março de 2017, mas a Equifax não o aplicou. O breach ocorreu em maio-julho de 2017.

A lição ética é clara: **manter software desatualizado quando patches de segurança críticos estão disponíveis é negligência**. Para desenvolvedores C++, isso significa que monitorar CVEs das dependências e aplicar atualizações tempestivamente é obrigação profissional, não opcional.

```cpp
/*
 * Padrão Equifax: dependências desatualizadas.
 * Ferramentas como Dependabot, Renovate ou Conan devem monitorar dependências.
 *
 * Exemplo: verificação de versão de biblioteca no código-fonte
 */
#include <string>
#include <sstream>

struct LibraryVersion {
    int major;
    int minor;
    int patch;
};

LibraryVersion parse_version(const std::string& version_str) {
    LibraryVersion v{0, 0, 0};
    std::istringstream iss(version_str);
    char dot;
    iss >> v.major >> dot >> v.minor >> dot >> v.patch;
    return v;
}

bool is_version_vulnerable(const LibraryVersion& current,
                           const LibraryVersion& fixed) {
    if (current.major != fixed.major) return current.major < fixed.major;
    if (current.minor != fixed.minor) return current.minor < fixed.minor;
    return current.patch < fixed.patch;
}

/* No build system (CMake), usar:
 * find_package(OpenSSL REQUIRED)
 * Versão mínima especificada para evitar vulnerabilidades conhecidas
 */
```

#### SolarWinds — Falha ética na cadeia de suprimentos

O ataque SolarWinds levantou questões éticas fundamentais sobre a responsabilidade de fornecedores de software na segurança de seus clientes. A comprometida cadeia de suprimentos afetou agências governamentais e empresas privadas que confiavam nas atualizações do SolarWinds.

A lição ética: **a confiança que usuários depositam em atualizações de software impõe uma obrigação moral de garantir a integridade do processo de build e distribuição**.

---

## 3. Público-Alvo e Pré-Requisitos

### 3.1 Quem deve ler este livro

Este livro foi escrito para três públicos principais:

**Desenvolvedores C++ com experiência intermediária a avançada**
- Que trabalham com código de produção e querem incorporar segurança em seu fluxo de trabalho
- Que já possuem familiaridade com conceitos como RAII, templates e gerenciamento de memória
- Que reconhecem que segurança é parte fundamental da qualidade do software

**Engenheiros de segurança que trabalham com software de sistema**
- Que precisam de conhecimento profundo sobre vulnerabilidades em C++ para conduzir revisões de código e testes de penetração
- Que querem entender os mecanismos de exploits em código nativo

**Arquitetos e tech leads**
- Que definem padrões de código e processos de revisão para equipes C++
- Que precisam de argumentos técnicos para justificar investimentos em segurança
- Que buscam estabelecer uma cultura de segurança em suas equipes

### 3.2 Pré-requisitos técnicos

**Conhecimento de C++ (obrigatório)**
- C++17 assume-se como base mínima
- Familiaridade com templates, RAII, smart pointers
- Compreensão de lifetime de objetos e gerenciamento de memória
- Experiência com compilação, linkage e sistemas de build

**Conhecimento de segurança (NÃO obrigatório)**
- Este livro é autocontido em termos de segurança
- Conceitos são introduzidos progressivamente
- Não é necessário conhecimento prévio de criptografia, redes ou engenharia reversa
- Referências são fornecidas para estudo aprofundado

**Ferramentas (obrigatório)**
- Compilador C++17 (GCC 12+, Clang 16+, ou MSVC 2022+)
- CMake 3.20+
- Linux (preferencialmente) ou WSL2
- Conta GitHub para acesso ao repositório companion

### 3.3 Como usar este livro

Este livro pode ser lido de forma sequencial ou por módulos. Cada capítulo é relativamente autocontido, mas capitulos posteriores fazem referências a conceitos introduzidos anteriormente.

**Caminho recomendado para iniciantes**: Capítulos 1-5 (fundamentos) → Capítulos 6-8 (padrões) → Capítulos 9-12 (avançado)

**Caminho para profissionais experientes**: Capítulos 1-2 (fundamentos) → Capítulos selecionados conforme necessidade → Capítulo 17 (referências)

**Caminho para arquitetos**: Capítulos 1-3 (fundamentos) → Capítulos 13-16 (segurança em larga escala) → Capítulo 17 (referências)

---

## 4. Ambiente de Desenvolvimento

### 4.1 Configuração do toolchain

Este livro assume um ambiente Linux (Ubuntu 22.04+ ou equivalente) com os seguintes compiladores:

| Compilador | Versão mínima | Observações |
|-----------|---------------|-------------|
| GCC       | 12+           | Suporte completo a C++17, sanitizers integrados |
| Clang     | 16+           | Excelente suporte a sanitizers e static analysis |
| MSVC      | 2022+         | Para desenvolvimento Windows, usar WSL2 para tools Linux |

Instalação no Ubuntu/Debian:

```bash
# GCC e Clang
sudo apt update
sudo apt install -y g++-12 clang-16 lld-16

# CMake
sudo apt install -y cmake

# Ferramentas de análise
sudo apt install -y valgrind clang-tidy-16 cppcheck

# Ferramentas de fuzzing
sudo apt install -y afl++ libfuzzer-16-dev

# OpenSSL (para exemplos de criptografia)
sudo apt install -y libssl-dev

# Google Benchmark e Google Test
sudo apt install -y libgtest-dev libgmock-dev libbenchmark-dev
```

### 4.2 Ferramentas de análise estática

#### clang-tidy

clang-tidy é o principal ferramenta de análise estática para C++. Ele verifica padrões de código, identifica bugs potenciais e sugere correções automáticas.

Arquivo de configuração `.clang-tidy` completo para projetos seguros:

```yaml
---
Checks: >
  -*,
  bugprone-*,
  -bugprone-easily-swappable-parameters,
  -bugprone-narrowing-conversions,
  cert-*,
  clang-analyzer-*,
  cppcoreguidelines-*,
  -cppcoreguidelines-avoid-magic-numbers,
  -cppcoreguidelines-avoid-c-arrays,
  -cppcoreguidelines-pro-bounds-pointer-arithmetic,
  -cppcoreguidelines-pro-bounds-constant-array-index,
  google-build-explicit-make-pair,
  google-readability-casting,
  misc-redundant-expression,
  misc-unused-using-decls,
  modernize-*,
  -modernize-use-trailing-return-type,
  performance-*,
  readability-braces-around-statements,
  readability-identifier-naming,
  security-*,

WarningsAsErrors: >
  bugprone-argument-comment,
  bugprone-assert-side-effect,
  bugprone-dangling-handle,
  bugprone-infinite-loop,
  bugprone-narrowing-conversions,
  bugprone-sizeof-expression,
  bugprone-suspicious-string-compare,
  bugprone-undelegated-constructor,
  cert-dcl50-cpp,
  cert-err33-c,
  cert-err34-c,
  cert-err52-cpp,
  cert-err58-cpp,
  cert-flp30-c,
  cert-msc24-c,
  cert-msc32-c,
  cert-msc50-cpp,
  clang-analyzer-core.NullDereference,
  clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling,
  cppcoreguidelines-avoid-c-arrays,
  cppcoreguidelines-avoid-goto,
  cppcoreguidelines-init-variables,
  cppcoreguidelines-narrowing-conversions,
  cppcoreguidelines-pro-type-cstyle-cast,
  cppcoreguidelines-pro-type-member-init,
  cppcoreguidelines-slicing,
  google-build-explicit-make-pair,
  misc-misplaced-const,
  misc-redundant-expression,
  performance-unnecessary-value-param,
  readability-implicit-bool-conversion,

HeaderFilterRegex: 'src/.*\.hpp$'

CheckOptions:
  - key: readability-identifier-naming.ClassCase
    value: CamelCase
  - key: readability-identifier-naming.FunctionCase
    value: camelBack
  - key: readability-identifier-naming.VariableCase
    value: camelBack
  - key: readability-identifier-naming.ConstantCase
    value: UPPER_CASE
  - key: readability-identifier-naming.NamespaceCase
    value: lower_case
  - key: bugprone-argument-comment.StrictMode
    value: '1'
  - key: cppcoreguidelines-init-variables.CheckAsUserAssigned
    value: '0'
```

Uso:

```bash
# Analisar todos os arquivos do projeto
clang-tidy-16 src/*.cpp -- -std=c++17 -Iinclude

# Corrigir automaticamente problemas encontrados
clang-tidy-16 src/*.cpp --fix -- -std=c++17 -Iinclude
```

#### cppcheck

cppcheck é uma ferramenta complementar ao clang-tidy, focada em detecção de bugs específicos de C/C++:

```bash
# Análise básica
cppcheck --std=c++17 --enable=all --suppress=missingIncludeSystem src/

# Análise com foco em segurança
cppcheck --std=c++17 --enable=warning,style,performance,portability \
    --check-level=exhaustive src/
```

#### Facebook Infer

Infer é uma ferramenta de análise estática baseada em teoria de tipos e separação, particularmente eficaz para detectar memory leaks, null pointer dereferences e race conditions:

```bash
# Análise com Infer
infer run -- make -j4

# Infer com configuração específica para C++
infer run --compilation-database compile_commands.json
```

### 4.3 Sanitizers

Sanitizers são ferramentas de runtime que detectam erros de memória, concorrência e comportamento indefinido. Eles são indispensáveis para desenvolvimento seguro em C++.

#### AddressSanitizer (ASan)

Detecta: buffer overflows, use-after-free, double-free, memory leaks:

```bash
# Compilar com ASan
g++-12 -std=c++17 -g -fsanitize=address -fno-omit-frame-pointer \
    -fsanitize-address-use-after-scope \
    -o my_program src/*.cpp

# Executar
./my_program
# Saída: relatório detalhado de qualquer erro de memória
```

#### ThreadSanitizer (TSan)

Detecta: data races, deadlocks, race conditions:

```bash
# Compilar com TSan
g++-12 -std=c++17 -g -fsanitize=thread -pthread \
    -o my_program src/*.cpp
```

#### UndefinedBehaviorSanitizer (UBSan)

Detecta: integer overflow, shift por valor inválido, null pointer arithmetic:

```bash
# Compilar com UBSan
g++-12 -std=c++17 -g -fsanitize=undefined,bounds,null \
    -fsanitize-recover=all \
    -o my_program src/*.cpp
```

### 4.4 Fuzzing

#### libFuzzer

libFuzzer é um fuzzing engine que encontra bugs automaticamente gerando inputs aleatórios:

```cpp
/*
 * Exemplo de alvo de fuzzing: parser de mensagens de rede
 */
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <vector>

struct ParsedMessage {
    uint16_t id;
    uint8_t type;
    std::vector<uint8_t> payload;
    bool valid;
};

ParsedMessage parse_message(const uint8_t* data, size_t size) {
    ParsedMessage result{0, 0, {}, false};
    if (size < 4) return result;

    result.id = static_cast<uint16_t>(data[0] | (data[1] << 8));
    result.type = data[2];
    uint16_t payload_len = static_cast<uint16_t>(data[3] | (data[4] << 8));

    if (size < 5 + payload_len) return result;

    result.payload.assign(data + 5, data + 5 + payload_len);
    result.valid = true;
    return result;
}

/* Entry point para libFuzzer */
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    auto msg = parse_message(data, size);
    if (msg.valid) {
        /* Processar mensagem válida */
        volatile uint8_t dummy = msg.payload[0];
        (void)dummy;
    }
    return 0;
}
```

Compilação e execução do fuzzer:

```bash
# Compilar com libFuzzer + ASan
g++-12 -std=c++17 -g -fsanitize=fuzzer,address \
    -o fuzz_parser src/fuzz_parser.cpp

# Executar fuzzing
./fuzz_parser -max_len=1024 -timeout=10
```

#### AFL++

AFL++ é um fuzzer baseado em cobertura de código que gera inputs de forma mais inteligente:

```bash
# Compilar para AFL++
afl++-clang++ -std=c++17 -g -o fuzz_afl src/fuzz_parser.cpp

# Executar fuzzing
mkdir -p input output
echo -ne '\x01\x00\x01\x00' > input/seed.bin
afl++-fuzz -i input -o output ./fuzz_afl
```

### 4.5 CMakeLists.txt completo para projeto seguro

Abaixo está um CMakeLists.txt completo, production-ready, com todas as flags de segurança recomendadas:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SecureCppProject
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Example project with security-hardened build configuration"
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ==============================================================================
# SECURITY FLAGS — Core hardening for all builds
# ==============================================================================

# Stack protection: canary values detect buffer overflows
add_compile_options(-fstack-protector-strong)

# FORTIFY_SOURCE: runtime checks for buffer overflows in libc functions
add_compile_definitions(_FORTIFY_SOURCE=2)

# Position-independent executable: enables full ASLR
add_compile_options(-fPIE)
add_link_options(-pie)

# Format string protection
add_compile_options(-Wformat -Wformat-security)

# Additional security-related warnings
add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
    -Wconversion
    -Wsign-conversion
    -Wnull-dereference
    -Wimplicit-fallthrough
    -Wdouble-promotion
    -Wformat=2
    -Werror=format-security
    -Wstack-protector
)

# Disable dangerous features
add_compile_options(
    -fno-exceptions
    -fno-rtti
)

# For projects that need exceptions (comment above and use this instead):
# add_compile_options(
#     -fexceptions
#     -frtti
# )

# ==============================================================================
# COMPILER-SPECIFIC SECURITY FLAGS
# ==============================================================================

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    # Control Flow Integrity
    add_compile_options(-fcf-protection=full)

    # Dead code elimination for cleaner binaries
    add_compile_options(-ffunction-sections -fdata-sections)
    add_link_options(-Wl,--gc-sections)

    # Stack clash protection (GCC 8+, Clang 11+)
    add_compile_options(-fstack-clash-protection)

    # Retpoline for Spectre v2 mitigation
    add_compile_options(-mretpoline)

    # Strict aliasing
    add_compile_options(-fstrict-aliasing)

    # Trap on integer overflow (GCC only)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
        add_compile_options(-ftrapv)
    endif()
endif()

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    # Control Flow Integrity — forward-edge (Clang-specific)
    add_compile_options(-fsanitize=cfi -fvisibility=hidden)
    add_link_options(-fsanitize=cfi)
endif()

if(MSVC)
    add_compile_options(
        /GS       # Buffer security check (stack canaries)
        /DYNAMICBASE  # ASLR
        /NXCOMPAT     # DEP/NX
        /guard:cf     # Control Flow Guard
        /sdl          # Security Development Lifecycle checks
        /W4           # High warning level
    )
    add_link_options(/GUARD:CF /NXCOMPAT /DYNAMICBASE)
endif()

# ==============================================================================
# BUILD TYPES
# ==============================================================================

# Debug build with sanitizers
set(CMAKE_CXX_FLAGS_DEBUG
    "-O0 -g3 -DDEBUG=1 \
     -fsanitize=address,undefined,leak \
     -fno-omit-frame-pointer \
     -fsanitize-address-use-after-scope \
     -fsanitize-recover=undefined"
    CACHE STRING "Debug build flags" FORCE)

# Release build with maximum hardening
set(CMAKE_CXX_FLAGS_RELEASE
    "-O2 -DNDEBUG=1 \
     -fstack-protector-strong \
     -D_FORTIFY_SOURCE=2 \
     -fcf-protection=full \
     -fstack-clash-protection \
     -Wformat -Wformat-security"
    CACHE STRING "Release build flags" FORCE)

# RelWithDebInfo: optimized but debuggable
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO
    "-O2 -g -DNDEBUG=1 \
     -fsanitize=address,undefined \
     -fno-omit-frame-pointer"
    CACHE STRING "RelWithDebInfo build flags" FORCE)

# Sanitizers build: all sanitizers enabled
set(CMAKE_CXX_FLAGS_SANITIZERS
    "-O1 -g3 -DDEBUG=1 \
     -fsanitize=address,thread,undefined,leak \
     -fno-omit-frame-pointer \
     -fsanitize-address-use-after-scope \
     -fsanitize-recover=undefined"
    CACHE STRING "Sanitizers build flags" FORCE)

# ==============================================================================
# OPTIONS
# ==============================================================================

option(ENABLE_COVERAGE "Enable code coverage" OFF)
option(ENABLE_HARDENING "Enable extra hardening flags" ON)
option(BUILD_TESTS "Build test suite" ON)
option(BUILD_FUZZERS "Build fuzz targets" OFF)

if(ENABLE_COVERAGE)
    add_compile_options(--coverage -O0 -g)
    add_link_options(--coverage)
endif()

# ==============================================================================
# DEPENDENCIES
# ==============================================================================

find_package(OpenSSL REQUIRED)

# ==============================================================================
# MAIN TARGET
# ==============================================================================

add_library(secure_project_lib STATIC
    src/core.cpp
    src/crypto.cpp
    src/network.cpp
)

target_include_directories(secure_project_lib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(secure_project_lib
    PUBLIC
        OpenSSL::SSL
        OpenSSL::Crypto
)

# ==============================================================================
# TESTS
# ==============================================================================

if(BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)

    add_executable(security_tests
        tests/test_crypto.cpp
        tests/test_network.cpp
        tests/test_parser.cpp
    )

    target_link_libraries(security_tests
        GTest::GTest
        GTest::Main
        secure_project_lib
    )

    target_compile_options(security_tests PRIVATE
        -fsanitize=address,undefined
    )

    include(GoogleTest)
    gtest_discover_tests(security_tests)
endif()

# ==============================================================================
# FUZZ TARGETS
# ==============================================================================

if(BUILD_FUZZERS)
    add_executable(fuzz_parser
        fuzzing/fuzz_parser.cpp
    )
    target_link_libraries(fuzz_parser
        secure_project_lib
    )
    target_compile_options(fuzz_parser PRIVATE
        -fsanitize=fuzzer,address,undefined
    )
endif()

# ==============================================================================
# INSTALL
# ==============================================================================

install(TARGETS secure_project_lib
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/
    DESTINATION include
)

# ==============================================================================
# COMPILE_COMMANDS (for clang-tidy and IDE support)
# ==============================================================================

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

### 4.6 CMake Presets

Para facilitar a gestão de múltiplas configurações, use CMake presets:

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "debug",
            "displayName": "Debug with Sanitizers",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/debug",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_HARDENING": "ON",
                "ENABLE_COVERAGE": "OFF",
                "BUILD_TESTS": "ON",
                "BUILD_FUZZERS": "OFF"
            }
        },
        {
            "name": "release",
            "displayName": "Release with Hardening",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/release",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "ENABLE_HARDENING": "ON",
                "ENABLE_COVERAGE": "OFF",
                "BUILD_TESTS": "ON",
                "BUILD_FUZZERS": "OFF"
            }
        },
        {
            "name": "sanitizers",
            "displayName": "All Sanitizers Enabled",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/sanitizers",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Sanitizers",
                "ENABLE_HARDENING": "ON",
                "ENABLE_COVERAGE": "OFF",
                "BUILD_TESTS": "ON",
                "BUILD_FUZZERS": "ON"
            }
        },
        {
            "name": "fuzz",
            "displayName": "Fuzzing Build",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/fuzz",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_HARDENING": "OFF",
                "ENABLE_COVERAGE": "OFF",
                "BUILD_TESTS": "OFF",
                "BUILD_FUZZERS": "ON"
            }
        },
        {
            "name": "coverage",
            "displayName": "Coverage Build",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/coverage",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_HARDENING": "OFF",
                "ENABLE_COVERAGE": "ON",
                "BUILD_TESTS": "ON",
                "BUILD_FUZZERS": "OFF"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "debug",
            "configurePreset": "debug"
        },
        {
            "name": "release",
            "configurePreset": "release"
        },
        {
            "name": "sanitizers",
            "configurePreset": "sanitizers"
        },
        {
            "name": "fuzz",
            "configurePreset": "fuzz"
        },
        {
            "name": "coverage",
            "configurePreset": "coverage"
        }
    ],
    "testPresets": [
        {
            "name": "debug",
            "configurePreset": "debug",
            "output": {
                "outputOnFailure": true
            }
        },
        {
            "name": "sanitizers",
            "configurePreset": "sanitizers",
            "output": {
                "outputOnFailure": true
            },
            "environment": {
                "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=0",
                "UBSAN_OPTIONS": "print_stacktrace=1:halt_on_error=0",
                "TSAN_OPTIONS": "halt_on_error=0"
            }
        }
    ]
}
```

### 4.7 Git Hooks para segurança

Configure pre-commit hooks para análise automática:

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Executa clang-tidy e verifica padrões de segurança

set -e

echo "Running clang-tidy..."
CHANGED_CPP=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(cpp|hpp|cc|cxx)$' || true)

if [ -n "$CHANGED_CPP" ]; then
    for file in $CHANGED_CPP; do
        clang-tidy-16 "$file" -- -std=c++17 -Iinclude 2>&1 | \
            grep -E '(warning:|error:)' && {
            echo "clang-tidy found issues in $file"
            exit 1
        }
    done
fi

echo "Checking for forbidden patterns..."

# Verificar secrets hardcoded
if git diff --cached --name-only | xargs grep -lE '(password|secret|api_key|token)\s*=\s*"[^"]+' 2>/dev/null; then
    echo "ERROR: Possible hardcoded secrets detected!"
    echo "Use environment variables or secret managers instead."
    exit 1
fi

# Verificar uso de funções perigosas
if git diff --cached | grep -E '^\+.*\b(strcpy|strcat|sprintf|gets)\s*\(' ; then
    echo "ERROR: Use safe alternatives (strncpy, strncat, snprintf, std::getline)"
    exit 1
fi

echo "Pre-commit checks passed."
```

### 4.8 Exemplo completo: configuração de projeto seguro

Arquivo de configuração completa para um projeto seguro:

```
project-root/
├── CMakeLists.txt              # Build system com security flags
├── CMakePresets.json            # Presets para diferentes configs
├── .clang-tidy                  # Análise estática
├── .clang-format                # Formatação consistente
├── .gitignore
├── .git/hooks/pre-commit       # Hook de segurança
├── include/
│   └── secure_project/
│       ├── crypto.hpp
│       ├── network.hpp
│       └── parser.hpp
├── src/
│   ├── core.cpp
│   ├── crypto.cpp
│   └── network.cpp
├── tests/
│   ├── test_crypto.cpp
│   ├── test_network.cpp
│   └── test_parser.cpp
├── fuzzing/
│   ├── fuzz_parser.cpp
│   └── fuzz_network.cpp
├── docs/
│   ├── SECURITY.md
│   └── threat-model.md
└── ci/
    ├── security-scan.yml
    └── fuzzing.yml
```

---

## 5. Convenções do Livro

### 5.1 Blocos de código

Todos os exemplos de código neste livro são C++17 compiláveis. Para compilar um exemplo, salve-o em um arquivo `.cpp` e use:

```bash
g++-12 -std=c++17 -o example example.cpp -lssl -lcrypto
```

Ou com Clang:

```bash
clang++-16 -std=c++17 -o example example.cpp -lssl -lcrypto
```

Nomes de variáveis, funções e comentários dentro do código estão em inglês, seguindo convenções padrão da indústria. O texto explicativo ao redor do código está em português brasileiro.

### 5.2 Padrão "vulnerável vs. seguro"

Este livro apresenta vulnerabilidades usando um padrão consistente:

1. **Código vulnerável**: mostra o padrão perigoso com comentários explicando o que está errado
2. **Análise**: explica o mecanismo de ataque e por que o código é vulnerável
3. **Código seguro**: mostra a correção com explicações sobre as proteções implementadas

Exemplo do padrão:

```cpp
/*
 * ============================================
 * CÓDIGO VULNERÁVEL — NÃO USE EM PRODUÇÃO
 * ============================================
 */
void process_input_vulnerable(const char* user_input) {
    char buffer[64];
    /* BUG: strcpy não valida o tamanho da entrada.
       Se user_input > 64 bytes, overflow de buffer. */
    strcpy(buffer, user_input);  /* CWE-120: Buffer Copy without Checking Size of Input */
    printf("Processing: %s\n", buffer);
}

/*
 * ============================================
 * CÓDIGO SEGURO
 * ============================================
 */
void process_input_safe(const char* user_input, size_t input_len) {
    constexpr size_t BUFFER_SIZE = 64;
    if (input_len >= BUFFER_SIZE) {
        fprintf(stderr, "Input too long: %zu >= %zu\n", input_len, BUFFER_SIZE);
        return;
    }
    char buffer[BUFFER_SIZE];
    strncpy(buffer, user_input, BUFFER_SIZE - 1);
    buffer[BUFFER_SIZE - 1] = '\0';
    printf("Processing: %s\n", buffer);
}

/* Versão moderna C++17: */
#include <string>
#include <string_view>

std::string process_input_modern(std::string_view user_input) {
    constexpr size_t MAX_LENGTH = 64;
    if (user_input.size() >= MAX_LENGTH) {
        throw std::out_of_range("Input exceeds maximum length");
    }
    return std::string(user_input);
}
```

### 5.3 Referências CWE/OWASP

Cada vulnerabilidade apresentada é mapeada para classificações CWE (Common Weakness Enumeration) e, quando aplicável, para OWASP. Isso permite:

- Rastrear padrões de vulnerabilidade em ferramentas de análise
- Correlacionar com bases de dados de CVEs
- Usar como referência em auditorias de segurança

Exemplo de referência:

| CWE | OWASP | Descrição |
|-----|-------|-----------|
| CWE-120 | A03:2021 | Buffer Copy without Checking Size of Input |
| CWE-416 | A03:2021 | Use After Free |
| CWE-787 | A03:2021 | Out-of-bounds Write |
| CWE-190 | A04:2021 | Integer Overflow or Wraparound |

### 5.4 Convencionais de formatação

**Avisos de segurança** são apresentados em blocos destacados:

> **ATENCAO**: Código ou padrão que representa risco imediato de segurança.

**Dicas** são apresentadas em blocos informativos:

> **DICA**: Informação útil para implementação ou configuração.

**Padrões perigosos** são marcados com o identificador CWE correspondente.

---

## 6. Estrutura do Livro

Este livro é organizado em 17 capítulos, agrupados em quatro módulos:

### Módulo 1: Fundamentos (Capítulos 1-4)

**Capítulo 1 — Modelo de Ameaças e Análise de Risco**
Introduz o conceito de threat modeling aplicado a C++. Apresenta STRIDE, DREAD e como identificar superfícies de ataque em aplicações C++. Inclui exemplos práticos de como mapear trust boundaries e data flow diagrams.

**Capítulo 2 — Memória Segura: Alocação, Lifetime e RAII**
Profundiza em gerenciamento seguro de memória em C++. Cobertura de smart pointers (unique_ptr, shared_ptr, weak_ptr), allocators personalizados, RAII patterns, e como evitar use-after-free, double-free e dangling pointers. Inclui análise de CVE-2023-33106 (Qualcomm MSM).

**Capítulo 3 — Validação de Entrada e Sanitização**
Cobre todas as formas de entrada em uma aplicação C++: dados de rede, argumentos de linha de commande, variáveis de ambiente, arquivos. Apresenta técnicas de validação, whitelisting, encoding/decoding seguro e fuzzing.

**Capítulo 4 — Criptografia Aplicada em C++**
Introduz OpenSSL libcrypto e principais primitivas criptográficas: AES-GCM, RSA, SHA-256, HKDF. Cobre chaveamento seguro, gestão de chaves, assinaturas digitais e TLS. Inclui exemplos usando C++ wrapper para OpenSSL.

### Módulo 2: Padrões de Segurança (Capítulos 5-8)

**Capítulo 5 — Padrões de Concorrência Segura**
Mutex, condition variables, atomics, memory model do C++17. Detectando e prevenindo data races com ThreadSanitizer. Padrões de lock-free programming e como evitá-los quando não são necessários.

**Capítulo 6 — Tratamento Seguro de Erros e Exceções**
Erros em código de segurança podem ser vetores de ataque. Cobre error handling que não vaza informações, noexcept correctness, e como exceções interagem com recursos de segurança.

**Capítulo 7 — Autenticação e Autorização em Código**
Implementação segura de autenticação (bcrypt, Argon2), controle de acesso baseado em roles, tokens JWT, e gestão de sessões em C++. Padrões para evitar timing attacks em comparações.

**Capítulo 8 — Proteção Contra Engenharia Reversa**
Ofuscação de código,anti-debugging, integrity checks, code signing. Limites e trade-offs dessas técnicas. Alternativas baseadas em arquitetura.

### Módulo 3: Infraestrutura e Sistemas (Capítulos 9-12)

**Capítulo 9 — Segurança em Redes com C++**
Programação de sockets seguros, TLS/SSL com OpenSSL, detecção de man-in-the-middle, certificate pinning. Segurança em protocolos customizados.

**Capítulo 10 — Drivers e Código de Kernel**
Específico para desenvolvimento de drivers Linux/Windows. User/kernel space boundary, DMA attacks, ioctl security, e como CVEs de kernel (CVE-2021-1048, CVE-2023-33106) se manifestam em código.

**Capítulo 11 — Segurança em Sistemas Embarcados**
Restrições de memória e processamento. Boot seguro, secure boot chains, firmware integrity. Padrões para sistemas com recursos limitados.

**Capítulo 12 — Segurança em Containers e Virtualização**
Isolamento de processos, namespaces, cgroups. Sandbox escapes e como preveni-los. Segurança em或questões de container escapes.

### Módulo 4: Processos e Governança (Capítulos 13-17)

**Capítulo 13 — Segurança no Pipeline CI/CD**
Integração de ferramentas de segurança no pipeline de build. SAST/DAST, dependency scanning, SBOM generation. GitHub Actions e GitLab CI para segurança.

**Capítulo 14 — Code Review Orientado à Segurança**
Checklists de code review para segurança. Padrões de review assíncrono. Como encontrar vulnerabilidades em revisão de código.

**Capítulo 15 — Resposta a Incidentes e Forense Digital**
O que fazer quando uma vulnerabilidade é descoberta. Coleta de evidências, preservação de logs, comunicação com stakeholders. Post-mortem analysis.

**Capítulo 16 — Conformidade e Auditoria**
LGPD, GDPR, PCI-DSS, SOC2 para código C++. Como preparar código para auditorias. Documentação de controles de segurança.

**Capítulo 17 — Referências e Recursos**
Bibliografia completa, ferramentas recomendadas, CVEs por categoria, glossário de termos de segurança, e links para comunidades.

### Grafo de dependências entre capítulos

```
Cap 1 (Threat Modeling)
├── Cap 2 (Memory Safety)
├── Cap 3 (Input Validation)
└── Cap 4 (Cryptography)
    ├── Cap 5 (Concurrency)
    ├── Cap 6 (Error Handling)
    ├── Cap 7 (Auth)
    └── Cap 8 (Anti-RE)
        ├── Cap 9 (Networks)
        ├── Cap 10 (Kernel)
        ├── Cap 11 (Embedded)
        └── Cap 12 (Containers)
            ├── Cap 13 (CI/CD)
            ├── Cap 14 (Code Review)
            ├── Cap 15 (Incident Response)
            └── Cap 16 (Compliance)
```

---

## 7. Como Acompanhar as Atualizações

### 7.1 CVE Tracking

O mundo de segurança de software muda constantemente. Novas vulnerabilidades são descobertas diariamente. Para manter-se atualizado:

**Fontes primárias de CVEs:**
- NIST NVD (nvd.nist.gov) — base oficial de CVEs
- MITRE CVE (cve.mitre.org) — registro e detalhes
- CVE.org — projeto original
- GitHub Advisory Database — foco em dependências open-source

**Fontes de análise de CVEs:**
- CISA KEV (Known Exploited Vulnerabilities) — CVEs com exploit conhecido ativo
- Packet Storm Security — exploits e advisories
- Full Disclosure — mailing list de segurança
- oss-security — discussão de vulnerabilidades em open-source

**Monitoramento automatizado:**
- GitHub Dependabot — monitora dependências do projeto
- Renovate — renova dependências automaticamente
- OSV.dev — base de vulnerabilidades para open-source
- Grype — scanning de containers

**Práticas recomendadas:**
- Assinar alertas de CVEs para as dependências do projeto
- Revisar semanalmente o NVD para CVEs em bibliotecas usadas
- Mantenir um SBOM (Software Bill of Materials) atualizado
- Estabelecer SLA para correção de CVEs críticos (24-48h) e altos (1-2 semanas)

### 7.2 Repositório Companion

O repositório companion deste livro está disponível em:

```
https://github.com/autor/secure-cpp-book
```

O repositório contém:
- Todos os exemplos de código compiláveis
- Soluções para exercícios propostos
- Configurações de ferramentas (.clang-tidy, CMakeLists.txt, CMakePresets.json)
- Scripts de automação para análise de segurança
- Fuzz targets para cada capítulo
- Cenarios de teste para vulnerabilidades descritas

Para clonar e usar:

```bash
git clone https://github.com/autor/secure-cpp-book.git
cd secure-cpp-book

# Configurar ambiente
cmake --preset sanitizers
cmake --build --preset sanitizers

# Executar testes
ctest --preset sanitizers
```

### 7.3 Comunidades e leitura complementar

**Conferências:**
- DEF CON — maior conferência de segurança do mundo
- Black Hat — conferência profissional de segurança
- Chaos Communication Congress (CCC) — segurança e privacidade
- PurpleCon — conferência de segurança brasileira
- DEF CON Brasil — comunidade brasileira

**Livros complementares:**
- "Secure Coding in C and C++" — Robert Seacord (SEI/CERT)
- "The Art of Software Security Assessment" — Andy Zou, Nick Fallone, John McDonald
- "Hacking: The Art of Exploitation" — Jon Erickson
- "Practical Binary Analysis" — Dennis Andriesse
- "The Web Application Hacker's Handbook" — Dafydd Stuttard, Marcus Pinto

**Websites e blogs:**
- CERT/CC Vulnerability Notes (kb.cert.org)
- OWASP (owasp.org)
- CISA (cisa.gov)
- Linux Kernel Security Documentation
- OpenSSL Security Advisories

**Padrões e frameworks:**
- CWE/SANS Top 25 Most Dangerous Software Weaknesses
- OWASP Top 10
- BSI IT-Grundschutz
- NIST Cybersecurity Framework
- CIS Controls

### 7.4 Contribuindo para o livro

Este livro é um projeto em evolução. Contribuições são bem-vindas:

- **Bug reports**: vulnerabilidades no código de exemplo
- **Sugestões**: novos padrões de segurança ou CVEs relevantes
- **Revisão**: erros técnicos ou de tradução
- **Novos exemplos**: implementações alternativas ou atualizações para C++20/23

---

## Nota Final

Segurança de software é uma jornada, não um destino. Nenhum livro, nenhuma ferramenta e nenhum processo garante segurança absoluta. O que podemos fazer é reduzir sistematicamente a superfície de ataque, detectar vulnerabilidades antes que sejam exploradas e responder rapidamente quando forem descobertas.

Este livro é um guia prático nessa jornão. Ele não substitui o pensamento crítico, o julgamento profissional ou a experiência acumulada. Ele fornece fundamentos, padrões e ferramentas que você pode aplicar imediatamente em seu trabalho diário.

O melhor momento para começar a pensar em segurança foi quando o projeto começou. O segundo melhor momento é agora.

---

## Glossário de Siglas

| Sigla | Significado |
|-------|-------------|
| ASan | AddressSanitizer |
| AFL | American Fuzzy Lop (fuzzer) |
| CFI | Control Flow Guard / Control Flow Integrity |
| CWE | Common Weakness Enumeration |
| CVE | Common Vulnerabilities and Exposures |
| DEP | Data Execution Prevention |
| DMA | Direct Memory Access |
| DAST | Dynamic Application Security Testing |
| GDPR | General Data Protection Regulation |
| JNDI | Java Naming and Directory Interface |
| LGPD | Lei Geral de Proteção de Dados |
| NX | No-Execute bit |
| OWASP | Open Worldwide Application Security Project |
| RAII | Resource Acquisition Is Initialization |
| RCE | Remote Code Execution |
| SAST | Static Application Security Testing |
| SBOM | Software Bill of Materials |
| SCM | Supply Chain Management |
| SMB | Server Message Block |
| SPDK | Storage Performance Development Kit |
| STRIDE | Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege |
| TSan | ThreadSanitizer |
| UBSan | UndefinedBehaviorSanitizer |
