# Próximos Projetos — Livros Open-Source

> Diretrizes do projeto: livros técnicos gratuitos em Markdown, linguagem PT-BR para texto, código em inglês (C++17 ou linguagem apropriada), mínimo 800 linhas por capítulo, 17+ capítulos, com casos públicos documentados (CVEs).

---

## Livro 1: Security-Driven Development (CONCLUÍDO)

- 17 capítulos | ~44.700 linhas | C++17
- [Indice](book/INDICE.md) | [Diretório](book/)

## Livro 2: DevSecOps na Prática (EM ANDAMENTO)

- Pipeline CI/CD seguro, ferramentas SAST/DAST/SCA, container security, GitOps seguro
- Mais operacional e menos teórico que o livro anterior
- Público: devs, ops, engenheiros de segurança
- [Diretório](devsecops/)

---

## Backlog de Livros

### Tier 1 — Alta demanda e sinergia direta

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 3 | **Secure Coding in C** | C puro, sistemas embarcados, kernels | C |
| 4 | **Arquitetura de Software Seguro** | Design de sistemas distribuídos, microsserviços | C++ / conceitual |
| 5 | **Programação Concorrente Segura em C++** | Concorrência, lock-free, memory model | C++17 |

### Tier 2 — Nichos com pouca cobertura em PT-BR

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 6 | **Reverse Engineering e Análise de Malware** | Forense de binários, engenharia reversa | C++ / Assembly |
| 7 | **Criptografia Aplicada com C++** | libsodium/OpenSSL, TLS, PKI, tokenização | C++17 |
| 8 | **Redes Seguras: De TCP/IP a Zero Trust** | Protocolo a protocolo com implementações C++ | C++17 |

### Tier 3 — Ampliam o alcance do projeto

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 9 | **Testes de Segurança Automatizados** | Fuzzing, property-based testing, mutation testing | C++ / multi |
| 10 | **Compliance Técnico para Desenvolvedores** | LGPD/GDPR, SOC2, SBOM, supply chain | Conceitual + código |
| 11 | **Kernel Linux: Desenvolvimento e Segurança** | user-space a kernel, seccomp, capabilities | C |

### Tier 4 — Expansão de linguagem

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 12 | **Secure Coding in Rust** | Rust para segurança de sistemas | Rust |
| 13 | **Python para Segurança de Software** | Automação, análise de dados, tooling | Python |

---

## Critérios de Seleção

- **Demanda**: livros com maior audiência potencial primeiro
- **Sinergia**: livros que complementam os anteriores
- **Diferenciação**: pouca cobertura gratuita em PT-BR
- **Viabilidade**: ferramentas e libs disponíveis para exemplos práticos
