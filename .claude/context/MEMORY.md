# Sistema de Memoria

## Arquitectura de Memoria en Capas

```
┌─────────────────────────────────────────────────────────────┐
│                    WORKING MEMORY                           │
│                  (Corto plazo - RAM)                        │
│                                                             │
│  ConversationHistory                                        │
│  - Últimos 3-10 mensajes                                    │
│  - Se pierde al reiniciar                                   │
│  - Acceso inmediato                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   LONG-TERM MEMORY                          │
│                 (Largo plazo - Base de datos)               │
│                                                             │
│  UserMemoryProfiles                                         │
│  - Resúmenes generados por LLM                              │
│  - Persiste entre sesiones                                  │
│  - Se actualiza cada N interacciones                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes

### ConversationHistory (Working Memory)

**Archivo**: `src/agent/conversation_history.py`

```python
class ConversationHistory:
    def __init__(self, max_messages: int = 10):
        self.messages: list[dict] = []
        self.max_messages = max_messages

    def add_user_message(self, content: str)
    def add_bot_response(self, content: str)
    def get_context(self) -> str
    def clear(self)
```

**Estructura de mensaje**:
```python
{
    "role": "user" | "assistant",
    "content": "texto del mensaje",
    "timestamp": datetime
}
```

---

### MemoryManager (Orquestador)

**Archivo**: `src/agent/memory/memory_manager.py`

```python
class MemoryManager:
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm_provider: LLMProvider,
        update_threshold: int = 10  # Actualizar cada N interacciones
    )

    async def get_memory_context(self, user_id: int) -> str
    async def record_interaction(
        self,
        user_id: int,
        query: str,
        response: str,
        query_type: str
    )
```

**Flujo de get_memory_context()**:
```
1. Verificar cache
   ├── Cache hit → Retornar cached
   └── Cache miss → Continuar

2. Obtener perfil de BD
   └── MemoryRepository.get_user_memory_profile()

3. Construir contexto
   └── MemoryInjector.build_context(profile)

4. Cachear resultado (TTL: 5 min)

5. Retornar contexto
```

**Flujo de record_interaction()**:
```
1. Guardar en LogOperaciones (siempre)

2. Incrementar contador de interacciones

3. ¿Contador >= threshold?
   ├── No → Terminar
   └── Sí → Actualizar memoria
         ├── Obtener últimas N interacciones
         ├── MemoryExtractor.generate_summary()
         ├── MemoryRepository.save_profile()
         └── Invalidar cache
```

---

### MemoryRepository (Persistencia)

**Archivo**: `src/agent/memory/memory_repository.py`

```python
@dataclass
class UserMemoryProfile:
    id_usuario: int
    resumen_contexto_laboral: Optional[str]   # "Trabaja en ventas..."
    resumen_temas_recientes: Optional[str]    # "Ha preguntado sobre..."
    resumen_historial_breve: Optional[str]    # "Usuario activo que..."
    num_interacciones: int
    ultima_actualizacion: datetime
    version: int

class MemoryRepository:
    async def get_user_memory_profile(self, user_id: int) -> Optional[UserMemoryProfile]
    async def save_memory_profile(self, profile: UserMemoryProfile)
    async def get_user_interactions(self, user_id: int, limit: int = 50) -> list[UserInteraction]
```

---

### MemoryExtractor (Generación de Resúmenes)

**Archivo**: `src/agent/memory/memory_extractor.py`

```python
class MemoryExtractor:
    def __init__(self, llm_provider: LLMProvider)

    async def generate_memory_summary(
        self,
        interactions: list[UserInteraction],
        previous_profile: Optional[UserMemoryProfile]
    ) -> UserMemoryProfile
```

**Prompt de extracción**:
```
Analiza las interacciones del usuario y genera resúmenes:

## Interacciones recientes
- [2024-01-15] "¿Ventas de enero?" → "Las ventas fueron $50,000"
- [2024-01-16] "¿Top vendedores?" → "Juan, María, Pedro"
...

## Genera:
1. Contexto laboral: ¿Qué área? ¿Qué consulta frecuentemente?
2. Temas recientes: ¿Qué ha preguntado últimamente?
3. Historial breve: Resumen general del usuario
```

---

### MemoryInjector (Inyección en Prompts)

**Archivo**: `src/agent/memory/memory_injector.py`

```python
class MemoryInjector:
    def build_context(self, profile: UserMemoryProfile) -> str
    def inject_into_prompt(self, prompt: str, profile: UserMemoryProfile) -> str
```

**Ejemplo de contexto generado**:
```
## Contexto del usuario
Este usuario trabaja en el área de ventas y frecuentemente
consulta sobre métricas de rendimiento y comparativas.

Últimamente ha preguntado sobre ventas mensuales y productos
más vendidos.

Es un usuario activo con 45 interacciones en el último mes.
```

---

## Tabla de Base de Datos

```sql
CREATE TABLE UserMemoryProfiles (
    idMemoryProfile INT PRIMARY KEY IDENTITY,
    idUsuario INT FK UNIQUE NOT NULL,
    resumenContextoLaboral NVARCHAR(MAX),
    resumenTemasRecientes NVARCHAR(MAX),
    resumenHistorialBreve NVARCHAR(MAX),
    numInteracciones INT DEFAULT 0,
    ultimaActualizacion DATETIME2 DEFAULT GETDATE(),
    fechaCreacion DATETIME2 DEFAULT GETDATE(),
    version INT DEFAULT 1
);
```

---

## Configuración

```python
# .env
ENABLE_MEMORY_SYSTEM=true
MEMORY_UPDATE_THRESHOLD=10      # Cada cuántas interacciones actualizar
MEMORY_CACHE_TTL=300            # TTL del cache en segundos
MEMORY_INTERACTIONS_LIMIT=50    # Cuántas interacciones analizar
```

---

## Flujo Completo

```
Usuario envía: "¿Cuántas ventas hubo ayer?"
    │
    ▼
LLMAgent.process_query()
    │
    ├── 1. Obtener contexto de memoria
    │      memory_manager.get_memory_context(user_id)
    │      │
    │      ├── Cache hit? → Usar cached
    │      │
    │      └── Cache miss?
    │           ├── repository.get_profile()
    │           ├── injector.build_context()
    │           └── Cachear
    │
    ├── 2. Clasificar query (con contexto de memoria)
    │      query_classifier.classify(query, memory_context)
    │
    ├── 3. Procesar (DATABASE/KNOWLEDGE/GENERAL)
    │      ...
    │
    └── 4. Registrar interacción (async)
           memory_manager.record_interaction()
           │
           ├── Guardar en LogOperaciones
           │
           └── ¿Threshold alcanzado?
                ├── No → Terminar
                └── Sí → Actualizar memoria
                     ├── Obtener interacciones
                     ├── extractor.generate_summary()
                     ├── repository.save_profile()
                     └── Invalidar cache
```

---

## Arquitectura Futura: MemoryAgent

En la migración a ReAct, la memoria se convertirá en un agente dedicado:

```python
class MemoryAgent:
    """Gestiona contexto del usuario."""

    async def get_context(self, user_id: str) -> UserContext
    async def record(self, event: ConversationEvent, response: AgentResponse)
    async def update_summary(self, user_id: str)
    async def extract_preferences(self, event: ConversationEvent)
```

**Mejoras planificadas**:
- Extracción automática de preferencias
- Memoria semántica con embeddings
- Búsqueda por similitud en historial
- Compresión progresiva de memoria antigua
