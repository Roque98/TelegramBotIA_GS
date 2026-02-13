# Arquitectura del Sistema

## Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPA 1: TELEGRAM                                    │
│                                                                             │
│  src/bot/handlers/                                                          │
│  ├── query_handlers.py      → Mensajes de texto (QueryHandler class)       │
│  ├── command_handlers.py    → /start, /help, /stats, /cancel               │
│  ├── tools_handlers.py      → /ia, /query                                  │
│  ├── registration_handlers.py → /register, /verify, /resend                │
│  └── universal_handler.py   → Fallback universal                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPA 2: AGENTES                                     │
│                                                                             │
│  src/agent/                                                                 │
│  ├── llm_agent.py           → LLMAgent (orquestador, 544 líneas)           │
│  ├── classifiers/                                                          │
│  │   └── query_classifier.py → QueryClassifier (DATABASE|KNOWLEDGE|GENERAL)│
│  ├── memory/                                                               │
│  │   ├── memory_manager.py   → MemoryManager (orquestador)                 │
│  │   ├── memory_repository.py → Persistencia BD                            │
│  │   ├── memory_extractor.py → Genera resúmenes con LLM                    │
│  │   └── memory_injector.py  → Inyecta contexto en prompts                 │
│  ├── knowledge/                                                            │
│  │   ├── knowledge_manager.py → Búsqueda + scoring                         │
│  │   └── knowledge_repository.py → Acceso a BD                             │
│  ├── prompts/                                                              │
│  │   ├── prompt_templates.py → Templates versionados                       │
│  │   └── prompt_manager.py   → Renderizado Jinja2                          │
│  ├── sql/                                                                  │
│  │   ├── sql_generator.py    → Text-to-SQL via LLM                         │
│  │   └── sql_validator.py    → Solo SELECT, sin injection                  │
│  ├── formatters/                                                           │
│  │   └── response_formatter.py → Resultados → lenguaje natural             │
│  └── providers/                                                            │
│      ├── openai_provider.py  → OpenAI GPT-4                                │
│      └── anthropic_provider.py → Claude                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPA 3: TOOLS                                       │
│                                                                             │
│  src/tools/                                                                 │
│  ├── tool_base.py           → BaseTool, ToolResult, ToolMetadata           │
│  ├── tool_registry.py       → ToolRegistry (singleton)                     │
│  ├── tool_orchestrator.py   → Ejecución con auth/permisos                  │
│  ├── execution_context.py   → ExecutionContext + Builder                   │
│  └── builtin/                                                              │
│      └── query_tool.py      → QueryTool (/ia, /query)                      │
│                                                                             │
│  src/orchestrator/                                                          │
│  └── tool_selector.py       → ToolSelector (auto-selección)                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CAPA 4: DATOS                                       │
│                                                                             │
│  src/database/                                                              │
│  └── connection.py          → DatabaseManager (pool, queries)              │
│                                                                             │
│  src/auth/                                                                  │
│  ├── user_manager.py        → UserManager (registro, verificación)         │
│  └── permission_checker.py  → PermissionChecker (roles, operaciones)       │
│                                                                             │
│  src/config/                                                                │
│  ├── settings.py            → Settings (Pydantic BaseSettings)             │
│  └── personality.py         → BOT_PERSONALITY                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Patrones de Diseño

| Patrón | Ubicación | Propósito |
|--------|-----------|-----------|
| **Facade** | LLMAgent | Simplifica acceso a múltiples componentes |
| **Singleton** | ToolRegistry | Una instancia global del registro |
| **Builder** | ExecutionContextBuilder | Construcción fluida de contextos |
| **Strategy** | LLMProvider | Intercambio OpenAI/Anthropic |
| **Template Method** | BaseTool | Estructura común para tools |
| **Chain of Responsibility** | QueryHandler → ToolSelector → Orchestrator | Procesamiento en cadena |

## Flujo de Datos

### Query de Base de Datos

```
"¿Cuántas ventas hubo ayer?"
    │
    ▼
QueryClassifier.classify() → DATABASE
    │
    ▼
SQLGenerator.generate_sql()
    │ Prompt: schema + query + ejemplos
    ▼
"SELECT COUNT(*) FROM ventas WHERE fecha = DATEADD(day, -1, GETDATE())"
    │
    ▼
SQLValidator.validate() → OK
    │
    ▼
DatabaseManager.execute_query()
    │
    ▼
[{"count": 45}]
    │
    ▼
ResponseFormatter.format()
    │
    ▼
"Ayer se realizaron 45 ventas."
```

### Query de Knowledge Base

```
"¿Cuál es la política de devoluciones?"
    │
    ▼
QueryClassifier.classify() → KNOWLEDGE
    │
    ▼
KnowledgeManager.search()
    │ Busca por keywords + scoring
    ▼
[KnowledgeEntry(title="Política de devoluciones", ...)]
    │
    ▼
LLM genera respuesta con contexto
    │
    ▼
"La política de devoluciones establece que..."
```

## Arquitectura Futura: ReAct

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NUEVO: AGENT LAYER                                   │
│                                                                             │
│  src/agents/                                                                │
│  ├── base/                  → BaseAgent, AgentResponse, UserContext        │
│  ├── orchestrator/          → AgentOrchestrator, ComplexityClassifier      │
│  ├── react/                 → ReActAgent, Scratchpad, ReActLoop            │
│  ├── single_step/           → DatabaseAgent, KnowledgeAgent, ChitchatAgent │
│  └── tools/                 → BaseTool (nuevo), ToolRegistry (nuevo)       │
│                                                                             │
│  Beneficios:                                                                │
│  - Agentes especializados e independientes                                  │
│  - Testing unitario fácil                                                   │
│  - Extensibilidad sin modificar código existente                           │
│  - ReAct para consultas multi-paso                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Dependencias Entre Componentes

```
LLMAgent
├── LLMProvider (OpenAI/Anthropic)
├── QueryClassifier
│   └── KnowledgeManager
├── SQLGenerator
│   └── LLMProvider
├── SQLValidator
├── ResponseFormatter
│   └── LLMProvider
├── MemoryManager
│   ├── MemoryRepository
│   ├── MemoryExtractor
│   │   └── LLMProvider
│   └── MemoryInjector
├── ConversationHistory
└── PromptManager

ToolOrchestrator
├── ToolRegistry
│   └── QueryTool
│       └── LLMAgent (delegación)
├── UserManager
└── PermissionChecker
```
