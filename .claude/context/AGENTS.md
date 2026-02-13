# Agentes LLM

## Estado Actual

### LLMAgent (Orquestador Principal)

**Archivo**: `src/agent/llm_agent.py`
**Líneas**: ~544
**Estado**: LEGACY - En proceso de migración a ReAct

```python
class LLMAgent:
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm_provider: str = "openai",
        model: str = "gpt-4"
    )

    async def process_query(
        self,
        user_id: int,
        query: str
    ) -> str
```

**Componentes internos**:
- `llm_provider`: OpenAIProvider | AnthropicProvider
- `query_classifier`: QueryClassifier
- `sql_generator`: SQLGenerator
- `sql_validator`: SQLValidator
- `response_formatter`: ResponseFormatter
- `memory_manager`: MemoryManager
- `conversation_history`: ConversationHistory
- `prompt_manager`: PromptManager

**Flujo de process_query()**:
```
1. conversation_history.add_message(query)
2. memory_context = memory_manager.get_memory_context()
3. classification = query_classifier.classify(query)
   │
   ├─ DATABASE
   │  ├── sql = sql_generator.generate(query)
   │  ├── sql_validator.validate(sql)
   │  ├── results = db_manager.execute_query(sql)
   │  └── response = response_formatter.format(results)
   │
   ├─ KNOWLEDGE
   │  ├── context = query_classifier.get_knowledge_context()
   │  └── response = llm.generate(prompt + context)
   │
   └─ GENERAL
      └── response = llm.generate(prompt) | saludo dinámico
   │
4. memory_manager.record_interaction() [async]
5. conversation_history.add_response(response)
6. return response
```

---

## Clasificación de Queries

### QueryClassifier

**Archivo**: `src/agent/classifiers/query_classifier.py`

```python
class QueryType(Enum):
    DATABASE = "database"    # Requiere SQL
    KNOWLEDGE = "knowledge"  # Buscar en KB
    GENERAL = "general"      # Conversación general

class QueryClassifier:
    async def classify(self, query: str, context: str = "") -> QueryType
    def get_knowledge_context(self) -> str  # Cached
```

**Lógica de clasificación**:
1. Busca en KnowledgeManager si hay entradas relevantes
2. Si hay match con score alto → KNOWLEDGE
3. Si parece query de datos (ventas, usuarios, etc.) → DATABASE
4. Si es saludo, despedida, pregunta sobre el bot → GENERAL

---

## Generación SQL

### SQLGenerator

**Archivo**: `src/agent/sql/sql_generator.py`

```python
class SQLGenerator:
    async def generate_sql(
        self,
        query: str,
        schema: dict = None
    ) -> str
```

**Prompt incluye**:
- Schema de la BD (tablas, columnas, tipos)
- Ejemplos few-shot
- Restricciones (solo SELECT)

### SQLValidator

**Archivo**: `src/agent/sql/sql_validator.py`

```python
class SQLValidator:
    def validate(self, sql: str) -> ValidationResult
    # Solo SELECT, EXEC, WITH
    # Rechaza modificaciones y injection
```

---

## Formateo de Respuestas

### ResponseFormatter

**Archivo**: `src/agent/formatters/response_formatter.py`

```python
class ResponseFormatter:
    async def format_query_results(
        self,
        query: str,
        results: list[dict],
        use_natural_language: bool = True
    ) -> str
```

**Modos**:
- `use_natural_language=True`: LLM convierte resultados a texto
- `use_natural_language=False`: Formato estructurado/tabla

---

## Proveedores LLM

### OpenAIProvider

**Archivo**: `src/agent/providers/openai_provider.py`

```python
class OpenAIProvider(LLMProvider):
    async def generate(self, prompt: str, max_tokens: int = 1000) -> str
    async def generate_structured(self, prompt: str, schema: Type[BaseModel]) -> T
```

### AnthropicProvider

**Archivo**: `src/agent/providers/anthropic_provider.py`

```python
class AnthropicProvider(LLMProvider):
    async def generate(self, prompt: str, max_tokens: int = 1000) -> str
    async def generate_structured(self, prompt: str, schema: Type[BaseModel]) -> T
```

---

## Arquitectura Futura: ReAct

### Estructura Planificada

```
src/agents/
├── base/
│   ├── agent.py           # BaseAgent, AgentResponse
│   ├── events.py          # ConversationEvent, UserContext
│   └── exceptions.py
│
├── orchestrator/
│   ├── orchestrator.py    # AgentOrchestrator
│   ├── complexity_classifier.py  # simple vs complex
│   └── router.py          # Ruteo a agentes
│
├── react/
│   ├── agent.py           # ReActAgent
│   ├── loop.py            # Think-Act-Observe loop
│   ├── scratchpad.py      # Historial de pasos
│   └── schemas.py         # ReActStep, ReActResponse
│
├── single_step/
│   ├── database_agent.py  # Solo queries BD
│   ├── knowledge_agent.py # Solo knowledge base
│   └── chitchat_agent.py  # Solo conversación
│
└── tools/
    ├── base.py            # BaseTool nuevo
    ├── registry.py        # ToolRegistry nuevo
    ├── database_tool.py
    ├── knowledge_tool.py
    └── calculate_tool.py
```

### Contratos Base

```python
class AgentType(str, Enum):
    SINGLE_STEP = "single_step"
    REACT = "react"

class AgentResponse(BaseModel):
    success: bool
    message: Optional[str]
    data: Optional[dict]
    error: Optional[str]
    agent_name: str
    agent_type: AgentType
    execution_time_ms: float
    steps_taken: int = 1

class UserContext(BaseModel):
    user_id: str
    display_name: str
    roles: list[str]
    preferences: dict
    working_memory: list[dict]
    long_term_summary: Optional[str]

class BaseAgent(ABC):
    name: str
    agent_type: AgentType

    @abstractmethod
    async def execute(
        self,
        query: str,
        context: UserContext
    ) -> AgentResponse
```

### ReAct Loop

```python
# Pseudocódigo
async def react_loop(query, context):
    scratchpad = []

    while len(scratchpad) < MAX_ITERATIONS:
        # THOUGHT: ¿Qué necesito hacer?
        # ACTION: Seleccionar tool
        response = await llm.generate_structured(prompt, ReActResponse)

        if response.action == "finish":
            return response.final_answer

        # OBSERVE: Ejecutar y ver resultado
        observation = await execute_tool(response.action)
        scratchpad.append(step)

    return synthesize_partial(scratchpad)
```

---

## Ramas de Migración

```
feature/react-agent-migration
├── feature/react-fase1-foundation     # BaseAgent, EventBus
├── feature/react-fase2-tools          # Tool System nuevo
├── feature/react-fase3-core           # ReActAgent, Scratchpad
├── feature/react-fase4-single-step-agents
├── feature/react-fase5-orchestrator
├── feature/react-fase6-integration
└── feature/react-fase7-polish
```

Ver `plan/IMPLEMENTACION_REACT_AGENT.md` para detalles completos.
