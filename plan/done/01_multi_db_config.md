# TODO: Soporte Multi-BD en Settings y DatabaseManager

## Objetivo
Permitir conexiones a múltiples servidores de BD identificados por alias,
definidos en un archivo JSON con credenciales encodeadas en base64.
La BD default sigue siendo la del `.env` sin ningún cambio.

---

## Concepto

```
src/config/db_connections.json  →  aliases con Host, User, Pass (base64)
.env                            →  BD default (sin cambios)

Código:
  DatabaseManager.get("BAZ_CDMX")   # alias del JSON
  DatabaseManager.get()             # default del .env
```

---

## Archivo a crear: `src/config/db_connections.json`

```json
{
  "BAZ_CDMX": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  },
  "BAZ_KIO": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  },
  "BAZ_CTGS": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  },
  "ABCMASMMI": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  },
  "RDS": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  },
  "MONITOREOS": {
    "Host": "10.x.x.x,1433",
    "User": "usuario",
    "Pass": "password"
  }
}
```

> El formato `"IP,PUERTO"` en Host es el estándar de SQL Server (`SERVER=IP,PUERTO`).
> Credenciales en texto plano. El nombre de BD se pasa al hacer la query,
> no se define en el JSON (un alias identifica el servidor, no la BD).

---

## Cambios en `src/config/settings.py`

Agregar carga del JSON y resolución de alias:

```python
import json
from pathlib import Path

DB_CONNECTIONS_FILE = Path(__file__).parent / "db_connections.json"

class Settings(BaseSettings):
    # ... campos existentes sin cambios ...

    def get_alias_config(self, alias: str) -> dict:
        """
        Carga db_connections.json y retorna la config del alias pedido.
        Retorna dict con keys: host, port, user, password
        Lanza ValueError si el alias no existe o el archivo no está.
        """
        if not DB_CONNECTIONS_FILE.exists():
            raise FileNotFoundError(
                f"Archivo de conexiones no encontrado: {DB_CONNECTIONS_FILE}"
            )

        with open(DB_CONNECTIONS_FILE, encoding="utf-8") as f:
            connections = json.load(f)

        if alias not in connections:
            available = list(connections.keys())
            raise ValueError(
                f"Alias '{alias}' no existe en db_connections.json. "
                f"Aliases disponibles: {available}"
            )

        cfg = connections[alias]
        # Host formato "IP,PUERTO"
        parts = cfg["Host"].split(",")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 1433

        return {
            "host":     host,
            "port":     port,
            "user":     cfg["User"],
            "password": cfg["Pass"],
        }
```

---

## Cambios en `src/database/connection.py`

```python
class DatabaseManager:
    _instances: dict[str, "DatabaseManager"] = {}

    @classmethod
    def get(cls, alias: str = "default") -> "DatabaseManager":
        """
        Retorna la instancia del alias pedido (singleton por alias).
        alias="default" → BD del .env
        alias="BAZ_CDMX" → config del db_connections.json
        """
        if alias not in cls._instances:
            url = cls._build_url(alias)
            cls._instances[alias] = cls(url)
        return cls._instances[alias]

    @staticmethod
    def _build_url(alias: str) -> str:
        if alias == "default":
            return settings.database_url

        cfg = settings.get_alias_config(alias)
        driver = "ODBC Driver 17 for SQL Server"
        odbc_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={cfg['host']},{cfg['port']};"
            f"UID={cfg['user']};"
            f"PWD={cfg['password']};"
            f"Connection Timeout=15;"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}"
```

> Nota: El nombre de BD (`DATABASE=`) no se incluye en el ODBC string base
> para que el mismo alias pueda ejecutar queries en distintas BDs usando
> nombres de 3 partes (`MONITOREOS.dbo.Tabla`) o cambiando el db_name al conectar.

### Uso en el código

```python
db = DatabaseManager.get("MONITOREOS")  # → IP/credenciales del JSON
db = DatabaseManager.get("BAZ_CDMX")   # → otro servidor
db = DatabaseManager.get()             # → default del .env (sin cambios)
```

---

## Seguridad

- `db_connections.json` va en `.gitignore` (igual que `.env`)

---

## Criterios de aceptación
- [ ] `DatabaseManager.get()` funciona igual que antes (sin regresiones)
- [ ] `DatabaseManager.get("MONITOREOS")` conecta al host del JSON
- [ ] Agregar un alias nuevo = agregar un bloque de 4 líneas al JSON
- [ ] Alias no registrado → `ValueError` con lista de aliases disponibles
- [ ] `db_connections.json` está en `.gitignore`

## Archivos a crear/modificar
- `src/config/db_connections.json` (crear, agregar a `.gitignore`)
- `src/config/settings.py` (agregar `get_alias_config`)
- `src/database/connection.py` (agregar `get` y `_build_url`)
