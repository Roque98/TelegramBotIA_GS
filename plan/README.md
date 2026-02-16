# Planes del Proyecto Iris Bot

> **Proyecto**: Iris - Bot conversacional con LLM
> **Ultima actualizacion**: 2026-02-16

---

## Estructura

```
plan/
├── README.md                              # Este indice
├── 01-completados/                        # Planes finalizados
│   └── PLAN_REACT_MIGRATION.md            # Migracion a ReAct (100%)
├── 02-activos/                            # Planes en progreso
│   ├── PLAN_CONSOLIDAR_LEGACY.md          # Eliminar codigo legacy (19 tareas)
│   └── PLAN_RETRY_RESILIENCE.md           # Retry con tenacity (14 tareas)
└── 03-ideas/                              # Ideas y propuestas
    └── IDEAS_MEJORA_BOT.md                # 10 ideas de mejora priorizadas
```

---

## Resumen General

| Metrica | Valor |
|---------|-------|
| Planes completados | 1 |
| Planes activos | 2 |
| Ideas documentadas | 10 |

---

## Planes Completados (01-completados/)

| Plan | Progreso | Rama | Fecha |
|------|----------|------|-------|
| [Migracion ReAct](01-completados/PLAN_REACT_MIGRATION.md) | 100% (47/47) | `feature/react-agent-migration` | 2024-02-13 |

---

## Planes Activos (02-activos/)

| Plan | Progreso | Rama | Tareas |
|------|----------|------|--------|
| [Consolidar Legacy](02-activos/PLAN_CONSOLIDAR_LEGACY.md) | 0% (0/19) | `feature/consolidar-legacy` | Eliminar ~6,000 ln legacy |
| [Retry Resilience](02-activos/PLAN_RETRY_RESILIENCE.md) | 0% (0/14) | `feature/retry-resilience` | Tenacity en LLM + BD |

---

## Ideas de Mejora (03-ideas/)

| # | Idea | Impacto | Esfuerzo |
|---|------|---------|----------|
| 1 | Consolidar sistemas legacy vs ReAct | Alto | Medio |
| 2 | Cache para LLM | Alto | Medio |
| 3 | Multi-agente con especialistas | Alto | Alto |
| 4 | RAG con base de conocimiento vectorial | Alto | Alto |
| 5 | Streaming de respuestas | Medio | Bajo |
| 6 | Retry con backoff exponencial | Medio | Bajo |
| 7 | Dashboard web de monitoreo | Medio | Alto |
| 8 | Feedback del usuario | Medio | Medio |
| 9 | Soporte multimedia | Medio | Alto |
| 10 | Scheduled tasks / recordatorios | Bajo | Medio |

Ver detalle completo en [IDEAS_MEJORA_BOT.md](03-ideas/IDEAS_MEJORA_BOT.md)

---

## Como Usar

### Crear Nuevo Plan
1. Usar plantilla de `.claude/skills/project-planner/SKILL.md`
2. Crear archivo `plan/02-activos/PLAN_<NOMBRE>.md`
3. Agregar entrada a este README
4. Commit: `docs(plan): crear plan <nombre>`

### Completar un Plan
1. Verificar que todas las tareas esten marcadas `[x]`
2. Mover de `02-activos/` a `01-completados/`
3. Actualizar este README
4. Commit: `docs(plan): completar plan <nombre>`

### Promover una Idea a Plan
1. Elegir idea de `03-ideas/`
2. Crear plan formal en `02-activos/PLAN_<NOMBRE>.md`
3. Actualizar ambos README
4. Commit: `docs(plan): promover idea <nombre> a plan activo`

---

## Estados

| Estado | Carpeta | Descripcion |
|--------|---------|-------------|
| Idea | `03-ideas/` | Propuesta sin plan formal |
| Activo | `02-activos/` | Plan con tareas en progreso |
| Completado | `01-completados/` | Todas las fases terminadas |
