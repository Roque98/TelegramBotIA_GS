Con base en el archivo database\init.sql quiero que me ayudes con algo.

La tabla usuarios ya existe, no existe usuarios 2 y esta es su estructura

USE [ABCMASplus]
GO

/****** Object:  Table [dbo].[Usuarios]    Script Date: 3/10/2026 6:49:23 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Usuarios](
	[idUsuario] [int] NOT NULL,
	[Nombre] [nvarchar](200) NULL,
	[Password] [nvarchar](200) NULL,
	[idRol] [int] NULL,
	[email] [nvarchar](150) NULL,
	[puesto] [nvarchar](150) NULL,
	[UltimoAcceso] [datetime] NULL,
	[EstatusLDAP] [nvarchar](40) NULL,
	[TipoCuentaLDAP] [int] NULL,
	[Empresa] [nvarchar](100) NULL,
	[Activa] [int] NULL,
 CONSTRAINT [PK_Usuarios_1] PRIMARY KEY CLUSTERED 
(
	[idUsuario] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO




Tambien la tabla roles 

SELECT TOP (1000) [idRol]
      ,[nombre]
      ,[fechaCreacion]
      ,[activo]
  FROM [abcmasplus].[dbo].[Roles]




Lo que necesito es lo siguiented

1.- Modifca mi archivo init para que todo se genere en consolaMonitoreo
2.- Revisa que los sps utilicen las tablas de usuarios y roles correctamente
3.- Modifica el nombre de todos los objetos de init para que todo tenga el prefijo BotIA
4.- Actualiza las referencias de base y tablas en el codigo 