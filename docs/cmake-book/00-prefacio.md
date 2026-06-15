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

CMake e o build system de facto para projetos C/C++. Usado por Qt, LLVM, OpenCV, TensorFlow e milhares de projetos open-source. Mas a maioria dos CMakeLists.txt e copiada de templates sem entender as implicacoes de seguranca.

Este livro transforma CMake de "gerador de Makefiles" em uma ferramenta de seguranca.

---

## Publico-Alvo

- **Engenheiros C/C++** que usam CMake e querem builds seguros
- **DevOps/Platform Engineers** que configuram pipelines de build
- **Security Engineers** que auditan build systems
- **Tech Leads** que definem padroes de build para equipes

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| C++ | Intermediario | Exemplos em C++17/20 |
| CMake | Basico | CMakeLists.txt, target properties |
| Make/Ninja | Basico | Geradores de build |
| GCC/Clang | Basico | Compiladores e flags |
| Git | Basico | Versionamento e CI/CD |

---

## Estrutura do Livro

### Parte I: Fundamentos (00-03)
- Prefacio, intro a CMake, target model, propriedades

### Parte II: Seguranca no Build (04-08)
- Flags de seguranca, sanitizers, hardening, static analysis, reproducibility

### Parte III: Dependencias e Supply Chain (09-12)
- Finding packages, FetchContent, vcpkg, conan, SBOM

### Parte IV: CI/CD e Operacao (13-17)
- Cross-compilation, testing, install, packaging, boas praticas

---

## Convencoes

- **Texto**: Portugues brasileiro (PT-BR)
- **Codigo**: Identificadores em ingles
- **Exemplos**: CMake 3.20+, C++17/20
- **Compiladores**: GCC 12+, Clang 16+, MSVC 2022+

---

## Casos Reais

- CVE-2023-44487: HTTP/2 Rapid Reset (afeta builds com dependencias de rede)
- CVE-2024-3094: XZ Utils backdoor (supply chain via build system)
- Projetos com builds nao-reproduziveis que falharam auditorias
- Binarios sem hardening comprometidos em producao

---

*[Proximo capitulo: 01 — Introducao ao CMake Moderno](01-introducao-cmake-moderno.md)*
