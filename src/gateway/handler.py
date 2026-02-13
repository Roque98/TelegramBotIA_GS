"""
Main Handler - Orquesta el flujo de conversación.

Coordina:
- MessageGateway: Normalización de entrada
- MemoryService: Contexto del usuario
- ReActAgent: Procesamiento de consultas
"""

import asyncio
import logging
import time
from typing import Any, Optional, Protocol

from telegram import Update
from telegram.ext import ContextTypes

from src.agents.base.agent import AgentResponse
from src.agents.base.events import ConversationEvent, UserContext
from src.agents.react.agent import ReActAgent
from src.memory.service import MemoryService

from .message_gateway import MessageGateway

logger = logging.getLogger(__name__)


class FallbackAgent(Protocol):
    """Protocolo para agente de fallback (LLMAgent existente)."""

    async def process_query(self, query: str) -> str:
        """Procesa una consulta y retorna respuesta."""
        ...


class MainHandler:
    """
    Handler principal que orquesta el flujo de conversación.

    Flujo:
    1. Gateway normaliza el input
    2. MemoryService obtiene contexto del usuario
    3. ReActAgent procesa la consulta
    4. Se registra la interacción
    5. Se retorna la respuesta

    Example:
        ```python
        handler = MainHandler(
            react_agent=agent,
            memory_service=memory,
            fallback_agent=llm_agent,  # opcional
        )
        response = await handler.handle_telegram(update, context)
        ```
    """

    def __init__(
        self,
        react_agent: ReActAgent,
        memory_service: MemoryService,
        fallback_agent: Optional[FallbackAgent] = None,
        use_fallback_on_error: bool = True,
    ):
        """
        Inicializa el handler.

        Args:
            react_agent: Agente ReAct para procesamiento
            memory_service: Servicio de memoria
            fallback_agent: Agente de fallback (LLMAgent existente)
            use_fallback_on_error: Si usar fallback cuando ReAct falla
        """
        self.react_agent = react_agent
        self.memory = memory_service
        self.fallback_agent = fallback_agent
        self.use_fallback_on_error = use_fallback_on_error
        self.gateway = MessageGateway()

        logger.info(
            f"MainHandler inicializado "
            f"(fallback={'enabled' if fallback_agent else 'disabled'})"
        )

    async def handle_telegram(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> str:
        """
        Procesa un mensaje de Telegram.

        Args:
            update: Update de Telegram
            context: Contexto de Telegram

        Returns:
            Respuesta para enviar al usuario
        """
        start_time = time.perf_counter()

        try:
            # 1. Normalizar input
            event = self.gateway.from_telegram(update)

            # 2. Procesar
            response = await self._process_event(event)

            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Telegram message processed: user={event.user_id}, "
                f"success={response.success}, time={elapsed:.0f}ms"
            )

            return response.message if response.success else self._format_error(response)

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error handling Telegram message: {e} ({elapsed:.0f}ms)",
                exc_info=True,
            )
            return self._get_error_message()

    async def handle_api(
        self,
        user_id: str,
        text: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Procesa una solicitud de API.

        Args:
            user_id: ID del usuario
            text: Texto del mensaje
            session_id: ID de sesión opcional
            metadata: Metadata adicional

        Returns:
            AgentResponse con el resultado
        """
        start_time = time.perf_counter()

        try:
            # Crear evento
            event = self.gateway.from_api(
                user_id=user_id,
                text=text,
                session_id=session_id,
                metadata=metadata,
            )

            # Procesar
            response = await self._process_event(event)

            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"API request processed: user={user_id}, "
                f"success={response.success}, time={elapsed:.0f}ms"
            )

            return response

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Error handling API request: {e} ({elapsed:.0f}ms)",
                exc_info=True,
            )
            return AgentResponse.error_response(
                agent_name="main_handler",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def _process_event(self, event: ConversationEvent) -> AgentResponse:
        """
        Procesa un evento normalizado.

        Args:
            event: Evento a procesar

        Returns:
            AgentResponse con el resultado
        """
        # 1. Obtener contexto del usuario
        user_context = await self.memory.get_context(event.user_id)

        # 2. Ejecutar ReAct Agent
        try:
            response = await self.react_agent.execute(
                query=event.text,
                context=user_context,
            )
        except Exception as e:
            logger.error(f"ReActAgent error: {e}", exc_info=True)

            # Usar fallback si está configurado
            if self.use_fallback_on_error and self.fallback_agent:
                logger.info("Using fallback agent")
                response = await self._use_fallback(event.text, user_context)
            else:
                raise

        # 3. Registrar interacción (async, no bloqueante)
        if response.success:
            asyncio.create_task(
                self._record_interaction(event, response)
            )

        return response

    async def _use_fallback(
        self,
        query: str,
        context: UserContext,
    ) -> AgentResponse:
        """
        Usa el agente de fallback.

        Args:
            query: Consulta del usuario
            context: Contexto del usuario

        Returns:
            AgentResponse del fallback
        """
        start_time = time.perf_counter()

        try:
            message = await self.fallback_agent.process_query(query)
            elapsed = (time.perf_counter() - start_time) * 1000

            return AgentResponse.success_response(
                agent_name="fallback",
                message=message,
                execution_time_ms=elapsed,
                metadata={"used_fallback": True},
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.error(f"Fallback agent error: {e}", exc_info=True)

            return AgentResponse.error_response(
                agent_name="fallback",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def _record_interaction(
        self,
        event: ConversationEvent,
        response: AgentResponse,
    ) -> None:
        """
        Registra la interacción en memoria.

        Args:
            event: Evento original
            response: Respuesta del agente
        """
        try:
            await self.memory.record_interaction(
                user_id=event.user_id,
                query=event.text,
                response=response.message or "",
                metadata={
                    "channel": event.channel,
                    "agent": response.agent_name,
                    "steps_taken": response.steps_taken,
                    "execution_time_ms": response.execution_time_ms,
                    "correlation_id": event.correlation_id,
                },
            )
        except Exception as e:
            # No fallar si no se puede registrar
            logger.error(f"Error recording interaction: {e}")

    def _format_error(self, response: AgentResponse) -> str:
        """
        Formatea un error para mostrar al usuario.

        Args:
            response: Respuesta con error

        Returns:
            Mensaje formateado
        """
        return (
            "Lo siento, no pude procesar tu consulta correctamente. "
            "Por favor, intenta de nuevo o reformula tu pregunta."
        )

    def _get_error_message(self) -> str:
        """
        Retorna mensaje de error genérico.

        Returns:
            Mensaje de error
        """
        return (
            "Lo siento, ocurrió un error inesperado. "
            "Por favor, intenta de nuevo más tarde."
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Verifica el estado de todos los componentes.

        Returns:
            Dict con estado de cada componente
        """
        results = {
            "gateway": True,  # Siempre disponible
            "memory": False,
            "react_agent": False,
            "fallback_agent": None,
        }

        # Verificar memoria
        try:
            results["memory"] = await self.memory.health_check()
        except Exception as e:
            logger.error(f"Memory health check failed: {e}")

        # Verificar ReAct Agent
        try:
            results["react_agent"] = await self.react_agent.health_check()
        except Exception as e:
            logger.error(f"ReAct Agent health check failed: {e}")

        # Verificar fallback si existe
        if self.fallback_agent:
            results["fallback_agent"] = True  # Asumimos que funciona

        results["healthy"] = results["memory"] and results["react_agent"]

        return results
