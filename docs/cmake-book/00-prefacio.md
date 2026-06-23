---
layout: default
title: "00-prefacio"
---

# Prefacio — CMake Seguro e Build Systems

> *"O build system e a primeira linha de defesa do seu software."*

---

## Por Que Este Livro Existe

A maioria dos engenheiros investe horas em code review, testes e hardening de runtime — mas ignora completamente o build system. E la esta o problema: um build system mal configurado pode:

- Compilar com sanitizers desabilitados, escondendo bugs de memoria
- Gerar binarios sem ASLR/DEP, facilitando exploits
- Usar compiladores antigos com vulnerabilidades conhecidas
- Incluir dependencias com CVEs sem detector
- Produzir binarios nao-reproduziveis, impossibilitando verificacao
- Executar scripts de build que executam codigo arbitrario
- Expor variaveis de ambiente sensiveis em logs de build
- Compilar com flags que desabilitam protecoes de seguranca
- Usar pacotes de terceiros sem verificacao de integridade
- Configurar RPATHs que permitem library injection

### O Cenario Atual

| Metrica | Valor | Fonte |
|---------|-------|-------|
| Projetos usando CMake | 2.5M+ | Kitware |
| CVEs em build systems (2020-2024) | 45+ | NVD |
| Projetos com builds nao-reproduziveis | 70%+ | Reproducible-builds.org |
| Custo medio de compromise via supply chain | US$ 4.6M | IBM 2024 |
| Ataques supply chain em 2024 | 300% aumento | Sonatype |

### O Ciclo de Inseguranca no Build

```
Desenvolvedor copia CMakeLists.txt template
    -> Flags de seguranca desabilitadas
        -> Dependencias sem hash verification
            -> Binarios sem hardening em producao
                -> Atacante explora build system ou binario
                    -> Comprometimento do software distribuido
```

### Por Que CMake Importa

CMake nao e apenas um gerador de Makefiles. Ele e o ponto de controle central para:

- **Flags de compilacao**: Determinam protecoes do binario final
- **Gerenciamento de dependencias**: Controla o que entra no projeto
- **Configuracao de toolchain**: Define como o codigo e compilado
- **Integracao com CI/CD**: Automatiza testes, analise e deploy
- **Packaging**: Determina como o software e distribuido

Cada uma dessas areas tem implicacoes de seguranca diretas. Este livro cobre todas elas.

---

## Publico-Alvo

### Engenheiros C/C++

Voce desenvolve software em C/C++ e precisa entender como configurar CMake para produzir binarios seguros, testados e auditaveis.

| Habilidade Atual | O Que Voce Vai Aprender |
|------------------|------------------------|
| Compila basico | Flags de seguranca: stack protector, FORTIFY, ASLR, RELRO |
| Usa makefiles | CMake moderno: targets, properties, generator expressions |
| Testa manualmente | Sanitizers: ASan, TSan, UBSan, MSan em CI/CD |
| Copia templates | Hardening: protecoes de binario, strip, RPATH |
| Dependencias ad-hoc | Supply chain: SBOM, Sigstore, vcpkg/Conan seguro |

### DevOps e Platform Engineers

Voce configura pipelines de build e precisa garantir que artifacts produzidos sao seguros e verificaveis.

| Responsabilidade | O Que Voce Vai Aprender |
|------------------|------------------------|
| Pipeline CI/CD | Security gates, SBOM generation, code signing |
| Artifact management | Hash verification, reproducible builds |
| Secret management | OIDC, vault integration para builds |
| Multi-platform builds | Cross-compilation segura |

### Security Engineers

Voce audita build systems e precisa de um framework para avaliar configuracoes CMake.

| Auditoria | O Que Voce Vai Aprender |
|-----------|------------------------|
| Flags check | Verificar flags de seguranca em CMakeLists.txt |
| Dependency audit | vcpkg/Conan audit, SBOM analysis |
| Build reproducibility | Diffoscope, hash verification |
| Supply chain | Sigstore, SLSA levels |

### Tech Leads

Voce define padroes de build para equipes e precisa de templates, checklists e decision trees.

| Decisao | Ferramentas Fornecidas |
|---------|----------------------|
| Qual gerador? | Decision tree: Make vs Ninja vs Visual Studio |
| Qual package manager? | vcpkg vs Conan vs submodules |
| Qual workflow? | Templates completos de CMakeLists.txt |
| Qual padrao? | Checklists de seguranca por area |

---

## Pre-Requisitos

### Tecnico

| Tecnologia | Nivel Minimo | O Que Voce Deve Saber |
|------------|-------------|----------------------|
| C++ | Intermediario | Templates, RAII, smart pointers |
| CMake | Basico | CMakeLists.txt, target_link_libraries |
| Make/Ninja | Basico | Como geram binarios |
| GCC/Clang | Basico | Flags de compilacao |
| Git | Basico | Versionamento, submodules |

### Seguranca (Desejavel)

| Conceito | Nivel | Onde Aprender Neste Livro |
|----------|-------|--------------------------|
| Buffer overflow | Basico | Cap. 04, 06 |
| Stack smashing | Basico | Cap. 04, 06 |
| Supply chain attack | Basico | Cap. 10, 12 |
| Reproducible builds | Nenhum | Cap. 08 |

### Ferramentas Necessarias

| Ferramenta | Versao | Para Que |
|------------|--------|----------|
| CMake | 3.20+ | Build system |
| GCC ou Clang | 12+ / 16+ | Compilador |
| Git | 2.30+ | Versionamento |
| Ninja (opcional) | 1.10+ | Build rapido |
| Docker (recomendado) | 20.10+ | Isolamento |

---

## Estrutura do Livro

### Parte I: Fundamentos do CMake (Capitulos 00-03)

| Capitulo | Titulo | Foco | Linhas |
|----------|--------|------|--------|
| 00 | Prefacio | Contexto, motivacao, como usar | Este |
| 01 | Introducao ao CMake Moderno | CMake 3.20+, targets, generators | 3000+ |
| 02 | Target Model e Properties | Propriedades, interface libraries | 3300+ |
| 03 | Expressoes e Funcoes | Generator expressions, funcoes customizadas | 2900+ |

### Parte II: Seguranca no Build (Capitulos 04-08)

| Capitulo | Titulo | Foco | Linhas |
|----------|--------|------|--------|
| 04 | Flags de Seguranca do Compilador | Stack protector, FORTIFY, PIE, RELRO | 2300+ |
| 05 | Sanitizers e Debug Builds | ASan, TSan, UBSan, MSan | 3000+ |
| 06 | Hardening de Binarios | RELRO, ASLR, strip, code signing | 2800+ |
| 07 | Analise Estatica com CMake | clang-tidy, cppcheck, Infer | 3400+ |
| 08 | Builds Reproduziveis | Determinismo, SOURCE_DATE_EPOCH | 2800+ |

### Parte III: Dependencias e Supply Chain (Capitulos 09-12)

| Capitulo | Titulo | Foco | Linhas |
|----------|--------|------|--------|
| 09 | Finding Packages Seguro | find_package, security risks | 2800+ |
| 10 | FetchContent e ExternalProject | Download seguro, hash verification | 2900+ |
| 11 | vcpkg e Conan | Package managers, lock files | 3300+ |
| 12 | SBOM e Supply Chain | SPDX, CycloneDX, Sigstore, SLSA | 4000+ |

### Parte IV: CI/CD e Operacao (Capitulos 13-17)

| Capitulo | Titulo | Foco | Linhas |
|----------|--------|------|--------|
| 13 | Cross-Compilation | Toolchains, seguranca cross-build | 3000+ |
| 14 | Testing no CMake | CTest, GoogleTest, fuzzing | 3700+ |
| 15 | Install e Packaging | CPack, DESTDIR, secure install | 2800+ |
| 16 | CI/CD Seguro com CMake | GitHub Actions, GitLab CI | 2800+ |
| 17 | Boas Praticas e Checklist | Anti-patterns, decision trees | 2800+ |

---

## Como Usar Este Livro

### Leitura Sequencial
Para quem e novo em CMake seguro, recomenda a leitura dos capitulos 01-08 antes de avancar para topicos especializados.

### Leitura por Perfil

**Engenheiro implementando build seguro:**
```
01 -> 02 -> 04 -> 05 -> 06 -> 07 -> 14 -> 16
```
Rationale: Targets (02) sao fundamentais. Seguranca (04-06) antes de tooling (07). Testing (14) e CI/CD (16) fecham o ciclo.

**DevOps configurando pipeline:**
```
01 -> 04 -> 06 -> 08 -> 13 -> 15 -> 16
```
Rationale: Flags (04) e hardening (06) definem o binario. Reproducibility (08) garante verificabilidade. Cross-compilation (13) e packaging (15) preparam distribuicao. CI/CD (16) automa tudo.

**Security auditor:**
```
04 -> 05 -> 06 -> 07 -> 08 -> 09 -> 10 -> 12 -> 17
```
Rationale: Comeca pelas protecoes (04-06), depois verifica com analise (07-08), audita dependencias (09-12), e fecha com checklist (17).

**Tech Lead definindo padroes:**
```
01 -> 02 -> 04 -> 06 -> 08 -> 09 -> 11 -> 12 -> 17
```
Rationale: Fundamentos (01-02) primeiro. Padroes de seguranca (04, 06) e reproducibility (08). Dependencias (09, 11) e supply chain (12). Checklist (17) para documentar decisoes.

### Leitura por Nivel de Experiencia

**CMake basico:**
Comece pelo capitulo 01 para entender o target model moderno. Depois avance para 04 (flags) e 06 (hardening) — estes dois capitulos ja melhoram significativamente a seguranca do seu build.

**CMake intermediario, seguranca nova:**
Pule para 04-08. Estes cobrem tudo que voce precisa para adicionar seguranca ao seu CMake existente.

**Experiente em ambos:**
Use o indice por CVEs e decision trees para focar nos topicos mais relevantes para seu projeto.

---

## Convencoes do Livro

### Texto
- **Idioma**: Portugues brasileiro (PT-BR)
- **Termos tecnicos**: Mantidos em ingles quando nao tem traduicao estabelecida (ex: target, generator, property)

### Codigo
- **Identificadores**: Ingles
- **Exemplos**: CMake 3.20+, C++17/20
- **Compiladores**: GCC 12+, Clang 16+, MSVC 2022+
- **Formato**: Cada exemplo e compilavel e executavel

### Estrutura de Cada Capitulo
1. **Objetivos de Aprendizado** (3-5 itens)
2. **Secoes tecnicas** com codigo
3. **Tabelas comparativas** quando aplicavel
4. **CVEs documentados** (quando relevante)
5. **Exercicios** (5+)
6. **Referencias** para estudo adicional

### Sinalizacao de Seguranca

| Sinal | Significado |
|-------|-------------|
| `[SEGURO]` | Pratica recomendada |
| `[PERIGOSO]` | Anti-pattern a evitar |
| `[CVE-XXXX-XXXX]` | Vulnerabilidade documentada |
| `[CHECKLIST]` | Item de verificacao |

---

## Casos Reais Documentados

| CVE | Titulo | Impacto | Capitulos |
|-----|--------|---------|-----------|
| CVE-2024-3094 | XZ Utils backdoor | Supply chain via build system | 10, 12 |
| CVE-2023-44487 | HTTP/2 Rapid Reset | Builds com dependencias de rede | 09 |
| CVE-2021-44228 | Log4Shell | Dependency management | 09, 12 |
| CVE-2020-1472 | Zerologon | Build authentication | 16 |
| CVE-2019-11091 | MDS (Microarchitectural) | Compilador e hardening | 04, 06 |
| CVE-2018-3639 | Spectre Variant 4 | Compiler mitigations | 04 |

---

## Ferramentas Referenciadas

| Ferramenta | Uso | Capitulos |
|------------|-----|-----------|
| CMake | Build system | Todos |
| GCC/Clang | Compiladores | 04, 05, 06 |
| clang-tidy | Analise estatica | 07 |
| cppcheck | Analise estatica | 07 |
| Facebook Infer | Analise profunda | 07 |
| Google Sanitizers | Runtime analysis | 05 |
| Valgrind | Memory analysis | 05 |
| vcpkg | Package manager | 11 |
| Conan | Package manager | 11 |
| syft | SBOM generation | 12 |
| cosign | Artifact signing | 12 |
| CTest | Test runner | 14 |
| CPack | Packaging | 15 |
| GitHub Actions | CI/CD | 16 |
| GitLab CI | CI/CD | 16 |
| Diffoscope | Build comparison | 08 |

---

## Agradecimentos

Aos mantenedores do CMake (Kitware) por criar e manter a ferramenta que torna possivel builds seguros em escala. Aos pesquisadores de seguranca que documentam CVEs em build systems, permitindo que outros aprendam. A comunidade de Reproducible Builds que luta por determinismo em software. Aos engenheiros que mantêm vcpkg, Conan e outras ferramentas que tornam a gestao de dependencias mais segura.

---

## Nota sobre Seguranca

Este livro documenta vulnerabilidades e tecnicas de ataque contra build systems. Todo o codigo ofensivo e apresentado em contexto educacional, com o objetivo de demonstrar por que certas praticas sao perigosas e como evita-las.

O codigo defensivo e sempre apresentado ao lado do ofensivo. O leitor deve implementar apenas as versoes defensivas em sistemas de producao.

---

## Exemplo Rapido: CMakeLists.txt Seguro vs Inseguro

### Versao Insegura (COMUM)

```cmake
# PERIGOSO: flags de seguranca desabilitadas
cmake_minimum_required(VERSION 3.0)
project(minha_app)

# Sem sanitizer, sem warnings, sem hardening
add_executable(app main.cpp)
```

**Problemas:**
- CMake 3.0 e obsoleto, sem suporte a modern policies
- Sem -Wall -Wextra -Werror
- Sem -fstack-protector-strong
- Sem -D_FORTIFY_SOURCE=2
- Sem sanitizer options
- Sem reproducibility settings

### Versao Segura (RECOMENDADA)

```cmake
# SEGURO: todas as protecoes habilitadas
cmake_minimum_required(VERSION 3.20)
project(minha_app LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Security flags
add_compile_options(
    -Wall -Wextra -Werror -Wpedantic
    -fstack-protector-strong
    -D_FORTIFY_SOURCE=2
    -fPIE
)

add_link_options(
    -Wl,-z,relro,-z,now
    -pie
)

# Sanitizer option
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
if(ENABLE_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()

add_executable(app main.cpp)

# Tests
enable_testing()
add_test(NAME unit_tests COMMAND app)
```

**Beneficios:**
- CMake 3.20 com policies modernas
- Warnings como erros
- Stack protector habilitado
- Buffer overflow detection
- Position independent executable
- Full RELRO
- Sanitizer configuravel
- Tests integrados

---

## Glossario

| Termo | Definicao |
|-------|-----------|
| **Target** | Unidade basica do CMake: executavel, library, interface |
| **Property** | Atributo de um target (compile options, include dirs, etc.) |
| **Generator** | Ferramenta que gera o build system real (Make, Ninja, VS) |
| **Toolchain** | Conjunto de compiladores e ferramentas para cross-compilation |
| **Sanitizer** | Instrumentacao de runtime para detectar bugs (ASan, TSan, etc.) |
| **SBOM** | Software Bill of Materials — lista de todas as dependencias |
| **REPRODUCIBLE** | Build que produz o mesmo binario dado o mesmo source |
| **HARDENING** | Técnicas para tornar binarios mais resistentes a ataques |
| **FORTIFY_SOURCE** | Macro que adiciona checks de buffer overflow em runtime |
| **RELRO** | Relocation Read-Only — protecao contra GOT overwrite |
| **PIE** | Position Independent Executable — necessario para ASLR |
| **RPATH** | Caminho para shared libraries — configuracao de seguranca |
| **FetchContent** | Mecanismo CMake para baixar e integrar dependencias |
| **FetchContent_Declare** | Declaracao de uma dependencia para FetchContent |
| **IMPORTED** | Target que representa uma library externa ja instalada |
| **INTERFACE** | Library header-only que so exporta includes/defines |
| **Alias** | Nome alternativo para um target (target_alias) |
| **CMakePresets** | Arquivo JSON com configuracoes de build pre-definidas |
| **DESTDIR** | Prefixo de instalacao para staging (usado em packaging) |

---

## Mapa Mental do Livro

```
CMake Seguro
|
+-- Fundamentos (01-03)
|   |-- Target model: como o CMake organiza o build
|   |-- Properties: como configurar cada target
|   +-- Expressoes: logica e funcoes customizadas
|
+-- Seguranca no Build (04-08)
|   |-- Flags: protecoes do compilador
|   |-- Sanitizers: deteccao de bugs em runtime
|   |-- Hardening: protecoes do binario final
|   |-- Analise estatica: verificacao antes de compilar
|   +-- Reproducibilidade: builds deterministicos
|
+-- Dependencias (09-12)
|   |-- Finding: localizar libraries seguramente
|   |-- FetchContent: baixar e integrar dependencias
|   |-- Package managers: vcpkg e Conan
|   +-- Supply chain: SBOM, signing, SLSA
|
+-- Operacao (13-17)
    |-- Cross-compilation: builds multi-plataforma
    |-- Testing: CTest, GoogleTest, fuzzing
    |-- Install: CPack, packaging seguro
    |-- CI/CD: automacao com seguranca
    +-- Checklist: boas praticas consolidadas
```

---

## Diferencial deste Livro

### Nao e um tutorial de CMake
Existem muitos tutoriais de CMake. Este livro e diferente: cada decision e avaliada pela perspectiva de seguranca.

### Cada flag e explicada
Nao basta dizer "use -fstack-protector-strong". Este livro explica:
- O que a flag faz internamente
- Por que ela e necessaria
- Quando NAO usa-la
- Como verificar se esta ativa

### Casos reais
Cada vulnerabilidade documentada inclui:
- O que aconteceu
- Por que aconteceu
- Como teria sido prevenida com CMake seguro
- Codigo corrigido

### Templates prontos
Os capitulos 16-17 fornecem templates completos de:
- CMakeLists.txt para projetos novos
- Toolchain files para cross-compilation
- CMakePresets.json para configuracoes padrao
- GitHub Actions pipeline completa
- GitLab CI pipeline completa

### Referencia completa
O livro pode ser usado como referencia rapida:
- Tabelas comparativas de flags por compilador
- Matrix de sanitizers vs deteccao
- Checklist de hardening por plataforma
- Decision trees para decisoes de build

---

## Por Que Seguranca Comeca no Build

### O Ataque Comeca Antes do Runtime

Muitos engenheiros pensam que seguranca e um problema de runtime — validacao de input, autenticacao, criptografia. Mas o ataque comeca muito antes:

1. **Compilador**: Se compilado sem -fstack-protector, buffer overflows sao exploitable
2. **Dependencias**: Se uma dependencia tem CVE e nao e detectada, o binario ja nasce vulneravel
3. **Build reproducibility**: Se o binario nao e reproduzivel, nao e possivel verificar integridade
4. **Supply chain**: Se o build system e comprometido (como XZ Utils), todo o software e comprometido

### O Modelo de Ameaca do Build System

| Vetor de Ataque | Exemplo | Mitigacao no CMake |
|----------------|---------|-------------------|
| Compilador comprometido | Compilador backdoored | Reproducible builds, verificacao |
| Dependencia maliciosa | XZ Utils CVE-2024-3094 | Hash verification, SBOM |
| Build flags inadequadas | Sem stack protector | Flags padrao seguras |
| Binario sem hardening | Sem RELRO, sem ASLR | Hardening checklist |
| Pipeline CI/CD | Secret em log | Secret management |
| Cross-compilation | Toolchain confiavel | Toolchain verification |

### O Retorno do Investimento

| Acao | Esforco | Impacto |
|------|---------|---------|
| Adicionar flags de seguranca | 5 minutos | Previne exploit de buffer overflow |
| Habilitar sanitizers | 10 minutos | Detecta memory bugs antes de producao |
| Configurar reproducible builds | 1 hora | Permite verificacao de integridade |
| Implementar SBOM | 2 horas | Detecta dependencias vulneraveis |
| CI/CD com security gates | 4 horas | Automatiza verificacao continua |

O tempo total de investimento e menor que o tempo medio para resolver um incidente de seguranca (194 dias, segundo IBM).

---

## Como Este Livro se Diferencia

### Nao e um tutorial de CMake
Existem muitos tutoriais de CMake. Este livro e diferente: cada decision e avaliada pela perspectiva de seguranca.

### Cada flag e explicada
Nao basta dizer "use -fstack-protector-strong". Este livro explica:
- O que a flag faz internamente
- Por que ela e necessaria
- Quando NAO usa-la
- Como verificar se esta ativa

### Casos reais
Cada vulnerabilidade documentada inclui:
- O que aconteceu
- Por que aconteceu
- Como teria sido prevenida com CMake seguro
- Codigo corrigido

### Templates prontos
Os capitulos 16-17 fornecem templates completos de:
- CMakeLists.txt para projetos novos
- Toolchain files para cross-compilation
- CMakePresets.json para configuracoes padrao
- GitHub Actions pipeline completa
- GitLab CI pipeline completa

### Referencia completa
O livro pode ser usado como referencia rapida:
- Tabelas comparativas de flags por compilador
- Matrix de sanitizers vs deteccao
- Checklist de hardening por plataforma
- Decision trees para decisoes de build

### Multi-plataforma
Todos os exemplos funcionam em:
- Linux (GCC, Clang)
- macOS (Apple Clang)
- Windows (MSVC, MinGW)
- Cross-compilation (ARM, RISC-V, WebAssembly)

### Integracao com ecossistema DevSecurity
Este livro complementa os outros 6 livros da colecao DevSecurity:
- Livro 1 (SDD): Securanca desde o design
- Livro 2 (DevSecOps): Pipelines seguras
- Livro 3 (Malware): Analise de binarios
- Livro 4 (Concorrencia): Bugs de threading
- Livro 5 (Criptografia): Implementacoes seguras
- Livro 6 (Web): Seguranca de aplicacoes web

---

## Committment do Autor

### O Que Voce Vai Conseguir Apos Ler Este Livro

1. **Configurar CMake para produzir binarios seguros** com todas as flags de protecao habilitadas
2. **Detectar bugs de memoria** antes de producao usando sanitizers
3. **Implementar builds reproduziveis** que podem ser verificadas por terceiros
4. **Gerenciar dependencias com seguranca** usando hash verification e SBOM
5. **Configurar CI/CD com security gates** que impedem binarios vulneraveis de serem distribuidos
6. **Auditar build systems** existentes usando o checklist deste livro
7. **Cross-compile de forma segura** para multiplas plataformas
8. **Packaging seguro** com code signing e verificacao de integridade

### O Que Nao E Garantido

- Seguranca absoluta — seguranca e um processo, nao um produto
- Compatibilidade com todas as versoes de CMake — focamos em 3.20+
- Cobertura de todas as possiveis configuracoes — focamos nas mais comuns
- Substituicao de auditoria profissional — este livro e uma ferramenta, nao um substituto

---

## Nota sobre Seguranca

Este livro documenta vulnerabilidades e tecnicas de ataque contra build systems. Todo o codigo ofensivo e apresentado em contexto educacional, com o objetivo de demonstrar por que certas praticas sao perigosas e como evita-las.

O codigo defensivo e sempre apresentado ao lado do ofensivo. O leitor deve implementar apenas as versoes defensivas em sistemas de producao.

Nenhum exploit ou tecnica de ataque apresentada neste livro deve ser utilizado contra sistemas sem autorizacao explicita do proprietario.

---

## Estatisticas do Livro

| Metrica | Valor |
|---------|-------|
| Total de capitulos | 18 |
| Total de linhas estimadas | ~52.500 |
| CVEs documentados | 6+ |
| Exemplos de codigo CMake | 100+ |
| Exercicios | 100+ |
| Tabelas comparativas | 50+ |
| Templates prontos | 10+ |
| Ferramentas referenciadas | 16 |
| Plataformas cobertas | Linux, macOS, Windows, ARM, RISC-V |

---

## Recursos Adicionais

| Recurso | URL | Descricao |
|---------|-----|-----------|
| CMake Documentation | cmake.org/cmake/help | Documentacao oficial |
| CMake Cookbook | cmake.org/cmake/help/latest | Exemplos praticos |
| Reproducible Builds | reproducible-builds.org | Padroes de determinismo |
| OWASP Build Security | owasp.org | Guia de seguranca |
| LLVM Hardening | llvm.org/docs/Hardening.html | Guia de hardening |
| GCC Security | gcc.gnu.org/onlinedocs/gcc/ | Flags de seguranca GCC |
| Clang Sanitizers | clang.llvm.org/docs/ | Documentacao de sanitizers |
| vcpkg | github.com/microsoft/vcpkg | Package manager C++ |
| Conan | conan.io | Package manager C++ |
| syft | github.com/anchore/syft | SBOM generation |
| cosign | github.com/sigstore/cosign | Artifact signing |
| Diffoscope | diffoscope.org | Build comparison |
| Nix | nixos.org | Reproducible builds |
| Guix | gnu.org/software/guix | Reproducible builds |

---

## Glossario Completo

| Termo | Definicao | Capitulo |
|-------|-----------|----------|
| **Target** | Unidade basica do CMake: executavel, library, interface | 01, 02 |
| **Property** | Atributo de um target (compile options, include dirs, etc.) | 02 |
| **Generator** | Ferramenta que gera o build system real (Make, Ninja, VS) | 01 |
| **Toolchain** | Conjunto de compiladores e ferramentas para cross-compilation | 13 |
| **Sanitizer** | Instrumentacao de runtime para detectar bugs | 05 |
| **SBOM** | Software Bill of Materials — lista de todas as dependencias | 12 |
| **REPRODUCIBLE** | Build que produz o mesmo binario dado o mesmo source | 08 |
| **HARDENING** | Tecnicas para tornar binarios mais resistentes a ataques | 06 |
| **FORTIFY_SOURCE** | Macro que adiciona checks de buffer overflow | 04 |
| **RELRO** | Relocation Read-Only — protecao contra GOT overwrite | 04, 06 |
| **PIE** | Position Independent Executable — necessario para ASLR | 04 |
| **RPATH** | Caminho para shared libraries — configuracao de seguranca | 15 |
| **FetchContent** | Mecanismo CMake para baixar e integrar dependencias | 10 |
| **IMPORTED** | Target que representa uma library externa ja instalada | 02 |
| **INTERFACE** | Library header-only que so exporta includes/defines | 02 |
| **Alias** | Nome alternativo para um target | 02 |
| **CMakePresets** | Arquivo JSON com configuracoes de build pre-definidas | 01 |
| **DESTDIR** | Prefixo de instalacao para staging | 15 |
| **Source date epoch** | Timestamp para builds reproduziveis | 08 |
| **Toolchain file** | Arquivo .cmake que define compiladores e flags | 13 |
| **Binary caching** | Cache de binarios compilados para builds incrementais | 11 |
| **Lock file** | Arquivo que trava versoes exatas de dependencias | 11 |
| **Triplet** | Identificador de plataforma (x64-linux, arm64-osx, etc.) | 13 |
| **SLSA** | Supply chain Levels for Software Artifacts | 12 |
| **Cosign** | Ferramenta de signing de artifacts da Sigstore | 12 |
| **Diffoscope** | Ferramenta para comparar dois binarios | 08 |
| **cpack** | Gerador de pacotes do CMake | 15 |
| **ctest** | Test runner do CMake | 14 |
| **Compile feature** | Requisito de linguagem (cxx_std_17, etc.) | 02 |
| **Generator expression** | Expressao avaliada durante a geracao do build | 03 |

---

## Mapa de Decisoes

```
Qual problema voce quer resolver?
|
+-- Binario vulneravel a exploits
|   +-- Cap. 04 (flags) + Cap. 06 (hardening)
|
+-- Bugs de memoria nao detectados
|   +-- Cap. 05 (sanitizers)
|
+-- Codigo com padroes inseguros
|   +-- Cap. 07 (analise estatica)
|
+-- Binario nao verificavel
|   +-- Cap. 08 (reproducible builds)
|
+-- Dependencias com CVEs
|   +-- Cap. 09 (finding) + Cap. 10 (fetch) + Cap. 12 (SBOM)
|
+-- Package management inseguro
|   +-- Cap. 11 (vcpkg/conan)
|
+-- Build multi-plataforma
|   +-- Cap. 13 (cross-compilation)
|
+-- Testes nao automatizados
|   +-- Cap. 14 (testing)
|
+-- Distribuicao manual
|   +-- Cap. 15 (install/packaging)
|
+-- Pipeline CI/CD insegura
|   +-- Cap. 16 (CI/CD)
|
+-- Nao sei por onde comecar
    +-- Cap. 17 (checklist)
```

---

## Perguntas Frequentes

**Preciso ser expert em C++ para ler este livro?**
Nao. O foco e CMake e build systems. Conhecimento basico de C++ e suficiente. O livro explica cada flag e configuracao com contexto.

**Posso usar este livro com projetos legados?**
Sim. O capitulo 17 tem um guia de migracao de CMake antigo para moderno. A maioria das configuracoes de seguranca pode ser adicionada incrementalmente.

**Este livro cobre apenas Linux?**
Nao. Todos os exemplos funcionam em Linux, macOS e Windows (MSVC). Cross-compilation e coberto no capitulo 13.

**Preciso de CMake 3.20+?**
Recomendado, mas nao obrigatorio. Algumas features (CMakePresets, compile features) requerem 3.20+. Flags de seguranca funcionam em versoes anteriores.

**Como verifico se meu build atual e seguro?**
Use o checklist do capitulo 17. Ele cobre todas as areas: flags, sanitizers, hardening, dependencias, CI/CD.

**Este livro substitui um auditor de seguranca?**
Nao. Este livro e uma ferramenta de aprendizado e referencia. Auditorias profissionais devem ser feitas por especialistas.

**Quanto tempo leva para implementar as recomendacoes?**
- 30 minutos: flags basicas de seguranca
- 2 horas: sanitizers + hardening
- 1 dia: CI/CD com security gates
- 1 semana: supply chain completo (SBOM, Sigstore)

---

## Historia dos Build Systems

### Evolucao dos Build Systems

| Epoca | Ferramenta | Limitacao |
|-------|-----------|-----------|
| 1976 | Make | Manual, nao portavel |
| 1996 | CMake | Complexo, muitas APIs |
| 2000 | Autotools | Fragil, difcil de debugar |
| 2007 | SCons | Lento, niche |
| 2010 | Meson | Rapido, mas menos maduro |
| 2012 | Ninja | Apenas gerador, precisa de front-end |
| 2020 | CMake 3.20+ | Moderno, presets, prescan |

### Por Que CMake Venceu

CMake venceu porque:
- **Portabilidade**: Gera Make, Ninja, VS, Xcode, em qualquer plataforma
- **Escalabilidade**: Projetos como LLVM (30M+ linhas) usam CMake
- **Ecossistema**: Qt, OpenCV, TensorFlow, Blender — todos CMake
- **Comunidade**: Mais de 2.5M de projetos no GitHub usam CMake
- **Evolution**: CMake 3.20+ resolveu muitos problemas historicos

### A Oportunidade de Seguranca

A maioria dos tutoriais de CMake foca em:
- Como compilar mais rapido
- Como organizar projetos grandes
- Como integrar com IDEs

Poucos tutoriais focam em:
- **Como compilar com seguranca**
- **Como gerenciar dependencias de forma segura**
- **Como produzir binarios verificaveis**
- **Como auditar o build system**

Este livro preenche essa lacuna. Com examples praticos, CVEs documentados, e templates prontos, voce vai conseguir transformar seu CMakeLists.txt de uma lista de comandos em uma configuracao segura, verificavel e reproduzivel.

---

*Bom estudo. A seguranca do build system e a fundacao da seguranca do software.*

*[Proximo capitulo: 01 — Introducao ao CMake Moderno](01-introducao-cmake-moderno.md)*
---


*[Próximo capítulo: 01 — Introducao Cmake Moderno](01-introducao-cmake-moderno.md)*
