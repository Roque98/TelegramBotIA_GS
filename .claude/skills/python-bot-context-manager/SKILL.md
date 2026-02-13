---
name: iris-bot-development
description: Skill especializada para desarrollo del bot Iris - Bot conversacional con LLM, arquitectura multi-agent ReAct, sistema de tools, base de conocimiento y memoria persistente.
version: 2.0.0
author: Angel
stack: Python 3.11+, python-telegram-bot, OpenAI, Anthropic, SQL Server, Pydantic
---

# Iris Bot Development Skill

Skill para desarrollo del bot **Iris** - un asistente conversacional inteligente con arquitectura multi-agent basada en ReAct.

## Archivos de Contexto

Para referencia rápida sobre el estado actual del proyecto, consulta:

```
.claude/context/
├── INDEX.md        # Índice y resumen ejecutivo
├── ARCHITECTURE.md # Arquitectura de 4 capas
├── HANDLERS.md     # 9 comandos, 2 message handlers
├── TOOLS.md        # Sistema de tools (1 tool)
├── DATABASE.md     # 15+ tablas, queries comunes
├── AGENTS.md       # LLMAgent actual + plan ReAct
├── PROMPTS.md      # 6 templates versionados
└── MEMORY.md       # Sistema de memoria en capas
```

**Uso**: Estos archivos contienen el estado actual (WHAT exists). Esta skill contiene patrones de desarrollo (HOW to build).

---

## Arquitectura del Proyecto

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM                                       │
│                                                                             │
│  Handlers (src/bot/handlers/)                                               │
│  ├── query_handlers.py    → Mensajes de texto, consultas                   │
│  ├── command_handlers.py  → /start, /help, /stats                          │
│  ├── tools_handlers.py    → /ia, herramientas del bot                      │
│  └── registration_handlers.py → /register, autenticación                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                       │
│                                                                             │
│  Orquestación (src/agent/)                                                  │
│  ├── llm_agent.py         → Orquestador principal (LEGACY → migrar)        │
│  ├── classifiers/         → Clasificación de intención                     │
│  ├── memory/              → Memoria persistente del usuario                │
│  ├── knowledge/           → Base de conocimiento + RAG                     │
│  ├── formatters/          → Formateo de respuestas                         │
│  ├── prompts/             → Templates de prompts versionados               │
│  └── sql/                 → Generación y validación SQL                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TOOLS LAYER                                       │
│                                                                             │
│  Sistema de Tools (src/tools/)                                              │
│  ├── tool_base.py         → BaseTool, ToolResult, ToolMetadata             │
│  ├── tool_registry.py     → Registro singleton de tools                    │
│  ├── tool_orchestrator.py → Ejecución con permisos                         │
│  └── builtin/             → Tools implementados                            │
│      └── query_tool.py    → Tool de consultas /ia                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                        │
│                                                                             │
│  Base de Datos (src/database/)                                              │
│  ├── connection.py        → Pool de conexiones SQL Server                  │
│  └── DatabaseManager      → Queries con sanitización                       │
│                                                                             │
│  Auth (src/auth/)                                                           │
│  ├── user_manager.py      → Gestión de usuarios                            │
│  └── permission_checker.py → Verificación de permisos                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Migración en Progreso: ReAct Agent

El proyecto está migrando a arquitectura **ReAct (Reasoning + Acting)**:

```
feature/react-agent-migration (rama principal)
├── feature/react-fase1-foundation     → Contratos base, EventBus
├── feature/react-fase2-tools          → Sistema de Tools
├── feature/react-fase3-core           → ReAct Agent Loop
├── feature/react-fase4-single-step-agents → DatabaseAgent, KnowledgeAgent
├── feature/react-fase5-orchestrator   → Orquestador + Classifier
├── feature/react-fase6-integration    → Conectar con Telegram
└── feature/react-fase7-polish         → Observability, docs
```

Ver `plan/IMPLEMENTACION_REACT_AGENT.md` para detalles completos.

---

## Patrones de Desarrollo

### 1. Crear un Handler de Telegram

**Ubicación**: `src/bot/handlers/`

```python
# src/bot/handlers/nuevo_handler.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from loguru import logger
from src.auth.user_manager import UserManager
from src.auth.permission_checker import PermissionChecker
from src.utils.status_message import StatusMessage

async def nuevo_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /nuevo - Descripción del comando

    Requiere: Usuario registrado, permiso 'nuevo_comando'
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 1. Verificar autenticación
    user_manager: UserManager = context.bot_data.get('user_manager')
    if not await user_manager.is_registered(user_id):
        await update.message.reply_text(
            "❌ Debes registrarte primero con /register"
        )
        return

    # 2. Verificar permisos
    permission_checker: PermissionChecker = context.bot_data.get('permission_checker')
    if not await permission_checker.has_permission(user_id, 'nuevo_comando'):
        await update.message.reply_text(
            "❌ No tienes permiso para usar este comando"
        )
        return

    # 3. Mostrar status de procesamiento
    status = StatusMessage(update, context)
    await status.start("🔄 Procesando...")

    try:
        # 4. Lógica del comando
        resultado = await procesar_logica(user_id, context.args)

        # 5. Responder
        await status.complete(f"✅ {resultado}")
        logger.info(f"Comando /nuevo ejecutado por {user_id}")

    except Exception as e:
        logger.error(f"Error en /nuevo: {e}")
        await status.error("❌ Ocurrió un error")

# Registrar en main.py
# application.add_handler(CommandHandler("nuevo", nuevo_comando))
```

### 2. Crear un Tool

**Ubicación**: `src/tools/builtin/`

```python
# src/tools/builtin/nuevo_tool.py
from src.tools.tool_base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ParameterType
)
from src.tools.execution_context import ExecutionContext
from typing import Any

class NuevoTool(BaseTool):
    """
    Tool para [descripción]

    Uso: /nuevo <parametro>
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="nuevo_tool",
            description="Descripción del tool",
            category=ToolCategory.UTILITY,
            commands=["/nuevo"],
            parameters=[
                ToolParameter(
                    name="parametro",
                    type=ParameterType.STRING,
                    description="Descripción del parámetro",
                    required=True,
                    min_length=1,
                    max_length=500
                )
            ],
            requires_auth=True,
            required_permissions=["use_tools"]
        )

    async def execute(
        self,
        user_id: str,
        params: dict[str, Any],
        context: ExecutionContext
    ) -> ToolResult:
        """Ejecuta el tool"""
        try:
            parametro = params.get("parametro")

            # Lógica del tool
            resultado = await self._procesar(parametro, context)

            return ToolResult.success(
                data={"resultado": resultado},
                message=f"Procesado: {resultado}"
            )

        except Exception as e:
            return ToolResult.error(f"Error: {str(e)}")

    async def _procesar(self, parametro: str, context: ExecutionContext) -> str:
        # Acceder a servicios via context
        db = context.db_manager
        llm = context.llm_agent

        # ... lógica
        return "resultado"


# Registrar en tool_registry.py
# from src.tools.builtin.nuevo_tool import NuevoTool
# registry.register(NuevoTool())
```

### 3. Agregar Entrada a Knowledge Base

**Tabla**: `BotKnowledge`

```sql
INSERT INTO BotKnowledge (
    category,
    title,
    content,
    keywords,
    is_active,
    required_roles
) VALUES (
    'FAQ',                              -- category: FAQ, POLITICAS, PROCEDIMIENTOS, GENERAL
    'Título de la entrada',             -- title
    'Contenido completo de la respuesta...', -- content
    'palabra1,palabra2,palabra3',       -- keywords separadas por coma
    1,                                  -- is_active
    NULL                                -- required_roles: NULL = todos, 'admin,ventas' = restringido
);
```

**Acceso via código**:

```python
from src.agent.knowledge.knowledge_manager import KnowledgeManager

# Búsqueda
knowledge_manager = KnowledgeManager(db_manager)
await knowledge_manager.load_knowledge(user_roles=['ventas'])

results = await knowledge_manager.search(
    query="política de devoluciones",
    limit=5
)

for entry in results:
    print(f"{entry.title}: {entry.content[:100]}...")
```

### 4. Modificar Prompts

**Ubicación**: `src/agent/prompts/prompt_templates.py`

```python
# Agregar nuevo prompt versionado
class PromptTemplates:
    # ... existing templates ...

    NUEVO_PROMPT_V1 = """
Eres Iris, asistente de {{ empresa }}.

## Contexto del usuario
- ID: {{ user_id }}
- Roles: {{ roles | join(', ') }}

## Memoria del usuario
{{ memory_context }}

## Instrucciones
{{ instrucciones }}

## Consulta
{{ query }}
"""

# Uso con PromptManager
from src.agent.prompts.prompt_manager import PromptManager

prompt_manager = PromptManager()
prompt = prompt_manager.render(
    "NUEVO_PROMPT",
    version="V1",
    empresa="Mi Empresa",
    user_id=123,
    roles=["ventas"],
    memory_context="Usuario frecuente...",
    instrucciones="Responde de forma concisa",
    query="¿Cuántas ventas hubo?"
)
```

### 5. Agregar Memoria de Usuario

**Ubicación**: `src/agent/memory/`

```python
from src.agent.memory.memory_manager import MemoryManager

# Inicializar
memory_manager = MemoryManager(
    db_manager=db,
    llm_provider=llm_provider
)

# Obtener contexto (con cache)
context = await memory_manager.get_memory_context(user_id)
# Retorna: "Usuario frecuente que pregunta sobre ventas..."

# Registrar interacción (async, no bloquea)
await memory_manager.record_interaction(
    user_id=123,
    query="¿Ventas de hoy?",
    response="Las ventas de hoy son $50,000",
    query_type="DATABASE"
)
```

---

## Arquitectura ReAct (Nueva)

### BaseAgent Contract

```python
# src/agents/base/agent.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Optional
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

class UserContext(BaseModel):
    user_id: str
    display_name: str
    roles: list[str]
    preferences: dict[str, Any]
    working_memory: list[dict]
    long_term_summary: Optional[str]

class BaseAgent(ABC):
    name: str
    agent_type: AgentType

    @abstractmethod
    async def execute(
        self,
        query: str,
        context: UserContext,
        **kwargs
    ) -> AgentResponse:
        pass
```

### ReAct Tool Contract

```python
# src/agents/tools/base.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any
from enum import Enum

class ToolCategory(str, Enum):
    DATABASE = "database"
    KNOWLEDGE = "knowledge"
    CALCULATION = "calculation"
    DATETIME = "datetime"

class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_observation(self) -> str:
        if not self.success:
            return f"Error: {self.error}"
        return str(self.data)

class BaseTool(ABC):
    @property
    @abstractmethod
    def definition(self) -> "ToolDefinition":
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass
```

### ReAct Loop

```python
# Pseudocódigo del loop ReAct
async def react_loop(query: str, context: UserContext) -> str:
    scratchpad = []

    while len(scratchpad) < MAX_ITERATIONS:
        # 1. THOUGHT: Razonar sobre qué hacer
        # 2. ACTION: Seleccionar tool y parámetros
        response = await llm.generate_structured(
            prompt=build_prompt(query, context, scratchpad),
            schema=ReActResponse
        )

        # 3. Si es FINISH, retornar
        if response.action == "finish":
            return response.final_answer

        # 4. OBSERVE: Ejecutar tool y observar resultado
        observation = await execute_tool(response.action, response.action_input)

        # 5. Agregar al scratchpad
        scratchpad.append({
            "thought": response.thought,
            "action": response.action,
            "observation": observation
        })

    return synthesize_partial_answer(scratchpad)
```

---

## Base de Datos

### Tablas Principales

| Tabla | Descripción | Archivo |
|-------|-------------|---------|
| `Usuarios` | Usuarios de Telegram registrados | - |
| `BotKnowledge` | Base de conocimiento del bot | `knowledge_repository.py` |
| `UserInteractions` | Historial de interacciones | `memory_repository.py` |
| `UserMemoryProfiles` | Perfiles de memoria largo plazo | `memory_repository.py` |
| `ToolAuditLog` | Auditoría de ejecución de tools | `tool_orchestrator.py` |

### Patrón de Queries

```python
from src.database.connection import DatabaseManager

async def ejemplo_query(db: DatabaseManager, user_id: int):
    # Query parametrizada (segura contra SQL injection)
    query = """
        SELECT id, nombre, total
        FROM Ventas
        WHERE vendedor_id = ?
        AND fecha >= ?
        ORDER BY total DESC
    """

    rows = await db.execute_query(query, [user_id, "2024-01-01"])

    return [dict(row) for row in rows]
```

---

## Configuración

### Variables de Entorno (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_token

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
DB_SERVER=localhost
DB_NAME=ChatBot
DB_USER=sa
DB_PASSWORD=...

# Features
USE_NATURAL_LANGUAGE_RESPONSES=true
ENABLE_MEMORY_SYSTEM=true
MEMORY_UPDATE_THRESHOLD=10
```

### Personalidad del Bot

**Ubicación**: `src/config/personality.py`

```python
BOT_PERSONALITY = {
    "nombre": "Iris",
    "empresa": "Tu Empresa",
    "tono": "profesional pero amigable",
    "emojis": True,
    "idioma": "español"
}
```

---

## Testing

### Estructura de Tests

```
tests/
├── unit/
│   ├── test_query_classifier.py
│   ├── test_sql_validator.py
│   └── test_tools.py
├── integration/
│   ├── test_llm_agent.py
│   └── test_knowledge_manager.py
└── e2e/
    └── test_telegram_flow.py
```

### Ejemplo de Test

```python
# tests/unit/test_nuevo_tool.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.tools.builtin.nuevo_tool import NuevoTool
from src.tools.execution_context import ExecutionContext

@pytest.fixture
def mock_context():
    context = MagicMock(spec=ExecutionContext)
    context.db_manager = AsyncMock()
    context.llm_agent = AsyncMock()
    return context

@pytest.fixture
def tool():
    return NuevoTool()

class TestNuevoTool:
    @pytest.mark.asyncio
    async def test_execute_success(self, tool, mock_context):
        # Arrange
        params = {"parametro": "valor"}
        mock_context.db_manager.execute_query.return_value = [{"id": 1}]

        # Act
        result = await tool.execute("user123", params, mock_context)

        # Assert
        assert result.success is True
        assert "resultado" in result.data

    @pytest.mark.asyncio
    async def test_execute_missing_param(self, tool, mock_context):
        # Arrange
        params = {}

        # Act
        result = await tool.execute("user123", params, mock_context)

        # Assert
        assert result.success is False
        assert "parametro" in result.error.lower()
```

---

## Comandos Útiles

```bash
# Ejecutar bot
pipenv run python main.py

# Tests
pipenv run pytest tests/ -v

# Tests con coverage
pipenv run pytest tests/ --cov=src --cov-report=html

# Lint
pipenv run flake8 src/
pipenv run mypy src/

# Generar migración de BD
# (manual - ver database/migrations/)
```

---

## Flujo de Desarrollo GitFlow

```bash
# 1. Crear feature desde develop
git checkout develop
git pull origin develop
git checkout -b feature/mi-feature

# 2. Desarrollar y commitear
git add .
git commit -m "feat(module): descripción"

# 3. Push y PR
git push -u origin feature/mi-feature
# Crear PR → develop

# 4. Después de merge, limpiar
git checkout develop
git pull origin develop
git branch -d feature/mi-feature
```

### Convención de Commits

```
feat(scope): nueva funcionalidad
fix(scope): corrección de bug
refactor(scope): refactorización sin cambio de comportamiento
docs(scope): documentación
test(scope): tests
chore(scope): tareas de mantenimiento
```

---

## Troubleshooting

### Error: "Usuario no registrado"
```python
# Verificar en BD
SELECT * FROM Usuarios WHERE telegram_id = ?

# O usar comando /register
```

### Error: "SQL inválido"
```python
# SQLValidator solo permite SELECT
# Verificar que no haya INSERT/UPDATE/DELETE
from src.agent.sql.sql_validator import SQLValidator
validator = SQLValidator()
result = validator.validate(query)
print(result.is_valid, result.reason)
```

### Error: "Tool no encontrado"
```python
# Verificar registro
from src.tools.tool_registry import ToolRegistry
registry = ToolRegistry()
print(registry.get_all_tools())
```

### Memoria no se actualiza
```python
# Verificar threshold
# MEMORY_UPDATE_THRESHOLD en .env
# Se actualiza cada N interacciones
```

---

*Skill actualizada para arquitectura ReAct - v2.0.0*
