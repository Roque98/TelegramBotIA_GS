# Sistema de Tools

## Resumen

| Métrica | Valor |
|---------|-------|
| Tools registrados | 1 |
| Comandos totales | 2 |
| Categorías usadas | 1 (DATABASE) |

---

## Tools Registrados

### QueryTool

```yaml
Nombre: "query"
Versión: "2.0.0"
Descripción: "Consultar base de datos en lenguaje natural"
Categoría: DATABASE

Comandos:
  - /ia
  - /query

Autenticación:
  requires_auth: true
  required_permissions: ["/ia"]

Parámetros:
  - name: query
    type: STRING
    required: true
    min_length: 3
    max_length: 1000
    description: "Consulta en lenguaje natural"

Archivo: src/tools/builtin/query_tool.py
```

**Flujo de ejecución**:
```
QueryTool.execute()
    │
    ▼
context.llm_agent.process_query()
    │
    ├── QueryClassifier → DATABASE | KNOWLEDGE | GENERAL
    │
    ├── Si DATABASE:
    │   ├── SQLGenerator.generate_sql()
    │   ├── SQLValidator.validate()
    │   ├── DatabaseManager.execute_query()
    │   └── ResponseFormatter.format()
    │
    ├── Si KNOWLEDGE:
    │   ├── KnowledgeManager.search()
    │   └── LLM genera respuesta con contexto
    │
    └── Si GENERAL:
        └── LLM responde directamente
```

---

## Estructura del Sistema

### Archivos

```
src/tools/
├── __init__.py              # Exporta API pública
├── tool_base.py             # Clases base
│   ├── ToolCategory (enum)
│   ├── ParameterType (enum)
│   ├── ToolParameter (dataclass)
│   ├── ToolMetadata (dataclass)
│   ├── ToolResult (dataclass)
│   └── BaseTool (abstract)
├── tool_registry.py         # ToolRegistry (singleton)
├── tool_orchestrator.py     # ToolOrchestrator
├── execution_context.py     # ExecutionContext + Builder
└── builtin/
    └── query_tool.py        # QueryTool
```

---

## Enumeraciones

### ToolCategory
```python
DATABASE        = "database"         # Operaciones de BD
SYSTEM          = "system"           # Sistema
USER_MANAGEMENT = "user_management"  # Gestión usuarios
ANALYTICS       = "analytics"        # Análisis
UTILITY         = "utility"          # Utilidades
INTEGRATION     = "integration"      # Integraciones
```

### ParameterType
```python
STRING   = "string"
INTEGER  = "integer"
FLOAT    = "float"
BOOLEAN  = "boolean"
LIST     = "list"
DICT     = "dict"
```

---

## ToolRegistry

**Patrón**: Singleton

```python
from src.tools import get_registry

registry = get_registry()

# Registrar tool
registry.register(MiTool())

# Buscar por nombre
tool = registry.get_tool_by_name("query")

# Buscar por comando
tool = registry.get_tool_by_command("/ia")

# Todos los tools
tools = registry.get_all_tools()

# Por categoría
tools = registry.get_tools_by_category(ToolCategory.DATABASE)

# Estadísticas
stats = registry.get_stats()
# {"total_tools": 1, "total_commands": 2, "categories": {"database": 1}}
```

---

## ToolOrchestrator

**Responsabilidades**:
1. Buscar tool por comando
2. Verificar autenticación
3. Verificar permisos
4. Validar parámetros
5. Ejecutar tool
6. Auditar operación

```python
from src.tools import ToolOrchestrator

orchestrator = ToolOrchestrator()

result = await orchestrator.execute_command(
    user_id=123,
    command="/ia",
    params={"query": "¿Ventas de hoy?"},
    context=execution_context
)

if result.success:
    print(result.data)
else:
    print(result.error)
```

---

## ExecutionContext

**Propósito**: Contenedor de dependencias para tools

```python
from src.tools import ExecutionContextBuilder

context = (
    ExecutionContextBuilder()
    .with_telegram(update, telegram_context)
    .with_db_manager(db_manager)
    .with_llm_agent(llm_agent)
    .with_user_manager(user_manager)
    .with_permission_checker(permission_checker)
    .build()
)

# Acceso a componentes
context.db_manager
context.llm_agent
context.user_manager

# Propiedades proxy al LLMAgent
context.llm_provider
context.query_classifier
context.sql_generator
context.response_formatter

# Datos de Telegram
context.get_user_id()
context.get_chat_id()
context.get_username()

# Validación
is_valid, error = context.validate_required_components('llm_agent', 'db_manager')
```

---

## ToolResult

```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    user_friendly_error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    execution_time_ms: Optional[float] = None
    timestamp: datetime = now()

# Factory methods
ToolResult.success_result(data={"ventas": 45})
ToolResult.error_result(error="SQL inválido", user_friendly_error="No pude procesar tu consulta")
```

---

## Crear Nuevo Tool

```python
# src/tools/builtin/mi_tool.py
from src.tools.tool_base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolCategory, ParameterType
)
from src.tools.execution_context import ExecutionContext

class MiTool(BaseTool):
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mi_tool",
            description="Descripción del tool",
            commands=["/mi_comando"],
            category=ToolCategory.UTILITY,
            requires_auth=True,
            required_permissions=["/mi_comando"],
            version="1.0.0"
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="param1",
                type=ParameterType.STRING,
                description="Descripción",
                required=True,
                validation_rules={"max_length": 500}
            )
        ]

    async def execute(
        self,
        user_id: int,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ToolResult:
        try:
            # Lógica
            resultado = await self._procesar(params["param1"], context)
            return ToolResult.success_result(data=resultado)
        except Exception as e:
            return ToolResult.error_result(
                error=str(e),
                user_friendly_error="Ocurrió un error"
            )
```

**Registrar**:
```python
# src/tools/tool_initializer.py
from .builtin.mi_tool import MiTool

builtin_tools = [
    QueryTool(),
    MiTool(),  # Agregar aquí
]
```

---

## Flujo Completo de Ejecución

```
/ia ¿Cuántos usuarios hay?
    │
    ▼
[tools_handlers.py]
handle_ia_command()
    │
    ▼
ExecutionContextBuilder().build()
    │
    ▼
[ToolOrchestrator]
execute_command(user_id, "/ia", {"query": "..."}, context)
    │
    ├── 1. get_registry().get_tool_by_command("/ia")
    │      └── QueryTool
    │
    ├── 2. _verify_authentication()
    │      └── UserManager.is_registered()
    │
    ├── 3. _verify_permissions()
    │      └── PermissionChecker.check_permission("/ia")
    │
    ├── 4. _validate_parameters()
    │      └── Verifica tipo, min_length, max_length
    │
    ├── 5. QueryTool.execute()
    │      └── context.llm_agent.process_query()
    │
    └── 6. _audit_execution()
           └── Log operación
    │
    ▼
ToolResult(success=True, data="Hay 1,234 usuarios registrados")
```
