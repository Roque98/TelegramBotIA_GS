"""
Punto de entrada principal del bot de Telegram con agente de base de datos.
"""
import asyncio
import logging
import nest_asyncio
from src.config.settings import settings
from src.bot.telegram_bot import TelegramBot
from src.observability import TracingFilter

# Permitir event loops anidados
nest_asyncio.apply()


def setup_logging():
    """Configurar el sistema de logging."""
    logging.basicConfig(
        format='%(asctime)s [%(trace_id)s] user=%(user_id)s %(name)s %(levelname)s - %(message)s',
        level=getattr(logging, settings.log_level.upper())
    )

    # Conectar TracingFilter para inyectar trace_id/user_id en todos los logs
    logging.getLogger().addFilter(TracingFilter())

    # Silenciar loggers ruidosos
    for noisy in ("httpcore", "httpx", "openai", "telegram", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def main():
    """Función principal para ejecutar el bot."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Iniciando bot de Telegram...")

    # Inicializar y ejecutar el bot
    bot = TelegramBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
