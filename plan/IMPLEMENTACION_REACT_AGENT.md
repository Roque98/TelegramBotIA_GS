# Plan de Implementación: ReAct Agent

## Objetivo

Implementar un sistema de agentes basado en el paradigma **ReAct (Reasoning + Acting)** que permita:
- Razonamiento paso a paso visible
- Ejecución de múltiples herramientas en secuencia
- Auto-corrección basada en observaciones
- Manejo de consultas complejas que requieren múltiples pasos

---

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRADA                                        │
│                                                                             │
│  Telegram/API → MessageNormalizer → ConversationEvent                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATOR                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        AgentOrchestrator                             │   │
│  │                                                                      │   │
│  │  1. Recibe ConversationEvent                                         │   │
│  │  2. Obtiene contexto (MemoryService)                                 │   │
│  │  3. Clasifica complejidad (simple vs complex)                        │   │
│  │  4. Rutea a SingleStepAgent o ReActAgent                             │   │
│  │  5. Retorna respuesta                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────────┐
│      SINGLE-STEP AGENTS       │   │            ReAct AGENT                │
│                               │   │                                       │
│  ┌─────────────────────────┐  │   │  ┌─────────────────────────────────┐ │
│  │ DatabaseAgent           │  │   │  │         ReAct Loop              │ │
│  │ - Genera SQL            │  │   │  │                                 │ │
│  │ - Ejecuta               │  │   │  │  ┌─────────┐                    │ │
│  │ - Formatea              │  │   │  │  │ THOUGHT │ ← Razona           │ │
│  └─────────────────────────┘  │   │  │  └────┬────┘                    │ │
│                               │   │  │       │                         │ │
│  ┌─────────────────────────┐  │   │  │       ▼                         │ │
│  │ KnowledgeAgent          │  │   │  │  ┌─────────┐                    │ │
│  │ - Busca en KB           │  │   │  │  │ ACTION  │ ← Ejecuta tool     │ │
│  │ - Genera respuesta      │  │   │  │  └────┬────┘                    │ │
│  └─────────────────────────┘  │   │  │       │                         │ │
│                               │   │  │       ▼                         │ │
│  ┌─────────────────────────┐  │   │  │  ┌─────────┐                    │ │
│  │ ChitchatAgent           │  │   │  │  │OBSERVE  │ ← Ve resultado     │ │
│  │ - Conversación casual   │  │   │  │  └────┬────┘                    │ │
│  └─────────────────────────┘  │   │  │       │                         │ │
│                               │   │  │       ▼                         │ │
│                               │   │  │  ¿Suficiente? ──No──→ [REPEAT]  │ │
│                               │   │  │       │                         │ │
│                               │   │  │      Yes                        │ │
│                               │   │  │       ▼                         │ │
│                               │   │  │  ┌─────────┐                    │ │
│                               │   │  │  │ ANSWER  │ ← Respuesta final  │ │
│                               │   │  │  └─────────┘                    │ │
│                               │   │  └─────────────────────────────────┘ │
└───────────────────────────────┘   └───────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TOOL REGISTRY                                  │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ DatabaseTool │ │KnowledgeTool │ │ CalculateTool│ │  CustomTools │       │
│  │              │ │              │ │              │ │              │       │
│  │ execute_sql  │ │ search_kb    │ │ evaluate     │ │ ...          │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SHARED SERVICES                                   │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ LLMGateway  │  │MemoryService│  │  DBService  │  │ EventLogger │        │
│  │             │  │             │  │             │  │             │        │
│  │ - OpenAI    │  │ - Working   │  │ - Pool      │  │ - Tracing   │        │
│  │ - Anthropic │  │ - Long-term │  │ - Schema    │  │ - Metrics   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
│   │   ├── orchestrator.py       # AgentOrchestrator principal
│   │   ├── complexity_classifier.py  # Determina simple vs complex
│   │   └── router.py             # Rutea a agente correcto
│   │
│   ├── react/
│   │   ├── __init__.py
│   │   ├── agent.py              # ReActAgent principal
│   │   ├── loop.py               # ReActLoop (think-act-observe)
│   │   ├── scratchpad.py         # Manejo del scratchpad
│   │   ├── prompts.py            # Prompts para ReAct
│   │   └── schemas.py            # ReActStep, ReActResponse
│   │
│   ├── single_step/
│   │   ├── __init__.py
│   │   ├── database_agent.py     # Consultas SQL directas
│   │   ├── knowledge_agent.py    # Búsqueda en KB
│   │   └── chitchat_agent.py     # Conversación casual
│   │
│   └── tools/
│       ├── __init__.py
│       ├── base.py               # BaseTool, ToolResult
│       ├── registry.py           # ToolRegistry singleton
│       ├── database_tool.py      # Ejecución SQL
│       ├── knowledge_tool.py     # Búsqueda KB
│       ├── calculate_tool.py     # Cálculos matemáticos
│       └── datetime_tool.py      # Operaciones con fechas
│
├── services/
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gateway.py            # LLMGateway con retry/fallback
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── openai.py
│   │   │   └── anthropic.py
│   │   └── rate_limiter.py
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── service.py            # MemoryService
│   │   ├── working_memory.py
│   │   └── long_term_memory.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── service.py            # DatabaseService
│   │   ├── schema_provider.py    # Obtiene schema para prompts
│   │   └── sql_validator.py
│   │
│   └── observability/
│       ├── __init__.py
│       ├── logger.py             # Structured logging
│       ├── tracer.py             # OpenTelemetry
│       └── metrics.py            # Prometheus metrics
│
└── config/
    ├── __init__.py
    ├── settings.py               # Pydantic settings
    └── prompts/
        ├── react/
        │   ├── system.yaml
        │   └── step.yaml
        └── single_step/
            ├── database.yaml
            └── knowledge.yaml
```

---

## Componentes Detallados

### 1. Contratos Base

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
    """Respuesta estándar de cualquier agente"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    agent_name: str
    agent_type: AgentType
    execution_time_ms: float = 0
    steps_taken: int = 1  # Para ReAct, número de iteraciones
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success_response(
        cls,
        agent_name: str,
        message: str,
        agent_type: AgentType = AgentType.SINGLE_STEP,
        **kwargs
    ) -> "AgentResponse":
        return cls(
            success=True,
            message=message,
            agent_name=agent_name,
            agent_type=agent_type,
            **kwargs
        )

    @classmethod
    def error_response(
        cls,
        agent_name: str,
        error: str,
        agent_type: AgentType = AgentType.SINGLE_STEP,
        **kwargs
    ) -> "AgentResponse":
        return cls(
            success=False,
            error=error,
            agent_name=agent_name,
            agent_type=agent_type,
            **kwargs
        )


class BaseAgent(ABC):
    """Contrato base para todos los agentes"""

    name: str
    agent_type: AgentType

    @abstractmethod
    async def execute(
        self,
        query: str,
        context: "UserContext",
        **kwargs
    ) -> AgentResponse:
        """Ejecuta la lógica del agente"""
        pass

    async def health_check(self) -> bool:
        """Verifica que el agente esté funcionando"""
        return True


# src/agents/base/events.py
class ConversationEvent(BaseModel):
    """Evento normalizado de cualquier canal"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    channel: str  # telegram, api, websocket
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UserContext(BaseModel):
    """Contexto del usuario disponible para todos los agentes"""
    user_id: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    working_memory: list[dict] = Field(default_factory=list)
    long_term_summary: Optional[str] = None
    current_date: datetime = Field(default_factory=datetime.utcnow)
```

---

### 2. Tool System

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
    EXTERNAL = "external"


class ToolParameter(BaseModel):
    """Definición de un parámetro de tool"""
    name: str
    type: str  # string, integer, float, boolean
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Definición completa de un tool para el LLM"""
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    examples: list[dict[str, Any]] = Field(default_factory=list)

    def to_prompt_format(self) -> str:
        """Genera descripción del tool para incluir en prompts"""
        params_desc = ", ".join([
            f"{p.name}: {p.type}" + (" (required)" if p.required else " (optional)")
            for p in self.parameters
        ])
        return f"- {self.name}: {self.description}\n  Parameters: {{{params_desc}}}"


class ToolResult(BaseModel):
    """Resultado de ejecución de un tool"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_observation(self) -> str:
        """Convierte el resultado a texto para el scratchpad"""
        if not self.success:
            return f"Error: {self.error}"
        if isinstance(self.data, list):
            if len(self.data) == 0:
                return "No results found"
            if len(self.data) > 10:
                return f"{self.data[:10]}... (and {len(self.data)-10} more)"
        return str(self.data)


class BaseTool(ABC):
    """Clase base para todos los tools"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Retorna la definición del tool"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Ejecuta el tool con los parámetros dados"""
        pass

    def validate_params(self, params: dict) -> tuple[bool, Optional[str]]:
        """Valida que los parámetros requeridos estén presentes"""
        for param in self.definition.parameters:
            if param.required and param.name not in params:
                return False, f"Missing required parameter: {param.name}"
        return True, None


# src/agents/tools/registry.py
from typing import Optional

class ToolRegistry:
    """Registro singleton de todos los tools disponibles"""

    _instance: Optional["ToolRegistry"] = None
    _tools: dict[str, BaseTool]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """Registra un tool"""
        self._tools[tool.definition.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Obtiene un tool por nombre"""
        return self._tools.get(name)

    def get_all(self) -> list[BaseTool]:
        """Retorna todos los tools registrados"""
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Retorna tools de una categoría"""
        return [
            tool for tool in self._tools.values()
            if tool.definition.category == category
        ]

    def get_tools_prompt(self) -> str:
        """Genera descripción de todos los tools para prompts"""
        return "\n".join([
            tool.definition.to_prompt_format()
            for tool in self._tools.values()
        ])


# Singleton global
tool_registry = ToolRegistry()
```

---

### 3. Tools Concretos

```python
# src/agents/tools/database_tool.py
from .base import BaseTool, ToolDefinition, ToolParameter, ToolResult, ToolCategory
from ...services.database import DatabaseService, SQLValidator
import time

class DatabaseTool(BaseTool):
    """Tool para ejecutar consultas SQL"""

    def __init__(self, db_service: DatabaseService, validator: SQLValidator):
        self.db = db_service
        self.validator = validator

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="database_query",
            description="Ejecuta una consulta SQL SELECT contra la base de datos. "
                       "Usa esto para obtener información de ventas, productos, clientes, etc.",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Consulta SQL SELECT a ejecutar",
                    required=True
                )
            ],
            examples=[
                {"query": "SELECT COUNT(*) as total FROM ventas WHERE fecha = CURRENT_DATE"},
                {"query": "SELECT nombre, SUM(total) as ventas FROM vendedores GROUP BY nombre ORDER BY ventas DESC LIMIT 5"}
            ]
        )

    async def execute(self, query: str) -> ToolResult:
        start = time.perf_counter()

        # Validar SQL
        validation = self.validator.validate(query)
        if not validation.is_valid:
            return ToolResult(
                success=False,
                error=f"SQL inválido: {validation.reason}",
                execution_time_ms=(time.perf_counter() - start) * 1000
            )

        try:
            rows = await self.db.execute_query(query)
            return ToolResult(
                success=True,
                data=rows,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                metadata={"rows_returned": len(rows)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.perf_counter() - start) * 1000
            )


# src/agents/tools/knowledge_tool.py
class KnowledgeTool(BaseTool):
    """Tool para buscar en la base de conocimiento"""

    def __init__(self, knowledge_service):
        self.knowledge = knowledge_service

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="knowledge_search",
            description="Busca información en la base de conocimiento interna. "
                       "Usa esto para políticas, procedimientos, FAQ, documentación.",
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="search_term",
                    type="string",
                    description="Término o pregunta a buscar",
                    required=True
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Categoría específica (opcional): FAQ, POLITICAS, PROCEDIMIENTOS",
                    required=False
                )
            ]
        )

    async def execute(self, search_term: str, category: str = None) -> ToolResult:
        start = time.perf_counter()

        try:
            results = await self.knowledge.search(
                query=search_term,
                category=category,
                limit=5
            )
            return ToolResult(
                success=True,
                data=[
                    {"title": r.title, "content": r.content, "category": r.category}
                    for r in results
                ],
                execution_time_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.perf_counter() - start) * 1000
            )


# src/agents/tools/calculate_tool.py
import ast
import operator

class CalculateTool(BaseTool):
    """Tool para cálculos matemáticos seguros"""

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculate",
            description="Evalúa expresiones matemáticas. Soporta +, -, *, /, ** (potencia).",
            category=ToolCategory.CALCULATION,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Expresión matemática a evaluar",
                    required=True
                )
            ],
            examples=[
                {"expression": "150000 * 0.15"},
                {"expression": "(45 + 32) / 2"},
                {"expression": "100 ** 2"}
            ]
        )

    async def execute(self, expression: str) -> ToolResult:
        try:
            result = self._safe_eval(expression)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=f"Error evaluando '{expression}': {str(e)}")

    def _safe_eval(self, expression: str) -> float:
        """Evalúa expresión de forma segura sin usar eval()"""
        tree = ast.parse(expression, mode='eval')
        return self._eval_node(tree.body)

    def _eval_node(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.OPERATORS[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            return self.OPERATORS[type(node.op)](operand)
        else:
            raise ValueError(f"Operación no soportada: {type(node)}")


# src/agents/tools/datetime_tool.py
from datetime import datetime, timedelta

class DateTimeTool(BaseTool):
    """Tool para operaciones con fechas"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="datetime",
            description="Obtiene fechas y realiza cálculos de tiempo. "
                       "Útil para 'ayer', 'mes pasado', 'hace 7 días', etc.",
            category=ToolCategory.DATETIME,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operación: 'today', 'yesterday', 'days_ago', 'start_of_month', 'end_of_month'",
                    required=True
                ),
                ToolParameter(
                    name="value",
                    type="integer",
                    description="Valor numérico (para 'days_ago', 'months_ago')",
                    required=False
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Formato de salida (default: YYYY-MM-DD)",
                    required=False,
                    default="%Y-%m-%d"
                )
            ]
        )

    async def execute(
        self,
        operation: str,
        value: int = None,
        format: str = "%Y-%m-%d"
    ) -> ToolResult:
        try:
            today = datetime.now()
            result_date = None

            if operation == "today":
                result_date = today
            elif operation == "yesterday":
                result_date = today - timedelta(days=1)
            elif operation == "days_ago":
                result_date = today - timedelta(days=value or 0)
            elif operation == "start_of_month":
                result_date = today.replace(day=1)
            elif operation == "end_of_month":
                next_month = today.replace(day=28) + timedelta(days=4)
                result_date = next_month - timedelta(days=next_month.day)
            elif operation == "start_of_last_month":
                first_of_this = today.replace(day=1)
                last_month = first_of_this - timedelta(days=1)
                result_date = last_month.replace(day=1)
            elif operation == "end_of_last_month":
                result_date = today.replace(day=1) - timedelta(days=1)
            else:
                return ToolResult(success=False, error=f"Operación desconocida: {operation}")

            return ToolResult(
                success=True,
                data=result_date.strftime(format)
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

---

### 4. ReAct Agent Core

```python
# src/agents/react/schemas.py
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from enum import Enum

class ActionType(str, Enum):
    DATABASE_QUERY = "database_query"
    KNOWLEDGE_SEARCH = "knowledge_search"
    CALCULATE = "calculate"
    DATETIME = "datetime"
    FINISH = "finish"


class ReActStep(BaseModel):
    """Un paso en el scratchpad"""
    step_number: int
    thought: str
    action: ActionType
    action_input: dict[str, Any]
    observation: Optional[str] = None


class ReActResponse(BaseModel):
    """Respuesta del LLM para cada iteración"""
    thought: str = Field(description="Razonamiento sobre qué hacer")
    action: ActionType = Field(description="Acción a tomar")
    action_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Parámetros para la acción"
    )
    final_answer: Optional[str] = Field(
        default=None,
        description="Respuesta final (solo si action=finish)"
    )


# src/agents/react/scratchpad.py
class Scratchpad:
    """Mantiene el historial de pasos del ReAct loop"""

    def __init__(self, max_steps: int = 10):
        self.steps: list[ReActStep] = []
        self.max_steps = max_steps

    def add_step(
        self,
        thought: str,
        action: ActionType,
        action_input: dict,
        observation: str = None
    ) -> ReActStep:
        step = ReActStep(
            step_number=len(self.steps) + 1,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation
        )
        self.steps.append(step)
        return step

    def update_last_observation(self, observation: str):
        if self.steps:
            self.steps[-1].observation = observation

    def is_full(self) -> bool:
        return len(self.steps) >= self.max_steps

    def to_prompt_format(self) -> str:
        if not self.steps:
            return "No previous steps (this is the first iteration)"

        lines = []
        for step in self.steps:
            lines.append(f"""
Step {step.step_number}:
  Thought: {step.thought}
  Action: {step.action.value}
  Action Input: {step.action_input}
  Observation: {step.observation or 'Pending...'}
""")
        return "\n".join(lines)

    def get_observations(self) -> list[str]:
        return [s.observation for s in self.steps if s.observation]


# src/agents/react/agent.py
from ..base import BaseAgent, AgentResponse, AgentType, UserContext
from ..tools import ToolRegistry, tool_registry
from .schemas import ReActResponse, ActionType
from .scratchpad import Scratchpad
from ...services.llm import LLMGateway
import time

class ReActAgent(BaseAgent):
    """
    Agente que implementa el paradigma ReAct.
    Razona paso a paso, ejecuta herramientas, y observa resultados.
    """

    name = "react"
    agent_type = AgentType.REACT

    MAX_ITERATIONS = 10
    TEMPERATURE = 0.2

    def __init__(
        self,
        llm: LLMGateway,
        tool_registry: ToolRegistry = tool_registry
    ):
        self.llm = llm
        self.tools = tool_registry

    async def execute(
        self,
        query: str,
        context: UserContext,
        **kwargs
    ) -> AgentResponse:
        start = time.perf_counter()
        scratchpad = Scratchpad(max_steps=self.MAX_ITERATIONS)

        try:
            while not scratchpad.is_full():
                # 1. Generar siguiente paso
                response = await self._generate_step(query, context, scratchpad)

                # 2. Si es FINISH, retornar respuesta
                if response.action == ActionType.FINISH:
                    elapsed = (time.perf_counter() - start) * 1000
                    return AgentResponse.success_response(
                        agent_name=self.name,
                        message=response.final_answer,
                        agent_type=self.agent_type,
                        execution_time_ms=elapsed,
                        steps_taken=len(scratchpad.steps) + 1,
                        data={"scratchpad": [s.model_dump() for s in scratchpad.steps]}
                    )

                # 3. Ejecutar tool
                observation = await self._execute_tool(
                    response.action,
                    response.action_input
                )

                # 4. Agregar al scratchpad
                scratchpad.add_step(
                    thought=response.thought,
                    action=response.action,
                    action_input=response.action_input,
                    observation=observation
                )

            # Excedimos iteraciones - sintetizar respuesta parcial
            elapsed = (time.perf_counter() - start) * 1000
            partial = await self._synthesize_partial(query, scratchpad)

            return AgentResponse.success_response(
                agent_name=self.name,
                message=partial,
                agent_type=self.agent_type,
                execution_time_ms=elapsed,
                steps_taken=len(scratchpad.steps),
                metadata={"partial": True, "reason": "max_iterations_reached"}
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return AgentResponse.error_response(
                agent_name=self.name,
                error=str(e),
                agent_type=self.agent_type,
                execution_time_ms=elapsed,
                steps_taken=len(scratchpad.steps)
            )

    async def _generate_step(
        self,
        query: str,
        context: UserContext,
        scratchpad: Scratchpad
    ) -> ReActResponse:
        prompt = self._build_prompt(query, context, scratchpad)
        return await self.llm.generate_structured(
            prompt=prompt,
            schema=ReActResponse,
            temperature=self.TEMPERATURE
        )

    async def _execute_tool(
        self,
        action: ActionType,
        action_input: dict
    ) -> str:
        tool = self.tools.get(action.value)
        if not tool:
            return f"Error: Tool '{action.value}' not found"

        result = await tool.execute(**action_input)
        return result.to_observation()

    async def _synthesize_partial(
        self,
        query: str,
        scratchpad: Scratchpad
    ) -> str:
        """Sintetiza respuesta parcial cuando se exceden iteraciones"""
        observations = scratchpad.get_observations()
        prompt = f"""
Based on the following observations gathered while trying to answer the query,
provide the best possible answer:

Query: {query}

Observations:
{chr(10).join(f'- {obs}' for obs in observations)}

Provide a helpful response based on what was learned.
"""
        response = await self.llm.generate(prompt, max_tokens=500)
        return response

    def _build_prompt(
        self,
        query: str,
        context: UserContext,
        scratchpad: Scratchpad
    ) -> str:
        return f"""
You are a helpful assistant that solves queries step by step using available tools.

## Available Tools
{self.tools.get_tools_prompt()}
- finish: Use when you have enough information to provide the final answer.
  Parameters: {{"answer": "Your final answer to the user's query"}}

## User Context
- Name: {context.display_name}
- Roles: {', '.join(context.roles) or 'Standard user'}
- Current date: {context.current_date.strftime('%Y-%m-%d')}
{f'- Relevant history: {context.long_term_summary}' if context.long_term_summary else ''}

## User Query
"{query}"

## Previous Steps (Scratchpad)
{scratchpad.to_prompt_format()}

## Instructions
Generate the next step. Your response must include:
- thought: Your reasoning about what to do next
- action: The tool to use (database_query, knowledge_search, calculate, datetime, or finish)
- action_input: Parameters for the tool
- final_answer: Only if action is "finish", provide the complete answer

Important:
- If you already have enough information, use action="finish"
- Use datetime tool to get correct date values before database queries
- Be concise in your thoughts
- When you finish, provide a natural language answer, not raw data
"""
```

---

### 5. Orchestrator

```python
# src/agents/orchestrator/complexity_classifier.py
from pydantic import BaseModel
from typing import Literal
from ...services.llm import LLMGateway

class ComplexityResult(BaseModel):
    complexity: Literal["simple", "complex"]
    confidence: float
    reasoning: str
    suggested_agent: str


class ComplexityClassifier:
    """Determina si una consulta requiere ReAct o un agente simple"""

    SIMPLE_INDICATORS = [
        "cuánto", "cuántos", "cuántas",  # Queries directas
        "qué es", "cuál es",              # Knowledge simple
        "hola", "gracias", "adiós"        # Chitchat
    ]

    COMPLEX_INDICATORS = [
        "compara", "comparar", "versus",
        "analiza", "análisis",
        "encuentra y luego", "busca y después",
        "top", "mejores", "peores",       # Ranking + detalles
        "tendencia", "evolución",
        "por qué", "explica"
    ]

    def __init__(self, llm: LLMGateway = None):
        self.llm = llm  # Opcional: usar LLM para casos ambiguos

    async def classify(self, query: str) -> ComplexityResult:
        query_lower = query.lower()

        # Heurística rápida
        simple_score = sum(1 for ind in self.SIMPLE_INDICATORS if ind in query_lower)
        complex_score = sum(1 for ind in self.COMPLEX_INDICATORS if ind in query_lower)

        # Múltiples signos de interrogación sugieren complejidad
        if query.count("?") > 1:
            complex_score += 2

        # Palabras que indican secuencia
        if " y " in query_lower and any(verb in query_lower for verb in ["muestra", "lista", "dame"]):
            complex_score += 1

        # Decidir
        if complex_score > simple_score:
            return ComplexityResult(
                complexity="complex",
                confidence=min(0.9, 0.5 + complex_score * 0.1),
                reasoning=f"Complex indicators: {complex_score}, Simple: {simple_score}",
                suggested_agent="react"
            )
        else:
            # Determinar agente simple específico
            agent = self._determine_simple_agent(query_lower)
            return ComplexityResult(
                complexity="simple",
                confidence=min(0.9, 0.5 + simple_score * 0.1),
                reasoning=f"Simple indicators: {simple_score}, Complex: {complex_score}",
                suggested_agent=agent
            )

    def _determine_simple_agent(self, query: str) -> str:
        chitchat_words = ["hola", "gracias", "adiós", "cómo estás", "buenos días"]
        knowledge_words = ["política", "procedimiento", "qué es", "cómo funciona", "regla"]

        if any(word in query for word in chitchat_words):
            return "chitchat"
        if any(word in query for word in knowledge_words):
            return "knowledge"
        return "database"


# src/agents/orchestrator/orchestrator.py
from ..base import BaseAgent, AgentResponse, ConversationEvent, UserContext
from ..react import ReActAgent
from ..single_step import DatabaseAgent, KnowledgeAgent, ChitchatAgent
from .complexity_classifier import ComplexityClassifier
from ...services.memory import MemoryService
from ...services.llm import LLMGateway
import time

class AgentOrchestrator:
    """
    Orquestador principal que:
    1. Recibe eventos
    2. Obtiene contexto
    3. Clasifica complejidad
    4. Rutea al agente apropiado
    """

    def __init__(
        self,
        llm: LLMGateway,
        memory_service: MemoryService,
        database_agent: DatabaseAgent,
        knowledge_agent: KnowledgeAgent,
        chitchat_agent: ChitchatAgent,
        react_agent: ReActAgent
    ):
        self.llm = llm
        self.memory = memory_service
        self.classifier = ComplexityClassifier(llm)

        self.agents = {
            "database": database_agent,
            "knowledge": knowledge_agent,
            "chitchat": chitchat_agent,
            "react": react_agent
        }

    async def handle(self, event: ConversationEvent) -> AgentResponse:
        start = time.perf_counter()

        # 1. Obtener contexto
        context = await self.memory.get_context(event.user_id)

        # 2. Clasificar complejidad
        complexity = await self.classifier.classify(event.text)

        # 3. Obtener agente
        agent = self.agents.get(complexity.suggested_agent)
        if not agent:
            return AgentResponse.error_response(
                agent_name="orchestrator",
                error=f"Agent '{complexity.suggested_agent}' not found"
            )

        # 4. Ejecutar
        response = await agent.execute(
            query=event.text,
            context=context
        )

        # 5. Registrar interacción (async)
        import asyncio
        asyncio.create_task(
            self.memory.record_interaction(event, response)
        )

        # 6. Agregar metadata de orquestación
        response.metadata.update({
            "complexity": complexity.complexity,
            "complexity_confidence": complexity.confidence,
            "routed_to": complexity.suggested_agent,
            "total_time_ms": (time.perf_counter() - start) * 1000
        })

        return response
```

---

## Prompts YAML

```yaml
# src/config/prompts/react/system.yaml
version: "1.0"
name: "react_system"

template: |
  You are a helpful assistant that solves queries step by step using available tools.

  ## Principles
  1. Think before acting - explain your reasoning
  2. Use the minimum number of steps necessary
  3. Verify your assumptions with data
  4. When you have enough information, finish immediately

  ## Available Tools
  {{ tools_description }}

  ## Response Format
  Always respond with:
  - thought: Your reasoning
  - action: Tool to use (or "finish")
  - action_input: Tool parameters
  - final_answer: Only when action is "finish"


# src/config/prompts/react/step.yaml
version: "1.0"
name: "react_step"

template: |
  ## User Context
  - Name: {{ user.display_name }}
  - Roles: {{ user.roles | join(', ') | default('Standard user') }}
  - Date: {{ user.current_date | date('%Y-%m-%d') }}
  {% if user.long_term_summary %}
  - History: {{ user.long_term_summary }}
  {% endif %}

  ## Query
  "{{ query }}"

  ## Previous Steps
  {{ scratchpad }}

  Generate the next step.
```

---

## Plan de Implementación por Fases

### Fase 1: Foundation (3-4 días)
- [ ] Crear estructura de carpetas
- [ ] Implementar `BaseAgent`, `AgentResponse`, `ConversationEvent`
- [ ] Implementar `BaseTool`, `ToolResult`, `ToolRegistry`
- [ ] Tests unitarios para contratos base

### Fase 2: Tools (3-4 días)
- [ ] Implementar `DatabaseTool`
- [ ] Implementar `KnowledgeTool`
- [ ] Implementar `CalculateTool`
- [ ] Implementar `DateTimeTool`
- [ ] Tests para cada tool

### Fase 3: ReAct Core (5-7 días)
- [ ] Implementar `Scratchpad`
- [ ] Implementar `ReActAgent` con loop
- [ ] Implementar prompts YAML
- [ ] Tests de integración ReAct
- [ ] Manejo de errores y edge cases

### Fase 4: Single-Step Agents (3-4 días)
- [ ] Migrar lógica a `DatabaseAgent`
- [ ] Migrar lógica a `KnowledgeAgent`
- [ ] Migrar lógica a `ChitchatAgent`
- [ ] Tests unitarios

### Fase 5: Orchestrator (3-4 días)
- [ ] Implementar `ComplexityClassifier`
- [ ] Implementar `AgentOrchestrator`
- [ ] Integrar con `MemoryService`
- [ ] Tests de integración

### Fase 6: Integration (3-4 días)
- [ ] Conectar con Telegram handlers
- [ ] Conectar con API REST (si existe)
- [ ] Feature flag para rollback
- [ ] Testing E2E

### Fase 7: Polish (2-3 días)
- [ ] Observability (logging, metrics)
- [ ] Documentación
- [ ] Optimización de prompts
- [ ] Performance tuning

---

## Criterios de Éxito

| Métrica | Objetivo |
|---------|----------|
| Latencia p95 (simple) | < 2 segundos |
| Latencia p95 (ReAct) | < 10 segundos |
| Precisión de routing | > 90% |
| Pasos promedio ReAct | < 4 |
| Cobertura de tests | > 80% |
| Errores en producción | < 1% |

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| ReAct loops infinitos | MAX_ITERATIONS = 10, timeout global |
| Latencia alta | Cache de schema, connection pooling |
| Costos LLM elevados | Clasificador de complejidad reduce uso de ReAct |
| Regresiones | Feature flag, tests A/B |
| SQL injection en tools | SQLValidator antes de ejecución |
