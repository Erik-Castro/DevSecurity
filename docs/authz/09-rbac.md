# Capítulo 9 — RBAC (Role-Based Access Control)

## Introdução

Role-Based Access Control (RBAC) é o modelo de autorização mais amplamente adotado em sistemas corporativos, governamentais, e web. RBAC define permissões através de papéis (roles): em vez de atribuir permissões diretamente a usuários, os usuários recebem papéis que agrupam permissões relacionadas. Essa camada intermediária simplifica drasticamente a gestão de acesso, reduz erros, e fornece auditoria centralizada.

RBAC não é apenas um padrão técnico — é um padrão de negócio. Organizações pensam naturalmente em termos de papéis: "desenvolvedores podem fazer deploy", "auditores podem ver logs", "clientes podem ver seus próprios dados". RBAC alinha o modelo técnico com a estrutura organizacional, tornando a autorização mais intuitiva e auditável.

O caso Misantropi4 contra o IDAP revela um problema clássico de RBAC: excessive privileges. Se os operadores do IDAP tivessem implementado RBAC com o princípio do menor privilege, mesmo que credenciais fossem comprometidas, o dano teria sido limitado ao escopo mínimo necessário. Um atacante com credenciais de um operador de nível baixo não deveria ter acesso a million de registros — apenas aos registros que seu papel permite.

Este capítulo cobre o modelo NIST RBAC, os quatro níveis (Core, Hierarchical, Constrained, Symmetric), implementação em bancos de dados, código Python e Go, design de hierarquias, o problema de role explosion, comparação com ACL, e análise do caso Misantropi4.

---

## 9.1 Fundamentos do RBAC

### 9.1.1 O modelo NIST RBAC

O NIST (National Institute of Standards and Technology) definiu o padrão RBAC no documento NIST RBAC Standard (ANSI INCITS 359-2004). O modelo NIST define quatro componentes fundamentais:

1. **Users**: As entidades que solicitam acesso (pessoas, processos, serviços)
2. **Roles**: Agrupamentos semânticos de permissões (desenvolvedor, auditor, admin)
3. **Permissions**: Autorização para executar uma ou mais operações em recursos
4. **Sessions**: Associações temporárias entre users e roles durante um período de acesso

**Relacionamentos:**
- **User Assignment (UA)**: Quais users são atribuídos a quais roles
- **Permission Assignment (PA)**: Quais permissões são atribuídas a quais roles

```
┌──────────┐    UA    ┌──────────┐    PA    ┌──────────────┐
│  Users   │<========>│  Roles   │<========>│ Permissions  │
└──────────┘          └──────────┘          └──────────────┘
     │                     │                       │
     │                     │                       │
     v                     v                       v
┌──────────┐          ┌──────────┐          ┌──────────────┐
│ Session  │          │Sessions  │          │  Resources   │
│ (user    │          │(active   │          │  + Actions   │
│  context)│          │  roles)  │          │              │
└──────────┘          └──────────┘          └──────────────┘
```

### 9.1.2 Por que RBAC em vez de ACL

**Access Control Lists (ACL)** associam permissões diretamente a usuários:

```
ACL:
  user:joao    -> read:file1, write:file1
  user:maria   -> read:file1, read:file2
  user:pedro   -> write:file2, delete:file2
```

**RBAC** usa roles como intermediários:

```
RBAC:
  role:editor   -> read:any_file, write:any_file
  role:viewer   -> read:any_file
  
  user:joao    -> role:editor
  user:maria   -> role:viewer
  user:pedro   -> role:editor
```

**Problemas do ACL em larga escala:**
- Adicionar uma nova permissão requer modificar cada usuário individualmente
- Não há visão consolidada de "quem pode fazer o quê"
- Auditoria é dolorosa: precisa verificar cada entrada de ACL
- Remover um funcionário requer deletar múltiplas entradas
- Consistência difícil de manter

**Vantagens do RBAC:**
- Adicionar permissão: atribuir a role, todos os usuários da role ganham acesso
- Remover usuário: desatribuir da role, todas as permissões são removidas
- Auditoria: verifique as roles e suas permissões
- Escalabilidade: O(n*m) para ACL vs O(n+m) para RBAC (n=usuários, m=permissões)

### 9.1.3 Propriedades formais do RBAC

O modelo NIST RBAC define propriedades formais que todo sistema deve satisfazer:

**Propriedade 1 (P1) - Multi-patrocinio de usuários**: Um usuário pode ser atribuído a múltiplas roles simultaneamente.

```
user:joao -> role:developer, role:team_lead
```

Isso permite que joao tenha todas as permissões de developer E team_lead.

**Propriedade 2 (P2) - Multi-patrocinio de permissões**: Uma permissão pode ser atribuída a múltiplas roles.

```
role:developer -> perm:read_code, perm:write_code
role:team_lead -> perm:read_code, perm:write_code, perm:approve_pr
```

Ambas as roles têm a permissão `read_code`.

**Propriedade 3 (P3) - Roles autorizadas por hierarquia**: Roles podem ter relacionamentos hierárquicos (herança).

```
role:admin > role:manager > role:employee
```

Admin herda todas as permissões de manager, que herda todas as permissões de employee.

**Propriedade 4 (P4) - Roles autorizadas por restrições**: Roles podem ter restrições de separação (separation of duty).

```
role:accountant pode_ter -> role:approver NÃO pode_ter
```

Um usuário que é accountant não pode ser approver (separação de duties).

---

## 9.2 Core RBAC

Core RBAC é o nível mais básico do modelo NIST. Define users, roles, permissions, e as associações user-role e permission-role.

### 9.2.1 Definição formal

```
Core RBAC = {
    U:  conjuntos de users
    R:  conjuntos de roles
    P:  conjuntos de permissions
    UA: U x R (user assignments)
    PA: R x P (permission assignments)
    RH: R x R (role hierarchy — opcional em Core)
}
```

### 9.2.2 Implementação em banco de dados

```sql
-- Schema de Core RBAC
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) UNIQUE NOT NULL,
    resource    VARCHAR(100) NOT NULL,
    action      VARCHAR(50) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(resource, action)
);

-- User-Role Assignment (UA)
CREATE TABLE user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by  UUID REFERENCES users(id),
    granted_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,  -- NULL = sem expiração
    
    UNIQUE(user_id, role_id)
);

-- Permission-Role Assignment (PA)
CREATE TABLE role_permissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(role_id, permission_id)
);

-- Indices
CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_perm ON role_permissions(permission_id);
CREATE INDEX idx_permissions_resource ON permissions(resource);
```

### 9.2.3 Seed data de exemplo

```sql
-- Roles do sistema
INSERT INTO roles (name, description) VALUES
    ('super_admin', 'Acesso total ao sistema'),
    ('admin', 'Administrador com permissões amplas'),
    ('manager', 'Gerente com permissões de gestão'),
    ('developer', 'Desenvolvedor com acesso ao código'),
    ('viewer', 'Visualizador somente leitura'),
    ('auditor', 'Auditor com acesso a logs e relatórios');

-- Permissions do sistema
INSERT INTO permissions (name, resource, action, description) VALUES
    -- Usuários
    ('users:read', 'users', 'read', 'Listar usuários'),
    ('users:create', 'users', 'create', 'Criar usuários'),
    ('users:update', 'users', 'update', 'Editar usuários'),
    ('users:delete', 'users', 'delete', 'Excluir usuários'),
    
    -- Projetos
    ('projects:read', 'projects', 'read', 'Ver projetos'),
    ('projects:create', 'projects', 'create', 'Criar projetos'),
    ('projects:update', 'projects', 'update', 'Editar projetos'),
    ('projects:delete', 'projects', 'delete', 'Excluir projetos'),
    ('projects:deploy', 'projects', 'deploy', 'Fazer deploy de projetos'),
    
    -- Código
    ('code:read', 'code', 'read', 'Ler código fonte'),
    ('code:write', 'code', 'write', 'Escrever código'),
    ('code:review', 'code', 'review', 'Revisar código'),
    ('code:merge', 'code', 'merge', 'Merge de branches'),
    
    -- Logs
    ('logs:read', 'logs', 'read', 'Visualizar logs'),
    ('logs:export', 'logs', 'export', 'Exportar logs'),
    
    -- Configurações
    ('settings:read', 'settings', 'read', 'Ver configurações'),
    ('settings:update', 'settings', 'update', 'Alterar configurações');

-- Role-Permission assignments
-- super_admin: tudo
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'super_admin';

-- admin: tudo exceto super_admin
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'admin'
AND p.name NOT LIKE 'super_%';

-- manager: gestão de projetos e usuários
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'manager'
AND p.name IN (
    'users:read', 'users:create', 'users:update',
    'projects:read', 'projects:create', 'projects:update',
    'logs:read'
);

-- developer: código e projetos
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'developer'
AND p.name IN (
    'projects:read', 'projects:update',
    'code:read', 'code:write', 'code:review'
);

-- viewer: apenas leitura
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'viewer'
AND p.name LIKE '%:read';

-- auditor: logs e leitura geral
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'auditor'
AND (p.name LIKE '%:read' OR p.name = 'logs:export');
```

### 9.2.4 Verificação de acesso

```sql
-- Verificar se um usuário tem uma permissão específica
SELECT 
    u.username,
    r.name AS role_name,
    p.name AS permission_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE u.id = :user_id
AND p.name = :permission_name
AND u.active = TRUE
AND r.active = TRUE
AND (ur.expires_at IS NULL OR ur.expires_at > NOW());

-- Listar todas as permissões de um usuário
SELECT DISTINCT p.name AS permission_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
JOIN role_permissions rp ON r.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id
WHERE u.id = :user_id
AND u.active = TRUE
AND r.active = TRUE
AND (ur.expires_at IS NULL OR ur.expires_at > NOW());

-- Listar todos os usuários com uma role específica
SELECT u.username, u.email
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE r.name = :role_name
AND u.active = TRUE
AND (ur.expires_at IS NULL OR ur.expires_at > NOW());
```

---

## 9.3 Hierarchical RBAC

Hierarchical RBAC adiciona relacionamentos de herança entre roles. Uma role pai herda todas as permissões de suas roles filhas, e uma role filho herda todas as permissões de suas roles pai.

### 9.3.1 Modelo de hierarquia

```
         ┌──────────┐
         │super_admin│
         └────┬─────┘
              │ herda
         ┌────┴─────┐
         │  admin    │
         └────┬─────┘
              │ herda
    ┌─────────┼─────────┐
    │         │         │
┌───┴──┐ ┌───┴──┐ ┌───┴──┐
│manager│ │viewer│ │auditor│
└───┬──┘ └──────┘ └──────┘
    │ herda
┌───┴──────┐
│developer │
└──────────┘
```

Neste diagrama:
- `super_admin` herda de `admin`
- `admin` herda de `manager`, `viewer`, `auditor`
- `manager` herda de `developer`

### 9.3.2 Implementação da hierarquia

```sql
-- Tabela de hierarquia de roles
CREATE TABLE role_hierarchy (
    parent_role_id  UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    child_role_id   UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    
    PRIMARY KEY (parent_role_id, child_role_id),
    -- Impedir auto-herança
    CHECK (parent_role_id != child_role_id)
);

-- Constraint para impedir ciclos (implementado via trigger)
-- Ver seção 9.3.4 para trigger

-- Indices
CREATE INDEX idx_role_hierarchy_parent ON role_hierarchy(parent_role_id);
CREATE INDEX idx_role_hierarchy_child ON role_hierarchy(child_role_id);

-- Hierarquia de exemplo
INSERT INTO role_hierarchy (parent_role_id, child_role_id) VALUES
    ((SELECT id FROM roles WHERE name = 'super_admin'),
     (SELECT id FROM roles WHERE name = 'admin')),
    ((SELECT id FROM roles WHERE name = 'admin'),
     (SELECT id FROM roles WHERE name = 'manager')),
    ((SELECT id FROM roles WHERE name = 'admin'),
     (SELECT id FROM roles WHERE name = 'viewer')),
    ((SELECT id FROM roles WHERE name = 'admin'),
     (SELECT id FROM roles WHERE name = 'auditor')),
    ((SELECT id FROM roles WHERE name = 'manager'),
     (SELECT id FROM roles WHERE name = 'developer'));
```

### 9.3.3 Query de herança recursiva

```sql
-- Obter todas as permissões de um usuário via hierarquia
WITH RECURSIVE role_tree AS (
    -- Roles diretas do usuário
    SELECT r.id, r.name
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE u.id = :user_id
    AND u.active = TRUE
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    
    UNION
    
    -- Roles pai (herança)
    SELECT rh.parent_role_id, r2.name
    FROM role_tree rt
    JOIN role_hierarchy rh ON rt.id = rh.child_role_id
    JOIN roles r2 ON rh.parent_role_id = r2.id
    WHERE r2.active = TRUE
)
SELECT DISTINCT p.name AS permission_name
FROM role_tree rt
JOIN role_permissions rp ON rt.id = rp.role_id
JOIN permissions p ON rp.permission_id = p.id;
```

### 9.3.4 Prevenção de ciclos na hierarquia

```sql
-- Trigger para impedir ciclos na hierarquia de roles
CREATE OR REPLACE FUNCTION check_role_hierarchy_cycle()
RETURNS TRIGGER AS $$
DECLARE
    cycle_exists BOOLEAN;
BEGIN
    -- Check if adding this edge would create a cycle
    WITH RECURSIVE ancestors AS (
        SELECT NEW.child_role_id AS role_id
        
        UNION ALL
        
        SELECT rh.parent_role_id
        FROM ancestors a
        JOIN role_hierarchy rh ON a.role_id = rh.child_role_id
        WHERE a.role_id != NEW.parent_role_id
    )
    SELECT EXISTS(
        SELECT 1 FROM ancestors WHERE role_id = NEW.parent_role_id
    ) INTO cycle_exists;
    
    IF cycle_exists THEN
        RAISE EXCEPTION 'Cycle detected in role hierarchy';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_role_hierarchy_cycle
    BEFORE INSERT OR UPDATE ON role_hierarchy
    FOR EACH ROW
    EXECUTE FUNCTION check_role_hierarchy_cycle();
```

```python
# Python — verificação de ciclo antes de inserir
class RoleHierarchyManager:
    """Manage role hierarchy with cycle detection."""
    
    def __init__(self, db):
        self.db = db
    
    def add_hierarchy(self, parent_role_id: str, child_role_id: str) -> bool:
        """Add a parent-child relationship with cycle detection."""
        # Check if relationship already exists
        existing = self.db.query("""
            SELECT 1 FROM role_hierarchy 
            WHERE parent_role_id = %s AND child_role_id = %s
        """, (parent_role_id, child_role_id))
        
        if existing:
            return True  # Already exists
        
        # Check for cycles using DFS
        if self._has_cycle(parent_role_id, child_role_id):
            raise ValueError(
                f"Adding {parent_role_id} -> {child_role_id} "
                f"would create a cycle"
            )
        
        # Check for self-assignment
        if parent_role_id == child_role_id:
            raise ValueError("A role cannot be its own parent")
        
        # Insert
        self.db.execute("""
            INSERT INTO role_hierarchy (parent_role_id, child_role_id)
            VALUES (%s, %s)
        """, (parent_role_id, child_role_id))
        
        return True
    
    def _has_cycle(self, parent_id: str, child_id: str) -> bool:
        """Check if adding parent->child would create a cycle."""
        # BFS from child to see if we can reach parent
        visited = set()
        queue = [child_id]
        
        while queue:
            current = queue.pop(0)
            
            if current == parent_id:
                return True  # Cycle found
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Get parents of current
            parents = self.db.query("""
                SELECT parent_role_id FROM role_hierarchy 
                WHERE child_role_id = %s
            """, (current,))
            
            for row in parents:
                queue.append(row['parent_role_id'])
        
        return False
    
    def get_all_ancestors(self, role_id: str) -> list:
        """Get all ancestor roles (roles that this role inherits from)."""
        query = """
            WITH RECURSIVE ancestors AS (
                SELECT parent_role_id
                FROM role_hierarchy
                WHERE child_role_id = %s
                
                UNION
                
                SELECT rh.parent_role_id
                FROM ancestors a
                JOIN role_hierarchy rh ON a.parent_role_id = rh.child_role_id
            )
            SELECT DISTINCT r.id, r.name
            FROM ancestors a
            JOIN roles r ON a.parent_role_id = r.id
        """
        return self.db.query(query, (role_id,))
    
    def get_all_descendants(self, role_id: str) -> list:
        """Get all descendant roles (roles that inherit from this role)."""
        query = """
            WITH RECURSIVE descendants AS (
                SELECT child_role_id
                FROM role_hierarchy
                WHERE parent_role_id = %s
                
                UNION
                
                SELECT rh.child_role_id
                FROM descendants d
                JOIN role_hierarchy rh ON d.child_role_id = rh.parent_role_id
            )
            SELECT DISTINCT r.id, r.name
            FROM descendants d
            JOIN roles r ON d.child_role_id = r.id
        """
        return self.db.query(query, (role_id,))
```

---

## 9.4 Constrained RBAC

Constrained RBAC adiciona restrições de separação de deveres (Separation of Duty - SoD). Isso impede que um usuário tenha roles conflitantes simultaneamente.

### 9.4.1 Tipos de separação de deveres

**Static Separation of Duty (SSoD)**: Um usuário não pode ser atribuído a duas roles conflitantes. A restrição é verificada no momento da atribuição.

```
Exemplo: Um usuário não pode ser tanto "accountant" quanto "approver"
SSoD: {accountant, approver}
```

**Dynamic Separation of Duty (DSoD)**: Um usuário pode ter ambas as roles, mas não pode ativá-las simultaneamente na mesma sessão.

```
Exemplo: Um usuário pode ser "developer" e "reviewer", mas não pode
usar ambas as roles ao mesmo tempo em uma sessão
DSoD: {developer, reviewer}
```

### 9.4.2 Implementação de SSoD

```sql
-- Tabela de restrições SSoD
CREATE TABLE sod_constraints (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    role_a_id   UUID NOT NULL REFERENCES roles(id),
    role_b_id   UUID NOT NULL REFERENCES roles(id),
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    
    -- Impedir auto-conflito
    CHECK (role_a_id != role_b_id),
    -- Impedir duplicatas (A,B = B,A)
    UNIQUE(role_a_id, role_b_id)
);

-- Trigger para verificar SSoD antes de atribuir role
CREATE OR REPLACE FUNCTION check_sod_constraint()
RETURNS TRIGGER AS $$
DECLARE
    conflict_exists BOOLEAN;
BEGIN
    -- Check if user already has a conflicting role
    SELECT EXISTS(
        SELECT 1
        FROM user_roles ur
        JOIN sod_constraints sc ON (
            (sc.role_a_id = ur.role_id AND sc.role_b_id = NEW.role_id)
            OR
            (sc.role_b_id = ur.role_id AND sc.role_a_id = NEW.role_id)
        )
        WHERE ur.user_id = NEW.user_id
        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
    ) INTO conflict_exists;
    
    IF conflict_exists THEN
        RAISE EXCEPTION 'SSoD violation: user cannot have both roles';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_sod_constraint
    BEFORE INSERT ON user_roles
    FOR EACH ROW
    EXECUTE FUNCTION check_sod_constraint();
```

### 9.4.3 Implementação de DSoD

```python
# Dynamic Separation of Duty
class DSoDManager:
    """Manage Dynamic Separation of Duty constraints."""
    
    def __init__(self, db):
        self.db = db
    
    def check_dsod(self, user_id: str, roles_to_activate: list) -> bool:
        """Check if activating these roles violates DSoD."""
        # Get DSoD constraints
        constraints = self.db.query("""
            SELECT role_a_id, role_b_id 
            FROM dsod_constraints
        """)
        
        # Get currently active roles
        active_roles = self.db.query("""
            SELECT role_id FROM user_role_sessions
            WHERE user_id = %s AND active = TRUE
        """, (user_id,))
        
        active_role_ids = {r['role_id'] for r in active_roles}
        new_role_ids = set(roles_to_activate)
        all_role_ids = active_role_ids | new_role_ids
        
        # Check each constraint
        for constraint in constraints:
            if (constraint['role_a_id'] in all_role_ids and
                constraint['role_b_id'] in all_role_ids):
                return False  # DSoD violation
        
        return True
    
    def activate_roles(self, user_id: str, session_id: str, 
                       roles: list) -> dict:
        """Activate roles for a session with DSoD check."""
        if not self.check_dsod(user_id, roles):
            return {
                'success': False,
                'error': 'DSoD violation: '
                         'cannot activate conflicting roles'
            }
        
        # Deactivate current roles
        self.db.execute("""
            UPDATE user_role_sessions
            SET active = FALSE
            WHERE user_id = %s AND session_id = %s
        """, (user_id, session_id))
        
        # Activate new roles
        for role_id in roles:
            self.db.execute("""
                INSERT INTO user_role_sessions 
                (user_id, session_id, role_id, activated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id, session_id, role_id)
                DO UPDATE SET active = TRUE, activated_at = NOW()
            """, (user_id, session_id, role_id))
        
        return {'success': True, 'activated_roles': roles}
```

### 9.4.4 DSoD com sessões

```sql
-- Tabela de sessões de roles (para DSoD)
CREATE TABLE user_role_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    session_id  UUID NOT NULL,
    role_id     UUID NOT NULL REFERENCES roles(id),
    active      BOOLEAN DEFAULT TRUE,
    activated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, session_id, role_id)
);

-- Constraints DSoD
CREATE TABLE dsod_constraints (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    role_a_id   UUID NOT NULL REFERENCES roles(id),
    role_b_id   UUID NOT NULL REFERENCES roles(id),
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    
    CHECK (role_a_id != role_b_id),
    UNIQUE(role_a_id, role_b_id)
);
```

---

## 9.5 RBAC em Bancos de Dados

### 9.5.1 Estratégias de implementação

**Strategy 1: Schema normalizado (recomendado)**
Tabelas separadas para users, roles, permissions, e tabelas de associação. Mais flexível, mais auditável.

**Strategy 2: Claims-based**
Permissões são embedadas em tokens JWT ou claims. Mais rápido para leitura, mais difícil de atualizar.

**Strategy 3: Hybrid**
Roles normalizadas, permissões em cache/claims. Equilíbrio entre flexibilidade e performance.

### 9.5.2 Performance e caching

```python
# RBAC com cache para performance
import redis
import json
from functools import lru_cache

class RBACService:
    """RBAC service with Redis caching."""
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.CACHE_TTL = 300  # 5 minutes
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission."""
        # Try cache first
        cache_key = f"rbac:{user_id}:{permission}"
        cached = self.redis.get(cache_key)
        
        if cached is not None:
            return cached == '1'
        
        # Cache miss — query database
        result = self.db.query("""
            SELECT EXISTS(
                SELECT 1
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                JOIN roles r ON ur.role_id = r.id
                JOIN role_permissions rp ON r.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE u.id = %s
                AND p.name = %s
                AND u.active = TRUE
                AND r.active = TRUE
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            )
        """, (user_id, permission))
        
        has_permission = result[0][0]
        
        # Cache result
        self.redis.setex(
            cache_key,
            self.CACHE_TTL,
            '1' if has_permission else '0'
        )
        
        return has_permission
    
    def get_user_permissions(self, user_id: str) -> set:
        """Get all permissions for a user."""
        cache_key = f"rbac:{user_id}:permissions"
        cached = self.redis.get(cache_key)
        
        if cached:
            return set(json.loads(cached))
        
        permissions = self.db.query("""
            SELECT DISTINCT p.name
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN roles r ON ur.role_id = r.id
            JOIN role_permissions rp ON r.id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = %s
            AND u.active = TRUE
            AND r.active = TRUE
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
        """, (user_id,))
        
        perm_set = {p['name'] for p in permissions}
        
        self.redis.setex(
            cache_key,
            self.CACHE_TTL,
            json.dumps(list(perm_set))
        )
        
        return perm_set
    
    def invalidate_cache(self, user_id: str):
        """Invalidate all cached permissions for a user."""
        pattern = f"rbac:{user_id}:*"
        keys = self.redis.keys(pattern)
        
        if keys:
            self.redis.delete(*keys)
    
    def on_role_change(self, role_id: str):
        """Invalidate cache for all users with this role."""
        # Get all users with this role
        users = self.db.query("""
            SELECT user_id FROM user_roles WHERE role_id = %s
        """, (role_id,))
        
        for user in users:
            self.invalidate_cache(user['user_id'])
```

### 9.5.3 Row-Level Security (RLS)

RBAC pode ser combinado com Row-Level Security para controle de acesso em nível de linha:

```sql
-- Row-Level Security com RBAC
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Policy: developers can only see their team's projects
CREATE POLICY developer_project_access ON projects
    FOR SELECT
    TO authenticated_user
    USING (
        team_id IN (
            SELECT t.id
            FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            WHERE tm.user_id = current_user_id()
        )
        OR
        EXISTS (
            SELECT 1
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = current_user_id()
            AND r.name IN ('admin', 'super_admin')
        )
    );

-- Policy: managers can see all projects in their department
CREATE POLICY manager_project_access ON projects
    FOR ALL
    TO authenticated_user
    USING (
        department_id = (
            SELECT department_id
            FROM users
            WHERE id = current_user_id()
        )
        AND
        EXISTS (
            SELECT 1
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = current_user_id()
            AND r.name = 'manager'
        )
    );
```

---

## 9.6 Implementação em Python

### 9.6.1 Framework RBAC completo

```python
# rbac_framework.py — RBAC framework completo
from functools import wraps
from typing import Optional, Set, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RBACFramework:
    """Complete RBAC framework for Python applications."""
    
    def __init__(self, db, cache=None):
        self.db = db
        self.cache = cache
        self.permission_cache = {}
    
    # --- Core Operations ---
    
    def assign_role(self, user_id: str, role_id: str, 
                    granted_by: Optional[str] = None,
                    expires_at: Optional[datetime] = None) -> bool:
        """Assign a role to a user."""
        # Check SSoD constraints
        if not self._check_ssod(user_id, role_id):
            raise SSoDViolation(
                f"User {user_id} cannot be assigned role {role_id} "
                f"due to SSoD constraints"
            )
        
        # Check if already assigned
        existing = self.db.query("""
            SELECT id FROM user_roles 
            WHERE user_id = %s AND role_id = %s
        """, (user_id, role_id))
        
        if existing:
            return True  # Already assigned
        
        # Assign
        self.db.execute("""
            INSERT INTO user_roles (user_id, role_id, granted_by, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, role_id, granted_by, expires_at))
        
        # Invalidate cache
        self._invalidate_cache(user_id)
        
        logger.info(f"Role {role_id} assigned to user {user_id}")
        return True
    
    def revoke_role(self, user_id: str, role_id: str) -> bool:
        """Revoke a role from a user."""
        result = self.db.execute("""
            DELETE FROM user_roles 
            WHERE user_id = %s AND role_id = %s
        """, (user_id, role_id))
        
        self._invalidate_cache(user_id)
        
        logger.info(f"Role {role_id} revoked from user {user_id}")
        return result.rowcount > 0
    
    def check_permission(self, user_id: str, 
                        permission_name: str) -> bool:
        """Check if a user has a specific permission."""
        # Try cache
        cache_key = f"{user_id}:{permission_name}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]
        
        # Query with hierarchy
        result = self.db.query("""
            WITH RECURSIVE role_tree AS (
                SELECT r.id
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                AND r.active = TRUE
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                
                UNION
                
                SELECT rh.parent_role_id
                FROM role_tree rt
                JOIN role_hierarchy rh ON rt.id = rh.child_role_id
            )
            SELECT EXISTS(
                SELECT 1
                FROM role_tree rt
                JOIN role_permissions rp ON rt.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE p.name = %s
            )
        """, (user_id, permission_name))
        
        has_permission = result[0][0]
        
        # Cache
        self.permission_cache[cache_key] = has_permission
        
        return has_permission
    
    def get_user_roles(self, user_id: str) -> List[dict]:
        """Get all roles for a user (including inherited)."""
        result = self.db.query("""
            WITH RECURSIVE role_tree AS (
                SELECT r.id, r.name, r.description, 
                       ur.granted_at, ur.expires_at
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                AND r.active = TRUE
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                
                UNION
                
                SELECT r2.id, r2.name, r2.description,
                       NULL, NULL
                FROM role_tree rt
                JOIN role_hierarchy rh ON rt.id = rh.child_role_id
                JOIN roles r2 ON rh.parent_role_id = r2.id
                WHERE r2.active = TRUE
            )
            SELECT DISTINCT id, name, description, granted_at, expires_at
            FROM role_tree
            ORDER BY name
        """, (user_id,))
        
        return result
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user."""
        result = self.db.query("""
            WITH RECURSIVE role_tree AS (
                SELECT r.id
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                AND r.active = TRUE
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                
                UNION
                
                SELECT rh.parent_role_id
                FROM role_tree rt
                JOIN role_hierarchy rh ON rt.id = rh.child_role_id
            )
            SELECT DISTINCT p.name
            FROM role_tree rt
            JOIN role_permissions rp ON rt.id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
        """, (user_id,))
        
        return {p['name'] for p in result}
    
    # --- SSoD ---
    
    def _check_ssod(self, user_id: str, role_id: str) -> bool:
        """Check if assigning a role would violate SSoD."""
        result = self.db.query("""
            SELECT EXISTS(
                SELECT 1
                FROM user_roles ur
                JOIN sod_constraints sc ON (
                    (sc.role_a_id = ur.role_id AND sc.role_b_id = %s)
                    OR
                    (sc.role_b_id = ur.role_id AND sc.role_a_id = %s)
                )
                WHERE ur.user_id = %s
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            )
        """, (role_id, role_id, user_id))
        
        return not result[0][0]
    
    def add_ssod_constraint(self, role_a_id: str, role_b_id: str,
                           name: str, description: str = None) -> bool:
        """Add a Static SoD constraint."""
        self.db.execute("""
            INSERT INTO sod_constraints (name, role_a_id, role_b_id, description)
            VALUES (%s, %s, %s, %s)
        """, (name, role_a_id, role_b_id, description))
        
        return True
    
    # --- Cache ---
    
    def _invalidate_cache(self, user_id: str):
        """Invalidate cached permissions for a user."""
        keys_to_remove = [
            k for k in self.permission_cache 
            if k.startswith(f"{user_id}:")
        ]
        for key in keys_to_remove:
            del self.permission_cache[key]


class SSoDViolation(Exception):
    """Raised when a Static Separation of Duty constraint is violated."""
    pass


# --- Decorator for route protection ---
def require_permission(permission: str):
    """Decorator to require a specific permission for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g, jsonify
            
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'error': 'Not authenticated'}), 401
            
            rbac = get_rbac_service()
            if not rbac.check_permission(user_id, permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(role_name: str):
    """Decorator to require a specific role for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g, jsonify
            
            user_id = g.get('user_id')
            if not user_id:
                return jsonify({'error': 'Not authenticated'}), 401
            
            rbac = get_rbac_service()
            user_roles = rbac.get_user_roles(user_id)
            role_names = {r['name'] for r in user_roles}
            
            if role_name not in role_names:
                return jsonify({'error': 'Insufficient role'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 9.6.2 Integração com Flask

```python
# app.py — Flask integration
from flask import Flask, g, jsonify, request
from functools import wraps

app = Flask(__name__)

# Initialize RBAC
rbac = RBACFramework(db=get_db())

@app.before_request
def load_user():
    """Load user and permissions before each request."""
    user_id = session.get('user_id')
    if user_id:
        g.user_id = user_id
        g.user_permissions = rbac.get_user_permissions(user_id)
        g.user_roles = rbac.get_user_roles(user_id)

# --- Protected Routes ---

@app.route('/api/projects')
@require_permission('projects:read')
def list_projects():
    """Only users with projects:read can access."""
    projects = db.query("SELECT * FROM projects")
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
@require_permission('projects:create')
def create_project():
    """Only users with projects:create can access."""
    data = request.get_json()
    # Create project...
    return jsonify({'message': 'Project created'}), 201

@app.route('/api/projects/<id>/deploy', methods=['POST'])
@require_permission('projects:deploy')
def deploy_project(id):
    """Only users with projects:deploy can access."""
    # Deploy project...
    return jsonify({'message': 'Deployment started'})

@app.route('/api/users', methods=['DELETE')
@require_role('admin')
def delete_user(id):
    """Only admins can delete users."""
    # Delete user...
    return jsonify({'message': 'User deleted'})

@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Check permission dynamically."""
    user_id = g.get('user_id')
    
    if not rbac.check_permission(user_id, 'settings:update'):
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Update settings...
    return jsonify({'message': 'Settings updated'})

# --- Admin Routes ---

@app.route('/api/admin/roles', methods=['POST'])
@require_role('super_admin')
def create_role():
    """Only super_admin can create roles."""
    data = request.get_json()
    # Create role...
    return jsonify({'message': 'Role created'}), 201

@app.route('/api/admin/roles/<role_id>/permissions', methods=['POST'])
@require_role('super_admin')
def assign_permission_to_role(role_id):
    """Only super_admin can assign permissions to roles."""
    data = request.get_json()
    permission_id = data.get('permission_id')
    # Assign permission...
    return jsonify({'message': 'Permission assigned'})

@app.route('/api/admin/users/<user_id>/roles', methods=['POST'])
@require_role('admin')
def assign_role_to_user(user_id):
    """Admins can assign roles (with SSoD check)."""
    data = request.get_json()
    role_id = data.get('role_id')
    
    try:
        rbac.assign_role(user_id, role_id, granted_by=g.user_id)
        return jsonify({'message': 'Role assigned'})
    except SSoDViolation as e:
        return jsonify({'error': str(e)}), 400
```

---

## 9.7 Implementação em Go

### 9.7.1 Framework RBAC em Go

```go
// rbac/rbac.go — RBAC framework em Go
package rbac

import (
    "database/sql"
    "fmt"
    "sync"
    "time"
)

// Permission represents a system permission
type Permission struct {
    ID          string
    Name        string
    Resource    string
    Action      string
    Description string
}

// Role represents a system role
type Role struct {
    ID          string
    Name        string
    Description string
    Active      bool
}

// User represents a system user
type User struct {
    ID       string
    Username string
    Email    string
    Active   bool
}

// RBACService provides RBAC operations
type RBACService struct {
    db            *sql.DB
    cache         *sync.Map
    cacheTimeout  time.Duration
}

// NewRBACService creates a new RBAC service
func NewRBACService(db *sql.DB) *RBACService {
    return &RBACService{
        db:           db,
        cache:        &sync.Map{},
        cacheTimeout: 5 * time.Minute,
    }
}

// CheckPermission checks if a user has a specific permission
func (s *RBACService) CheckPermission(userID, permissionName string) (bool, error) {
    // Try cache
    cacheKey := fmt.Sprintf("%s:%s", userID, permissionName)
    if cached, ok := s.cache.Load(cacheKey); ok {
        return cached.(bool), nil
    }

    query := `
        WITH RECURSIVE role_tree AS (
            SELECT r.id
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = $1
            AND r.active = TRUE
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            
            UNION
            
            SELECT rh.parent_role_id
            FROM role_tree rt
            JOIN role_hierarchy rh ON rt.id = rh.child_role_id
        )
        SELECT EXISTS(
            SELECT 1
            FROM role_tree rt
            JOIN role_permissions rp ON rt.id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE p.name = $2
        )
    `

    var exists bool
    err := s.db.QueryRow(query, userID, permissionName).Scan(&exists)
    if err != nil {
        return false, fmt.Errorf("check permission: %w", err)
    }

    // Cache result
    s.cache.Store(cacheKey, exists)
    
    // Schedule cache invalidation
    go func() {
        time.Sleep(s.cacheTimeout)
        s.cache.Delete(cacheKey)
    }()

    return exists, nil
}

// GetUserPermissions returns all permissions for a user
func (s *RBACService) GetUserPermissions(userID string) (map[string]bool, error) {
    query := `
        WITH RECURSIVE role_tree AS (
            SELECT r.id
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = $1
            AND r.active = TRUE
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
            
            UNION
            
            SELECT rh.parent_role_id
            FROM role_tree rt
            JOIN role_hierarchy rh ON rt.id = rh.child_role_id
        )
        SELECT DISTINCT p.name
        FROM role_tree rt
        JOIN role_permissions rp ON rt.id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
    `

    rows, err := s.db.Query(query, userID)
    if err != nil {
        return nil, fmt.Errorf("get permissions: %w", err)
    }
    defer rows.Close()

    permissions := make(map[string]bool)
    for rows.Next() {
        var name string
        if err := rows.Scan(&name); err != nil {
            return nil, fmt.Errorf("scan permission: %w", err)
        }
        permissions[name] = true
    }

    return permissions, nil
}

// AssignRole assigns a role to a user
func (s *RBACService) AssignRole(userID, roleID, grantedBy string) error {
    // Check SSoD constraints
    if err := s.checkSSoD(userID, roleID); err != nil {
        return err
    }

    query := `
        INSERT INTO user_roles (user_id, role_id, granted_by)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id, role_id) DO NOTHING
    `

    _, err := s.db.Exec(query, userID, roleID, grantedBy)
    if err != nil {
        return fmt.Errorf("assign role: %w", err)
    }

    // Invalidate cache
    s.invalidateCache(userID)

    return nil
}

// RevokeRole revokes a role from a user
func (s *RBACService) RevokeRole(userID, roleID string) error {
    query := `DELETE FROM user_roles WHERE user_id = $1 AND role_id = $2`
    
    _, err := s.db.Exec(query, userID, roleID)
    if err != nil {
        return fmt.Errorf("revoke role: %w", err)
    }

    s.invalidateCache(userID)
    return nil
}

// checkSSoD checks Static Separation of Duty constraints
func (s *RBACService) checkSSoD(userID, roleID string) error {
    query := `
        SELECT EXISTS(
            SELECT 1
            FROM user_roles ur
            JOIN sod_constraints sc ON (
                (sc.role_a_id = ur.role_id AND sc.role_b_id = $2)
                OR
                (sc.role_b_id = ur.role_id AND sc.role_a_id = $2)
            )
            WHERE ur.user_id = $1
            AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
        )
    `

    var conflict bool
    err := s.db.QueryRow(query, userID, roleID).Scan(&conflict)
    if err != nil {
        return fmt.Errorf("check ssod: %w", err)
    }

    if conflict {
        return fmt.Errorf("SSoD violation: user %s cannot have role %s", userID, roleID)
    }

    return nil
}

// invalidateCache removes all cached permissions for a user
func (s *RBACService) invalidateCache(userID string) {
    s.cache.Range(func(key, value interface{}) bool {
        if k, ok := key.(string); ok {
            if len(k) > len(userID) && k[:len(userID)+1] == userID+":" {
                s.cache.Delete(key)
            }
        }
        return true
    })
}
```

### 9.7.2 Middleware RBAC em Go

```go
// rbac/middleware.go — HTTP middleware
package rbac

import (
    "context"
    "net/http"
    "strings"
)

type contextKey string

const (
    userIDKey       contextKey = "user_id"
    userPermissionsKey contextKey = "user_permissions"
)

// Middleware creates an RBAC middleware
func Middleware(rbac *RBACService) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Extract user ID from session/token
            userID := extractUserID(r)
            if userID == "" {
                http.Error(w, "Unauthorized", http.StatusUnauthorized)
                return
            }

            // Load user permissions
            permissions, err := rbac.GetUserPermissions(userID)
            if err != nil {
                http.Error(w, "Internal error", http.StatusInternalServerError)
                return
            }

            // Add to context
            ctx := context.WithValue(r.Context(), userIDKey, userID)
            ctx = context.WithValue(ctx, userPermissionsKey, permissions)
            
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}

// RequirePermission creates a middleware that requires a specific permission
func RequirePermission(rbac *RBACService, permission string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            userID := r.Context().Value(userIDKey).(string)
            
            hasPermission, err := rbac.CheckPermission(userID, permission)
            if err != nil {
                http.Error(w, "Internal error", http.StatusInternalServerError)
                return
            }

            if !hasPermission {
                http.Error(w, "Forbidden", http.StatusForbidden)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

// RequireRole creates a middleware that requires a specific role
func RequireRole(rbac *RBACService, roleNames ...string) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            userID := r.Context().Value(userIDKey).(string)
            
            permissions := r.Context().Value(userPermissionsKey).(map[string]bool)
            
            // Check if user has any of the required roles
            for _, roleName := range roleNames {
                rolePermission := fmt.Sprintf("role:%s", roleName)
                if permissions[rolePermission] {
                    next.ServeHTTP(w, r)
                    return
                }
            }

            http.Error(w, "Forbidden", http.StatusForbidden)
        })
    }
}

func extractUserID(r *http.Request) string {
    // Extract from session cookie, JWT, etc.
    cookie, err := r.Cookie("session")
    if err != nil {
        return ""
    }
    
    // Validate session and extract user ID
    // ...
    
    return "" // placeholder
}
```

---

## 9.8 Design de Hierarquias de Roles

### 9.8.1 Princípios de design

**Princípio 1: Hierarquia plana vs profunda**
Hierarquias profundas (>5 níveis) são difíceis de entender e manter. Prefira hierarquias planas com roles bem definidas.

```
BOM (plana):
  admin > manager > employee

RUIM (profunda):
  super_admin > regional_admin > dept_admin > team_lead > senior > mid > junior > intern
```

**Princípio 2: Separar roles funcionais de roles de seniority**
Em vez de criar roles para cada nível de seniority, use roles funcionais e ajuste permissões por projeto/departamento.

```sql
-- BOM: Roles funcionais
INSERT INTO roles (name) VALUES
    ('developer'),
    ('tech_lead'),
    ('architect'),
    ('devops'),
    ('security');

-- RUIM: Roles de seniority (role explosion)
INSERT INTO roles (name) VALUES
    ('junior_developer'),
    ('mid_developer'),
    ('senior_developer'),
    ('lead_developer'),
    ('principal_developer'),
    ('staff_developer');
```

**Princípio 3: Usar constraints em vez de roles adicionais**
Se um desenvolvedor não deve fazer deploy, use SSoD em vez de criar uma role "developer_sem_deploy".

### 9.8.2 Patterns de hierarquia

**Pattern 1: Organizacional**
Roles espelham a estrutura organizacional:

```
CEO > VP > Director > Manager > Employee
```

**Pattern 2: Funcional**
Roles baseadas em responsabilidades:

```
admin > manager > developer > viewer
```

**Pattern 3: Combinada**
Combina organizacional e funcional:

```
admin > manager > team_lead > developer
                           > designer
                           > qa
```

### 9.8.3 Anti-patterns

**Anti-pattern 1: Role per user**
Criar uma role para cada usuário:

```sql
-- ERRADO
INSERT INTO roles (name) VALUES
    ('joao_desenvolvedor'),
    ('maria_analista'),
    ('pedro_gerente');
```

Isso é equivalente a ACL e perde todas as vantagens do RBAC.

**Anti-pattern 2: Permission per user**
Atribuir permissões diretamente a usuários:

```sql
-- ERRADO
INSERT INTO user_permissions (user_id, permission_id)
SELECT u.id, p.id
FROM users u, permissions p
WHERE u.username = 'joao'
AND p.name = 'code:write';
```

Isso bypassa o modelo RBAC e torna a gestão impossível.

**Anti-pattern 3: Roles monolíticas**
Uma role que tem todas as permissões:

```sql
-- ERRADO
INSERT INTO roles (name) VALUES ('god_mode');

-- Todas as permissões para god_mode
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'god_mode';
```

Isso viola o princípio do menor privilege.

---

## 9.9 O Problema de Role Explosion

### 9.9.1 O que é role explosion

Role explosion ocorre quando o número de roles cresce exponencialmente em resposta a requisitos de permissão. Cada nova combinação de permissões gera uma nova role, tornando o sistema impossível de gerenciar.

**Exemplo clássico:**
- 5 departamentos (Eng, Vendas, Marketing, Financeiro, RH)
- 3 níveis de acesso (leitura, escrita, admin)
- 4 recursos (projetos, relatórios, configurações, usuários)

Sem role explosion: 5 + 3 + 4 = 12 roles
Com role explosion: 5 x 3 x 4 = 60 roles (cada combinação = uma role)

### 9.9.2 Soluções para role explosion

**Solução 1: RBAC + ABAC (Attribute-Based Access Control)**
Usar attributes em vez de roles para controlar acesso granular:

```python
# RBAC para roles base + ABAC para granularidade
class HybridRBAC:
    """RBAC with ABAC for fine-grained control."""
    
    def check_access(self, user_id: str, resource: str, 
                     action: str, context: dict = None) -> bool:
        """Check access using RBAC + ABAC."""
        # Check RBAC first
        if self.check_rbac(user_id, resource, action):
            return True
        
        # If RBAC fails, check ABAC attributes
        if context and self.check_abac(user_id, resource, action, context):
            return True
        
        return False
    
    def check_abac(self, user_id: str, resource: str,
                   action: str, context: dict) -> bool:
        """Check ABAC attributes."""
        user_attrs = self.get_user_attributes(user_id)
        resource_attrs = self.get_resource_attributes(resource)
        
        # Example policy: user can access own department's resources
        if (user_attrs.get('department') == resource_attrs.get('department')):
            return self.check_permission(user_id, f"{resource}:{action}")
        
        return False
```

**Solução 2: Permission inheritance**
Usar herança de permissões em vez de herança de roles:

```sql
-- Permission groups
CREATE TABLE permission_groups (
    id          UUID PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    parent_id   UUID REFERENCES permission_groups(id)
);

-- Permissions in groups
CREATE TABLE group_permissions (
    group_id    UUID REFERENCES permission_groups(id),
    permission_id UUID REFERENCES permissions(id),
    PRIMARY KEY (group_id, permission_id)
);

-- Roles reference groups, not individual permissions
CREATE TABLE role_permission_groups (
    role_id     UUID REFERENCES roles(id),
    group_id    UUID REFERENCES permission_groups(id),
    PRIMARY KEY (role_id, group_id)
);
```

**Solução 3: Context-aware roles**
Roles que mudam baseadas no contexto:

```python
# Dynamic role resolution
class ContextAwareRBAC:
    """RBAC with context-aware role resolution."""
    
    def resolve_roles(self, user_id: str, context: dict) -> list:
        """Resolve roles based on context."""
        base_roles = self.get_base_roles(user_id)
        
        # Add context-specific roles
        if context.get('is_admin_area'):
            if 'admin' in base_roles:
                base_roles.append('admin_context')
        
        if context.get('is_own_department'):
            base_roles.append('department_member')
        
        if context.get('time') == 'business_hours':
            base_roles.append('business_hours_user')
        
        return base_roles
```

---

## 9.10 RBAC vs ACL

### 9.10.1 Comparação detalhada

| Aspecto | RBAC | ACL |
|---------|------|-----|
| Modelo | Roles como intermediários | Permissões diretas |
| Escalabilidade | Alta (O(n+m)) | Baixa (O(n*m)) |
| Auditoria | Fácil (verificar roles) | Difícil (verificar cada entrada) |
| Gestão | Centralizada por role | Descentralizada por usuário |
| Flexibilidade | Menos flexível | Mais flexível |
| Performance | Mais lento (join) | Mais rápido (lookup direto) |
| Manutenção | Fácil (mudar role = mudar todos) | Difícil (mudar cada usuário) |
| Compatibilidade | Padrão enterprise | Padrão UNIX/filesystem |

### 9.10.2 Quando usar cada um

**Use RBAC quando:**
- Organização com estrutura clara de papéis
- Muitos usuários com permissões similares
- Auditoria é importante
- Gestão centralizada é desejada
- Compliance exige visibilidade

**Use ACL quando:**
- Poucos usuários com permissões muito específicas
- Recursos individuais com permissões únicas
- Sistema de arquivos ou APIs granulares
- Herança não é necessária
- Simplicidade é prioridade

**Use RBAC + ACL quando:**
- RBAC para controle base + ACL para exceções
- Exemplo: RBAC define acesso geral, ACL define acesso a arquivos específicos

---

## 9.11 Misantropi4: Excesso de Privilégios no IDAP

### 9.11.1 O problema de excessive privileges

O caso Misantropi4 revelou que o IDAP sofreu de excessive privileges — um problema clássico de RBAC mal implementado. Analisando o ataque:

**Vetor do ataque:**
1. Comprometimento de credenciais de um operador
2. Acesso a million de registros de cidadãos
3. Exfiltração de dados pessoais (CPF, nome, endereço, biometria)

**Root cause: excessive privileges**
O operador comprometido tinha acesso a TODOS os registros do sistema, não apenas aos registros que seu papel exigia. Isso é uma violação do princípio do menor privilege (least privilege).

### 9.11.2 Como RBAC teria prevenido o dano

Se o IDAP tivesse implementado RBAC com restrições adequadas:

**Nível 1 — RBAC básico:**
```sql
-- Roles do IDAP
INSERT INTO roles (name, description) VALUES
    ('operador_nivel_1', 'Atendimento ao cidadao'),
    ('operador_nivel_2', 'Consulta e edicao limitada'),
    ('supervisor', 'Gerenciamento de equipe'),
    ('administrador', 'Administracao do sistema'),
    ('auditor', 'Auditoria e logs');

-- Permissoes
INSERT INTO permissions (name, resource, action) VALUES
    ('cidadaos:read_own', 'cidadaos', 'read_own'),
    ('cidadaos:read_limited', 'cidadaos', 'read_limited'),
    ('cidadaos:read_all', 'cidadaos', 'read_all'),
    ('cidadaos:update_own', 'cidadaos', 'update_own'),
    ('cidadaos:update_limited', 'cidadaos', 'update_limited'),
    ('logs:read', 'logs', 'read'),
    ('reports:read', 'reports', 'read'),
    ('system:admin', 'system', 'admin');
```

**Nível 2 — RBAC com restrições de dado:**
```sql
-- Row-Level Security
ALTER TABLE cidadaos ENABLE ROW LEVEL SECURITY;

-- Operador nivel 1: apenas cidadaos do seu atendimento
CREATE POLICY operador_nivel_1_policy ON cidadaos
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM atendimentos a
            WHERE a.cidadao_id = cidadaos.id
            AND a.operador_id = current_user_id()
            AND a.status = 'em_atendimento'
        )
    );

-- Supervisor: cidadaos da sua equipe
CREATE POLICY supervisor_policy ON cidadaos
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM atendimentos a
            JOIN equipe_membros em ON a.operador_id = em.usuario_id
            WHERE a.cidadao_id = cidadaos.id
            AND em.supervisor_id = current_user_id()
        )
    );
```

**Nível 3 — SSoD e auditoria:**
```sql
-- Separacao de deveres
INSERT INTO sod_constraints (name, role_a_id, role_b_id) VALUES
    ('operador_supervisor', 
     (SELECT id FROM roles WHERE name = 'operador_nivel_1'),
     (SELECT id FROM roles WHERE name = 'supervisor')),
    ('operador_administrador',
     (SELECT id FROM roles WHERE name = 'operador_nivel_1'),
     (SELECT id FROM roles WHERE name = 'administrador'));

-- Auditoria de acesso
CREATE TABLE access_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    resource    VARCHAR(100) NOT NULL,
    action      VARCHAR(50) NOT NULL,
    cidadao_id  UUID,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Trigger para logar todo acesso a cidadaos
CREATE OR REPLACE FUNCTION log_cidadao_access()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO access_log (user_id, resource, action, cidadao_id, ip_address)
    VALUES (
        current_user_id(),
        TG_TABLE_NAME,
        TG_OP,
        COALESCE(NEW.id, OLD.id),
        inet_client_addr()
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_cidadao_select
    AFTER SELECT ON cidadaos
    FOR EACH ROW
    EXECUTE FUNCTION log_cidadao_access();
```

### 9.11.3 Impacto na resposta ao incidente

Com RBAC implementado, a resposta ao incidente Misantropi4 seria significativamente diferente:

**Sem RBAC (real):**
- Operador comprometido tinha acesso a 100% dos registros
- Dano: million de registros comprometidos
- Escopo: impossível determinar sem auditoria granular
- Remediação: desabilitar todas as contas de operadores

**Com RBAC (proposto):**
- Operador comprometido tinha acesso apenas aos seus atendimentos
- Dano: limitado aos registros do operador (centenas, não milhões)
- Escopo: determinado imediatamente via audit log
- Remediação: desabilitar apenas a conta comprometida

**Com RBAC + SSoD + Auditoria:**
- Operador comprometido não podia acessar dados sem atendimento ativo
- Operador não podia ter papel de admin e operador simultaneamente
- Todo acesso era logado com timestamp, IP, e ação
- Resposta ao incidente: minutos, não semanas

### 9.11.4 Recomendações para o IDAP

1. **Implementar RBAC com hierarquia**: Roles organizadas por nível de acesso e departamento
2. **Princípio do menor privilege**: Cada operador deve ter acesso apenas aos dados necessários para sua função
3. **Separation of Duties**: Um operador não deve poder criar e aprovar transações
4. **Row-Level Security**: Dados de cidadãos acessíveis apenas por atendimentos vinculados
5. **Auditoria completa**: Todo acesso a dados pessoais deve ser logado
6. **Revisão periódica**: Auditoria trimestral de permissões e acesso
7. **RBAC + FIDO2**: Combinar controle de acesso com autenticação forte (capítulo anterior)

---

## 9.12 RBAC em sistemas distribuídos

### 9.12.1 RBAC multi-tenant

Em sistemas multi-tenant, cada organização (tenant) tem suas próprias roles e permissões. O RBAC deve ser isolado por tenant para garantir que uma organização não acesse dados de outra.

```sql
-- Schema multi-tenant RBAC
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Roles são scoped por tenant
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, name)
);

-- Permissions são globais (não por tenant)
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) UNIQUE NOT NULL,
    resource    VARCHAR(100) NOT NULL,
    action      VARCHAR(50) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Role-Permission assignment é scoped por tenant
CREATE TABLE role_permissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(role_id, permission_id)
);

-- User-Role assignment é scoped por tenant
CREATE TABLE user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by  UUID REFERENCES users(id),
    granted_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,
    
    UNIQUE(tenant_id, user_id, role_id)
);

-- Indices multi-tenant
CREATE INDEX idx_roles_tenant ON roles(tenant_id);
CREATE INDEX idx_user_roles_tenant ON user_roles(tenant_id);
CREATE INDEX idx_user_roles_user_tenant ON user_roles(user_id, tenant_id);
```

```python
# Multi-tenant RBAC service
class MultiTenantRBAC:
    """RBAC service with tenant isolation."""
    
    def __init__(self, db):
        self.db = db
    
    def check_permission(self, tenant_id: str, user_id: str,
                        permission_name: str) -> bool:
        """Check permission within tenant scope."""
        result = self.db.query("""
            WITH RECURSIVE role_tree AS (
                SELECT r.id
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                AND ur.tenant_id = %s
                AND r.active = TRUE
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                
                UNION
                
                SELECT rh.parent_role_id
                FROM role_tree rt
                JOIN role_hierarchy rh ON rt.id = rh.child_role_id
                JOIN roles r2 ON rh.parent_role_id = r2.id
                WHERE r2.tenant_id = %s
            )
            SELECT EXISTS(
                SELECT 1
                FROM role_tree rt
                JOIN role_permissions rp ON rt.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE p.name = %s
            )
        """, (user_id, tenant_id, tenant_id, permission_name))
        
        return result[0][0]
    
    def create_tenant_role(self, tenant_id: str, name: str,
                          description: str = None) -> dict:
        """Create a role within a tenant."""
        # Check for duplicate within tenant
        existing = self.db.query("""
            SELECT id FROM roles 
            WHERE tenant_id = %s AND name = %s
        """, (tenant_id, name))
        
        if existing:
            return {'error': 'Role already exists in this tenant'}
        
        role_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO roles (id, tenant_id, name, description)
            VALUES (%s, %s, %s, %s)
        """, (role_id, tenant_id, name, description))
        
        return {'success': True, 'role_id': role_id}
    
    def assign_role_cross_tenant(self, user_id: str, 
                                 source_tenant: str,
                                 target_tenant: str,
                                 role_name: str) -> dict:
        """Assign a role from another tenant (cross-tenant access)."""
        # Get role from target tenant
        role = self.db.query("""
            SELECT id FROM roles 
            WHERE tenant_id = %s AND name = %s
        """, (target_tenant, role_name))
        
        if not role:
            return {'error': 'Role not found in target tenant'}
        
        # Assign with cross-tenant marker
        self.db.execute("""
            INSERT INTO user_roles 
            (tenant_id, user_id, role_id, granted_by)
            VALUES (%s, %s, %s, NULL)
            ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
        """, (target_tenant, user_id, role[0]['id']))
        
        return {'success': True, 'message': 'Cross-tenant role assigned'}
    
    def get_tenant_roles_summary(self, tenant_id: str) -> dict:
        """Get summary of roles and their usage in a tenant."""
        roles = self.db.query("""
            SELECT 
                r.name,
                r.description,
                COUNT(ur.user_id) as user_count,
                COUNT(rp.permission_id) as permission_count
            FROM roles r
            LEFT JOIN user_roles ur ON r.id = ur.role_id 
                AND ur.tenant_id = %s
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            WHERE r.tenant_id = %s AND r.active = TRUE
            GROUP BY r.id, r.name, r.description
            ORDER BY user_count DESC
        """, (tenant_id, tenant_id))
        
        return {
            'tenant_id': tenant_id,
            'roles': [{
                'name': r['name'],
                'description': r['description'],
                'users': r['user_count'],
                'permissions': r['permission_count'],
            } for r in roles]
        }
```

### 9.12.2 RBAC em microserviços

Em arquiteturas de microserviços, cada serviço pode ter seu próprio RBAC, ou pode haver um serviço centralizado de autorização.

**Pattern 1: Centralized authorization service**

```python
# Centralized authz service
class AuthorizationService:
    """Centralized authorization microservice."""
    
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
    
    def check_access(self, request: dict) -> dict:
        """Check if a request is authorized."""
        user_id = request['user_id']
        service = request['service']
        resource = request['resource']
        action = request['action']
        context = request.get('context', {})
        
        # Build cache key
        cache_key = f"authz:{user_id}:{service}:{resource}:{action}"
        
        # Try cache
        cached = self.cache.get(cache_key)
        if cached is not None:
            return {'allowed': cached == '1'}
        
        # Query database
        result = self._evaluate_policy(
            user_id, service, resource, action, context
        )
        
        # Cache result
        self.cache.setex(cache_key, 300, '1' if result['allowed'] else '0')
        
        return result
    
    def _evaluate_policy(self, user_id: str, service: str,
                        resource: str, action: str,
                        context: dict) -> dict:
        """Evaluate access policy."""
        # Check RBAC
        rbac_result = self._check_rbac(user_id, service, resource, action)
        
        if rbac_result['allowed']:
            return rbac_result
        
        # Check ABAC (attribute-based)
        abac_result = self._check_abac(user_id, service, resource, action, context)
        
        if abac_result['allowed']:
            return abac_result
        
        # Check resource-level policies
        resource_result = self._check_resource_policy(
            user_id, service, resource, action, context
        )
        
        return resource_result
    
    def _check_rbac(self, user_id: str, service: str,
                    resource: str, action: str) -> dict:
        """Check RBAC permissions."""
        permission_name = f"{service}:{resource}:{action}"
        
        result = self.db.query("""
            WITH RECURSIVE role_tree AS (
                SELECT r.id
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id = %s
                AND r.active = TRUE
                
                UNION
                
                SELECT rh.parent_role_id
                FROM role_tree rt
                JOIN role_hierarchy rh ON rt.id = rh.child_role_id
            )
            SELECT EXISTS(
                SELECT 1
                FROM role_tree rt
                JOIN role_permissions rp ON rt.id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE p.name = %s
            )
        """, (user_id, permission_name))
        
        return {'allowed': result[0][0], 'method': 'rbac'}
    
    def _check_abac(self, user_id: str, service: str,
                    resource: str, action: str,
                    context: dict) -> dict:
        """Check ABAC policies."""
        # Example: user can access own department's resources
        user_dept = self._get_user_attribute(user_id, 'department')
        resource_dept = context.get('department')
        
        if user_dept and resource_dept and user_dept == resource_dept:
            # Same department — check basic permission
            return self._check_rbac(user_id, service, resource, 'read')
        
        return {'allowed': False, 'method': 'abac'}
    
    def _check_resource_policy(self, user_id: str, service: str,
                              resource: str, action: str,
                              context: dict) -> dict:
        """Check resource-specific policies."""
        # Check if resource has custom ACL
        acl = self.db.query("""
            SELECT * FROM resource_acl
            WHERE service = %s AND resource = %s
            AND (user_id = %s OR user_id = '*')
        """, (service, resource, user_id))
        
        if acl:
            for entry in acl:
                if action in entry['allowed_actions']:
                    return {'allowed': True, 'method': 'resource_acl'}
        
        return {'allowed': False, 'method': 'resource_policy'}
```

**Pattern 2: Service-local RBAC with policy sync**

```python
# Service-local RBAC with periodic sync
class ServiceLocalRBAC:
    """RBAC that runs locally in each microservice."""
    
    def __init__(self, db, sync_interval=300):
        self.db = db
        self.sync_interval = sync_interval
        self.local_cache = {}
        self.last_sync = None
    
    async def sync_policies(self):
        """Periodically sync policies from central service."""
        while True:
            try:
                policies = await self.fetch_policies_from_central()
                self.local_cache = policies
                self.last_sync = datetime.utcnow()
            except Exception as e:
                logging.error(f"Policy sync failed: {e}")
            
            await asyncio.sleep(self.sync_interval)
    
    async def fetch_policies_from_central(self) -> dict:
        """Fetch all policies from central authz service."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{AUTHZ_SERVICE_URL}/api/policies',
                headers={'Authorization': f'Bearer {SERVICE_TOKEN}'}
            ) as response:
                return await response.json()
    
    def check_local(self, user_id: str, permission: str) -> bool:
        """Check permission against local cache."""
        cache_key = f"{user_id}:{permission}"
        
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # Fallback to database
        return self._check_database(user_id, permission)
```

### 9.12.3 RBAC com SCIM provisioning

SCIM (System for Cross-domain Identity Management) é o padrão para provisioning automático de identidades:

```python
# SCIM 2.0 integration for RBAC
class SCIMProvisioning:
    """SCIM 2.0 provisioning for RBAC."""
    
    def __init__(self, db, rbac):
        self.db = db
        self.rbac = rbac
    
    def provision_user(self, scim_user: dict) -> dict:
        """Provision a new user from SCIM."""
        # Extract user data
        user_data = {
            'external_id': scim_user.get('externalId'),
            'username': scim_user['userName'],
            'email': scim_user['emails'][0]['value'],
            'active': scim_user.get('active', True),
        }
        
        # Check if user exists
        existing = self.db.query(
            "SELECT id FROM users WHERE external_id = %s",
            (user_data['external_id'],)
        )
        
        if existing:
            return self.update_user(existing[0]['id'], scim_user)
        
        # Create user
        user_id = str(uuid.uuid4())
        self.db.execute("""
            INSERT INTO users (id, external_id, username, email, active)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            user_data['external_id'],
            user_data['username'],
            user_data['email'],
            user_data['active'],
        ))
        
        # Provision roles from SCIM groups
        for group in scim_user.get('groups', []):
            role = self._resolve_scim_group_to_role(group)
            if role:
                self.rbac.assign_role(user_id, role)
        
        return {'success': True, 'user_id': user_id}
    
    def deprovision_user(self, external_id: str) -> dict:
        """Deprovision a user from SCIM."""
        user = self.db.query(
            "SELECT id FROM users WHERE external_id = %s",
            (external_id,)
        )
        
        if not user:
            return {'error': 'User not found'}
        
        user_id = user[0]['id']
        
        # Deactivate user
        self.db.execute(
            "UPDATE users SET active = FALSE WHERE id = %s",
            (user_id,)
        )
        
        # Revoke all roles
        self.db.execute(
            "DELETE FROM user_roles WHERE user_id = %s",
            (user_id,)
        )
        
        # Invalidate cache
        self.rbac._invalidate_cache(user_id)
        
        return {'success': True, 'message': 'User deprovisioned'}
    
    def _resolve_scim_group_to_role(self, group: dict) -> str:
        """Map SCIM group to RBAC role."""
        # Mapping table
        GROUP_ROLE_MAP = {
            'Engineering': 'developer',
            'Management': 'manager',
            'Administration': 'admin',
            'Security': 'security',
            'Auditing': 'auditor',
        }
        
        group_display = group.get('display', '')
        return GROUP_ROLE_MAP.get(group_display)
    
    def sync_group_members(self, group_id: str, members: list) -> dict:
        """Sync group membership from SCIM."""
        role = self._resolve_scim_group_to_role({'display': group_id})
        
        if not role:
            return {'error': f'No role mapping for group {group_id}'}
        
        # Get current members
        current_members = self.db.query("""
            SELECT user_id FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE r.name = %s
        """, (role,))
        
        current_ids = {m['user_id'] for m in current_members}
        new_ids = set(members)
        
        # Add new members
        for user_id in new_ids - current_ids:
            self.rbac.assign_role(user_id, role)
        
        # Remove old members
        for user_id in current_ids - new_ids:
            self.rbac.revoke_role(user_id, role)
        
        return {
            'added': len(new_ids - current_ids),
            'removed': len(current_ids - new_ids),
        }
```

---

## 9.13 Checklist de Implementação

### Design:
- [ ] Definir roles baseadas em funções, não em pessoas
- [ ] Manter hierarquia plana (<5 níveis)
- [ ] Separar roles funcionais de roles de seniority
- [ ] Usar constraints SSoD/DSoD quando necessário
- [ ] Evitar role explosion com ABAC ou permission groups

### Implementação:
- [ ] Schema normalizado com tabelas separadas
- [ ] Índices em todas as foreign keys
- [ ] Queries recursivas para herança
- [ ] Cache de permissões para performance
- [ ] Invalidação de cache em mudanças

### Segurança:
- [ ] Princípio do menor privilege
- [ ] SSoD para roles conflitantes
- [ ] DSoD para sessões
- [ ] Auditoria de todas as mudanças de permissão
- [ ] Rate limiting em endpoints de administração
- [ ] Logging de tentativas de acesso negadas

### Operacional:
- [ ] Documentação de todas as roles e permissões
- [ ] Processo de review periódico de permissões
- [ ] Provisão automática (SCIM)
- [ ] Desprovisão automática (offboarding)
- [ ] Relatórios de uso de permissões
- [ ] Alertas para atividades incomuns

---

## 9.13 Resumo

RBAC é o modelo de autorização mais maduro e amplamente adotado. Ao definir permissões através de roles, RBAC simplifica a gestão de acesso, facilita auditoria, e suporta o princípio do menor privilege.

O modelo NIST define quatro níveis: Core RBAC (básico), Hierarchical RBAC (herança), Constrained RBAC (SSoD/DSoD), e Symmetric RBAC (review). Cada nível adiciona funcionalidade sem complicar excessivamente o modelo.

Para o caso Misantropi4, RBAC com restrições adequadas teria limitado significativamente o dano. Um operador com excessive privileges é um risco de segurança — RBAC resolve isso definindo scopes de acesso por papel, não por usuário.

RBAC não é perfeito: sofre de role explosion quando mal projetado, e pode ser combinado com ABAC para controle mais granular. Mas para a maioria dos sistemas, RBAC fornece o equilíbrio certo entre segurança, usabilidade, e manutenção.

## 9.14 RBAC e compliance regulatório

### 9.14.1 SOX (Sarbanes-Oxley) e RBAC

SOX exige controles de acesso rigorosos para sistemas financeiros. RBAC implementa separação de deveres e auditoria:

```python
# SOX compliance com RBAC
class SOXCompliance:
    """SOX compliance for financial systems using RBAC."""
    
    SOX_SEPARATION_RULES = {
        'financial_approval': {
            'description': 'Cannot approve own transactions',
            'constraint': {
                'role_a': 'transaction_initiator',
                'role_b': 'transaction_approver',
                'type': 'SSoD'
            }
        },
        'reconciliation': {
            'description': 'Cannot reconcile own accounts',
            'constraint': {
                'role_a': 'account_manager',
                'role_b': 'reconciliation_officer',
                'type': 'SSoD'
            }
        },
        'audit_independence': {
            'description': 'Auditor cannot modify audited data',
            'constraint': {
                'role_a': 'auditor',
                'role_b': 'data_modifier',
                'type': 'SSoD'
            }
        },
    }
    
    def validate_sox_access(self, user_id: str, 
                           transaction_type: str) -> dict:
        """Validate SOX compliance for financial transaction."""
        user_roles = self.get_user_roles(user_id)
        
        # Check SOX separation rules
        for rule_name, rule in self.SOX_SEPARATION_RULES.items():
            constraint = rule['constraint']
            
            role_a_users = self.get_users_with_role(constraint['role_a'])
            role_b_users = self.get_users_with_role(constraint['role_b'])
            
            if user_id in role_a_users and user_id in role_b_users:
                return {
                    'compliant': False,
                    'violation': rule_name,
                    'description': rule['description'],
                    'remediation': f'Revoke one of: '
                                 f'{constraint["role_a"]} or '
                                 f'{constraint["role_b"]}'
                }
        
        # Check transaction-specific rules
        if transaction_type == 'payment':
            return self._validate_payment_rules(user_id)
        elif transaction_type == 'journal_entry':
            return self._validate_journal_rules(user_id)
        
        return {'compliant': True}
    
    def _validate_payment_rules(self, user_id: str) -> dict:
        """Validate payment-specific SOX rules."""
        # Payment requires dual authorization
        approvers = self.get_users_with_role('payment_approver')
        
        if len(approvers) < 2:
            return {
                'compliant': False,
                'reason': 'SOX: Dual authorization required '
                         'for payments',
                'current_approvers': len(approvers),
                'required_approvers': 2
            }
        
        return {'compliant': True}
    
    def generate_sox_report(self) -> dict:
        """Generate SOX compliance report."""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'separation_violations': [],
            'access_summary': {},
            'recommendations': [],
        }
        
        # Check for separation violations
        for rule_name, rule in self.SOX_SEPARATION_RULES.items():
            users_with_both = self._find_users_with_both_roles(
                rule['constraint']['role_a'],
                rule['constraint']['role_b']
            )
            
            if users_with_both:
                report['separation_violations'].append({
                    'rule': rule_name,
                    'description': rule['description'],
                    'violating_users': users_with_both,
                })
        
        # Access summary
        report['access_summary'] = {
            'total_users': self._count_active_users(),
            'users_with_financial_access': self._count_financial_users(),
            'users_with_admin_access': self._count_admin_users(),
        }
        
        # Recommendations
        if report['separation_violations']:
            report['recommendations'].append(
                'URGENT: Separation of duties violations detected. '
                'Review and remediate immediately.'
            )
        
        return report
```

### 9.14.2 HIPAA e RBAC para dados de saúde

HIPAA (Health Insurance Portability and Accountability Act) requer controles de acesso rigorosos para dados de saúde. RBAC implementa minimum necessary access:

```python
# HIPAA compliance com RBAC
class HIPAACompliance:
    """HIPAA compliance for healthcare systems using RBAC."""
    
    HIPAA_ROLES = {
        'physician': {
            'description': 'Full access to patient records',
            'permissions': [
                'patient:read', 'patient:write',
                'prescription:read', 'prescription:write',
                'lab:read', 'lab:order',
            ]
        },
        'nurse': {
            'description': 'Read access, limited write',
            'permissions': [
                'patient:read', 'patient:vitals_write',
                'prescription:read',
                'lab:read',
            ]
        },
        'admin_staff': {
            'description': 'Demographic and billing only',
            'permissions': [
                'patient:demographics_read',
                'patient:demographics_write',
                'billing:read', 'billing:write',
            ]
        },
        'lab_tech': {
            'description': 'Lab results only',
            'permissions': [
                'patient:read_limited',
                'lab:read', 'lab:write',
            ]
        },
    }
    
    def validate_hipaa_access(self, user_id: str,
                             resource_type: str,
                             action: str) -> dict:
        """Validate HIPAA minimum necessary access."""
        user_roles = self.get_user_roles(user_id)
        
        # Check if user has minimum necessary access
        has_access = False
        
        for role_name in user_roles:
            role_perms = self.HIPAA_ROLES.get(role_name, {})
            permissions = role_perms.get('permissions', [])
            
            # Check exact permission
            if f'{resource_type}:{action}' in permissions:
                has_access = True
                break
            
            # Check wildcard permission
            if f'{resource_type}:*' in permissions:
                has_access = True
                break
        
        if not has_access:
            return {
                'allowed': False,
                'reason': 'HIPAA minimum necessary: '
                         'insufficient permissions',
                'user_roles': user_roles,
                'resource_type': resource_type,
                'action': action,
            }
        
        # Log access for audit trail
        self.log_hipaa_access(
            user_id=user_id,
            resource_type=resource_type,
            action=action,
            timestamp=datetime.utcnow()
        )
        
        return {'allowed': True}
    
    def log_hipaa_access(self, user_id: str,
                        resource_type: str, action: str,
                        timestamp: datetime):
        """Log access for HIPAA audit trail."""
        self.db.execute("""
            INSERT INTO hipaa_audit_log 
            (user_id, resource_type, action, timestamp, ip_address)
            VALUES (%s, %s, %s, %s, inet_client_addr())
        """, (user_id, resource_type, action, timestamp))
    
    def generate_hipaa_report(self) -> dict:
        """Generate HIPAA compliance report."""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'access_summary': {},
            'anomalies': [],
            'recommendations': [],
        }
        
        # Analyze access patterns
        access_stats = self.db.query("""
            SELECT 
                user_id,
                resource_type,
                COUNT(*) as access_count,
                MAX(timestamp) as last_access
            FROM hipaa_audit_log
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY user_id, resource_type
        """)
        
        report['access_summary'] = [{
            'user_id': stat['user_id'],
            'resource': stat['resource_type'],
            'access_count': stat['access_count'],
            'last_access': stat['last_access'].isoformat(),
        } for stat in access_stats]
        
        # Detect anomalies
        anomalies = self.db.query("""
            SELECT user_id, COUNT(*) as after_hours_count
            FROM hipaa_audit_log
            WHERE EXTRACT(HOUR FROM timestamp) NOT BETWEEN 8 AND 18
            AND timestamp > NOW() - INTERVAL '7 days'
            GROUP BY user_id
            HAVING COUNT(*) > 10
        """)
        
        report['anomalies'] = [{
            'user_id': a['user_id'],
            'type': 'after_hours_access',
            'count': a['after_hours_count'],
        } for a in anomalies]
        
        return report
```

### 9.14.3 GDPR e RBAC para dados da UE

GDPR (General Data Protection Regulation) exige consentimento e controle de acesso para dados de cidadãos da UE. RBAC implementa data governance:

```python
# GDPR compliance com RBAC
class GDPRCompliance:
    """GDPR compliance for EU data protection using RBAC."""
    
    def __init__(self, db):
        self.db = db
    
    def validate_gdpr_access(self, user_id: str,
                            data_subject_id: str,
                            processing_purpose: str) -> dict:
        """Validate GDPR access with purpose limitation."""
        # Check if user has role for this processing purpose
        user_roles = self.get_user_roles(user_id)
        
        purpose_roles = {
            'customer_service': ['support_agent', 'customer_manager'],
            'marketing': ['marketing_specialist', 'campaign_manager'],
            'analytics': ['data_analyst', 'data_scientist'],
            'legal_compliance': ['legal_officer', 'compliance_officer'],
        }
        
        required_roles = purpose_roles.get(processing_purpose, [])
        
        has_role = any(role in required_roles for role in user_roles)
        
        if not has_role:
            return {
                'allowed': False,
                'reason': 'GDPR: Purpose limitation — '
                         'user role not authorized for this purpose',
                'processing_purpose': processing_purpose,
                'user_roles': user_roles,
            }
        
        # Check consent
        consent = self.db.query("""
            SELECT * FROM consent_records
            WHERE data_subject_id = %s
            AND processing_purpose = %s
            AND granted = TRUE
            AND expires_at > NOW()
        """, (data_subject_id, processing_purpose))
        
        if not consent:
            return {
                'allowed': False,
                'reason': 'GDPR: No valid consent for '
                         'this processing purpose',
            }
        
        # Log access
        self.log_gdpr_access(
            user_id=user_id,
            data_subject_id=data_subject_id,
            purpose=processing_purpose
        )
        
        return {'allowed': True}
    
    def log_gdpr_access(self, user_id: str,
                       data_subject_id: str, purpose: str):
        """Log access for GDPR accountability."""
        self.db.execute("""
            INSERT INTO gdpr_access_log 
            (user_id, data_subject_id, purpose, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, data_subject_id, purpose))
    
    def handle_data_breach(self, affected_users: list) -> dict:
        """Handle GDPR data breach notification."""
        # Notify supervisory authority within 72 hours
        self.notify_authority(affected_users)
        
        # Notify affected data subjects
        for user_id in affected_users:
            user = self.db.query(
                "SELECT email, name FROM users WHERE id = %s",
                (user_id,)
            )
            
            if user:
                self.send_breach_notification(
                    email=user[0]['email'],
                    name=user[0]['name'],
                    breach_date=datetime.utcnow()
                )
        
        # Log breach
        self.db.execute("""
            INSERT INTO data_breaches 
            (affected_users, reported_at, authority_notified)
            VALUES (%s, NOW(), TRUE)
        """, (json.dumps(affected_users),))
        
        return {
            'success': True,
            'affected_count': len(affected_users),
            'authority_notified': True,
        }
```

### 9.14.4 LGPD e RBAC

LGPD (Lei Geral de Proteção de Dados) brasileira requer controles de acesso para dados pessoais:

```python
# LGPD compliance com RBAC
class LGPDCompliance:
    """LGPD compliance for Brazilian data protection."""
    
    LGPD_CATEGORIES = {
        'dados_pessoais': 'Personal data (name, email, CPF)',
        'dados_sensiveis': 'Sensitive data (health, biometrics)',
        'dados_financeiros': 'Financial data (bank, credit)',
        'dados_infantis': 'Children data (under 12)',
    }
    
    def validate_lgpd_access(self, user_id: str,
                            data_category: str,
                            processing_basis: str) -> dict:
        """Validate LGPD access with legal basis."""
        # Check user role for this data category
        user_roles = self.get_user_roles(user_id)
        
        category_roles = {
            'dados_pessoais': ['atendente', 'analista', 'gerente'],
            'dados_sensiveis': ['medico', 'psicologo', 'auditor'],
            'dados_financeiros': ['financeiro', 'tesoureiro'],
            'dados_infantis': ['pediatra', 'educador', 'assistente_social'],
        }
        
        required_roles = category_roles.get(data_category, [])
        
        has_role = any(role in required_roles for role in user_roles)
        
        if not has_role:
            return {
                'allowed': False,
                'reason': 'LGPD: Perfil nao autorizado para '
                         f'{data_category}',
            }
        
        # Check legal basis
        valid_bases = [
            'consentimento', 'obrigacao_legal', 'execucao_contrato',
            'protecao_vida', 'saude_publica', 'legitimo_interesse'
        ]
        
        if processing_basis not in valid_bases:
            return {
                'allowed': False,
                'reason': 'LGPD: Base legal invalida',
            }
        
        # Log access
        self.log_lgpd_access(
            user_id=user_id,
            data_category=data_category,
            basis=processing_basis
        )
        
        return {'allowed': True}
    
    def log_lgpd_access(self, user_id: str,
                       data_category: str, basis: str):
        """Log access for LGPD accountability."""
        self.db.execute("""
            INSERT INTO lgpd_access_log 
            (user_id, data_category, legal_basis, timestamp)
            VALUES (%s, %s, %s, NOW())
        """, (user_id, data_category, basis))
    
    def generate_lgpd_report(self) -> dict:
        """Generate LGPD compliance report."""
        report = {
            'gerado_em': datetime.utcnow().isoformat(),
            'categorias_dados': self.LGPD_CATEGORIES,
            'resumo_acessos': {},
            'alertas': [],
        }
        
        # Access summary by category
        stats = self.db.query("""
            SELECT data_category, COUNT(*) as access_count
            FROM lgpd_access_log
            WHERE timestamp > NOW() - INTERVAL '30 days'
            GROUP BY data_category
        """)
        
        report['resumo_acessos'] = {
            s['data_category']: s['access_count'] for s in stats
        }
        
        # Check for unusual access patterns
        anomalies = self.db.query("""
            SELECT user_id, data_category, COUNT(*) as count
            FROM lgpd_access_log
            WHERE timestamp > NOW() - INTERVAL '7 days'
            GROUP BY user_id, data_category
            HAVING COUNT(*) > 100
        """)
        
        for anomaly in anomalies:
            report['alertas'].append({
                'tipo': 'acesso_excessivo',
                'usuario': anomaly['user_id'],
                'categoria': anomaly['data_category'],
                'quantidade': anomaly['count'],
            })
        
        return report
```

---

*No próximo capítulo: ABAC (Attribute-Based Access Control) — controle de acesso baseado em atributos para cenários onde RBAC não é granular o suficiente.*
---

*[Capítulo anterior: 08 — Webauthn Fido2](08-webauthn-fido2.md)*
*[Próximo capítulo: 10 — Abac](10-abac.md)*
