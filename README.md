---
layout: default
title: "DevSecurity"
---

# DevSecurity — Livros de Desenvolvimento Seguro

> **Seguranca nao e um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositorio

Este e o repositorio central da colecao **DevSecurity**: livros tecnicos de desenvolvimento de software seguro, escritos em portugues, com foco pratico em **C++ moderno (C++17/20)** e arquitetura de sistemas.

O objetivo e preencher a lacuna entre teoria de seguranca e pratica de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padroes de codigo seguro, verificavel e pronto para producao.

### Numeros da Colecao

| Metrica | Valor |
|---------|-------|
| Livros publicados | 8 |
| Total de capitulos | 144 |
| Total de linhas | ~400.000+ |
| CVEs documentados | 380+ |
| Linguagens | C++17/20, Python, Bash, YAML, Go, Assembly, JS/TS, CMake, GitHub Actions |
| Idioma | Portugues (PT-BR) para texto, Ingles para codigo |

---

## Livros Publicados

### 1. Security-Driven Development com C++17

> *Desenvolvimento Seguro orientado a Seguranca — 17 capitulos | ~48.500 linhas | 100+ CVEs*

[Leia online](docs/book/INDICE.md)

---

### 2. DevSecOps na Pratica

> *Pipeline CI/CD Seguro, Containers, Cloud, Kubernetes — 18 capitulos | ~52.300 linhas | 60+ CVEs*

[Leia online](docs/devsecops/INDICE.md)

---

### 3. Engenharia e Analise de Malware em C++

> *Reverse Engineering, Debugging, Ransomware, Rootkits — 18 capitulos | ~55.600 linhas | 100+ malwares*

[Leia online](docs/malware/INDICE.md)

---

### 4. Concorrencia e Paralelismo Seguro em C++

> *Lock-Free, Deadlocks, Thread Pools, Coroutines — 18 capitulos | ~19.700 linhas*

[Leia online](docs/concurrency/INDICE.md)

---

### 5. Criptografia Engenheira em C++

> *Constant-Time, Side-Channels, TLS 1.3, PQC, FHE — 18 capitulos | ~66.400 linhas | 20+ CVEs*

[Leia online](docs/cryptography/INDICE.md)

---

### 6. Desenvolvimento Seguro na Web

> *OWASP Top 10, XSS, SQLi, Auth, API Security — 18 capitulos | ~57.800 linhas | 20+ CVEs*

[Leia online](docs/web/INDICE.md)

---

### 7. CMake Seguro e Build Systems

> *Flags de Seguranca, Sanitizers, Hardening, Supply Chain — 18 capitulos | ~52.500 linhas*

[Leia online](docs/cmake-book/INDICE.md)

---

### 8. GitHub Actions Pipelines Seguros

> *Triggers, Secrets, OIDC, Reusable Workflows, Supply Chain — 18 capitulos | ~49.000 linhas*

[Leia online](docs/github-actions/INDICE.md)

---

## Para Quem Escrevo

- **Desenvolvedores C++** que querem codigo seguro por design
- **Engenheiros de Seguranca** que auditam e revisam codigo
- **DevOps / Platform Engineers** que constroem pipelines seguros
- **Tech Leads** que definem padroes de build e deploy
- **Estudantes avancados** de ciencia da computacao

---

## Como Usar os Livros

Cada livro e **autocontido**, mas a sequencia recomendada por perfil:

```
Desenvolvedor:   SDD (1-5) -> SDD (6-12) -> DevSecOps (1-4) -> DevSecOps (5-9)
Eng. Seguranca:  Malware (1-4) -> Malware (5-10) -> SDD (13-17) -> DevSecOps (10-17)
DevOps/Platform: DevSecOps (1-9) -> DevSecOps (10-17) -> GitHub Actions (1-9)
Arquiteto:       SDD (1-3) -> DevSecOps (1-3) -> CMake (1-8) -> GitHub Actions (1-8)
Criptografia:    SDD (1-3) -> Criptografia (01-03) -> Criptografia (04-09) -> Criptografia (10-17)
```

---

## Estrutura do Repositorio

```
DevSecurity/
├── README.md
├── CONTRIBUTING.md
├── PROXIMOS-PROJETOS.md
├── docs/
│   ├── index.md
│   ├── book/           # Livro 1: SDD (C++17)
│   ├── devsecops/      # Livro 2: DevSecOps (Multi-lang)
│   ├── malware/        # Livro 3: Malware (C++17 + asm)
│   ├── concurrency/    # Livro 4: Concorrencia (C++17/20)
│   ├── cryptography/   # Livro 5: Criptografia (C++17)
│   ├── web/            # Livro 6: Web Security (JS/TS/Python/Go)
│   ├── cmake-book/     # Livro 7: CMake (CMake + C/C++)
│   └── github-actions/ # Livro 8: GitHub Actions (YAML/Bash)
├── epub/               # Versoes EPUB dos livros
├── openspec/           # SDD artifacts
└── scripts/            # Scripts auxiliares
```

---

## Contribuicoes

Este e um projeto de autoria individual, mas **feedback e bem-vindo**:

- **Issues**: Erros tecnicos, CVEs faltando, exemplos que nao compilam
- **Discussoes**: Sugestoes de temas, capitulos, formatos
- **Traducoes**: Se quiser traduzir para ingles/espanhol, abra issue primeiro

---

## Licenca

**CC BY-NC-SA 4.0** — Compartilhe, adapte, cite a fonte. Uso comercial requer autorizacao.

---

## Autor

Desenvolvedor de sistemas, foco em seguranca de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com seguranca de verdade."*
