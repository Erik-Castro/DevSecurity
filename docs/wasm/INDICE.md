---
layout: default
title: "INDICE"
---

# WebAssembly Seguro — Indice do Livro

---

| # | Capitulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefacio](00-prefacio.md) | Motivacao, publico-alvo |
| 01 | [Introducao ao WebAssembly](01-introducao-webassembly.md) | Historia, arquitetura, bytecode |
| 02 | [Modelo de Seguranca do Wasm](02-modelo-seguranca.md) | Sandbox, memory model, control flow |
| 03 | [WASI e System Interface](03-wasi-system-interface.md) | WASI preview1/preview2, capabilities |
| 04 | [Compilacao: Rust para Wasm](04-rust-wasm.md) | wasm-pack, wasm-bindgen, trunk |
| 05 | [Compilacao: C++ para Wasm](05-cpp-emscripten.md) | Emscripten, toolchain, flags |
| 06 | [Runtimes de WebAssembly](06-runtimes.md) | V8, SpiderMonkey, Wasmtime, Wasmer, WasmEdge |
| 07 | [Sandboxing e Isolamento](07-sandboxing.md) | Process isolation, gVisor, Firecracker |
| 08 | [Component Model](08-component-model.md) | WASI preview2, component interface types |
| 09 | [Memory Safety em Wasm](09-memory-safety.md) | Bounds checking, guard pages, ASLR |
| 10 | [Side-Channels em Wasm](10-side-channels.md) | Cache-timing, Spectre, mitigations |
| 11 | [Supply Chain de Plugins](11-supply-chain-plugins.md) | Signing, verification, attestation |
| 12 | [Fuzzing de Modulos Wasm](12-fuzzing.md) | Structure-aware fuzzing, coverage |
| 13 | [Plugins Seguros](13-plugins-seguros.md) | Envoy, VS Code, Extism |
| 14 | [Wasm no Edge Computing](14-edge-computing.md) | Cloudflare Workers, Fastly |
| 15 | [Wasm e Blockchain](15-blockchain.md) | Smart contracts, Polkadot, NEAR |
| 16 | [Compliance e Normas](16-compliance.md) | NIST, OWASP, certificacoes |
| 17 | [Boas Praticas e Checklist](17-boas-praticas.md) | Anti-patterns, decision trees, checklist |

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

## CVEs e Incidentes

| Incidente | Titulo | Capitulos |
|-----------|--------|-----------|
| CVE-2021-30672 | V8 JIT compilation bug | 06, 10 |
| CVE-2020-6492 | Chrome V8 type confusion | 06 |
| Chrome V8 Spectre mitigations | Browser-side Spectre | 10 |
| npm package typosquatting | Supply chain | 11 |
| Envoy WASM plugin vulnerability | Plugin security | 13 |

---

## Ferramentas

| Ferramenta | Uso | Capitulos |
|------------|-----|-----------|
| Rust + wasm-pack | Compilacao Rust->Wasm | 04 |
| Emscripten | Compilacao C++->Wasm | 05 |
| Wasmtime | Runtime WASI | 06 |
| Wasmer | Runtime Wasm | 06 |
| WasmEdge | Runtime edge | 06 |
| wabt | WebAssembly Binary Toolkit | 01 |
| wasm-tools | CLI para Wasm | 04, 08 |
| wasm-bindgen | Figma Rust/JS | 04 |
| Extism | Plugin framework | 13 |
