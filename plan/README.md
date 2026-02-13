# Planes del Proyecto Iris Bot

> **Proyecto**: Iris - Bot conversacional con LLM
> **Última actualización**: 2024-02-13

---

## Resumen General

| Métrica | Valor |
|---------|-------|
| Planes activos | 1 |
| Planes completados | 0 |
| Progreso global | 5% |

---

## Planes Activos

| Plan | Estado | Progreso | Rama | Última Actualización |
|------|--------|----------|------|---------------------|
| [Migración ReAct](PLAN_REACT_MIGRATION.md) | 🟡 En progreso | █░░░░░░░░░ 5% | `feature/react-agent-migration` | 2024-02-13 |

---

## Documentación de Referencia

| Archivo | Descripción |
|---------|-------------|
| [ARQUITECTURA_PROPUESTA.md](ARQUITECTURA_PROPUESTA.md) | Diseño de arquitectura multi-agent |
| [EJEMPLOS_IMPLEMENTACION.md](EJEMPLOS_IMPLEMENTACION.md) | Código de ejemplo para componentes |
| [IMPLEMENTACION_REACT_AGENT.md](IMPLEMENTACION_REACT_AGENT.md) | Especificación técnica detallada |
| [PLAN_MIGRACION.md](PLAN_MIGRACION.md) | Estrategia de migración incremental |
| [REACT_AGENT.md](REACT_AGENT.md) | Explicación del paradigma ReAct |

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
1. Abrir el plan específico
2. Revisar tabla "Resumen de Progreso"
3. Ver tareas pendientes por fase

### Actualizar Progreso
1. Marcar tarea: `[ ]` → `[x]`
2. Agregar commit hash si aplica
3. Recalcular porcentaje de fase
4. Actualizar tabla de resumen
5. Commit: `docs(plan): actualizar progreso`

### Crear Nuevo Plan
1. Usar plantilla de `.claude/skills/project-planner/SKILL.md`
2. Crear archivo `plan/PLAN_<nombre>.md`
3. Agregar entrada a este README

---

## Convención de Nombres

```
plan/
├── README.md                      # Este índice
├── PLAN_<nombre>.md               # Plan con TODOs y progreso
├── <NOMBRE>_<detalle>.md          # Documentación de referencia
└── progress/                      # (Opcional) Historial de progreso
    └── PROGRESS_<nombre>.md
```

---

## Estados de Planes

| Estado | Icono | Descripción |
|--------|-------|-------------|
| No iniciado | ⚪ | Plan creado pero sin trabajo |
| En progreso | 🟡 | Tiene tareas completadas |
| Completado | 🟢 | Todas las fases terminadas |
| Bloqueado | 🔴 | Esperando dependencia externa |
| Pausado | ⏸️ | Detenido temporalmente |
