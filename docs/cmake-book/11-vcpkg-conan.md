---
layout: default
title: "vcpkg e Conan"
---

# Capitulo 11 — vcpkg e Conan

> *"Gerenciar dependencias e gerenciar riscos. Um pacote nao verificado e uma caixa-preta que pode explodir a qualquer momento."*

---

## Sumario

1. Objetivos de Aprendizado
2. vcpkg: instalacao, vcpkg.json, triplet system
3. Conan 2.x: conanfile.txt, conanfile.py
4. Comparacao: vcpkg vs Conan vs system packages
5. Security features: hash verification, signing
6. Lock files: vcpkg-lock.json, conan.lock
7. Binary caching: vcpkg binary caching, Conan cache
8. Private registries: vcpkg config, Conan remote
9. Audit: vcpkg audit, conan audit
10. Integration with CMake: find_package after install
11. Supply chain security: pinning, reproducibility
12. Exemplo: projeto com vcpkg + Conan
13. Exercicios
14. Referencias

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

- Instalar e configurar vcpkg e Conan 2.x para projetos CMake
- Especificar dependencias com vcpkg.json e conanfile.py/txt
- Compreender o triplet system do vcpkg e como ele afeta builds cross-platform
- Configurar features, opcoes e perfil de compilacao em ambos os gerenciadores
- Implementar verificacao de integridade via hash e assinatura digital
- Usar lock files para builds reproduziveis
- Configurar binary caching para acelerar builds sem comprometer seguranca
- Configurar registros privados (private registries) para dependencias proprietarias
- Auditar dependencias para vulnerabilidades conhecidas
- Integrar vcpkg/Conan com CMake via find_package
- Implementar pinning estrito para supply chain security
- Comparar trade-offs entre vcpkg, Conan e system packages

---

## 2. vcpkg: instalacao, vcpkg.json, triplet system

### 2.1 O que e vcpkg

vcpkg e um gerenciador de pacotes C/C++ desenvolvido e mantido pela Microsoft. Ele se integra nativamente com CMake e suporta mais de 2000 bibliotecas. A diferencial do vcpkg e o modelo de manifest: voce declara dependencias em um arquivo JSON versionado no repositorio, garantindo que todos os membros da equipe usem as mesmas versoes.

Diferentemente de gerenciadores de pacotes do sistema operacional (apt, yum, brew), vcpkg compila as bibliotecas do codigo-fonte, garantindo que o build seja consistente em todas as plataformas.

O vcpkg se destaca por:

- Compilacao a partir do codigo-fonte com configuracoes padrao testadas
- Integracao nativa com CMake via CMAKE_TOOLCHAIN_FILE
- Suporte a multiplas plataformas com o mesmo modelo de configuracao
- Compatibilidade com presets do CMake para configuracoes reproduziveis
- Registro publico de ports com revisao comunitaria

### 2.2 Instalacao do vcpkg

Existem duas formas principais de instalar vcpkg: a instalacao global e a instalacao por projeto (modo manifest). A instalacao por projeto e a recomendada para equipes, pois mantem as dependencias isoladas por repositorio.

#### Instalacao Global (User-Local)

```bash
# Clonar o repositorio do vcpkg
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg

# Executar o bootstrap (compila o proprio vcpkg)
./bootstrap-vcpkg.sh

# Ou no Windows:
# .\bootstrap-vcpkg.bat

# Instalar uma biblioteca globalmente
./vcpkg install nlohmann-json
./vcpkg install fmt
./vcpkg install openssl
```

A instalacao global coloca as bibliotecas em `vcpkg_installed/` dentro do diretorio do vcpkg. Isso e conveniente para experimentacao, mas problematico para equipes porque:

1. Cada desenvolvedor pode ter versoes diferentes instaladas
2. Nao ha registro no repositorio do que esta instalado
3. Builds nao sao reproduziveis entre maquinas
4. Conflitos entre versoes de bibliotecas sao dificeis de rastrear

#### Instalacao por Projeto (Modo Manifest)

O modo manifest e a abordagem recomendada. Neste modo, vcpkg e ativado via CMake e as dependencias sao especificadas em um arquivo `vcpkg.json` na raiz do projeto.

```bash
# Na raiz do projeto, criar o arquivo vcpkg.json
# (detalhado na secao 2.3)

# Ativar vcpkg no CMake (integracao automatica)
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=/path/to/vcpkg/scripts/buildsystems/vcpkg.cmake

# Ou usar vcpkg preset (recomendado)
cmake --preset default
```

#### Instalacao via Bootstrap do Projeto

Uma abordagem comum e incluir o repositorio do vcpkg como um submodule Git:

```bash
# Adicionar vcpkg como submodule
git submodule add https://github.com/microsoft/vcpkg.git vcpkg

# Inicializar e atualizar o submodule
git submodule update --init --recursive

# O bootstrap e feito automaticamente pelo CMake
```

Quando o vcpkg e ativado via CMAKE_TOOLCHAIN_FILE, ele executa o bootstrap automaticamente na primeira configuracao. Isso simplifica a experiencia do desenvolvedor, mas significa que a compilacao inicial leva mais tempo.

#### VCPKG_ROOT

A variavel de ambiente `VCPKG_ROOT` define onde o vcpkg esta instalado:

```bash
# Definir VCPKG_ROOT
export VCPKG_ROOT=/path/to/vcpkg

# Agora o CMake pode encontrar o vcpkg automaticamente
cmake -B build -S .
```

Em CI/CD, defina `VCPKG_ROOT` como variavel de ambiente do runner:

```yaml
# GitHub Actions
env:
  VCPKG_ROOT: ${{ github.workspace }}/vcpkg
```

### 2.3 vcpkg.json — O Manifesto

O arquivo `vcpkg.json` e o coracao da configuracao do vcpkg no modo manifest. Ele define todas as dependencias do projeto, suas versoes e opcoes de compilacao.

#### Estrutura Basica

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg.schema.json",
  "name": "meu-projeto",
  "version-string": "1.0.0",
  "description": "Projeto de exemplo com vcpkg",
  "license": "MIT",
  "supports": "linux | osx | windows",
  "dependencies": [
    "nlohmann-json",
    "fmt",
    {
      "name": "openssl",
      "version>=": "3.1.0"
    }
  ]
}
```

#### Campos do vcpkg.json

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `$schema` | string | URL do schema para validacao no editor |
| `name` | string | Nome do projeto |
| `version-string` | string | Versao do projeto (para registry proprio) |
| `version` | string | Versao em formato semver |
| `version-date` | string | Versao no formato YYYY-MM-DD |
| `description` | string ou array | Descricao do projeto |
| `license` | string | SPDX do license |
| `supports` | string | Expressao de suporte a plataforma |
| `dependencies` | array | Lista de dependencias |
| `overrides` | array | Override de versoes especificas |
| `registries` | array | Registros adicionais de pacotes |

#### Dependencias com Versao

```json
{
  "dependencies": [
    "nlohmann-json",
    {
      "name": "openssl",
      "version>=": "3.1.0"
    },
    {
      "name": "boost",
      "version>=": "1.82.0",
      "features": ["fiber", "json"]
    }
  ]
}
```

O campo `version>=` estabelece um minimo, mas o vcpkg resolve a versao real com base no registro. Para controle estrito, use o lock file (secao 6).

#### Features

Muitas bibliotecas oferecem componentes ou features opcionais. O vcpkg permite habilitar features especificas:

```json
{
  "dependencies": [
    {
      "name": "boost",
      "features": ["fiber", "json", "system"]
    },
    {
      "name": "curl",
      "features": ["ssl", "http2"]
    },
    {
      "name": "qt-base",
      "features": ["openssl", "dbus"]
    }
  ]
}
```

Cada feature pode ativar dependencias adicionais e opcoes de compilacao. O vcpkg resolve a arvore de dependencias automaticamente.

Para descobrir quais features uma biblioteca oferece:

```bash
# Listar features disponiveis para uma port
vcpkg search openssl

# Ou consultar o portfile.cmake
cat vcpkg/ports/openssl/vcpkg.json
```

#### Overrides

Para forcar uma versao especifica (necessario em alguns casos de seguranca):

```json
{
  "dependencies": [
    {
      "name": "openssl",
      "version>=": "3.1.0"
    }
  ],
  "overrides": [
    {
      "name": "openssl",
      "version": "3.1.4"
    }
  ]
}
```

Overrides bypassam a resolucao normal de versao. Use apenas quando necessario, pois podem causar incompatibilidades com outras dependencias que esperam versoes diferentes.

#### Registries

```json
{
  "registries": [
    {
      "kind": "git",
      "repository": "https://github.com/meu-org/vcpkg-registry",
      "baseline": "a1b2c3d4e5f6789012345678901234567890abcd"
    }
  ],
  "dependencies": [
    {
      "name": "minha-bib",
      "version>=": "2.0.0"
    }
  ]
}
```

Registries permitem adicionar repositorios de pacotes adicionais alem do vcpkg-ports oficial. O campo `baseline` e um commit hash que define a versao exata do registro a ser usada.

#### default-registry

Para definir o registro padrao (que contem a maioria das bibliotecas):

```json
{
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "registries": [
    {
      "kind": "git",
      "repository": "https://github.com/meu-org/vcpkg-registry",
      "baseline": "a1b2c3d4e5f6789012345678901234567890abcd",
      "packages": ["minha-bib", "outra-bib"]
    }
  ],
  "dependencies": [
    "nlohmann-json",
    "minha-bib"
  ]
}
```

O campo `packages` no registro adicional limita quais pacotes aquele registro fornece. Pacotes nao listados sao resolvidos pelo registro padrao.

### 2.4 Triplets

Triplets sao o mecanismo do vcpkg para definir como compilar bibliotecas. Um triplet e composto por tres partes:

```
{arquitetura}-{sistema}-{linkage}
```

Por exemplo:
- `x64-linux` — 64-bit, Linux, shared libraries
- `x64-linux-static` — 64-bit, Linux, static libraries
- `x64-windows-static-md` — 64-bit, Windows, static libs, MD runtime
- `arm64-osx` — ARM64, macOS, shared libraries

#### Triplets Padrao

O vcpkg inclui triplets padrao para todas as combinacoes de plataforma suportadas:

```bash
# Listar triplets disponiveis
./vcpkg triplet list

# Listar pacotes instalados para um triplet
./vcpkg list --triplet x64-linux
```

Triplets padrao definem:
- Compilador e flags de compilacao
- Tipo de linkage (shared/static)
- Target OS e arquitetura
- Variaveis de ambiente especificas da plataforma

#### Estrutura de um Triplet

Um arquivo de triplet e na verdade um arquivo CMake que define variaveis:

```cmake
# Exemplo: x64-linux.cmake
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)

set(VCPKG_C_FLAGS "")
set(VCPKG_CXX_FLAGS "")
```

| Variavel | Opcoes | Descricao |
|----------|--------|-----------|
| `VCPKG_TARGET_ARCHITECTURE` | x86, x64, arm, arm64, s390x | Arquitetura alvo |
| `VCPKG_CRT_LINKAGE` | static, dynamic | Linkage da C runtime |
| `VCPKG_LIBRARY_LINKAGE` | static, shared | Linkage das bibliotecas |
| `VCPKG_C_FLAGS` | string | Flags adicionais para C |
| `VCPKG_CXX_FLAGS` | string | Flags adicionais para C++ |

#### Custom Triplets

Para necessidades especificas, crie triplets customizados:

```cmake
# vcpkg/triplets/community/x64-linux-secure.cmake
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE static)
set(VCPKG_LIBRARY_LINKAGE static)

set(VCPKG_C_FLAGS "-fstack-protector-strong -D_FORTIFY_SOURCE=2")
set(VCPKG_CXX_FLAGS "-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE")

set(VCPKG_CMAKE_CONFIGURE_OPTIONS
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
  -DCMAKE_BUILD_TYPE=Release
)
```

Para usar o triplet customizado:

```bash
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=/path/to/vcpkg/scripts/buildsystems/vcpkg.cmake \
  -DVCPKG_TARGET_TRIPLET=x64-linux-secure
```

#### Seguranca via Triplets

Triplets sao uma forma poderosa de impor padroes de seguranca em todas as dependencias:

```cmake
# vcpkg/triplets/x64-linux-hardened.cmake
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE static)
set(VCPKG_LIBRARY_LINKAGE static)

# Flags de hardening para todas as dependencias
set(VCPKG_C_FLAGS
  "-fstack-protector-strong \
   -D_FORTIFY_SOURCE=2 \
   -fPIE \
   -Wformat -Wformat-security"
)
set(VCPKG_CXX_FLAGS
  "-fstack-protector-strong \
   -D_FORTIFY_SOURCE=2 \
   -fPIE \
   -Wformat -Wformat-security \
   -fno-exceptions"
)

# Usar LTO para reduzir superficie de ataque
set(VCPKG_C_FLAGS "${VCPKG_C_FLAGS} -flto=auto")
set(VCPKG_CXX_FLAGS "${VCPKG_CXX_FLAGS} -flto=auto")
```

Isso garante que TODAS as bibliotecas compiladas via vcpkg recebam as mesmas flags de hardening, independentemente de como o projeto principal esteja configurado.

#### Comparacao de Triplets Seguros vs Padrao

| Aspecto | Triplet Padrao | Triplet Hardened |
|---------|---------------|------------------|
| Stack protector | Depende do compilador | Sempre ativo |
| FORTIFY_SOURCE | Nao definido | Nivel 2 |
| PIE/PIC | Nao garantido | Sempre ativo |
| Format security | Nao verificado | Werror + Wformat |
| LTO | Nao ativo | Ativado |
| Static linking | Variavel | Static (recomendado) |

#### Overlay Triplets

Para nao modificar o repositorio do vcpkg, voce pode usar overlay triplets:

```bash
cmake -B build -S . \
  -DVCPKG_OVERLAY_TRIPLETS=./cmake/triplets
```

Coloque seus triplets customizados em `./cmake/triplets/` e o vcpkg os usara antes dos triplets padrao.

#### vcpkg-configuration.json

Este arquivo (nao confundir com vcpkg.json) configura comportamentos do proprio vcpkg:

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg-configuration.schema.json",
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "registries": [
    {
      "kind": "git",
      "repository": "https://github.com/meu-org/vcpkg-registry",
      "baseline": "a1b2c3d4e5f6789012345678901234567890abcd",
      "packages": ["minha-bib"]
    }
  ]
}
```

### 2.5 vcpkg Presets

Presets do CMake podem ser estendidos para incluir vcpkg:

```json
{
  "version": 6,
  "configurePresets": [
    {
      "name": "vcpkg",
      "hidden": true,
      "toolchainFile": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake",
      "cacheVariables": {
        "CMAKE_TOOLCHAIN_FILE": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
      }
    },
    {
      "name": "default",
      "displayName": "Default Config",
      "inherits": "vcpkg",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/${presetName}",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "VCPKG_TARGET_TRIPLET": "x64-linux"
      }
    },
    {
      "name": "secure",
      "displayName": "Secure Config",
      "inherits": "vcpkg",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/${presetName}",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "VCPKG_TARGET_TRIPLET": "x64-linux-hardened"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "default",
      "configurePreset": "default"
    },
    {
      "name": "secure",
      "configurePreset": "secure"
    }
  ]
}
```

Uso:

```bash
# Configurar com preset padrao
cmake --preset default

# Configurar com preset seguro
cmake --preset secure

# Build
cmake --build --preset default
```

### 2.6 Exemplo Completo vcp.json

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg.schema.json",
  "name": "seguranca-app",
  "version-string": "1.0.0",
  "description": "Aplicacao com gerenciamento seguro de dependencias",
  "license": "Apache-2.0",
  "supports": "linux | osx",
  "dependencies": [
    {
      "name": "openssl",
      "version>=": "3.1.0",
      "features": ["tools"]
    },
    "nlohmann-json",
    {
      "name": "fmt",
      "version>=": "10.0.0"
    },
    {
      "name": "spdlog",
      "version>=": "1.12.0",
      "features": ["fmt"]
    },
    {
      "name": "catch2",
      "version>=": "3.4.0"
    },
    {
      "name": "benchmark",
      "version>=": "1.8.0"
    }
  ],
  "overrides": [
    {
      "name": "openssl",
      "version": "3.1.4"
    }
  ]
}
```

---

## 3. Conan 2.x: conanfile.txt, conanfile.py

### 3.1 O que e Conan

Conan e um gerenciador de pacotes C/C++ descentralizado, desenvolvido pela JFrog. Diferentemente do vcpkg, Conan suporta multiplos sistemas de build (CMake, Meson, Autotools, MSBuild) e oferece um modelo mais flexivel de perfil e configuracao.

Conan 2.x representou uma reescrita significativa, simplificando a API e melhorando a performance. As principais diferencas em relacao ao 1.x incluem:

- Novo modelo de recipes (conanfile.py simplificado)
- Sistema de confiabilidade (trust) redesenhado
- Melhor suporte a lock files
- Novo sistema de graph resolution
- Binary compatibility baseada em settings e options

### 3.2 Instalacao do Conan

```bash
# Instalar via pip (recomendado)
pip install conan

# Ou via pipx (isolamento de ambiente)
pipx install conan

# Verificar instalacao
conan --version

# Configurar o padrao de compilacao
conan profile detect --force
```

O comando `conan profile detect` cria um perfil padrao em `~/.conan2/profiles/default` baseado no compilador e SO detectados.

### 3.3 Estrutura de Diretorios do Conan 2.x

```
~/.conan2/
  profiles/       # Perfis de compilacao
  p/              # Pacotes instalados (cache binario)
  extensions/     # Plugins e extensoes
```

O cache do Conan armazena:
- Recipes (conanfile.py de cada pacote)
- Fontes baixadas
- Binarios compilados
- Metadados de compilacao

### 3.4 conanfile.txt — Formato Simples

O `conanfile.txt` e a forma mais simples de declarar dependencias. Ele e adequado para projetos que nao precisam de customizacao avancada.

#### Estrutura Basica

```ini
[requires]
nlohmann_json/3.11.2
fmt/10.1.1
spdlog/1.12.0
openssl/3.1.4
catch2/3.4.0

[generators]
CMakeDeps
CMakeToolchain

[layout]
cmake_layout

[options]
openssl/*:shared=False
fmt/*:shared=False
```

#### Secoes do conanfile.txt

| Secao | Descricao |
|-------|-----------|
| `[requires]` | Dependencias de biblioteca (runtime + dev) |
| `[build_requires]` | Dependencias apenas para build (ferramentas) |
| `[test_requires]` | Dependencias apenas para testes |
| `[generators]` | Geradores de arquivos de integracao com build system |
| `[layout]` | Layout do diretorio de build |
| `[options]` | Opcoes de compilacao para dependencias |
| `[import]` | Importar arquivos de outros diretorios |
| `[tool_requires]` | Ferramentas necessarias para build (alias de build_requires) |

#### Generators

Os generators determinam como Conan gera os arquivos de integracao:

```ini
[generators]
CMakeDeps        # Gera arquivos FindXXX.cmake ou xxx-config.cmake
CMakeToolchain   # Gera CMakeToolchain.cmake para toolchain
```

CMakeDeps gera arquivos de configuracao CMake para cada dependencia. CMakeToolchain gera um arquivo de toolchain que configura o CMake corretamente.

#### Formato de Dependencias

No conanfile.txt, as dependencias seguem o formato `nome/versao`:

```ini
[requires]
# Versao exata
openssl/3.1.4

# Versao minima (resolvida pelo Conan)
# O proprio Conan resolve a versao mais recente compativel
nlohmann_json/3.11.2
```

#### Opcoes

As opcoes seguem o formato `pacote/opcao=valor`:

```ini
[options]
openssl/*:shared=False
fmt/*:shared=False
boost/*:shared=False
boost/*:header_only=True
```

O curinga `*` aplica a opcao para todas as versoes daquele pacote.

### 3.5 conanfile.py — Formato Flexivel

O `conanfile.py` e um script Python que herda de `ConanFile`. Ele oferece controle total sobre como as dependencias sao resolvidas, construidas e empacotadas.

#### Estrutura Basica

```python
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain
from conan.tools.files import copy, get
import os


class MeuProjetoConan(ConanFile):
    name = "meu-projeto"
    version = "1.0.0"
    license = "MIT"
    description = "Projeto com gerenciamento seguro de dependencias"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def requirements(self):
        self.requires("nlohmann_json/3.11.2")
        self.requires("fmt/10.1.1")
        self.requires("spdlog/1.12.0")
        self.requires("openssl/3.1.4")

    def build_requirements(self):
        self.tool_requires("cmake/3.27.7")
        self.tool_requires("ninja/1.11.1")

    def test_requires(self):
        self.test_requires("catch2/3.4.0")
        self.test_requires("benchmark/1.8.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
```

#### Metodos do conanfile.py

| Metodo | Quando Executado | Descricao |
|--------|------------------|-----------|
| `requirements()` | Resolucao de grafico | Declara dependencias de runtime |
| `build_requirements()` | Resolucao de grafico | Declara ferramentas de build |
| `test_requires()` | Resolucao de grafico | Declara dependencias de teste |
| `layout()` | Depois de resolver | Define estrutura de diretorios |
| `generate()` | Apos layout | Gera arquivos para o build system |
| `build()` | Durante build | Executa o build |
| `package()` | Apos build | Empacota os artefatos |
| `package_id()` | Calculo de ID | Define identidade do pacote |
| `validate()` | Antes de resolver | Valida configuracao |
| `configure()` | Apos requirements | Configuracao adicional |

#### Configuracoes Avancadas

```python
class ProjetoSeguroConan(ConanFile):
    name = "projeto-seguro"
    version = "2.0.0"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": True,
    }

    def validate(self):
        if self.settings.compiler == "gcc":
            if self.settings.compiler.version < "12":
                raise ConanException("GCC >= 12 requerido")

        if self.settings.build_type == "Debug":
            self.output.warning("Build de Debug nao recomendado em producao")

    def requirements(self):
        self.requires("nlohmann_json/3.11.2")
        self.requires("fmt/10.1.1")

        if self.options.with_ssl:
            self.requires("openssl/3.1.4")
            self.requires("curl/8.4.0")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["SECURITY_FLAGS"] = True
        tc.generate()
```

#### Dependencias Condicionais

```python
def requirements(self):
    # Dependencia sempre presente
    self.requires("nlohmann_json/3.11.2")

    # Dependencia condicional a plataforma
    if self.settings.os == "Linux":
        self.requires("libunwind/1.7.2")

    # Dependencia condicional a opcao
    if self.options.with_ssl:
        self.requires("openssl/3.1.4")

    # Dependencia condicional a compilador
    if self.settings.compiler == "msvc":
        self.requires("dirent/1.24")

    # Dependencia condicional a build type
    if self.settings.build_type == "Debug":
        self.test_requires("fakeit/2.5.0")
```

### 3.6 Perfis de Compilacao

Perfis sao fundamentais no Conan. Eles definem as configuracoes de compilacao usadas para resolver e compilar dependencias.

#### Perfil Padrao

```bash
# Criar perfil padrao automaticamente
conan profile detect --force

# Conteudo do perfil detectado
# ~/.conan2/profiles/default
```

```
[settings]
arch=x86_64
build_type=Release
compiler=gcc
compiler.cppstd=17
compiler.libcxx=libstdc++11
compiler.version=13
os=Linux
```

#### Perfil Customizado

```ini
# ~/.conan2/profiles/linux-release
[settings]
arch=x86_64
build_type=Release
compiler=gcc
compiler.cppstd=17
compiler.libcxx=libstdc++11
compiler.version=13
compiler.libcxx=libstdc++11
os=Linux

[options]
*:shared=False
openssl*:shared=False

[buildenv]
CC=gcc-13
CXX=g++-13
```

#### Perfil para Debug

```ini
# ~/.conan2/profiles/linux-debug
[settings]
arch=x86_64
build_type=Debug
compiler=gcc
compiler.cppstd=17
compiler.libcxx=libstdc++11
compiler.version=13
os=Linux

[options]
*:shared=False
*:fPIC=True

[buildenv]
CC=gcc-13
CXX=g++-13
CFLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer
CXXFLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS=-fsanitize=address,undefined
```

#### Perfil para Cross-Compilation

```ini
# ~/.conan2/profiles/linux-arm64
[settings]
arch=armv8
build_type=Release
compiler=gcc
compiler.cppstd=17
compiler.libcxx=libstdc++11
compiler.version=13
os=Linux

[buildenv]
CC=aarch64-linux-gnu-gcc-13
CXX=aarch64-linux-gnu-g++-13
```

#### Profile Show

```bash
# Mostrar perfil ativo
conan profile show

# Mostrar perfil especifico
conan profile show linux-release

# Listar todos os perfis
conan profile list
```

### 3.7 Exemplo Completo conanfile.py

```python
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain
import os


class SegurancaAppConan(ConanFile):
    name = "seguranca-app"
    version = "1.0.0"
    license = "Apache-2.0"
    description = "Aplicacao com gerenciamento seguro de dependencias"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": True,
        "with_tests": True,
    }
    exports_sources = "CMakeLists.txt", "src/*", "include/*", "test/*"

    def requirements(self):
        self.requires("nlohmann_json/3.11.2")
        self.requires("fmt/10.1.1")
        self.requires("spdlog/1.12.0")

        if self.options.with_ssl:
            self.requires("openssl/3.1.4")
            self.requires("libcurl/8.4.0")

    def build_requirements(self):
        self.tool_requires("cmake/3.27.7")
        self.tool_requires("ninja/1.11.1")

    def test_requires(self):
        if self.options.with_tests:
            self.test_requires("catch2/3.4.0")
            self.test_requires("benchmark/1.8.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = self.options.with_tests
        tc.variables["WITH_SSL"] = self.options.with_ssl
        tc.variables["SECURITY_HARDENING"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        # Binary compatibility: opcoes nao afetam o ID do pacote
        if self.info.options.safe_locals("with_ssl") is not None:
            del self.info.options["with_ssl"]

    def package_info(self):
        self.cpp_info.libs = ["seguranca-app"]
        self.cpp_info.set_property("cmake_file_name", "SegurancaApp")
        self.cpp_info.set_property("cmake_find_mode", "config")
```

---

## 4. Comparacao: vcpkg vs Conan vs system packages

### 4.1 Visao Geral

| Aspecto | vcpkg | Conan 2.x | System Packages |
|---------|-------|-----------|-----------------|
| Mantenedor | Microsoft | JFrog | Distro (apt, yum) |
| Modelo | Manifest (declarativo) | Recipe (imperativo) | Binarios pre-compilados |
| Linguagem | JSON | Python | Varia (DEB, RPM) |
| Build system | CMake exclusivo | Multi (CMake, Meson, etc) | N/A (binarios) |
| Cross-platform | Sim | Sim | Nao (por distro) |
| Versoes | Port files no repo | Recipes no ConanCenter | Dependente da distro |
| Controle de versao | Overrides + lock | Ranges + lock | Limitado |
| Velocidade | Media (compila do fonte) | Media (compila do fonte) | Rapida (binarios) |
| Flexibilidade | Baixa (ports padronizados) | Alta (recipes customizaveis) | Baixa (pacotes do sistema) |
| Seguranca | Basica (hash do port) | Basica (hash do recipe) | GPG signing |

### 4.2 vcpkg vs Conan: Detalhamento

#### Arquitetura

**vcpkg** usa um modelo centralizado onde todas as ports estao em um unico repositorio (microsoft/vcpkg). Cada port e uma pasta com um `portfile.cmake` e um `vcpkg.json`. A compilacao e feita de forma padronizada.

**Conan** usa um modelo descentralizado com um repositorio central (ConanCenter) e a possibilidade de criar registros privados. Cada pacote tem um recipe (conanfile.py) que define como compilar.

#### Fluxo de Trabalho

**vcpkg:**
1. Declarar dependencias em `vcpkg.json`
2. Configurar CMake com `CMAKE_TOOLCHAIN_FILE`
3. vcpkg compila e instala automaticamente durante `cmake -B build`
4. Usar `find_package()` no CMakeLists.txt

**Conan:**
1. Declarar dependencias em `conanfile.py` ou `conanfile.txt`
2. Executar `conan install` para gerar arquivos de integracao
3. Configurar CMake com o toolchain gerado
4. Usar `find_package()` no CMakeLists.txt

#### Controle de Versao

**vcpkg:**
- Versoes minimas via `version>=`
- Overrides para forcar versao especifica
- Lock files para reproduzibilidade

**Conan:**
- Ranges de versao: `pkg/[>=1.0 <2.0]`
- Versao exata: `pkg/1.0.0`
- Lock files para reproduzibilidade
- Binary compatibility via package_id

#### Seguranca

**vcpkg:**
- Verificacao de hash implicita (via git baseline)
- Triplets para impor flags de seguranca
- Registros privados para dependencias proprietarias
- Sem auditoria integrada (requer ferramentas externas)

**Conan:**
- Verificacao de hash em recipes
- Perfis para configuracao de seguranca
- Registros privados (remotes) com autenticacao
- Conan audit (experimental) para vulnerabilidades

### 4.3 System Packages (apt, yum, brew)

Os pacotes do sistema sao a forma mais tradicional de gerenciar dependencias C/C++. Eles tem vantagens claras em cenarios de producao:

**Vantagens:**
- Binarios ja compilados e testados
- Atualizacoes de seguranca via pacotes do sistema
- Integracao com gerenciadores de seguranca do SO (unattended-upgrades)
- Instalacao rapida (nao compila do fonte)

**Desvantagens:**
- Versoes frequentemente desatualizadas
- Dificuldade de manter versoes especificas entre ambientes
- Nao funciona cross-platform (cada distro tem seus pacotes)
- Dependencias podem ser compartilhadas entre projetos (conflitos)

#### Quando Usar System Packages

```bash
# Ideal para: bibliotecas de sistema criticas
apt-get install -y \
  libssl-dev \
  libcurl4-openssl-dev \
  zlib1g-dev \
  libbz2-dev

# Nao ideal para: bibliotecas que precisam de versao especifica
# ou configuracao customizada
```

### 4.4 Tabela de Decisao

| Criterio | vcpkg | Conan | System |
|----------|-------|-------|--------|
| Projeto novo com controle total | Melhor | Bom | Nao |
| Multiplas plataformas | Excelente | Excelente | Nao |
| Binarios pre-compilados | Depende | Depende | Sim |
| Flexibilidade de configuracao | Media | Alta | Baixa |
| Producao com distro suportada | Nao | Nao | Sim |
| Dependencias proprietarias | Via registro | Via remote | Nao |
| Speed de build | Lenta (1a vez) | Lenta (1a vez) | Rapida |
| Reprodutibilidade | Excelente | Excelente | Boa |

### 4.5 Combinacao de Ferramentas

Em muitos projetos reais, e possivel e as vezes recomendado combinar abordagens:

```bash
# Usar system packages para dependencias de SO
apt-get install -y libssl-dev

# Usar vcpkg para bibliotecas C++ especificas
# via vcpkg.json

# Usar Conan para dependencias com configuracao complexa
# via conanfile.py
```

No entanto, e importante entender os trade-offs:

- Combinar fontes de dependencias dificulta a auditoria
- Cada ferramenta tem seu mecanismo de verificacao
- Builds reproduziveis sao mais dificeis quando dependencias vêm de multiplas fontes

---

## 5. Security features: hash verification, signing

### 5.1 Por Que Verificacao de Integridade

A verificacao de integridade e o processo de garantir que um pacote baixado e exatamente o que o autor publicou, sem alteracoes maliciousas. Sem verificacao, um atacante pode:

- Substituir um pacote por uma versao backdoorada
- Injetar codigo malicioso durante o download
- Modificar dependencias em transito (man-in-the-middle)
- Comprometer repositorios de pacotes

O caso mais notorio e o CVE-2024-3094 (XZ Utils backdoor), onde um maintainer comprometeu deliberadamente o codigo-fonte de uma biblioteca amplamente usada.

### 5.2 vcpkg: Verificacao de Hash

vcpkg usa hashes SHA-512 para verificar a integridade dos arquivos baixados. Cada port define o hash esperado em seu portfile:

```cmake
# vcpkg/ports/openssl/portfile.cmake
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO openssl/openssl
    REF openssl-3.1.4
    SHA512 ab1234...  # Hash esperado do arquivo baixado
    ...
)
```

Quando voce instala uma porta, vcpkg:

1. Baixa o arquivo da fonte especificada
2. Calcula o hash SHA-512 do arquivo baixado
3. Compara com o hash definido no portfile
4. Aborta se os hashes nao conferirem

#### Verificacao Manual

```bash
# Verificar hash de um pacote baixado
sha512sum /path/to/downloaded/file.tar.gz

# Comparar com o hash definido no portfile
cat vcpkg/ports/openssl/portfile.cmake | grep SHA512
```

#### Custom Ports com Hash

Quando voce cria uma porta customizada para uma biblioteca proprietaria:

```cmake
# vcpkg/ports/minha-lib/portfile.cmake
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO minha-org/minha-lib
    REF v1.2.3
    SHA512 a1b2c3d4e5f6789012345678901234567890abcdef12345678901234567890abcdef123456789012345678901234567890123456789012345678901234567890
    HEAD_REF main
)

vcpkg_cmake_configure(
    SOURCE_PATH ${SOURCE_PATH}
)

vcpkg_cmake_install()
```

### 5.3 Conan: Verificacao de Hash

Conan usa hashes SHA-256 para verificar integridade em multiplas camadas:

#### Hash no Recipe

```python
from conan import ConanFile
from conan.tools.files import get, load


class MinhaLibConan(ConanFile):
    name = "minha-lib"
    version = "1.2.3"
    url = "https://github.com/minha-org/minha-lib"
    license = "MIT"

    def source(self):
        get(self,
            "https://github.com/minha-org/minha-lib/archive/refs/tags/v1.2.3.tar.gz",
            sha256="a1b2c3d4e5f6789012345678901234567890abcdef12345678901234567890ab",
            strip_root=True)
```

#### Hash no Conanfile.txt

```ini
[requires]
openssl/3.1.4
```

O ConanCenter mantem hashes de todos os pacotes e verifica automaticamente ao baixar.

#### Verificacao em Registros Privados

```python
def source(self):
    # Conan verifica o hash automaticamente
    # se definido no recipe
    get(self,
        "https://artifactory.minha-org.com/artifacts/minha-lib-1.2.3.tar.gz",
        sha256="abc123...",
        strip_root=True)
```

### 5.4 Assinatura Digital

Alem da verificacao de hash, a assinatura digital fornece autenticidade (quem criou o pacote) alem de integridade.

#### GPG/PGP

Tanto vcpkg quanto Conan suportam verificacao GPG:

```bash
# Verificar assinatura de um pacote baixado
gpg --verify package.tar.gz.sig package.tar.gz

# Importar chave publica do autor
gpg --import chave-publica.asc

# Listar chaves importadas
gpg --list-keys
```

#### Conan com Assinatura

```python
from conan import ConanFile
from conan.tools.files import get, export_conandata_patches


class ProjetoAssinadoConan(ConanFile):
    name = "projeto-assinado"
    version = "1.0.0"

    def source(self):
        get(self,
            "https://github.com/minha-org/projeto/archive/refs/tags/v1.0.0.tar.gz",
            sha256="abc123...",
            strip_root=True)

    def export_sources(self):
        # Exporta patches com verificacao
        export_conandata_patches(self)
```

#### Sigstore

Sigstore e uma ferramenta moderna de assinatura de artefatos:

```bash
# Assinar um arquivo
cosign sign-blob --bundle projeto.bundle projeto.tar.gz

# Verificar assinatura
cosign verify-blob --bundle projeto.bundle projeto.tar.gz
```

### 5.5 TLS e Transporte Seguro

Tanto vcpkg quanto Conan usam HTTPS por padrao para downloads. Isso garante que a conexao e criptografada, protegendo contra ataques man-in-the-middle.

#### vcpkg

```bash
# Configurar proxy (se necessario)
export http_proxy=http://proxy.minha-org.com:8080
export https_proxy=http://proxy.minha-org.com:8080

# Ou configurar no vcpkg
./vcpkg install openssl --x-asset-sources=https://artifactory.minha-org.com
```

#### Conan

```ini
# ~/.conan2/remotes.yml
- name: conancenter
  url: https://center.conan.io
  verify_ssl: true

- name: minha-artifactory
  url: https://artifactory.minha-org.com/api/conan/conan-v1
  verify_ssl: true
```

O campo `verify_ssl: true` garante que o certificado SSL e verificado. Em ambientes corporativos com certificados auto-assinados:

```bash
# Configurar certificado CA
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
```

### 5.6 SBOM e Rastreabilidade

Gerar SBOM (Software Bill of Materials) e essencial para rastrear todas as dependencias:

#### vcpkg com SBOM

```bash
# Gerar lista de dependencias
vcpkg list --triplet x64-linux > dependencies.txt

# Ou usar CMake para gerar SPDX
cmake -B build -S . -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
```

#### Conan com SBOM

```bash
# Listar dependencias com informacoes detalhadas
conan graph info . --format=json > dependencies.json

# Gerar grafo de dependencias
conan graph info . --format=html > dependencies.html
```

---

## 6. Lock files: vcpkg-lock.json, conan.lock

### 6.1 Por Que Lock Files

Lock files sao arquivos que registram a versao EXATA de cada dependencia (e suas sub-dependencias) resolvida em um momento especifico. Sem lock files:

- `vcpkg.json` com `version>=3.1.0` pode resolver para 3.1.0 em uma maquina e 3.2.0 em outra
- `conanfile.txt` com `openssl/3.1.4` pode resolver sub-dependencias diferentes dependendo do perfil
- Builds nao sao reproduziveis entre ambientes e ao longo do tempo

Lock files resolvem isso fixando todas as versoes na arvore de dependencias.

### 6.2 vcpkg Lock Files

#### Gerando o Lock File

```bash
# Gerar o lock file
vcpkg x-update-baseline --lock
# Ou
cmake --preset default  # Gera automaticamente se configurado
```

#### Estrutura do vcpkg-lock.json

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg-lock.schema.json",
  "version": 1,
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "registries": [],
  "packages": [
    {
      "name": "openssl",
      "version": "3.1.4",
      "port-version": 0
    },
    {
      "name": "nlohmann-json",
      "version": "3.11.2",
      "port-version": 0
    },
    {
      "name": "fmt",
      "version": "10.1.1",
      "port-version": 0
    }
  ]
}
```

#### Uso do Lock File

```bash
# Instalar dependencias exatas do lock file
vcpkg install --x-install-root=vcpkg_installed

# Verificar se o lock file esta atualizado
vcpkg x-check-licenses

# Atualizar lock file (muda versoes para as mais recentes)
vcpkg x-update-baseline --update
```

#### Integracao com CMake

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(projeto-seguro LANGUAGES CXX)

# O vcpkg automaticamente usa o lock file se ele existir
find_package(nlohmann_json REQUIRED)
find_package(fmt REQUIRED)

add_executable(app main.cpp)
target_link_libraries(app nlohmann_json::nlohmann_json fmt::fmt)
```

### 6.3 Conan Lock Files

#### Gerando o Lock File

```bash
# Criar lock file
conan lock create conanfile.py --lockfile-out=conan.lock

# Ou com conanfile.txt
conan lock create conanfile.txt --lockfile-out=conan.lock
```

#### Estrutura do conan.lock

```json
{
  "version": "0.5",
  "requires": [
    "openssl/3.1.4#abc123def456",
    "nlohmann_json/3.11.2#def789abc012",
    "fmt/10.1.1#123abc456def"
  ],
  "build_requires": [
    "cmake/3.27.7#789abc012def"
  ],
  "python_requires": []
}
```

O formato inclui um hash (`#abc123...`) apos cada versao. Esse hash e o `recipe_revision` do Conan, que garante que nao apenas a versao, mas tambem o recipe exato e usado.

#### Uso do Lock File

```bash
# Instalar com lock file (usar versoes exatas)
conan install . --lockfile=conan.lock

# Atualizar dependencias mantendo o lock file
conan graph info . --lockfile=conan.lock --lockfile-out=conan.lock

# Verificar se o lock file e consistente
conan lock create conanfile.py --lockfile=conan.lock
```

#### Lock File em CI/CD

```yaml
# GitHub Actions
steps:
  - name: Install dependencies
    run: |
      conan install . --lockfile=conan.lock --build=missing
      cmake --preset conan-release
```

### 6.4 Melhores Praticas para Lock Files

1. **Versionar lock files**: Adicione tanto `vcpkg-lock.json` quanto `conan.lock` ao repositorio Git
2. **Atualizar periodicamente**: Use ferramentas de atualizacao automatizada (Dependabot, Renovate)
3. **Verificar em CI**: Valide que o lock file e consistente com o manifesto em cada build
4. **Documentar processo**: Defina quem e como atualizar dependencias

```bash
# Git: adicionar lock files
git add vcpkg.json vcpkg-lock.json conanfile.py conan.lock
git commit -m "deps: pin all dependencies with lock files"
```

### 6.5 Atualizacao de Dependencias

#### vcpkg

```bash
# Atualizar baseline (muda a versao resolvida)
vcpkg x-update-baseline --update

# Revisar mudancas
git diff vcpkg-lock.json

# Testar antes de commitar
cmake --preset default && cmake --build --preset default && ctest --preset default
```

#### Conan

```bash
# Atualizar todas as dependencias
conan graph info . --update --lockfile-out=conan.lock

# Atualizar pacote especifico
conan graph info . --update openssl/* --lockfile-out=conan.lock

# Revisar mudancas
git diff conan.lock
```

---

## 7. Binary caching: vcpkg binary caching, Conan cache

### 7.1 Por Que Binary Caching

Compilar dependencias do codigo-fonte e lento. O OpenSSL, por exemplo, pode levar varios minutos para compilar. Em ambientes com multiplos desenvolvedores ou CI/CD com muitos builds, recompilar sempre e desperdicio.

Binary caching armazena binarios compilados para que possam ser reutilizados. Isso reduz drasticamente o tempo de build, mas introduce riscos de seguranca:

- Binarios cacheados podem estar desatualizados
- Cache compartilhado pode ser comprometido
- Binarios de arquiteturas diferentes podem ser confundidos

### 7.2 vcpkg Binary Caching

#### Como Funciona

vcpkg mantem um cache local por padrao em `~/.cache/vcpkg/archives/`. Quando uma dependencia e compilada, o binario e armazenado com base no hash da configuracao.

#### Configuracao Basica

```bash
# Usar cache local (padrao)
# Nao e necessaria configuracao adicional

# Verificar cache
ls ~/.cache/vcpkg/archives/

# Limpar cache
rm -rf ~/.cache/vcpkg/archives/*
```

#### Filesystem Cache (Recomendado para Equipes)

```bash
# Usar cache em diretorio compartilhado
export VCPKG_DEFAULT_BINARY_CACHE=/mnt/shared/vcpkg-cache

# Ou configurar no vcpkg-configuration.json
```

```json
{
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "cache": {
    "files": [
      {
        "kind": "filesystem",
        "path": "/mnt/shared/vcpkg-cache"
      }
    ]
  }
}
```

#### Azure Blob Storage

```bash
# Configurar cache no Azure
export VCPKG_BINARY_SOURCES="clear;x-azure,https://meublob.blob.core.windows.net/vcpkg-cache?SAS_TOKEN"

# Ou com account key
export VCPKG_BINARY_SOURCES="clear;x-azure,https://meublob.blob.core.windows.net/vcpkg-cache,readwrite"
```

#### GitHub Actions Cache

```yaml
# GitHub Actions com cache
env:
  VCPKG_BINARY_SOURCES: "clear;x-gha,readwrite"

steps:
  - name: Setup vcpkg
    uses: lukka/run-vcpkg@v11

  - name: Cache vcpkg binaries
    uses: actions/cache@v4
    with:
      path: ~/.cache/vcpkg
      key: vcpkg-${{ runner.os }}-${{ hashFiles('vcpkg.json') }}
      restore-keys: |
        vcpkg-${{ runner.os }}-
```

#### Seguranca do Cache

```bash
# Verificar integridade do cache
# vcpkg ja verifica hashes automaticamente

# Limpar cache periodicamente
find ~/.cache/vcpkg/archives/ -mtime +30 -delete

# Usar cache somente leitura em CI de producao
export VCPKG_BINARY_SOURCES="clear;files,/mnt/shared/cache,read"
```

### 7.3 Conan Cache

#### Como Funciona

Conan mantem um cache local em `~/.conan2/p/`. Cada pacote e indexado por:
- Nome e versao
- Settings (SO, compilador, build_type, arch)
- Opcoes
- Recipe revision
- Package revision

#### Configuracao Basica

```bash
# Verificar cache
conan cache list

# Limpar cache
conan remove "*" -c

# Verificar tamanho do cache
du -sh ~/.conan2/p/
```

#### Cache Compartilhado

```bash
# Configurar cache em diretorio compartilhado
# (via symlinks ou bind mounts)

# Ou usar Artifactory/Conan Server como cache remoto
conan remote add minha-cache https://artifactory.minha-org.com/api/conan/conan-cache
```

#### Binary Compatibility

Conan e mais granular que vcpkg na determinacao de compatibilidade binaria. Um pacote compilado com GCC 13 e considerado incompativel com GCC 14:

```python
# No conanfile.py, controlar compatibilidade
def package_id(self):
    # Versao do compilador nao afeta o ID
    self.info.settings.compiler.version = "ANY"

    # Build type afeta o ID
    # (padrao: afeta)
```

#### Upload para Cache Remoto

```bash
# Upload todos os pacotes locais
conan upload "*" --all -r minha-cache

# Upload pacote especifico
conan upload openssl/3.1.4 -r minha-cache

# Upload com verificacao
conan upload "*" --all -r minha-cache --check
```

### 7.4 Comparacao de Binary Caching

| Aspecto | vcpkg | Conan |
|---------|-------|-------|
| Cache local | ~/.cache/vcpkg | ~/.conan2/p |
| Granularidade | Por package + triplet | Por package + settings |
| Cache remoto | Azure, GCS, S3 | Artifactory, Nexus, S3 |
| Compatibilidade binaria | Por triplet + build_type | Configuravel |
| Verificacao de integridade | Hash SHA-512 | Hash SHA-256 + recipe_rev |
| Limpeza automatica | Nao | Nao |

### 7.5 Melhores Praticas

1. **Nunca confie cegamente em binarios cacheados**: Verifique hashes sempre
2. **Use cache somente leitura em CI de producao**: Evite que builds de producao atualizem o cache
3. **Separe caches por ambiente**: Cache de dev, staging e producao devem ser isolados
4. **Monitore o tamanho do cache**: Cache descontrolado consome disco
5. **Invalide cache apos atualizacoes de seguranca**: Quando uma dependencia recebe um patch de seguranca, invalide o cache

```bash
# Invalidar cache especifico
rm -rf ~/.cache/vcpkg/archives/*openssl*
conan remove "openssl/*" -c

# Reconstruir
cmake --preset default --fresh
```

---

## 8. Private registries: vcpkg config, Conan remote

### 8.1 Por Que Registros Privados

Muitas organizacoes possuem bibliotecas proprietarias que nao podem ser publicadas em registros publicos. Registros privados permitem:

- Publicar e consumir bibliotecas internas
- Controlar quais versoes estao disponiveis
- Aplicar politicas de seguranca (aprovacao, auditoria)
- Manter bibliotecas proprietarias seguras

### 8.2 vcpkg: Registros Privados

#### Estrutura de um Registro Privado

Um registro vcpkg e um repositorio Git com a estrutura de ports:

```
meu-registry/
  ports/
    minha-lib/
      vcpkg.json
      portfile.cmake
      fix-include.patch
    outra-lib/
      vcpkg.json
      portfile.cmake
  versions/
    baseline.json
    m-/minha-lib.json
    o-/outra-lib.json
```

#### Configuracao do Registro

```json
// vcpkg-configuration.json
{
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "registries": [
    {
      "kind": "git",
      "repository": "https://github.com/minha-org/vcpkg-registry",
      "baseline": "a1b2c3d4e5f6789012345678901234567890abcd",
      "packages": ["minha-lib", "outra-lib"]
    }
  ]
}
```

#### Criando uma Port no Registro Privado

```cmake
# meu-registry/ports/minha-lib/vcpkg.json
{
  "name": "minha-lib",
  "version-string": "1.2.3",
  "description": "Biblioteca proprietaria da minha organizacao",
  "license": "Proprietary",
  "dependencies": [
    "nlohmann-json",
    "fmt"
  ]
}
```

```cmake
# meu-registry/ports/minha-lib/portfile.cmake
set(VCPKG_POLICY_CMAKE_HELPER_POLICY enabled)

vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO minha-org/minha-lib
    REF v1.2.3
    SHA512 a1b2c3d4e5f6789012345678901234567890abcdef12345678901234567890abcdef123456789012345678901234567890123456789012345678901234567890
    HEAD_REF main
    PATCHES
        fix-include.patch
)

vcpkg_cmake_configure(
    SOURCE_PATH ${SOURCE_PATH}
    OPTIONS
        -DBUILD_TESTING=OFF
        -DCMAKE_BUILD_TYPE=Release
)

vcpkg_cmake_install()
vcpkg_fixup_cmake_targets()
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
```

#### Artifactory como Registro

```json
{
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  },
  "registries": [
    {
      "kind": "artifactory",
      "repository": "https://artifactory.minha-org.com/artifactory/vcpkg-registry",
      "packages": ["minha-lib"]
    }
  ]
}
```

### 8.3 Conan: Remotes Privados

#### Estrutura de um Remote

Um remote Conan e um servidor que hospeda pacotes. Opcoes incluem:

- **Conan Server**: servidor simples incluso no Conan
- **Artifactory**: solucao corporativa completa
- **Nexus**: alternativa open-source
- **S3/MinIO**: armazenamento de objetos com estrutura de pacotes

#### Configuracao de Remotes

```bash
# Adicionar remote
conan remote add minha-cache https://artifactory.minha-org.com/api/conan/conan-cache

# Listar remotes
conan remote list

# Remover remote
conan remote remove minha-cache
```

#### Arquivo de Configuracao

```yaml
# ~/.conan2/remotes.yml
- name: conancenter
  url: https://center.conan.io
  verify_ssl: true

- name: minha-artifactory
  url: https://artifactory.minha-org.com/api/conan/conan-cache
  verify_ssl: true

- name: nexus-local
  url: https://nexus.minha-org.com/repository/conan-local/
  verify_ssl: true
```

#### Conan Server Basico

```bash
# Iniciar servidor local (para desenvolvimento)
conan server

# Configuracao do servidor
# ~/.conan2/server.conf
[server]
port: 9300
users: admin:admin,dev:dev
```

#### Autenticacao

```bash
# Login no remote
conan remote login minha-artifactory admin

# Verificar credenciais
conan remote list

# Logout
conan remote logout minha-artifactory
```

#### Upload para Remote

```bash
# Upload pacote para remote
conan upload openssl/3.1.4 -r minha-cache

# Upload todos os pacotes
conan upload "*" -r minha-cache

# Upload com selecao
conan upload "openssl/*" -r minha-cache --confirm
```

### 8.4 Melhores Praticas para Registros Privados

1. **Use autenticacao por token**: Nunca use senhas em texto plano
2. **Configure TLS**: Todos os remotes devem usar HTTPS
3. **Aplique politicas de aprovacao**: Nem todos devem poder publicar
4. **Audite acessos**: Registre quem baixa o que e quando
5. **Versione a configuracao**: Mantenha vcpkg-configuration.json e remotes.yml no repositorio

---

## 9. Audit: vcpkg audit, conan audit

### 9.1 Por Que Auditar Dependencias

Vulnerabilidades em dependencias de terceiros sao uma das maiores fontes de ataques. O Sonatype Relatorio 2023 documentou mais de 245.000 ataques a software supply chain. Auditar dependencias e o processo de verificar se as bibliotecas que voce usa tem vulnerabilidades conhecidas.

### 9.2 Ferramentas de Auditoria

#### OSV-Scanner (Google)

```bash
# Instalar
go install github.com/google/osv-scanner/cmd/osv-scanner@latest

# Ou via npm
npm install -g osv-scanner

# Escanear projeto vcpkg
osv-scanner --lockfile=vcpkg-lock.json

# Escanear projeto Conan
osv-scanner --lockfile=conan.lock

# Modo recursivo
osv-scanner -r ./
```

#### Grype (Anchore)

```bash
# Instalar
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# Escanear SBOM
grype sbom:./sbom.spdx.json

# Escanear imagem Docker
grype docker:meu-app:latest
```

#### Snyk

```bash
# Instalar
npm install -g snyk

# Autenticar
snyk auth

# Escanear projeto
snyk test

# Monitor continuo
snyk monitor
```

### 9.3 vcpkg Audit

O vcpkg nao tem um comando de auditoria integrado, mas existem abordagens:

#### Usando vcpkg com OSV-Scanner

```bash
# 1. Gerar lista de dependencias
vcpkg list --triplet x64-linux --x-json > deps.json

# 2. Escanear com OSV-Scanner
osv-scanner --lockfile=vcpkg-lock.json

# 3. Ou gerar SBOM e escanear
# Usando cdxgen para gerar CycloneDX
npx @cyclonedx/cdxgen -o sbom.json
grype sbom:sbom.json
```

#### Script de Auditoria

```bash
#!/bin/bash
# audit-vcpkg.sh

echo "=== Auditoria de Dependencias vcpkg ==="
echo ""

# Verificar se vcpkg-lock.json existe
if [ ! -f "vcpkg-lock.json" ]; then
    echo "ERRO: vcpkg-lock.json nao encontrado"
    echo "Execute: vcpkg x-update-baseline --lock"
    exit 1
fi

# Extrair pacotes e versoes
echo "Pacotes instalados:"
jq -r '.packages[] | "\(.name)/\(.version)"' vcpkg-lock.json

echo ""
echo "Escaneando com OSV-Scanner..."
osv-scanner --lockfile=vcpkg-lock.json

if [ $? -ne 0 ]; then
    echo ""
    echo "AVISO: Vulnerabilidades encontradas!"
    echo "Revise as vulnerabilidades antes de prosseguir."
    exit 1
fi

echo ""
echo "Nenhuma vulnerabilidade encontrada."
```

### 9.4 Conan Audit

Conan 2.x inclui suporte experimental a auditoria:

#### Usando conan audit

```bash
# Verificar vulnerabilidades (requer conan 2.x+)
conan audit

# Escanear grafo de dependencias
conan graph info . --format=json | jq '.dependencies' > deps.json
osv-scanner --package-lock=deps.json
```

#### Integração com CVEDb

```python
# conanfile.py com verificacao de seguranca
from conan import ConanFile


class ProjetoAuditConan(ConanFile):
    name = "projeto-audit"
    version = "1.0.0"

    def requirements(self):
        self.requires("openssl/3.1.4")
        self.requires("nlohmann_json/3.11.2")

    def build_requirements(self):
        self.tool_requires("cmake/3.27.7")

    def generate(self):
        # Gerar relatorio de dependencias para auditoria
        deps = self.dependencies
        for require, dependency in deps.items():
            self.output.info(
                f"Dependency: {require.ref.name}/{require.ref.version}"
            )
```

### 9.5 CI/CD com Auditoria

```yaml
# GitHub Actions
name: Dependency Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Segunda-feira as 6h

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install OSV-Scanner
        run: |
          go install github.com/google/osv-scanner/cmd/osv-scanner@latest

      - name: Audit vcpkg dependencies
        run: osv-scanner --lockfile=vcpkg-lock.json --output=report.json

      - name: Check for critical vulnerabilities
        run: |
          CRITICAL=$(jq '[.results[].packages[] | select(.vulnerabilities[]?.severity == "CRITICAL")] | length' report.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "ERRO: Vulnerabilidades criticas encontradas!"
            jq '.results[].packages[] | select(.vulnerabilities[]?.severity == "CRITICAL")' report.json
            exit 1
          fi

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: audit-report
          path: report.json
```

---

## 10. Integration with CMake: find_package after install

### 10.1 Integracao basica do vcpkg com CMake

vcpkg se integra com CMake via CMAKE_TOOLCHAIN_FILE. Quando voce configura o CMake com o toolchain do vcpkg, ele automaticamente:

1. Compila as dependencias declaradas em `vcpkg.json`
2. Instala os binarios em `vcpkg_installed/`
3. Configura os paths para que `find_package()` encontre as bibliotecas

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(projeto-seguro LANGUAGES CXX)

# find_package funciona normalmente
find_package(nlohmann_json REQUIRED)
find_package(fmt REQUIRED)
find_package(OpenSSL REQUIRED)

add_executable(app
    src/main.cpp
    src/crypto.cpp
)

target_link_libraries(app
    PRIVATE
        nlohmann_json::nlohmann_json
        fmt::fmt
        OpenSSL::SSL
        OpenSSL::Crypto
)

# Configurar target properties
set_target_properties(app PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)
```

#### Configuracao

```bash
# Com vcpkg como submodule
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=./vcpkg/scripts/buildsystems/vcpkg.cmake \
  -DVCPKG_TARGET_TRIPLET=x64-linux

# Com VCPKG_ROOT definido
cmake -B build -S .

# Com vcpkg preset
cmake --preset default
```

### 10.2 Integracao do Conan com CMake

Conan gera arquivos de integracao que o CMake usa para encontrar dependencias.

#### Fluxo de Trabalho

```bash
# 1. Instalar dependencias (gera arquivos de integracao)
conan install . --output-folder=build --build=missing

# 2. Configurar CMake usando o toolchain gerado
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release

# 3. Compilar
cmake --build build
```

#### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(projeto-seguro LANGUAGES CXX)

# find_package funciona normalmente (arquivos gerados pelo Conan)
find_package(nlohmann_json REQUIRED)
find_package(fmt REQUIRED)
find_package(OpenSSL REQUIRED)

add_executable(app
    src/main.cpp
    src/crypto.cpp
)

target_link_libraries(app
    PRIVATE
        nlohmann_json::nlohmann_json
        fmt::fmt
        OpenSSL::SSL
        OpenSSL::Crypto
)
```

### 10.3 CMakePresets.json para Ambos

```json
{
  "version": 6,
  "configurePresets": [
    {
      "name": "vcpkg-base",
      "hidden": true,
      "toolchainFile": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake",
      "binaryDir": "${sourceDir}/build/vcpkg-${presetName}",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release"
      }
    },
    {
      "name": "vcpkg-default",
      "displayName": "vcpkg Default",
      "inherits": "vcpkg-base",
      "generator": "Ninja",
      "cacheVariables": {
        "VCPKG_TARGET_TRIPLET": "x64-linux"
      }
    },
    {
      "name": "conan-release",
      "displayName": "Conan Release",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/conan-release",
      "toolchainFile": "${sourceDir}/build/conan_toolchain.cmake",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "vcpkg-default",
      "configurePreset": "vcpkg-default"
    },
    {
      "name": "conan-release",
      "configurePreset": "conan-release"
    }
  ]
}
```

### 10.4 Tratamento de Erros Comuns

#### vcpkg: Pacote nao encontrado

```cmake
# E se find_package falhar?
find_package(nlohmann_json QUIET)
if(NOT nlohmann_json_FOUND)
    message(WARNING "nlohmann_json nao encontrado via vcpkg")
    # Fallback: usar FetchContent
    include(FetchContent)
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG v3.11.2
    )
    FetchContent_MakeAvailable(nlohmann_json)
endif()
```

#### Conan: Versao incompativel

```python
# conanfile.py com tratamento de erro
def requirements(self):
    try:
        self.requires("openssl/3.1.4")
    except ConanException:
        self.output.warning("openssl 3.1.4 indisponivel, usando 3.0.12")
        self.requires("openssl/3.0.12")
```

### 10.5 find_package: Modos de Busca

```cmake
# Modo CONFIG (recomendado)
find_package(OpenSSL CONFIG REQUIRED)

# Modo MODULE (procura FindXXX.cmake)
find_package(OpenSSL MODULE REQUIRED)

# Com versao especifica
find_package(fmt 10.0 REQUIRED)

# Componentes
find_package(Qt6 COMPONENTS Core Network Widgets REQUIRED)
```

---

## 11. Supply chain security: pinning, reproducibility

### 11.1 O Problema do Supply Chain

Supply chain attacks exploram a confianca que projetos depositam em dependencias de terceiros. Exemplos reais:

- **CVE-2024-3094 (XZ Utils)**: Backdoor inserida por um maintainer de confianca
- **CVE-2021-44228 (Log4Shell)**: Vulnerabilidade em biblioteca amplamente usada
- **event-stream (2018)**: Pacote npm comprometido apos transferencia de propriedade
- **ua-parser-js (2021)**: Pacote popular no npm infectado com malware

### 11.2 Estrategias de Defesa

#### Pinning Exato

Fixar versoes exatas de todas as dependencias:

```json
// vcpkg.json — pinning via overrides
{
  "dependencies": [
    { "name": "openssl", "version>=": "3.1.0" }
  ],
  "overrides": [
    { "name": "openssl", "version": "3.1.4" }
  ]
}
```

```ini
# conanfile.txt — pinning por versao exata
[requires]
openssl/3.1.4
nlohmann_json/3.11.2
fmt/10.1.1
```

#### Baseline Pinning

Fixar o baseline do registro para garantir que todas as versoes sejam consistentes:

```json
// vcpkg-configuration.json
{
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"  // Commit hash ou tag
  }
}
```

#### Recipe Revision Pinning (Conan)

```bash
# Conan usa recipe revision para fixar o recipe exato
conan lock create conanfile.py --lockfile-out=conan.lock

# O lock file inclui o recipe revision:
# "openssl/3.1.4#abc123..."
# O "#abc123" e o recipe revision
```

### 11.3 Reprodutibilidade

#### O Que e Build Reproduzivel

Um build e reproduzivel se, dado o mesmo codigo-fonte e as mesmas dependencias, o resultado binario e identico (bit-a-bit). Isso e importante porque:

- Permite verificar se um binario distribuido corresponde ao codigo-fonte
- Facilita auditorias de seguranca
- Detecta contaminacao no processo de build

#### Como Conseguir Reprodutibilidade

1. **Pin todas as dependencias**: Use lock files
2. **Fixe o compilador**: Use a mesma versao do compilador
3. **Fixe as flags**: Nao use variaveis de ambiente que afetem o build
4. **Use timestamps zero**: Configure SOURCE_DATE_EPOCH=0
5. **Nao use rede durante o build**: Pre-cache todas as dependencias

```bash
# vcpkg: build reproduzivel
export SOURCE_DATE_EPOCH=0
cmake --preset default
cmake --build --preset default
```

```bash
# Conan: build reproduzivel
conan install . --lockfile=conan.lock --build=missing
export SOURCE_DATE_EPOCH=0
cmake -B build -S . \
  -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

### 11.4 Verificacao de Assinatura

#### cosign (Sigstore)

```bash
# Assinar um artefato
cosign sign-blob --bundle projeto.bundle projeto.tar.gz

# Verificar assinatura
cosign verify-blob --bundle projeto.bundle projeto.tar.gz

# Verificar com chave publica
cosign verify-blob --bundle projeto.bundle \
  --key cosign.pub \
  projeto.tar.gz
```

#### Integração com CI/CD

```yaml
# GitHub Actions
steps:
  - name: Verify artifact signature
    run: |
      cosign verify-blob \
        --bundle artifacts.bundle \
        --certificate-identity-regexp "https://github.com/minha-org/*" \
        --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
        build/output.tar.gz
```

### 11.5 SLSA (Supply-chain Levels for Software Artifacts)

SLSA e um framework que define niveis de seguranca para software supply chain:

| Nivel | Descricao | Protecao |
|-------|-----------|----------|
| SLSA 1 | Build process documentado | Protecao basica contra adulteracao |
| SLSA 2 | Build hospedado e gerenciado | Protecao contra manipulacao individual |
| SLSA 3 | Build com isolamento | Protecao contra alteracoes de insiders |
| SLSA 4 | Build reproduzivel | Protecao completa contra adulteracao |

#### Implementando SLSA com vcpkg + Conan

```yaml
# GitHub Actions com SLSA
name: Build with SLSA

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup vcpkg
        uses: lukka/run-vcpkg@v11

      - name: Install Conan dependencies
        run: |
          pip install conan
          conan install . --lockfile=conan.lock --build=missing

      - name: Build
        run: |
          cmake --preset default
          cmake --build --preset default

      - name: Generate SBOM
        run: |
          npx @cyclonedx/cdxgen -o sbom.json

      - name: Sign artifacts
        run: |
          cosign sign-blob --bundle build.bundle build/app
```

### 11.6 Dependabot / Renovate

Ferramentas de atualizacao automatizada de dependencias:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "vcpkg"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "security"
```

```json
// renovate.json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "vcpkg": {
    "enabled": true
  },
  "lockFileMaintenance": {
    "enabled": true
  }
}
```

---

## 12. Exemplo: projeto com vcpkg + Conan

### 12.1 Estrutura do Projeto

```
projeto-seguro/
  CMakeLists.txt
  CMakePresets.json
  vcpkg.json
  vcpkg-configuration.json
  vcpkg-lock.json
  conanfile.py
  conan.lock
  conanprofiles/
    default
    release
    debug
  src/
    main.cpp
    crypto.h
    crypto.cpp
    config.h.in
  test/
    CMakeLists.txt
    test_crypto.cpp
  cmake/
    FindDependencies.cmake
  .github/
    workflows/
      ci.yml
```

### 12.2 vcpkg.json

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg.schema.json",
  "name": "projeto-seguro",
  "version-string": "1.0.0",
  "description": "Projeto com gerenciamento seguro de dependencias C++",
  "license": "Apache-2.0",
  "supports": "linux | osx",
  "dependencies": [
    {
      "name": "openssl",
      "version>=": "3.1.0",
      "features": ["tools"]
    },
    "nlohmann-json",
    {
      "name": "fmt",
      "version>=": "10.0.0"
    },
    {
      "name": "spdlog",
      "version>=": "1.12.0",
      "features": ["fmt"]
    }
  ],
  "overrides": [
    {
      "name": "openssl",
      "version": "3.1.4"
    }
  ]
}
```

### 12.3 vcpkg-configuration.json

```json
{
  "$schema": "https://raw.githubusercontent.com/microsoft/vcpkg-tool/main/docs/vcpkg-configuration.schema.json",
  "default-registry": {
    "kind": "git",
    "repository": "https://github.com/microsoft/vcpkg",
    "baseline": "2024.01.12"
  }
}
```

### 12.4 conanfile.py

```python
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout, CMakeDeps, CMakeToolchain
import os


class ProjetoSeguroConan(ConanFile):
    name = "projeto-seguro"
    version = "1.0.0"
    license = "Apache-2.0"
    description = "Projeto com gerenciamento seguro de dependencias C++"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "CMakeLists.txt", "src/*", "test/*"

    def requirements(self):
        self.requires("openssl/3.1.4")
        self.requires("nlohmann_json/3.11.2")
        self.requires("fmt/10.1.1")
        self.requires("spdlog/1.12.0")

    def build_requirements(self):
        self.tool_requires("cmake/3.27.7")
        self.tool_requires("ninja/1.11.1")

    def test_requires(self):
        self.test_requires("catch2/3.4.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
```

### 12.5 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(projeto-seguro VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Opcoes de build
option(BUILD_TESTING "Construir testes" ON)
option(SECURITY_HARDENING "Aplicar flags de hardening" ON)

# Flags de seguranca (se habilitadas)
if(SECURITY_HARDENING)
    add_compile_options(
        -fstack-protector-strong
        -D_FORTIFY_SOURCE=2
        -fPIE
        -Wformat -Wformat-security
    )
    add_link_options(-pie)
endif()

# Encontrar dependencias
find_package(OpenSSL REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(fmt REQUIRED)
find_package(spdlog REQUIRED)

# Library principal
add_library(projeto-seguro-lib
    src/crypto.cpp
)

target_include_directories(projeto-seguro-lib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(projeto-seguro-lib
    PUBLIC
        OpenSSL::SSL
        OpenSSL::Crypto
        nlohmann_json::nlohmann_json
        fmt::fmt
        spdlog::spdlog
)

# Executavel principal
add_executable(projeto-seguro
    src/main.cpp
)

target_link_libraries(projeto-seguro
    PRIVATE
        projeto-seguro-lib
)

# Testes
if(BUILD_TESTING)
    enable_testing()
    find_package(Catch2 REQUIRED)

    add_executable(test_crypto
        test/test_crypto.cpp
    )

    target_link_libraries(test_crypto
        PRIVATE
            projeto-seguro-lib
            Catch2::Catch2WithMain
    )

    include(Catch)
    catch_discover_tests(test_crypto)
endif()

# Instalacao
include(GNUInstallDirs)

install(TARGETS projeto-seguro
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(TARGETS projeto-seguro-lib
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
```

### 12.6 CMakePresets.json

```json
{
  "version": 6,
  "configurePresets": [
    {
      "name": "vcpkg-base",
      "hidden": true,
      "toolchainFile": "$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake",
      "binaryDir": "${sourceDir}/build/${presetName}",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    },
    {
      "name": "default",
      "displayName": "Default (vcpkg)",
      "inherits": "vcpkg-base",
      "generator": "Ninja",
      "cacheVariables": {
        "VCPKG_TARGET_TRIPLET": "x64-linux"
      }
    },
    {
      "name": "secure",
      "displayName": "Secure (vcpkg + hardening)",
      "inherits": "vcpkg-base",
      "generator": "Ninja",
      "cacheVariables": {
        "VCPKG_TARGET_TRIPLET": "x64-linux-hardened",
        "SECURITY_HARDENING": "ON"
      }
    },
    {
      "name": "conan-release",
      "displayName": "Conan Release",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/conan-release",
      "toolchainFile": "${sourceDir}/build/conan_toolchain.cmake",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
      }
    }
  ],
  "buildPresets": [
    {
      "name": "default",
      "configurePreset": "default"
    },
    {
      "name": "secure",
      "configurePreset": "secure"
    },
    {
      "name": "conan-release",
      "configurePreset": "conan-release"
    }
  ],
  "testPresets": [
    {
      "name": "default",
      "configurePreset": "default",
      "output": {
        "outputOnFailure": true
      }
    }
  ]
}
```

### 12.7 Fonte do Projeto

```cpp
// src/crypto.h
#pragma once

#include <string>
#include <vector>
#include <openssl/evp.h>
#include <nlohmann/json.hpp>

namespace seguranca {

class Crypto {
public:
    Crypto();
    ~Crypto();

    std::string hash_sha256(const std::string& data);
    std::string encrypt_aes_256(const std::string& plaintext, const std::string& key);
    std::string decrypt_aes_256(const std::string& ciphertext, const std::string& key);
    bool verify_signature(const std::string& data, const std::string& signature, const std::string& pub_key);

    nlohmann::json generate_report(const std::string& operation, bool success);

private:
    bool initialized_;
};

}  // namespace seguranca
```

```cpp
// src/crypto.cpp
#include "crypto.h"
#include <openssl/sha.h>
#include <openssl/aes.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <fmt/format.h>
#include <spdlog/spdlog.h>
#include <stdexcept>

namespace seguranca {

Crypto::Crypto() : initialized_(false) {
    OpenSSL_add_all_algorithms();
    initialized_ = true;
    spdlog::info("Crypto module initialized");
}

Crypto::~Crypto() {
    EVP_cleanup();
}

std::string Crypto::hash_sha256(const std::string& data) {
    unsigned char hash[SHA256_DIGEST_LENGTH];
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();

    if (!ctx) {
        throw std::runtime_error("Failed to create EVP context");
    }

    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, data.c_str(), data.size());
    EVP_DigestFinal_ex(ctx, hash, nullptr);
    EVP_MD_CTX_free(ctx);

    std::string result;
    result.reserve(SHA256_DIGEST_LENGTH * 2);
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        result += fmt::format("{:02x}", hash[i]);
    }

    return result;
}

std::string Crypto::encrypt_aes_256(const std::string& plaintext, const std::string& key) {
    if (key.size() != 32) {
        throw std::invalid_argument("Key must be 32 bytes for AES-256");
    }

    unsigned char iv[16];
    if (RAND_bytes(iv, sizeof(iv)) != 1) {
        throw std::runtime_error("Failed to generate IV");
    }

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        throw std::runtime_error("Failed to create cipher context");
    }

    EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr,
                       reinterpret_cast<const unsigned char*>(key.c_str()), iv);

    std::vector<unsigned char> ciphertext(plaintext.size() + EVP_CIPHER_block_size(EVP_aes_256_cbc()));
    int len = 0;
    int ciphertext_len = 0;

    EVP_EncryptUpdate(ctx, ciphertext.data(), &len,
                      reinterpret_cast<const unsigned char*>(plaintext.c_str()),
                      plaintext.size());
    ciphertext_len = len;

    EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len);
    ciphertext_len += len;

    EVP_CIPHER_CTX_free(ctx);

    ciphertext.resize(ciphertext_len);

    // Prepend IV to ciphertext
    std::string result(reinterpret_cast<char*>(iv), sizeof(iv));
    result.append(reinterpret_cast<char*>(ciphertext.data()), ciphertext_len);

    return result;
}

std::string Crypto::decrypt_aes_256(const std::string& ciphertext, const std::string& key) {
    if (key.size() != 32) {
        throw std::invalid_argument("Key must be 32 bytes for AES-256");
    }

    if (ciphertext.size() < 16) {
        throw std::invalid_argument("Ciphertext too short");
    }

    const unsigned char* iv = reinterpret_cast<const unsigned char*>(ciphertext.c_str());
    const unsigned char* enc_data = reinterpret_cast<const unsigned char*>(ciphertext.c_str() + 16);
    int enc_len = ciphertext.size() - 16;

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        throw std::runtime_error("Failed to create cipher context");
    }

    EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr,
                       reinterpret_cast<const unsigned char*>(key.c_str()), iv);

    std::vector<unsigned char> plaintext(enc_len + EVP_CIPHER_block_size(EVP_aes_256_cbc()));
    int len = 0;
    int plaintext_len = 0;

    EVP_DecryptUpdate(ctx, plaintext.data(), &len, enc_data, enc_len);
    plaintext_len = len;

    EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len);
    plaintext_len += len;

    EVP_CIPHER_CTX_free(ctx);

    return std::string(reinterpret_cast<char*>(plaintext.data()), plaintext_len);
}

nlohmann::json Crypto::generate_report(const std::string& operation, bool success) {
    return nlohmann::json{
        {"operation", operation},
        {"success", success},
        {"timestamp", fmt::format("{:%Y-%m-%dT%H:%M:%S}", fmt::localtime(std::time(nullptr)))},
        {"library", "projeto-seguro"},
        {"version", "1.0.0"}
    };
}

}  // namespace seguranca
```

```cpp
// src/main.cpp
#include <iostream>
#include <string>
#include "crypto.h"
#include <fmt/format.h>
#include <spdlog/spdlog.h>

int main() {
    spdlog::set_level(spdlog::level::info);

    try {
        seguranca::Crypto crypto;

        // Hash
        std::string data = "Hello, Seguranca!";
        std::string hash = crypto.hash_sha256(data);
        fmt::print("SHA-256: {}\n", hash);

        // Encrypt/Decrypt
        std::string key(32, 'k');
        std::string encrypted = crypto.encrypt_aes_256(data, key);
        std::string decrypted = crypto.decrypt_aes_256(encrypted, key);

        fmt::print("Original:  {}\n", data);
        fmt::print("Decrypted: {}\n", decrypted);

        // Report
        auto report = crypto.generate_report("encryption", true);
        fmt::print("Report: {}\n", report.dump(2));

        return 0;
    } catch (const std::exception& e) {
        spdlog::error("Error: {}", e.what());
        return 1;
    }
}
```

```cpp
// test/test_crypto.cpp
#include <catch2/catch_test_macros.hpp>
#include "crypto.h"

TEST_CASE("SHA-256 hashing", "[crypto]") {
    seguranca::Crypto crypto;

    std::string hash = crypto.hash_sha256("hello");
    REQUIRE(hash.length() == 64);
    REQUIRE(hash == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824");
}

TEST_CASE("AES-256 encrypt/decrypt", "[crypto]") {
    seguranca::Crypto crypto;

    std::string key(32, 'a');
    std::string plaintext = "Teste de criptografia";
    std::string encrypted = crypto.encrypt_aes_256(plaintext, key);
    std::string decrypted = crypto.decrypt_aes_256(encrypted, key);

    REQUIRE(decrypted == plaintext);
    REQUIRE(encrypted != plaintext);
}

TEST_CASE("Report generation", "[crypto]") {
    seguranca::Crypto crypto;

    auto report = crypto.generate_report("test", true);
    REQUIRE(report["operation"] == "test");
    REQUIRE(report["success"] == true);
    REQUIRE(report.contains("timestamp"));
}
```

### 12.8 CI/CD

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  VCPKG_ROOT: ${{ github.workspace }}/vcpkg

jobs:
  build-vcpkg:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup vcpkg
        uses: lukka/run-vcpkg@v11

      - name: Configure
        run: cmake --preset default

      - name: Build
        run: cmake --build --preset default

      - name: Test
        run: ctest --preset default

      - name: Audit dependencies
        run: |
          go install github.com/google/osv-scanner/cmd/osv-scanner@latest
          osv-scanner --lockfile=vcpkg-lock.json

  build-conan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Conan
        run: pip install conan

      - name: Detect profile
        run: conan profile detect --force

      - name: Install dependencies
        run: conan install . --output-folder=build --build=missing --lockfile=conan.lock

      - name: Configure
        run: cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release

      - name: Build
        run: cmake --build build

      - name: Test
        run: ctest --test-dir build
```

---

## 13. Exercicios

### Exercicio 1: Configuracao Basica de vcpkg

**Objetivo**: Configurar um projeto basico com vcpkg.

**Instrucoes**:
1. Crie um projeto CMake com `vcpkg.json` declarando `nlohmann-json` e `fmt`
2. Configure o CMake para usar vcpkg
3. Crie um programa que le um JSON e formata a saida com fmt
4. Valide que o build funciona

**Criterio de aceite**:
- `vcpkg.json` esta versionado no repositorio
- Build funciona com `cmake --preset default`
- Programa le JSON e formata corretamente

### Exercicio 2: Custom Triplet com Hardening

**Objetivo**: Criar um triplet que aplique flags de seguranca.

**Instrucoes**:
1. Crie um triplet `x64-linux-hardened` com flags de hardening
2. Configure `CMAKE_TOOLCHAIN_FILE` e `VCPKG_TARGET_TRIPLET`
3. Compile o projeto do Exercicio 1 com o triplet hardened
4. Verifique as flags com `readelf -d` ou `checksec`

**Criterio de aceite**:
- Triplet personalizado em `cmake/triplets/`
- Binario tem RELRO, stack canary, PIE habilitados
- Documentacao de como usar o triplet

### Exercicio 3: Migracao para Conan

**Objetivo**: Implementar o mesmo projeto usando Conan em vez de vcpkg.

**Instrucoes**:
1. Crie `conanfile.py` com as mesmas dependencias do Exercicio 1
2. Configure perfis para Release e Debug
3. Implemente o build com `conan install` + CMake
4. Compare o tempo de build com vcpkg

**Criterio de aceite**:
- `conanfile.py` implementado corretamente
- Perfis configurados em `~/.conan2/profiles/`
- Build funciona com ambos os perfis
- Documentacao do comparativo de performance

### Exercicio 4: Lock Files e Reprodutibilidade

**Objetivo**: Implementar lock files para builds reproduziveis.

**Instrucoes**:
1. Gere `vcpkg-lock.json` para o projeto vcpkg
2. Gere `conan.lock` para o projeto Conan
3. Adicione ambos ao repositorio Git
4. Simule uma atualizacao de dependencia e verifique que o lock file previne mudancas

**Criterio de aceite**:
- Ambos os lock files gerados e versionados
- Build e identico em dois runs consecutivos
- Documentacao do processo de atualizacao

### Exercicio 5: Auditoria de Dependencias

**Objetivo**: Implementar auditoria automatizada de dependencias.

**Instrucoes**:
1. Instale `osv-scanner`
2. Execute auditoria no projeto com vcpkg-lock.json
3. Crie script que verifica vulnerabilidades criticas
4. Adicione o script ao CI/CD

**Criterio de aceite**:
- Script de auditoria funcional
- CI/CD falha se houver vulnerabilidades criticas
- Relatorio de auditoria gerado

### Exercicio 6: Binary Caching com Azure

**Objetivo**: Configurar binary caching remoto.

**Instrucoes**:
1. Configure um container Azure Blob para cache
2. Configure `VCPKG_BINARY_SOURCES` para usar o cache
3. Execute o build duas vezes e meca o tempo
4. Documente a configuracao

**Criterio de aceite**:
- Cache configurado e funcional
- Segundo build e significativamente mais rapido
- Documentacao da configuracao e seguranca

### Exercicio 7: Projeto Completo com Ambos Gerenciadores

**Objetivo**: Criar projeto que suporte vcpkg e Conan simultaneamente.

**Instrucoes**:
1. Implemente o projeto do Exercicio 12
2. Crie presets para ambos os gerenciadores
3. Implemente CI/CD que testa ambos
4. Gere SBOM para ambos

**Criterio de aceite**:
- Ambos os presets funcionam
- CI/CD executa build com vcpkg e Conan
- SBOM gerado para ambos
- Documentacao completa do setup

---

## 14. Referencias

### Documentacao Oficial

- [vcpkg Documentation](https://learn.microsoft.com/en-us/vcpkg/)
- [vcpkg Manifest Mode](https://learn.microsoft.com/en-us/vcpkg/concepts/manifest-mode)
- [Conan 2.x Documentation](https://docs.conan.io/2/)
- [Conan CMake Integration](https://docs.conan.io/2/reference/tools/cmake.html)

### Seguranca e Supply Chain

- [SLSA Framework](https://slsa.dev/)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- [OSV-Scanner](https://google.github.io/osv-scanner/)
- [Sigstore](https://www.sigstore.dev/)
- [cosign](https://docs.sigstore.dev/cosign/overview/)

### Casos de Estudo

- CVE-2024-3094: XZ Utils Backdoor — Analise de supply chain attack
- CVE-2021-44228: Log4Shell — Dependencias de terceiros em producao
- A2A: Account Takeover via dependency confusion
- Event-stream incident: Risks of package ownership transfer

### Artigos e Papers

- "The Dos and Don'ts of Dependency Management" — SEI CERT
- "Supply Chain Security Best Practices" — NIST SP 800-218
- "Reproducible Builds" — Reproducible-builds.org
- "Binary Transparency for Package Managers" — Google Research

---

*[Capitulo 12 — SBOM e Supply Chain Security](12-sbom-supply-chain.md)*
