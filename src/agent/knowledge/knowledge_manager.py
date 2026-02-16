"""
Gestor de conocimiento empresarial.

Proporciona funcionalidades para buscar y acceder al conocimiento
institucional de la empresa.
"""
import logging
from typing import List, Optional, Dict, Tuple, Any
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

        Busca primero con filtro de categoría si se proporciona.
        Si no hay buenos resultados, busca en todas las categorías.

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

        # Detectar si se está preguntando por una categoría específica
        category_from_query = self._detect_category_in_query(query_lower)
        if category_from_query and not category_filter:
            logger.info(f"Detectada pregunta sobre categoría: {category_from_query.value}")
            return self.get_entries_by_category(category_from_query, top_k=top_k)

        # Buscar con filtro de categoría si se proporciona
        if category_filter:
            results = self._score_entries(query_lower, category_filter, top_k, min_score)
            if results:
                return results
            # Fallback: buscar en TODAS las categorías si la filtrada no dio resultados
            logger.info(
                f"Sin resultados en categoría '{category_filter.value}', "
                f"buscando en todas las categorías"
            )

        return self._score_entries(query_lower, None, top_k, min_score)

    def _score_entries(
        self,
        query_lower: str,
        category_filter: Optional[KnowledgeCategory],
        top_k: int,
        min_score: float,
    ) -> List[KnowledgeEntry]:
        """Score and rank entries against a query."""
        entries_to_search = (
            [entry for entry in self.knowledge_base if entry.category == category_filter]
            if category_filter
            else self.knowledge_base
        )

        scored_entries = []
        for entry in entries_to_search:
            score = self._calculate_score(query_lower, entry)
            if score >= min_score:
                scored_entries.append((score, entry))

        scored_entries.sort(reverse=True, key=lambda x: x[0])
        results = [entry for _, entry in scored_entries[:top_k]]

        logger.debug(
            f"Búsqueda: '{query_lower[:50]}' → {len(results)} resultados "
            f"(scores: {[round(s, 2) for s, _ in scored_entries[:top_k]]})"
        )

        return results

    @staticmethod
    def _stem_es(word: str) -> str:
        """
        Stemming ultra-simple para español.

        Reduce palabras a una raíz aproximada removiendo sufijos comunes.
        No es un stemmer completo, pero cubre los casos más frecuentes
        (solicitar/solicito/solicitud, vacaciones/vacación, etc.).
        """
        if len(word) <= 4:
            return word
        # Orden importa: probar sufijos más largos primero
        for suffix in (
            "aciones", "iciones", "amiento", "imiento",
            "acion", "icion", "ando", "endo", "iendo",
            "ador", "edor", "idor",
            "ante", "ente", "iente",
            "able", "ible",
            "ción", "sión",
            "idad", "edad",
            "mente",
            "amos", "emos", "imos",
            "aron", "eron", "ieron",
            "ando", "endo",
            "ado", "ido", "ido",
            "aba", "ían",
            "ar", "er", "ir",
            "as", "es", "os",
            "an", "en",
            "ón",
            "or",
            "al",
            "o", "a",
        ):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[: -len(suffix)]
        return word

    def _calculate_score(self, query: str, entry: KnowledgeEntry) -> float:
        """
        Calcular score de relevancia entre query y entrada.

        Estrategia de scoring:
        - Keywords match (exacto): +1.0 por keyword encontrado
        - Keywords match (stem): +0.7 por keyword con raíz común
        - Question similarity: +0.5 si hay palabras comunes significativas
        - Prioridad: multiplicador (1.0, 1.2, 1.5)

        Args:
            query: Query normalizada (lowercase)
            entry: Entrada de conocimiento

        Returns:
            Score de relevancia (mayor = más relevante)
        """
        score = 0.0
        query_words = set(query.split())
        query_stems = {self._stem_es(w) for w in query_words}

        # 1. Keyword matching (exacto + stem)
        for keyword in entry.keywords:
            kw = keyword.lower()
            if kw in query:
                # Match exacto de keyword como substring
                score += 1.0
            elif self._stem_es(kw) in query_stems:
                # Match por raíz (solicitar ~ solicito)
                score += 0.7

        # 2. Question similarity (palabras en común)
        question_words = set(entry.question.lower().split())

        stopwords = {
            'qué', 'cómo', 'cuál', 'dónde', 'cuándo', 'cuántos',
            'por', 'para', 'el', 'la', 'los', 'las', 'de', 'del',
            'en', 'a', 'un', 'una', 'es', 'son', 'se', 'si', 'no',
            'que', 'como', 'cual', 'donde', 'cuando', 'hay', 'mi',
            'su', 'al', 'con', 'sin', 'sobre', 'entre', 'más', 'o',
            'y', 'e', 'ni', 'pero', '¿', '?',
        }

        meaningful_query = query_words - stopwords
        meaningful_question = question_words - stopwords

        # Match exacto de palabras
        common_words = meaningful_query & meaningful_question
        score += len(common_words) * 0.5

        # Match por stems de palabras restantes
        remaining_query_stems = {self._stem_es(w) for w in meaningful_query - common_words}
        remaining_question_stems = {self._stem_es(w) for w in meaningful_question - common_words}
        stem_matches = remaining_query_stems & remaining_question_stems
        score += len(stem_matches) * 0.3

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

    def _detect_category_in_query(self, query_lower: str) -> Optional[KnowledgeCategory]:
        """
        Detectar si la query pregunta sobre una categoría específica.

        Args:
            query_lower: Query normalizada a minúsculas

        Returns:
            KnowledgeCategory si se detecta, None si no

        Example:
            >>> manager._detect_category_in_query("qué sabes sobre sistemas")
            <KnowledgeCategory.SISTEMAS: 'sistemas'>
        """
        # Palabras que indican pregunta sobre categoría
        category_indicators = [
            "qué sabes sobre",
            "que sabes sobre",
            "qué sabes de",
            "que sabes de",
            "información sobre",
            "informacion sobre",
            "háblame de",
            "hablame de",
            "cuéntame sobre",
            "cuentame sobre",
            "dime sobre",
            "dime de"
        ]

        # Verificar si hay un indicador de pregunta por categoría
        is_category_question = any(indicator in query_lower for indicator in category_indicators)

        if not is_category_question:
            return None

        # Mapeo de palabras clave a categorías
        category_keywords = {
            KnowledgeCategory.SISTEMAS: ["sistemas", "sistema", "aplicaciones", "aplicación", "software", "herramientas"],
            KnowledgeCategory.PROCESOS: ["procesos", "proceso", "procedimientos", "procedimiento", "flujos", "flujo"],
            KnowledgeCategory.POLITICAS: ["políticas", "politicas", "política", "politica", "normas", "norma", "reglas", "regla"],
            KnowledgeCategory.FAQS: ["faqs", "faq", "preguntas frecuentes", "preguntas comunes", "dudas"],
            KnowledgeCategory.CONTACTOS: ["contactos", "contacto", "teléfonos", "telefono", "correos", "correo"],
            KnowledgeCategory.RECURSOS_HUMANOS: ["recursos humanos", "rrhh", "rh", "personal", "empleados", "empleado"],
            KnowledgeCategory.BASE_DATOS: ["base datos", "base de datos", "bd", "tablas", "tabla", "datos"]
        }

        # Buscar qué categoría se menciona
        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category

        return None

    def get_entries_by_category(
        self,
        category: KnowledgeCategory,
        top_k: int = 5
    ) -> List[KnowledgeEntry]:
        """
        Obtener entradas de una categoría específica.

        Args:
            category: Categoría a buscar
            top_k: Número máximo de resultados

        Returns:
            Lista de entradas de la categoría (hasta top_k)

        Example:
            >>> entries = manager.get_entries_by_category(KnowledgeCategory.SISTEMAS, top_k=3)
            >>> all(e.category == KnowledgeCategory.SISTEMAS for e in entries)
            True
        """
        category_entries = [
            entry for entry in self.knowledge_base
            if entry.category == category
        ]

        # Ordenar por prioridad (mayor = más importante)
        category_entries.sort(key=lambda e: e.priority, reverse=True)

        result = category_entries[:top_k]

        logger.info(
            f"Obtenidas {len(result)} entradas de categoría {category.value} "
            f"(total en categoría: {len(category_entries)})"
        )

        return result

    def __repr__(self) -> str:
        """Representación del manager."""
        role_info = f", role={self.id_rol}" if self.id_rol is not None else ""
        return f"KnowledgeManager(entries={len(self.knowledge_base)}, source='{self.source}'{role_info})"
