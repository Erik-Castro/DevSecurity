# Prefácio — Desenvolvimento Seguro na Web

> *"A web é o maior sistema distribuído do mundo — e o mais atacado."*

---

## Por Que Este Livro Existe

Cada dia, bilhões de pessoas confiam seus dados mais sensíveis a aplicações web: dados bancários, históricos médicos, conversas privadas, documentos corporativos. E a cada dia, milhares de aplicações web são comprometidas por vulnerabilidades que poderiam ter sido evitadas.

O OWASP Top 10 não muda fundamentalmente há décadas. Injeção SQL continua no topo. XSS persiste. Broken authentication mata mais sistemas do que qualquer exploit exótico. O problema não é falta de conhecimento — é a lacuna entre conhecer e aplicar.

Este livro existe para fechar essa lacuna. Não é um catálogo de CVEs — é um guia prático de como construir aplicações web que resistam aos ataques mais comuns e mais perigosos do mundo real.

---

## Público-Alvo

### Desenvolvedores Full-Stack
Você constrói aplicações web com JavaScript/TypeScript, Python ou Go e precisa entender como proteger cada camada — do frontend ao banco de dados.

### Engenheiros de Segurança
Você audita aplicações web e precisa de um framework sistemático para identificar e corrigir vulnerabilidades.

### Tech Leads e Arquitetos
Você define padrões de segurança para equipes e precisa de checklists, decision trees e referências para guiar decisões.

### DevOps e Platform Engineers
Você configura pipelines, containers e infraestrutura e precisa garantir que a cadeia de deploy não introduza vulnerabilidades.

---

## Pré-Requisitos

| Tecnologia | Nível | Uso no Livro |
|------------|-------|-------------|
| HTML/CSS | Básico | Understanding of DOM, forms |
| JavaScript/TypeScript | Intermediário | CSP, DOMPurify, auth flows |
| Python | Intermediário | Flask/Django security |
| Go | Básico | API security, middleware |
| SQL | Intermediário | Injection prevention |
| HTTP | Intermediário | Headers, cookies, CORS |
| Linux/CLI | Básico | Tools, deployment |

---

## Estrutura do Livro

### Parte I: Fundamentos (Capítulos 00-03)
- Prefácio, introdução, OWASP Top 10, threat modeling

### Parte II: Vulnerabilidades (Capítulos 04-08)
- SQL injection, XSS, CSRF, authentication, authorization

### Parte III: Defesa (Capítulos 09-13)
- Crypto na web, input validation, API security, JavaScript security, server-side

### Parte IV: Operação (Capítulos 14-17)
- Containers, DevSecOps, pen testing, compliance, boas práticas

---

## Convenções

- **Texto**: Português brasileiro (PT-BR)
- **Código**: Identificadores em inglês
- **Exemplos**: JavaScript/TypeScript, Python, Go
- **CVEs**: Documentados com código vulnerável e corrigido
- **Checklists**: Items verificáveis para cada domínio

---

## Casos Reais Documentados

Este livro documenta 30+ CVEs e incidentes reais, incluindo:

| Incidente | Ano | Vulnerabilidade |
|-----------|-----|-----------------|
| Equifax Breach | 2017 | Apache Struts CVE-2017-5638 |
| Capital One | 2019 | SSRF + IAM misconfiguration |
| SolarWinds | 2020 | Supply chain compromise |
| Log4Shell | 2021 | JNDI injection CVE-2021-44228 |
| 3CX Supply Chain | 2023 | Trojanized update |
| MOVEit | 2023 | SQL injection CVE-2023-34362 |
| xz-utils | 2024 | Backdoor in build system |

---

## Como Usar Este Livro

**Para desenvolvedores que querem proteger suas aplicações:**
Comece pelo Capítulo 03 (OWASP Top 10), depois avance para os capítulos específicos das vulnerabilidades que mais os afetam.

**Para equipes que querem implementar DevSecOps:**
Foque nos capítulos 14-15 (Containers e DevSecOps), complementando com 09-11 para a camada de aplicação.

**Para auditores e pen testers:**
O Capítulo 16 (Penetration Testing) é seu ponto de entrada, com referências cruzadas para cada tipo de vulnerabilidade.

---

*[Próximo capítulo: 01 — Introdução à Segurança Web](01-introducao-seguranca-web.md)*

---

## Por Que a Segurança Web Importa Agora Mais do Que Nunca

### O Cenário Atual

Em 2024, mais de 5.6 bilhões de pessoas usam a internet. Cada uma interage com dezenas de aplicações web diariamente — banking, saúde, educação, governo, social media. A superfície de ataque é infinita.

### Números que Importam

| Métrica | Valor | Fonte |
|---------|-------|-------|
| Custo médio de breach (2024) | US$ 4.88M | IBM Cost of a Data Breach |
| Tempo médio para detectar um breach | 194 dias | IBM X-Force |
| % de breaches envolvendo dados web | 74% | Verizon DBIR |
| Ataques web mais comuns | Injection, XSS, Broken Auth | OWASP |
| Aumento de ataques web (ano a ano) | +38% | Akamai |

### O Ciclo da Insegurança

```
Desenvolvedor cria feature → Teste ignora segurança → Deploy sem hardening →
Atacante encontra falha → Dados expostos → Custo enorme → Correção emergencial
```

O objetivo deste livro é quebrar esse ciclo.

---

## Como Este Livro se Diferencia

### Não é um Catálogo de CVEs

Existem milhares de blogs listando CVEs. Este livro é diferente: cada vulnerabilidade é apresentada com **código vulnerável**, **código corrigido**, **explicação do por quê**, e **prevenção em múltiplos frameworks**.

### Abordagem Multiframework

Cada conceito é demonstrado em **3 frameworks**:
- **JavaScript/TypeScript** (Express.js, Next.js)
- **Python** (Flask, Django, FastAPI)
- **Go** (Gin, Echo, Chi)

Isso garante que o conhecimento é transferível, não dependente de uma stack específica.

### Foco em Padrões, Não em Versões

Ensinamos padrões (OWASP, NIST, CIS) que sobrevivem a atualizações de framework. Quando um framework muda, os padrões permanecem.

---

## Estrutura de Cada Capítulo

Cada capítulo segue este formato:

1. **Objetivos de Aprendizado** — O que você será capaz de fazer após ler
2. **Conceitos Fundamentais** — Teoria necessária, sem encher linguiça
3. **Ataques e Vetores** — Como o atacante explora a vulnerabilidade
4. **Código Vulnerável** — Exemplos reais do que NÃO fazer
5. **Código Corrigido** — Implementação segura com explicações
6. **CVEs e Casos Reais** — Vulnerabilidades documentadas e analisadas
7. **Checklists** — Itens verificáveis para cada domínio
8. **Exercícios** — Prática hands-on com soluções
9. **Referências** — Links para OWASP, CWE, RFCs, documentação oficial

---

## Pré-requisitos Detalhados

### Programação

| Tecnologia | Nível Mínimo | O que você deve saber |
|------------|-------------|----------------------|
| HTML/CSS | Básico | DOM, forms, eventos |
| JavaScript | Intermediário | async/await, promises, closures, fetch API |
| Python | Intermediário | requests, decorators, context managers |
| Go | Básico | Goroutines, interfaces, HTTP handlers |
| SQL | Intermediário | JOINs, subqueries, stored procedures |
| Git | Básico | add, commit, push, branches |

### Segurança

| Conceito | Nível | Onde aprender neste livro |
|----------|-------|--------------------------|
| HTTP protocol | Intermediário | Cap. 01-02 |
| TLS/SSL | Básico | Cap. 02, 09 |
| Cryptographic hashing | Básico | Cap. 07, 09 |
| Encoding (Base64, URL, HTML) | Básico | Cap. 05, 10 |

### Infraestrutura

| Ferramenta | Uso no Livro |
|------------|-------------|
| Docker | Cap. 14 — Container security |
| Kubernetes | Cap. 14 — Orchestration security |
| nginx/Caddy | Cap. 02 — Server configuration |
| PostgreSQL/MySQL | Cap. 04 — Database security |
| Redis | Cap. 07 — Session storage |
| Burp Suite / OWASP ZAP | Cap. 16 — Penetration testing |

---

## Comunidade e Suporte

- **Issues**: Abra no GitHub para erros técnicos ou dúvidas
- **Discussões**: Sugestões de capítulos, CVEs para adicionar
- **PRs**: Bem-vindos para correções e melhorias
- **Tradução**: Planejada para inglês e espanhol após conclusão

---

## Licença

Este material é licenciado sob **CC BY-NC-SA 4.0**:
- **BY**: Cite a fonte
- **NC**: Uso não-comercial (educação, estudo pessoal)
- **SA**: Derivações na mesma licença
- **Uso comercial**: Requer autorização

---

## Agradecimentos

À comunidade de segurança web que compartilha conhecimento abertamente:
- **OWASP** por manter os padrões e cheat sheets
- **PortSwigger** por tornar a pesquisa de segurança acessível
- **Cure53** pelo DOMPurify e pesquisas de segurança
- **Mozilla** pelas headers de segurança e Mozilla Observatory
- **Google** pelo Project Zero, CSP, e Trusted Types
- A todos os pesquisadores que documentam CVEs publicamente

---

*Bom estudo. A segurança web não é opcional — é responsabilidade profissional.*

*[Próximo capítulo: 01 — Introdução à Segurança Web](01-introducao-seguranca-web.md)*
