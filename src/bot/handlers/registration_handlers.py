"""
Handlers para el proceso de registro de usuarios.

Maneja los comandos:
- /register: Iniciar proceso de registro usando número de empleado
- /verify: Verificar cuenta con código
- /resend: Reenviar código de verificación

El código de verificación se guarda en la base de datos y el usuario
puede consultarlo desde el portal de consola de monitoreo.
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from src.database.connection import DatabaseManager
from src.auth import RegistrationManager

logger = logging.getLogger(__name__)

# Estados de la conversación de registro
WAITING_FOR_EMPLOYEE_ID = range(1)


class RegistrationHandlers:
    """Clase para manejar el flujo de registro de usuarios."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializar handlers de registro.

        Args:
            db_manager: Gestor de base de datos
        """
        self.db_manager = db_manager

    async def cmd_register(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para el comando /register.

        Inicia el proceso de registro solicitando el número de empleado.
        """
        user = update.effective_user

        # Verificar si ya está registrado
        with self.db_manager.get_session() as session:
            from src.auth import UserManager
            user_manager = UserManager(session)

            if user_manager.is_user_registered(user.id):
                telegram_user = user_manager.get_user_by_chat_id(user.id)

                if telegram_user.is_verified:
                    await update.message.reply_text(
                        f"✅ Hola {telegram_user.nombre_completo},\n\n"
                        f"Ya estás registrado y verificado en el sistema.\n\n"
                        f"👤 *Rol:* {telegram_user.rol_nombre}\n\n"
                        f"Puedes usar /help para ver los comandos disponibles.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Tu cuenta ya está registrada pero aún no está verificada.\n\n"
                        "🔑 Ingresa al portal de consola de monitoreo para obtener tu código de verificación.\n\n"
                        "Luego usa: /verify <codigo>"
                    )
                return ConversationHandler.END

        # Iniciar proceso de registro
        await update.message.reply_text(
            "👋 *Bienvenido al proceso de registro*\n\n"
            "Para registrarte, necesito que me proporciones tu *número de empleado* "
            "registrado en el sistema.\n\n"
            "📝 Por favor, envía tu número de empleado:",
            parse_mode='Markdown'
        )

        return WAITING_FOR_EMPLOYEE_ID

    async def handle_employee_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para procesar el número de empleado ingresado.

        Verifica que el número de empleado exista en la base de datos y genera código de verificación.
        """
        employee_id_text = update.message.text.strip()
        user = update.effective_user

        # Validar que sea un número
        try:
            employee_id = int(employee_id_text)
        except ValueError:
            await update.message.reply_text(
                "❌ El número de empleado debe ser un valor numérico.\n\n"
                "Por favor, ingresa un número válido o usa /cancel para cancelar."
            )
            return WAITING_FOR_EMPLOYEE_ID

        try:
            with self.db_manager.get_session() as session:
                reg_manager = RegistrationManager(session)

                # Buscar usuario por número de empleado
                user_data = reg_manager.find_user_by_employee_id(employee_id)

                if not user_data:
                    await update.message.reply_text(
                        f"❌ No encontré ningún usuario con el número de empleado *{employee_id}* "
                        f"en el sistema.\n\n"
                        f"Por favor, verifica tu número de empleado o contacta al administrador.\n\n"
                        f"Usa /cancel para cancelar el registro.",
                        parse_mode='Markdown'
                    )
                    return WAITING_FOR_EMPLOYEE_ID

                # Iniciar registro
                success, message, verification_code = reg_manager.start_registration(
                    user_id=user_data['idUsuario'],
                    chat_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )

                if not success:
                    await update.message.reply_text(
                        f"❌ Error al iniciar registro:\n\n{message}\n\n"
                        f"Usa /cancel para cancelar."
                    )
                    return ConversationHandler.END

                # Guardar datos en context para uso posterior
                context.user_data['registration_user_id'] = user_data['idUsuario']
                context.user_data['registration_employee_id'] = employee_id

                # Informar al usuario que debe consultar el portal
                await update.message.reply_text(
                    f"✅ *Registro iniciado exitosamente*\n\n"
                    f"Hola *{user_data['nombre']} {user_data['apellido']}*,\n\n"
                    f"📋 Tu cuenta de Telegram ha sido registrada en el sistema.\n\n"
                    f"🔐 *Para completar el registro:*\n"
                    f"1️⃣ Ingresa al *Portal de Consola de Monitoreo*\n"
                    f"2️⃣ Ve a la sección de *Administración de Cuentas Telegram*\n"
                    f"3️⃣ Consulta tu *código de verificación*\n"
                    f"4️⃣ Regresa a Telegram y usa: `/verify <codigo>`\n\n"
                    f"⏰ El código es válido por 24 horas.\n\n"
                    f"_ID Empleado: {employee_id}_\n"
                    f"_Email: {user_data['email']}_",
                    parse_mode='Markdown'
                )

                logger.info(
                    f"Registro iniciado para employee_id={employee_id} "
                    f"(user_id={user_data['idUsuario']}, chat_id={user.id}). "
                    f"Código guardado en BD."
                )

                return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error en proceso de registro: {e}")
            await update.message.reply_text(
                "❌ Ocurrió un error al procesar tu registro.\n"
                "Por favor, intenta más tarde o contacta al administrador."
            )
            return ConversationHandler.END

    async def cmd_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para el comando /verify <codigo>.

        Verifica la cuenta del usuario con el código proporcionado.
        """
        user = update.effective_user

        # Verificar que se proporcionó un código
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "⚠️ Por favor, proporciona el código de verificación.\n\n"
                "*Uso:* `/verify <codigo>`\n"
                "*Ejemplo:* `/verify 123456`\n\n"
                "🔑 Consulta tu código en el Portal de Consola de Monitoreo.",
                parse_mode='Markdown'
            )
            return

        verification_code = context.args[0].strip()

        try:
            with self.db_manager.get_session() as session:
                reg_manager = RegistrationManager(session)

                # Verificar cuenta
                success, message = reg_manager.verify_account(
                    chat_id=user.id,
                    verification_code=verification_code
                )

                if success:
                    # Obtener información del usuario verificado
                    from src.auth import UserManager
                    user_manager = UserManager(session)
                    telegram_user = user_manager.get_user_by_chat_id(user.id)

                    await update.message.reply_text(
                        f"🎉 *¡Verificación exitosa!*\n\n"
                        f"Bienvenido, *{telegram_user.nombre_completo}*\n\n"
                        f"👤 *Rol:* {telegram_user.rol_nombre}\n"
                        f"📧 *Email:* {telegram_user.email}\n\n"
                        f"✅ Tu cuenta está activa.\n"
                        f"Usa /help para ver los comandos disponibles.",
                        parse_mode='Markdown'
                    )

                    logger.info(f"Cuenta verificada exitosamente: chat_id={user.id}")
                else:
                    await update.message.reply_text(f"❌ {message}")

        except Exception as e:
            logger.error(f"Error en verificación: {e}")
            await update.message.reply_text(
                "❌ Ocurrió un error al verificar tu cuenta.\n"
                "Por favor, intenta más tarde."
            )

    async def cmd_resend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para el comando /resend.

        Genera un nuevo código de verificación.
        """
        user = update.effective_user

        try:
            with self.db_manager.get_session() as session:
                reg_manager = RegistrationManager(session)

                # Reenviar código
                success, message, verification_code = reg_manager.resend_verification_code(
                    chat_id=user.id
                )

                if success:
                    await update.message.reply_text(
                        f"✅ {message}\n\n"
                        f"🔑 *Nuevo código generado*\n\n"
                        f"Por favor:\n"
                        f"1️⃣ Ingresa al *Portal de Consola de Monitoreo*\n"
                        f"2️⃣ Consulta tu nuevo código de verificación\n"
                        f"3️⃣ Usa: `/verify <codigo>`",
                        parse_mode='Markdown'
                    )

                    logger.info(f"Nuevo código generado para chat_id={user.id}")
                else:
                    await update.message.reply_text(f"❌ {message}")

        except Exception as e:
            logger.error(f"Error generando nuevo código: {e}")
            await update.message.reply_text(
                "❌ Ocurrió un error al generar el nuevo código.\n"
                "Por favor, intenta más tarde."
            )

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handler para cancelar el proceso de registro.
        """
        await update.message.reply_text(
            "❌ Proceso de registro cancelado.\n\n"
            "Puedes volver a iniciar el registro con /register cuando quieras."
        )

        return ConversationHandler.END


def register_registration_handlers(application: Application, db_manager: DatabaseManager):
    """
    Registrar handlers de registro en la aplicación.

    Args:
        application: Aplicación de Telegram
        db_manager: Gestor de base de datos
    """
    logger.info("Registrando handlers de registro...")

    handlers = RegistrationHandlers(db_manager)

    # Conversation handler para el proceso de registro
    registration_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('register', handlers.cmd_register)],
        states={
            WAITING_FOR_EMPLOYEE_ID: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handlers.handle_employee_id
                )
            ]
        },
        fallbacks=[CommandHandler('cancel', handlers.cmd_cancel)]
    )

    application.add_handler(registration_conv_handler)

    # Handlers para verificación
    application.add_handler(CommandHandler('verify', handlers.cmd_verify))
    application.add_handler(CommandHandler('resend', handlers.cmd_resend))

    logger.info("Handlers de registro registrados exitosamente")
