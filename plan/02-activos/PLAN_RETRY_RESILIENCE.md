# Plan: Retry con Backoff Exponencial

> **Estado**: ⚪ No iniciado
> **Ultima actualizacion**: 2026-02-16
> **Rama Git**: feature/retry-resilience
> **Dependencia**: tenacity==9.0.0 (ya instalada)

---

## Resumen de Progreso

| Fase | Progreso | Tareas | Estado |
|------|----------|--------|--------|
| Fase 1: Retry en LLM providers | ░░░░░░░░░░ 0% | 0/5 | ⏳ Pendiente |
| Fase 2: Retry en base de datos | ░░░░░░░░░░ 0% | 0/5 | ⏳ Pendiente |
| Fase 3: Tests y validacion | ░░░░░░░░░░ 0% | 0/4 | ⏳ Pendiente |

**Progreso Total**: ░░░░░░░░░░ 0% (0/14 tareas)

---

## Descripcion

### Problema Actual

El bot no tiene ningun mecanismo de retry. Si OpenAI devuelve un error transitorio (rate limit, timeout, 500) o la base de datos tiene un hiccup de conexion, la consulta falla inmediatamente.

**Puntos de fallo sin retry:**
| Componente | Archivo | Error tipico |
|------------|---------|--------------|
| OpenAI API | `src/agents/react/agent.py` | RateLimitError, APIConnectionError, Timeout |
| Database query | `src/database/connection.py` | OperationalError, TimeoutError |
| Database write | `src/database/connection.py` | OperationalError, TimeoutError |
| Knowledge lookup | `src/agent/knowledge/knowledge_repository.py` | ConnectionError |

### Solucion

Usar `tenacity` (ya instalada, v9.0.0) para agregar retry con backoff exponencial en los puntos criticos.

**Estrategia de retry:**
```
Intento 1: inmediato
Intento 2: espera 2s
Intento 3: espera 4s
(max 3 intentos, max 30s total)
```

---

## Fase 1: Retry en LLM providers

**Objetivo**: Proteger las llamadas a OpenAI/Anthropic con retry automatico
**Duracion estimada**: 1 dia
**Dependencias**: Ninguna

### Tareas

- [ ] **Crear helper de retry reutilizable** - Configuracion centralizada
  - Archivo: `src/utils/retry.py`
  - Contenido:
    ```python
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    import logging

    logger = logging.getLogger(__name__)

    def llm_retry():
        """Retry decorator para llamadas LLM."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=30),
            retry=retry_if_exception_type((
                Exception,  # Se refinara con tipos especificos
            )),
            before_sleep=lambda retry_state: logger.warning(
                f"LLM retry #{retry_state.attempt_number}: {retry_state.outcome.exception()}"
            ),
            reraise=True,
        )

    def db_retry():
        """Retry decorator para operaciones de BD."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=15),
            retry=retry_if_exception_type((
                ConnectionError,
                TimeoutError,
            )),
            before_sleep=lambda retry_state: logger.warning(
                f"DB retry #{retry_state.attempt_number}: {retry_state.outcome.exception()}"
            ),
            reraise=True,
        )
    ```

- [ ] **Agregar retry al ReActAgent** - Llamada principal al LLM
  - Archivo: `src/agents/react/agent.py`
  - Metodo: `_generate_step()` o donde se llama a OpenAI
  - Decorar con `@llm_retry()`
  - Importar excepciones especificas de OpenAI:
    - `openai.APIError`
    - `openai.RateLimitError`
    - `openai.APIConnectionError`
    - `openai.APITimeoutError`

- [ ] **Agregar retry al OpenAI provider legacy** (si aun se usa)
  - Archivo: `src/agent/providers/openai_provider.py`
  - Metodos: `generate()`, `generate_structured()`
  - Decorar con `@llm_retry()`

- [ ] **Agregar retry al Anthropic provider** (si aun se usa)
  - Archivo: `src/agent/providers/anthropic_provider.py`
  - Metodos: `generate()`, `generate_structured()`
  - Decorar con `@llm_retry()`

- [ ] **Agregar logging de metricas de retry**
  - Loggear: numero de intentos, tiempo total, tipo de error
  - Nivel: WARNING para retries, ERROR para fallo final

### Entregables
- [ ] `src/utils/retry.py` con decoradores reutilizables
- [ ] Llamadas LLM protegidas con retry
- [ ] Logs de retry visibles

---

## Fase 2: Retry en base de datos

**Objetivo**: Proteger operaciones de BD contra errores transitorios
**Duracion estimada**: 1 dia
**Dependencias**: Fase 1 (usa el mismo helper)

### Tareas

- [ ] **Agregar retry a `execute_query()`**
  - Archivo: `src/database/connection.py`
  - Decorar con `@db_retry()`
  - Errores a reintentar: `OperationalError`, `SQLTimeoutError`
  - NO reintentar: `ValueError` (query invalida)

- [ ] **Agregar retry a `execute_non_query()`**
  - Archivo: `src/database/connection.py`
  - Decorar con `@db_retry()`
  - Mismo patron que execute_query

- [ ] **Agregar retry a `get_schema()`**
  - Archivo: `src/database/connection.py`
  - Decorar con `@db_retry()`
  - Errores a reintentar: `OperationalError`, `SQLTimeoutError`

- [ ] **Agregar retry al MemoryRepository**
  - Archivo: `src/memory/repository.py`
  - Metodos: `get_user_profile()`, `save_interaction()`
  - Estos llaman a execute_query/execute_non_query, que ya tendran retry
  - Verificar que no haya doble retry

- [ ] **Configurar retry por entorno**
  - Archivo: `src/config/settings.py`
  - Variables:
    ```python
    RETRY_LLM_MAX_ATTEMPTS: int = 3
    RETRY_LLM_MIN_WAIT: int = 2
    RETRY_LLM_MAX_WAIT: int = 30
    RETRY_DB_MAX_ATTEMPTS: int = 3
    RETRY_DB_MIN_WAIT: int = 1
    RETRY_DB_MAX_WAIT: int = 15
    ```

### Entregables
- [ ] Operaciones de BD protegidas con retry
- [ ] Configuracion por entorno
- [ ] Sin doble retry en cadenas de llamadas

---

## Fase 3: Tests y validacion

**Objetivo**: Verificar que el retry funciona correctamente
**Duracion estimada**: 1 dia
**Dependencias**: Fase 1, Fase 2

### Tareas

- [ ] **Tests unitarios para retry helper**
  - Archivo: `tests/utils/test_retry.py`
  - Tests:
    - Retry se activa en error transitorio
    - Retry NO se activa en error permanente (ValueError)
    - Max attempts se respeta
    - Backoff exponencial funciona
    - Logging de retry correcto

- [ ] **Tests de integracion para LLM retry**
  - Mock OpenAI para simular RateLimitError
  - Verificar que reintenta y luego tiene exito
  - Verificar que falla despues de max attempts

- [ ] **Tests de integracion para DB retry**
  - Mock session para simular OperationalError
  - Verificar retry y recuperacion
  - Verificar que ValueError no hace retry

- [ ] **Test manual end-to-end**
  - Probar con bot real
  - Verificar logs de retry
  - Verificar que errores transitorios se recuperan

### Entregables
- [ ] Suite de tests para retry
- [ ] Validacion manual exitosa
- [ ] Documentacion actualizada

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|------------|
| Retry en escrituras causa duplicados | Media | Alto | execute_non_query es idempotente (UPDATE/MERGE) |
| Retry alarga el tiempo de respuesta | Baja | Medio | Max 30s para LLM, 15s para BD, usuario ve "escribiendo..." |
| Doble retry (tool + DB) | Media | Bajo | Retry solo en capa mas baja (connection.py) |
| Rate limit loop infinito | Baja | Alto | Max 3 intentos, backoff exponencial |

---

## Criterios de Exito

- [ ] Zero llamadas a OpenAI sin proteccion de retry
- [ ] Zero operaciones de BD sin proteccion de retry
- [ ] Tests de retry pasando
- [ ] Logs muestran retries cuando ocurren errores transitorios
- [ ] Tiempo de respuesta promedio no afectado en condiciones normales

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2026-02-16 | Creacion del plan | Claude |
