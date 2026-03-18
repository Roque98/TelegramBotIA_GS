"""
Gestión de conexiones a la base de datos.
"""
import logging
from typing import List, Dict, Any
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de conexiones y operaciones de base de datos."""

    _instances: dict = {}  # alias → instancia (singleton por alias)

    @classmethod
    def get(cls, alias: str = "default") -> "DatabaseManager":
        """
        Retorna la instancia de BD del alias pedido (singleton por alias).

        Sin alias → BD default del .env.
        Con alias → servidor definido en variables DB_{ALIAS}_* del .env.

        Ejemplos:
            DatabaseManager.get()              # default del .env
            DatabaseManager.get("BAZ_CDMX")   # servidor del JSON
        """
        if alias not in cls._instances:
            url = cls._build_url(alias)
            cls._instances[alias] = cls(url)
        return cls._instances[alias]

    @staticmethod
    def _build_url(alias: str) -> str:
        """Construye la URL de conexión para el alias dado."""
        if alias == "default":
            return settings.database_url

        cfg = settings.get_alias_config(alias)
        driver = "ODBC Driver 17 for SQL Server"
        db_part = f"DATABASE={cfg['db']};" if cfg.get("db") else ""
        odbc_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={cfg['host']},{cfg['port']};"
            f"{db_part}"
            f"UID={cfg['user']};"
            f"PWD={cfg['password']};"
            f"Connection Timeout=15;"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"

    def __init__(self, database_url: str = None):
        """Inicializar el gestor de base de datos."""
        self.database_url = database_url or settings.database_url

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

        logger.info(f"DatabaseManager inicializado: {self.database_url[:40]}...")

    def get_session(self) -> Session:
        """Obtener una sesión de base de datos."""
        return self.SessionLocal()

    def get_schema(self) -> str:
        """
        Obtener el esquema de la base de datos en formato texto.

        Returns:
            Descripción del esquema de la base de datos
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

        except Exception as e:
            logger.error(f"Error obteniendo esquema: {e}")
            raise

    def execute_query(self, sql_query: str, params: Dict[str, Any] = None, autocommit: bool = False) -> List[Dict[str, Any]]:
        """
        Ejecutar una consulta SQL de solo lectura o EXEC de stored procedure.

        Args:
            sql_query: Consulta SQL o EXEC a ejecutar
            params: Parámetros nombrados para la consulta (ej: {"ip": "10.0.0.1"})
            autocommit: Si True, ejecuta sin transacción implícita. Necesario para
                        SPs que usan OPENDATASOURCE (evita transacciones distribuidas).

        Returns:
            Lista de diccionarios con los resultados

        Raises:
            ValueError: Si la consulta no es SELECT ni EXEC
        """
        # Validar que sea operación de lectura (SELECT o EXEC de SP)
        query_upper = sql_query.strip().upper()
        if not (query_upper.startswith("SELECT") or query_upper.startswith("EXEC")):
            raise ValueError("Solo se permiten consultas SELECT o EXEC de stored procedures")

        try:
            if autocommit:
                with self.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                    result = conn.execute(text(sql_query), params or {})
                    rows = result.fetchall()
            else:
                with self.get_session() as session:
                    result = session.execute(text(sql_query), params or {})
                    rows = result.fetchall()

            # Convertir a lista de diccionarios
            if rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in rows]
            return []

        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            raise

    def close(self):
        """Cerrar las conexiones de base de datos."""
        self.engine.dispose()
        logger.info("Conexiones de base de datos cerradas")
