---
layout: default
title: "INDICE"
---

# CMake Seguro e Build Systems — Indice do Livro

> **Build Systems, Hardening, Supply Chain, Reproducibility**

---

## Sumario Rapido

| # | Capitulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefacio](00-prefacio.md) | Motivacao, publico-alvo, convencoes |
| 01 | [Introducao ao CMake Moderno](01-introducao-cmake-moderno.md) | CMake 3.20+, targets, properties, generators |
| 02 | [Target Model e Properties](02-target-model-properties.md) | Target-based build, interface libraries, compile features |
| 03 | [Expressoes e Funcoes](03-expressoes-funcoes.md) | Generator expressions, custom functions, macros |
| 04 | [Flags de Seguranca do Compilador](04-flags-seguranca-compilador.md) | -fstack-protector, ASLR, DEP, FORTIFY, PIE |
| 05 | [Sanitizers e Debug Builds](05-sanitizers-debug.md) | ASan, TSan, UBSan, MSan,配置, uso em CI/CD |
| 06 | [Hardening de Binarios](06-hardening-binarios.md) | RELRO, NOW, stack canaries, strip, reproducible builds |
| 07 | [Analise Estatica com CMake](07-analise-estatica.md) | clang-tidy, cppcheck, Infer, integration |
| 08 | [Builds Reproduziveis](08-builds-reproduziveis.md) | Deterministic builds, hash verification, reprotest |
| 09 | [Finding Packages Seguro](09-finding-packages.md) | find_package,/pkg-config, security implications |
| 10 | [FetchContent e ExternalProject](10-fetchcontent-external.md) | Secure fetching, pinning, hash verification |
| 11 | [vcpkg e Conan](11-vcpkg-conan.md) | Package managers: security, audit, lockfiles |
| 12 | [SBOM e Supply Chain](12-sbom-supply-chain.md) | SPDX, CycloneDX, Sigstore, SLSA |
| 13 | [Cross-Compilation](13-cross-compilation.md) | Toolchains, sysroots, secure cross-builds |
| 14 | [Testing no CMake](14-testing-cmake.md) | CTest, GoogleTest, fuzzing integration |
| 15 | [Install e Packaging](15-install-packaging.md) | CPack, DESTDIR, secure installation |
| 16 | [CI/CD Seguro com CMake](16-cicd-seguro.md) | GitHub Actions, GitLab CI, security gates |
| 17 | [Boas Praticas e Checklist](17-boas-praticas-checklist.md) | Anti-patterns, decision trees, checklist |

---

## Dependencias

```
00 -> 01 -> 02 -> 03
                 |
         +-------+-------+
         |       |       |
         04      05      06
         |       |       |
         +---+---+---+---+
             |       |
             07      08
             |       |
         +---+---+---+---+
         |       |       |
         09      10      11
         |       |       |
         +---+---+---+---+
             |
             12
             |
         +---+---+---+---+
         |       |       |
         13      14      15
         |       |       |
         +---+---+---+---+
             |
         16 -> 17
```

---

## CVEs Documentados

| CVE | Titulo | Capitulo |
|-----|--------|----------|
| CVE-2024-3094 | XZ Utils backdoor (supply chain) | 10, 12 |
| CVE-2023-44487 | HTTP/2 Rapid Reset | 09 |
| CVE-2021-44228 | Log4Shell (dependency) | 09, 12 |
| CVE-2020-1472 | Zerologon (build auth) | 16 |

---

## Ferramentas Referenciadas

| Ferramenta | Uso | Capitulos |
|------------|-----|-----------|
| CMake | Build system | Todos |
| GCC/Clang | Compiladores | 04, 05, 06 |
| clang-tidy | Analise estatica | 07 |
| cppcheck | Analise estatica | 07 |
| Google Sanitizers | Runtime analysis | 05 |
| vcpkg | Package manager | 11 |
| Conan | Package manager | 11 |
| SPDX | SBOM format | 12 |
| CycloneDX | SBOM format | 12 |
| cosign/Sigstore | Artifact signing | 12 |
| CTest | Test runner | 14 |
| CPack | Packaging | 15 |
| GitHub Actions | CI/CD | 16 |
| GitLab CI | CI/CD | 16 |
