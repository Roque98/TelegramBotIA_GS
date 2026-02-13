# Planes del Proyecto Iris Bot

> **Proyecto**: Iris - Bot conversacional con LLM
> **Última actualización**: 2024-02-13

---

## Resumen General

| Métrica | Valor |
|---------|-------|
| Planes activos | 1 |
| Planes completados | 0 |
| Progreso global | 4% |

---

## Planes Activos

| Plan | Estado | Progreso | Rama | Archivo Referencia |
|------|--------|----------|------|-------------------|
| [Migración ReAct](PLAN_REACT_MIGRATION.md) | En progreso | 4% (2/56) | `feature/react-agent-migration` | `src/agent/llm_agent.py` |

---

## Planes Futuros

- [ ] API REST para integración externa
- [ ] WebSocket para tiempo real
- [ ] Dashboard de administración
- [ ] Sistema de plugins
- [ ] Multi-idioma

---

## Cómo Usar los Planes

### Ver Progreso
1. Abrir `PLAN_REACT_MIGRATION.md`
2. Revisar tabla "Resumen de Progreso"
3. Ver tareas pendientes por fase

### Actualizar Progreso
1. Marcar tarea: `[ ]` → `[x]`
2. Agregar commit hash si aplica
3. Recalcular porcentaje de fase
4. Actualizar tabla de resumen
5. Commit: `docs(plan): actualizar progreso fase N`

### Crear Nuevo Plan
1. Usar plantilla de `.claude/skills/project-planner/SKILL.md`
2. Crear archivo `plan/PLAN_<nombre>.md`
3. Agregar entrada a este README

---

## Estructura

```
plan/
├── README.md                 # Este índice
└── PLAN_REACT_MIGRATION.md   # Plan consolidado con TODOs y código
```

---

## Estados de Planes

| Estado | Descripción |
|--------|-------------|
| No iniciado | Plan creado pero sin trabajo |
| En progreso | Tiene tareas completadas |
| Completado | Todas las fases terminadas |
| Bloqueado | Esperando dependencia externa |
| Pausado | Detenido temporalmente |
