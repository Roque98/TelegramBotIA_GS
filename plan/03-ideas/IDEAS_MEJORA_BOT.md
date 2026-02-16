# Ideas de Mejora - Iris Bot

> **Creado**: 2026-02-16
> **Basado en**: Analisis del codigo actual (feature/react-fase6-polish)
> **Prioridad**: Ordenadas por impacto estimado

---

## Resumen

| # | Idea | Impacto | Esfuerzo | Categoria |
|---|------|---------|----------|-----------|
| 1 | Consolidar sistemas legacy vs ReAct | Alto | Medio | Limpieza |
| 2 | Sistema de cache para LLM | Alto | Medio | Performance |
| 3 | Multi-agente con especialistas | Alto | Alto | Arquitectura |
| 4 | RAG con base de conocimiento vectorial | Alto | Alto | Funcionalidad |
| 5 | Streaming de respuestas en Telegram | Medio | Bajo | UX |
| 6 | Retry con backoff exponencial | Medio | Bajo | Resiliencia |
| 7 | Dashboard web de monitoreo | Medio | Alto | Observabilidad |
| 8 | Sistema de feedback del usuario | Medio | Medio | UX |
| 9 | Soporte multimedia (imagenes, audio) | Medio | Alto | Funcionalidad |
| 10 | Scheduled tasks / recordatorios | Bajo | Medio | Funcionalidad |

---

## 1. Consolidar sistemas legacy vs ReAct

**Problema**: Coexisten dos sistemas paralelos:
- `src/agent/` - LLMAgent legacy (God Object original)
- `src/agents/` - ReAct Agent nuevo (ya funcional)
- `src/tools/` - Framework de tools legacy
- `src/agents/tools/` - Tools del ReAct

**Propuesta**: Eliminar el codigo legacy que ya fue reemplazado por ReAct.

**Beneficios**:
- Reducir confusion para desarrolladores
- Menos codigo que mantener (~1500 lineas menos)
- Imports mas claros

**Archivos candidatos a eliminar/deprecar**:
```
src/agent/llm_agent.py          -> Reemplazado por src/agents/react/agent.py
src/agent/classifiers/          -> ReAct decide solo, no necesita clasificador
src/agent/sql/                  -> Reemplazado por database_tool
src/tools/                      -> Reemplazado por src/agents/tools/
src/orchestrator/               -> ReAct es su propio orquestador
```

---

## 2. Sistema de cache para LLM

**Problema**: Cada consulta va directo a OpenAI API, incluso consultas repetidas o similares.

**Propuesta**: Cache en dos niveles:
1. **Cache exacto**: Hash de (prompt + context) -> respuesta guardada
2. **Cache semantico**: Embeddings para detectar consultas similares

**Implementacion sugerida**:
```
src/cache/
    __init__.py
    cache_manager.py      # Orquestador de cache
    memory_cache.py       # Cache en memoria (LRU, TTL configurable)
    semantic_cache.py     # Cache por similitud con embeddings
```

**Beneficios**:
- Reduccion de costos API (~30-50% consultas repetidas)
- Respuestas instantaneas para queries frecuentes
- Menos latencia para el usuario

---

## 3. Multi-agente con especialistas

**Problema**: El ReAct Agent hace todo: consultas BD, conversacion, preferencias, calculos. A medida que crece, el prompt se sobrecarga.

**Propuesta**: Router Agent que delega a agentes especializados:

```
Usuario -> Router Agent -> SQL Agent (consultas BD)
                        -> Chat Agent (conversacion casual)
                        -> Admin Agent (configuracion, preferencias)
                        -> Knowledge Agent (base de conocimiento)
```

**Beneficios**:
- Prompts mas enfocados = mejor calidad de respuesta
- Cada agente puede usar modelo diferente (gpt-4o para SQL, gpt-4o-mini para chat)
- Escalabilidad: agregar agentes sin modificar los existentes

---

## 4. RAG con base de conocimiento vectorial

**Problema**: `knowledge_tool` busca en BD relacional con LIKE. No escala bien ni entiende contexto semantico.

**Propuesta**: Implementar RAG (Retrieval Augmented Generation):
1. Vectorizar documentos de conocimiento con embeddings
2. Almacenar en base vectorial (ChromaDB local o pgvector)
3. Buscar por similitud semantica antes de generar respuesta

**Implementacion sugerida**:
```
src/knowledge/
    __init__.py
    embeddings.py         # Generacion de embeddings
    vector_store.py       # Almacen vectorial (ChromaDB)
    retriever.py          # Busqueda semantica
    rag_pipeline.py       # Pipeline completo: retrieve -> augment -> generate
```

**Beneficios**:
- Respuestas mas precisas basadas en documentacion real
- Busqueda semantica vs keyword matching
- Puede indexar PDFs, docs internos, wikis

---

## 5. Streaming de respuestas en Telegram

**Problema**: El usuario espera 5-25 segundos viendo "escribiendo..." hasta que llega la respuesta completa.

**Propuesta**: Usar streaming de OpenAI + editar mensaje de Telegram progresivamente.

**Flujo**:
1. Enviar mensaje placeholder "Pensando..."
2. Hacer stream de tokens desde OpenAI
3. Cada N tokens, editar el mensaje de Telegram con el texto parcial
4. Al completar, enviar mensaje final

**Nota**: Telegram limita ediciones a ~1 por segundo, asi que acumular tokens y editar cada ~1s.

**Beneficios**:
- Percepcion de velocidad mucho mayor
- El usuario ve la respuesta formarse en tiempo real
- Mejor UX, similar a ChatGPT

---

## 6. Retry con backoff exponencial

**Problema**: Si OpenAI falla o hay timeout, la consulta falla directamente. Ya se tiene `tenacity` instalado pero no se usa.

**Propuesta**: Decorar llamadas a LLM y BD con retry:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
)
async def call_llm(self, ...):
    ...
```

**Beneficios**:
- Resiliencia ante fallos transitorios de API
- Ya tienen la dependencia instalada, solo falta usarla
- Esfuerzo minimo, alto impacto

---

## 7. Dashboard web de monitoreo

**Problema**: Solo se puede ver el estado del bot por logs. No hay visibilidad en tiempo real.

**Propuesta**: Dashboard ligero con FastAPI + HTMX (sin framework JS pesado):

```
src/dashboard/
    __init__.py
    app.py                # FastAPI app
    templates/            # Templates Jinja2 + HTMX
    routes/
        metrics.py        # Metricas en tiempo real
        conversations.py  # Historial de conversaciones
        users.py          # Gestion de usuarios
```

**Metricas a mostrar**:
- Consultas por hora/dia
- Tiempo promedio de respuesta
- Errores recientes
- Usuarios activos
- Costos estimados de API
- Tools mas usados

---

## 8. Sistema de feedback del usuario

**Problema**: No hay forma de saber si las respuestas del bot son utiles.

**Propuesta**: Agregar botones inline despues de cada respuesta:

```
[Respuesta del bot aqui...]

[  Util  ] [  No util  ] [  Reportar  ]
```

**Almacenamiento**:
```sql
CREATE TABLE FeedbackRespuestas (
    id INT IDENTITY PRIMARY KEY,
    idUsuario INT,
    idConversacion INT,
    rating VARCHAR(20),      -- 'util', 'no_util', 'reportar'
    comentario NVARCHAR(500),
    fechaCreacion DATETIME DEFAULT GETDATE()
)
```

**Beneficios**:
- Datos reales de calidad de respuestas
- Identificar areas de mejora del prompt
- Detectar consultas problematicas
- Metricas de satisfaccion del usuario

---

## 9. Soporte multimedia (imagenes, audio)

**Problema**: El bot solo procesa texto.

**Propuesta fase 1 - Imagenes**:
- Recibir imagenes y analizarlas con GPT-4o vision
- Generar graficos/charts con matplotlib y enviarlos como imagen

**Propuesta fase 2 - Audio**:
- Recibir notas de voz, transcribir con Whisper
- Responder con audio usando TTS

**Beneficios**:
- UX mas rica y natural
- Usuarios pueden enviar capturas de pantalla para consultar
- Accesibilidad para usuarios que prefieren audio

---

## 10. Scheduled tasks / recordatorios

**Problema**: El bot solo responde cuando le hablan. No tiene proactividad.

**Propuesta**: Sistema de tareas programadas:
- "Recordame revisar ventas todos los lunes a las 9am"
- Alertas automaticas: "Las ventas de hoy cayeron 20% vs ayer"
- Reportes programados enviados por Telegram

**Implementacion**:
- `APScheduler` para scheduling
- Nuevo tool `schedule_tool` para que el agente programe tareas
- Tabla en BD para persistir schedules

---

## Notas

- Estas ideas estan ordenadas por impacto estimado, no por orden de implementacion
- Se recomienda empezar por la #1 (limpieza) y #6 (retry) por ser las de menor esfuerzo
- Las ideas #3 y #4 son las mas ambiciosas pero las de mayor diferenciacion
- Cada idea puede convertirse en un plan formal en `plan/02-activos/`
