---
layout: default
title: "Capitulo 12 — SBOM e Supply Chain Security"
---

# Capitulo 12 — SBOM e Supply Chain Security

> *"A cadeia de suprimentos de software e apenas tão segura quanto seu elo mais fraco. Um SBOM transforma esse elo invisível em uma cadeia auditável."*

---

## Sumario

- [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
- [O que e um SBOM](#2-o-que-e-um-sbom)
- [SPDX: formato, campos obrigatorios](#3-spdx-formato-campos-obrigatorios)
- [CycloneDX: formato, XML/JSON](#4-cyclonedx-formato-xmljson)
- [Geracao de SBOM: syft, cdxgen, spdx-tools](#5-geracao-de-sbom-syft-cdxgen-spdx-tools)
- [SBOM para projetos C++](#6-sbom-para-projetos-c)
- [Sigstore: signing, verification](#7-sigstore-signing-verification)
- [Cosign: artifact signing](#8-cosign-artifact-signing)
- [SLSA: Supply chain Levels](#9-slsa-supply-chain-levels)
- [in-toto: supply chain integrity](#10-in-toto-supply-chain-integrity)
- [Dependabot/Renovate para C++](#11-dependabotrenovate-para-c)
- [CVE-2024-3094 post-mortem](#12-cve-2024-3094-post-mortem)
- [Exemplo: pipeline com SBOM](#13-exemplo-pipeline-com-sbom)
- [Exercicios](#14-exercicios)
- [Referencias](#15-referencias)

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Definir o que e um Software Bill of Materials (SBOM) e por que ele e essencial para seguranca de software.
2. Diferenciar os formatos SPDX e CycloneDX, incluindo seus campos obrigatorios e uso recomendado.
3. Gerar SBOMs para projetos C++ usando ferramentas como syft, cdxgen e spdx-tools.
4. Integrar geracao de SBOM em pipelines CMake de forma automatizada e auditavel.
5. Entender os conceitos de signing e verification usando Sigstore e Cosign.
6. Classificar niveis de maturidade de supply chain usando o framework SLSA.
7. Aplicar o framework in-toto para garantir integridade da cadeia de suprimentos.
8. Configurar Dependabot ou Renovate para gerenciamento automatizado de dependencias C++.
9. Analisar o post-mortem do CVE-2024-3094 (XZ Utils) como estudo de caso real.
10. Construir uma pipeline completa com SBOM, signing e verificacao para projetos CMake.

### Por que este capitulo e critico para seguranca

A cadeia de suprimentos de software se tornou o alvo preferido de atacantes nos ultimos anos. Em vez de atacar diretamente o codigo-fonte de uma aplicacao, um invasor pode comprometer uma dependencia, uma ferramenta de build, ou ate mesmo o repositorio de um projeto open-source. Estes ataques sao especialmente perigosos porque:

- Exploram a confianca implicita que desenvolvedores depositam em dependencias de terceiros
- Podem permanecer indetectados por meses ou anos antes de serem descobertos
- Afetam milhoes de usuarios simultaneamente quando a dependencia e amplamente utilizada
- Sao dificeis de detectar usando apenas analise estatica de codigo

O SBOM resolve metade desse problema ao tornar transparente o que esta incluido no software. A outra metade e resolvida por mecanismos de signing, verificacao e integridade que veremos ao longo deste capitulo.

### Contexto dentro da serie

Este capitulo se conecta com varios conceitos abordados anteriormente na serie:

- **Capitulos anteriores de CMake**: Aqui veremos como integrar geracao de SBOM no proprio build system
- **Capitulos de seguranca**: O SBOM complementa analise de vulnerabilidades e hardening de compilacao
- **Capitulos de CI/CD**: As pipelines mostradas aqui usam os conceitos de build automatizado ja estabelecidos

---

## 2. O que e um SBOM

### 2.1 Definicao formal

Um Software Bill of Materials (SBOM) e uma lista estruturada e machine-readable de todos os componentes, bibliotecas e modulos que compoem um software. Assim como um BoM em engenharia mecanica lista todas as pecas de uma maquina, um SBOM lista todas as pecas de um software.

Segundo a NIST (National Institute of Standards and Technology), um SBOM deve conter:

- O nome de cada componente ou biblioteca utilizado
- A versao exata de cada componente
- O fornecedor ou maintainers de cada componente
- As licencas associadas a cada componente
- As relacoes de dependencia entre componentes
- Identificadores unicos quando disponiveis (CPE, PURL, SWID)

### 2.2 Por que SBOM se tornou obrigatorio

Em maio de 2021, o Executive Order 14028 do governo dos Estados Unidos estabeleceu requisitos rigorosos para seguranca de software em entidades governamentais. O documento exigiu:

1. Desenvolvedores de software fornecem SBOMs para todos os produtos vendidos ao governo
2. As agencias governamentais mantem registro de SBOMs para todos os softwares em producao
3. Os SBOMs devem ser atualizados sempre que houver mudancas nas dependencias

Desde entao, a Uniao Europeia, Japao, Australia e outros paises adotaram requisitos semelhantes. O SBOM deixou de ser opcional em muitos mercados regulados.

### 2.3 Tipos de SBOM

Existem tres tipos principais de SBOM, cada um com objetivo distinto:

**SBOM de Composicao (Composition)**
Lista todos os componentes presentes no software final. Este e o tipo mais comum e inclui bibliotecas estaticas, dinamicas, headers e ferramentas de build.

**SBOM de Dependencia (Dependency)**
Mapeia apenas as dependencias diretas e transitivas. Util para analise de vulnerabilidade e gestao de licencas.

**SBOM de Vulnerabilidade (Vulnerability)**
Enriquece o SBOM de composicao com dados de CVEs, severidade e status de remedicao. Util para resposta a incidentes e compliance.

### 2.4 SBOM nao e o mesmo que lockfile

Uma confusao comum e equiparar SBOM a arquivos como `package-lock.json`, `conanfile.txt` ou `vcpkg.json`. A diferenca e fundamental:

| Aspecto | Lockfile | SBOM |
|---------|----------|------|
| Escopo | Dependencias gerenciadas pelo gerenciador de pacotes | TODOS os componentes, incluindo transientes |
| Formato | Especifico do ecossistema | Padronizado (SPDX, CycloneDX) |
| Auditoria | Limitada | Completa, machine-readable |
| Uso legal | Insuficiente em muitos mercados | Atende requisitos regulatórios |
| Dependencias transientes | Parcialmente cobertas | Totalmente cobertas |

Um lockfile e uma entrada para um SBOM, mas nao substitui um.

### 2.5 Beneficios concretos do SBOM

**Visibilidade de Dependencias**
O SBOM revela exatamente o que esta dentro do seu software. Muitos projetos C++ descobrem, ao gerar seu primeiro SBOM, que possuem centenas de dependencias transientes que nao sabiam existir.

**Resposta Rapida a CVEs**
Quando uma nova vulnerabilidade e descoberta, o SBOM permite identificar imediatamente quais sistemas afetados. Sem SBOM, a equipe precisa rastrear manualmente cada dependencia em cada projeto.

**Compliance Regulatorio**
Em setores como saude (FDA), financeiro (FINRA) e defesa (DoD), o SBOM e frequentemente exigido para certificacao e auditoria.

**Gestao de Licencas**
O SBOM revela conflitos de licenca (GPL em software proprietario, por exemplo) antes que se tornem problemas legais.

**Auditoria Forense**
Em caso de incidente de seguranca, o SBOM fornece o inventario exato do software para investigacao.

### 2.6 O ciclo de vida de um SBOM

Um SBOM nao e um documento estatico gerado uma vez. Seu ciclo de vida inclui:

1. **Geracao**: Criado durante o build ou em pipeline CI/CD
2. **Validacao**: Verificado contra padroes (SPDX, CycloneDX) e completude
3. **Distribuicao**: Compartilhado com consumidores (clientes, parceiros, agencias)
4. **Atualizacao**: Regenerado sempre que dependencias mudam
5. **Consumo**: Utilizado por ferramentas de analise de vulnerabilidade e compliance
6. **Arquivamento**: Mantido para auditoria historica e rastreabilidade

### 2.7 SBOM e seguranca de compilacao

Integrar SBOM com seguranca de compilacao cria uma cadeia de confianca completa:

- O SBOM lista o que esta no software
- A analise de vulnerabilidade identifica riscos nesses componentes
- O signing garante que o SBOM e os binarios nao foram adulterados
- A verificacao confirma que a cadeia de confianca nao foi quebrada em nenhum ponto

Esta integracao e o tema central deste capitulo.

---

## 3. SPDX: formato, campos obrigatorios

### 3.1 Historia e contexto do SPDX

SPDX (Software Package Data Exchange) e um padrao aberto para comunicacao de informacoes sobre software, incluindo componentes, licencas e direitos autorais. Foi criado em 2010 pela Linux Foundation como resposta a necessidade de um formato padronizado para troca de informacoes sobre composicao de software.

O SPDX se tornou o padrao ISO 26200 (ISO/IEC 5962:2021) e e amplamente utilizado em ecosistemas open-source e corporativos.

### 3.2 Estrutura basica de um documento SPDX

Um documento SPDX consiste em:

- **Document Creation Information**: Metadados sobre o proprio documento
- **Package Information**: Informacoes sobre cada componente
- **File Information**: Informacoes sobre arquivos especificos (opcional)
- **Snippet Information**: Trechos de arquivos (opcional)
- **Relationship Information**: Relacoes entre pacotes
- **Annotation Information**: Comentarios e anotacoes
- **External Document References**: Links para documentos externos

### 3.3 Campos obrigatorios do SPDX

Segundo a especificacao SPDX 2.3, os campos obrigatorios sao:

**Document Creation Section (obrigatoria)**

```
SPDXID: SPDXRef-DOCUMENT
SpdxVersion: SPDX-2.3
DataLicense: CC0-1.0
SPDXDocumentName: <nome do documento>
Creator: <tool, person ou organization>
Created: <timestamp ISO 8601>
DocumentNamespace: <URI unica>
```

**Package Section (obrigatoria para cada pacote)**

```
PackageName: <nome do pacote>
SPDXID: SPDXRef-Package-<nome>
PackageVersion: <versao>
PackageSupplier: <supplier>
PackageDownloadLocation: <URL>
FilesAnalyzed: <true ou false>
PackageCopyrightText: <texto ou NOASSERTION>
PackageLicenseConcluded: <licenca ou NOASSERTION>
PackageLicenseDeclared: <licenca ou NOASSERTION>
PackageVerificationCode: <hash>
```

### 3.4 Exemplo de documento SPDX para um projeto C++

```spdx
SPDXVersion: SPDX-2.3
DataLicense: CC0-1.0
SPDXID: SPDXRef-DOCUMENT
DocumentName: my-project-sbom
DocumentNamespace: https://example.com/my-project/sbom/v1
Creator: Tool: cdxgen-2.0.0
Created: 2024-11-15T10:30:00Z

PackageName: my-project
SPDXID: SPDXRef- Package-my-project
PackageVersion: 1.0.0
PackageSupplier: Organization: My Company
PackageDownloadLocation: https://github.com/mycompany/my-project/archive/refs/tags/v1.0.0.tar.gz
FilesAnalyzed: true
PackageVerificationCode: 8a3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b
PackageCopyrightText: Copyright 2024 My Company
PackageLicenseConcluded: Apache-2.0
PackageLicenseDeclared: Apache-2.0

PackageName: openssl
SPDXID: SPDXRef- Package-openssl
PackageVersion: 3.2.0
PackageSupplier: Organization: OpenSSL Software Foundation
PackageDownloadLocation: https://www.openssl.org/source/openssl-3.2.0.tar.gz
FilesAnalyzed: false
PackageVerificationCode: d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3
PackageCopyrightText: Copyright 2000-2024 The OpenSSL Project
PackageLicenseConcluded: Apache-2.0
PackageLicenseDeclared: Apache-2.0

PackageName: zlib
SPDXID: SPDXRef- Package-zlib
PackageVersion: 1.3.1
PackageSupplier: Organization: zlib Authors
PackageDownloadLocation: https://zlib.net/fossils/zlib-1.3.1.tar.gz
FilesAnalyzed: false
PackageVerificationCode: b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0
PackageCopyrightText: Copyright 1995-2024 Jean-loup Gailly and Mark Adler
PackageLicenseConcluded: Zlib
PackageLicenseDeclared: Zlib

Relationship: SPDXRef-Package-my-project DEPENDS_ON SPDXRef-Package-openssl
Relationship: SPDXRef-Package-my-project DEPENDS_ON SPDXRef-Package-zlib
```

### 3.5 Formatos de serializacao do SPDX

O SPDX suporta tres formatos de serializacao:

**SPDX Tag-Value**
Formato textual simples, facil de ler e escrever. Ideal para revisao manual.

```
SPDXID: SPDXRef-Package-openssl
PackageName: openssl
PackageVersion: 3.2.0
```

**SPDX RDF/XML**
Formato XML baseado em RDF (Resource Description Framework). Util para integracao com ferramentas semanticas.

```xml
<spdx:Package rdf:about="...">
  <spdx:name>openssl</spdx:name>
  <spdx:versionInfo>3.2.0</spdx:versionInfo>
  <spdx:downloadLocation>...</spdx:downloadLocation>
</spdx:Package>
```

**SPDX JSON**
Formato JSON padronizado, amplamente suportado por ferramentas.

```json
{
  "spdxVersion": "SPDX-2.3",
  "dataLicense": "CC0-1.0",
  "SPDXID": "SPDXRef-DOCUMENT",
  "packages": [
    {
      "SPDXID": "SPDXRef-Package-openssl",
      "name": "openssl",
      "versionInfo": "3.2.0"
    }
  ]
}
```

### 3.6 Identificadores de pacotes no SPDX

O SPDX define varios esquemas de identificadores para pacotes:

**Package Verification Code**
Um hash SHA-1 dos arquivos do pacote, util para verificacao de integridade.

**External Document References**
Links para documentos SPDX externos que contêm informacoes adicionais.

**CPE (Common Platform Enumeration)**
Identificador padronizado para vulnerabilidades, no formato:
```
cpe:2.3:a:openssl:openssl:3.2.0:*:*:*:*:*:*:*
```

**PURL (Package URL)**
Identificador padronizado para localizacao de pacotes:
```
pkg:github/openssl/openssl@3.2.0
pkg:deb/ubuntu/openssl@3.2.0-1
```

### 3.7 Validacao de SPDX

A validacao de um documento SPDX e crucial para garantir que ele atenda aos padroes:

```bash
# Usando spdx-tools para validar
pip install spdx-tools

# Validar um documento SPDX
python -m spdx tools validate --file my-project.spdx.json
```

```python
# Script de validacao customizado
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.validation.spdx_validator import validate_document

def validate_sbom(spdx_file):
    document = parse_file(spdx_file)
    validation_results = validate_document(document)
    
    for result in validation_results:
        if result.validation_message:
            print(f"Erro: {result.validation_message}")
        else:
            print("Documento valido")
    
    return validation_results
```

### 3.8 SPDX e CMake

O CMake nao gera SPDX nativamente, mas podemos integrar geracao de SPDX no build:

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Coletar informacoes para SBOM
set(SBOM_PROJECT_NAME ${PROJECT_NAME})
set(SBOM_VERSION ${PROJECT_VERSION})
set(SBOM_AUTHOR "My Company")
set(SBOM_LICENSE "Apache-2.0")

# Gerar SPDX durante o build
add_custom_target(generate_sbom
    COMMAND ${CMAKE_COMMAND} -E echo "Gerando SBOM SPDX..."
    COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/generate_spdx.py
        --project-name ${SBOM_PROJECT_NAME}
        --version ${SBOM_VERSION}
        --output ${CMAKE_BINARY_DIR}/${SBOM_PROJECT_NAME}-${SBOM_VERSION}.spdx.json
    DEPENDS ${PROJECT_NAME}
    COMMENT "Gerando SBOM SPDX"
)

add_dependencies(${PROJECT_NAME} generate_sbom)
```

### 3.9 Melhores praticas SPDX para projetos C++

1. **Gere SBOM automaticamente em cada build release**
2. **Valide o SBOM gerado contra a especificacao SPDX**
3. **Use Package URLs (PURL) para identificadores padronizados**
4. **Inclua o SBOM no artefato de release junto com os binarios**
5. **Mantenha historico de SBOMs para auditoria**
6. **Atualize o SBOM sempre que uma dependencia for atualizada**
7. **Use o campo PackageCopyrightText para compliance de licencas**

---

## 4. CycloneDX: formato, XML/JSON

### 4.1 Historia e contexto do CycloneDX

CycloneDX e um padrao aberto para SBOMs criado pela OWASP (Open Web Application Security Project) em 2017. Diferente do SPDX, que foca em comunicacao de informacoes sobre licencas e direitos autorais, CycloneDX foi projetado especificamente para seguranca e gestao de riscos.

O CycloneDX se tornou um padrao da industria para SBOMs orientados a seguranca, sendo adotado por ferramentas de analise de vulnerabilidade, scanners de seguranca e frameworks de compliance.

### 4.2 Estrutura do CycloneDX

Um documento CycloneDX consiste em:

- **Metadata**: Informacoes sobre o SBOM (timestamp, ferramenta, fornecedor)
- **Components**: Lista de componentes do software
- **Services**: Servicos externos utilizados
- **Dependencies**: Grafo de dependencias
- **Compositions**: Composicao de componentes
- **External References**: Links para informacoes externas
- **Vulnerabilities**: Vulnerabilidades conhecidas (enriquecimento)
- **Supply Chain**: Informacoes de cadeia de suprimentos

### 4.3 Campos obrigatorios do CycloneDX

**Metadata Section (obrigatoria)**

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  "version": 1,
  "metadata": {
    "timestamp": "2024-11-15T10:30:00Z",
    "tools": [
      {
        "vendor": "OWASP",
        "name": "CycloneDX CLI",
        "version": "0.24.0"
      }
    ],
    "component": {
      "type": "application",
      "name": "my-project",
      "version": "1.0.0",
      "bom-ref": "my-project-1.0.0"
    }
  }
}
```

**Components Section (obrigatoria para cada componente)**

```json
{
  "components": [
    {
      "type": "library",
      "name": "openssl",
      "version": "3.2.0",
      "bom-ref": "openssl-3.2.0",
      "purl": "pkg:github/openssl/openssl@3.2.0",
      "licenses": [
        {
          "license": {
            "id": "Apache-2.0"
          }
        }
      ],
      "externalReferences": [
        {
          "type": "website",
          "url": "https://www.openssl.org/"
        },
        {
          "type": "distribution",
          "url": "https://www.openssl.org/source/openssl-3.2.0.tar.gz"
        }
      ]
    }
  ]
}
```

### 4.4 Exemplo completo CycloneDX JSON para projeto C++

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  "version": 1,
  "metadata": {
    "timestamp": "2024-11-15T10:30:00Z",
    "tools": [
      {
        "vendor": "OWASP",
        "name": "CycloneDX CLI",
        "version": "0.24.0"
      }
    ],
    "component": {
      "type": "application",
      "name": "my-project",
      "version": "1.0.0",
      "bom-ref": "my-project-1.0.0",
      "author": "My Company",
      "supplier": {
        "name": "My Company",
        "url": ["https://example.com"]
      },
      "licenses": [
        {
          "license": {
            "id": "Apache-2.0"
          }
        }
      ]
    }
  },
  "components": [
    {
      "type": "library",
      "name": "openssl",
      "version": "3.2.0",
      "bom-ref": "openssl-3.2.0",
      "purl": "pkg:github/openssl/openssl@3.2.0",
      "cpe": "cpe:2.3:a:openssl:openssl:3.2.0:*:*:*:*:*:*:*",
      "licenses": [
        {
          "license": {
            "id": "Apache-2.0"
          }
        }
      ],
      "externalReferences": [
        {
          "type": "website",
          "url": "https://www.openssl.org/"
        }
      ]
    },
    {
      "type": "library",
      "name": "zlib",
      "version": "1.3.1",
      "bom-ref": "zlib-1.3.1",
      "purl": "pkg:generic/zlib/zlib@1.3.1",
      "cpe": "cpe:2.3:a:zlib:zlib:1.3.1:*:*:*:*:*:*:*",
      "licenses": [
        {
          "license": {
            "id": "Zlib"
          }
        }
      ]
    },
    {
      "type": "library",
      "name": "fmt",
      "version": "10.2.1",
      "bom-ref": "fmt-10.2.1",
      "purl": "pkg:github/fmtlib/fmt@10.2.1",
      "cpe": "cpe:2.3:a:fmtlib:fmt:10.2.1:*:*:*:*:*:*:*",
      "licenses": [
        {
          "license": {
            "id": "MIT"
          }
        }
      ]
    },
    {
      "type": "library",
      "name": "spdlog",
      "version": "1.13.0",
      "bom-ref": "spdlog-1.13.0",
      "purl": "pkg:github/gabime/spdlog@1.13.0",
      "cpe": "cpe:2.3:a:spdlog_project:spdlog:1.13.0:*:*:*:*:*:*:*",
      "licenses": [
        {
          "license": {
            "id": "MIT"
          }
        }
      ],
      "properties": [
        {
          "name": "internal:pedigree:commit",
          "value": "abc123def456"
        }
      ]
    }
  ],
  "dependencies": [
    {
      "ref": "my-project-1.0.0",
      "dependsOn": [
        "openssl-3.2.0",
        "zlib-1.3.1",
        "fmt-10.2.1",
        "spdlog-1.13.0"
      ]
    },
    {
      "ref": "spdlog-1.13.0",
      "dependsOn": [
        "fmt-10.2.1"
      ]
    }
  ],
  "externalReferences": [
    {
      "type": "vcs",
      "url": "https://github.com/mycompany/my-project"
    },
    {
      "type": "website",
      "url": "https://example.com/my-project"
    }
  ]
}
```

### 4.5 CycloneDX XML vs JSON

O CycloneDX suporta ambos XML e JSON. A escolha depende do contexto:

| Aspecto | XML | JSON |
|---------|-----|------|
| Legibilidade humana | Media | Alta |
| Tamanho do arquivo | Maior | Menor |
| Parsing programatico | Mais complexo | Mais simples |
| Suporte a ferramentas | Excelente | Excelente |
| Validacao (XSD/Schema) | XSD disponivel | Schema disponivel |
| Integracao web | Completa | Completa |

**Recomendacao**: Use JSON para integracao com ferramentas automatizadas e XML quando precisar de validacao XSD ou integracao com sistemas legados.

### 4.6 Propriedades e Metadados Customizados

O CycloneDX permite adicionar propriedades customizadas para enriquecer o SBOM:

```json
{
  "properties": [
    {
      "name": "internal:security:criticality",
      "value": "high",
      "description": "Criticalidade de seguranca do componente"
    },
    {
      "name": "internal:security:patch-status",
      "value": "patched",
      "description": "Status de patches de seguranca"
    },
    {
      "name": "internal:compliance:export-controlled",
      "value": "false",
      "description": "Controle de exportacao"
    }
  ]
}
```

### 4.7 Vulnerabilidades no CycloneDX

O CycloneDX pode incluir informacoes de vulnerabilidade diretamente no SBOM:

```json
{
  "vulnerabilities": [
    {
      "id": "CVE-2024-12345",
      "source": {
        "name": "NVD",
        "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
      },
      "ratings": [
        {
          "source": {
            "name": "NVD"
          },
          "score": 9.8,
          "severity": "critical",
          "method": "CVSSv31"
        }
      ],
      "description": "Buffer overflow in OpenSSL",
      "published": "2024-11-10T00:00:00Z",
      "affected": [
        {
          "ref": "openssl-3.2.0",
          "versions": [
            {
              "version": "3.2.0",
              "lessThanOrEqual": "3.2.0"
            }
          ]
        }
      ],
      "recommendations": [
        {
          "url": "https://www.openssl.org/news/secadv/20241110.txt"
        }
      ]
    }
  ]
}
```

### 4.8 CycloneDX e CMake

Integrar CycloneDX no CMake:

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Configurar SBOM
set(SBOM_FORMAT "json" CACHE STRING "Formato do SBOM (json ou xml)")
set(SBOM_OUTPUT "${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.${SBOM_FORMAT}")

# Detectar ferramenta de geracao de SBOM
find_program(CDXGEN_EXECUTABLE cdxgen)
find_program(CYCLONEDX_EXECUTABLE cyclonedx)

if(CDXGEN_EXECUTABLE)
    set(SBOM_TOOL ${CDXGEN_EXECUTABLE})
    set(SBOM_ARGS --output-file ${SBOM_OUTPUT})
elseif(CYCLONEDX_EXECUTABLE)
    set(SBOM_TOOL ${CYCLONEDX_EXECUTABLE})
    set(SBOM_ARGS --output-file ${SBOM_OUTPUT} --output-format ${SBOM_FORMAT})
else()
    message(WARNING "Nenhuma ferramenta CycloneDX encontrada. Instale cdxgen ou cyclonedx-cli.")
endif()

# Target para gerar SBOM
add_custom_target(generate-sbom
    COMMAND ${SBOM_TOOL} ${SBOM_ARGS}
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Gerando CycloneDX SBOM"
    VERBATIM
)

# Target para validar SBOM
add_custom_target(validate-sbom
    COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/validate_cyclonedx.py
        --input ${SBOM_OUTPUT}
    DEPENDS generate-sbom
    COMMENT "Validando CycloneDX SBOM"
)
```

### 4.9 Melhores praticas CycloneDX

1. **Use especificacao 1.5 ou superior** para suporte completo a supply chain
2. **Inclua PURL e CPE** para cada componente (ambos quando possivel)
3. **Adicione propriedades customizadas** para metadados de seguranca internos
4. **Mantenha o serialNumber unico** para cada versao do SBOM
5. **Gere SBOM em pipeline CI/CD** e armazene como artefato
6. **Enriqueça com dados de vulnerabilidade** usando ferramentas como OWASP Dependency-Check
7. **Distribua o SBOM** junto com os binarios em cada release

---

## 5. Geracao de SBOM: syft, cdxgen, spdx-tools

### 5.1 Visao geral das ferramentas

Existem diversas ferramentas para geracao de SBOM, cada uma com pontos fortes diferentes:

| Ferramenta | Formatos Suportados | Linguagem | Pontos Fortes |
|-----------|---------------------|-----------|---------------|
| syft | SPDX, CycloneDX | Go | Velocidade, ampla deteccao |
| cdxgen | CycloneDX | Node.js | Profundidade de analise |
| spdx-tools | SPDX | Python | Validacao SPDX |
| trivy | SPDX, CycloneDX | Go | Integracao com scanning |
| bomber | CycloneDX | Go | Analise de vulnerabilidade |
| sbom-scorecard | N/A | Go | Avaliacao de qualidade SBOM |

### 5.2 syft: geracao rapida e completa

syft e uma ferramenta da Anchore para geracao de SBOMs. Ela suporta multiplos formatos e e especialmente forte em deteccao de pacotes de sistemas operacionais.

**Instalacao**

```bash
# Linux (amd64)
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# macOS
brew install syft

# Verificar versao
syft version
```

**Uso basico**

```bash
# Gerar SBOM para um diretorio
syft dir:./my-project -o spdx-json > my-project.spdx.json

# Gerar SBOM CycloneDX
syft dir:./my-project -o cyclonedx-json > my-project-bom.json

# Gerar SBOM para uma imagem Docker
syft docker:my-project:latest -o spdx-json > image-sbom.spdx.json

# Gerar SBOM com formato tag-value
syft dir:./my-project -o spdx-tag-value > my-project.spdx
```

**Configuracao via .syft.yaml**

```yaml
# .syft.yaml
output:
  - spdx-json
  - cyclonedx-json
  
file:
  cataloger:
    search:
      scope: all-layers
      
python:
  cataloger:
    search:
      scope: all-layers
      
javascript:
  cataloger:
    search:
      scope: all-layers

# Configuracoes de exclusao
exclude:
  - "**/test/**"
  - "**/tests/**"
  - "**/docs/**"
  - "**/examples/**"
```

**Exemplo de saida syft (SPDX JSON)**

```json
{
  "spdxVersion": "SPDX-2.3",
  "dataLicense": "CC0-1.0",
  "SPDXID": "SPDXRef-DOCUMENT",
  "documentName": "my-project-directory",
  "documentNamespace": "https://example.com/syft/my-project",
  "creationInfo": {
    "created": "2024-11-15T10:30:00Z",
    "creators": [
      "Tool: syft-0.95.0"
    ],
    "licenseListVersion": "3.22"
  },
  "packages": [
    {
      "name": "my-project",
      "SPDXID": "SPDXRef-Package-my-project",
      "versionInfo": "1.0.0",
      "packageFileName": "my-project-1.0.0",
      "supplier": "NOASSERTION",
      "downloadLocation": "NOASSERTION",
      "filesAnalyzed": true,
      "checksums": [
        {
          "algorithm": "SHA1",
          "checksumValue": "8a3b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b"
        }
      ],
      "licenseConcluded": "Apache-2.0",
      "licenseDeclared": "Apache-2.0",
      "copyrightText": "Copyright 2024 My Company"
    },
    {
      "name": "openssl",
      "SPDXID": "SPDXRef-Package-openssl",
      "versionInfo": "3.2.0",
      "supplier": "Organization: OpenSSL Software Foundation",
      "downloadLocation": "https://www.openssl.org/source/openssl-3.2.0.tar.gz",
      "filesAnalyzed": false,
      "licenseConcluded": "Apache-2.0",
      "licenseDeclared": "Apache-2.0",
      "externalRefs": [
        {
          "referenceCategory": "SECURITY",
          "referenceType": "cpe23Type",
          "referenceLocator": "cpe:2.3:a:openssl:openssl:3.2.0:*:*:*:*:*:*:*"
        },
        {
          "referenceCategory": "PACKAGE-MANAGER",
          "referenceType": "purl",
          "referenceLocator": "pkg:github/openssl/openssl@3.2.0"
        }
      ]
    }
  ]
}
```

### 5.3 cdxgen: analise profunda CycloneDX

cdxgen e uma ferramenta da OWASP para geracao de SBOMs CycloneDX com analise profunda de dependencias.

**Instalacao**

```bash
# Instalar globalmente
npm install -g @cyclonedx/cdxgen

# Ou usar npx
npx @cyclonedx/cdxgen

# Verificar versao
cdxgen --version
```

**Uso para projetos C++**

```bash
# Gerar SBOM para projeto C++
cdxgen --spec-version 1_5 -o bom.json -t c-cpp .

# Gerar SBOM com profundidade de analise
cdxgen --spec-version 1_5 -o bom.json -t c-cpp --deep . 

# Gerar SBOM com analise de composicao
cdxgen --spec-version 1_5 -o bom.json -t c-cpp --include-composition .

# Gerar SBOM CycloneDX XML
cdxgen --spec-version 1_5 -o bom.xml -t c-cpp --format xml .
```

**Configuracao via .cdxgen.json**

```json
{
  "specVersion": "1.5",
  "outputFormat": "json",
  "includeBomSerialNumber": true,
  "filter": {
    "exclude": [
      "**/test/**",
      "**/tests/**",
      "**/docs/**"
    ]
  },
  "defaults": {
    "production": true,
    "specVersion": "1_5"
  }
}
```

**Exemplo de saida cdxgen**

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:550e8400-e29b-41d4-a716-446655440000",
  "version": 1,
  "metadata": {
    "timestamp": "2024-11-15T10:30:00Z",
    "tools": [
      {
        "vendor": "OWASP Foundation",
        "name": "cdxgen",
        "version": "10.2.0"
      }
    ],
    "component": {
      "type": "application",
      "name": "my-project",
      "version": "1.0.0",
      "bom-ref": "my-project-1.0.0"
    }
  },
  "components": [
    {
      "type": "library",
      "name": "openssl",
      "version": "3.2.0",
      "bom-ref": "openssl-3.2.0",
      "purl": "pkg:github/openssl/openssl@3.2.0",
      "cpe": "cpe:2.3:a:openssl:openssl:3.2.0:*:*:*:*:*:*:*",
      "licenses": [
        {
          "license": {
            "id": "Apache-2.0"
          }
        }
      ],
      "properties": [
        {
          "name": "cdxgen:foundBy",
          "value": "package-file-analysis"
        },
        {
          "name": "cdxgen:confidence",
          "value": "high"
        }
      ]
    }
  ],
  "dependencies": [
    {
      "ref": "my-project-1.0.0",
      "dependsOn": [
        "openssl-3.2.0"
      ]
    }
  ]
}
```

### 5.4 spdx-tools: validacao e manipulacao SPDX

spdx-tools e uma biblioteca Python para criacao, validacao e manipulacao de documentos SPDX.

**Instalacao**

```bash
# Instalar spdx-tools
pip install spdx-tools

# Ou com ferramentas adicionais
pip install spdx-tools[web]
```

**Script de geracao de SBOM SPDX**

```python
#!/usr/bin/env python3
"""
Gerador de SBOM SPDX para projetos C++
"""

import argparse
import json
import hashlib
import datetime
from pathlib import Path

from spdx_tools.spdx.model.document import (
    Document,
    CreationInfo,
    Package,
    File,
    Relationship,
    RelationshipType,
    SpdxNoAssertion,
    SpdxNone,
)
from spdx_tools.spdx.model.enums import (
    ChecksumAlgorithm,
    PackagePurpose,
    ExternalDocumentRefCategory,
)
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.writer.write_anything import write_file
from spdx_tools.spdx.validation.spdx_validator import validate_document


def calculate_verification_code(directory):
    """Calcula o Package Verification Code para um diretorio."""
    file_hashes = []
    
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            with open(file_path, "rb") as f:
                content = f.read()
                file_hash = hashlib.sha1(content).hexdigest()
                file_hashes.append(file_hash)
    
    if not file_hashes:
        return hashlib.sha1(b"").hexdigest()
    
    combined = "".join(sorted(file_hashes))
    return hashlib.sha1(combined.encode()).hexdigest()


def create_sbom(project_name, version, components, output_path):
    """Cria um documento SPDX para o projeto."""
    
    # Criar informacoes de criacao
    creation_info = CreationInfo(
        spdx_version="SPDX-2.3",
        data_license="CC0-1.0",
        spdx_id="SPDXRef-DOCUMENT",
        document_name=f"{project_name}-sbom",
        document_namespace=f"https://example.com/{project_name}/sbom/v1",
        creator_list=[f"Tool: spdx-tools"],
        created=datetime.datetime.now(datetime.timezone.utc),
    )
    
    # Criar pacote principal
    main_package = Package(
        name=project_name,
        spdx_id=f"SPDXRef-Package-{project_name}",
        version_info=version,
        download_location=SpdxNoAssertion(),
        files_analyzed=False,
        supplier=SpdxNoAssertion(),
        originator=SpdxNoAssertion(),
        copyright_text=f"Copyright {datetime.datetime.now().year} My Company",
        license_concluded=SpdxNoAssertion(),
        license_declared=SpdxNoAssertion(),
    )
    
    # Adicionar componentes
    packages = [main_package]
    relationships = []
    
    for component in components:
        pkg = Package(
            name=component["name"],
            spdx_id=f"SPDXRef-Package-{component['name']}",
            version_info=component["version"],
            download_location=component.get("download_location", SpdxNoAssertion()),
            files_analyzed=False,
            supplier=SpdxNoAssertion(),
            originator=SpdxNoAssertion(),
            copyright_text=component.get("copyright", SpdxNoAssertion()),
            license_concluded=component.get("license", SpdxNoAssertion()),
            license_declared=component.get("license", SpdxNoAssertion()),
        )
        packages.append(pkg)
        
        # Criar relacao de dependencia
        rel = Relationship(
            spdx_element_id=f"SPDXRef-Package-{project_name}",
            relationship_type=RelationshipType.DEPENDS_ON,
            related_spdx_element=f"SPDXRef-Package-{component['name']}",
        )
        relationships.append(rel)
    
    # Criar documento
    document = Document(
        creation_info=creation_info,
        packages=packages,
        relationships=relationships,
    )
    
    # Validar documento
    validation_results = validate_document(document)
    if validation_results:
        print("Avisos de validacao:")
        for result in validation_results:
            print(f"  - {result.validation_message}")
    
    # Salvar documento
    write_file(document, output_path)
    print(f"SBOM salvo em: {output_path}")
    
    return document


def main():
    parser = argparse.ArgumentParser(description="Gerador de SBOM SPDX")
    parser.add_argument("--project-name", required=True, help="Nome do projeto")
    parser.add_argument("--version", required=True, help="Versao do projeto")
    parser.add_argument("--components", required=True, help="Arquivo JSON com componentes")
    parser.add_argument("--output", required=True, help="Arquivo de saida")
    
    args = parser.parse_args()
    
    # Carregar componentes
    with open(args.components) as f:
        components = json.load(f)
    
    # Gerar SBOM
    create_sbom(args.project_name, args.version, components, args.output)


if __name__ == "__main__":
    main()
```

### 5.5 Comparacao detalhada das ferramentas

| Caracteristica | syft | cdxgen | spdx-tools |
|---------------|------|--------|------------|
| Velocidade | Alta | Media | Baixa |
| Deteccao de pacotes OS | Excelente | Boa | Limitada |
| Deteccao de pacotes build | Boa | Excelente | Boa |
| Formatos de saida | SPDX, CycloneDX | CycloneDX | SPDX |
| Analise profunda | Parcial | Excelente | N/A |
| Integracao Docker | Excelente | Parcial | Limitada |
| Customizacao | Media | Alta | Alta |
| Validacao | Parcial | Parcial | Excelente |
| Uso recomendado | CI/CD, container | Desenvolvimento | Validacao SPDX |

### 5.6 Estrategia de geracao de SBOM recomendada

Para projetos C++, recomenda-se a seguinte estrategia:

1. **Durante desenvolvimento**: Use cdxgen para analise profunda de dependencias
2. **Em pipeline CI/CD**: Use syft para geracao rapida e multi-formato
3. **Para compliance**: Use spdx-tools para validacao e manipulacao SPDX
4. **Para scanning**: Use trivy para integracao com analise de vulnerabilidade

### 5.7 Automacao com CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Configuracao de SBOM
option(GENERATE_SBOM "Gerar SBOM durante o build" ON)
option(SBOM_FORMAT "Formato do SBOM (spdx-json, cyclonedx-json)" "cyclonedx-json")

# Detectar ferramentas
find_program(SYFT_EXECUTABLE syft)
find_program(CDXGEN_EXECUTABLE cdxgen)
find_program(TRIVY_EXECUTABLE trivy)

# Configurar ferramenta de SBOM
if(SYFT_EXECUTABLE)
    set(SBOM_TOOL ${SYFT_EXECUTABLE})
    set(SBOM_TOOL_NAME "syft")
elseif(CDXGEN_EXECUTABLE)
    set(SBOM_TOOL ${CDXGEN_EXECUTABLE})
    set(SBOM_TOOL_NAME "cdxgen")
elseif(TRIVY_EXECUTABLE)
    set(SBOM_TOOL ${TRIVY_EXECUTABLE})
    set(SBOM_TOOL_NAME "trivy")
else()
    message(WARNING "Nenhuma ferramenta SBOM encontrada. Geracao de SBOM desabilitada.")
    set(GENERATE_SBOM OFF)
endif()

# Definir formato de saida
if(SBOM_FORMAT STREQUAL "spdx-json")
    set(SBOM_OUTPUT_FLAG "-o" "spdx-json")
    set(SBOM_EXTENSION "spdx.json")
elseif(SBOM_FORMAT STREQUAL "cyclonedx-json")
    set(SBOM_OUTPUT_FLAG "-o" "cyclonedx-json")
    set(SBOM_EXTENSION "bom.json")
else()
    message(FATAL_ERROR "Formato SBOM invalido: ${SBOM_FORMAT}")
endif()

# Gerar SBOM se habilitado
if(GENERATE_SBOM AND SBOM_TOOL)
    set(SBOM_OUTPUT_FILE "${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}.${SBOM_EXTENSION}")
    
    add_custom_target(generate-sbom
        COMMAND ${SBOM_TOOL} ${SBOM_OUTPUT_FLAG} ${SBOM_OUTPUT_FILE} dir:${CMAKE_SOURCE_DIR}
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Gerando SBOM ${SBOM_FORMAT}"
        VERBATIM
    )
    
    # Integrar com build principal
    add_dependencies(${PROJECT_NAME} generate-sbom)
    
    message(STATUS "SBOM sera gerado durante o build usando ${SBOM_TOOL_NAME}")
else()
    message(STATUS "Geracao de SBOM desabilitada")
endif()
```

---

## 6. SBOM para projetos C++

### 6.1 Desafios especificos do C++

Projetos C++ apresentam desafios unicos para geracao de SBOM:

**Dependencias de Sistema**
Bibliotecas como OpenSSL, zlib e pthreads podem ser fornecidas pelo sistema operacional ou compiladas estaticamente. O SBOM deve refletir exatamente qual opcao foi usada.

**Dependencias de Build**
Ferramentas como CMake, Conan, vcpkg e Hunter geram dependencias que devem ser incluidas no SBOM.

**Headers e Source**
Alem das bibliotecas, projetos C++ podem incluir headers e arquivos-fonte de terceiros que devem ser catalogados.

**Compiladores e Toolchain**
Embora nao sejam componentes do software final, compiladores e toolchains podem afetar a seguranca do binario e devem ser documentados.

### 6.2 Catalogando dependencias C++ com syft

syft suporta deteccao automatica de pacotes C++ atraves de varios mecanismos:

**CMakeLists.txt**
```bash
# syft detecta dependencias declaradas em CMakeLists.txt
syft dir:./my-project -o cyclonedx-json

# Saida esperada:
# - openssl (detectado via find_package)
# - zlib (detectado via find_package)
# - Threads (detectado via find_package)
```

**Arquivos de lock do gerenciador de pacotes**
```bash
# Para projetos com Conan
syft dir:./my-project --from conanfile.txt -o cyclonedx-json

# Para projetos com vcpkg
syft dir:./my-project --from vcpkg.json -o cyclonedx-json

# Para projetos com Hunter
syft dir:./my-project --from cmake/Hunter/gate.cmake -o cyclonedx-json
```

### 6.3 Catalogando dependencias C++ com cdxgen

cdxgen oferece analise mais profunda para projetos C++:

```bash
# Analise profunda com cdxgen
cdxgen --spec-version 1_5 -o bom.json -t c-cpp .

# Com opcoes especificas
cdxgen --spec-version 1_5 -o bom.json -t c-cpp \
    --include-build-deps \
    --include-dev \
    --deep .
```

### 6.4 Gerenciadores de pacotes C++ e SBOM

**Conan**

```python
# Script para extrair dependencias Conan para CycloneDX
import json
import subprocess
from pathlib import Path

def get_conan_packages():
    """Extrai pacotes instalados pelo Conan."""
    result = subprocess.run(
        ["conan", "list", "*:*"],
        capture_output=True,
        text=True
    )
    
    packages = []
    for line in result.stdout.splitlines():
        if "/" in line and "@" in line:
            name, version = line.split("/")[0], line.split("@")[0].split("/")[1]
            packages.append({
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:conan/{name}@{version}"
            })
    
    return packages
```

**vcpkg**

```python
# Script para extrair dependencias vcpkg para CycloneDX
import json
import subprocess
from pathlib import Path

def get_vcpkg_packages(vcpkg_json_path):
    """Extrai pacotes declarados no vcpkg.json."""
    with open(vcpkg_json_path) as f:
        manifest = json.load(f)
    
    packages = []
    for dep in manifest.get("dependencies", []):
        name = dep if isinstance(dep, str) else dep.get("name")
        version = dep.get("version>=", "latest") if isinstance(dep, dict) else "latest"
        
        packages.append({
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:github/microsoft/vcpkg@{name}"
        })
    
    return packages
```

**Hunter**

```python
# Script para extrair dependencias Hunter para CycloneDX
import json
import re
from pathlib import Path

def get_hunter_packages(cmake_modules_dir):
    """Extrai pacotes gerenciados pelo Hunter."""
    packages = []
    
    for cmake_file in Path(cmake_modules_dir).rglob("*.cmake"):
        with open(cmake_file) as f:
            content = f.read()
        
        # Procurar por hunter_add_package
        matches = re.findall(r'hunter_add_package\((\w+)\)', content)
        for match in matches:
            packages.append({
                "type": "library",
                "name": match.lower(),
                "version": "hunter-managed",
                "purl": f"pkg:generic/hunter/{match.lower()}@hunter"
            })
    
    return packages
```

### 6.5 Estrutura de diretorio recomendada para SBOM C++

```
my-project/
├── CMakeLists.txt
├── vcpkg.json
├── conanfile.txt
├── sbom/
│   ├── templates/
│   │   ├── spdx-template.json
│   │   └── cyclonedx-template.json
│   ├── scripts/
│   │   ├── generate_sbom.py
│   │   ├── validate_sbom.py
│   │   └── update_sbom.py
│   ├── generated/
│   │   ├── my-project-1.0.0.spdx.json
│   │   └── my-project-1.0.0-bom.json
│   └── docs/
│       ├── SBOM-GUIDE.md
│       └── SBOM-POLICY.md
├── scripts/
│   ├── generate_sbom.sh
│   └── validate_sbom.sh
└── .github/
    └── workflows/
        └── sbom.yml
```

### 6.6 Exemplo completo: SBOM para projeto C++ com CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Buscar dependencias
find_package(OpenSSL REQUIRED)
find_package(zlib REQUIRED)
find_package(Threads REQUIRED)

# Criar executavel
add_executable(my-project
    src/main.cpp
    src/utils.cpp
    src/crypto.cpp
)

target_link_libraries(my-project
    PRIVATE
        OpenSSL::SSL
        OpenSSL::Crypto
        zlib::zlib
        Threads::Threads
)

# Configurar SBOM
option(GENERATE_SBOM "Gerar SBOM durante o build" ON)

if(GENERATE_SBOM)
    # Extrair informacoes de dependencias do CMake
    set(SBOM_DEPENDENCIES "")
    
    foreach(dep OpenSSL::SSL OpenSSL::Crypto zlib::zlib Threads::Threads)
        get_target_property(dep_type ${dep} TYPE)
        get_target_property(dep_imported ${dep} IMPORTED)
        
        if(dep_imported)
            get_target_property(dep_location ${dep} IMPORTED_LOCATION)
            get_target_property(dep_version ${dep} VERSION)
            
            list(APPEND SBOM_DEPENDENCIES
                "{\"name\": \"${dep}\", \"version\": \"${dep_version}\", \"location\": \"${dep_location}\"}"
            )
        endif()
    endforeach()
    
    # Criar target para gerar SBOM
    add_custom_target(generate-sbom
        COMMAND ${CMAKE_COMMAND} -E echo "Gerando SBOM para ${PROJECT_NAME} ${PROJECT_VERSION}"
        COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/generate_sbom.py
            --project-name ${PROJECT_NAME}
            --version ${PROJECT_VERSION}
            --dependencies '${SBOM_DEPENDENCIES}'
            --output ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.json
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Gerando SBOM CycloneDX"
        VERBATIM
    )
    
    # Integrar com build principal
    add_dependencies(${PROJECT_NAME} generate-sbom)
endif()
```

### 6.7 Scripts de automacao para SBOM C++

**Script de geracao de SBOM (scripts/generate_sbom.sh)**

```bash
#!/bin/bash
set -euo pipefail

# Configuracoes
PROJECT_NAME="${1:-my-project}"
VERSION="${2:-1.0.0}"
OUTPUT_DIR="${3:-./sbom/generated}"
FORMAT="${4:-cyclonedx-json}"

# Criar diretorio de saida
mkdir -p "$OUTPUT_DIR"

# Detectar ferramenta disponivel
if command -v syft &> /dev/null; then
    TOOL="syft"
elif command -v cdxgen &> /dev/null; then
    TOOL="cdxgen"
elif command -v trivy &> /dev/null; then
    TOOL="trivy"
else
    echo "Erro: Nenhuma ferramenta SBOM encontrada"
    exit 1
fi

echo "Usando ferramenta: $TOOL"

# Gerar SBOM
case "$TOOL" in
    syft)
        syft dir:. -o "$FORMAT" > "$OUTPUT_DIR/${PROJECT_NAME}-${VERSION}-bom.${FORMAT##*-}"
        ;;
    cdxgen)
        cdxgen --spec-version 1_5 -o "$OUTPUT_DIR/${PROJECT_NAME}-${VERSION}-bom.json" -t c-cpp .
        ;;
    trivy)
        trivy fs --format cyclonedx -o "$OUTPUT_DIR/${PROJECT_NAME}-${VERSION}-bom.json" .
        ;;
esac

echo "SBOM gerado em: $OUTPUT_DIR"
```

**Script de validacao de SBOM (scripts/validate_sbom.sh)**

```bash
#!/bin/bash
set -euo pipefail

SBOM_FILE="${1:-./sbom/generated/my-project-1.0.0-bom.json}"

echo "Validando SBOM: $SBOM_FILE"

# Verificar se o arquivo existe
if [ ! -f "$SBOM_FILE" ]; then
    echo "Erro: Arquivo SBOM nao encontrado: $SBOM_FILE"
    exit 1
fi

# Validar formato JSON
if ! python3 -m json.tool "$SBOM_FILE" > /dev/null 2>&1; then
    echo "Erro: Arquivo SBOM nao e JSON valido"
    exit 1
fi

# Verificar campos obrigatorios
REQUIRED_FIELDS=("bomFormat" "specVersion" "serialNumber" "version" "metadata" "components")

for field in "${REQUIRED_FIELDS[@]}"; do
    if ! python3 -c "import json; data=json.load(open('$SBOM_FILE')); assert '$field' in data" 2>/dev/null; then
        echo "Erro: Campo obrigatorio ausente: $field"
        exit 1
    fi
done

# Verificar se ha componentes
COMPONENT_COUNT=$(python3 -c "import json; print(len(json.load(open('$SBOM_FILE')).get('components', [])))")
echo "Componentes encontrados: $COMPONENT_COUNT"

if [ "$COMPONENT_COUNT" -eq 0 ]; then
    echo "Aviso: Nenhum componente encontrado no SBOM"
fi

echo "Validacao concluida com sucesso"
```

### 6.8 Melhores praticas para SBOM em projetos C++

1. **Gere SBOM em cada build de release** e armazene como artefato
2. **Valide o SBOM** antes de publicar ou distribuir
3. **Mantenha historico de SBOMs** para auditoria e rastreabilidade
4. **Atualize SBOM sempre que dependencias mudarem**
5. **Inclua SBOM no pacote de distribuicao** junto com binarios
6. **Use identificadores padronizados** (PURL, CPE) para cada componente
7. **Documente o processo de geracao de SBOM** na documentacao do projeto
8. **Automatize atualizacoes** usando ferramentas como Dependabot ou Renovate

---

## 7. Sigstore: signing, verification

### 7.1 O que e Sigstore

Sigstore e um conjunto de ferramentas para simplificar a assinatura e verificacao de artefatos de software. Foi criado para resolver um problema fundamental da seguranca de software: a maioria dos desenvolvedores nao assina seus artefatos porque o processo e complexo e requer gestao de chaves criptograficas.

O Sigstore elimina a necessidade de gerenciar chaves de longo prazo, usando um modelo baseado em identidade de OIDC (OpenID Connect) para autenticacao durante a assinatura.

### 7.2 Arquitetura do Sigstore

O Sigstore consiste em tres componentes principais:

**Fulcio (Certificate Authority)**
Emitido certificados de curta duracao baseados em identidade OIDC. Cada certificado e valido por apenas uma operacao de assinatura.

**Rekor (Transparency Log)**
Um log imutavel e distribuido que registra todas as operacoes de assinatura. Permite verificacao retroativa e deteccao de tentativas de repudio.

**Cosign (Signing Tool)**
A ferramenta principal para assinar e verificar artefatos. Interface amigavel para desenvolvedores.

### 7.3 Fluxo de signing com Sigstore

O fluxo completo de signing com Sigstore funciona assim:

1. **Autenticacao**: O desenvolvedor se autentica usando OIDC (GitHub, GitLab, Google, etc.)
2. **Emissao de certificado**: Fulcio emite um certificado de curta duracao vinculado a identidade
3. **Assinatura**: O artefato e assinado usando a chave privada temporaria
4. **Registro**: A assinatura e registrada no Rekor transparency log
5. **Distribuicao**: O artefato assinado e distribuido com a assinatura
6. **Verificacao**: Qualquer pessoa pode verificar a assinatura usando o Rekor

### 7.4 Instalacao do Sigstore

```bash
# Instalar Cosign (principal ferramenta do Sigstore)
# Linux (amd64)
COSIGN_VERSION="v1.13.5"
curl -LO "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# macOS
brew install cosign

# Verificar instalacao
cosign version
```

### 7.5 Assinatura de artefatos com Cosign

**Assinatura com chave gerenciada pelo Sigstore (keyless)**

```bash
# Assinar um binario usando OIDC (keyless)
cosign sign-blob \
    --bundle my-project-1.0.0-linux-amd64.bundle \
    my-project-1.0.0-linux-amd64

# O sistema abrira o navegador para autenticacao OIDC
# Apos autenticacao, a assinatura sera criada e registrada no Rekor
```

**Assinatura com chave tradicional**

```bash
# Gerar par de chaves
cosign generate-key-pair

# Assinar usando a chave
cosign sign-blob \
    --key cosign.key \
    --output-signature my-project-1.0.0-linux-amd64.sig \
    my-project-1.0.0-linux-amd64
```

**Assinatura de imagem Docker**

```bash
# Assinar imagem Docker
cosign sign \
    --key cosign.key \
    myregistry/my-project:1.0.0

# Assinar imagem Docker com keyless
cosign sign \
    myregistry/my-project:1.0.0
```

### 7.6 Verificacao de assinaturas

**Verificacao basica**

```bash
# Verificar assinatura de binario
cosign verify-blob \
    --bundle my-project-1.0.0-linux-amd64.bundle \
    my-project-1.0.0-linux-amd64

# Verificar assinatura com chave publica
cosign verify-blob \
    --key cosign.pub \
    --signature my-project-1.0.0-linux-amd64.sig \
    my-project-1.0.0-linux-amd64
```

**Verificacao detalhada**

```bash
# Verificar com verbose
cosign verify-blob \
    --bundle my-project-1.0.0-linux-amd64.bundle \
    --certificate-identity https://github.com/mycompany/my-project/.github/workflows/release.yml@refs/heads/main \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    my-project-1.0.0-linux-amd64

# Verificar assinatura de imagem Docker
cosign verify \
    --key cosign.pub \
    myregistry/my-project:1.0.0

# Verificar com detalhes de OIDC
cosign verify \
    --key cosign.pub \
    --certificate-identity user@example.com \
    --certificate-oidc-issuer https://accounts.google.com \
    myregistry/my-project:1.0.0
```

### 7.7 SBOM e Sigstore

Assinar o SBOM garante que ele nao foi adulterado:

```bash
# Assinar SBOM
cosign sign-blob \
    --bundle my-project-1.0.0-bom.json.bundle \
    my-project-1.0.0-bom.json

# Verificar SBOM
cosign verify-blob \
    --bundle my-project-1.0.0-bom.json.bundle \
    my-project-1.0.0-bom.json
```

### 7.8 Integracao com CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Configurar signing
option(SIGN_ARTIFACTS "Assinar artefatos do build" ON)
option(COSIGN_KEY "Chave para assinatura" "")
option(SIGN_IDENTITY "Identidade OIDC para keyless signing" "")

# Verificar se Cosign esta disponivel
find_program(COSIGN_EXECUTABLE cosign)
if(NOT COSIGN_EXECUTABLE)
    message(WARNING "Cosign nao encontrado. Signing desabilitado.")
    set(SIGN_ARTIFACTS OFF)
endif()

# Target para assinar artefatos
if(SIGN_ARTIFACTS AND COSIGN_EXECUTABLE)
    # Assinar executavel
    add_custom_target(sign-executable
        COMMAND ${COSIGN_EXECUTABLE} sign-blob
            --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-linux-amd64.bundle
            ${CMAKE_BINARY_DIR}/${PROJECT_NAME}
        DEPENDS ${PROJECT_NAME}
        COMMENT "Assinando executavel"
        VERBATIM
    )
    
    # Assinar SBOM
    add_custom_target(sign-sbom
        COMMAND ${COSIGN_EXECUTABLE} sign-blob
            --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.json.bundle
            ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.json
        DEPENDS generate-sbom
        COMMENT "Assinando SBOM"
        VERBATIM
    )
    
    # Target para verificar assinaturas
    add_custom_target(verify-signatures
        COMMAND ${COSIGN_EXECUTABLE} verify-blob
            --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-linux-amd64.bundle
            ${CMAKE_BINARY_DIR}/${PROJECT_NAME}
        COMMAND ${COSIGN_EXECUTABLE} verify-blob
            --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.json.bundle
            ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-${PROJECT_VERSION}-bom.json
        COMMENT "Verificando assinaturas"
        VERBATIM
    )
endif()
```

### 7.9 Melhores praticas de signing

1. **Use keyless signing** sempre que possivel (mais simples e seguro)
2. **Assine SBOMs junto com binarios** para garantir integridade completa
3. **Registre assinaturas em transparency log** para auditoria retroativa
4. **Automatize signing em CI/CD** para consistencia e auditabilidade
5. **Mantenha chaves publicas acessiveis** para verificacao por terceiros
6. **Documente o processo de verificacao** para consumidores do software
7. **Use certificados de curta duracao** em vez de chaves de longo prazo

---

## 8. Cosign: artifact signing

### 8.1 Cosign em detalhes

Cosign e a ferramenta de assinatura do ecossistema Sigstore. Ela suporta:

- Assinatura de binarios e artefatos genericos
- Assinatura de imagens Docker
- Assinatura de SBOMs
- Assinatura com chave tradicional ou keyless (OIDC)
- Verificacao de assinaturas
- Gerenciamento de chaves

### 8.2 Tipos de assinatura do Cosign

**Assinatura de blob (arquivos genericos)**

```bash
# Assinar um arquivo arbitrario
cosign sign-blob \
    --output-certificate my-cert.pem \
    --output-signature my-sig.sig \
    my-file.txt

# Assinar com bundle (recomendado)
cosign sign-blob \
    --bundle my-file.bundle \
    my-file.txt
```

**Assinatura de imagem Docker**

```bash
# Assinar imagem Docker
cosign sign \
    --key cosign.key \
    docker.io/myuser/myimage:latest

# Assinar com keyless
cosign sign \
    docker.io/myuser/myimage:latest
```

**Assinatura de SBOM**

```bash
# Assinar SBOM CycloneDX
cosign sign-blob \
    --bundle sbom.bundle \
    my-project-bom.json

# Assinar SBOM SPDX
cosign sign-blob \
    --bundle sbom-spdx.bundle \
    my-project.spdx.json
```

### 8.3 Gerenciamento de chaves do Cosign

**Gerar par de chaves**

```bash
# Gerar par de chaves no formato PKCS8
cosign generate-key-pair

# Gerar par de chaves com nome especifico
cosign generate-key-pair --key cosign.key

# Gerar par de chaves com senha
cosign generate-key-pair --key cosign.key --password
```

**Formato das chaves**

```
cosign.key    # Chave privada (PKCS8 PEM)
cosign.pub    # Chave publica (PEM)
```

**Estrutura de diretorio para chaves**

```
keys/
├── cosign.key           # Chave privada
├── cosign.pub           # Chave publica
├── README.md            # Documentacao
└── .gitignore           # Ignorar chave privada
```

**.gitignore para chaves**

```
# Ignorar chaves privadas
cosign.key
*.key
*.pem

# Manter chaves publicas
!cosign.pub
!*.pub
```

### 8.4 Verificacao detalhada com Cosign

**Verificacao basica**

```bash
# Verificar assinatura de binario
cosign verify-blob \
    --key cosign.pub \
    --signature my-file.sig \
    my-file

# Verificar com bundle
cosign verify-blob \
    --key cosign.pub \
    --bundle my-file.bundle \
    my-file
```

**Verificacao com identidade OIDC**

```bash
# Verificar com identidade especifica
cosign verify-blob \
    --certificate-identity user@example.com \
    --certificate-oidc-issuer https://accounts.google.com \
    --bundle my-file.bundle \
    my-file

# Verificar com GitHub Actions
cosign verify-blob \
    --certificate-identity https://github.com/myorg/myrepo/.github/workflows/release.yml@refs/heads/main \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    --bundle my-file.bundle \
    my-file
```

**Verificacao com verbose**

```bash
# Verificar com saida detalhada
cosign verify-blob \
    --key cosign.pub \
    --bundle my-file.bundle \
    --output-text \
    my-file
```

### 8.5 Cosign e imagens Docker

**Assinatura de imagens**

```bash
# Assinar imagem Docker com chave
cosign sign \
    --key cosign.key \
    docker.io/myuser/myimage:1.0.0

# Assinar imagem Docker keyless
cosign sign \
    docker.io/myuser/myimage:1.0.0

# Assinar com annotations
cosign sign \
    --key cosign.key \
    -a "repo=https://github.com/myorg/myrepo" \
    -a "vulnerability-critical=true" \
    docker.io/myuser/myimage:1.0.0
```

**Verificacao de imagens**

```bash
# Verificar assinatura de imagem
cosign verify \
    --key cosign.pub \
    docker.io/myuser/myimage:1.0.0

# Verificar com identidade OIDC
cosign verify \
    --certificate-identity user@example.com \
    --certificate-oidc-issuer https://accounts.google.com \
    docker.io/myuser/myimage:1.0.0

# Verificar com verbose
cosign verify \
    --key cosign.pub \
    --output-text \
    docker.io/myuser/myimage:1.0.0
```

### 8.6 Cosign e SBOM

```bash
# Assinar SBOM CycloneDX
cosign sign-blob \
    --bundle sbom-cdx.bundle \
    my-project-bom.json

# Assinar SBOM SPDX
cosign sign-blob \
    --bundle sbom-spdx.bundle \
    my-project.spdx.json

# Verificar SBOM CycloneDX
cosign verify-blob \
    --key cosign.pub \
    --bundle sbom-cdx.bundle \
    my-project-bom.json

# Verificar SBOM SPDX
cosign verify-blob \
    --key cosign.pub \
    --bundle sbom-spdx.bundle \
    my-project.spdx.json
```

### 8.7 Cosign e Kubernetes

```bash
# Verificar imagem em cluster Kubernetes
cosign verify \
    --key cosign.pub \
    docker.io/myuser/myimage:1.0.0

# Verificar com policy no Kyverno
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: check-image-signature
      match:
        resources:
          kinds:
            - Pod
      verifyImages:
        - imageReferences:
            - "docker.io/myuser/*"
          attestors:
            - entries:
                - keys:
                    publicKeys: |-
                      -----BEGIN PUBLIC KEY-----
                      MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
                      -----END PUBLIC KEY-----
```

### 8.8 Exemplo completo: pipeline com Cosign

```yaml
# .github/workflows/release.yml
name: Release Pipeline

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read
  packages: write
  id-token: write  # Para keyless signing

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build project
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          make -j$(nproc)
      
      - name: Generate SBOM
        run: |
          syft dir:. -o cyclonedx-json > build/my-project-bom.json
      
      - name: Sign SBOM
        run: |
          cosign sign-blob \
            --bundle build/my-project-bom.json.bundle \
            build/my-project-bom.json
      
      - name: Sign executable
        run: |
          cosign sign-blob \
            --bundle build/my-project.bundle \
            build/my-project
      
      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            build/my-project
            build/my-project-bom.json
            build/my-project-bom.json.bundle
            build/my-project.bundle
```

### 8.9 Melhores praticas do Cosign

1. **Use keyless signing** sempre que possivel (mais simples e seguro)
2. **Assine SBOMs junto com binarios** para garantir integridade completa
3. **Use bundles** em vez de arquivos separados (cert + signature)
4. **Automatize signing em CI/CD** para consistencia
5. **Mantenha chaves publicas em repositorio acessivel**
6. **Documente processo de verificacao** para consumidores
7. **Use annotations** para metadata adicional
8. **Integre com policy engines** como Kyverno ou OPA

---

## 9. SLSA: Supply chain Levels

### 9.1 O que e SLSA

SLSA (Supply chain Levels for Software Artifacts) e um framework de seguranca open-source criado pelo Google para proteger a cadeia de suprimentos de software. SLSA define niveis de maturidade que medem a resistencia de um software a ataques na cadeia de suprimentos.

O framework e inspirado no modelo de maturidade de padroes como CMMI e define quatro niveis progressivos de protecao.

### 9.2 Niveis do SLSA

**SLSA Level 0: Nenhuma garantia**

Este e o nivel padrao. Nao ha garantias de seguranca na cadeia de suprimentos.

Caracteristicas:
- Processo de build nao documentado
- Sem verificacao de origem
- Sem verificacao de integridade
- Sem logging de build
- Qualquer pessoa pode alterar o build

Riscos:
- Atacante pode substituir binarios por versoes maliciosas
- Nao ha como rastrear origem de uma vulnerabilidade
- Nao ha como provar que o binario corresponde ao codigo-fonte

**SLSA Level 1: Processo de build documentado**

Este nivel exige que o processo de build seja documentado e auditavel.

Caracteristicas:
- Script de build documentado
- Historico de versoes mantido
- Build executado em ambiente controlado
- Artefatos gerados com metadados basicos

Protecoes:
- Atacante pode substituir binarios, mas ha evidencia do build original
- Permite auditar o processo de build
- Facilita reproducao de builds

Exemplo de implementacao:

```yaml
# GitHub Actions workflow com SLSA Level 1
name: Build with Documentation

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Document build process
        run: |
          echo "Build Process Documentation" > build-docs.txt
          echo "========================" >> build-docs.txt
          echo "Date: $(date -u)" >> build-docs.txt
          echo "Commit: ${{ github.sha }}" >> build-docs.txt
          echo "Runner: ${{ runner.os }}" >> build-docs.txt
          echo "Command: cmake --build build" >> build-docs.txt
      
      - name: Build project
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          cmake --build .
      
      - name: Generate build metadata
        run: |
          cat > build-metadata.json << EOF
          {
            "build_id": "${{ github.run_id }}",
            "build_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "commit_sha": "${{ github.sha }}",
            "build_command": "cmake --build build",
            "runner_os": "${{ runner.os }}",
            "builder": "github-actions"
          }
          EOF
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-output
          path: |
            build/my-project
            build/build-metadata.json
            build-docs.txt
```

**SLSA Level 2: Build host gerenciado e assinatura**

Este nivel exige que o build seja executado em um host gerenciado e que os artefatos sejam assinados.

Caracteristicas:
- Build executado em host gerenciado (nao local)
- Artefatos assinados com chave de build
- Historico de builds imutavel
- Verificacao de origem do codigo-fonte

Protecoes:
- Atacante nao pode executar builds locais maliciosos
- Artefatos podem ser verificados contra a assinatura de build
- Permite deteccao de substituicao de artefatos

Exemplo de implementacao:

```yaml
# GitHub Actions workflow com SLSA Level 2
name: Build with Signing

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
    steps:
      - uses: actions/checkout@v4
      
      - name: Build project
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          cmake --build .
      
      - name: Sign build artifacts
        run: |
          # Assinar executavel
          cosign sign-blob \
            --bundle build/my-project.bundle \
            build/my-project
          
          # Assinar SBOM
          cosign sign-blob \
            --bundle build/my-project-bom.json.bundle \
            build/my-project-bom.json
      
      - name: Generate build provenance
        run: |
          cat > build-provenance.json << EOF
          {
            "buildType": "https://slsa.dev/build/v1",
            "builder": {
              "id": "https://github.com/actions/runner"
            },
            "buildConfig": {
              "steps": [
                {
                  "name": "Build",
                  "command": "cmake --build build"
                }
              ]
            },
            "metadata": {
              "buildInvocationId": "${{ github.run_id }}",
              "buildStartedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "buildFinishedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "completeness": {
                "parameters": true,
                "environment": false,
                "materials": true
              },
              "reproducible": false
            },
            "materials": [
              {
                "uri": "git+https://github.com/${{ github.repository }}@${{ github.sha }}",
                "digest": {
                  "gitCommit": "${{ github.sha }}"
                }
              }
            ]
          }
          EOF
      
      - name: Sign build provenance
        run: |
          cosign sign-blob \
            --bundle build-provenance.json.bundle \
            build-provenance.json
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-output
          path: |
            build/my-project
            build/my-project.bundle
            build/my-project-bom.json
            build/my-project-bom.json.bundle
            build-provenance.json
            build-provenance.json.bundle
```

**SLSA Level 3: Build alinhado a especificacao**

Este nivel exige que o build seja executado em um ambiente que atenda a especificacao SLSA, com verificacao de integridade completa.

Caracteristicas:
- Build executado em plataforma SLSA-compativel
- Verificacao de integridade do codigo-fonte
- Verificacao de integridade das dependencias
- Logging imutavel de build
- Build reproduzivel

Protecoes:
- Atacante nao pode alterar o processo de build
- Artefatos podem ser verificados contra o codigo-fonte
- Permite verificacao completa da cadeia de suprimentos

Exemplo de implementacao:

```yaml
# GitHub Actions workflow com SLSA Level 3
name: Build with SLSA Level 3

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
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Historico completo para verificacao
      
      - name: Verify source integrity
        run: |
          # Verificar assinatura do commit
          git verify-commit HEAD || echo "WARNING: Commit not signed"
          
          # Verificar branch
          git branch -r --contains HEAD
      
      - name: Verify dependencies
        run: |
          # Verificar checksums de dependencias
          sha256sum -c checksums.txt
      
      - name: Build project
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release -DREPRODUCIBLE_BUILD=ON
          cmake --build .
      
      - name: Generate build provenance
        run: |
          # Coletar informacoes detalhadas do build
          BUILD_START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
          
          cat > build-provenance.json << EOF
          {
            "buildType": "https://slsa.dev/build/v1",
            "builder": {
              "id": "https://github.com/actions/runner",
              "version": "1.0.0"
            },
            "buildConfig": {
              "steps": [
                {
                  "name": "Verify source",
                  "command": "git verify-commit HEAD"
                },
                {
                  "name": "Build",
                  "command": "cmake --build build"
                }
              ]
            },
            "metadata": {
              "buildInvocationId": "${{ github.run_id }}",
              "buildStartedOn": "$BUILD_START",
              "buildFinishedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "completeness": {
                "parameters": true,
                "environment": true,
                "materials": true
              },
              "reproducible": true
            },
            "materials": [
              {
                "uri": "git+https://github.com/${{ github.repository }}@${{ github.sha }}",
                "digest": {
                  "gitCommit": "${{ github.sha }}"
                }
              }
            ]
          }
          EOF
      
      - name: Sign all artifacts
        run: |
          # Assinar executavel
          cosign sign-blob --bundle my-project.bundle build/my-project
          
          # Assinar SBOM
          cosign sign-blob --bundle sbom.bundle build/my-project-bom.json
          
          # Assinar provenance
          cosign sign-blob --bundle provenance.bundle build-provenance.json
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-output
          path: |
            build/my-project
            my-project.bundle
            build/my-project-bom.json
            sbom.bundle
            build-provenance.json
            provenance.bundle
```

**SLSA Level 4: Build alinhado a especificacao com hardening**

Este nivel exige hardening adicional do build e verificacao de integridade completa.

Caracteristicas:
- Build executado em ambiente hardening
- Verificacao de integridade completa
- Isolamento de build
- Verificacao de dependencias
- Build reproduzivel e auditavel

Protecoes:
- Atacante nao pode comprometer o ambiente de build
- Artefatos podem ser verificados contra codigo-fonte e dependencias
- Permite verificacao completa e auditavel da cadeia de suprimentos

### 9.3 Implementacao do SLSA com CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Configuracao de build reproduzivel
option(REPRODUCIBLE_BUILD "Habilitar build reproduzivel" OFF)
option(SLSA_LEVEL "Nivel SLSA desejado (0-4)" "3")

if(REPRODUCIBLE_BUILD)
    # Forcar compilacao identica
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffile-prefix-map=${CMAKE_SOURCE_DIR}=.")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -ffile-prefix-map=${CMAKE_SOURCE_DIR}=.")
    
    # Desabilitar timestamp no binario
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wdate-time")
    
    # Usar source date epoch
    set(ENV{SOURCE_DATE_EPOCH} "0")
endif()

# Configurar SBOM
option(GENERATE_SBOM "Gerar SBOM" ON)
option(GENERATE_PROVENANCE "Gerar build provenance" ON)

# Target para gerar build provenance
if(GENERATE_PROVENANCE)
    add_custom_target(generate-provenance
        COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/generate_provenance.py
            --build-id ${CMAKE_BINARY_DIR}
            --source-uri git+https://github.com/myorg/myrepo
            --source-revision ${GIT_COMMIT_HASH}
            --output ${CMAKE_BINARY_DIR}/build-provenance.json
        COMMENT "Gerando build provenance"
        VERBATIM
    )
    
    add_dependencies(${PROJECT_NAME} generate-provenance)
endif()

# Target para assinar artefatos SLSA
if(SLSA_LEVEL GREATER_EQUAL 2)
    add_custom_target(sign-slsa
        COMMAND cosign sign-blob --bundle ${PROJECT_NAME}.bundle ${PROJECT_NAME}
        COMMAND cosign sign-blob --bundle sbom.bundle ${PROJECT_NAME}-bom.json
        COMMAND cosign sign-blob --bundle provenance.bundle build-provenance.json
        DEPENDS ${PROJECT_NAME} generate-sbom generate-provenance
        COMMENT "Assinando artefatos SLSA"
        VERBATIM
    )
endif()
```

### 9.4 Ferramentas SLSA

**slsa-verifier**

```bash
# Instalar slsa-verifier
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest

# Verificar build provenance
slsa-verifier verify-artifact \
    --provenance-path build-provenance.json \
    --source-uri github.com/myorg/myrepo \
    --source-tag v1.0.0 \
    build/my-project
```

**slsa-github-generator**

```yaml
# Usar slsa-github-generator para builds SLSA Level 3
name: Build with SLSA Generator

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build project
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          cmake --build .
      
      - name: Generate SBOM
        run: |
          syft dir:. -o cyclonedx-json > build/my-project-bom.json
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-output
          path: |
            build/my-project
            build/my-project-bom.json
  
  provenance:
    needs: build
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.10.0
    with:
      base64-subjects: "${{ needs.build.outputs.digest }}"
```

### 9.5 Melhores praticas SLSA

1. **Comece com SLSA Level 1** e evolua progressivamente
2. **Documente o processo de build** em cada nivel
3. **Use build hosts gerenciados** (GitHub Actions, GitLab CI)
4. **Assine todos os artefatos** (binarios, SBOMs, provenance)
5. **Mantenha logs de build imutaveis**
6. **Verifique integridade do codigo-fonte** e dependencias
7. **Implemente builds reproduziveis** sempre que possivel
8. **Use ferramentas SLSA** como slsa-verifier e slsa-github-generator

---

## 10. in-toto: supply chain integrity

### 10.1 O que e in-toto

in-toto e um framework open-source para garantir a integridade da cadeia de suprimentos de software. Diferente do SLSA, que foca em niveis de maturidade, in-toto foca em verificacao criptografica de cada etapa do processo de build e distribuicao.

O in-toto foi criado na universidade de NYU e e mantido pela organizacao Linux Foundation. Ele funciona como um "mapa de rota" criptografico que descreve todas as etapas que o software deve passar ate chegar ao usuario final.

### 10.2 Conceitos fundamentais do in-toto

**Layout**
Um documento que descreve todas as etapas do processo de build e distribuicao. Define quem pode executar cada etapa e quais artefatos sao produzidos e consumidos.

**Step**
Uma etapa individual no processo de build. Cada step e executado por um "functionary" (executante) e produz e consome artefatos especificos.

**Functionary**
A entidade (pessoa ou sistema) que executa um step. Cada functionary tem uma chave criptografica associada.

**Supply Chain Link**
A conexao entre steps, garantindo que os artefatos produzidos por um step sao consumidos pelo proximo step.

**Metablock**
Um arquivo que contem as assinaturas de um step, provando que ele foi executado corretamente.

### 10.3 Estrutura do Layout in-toto

```json
{
  "_type": "layout",
  "expires": "2025-12-31T23:59:59Z",
  "keys": {
    "keyid1": {
      "keytype": "ed25519",
      "keyval": {
        "public": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
      }
    },
    "keyid2": {
      "keytype": "ed25519",
      "keyval": {
        "public": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
      }
    }
  },
  "steps": [
    {
      "name": "build",
      "expected_materials": [],
      "expected_products": [
        ["CREATE", "build/my-project"],
        ["CREATE", "build/my-project-bom.json"]
      ],
      "pubkeys": ["keyid1"],
      "threshold": 1
    },
    {
      "name": "test",
      "expected_materials": [
        ["MATCH", "build/my-project", "WITH", "FROM", "build"]
      ],
      "expected_products": [
        ["DISALLOW", "build/*"]
      ],
      "pubkeys": ["keyid2"],
      "threshold": 1
    },
    {
      "name": "sign",
      "expected_materials": [
        ["MATCH", "build/my-project", "WITH", "FROM", "build"],
        ["MATCH", "build/my-project-bom.json", "WITH", "FROM", "build"]
      ],
      "expected_products": [
        ["CREATE", "build/my-project.sig"],
        ["CREATE", "build/my-project-bom.json.sig"]
      ],
      "pubkeys": ["keyid1"],
      "threshold": 1
    }
  ],
  "inspect": [
    {
      "name": "verify",
      "patterns": [
        "build/my-project",
        "build/my-project-bom.json"
      ]
    }
  ]
}
```

### 10.4 Instalacao do in-toto

```bash
# Instalar in-toto
pip install in-toto

# Ou instalar da fonte
git clone https://github.com/in-toto/in-toto.git
cd in-toto
pip install -e .

# Verificar instalacao
in-toto-run --help
```

### 10.5 Usando in-toto

**Gerar chaves para functionaries**

```bash
# Gerar chave para build
in-toto-keygen -f build-key

# Gerar chave para test
in-toto-keygen -f test-key

# Gerar chave para sign
in-toto-keygen -f sign-key

# Listar chaves geradas
ls *.key *.pub
```

**Criar layout**

```bash
# Criar layout usando ferramenta de geracao
in-toto-run \
    --step-name create-layout \
    --layout-layout layout.layout \
    -- \
    python3 scripts/generate_layout.py
```

**Assinar layout**

```bash
# Assinar layout com chave do maintainer
in-toto-sign \
    --layout layout.layout \
    --layout-key maintainers.key \
    --output layout-signed.layout
```

**Executar steps**

```bash
# Executar step de build
in-toto-run \
    --step-name build \
    --key build.key \
    --materials build/ \
    --products build/my-project build/my-project-bom.json \
    -- \
    cmake --build build

# Executar step de test
in-toto-run \
    --step-name test \
    --key test.key \
    --materials build/my-project \
    -- \
    ctest --test-dir build

# Executar step de sign
in-toto-run \
    --step-name sign \
    --key sign.key \
    --materials build/my-project build/my-project-bom.json \
    --products build/my-project.sig build/my-project-bom.json.sig \
    -- \
    cosign sign-blob --key cosign.key --bundle build/my-project.bundle build/my-project
```

**Verificar supply chain**

```bash
# Verificar toda a supply chain
in-toto-verify \
    --layout layout-signed.layout \
    --layout-key maintainers.key

# Verificar com verbose
in-toto-verify \
    --layout layout-signed.layout \
    --layout-key maintainers.key \
    --verbose
```

### 10.6 in-toto e CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Configurar in-toto
option(USE_IN_TOTO "Usar in-toto para verificacao de supply chain" OFF)
option(IN_TOTO_LAYOUT "Caminho para o layout in-toto" "")

if(USE_IN_TOTO)
    find_program(IN_TOTO_RUN in-toto-run)
    find_program(IN_TOTO_VERIFY in-toto-verify)
    
    if(NOT IN_TOTO_RUN OR NOT IN_TOTO_VERIFY)
        message(WARNING "in-toto nao encontrado. Supply chain verification desabilitada.")
        set(USE_IN_TOTO OFF)
    endif()
endif()

# Target para executar build com in-toto
if(USE_IN_TOTO)
    add_custom_target(in-toto-build
        COMMAND ${IN_TOTO_RUN}
            --step-name build
            --key ${CMAKE_BINARY_DIR}/build.key
            --materials ${CMAKE_SOURCE_DIR}
            --products ${CMAKE_BINARY_DIR}/${PROJECT_NAME}
            -- cmake --build ${CMAKE_BINARY_DIR}
        DEPENDS ${PROJECT_NAME}
        COMMENT "Executando build com in-toto"
        VERBATIM
    )
    
    # Target para executar test com in-toto
    add_custom_target(in-toto-test
        COMMAND ${IN_TOTO_RUN}
            --step-name test
            --key ${CMAKE_BINARY_DIR}/test.key
            --materials ${CMAKE_BINARY_DIR}/${PROJECT_NAME}
            -- ctest --test-dir ${CMAKE_BINARY_DIR}
        DEPENDS in-toto-build
        COMMENT "Executando test com in-toto"
        VERBATIM
    )
    
    # Target para verificar supply chain
    add_custom_target(verify-supply-chain
        COMMAND ${IN_TOTO_VERIFY}
            --layout ${IN_TOTO_LAYOUT}
            --layout-key ${CMAKE_BINARY_DIR}/maintainers.key
        DEPENDS in-toto-build in-toto-test
        COMMENT "Verificando supply chain"
        VERBATIM
    )
endif()
```

### 10.7 Melhores praticas in-toto

1. **Defina um layout completo** que cubra todas as etapas do processo
2. **Use chaves separadas** para cada functionary
3. **Mantenha chaves de layout em local seguro**
4. **Execute in-toto em cada build** para registro completo
5. **Verifique supply chain antes de distribuir** software
6. **Mantenha historico de metablocks** para auditoria
7. **Integre com CI/CD** para automatizacao completa
8. **Combine com SLSA** para protecao em profundidade

---

## 11. Dependabot/Renovate para C++

### 11.1 O problema de gerenciar dependencias C++

Gerenciar dependencias em projetos C++ e um desafio unico:

- Nao existe um ecossistema unificado como npm ou pip
- Dependencias podem ser gerenciadas por Conan, vcpkg, Hunter, ou sistema operacional
- Atualizacoes podem quebrar compatibilidade ABI
- Vulnerabilidades podem afetar dependencias transientes nao visiveis
- Processo manual e propenso a erros

### 11.2 Dependabot para C++

Dependabot e um servico da GitHub para gerenciamento automatizado de dependencias. Ele suporta varios ecossistemas, incluindo alguns usados em projetos C++.

**Configuracao do Dependabot**

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Atualizar dependencias GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "github-actions"
  
  # Atualizar dependencias Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "docker"
  
  # Atualizar dependencias Conan
  - package-ecosystem: "conan"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "conan"
    # Configuracao especifica para Conan
    config:
      version: 2
  
  # Atualizar dependencias vcpkg
  - package-ecosystem: "vcpkg"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "vcpkg"
  
  # Atualizar dependencias npm (para ferramentas de build)
  - package-ecosystem: "npm"
    directory: "/tools"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "npm"
```

**Configuracao especifica para Conan**

```yaml
# .github/dependabot.yml para projeto com Conan
version: 2
updates:
  - package-ecosystem: "conan"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "myorg/security-team"
    labels:
      - "dependencies"
      - "security"
    # Configuracao de versao
    versioning-strategy: increase
    # Grupos de atualizacao
    groups:
      security-updates:
        patterns:
          - "openssl*"
          - "zlib*"
        update-types:
          - "patch"
          - "minor"
```

**Configuracao especifica para vcpkg**

```yaml
# .github/dependabot.yml para projeto com vcpkg
version: 2
updates:
  - package-ecosystem: "vcpkg"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "myorg/security-team"
    labels:
      - "dependencies"
      - "vcpkg"
    # Configuracao de versao
    versioning-strategy: increase
```

### 11.3 Renovate para C++

Renovate e uma alternativa ao Dependabot com suporte mais amplo a ecossistemas C++. Ele suporta Conan, vcpkg, e muitos outros gerenciadores de pacotes.

**Configuracao basica do Renovate**

```json
// renovate.json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base",
    ":dependencyDashboard",
    ":semanticCommits",
    "group:allNonMajor"
  ],
  "labels": ["dependencies"],
  "schedule": ["before 6am on monday"],
  "timezone": "America/Sao_Paulo",
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
      "automerge": true
    },
    {
      "matchPackagePatterns": ["openssl"],
      "labels": ["security", "dependencies"],
      "reviewers": ["team:security-team"]
    }
  ]
}
```

**Configuracao para Conan**

```json
// renovate.json para projeto com Conan
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "packageRules": [
    {
      "matchManagers": ["conan"],
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    },
    {
      "matchManagers": ["conan"],
      "matchPackagePatterns": ["openssl"],
      "labels": ["security"],
      "reviewers": ["team:security-team"]
    }
  ],
  "conan": {
    "fileMatch": ["conanfile\\.txt$", "conanfile\\.py$"]
  }
}
```

**Configuracao para vcpkg**

```json
// renovate.json para projeto com vcpkg
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "packageRules": [
    {
      "matchManagers": ["vcpkg"],
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    },
    {
      "matchManagers": ["vcpkg"],
      "matchPackagePatterns": ["openssl"],
      "labels": ["security"],
      "reviewers": ["team:security-team"]
    }
  ],
  "vcpkg": {
    "fileMatch": ["vcpkg\\.json$"]
  }
}
```

### 11.4 Comparacao Dependabot vs Renovate

| Caracteristica | Dependabot | Renovate |
|---------------|------------|----------|
| Suporte a Conan | Sim | Sim |
| Suporte a vcpkg | Sim | Sim |
| Suporte a Hunter | Nao | Parcial |
| Automerge | Limitado | Avancado |
| Grupos de atualizacao | Limitado | Avancado |
| Personalizacao | Media | Alta |
| Dashboard | Limitado | Completo |
| Linguagens suportadas | 15+ | 50+ |

### 11.5 Melhores praticas para gerenciamento de dependencias C++

1. **Ative atualizacoes automaticas** para patches de seguranca
2. **Configure revisao manual** para atualizacoes menores e maiores
3. **Use grupos de atualizacao** para organizar PRs
4. **Configure reviewers** especificos para dependencias criticas
5. **Mantenha historico de atualizacoes** para auditoria
6. **Teste atualizacoes** antes de merge
7. **Monitore dashboard de dependencias** regularmente
8. **Combine com SBOM** para visibilidade completa

---

## 12. CVE-2024-3094 post-mortem

### 12.1 Resumo do incidente

Em 29 de marco de 2024, uma vulnerabilidade critica (CVE-2024-3094) foi descoberta no XZ Utils, uma biblioteca de compressao amplamente utilizada em sistemas Linux. A vulnerabilidade permitia remote code execution (RCE) no systemd, afetando potencialmente milhoes de sistemas.

### 12.2 Timeline do ataque

**Fevereiro 2023**: Atacante comecou a contribuir para o projeto XZ Utils usando o nome "Jia Tan". As contribuicoes eram legitimas e de alta qualidade.

**Janeiro 2024**: Atacante comecou a inserir codigo malicioso no build system do XZ Utils. O codigo era ofuscado e dificil de detectar.

**Marco 2024**: Atacante fez commit de versoes comprometidas do XZ Utils (5.6.0 e 5.6.1) que continham backdoor.

**29 de Marco 2024**: Andres Freund, um engenheiro da Microsoft, descobriu a vulnerabilidade enquanto investigava lentidao inesperada no sshd.

**30 de Marco 2024**: Vulnerabilidade foi reportada publicamente e distribuicoes Linux comecaram a emitir patches.

### 12.3 Mecanismo do ataque

O ataque utilizou varias tecnicas sofisticadas:

**Social Engineering**
O atacante ganhou confianca da comunidade do XZ Utils ao longo de meses, fazendo contribuicoes legitimas antes de inserir codigo malicioso.

**Build System Compromise**
O codigo malicioso foi inserido nos arquivos de build (configure.ac, Makefile.in) e scripts de teste, nao no codigo-fonte principal.

**Obfuscação**
O codigo malicioso era ofuscado e so era ativado em versoes especificas do XZ Utils em ambiente de producao.

**Targeted Attack**
O backdoor foi projetado especificamente para comprometer o sshd via systemd, afetando apenas sistemas Debian/Ubuntu.

### 12.4 Impacto

- Milhoes de sistemas Linux potencialmente afetados
- Distribuicoes principais (Debian, Ubuntu, Fedora, openSUSE) emitiram patches
- CI/CD pipelines afetadas em projetos que dependiam de XZ Utils
- Dano a confianca na comunidade open-source
- Custo estimado de remediacao em milhoes de dolares

### 12.5 O que teria ajudado

**SBOM Completo**
Um SBOM teria permitido identificar imediatamente quais sistemas eram afetados pela versao comprometida do XZ Utils.

**Assinatura de Artefatos**
Se os binarios do XZ Utils fossem assinados e verificados, o ataque teria sido detectado mais cedo.

**Build Provenance**
Build provenance teria mostrado que o build do XZ Utils nao era reproduzivel ou que o processo de build foi alterado.

**in-toto**
O in-toto teria detectado que o processo de build foi alterado nao autorizadamente.

**Dependabot/Renovate**
Ferramentas de gerenciamento de dependencias teriam alertado sobre atualizacoes suspeitas no XZ Utils.

### 12.6 Lições aprendidas

1. **Confie, mas verifique**: Contribuicoes de longa data nao devem ser isentas de auditoria
2. **Monitore o build system**: Alteracoes em arquivos de build devem ser auditadas com a mesma rigidez que alteracoes no codigo-fonte
3. **Use SBOMs**: Ter um inventario completo de dependencias permite resposta rapida a incidentes
4. **Assine artefatos**: Signing e verificacao de artefatos adicionam uma camada extra de seguranca
5. **Implemente SLSA**: Builds reproduziveis e auditaveis dificultam ataques de supply chain
6. **Combine ferramentas**: Nenhuma ferramenta individual e suficiente; use SBLA, SBOM, signing, e gerenciamento de dependencias em conjunto
7. **Cultura de seguranca**: A comunidade precisa cultivar uma cultura de desconfianca saudavel

### 12.7 Defesas contra ataques similares

**Defesa em Profundidade**

```
┌─────────────────────────────────────────────────────────┐
│                    Defesa em Profundidade                │
├─────────────────────────────────────────────────────────┤
│  1. SBOM                                                 │
│     └─ Visibilidade completa de dependencias             │
│  2. Signing e Verification                               │
│     └─ Garantia de integridade de artefatos              │
│  3. SLSA                                                 │
│     └─ Build reproduzivel e auditavel                    │
│  4. in-toto                                              │
│     └─ Verificacao de cada etapa da supply chain         │
│  5. Dependabot/Renovate                                  │
│     └─ Gerenciamento automatizado de dependencias        │
│  6. Code Review                                          │
│     └─ Auditoria humana de alteracoes criticas           │
│  7. Monitoring                                           │
│     └─ Deteccao anomalias em runtime                     │
└─────────────────────────────────────────────────────────┘
```

**Implementacao concreta**

```yaml
# Pipeline de defesa completa
name: Supply Chain Security

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # 1. Verificar integridade do codigo-fonte
      - name: Verify source integrity
        run: |
          git verify-commit HEAD
          git verify-tag ${{ github.ref_name }}
      
      # 2. Gerar SBOM
      - name: Generate SBOM
        run: |
          syft dir:. -o cyclonedx-json > sbom.json
      
      # 3. Verificar dependencias
      - name: Check dependencies
        run: |
          # Verificar contra CVEs conhecidas
          trivy fs --severity CRITICAL,HIGH .
      
      # 4. Build com SLSA
      - name: Build with SLSA
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release -DREPRODUCIBLE_BUILD=ON
          cmake --build .
      
      # 5. Assinar artefatos
      - name: Sign artifacts
        run: |
          cosign sign-blob --bundle sbom.bundle sbom.json
          cosign sign-blob --bundle build.bundle build/my-project
      
      # 6. Gerar build provenance
      - name: Generate provenance
        run: |
          # Gerar build provenance SLSA
          cat > provenance.json << EOF
          {
            "buildType": "https://slsa.dev/build/v1",
            "builder": {"id": "github-actions"},
            "metadata": {
              "buildInvocationId": "${{ github.run_id }}",
              "completeness": {
                "parameters": true,
                "environment": true,
                "materials": true
              }
            }
          }
          EOF
      
      # 7. Verificar supply chain
      - name: Verify supply chain
        run: |
          in-toto-verify \
            --layout layout-signed.layout \
            --layout-key maintainers.key
```

---

## 13. Exemplo: pipeline com SBOM

### 13.1 Pipeline completa com SBOM, signing e verificacao

Este exemplo mostra uma pipeline completa para um projeto C++ com CMake, incluindo geracao de SBOM, signing, e verificacao de supply chain.

```yaml
# .github/workflows/release.yml
name: Release Pipeline with SBOM

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read
  packages: write
  id-token: write

env:
  BUILD_TYPE: Release
  SBOM_FORMAT: cyclonedx-json

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            cmake \
            ninja-build \
            gcc-12 \
            g++-12 \
            libssl-dev \
            zlib1g-dev
      
      - name: Install SBOM tools
        run: |
          # Instalar syft
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          
          # Instalar cosign
          COSIGN_VERSION="v1.13.5"
          curl -LO "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
          chmod +x cosign-linux-amd64
          sudo mv cosign-linux-amd64 /usr/local/bin/cosign
      
      - name: Configure CMake
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=${{ env.BUILD_TYPE }} \
            -DCMAKE_C_COMPILER=gcc-12 \
            -DCMAKE_CXX_COMPILER=g++-12 \
            -DGENERATE_SBOM=ON \
            -DSIGN_ARTIFACTS=ON
      
      - name: Build
        run: |
          cmake --build build --config ${{ env.BUILD_TYPE }} -j$(nproc)
      
      - name: Run tests
        run: |
          cd build && ctest --output-on-failure
      
      - name: Generate SBOM
        run: |
          syft dir:. -o ${{ env.SBOM_FORMAT }} > build/project-bom.json
          
          # Validar SBOM
          python3 scripts/validate_sbom.py --input build/project-bom.json
      
      - name: Sign artifacts
        run: |
          # Assinar executavel
          cosign sign-blob \
            --bundle build/project.bundle \
            build/project
          
          # Assinar SBOM
          cosign sign-blob \
            --bundle build/project-bom.json.bundle \
            build/project-bom.json
      
      - name: Generate build provenance
        run: |
          cat > build/provenance.json << EOF
          {
            "buildType": "https://slsa.dev/build/v1",
            "builder": {
              "id": "https://github.com/actions/runner",
              "version": "1.0.0"
            },
            "buildConfig": {
              "steps": [
                {
                  "name": "Build",
                  "command": "cmake --build build"
                }
              ]
            },
            "metadata": {
              "buildInvocationId": "${{ github.run_id }}",
              "buildStartedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "buildFinishedOn": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
              "completeness": {
                "parameters": true,
                "environment": true,
                "materials": true
              },
              "reproducible": true
            },
            "materials": [
              {
                "uri": "git+https://github.com/${{ github.repository }}@${{ github.sha }}",
                "digest": {
                  "gitCommit": "${{ github.sha }}"
                }
              }
            ]
          }
          EOF
      
      - name: Sign build provenance
        run: |
          cosign sign-blob \
            --bundle build/provenance.json.bundle \
            build/provenance.json
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: release-artifacts
          path: |
            build/project
            build/project.bundle
            build/project-bom.json
            build/project-bom.json.bundle
            build/provenance.json
            build/provenance.json.bundle
  
  verify:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
        with:
          name: release-artifacts
      
      - name: Install verification tools
        run: |
          # Instalar cosign
          COSIGN_VERSION="v1.13.5"
          curl -LO "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
          chmod +x cosign-linux-amd64
          sudo mv cosign-linux-amd64 /usr/local/bin/cosign
          
          # Instalar slsa-verifier
          go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest
      
      - name: Verify executable signature
        run: |
          cosign verify-blob \
            --bundle project.bundle \
            project
      
      - name: Verify SBOM signature
        run: |
          cosign verify-blob \
            --bundle project-bom.json.bundle \
            project-bom.json
      
      - name: Verify build provenance
        run: |
          cosign verify-blob \
            --bundle provenance.json.bundle \
            provenance.json
      
      - name: Verify with slsa-verifier
        run: |
          slsa-verifier verify-artifact \
            --provenance-path provenance.json \
            --source-uri github.com/${{ github.repository }} \
            --source-tag ${{ github.ref_name }} \
            project
  
  release:
    needs: verify
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
        with:
          name: release-artifacts
      
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            project
            project.bundle
            project-bom.json
            project-bom.json.bundle
            provenance.json
            provenance.json.bundle
          body: |
            ## Release ${{ github.ref_name }}
            
            ### Artefatos
            
            - `project` - Executavel principal
            - `project.bundle` - Assinatura do executavel (Cosign)
            - `project-bom.json` - SBOM CycloneDX
            - `project-bom.json.bundle` - Assinatura do SBOM (Cosign)
            - `provenance.json` - Build provenance (SLSA)
            - `provenance.json.bundle` - Assinatura da provenance (Cosign)
            
            ### Verificacao
            
            ```bash
            # Verificar executavel
            cosign verify-blob --bundle project.bundle project
            
            # Verificar SBOM
            cosign verify-blob --bundle project-bom.json.bundle project-bom.json
            
            # Verificar provenance
            cosign verify-blob --bundle provenance.json.bundle provenance.json
            ```
```

### 13.2 Scripts de suporte

**Script de validacao de SBOM (scripts/validate_sbom.py)**

```python
#!/usr/bin/env python3
"""
Validador de SBOM CycloneDX
"""

import argparse
import json
import sys
from pathlib import Path

def validate_sbom(sbom_path):
    """Valida um SBOM CycloneDX."""
    
    # Carregar SBOM
    try:
        with open(sbom_path) as f:
            sbom = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erro: Arquivo JSON invalido: {e}")
        return False
    
    # Verificar campos obrigatorios
    required_fields = ["bomFormat", "specVersion", "serialNumber", "version", "metadata", "components"]
    missing_fields = [field for field in required_fields if field not in sbom]
    
    if missing_fields:
        print(f"Erro: Campos obrigatorios ausentes: {missing_fields}")
        return False
    
    # Verificar formato
    if sbom["bomFormat"] != "CycloneDX":
        print(f"Erro: Formato invalido: {sbom['bomFormat']}")
        return False
    
    # Verificar versao da especificacao
    spec_version = sbom.get("specVersion", "")
    if not spec_version.startswith("1."):
        print(f"Erro: Versao da especificacao invalida: {spec_version}")
        return False
    
    # Verificar se ha componentes
    components = sbom.get("components", [])
    if not components:
        print("Aviso: Nenhum componente encontrado no SBOM")
    
    # Verificar PURL em componentes
    for component in components:
        if "purl" not in component:
            print(f"Aviso: Componente '{component.get('name')}' sem PURL")
    
    print(f"SBOM validado com sucesso: {len(components)} componentes")
    return True

def main():
    parser = argparse.ArgumentParser(description="Validador de SBOM CycloneDX")
    parser.add_argument("--input", required=True, help="Caminho para o SBOM")
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Erro: Arquivo nao encontrado: {args.input}")
        sys.exit(1)
    
    if validate_sbom(args.input):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Script de verificacao de assinaturas (scripts/verify_signatures.sh)**

```bash
#!/bin/bash
set -euo pipefail

# Verificar todas as assinaturas de um release
ARTIFACTS_DIR="${1:-.}"

echo "Verificando assinaturas em: $ARTIFACTS_DIR"

# Verificar executavel
if [ -f "$ARTIFACTS_DIR/project" ] && [ -f "$ARTIFACTS_DIR/project.bundle" ]; then
    echo "Verificando assinatura do executavel..."
    cosign verify-blob \
        --bundle "$ARTIFACTS_DIR/project.bundle" \
        "$ARTIFACTS_DIR/project"
    echo "Executavel verificado com sucesso"
else
    echo "Aviso: Executavel ou assinatura nao encontrados"
fi

# Verificar SBOM
if [ -f "$ARTIFACTS_DIR/project-bom.json" ] && [ -f "$ARTIFACTS_DIR/project-bom.json.bundle" ]; then
    echo "Verificando assinatura do SBOM..."
    cosign verify-blob \
        --bundle "$ARTIFACTS_DIR/project-bom.json.bundle" \
        "$ARTIFACTS_DIR/project-bom.json"
    echo "SBOM verificado com sucesso"
else
    echo "Aviso: SBOM ou assinatura nao encontrados"
fi

# Verificar provenance
if [ -f "$ARTIFACTS_DIR/provenance.json" ] && [ -f "$ARTIFACTS_DIR/provenance.json.bundle" ]; then
    echo "Verificando assinatura da provenance..."
    cosign verify-blob \
        --bundle "$ARTIFACTS_DIR/provenance.json.bundle" \
        "$ARTIFACTS_DIR/provenance.json"
    echo "Provenance verificada com sucesso"
else
    echo "Aviso: Provenance ou assinatura nao encontrados"
fi

echo "Verificacao de assinaturas concluida"
```

### 13.3 CMakeLists.txt para o projeto exemplo

```cmake
cmake_minimum_required(VERSION 3.20)

project(my-project VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Configuracoes de build
option(GENERATE_SBOM "Gerar SBOM durante o build" ON)
option(SIGN_ARTIFACTS "Assinar artefatos do build" ON)
option(SLSA_LEVEL "Nivel SLSA desejado" "3")

# Buscar dependencias
find_package(OpenSSL REQUIRED)
find_package(zlib REQUIRED)
find_package(Threads REQUIRED)

# Criar executavel
add_executable(${PROJECT_NAME}
    src/main.cpp
    src/utils.cpp
    src/crypto.cpp
)

target_link_libraries(${PROJECT_NAME}
    PRIVATE
        OpenSSL::SSL
        OpenSSL::Crypto
        zlib::zlib
        Threads::Threads
)

# Configurar SBOM
if(GENERATE_SBOM)
    find_program(SYFT_EXECUTABLE syft)
    if(SYFT_EXECUTABLE)
        add_custom_target(generate-sbom
            COMMAND ${SYFT_EXECUTABLE} dir:${CMAKE_SOURCE_DIR} -o cyclonedx-json
                ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-bom.json
            WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
            COMMENT "Gerando SBOM CycloneDX"
            VERBATIM
        )
        add_dependencies(${PROJECT_NAME} generate-sbom)
    else()
        message(WARNING "syft nao encontrado. Geracao de SBOM desabilitada.")
    endif()
endif()

# Configurar signing
if(SIGN_ARTIFACTS)
    find_program(COSIGN_EXECUTABLE cosign)
    if(COSIGN_EXECUTABLE)
        add_custom_target(sign-executable
            COMMAND ${COSIGN_EXECUTABLE} sign-blob
                --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}.bundle
                ${CMAKE_BINARY_DIR}/${PROJECT_NAME}
            DEPENDS ${PROJECT_NAME}
            COMMENT "Assinando executavel"
            VERBATIM
        )
        
        add_custom_target(sign-sbom
            COMMAND ${COSIGN_EXECUTABLE} sign-blob
                --bundle ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-bom.json.bundle
                ${CMAKE_BINARY_DIR}/${PROJECT_NAME}-bom.json
            DEPENDS generate-sbom
            COMMENT "Assinando SBOM"
            VERBATIM
        )
        
        add_dependencies(${PROJECT_NAME} sign-executable sign-sbom)
    else()
        message(WARNING "cosign nao encontrado. Signing desabilitado.")
    endif()
endif()
```

---

## 14. Exercicios

### Exercicio 1: Geracao de SBOM

**Objetivo**: Gerar um SBOM CycloneDX para um projeto C++ existente.

**Instrucoes**:
1. Instale o syft ou cdxgen
2. Clone um projeto C++ existente (por exemplo, https://github.com/fmtlib/fmt)
3. Gere um SBOM CycloneDX para o projeto
4. Valide o SBOM gerado
5. Analise os componentes listados e identifique potenciais problemas de seguranca

**Solucao esperada**:
```bash
# Instalar syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Clonar projeto
git clone https://github.com/fmtlib/fmt.git
cd fmt

# Gerar SBOM
syft dir:. -o cyclonedx-json > fmt-bom.json

# Validar SBOM
python3 scripts/validate_sbom.py --input fmt-bom.json
```

### Exercicio 2: Assinatura de Artefatos

**Objetivo**: Assinar e verificar um binario usando Cosign.

**Instrucoes**:
1. Instale o Cosign
2. Compile um projeto C++ simples
3. Assine o binario gerado
4. Verifique a assinatura
5. Documente o processo

**Solucao esperada**:
```bash
# Instalar cosign
COSIGN_VERSION="v1.13.5"
curl -LO "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
chmod +x cosign-linux-amd64
sudo mv cosign-linux-amd64 /usr/local/bin/cosign

# Compilar projeto
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .

# Assinar binario
cosign sign-blob --bundle my-project.bundle my-project

# Verificar assinatura
cosign verify-blob --bundle my-project.bundle my-project
```

### Exercicio 3: Pipeline com SBOM

**Objetivo**: Criar uma pipeline GitHub Actions que gere SBOM e assine artefatos.

**Instrucoes**:
1. Crie um repositorio GitHub com um projeto C++ simples
2. Crie um workflow GitHub Actions que:
   - Compile o projeto
   - Gere um SBOM CycloneDX
   - Assine o binario e o SBOM
   - Crie um release com os artefatos assinados
3. Execute a pipeline e verifique os resultados

**Solucao esperada**:
```yaml
# .github/workflows/release.yml
name: Release with SBOM

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        run: |
          mkdir build && cd build
          cmake .. -DCMAKE_BUILD_TYPE=Release
          cmake --build .
      
      - name: Generate SBOM
        run: |
          syft dir:. -o cyclonedx-json > build/project-bom.json
      
      - name: Sign artifacts
        run: |
          cosign sign-blob --bundle build/project.bundle build/project
          cosign sign-blob --bundle build/project-bom.json.bundle build/project-bom.json
      
      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            build/project
            build/project.bundle
            build/project-bom.json
            build/project-bom.json.bundle
```

### Exercicio 4: Analise de CVE com SBOM

**Objetivo**: Usar um SBOM para identificar vulnerabilidades em um projeto.

**Instrucoes**:
1. Gere um SBOM para um projeto C++
2. Use o trivy para analisar o SBOM em busca de CVEs
3. Documente as vulnerabilidades encontradas
4. Proponha remediaoes

**Solucao esperada**:
```bash
# Gerar SBOM
syft dir:. -o cyclonedx-json > project-bom.json

# Analisar com trivy
trivy sbom --severity CRITICAL,HIGH project-bom.json

# Documentar vulnerabilidades
trivy sbom --format json --output results.json project-bom.json
```

### Exercicio 5: SLSA Build Provenance

**Objetivo**: Implementar build provenance SLSA para um projeto C++.

**Instrucoes**:
1. Configure um build reproduzivel no CMake
2. Gere build provenance em formato JSON
3. Assine a provenance com Cosign
4. Verifique a provenance usando slsa-verifier

**Solucao esperada**:
```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(my-project VERSION 1.0.0 LANGUAGES CXX)

# Build reproduzivel
option(REPRODUCIBLE_BUILD "Build reproduzivel" ON)
if(REPRODUCIBLE_BUILD)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffile-prefix-map=${CMAKE_SOURCE_DIR}=.")
endif()

# Resto do CMakeLists.txt...
```

```bash
# Gerar build provenance
cat > provenance.json << EOF
{
  "buildType": "https://slsa.dev/build/v1",
  "builder": {"id": "github-actions"},
  "metadata": {
    "buildInvocationId": "12345",
    "completeness": {
      "parameters": true,
      "environment": true,
      "materials": true
    },
    "reproducible": true
  }
}
EOF

# Assinar provenance
cosign sign-blob --bundle provenance.bundle provenance.json

# Verificar com slsa-verifier
slsa-verifier verify-artifact \
    --provenance-path provenance.json \
    --source-uri github.com/myorg/myrepo \
    --source-tag v1.0.0 \
    my-project
```

### Exercicio 6: Dependabot para Projeto C++

**Objetivo**: Configurar Dependabot ou Renovate para gerenciar dependencias de um projeto C++.

**Instrucoes**:
1. Crie um projeto C++ com Conan ou vcpkg
2. Configure Dependabot ou Renovate para atualizacoes automaticas
3. Configure regras de automerge para patches de seguranca
4. Teste o fluxo de atualizacao

**Solucao esperada**:
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "conan"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
    packageRules:
      - matchUpdateTypes: ["patch"]
        automerge: true
```

### Exercicio 7: in-toto para Supply Chain

**Objetivo**: Implementar in-toto para verificacao de supply chain.

**Instrucoes**:
1. Instale o in-toto
2. Crie um layout que descreva o processo de build
3. Gere chaves para functionaries
4. Execute steps com in-toto-run
5. Verifique a supply chain com in-toto-verify

**Solucao esperada**:
```bash
# Instalar in-toto
pip install in-toto

# Gerar chaves
in-toto-keygen -f build-key
in-toto-keygen -f test-key

# Criar layout (usando script customizado)
python3 scripts/generate_layout.py > layout.layout

# Assinar layout
in-toto-sign --layout layout.layout --layout-key maintainers.key

# Executar build
in-toto-run --step-name build --key build.key -- cmake --build build

# Verificar
in-toto-verify --layout layout-signed.layout --layout-key maintainers.key
```

---

## 15. Referencias

### 15.1 Especificacoes e Padroes

1. **SPDX Specification**: https://spdx.github.io/spdx-spec/
2. **CycloneDX Specification**: https://cyclonedx.org/specification/
3. **SLSA Framework**: https://slsa.dev/
4. **in-toto Framework**: https://in-toto.io/
5. **NIST SBOM Guidance**: https://csrc.nist.gov/projects/ssdf

### 15.2 Ferramentas

6. **syft**: https://github.com/anchore/syft
7. **cdxgen**: https://github.com/CycloneDX/cdxgen
8. **spdx-tools**: https://github.com/spdx/tools-python
9. **trivy**: https://github.com/aquasecurity/trivy
10. **Cosign**: https://github.com/sigstore/cosign
11. **slsa-verifier**: https://github.com/slsa-framework/slsa-verifier

### 15.3 Documentacao e Tutoriais

12. **Sigstore Documentation**: https://docs.sigstore.dev/
13. **SLSA Getting Started**: https://slsa.dev/start
14. **in-toto Documentation**: https://in-toto.readthedocs.io/
15. **Dependabot Documentation**: https://docs.github.com/en/code-security/dependabot
16. **Renovate Documentation**: https://docs.renovatebot.com/

### 15.4 Artigos e Posts

17. **Executive Order 14028**: https://www.whitehouse.gov/briefing-room/presidential-actions/2021/05/12/executive-order-on-improving-the-nations-cybersecurity/
18. **XZ Utils Backdoor Analysis**: https://www.openwall.com/lists/oss-security/2024/03/29/4
19. **Supply Chain Security Best Practices**: https://owasp.org/www-project-dependency-track/
20. **SBOM in Practice**: https://docs.oasis-open.org/sbom/examples/sbom-in-practice/

### 15.5 Videos e Apresentacoes

21. **SLSA Explained**: https://www.youtube.com/watch?v=PcDhmhaUfYw
22. **Sigstore Deep Dive**: https://www.youtube.com/watch?v=8hrG4hBPtJw
23. **SBOM Workshop**: https://www.youtube.com/watch?v=6f6bKz0bGw
24. **Supply Chain Security Talk**: https://www.youtube.com/watch?v=3BpOoVz7bJc

### 15.6 Repositorios de Exemplo

25. **SLSA GitHub Generator**: https://github.com/slsa-framework/slsa-github-generator
26. **in-toto attestation**: https://github.com/in-toto/attestation
27. **CycloneDX Examples**: https://github.com/CycloneDX/cyclonedx-example
28. **SPDX Examples**: https://github.com/spdx/spdx-examples

### 15.7 Comunidade e Suporte

29. **OWASP Dependency-Track**: https://dependencytrack.org/
30. **SPDX Mailing List**: https://lists.spdx.org/
31. **CycloneDX Mailing List**: https://owasp.org/www-project-cyclonedx/
32. **SLSA Community**: https://slsa.dev/community

---

## Sumario do Capitulo

Neste capitulo, exploramos os conceitos fundamentais de SBOM e Supply Chain Security para projetos C++. Cobrimos desde a geracao de SBOMs usando ferramentas como syft e cdxgen, ate assinatura de artefatos com Sigstore e Cosign, framework SLSA para niveis de maturidade, e in-toto para verificacao de integridade da cadeia de suprimentos.

Tambem analisamos o post-mortem do CVE-2024-3094 (XZ Utils) como estudo de caso real de ataque a cadeia de suprimentos, e implementamos uma pipeline completa com SBOM, signing e verificacao.

O SBOM e uma ferramenta essencial para visibilidade de dependencias, resposta rapida a CVEs e compliance regulatorio. Combinado com signing, SLSA e in-toto, cria uma defesa em profundidade contra ataques a cadeia de suprimentos.

---

> *"A cadeia de suprimentos de software e apenas tao segura quanto seu elo mais fraco. O SBOM transforma esse elo invisivel em uma cadeia auditavel."*

---

**Proximo Capitulo**: [Capitulo 13 — Incident Response e Post-Mortem](13-incident-response.md)

---

*Ultima atualizacao: Novembro 2024*
