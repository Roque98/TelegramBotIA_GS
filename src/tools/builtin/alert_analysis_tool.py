"""
AlertAnalysisTool - Análisis de alertas activas de monitoreo PRTG.

Combina datos del evento actual con historial de tickets similares
y genera un diagnóstico mediante LLM.
"""
import re
import logging
from typing import Any, Dict, List

from src.tools.tool_base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ParameterType,
)
from src.tools.execution_context import ExecutionContext
from src.database.alert_repository import AlertRepository
from src.agent.prompts.alert_prompt_builder import AlertPromptBuilder

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "\n\n---\n"
    "_⚠️ Las sugerencias anteriores son orientativas. "
    "La decisión de ejecutar cualquier acción es responsabilidad exclusiva del operador. "
    "Valide siempre el impacto antes de actuar._"
)


class AlertAnalysisTool(BaseTool):
    """
    Tool para analizar alertas activas de monitoreo PRTG.

    El usuario puede preguntar de forma natural:
      - "analiza las alertas actuales"
      - "qué pasa con 10.80.191.22?"
      - "hay algo caído en producción?"
      - "dame un diagnóstico de los eventos Down"
    """

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="alert_analysis",
            description=(
                "Analiza alertas activas de monitoreo PRTG. "
                "Úsame cuando el usuario pregunta por alertas, eventos Down, "
                "sensores alertados, diagnóstico de incidentes o estado de equipos."
            ),
            commands=["/alertas"],
            category=ToolCategory.INTEGRATION,
            requires_auth=True,
            required_permissions=["/ia"],
            version="1.0.0",
            author="System",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ParameterType.STRING,
                description="Pregunta o filtro del usuario (IP, equipo, texto libre)",
                required=True,
                validation_rules={"min_length": 3, "max_length": 500},
            )
        ]

    async def execute(
        self,
        user_id: int,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """
        Obtiene eventos activos, historial de tickets y genera análisis con LLM.
        """
        is_valid, error = context.validate_required_components("llm_agent")
        if not is_valid:
            return ToolResult.error_result(
                error=error,
                user_friendly_error="El sistema de análisis no está disponible.",
            )

        query = params["query"]
        filtros = self._extraer_filtros(query)

        try:
            repo = AlertRepository()
            eventos = repo.get_active_events(**filtros)

            if not eventos:
                return ToolResult.success_result(
                    data="No encontré alertas activas con esos criterios."
                )

            # IP o equipo específico → 1 evento; sin filtro → top 3 más críticos
            tiene_filtro_especifico = bool(filtros.get("ip") or filtros.get("equipo"))
            eventos_a_analizar = eventos[:1] if tiene_filtro_especifico else self._top_criticos(eventos, n=3)

            builder = AlertPromptBuilder()
            respuestas = []

            for evento in eventos_a_analizar:
                ip = evento.get("IP", "")
                sensor = evento.get("Sensor", "")

                tickets = repo.get_historical_tickets(ip=ip, sensor=sensor)
                prompt = builder.build(evento, tickets, query)

                user_context = {
                    "telegram_chat_id": context.get_chat_id(),
                    "telegram_username": context.get_username(),
                    "id_usuario": user_id,
                }
                analisis = await context.llm_agent.process_query(prompt, user_context)
                respuestas.append(analisis + _DISCLAIMER)

            return ToolResult.success_result(data="\n\n".join(respuestas))

        except Exception as e:
            logger.error(f"Error en AlertAnalysisTool: {e}", exc_info=True)
            return ToolResult.error_result(
                error=str(e),
                user_friendly_error="No pude obtener el análisis de alertas en este momento.",
            )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _extraer_filtros(self, query: str) -> dict:
        """Extrae filtros de la pregunta del usuario."""
        ip_match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", query)
        palabras_down = ["down", "caído", "caida", "alerta", "error", "falla", "fallo"]
        return {
            "ip": ip_match.group(1) if ip_match else None,
            "equipo": None,
            "solo_down": any(p in query.lower() for p in palabras_down),
        }

    def _top_criticos(self, eventos: list, n: int) -> list:
        """Retorna los N eventos más críticos ordenados por Prioridad desc."""
        def prioridad(e):
            try:
                return int(e.get("Prioridad") or 0)
            except (ValueError, TypeError):
                return 0

        return sorted(eventos, key=prioridad, reverse=True)[:n]
