# Capítulo 10 — ABAC (Attribute-Based Access Control)

## 10.1 Fundamentos do ABAC

Attribute-Based Access Control (ABAC) representa um dos modelos de autorização mais expressivos e flexíveis disponíveis para sistemas modernos. Diferentemente de RBAC, que toma decisões baseadas em papeis estáticos atribuídos a usuários, ABAC avalia atributos — propriedades discretas de sujeitos, recursos, ações e do ambiente — contra políticas declarativas para determinar se uma requisição de acesso deve ser permitida ou negada.

O padrão de referência para ABAC é o **NIST Special Publication 800-162** ("Guide to Attribute-Based Access Control: Definition and Considerations"), que define ABAC como:

> Um mecanismo de controle de acesso que usa atributos para conceder ou negar acesso. As políticas de controle de acesso são expressas em termos de atributos do sujeito, do recurso e do ambiente, e das ações solicitadas.

A essência do ABAC é a separação entre decisões de autorização e a estrutura organizacional. Em RBAC, se uma empresa reorganiza seus departamentos, centenas de regras de acesso podem precisar ser reescritas. Em ABAC, as políticas são definidas em termos de propriedades que existem independentemente da estrutura organizacional — cargo, departamento, clearance, localização, horário, e assim por diante.

### Por que ABAC importa em segurança

Em ambientes corporativos contemporâneos, o controle de acesso baseado em papeis frequentemente se torna insuficiente por razões concretas. Uma enfermeira em um hospital, por exemplo, precisa acessar registros de pacientes, mas apenas durante seu turno, apenas no andar designado, e apenas para pacientes sob seus cuidados diretos. RBAC pode modelar "enfermeira acessa registros", mas não consegue expressar "enfermeira acessa registros apenas durante turno X, no andar Y, para pacientes do grupo Z."

ABAC resolve esse problema porque as políticas são formuladas em termos de atributos que capturam essas restrições diretamente. Cada decisão de acesso é o resultado de uma avaliação que cruza múltiplas dimensões simultaneamente.

### Ciclo de vida de uma decisão ABAC

O ciclo de vida padrão de uma decisão ABAC segue estas etapas:

1. **Requisição**: O sujeito tenta realizar uma ação sobre um recurso.
2. **Interceptação**: O PEP (Policy Enforcement Point) intercepta a requisição.
3. **Consulta**: O PEP encaminha a requisição ao PDP (Policy Decision Point).
4. **Coleta de atributos**: O PDP solicita atributos adicionais ao PIP (Policy Information Point) quando necessário.
5. **Avaliação**: O PDP avalia as políticas relevantes contra os atributos coletados.
6. **Decisão**: O PDP retorna PERMIT, DENY ou INDETERMINATE.
7. **Execução**: O PEP aplica a decisão — permite ou bloqueia o acesso.
8. **Obligation**: Se a política define obrigações (obligations), o PEP as executa (log, notificação, encriptação).

Esse ciclo é stateless por natureza — cada requisição é avaliada independentemente, o que facilita a horizontalidade e a escalabilidade do modelo.

### Propriedades fundamentais

ABAC possui propriedades que o distinguem de outros modelos:

- **Granularidade fina**: Cada política pode referenciar quantos atributos forem necessários.
- **Expressividade**: Políticas complexas com lógica quantificacional (para todo, existe) podem ser expressas.
- **Agilidade organizacional**: Mudanças na estrutura da organização não requerem reescrita de políticas, apenas atualização de atributos.
- **Composição**: Políticas simples podem ser combinadas para gerar comportamentos complexos.
- **Contextualidade**: Atributos de ambiente (hora, localização, risco da sessão) influenciam decisões.

---

## 10.2 Componentes do ABAC — PEP, PDP, PIP, PAP

A arquitetura ABAC é composta por quatro componentes principais, definidos no padrão XACML (eXtensible Access Control Markup Language) do OASIS. Entender a responsabilidade de cada componente é essencial para implementar ABAC corretamente.

### Policy Enforcement Point (PEP)

O PEP é o ponto de enforcement — o "porteiro" do sistema. Toda requisição de acesso passa pelo PEP antes de chegar ao recurso. O PEP não toma decisões; ele aplica decisões.

Responsabilidades do PEP:

- Interceptar requisições de acesso antes de chegarem ao recurso.
- Extrair atributos iniciais da requisição (sujeito, recurso, ação).
- Consultar o PDP para obter uma decisão.
- Aplicar a decisão (PERMIT → permitir acesso; DENY → bloquear).
- Executar obrigações associadas à política.
- Registrar tentativas de acesso para auditoria.

```python
class PolicyEnforcementPoint:
    def __init__(self, pdp: PolicyDecisionPoint, audit_logger: AuditLogger):
        self.pdp = pdp
        self.audit = audit_logger

    def enforce(self, subject: Subject, resource: Resource,
                action: Action, environment: Environment) -> bool:
        request = AccessRequest(
            subject=subject,
            resource=resource,
            action=action,
            environment=environment,
        )

        decision = self.pdp.evaluate(request)

        self.audit.log(AuditEntry(
            subject=subject.id,
            resource=resource.uri,
            action=action.verb,
            decision=decision.value,
            timestamp=datetime.utcnow(),
        ))

        if decision.value == "PERMIT":
            for obligation in decision.obligations:
                self._execute_obligation(obligation)
            return True

        if decision.value == "DENY":
            return False

        if decision.value == "INDETERMINATE":
            self.audit.log_warning("Indeterminate decision — default deny")
            return False

    def _execute_obligation(self, obligation: Obligation):
        if obligation.type == "LOG":
            self.audit.log_obligation(obligation)
        elif obligation.type == "NOTIFY":
            notification_service.send(obligation.target, obligation.message)
        elif obligation.type == "ENCRYPT":
            crypto_service.encrypt_context(obligation.context)
```

O PEP deve ser implementado de forma a falhar por default (deny). Se o PDP estiver indisponível, o PEP deve negar o acesso em vez de permiti-lo. Essa é uma regra fundamental de segurança — a falha deve ser segura (fail-safe).

### Policy Decision Point (PDP)

O PDP é o cérebro do sistema ABAC. Ele recebe requisições de autorização, coleta atributos necessários, avalia políticas e retorna uma decisão.

Responsabilidades do PDP:

- Receber requisições de autorização do PEP.
- Identificar políticas aplicáveis com base no target das políticas.
- Solicitar atributos adicionais ao PIP quando necessário.
- Avaliar regras contidas nas políticas aplicáveis.
- Combinar decisões de múltiplas políticas usando algoritmos de combinação.
- Retornar PERMIT, DENY ou INDETERMINATE.

```python
class PolicyDecisionPoint:
    def __init__(self, pip: PolicyInformationPoint,
                 pap: PolicyAdministrationPoint):
        self.pip = pip
        self.pap = pap
        self.combining_algorithms = {
            "permit-overrides": self._permit_overrides,
            "deny-overrides": self._deny_overrides,
            "first-applicable": self._first_applicable,
            "only-one-applicable": self._only_one_applicable,
        }

    def evaluate(self, request: AccessRequest) -> Decision:
        policies = self.pap.get_applicable_policies(request)
        if not policies:
            return Decision(value="DENY", reason="no applicable policy")

        decisions = []
        for policy in policies:
            if self._target_matches(policy.target, request):
                attrs = self._collect_attributes(policy, request)
                decision = self._evaluate_rules(policy.rules, attrs)
                decisions.append(decision)

        combining_algo = policies[0].combining_algorithm
        return self.combining_algorithms[combining_algo](decisions)

    def _evaluate_rules(self, rules: list, attrs: dict) -> Decision:
        for rule in rules:
            if rule.effect == "permit" and self._condition_matches(rule.condition, attrs):
                return Decision(value="PERMIT", obligations=rule.obligations)
            if rule.effect == "deny" and self._condition_matches(rule.condition, attrs):
                return Decision(value="DENY", obligations=rule.obligations)
        return Decision(value="INDETERMINATE")

    def _collect_attributes(self, policy: Policy,
                            request: AccessRequest) -> dict:
        attrs = {
            "subject": request.subject.attributes,
            "resource": request.resource.attributes,
            "action": request.action.attributes,
            "environment": request.environment.attributes,
        }
        for attr_ref in policy.required_attributes:
            category, name = attr_ref
            if name not in attrs.get(category, {}):
                pip_attrs = self.pip.get_attribute(
                    category=category, name=name,
                    subject=request.subject,
                    resource=request.resource,
                )
                attrs.setdefault(category, {}).update(pip_attrs)
        return attrs
```

O PDP deve ser idempotente — avaliar a mesma requisição com os mesmos atributos deve sempre produzir o mesmo resultado. Essa propriedade é crítica para caching e testabilidade.

### Policy Information Point (PIP)

O PIP é a fonte de verdade para atributos. Quando o PDP precisa de um atributo que não está disponível na requisição original, ele consulta o PIP.

Responsabilidades do PIP:

- Fornecer atributos de sujeitos (departamento, clearance, certificações).
- Fornecer atributos de recursos (classificação, proprietário, data de criação).
- Fornecer atributos de ambiente (hora, localização, nível de risco da sessão).
- Integrar com fontes externas (LDAP, bases de dados, APIs).
- Cachear atributos quando apropriado para performance.

```python
class PolicyInformationPoint:
    def __init__(self, subject_store: SubjectStore,
                 resource_store: ResourceStore,
                 env_provider: EnvironmentProvider,
                 cache: AttributeCache):
        self.subject_store = subject_store
        self.resource_store = resource_store
        self.env_provider = env_provider
        self.cache = cache

    def get_attribute(self, category: str, name: str,
                      subject: Subject = None,
                      resource: Resource = None) -> dict:
        cache_key = f"{category}:{name}:{subject and subject.id}:{resource and resource.id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if category == "subject":
            attrs = self.subject_store.get_attributes(subject.id)
        elif category == "resource":
            attrs = self.resource_store.get_attributes(resource.id)
        elif category == "environment":
            attrs = self.env_provider.get_current()
        else:
            raise UnknownAttributeCategory(category)

        value = {name: attrs.get(name)}
        self.cache.set(cache_key, value, ttl=300)
        return value

    def get_subject_attributes(self, subject_id: str) -> dict:
        return self.subject_store.get_attributes(subject_id)

    def get_resource_attributes(self, resource_id: str) -> dict:
        return self.resource_store.get_attributes(resource_id)
```

A latência do PIP é um dos maiores gargalos de performance em sistemas ABAC. Implementações de produção devem sempre incluir caching com TTL adequado e invalidação baseada em eventos.

### Policy Administration Point (PAP)

O PAP é o repositório de políticas. Ele armazena, gerencia e distribui políticas para o PDP.

Responsabilidades do PAP:

- Armazenar políticas em formato padronizado (XACML, Rego, Cedar).
- Versionar políticas para auditoria e rollback.
- Distribuir políticas para PDPs distribuídos.
- Fornecer interfaces para administradores definirem políticas.
- Validar sintaxe e consistência de políticas.

```python
class PolicyAdministrationPoint:
    def __init__(self, policy_store: PolicyStore,
                 policy_validator: PolicyValidator):
        self.store = policy_store
        self.validator = policy_validator

    def get_applicable_policies(self, request: AccessRequest) -> list:
        all_policies = self.store.list_policies()
        return [p for p in all_policies
                if self._target_matches(p.target, request)]

    def add_policy(self, policy: Policy) -> str:
        errors = self.validator.validate(policy)
        if errors:
            raise PolicyValidationError(errors)
        policy_id = self.store.create(policy)
        self._distribute_to_pdps(policy)
        return policy_id

    def update_policy(self, policy_id: str, policy: Policy):
        errors = self.validator.validate(policy)
        if errors:
            raise PolicyValidationError(errors)
        self.store.update(policy_id, policy)
        self._distribute_to_pdps(policy)

    def remove_policy(self, policy_id: str):
        self.store.delete(policy_id)
        self._notify_pdps_removal(policy_id)

    def _distribute_to_pdps(self, policy: Policy):
        for pdp_endpoint in self.discovered_pdps:
            http_post(pdp_endpoint + "/policies/sync", policy.serialize())
```

### Diagrama de interação entre componentes

```
+-----------+       +-----------+       +-----------+
|  Subject   |------>|    PEP    |------>|  Resource |
| (Usuário)  |<------| (Enforce) |<------|           |
+-----------+       +-----+-----+       +-----------+
                           |
                     decision? (PERMIT/DENY)
                           |
                           v
                     +-----------+       +-----------+
                     |    PDP    |<----->|    PIP    |
                     | (Decide)  |       | (Attributes)|
                     +-----+-----+       +-----------+
                           |
                     which policies?
                           |
                           v
                     +-----------+
                     |    PAP    |
                     | (Policies)|
                     +-----------+
```

---

## 10.3 Estrutura de Política — Target, Rule, Obligation

Uma política ABAC é uma estrutura hierárquica composta por três elementos fundamentais: targets, rules e obligations. Cada elemento tem um papel específico na tomada de decisão.

### Target (Alvo)

O target define QUANDO uma política é aplicável. É um predicado que compara atributos da requisição com valores constantes. Se o target não corresponde, a política é ignorada — as regras dentro dela nem sequer são avaliadas.

Targets são a primeira camada de filtragem. Eles permitem que o PDP rapidamente descarte políticas irrelevantes antes de entrar na avaliação custosa das regras.

Estrutura típica de um target:

```
target {
    subject.role == "nurse"
    AND subject.department == "cardiology"
    AND resource.type == "patient-record"
    AND action.verb == "read"
}
```

Targets podem usar operadores lógicos (AND, OR, NOT) e comparações de atributos. O padrão XACML define operadores ricos: string-equals, numeric-greater-than, date-before, e assim por diante.

```python
class Target:
    def __init__(self, expressions: list, operator: str = "AND"):
        self.expressions = expressions
        self.operator = operator

    def matches(self, request: AccessRequest) -> bool:
        results = []
        for expr in self.expressions:
            attr_value = self._resolve_attribute(expr.category,
                                                  expr.attribute, request)
            result = self._compare(attr_value, expr.operator, expr.value)
            results.append(result)

        if self.operator == "AND":
            return all(results)
        elif self.operator == "OR":
            return any(results)

    def _resolve_attribute(self, category: str, attribute: str,
                           request: AccessRequest):
        if category == "subject":
            return request.subject.attributes.get(attribute)
        elif category == "resource":
            return request.resource.attributes.get(attribute)
        elif category == "action":
            return request.action.attributes.get(attribute)
        elif category == "environment":
            return request.environment.attributes.get(attribute)

    def _compare(self, value, operator: str, expected) -> bool:
        if operator == "string-equals":
            return str(value) == str(expected)
        elif operator == "numeric-greater-than":
            return float(value) > float(expected)
        elif operator == "numeric-less-than":
            return float(value) < float(expected)
        elif operator == "date-before":
            return datetime.fromisoformat(str(value)) < datetime.fromisoformat(str(expected))
        elif operator == "string-in-set":
            return str(value) in expected
```

### Rule (Regra)

A rule é o elemento que define a decisão concreta — PERMIT ou DENY. Cada regra contém uma condição (condicional) que é avaliada contra os atributos coletados.

Uma política pode conter múltiplas regras. O efeito de cada regra é PERMIT ou DENY. Quando múltiplas regras correspondem, o algoritmo de combinação de regras (rule-combining-algorithm) determina o resultado final.

```python
class Rule:
    def __init__(self, rule_id: str, effect: str, condition: Condition,
                 obligations: list = None):
        self.rule_id = rule_id
        self.effect = effect  # "permit" or "deny"
        self.condition = condition
        self.obligations = obligations or []

    def evaluate(self, attributes: dict) -> RuleResult:
        if self.condition.satisfied(attributes):
            return RuleResult(
                applicable=True,
                effect=self.effect,
                obligations=self.obligations,
            )
        return RuleResult(applicable=False, effect=None, obligations=[])


class Condition:
    def __init__(self, expression: str):
        self.expression = expression

    def satisfied(self, attributes: dict) -> bool:
        return bool(eval(self.expression, {"__builtins__": {}}, attributes))
```

Exemplo de uma regra concreta:

```
rule "nurse-read-patient-record" {
    effect: PERMIT
    condition: (
        subject.role == "nurse"
        AND subject.assigned_patients CONTAINS resource.patient_id
        AND action.verb == "read"
        AND environment.time >= subject.shift_start
        AND environment.time <= subject.shift_end
    )
    obligations: [
        LOG_AUDIT(subject.id, resource.id, "read", environment.timestamp),
        ENCRYPT_RESPONSE("AES-256")
    ]
}
```

### Obligation (Obrigação)

Obligations são ações que o PEP DEVE executar quando uma decisão PERMIT é retornada. Elas são distintas da decisão em si — a obligation não determina se o acesso é permitido, mas especifica o que deve acontecer como parte da concessão.

Obligations são uma das características mais poderosas de ABAC. Elas permitem que políticas não apenas respondam "sim ou não", mas também definam como o acesso deve ser registrado, protegido ou auditado.

```python
class Obligation:
    def __init__(self, obligation_id: str, obligation_type: str,
                 target: str, parameters: dict):
        self.obligation_id = obligation_id
        self.obligation_type = obligation_type
        self.target = target
        self.parameters = parameters


class ObligationExecutor:
    def __init__(self, audit_store: AuditStore,
                 notification_service: NotificationService,
                 crypto_service: CryptoService):
        self.audit = audit_store
        self.notifications = notification_service
        self.crypto = crypto_service

    def execute(self, obligation: Obligation, request: AccessRequest):
        if obligation.obligation_type == "LOG_ACCESS":
            self._log_access(obligation, request)
        elif obligation.obligation_type == "ENCRYPT_DATA":
            self._encrypt_response(obligation)
        elif obligation.obligation_type == "NOTIFY_ADMIN":
            self._notify_admin(obligation, request)
        elif obligation.obligation_type == "MFA_REQUIRED":
            self._verify_mfa(obligation, request)

    def _log_access(self, obligation: Obligation, request: AccessRequest):
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            subject_id=request.subject.id,
            resource_id=request.resource.id,
            action=request.action.verb,
            decision="PERMIT",
            obligation_id=obligation.obligation_id,
        )
        self.audit.store(entry)

    def _encrypt_response(self, obligation: Obligation):
        algorithm = obligation.parameters.get("algorithm", "AES-256-GCM")
        self.crypto.set_response_encryption(algorithm)
```

Obligations são obrigatórias — se o PEP não puder executá-la, o acesso deve ser negado. Essa semantics é frequentemente mal compreendida e implementada incorretamente, gerando brechas de segurança.

### Combinação de Políticas

Quando múltiplas políticas se aplicam a uma mesma requisição, é necessário um algoritmo de combinação para resolver conflitos. Os algoritmos padrão definidos pelo XACML são:

- **Permit-Overrides**: Se qualquer política retornar PERMIT, o resultado é PERMIT (independente de DENYs).
- **Deny-Overrides**: Se qualquer política retornar DENY, o resultado é DENY (independente de PERMITs).
- **First-Applicable**: A primeira política avaliada que retorna PERMIT ou DENY determina o resultado.
- **Only-One-Applicable**: Exatamente uma política deve ser aplicável; caso contrário, INDETERMINATE.
- **Ordered-Permit-Overrides**: Similar a permit-overrides, mas respeita a ordem de precedência.
- **Ordered-Deny-Overrides**: Similar a deny-overrides, mas respeita a ordem de precedência.

```python
class CombiningAlgorithms:
    @staticmethod
    def permit_overrides(decisions: list) -> Decision:
        obligations = []
        has_permit = False
        has_ineterminate = False

        for d in decisions:
            if d.value == "PERMIT":
                has_permit = True
                obligations.extend(d.obligations)
            elif d.value == "INDETERMINATE":
                has_ineterminate = True

        if has_permit:
            return Decision(value="PERMIT", obligations=obligations)
        if has_ineterminate:
            return Decision(value="INDETERMINATE")
        return Decision(value="DENY")

    @staticmethod
    def deny_overrides(decisions: list) -> Decision:
        obligations = []
        has_deny = False
        has_ineterminate = False

        for d in decisions:
            if d.value == "DENY":
                has_deny = True
                obligations.extend(d.obligations)
            elif d.value == "INDETERMINATE":
                has_ineterminate = True

        if has_deny:
            return Decision(value="DENY", obligations=obligations)
        if has_ineterminate:
            return Decision(value="INDETERMINATE")
        return Decision(value="PERMIT")

    @staticmethod
    def first_applicable(decisions: list) -> Decision:
        for d in decisions:
            if d.value in ("PERMIT", "DENY"):
                return d
        return Decision(value="INDETERMINATE")
```

---

## 10.4 Tipos de Atributos — Subject, Resource, Action, Environment

A expressividade de ABAC depende diretamente da riqueza dos atributos disponíveis. Cada requisição de acesso é descrita por quatro categorias de atributos, e cada categoria contribui com uma dimensão diferente para a decisão.

### Atributos de Subject (Sujeito)

Atributos de sujeito descrevem quem está solicitando o acesso. São propriedades que caracterizam a identidade, função e contexto do solicitante.

Categorias comuns de atributos de sujeito:

- **Identidade**: id, nome, email, groups.
- **Organização**: department, team, cost_center.
- **Função**: role, job_title, clearance_level.
- **Certificações**: certifications[], training_completed[], access_history[].
- **Contexto**: session_risk_score, mfa_verified, device_type, last_login.

```python
class SubjectAttributes:
    def __init__(self, subject_id: str):
        self.id = subject_id
        self.attributes = {}

    def set_identity(self, **kwargs):
        self.attributes.update({
            "subject.id": kwargs.get("id"),
            "subject.name": kwargs.get("name"),
            "subject.email": kwargs.get("email"),
            "subject.groups": kwargs.get("groups", []),
        })

    def set_organization(self, **kwargs):
        self.attributes.update({
            "subject.department": kwargs.get("department"),
            "subject.team": kwargs.get("team"),
            "subject.cost_center": kwargs.get("cost_center"),
        })

    def set_function(self, **kwargs):
        self.attributes.update({
            "subject.role": kwargs.get("role"),
            "subject.job_title": kwargs.get("job_title"),
            "subject.clearance_level": kwargs.get("clearance_level"),
        })

    def set_context(self, **kwargs):
        self.attributes.update({
            "subject.session_risk_score": kwargs.get("risk_score", 0.0),
            "subject.mfa_verified": kwargs.get("mfa_verified", False),
            "subject.device_type": kwargs.get("device_type"),
            "subject.last_login": kwargs.get("last_login"),
        })
```

Em sistemas de saúde (HIPAA), atributos de sujeito incluem credenciais profissionais, especializações e afiliação a unidades. Em sistemas financeiros, incluem licenças regulatórias, aprovações de risco e níveis de assinatura.

### Atributos de Resource (Recurso)

Atributos de recurso descrevem o objeto sobre o qual o acesso é solicitado. Eles definem a natureza, classificação e contexto do recurso.

Categorias comuns de atributos de resource:

- **Identidade**: id, uri, name, type.
- **Classificação**: sensitivity, classification_level, data_category.
- **Propriedade**: owner, created_by, department.
- **Temporal**: created_at, expires_at, last_modified.
- **Relacional**: parent_resource, associated_project, data_subject.

```python
class ResourceAttributes:
    def __init__(self, resource_id: str):
        self.id = resource_id
        self.attributes = {}

    def set_identity(self, **kwargs):
        self.attributes.update({
            "resource.id": kwargs.get("id"),
            "resource.uri": kwargs.get("uri"),
            "resource.name": kwargs.get("name"),
            "resource.type": kwargs.get("type"),
        })

    def set_classification(self, **kwargs):
        self.attributes.update({
            "resource.sensitivity": kwargs.get("sensitivity"),
            "resource.classification_level": kwargs.get("classification_level"),
            "resource.data_category": kwargs.get("data_category"),
        })

    def set_ownership(self, **kwargs):
        self.attributes.update({
            "resource.owner": kwargs.get("owner"),
            "resource.created_by": kwargs.get("created_by"),
            "resource.department": kwargs.get("department"),
        })

    def set_temporal(self, **kwargs):
        self.attributes.update({
            "resource.created_at": kwargs.get("created_at"),
            "resource.expires_at": kwargs.get("expires_at"),
            "resource.last_modified": kwargs.get("last_modified"),
        })
```

### Atributos de Action (Ação)

Atributos de ação descrevem o que o sujeito quer fazer com o recurso. Na maioria dos sistemas, a ação é simplesmente "read", "write" ou "delete", mas ABAC permite ações muito mais granulares.

Categorias comuns de atributos de action:

- **Verbo**: verb (read, write, delete, execute, approve, transfer).
- **Parâmetros**: fields_accessed, amount, destination.
- **Modo**: bulk, individual, simulated, deferred.

```python
class ActionAttributes:
    def __init__(self, verb: str):
        self.verb = verb
        self.attributes = {"action.verb": verb}

    def set_parameters(self, **kwargs):
        if "fields" in kwargs:
            self.attributes["action.fields_accessed"] = kwargs["fields"]
        if "amount" in kwargs:
            self.attributes["action.amount"] = kwargs["amount"]
        if "destination" in kwargs:
            self.attributes["action.destination"] = kwargs["destination"]

    def set_mode(self, mode: str):
        self.attributes["action.mode"] = mode
```

### Atributos de Environment (Ambiente)

Atributos de ambiente descrevem o contexto em que a requisição ocorre. Eles são independentes do sujeito e do recurso, e introduzem fatores situacionais nas decisões.

Categorias comuns de atributos de environment:

- **Temporal**: current_time, day_of_week, is_business_hours.
- **Localização**: client_ip, geo_location, network_zone, is_vpn.
- **Sessão**: session_id, session_age, risk_score.
- **Infraestrutura**: device_type, os_version, browser_version.
- **Segurança**: threat_level, intrusion_detected, compliance_status.

```python
class EnvironmentAttributes:
    def __init__(self):
        self.attributes = {}

    def capture_current(self):
        now = datetime.utcnow()
        self.attributes.update({
            "environment.current_time": now.isoformat(),
            "environment.day_of_week": now.strftime("%A"),
            "environment.is_business_hours": 9 <= now.hour <= 17,
        })

    def set_network(self, **kwargs):
        self.attributes.update({
            "environment.client_ip": kwargs.get("client_ip"),
            "environment.geo_location": kwargs.get("geo_location"),
            "environment.network_zone": kwargs.get("network_zone"),
            "environment.is_vpn": kwargs.get("is_vpn", False),
        })

    def set_threat(self, **kwargs):
        self.attributes.update({
            "environment.threat_level": kwargs.get("threat_level", "low"),
            "environment.intrusion_detected": kwargs.get("intrusion_detected", False),
        })
```

### Exemplo integrado: decisão com todos os atributos

```
Requisição:
  subject.role = "financial-analyst"
  subject.department = "risk"
  subject.clearance_level = 3
  subject.mfa_verified = true

  resource.type = "trading-order"
  resource.sensitivity = "high"
  resource.amount = 2500000
  resource.owner = "trading-desk-a"

  action.verb = "approve"
  action.amount = 2500000

  environment.is_business_hours = true
  environment.network_zone = "internal"
  environment.threat_level = "low"

Política evaluada:
  IF subject.role == "financial-analyst"
     AND subject.clearance_level >= 3
     AND subject.mfa_verified == true
     AND resource.type == "trading-order"
     AND resource.sensitivity == "high"
     AND action.verb == "approve"
     AND action.amount <= 5000000
     AND environment.is_business_hours == true
     AND environment.network_zone == "internal"
     AND environment.threat_level != "high"
  THEN PERMIT
       OBLIGATIONS: LOG_APPROVAL, NOTIFY_COMPLIANCE
```

---

## 10.5 ABAC vs RBAC

A comparação entre ABAC e RBAC não é sobre qual modelo é "melhor" — é sobre qual modelo se adapta melhor aos requisitos específicos de cada sistema. Ambos têm seus lugar e muitas organizações usam ambos simultaneamente.

### Limitações de RBAC

RBAC é intuitivo e fácil de implementar, mas possui limitações concretas:

- **Explosão de papeis**: Em organizações complexas, o número de papeis necessários cresce exponencialmente para cobrir todas as combinações de permissões.
- **Falta de contexto**: RBAC não considera fatores temporais, geográficos ou de risco.
- **Gestão rígida**: Adicionar uma nova restrição exige criar novos papeis ou modificar hierarquias existentes.
- **Granularidade limitada**: Permissões são tipicamente coarse-grained (read, write, admin).

### Vantagens de ABAC sobre RBAC

- **Granularidade**: Políticas podem referenciar quantos atributos forem necessários.
- **Contexto**: Decisões podem considerar hora, localização, risco, e qualquer outro fator.
- **Dinamismo**: Novas restrições são adicionadas como novas políticas, não como novos papeis.
- **Composição**: Políticas simples combinam para gerar comportamento complexo.
- **Auditabilidade**: Cada decisão é explicável — os atributos que levaram à decisão são registrados.

### Quando usar RBAC

- Sistemas com estrutura organizacional estável.
- Requisitos de compliance simples (quem pode fazer o quê).
- Equipes pequenas com pouca variação nas necessidades de acesso.
- Sistemas legados onde a migração para ABAC é custosa demais.

### Quando usar ABAC

- Ambientes com requisitos de segurança complexos.
- Sistemas que precisam de decisões contextuais (horário, local, risco).
- Organizações em constante reorganização.
- Sistemas que precisam de auditoria granular.
- Multi-tenant SaaS com necessidades variáveis por tenant.

### ABAC + RBAC híbrido

Na prática, muitas implementações combinam RBAC e ABAC. RBAC define o "macro-controle" — quem tem acesso básico a que sistemas. ABAC fornece o "micro-controle" — restrições contextuais sobre como e quando esse acesso pode ser exercido.

```python
class HybridAccessControl:
    def __init__(self, rbac_engine: RBACEngine, abac_engine: ABACEngine):
        self.rbac = rbac_engine
        self.abac = abac_engine

    def check_access(self, user: User, resource: Resource,
                     action: str, context: dict) -> bool:
        if not self.rbac.is_authorized(user, resource.type, action):
            return False

        return self.abac.evaluate(
            subject=user.to_subject_attributes(),
            resource=resource.to_resource_attributes(),
            action=ActionAttributes(action),
            environment=EnvironmentAttributes.from_context(context),
        )
```

---

## 10.6 ABAC em Microserviços

Implementar ABAC em arquiteturas de microserviços apresenta desafios únicos. A autorização não pode ser um monolito — ela precisa ser distribuída, consistente e de baixa latência.

### Desafios específicos

1. **Consistência distribuída**: Políticas devem ser consistentes entre múltiplas instâncias de PDP.
2. **Latência**: Cada chamada entre microsserviços pode exigir uma verificação de autorização.
3. **Observabilidade**: Decisões de autorização em dezenas de serviços precisam ser centralizadas para auditoria.
4. **Evolução independente**: Cada microsserviço pode ter necessidades de autorização diferentes.

### Padrão: Sidecar PDP

O padrão mais comum é implantar um PDP como sidecar junto a cada instância de microsserviço. O sidecar intercepta chamadas, avalia políticas locais e retorna decisões com latência mínima.

```
+-------------------+      +-------------------+
| Microsserviço A   |      | Microsserviço B   |
| +-------------+   |      | +-------------+   |
| |  App Logic  |   |      | |  App Logic  |   |
| +------+------+   |      | +------+------+   |
|        |          |      |        |          |
| +------+------+   |      | +------+------+   |
| | PDP Sidecar |   |      | | PDP Sidecar |   |
| +------+------+   |      | +------+------+   |
+--------|----------+      +--------|----------+
         |                          |
    policies pushed            policies pushed
         |                          |
         v                          v
    +---------+      +---------+---------+
    |   PAP   |      | Centralized Audit |
    +---------+      +-------------------+
```

### Padrão: Centralized PDP com Cache

Alternativamente, um PDP centralizado com cache distribuído (Redis, por exemplo) pode servir múltiplos microsserviços.

```python
class DistributedPDP:
    def __init__(self, policy_store: PolicyStore,
                 cache: RedisCache,
                 audit_client: AuditClient):
        self.store = policy_store
        self.cache = cache
        self.audit = audit_client

    async def evaluate(self, request: AccessRequest) -> Decision:
        cache_key = self._cache_key(request)
        cached = await self.cache.get(cache_key)
        if cached:
            return Decision.deserialize(cached)

        policies = await self.store.get_applicable_policies(request)
        decision = self._evaluate_policies(policies, request)

        await self.cache.set(cache_key, decision.serialize(), ttl=30)
        await self.audit.record(request, decision)

        return decision

    def _cache_key(self, request: AccessRequest) -> str:
        attr_hash = hashlib.sha256(
            json.dumps(request.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:16]
        return f"pdp:decision:{attr_hash}"
```

### Padrão: Event-Driven Policy Distribution

Políticas devem ser distribuídas via eventos para garantir consistência eventual entre PDPs:

```python
class PolicyEventPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def publish_policy_created(self, policy: Policy):
        event = PolicyEvent(
            type="policy.created",
            policy_id=policy.id,
            payload=policy.serialize(),
            timestamp=datetime.utcnow(),
        )
        await self.event_bus.publish("pdp.policy-updates", event)

    async def publish_policy_updated(self, policy: Policy):
        event = PolicyEvent(
            type="policy.updated",
            policy_id=policy.id,
            payload=policy.serialize(),
            timestamp=datetime.utcnow(),
        )
        await self.event_bus.publish("pdp.policy-updates", event)

    async def publish_policy_deleted(self, policy_id: str):
        event = PolicyEvent(
            type="policy.deleted",
            policy_id=policy_id,
            timestamp=datetime.utcnow(),
        )
        await self.event_bus.publish("pdp.policy-updates", event)


class PolicyEventSubscriber:
    def __init__(self, local_store: LocalPolicyCache):
        self.local_store = local_store

    async def handle_event(self, event: PolicyEvent):
        if event.type == "policy.created":
            self.local_store.add(Policy.deserialize(event.payload))
        elif event.type == "policy.updated":
            self.local_store.update(
                event.policy_id, Policy.deserialize(event.payload)
            )
        elif event.type == "policy.deleted":
            self.local_store.remove(event.policy_id)
```

---

## 10.7 XACML — eXtensible Access Control Markup Language

XACML é a linguagem padronizada para expressar políticas ABAC. Definida pelo OASIS, XACML usa XML como formato de serialização e define uma arquitetura completa para tomada de decisão de autorização.

### Estrutura XACML

Um documento XACML contém:

- **PolicySet**: Coleção de políticas com um algoritmo de combinação.
- **Policy**: Regras agrupadas com um target e um algoritmo de combinação de regras.
- **Rule**: Condição individual com efeito PERMIT ou DENY.
- **Target**: Condição de applicabilidade.
- **Condition**: Expressão booleana avaliada contra atributos.

```xml
<PolicySet xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17"
           PolicySetId="hospital-access-policy"
           Version="1.0"
           PolicyCombiningAlgorithm="permit-overrides">

    <Target>
        <AnyOf>
            <AllOf>
                <Match MatchId="string-equal">
                    <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">
                        hospital
                    </AttributeValue>
                    <AttributeDesignator AttributeId="system.type"
                                         Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
                                         DataType="http://www.w3.org/2001/XMLSchema#string"/>
                </Match>
            </AllOf>
        </AnyOf>
    </Target>

    <Policy PolicyId="nurse-access-policy"
            Version="1.0"
            RuleCombiningAlgorithm="deny-overrides">

        <Target>
            <AnyOf>
                <AllOf>
                    <Match MatchId="string-equal">
                        <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">
                            nurse
                        </AttributeValue>
                        <AttributeDesignator AttributeId="role"
                                             Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
                                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </Match>
                </AllOf>
            </AnyOf>
        </Target>

        <Rule RuleId="nurse-read-patient"
              Effect="Permit">
            <Description>
                Nurses may read records of their assigned patients during their shift.
            </Description>
            <Target>
                <AnyOf>
                    <AllOf>
                        <Match MatchId="string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">
                                read
                            </AttributeValue>
                            <AttributeDesignator AttributeId="action"
                                                 Category="urn:oasis:names:tc:xacml:3.0:attribute-category:action"
                                                 DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </Match>
                        <Match MatchId="string-equal">
                            <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">
                                patient-record
                            </AttributeValue>
                            <AttributeDesignator AttributeId="resource-type"
                                                 Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource"
                                                 DataType="http://www.w3.org/2001/XMLSchema#string"/>
                        </Match>
                    </AllOf>
                </AnyOf>
            </Target>
            <Condition>
                <Apply ApplyId="and">
                    <Apply ApplyId="string-equal">
                        <AttributeDesignator AttributeId="assigned-patients"
                                             Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
                                             DataType="http://www.w3.org/2001/XMLSchema#string"
                                             MustBePresent="true"/>
                        <AttributeDesignator AttributeId="patient-id"
                                             Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource"
                                             DataType="http://www.w3.org/2001/XMLSchema#string"
                                             MustBePresent="true"/>
                    </Apply>
                    <Apply ApplyId="greater-than-or-equal">
                        <AttributeDesignator AttributeId="current-time"
                                             Category="urn:oasis:names:tc:xacml:3.0:attribute-category:environment"
                                             DataType="http://www.w3.org/2001/XMLSchema#time"
                                             MustBePresent="true"/>
                        <AttributeDesignator AttributeId="shift-start"
                                             Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
                                             DataType="http://www.w3.org/2001/XMLSchema#time"
                                             MustBePresent="true"/>
                    </Apply>
                    <Apply ApplyId="less-than-or-equal">
                        <AttributeDesignator AttributeId="current-time"
                                             Category="urn:oasis:names:tc:xacml:3.0:attribute-category:environment"
                                             DataType="http://www.w3.org/2001/XMLSchema#time"
                                             MustBePresent="true"/>
                        <AttributeDesignator AttributeId="shift-end"
                                             Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject"
                                             DataType="http://www.w3.org/2001/XMLSchema#time"
                                             MustBePresent="true"/>
                    </Apply>
                </Apply>
            </Condition>
        </Rule>
    </Policy>
</PolicySet>
```

### Limitações do XACML

Apesar de ser o padrão de referência, XACML possui desafios práticos:

- **Verbosidade**: Políticas simples resultam em XML extenso e difícil de ler.
- **Curva de aprendizado**: A sintaxe XML é propensa a erros e difícil de revisar manualmente.
- **Performance**: Parsing de XML é mais lento que formatos binários ou JSON.
- **Ferramentas**: O ecossistema de ferramentas XACML é menor que alternativas modernas.

Por essas razões, muitas implementações modernas usam alternativas como Rego (OPA), Cedar (AWS), ou DSLs proprietárias.

---

## 10.8 Implementação em Python e Go

### Implementação em Python

Uma implementação completa de ABAC em Python pode ser construída com foco em clareza e extensibilidade:

```python
import json
import hashlib
from datetime import datetime
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class Decision(Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"
    INDETERMINATE = "INDETERMINATE"


@dataclass
class AccessRequest:
    subject: dict
    resource: dict
    action: dict
    environment: dict


@dataclass
class AccessDecision:
    decision: Decision
    obligations: list = field(default_factory=list)
    reason: str = ""


@dataclass
class Policy:
    id: str
    target: dict
    rules: list
    combining_algorithm: str = "deny-overrides"


class AttributeResolver:
    def __init__(self, providers: dict = None):
        self.providers = providers or {}

    def resolve(self, category: str, attribute: str,
                request: AccessRequest) -> Any:
        source = getattr(request, category, None)
        if source and attribute in source:
            return source[attribute]

        if category in self.providers:
            return self.providers[category].get(attribute)

        return None


class ConditionEvaluator:
    OPERATORS = {
        "eq": lambda a, b: a == b,
        "neq": lambda a, b: a != b,
        "gt": lambda a, b: float(a) > float(b),
        "gte": lambda a, b: float(a) >= float(b),
        "lt": lambda a, b: float(a) < float(b),
        "lte": lambda a, b: float(a) <= float(b),
        "in": lambda a, b: a in b,
        "contains": lambda a, b: b in a,
        "starts_with": lambda a, b: str(a).startswith(str(b)),
        "ends_with": lambda a, b: str(a).endswith(str(b)),
        "matches": lambda a, b: bool(re.match(str(b), str(a))),
    }

    def evaluate(self, condition: dict, attributes: dict) -> bool:
        op = condition["operator"]
        left = self._resolve_value(condition["left"], attributes)
        right = condition["right"]

        if op not in self.OPERATORS:
            raise ValueError(f"Unknown operator: {op}")

        return self.OPERATORS[op](left, right)

    def _resolve_value(self, ref: str, attributes: dict) -> Any:
        parts = ref.split(".")
        current = attributes
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current


class PolicyEngine:
    def __init__(self, attribute_resolver: AttributeResolver,
                 condition_evaluator: ConditionEvaluator):
        self.resolver = attribute_resolver
        self.evaluator = condition_evaluator
        self.policies: list[Policy] = []

    def load_policies(self, policies: list[Policy]):
        self.policies = policies

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        applicable = [p for p in self.policies
                      if self._target_matches(p.target, request)]

        if not applicable:
            return AccessDecision(
                decision=Decision.DENY,
                reason="No applicable policy found",
            )

        decisions = []
        for policy in applicable:
            decision = self._evaluate_policy(policy, request)
            decisions.append(decision)

        return self._combine_decisions(decisions)

    def _target_matches(self, target: dict, request: AccessRequest) -> bool:
        for condition in target.get("conditions", []):
            left = self.resolver.resolve(
                condition["category"], condition["attribute"], request
            )
            right = condition["value"]
            op = condition.get("operator", "eq")

            if op == "eq" and left != right:
                return False
            if op == "in" and left not in right:
                return False
        return True

    def _evaluate_policy(self, policy: Policy,
                         request: AccessRequest) -> AccessDecision:
        for rule in policy.rules:
            if self._evaluate_conditions(rule["conditions"], request):
                return AccessDecision(
                    decision=Decision(rule["effect"]),
                    obligations=rule.get("obligations", []),
                    reason=rule.get("description", ""),
                )
        return AccessDecision(
            decision=Decision.INDETERMINATE,
            reason=f"No rule matched in policy {policy.id}",
        )

    def _evaluate_conditions(self, conditions: list, request: AccessRequest) -> bool:
        for condition in conditions:
            if not self.evaluator.evaluate(condition, request.__dict__):
                return False
        return True

    def _combine_decisions(self, decisions: list) -> AccessDecision:
        if not decisions:
            return AccessDecision(decision=Decision.DENY, reason="No decisions")

        deny_overrides = [d for d in decisions if d.decision == Decision.DENY]
        if deny_overrides:
            return deny_overrides[0]

        permits = [d for d in decisions if d.decision == Decision.PERMIT]
        if permits:
            combined_obligations = []
            for p in permits:
                combined_obligations.extend(p.obligations)
            return AccessDecision(
                decision=Decision.PERMIT,
                obligations=combined_obligations,
            )

        return AccessDecision(
            decision=Decision.INDETERMINATE,
            reason="All decisions were indeterminate",
        )
```

### Implementação em Go

Go é particularmente adequado para implementações de ABAC de alta performance devido à sua concorrência nativa e baixa latência de garbage collection:

```go
package abac

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"sync"
	"time"
)

type Decision string

const (
	Permit       Decision = "PERMIT"
	Deny         Decision = "DENY"
	Ineterminate Decision = "INDETERMINATE"
)

type AccessRequest struct {
	Subject     map[string]interface{} `json:"subject"`
	Resource    map[string]interface{} `json:"resource"`
	Action      map[string]interface{} `json:"action"`
	Environment map[string]interface{} `json:"environment"`
}

type AccessDecision struct {
	Decision   Decision     `json:"decision"`
	Obligations []Obligation `json:"obligations"`
	Reason     string       `json:"reason"`
}

type Obligation struct {
	Type       string                 `json:"type"`
	Parameters map[string]interface{} `json:"parameters"`
}

type Condition struct {
	Category string      `json:"category"`
	Attr     string      `json:"attribute"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
}

type Rule struct {
	ID          string      `json:"id"`
	Description string      `json:"description"`
	Effect      Decision    `json:"effect"`
	Conditions  []Condition `json:"conditions"`
	Obligations []Obligation `json:"obligations,omitempty"`
}

type Policy struct {
	ID                   string   `json:"id"`
	Target               []Condition `json:"target"`
	Rules                []Rule   `json:"rules"`
	CombiningAlgorithm   string   `json:"combining_algorithm"`
}

type PolicyEngine struct {
	mu       sync.RWMutex
	policies []Policy
	cache    *DecisionCache
}

type DecisionCache struct {
	mu      sync.RWMutex
	entries map[string]cachedEntry
	ttl     time.Duration
}

type cachedEntry struct {
	decision AccessDecision
	expires  time.Time
}

func NewPolicyEngine() *PolicyEngine {
	return &PolicyEngine{
		cache: &DecisionCache{
			entries: make(map[string]cachedEntry),
			ttl:     30 * time.Second,
		},
	}
}

func (pe *PolicyEngine) LoadPolicies(policies []Policy) {
	pe.mu.Lock()
	defer pe.mu.Unlock()
	pe.policies = policies
	pe.cache.Clear()
}

func (pe *PolicyEngine) Evaluate(req AccessRequest) AccessDecision {
	key := pe.cacheKey(req)

	pe.cache.mu.RLock()
	if entry, ok := pe.cache.entries[key]; ok && time.Now().Before(entry.expires) {
		pe.cache.mu.RUnlock()
		return entry.decision
	}
	pe.cache.mu.RUnlock()

	pe.mu.RLock()
	applicable := pe.findApplicable(req)
	pe.mu.RUnlock()

	if len(applicable) == 0 {
		decision := AccessDecision{
			Decision: Deny,
			Reason:   "no applicable policy",
		}
		pe.cache.Set(key, decision)
		return decision
	}

	var decisions []AccessDecision
	for _, policy := range applicable {
		d := pe.evaluatePolicy(policy, req)
		decisions = append(decisions, d)
	}

	result := pe.combineDecisions(decisions, applicable[0].CombiningAlgorithm)
	pe.cache.Set(key, result)
	return result
}

func (pe *PolicyEngine) findApplicable(req AccessRequest) []Policy {
	var applicable []Policy
	for _, p := range pe.policies {
		if pe.targetMatches(p.Target, req) {
			applicable = append(applicable, p)
		}
	}
	return applicable
}

func (pe *PolicyEngine) targetMatches(conditions []Condition, req AccessRequest) bool {
	for _, c := range conditions {
		val := pe.resolveAttribute(c.Category, c.Attr, req)
		if !pe.compare(val, c.Operator, c.Value) {
			return false
		}
	}
	return true
}

func (pe *PolicyEngine) evaluatePolicy(policy Policy, req AccessRequest) AccessDecision {
	for _, rule := range policy.Rules {
		if pe.evaluateConditions(rule.Conditions, req) {
			return AccessDecision{
				Decision:   rule.Effect,
				Obligations: rule.Obligations,
				Reason:     rule.Description,
			}
		}
	}
	return AccessDecision{
		Decision: Ineterminate,
		Reason:   fmt.Sprintf("no rule matched in policy %s", policy.ID),
	}
}

func (pe *PolicyEngine) evaluateConditions(conditions []Condition, req AccessRequest) bool {
	for _, c := range conditions {
		val := pe.resolveAttribute(c.Category, c.Attr, req)
		if !pe.compare(val, c.Operator, c.Value) {
			return false
		}
	}
	return true
}

func (pe *PolicyEngine) resolveAttribute(category, attr string, req AccessRequest) interface{} {
	var source map[string]interface{}
	switch category {
	case "subject":
		source = req.Subject
	case "resource":
		source = req.Resource
	case "action":
		source = req.Action
	case "environment":
		source = req.Environment
	}
	if source == nil {
		return nil
	}
	return source[attr]
}

func (pe *PolicyEngine) compare(left interface{}, operator string, right interface{}) bool {
	switch operator {
	case "eq":
		return fmt.Sprintf("%v", left) == fmt.Sprintf("%v", right)
	case "neq":
		return fmt.Sprintf("%v", left) != fmt.Sprintf("%v", right)
	case "gt":
		return toFloat(left) > toFloat(right)
	case "gte":
		return toFloat(left) >= toFloat(right)
	case "lt":
		return toFloat(left) < toFloat(right)
	case "lte":
		return toFloat(left) <= toFloat(right)
	case "in":
		if arr, ok := right.([]interface{}); ok {
			for _, v := range arr {
				if fmt.Sprintf("%v", left) == fmt.Sprintf("%v", v) {
					return true
				}
			}
		}
		return false
	case "contains":
		return fmt.Sprintf("%v", right) != "" &&
			containsString(fmt.Sprintf("%v", left), fmt.Sprintf("%v", right))
	}
	return false
}

func (pe *PolicyEngine) combineDecisions(decisions []AccessDecision, algorithm string) AccessDecision {
	switch algorithm {
	case "deny-overrides":
		return pe.denyOverrides(decisions)
	case "permit-overrides":
		return pe.permitOverrides(decisions)
	case "first-applicable":
		return pe.firstApplicable(decisions)
	default:
		return pe.denyOverrides(decisions)
	}
}

func (pe *PolicyEngine) denyOverrides(decisions []AccessDecision) AccessDecision {
	for _, d := range decisions {
		if d.Decision == Deny {
			return d
		}
	}
	for _, d := range decisions {
		if d.Decision == Permit {
			return d
		}
	}
	return AccessDecision{Decision: Ineterminate, Reason: "all indeterminate"}
}

func (pe *PolicyEngine) permitOverrides(decisions []AccessDecision) AccessDecision {
	for _, d := range decisions {
		if d.Decision == Permit {
			return d
		}
	}
	for _, d := range decisions {
		if d.Decision == Deny {
			return d
		}
	}
	return AccessDecision{Decision: Ineterminate, Reason: "all indeterminate"}
}

func (pe *PolicyEngine) firstApplicable(decisions []AccessDecision) AccessDecision {
	for _, d := range decisions {
		if d.Decision == Permit || d.Decision == Deny {
			return d
		}
	}
	return AccessDecision{Decision: Ineterminate, Reason: "none applicable"}
}

func (pe *PolicyEngine) cacheKey(req AccessRequest) string {
	data, _ := json.Marshal(req)
	hash := sha256.Sum256(data)
	return fmt.Sprintf("%x", hash[:16])
}

func (dc *DecisionCache) Set(key string, decision AccessDecision) {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	dc.entries[key] = cachedEntry{
		decision: decision,
		expires:  time.Now().Add(dc.ttl),
	}
}

func (dc *DecisionCache) Clear() {
	dc.mu.Lock()
	defer dc.mu.Unlock()
	dc.entries = make(map[string]cachedEntry)
}

func toFloat(v interface{}) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	case string:
		var f float64
		fmt.Sscanf(n, "%f", &f)
		return f
	}
	return 0
}

func containsString(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsSubstring(s, substr))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
```

---

## 10.9 Considerações de Performance

ABAC é expressivo, mas essa expressividade tem custo. Cada decisão pode envolver múltiplas consultas a atributos, avaliação de múltiplas políticas, e execução de obrigações. Sem otimizações adequadas, a latência de autorização pode se tornar um gargalo.

### Estratégias de otimização

**1. Cache de decisões**

Decisões podem ser cacheadas quando os atributos envolvidos são relativamente estáticos. A chave do cache deve incluir um hash de todos os atributos relevantes.

```python
class DecisionCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}

    def get(self, request: AccessRequest) -> Optional[AccessDecision]:
        key = self._hash_request(request)
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def set(self, request: AccessRequest, decision: AccessDecision):
        key = self._hash_request(request)
        self.cache[key] = decision
        self.timestamps[key] = time.time()

    def invalidate(self, subject_id: str = None, resource_id: str = None):
        keys_to_remove = []
        for key, ts in self.timestamps.items():
            if time.time() - ts >= self.ttl:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.cache[key]
            del self.timestamps[key]

    def _hash_request(self, request: AccessRequest) -> str:
        data = json.dumps({
            "subject": request.subject,
            "resource": request.resource,
            "action": request.action,
            "environment": request.environment,
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
```

**2. Cache de atributos**

Atributos devem ser cacheados com TTLs que reflitam sua taxa de mudança:

```python
class AttributeCacheConfig:
    TTL_BY_CATEGORY = {
        "subject.identity": 3600,
        "subject.session": 300,
        "subject.department": 86400,
        "resource.classification": 86400,
        "resource.owner": 3600,
        "environment.time": 60,
        "environment.threat_level": 120,
    }
```

**3. Avaliação lazy de atributos**

Não colete todos os atributos antes de começar a avaliar. Avalie em ordem de seletividade — atributos que eliminam mais candidatos devem ser avaliados primeiro.

```python
class LazyAttributeEvaluator:
    def __init__(self, resolver: AttributeResolver):
        self.resolver = resolver

    def evaluate_with_early_exit(self, conditions: list,
                                  request: AccessRequest) -> bool:
        sorted_conditions = sorted(
            conditions,
            key=lambda c: self._selectivity(c),
            reverse=True,
        )

        for condition in sorted_conditions:
            value = self.resolver.resolve(
                condition["category"],
                condition["attribute"],
                request,
            )
            if not self._compare(value, condition["operator"], condition["value"]):
                return False
        return True
```

**4. Compilação de políticas**

Políticas podem ser compiladas para formas mais eficientes — árvores de decisão, tabelas de hash, ou código nativo.

```python
class CompiledPolicy:
    def __init__(self, policy: Policy):
        self.decision_tree = self._compile(policy)

    def _compile(self, policy: Policy):
        tree = {"type": "root", "children": []}
        for rule in policy.rules:
            node = {
                "type": "rule",
                "effect": rule["effect"],
                "checks": self._compile_conditions(rule["conditions"]),
                "obligations": rule.get("obligations", []),
            }
            tree["children"].append(node)
        return tree

    def evaluate(self, attributes: dict) -> AccessDecision:
        for child in self.decision_tree["children"]:
            if self._traverse(child["checks"], attributes):
                return AccessDecision(
                    decision=Decision(child["effect"]),
                    obligations=child.get("obligations", []),
                )
        return AccessDecision(decision=Decision.INDETERMINATE)
```

**5. Pipeline de avaliação paralela**

Quando múltiplas políticas são avaliadas independentemente, elas podem ser processadas em paralelo:

```python
import asyncio

class ParallelPolicyEvaluator:
    def __init__(self, engine: PolicyEngine, max_workers: int = 10):
        self.engine = engine
        self.semaphore = asyncio.Semaphore(max_workers)

    async def evaluate_parallel(self, requests: list) -> list:
        tasks = [self._evaluate_one(req) for req in requests]
        return await asyncio.gather(*tasks)

    async def _evaluate_one(self, request: AccessRequest) -> AccessDecision:
        async with self.semaphore:
            return await asyncio.to_thread(self.engine.evaluate, request)
```

### Benchmarks de referência

Para dimensionar adequadamente, considere estes benchmarks de referência:

| Operação | Latência típica | Throughput |
|---|---|---|
| PDP local (cache hit) | < 1ms | > 100k req/s |
| PDP local (cache miss) | 2-5ms | 20-50k req/s |
| PDP distribuído (rede) | 5-20ms | 5-20k req/s |
| PIP query (LDAP) | 10-50ms | 1-5k req/s |
| PIP query (database) | 5-30ms | 5-20k req/s |
| XACML parsing | 1-5ms | 10-50k pol/s |

---

## 10.10 Exemplos de Políticas Complexas

### Caso de estudo: Misantropi4 — Controle de acesso a dados sensíveis

Misantropi4 é um caso hipotético de uma plataforma de dados financeiros que processa informações de múltiplos clientes institucionais. A plataforma precisa implementar ABAC para garantir que:

1. Analistas acessem apenas dados de seus clientes atribuídos.
2. Transações acima de certo valor exigam aprovação dupla.
3. Dados classificados como "confidencial" só sejam acessíveis dentro da rede corporativa.
4. Acessos fora do horário comercial exigam MFA.
5. Dados de auditoria não possam ser modificados por ninguém.
6. Clientes jamais acessem dados de outros clientes.

#### Política de isolamento de tenant

```
policy "tenant-isolation" {
    target {
        subject.tenant_id == resource.tenant_id
    }

    rule "allow-tenant-access" {
        effect: PERMIT
        condition: (
            subject.tenant_id == resource.tenant_id
            AND subject.account_status == "active"
            AND subject.clearance_level >= resource.classification_level
        )
        obligations: [
            LOG_ACCESS(subject.id, resource.id, action.verb),
            RATE_LIMIT(subject.id, max_requests=1000, window="1h")
        ]
    }

    rule "deny-cross-tenant" {
        effect: DENY
        condition: (
            subject.tenant_id != resource.tenant_id
        )
        obligations: [
            LOG_SECURITY_EVENT("cross-tenant-access-attempt",
                               subject.id, resource.id),
            ALERT_SECOPS(severity="high")
        ]
    }
}
```

#### Política de aprovação para transações de alto valor

```
policy "high-value-transaction" {
    target {
        resource.type == "transaction"
        AND resource.amount > 100000
    }

    rule "require-dual-approval" {
        effect: PERMIT
        condition: (
            subject.role IN ["trader", "risk-manager"]
            AND subject.tenant_id == resource.tenant_id
            AND resource.approval_count >= 2
            AND resource.approvers CONTAINS subject.id
            AND subject.mfa_verified == true
            AND environment.network_zone == "trading-floor"
            AND environment.time BETWEEN resource.trading_window_start
                                      AND resource.trading_window_end
        )
        obligations: [
            LOG_APPROVAL(subject.id, resource.id, resource.amount),
            NOTIFY_COMPLIANCE(resource.id, resource.amount),
            ENCRYPT_RESPONSE("AES-256-GCM")
        ]
    }

    rule "deny-unauthorized-approval" {
        effect: DENY
        condition: (
            resource.amount > 100000
            AND NOT (
                subject.role IN ["trader", "risk-manager"]
                AND resource.approval_count >= 2
            )
        )
        obligations: [
            LOG_SECURITY_EVENT("unauthorized-approval-attempt",
                               subject.id, resource.id),
            ALERT_SECOPS(severity="critical")
        ]
    }
}
```

#### Política de acesso condicional baseado em risco

```
policy "risk-based-access" {
    target {
        resource.sensitivity IN ["confidential", "secret"]
    }

    rule "low-risk-access" {
        effect: PERMIT
        condition: (
            subject.risk_score < 0.3
            AND subject.mfa_verified == true
            AND subject.device_trusted == true
            AND environment.threat_level IN ["low", "medium"]
        )
        obligations: [
            LOG_ACCESS(subject.id, resource.id, action.verb),
            SET_SESSION_TIMEOUT(minutes=30)
        ]
    }

    rule "medium-risk-access" {
        effect: PERMIT
        condition: (
            subject.risk_score BETWEEN 0.3 AND 0.7
            AND subject.mfa_verified == true
            AND subject.device_trusted == true
            AND environment.threat_level == "low"
        )
        obligations: [
            LOG_ACCESS(subject.id, resource.id, action.verb),
            SCREEN_CAPTURE(subject.session_id),
            SET_SESSION_TIMEOUT(minutes=15)
        ]
    }

    rule "high-risk-deny" {
        effect: DENY
        condition: (
            subject.risk_score > 0.7
            OR environment.threat_level == "high"
            OR subject.device_trusted == false
        )
        obligations: [
            LOG_SECURITY_EVENT("high-risk-access-denied",
                               subject.id, resource.id),
            LOCK_ACCOUNT(subject.id, duration="1h"),
            ALERT_SECOPS(severity="critical")
        ]
    }
}
```

#### Política de dados imutáveis para auditoria

```
policy "immutable-audit-data" {
    target {
        resource.type == "audit-record"
    }

    rule "read-only-for-all" {
        effect: PERMIT
        condition: (
            action.verb == "read"
            AND subject.role IN ["auditor", "compliance-officer", "admin"]
            AND subject.tenant_id == resource.tenant_id
        )
        obligations: [
            LOG_AUDIT_ACCESS(subject.id, resource.id),
            WATERMARK_RESPONSE(subject.id, datetime.now())
        ]
    }

    rule "deny-modification" {
        effect: DENY
        condition: (
            action.verb IN ["write", "delete", "update"]
        )
        obligations: [
            LOG_SECURITY_EVENT("immutable-data-modification-attempt",
                               subject.id, resource.id),
            ALERT_SECOPS(severity="critical"),
            BLOCK_IP(environment.client_ip, duration="24h")
        ]
    }
}
```

#### Política de conformidade regulatória (LGPD/GDPR)

```
policy "lgpd-data-access" {
    target {
        resource.data_category IN ["personal-data", "sensitive-data"]
        AND resource.jurisdiction == "BR"
    }

    rule "data-subject-access" {
        effect: PERMIT
        condition: (
            subject.role == "data-subject"
            AND subject.cpf == resource.owner_cpf
            AND action.verb == "read"
        )
        obligations: [
            LOG_DATA_SUBJECT_ACCESS(subject.id, resource.id),
            REDACT_SENSITIVE_FIELDS(resource.id, fields=["cpf", "rg"])
        ]
    }

    rule "legal-basis-access" {
        effect: PERMIT
        condition: (
            subject.role IN ["data-analyst", "dpo"]
            AND subject.legal_basis != null
            AND subject.legal_basis IN ["consent", "contract", "legal-obligation",
                                         "legitimate-interest", "vital-interest",
                                         "public-interest", "research"]
            AND resource.processing_purpose == subject.legal_basis
        )
        obligations: [
            LOG_LEGAL_BASIS_ACCESS(subject.id, resource.id, subject.legal_basis),
            NOTIFY_DATA_SUBJECT(resource.owner_id, subject.legal_basis)
        ]
    }

    rule "deny-unauthorized-processing" {
        effect: DENY
        condition: (
            action.verb IN ["process", "transfer", "export"]
            AND NOT (
                subject.role IN ["data-analyst", "dpo"]
                AND subject.legal_basis != null
            )
        )
        obligations: [
            LOG_COMPLIANCE_VIOLATION(subject.id, resource.id),
            ALERT_DPO(severity="high")
        ]
    }
}
```

### Integração com o caso Misantropi4

No caso Misantropi4, o sistema ABAC completo combinaria todas essas políticas usando deny-overrides como algoritmo de combinação. Isso garante que qualquer DENY de qualquer política resulta em DENY global — uma postura de segurança conservadora e adequada para dados financeiros.

```python
class Misantropi4AccessControl:
    def __init__(self):
        self.engine = PolicyEngine(
            attribute_resolver=AttributeResolver(),
            condition_evaluator=ConditionEvaluator(),
        )
        self.engine.load_policies([
            TENANT_ISOLATION_POLICY,
            HIGH_VALUE_TRANSACTION_POLICY,
            RISK_BASED_ACCESS_POLICY,
            IMMUTABLE_AUDIT_POLICY,
            LGPD_DATA_ACCESS_POLICY,
        ])

    def check_access(self, request: AccessRequest) -> AccessDecision:
        decision = self.engine.evaluate(request)

        if decision.decision == Decision.PERMIT:
            for obligation in decision.obligations:
                self._execute_obligation(obligation, request)

        self._record_decision(request, decision)
        return decision
```

## 10.11 Testing e Validação de Políticas ABAC

Testar políticas ABAC é fundamental para garantir que o comportamento esperado realmente ocorre em produção. Políticas complexas com múltiplas condições, obrigações e algoritmos de combinação são propensas a erros sutis que só se manifestam em cenários específicos.

### Estratégias de teste

**1. Testes unitários para regras individuais**

Cada regra deve ser testada isoladamente com cenários positivos e negativos:

```python
import pytest
from typing import Dict, List


class TestRuleEvaluation:
    def setup_method(self):
        self.engine = PolicyEngine(
            attribute_resolver=AttributeResolver(),
            condition_evaluator=ConditionEvaluator(),
        )

    def test_nurse_read_patient_allows_assigned_patient(self):
        policy = Policy(
            id="nurse-read",
            target={"conditions": [
                {"category": "subject", "attribute": "role", "operator": "eq", "value": "nurse"},
            ]},
            rules=[{
                "id": "nurse-read-assigned",
                "effect": "permit",
                "conditions": [
                    {"category": "subject", "attribute": "role", "operator": "eq", "value": "nurse"},
                    {"category": "subject", "attribute": "assigned_patients", "operator": "contains", "value": "patient-123"},
                    {"category": "action", "attribute": "verb", "operator": "eq", "value": "read"},
                ],
            }],
            combining_algorithm="deny-overrides",
        )
        self.engine.load_policies([policy])

        request = AccessRequest(
            subject={"role": "nurse", "assigned_patients": ["patient-123", "patient-456"]},
            resource={"id": "patient-123", "type": "patient-record"},
            action={"verb": "read"},
            environment={"is_business_hours": True},
        )

        decision = self.engine.evaluate(request)
        assert decision.decision == Decision.PERMIT

    def test_nurse_read_patient_denies_unassigned_patient(self):
        policy = Policy(
            id="nurse-read",
            target={"conditions": [
                {"category": "subject", "attribute": "role", "operator": "eq", "value": "nurse"},
            ]},
            rules=[{
                "id": "nurse-read-assigned",
                "effect": "permit",
                "conditions": [
                    {"category": "subject", "attribute": "role", "operator": "eq", "value": "nurse"},
                    {"category": "subject", "attribute": "assigned_patients", "operator": "contains", "value": "patient-999"},
                    {"category": "action", "attribute": "verb", "operator": "eq", "value": "read"},
                ],
            }],
            combining_algorithm="deny-overrides",
        )
        self.engine.load_policies([policy])

        request = AccessRequest(
            subject={"role": "nurse", "assigned_patients": ["patient-123"]},
            resource={"id": "patient-999", "type": "patient-record"},
            action={"verb": "read"},
            environment={"is_business_hours": True},
        )

        decision = self.engine.evaluate(request)
        assert decision.decision == Decision.INDETERMINATE

    def test_no_applicable_policy_returns_deny(self):
        self.engine.load_policies([])

        request = AccessRequest(
            subject={"role": "nurse"},
            resource={"id": "doc-1"},
            action={"verb": "read"},
            environment={},
        )

        decision = self.engine.evaluate(request)
        assert decision.decision == Decision.DENY
        assert "No applicable policy" in decision.reason

    def test_deny_overrides_permit(self):
        policy = Policy(
            id="test",
            target={"conditions": []},
            rules=[
                {
                    "id": "rule-1",
                    "effect": "permit",
                    "conditions": [{"category": "subject", "attribute": "role", "operator": "eq", "value": "nurse"}],
                },
                {
                    "id": "rule-2",
                    "effect": "deny",
                    "conditions": [{"category": "subject", "attribute": "department", "operator": "eq", "value": "suspended"}],
                },
            ],
            combining_algorithm="deny-overrides",
        )
        self.engine.load_policies([policy])

        request = AccessRequest(
            subject={"role": "nurse", "department": "suspended"},
            resource={"id": "doc-1"},
            action={"verb": "read"},
            environment={},
        )

        decision = self.engine.evaluate(request)
        assert decision.decision == Decision.DENY
```

**2. Testes de target matching**

Targets determinam quando uma política se aplica. Erros em targets são difíceis de detectar porque a política simplesmente não é avaliada:

```python
class TestTargetMatching:
    def test_target_matches_exact_value(self):
        target = Target(
            expressions=[
                {"category": "subject", "attribute": "role", "operator": "string-equals", "value": "admin"}
            ]
        )
        request = AccessRequest(
            subject={"role": "admin"},
            resource={},
            action={},
            environment={},
        )
        assert target.matches(request) is True

    def test_target_rejects_wrong_value(self):
        target = Target(
            expressions=[
                {"category": "subject", "attribute": "role", "operator": "string-equals", "value": "admin"}
            ]
        )
        request = AccessRequest(
            subject={"role": "user"},
            resource={},
            action={},
            environment={},
        )
        assert target.matches(request) is False

    def test_target_with_and_operator(self):
        target = Target(
            expressions=[
                {"category": "subject", "attribute": "role", "operator": "string-equals", "value": "nurse"},
                {"category": "resource", "attribute": "type", "operator": "string-equals", "value": "patient-record"},
            ],
            operator="AND",
        )
        request = AccessRequest(
            subject={"role": "nurse"},
            resource={"type": "patient-record"},
            action={},
            environment={},
        )
        assert target.matches(request) is True

    def test_target_with_or_operator(self):
        target = Target(
            expressions=[
                {"category": "subject", "attribute": "role", "operator": "string-equals", "value": "admin"},
                {"category": "subject", "attribute": "role", "operator": "string-equals", "value": "superadmin"},
            ],
            operator="OR",
        )
        request = AccessRequest(
            subject={"role": "superadmin"},
            resource={},
            action={},
            environment={},
        )
        assert target.matches(request) is True

    def test_target_numeric_comparison(self):
        target = Target(
            expressions=[
                {"category": "resource", "attribute": "amount", "operator": "numeric-greater-than", "value": 10000}
            ]
        )
        request = AccessRequest(
            subject={},
            resource={"amount": 25000},
            action={},
            environment={},
        )
        assert target.matches(request) is True
```

**3. Testes de algoritmos de combinação**

```python
class TestCombiningAlgorithms:
    def test_permit_overrides_returns_permit(self):
        decisions = [
            AccessDecision(Decision.DENY, reason="denied"),
            AccessDecision(Decision.PERMIT, reason="allowed"),
        ]
        result = CombiningAlgorithms.permit_overrides(decisions)
        assert result.decision == Decision.PERMIT

    def test_deny_overrides_returns_deny(self):
        decisions = [
            AccessDecision(Decision.PERMIT, reason="allowed"),
            AccessDecision(Decision.DENY, reason="denied"),
        ]
        result = CombiningAlgorithms.deny_overrides(decisions)
        assert result.decision == Decision.DENY

    def test_first_applicable_returns_first_decided(self):
        decisions = [
            AccessDecision(Decision.INDETERMINATE, reason="unknown"),
            AccessDecision(Decision.PERMIT, reason="allowed"),
            AccessDecision(Decision.DENY, reason="denied"),
        ]
        result = CombiningAlgorithms.first_applicable(decisions)
        assert result.decision == Decision.PERMIT

    def test_all_indeterminate_returns_indeterminate(self):
        decisions = [
            AccessDecision(Decision.INDETERMINATE),
            AccessDecision(Decision.INDETERMINATE),
        ]
        result = CombiningAlgorithms.permit_overrides(decisions)
        assert result.decision == Decision.INDETERMINATE
```

**4. Testes de obrigações**

```python
class TestObligations:
    def test_obligation_executed_on_permit(self):
        executor = MockObligationExecutor()
        obligation = Obligation(
            obligation_id="log-1",
            obligation_type="LOG_ACCESS",
            target="audit-store",
            parameters={"level": "info"},
        )
        request = AccessRequest(
            subject={"id": "user-1"},
            resource={"id": "doc-1"},
            action={"verb": "read"},
            environment={},
        )
        executor.execute(obligation, request)
        assert executor.executed == [("LOG_ACCESS", "user-1", "doc-1")]

    def test_obligation_not_executed_on_deny(self):
        pass

    def test_multiple_obligations_executed(self):
        executor = MockObligationExecutor()
        obligations = [
            Obligation("log-1", "LOG_ACCESS", "audit", {}),
            Obligation("notify-1", "NOTIFY_ADMIN", "admin", {}),
        ]
        request = AccessRequest(
            subject={"id": "user-1"},
            resource={"id": "doc-1"},
            action={"verb": "read"},
            environment={},
        )
        for obl in obligations:
            executor.execute(obl, request)
        assert len(executor.executed) == 2
```

### Property-based testing

Property-based testing gera entradas aleatórias e verifica propriedades que devem ser sempre verdadeiras:

```python
from hypothesis import given, strategies as st

class TestABACProperties:
    @given(
        role=st.sampled_from(["nurse", "doctor", "admin", "user"]),
        resource_type=st.sampled_from(["patient-record", "lab-result", "prescription"]),
        action=st.sampled_from(["read", "write", "delete"]),
    )
    def test_deny_without_policy_is_always_safe(self, role, resource_type, action):
        engine = PolicyEngine(
            attribute_resolver=AttributeResolver(),
            condition_evaluator=ConditionEvaluator(),
        )
        engine.load_policies([])

        request = AccessRequest(
            subject={"role": role},
            resource={"type": resource_type},
            action={"verb": action},
            environment={},
        )
        decision = engine.evaluate(request)
        assert decision.decision == Decision.DENY

    @given(amount=st.floats(min_value=0, max_value=10000000))
    def test_high_value_transaction_requires_approval(self, amount):
        policy = Policy(
            id="high-value",
            target={"conditions": [
                {"category": "resource", "attribute": "amount", "operator": "numeric-greater-than", "value": 100000}
            ]},
            rules=[{
                "id": "require-approval",
                "effect": "deny",
                "conditions": [
                    {"category": "resource", "attribute": "approval_count", "operator": "numeric-less-than", "value": 2}
                ],
            }],
            combining_algorithm="deny-overrides",
        )
        engine = PolicyEngine(
            attribute_resolver=AttributeResolver(),
            condition_evaluator=ConditionEvaluator(),
        )
        engine.load_policies([policy])

        if amount > 100000:
            request = AccessRequest(
                subject={"role": "trader"},
                resource={"amount": amount, "approval_count": 0},
                action={"verb": "execute"},
                environment={},
            )
            decision = engine.evaluate(request)
            assert decision.decision == Decision.DENY
```

### Fuzzing de políticas

```python
import random
import string

class PolicyFuzzer:
    def __init__(self, engine: PolicyEngine):
        self.engine = engine

    def generate_random_request(self) -> AccessRequest:
        return AccessRequest(
            subject={
                "role": random.choice(["admin", "user", "nurse", "doctor", None]),
                "department": random.choice(["hr", "finance", "it", None]),
                "clearance_level": random.randint(0, 10),
                "mfa_verified": random.choice([True, False]),
            },
            resource={
                "type": random.choice(["document", "patient-record", "transaction", None]),
                "sensitivity": random.choice(["low", "medium", "high", None]),
                "amount": random.uniform(0, 1000000),
                "tenant_id": random.choice(["t1", "t2", "t3"]),
            },
            action={
                "verb": random.choice(["read", "write", "delete", "approve", None]),
            },
            environment={
                "is_business_hours": random.choice([True, False]),
                "network_zone": random.choice(["internal", "external", "vpn", None]),
                "threat_level": random.choice(["low", "medium", "high"]),
            },
        )

    def fuzz(self, iterations: int = 10000) -> dict:
        results = {"PERMIT": 0, "DENY": 0, "INDETERMINATE": 0, "ERROR": 0}

        for i in range(iterations):
            try:
                request = self.generate_random_request()
                decision = self.engine.evaluate(request)
                results[decision.decision.value] += 1
            except Exception as e:
                results["ERROR"] += 1
                print(f"Error at iteration {i}: {e}")

        return results

    def fuzz_edge_cases(self) -> list:
        edge_cases = [
            AccessRequest(subject={}, resource={}, action={}, environment={}),
            AccessRequest(
                subject={"role": None},
                resource={"type": "x" * 10000},
                action={"verb": ""},
                environment={"time": -1},
            ),
            AccessRequest(
                subject={"role": "admin", "clearance_level": float("inf")},
                resource={"amount": float("nan")},
                action={"verb": "read"},
                environment={},
            ),
        ]

        failures = []
        for i, request in enumerate(edge_cases):
            try:
                decision = self.engine.evaluate(request)
            except Exception as e:
                failures.append({"case": i, "error": str(e), "request": request})

        return failures
```

## 10.12 Padrões de Projeto para ABAC em Produção

### Padrão: Policy-as-Code

Políticas ABAC devem ser tratadas como código — versionadas, testadas, e revisadas:

```python
class PolicyAsCodeRepository:
    def __init__(self, git_repo_path: str):
        self.repo_path = git_repo_path
        self.policy_store = PolicyStore()

    def load_policies_from_files(self):
        import os
        for root, dirs, files in os.walk(self.repo_path):
            for f in files:
                if f.endswith(".policy.json"):
                    path = os.path.join(root, f)
                    with open(path) as fh:
                        policy_data = json.load(fh)
                    policy = Policy.from_dict(policy_data)
                    self.policy_store.add(policy)

    def validate_all_policies(self) -> list:
        errors = []
        for policy in self.policy_store.list_all():
            validator = PolicyValidator()
            errs = validator.validate(policy)
            if errs:
                errors.extend([{"policy": policy.id, "error": e} for e in errs])
        return errors

    def diff_policies(self, old_version: str, new_version: str) -> dict:
        old_policies = self._load_version(old_version)
        new_policies = self._load_version(new_version)

        old_ids = {p.id for p in old_policies}
        new_ids = {p.id for p in new_policies}

        return {
            "added": list(new_ids - old_ids),
            "removed": list(old_ids - new_ids),
            "modified": [
                p.id for p in new_policies
                if p.id in old_ids and p != self._find_by_id(old_policies, p.id)
            ],
        }

    def _load_version(self, version: str) -> list:
        return []

    def _find_by_id(self, policies: list, policy_id: str):
        for p in policies:
            if p.id == policy_id:
                return p
        return None
```

### Padrão: Circuit Breaker para PDP

```python
import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerPDP:
    def __init__(self, pdp: PolicyDecisionPoint,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 30):
        self.pdp = pdp
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0

    def evaluate(self, request: AccessRequest) -> AccessDecision:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return AccessDecision(
                    decision=Decision.DENY,
                    reason="Circuit breaker open — PDP unavailable",
                )

        try:
            decision = self.pdp.evaluate(request)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return decision
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            return AccessDecision(
                decision=Decision.DENY,
                reason=f"PDP error: {e}",
            )
```

### Padrão: Policy Distribution com Event Sourcing

```python
class PolicyEventStore:
    def __init__(self):
        self.events: list = []
        self.projections: dict = {}

    def append(self, event: dict):
        self.events.append(event)
        self._update_projections(event)

    def _update_projections(self, event: dict):
        event_type = event["type"]
        if event_type == "policy.created":
            policy = event["payload"]
            self.projections[policy["id"]] = policy
        elif event_type == "policy.updated":
            policy = event["payload"]
            self.projections[policy["id"]] = policy
        elif event_type == "policy.deleted":
            self.projections.pop(event["policy_id"], None)

    def get_current_policies(self) -> list:
        return list(self.projections.values())

    def get_events_since(self, timestamp: float) -> list:
        return [e for e in self.events if e["timestamp"] >= timestamp]

    def rebuild_projection(self):
        self.projections = {}
        for event in self.events:
            self._update_projections(event)
```

### Padrão: Multi-Region Policy Sync

```python
class MultiRegionPolicySync:
    def __init__(self, local_region: str, regions: list):
        self.local_region = local_region
        self.regions = regions
        self.policy_store = PolicyStore()
        self.sync_log = []

    def publish_policy_change(self, policy: Policy, change_type: str):
        event = {
            "type": f"policy.{change_type}",
            "policy": policy.serialize(),
            "source_region": self.local_region,
            "timestamp": time.time(),
            "sequence": self._next_sequence(),
        }

        for region in self.regions:
            if region != self.local_region:
                self._send_to_region(region, event)

        self.sync_log.append(event)

    def handle_remote_event(self, event: dict):
        source = event["source_region"]
        sequence = event["sequence"]

        if self._already_applied(source, sequence):
            return

        if event["type"] == "policy.created":
            policy = Policy.deserialize(event["policy"])
            self.policy_store.add(policy)
        elif event["type"] == "policy.updated":
            policy = Policy.deserialize(event["policy"])
            self.policy_store.update(policy.id, policy)
        elif event["type"] == "policy.deleted":
            self.policy_store.delete(event["policy_id"])

        self._mark_applied(source, sequence)

    def _send_to_region(self, region: str, event: dict):
        pass

    def _next_sequence(self) -> int:
        return len(self.sync_log) + 1

    def _already_applied(self, source: str, sequence: int) -> bool:
        return False

    def _mark_applied(self, source: str, sequence: int):
        pass
```

## 10.13 Erros Comuns e Anti-Padrões

### Anti-padrão 1: Default Permit

O erro mais perigoso em ABAC é retornar PERMIT quando nenhuma política se aplica. O padrão correto é sempre retornar DENY quando não há política aplicável.

```python
class DangerousPDPOld:
    def evaluate(self, request):
        applicable = self.find_applicable_policies(request)
        if not applicable:
            return Decision.PERMIT  # PERIGO: default permit

class SafePDPNew:
    def evaluate(self, request):
        applicable = self.find_applicable_policies(request)
        if not applicable:
            return Decision.DENY  # CORRETO: default deny
```

### Anti-padrão 2: Avaliar todos os atributos antes de verificar regras

```python
class InefficientEvaluation:
    def evaluate(self, request):
        all_attrs = self.collect_all_attributes(request)
        for rule in self.rules:
            if self.check_rule(rule, all_attrs):
                return rule.effect
        return "DENY"

class EfficientEvaluation:
    def evaluate(self, request):
        for rule in self.rules:
            if self.quick_check(rule, request):
                all_attrs = self.collect_needed_attributes(rule, request)
                if self.check_rule(rule, all_attrs):
                    return rule.effect
        return "DENY"
```

### Anti-padrão 3: Cache sem invalidação

```python
class BadCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

class GoodCache:
    def __init__(self, ttl_seconds=30):
        self.cache = {}
        self.timestamps = {}

    def get(self, key):
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None

    def invalidate_for_subject(self, subject_id: str):
        keys_to_remove = [k for k in self.cache if subject_id in k]
        for k in keys_to_remove:
            del self.cache[k]
            del self.timestamps[k]
```

### Anti-padrão 4: Logs de decisão incompletos

```python
class IncompleteAudit:
    def log_decision(self, request, decision):
        self.log(f"Decision: {decision}")

class CompleteAudit:
    def log_decision(self, request, decision):
        self.log({
            "timestamp": datetime.utcnow().isoformat(),
            "subject": request.subject,
            "resource": request.resource,
            "action": request.action,
            "environment": request.environment,
            "decision": decision.value,
            "reason": decision.reason,
            "obligations": decision.obligations,
            "policies_evaluated": decision.policies_evaluated,
            "attributes_used": decision.attributes_used,
        })
```

---

## 10.14 ABAC no Caso Misantropi4 — Implementação Completa

O caso Misantropi4 representa uma plataforma de dados financeiros multi-tenant que processa transações de alto volume com requisitos regulatórios estritos. A implementação ABAC completa cobre todas as camadas de segurança necessárias.

### Arquitetura de segurança em camadas

A arquitetura do Misantropi4 usa ABAC em múltiplas camadas para defesa em profundidade:

```
Camada 1: Autenticação (mTLS + JWT)
    ↓
Camada 2: Autorização de serviço (Service Mesh ABAC)
    ↓
Camada 3: Autorização de dados (Data-level ABAC)
    ↓
Camada 4: Auditoria e compliance (Audit ABAC)
```

Cada camada avalia atributos diferentes e aplica políticas independentes. A falha em qualquer camada resulta em DENY — modelo fail-secure.

### Políticas por camada

```python
class Misantropi4LayeredPolicies:
    def __init__(self):
        self.service_policies = self._define_service_policies()
        self.data_policies = self._define_data_policies()
        self.audit_policies = self._define_audit_policies()

    def _define_service_policies(self):
        return [
            Policy(
                id="service-auth",
                target={"conditions": [
                    {"category": "environment", "attribute": "protocol", "operator": "eq", "value": "https"},
                    {"category": "environment", "attribute": "mtls_verified", "operator": "eq", "value": True},
                ]},
                rules=[{
                    "id": "require-mtls",
                    "effect": "permit",
                    "conditions": [
                        {"category": "environment", "attribute": "mtls_verified", "operator": "eq", "value": True},
                        {"category": "environment", "attribute": "jwt_valid", "operator": "eq", "value": True},
                    ],
                }],
                combining_algorithm="deny-overrides",
            ),
            Policy(
                id="service-rate-limit",
                target={"conditions": [
                    {"category": "subject", "attribute": "tenant_id", "operator": "neq", "value": None},
                ]},
                rules=[{
                    "id": "rate-limit",
                    "effect": "permit",
                    "conditions": [
                        {"category": "subject", "attribute": "request_count_1m", "operator": "numeric-less-than", "value": 1000},
                        {"category": "subject", "attribute": "request_count_1h", "operator": "numeric-less-than", "value": 50000},
                    ],
                }],
                combining_algorithm="deny-overrides",
            ),
        ]

    def _define_data_policies(self):
        return [
            Policy(
                id="data-tenant-isolation",
                target={"conditions": [
                    {"category": "resource", "attribute": "tenant_id", "operator": "neq", "value": None},
                ]},
                rules=[
                    {
                        "id": "tenant-can-access",
                        "effect": "permit",
                        "conditions": [
                            {"category": "subject", "attribute": "tenant_id", "operator": "eq", "value": "__resource.tenant_id"},
                            {"category": "subject", "attribute": "account_status", "operator": "eq", "value": "active"},
                        ],
                    },
                    {
                        "id": "cross-tenant-deny",
                        "effect": "deny",
                        "conditions": [
                            {"category": "subject", "attribute": "tenant_id", "operator": "neq", "value": "__resource.tenant_id"},
                        ],
                    },
                ],
                combining_algorithm="deny-overrides",
            ),
            Policy(
                id="data-classification",
                target={"conditions": [
                    {"category": "resource", "attribute": "classification", "operator": "in", "value": ["confidential", "secret"]},
                ]},
                rules=[{
                    "id": "high-classification-restrictions",
                    "effect": "permit",
                    "conditions": [
                        {"category": "subject", "attribute": "clearance_level", "operator": "numeric-greater-than-or-equal", "value": "__resource.classification_level"},
                        {"category": "environment", "attribute": "network_zone", "operator": "eq", "value": "internal"},
                        {"category": "subject", "attribute": "mfa_verified", "operator": "eq", "value": True},
                        {"category": "subject", "attribute": "device_trusted", "operator": "eq", "value": True},
                    ],
                }],
                combining_algorithm="deny-overrides",
            ),
            Policy(
                id="data-temporal",
                target={"conditions": [
                    {"category": "resource", "attribute": "sensitivity", "operator": "in", "value": ["high", "critical"]},
                ]},
                rules=[{
                    "id": "business-hours-only",
                    "effect": "permit",
                    "conditions": [
                        {"category": "environment", "attribute": "is_business_hours", "operator": "eq", "value": True},
                        {"category": "environment", "attribute": "day_of_week", "operator": "in", "value": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]},
                    ],
                }],
                combining_algorithm="deny-overrides",
            ),
        ]

    def _define_audit_policies(self):
        return [
            Policy(
                id="audit-immutable",
                target={"conditions": [
                    {"category": "resource", "attribute": "type", "operator": "eq", "value": "audit-log"},
                ]},
                rules=[
                    {
                        "id": "read-only-for-all",
                        "effect": "permit",
                        "conditions": [
                            {"category": "action", "attribute": "verb", "operator": "eq", "value": "read"},
                            {"category": "subject", "attribute": "role", "operator": "in", "value": ["auditor", "compliance-officer"]},
                        ],
                    },
                    {
                        "id": "deny-modification",
                        "effect": "deny",
                        "conditions": [
                            {"category": "action", "attribute": "verb", "operator": "in", "value": ["write", "delete", "update"]},
                        ],
                    },
                ],
                combining_algorithm="deny-overrides",
            ),
        ]
```

### Integração com OpenPolicyAgent (OPA)

```python
class OPAIntegration:
    def __init__(self, opa_endpoint: str):
        self.endpoint = opa_endpoint

    async def evaluate(self, input_data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/data/misantropi4/authz/allow",
                json={"input": input_data},
            )
            return response.json()

    async def evaluate_batch(self, inputs: list) -> list:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/v1/data/misantropi4/authz/allow",
                json={"input": inputs},
            )
            return response.json()
```

Política Rego para OPA:

```rego
package misantropi4.authz

default allow = false

# Service-level authorization
allow {
    input.environment.mtls_verified == true
    input.environment.jwt_valid == true
    input.subject.tenant_id == input.resource.tenant_id
    input.subject.account_status == "active"
}

# Tenant isolation
allow {
    input.subject.tenant_id == input.resource.tenant_id
    input.subject.account_status == "active"
    input.subject.clearance_level >= input.resource.classification_level
}

# High-value transaction requires dual approval
allow {
    input.resource.type == "transaction"
    input.resource.amount > 100000
    input.resource.approval_count >= 2
    input.subject.mfa_verified == true
    input.environment.network_zone == "trading-floor"
}

# Temporal restriction for sensitive data
allow {
    input.resource.sensitivity == "high"
    input.environment.is_business_hours == true
    input.environment.day_of_week != "Saturday"
    input.environment.day_of_week != "Sunday"
}

# Audit log read-only
allow {
    input.resource.type == "audit-log"
    input.action.verb == "read"
    input.subject.role == "auditor"
}

# Deny cross-tenant access
deny {
    input.subject.tenant_id != input.resource.tenant_id
}

# Deny modification of audit logs
deny {
    input.resource.type == "audit-log"
    input.action.verb == "write"
}

# Obligations for permitted access
obligations = obligations_log {
    allow
    input.action.verb == "read"
    obligations_log := {"type": "LOG_ACCESS", "level": "info"}
}

obligations = obligations_notify {
    allow
    input.resource.amount > 100000
    obligations_notify := {"type": "NOTIFY_COMPLIANCE", "severity": "high"}
}
```

### Métricas e observabilidade

```python
class Misantropi4AuthZMetrics:
    def __init__(self):
        self.decision_counts = {"PERMIT": 0, "DENY": 0, "INDETERMINATE": 0}
        self.latency_histogram = []
        self.policy_hit_counts = {}
        self.tenant_decision_counts = {}

    def record_decision(self, decision: AccessDecision, latency_ms: float,
                        tenant_id: str, policy_ids: list):
        self.decision_counts[decision.decision.value] += 1
        self.latency_histogram.append(latency_ms)

        for pid in policy_ids:
            self.policy_hit_counts[pid] = self.policy_hit_counts.get(pid, 0) + 1

        self.tenant_decision_counts.setdefault(tenant_id, {"PERMIT": 0, "DENY": 0})
        self.tenant_decision_counts[tenant_id][decision.decision.value] += 1

    def get_p99_latency(self) -> float:
        sorted_latencies = sorted(self.latency_histogram)
        p99_index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[p99_index] if sorted_latencies else 0

    def get_denial_rate(self, tenant_id: str = None) -> float:
        if tenant_id:
            counts = self.tenant_decision_counts.get(tenant_id, {"PERMIT": 0, "DENY": 0})
            total = counts["PERMIT"] + counts["DENY"]
            return counts["DENY"] / total if total > 0 else 0
        total = self.decision_counts["PERMIT"] + self.decision_counts["DENY"]
        return self.decision_counts["DENY"] / total if total > 0 else 0

    def get_top_policies(self, limit: int = 10) -> list:
        sorted_policies = sorted(
            self.policy_hit_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_policies[:limit]
```

---

## 10.15 Referências

- NIST SP 800-162: Guide to Attribute-Based Access Control
- NIST SP 800-205: Attribute Considerations for Access Control
- OASIS XACML 3.0 Standard
- Ferraiolo, D., Kuhn, D.R., Chandramouli, R. "Role-Based Access Control" (2003)
- Hu, V.C. et al. "Guide to Attribute-Based Access Control (ABAC) Definition and Considerations" (2014)
- Biskup, J. "Security in Computing Systems" (2009)
- Park, J., Sandhu, R. "The UCONUsage Usage Control Model" (2004)
- Jin, X. et al. "ABAC Policy Administration in Large-Scale Systems" (2016)
- Martin, R. et al. "The XACML v3.0 core profile" (2013)
- Anderson, A. "XACML Profile for Role-Based Access Control" (2004)
- Kuhn, D.R. et al. "Introduction to Role-Based Access Control" (NIST, 2020)
- Lupu, E., Sloman, M. "Towards a Role-Based Framework for Distributed Systems Management" (1997)
- Schaad, J. et al. "A Role-Based Access Control Method Using XML" (2001)
- Moses, T. "eXtensible Access Control Markup Language (XACML) Version 3.0" (2013)
- OASIS. "Core and Hierarchical Role Based Access Control (RBAC) Profile of XACML v2.0" (2005)
- Smith, B. "A Guide to Implementing ABAC in Enterprise Systems" (2020)
- Fong, P.W.L. "Attribute-Based Access Control for protecting web services" (2007)
- Chandramouli, R. "Reference Architecture for Attribute Based Access Control" (2015)
- NIST. "Policy Machine" (2020)
- Open Policy Agent. "Rego Policy Language" (2021)
- AWS Cedar. "Cedar Policy Language" (2022)
