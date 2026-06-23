# Capítulo 11 — ReBAC (Relationship-Based Access Control)

## 11.1 Fundamentos do ReBAC

Relationship-Based Access Control (ReBAC) é um modelo de autorização que toma decisões com base nas relações entre entidades, em vez de atributos isolados ou papeis estáticos. Enquanto RBAC pergunta "que papel esse sujeito tem?" e ABAC pergunta "quais atributos governam essa decisão?", ReBAC pergunta "qual é o relacionamento entre esse sujeito e esse recurso?"

A intuição fundamental de ReBAC é simples: em muitos sistemas, o controle de acesso é naturalmente expresso em termos de relações. Quem pode ver um documento? Quem está na mesma equipe. Quem pode editar um repositório? Quem tem permissão de manutenção. Quem pode ver um post no Facebook? Quem é amigo do autor ou está na mesma lista de circulo.

Essa modelagem por relações é particularmente poderosa em sistemas onde a estrutura de acesso é determinada por grafos de relacionamento — redes sociais, organizações multi-tenant, sistemas de协作, e plataformas de dados compartilhados.

### A tese central do ReBAC

A tese central do ReBAC é que relações são a abstração natural para controle de acesso em sistemas onde:

1. O acesso é determinado por conexões sociais, organizacionais ou de propriedade.
2. As relações são frequentemente atualizadas (amizades, associações, transferências).
3. A estrutura de acesso forma um grafo — não uma hierarquia plana.
4. Políticas recursivas são necessárias (acesso transitivo através de cadeias de relação).

### Modelo mental

Pense em um grafo direcionado onde:

- **Nós** são entidades: usuários, documentos, equipes, organizações.
- **Arestas** são relações: membro, proprietário, colaborador, seguidor.
- **Permissões** são derivadas de caminhos no grafo: se existe um caminho de "usuário" a "documento" através de relações permitidas, o acesso é concedido.

```
Alice --[member]--> Team-A --[owns]--> Document-1
  |                                       ^
  +--[admin]--> Organization-X --[parent]--+
```

Nesse grafo, Alice pode acessar Document-1 porque existe um caminho: Alice --[member]--> Team-A --[owns]--> Document-1.

### ReBAC vs RBAC vs ABAC

| Dimensão | RBAC | ABAC | ReBAC |
|---|---|---|---|
| Unidade de decisão | Papel | Atributo | Relação |
| Estrutura | Hierarquia plana | Espaço vetorial | Grafo |
| Expressividade | Baixa | Alta | Média-Alta |
| Performance | O(1) | O(n) | O(caminho) |
| Complexidade de gestão | Média | Alta | Média |
| Caso de uso típico | Enterprise apps | Context-sensitive | Social/sharing |

ReBAC não substitui ABAC ou RBAC — ele complementa modelos quando relações são o conceito dominante para decisões de acesso.

---

## 11.2 Grafos de Relacionamento

A fundamentação matemática do ReBAC é a teoria de grafos. Um grafo de relacionamento para controle de acesso é um grafo direcionado tipado, onde cada aresta tem um tipo de relação e cada nó tem um tipo de entidade.

### Definição formal

Um grafo de relações G é definido como:

G = (V, E, T)

Onde:
- V é o conjunto de nós (entidades).
- E é o conjunto de arestas (relações) com E ⊆ V × R × V, onde R é o conjunto de tipos de relação.
- T é a função de tipo que mapeia nós para seus tipos.

### Tipos de relações

Relações em ReBAC são tipicamente categorizadas:

- **Hierárquicas**: parent, owner, ancestor. Permitem navegação para cima/baixo em hierarquias.
- **Associativas**: member, collaborator, follower. Conectam entidades em agrupamentos.
- **Permissivas**: admin, editor, viewer. Concedem permissões diretamente.
- **Transitivas**: ancestor, descendant, contained-in. Permitem encadeamento de relações.

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


class RelationType(Enum):
    MEMBER_OF = "member_of"
    OWNS = "owns"
    ADMIN_OF = "admin_of"
    COLLABORATOR_ON = "collaborator_on"
    FOLLOWS = "follows"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    SHARED_WITH = "shared_with"
    EDITOR_OF = "editor_of"
    VIEWER_OF = "viewer_of"


class EntityType(Enum):
    USER = "user"
    TEAM = "team"
    ORGANIZATION = "organization"
    DOCUMENT = "document"
    REPOSITORY = "repository"
    FOLDER = "folder"
    PROJECT = "project"


@dataclass
class Node:
    id: str
    entity_type: EntityType
    attributes: Dict = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class Edge:
    source: str
    relation: RelationType
    target: str
    attributes: Dict = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class RelationshipGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[str, List[Edge]] = {}
        self.reverse_adjacency: Dict[str, List[Edge]] = {}

    def add_node(self, node: Node):
        self.nodes[node.id] = node
        self.adjacency.setdefault(node.id, [])
        self.reverse_adjacency.setdefault(node.id, [])

    def add_edge(self, edge: Edge):
        self.edges.append(edge)
        self.adjacency[edge.source].append(edge)
        self.reverse_adjacency[edge.target].append(edge)

    def remove_edge(self, source: str, relation: RelationType, target: str):
        self.edges = [
            e for e in self.edges
            if not (e.source == source and e.relation == relation and e.target == target)
        ]
        self.adjacency[source] = [
            e for e in self.adjacency[source]
            if not (e.relation == relation and e.target == target)
        ]
        self.reverse_adjacency[target] = [
            e for e in self.reverse_adjacency[target]
            if not (e.source == source and e.relation == relation)
        ]

    def get_outgoing(self, node_id: str,
                     relation: RelationType = None) -> List[Edge]:
        edges = self.adjacency.get(node_id, [])
        if relation:
            return [e for e in edges if e.relation == relation]
        return edges

    def get_incoming(self, node_id: str,
                     relation: RelationType = None) -> List[Edge]:
        edges = self.reverse_adjacency.get(node_id, [])
        if relation:
            return [e for e in edges if e.relation == relation]
        return edges

    def find_path(self, source: str, target: str,
                  allowed_relations: Set[RelationType] = None,
                  max_depth: int = 10) -> Optional[List[Edge]]:
        if source == target:
            return []

        visited = set()
        queue = [(source, [])]

        while queue:
            current, path = queue.pop(0)
            if current == target:
                return path
            if len(path) >= max_depth:
                continue
            if current in visited:
                continue
            visited.add(current)

            for edge in self.adjacency.get(current, []):
                if allowed_relations and edge.relation not in allowed_relations:
                    continue
                queue.append((edge.target, path + [edge]))

        return None

    def reachable_from(self, source: str,
                       allowed_relations: Set[RelationType] = None,
                       max_depth: int = 10) -> Set[str]:
        visited = set()
        queue = [(source, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            for edge in self.adjacency.get(current, []):
                if allowed_relations and edge.relation not in allowed_relations:
                    continue
                queue.append((edge.target, depth + 1))

        return visited

    def shortest_path(self, source: str, target: str,
                      allowed_relations: Set[RelationType] = None) -> Optional[List[Edge]]:
        if source == target:
            return []

        visited = {source}
        queue = [(source, [])]

        while queue:
            current, path = queue.pop(0)

            for edge in self.adjacency.get(current, []):
                if allowed_relations and edge.relation not in allowed_relations:
                    continue
                if edge.target == target:
                    return path + [edge]
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge]))

        return None
```

### Navegação em grafo para autorização

A operação fundamental de ReBAC é a navegação — seguir arestas no grafo para determinar se um caminho existe entre sujeito e recurso:

```python
class RelationshipNavigator:
    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def check_access(self, subject_id: str, resource_id: str,
                     permission: str) -> bool:
        rules = self._get_rules_for_permission(permission)
        for rule in rules:
            if self._evaluate_rule(subject_id, resource_id, rule):
                return True
        return False

    def _get_rules_for_permission(self, permission: str) -> list:
        return self.rules.get(permission, [])

    def _evaluate_rule(self, subject_id: str, resource_id: str,
                       rule: dict) -> bool:
        path = self.graph.find_path(
            source=subject_id,
            target=resource_id,
            allowed_relations=set(rule["relations"]),
            max_depth=rule.get("max_depth", 10),
        )
        if path is None:
            return False

        if "intermediate_checks" in rule:
            for edge in path:
                for check in rule["intermediate_checks"]:
                    if not self._intermediate_check(edge, check):
                        return False
        return True

    def _intermediate_check(self, edge: Edge, check: dict) -> bool:
        node = self.graph.nodes.get(edge.target)
        if not node:
            return False
        return node.attributes.get(check["attribute"]) == check["value"]
```

---

## 11.3 Google Zanzibar

Google Zanzibar é o sistema de autorização que sustenta Google Drive, Google Docs, YouTube, Google Cloud e outros serviços do Google. Seu paper de 2019 ("Zanzibar: Google's Consistent, Global Authorization System") definiu o estado da arte para sistemas de autorização baseados em relações.

### Por que Zanzibar existe

Antes do Zanzibar, o Google usava múltiplos sistemas de autorização fragmentados. Cada serviço implementava sua própria lógica, levando a inconsistências, duplicação de esforço e dificuldade de auditoria. O Zanzibar foi criado para ser o sistema unificado de autorização global.

### Conceitos fundamentais do Zanzibar

O Zanzibar modela o mundo em termos de **objects**, **relations** e **users**:

- **Object**: Qualquer entidade que pode ser protegida (documento, pasta, repositório).
- **User**: Qualquer entidade que pode ter permissão (pessoa, grupo, serviço).
- **Relation**: Uma conexão nomeada entre um user e um object (editor, viewer, owner).

O insight central do Zanzibar é que permissões são **relações computadas**. Em vez de armazenar permissões diretamente, o Zanzibar armazena relações de base e computa permissões como conjuntos de relações.

### Namespace Definitions (NDFs)

No Zanzibar, o schema do sistema é definido por Namespace Definitions:

```
definition document {
    relation owner: user
    relation editor: user | group#member
    relation viewer: user | group#member | document#viewer
    relation parent: folder

    permission view = viewer or editor or owner
    permission edit = editor or owner
    permission delete = owner
    permission share = owner or editor
}

definition folder {
    relation parent: folder
    relation owner: user
    relation editor: user | group#member
    relation viewer: user | group#member

    permission view = viewer or editor or owner
    permission edit = editor or owner
    permission create_child = editor or owner
}

definition group {
    relation member: user | group#member
}
```

Nesse schema:

- `document#viewer` significa "qualquer pessoa que seja viewer desse documento".
- `group#member` significa "qualquer pessoa que seja membro desse grupo".
- `document#viewer` em uma relation de viewer significa "herdar viewers de outro documento".
- Permissões são computadas recursivamente: `view = viewer or editor or owner` significa que owners e editors também podem ver.

### Zookie (Zanzibar Look-alike) e Consistência

O Zanzibar usa **Zookies** — tokens compactos que representam o estado do sistema em um ponto no tempo. Quando um cliente pede uma verificação de autorização, ele pode enviar um Zookie para garantir que a decisão é tomada com base no estado mais recente que ele viu.

```
AuthorizationCheckRequest:
  object: document:readme
  relation: viewer
  user: alice
  zookie: token_v3_abc123   // garantir consistência com esse estado
```

O servidor garante que, se o Zookie é do token v3_abc123, a decisão é tomada com base em um estado pelo menos tão recente quanto o que foi representado por aquele token.

### Algoritmo de resolução

O algoritmo principal do Zanzibar é um DFS (Depth-First Search) sobre o grafo de relações, com memoização para evitar recomputação:

```python
class ZanzibarResolver:
    def __init__(self, namespace_store: NamespaceStore,
                 relation_store: RelationStore):
        self.namespaces = namespace_store
        self.relations = relation_store

    def check(self, check_request: CheckRequest) -> bool:
        namespace = self.namespaces.get(check_request.object_type)
        permission_def = namespace.permissions.get(check_request.permission)

        if permission_def is None:
            return False

        relations_needed = self._extract_relations(permission_def)
        return self._check_relations(
            check_request.object_id,
            relations_needed,
            check_request.user_id,
        )

    def _check_relations(self, object_id: str, relations: list,
                         user_id: str) -> bool:
        for relation_name in relations:
            if self._check_relation(object_id, relation_name, user_id):
                return True
        return False

    def _check_relation(self, object_id: str, relation_name: str,
                        user_id: str) -> bool:
        tuples = self.relations.list(
            object_type=None,
            object_id=object_id,
            relation=relation_name,
        )

        for t in tuples:
            if t.user_id == user_id:
                return True
            if "#" in t.user_id:
                ref_type, ref_relation = t.user_id.split("#")
                if self._check_relation(t.object_id, ref_relation, user_id):
                    return True
        return False

    def _extract_relations(self, permission_def) -> list:
        if isinstance(permission_def, str):
            return [permission_def]
        relations = []
        for item in permission_def:
            if item.startswith("not "):
                continue
            if " or " in item:
                for part in item.split(" or "):
                    relations.append(part.strip())
            else:
                relations.append(item)
        return relations
```

### Expansão do Zanzibar

O modelo Zanzibar foi expandido pelo Google em trabalhos subsequentes:

- **Zanzibar (2019)**: Modelo base com relações computadas.
- **Zanzibar++ (2023)**: Extensões para controle de acesso condicional, permissões temporárias e políticas de compliance.

---

## 11.4 SpiceDB

SpiceDB é uma implementação open-source do modelo Zanzibar, desenvolvida pela AuthZed. É a implementação open-source de referência para sistemas de autorização baseados em relações.

### Arquitetura do SpiceDB

```
+-------------------+
|      Client       |
+--------+----------+
         |
    gRPC/REST
         |
+--------v----------+
|    SpiceDB API     |
+--------+----------+
         |
    +----+----+
    |         |
+---v---+ +---v---+
| Graph | | Cache |
| Store | | Layer |
+---+---+ +-------+
    |
+---v----------+
| PostgreSQL / |
| CockroachDB  |
+--------------+
```

### Definição de schema no SpiceDB

```python
class SpiceDBSchema:
    def __init__(self):
        self.schema = """
definition user {}

definition document {
    relation owner: user
    relation editor: user | group#member
    relation viewer: user | group#member
    relation parent_folder: folder

    permission view = viewer + editor + owner
    permission edit = editor + owner
    permission delete = owner
    permission share = owner + editor
}

definition folder {
    relation parent: folder
    relation owner: user
    relation editor: user | group#member
    relation viewer: user | group#member

    permission view = viewer + editor + owner
    permission edit = editor + owner
    permission create_child = editor + owner
    permission view_recursive = view + parent_folder->view_recursive
}

definition group {
    relation member: user | group#member
}

definition organization {
    relation admin: user
    relation member: user | group#member
    relation billing_admin: user

    permission manage_org = admin
    permission manage_billing = billing_admin + admin
    permission access = member
}
"""

    def get_schema(self) -> str:
        return self.schema
```

### Operações do SpiceDB

```python
import httpx
from typing import List, Optional


class SpiceDBClient:
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def write_tuples(self, tuples: List[dict]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/relationships/write",
                headers=self.headers,
                json={
                    "updates": [
                        {
                            "operation": "TOUCH",
                            "relationship": t
                        } for t in tuples
                    ]
                },
            )
            return response.json()

    async def delete_tuples(self, tuples: List[dict]) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/relationships/delete",
                headers=self.headers,
                json={
                    "deletions": [
                        {
                            "relationship_filter": {
                                "resource_type": t["resource"]["object_type"],
                                "optional_resource_id": t["resource"]["object_id"],
                                "relation": t["relation"],
                                "optional_subject_filter": {
                                    "subject_type": t["subject"]["object_type"],
                                    "optional_subject_id": t["subject"]["object_id"],
                                },
                            }
                        } for t in tuples
                    ]
                },
            )
            return response.json()

    async def check(self, resource_type: str, resource_id: str,
                    permission: str, subject_type: str,
                    subject_id: str, zookie: str = None) -> dict:
        body = {
            "consistency": {"minimizeLatency": True},
            "resource": {
                "object_type": resource_type,
                "object_id": resource_id,
            },
            "permission": permission,
            "subject": {
                "object": {
                    "object_type": subject_type,
                    "object_id": subject_id,
                },
            },
        }
        if zookie:
            body["consistency"]["atExactSnapshot"] = {"token": zookie}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/permissions/check",
                headers=self.headers,
                json=body,
            )
            return response.json()

    async def lookup_resources(self, resource_type: str, permission: str,
                               subject_type: str,
                               subject_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/permissions/lookup-resources",
                headers=self.headers,
                json={
                    "consistency": {"minimizeLatency": True},
                    "resourceObjectType": resource_type,
                    "permission": permission,
                    "subject": {
                        "object": {
                            "object_type": subject_type,
                            "object_id": subject_id,
                        },
                    },
                },
            )
            return response.json()

    async def lookup_subjects(self, resource_type: str, resource_id: str,
                              permission: str,
                              subject_type: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/permissions/lookup-subjects",
                headers=self.headers,
                json={
                    "consistency": {"minimizeLatency": True},
                    "resource": {
                        "object_type": resource_type,
                        "object_id": resource_id,
                    },
                    "permission": permission,
                    "subjectObjectType": subject_type,
                },
            )
            return response.json()

    async def read_relationships(self, resource_type: str = None,
                                  resource_id: str = None,
                                  relation: str = None) -> dict:
        filter_obj = {}
        if resource_type:
            filter_obj["resource_type"] = resource_type
        if resource_id:
            filter_obj["optional_resource_id"] = resource_id
        if relation:
            filter_obj["relation"] = relation

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/relationships/read",
                headers=self.headers,
                json={
                    "consistency": {"minimizeLatency": True},
                    "relationshipFilter": filter_obj,
                },
            )
            return response.json()
```

### Vantagens do SpiceDB sobre implementação própria

1. **Consistência serializável**: Usa CockroachDB ou PostgreSQL com transações ACID.
2. **Performance**: Cache em memória com invalidação baseada em eventos.
3. **API gRPC**: Interface de alta performance com suporte a streaming.
4. **Observabilidade**: Métricas, tracing e logging integrados.
5. **Escalabilidade horizontal**: Pode ser escalado com réplicas de leitura.

---

## 11.5 Ory Keto

Ory Keto é um componente do ecossistema Ory focado em verificação e lookup de autorização. Ele implementa um modelo inspirado no Zanzibar mas com extensões para uso generalizado.

### Conceitos do Keto

- **Namespace**: Define o tipo de entidade e suas relações.
- **Relation Tuple**: Uma tripla (object, relation, subject) que representa uma relação.
- **Check**: Verificar se um subject tem uma relação com um object.
- **Expand**: Expandir todas as relações computadas de um object.

### Definição de schema no Keto

```yaml
# Keto namespace configuration
namespaces:
  - name: documents
    config:
      subjects:
        - users
        - groups#members
      relations:
        - owner
        - editor
        - viewer
      permissions:
        - view
        - edit
        - delete

  - name: groups
    config:
      subjects:
        - users
        - groups#members
      relations:
        - member

  - name: organizations
    config:
      subjects:
        - users
        - groups#members
      relations:
        - admin
        - member
      permissions:
        - manage
        - access
```

### Uso do Keto

```python
import httpx
from typing import List, Optional


class OryKetoClient:
    def __init__(self, read_url: str, write_url: str, check_url: str):
        self.read_url = read_url
        self.write_url = write_url
        self.check_url = check_url

    async def create_relation(self, namespace: str, object_id: str,
                               relation: str, subject_id: str,
                               subject_set_namespace: str = None,
                               subject_set_relation: str = None) -> dict:
        subject = {"id": subject_id}
        if subject_set_namespace:
            subject["namespace"] = subject_set_namespace
        if subject_set_relation:
            subject["relation"] = subject_set_relation

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.write_url}/relation-tuples",
                json={
                    "namespace": namespace,
                    "object": object_id,
                    "relation": relation,
                    "subject": subject,
                },
            )
            return response.json()

    async def check(self, namespace: str, object_id: str,
                    relation: str, subject_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.check_url}/check",
                params={
                    "namespace": namespace,
                    "object": object_id,
                    "relation": relation,
                    "subject_id": subject_id,
                },
            )
            return response.json()

    async def expand(self, namespace: str, object_id: str,
                     relation: str, depth: int = 10) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.read_url}/expand",
                params={
                    "namespace": namespace,
                    "object": object_id,
                    "relation": relation,
                    "depth": depth,
                },
            )
            return response.json()

    async def query_relation_tuples(self, namespace: str = None,
                                     object_id: str = None,
                                     relation: str = None,
                                     subject_id: str = None) -> List[dict]:
        params = {}
        if namespace:
            params["namespace"] = namespace
        if object_id:
            params["object"] = object_id
        if relation:
            params["relation"] = relation
        if subject_id:
            params["subject_id"] = subject_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.read_url}/relation-tuples",
                params=params,
            )
            return response.json()
```

### Keto vs SpiceDB

| Aspecto | Ory Keto | SpiceDB |
|---|---|---|
| Protocolo | REST + gRPC | gRPC |
| Backend | SQL | SQL (CockroachDB) |
| Consistência | Eventually | Serializable |
| Ecossistema | Ory Suite | Independente |
| Maturity | Alta | Alta |
| License | Apache 2.0 | Apache 2.0 |

---

## 11.6 Casbin com ReBAC

Casbin é um framework de autorização open-source que suporta múltiplos modelos, incluindo ReBAC. Sua versatilidade e performance o tornam uma escolha popular para projetos que precisam de flexibilidade.

### Modelo ReBAC no Casbin

```
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _
g2 = _, _

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act || \
    r.sub == r.obj.owner || \
    r.sub in r.obj.collaborators || \
    g2(r.sub, r.obj.team) && r.obj.team_permission == r.act
```

### Modelos ReBAC no Casbin

```python
import casbin
from casbin import persist
from typing import List, Optional, Dict


class CasbinReBACManager:
    def __init__(self, model_path: str, adapter: persist.Adapter):
        self.enforcer = casbin.Enforcer(model_path, adapter)

    def add_user(self, user: str):
        pass

    def add_group(self, group: str):
        pass

    def add_user_to_group(self, user: str, group: str):
        self.enforcer.add_grouping_policy(user, group)

    def add_object(self, obj: str, owner: str,
                   collaborators: List[str] = None,
                   team: str = None):
        self.enforcer.add_policy(owner, obj, "owner")
        if collaborators:
            for c in collaborators:
                self.enforcer.add_policy(c, obj, "collaborator")
        if team:
            self.enforcer.add_policy(team, obj, "team_member")

    def check_access(self, subject: str, resource: str,
                     action: str) -> bool:
        return self.enforcer.enforce(subject, resource, action)

    def get_allowed_resources(self, subject: str,
                              action: str) -> List[str]:
        all_resources = self._get_all_resources()
        return [r for r in all_resources
                if self.check_access(subject, r, action)]

    def get_allowed_subjects(self, resource: str,
                             action: str) -> List[str]:
        all_users = self._get_all_users()
        return [u for u in all_users
                if self.check_access(u, resource, action)]

    def remove_user(self, user: str):
        self.enforcer.remove_filtered_policy(0, user)

    def remove_group(self, group: str):
        self.enforcer.remove_filtered_grouping_policy(0, group)

    def _get_all_resources(self) -> List[str]:
        policy = self.enforcer.get_all_objects()
        return list(set(policy))

    def _get_all_users(self) -> List[str]:
        policy = self.enforcer.get_all_subjects()
        groups = self.enforcer.get_all_roles()
        return list(set(policy + groups))


class CasbinReBACAdapter:
    def __init__(self, connection_string: str):
        self.conn = connection_string

    def load_policy(self, model):
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT sub, obj, act FROM casbin_rules WHERE p_type = 'p'"
            )
            for row in cursor:
                model.add_policy(row[0], row[1], row[2])

            cursor = conn.execute(
                "SELECT sub, obj FROM casbin_rules WHERE p_type = 'g'"
            )
            for row in cursor:
                model.add_grouping_policy(row[0], row[1])

    def save_policy(self, model):
        with self._connect() as conn:
            conn.execute("DELETE FROM casbin_rules")
            for policy in model.get_all_policy():
                conn.execute(
                    "INSERT INTO casbin_rules (p_type, sub, obj, act) VALUES (?, ?, ?, ?)",
                    ("p", policy[0], policy[1], policy[2]),
                )
            for group in model.get_all_grouping_policy():
                conn.execute(
                    "INSERT INTO casbin_rules (p_type, sub, obj) VALUES (?, ?, ?)",
                    ("g", group[0], group[1]),
                )

    def add_policy(self, sub: str, obj: str, act: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO casbin_rules (p_type, sub, obj, act) VALUES (?, ?, ?, ?)",
                ("p", sub, obj, act),
            )

    def remove_policy(self, sub: str, obj: str, act: str):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM casbin_rules WHERE p_type = 'p' AND sub = ? AND obj = ? AND act = ?",
                (sub, obj, act),
            )

    def _connect(self):
        import sqlite3
        return sqlite3.connect(self.conn)
```

### Modelo ReBAC avançado no Casbin

```
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act, eft

[role_definition]
g = _, _
g2 = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = (g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act) || \
    (r.obj.parent.owner == r.sub) || \
    (r.obj.parent.collaborators.contains(r.sub)) || \
    (g2(r.sub, r.obj.parent.team) && r.act in r.obj.parent.team_permissions) || \
    (r.sub == r.obj.sharing.subject && r.act in r.obj.sharing.allowed_actions)
```

---

## 11.7 Autorização em Grafos Sociais

As redes sociais são o caso de uso natural para ReBAC. Controle de acesso em feeds, mensagens privadas, grupos e conteúdo é fundamentalmente relacional.

### Modelo de grafo social

```python
class SocialGraph:
    def __init__(self):
        self.graph = RelationshipGraph()

    def add_friendship(self, user1: str, user2: str):
        self.graph.add_edge(Edge(
            source=user1, relation=RelationType.FOLLOWS, target=user2
        ))
        self.graph.add_edge(Edge(
            source=user2, relation=RelationType.FOLLOWS, target=user1
        ))

    def add_group_membership(self, user: str, group: str):
        self.graph.add_edge(Edge(
            source=user, relation=RelationType.MEMBER_OF, target=group
        ))

    def add_post(self, user: str, post_id: str, visibility: str):
        self.graph.add_node(Node(
            id=post_id, entity_type=EntityType.DOCUMENT,
            attributes={"visibility": visibility, "author": user}
        ))
        self.graph.add_edge(Edge(
            source=post_id, relation=RelationType.OWNS, target=user
        ))

    def can_view_post(self, viewer: str, post_id: str) -> bool:
        post = self.graph.nodes.get(post_id)
        if not post:
            return False

        if post.attributes.get("visibility") == "public":
            return True

        if post.attributes.get("visibility") == "friends":
            author = post.attributes.get("author")
            return self._are_friends(viewer, author)

        if post.attributes.get("visibility") == "group":
            author = post.attributes.get("author")
            author_groups = {
                e.target for e in self.graph.get_outgoing(
                    author, RelationType.MEMBER_OF
                )
            }
            viewer_groups = {
                e.target for e in self.graph.get_outgoing(
                    viewer, RelationType.MEMBER_OF
                )
            }
            return bool(author_groups & viewer_groups)

        if post.attributes.get("visibility") == "private":
            return post.attributes.get("author") == viewer

        return False

    def can_comment(self, commenter: str, post_id: str) -> bool:
        post = self.graph.nodes.get(post_id)
        if not post:
            return False

        if not self.can_view_post(commenter, post_id):
            return False

        post = self.graph.nodes[post_id]
        if post.attributes.get("comments_disabled"):
            return False

        author = post.attributes.get("author")
        if post.attributes.get("commenters") == "friends_only":
            return self._are_friends(commenter, author)

        return True

    def _are_friends(self, user1: str, user2: str) -> bool:
        edges1 = self.graph.get_outgoing(user1, RelationType.FOLLOWS)
        edges2 = self.graph.get_outgoing(user2, RelationType.FOLLOWS)
        targets1 = {e.target for e in edges1}
        targets2 = {e.target for e in edges2}
        return user2 in targets1 and user1 in targets2
```

### Controle de acesso a feed

```python
class FeedAccessControl:
    def __init__(self, social_graph: SocialGraph):
        self.graph = social_graph

    def filter_feed(self, viewer: str, post_ids: List[str]) -> List[str]:
        return [pid for pid in post_ids
                if self.graph.can_view_post(viewer, pid)]

    def get_visible_posts_from_user(self, viewer: str,
                                     author: str) -> List[str]:
        outgoing = self.graph.get_outgoing(author, RelationType.OWNS)
        post_ids = [e.source for e in outgoing
                    if self.graph.nodes.get(e.source) and
                    self.graph.nodes[e.source].entity_type == EntityType.DOCUMENT]

        return [pid for pid in post_ids
                if self.graph.can_view_post(viewer, pid)]

    def get_mutual_friends_content(self, user: str,
                                    limit: int = 100) -> List[str]:
        friends = self._get_friends(user)
        visible_posts = []

        for friend in friends:
            posts = self.get_visible_posts_from_user(user, friend)
            visible_posts.extend(posts)

        return visible_posts[:limit]

    def _get_friends(self, user: str) -> List[str]:
        outgoing = self.graph.get_outgoing(user, RelationType.FOLLOWS)
        friends = []
        for e in outgoing:
            reverse = self.graph.get_outgoing(e.target, RelationType.FOLLOWS)
            if any(r.target == user for r in reverse):
                friends.append(e.target)
        return friends
```

---

## 11.8 ReBAC Multi-Tenant

Em sistemas multi-tenant, ReBAC precisa lidar com isolamento entre tenants enquanto permite relações intra-tenant.

### Modelo de isolamento

```python
class MultiTenantReBAC:
    def __init__(self):
        self.tenant_graphs: Dict[str, RelationshipGraph] = {}
        self.global_graph = RelationshipGraph()

    def create_tenant(self, tenant_id: str):
        self.tenant_graphs[tenant_id] = RelationshipGraph()

    def add_tenant_relation(self, tenant_id: str, source: str,
                            relation: RelationType, target: str):
        graph = self.tenant_graphs[tenant_id]
        graph.add_edge(Edge(
            source=f"{tenant_id}:{source}",
            relation=relation,
            target=f"{tenant_id}:{target}",
        ))

    def add_cross_tenant_relation(self, source_tenant: str, source: str,
                                   relation: RelationType,
                                   target_tenant: str, target: str):
        self.global_graph.add_edge(Edge(
            source=f"{source_tenant}:{source}",
            relation=relation,
            target=f"{target_tenant}:{target}",
        ))

    def check_tenant_access(self, tenant_id: str, subject: str,
                             resource: str, permission: str) -> bool:
        graph = self.tenant_graphs[tenant_id]
        navigator = RelationshipNavigator(graph)
        return navigator.check_access(
            f"{tenant_id}:{subject}",
            f"{tenant_id}:{resource}",
            permission,
        )

    def check_cross_tenant_access(self, subject_tenant: str, subject: str,
                                   resource_tenant: str, resource: str,
                                   permission: str) -> bool:
        if subject_tenant != resource_tenant:
            return False

        graph = self.tenant_graphs[subject_tenant]
        navigator = RelationshipNavigator(graph)
        return navigator.check_access(
            f"{subject_tenant}:{subject}",
            f"{subject_tenant}:{resource}",
            permission,
        )
```

### RBAC + ReBAC híbrido multi-tenant

```python
class HybridMultiTenantAuthZ:
    def __init__(self, rebac: MultiTenantReBAC, rbac: RBACEngine):
        self.rebac = rebac
        self.rbac = rbac

    def check_access(self, tenant_id: str, user_id: str,
                     resource_id: str, action: str) -> bool:
        if not self.rbac.has_role(tenant_id, user_id, f"tenant:{tenant_id}:role"):
            return False

        return self.rebac.check_tenant_access(
            tenant_id, user_id, resource_id, action
        )
```

---

## 11.9 Comparação com RBAC e ABAC

### Quando usar ReBAC

- **Redes sociais**: Acesso determinado por amizades, seguidores, membros de grupo.
- **Plataformas de compartilhamento**: Documentos, pastas, repositórios compartilhados.
- **Organizações complexas**: Hierarquias com herança transitiva.
- **Multi-tenant SaaS**: Isolamento de tenant baseado em relações.
- **Sistemas de协作**: Edição colaborativa com permissões por relação.

### Quando NÃO usar ReBAC

- **Controles contextuais**: Se a decisão depende de hora, localização ou risco, ABAC é mais adequado.
- **Papeis estáticos**: Se a estrutura de acesso é hierárquica e estável, RBAC é mais simples.
- **Performance crítica**: Consultas em grafos podem ser lentas para grafos grandes sem cache adequado.
- **Compliance simples**: Se requisitos regulatórios são simples, RBAC pode ser suficiente.

### Combinação de modelos

A maioria dos sistemas em produção combina múltiplos modelos. Um padrão comum é:

1. **RBAC para macro-controle**: "Usuários autenticados podem acessar o sistema."
2. **ReBAC para relações**: "Usuários em um grupo podem acessar recursos do grupo."
3. **ABAC para restrições contextuais**: "Mas apenas durante o horário comercial e com MFA."

```python
class CombinedAccessControl:
    def __init__(self, rbac: RBACEngine, rebac: MultiTenantReBAC,
                 abac: ABACEngine):
        self.rbac = rbac
        self.rebac = rebac
        self.abac = abac

    def check_access(self, tenant_id: str, user_id: str,
                     resource_id: str, action: str,
                     context: dict) -> bool:
        if not self.rbac.is_authenticated(user_id):
            return False

        if not self.rebac.check_tenant_access(
            tenant_id, user_id, resource_id, action
        ):
            return False

        request = AccessRequest(
            subject={"id": user_id, "tenant_id": tenant_id},
            resource={"id": resource_id},
            action={"verb": action},
            environment=context,
        )
        decision = self.abac.evaluate(request)
        return decision.decision == Decision.PERMIT
```

---

## 11.10 Zed (OpenZiti)

OpenZiti é um framework de rede zero-trust que inclui autorização baseada em relações. O componente Zed fornece um mecanismo de política de rede onde identidades e serviços são conectados por relações.

### Conceitos do Zed

- **Identity**: Uma entidade que pode acessar serviços (usuário, dispositivo, serviço).
- **Service**: Um recurso de rede que precisa ser protegido.
- **Policy**: Define quais identities podem acessar quais services.
- **Edge Router**: Intercepta tráfego e aplica políticas.

### Modelo de política Zed

```python
class ZedPolicy:
    def __init__(self):
        self.policies = []

    def add_policy(self, name: str, identity_roles: List[str],
                   service_roles: List[str],
                   semantic: str = "AnyOf"):
        self.policies.append({
            "name": name,
            "type": "Service",
            "semantic": semantic,
            "identityRoles": identity_roles,
            "serviceRoles": service_roles,
        })

    def add_service_policy(self, service_name: str,
                            allowed_identities: List[str]):
        self.add_policy(
            name=f"policy-{service_name}",
            identity_roles=[f"#identity://{i}" for i in allowed_identities],
            service_roles=[f"#service://{service_name}"],
        )
```

### Integração Zed com aplicações

```python
class ZedApplicationAuthZ:
    def __init__(self, zed_client, policy_engine):
        self.zed = zed_client
        self.engine = policy_engine

    def authorize_request(self, identity_id: str, service_id: str,
                          action: str) -> bool:
        return self.zed.check_access(identity_id, service_id, action)

    def filter_services(self, identity_id: str) -> List[str]:
        return self.zed.list_accessible_services(identity_id)

    def register_service(self, service_id: str, attributes: dict):
        self.zed.register_service(service_id, attributes)
```

---

## 11.11 Exemplos de Implementação

### Implementação completa de ReBAC em Go

```go
package rebac

import (
	"fmt"
	"sync"
)

type RelationType string

const (
	MemberOf     RelationType = "member_of"
	Owns         RelationType = "owns"
	AdminOf      RelationType = "admin_of"
	Collaborator RelationType = "collaborator"
	Follower     RelationType = "follows"
	SharedWith   RelationType = "shared_with"
)

type Node struct {
	ID         string
 EntityType string
	Attributes map[string]interface{}
}

type Edge struct {
	Source   string
	Relation RelationType
	Target   string
}

type Graph struct {
	mu          sync.RWMutex
	nodes       map[string]*Node
	edges       []Edge
	adjacency   map[string][]Edge
	reverseAdj  map[string][]Edge
}

func NewGraph() *Graph {
	return &Graph{
		nodes:      make(map[string]*Node),
		edges:      make([]Edge, 0),
		adjacency:  make(map[string][]Edge),
		reverseAdj: make(map[string][]Edge),
	}
}

func (g *Graph) AddNode(node *Node) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.nodes[node.ID] = node
	if _, ok := g.adjacency[node.ID]; !ok {
		g.adjacency[node.ID] = make([]Edge, 0)
	}
	if _, ok := g.reverseAdj[node.ID]; !ok {
		g.reverseAdj[node.ID] = make([]Edge, 0)
	}
}

func (g *Graph) AddEdge(edge Edge) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.edges = append(g.edges, edge)
	g.adjacency[edge.Source] = append(g.adjacency[edge.Source], edge)
	g.reverseAdj[edge.Target] = append(g.reverseAdj[edge.Target], edge)
}

func (g *Graph) RemoveEdge(source string, relation RelationType, target string) {
	g.mu.Lock()
	defer g.mu.Unlock()

	newEdges := make([]Edge, 0)
	for _, e := range g.edges {
		if !(e.Source == source && e.Relation == relation && e.Target == target) {
			newEdges = append(newEdges, e)
		}
	}
	g.edges = newEdges

	newAdj := make([]Edge, 0)
	for _, e := range g.adjacency[source] {
		if !(e.Relation == relation && e.Target == target) {
			newAdj = append(newAdj, e)
		}
	}
	g.adjacency[source] = newAdj
}

func (g *Graph) FindPath(source, target string, allowedRelations map[RelationType]bool, maxDepth int) []Edge {
	if source == target {
		return []Edge{}
	}

	type queueItem struct {
		node string
		path []Edge
	}

	visited := make(map[string]bool)
	queue := []queueItem{{node: source, path: []Edge{}}}

	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]

		if current.node == target {
			return current.path
		}
		if len(current.path) >= maxDepth {
			continue
		}
		if visited[current.node] {
			continue
		}
		visited[current.node] = true

		for _, edge := range g.adjacency[current.node] {
			if allowedRelations != nil && !allowedRelations[edge.Relation] {
				continue
			}
			newPath := make([]Edge, len(current.path))
			copy(newPath, current.path)
			queue = append(queue, queueItem{
				node: edge.Target,
				path: append(newPath, edge),
			})
		}
	}

	return nil
}

func (g *Graph) Reachable(source string, allowedRelations map[RelationType]bool, maxDepth int) map[string]bool {
	visited := make(map[string]bool)
	type item struct {
		node  string
		depth int
	}
	queue := []item{{node: source, depth: 0}}

	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]

		if visited[current.node] || current.depth > maxDepth {
			continue
		}
		visited[current.node] = true

		for _, edge := range g.adjacency[current.node] {
			if allowedRelations != nil && !allowedRelations[edge.Relation] {
				continue
			}
			queue = append(queue, item{
				node:  edge.Target,
				depth: current.depth + 1,
			})
		}
	}

	return visited
}

type AccessPolicy struct {
	Permission      string
	AllowedRelations []RelationType
	MaxDepth        int
	IntermediateChecks []IntermediateCheck
}

type IntermediateCheck struct {
	Attribute string
	Value     interface{}
}

type Authorizer struct {
	graph  *Graph
	policies map[string]AccessPolicy
}

func NewAuthorizer(graph *Graph) *Authorizer {
	return &Authorizer{
		graph:    graph,
		policies: make(map[string]AccessPolicy),
	}
}

func (a *Authorizer) AddPolicy(policy AccessPolicy) {
	a.policies[policy.Permission] = policy
}

func (a *Authorizer) CheckAccess(subjectID, resourceID, permission string) bool {
	policy, ok := a.policies[permission]
	if !ok {
		return false
	}

	allowedRelations := make(map[RelationType]bool)
	for _, r := range policy.AllowedRelations {
		allowedRelations[r] = true
	}

	path := a.graph.FindPath(subjectID, resourceID, allowedRelations, policy.MaxDepth)
	if path == nil {
		return false
	}

	if len(path) == 0 {
		return true
	}

	if len(policy.IntermediateChecks) > 0 {
		for _, edge := range path {
			node, ok := a.graph.nodes[edge.Target]
			if !ok {
				return false
			}
			for _, check := range policy.IntermediateChecks {
				if node.Attributes[check.Attribute] != check.Value {
					return false
				}
			}
		}
	}

	return true
}

func (a *Authorizer) LookupAccessible(subjectID, permission string) []string {
	policy, ok := a.policies[permission]
	if !ok {
		return []string{}
	}

	allowedRelations := make(map[RelationType]bool)
	for _, r := range policy.AllowedRelations {
		allowedRelations[r] = true
	}

	reachable := a.graph.Reachable(subjectID, allowedRelations, policy.MaxDepth)
	resources := make([]string, 0)
	for id := range reachable {
		if id != subjectID {
			node, ok := a.graph.nodes[id]
			if ok && node.EntityType == "resource" {
				resources = append(resources, id)
			}
		}
	}
	return resources
}
```

### Exemplo: Plataforma de compartilhamento de documentos

```python
class DocumentSharingPlatform:
    def __init__(self):
        self.graph = RelationshipGraph()
        self.authorizer = Authorizer(self.graph)
        self._setup_policies()

    def _setup_policies(self):
        self.authorizer.add_policy(AccessPolicy(
            permission="view",
            allowed_relations=[RelationType.OWNS, RelationType.COLLABORATOR_ON,
                              RelationType.SHARED_WITH, RelationType.MEMBER_OF],
            max_depth=5,
        ))
        self.authorizer.add_policy(AccessPolicy(
            permission="edit",
            allowed_relations=[RelationType.OWNS, RelationType.COLLABORATOR_ON],
            max_depth=2,
        ))
        self.authorizer.add_policy(AccessPolicy(
            permission="share",
            allowed_relations=[RelationType.OWNS],
            max_depth=1,
        ))
        self.authorizer.add_policy(AccessPolicy(
            permission="delete",
            allowed_relations=[RelationType.OWNS],
            max_depth=1,
        ))

    def create_organization(self, org_id: str, admin_id: str):
        self.graph.add_node(Node(
            id=org_id, entity_type="organization",
            attributes={"admin": admin_id}
        ))
        self.graph.add_edge(Edge(
            source=admin_id, relation=RelationType.ADMIN_OF, target=org_id
        ))

    def create_team(self, team_id: str, org_id: str):
        self.graph.add_node(Node(
            id=team_id, entity_type="team"
        ))
        self.graph.add_edge(Edge(
            source=org_id, relation=RelationType.OWNS, target=team_id
        ))

    def add_team_member(self, user_id: str, team_id: str):
        self.graph.add_edge(Edge(
            source=user_id, relation=RelationType.MEMBER_OF, target=team_id
        ))

    def create_document(self, doc_id: str, owner_id: str,
                        team_id: str = None):
        self.graph.add_node(Node(
            id=doc_id, entity_type="document",
            attributes={"owner": owner_id}
        ))
        self.graph.add_edge(Edge(
            source=owner_id, relation=RelationType.OWNS, target=doc_id
        ))
        if team_id:
            self.graph.add_edge(Edge(
                source=team_id, relation=RelationType.COLLABORATOR_ON, target=doc_id
            ))

    def share_document(self, doc_id: str, user_id: str,
                       permission: str, shared_by: str):
        if not self.authorizer.check_access(shared_by, doc_id, "share"):
            raise PermissionError("Cannot share this document")

        if permission == "edit":
            self.graph.add_edge(Edge(
                source=user_id, relation=RelationType.COLLABORATOR_ON, target=doc_id
            ))
        elif permission == "view":
            self.graph.add_edge(Edge(
                source=user_id, relation=RelationType.SHARED_WITH, target=doc_id
            ))

    def check_access(self, user_id: str, doc_id: str,
                     permission: str) -> bool:
        return self.authorizer.check_access(user_id, doc_id, permission)

    def get_accessible_documents(self, user_id: str,
                                  permission: str) -> List[str]:
        return self.authorizer.LookupAccessible(user_id, permission)

    def remove_access(self, user_id: str, doc_id: str,
                      relation: RelationType):
        self.graph.remove_edge(user_id, relation, doc_id)

    def get_document_sharers(self, doc_id: str) -> List[str]:
        incoming = self.graph.get_incoming(doc_id)
        return list(set(e.source for e in incoming))
```

### Exemplo: Rede social com controle de acesso

```python
class SocialNetwork:
    def __init__(self):
        self.graph = RelationshipGraph()
        self.authorizer = Authorizer(self.graph)

    def create_user(self, user_id: str, name: str):
        self.graph.add_node(Node(
            id=user_id, entity_type="user",
            attributes={"name": name}
        ))

    def follow(self, follower_id: str, followee_id: str):
        self.graph.add_edge(Edge(
            source=follower_id, relation=RelationType.FOLLOWER, target=followee_id
        ))

    def create_post(self, post_id: str, author_id: str, visibility: str):
        self.graph.add_node(Node(
            id=post_id, entity_type="post",
            attributes={"author": author_id, "visibility": visibility}
        ))
        self.graph.add_edge(Edge(
            source=author_id, relation=RelationType.OWNS, target=post_id
        ))

    def create_group(self, group_id: str, creator_id: str):
        self.graph.add_node(Node(
            id=group_id, entity_type="group"
        ))
        self.graph.add_edge(Edge(
            source=creator_id, relation=RelationType.OWNS, target=group_id
        ))
        self.graph.add_edge(Edge(
            source=creator_id, relation=RelationType.MEMBER_OF, target=group_id
        ))

    def join_group(self, user_id: str, group_id: str):
        self.graph.add_edge(Edge(
            source=user_id, relation=RelationType.MEMBER_OF, target=group_id
        ))

    def can_view_post(self, viewer_id: str, post_id: str) -> bool:
        post_node = self.graph.nodes.get(post_id)
        if not post_node:
            return False

        visibility = post_node.attributes.get("visibility", "private")

        if visibility == "public":
            return True

        if visibility == "followers":
            author = post_node.attributes.get("author")
            return self._is_follower(viewer_id, author)

        if visibility == "friends":
            author = post_node.attributes.get("author")
            return self._are_mutual_friends(viewer_id, author)

        if visibility == "group":
            author = post_node.attributes.get("author")
            author_groups = self._get_user_groups(author)
            viewer_groups = self._get_user_groups(viewer_id)
            return bool(author_groups & viewer_groups)

        if visibility == "private":
            return viewer_id == post_node.attributes.get("author")

        return False

    def get_feed(self, user_id: str, limit: int = 50) -> List[str]:
        following = self._get_following(user_id)
        feed = []
        for followee in following:
            posts = self._get_user_posts(followee)
            for post_id in posts:
                if self.can_view_post(user_id, post_id):
                    feed.append(post_id)
        return feed[:limit]

    def _is_follower(self, follower_id: str, followee_id: str) -> bool:
        edges = self.graph.get_outgoing(follower_id, RelationType.FOLLOWER)
        return any(e.target == followee_id for e in edges)

    def _are_mutual_friends(self, user1: str, user2: str) -> bool:
        return self._is_follower(user1, user2) and self._is_follower(user2, user1)

    def _get_user_groups(self, user_id: str) -> set:
        edges = self.graph.get_outgoing(user_id, RelationType.MEMBER_OF)
        return {e.target for e in edges}

    def _get_following(self, user_id: str) -> List[str]:
        edges = self.graph.get_outgoing(user_id, RelationType.FOLLOWER)
        return [e.target for e in edges]

    def _get_user_posts(self, user_id: str) -> List[str]:
        edges = self.graph.get_outgoing(user_id, RelationType.OWNS)
        return [e.source for e in edges
                if self.graph.nodes.get(e.source) and
                self.graph.nodes[e.source].entity_type == "post"]
```

## 11.12 Testing e Validação de ReBAC

Testar sistemas ReBAC requer uma abordagem diferente de RBAC ou ABAC, porque as decisões dependem da topologia do grafo de relações — e mudanças em uma relação podem afetar acessos em cadeia.

### Testes de grafo

```python
import pytest
from typing import Set


class TestRelationshipGraph:
    def setup_method(self):
        self.graph = RelationshipGraph()

    def test_add_node_and_retrieve(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        assert "user-1" in self.graph.nodes
        assert self.graph.nodes["user-1"].entity_type == EntityType.USER

    def test_add_edge_and_traverse(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(
            source="user-1", relation=RelationType.OWNS, target="doc-1"
        ))
        outgoing = self.graph.get_outgoing("user-1", RelationType.OWNS)
        assert len(outgoing) == 1
        assert outgoing[0].target == "doc-1"

    def test_find_path_direct(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(
            source="user-1", relation=RelationType.OWNS, target="doc-1"
        ))
        path = self.graph.find_path("user-1", "doc-1")
        assert path is not None
        assert len(path) == 1

    def test_find_path_indirect(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="team-1", entity_type=EntityType.TEAM))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(
            source="user-1", relation=RelationType.MEMBER_OF, target="team-1"
        ))
        self.graph.add_edge(Edge(
            source="team-1", relation=RelationType.COLLABORATOR_ON, target="doc-1"
        ))
        path = self.graph.find_path("user-1", "doc-1",
                                     allowed_relations={RelationType.MEMBER_OF, RelationType.COLLABORATOR_ON})
        assert path is not None
        assert len(path) == 2

    def test_find_path_no_route(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        path = self.graph.find_path("user-1", "doc-1")
        assert path is None

    def test_find_path_max_depth(self):
        for i in range(20):
            self.graph.add_node(Node(id=f"node-{i}", entity_type=EntityType.USER))
            if i > 0:
                self.graph.add_edge(Edge(
                    source=f"node-{i-1}", relation=RelationType.MEMBER_OF,
                    target=f"node-{i}"
                ))
        path = self.graph.find_path("node-0", "node-19", max_depth=5)
        assert path is None
        path = self.graph.find_path("node-0", "node-19", max_depth=20)
        assert path is not None

    def test_reachable_from(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="team-1", entity_type=EntityType.TEAM))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(source="user-1", relation=RelationType.MEMBER_OF, target="team-1"))
        self.graph.add_edge(Edge(source="team-1", relation=RelationType.COLLABORATOR_ON, target="doc-1"))
        reachable = self.graph.reachable_from("user-1")
        assert "team-1" in reachable
        assert "doc-1" in reachable

    def test_remove_edge(self):
        self.graph.add_node(Node(id="user-1", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="doc-1", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(source="user-1", relation=RelationType.OWNS, target="doc-1"))
        self.graph.remove_edge("user-1", RelationType.OWNS, "doc-1")
        assert len(self.graph.get_outgoing("user-1")) == 0

    def test_shortest_path(self):
        self.graph.add_node(Node(id="a", entity_type=EntityType.USER))
        self.graph.add_node(Node(id="b", entity_type=EntityType.TEAM))
        self.graph.add_node(Node(id="c", entity_type=EntityType.DOCUMENT))
        self.graph.add_edge(Edge(source="a", relation=RelationType.MEMBER_OF, target="b"))
        self.graph.add_edge(Edge(source="b", relation=RelationType.COLLABORATOR_ON, target="c"))
        path = self.graph.shortest_path("a", "c")
        assert path is not None
        assert len(path) == 2
```

### Testes de autorização

```python
class TestAuthorizer:
    def setup_method(self):
        self.graph = RelationshipGraph()
        self.authorizer = Authorizer(self.graph)

        self.graph.add_node(Node(id="alice", entity_type="user"))
        self.graph.add_node(Node(id="bob", entity_type="user"))
        self.graph.add_node(Node(id="team-eng", entity_type="team"))
        self.graph.add_node(Node(id="doc-1", entity_type="document"))

        self.graph.add_edge(Edge(source="alice", relation=RelationType.OWNS, target="doc-1"))
        self.graph.add_edge(Edge(source="bob", relation=RelationType.MEMBER_OF, target="team-eng"))
        self.graph.add_edge(Edge(source="team-eng", relation=RelationType.COLLABORATOR_ON, target="doc-1"))

        self.authorizer.add_policy(AccessPolicy(
            permission="view",
            allowed_relations=[RelationType.OWNS, RelationType.COLLABORATOR_ON, RelationType.MEMBER_OF],
            max_depth=5,
        ))
        self.authorizer.add_policy(AccessPolicy(
            permission="edit",
            allowed_relations=[RelationType.OWNS, RelationType.COLLABORATOR_ON],
            max_depth=2,
        ))

    def test_owner_can_view(self):
        assert self.authorizer.check_access("alice", "doc-1", "view") is True

    def test_team_member_can_view(self):
        assert self.authorizer.check_access("bob", "doc-1", "view") is True

    def test_owner_can_edit(self):
        assert self.authorizer.check_access("alice", "doc-1", "edit") is True

    def test_team_member_cannot_edit(self):
        assert self.authorizer.check_access("bob", "doc-1", "edit") is False

    def test_unknown_user_cannot_view(self):
        assert self.authorizer.check_access("eve", "doc-1", "view") is False

    def test_lookup_accessible_resources(self):
        resources = self.authorizer.LookupAccessible("alice", "view")
        assert "doc-1" in resources
```

### Testes de SpiceDB

```python
class TestSpiceDBIntegration:
    def setup_method(self):
        self.client = SpiceDBClient(
            endpoint="localhost:50051",
            token="test-token",
        )

    @pytest.mark.asyncio
    async def test_write_and_check(self):
        await self.client.write_tuples([
            {
                "resource": {"object_type": "document", "object_id": "doc-1"},
                "relation": "owner",
                "subject": {"object": {"object_type": "user", "object_id": "alice"}},
            }
        ])
        result = await self.client.check(
            resource_type="document",
            resource_id="doc-1",
            permission="view",
            subject_type="user",
            subject_id="alice",
        )
        assert result.get("permissionship") == "HAS_PERMISSION"

    @pytest.mark.asyncio
    async def test_check_no_permission(self):
        result = await self.client.check(
            resource_type="document",
            resource_id="doc-1",
            permission="edit",
            subject_type="user",
            subject_id="eve",
        )
        assert result.get("permissionship") == "NO_PERMISSION"

    @pytest.mark.asyncio
    async def test_lookup_resources(self):
        await self.client.write_tuples([
            {
                "resource": {"object_type": "document", "object_id": "doc-1"},
                "relation": "viewer",
                "subject": {"object": {"object_type": "user", "object_id": "bob"}},
            },
        ])
        result = await self.client.lookup_resources(
            resource_type="document",
            permission="view",
            subject_type="user",
            subject_id="bob",
        )
        object_ids = [r.get("object_id") for r in result.get("result", [])]
        assert "doc-1" in object_ids
```

### Property-based testing para ReBAC

```python
from hypothesis import given, strategies as st

class TestReBACProperties:
    @given(
        num_users=st.integers(min_value=1, max_value=50),
        num_resources=st.integers(min_value=1, max_value=50),
    )
    def test_owner_always_has_access(self, num_users, num_resources):
        graph = RelationshipGraph()
        authorizer = Authorizer(graph)
        authorizer.add_policy(AccessPolicy(
            permission="view",
            allowed_relations=[RelationType.OWNS],
            max_depth=1,
        ))

        for i in range(num_users):
            graph.add_node(Node(id=f"user-{i}", entity_type="user"))
        for i in range(num_resources):
            graph.add_node(Node(id=f"doc-{i}", entity_type="document"))

        for i in range(min(num_users, num_resources)):
            graph.add_edge(Edge(source=f"user-{i}", relation=RelationType.OWNS, target=f"doc-{i}"))
            assert authorizer.check_access(f"user-{i}", f"doc-{i}", "view")

    def test_no_relation_means_no_access(self):
        graph = RelationshipGraph()
        authorizer = Authorizer(graph)
        authorizer.add_policy(AccessPolicy(
            permission="view",
            allowed_relations=[RelationType.OWNS, RelationType.COLLABORATOR_ON],
            max_depth=5,
        ))

        graph.add_node(Node(id="alice", entity_type="user"))
        graph.add_node(Node(id="secret-doc", entity_type="document"))

        assert authorizer.check_access("alice", "secret-doc", "view") is False
```

---

## 11.13 Casos de Estudo Reais

### Caso 1: Google Drive

O Google Drive usa o modelo Zanzibar para controlar acesso a arquivos e pastas. A estrutura de relacionamento inclui:

```
User --[owner]--> File
User --[writer]--> File
User --[reader]--> File
Group --[member]--> User
File --[parent]--> Folder
Folder --[parent]--> Folder
File --[shared_via_link]--> Link
```

Permissões computadas:
- `can_read = reader OR writer OR owner`
- `can_write = writer OR owner`
- `can_share = owner OR writer`
- `can_delete = owner`

A herança de permissões funciona através da relação `parent`: se um usuário tem acesso a uma pasta, ele herda acesso a todos os arquivos dentro dela.

### Caso 2: GitHub

GitHub usa um modelo ReBAC para controle de acesso a repositórios:

```
User --[owner]--> Repository
User --[collaborator]--> Repository
Team --[member]--> User
Organization --[owns]--> Repository
Organization --[has_team]--> Team
Repository --[fork]--> Repository
PullRequest --[targets]--> Repository
```

Permissões:
- `can_read = collaborator OR owner OR org_member`
- `can_push = collaborator OR owner`
- `can_admin = owner`
- `can_fork = anyone (public repos)`

### Caso 3: Notion

O Notion usa um modelo de permissões baseado em relações para workspaces, páginas e bancos de dados:

```
User --[workspace_member]--> Workspace
Page --[parent]--> Page
Page --[workspace]--> Workspace
User --[page_owner]--> Page
User --[page_editor]--> Page
User --[page_commenter]--> Page
User --[page_viewer]--> Page
```

As permissões são herdadas hierarquicamente: se um usuário tem acesso a uma página pai, ele herda acesso a todas as páginas filhas.

---

## 11.14 Erros Comuns e Anti-Padrões

### Anti-padrão 1: Não considerar ciclos no grafo

Grafos de relações podem conter ciclos (A segue B, B segue A). Sem proteção, algoritmos de busca entrarão em loop infinito.

```python
class UnprotectedTraversal:
    def find_path(self, source, target):
        queue = [(source, [])]
        while queue:
            current, path = queue.pop(0)
            for edge in self.adjacency[current]:
                queue.append((edge.target, path + [edge]))
        return None  # Loop infinito se houver ciclos

class ProtectedTraversal:
    def find_path(self, source, target, max_depth=10):
        visited = set()
        queue = [(source, [])]
        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            if len(path) > max_depth:
                continue
            visited.add(current)
            for edge in self.adjacency.get(current, []):
                if edge.target == target:
                    return path + [edge]
                queue.append((edge.target, path + [edge]))
        return None
```

### Anti-padrão 2: Não cachear consultas de grafo

Consultas de grafo são computacionalmente custosas. Sem cache, cada verificação de acesso pode percorrer o grafo inteiro.

```python
class UncachedAuthorizer:
    def check_access(self, subject_id, resource_id, permission):
        return self.graph.find_path(subject_id, resource_id) is not None

class CachedAuthorizer:
    def __init__(self, cache_ttl=300):
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.cache_timestamps = {}

    def check_access(self, subject_id, resource_id, permission):
        cache_key = f"{subject_id}:{resource_id}:{permission}"
        if cache_key in self.cache:
            if time.time() - self.cache_timestamps[cache_key] < self.cache_ttl:
                return self.cache[cache_key]

        result = self.graph.find_path(subject_id, resource_id) is not None
        self.cache[cache_key] = result
        self.cache_timestamps[cache_key] = time.time()
        return result

    def invalidate(self, subject_id=None):
        if subject_id:
            keys = [k for k in self.cache if k.startswith(subject_id)]
            for k in keys:
                del self.cache[k]
                del self.cache_timestamps[k]
        else:
            self.cache.clear()
            self.cache_timestamps.clear()
```

### Anti-padrão 3: Relações granulares demais

Ter muitos tipos de relação aumenta a complexidade sem necessidade. Use tipos de relação genéricos e parametrize com atributos.

```python
# RUIM: muitos tipos de relação
class BadRelationTypes(Enum):
    CAN_READ = "can_read"
    CAN_WRITE = "can_write"
    CAN_COMMENT = "can_comment"
    CAN_SHARE = "can_share"
    CAN_DELETE = "can_delete"
    CAN_ADMIN = "can_admin"
    CAN_VIEW_HISTORY = "can_view_history"
    CAN_EXPORT = "can_export"

# BOM: poucos tipos genéricos + atributos
class GoodRelationTypes(Enum):
    MEMBER = "member"
    ADMIN = "admin"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"

# Permissões computadas a partir das relações
```

### Anti-padrão 4: Não validar integridade do grafo

O grafo pode ficar inconsistente se relações são removidas mas referências permanecem.

```python
class IntegrityValidator:
    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def validate(self) -> list:
        errors = []

        for edge in self.graph.edges:
            if edge.source not in self.graph.nodes:
                errors.append(f"Edge source {edge.source} not in nodes")
            if edge.target not in self.graph.nodes:
                errors.append(f"Edge target {edge.target} not in nodes")

        for node_id in self.graph.nodes:
            if node_id not in self.graph.adjacency:
                errors.append(f"Node {node_id} not in adjacency list")
            if node_id not in self.graph.reverse_adjacency:
                errors.append(f"Node {node_id} not in reverse adjacency list")

        return errors

    def repair(self):
        orphan_edges = []
        for edge in self.graph.edges:
            if edge.source not in self.graph.nodes or edge.target not in self.graph.nodes:
                orphan_edges.append(edge)

        for edge in orphan_edges:
            self.graph.edges.remove(edge)
            if edge in self.graph.adjacency.get(edge.source, []):
                self.graph.adjacency[edge.source].remove(edge)
            if edge in self.graph.reverse_adjacency.get(edge.target, []):
                self.graph.reverse_adjacency[edge.target].remove(edge)
```

## 11.16 ReBAC no Caso Misantropi4

No contexto do Misantropi4, ReBAC é usado para modelar relacionamentos entre tenants, equipes, dados e processos de aprovação. O grafo de relações do Misantropi4 captura a estrutura organizacional e as cadeias de aprovação necessárias para transações de alto valor.

### Grafo de relações do Misantropi4

```
Tenant-A --[owns]--> TradingDesk-A
Tenant-A --[owns]--> RiskTeam-A
TradingDesk-A --[member]--> Alice
TradingDesk-A --[member]--> Bob
RiskTeam-A --[member]--> Carol
RiskTeam-A --[member]--> Dave

Transaction-1 --[belongs_to]--> Tenant-A
Transaction-1 --[requires_approval_from]--> RiskTeam-A

ApprovalChain-1 --[approves]--> Transaction-1
ApprovalChain-1 --[approver]--> Carol
ApprovalChain-1 --[approver]--> Dave
```

### Schema SpiceDB para Misantropi4

```
definition tenant {
    relation admin: user
    relation member: user | group#member
    relation billing_admin: user

    permission manage = admin
    permission access = member
    permission manage_billing = billing_admin + admin
}

definition team {
    relation parent: tenant
    relation member: user | team#member
    relation lead: user

    permission view = member + lead
    permission manage = lead
    permission approve = lead + member
}

definition transaction {
    relation belongs_to: tenant
    relation initiated_by: user
    relation requires_approval_from: team
    relation approved_by: user
    relation risk_reviewed_by: user

    permission view = belongs_to->member
    permission initiate = belongs_to->member
    permission approve = requires_approval_from->member
    permission execute = approved_by + belongs_to->admin
    permission cancel = initiated_by + belongs_to->admin
}

definition approval_chain {
    relation approves: transaction
    relation approver: user
    relation co_approver: user

    permission view = approver + co_approver
    permission submit = approver
    permission co_sign = co_approver
}

definition document {
    relation belongs_to: tenant
    relation owner: user
    relation shared_with: user | team#member
    relation parent_folder: folder

    permission view = owner + shared_with + belongs_to->admin
    permission edit = owner + belongs_to->admin
    permission share = owner
    permission delete = owner + belongs_to->admin
}

definition folder {
    relation belongs_to: tenant
    relation owner: user
    relation shared_with: user | team#member
    relation parent: folder

    permission view = owner + shared_with + belongs_to->admin
    permission edit = owner + belongs_to->admin
    permission create_child = owner + belongs_to->admin
}

definition group {
    relation member: user | group#member
}
```

### Integração SpiceDB + ABAC

```python
class Misantropi4HybridAuthZ:
    def __init__(self, spicedb_client: SpiceDBClient,
                 abac_engine: ABACEngine):
        self.spicedb = spicedb_client
        self.abac = abac_engine

    async def check_transaction_access(self, user_id: str,
                                        transaction_id: str,
                                        action: str,
                                        context: dict) -> AccessDecision:
        spicedb_check = await self.spicedb.check(
            resource_type="transaction",
            resource_id=transaction_id,
            permission=action,
            subject_type="user",
            subject_id=user_id,
        )

        if spicedb_check.get("permissionship") != "HAS_PERMISSION":
            return AccessDecision(
                decision=Decision.DENY,
                reason="No ReBAC relationship grants access",
            )

        abac_request = AccessRequest(
            subject={"id": user_id, "tenant_id": context.get("tenant_id")},
            resource={"id": transaction_id, "type": "transaction",
                      "amount": context.get("amount")},
            action={"verb": action},
            environment=context,
        )
        abac_decision = self.abac.evaluate(abac_request)

        if abac_decision.decision == Decision.DENY:
            return AccessDecision(
                decision=Decision.DENY,
                reason=f"ABAC denied: {abac_decision.reason}",
            )

        return AccessDecision(
            decision=Decision.PERMIT,
            obligations=abac_decision.obligations,
        )

    async def get_accessible_transactions(self, user_id: str,
                                           tenant_id: str) -> list:
        result = await self.spicedb.lookup_resources(
            resource_type="transaction",
            permission="view",
            subject_type="user",
            subject_id=user_id,
        )
        return [r["object_id"] for r in result.get("result", [])]
```

### Políticas de cadeia de aprovação

A cadeia de aprovação é um dos aspectos mais críticos do Misantropi4. Transações acima de $100,000 requerem aprovação dupla — um trader e um risk manager.

```python
class ApprovalChainManager:
    def __init__(self, spicedb: SpiceDBClient):
        self.spicedb = spicedb

    async def initiate_approval(self, transaction_id: str,
                                 initiator_id: str) -> dict:
        await self.spicedb.write_tuples([
            {
                "resource": {"object_type": "transaction", "object_id": transaction_id},
                "relation": "initiated_by",
                "subject": {"object": {"object_type": "user", "object_id": initiator_id}},
            },
        ])
        return {"status": "initiated", "transaction_id": transaction_id}

    async def add_approver(self, transaction_id: str,
                           approver_id: str) -> dict:
        await self.spicedb.write_tuples([
            {
                "resource": {"object_type": "transaction", "object_id": transaction_id},
                "relation": "approved_by",
                "subject": {"object": {"object_type": "user", "object_id": approver_id}},
            },
        ])
        approval_count = await self._get_approval_count(transaction_id)
        return {
            "status": "approved" if approval_count >= 2 else "pending",
            "approval_count": approval_count,
            "required": 2,
        }

    async def _get_approval_count(self, transaction_id: str) -> int:
        result = await self.spicedb.read_relationships(
            resource_type="transaction",
            resource_id=transaction_id,
            relation="approved_by",
        )
        return len(result.get("relation_tuples", []))

    async def can_execute(self, transaction_id: str,
                          executor_id: str) -> bool:
        check = await self.spicedb.check(
            resource_type="transaction",
            resource_id=transaction_id,
            permission="execute",
            subject_type="user",
            subject_id=executor_id,
        )
        return check.get("permissionship") == "HAS_PERMISSION"
```

### Auditoria de relacionamentos

```python
class RelationshipAuditLog:
    def __init__(self, spicedb: SpiceDBClient, audit_store: AuditStore):
        self.spicedb = spicedb
        self.audit = audit_store

    async def log_relationship_change(self, change_type: str,
                                       resource_type: str,
                                       resource_id: str,
                                       relation: str,
                                       subject_type: str,
                                       subject_id: str,
                                       actor_id: str):
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            event_type=f"relationship.{change_type}",
            resource=f"{resource_type}:{resource_id}",
            relation=relation,
            subject=f"{subject_type}:{subject_id}",
            actor=actor_id,
        )
        await self.audit.store(entry)

    async def get_relationship_history(self, resource_type: str,
                                        resource_id: str) -> list:
        return await self.audit.query(
            resource=f"{resource_type}:{resource_id}",
            event_type_prefix="relationship.",
        )

    async def validate_integrity(self) -> list:
        result = await self.spicedb.read_relationships()
        tuples = result.get("relation_tuples", [])
        issues = []

        for t in tuples:
            resource = t.get("resource", {})
            subject = t.get("subject", {}).get("object", {})

            if not subject.get("object_id"):
                issues.append({
                    "type": "orphan_reference",
                    "tuple": t,
                    "reason": "Subject has no object_id",
                })

        return issues
```

## 11.18 Padrões de Performance para ReBAC em Escala

Quando um sistema ReBAC cresce para milhões de nós e bilhões de arestas, a performance da resolução de relações se torna um desafio crítico. As estratégias a seguir são essenciais para manter latência aceitável.

### Estratégia 1: Materialização de permissões

Em vez de resolver o grafo a cada consulta, materialize as permissões computadas e as armazene em uma tabela de consulta rápida.

```python
class PermissionMaterializer:
    def __init__(self, graph: RelationshipGraph, policy_store: PolicyStore):
        self.graph = graph
        self.policies = policy_store
        self.materialized: Dict[str, Set[str]] = {}

    def materialize(self, subject_id: str, permission: str):
        policy = self.policies.get_permission_policy(permission)
        allowed_relations = set(policy.allowed_relations)
        reachable = self.graph.reachable_from(subject_id, allowed_relations, policy.max_depth)
        self.materialized[f"{subject_id}:{permission}"] = reachable

    def check_materialized(self, subject_id: str, resource_id: str,
                           permission: str) -> bool:
        key = f"{subject_id}:{permission}"
        reachable = self.materialized.get(key, set())
        return resource_id in reachable

    def invalidate(self, subject_id: str = None, permission: str = None):
        if subject_id and permission:
            self.materialized.pop(f"{subject_id}:{permission}", None)
        elif subject_id:
            keys = [k for k in self.materialized if k.startswith(f"{subject_id}:")]
            for k in keys:
                del self.materialized[k]
        else:
            self.materialized.clear()

    def on_relationship_change(self, edge: Edge):
        affected = set()
        for key in self.materialized:
            subject_id, perm = key.split(":", 1)
            if edge.source == subject_id or edge.target == subject_id:
                affected.add(key)
        for key in affected:
            subject_id, perm = key.split(":", 1)
            self.materialize(subject_id, perm)
```

### Estratégia 2: Índices invertidos para relações

Índices invertidos permitem encontrar rapidamente todas as relações de um tipo sem percorrer o grafo inteiro.

```python
class InvertedRelationIndex:
    def __init__(self):
        self.forward: Dict[str, Dict[RelationType, Set[str]]] = {}
        self.reverse: Dict[str, Dict[RelationType, Set[str]]] = {}

    def add(self, edge: Edge):
        self.forward.setdefault(edge.source, {}).setdefault(edge.relation, set()).add(edge.target)
        self.reverse.setdefault(edge.target, {}).setdefault(edge.relation, set()).add(edge.source)

    def remove(self, edge: Edge):
        if edge.source in self.forward and edge.relation in self.forward[edge.source]:
            self.forward[edge.source][edge.relation].discard(edge.target)
        if edge.target in self.reverse and edge.relation in self.reverse[edge.target]:
            self.reverse[edge.target][edge.relation].discard(edge.source)

    def get_outgoing(self, node_id: str, relation: RelationType) -> Set[str]:
        return self.forward.get(node_id, {}).get(relation, set())

    def get_incoming(self, node_id: str, relation: RelationType) -> Set[str]:
        return self.reverse.get(node_id, {}).get(relation, set())

    def get_all_outgoing(self, node_id: str) -> Dict[RelationType, Set[str]]:
        return self.forward.get(node_id, {})

    def get_all_incoming(self, node_id: str) -> Dict[RelationType, Set[str]]:
        return self.reverse.get(node_id, {})
```

### Estratégia 3: Cache distribuído com invalidação

```python
import redis
import json
import hashlib


class DistributedReBACCache:
    def __init__(self, redis_client: redis.Redis, ttl: int = 300):
        self.redis = redis_client
        self.ttl = ttl
        self.pubsub = redis_client.pubsub()
        self.pubsub.subscribe(**{"rebac:invalidate": self._handle_invalidation})

    def get_check_result(self, subject_id: str, resource_id: str,
                         permission: str) -> Optional[bool]:
        key = self._cache_key(subject_id, resource_id, permission)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    def set_check_result(self, subject_id: str, resource_id: str,
                         permission: str, result: bool):
        key = self._cache_key(subject_id, resource_id, permission)
        self.redis.setex(key, self.ttl, json.dumps(result))

    def invalidate_subject(self, subject_id: str):
        pattern = f"rebac:check:{subject_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
        self.redis.publish("rebac:invalidate",
                          json.dumps({"type": "subject", "id": subject_id}))

    def invalidate_resource(self, resource_id: str):
        pattern = f"rebac:check:*:{resource_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
        self.redis.publish("rebac:invalidate",
                          json.dumps({"type": "resource", "id": resource_id}))

    def _handle_invalidation(self, message):
        data = json.loads(message["data"])
        if data["type"] == "subject":
            self.invalidate_subject(data["id"])
        elif data["type"] == "resource":
            self.invalidate_resource(data["id"])

    def _cache_key(self, subject_id: str, resource_id: str,
                   permission: str) -> str:
        raw = f"{subject_id}:{resource_id}:{permission}"
        return f"rebac:check:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
```

### Estratégia 4: Bloom filter para negação rápida

Quando a maioria das consultas resulta em DENY (cenário comum em sistemas grandes), um bloom filter pode rapidamente identificar pares que definitivamente não têm relação.

```python
class BloomFilterReBAC:
    def __init__(self, expected_elements: int = 1000000, fp_rate: float = 0.01):
        self.bloom = BloomFilter(expected_elements, fp_rate)
        self.exact_cache = {}

    def index_relationship(self, subject_id: str, resource_id: str,
                           permission: str):
        key = f"{subject_id}:{resource_id}:{permission}"
        self.bloom.add(key)

    def might_have_relationship(self, subject_id: str, resource_id: str,
                                 permission: str) -> bool:
        key = f"{subject_id}:{resource_id}:{permission}"
        return key in self.bloom

    def check(self, subject_id: str, resource_id: str,
              permission: str) -> Optional[bool]:
        if not self.might_have_relationship(subject_id, resource_id, permission):
            return False

        cached = self.exact_cache.get(
            f"{subject_id}:{resource_id}:{permission}"
        )
        if cached is not None:
            return cached

        return None
```

### Benchmark de referência

| Operação | Grafo 1M nós | Grafo 10M nós | Grafo 100M nós |
|---|---|---|---|
| Check (cache hit) | < 1ms | < 1ms | < 1ms |
| Check (cache miss, direto) | 2-5ms | 5-15ms | 15-50ms |
| Check (cache miss, 3 hops) | 5-10ms | 15-40ms | 40-150ms |
| Lookup resources | 10-50ms | 50-200ms | 200-1000ms |
| Materialização completa | 1-5s | 5-30s | 30-300s |
| Invalidação | < 1ms | < 1ms | < 1ms |

---

## 11.19 Operações de Grafo Avançadas

### Consultas compostas em ReBAC

Sistemas reais frequentemente precisam de consultas que combinam múltiplos critérios de relação. Por exemplo: "encontre todos os documentos que o usuário pode editar e que são compartilhados com a equipe de engenharia."

```python
class CompoundQuery:
    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def find_shared_resources(self, user_id: str, team_id: str,
                               permission: str) -> Set[str]:
        user_resources = self._get_resources_with_permission(user_id, permission)
        team_resources = self._get_team_resources(team_id)
        return user_resources & team_resources

    def find_mutual_access(self, user1: str, user2: str,
                            permission: str) -> Set[str]:
        resources1 = self._get_resources_with_permission(user1, permission)
        resources2 = self._get_resources_with_permission(user2, permission)
        return resources1 & resources2

    def find_accessible_by_all(self, user_ids: List[str],
                                permission: str) -> Set[str]:
        if not user_ids:
            return set()
        result = self._get_resources_with_permission(user_ids[0], permission)
        for uid in user_ids[1:]:
            result &= self._get_resources_with_permission(uid, permission)
        return result

    def find_accessible_by_any(self, user_ids: List[str],
                                permission: str) -> Set[str]:
        result = set()
        for uid in user_ids:
            result |= self._get_resources_with_permission(uid, permission)
        return result

    def find_transitive_members(self, group_id: str,
                                 max_depth: int = 5) -> Set[str]:
        visited = set()
        queue = [(group_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for edge in self.graph.get_outgoing(current, RelationType.MEMBER_OF):
                if edge.target not in visited:
                    queue.append((edge.target, depth + 1))
        return visited - {group_id}

    def _get_resources_with_permission(self, user_id: str,
                                       permission: str) -> Set[str]:
        reachable = self.graph.reachable_from(
            user_id,
            allowed_relations={RelationType.OWNS, RelationType.COLLABORATOR_ON,
                              RelationType.SHARED_WITH, RelationType.MEMBER_OF},
            max_depth=5,
        )
        return {nid for nid in reachable
                if self.graph.nodes.get(nid) and
                self.graph.nodes[nid].entity_type in ("document", "file", "resource")}
```

### Métricas de grafo para monitoramento

```python
class GraphMetrics:
    def __init__(self, graph: RelationshipGraph):
        self.graph = graph

    def count_nodes(self) -> int:
        return len(self.graph.nodes)

    def count_edges(self) -> int:
        return len(self.graph.edges)

    def count_edges_by_type(self) -> Dict[RelationType, int]:
        counts = {}
        for edge in self.graph.edges:
            counts[edge.relation] = counts.get(edge.relation, 0) + 1
        return counts

    def average_out_degree(self) -> float:
        if not self.graph.nodes:
            return 0
        total = sum(len(edges) for edges in self.graph.adjacency.values())
        return total / len(self.graph.nodes)

    def average_in_degree(self) -> float:
        if not self.graph.nodes:
            return 0
        total = sum(len(edges) for edges in self.graph.reverse_adjacency.values())
        return total / len(self.graph.nodes)

    def max_out_degree(self) -> int:
        if not self.graph.adjacency:
            return 0
        return max(len(edges) for edges in self.graph.adjacency.values())

    def isolated_nodes(self) -> List[str]:
        return [nid for nid, edges in self.graph.adjacency.items()
                if not edges and not self.graph.reverse_adjacency.get(nid)]

    def density(self) -> float:
        n = len(self.graph.nodes)
        if n <= 1:
            return 0
        max_edges = n * (n - 1)
        return len(self.graph.edges) / max_edges

    def report(self) -> dict:
        return {
            "total_nodes": self.count_nodes(),
            "total_edges": self.count_edges(),
            "edges_by_type": self.count_edges_by_type(),
            "avg_out_degree": self.average_out_degree(),
            "avg_in_degree": self.average_in_degree(),
            "max_out_degree": self.max_out_degree(),
            "isolated_nodes": len(self.isolated_nodes()),
            "density": self.density(),
        }
```

---

## 11.20 Referências

- Pang, H. et al. "Zanzibar: Google's Consistent, Global Authorization System" (2019)
- AuthZed. "SpiceDB: Open-Source Zanzibar-Compatible Database"
- Ory. "Ory Keto: Open Source Go Access Control Server"
- Casbin. "Authorization Library that Supports Access Control Models like ACL, RBAC, ABAC"
- Fong, P.W.L. "Relationship-Based Access Control: Protection Model and Policy Language" (2013)
- Fong, P.W.L. et al. "Relationship-Based Access Control for Social Network Services" (2011)
- Sandhu, R. et al. "Relationship-Based Access Control" (2014)
- OpenZiti. "Zero Trust Networking Platform"
- Beynon-Davies, P. "Database Systems" (2004)
- Cardwell, N. "Consistent Hashing" (2014)
- Zanzibar++: "Consistent and Durably Authorizing Access Control" (2023)
- AuthZed. "SpiceDB Architecture" (2022)
- Ory Keto. "Relation Tuple and Check API Documentation" (2023)
- Casbin. "PERM Model: Policy, Effect, Request, Matchers" (2022)
- Google. "Zanzibar: Solving Authorization at Scale" (2020)
- Fong, P.W.L., Suri, A. "Relationship-Based Access Control for Cloud Services" (2014)
- Jin, X. et al. "ReBAC: A Relationship-Based Access Control Model" (2020)
- AuthZed. "Authorization Patterns and Anti-Patterns" (2023)
- Ory. "Zero Trust Architecture with Ory" (2022)
- OpenZed. "OpenZiti Zero Trust Framework" (2023)
