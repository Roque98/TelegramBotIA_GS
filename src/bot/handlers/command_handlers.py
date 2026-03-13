"""
Handlers para comandos del bot de Telegram.

Maneja comandos básicos como /start, /help, /stats, etc.
"""
import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, Application

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejar el comando /start.

    Args:
        update: Objeto de actualización de Telegram
        context: Contexto de la conversación
    """
    user = update.effective_user
    logger.info(f"Usuario {user.id} ({user.username}) ejecutó /start")

    welcome_message = (
        f"¡Hola {user.first_name}! 👋\n\n"
        "Soy tu **asistente de monitoreo PRTG**.\n\n"
        "Analizo las alertas activas de los dispositivos del banco y te ayudo a diagnosticar incidentes.\n\n"
        "**Ejemplos de consultas:**\n"
        "• Analiza las alertas actuales\n"
        "• ¿Qué pasa con 10.80.191.22?\n"
        "• ¿Hay algo caído en producción?\n"
        "• Dame un diagnóstico de los eventos Down\n\n"
        "**Comandos disponibles:**\n"
        "/help - Ver ayuda detallada\n\n"
        "¡Escribe tu pregunta y empecemos! 🚀"
    )

    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejar el comando /help.

    Args:
        update: Objeto de actualización de Telegram
        context: Contexto de la conversación
    """
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} ejecutó /help")

    help_message = (
        "**📖 Guía de Uso**\n\n"
        "**Comandos Disponibles:**\n"
        "/start - Iniciar el bot y ver bienvenida\n"
        "/help - Mostrar esta ayuda\n\n"
        "**Cómo hacer consultas:**\n\n"
        "1️⃣ **Análisis de alertas PRTG:**\n"
        "   Escribe preguntas en lenguaje natural sobre las alertas activas:\n"
        "   • Analiza las alertas actuales\n"
        "   • ¿Qué pasa con 10.80.191.22?\n"
        "   • ¿Hay algo caído en producción?\n"
        "   • Dame un diagnóstico de los eventos Down\n"
        "   • ¿Cuántos dispositivos están en alerta?\n\n"
        "**Consejos:**\n"
        "✅ Puedes mencionar una IP específica para enfocarte en un dispositivo\n"
        "✅ Puedes preguntar por tipo de evento (Down, Warning, etc.)\n"
        "✅ El bot cruza las alertas con historial de tickets similares\n\n"
        "**Seguridad:**\n"
        "🔒 Solo se permiten consultas de lectura\n"
        "🔒 No se pueden modificar datos"
    )

    await update.message.reply_text(
        help_message,
        parse_mode='Markdown'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejar el comando /stats.

    Muestra estadísticas de uso del bot (placeholder por ahora).

    Args:
        update: Objeto de actualización de Telegram
        context: Contexto de la conversación
    """
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} ejecutó /stats")

    # TODO: Implementar estadísticas reales cuando se tenga el sistema de logging
    stats_message = (
        "**📊 Estadísticas de Uso**\n\n"
        "🔄 Consultas realizadas: N/A\n"
        "✅ Consultas exitosas: N/A\n"
        "❌ Consultas con error: N/A\n"
        "⏱️ Tiempo promedio: N/A\n\n"
        "_Sistema de estadísticas en desarrollo_"
    )

    await update.message.reply_text(
        stats_message,
        parse_mode='Markdown'
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manejar el comando /cancel.

    Cancela la operación actual (útil para flujos conversacionales).

    Args:
        update: Objeto de actualización de Telegram
        context: Contexto de la conversación
    """
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} ejecutó /cancel")

    await update.message.reply_text(
        "Operación cancelada. ¿En qué más puedo ayudarte?",
        parse_mode='Markdown'
    )


def register_command_handlers(application: Application) -> None:
    """
    Registrar todos los command handlers en la aplicación.

    Args:
        application: Aplicación de Telegram
    """
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    logger.info("Command handlers registrados exitosamente")
