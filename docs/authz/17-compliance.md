# Capítulo 17 — Compliance e Boas Práticas

## Introdução

Compliance não é burocracia — é a tradução regulatória de boas práticas de segurança que já deveriam existir. Quando uma organização ignora compliance, não está "economizando esforço"; está acumulando risco jurídico, financeiro, e reputacional que explodirá em algum momento. O caso Misantropi4 contra o IDAP ilustra isso com clareza: um sistema governamental brasileiro processando dados de milhões de cidadãos, exposto por falhas que qualquer framework de compliance teria identificado.

Este capítulo é um guia prático de compliance e boas práticas para autenticação, autorização, e controle de acesso. Cada seção mapeia requisitos regulatórios específicos para controles técnicos implementáveis. Ao final, você terá um checklist de 50+ itens, árvores de decisão, e referências rápidas para implementação.

---

## 17.1 OWASP ASVS — Application Security Verification Standard

### 17.1.1 Visão geral do ASVS

O OWASP ASVS é o padrão mais abrangente para verificação de segurança de aplicações. Diferente do OWASP Top 10 (que lista vulnerabilidades), o ASVS define níveis de verificação e requisitos específicos para cada área de segurança.

**Níveis de verificação:**

| Nível | Descrição | Uso Recomendado |
|-------|-----------|-----------------|
| Nível 1 | Mínimo — defesas contra ameaças de baixa habilidade | Aplicações internas, protótipos |
| Nível 2 | Padrão — defesas contra atacantes com habilidade média | Aplicações web com dados sensíveis |
| Nível 3 | Avançado — defesas contra atacantes com habilidade elevada | Sistemas financeiros, governamentais, healthcare |

Para o contexto do caso Misantropi4 (sistema governamental com dados de milhões de cidadãos), o **Nível 3** seria o mínimo aceitável.

### 17.1.2 Requisitos ASVS para autenticação (Capítulo 2)

O ASVS Capítulo 2 define requisitos específicos para autenticação. Os mais relevantes para nosso contexto:

**V2.1 — Autenticação de Senha:**

```
Requisito 2.1.1: Nível 1
"Passwords devem ser armazenadas de forma que sejam resilientes a ataques offline."

Controles técnicos:
- Argon2id com parâmetros mínimos: 64MB memória, 3 iterações, 4 paralelismo
- Sal único por senha, gerado com CSPRNG
- Hash armazenado em campo dedicado (nunca em logs, nunca em responses)

Verificação:
SELECT password_hash FROM users LIMIT 1;
-- Deve conter prefixo $argon2id$
```

```
Requisito 2.1.7: Nível 1
"Passwords devem ter no mínimo 12 caracteres (NIST SP 800-63B)."

Controles técnicos:
- Validação server-side com minLength: 12
- Suporte a Unicode e espaços
- Sem limite máximo artificial (NIST recomenda >= 64 caracteres)
- Sem requisitos de complexidade excessivos (caixa alta/número/special)

Verificação:
-- Política de senha armazenada
SELECT policy FROM password_policies WHERE active = true;
-- Deve retornar minLength >= 12
```

```
Requisito 2.1.10: Nível 2
"Devem existir mecanismos para detectar, prevenir, e recuperar de accounts compromise."

Controles técnicos:
- Rate limiting com escalação
- Account lockout após tentativas失败
- Notificação de login suspeito
- Recovery codes para MFA
- Session invalidation após detecção

Verificação:
-- Verificar se rate limiting está ativo
-- Verificar se lockout está configurado
-- Verificar se notificações estão sendo enviadas
```

**V2.2 — Autenticação Genérica:**

```
Requisito 2.2.1: Nível 1
"Autenticação deve ser realizada em um servidor seguro."

Controles técnicos:
- Nunca confiar em autenticação client-side
- Validação de credenciais sempre server-side
- Tokens validados no servidor em cada request

Verificação:
-- Verificar se endpoints de login retornam tokens
-- Verificar se tokens são validados em cada request
-- Verificar se não existe bypass client-side
```

```
Requisito 2.2.2: Nível 2
"O sistema deve implementar controle de brute force."

Controles técnicos:
- Rate limiting por IP e por usuário
- Account lockout com escalação
- CAPTCHA após N tentativas (opcional)
- Logging de todas as tentativas

Verificação:
-- Testar brute force com 100 tentativas
-- Verificar se lockout ocorre
-- Verificar se rate limiting responde com 429
```

```
Requisito 2.2.5: Nível 2
"Mensagens de erro de autenticação não devem revelar se o usuário existe."

Controles técnicos:
- Mensagem genérica: "Credenciais inválidas"
- Tempo constante para usuários inexistentes
- Sem diferenciação entre "usuário não existe" e "senha incorreta"

Verificação:
-- Testar com email existente e inexistente
-- Medir tempo de resposta (deve ser similar)
-- Verificar mensagem de erro (deve ser idêntica)
```

**V2.3 — Autenticação de Fatores Múltiplos:**

```
Requisito 2.3.1: Nível 2
"O sistema deve suportar autenticação de fatores múltiplos."

Controles técnicos:
- TOTP como fator adicional
- WebAuthn/FIDO2 para passwordless
- SMS como fallback (menos seguro)
- Push notifications para mobile

Verificação:
-- Verificar se MFA está disponível
-- Verificar se TOTP funciona corretamente
-- Verificar se backup codes são gerados
```

```
Requisito 2.3.4: Nível 3
"MFA deve ser obrigatório para contas privilegiadas."

Controles técnicos:
- Admin/operator accounts devem ter MFA ativo
- Login sem MFA deve retornar erro 403
- Setup de MFA deve ser fluxo guiado
- Backup codes devem ser fornecidos

Verificação:
-- Criar conta admin sem MFA
-- Tentar acessar endpoint protegido
-- Deve retornar erro de MFA obrigatório
```

**V2.4 — Autenticação de Autenticadores:**

```
Requisito 2.4.1: Nível 2
"Credenciais de autenticação devem ser armazenadas de forma segura."

Controles técnicos:
- Secrets de TOTP encriptados em repouso
- Chaves de WebAuthn em hardware (quando possível)
- Backup codes hasheados com SHA-256
- Rotação de secrets periodicamente

Verificação:
-- Verificar se TOTP secrets estão encriptados
-- Verificar se backup codes estão hasheados
-- Verificar se chaves WebAuthn são armazenadas seguramente
```

---

## 17.2 OWASP Top 10 — Vulnerabilidades Relacionadas a Auth/AuthZ

### 17.2.1 A07:2021 — Identification and Authentication Failures

Esta categoria do OWASP Top 10 2021 é diretamente relevante para nosso contexto. Ela consolida a antiga A02 (Broken Authentication) e inclui:

**Sub-vulnerabilidades:**

1. **Permitir credenciais fraca** (A07:2021-02): O IDAP possivelmente não impôs políticas de senha adequadas
2. **Permitir brute force ou ataques de credentials stuffing** (A07:2021-03): Rate limiting insuficiente
3. **Permitir senhas fracas, well-known, ou compromise** (A07:2021-04): Sem verificação contra listas de senhas vazadas

**Controles OWASP para A07:**

```
// Checklist de mitigação A07:2021

// 1. Não permitir credenciais padrão
if (email === 'admin@example.com' && password === 'admin') {
  reject('Credenciais padrão não são permitidas');
}

// 2. Implementar verificação de senhas vazadas (Have I Been Pwned API)
async function checkPwnedPassword(password) {
  const sha1 = crypto.createHash('sha1').update(password).digest('hex').toUpperCase();
  const prefix = sha1.substring(0, 5);
  const suffix = sha1.substring(5);

  const response = await fetch(`https://api.pwnedpasswords.com/range/${prefix}`);
  const text = await response.text();

  return text.includes(suffix);
}

// 3. Rate limiting robusto
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  skipSuccessfulRequests: true
});

// 4. MFA obrigatório para contas sensíveis
if (user.role === 'admin' && !user.mfa_enabled) {
  reject('MFA obrigatório para contas administrativas');
}

// 5. Passwordless quando possível (WebAuthn)
// 6. Gerenciamento seguro de sessões
// 7. Desabilitar autocomplete em forms de login
```

### 17.2.2 A01:2021 — Broken Access Control

Esta é a vulnerabilidade mais comum no OWASP Top 10 2021 e diretamente relacionada ao caso Misantropi4:

**Sub-vulnerabilidades:**

1. **Violação do princípio de menor privilege** (A01:2021-02): Usuários com acesso excessivo
2. **Escopo de funcionalidade desatualizado** (A01:2021-04): Permissões não atualizadas
3. **Controle de acesso ausente em API** (A01:2021-05): Endpoints sem verificação

**Controles OWASP para A01:**

```
// Checklist de mitigação A01:2021

// 1. Negar por padrão
// Exceto para recursos públicos, o acesso deve ser negado por padrão

// 2. Implementar mecanismos de acesso uma única vez na API
// Todas as chamadas de API devem ser verificadas

// 3. Limitar o acesso por controles de API
// Usuários normais não devem ter acesso a endpoints admin

// 4. Registrar falhas de controle de acesso
// Alertas para tentativas de escalonamento de privilégio

// 5. Desabilitar director listing no servidor web
// Impedir acesso a diretórios sem index

// 6. Desabilitar acesso a arquivos sensíveis (ex: .git, .env)
// Excepto para aqueles que precisam ser servidos

// 7. Usar templates de erro sem informações sensíveis
// NUNCA expor stack traces em produção
```

### 17.2.3 A04:2021 — Insecure Design

O Insecure Design é relevante quando a arquitetura de autenticação é fundamentalmente falha:

**Exemplos no contexto Misantropi4:**

```
// Design inseguro: autenticação sem MFA em sistema governamental
// Design inseguro: roles com excesso de privilégios
// Design inseguro: sem rate limiting em endpoints sensíveis
// Design inseguro: sem audit logging para detecção de incidentes

// Controles:
// 1. Usar threat modeling (STRIDE) na fase de design
// 2. Implementar padrões de segurança (este livro)
// 3. Revisão de design por equipe de segurança
// 4. Testes de segurança antes do deploy
```

### 17.2.4 A02:2021 — Cryptographic Failures

Relevante para armazenamento de credenciais e tokens:

```
// Falhas criptográficas comuns em autenticação:

// 1. Armazenar senhas com MD5 ou SHA-1 (hash fraco)
// CORRETO: Argon2id

// 2. Usar JWT com algoritmo "none"
// CORRETO: RS256 ou ES256

// 3. Chaves JWT fracas ou previsíveis
// CORRETO: RSA 2048+ ou ECDSA P-256+

// 4. TLS 1.0/1.1 (versões obsoletas)
// CORRETO: TLS 1.2+ obrigatório

// 5. Senhas em logs ou mensagens de erro
// CORRETO: Nunca logar credenciais
```

### 17.2.5 A05:2021 — Security Misconfiguration

Configurações incorretas que comprometem autenticação:

```
// Configurações de segurança para verificar:

// 1. CORS configurado corretamente
app.use(cors({
  origin: ['https://meudominio.com'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
  maxAge: 86400
}));

// 2. Headers de segurança habilitados
// 3. Debug mode desabilitado em produção
// 4. Error pages sem informações sensíveis
// 5. Server tokens desabilitados (Server, X-Powered-By)
// 6. Cookie flags configurados
// 7. HSTS habilitado
```

### 17.2.6 A08:2021 — Software and Data Integrity Failures

Relevante para integridade de tokens e sessões:

```
// 1. Verificar integridade de JWT
const payload = jwt.verify(token, publicKey, {
  algorithms: ['RS256'],  // Nunca aceitar 'none'
  issuer: 'auth.example.com',
  audience: 'api.example.com'
});

// 2. Verificar integridade de sessões
// Usar HMAC ou assinatura digital em cookies de sessão

// 3. Verificar integridade de código
// Usar dependências assinadas e verificadas

// 4. Verificar integridade de logs de auditoria
// Chain de hash para detecção de adulteração
```

---

## 17.3 NIST SP 800-63 — Digital Identity Guidelines

### 17.3.1 Visão geral do NIST SP 800-63

O NIST SP 800-63 é o guia definitivo para identidade digital, publicado pelo National Institute of Standards and Technology dos EUA. Ele define níveis de garantia de identidade (IAL), autenticação (AAL), e federação (FAL).

**Níveis de Garantia de Autenticação (AAL):**

| Nível | Requisitos | MFA | Re-authentication |
|-------|------------|-----|-------------------|
| AAL1 | Autenticação de fator único | Não obrigatório | 30 dias |
| AAL2 | Autenticação de dois fatores | Obrigatório | 12 horas |
| AAL3 | Autenticação de dois fatores com hardware | Hardware obrigatório | 12 horas |

**Para o contexto Misantropi4**: AAL2 seria o mínimo aceitável para um sistema governamental com dados de milhões de cidadãos.

### 17.3.2 Requisitos NIST para senhas (SP 800-63B)

O NIST SP 800-63B revolucionou as recomendações de senhas ao abandonar requisitos de complexidade em favor de comprimento mínimo e verificação contra senhas comprometidas:

```
// Requisitos NIST SP 800-63B para senhas:

// 1. Comprimento mínimo: 8 caracteres (recomendado: 12+)
// 2. Suporte a Unicode e espaços
// 3. Sem limite máximo artificial (recomendado: >= 64 caracteres)
// 4. Verificar contra listas de senhas comprometidas
// 5. NÃO impor requisitos de complexidade excessivos
// 6. NÃO impor rotação periódica (exceto após comprometimento)
// 7. Permitir colar senhas (password managers)
// 8. Feedback em tempo real de força da senha

// Implementação:
class NISTPasswordPolicy {
  constructor() {
    this.minLength = 8;  // Mínimo NIST
    this.recommendedLength = 12;  // Recomendado
    this.maxLength = 64;  // Máximo prático
    this.maxAttempts = 100;  // Verificar 100k senhas comprometidas
  }

  validate(password) {
    const errors = [];

    if (password.length < this.minLength) {
      errors.push(`Mínimo de ${this.minLength} caracteres`);
    }

    if (password.length > this.maxLength) {
      errors.push(`Máximo de ${this.maxLength} caracteres`);
    }

    return errors;
  }

  async checkCompromised(password) {
    // Verificar contra Have I Been Pwned
    const sha1 = crypto.createHash('sha1')
      .update(password)
      .digest('hex')
      .toUpperCase();

    const prefix = sha1.substring(0, 5);
    const suffix = sha1.substring(5);

    const response = await fetch(
      `https://api.pwnedpasswords.com/range/${prefix}`,
      { headers: { 'Add-Padding': 'true' } }
    );

    const text = await response.text();
    const lines = text.split('\n');

    for (const line of lines) {
      const [hashSuffix, count] = line.split(':');
      if (hashSuffix.trim() === suffix) {
        return parseInt(count.trim()) > 0;
      }
    }

    return false;
  }
}
```

### 17.3.3 Requisitos NIST para autenticação (SP 800-63B)

```
// Requisitos NIST SP 800-63B para autenticação:

// 1. Autenticação deve ser realizada em canal seguro (TLS 1.2+)
// 2. Mensagens de erro não devem diferenciar "usuário não existe" de "senha incorreta"
// 3. Rate limiting deve ser implementado
// 4. Account lockout deve ser temporário (não permanente)
// 5. Autenticadores devem ser resistentes a replay
// 6. Autenticadores devem ser armazenados de forma segura
// 7. Autenticadores devem ser invalidados após uso (tokens de uso único)
// 8. Autenticadores devem ser protegidos contra interceptação

// Implementação de account lockout NIST-compliant:
class NISTAccountLockout {
  constructor() {
    this.maxAttempts = 100;  // NIST permite mais tentativas
    this.lockoutDuration = 30 * 60 * 1000;  // 30 minutos (temporário)
    this.lockoutThreshold = 100;  // Após 100 tentativas
  }

  async handleFailedAttempt(userId) {
    const attempts = await this.getAttemptCount(userId);

    if (attempts >= this.lockoutThreshold) {
      await this.lockAccount(userId, this.lockoutDuration);
      await this.notifyUser(userId, 'account_locked');
      return { locked: true, duration: this.lockoutDuration };
    }

    return { locked: false, remaining: this.lockoutThreshold - attempts };
  }

  async lockAccount(userId, duration) {
    await db.updateUser(userId, {
      locked_until: new Date(Date.now() + duration),
      lockout_reason: 'too_many_failed_attempts'
    });
  }
}
```

### 17.3.4 Requisitos NIST para federação (SP 800-63C)

Para sistemas que usam SSO ou OIDC, o NIST SP 800-63C define:

```
// Requisitos NIST SP 800-63C para federação:

// 1._assertions devem ser assinadas digitalmente
// 2._assertions devem ter tempo de vida limitado
// 3._assertions devem ser validadas no receptor
// 4. Federação deve usar protocolos padrão (OIDC, SAML)
// 5. Identifiers devem ser persistentes e não reutilizados
// 6. Logout deve ser propagado entre partes
// 7. Privacidade deve ser considerada (data minimization)

// Implementação OIDC NIST-compliant:
class NISTOIDCClient {
  constructor(config) {
    this.issuer = config.issuer;
    this.jwksUri = config.jwksUri;
    this.allowedAlgorithms = ['RS256', 'ES256'];
    this.maxAssertionAge = 300;  // 5 minutos
  }

  async validateAssertion(assertion) {
    // 1. Verificar assinatura
    const signingKey = await this.getSigningKey(assertion.header.kid);
    const payload = jwt.verify(assertion.token, signingKey, {
      algorithms: this.allowedAlgorithms,
      issuer: this.issuer
    });

    // 2. Verificar idade da assertion
    const age = Math.floor(Date.now() / 1000) - payload.iat;
    if (age > this.maxAssertionAge) {
      throw new Error('Assertion too old');
    }

    // 3. Verificar audiência
    if (payload.aud !== process.env.API_AUDIENCE) {
      throw new Error('Invalid audience');
    }

    // 4. Verificar nonce (prevenir replay)
    if (await this.isNonceUsed(payload.nonce)) {
      throw new Error('Nonce already used');
    }
    await this.markNonceUsed(payload.nonce);

    return payload;
  }
}
```

---

## 17.4 LGPD — Lei Geral de Proteção de Dados

### 17.4.1 Requisitos LGPD para autenticação

A Lei Geral de Proteção de Dados (LGPD) — Lei nº 13.709/2018 — é a legislação brasileira de proteção de dados. Ela não define requisitos técnicos específicos para autenticação, mas estabelece princípios que impactam diretamente a implementação:

**Art. 46 — Segurança e Sigilo:**

```
// LGPD Art. 46: "Os agentes de tratamento devem adotar medidas de segurança,
// técnicas e administrativas aptas a proteger os dados pessoais de acessos
// não autorizados e de situações acidentais ou ilícitas de destruição,
// perda, alteração, comunicação ou qualquer forma de tratamento inadequado
// ou ilícito."

// Controles técnicos para compliance LGPD:
class LGPDAuthControls {
  // 1. Autenticação robusta (Art. 46)
  static getAuthenticationRequirements() {
    return {
      passwordPolicy: {
        minLength: 12,  // LGPD não define, mas 12 é best practice
        requireMFA: true,  // Para dados sensíveis
        maxAge: 90,  // Dias
        historyCount: 12  // Não reutilizar
      },
      sessionManagement: {
        maxAge: 30 * 60 * 1000,  // 30 minutos
        absoluteTimeout: 24 * 60 * 60 * 1000,  // 24 horas
        regenerateOnLogin: true,
        invalidateOnLogout: true
      },
      auditLogging: {
        logAuthenticationEvents: true,
        logAuthorizationDecisions: true,
        retentionPeriod: 5 * 365 * 24 * 60 * 60,  // 5 anos
        immutable: true
      }
    };
  }

  // 2. Minimização de dados (Art. 6, III)
  static getDataMinimizationRules() {
    return {
      loginLogs: {
        collect: ['userId', 'ip', 'userAgent', 'timestamp', 'result'],
        neverCollect: ['password', 'token', 'mfaCode'],
        anonymizeAfter: 90 * 24 * 60 * 60  // 90 dias
      },
      sessionData: {
        collect: ['userId', 'createdAt', 'lastActiveAt', 'ip'],
        neverCollect: ['password', 'permissions'],
        maxSessions: 5  // Limite de sessões simultâneas
      }
    };
  }

  // 3. Direito do titular (Art. 18)
  static getDataSubjectRights() {
    return {
      access: {
        description: 'Confirmar existência de tratamento',
        implementation: 'Endpoint /api/my-data que retorna dados do usuário',
        responseTime: 15  // dias
      },
      correction: {
        description: 'Corrigir dados incompletos ou inexatos',
        implementation: 'Endpoint /api/my-data/update',
        responseTime: 15
      },
      anonymization: {
        description: 'Anonimizar dados desnecessários',
        implementation: 'Soft delete com anonymization após 30 dias',
        responseTime: 15
      },
      portability: {
        description: 'Exportar dados em formato estruturado',
        implementation: 'Endpoint /api/my-data/export (JSON/CSV)',
        responseTime: 15
      }
    };
  }

  // 4. Comunicação de incidentes (Art. 48)
  static getIncidentResponseRequirements() {
    return {
      notifyAuthority: {
        timeframe: 'razoável',  // ANPD interpreta como 2 dias úteis
        authority: 'ANPD',
        channel: 'canal oficial da ANPD'
      },
      notifyDataSubject: {
        when: 'risco ou dano relevante',
        timeframe: 'em prazo razoável',
        content: ['natureza dos dados', 'informações de contato', 'consequências', 'medidas adotadas']
      }
    };
  }
}
```

### 17.4.2 Mapeamento LGPD para controles técnicos

| Princípio LGPD | Artigo | Controle Técnico | Implementação |
|----------------|--------|------------------|---------------|
| Finalidade | 6, I | Logging mínimo | Logar apenas eventos necessários |
| Adequação | 6, II | Autenticação proporcional | MFA para dados sensíveis |
| Necessidade | 6, III | Least privilege | RBAC com permissões mínimas |
| Qualidade | 6, IV | Validação de dados | Validação server-side |
| Segurança | 6, V | Controles de acesso | Autenticação + autorização |
| Prevenção | 6, VII | Security by design | Threat modeling, secure SDLC |
| Responsabilização | 6, X | Audit logging | Logs imutáveis, retenção |
| Não discriminação | 6, IX | Acesso igualitário | Mesmos padrões para todos |

### 17.4.3 DPO e governança de autenticação

```
// O DPO (Data Protection Officer) deve supervisionar:

// 1. Política de autenticação
class AuthenticationPolicy {
  static getPolicy() {
    return {
      version: '2.0',
      lastReview: '2026-01-15',
      nextReview: '2026-07-15',
      approvedBy: 'DPO',
      scope: 'Todos os sistemas que tratam dados pessoais',

      requirements: {
        passwords: 'NIST SP 800-63B + LGPD Art. 46',
        mfa: 'Obrigatório para acessos remotos e dados sensíveis',
        sessions: 'Timeout 30min, absolute 24h',
        audit: 'Retenção mínima 5 anos',
        incident: 'Comunicação em 2 dias úteis à ANPD'
      },

      exceptions: [
        {
          system: 'Sistema legado X',
          exception: 'MFA não implementado',
          risk: 'Alto',
          mitigation: 'Acesso restrito a rede interna',
          expiresAt: '2026-12-31',
          approvedBy: 'CISO'
        }
      ]
    };
  }
}
```

---

## 17.5 GDPR Article 32 — Security of Processing

### 17.5.1 Requisitos GDPR para autenticação

O GDPR (General Data Protection Regulation) da União Europeia, Artigo 32, define requisitos de segurança para processamento de dados pessoais. Embora a LGPD seja a legislação brasileira, muitas organizações brasileiras também devem cumprir GDPR (processamento de dados de cidadãos europeus):

```
// GDPR Art. 32 — "O responsável pelo tratamento e o operador devem
// implementar medidas técnicas e organizacionais adequadas ao nível de
// risco, incluindo, entre outras:
//   a) Ofuscação e criptografia de dados pessoais;
//   b) Capacidade de garantir confidencialidade, integridade, disponibilidade
//      e resiliência dos sistemas e serviços;
//   c) Capacidade de restaurar a disponibilidade e acesso aos dados pessoais
//      em tempo oportuno em caso de incidente físico ou técnico;
//   d) Processo regular de teste, avaliação e medição da eficácia das medidas
//      técnicas e organizacionais para garantir a segurança do tratamento."

// Controles GDPR para autenticação:
class GDPPAuthControls {
  static getTechnicalMeasures() {
    return {
      // a) Criptografia
      encryption: {
        atRest: 'AES-256-GCM para dados sensíveis',
        inTransit: 'TLS 1.3 obrigatório',
        keyManagement: 'HSM ou cloud KMS',
        passwordHashing: 'Argon2id'
      },

      // b) Confidencialidade, integridade, disponibilidade
      confidentiality: {
        accessControl: 'RBAC + ABAC',
        leastPrivilege: true,
        needToKnow: true,
        segregationOfDuties: true
      },
      integrity: {
        auditLogging: true,
        tamperDetection: 'Chain de hash em logs',
        inputValidation: 'Server-side validation',
        digitalSignatures: 'JWT assinados com RS256'
      },
      availability: {
        rateLimiting: true,
        ddosProtection: true,
        backupStrategy: 'Diário com retenção 30 dias',
        disasterRecovery: 'RPO 1h, RTO 4h'
      },

      // c) Recuperação de incidentes
      incidentRecovery: {
        backupFrequency: 'Diário',
        backupRetention: '30 dias',
        recoveryProcedure: 'Documentado e testado semestralmente',
        notificationTimeframe: '72 horas (Art. 33)'
      },

      // d) Teste e avaliação
      testing: {
        penetrationTesting: 'Anual mínimo',
        vulnerabilityScanning: 'Mensal',
        securityAudits: 'Semestral',
        incidentResponseDrills: 'Trimestral'
      }
    };
  }
}
```

### 17.5.2 Data Protection Impact Assessment (DPIA)

O GDPR Art. 35 exige DPIA para tratamentos de alto risco. Autenticação de sistemas com dados sensíveis geralmente se qualifica:

```
// DPIA para sistema de autenticação
const dpiaTemplate = {
  project: 'Sistema de Autenticação',
  description: 'Autenticação e autorização de usuários',

  necessity: {
    purpose: 'Controle de acesso a dados pessoais',
    legalBasis: 'Art. 6, 1(f) — Legítimo interesse',
    dataTypes: ['email', 'nome', 'IP', 'user agent', 'timestamps'],
    dataSubjects: 'Usuários do sistema',
    volume: '10.000+ usuários'
  },

  risks: [
    {
      risk: 'Credential stuffing',
      likelihood: 'Alta',
      impact: 'Alto',
      mitigations: ['Rate limiting', 'MFA', 'Breach detection'],
      residualRisk: 'Baixo'
    },
    {
      risk: 'Session hijacking',
      likelihood: 'Média',
      impact: 'Alto',
      mitigations: ['Secure cookies', 'Token rotation', 'IP binding'],
      residualRisk: 'Baixo'
    },
    {
      risk: 'Privilege escalation',
      likelihood: 'Média',
      impact: 'Crítico',
      mitigations: ['RBAC', 'Least privilege', 'Audit logging'],
      residualRisk: 'Baixo'
    },
    {
      risk: 'Data breach via auth bypass',
      likelihood: 'Baixa',
      impact: 'Crítico',
      mitigations: ['Secure design', 'Pen testing', 'Bug bounty'],
      residualRisk: 'Muito Baixo'
    }
  ],

  consultation: {
    dpo: 'Consultado em 2026-01-15',
    dataSubjects: 'Não necessário (representante legal)',
    authority: 'ANPD não consultada (risco residual baixo)'
  }
};
```

---

## 17.6 PCI DSS — Requisitos 8 e 10

### 17.6.1 PCI DSS Requisito 8 — Identificação e Autenticação

O PCI DSS (Payment Card Industry Data Security Standard) é obrigatório para qualquer sistema que processe dados de cartão de crédito. O Requisito 8 define controles específicos para identificação e autenticação:

```
// PCI DSS v4.0 — Requisito 8

// 8.1: Identificar usuários e autenticar acesso a sistemas e componentes
// 8.2: Autenticar acesso a sistemas e componentes
// 8.3: Autenticar acesso ao CDE (Cardholder Data Environment)
// 8.4: Autenticar acesso ao CDE via.Console físico/lógico
// 8.5: Não usar autenticação compartilhada
// 8.6: Sistema/serviços de autenticação
// 8.7: Contas de acesso não-interativo
// 8.8: Senhas do sistema/serviços

// Implementação PCI DSS:
class PCIDSSAuthControls {
  static getRequirements() {
    return {
      // 8.1: User identification
      userIdentification: {
        uniqueUserId: true,  // ID único por usuário
        noGenericAccounts: true,  // Sem contas genéricas
        noSharedAccounts: true,  // Sem contas compartilhadas
        auditTrail: true  // Trilha de auditoria por usuário
      },

      // 8.2: Authentication
      authentication: {
        strongPasswords: {
          minLength: 12,
          complexity: 'Mínimo 1 maiúscula, 1 minúscula, 1 número',
          maxAge: 90,  // dias
          history: 4  // Não reutilizar últimas 4 senhas
        },
        mfa: {
          required: true,  // Para todos os acessos ao CDE
          methods: ['TOTP', 'Hardware token', 'Smart card'],
          backupMethods: true  // Método backup obrigatório
        },
        lockout: {
          maxAttempts: 6,
          lockoutDuration: 30,  // minutos
          resetAfter: 30  // minutos
        }
      },

      // 8.3: MFA for CDE
      mfaForCDE: {
        required: true,
        methods: ['Fator múltiplo baseado em algo que sabe + algo que tem'],
        exceptions: 'Nenhuma exceção para acesso ao CDE'
      },

      // 8.4: Console access
      consoleAccess: {
        mfaRequired: true,
        sessionTimeout: 15,  // minutos
        autoLock: true
      },

      // 8.5: No shared authentication
      sharedAuth: {
        prohibited: true,
        genericAccounts: false,
        sharedCredentials: false
      },

      // 8.6: Service accounts
      serviceAccounts: {
        uniqueId: true,  // ID único por serviço
        passwordRotation: 90,  // dias
        mfa: 'Preferível mas não obrigatório',
        audit: true
      },

      // 8.7: Non-interactive accounts
      nonInteractiveAccounts: {
        uniqueId: true,
        passwordRotation: 90,
        mfa: 'Certificate-based preferred',
        audit: true
      },

      // 8.8: System/service passwords
      systemPasswords: {
        minLength: 12,
        complexity: 'Alfanumérico + especial',
        rotation: 90,  // dias
        secureStorage: 'Vault ou keystore'
      }
    };
  }
}
```

### 17.6.2 PCI DSS Requisito 10 — Rastreamento e Monitoramento

```
// PCI DSS v4.0 — Requisito 10

// 10.1: Processos e mecanismos de rastreamento e monitoramento
// 10.2: Logs de auditoria são implementados
// 10.3: Logs de auditoria incluem detalhes suficientes
// 10.4: Logs de auditoria são revisados em tempo oportuno
// 10.5: Logs de auditoria são protegidos
// 10.6: Logs históricos são preservados
// 10.7: Tempo de retenção de logs
// 10.8: Resposta a falhas de segurança dos controles críticos

// Implementação PCI DSS logging:
class PCIDSSAuditLogging {
  static getRequirements() {
    return {
      // 10.2: Audit logs
      auditLogs: {
        required: true,
        events: [
          'Todos os acessos ao CDE',
          'Ações de usuários com privilégios elevados',
          'Acesso a dados de cartão',
          'Acesso a sistemas de segurança',
          'Criação/modificação de contas',
          'Alterações em permissões',
          'Tentativas de login失败',
          'Bloqueio/desbloqueio de contas',
          'Alterações em configurações de segurança'
        ]
      },

      // 10.3: Log details
      logDetails: {
        userId: true,
        timestamp: true,
        ipAddress: true,
        userAgent: true,
        eventType: true,
        resource: true,
        action: true,
        result: true,
        previousValue: true,  // Para mudanças
        newValue: true  // Para mudanças
      },

      // 10.5: Log protection
      logProtection: {
        immutable: true,  // Logs não podem ser alterados/deletados
        centralized: true,  // SIEM centralizado
        encrypted: true,  // Logs em repouso encriptados
        accessControl: true,  // Acesso restrito a equipe de segurança
        integrityCheck: true  // Hash chain para detecção de adulteração
      },

      // 10.6: Log retention
      logRetention: {
        minimum: 12,  // meses
        recommended: 36,  // meses
        archive: true  // Backup para compliance
      },

      // 10.7: Retention period
      retentionPeriod: {
        online: 12,  // meses (acesso rápido)
        offline: 36,  // meses (archive)
        legalMinimum: 'Conforme legislação aplicável'
      }
    };
  }
}
```

---

## 17.7 HIPAA — Health Insurance Portability and Accountability Act

### 17.7.1 HIPAA Security Rule para autenticação

O HIPAA é obrigatório para sistemas que processam dados de saúde nos EUA. Embora seja legislação americana, muitas organizações brasileiras que operam internacionalmente devem cumprir HIPAA:

```
// HIPAA Security Rule — 45 CFR Part 164

// §164.312(d) — Person or Entity Authentication
// "Implement procedures to verify that a person or entity seeking
// access to electronic protected health information is the one claimed."

// §164.312(a)(1) — Access Control
// "Implement technical policies and procedures for electronic information
// systems that maintain electronic protected health information to allow
// access only to those persons or software programs that have been granted
// access rights."

// Implementação HIPAA:
class HIPAAAuthControls {
  static getRequirements() {
    return {
      // §164.312(d) — Authentication
      authentication: {
        uniqueUserId: true,
        strongPasswords: true,
        mfa: 'Recomendado para acesso remoto',
        sessionManagement: {
          timeout: 30,  // minutos
          reauthentication: true  // Para operações críticas
        }
      },

      // §164.312(a)(1) — Access Control
      accessControl: {
        roleBased: true,
        leastPrivilege: true,
        emergencyAccess: true,  // Conta de emergência documentada
        automaticLogoff: true,
        encryption: true  // Dados em repouso e em trânsito
      },

      // §164.312(b) — Audit Controls
      auditControls: {
        logAccess: true,
        logModifications: true,
        logDisclosures: true,
        regularReview: true,  // Revisão periódica de logs
        retention: 6  // anos mínimo
      },

      // §164.312(c)(1) — Integrity
      integrity: {
        dataIntegrity: true,  // Mecanismos para verificar integridade
        authentication: true,  // Autenticação de dados recebidos
        auditLogs: true  // Logs imutáveis
      },

      // §164.312(e)(1) — Transmission Security
      transmissionSecurity: {
        encryption: 'TLS 1.2+ obrigatório',
        integrityControls: true,  // Mecanismos de integridade em transmissão
        secureChannel: true  // Canal seguro para dados sensíveis
      }
    };
  }
}
```

---

## 17.8 SOC 2 — Service Organization Control

### 17.8.1 SOC 2 Trust Service Criteria para autenticação

SOC 2 é um framework de auditoria para organizações que fornecem serviços. Os Trust Service Criteria incluem requisitos específicos para autenticação:

```
// SOC 2 Trust Service Criteria — Security (Common Criteria)

// CC6.1: Logical and physical access controls
// "The entity implements logical access security software, infrastructure,
// and architectures over protected information assets to protect them
// from security events."

// CC6.2: Authentication
// "Prior to issuing system credentials and granting system access,
// the entity registers and authorizes new internal and external users
// whose access is administered by the entity."

// CC6.3: Authorization
// "The entity authorizes, modifies, or removes access to data, software,
// functions, and other protected information assets based on roles,
// responsibilities, or the system design and changes."

// CC6.6: System boundaries
// "The entity implements controls over credentials, keys, and other
// authentication mechanisms used to grant access to systems and data."

// CC6.7: Data transmission
// "The entity restricts the transmission, movement, and removal of
// information to authorized users and processes."

// Implementação SOC 2:
class SOC2AuthControls {
  static getRequirements() {
    return {
      // CC6.1: Access controls
      cc6_1: {
        accessControlPolicy: true,
        accessControlProcedures: true,
        periodicAccessReview: true,
        accessProvisioning: 'Approval required',
        accessDeprovisioning: 'Automated on termination'
      },

      // CC6.2: Authentication
      cc6_2: {
        newUserRegistration: 'Approval required',
        credentialManagement: {
          issuance: 'Secure process',
          modification: 'With approval',
          removal: 'Automated on termination'
        },
        passwordPolicy: 'NIST SP 800-63B compliant',
        mfa: 'Required for privileged access'
      },

      // CC6.3: Authorization
      cc6_3: {
        roleBasedAccess: true,
        leastPrivilege: true,
        segregationOfDuties: true,
        accessModification: 'With approval',
        accessRemoval: 'Automated on role change'
      },

      // CC6.6: Credential management
      cc6_6: {
        credentialStorage: 'Encrypted at rest',
        credentialRotation: 'Periodic',
        keyManagement: 'HSM or KMS',
        certificateManagement: 'Automated renewal'
      },

      // CC6.7: Data transmission
      cc6_7: {
        encryptionInTransit: 'TLS 1.2+',
        secureProtocols: 'HTTPS, SSH, SFTP',
        dataClassification: true,
        dataLabeling: true
      }
    };
  }
}
```

---

## 17.9 Automação de Compliance

### 17.9.1 Ferramentas de automação

A automação de compliance reduz erros humanos, acelera auditorias, e garante conformidade contínua:

```
# Ferramentas de automação de compliance para autenticação

# 1. Policy as Code (OPA/Rego)
package authz

default allow = false

# Regra: MFA obrigatório para admin
allow {
    input.user.mfa_enabled == true
    input.user.role == "admin"
    input.action == "access"
}

# Regra: Password policy compliance
allow {
    input.user.password_age_days < 90
    input.user.password_length >= 12
}

# 2. Infrastructure as Code (Terraform)
resource "aws_iam_policy" "auth_policy" {
  name = "auth-compliance-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminInitiateAuth",
          "cognito-idp:AdminRespondToAuthChallenge"
        ]
        Resource = aws_cognito_user_pool.auth_pool.arn
      }
    ]
  })
}

# 3. Security Scanning (OWASP ZAP)
# Automatizar testes de autenticação
# Verificar headers de segurança
# Testar rate limiting
# Verificar vulnerabilidades conhecidas
```

### 17.9.2 Pipeline de compliance contínuo

```
// Pipeline CI/CD com gates de compliance
class CompliancePipeline {
  constructor() {
    this.stages = [
      'static-analysis',
      'dependency-check',
      'sast',
      'auth-pattern-check',
      'policy-validation',
      'pen-test',
      'compliance-report'
    ];
  }

  async run() {
    for (const stage of this.stages) {
      const result = await this.executeStage(stage);
      if (!result.passed) {
        throw new ComplianceError(`Stage ${stage} failed`, result);
      }
    }
  }

  async executeStage(stage) {
    switch (stage) {
      case 'static-analysis':
        return await this.runStaticAnalysis();
      case 'dependency-check':
        return await this.checkDependencies();
      case 'sast':
        return await this.runSAST();
      case 'auth-pattern-check':
        return await this.checkAuthPatterns();
      case 'policy-validation':
        return await this.validatePolicies();
      case 'pen-test':
        return await this.runPenTest();
      case 'compliance-report':
        return await this.generateReport();
    }
  }

  async checkAuthPatterns() {
    // Verificar anti-patterns de autenticação
    const issues = [];

    // Verificar se senhas são hasheadas com Argon2id
    const hashPatterns = await this.scanForPatterns([
      'md5(', 'sha1(', 'sha256(', 'bcrypt('
    ]);

    if (hashPatterns.length > 0) {
      issues.push({
        severity: 'CRITICAL',
        message: 'Weak password hashing detected',
        files: hashPatterns
      });
    }

    // Verificar se JWT validation está presente
    const jwtValidation = await this.scanForPatterns([
      'jwt.verify(', 'jwt.decode('
    ]);

    if (jwtValidation.length === 0) {
      issues.push({
        severity: 'HIGH',
        message: 'JWT validation not found in codebase'
      });
    }

    // Verificar se rate limiting está configurado
    const rateLimiting = await this.scanForPatterns([
      'rateLimit', 'rate_limit', 'throttle'
    ]);

    if (rateLimiting.length === 0) {
      issues.push({
        severity: 'HIGH',
        message: 'Rate limiting not configured'
      });
    }

    return {
      passed: issues.filter(i => i.severity === 'CRITICAL').length === 0,
      issues
    };
  }
}
```

---

## 17.10 Checklist de Segurança — 50+ Itens

### 17.10.1 Checklist completo de autenticação e autorização

**CATEGORIA 1: Senhas e Credenciais (10 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 1 | Senhas armazenadas com Argon2id | Crítica | Verificar hash prefix `$argon2id$` |
| 2 | Sal único por usuário | Crítica | Verificar que sal é único em cada registro |
| 3 | Comprimento mínimo 12 caracteres | Alta | Testar com senhas < 12 caracteres |
| 4 | Verificação contra senhas comprometidas | Alta | Testar com senhas do HIBP |
| 5 | Sem senhas padrão em contas default | Crítica | Verificar todas as contas default |
| 6 | Senhas não em logs ou responses | Crítica | Grep por pattern de senha em logs |
| 7 | Rate limiting em login | Crítica | Testar com 100 tentativas |
| 8 | Account lockout após falhas | Alta | Verificar lockout após 5 tentativas |
| 9 | Mensagens de erro genéricas | Alta | Testar com email existente/inexistente |
| 10 | MFA para contas privilegiadas | Crítica | Verificar se admin tem MFA obrigatório |

**CATEGORIA 2: Sessões e Tokens (10 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 11 | JWT com expiração curta (15min) | Crítica | Verificar payload exp |
| 12 | Refresh token em cookie HttpOnly | Crítica | Verificar flags do cookie |
| 13 | Rotação de refresh token | Alta | Verificar se token antigo é invalidado |
| 14 | Invalidação no logout | Alta | Verificar se sessão é invalidada no servidor |
| 15 | Regeneração de sessão após login | Alta | Verificar se session ID muda |
| 16 | Timeout de inatividade (30min) | Alta | Verificar se sessão expira por inatividade |
| 17 | Timeout absoluto (24h) | Média | Verificar se sessão tem limite absoluto |
| 18 | Token blacklist para logout | Alta | Verificar se token é invalidado |
| 19 | Sem tokens no localStorage | Crítica | Grep por `localStorage.*token` |
| 20 | Tokens não em URLs | Alta | Verificar se tokens aparecem em query params |

**CATEGORIA 3: Autorização (10 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 21 | Deny-by-default em todas as políticas | Crítica | Verificar política padrão |
| 22 | Least privilege para roles | Crítica | Auditar permissões por role |
| 23 | Verificação server-side em cada endpoint | Crítica | Testar com token inválido |
| 24 | Sem autorização client-side | Crítica | Grep por `localStorage.*role` |
| 25 | Separation of Duty para operações críticas | Alta | Verificar se transferências requerem 2 aprovações |
| 26 | RBAC implementado corretamente | Alta | Mapear roles e permissões |
| 27 | Sem contas genéricas | Crítica | Verificar contas default |
| 28 | Auditoria de decisões de autorização | Alta | Verificar logs de acesso |
| 29 | Proteção contra IDOR | Crítica | Testar com IDs de outros usuários |
| 30 | CORS configurado corretamente | Alta | Verificar origens permitidas |

**CATEGORIA 4: API Security (10 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 31 | HTTPS obrigatório (HSTS) | Crítica | Verificar header HSTS |
| 32 | Autenticação em cada request | Crítica | Testar sem token |
| 33 | Rate limiting por endpoint | Alta | Testar endpoints sensíveis |
| 34 | Validação de JWT com algoritmo fixo | Crítica | Verificar `algorithms: ['RS256']` |
| 35 | JWKS rotation suportado | Alta | Verificar rotação de chaves |
| 36 | Scopes mínimo necessário | Alta | Auditar scopes por role |
| 37 | Input validation em todos os endpoints | Crítica | Testar com inputs maliciosos |
| 38 | Error responses sem info sensível | Alta | Verificar stack traces em produção |
| 39 | API versioning implementada | Média | Verificar versionamento |
| 40 | Deprecation policy documentada | Média | Verificar documentação |

**CATEGORIA 5: Infraestrutura e Monitoring (10 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 41 | Secrets em vault (não hardcoded) | Crítica | Grep por secrets no código |
| 42 | Environment segregation | Alta | Verificar variáveis por ambiente |
| 43 | Monitoring e alerting configurados | Alta | Verificar alertas para eventos críticos |
| 44 | Incident response plan documentado | Alta | Verificar documentação |
| 45 | Penetration testing anual | Alta | Verificar relatório de pen test |
| 46 | Vulnerability scanning mensal | Alta | Verificar relatório de scan |
| 47 | Backup e recovery testados | Alta | Verificar testes de restore |
| 48 | Disaster recovery plan | Média | Verificar documentação |
| 49 | Security training para equipe | Média | Verificar treinamentos |
| 50 | Third-party dependency audit | Alta | Verificar dependências vulneráveis |

**CATEGORIA 6: Compliance e Governance (5 itens)**

| # | Item | Severidade | Verificação |
|---|------|------------|-------------|
| 51 | Privacy policy atualizada | Alta | Verificar política no site |
| 52 | Data retention policy definida | Alta | Verificar política |
| 53 | DPO nomeado (se aplicável LGPD) | Alta | Verificar nomeação |
| 54 | DPIA realizado para dados sensíveis | Alta | Verificar relatório |
| 55 | Terms of service atualizados | Média | Verificar TOS |

---

## 17.11 Árvores de Decisão

### 17.11.1 Árvore de decisão: Qual framework de compliance?

```
O sistema processa dados de cartão de crédito?
├── SIM → PCI DSS obrigatório
│   ├── Dados armazenados? → Requisitos 3, 4, 8, 10
│   └── Dados transmitidos? → Requisitos 3, 4
└── NÃO
    ├── O sistema processa dados de saúde (EUA)?
    │   ├── SIM → HIPAA obrigatório
    │   └── NÃO
    │       ├── O sistema processa dados de cidadãos europeus?
    │       │   ├── SIM → GDPR obrigatório
    │       │   └── NÃO
    │       │       ├── O sistema é brasileiro?
    │       │       │   ├── SIM → LGPD obrigatório
    │       │       │   └── NÃO → Verificar legislação local
    │       │       └── É um serviço B2B?
    │       │           ├── SIM → SOC 2 recomendado
    │       │           └── NÃO → OWASP ASVS recomendado
    │       └── Qualquer sistema → OWASP ASVS recomendado
    └── Qualquer sistema → OWASP Top 10 como baseline
```

### 17.11.2 Árvore de decisão: Qual nível de autenticação?

```
Quais dados o sistema processa?
├── Dados públicos
│   ├── Autenticação básica (AAL1)
│   ├── Senha + rate limiting
│   └── MFA opcional
├── Dados pessoais (LGPD/GDPR)
│   ├── Autenticação padrão (AAL2)
│   ├── Senha forte + MFA
│   ├── Rate limiting + lockout
│   └── Audit logging
├── Dados financeiros (PCI DSS)
│   ├── Autenticação robusta (AAL2/AAL3)
│   ├── MFA obrigatório
│   ├── Hardware tokens preferidos
│   └── Audit logging completo
├── Dados de saúde (HIPAA)
│   ├── Autenticação robusta (AAL2)
│   ├── MFA para acesso remoto
│   ├── Session management rigoroso
│   └── Audit logging com retenção 6 anos
└── Dados governamentais (como IDAP)
    ├── Autenticação máxima (AAL3)
    ├── MFA obrigatório para todos
    ├── Hardware tokens para operadores
    ├── Audit logging imutável
    ├── Incident response plan
    └── Pen testing trimestral
```

### 17.11.3 Árvore de decisão: Como responder a um incidente?

```
Um incidente de autenticação foi detectado
│
├── 1. CONTENÇÃO (primeiras 24h)
│   ├── Conta comprometida? → Congelar conta, invalidar sessões
│   ├── Credenciais vazadas? → Forçar reset de senha para todos afetados
│   ├── Ataque em andamento? → Block IP, escalar para SOC
│   └── Dados expostos? → Iniciar investigação forense
│
├── 2. NOTIFICAÇÃO (24-72h)
│   ├── Dados pessoais brasileiros? → ANPD em "prazo razoável" (2 dias úteis)
│   ├── Dados de cidadãos europeus? → Autoridade competente em 72h (GDPR Art. 33)
│   ├── Dados de cartão? → Brand (Visa/Mastercard) + acquirer
│   ├── Dados de saúde? → HHS em 60 dias (HIPAA)
│   └── Usuários afetados? → Notificar em "prazo razoável"
│
├── 3. INVESTIGAÇÃO (1-30 dias)
│   ├── Logs de auditoria → Verificar integridade
│   ├── Scope do ataque → Determinar dados comprometidos
│   ├── Vetor de ataque → Identificar vulnerabilidade
│   └── Impacto → Avaliar dano aos usuários
│
├── 4. REMEDIAÇÃO (30-90 dias)
│   ├── Corrigir vulnerabilidade → Patch ou mudança de configuração
│   ├── Fortalecer controles → Implementar padrões deste livro
│   ├── Atualizar políticas → Revisar e atualizar
│   └── Treinar equipe → Awareness training
│
└── 5. PREVENÇÃO (contínuo)
    ├── Monitoramento → Alertas para comportamento anômalo
    ├── Testes → Pen testing regular
    ├── Compliance → Auditorias periódicas
    └── Melhoria contínua → Lessons learned
```

---

## 17.12 Referência Rápida

### 17.12.1 Tabela de compliance por tipo de dados

| Tipo de Dados | Framework | Autenticação | MFA | Logging | Retenção |
|---------------|-----------|--------------|-----|---------|----------|
| Públicos | OWASP ASVS L1 | Senha | Opcional | Básico | 30 dias |
| Pessoais (BR) | LGPD | Senha forte | Recomendado | Completo | 5 anos |
| Pessoais (EU) | GDPR | Senha forte | Recomendado | Completo | 30 meses |
| Cartão de crédito | PCI DSS | Senha forte | Obrigatório | Completo | 12 meses |
| Saúde (EUA) | HIPAA | Senha forte | Recomendado | Completo | 6 anos |
| Saúde (BR) | LGPD + ANS | Senha forte | Obrigatório | Completo | 20 anos |
| Governamental | OWASP ASVS L3 | MFA obrigatório | Obrigatório | Imutável | 5+ anos |
| Financeiro | PCI DSS + BACEN | MFA obrigatório | Obrigatório | Imutável | 5+ anos |

### 17.12.2 Mapeamento de controles por framework

| Controle | OWASP ASVS | NIST 800-63 | LGPD | GDPR | PCI DSS | HIPAA | SOC 2 |
|----------|------------|-------------|------|------|---------|-------|-------|
| Password hashing | V2.1.1 | SP 800-63B | Art. 46 | Art. 32 | Req 8 | §164.312 | CC6.1 |
| MFA | V2.3 | AAL2+ | Art. 46 | Art. 32 | Req 8.3 | §164.312 | CC6.2 |
| Rate limiting | V2.2.2 | SP 800-63B | Art. 46 | Art. 32 | Req 8 | §164.312 | CC6.1 |
| Audit logging | V7.1 | SP 800-63B | Art. 37 | Art. 30 | Req 10 | §164.312 | CC7.2 |
| Encryption | V6.1 | SP 800-57 | Art. 46 | Art. 32 | Req 3,4 | §164.312 | CC6.7 |
| Session management | V3.1 | SP 800-63B | Art. 46 | Art. 32 | Req 8 | §164.312 | CC6.1 |
| Access control | V4.1 | SP 800-53 | Art. 46 | Art. 25 | Req 7 | §164.312 | CC6.3 |
| Incident response | V15.1 | SP 800-61 | Art. 48 | Art. 33 | Req 12 | §164.308 | CC7.3 |

### 17.12.3 Quick reference: O que implementar primeiro

**Se você tem 1 dia:**
- Senhas com Argon2id
- Rate limiting em login
- Mensagens de erro genéricas
- HTTPS com HSTS

**Se você tem 1 semana:**
- Tudo do dia 1
- MFA para contas admin
- JWT com expiração curta
- Audit logging básico
- Secure cookies

**Se você tem 1 mês:**
- Tudo da semana
- RBAC implementado
- Password reset seguro
- Session management completo
- Monitoring e alerting

**Se você tem 3 meses:**
- Tudo do mês
- WebAuthn/FIDO2
- Policy engine (OPA/Cedar)
- Compliance automation
- Penetration testing
- Incident response plan

**Se você tem 6 meses:**
- Tudo de 3 meses
- SOC 2 readiness
- DPIA para dados sensíveis
- Security training para equipe
- Bug bounty program
- Continuous compliance monitoring

---

## 17.13 Métricas e KPIs de Segurança de Autenticação

### 17.13.1 Métricas operacionais

Métricas são essenciais para medir a eficácia dos controles de autenticação e autorização. Sem métricas, não há como saber se os controles estão funcionando:

```
class AuthSecurityMetrics {
  constructor(db, redis) {
    this.db = db;
    this.redis = redis;
  }

  // Métrica 1: Taxa de falha de login
  async getLoginFailureRate(period = '24h') {
    const result = await this.db.query(`
      SELECT
        COUNT(CASE WHEN result = 'failure' THEN 1 END) as failures,
        COUNT(CASE WHEN result = 'success' THEN 1 END) as successes,
        COUNT(*) as total
      FROM audit_logs
      WHERE event_type IN ('auth.login.success', 'auth.login.failed')
        AND timestamp > NOW() - INTERVAL '${period}'
    `);

    const { failures, total } = result.rows[0];
    return {
      failures: parseInt(failures),
      total: parseInt(total),
      rate: total > 0 ? (failures / total * 100).toFixed(2) : 0,
      alertThreshold: 30,  // Alertar se > 30% de falhas
      status: (failures / total * 100) > 30 ? 'WARNING' : 'OK'
    };
  }

  // Métrica 2: Taxa de adoção de MFA
  async getMFAAdoptionRate() {
    const result = await this.db.query(`
      SELECT
        COUNT(CASE WHEN mfa_enabled = true THEN 1 END) as with_mfa,
        COUNT(*) as total
      FROM users
      WHERE status = 'active'
    `);

    const { with_mfa, total } = result.rows[0];
    return {
      withMFA: parseInt(with_mfa),
      total: parseInt(total),
      rate: (with_mfa / total * 100).toFixed(2),
      targetRate: 100,  // Meta: 100% para contas privilegiadas
      privilegedUsers: await this.getPrivilegedUsersMFA(),
      status: parseInt(with_mfa) / parseInt(total) < 0.8 ? 'WARNING' : 'OK'
    };
  }

  // Métrica 3: Tempo médio de resposta a incidentes
  async getIncidentResponseTime() {
    const result = await this.db.query(`
      SELECT
        AVG(EXTRACT(EPOCH FROM (resolved_at - detected_at))) as avg_resolution_time,
        MIN(EXTRACT(EPOCH FROM (resolved_at - detected_at))) as fastest,
        MAX(EXTRACT(EPOCH FROM (resolved_at - detected_at))) as slowest,
        COUNT(*) as incidents
      FROM security_incidents
      WHERE detected_at > NOW() - INTERVAL '30 days'
        AND resolved_at IS NOT NULL
    `);

    return {
      avgResolutionTime: result.rows[0].avg_resolution_time,
      fastest: result.rows[0].fastest,
      slowest: result.rows[0].slowest,
      incidents: parseInt(result.rows[0].incidents),
      slaTarget: 3600,  // 1 hora
      status: result.rows[0].avg_resolution_time > 3600 ? 'WARNING' : 'OK'
    };
  }

  // Métrica 4: Contas bloqueadas
  async getLockedAccountsCount() {
    const result = await this.db.query(`
      SELECT COUNT(*) as locked
      FROM users
      WHERE locked_until > NOW()
    `);

    const locked = parseInt(result.rows[0].locked);
    return {
      lockedAccounts: locked,
      alertThreshold: 50,
      status: locked > 50 ? 'WARNING' : 'OK'
    };
  }

  // Métrica 5: Tokens expirados vs ativados
  async getTokenHealth() {
    const result = await this.db.query(`
      SELECT
        COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired,
        COUNT(CASE WHEN expires_at >= NOW() THEN 1 END) as active,
        COUNT(*) as total
      FROM refresh_tokens
      WHERE created_at > NOW() - INTERVAL '30 days'
    `);

    return {
      expired: parseInt(result.rows[0].expired),
      active: parseInt(result.rows[0].active),
      total: parseInt(result.rows[0].total),
      expirationRate: (result.rows[0].expired / result.rows[0].total * 100).toFixed(2)
    };
  }

  // Dashboard completo
  async getSecurityDashboard() {
    const [
      loginFailureRate,
      mfaAdoption,
      incidentResponse,
      lockedAccounts,
      tokenHealth
    ] = await Promise.all([
      this.getLoginFailureRate(),
      this.getMFAAdoptionRate(),
      this.getIncidentResponseTime(),
      this.getLockedAccountsCount(),
      this.getTokenHealth()
    ]);

    return {
      timestamp: new Date().toISOString(),
      metrics: {
        loginFailureRate,
        mfaAdoption,
        incidentResponse,
        lockedAccounts,
        tokenHealth
      },
      overallStatus: this.calculateOverallStatus([
        loginFailureRate.status,
        mfaAdoption.status,
        incidentResponse.status,
        lockedAccounts.status
      ])
    };
  }

  calculateOverallStatus(statuses) {
    if (statuses.includes('CRITICAL')) return 'CRITICAL';
    if (statuses.includes('WARNING')) return 'WARNING';
    return 'OK';
  }
}
```

### 17.13.2 KPIs para relatórios de compliance

```
// KPIs para relatórios de compliance (mensal/trimestral)
class ComplianceKPIs {
  static getMonthlyReport() {
    return {
      // KPIs de autenticação
      authentication: {
        totalLogins: 'COUNT de logins bem-sucedidos',
        failedLogins: 'COUNT de tentativas失败',
        mfaEnabled: 'Percentual de contas com MFA',
        mfaBypassAttempts: 'Tentativas de bypass de MFA',
        passwordResets: 'COUNT de resets de senha',
        averagePasswordAge: 'Idade média das senhas (dias)',
        compromisedPasswords: 'Senhas encontradas em breaches'
      },

      // KPIs de autorização
      authorization: {
        accessDenied: 'COUNT de acessos negados',
        privilegeEscalation: 'Tentativas de escalonamento',
        idorAttempts: 'Tentativas de IDOR detectadas',
        roleChanges: 'Mudanças de role realizadas',
        permissionAudits: 'Auditorias de permissão realizadas'
      },

      // KPIs de sessão
      sessions: {
        activeSessions: 'Sessões ativas',
        expiredSessions: 'Sessões expiradas',
        averageSessionDuration: 'Duração média da sessão',
        concurrentSessions: 'Pico de sessões simultâneas',
        sessionHijackingAttempts: 'Tentativas de hijacking'
      },

      // KPIs de incidente
      incidents: {
        totalIncidents: 'Total de incidentes',
        authIncidents: 'Incidentes de autenticação',
        averageResponseTime: 'Tempo médio de resposta',
        averageResolutionTime: 'Tempo médio de resolução',
        falsePositives: 'Falsos positivos de alertas'
      },

      // KPIs de compliance
      compliance: {
        asvsScore: 'Pontuação OWASP ASVS',
        pciDSSCompliance: 'Conformidade PCI DSS',
        lgpdCompliance: 'Conformidade LGPD',
        auditLogIntegrity: 'Integridade dos logs',
        policyViolations: 'Violações de política'
      }
    };
  }
}
```

---

## 17.14 Treinamento e Conscientização de Segurança

### 17.14.1 Programa de treinamento obrigatório

Treinamento de segurança não é opcional — é requisito de compliance para frameworks como PCI DSS (Req 12.6), HIPAA (§164.308(a)(5)), e SOC 2 (CC1.4):

```
class SecurityTrainingProgram {
  constructor() {
    this.modules = [
      {
        id: 'auth-fundamentals',
        title: 'Fundamentos de Autenticação e Autorização',
        duration: '2 horas',
        frequency: 'Anual',
        audience: 'Todos os funcionários',
        topics: [
          'O que é autenticação vs autorização',
          'Por que senhas fracas são perigosas',
          'Como MFA protege contas',
          'Reconhecimento de phishing',
          'Política de senhas da organização'
        ],
        assessment: {
          passingScore: 80,
          maxAttempts: 3,
          retakeFrequency: 'Anual'
        }
      },
      {
        id: 'secure-coding',
        title: 'Codificação Segura para Autenticação',
        duration: '4 horas',
        frequency: 'Anual',
        audience: 'Desenvolvedores',
        topics: [
          'Anti-patterns de autenticação',
          'Implementação segura de JWT',
          'Rate limiting e brute force protection',
          'Secure session management',
          'OWASP Top 10 aplicado a auth'
        ],
        assessment: {
          passingScore: 85,
          maxAttempts: 2,
          retakeFrequency: 'Anual'
        }
      },
      {
        id: 'incident-response',
        title: 'Resposta a Incidentes de Segurança',
        duration: '3 horas',
        frequency: 'Semestral',
        audience: 'Equipe de segurança + TI',
        topics: [
          'Identificação de incidentes',
          'Classificação de severidade',
          'Procedimentos de contenção',
          'Comunicação interna e externa',
          'Investigação forense básica',
          'Lições aprendidas'
        ],
        assessment: {
          type: 'simulation',
          passingScore: 'Participation',
          frequency: 'Trimestral (drills)'
        }
      },
      {
        id: 'compliance-awareness',
        title: 'Conscientização de Compliance',
        duration: '1 hora',
        frequency: 'Anual',
        audience: 'Todos os funcionários',
        topics: [
          'LGPD e proteção de dados',
          'Política de uso aceitável',
          'Proteção de credenciais',
          'Reporte de incidentes',
          'Consequências de violações'
        ],
        assessment: {
          passingScore: 80,
          maxAttempts: 3,
          retakeFrequency: 'Anual'
        }
      }
    ];
  }

  async trackCompletion(userId, moduleId) {
    const module = this.modules.find(m => m.id === moduleId);
    if (!module) {
      throw new Error(`Module ${moduleId} not found`);
    }

    await db.query(`
      INSERT INTO training_completions (user_id, module_id, completed_at, score, status)
      VALUES ($1, $2, NOW(), $3, 'completed')
      ON CONFLICT (user_id, module_id, year(completed_at))
      DO UPDATE SET
        completed_at = NOW(),
        score = $3,
        status = 'completed'
    `, [userId, moduleId, score]);

    // Verificar se treinamento é obrigatório para o role do usuário
    const user = await db.findUserById(userId);
    if (module.audience.includes(user.role)) {
      // Notificar se não completou
      const overdue = await this.checkOverdue(userId, moduleId);
      if (overdue) {
        await this.sendReminder(userId, moduleId);
      }
    }
  }

  async getComplianceStatus() {
    const status = {};

    for (const module of this.modules) {
      const completions = await db.query(`
        SELECT
          COUNT(DISTINCT user_id) as completed,
          (SELECT COUNT(*) FROM users WHERE status = 'active') as total
        FROM training_completions
        WHERE module_id = $1
          AND completed_at > NOW() - INTERVAL '${module.frequency}'
          AND score >= $2
      `, [module.id, module.assessment.passingScore]);

      const { completed, total } = completions.rows[0];
      status[module.id] = {
        title: module.title,
        completed: parseInt(completed),
        total: parseInt(total),
        rate: (completed / total * 100).toFixed(2),
        status: completed / total >= 0.95 ? 'COMPLIANT' : 'NON_COMPLIANT'
      };
    }

    return status;
  }
}
```

### 17.14.2 Simulações e exercícios

```
// Exercícios práticos de segurança
class SecurityExercises {
  static getExercises() {
    return [
      {
        id: 'phishing-simulation',
        title: 'Simulação de Phishing',
        frequency: 'Mensal',
        description: 'Enviar emails de phishing simulados para todos os funcionários',
        successCriteria: 'Menos de 5% de cliques no link',
        remediation: 'Treinamento adicional para funcionários que clicaram'
      },
      {
        id: 'credential-stuffing-test',
        title: 'Teste de Credential Stuffing',
        frequency: 'Trimestral',
        description: 'Simular ataque de credential stuffing contra o sistema de login',
        successCriteria: 'Rate limiting bloqueia após 5 tentativas',
        remediation: 'Ajustar configurações de rate limiting'
      },
      {
        id: 'privilege-escalation-test',
        title: 'Teste de Escalonamento de Privilégios',
        frequency: 'Semestral',
        description: 'Tentar acessar recursos com credenciais de nível inferior',
        successCriteria: 'Acesso negado em 100% das tentativas',
        remediation: 'Revisar e corrigir políticas de autorização'
      },
      {
        id: 'session-hijack-simulation',
        title: 'Simulação de Session Hijacking',
        frequency: 'Semestral',
        description: 'Simular roubo de sessão via XSS ou MITM',
        successCriteria: 'Cookies protegidos, tokens invalidados',
        remediation: 'Melhorar flags de cookies e validação de tokens'
      },
      {
        id: 'password-spraying-test',
        title: 'Teste de Password Spraying',
        frequency: 'Trimestral',
        description: 'Testar senhas comuns contra múltiplas contas',
        successCriteria: 'Lockout e detecção funcionam',
        remediation: 'Ajustar thresholds de lockout'
      }
    ];
  }
}
```

---

## 17.15 Gestão de Vulnerabilidades em Autenticação

### 17.15.1 Processo de gestão de vulnerabilidades

A gestão de vulnerabilidades é um processo contínuo que inclui identificação, classificação, remediação, e verificação:

```
class VulnerabilityManagement {
  constructor() {
    this.severityLevels = {
      CRITICAL: {
        cvssMin: 9.0,
        remediationTime: 24,  // horas
        escalation: 'CISO',
        notification: 'Board'
      },
      HIGH: {
        cvssMin: 7.0,
        remediationTime: 72,
        escalation: 'Security Team Lead',
        notification: 'CISO'
      },
      MEDIUM: {
        cvssMin: 4.0,
        remediationTime: 30,  // dias
        escalation: 'Development Lead',
        notification: 'Security Team'
      },
      LOW: {
        cvssMin: 0.1,
        remediationTime: 90,
        escalation: 'Development Team',
        notification: 'Development Lead'
      }
    };
  }

  async processVulnerability(vuln) {
    // 1. Classificar
    const severity = this.classifySeverity(vuln.cvssScore);

    // 2. Notificar
    await this.notify(vuln, severity);

    // 3. Criar ticket de remediação
    const ticket = await this.createRemediationTicket(vuln, severity);

    // 4. Acompanhar progresso
    await this.trackProgress(ticket);

    // 5. Verificar remediação
    await this.verifyRemediation(ticket);

    return { ticket, severity };
  }

  classifySeverity(cvssScore) {
    for (const [level, config] of Object.entries(this.severityLevels)) {
      if (cvssScore >= config.cvssMin) {
        return { level, ...config };
      }
    }
    return { level: 'INFO', cvssMin: 0, remediationTime: null };
  }

  async getVulnerabilityReport() {
    const result = await db.query(`
      SELECT
        severity,
        COUNT(*) as count,
        AVG(EXTRACT(EPOCH FROM (resolved_at - reported_at))/86400) as avg_resolution_days,
        COUNT(CASE WHEN resolved_at IS NULL THEN 1 END) as open
      FROM vulnerabilities
      WHERE reported_at > NOW() - INTERVAL '90 days'
      GROUP BY severity
      ORDER BY CASE severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
      END
    `);

    return result.rows;
  }
}
```

### 17.15.2 Scan de vulnerabilidades autenticado

```
// Scanners de vulnerabilidade para autenticação
class AuthVulnerabilityScanner {
  async scanTarget(target) {
    const findings = [];

    // 1. Verificar headers de segurança
    const headers = await this.checkSecurityHeaders(target);
    findings.push(...headers);

    // 2. Verificar política de senhas
    const passwordPolicy = await this.checkPasswordPolicy(target);
    findings.push(...passwordPolicy);

    // 3. Verificar rate limiting
    const rateLimiting = await this.checkRateLimiting(target);
    findings.push(...rateLimiting);

    // 4. Verificar sessões
    const sessions = await this.checkSessionSecurity(target);
    findings.push(...sessions);

    // 5. Verificar tokens
    const tokens = await this.checkTokenSecurity(target);
    findings.push(...tokens);

    // 6. Verificar CORS
    const cors = await this.checkCORSSecurity(target);
    findings.push(...cors);

    return findings;
  }

  async checkSecurityHeaders(target) {
    const response = await fetch(target);
    const headers = response.headers;
    const findings = [];

    if (!headers.get('strict-transport-security')) {
      findings.push({
        severity: 'HIGH',
        title: 'HSTS header missing',
        description: 'O header Strict-Transport-Security não está configurado',
        remediation: 'Adicionar header HSTS com max-age >= 31536000',
        compliance: ['OWASP ASVS V14.4.3', 'PCI DSS Req 6.5']
      });
    }

    if (!headers.get('x-content-type-options')) {
      findings.push({
        severity: 'MEDIUM',
        title: 'X-Content-Type-Options header missing',
        description: 'O header X-Content-Type-Options não está configurado',
        remediation: 'Adicionar header X-Content-Type-Options: nosniff'
      });
    }

    if (headers.get('x-frame-options') !== 'DENY') {
      findings.push({
        severity: 'MEDIUM',
        title: 'X-Frame-Options not set to DENY',
        description: 'O header X-Frame-Options não está configurado como DENY',
        remediation: 'Adicionar header X-Frame-Options: DENY'
      });
    }

    return findings;
  }

  async checkRateLimiting(target) {
    const findings = [];
    const loginEndpoint = `${target}/auth/login`;

    // Testar com 20 tentativas rápidas
    let blocked = false;
    for (let i = 0; i < 20; i++) {
      const response = await fetch(loginEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@test.com', password: 'wrong' })
      });

      if (response.status === 429) {
        blocked = true;
        break;
      }
    }

    if (!blocked) {
      findings.push({
        severity: 'CRITICAL',
        title: 'No rate limiting on login endpoint',
        description: 'O endpoint de login não possui rate limiting',
        remediation: 'Implementar rate limiting com máximo de 5 tentativas por 15 minutos',
        compliance: ['OWASP ASVS V2.2.2', 'NIST SP 800-63B']
      });
    }

    return findings;
  }
}
```

---

## 17.16 Gestão de Riscos de Terceiros

### 17.16.1 Avaliação de segurança de fornecedores

Quando um sistema depende de serviços de terceiros (Auth0, Keycloak, AWS Cognito), a segurança desses serviços impacta diretamente o sistema:

```
class ThirdPartySecurityAssessment {
  async assessProvider(provider) {
    const assessment = {
      provider: provider.name,
      assessmentDate: new Date().toISOString(),
      criteria: []
    };

    // 1. Certificações de segurança
    assessment.criteria.push({
      category: 'Certifications',
      items: [
        { name: 'SOC 2 Type II', required: true, status: provider.soc2 },
        { name: 'ISO 27001', required: true, status: provider.iso27001 },
        { name: 'PCI DSS', required: provider.processesPayments, status: provider.pciDss },
        { name: 'HIPAA BAA', required: provider.processesHealthData, status: provider.hipaaBaa }
      ]
    });

    // 2. Controles de autenticação
    assessment.criteria.push({
      category: 'Authentication Controls',
      items: [
        { name: 'MFA support', required: true, status: provider.mfaSupport },
        { name: 'Password policy', required: true, status: provider.passwordPolicy },
        { name: 'Rate limiting', required: true, status: provider.rateLimiting },
        { name: 'Account lockout', required: true, status: provider.accountLockout },
        { name: 'Session management', required: true, status: provider.sessionManagement }
      ]
    });

    // 3. Controles de autorização
    assessment.criteria.push({
      category: 'Authorization Controls',
      items: [
        { name: 'RBAC', required: true, status: provider.rbac },
        { name: 'ABAC', required: false, status: provider.abac },
        { name: 'Custom policies', required: true, status: provider.customPolicies },
        { name: 'Audit logging', required: true, status: provider.auditLogging }
      ]
    });

    // 4. Criptografia
    assessment.criteria.push({
      category: 'Cryptography',
      items: [
        { name: 'TLS 1.2+ mandatory', required: true, status: provider.tlsMinimum },
        { name: 'Data encryption at rest', required: true, status: provider.encryptionAtRest },
        { name: 'Key management', required: true, status: provider.keyManagement },
        { name: 'Password hashing (Argon2/bcrypt)', required: true, status: provider.passwordHashing }
      ]
    });

    // 5. Compliance
    assessment.criteria.push({
      category: 'Compliance',
      items: [
        { name: 'LGPD compliance', required: true, status: provider.lgpd },
        { name: 'GDPR compliance', required: provider.servesEU, status: provider.gdpr },
        { name: 'Data processing agreement', required: true, status: provider.dpa },
        { name: 'Incident notification', required: true, status: provider.incidentNotification }
      ]
    });

    // Calcular score
    let totalItems = 0;
    let passedItems = 0;
    let criticalFailures = [];

    for (const category of assessment.criteria) {
      for (const item of category.items) {
        totalItems++;
        if (item.status) {
          passedItems++;
        } else if (item.required) {
          criticalFailures.push(item);
        }
      }
    }

    assessment.score = (passedItems / totalItems * 100).toFixed(2);
    assessment.criticalFailures = criticalFailures;
    assessment.approved = criticalFailures.length === 0;

    return assessment;
  }
}
```

---

## 17.17 Classificação e Tratamento de Dados

### 17.17.1 Matriz de classificação de dados

A classificação de dados determina quais controles de autenticação e autorização são necessários:

```
class DataClassification {
  static getClassifications() {
    return {
      PUBLIC: {
        description: 'Dados públicos, sem restrições de acesso',
        examples: ['Website content', 'Public APIs', 'Marketing materials'],
        authRequirements: {
          authentication: 'Opcional (para funcionalidades específicas)',
          mfa: 'Não obrigatório',
          sessionTimeout: 'Não aplicável',
          encryption: 'TLS para transmissão'
        },
        authzRequirements: {
          model: 'Nenhum (acesso livre)',
          audit: 'Básico (logs de acesso)'
        }
      },

      INTERNAL: {
        description: 'Dados para uso interno da organização',
        examples: ['Internal documentation', 'Employee directory', 'Internal tools'],
        authRequirements: {
          authentication: 'Obrigatória (senha + SSO)',
          mfa: 'Recomendado',
          sessionTimeout: '60 minutos',
          encryption: 'TLS + hash de senhas'
        },
        authzRequirements: {
          model: 'RBAC básico',
          audit: 'Logs de acesso por usuário'
        }
      },

      CONFIDENTIAL: {
        description: 'Dados sensíveis que requerem proteção',
        examples: ['Customer PII', 'Financial records', 'Health data', 'Authentication credentials'],
        authRequirements: {
          authentication: 'Obrigatória (senha forte + MFA)',
          mfa: 'Obrigatório',
          sessionTimeout: '30 minutos',
          encryption: 'TLS 1.2+ + AES-256 at rest + Argon2id'
        },
        authzRequirements: {
          model: 'RBAC + ABAC',
          leastPrivilege: true,
          audit: 'Logs completos com integridade'
        }
      },

      RESTRICTED: {
        description: 'Dados de alto impacto, acesso extremamente restrito',
        examples: ['Payment card data', 'Government IDs', 'Health records (HIPAA)', 'Authentication secrets'],
        authRequirements: {
          authentication: 'Obrigatória (MFA com hardware token)',
          mfa: 'Obrigatório (hardware token preferido)',
          sessionTimeout: '15 minutos',
          encryption: 'TLS 1.3 + AES-256-GCM + HSM para chaves',
          specialControls: [
            'Separation of Duty',
            'IP whitelisting',
            'Time-based access restrictions',
            'Real-time monitoring'
          ]
        },
        authzRequirements: {
          model: 'ABAC + Policy Engine',
          leastPrivilege: true,
          segregationOfDuties: true,
          audit: 'Logs imutáveis com chain de hash',
          realTimeAlerting: true
        }
      }
    };
  }

  static getControlsForClassification(classification) {
    const classes = this.getClassifications();
    const classConfig = classes[classification];

    if (!classConfig) {
      throw new Error(`Unknown classification: ${classification}`);
    }

    return {
      authentication: classConfig.authRequirements,
      authorization: classConfig.authzRequirements,
      controls: this.getTechnicalControls(classification)
    };
  }

  static getTechnicalControls(classification) {
    const controls = {
      PUBLIC: ['HTTPS'],
      INTERNAL: ['HTTPS', 'SSO', 'Basic RBAC', 'Audit logs'],
      CONFIDENTIAL: ['HTTPS', 'MFA', 'RBAC', 'ABAC', 'Encryption at rest', 'Audit logs', 'Session management'],
      RESTRICTED: ['HTTPS', 'Hardware MFA', 'ABAC', 'Policy Engine', 'HSM', 'Immutable audit logs', 'Real-time monitoring', 'IP whitelisting', 'Separation of Duty']
    };

    return controls[classification] || controls.INTERNAL;
  }
}
```

### 17.17.2 Data masking para logs

Logs de auditoria devem registrar ações, mas não devem expor dados sensíveis:

```
class DataMasker {
  static maskSensitiveData(data, context = {}) {
    const masked = { ...data };

    // PII fields
    const piiFields = ['email', 'phone', 'cpf', 'cnpj', 'rg', 'passport'];
    for (const field of piiFields) {
      if (masked[field]) {
        masked[field] = this.maskPII(masked[field], field);
      }
    }

    // Authentication fields
    const authFields = ['password', 'token', 'secret', 'mfa_code', 'backup_code'];
    for (const field of authFields) {
      if (masked[field]) {
        masked[field] = '[REDACTED]';
      }
    }

    // Financial fields
    const financialFields = ['credit_card', 'bank_account', 'pix_key'];
    for (const field of financialFields) {
      if (masked[field]) {
        masked[field] = this.maskFinancial(masked[field], field);
      }
    }

    return masked;
  }

  static maskPII(value, type) {
    switch (type) {
      case 'email':
        // user@example.com -> u***@example.com
        const [local, domain] = value.split('@');
        return `${local[0]}***@${domain}`;

      case 'phone':
        // +5511999998888 -> +55119****8888
        return value.substring(0, 7) + '****' + value.substring(value.length - 4);

      case 'cpf':
        // 123.456.789-00 -> ***.456.789-**
        return '***.' + value.substring(4, 7) + '.***-**';

      default:
        return value.substring(0, 2) + '***' + value.substring(value.length - 2);
    }
  }

  static maskFinancial(value, type) {
    switch (type) {
      case 'credit_card':
        // 4111111111111111 -> **** **** **** 1111
        return '**** **** **** ' + value.substring(value.length - 4);

      case 'bank_account':
        // 12345678-9 -> *****678-9
        return '*****' + value.substring(value.length - 4);

      default:
        return '***REDACTED***';
    }
  }
}

// Uso em audit logging
function logWithMasking(event) {
  const maskedEvent = DataMasker.maskSensitiveData(event);
  auditLogger.log(maskedEvent);
}
```

---

## 17.18 Relação com o Caso Misantropi4

### 17.18.1 Análise de compliance do IDAP

O caso Misantropi4 contra o IDAP pode ser analisado sob a perspectiva de compliance para identificar falhas:

```
// Análise: O que o IDAP deveria ter implementado

const IDAPComplianceGaps = {
  // 1. OWASP ASVS
  owaspASVS: {
    expectedLevel: 'Nível 3 (dados governamentais)',
    gaps: [
      'V2.1.1: Senhas possivelmente armazenadas inseguramente',
      'V2.2.2: Rate limiting ausente ou insuficiente',
      'V2.3.4: MFA não obrigatório para operadores',
      'V3.1.3: Session timeout não configurado',
      'V4.1.1: Authorization controls inadequados',
      'V7.1: Audit logging insuficiente'
    ],
    impact: 'CRÍTICO — Todos os requisitos ASVS Nível 3 violados'
  },

  // 2. NIST SP 800-63
  nistSP80063: {
    expectedAAL: 'AAL2 (mínimo para dados governamentais)',
    gaps: [
      'AAL2 requires MFA: Não implementado',
      'Password policy: Não seguia NIST SP 800-63B',
      'Rate limiting: Não atendia requisitos NIST',
      'Account lockout: Ausente ou inadequado'
    ],
    impact: 'CRÍTICO — Requisitos NIST violados'
  },

  // 3. LGPD
  lgpd: {
    expectedCompliance: 'Total (dados de milhões de cidadãos)',
    gaps: [
      'Art. 46: Medidas de segurança inadequadas',
      'Art. 6, III: Necessidade — acesso excessivo',
      'Art. 6, V: Segurança — controles insuficientes',
      'Art. 46: Integrity — logs auditáveis ausentes',
      'Art. 48: Comunicação de incidentes — provavelmente atrasada'
    ],
    impact: 'CRÍTICO — LGPD significativamente violada'
  },

  // 4. NIST Cybersecurity Framework
  nistCSF: {
    expectedFunctions: ['Identify', 'Protect', 'Detect', 'Respond', 'Recover'],
    gaps: [
      'Protect: Controles de autenticação inadequados',
      'Detect: Monitoring e alertas insuficientes',
      'Respond: Incident response provavelmente não testado',
      'Recover: Recovery plan possivelmente não documentado'
    ],
    impact: 'ALTO — Múltiplas funções CSF comprometidas'
  }
};

// Lições aprendidas
const lessonsLearned = [
  'Compliance não é opcional para sistemas governamentais',
  'MFA deve ser obrigatório para qualquer sistema com dados sensíveis',
  'Rate limiting é uma defesa essencial contra credential stuffing',
  'Audit logging deve ser imutável e retido por período adequado',
  'Incident response deve ser testado regularmente',
  'Penetration testing deve ser realizado antes e após deploy',
  'Treinamento de segurança deve ser contínuo',
  'Classificação de dados determina controles necessários'
];
```

### 17.18.2 Plano de remediação

Se o IDAP fosse reconstruir o sistema após o incidente, o plano de remediação seria:

```
// Plano de remediação Misantropi4 — Fase 1 (Primeiras 2 semanas)
const remediationPhase1 = {
  immediate: [
    'Forçar reset de todas as senhas de usuários',
    'Habilitar MFA para todas as contas',
    'Implementar rate limiting em todos os endpoints de login',
    'Configurar alertas para login失败',
    'Revisar e revogar todas as sessões ativas'
  ],
  security: [
    'Migrar senhas para Argon2id',
    'Implementar account lockout',
    'Configurar session timeout (30 minutos)',
    'Implementar audit logging imutável',
    'Configurar HSTS e security headers'
  ]
};

// Fase 2 (1-3 meses)
const remediationPhase2 = {
  architecture: [
    'Implementar RBAC com least privilege',
    'Deploy policy engine (OPA/Cedar)',
    'Implementar WebAuthn/FIDO2 para passwordless',
    'Configurar SIEM para monitoramento centralizado',
    'Implementar data classification'
  ],
  compliance: [
    'Realizar DPIA para todos os dados processados',
    'Documentar todas as políticas de segurança',
    'Implementar programa de treinamento',
    'Configurar vulnerability scanning contínuo',
    'Agendar penetration testing'
  ]
};

// Fase 3 (3-6 meses)
const remediationPhase3 = {
  maturity: [
    'Implementar SOC 2 readiness',
    'Configurar compliance automation',
    'Implementar bug bounty program',
    'Realizar auditoria de compliance completa',
    'Documentar lições aprendidas e compartilhar publicamente'
  ]
};
```

---

## Resumo

Este capítulo apresentou um guia abrangente de compliance e boas práticas para autenticação, autorização, e controle de acesso. O OWASP ASVS fornece o framework de verificação mais completo, com níveis de verificação alinhados ao risco do sistema. O OWASP Top 10 identifica as vulnerabilidades mais comuns e críticas. O NIST SP 800-63 define padrões rigorosos para identidade digital, enquanto LGPD e GDPR estabelecem requisitos legais para proteção de dados. PCI DSS e HIPAA adicionam requisitos específicos para dados financeiros e de saúde, respectivamente. SOC 2 fornece framework para auditoria de serviços. Métricas e KPIs permitem medir eficácia dos controles. Treinamento e conscientização são requisitos de compliance. Gestão de vulnerabilidades e riscos de terceiros completam o panorama. Classificação de dados determina quais controles são necessários. O caso Misantropi4 contra o IDAP serve como lembrete de que a não conformidade não é apenas um risco legal — é um risco de segurança que pode afetar milhões de pessoas. O checklist de 50+ itens, árvores de decisão, e referência rápida fornecem ferramentas práticas para implementação imediata. O OWASP ASVS fornece o framework de verificação mais completo, com níveis de verificação alinhados ao risco do sistema. O OWASP Top 10 identifica as vulnerabilidades mais comuns e críticas. O NIST SP 800-63 define padrões rigorosos para identidade digital, enquanto LGPD e GDPR estabelecem requisitos legais para proteção de dados. PCI DSS e HIPAA adicionam requisitos específicos para dados financeiros e de saúde, respectivamente. SOC 2 fornece framework para auditoria de serviços. O checklist de 50+ itens, árvores de decisão, e referência rápida fornecem ferramentas práticas para implementação. O caso Misantropi4 contra o IDAP serve como lembrete de que a não conformidade não é apenas um risco legal — é um risco de segurança que pode afetar milhões de pessoas.

---

## Exercícios

1. **Gap analysis**: Realize uma análise de gap entre os requisitos OWASP ASVS Nível 2 e um projeto real. Identifique os controles ausentes e priorize implementação

2. **LGPD compliance check**: Verifique se um sistema existente atende aos requisitos LGPD para autenticação. Documente os gaps e proponha correções

3. **PCI DSS assessment**: Avalie um endpoint de pagamento contra os requisitos 8 e 10 do PCI DSS. Documente não conformidades e proponha remediação

4. **NIST SP 800-63 implementation**: Implemente autenticação NIST-compliant com AAL2. Inclua MFA, rate limiting, e audit logging

5. **Compliance automation**: Configure um pipeline CI/CD que verifique automaticamente anti-patterns de autenticação. Teste com código vulnerável e código seguro

6. **Incident response drill**: Simule um incidente de autenticação (conta comprometida) e execute o plano de resposta documentado na seção 17.11.3

7. **SOC 2 readiness**: Avalie um sistema contra os Trust Service Criteria SOC 2. Identifique gaps e proponha plano de remediação

8. **DPIA creation**: Crie um DPIA para um sistema de autenticação que processe dados de saúde. Inclua todos os elementos do template da seção 17.5.2

---

## 17.19 Padrões de Arquitetura de Segurança

### 17.19.1 Defense in Depth para autenticação

Defense in Depth é a estratégia de múltiplas camadas de defesa. Nenhum controle individual é perfeito, mas combinados criam uma postura de segurança robusta:

```
// Camadas de defesa para autenticação

// CAMADA 1: Proteção de rede
// - WAF (Web Application Firewall)
// - DDoS protection
// - IP reputation filtering
// - Geo-blocking (se aplicável)

// CAMADA 2: Transporte
// - TLS 1.3 obrigatório
// - HSTS com preload
// - Certificate pinning (mobile)

// CAMADA 3: Aplicação
// - Input validation
// - Rate limiting
// - CAPTCHA (após N tentativas)
// - Security headers

// CAMADA 4: Autenticação
// - Password policy forte
// - MFA obrigatório
// - Account lockout
// - Breach detection

// CAMADA 5: Autorização
// - RBAC/ABAC
// - Least privilege
// - Deny-by-default
// - Separation of duty

// CAMADA 6: Sessão
// - Secure cookies
// - Token rotation
// - Session timeout
// - Invalidation on logout

// CAMADA 7: Dados
// - Encryption at rest
// - Encryption in transit
// - Data masking
// - Access logging

// CAMADA 8: Monitoramento
// - Real-time alerting
// - SIEM integration
// - Anomaly detection
// - Incident response
```

### 17.19.2 Zero Trust Architecture

Zero Trust é um modelo de segurança que assume nenhum usuário ou dispositivo é confiável por padrão, mesmo dentro da rede:

```
class ZeroTrustAuthArchitecture {
  constructor() {
    this.principles = {
      neverTrust: 'Nunca confie, sempre verifique',
      leastPrivilege: 'Acesso mínimo necessário',
      assumeBreach: 'Assuma que a rede já está comprometida',
      verifyExplicitly: 'Verifique cada acesso explicitamente'
    };
  }

  async evaluateAccess(request) {
    const context = {
      user: await this.verifyUser(request.user),
      device: await this.verifyDevice(request.device),
      network: await this.verifyNetwork(request.network),
      application: await this.verifyApplication(request.application),
      data: await this.classifyData(request.resource)
    };

    // Verificar TODOS os fatores
    const riskScore = this.calculateRiskScore(context);

    if (riskScore > this.thresholds.block) {
      return { allowed: false, reason: 'Risk score too high' };
    }

    if (riskScore > this.thresholds.stepUp) {
      return {
        allowed: true,
        stepUp: true,
        requiredAuth: this.getStepUpAuth(context)
      };
    }

    return { allowed: true, context };
  }

  async verifyUser(user) {
    return {
      authenticated: await this.verifyAuthentication(user),
      mfaVerified: await this.verifyMFA(user),
      riskLevel: await this.assessUserRisk(user),
      lastVerification: user.lastAuthTime
    };
  }

  async verifyDevice(device) {
    return {
      compliant: await this.checkDeviceCompliance(device),
      managed: device.managementStatus === 'managed',
      patched: await this.checkPatchLevel(device),
      encrypted: device.encryptionStatus === 'encrypted'
    };
  }

  async verifyNetwork(network) {
    return {
      trusted: this.isTrustedNetwork(network),
      location: await this.verifyLocation(network),
      vpn: network.vpnActive,
      proxy: network.proxyDetected
    };
  }

  calculateRiskScore(context) {
    let score = 0;

    // User factors
    if (!context.user.authenticated) score += 40;
    if (!context.user.mfaVerified) score += 20;
    if (context.user.riskLevel === 'high') score += 15;

    // Device factors
    if (!context.device.compliant) score += 15;
    if (!context.device.managed) score += 10;
    if (!context.device.patched) score += 10;
    if (!context.device.encrypted) score += 10;

    // Network factors
    if (!context.network.trusted) score += 10;
    if (context.network.proxy) score += 5;

    // Data sensitivity
    if (context.data.classification === 'RESTRICTED') score += 20;
    if (context.data.classification === 'CONFIDENTIAL') score += 10;

    return Math.min(score, 100);
  }
}
```

---

## 17.20 Template de Plano de Resposta a Incidentes

### 17.20.1 Plano de resposta para incidentes de autenticação

```
// Template de plano de resposta a incidentes
const IncidentResponsePlan = {
  metadata: {
    version: '1.0',
    lastUpdated: '2026-01-15',
    owner: 'Security Team',
    approvedBy: 'CISO'
  },

  phases: {
    // FASE 1: Preparação
    preparation: {
      description: 'Ativar time de resposta',
      actions: [
        'Verificar se o time de resposta está disponível',
        'Ativar canal de comunicação seguro (Slack/Teams dedicado)',
        'Preparar ambiente de investigation',
        'Notificar stakeholders conforme matrix de comunicação'
      ],
      responsible: 'Incident Commander',
      timeframe: 'Imediato'
    },

    // FASE 2: Identificação
    identification: {
      description: 'Determinar natureza e escopo do incidente',
      actions: [
        'Coletar evidências iniciais (logs, alertas)',
        'Classificar severidade (P1/P2/P3/P4)',
        'Determinar tipo de incidente',
        'Estimar impacto em usuários e dados',
        'DocumentarTimeline de eventos'
      ],
      severityClassification: {
        P1: 'Account takeover massivo, credentials vazadas, data breach',
        P2: 'Brute force ativo, MFA bypass, privilege escalation',
        P3: 'Tentativa de ataque bloqueada, vulnerability explorada sem sucesso',
        P4: 'Policy violation, suspicious activity detected'
      },
      responsible: 'Security Analyst',
      timeframe: '1 hora'
    },

    // FASE 3: Contenção
    containment: {
      shortTerm: {
        description: 'Conter o dano imediatamente',
        actions: [
          'Congelar contas comprometidas',
          'Invalidar todas as sessões afetadas',
          'Bloquear IPs/UA de atacantes',
          'Revogar tokens comprometidos',
          'Ativar WAF rules emergenciais'
        ]
      },
      longTerm: {
        description: 'Prevenir propagação',
        actions: [
          'Forçar reset de senha para usuários afetados',
          'Habilitar MFA obrigatório para todos',
          'Revisar e ajustar rate limiting',
          'Implementar controles adicionais',
          'Monitorar tentativas de re-ativação'
        ]
      },
      responsible: 'Security Engineer',
      timeframe: '4 horas'
    },

    // FASE 4: Erradicação
    eradication: {
      description: 'Remover causa raiz',
      actions: [
        'Identificar vetor de ataque completo',
        'Corrigir vulnerabilidade explorada',
        'Atualizar dependências vulneráveis',
        'Revisar configurações de segurança',
        'Implementar controles faltantes'
      ],
      responsible: 'Development Team + Security',
      timeframe: '24-72 horas'
    },

    // FASE 5: Recovery
    recovery: {
      description: 'Restaurar operações normais',
      actions: [
        'Restaurar sistemas de backup se necessário',
        'Verificar integridade dos dados',
        'Validar controles de segurança',
        'Monitorar intensivamente por 7 dias',
        'Confirmar normalização com stakeholders'
      ],
      responsible: 'Operations Team',
      timeframe: '24-48 horas'
    },

    // FASE 6: Lições aprendidas
    lessonsLearned: {
      description: 'Documentar e melhorar',
      actions: [
        'Realizar post-mortem (blameless)',
        'DocumentarTimeline completa',
        'Identificar melhorias de processo',
        'Atualizar runbooks e procedures',
        'Compartilhar lições com a organização',
        'Atualizar este plano conforme necessário'
      ],
      responsible: 'Incident Commander',
      timeframe: '5 dias após resolução'
    }
  },

  communicationMatrix: {
    internal: {
      'P1': ['CISO', 'CTO', 'CEO', 'Legal'],
      'P2': ['CISO', 'Security Team', 'Development Lead'],
      'P3': ['Security Team'],
      'P4': ['Security Analyst']
    },
    external: {
      'P1': ['ANPD (2 dias úteis)', 'Affected users', 'Law enforcement (se aplicável)'],
      'P2': ['ANPD (se data breach)', 'Affected users'],
      'P3': ['Nenhum (unless escalation)'],
      'P4': ['Nenhum']
    }
  }
};
```

---

## Referências

1. OWASP ASVS v4.0 — Application Security Verification Standard
2. OWASP Top 10 2021 — Top Ten Web Application Security Risks
3. NIST SP 800-63B — Digital Identity Guidelines: Authentication and Lifecycle Management
4. NIST SP 800-63C — Digital Identity Guidelines: Federation and Assertions
5. LGPD — Lei nº 13.709/2018 — Lei Geral de Proteção de Dados Pessoais
6. GDPR — Regulation (EU) 2016/679 — General Data Protection Regulation
7. PCI DSS v4.0 — Payment Card Industry Data Security Standard
8. HIPAA Security Rule — 45 CFR Part 164
9. SOC 2 — AICPA Trust Service Criteria
10. ANPD — Autoridade Nacional de Proteção de Dados — Orientações
11. OWASP Cheat Sheet Series — Authentication Cheat Sheet
12. OWASP Cheat Sheet Series — Authorization Cheat Sheet
13. OWASP Cheat Sheet Series — Session Management Cheat Sheet
14. NIST Cybersecurity Framework v2.0
15. ISO 27001:2022 — Information Security Management
16. Misantropi4 Case Study — Análise de incidente de segurança governamental (Capítulo 15)
17. LastPass Breach Analysis (2022) — Falhas em compliance e controles
18. Colonial Pipeline Incident (2021) — Falhas em MFA e VPN
19. Uber MFA Fatigue Attack (2022) — Falhas em processos de autenticação
20. SolarWinds Breach (2020) — Falhas em supply chain e compliance
---

*[Capítulo anterior: 16 — Padroes Seguros](16-padroes-seguros.md)*

