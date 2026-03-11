"""
Gestor de registro de usuarios de Telegram.

Este módulo maneja el flujo de registro y verificación de cuentas de Telegram:
- Generación de códigos de verificación
- Inicio del proceso de registro
- Verificación de códigos
- Vinculación de cuentas
"""

import logging
import random
import string
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Excepción para errores en el proceso de registro."""
    pass


class RegistrationManager:
    """Gestor del proceso de registro de usuarios de Telegram."""

    # Configuración
    VERIFICATION_CODE_LENGTH = 6
    MAX_VERIFICATION_ATTEMPTS = 5
    VERIFICATION_CODE_EXPIRY_HOURS = 24

    def __init__(self, db_session: Session):
        """
        Inicializar gestor de registro.

        Args:
            db_session: Sesión de base de datos SQLAlchemy
        """
        self.session = db_session

    def generate_verification_code(self) -> str:
        """
        Generar código de verificación aleatorio.

        Returns:
            Código de verificación de 6 dígitos
        """
        return ''.join(
            random.choices(string.digits, k=self.VERIFICATION_CODE_LENGTH)
        )

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Buscar usuario por email.

        Args:
            email: Email del usuario

        Returns:
            Datos del usuario si existe, None en caso contrario
        """
        try:
            query = text("""
                SELECT
                    idUsuario,
                    Nombre AS nombre,
                    NULL AS apellido,
                    email,
                    idRol AS rol,
                    puesto,
                    Activa AS activo
                FROM  OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios
                WHERE email = :email
                    AND Activa = 1
            """)

            result = self.session.execute(query, {"email": email})
            row = result.fetchone()

            if row:
                return dict(zip(result.keys(), row))

            return None

        except Exception as e:
            logger.error(f"Error buscando usuario por email {email}: {e}")
            raise

    def find_user_by_employee_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """
        Buscar usuario por ID de empleado.

        Args:
            employee_id: ID del empleado

        Returns:
            Datos del usuario si existe, None en caso contrario
        """
        try:
            query = text("""
                SELECT
                    idUsuario,
                    Nombre AS nombre,
                    NULL AS apellido,
                    email,
                    idRol AS rol,
                    puesto,
                    Activa AS activo
                FROM OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios
                WHERE idUsuario = :employee_id
                    AND Activa = 1
            """)

            result = self.session.execute(query, {"employee_id": employee_id})
            row = result.fetchone()

            if row:
                return dict(zip(result.keys(), row))

            return None

        except Exception as e:
            logger.error(f"Error buscando usuario por employee_id {employee_id}: {e}")
            raise

    def start_registration(
        self,
        user_id: int,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        alias: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Iniciar proceso de registro de una cuenta de Telegram.

        Args:
            user_id: ID del usuario en la base de datos
            chat_id: Chat ID de Telegram
            username: Username de Telegram
            first_name: Nombre en Telegram
            last_name: Apellido en Telegram
            alias: Alias personalizado

        Returns:
            Tupla (éxito, mensaje, código_verificación)
        """
        try:
            # Verificar si el chat_id ya está registrado
            check_query = text("""
                SELECT COUNT(*) as count
                FROM consolaMonitoreo..BotIA_UsuariosTelegram
                WHERE telegramChatId = :chat_id
                    AND activo = 1
            """)
            result = self.session.execute(check_query, {"chat_id": chat_id})
            count = result.scalar()

            if count > 0:
                return (
                    False,
                    "Esta cuenta de Telegram ya está registrada.",
                    None
                )

            # Verificar si el usuario ya tiene una cuenta principal
            check_principal_query = text("""
                SELECT COUNT(*) as count
                FROM consolaMonitoreo..BotIA_UsuariosTelegram
                WHERE idUsuario = :user_id
                    AND esPrincipal = 1
                    AND activo = 1
            """)
            result = self.session.execute(check_principal_query, {"user_id": user_id})
            has_principal = result.scalar() > 0

            # Generar código de verificación
            verification_code = self.generate_verification_code()

            # Insertar registro de cuenta de Telegram
            insert_query = text("""
                INSERT INTO consolaMonitoreo..BotIA_UsuariosTelegram (
                    idUsuario,
                    telegramChatId,
                    telegramUsername,
                    telegramFirstName,
                    telegramLastName,
                    alias,
                    esPrincipal,
                    estado,
                    codigoVerificacion,
                    verificado,
                    intentosVerificacion,
                    fechaRegistro,
                    activo
                ) VALUES (
                    :user_id,
                    :chat_id,
                    :username,
                    :first_name,
                    :last_name,
                    :alias,
                    :es_principal,
                    'ACTIVO',
                    :verification_code,
                    0,
                    0,
                    GETDATE(),
                    1
                )
            """)

            self.session.execute(
                insert_query,
                {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "alias": alias,
                    "es_principal": 0 if has_principal else 1,
                    "verification_code": verification_code
                }
            )
            self.session.commit()

            logger.info(
                f"Registro iniciado para usuario {user_id}, "
                f"chat_id {chat_id}"
            )

            return (
                True,
                "Registro iniciado exitosamente. "
                "Por favor, verifica tu cuenta con el código que recibirás.",
                verification_code
            )

        except Exception as e:
            logger.error(f"Error iniciando registro: {e}")
            self.session.rollback()
            return (False, f"Error al iniciar registro: {str(e)}", None)

    def verify_account(
        self,
        chat_id: int,
        verification_code: str
    ) -> Tuple[bool, str]:
        """
        Verificar cuenta con código de verificación.

        Args:
            chat_id: Chat ID de Telegram
            verification_code: Código de verificación

        Returns:
            Tupla (éxito, mensaje)
        """
        try:
            # Obtener cuenta pendiente de verificación
            query = text("""
                SELECT
                    idUsuarioTelegram,
                    idUsuario,
                    codigoVerificacion,
                    intentosVerificacion,
                    fechaRegistro,
                    verificado
                FROM consolaMonitoreo..BotIA_UsuariosTelegram
                WHERE telegramChatId = :chat_id
                    AND activo = 1
            """)

            result = self.session.execute(query, {"chat_id": chat_id})
            row = result.fetchone()

            if not row:
                return (False, "Cuenta no encontrada.")

            data = dict(zip(result.keys(), row))

            # Verificar si ya está verificada
            if data['verificado']:
                return (True, "Tu cuenta ya está verificada.")

            # Verificar intentos
            if data['intentosVerificacion'] >= self.MAX_VERIFICATION_ATTEMPTS:
                # Bloquear cuenta
                self._block_account(chat_id)
                return (
                    False,
                    "Demasiados intentos fallidos. "
                    "Tu cuenta ha sido bloqueada. "
                    "Contacta al administrador."
                )

            # Verificar expiración del código
            fecha_registro = data['fechaRegistro']
            if isinstance(fecha_registro, str):
                fecha_registro = datetime.fromisoformat(fecha_registro)

            expiry_time = fecha_registro + timedelta(
                hours=self.VERIFICATION_CODE_EXPIRY_HOURS
            )
            if datetime.now() > expiry_time:
                return (
                    False,
                    "El código de verificación ha expirado. "
                    "Por favor, solicita uno nuevo."
                )

            # Verificar código
            if data['codigoVerificacion'] == verification_code:
                # Marcar como verificada
                update_query = text("""
                    UPDATE consolaMonitoreo..BotIA_UsuariosTelegram
                    SET verificado = 1,
                        fechaVerificacion = GETDATE(),
                        codigoVerificacion = NULL
                    WHERE telegramChatId = :chat_id
                """)
                self.session.execute(update_query, {"chat_id": chat_id})
                self.session.commit()

                logger.info(f"Cuenta verificada exitosamente: chat_id={chat_id}")
                return (True, "Cuenta verificada exitosamente.")
            else:
                # Incrementar intentos fallidos
                update_query = text("""
                    UPDATE consolaMonitoreo..BotIA_UsuariosTelegram
                    SET intentosVerificacion = intentosVerificacion + 1
                    WHERE telegramChatId = :chat_id
                """)
                self.session.execute(update_query, {"chat_id": chat_id})
                self.session.commit()

                intentos_restantes = (
                    self.MAX_VERIFICATION_ATTEMPTS -
                    data['intentosVerificacion'] - 1
                )
                return (
                    False,
                    f"Código incorrecto. "
                    f"Te quedan {intentos_restantes} intentos."
                )

        except Exception as e:
            logger.error(f"Error verificando cuenta: {e}")
            self.session.rollback()
            return (False, f"Error al verificar cuenta: {str(e)}")

    def resend_verification_code(self, chat_id: int) -> Tuple[bool, str, Optional[str]]:
        """
        Reenviar código de verificación.

        Args:
            chat_id: Chat ID de Telegram

        Returns:
            Tupla (éxito, mensaje, código_verificación)
        """
        try:
            # Verificar que la cuenta existe y no está verificada
            query = text("""
                SELECT verificado, estado
                FROM consolaMonitoreo..BotIA_UsuariosTelegram
                WHERE telegramChatId = :chat_id
                    AND activo = 1
            """)

            result = self.session.execute(query, {"chat_id": chat_id})
            row = result.fetchone()

            if not row:
                return (False, "Cuenta no encontrada.", None)

            data = dict(zip(result.keys(), row))

            if data['verificado']:
                return (False, "Tu cuenta ya está verificada.", None)

            if data['estado'] == 'BLOQUEADO':
                return (
                    False,
                    "Tu cuenta está bloqueada. Contacta al administrador.",
                    None
                )

            # Generar nuevo código
            new_code = self.generate_verification_code()

            # Actualizar código
            update_query = text("""
                UPDATE consolaMonitoreo..BotIA_UsuariosTelegram
                SET codigoVerificacion = :new_code,
                    intentosVerificacion = 0,
                    fechaRegistro = GETDATE()
                WHERE telegramChatId = :chat_id
            """)

            self.session.execute(
                update_query,
                {"new_code": new_code, "chat_id": chat_id}
            )
            self.session.commit()

            logger.info(f"Código reenviado para chat_id={chat_id}")
            return (
                True,
                "Nuevo código de verificación generado.",
                new_code
            )

        except Exception as e:
            logger.error(f"Error reenviando código: {e}")
            self.session.rollback()
            return (False, f"Error al reenviar código: {str(e)}", None)

    def _block_account(self, chat_id: int) -> None:
        """
        Bloquear cuenta por exceso de intentos.

        Args:
            chat_id: Chat ID de Telegram
        """
        try:
            query = text("""
                UPDATE consolaMonitoreo..BotIA_UsuariosTelegram
                SET estado = 'BLOQUEADO'
                WHERE telegramChatId = :chat_id
            """)
            self.session.execute(query, {"chat_id": chat_id})
            self.session.commit()
            logger.warning(f"Cuenta bloqueada: chat_id={chat_id}")
        except Exception as e:
            logger.error(f"Error bloqueando cuenta: {e}")
            self.session.rollback()

    def get_registration_status(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener estado del registro de una cuenta.

        Args:
            chat_id: Chat ID de Telegram

        Returns:
            Diccionario con el estado o None
        """
        try:
            query = text("""
                SELECT
                    ut.verificado,
                    ut.estado,
                    ut.intentosVerificacion,
                    ut.fechaRegistro,
                    u.Nombre,
                    u.email
                FROM consolaMonitoreo..BotIA_UsuariosTelegram ut
                INNER JOIN OPENDATASOURCE('SQLNCLI', 'Data Source=10.53.34.130,1533;User ID=usrmon;Password=MonAplic01@;').ABCMASplus.dbo.Usuarios u ON ut.idUsuario = u.idUsuario
                WHERE ut.telegramChatId = :chat_id
                    AND ut.activo = 1
            """)

            result = self.session.execute(query, {"chat_id": chat_id})
            row = result.fetchone()

            if row:
                return dict(zip(result.keys(), row))

            return None

        except Exception as e:
            logger.error(f"Error obteniendo estado de registro: {e}")
            raise
