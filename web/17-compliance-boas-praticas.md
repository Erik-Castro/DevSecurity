# Capítulo 17: Compliance e Boas Práticas para Aplicações Web

## Sumário

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [OWASP ASVS](#2-owasp-asvs)
3. [OWASP SAMM](#3-owasp-samm)
4. [PCI DSS para Aplicações Web](#4-pci-dss-para-aplicações-web)
5. [LGPD/GDPR para Web Apps](#5-lgpdgdpr-para-web-apps)
6. [HIPAA para Aplicações Web de Saúde](#6-hipaa-para-aplicações-web-de-saúde)
7. [SOC 2 para SaaS Web](#7-soc-2-para-saas-web)
8. [ISO 27001 para Segurança de Aplicações Web](#8-iso-27001-para-segurança-de-aplicações-web)
9. [CIS Benchmarks para Web Servers](#9-cis-benchmarks-para-web-servers)
10. [Anti-Patterns em Segurança Web](#10-anti-patterns-em-segurança-web)
11. [Security Checklist Completa](#11-security-checklist-completa)
12. [Decision Trees](#12-decision-trees)
13. [Migração de Aplicações Legacy para Modernas e Seguras](#13-migração-de-aplicações-legacy-para-modernas-e-seguras)
14. [Templates de Documentação de Segurança](#14-templates-de-documentação-de-segurança)
15. [Exercícios](#15-exercícios)
16. [Referências](#16-referências)

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Compreender e aplicar os principais frameworks de compliance para aplicações web
- Implementar controles de segurança alinhados com OWASP ASVS e SAMM
- Garantir conformidade com PCI DSS em ambientes de pagamento web
- Implementar controles de proteção de dados conforme LGPD e GDPR
- Projetar aplicações web que atendam a requisitos de HIPAA
- Estruturar processos de segurança para certificação SOC 2
- Aplicar ISO 27001 no contexto de segurança de aplicações web
- Configurar web servers conforme CIS Benchmarks
- Identificar e evitar anti-patterns comuns em segurança web
- Utilizar checklists e decision trees para decisões de segurança
- Planejar migrações de aplicações legacy para arquiteturas modernas seguras
- Criar documentação de segurança padronizada e eficaz

### 1.1 Por que Compliance Importa

Compliance não é apenas um requisito legal ou regulatório — é um indicador de maturidade em segurança da informação. Organizações que ignoram frameworks de compliance enfrentam riscos significativos:

- Multas regulatórias que podem chegar a 4% do faturamento global (GDPR)
- Perda de confiança dos clientes e parceiros comerciais
- Custos de remediação pós-incidente muito superiores aos investimentos preventivos
- Impacto reputacional que pode levar anos para ser mitigado

O desenvolvedor web moderno precisa entender que segurança e compliance são intrínsecos ao desenvolvimento de software de qualidade. Não são fases posteriores ou tarefas de equipe isolada — são responsabilidades de toda a cadeia de desenvolvimento.

### 1.2 Abordagem deste Capítulo

Cada seção deste capítulo aborda um framework ou padrão específico, incluindo:

- Visão geral e contexto regulatório
- Requisitos principais relevantes para desenvolvimento web
- Implementação prática com código
- Ferramentas de verificação e automação
- Integração com pipelines de CI/CD

---

## 2. OWASP ASVS

### 2.1 Visão Geral

O OWASP Application Security Verification Standard (ASVS) é um framework aberto que fornece base para testes de segurança de aplicações web. Diferente do OWASP Top 10, que lista vulnerabilidades mais comuns, o ASVS define níveis de verificação de segurança que podem ser aplicados em diferentes contextos.

### 2.2 Níveis de Verificação

O ASVS define três níveis de verificação:

**Nível 1 — Padrão (Required)**
- Adequado para aplicações de baixo risco
- Foco em controles básicos de segurança
- Mínimo 28 requisitos verificáveis

**Nível 2 — Padrão (Standard)**
- Para aplicações que contêm dados sensíveis
- Exige controles adicionais além do nível 1
- Recomendado para a maioria das aplicações web

**Nível 3 — Avançado (Advanced)**
- Para aplicações de alta segurança
- Controles avançados contra ataques sofisticados
- Necessário para sistemas críticos

### 2.3 Requisitos Principais do ASVS para Web Apps

#### 2.3.1 Arquitetura de Segurança (Capítulo 1)

```yaml
# ASVS Architecture Requirements Summary
levels:
  level_1:
    requirements:
      - 1.1.1: Use of secure development lifecycle
      - 1.2.1: Security architecture documentation
      - 1.3.1: Threat modeling
      - 1.4.1: Security controls verification
    focus: Basic architecture controls

  level_2:
    requirements:
      - 1.5.1: Architectural security controls
      - 1.6.1: Threat intelligence integration
      - 1.7.1: Segregation of duties
    focus: Enhanced architectural controls

  level_3:
    requirements:
      - 1.8.1: Advanced threat modeling
      - 1.9.1: Security architecture review
      - 1.10.1: Compliance verification
    focus: Advanced architectural controls
```

#### 2.3.2 Autenticação (Capítulo 2)

```typescript
// ASVS Level 2 Authentication Implementation
interface ASVSAuthConfig {
  // 2.1.1 - Password requirements
  passwordPolicy: {
    minLength: number;           // Minimum 12 characters for L2
    maxLength: number;           // Maximum 128 characters
    requireUppercase: boolean;   // At least 1 uppercase
    requireLowercase: boolean;   // At least 1 lowercase
    requireNumber: boolean;      // At least 1 number
    requireSpecial: boolean;     // At least 1 special character
    maxAge: number;              // Password expiration in days
    historyCount: number;        // Password history to prevent reuse
  };

  // 2.2.1 - Authentication mechanisms
  mfaEnabled: boolean;           // Multi-factor authentication required
  mfaMethods: MFAMethod[];       // Supported MFA methods

  // 2.3.1 - Credential storage
  passwordHashing: {
    algorithm: 'argon2id' | 'bcrypt' | 'scrypt';
    memoryCost: number;          // Memory cost for argon2
    timeCost: number;            // CPU cost
    parallelism: number;         // Parallelism parameter
    saltLength: number;          // Salt length in bytes
  };

  // 2.4.1 - Credential recovery
  recoveryOptions: RecoveryMethod[];
}

enum MFAMethod {
  TOTP = 'totp',
  WEBAUTHN = 'webauthn',
  SMS = 'sms',
  EMAIL = 'email'
}

enum RecoveryMethod {
  BACKUP_CODES = 'backup_codes',
  EMAIL = 'email',
  SECURITY_QUESTIONS = 'security_questions',
  ADMIN_RESET = 'admin_reset'
}

// ASVS Level 2 Password Validator
class ASVSPasswordValidator implements PasswordValidator {
  private config: ASVSAuthConfig['passwordPolicy'];

  constructor(config: ASVSAuthConfig['passwordPolicy']) {
    this.config = config;
  }

  validate(password: string): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Length checks
    if (password.length < this.config.minLength) {
      errors.push(
        `Password must be at least ${this.config.minLength} characters`
      );
    }

    if (password.length > this.config.maxLength) {
      errors.push(
        `Password must not exceed ${this.config.maxLength} characters`
      );
    }

    // Character class checks
    if (this.config.requireUppercase && !/[A-Z]/.test(password)) {
      errors.push('Password must contain at least 1 uppercase letter');
    }

    if (this.config.requireLowercase && !/[a-z]/.test(password)) {
      errors.push('Password must contain at least 1 lowercase letter');
    }

    if (this.config.requireNumber && !/[0-9]/.test(password)) {
      errors.push('Password must contain at least 1 number');
    }

    if (this.config.requireSpecial && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      errors.push('Password must contain at least 1 special character');
    }

    // Check against common passwords
    if (this.isCommonPassword(password)) {
      errors.push('Password is too common');
    }

    // Check for sequential patterns
    if (this.hasSequentialPattern(password)) {
      warnings.push('Password contains sequential patterns');
    }

    // Check for repeated characters
    if (this.hasRepeatedCharacters(password)) {
      warnings.push('Password contains repeated characters');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      score: this.calculateStrengthScore(password)
    };
  }

  private isCommonPassword(password: string): boolean {
    const commonPasswords = [
      'password', '123456', '12345678', 'qwerty',
      'abc123', 'password123', 'admin', 'welcome'
    ];
    return commonPasswords.includes(password.toLowerCase());
  }

  private hasSequentialPattern(password: string): boolean {
    const sequentialPatterns = [
      'abcdef', '123456', 'qwerty', 'zxcvbn'
    ];
    const lowerPassword = password.toLowerCase();
    return sequentialPatterns.some(pattern =>
      lowerPassword.includes(pattern)
    );
  }

  private hasRepeatedCharacters(password: string): boolean {
    return /(.)\1{2,}/.test(password);
  }

  private calculateStrengthScore(password: string): number {
    let score = 0;
    score += Math.min(password.length * 2, 40);
    if (/[A-Z]/.test(password)) score += 10;
    if (/[a-z]/.test(password)) score += 10;
    if (/[0-9]/.test(password)) score += 10;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 15;
    return Math.min(score, 100);
  }
}

interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  score: number;
}
```

#### 2.3.3 Gerenciamento de Sessão (Capítulo 3)

```typescript
// ASVS Session Management Implementation
interface SessionConfig {
  // 3.1.1 - Session management
  sessionTimeout: number;              // Idle timeout in minutes
  absoluteTimeout: number;             // Absolute timeout in minutes
  regenerateOnAuth: boolean;           // Regenerate session ID after auth
  regenerateInterval: number;          // Periodic regeneration interval

  // 3.2.1 - Cookie attributes
  cookieConfig: {
    httpOnly: boolean;                 // Prevent JavaScript access
    secure: boolean;                   // HTTPS only
    sameSite: 'strict' | 'lax' | 'none';
    domain: string;
    path: string;
    maxAge: number;                    // Cookie expiration
  };

  // 3.3.1 - Token management
  tokenConfig: {
    accessTokenTTL: number;            // Access token TTL in seconds
    refreshTokenTTL: number;           // Refresh token TTL in seconds
    rotateRefreshTokens: boolean;      // Rotate refresh tokens
    revokeOnLogout: boolean;           // Revoke tokens on logout
  };
}

class ASVSSessionManager {
  private store: SessionStore;
  private config: SessionConfig;

  constructor(store: SessionStore, config: SessionConfig) {
    this.store = store;
    this.config = config;
  }

  async createSession(
    userId: string,
    request: IncomingMessage
  ): Promise<Session> {
    const sessionId = crypto.randomBytes(32).toString('hex');

    const session: Session = {
      id: sessionId,
      userId,
      createdAt: new Date(),
      lastAccessedAt: new Date(),
      ipAddress: request.socket.remoteAddress || '',
      userAgent: request.headers['user-agent'] || '',
      data: {}
    };

    await this.store.create(session);

    return session;
  }

  async validateSession(
    sessionId: string,
    request: IncomingMessage
  ): Promise<SessionValidationResult> {
    const session = await this.store.get(sessionId);

    if (!session) {
      return { valid: false, reason: 'Session not found' };
    }

    // Check idle timeout
    const idleTime = Date.now() - session.lastAccessedAt.getTime();
    if (idleTime > this.config.sessionTimeout * 60 * 1000) {
      await this.store.delete(sessionId);
      return { valid: false, reason: 'Session idle timeout' };
    }

    // Check absolute timeout
    const totalTime = Date.now() - session.createdAt.getTime();
    if (totalTime > this.config.absoluteTimeout * 60 * 1000) {
      await this.store.delete(sessionId);
      return { valid: false, reason: 'Session absolute timeout' };
    }

    // Validate IP and User-Agent
    if (session.ipAddress !== request.socket.remoteAddress) {
      await this.store.delete(sessionId);
      return { valid: false, reason: 'IP address mismatch' };
    }

    if (session.userAgent !== request.headers['user-agent']) {
      await this.store.delete(sessionId);
      return { valid: false, reason: 'User-Agent mismatch' };
    }

    // Update last accessed time
    await this.store.update(sessionId, {
      lastAccessedAt: new Date()
    });

    return { valid: true, session };
  }

  async destroySession(sessionId: string): Promise<void> {
    await this.store.delete(sessionId);
  }

  getCookieHeader(session: Session): string {
    const { cookieConfig } = this.config;
    const parts = [
      `session=${session.id}`,
      `HttpOnly`,
      `Path=${cookieConfig.path}`,
      `Max-Age=${cookieConfig.maxAge}`
    ];

    if (cookieConfig.secure) {
      parts.push('Secure');
    }

    if (cookieConfig.sameSite) {
      parts.push(`SameSite=${cookieConfig.sameSite}`);
    }

    if (cookieConfig.domain) {
      parts.push(`Domain=${cookieConfig.domain}`);
    }

    return parts.join('; ');
  }
}

interface SessionValidationResult {
  valid: boolean;
  session?: Session;
  reason?: string;
}
```

#### 2.3.4 Controle de Acesso (Capítulo 4)

```typescript
// ASVS Authorization Implementation
interface AuthorizationConfig {
  // 4.1.1 - Access control
  defaultDeny: boolean;               // Deny by default
  roleBasedAccess: boolean;           // RBAC enabled
  attributeBasedAccess: boolean;      // ABAC enabled

  // 4.2.1 - Access control mechanisms
  accessControl: {
    enforceAtController: boolean;     // Check at controller level
    enforceAtService: boolean;        // Check at service level
    enforceAtDatabase: boolean;       // Check at database level
    auditAllAccess: boolean;          // Audit all access attempts
  };

  // 4.3.1 - Administrative access
  adminAccess: {
    requireMFA: boolean;              // MFA for admin access
    sessionTimeout: number;           // Shorter timeout for admin
    ipWhitelist: string[];            // IP whitelist for admin
  };
}

class ASVSAuthorizationService {
  private policies: Map<string, Policy> = new Map();
  private auditLog: AuditLogger;

  constructor(auditLog: AuditLogger) {
    this.auditLog = auditLog;
  }

  async checkAccess(
    user: User,
    resource: Resource,
    action: Action,
    context: RequestContext
  ): Promise<AuthorizationResult> {
    // Get all applicable policies
    const applicablePolicies = this.getPoliciesForResource(resource);

    // Check each policy
    for (const policy of applicablePolicies) {
      const result = await this.evaluatePolicy(
        policy, user, resource, action, context
      );

      if (result.decision === 'deny') {
        await this.auditLog.log({
          userId: user.id,
          resourceId: resource.id,
          action: action.name,
          decision: 'deny',
          reason: result.reason,
          timestamp: new Date()
        });

        return { allowed: false, reason: result.reason };
      }
    }

    // Default deny if no policy explicitly allows
    await this.auditLog.log({
      userId: user.id,
      resourceId: resource.id,
      action: action.name,
      decision: 'allowed',
      timestamp: new Date()
    });

    return { allowed: true };
  }

  private async evaluatePolicy(
    policy: Policy,
    user: User,
    resource: Resource,
    action: Action,
    context: RequestContext
  ): Promise<PolicyEvaluationResult> {
    // Check role-based conditions
    if (policy.conditions.roles) {
      const hasRole = policy.conditions.roles.some(
        role => user.roles.includes(role)
      );
      if (!hasRole) {
        return { decision: 'deny', reason: 'Insufficient role' };
      }
    }

    // Check attribute-based conditions
    if (policy.conditions.attributes) {
      for (const [key, value] of Object.entries(
        policy.conditions.attributes
      )) {
        if (user.attributes[key] !== value) {
          return { decision: 'deny', reason: `Attribute ${key} mismatch` };
        }
      }
    }

    // Check time-based conditions
    if (policy.conditions.timeRange) {
      const now = new Date();
      const { start, end } = policy.conditions.timeRange;
      if (now < start || now > end) {
        return { decision: 'deny', reason: 'Outside allowed time range' };
      }
    }

    // Check IP-based conditions
    if (policy.conditions.ipWhitelist) {
      if (!policy.conditions.ipWhitelist.includes(context.ipAddress)) {
        return { decision: 'deny', reason: 'IP not in whitelist' };
      }
    }

    return { decision: 'allow' };
  }

  private getPoliciesForResource(resource: Resource): Policy[] {
    return Array.from(this.policies.values()).filter(
      policy => policy.resourceType === resource.type
    );
  }
}
```

#### 2.3.5 Validação de Entrada (Capítulo 5)

```typescript
// ASVS Input Validation Implementation
interface ValidationConfig {
  // 5.1.1 - Input validation
  whitelistValidation: boolean;       // Whitelist approach
  inputLengthLimits: {                // Maximum input lengths
    string: number;
    array: number;
    object: number;
  };

  // 5.2.1 - Output encoding
  outputEncoding: {
    html: boolean;                    // HTML entity encoding
    javascript: boolean;              // JavaScript string encoding
    url: boolean;                     // URL encoding
    css: boolean;                     // CSS encoding
    sql: boolean;                     // SQL parameterization
  };

  // 5.3.1 - SQL Injection prevention
  sqlInjection: {
    useParameterizedQueries: boolean;
    useORM: boolean;
    useStoredProcedures: boolean;
  };

  // 5.4.1 - XSS prevention
  xssPrevention: {
    contentSecurityPolicy: boolean;
    xssProtection: boolean;
    xContentTypeOptions: boolean;
    inputSanitization: boolean;
    outputEncoding: boolean;
  };
}

class ASVSInputValidator {
  private config: ValidationConfig;

  constructor(config: ValidationConfig) {
    this.config = config;
  }

  validateString(
    input: string,
    fieldName: string,
    rules: ValidationRules
  ): ValidationResult {
    const errors: string[] = [];

    // Check length limits
    if (input.length > this.config.inputLengthLimits.string) {
      errors.push(
        `${fieldName}: Exceeds maximum length of ${
          this.config.inputLengthLimits.string
        }`
      );
    }

    // Whitelist validation
    if (this.config.whitelistValidation) {
      const allowedPattern = rules.allowedCharacters || /^[a-zA-Z0-9\s]*$/;
      if (!allowedPattern.test(input)) {
        errors.push(
          `${fieldName}: Contains invalid characters`
        );
      }
    }

    // Pattern validation
    if (rules.pattern && !rules.pattern.test(input)) {
      errors.push(
        `${fieldName}: Does not match required pattern`
      );
    }

    // Length range validation
    if (rules.minLength && input.length < rules.minLength) {
      errors.push(
        `${fieldName}: Must be at least ${rules.minLength} characters`
      );
    }

    if (rules.maxLength && input.length > rules.maxLength) {
      errors.push(
        `${fieldName}: Must not exceed ${rules.maxLength} characters`
      );
    }

    // XSS detection
    if (this.config.xssPrevention.inputSanitization) {
      const xssPatterns = [
        /<script\b[^>]*(?:document\.cookie|alert\(|eval\()/i,
        /javascript:/i,
        /on\w+\s*=/i,
        /data:text\/html/i
      ];

      for (const pattern of xssPatterns) {
        if (pattern.test(input)) {
          errors.push(`${fieldName}: Potential XSS detected`);
          break;
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitized: this.sanitizeString(input)
    };
  }

  validateObject(
    input: Record<string, unknown>,
    schema: ValidationSchema
  ): ValidationResult {
    const errors: string[] = [];

    // Check for unknown fields (whitelist approach)
    const allowedFields = Object.keys(schema.fields);
    const inputFields = Object.keys(input);

    for (const field of inputFields) {
      if (!allowedFields.includes(field)) {
        errors.push(`Unknown field: ${field}`);
      }
    }

    // Validate each field
    for (const [fieldName, fieldSchema] of Object.entries(schema.fields)) {
      const value = input[fieldName];

      if (value === undefined || value === null) {
        if (fieldSchema.required) {
          errors.push(`${fieldName}: Required field missing`);
        }
        continue;
      }

      const fieldResult = this.validateField(
        value, fieldName, fieldSchema
      );

      if (!fieldResult.isValid) {
        errors.push(...fieldResult.errors);
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  private validateField(
    value: unknown,
    fieldName: string,
    schema: FieldSchema
  ): ValidationResult {
    switch (schema.type) {
      case 'string':
        return this.validateString(
          value as string, fieldName, schema.rules || {}
        );
      case 'number':
        return this.validateNumber(
          value as number, fieldName, schema.rules || {}
        );
      case 'email':
        return this.validateEmail(value as string, fieldName);
      case 'url':
        return this.validateUrl(value as string, fieldName);
      default:
        return { isValid: true, errors: [] };
    }
  }

  private validateNumber(
    value: number,
    fieldName: string,
    rules: ValidationRules
  ): ValidationResult {
    const errors: string[] = [];

    if (rules.min !== undefined && value < rules.min) {
      errors.push(
        `${fieldName}: Must be at least ${rules.min}`
      );
    }

    if (rules.max !== undefined && value > rules.max) {
      errors.push(
        `${fieldName}: Must not exceed ${rules.max}`
      );
    }

    if (rules.integer && !Number.isInteger(value)) {
      errors.push(`${fieldName}: Must be an integer`);
    }

    return { isValid: errors.length === 0, errors };
  }

  private validateEmail(
    value: string,
    fieldName: string
  ): ValidationResult {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const isValid = emailRegex.test(value);

    return {
      isValid,
      errors: isValid ? [] : [`${fieldName}: Invalid email format`]
    };
  }

  private validateUrl(
    value: string,
    fieldName: string
  ): ValidationResult {
    try {
      const url = new URL(value);
      const allowedProtocols = ['http:', 'https:'];

      if (!allowedProtocols.includes(url.protocol)) {
        return {
          isValid: false,
          errors: [
            `${fieldName}: Only HTTP and HTTPS protocols allowed`
          ]
        };
      }

      return { isValid: true, errors: [] };
    } catch {
      return {
        isValid: false,
        errors: [`${fieldName}: Invalid URL format`]
      };
    }
  }

  private sanitizeString(input: string): string {
    return input
      .replace(/[<>]/g, '') // Remove angle brackets
      .replace(/['"]/g, '') // Remove quotes
      .trim();
  }
}
```

### 2.4 Ferramentas de Verificação ASVS

```yaml
# ASVS Verification Tools
asvs_tools:
  static_analysis:
    - name: SonarQube
      url: https://www.sonarsource.com/
      purpose: Code quality and security analysis
      integration: CI/CD pipeline

    - name: Bandit
      url: https://bandit.readthedocs.io/
      purpose: Python security linter
      command: bandit -r src/

    - name: ESLint Security
      url: https://github.com/nodesecurity/eslint-plugin-security
      purpose: JavaScript security rules
      command: eslint --plugin security src/

  dynamic_analysis:
    - name: OWASP ZAP
      url: https://www.zaproxy.org/
      purpose: Dynamic application security testing
      command: zap-cli quick-scan -r http://localhost:3000

    - name: Burp Suite
      url: https://portswigger.net/burp
      purpose: Professional DAST tool
      integration: Manual and automated scans

  dependency_scanning:
    - name: npm audit
      command: npm audit
      purpose: Check for known vulnerabilities

    - name: Snyk
      url: https://snyk.io/
      purpose: Comprehensive dependency scanning

    - name: OWASP Dependency-Check
      url: https://owasp.org/www-project-dependency-check/
      purpose: Detects public CVEs in project dependencies

  infrastructure_scanning:
    - name: Lynis
      url: https://cisofy.com/lynis/
      purpose: System hardening audit
      command: lynis audit system

    - name: Docker Bench Security
      url: https://github.com/docker/docker-bench-security
      purpose: Docker container security
      command: ./docker-bench-security.sh
```

---

## 3. OWASP SAMM

### 3.1 Visão Geral

O OWASP Software Assurance Maturity Model (SAMM) é um framework de avaliação de maturidade de segurança de software. Diferente do ASVS, que foca em controles técnicos, o SAMM avalia processos e práticas de segurança em toda a organização.

### 3.2 Domínios do SAMM

O SAMM é organizado em 5 domínios, cada um com 3 práticas:

**Governo**
- Estratégia e Métricas
- Política e Compliace
- Educação e Orientação

**Design**
- Requisitos de Segurança
- Ameaças e Defesas
- Segurança de Arquitetura

**Implementação**
- Segurança no Desenvolvimento
- Segurança de Construção e Deploy
- Defesa em profundidade

**Verificação**
- Testes de Segurança
- Revisão de Arquitetura
- Revisão de Código

**Operações**
- Gerenciamento de Incidentes
- Gerenciamento de Ativos
- Gerenciamento de Mudanças e Infraestrutura

### 3.3 Níveis de Maturidade

Cada prática pode estar em 4 níveis de maturidade:

**Nível 0 — Inicial**
- Processos ad hoc e reativos
- Nenhuma formalização
- Conhecimento em silos

**Nível 1 — Repetível**
- Processos documentados
- Consistência básica
- Conhecimento compartilhado

**Nível 2 — Definido**
- Processos padronizados
- Métricas coletadas
- Melhoria contínua iniciada

**Nível 3 — Gerenciado**
- Processos otimizados
- Métricas avançadas
- Melhoria contínua madura

### 3.4 Avaliação de Maturidade SAMM

```python
# SAMM Maturity Assessment Implementation
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import IntEnum
from datetime import datetime


class MaturityLevel(IntEnum):
    INITIAL = 0
    REPEATABLE = 1
    DEFINED = 2
    MANAGED = 3


@dataclass
class PracticeAssessment:
    domain: str
    practice: str
    current_level: MaturityLevel
    target_level: MaturityLevel
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]


@dataclass
class DomainScore:
    domain: str
    practices: List[PracticeAssessment]
    average_level: float
    overall_level: MaturityLevel


@dataclass
class SAMMAssessment:
    organization: str
    assessment_date: datetime
    assessor: str
    domains: List[DomainScore]
    overall_maturity: float
    overall_level: MaturityLevel
    summary: str
    action_items: List[str]


class SAMMAssessor:
    def __init__(self):
        self.domains = [
            'Governance', 'Design', 'Implementation',
            'Verification', 'Operations'
        ]

        self.practices = {
            'Governance': [
                'Strategy and Metrics',
                'Policy and Compliance',
                'Education and Guidance'
            ],
            'Design': [
                'Security Requirements',
                'Threat Assessment',
                'Security Architecture'
            ],
            'Implementation': [
                'Secure Build',
                'Secure Deployment',
                'Defense in Depth'
            ],
            'Verification': [
                'Assessment',
                'Architecture Assessment',
                'Code Review'
            ],
            'Operations': [
                'Incident Management',
                'Environment Management',
                'Operational Management'
            ]
        }

    def assess_practice(
        self,
        domain: str,
        practice: str,
        responses: Dict[str, bool]
    ) -> PracticeAssessment:
        """Assess a single practice based on questionnaire responses."""

        level = self.calculate_level(responses)
        evidence = self.collect_evidence(responses)
        gaps = self.identify_gaps(responses, level)
        recommendations = self.generate_recommendations(
            domain, practice, level, gaps
        )

        return PracticeAssessment(
            domain=domain,
            practice=practice,
            current_level=level,
            target_level=self.determine_target_level(domain, practice),
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )

    def calculate_level(
        self, responses: Dict[str, bool]
    ) -> MaturityLevel:
        """Calculate maturity level based on responses."""
        true_count = sum(responses.values())
        total = len(responses)

        if total == 0:
            return MaturityLevel.INITIAL

        percentage = true_count / total

        if percentage >= 0.9:
            return MaturityLevel.MANAGED
        elif percentage >= 0.7:
            return MaturityLevel.DEFINED
        elif percentage >= 0.4:
            return MaturityLevel.REPEATABLE
        else:
            return MaturityLevel.INITIAL

    def collect_evidence(
        self, responses: Dict[str, bool]
    ) -> List[str]:
        """Collect evidence from positive responses."""
        evidence = []
        for question, answer in responses.items():
            if answer:
                evidence.append(f"Confirmed: {question}")
        return evidence

    def identify_gaps(
        self,
        responses: Dict[str, bool],
        current_level: MaturityLevel
    ) -> List[str]:
        """Identify gaps between current and target level."""
        gaps = []
        target = self.determine_target_level('', '')

        for question, answer in responses.items():
            if not answer:
                gaps.append(f"Not implemented: {question}")

        return gaps

    def generate_recommendations(
        self,
        domain: str,
        practice: str,
        current_level: MaturityLevel,
        gaps: List[str]
    ) -> List[str]:
        """Generate recommendations based on assessment."""
        recommendations = []

        if current_level == MaturityLevel.INITIAL:
            recommendations.append(
                f"Start documenting {practice} processes"
            )
            recommendations.append(
                f"Assign ownership for {practice} in {domain}"
            )
        elif current_level == MaturityLevel.REPEATABLE:
            recommendations.append(
                f"Standardize {practice} processes"
            )
            recommendations.append(
                f"Implement metrics for {practice}"
            )
        elif current_level == MaturityLevel.DEFINED:
            recommendations.append(
                f"Automate {practice} measurements"
            )
            recommendations.append(
                f"Integrate {practice} with other domains"
            )

        for gap in gaps[:3]:  # Top 3 gaps
            recommendations.append(f"Address: {gap}")

        return recommendations

    def determine_target_level(
        self, domain: str, practice: str
    ) -> MaturityLevel:
        """Determine target maturity level."""
        return MaturityLevel.DEFINED

    def generate_report(self, assessments: List[PracticeAssessment]) -> SAMMAssessment:
        """Generate full SAMM assessment report."""
        domain_scores = []

        for domain in self.domains:
            domain_practices = [
                a for a in assessments if a.domain == domain
            ]

            if domain_practices:
                avg_level = sum(
                    a.current_level for a in domain_practices
                ) / len(domain_practices)

                overall_level = MaturityLevel(round(avg_level))

                domain_scores.append(DomainScore(
                    domain=domain,
                    practices=domain_practices,
                    average_level=avg_level,
                    overall_level=overall_level
                ))

        overall_maturity = (
            sum(d.average_level for d in domain_scores) /
            len(domain_scores) if domain_scores else 0
        )

        return SAMMAssessment(
            organization="Assessment Organization",
            assessment_date=datetime.now(),
            assessor="Security Team",
            domains=domain_scores,
            overall_maturity=overall_maturity,
            overall_level=MaturityLevel(round(overall_maturity)),
            summary=self.generate_summary(domain_scores),
            action_items=self.generate_action_items(domain_scores)
        )

    def generate_summary(
        self, domain_scores: List[DomainScore]
    ) -> str:
        """Generate executive summary."""
        summary_parts = []

        for domain_score in domain_scores:
            summary_parts.append(
                f"{domain_score.domain}: "
                f"Level {domain_score.overall_level.value} "
                f"(avg: {domain_score.average_level:.1f})"
            )

        return " | ".join(summary_parts)

    def generate_action_items(
        self, domain_scores: List[DomainScore]
    ) -> List[str]:
        """Generate prioritized action items."""
        action_items = []

        # Sort by maturity level (lowest first)
        sorted_domains = sorted(
            domain_scores, key=lambda d: d.average_level
        )

        for domain_score in sorted_domains:
            for practice in domain_score.practices:
                if practice.current_level < practice.target_level:
                    action_items.append(
                        f"Improve {practice.practice} in "
                        f"{practice.domain} from level "
                        f"{practice.current_level.value} to "
                        f"{practice.target_level.value}"
                    )

        return action_items[:10]  # Top 10 action items
```

### 3.5 Integração SAMM com Pipeline

```yaml
# SAMM Integration in CI/CD Pipeline
saml_integration:
  stages:
    - name: security_metrics
      trigger: every_build
      actions:
        - collect_security_metrics
        - update_samm_dashboard
        - alert_on_regression

    - name: maturity_assessment
      trigger: quarterly
      actions:
        - run_assessment_questionnaire
        - generate_maturity_report
        - present_to_leadership

  metrics_collection:
    code_review:
      - metric: review_coverage
        target: 100
        unit: percent

      - metric: vulnerability_fix_time
        target: 48
        unit: hours

    testing:
      - metric: test_coverage
        target: 80
        unit: percent

      - metric: security_test_coverage
        target: 90
        unit: percent

    deployment:
      - metric: deployment_frequency
        target: daily
        unit: count

      - metric: mean_time_to_recovery
        target: 4
        unit: hours

  dashboards:
    - name: samm_maturity_overview
      refresh: daily
      widgets:
        - domain_maturity_chart
        - trend_analysis
        - gap_analysis
        - improvement_tracking
```

---

## 4. PCI DSS para Aplicações Web

### 4.1 Visão Geral do PCI DSS

O Payment Card Industry Data Security Standard (PCI DSS) é um padrão de segurança para organizações que processam, armazenam ou transmitem dados de cartão de crédito. Qualquer comerciante ou serviço que aceite pagamentos com cartão deve cumprir com o PCI DSS.

### 4.2 Requisitos do PCI DSS para Web Apps

**Requisito 1: Instalar e manter controle de acesso**
- Configurar firewall entre internet e rede de dados
- Restringir acesso a dados de cartão apenas ao necessário
- Documentar todas as permissões de acesso

**Requisito 2: Usar senhas padrão e outros parâmetros de segurança**
- Alterar senhas padrão de fábrica
- Implementar políticas de senha robustas
- Criptografar senhas em trânsito e em repouso

**Requisito 3: Proteger dados de titular de cartão**
- Criptografar transmissão de dados de cartão em redes públicas
- Não armazenar dados de trilha magnética
- Renderizar ilegíveis os dados de PAN quando armazenados

**Requisito 4: Criptografar transmissão de dados**
- Usar criptografia forte durante transmissão
- Implementar TLS 1.2 ou superior
- Verificar certificados SSL/TLS

**Requisito 5: Usar e atualizar software antivírus**
- Instalar software antivírus em todos os sistemas
- Manter assinaturas atualizadas
- Realizar verificações regulares

**Requisito 6: Desenvolver e manter sistemas seguros**
- Estabelecer processo de desenvolvimento seguro
- Aplicar patches de segurança regulares
- Implementar controles de segurança no desenvolvimento

**Requisito 7: Restringir acesso por necessidade**
- Implementar controle de acesso baseado em função
- Atribuir permissões conforme necessidade
- Revisar permissões periodicamente

**Requisito 8: Identificar e autenticar acesso**
- Implementar identificação única para usuários
- Autenticar acesso ao sistema
- Implementar controle de sessão

**Requisito 9: Restringir acesso físico**
- Implementar controles de acesso físico
- Monitorar acessos físicos
- Gerenciar mídias removíveis

**Requisito 10: Monitorar e auditar acessos**
- Implementar logs de acesso
- Monitorar atividades de usuários
- Revisar logs regularmente

**Requisito 11: Testar regularmente sistemas**
- Realizar testes de vulnerabilidade
- Executar testes de penetração
- Detectar mudanças não autorizadas

**Requisito 12: Manter política de segurança**
- Documentar políticas de segurança
- Treinar funcionários regularmente
- Implementar resposta a incidentes

### 4.3 Implementação PCI DSS em Web Apps

```typescript
// PCI DSS Compliant Payment Processing
interface PCIConfig {
  // Requirement 3: Protect cardholder data
  encryption: {
    algorithm: 'AES-256-GCM';
    keyRotationDays: number;
    keyStorage: 'HSM' | 'KMS' | 'vault';
  };

  // Requirement 4: Encrypt transmission
  tls: {
    minVersion: 'TLSv1.2';
    cipherSuites: string[];
    certificateValidation: boolean;
  };

  // Requirement 6: Develop secure systems
  securityHeaders: {
    strictTransportSecurity: boolean;
    contentSecurityPolicy: boolean;
    xFrameOptions: boolean;
  };

  // Requirement 8: Identify and authenticate
  authentication: {
    mfaRequired: boolean;
    sessionTimeout: number;
    passwordPolicy: PasswordPolicy;
  };

  // Requirement 10: Monitor access
  logging: {
    auditTrail: boolean;
    logRetention: number;
    realTimeAlerting: boolean;
  };
}

class PCIPaymentProcessor {
  private encryptionService: EncryptionService;
  private auditLogger: AuditLogger;
  private config: PCIConfig;

  constructor(config: PCIConfig) {
    this.config = config;
    this.encryptionService = new EncryptionService(
      config.encryption
    );
    this.auditLogger = new AuditLogger(config.logging);
  }

  async processPayment(
    paymentData: PaymentData,
    userId: string
  ): Promise<PaymentResult> {
    const requestId = crypto.randomUUID();

    try {
      // Log the attempt
      await this.auditLogger.log({
        action: 'payment_attempt',
        userId,
        requestId,
        timestamp: new Date()
      });

      // Validate input (Requirement 6)
      this.validatePaymentData(paymentData);

      // Tokenize card data (Requirement 3)
      const tokenizedData = await this.tokenizeCardData(
        paymentData.cardNumber
      );

      // Process payment with token
      const result = await this.chargeWithToken(
        tokenizedData,
        paymentData.amount,
        paymentData.currency
      );

      // Log success
      await this.auditLogger.log({
        action: 'payment_success',
        userId,
        requestId,
        transactionId: result.transactionId,
        amount: paymentData.amount,
        timestamp: new Date()
      });

      return result;
    } catch (error) {
      // Log failure
      await this.auditLogger.log({
        action: 'payment_failure',
        userId,
        requestId,
        error: error instanceof Error ? error.message : 'Unknown',
        timestamp: new Date()
      });

      throw error;
    }
  }

  private validatePaymentData(data: PaymentData): void {
    // Luhn algorithm for card number validation
    if (!this.validateCardNumber(data.cardNumber)) {
      throw new ValidationError('Invalid card number');
    }

    // Validate expiry date
    if (!this.validateExpiryDate(data.expiryDate)) {
      throw new ValidationError('Invalid expiry date');
    }

    // Validate CVV
    if (!this.validateCVV(data.cvv)) {
      throw new ValidationError('Invalid CVV');
    }

    // Validate amount
    if (data.amount <= 0 || data.amount > 99999999) {
      throw new ValidationError('Invalid amount');
    }
  }

  private validateCardNumber(cardNumber: string): boolean {
    // Luhn algorithm
    const digits = cardNumber.replace(/\D/g, '');
    let sum = 0;
    let alternate = false;

    for (let i = digits.length - 1; i >= 0; i--) {
      let n = parseInt(digits[i], 10);

      if (alternate) {
        n *= 2;
        if (n > 9) {
          n -= 9;
        }
      }

      sum += n;
      alternate = !alternate;
    }

    return sum % 10 === 0;
  }

  private validateExpiryDate(expiry: string): boolean {
    const [month, year] = expiry.split('/').map(Number);
    const now = new Date();
    const currentYear = now.getFullYear() % 100;
    const currentMonth = now.getMonth() + 1;

    if (month < 1 || month > 12) return false;
    if (year < currentYear) return false;
    if (year === currentYear && month < currentMonth) return false;

    return true;
  }

  private validateCVV(cvv: string): boolean {
    return /^\d{3,4}$/.test(cvv);
  }

  private async tokenizeCardData(
    cardNumber: string
  ): Promise<string> {
    // Replace card number with token
    // Actual implementation would call payment gateway
    const token = crypto.randomBytes(32).toString('hex');

    await this.auditLogger.log({
      action: 'card_tokenized',
      timestamp: new Date()
    });

    return token;
  }

  private async chargeWithToken(
    token: string,
    amount: number,
    currency: string
  ): Promise<PaymentResult> {
    // Simulate payment processing
    return {
      transactionId: crypto.randomUUID(),
      status: 'completed',
      amount,
      currency,
      timestamp: new Date()
    };
  }
}

// PCI DSS Security Headers Middleware
class PCISecurityHeaders {
  static getHeaders(): Record<string, string> {
    return {
      // Requirement 4: Encrypt transmission
      'Strict-Transport-Security':
        'max-age=31536000; includeSubDomains; preload',

      // Requirement 6: Develop secure systems
      'Content-Security-Policy':
        "default-src 'self'; " +
        "script-src 'self'; " +
        "style-src 'self'; " +
        "img-src 'self' data:; " +
        "font-src 'self'; " +
        "connect-src 'self'; " +
        "frame-ancestors 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'",

      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
      'X-XSS-Protection': '1; mode=block',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy':
        'camera=(), microphone=(), geolocation=()',

      // Hide server information
      'Server': '',
      'X-Powered-By': ''
    };
  }
}

interface PaymentData {
  cardNumber: string;
  expiryDate: string;
  cvv: string;
  amount: number;
  currency: string;
}

interface PaymentResult {
  transactionId: string;
  status: string;
  amount: number;
  currency: string;
  timestamp: Date;
}

interface ValidationError extends Error {
  code: string;
}
```

### 4.4 Scoping PCI DSS

```yaml
# PCI DSS Scope Definition
scope_definition:
  cardholder_data_environment:
    - payment_processing_servers
    - web_servers_accepting_card_data
    - databases_storing_card_data
    - authentication_servers

  connected_systems:
    - ldap_servers
    - dns_servers
    - logging_servers
    - monitoring_systems

  out_of_scope:
    - development_environments
    - testing_environments
    - backup_systems
    - third_party_services

  segmentation:
    method: network_segmentation
    controls:
      - firewall_rules
      - vlan_isolation
      - access_control_lists
      - encryption_in_transit

  validation:
    quarterly:
      - network_scan
      - vulnerability_assessment
      - penetration_test
    annually:
      - comprehensive_assessment
      - scope_validation
```

---

## 5. LGPD/GDPR para Web Apps

### 5.1 Visão Geral

A Lei Geral de Proteção de Dados (LGPD) no Brasil e o General Data Protection Regulation (GDPR) na Europa são regulamentações de proteção de dados que afetam diretamente aplicações web que coletam, processam ou armazenam dados pessoais.

### 5.2 Princípios Fundamentais

**Legalidade, Transparência e Boa-fé**
- Dados devem ser processados legalmente
- Usuários devem ser informados sobre o processamento
- Processamento deve ser realizado de boa-fé

**Finalidade e Adequação**
- Dados devem ser coletados para finalidades específicas
- Processamento deve ser compatível com a finalidade
- Dados devem ser adequados ao propósito

**Necessidade e Minimização**
- Coletar apenas dados necessários
- Limitar acesso aos dados ao mínimo necessário
- Manter dados apenas pelo tempo necessário

**Qualidade e Segurança**
- Dados devem ser precisos e atualizados
- Medidas de segurança adequadas devem ser implementadas
- Proteção contra acesso não autorizado

**Responsabilização e Prestação de Contas**
- Controlador deve demonstrar conformidade
- Implementar medidas de segurança
- Documentar processos de proteção de dados

### 5.3 Base Legal para Processamento

```typescript
// LGPD/GDPR Legal Basis Implementation
enum LegalBasis {
  CONSENT = 'consent',
  CONTRACT = 'contract',
  LEGAL_OBLIGATION = 'legal_obligation',
  VITAL_INTERESTS = 'vital_interests',
  PUBLIC_TASK = 'public_task',
  LEGITIMATE_INTERESTS = 'legitimate_interests'
}

interface ConsentRecord {
  id: string;
  userId: string;
  purposes: string[];
  timestamp: Date;
  ipAddress: string;
  userAgent: string;
  version: string;
  withdrawnAt?: Date;
}

class LGPDConsentManager {
  private consentStore: ConsentStore;

  constructor(consentStore: ConsentStore) {
    this.consentStore = consentStore;
  }

  async recordConsent(
    userId: string,
    purposes: string[],
    request: Request
  ): Promise<ConsentRecord> {
    const record: ConsentRecord = {
      id: crypto.randomUUID(),
      userId,
      purposes,
      timestamp: new Date(),
      ipAddress: request.ip || '',
      userAgent: request.headers['user-agent'] || '',
      version: '1.0'
    };

    await this.consentStore.save(record);

    return record;
  }

  async withdrawConsent(
    userId: string,
    purpose?: string
  ): Promise<void> {
    const records = await this.consentStore.findByUserId(userId);

    for (const record of records) {
      if (!purpose || record.purposes.includes(purpose)) {
        record.withdrawnAt = new Date();
        await this.consentStore.update(record);
      }
    }
  }

  async hasConsent(
    userId: string,
    purpose: string
  ): Promise<boolean> {
    const records = await this.consentStore.findByUserId(userId);

    return records.some(
      record =>
        record.purposes.includes(purpose) &&
        !record.withdrawnAt
    );
  }

  async getConsentHistory(
    userId: string
  ): Promise<ConsentRecord[]> {
    return this.consentStore.findByUserId(userId);
  }

  async exportConsentData(
    userId: string
  ): Promise<ConsentExport> {
    const records = await this.consentStore.findByUserId(userId);

    return {
      userId,
      records,
      exportedAt: new Date()
    };
  }
}

// Data Subject Rights Implementation
class LGPDDataSubjectRights {
  private dataStore: DataStore;
  private auditLogger: AuditLogger;

  constructor(dataStore: DataStore, auditLogger: AuditLogger) {
    this.dataStore = dataStore;
    this.auditLogger = auditLogger;
  }

  // Right to confirmation and access
  async getDataSubjectData(
    userId: string
  ): Promise<DataSubjectData> {
    const personalData = await this.dataStore.getPersonalData(
      userId
    );

    const processingActivities =
      await this.dataStore.getProcessingActivities(userId);

    return {
      personalData,
      processingActivities,
      dataCategories: this.getDataCategories(personalData),
      retentionPeriods: this.getRetentionPeriods(),
      thirdPartySharing: this.getThirdPartySharing()
    };
  }

  // Right to rectification
  async rectifyData(
    userId: string,
    corrections: Record<string, unknown>
  ): Promise<void> {
    await this.dataStore.updatePersonalData(userId, corrections);

    await this.auditLogger.log({
      action: 'data_rectification',
      userId,
      corrections,
      timestamp: new Date()
    });
  }

  // Right to erasure (right to be forgotten)
  async eraseData(
    userId: string,
    reason: string
  ): Promise<void> {
    // Check if erasure is required by law
    const legalHold = await this.checkLegalHold(userId);
    if (legalHold) {
      throw new Error(
        'Data cannot be erased due to legal requirements'
      );
    }

    await this.dataStore.deletePersonalData(userId);

    await this.auditLogger.log({
      action: 'data_erasure',
      userId,
      reason,
      timestamp: new Date()
    });
  }

  // Right to data portability
  async exportData(
    userId: string,
    format: 'json' | 'csv' | 'xml'
  ): Promise<DataExport> {
    const data = await this.getDataSubjectData(userId);

    return {
      data,
      format,
      exportedAt: new Date(),
      filename: `data-export-${userId}-${Date.now()}.${format}`
    };
  }

  // Right to object
  async objectToProcessing(
    userId: string,
    purpose: string
  ): Promise<void> {
    const currentConsent =
      await this.dataStore.getConsent(userId, purpose);

    if (currentConsent) {
      await this.dataStore.withdrawConsent(userId, purpose);
    }

    await this.auditLogger.log({
      action: 'processing_objection',
      userId,
      purpose,
      timestamp: new Date()
    });
  }

  private getDataCategories(
    data: Record<string, unknown>
  ): string[] {
    const categories = new Set<string>();

    // Identify data categories
    for (const key of Object.keys(data)) {
      if (key.includes('name') || key.includes('email')) {
        categories.add('identification');
      }
      if (key.includes('address') || key.includes('location')) {
        categories.add('location');
      }
      if (key.includes('birth') || key.includes('age')) {
        categories.add('demographic');
      }
    }

    return Array.from(categories);
  }

  private getRetentionPeriods(): Record<string, number> {
    return {
      identification: 365 * 5,
      contact: 365 * 3,
      location: 365 * 2,
      demographic: 365 * 5,
      financial: 365 * 7
    };
  }

  private getThirdPartySharing(): ThirdPartySharing[] {
    return [
      {
        recipient: 'Payment Processor',
        purpose: 'Payment processing',
        legalBasis: LegalBasis.CONTRACT
      },
      {
        recipient: 'Analytics Provider',
        purpose: 'Usage analytics',
        legalBasis: LegalBasis.LEGITIMATE_INTERESTS
      }
    ];
  }

  private async checkLegalHold(userId: string): Promise<boolean> {
    // Check if there are legal requirements to retain data
    return false;
  }
}
```

### 5.4 Privacy by Design

```typescript
// Privacy by Design Implementation
class PrivacyByDesign {
  // Data Minimization
  static collectMinimizedData(
    formData: Record<string, unknown>,
    requiredFields: string[]
  ): Record<string, unknown> {
    const minimized: Record<string, unknown> = {};

    for (const field of requiredFields) {
      if (formData[field] !== undefined) {
        minimized[field] = formData[field];
      }
    }

    return minimized;
  }

  // Purpose Limitation
  static enforcePurposeLimitation(
    data: Record<string, unknown>,
    purpose: string,
    purposeMap: Record<string, string[]>
  ): Record<string, unknown> {
    const allowedFields = purposeMap[purpose] || [];
    const limited: Record<string, unknown> = {};

    for (const field of allowedFields) {
      if (data[field] !== undefined) {
        limited[field] = data[field];
      }
    }

    return limited;
  }

  // Storage Limitation
  static enforceRetentionPolicy(
    data: Record<string, unknown>,
    retentionPolicies: Record<string, number>
  ): Record<string, unknown> {
    const now = new Date();
    const result: Record<string, unknown> = {};

    for (const [field, value] of Object.entries(data)) {
      const retentionDays = retentionPolicies[field] || 365;
      const created = (value as any).createdAt;
      const ageDays = (now.getTime() - new Date(created).getTime()) /
        (1000 * 60 * 60 * 24);

      if (ageDays < retentionDays) {
        result[field] = value;
      }
    }

    return result;
  }

  // Data Protection Impact Assessment
  static conductDPIA(
    project: ProjectInfo
  ): DPIAReport {
    const risks = this.assessRisks(project);
    const mitigations = this.identifyMitigations(risks);

    return {
      project: project.name,
      assessmentDate: new Date(),
      dataProcessing: project.dataProcessing,
      risks,
      mitigations,
      recommendations: this.generateRecommendations(risks)
    };
  }

  private static assessRisks(
    project: ProjectInfo
  ): RiskAssessment[] {
    const risks: RiskAssessment[] = [];

    // Assess data sensitivity
    if (project.dataProcessing.includes('health')) {
      risks.push({
        category: 'data_sensitivity',
        level: 'high',
        description: 'Processing health data',
        impact: 'Severe personal impact if breached'
      });
    }

    if (project.dataProcessing.includes('financial')) {
      risks.push({
        category: 'data_sensitivity',
        level: 'high',
        description: 'Processing financial data',
        impact: 'Financial loss if breached'
      });
    }

    // Assess processing scale
    if (project.expectedUsers > 100000) {
      risks.push({
        category: 'processing_scale',
        level: 'medium',
        description: 'Large scale processing',
        impact: 'Many individuals affected if breached'
      });
    }

    return risks;
  }

  private static identifyMitigations(
    risks: RiskAssessment[]
  ): Mitigation[] {
    return risks.map(risk => ({
      risk: risk.category,
      measure: this.getMitigationMeasure(risk.level),
      implementation: this.getImplementationSteps(risk.level)
    }));
  }

  private static getMitigationMeasure(
    level: string
  ): string {
    switch (level) {
      case 'high':
        return 'Encryption, access controls, audit logging';
      case 'medium':
        return 'Access controls, monitoring';
      case 'low':
        return 'Basic security measures';
      default:
        return 'Standard security practices';
    }
  }

  private static getImplementationSteps(
    level: string
  ): string[] {
    switch (level) {
      case 'high':
        return [
          'Implement end-to-end encryption',
          'Deploy strict access controls',
          'Enable comprehensive audit logging',
          'Conduct regular security assessments'
        ];
      case 'medium':
        return [
          'Implement access controls',
          'Enable monitoring and alerting',
          'Regular security reviews'
        ];
      default:
        return [
          'Apply standard security measures'
        ];
    }
  }

  private static generateRecommendations(
    risks: RiskAssessment[]
  ): string[] {
    const recommendations: string[] = [];

    if (risks.some(r => r.level === 'high')) {
      recommendations.push(
        'Conduct full DPIA before processing begins'
      );
      recommendations.push(
        'Consult with Data Protection Officer'
      );
    }

    recommendations.push(
      'Implement privacy by default settings'
    );
    recommendations.push(
      'Provide clear and accessible privacy notice'
    );
    recommendations.push(
      'Enable easy consent withdrawal mechanism'
    );

    return recommendations;
  }
}
```

### 5.5 Consent Management UI Component

```tsx
// LGPD/GDPR Consent Management Component
import React, { useState, useEffect } from 'react';

interface ConsentPurpose {
  id: string;
  name: string;
  description: string;
  required: boolean;
  category: string;
}

interface ConsentSettings {
  purposes: ConsentPurpose[];
  version: string;
  lastUpdated: Date;
}

interface ConsentManagerProps {
  userId: string;
  settings: ConsentSettings;
  onConsentChange: (consents: Record<string, boolean>) => void;
}

export const ConsentManager: React.FC<ConsentManagerProps> = ({
  userId,
  settings,
  onConsentChange
}) => {
  const [consents, setConsents] = useState<Record<string, boolean>>(
    {}
  );
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    // Load existing consents
    loadExistingConsents(userId);
  }, [userId]);

  const loadExistingConsents = async (userId: string) => {
    // In production, fetch from API
    const existing: Record<string, boolean> = {};
    settings.purposes.forEach(purpose => {
      existing[purpose.id] = purpose.required;
    });
    setConsents(existing);
  };

  const handleConsentChange = (
    purposeId: string,
    value: boolean
  ) => {
    const purpose = settings.purposes.find(
      p => p.id === purposeId
    );

    if (purpose?.required && !value) {
      // Cannot opt out of required purposes
      return;
    }

    const newConsents = { ...consents, [purposeId]: value };
    setConsents(newConsents);
    onConsentChange(newConsents);
  };

  const handleAcceptAll = () => {
    const allConsents: Record<string, boolean> = {};
    settings.purposes.forEach(purpose => {
      allConsents[purpose.id] = true;
    });
    setConsents(allConsents);
    onConsentChange(allConsents);
  };

  const handleRejectOptional = () => {
    const requiredOnly: Record<string, boolean> = {};
    settings.purposes.forEach(purpose => {
      requiredOnly[purpose.id] = purpose.required;
    });
    setConsents(requiredOnly);
    onConsentChange(requiredOnly);
  };

  const requiredPurposes = settings.purposes.filter(p => p.required);
  const optionalPurposes = settings.purposes.filter(p => !p.required);

  return (
    <div className="consent-manager">
      <h2>Configuracoes de Privacidade</h2>
      <p>
        Utilizamos cookies e processamos dados pessoais para
        melhorar sua experiencia. Voce pode personalizar suas
        preferencias abaixo.
      </p>

      <div className="consent-section">
        <h3>Essenciais (sempre ativos)</h3>
        {requiredPurposes.map(purpose => (
          <div key={purpose.id} className="consent-item">
            <label>
              <input
                type="checkbox"
                checked={true}
                disabled={true}
              />
              <strong>{purpose.name}</strong>
            </label>
            <p>{purpose.description}</p>
          </div>
        ))}
      </div>

      <div className="consent-section">
        <h3>Opcionais</h3>
        {optionalPurposes.map(purpose => (
          <div key={purpose.id} className="consent-item">
            <label>
              <input
                type="checkbox"
                checked={consents[purpose.id] || false}
                onChange={e =>
                  handleConsentChange(
                    purpose.id,
                    e.target.checked
                  )
                }
              />
              <strong>{purpose.name}</strong>
            </label>
            <p>{purpose.description}</p>
          </div>
        ))}
      </div>

      <div className="consent-actions">
        <button onClick={handleAcceptAll}>
          Aceitar Todos
        </button>
        <button onClick={handleRejectOptional}>
          Apenas Essenciais
        </button>
        <button onClick={() => setShowDetails(!showDetails)}>
          {showDetails ? 'Ocultar Detalhes' : 'Ver Detalhes'}
        </button>
      </div>

      {showDetails && (
        <div className="consent-details">
          <p>
            Versao: {settings.version} | Ultima atualizacao:{' '}
            {settings.lastUpdated.toLocaleDateString('pt-BR')}
          </p>
          <p>
            Voce pode alterar suas preferencias a qualquer momento
            nas configuracoes da conta.
          </p>
          <p>
            Para mais informacoes, consulte nossa{' '}
            <a href="/privacy">Politica de Privacidade</a>.
          </p>
        </div>
      )}
    </div>
  );
};
```

---

## 6. HIPAA para Aplicações Web de Saúde

### 6.1 Visão Geral

O Health Insurance Portability and Accountability Act (HIPAA) é uma regulamentacao dos EUA que protege dados de saude do paciente (PHI - Protected Health Information). Aplicacoes web de saude devem implementar controles rigorosos para proteger PHI.

### 6.2 Requisitos HIPAA para Web Apps

**Regras de Privacidade**
- Notificar pacientes sobre uso de PHI
- Implementar direitos de acesso ao paciente
- Documentar praticas de privacidade

**Regras de Seguranca**
- Controles administrativos
- Controles fisicos
- Controles tecnicos

**Regras de Notificacao de Violacao**
- Notificar individuos afetados
- Notificar HHS (Department of Health and Human Services)
- Notificar midia para violacoes grandes

### 6.3 Implementacao HIPAA

```typescript
// HIPAA Compliant Health Data Management
interface HIPAAConfig {
  // Administrative Controls
  administrativeControls: {
    securityOfficer: string;
    privacyOfficer: string;
    trainingFrequency: number;       // days
    riskAssessmentFrequency: number; // days
    contingencyPlan: boolean;
  };

  // Technical Controls
  technicalControls: {
    accessControl: {
      uniqueUserIdentification: boolean;
      emergencyAccessProcedure: boolean;
      automaticLogoff: number;       // minutes
      encryption: boolean;
    };
    auditControls: {
      auditLogging: boolean;
      auditReviewFrequency: number;  // days
      auditRetention: number;        // days
    };
    integrity: {
      dataIntegrityVerification: boolean;
      authentication: boolean;
      transmissionSecurity: boolean;
    };
  };

  // Physical Controls
  physicalControls: {
    facilityAccessControls: boolean;
    workstationSecurity: boolean;
    deviceControls: boolean;
    mediaControls: boolean;
  };
}

class HIPAADataManager {
  private encryptionService: EncryptionService;
  private auditLogger: AuditLogger;
  private accessControl: AccessControl;
  private config: HIPAAConfig;

  constructor(config: HIPAAConfig) {
    this.config = config;
    this.encryptionService = new EncryptionService();
    this.auditLogger = new AuditLogger();
    this.accessControl = new AccessControl();
  }

  async accessPHI(
    userId: string,
    patientId: string,
    dataType: string,
    purpose: string
  ): Promise<PHIData> {
    // Verify user authorization
    const isAuthorized = await this.accessControl.checkAccess(
      userId,
      patientId,
      dataType,
      purpose
    );

    if (!isAuthorized) {
      await this.auditLogger.log({
        action: 'access_denied',
        userId,
        patientId,
        dataType,
        purpose,
        timestamp: new Date()
      });

      throw new UnauthorizedError(
        'Not authorized to access this PHI'
      );
    }

    // Retrieve and decrypt PHI
    const encryptedData = await this.retrieveEncryptedPHI(
      patientId,
      dataType
    );

    const decryptedData = await this.encryptionService.decrypt(
      encryptedData
    );

    // Log access
    await this.auditLogger.log({
      action: 'phi_accessed',
      userId,
      patientId,
      dataType,
      purpose,
      timestamp: new Date()
    });

    return decryptedData;
  }

  async storePHI(
    patientId: string,
    dataType: string,
    data: PHIData,
    userId: string
  ): Promise<void> {
    // Verify user authorization for write
    const isAuthorized = await this.accessControl.checkWriteAccess(
      userId,
      patientId,
      dataType
    );

    if (!isAuthorized) {
      throw new UnauthorizedError(
        'Not authorized to write this PHI'
      );
    }

    // Encrypt PHI before storage
    const encryptedData = await this.encryptionService.encrypt(
      data
    );

    // Store with audit trail
    await this.storeEncryptedPHI(
      patientId,
      dataType,
      encryptedData
    );

    // Log storage
    await this.auditLogger.log({
      action: 'phi_stored',
      userId,
      patientId,
      dataType,
      timestamp: new Date()
    });
  }

  async deletePHI(
    patientId: string,
    dataType: string,
    userId: string,
    reason: string
  ): Promise<void> {
    // Check if deletion is allowed
    const retentionPolicy = await this.getRetentionPolicy(
      dataType
    );

    if (retentionPolicy.minimumRetention > 0) {
      throw new Error(
        'PHI cannot be deleted due to retention policy'
      );
    }

    // Soft delete with audit trail
    await this.softDeletePHI(
      patientId,
      dataType,
      userId,
      reason
    );

    // Log deletion
    await this.auditLogger.log({
      action: 'phi_deleted',
      userId,
      patientId,
      dataType,
      reason,
      timestamp: new Date()
    });
  }

  async auditAccess(
    startDate: Date,
    endDate: Date,
    patientId?: string
  ): Promise<AuditReport> {
    const logs = await this.auditLogger.getLogs({
      startDate,
      endDate,
      patientId,
      action: 'phi_accessed'
    });

    return {
      period: { startDate, endDate },
      totalAccesses: logs.length,
      uniqueUsers: new Set(logs.map(l => l.userId)).size,
      accessByType: this.groupByDataType(logs),
      accessByPurpose: this.groupByPurpose(logs),
      suspiciousActivity: this.detectSuspiciousActivity(logs)
    };
  }

  private async retrieveEncryptedPHI(
    patientId: string,
    dataType: string
  ): Promise<EncryptedData> {
    // Implementation depends on storage backend
    return {} as EncryptedData;
  }

  private async storeEncryptedPHI(
    patientId: string,
    dataType: string,
    data: EncryptedData
  ): Promise<void> {
    // Implementation depends on storage backend
  }

  private async softDeletePHI(
    patientId: string,
    dataType: string,
    userId: string,
    reason: string
  ): Promise<void> {
    // Mark as deleted, don't physically remove
  }

  private async getRetentionPolicy(
    dataType: string
  ): Promise<RetentionPolicy> {
    return {
      minimumRetention: 365 * 6, // 6 years minimum
      maximumRetention: 365 * 10
    };
  }

  private groupByDataType(
    logs: AuditLog[]
  ): Record<string, number> {
    const grouped: Record<string, number> = {};
    logs.forEach(log => {
      grouped[log.dataType] = (grouped[log.dataType] || 0) + 1;
    });
    return grouped;
  }

  private groupByPurpose(
    logs: AuditLog[]
  ): Record<string, number> {
    const grouped: Record<string, number> = {};
    logs.forEach(log => {
      grouped[log.purpose] = (grouped[log.purpose] || 0) + 1;
    });
    return grouped;
  }

  private detectSuspiciousActivity(
    logs: AuditLog[]
  ): SuspiciousActivity[] {
    const suspicious: SuspiciousActivity[] = [];

    // Detect unusual access patterns
    const userAccessCounts = new Map<string, number>();
    logs.forEach(log => {
      const count = userAccessCounts.get(log.userId) || 0;
      userAccessCounts.set(log.userId, count + 1);
    });

    // Flag users with excessive access
    const averageAccess =
      logs.length / userAccessCounts.size;

    userAccessCounts.forEach((count, userId) => {
      if (count > averageAccess * 3) {
        suspicious.push({
          userId,
          reason: 'Excessive PHI access',
          count,
          averageCount: averageAccess
        });
      }
    });

    return suspicious;
  }
}

// HIPAA Security Headers
class HIPAASecurityHeaders {
  static getHeaders(): Record<string, string> {
    return {
      'Strict-Transport-Security':
        'max-age=31536000; includeSubDomains; preload',
      'Content-Security-Policy':
        "default-src 'self'; " +
        "script-src 'self'; " +
        "style-src 'self'; " +
        "img-src 'self' data:; " +
        "connect-src 'self'; " +
        "frame-ancestors 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'",
      'X-Frame-Options': 'DENY',
      'X-Content-Type-Options': 'nosniff',
      'X-XSS-Protection': '1; mode=block',
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache'
    };
  }
}
```

### 6.4 HIPAA Compliance Checklist

```yaml
# HIPAA Compliance Checklist for Web Applications
hipaa_checklist:
  administrative:
    - assigned_security_responsibility
    - workforce_security
    - information_access_management
    - security_awareness_training
    - security_incident_procedures
    - contingency_plan
    - evaluation

  physical:
    - facility_access_controls
    - workstation_use
    - workstation_security
    - device_media_controls

  technical:
    - access_control:
        - unique_user_identification
        - emergency_access_procedure
        - automatic_logoff
        - encryption_decryption
    - audit_controls:
        - audit_logging
        - audit_log_review
        - audit_log_retention
    - integrity:
        - data_integrity_verification
        - authentication
    - transmission_security:
        - encryption_in_transit
        - integrity_controls
```

---

## 7. SOC 2 para SaaS Web

### 7.1 Visao Geral

SOC 2 (Service Organization Control 2) e um framework de auditoria para organizacoes que fornecem servicos baseados em cloud. E baseado nos Cinco Criterios de Controle de Servico (Trust Services Criteria).

### 7.2 Criterios de Confianca

**Seguranca (Security)**
- Firewall e seguranca de rede
- Controles de acesso logico
- Deteccao e prevencao de intrusao
- Gerenciamento de mudancas

**Disponibilidade (Availability)**
- Monitoramento de performance
- Planos de contingencia
- Analise de risco
- Gestao de incidentes

**Integridade de Processamento (Processing Integrity)**
- Validacao de processamento
- Monitoramento de erros
- Controles de qualidade
- Gerenciamento de dados

**Confidencialidade (Confidentiality)**
- Criptografia de dados sensiveis
- Controles de acesso
- Monitoramento de acesso
- Politica de retencao

**Privacidade (Privacy)**
- Coleta de dados conforme necessario
- Consentimento do titular
- Direitos do titular dos dados
- Transferencia internacional

### 7.3 Implementacao SOC 2

```typescript
// SOC 2 Compliance Implementation
interface SOC2Config {
  // Security Controls
  security: {
    firewall: boolean;
    intrusionDetection: boolean;
    accessControl: {
      mfa: boolean;
      roleBasedAccess: boolean;
      leastPrivilege: boolean;
    };
    changeManagement: {
      approvalRequired: boolean;
      testingRequired: boolean;
      rollbackPlan: boolean;
    };
  };

  // Availability Controls
  availability: {
    uptimeSLA: number;              // percentage
    monitoringInterval: number;     // minutes
    backupFrequency: number;        // hours
    recoveryTimeObjective: number;  // minutes
    recoveryPointObjective: number; // minutes
  };

  // Processing Integrity Controls
  processingIntegrity: {
    inputValidation: boolean;
    errorHandling: boolean;
    qualityAssurance: boolean;
    dataValidation: boolean;
  };

  // Confidentiality Controls
  confidentiality: {
    encryptionAtRest: boolean;
    encryptionInTransit: boolean;
    accessLogging: boolean;
    dataClassification: boolean;
  };

  // Privacy Controls
  privacy: {
    dataMinimization: boolean;
    consentManagement: boolean;
    dataSubjectRights: boolean;
    crossBorderTransfers: boolean;
  };
}

class SOC2ComplianceManager {
  private config: SOC2Config;
  private auditLogger: AuditLogger;
  private metricsCollector: MetricsCollector;

  constructor(config: SOC2Config) {
    this.config = config;
    this.auditLogger = new AuditLogger();
    this.metricsCollector = new MetricsCollector();
  }

  // Security Controls
  async monitorAccess(
    userId: string,
    resource: string,
    action: string
  ): Promise<void> {
    // Log access attempt
    await this.auditLogger.log({
      category: 'security',
      userId,
      resource,
      action,
      timestamp: new Date(),
      success: true
    });

    // Check for suspicious activity
    const suspicious = await this.detectSuspiciousActivity(userId);
    if (suspicious) {
      await this.alertSecurityTeam(userId, suspicious);
    }
  }

  async manageChange(
    change: ChangeRequest,
    approver: string
  ): Promise<void> {
    // Verify approval process
    if (this.config.security.changeManagement.approvalRequired) {
      if (!change.approved) {
        throw new Error('Change not approved');
      }
    }

    // Log change
    await this.auditLogger.log({
      category: 'change_management',
      changeId: change.id,
      description: change.description,
      approver,
      timestamp: new Date()
    });

    // Execute change with rollback plan
    try {
      await this.executeChange(change);
    } catch (error) {
      if (this.config.security.changeManagement.rollbackPlan) {
        await this.rollbackChange(change);
      }
      throw error;
    }
  }

  // Availability Controls
  async monitorAvailability(): Promise<AvailabilityReport> {
    const metrics = await this.metricsCollector.getMetrics();

    return {
      uptime: metrics.uptime,
      responseTime: metrics.avgResponseTime,
      errorRate: metrics.errorRate,
      incidents: metrics.incidents,
      compliance: metrics.uptime >=
        this.config.availability.uptimeSLA / 100
    };
  }

  async createBackup(): Promise<BackupResult> {
    const backup = await this.performBackup();

    await this.auditLogger.log({
      category: 'availability',
      action: 'backup_created',
      backupId: backup.id,
      timestamp: new Date()
    });

    return backup;
  }

  async testRecovery(): Promise<RecoveryTestResult> {
    const startTime = Date.now();

    // Simulate disaster recovery
    await this.simulateRecovery();

    const recoveryTime = Date.now() - startTime;

    return {
      recoveryTime,
      rtoCompliant: recoveryTime <=
        this.config.availability.recoveryTimeObjective * 60 * 1000,
      dataIntegrity: await this.verifyDataIntegrity()
    };
  }

  // Processing Integrity Controls
  async validateProcessing(
    processData: ProcessData
  ): Promise<ValidationResult> {
    const errors: string[] = [];

    // Input validation
    if (this.config.processingIntegrity.inputValidation) {
      const inputErrors = this.validateInput(processData);
      errors.push(...inputErrors);
    }

    // Data validation
    if (this.config.processingIntegrity.dataValidation) {
      const dataErrors = this.validateData(processData);
      errors.push(...dataErrors);
    }

    return {
      isValid: errors.length === 0,
      errors,
      timestamp: new Date()
    };
  }

  // Confidentiality Controls
  async encryptSensitiveData(
    data: Record<string, unknown>
  ): Promise<EncryptedData> {
    const sensitiveFields = this.identifySensitiveFields(data);

    const encryptedData = { ...data };

    for (const field of sensitiveFields) {
      if (encryptedData[field]) {
        encryptedData[field] = await this.encrypt(
          encryptedData[field] as string
        );
      }
    }

    await this.auditLogger.log({
      category: 'confidentiality',
      action: 'data_encrypted',
      fields: sensitiveFields,
      timestamp: new Date()
    });

    return encryptedData as EncryptedData;
  }

  // Privacy Controls
  async handleDataSubjectRequest(
    request: DataSubjectRequest
  ): Promise<void> {
    // Log the request
    await this.auditLogger.log({
      category: 'privacy',
      action: 'data_subject_request',
      type: request.type,
      userId: request.userId,
      timestamp: new Date()
    });

    // Process based on request type
    switch (request.type) {
      case 'access':
        await this.provideDataAccess(request.userId);
        break;
      case 'deletion':
        await this.deleteUserData(request.userId);
        break;
      case 'portability':
        await this.exportUserData(request.userId);
        break;
      case 'rectification':
        await this.rectifyUserData(
          request.userId,
          request.corrections
        );
        break;
    }
  }

  private async detectSuspiciousActivity(
    userId: string
  ): Promise<boolean> {
    // Implement suspicious activity detection
    return false;
  }

  private async alertSecurityTeam(
    userId: string,
    reason: string
  ): Promise<void> {
    // Implement security alerting
  }

  private async executeChange(
    change: ChangeRequest
  ): Promise<void> {
    // Implement change execution
  }

  private async rollbackChange(
    change: ChangeRequest
  ): Promise<void> {
    // Implement rollback
  }

  private async performBackup(): Promise<BackupResult> {
    // Implement backup
    return {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      size: 0,
      encrypted: true
    };
  }

  private async simulateRecovery(): Promise<void> {
    // Simulate recovery process
  }

  private async verifyDataIntegrity(): Promise<boolean> {
    // Verify data integrity after recovery
    return true;
  }

  private validateInput(data: ProcessData): string[] {
    // Implement input validation
    return [];
  }

  private validateData(data: ProcessData): string[] {
    // Implement data validation
    return [];
  }

  private identifySensitiveFields(
    data: Record<string, unknown>
  ): string[] {
    const sensitivePatterns = [
      'password', 'ssn', 'credit_card', 'health',
      'financial', 'personal'
    ];

    return Object.keys(data).filter(key =>
      sensitivePatterns.some(pattern =>
        key.toLowerCase().includes(pattern)
      )
    );
  }

  private async encrypt(data: string): Promise<string> {
    // Implement encryption
    return data;
  }

  private async provideDataAccess(userId: string): Promise<void> {
    // Provide data access to user
  }

  private async deleteUserData(userId: string): Promise<void> {
    // Delete user data
  }

  private async exportUserData(userId: string): Promise<void> {
    // Export user data
  }

  private async rectifyUserData(
    userId: string,
    corrections: Record<string, unknown>
  ): Promise<void> {
    // Rectify user data
  }
}
```

---

## 8. ISO 27001 para Seguranca de Aplicacoes Web

### 8.1 Visao Geral

ISO 27001 e um padrao internacional para sistemas de gestao de seguranca da informacao (ISMS). Fornece framework para estabelecer, implementar, manter e melhorar continuamente um ISMS.

### 8.2 Controles do Anexo A

**Organizacionais (A.5-A.8)**
- Politicas de seguranca da informacao
- Organizacao da seguranca
- Controle de ativos
- Seguranca de recursos humanos

**Fisicos (A.9)**
- Seguranca de areas seguras
- Controles de entrada
- Seguranca de escritorios, salas e instalacoes
- Seguranca de equipamentos
- Controle de midia removivel

**Tecnicos (A.10-A.12)**
- Controles de acesso
- Criptografia
- Seguranca fisica e ambiental
- Seguranca de operacoes
- Seguranca de comunicacoes
- Aquisicao, desenvolvimento e manutencao de sistemas

### 8.3 Implementacao ISO 27001

```typescript
// ISO 27001 ISMS Implementation
interface ISMSConfig {
  // A.5: Information Security Policies
  policies: {
    informationSecurityPolicy: boolean;
    reviewFrequency: number;          // days
    managementApproval: boolean;
  };

  // A.6: Organization of Information Security
  organization: {
    securityRoles: SecurityRole[];
    segregationOfDuties: boolean;
    contactWithAuthorities: boolean;
  };

  // A.7: Human Resource Security
  humanResources: {
    backgroundVerification: boolean;
    termsOfEmployment: boolean;
    securityAwareness: boolean;
    disciplinaryProcess: boolean;
  };

  // A.8: Asset Management
  assetManagement: {
    assetInventory: boolean;
    assetClassification: boolean;
    mediaHandling: boolean;
  };

  // A.9: Access Control
  accessControl: {
    accessPolicy: boolean;
    userAccessManagement: boolean;
    systemAccessControl: boolean;
    mobileDeviceSecurity: boolean;
  };

  // A.10: Cryptography
  cryptography: {
    encryptionPolicy: boolean;
    keyManagement: boolean;
  };

  // A.11: Physical and Environmental Security
  physicalSecurity: {
    secureAreas: boolean;
    equipmentSecurity: boolean;
  };

  // A.12: Operations Security
  operationsSecurity: {
    operationalProcedures: boolean;
    protectionFromMalware: boolean;
    backup: boolean;
    loggingAndMonitoring: boolean;
    vulnerabilityManagement: boolean;
    technicalVulnerabilityManagement: boolean;
  };

  // A.13: Communications Security
  communicationsSecurity: {
    networkSecurity: boolean;
    informationTransfer: boolean;
  };

  // A.14: System Acquisition, Development and Maintenance
  systemDevelopment: {
    securityRequirements: boolean;
    secureDevelopment: boolean;
    testData: boolean;
  };

  // A.15: Supplier Relationships
  supplierRelationships: {
    securityInSupplierAgreements: boolean;
    supplierServiceDelivery: boolean;
  };

  // A.16: Information Security Incident Management
  incidentManagement: {
    incidentResponsePlan: boolean;
    reporting: boolean;
    learningFromIncidents: boolean;
  };

  // A.17: Information Security Aspects of Business Continuity
  businessContinuity: {
    continuityPlanning: boolean;
    testing: boolean;
  };

  // A.18: Compliance
  compliance: {
    complianceWithLegalRequirements: boolean;
    securityReviews: boolean;
  };
}

class ISO27001Manager {
  private config: ISMSConfig;
  private auditLogger: AuditLogger;
  private documentManager: DocumentManager;

  constructor(config: ISMSConfig) {
    this.config = config;
    this.auditLogger = new AuditLogger();
    this.documentManager = new DocumentManager();
  }

  // A.5: Information Security Policies
  async createSecurityPolicy(
    policy: SecurityPolicy
  ): Promise<void> {
    // Verify management approval
    if (this.config.policies.managementApproval) {
      if (!policy.approvedBy) {
        throw new Error('Policy requires management approval');
      }
    }

    // Store policy
    await this.documentManager.storePolicy(policy);

    // Log creation
    await this.auditLogger.log({
      control: 'A.5',
      action: 'policy_created',
      policyId: policy.id,
      timestamp: new Date()
    });
  }

  async reviewSecurityPolicy(): Promise<void> {
    const policies = await this.documentManager.getPolicies();

    for (const policy of policies) {
      const daysSinceLastReview =
        (Date.now() - policy.lastReviewed.getTime()) /
        (1000 * 60 * 60 * 24);

      if (daysSinceLastReview > this.config.policies.reviewFrequency) {
        await this.documentManager.flagForReview(policy.id);

        await this.auditLogger.log({
          control: 'A.5',
          action: 'policy_review_required',
          policyId: policy.id,
          daysSinceLastReview,
          timestamp: new Date()
        });
      }
    }
  }

  // A.6: Organization of Information Security
  async assignSecurityRoles(): Promise<void> {
    for (const role of this.config.organization.securityRoles) {
      await this.documentManager.assignRole(role);

      await this.auditLogger.log({
        control: 'A.6',
        action: 'role_assigned',
        role: role.name,
        assignee: role.assignee,
        timestamp: new Date()
      });
    }
  }

  // A.8: Asset Management
  async inventoryAssets(): Promise<AssetInventory> {
    const assets = await this.scanForAssets();

    const inventory: AssetInventory = {
      totalAssets: assets.length,
      categorized: this.categorizeAssets(assets),
      lastUpdated: new Date()
    };

    await this.documentManager.storeInventory(inventory);

    return inventory;
  }

  // A.9: Access Control
  async manageUserAccess(
    userId: string,
    action: 'grant' | 'revoke' | 'modify',
    permissions: Permission[]
  ): Promise<void> {
    // Verify access request is authorized
    const isAuthorized = await this.verifyAccessAuthorization(
      userId,
      action
    );

    if (!isAuthorized) {
      throw new Error('Unauthorized access request');
    }

    // Execute access change
    await this.updateAccessControl(userId, action, permissions);

    // Log the change
    await this.auditLogger.log({
      control: 'A.9',
      action: `access_${action}`,
      userId,
      permissions,
      timestamp: new Date()
    });
  }

  // A.10: Cryptography
  async manageEncryptionKeys(): Promise<void> {
    if (!this.config.cryptography.keyManagement) {
      return;
    }

    const keys = await this.getEncryptionKeys();

    for (const key of keys) {
      // Check key rotation
      const daysSinceCreation =
        (Date.now() - key.createdAt.getTime()) /
        (1000 * 60 * 60 * 24);

      if (daysSinceCreation > 365) {
        await this.rotateKey(key.id);

        await this.auditLogger.log({
          control: 'A.10',
          action: 'key_rotated',
          keyId: key.id,
          timestamp: new Date()
        });
      }
    }
  }

  // A.12: Operations Security
  async monitorOperations(): Promise<OperationsReport> {
    const report: OperationsReport = {
      malwareProtection: await this.checkMalwareProtection(),
      backupStatus: await this.checkBackupStatus(),
      loggingStatus: await this.checkLoggingStatus(),
      vulnerabilityStatus: await this.checkVulnerabilityStatus(),
      timestamp: new Date()
    };

    return report;
  }

  // A.16: Incident Management
  async handleIncident(
    incident: SecurityIncident
  ): Promise<void> {
    // Log incident
    await this.auditLogger.log({
      control: 'A.16',
      action: 'incident_reported',
      incidentId: incident.id,
      severity: incident.severity,
      timestamp: new Date()
    });

    // Execute response plan
    await this.executeIncidentResponse(incident);

    // Document lessons learned
    if (this.config.incidentManagement.learningFromIncidents) {
      await this.documentLessonsLearned(incident);
    }
  }

  // A.18: Compliance
  async verifyCompliance(): Promise<ComplianceReport> {
    const checks = await this.runComplianceChecks();

    return {
      controlsChecked: checks.length,
      controlsCompliant: checks.filter(c => c.compliant).length,
      controlsNonCompliant: checks.filter(c => !c.compliant).length,
      nonCompliantControls: checks
        .filter(c => !c.compliant)
        .map(c => c.control),
      timestamp: new Date()
    };
  }

  private async scanForAssets(): Promise<Asset[]> {
    // Implement asset scanning
    return [];
  }

  private categorizeAssets(assets: Asset[]): Record<string, number> {
    const categories: Record<string, number> = {};
    assets.forEach(asset => {
      categories[asset.category] =
        (categories[asset.category] || 0) + 1;
    });
    return categories;
  }

  private async verifyAccessAuthorization(
    userId: string,
    action: string
  ): Promise<boolean> {
    // Implement authorization check
    return true;
  }

  private async updateAccessControl(
    userId: string,
    action: string,
    permissions: Permission[]
  ): Promise<void> {
    // Implement access control update
  }

  private async getEncryptionKeys(): Promise<EncryptionKey[]> {
    // Implement key retrieval
    return [];
  }

  private async rotateKey(keyId: string): Promise<void> {
    // Implement key rotation
  }

  private async checkMalwareProtection(): Promise<boolean> {
    // Implement malware protection check
    return true;
  }

  private async checkBackupStatus(): Promise<boolean> {
    // Implement backup status check
    return true;
  }

  private async checkLoggingStatus(): Promise<boolean> {
    // Implement logging status check
    return true;
  }

  private async checkVulnerabilityStatus(): Promise<boolean> {
    // Implement vulnerability status check
    return true;
  }

  private async executeIncidentResponse(
    incident: SecurityIncident
  ): Promise<void> {
    // Implement incident response
  }

  private async documentLessonsLearned(
    incident: SecurityIncident
  ): Promise<void> {
    // Implement lessons learned documentation
  }

  private async runComplianceChecks(): Promise<ComplianceCheck[]> {
    // Implement compliance checks
    return [];
  }
}
```

---

## 9. CIS Benchmarks para Web Servers

### 9.1 Visao Geral

CIS (Center for Internet Security) Benchmarks sao guias de configuracao segura para varios sistemas e aplicacoes. Para web servers, CIS Benchmarks cobrem:

- Apache HTTP Server
- Nginx
- Microsoft IIS
- Tomcat

### 9.2 CIS Benchmark para Nginx

```nginx
# CIS Benchmark for Nginx - Hardened Configuration

# Run as non-privileged user
user nginx nginx;

# Limit worker processes
worker_processes auto;
worker_rlimit_nofile 65535;

# Error log location and level
error_log /var/log/nginx/error.log warn;

# PID file location
pid /run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

http {
    # Basic settings
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time';

    access_log /var/log/nginx/access.log main;

    # Performance settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript
               application/xml application/rss+xml
               application/atom+xml image/svg+xml;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin"
                               always;
    add_header Content-Security-Policy
               "default-src 'self'; script-src 'self'; "
               "style-src 'self'; img-src 'self' data:; "
               "font-src 'self'; connect-src 'self'; "
               "frame-ancestors 'none'; base-uri 'self'; "
               "form-action 'self'" always;
    add_header Strict-Transport-Security
               "max-age=31536000; includeSubDomains; preload"
               always;

    # SSL/TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m
                   rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m
                   rate=5r/m;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Client settings
    client_body_buffer_size 10K;
    client_header_buffer_size 1k;
    client_max_body_size 10m;
    large_client_header_buffers 2 1k;

    # Hide server information
    server_tokens off;

    # Virtual hosts
    include /etc/nginx/conf.d/*.conf;
}

# Main server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    root /var/www/html;
    index index.html index.htm;

    # Security headers (redundant but explicit)
    add_header Strict-Transport-Security
               "max-age=31536000; includeSubDomains; preload"
               always;

    # Rate limiting
    limit_req zone=general burst=20 nodelay;
    limit_conn addr 100;

    # Location blocks
    location / {
        try_files $uri $uri/ =404;
    }

    location /api {
        limit_req zone=api burst=10 nodelay;

        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /login {
        limit_req zone=login burst=5 nodelay;

        proxy_pass http://backend;
    }

    # Block sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~* \.(engine|inc|install|make|module|profile|po|sh|.*sql|theme|twig|tpl(\.php)?|xtmpl|yml)(~|\.sw[op]|\.bak|\.orig|\.save)?$|^(\.(?!well-known).*|Entries.*|Repository|Root|Tag|Template|composer\.json|license\.txt)$ {
        deny all;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name example.com;

    return 301 https://$server_name$request_uri;
}
```

### 9.3 CIS Benchmark para Apache

```apache
# CIS Benchmark for Apache HTTP Server

# Run as non-privileged user
User apache
Group apache

# Server information
ServerTokens Prod
ServerSignature Off

# Security headers
Header always set Strict-Transport-Security
                "max-age=31536000; includeSubDomains; preload"
Header always set X-Frame-Options "DENY"
Header always set X-Content-Type-Options "nosniff"
Header always set X-XSS-Protection "1; mode=block"
Header always set Referrer-Policy
                "strict-origin-when-cross-origin"
Header always set Content-Security-Policy
                "default-src 'self'; script-src 'self'; "
                "style-src 'self'; img-src 'self' data:; "
                "font-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'self'; "
                "form-action 'self'"

# SSL/TLS Configuration
SSLProtocol -all +TLSv1.2 +TLSv1.3
SSLCipherSuite ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305
SSLHonorCipherOrder on
SSLCompression off
SSLSessionTickets off

# OCSP Stapling
SSLUseStapling On
SSLStaplingCache "shmcb:logs/ssl_stapling(32768)"

# Security Modules
LoadModule security2_module modules/mod_security2.so
LoadModule reqtimeout_module modules/mod_reqtimeout.so
LoadModule headers_module modules/mod_headers.so

# ModSecurity Configuration
<IfModule mod_security2.c>
    SecRuleEngine On
    SecRequestBodyAccess On
    SecResponseBodyAccess Off
    SecPcreMatchLimit 100000
    SecPcreMatchLimitRecursion 100000

    SecTmpDir /tmp/
    SecDataDir /tmp/

    SecRule REQUEST_URI \
        "@streq /admin" \
        "id:1001,phase:1,deny,status:403"
</IfModule>

# Request Limits
LimitRequestFields 100
LimitRequestFieldSize 8190
LimitRequestLine 8190
LimitRequestBody 10485760

# Directory Configuration
<Directory />
    Options None
    AllowOverride None
    Require all denied
</Directory>

<Directory /var/www/html>
    Options -Indexes -FollowSymLinks
    AllowOverride None
    Require all granted
</Directory>

# Block sensitive files
<FilesMatch "^\.">
    Require all denied
</FilesMatch>

<FilesMatch "\.(bak|config|dist|fla|inc|ini|log|psd|sh|sql|sw[op])$">
    Require all denied
</FilesMatch>

# Error pages
ErrorDocument 400 /errors/400.html
ErrorDocument 401 /errors/401.html
ErrorDocument 403 /errors/403.html
ErrorDocument 404 /errors/404.html
ErrorDocument 500 /errors/500.html

# Logging
LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"" combined
CustomLog /var/log/httpd/access.log combined
ErrorLog /var/log/httpd/error.log

# Timeout Settings
Timeout 60
KeepAliveTimeout 5
MaxKeepAliveRequests 100
```

### 9.4 CIS Benchmark Validation Scripts

```bash
#!/bin/bash
# CIS Benchmark Validation Script for Web Servers

set -euo pipefail

LOG_FILE="/var/log/cis-benchmark-$(date +%Y%m%d).log"
REPORT_FILE="/var/log/cis-report-$(date +%Y%m%d).json"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_nginx_cis() {
    log "Checking Nginx CIS Benchmark..."

    local checks=0
    local passed=0

    # 2.1.1: Ensure permissions on nginx.conf
    if [ "$(stat -c %a /etc/nginx/nginx.conf)" = "644" ]; then
        log "PASS: nginx.conf permissions"
        ((passed++))
    else
        log "FAIL: nginx.conf permissions"
    fi
    ((checks++))

    # 2.1.2: Ensure ownership of nginx.conf
    if [ "$(stat -c %U:%G /etc/nginx/nginx.conf)" = "root:root" ]; then
        log "PASS: nginx.conf ownership"
        ((passed++))
    else
        log "FAIL: nginx.conf ownership"
    fi
    ((checks++))

    # 2.2.1: Ensure server_tokens is off
    if grep -q "server_tokens off" /etc/nginx/nginx.conf; then
        log "PASS: server_tokens off"
        ((passed++))
    else
        log "FAIL: server_tokens not off"
    fi
    ((checks++))

    # 2.2.2: Ensure SSL protocols are correct
    if grep -q "ssl_protocols TLSv1.2 TLSv1.3" /etc/nginx/nginx.conf; then
        log "PASS: SSL protocols correct"
        ((passed++))
    else
        log "FAIL: SSL protocols incorrect"
    fi
    ((checks++))

    # 2.2.3: Ensure SSL ciphers are strong
    if grep -q "ssl_ciphers" /etc/nginx/nginx.conf; then
        log "PASS: SSL ciphers configured"
        ((passed++))
    else
        log "FAIL: SSL ciphers not configured"
    fi
    ((checks++))

    # 2.2.4: Ensure HSTS is enabled
    if grep -q "Strict-Transport-Security" /etc/nginx/nginx.conf; then
        log "PASS: HSTS enabled"
        ((passed++))
    else
        log "FAIL: HSTS not enabled"
    fi
    ((checks++))

    # 2.2.5: Ensure X-Frame-Options is set
    if grep -q "X-Frame-Options" /etc/nginx/nginx.conf; then
        log "PASS: X-Frame-Options set"
        ((passed++))
    else
        log "FAIL: X-Frame-Options not set"
    fi
    ((checks++))

    # Generate report
    cat > "$REPORT_FILE" << EOF
{
    "benchmark": "CIS Nginx",
    "timestamp": "$(date -Iseconds)",
    "total_checks": $checks,
    "passed": $passed,
    "failed": $((checks - passed)),
    "score": $(echo "scale=2; $passed * 100 / $checks" | bc)
}
EOF

    log "CIS Benchmark check complete: $passed/$checks passed"
}

check_apache_cis() {
    log "Checking Apache CIS Benchmark..."

    local checks=0
    local passed=0

    # 1.1.1: Ensure Apache is up to date
    if apache2 -v | grep -q "Apache/2.4"; then
        log "PASS: Apache version"
        ((passed++))
    else
        log "FAIL: Apache version outdated"
    fi
    ((checks++))

    # 2.1.1: Ensure ServerTokens is Prod
    if grep -q "ServerTokens Prod" /etc/apache2/apache2.conf; then
        log "PASS: ServerTokens Prod"
        ((passed++))
    else
        log "FAIL: ServerTokens not Prod"
    fi
    ((checks++))

    # 2.1.2: Ensure ServerSignature is Off
    if grep -q "ServerSignature Off" /etc/apache2/apache2.conf; then
        log "PASS: ServerSignature Off"
        ((passed++))
    else
        log "FAIL: ServerSignature not Off"
    fi
    ((checks++))

    # 2.2.1: Ensure SSLProtocol is correct
    if grep -q "SSLProtocol -all +TLSv1.2" /etc/apache2/apache2.conf; then
        log "PASS: SSLProtocol correct"
        ((passed++))
    else
        log "FAIL: SSLProtocol incorrect"
    fi
    ((checks++))

    # Generate report
    cat > "$REPORT_FILE" << EOF
{
    "benchmark": "CIS Apache",
    "timestamp": "$(date -Iseconds)",
    "total_checks": $checks,
    "passed": $passed,
    "failed": $((checks - passed)),
    "score": $(echo "scale=2; $passed * 100 / $checks" | bc)
}
EOF

    log "CIS Benchmark check complete: $passed/$checks passed"
}

main() {
    log "Starting CIS Benchmark validation..."

    if command -v nginx &> /dev/null; then
        check_nginx_cis
    fi

    if command -v apache2 &> /dev/null; then
        check_apache_cis
    fi

    log "CIS Benchmark validation complete"
}

main "$@"
```

---

## 10. Anti-Patterns em Seguranca Web

### 10.1 Lista de Anti-Patterns

1. **Hardcoding de credenciais**
2. **Uso de criptografia fraca**
3. **Falta de validacao de entrada**
4. **Exposicao de informacoes detalhadas de erro**
5. **Uso de default credentials**
6. **Falta de rate limiting**
7. **Uso de HTTP sem HTTPS**
8. **Armazenamento de senhas em texto plano**
9. **Falta de headers de seguranca**
10. **Uso de bibliotecas desatualizadas**
11. **Falta de audit logging**
12. **Uso de sessoes fixas**
13. **Falta de CSRF protection**
14. **Uso de eval() com input do usuario**
15. **Falta de Content Security Policy**
16. **Exposicao de metadados sensiveis**
17. **Falta de input sanitization**
18. **Uso de SQL queries dinamicas**
19. **Falta de HTTPS enforcement**
20. **Uso de cookies sem HttpOnly/Secure**
21. **Falta de timeout de sessao**
22. **Uso de tokens sem expiracao**
23. **Falta de audit trail**
24. **Uso de algoritmos de hash fracos**
25. **Falta de segregation of duties**

### 10.2 Codigo de Anti-Patterns

```typescript
// ANTI-PATTERN 1: Hardcoded Credentials
// NEVER DO THIS
const DB_PASSWORD = "admin123";
const API_KEY = "sk_live_abc123def456";

// CORRECT: Use environment variables
const DB_PASSWORD = process.env.DB_PASSWORD;
const API_KEY = process.env.API_KEY;


// ANTI-PATTERN 2: Weak Encryption
// NEVER DO THIS
const hash = crypto.createHash('md5').update(password).digest('hex');

// CORRECT: Use strong algorithms
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(password, 12);


// ANTI-PATTERN 3: SQL Injection
// NEVER DO THIS
const query = `SELECT * FROM users WHERE id = ${userId}`;
const result = await db.query(query);

// CORRECT: Use parameterized queries
const query = 'SELECT * FROM users WHERE id = $1';
const result = await db.query(query, [userId]);


// ANTI-PATTERN 4: No Input Validation
// NEVER DO THIS
app.post('/api/user', (req, res) => {
  const { name, email } = req.body;
  // No validation, direct use
  db.createUser({ name, email });
});

// CORRECT: Validate all input
app.post('/api/user', (req, res) => {
  const { name, email } = req.body;

  if (!name || typeof name !== 'string') {
    return res.status(400).json({ error: 'Invalid name' });
  }

  if (!email || !isValidEmail(email)) {
    return res.status(400).json({ error: 'Invalid email' });
  }

  db.createUser({ name: sanitize(name), email: sanitize(email) });
});


// ANTI-PATTERN 5: Detailed Error Messages
// NEVER DO THIS
app.use((err, req, res, next) => {
  res.status(500).json({
    error: err.message,
    stack: err.stack,
    query: req.query,
    body: req.body
  });
});

// CORRECT: Generic error messages
app.use((err, req, res, next) => {
  console.error('Server error:', err);

  res.status(500).json({
    error: 'An unexpected error occurred'
  });
});


// ANTI-PATTERN 6: No Rate Limiting
// NEVER DO THIS
app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  const user = await authenticate(username, password);

  if (user) {
    res.json({ token: generateToken(user) });
  } else {
    res.status(401).json({ error: 'Invalid credentials' });
  }
});

// CORRECT: Implement rate limiting
const rateLimit = require('express-rate-limit');

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5,                    // 5 attempts
  message: 'Too many login attempts'
});

app.post('/api/login', loginLimiter, async (req, res) => {
  const { username, password } = req.body;
  const user = await authenticate(username, password);

  if (user) {
    res.json({ token: generateToken(user) });
  } else {
    res.status(401).json({ error: 'Invalid credentials' });
  }
});


// ANTI-PATTERN 7: HTTP without HTTPS
// NEVER DO THIS
const server = http.createServer(app);
server.listen(80);

// CORRECT: Always use HTTPS
const https = require('https');
const fs = require('fs');

const options = {
  key: fs.readFileSync('/path/to/key.pem'),
  cert: fs.readFileSync('/path/to/cert.pem')
};

const server = https.createServer(options, app);
server.listen(443);


// ANTI-PATTERN 8: Plaintext Password Storage
// NEVER DO THIS
async function createUser(username, password) {
  await db.query(
    'INSERT INTO users (username, password) VALUES ($1, $2)',
    [username, password]
  );
}

// CORRECT: Hash passwords before storage
async function createUser(username, password) {
  const hashedPassword = await bcrypt.hash(password, 12);
  await db.query(
    'INSERT INTO users (username, password) VALUES ($1, $2)',
    [username, hashedPassword]
  );
}


// ANTI-PATTERN 9: Missing Security Headers
// NEVER DO THIS
app.use((req, res, next) => {
  next();
});

// CORRECT: Add security headers
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Strict-Transport-Security',
    'max-age=31536000; includeSubDomains; preload');
  res.setHeader('Content-Security-Policy',
    "default-src 'self'");
  next();
});


// ANTI-PATTERN 10: Outdated Dependencies
// NEVER DO THIS
// Using old, vulnerable packages without updates

// CORRECT: Regularly update and audit dependencies
// package.json scripts:
// "audit": "npm audit",
// "update": "npm update",
// "check-updates": "npx npm-check-updates"


// ANTI-PATTERN 11: No Audit Logging
// NEVER DO THIS
app.post('/api/admin/delete-user', async (req, res) => {
  const { userId } = req.body;
  await db.deleteUser(userId);
  res.json({ success: true });
});

// CORRECT: Log all admin actions
app.post('/api/admin/delete-user', async (req, res) => {
  const { userId } = req.body;
  const adminId = req.user.id;

  await auditLogger.log({
    action: 'user_deletion',
    adminId,
    targetUserId: userId,
    timestamp: new Date(),
    ipAddress: req.ip
  });

  await db.deleteUser(userId);
  res.json({ success: true });
});


// ANTI-PATTERN 12: Fixed Sessions
// NEVER DO THIS
const session = {
  userId: '123',
  role: 'admin',
  createdAt: new Date('2020-01-01')
};

// CORRECT: Session management with timeout
const session = {
  id: crypto.randomBytes(32).toString('hex'),
  userId: '123',
  role: 'admin',
  createdAt: new Date(),
  lastAccessedAt: new Date(),
  ipAddress: req.ip,
  userAgent: req.headers['user-agent']
};


// ANTI-PATTERN 13: No CSRF Protection
// NEVER DO THIS
app.post('/api/transfer', async (req, res) => {
  const { amount, toAccount } = req.body;
  await transferMoney(req.user.id, toAccount, amount);
  res.json({ success: true });
});

// CORRECT: Implement CSRF tokens
const csrf = require('csurf');
const csrfProtection = csrf({ cookie: true });

app.post('/api/transfer', csrfProtection, async (req, res) => {
  const { amount, toAccount } = req.body;
  await transferMoney(req.user.id, toAccount, amount);
  res.json({ success: true });
});


// ANTI-PATTERN 14: eval() with User Input
// NEVER DO THIS
app.post('/api/execute', (req, res) => {
  const { code } = req.body;
  const result = eval(code); // DANGEROUS!
  res.json({ result });
});

// CORRECT: Never use eval with user input
// Use a safe evaluation library if needed


// ANTI-PATTERN 15: No CSP
// NEVER DO THIS
// Missing Content-Security-Policy header

// CORRECT: Implement strict CSP
app.use((req, res, next) => {
  res.setHeader('Content-Security-Policy',
    "default-src 'self'; " +
    "script-src 'self'; " +
    "style-src 'self'; " +
    "img-src 'self' data:; " +
    "font-src 'self'; " +
    "connect-src 'self'; " +
    "frame-ancestors 'none'; " +
    "base-uri 'self'; " +
    "form-action 'self'"
  );
  next();
});


// ANTI-PATTERN 16: Exposing Metadata
// NEVER DO THIS
app.get('/api/user/:id', async (req, res) => {
  const user = await db.getUser(req.params.id);
  res.json({
    ...user,
    password: user.password,  // NEVER expose password
    ssn: user.ssn,           // NEVER expose SSN
    creditCard: user.creditCard  // NEVER expose credit card
  });
});

// CORRECT: Exclude sensitive fields
app.get('/api/user/:id', async (req, res) => {
  const user = await db.getUser(req.params.id);
  const { password, ssn, creditCard, ...safeUser } = user;
  res.json(safeUser);
});


// ANTI-PATTERN 17: No Input Sanitization
// NEVER DO THIS
app.post('/api/comment', (req, res) => {
  const { comment } = req.body;
  db.saveComment(comment); // XSS vulnerability
});

// CORRECT: Sanitize all input
const DOMPurify = require('dompurify');
const { JSDOM } = require('jsdom');
const window = new JSDOM('').window;
const purify = DOMPurify(window);

app.post('/api/comment', (req, res) => {
  const { comment } = req.body;
  const sanitized = purify.sanitize(comment);
  db.saveComment(sanitized);
});


// ANTI-PATTERN 18: Dynamic SQL Queries
// NEVER DO THIS
function getUser(userId) {
  const query = "SELECT * FROM users WHERE id = '" + userId + "'";
  return db.query(query);
}

// CORRECT: Use parameterized queries
function getUser(userId) {
  return db.query(
    'SELECT * FROM users WHERE id = $1',
    [userId]
  );
}


// ANTI-PATTERN 19: No HTTPS Enforcement
// NEVER DO THIS
app.use((req, res, next) => {
  next(); // No redirect to HTTPS
});

// CORRECT: Force HTTPS
app.use((req, res, next) => {
  if (req.headers['x-forwarded-proto'] !== 'https') {
    return res.redirect(301, `https://${req.hostname}${req.url}`);
  }
  next();
});


// ANTI-PATTERN 20: Insecure Cookies
// NEVER DO THIS
res.cookie('session', sessionId);

// CORRECT: Secure cookie configuration
res.cookie('session', sessionId, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 24 * 60 * 60 * 1000 // 24 hours
});


// ANTI-PATTERN 21: No Session Timeout
// NEVER DO THIS
// Sessions never expire

// CORRECT: Implement session timeout
const session = {
  id: sessionId,
  createdAt: new Date(),
  lastAccessedAt: new Date(),
  timeout: 30 * 60 * 1000 // 30 minutes
};

function isSessionValid(session) {
  const now = Date.now();
  const lastAccess = session.lastAccessedAt.getTime();

  return (now - lastAccess) < session.timeout;
}


// ANTI-PATTERN 22: Tokens Without Expiration
// NEVER DO THIS
const token = jwt.sign({ userId: user.id }, SECRET_KEY);

// CORRECT: Tokens with expiration
const token = jwt.sign(
  { userId: user.id },
  SECRET_KEY,
  { expiresIn: '1h' }
);


// ANTI-PATTERN 23: No Audit Trail
// NEVER DO THIS
// No logging of important actions

// CORRECT: Comprehensive audit trail
async function auditAction(action, userId, details) {
  await auditLogger.log({
    action,
    userId,
    details,
    timestamp: new Date(),
    ipAddress: req.ip,
    userAgent: req.headers['user-agent']
  });
}


// ANTI-PATTERN 24: Weak Hash Algorithms
// NEVER DO THIS
const hash = crypto.createHash('md5').update(password).digest('hex');
const hash = crypto.createHash('sha1').update(password).digest('hex');

// CORRECT: Use strong algorithms
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(password, 12);

// Or for higher performance needs
const argon2 = require('argon2');
const hash = await argon2.hash(password, {
  type: argon2.argon2id,
  memoryCost: 65536,
  timeCost: 3,
  parallelism: 4
});


// ANTI-PATTERN 25: No Segregation of Duties
// NEVER DO THIS
// Same user can create, approve, and deploy

// CORRECT: Separate duties
const workflow = {
  creator: 'user1',
  approver: 'user2',
  deployer: 'user3'
};

async function deployChange(change, user) {
  if (user.id === change.creator) {
    throw new Error('Creator cannot approve own change');
  }

  if (user.id === change.approver) {
    throw new Error('Approver cannot deploy');
  }

  // Proceed with deployment
}
```

---

## 11. Security Checklist Completa

### 11.1 Checklist de Seguranca para Desenvolvimento Web

```yaml
# Security Checklist for Web Application Development
# Minimum 50 items

security_checklist:
  authentication:
    - id: AUTH-001
      description: "Multi-factor authentication available"
      priority: high
      frameworks: [ASVS, PCI DSS, HIPAA]

    - id: AUTH-002
      description: "Password policy enforced (min 12 chars)"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: AUTH-003
      description: "Account lockout after failed attempts"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: AUTH-004
      description: "Session timeout configured"
      priority: high
      frameworks: [ASVS, PCI DSS, HIPAA]

    - id: AUTH-005
      description: "Password recovery is secure"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: AUTH-006
      description: "Credentials stored with strong hashing"
      priority: critical
      frameworks: [ASVS, PCI DSS, HIPAA]

    - id: AUTH-007
      description: "JWT tokens have expiration"
      priority: high
      frameworks: [ASVS]

    - id: AUTH-008
      description: "Refresh tokens are rotated"
      priority: medium
      frameworks: [ASVS]

  authorization:
    - id: AUTHZ-001
      description: "Role-based access control implemented"
      priority: high
      frameworks: [ASVS, PCI DSS, HIPAA]

    - id: AUTHZ-002
      description: "Principle of least privilege applied"
      priority: high
      frameworks: [ASVS, PCI DSS, ISO 27001]

    - id: AUTHZ-003
      description: "Admin functions require authorization"
      priority: critical
      frameworks: [ASVS, PCI DSS]

    - id: AUTHZ-004
      description: "API endpoints have authorization checks"
      priority: high
      frameworks: [ASVS]

    - id: AUTHZ-005
      description: "File access is restricted"
      priority: high
      frameworks: [ASVS, PCI DSS]

  input_validation:
    - id: INPUT-001
      description: "All user input is validated"
      priority: critical
      frameworks: [ASVS, PCI DSS]

    - id: INPUT-002
      description: "SQL queries use parameterization"
      priority: critical
      frameworks: [ASVS, PCI DSS]

    - id: INPUT-003
      description: "XSS prevention implemented"
      priority: critical
      frameworks: [ASVS]

    - id: INPUT-004
      description: "File upload validation"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: INPUT-005
      description: "Input length limits enforced"
      priority: medium
      frameworks: [ASVS]

  output_encoding:
    - id: OUTPUT-001
      description: "HTML output is encoded"
      priority: high
      frameworks: [ASVS]

    - id: OUTPUT-002
      description: "JavaScript output is escaped"
      priority: high
      frameworks: [ASVS]

    - id: OUTPUT-003
      description: "URL parameters are encoded"
      priority: medium
      frameworks: [ASVS]

  cryptography:
    - id: CRYPTO-001
      description: "TLS 1.2+ enforced"
      priority: critical
      frameworks: [ASVS, PCI DSS, HIPAA]

    - id: CRYPTO-002
      description: "Strong cipher suites only"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: CRYPTO-003
      description: "Sensitive data encrypted at rest"
      priority: critical
      frameworks: [PCI DSS, HIPAA, LGPD]

    - id: CRYPTO-004
      description: "Encryption keys rotated regularly"
      priority: high
      frameworks: [PCI DSS, ISO 27001]

    - id: CRYPTO-005
      description: "No hardcoded secrets"
      priority: critical
      frameworks: [ASVS, PCI DSS]

  session_management:
    - id: SESSION-001
      description: "Session ID regenerated after login"
      priority: high
      frameworks: [ASVS]

    - id: SESSION-002
      description: "Session fixation prevented"
      priority: high
      frameworks: [ASVS]

    - id: SESSION-003
      description: "Concurrent session control"
      priority: medium
      frameworks: [ASVS]

    - id: SESSION-004
      description: "Session data not in URL"
      priority: medium
      frameworks: [ASVS]

  security_headers:
    - id: HEADER-001
      description: "Content-Security-Policy set"
      priority: high
      frameworks: [ASVS]

    - id: HEADER-002
      description: "X-Frame-Options set"
      priority: high
      frameworks: [ASVS]

    - id: HEADER-003
      description: "Strict-Transport-Security set"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: HEADER-004
      description: "X-Content-Type-Options set"
      priority: medium
      frameworks: [ASVS]

    - id: HEADER-005
      description: "X-XSS-Protection set"
      priority: medium
      frameworks: [ASVS]

  error_handling:
    - id: ERROR-001
      description: "Generic error messages in production"
      priority: high
      frameworks: [ASVS]

    - id: ERROR-002
      description: "No stack traces exposed"
      priority: high
      frameworks: [ASVS]

    - id: ERROR-003
      description: "Error logging implemented"
      priority: high
      frameworks: [ASVS, ISO 27001]

  logging_and_monitoring:
    - id: LOG-001
      description: "Security events logged"
      priority: critical
      frameworks: [ASVS, PCI DSS, ISO 27001]

    - id: LOG-002
      description: "Log integrity protected"
      priority: high
      frameworks: [PCI DSS, ISO 27001]

    - id: LOG-003
      description: "Real-time alerting configured"
      priority: high
      frameworks: [PCI DSS]

    - id: LOG-004
      description: "Log retention policy defined"
      priority: medium
      frameworks: [PCI DSS, ISO 27001]

  dependency_management:
    - id: DEP-001
      description: "Dependencies scanned for vulnerabilities"
      priority: high
      frameworks: [ASVS]

    - id: DEP-002
      description: "Outdated dependencies updated"
      priority: high
      frameworks: [ASVS]

    - id: DEP-003
      description: "Lock files committed"
      priority: medium
      frameworks: [ASVS]

  data_protection:
    - id: DATA-001
      description: "PII data identified and classified"
      priority: high
      frameworks: [LGPD, GDPR, HIPAA]

    - id: DATA-002
      description: "Data retention policy implemented"
      priority: high
      frameworks: [LGPD, GDPR]

    - id: DATA-003
      description: "Data subject rights supported"
      priority: high
      frameworks: [LGPD, GDPR]

    - id: DATA-004
      description: "Consent management implemented"
      priority: high
      frameworks: [LGPD, GDPR]

  infrastructure:
    - id: INFRA-001
      description: "Web server hardened per CIS Benchmark"
      priority: high
      frameworks: [CIS]

    - id: INFRA-002
      description: "Firewall configured"
      priority: high
      frameworks: [PCI DSS, ISO 27001]

    - id: INFRA-003
      description: "Intrusion detection enabled"
      priority: medium
      frameworks: [PCI DSS]

    - id: INFRA-004
      description: "Regular security scans scheduled"
      priority: high
      frameworks: [PCI DSS, ISO 27001]

  testing:
    - id: TEST-001
      description: "Unit tests for security functions"
      priority: high
      frameworks: [ASVS, OWASP SAMM]

    - id: TEST-002
      description: "Integration tests for auth flows"
      priority: high
      frameworks: [ASVS]

    - id: TEST-003
      description: "DAST scans in CI/CD"
      priority: high
      frameworks: [ASVS, PCI DSS]

    - id: TEST-004
      description: "Penetration testing annually"
      priority: high
      frameworks: [PCI DSS, ISO 27001]
```

### 11.2 Checklist de Verificacao

```typescript
// Security Checklist Verification System
interface ChecklistItem {
  id: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  frameworks: string[];
  implemented: boolean;
  evidence?: string;
  lastVerified?: Date;
  verifiedBy?: string;
}

interface ChecklistReport {
  totalItems: number;
  implemented: number;
  notImplemented: number;
  complianceScore: number;
  criticalGaps: ChecklistItem[];
  recommendations: string[];
}

class SecurityChecklistVerifier {
  private items: ChecklistItem[];

  constructor(items: ChecklistItem[]) {
    this.items = items;
  }

  async verifyImplementation(): Promise<ChecklistReport> {
    const implemented = this.items.filter(i => i.implemented);
    const notImplemented = this.items.filter(i => !i.implemented);

    const complianceScore =
      (implemented.length / this.items.length) * 100;

    const criticalGaps = notImplemented.filter(
      i => i.priority === 'critical'
    );

    return {
      totalItems: this.items.length,
      implemented: implemented.length,
      notImplemented: notImplemented.length,
      complianceScore,
      criticalGaps,
      recommendations: this.generateRecommendations(
        notImplemented
      )
    };
  }

  private generateRecommendations(
    gaps: ChecklistItem[]
  ): string[] {
    const recommendations: string[] = [];

    // Prioritize critical gaps
    const criticalGaps = gaps.filter(i => i.priority === 'critical');
    criticalGaps.forEach(gap => {
      recommendations.push(
        `URGENT: Implement ${gap.description}`
      );
    });

    // Add high priority gaps
    const highGaps = gaps.filter(i => i.priority === 'high');
    highGaps.slice(0, 5).forEach(gap => {
      recommendations.push(
        `HIGH: Implement ${gap.description}`
      );
    });

    return recommendations;
  }

  async generateFrameworkReport(
    framework: string
  ): Promise<FrameworkReport> {
    const frameworkItems = this.items.filter(
      i => i.frameworks.includes(framework)
    );

    const implemented = frameworkItems.filter(i => i.implemented);
    const score =
      (implemented.length / frameworkItems.length) * 100;

    return {
      framework,
      totalControls: frameworkItems.length,
      implementedControls: implemented.length,
      complianceScore: score,
      gaps: frameworkItems.filter(i => !i.implemented)
    };
  }
}
```

---

## 12. Decision Trees

### 12.1 Decision Tree: Framework Selection

```
START: Which framework to use?
|
+-- Do you process payments?
|  +-- Yes -> PCI DSS
|  +-- No |
|
+-- Do you handle health data (PHI)?
|  +-- Yes -> HIPAA
|  +-- No |
|
+-- Do you operate in EU/BR?
|  +-- Yes -> GDPR/LGPD
|  +-- No |
|
+-- Do you need SOC 2 certification?
|  +-- Yes -> SOC 2
|  +-- No |
|
+-- Do you need ISO 27001 certification?
|  +-- Yes -> ISO 27001
|  +-- No |
|
+-- Default: OWASP ASVS + OWASP SAMM
```

### 12.2 Decision Tree: Authentication Method

```
START: Which authentication method?
|
+-- Is MFA required?
|  +-- Yes |
|  |  +-- Is it a high-security app?
|  |  |  +-- Yes -> WebAuthn/FIDO2 + TOTP
|  |  |  +-- No -> TOTP + SMS backup
|  |  |
|  +-- No |
|
+-- What type of application?
|  +-- B2B SaaS -> OAuth 2.0 + OIDC
|  +-- B2C Web -> Password + Social Login
|  +-- Mobile API -> OAuth 2.0 + PKCE
|  +-- Internal Tool -> LDAP + MFA
|
+-- Consider:
   - User experience requirements
   - Security requirements
   - Compliance requirements
   - Integration needs
```

### 12.3 Decision Tree: Encryption

```
START: What to encrypt?
|
+-- Data at rest?
|  +-- Database -> AES-256-GCM
|  +-- Files -> AES-256-GCM
|  +-- Backups -> AES-256-GCM
|  +-- Key storage -> HSM or KMS
|
+-- Data in transit?
|  +-- External -> TLS 1.2+ (mandatory)
|  +-- Internal service-to-service -> mTLS
|  +-- WebSocket -> WSS (TLS)
|
+-- Passwords?
|  +-- Standard -> bcrypt (cost 12)
|  +-- High security -> argon2id
|  +-- Legacy support -> bcrypt + pepper
|
+-- API tokens?
|  +-- JWT -> RS256 or ES256
|  +-- Session tokens -> Random 32 bytes
|  +-- API keys -> HMAC-SHA256
|
+-- Key rotation?
   +-- Symmetric keys -> Every 90 days
   +-- Asymmetric keys -> Every 365 days
   +-- Passwords -> Every 90 days (user)
```

### 12.4 Decision Tree: Security Testing

```
START: What to test?
|
+-- Code level?
|  +-- Yes -> SAST (SonarQube, Bandit)
|  |  +-- When: Every commit
|  |
+-- Dependencies?
|  +-- Yes -> SCA (npm audit, Snyk)
|  |  +-- When: Every build
|  |
+-- Running application?
|  +-- Yes -> DAST (OWASP ZAP, Burp)
|  |  +-- When: Weekly / Pre-release
|  |
+-- Infrastructure?
|  +-- Yes -> CIS Benchmarks
|  |  +-- When: Monthly / After changes
|  |
+-- Penetration testing?
|  +-- Yes -> Manual pentest
|  |  +-- When: Annually / Major releases
|  |
+-- Compliance verification?
   +-- Yes -> Framework-specific audit
      +-- When: Annually / Before certification
```

---

## 13. Migracao de Aplicacoes Legacy para Modernas e Seguras

### 13.1 Estrategia de Migracao

```yaml
# Legacy to Modern Migration Strategy
migration_strategy:
  assessment_phase:
    - inventory_existing_systems
    - identify_security_gaps
    - document_business_requirements
    - prioritize_migrations

  planning_phase:
    - define_target_architecture
    - create_migration_roadmap
    - allocate_resources
    - establish_success_criteria

  execution_phase:
    - implement_security_controls
    - refactor_vulnerable_code
    - update_dependencies
    - add_monitoring_logging

  validation_phase:
    - security_testing
    - performance_testing
    - compliance_verification
    - user_acceptance_testing
```

### 13.2 Common Legacy Security Issues

```typescript
// Legacy Code Patterns to Modernize

// ISSUE 1: Hardcoded database connections
// Legacy:
const db = mysql.createConnection({
  host: 'localhost',
  user: 'admin',
  password: 'password123',
  database: 'myapp'
});

// Modern:
const db = mysql.createConnection({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  ssl: {
    rejectUnauthorized: true,
    ca: fs.readFileSync('/path/to/ca.pem')
  }
});


// ISSUE 2: No input validation
// Legacy:
app.post('/api/users', (req, res) => {
  const query = `INSERT INTO users VALUES
    ('${req.body.name}', '${req.body.email}')`;
  db.query(query);
});

// Modern:
app.post('/api/users', validateUser, async (req, res) => {
  const { name, email } = matchedData(req);

  await db.query(
    'INSERT INTO users (name, email) VALUES ($1, $2)',
    [name, email]
  );
});


// ISSUE 3: No authentication/authorization
// Legacy:
app.get('/api/admin/users', (req, res) => {
  db.query('SELECT * FROM users', (err, results) => {
    res.json(results);
  });
});

// Modern:
app.get('/api/admin/users',
  authenticate,
  authorize('admin'),
  async (req, res) => {
    const users = await db.query(
      'SELECT id, name, email FROM users'
    );
    res.json(users);
  }
);


// ISSUE 4: No error handling
// Legacy:
app.get('/api/users/:id', (req, res) => {
  db.query(
    `SELECT * FROM users WHERE id = ${req.params.id}`,
    (err, results) => {
      if (err) throw err;
      res.json(results[0]);
    }
  );
});

// Modern:
app.get('/api/users/:id', async (req, res) => {
  try {
    const user = await db.query(
      'SELECT id, name, email FROM users WHERE id = $1',
      [req.params.id]
    );

    if (!user) {
      return res.status(404).json({
        error: 'User not found'
      });
    }

    res.json(user);
  } catch (error) {
    logger.error('Error fetching user', { error, userId: req.params.id });
    res.status(500).json({
      error: 'An unexpected error occurred'
    });
  }
});


// ISSUE 5: No audit logging
// Legacy:
app.delete('/api/users/:id', (req, res) => {
  db.query(`DELETE FROM users WHERE id = ${req.params.id}`);
  res.json({ success: true });
});

// Modern:
app.delete('/api/users/:id',
  authenticate,
  authorize('admin'),
  async (req, res) => {
    const { id } = req.params;
    const adminId = req.user.id;

    await auditLogger.log({
      action: 'user_deletion',
      adminId,
      targetUserId: id,
      timestamp: new Date(),
      ipAddress: req.ip
    });

    await db.query('DELETE FROM users WHERE id = $1', [id]);

    res.json({ success: true });
  }
);
```

### 13.3 Migration Checklist

```yaml
# Security Migration Checklist
migration_checklist:
  before_migration:
    - document_current_state
    - identify_sensitive_data
    - create_backup
    - establishrollback_plan

  during_migration:
    - implement_https_everywhere
    - add_authentication
    - add_authorization
    - implement_input_validation
    - add_output_encoding
    - implement_csp_headers
    - add_rate_limiting
    - implement_logging
    - add_monitoring
    - update_dependencies

  after_migration:
    - security_testing
    - penetration_testing
    - compliance_verification
    - performance_testing
    - user_acceptance_testing
    - documentation_update
    - team_training
    - monitoring_verification
```

---

## 14. Templates de Documentacao de Seguranca

### 14.1 Security Policy Template

```markdown
# [Organization Name] Information Security Policy

## 1. Purpose
This policy establishes the framework for protecting
[Organization]'s information assets and systems.

## 2. Scope
This policy applies to all employees, contractors, and
third parties who access [Organization]'s systems.

## 3. Roles and Responsibilities

### 3.1 Information Security Officer
- Overall responsibility for information security
- Policy development and enforcement
- Incident response coordination

### 3.2 Development Team
- Implement security controls in applications
- Follow secure coding practices
- Report security vulnerabilities

### 3.3 Operations Team
- Maintain system security configurations
- Monitor security events
- Implement security patches

## 4. Access Control

### 4.1 User Access Management
- Access granted based on job function
- Least privilege principle enforced
- Access reviewed quarterly

### 4.2 Authentication Requirements
- MFA required for all administrative access
- Password policy: minimum 12 characters
- Session timeout: 30 minutes

## 5. Data Protection

### 5.1 Data Classification
- Public: No protection required
- Internal: Basic access controls
- Confidential: Encryption and access logging
- Restricted: Strong encryption and strict access

### 5.2 Encryption Standards
- Data at rest: AES-256-GCM
- Data in transit: TLS 1.2+
- Key management: HSM or KMS

## 6. Secure Development

### 6.1 Secure Coding Practices
- Input validation on all user inputs
- Output encoding to prevent XSS
- Parameterized queries for database access
- Error handling without information leakage

### 6.2 Code Review
- All code changes require peer review
- Security-focused review for sensitive changes
- Automated security scanning in CI/CD

## 7. Incident Response

### 7.1 Incident Reporting
- All security incidents reported within 1 hour
- Incident response team notified immediately
- Documentation maintained for all incidents

### 7.2 Response Procedures
- Contain the incident
- Eradicate the threat
- Recover systems
- Lessons learned documented

## 8. Compliance

### 8.1 Regulatory Requirements
- PCI DSS for payment processing
- LGPD/GDPR for personal data
- Industry-specific requirements

### 8.2 Audit and Assessment
- Annual security assessment
- Quarterly vulnerability scanning
- Continuous monitoring

## 9. Policy Enforcement

### 9.1 Violations
- Violations may result in disciplinary action
- Serious violations may result in termination
- Legal action may be taken for criminal violations

### 9.2 Exceptions
- Exceptions require CISO approval
- Exceptions documented and time-limited
- Exceptions reviewed quarterly

## 10. Policy Review
- This policy is reviewed annually
- Updated as needed based on changes in
  technology, threats, and regulations
```

### 14.2 Incident Response Plan Template

```markdown
# Incident Response Plan

## 1. Introduction

### 1.1 Purpose
This plan outlines the procedures for responding to
security incidents at [Organization].

### 1.2 Scope
This plan covers all security incidents affecting
[Organization]'s systems, data, and operations.

## 2. Incident Response Team

### 2.1 Team Composition
- Incident Commander
- Technical Lead
- Communications Lead
- Legal Counsel
- Human Resources

### 2.2 Contact Information
- Primary: [Phone/Email]
- Secondary: [Phone/Email]
- Emergency: [Phone/Email]

## 3. Incident Classification

### 3.1 Severity Levels

#### P1 - Critical
- Complete system compromise
- Data breach with sensitive data
- Ransomware attack
- Response time: Immediate

#### P2 - High
- Partial system compromise
- Attempted data breach
- DDoS attack
- Response time: 1 hour

#### P3 - Medium
- Suspicious activity detected
- Policy violation
- Minor vulnerability exploitation
- Response time: 4 hours

#### P4 - Low
- Information gathering attempts
- Minor policy violations
- Response time: 24 hours

## 4. Response Procedures

### 4.1 Detection and Analysis
1. Identify the incident
2. Classify severity level
3. Document initial findings
4. Notify incident response team

### 4.2 Containment
1. Isolate affected systems
2. Preserve evidence
3. Implement temporary controls
4. Assess scope of compromise

### 4.3 Eradication
1. Identify root cause
2. Remove threat from environment
3. Verify removal
4. Implement permanent controls

### 4.4 Recovery
1. Restore systems from clean backups
2. Verify system integrity
3. Monitor for recurrence
4. Return to normal operations

### 4.5 Post-Incident
1. Conduct lessons learned review
2. Update incident response plan
3. Implement preventive measures
4. Document findings

## 5. Communication

### 5.1 Internal Communication
- Notify affected stakeholders
- Provide regular status updates
- Document all communications

### 5.2 External Communication
- Notify affected individuals (if required)
- Notify regulatory authorities (if required)
- Issue public statement (if required)

## 6. Evidence Collection

### 6.1 Evidence Types
- System logs
- Network traffic
- Memory dumps
- Disk images
- Screenshots

### 6.2 Chain of Custody
- Document all evidence handling
- Maintain integrity of evidence
- Store evidence securely

## 7. Legal Considerations

### 7.1 Regulatory Requirements
- LGPD/GDPR notification requirements
- Industry-specific requirements
- Law enforcement coordination

### 7.2 Legal Hold
- Preserve all relevant evidence
- Document all actions taken
- Consult legal counsel

## 8. Plan Maintenance

### 8.1 Testing
- Quarterly tabletop exercises
- Annual full-scale exercises
- Update based on lessons learned

### 8.2 Review
- Annual plan review
- Update after major incidents
- Incorporate industry best practices
```

### 14.3 Security Assessment Report Template

```markdown
# Security Assessment Report

## Executive Summary

### Assessment Overview
- Assessment Type: [Penetration Test / Vulnerability Assessment]
- Date: [Start Date] - [End Date]
- Scope: [Systems/Applications Assessed]
- Assessor: [Name/Organization]

### Key Findings
- Critical: [Number]
- High: [Number]
- Medium: [Number]
- Low: [Number]

### Overall Risk Rating: [Critical/High/Medium/Low]

## Methodology

### Testing Approach
- Reconnaissance
- Vulnerability Discovery
- Exploitation
- Post-Exploitation
- Reporting

### Tools Used
- [List of tools]

## Detailed Findings

### Finding 1: [Title]
- Severity: [Critical/High/Medium/Low]
- CVSS Score: [Score]
- Affected Systems: [Systems]
- Description: [Description]
- Impact: [Impact]
- Remediation: [Recommendation]
- References: [CVE/CWE numbers]

## Recommendations

### Immediate Actions
1. [Critical remediation items]

### Short-term Actions
1. [High priority items]

### Long-term Actions
1. [Strategic improvements]

## Appendices

### A. Vulnerability Details
[Detailed vulnerability information]

### B. Evidence
[Screenshots, logs, proof of concepts]

### C. Methodology Details
[Detailed testing methodology]
```

---

## 15. Exercicios

### Exercicio 1: OWASP ASVS Assessment

**Objetivo**: Avaliar uma aplicacao web usando o framework ASVS.

**Instrucoes**:
1. Escolha uma aplicacao web (pode ser um projeto pessoal ou open source)
2. Selecione o nivel de verificacao apropriado
3. Avalie a aplicacao contra os requisitos do ASVS
4. Documente as lacunas encontradas
5. Crie um plano de remediacao

**Entregaveis**:
- Relatorio de avaliacao ASVS
- Lista de lacunas com prioridades
- Plano de remediacao com timeline

---

### Exercicio 2: PCI DSS Implementation

**Objetivo**: Implementar controles PCI DSS em uma aplicacao de pagamento.

**Instrucoes**:
1. Crie uma aplicacao web simples de processamento de pagamento
2. Implemente criptografia de dados de cartao
3. Adicione tokenizacao
4. Implemente logging de auditoria
5. Adicione headers de seguranca

**Entregaveis**:
- Codigo-fonte da aplicacao
- Documentacao dos controles implementados
- Relatorio de conformidade PCI DSS

---

### Exercicio 3: LGPD Compliance

**Objetivo**: Implementar gerenciamento de consentimento conforme LGPD.

**Instrucoes**:
1. Crie um componente de gerenciamento de consentimento
2. Implemente registro de consentimento
3. Adicione funcionalidade de retiro de consentimento
4. Implemente exportacao de dados (portabilidade)
5. Implemente exclusao de dados (right to be forgotten)

**Entregaveis**:
- Componente de consentimento
- API de gerenciamento de consentimento
- Documentacao de conformidade LGPD

---

### Exercicio 4: Security Hardening

**Objetivo**: Configurar um web server conforme CIS Benchmark.

**Instrucoes**:
1. Instale Nginx ou Apache
2. Aplique as configuracoes CIS Benchmark
3. Implemente headers de seguranca
4. Configure SSL/TLS corretamente
5. Valide as configuracoes

**Entregaveis**:
- Configuracao do web server
- Script de validacao
- Relatorio de conformidade CIS

---

### Exercicio 5: Incident Response Drill

**Objetivo**: Simular resposta a incidente de seguranca.

**Instrucoes**:
1. Crie um cenario de incidente
2. Execute o plano de resposta a incidentes
3. Documente todas as acoes tomadas
4. Analise a eficacia da resposta
5. Identifique melhorias

**Entregaveis**:
- Cenario de incidente
- Documentacao do exercicio
- Relatorio pos-incidente
- Lista de melhorias

---

### Exercicio 6: Security Checklist Audit

**Objetivo**: Realizar auditoria completa usando checklist de seguranca.

**Instrucoes**:
1. Use a checklist fornecida neste capitulo
2. Verifique cada item em uma aplicacao web
3. Documente conformidade/nao-conformidade
4. Gere relatorio de conformidade
5. Crie plano de acao para lacunas

**Entregaveis**:
- Checklist preenchido
- Relatorio de conformidade
- Plano de acao

---

### Exercicio 7: Legacy Migration

**Objetivo**: Migrar aplicacao legacy para arquitetura moderna segura.

**Instrucoes**:
1. Identifique vulnerabilidades em codigo legacy
2. Crie plano de migracao
3. Implemente correcoes de seguranca
4. Adicione autenticacao e autorizacao
5. Implemente logging e monitoramento

**Entregaveis**:
- Analise de vulnerabilidades
- Plano de migracao
- Codigo migrado
- Documentacao das mudancas

---

## 16. Referencias

### 16.1 Padroes e Frameworks

- OWASP Application Security Verification Standard (ASVS)
  https://owasp.org/www-project-application-security-verification-standard/

- OWASP Software Assurance Maturity Model (SAMM)
  https://owasp.org/www-project-samm/

- PCI Data Security Standard (PCI DSS)
  https://www.pcisecuritystandards.org/document_library/

- LGPD - Lei Geral de Protecao de Dados
  https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm

- GDPR - General Data Protection Regulation
  https://gdpr-info.eu/

- HIPAA Security Rule
  https://www.hhs.gov/hipaa/for-professionals/security/index.html

- SOC 2
  https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report

- ISO/IEC 27001
  https://www.iso.org/isoiec-27001-information-security.html

- CIS Benchmarks
  https://www.cisecurity.org/cis-benchmarks/

### 16.2 Ferramentas

- OWASP ZAP (Dynamic Application Security Testing)
  https://www.zaproxy.org/

- Burp Suite (Web Application Security Testing)
  https://portswigger.net/burp

- SonarQube (Static Code Analysis)
  https://www.sonarsource.com/

- Snyk (Dependency Scanning)
  https://snyk.io/

- npm audit (Dependency Vulnerability Check)
  https://docs.npmjs.com/cli/audit

### 16.3 Livros e Artigos

- "The Web Application Hacker's Handbook" by Dafydd Stuttard
- "Application Security for the Android Platform" by Joel Scambray
- "Securing Node.js Web Applications" by Frank Zammetti
- "OAuth 2 in Action" by Justin Richer
- "Secure by Design" by Dan Bergh Johnsson

### 16.4 Recursos Online

- OWASP Cheat Sheet Series
  https://cheatsheetseries.owasp.org/

- NIST Cybersecurity Framework
  https://www.nist.gov/cyberframework

- SANS Reading Room
  https://www.sans.org/reading-room/

- SecurityHeaders.com (Security Header Analysis)
  https://securityheaders.com/

- Mozilla Observatory (Security Assessment)
  https://observatory.mozilla.org/

---

## Resumo

Este capitulo cobriu os principais frameworks de compliance e boas praticas para aplicacoes web, incluindo:

1. **OWASP ASVS**: Framework de verificacao de seguranca com tres niveis de maturidade
2. **OWASP SAMM**: Modelo de maturidade para processos de seguranca de software
3. **PCI DSS**: Padrao de seguranca para processamento de pagamentos
4. **LGPD/GDPR**: Regulamentacoes de protecao de dados pessoais
5. **HIPAA**: Regulamentacao para dados de saude
6. **SOC 2**: Framework de auditoria para servicos baseados em cloud
7. **ISO 27001**: Padrao internacional para gestao de seguranca da informacao
8. **CIS Benchmarks**: Guias de configuracao segura para web servers
9. **Anti-Patterns**: Padroes a serem evitados em seguranca web
10. **Checklists**: Listas de verificacao para garantir conformidade
11. **Decision Trees**: Arvores de decisao para escolhas de seguranca
12. **Migracao**: Estrategias para modernizar aplicacoes legacy
13. **Documentacao**: Templates para politicas e procedimentos de seguranca

Lembre-se: compliance e um processo continuo, nao um destino. Implemente controles de seguranca, monitore continuamente, e melhore seus processos regularmente.
