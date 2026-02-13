---
name: project-planner
description: Skill para crear y gestionar planes de proyecto con TODOs, seguimiento de progreso por fases, y documentación estructurada. Todos los planes se guardan en la carpeta plan/.
version: 1.0.0
author: Angel
output_folder: plan/
---

# Project Planner Skill

Skill para crear planes de proyecto estructurados con seguimiento de progreso.

## Ubicación de Archivos

```
plan/
├── README.md                    # Índice de todos los planes
├── PLAN_<nombre>.md             # Plan individual
└── progress/
    └── PROGRESS_<nombre>.md     # Seguimiento de progreso (opcional)
```

---

## Formato de Plan

### Estructura Base

```markdown
# Plan: [Nombre del Plan]

> **Estado**: 🟡 En progreso | 🟢 Completado | 🔴 Bloqueado | ⚪ No iniciado
> **Última actualización**: YYYY-MM-DD
> **Rama Git**: feature/nombre-rama

## Resumen de Progreso

| Fase | Progreso | Estado |
|------|----------|--------|
| Fase 1: [Nombre] | ██████████ 100% | ✅ Completada |
| Fase 2: [Nombre] | ████████░░ 80% | 🔄 En progreso |
| Fase 3: [Nombre] | ░░░░░░░░░░ 0% | ⏳ Pendiente |

**Progreso Total**: ████████░░ 60% (18/30 tareas)

---

## Descripción

[Descripción breve del objetivo del plan]

---

## Fases

### Fase 1: [Nombre de la Fase]

**Objetivo**: [Qué se logra al completar esta fase]
**Duración estimada**: [X días/semanas]
**Dependencias**: [Ninguna | Fase N]

#### Tareas

- [x] **Tarea completada** - Descripción breve
  - Archivo: `src/path/to/file.py`
  - Commit: `abc1234`

- [ ] **Tarea pendiente** - Descripción breve
  - Archivo: `src/path/to/file.py`
  - Notas: Consideraciones adicionales

- [ ] **Tarea con subtareas**
  - [ ] Subtarea 1
  - [ ] Subtarea 2
  - [x] Subtarea 3 completada

#### Entregables
- [ ] Entregable 1
- [ ] Entregable 2

#### Notas de Fase
> Observaciones, decisiones tomadas, problemas encontrados

---

### Fase 2: [Nombre de la Fase]
...

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| [Riesgo 1] | Alta | Alto | [Cómo mitigar] |
| [Riesgo 2] | Media | Medio | [Cómo mitigar] |

---

## Criterios de Éxito

- [ ] Criterio 1: [Descripción medible]
- [ ] Criterio 2: [Descripción medible]
- [ ] Criterio 3: [Descripción medible]

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| YYYY-MM-DD | Creación del plan | [Nombre] |
| YYYY-MM-DD | Completada Fase 1 | [Nombre] |
```

---

## Cálculo de Progreso

### Por Fase
```
Progreso = (tareas_completadas / total_tareas) * 100

Ejemplo:
- Total tareas: 10
- Completadas: 7
- Progreso: 70%
```

### Barra Visual
```
0%   ░░░░░░░░░░
10%  █░░░░░░░░░
20%  ██░░░░░░░░
30%  ███░░░░░░░
40%  ████░░░░░░
50%  █████░░░░░
60%  ██████░░░░
70%  ███████░░░
80%  ████████░░
90%  █████████░
100% ██████████
```

### Estados de Fase
```
⏳ Pendiente     - No iniciada
🔄 En progreso   - Tiene tareas completadas pero no todas
✅ Completada    - Todas las tareas completadas
🔴 Bloqueada     - Esperando dependencia o problema
⏸️ Pausada       - Detenida temporalmente
```

---

## Formato de Tareas

### Tarea Simple
```markdown
- [ ] **Nombre de la tarea** - Descripción breve
```

### Tarea con Detalles
```markdown
- [ ] **Nombre de la tarea** - Descripción breve
  - Archivo: `src/ruta/archivo.py`
  - Dependencia: Tarea X
  - Notas: Información adicional
```

### Tarea con Subtareas
```markdown
- [ ] **Tarea principal**
  - [ ] Subtarea 1
  - [ ] Subtarea 2
  - [ ] Subtarea 3
```

### Tarea Completada
```markdown
- [x] **Tarea completada** - Descripción
  - Archivo: `src/ruta/archivo.py`
  - Commit: `abc1234`
  - Completado: 2024-02-13
```

### Tarea Bloqueada
```markdown
- [ ] 🔴 **Tarea bloqueada** - Descripción
  - Bloqueado por: [Razón]
  - Esperando: [Qué se necesita]
```

---

## Comandos para Actualizar Progreso

### Marcar Tarea Completada
```markdown
# Antes
- [ ] **Implementar feature X**

# Después
- [x] **Implementar feature X**
  - Commit: `abc1234`
  - Completado: 2024-02-13
```

### Actualizar Resumen de Progreso
```markdown
# Contar tareas en el archivo:
# - Total: Contar todos los `- [ ]` y `- [x]`
# - Completadas: Contar solo `- [x]`
# - Calcular porcentaje

| Fase | Progreso | Estado |
|------|----------|--------|
| Fase 1 | ██████████ 100% | ✅ Completada |
| Fase 2 | ████████░░ 80% | 🔄 En progreso |
```

---

## Plantilla: Plan Nuevo

```markdown
# Plan: [NOMBRE]

> **Estado**: ⚪ No iniciado
> **Última actualización**: YYYY-MM-DD
> **Rama Git**: feature/nombre

## Resumen de Progreso

| Fase | Progreso | Estado |
|------|----------|--------|
| Fase 1: [Nombre] | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 2: [Nombre] | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 3: [Nombre] | ░░░░░░░░░░ 0% | ⏳ Pendiente |

**Progreso Total**: ░░░░░░░░░░ 0% (0/X tareas)

---

## Descripción

[Objetivo del plan]

---

## Fase 1: [Nombre]

**Objetivo**: [Qué se logra]
**Dependencias**: Ninguna

### Tareas

- [ ] **Tarea 1** - Descripción
- [ ] **Tarea 2** - Descripción
- [ ] **Tarea 3** - Descripción

### Entregables
- [ ] Entregable 1

---

## Fase 2: [Nombre]

**Objetivo**: [Qué se logra]
**Dependencias**: Fase 1

### Tareas

- [ ] **Tarea 1** - Descripción
- [ ] **Tarea 2** - Descripción

### Entregables
- [ ] Entregable 1

---

## Criterios de Éxito

- [ ] Criterio 1
- [ ] Criterio 2

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| YYYY-MM-DD | Creación del plan | [Nombre] |
```

---

## Ejemplo: Plan de Migración ReAct

```markdown
# Plan: Migración a Arquitectura ReAct

> **Estado**: 🟡 En progreso
> **Última actualización**: 2024-02-13
> **Rama Git**: feature/react-agent-migration

## Resumen de Progreso

| Fase | Progreso | Estado |
|------|----------|--------|
| Fase 1: Foundation | ██░░░░░░░░ 20% | 🔄 En progreso |
| Fase 2: Tools | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 3: ReAct Core | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 4: Single-Step Agents | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 5: Orchestrator | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 6: Integration | ░░░░░░░░░░ 0% | ⏳ Pendiente |
| Fase 7: Polish | ░░░░░░░░░░ 0% | ⏳ Pendiente |

**Progreso Total**: █░░░░░░░░░ 3% (2/60 tareas)

---

## Descripción

Migrar la arquitectura actual del bot (LLMAgent monolítico) a una
arquitectura multi-agent basada en el paradigma ReAct (Reasoning + Acting).

---

## Fase 1: Foundation

**Objetivo**: Establecer contratos base y estructura de carpetas
**Dependencias**: Ninguna

### Tareas

- [x] **Crear estructura de carpetas** - `src/agents/`
  - Commit: `abc1234`

- [x] **Documentar plan de migración** - Archivos en `plan/`
  - Commit: `def5678`

- [ ] **Implementar BaseAgent** - Clase abstracta base
  - Archivo: `src/agents/base/agent.py`

- [ ] **Implementar AgentResponse** - Modelo de respuesta
  - Archivo: `src/agents/base/agent.py`

- [ ] **Implementar UserContext** - Contexto de usuario
  - Archivo: `src/agents/base/events.py`

- [ ] **Implementar EventBus** - Comunicación entre agentes
  - Archivo: `src/events/bus.py`

- [ ] **Tests para contratos base**
  - Archivo: `tests/agents/test_base.py`

### Entregables
- [ ] `src/agents/base/` con contratos
- [ ] Tests unitarios pasando
- [ ] Documentación actualizada

---

## Fase 2: Tools
...
```

---

## Índice de Planes (plan/README.md)

```markdown
# Planes del Proyecto

## Planes Activos

| Plan | Estado | Progreso | Última Actualización |
|------|--------|----------|---------------------|
| [Migración ReAct](IMPLEMENTACION_REACT_AGENT.md) | 🟡 En progreso | 3% | 2024-02-13 |

## Planes Completados

| Plan | Fecha Completado |
|------|-----------------|
| [Ejemplo](PLAN_ejemplo.md) | 2024-01-15 |

## Planes Futuros

- [ ] Plan de API REST
- [ ] Plan de WebSocket
- [ ] Plan de Dashboard Admin
```

---

## Flujo de Trabajo

### 1. Crear Plan Nuevo
```bash
# Crear archivo con plantilla
touch plan/PLAN_nombre.md

# Llenar con plantilla base
# Definir fases y tareas
```

### 2. Trabajar en Tareas
```bash
# Al comenzar tarea
git checkout feature/rama-del-plan

# Al completar tarea
# 1. Commit del código
# 2. Actualizar plan: [ ] → [x]
# 3. Agregar commit hash
# 4. Actualizar progreso de fase
# 5. Actualizar progreso total
```

### 3. Actualizar Progreso
```bash
# Cada vez que se completa una tarea:
# 1. Marcar checkbox
# 2. Recalcular porcentaje de fase
# 3. Recalcular porcentaje total
# 4. Commit del plan actualizado
```

### 4. Completar Fase
```bash
# Al completar todas las tareas de una fase:
# 1. Cambiar estado: 🔄 → ✅
# 2. Verificar entregables
# 3. Agregar notas si es necesario
# 4. Commit: "docs(plan): completar fase N"
```

---

## Integración con GitFlow

```bash
# Plan vive en rama de feature
git checkout feature/nombre-feature

# Cada fase puede tener su propia rama
git checkout -b feature/nombre-fase1

# Al completar fase, merge a rama principal
git checkout feature/nombre-feature
git merge feature/nombre-fase1

# Actualizar plan con progreso
git add plan/PLAN_nombre.md
git commit -m "docs(plan): completar fase 1 - [nombre]"
```

---

## Tips

### Granularidad de Tareas
- Cada tarea debe ser completable en 1-4 horas
- Si es más grande, dividir en subtareas
- Máximo 10-15 tareas por fase

### Actualizaciones Frecuentes
- Actualizar plan al menos 1 vez al día
- Commitear cambios de progreso
- No dejar tareas "casi listas" sin marcar

### Documentar Decisiones
- Usar sección "Notas de Fase" para decisiones
- Documentar cambios de enfoque
- Registrar problemas encontrados

---

*Skill de Project Planner - v1.0.0*
