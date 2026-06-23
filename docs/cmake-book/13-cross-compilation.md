---
layout: default
title: "13-cross-compilation"
---

# Capitulo 13: Cross-Compilation

> *"Cross-compilation nao e apenas trocar o compilador — e reconstruir toda a cadeia de confianca para outro alvo."*

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

- Entender o conceito de cross-compilation e seus cenarios de uso
- Criar toolchain files seguros para CMake
- Configurar sysroots, target triplets e compiladores cruzados
- Gerenciar find_package em ambientes de cross-compilation
- Integrar vcpkg com triplets para dependencias cruzadas
- Implementar verificacao de toolchain como parte do build seguro
- Construir para multiplos arquiteturas com CMake presets
- Executar um exemplo completo de ARM cross-compilation seguro

### 1.1 O que voce precisa saber antes

Antes de prosseguir, e fundamental que voce domine os seguintes topicos:

- CMake target model e properties (Capitulo 02)
- Expressoes e generator expressions (Capitulo 03)
- Flags de seguranca do compilador (Capitulo 04)
- Finding packages seguros (Capitulo 09)
- FetchContent e ExternalProject (Capitulo 10)
- vcpkg e Conan (Capitulo 11)

Cross-compilation amplifica significativamente a superficie de ataque do build system. Um erro na configuracao da toolchain pode resultar em binarios compilados sem hardening, com libraries incorretas ou ate mesmo comprometidos durante o processo de build.

---

## 2. Por Que Cross-Compile: Embedded, Mobile, IoT

### 2.1 Definicao de Cross-Compilation

Cross-compilation e o processo de compilar codigo em uma maquina (host) para ser executado em outra maquina com arquitetura ou sistema operacional diferente (target). A maquina onde o compilador roda e chamada de **host**, enquanto a maquina onde o binario sera executado e chamada de **target**.

Em uma compilacao nativa, host e target sao a mesma maquina. Em cross-compilation, eles sao distintos. Essa distincao tem implicacoes profundas para a seguranca do build:

```
Host (build machine):          Target (run machine):
  x86_64 Linux                  ARM Cortex-M4 bare-metal
  GCC compilador                Binario gerado
  Roda CMake                   Roda o firmware
  Gera Makefiles               Usa as bibliotecas do target
```

### 2.2 Cenarios de Cross-Compilation

#### 2.2.1 Embedded Systems

Sistemas embarcados representam o maior uso de cross-compilation. Microcontroladores ARM Cortex-M, RISC-V e MIPS nao possuem recursos suficientes para compilar codigo nativamente. O host roda ferramentas de desenvolvimento completas enquanto o target recebe binarios otimizados para hardware restrito.

```cmake
# Exemplo: firmware para STM32F4 (ARM Cortex-M4)
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
```

Em embedded, a verificacao da toolchain e critica. Um compilador incorreto pode gerar binarios que funcionam em simulacao mas falham em hardware real, ou pior, binarios com comportamento indefinido que so se manifestam em campos especificos.

#### 2.2.2 Mobile Development

Desenvolvimento mobile para Android e iOS requer cross-compilation obrigatoriamente. O Android NDK fornece toolchains para ARM, ARM64, x86 e x86_64, cada uma com implicacoes de seguranca diferentes:

```
Android NDK targets:
  armeabi-v7a   -> ARM 32-bit (legacy)
  arm64-v8a     -> ARM 64-bit (moderno)
  x86           -> x86 32-bit (emuladores)
  x86_64        -> x86 64-bit (emuladores)
```

Cada target pode exigir flags de hardening diferentes. ARM64 suporta PAC (Pointer Authentication) e BTI (Branch Target Identification) que nao estao disponiveis em 32-bit.

#### 2.2.3 IoT e Dispositivos Conectados

IoT amplia o escopo de cross-compilation para incluir sistemas que rodam Linux embutido, RTOS e firmwares proprietarios. A diversidade de arquiteturas (ARM, RISC-V, MIPS, Xtensa) e a necessidade de atualizacoes seguras (OTA) tornam a cross-compilation um componente critico da cadeia de seguranca.

```
IoT architecture targets:
  ARM Cortex-A    -> Linux embedded (Raspberry Pi, BeagleBone)
  ARM Cortex-M    -> RTOS (FreeRTOS, Zephyr)
  RISC-V          -> Emergente (ESP32-C3, SiFive)
  Xtensa          -> WiFi/BLE (ESP32 original)
```

### 2.3 Por Que a Seguranca Importa em Cross-Compilation

Cross-compilation introduz riscos unicos:

**Risco 1: Toolchain falsificada.** Se a toolchain for comprometida durante download ou instalacao, todos os binarios gerados podem conter backdoors. Isso e exatamente o que aconteceu no caso do XZ Utils (CVE-2024-3094), onde a supply chain foi atacada.

**Risco 2: Libraries incorretas.** Se o sysroot apontar para libraries erradas ou desatualizadas, o binario final pode conter vulnerabilidades conhecidas que foram corrigidas nas versoes corretas.

**Risco 3: Flags de seguranca ausentes.** Muitas toolchains de cross-compilation nao aplicam automaticamente flags de hardening. Sem ASLR, stack canaries ou FORTIFY_SOURCE, o binario fica significativamente mais facil de explorar.

**Risco 4: Build nao-reproduzivel.** Cross-compilation aumenta a complexidade de builds reproduziveis pois envolve mais componentes (toolchain, sysroot, libraries alvo) que podem variar entre ambientes.

### 2.4 Estudo de Caso: Ataque via Toolchain

O caso CVE-2024-3094 (XZ Utils backdoor) demonstra como atacantes podem comprometer uma toolchain para inserir backdoors em binarios compilados:

1. O maintainer do XZ Utils foi comprometido psicologicamente
2. Backdoor foi inserida no codigo-fonte
3. O build system (autotools) foi manipulado para incluir o malicious code
4. Binarios gerados continham funcionalidade de backdoor SSH

Em cross-compilation, o risco e amplificado pois as toolchains frequentemente sao baixadas de fontes externas e verificadas menos rigorosamente que dependencias de linguagem.

### 2.5 O Modelo Mental Correto

Para pensar sobre cross-compilation com seguranca, adote este modelo mental:

```
                    +---------------------+
                    |   Host Machine      |
                    |                     |
                    |   Build System      |
                    |   (CMake)           |
                    |        |            |
                    |   Toolchain         |
                    |   (Compiler +       |
                    |    Libraries)       |
                    |        |            |
                    |   +-----------+     |
                    |   | Sysroot   |     |
                    |   | (Target   |     |
                    |   |  libs)    |     |
                    |   +-----------+     |
                    +--------+------------+
                             |
                             | Build output
                             v
                    +---------------------+
                    |   Target Machine    |
                    |                     |
                    |   Run the binary    |
                    |   with target libs  |
                    +---------------------+
```

Cada componente neste diagrama e um ponto de confianca que deve ser verificado. A toolchain deve ser autenticada, o sysroot deve ser integro e as libraries devem estar na versao correta.

---

## 3. Toolchain Files: CMAKE_TOOLCHAIN_FILE

### 3.1 O Que e um Toolchain File

Um toolchain file e um arquivo CMake que define como compilar para um target diferente do host. Ele e especificado via variavel `CMAKE_TOOLCHAIN_FILE` e deve ser processado antes de qualquer outro comando CMake.

O toolchain file e o ponto de entrada mais importante para cross-compilation segura. Ele define:

- Compiladores (C, C++, ASM)
- Compilador de ligacao (linker)
- Arquitetura alvo
- Flags de compilacao obrigatorias
- Caminho para o sysroot
- Programas de utilidade (strip, objcopy, size)

### 3.2 Estrutura Basica de um Toolchain File

```cmake
# cmake/toolchains/arm-none-eabi-gcc.cmake
# Cross-compilation toolchain for ARM Cortex-M bare-metal

# O toolchain file e processado muito antes do projeto.
# Nao use aqui: project(), find_package(), ou qualquer
# comando que dependa de informacoes do projeto.

# 1. Sistema alvo
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# 2. Compiladores
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_AR arm-none-eabi-ar)
set(CMAKE_RANLIB arm-none-eabi-ranlib)
set(CMAKE_STRIP arm-none-eabi-strip)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_OBJDUMP arm-none-eabi-objdump)
set(CMAKE_SIZE arm-none-eabi-size)

# 3. Sysroot (se necessario)
# set(CMAKE_SYSROOT /path/to/arm-none-eabi/sysroot)

# 4. Ambiente de busca
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 3.3 Ordem de Processamento do Toolchain File

O CMake processa o toolchain file em uma ordem especifica e restrita. Entender essa ordem e essencial para evitar erros sutis:

1. `CMAKE_TOOLCHAIN_FILE` e lido antes do comando `project()`
2. As variaveis `CMAKE_SYSTEM_NAME` e `CMAKE_SYSTEM_PROCESSOR` sao avaliadas
3. Os compiladores sao configurados
4. O `project()` e executado, detectando o compilador
5. O restante do CMakeLists.txt e processado

**Regra critica:** Nao coloque comandos que dependam de `PROJECT_NAME`, `PROJECT_SOURCE_DIR`, ou qualquer variavel de projeto no toolchain file. Essas variaveis ainda nao existem quando o toolchain file e processado.

### 3.4 CMAKE_FIND_ROOT_PATH Modes

As variaveis `CMAKE_FIND_ROOT_PATH_MODE_*` controlam onde o CMake busca programas, libraries, headers e packages:

```cmake
# NEVER: buscar apenas no host (ignora sysroot)
# ONLY: buscar apenas no target (via sysroot)
# BOTH: buscar primeiro no target, depois no host

# Para cross-compilation segura:
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
# Programas (como testes) devem rodar no host

set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
# Libraries devem ser do target

set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
# Headers devem ser do target

set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
# Packages devem ser do target
```

Se `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY` estiver em `BOTH` ou `NEVER`, voce pode inadvertidamente linkar contra libraries do host, criando binarios que funcionam no build mas falham no target.

### 3.5 Toolchain File Seguro: Checklist

Antes de usar um toolchain file em producao, verifique:

```
[ ] Compiladores apontam para cross-compiler correto
[ ] CMAKE_SYSTEM_NAME esta definido corretamente
[ ] CMAKE_SYSTEM_PROCESSOR esta definido corretamente
[ ] CMAKE_FIND_ROOT_PATH_MODE_LIBRARY e ONLY
[ ] CMAKE_FIND_ROOT_PATH_MODE_INCLUDE e ONLY
[ ] CMAKE_FIND_ROOT_PATH_MODE_PACKAGE e ONLY
[ ] CMAKE_FIND_ROOT_PATH_MODE_PROGRAM e NEVER (ou ONLY se target roda no host)
[ ] Nao ha comandos project() ou find_package() no toolchain file
[ ] Nao ha hardcoded paths que funcionam apenas em uma maquina
[ ] O toolchain file e versionado no controle de versao
[ ] A toolchain e verificada via checksum ou assinatura
[ ] O toolchain e testada em um ambiente limpo antes de usar em producao
```

### 3.6 Multi-Configuration Toolchain Files

Para projetos que suportam multiplos targets, voce pode criar toolchain files separados ou usar um toolchain file parametrizavel:

```cmake
# cmake/toolchains/arm-cortex-m-generic.cmake
# Parametrizavel via variaveis de ambiente ou cache

# Processor selection
if(NOT DEFINED ARM_TARGET_MCU)
    set(ARM_TARGET_MCU "cortex-m4" CACHE STRING "ARM MCU target")
endif()

if(NOT DEFINED ARM_TARGET_FPU)
    set(ARM_TARGET_FPU "fpv4-sp-d16" CACHE STRING "FPU type")
endif()

# System
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Compiler
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)

# Architecture flags
set(CPU_FLAGS "-mcpu=${ARM_TARGET_MCU} -mthumb -mfloat-abi=hard -mfpu=${ARM_TARGET_FPU}")
set(CMAKE_C_FLAGS_INIT "${CPU_FLAGS}")
set(CMAKE_CXX_FLAGS_INIT "${CPU_FLAGS}")
set(CMAKE_ASM_FLAGS_INIT "${CPU_FLAGS}")

# Linker flags
set(CMAKE_EXE_LINKER_FLAGS_INIT "${CPU_FLAGS} -specs=nosys.specs -specs=nano.specs")

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 3.7 Variaveis Importantes no Toolchain File

```
Variavel                          Descricao
CMAKE_SYSTEM_NAME                 Nome do sistema alvo (Linux, Windows, Generic, etc.)
CMAKE_SYSTEM_PROCESSOR            Processador alvo (arm, aarch64, x86_64, etc.)
CMAKE_C_COMPILER                  Caminho para o compilador C
CMAKE_CXX_COMPILER                Caminho para o compilador C++
CMAKE_ASM_COMPILER                Caminho para o compilador Assembly
CMAKE_AR                          Caminho para o arquivador
CMAKE_RANLIB                      Caminho para o ranlib
CMAKE_STRIP                       Caminho para o strip
CMAKE_OBJCOPY                     Caminho para o objcopy
CMAKE_OBJDUMP                     Caminho para o objdump
CMAKE_LINKER                      Caminho para o linker
CMAKE_SYSROOT                     Caminho para o sysroot
CMAKE_STAGING_PREFIX              Prefixo para install (evita sobrescrever host)
CMAKE_C_FLAGS                     Flags adicionais para C
CMAKE_CXX_FLAGS                   Flags adicionais para C++
CMAKE_EXE_LINKER_FLAGS            Flags adicionais para linking
CMAKE_FIND_ROOT_PATH              Diretorio raiz para busca de libraries
CMAKE_FIND_ROOT_PATH_MODE_*       Modos de busca (LIBRARY, INCLUDE, PROGRAM, PACKAGE)
```

### 3.8 Erros Comuns em Toolchain Files

**Erro 1: Usar project() no toolchain file.**

```cmake
# ERRADO: project() no toolchain file
project(MyProject C CXX)  # ERRO! Variaveis do projeto nao existem ainda

# CORRETO: project() no CMakeLists.txt principal
```

**Erro 2: CMAKE_FIND_ROOT_PATH_MODE_LIBRARY como BOTH.**

```cmake
# ERRADO: pode linkar contra libraries do host
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)

# CORRETO: buscar apenas no target
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
```

**Erro 3: Hardcoded paths absolutos.**

```cmake
# ERRADO: path especifico de uma maquina
set(CMAKE_C_COMPILER /home/user/tools/arm/bin/arm-none-eabi-gcc)

# CORRETO: path generico que funciona em qualquer ambiente
find_program(ARM_GCC arm-none-eabi-gcc)
if(NOT ARM_GCC)
    message(FATAL_ERROR "arm-none-eabi-gcc not found in PATH")
endif()
set(CMAKE_C_COMPILER ${ARM_GCC})
```

**Erro 4: Nao verificar existencia do compilador.**

```cmake
# ERRADO: assumir que o compilador existe
set(CMAKE_C_COMPILER arm-none-eabi-gcc)

# CORRETO: verificar antes de usar
find_program(ARM_GCC arm-none-eabi-gcc REQUIRED)
set(CMAKE_C_COMPILER ${ARM_GCC})
```

**Erro 5: Toolchain file commitado com paths do desenvolvedor.**

```cmake
# ERRADO: path do desenvolvedor
set(CMAKE_SYSROOT /home/joao/dev/sysroot)

# CORRETO: path relativo ou via variavel
set(CMAKE_SYSROOT $ENV{TOOLCHAIN_SYSROOT})
```

---

## 4. System Name: CMAKE_SYSTEM_NAME, CMAKE_SYSTEM_PROCESSOR

### 4.1 CMAKE_SYSTEM_NAME

A variavel `CMAKE_SYSTEM_NAME` identifica o sistema operacional alvo. O CMake a usa para decidir comportamentos especificos da plataforma, como convencoes de nomes de arquivos, bibliotecas de sistema e metodos de linking.

```
Valor                    Descricao
Linux                    Target roda Linux
Windows                  Target roda Windows
Darwin                   Target roda macOS
Generic                  Target sem SO (bare-metal, RTOS)
FreeBSD                  Target roda FreeBSD
Emscripten               Target e WebAssembly
Android                  Target roda Android (via NDK)
```

**IMPORTANTE:** Quando `CMAKE_SYSTEM_NAME` e definido no toolchain file, o CMake automaticamente assume que e uma cross-compilation e configura `CMAKE_CROSSCOMPILING` como `TRUE`.

```cmake
# Isso ativa automaticamente CMAKE_CROSSCOMPILING=TRUE
set(CMAKE_SYSTEM_NAME Linux)
```

### 4.2 CMAKE_SYSTEM_PROCESSOR

A variavel `CMAKE_SYSTEM_PROCESSOR` identifica a arquitetura do processador alvo. Ela e usada pelo CMake e por scripts de busca de packages para selecionar a versao correta de libraries.

```
Valor                    Descricao
arm                      ARM 32-bit
aarch64                  ARM 64-bit
x86                      x86 32-bit
x86_64                   x86 64-bit
riscv                    RISC-V
mips                     MIPS
wasm32                   WebAssembly 32-bit
wasm64                   WebAssembly 64-bit
```

### 4.3 Combinacoes Validas

Nem todas as combinacoes de `CMAKE_SYSTEM_NAME` e `CMAKE_SYSTEM_PROCESSOR` sao validas. O CMake valida essas combinacoes internamente e pode rejeitar configuracoes invalidas.

```cmake
# Combinacoes validas para Linux
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)  # ARM64 Linux
set(CMAKE_SYSTEM_PROCESSOR arm)      # ARM32 Linux
set(CMAKE_SYSTEM_PROCESSOR x86_64)   # x86_64 Linux (nao cross, mas valido)
set(CMAKE_SYSTEM_PROCESSOR riscv64)  # RISC-V 64 Linux

# Combinacao invalida (nao existe Windows para ARM64 com GCC nativo)
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR arm)      # Invalido sem cross-compiler adequado
```

### 4.4 Como o CMake Usa essas Variaveis

O CMake usa `CMAKE_SYSTEM_NAME` para:

1. Selecionar o modulo correto de FindModules
2. Determinar convencoes de nomes de libraries (lib.so vs .dll)
3. Configurar comportamento de install
4. Detectar features do compilador

O CMake usa `CMAKE_SYSTEM_PROCESSOR` para:

1. Selecionar bibliotecas corretas no sysroot
2. Determinar flags de arquitetura
3. Filtrar packages no vcpkg/conan
4. Configurar geradores de codigo

### 4.5 Cross-Compilation Detection

O CMake detecta automaticamente cross-compilation quando `CMAKE_SYSTEM_NAME` e diferente do host:

```cmake
# No CMakeLists.txt, voce pode verificar:
if(CMAKE_CROSSCOMPILING)
    message(STATUS "Cross-compiling for ${CMAKE_SYSTEM_NAME}/${CMAKE_SYSTEM_PROCESSOR}")
else()
    message(STATUS "Native compilation for ${CMAKE_SYSTEM_NAME}/${CMAKE_SYSTEM_PROCESSOR}")
endif()
```

Essa verificacao e util para habilitar ou desabilitar features especificas de cross-compilation:

```cmake
if(CMAKE_CROSSCOMPILING)
    # Desabilitar testes que precisam rodar no target
    set(BUILD_TESTING OFF CACHE BOOL "Disable testing" FORCE)

    # Habilitar verificacao adicional de toolchain
    set(VERIFY_TOOLCHAIN ON)

    # Desabilitar features que dependem de execucao no host
    set(ENABLE_CODE_GENERATION OFF)
endif()
```

### 4.6 Detecao Automatica de Processador

Para projetos que precisam de deteccao granular de processador:

```cmake
# Detectar sub-arquitetura do ARM
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm|ARM)")
    include(CheckCCompilerFlag)

    # Verificar suporte a NEON
    check_c_compiler_flag("-mfpu=neon" COMPILER_SUPPORTS_NEON)
    if(COMPILER_SUPPORTS_NEON)
        set(ARM_NEON_AVAILABLE TRUE)
    endif()

    # Verificar suporte a Thumb-2
    check_c_compiler_flag("-mthumb" COMPILER_SUPPORTS_THUMB)
endif()

# Detectar sub-arquitetura do RISC-V
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(riscv|RISCV)")
    # Verificar suporte a extensoes atomic
    include(CheckCSourceCompiles)
    check_c_source_compiles("
        #include <stdatomic.h>
        int main() { return 0; }
    " HAS_STDATOMIC)
endif()
```

---

## 5. Sysroot: CMAKE_SYSROOT

### 5.1 O Que e um Sysroot

O sysroot e o diretorio raiz que contem as headers e libraries do target. Ele funciona como um "mini filesystem" do target, permitindo que o compilador encontre as dependencias corretas para a arquitetura alvo.

Sem um sysroot correto, o compilador pode:

1. Encontrar headers do host em vez do target
2. Linkar contra libraries da arquitetura errada
3. Usar bibliotecas de sistema incompativeis

```
Estrutura tipica de um sysroot:

/opt/toolchain/sysroot/
├── usr/
│   ├── include/
│   │   ├── stdio.h
│   │   ├── stdlib.h
│   │   ├── arm_neon.h
│   │   └── ...
│   ├── lib/
│   │   ├── libc.so
│   │   ├── libm.so
│   │   ├── libpthread.so
│   │   └── ...
│   └── lib/
│       └── aarch64-linux-gnu/
│           └── ...
├── lib/
│   ├── ld-linux-aarch64.so.1
│   └── ...
└── etc/
    └── ...
```

### 5.2 Configurando o Sysroot

```cmake
# No toolchain file:
set(CMAKE_SYSROOT /opt/toolchain/aarch64-linux-gnu/sysroot)

# Ou via linha de commande:
# cmake -DCMAKE_SYSROOT=/opt/toolchain/aarch64-linux-gnu/sysroot ..
```

### 5.3 Verificacao de Integridade do Sysroot

Para cross-compilation segura, o sysroot deve ser verificado:

```cmake
# cmake/VerifySysroot.cmake
function(verify_sysroot)
    if(NOT CMAKE_SYSROOT)
        message(WARNING "No sysroot configured - cross-compilation may use host libraries")
        return()
    endif()

    if(NOT EXISTS "${CMAKE_SYSROOT}")
        message(FATAL_ERROR "Sysroot does not exist: ${CMAKE_SYSROOT}")
    endif()

    # Verificar se o sysroot contem as estruturas basicas
    set(REQUIRED_DIRS "usr/include" "usr/lib")
    foreach(DIR ${REQUIRED_DIRS})
        if(NOT EXISTS "${CMAKE_SYSROOT}/${DIR}")
            message(FATAL_ERROR "Sysroot missing required directory: ${DIR}")
        endif()
    endforeach()

    # Verificar se ha headers basicos
    set(REQUIRED_HEADERS "stdio.h" "stdlib.h" "string.h")
    foreach(HEADER ${REQUIRED_HEADERS})
        if(NOT EXISTS "${CMAKE_SYSROOT}/usr/include/${HEADER}")
            message(WARNING "Sysroot missing header: ${HEADER}")
        endif()
    endforeach()

    # Verificar integridade via checksum (se disponivel)
    set(SYSROOT_CHECKSUM_FILE "${CMAKE_SYSROOT}/.checksum")
    if(EXISTS "${SYSROOT_CHECKSUM_FILE}")
        message(STATUS "Sysroot checksum file found - verifying integrity")
        # A verificacao real depende do formato do checksum
    endif()

    message(STATUS "Sysroot verified: ${CMAKE_SYSROOT}")
endfunction()

# Chamar no inicio do CMakeLists.txt
verify_sysroot()
```

### 5.4 Sysroot vs CMAKE_FIND_ROOT_PATH

Essas duas variaveis tem propositos diferentes:

```
CMAKE_SYSROOT:
  - Caminho para o sysroot do compilador
  - Afeta onde o compilador busca headers e libraries
  - Configurado como --sysroot no gcc/clang
  - Deve apontar para o root do filesystem alvo

CMAKE_FIND_ROOT_PATH:
  - Caminho para onde o CMake busca packages
  - Afeta find_library(), find_path(), find_package()
  - Configurado via variavel CMake
  - Pode ter multiplos valores (lista)
```

```cmake
# Configuracao completa para cross-compilation:
set(CMAKE_SYSROOT /opt/toolchain/sysroot)
set(CMAKE_FIND_ROOT_PATH /opt/toolchain/sysroot/usr)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 5.5 Sysroot Dinamico

Para projetos que suportam multiplos targets, o sysroot pode ser configurado dinamicamente:

```cmake
# cmake/toolchains/linux-arm64.cmake
if(NOT DEFINED ENV{ARM64_SYSROOT})
    # Fallback para localizacao padrao
    set(CMAKE_SYSROOT "/opt/arm64-linux-gnu/sysroot")
else()
    set(CMAKE_SYSROOT "$ENV{ARM64_SYSROOT}")
endif()

# Verificar se o sysroot existe
if(NOT EXISTS "${CMAKE_SYSROOT}")
    message(FATAL_ERROR
        "ARM64 sysroot not found at: ${CMAKE_SYSROOT}\n"
        "Set ARM64_SYSROOT environment variable or install the sysroot.\n"
        "Example: export ARM64_SYSROOT=/opt/arm64-sysroot"
    )
endif()
```

### 5.6 Criando um Sysroot Minimal

Para ambientes onde o sysroot nao esta disponivel:

```bash
#!/bin/bash
# scripts/create-sysroot.sh
# Cria um sysroot minimal para cross-compilation

set -euo pipefail

TARGET_ARCH=$1
SYSROOT_DIR=$2

mkdir -p "${SYSROOT_DIR}/usr/include"
mkdir -p "${SYSROOT_DIR}/usr/lib"
mkdir -p "${SYSROOT_DIR}/lib"

# Baixar e extrair as libraries de destino
case ${TARGET_ARCH} in
    aarch64-linux-gnu)
        sudo apt-get download libacl1-dev:arm64
        sudo dpkg -x libacl1-dev_*.deb "${SYSROOT_DIR}"
        # Baixar mais dependencias conforme necessario
        ;;
    arm-none-eabi)
        # Baixar o toolchain ARM
        wget -q https://developer.arm.com/-/media/Files/downloads/gnu/12.3.rel1/binrel/arm-gnu-toolchain-12.3.rel1-x86_64-arm-none-eabi.tar.xz
        tar xf arm-gnu-toolchain-*.tar.xz -C "${SYSROOT_DIR}"
        ;;
esac

echo "Sysroot created at: ${SYSROOT_DIR}"
```

---

## 6. Compilers: arm-none-eabi-gcc, aarch64-linux-gnu-gcc

### 6.1 Visao Geral dos Compiladores Cross

Compiladores cross sao variacoes de compiladores tradicionais que geram codigo para arquiteturas diferentes do host. Os nomes seguem a convencao:

```
<arquitetura>-<fabricante>-<sistema>
    |              |           |
    |              |           +-- linux-gnu, none-eabi, etc.
    |              +-- fabricante do chip (arm, aarch64, riscv)
    +-- arquitetura do processador
```

### 6.2 Compiladores Comuns

#### 6.2.1 arm-none-eabi-gcc (Bare-metal ARM)

Usado para microcontroladores ARM sem sistema operacional (Cortex-M, Cortex-R).

```cmake
# cmake/toolchains/arm-none-eabi.cmake
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Compiladores
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
set(CMAKE_SIZE arm-none-eabi-size)

# Flags para Cortex-M4 com FPU
set(CPU_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(CMAKE_C_FLAGS_INIT "${CPU_FLAGS}")
set(CMAKE_CXX_FLAGS_INIT "${CPU_FLAGS}")
set(CMAKE_ASM_FLAGS_INIT "${CPU_FLAGS}")

# Linker specs
set(CMAKE_EXE_LINKER_FLAGS_INIT
    "${CPU_FLAGS} -T${CMAKE_CURRENT_LIST_DIR}/STM32F407.ld -specs=nosys.specs -specs=nano.specs"
)

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

#### 6.2.2 aarch64-linux-gnu-gcc (ARM64 Linux)

Usado para sistemas ARM64 com Linux (Raspberry Pi 4, AWS Graviton, Apple Silicon via Linux).

```cmake
# cmake/toolchains/aarch64-linux-gnu.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# Compiladores
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_AR aarch64-linux-gnu-ar)
set(CMAKE_RANLIB aarch64-linux-gnu-ranlib)
set(CMAKE_STRIP aarch64-linux-gnu-strip)
set(CMAKE_OBJCOPY aarch64-linux-gnu-objcopy)

# Sysroot
set(CMAKE_SYSROOT /opt/aarch64-linux-gnu/sysroot)

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

#### 6.2.3 arm-linux-gnueabihf-gcc (ARM32 Linux)

Usado para sistemas ARM32 com Linux e hardware float (Raspberry Pi 3, BeagleBone).

```cmake
# cmake/toolchains/arm-linux-gnueabihf.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Compiladores
set(CMAKE_C_COMPILER arm-linux-gnueabihf-gcc)
set(CMAKE_CXX_COMPILER arm-linux-gnueabihf-g++)
set(CMAKE_AR arm-linux-gnueabihf-ar)
set(CMAKE_RANLIB arm-linux-gnueabihf-ranlib)
set(CMAKE_STRIP arm-linux-gnueabihf-strip)

# Sysroot
set(CMAKE_SYSROOT /opt/arm-linux-gnueabihf/sysroot)

# Flags de seguranca
set(CMAKE_C_FLAGS_INIT "-march=armv7-a -mfpu=neon -mfloat-abi=hard")
set(CMAKE_CXX_FLAGS_INIT "-march=armv7-a -mfpu=neon -mfloat-abi=hard")

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

#### 6.2.4 riscv64-linux-gnu-gcc (RISC-V 64-bit)

Usado para RISC-V 64-bit com Linux.

```cmake
# cmake/toolchains/riscv64-linux-gnu.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

# Compiladores
set(CMAKE_C_COMPILER riscv64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER riscv64-linux-gnu-g++)
set(CMAKE_AR riscv64-linux-gnu-ar)
set(CMAKE_RANLIB riscv64-linux-gnu-ranlib)
set(CMAKE_STRIP riscv64-linux-gnu-strip)

# Sysroot
set(CMAKE_SYSROOT /opt/riscv64-linux-gnu/sysroot)

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 6.3 Verificacao do Compilador Cross

A verificacao do compilador cross e um passo critico que deve ser executado antes de qualquer build:

```cmake
# cmake/VerifyCrossCompiler.cmake
function(verify_cross_compiler)
    # Verificar se CMAKE_CROSSCOMPILING esta ativo
    if(NOT CMAKE_CROSSCOMPILING)
        message(WARNING "Cross-compilation not detected. Check CMAKE_SYSTEM_NAME.")
        return()
    endif()

    # Verificar se o compilador existe
    if(NOT CMAKE_C_COMPILER)
        message(FATAL_ERROR "C compiler not set for cross-compilation")
    endif()

    # Verificar se o compilador funciona
    execute_process(
        COMMAND ${CMAKE_C_COMPILER} --version
        OUTPUT_VARIABLE COMPILER_VERSION
        ERROR_QUIET
        RESULT_VARIABLE COMPILER_RESULT
    )

    if(NOT COMPILER_RESULT EQUAL 0)
        message(FATAL_ERROR
            "Cross-compiler not working: ${CMAKE_C_COMPILER}\n"
            "Error: ${COMPILER_VERSION}"
        )
    endif()

    # Verificar se o compilador e o correto para o target
    string(FIND "${COMPILER_VERSION}" "${CMAKE_SYSTEM_PROCESSOR}" FOUND)
    if(NOT FOUND)
        message(WARNING
            "Compiler may not match target processor.\n"
            "Compiler: ${COMPILER_VERSION}\n"
            "Target: ${CMAKE_SYSTEM_PROCESSOR}"
        )
    endif()

    # Verificar se o compilador suporta as flags de seguranca
    include(CheckCCompilerFlag)
    check_c_compiler_flag("-fstack-protector-strong" HAS_STACK_PROTECTOR)
    if(NOT HAS_STACK_PROTECTOR)
        message(WARNING "Cross-compiler does not support -fstack-protector-strong")
    endif()

    check_c_compiler_flag("-fPIE" HAS_PIE)
    if(NOT HAS_PIE)
        message(WARNING "Cross-compiler does not support -fPIE")
    endif()

    message(STATUS "Cross-compiler verified: ${CMAKE_C_COMPILER}")
    message(STATUS "Compiler version: ${COMPILER_VERSION}")
endfunction()
```

### 6.4 Compiladores Clang Cross

Clang suporta cross-compilation nativamente sem necessidade de toolchains separadas:

```cmake
# cmake/toolchains/clang-aarch64-linux.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# Clang cross-compilation
set(CMAKE_C_COMPILER clang)
set(CMAKE_CXX_COMPILER clang++)

# Flags de target para Clang
set(CMAKE_C_FLAGS_INIT "--target=aarch64-linux-gnu --sysroot=/opt/aarch64-sysroot")
set(CMAKE_CXX_FLAGS_INIT "--target=aarch64-linux-gnu --sysroot=/opt/aarch64-sysroot")

# Find root
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

A vantagem do Clang e que um unico binario pode servir como compilador para multiplos targets, simplificando a gestao de toolchains.

### 6.5 Nomes de Binarios por Target

Apos a compilacao, os binarios gerados precisam ser identificados:

```cmake
# Sufixos de arquivo por sistema operacional alvo
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CMAKE_EXECUTABLE_SUFFIX "")
    set(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
    set(CMAKE_STATIC_LIBRARY_SUFFIX ".a")
    set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")
elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(CMAKE_EXECUTABLE_SUFFIX ".exe")
    set(CMAKE_SHARED_LIBRARY_SUFFIX ".dll")
    set(CMAKE_STATIC_LIBRARY_SUFFIX ".lib")
elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(CMAKE_EXECUTABLE_SUFFIX "")
    set(CMAKE_SHARED_LIBRARY_SUFFIX ".dylib")
    set(CMAKE_STATIC_LIBRARY_SUFFIX ".a")
endif()
```

---

## 7. Target Triplet Concept

### 7.1 O Que e um Target Triplet

O target triplet e uma string que identifica unicamente a combinacao de compilador, arquitetura e sistema operacional alvo. O formato padrao e:

```
<arquitetura>-<fabricante>-<sistema>
```

Exemplos:

```
x86_64-pc-linux-gnu          # Linux x86_64 nativo
aarch64-linux-gnu            # Linux ARM64
arm-none-eabi                # Bare-metal ARM
arm-linux-gnueabihf          # Linux ARM32 com hard float
riscv64-linux-gnu            # Linux RISC-V 64
wasm32-unknown-emscripten    # WebAssembly
```

### 7.2 Componentes do Triplet

```
aarch64-linux-gnu
   |       |    |
   |       |    +-- Vendor: fabricante do SO ou sistema
   |       +------- OS: sistema operacional
   +--------------- CPU: arquitetura do processador
```

### 7.3 Triplets no Contexto do CMake

O CMake nao usa triplets internamente da mesma forma que o Autotools, mas o conceito e importante para:

1. **vcpkg**: Usa triplets para selecionar packages corretos
2. **pkg-config**: Usa triplets para configurar paths
3. **GNU triplet**: Usado pela maioria dos toolchains GCC/Clang

### 7.4 Determinando o Triplet

```cmake
# cmake/DetectTriplet.cmake
function(detect_target_triplet)
    # Mapear CMAKE_SYSTEM_PROCESSOR para componente CPU do triplet
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)")
        set(TRIPLET_CPU "x86_64")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(i[3-6]86|x86)")
        set(TRIPLET_CPU "i686")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|ARM64)")
        set(TRIPLET_CPU "aarch64")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm|ARM)")
        set(TRIPLET_CPU "arm")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(riscv64|RISCV)")
        set(TRIPLET_CPU "riscv64")
    elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(mips|MIPS)")
        set(TRIPLET_CPU "mips")
    else()
        set(TRIPLET_CPU "${CMAKE_SYSTEM_PROCESSOR}")
    endif()

    # Mapear CMAKE_SYSTEM_NAME para componente OS do triplet
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        set(TRIPLET_OS "linux")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
        set(TRIPLET_OS "w64-mingw32")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
        set(TRIPLET_OS "apple")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Generic")
        set(TRIPLET_OS "none")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Emscripten")
        set(TRIPLET_OS "unknown-emscripten")
    elseif(CMAKE_SYSTEM_NAME STREQUAL "Android")
        set(TRIPLET_OS "linux-android")
    else()
        set(TRIPLET_OS "unknown")
    endif()

    # Vendor
    set(TRIPLET_VENDOR "pc" CACHE STRING "Target triplet vendor")

    # Montar o triplet
    set(TARGET_TRIPLET "${TRIPLET_CPU}-${TRIPLET_VENDOR}-${TRIPLET_OS}" PARENT_SCOPE)
    set(TARGET_TRIPLET "${TRIPLET_CPU}-${TRIPLET_VENDOR}-${TRIPLET_OS}")
    message(STATUS "Detected target triplet: ${TARGET_TRIPLET}")
endfunction()
```

### 7.5 Triplets e Seguranca

O triplet correto e essencial para seguranca porque:

1. **Selecao de packages**: Triplets incorretos podem baixar libraries compiladas com flags diferentes
2. **Verificao de hashes**: vcpkg usa triplets para gerar hashes de packages
3. **Reproducibilidade**: Triplets padronizam o ambiente de build
4. **Auditoria**: Triplets documentam exatamente para que target o codigo foi compilado

---

## 8. Find Package em Cross-Compilation

### 8.1 O Desafio

`find_package()` e um dos comandos mais complexos em cross-compilation. Por padrao, ele busca no host, mas em cross-compilation precisamos buscar no target (sysroot).

### 8.2 Configuracao Correta

```cmake
# No toolchain file:
set(CMAKE_FIND_ROOT_PATH /opt/arm64-sysroot)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

Com essa configuracao, `find_package()` buscara automaticamente no sysroot.

### 8.3 find_package e o Sysroot

Quando `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE` e `ONLY`, o CMake：

1. Busca `*.cmake` ou `*-config.cmake` no sysroot
2. Busca em `CMAKE_FIND_ROOT_PATH` e subdiretorios
3. Nao busca no host

```cmake
# Isso encontra o OpenSSL do sysroot, nao do host
find_package(OpenSSL REQUIRED)
```

### 8.4 Packages que Nao Funcionam em Cross-Compilation

Alguns packages usam `try_compile()` ou executam binarios durante a busca, o que falha em cross-compilation porque o binario gerado e para o target e nao pode rodar no host.

```cmake
# Solucao: sobrescrever try_compile para cross-compilation
macro(CMAKE_TRY_COMPILE_PLATFORM_VARIABLES)
    list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES
        CMAKE_SYSTEM_NAME
        CMAKE_SYSTEM_PROCESSOR
        CMAKE_C_COMPILER
        CMAKE_CXX_COMPILER
        CMAKE_SYSROOT
    )
endmacro()
```

### 8.5 Usando Toolchain Files com find_package

```cmake
# cmake/FindCrossOpenSSL.cmake
# Wrapper para find_package(OpenSSL) em cross-compilation

macro(find_cross_package PACKAGE_NAME)
    if(CMAKE_CROSSCOMPILING)
        # Usar find_package com paths do sysroot
        find_package(${PACKAGE_NAME}
            HINTS ${CMAKE_SYSROOT}/usr
            NO_DEFAULT_PATH
        )
    else()
        # Busca normal
        find_package(${PACKAGE_NAME})
    endif()
endmacro()
```

### 8.6 Criando um FindModule Customizado

```cmake
# cmake/FindTargetLib.cmake
# FindModule para bibliotecas customizadas em cross-compilation

#[=[
Find the target library.

This module defines:
  TARGETLIB_FOUND        - True if the library was found
  TARGETLIB_INCLUDE_DIRS - Include directories
  TARGETLIB_LIBRARIES    - Libraries to link
  TARGETLIB_VERSION      - Version of the library
#]=]

# Buscar no sysroot primeiro
find_path(TARGETLIB_INCLUDE_DIR
    NAMES targetlib.h
    HINTS ${CMAKE_SYSROOT}/usr/include
          ${CMAKE_FIND_ROOT_PATH}/include
)

find_library(TARGETLIB_LIBRARY
    NAMES targetlib
    HINTS ${CMAKE_SYSROOT}/usr/lib
          ${CMAKE_SYSROOT}/usr/lib/${CMAKE_SYSTEM_PROCESSOR}-linux-gnu
          ${CMAKE_FIND_ROOT_PATH}/lib
)

# Verificar versao
if(TARGETLIB_INCLUDE_DIR AND EXISTS "${TARGETLIB_INCLUDE_DIR}/targetlib/version.h")
    file(STRINGS "${TARGETLIB_INCLUDE_DIR}/targetlib/version.h" TARGETLIB_VERSION_MAJOR
        REGEX "#define TARGETLIB_VERSION_MAJOR [0-9]+")
    file(STRINGS "${TARGETLIB_INCLUDE_DIR}/targetlib/version.h" TARGETLIB_VERSION_MINOR
        REGEX "#define TARGETLIB_VERSION_MINOR [0-9]+")

    string(REGEX REPLACE ".*#define TARGETLIB_VERSION_MAJOR ([0-9]+).*" "\\1"
        TARGETLIB_VERSION_MAJOR "${TARGETLIB_VERSION_MAJOR}")
    string(REGEX REPLACE ".*#define TARGETLIB_VERSION_MINOR ([0-9]+).*" "\\1"
        TARGETLIB_VERSION_MINOR "${TARGETLIB_VERSION_MINOR}")

    set(TARGETLIB_VERSION "${TARGETLIB_VERSION_MAJOR}.${TARGETLIB_VERSION_MINOR}")
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(TargetLib
    REQUIRED_VARS TARGETLIB_LIBRARY TARGETLIB_INCLUDE_DIR
    VERSION_VAR TARGETLIB_VERSION
)

if(TARGETLIB_FOUND)
    set(TARGETLIB_INCLUDE_DIRS ${TARGETLIB_INCLUDE_DIR})
    set(TARGETLIB_LIBRARIES ${TARGETLIB_LIBRARY})

    if(NOT TARGET TargetLib::TargetLib)
        add_library(TargetLib::TargetLib UNKNOWN IMPORTED)
        set_target_properties(TargetLib::TargetLib PROPERTIES
            IMPORTED_LOCATION "${TARGETLIB_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${TARGETLIB_INCLUDE_DIRS}"
        )
    endif()
endif()

mark_as_advanced(TARGETLIB_INCLUDE_DIR TARGETLIB_LIBRARY)
```

---

## 9. VCPKG_TARGET_TRIPLET

### 9.1 vcpkg e Cross-Compilation

vcpkg e um gerenciador de pacotes que suporta cross-compilation via triplets. O triplet define como compilar e empacotar cada dependencia.

### 9.2 Configuracao de Triplet

```bash
# Definir o triplet para o vcpkg
export VCPKG_TARGET_TRIPLET=arm64-linux
export VCPKG_HOST_TRIPLET=x64-linux

# Ou via CMake
cmake -B build \
    -DCMAKE_TOOLCHAIN_FILE=/path/to/vcpkg/scripts/buildsystems/vcpkg.cmake \
    -DVCPKG_TARGET_TRIPLET=arm64-linux
```

### 9.3 Triplets Padrao do vcpkg

```
Triplet                  Descricao
x64-linux                Linux x86_64
x64-linux-static         Linux x86_64 static
x86-linux                Linux x86 32-bit
arm64-linux              Linux ARM64
arm-linux-dynamic        Linux ARM32 dynamic
x64-windows              Windows x86_64
x64-windows-static       Windows x86_64 static
arm64-windows            Windows ARM64
x64-osx                  macOS x86_64
arm64-osx                macOS ARM64
wasm32-emscripten        WebAssembly
```

### 9.4 Criando um Triplet Customizado

```cmake
# vcpkg/triplets/community/arm-linux-gnueabihf.cmake
set(VCPKG_TARGET_ARCHITECTURE arm)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_CMAKE_SYSTEM_NAME Linux)
set(VCPKG_CMAKE_CONFIGURE_OPTIONS
    -DCMAKE_SYSTEM_NAME=Linux
    -DCMAKE_SYSTEM_PROCESSOR=arm
    -DCMAKE_C_COMPILER=arm-linux-gnueabihf-gcc
    -DCMAKE_CXX_COMPILER=arm-linux-gnueabihf-g++
    -DCMAKE_SYSROOT=/opt/arm-sysroot
)
```

### 9.5 Integracao com CMakeLists.txt

```cmake
# CMakeLists.txt principal
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES C CXX)

# vcpkg integration
if(DEFINED ENV{VCPKG_ROOT})
    set(CMAKE_TOOLCHAIN_FILE
        "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        CACHE STRING "vcpkg toolchain file"
    )
endif()

# Packages (vcpkg respeita o triplet)
find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(spdlog REQUIRED)

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE ZLIB::ZLIB OpenSSL::SSL spdlog::spdlog)
```

### 9.6 Triplets e Seguranca do vcpkg

O triplet afeta diretamente a seguranca porque:

1. **Linkage estatico vs dinamico**: Estatico e mais seguro em embedded (nao depende de libraries no target)
2. **Flags de compilacao**: Triplets podem incluir flags de hardening
3. **Reproducibilidade**: Triplets fixam opcoes de compilacao
4. **Auditoria**: Triplets documentam como cada package foi compilado

```cmake
# Triplet seguro para embedded
set(VCPKG_TARGET_ARCHITECTURE arm)
set(VCPKG_CRT_LINKAGE static)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_CMAKE_SYSTEM_NAME Generic)
set(VCPKG_CMAKE_CONFIGURE_OPTIONS
    -DCMAKE_SYSTEM_NAME=Generic
    -DCMAKE_C_FLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2"
    -DCMAKE_CXX_FLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2"
)
```

### 9.7 Resolucao de Dependencias Cross

Quando uma dependencia do target requer outra dependencia, o vcpkg resolve automaticamente usando o mesmo triplet:

```bash
# Isso instala todas as dependencias para ARM64 Linux
vcpkg install openssl:arm64-linux

# O vcpkg instala automaticamente as dependencias transitivas
# OpenSSL -> zlib (tambem para arm64-linux)
```

---

## 10. Secure Cross-Builds: Verificacao de Toolchain

### 10.1 Por Que Verificar a Toolchain

A toolchain e o pilar de confianca em cross-compilation. Se ela for comprometida, todos os binarios gerados podem conter backdoors, vulnerabilidades ou comportamento malicioso.

### 10.2 Verificacao de Hash

```cmake
# cmake/VerifyToolchain.cmake
function(verify_toolchain_hash)
    if(NOT DEFINED TOOLCHAIN_HASH)
        message(STATUS "No toolchain hash verification configured")
        return()
    endif()

    # Calcular hash do compilador
    file(MD5 "${CMAKE_C_COMPILER}" COMPILER_HASH)
    file(SHA256 "${CMAKE_C_COMPILER}" COMPILER_HASH_SHA256)

    if(COMPILER_HASH STREQUAL TOOLCHAIN_HASH)
        message(STATUS "Toolchain hash verification PASSED")
    else()
        message(FATAL_ERROR
            "Toolchain hash verification FAILED!\n"
            "Expected: ${TOOLCHAIN_HASH}\n"
            "Got: ${COMPILER_HASH}\n"
            "This could indicate a compromised toolchain."
        )
    endif()
endfunction()
```

### 10.3 Verificacao de Versao do Compilador

```cmake
# cmake/VerifyCompilerVersion.cmake
function(verify_compiler_version)
    # Obter versao do compilador
    execute_process(
        COMMAND ${CMAKE_C_COMPILER} -dumpversion
        OUTPUT_VARIABLE COMPILER_VERSION_RAW
        ERROR_QUIET
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )

    # Parse da versao
    string(REGEX MATCH "([0-9]+)\\.([0-9]+)\\.([0-9]+)" _ "${COMPILER_VERSION_RAW}")
    set(COMPILER_MAJOR ${CMAKE_MATCH_1})
    set(COMPILER_MINOR ${CMAKE_MATCH_2})
    set(COMPILER_PATCH ${CMAKE_MATCH_3})

    # Verificar versao minima
    if(COMPILER_MAJOR LESS 12)
        message(WARNING
            "Cross-compiler version ${COMPILER_VERSION_RAW} is too old.\n"
            "Minimum recommended: 12.0.0\n"
            "Older compilers may have known vulnerabilities."
        )
    endif()

    # Verificar se e uma versao conhecida vulneravel
    set(VULNERABLE_VERSIONS
        "11.3.0"  # Known issue
        "10.2.0"  # Known issue
    )

    foreach(VULN ${VULNERABLE_VERSIONS})
        if("${COMPILER_VERSION_RAW}" STREQUAL "${VULN}")
            message(FATAL_ERROR
                "Cross-compiler version ${COMPILER_VERSION_RAW} has known vulnerabilities.\n"
                "Please update to a newer version."
            )
        endif()
    endforeach()

    message(STATUS "Compiler version verified: ${COMPILER_VERSION_RAW}")
endfunction()
```

### 10.4 Verificacao de Sysroot

```cmake
# cmake/VerifySysrootIntegrity.cmake
function(verify_sysroot_integrity)
    if(NOT CMAKE_SYSROOT)
        message(STATUS "No sysroot configured, skipping verification")
        return()
    endif()

    # Verificar se o sysroot e um diretorio
    if(NOT IS_DIRECTORY "${CMAKE_SYSROOT}")
        message(FATAL_ERROR "Sysroot is not a directory: ${CMAKE_SYSROOT}")
    endif()

    # Verificar permissoes
    file(REAL_PATH "${CMAKE_SYSROOT}" SYSROOT_REAL_PATH)
    if(NOT IS_READABLE "${SYSROOT_REAL_PATH}")
        message(FATAL_ERROR "Sysroot is not readable: ${SYSROOT_REAL_PATH}")
    endif()

    # Verificar estrutura basica
    set(REQUIRED_FILES
        "usr/include/stdio.h"
        "usr/include/stdlib.h"
        "usr/include/string.h"
    )

    foreach(FILE ${REQUIRED_FILES})
        if(NOT EXISTS "${CMAKE_SYSROOT}/${FILE}")
            message(WARNING "Sysroot missing: ${FILE}")
        endif()
    endforeach()

    # Verificar se o sysroot nao contem arquivos suspeitos
    file(GLOB SUSPICIOUS_FILES "${CMAKE_SYSROOT}/**/*.sh"
         "${CMAKE_SYSROOT}/**/*.py" "${CMAKE_SYSROOT}/**/*.pl")

    if(SUSPICIOUS_FILES)
        message(WARNING
            "Sysroot contains script files that may be suspicious:\n"
            "${SUSPICIOUS_FILES}\n"
            "Review these files before proceeding."
        )
    endif()

    message(STATUS "Sysroot integrity verified: ${CMAKE_SYSROOT}")
endfunction()
```

### 10.5 Verificacao Completa de Cross-Build

```cmake
# cmake/SecureCrossBuild.cmake
function(secure_cross_build_setup)
    # 1. Verificar se estamos em cross-compilation
    if(NOT CMAKE_CROSSCOMPILING)
        message(STATUS "Not cross-compiling, skipping cross-build security checks")
        return()
    endif()

    message(STATUS "=== Secure Cross-Build Setup ===")

    # 2. Verificar toolchain
    include(VerifyCrossCompiler)
    verify_cross_compiler()

    # 3. Verificar hash do compilador (se configurado)
    if(DEFINED TOOLCHAIN_HASH)
        include(VerifyToolchain)
        verify_toolchain_hash()
    endif()

    # 4. Verificar versao do compilador
    include(VerifyCompilerVersion)
    verify_compiler_version()

    # 5. Verificar sysroot
    include(VerifySysrootIntegrity)
    verify_sysroot_integrity()

    # 6. Verificar flags de seguranca
    include(CheckSecurityFlags)
    check_security_flags_available()

    # 7. Registrar informacoes do cross-build
    set(CROSS_BUILD_INFO
        "Host: ${CMAKE_HOST_SYSTEM_NAME}/${CMAKE_HOST_SYSTEM_PROCESSOR}"
        "Target: ${CMAKE_SYSTEM_NAME}/${CMAKE_SYSTEM_PROCESSOR}"
        "C Compiler: ${CMAKE_C_COMPILER}"
        "CXX Compiler: ${CMAKE_CXX_COMPILER}"
        "Sysroot: ${CMAKE_SYSROOT}"
        "Timestamp: ${CMAKE_CURRENT_LIST_FILE}:${CMAKE_CURRENT_LIST_LINE}"
    )
    string(REPLACE ";" "\n" CROSS_BUILD_INFO "${CROSS_BUILD_INFO}")

    file(WRITE
        "${CMAKE_BINARY_DIR}/cross-build-info.txt"
        "${CROSS_BUILD_INFO}"
    )

    message(STATUS "Cross-build info written to: ${CMAKE_BINARY_DIR}/cross-build-info.txt")
    message(STATUS "=== Secure Cross-Build Setup Complete ===")
endfunction()
```

### 10.6 Verificacao de Binarios Gerados

Apos a compilacao, os binarios devem ser verificados:

```cmake
# cmake/VerifyCrossBinaries.cmake
function(verify_cross_binaries)
    # Verificar formato do binario
    foreach(BINARY ${ARGN})
        if(NOT EXISTS "${BINARY}")
            message(WARNING "Binary not found: ${BINARY}")
            continue()
        endif()

        # Verificar se o binario e para o target correto
        execute_process(
            COMMAND file "${BINARY}"
            OUTPUT_VARIABLE FILE_OUTPUT
            ERROR_QUIET
        )

        if(CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
            string(FIND "${FILE_OUTPUT}" "ARM aarch64" FOUND)
        elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL "arm")
            string(FIND "${FILE_OUTPUT}" "ARM" FOUND)
        elseif(CMAKE_SYSTEM_PROCESSOR STREQUAL "x86_64")
            string(FIND "${FILE_OUTPUT}" "x86-64" FOUND)
        else()
            set(FOUND TRUE)
        endif()

        if(NOT FOUND)
            message(WARNING
                "Binary ${BINARY} does not match target architecture.\n"
                "Output: ${FILE_OUTPUT}"
            )
        else()
            message(STATUS "Binary verified: ${BINARY}")
        endif()

        # Verificar se o binario esta stripped (producao)
        execute_process(
            COMMAND ${CMAKE_OBJDUMP} -h "${BINARY}"
            OUTPUT_VARIABLE OBJDUMP_OUTPUT
            ERROR_QUIET
        )

        string(FIND "${OBJDUMP_OUTPUT}" ".debug" HAS_DEBUG)
        if(HAS_DEBUG)
            message(STATUS "Binary ${BINARY} contains debug symbols (not stripped)")
        endif()
    endforeach()
endfunction()
```

### 10.7 Checklist de Seguranca para Cross-Builds

```
[ ] Toolchain baixada de fonte confiavel
[ ] Hash/sha256 da toolchain verificado contra valor esperado
[ ] Versao do compilador e recente e nao contem CVEs conhecidos
[ ] Sysroot verificado (estrutura, integridade, ausencia de scripts)
[ ] CMAKE_FIND_ROOT_PATH_MODE_LIBRARY configurado como ONLY
[ ] CMAKE_FIND_ROOT_PATH_MODE_INCLUDE configurado como ONLY
[ ] CMAKE_FIND_ROOT_PATH_MODE_PACKAGE configurado como ONLY
[ ] Flags de hardening habilitadas no toolchain file
[ ] Binarios finais verificados com file(1) para arquitetura correta
[ ] Binarios stripped para producao
[ ] cross-build-info.txt gerado para auditoria
[ ] Build em ambiente isolado (container, VM limpa)
[ ] Dependencias baixadas com verificacao de hash
[ ] SBOM gerado para o cross-build
[ ] Build reproduzivel verificado em outro ambiente
```

---

## 11. Build for Multiple Architectures

### 11.1 O Desafio de Multi-Architecture

Muitos projetos precisam gerar binarios para multiplos targets simultaneamente. Isso e comum em:

- Sistemas embarcados que suportam multiplos hardware
- Aplicacoes mobile (Android multi-ABI)
- Docker multi-architecture images
- Distribuicoes Linux para varias arquiteturas

### 11.2 Abordagem 1: Build Separados

```bash
# Build para cada arquitetura separadamente
cmake -B build-arm64 \
    -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-gnu.cmake \
    -DCMAKE_INSTALL_PREFIX=/opt/arm64
cmake --build build-arm64

cmake -B build-arm32 \
    -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/arm-linux-gnueabihf.cmake \
    -DCMAKE_INSTALL_PREFIX=/opt/arm32
cmake --build build-arm32

cmake -B build-x86_64 \
    -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/x86_64-linux-gnu.cmake \
    -DCMAKE_INSTALL_PREFIX=/opt/x86_64
cmake --build build-x86_64
```

### 11.3 Abordagem 2: CMake Presets

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "arm64-linux",
            "displayName": "ARM64 Linux",
            "toolchainFile": "${sourceDir}/cmake/toolchains/aarch64-linux-gnu.cmake",
            "binaryDir": "${sourceDir}/build-arm64",
            "cacheVariables": {
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/arm64"
            }
        },
        {
            "name": "arm32-linux",
            "displayName": "ARM32 Linux",
            "toolchainFile": "${sourceDir}/cmake/toolchains/arm-linux-gnueabihf.cmake",
            "binaryDir": "${sourceDir}/build-arm32",
            "cacheVariables": {
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/arm32"
            }
        },
        {
            "name": "x86_64-linux",
            "displayName": "x86_64 Linux",
            "toolchainFile": "${sourceDir}/cmake/toolchains/x86_64-linux-gnu.cmake",
            "binaryDir": "${sourceDir}/build-x86_64",
            "cacheVariables": {
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/x86_64"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "arm64-release",
            "configurePreset": "arm64-linux",
            "configuration": "Release"
        },
        {
            "name": "arm32-release",
            "configurePreset": "arm32-linux",
            "configuration": "Release"
        },
        {
            "name": "x86_64-release",
            "configurePreset": "x86_64-linux",
            "configuration": "Release"
        }
    ]
}
```

### 11.4 Abordagem 3: Super Builds com ExternalProject

```cmake
# cmake/superbuild-multiarch.cmake
# Super-build que gera binarios para multiplos targets

include(ExternalProject)

set(TARGETS
    "aarch64-linux-gnu:aarch64:ARM64 Linux"
    "arm-linux-gnueabihf:arm:ARM32 Linux"
    "x86_64-linux-gnu:x86_64:x86_64 Linux"
)

foreach(TARGET_INFO ${TARGETS})
    string(REPLACE ":" ";" TARGET_PARTS ${TARGET_INFO})
    list(GET TARGET_PARTS 0 TRIPLET)
    list(GET TARGET_PARTS 1 ARCH)
    list(GET TARGET_PARTS 2 DESCRIPTION)

    ExternalProject_Add(
        "build-${ARCH}"
        SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}
        CMAKE_ARGS
            -DCMAKE_TOOLCHAIN_FILE=${CMAKE_CURRENT_SOURCE_DIR}/cmake/toolchains/${TRIPLET}.cmake
            -DCMAKE_INSTALL_PREFIX=${CMAKE_CURRENT_BINARY_DIR}/install/${ARCH}
            -DCMAKE_BUILD_TYPE=Release
        BUILD_COMMAND ${CMAKE_COMMAND} --build <BINARY_DIR> --config Release
        INSTALL_COMMAND ${CMAKE_COMMAND} --install <BINARY_DIR> --config Release
    )
endforeach()
```

### 11.5 Gerenciamento de Build Directory

```cmake
# cmake/MultiArchBuild.cmake
function(multi_arch_build)
    # Criar diretorios de build para cada arquitetura
    set(ARCHITECTURES
        "aarch64-linux-gnu:arm64"
        "arm-linux-gnueabihf:arm"
        "x86_64-linux-gnu:x86_64"
    )

    foreach(ARCH_INFO ${ARCHITECTURES})
        string(REPLACE ":" ";" ARCH_PARTS ${ARCH_INFO})
        list(GET ARCH_PARTS 0 TRIPLET)
        list(GET ARCH_PARTS 1 ARCH)

        set(BUILD_DIR "${CMAKE_BINARY_DIR}/build-${ARCH}")
        set(INSTALL_DIR "${CMAKE_BINARY_DIR}/install-${ARCH}")

        # Verificar se o toolchain existe
        set(TOOLCHAIN_FILE "${CMAKE_SOURCE_DIR}/cmake/toolchains/${TRIPLET}.cmake")
        if(NOT EXISTS "${TOOLCHAIN_FILE}")
            message(WARNING "Toolchain not found for ${ARCH}: ${TOOLCHAIN_FILE}")
            continue()
        endif()

        # Configurar build
        execute_process(
            COMMAND ${CMAKE_COMMAND}
                -S ${CMAKE_SOURCE_DIR}
                -B ${BUILD_DIR}
                -DCMAKE_TOOLCHAIN_FILE=${TOOLCHAIN_FILE}
                -DCMAKE_INSTALL_PREFIX=${INSTALL_DIR}
                -DCMAKE_BUILD_TYPE=Release
            RESULT_VARIABLE CONFIGURE_RESULT
        )

        if(NOT CONFIGURE_RESULT EQUAL 0)
            message(FATAL_ERROR "Configure failed for ${ARCH}")
        endif()

        # Build
        execute_process(
            COMMAND ${CMAKE_COMMAND} --build ${BUILD_DIR} --config Release
            RESULT_VARIABLE BUILD_RESULT
        )

        if(NOT BUILD_RESULT EQUAL 0)
            message(FATAL_ERROR "Build failed for ${ARCH}")
        endif()

        # Install
        execute_process(
            COMMAND ${CMAKE_COMMAND} --install ${BUILD_DIR} --config Release
            RESULT_VARIABLE INSTALL_RESULT
        )

        if(NOT INSTALL_RESULT EQUAL 0)
            message(FATAL_ERROR "Install failed for ${ARCH}")
        endif()

        message(STATUS "Build completed for ${ARCH}: ${INSTALL_DIR}")
    endforeach()
endfunction()
```

### 11.6 Docker Multi-Architecture

```cmake
# cmake/DockerMultiArch.cmake
function(docker_multi_arch_build)
    # Definir alvos
    set(ARCHITECTURES "linux/arm64" "linux/arm/v7" "linux/amd64")

    foreach(ARCH ${ARCHITECTURES})
        # Criar Dockerfile para cada arquitetura
        configure_file(
            "${CMAKE_SOURCE_DIR}/cmake/Dockerfile.cross.in"
            "${CMAKE_BINARY_DIR}/Dockerfile.${ARCH}"
            @ONLY
        )

        # Build da imagem
        execute_process(
            COMMAND docker buildx build
                --platform ${ARCH}
                -t "${PROJECT_NAME}:${ARCH}"
                -f "${CMAKE_BINARY_DIR}/Dockerfile.${ARCH}"
                .
            RESULT_VARIABLE DOCKER_BUILD_RESULT
        )

        if(NOT DOCKER_BUILD_RESULT EQUAL 0)
            message(FATAL_ERROR "Docker build failed for ${ARCH}")
        endif()
    endforeach()

    # Criar manifest multi-arch
    execute_process(
        COMMAND docker manifest create
            "${PROJECT_NAME}:latest"
            ${foreach(ARCH ${ARCHITECTURES} "${PROJECT_NAME}:${ARCH}")}
        RESULT_VARIABLE MANIFEST_RESULT
    )
endfunction()
```

---

## 12. CMake Presets for Cross-Compilation

### 12.1 Visao Geral dos Presets

CMake presets (disponiveis desde CMake 3.19) permitem definir configuracoes de build declarativamente, incluindo toolchain files e variaveis de cross-compilation.

### 12.2 Estrutura de Presets

```json
{
    "version": 6,
    "cmakeMinimumRequired": {
        "major": 3,
        "minor": 21,
        "patch": 0
    },
    "configurePresets": [
        {
            "name": "default",
            "displayName": "Default Config",
            "description": "Default configuration with security hardening",
            "binaryDir": "${sourceDir}/build/${presetName}",
            "installDir": "${sourceDir}/install/${presetName}",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "BUILD_SHARED_LIBS": "OFF"
            }
        },
        {
            "name": "arm64-linux",
            "displayName": "ARM64 Linux Cross-Compilation",
            "description": "Cross-compile for ARM64 Linux with security hardening",
            "inherits": "default",
            "toolchainFile": "${sourceDir}/cmake/toolchains/aarch64-linux-gnu.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/arm64",
                "VERIFY_TOOLCHAIN": "ON",
                "ENABLE_HARDENING": "ON"
            }
        },
        {
            "name": "arm32-linux",
            "displayName": "ARM32 Linux Cross-Compilation",
            "description": "Cross-compile for ARM32 Linux with security hardening",
            "inherits": "default",
            "toolchainFile": "${sourceDir}/cmake/toolchains/arm-linux-gnueabihf.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/arm32",
                "VERIFY_TOOLCHAIN": "ON"
            }
        },
        {
            "name": "arm-none-eabi",
            "displayName": "ARM Bare-Metal",
            "description": "Cross-compile for ARM Cortex-M bare-metal",
            "inherits": "default",
            "toolchainFile": "${sourceDir}/cmake/toolchains/arm-none-eabi.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/bare-metal",
                "ARM_TARGET_MCU": "cortex-m4",
                "ARM_TARGET_FPU": "fpv4-sp-d16"
            }
        },
        {
            "name": "riscv64-linux",
            "displayName": "RISC-V 64 Linux Cross-Compilation",
            "description": "Cross-compile for RISC-V 64 Linux",
            "inherits": "default",
            "toolchainFile": "${sourceDir}/cmake/toolchains/riscv64-linux-gnu.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/riscv64"
            }
        },
        {
            "name": "wasm",
            "displayName": "WebAssembly",
            "description": "Cross-compile for WebAssembly via Emscripten",
            "inherits": "default",
            "toolchainFile": "$ENV{EMSDK}/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/wasm"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "arm64-release",
            "configurePreset": "arm64-linux",
            "configuration": "Release"
        },
        {
            "name": "arm32-release",
            "configurePreset": "arm32-linux",
            "configuration": "Release"
        },
        {
            "name": "arm-bare-metal",
            "configurePreset": "arm-none-eabi",
            "configuration": "Release"
        },
        {
            "name": "riscv64-release",
            "configurePreset": "riscv64-linux",
            "configuration": "Release"
        },
        {
            "name": "wasm-release",
            "configurePreset": "wasm",
            "configuration": "Release"
        }
    ],
    "testPresets": [
        {
            "name": "arm64-test",
            "configurePreset": "arm64-linux",
            "output": {
                "outputOnFailure": true
            }
        }
    ]
}
```

### 12.3 Uso de Presets

```bash
# Listar presets disponiveis
cmake --list-presets

# Configurar para ARM64
cmake --preset arm64-linux

# Build para ARM64
cmake --build --preset arm64-release

# Configurar para ARM32
cmake --preset arm32-linux

# Build para ARM32
cmake --build --preset arm32-release

# Configurar para bare-metal
cmake --preset arm-none-eabi

# Build para bare-metal
cmake --build --preset arm-bare-metal
```

### 12.4 Presets Herdados

Presets podem herdar de outros presets para reutilizar configuracoes:

```json
{
    "configurePresets": [
        {
            "name": "base-cross",
            "description": "Base cross-compilation settings",
            "cacheVariables": {
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "VERIFY_TOOLCHAIN": "ON"
            }
        },
        {
            "name": "arm64-linux",
            "inherits": "base-cross",
            "toolchainFile": "${sourceDir}/cmake/toolchains/aarch64-linux-gnu.cmake",
            "cacheVariables": {
                "CMAKE_INSTALL_PREFIX": "${sourceDir}/install/arm64"
            }
        },
        {
            "name": "arm64-linux-debug",
            "inherits": "arm64-linux",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_SANITIZERS": "ON"
            }
        }
    ]
}
```

### 12.5 Presets para CI/CD

```json
{
    "configurePresets": [
        {
            "name": "ci-arm64",
            "inherits": "arm64-linux",
            "binaryDir": "${sourceDir}/build/ci-arm64",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "ENABLE_HARDENING": "ON",
                "BUILD_TESTING": "OFF"
            },
            "environment": {
                "TOOLCHAIN_HASH": "$env{TOOLCHAIN_HASH}"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "ci-arm64-release",
            "configurePreset": "ci-arm64",
            "configuration": "Release",
            "jobs": 4
        }
    ]
}
```

### 12.6 Validacao de Presets

```cmake
# cmake/ValidatePresets.cmake
function(validate_cross_preset)
    # Verificar se o preset esta configurado corretamente
    if(NOT CMAKE_CROSSCOMPILING)
        message(STATUS "Not cross-compiling, skipping preset validation")
        return()
    endif()

    # Verificar toolchain
    if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
        message(FATAL_ERROR "CMAKE_TOOLCHAIN_FILE not set in cross-compilation preset")
    endif()

    if(NOT EXISTS "${CMAKE_TOOLCHAIN_FILE}")
        message(FATAL_ERROR "Toolchain file not found: ${CMAKE_TOOLCHAIN_FILE}")
    endif()

    # Verificar variaveis obrigatorias
    set(REQUIRED_VARS
        CMAKE_SYSTEM_NAME
        CMAKE_SYSTEM_PROCESSOR
        CMAKE_C_COMPILER
    )

    foreach(VAR ${REQUIRED_VARS})
        if(NOT DEFINED ${VAR} OR "${${VAR}}" STREQUAL "")
            message(FATAL_ERROR "Required variable not set in preset: ${VAR}")
        endif()
    endforeach()

    message(STATUS "Cross-compilation preset validated successfully")
endfunction()
```

---

## 13. Exemplo: ARM Cross-Compilation Seguro

### 13.1 Cenario Completo

Neste exemplo, vamos criar um projeto completo que executa cross-compilation para ARM64 Linux com todas as verificacoes de seguranca habilitadas.

### 13.2 Estrutura do Projeto

```
secure-arm-project/
├── CMakeLists.txt
├── CMakePresets.json
├── cmake/
│   ├── toolchains/
│   │   ├── aarch64-linux-gnu.cmake
│   │   └── arm-none-eabi.cmake
│   ├── VerifyCrossCompiler.cmake
│   ├── VerifyToolchain.cmake
│   ├── VerifySysrootIntegrity.cmake
│   ├── SecureCrossBuild.cmake
│   └── SecurityFlags.cmake
├── src/
│   ├── main.cpp
│   ├── crypto/
│   │   ├── CMakeLists.txt
│   │   └── hash.cpp
│   └── network/
│       ├── CMakeLists.txt
│       └── client.cpp
├── tests/
│   ├── CMakeLists.txt
│   └── test_main.cpp
└── scripts/
    ├── build-all-archs.sh
    └── verify-binaries.sh
```

### 13.3 Toolchain File Seguro

```cmake
# cmake/toolchains/aarch64-linux-gnu.cmake
# Secure cross-compilation toolchain for ARM64 Linux

# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# ============================================================================
# COMPILER CONFIGURATION
# ============================================================================

# Compiladores
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_ASM_COMPILER aarch64-linux-gnu-gcc)

# Arquivador e utilitarios
set(CMAKE_AR aarch64-linux-gnu-ar)
set(CMAKE_RANLIB aarch64-linux-gnu-ranlib)
set(CMAKE_STRIP aarch64-linux-gnu-strip)
set(CMAKE_OBJCOPY aarch64-linux-gnu-objcopy)
set(CMAKE_OBJDUMP aarch64-linux-gnu-objdump)
set(CMAKE_SIZE aarch64-linux-gnu-size)

# ============================================================================
# SYSROOT CONFIGURATION
# ============================================================================

# Buscar sysroot via variavel de ambiente ou path padrao
if(DEFINED ENV{ARM64_SYSROOT})
    set(CMAKE_SYSROOT "$ENV{ARM64_SYSROOT}")
elseif(EXISTS "/opt/aarch64-linux-gnu/sysroot")
    set(CMAKE_SYSROOT "/opt/aarch64-linux-gnu/sysroot")
elseif(EXISTS "/usr/aarch64-linux-gnu")
    set(CMAKE_SYSROOT "/usr/aarch64-linux-gnu")
else()
    message(FATAL_ERROR
        "ARM64 sysroot not found.\n"
        "Set ARM64_SYSROOT environment variable or install the sysroot.\n"
        "Example: export ARM64_SYSROOT=/opt/arm64-sysroot"
    )
endif()

# ============================================================================
# FIND ROOT CONFIGURATION
# ============================================================================

# Programas: buscar no host (nao no target)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# Libraries: buscar apenas no target
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)

# Headers: buscar apenas no target
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)

# Packages: buscar apenas no target
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# ============================================================================
# SECURITY FLAGS
# ============================================================================

# Flags de seguranca para ARM64
set(ARM64_SECURITY_FLAGS
    "-fstack-protector-strong"
    "-D_FORTIFY_SOURCE=2"
    "-fPIE"
    "-Wformat"
    "-Wformat-security"
)

# Flags de compilacao
set(CMAKE_C_FLAGS_INIT "${ARM64_SECURITY_FLAGS}")
set(CMAKE_CXX_FLAGS_INIT "${ARM64_SECURITY_FLAGS}")

# Flags de linking
set(CMAKE_EXE_LINKER_FLAGS_INIT "-pie -Wl,-z,relro,-z,now")

# ============================================================================
# FIND ROOT PATH
# ============================================================================

set(CMAKE_FIND_ROOT_PATH
    ${CMAKE_SYSROOT}
    ${CMAKE_SYSROOT}/usr
)
```

### 13.4 Modulos de Verificacao

```cmake
# cmake/SecureCrossBuild.cmake
# Modulo principal de verificacao de cross-compilation segura

#[=[
Secure Cross-Build Module

Este modulo implementa verificacoes de seguranca para cross-compilation.
Ele deve ser incluido no inicio do CMakeLists.txt principal.

Uso:
    include(SecureCrossBuild)
    secure_cross_build_setup()
#]=]

# ============================================================================
# FUNCTIONS
# ============================================================================

#[=[
Verificar se a toolchain esta configurada corretamente.
Verifica existencia, funcionalidade e compatibilidade.
#]=]
function(verify_toolchain)
    if(NOT CMAKE_CROSSCOMPILING)
        message(STATUS "[SECURE-CROSS] Not cross-compiling, skipping toolchain verification")
        return()
    endif()

    message(STATUS "[SECURE-CROSS] Verifying cross-compilation toolchain...")

    # Verificar compilador C
    if(NOT CMAKE_C_COMPILER)
        message(FATAL_ERROR "[SECURE-CROSS] C compiler not configured")
    endif()

    if(NOT EXISTS "${CMAKE_C_COMPILER}")
        # Verificar se esta no PATH
        find_program(CMAKE_C_COMPILER NAMES ${CMAKE_C_COMPILER})
        if(NOT CMAKE_C_COMPILER)
            message(FATAL_ERROR
                "[SECURE-CROSS] C compiler not found: ${CMAKE_C_COMPILER}\n"
                "Ensure the cross-compiler is installed and in PATH."
            )
        endif()
    endif()

    # Verificar compilador C++
    if(NOT CMAKE_CXX_COMPILER)
        message(FATAL_ERROR "[SECURE-CROSS] C++ compiler not configured")
    endif()

    # Verificar versao do compilador
    execute_process(
        COMMAND ${CMAKE_C_COMPILER} --version
        OUTPUT_VARIABLE COMPILER_VERSION
        ERROR_QUIET
        RESULT_VARIABLE COMPILER_RESULT
    )

    if(NOT COMPILER_RESULT EQUAL 0)
        message(FATAL_ERROR
            "[SECURE-CROSS] Cross-compiler not working: ${CMAKE_C_COMPILER}"
        )
    endif()

    # Verificar se o compilador e para o target correto
    string(TOLOWER "${COMPILER_VERSION}" COMPILER_VERSION_LOWER)
    if(CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
        string(FIND "${COMPILER_VERSION_LOWER}" "aarch64" FOUND)
        if(NOT FOUND)
            message(WARNING
                "[SECURE-CROSS] Compiler may not be for ARM64.\n"
                "Version: ${COMPILER_VERSION}"
            )
        endif()
    endif()

    message(STATUS "[SECURE-CROSS] Toolchain verified: ${CMAKE_C_COMPILER}")
    message(STATUS "[SECURE-CROSS] Compiler version: ${COMPILER_VERSION}")
endfunction()

#[=[
Verificar integridade do sysroot.
#]=]
function(verify_sysroot)
    if(NOT CMAKE_CROSSCOMPILING)
        return()
    endif()

    if(NOT CMAKE_SYSROOT)
        message(WARNING "[SECURE-CROSS] No sysroot configured")
        return()
    endif()

    message(STATUS "[SECURE-CROSS] Verifying sysroot: ${CMAKE_SYSROOT}")

    # Verificar se o sysroot existe
    if(NOT EXISTS "${CMAKE_SYSROOT}")
        message(FATAL_ERROR "[SECURE-CROSS] Sysroot does not exist: ${CMAKE_SYSROOT}")
    endif()

    # Verificar estrutura
    set(REQUIRED_DIRS "usr/include" "usr/lib")
    foreach(DIR ${REQUIRED_DIRS})
        if(NOT IS_DIRECTORY "${CMAKE_SYSROOT}/${DIR}")
            message(WARNING "[SECURE-CROSS] Sysroot missing directory: ${DIR}")
        endif()
    endforeach()

    # Verificar headers basicos
    set(REQUIRED_HEADERS "stdio.h" "stdlib.h" "string.h" "stdint.h")
    foreach(HEADER ${REQUIRED_HEADERS})
        if(NOT EXISTS "${CMAKE_SYSROOT}/usr/include/${HEADER}")
            message(WARNING "[SECURE-CROSS] Sysroot missing header: ${HEADER}")
        endif()
    endforeach()

    message(STATUS "[SECURE-CROSS] Sysroot verification complete")
endfunction()

#[=[
Verificar flags de seguranca disponiveis.
#]=]
function(verify_security_flags)
    if(NOT CMAKE_CROSSCOMPILING)
        return()
    endif()

    message(STATUS "[SECURE-CROSS] Verifying security flags...")

    include(CheckCCompilerFlag)

    # Stack protector
    check_c_compiler_flag("-fstack-protector-strong" HAS_STACK_PROTECTOR)
    if(HAS_STACK_PROTECTOR)
        message(STATUS "[SECURE-CROSS] Stack protector: AVAILABLE")
    else()
        message(WARNING "[SECURE-CROSS] Stack protector: NOT AVAILABLE")
    endif()

    # FORTIFY_SOURCE
    check_c_compiler_flag("-D_FORTIFY_SOURCE=2" HAS_FORTIFY)
    if(HAS_FORTIFY)
        message(STATUS "[SECURE-CROSS] FORTIFY_SOURCE: AVAILABLE")
    else()
        message(WARNING "[SECURE-CROSS] FORTIFY_SOURCE: NOT AVAILABLE")
    endif()

    # PIE
    check_c_compiler_flag("-fPIE" HAS_PIE)
    if(HAS_PIE)
        message(STATUS "[SECURE-CROSS] PIE: AVAILABLE")
    else()
        message(WARNING "[SECURE-CROSS] PIE: NOT AVAILABLE")
    endif()

    # RELRO
    check_c_compiler_flag("-Wl,-z,relro" HAS_RELRO)
    if(HAS_RELRO)
        message(STATUS "[SECURE-CROSS] RELRO: AVAILABLE")
    else()
        message(WARNING "[SECURE-CROSS] RELRO: NOT AVAILABLE")
    endif()

    message(STATUS "[SECURE-CROSS] Security flags verification complete")
endfunction()

#[=[
Gerar informacoes do cross-build para auditoria.
#]=]
function(generate_cross_build_info)
    if(NOT CMAKE_CROSSCOMPILING)
        return()
    endif()

    set(BUILD_INFO "")
    string(APPEND BUILD_INFO "=== Cross-Build Information ===\n")
    string(APPEND BUILD_INFO "Timestamp: ${CMAKE_CURRENT_LIST_FILE}:${CMAKE_CURRENT_LIST_LINE}\n")
    string(APPEND BUILD_INFO "Host System: ${CMAKE_HOST_SYSTEM_NAME}/${CMAKE_HOST_SYSTEM_PROCESSOR}\n")
    string(APPEND BUILD_INFO "Target System: ${CMAKE_SYSTEM_NAME}/${CMAKE_SYSTEM_PROCESSOR}\n")
    string(APPEND BUILD_INFO "C Compiler: ${CMAKE_C_COMPILER}\n")
    string(APPEND BUILD_INFO "CXX Compiler: ${CMAKE_CXX_COMPILER}\n")
    string(APPEND BUILD_INFO "Sysroot: ${CMAKE_SYSROOT}\n")
    string(APPEND BUILD_INFO "Build Type: ${CMAKE_BUILD_TYPE}\n")
    string(APPEND BUILD_INFO "C Flags: ${CMAKE_C_FLAGS}\n")
    string(APPEND BUILD_INFO "CXX Flags: ${CMAKE_CXX_FLAGS}\n")
    string(APPEND BUILD_INFO "Linker Flags: ${CMAKE_EXE_LINKER_FLAGS}\n")
    string(APPEND BUILD_INFO "==============================\n")

    file(WRITE "${CMAKE_BINARY_DIR}/cross-build-info.txt" "${BUILD_INFO}")
    message(STATUS "[SECURE-CROSS] Cross-build info written to: ${CMAKE_BINARY_DIR}/cross-build-info.txt")
endfunction()

# ============================================================================
# MAIN FUNCTION
# ============================================================================

#[=[
Funcao principal de setup de cross-compilation segura.
Chamar no inicio do CMakeLists.txt.
#]=]
function(secure_cross_build_setup)
    if(NOT CMAKE_CROSSCOMPILING)
        message(STATUS "[SECURE-CROSS] Native compilation detected, skipping cross-build setup")
        return()
    endif()

    message(STATUS "[SECURE-CROSS] ==========================================")
    message(STATUS "[SECURE-CROSS] Secure Cross-Build Setup")
    message(STATUS "[SECURE-CROSS] ==========================================")

    verify_toolchain()
    verify_sysroot()
    verify_security_flags()
    generate_cross_build_info()

    message(STATUS "[SECURE-CROSS] ==========================================")
    message(STATUS "[SECURE-CROSS] Setup complete")
    message(STATUS "[SECURE-CROSS] ==========================================")
endfunction()
```

### 13.5 CMakeLists.txt Principal

```cmake
# CMakeLists.txt
# Projeto de exemplo para cross-compilation segura

cmake_minimum_required(VERSION 3.20)

project(SecureARMProject
    VERSION 1.0.0
    DESCRIPTION "Secure ARM cross-compilation example"
    LANGUAGES C CXX
)

# ============================================================================
# SECURITY SETUP
# ============================================================================

# Incluir modulo de verificacao
list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
include(SecureCrossBuild)

# Executar verificacoes de seguranca
secure_cross_build_setup()

# ============================================================================
# BUILD OPTIONS
# ============================================================================

option(BUILD_SHARED_LIBS "Build shared libraries" OFF)
option(BUILD_TESTING "Build tests" ON)
option(ENABLE_HARDENING "Enable security hardening" ON)
option(ENABLE_PIE "Enable Position Independent Executable" ON)
option(ENABLE_FORTIFY "Enable FORTIFY_SOURCE" ON)

# ============================================================================
# SECURITY HARDENING
# ============================================================================

if(ENABLE_HARDENING)
    include(SecurityFlags)
    apply_security_hardening()
endif()

# ============================================================================
# PROJECT CONFIGURATION
# ============================================================================

# Configurar padroes de C++
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Exportar compile commands para analise
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# FIND PACKAGES
# ============================================================================

# OpenSSL (via sysroot)
find_package(OpenSSL QUIET)
if(OPENSSL_FOUND)
    message(STATUS "OpenSSL found: ${OPENSSL_VERSION}")
else()
    message(STATUS "OpenSSL not found, building without crypto support")
endif()

# Threads
find_package(Threads REQUIRED)

# ============================================================================
# SUBDIRECTORIES
# ============================================================================

add_subdirectory(src)

if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# ============================================================================
# INSTALL CONFIGURATION
# ============================================================================

# Instalar headers
install(DIRECTORY src/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h" PATTERN "*.hpp"
)

# Instalar binarios
install(TARGETS secure_app
    RUNTIME DESTINATION bin
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

# Instalar informacoes de cross-build
install(FILES "${CMAKE_BINARY_DIR}/cross-build-info.txt"
    DESTINATION share/${PROJECT_NAME}
)
```

### 13.6 Modulos de Seguranca

```cmake
# cmake/SecurityFlags.cmake
# Flags de seguranca para cross-compilation

#[=[
Apply security hardening flags to all targets.
#]=]
function(apply_security_hardening)
    message(STATUS "[SECURITY] Applying hardening flags...")

    # Flags comuns para todos os compiladores
    set(COMMON_FLAGS "")

    # Stack protector
    include(CheckCCompilerFlag)
    check_c_compiler_flag("-fstack-protector-strong" HAS_STACK_PROTECTOR)
    if(HAS_STACK_PROTECTOR)
        list(APPEND COMMON_FLAGS "-fstack-protector-strong")
    endif()

    # Format security
    check_c_compiler_flag("-Wformat -Wformat-security" HAS_FORMAT_SECURITY)
    if(HAS_FORMAT_SECURITY)
        list(APPEND COMMON_FLAGS "-Wformat" "-Wformat-security")
    endif()

    # FORTIFY_SOURCE
    if(ENABLE_FORTIFY)
        check_c_compiler_flag("-D_FORTIFY_SOURCE=2" HAS_FORTIFY)
        if(HAS_FORTIFY)
            list(APPEND COMMON_FLAGS "-D_FORTIFY_SOURCE=2")
        endif()
    endif()

    # PIE
    if(ENABLE_PIE)
        check_c_compiler_flag("-fPIE" HAS_PIE)
        if(HAS_PIE)
            list(APPEND COMMON_FLAGS "-fPIE")
        endif()
    endif()

    # Converter para string
    string(REPLACE ";" " " COMMON_FLAGS_STR "${COMMON_FLAGS}")

    # Aplicar flags
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${COMMON_FLAGS_STR}" PARENT_SCOPE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${COMMON_FLAGS_STR}" PARENT_SCOPE)

    # Linker flags
    set(LINKER_FLAGS "")

    # PIE (linker)
    if(ENABLE_PIE)
        check_c_compiler_flag("-pie" HAS_PIE_LINK)
        if(HAS_PIE_LINK)
            list(APPEND LINKER_FLAGS "-pie")
        endif()
    endif()

    # RELRO
    check_c_compiler_flag("-Wl,-z,relro" HAS_RELRO)
    if(HAS_RELRO)
        list(APPEND LINKER_FLAGS "-Wl,-z,relro")
    endif()

    # NOW
    check_c_compiler_flag("-Wl,-z,now" HAS_NOW)
    if(HAS_NOW)
        list(APPEND LINKER_FLAGS "-Wl,-z,now")
    endif()

    # No-execute stack
    check_c_compiler_flag("-Wl,-z,noexecstack" HAS_NOEXECSTACK)
    if(HAS_NOEXECSTACK)
        list(APPEND LINKER_FLAGS "-Wl,-z,noexecstack")
    endif()

    string(REPLACE ";" " " LINKER_FLAGS_STR "${LINKER_FLAGS}")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${LINKER_FLAGS_STR}" PARENT_SCOPE)

    message(STATUS "[SECURITY] Hardening flags applied")
endfunction()

#[=[
Verificar se o binario final tem as flags de seguranca.
#]=]
function(verify_binary_security BINARY)
    if(NOT EXISTS "${BINARY}")
        message(WARNING "[SECURITY] Binary not found: ${BINARY}")
        return()
    endif()

    message(STATUS "[SECURITY] Verifying binary security: ${BINARY}")

    # Verificar com checksec (se disponivel)
    find_program(CHECKSEC checksec)
    if(CHECKSEC)
        execute_process(
            COMMAND ${CHECKSEC} --file=${BINARY}
            OUTPUT_VARIABLE CHECKSEC_OUTPUT
            ERROR_QUIET
        )
        message(STATUS "[SECURITY] checksec output:\n${CHECKSEC_OUTPUT}")
    endif()

    # Verificar com readelf
    find_program(READELF readelf)
    if(READELF)
        # Verificar RELRO
        execute_process(
            COMMAND ${READELF} -l "${BINARY}"
            OUTPUT_VARIABLE READ_ELF_OUTPUT
            ERROR_QUIET
        )

        string(FIND "${READ_ELF_OUTPUT}" "GNU_RELRO" HAS_RELRO)
        if(HAS_RELRO)
            message(STATUS "[SECURITY] RELRO: ENABLED")
        else()
            message(WARNING "[SECURITY] RELRO: NOT FOUND")
        endif()

        string(FIND "${READ_ELF_OUTPUT}" "GNU_STACK" HAS_STACK)
        if(HAS_STACK)
            string(FIND "${READ_ELF_OUTPUT}" "RWE" STACK_RWX)
            if(STACK_RWX)
                message(WARNING "[SECURITY] Stack is RWE (no NX)")
            else()
                message(STATUS "[SECURITY] Stack NX: ENABLED")
            endif()
        endif()
    endif()
endfunction()
```

### 13.7 Script de Build Multi-Arch

```bash
#!/bin/bash
# scripts/build-all-archs.sh
# Build para todas as arquiteturas suportadas

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
BUILD_BASE="${PROJECT_DIR}/build"
INSTALL_BASE="${PROJECT_DIR}/install"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se as toolchains estao instaladas
check_toolchain() {
    local toolchain=$1
    if ! command -v "${toolchain}" &> /dev/null; then
        log_error "Toolchain not found: ${toolchain}"
        log_error "Install with: sudo apt-get install gcc-aarch64-linux-gnu"
        return 1
    fi
    return 0
}

# Build para uma arquitetura
build_arch() {
    local arch=$1
    local toolchain=$2
    local description=$3

    log_info "Building for ${description}..."

    # Verificar toolchain
    if ! check_toolchain "${toolchain}"; then
        return 1
    fi

    local build_dir="${BUILD_BASE}/${arch}"
    local install_dir="${INSTALL_BASE}/${arch}"

    # Configurar
    cmake -S "${PROJECT_DIR}" \
        -B "${build_dir}" \
        -DCMAKE_TOOLCHAIN_FILE="${PROJECT_DIR}/cmake/toolchains/${toolchain}.cmake" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${install_dir}" \
        -DBUILD_TESTING=OFF

    # Build
    cmake --build "${build_dir}" --config Release -j$(nproc)

    # Install
    cmake --install "${build_dir}" --config Release

    # Verificar binario
    local binary="${build_dir}/src/secure_app"
    if [[ -f "${binary}" ]]; then
        log_info "Binary: ${binary}"
        file "${binary}"
    fi

    log_info "Build complete for ${description}"
}

# Build para todas as arquiteturas
main() {
    log_info "Starting multi-architecture build..."

    # Verificar diretorios
    mkdir -p "${BUILD_BASE}"
    mkdir -p "${INSTALL_BASE}"

    # Build para cada arquitetura
    build_arch "arm64" "aarch64-linux-gnu-gcc" "ARM64 Linux"
    build_arch "arm32" "arm-linux-gnueabihf-gcc" "ARM32 Linux"
    build_arch "x86_64" "gcc" "x86_64 Linux"

    # Resumo
    log_info "=========================================="
    log_info "Multi-architecture build complete!"
    log_info "=========================================="
    log_info "Install directories:"
    ls -la "${INSTALL_BASE}"

    # Verificar binarios
    log_info "Binaries:"
    for arch_dir in "${INSTALL_BASE}"/*/; do
        if [[ -d "${arch_dir}/bin" ]]; then
            echo "  ${arch_dir}:"
            ls -la "${arch_dir}/bin/"
        fi
    done
}

main "$@"
```

### 13.8 Script de Verificacao

```bash
#!/bin/bash
# scripts/verify-binaries.sh
# Verificar seguranca dos binarios gerados

set -euo pipefail

INSTALL_BASE="${1:-./install}"

echo "=========================================="
echo "Binary Security Verification"
echo "=========================================="

# Verificar cada binario
for binary in $(find "${INSTALL_BASE}" -type f -executable); do
    echo ""
    echo "Checking: ${binary}"
    echo "------------------------------------------"

    # Verificar formato
    echo "Format:"
    file "${binary}"
    echo ""

    # Verificar arquitetura
    echo "Architecture:"
    readelf -h "${binary}" 2>/dev/null | grep -E "Machine|Class" || echo "  Not an ELF binary"
    echo ""

    # Verificar seguranca
    echo "Security features:"

    # RELRO
    if readelf -l "${binary}" 2>/dev/null | grep -q "GNU_RELRO"; then
        echo "  RELRO: ENABLED"
    else
        echo "  RELRO: MISSING"
    fi

    # NX
    if readelf -l "${binary}" 2>/dev/null | grep -q "GNU_STACK"; then
        stack_flags=$(readelf -l "${binary}" 2>/dev/null | grep "GNU_STACK" | awk '{print $NF}')
        if echo "${stack_flags}" | grep -q "E"; then
            echo "  NX (non-executable stack): MISSING"
        else
            echo "  NX (non-executable stack): ENABLED"
        fi
    fi

    # PIE
    if readelf -h "${binary}" 2>/dev/null | grep -q "DYN"; then
        echo "  PIE: ENABLED"
    else
        echo "  PIE: MISSING"
    fi

    # Stack canary
    if readelf -s "${binary}" 2>/dev/null | grep -q "__stack_chk_fail"; then
        echo "  Stack canary: ENABLED"
    else
        echo "  Stack canary: MISSING"
    fi

    # FORTIFY
    if readelf -s "${binary}" 2>/dev/null | grep -q "__*_chk@"; then
        echo "  FORTIFY: ENABLED"
    else
        echo "  FORTIFY: MISSING"
    fi

    # Debug symbols
    if readelf -S "${binary}" 2>/dev/null | grep -q ".debug"; then
        echo "  Debug symbols: PRESENT (should strip for production)"
    else
        echo "  Debug symbols: ABSENT (good for production)"
    fi

    # Size
    echo ""
    echo "Size:"
    size "${binary}" 2>/dev/null || echo "  Unable to determine size"
done

echo ""
echo "=========================================="
echo "Verification complete"
echo "=========================================="
```

---

## 14. Exercicios

### Exercicio 1: Toolchain File para RISC-V

**Objetivo:** Criar um toolchain file para cross-compilation de RISC-V 64-bit.

**Tarefa:** Crie um arquivo `cmake/toolchains/riscv64-linux-gnu.cmake` que:

1. Configure `CMAKE_SYSTEM_NAME` e `CMAKE_SYSTEM_PROCESSOR` corretamente
2. Configure todos os compiladores e utilitarios
3. Configure o sysroot
4. Configure `CMAKE_FIND_ROOT_PATH_MODE_*` corretamente
5. Inclua flags de seguranca minimas

**Solucao esperada:**

```cmake
# cmake/toolchains/riscv64-linux-gnu.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

set(CMAKE_C_COMPILER riscv64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER riscv64-linux-gnu-g++)
set(CMAKE_AR riscv64-linux-gnu-ar)
set(CMAKE_RANLIB riscv64-linux-gnu-ranlib)
set(CMAKE_STRIP riscv64-linux-gnu-strip)
set(CMAKE_OBJCOPY riscv64-linux-gnu-objcopy)

set(CMAKE_SYSROOT /opt/riscv64-linux-gnu/sysroot)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

set(CMAKE_C_FLAGS_INIT "-march=rv64gc -mabi=lp64d")
set(CMAKE_CXX_FLAGS_INIT "-march=rv64gc -mabi=lp64d")
```

### Exercicio 2: Verificacao de Toolchain

**Objetivo:** Implementar verificacao de toolchain para cross-compilation.

**Tarefa:** Crie um modulo CMake que:

1. Verifique se o compilador cross existe e funciona
2. Verifique se a versao e recente o suficiente
3. Verifique se o sysroot existe e tem a estrutura correta
4. Gere um relatorio de verificacao

**Criterios de avaliacao:**
- O modulo deve usar `execute_process` para verificar o compilador
- Deve verificar versao minima (GCC >= 12 ou Clang >= 16)
- Deve verificar estrutura do sysroot (diretorios e headers)
- Deve gerar um arquivo de relatorio

### Exercicio 3: CMake Presets Multi-Arch

**Objetivo:** Criar presets para 3 arquiteturas diferentes.

**Tarefa:** Crie um arquivo `CMakePresets.json` que:

1. Defina um preset base com configuracoes de seguranca
2. Crie presets herdados para ARM64, ARM32 e x86_64
3. Inclua build presets para cada arquitetura
4. Inclua um test preset

**Criterios de avaliacao:**
- Presets devem herdar de um base comum
- Cada preset deve apontar para o toolchain correto
- Build presets devem especificar configuracao Release
- Test presets devem ser configurados para cross-compilation

### Exercicio 4: Integracao vcpkg com Cross-Compilation

**Objetivo:** Configurar vcpkg para funcionar com cross-compilation.

**Tarefa:**

1. Crie um triplet customizado para ARM64 Linux
2. Configure o CMakeLists.txt para usar vcpkg com o triplet
3. Inclua verificacao de hash para os packages baixados
4. Documente como auditar as dependencias

**Criterios de avaliacao:**
- Triplet deve definir arquitetura, linkage e flags
- CMakeLists.txt deve detectar vcpkg automaticamente
- Packages devem ser verificados via hash
- Deve haver documentacao do processo de auditoria

### Exercicio 5: Build Reproduzivel Cross-Compilation

**Objetivo:** Implementar build reproduzivel para cross-compilation.

**Tarefa:**

1. Configure o projeto para builds reproduziveis
2. Documente todas as dependencias (toolchain, sysroot, packages)
3. Crie script que recria o ambiente de build
4. Implemente verificacao de reproduceibilidade

**Criterios de avaliacao:**
- Build deve ser identico em dois ambientes limpos
- Todas as versoes devem ser fixadas
- Script deve funcionar em container Docker
- Verificacao deve comparar hashes dos binarios

### Exercicio 6: Seguranca em Cross-Compilation CI/CD

**Objetivo:** Implementar pipeline CI/CD para cross-compilation segura.

**Tarefa:** Crie um pipeline (GitHub Actions ou GitLab CI) que:

1. Instale as toolchains cross
2. Execute verificacoes de seguranca
3. Compile para multiplos targets
4. Verifique os binarios gerados
5. Gere SBOM para cada target
6. Assine os binarios

**Criterios de avaliacao:**
- Pipeline deve ser executavel em ambiente limpo
- Toolchains devem ser verificadas via hash
- Binarios devem ser verificados apos compilacao
- SBOM deve ser gerado para cada target
- Binarios devem ser assinados com cosign ou similar

### Exercicio 7: Cross-Compilation com Sanitizers

**Objetivo:** Habilitar sanitizers em cross-compilation.

**Tarefa:**

1. Modifique o toolchain file para suportar sanitizers
2. Implemente deteccao de suporte a sanitizers no compilador cross
3. Crie preset para debug com sanitizers
4. Implemente execucao de testes com sanitizers via QEMU

**Criterios de avaliacao:**
- Toolchain deve detectar suporte a ASan, UBSan, TSan
- Preset de debug deve habilitar sanitizers
- Testes devem ser executaveis via QEMU
- Relatorio deve incluir resultado dos sanitizers

---

## 15. Referencias

### 15.1 Documentacao Oficial

- **CMake Documentation**: https://cmake.org/cmake/help/latest/
  - [Cross Compiling](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html)
  - [CMAKE_SYSTEM_NAME](https://cmake.org/cmake/latest/variable/CMAKE_SYSTEM_NAME.html)
  - [CMAKE_SYSROOT](https://cmake.org/cmake/latest/variable/CMAKE_SYSROOT.html)
  - [find_package](https://cmake.org/cmake/latest/command/find_package.html)
  - [CMake Presets](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html)

- **GNU ARM Embedded Toolchain**: https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm
- **aarch64-linux-gnu Toolchain**: https://linaro-toolchain.org/
- **RISC-V GNU Toolchain**: https://github.com/riscv-collab/riscv-gnu-toolchain

### 15.2 Seguranca

- **CWE-506**: Embedded Malicious Code
- **CWE-494**: Download of Code Without Integrity Check
- **CWE-829**: Inclusion of Functionality from Untrusted Control Sphere
- **NIST SP 800-161**: Supply Chain Risk Management
- **SLSA Framework**: https://slsa.dev/
- **Sigstore**: https://www.sigstore.dev/
- **in-toto**: https://in-toto.io/

### 15.3 CVEs Relacionadas

- **CVE-2024-3094**: XZ Utils backdoor (supply chain attack via build system)
- **CVE-2023-38408**: OpenSSH agent forwarding RCE (afeta builds com SSH)
- **CVE-2022-24765**: Git directory traversal (afeta submodules em cross-builds)
- **CVE-2021-22893**: Pulse Secure VPN zero-day (afeta VPN clients cross-compilados)

### 15.4 Ferramentas

- **QEMU**: Emulador para testes de cross-compilation
- **checksec**: Verificacao de seguranca de binarios ELF
- **readelf**: Analise de binarios ELF
- **objdump**: Desassemblagem e analise de binarios
- **crosstool-ng**: Gerador de toolchains cross
- **Buildroot**: Sistema de build para embedded Linux
- **Yocto Project**: Framework para embedded Linux

### 15.5 Artigos e Livros

- "Cross-Compilation with CMake" - Kitware Blog
- "Embedded Linux Development with Yocto Project" - Puja Supriya Das
- "Mastering Embedded Linux Programming" - Chris Simmonds
- "Building Embedded Linux Systems" - Karim Yaghmour
- "Secure Coding in C and C++" - Robert C. Seacord

### 15.6 Repositorios de Referencia

- **Zephyr RTOS**: https://github.com/zephyrproject-rtos/zephyr (exemplo de cross-compilation complexa)
- **Buildroot**: https://github.com/buildroot/buildroot (sistema de build completo)
- **ESP-IDF**: https://github.com/espressif/esp-idf (toolchain para ESP32)
- **Android NDK**: https://github.com/android/ndk (cross-compilation para Android)

---

## Resumo

Neste capitulo, exploramos os fundamentos e boas praticas de cross-compilation com foco em seguranca. Os topicos principais incluem:

1. **Conceitos basicos**: host vs target, por que cross-compile
2. **Toolchain files**: estrutura, configuracao, verificacao
3. **System name e processor**: configuracao correta para cada target
4. **Sysroot**: configuracao, verificacao de integridade
5. **Compiladores cross**: GCC, Clang, arm-none-eabi, aarch64-linux-gnu
6. **Target triplet**: conceito e uso no vcpkg
7. **Find package**: configuracao para cross-compilation
8. **vcpkg triplets**: integracao com gerenciador de pacotes
9. **Verificacao de toolchain**: hash, versao, integridade
10. **Multi-architecture**: build para multiplos targets
11. **CMake presets**: configuracao declarativa
12. **Exemplo completo**: ARM cross-compilation seguro

### Pontos-Chave

- Cross-compilation amplifica a superficie de ataque do build system
- A toolchain e o pilar de confianca — sempre verifique hash e versao
- `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY` deve ser `ONLY` em cross-compilation
- Sysroot deve ser verificado antes de cada build
- CMake presets simplificam a gestao de multiplos targets
- Binarios gerados devem ser verificados apos compilacao
- Builds reproduziveis sao mais dificeis em cross-compilation, mas essenciais

### Proximo Capitulo

No proximo capitulo, veremos como configurar testes em CMake (CTest, GoogleTest, fuzzing) e como testar binarios cross-compilados via QEMU.

---

*[Capitulo 12 — SBOM e Supply Chain Security](12-sbom-supply-chain.md) | [Proximo capitulo: 14 — Testing no CMake](14-testing-cmake.md)*
---

*[Capítulo anterior: 12 — Sbom Supply Chain](12-sbom-supply-chain.md)*
*[Próximo capítulo: 14 — Testing Cmake](14-testing-cmake.md)*
