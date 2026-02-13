# Plan de Migración Incremental

## Estrategia: Strangler Fig Pattern

No reescribimos todo de una vez. Vamos envolviendo el sistema actual con la nueva arquitectura, migrando pieza por pieza.

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: Foundation                           │
│  Event Bus + Observability + Base Contracts                     │
│  (Sistema actual sigue funcionando igual)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: Extract Agents                       │
│  ClassifierAgent + GuardrailAgent                               │
│  (LLMAgent delega a los nuevos agentes)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: Supervisor                           │
│  SupervisorAgent reemplaza orquestación de LLMAgent             │
│  (LLMAgent se convierte en adapter temporal)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 4: Specialist Agents                    │
│  DatabaseAgent + KnowledgeAgent + MemoryAgent                   │
│  (Migración completa de lógica)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 5: Advanced Features                    │
│  PlannerAgent + Multi-channel + Event Sourcing completo         │
└─────────────────────────────────────────────────────────────────┘
```

---

## FASE 1: Foundation

### Objetivo
Establecer la infraestructura base sin romper nada existente.

### Tareas

#### 1.1 Event Bus In-Memory
```
src/events/
├── __init__.py
├── base.py          # BaseEvent
├── bus.py           # EventBus singleton
└── types.py         # Tipos de eventos
```

**Archivo: `src/events/bus.py`**
- Implementar EventBus simple con pub/sub
- Agregar logging de eventos para debugging

#### 1.2 Base Contracts
```
src/agents/
├── __init__.py
└── base.py          # BaseAgent, AgentResponse, ConversationEvent
```

**Archivo: `src/agents/base.py`**
- Definir `BaseAgent` abstracto
- Definir `AgentResponse` estándar
- Definir `ConversationEvent` normalizado
- Definir `UserContext`

#### 1.3 Observability Básica
```
src/observability/
├── __init__.py
├── tracing.py       # Decoradores para tracing
└── metrics.py       # Contadores básicos
```

**Archivo: `src/observability/tracing.py`**
- Decorador `@trace` para funciones async
- Logging estructurado con correlation_id

#### 1.4 Integración con Sistema Actual

Modificar `LLMAgent.process_query()` para emitir eventos:

```python
# En LLMAgent.process_query()
async def process_query(self, user_id, query):
    # NUEVO: Emitir evento de inicio
    await event_bus.publish("query.received", {
        "user_id": user_id,
        "query": query,
        "timestamp": datetime.utcnow().isoformat()
    })

    # ... lógica existente ...

    # NUEVO: Emitir evento de respuesta
    await event_bus.publish("query.completed", {
        "user_id": user_id,
        "classification": classification.value,
        "response_length": len(response)
    })

    return response
```

### Entregables Fase 1
- [ ] EventBus funcionando
- [ ] Contratos base definidos
- [ ] Eventos emitidos desde LLMAgent
- [ ] Dashboard simple de eventos (logs)
- [ ] Tests para EventBus

### Duración estimada: 3-5 días

---

## FASE 2: Extract Agents

### Objetivo
Extraer la lógica de clasificación y seguridad en agentes dedicados.

### Tareas

#### 2.1 ClassifierAgent

Extraer de:
- `src/agent/classifiers/query_classifier.py`
- `src/orchestrator/tool_selector.py`

Crear:
```
src/agents/
├── classifier/
│   ├── __init__.py
│   ├── agent.py           # ClassifierAgent
│   ├── intent.py          # Intent model
│   └── prompts.py         # Prompts de clasificación
```

**Cambios en LLMAgent:**
```python
# ANTES
classification = await self.query_classifier.classify(query, context)

# DESPUÉS
intent = await self.classifier_agent.classify(event, context)
classification = self._intent_to_query_type(intent)  # Adapter temporal
```

#### 2.2 GuardrailAgent

Extraer de:
- `src/bot/handlers/query_handlers.py` (validaciones de auth)
- `src/tools/tool_orchestrator.py` (verificación de permisos)
- `src/agent/sql/sql_validator.py` (validación SQL)

Crear:
```
src/agents/
├── guardrail/
│   ├── __init__.py
│   ├── agent.py           # GuardrailAgent
│   └── validators/
│       ├── __init__.py
│       ├── auth.py        # Validación de autenticación
│       ├── permissions.py # Validación de permisos
│       ├── rate_limit.py  # Rate limiting
│       └── content.py     # Validación de contenido
```

**Cambios en QueryHandler:**
```python
# ANTES
if not await self._check_user_registered(user_id):
    return "No estás registrado"
if not await self._check_permission(user_id, "/ia"):
    return "No tienes permiso"

# DESPUÉS
validation = await self.guardrail_agent.validate(event, intent, context)
if not validation.allowed:
    return validation.reason
```

### Entregables Fase 2
- [ ] ClassifierAgent extrayendo lógica de QueryClassifier + ToolSelector
- [ ] GuardrailAgent centralizando validaciones
- [ ] LLMAgent usando los nuevos agentes via adapters
- [ ] Tests unitarios para ambos agentes
- [ ] Feature flag para rollback

### Duración estimada: 5-7 días

---

## FASE 3: Supervisor

### Objetivo
Implementar SupervisorAgent como nuevo punto de entrada.

### Tareas

#### 3.1 SupervisorAgent

Crear:
```
src/agents/
├── supervisor/
│   ├── __init__.py
│   ├── agent.py           # SupervisorAgent
│   └── router.py          # Routing a agentes especialistas
```

#### 3.2 LLMAgent como Legacy Adapter

Convertir LLMAgent en un adapter que delega al Supervisor:

```python
# src/agent/llm_agent.py
class LLMAgent:
    """
    LEGACY: Este clase ahora delega al SupervisorAgent.
    Mantener para compatibilidad con código existente.
    """

    def __init__(self, ...):
        # Inicializar supervisor
        self.supervisor = SupervisorAgent(
            classifier=ClassifierAgent(...),
            guardrail=GuardrailAgent(...),
            memory=MemoryAgent(...),
            agents={
                "database": self,  # LLMAgent actúa como DatabaseAgent temporalmente
                "knowledge": self,
                "chitchat": self,
            }
        )

    async def process_query(self, user_id: str, query: str) -> str:
        # Convertir a nuevo formato
        event = ConversationEvent(
            event_id=str(uuid4()),
            user_id=user_id,
            channel="legacy",
            text=query,
            timestamp=datetime.utcnow(),
            correlation_id=str(uuid4())
        )

        # Delegar al supervisor
        response = await self.supervisor.handle(event)

        # Convertir respuesta al formato esperado
        return response.message or response.error
```

#### 3.3 MessageGateway

Crear gateway unificado:
```
src/gateway/
├── __init__.py
├── message_gateway.py     # Gateway unificado
└── telegram/
    ├── __init__.py
    └── normalizer.py      # Normaliza updates de Telegram
```

### Entregables Fase 3
- [ ] SupervisorAgent funcionando
- [ ] LLMAgent delegando al Supervisor
- [ ] MessageGateway para Telegram
- [ ] Tests de integración
- [ ] Métricas comparativas (latencia antes/después)

### Duración estimada: 5-7 días

---

## FASE 4: Specialist Agents

### Objetivo
Migrar toda la lógica de negocio a agentes especializados.

### Tareas

#### 4.1 DatabaseAgent

Extraer de:
- `src/agent/sql/sql_generator.py`
- `src/agent/sql/sql_validator.py`
- `src/agent/formatters/response_formatter.py`

Crear:
```
src/agents/
├── database/
│   ├── __init__.py
│   ├── agent.py           # DatabaseAgent con pipeline
│   ├── sql_generator.py   # Generación SQL
│   ├── sql_validator.py   # Validación SQL
│   └── result_formatter.py # Formateo de resultados
```

#### 4.2 KnowledgeAgent

Extraer de:
- `src/agent/knowledge/knowledge_manager.py`
- Lógica de RAG en `LLMAgent._handle_knowledge_query()`

Crear:
```
src/agents/
├── knowledge/
│   ├── __init__.py
│   ├── agent.py           # KnowledgeAgent
│   ├── retriever.py       # Búsqueda híbrida
│   └── reranker.py        # Reranking opcional
```

#### 4.3 MemoryAgent

Extraer de:
- `src/agent/memory/memory_manager.py`
- `src/agent/conversation_history.py`

Crear:
```
src/agents/
├── memory/
│   ├── __init__.py
│   ├── agent.py           # MemoryAgent
│   ├── working_memory.py  # Memoria de corto plazo
│   └── long_term.py       # Memoria de largo plazo
```

#### 4.4 ChitchatAgent

Extraer de:
- Lógica de saludos en `LLMAgent._handle_general_query()`

Crear:
```
src/agents/
├── chitchat/
│   ├── __init__.py
│   └── agent.py           # ChitchatAgent
```

### Entregables Fase 4
- [ ] DatabaseAgent con pipeline completo
- [ ] KnowledgeAgent con búsqueda híbrida
- [ ] MemoryAgent con memoria en capas
- [ ] ChitchatAgent para conversación casual
- [ ] LLMAgent deprecado (solo como fallback)
- [ ] Tests completos para cada agente

### Duración estimada: 10-14 días

---

## FASE 5: Advanced Features

### Objetivo
Agregar capacidades avanzadas que no eran posibles antes.

### Tareas

#### 5.1 PlannerAgent
```
src/agents/
├── planner/
│   ├── __init__.py
│   ├── agent.py           # PlannerAgent
│   └── plan_executor.py   # Ejecutor de planes multi-step
```

#### 5.2 Event Sourcing Completo
```
src/events/
├── store.py               # Persistencia de eventos
└── replay.py              # Replay para debugging
```

#### 5.3 Multi-Channel Support
```
src/gateway/
├── whatsapp/
│   └── normalizer.py
├── api/
│   └── routes.py
└── websocket/
    └── handler.py
```

#### 5.4 Self-Correction
- Reintentar con estrategia diferente si falla
- Feedback loop para mejorar clasificación

### Entregables Fase 5
- [ ] PlannerAgent para tareas complejas
- [ ] Event store persistente
- [ ] Soporte multi-canal
- [ ] Self-correction básico
- [ ] Documentación completa

### Duración estimada: 10-14 días

---

## Estructura Final

```
src/
├── agents/
│   ├── __init__.py
│   ├── base.py
│   ├── supervisor/
│   ├── classifier/
│   ├── guardrail/
│   ├── database/
│   ├── knowledge/
│   ├── memory/
│   ├── chitchat/
│   └── planner/
├── events/
│   ├── __init__.py
│   ├── base.py
│   ├── bus.py
│   ├── store.py
│   └── types.py
├── gateway/
│   ├── __init__.py
│   ├── message_gateway.py
│   ├── telegram/
│   ├── api/
│   └── websocket/
├── services/
│   ├── llm/
│   ├── database/
│   ├── cache/
│   └── embeddings/
├── observability/
│   ├── tracing.py
│   ├── metrics.py
│   └── logging.py
├── config/
│   ├── settings.py
│   └── prompts/
├── bot/                    # (LEGACY - mantener por compatibilidad)
├── agent/                  # (LEGACY - deprecar gradualmente)
└── tools/                  # (Integrar en ToolAgent)
```

---

## Checklist de Migración

### Pre-migración
- [ ] Backup completo del código
- [ ] Tests de regresión del sistema actual
- [ ] Métricas baseline (latencia, errores, etc.)
- [ ] Feature flags configurados

### Durante migración
- [ ] Cada fase tiene su propio PR
- [ ] Code review obligatorio
- [ ] Tests pasan antes de merge
- [ ] Rollback plan documentado

### Post-migración
- [ ] Comparar métricas con baseline
- [ ] Documentación actualizada
- [ ] Deprecation warnings en código legacy
- [ ] Plan de eliminación de código legacy

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Regresiones en clasificación | Media | Alto | Tests A/B con tráfico real |
| Aumento de latencia | Media | Medio | Profiling + optimización |
| Complejidad excesiva | Baja | Alto | Revisión de diseño por fase |
| Pérdida de contexto | Baja | Alto | Migración incremental de memoria |

---

## Métricas de Éxito

1. **Latencia p95** <= latencia actual + 10%
2. **Precisión de clasificación** >= 95%
3. **Cobertura de tests** >= 80%
4. **Tiempo de onboarding** para nuevo agente <= 1 día
5. **Código en LLMAgent** reducido a < 100 líneas (solo adapter)
