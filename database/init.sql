-- ============================================================
--  Base de datos destino: consolaMonitoreo
--  Prefijo de todos los objetos: BotIA_
--
--  Orden de creación (respetando dependencias FK):
--    1. BotIA_knowledge_categories
--    2. BotIA_knowledge_entries   -> FK: BotIA_knowledge_categories
--    3. BotIA_UsuariosTelegram    (ref. OPENDATASOURCE Usuarios, cross-db sin FK)
--    4. BotIA_Modulos
--    5. BotIA_Operaciones         -> FK: BotIA_Modulos
--    6. BotIA_RolesOperaciones    -> FK: BotIA_Operaciones
--                                   (ref. OPENDATASOURCE Roles, cross-db sin FK)
--    7. BotIA_UsuariosOperaciones -> FK: BotIA_Operaciones
--                                   (ref. OPENDATASOURCE Usuarios, cross-db sin FK)
--    8. BotIA_LogOperaciones      -> FK: BotIA_Operaciones
--
--  NOTA: SQL Server no admite FK cross-database. Las referencias a
--  Usuarios y Roles se resuelven via OPENDATASOURCE en los SPs.
-- ============================================================

USE [consolaMonitoreo]
GO


-- ============================================================
--  1. BotIA_knowledge_categories
-- ============================================================
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_knowledge_categories](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [varchar](50) NOT NULL,
	[display_name] [nvarchar](100) NOT NULL,
	[description] [nvarchar](500) NULL,
	[icon] [nvarchar](10) NULL,
	[active] [bit] NOT NULL,
	[created_at] [datetime2](7) NOT NULL,
	[updated_at] [datetime2](7) NOT NULL,
 CONSTRAINT [PK_BotIA_knowledge_categories] PRIMARY KEY CLUSTERED
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_BotIA_knowledge_categories_name] UNIQUE NONCLUSTERED
(
	[name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_knowledge_categories] ADD  DEFAULT ((1)) FOR [active]
GO
ALTER TABLE [dbo].[BotIA_knowledge_categories] ADD  DEFAULT (getdate()) FOR [created_at]
GO
ALTER TABLE [dbo].[BotIA_knowledge_categories] ADD  DEFAULT (getdate()) FOR [updated_at]
GO


-- ============================================================
--  2. BotIA_knowledge_entries
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_knowledge_entries](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[category_id] [int] NOT NULL,
	[question] [nvarchar](500) NOT NULL,
	[answer] [nvarchar](max) NOT NULL,
	[keywords] [nvarchar](max) NOT NULL,
	[related_commands] [nvarchar](500) NULL,
	[priority] [int] NOT NULL,
	[active] [bit] NOT NULL,
	[created_at] [datetime2](7) NOT NULL,
	[updated_at] [datetime2](7) NOT NULL,
	[created_by] [nvarchar](100) NULL,
 CONSTRAINT [PK_BotIA_knowledge_entries] PRIMARY KEY CLUSTERED
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_knowledge_entries] ADD  DEFAULT ((1)) FOR [priority]
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] ADD  DEFAULT ((1)) FOR [active]
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] ADD  DEFAULT (getdate()) FOR [created_at]
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] ADD  DEFAULT (getdate()) FOR [updated_at]
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] ADD  DEFAULT ('system') FOR [created_by]
GO

ALTER TABLE [dbo].[BotIA_knowledge_entries]  WITH CHECK ADD  CONSTRAINT [FK_BotIA_knowledge_entries_category] FOREIGN KEY([category_id])
REFERENCES [dbo].[BotIA_knowledge_categories] ([id])
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] CHECK CONSTRAINT [FK_BotIA_knowledge_entries_category]
GO

ALTER TABLE [dbo].[BotIA_knowledge_entries]  WITH CHECK ADD  CONSTRAINT [CK_BotIA_knowledge_entries_priority] CHECK  (([priority]>=(1) AND [priority]<=(3)))
GO
ALTER TABLE [dbo].[BotIA_knowledge_entries] CHECK CONSTRAINT [CK_BotIA_knowledge_entries_priority]
GO


-- ============================================================
--  3. BotIA_UsuariosTelegram
--  idUsuario referencia OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios (cross-db, sin FK)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_UsuariosTelegram](
	[idUsuarioTelegram] [int] IDENTITY(1,1) NOT NULL,
	[idUsuario] [int] NOT NULL,
	[telegramChatId] [bigint] NOT NULL,
	[telegramUsername] [nvarchar](100) NULL,
	[telegramFirstName] [nvarchar](100) NULL,
	[telegramLastName] [nvarchar](100) NULL,
	[alias] [nvarchar](50) NULL,
	[esPrincipal] [bit] NOT NULL,
	[estado] [nvarchar](20) NOT NULL,
	[fechaRegistro] [datetime] NOT NULL,
	[fechaUltimaActividad] [datetime] NULL,
	[fechaVerificacion] [datetime] NULL,
	[codigoVerificacion] [nvarchar](10) NULL,
	[verificado] [bit] NOT NULL,
	[intentosVerificacion] [int] NOT NULL,
	[notificacionesActivas] [bit] NOT NULL,
	[observaciones] [nvarchar](500) NULL,
	[activo] [bit] NOT NULL,
	[fechaCreacion] [datetime] NOT NULL,
	[usuarioCreacion] [int] NULL,
	[fechaModificacion] [datetime] NULL,
	[usuarioModificacion] [int] NULL,
 CONSTRAINT [PK_BotIA_UsuariosTelegram] PRIMARY KEY CLUSTERED
(
	[idUsuarioTelegram] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_BotIA_UsuariosTelegram_ChatId] UNIQUE NONCLUSTERED
(
	[telegramChatId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ((0)) FOR [esPrincipal]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ('ACTIVO') FOR [estado]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT (getdate()) FOR [fechaRegistro]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ((0)) FOR [verificado]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ((0)) FOR [intentosVerificacion]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ((1)) FOR [notificacionesActivas]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT ((1)) FOR [activo]
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] ADD  DEFAULT (getdate()) FOR [fechaCreacion]
GO

ALTER TABLE [dbo].[BotIA_UsuariosTelegram]  WITH CHECK ADD  CONSTRAINT [CK_BotIA_UsuariosTelegram_Estado] CHECK  (([estado]='BLOQUEADO' OR [estado]='SUSPENDIDO' OR [estado]='ACTIVO'))
GO
ALTER TABLE [dbo].[BotIA_UsuariosTelegram] CHECK CONSTRAINT [CK_BotIA_UsuariosTelegram_Estado]
GO


-- ============================================================
--  4. BotIA_Modulos
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_Modulos](
	[idModulo] [int] IDENTITY(1,1) NOT NULL,
	[nombre] [nvarchar](100) NOT NULL,
	[descripcion] [nvarchar](500) NULL,
	[icono] [nvarchar](50) NULL,
	[orden] [int] NOT NULL,
	[activo] [bit] NOT NULL,
	[fechaCreacion] [datetime] NOT NULL,
 CONSTRAINT [PK_Modulos] PRIMARY KEY CLUSTERED
(
	[idModulo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_Modulos_Nombre] UNIQUE NONCLUSTERED
(
	[nombre] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_Modulos] ADD  DEFAULT ((0)) FOR [orden]
GO
ALTER TABLE [dbo].[BotIA_Modulos] ADD  DEFAULT ((1)) FOR [activo]
GO
ALTER TABLE [dbo].[BotIA_Modulos] ADD  DEFAULT (getdate()) FOR [fechaCreacion]
GO


-- ============================================================
--  5. BotIA_Operaciones  -> FK: BotIA_Modulos
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_Operaciones](
	[idOperacion] [int] IDENTITY(1,1) NOT NULL,
	[idModulo] [int] NOT NULL,
	[nombre] [nvarchar](100) NOT NULL,
	[descripcion] [nvarchar](500) NULL,
	[comando] [nvarchar](100) NULL,
	[requiereParametros] [bit] NOT NULL,
	[parametrosEjemplo] [nvarchar](500) NULL,
	[nivelCriticidad] [int] NOT NULL,
	[orden] [int] NOT NULL,
	[activo] [bit] NOT NULL,
	[fechaCreacion] [datetime] NOT NULL,
 CONSTRAINT [PK_BotIA_Operaciones] PRIMARY KEY CLUSTERED
(
	[idOperacion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_BotIA_Operaciones_Comando] UNIQUE NONCLUSTERED
(
	[comando] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_Operaciones] ADD  DEFAULT ((0)) FOR [requiereParametros]
GO
ALTER TABLE [dbo].[BotIA_Operaciones] ADD  DEFAULT ((1)) FOR [nivelCriticidad]
GO
ALTER TABLE [dbo].[BotIA_Operaciones] ADD  DEFAULT ((0)) FOR [orden]
GO
ALTER TABLE [dbo].[BotIA_Operaciones] ADD  DEFAULT ((1)) FOR [activo]
GO
ALTER TABLE [dbo].[BotIA_Operaciones] ADD  DEFAULT (getdate()) FOR [fechaCreacion]
GO

ALTER TABLE [dbo].[BotIA_Operaciones]  WITH CHECK ADD  CONSTRAINT [FK_BotIA_Operaciones_Modulos] FOREIGN KEY([idModulo])
REFERENCES [dbo].[BotIA_Modulos] ([idModulo])
GO
ALTER TABLE [dbo].[BotIA_Operaciones] CHECK CONSTRAINT [FK_BotIA_Operaciones_Modulos]
GO


-- ============================================================
--  6. BotIA_RolesOperaciones  -> FK: BotIA_Operaciones
--  idRol referencia OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Roles (cross-db, sin FK)
--  usuarioAsignacion referencia OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios (cross-db, sin FK)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_RolesOperaciones](
	[idRolOperacion] [int] IDENTITY(1,1) NOT NULL,
	[idRol] [int] NOT NULL,
	[idOperacion] [int] NOT NULL,
	[permitido] [bit] NOT NULL,
	[fechaAsignacion] [datetime] NOT NULL,
	[usuarioAsignacion] [int] NULL,
	[observaciones] [nvarchar](500) NULL,
	[activo] [bit] NOT NULL,
 CONSTRAINT [PK_BotIA_RolesOperaciones] PRIMARY KEY CLUSTERED
(
	[idRolOperacion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_BotIA_RolesOperaciones] UNIQUE NONCLUSTERED
(
	[idRol] ASC,
	[idOperacion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_RolesOperaciones] ADD  DEFAULT ((1)) FOR [permitido]
GO
ALTER TABLE [dbo].[BotIA_RolesOperaciones] ADD  DEFAULT (getdate()) FOR [fechaAsignacion]
GO
ALTER TABLE [dbo].[BotIA_RolesOperaciones] ADD  DEFAULT ((1)) FOR [activo]
GO

ALTER TABLE [dbo].[BotIA_RolesOperaciones]  WITH CHECK ADD  CONSTRAINT [FK_BotIA_RolesOperaciones_Operaciones] FOREIGN KEY([idOperacion])
REFERENCES [dbo].[BotIA_Operaciones] ([idOperacion])
GO
ALTER TABLE [dbo].[BotIA_RolesOperaciones] CHECK CONSTRAINT [FK_BotIA_RolesOperaciones_Operaciones]
GO


-- ============================================================
--  6. BotIA_UsuariosOperaciones
--  idUsuario y usuarioAsignacion referencian OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios
--  (cross-db, sin FK)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_UsuariosOperaciones](
	[idUsuarioOperacion] [int] IDENTITY(1,1) NOT NULL,
	[idUsuario] [int] NOT NULL,
	[idOperacion] [int] NOT NULL,
	[permitido] [bit] NOT NULL,
	[fechaAsignacion] [datetime] NOT NULL,
	[fechaExpiracion] [datetime] NULL,
	[usuarioAsignacion] [int] NULL,
	[observaciones] [nvarchar](500) NULL,
	[activo] [bit] NOT NULL,
 CONSTRAINT [PK_BotIA_UsuariosOperaciones] PRIMARY KEY CLUSTERED
(
	[idUsuarioOperacion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
 CONSTRAINT [UQ_BotIA_UsuariosOperaciones] UNIQUE NONCLUSTERED
(
	[idUsuario] ASC,
	[idOperacion] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_UsuariosOperaciones] ADD  DEFAULT ((1)) FOR [permitido]
GO
ALTER TABLE [dbo].[BotIA_UsuariosOperaciones] ADD  DEFAULT (getdate()) FOR [fechaAsignacion]
GO
ALTER TABLE [dbo].[BotIA_UsuariosOperaciones] ADD  DEFAULT ((1)) FOR [activo]
GO

ALTER TABLE [dbo].[BotIA_UsuariosOperaciones]  WITH CHECK ADD  CONSTRAINT [FK_BotIA_UsuariosOperaciones_Operaciones] FOREIGN KEY([idOperacion])
REFERENCES [dbo].[BotIA_Operaciones] ([idOperacion])
GO
ALTER TABLE [dbo].[BotIA_UsuariosOperaciones] CHECK CONSTRAINT [FK_BotIA_UsuariosOperaciones_Operaciones]
GO


-- ============================================================
--  7. BotIA_LogOperaciones
--  idUsuario referencia OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios (cross-db, sin FK)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BotIA_LogOperaciones](
	[idLog] [bigint] IDENTITY(1,1) NOT NULL,
	[idUsuario] [int] NOT NULL,
	[idOperacion] [int] NULL,
	[telegramChatId] [bigint] NULL,
	[telegramUsername] [nvarchar](100) NULL,
	[parametros] [nvarchar](max) NULL,
	[resultado] [nvarchar](50) NOT NULL,
	[mensajeError] [nvarchar](max) NULL,
	[duracionMs] [int] NULL,
	[ipOrigen] [nvarchar](50) NULL,
	[fechaEjecucion] [datetime] NOT NULL,
 CONSTRAINT [PK_BotIA_LogOperaciones] PRIMARY KEY CLUSTERED
(
	[idLog] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[BotIA_LogOperaciones] ADD  DEFAULT (getdate()) FOR [fechaEjecucion]
GO

ALTER TABLE [dbo].[BotIA_LogOperaciones]  WITH CHECK ADD  CONSTRAINT [FK_BotIA_LogOperaciones_Operaciones] FOREIGN KEY([idOperacion])
REFERENCES [dbo].[BotIA_Operaciones] ([idOperacion])
GO
ALTER TABLE [dbo].[BotIA_LogOperaciones] CHECK CONSTRAINT [FK_BotIA_LogOperaciones_Operaciones]
GO


-- ============================================================
--  BotIA_sp_search_knowledge
--  Tablas knowledge en consolaMonitoreo: sin prefijo de BD
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[BotIA_sp_search_knowledge]
    @query NVARCHAR(500),
    @category VARCHAR(50) = NULL,
    @top_k INT = 3,
    @min_priority INT = 1
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (@top_k)
        e.id,
        e.question,
        e.answer,
        e.keywords,
        e.related_commands,
        e.priority,
        c.name as category,
        c.display_name as category_display_name,
        c.icon as category_icon,
        CASE
            WHEN e.priority = 3 THEN 1.5
            WHEN e.priority = 2 THEN 1.2
            ELSE 1.0
        END as score
    FROM BotIA_knowledge_entries e
    INNER JOIN BotIA_knowledge_categories c ON e.category_id = c.id
    WHERE
        e.active = 1
        AND c.active = 1
        AND e.priority >= @min_priority
        AND (@category IS NULL OR c.name = @category)
        AND (
            e.question LIKE '%' + @query + '%'
            OR e.answer LIKE '%' + @query + '%'
            OR e.keywords LIKE '%' + @query + '%'
        )
    ORDER BY
        e.priority DESC,
        LEN(e.question) ASC;
END
GO


-- ============================================================
--  BotIA_sp_VerificarPermisoOperacion
--  - Usuarios: abcmasplus (Activa=1, columna idRol)
--  - Operaciones/RolesOperaciones/UsuariosOperaciones: consolaMonitoreo
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[BotIA_sp_VerificarPermisoOperacion]
    @idUsuario INT,
    @comando NVARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @tienePermiso BIT = 0;
    DECLARE @mensaje NVARCHAR(500);
    DECLARE @idOperacion INT;
    DECLARE @nombreOperacion NVARCHAR(100);
    DECLARE @descripcionOperacion NVARCHAR(500);
    DECLARE @requiereParametros BIT;
    DECLARE @parametrosEjemplo NVARCHAR(500);
    DECLARE @rolUsuario INT;

    -- Verificar que el usuario existe y está activo
    -- Usuarios.Activa (int 1/0), columna idRol
    IF NOT EXISTS (SELECT 1 FROM OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios WHERE idUsuario = @idUsuario AND Activa = 1)
    BEGIN
        SELECT
            0 AS TienePermiso,
            'Usuario no encontrado o inactivo' AS Mensaje,
            NULL AS NombreOperacion,
            NULL AS DescripcionOperacion,
            NULL AS RequiereParametros,
            NULL AS ParametrosEjemplo;
        RETURN;
    END

    -- Obtener rol del usuario
    SELECT @rolUsuario = idRol FROM OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios WHERE idUsuario = @idUsuario;

    -- Buscar la operación por comando
    SELECT
        @idOperacion = idOperacion,
        @nombreOperacion = nombre,
        @descripcionOperacion = descripcion,
        @requiereParametros = requiereParametros,
        @parametrosEjemplo = parametrosEjemplo
    FROM BotIA_Operaciones
    WHERE comando = @comando AND activo = 1;

    IF @idOperacion IS NULL
    BEGIN
        SELECT
            0 AS TienePermiso,
            'Operación no encontrada' AS Mensaje,
            NULL AS NombreOperacion,
            NULL AS DescripcionOperacion,
            NULL AS RequiereParametros,
            NULL AS ParametrosEjemplo;
        RETURN;
    END

    -- Verificar permisos específicos del usuario (prioridad alta)
    IF EXISTS (
        SELECT 1
        FROM BotIA_UsuariosOperaciones
        WHERE idUsuario = @idUsuario
            AND idOperacion = @idOperacion
            AND activo = 1
            AND (fechaExpiracion IS NULL OR fechaExpiracion > GETDATE())
    )
    BEGIN
        SELECT @tienePermiso = permitido
        FROM BotIA_UsuariosOperaciones
        WHERE idUsuario = @idUsuario
            AND idOperacion = @idOperacion
            AND activo = 1
            AND (fechaExpiracion IS NULL OR fechaExpiracion > GETDATE());

        SET @mensaje = CASE
            WHEN @tienePermiso = 1 THEN 'Permiso concedido (permiso específico de usuario)'
            ELSE 'Permiso denegado (permiso específico de usuario)'
        END;
    END
    ELSE
    BEGIN
        -- Verificar permisos del rol
        IF EXISTS (
            SELECT 1
            FROM BotIA_RolesOperaciones
            WHERE idRol = @rolUsuario
                AND idOperacion = @idOperacion
                AND activo = 1
        )
        BEGIN
            SELECT @tienePermiso = permitido
            FROM BotIA_RolesOperaciones
            WHERE idRol = @rolUsuario
                AND idOperacion = @idOperacion
                AND activo = 1;

            SET @mensaje = CASE
                WHEN @tienePermiso = 1 THEN 'Permiso concedido (permiso de rol)'
                ELSE 'Permiso denegado (permiso de rol)'
            END;
        END
        ELSE
        BEGIN
            SET @tienePermiso = 0;
            SET @mensaje = 'Permiso no configurado para este usuario o rol';
        END
    END

    SELECT
        @tienePermiso AS TienePermiso,
        @mensaje AS Mensaje,
        @nombreOperacion AS NombreOperacion,
        @descripcionOperacion AS DescripcionOperacion,
        @requiereParametros AS RequiereParametros,
        @parametrosEjemplo AS ParametrosEjemplo;
END
GO


-- ============================================================
--  BotIA_sp_ObtenerOperacionesUsuario
--  - Usuarios: OPENDATASOURCE (Activa=1, columna idRol)
--  - Operaciones/Modulos: consolaMonitoreo (BotIA_Operaciones, BotIA_Modulos)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[BotIA_sp_ObtenerOperacionesUsuario]
    @idUsuario INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @rolUsuario INT;

    -- Obtener rol del usuario
    SELECT @rolUsuario = idRol
    FROM OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios
    WHERE idUsuario = @idUsuario AND Activa = 1;

    IF @rolUsuario IS NULL
    BEGIN
        SELECT
            NULL AS Modulo,
            NULL AS IconoModulo,
            NULL AS idOperacion,
            NULL AS Operacion,
            NULL AS descripcion,
            NULL AS comando,
            NULL AS requiereParametros,
            NULL AS parametrosEjemplo,
            NULL AS nivelCriticidad,
            NULL AS OrigenPermiso,
            0 AS Permitido
        WHERE 1 = 0;
        RETURN;
    END

    SELECT DISTINCT
        m.nombre AS Modulo,
        m.icono AS IconoModulo,
        m.orden AS OrdenModulo,
        o.idOperacion,
        o.nombre AS Operacion,
        o.descripcion,
        o.comando,
        o.requiereParametros,
        o.parametrosEjemplo,
        o.nivelCriticidad,
        o.orden AS OrdenOperacion,
        CASE
            WHEN uo.idUsuarioOperacion IS NOT NULL THEN 'Usuario'
            ELSE 'Rol'
        END AS OrigenPermiso,
        CASE
            WHEN uo.idUsuarioOperacion IS NOT NULL THEN uo.permitido
            ELSE ro.permitido
        END AS Permitido
    FROM BotIA_Operaciones o
    INNER JOIN BotIA_Modulos m ON o.idModulo = m.idModulo
    LEFT JOIN BotIA_RolesOperaciones ro ON o.idOperacion = ro.idOperacion
        AND ro.idRol = @rolUsuario
        AND ro.activo = 1
    LEFT JOIN BotIA_UsuariosOperaciones uo ON o.idOperacion = uo.idOperacion
        AND uo.idUsuario = @idUsuario
        AND uo.activo = 1
        AND (uo.fechaExpiracion IS NULL OR uo.fechaExpiracion > GETDATE())
    WHERE o.activo = 1
        AND m.activo = 1
        AND (
            (uo.idUsuarioOperacion IS NOT NULL AND uo.permitido = 1)
            OR (uo.idUsuarioOperacion IS NULL AND ro.idRolOperacion IS NOT NULL AND ro.permitido = 1)
        )
    ORDER BY m.orden, o.orden, o.nombre;
END
GO


-- ============================================================
--  BotIA_sp_RegistrarLogOperacion
--  Inserta en BotIA_LogOperaciones
--  Busca idOperacion en BotIA_Operaciones (misma BD)
-- ============================================================
USE [consolaMonitoreo]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[BotIA_sp_RegistrarLogOperacion]
    @idUsuario INT,
    @comando NVARCHAR(100),
    @telegramChatId BIGINT = NULL,
    @telegramUsername NVARCHAR(100) = NULL,
    @parametros NVARCHAR(MAX) = NULL,
    @resultado NVARCHAR(50) = 'EXITOSO',
    @mensajeError NVARCHAR(MAX) = NULL,
    @duracionMs INT = NULL,
    @ipOrigen NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @idOperacion INT;

    -- Buscar la operación por comando
    SELECT @idOperacion = idOperacion
    FROM BotIA_Operaciones
    WHERE comando = @comando;

    -- Si no encuentra la operación, intentar con operación genérica
    IF @idOperacion IS NULL
    BEGIN
        SELECT @idOperacion = idOperacion
        FROM BotIA_Operaciones
        WHERE nombre = 'Operación Desconocida' OR comando IS NULL
        ORDER BY idOperacion
        OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY;
    END

    INSERT INTO BotIA_LogOperaciones (
        idUsuario,
        idOperacion,
        telegramChatId,
        telegramUsername,
        parametros,
        resultado,
        mensajeError,
        duracionMs,
        ipOrigen,
        fechaEjecucion
    )
    VALUES (
        @idUsuario,
        @idOperacion,
        @telegramChatId,
        @telegramUsername,
        @parametros,
        @resultado,
        @mensajeError,
        @duracionMs,
        @ipOrigen,
        GETDATE()
    );

    SELECT SCOPE_IDENTITY() AS idLog;
END
GO
