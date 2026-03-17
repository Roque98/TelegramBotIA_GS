# Plan: AlertAnalysisTool — Análisis de Alertas por Lenguaje Natural

## Objetivo
Permitir que el usuario le hable al bot de forma natural para obtener un análisis
inteligente de alertas activas en la plataforma de monitoreo, combinando:
- Datos del evento actual (SP `PrtgObtenerEventosEnriquecidos`)
- Historial de tickets en sensores similares (Query histórica)

## Estructura del plan

| Carpeta/Archivo | Contenido |
|---|---|
| `todo/` | Tareas pendientes de iniciar |
| `in_progress/` | Tareas en desarrollo activo |
| `done/` | Tareas completadas |

## Orden de implementación recomendado

1. **Multi-DB Config** — soporte de múltiples conexiones en settings y DatabaseManager
2. **AlertRepository** — queries SP1 y Query 2 contra la BD de monitoreo
3. **AlertPromptBuilder** — construcción del prompt enriquecido
4. **AlertAnalysisTool** — tool registrado en el pipeline existente
5. **Registro del tool** — ToolRegistry + ToolSelector reconoce el nuevo tool
6. **Pruebas de integración**

## Decisiones de diseño

- La BD por default sigue siendo la del `.env` actual (`consolaMonitoreo`)
- Las BDs adicionales se identifican con un **alias** (ej: `monitoreos`, `abcmasplus`)
- Cada alias tiene su propio bloque de config en `.env` con prefijo (ej: `MONITOREOS_DB_HOST`)
- `DatabaseManager` acepta un parámetro `db_alias` opcional; sin él usa la default
- El `AlertRepository` recibe explícitamente el alias `monitoreos` al instanciarse
