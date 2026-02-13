# Plan: Migración a Arquitectura ReAct

> **Estado**: 🟡 En progreso
> **Última actualización**: 2024-02-13
> **Rama Git**: `feature/react-agent-migration`
> **Documentación**: [IMPLEMENTACION_REACT_AGENT.md](IMPLEMENTACION_REACT_AGENT.md)

---

## Resumen de Progreso

| Fase | Progreso | Tareas | Estado |
|------|----------|--------|--------|
| Fase 1: Foundation | ██░░░░░░░░ 20% | 2/10 | 🔄 En progreso |
| Fase 2: Tools | ░░░░░░░░░░ 0% | 0/8 | ⏳ Pendiente |
| Fase 3: ReAct Core | ░░░░░░░░░░ 0% | 0/10 | ⏳ Pendiente |
| Fase 4: Single-Step Agents | ░░░░░░░░░░ 0% | 0/8 | ⏳ Pendiente |
| Fase 5: Orchestrator | ░░░░░░░░░░ 0% | 0/6 | ⏳ Pendiente |
| Fase 6: Integration | ░░░░░░░░░░ 0% | 0/8 | ⏳ Pendiente |
| Fase 7: Polish | ░░░░░░░░░░ 0% | 0/6 | ⏳ Pendiente |

**Progreso Total**: █░░░░░░░░░ 4% (2/56 tareas)

---

## Descripción

Migrar la arquitectura actual del bot (LLMAgent monolítico de 544 líneas) a una arquitectura multi-agent basada en el paradigma **ReAct (Reasoning + Acting)**.

### Objetivos
- Separar responsabilidades en agentes especializados
- Implementar razonamiento paso a paso para consultas complejas
- Mejorar testabilidad y extensibilidad
- Mantener compatibilidad con funcionalidad actual

### Estrategia
Usar **Strangler Fig Pattern**: envolver el sistema actual con la nueva arquitectura, migrando pieza por pieza.

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

### Entregables
- [ ] `src/agents/base/` con todos los contratos
- [ ] `src/events/bus.py` funcionando
- [ ] Tests pasando con cobertura >80%
- [ ] Documentación actualizada

### Notas de Fase
> - Usar Pydantic v2 para todos los modelos
> - EventBus debe ser async-compatible
> - No modificar código existente en esta fase

---

## Fase 2: Tools

**Objetivo**: Implementar sistema de Tools nuevo compatible con ReAct
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

- [ ] **Implementar BaseTool nuevo** - Clase abstracta para ReAct tools
  - Archivo: `src/agents/tools/base.py`
  - Métodos: `definition`, `execute()`, `validate_params()`

- [ ] **Implementar ToolRegistry nuevo** - Registro singleton
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

### Entregables
- [ ] `src/agents/tools/` con todos los tools
- [ ] Tests para cada tool
- [ ] Documentación de cómo agregar nuevos tools

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
  - Templates: system prompt, step prompt

- [ ] **Implementar _generate_step()** - Generar siguiente paso
  - Usa: LLM con structured output (Pydantic)

- [ ] **Implementar _execute_tool()** - Ejecutar tool y obtener observación
  - Integra: ToolRegistry

- [ ] **Implementar _synthesize_partial()** - Respuesta si se exceden iteraciones
  - Genera respuesta parcial con observaciones recolectadas

- [ ] **Tests de integración ReAct** - Tests del loop completo
  - Archivo: `tests/agents/test_react.py`
  - Mocks para LLM y tools

### Entregables
- [ ] `src/agents/react/` completo
- [ ] ReActAgent funcionando con tools de Fase 2
- [ ] Tests de integración pasando
- [ ] Ejemplos documentados

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

- [ ] **Tests unitarios por agente** - Tests aislados
  - Archivos: `tests/agents/test_database_agent.py`, etc.

- [ ] **Tests de integración** - Agentes funcionando juntos
  - Archivo: `tests/agents/test_single_step_integration.py`

- [ ] **Documentar patrones** - Cómo crear nuevos agentes
  - Actualizar: `.claude/skills/python-bot-context-manager/SKILL.md`

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
  - Obtener contexto antes de ejecutar

- [ ] **Tests de orquestación** - Routing correcto
  - Archivo: `tests/agents/test_orchestrator.py`

- [ ] **Métricas de routing** - Logging de decisiones
  - Para análisis y mejora del clasificador

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
  - Mantener código existente como backup

- [ ] **Tests E2E** - Flujo completo Telegram → Respuesta
  - Archivo: `tests/e2e/test_telegram_flow.py`

- [ ] **Comparar métricas** - Latencia, precisión
  - Antes vs después de migración

- [ ] **Documentar rollback** - Procedimiento de emergencia
  - En caso de problemas en producción

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
  - Traces por request completo

- [ ] **Implementar métricas** - Prometheus/básicas
  - Archivo: `src/observability/metrics.py`
  - Métricas: latencia, errores, uso por agente

- [ ] **Structured logging** - Logs JSON
  - Archivo: `src/observability/logging.py`
  - Correlation IDs

- [ ] **Actualizar documentación** - Contexto y skills
  - Archivos: `.claude/context/*.md`

- [ ] **Optimización de prompts** - Reducir tokens
  - Revisar y optimizar prompts de ReAct

- [ ] **Performance tuning** - Cachés, connection pools
  - Revisar bottlenecks

### Entregables
- [ ] Observabilidad completa
- [ ] Documentación actualizada
- [ ] Performance optimizada
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
- [ ] Documentación completa

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2024-02-13 | Creación del plan | Claude |
| 2024-02-13 | Estructura de carpetas y documentación | Claude |
| 2024-02-13 | Formato con TODOs | Claude |
