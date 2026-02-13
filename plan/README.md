# Plan de Refactorización: Multi-Agent Architecture

## Resumen Ejecutivo

Tu `LLMAgent` actual tiene **demasiadas responsabilidades**:
- Orquestación
- Clasificación de intención
- Generación de SQL
- Formateo de respuestas
- Gestión de memoria
- Validación de seguridad

Esto genera:
- Código difícil de testear
- Cambios que afectan todo el sistema
- Dificultad para agregar nuevas funcionalidades

## Solución Propuesta

**Arquitectura Multi-Agent con Event-Driven Design**

```
                    ┌─────────────────┐
                    │  SUPERVISOR     │  ← Único orquestador
                    │  (No lógica)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  CLASSIFIER     │ │   DATABASE      │ │   KNOWLEDGE     │
│  Agent          │ │   Agent         │ │   Agent         │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                    ┌────────▼────────┐
                    │   EVENT BUS     │  ← Comunicación desacoplada
                    └─────────────────┘
```

## Documentos en este Plan

| Archivo | Descripción |
|---------|-------------|
| `ARQUITECTURA_PROPUESTA.md` | Diseño completo de la nueva arquitectura |
| `EJEMPLOS_IMPLEMENTACION.md` | Código de ejemplo para cada componente |
| `PLAN_MIGRACION.md` | Plan incremental de 5 fases |

## Beneficios Clave

1. **Testabilidad**: Cada agente se testea en aislamiento
2. **Extensibilidad**: Agregar agente = nuevo archivo, sin tocar existentes
3. **Observabilidad**: Event sourcing = audit trail completo
4. **Escalabilidad**: Agentes pueden escalar independientemente
5. **Mantenibilidad**: Código más pequeño y enfocado

## Próximos Pasos

1. Revisar `ARQUITECTURA_PROPUESTA.md`
2. Decidir si la dirección es correcta
3. Comenzar con Fase 1 (Foundation)

## Tecnologías Sugeridas

- **Event Bus**: Redis Pub/Sub (producción) / In-memory (desarrollo)
- **Structured Output**: Pydantic + LLM generate_structured
- **Tracing**: OpenTelemetry
- **Tests**: pytest-asyncio
