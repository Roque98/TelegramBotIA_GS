"""
Context Builder - Construye UserContext desde datos de memoria.

Combina working memory (mensajes recientes) con long-term summary
para crear el contexto completo del usuario.
"""

import logging
from typing import Any, Optional

from src.agents.base.events import UserContext

from .repository import MemoryRepository, UserProfile

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Construye UserContext combinando diferentes fuentes de memoria.

    Responsabilidades:
    - Obtener perfil de usuario desde repository
    - Cargar mensajes recientes (working memory)
    - Combinar con resumen de largo plazo
    - Crear UserContext listo para el agente
    """

    def __init__(
        self,
        repository: MemoryRepository,
        max_working_memory: int = 10,
    ):
        """
        Inicializa el builder.

        Args:
            repository: Repository de memoria
            max_working_memory: Máximo de mensajes en working memory
        """
        self.repository = repository
        self.max_working_memory = max_working_memory
        logger.info(f"ContextBuilder inicializado (max_working_memory={max_working_memory})")

    async def build_context(
        self,
        user_id: str,
        include_working_memory: bool = True,
        include_long_term: bool = True,
    ) -> UserContext:
        """
        Construye el UserContext completo para un usuario.

        Args:
            user_id: ID del usuario
            include_working_memory: Si incluir mensajes recientes
            include_long_term: Si incluir resumen de largo plazo

        Returns:
            UserContext con toda la información disponible
        """
        logger.debug(f"Building context for user {user_id}")

        # Obtener perfil
        profile = await self.repository.get_profile(user_id)

        # Obtener working memory
        working_memory = []
        if include_working_memory:
            working_memory = await self.repository.get_recent_messages(
                user_id=user_id,
                limit=self.max_working_memory,
            )

        # Construir contexto
        context = UserContext(
            user_id=user_id,
            display_name=profile.display_name if profile else "Usuario",
            roles=profile.roles if profile else [],
            preferences=profile.preferences if profile else {},
            working_memory=working_memory,
            long_term_summary=(
                profile.long_term_summary
                if profile and include_long_term
                else None
            ),
        )

        logger.debug(
            f"Context built for {user_id}: "
            f"{len(working_memory)} messages, "
            f"has_summary={context.long_term_summary is not None}"
        )

        return context

    async def build_minimal_context(self, user_id: str) -> UserContext:
        """
        Construye un contexto mínimo (solo ID y nombre).

        Útil para operaciones rápidas donde no se necesita historial.

        Args:
            user_id: ID del usuario

        Returns:
            UserContext mínimo
        """
        profile = await self.repository.get_profile(user_id)

        return UserContext(
            user_id=user_id,
            display_name=profile.display_name if profile else "Usuario",
            roles=profile.roles if profile else [],
        )

    async def enrich_context(
        self,
        context: UserContext,
        additional_data: dict[str, Any],
    ) -> UserContext:
        """
        Enriquece un contexto existente con datos adicionales.

        Args:
            context: Contexto base
            additional_data: Datos para agregar a preferences

        Returns:
            Nuevo UserContext con datos adicionales
        """
        # Crear nuevo contexto con datos adicionales
        return UserContext(
            user_id=context.user_id,
            display_name=context.display_name,
            roles=context.roles,
            preferences={**context.preferences, **additional_data},
            working_memory=context.working_memory,
            long_term_summary=context.long_term_summary,
            current_date=context.current_date,
        )

    @staticmethod
    def format_working_memory(messages: list[dict[str, Any]]) -> str:
        """
        Formatea working memory para incluir en prompts.

        Args:
            messages: Lista de mensajes

        Returns:
            String formateado
        """
        if not messages:
            return "Sin conversaciones recientes."

        formatted = []
        for msg in messages[-5:]:  # Solo los últimos 5
            role = "Usuario" if msg.get("role") == "user" else "Asistente"
            content = msg.get("content", "")[:200]  # Truncar
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)
