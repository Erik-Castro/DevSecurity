---
layout: default
title: "ÍNDICE"
---

# CMake Seguro e Build Systems — Índice do Livro

> **Build Systems, Hardening, Supply Chain, Reproducibility**

---

## Sumário Rápido

| # | Capítulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefácio](00-prefacio.md) | Motivação, público-alvo, convenções |
| 01 | [Introdução ao CMake Moderno](01-introducao-cmake-moderno.md) | CMake 3.20+, targets, properties, generators |
| 02 | [Target Model e Properties](02-target-model-properties.md) | Target-based build, interface libraries, compile features |
| 03 | [Expressões e Funções](03-expressoes-funcoes.md) | Generator expressions, custom functions, macros |
| 04 | [Flags de Segurança do Compilador](04-flags-seguranca-compilador.md) | -fstack-protector, ASLR, DEP, FORTIFY, PIE |
| 05 | [Sanitizers e Debug Builds](05-sanitizers-debug.md) | ASan, TSan, UBSan, MSan, configuração, uso em CI/CD |
| 06 | [Hardening de Binários](06-hardening-binarios.md) | RELRO, NOW, stack canaries, strip, reproducible builds |
| 07 | [Análise Estática com CMake](07-analise-estatica.md) | clang-tidy, cppcheck, Infer, integration |
| 08 | [Builds Reprodutíveis](08-builds-reproduziveis.md) | Deterministic builds, hash verification, reprotest |
| 09 | [Finding Packages Seguro](09-finding-packages.md) | find_package, pkg-config, security implications |
| 10 | [FetchContent e ExternalProject](10-fetchcontent-external.md) | Secure fetching, pinning, hash verification |
| 11 | [vcpkg e Conan](11-vcpkg-conan.md) | Package managers: security, audit, lockfiles |
| 12 | [SBOM e Supply Chain](12-sbom-supply-chain.md) | SPDX, CycloneDX, Sigstore, SLSA |
| 13 | [Cross-Compilation](13-cross-compilation.md) | Toolchains, sysroots, secure cross-builds |
| 14 | [Testing no CMake](14-testing-cmake.md) | CTest, GoogleTest, fuzzing integration |
| 15 | [Instalação e Distribuição Segura](15-instalacao-distribuicao.md) | CMake install, CPack, signing |
| 16 | [Compliance e Normas para Build](16-compliance-normas.md) | Reproducible builds, SLSA, SBOM generation |
| 17 | [Conclusão e Checklist](17-conclusao-checklist.md) | Resumo, checklist de build seguro |
