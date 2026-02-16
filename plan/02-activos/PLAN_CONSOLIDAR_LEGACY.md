# Plan: Consolidar Sistemas Legacy vs ReAct

> **Estado**: ⚪ No iniciado
> **Ultima actualizacion**: 2026-02-16
> **Rama Git**: feature/consolidar-legacy
> **Archivo referencia**: `src/agent/llm_agent.py` (543 lineas)

---

## Resumen de Progreso

| Fase | Progreso | Tareas | Estado |
|------|----------|--------|--------|
| Fase 1: Eliminar codigo muerto | ░░░░░░░░░░ 0% | 0/6 | ⏳ Pendiente |
| Fase 2: Migrar dependencias activas | ░░░░░░░░░░ 0% | 0/8 | ⏳ Pendiente |
| Fase 3: Remover legacy y limpiar | ░░░░░░░░░░ 0% | 0/5 | ⏳ Pendiente |

**Progreso Total**: ░░░░░░░░░░ 0% (0/19 tareas)

---

## Descripcion

### Problema Actual

Coexisten dos sistemas paralelos tras la migracion a ReAct:
- `src/agent/` (4,646 lineas) - LLMAgent legacy
- `src/agents/` - ReAct Agent nuevo (en uso)
- `src/tools/` (1,087 lineas) - Framework de tools legacy
- `src/orchestrator/` (346 lineas) - Orquestador legacy

**Total codigo legacy: ~6,079 lineas**, de las cuales **~3,580 estan completamente sin usar**.

### Analisis de Dependencias

**Codigo legacy SIN USAR (eliminacion directa):**
| Modulo | Lineas | Razon |
|--------|--------|-------|
| `src/agent/providers/` | 271 | Reemplazado por ReAct con OpenAI directo |
| `src/agent/prompts/` | 900 | Reemplazado por `src/agents/react/prompts.py` |
| `src/agent/memory/` | 888 | Reemplazado por `src/memory/` |
| `src/agent/formatters/` | 313 | ReAct formatea directo |
| `src/agent/classifiers/` | 181 | ReAct decide solo, sin clasificador |
| `src/agent/sql/sql_generator.py` | 94 | Reemplazado por database_tool |
| `src/agent/conversation_history.py` | 189 | Reemplazado por memory service |
| `src/tools/tool_initializer.py` | 79 | No usado |
| `src/tools/builtin/` | 232 | Reemplazado por `src/agents/tools/` |
| **Total** | **~3,147** | |

**Codigo legacy AUN EN USO (requiere migracion):**
| Modulo | Usado por | Accion |
|--------|-----------|--------|
| `src/agent/llm_agent.py` (543 ln) | `query_handlers.py`, `command_handlers.py`, `telegram_bot.py` | Eliminar fallback, usar solo ReAct |
| `src/agent/knowledge/` (1,449 ln) | `command_handlers.py`, `factory.py` | Mover a `src/knowledge/` |
| `src/agent/sql/sql_validator.py` (151 ln) | `database_tool.py` | Mover a `src/agents/tools/` o `src/database/` |
| `src/tools/tool_orchestrator.py` (363 ln) | `query_handlers.py` | Eliminar, ReAct ya orquesta |
| `src/tools/tool_registry.py` (264 ln) | `universal_handler.py` | Eliminar, usar `src/agents/tools/registry.py` |
| `src/tools/execution_context.py` (359 ln) | `universal_handler.py` | Eliminar referencia |
| `src/orchestrator/tool_selector.py` (334 ln) | `query_handlers.py` | Eliminar, ReAct selecciona tools |

---

## Fase 1: Eliminar codigo muerto

**Objetivo**: Eliminar modulos legacy que no son importados por ningun archivo activo
**Duracion estimada**: 1 dia
**Dependencias**: Ninguna

### Tareas

- [ ] **Eliminar `src/agent/providers/`** - Providers legacy (openai, anthropic, base)
  - Archivos: `openai_provider.py`, `anthropic_provider.py`, `base_provider.py`, `__init__.py`
  - Verificar: ningun import activo

- [ ] **Eliminar `src/agent/prompts/`** - Sistema de prompts legacy
  - Archivos: `prompt_templates.py`, `prompt_manager.py`, `config_example.py`, `__init__.py`
  - Verificar: ningun import activo

- [ ] **Eliminar `src/agent/memory/`** - Sistema de memoria legacy
  - Archivos: `memory_repository.py`, `memory_extractor.py`, `memory_manager.py`, `memory_injector.py`, `__init__.py`
  - Verificar: ningun import activo (el nuevo esta en `src/memory/`)

- [ ] **Eliminar `src/agent/formatters/`** - Formateador legacy
  - Archivos: `response_formatter.py`, `__init__.py`
  - Verificar: ningun import activo

- [ ] **Eliminar `src/agent/classifiers/`** - Clasificador legacy
  - Archivos: `query_classifier.py`, `__init__.py`
  - Verificar: ningun import activo

- [ ] **Eliminar archivos sueltos legacy**
  - `src/agent/conversation_history.py` - No usado
  - `src/agent/sql/sql_generator.py` - No usado
  - `src/tools/tool_initializer.py` - No usado
  - `src/tools/builtin/` - Carpeta completa no usada

### Entregables
- [ ] ~3,147 lineas de codigo muerto eliminadas
- [ ] Tests existentes siguen pasando
- [ ] Commit: `refactor(agent): remove unused legacy modules`

---

## Fase 2: Migrar dependencias activas

**Objetivo**: Reubicar los modulos legacy que aun se usan en la ubicacion correcta
**Duracion estimada**: 2-3 dias
**Dependencias**: Fase 1

### Tareas

- [ ] **Mover `src/agent/knowledge/` a `src/knowledge/`** - Modulo de conocimiento
  - Mover: `knowledge_repository.py`, `company_knowledge.py`, `knowledge_manager.py`, `knowledge_categories.py`
  - Actualizar imports en: `command_handlers.py`, `factory.py`

- [ ] **Mover `src/agent/sql/sql_validator.py` a `src/database/sql_validator.py`**
  - Actualizar import en: `src/agents/tools/database_tool.py`

- [ ] **Actualizar `query_handlers.py`** - Eliminar imports de LLMAgent
  - Remover: import de `LLMAgent`, `ToolOrchestrator`, `ToolSelector`
  - Usar solo: `MainHandler` de gateway (ya existe la integracion)

- [ ] **Actualizar `command_handlers.py`** - Eliminar import de LLMAgent
  - El health check puede verificar ReActAgent en vez de LLMAgent

- [ ] **Actualizar `telegram_bot.py`** - Eliminar inicializacion de LLMAgent
  - Remover: creacion de instancia LLMAgent
  - Verificar: factory.py ya crea ReActAgent

- [ ] **Actualizar `universal_handler.py`** - Eliminar imports legacy tools
  - Remover: imports de `tool_registry`, `execution_context` legacy
  - Usar: `src/agents/tools/registry.py` si es necesario

- [ ] **Eliminar feature flag REACT_FALLBACK_ON_ERROR**
  - El fallback a LLMAgent ya no sera necesario
  - Archivo: `src/config/settings.py`

- [ ] **Actualizar tests** - Ajustar tests que referencien modulos movidos
  - `tests/agent/` - Verificar si los tests aplican al nuevo sistema
  - Actualizar imports en tests existentes

### Entregables
- [ ] `src/knowledge/` funcional con imports actualizados
- [ ] `src/database/sql_validator.py` accesible para database_tool
- [ ] Handlers usando solo ReAct (sin fallback legacy)
- [ ] Tests pasando con nuevos imports

---

## Fase 3: Remover legacy y limpiar

**Objetivo**: Eliminar las carpetas legacy vacias y limpiar la estructura
**Duracion estimada**: 1 dia
**Dependencias**: Fase 2

### Tareas

- [ ] **Eliminar `src/agent/`** - Carpeta legacy completa
  - Verificar: ya no queda ningun archivo necesario
  - Eliminar: carpeta completa incluyendo `__init__.py`

- [ ] **Eliminar `src/tools/`** - Framework de tools legacy
  - Verificar: ningun import activo
  - Eliminar: carpeta completa

- [ ] **Eliminar `src/orchestrator/`** - Orquestador legacy
  - Verificar: ningun import activo
  - Eliminar: carpeta completa

- [ ] **Actualizar documentacion**
  - `.claude/context/ARCHITECTURE.md` - Reflejar nueva estructura
  - `.claude/context/TOOLS.md` - Solo tools de ReAct
  - `plan/README.md` - Marcar este plan como completado

- [ ] **Limpiar tests legacy**
  - `tests/agent/` - Eliminar tests de modulos removidos
  - `tests/tools/` - Eliminar tests de tools legacy
  - `tests/orchestrator/` - Eliminar tests de orquestador legacy

### Entregables
- [ ] Estructura limpia sin carpetas legacy
- [ ] Documentacion actualizada
- [ ] Tests limpios y pasando
- [ ] Commit final: `refactor: remove all legacy code after ReAct consolidation`

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|------------|
| Romper imports ocultos | Media | Alto | Grep exhaustivo antes de eliminar, correr tests |
| Perder funcionalidad del LLMAgent fallback | Baja | Medio | ReAct ya es estable, verificar edge cases |
| Knowledge module tiene logica unica | Baja | Alto | Mover sin modificar, solo reubicar |
| Tests dejan de pasar | Media | Medio | Correr tests despues de cada paso |

---

## Criterios de Exito

- [ ] Cero imports a `src/agent/`, `src/tools/`, `src/orchestrator/`
- [ ] Todas las carpetas legacy eliminadas
- [ ] ~6,000 lineas de codigo legacy removidas
- [ ] Tests existentes pasan (los relevantes)
- [ ] Bot funciona correctamente con solo ReAct
- [ ] Documentacion refleja la estructura actual

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2026-02-16 | Creacion del plan | Claude |
