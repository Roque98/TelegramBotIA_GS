# 📋 Iris Bot - Consolidacion de Codigo Legacy

## 📝 Descripcion
Eliminacion y reubicacion del codigo legacy que quedo tras la migracion exitosa a arquitectura ReAct. El proyecto mantiene ~6,079 lineas de codigo obsoleto en `src/agent/`, `src/tools/` y `src/orchestrator/` que generan confusion, duplicidad y carga de mantenimiento.

## 🏷️ Tipo de Proyecto
- Desarrollo
- Bot/Automatizacion

## 📊 Status
- [x] ⏸️ Pendiente

## 📈 Avance
- Tareas completadas / Total tareas: 0 / 19
- Porcentaje: 0%

## 📅 Cronologia
- **Semana de inicio**: Semana 8 - 16/02/2026
- **Semana de fin**: En curso
- **Deadline critico**: N/A

## 👥 Solicitantes

| Nombre | Correo | Area | Extension/Celular |
|--------|--------|------|-------------------|
| Angel | [correo@ejemplo.com] | Desarrollo | N/A |

## 👨‍💻 Recursos Asignados

**Admin:**
- Angel - Tech Lead

**Desarrollo:**
- Claude - Asistente IA / Desarrollo

## 🔧 Actividades

### ✅ Realizadas
- ✔️ **Analisis de dependencias**: Identificados 3,147 lineas sin usar y 2,932 lineas que requieren migracion
- ✔️ **Plan de ejecucion**: Creado plan en 3 fases con 19 tareas detalladas

### 📋 Por hacer

**Fase 1 - Eliminar codigo muerto (6 tareas):**
- ⏳ **Eliminar providers legacy**: `src/agent/providers/` (271 lineas) - reemplazados por ReAct
- ⏳ **Eliminar prompts legacy**: `src/agent/prompts/` (900 lineas) - reemplazados por `src/agents/react/prompts.py`
- ⏳ **Eliminar memory legacy**: `src/agent/memory/` (888 lineas) - reemplazado por `src/memory/`
- ⏳ **Eliminar formatters legacy**: `src/agent/formatters/` (313 lineas) - ReAct formatea directo
- ⏳ **Eliminar classifiers legacy**: `src/agent/classifiers/` (181 lineas) - ReAct decide solo
- ⏳ **Eliminar archivos sueltos**: `conversation_history.py`, `sql_generator.py`, `tool_initializer.py`, `builtin/`

**Fase 2 - Migrar dependencias activas (8 tareas):**
- ⏳ **Mover knowledge**: `src/agent/knowledge/` → `src/knowledge/` (1,449 lineas, usado por handlers)
- ⏳ **Mover sql_validator**: `src/agent/sql/sql_validator.py` → `src/database/` (151 lineas, usado por database_tool)
- ⏳ **Actualizar query_handlers**: Eliminar imports de LLMAgent, usar solo ReAct
- ⏳ **Actualizar command_handlers**: Eliminar import de LLMAgent
- ⏳ **Actualizar telegram_bot.py**: Eliminar inicializacion de LLMAgent
- ⏳ **Actualizar universal_handler**: Eliminar imports de tools legacy
- ⏳ **Eliminar feature flag**: Remover REACT_FALLBACK_ON_ERROR
- ⏳ **Actualizar tests**: Ajustar imports a nuevas ubicaciones

**Fase 3 - Remover legacy y limpiar (5 tareas):**
- ⏳ **Eliminar src/agent/**: Carpeta legacy completa
- ⏳ **Eliminar src/tools/**: Framework legacy completo
- ⏳ **Eliminar src/orchestrator/**: Orquestador legacy completo
- ⏳ **Actualizar documentacion**: ARCHITECTURE.md, TOOLS.md
- ⏳ **Limpiar tests legacy**: tests/agent/, tests/tools/, tests/orchestrator/

## ⚠️ Impedimentos y Deadlines

### 🚧 Bloqueadores Activos
N/A - No hay bloqueadores activos

## 📦 Entregables
- [ ] 📖 **Plan de consolidacion**: [PLAN_CONSOLIDAR_LEGACY.md](../../plan/02-activos/PLAN_CONSOLIDAR_LEGACY.md)
- [ ] 📓 **OneNote actualizado**: Este documento
- [ ] 🔧 **Codigo limpio**: ~6,000 lineas legacy eliminadas
- [ ] 📝 **Documentacion actualizada**: ARCHITECTURE.md, TOOLS.md

## 🔗 URLs

### 📊 Repositorio
- [GitHub - TelegramBotIA](https://github.com/Roque98/TelegramBotIA)

### 🖥️ Ramas Git
- `feature/consolidar-legacy` - Rama para este trabajo

## 🔧 Informacion Tecnica

### 💻 Codigo a Eliminar
```
src/agent/                    # 4,646 lineas (eliminar todo)
├── providers/                # 271 ln - NO USADO
├── prompts/                  # 900 ln - NO USADO
├── memory/                   # 888 ln - NO USADO
├── formatters/               # 313 ln - NO USADO
├── classifiers/              # 181 ln - NO USADO
├── knowledge/                # 1,449 ln - MOVER a src/knowledge/
├── sql/sql_validator.py      # 151 ln - MOVER a src/database/
├── sql/sql_generator.py      # 94 ln - NO USADO
├── conversation_history.py   # 189 ln - NO USADO
└── llm_agent.py              # 543 ln - ELIMINAR (fallback)

src/tools/                    # 1,087 lineas (eliminar todo)
src/orchestrator/             # 346 lineas (eliminar todo)
```

### 💻 Estructura Final Esperada
```
src/
├── agents/          # ReAct agent (unico sistema)
├── bot/             # Handlers de Telegram
├── config/          # Configuracion
├── database/        # Conexion + sql_validator
├── events/          # Event bus
├── gateway/         # Message gateway
├── knowledge/       # NUEVO - migrado desde agent/knowledge
├── memory/          # Servicio de memoria
├── observability/   # Metricas y tracing
└── utils/           # Utilidades
```

### 🖥️ Servidores/Deploy
- **Ambiente**: DEV
- **Servidor**: Local
- **Ruta**: D:\proyectos\gs\GPT5

## 📋 Ordenes de Cambio

| OC | Descripcion | Status | Fecha |
|----|-------------|--------|-------|
| N/A | Sin OCs registradas | - | - |

---

*Documento generado: 16/02/2026*
*Ultima actualizacion: 16/02/2026*
