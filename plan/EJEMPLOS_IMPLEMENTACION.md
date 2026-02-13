# Ejemplos de Implementación

## 1. BaseAgent y Contratos

```python
# src/agents/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")

class AgentResponse(BaseModel):
    """Respuesta estándar de cualquier agente"""
    success: bool
    data: dict | None = None
    message: str | None = None
    error: str | None = None
    agent_name: str
    execution_time_ms: float
    metadata: dict = {}

    @classmethod
    def ok(cls, agent: str, data: dict = None, message: str = None, **meta):
        return cls(
            success=True,
            data=data,
            message=message,
            agent_name=agent,
            execution_time_ms=0,
            metadata=meta
        )

    @classmethod
    def fail(cls, agent: str, error: str, **meta):
        return cls(
            success=False,
            error=error,
            agent_name=agent,
            execution_time_ms=0,
            metadata=meta
        )


class ConversationEvent(BaseModel):
    """Evento normalizado de cualquier canal"""
    event_id: str
    user_id: str
    channel: str  # telegram, whatsapp, api
    text: str
    timestamp: datetime
    correlation_id: str  # Para trazar conversación completa
    metadata: dict = {}


class UserContext(BaseModel):
    """Contexto del usuario para cualquier agente"""
    user_id: str
    display_name: str
    roles: list[str]
    preferences: dict
    working_memory: list[dict]  # Últimos mensajes
    long_term_summary: str | None


class BaseAgent(ABC):
    """Contrato base para todos los agentes"""

    name: str

    @abstractmethod
    async def execute(
        self,
        event: ConversationEvent,
        context: UserContext,
        **kwargs
    ) -> AgentResponse:
        """Ejecuta la lógica del agente"""
        pass

    async def health_check(self) -> bool:
        """Verifica que el agente esté funcionando"""
        return True
```

---

## 2. Event Bus Simple

```python
# src/events/bus.py
from typing import Callable, Awaitable
from collections import defaultdict
import asyncio

EventHandler = Callable[..., Awaitable[None]]

class EventBus:
    """
    Event bus simple en memoria.
    Para producción, reemplazar con Redis Pub/Sub.
    """

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler):
        """Suscribe un handler a un tipo de evento"""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        """Desuscribe un handler"""
        self._handlers[event_type].remove(handler)

    async def publish(self, event_type: str, event: dict):
        """Publica un evento a todos los suscriptores"""
        handlers = self._handlers.get(event_type, [])
        if handlers:
            await asyncio.gather(
                *[handler(event) for handler in handlers],
                return_exceptions=True  # No falla si un handler falla
            )

    async def publish_and_wait(self, event_type: str, event: dict):
        """Publica y espera respuesta (request-reply pattern)"""
        future = asyncio.Future()
        reply_event = f"{event_type}:reply:{event.get('event_id')}"

        async def reply_handler(response):
            future.set_result(response)
            self.unsubscribe(reply_event, reply_handler)

        self.subscribe(reply_event, reply_handler)
        await self.publish(event_type, event)

        return await asyncio.wait_for(future, timeout=30.0)


# Singleton global
event_bus = EventBus()
```

---

## 3. SupervisorAgent

```python
# src/agents/supervisor.py
from .base import BaseAgent, AgentResponse, ConversationEvent, UserContext
from ..events.bus import event_bus
import time

class SupervisorAgent:
    """
    Orquestador central. No contiene lógica de negocio.
    Solo decide qué agente debe actuar y coordina.
    """

    def __init__(
        self,
        classifier: "ClassifierAgent",
        guardrail: "GuardrailAgent",
        memory: "MemoryAgent",
        agents: dict[str, BaseAgent]
    ):
        self.classifier = classifier
        self.guardrail = guardrail
        self.memory = memory
        self.agents = agents  # {"database": DatabaseAgent, "knowledge": KnowledgeAgent, ...}

    async def handle(self, event: ConversationEvent) -> AgentResponse:
        start = time.perf_counter()

        # 1. Obtener contexto del usuario
        context = await self.memory.get_context(event.user_id)

        # 2. Clasificar intención
        intent = await self.classifier.classify(event, context)

        # Emitir evento de clasificación
        await event_bus.publish("intent.classified", {
            "event_id": event.event_id,
            "user_id": event.user_id,
            "intent_type": intent.type,
            "confidence": intent.confidence
        })

        # 3. Validar con guardrails
        validation = await self.guardrail.validate(event, intent, context)
        if not validation.allowed:
            return AgentResponse.fail(
                agent="supervisor",
                error=validation.reason or "Operación no permitida"
            )

        # 4. Manejar clarificación si es necesario
        if intent.requires_clarification:
            return AgentResponse.ok(
                agent="supervisor",
                message=intent.clarification_question,
                metadata={"awaiting_clarification": True}
            )

        # 5. Delegar al agente especialista
        agent = self.agents.get(intent.suggested_agent)
        if not agent:
            return AgentResponse.fail(
                agent="supervisor",
                error=f"Agente '{intent.suggested_agent}' no encontrado"
            )

        response = await agent.execute(event, context, intent=intent)

        # 6. Actualizar memoria (async, no bloquea la respuesta)
        asyncio.create_task(
            self.memory.record(event, response)
        )

        # 7. Emitir evento de respuesta
        await event_bus.publish("response.sent", {
            "event_id": event.event_id,
            "user_id": event.user_id,
            "agent_used": response.agent_name,
            "success": response.success
        })

        elapsed = (time.perf_counter() - start) * 1000
        response.execution_time_ms = elapsed

        return response
```

---

## 4. ClassifierAgent

```python
# src/agents/classifier.py
from pydantic import BaseModel
from typing import Literal, Optional
from .base import BaseAgent, ConversationEvent, UserContext

class Intent(BaseModel):
    """Resultado de la clasificación"""
    type: Literal["database", "knowledge", "chitchat", "tool", "clarification"]
    confidence: float
    entities: dict = {}
    suggested_agent: str
    requires_clarification: bool = False
    clarification_question: Optional[str] = None


class ClassifierAgent(BaseAgent):
    """
    Un solo punto de clasificación de intención.
    Reemplaza QueryClassifier + ToolSelector.
    """

    name = "classifier"

    def __init__(self, llm_gateway, knowledge_retriever):
        self.llm = llm_gateway
        self.knowledge = knowledge_retriever

    async def classify(
        self,
        event: ConversationEvent,
        context: UserContext
    ) -> Intent:
        # Buscar si hay conocimiento relevante
        knowledge_hits = await self.knowledge.quick_search(
            event.text,
            user_roles=context.roles,
            limit=3
        )

        prompt = f"""
Analiza la siguiente consulta del usuario y clasifica su intención.

## Contexto del usuario
- Nombre: {context.display_name}
- Roles: {', '.join(context.roles)}
- Resumen de conversaciones previas: {context.long_term_summary or 'Primera interacción'}

## Últimos mensajes
{self._format_memory(context.working_memory)}

## Consulta actual
"{event.text}"

## Conocimiento relevante encontrado
{self._format_knowledge(knowledge_hits) if knowledge_hits else 'Ninguno'}

## Instrucciones
Clasifica la intención:
- "database": Consulta que requiere buscar en la base de datos (ventas, productos, clientes, etc.)
- "knowledge": Pregunta que puede responderse con el conocimiento disponible
- "chitchat": Conversación casual, saludos, despedidas
- "tool": Solicita ejecutar una acción específica (enviar mensaje, generar reporte, etc.)
- "clarification": La consulta es ambigua y necesitas más información

Responde en JSON con el formato Intent.
"""

        return await self.llm.generate_structured(
            prompt=prompt,
            schema=Intent,
            temperature=0.1  # Baja creatividad para clasificación
        )

    def _format_memory(self, messages: list[dict]) -> str:
        if not messages:
            return "Sin mensajes previos"
        return "\n".join([
            f"- {m['role']}: {m['content'][:100]}..."
            for m in messages[-5:]  # Últimos 5
        ])

    def _format_knowledge(self, hits: list) -> str:
        return "\n".join([
            f"- [{h.category}] {h.title}: {h.content[:200]}..."
            for h in hits
        ])
```

---

## 5. DatabaseAgent con Pipeline

```python
# src/agents/database/agent.py
from ..base import BaseAgent, AgentResponse, ConversationEvent, UserContext
from .sql_generator import SQLGenerator
from .sql_validator import SQLValidator
from .result_formatter import ResultFormatter
from dataclasses import dataclass
from typing import Any

@dataclass
class PipelineState:
    """Estado que fluye a través del pipeline"""
    event: ConversationEvent
    context: UserContext
    intent: Any
    sql: str | None = None
    validation_result: dict | None = None
    query_result: list[dict] | None = None
    formatted_response: str | None = None
    error: str | None = None


class DatabaseAgent(BaseAgent):
    """
    Especialista en consultas a base de datos.
    Pipeline: Generar SQL → Validar → Ejecutar → Formatear
    """

    name = "database"

    def __init__(self, llm_gateway, db_pool, schema_provider):
        self.llm = llm_gateway
        self.db = db_pool
        self.schema = schema_provider
        self.generator = SQLGenerator(llm_gateway, schema_provider)
        self.validator = SQLValidator()
        self.formatter = ResultFormatter(llm_gateway)

    async def execute(
        self,
        event: ConversationEvent,
        context: UserContext,
        **kwargs
    ) -> AgentResponse:
        state = PipelineState(
            event=event,
            context=context,
            intent=kwargs.get("intent")
        )

        # Pipeline secuencial
        pipeline_steps = [
            ("generate_sql", self._generate_sql),
            ("validate_sql", self._validate_sql),
            ("execute_sql", self._execute_sql),
            ("format_response", self._format_response),
        ]

        for step_name, step_fn in pipeline_steps:
            try:
                state = await step_fn(state)
                if state.error:
                    return AgentResponse.fail(
                        agent=self.name,
                        error=state.error,
                        metadata={"failed_step": step_name}
                    )
            except Exception as e:
                return AgentResponse.fail(
                    agent=self.name,
                    error=f"Error en {step_name}: {str(e)}",
                    metadata={"failed_step": step_name}
                )

        return AgentResponse.ok(
            agent=self.name,
            message=state.formatted_response,
            data={"rows": state.query_result, "sql": state.sql}
        )

    async def _generate_sql(self, state: PipelineState) -> PipelineState:
        schema = await self.schema.get_relevant_schema(state.event.text)
        state.sql = await self.generator.generate(
            query=state.event.text,
            schema=schema,
            context=state.context
        )
        return state

    async def _validate_sql(self, state: PipelineState) -> PipelineState:
        result = self.validator.validate(state.sql)
        if not result.is_valid:
            state.error = f"SQL no válido: {result.reason}"
        state.validation_result = result.model_dump()
        return state

    async def _execute_sql(self, state: PipelineState) -> PipelineState:
        async with self.db.acquire() as conn:
            rows = await conn.fetch(state.sql)
            state.query_result = [dict(row) for row in rows]
        return state

    async def _format_response(self, state: PipelineState) -> PipelineState:
        if not state.query_result:
            state.formatted_response = "No encontré resultados para tu consulta."
            return state

        state.formatted_response = await self.formatter.format(
            query=state.event.text,
            results=state.query_result,
            context=state.context
        )
        return state
```

---

## 6. GuardrailAgent

```python
# src/agents/guardrail/agent.py
from pydantic import BaseModel
from typing import Optional
from ..base import ConversationEvent, UserContext
import asyncio

class ValidationResult(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    warnings: list[str] = []


class GuardrailAgent:
    """
    Valida seguridad y políticas ANTES de ejecutar cualquier acción.
    """

    def __init__(self, auth_service, rate_limiter, content_policy):
        self.auth = auth_service
        self.rate_limiter = rate_limiter
        self.content_policy = content_policy

    async def validate(
        self,
        event: ConversationEvent,
        intent,
        context: UserContext
    ) -> ValidationResult:
        # Ejecutar todas las validaciones en paralelo
        checks = await asyncio.gather(
            self._check_auth(event, context),
            self._check_permissions(event, intent, context),
            self._check_rate_limit(event),
            self._check_content(event),
            return_exceptions=True
        )

        warnings = []
        for check in checks:
            if isinstance(check, Exception):
                return ValidationResult(
                    allowed=False,
                    reason=f"Error de validación: {str(check)}"
                )
            if not check.allowed:
                return check
            warnings.extend(check.warnings)

        return ValidationResult(allowed=True, warnings=warnings)

    async def _check_auth(self, event: ConversationEvent, context: UserContext) -> ValidationResult:
        if not context.user_id:
            return ValidationResult(
                allowed=False,
                reason="Usuario no autenticado. Usa /register para registrarte."
            )
        return ValidationResult(allowed=True)

    async def _check_permissions(self, event, intent, context) -> ValidationResult:
        # Verificar que el usuario tenga permisos para la acción
        required_permission = self._get_required_permission(intent)
        if required_permission and required_permission not in context.roles:
            return ValidationResult(
                allowed=False,
                reason=f"No tienes permiso para esta acción. Se requiere: {required_permission}"
            )
        return ValidationResult(allowed=True)

    async def _check_rate_limit(self, event: ConversationEvent) -> ValidationResult:
        is_allowed = await self.rate_limiter.check(event.user_id)
        if not is_allowed:
            return ValidationResult(
                allowed=False,
                reason="Has excedido el límite de consultas. Intenta de nuevo en unos minutos."
            )
        return ValidationResult(allowed=True)

    async def _check_content(self, event: ConversationEvent) -> ValidationResult:
        # Validar que el contenido no viole políticas
        violation = await self.content_policy.check(event.text)
        if violation:
            return ValidationResult(
                allowed=False,
                reason="Tu mensaje contiene contenido que no puedo procesar."
            )
        return ValidationResult(allowed=True)

    def _get_required_permission(self, intent) -> str | None:
        permission_map = {
            "database": "query_database",
            "tool": "execute_tools",
        }
        return permission_map.get(intent.type)
```

---

## 7. MemoryAgent

```python
# src/agents/memory/agent.py
from ..base import UserContext
from datetime import datetime, timedelta
from typing import Optional

class MemoryAgent:
    """
    Gestiona contexto del usuario con memoria en capas:
    - Working memory: Últimos N mensajes (corto plazo)
    - Long-term memory: Resumen generado por LLM (largo plazo)
    """

    def __init__(self, repository, llm_gateway, cache):
        self.repo = repository
        self.llm = llm_gateway
        self.cache = cache
        self.summary_threshold = 10  # Actualizar resumen cada N interacciones

    async def get_context(self, user_id: str) -> UserContext:
        # Intentar obtener de cache primero
        cached = await self.cache.get(f"context:{user_id}")
        if cached:
            return UserContext.model_validate(cached)

        # Construir contexto desde BD
        user = await self.repo.get_user(user_id)
        if not user:
            return self._empty_context(user_id)

        working_memory = await self.repo.get_recent_messages(
            user_id,
            limit=10
        )

        long_term = await self.repo.get_memory_summary(user_id)

        context = UserContext(
            user_id=user_id,
            display_name=user.display_name,
            roles=user.roles,
            preferences=user.preferences or {},
            working_memory=working_memory,
            long_term_summary=long_term
        )

        # Cachear por 5 minutos
        await self.cache.set(
            f"context:{user_id}",
            context.model_dump(),
            ttl=300
        )

        return context

    async def record(self, event, response):
        """Registra interacción y actualiza memoria si es necesario"""
        # 1. Guardar mensaje
        await self.repo.save_message(
            user_id=event.user_id,
            role="user",
            content=event.text,
            timestamp=event.timestamp
        )

        await self.repo.save_message(
            user_id=event.user_id,
            role="assistant",
            content=response.message,
            timestamp=datetime.utcnow()
        )

        # 2. Invalidar cache
        await self.cache.delete(f"context:{event.user_id}")

        # 3. Verificar si necesita actualizar resumen
        count = await self.repo.get_interaction_count_since_summary(event.user_id)
        if count >= self.summary_threshold:
            await self._update_summary(event.user_id)

        # 4. Extraer preferencias implícitas
        await self._extract_preferences(event)

    async def _update_summary(self, user_id: str):
        """Genera nuevo resumen de memoria a largo plazo"""
        messages = await self.repo.get_recent_messages(user_id, limit=50)
        current_summary = await self.repo.get_memory_summary(user_id)

        prompt = f"""
Genera un resumen actualizado del usuario basado en sus interacciones.

## Resumen anterior
{current_summary or 'Primera vez generando resumen'}

## Interacciones recientes
{self._format_messages(messages)}

## Instrucciones
Genera un resumen de 2-3 párrafos que capture:
1. Qué tipo de consultas hace frecuentemente
2. Sus preferencias de comunicación
3. Información relevante mencionada (rol, departamento, etc.)
4. Patrones de uso
"""

        new_summary = await self.llm.generate(prompt, max_tokens=500)
        await self.repo.save_memory_summary(user_id, new_summary)

    async def _extract_preferences(self, event):
        """Detecta preferencias implícitas en el mensaje"""
        # Esto podría usar LLM para extraer preferencias
        # Por ahora, detección simple por keywords
        text_lower = event.text.lower()

        preferences_detected = {}
        if "formato corto" in text_lower or "breve" in text_lower:
            preferences_detected["response_length"] = "short"
        if "detallado" in text_lower or "completo" in text_lower:
            preferences_detected["response_length"] = "detailed"

        if preferences_detected:
            await self.repo.update_preferences(event.user_id, preferences_detected)

    def _empty_context(self, user_id: str) -> UserContext:
        return UserContext(
            user_id=user_id,
            display_name="Usuario",
            roles=[],
            preferences={},
            working_memory=[],
            long_term_summary=None
        )

    def _format_messages(self, messages: list) -> str:
        return "\n".join([
            f"[{m['role']}] {m['content']}"
            for m in messages
        ])
```

---

## 8. Gateway Unificado

```python
# src/gateway/message_gateway.py
from ..agents.base import ConversationEvent
from datetime import datetime
import uuid

class MessageGateway:
    """
    Normaliza mensajes de cualquier canal a ConversationEvent.
    """

    def __init__(self, supervisor):
        self.supervisor = supervisor

    async def handle_telegram(self, update, context) -> str:
        """Procesa mensaje de Telegram"""
        event = ConversationEvent(
            event_id=str(uuid.uuid4()),
            user_id=str(update.effective_user.id),
            channel="telegram",
            text=update.message.text,
            timestamp=datetime.utcnow(),
            correlation_id=str(update.message.chat_id),
            metadata={
                "chat_id": update.message.chat_id,
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
            }
        )

        response = await self.supervisor.handle(event)
        return response.message or response.error

    async def handle_api(self, request: dict) -> dict:
        """Procesa mensaje de API REST"""
        event = ConversationEvent(
            event_id=str(uuid.uuid4()),
            user_id=request["user_id"],
            channel="api",
            text=request["message"],
            timestamp=datetime.utcnow(),
            correlation_id=request.get("session_id", str(uuid.uuid4())),
            metadata=request.get("metadata", {})
        )

        response = await self.supervisor.handle(event)

        return {
            "success": response.success,
            "message": response.message,
            "error": response.error,
            "data": response.data,
            "metadata": response.metadata
        }

    async def handle_webhook(self, payload: dict) -> dict:
        """Procesa webhook genérico (WhatsApp, Slack, etc.)"""
        channel = payload.get("channel", "webhook")
        normalizer = self._get_normalizer(channel)

        event = normalizer(payload)
        response = await self.supervisor.handle(event)

        return self._format_response(channel, response)

    def _get_normalizer(self, channel: str):
        normalizers = {
            "whatsapp": self._normalize_whatsapp,
            "slack": self._normalize_slack,
            "discord": self._normalize_discord,
        }
        return normalizers.get(channel, self._normalize_generic)
```

---

## 9. Configuración de Prompts (YAML)

```yaml
# src/config/prompts/classification.yaml
version: "1.0"

templates:
  main:
    description: "Clasificación principal de intención"
    model: "claude-3-5-sonnet"
    temperature: 0.1
    max_tokens: 500

    system: |
      Eres un clasificador de intención para un asistente empresarial.
      Tu trabajo es determinar qué tipo de acción requiere la consulta del usuario.

    user: |
      ## Contexto del usuario
      - Nombre: {{ user.display_name }}
      - Roles: {{ user.roles | join(', ') }}
      {% if user.long_term_summary %}
      - Historial: {{ user.long_term_summary }}
      {% endif %}

      ## Últimos mensajes
      {% for msg in working_memory[-5:] %}
      - {{ msg.role }}: {{ msg.content | truncate(100) }}
      {% endfor %}

      ## Consulta actual
      "{{ query }}"

      ## Conocimiento disponible
      {% if knowledge_hits %}
      {% for hit in knowledge_hits %}
      - [{{ hit.category }}] {{ hit.title }}
      {% endfor %}
      {% else %}
      Ninguno relevante encontrado
      {% endif %}

      Clasifica la intención del usuario.

    output_schema:
      type: object
      properties:
        type:
          type: string
          enum: [database, knowledge, chitchat, tool, clarification]
        confidence:
          type: number
          minimum: 0
          maximum: 1
        suggested_agent:
          type: string
        entities:
          type: object
        requires_clarification:
          type: boolean
        clarification_question:
          type: string
      required: [type, confidence, suggested_agent]
```

---

## 10. Testing de Agentes

```python
# tests/agents/test_classifier.py
import pytest
from src.agents.classifier import ClassifierAgent, Intent
from src.agents.base import ConversationEvent, UserContext
from unittest.mock import AsyncMock
from datetime import datetime

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate_structured = AsyncMock()
    return llm

@pytest.fixture
def mock_knowledge():
    knowledge = AsyncMock()
    knowledge.quick_search = AsyncMock(return_value=[])
    return knowledge

@pytest.fixture
def classifier(mock_llm, mock_knowledge):
    return ClassifierAgent(mock_llm, mock_knowledge)

@pytest.fixture
def sample_event():
    return ConversationEvent(
        event_id="test-123",
        user_id="user-456",
        channel="telegram",
        text="¿Cuántas ventas hubo ayer?",
        timestamp=datetime.utcnow(),
        correlation_id="conv-789"
    )

@pytest.fixture
def sample_context():
    return UserContext(
        user_id="user-456",
        display_name="Juan",
        roles=["ventas"],
        preferences={},
        working_memory=[],
        long_term_summary=None
    )


class TestClassifierAgent:

    @pytest.mark.asyncio
    async def test_classifies_database_query(
        self, classifier, mock_llm, sample_event, sample_context
    ):
        # Arrange
        mock_llm.generate_structured.return_value = Intent(
            type="database",
            confidence=0.95,
            suggested_agent="database",
            entities={"metric": "ventas", "time": "ayer"}
        )

        # Act
        result = await classifier.classify(sample_event, sample_context)

        # Assert
        assert result.type == "database"
        assert result.confidence > 0.9
        assert result.suggested_agent == "database"

    @pytest.mark.asyncio
    async def test_classifies_chitchat(
        self, classifier, mock_llm, sample_context
    ):
        # Arrange
        event = ConversationEvent(
            event_id="test-123",
            user_id="user-456",
            channel="telegram",
            text="Hola, ¿cómo estás?",
            timestamp=datetime.utcnow(),
            correlation_id="conv-789"
        )

        mock_llm.generate_structured.return_value = Intent(
            type="chitchat",
            confidence=0.98,
            suggested_agent="chitchat"
        )

        # Act
        result = await classifier.classify(event, sample_context)

        # Assert
        assert result.type == "chitchat"
        assert result.suggested_agent == "chitchat"

    @pytest.mark.asyncio
    async def test_uses_knowledge_when_available(
        self, classifier, mock_llm, mock_knowledge, sample_context
    ):
        # Arrange
        event = ConversationEvent(
            event_id="test-123",
            user_id="user-456",
            channel="telegram",
            text="¿Cuál es la política de devoluciones?",
            timestamp=datetime.utcnow(),
            correlation_id="conv-789"
        )

        mock_knowledge.quick_search.return_value = [
            {"title": "Política de devoluciones", "category": "FAQ"}
        ]

        mock_llm.generate_structured.return_value = Intent(
            type="knowledge",
            confidence=0.92,
            suggested_agent="knowledge"
        )

        # Act
        result = await classifier.classify(event, sample_context)

        # Assert
        assert result.type == "knowledge"
        mock_knowledge.quick_search.assert_called_once()
```

---

Estos ejemplos muestran cómo cada componente es:
1. **Independiente**: Se puede testear en aislamiento
2. **Tipado**: Usa Pydantic para contratos claros
3. **Async**: Aprovecha asyncio para concurrencia
4. **Extensible**: Fácil de agregar nuevos agentes o validadores
