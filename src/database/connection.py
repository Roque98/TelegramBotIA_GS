"""
Gestión de conexiones a la base de datos.
"""
import logging
from typing import List, Dict, Any, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError as SQLTimeoutError
from src.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de conexiones y operaciones de base de datos."""

    def __init__(self):
        """Inicializar el gestor de base de datos."""
        self.database_url = settings.database_url

        # Para operaciones síncronas con configuración optimizada
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_size=5,              # Número de conexiones permanentes en el pool
            max_overflow=10,          # Conexiones adicionales permitidas
            pool_timeout=20,          # Segundos esperando conexión del pool
            pool_recycle=3600,        # Reciclar conexiones cada hora (evita timeouts)
            pool_pre_ping=True,       # Verificar conexión antes de usar (previene errores)
            connect_args={
                "timeout": 15,        # Timeout de conexión inicial (segundos)
            }
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Conectado a base de datos: {settings.db_type} en {settings.db_host}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Obtener una sesión de base de datos con context manager.

        ✅ CORREGIDO: Ahora usa context manager para garantizar cierre de sesión.

        Uso:
            with db_manager.get_session() as session:
                # Usar sesión
                result = session.execute(query)
            # Sesión cerrada automáticamente

        Yields:
            Session: Sesión de SQLAlchemy

        Raises:
            ConnectionError: Si hay error de conexión a BD
            SQLAlchemyError: Si hay error en operación de BD
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()  # Commit automático si no hubo errores
        except Exception:
            session.rollback()  # Rollback automático en error
            raise
        finally:
            session.close()  # Siempre cerrar sesión

    def get_schema(self) -> str:
        """
        Obtener el esquema de la base de datos en formato texto.

        ✅ CORREGIDO: Manejo específico de excepciones.

        Returns:
            Descripción del esquema de la base de datos

        Raises:
            ConnectionError: Si hay error de conexión a BD
            TimeoutError: Si la operación tarda demasiado
            SQLAlchemyError: Si hay error de BD
        """
        try:
            inspector = inspect(self.engine)
            schema_description = []

            for table_name in inspector.get_table_names():
                schema_description.append(f"\nTabla: {table_name}")
                columns = inspector.get_columns(table_name)

                for column in columns:
                    col_type = str(column['type'])
                    nullable = "NULL" if column['nullable'] else "NOT NULL"
                    schema_description.append(
                        f"  - {column['name']}: {col_type} {nullable}"
                    )

            return "\n".join(schema_description)

        except OperationalError as e:
            # Error de conexión a BD
            logger.error(f"Error de conexión al obtener esquema: {e}")
            raise ConnectionError(f"No se pudo conectar a la base de datos: {e}") from e

        except SQLTimeoutError as e:
            # Timeout
            logger.error(f"Timeout al obtener esquema: {e}")
            raise TimeoutError(f"La base de datos no respondió a tiempo: {e}") from e

        except SQLAlchemyError as e:
            # Otros errores de SQLAlchemy
            logger.error(f"Error de SQLAlchemy obteniendo esquema: {e}")
            raise

        except Exception as e:
            # Solo para errores verdaderamente inesperados
            logger.error(f"Error inesperado obteniendo esquema: {e}", exc_info=True)
            raise

    def execute_query(self, sql_query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Ejecutar una consulta SQL de solo lectura.

        ✅ CORREGIDO: Manejo específico de excepciones y soporte para parámetros.

        Args:
            sql_query: Consulta SQL a ejecutar
            params: Parámetros opcionales para la consulta (tuple)

        Returns:
            Lista de diccionarios con los resultados

        Raises:
            ValueError: Si la consulta no es de solo lectura
            ConnectionError: Si hay error de conexión a BD
            TimeoutError: Si la consulta tarda demasiado
            SQLAlchemyError: Si hay error de BD
        """
        # Validar que sea solo SELECT o EXEC (stored procedures)
        query_upper = sql_query.strip().upper()
        if not (query_upper.startswith("SELECT") or query_upper.startswith("EXEC")):
            raise ValueError("Solo se permiten consultas SELECT o EXEC")

        try:
            with self.get_session() as session:
                if params:
                    result = session.execute(text(sql_query), params)
                else:
                    result = session.execute(text(sql_query))
                rows = result.fetchall()

                # Convertir a lista de diccionarios
                if rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in rows]
                return []

        except OperationalError as e:
            logger.error(f"Error de conexión ejecutando consulta: {e}")
            raise ConnectionError("Error de conexión a la base de datos") from e

        except SQLTimeoutError as e:
            logger.error(f"Timeout ejecutando consulta: {e}")
            raise TimeoutError("La consulta tardó demasiado tiempo") from e

        except SQLAlchemyError as e:
            logger.error(f"Error SQL ejecutando consulta: {e}")
            # Re-raise con contexto
            raise RuntimeError(f"Error ejecutando consulta SQL: {str(e)}") from e

        except Exception as e:
            # Errores inesperados
            logger.error(f"Error inesperado ejecutando consulta: {e}", exc_info=True)
            raise

    def close(self):
        """Cerrar las conexiones de base de datos."""
        self.engine.dispose()
        logger.info("Conexiones de base de datos cerradas")
