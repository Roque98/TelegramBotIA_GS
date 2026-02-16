# Migración de Tablas - Prefijo IABOT_ y Reubicación a consolamonitoreo

## Información del Proyecto

| Campo | Valor |
|-------|-------|
| **Proyecto** | Iris Bot |
| **Fecha inicio** | 2026-02-16 |
| **Estado** | En progreso |
| **Rama** | feature/react-fase6-polish |

---

## Descripción

Migración de las tablas propias del bot desde `ABCMASplus` hacia `consolamonitoreo`, renombrándolas con el prefijo `IABOT_`. Las tablas compartidas del sistema (`Usuarios`, `Gerencias`, `GerenciasUsuarios`) permanecen en `ABCMASplus` sin cambios de nombre.

Adicionalmente, se actualiza la estructura de las tablas de usuarios para reflejar el esquema real de ABCMASplus.

---

## Cambios en Estructura de Tablas Compartidas (ABCMASplus)

### Usuarios (se mantiene en ABCMASplus.dbo)

**Estructura actual (real):**

| Campo | Descripción |
|-------|-------------|
| idUsuario | PK, identificador |
| Nombre | Nombre del usuario |
| Password | Contraseña |
| idRol | FK a Roles (ahora en consolamonitoreo como IABOT_Roles) |
| email | Correo electrónico |
| puesto | Puesto del usuario |
| UltimoAcceso | Fecha último acceso |
| EstatusLDAP | Estatus en LDAP |
| TipoCuentaLDAP | Tipo de cuenta LDAP |
| Empresa | Empresa del usuario |
| Activa | Estado activo/inactivo |

**Cambios respecto a documentación anterior:**
- Se elimina: `idEmpleado`, `apellido`, `fechaCreacion`, `fechaUltimoAcceso`, `activo`
- Se agrega: `Nombre` (reemplaza nombre+apellido), `Password`, `puesto`, `UltimoAcceso`, `EstatusLDAP`, `TipoCuentaLDAP`, `Empresa`, `Activa` (reemplaza `activo`)

### Gerencias (se mantiene en ABCMASplus.dbo)

**Estructura actual (real):**

| Campo | Descripción |
|-------|-------------|
| idGerencia | PK, identificador |
| idGerente | FK al gerente |
| idResponsable | FK al responsable |
| Gerencia | Nombre de la gerencia |
| CentroCostos | Centro de costos |
| idDireccion | FK a dirección |
| GrupoDeCorreo | Grupo de correo |
| id_ChatTelegram | Chat ID de Telegram de la gerencia |
| Nickname | Nickname de la gerencia |

**Cambios respecto a documentación anterior:**
- Se elimina: `alias`, `correo`, `fechaCreacion`, `activo`
- Se agrega: `idGerente`, `CentroCostos`, `idDireccion`, `GrupoDeCorreo`, `id_ChatTelegram`, `Nickname`

### GerenciasUsuarios (se mantiene en ABCMASplus.dbo)

**Estructura actual (real):**

| Campo | Descripción |
|-------|-------------|
| IdGerencia | FK a Gerencias |
| IdUsuario | FK a Usuarios |

**Cambios respecto a documentación anterior:**
- Se elimina: `idGerenciaUsuario` (PK), `fechaAsignacion`, `activo`
- Tabla simplificada: solo las dos FK

---

## Mapeo Completo de Tablas

### Base de datos: ABCMASplus.dbo (sin renombrar)

| Tabla | Estado |
|-------|--------|
| Usuarios | Permanece (estructura actualizada) |
| Gerencias | Permanece (estructura actualizada) |
| GerenciasUsuarios | Permanece (estructura actualizada) |

### Base de datos: consolamonitoreo.dbo (renombradas con IABOT_)

| Tabla original | Tabla nueva | Categoría |
|---|---|---|
| Roles | IABOT_Roles | Autenticación |
| RolesIA | IABOT_RolesIA | Autenticación |
| UsuariosTelegram | IABOT_UsuariosTelegram | Autenticación |
| AreaAtendedora | IABOT_AreaAtendedora | Gerencias |
| GerenciasRolesIA | IABOT_GerenciasRolesIA | Gerencias |
| UsuariosRolesIA | IABOT_UsuariosRolesIA | Roles IA |
| Modulos | IABOT_Modulos | Permisos |
| Operaciones | IABOT_Operaciones | Permisos |
| RolesOperaciones | IABOT_RolesOperaciones | Permisos |
| UsuariosOperaciones | IABOT_UsuariosOperaciones | Permisos |
| LogOperaciones | IABOT_LogOperaciones | Auditoría |
| knowledge_categories | IABOT_knowledge_categories | Knowledge Base |
| knowledge_entries | IABOT_knowledge_entries | Knowledge Base |
| RolesCategoriesKnowledge | IABOT_RolesCategoriesKnowledge | Knowledge Base |
| table_documentation | IABOT_table_documentation | Knowledge Base |
| column_documentation | IABOT_column_documentation | Knowledge Base |
| UserMemoryProfiles | IABOT_UserMemoryProfiles | Memoria |
| ChatConversaciones | IABOT_ChatConversaciones | Chat |
| ChatMensajes | IABOT_ChatMensajes | Chat |

### Stored Procedures (consolamonitoreo)

| SP original | SP nuevo |
|---|---|
| sp_VerificarPermisoOperacion | IABOT_sp_VerificarPermisoOperacion |
| sp_ObtenerOperacionesUsuario | IABOT_sp_ObtenerOperacionesUsuario |
| sp_RegistrarLogOperacion | IABOT_sp_RegistrarLogOperacion |
| sp_ActualizarActividadTelegram | IABOT_sp_ActualizarActividadTelegram |
| sp_search_knowledge | IABOT_sp_search_knowledge |

### Vistas (consolamonitoreo)

| Vista original | Vista nueva |
|---|---|
| vw_PermisosUsuarios | IABOT_vw_PermisosUsuarios |
| vw_knowledge_base | IABOT_vw_knowledge_base |

---

## Diagrama de Arquitectura de Datos

```
┌─────────────────────────────────┐     ┌──────────────────────────────────────┐
│     ABCMASplus.dbo              │     │     consolamonitoreo.dbo             │
│  (Tablas compartidas)           │     │  (Tablas del bot - prefijo IABOT_)   │
│                                 │     │                                      │
│  ┌───────────────────┐          │     │  ┌──────────────────────────┐        │
│  │ Usuarios          │◄─────────┼──┐  │  │ IABOT_Roles              │        │
│  │ (idUsuario, ...)  │          │  │  │  │ IABOT_RolesIA            │        │
│  └───────────────────┘          │  │  │  │ IABOT_UsuariosTelegram   │        │
│                                 │  │  │  │ IABOT_UsuariosRolesIA    │        │
│  ┌───────────────────┐          │  ├──┼──│ IABOT_RolesOperaciones   │        │
│  │ Gerencias         │◄─────────┼──┤  │  │ IABOT_UsuariosOperaciones│        │
│  │ (idGerencia, ...) │          │  │  │  │ IABOT_LogOperaciones     │        │
│  └───────────────────┘          │  │  │  │ IABOT_Operaciones        │        │
│                                 │  │  │  │ IABOT_Modulos            │        │
│  ┌───────────────────┐          │  │  │  │ IABOT_AreaAtendedora     │        │
│  │ GerenciasUsuarios │          │  │  │  │ IABOT_GerenciasRolesIA   │        │
│  │ (IdGerencia,      │          │  │  │  │ IABOT_UserMemoryProfiles │        │
│  │  IdUsuario)       │          │  │  │  │ IABOT_ChatConversaciones │        │
│  └───────────────────┘          │  │  │  │ IABOT_ChatMensajes       │        │
│                                 │  │  │  │ IABOT_knowledge_*        │        │
│                                 │  │  │  │ IABOT_RolesCategoriesK.. │        │
│                                 │  └──┼──│ IABOT_table_documentation│        │
│                                 │     │  │ IABOT_column_documentation│       │
│                                 │     │  └──────────────────────────┘        │
└─────────────────────────────────┘     └──────────────────────────────────────┘
         ▲ Cross-database JOINs ▲
         │  (ABCMASplus.dbo.X)  │
         └──────────────────────┘
```

---

## Impacto en el Código

### Archivos que requieren cambios

| Archivo | Cambios necesarios |
|---|---|
| `src/auth/registration.py` | Nuevas referencias de tablas + nuevas columnas Usuarios |
| `src/auth/user_manager.py` | Nuevas referencias de tablas + nuevas columnas |
| `src/auth/permission_checker.py` | Nuevas referencias de tablas + SPs renombrados |
| `src/memory/repository.py` | IABOT_UserMemoryProfiles, IABOT_LogOperaciones |
| `src/agent/memory/memory_repository.py` | IABOT_UserMemoryProfiles |
| `src/agent/knowledge/knowledge_repository.py` | IABOT_knowledge_*, IABOT_RolesCategoriesKnowledge |
| `src/agents/tools/preference_tool.py` | IABOT_UserMemoryProfiles, IABOT_UsuariosTelegram |
| `src/agents/tools/database_tool.py` | Queries genéricas |
| `docs/sql/*.sql` | Toda la documentación SQL |
| `database/migrations/` | Nueva migración |
| `.claude/context/DATABASE.md` | Documentación actualizada |

---

## Consideraciones Técnicas

1. **Sin segunda conexión**: No se necesita configurar una segunda BD. Se usan nombres fully qualified en las queries: `ABCMASplus.dbo.Usuarios`, `consolamonitoreo.dbo.IABOT_Roles`, etc.
2. **Permisos SQL Server**: El usuario de BD necesita permisos en ambas bases de datos
3. **FK cross-database**: SQL Server no soporta FK entre bases de datos - la integridad referencial se mantiene a nivel de aplicación
4. **SPs cross-database**: Los SPs en consolamonitoreo pueden referenciar tablas en ABCMASplus usando nombre completo

---

## Avance

| Fase | Descripción | Estado | Progreso |
|------|-------------|--------|----------|
| 1 | Actualizar código (tablas renombradas con fully qualified names) | Pendiente | 0% |
| 2 | Actualizar código (nueva estructura Usuarios) | Pendiente | 0% |
| 3 | Documentación | Pendiente | 0% |
| 4 | Testing | Pendiente | 0% |

> **Nota**: Los scripts SQL de migración se realizan manualmente fuera de este plan.

**Progreso total: 0%**

---

## Actividades Realizadas

### 2026-02-16
- Creación del plan de migración
- Análisis de tablas afectadas y mapeo completo
- Identificación de archivos de código que requieren cambios
- Documentación de nueva estructura de tablas compartidas (Usuarios, Gerencias, GerenciasUsuarios)

---

## Commits Relacionados

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| 2026-02-16 | (pendiente) | docs(plan): add IABOT table migration plan |
