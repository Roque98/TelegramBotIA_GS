"""
Repository para gestión de perfiles de memoria de usuarios.

Este módulo maneja el acceso a la base de datos para los perfiles de memoria
y la lectura de interacciones desde LogOperaciones.
"""
import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class UserMemoryProfile:
    """
    Perfil de memoria de usuario con resúmenes narrativos.

    Attributes:
        id_usuario: ID del usuario en la tabla Usuarios
        resumen_contexto_laboral: Párrafo sobre rol, proyectos, herramientas
        resumen_temas_recientes: Párrafo sobre consultas frecuentes recientes
        resumen_historial_breve: Párrafo sobre problemas resueltos y patrones
        num_interacciones: Contador de interacciones desde última actualización
        ultima_actualizacion: Timestamp de última actualización de resúmenes
        fecha_creacion: Timestamp de creación del perfil
        version: Versión del formato de datos (para migraciones futuras)
    """
    id_usuario: int
    resumen_contexto_laboral: Optional[str] = None
    resumen_temas_recientes: Optional[str] = None
    resumen_historial_breve: Optional[str] = None
    num_interacciones: int = 0
    ultima_actualizacion: Optional[datetime] = None
    fecha_creacion: Optional[datetime] = None
    version: int = 1

    def has_content(self) -> bool:
        """Verificar si el perfil tiene algún resumen generado."""
        return any([
            self.resumen_contexto_laboral,
            self.resumen_temas_recientes,
            self.resumen_historial_breve
        ])


@dataclass
class UserInteraction:
    """
    Representa una interacción del usuario desde LogOperaciones.

    Attributes:
        id_log: ID del registro en LogOperaciones
        comando: Comando ejecutado (generalmente '/ia')
        parametros: Parámetros JSON con la query del usuario
        resultado: Resultado de la operación (EXITOSO, ERROR, etc.)
        fecha_hora: Timestamp de la interacción
        duracion_ms: Duración de procesamiento en milisegundos
    """
    id_log: int
    comando: str
    parametros: Dict[str, Any]
    resultado: str
    fecha_hora: datetime
    duracion_ms: Optional[int] = None

    @property
    def user_query(self) -> str:
        """Extraer la query del usuario desde parametros JSON."""
        if isinstance(self.parametros, dict):
            return self.parametros.get('query', '')
        elif isinstance(self.parametros, str):
            try:
                params = json.loads(self.parametros)
                return params.get('query', '')
            except (json.JSONDecodeError, AttributeError):
                return self.parametros
        return ''


class MemoryRepository:
    """
    Repository para acceso a perfiles de memoria en base de datos.

    Proporciona métodos CRUD para UserMemoryProfiles y lectura de
    interacciones desde LogOperaciones.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializar el repository.

        Args:
            db_manager: Gestor de base de datos
        """
        self.db_manager = db_manager

    def get_user_profile(self, user_id: int) -> Optional[UserMemoryProfile]:
        """
        Obtener perfil de memoria de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            UserMemoryProfile si existe, None si no

        Raises:
            Exception: Si hay error de base de datos
        """
        try:
            with self.db_manager.get_session() as session:
                query = text("""
                    SELECT
                        idUsuario,
                        resumenContextoLaboral,
                        resumenTemasRecientes,
                        resumenHistorialBreve,
                        numInteracciones,
                        ultimaActualizacion,
                        fechaCreacion,
                        version
                    FROM [abcmasplus].[dbo].[UserMemoryProfiles]
                    WHERE idUsuario = :user_id
                """)

                result = session.execute(query, {"user_id": user_id}).fetchone()

                if not result:
                    return None

                return UserMemoryProfile(
                    id_usuario=result.idUsuario,
                    resumen_contexto_laboral=result.resumenContextoLaboral,
                    resumen_temas_recientes=result.resumenTemasRecientes,
                    resumen_historial_breve=result.resumenHistorialBreve,
                    num_interacciones=result.numInteracciones,
                    ultima_actualizacion=result.ultimaActualizacion,
                    fecha_creacion=result.fechaCreacion,
                    version=result.version
                )

        except Exception as e:
            logger.error(f"Error obteniendo perfil de usuario {user_id}: {e}", exc_info=True)
            raise

    def save_user_profile(self, profile: UserMemoryProfile) -> None:
        """
        Guardar o actualizar perfil de memoria.

        Si el perfil existe, lo actualiza. Si no existe, lo crea.

        Args:
            profile: Perfil de memoria a guardar

        Raises:
            Exception: Si hay error de base de datos
        """
        try:
            with self.db_manager.get_session() as session:
                # Verificar si existe
                check_query = text("""
                    SELECT COUNT(*) as count
                    FROM [abcmasplus].[dbo].[UserMemoryProfiles]
                    WHERE idUsuario = :user_id
                """)
                exists = session.execute(
                    check_query,
                    {"user_id": profile.id_usuario}
                ).fetchone().count > 0

                if exists:
                    # UPDATE
                    update_query = text("""
                        UPDATE [abcmasplus].[dbo].[UserMemoryProfiles]
                        SET
                            resumenContextoLaboral = :contexto_laboral,
                            resumenTemasRecientes = :temas_recientes,
                            resumenHistorialBreve = :historial_breve,
                            numInteracciones = :num_interacciones,
                            ultimaActualizacion = GETDATE(),
                            version = :version
                        WHERE idUsuario = :user_id
                    """)

                    session.execute(update_query, {
                        "user_id": profile.id_usuario,
                        "contexto_laboral": profile.resumen_contexto_laboral,
                        "temas_recientes": profile.resumen_temas_recientes,
                        "historial_breve": profile.resumen_historial_breve,
                        "num_interacciones": profile.num_interacciones,
                        "version": profile.version
                    })

                    logger.info(f"Perfil actualizado para usuario {profile.id_usuario}")

                else:
                    # INSERT
                    insert_query = text("""
                        INSERT INTO [abcmasplus].[dbo].[UserMemoryProfiles]
                            (idUsuario, resumenContextoLaboral, resumenTemasRecientes,
                             resumenHistorialBreve, numInteracciones, version)
                        VALUES
                            (:user_id, :contexto_laboral, :temas_recientes,
                             :historial_breve, :num_interacciones, :version)
                    """)

                    session.execute(insert_query, {
                        "user_id": profile.id_usuario,
                        "contexto_laboral": profile.resumen_contexto_laboral,
                        "temas_recientes": profile.resumen_temas_recientes,
                        "historial_breve": profile.resumen_historial_breve,
                        "num_interacciones": profile.num_interacciones,
                        "version": profile.version
                    })

                    logger.info(f"Perfil creado para usuario {profile.id_usuario}")

                session.commit()

        except Exception as e:
            logger.error(f"Error guardando perfil de usuario {profile.id_usuario}: {e}", exc_info=True)
            raise

    def get_recent_interactions(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[UserInteraction]:
        """
        Obtener últimas interacciones exitosas de un usuario desde LogOperaciones.

        Args:
            user_id: ID del usuario
            limit: Número máximo de interacciones a obtener (default: 10)

        Returns:
            Lista de UserInteraction ordenadas por fecha (más reciente primero)

        Raises:
            Exception: Si hay error de base de datos
        """
        try:
            with self.db_manager.get_session() as session:
                query = text("""
                    SELECT TOP (:limit)
                        l.idLog,
                        o.comando,
                        l.parametros,
                        l.resultado,
                        l.fechaEjecucion as fechaHora,
                        l.duracionMs
                    FROM [abcmasplus].[dbo].[LogOperaciones] l
                    INNER JOIN [abcmasplus].[dbo].[Operaciones] o ON l.idOperacion = o.idOperacion
                    WHERE l.idUsuario = :user_id
                      AND o.comando = '/ia'
                      AND l.resultado = 'EXITOSO'
                    ORDER BY l.fechaEjecucion DESC
                """)

                results = session.execute(query, {
                    "user_id": user_id,
                    "limit": limit
                }).fetchall()

                interactions = []
                for row in results:
                    # Parsear parametros JSON
                    try:
                        if isinstance(row.parametros, str):
                            parametros = json.loads(row.parametros)
                        else:
                            parametros = row.parametros or {}
                    except (json.JSONDecodeError, TypeError):
                        parametros = {"query": str(row.parametros) if row.parametros else ""}

                    interactions.append(UserInteraction(
                        id_log=row.idLog,
                        comando=row.comando,
                        parametros=parametros,
                        resultado=row.resultado,
                        fecha_hora=row.fechaHora,
                        duracion_ms=row.duracionMs
                    ))

                logger.debug(f"Obtenidas {len(interactions)} interacciones para usuario {user_id}")
                return interactions

        except Exception as e:
            logger.error(f"Error obteniendo interacciones de usuario {user_id}: {e}", exc_info=True)
            raise

    def increment_interaction_count(self, user_id: int) -> int:
        """
        Incrementar contador de interacciones y retornar el nuevo valor.

        Si el usuario no tiene perfil, lo crea con contador en 1.

        Args:
            user_id: ID del usuario

        Returns:
            Nuevo número de interacciones

        Raises:
            Exception: Si hay error de base de datos
        """
        try:
            logger.info(f"🔢 Incrementando contador para usuario {user_id}")

            with self.db_manager.get_session() as session:
                # Intentar actualizar
                update_query = text("""
                    UPDATE [abcmasplus].[dbo].[UserMemoryProfiles]
                    SET numInteracciones = numInteracciones + 1,
                        ultimaActualizacion = GETDATE()
                    WHERE idUsuario = :user_id
                """)

                result = session.execute(update_query, {"user_id": user_id})
                logger.info(f"   → Filas afectadas por UPDATE: {result.rowcount}")

                if result.rowcount == 0:
                    # No existe, crear perfil con contador en 1
                    logger.info(f"   → Perfil no existe, creando nuevo...")
                    insert_query = text("""
                        INSERT INTO [abcmasplus].[dbo].[UserMemoryProfiles]
                            (idUsuario, numInteracciones)
                        VALUES (:user_id, 1)
                    """)
                    session.execute(insert_query, {"user_id": user_id})
                    session.commit()
                    logger.info(f"✅ Perfil creado para usuario {user_id} con contador=1")
                    return 1

                # Obtener nuevo valor
                select_query = text("""
                    SELECT numInteracciones
                    FROM [abcmasplus].[dbo].[UserMemoryProfiles]
                    WHERE idUsuario = :user_id
                """)
                new_count = session.execute(
                    select_query,
                    {"user_id": user_id}
                ).fetchone().numInteracciones

                session.commit()
                logger.info(f"✅ Contador incrementado a {new_count} para usuario {user_id}")
                return new_count

        except Exception as e:
            logger.error(f"Error incrementando contador de usuario {user_id}: {e}", exc_info=True)
            raise

    def reset_interaction_count(self, user_id: int) -> None:
        """
        Resetear contador de interacciones a 0.

        Se llama después de generar resúmenes para reiniciar el contador.

        Args:
            user_id: ID del usuario

        Raises:
            Exception: Si hay error de base de datos
        """
        try:
            with self.db_manager.get_session() as session:
                query = text("""
                    UPDATE [abcmasplus].[dbo].[UserMemoryProfiles]
                    SET numInteracciones = 0
                    WHERE idUsuario = :user_id
                """)
                session.execute(query, {"user_id": user_id})
                session.commit()
                logger.debug(f"Contador reseteado para usuario {user_id}")

        except Exception as e:
            logger.error(f"Error reseteando contador de usuario {user_id}: {e}", exc_info=True)
            raise
