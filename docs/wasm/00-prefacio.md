---
layout: default
title: "00-prefacio"
---

# Prefacio — WebAssembly Seguro

> *"WebAssembly nao e apenas para a web — e o futuro da computacao segura portavel."*

---

## Por Que Este Livro Existe

WebAssembly (Wasm) surgiu em 2017 como formato de compilacao para navegadores, mas rapidamente se expandiu para servidores, edge computing, plugins e ate blockchains. Hoje, WebAssembly e usado por:

- **Navegadores**: Figma, Google Earth, AutoCAD, Adobe Photoshop
- **Servidores**: Fastly Compute, Cloudflare Workers, Fermyon Spin
- **Edge**: WASI (WebAssembly System Interface) para computing distribuido
- **Plugins**: Extensao segura para aplicacoes (Envoy, VS Code)
- **Blockchain**: Smart contracts em Polkadot, NEAR, Cosmos

Mas essa explosao de uso traz novos desafios de seguranca. Um modulo Wasm malicioso pode:
- Executar codigo arbitrario dentro de um sandbox
- Acessar recursos do host via WASI
- Comprometer a supply chain de plugins
- Explorar vulnerabilidades no runtime
- Exfiltrar dados via side-channels

WebAssembly e projetado para seguranca — mas seguranca nao e automatica. Este livro mostra como usar Wasm de forma segura em qualquer ambiente.

---

## Publico-Alvo

- **Desenvolvedores Rust/C++** que compilam para WebAssembly
- **Engenheiros de Seguranca** que auditam modulos Wasm
- **DevOps/Platform Engineers** que rodam Wasm em producao
- **Arquitetos** que avaliam Wasm para plugins e extensao
- **Pesquisadores** em seguranca de sistemas compilados

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| Rust ou C++ | Intermediario | Linguagens de compilacao |
| Compiladores | Basico | wasm-pack, wasm-bindgen, Emscripten |
| Seguranca basica | Basico | Buffer overflows, memory safety |
| HTTP/WebSockets | Basico | Para exemplos client-server |

---

## Estrutura do Livro

### Parte I: Fundamentos (00-03)
- Prefacio, intro a Wasm, modelo de seguranca, WASI

### Parte II: Compilacao e Runtime (04-08)
- Rust/Wasm, C++/Emscripten, runtimes, sandbox, WASI

### Parte III: Seguranca em Profundidade (09-12)
- Memory safety, side-channels, supply chain, fuzzing

### Parte IV: Producao e Operacao (13-17)
- Plugins, edge computing, blockchain, compliance, boas praticas

---

## Convencoes

- **Texto**: Portugues brasileiro (PT-BR)
- **Codigo**: Identificadores em ingles
- **Exemplos**: Rust, C++, WebAssembly Text Format (WAT)
- **Plataformas**: Browser, WASI, Docker, Kubernetes
---


*[Próximo capítulo: 01 — Introducao Webassembly](01-introducao-webassembly.md)*
