# Especificación de API REST para IRIS Bot

> Endpoints propuestos para exponer las funcionalidades del bot IRIS mediante API REST

## Tabla de Contenidos

- [Visión General](#visión-general)
- [Autenticación](#autenticación)
- [Endpoints de Autenticación y Usuario](#endpoints-de-autenticación-y-usuario)
- [Endpoints de Consultas (Core)](#endpoints-de-consultas-core)
- [Endpoints de Knowledge Base](#endpoints-de-knowledge-base)
- [Endpoints de Base de Datos](#endpoints-de-base-de-datos)
- [Endpoints de Tools](#endpoints-de-tools)
- [Endpoints de Administración](#endpoints-de-administración)
- [Modelos de Datos](#modelos-de-datos)
- [Códigos de Estado](#códigos-de-estado)
- [Consideraciones de Implementación](#consideraciones-de-implementación)

---

## Visión General

La API REST expone todas las funcionalidades del bot IRIS permitiendo:
- Procesar consultas en lenguaje natural
- Acceder al conocimiento empresarial
- Ejecutar consultas a base de datos de forma segura
- Gestionar usuarios y permisos
- Utilizar el sistema de Tools

**Base URL:** `https://api.iris.empresa.com/v1`

**Formato de respuesta:** JSON

**Autenticación:** JWT Bearer Token

---

## Autenticación

Todos los endpoints (excepto los de registro/login) requieren autenticación mediante JWT Bearer Token.

```http
Authorization: Bearer <token>
```

El token debe incluirse en el header de todas las requests.

---

## Endpoints de Autenticación y Usuario

### 1. Registrar Usuario

```http
POST /auth/register
```

Iniciar proceso de registro de un nuevo usuario.

**Request Body:**
```json
{
  "telegram_chat_id": 123456789,
  "username": "juan_perez",
  "first_name": "Juan",
  "last_name": "Pérez",
  "email": "juan.perez@empresa.com"
}
```

**Response 201:**
```json
{
  "status": "pending_verification",
  "message": "Código de verificación enviado por email",
  "user_id": "usr_abc123",
  "expires_at": "2025-12-22T15:30:00Z"
}
```

---

### 2. Verificar Código de Registro

```http
POST /auth/verify
```

Verificar el código de registro enviado por email.

**Request Body:**
```json
{
  "user_id": "usr_abc123",
  "verification_code": "ABC123"
}
```

**Response 200:**
```json
{
  "status": "verified",
  "message": "Usuario verificado exitosamente",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "user": {
    "id": "usr_abc123",
    "username": "juan_perez",
    "email": "juan.perez@empresa.com",
    "role": "usuario",
    "permissions": ["read:knowledge", "execute:query"]
  }
}
```

---

### 3. Login

```http
POST /auth/login
```

Autenticar usuario existente.

**Request Body:**
```json
{
  "email": "juan.perez@empresa.com",
  "telegram_chat_id": 123456789
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "user": {
    "id": "usr_abc123",
    "username": "juan_perez",
    "role": "usuario"
  }
}
```

---

### 4. Refresh Token

```http
POST /auth/refresh
```

Renovar access token usando refresh token.

**Request Body:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

**Response 200:**
```json
{
  "access_token": "new_access_token",
  "expires_in": 3600
}
```

---

### 5. Obtener Perfil de Usuario

```http
GET /users/me
```

Obtener información del usuario autenticado.

**Response 200:**
```json
{
  "id": "usr_abc123",
  "username": "juan_perez",
  "email": "juan.perez@empresa.com",
  "first_name": "Juan",
  "last_name": "Pérez",
  "role": "usuario",
  "permissions": ["read:knowledge", "execute:query"],
  "created_at": "2025-01-15T10:00:00Z",
  "last_activity": "2025-12-22T14:30:00Z",
  "stats": {
    "total_queries": 150,
    "successful_queries": 145,
    "failed_queries": 5
  }
}
```

---

### 6. Actualizar Perfil

```http
PATCH /users/me
```

Actualizar información del usuario.

**Request Body:**
```json
{
  "first_name": "Juan Carlos",
  "last_name": "Pérez González",
  "email": "juanc.perez@empresa.com"
}
```

**Response 200:**
```json
{
  "id": "usr_abc123",
  "username": "juan_perez",
  "email": "juanc.perez@empresa.com",
  "first_name": "Juan Carlos",
  "last_name": "Pérez González",
  "updated_at": "2025-12-22T15:00:00Z"
}
```

---

## Endpoints de Consultas (Core)

### 7. Procesar Consulta en Lenguaje Natural

```http
POST /queries
```

Endpoint principal para procesar cualquier consulta (clasifica automáticamente).

**Request Body:**
```json
{
  "query": "¿Cómo solicito vacaciones?",
  "context": {
    "conversation_id": "conv_123",
    "include_metadata": true
  }
}
```

**Response 200:**
```json
{
  "id": "qry_xyz789",
  "type": "knowledge",
  "query": "¿Cómo solicito vacaciones?",
  "response": "Para solicitar vacaciones debes:\n1. Acceder al portal de RRHH...",
  "sources": [
    {
      "type": "knowledge_base",
      "category": "PROCESOS",
      "title": "Solicitud de Vacaciones",
      "relevance_score": 0.95
    }
  ],
  "metadata": {
    "classification_confidence": 0.98,
    "processing_time_ms": 450,
    "tokens_used": 120
  },
  "created_at": "2025-12-22T15:05:00Z"
}
```

**Tipos de respuesta según clasificación:**

- **General:** Respuesta conversacional de IRIS
- **Knowledge:** Respuesta desde knowledge base
- **Database:** Resultados de consulta SQL

---

### 8. Obtener Historial de Consultas

```http
GET /queries?limit=20&offset=0&type=knowledge
```

Obtener historial de consultas del usuario.

**Query Parameters:**
- `limit` (default: 20): Número de resultados
- `offset` (default: 0): Desplazamiento para paginación
- `type` (optional): Filtrar por tipo (general, knowledge, database)
- `from_date` (optional): Fecha desde (ISO 8601)
- `to_date` (optional): Fecha hasta (ISO 8601)

**Response 200:**
```json
{
  "queries": [
    {
      "id": "qry_xyz789",
      "type": "knowledge",
      "query": "¿Cómo solicito vacaciones?",
      "response_preview": "Para solicitar vacaciones debes...",
      "created_at": "2025-12-22T15:05:00Z",
      "processing_time_ms": 450
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

---

### 9. Obtener Detalle de Consulta

```http
GET /queries/{query_id}
```

Obtener detalles completos de una consulta específica.

**Response 200:**
```json
{
  "id": "qry_xyz789",
  "type": "knowledge",
  "query": "¿Cómo solicito vacaciones?",
  "response": "Para solicitar vacaciones debes:\n1. Acceder al portal de RRHH...",
  "sources": [...],
  "metadata": {...},
  "created_at": "2025-12-22T15:05:00Z"
}
```

---

## Endpoints de Knowledge Base

### 10. Buscar en Knowledge Base

```http
POST /knowledge/search
```

Buscar directamente en la base de conocimiento empresarial.

**Request Body:**
```json
{
  "query": "vacaciones",
  "category": "PROCESOS",
  "top_k": 5,
  "min_score": 0.3,
  "include_metadata": true
}
```

**Response 200:**
```json
{
  "results": [
    {
      "id": "kb_001",
      "question": "¿Cómo solicito vacaciones?",
      "answer": "Para solicitar vacaciones debes...",
      "category": "PROCESOS",
      "keywords": ["vacaciones", "permisos", "ausencias"],
      "priority": 3,
      "relevance_score": 0.95,
      "related_commands": ["/rrhh", "/ausencias"]
    }
  ],
  "total_results": 3,
  "search_time_ms": 25
}
```

---

### 11. Listar Categorías de Conocimiento

```http
GET /knowledge/categories
```

Obtener todas las categorías disponibles (filtradas por permisos del usuario).

**Response 200:**
```json
{
  "categories": [
    {
      "name": "PROCESOS",
      "display_name": "Procesos",
      "icon": "⚙️",
      "entry_count": 45,
      "accessible": true
    },
    {
      "name": "POLITICAS",
      "display_name": "Políticas",
      "icon": "📋",
      "entry_count": 32,
      "accessible": true
    },
    {
      "name": "FAQS",
      "display_name": "Preguntas Frecuentes",
      "icon": "❓",
      "entry_count": 58,
      "accessible": true
    }
  ],
  "total_categories": 3,
  "total_entries": 135
}
```

---

### 12. Obtener Entradas por Categoría

```http
GET /knowledge/categories/{category_name}/entries
```

Listar todas las entradas de una categoría específica.

**Response 200:**
```json
{
  "category": {
    "name": "PROCESOS",
    "display_name": "Procesos",
    "icon": "⚙️"
  },
  "entries": [
    {
      "id": "kb_001",
      "question": "¿Cómo solicito vacaciones?",
      "answer": "Para solicitar vacaciones...",
      "keywords": ["vacaciones", "permisos"],
      "priority": 3,
      "related_commands": ["/rrhh"]
    }
  ],
  "total_entries": 45
}
```

---

### 13. Obtener Entrada Específica

```http
GET /knowledge/entries/{entry_id}
```

Obtener detalles completos de una entrada de conocimiento.

**Response 200:**
```json
{
  "id": "kb_001",
  "question": "¿Cómo solicito vacaciones?",
  "answer": "Para solicitar vacaciones debes:\n1. Acceder al portal...",
  "category": "PROCESOS",
  "keywords": ["vacaciones", "permisos", "ausencias"],
  "priority": 3,
  "related_commands": ["/rrhh", "/ausencias"],
  "created_at": "2025-01-10T08:00:00Z",
  "updated_at": "2025-11-15T14:30:00Z",
  "views_count": 342,
  "helpful_count": 298
}
```

---

### 14. Obtener Preguntas de Ejemplo

```http
GET /knowledge/examples?limit=6
```

Obtener preguntas de ejemplo populares/destacadas.

**Response 200:**
```json
{
  "examples": [
    "¿Cómo solicito vacaciones?",
    "¿Cuál es el horario de trabajo?",
    "¿Cómo contacto al departamento de IT?",
    "¿Dónde encuentro las políticas de seguridad?",
    "¿Cómo reporto un incidente?",
    "¿Cuál es el proceso de onboarding?"
  ]
}
```

---

## Endpoints de Base de Datos

### 15. Ejecutar Consulta de Base de Datos

```http
POST /database/query
```

Procesar consulta en lenguaje natural y ejecutarla contra la BD.

**Request Body:**
```json
{
  "query": "¿Cuántos empleados hay en el departamento de IT?",
  "include_sql": false,
  "max_results": 100
}
```

**Response 200:**
```json
{
  "id": "dbq_abc456",
  "query": "¿Cuántos empleados hay en el departamento de IT?",
  "sql_query": "SELECT COUNT(*) FROM empleados WHERE departamento = 'IT'",
  "results": {
    "columns": ["count"],
    "rows": [
      [25]
    ],
    "row_count": 1
  },
  "natural_language_response": "Hay 25 empleados en el departamento de IT.",
  "execution_time_ms": 120,
  "created_at": "2025-12-22T15:10:00Z"
}
```

---

### 16. Validar SQL

```http
POST /database/validate
```

Validar una consulta SQL sin ejecutarla (útil para debugging).

**Request Body:**
```json
{
  "sql": "SELECT * FROM empleados WHERE departamento = 'IT'"
}
```

**Response 200:**
```json
{
  "valid": true,
  "warnings": [],
  "validation_rules_passed": [
    "read_only",
    "no_dangerous_operations",
    "valid_syntax"
  ]
}
```

**Response 400 (SQL inválido):**
```json
{
  "valid": false,
  "errors": [
    "Operación UPDATE no permitida (solo consultas SELECT)",
    "Sintaxis inválida en línea 2"
  ],
  "validation_rules_failed": ["read_only"]
}
```

---

### 17. Obtener Esquema de Base de Datos

```http
GET /database/schema
```

Obtener el esquema disponible de la BD (según permisos del usuario).

**Response 200:**
```json
{
  "tables": [
    {
      "name": "empleados",
      "columns": [
        {
          "name": "id",
          "type": "INTEGER",
          "nullable": false,
          "primary_key": true
        },
        {
          "name": "nombre",
          "type": "VARCHAR(100)",
          "nullable": false
        },
        {
          "name": "departamento",
          "type": "VARCHAR(50)",
          "nullable": true
        }
      ],
      "accessible": true
    }
  ],
  "total_tables": 15,
  "accessible_tables": 8
}
```

---

## Endpoints de Tools

### 18. Listar Tools Disponibles

```http
GET /tools
```

Obtener lista de tools disponibles para el usuario (según permisos).

**Response 200:**
```json
{
  "tools": [
    {
      "name": "QueryTool",
      "display_name": "Consulta de Base de Datos",
      "description": "Ejecuta consultas en lenguaje natural contra la base de datos",
      "commands": ["/ia", "/query"],
      "category": "DATABASE",
      "requires_auth": true,
      "required_permissions": ["execute:query"],
      "accessible": true
    }
  ],
  "total_tools": 5,
  "accessible_tools": 3,
  "categories": ["DATABASE", "KNOWLEDGE", "UTILITY"]
}
```

---

### 19. Ejecutar Tool Específico

```http
POST /tools/{tool_name}/execute
```

Ejecutar un tool específico con parámetros.

**Request Body:**
```json
{
  "parameters": {
    "query": "¿Cuántos usuarios activos hay?"
  },
  "context": {
    "user_id": "usr_abc123"
  }
}
```

**Response 200:**
```json
{
  "tool": "QueryTool",
  "status": "success",
  "result": {
    "response": "Hay 1,250 usuarios activos en el sistema.",
    "data": {...}
  },
  "execution_time_ms": 340,
  "executed_at": "2025-12-22T15:15:00Z"
}
```

---

### 20. Obtener Detalles de Tool

```http
GET /tools/{tool_name}
```

Obtener información detallada de un tool específico.

**Response 200:**
```json
{
  "name": "QueryTool",
  "display_name": "Consulta de Base de Datos",
  "description": "Ejecuta consultas en lenguaje natural contra la base de datos",
  "commands": ["/ia", "/query"],
  "category": "DATABASE",
  "requires_auth": true,
  "required_permissions": ["execute:query"],
  "parameters": [
    {
      "name": "query",
      "type": "string",
      "required": true,
      "description": "Consulta en lenguaje natural"
    }
  ],
  "examples": [
    {
      "query": "¿Cuántos empleados hay?",
      "description": "Contar total de empleados"
    }
  ]
}
```

---

## Endpoints de Administración

### 21. Obtener Estadísticas del Sistema

```http
GET /admin/stats
```

**Requiere:** Rol de administrador

Obtener estadísticas generales del sistema.

**Response 200:**
```json
{
  "users": {
    "total": 1250,
    "active_last_30_days": 980,
    "new_this_month": 45
  },
  "queries": {
    "total": 45000,
    "today": 320,
    "avg_per_day": 450,
    "by_type": {
      "general": 5000,
      "knowledge": 25000,
      "database": 15000
    }
  },
  "knowledge_base": {
    "total_entries": 135,
    "total_categories": 8,
    "most_accessed_category": "FAQS"
  },
  "system": {
    "uptime_seconds": 2592000,
    "version": "1.0.0",
    "database_status": "healthy"
  }
}
```

---

### 22. Listar Usuarios (Admin)

```http
GET /admin/users?limit=50&offset=0&role=usuario
```

**Requiere:** Rol de administrador

Listar todos los usuarios del sistema.

**Query Parameters:**
- `limit` (default: 50)
- `offset` (default: 0)
- `role` (optional): Filtrar por rol
- `status` (optional): active, inactive, pending

**Response 200:**
```json
{
  "users": [
    {
      "id": "usr_abc123",
      "username": "juan_perez",
      "email": "juan.perez@empresa.com",
      "role": "usuario",
      "status": "active",
      "last_activity": "2025-12-22T14:30:00Z",
      "total_queries": 150,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 1250,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

### 23. Gestionar Permisos de Usuario

```http
PATCH /admin/users/{user_id}/permissions
```

**Requiere:** Rol de administrador

Modificar permisos de un usuario.

**Request Body:**
```json
{
  "role": "admin",
  "permissions": ["read:knowledge", "execute:query", "manage:users"]
}
```

**Response 200:**
```json
{
  "user_id": "usr_abc123",
  "role": "admin",
  "permissions": ["read:knowledge", "execute:query", "manage:users"],
  "updated_at": "2025-12-22T15:20:00Z"
}
```

---

### 24. Gestionar Entradas de Knowledge Base (Admin)

```http
POST /admin/knowledge/entries
PUT /admin/knowledge/entries/{entry_id}
DELETE /admin/knowledge/entries/{entry_id}
```

**Requiere:** Rol de administrador

Crear, actualizar o eliminar entradas de conocimiento.

**POST Request Body:**
```json
{
  "question": "¿Cómo reseteo mi contraseña?",
  "answer": "Para resetear tu contraseña:\n1. Ve a...",
  "category": "SISTEMAS",
  "keywords": ["contraseña", "password", "reset"],
  "priority": 2,
  "related_commands": ["/help"],
  "role_permissions": [1, 2, 3]
}
```

**Response 201:**
```json
{
  "id": "kb_new_123",
  "question": "¿Cómo reseteo mi contraseña?",
  "category": "SISTEMAS",
  "created_at": "2025-12-22T15:25:00Z",
  "created_by": "usr_abc123"
}
```

---

### 25. Health Check

```http
GET /health
```

**Sin autenticación requerida**

Verificar estado del sistema.

**Response 200:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T15:30:00Z",
  "services": {
    "api": "up",
    "database": "up",
    "llm_provider": "up",
    "knowledge_base": "up"
  },
  "version": "1.0.0"
}
```

---

### 26. Obtener Logs del Sistema (Admin)

```http
GET /admin/logs?level=error&from_date=2025-12-20&limit=100
```

**Requiere:** Rol de administrador

Obtener logs del sistema para debugging.

**Query Parameters:**
- `level` (optional): debug, info, warning, error, critical
- `from_date` (optional): ISO 8601
- `to_date` (optional): ISO 8601
- `limit` (default: 100)
- `offset` (default: 0)

**Response 200:**
```json
{
  "logs": [
    {
      "timestamp": "2025-12-22T15:30:45Z",
      "level": "error",
      "message": "Error ejecutando consulta SQL",
      "context": {
        "user_id": "usr_xyz",
        "query_id": "qry_123",
        "error_code": "DB_TIMEOUT"
      }
    }
  ],
  "pagination": {
    "total": 523,
    "limit": 100,
    "offset": 0
  }
}
```

---

## Modelos de Datos

### Usuario (User)

```typescript
{
  id: string;               // Identificador único
  username: string;         // Nombre de usuario
  email: string;            // Email
  first_name: string;       // Nombre
  last_name: string;        // Apellido
  telegram_chat_id?: number;// ID de chat de Telegram (opcional)
  role: string;             // Rol: "usuario", "admin", "super_admin"
  permissions: string[];    // Lista de permisos
  status: string;           // "active", "inactive", "pending"
  created_at: string;       // ISO 8601
  last_activity: string;    // ISO 8601
  stats: UserStats;         // Estadísticas
}
```

### Consulta (Query)

```typescript
{
  id: string;                   // Identificador único
  user_id: string;              // ID del usuario
  type: string;                 // "general", "knowledge", "database"
  query: string;                // Texto de la consulta
  response: string;             // Respuesta generada
  sources?: Source[];           // Fuentes de información
  metadata: QueryMetadata;      // Metadatos
  created_at: string;           // ISO 8601
}
```

### Entrada de Conocimiento (KnowledgeEntry)

```typescript
{
  id: string;                   // Identificador único
  question: string;             // Pregunta
  answer: string;               // Respuesta
  category: string;             // Categoría
  keywords: string[];           // Keywords para búsqueda
  priority: number;             // 1 (baja), 2 (media), 3 (alta)
  related_commands?: string[];  // Comandos relacionados
  role_permissions?: number[];  // IDs de roles con acceso
  created_at: string;           // ISO 8601
  updated_at: string;           // ISO 8601
  views_count: number;          // Número de visualizaciones
  helpful_count: number;        // Votos de utilidad
}
```

---

## Códigos de Estado

| Código | Descripción |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 201 | Created - Recurso creado exitosamente |
| 400 | Bad Request - Datos inválidos |
| 401 | Unauthorized - Token inválido o faltante |
| 403 | Forbidden - Sin permisos suficientes |
| 404 | Not Found - Recurso no encontrado |
| 422 | Unprocessable Entity - Validación falló |
| 429 | Too Many Requests - Rate limit excedido |
| 500 | Internal Server Error - Error del servidor |
| 503 | Service Unavailable - Servicio temporalmente no disponible |

---

## Consideraciones de Implementación

### 1. Seguridad

- **Rate Limiting:**
  - Usuarios: 100 requests/min
  - Admins: 500 requests/min
- **CORS:** Configurar origins permitidos
- **API Keys:** Para integraciones de servicios
- **Validación de Input:** Sanitizar todas las entradas
- **SQL Injection:** Usar prepared statements siempre
- **Audit Logging:** Registrar todas las operaciones administrativas

### 2. Performance

- **Caché:**
  - Knowledge base entries: 1 hora
  - Categorías: 24 horas
  - Esquema de BD: 6 horas
- **Paginación:** Implementar en todos los listados
- **Compresión:** GZIP para responses grandes
- **Async Processing:** Para consultas pesadas

### 3. Versionado

- **Semantic Versioning:** Major.Minor.Patch
- **URL Versioning:** `/v1/`, `/v2/`
- **Deprecation Policy:** Aviso 6 meses antes
- **Backward Compatibility:** Mantener al menos 2 versiones

### 4. Documentación

- **OpenAPI/Swagger:** Especificación completa
- **Ejemplos:** Request/Response para cada endpoint
- **SDKs:** Generar para Python, JavaScript, etc.
- **Changelog:** Documentar todos los cambios

### 5. Monitoring

- **Métricas:**
  - Requests por segundo
  - Latencia promedio (p50, p95, p99)
  - Tasa de errores
  - Uso de tokens LLM
- **Alertas:**
  - Tasa de error > 5%
  - Latencia > 2s
  - BD no disponible
  - LLM provider down

### 6. Testing

- **Unit Tests:** Cobertura > 80%
- **Integration Tests:** Todos los endpoints
- **Load Testing:** 1000 requests/s
- **Security Testing:** OWASP Top 10

### 7. Framework Recomendado

```python
# Stack sugerido para implementación
- Framework: FastAPI (async, OpenAPI integrado, validación con Pydantic)
- Auth: FastAPI-JWT-Auth
- ORM: SQLAlchemy 2.0 (async)
- Validación: Pydantic v2
- Docs: Swagger UI / ReDoc (auto-generado por FastAPI)
- Testing: pytest + httpx
- Rate Limiting: slowapi
- Cache: Redis
```

### 8. Estructura de Proyecto Sugerida

```
api/
├── main.py                    # Punto de entrada
├── config/
│   └── settings.py           # Configuración
├── routes/
│   ├── auth.py               # Endpoints de autenticación
│   ├── queries.py            # Endpoints de consultas
│   ├── knowledge.py          # Endpoints de knowledge base
│   ├── database.py           # Endpoints de BD
│   ├── tools.py              # Endpoints de tools
│   └── admin.py              # Endpoints de admin
├── models/
│   └── schemas.py            # Modelos Pydantic
├── services/
│   ├── auth_service.py       # Lógica de autenticación
│   ├── query_service.py      # Lógica de consultas
│   └── knowledge_service.py  # Lógica de knowledge base
├── middleware/
│   ├── auth.py               # Middleware de autenticación
│   ├── rate_limit.py         # Rate limiting
│   └── logging.py            # Logging
└── utils/
    └── validators.py          # Validadores personalizados
```

---

## Ejemplo de Implementación (FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel

app = FastAPI(title="IRIS API", version="1.0.0")
security = HTTPBearer()

class QueryRequest(BaseModel):
    query: str
    context: dict = {}

class QueryResponse(BaseModel):
    id: str
    type: str
    query: str
    response: str
    metadata: dict

@app.post("/v1/queries", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    token: str = Depends(security)
):
    """
    Procesar consulta en lenguaje natural.

    El sistema clasificará automáticamente la consulta y
    aplicará el procesamiento correspondiente.
    """
    # Implementación aquí
    pass

@app.get("/v1/health")
async def health_check():
    """Health check del sistema."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }
```

---

## Próximos Pasos

1. **Priorización de Endpoints:**
   - Fase 1: Auth + Queries + Knowledge (endpoints core)
   - Fase 2: Database + Tools
   - Fase 3: Admin + Stats

2. **Desarrollo:**
   - Crear especificación OpenAPI completa
   - Implementar autenticación JWT
   - Migrar lógica del bot a servicios reutilizables
   - Implementar endpoints progresivamente

3. **Testing:**
   - Crear suite de tests de integración
   - Implementar CI/CD pipeline
   - Load testing antes de producción

4. **Documentación:**
   - Generar docs interactivas con Swagger
   - Crear guías de integración
   - Ejemplos de uso para cada endpoint

---

**Versión del documento:** 1.0.0
**Fecha:** 2025-12-22
**Autor:** Claude Code
**Estado:** Propuesta inicial
