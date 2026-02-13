# Base de Datos

## Configuración

| Campo | Valor |
|-------|-------|
| **Motor** | SQL Server / MySQL |
| **Base de datos** | `abcmasplus` |
| **ORM** | SQLAlchemy 2.0 |
| **Pool** | 5 conexiones + 10 overflow |
| **Timeout** | 20 segundos |

---

## Tablas Principales

### Usuarios y Autenticación

#### Usuarios
```sql
CREATE TABLE Usuarios (
    idUsuario INT PRIMARY KEY,
    idEmpleado INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    rol INT NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    fechaCreacion DATETIME NOT NULL,
    fechaUltimoAcceso DATETIME NULL,
    activo BIT NOT NULL
);
```

#### UsuariosTelegram
```sql
-- Vincula usuarios con Telegram
telegram_id BIGINT UNIQUE,
idUsuario INT FK,
username VARCHAR(100),
verificado BIT,
codigo_verificacion VARCHAR(10)
```

---

### Knowledge Base

#### knowledge_categories
```sql
CREATE TABLE knowledge_categories (
    id INT PRIMARY KEY IDENTITY,
    name VARCHAR(50) UNIQUE NOT NULL,      -- 'PROCESOS', 'POLITICAS', etc.
    display_name NVARCHAR(100) NOT NULL,
    description NVARCHAR(500),
    icon NVARCHAR(10),                      -- Emoji
    active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE()
);
```

**Categorías predefinidas**:
| name | display_name | icon |
|------|--------------|------|
| PROCESOS | Procesos | ⚙️ |
| POLITICAS | Políticas | 📋 |
| FAQS | Preguntas frecuentes | ❓ |
| CONTACTOS | Contactos | 📞 |
| RECURSOS_HUMANOS | RRHH | 👥 |
| SISTEMAS | Sistemas | 💻 |
| BASE_DATOS | Base de datos | 🗄️ |

#### knowledge_entries
```sql
CREATE TABLE knowledge_entries (
    id INT PRIMARY KEY IDENTITY,
    category_id INT FK NOT NULL,
    question NVARCHAR(500) NOT NULL,
    answer NVARCHAR(MAX) NOT NULL,
    keywords NVARCHAR(MAX) NOT NULL,       -- JSON: ["palabra1", "palabra2"]
    related_commands NVARCHAR(500),        -- JSON: ["/help", "/ia"]
    priority INT DEFAULT 1,                -- 1=normal, 2=high, 3=critical
    active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE()
);
```

---

### Memoria de Usuario

#### UserMemoryProfiles
```sql
CREATE TABLE UserMemoryProfiles (
    idMemoryProfile INT PRIMARY KEY IDENTITY,
    idUsuario INT FK UNIQUE NOT NULL,
    resumenContextoLaboral NVARCHAR(MAX),   -- "Usuario del área de ventas..."
    resumenTemasRecientes NVARCHAR(MAX),    -- "Últimamente pregunta sobre..."
    resumenHistorialBreve NVARCHAR(MAX),    -- "Ha realizado 45 consultas..."
    numInteracciones INT DEFAULT 0,
    ultimaActualizacion DATETIME2 DEFAULT GETDATE(),
    fechaCreacion DATETIME2 DEFAULT GETDATE(),
    version INT DEFAULT 1
);
```

---

### Permisos y Roles

#### Roles
```sql
CREATE TABLE Roles (
    idRol INT PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    activo BIT NOT NULL
);
```

#### RolesCategoriesKnowledge
```sql
-- Controla qué roles pueden ver qué categorías de knowledge
CREATE TABLE RolesCategoriesKnowledge (
    idRolCategoria INT PRIMARY KEY,
    idRol INT FK NOT NULL,
    idCategoria INT FK NOT NULL,
    permitido BIT NOT NULL,
    activo BIT DEFAULT 1,
    UNIQUE (idRol, idCategoria)
);
```

#### RolesOperaciones
```sql
-- Controla qué roles pueden ejecutar qué operaciones
CREATE TABLE RolesOperaciones (
    idRolOperacion INT PRIMARY KEY,
    idRol INT FK NOT NULL,
    idOperacion INT FK NOT NULL,
    permitido BIT NOT NULL,
    activo BIT NOT NULL,
    UNIQUE (idRol, idOperacion)
);
```

#### Operaciones
```sql
CREATE TABLE Operaciones (
    idOperacion INT PRIMARY KEY,
    idModulo INT FK NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500),
    comando VARCHAR(100),              -- '/ia', '/stats', etc.
    requiereParametros BIT NOT NULL,
    nivelCriticidad INT NOT NULL,
    activo BIT NOT NULL
);
```

---

### Logs y Auditoría

#### LogOperaciones
```sql
CREATE TABLE LogOperaciones (
    idLog BIGINT PRIMARY KEY IDENTITY,
    idUsuario INT FK NOT NULL,
    idOperacion INT FK NOT NULL,
    telegramChatId BIGINT,
    telegramUsername VARCHAR(100),
    parametros TEXT,                   -- JSON con query del usuario
    resultado VARCHAR(50),             -- 'EXITOSO', 'ERROR', 'DENEGADO'
    mensajeError TEXT,
    duracionMs INT,
    ipOrigen VARCHAR(50),
    fechaEjecucion DATETIME NOT NULL
);
```

---

### Chat e IA

#### ChatConversaciones
```sql
CREATE TABLE ChatConversaciones (
    IdConversacion INT PRIMARY KEY,
    IdUsuario INT FK NOT NULL,
    Titulo VARCHAR(200),
    Modelo VARCHAR(100),               -- 'gpt-4', 'claude-3-sonnet'
    Temperatura DECIMAL(3,2),
    MaxTokens INT,
    MensajeSistema TEXT,
    TotalMensajes INT DEFAULT 0,
    TotalTokensUsados INT DEFAULT 0,
    CostoTotal DECIMAL(10,4) DEFAULT 0,
    Activa BIT DEFAULT 1,
    FechaCreacion DATETIME NOT NULL
);
```

#### ChatMensajes
```sql
CREATE TABLE ChatMensajes (
    IdMensaje INT PRIMARY KEY,
    IdConversacion INT FK NOT NULL,
    Rol VARCHAR(20) NOT NULL,          -- 'user', 'assistant'
    Contenido TEXT NOT NULL,
    TokensPrompt INT,
    TokensCompletion INT,
    TiempoRespuestaMs INT,
    Costo DECIMAL(10,6),
    Modelo VARCHAR(100),
    FechaCreacion DATETIME NOT NULL
);
```

---

## Stored Procedures

### sp_search_knowledge
```sql
EXEC sp_search_knowledge
    @query = 'política devoluciones',
    @category = NULL,              -- o 'POLITICAS'
    @top_k = 3,
    @min_priority = 1
```

**Retorna**: Entradas ordenadas por prioridad + relevancia

---

## Queries Comunes

### Buscar en Knowledge Base
```python
# KnowledgeRepository.search_entries()
query = """
SELECT e.*, c.name as category_name
FROM knowledge_entries e
JOIN knowledge_categories c ON e.category_id = c.id
WHERE e.active = 1 AND c.active = 1
  AND (e.question LIKE ? OR e.keywords LIKE ?)
ORDER BY e.priority DESC
"""
```

### Obtener perfil de memoria
```python
# MemoryRepository.get_user_memory_profile()
query = """
SELECT * FROM UserMemoryProfiles
WHERE idUsuario = :user_id
"""
```

### Guardar perfil de memoria
```python
# MemoryRepository.save_memory_profile()
# INSERT si no existe, UPDATE si existe
query = """
MERGE INTO UserMemoryProfiles AS target
USING (SELECT :user_id AS idUsuario) AS source
ON target.idUsuario = source.idUsuario
WHEN MATCHED THEN
    UPDATE SET resumenContextoLaboral = :contexto, ...
WHEN NOT MATCHED THEN
    INSERT (idUsuario, ...) VALUES (:user_id, ...)
"""
```

### Verificar permisos
```python
# PermissionChecker.check_permission()
query = """
SELECT ro.permitido
FROM RolesOperaciones ro
JOIN Operaciones o ON ro.idOperacion = o.idOperacion
JOIN Usuarios u ON u.rol = ro.idRol
WHERE u.idUsuario = ? AND o.comando = ?
  AND ro.activo = 1 AND o.activo = 1
"""
```

---

## Conexión

### DatabaseManager
```python
# src/database/connection.py

class DatabaseManager:
    async def get_session(self) -> AsyncSession
    async def execute_query(self, sql: str, params: list = None) -> list[dict]
    async def get_schema(self) -> dict  # Para SQLGenerator
    async def close(self)
```

### Configuración
```python
# src/config/settings.py

class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 1433
    db_name: str = "abcmasplus"
    db_user: str
    db_password: str
    db_type: str = "mssql"  # mssql, mysql, postgresql

    @property
    def database_url(self) -> str:
        # Construye URL según db_type
```

---

## Migraciones

```
database/migrations/
├── 001_create_knowledge_base_tables.sql
├── 002_create_user_memory_profiles.sql
└── 002_seed_knowledge_base.sql
```

---

## Seguridad

### SQLValidator
- Solo permite `SELECT`, `EXEC`, `WITH`
- Rechaza `INSERT`, `UPDATE`, `DELETE`, `DROP`
- Rechaza comentarios `--`, `/*`, `*/`
- Rechaza múltiples statements (`;`)

### Queries parametrizadas
```python
# ✅ Correcto
db.execute_query("SELECT * FROM users WHERE id = ?", [user_id])

# ❌ Incorrecto (SQL injection)
db.execute_query(f"SELECT * FROM users WHERE id = {user_id}")
```
