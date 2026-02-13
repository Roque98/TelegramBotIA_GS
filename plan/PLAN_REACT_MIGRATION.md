# Plan: Migración a Arquitectura ReAct

> **Estado**: En progreso
> **Última actualización**: 2024-02-13
> **Rama Git**: `feature/react-agent-migration`
> **Archivo referencia**: `src/agent/llm_agent.py` (544 líneas)

---

## Resumen de Progreso

| Fase | Progreso | Tareas | Estado |
|------|----------|--------|--------|
| Fase 1: Foundation | ██░░░░░░░░ 20% | 2/10 | En progreso |
| Fase 2: Tools | ░░░░░░░░░░ 0% | 0/8 | Pendiente |
| Fase 3: ReAct Core | ░░░░░░░░░░ 0% | 0/10 | Pendiente |
| Fase 4: Single-Step Agents | ░░░░░░░░░░ 0% | 0/8 | Pendiente |
| Fase 5: Orchestrator | ░░░░░░░░░░ 0% | 0/6 | Pendiente |
| Fase 6: Integration | ░░░░░░░░░░ 0% | 0/8 | Pendiente |
| Fase 7: Polish | ░░░░░░░░░░ 0% | 0/6 | Pendiente |

**Progreso Total**: 4% (2/56 tareas)

---

## Descripción

### Problema Actual

El `LLMAgent` actual (544 líneas) es un "God Object" con demasiadas responsabilidades:
- Orquestación + lógica de negocio + detalles de implementación
- Múltiples puntos de entrada inconsistentes
- Acoplamiento fuerte entre componentes
- Difícil de testear y mantener

### Solución Propuesta

Migrar a una arquitectura **multi-agent basada en ReAct (Reasoning + Acting)**:
- Separar responsabilidades en agentes especializados
- Implementar razonamiento paso a paso para consultas complejas
- Mejorar testabilidad y extensibilidad
- Mantener compatibilidad con funcionalidad actual

### Estrategia: Strangler Fig Pattern

No reescribimos todo de una vez. Envolvemos el sistema actual con la nueva arquitectura, migrando pieza por pieza.

---

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRADA                                        │
│  Telegram/API → MessageGateway → ConversationEvent                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR                                      │
│  1. Recibe ConversationEvent                                                │
│  2. Obtiene contexto (MemoryService)                                        │
│  3. Clasifica complejidad (simple vs complex)                               │
│  4. Rutea a SingleStepAgent o ReActAgent                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────────┐
│      SINGLE-STEP AGENTS       │   │            ReAct AGENT                │
│                               │   │                                       │
│  DatabaseAgent (SQL directo)  │   │  Loop: THOUGHT → ACTION → OBSERVE     │
│  KnowledgeAgent (búsqueda KB) │   │                                       │
│  ChitchatAgent (conversación) │   │  Para consultas multi-paso            │
└───────────────────────────────┘   └───────────────────────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL REGISTRY                                  │
│  DatabaseTool │ KnowledgeTool │ CalculateTool │ DateTimeTool                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Qué es ReAct

ReAct (Reasoning and Acting) es un paradigma donde el LLM:

1. **Thought**: Razona sobre qué hacer
2. **Action**: Ejecuta una herramienta
3. **Observation**: Observa el resultado
4. **Repeat**: Repite hasta tener la respuesta final

**Ejemplo:**
```
User: "¿Quién vendió más el mes pasado y cuáles fueron sus productos top?"

Thought 1: Necesito encontrar el mejor vendedor del mes pasado.
Action 1: database_query("SELECT vendedor_id, SUM(total) as ventas FROM ventas WHERE fecha >= '2024-01-01' GROUP BY vendedor_id ORDER BY ventas DESC LIMIT 1")
Observation 1: [{"vendedor_id": 42, "ventas": 150000}]

Thought 2: Ahora necesito los productos más vendidos por el vendedor 42.
Action 2: database_query("SELECT producto, COUNT(*) as cantidad FROM ventas WHERE vendedor_id = 42 GROUP BY producto ORDER BY cantidad DESC LIMIT 5")
Observation 2: [{"producto": "Laptop Pro", "cantidad": 45}, ...]

Thought 3: Tengo toda la información necesaria.
Action 3: finish({"answer": "El mejor vendedor generó $150,000. Sus productos top fueron Laptop Pro (45 unidades)..."})
```

### Cuándo usar cada enfoque

| Escenario | Agente | Por qué |
|-----------|--------|---------|
| "¿Cuántas ventas hubo ayer?" | DatabaseAgent | Una sola consulta |
| "¿Qué es la política de devoluciones?" | KnowledgeAgent | Búsqueda simple |
| "Hola, ¿cómo estás?" | ChitchatAgent | Conversación casual |
| "Compara ventas de enero vs febrero" | **ReActAgent** | Requiere múltiples pasos |

---

## Estructura de Archivos

```
src/
├── agents/
│   ├── __init__.py
│   ├── base/
│   │   ├── __init__.py
│   │   ├── agent.py              # BaseAgent, AgentResponse
│   │   ├── events.py             # ConversationEvent, UserContext
│   │   └── exceptions.py         # AgentException, ToolException
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # AgentOrchestrator
│   │   ├── complexity_classifier.py
│   │   └── router.py
│   │
│   ├── react/
│   │   ├── __init__.py
│   │   ├── agent.py              # ReActAgent
│   │   ├── scratchpad.py
│   │   ├── prompts.py
│   │   └── schemas.py            # ReActStep, ReActResponse
│   │
│   ├── single_step/
│   │   ├── __init__.py
│   │   ├── database_agent.py
│   │   ├── knowledge_agent.py
│   │   └── chitchat_agent.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── base.py               # BaseTool, ToolResult
│       ├── registry.py           # ToolRegistry
│       ├── database_tool.py
│       ├── knowledge_tool.py
│       └── calculate_tool.py
│
├── events/
│   ├── __init__.py
│   └── bus.py                    # EventBus pub/sub
│
└── gateway/
    └── message_gateway.py        # Normaliza input
```

---

## Fase 1: Foundation

**Objetivo**: Establecer contratos base, EventBus y estructura de carpetas
**Rama**: `feature/react-fase1-foundation`
**Dependencias**: Ninguna

### Tareas

- [x] **Crear estructura de carpetas** - Directorios para nueva arquitectura
  - Carpeta: `plan/`
  - Commit: `c4d1b0c`
  - Completado: 2024-02-13

- [x] **Documentar plan de migración** - Archivos de plan y arquitectura
  - Archivos: `plan/*.md`
  - Commit: `c4d1b0c`
  - Completado: 2024-02-13

- [ ] **Crear carpeta src/agents/** - Estructura base de agentes
  - Carpetas: `base/`, `orchestrator/`, `react/`, `single_step/`, `tools/`

- [ ] **Implementar BaseAgent** - Clase abstracta base para todos los agentes
  - Archivo: `src/agents/base/agent.py`
  - Incluye: `name`, `agent_type`, `execute()` abstracto

- [ ] **Implementar AgentResponse** - Modelo Pydantic de respuesta estándar
  - Archivo: `src/agents/base/agent.py`
  - Campos: `success`, `message`, `data`, `error`, `agent_name`, `execution_time_ms`

- [ ] **Implementar UserContext** - Contexto de usuario para agentes
  - Archivo: `src/agents/base/events.py`
  - Campos: `user_id`, `display_name`, `roles`, `working_memory`, `long_term_summary`

- [ ] **Implementar ConversationEvent** - Evento normalizado de entrada
  - Archivo: `src/agents/base/events.py`
  - Campos: `event_id`, `user_id`, `channel`, `text`, `timestamp`, `correlation_id`

- [ ] **Implementar EventBus simple** - Pub/Sub en memoria
  - Archivo: `src/events/bus.py`
  - Métodos: `subscribe()`, `publish()`, `unsubscribe()`

- [ ] **Implementar excepciones base** - Excepciones específicas de agentes
  - Archivo: `src/agents/base/exceptions.py`
  - Clases: `AgentException`, `ToolException`, `ValidationException`

- [ ] **Tests para contratos base** - Tests unitarios de Fase 1
  - Archivo: `tests/agents/test_base.py`
  - Cobertura: BaseAgent, AgentResponse, UserContext, EventBus

### Código de Referencia

```python
# src/agents/base/agent.py
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from enum import Enum

class AgentType(str, Enum):
    SINGLE_STEP = "single_step"
    REACT = "react"

class AgentResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    agent_name: str
    agent_type: AgentType
    execution_time_ms: float = 0
    steps_taken: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success_response(cls, agent_name: str, message: str, **kwargs) -> "AgentResponse":
        return cls(success=True, message=message, agent_name=agent_name, **kwargs)

    @classmethod
    def error_response(cls, agent_name: str, error: str, **kwargs) -> "AgentResponse":
        return cls(success=False, error=error, agent_name=agent_name, **kwargs)

class BaseAgent(ABC):
    name: str
    agent_type: AgentType

    @abstractmethod
    async def execute(self, query: str, context: "UserContext", **kwargs) -> AgentResponse:
        pass

    async def health_check(self) -> bool:
        return True
```

```python
# src/agents/base/events.py
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import uuid4

class ConversationEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    channel: str  # telegram, api, websocket
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

class UserContext(BaseModel):
    user_id: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    working_memory: list[dict] = Field(default_factory=list)
    long_term_summary: Optional[str] = None
    current_date: datetime = Field(default_factory=datetime.utcnow)
```

```python
# src/events/bus.py
from typing import Callable, Awaitable
from collections import defaultdict
import asyncio

EventHandler = Callable[..., Awaitable[None]]

class EventBus:
    _instance: Optional["EventBus"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = defaultdict(list)
        return cls._instance

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        self._handlers[event_type].remove(handler)

    async def publish(self, event_type: str, event: dict):
        handlers = self._handlers.get(event_type, [])
        if handlers:
            await asyncio.gather(
                *[handler(event) for handler in handlers],
                return_exceptions=True
            )

event_bus = EventBus()
```

### Entregables
- [ ] `src/agents/base/` con todos los contratos
- [ ] `src/events/bus.py` funcionando
- [ ] Tests pasando con cobertura >80%

---

## Fase 2: Tools

**Objetivo**: Implementar sistema de Tools compatible con ReAct
**Rama**: `feature/react-fase2-tools`
**Dependencias**: Fase 1

### Tareas

- [ ] **Implementar ToolDefinition** - Metadata del tool para prompts
  - Archivo: `src/agents/tools/base.py`
  - Campos: `name`, `description`, `category`, `parameters`, `examples`

- [ ] **Implementar ToolParameter** - Definición de parámetros
  - Archivo: `src/agents/tools/base.py`
  - Validación: tipo, required, min/max

- [ ] **Implementar ToolResult** - Resultado de ejecución
  - Archivo: `src/agents/tools/base.py`
  - Método: `to_observation()` para ReAct

- [ ] **Implementar BaseTool** - Clase abstracta para ReAct tools
  - Archivo: `src/agents/tools/base.py`
  - Métodos: `definition`, `execute()`, `validate_params()`

- [ ] **Implementar ToolRegistry** - Registro singleton
  - Archivo: `src/agents/tools/registry.py`
  - Método: `get_tools_prompt()` para generar descripción de tools

- [ ] **Implementar DatabaseTool** - Ejecución de queries SQL
  - Archivo: `src/agents/tools/database_tool.py`
  - Usa: SQLValidator existente

- [ ] **Implementar KnowledgeTool** - Búsqueda en knowledge base
  - Archivo: `src/agents/tools/knowledge_tool.py`
  - Usa: KnowledgeManager existente

- [ ] **Implementar CalculateTool** - Cálculos matemáticos seguros
  - Archivo: `src/agents/tools/calculate_tool.py`
  - Evaluador seguro sin `eval()`

### Código de Referencia

```python
# src/agents/tools/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Optional
from enum import Enum

class ToolCategory(str, Enum):
    DATABASE = "database"
    KNOWLEDGE = "knowledge"
    CALCULATION = "calculation"
    DATETIME = "datetime"

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    examples: list[dict[str, Any]] = Field(default_factory=list)

    def to_prompt_format(self) -> str:
        params = ", ".join([f"{p.name}: {p.type}" for p in self.parameters])
        return f"- {self.name}: {self.description}\n  Parameters: {{{params}}}"

class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0

    def to_observation(self) -> str:
        if not self.success:
            return f"Error: {self.error}"
        if isinstance(self.data, list) and len(self.data) == 0:
            return "No results found"
        return str(self.data)

class BaseTool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

    def validate_params(self, params: dict) -> tuple[bool, Optional[str]]:
        for param in self.definition.parameters:
            if param.required and param.name not in params:
                return False, f"Missing required parameter: {param.name}"
        return True, None
```

### Entregables
- [ ] `src/agents/tools/` con todos los tools
- [ ] Tests para cada tool

---

## Fase 3: ReAct Core

**Objetivo**: Implementar el agente ReAct con loop de razonamiento
**Rama**: `feature/react-fase3-core`
**Dependencias**: Fase 1, Fase 2

### Tareas

- [ ] **Implementar ReActStep** - Modelo de un paso del loop
  - Archivo: `src/agents/react/schemas.py`
  - Campos: `step_number`, `thought`, `action`, `action_input`, `observation`

- [ ] **Implementar ReActResponse** - Respuesta del LLM en cada iteración
  - Archivo: `src/agents/react/schemas.py`
  - Campos: `thought`, `action`, `action_input`, `final_answer`

- [ ] **Implementar ActionType** - Enum de acciones disponibles
  - Archivo: `src/agents/react/schemas.py`
  - Valores: `DATABASE_QUERY`, `KNOWLEDGE_SEARCH`, `CALCULATE`, `FINISH`

- [ ] **Implementar Scratchpad** - Historial de pasos
  - Archivo: `src/agents/react/scratchpad.py`
  - Métodos: `add_step()`, `to_prompt_format()`, `is_full()`

- [ ] **Implementar ReActAgent** - Agente principal
  - Archivo: `src/agents/react/agent.py`
  - Método: `execute()` con loop Think-Act-Observe

- [ ] **Implementar prompts ReAct** - Templates para el loop
  - Archivo: `src/agents/react/prompts.py`

- [ ] **Implementar _generate_step()** - Generar siguiente paso
  - Usa: LLM con structured output (Pydantic)

- [ ] **Implementar _execute_tool()** - Ejecutar tool y obtener observación
  - Integra: ToolRegistry

- [ ] **Implementar _synthesize_partial()** - Respuesta si se exceden iteraciones

- [ ] **Tests de integración ReAct** - Tests del loop completo
  - Archivo: `tests/agents/test_react.py`

### Código de Referencia

```python
# src/agents/react/agent.py
class ReActAgent(BaseAgent):
    name = "react"
    agent_type = AgentType.REACT
    MAX_ITERATIONS = 10

    def __init__(self, llm: LLMGateway, tool_registry: ToolRegistry):
        self.llm = llm
        self.tools = tool_registry

    async def execute(self, query: str, context: UserContext, **kwargs) -> AgentResponse:
        scratchpad = Scratchpad(max_steps=self.MAX_ITERATIONS)

        while not scratchpad.is_full():
            response = await self._generate_step(query, context, scratchpad)

            if response.action == ActionType.FINISH:
                return AgentResponse.success_response(
                    agent_name=self.name,
                    message=response.final_answer,
                    agent_type=self.agent_type,
                    steps_taken=len(scratchpad.steps) + 1
                )

            observation = await self._execute_tool(response.action, response.action_input)
            scratchpad.add_step(
                thought=response.thought,
                action=response.action,
                action_input=response.action_input,
                observation=observation
            )

        return AgentResponse.success_response(
            agent_name=self.name,
            message=await self._synthesize_partial(query, scratchpad),
            metadata={"partial": True}
        )
```

### Entregables
- [ ] `src/agents/react/` completo
- [ ] ReActAgent funcionando con tools
- [ ] Tests de integración pasando

---

## Fase 4: Single-Step Agents

**Objetivo**: Extraer lógica a agentes especializados de un solo paso
**Rama**: `feature/react-fase4-single-step-agents`
**Dependencias**: Fase 1

### Tareas

- [ ] **Implementar DatabaseAgent** - Consultas SQL directas
  - Archivo: `src/agents/single_step/database_agent.py`
  - Pipeline: generate → validate → execute → format

- [ ] **Implementar KnowledgeAgent** - Búsqueda en KB
  - Archivo: `src/agents/single_step/knowledge_agent.py`
  - Usa: KnowledgeManager existente

- [ ] **Implementar ChitchatAgent** - Conversación casual
  - Archivo: `src/agents/single_step/chitchat_agent.py`
  - Maneja: saludos, despedidas, preguntas sobre el bot

- [ ] **Implementar MemoryAgent** - Gestión de memoria
  - Archivo: `src/agents/single_step/memory_agent.py`
  - Métodos: `get_context()`, `record()`, `update_summary()`

- [ ] **Extraer lógica de LLMAgent** - Mover a agentes especializados
  - Refactor: Mantener LLMAgent como adapter temporal

- [ ] **Tests unitarios por agente**
  - Archivos: `tests/agents/test_database_agent.py`, etc.

- [ ] **Tests de integración**
  - Archivo: `tests/agents/test_single_step_integration.py`

- [ ] **Documentar patrones** - Cómo crear nuevos agentes

### Entregables
- [ ] `src/agents/single_step/` con 4 agentes
- [ ] LLMAgent delegando a nuevos agentes
- [ ] Tests completos

---

## Fase 5: Orchestrator

**Objetivo**: Implementar orquestador que decide qué agente usar
**Rama**: `feature/react-fase5-orchestrator`
**Dependencias**: Fase 3, Fase 4

### Tareas

- [ ] **Implementar ComplexityClassifier** - Determina simple vs complex
  - Archivo: `src/agents/orchestrator/complexity_classifier.py`
  - Heurísticas + LLM opcional

- [ ] **Implementar AgentOrchestrator** - Orquestador principal
  - Archivo: `src/agents/orchestrator/orchestrator.py`
  - Flujo: classify → route → execute → record

- [ ] **Implementar router** - Mapeo de intención a agente
  - Archivo: `src/agents/orchestrator/router.py`

- [ ] **Integrar con MemoryAgent** - Contexto automático

- [ ] **Tests de orquestación** - Routing correcto
  - Archivo: `tests/agents/test_orchestrator.py`

- [ ] **Métricas de routing** - Logging de decisiones

### Código de Referencia

```python
# src/agents/orchestrator/orchestrator.py
class AgentOrchestrator:
    def __init__(self, llm, memory_service, agents: dict[str, BaseAgent]):
        self.llm = llm
        self.memory = memory_service
        self.classifier = ComplexityClassifier(llm)
        self.agents = agents

    async def handle(self, event: ConversationEvent) -> AgentResponse:
        context = await self.memory.get_context(event.user_id)
        complexity = await self.classifier.classify(event.text)

        agent = self.agents.get(complexity.suggested_agent)
        response = await agent.execute(query=event.text, context=context)

        asyncio.create_task(self.memory.record_interaction(event, response))
        return response
```

### Entregables
- [ ] `src/agents/orchestrator/` completo
- [ ] Routing funcionando correctamente
- [ ] Métricas de decisiones

---

## Fase 6: Integration

**Objetivo**: Conectar nueva arquitectura con Telegram y sistema actual
**Rama**: `feature/react-fase6-integration`
**Dependencias**: Fase 5

### Tareas

- [ ] **Implementar MessageGateway** - Normaliza input de Telegram
  - Archivo: `src/gateway/message_gateway.py`
  - Método: `handle_telegram()` → `ConversationEvent`

- [ ] **Actualizar QueryHandler** - Usar AgentOrchestrator
  - Modificar: `src/bot/handlers/query_handlers.py`
  - Feature flag para rollback

- [ ] **Actualizar ToolsHandler** - Delegar a orquestador
  - Modificar: `src/bot/handlers/tools_handlers.py`

- [ ] **Implementar feature flag** - Toggle entre arquitecturas
  - Config: `USE_REACT_ARCHITECTURE=true/false`

- [ ] **LLMAgent como fallback** - Si nuevo sistema falla

- [ ] **Tests E2E** - Flujo completo Telegram → Respuesta
  - Archivo: `tests/e2e/test_telegram_flow.py`

- [ ] **Comparar métricas** - Latencia, precisión

- [ ] **Documentar rollback** - Procedimiento de emergencia

### Entregables
- [ ] Handlers actualizados
- [ ] Feature flag funcionando
- [ ] Tests E2E pasando
- [ ] Plan de rollback documentado

---

## Fase 7: Polish

**Objetivo**: Observabilidad, documentación y optimización
**Rama**: `feature/react-fase7-polish`
**Dependencias**: Fase 6

### Tareas

- [ ] **Implementar tracing** - OpenTelemetry básico
  - Archivo: `src/observability/tracing.py`

- [ ] **Implementar métricas** - Prometheus/básicas
  - Archivo: `src/observability/metrics.py`

- [ ] **Structured logging** - Logs JSON
  - Archivo: `src/observability/logging.py`

- [ ] **Actualizar documentación** - Contexto y skills

- [ ] **Optimización de prompts** - Reducir tokens

- [ ] **Performance tuning** - Cachés, connection pools

### Entregables
- [ ] Observabilidad completa
- [ ] Documentación actualizada
- [ ] Sistema listo para producción

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| ReAct loops infinitos | Media | Alto | MAX_ITERATIONS=10, timeout global |
| Regresión en clasificación | Media | Alto | Tests A/B, feature flag |
| Aumento de latencia | Media | Medio | Profiling, caché agresivo |
| Costos LLM elevados | Baja | Medio | ComplexityClassifier reduce uso de ReAct |

---

## Criterios de Éxito

- [ ] Latencia p95 <= latencia actual + 10%
- [ ] Precisión de clasificación >= 95%
- [ ] Cobertura de tests >= 80%
- [ ] Zero regresiones en funcionalidad actual
- [ ] Código en LLMAgent reducido a < 100 líneas (solo adapter)

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2024-02-13 | Creación del plan | Claude |
| 2024-02-13 | Consolidación de documentos | Claude |
