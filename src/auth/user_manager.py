"""
Gestor de usuarios de Telegram.

Este módulo maneja la gestión de usuarios, incluyendo:
- Verificación de registro de usuarios
- Obtención de información del usuario
- Actualización de actividad
- Gestión de cuentas de Telegram
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TelegramUser:
    """Representa un usuario de Telegram registrado en el sistema."""

    def __init__(self, data: Dict[str, Any]):
        """
        Inicializar usuario desde datos de la base de datos.

        Args:
            data: Diccionario con los datos del usuario
        """
        # Datos del usuario
        self.id_usuario = data.get('idUsuario')
        self.nombre = data.get('Nombre')
        self.email = data.get('email')
        self.rol_id = data.get('idRol')
        self.rol_nombre = data.get('rolNombre')
        self.activo = data.get('Activa', True)

        # Datos de la cuenta de Telegram
        self.id_usuario_telegram = data.get('idUsuarioTelegram')
        self.telegram_chat_id = data.get('telegramChatId')
        self.telegram_username = data.get('telegramUsername')
        self.telegram_first_name = data.get('telegramFirstName')
        self.telegram_last_name = data.get('telegramLastName')
        self.alias = data.get('alias')
        self.es_principal = data.get('esPrincipal', False)
        self.estado = data.get('estado', 'ACTIVO')
        self.verificado = data.get('verificado', False)
        self.fecha_ultima_actividad = data.get('fechaUltimaActividad')

    @property
    def nombre_completo(self) -> str:
        """Obtener nombre completo del usuario."""
        return self.nombre or ''

    @property
    def is_active(self) -> bool:
        """Verificar si el usuario y la cuenta están activos."""
        return self.activo and self.estado == 'ACTIVO'

    @property
    def is_verified(self) -> bool:
        """Verificar si la cuenta está verificada."""
        return self.verificado

    def __repr__(self) -> str:
        return (
            f"TelegramUser(id={self.id_usuario}, "
            f"nombre='{self.nombre_completo}', "
            f"chat_id={self.telegram_chat_id}, "
            f"rol='{self.rol_nombre}')"
        )


class UserManager:
    """Gestor de usuarios de Telegram."""

    def __init__(self, db_session: Session):
        """
        Inicializar el gestor de usuarios.

        Args:
            db_session: Sesión de base de datos SQLAlchemy
        """
        self.session = db_session

    def get_user_by_chat_id(self, chat_id: int) -> Optional[TelegramUser]:
        """
        Obtener usuario por su Chat ID de Telegram.

        Args:
            chat_id: Chat ID de Telegram

        Returns:
            TelegramUser si existe, None en caso contrario
        """
        try:
            query = text("""
                SELECT
                    u.idUsuario,
                    u.Nombre,
                    u.email,
                    u.idRol,
                    r.rol AS rolNombre,
                    u.Activa,
                    ut.idUsuarioTelegram,
                    ut.telegramChatId,
                    ut.telegramUsername,
                    ut.telegramFirstName,
                    ut.telegramLastName,
                    ut.alias,
                    ut.esPrincipal,
                    ut.estado,
                    ut.verificado,
                    ut.fechaUltimaActividad
                FROM consolaMonitoreo..BotIA_UsuariosTelegram ut
                INNER JOIN  OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios u ON ut.idUsuario = u.idUsuario
                INNER JOIN  OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Roles r ON u.idRol = r.idRol
                WHERE ut.telegramChatId = :chat_id
                    AND ut.activo = 1
            """)

            result = self.session.execute(query, {"chat_id": chat_id})
            row = result.fetchone()

            if row:
                # Convertir row a diccionario
                data = dict(zip(result.keys(), row))
                return TelegramUser(data)

            return None

        except Exception as e:
            logger.error(f"Error obteniendo usuario por chat_id {chat_id}: {e}")
            raise

    def get_user_by_id(self, user_id: int) -> Optional[TelegramUser]:
        """
        Obtener usuario por su ID.

        Args:
            user_id: ID del usuario

        Returns:
            TelegramUser si existe, None en caso contrario
        """
        try:
            query = text("""
                SELECT
                    u.idUsuario,
                    u.Nombre,
                    u.email,
                    u.idRol,
                    r.rol AS rolNombre,
                    u.Activa,
                    ut.idUsuarioTelegram,
                    ut.telegramChatId,
                    ut.telegramUsername,
                    ut.telegramFirstName,
                    ut.telegramLastName,
                    ut.alias,
                    ut.esPrincipal,
                    ut.estado,
                    ut.verificado,
                    ut.fechaUltimaActividad
                FROM  OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios u
                INNER JOIN  OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Roles r ON u.idRol = r.idRol
                LEFT JOIN  consolaMonitoreo..BotIA_UsuariosTelegram ut ON u.idUsuario = ut.idUsuario
                    AND ut.esPrincipal = 1
                    AND ut.activo = 1
                WHERE u.idUsuario = :user_id
            """)

            result = self.session.execute(query, {"user_id": user_id})
            row = result.fetchone()

            if row:
                data = dict(zip(result.keys(), row))
                return TelegramUser(data)

            return None

        except Exception as e:
            logger.error(f"Error obteniendo usuario por ID {user_id}: {e}")
            raise

    def is_user_registered(self, chat_id: int) -> bool:
        """
        Verificar si un chat_id está registrado.

        Args:
            chat_id: Chat ID de Telegram

        Returns:
            True si está registrado, False en caso contrario
        """
        user = self.get_user_by_chat_id(chat_id)
        return user is not None

    def update_last_activity(self, chat_id: int) -> bool:
        """
        Actualizar la fecha de última actividad de un usuario.

        Args:
            chat_id: Chat ID de Telegram

        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        try:
            query = text("""
                UPDATE  consolaMonitoreo..BotIA_UsuariosTelegram
                SET fechaUltimaActividad = GETDATE()
                WHERE telegramChatId = :chat_id
                    AND activo = 1
            """)

            result = self.session.execute(query, {"chat_id": chat_id})
            self.session.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error actualizando última actividad para chat_id {chat_id}: {e}")
            self.session.rollback()
            return False

    def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener estadísticas de uso de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con estadísticas o None
        """
        try:
            query = text("""
                SELECT
                    COUNT(*) AS totalOperaciones,
                    SUM(CASE WHEN resultado = 'EXITOSO' THEN 1 ELSE 0 END) AS exitosas,
                    SUM(CASE WHEN resultado = 'ERROR' THEN 1 ELSE 0 END) AS errores,
                    SUM(CASE WHEN resultado = 'DENEGADO' THEN 1 ELSE 0 END) AS denegadas,
                    AVG(CAST(duracionMs AS FLOAT)) AS duracionPromedio,
                    MAX(fechaEjecucion) AS ultimaOperacion
                FROM  consolaMonitoreo..BotIA_LogOperaciones
                WHERE idUsuario = :user_id
            """)

            result = self.session.execute(query, {"user_id": user_id})
            row = result.fetchone()

            if row:
                return dict(zip(result.keys(), row))

            return None

        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del usuario {user_id}: {e}")
            raise

    def get_all_user_telegram_accounts(self, user_id: int) -> list:
        """
        Obtener todas las cuentas de Telegram de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de cuentas de Telegram
        """
        try:
            query = text("""
                SELECT
                    idUsuarioTelegram,
                    telegramChatId,
                    telegramUsername,
                    alias,
                    esPrincipal,
                    estado,
                    verificado,
                    fechaRegistro,
                    fechaUltimaActividad
                FROM  consolaMonitoreo..BotIA_UsuariosTelegram
                WHERE idUsuario = :user_id
                    AND activo = 1
                ORDER BY esPrincipal DESC, fechaRegistro DESC
            """)

            result = self.session.execute(query, {"user_id": user_id})
            rows = result.fetchall()

            return [dict(zip(result.keys(), row)) for row in rows]

        except Exception as e:
            logger.error(f"Error obteniendo cuentas de Telegram del usuario {user_id}: {e}")
            raise
