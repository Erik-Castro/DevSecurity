# Capítulo 13 — Policy Engines

## 13.1 Conceitos de Engines de Política

### 13.1.1 O que são engines de política

Uma engine de política (policy engine) é um software que avalia regras declarativas contra dados de contexto para produzir decisões de autorização. Diferente de abordagens imperativas — onde a lógica de acesso é codificada diretamente em `if/else` espalhados por controllers e handlers — uma engine de política separa a lógica de autorização em um domínio dedicado, versionável, testável, e auditável.

A separação entre lógica de negócio e lógica de autorização é um dos princípios fundamentais de engenharia de software seguro. Quando a autorização vive dentro do código de aplicação, cada endpoint precisa reimplementar (ou copiar) a mesma lógica, o que cria consistência frágil, difícil de auditar, e propensa a erros. Uma engine de política centraliza essas decisões em um local que pode ser analisado, testado, e monitorado como um ativo de segurança de primeira classe.

O caso Misantropi4 demonstra o custo real da ausência de uma engine de política. O IDAP não possuía um mecanismo centralizado de autorização. As permissões eram definidas diretamente no código da aplicação, sem separação entre "quem pode acessar" e "o que o código faz." Quando credenciais foram comprometidas via credential stuffing, não havia uma camada intermediária que pudesse reavaliar o contexto da requisição e detectar que algo estava errado.

### 13.1.2 Por que engines de política importam

Em sistemas com centenas de endpoints, múltiplos microsserviços, e dezenas de papéis, a manutenção da lógica de autorização de forma descentralizada se torna insustentável. Cada mudança de requisito regulatório (LGPD, GDPR, HIPAA) requer atualização manual em múltiplos locais, cada um com sua própria sintaxe e convenções.

Engines de política resolvem isso oferecendo:

1. **Consistência**: Uma única fonte de verdade para regras de acesso.
2. **Separation of concerns**: Desenvolvedores focam em lógica de negócio; times de segurança definem políticas.
3. **Auditoria**: Cada decisão pode ser rastreada até uma política específica.
4. **Testabilidade**: Políticas são código que pode ser testado com cenários reais.
5. **Agilidade**: Mudanças de política podem ser implementadas sem redeploy da aplicação.
6. **Compliance**: Reguladores podem revisar políticas declarativas mais facilmente que código imperativo.

### 13.1.3 Taxonomia de engines de política

As engines de política se encaixam em diferentes categorias:

**Engines embutidas (embedded)**: Rodam como bibliotecas dentro da aplicação. Não requerem comunicação via rede. Exemplos: Casbin (Go), PyABAC (Python). São mais rápidas por evitar overhead de rede, mas acoplam a política ao ciclo de vida da aplicação.

**Engines como serviço (standalone)**: Rodam como processos ou microsserviços independentes. A aplicação consulta via API HTTP/gRPC. Exemplos: OPA, Cedar. Oferecem isolamento de processo e podem ser compartilhados entre múltiplas aplicações.

**Engines distribuídas**: Projetadas para ambientes de grande escala com replicação e consistência distribuída. Exemplos: Zanzibar/SpiceDB. Projetadas para bilhões de objetos e milhares de consultas por segundo.

### 13.1.4 O ciclo de decisão de autorização

Independentemente da engine escolhida, o ciclo de decisão segue um padrão comum:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Request   │────>│  Policy     │────>│  Decision   │
│   (subject, │     │  Engine     │     │  (ALLOW /   │
│   resource, │     │             │     │   DENY)     │
│   action)   │     │  + Context  │     │             │
└─────────────┘     │  (attributes│     └──────┬──────┘
                    │   + data)   │            │
                    └─────────────┘            │
                                               v
                                        ┌─────────────┐
                                        │  Audit Log  │
                                        │  + Metrics  │
                                        └─────────────┘
```

Cada componente do ciclo:
- **Subject**: Quem está solicitando acesso (usuário, serviço, processo).
- **Resource**: O que está sendo acessado (documento, API, banco de dados).
- **Action**: O que o sujeito quer fazer (ler, escrever, deletar, executar).
- **Context/Ambient attributes**: Condições ambientais (hora, IP, geolocalização, risco da sessão).
- **Decision**: O resultado da avaliação (ALLOW, DENY, ou indeterminado).
- **Audit**: Registro da decisão para compliance e investigação.

### 13.1.5 Modelos de autorização suportados

Engines de política modernas suportam múltiplos modelos de autorização, frequentemente combinando-os:

| Modelo | Descrição | Granularidade | Complexidade |
|--------|-----------|---------------|--------------|
| ACL | Access Control Lists | Baixa | Baixa |
| RBAC | Role-Based | Média | Média |
| ABAC | Attribute-Based | Alta | Alta |
| ReBAC | Relationship-Based | Alta | Média |
| hybrid | Combinações | Variável | Alta |

Uma engine de política madura permite que políticas de diferentes modelos coexistam. Uma aplicação pode usar RBAC para controle gross ("admin pode acessar tudo") e ABAC para controle fino ("só acessa durante horário comercial se o risco da sessão for baixo").

---

## 13.2 OPA (Open Policy Agent) com Linguagem Rego

### 13.2.1 Visão geral do OPA

Open Policy Agent (OPA) é uma engine de política general-purpose criada pela Styra e graduada como projeto CNCF (Cloud Native Computing Foundation). OPA é projetado para offload decisões de autorização de aplicações, tornando-as declarativas, testáveis, e auditáveis.

OPA usa a linguagem **Rego** para definir políticas. Rego é uma linguagem declarativa inspirada em Datalog, projetada especificamente para consultar e transformar dados estruturados. Diferente de linguagens imperativas, Rego expressa "o que deve ser verdade" em vez de "como calcular se é verdade."

O caso Misantropi4 poderia ter sido mitigado com OPA implementado como camada de autorização. Uma política Rego poderia ter verificado:

1. A origem da requisição (IP, geolocalização).
2. O padrão de acesso (número de registros acessados por minuto).
3. A combinação de papel + horário + localização.
4. Se o captcha foi validado corretamente.
5. Se MFA foi completado para a sessão.

Qualquer uma dessas verificações, implementada como política Rego, teria bloqueado ou sinalizado o ataque antes que danos significativos ocorressem.

### 13.2.2 Arquitetura do OPA

OPA pode operar em dois modos:

**Modo embutido (in-process)**: OPA roda como biblioteca dentro da aplicação. Não há comunicação via rede. Ideal para latência mínima e cenários onde a política é avaliada a cada chamada de função.

**Modo sidecar/serviço**: OPA roda como processo separado (container, daemon). A aplicação consulta via REST API ou gRPC. Ideal para microsserviços onde múltiplas aplicações compartilham a mesma engine.

```
┌──────────────┐         ┌──────────────┐
│  Aplicação   │  HTTP   │  OPA Server  │
│  (Go/Python/ │───────>│  :8181       │
│   Node/etc)  │  POST   │              │
│              │<───────│  v1/data/    │
│              │  JSON   │  policy/     │
└──────────────┘         └──────┬───────┘
                                │
                         ┌──────┴───────┐
                         │  Rego Policy │
                         │  + Input     │
                         │  + Data      │
                         └──────────────┘
```

A API principal do OPA:

```bash
# Avaliar política
POST /v1/data/{policy_path}
Content-Type: application/json

{
  "input": {
    "principal": {"id": "user:123", "role": "admin"},
    "action": "read",
    "resource": {"type": "document", "id": "doc-456"}
  }
}

# Resposta
{
  "result": true
}
```

### 13.2.3 Sintaxe básica de Rego

Rego opera sobre dados JSON. Políticas são funções que aceitam `input` (a requisição atual) e `data` (estado global) e retornam `true` (permitido) ou `false` (negado).

**Exemplo básico — quem pode ler um documento:**

```rego
package authz

default allow = false

allow {
    input.principal.role == "admin"
}

allow {
    input.principal.id == input.resource.owner_id
    input.action == "read"
}

allow {
    input.principal.role == "editor"
    input.action == "read"
    input.resource.project_id == input.principal.project_id
}
```

Cada bloco `allow { ... }` é uma regra independente. Se QUALQUER regra retornar `true`, o resultado final é `allow = true`. Se nenhuma retornar `true`, `default allow = false` se aplica.

**Compostos e conjuntos:**

```rego
package authz

# Define permissões por role
role_permissions := {
    "admin": {
        "actions": ["read", "write", "delete", "admin"],
    },
    "editor": {
        "actions": ["read", "write"],
    },
    "viewer": {
        "actions": ["read"],
    },
}

# Verifica se a role do sujeito permite a ação
allow {
    role := input.principal.role
    permissions := role_permissions[role]
    input.action in permissions.actions
}
```

**Variáveis e iteração:**

```rego
package authz

# Verifica se o usuário tem acesso a algum projeto do recurso
allow {
    some project_id in input.principal.project_ids
    input.resource.project_id == project_id
    input.action == "read"
}

# Conta quantos registros o usuário acessou nesta sessão
record_count := count([r |
    r := data.access_log[_]
    r.user_id == input.principal.id
    r.timestamp > time.now_ns() - (3600 * 1000000000)  # ultima hora
])

# Bloqueia se acessar mais de 1000 registros por hora
deny {
    record_count > 1000
}
```

### 13.2.4 Rego avançado — funções, partial rules, e complementos

**Funções em Rego:**

```rego
package authz

# Funcao auxiliar para normalizar nomes
normalize_name(name) = lower(trim_space(name)) {
    true
}

# Funcao que verifica se dois timestamps estao no mesmo dia
same_day(ts1, ts2) {
    date1 := time.clock(ts1)
    date2 := time.clock(ts2)
    date1[0] == date2[0]
    date1[1] == date2[1]
    date1[2] == date2[2]
}

# Funcao com valor de retorno
is_business_hours(timestamp) = result {
    clock := time.clock(timestamp)
    hour := clock[0]
    hour >= 8
    hour < 18
    result := true
} else = result {
    result := false
}
```

**Partial rules (regras parciais):**

```rego
package authz

# Partial rules constroem conjuntos ou objetos dinamicamente
# Cada "match" gera um elemento no conjunto resultante

# Quem pode acessar um resource
editors[editor_id] {
    some editor_id
    data.project_members[editor_id].role == "editor"
    data.project_members[editor_id].project_id == input.resource.project_id
}

# Regra composta usando partial rules
allow {
    count(editors) > 0
    input.principal.id in editors
}
```

**Complementos (else):**

```rego
package authz

default allow = false

allow {
    input.action == "read"
    is_public_resource
}

allow {
    input.action == "read"
    is_authenticated
    has_permission("read")
}

allow {
    input.action == "write"
    is_authenticated
    has_permission("write")
}

# Funcoes auxiliares
is_public_resource {
    input.resource.visibility == "public"
}

is_authenticated {
    input.principal.id != ""
}

has_permission(perm) {
    some p
    p := data.role_permissions[input.principal.role][_]
    p == perm
}
```

### 13.2.5 OPA com dados estruturados

OPA é especialmente poderoso quando avalia políticas contra dados complexos. O parâmetro `data` do OPA pode conter qualquer estrutura JSON — listas de usuários, relações de projeto, configurações de organização.

```bash
# Carregar dados no OPA
PUT /v1/data/authz
{
    "roles": {
        "admin": ["read", "write", "delete"],
        "editor": ["read", "write"],
        "viewer": ["read"]
    },
    "users": {
        "user:001": {
            "role": "admin",
            "organization": "org:acme"
        },
        "user:002": {
            "role": "editor",
            "organization": "org:acme"
        }
    },
    "resources": {
        "doc:001": {
            "organization": "org:acme",
            "classification": "confidential"
        }
    }
}
```

**Política que usa dados:**

```rego
package authz

default allow = false

# Admin pode tudo na propria organizacao
allow {
    data.users[input.principal.id].role == "admin"
    data.users[input.principal.id].organization == data.resources[input.resource.id].organization
}

# Editor pode ler/editar documentos da propria organizacao
allow {
    data.users[input.principal.id].role == "editor"
    data.users[input.principal.id].organization == data.resources[input.resource.id].organization
    input.action in ["read", "write"]
}

# Qualquer um pode ler documentos publicos
allow {
    data.resources[input.resource.id].visibility == "public"
    input.action == "read"
}
```

### 13.2.6 Bundle API — distribuição de políticas

OPA suporta a distribuição de políticas e dados via Bundle API. Um bundle é um arquivo tarball (`.tar.gz`) contendo arquivos `.rego` (políticas) e `.json` (dados) que OPA baixa periodicamente de um servidor HTTP.

```
┌─────────────┐     HTTP GET     ┌─────────────────┐
│             │────────────────>│  Policy Server   │
│     OPA     │   /bundles/     │  (S3, GCS,      │
│  (Sidecar)  │                 │   HTTP server)   │
│             │<────────────────│                  │
│             │   tarball       │                  │
└─────────────┘                 └─────────────────┘
```

O Bundle API garante que todas as instâncias de OPA em um cluster recebam as mesmas políticas, com hash para detecção de alterações e polling configurável.

### 13.2.7 Limitações do OPA

Apesar de ser a engine de política de referência no ecossistema cloud-native, OPA tem limitações:

- **Curva de aprendizado de Rego**: A sintaxe de Rego, embora poderosa, tem uma curva de aprendizado significativa para desenvolvedores não familiarizados com Datalog.
- **Performance com grandes datasets**: Políticas que operam sobre grandes conjuntos de dados podem ter latência elevada sem indexação adequada.
- **Gerenciamento de estado**: OPA é stateless; dados devem ser carregados externamente ou via bundles.
- **Falta de relações nativas**: OPA não suporta consultas sobre relações (como "quem é membro do time do dono do documento") nativamente — requer modeling via dados ou funções.
- **Debugging**: Ferramentas de debug de Rego são limitadas comparadas a linguagens mainstream.

---

## 13.3 Cedar — AWS Authorization

### 13.3.1 Visão geral do Cedar

Cedar é uma linguagem de política de autorização criada pela Amazon Web Services (AWS) e open-sourced em 2022. Cedar foi projetada para ser uma linguagem de política segura por construção — com type safety, sandboxing, e determinismo garantido.

Enquanto Rego é uma linguagem general-purpose (que pode expressar qualquer computação), Cedar é intencionalmente restrita. Cedar não permite side effects, loops infinitos, ou acesso a estado externo. Essa restrição é uma Feature — garante que políticas sejam sempre terminantes, deterministas, e seguras.

O Cedar é usado internamente na AWS para serviços como AWS Verified Permissions, AWS S3 Access Points, e AWS IAM. Em 2024, a AWS lançou o **Cedar Planner**, um algoritmo de resolução de políticas que suporta policy reconciliation e minimization.

### 13.3.2 Modelo de dados Cedar

Cedar opera sobre três tipos de entidades:

1. **Principal**: Quem está solicitando (equivalente a "subject" em outros modelos).
2. **Action**: O que o principal quer fazer.
3. **Resource**: O alvo da ação.

Cada entidade é representada como um **Entity** com um tipo e um namespace:

```
User::"alice"
Role::"admin"
Resource::"document123"
Action::"read"
```

**Políticas Cedar são escritas em sintaxe own:**

```cedar
permit(
    principal == User::"alice",
    action == Action::"read",
    resource == Resource::"document123"
);

permit(
    principal in Role::"admin",
    action in [Action::"read", Action::"write"],
    resource in Album::"family-photos"
);

forbid(
    principal,
    action == Action::"delete",
    resource
);
```

### 13.3.3 Tipos e namespaces Cedar

Cedar usa tipos para dar estrutura às entidades:

```cedar
namespace MyNamespace {

    entity User {
        "email": String,
        "role": String,
        "organization": String,
        "clearanceLevel": Long,
    };

    entity Role {
        "permissions": Set<String>,
    };

    entity Resource {
        "owner": User,
        "classification": String,
        "org": String,
    };

    entity Album {
        "owner": User,
        "public": Bool,
        "sharedWith": Set<User>,
    };

    action Read;
    action Write;
    action Delete;
    action Admin;
}
```

### 13.3.4 Sintaxe de políticas Cedar

Cedar suporta `permit` e `forbid` policies:

**Permit policies:**

```cedar
// Permitir leitura em documentos publicos
permit(
    principal,
    action == Action::"read",
    resource in Album::"public-album"
) when {
    resource.public == true
};

// Permitir ao dono acessar seus proprios documentos
permit(
    principal,
    action in [Action::"read", Action::"write"],
    resource
) when {
    resource.owner == principal
};

// Permitir a admins de uma organizacao
permit(
    principal,
    action,
    resource
) when {
    principal.role == "admin"
    principal.organization == resource.org
};
```

**Forbid policies (sempre prevalecem sobre permit):**

```cedar
// Proibir deletar documentos classificados
forbid(
    principal,
    action == Action::"delete",
    resource
) when {
    resource.classification == "confidential"
};

// Proibir acesso a documentos de outra organizacao
forbid(
    principal,
    action,
    resource
) when {
    principal.organization != resource.org
};
```

**Regra de resolução**: Se existe `forbid` aplicável, a decisão é DENY. Caso contrário, se existe `permit` aplicável, a decisão é ALLOW. Se não existe nenhuma política aplicável, a decisão é DENY (default deny).

### 13.3.5 Cedar e AWS Verified Permissions

AWS Verified Permissions é o serviço managed que usa Cedar. Ele fornece:

- **Policy Store**: Armazenamento centralizado de políticas Cedar.
- **Identity Provider**: Integração com Amazon Cognito, SAML, OIDC.
- **API de avaliação**: A API `IsAuthorized` aceita principal, action, resource e retorna ALLOW/DENY.
- **Schema validation**: Valida que entidades e ações seguem o schema definido.

```python
import boto3

client = boto3.client('verifiedpermissions')

response = client.is_authorized(
    policyStoreId='PSEXAMPLE123EXAMPLE',
    principal={
        'entityType': 'User',
        'entityId': 'alice'
    },
    action={
        'actionType': 'MyNamespace',
        'actionId': 'read'
    },
    resource={
        'entityType': 'Resource',
        'entityId': 'doc123'
    }
)

print(response['decision'])  # ALLOW ou DENY
print(response['determiningPolicies'])  # Quais politicas determinaram a decisao
```

### 13.3.6 Cedar Planner — reconciliação e minimização

O Cedar Planner (2024) introduz duas capacidades:

**Policy Reconciliation**: Dado um conjunto de políticas e uma intenção desejada ("alice deve poder ler doc123 mas não deletar"), o planner identifica políticas conflitantes e sugere resoluções.

**Policy Minimization**: Dado um conjunto de políticas, o planner gera o conjunto mínimo equivalente — reduzindo superfície de ataque e complexidade de auditoria.

### 13.3.7 Vantagens e limitações do Cedar

**Vantagens:**
- Segurança por construção (type safety, sandboxing, determinismo).
- Sintaxe simples e legível.
- Default deny (fail-closed).
- Suporte a tipos e namespaces.
- Ferramenta de reconciliação (Planner).
- Open source (Apache 2.0).

**Limitações:**
- Não suporta lógica quantificacional complexa (para todo, existe).
- Não possui engine própria de avaliação para uso local (requer Verified Permissions ou bibliotecas open source).
- Ecossistema ainda menor que OPA.
- Não suporta atualização dinâmica de dados (sem Bundle API equivalente).
- Sem suporte nativo a relações (modelagem requer tipos customizados).

---

## 13.4 Casbin — Multi-Model Authorization

### 13.4.1 Visão geral do Casbin

Casbin é uma biblioteca de autorização open source (Apache 2.0) escrita em Go, com bindings para Python, Java, Node.js, C++, Rust, e outras linguagens. Casbin se destaca por suportar múltiplos modelos de acesso (ACL, RBAC, ABAC, ReBAC) em uma única API.

Enquanto OPA usa Rego e Cedar usa sua própria sintaxe, Casbin usa um sistema de **model files** (definem o modelo) e **policy files** (definem as regras). Essa separação permite que o mesmo motor de avaliação aplique diferentes modelos de autorização sem alteração de código.

O caso Misantropi4 poderia ter beneficiado do Casbin pela facilidade de combinar modelos. O IDAP poderia usar RBAC para controle básico ("operador X pode acessar endpoint Y") e ABAC para controle contextual ("só durante horário comercial, só a partir de IPs whitelistados, no máximo N registros por hora").

### 13.4.2 Arquitetura do Casbin

```
┌──────────────────┐     ┌──────────────────┐
│  Model File      │     │  Policy File     │
│  (model.conf)    │     │  (policy.csv)    │
│                  │     │                  │
│  - Request       │     │  - Permissoes    │
│  - Policy        │     │  - Roles         │
│  - Matchers      │     │  - Restricoes    │
│  - Effect        │     │                  │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         └──────────┬─────────────┘
                    │
         ┌──────────┴──────────┐
         │   Casbin Enforcer   │
         │   (motor avaliacao) │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │   Adapter           │
         │   (MySQL, PG, etc.) │
         └─────────────────────┘
```

### 13.4.3 Model file — definindo o modelo

O model file define como as requisições são mapeadas para decisões:

```ini
# model.conf - RBAC basico
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

**Explicação dos campos:**
- `request_definition`: Define os parâmetros da requisição (sujeito, objeto, ação).
- `policy_definition`: Define os parâmetros da política.
- `role_definition`: Define hierarquias de papel (g = role assignment).
- `policy_effect`: Define como múltiplas políticas são combinadas.
- `matchers`: Define a lógica de correspondência entre requisição e política.

### 13.4.4 ACL com Casbin

```ini
# model.conf - ACL
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.sub == p.sub && r.obj == p.obj && r.act == p.act
```

**Policy file (policy.csv):**

```csv
p, alice, document1, read
p, alice, document1, write
p, bob, document2, read
p, bob, document2, write
p, charlie, document1, read
```

### 13.4.5 RBAC com Casbin

```ini
# model.conf - RBAC com herdabilidade
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _
g2 = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = (g(r.sub, p.sub) || g2(r.sub, p.sub)) && r.obj == p.obj && r.act == p.act
```

**Policy:**

```csv
p, admin, *, *
p, editor, document, read
p, editor, document, write
p, viewer, document, read

g, alice, admin
g, bob, editor
g, charlie, viewer
g, dave, editor
g, dave, viewer
```

**Avaliação:**
- alice (admin) → pode tudo: `g(alice, admin)` → `p(admin, *, *)`
- bob (editor) → pode ler e escrever: `g(bob, editor)` → `p(editor, document, read/write)`
- charlie (viewer) → pode ler: `g(charlie, viewer)` → `p(viewer, document, read)`

### 13.4.6 ABAC com Casbin

```ini
# model.conf - ABAC
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub_rule, obj, act

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = eval(p.sub_rule) && r.obj == p.obj && r.act == p.act
```

**Policy com expressões ABAC:**

```csv
p, r.sub.age > 18, document, read
p, r.sub.department == r.obj.department, document, write
p, r.sub.role == "admin", *, *
```

### 13.4.7 ReBAC com Casbin

```ini
# model.conf - ReBAC
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, rel, obj

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = r.obj in r.sub | r.rel && r.act == "read"
```

**Policy definindo relações:**

```csv
p, alice, owner, document1
p, bob, editor, document1
p, charlie, viewer, document1
p, alice, owner, project1
p, document1, parent, project1
```

### 13.4.8 Casbin com adaptadores persistentes

Casbin suporta múltiplos backends de persistência:

```python
import casbin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adaptador MySQL
e = casbin.Enforcer('model.conf', 'mysql://user:pass@localhost/db')

# Adaptador PostgreSQL
e = casbin.Enforcer('model.conf', 'postgres://user:pass@localhost/db')

# Adaptador Redis
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
e = casbin.Enforcer('model.conf', r)

# Avaliar
allowed = e.enforce("alice", "document1", "read")
print(allowed)  # True ou False

# Gerenciar politicas via API
e.add_policy("admin", "*", "*")
e.remove_policy("admin", "*", "*")

# Gerenciar roles
e.add_grouping_policy("alice", "admin")
e.remove_grouping_policy("alice", "admin")
```

### 13.4.9 Casbin com middleware de frameworks web

```python
# Flask + Casbin
from flask import Flask, request, jsonify
from functools import wraps
import casbin

app = Flask(__name__)
enforcer = casbin.Enforcer('model.conf', 'policy.csv')

def require_permission(resource_type, action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            resource = kwargs.get('id', resource_type)
            
            if not enforcer.enforce(user, resource, action):
                return jsonify({'error': 'Forbidden'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/documents/<int:id>')
@require_permission('document', 'read')
def get_document(id):
    return jsonify({'document': f'document_{id}'})

@app.route('/documents/<int:id>', methods=['PUT'])
@require_permission('document', 'write')
def update_document(id):
    return jsonify({'status': 'updated'})
```

### 13.4.10 Limitações do Casbin

- **Performance**: Avaliação de expressões ABAC dinâmicas pode ser lenta para altas taxas de throughput.
- **Escalabilidade**: Casbin é uma biblioteca, não um serviço distribuído — para escala horizontal, cada instância mantém sua própria cópia das políticas.
- **Consistência**: Sincronização de políticas entre múltiplas instâncias requer implementação customizada.
- **Complexidade de modelos ABAC**: Expressões ABAC complexas são difíceis de testar e debugar.
- **Ausência de audit logging nativo**: O audit trail precisa ser implementado na camada da aplicação.

---

## 13.5 Google Zanzibar e SpiceDB

### 13.5.1 O modelo Zanzibar

Google Zanzibar é o sistema de autorização global do Google, usado por Google Drive, YouTube, Google Cloud IAM, e Gmail. O paper "Zanzibar: Google's Consistent, Global Authorization System" (2019) descreve o sistema que processa bilhões de consultas por segundo com latência média de poucos milissegundos.

Zanzibar é baseado em **relationship-based access control** (ReBAC), onde o acesso é determinado por relações entre entidades: "Alice é editor do Documento X", "Documento X pertence ao Projeto Y", "Projeto Y está na Organização Z."

### 13.5.2 Conceitos fundamentais do Zanzibar

**Namespaces**: Cada tipo de entidade (documento, projeto, organização) é um namespace com relações definidas.

**Relations**: Conexões entre entidades. Exemplo: `document:readme#viewer@user:alice`.

**Usersets**: Expressões que computam o conjunto de usuários que têm uma relação com um objeto. Exemplo: `document:readme#viewer` pode ser computado como os usuários que são `editor` OU os usuários que estão na `organization` que contém o `project` que contém o `document`.

**Tuples**: Triples `(object, relation, user)` que representam fatos. Exemplo: `(document:readme, editor, user:alice)`.

```
Namespace: document
  relations:
    - editor
    - viewer
    - owner

Namespace: project
  relations:
    - member
    - owner

Namespace: organization
  relations:
    - member
    - owner

Rewrite rules (userset rewrite):
  document#viewer = document#editor OR project#member->document
  document#viewer = organization#member->project->document (traversal)
```

### 13.5.3 SpiceDB — open source Zanzibar

SpiceDB (Authzed) é a implementação open source do modelo Zanzibar. SpiceDB replica a arquitetura do Zanzibar com:

- **Consistency guarantees**: Serializable consistency para consultas.
- **Namespace definitions**: Linguagem own para definir namespaces e relações.
- **API gRPC**: Interface de alta performance.
- **Cluster mode**: Replicação com Raft para alta disponibilidade.

**Definição de schema no SpiceDB:**

```zed
definition user {}

definition organization {
    relation member: user
    relation admin: user
    relation owner: user
}

definition project {
    relation org: organization
    relation member: user
    relation owner: user
    
    permission view = member + org->member
    permission edit = owner + org->admin
}

definition document {
    relation project: project
    relation owner: user
    relation editor: user
    
    permission view = editor + project->view
    permission edit = owner + project->edit
    permission delete = owner
}

definition folder {
    relation parent: folder
    relation project: project
    relation editor: user
    
    permission view = editor + project->view
    permission edit = editor + project->edit
    permission create_document = edit
}
```

**Operações no SpiceDB:**

```bash
# Criar relacoes
zed relationship write document:readme editor user:alice
zed relationship write document:readme project project:devdocs
zed relationship write project:devdocs org organization:acme
zed relationship write organization:acme member user:bob

# Consultar relacoes
zed relationship read document:readme#viewer
# Resultado: user:alice, user:bob (via project->org->member)

# Verificar permissao especifica
zed permission check document:readme view user:alice
# Resultado: true

zed permission check document:readme view user:charlie
# Resultado: false

# Listar todos os recursos que um usuario pode acessar
zed permission lookup-resources document view user:alice
# Resultado: document:readme, document:guide, ...
```

### 13.5.4 SpiceDB com aplicação Python

```python
from authzed.api.v1 import (
    Client,
    WriteRelationshipsRequest,
    ReadRelationshipsRequest,
    CheckPermissionRequest,
    LookupResourcesRequest,
)
import grpc

# Conectar ao SpiceDB
client = Client(
    client=grpc.insecure_channel("localhost:50051"),
    preshared_key="your_api_key",
    lease=Client.new_lease(),
)

# Escrever relacoes
await client.write_relationships(WriteRelationshipsRequest(
    updates=[
        RelationshipUpdate(
            operation=RelationshipUpdate.Operation.CREATE,
            relationship=Relationship(
                resource=ObjectReference(object_type="document", object_id="readme"),
                relation="editor",
                subject=ObjectReference(object_type="user", object_id="alice"),
            ),
        ),
    ],
))

# Verificar permissao
response = await client.check_permission(CheckPermissionRequest(
    resource=ObjectReference(object_type="document", object_id="readme"),
    permission="view",
    subject=ObjectReference(object_type="user", object_id="alice"),
))
print(response.permitted)  # True

# Listar recursos acessiveis
async for result in client.lookup_resources(LookupResourcesRequest(
    resource_object_type="document",
    permission="view",
    subject=ObjectReference(object_type="user", object_id="alice"),
)):
    print(result.resource.object_id)
```

### 13.5.5 Comparação Zanzibar vs OPA vs Casbin

| Critério | Zanzibar/SpiceDB | OPA | Casbin |
|----------|-------------------|-----|--------|
| Modelo primário | ReBAC | ABAC/Datalog | Multi-model |
| Linguagem | Schema (zed) | Rego | model.conf + policy.csv |
| Escalabilidade | Bilhões de tuples | Milhares de queries/s | Limitada (in-process) |
| Consistency | Serializable | Eventual (bundles) | In-memory |
| Complexidade operacional | Alta | Média | Baixa |
| Uso típico | Google-scale apps | Cloud-native/Microservices | Apps monolíticas |
| Audit trail | Nativo | Via plugins | Manual |
| Latência | < 5ms (p99) | < 10ms | < 1ms (in-process) |

### 13.5.6 Quando usar Zanzibar/SpiceDB

Zanzibar/SpiceDB é ideal quando:
- O modelo de acesso é naturalmente relacional ("usuário X é membro do time Y que tem acesso ao projeto Z").
- A aplicação precisa de escalabilidade horizontal para consultas de autorização.
- A consistência é crítica (financeiro, healthcare, governo).
- O número de relações é muito grande para ser expresso como dados estaticos.

Não é ideal quando:
- O modelo de acesso é primariamente baseado em atributos (ABAC puro).
- A complexidade operacional de manter um cluster distribuído é proibitiva.
- O throughput de autorização é baixo e não justifica a infraestrutura.

---

## 13.6 Policy as Code

### 13.6.1 Definição e princípios

Policy as Code (PaC) é a prática de gerenciar políticas de autorização, segurança, e compliance como código versionado. Assim como Infrastructure as Code (IaC) trata servidores e redes como código, PaC trata regras de acesso como artefatos de software que podem ser versionados, testados, revisados, e implantados via pipelines de CI/CD.

Princípios fundamentais de PaC:

1. **Versionamento**: Políticas vivem em repositórios Git com histórico completo.
2. **Code review**: Mudanças de política passam por pull requests com aprovação de times de segurança.
3. **Testes automatizados**: Políticas são testadas com cenários antes de serem implantadas.
4. **CI/CD**: Políticas são validadas e implantadas via pipelines automáticas.
5. **Audit trail**: Cada mudança de política é rastreável com autor, data, e justificativa.
6. **Rollback**: Reverter uma política é tão fácil quanto reverter um commit.

### 13.6.2 Estrutura de repositório PaC

```
policies/
  models/
    rbac-model.conf
    abac-model.conf
    rebac-schema.zed
  policies/
    rbac/
      admin-policy.csv
      editor-policy.csv
      viewer-policy.csv
    abac/
      time-based.rego
      location-based.rego
      risk-based.rego
    rebac/
      org-project-document.zed
  tests/
    test_rbac_admin.yaml
    test_rbac_editor.yaml
    test_abac_time.yaml
    test_rebac_document.yaml
  fixtures/
    users.json
    projects.json
    organizations.json
  scripts/
    deploy-policies.sh
    validate-policies.sh
  ci/
    policy-lint.yaml
    policy-test.yaml
```

### 13.6.3 Versionamento e branch strategy

Políticas seguem a mesma branch strategy que código de aplicação:

```
main (producao)
  |
  +-- feature/add-risk-policy
  |     |
  |     +-- commit: "feat(policies): add risk-based ABAC for admin endpoints"
  |     +-- commit: "test(policies): add test scenarios for risk policy"
  |     +-- PR review by security team
  |     +-- merge to main
  |
  +-- hotfix/block-credential-stuffing
        |
        +-- commit: "hotfix(policies): block requests with >10 failed attempts"
        +-- emergency deploy
```

### 13.6.4 Policy testing

Testes de política verificam que as regras se comportam como esperado:

```yaml
# tests/test_rbac_admin.yaml
name: Admin should have full access
scenarios:
  - description: Admin can read any resource
    input:
      principal:
        id: "user:alice"
        role: "admin"
      action: "read"
      resource:
        id: "document:123"
        type: "confidential"
    expected: ALLOW

  - description: Admin can delete any resource
    input:
      principal:
        id: "user:alice"
        role: "admin"
      action: "delete"
      resource:
        id: "document:123"
    expected: ALLOW

  - description: Viewer cannot delete
    input:
      principal:
        id: "user:bob"
        role: "viewer"
      action: "delete"
      resource:
        id: "document:123"
    expected: DENY

  - description: Anonymous user has no access
    input:
      principal:
        id: ""
        role: ""
      action: "read"
      resource:
        id: "document:123"
    expected: DENY
```

```python
# Test runner para politicas Rego
import json
import subprocess

def evaluate_rego_policy(policy_file, input_data):
    """Avalia uma politica Rego com input especifico."""
    cmd = ['opa', 'eval', '-d', policy_file, '-I', 'data.authz.allow']
    
    result = subprocess.run(
        cmd,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        raise Exception(f"OPA eval failed: {result.stderr}")
    
    return json.loads(result.stdout)

def test_admin_can_read():
    input_data = {
        "input": {
            "principal": {"id": "user:alice", "role": "admin"},
            "action": "read",
            "resource": {"id": "document:123", "type": "confidential"}
        }
    }
    result = evaluate_rego_policy("policies/rbac-admin.rego", input_data)
    assert result == True, "Admin should be able to read"

def test_viewer_cannot_delete():
    input_data = {
        "input": {
            "principal": {"id": "user:bob", "role": "viewer"},
            "action": "delete",
            "resource": {"id": "document:123"}
        }
    }
    result = evaluate_rego_policy("policies/rbac-admin.rego", input_data)
    assert result == False, "Viewer should not be able to delete"
```

### 13.6.5 CI/CD para políticas

```yaml
# .github/workflows/policy-ci.yaml
name: Policy CI

on:
  push:
    paths:
      - 'policies/**'
  pull_request:
    paths:
      - 'policies/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint Rego policies
        run: |
          for f in $(find policies -name "*.rego"); do
            opa fmt $f --diff || exit 1
          done
      - name: Lint Cedar policies
        run: |
          cargo install cedar-policy-cli
          for f in $(find policies -name "*.cedar"); do
            cedar check --policy-file $f || exit 1
          done

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install OPA
        run: |
          curl -L -o /usr/local/bin/opa \
            https://openpolicyagent.org/downloads/latest/opa_linux_amd64
          chmod +x /usr/local/bin/opa
      - name: Run policy tests
        run: opa test policies/ -v

  security-review:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.event_name == 'pull_request'
    steps:
      - name: Require security team approval
        uses: actions/github-script@v7
        with:
          script: |
            const reviews = await github.rest.pulls.listReviews({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
            });
            const approved = reviews.data.filter(
              r => r.state === 'APPROVED' && 
                   r.user.login === 'security-team-lead'
            );
            if (approved.length === 0) {
              core.setFailed('Security team approval required');
            }
```

### 13.6.6 Deploy de políticas

```python
# deploy.py - Deploy de politicas com validacao
import json
import hashlib
from datetime import datetime

class PolicyDeployer:
    def __init__(self, policy_store, audit_log):
        self.store = policy_store
        self.audit = audit_log
    
    def deploy(self, policy_set: dict, deployer: str):
        # 1. Validar sintaxe
        for name, policy in policy_set.items():
            if not self.validate_syntax(policy):
                raise ValueError(f"Invalid policy syntax: {name}")
        
        # 2. Executar testes
        test_results = self.run_tests(policy_set)
        if not test_results.all_passed:
            raise ValueError(
                f"Policy tests failed: {test_results.failures}"
            )
        
        # 3. Verificar regressoes
        current = self.store.get_current_policies()
        regressions = self.detect_regressions(current, policy_set)
        if regressions:
            raise ValueError(
                f"Policy regressions detected: {regressions}"
            )
        
        # 4. Calcular hash para audit
        policy_hash = hashlib.sha256(
            json.dumps(policy_set, sort_keys=True).encode()
        ).hexdigest()
        
        # 5. Deploy
        self.store.update(policy_set)
        
        # 6. Audit log
        self.audit.log({
            "event": "policy_deploy",
            "deployer": deployer,
            "timestamp": datetime.utcnow().isoformat(),
            "policy_hash": policy_hash,
            "policy_count": len(policy_set),
            "policies": list(policy_set.keys()),
        })
        
        return {
            "status": "deployed",
            "hash": policy_hash,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def rollback(self, version: str, deployer: str):
        """Reverter para versao anterior de politicas."""
        previous = self.store.get_version(version)
        if not previous:
            raise ValueError(f"Version {version} not found")
        
        self.store.update(previous)
        self.audit.log({
            "event": "policy_rollback",
            "deployer": deployer,
            "target_version": version,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def validate_syntax(self, policy: dict) -> bool:
        """Valida sintaxe da politica."""
        try:
            # Para Rego: opa fmt --check
            # Para Cedar: cedar check
            # Para Casbin: carregar enforcer
            return True
        except Exception:
            return False
    
    def run_tests(self, policy_set: dict):
        """Executa testes de politica."""
        results = TestResults()
        for test_file in self.get_test_files():
            result = self.execute_test(test_file, policy_set)
            results.add(result)
        return results
    
    def detect_regressions(self, current: dict, new: dict) -> list:
        """Detecta regresses entre versoes de politicas."""
        regressions = []
        for policy_name in current:
            if policy_name in new:
                # Verificar se a politica ficou mais restritiva
                # quando deveria ficar menos
                if self.is_less_restrictive(
                    current[policy_name], new[policy_name]
                ):
                    regressions.append({
                        "policy": policy_name,
                        "type": "less_restrictive",
                    })
        return regressions
```

---

## 13.7 Testes de Políticas

### 13.7.1 Por que testar políticas

Políticas de autorização são código que controla quem pode acessar o quê. Um bug em uma política pode significar:
- Usuários não autorizados acessando dados sensíveis (falso positivo — allow indevido).
- Usuários legítimos bloqueados de acessar recursos necessários (falso negativo — deny indevido).
- Violações de compliance (LGPD, GDPR, HIPAA) por falha de auditoria.

O caso Misantropi4 demonstra o custo de políticas não testadas. Se o IDAP tivesse cenários de teste que verificassem:
1. "Um operador com credenciais comprometidas não deveria acessar >100 registros por hora."
2. "Requisições sem captcha válido deveriam ser negadas."
3. "Acessos de IPs fora do Brasil deveriam exigir MFA adicional."

...o ataque teria sido detectado antes de causar danos.

### 13.7.2 Tipos de teste de política

**Testes unitários**: Verificam que uma política individual se comporta corretamente.

```yaml
# test_unit.yaml
name: Time-based access control
policy: time-based-access.rego
input:
  principal:
    role: "operator"
    clearance: "standard"
  resource:
    type: "citizen_record"
    classification: "sensitive"
  environment:
    timestamp: "2026-06-20T10:00:00Z"
    timezone: "America/Sao_Paulo"
expected: ALLOW
```

**Testes de integração**: Verificam que múltiplas políticas interagem corretamente.

```yaml
# test_integration.yaml
name: RBAC + ABAC combined access
policies:
  - rbac-model.conf
  - abac-time-based.conf
  - abac-location-based.conf
scenarios:
  - description: Admin in Brazil during business hours
    input:
      principal:
        role: "admin"
      resource:
        type: "citizen_record"
      environment:
        country: "BR"
        timestamp: "2026-06-20T10:00:00Z"
    expected: ALLOW
  
  - description: Admin outside Brazil
    input:
      principal:
        role: "admin"
      resource:
        type: "citizen_record"
      environment:
        country: "US"
        timestamp: "2026-06-20T10:00:00Z"
    expected: DENY
```

**Testes de regressão**: Verificam que mudanças não quebram comportamento existente.

```python
def test_regression_admin_access_not_broken():
    """Garantir que politica de admin continua funcionando."""
    # Cenarios que DEVEM funcionar
    must_allow = [
        {"input": admin_read_confidential},
        {"input": admin_write_internal},
        {"input": admin_delete_draft},
    ]
    
    # Cenarios que DEVEM continuar negados
    must_deny = [
        {"input": admin_delete_production},
        {"input": admin_access_other_org},
    ]
    
    for scenario in must_allow:
        assert evaluate(scenario) == ALLOW, \
            f"Regression: admin should allow {scenario}"
    
    for scenario in must_deny:
        assert evaluate(scenario) == DENY, \
            f"Regression: admin should deny {scenario}"
```

**Testes de fuzzing**: Geram inputs aleatórios para encontrar edge cases.

```python
import random
import string

def generate_random_input():
    """Gera inputs aleatorios para testes de fuzzing."""
    return {
        "principal": {
            "id": "user:" + "".join(random.choices(string.ascii_lowercase, k=10)),
            "role": random.choice(["admin", "editor", "viewer", "", None]),
        },
        "action": random.choice(["read", "write", "delete", "admin", "", None]),
        "resource": {
            "id": "resource:" + "".join(random.choices(string.ascii_lowercase, k=10)),
            "type": random.choice(["document", "folder", "project", "", None]),
            "classification": random.choice(["public", "internal", "confidential", ""]),
        },
        "environment": {
            "timestamp": "2026-06-20T" + f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
            "country": random.choice(["BR", "US", "CN", "", None]),
        },
    }

def fuzz_policy(policy_file, iterations=10000):
    """Fuzzing de politica."""
    crashes = []
    for i in range(iterations):
        try:
            input_data = generate_random_input()
            result = evaluate_rego_policy(policy_file, {"input": input_data})
            # Verificar que resultado e bool
            assert isinstance(result, bool), \
                f"Non-boolean result: {result}"
        except Exception as e:
            crashes.append({"iteration": i, "error": str(e), "input": input_data})
    
    return crashes
```

### 13.7.3 Framework de testes completo

```python
# policy_test_framework.py
import json
import yaml
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

@dataclass
class TestCase:
    name: str
    description: str
    input_data: dict
    expected: bool
    tags: list = field(default_factory=list)
    skip: bool = False
    skip_reason: str = ""

@dataclass
class TestSuite:
    name: str
    policy_file: str
    test_cases: list
    fixtures: dict = field(default_factory=dict)

@dataclass
class TestResult:
    test_name: str
    passed: bool
    expected: bool
    actual: bool
    error: Optional[str] = None
    duration_ms: float = 0

class PolicyTestRunner:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.results = []
    
    def load_suite(self, suite_file: Path) -> TestSuite:
        with open(suite_file) as f:
            data = yaml.safe_load(f)
        return TestSuite(
            name=data["name"],
            policy_file=data["policy"],
            test_cases=[
                TestCase(
                    name=tc["name"],
                    description=tc.get("description", ""),
                    input_data=tc["input"],
                    expected=tc["expected"],
                    tags=tc.get("tags", []),
                    skip=tc.get("skip", False),
                    skip_reason=tc.get("skip_reason", ""),
                )
                for tc in data["tests"]
            ],
            fixtures=data.get("fixtures", {}),
        )
    
    def run_suite(self, suite: TestSuite) -> list:
        results = []
        for tc in suite.test_cases:
            if tc.skip:
                print(f"  SKIP: {tc.name} ({tc.skip_reason})")
                continue
            
            result = self.run_test(suite.policy_file, tc)
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  {status}: {tc.name}")
        
        self.results.extend(results)
        return results
    
    def run_test(self, policy_file: str, tc: TestCase) -> TestResult:
        import time
        start = time.time()
        
        try:
            actual = self.evaluator.evaluate(policy_file, tc.input_data)
            duration = (time.time() - start) * 1000
            
            return TestResult(
                test_name=tc.name,
                passed=(actual == tc.expected),
                expected=tc.expected,
                actual=actual,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(
                test_name=tc.name,
                passed=False,
                expected=tc.expected,
                actual=None,
                error=str(e),
                duration_ms=duration,
            )
    
    def summary(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        errors = sum(1 for r in self.results if r.error)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            "avg_duration_ms": (
                sum(r.duration_ms for r in self.results) / total
                if total > 0 else 0
            ),
        }
    
    def report(self) -> str:
        summary = self.summary()
        lines = [
            "=" * 60,
            "POLICY TEST REPORT",
            "=" * 60,
            f"Total: {summary['total']}",
            f"Passed: {summary['passed']}",
            f"Failed: {summary['failed']}",
            f"Errors: {summary['errors']}",
            f"Pass rate: {summary['pass_rate']}",
            f"Avg duration: {summary['avg_duration_ms']:.2f}ms",
            "",
        ]
        
        if summary['failed'] > 0:
            lines.append("FAILURES:")
            for r in self.results:
                if not r.passed:
                    lines.append(f"  - {r.test_name}")
                    if r.error:
                        lines.append(f"    Error: {r.error}")
                    else:
                        lines.append(
                            f"    Expected: {r.expected}, Got: {r.actual}"
                        )
        
        return "\n".join(lines)
```

---

## 13.8 Auditoria e Logging

### 13.8.1 Importância do audit trail

Cada decisão de autorização — tanto ALLOW quanto DENY — deve ser registrada. O audit trail de autorização é essencial para:

1. **Investigação de incidentes**: Após o Misantropi4, investigadores precisaram reconstruir quais registros foram acessados, quando, e de onde. Sem audit trail, essa reconstrução é impossível.
2. **Compliance**: LGPD, GDPR, HIPAA, PCI-DSS exigem trilhas de auditoria para acessos a dados sensíveis.
3. **Detecção de anomalias**: Padrões de acesso incomuns (muitas leituras por minuto, acessos fora do horário, IPs estrangeiros) podem indicar comprometimento de credenciais.
4. **Accountability**: Cada acesso deve ser rastreado a um sujeito identificável.
5. **Forense**: Em caso de incidente, o audit trail é a principal fonte de evidência.

### 13.8.2 O que registrar

Para cada decisão de autorização, registrar:

```json
{
    "event_id": "evt-2026-06-20T10:15:30Z-abc123",
    "timestamp": "2026-06-20T10:15:30.123Z",
    "event_type": "authorization_decision",
    "decision": "ALLOW",
    "subject": {
        "id": "user:operador-001",
        "role": "operator",
        "session_id": "sess-xyz789"
    },
    "resource": {
        "type": "citizen_record",
        "id": "record-456",
        "classification": "sensitive"
    },
    "action": "read",
    "context": {
        "ip_address": "189.45.23.10",
        "user_agent": "Mozilla/5.0...",
        "geo_country": "BR",
        "geo_state": "SP",
        "timestamp_evaluated": "2026-06-20T10:15:30.100Z",
        "latency_ms": 23
    },
    "policy_version": "v2.3.1",
    "policy_hash": "sha256:abc123...",
    "matched_rules": ["rule:operator-read-sensitive"],
    "risk_score": 0.3
}
```

### 13.8.3 Implementação de audit logging

```python
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class AuditEvent:
    event_id: str
    timestamp: str
    event_type: str
    decision: str
    subject_id: str
    subject_role: str
    session_id: str
    resource_type: str
    resource_id: str
    action: str
    ip_address: str
    user_agent: str
    geo_country: str
    geo_state: str
    policy_version: str
    policy_hash: str
    matched_rules: list
    risk_score: float
    latency_ms: float
    error: Optional[str] = None

class AuthorizationAuditLogger:
    def __init__(self, storage, alert_thresholds=None):
        self.storage = storage
        self.thresholds = alert_thresholds or {
            "max_requests_per_minute": 100,
            "max_denials_per_minute": 20,
            "max_failed_mfa_per_hour": 5,
        }
        self.counters = {}
    
    def log_decision(
        self,
        subject_id: str,
        subject_role: str,
        session_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        decision: str,
        context: Dict[str, Any],
        policy_version: str,
        policy_hash: str,
        matched_rules: list,
        risk_score: float,
        latency_ms: float,
        error: Optional[str] = None,
    ):
        event = AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type="authorization_decision",
            decision=decision,
            subject_id=subject_id,
            subject_role=subject_role,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            ip_address=context.get("ip_address", ""),
            user_agent=context.get("user_agent", ""),
            geo_country=context.get("geo_country", ""),
            geo_state=context.get("geo_state", ""),
            policy_version=policy_version,
            policy_hash=policy_hash,
            matched_rules=matched_rules,
            risk_score=risk_score,
            latency_ms=latency_ms,
            error=error,
        )
        
        self.storage.write(asdict(event))
        
        self._check_thresholds(event)
        
        self._detect_anomalies(event)
    
    def _check_thresholds(self, event: AuditEvent):
        key = f"{event.subject_id}:{event.timestamp[:16]}"
        
        if key not in self.counters:
            self.counters[key] = {
                "total": 0,
                "denials": 0,
                "mfa_failures": 0,
            }
        
        self.counters[key]["total"] += 1
        
        if event.decision == "DENY":
            self.counters[key]["denials"] += 1
        
        if event.error and "mfa" in event.error.lower():
            self.counters[key]["mfa_failures"] += 1
        
        if self.counters[key]["total"] > self.thresholds["max_requests_per_minute"]:
            self._alert("rate_limit_exceeded", event, {
                "requests": self.counters[key]["total"],
                "threshold": self.thresholds["max_requests_per_minute"],
            })
        
        if self.counters[key]["denials"] > self.thresholds["max_denials_per_minute"]:
            self._alert("excessive_denials", event, {
                "denials": self.counters[key]["denials"],
                "threshold": self.thresholds["max_denials_per_minute"],
            })
    
    def _detect_anomalies(self, event: AuditEvent):
        if event.risk_score > 0.8:
            self._alert("high_risk_access", event, {
                "risk_score": event.risk_score,
            })
        
        if event.geo_country not in ["BR"]:
            self._alert("foreign_access", event, {
                "country": event.geo_country,
            })
        
        hour = int(event.timestamp[11:13])
        if hour < 6 or hour > 22:
            self._alert("off_hours_access", event, {
                "hour": hour,
            })
    
    def _alert(self, alert_type: str, event: AuditEvent, details: dict):
        alert = {
            "alert_type": alert_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": asdict(event),
            "details": details,
            "severity": self._get_severity(alert_type),
        }
        
        self.storage.write_alert(alert)
    
    def _get_severity(self, alert_type: str) -> str:
        severity_map = {
            "rate_limit_exceeded": "HIGH",
            "excessive_denials": "HIGH",
            "high_risk_access": "CRITICAL",
            "foreign_access": "MEDIUM",
            "off_hours_access": "LOW",
        }
        return severity_map.get(alert_type, "INFO")
    
    def generate_report(self, start_date: str, end_date: str) -> dict:
        events = self.storage.query(start_date, end_date)
        
        total = len(events)
        allows = sum(1 for e in events if e["decision"] == "ALLOW")
        denials = sum(1 for e in events if e["decision"] == "DENY")
        
        unique_subjects = len(set(e["subject_id"] for e in events))
        unique_resources = len(set(e["resource_id"] for e in events))
        
        top_subjects = self._top_by_field(events, "subject_id", 10)
        top_resources = self._top_by_field(events, "resource_id", 10)
        
        hourly_distribution = self._hourly_distribution(events)
        
        return {
            "period": f"{start_date} to {end_date}",
            "total_events": total,
            "allows": allows,
            "denials": denials,
            "allow_rate": f"{(allows/total*100):.1f}%" if total > 0 else "N/A",
            "unique_subjects": unique_subjects,
            "unique_resources": unique_resources,
            "top_subjects": top_subjects,
            "top_resources": top_resources,
            "hourly_distribution": hourly_distribution,
        }
    
    def _top_by_field(self, events, field, limit):
        counts = {}
        for e in events:
            val = e[field]
            counts[val] = counts.get(val, 0) + 1
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"id": k, "count": v} for k, v in sorted_items[:limit]]
    
    def _hourly_distribution(self, events):
        hours = {}
        for e in events:
            hour = e["timestamp"][11:13]
            hours[hour] = hours.get(hour, 0) + 1
        return dict(sorted(hours.items()))
```

### 13.8.4 SIEM integration

```python
class SIEMExporter:
    def __init__(self, siem_client):
        self.client = siem_client
    
    def export_event(self, event: AuditEvent):
        siem_event = {
            "source": "policy_engine",
            "sourcetype": "authorization:decision",
            "time": event.timestamp,
            "event": {
                "action": event.action,
                "decision": event.decision,
                "subject": event.subject_id,
                "resource": event.resource_id,
                "ip": event.ip_address,
                "geo": f"{event.geo_state}/{event.geo_country}",
                "risk_score": event.risk_score,
                "policy_version": event.policy_version,
            },
            "fields": {
                "subject_role": event.subject_role,
                "resource_type": event.resource_type,
                "latency_ms": event.latency_ms,
                "matched_rules": event.matched_rules,
            },
        }
        
        self.client.send(siem_event)
    
    def export_alert(self, alert: dict):
        siem_alert = {
            "source": "policy_engine",
            "sourcetype": "authorization:alert",
            "time": alert["timestamp"],
            "event": alert,
            "severity": self._map_severity(alert["severity"]),
        }
        
        self.client.send(siem_alert)
    
    def _map_severity(self, severity: str) -> int:
        return {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "INFO": 0,
        }.get(severity, 0)
```

---

## 13.9 Performance e Otimização

### 13.9.1 Benchmarks de engines de política

A performance de uma engine de política depende de múltiplos fatores: complexidade das regras, tamanho dos dados, frequência de consultas, e latência de rede (para engines como serviço).

Métricas típicas:
- **Throughput**: Número de avaliações por segundo (QPS).
- **Latência**: Tempo para uma avaliação individual (p50, p95, p99).
- **CPU usage**: Carga de CPU por avaliação.
- **Memory usage**: Consumo de memória para dados e políticas.

### 13.9.2 Otimizações de performance

**Cache de decisões**: Para requisições repetidas com o mesmo input, cachear a decisão por um curto período (TTL).

```python
import time
from functools import lru_cache
from typing import Tuple

class CachedPolicyEngine:
    def __init__(self, engine, ttl_seconds=60):
        self.engine = engine
        self.ttl = ttl_seconds
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def evaluate(self, subject_id: str, action: str,
                 resource_id: str) -> bool:
        cache_key = self._make_key(subject_id, action, resource_id)
        
        now = time.time()
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if now - entry["timestamp"] < self.ttl:
                self.cache_hits += 1
                return entry["decision"]
        
        self.cache_misses += 1
        decision = self.engine.evaluate(subject_id, action, resource_id)
        
        self.cache[cache_key] = {
            "decision": decision,
            "timestamp": now,
        }
        
        return decision
    
    def invalidate(self, subject_id: str = None,
                   resource_id: str = None):
        if subject_id is None and resource_id is None:
            self.cache.clear()
            return
        
        keys_to_remove = []
        for key in self.cache:
            parts = key.split(":")
            if subject_id and parts[0] == subject_id:
                keys_to_remove.append(key)
            if resource_id and parts[1] == resource_id:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def _make_key(self, subject_id: str, action: str,
                  resource_id: str) -> str:
        return f"{subject_id}:{action}:{resource_id}"
    
    def stats(self) -> dict:
        total = self.cache_hits + self.cache_misses
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_rate": f"{(self.cache_hits/total*100):.1f}%" if total > 0 else "N/A",
            "cache_size": len(self.cache),
        }
```

**Indexação de políticas**: Para engines que avaliam múltiplas regras, indexar por campos frequentemente consultados.

**Pre-computação**: Para políticas que dependem de dados estáticos ou lentamente mutáveis, pré-computar resultados.

```python
class PrecomputedPolicyEngine:
    def __init__(self, engine, data_loader):
        self.engine = engine
        self.loader = data_loader
        self.matrix = {}
    
    def build_matrix(self):
        """Pre-compute access matrix para todas as combinatorias."""
        subjects = self.loader.get_all_subjects()
        resources = self.loader.get_all_resources()
        actions = self.loader.get_all_actions()
        
        self.matrix = {}
        for subject in subjects:
            for resource in resources:
                for action in actions:
                    key = f"{subject['id']}:{resource['id']}:{action}"
                    self.matrix[key] = self.engine.evaluate(
                        subject, action, resource
                    )
    
    def evaluate(self, subject_id: str, action: str,
                 resource_id: str) -> bool:
        key = f"{subject_id}:{resource_id}:{action}"
        if key in self.matrix:
            return self.matrix[key]
        
        # Fallback to engine for unknown combinations
        subject = self.loader.get_subject(subject_id)
        resource = self.loader.get_resource(resource_id)
        return self.engine.evaluate(subject, action, resource)
```

### 13.9.3 Latência por tipo de engine

| Engine | Modo | Latência típica (p99) | Throughput |
|--------|------|----------------------|------------|
| Casbin | In-process | < 1ms | 100K+ QPS |
| OPA | Sidecar (local) | 1-5ms | 10K+ QPS |
| OPA | Serviço (HTTP) | 5-20ms | 5K+ QPS |
| Cedar | In-process | 1-3ms | 50K+ QPS |
| SpiceDB | gRPC (local) | 2-5ms | 50K+ QPS |
| SpiceDB | gRPC (remoto) | 5-15ms | 10K+ QPS |

### 13.9.4 Estratégias de mitigação de latência

**Circuit breaker**: Se a engine de política estiver indisponível, usar fallback (deny by default ou cached decisions).

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerPolicyEngine:
    def __init__(self, engine, failure_threshold=5,
                 recovery_timeout=30):
        self.engine = engine
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.cached_decisions = {}
    
    def evaluate(self, subject_id, action, resource_id):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return self._fallback(subject_id, action, resource_id)
        
        try:
            decision = self.engine.evaluate(
                subject_id, action, resource_id
            )
            self._on_success()
            self._cache(subject_id, action, resource_id, decision)
            return decision
        except Exception:
            self._on_failure()
            return self._fallback(subject_id, action, resource_id)
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _fallback(self, subject_id, action, resource_id):
        key = f"{subject_id}:{action}:{resource_id}"
        return self.cached_decisions.get(key, False)
    
    def _cache(self, subject_id, action, resource_id, decision):
        key = f"{subject_id}:{action}:{resource_id}"
        self.cached_decisions[key] = decision
```

---

## 13.10 Exemplos Completos de Políticas

### 13.10.1 Sistema de gestão de documentos

**Cenário**: Sistema corporativo com usuários em múltiplos projetos, documentos classificados em níveis (public, internal, confidential, secret), e políticas baseadas em rôle, atributo, e relação.

**Modelo Rego completo:**

```rego
package documents.authz

import rego.v1

default allow = false

# Regras de papel
role_permissions := {
    "admin": {
        "actions": ["read", "write", "delete", "share", "admin"],
        "max_classification": "secret",
    },
    "manager": {
        "actions": ["read", "write", "delete", "share"],
        "max_classification": "confidential",
    },
    "editor": {
        "actions": ["read", "write"],
        "max_classification": "internal",
    },
    "viewer": {
        "actions": ["read"],
        "max_classification": "internal",
    },
}

classification_levels := {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "secret": 3,
}

# Hierarquia de classificacao
user_clearance_level(user_id) = level if {
    user := data.users[user_id]
    level := classification_levels[user.clearance]
}

resource_classification_level(resource_id) = level if {
    resource := data.resources[resource_id]
    level := classification_levels[resource.classification]
}

# Regra 1: Admin pode tudo em documentos da propria organizacao
allow if {
    user := data.users[input.principal.id]
    user.role == "admin"
    resource := data.resources[input.resource.id]
    user.organization == resource.organization
}

# Regra 2: Gerente pode ler/escrever/deletar documentos do projeto
allow if {
    user := data.users[input.principal.id]
    user.role == "manager"
    input.action in ["read", "write", "delete"]
    resource := data.resources[input.resource.id]
    user_clearance_level(input.principal.id) >= resource_classification_level(input.resource.id)
    is_project_member(input.principal.id, resource.project_id)
}

# Regra 3: Editor pode ler e escrever em documentos do projeto
allow if {
    user := data.users[input.principal.id]
    user.role == "editor"
    input.action in ["read", "write"]
    resource := data.resources[input.resource.id]
    user_clearance_level(input.principal.id) >= resource_classification_level(input.resource.id)
    is_project_member(input.principal.id, resource.project_id)
}

# Regra 4: Visualizador pode ler documentos publicos e internos
allow if {
    user := data.users[input.principal.id]
    user.role == "viewer"
    input.action == "read"
    resource := data.resources[input.resource.id]
    resource.classification in ["public", "internal"]
    is_project_member(input.principal.id, resource.project_id)
}

# Regra 5: Documentos publicos sao legiveis por qualquer um autenticado
allow if {
    input.action == "read"
    resource := data.resources[input.resource.id]
    resource.visibility == "public"
    input.principal.id != ""
}

# Regra 6: Dono pode compartilhar documentos
allow if {
    input.action == "share"
    resource := data.resources[input.resource.id]
    resource.owner == input.principal.id
}

# Regra 7: Controle temporal — acesso restrito a horario comercial
allow if {
    is_business_hours
    user := data.users[input.principal.id]
    user.role in ["editor", "viewer"]
    resource := data.resources[input.resource.id]
    resource.classification == "confidential"
}

# Regra 8: Controle geografico — acesso apenas do pais configurado
allow if {
    user := data.users[input.principal.id]
    input.context.country in user.allowed_countries
    resource := data.resources[input.resource.id]
    resource.classification in ["confidential", "secret"]
}

# Regra 9: Rate limiting — maximo de acessos por hora
deny if {
    access_count := count([a |
        a := data.access_log[_]
        a.user_id == input.principal.id
        a.timestamp > now - 3600
    ])
    access_count > input.context.user_hourly_limit
}

# Regra 10: Requer MFA para classificacao alta
allow if {
    resource := data.resources[input.resource.id]
    resource.classification in ["confidential", "secret"]
    input.context.mfa_verified == true
}

# Funcoes auxiliares
is_project_member(user_id, project_id) if {
    some membership
    membership := data.memberships[_]
    membership.user_id == user_id
    membership.project_id == project_id
    membership.active == true
}

is_business_hours if {
    hour := time.clock(time.now_ns())[0]
    hour >= 8
    hour < 18
}

now := time.now_ns() / 1000000000
```

### 13.10.2 Políticas Cedar equivalentes

```cedar
namespace Documents {

    entity User {
        "email": String,
        "role": String,
        "organization": String,
        "clearance": String,
        "mfaVerified": Bool,
        "allowedCountries": Set<String>,
    };

    entity Resource {
        "owner": User,
        "organization": String,
        "project": String,
        "classification": String,
        "visibility": String,
    };

    entity Project {
        "org": String,
        "members": Set<User>,
    };

    action read;
    action write;
    action delete;
    action share;

    // Regra 1: Admin pode tudo na propria organizacao
    permit(
        principal in User,
        action in [read, write, delete, share],
        resource in Resource
    ) when {
        principal.role == "admin"
        && principal.organization == resource.organization
    };

    // Regra 2: Gerente pode acessar documentos do projeto
    permit(
        principal in User,
        action in [read, write, delete],
        resource in Resource
    ) when {
        principal.role == "manager"
        && principal.organization == resource.organization
    };

    // Regra 3: MFA obrigatorio para classificacao alta
    forbid(
        principal in User,
        action,
        resource in Resource
    ) when {
        resource.classification in ["confidential", "secret"]
        && !principal.mfaVerified
    };

    // Regra 4: Apenas do pais permitido para dados sensiveis
    forbid(
        principal in User,
        action,
        resource in Resource
    ) when {
        resource.classification in ["confidential", "secret"]
    };
}
```

### 13.10.3 Casbin equivalente

```ini
# model.conf
[request_definition]
r = sub, obj, act, ctx

[policy_definition]
p = sub_role, sub_clearance, obj_classification, act, condition

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub_role) && r.act == p.act && r.ctx.country == "BR" && r.ctx.mfa_verified == true
```

```csv
# policy.csv
p, admin, secret, read, true
p, admin, secret, write, true
p, admin, secret, delete, true
p, manager, confidential, read, true
p, manager, confidential, write, true
p, manager, confidential, delete, true
p, editor, internal, read, true
p, editor, internal, write, true
p, viewer, public, read, true
p, viewer, internal, read, true

g, alice, admin
g, bob, manager
g, charlie, editor
g, dave, viewer
```

---

## 13.11 Integração com Microsserviços

### 13.11.1 Padrões de integração

Em arquiteturas de microsserviços, a engine de política pode ser integrada de três formas principais:

**Padrão 1 — Sidecar proxy**: Um proxy (Envoy, Istio) intercepta todas as requisições e consulta a engine de política antes de encaminhar ao microsserviço.

```
┌─────────┐     ┌─────────┐     ┌──────────────┐
│  Client  │────>│  Envoy  │────>│  Microservice│
│          │     │  Proxy  │     │  (Backend)   │
│          │<────│         │<────│              │
└─────────┘     │  OPA    │     └──────────────┘
                │  Sidecar│
                └─────────┘
```

**Padrão 2 — Library/biblioteca**: Cada microsserviço inclui a engine de política como biblioteca. Não há overhead de rede, mas a política é distribuída.

```
┌─────────────────────┐
│  Microservice       │
│  + Casbin (lib)     │
│  + Policy Engine    │
└─────────────────────┘
```

**Padrão 3 — Centralized service**: Serviço centralizado de autorização. Microsserviços consultam via API.

```
┌──────────┐     ┌──────────────┐
│ Service A │────>│              │
│           │<────│  AuthZ       │
└──────────┘     │  Service     │
┌──────────┐     │  (OPA/Cedar) │
│ Service B │────>│              │
│           │<────│              │
└──────────┘     └──────────────┘
```

### 13.11.2 Integração com Envoy + OPA

```yaml
# envoy.yaml
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: local_service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: local_service
          http_filters:
          - name: envoy.filters.http.ext_authz
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.ext_authz.v3.ExtAuthz
              grpc_service:
                envoy_grpc:
                  cluster_name: opa_ext_authz
              failure_mode_allow: false
              include_peer_certificate: true
  clusters:
  - name: opa_ext_authz
    type: STATIC
    load_assignment:
      cluster_name: opa_ext_authz
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 9191
    http2_protocol_options: {}
```

**OPA config para Envoy:**

```yaml
# opa-config.yaml
plugins:
  envoy_ext_authz_grpc:
    addr: ":9191"
    path: "authz/allow"
    dry-run: false
    log-message: true

services:
  bundle:
    url: http://policy-server:8181/bundles/authz
    resource: "/bundles/authz.tar.gz"

labels:
  app: "myapp"
  environment: "production"

decision_logs:
  service: "decision-logger"
  console: true

status:
  log:
    level: "info"
```

### 13.11.3 Integração com API Gateway

```python
# FastAPI middleware with Casbin
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import casbin

app = FastAPI()
enforcer = casbin.Enforcer('model.conf', 'policy.csv')

class CasbinMiddleware:
    def __init__(self, app, enforcer):
        self.app = app
        self.enforcer = enforcer
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            user_id = request.headers.get("X-User-ID", "")
            user_role = request.headers.get("X-User-Role", "")
            path = request.url.path
            method = request.method
            
            resource_type = self._extract_resource_type(path)
            action = self._map_method_to_action(method)
            
            if not self.enforcer.enforce(user_id, resource_type, action):
                response = HTTPException(status_code=403, detail="Forbidden")
                await response(scope, receive, send)
                return
        
        await self.app(scope, receive, send)
    
    def _extract_resource_type(self, path: str) -> str:
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[1]  # /documents/123 -> documents
        return "global"
    
    def _map_method_to_action(self, method: str) -> str:
        return {
            "GET": "read",
            "POST": "create",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
        }.get(method, "read")

app.add_middleware(CasbinMiddleware, enforcer=enforcer)
```

### 13.11.4 Integração com Kubernetes

```yaml
# OPA Gatekeeper - ConstraintTemplate
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sauthzpolicy
spec:
  crd:
    spec:
      names:
        kind: K8sAuthzPolicy
      validation:
        openAPIV3Schema:
          type: object
          properties:
            allowedRoles:
              type: array
              items:
                type: string
            requireMFA:
              type: boolean
            allowedNamespaces:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sauthzpolicy
        
        violation[{"msg": msg}] {
          input.review.object.metadata.labels.role
          not input.review.object.metadata.labels.role in input.parameters.allowedRoles
          msg := sprintf("Role %v is not allowed", [input.review.object.metadata.labels.role])
        }
        
        violation[{"msg": msg}] {
          input.parameters.requireMFA
          not input.review.object.metadata.annotations["mfa-verified"]
          msg := "MFA verification required"
        }
        
        violation[{"msg": msg}] {
          input.parameters.allowedNamespaces
          not input.review.object.metadata.namespace in input.parameters.allowedNamespaces
          msg := sprintf("Namespace %v is not allowed", [input.review.object.metadata.namespace])
        }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sAuthzPolicy
metadata:
  name: require-mfa-for-prod
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["production"]
  parameters:
    allowedRoles: ["admin", "operator"]
    requireMFA: true
    allowedNamespaces: ["production", "staging"]
```

### 13.11.5 Padrão de fallback resilience

```python
class ResilientPolicyClient:
    def __init__(self, primary_client, fallback_client):
        self.primary = primary_client
        self.fallback = fallback_client
        self.circuit_open = False
        self.failure_count = 0
        self.failure_threshold = 5
        self.recovery_timeout = 30
        self.last_failure_time = 0
    
    async def check(self, subject, action, resource, context):
        if self.circuit_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.circuit_open = False
                self.failure_count = 0
            else:
                return await self._fallback_check(subject, action, resource)
        
        try:
            result = await self.primary.check(subject, action, resource, context)
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.circuit_open = True
            
            return await self._fallback_check(subject, action, resource)
    
    async def _fallback_check(self, subject, action, resource):
        try:
            result = await self.fallback.check(subject, action, resource)
            return result
        except Exception:
            # Default: deny all when both engines fail
            return {"decision": "DENY", "reason": "policy_engine_unavailable"}
```

---

## 13.12 Caso Misantropi4 — Lições para Engines de Política

### 13.12.1 Como uma engine de política teria mitigado o ataque

O ataque ao IDAP (detalhado no Capítulo 15) explorou múltiplas falhas que uma engine de política centralizada poderia ter prevenido:

**Falha 1 — Sem verificação de origem**: O IDAP não verificava se as requisições vinham de IPs brasileiros ou de ranges autorizados.

```rego
# Politica que teria bloqueado acessos estrangeiros
package idap.authz

default allow = false

allow if {
    input.context.country == "BR"
    has_valid_mfa
    is_normal_hour
    rate_limit_ok
}

deny if {
    input.context.country != "BR"
}
```

**Falha 2 — Sem rate limiting**: O atacante fez milhares de tentativas de login sem restrição.

```rego
# Rate limiting via politica
deny if {
    login_attempts := count([a |
        a := data.login_attempts[_]
        a.ip == input.context.ip
        a.timestamp > now - 900  # 15 minutos
    ])
    login_attempts > 10
}
```

**Falha 3 — Sem verificação de MFA**: Credenciais comprometidas resultaram em acesso completo.

```rego
# MFA obrigatorio para acessos sensiveis
deny if {
    input.resource.type == "citizen_record"
    not input.context.mfa_verified
}
```

**Falha 4 — Sem verificação de captcha**: O captcha matemático era trivial e não verificado no backend.

```rego
# Captcha obrigatorio para login
deny if {
    action == "login"
    not input.context.captcha_verified
}
```

**Falha 5 — Privilegios excessivos**: Credenciais de operador davam acesso a milhões de registros.

```rego
# Limite de registros acessiveis por role
deny if {
    user := data.users[input.principal.id]
    records_requested := count(input.resource.record_ids)
    records_requested > user.max_records_per_session
}

# max_records_per_session por role:
# operator: 100
# supervisor: 1000
# auditor: 10000
# admin: unlimited (mas com alert)
```

### 13.12.2 Checklist de políticas para sistemas governamentais

```yaml
# policies/government-system-checklist.yaml
authentication:
  - policy: "MFA obrigatorio para todos os acessos"
    control: "NIST SP 800-63B AAL2"
  - policy: "Captcha obrigatorio em login (verificado no backend)"
    control: "OWASP ASVS 2.1"
  - policy: "Lockout apos 5 tentativas fracassadas em 15 minutos"
    control: "NIST SP 800-63B"
  - policy: "Rotacao de senha a cada 90 dias"
    control: "LGPD Art. 46"

authorization:
  - policy: "Principio do menor privilege"
    control: "NIST SP 800-53 AC-6"
  - policy: "Segregacao de duties"
    control: "NIST SP 800-53 AC-5"
  - policy: "Revisao de privilegios a cada 30 dias"
    control: "NIST SP 800-53 AC-2"
  - policy: "Acesso a dados sensiveis requer justificativa"
    control: "LGPD Art. 46"

monitoring:
  - policy: "Log de todas as decisoes de autorizacao"
    control: "NIST SP 800-53 AU-2"
  - policy: "Alerta para acessos fora do horario comercial"
    control: "NIST SP 800-53 AU-6"
  - policy: "Alerta para acessos de IPs estrangeiros"
    control: "NIST SP 800-53 AU-6"
  - policy: "Rate limiting em endpoints sensiveis"
    control: "OWASP API Security Top 10"

network:
  - policy: "Acesso apenas de ranges de IP autorizados"
    control: "NIST SP 800-53 SC-7"
  - policy: "TLS obrigatorio para todas as comunicacoes"
    control: "NIST SP 800-53 SC-8"
  - policy: "VPN obrigatoria para acesso a sistemas internos"
    control: "NIST SP 800-53 SC-7"
```

### 13.12.3 Padrão de defesa em profundidade

Uma engine de política não é a única defesa necessária. O padrão correto é defesa em profundidade:

```
┌─────────────────────────────────────────────┐
│  Camada 1: WAF + Rate Limiter              │
│  (bloqueia trafego malicioso na borda)      │
├─────────────────────────────────────────────┤
│  Camada 2: Captcha (verificado no backend)  │
│  (previne bots automatizados)               │
├─────────────────────────────────────────────┤
│  Camada 3: MFA                              │
│  (previne uso de credenciais roubadas)      │
├─────────────────────────────────────────────┤
│  Camada 4: Policy Engine (OPA/Cedar)        │
│  (avalia contexto: IP, horario, risco)      │
├─────────────────────────────────────────────┤
│  Camada 5: RBAC + ABAC                      │
│  (controla o que o usuario pode fazer)      │
├─────────────────────────────────────────────┤
│  Camada 6: Audit + Alerting                 │
│  (detecta e responde a anomalias)           │
├─────────────────────────────────────────────┤
│  Camada 7: Data encryption                  │
│  (protege dados em repouso e transito)      │
└─────────────────────────────────────────────┘
```

### 13.12.4 Métricas de sucesso

Após implementar uma engine de política, monitore:

- **Taxa de falsos positivos**: Usuários legítimos bloqueados. Meta: < 1%.
- **Taxa de falsos negativos**: Ataques que passaram. Meta: 0% para ataques conhecidos.
- **Latência de avaliação**: Overhead adicionado a cada requisição. Meta: < 5ms p99.
- **Cobertura de políticas**: % de endpoints protegidos por políticas. Meta: 100%.
- **Tempo de resposta a incidentes**: Tempo para implementar nova política emergencial. Meta: < 5 minutos.
- **Taxa de alertas**: Freqência de alertas de segurança. Meta: sinal > ruído.

### 13.12.5 Referências

- Styra. "Open Policy Agent Documentation" (2023-present)
- AWS. "Cedar: An Open Source Language for Authorization" (2022)
- Authzed. "SpiceDB: Open Source Zanzibar" (2022-present)
- Casbin. "Casbin Authorization Library" (2017-present)
- Google. "Zanzibar: Google's Consistent, Global Authorization System" (2019)
- NIST SP 800-53 Rev. 5: Security and Privacy Controls (2020)
- NIST SP 800-162: Guide to Attribute-Based Access Control (2014)
- OWASP. "ASVS: Application Security Verification Standard" (2021)
- OWASP. "API Security Top 10" (2023)
- LGPD. "Lei Geral de Protecao de Dados" (2020)
- Bishop, M. "Computer Security: Art and Science" (2003)
- Sandhu, R. et al. "Role-Based Access Control Models" (1996)
- Fong, P.W.L. "Relationship-Based Access Control" (2013)
- Anderson, R. "Security Engineering" (2008)
- Lampson, B. "Protection" (1971)
- Saltzer, J., Schroeder, M. "The Protection of Information in Computer Systems" (1975)
- Bell, D.E., LaPadula, L.J. "Secure Computer Systems" (1973)
- Harrison, M., Ruzzo, W., Ullman, J. "Protection in Operating Systems" (1976)
- Common Criteria. "Protection Profile for Operating Systems" (2012)
- NIST. "Zero Trust Architecture" (SP 800-207, 2020)
- ISO/IEC 27001: Information Security Management (2022)
- OSSTMM: Open Source Security Testing Methodology Manual (2010)
- NIST SP 800-177: Trustworthy Email (2016)
- CERT. "Introduction to the Priority Usage Limit Concept" (2005)
- NIST. "Unified Log Framework for MAC Systems" (2021)

---

*No próximo capítulo: Ataques a Identidade — credential stuffing, brute force, session hijacking, e como o caso Misantropi4 explodiu cada uma dessas vetores.*
---

*[Capítulo anterior: 12 — Mac Dac](12-mac-dac.md)*
*[Próximo capítulo: 14 — Ataques Identidade](14-ataques-identidade.md)*
