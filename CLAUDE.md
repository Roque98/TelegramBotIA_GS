# Instrucciones para Claude Code

## Proyecto
**Nombre**: Iris Bot
**Tipo**: Bot conversacional con LLM para Telegram
**Rama principal**: develop (GitFlow)

## Comportamiento de Git

### Commits Automáticos
- **Hacer commit automáticamente** cuando se completen cambios significativos:
  - Creación o modificación de archivos de código
  - Actualización de documentación o planes
  - Consolidación o refactorización de archivos
  - Finalización de una tarea del plan

### Convención de Commits
Usar formato: `tipo(scope): descripción`

Tipos:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `refactor`: Refactorización sin cambio de funcionalidad
- `docs`: Documentación
- `test`: Tests
- `chore`: Tareas de mantenimiento

Scopes del proyecto:
- `agent`: LLMAgent y agentes
- `bot`: Handlers de Telegram
- `tools`: Sistema de herramientas
- `db`: Base de datos
- `auth`: Autenticación
- `plan`: Planes de proyecto
- `skill`: Skills de Claude

### Push Automático
- Hacer push automáticamente después de cada commit
- Rama actual: seguir GitFlow (feature/*, develop, etc.)

## Plan Activo

El plan principal está en: `plan/PLAN_REACT_MIGRATION.md`
- Archivo de referencia: `src/agent/llm_agent.py`
- Progreso actual: Fase 1 - Foundation

## Archivos de Contexto

- `.claude/context/` - Documentación del estado actual del proyecto
- `.claude/skills/` - Skills disponibles para desarrollo
- `plan/` - Planes de proyecto con TODOs

## Notas Importantes

- Usar Pydantic v2 para modelos
- El proyecto usa async/await
- Base de datos: SQL Server
- LLM Provider: OpenAI (configurable)
