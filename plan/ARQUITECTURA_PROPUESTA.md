# Propuesta de Arquitectura: Multi-Agent Conversational System

## Diagnóstico del Estado Actual

### Problemas Identificados

1. **LLMAgent como "God Object"** (544 líneas)
   - Orquestación + lógica de negocio + detalles de implementación
   - Difícil de testear y mantener
   - Cambios pequeños afectan todo el sistema

2. **Múltiples puntos de entrada inconsistentes**
   - `query_handlers` → `ToolSelector` → `ToolOrchestrator`
   - `command_handlers` → directo a BD
   - `tools_handlers` → diferente flujo

3. **Acoplamiento fuerte**
   - Todo pasa por LLMAgent
   - ExecutionContext se convierte en contenedor de dependencias
   - Componentes no pueden funcionar independientemente

4. **Lógica duplicada**
   - QueryClassifier vs ToolSelector hacen cosas similares
   - Múltiples puntos de clasificación de intención

---

## Propuesta: Arquitectura Multi-Agent con Event Sourcing

### Principios Fundamentales

```
┌─────────────────────────────────────────────────────────────────┐
│  1. SINGLE RESPONSIBILITY: Un agente = una responsabilidad     │
│  2. EVENT-DRIVEN: Comunicación por eventos, no llamadas        │
│  3. STATELESS AGENTS: Estado en event store, no en memoria     │
│  4. OBSERVABLE: Cada acción es trazable                        │
│  5. COMPOSABLE: Agentes se combinan como piezas LEGO           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquitectura Propuesta

```
                                    ┌──────────────────┐
                                    │   Telegram API   │
                                    └────────┬─────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           GATEWAY LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  MessageGateway: Normaliza input de cualquier canal (Telegram,      │  │
│  │  WhatsApp, API REST, WebSocket) a un formato unificado              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼ ConversationEvent
┌────────────────────────────────────────────────────────────────────────────┐
│                           EVENT BUS (In-Memory or Redis)                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Pub/Sub para comunicación desacoplada entre agentes               │  │
│  │  Eventos: MessageReceived, IntentClassified, QueryGenerated, etc.  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    ▼                        ▼                        ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│    SUPERVISOR AGENT     │  │     EVENT STORE         │  │   OBSERVABILITY         │
│                         │  │                         │  │                         │
│  - Recibe eventos       │  │  - Persiste todos los   │  │  - OpenTelemetry traces │
│  - Decide qué agente    │  │    eventos              │  │  - Métricas por agente  │
│    debe actuar          │  │  - Replay para debug    │  │  - Alertas automáticas  │
│  - Maneja timeouts      │  │  - Audit trail          │  │                         │
│  - Coordina multi-turn  │  │                         │  │                         │
└───────────┬─────────────┘  └─────────────────────────┘  └─────────────────────────┘
            │
            │ Delega según intención
            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         AGENT POOL (Especialistas)                         │
│                                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  CLASSIFIER  │  │   KNOWLEDGE  │  │   DATABASE   │  │   CHITCHAT   │  │
│  │    AGENT     │  │    AGENT     │  │    AGENT     │  │    AGENT     │  │
│  │              │  │              │  │              │  │              │  │
│  │ Determina    │  │ RAG sobre    │  │ Text-to-SQL  │  │ Conversación │  │
│  │ intención    │  │ knowledge    │  │ + ejecución  │  │ casual       │  │
│  │ del usuario  │  │ base         │  │ + formateo   │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   MEMORY     │  │   GUARDRAIL  │  │    TOOL      │  │   PLANNER    │  │
│  │    AGENT     │  │    AGENT     │  │    AGENT     │  │    AGENT     │  │
│  │              │  │              │  │              │  │              │  │
│  │ Gestiona     │  │ Valida       │  │ Ejecuta      │  │ Descompone   │  │
│  │ contexto     │  │ seguridad    │  │ tools        │  │ tareas       │  │
│  │ usuario      │  │ y políticas  │  │ externos     │  │ complejas    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                             │
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         SHARED SERVICES                                    │
│                                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ LLM Gateway │  │  DB Pool    │  │   Cache     │  │  Secrets    │      │
│  │             │  │             │  │  (Redis)    │  │  Manager    │      │
│  │ Rate limit  │  │ Connection  │  │             │  │             │      │
│  │ Fallback    │  │ pooling     │  │ Embeddings  │  │ API keys    │      │
│  │ Multi-model │  │             │  │ Sessions    │  │ Tokens      │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Detalle de Cada Agente

### 1. SupervisorAgent (El Orquestador)

```python
class SupervisorAgent:
    """
    Único punto de entrada. No contiene lógica de negocio.
    Solo decide qué agente debe actuar y coordina.
    """

    async def handle(self, event: ConversationEvent) -> AgentResponse:
        # 1. Obtener contexto de memoria
        context = await self.memory_agent.get_context(event.user_id)

        # 2. Clasificar intención
        intent = await self.classifier_agent.classify(event, context)

        # 3. Validar seguridad
        if not await self.guardrail_agent.validate(event, intent):
            return AgentResponse.blocked("Operación no permitida")

        # 4. Delegar al agente especialista
        specialist = self.router.get_agent(intent.type)
        response = await specialist.execute(event, intent, context)

        # 5. Actualizar memoria (async, no bloquea)
        asyncio.create_task(
            self.memory_agent.record(event, response)
        )

        return response
```

**Responsabilidad**: Solo coordinación. Cero lógica de negocio.

---

### 2. ClassifierAgent (Intención + Routing)

```python
class ClassifierAgent:
    """
    Determina QUÉ quiere el usuario y A DÓNDE debe ir.
    Reemplaza: QueryClassifier + ToolSelector
    """

    class Intent(BaseModel):
        type: Literal["database", "knowledge", "chitchat", "tool", "clarification"]
        confidence: float
        entities: dict[str, Any]
        suggested_agent: str
        requires_clarification: bool
        clarification_question: Optional[str]

    async def classify(
        self,
        event: ConversationEvent,
        context: UserContext
    ) -> Intent:
        # Un solo LLM call con structured output
        return await self.llm.generate_structured(
            prompt=self.build_prompt(event, context),
            schema=Intent
        )
```

**Innovación**: Un solo punto de clasificación. Output estructurado con confianza.

---

### 3. DatabaseAgent (Text-to-SQL Especializado)

```python
class DatabaseAgent:
    """
    Especialista en consultas a base de datos.
    Pipeline completo: SQL → Validación → Ejecución → Formato
    """

    async def execute(
        self,
        event: ConversationEvent,
        intent: Intent,
        context: UserContext
    ) -> AgentResponse:

        # Pipeline interno con pasos claros
        pipeline = (
            self.generate_sql
            | self.validate_sql
            | self.execute_sql
            | self.format_response
        )

        return await pipeline.run(event, intent, context)

    async def generate_sql(self, state: PipelineState) -> PipelineState:
        # Genera SQL usando schema + ejemplos few-shot
        ...

    async def validate_sql(self, state: PipelineState) -> PipelineState:
        # Valida seguridad (solo SELECT, no injection)
        ...

    async def execute_sql(self, state: PipelineState) -> PipelineState:
        # Ejecuta contra la BD
        ...

    async def format_response(self, state: PipelineState) -> PipelineState:
        # Formatea en lenguaje natural
        ...
```

**Innovación**: Pipeline pattern interno. Cada paso es testeable independientemente.

---

### 4. KnowledgeAgent (RAG Moderno)

```python
class KnowledgeAgent:
    """
    Retrieval-Augmented Generation sobre base de conocimiento.
    Usa embeddings para búsqueda semántica.
    """

    async def execute(
        self,
        event: ConversationEvent,
        intent: Intent,
        context: UserContext
    ) -> AgentResponse:

        # 1. Búsqueda híbrida: keyword + semantic
        results = await self.hybrid_search(
            query=event.text,
            user_roles=context.user.roles,
            top_k=5
        )

        # 2. Reranking con cross-encoder (opcional)
        ranked = await self.rerank(event.text, results)

        # 3. Generar respuesta con contexto
        return await self.generate_with_context(
            query=event.text,
            context=ranked,
            user_context=context
        )

    async def hybrid_search(self, query: str, user_roles: list, top_k: int):
        # Combina BM25 (keyword) + embeddings (semantic)
        keyword_results = await self.bm25_search(query)
        semantic_results = await self.vector_search(
            embedding=await self.embed(query)
        )
        return self.merge_results(keyword_results, semantic_results)
```

**Innovación**: Búsqueda híbrida + reranking = resultados más relevantes.

---

### 5. MemoryAgent (Memoria Persistente Inteligente)

```python
class MemoryAgent:
    """
    Gestiona el contexto del usuario a través del tiempo.
    Memoria de trabajo + memoria a largo plazo.
    """

    class UserContext(BaseModel):
        user: UserProfile
        working_memory: list[Message]  # Últimos N mensajes
        long_term_summary: str  # Resumen generado por LLM
        preferences: dict[str, Any]  # Preferencias detectadas
        conversation_state: ConversationState  # Estado actual

    async def get_context(self, user_id: str) -> UserContext:
        # Combina todas las fuentes de memoria
        return UserContext(
            user=await self.get_profile(user_id),
            working_memory=await self.get_recent_messages(user_id, limit=10),
            long_term_summary=await self.get_summary(user_id),
            preferences=await self.get_preferences(user_id),
            conversation_state=await self.get_state(user_id)
        )

    async def record(
        self,
        event: ConversationEvent,
        response: AgentResponse
    ):
        # 1. Guardar en working memory
        await self.save_message(event, response)

        # 2. Detectar preferencias implícitas
        preferences = await self.extract_preferences(event)
        if preferences:
            await self.update_preferences(event.user_id, preferences)

        # 3. Actualizar resumen si es necesario (cada N interacciones)
        if await self.should_update_summary(event.user_id):
            await self.update_summary(event.user_id)
```

**Innovación**: Memoria en capas (working + long-term) + extracción automática de preferencias.

---

### 6. GuardrailAgent (Seguridad y Políticas)

```python
class GuardrailAgent:
    """
    Valida seguridad, permisos y políticas antes de ejecutar.
    Intercepta todo ANTES de que llegue a los agentes especialistas.
    """

    class ValidationResult(BaseModel):
        allowed: bool
        reason: Optional[str]
        modified_input: Optional[str]  # Input sanitizado
        warnings: list[str]

    async def validate(
        self,
        event: ConversationEvent,
        intent: Intent
    ) -> ValidationResult:

        checks = [
            self.check_authentication(event),
            self.check_permissions(event, intent),
            self.check_rate_limit(event),
            self.check_content_policy(event),
            self.check_sql_injection(event) if intent.type == "database" else None,
            self.check_pii_exposure(event),
        ]

        results = await asyncio.gather(*[c for c in checks if c])

        # Si alguno falla, bloquear
        for result in results:
            if not result.allowed:
                return result

        return ValidationResult(allowed=True)
```

**Innovación**: Seguridad como ciudadano de primera clase. No es un afterthought.

---

### 7. PlannerAgent (Para Tareas Complejas)

```python
class PlannerAgent:
    """
    Descompone tareas complejas en pasos ejecutables.
    Inspirado en ReAct y Chain-of-Thought.
    """

    class Plan(BaseModel):
        steps: list[PlanStep]
        estimated_complexity: Literal["simple", "medium", "complex"]
        requires_confirmation: bool

    class PlanStep(BaseModel):
        action: str
        agent: str
        input: dict[str, Any]
        depends_on: list[int]  # Índices de pasos previos

    async def create_plan(
        self,
        event: ConversationEvent,
        intent: Intent
    ) -> Plan:
        # LLM genera plan estructurado
        return await self.llm.generate_structured(
            prompt=f"""
            Tarea: {event.text}
            Intención detectada: {intent}

            Genera un plan paso a paso usando los agentes disponibles:
            - DatabaseAgent: consultas a BD
            - KnowledgeAgent: búsqueda en conocimiento
            - ToolAgent: ejecución de herramientas

            Cada paso debe ser atómico y tener dependencias claras.
            """,
            schema=Plan
        )

    async def execute_plan(self, plan: Plan) -> AgentResponse:
        results = {}

        for i, step in enumerate(plan.steps):
            # Esperar dependencias
            deps = {j: results[j] for j in step.depends_on}

            # Ejecutar paso
            agent = self.agent_pool.get(step.agent)
            results[i] = await agent.execute_step(step, deps)

        return self.synthesize_results(results)
```

**Innovación**: Permite consultas multi-step como "Muéstrame los usuarios que más compraron el mes pasado y envíales un mensaje".

---

## Event Sourcing

### Eventos del Sistema

```python
# Todos los eventos heredan de BaseEvent
class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str  # Para trazar una conversación completa
    user_id: str

class MessageReceived(BaseEvent):
    channel: Literal["telegram", "whatsapp", "api"]
    text: str
    metadata: dict

class IntentClassified(BaseEvent):
    intent_type: str
    confidence: float
    entities: dict

class SQLGenerated(BaseEvent):
    query: str
    tables_used: list[str]

class SQLExecuted(BaseEvent):
    rows_returned: int
    execution_time_ms: float

class ResponseSent(BaseEvent):
    response_text: str
    agent_used: str
```

### Beneficios

1. **Audit Trail Completo**: Cada acción queda registrada
2. **Debugging**: Replay de eventos para reproducir bugs
3. **Analytics**: Métricas derivadas de eventos
4. **Rollback**: Reconstruir estado desde eventos

---

## Estructura de Carpetas Propuesta

```
src/
├── agents/                      # Agentes especializados
│   ├── base.py                  # BaseAgent, AgentResponse
│   ├── supervisor.py            # SupervisorAgent (orquestador)
│   ├── classifier.py            # ClassifierAgent (intención)
│   ├── database/                # DatabaseAgent
│   │   ├── agent.py
│   │   ├── sql_generator.py
│   │   ├── sql_validator.py
│   │   └── result_formatter.py
│   ├── knowledge/               # KnowledgeAgent
│   │   ├── agent.py
│   │   ├── retriever.py
│   │   └── reranker.py
│   ├── memory/                  # MemoryAgent
│   │   ├── agent.py
│   │   ├── working_memory.py
│   │   └── long_term.py
│   ├── guardrail/               # GuardrailAgent
│   │   ├── agent.py
│   │   ├── validators/
│   │   │   ├── auth.py
│   │   │   ├── permissions.py
│   │   │   ├── rate_limit.py
│   │   │   └── content_policy.py
│   │   └── sanitizers.py
│   ├── planner/                 # PlannerAgent
│   │   ├── agent.py
│   │   └── plan_executor.py
│   └── chitchat/                # ChitchatAgent
│       └── agent.py
│
├── events/                      # Event Sourcing
│   ├── base.py                  # BaseEvent
│   ├── conversation.py          # Eventos de conversación
│   ├── bus.py                   # EventBus (in-memory o Redis)
│   └── store.py                 # EventStore (persistencia)
│
├── gateway/                     # Capa de entrada
│   ├── telegram/
│   │   ├── handler.py
│   │   └── normalizer.py
│   ├── api/
│   │   └── routes.py
│   └── message_gateway.py       # Abstracción unificada
│
├── services/                    # Servicios compartidos
│   ├── llm/
│   │   ├── gateway.py           # LLM Gateway con rate limit
│   │   ├── providers/
│   │   │   ├── openai.py
│   │   │   └── anthropic.py
│   │   └── fallback.py
│   ├── database/
│   │   ├── pool.py
│   │   └── repositories/
│   ├── cache/
│   │   └── redis.py
│   └── embeddings/
│       └── encoder.py
│
├── observability/               # Trazabilidad
│   ├── tracing.py               # OpenTelemetry
│   ├── metrics.py
│   └── logging.py
│
└── config/
    ├── settings.py
    └── prompts/                 # Prompts versionados
        ├── classification.yaml
        ├── sql_generation.yaml
        └── response.yaml
```

---

## Migración Incremental

### Fase 1: Event Bus + Observability (1-2 semanas)
- Implementar EventBus simple (in-memory)
- Agregar tracing básico
- Los componentes actuales emiten eventos sin cambiar lógica

### Fase 2: Extraer Agentes (2-3 semanas)
- ClassifierAgent (extraer de QueryClassifier + ToolSelector)
- GuardrailAgent (extraer validaciones dispersas)
- Mantener LLMAgent como "legacy supervisor"

### Fase 3: SupervisorAgent (1-2 semanas)
- Nuevo SupervisorAgent reemplaza LLMAgent
- Routing basado en eventos
- LLMAgent se depreca gradualmente

### Fase 4: Agentes Especialistas (3-4 semanas)
- DatabaseAgent con pipeline interno
- KnowledgeAgent con búsqueda híbrida
- MemoryAgent con memoria en capas

### Fase 5: PlannerAgent + Features Avanzados (2-3 semanas)
- Tareas multi-step
- Confirmaciones interactivas
- Self-correction (reintentar con diferente estrategia)

---

## Comparativa: Antes vs Después

| Aspecto | Arquitectura Actual | Arquitectura Propuesta |
|---------|---------------------|------------------------|
| **Punto de entrada** | Múltiples (handlers) | Único (SupervisorAgent) |
| **Clasificación** | 2 lugares (QueryClassifier + ToolSelector) | 1 lugar (ClassifierAgent) |
| **Seguridad** | Dispersa (en handlers, orchestrator) | Centralizada (GuardrailAgent) |
| **Testing** | Difícil (todo acoplado) | Fácil (agentes independientes) |
| **Trazabilidad** | Logs dispersos | Event Sourcing completo |
| **Extensibilidad** | Modificar LLMAgent | Agregar nuevo agente |
| **Memoria** | Básica (últimos 3 mensajes) | En capas (working + long-term) |
| **Tareas complejas** | No soportado | PlannerAgent |
| **Multi-canal** | Solo Telegram | Gateway unificado |

---

## Tecnologías Recomendadas

| Componente | Opción Recomendada | Alternativas |
|------------|-------------------|--------------|
| Event Bus | Redis Pub/Sub | In-memory (dev), Kafka (escala) |
| Event Store | PostgreSQL | MongoDB, EventStoreDB |
| Cache | Redis | Memcached |
| Embeddings | OpenAI Ada-002 | Sentence Transformers (local) |
| Tracing | OpenTelemetry | Jaeger, Zipkin |
| LLM | Claude 3.5 Sonnet | GPT-4o, Mixtral |
| Vector Search | pgvector | Pinecone, Qdrant |

---

## Conclusión

Esta arquitectura transforma el sistema de un **monolito con un LLM central** a un **ecosistema de agentes especializados** que:

1. **Escalan independientemente**: Puedes agregar más instancias de DatabaseAgent si hay muchas queries
2. **Fallan gracefully**: Si KnowledgeAgent falla, el resto sigue funcionando
3. **Son observables**: Cada acción es un evento trazable
4. **Son testeables**: Cada agente se testea en aislamiento
5. **Son extensibles**: Agregar un nuevo agente no toca código existente

El paradigma de **agentes especializados + eventos** es el estándar actual en sistemas de IA conversacional de producción (ver: LangGraph, CrewAI, AutoGen).
