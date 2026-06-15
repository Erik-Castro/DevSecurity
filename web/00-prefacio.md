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
