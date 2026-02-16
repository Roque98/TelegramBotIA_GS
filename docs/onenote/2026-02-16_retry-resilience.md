# 📋 Iris Bot - Retry con Backoff Exponencial

## 📝 Descripcion
Implementacion de mecanismo de retry automatico con backoff exponencial para proteger las llamadas a OpenAI API y base de datos contra errores transitorios. Utiliza la libreria `tenacity` (v9.0.0) que ya esta instalada pero no se usa en ningun lugar del proyecto.

## 🏷️ Tipo de Proyecto
- Desarrollo
- Bot/Automatizacion

## 📊 Status
- [x] ⏸️ Pendiente

## 📈 Avance
- Tareas completadas / Total tareas: 0 / 14
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
- ✔️ **Analisis de puntos de fallo**: Identificados 6 puntos criticos sin retry (2 LLM, 4 BD)
- ✔️ **Verificacion de dependencia**: tenacity==9.0.0 confirmado en requirements.txt y Pipfile
- ✔️ **Plan de ejecucion**: Creado plan en 3 fases con 14 tareas

### 📋 Por hacer

**Fase 1 - Retry en LLM providers (5 tareas):**
- ⏳ **Crear retry helper**: `src/utils/retry.py` con decoradores `llm_retry()` y `db_retry()` reutilizables
- ⏳ **Proteger ReActAgent**: Decorar `_generate_step()` con retry para OpenAI API
- ⏳ **Proteger OpenAI provider**: Decorar `generate()` y `generate_structured()` con retry
- ⏳ **Proteger Anthropic provider**: Decorar `generate()` y `generate_structured()` con retry
- ⏳ **Agregar logging de retry**: WARNING en cada reintento, ERROR en fallo final

**Fase 2 - Retry en base de datos (5 tareas):**
- ⏳ **Proteger execute_query()**: Retry en `src/database/connection.py` para OperationalError/TimeoutError
- ⏳ **Proteger execute_non_query()**: Retry en `src/database/connection.py` para escrituras
- ⏳ **Proteger get_schema()**: Retry para inspeccion de esquema
- ⏳ **Verificar MemoryRepository**: Asegurar que no haya doble retry con connection.py
- ⏳ **Configuracion por entorno**: Variables en settings.py para max_attempts, min/max_wait

**Fase 3 - Tests y validacion (4 tareas):**
- ⏳ **Tests unitarios**: `tests/utils/test_retry.py` - retry activo/inactivo segun tipo de error
- ⏳ **Tests integracion LLM**: Mock OpenAI con RateLimitError, verificar recuperacion
- ⏳ **Tests integracion BD**: Mock session con OperationalError, verificar retry
- ⏳ **Validacion manual**: Probar bot real, verificar logs

## ⚠️ Impedimentos y Deadlines

### 🚧 Bloqueadores Activos
N/A - No hay bloqueadores activos

## 📦 Entregables
- [ ] 📖 **Plan de retry**: [PLAN_RETRY_RESILIENCE.md](../../plan/02-activos/PLAN_RETRY_RESILIENCE.md)
- [ ] 📓 **OneNote actualizado**: Este documento
- [ ] 🔧 **Modulo de retry**: `src/utils/retry.py`
- [ ] 🧪 **Tests de retry**: `tests/utils/test_retry.py`

## 🔗 URLs

### 📊 Repositorio
- [GitHub - TelegramBotIA](https://github.com/Roque98/TelegramBotIA)

### 🖥️ Ramas Git
- `feature/retry-resilience` - Rama para este trabajo

## 🔧 Informacion Tecnica

### 💻 Puntos de Fallo Actuales (Sin Retry)

| Componente | Archivo | Errores Transitorios | Retry Actual |
|------------|---------|----------------------|--------------|
| OpenAI API | `src/agents/react/agent.py` | RateLimitError, APIConnectionError, Timeout | ❌ |
| OpenAI Provider | `src/agent/providers/openai_provider.py` | APIError, RateLimitError | ❌ |
| Anthropic Provider | `src/agent/providers/anthropic_provider.py` | APIError, RateLimitError | ❌ |
| DB execute_query | `src/database/connection.py` | OperationalError, TimeoutError | ❌ |
| DB execute_non_query | `src/database/connection.py` | OperationalError, TimeoutError | ❌ |
| DB get_schema | `src/database/connection.py` | OperationalError, TimeoutError | ❌ |

### 💻 Estrategia de Retry

```python
# LLM calls
@retry(
    stop=stop_after_attempt(3),           # Max 3 intentos
    wait=wait_exponential(min=2, max=30), # 2s -> 4s -> 8s...
    retry=retry_if_exception_type((
        openai.RateLimitError,
        openai.APIConnectionError,
        openai.APITimeoutError,
    ))
)

# Database calls
@retry(
    stop=stop_after_attempt(3),           # Max 3 intentos
    wait=wait_exponential(min=1, max=15), # 1s -> 2s -> 4s...
    retry=retry_if_exception_type((
        OperationalError,
        SQLTimeoutError,
    ))
)
```

### 💻 Configuracion en settings.py
```python
# Retry settings
RETRY_LLM_MAX_ATTEMPTS: int = 3
RETRY_LLM_MIN_WAIT: int = 2      # segundos
RETRY_LLM_MAX_WAIT: int = 30     # segundos
RETRY_DB_MAX_ATTEMPTS: int = 3
RETRY_DB_MIN_WAIT: int = 1       # segundos
RETRY_DB_MAX_WAIT: int = 15      # segundos
```

### 🗄️ Dependencias
- `tenacity==9.0.0` (ya instalada, solo falta importar)

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
