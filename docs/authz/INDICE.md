---
layout: default
title: "INDICE"
---

# Autenticacao, Autorizacao e Controle de Acesso — Indice

---

| # | Capitulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefacio](00-prefacio.md) | Caso Misantropi4, motivacao |
| 01 | [Autenticacao vs Autorizacao](01-auth-vs-authz.md) | Conceitos, terminologia, flujo |
| 02 | [Metodos de Autenticacao](02-metodos-autenticacao.md) | Senhas, MFA, biometria, tokens |
| 03 | [Seguranca de Senhas](03-seguranca-senhas.md) | Hashing, salting, Argon2, PBKDF2 |
| 04 | [OAuth 2.0](04-oauth2.md) | Flows, tokens, scopes, PKCE |
| 05 | [OpenID Connect](05-openid-connect.md) | ID tokens, UserInfo, logout |
| 06 | [Single Sign-On (SSO)](06-sso.md) | SAML, OIDC SSO, federation |
| 07 | [Magic Links e Passwordless](07-magic-links.md) | Tokens temporarios, email magic links, deep linking |
| 08 | [WebAuthn e FIDO2](08-webauthn-fido2.md) | Passkeys, authenticators, biometria, hardware tokens |
| 09 | [RBAC](09-rbac.md) | Role-Based Access Control, NIST RBAC, hierarchical roles |
| 10 | [ABAC](10-abac.md) | Attribute-Based Access Control |
| 11 | [ReBAC](11-rebac.md) | Relationship-Based Access Control |
| 12 | [MAC, DAC e Hybrid Models](12-mac-dac.md) | Mandatory, Discretionary, hibridos |
| 13 | [Policy Engines](13-policy-engines.md) | OPA, Cedar, Casbin |
| 14 | [Ataques a Identidade](14-ataques-identidade.md) | Credential stuffing, brute force, session hijack |
| 15 | [Caso Misantropi4: IDAP](15-caso-misantropi4.md) | Analise completa do ataque |
| 16 | [Padroes Seguros de Implementacao](16-padroes-seguros.md) | Auth patterns, anti-patterns |
| 17 | [Compliance e Boas Praticas](17-compliance.md) | OWASP ASVS, LGPD, checklist |

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
         |       |       |
         12      13      14
         |       |       |
         +---+---+---+---+
             |
         15 -> 16 -> 17
```

---

## CVEs e Incidentes Documentados

| Incidente | Titulo | Capitulos |
|-----------|--------|-----------|
| Misantropi4/IDAP (2026) | Credenciais vazadas em sistema governamental | 03, 07, 14, 15 |
| Log4Shell (2021) | Bypass de autenticacao | 04, 16 |
| SolarWinds (2020) | Comprometimento de supply chain | 06, 14 |
| Colonial Pipeline (2021) | Credenciais comprometidas via VPN | 02, 14 |
| LastPass (2022) | Vault comprometido | 03, 16 |
| Uber (2022) | MFA fatigue attack | 02, 07 |
| Okta/Lapsus$ (2022) | Social engineering + session hijack | 05, 06, 14 |
| Imperial/Kaseya (2021) | Supply chain + credentials | 14 |

---

## Ferramentas e Bibliotecas

| Ferramenta | Uso | Capitulos |
|------------|-----|-----------|
| OAuth 2.0 | Authorization framework | 04, 05 |
| OpenID Connect | Authentication layer | 05, 06 |
| SAML 2.0 | Enterprise SSO | 06 |
| WebAuthn/FIDO2 | Passwordless auth | 07, 08 |
| OPA/Rego | Policy engine | 13 |
| Casbin | Authorization library | 13 |
| Cedar | AWS authorization | 13 |
| Keycloak | Identity provider | 06 |
| Auth0 | Authentication service | 04, 05 |
