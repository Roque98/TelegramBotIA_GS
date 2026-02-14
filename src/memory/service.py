"""
Memory Service - Servicio principal de memoria para el ReAct Agent.

Coordina MemoryRepository y ContextBuilder para proporcionar
contexto de usuario con caching.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from src.agents.base.events import UserContext

from .context_builder import ContextBuilder
from .repository import MemoryRepository, UserProfile

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrada de cache con TTL."""

    context: UserContext
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: int = 300  # 5 minutos por defecto

    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado."""
        now = datetime.now(UTC)
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return now > expiry

    def time_remaining(self) -> float:
        """Retorna segundos restantes antes de expirar."""
        now = datetime.now(UTC)
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expiry - now).total_seconds()
        return max(0, remaining)


class MemoryService:
    """
    Servicio de memoria para el agente conversacional.

    Responsabilidades:
    - Obtener contexto de usuario con caching
    - Registrar interacciones
    - Actualizar resúmenes de memoria a largo plazo
    - Gestionar cache de contextos

    Example:
        ```python
        service = MemoryService(db_manager)
        context = await service.get_context("user_123")
        await service.record_interaction("user_123", "query", "response")
        ```
    """

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        context_builder: Optional[ContextBuilder] = None,
        cache_ttl_seconds: int = 300,
        max_cache_size: int = 1000,
        max_working_memory: int = 10,
    ):
        """
        Inicializa el servicio de memoria.

        Args:
            repository: Repository de memoria (se crea uno si no se proporciona)
            context_builder: Builder de contexto (se crea uno si no se proporciona)
            cache_ttl_seconds: Tiempo de vida del cache en segundos
            max_cache_size: Tamaño máximo del cache
            max_working_memory: Máximo de mensajes en working memory
        """
        self.repository = repository or MemoryRepository()
        self.context_builder = context_builder or ContextBuilder(
            repository=self.repository,
            max_working_memory=max_working_memory,
        )
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_size = max_cache_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

        logger.info(
            f"MemoryService inicializado "
            f"(cache_ttl={cache_ttl_seconds}s, max_cache={max_cache_size})"
        )

    async def get_context(
        self,
        user_id: str,
        include_working_memory: bool = True,
        include_long_term: bool = True,
        force_refresh: bool = False,
    ) -> UserContext:
        """
        Obtiene el contexto del usuario, usando cache si está disponible.

        Args:
            user_id: ID del usuario
            include_working_memory: Si incluir mensajes recientes
            include_long_term: Si incluir resumen de largo plazo
            force_refresh: Si forzar recarga desde BD

        Returns:
            UserContext con información del usuario
        """
        cache_key = f"{user_id}:{include_working_memory}:{include_long_term}"

        # Verificar cache
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for user {user_id}")
                return cached

        logger.debug(f"Cache miss for user {user_id}, building context")

        # Construir contexto
        context = await self.context_builder.build_context(
            user_id=user_id,
            include_working_memory=include_working_memory,
            include_long_term=include_long_term,
        )

        logger.info(
            f"[DEBUG] Context built for {user_id}: "
            f"name={context.display_name}, "
            f"working_memory={len(context.working_memory)} msgs, "
            f"has_summary={context.long_term_summary is not None}"
        )

        # Guardar en cache
        await self._add_to_cache(cache_key, context)

        return context

    async def get_minimal_context(self, user_id: str) -> UserContext:
        """
        Obtiene un contexto mínimo (solo ID y nombre).

        Útil para operaciones rápidas donde no se necesita historial.

        Args:
            user_id: ID del usuario

        Returns:
            UserContext mínimo
        """
        return await self.context_builder.build_minimal_context(user_id)

    async def record_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Registra una interacción usuario-agente.

        Args:
            user_id: ID del usuario
            query: Consulta del usuario
            response: Respuesta del agente
            metadata: Datos adicionales (tools usados, tiempo, etc.)

        Returns:
            True si se guardó correctamente
        """
        try:
            # Guardar interacción
            saved = await self.repository.save_interaction(
                user_id=user_id,
                query=query,
                response=response,
                metadata=metadata,
            )

            if saved:
                # Incrementar contador
                await self.repository.increment_interaction_count(user_id)

                # Invalidar cache para este usuario
                self._invalidate_user_cache(user_id)

                logger.debug(f"Interaction recorded for user {user_id}")

            return saved

        except Exception as e:
            logger.error(f"Error recording interaction for {user_id}: {e}")
            return False

    async def update_summary(
        self,
        user_id: str,
        new_summary: str,
    ) -> bool:
        """
        Actualiza el resumen de memoria a largo plazo.

        Args:
            user_id: ID del usuario
            new_summary: Nuevo resumen

        Returns:
            True si se actualizó correctamente
        """
        try:
            # Obtener perfil actual
            profile = await self.repository.get_profile(user_id)

            if not profile:
                # Crear perfil nuevo
                profile = UserProfile(
                    user_id=user_id,
                    long_term_summary=new_summary,
                )
            else:
                # Actualizar resumen existente
                profile.long_term_summary = new_summary
                profile.last_updated = datetime.now(UTC)

            # Guardar perfil
            saved = await self.repository.save_profile(profile)

            if saved:
                # Invalidar cache
                self._invalidate_user_cache(user_id)
                logger.info(f"Summary updated for user {user_id}")

            return saved

        except Exception as e:
            logger.error(f"Error updating summary for {user_id}: {e}")
            return False

    async def enrich_context(
        self,
        context: UserContext,
        additional_data: dict[str, Any],
    ) -> UserContext:
        """
        Enriquece un contexto existente con datos adicionales.

        Args:
            context: Contexto base
            additional_data: Datos para agregar

        Returns:
            Contexto enriquecido
        """
        return await self.context_builder.enrich_context(context, additional_data)

    def _get_from_cache(self, key: str) -> Optional[UserContext]:
        """Obtiene un contexto del cache si existe y no ha expirado."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.context
        elif entry:
            # Eliminar entrada expirada
            del self._cache[key]
        return None

    async def _add_to_cache(self, key: str, context: UserContext) -> None:
        """Agrega un contexto al cache."""
        async with self._lock:
            # Limpiar entradas expiradas si el cache está lleno
            if len(self._cache) >= self.max_cache_size:
                self._cleanup_cache()

            self._cache[key] = CacheEntry(
                context=context,
                ttl_seconds=self.cache_ttl_seconds,
            )

    def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalida todas las entradas de cache para un usuario."""
        keys_to_delete = [k for k in self._cache if k.startswith(f"{user_id}:")]
        for key in keys_to_delete:
            del self._cache[key]

        # También invalidar en el repository
        self.repository.invalidate_cache(user_id)

    def _cleanup_cache(self) -> None:
        """Elimina entradas expiradas del cache."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]

        # Si aún está lleno, eliminar las más antiguas
        if len(self._cache) >= self.max_cache_size:
            # Ordenar por tiempo de creación
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at,
            )
            # Eliminar el 25% más antiguo (mínimo 1)
            to_remove = max(1, len(sorted_keys) // 4)
            for key in sorted_keys[:to_remove]:
                del self._cache[key]

    def clear_cache(self) -> None:
        """Limpia todo el cache."""
        self._cache.clear()
        self.repository.clear_cache()
        logger.info("Memory cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Obtiene estadísticas del cache.

        Returns:
            Dict con estadísticas
        """
        expired = sum(1 for v in self._cache.values() if v.is_expired())
        active = len(self._cache) - expired

        return {
            "total_entries": len(self._cache),
            "active_entries": active,
            "expired_entries": expired,
            "max_size": self.max_cache_size,
            "ttl_seconds": self.cache_ttl_seconds,
        }

    async def health_check(self) -> bool:
        """
        Verifica que el servicio está funcionando.

        Returns:
            True si el servicio está sano
        """
        try:
            # Intentar obtener un contexto vacío
            context = await self.get_minimal_context("__health_check__")
            return context is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
