"""
Repositorio de conocimiento para lectura desde base de datos.

Proporciona acceso a la base de conocimiento almacenada en SQL Server
con fallback automático al código si hay errores de conexión.
"""
import json
import logging
from typing import List, Optional, Dict, Any
from src.database.connection import DatabaseManager
from .knowledge_categories import KnowledgeCategory
from .company_knowledge import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeRepository:
    """
    Repositorio para acceder a la base de conocimiento desde BD.

    Lee las entradas de conocimiento desde las tablas:
    - knowledge_categories
    - knowledge_entries

    Convierte los datos de BD a objetos KnowledgeEntry.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Inicializar el repositorio.

        Args:
            db_manager: Gestor de base de datos (opcional)
        """
        self.db_manager = db_manager or DatabaseManager()
        self._categories_cache: Optional[Dict[int, KnowledgeCategory]] = None

    def get_all_entries(self) -> List[KnowledgeEntry]:
        """
        Obtener todas las entradas de conocimiento activas desde BD.

        Returns:
            Lista de entradas de conocimiento

        Raises:
            Exception: Si hay error de conexión o consulta a BD
        """
        query = """
        SELECT
            e.id,
            e.category_id,
            e.question,
            e.answer,
            e.keywords,
            e.related_commands,
            e.priority,
            c.name as category_name
        FROM consolaMonitoreo.dbo.BotIA_knowledge_entries e
        INNER JOIN consolaMonitoreo.dbo.BotIA_knowledge_categories c ON e.category_id = c.id
        WHERE e.active = 1 AND c.active = 1
        ORDER BY e.priority DESC, e.id
        """

        try:
            results = self.db_manager.execute_query(query)
            entries = []

            for row in results:
                entry = self._row_to_entry(row)
                if entry:
                    entries.append(entry)

            logger.info(f"Cargadas {len(entries)} entradas desde BD")
            return entries

        except Exception as e:
            logger.error(f"Error al cargar entradas desde BD: {e}")
            raise

    def get_entries_by_category(
        self,
        category: KnowledgeCategory
    ) -> List[KnowledgeEntry]:
        """
        Obtener entradas de una categoría específica.

        Args:
            category: Categoría a filtrar

        Returns:
            Lista de entradas de la categoría
        """
        query = """
        SELECT
            e.id,
            e.category_id,
            e.question,
            e.answer,
            e.keywords,
            e.related_commands,
            e.priority,
            c.name as category_name
        FROM consolaMonitoreo.dbo.BotIA_knowledge_entries e
        INNER JOIN consolaMonitoreo.dbo.BotIA_knowledge_categories c ON e.category_id = c.id
        WHERE e.active = 1
            AND c.active = 1
            AND c.name = ?
        ORDER BY e.priority DESC, e.id
        """

        try:
            results = self.db_manager.execute_query(query, (category.name,))
            entries = []

            for row in results:
                entry = self._row_to_entry(row)
                if entry:
                    entries.append(entry)

            return entries

        except Exception as e:
            logger.error(f"Error al cargar entradas de categoría {category.name}: {e}")
            raise

    def search_entries(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar entradas usando el stored procedure de BD.

        Args:
            query: Texto de búsqueda
            top_k: Número máximo de resultados
            category: Filtro opcional de categoría

        Returns:
            Lista de resultados con scores
        """
        sql = "EXEC consolaMonitoreo.dbo.BotIA_sp_search_knowledge @query=?, @category=?, @top_k=?"

        try:
            results = self.db_manager.execute_query(
                sql,
                (query, category, top_k)
            )
            return results

        except Exception as e:
            logger.error(f"Error en búsqueda BD: {e}")
            raise

    def _row_to_entry(self, row: Dict[str, Any]) -> Optional[KnowledgeEntry]:
        """
        Convertir fila de BD a objeto KnowledgeEntry.

        Args:
            row: Fila de resultados de BD

        Returns:
            KnowledgeEntry o None si hay error
        """
        try:
            # Parsear categoría
            category_name = row.get('category_name')
            if not category_name:
                logger.warning(f"Entrada sin categoría: {row.get('id')}")
                return None

            try:
                category = KnowledgeCategory[category_name]
            except KeyError:
                logger.warning(f"Categoría desconocida: {category_name}")
                return None

            # Parsear keywords (JSON array)
            keywords_json = row.get('keywords', '[]')
            try:
                keywords = json.loads(keywords_json) if keywords_json else []
            except json.JSONDecodeError:
                logger.warning(f"Keywords JSON inválido en entrada {row.get('id')}")
                keywords = []

            # Parsear related_commands (JSON array, opcional)
            related_json = row.get('related_commands', '[]')
            try:
                related_commands = json.loads(related_json) if related_json else None
            except json.JSONDecodeError:
                logger.warning(f"Related commands JSON inválido en entrada {row.get('id')}")
                related_commands = None

            # Crear entrada
            return KnowledgeEntry(
                category=category,
                question=row.get('question', ''),
                answer=row.get('answer', ''),
                keywords=keywords,
                related_commands=related_commands,
                priority=row.get('priority', 1)
            )

        except Exception as e:
            logger.error(f"Error convirtiendo fila a entrada: {e}", exc_info=True)
            return None

    def get_categories(self) -> Dict[int, KnowledgeCategory]:
        """
        Obtener mapeo de category_id a KnowledgeCategory.

        Returns:
            Diccionario {category_id: KnowledgeCategory}
        """
        if self._categories_cache is not None:
            return self._categories_cache

        query = """
        SELECT id, name, display_name, icon
        FROM consolaMonitoreo.dbo.BotIA_knowledge_categories
        WHERE active = 1
        """

        try:
            results = self.db_manager.execute_query(query)
            categories = {}

            for row in results:
                try:
                    category = KnowledgeCategory[row['name']]
                    categories[row['id']] = category
                except KeyError:
                    logger.warning(f"Categoría desconocida en BD: {row['name']}")

            self._categories_cache = categories
            return categories

        except Exception as e:
            logger.error(f"Error al cargar categorías: {e}")
            raise

    def health_check(self) -> bool:
        """
        Verificar si la conexión a BD está funcionando.

        Returns:
            True si la BD responde correctamente
        """
        try:
            query = "SELECT COUNT(*) as total FROM consolaMonitoreo.dbo.BotIA_knowledge_entries WHERE active = 1"
            result = self.db_manager.execute_query(query)

            if result and len(result) > 0:
                total = result[0].get('total', 0)
                logger.debug(f"Health check OK: {total} entradas activas")
                return True
            return False

        except Exception as e:
            logger.warning(f"Health check falló: {e}")
            return False
