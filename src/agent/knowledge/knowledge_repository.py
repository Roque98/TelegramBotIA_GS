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
        self._role_permissions_cache: Dict[int, List[int]] = {}  # {id_rol: [id_categorias]}

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
        FROM abcmasplus.dbo.knowledge_entries e
        INNER JOIN abcmasplus.dbo.knowledge_categories c ON e.category_id = c.id
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
        # ✅ SEGURO: Usar parámetro SQL en lugar de string interpolation
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
        FROM abcmasplus.dbo.knowledge_entries e
        INNER JOIN abcmasplus.dbo.knowledge_categories c ON e.category_id = c.id
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
        category: Optional[str] = None,
        id_rol: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Buscar entradas usando el stored procedure de BD, filtradas por permisos de rol.

        Args:
            query: Texto de búsqueda
            top_k: Número máximo de resultados
            category: Filtro opcional de categoría
            id_rol: ID del rol del usuario (None = sin filtro de permisos)

        Returns:
            Lista de resultados con scores filtrados por permisos
        """
        # Si no hay rol, usar búsqueda normal
        if id_rol is None:
            sql = "EXEC abcmasplus.dbo.sp_search_knowledge @query=?, @category=?, @top_k=?"
            try:
                results = self.db_manager.execute_query(
                    sql,
                    (query, category, top_k)
                )
                return results
            except Exception as e:
                logger.error(f"Error en búsqueda BD: {e}")
                raise

        # Con rol: filtrar por categorías permitidas
        allowed_categories = self.get_allowed_categories_by_role(id_rol)

        if not allowed_categories:
            logger.warning(f"Rol {id_rol} no tiene acceso a ninguna categoría")
            return []

        # Primero hacer la búsqueda completa
        sql = "EXEC abcmasplus.dbo.sp_search_knowledge @query=?, @category=?, @top_k=?"

        try:
            # Pedir más resultados para compensar el filtrado
            results = self.db_manager.execute_query(
                sql,
                (query, category, top_k * 2)
            )

            # Filtrar resultados por categorías permitidas
            filtered_results = [
                result for result in results
                if result.get('category_id') in allowed_categories
            ]

            # Limitar a top_k después del filtrado
            filtered_results = filtered_results[:top_k]

            logger.debug(
                f"Búsqueda con permisos: {len(results)} resultados totales, "
                f"{len(filtered_results)} permitidos para rol {id_rol}"
            )

            return filtered_results

        except Exception as e:
            logger.error(f"Error en búsqueda BD con filtro de rol: {e}")
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
        FROM abcmasplus.dbo.knowledge_categories
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

    def get_categories_info(self, id_rol: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtener información completa de categorías desde BD, filtradas por permisos de rol.

        Args:
            id_rol: ID del rol del usuario (None = todas las categorías)

        Returns:
            Lista de diccionarios con {name, display_name, icon, entry_count}

        Example:
            [
                {'name': 'PROCESOS', 'display_name': 'Procesos', 'icon': '⚙️', 'entry_count': 5},
                {'name': 'POLITICAS', 'display_name': 'Políticas', 'icon': '📋', 'entry_count': 3}
            ]
        """
        # Si no hay rol, retornar todas las categorías
        if id_rol is None:
            query = """
            SELECT
                c.id,
                c.name,
                c.display_name,
                c.icon,
                COUNT(e.id) as entry_count
            FROM abcmasplus.dbo.knowledge_categories c
            LEFT JOIN abcmasplus.dbo.knowledge_entries e ON c.id = e.category_id AND e.active = 1
            WHERE c.active = 1
            GROUP BY c.id, c.name, c.display_name, c.icon
            ORDER BY c.display_name
            """

            try:
                results = self.db_manager.execute_query(query)
                return results
            except Exception as e:
                logger.error(f"Error al obtener info de categorías: {e}")
                raise

        # Con rol: usar JOIN con tabla de permisos (sin concatenación SQL)
        # ✅ SEGURO: No hay concatenación de strings, solo parámetro
        query = """
        SELECT
            c.id,
            c.name,
            c.display_name,
            c.icon,
            COUNT(e.id) as entry_count
        FROM abcmasplus.dbo.knowledge_categories c
        INNER JOIN abcmasplus.dbo.RolesCategoriesKnowledge rc
            ON c.id = rc.idCategoria
            AND rc.idRol = ?
            AND rc.permitido = 1
            AND rc.activo = 1
        LEFT JOIN abcmasplus.dbo.knowledge_entries e ON c.id = e.category_id AND e.active = 1
        WHERE c.active = 1
        GROUP BY c.id, c.name, c.display_name, c.icon
        ORDER BY c.display_name
        """

        try:
            results = self.db_manager.execute_query(query, (id_rol,))
            logger.debug(
                f"Info de categorías para rol {id_rol}: {len(results)} categorías permitidas"
            )
            return results

        except Exception as e:
            logger.error(f"Error al obtener info de categorías para rol {id_rol}: {e}")
            raise

    def get_example_questions(self, limit: int = 4) -> List[str]:
        """
        Obtener preguntas de ejemplo de alta prioridad desde BD.

        Args:
            limit: Número máximo de preguntas a retornar

        Returns:
            Lista de preguntas de ejemplo
        """
        query = f"""
        SELECT TOP ({limit}) question
        FROM abcmasplus.dbo.knowledge_entries
        WHERE active = 1 AND priority >= 2
        ORDER BY priority DESC, id
        """

        try:
            results = self.db_manager.execute_query(query)
            return [row['question'] for row in results]

        except Exception as e:
            logger.error(f"Error al obtener preguntas de ejemplo: {e}")
            raise

    def health_check(self) -> bool:
        """
        Verificar si la conexión a BD está funcionando.

        Returns:
            True si la BD responde correctamente
        """
        try:
            query = "SELECT COUNT(*) as total FROM abcmasplus.dbo.knowledge_entries WHERE active = 1"
            result = self.db_manager.execute_query(query)

            if result and len(result) > 0:
                total = result[0].get('total', 0)
                logger.debug(f"Health check OK: {total} entradas activas")
                return True
            return False

        except Exception as e:
            logger.warning(f"Health check falló: {e}")
            return False

    def get_allowed_categories_by_role(self, id_rol: int) -> List[int]:
        """
        Obtener las categorías permitidas para un rol específico.

        Args:
            id_rol: ID del rol a consultar

        Returns:
            Lista de IDs de categorías permitidas para el rol

        Example:
            >>> categories = repo.get_allowed_categories_by_role(5)
            >>> # [1, 2, 3]  # IDs de categorías permitidas
        """
        # Verificar cache primero
        if id_rol in self._role_permissions_cache:
            logger.debug(f"Usando cache de permisos para rol {id_rol}")
            return self._role_permissions_cache[id_rol]

        query = """
        SELECT DISTINCT rc.idCategoria
        FROM abcmasplus.dbo.RolesCategoriesKnowledge rc
        WHERE rc.idRol = ?
            AND rc.permitido = 1
            AND rc.activo = 1
        ORDER BY rc.idCategoria
        """

        try:
            results = self.db_manager.execute_query(query, (id_rol,))
            category_ids = [row['idCategoria'] for row in results]

            # Guardar en cache
            self._role_permissions_cache[id_rol] = category_ids

            logger.info(
                f"Rol {id_rol} tiene acceso a {len(category_ids)} categorías: {category_ids}"
            )
            return category_ids

        except Exception as e:
            logger.error(f"Error al obtener categorías permitidas para rol {id_rol}: {e}")
            # En caso de error, retornar lista vacía (acceso denegado)
            return []

    def get_all_entries_by_role(self, id_rol: Optional[int] = None) -> List[KnowledgeEntry]:
        """
        Obtener entradas de conocimiento filtradas por permisos de rol.

        Args:
            id_rol: ID del rol del usuario (None = sin filtro de permisos)

        Returns:
            Lista de entradas de conocimiento permitidas para el rol

        Example:
            >>> entries = repo.get_all_entries_by_role(5)
            >>> # Solo entradas de categorías permitidas para rol 5
        """
        # Si no se especifica rol, obtener todas
        if id_rol is None:
            return self.get_all_entries()

        # ✅ SEGURO: Usar JOIN con tabla de permisos en lugar de concatenación
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
        FROM abcmasplus.dbo.knowledge_entries e
        INNER JOIN abcmasplus.dbo.knowledge_categories c ON e.category_id = c.id
        INNER JOIN abcmasplus.dbo.RolesCategoriesKnowledge rc
            ON c.id = rc.idCategoria
            AND rc.idRol = ?
            AND rc.permitido = 1
            AND rc.activo = 1
        WHERE e.active = 1
            AND c.active = 1
        ORDER BY e.priority DESC, e.id
        """

        try:
            results = self.db_manager.execute_query(query, (id_rol,))
            entries = []

            for row in results:
                entry = self._row_to_entry(row)
                if entry:
                    entries.append(entry)

            logger.info(
                f"Cargadas {len(entries)} entradas desde BD para rol {id_rol}"
            )
            return entries

        except Exception as e:
            logger.error(f"Error al cargar entradas filtradas por rol {id_rol}: {e}")
            raise
