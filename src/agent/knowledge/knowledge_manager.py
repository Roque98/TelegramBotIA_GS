"""
Gestor de conocimiento empresarial.

Proporciona funcionalidades para buscar y acceder al conocimiento
institucional de la empresa.
"""
import logging
from typing import List, Optional, Dict, Tuple
from .company_knowledge import KnowledgeEntry  # get_knowledge_base, get_entries_by_category
from .knowledge_categories import KnowledgeCategory
from .knowledge_repository import KnowledgeRepository
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    Gestor de conocimiento empresarial.

    Proporciona búsqueda inteligente en la base de conocimiento
    usando keywords y scoring.

    Lee primero desde base de datos (abcmasplus) y usa fallback
    a código si la BD no está disponible.

    Examples:
        >>> manager = KnowledgeManager()
        >>> results = manager.search("¿Cómo pido vacaciones?")
        >>> print(results[0].answer)
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None, id_rol: Optional[int] = None):
        """
        Inicializar el gestor de conocimiento.

        Args:
            db_manager: Gestor de base de datos (opcional)
            id_rol: ID del rol del usuario para filtrar conocimiento (opcional)
        """
        self.repository = KnowledgeRepository(db_manager)
        self.knowledge_base = []
        self.source = "unknown"
        self.id_rol = id_rol  # ID del rol para filtrado de permisos

        # Intentar cargar desde BD primero
        try:
            if self.repository.health_check():
                # Cargar entradas filtradas por rol si se especifica
                if id_rol is not None:
                    self.knowledge_base = self.repository.get_all_entries_by_role(id_rol)
                    logger.info(
                        f"✅ KnowledgeManager inicializado desde BD para rol {id_rol} "
                        f"con {len(self.knowledge_base)} entradas"
                    )
                else:
                    self.knowledge_base = self.repository.get_all_entries()
                    logger.info(
                        f"✅ KnowledgeManager inicializado desde BD "
                        f"con {len(self.knowledge_base)} entradas (sin filtro de rol)"
                    )

                if self.knowledge_base:
                    self.source = "database"
                else:
                    # BD vacía o sin permisos
                    if id_rol is not None:
                        logger.warning(f"Rol {id_rol} no tiene acceso a ninguna categoría de conocimiento")
                    else:
                        raise ValueError("Base de datos sin entradas")
            else:
                # Health check falló
                raise ConnectionError("Base de datos no disponible")

        except Exception as e:
            # Solo usar BD - fallar si no está disponible
            logger.error(f"❌ No se pudo cargar conocimiento desde BD: {e}")
            self.knowledge_base = []
            self.source = "none"
            raise RuntimeError(f"Base de datos no disponible y fallback deshabilitado: {e}")

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.1,
        category_filter: Optional[KnowledgeCategory] = None
    ) -> List[KnowledgeEntry]:
        """
        Buscar entradas relevantes por keywords.

        Args:
            query: Consulta del usuario
            top_k: Número máximo de resultados
            min_score: Score mínimo para considerar relevante
            category_filter: Filtrar solo por esta categoría

        Returns:
            Lista de entradas más relevantes ordenadas por score

        Example:
            >>> results = manager.search("vacaciones", top_k=2)
            >>> len(results) <= 2
            True
        """
        query_lower = query.lower()
        scored_entries = []

        # Filtrar por categoría si se especifica (desde self.knowledge_base, no desde código)
        entries_to_search = (
            [entry for entry in self.knowledge_base if entry.category == category_filter]
            if category_filter
            else self.knowledge_base
        )

        for entry in entries_to_search:
            score = self._calculate_score(query_lower, entry)

            if score >= min_score:
                scored_entries.append((score, entry))

        # Ordenar por score descendente
        scored_entries.sort(reverse=True, key=lambda x: x[0])

        # Retornar top_k resultados
        results = [entry for _, entry in scored_entries[:top_k]]

        logger.debug(
            f"Búsqueda: '{query[:50]}...' → {len(results)} resultados "
            f"(scores: {[round(s, 2) for s, _ in scored_entries[:top_k]]})"
        )

        return results

    def _calculate_score(self, query: str, entry: KnowledgeEntry) -> float:
        """
        Calcular score de relevancia entre query y entrada.

        Estrategia de scoring:
        - Keywords match: +1.0 por keyword encontrado
        - Prioridad: multiplicador (1.0, 1.2, 1.5)
        - Question similarity: +0.5 si hay palabras comunes

        Args:
            query: Query normalizada (lowercase)
            entry: Entrada de conocimiento

        Returns:
            Score de relevancia (mayor = más relevante)
        """
        score = 0.0

        # 1. Keyword matching
        for keyword in entry.keywords:
            if keyword.lower() in query:
                score += 1.0

        # 2. Question similarity (palabras en común)
        query_words = set(query.split())
        question_words = set(entry.question.lower().split())
        common_words = query_words & question_words

        # Filtrar palabras comunes irrelevantes
        stopwords = {'qué', 'cómo', 'cuál', 'dónde', 'cuándo', 'por', 'para', 'el', 'la', 'los', 'las', 'de', 'en', 'a'}
        meaningful_common = common_words - stopwords

        score += len(meaningful_common) * 0.5

        # 3. Priority multiplier
        priority_multipliers = {
            1: 1.0,
            2: 1.2,
            3: 1.5
        }
        score *= priority_multipliers.get(entry.priority, 1.0)

        return score

    def get_context_for_llm(
        self,
        query: str,
        top_k: int = 2,
        include_metadata: bool = True
    ) -> str:
        """
        Generar contexto de conocimiento para agregar al prompt del LLM.

        Args:
            query: Consulta del usuario
            top_k: Número de entradas a incluir
            include_metadata: Si incluir categoría y prioridad

        Returns:
            String formateado para agregar al prompt

        Example:
            >>> context = manager.get_context_for_llm("vacaciones")
            >>> "CONOCIMIENTO INSTITUCIONAL" in context
            True
        """
        relevant = self.search(query, top_k=top_k)

        if not relevant:
            return ""

        context = "📚 CONOCIMIENTO INSTITUCIONAL RELEVANTE:\n\n"

        for idx, entry in enumerate(relevant, 1):
            if include_metadata:
                category_name = KnowledgeCategory.get_display_name(entry.category)
                context += f"**{idx}. [{category_name}] {entry.question}**\n"
            else:
                context += f"**{idx}. {entry.question}**\n"

            context += f"{entry.answer}\n\n"

            if entry.related_commands:
                commands_str = ", ".join(entry.related_commands)
                context += f"_Comandos relacionados: {commands_str}_\n\n"

        context += "---\n\n"

        return context

    def get_all_categories(self) -> List[KnowledgeCategory]:
        """Obtener todas las categorías disponibles."""
        return KnowledgeCategory.get_all()

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la base de conocimiento.

        Returns:
            Diccionario con estadísticas

        Example:
            >>> stats = manager.get_stats()
            >>> stats['total_entries'] > 0
            True
        """
        stats = {
            'total_entries': len(self.knowledge_base),
            'categories': {},
            'priority_distribution': {1: 0, 2: 0, 3: 0}
        }

        for entry in self.knowledge_base:
            # Contar por categoría
            category_name = entry.category.value
            stats['categories'][category_name] = stats['categories'].get(category_name, 0) + 1

            # Contar por prioridad
            stats['priority_distribution'][entry.priority] += 1

        return stats

    def find_by_keywords(self, keywords: List[str]) -> List[KnowledgeEntry]:
        """
        Buscar entradas que contengan cualquiera de los keywords.

        Args:
            keywords: Lista de keywords a buscar

        Returns:
            Lista de entradas que coinciden
        """
        matching_entries = []

        for entry in self.knowledge_base:
            for keyword in keywords:
                if keyword.lower() in [k.lower() for k in entry.keywords]:
                    matching_entries.append(entry)
                    break  # No agregar duplicados

        return matching_entries

    def get_high_priority_entries(self) -> List[KnowledgeEntry]:
        """Obtener entradas de alta prioridad (útil para FAQs destacadas)."""
        return [entry for entry in self.knowledge_base if entry.priority >= 2]

    def get_source(self) -> str:
        """
        Obtener la fuente de datos actual.

        Returns:
            'database' si está usando BD, 'code' si está usando código
        """
        return self.source

    def reload_from_database(self) -> bool:
        """
        Intentar recargar datos desde la base de datos.

        Útil si la BD no estaba disponible al iniciar pero ahora sí.

        Returns:
            True si se recargó exitosamente desde BD
        """
        try:
            if self.repository.health_check():
                entries = self.repository.get_all_entries()
                if entries:
                    self.knowledge_base = entries
                    self.source = "database"
                    logger.info(
                        f"✅ Conocimiento recargado desde BD: {len(entries)} entradas"
                    )
                    return True
            return False
        except Exception as e:
            logger.error(f"Error al recargar desde BD: {e}")
            return False

    def __repr__(self) -> str:
        """Representación del manager."""
        role_info = f", role={self.id_rol}" if self.id_rol is not None else ""
        return f"KnowledgeManager(entries={len(self.knowledge_base)}, source='{self.source}'{role_info})"
