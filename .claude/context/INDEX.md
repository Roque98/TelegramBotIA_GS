# Iris Bot - Índice de Contexto

**Última actualización**: 2024-02-13
**Rama actual**: `feature/react-fase1-foundation`
**Estado**: Migración a ReAct en progreso

## Navegación Rápida

| Archivo | Descripción | Elementos |
|---------|-------------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitectura del sistema | 4 capas |
| [HANDLERS.md](HANDLERS.md) | Handlers de Telegram | 9 comandos |
| [TOOLS.md](TOOLS.md) | Sistema de Tools | 1 tool |
| [DATABASE.md](DATABASE.md) | Tablas y queries | 15+ tablas |
| [AGENTS.md](AGENTS.md) | Agentes LLM | 1 actual + 7 planificados |
| [PROMPTS.md](PROMPTS.md) | Sistema de prompts | 6 templates |
| [MEMORY.md](MEMORY.md) | Sistema de memoria | 2 capas |

---

## Resumen Ejecutivo

**Iris** es un bot de Telegram conversacional con:
- Consultas a base de datos en lenguaje natural
- Base de conocimiento empresarial con RAG
- Sistema de memoria persistente por usuario
- Arquitectura de Tools extensible

## Stack Tecnológico

```
Backend:     Python 3.11+
Bot:         python-telegram-bot 20.x
LLM:         OpenAI GPT-4 / Anthropic Claude
Database:    SQL Server / MySQL
ORM:         SQLAlchemy 2.0
Validation:  Pydantic 2.x
```

## Estructura del Proyecto

```
src/
├── agent/              # Capa de agentes LLM
│   ├── llm_agent.py    # Orquestador principal
│   ├── classifiers/    # Clasificación de intención
│   ├── memory/         # Memoria persistente
│   ├── knowledge/      # Base de conocimiento
│   ├── prompts/        # Templates de prompts
│   └── sql/            # Generación SQL
├── bot/                # Capa de Telegram
│   └── handlers/       # Command/Message handlers
├── tools/              # Sistema de tools
│   ├── tool_base.py
│   ├── tool_registry.py
│   └── builtin/
├── database/           # Conexión BD
├── auth/               # Autenticación
└── config/             # Configuración
```

## Migración ReAct

```
feature/react-agent-migration
├── feature/react-fase1-foundation     ← EN PROGRESO
├── feature/react-fase2-tools
├── feature/react-fase3-core
├── feature/react-fase4-single-step-agents
├── feature/react-fase5-orchestrator
├── feature/react-fase6-integration
└── feature/react-fase7-polish
```

## Flujo Principal

```
Telegram Message
    ↓
QueryHandler (autenticación + permisos)
    ↓
ToolSelector (auto-selección)
    ↓
ToolOrchestrator → QueryTool
    ↓
LLMAgent.process_query()
    ├── QueryClassifier → DATABASE | KNOWLEDGE | GENERAL
    ├── SQLGenerator (si DATABASE)
    ├── KnowledgeManager (si KNOWLEDGE)
    └── ResponseFormatter
    ↓
Respuesta al usuario
```

## Comandos Disponibles

| Comando | Descripción | Handler |
|---------|-------------|---------|
| `/start` | Bienvenida dinámica | command_handlers.py |
| `/help` | Guía de uso | command_handlers.py |
| `/ia <query>` | Consulta inteligente | tools_handlers.py |
| `/register` | Registro de usuario | registration_handlers.py |
| `/verify` | Verificar cuenta | registration_handlers.py |

## Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Archivos Python | ~50 |
| Líneas de código | ~8,000 |
| Handlers | 9 |
| Tools | 1 |
| Tablas BD | 15+ |
| Templates de Prompts | 6 |
