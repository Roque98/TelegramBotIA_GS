"""
ReAct Agent - Agente principal con razonamiento paso a paso.

Implementa el patrón ReAct (Reasoning + Acting) donde el agente
razona sobre qué hacer, ejecuta una acción, observa el resultado,
y repite hasta tener suficiente información.
"""

import json
import logging
import time
from typing import Any, Optional, Protocol

from ..base.agent import AgentResponse, BaseAgent
from ..base.events import UserContext
from ..base.exceptions import LLMException, MaxIterationsException, ToolException
from ..tools.base import ToolResult
from ..tools.registry import ToolRegistry
from .prompts import (
    build_continue_prompt,
    build_synthesis_prompt,
    build_system_prompt,
    build_user_prompt,
)
from .schemas import ActionType, ReActResponse
from .scratchpad import Scratchpad

# Importación opcional de observability (no falla si no está disponible)
try:
    from src.observability import get_tracer, get_metrics
    _OBSERVABILITY_AVAILABLE = True
except ImportError:
    _OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Protocolo para proveedores de LLM."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        response_format: Optional[type] = None,
        **kwargs: Any,
    ) -> str:
        """Genera una respuesta del LLM."""
        ...


class ReActAgent(BaseAgent):
    """
    Agente principal del sistema usando razonamiento ReAct.

    El agente decide cuántos pasos necesita según la complejidad
    de la consulta. Para saludos simples usa FINISH directamente,
    para consultas complejas puede ejecutar múltiples tools.

    Attributes:
        name: Nombre del agente ("react")
        llm: Proveedor de LLM
        tools: Registro de herramientas
        max_iterations: Máximo de iteraciones permitidas

    Example:
        >>> agent = ReActAgent(llm=openai_provider, tool_registry=registry)
        >>> response = await agent.execute("¿Cuántas ventas hubo ayer?", context)
        >>> print(response.message)
    """

    name = "react"

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
        temperature: float = 0.1,
    ):
        """
        Inicializa el agente ReAct.

        Args:
            llm: Proveedor de LLM (OpenAI, Anthropic, etc.)
            tool_registry: Registro de herramientas disponibles
            max_iterations: Número máximo de iteraciones
            temperature: Temperatura para generación del LLM
        """
        self.llm = llm
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self.temperature = temperature

        logger.info(
            f"ReActAgent inicializado (max_iterations={max_iterations}, "
            f"tools={len(tool_registry)})"
        )

    async def execute(
        self,
        query: str,
        context: UserContext,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Ejecuta el loop ReAct para responder una consulta.

        Args:
            query: Consulta del usuario
            context: Contexto del usuario
            **kwargs: Argumentos adicionales

        Returns:
            AgentResponse con la respuesta o error
        """
        start_time = time.perf_counter()
        scratchpad = Scratchpad(max_steps=self.max_iterations)

        # Iniciar tracing si está disponible
        tracer = get_tracer() if _OBSERVABILITY_AVAILABLE else None
        if tracer:
            tracer.start_trace(
                user_id=context.user_id,
                channel=kwargs.get("channel", "unknown"),
                metadata={"query_length": len(query)},
            )

        logger.info(f"Ejecutando ReAct para: '{query[:50]}...'")

        try:
            # Construir prompts base
            system_prompt = build_system_prompt(self.tools.get_tools_prompt())
            messages = [{"role": "system", "content": system_prompt}]

            while not scratchpad.is_full():
                # 1. Generar siguiente paso
                react_response = await self._generate_step(
                    query=query,
                    context=context,
                    scratchpad=scratchpad,
                    messages=messages,
                )

                # 2. Si es FINISH, retornar respuesta final
                if react_response.is_final():
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    steps = len(scratchpad) + 1
                    logger.info(
                        f"ReAct completado en {steps} pasos, "
                        f"{elapsed_ms:.2f}ms"
                    )

                    # Registrar métricas
                    if _OBSERVABILITY_AVAILABLE:
                        get_metrics().record_request(
                            channel=kwargs.get("channel", "unknown"),
                            duration_ms=elapsed_ms,
                            steps=steps,
                            success=True,
                        )
                        if tracer:
                            tracer.end_trace()

                    return AgentResponse.success_response(
                        agent_name=self.name,
                        message=react_response.final_answer or "",
                        execution_time_ms=elapsed_ms,
                        steps_taken=steps,
                        data={"scratchpad": scratchpad.to_dict()},
                    )

                # 3. Ejecutar tool
                observation = await self._execute_tool(
                    action=react_response.action,
                    action_input=react_response.action_input,
                )

                # Registrar uso de tool
                if _OBSERVABILITY_AVAILABLE:
                    get_metrics().record_tool_usage(react_response.action.value)

                # 4. Agregar al scratchpad
                scratchpad.add_step(
                    thought=react_response.thought,
                    action=react_response.action,
                    action_input=react_response.action_input,
                    observation=observation,
                )

                logger.debug(f"Paso {len(scratchpad)}: {react_response.action.value}")

            # Excedimos iteraciones - sintetizar respuesta parcial
            logger.warning(
                f"Max iterations reached ({self.max_iterations}), synthesizing partial"
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            partial_answer = await self._synthesize_partial(query, scratchpad)

            # Registrar métricas (partial se considera success)
            if _OBSERVABILITY_AVAILABLE:
                get_metrics().record_request(
                    channel=kwargs.get("channel", "unknown"),
                    duration_ms=elapsed_ms,
                    steps=len(scratchpad),
                    success=True,
                )
                if tracer:
                    tracer.end_trace()

            return AgentResponse.success_response(
                agent_name=self.name,
                message=partial_answer,
                execution_time_ms=elapsed_ms,
                steps_taken=len(scratchpad),
                metadata={
                    "partial": True,
                    "reason": "max_iterations_reached",
                },
                data={"scratchpad": scratchpad.to_dict()},
            )

        except MaxIterationsException as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Max iterations exception: {e}")
            self._record_error_metrics(kwargs, elapsed_ms, len(scratchpad), "MaxIterationsException", tracer)
            return AgentResponse.error_response(
                agent_name=self.name,
                error=str(e),
                execution_time_ms=elapsed_ms,
                steps_taken=len(scratchpad),
            )

        except LLMException as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"LLM error: {e}")
            self._record_error_metrics(kwargs, elapsed_ms, len(scratchpad), "LLMException", tracer)
            return AgentResponse.error_response(
                agent_name=self.name,
                error=f"Error del modelo: {e}",
                execution_time_ms=elapsed_ms,
                steps_taken=len(scratchpad),
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(f"Unexpected error in ReAct: {e}")
            self._record_error_metrics(kwargs, elapsed_ms, len(scratchpad), type(e).__name__, tracer)
            return AgentResponse.error_response(
                agent_name=self.name,
                error=str(e),
                execution_time_ms=elapsed_ms,
                steps_taken=len(scratchpad),
            )

    def _record_error_metrics(
        self,
        kwargs: dict,
        elapsed_ms: float,
        steps: int,
        error_type: str,
        tracer: Optional[Any],
    ) -> None:
        """Registra métricas de error."""
        if _OBSERVABILITY_AVAILABLE:
            get_metrics().record_request(
                channel=kwargs.get("channel", "unknown"),
                duration_ms=elapsed_ms,
                steps=steps,
                success=False,
                error_type=error_type,
            )
            if tracer:
                tracer.end_trace()

    async def _generate_step(
        self,
        query: str,
        context: UserContext,
        scratchpad: Scratchpad,
        messages: list[dict[str, str]],
    ) -> ReActResponse:
        """
        Genera el siguiente paso de razonamiento.

        Args:
            query: Consulta del usuario
            context: Contexto del usuario
            scratchpad: Historial de pasos
            messages: Historial de mensajes para el LLM

        Returns:
            ReActResponse con el siguiente paso

        Raises:
            LLMException: Si hay error en la generación
        """
        # Construir prompt de usuario
        if scratchpad.is_empty():
            prompt_context = context.to_prompt_context()
            logger.debug(f"[DEBUG] User context for prompt:\n{prompt_context}")
            user_prompt = build_user_prompt(
                query=query,
                user_context=prompt_context,
                scratchpad="",
            )
        else:
            last_obs = scratchpad.get_last_observation() or "No observation"
            user_prompt = build_continue_prompt(observation=last_obs)

        # Agregar al historial
        messages.append({"role": "user", "content": user_prompt})

        try:
            # Convertir mensajes a prompt string para el provider
            prompt = self._messages_to_prompt(messages)

            # Generar respuesta
            response_text = await self.llm.generate(prompt=prompt)

            # Parsear JSON
            react_response = self._parse_response(response_text)

            # Agregar respuesta al historial
            messages.append({"role": "assistant", "content": response_text})

            return react_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise LLMException(
                message=f"Invalid JSON response from LLM: {e}",
                provider="unknown",
            )
        except Exception as e:
            logger.error(f"Error generating step: {e}")
            raise LLMException(
                message=str(e),
                provider="unknown",
            )

    def _parse_response(self, response_text: str) -> ReActResponse:
        """
        Parsea la respuesta del LLM a ReActResponse.

        Args:
            response_text: Texto de respuesta del LLM

        Returns:
            ReActResponse parseado

        Raises:
            ValueError: Si el formato es inválido
        """
        # Intentar extraer JSON del texto
        text = response_text.strip()

        # Si está envuelto en ```json ... ```
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Parsear JSON
        data = json.loads(text)

        # Convertir action a ActionType
        action_str = data.get("action", "finish")
        action = ActionType.from_string(action_str)

        return ReActResponse(
            thought=data.get("thought", ""),
            action=action,
            action_input=data.get("action_input", {}),
            final_answer=data.get("final_answer"),
        )

    def _messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """
        Convierte lista de mensajes a un prompt string.

        Args:
            messages: Lista de mensajes con role y content

        Returns:
            Prompt formateado como string
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"[Sistema]\n{content}\n")
            elif role == "user":
                parts.append(f"[Usuario]\n{content}\n")
            elif role == "assistant":
                parts.append(f"[Asistente]\n{content}\n")

        return "\n".join(parts)

    async def _execute_tool(
        self,
        action: ActionType,
        action_input: dict[str, Any],
    ) -> str:
        """
        Ejecuta un tool y retorna la observación.

        Args:
            action: Tipo de acción/tool
            action_input: Parámetros del tool

        Returns:
            Observación como string

        Raises:
            ToolException: Si el tool falla
        """
        tool_name = action.value
        tool = self.tools.get(tool_name)

        if tool is None:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        try:
            logger.debug(f"Executing tool: {tool_name} with {action_input}")
            result: ToolResult = await tool.execute(**action_input)

            observation = result.to_observation()
            logger.debug(f"Tool result: {observation[:100]}...")

            return observation

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _synthesize_partial(
        self,
        query: str,
        scratchpad: Scratchpad,
    ) -> str:
        """
        Sintetiza una respuesta parcial cuando se exceden las iteraciones.

        Args:
            query: Consulta original
            scratchpad: Historial de pasos

        Returns:
            Respuesta parcial
        """
        try:
            synthesis_prompt = build_synthesis_prompt(
                query=query,
                scratchpad=scratchpad.to_prompt_format(),
                steps=len(scratchpad),
            )

            messages = [
                {"role": "system", "content": "Eres Amber, una asistente amigable."},
                {"role": "user", "content": synthesis_prompt},
            ]

            prompt = self._messages_to_prompt(messages)
            response_text = await self.llm.generate(prompt=prompt)

            # Intentar parsear como JSON
            try:
                react_response = self._parse_response(response_text)
                return react_response.final_answer or response_text
            except (json.JSONDecodeError, ValueError):
                # Si no es JSON, usar el texto directamente
                return response_text

        except Exception as e:
            logger.error(f"Error synthesizing partial: {e}")
            # Fallback con la información disponible
            observations = scratchpad.get_all_observations()
            if observations:
                return (
                    "Basándome en la información recopilada:\n\n"
                    + "\n".join(f"- {obs[:200]}" for obs in observations[-3:])
                )
            return "Lo siento, no pude completar la consulta. Por favor intenta reformularla."

    async def health_check(self) -> bool:
        """
        Verifica que el agente esté funcionando.

        Returns:
            True si está saludable
        """
        try:
            # Verificar que tenemos tools registrados
            if len(self.tools) == 0:
                logger.warning("No tools registered")
                return False

            # Podríamos verificar el LLM aquí también
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
