"""
Clasificador de consultas de usuario.

Determina si una consulta requiere acceso a base de datos, conocimiento institucional,
o es una pregunta general.
"""
import logging
from enum import Enum
from typing import Optional
from ..providers.base_provider import LLMProvider
from ..prompts import get_default_manager
from ..knowledge import KnowledgeManager

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Tipos de consulta."""
    DATABASE = "database"
    GENERAL = "general"
    KNOWLEDGE = "knowledge"


class QueryClassifier:
    """Clasificador de consultas usando LLM."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_version: Optional[int] = None,
        knowledge_manager: Optional[KnowledgeManager] = None
    ):
        """
        Inicializar el clasificador.

        Args:
            llm_provider: Proveedor de LLM para clasificación
            prompt_version: Versión del prompt a usar (None = auto según A/B testing)
            knowledge_manager: Gestor de conocimiento institucional (opcional)
        """
        self.llm_provider = llm_provider
        self.prompt_manager = get_default_manager()
        self.prompt_version = prompt_version
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        # Cache para el último contexto de conocimiento
        self._last_knowledge_context = ""
        logger.info(
            f"Inicializado clasificador con proveedor: {llm_provider.get_provider_name()}, "
            f"knowledge_base: {len(self.knowledge_manager.knowledge_base)} entradas"
        )

    async def classify(self, user_query: str) -> QueryType:
        """
        Clasificar una consulta de usuario.

        Busca primero en el conocimiento institucional, luego clasifica
        entre DATABASE, KNOWLEDGE o GENERAL.

        Args:
            user_query: Consulta del usuario

        Returns:
            Tipo de consulta (KNOWLEDGE, DATABASE o GENERAL)
        """
        # 1. Buscar en conocimiento institucional
        # Usar min_score más bajo para no perder resultados relevantes
        knowledge_results = self.knowledge_manager.search(
            user_query,
            top_k=3,
            min_score=0.3  # Score mínimo más permisivo
        )

        # 2. Preparar contexto de conocimiento si hay resultados
        knowledge_context = ""
        knowledge_available = False

        if knowledge_results:
            knowledge_available = True
            knowledge_context = self.knowledge_manager.get_context_for_llm(
                user_query,
                top_k=3,
                include_metadata=False
            )
            # Guardar el contexto en cache para reutilizarlo
            self._last_knowledge_context = knowledge_context

        # 3. Usar el sistema de prompts con contexto de conocimiento
        # Si hay knowledge_manager, usar V3, si no, usar la versión especificada
        version_to_use = self.prompt_version
        if version_to_use is None and knowledge_available:
            version_to_use = 3  # Usar V3 si hay conocimiento disponible

        prompt = self.prompt_manager.get_prompt(
            'classification',
            version=version_to_use,
            user_query=user_query,
            knowledge_available=knowledge_available,
            knowledge_context=knowledge_context
        )

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=50)
            classification = response.strip().lower()

            # Determinar tipo basado en la respuesta
            if "knowledge" in classification:
                logger.info(
                    f"Consulta clasificada como KNOWLEDGE: '{user_query[:50]}...' "
                    f"(encontradas {len(knowledge_results)} entradas relevantes)"
                )
                return QueryType.KNOWLEDGE
            elif "database" in classification:
                logger.info(f"Consulta clasificada como DATABASE: '{user_query[:50]}...'")
                return QueryType.DATABASE
            else:
                # FALLBACK: Si el LLM clasifica como GENERAL pero hay conocimiento relevante,
                # forzar clasificación a KNOWLEDGE (especialmente para preguntas de categorías)
                if knowledge_results:
                    logger.warning(
                        f"LLM clasificó como GENERAL pero hay {len(knowledge_results)} entradas "
                        f"de conocimiento relevantes - Forzando KNOWLEDGE"
                    )
                    return QueryType.KNOWLEDGE

                logger.info(f"Consulta clasificada como GENERAL: '{user_query[:50]}...'")
                return QueryType.GENERAL

        except Exception as e:
            logger.error(f"Error clasificando consulta: {e}")
            # En caso de error, verificar si hay conocimiento relevante
            if knowledge_results:
                logger.warning("Asumiendo tipo KNOWLEDGE por error en clasificación (hay resultados)")
                return QueryType.KNOWLEDGE
            else:
                logger.warning("Asumiendo tipo DATABASE por error en clasificación")
                return QueryType.DATABASE

    async def is_database_query(self, user_query: str) -> bool:
        """
        Verificar si una consulta requiere base de datos.

        Args:
            user_query: Consulta del usuario

        Returns:
            True si requiere base de datos, False si no
        """
        query_type = await self.classify(user_query)
        return query_type == QueryType.DATABASE

    def get_knowledge_context(self, user_query: str, top_k: int = 2) -> str:
        """
        Obtener contexto de conocimiento para una consulta.

        Este método busca en la base de conocimiento y retorna
        el contexto formateado para incluir en la respuesta del LLM.

        Si hay un contexto cacheado de la última clasificación, lo retorna
        para evitar búsquedas duplicadas.

        Args:
            user_query: Consulta del usuario
            top_k: Número máximo de entradas a retornar

        Returns:
            Contexto formateado con conocimiento relevante, o string vacío si no hay resultados
        """
        # Si hay contexto cacheado de la última clasificación, usarlo
        if self._last_knowledge_context:
            logger.debug("Usando contexto de conocimiento cacheado")
            cached = self._last_knowledge_context
            # Limpiar el cache después de usarlo
            self._last_knowledge_context = ""
            return cached

        # Si no hay cache, buscar normalmente
        return self.knowledge_manager.get_context_for_llm(user_query, top_k=top_k)
