---
layout: default
title: "00-prefacio"
---

# Prefacio — Autenticacao, Autorizacao e Controle de Acesso

> *"Quem voce e nao importa se qualquer um pode ser voce."*

---

## Por Que Este Livro Existe

Em junho de 2026, o sistema brasileiro IDAP (Interface de Divulgacao de Alertas Publicos) foi comprometido por um atacante que usou **credenciais vazadas** de servidores publicos. O resultado: milhares de cidadaos em Sao Paulo, Rio de Janeiro, Parana, Mato Grosso do Sul e Distrito Federal receberam alertas de emergencia falsos durante a Copa do Mundo.

O ataque, conhecido como **"Misantropi4"**, expôs falhas criticas na autenticacao de sistemas governamentais:
- **Sem MFA**: Apenas login e senha
- **Captcha fraco**: Contas de matematica simples (2+2, 5+5)
- **Credenciais nao rotacionadas**: Funcionarios nao trocaram senhas em anos
- **Reuso de credenciais**: Mesma senha em multiplos sistemas governamentais
- **Excesso de privilegios**: Credenciais tinham acesso a regioes inteiras do Brasil

Este livro usa o caso Misantropi4 como fio condutor para ensinar autenticacao, autorizacao e controle de acesso de forma pragmatica. Cada capitulo inclui analise de como o ataque poderia ter sido prevenido.

---

## Publico-Alvo

- **Desenvolvedores Full-Stack** que constroem sistemas de autenticacao
- **Engenheiros de Seguranca** que auditan identidade e acesso
- **DevOps/Platform Engineers** que configuram SSO e OIDC
- **Arquitetos** que projetam sistemas de controle de acesso
- **Tech Leads** que definem padroes de seguranca

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| HTTP/HTTPS | Intermediario | TLS, cookies, headers |
| JavaScript/TypeScript | Intermediario | Frontend auth flows |
| Python ou Go | Basico | Backend examples |
| JWT/OAuth basico | Desejavel | Explorado em detalhe |

---

## Estrutura do Livro

### Parte I: Fundamentos (00-03)
- Prefacio, auth vs authorization, metodos de autenticacao, seguranca de senhas

### Parte II: Autenticacao Moderna (04-08)
- OAuth 2.0, OpenID Connect, SSO, Magic Links, WebAuthn/FIDO2

### Parte III: Modelos de Controle de Acesso (09-13)
- RBAC, ABAC, ReBAC, MAC/DAC, Policy Engines

### Parte IV: Seguranca e Implementacao (14-17)
- Ataques a identidade, Caso Misantropi4, padroes seguros, compliance
---


*[Próximo capítulo: 01 — Auth Vs Authz](01-auth-vs-authz.md)*
