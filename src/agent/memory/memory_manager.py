"""
Gestor principal de memoria persistente.

Este módulo orquesta todo el sistema de memoria:
- Registra interacciones y decide cuándo actualizar
- Coordina extracción de resúmenes con LLM
- Gestiona caché de perfiles
- Proporciona contexto de memoria para prompts
"""
import logging
import asyncio
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from src.database.connection import DatabaseManager
from src.agent.providers.base_provider import LLMProvider
from .memory_repository import MemoryRepository, UserMemoryProfile
from .memory_extractor import MemoryExtractor
from .memory_injector import MemoryInjector

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Gestor principal de memoria persistente.

    Coordina:
    - Registro de interacciones
    - Generación de resúmenes con LLM
    - Caché de perfiles
    - Inyección en prompts
    """

    # Actualizar memoria cada N interacciones
    INTERACTIONS_THRESHOLD = 10

    # TTL de caché en minutos
    CACHE_TTL_MINUTES = 15

    def __init__(self, db_manager: DatabaseManager, llm_provider: LLMProvider):
        """
        Inicializar el gestor de memoria.

        Args:
            db_manager: Gestor de base de datos
            llm_provider: Proveedor de LLM para generación de resúmenes
        """
        self.repository = MemoryRepository(db_manager)
        self.extractor = MemoryExtractor(llm_provider)
        self.injector = MemoryInjector()

        # Caché: {user_id: (formatted_context, timestamp)}
        self._cache: Dict[int, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(minutes=self.CACHE_TTL_MINUTES)

        logger.info(
            f"MemoryManager inicializado "
            f"(threshold: {self.INTERACTIONS_THRESHOLD} interacciones, "
            f"cache TTL: {self.CACHE_TTL_MINUTES} min)"
        )

    async def record_interaction(self, user_id: int) -> None:
        """
        Registrar interacción y actualizar memoria si es necesario.

        Este método se llama DESPUÉS de responder al usuario (asíncrono).

        Flujo:
        1. Incrementar contador de interacciones
        2. Si contador % INTERACTIONS_THRESHOLD == 0:
           - Obtener últimas interacciones desde LogOperaciones
           - Generar nuevos resúmenes con LLM
           - Guardar perfil actualizado
           - Invalidar caché

        Args:
            user_id: ID del usuario

        Note:
            Los errores se loguean pero no se propagan para no afectar la
            experiencia del usuario.
        """
        try:
            logger.info(f"📝 record_interaction() llamado para usuario {user_id}")

            # 1. Incrementar contador
            new_count = self.repository.increment_interaction_count(user_id)

            logger.info(f"✅ Interacción registrada para usuario {user_id} (count: {new_count}/{self.INTERACTIONS_THRESHOLD})")

            # 2. Verificar si es tiempo de actualizar
            if new_count % self.INTERACTIONS_THRESHOLD == 0:
                logger.info(
                    f"🔄 Umbral alcanzado para usuario {user_id} "
                    f"({new_count} interacciones). Generando resúmenes..."
                )
                await self._update_memory_profile(user_id)

        except Exception as e:
            # No propagar error para no afectar al usuario
            logger.error(
                f"Error registrando interacción para usuario {user_id}: {e}",
                exc_info=True
            )

    async def _update_memory_profile(self, user_id: int) -> None:
        """
        Actualizar perfil de memoria generando nuevos resúmenes.

        Args:
            user_id: ID del usuario

        Raises:
            Exception: Si hay error en actualización (para logging)
        """
        try:
            # 1. Obtener interacciones recientes
            interactions = self.repository.get_recent_interactions(
                user_id,
                limit=self.INTERACTIONS_THRESHOLD
            )

            if not interactions:
                logger.warning(f"No hay interacciones para usuario {user_id}")
                return

            # 2. Obtener perfil existente
            existing_profile = self.repository.get_user_profile(user_id)

            # 3. Generar resúmenes con LLM
            logger.info(f"Generando resúmenes para usuario {user_id}...")
            updated_profile = await self.extractor.generate_memory_summary(
                interactions,
                existing_profile
            )

            # 4. Guardar en BD
            self.repository.save_user_profile(updated_profile)

            # 5. Resetear contador
            self.repository.reset_interaction_count(user_id)

            # 6. Invalidar caché
            self.invalidate_cache(user_id)

            logger.info(f"✅ Perfil de memoria actualizado para usuario {user_id}")

        except Exception as e:
            logger.error(
                f"Error actualizando perfil de memoria para usuario {user_id}: {e}",
                exc_info=True
            )
            raise

    def get_memory_context(self, user_id: int) -> str:
        """
        Obtener contexto de memoria para inyectar en prompt.

        Este método se llama ANTES de enviar al LLM.

        Usa caché para evitar lecturas frecuentes de BD.

        Args:
            user_id: ID del usuario

        Returns:
            String formateado para inyectar en prompt, o "" si no hay perfil

        Note:
            Los errores se loguean pero retornan "" para no bloquear al usuario.
        """
        try:
            # 1. Verificar caché
            if user_id in self._cache:
                cached_context, cached_at = self._cache[user_id]
                age = datetime.now() - cached_at

                if age < self._cache_ttl:
                    logger.debug(f"Cache hit para usuario {user_id} (age: {age.seconds}s)")
                    return cached_context
                else:
                    logger.debug(f"Cache expired para usuario {user_id}")

            # 2. Cache miss: leer de BD
            profile = self.repository.get_user_profile(user_id)

            if not profile or not profile.has_content():
                # Sin perfil o perfil vacío
                self._cache[user_id] = ("", datetime.now())
                return ""

            # 3. Formatear para prompt
            formatted = self.injector.format_for_prompt(profile)

            # 4. Truncar si es necesario
            formatted = self.injector.truncate_if_needed(formatted, max_tokens=300)

            # 5. Cachear
            self._cache[user_id] = (formatted, datetime.now())

            logger.debug(
                f"Contexto de memoria cargado para usuario {user_id} "
                f"({len(formatted)} chars)"
            )

            return formatted

        except Exception as e:
            logger.error(
                f"Error obteniendo contexto de memoria para usuario {user_id}: {e}",
                exc_info=True
            )
            # Retornar vacío para no bloquear al usuario
            return ""

    def invalidate_cache(self, user_id: int) -> None:
        """
        Invalidar caché de memoria para un usuario.

        Se llama después de actualizar el perfil.

        Args:
            user_id: ID del usuario
        """
        if user_id in self._cache:
            del self._cache[user_id]
            logger.debug(f"Caché invalidado para usuario {user_id}")

    def clear_all_cache(self) -> None:
        """
        Limpiar toda la caché.

        Útil para mantenimiento o testing.
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Caché completo limpiado ({cache_size} entradas)")

    def get_stats(self) -> dict:
        """
        Obtener estadísticas del gestor de memoria.

        Returns:
            Diccionario con estadísticas

        Example:
            >>> stats = memory_manager.get_stats()
            >>> print(stats)
            {
                'cache_size': 42,
                'threshold': 10,
                'cache_ttl_minutes': 15
            }
        """
        return {
            'cache_size': len(self._cache),
            'threshold': self.INTERACTIONS_THRESHOLD,
            'cache_ttl_minutes': self.CACHE_TTL_MINUTES
        }
