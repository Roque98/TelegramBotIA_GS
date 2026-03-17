"""
Configuración centralizada de la aplicación usando Pydantic Settings.
"""
import os
from pathlib import Path
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Obtener la ruta del directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Forzar carga del archivo .env con prioridad sobre variables de entorno del sistema
load_dotenv(ENV_FILE, override=True)


class Settings(BaseSettings):
    """Configuración de la aplicación."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Telegram
    telegram_bot_token: str

    # LLM Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-5-nano-2025-08-07"
    anthropic_api_key: str = ""

    # Database
    db_host: str = "localhost"
    db_port: int = 1433
    db_instance: str = ""  # Para SQL Server: SQLEXPRESS, MSSQLSERVER, etc.
    db_name: str
    db_user: str
    db_password: str
    db_type: str = "mssql"

    # Application
    log_level: str = "INFO"
    environment: str = "development"

    def get_alias_config(self, alias: str) -> dict:
        """
        Lee la configuración de un alias de BD desde variables de entorno.
        Convención: DB_{ALIAS}_HOST, DB_{ALIAS}_PORT, DB_{ALIAS}_USER, DB_{ALIAS}_PASS
        Opcional:   DB_{ALIAS}_DB  (nombre de base de datos inicial)

        Retorna dict con keys: host, port, user, password, db.
        Lanza ValueError si las variables requeridas no están definidas.
        """
        prefix = f"DB_{alias.upper().replace('-', '_')}_"

        host = os.environ.get(f"{prefix}HOST")
        user = os.environ.get(f"{prefix}USER")
        password = os.environ.get(f"{prefix}PASS")

        if not host or not user or not password:
            raise ValueError(
                f"Alias '{alias}' no configurado. "
                f"Define {prefix}HOST, {prefix}USER y {prefix}PASS en .env"
            )

        return {
            "host": host,
            "port": int(os.environ.get(f"{prefix}PORT", "1433")),
            "user": user,
            "password": password,
            "db": os.environ.get(f"{prefix}DB", ""),
        }

    @property
    def database_url(self) -> str:
        """Construir URL de conexión a la base de datos."""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.db_name}"
        elif self.db_type == "postgresql":
            return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        elif self.db_type == "mysql":
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        elif self.db_type == "mssql" or self.db_type == "sqlserver":
            # Para SQL Server usando pyodbc con ODBC Driver 17 for SQL Server
            driver = "ODBC Driver 17 for SQL Server"

            # Si se especifica una instancia nombrada (ej: SQLEXPRESS), usar odbc_connect
            if self.db_instance:
                # Construir connection string ODBC directa para instancia nombrada
                # Si hay puerto personalizado, incluirlo para evitar depender de SQL Server Browser
                server = f"{self.db_host}\\{self.db_instance}"
                if self.db_port and self.db_port != 1433:
                    server = f"{self.db_host},{self.db_port}\\{self.db_instance}"
                odbc_str = (
                    f"DRIVER={{{driver}}};"
                    f"SERVER={server};"
                    f"DATABASE={self.db_name};"
                    f"UID={self.db_user};"
                    f"PWD={self.db_password};"
                    f"Connection Timeout=15;"
                )
                # Usar odbc_connect permite pasar la connection string completa
                return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"
            else:
                # Para conexión por puerto TCP/IP (sin instancia nombrada)
                user = quote_plus(self.db_user)
                password = quote_plus(self.db_password)
                driver_encoded = "ODBC+Driver+17+for+SQL+Server"
                return f"mssql+pyodbc://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}?driver={driver_encoded}"
        else:
            raise ValueError(f"Tipo de base de datos no soportado: {self.db_type}")


# Instancia global de configuración
settings = Settings()
