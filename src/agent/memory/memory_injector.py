"""
Inyector de memoria que formatea perfiles para inyectar en prompts del LLM.

Este módulo se encarga de formatear los resúmenes de memoria en un texto
legible y estructurado que se puede inyectar en los prompts del sistema.
"""
import logging
from typing import Optional
from .memory_repository import UserMemoryProfile

logger = logging.getLogger(__name__)


class MemoryInjector:
    """
    Inyecta contexto de memoria en prompts del LLM.

    Formatea los resúmenes de memoria en un texto estructurado con emojis
    y formato markdown que se puede agregar al system prompt.
    """

    @staticmethod
    def format_for_prompt(profile: UserMemoryProfile) -> str:
        """
        Formatear perfil de memoria para inyección en prompt.

        Genera un texto formateado con emojis y estructura clara que
        el LLM puede usar para personalizar sus respuestas.

        Args:
            profile: Perfil de memoria del usuario

        Returns:
            String formateado para inyectar en prompt, o "" si no hay contenido

        Example:
            >>> injector = MemoryInjector()
            >>> context = injector.format_for_prompt(profile)
            >>> print(context)
            📋 CONTEXTO DEL USUARIO:

            🏢 Contexto Laboral:
            Juan es Analista de Datos en Gerencia de Tecnología...

            🎯 Temas Recientes:
            En los últimos días ha consultado frecuentemente sobre...
        """
        if not profile or not profile.has_content():
            return ""

        sections = []

        # Contexto Laboral
        if profile.resumen_contexto_laboral:
            sections.append(
                f"🏢 Contexto Laboral:\n{profile.resumen_contexto_laboral}"
            )

        # Temas Recientes
        if profile.resumen_temas_recientes:
            sections.append(
                f"🎯 Temas Recientes:\n{profile.resumen_temas_recientes}"
            )

        # Historial Breve
        if profile.resumen_historial_breve:
            sections.append(
                f"📝 Historial:\n{profile.resumen_historial_breve}"
            )

        if not sections:
            return ""

        # Construir texto completo
        formatted = "📋 CONTEXTO DEL USUARIO:\n\n" + "\n\n".join(sections)

        logger.debug(f"Memoria formateada: {len(formatted)} caracteres")
        return formatted

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimar número de tokens de un texto.

        Usa aproximación simple: 1 token ≈ 4 caracteres

        Args:
            text: Texto a estimar

        Returns:
            Número estimado de tokens
        """
        return len(text) // 4

    @staticmethod
    def truncate_if_needed(
        formatted_text: str,
        max_tokens: int = 300
    ) -> str:
        """
        Truncar texto si excede límite de tokens.

        Si el texto es demasiado largo, prioriza:
        1. Temas recientes (más relevante para la conversación actual)
        2. Contexto laboral
        3. Historial

        Args:
            formatted_text: Texto formateado
            max_tokens: Límite máximo de tokens (default: 300)

        Returns:
            Texto truncado si es necesario
        """
        estimated_tokens = MemoryInjector.estimate_tokens(formatted_text)

        if estimated_tokens <= max_tokens:
            return formatted_text

        logger.warning(
            f"Memoria excede límite de tokens ({estimated_tokens} > {max_tokens}), "
            "truncando..."
        )

        # Estrategia simple: cortar caracteres al final
        max_chars = max_tokens * 4
        truncated = formatted_text[:max_chars] + "..."

        return truncated
