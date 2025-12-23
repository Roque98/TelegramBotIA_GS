"""
UniversalHandler - Handler genérico que delega comandos al ToolOrchestrator.

Este handler reemplaza gradualmente los handlers específicos tradicionales,
delegando toda la lógica al sistema de Tools.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.tools.tool_orchestrator import ToolOrchestrator
from src.tools.execution_context import ExecutionContextBuilder
from src.utils.status_message import StatusMessage
from src.utils.input_validator import InputValidator
from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Rate limiter global (10 requests por minuto por usuario)
_rate_limiter = RateLimiter(max_requests=10, time_window=60)


class UniversalHandler:
    """
    Handler universal que delega comandos al sistema de Tools.

    Este handler actúa como puente entre Telegram y el ToolOrchestrator,
    traduciendo updates de Telegram a llamadas de tools.
    """

    def __init__(
        self,
        tool_orchestrator: ToolOrchestrator,
        db_manager=None,
        llm_agent=None,
        user_manager=None,
        permission_checker=None
    ):
        """
        Inicializar el handler universal.

        Args:
            tool_orchestrator: Orquestador de tools
            db_manager: Gestor de base de datos (opcional)
            llm_agent: Agente LLM (opcional)
            user_manager: Gestor de usuarios (opcional)
            permission_checker: Verificador de permisos (opcional)
        """
        self.tool_orchestrator = tool_orchestrator
        self.db_manager = db_manager
        self.llm_agent = llm_agent
        self.user_manager = user_manager
        self.permission_checker = permission_checker
        logger.info("UniversalHandler inicializado")

    async def handle_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str = None
    ):
        """
        Manejar cualquier comando delegándolo al ToolOrchestrator.

        Args:
            update: Update de Telegram
            context: Context de Telegram
            command: Comando a ejecutar (si no se proporciona, se extrae del update)
        """
        user_id = update.effective_user.id
        message_text = update.message.text

        # Extraer comando si no se proporcionó
        if command is None:
            # Extraer el comando del mensaje (ej: "/ia" de "/ia consulta")
            parts = message_text.split(maxsplit=1)
            command = parts[0] if parts else ""

        # Extraer argumentos del comando
        args_text = message_text.replace(command, '').strip()

        logger.info(f"UniversalHandler procesando comando '{command}' para usuario {user_id}")

        # ✅ NUEVA VALIDACIÓN: Rate limiting
        if not _rate_limiter.is_allowed(user_id):
            retry_after = _rate_limiter.get_retry_after(user_id)
            await update.message.reply_text(
                f"⏱️ Has alcanzado el límite de consultas.\n"
                f"Intenta de nuevo en {retry_after} segundos.\n\n"
                "_IRIS está aquí para ayudarte, pero con moderación_ 💙"
            )
            return

        # ✅ NUEVA VALIDACIÓN: Input validation para comandos de consulta
        if command in ["/ia", "/query"]:
            if not args_text:
                await update.message.reply_text(
                    "❌ Debes proporcionar una consulta.\n\n"
                    "**Ejemplo:** `/ia ¿Cuántos usuarios hay?`",
                    parse_mode='Markdown'
                )
                return

            # Validar la consulta
            is_valid, error_message = InputValidator.validate_query(args_text)
            if not is_valid:
                await update.message.reply_text(
                    f"❌ Consulta inválida: {error_message}\n\n"
                    "_Asegúrate de que tu consulta sea clara y específica_ 💡",
                    parse_mode='Markdown'
                )
                return

            # Sanitizar la consulta
            args_text = InputValidator.sanitize_query(args_text)
            logger.debug(f"Query sanitizada para usuario {user_id}")

        # Buscar el tool correspondiente
        tool = self.tool_orchestrator.registry.get_tool_by_command(command)

        if not tool:
            await update.message.reply_text(
                f"❌ Comando desconocido: {command}\n\n"
                "Usa /help para ver los comandos disponibles."
            )
            return

        # Crear mensaje de estado
        status_msg = StatusMessage(update, context)

        try:
            # Determinar mensaje de estado según el tool (con personalidad de IRIS)
            status_messages = {
                "/ia": "🔍 IRIS analizando tu consulta...",
                "/query": "🔍 IRIS analizando tu consulta...",
                "/help": "📚 IRIS preparando la ayuda...",
                "/stats": "📊 IRIS generando tus estadísticas..."
            }
            initial_status = status_messages.get(command, f"⚙️ IRIS ejecutando {command}...")
            await status_msg.send(initial_status)

            # Construir contexto de ejecución
            exec_context = self._build_execution_context(update, context)

            # Preparar parámetros según el tool
            params = self._extract_parameters(tool, args_text, update, context)

            # Actualizar estado antes de ejecutar
            await status_msg.update(f"✨ Procesando...")

            # Ejecutar tool a través del orquestador
            result = await self.tool_orchestrator.execute_command(
                user_id=user_id,
                command=command,
                params=params,
                context=exec_context
            )

            # Eliminar mensaje de estado
            await status_msg.delete()

            # Enviar respuesta
            if result.success:
                # Determinar modo de parseo según el contenido
                parse_mode = 'Markdown' if self._has_markdown(result.data) else None

                await update.message.reply_text(
                    str(result.data),
                    parse_mode=parse_mode
                )

                logger.info(
                    f"Comando '{command}' ejecutado exitosamente "
                    f"en {result.execution_time_ms:.2f}ms"
                )
            else:
                error_msg = result.user_friendly_error or result.error
                await update.message.reply_text(f"❌ {error_msg}")

                logger.warning(f"Comando '{command}' falló: {result.error}")

        except Exception as e:
            logger.error(f"Error en handle_command '{command}': {e}", exc_info=True)
            await status_msg.delete()
            await update.message.reply_text(
                "❌ Ocurrió un error inesperado al ejecutar el comando.\n"
                "Por favor, intenta nuevamente."
            )

    def _build_execution_context(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Construir el contexto de ejecución para el tool.

        Args:
            update: Update de Telegram
            context: Context de Telegram

        Returns:
            ExecutionContext configurado
        """
        builder = ExecutionContextBuilder().with_telegram(update, context)

        if self.db_manager:
            builder.with_db_manager(self.db_manager)

        if self.llm_agent:
            builder.with_llm_agent(self.llm_agent)

        if self.user_manager:
            builder.with_user_manager(self.user_manager)

        if self.permission_checker:
            builder.with_permission_checker(self.permission_checker)

        return builder.build()

    def _extract_parameters(
        self,
        tool,
        args_text: str,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> dict:
        """
        Extraer parámetros para el tool desde el mensaje.

        Args:
            tool: Tool a ejecutar
            args_text: Texto de argumentos
            update: Update de Telegram
            context: Context de Telegram

        Returns:
            Diccionario de parámetros
        """
        params = {}

        # Para QueryTool, el parámetro es la query completa
        if tool.name == "query":
            params["query"] = args_text if args_text else ""

        # Para otros tools, parsear según sus parámetros definidos
        # TODO: Implementar parsing más sofisticado cuando tengamos más tools

        return params

    @staticmethod
    def _has_markdown(text: str) -> bool:
        """
        Detectar si el texto contiene markdown.

        Args:
            text: Texto a analizar

        Returns:
            True si contiene markdown
        """
        if not isinstance(text, str):
            return False

        markdown_indicators = ['**', '*', '`', '_', '[', ']', '#']
        return any(indicator in text for indicator in markdown_indicators)

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Manejar mensajes de texto que no son comandos.

        Los trata como queries implícitas al QueryTool.

        Args:
            update: Update de Telegram
            context: Context de Telegram
        """
        # Construir comando /ia implícito
        message_text = update.message.text

        # Validar que el mensaje no esté vacío
        if not message_text or not message_text.strip():
            return

        logger.info(f"Texto recibido (query implícita): {message_text[:50]}...")

        # Delegar al handler de comando /ia
        # Simulamos que el usuario escribió "/ia <mensaje>"
        update.message.text = f"/ia {message_text}"

        await self.handle_command(update, context, command="/ia")


def create_universal_handler(
    tool_orchestrator: ToolOrchestrator,
    **kwargs
) -> UniversalHandler:
    """
    Factory function para crear UniversalHandler con configuración.

    Args:
        tool_orchestrator: Orquestador de tools
        **kwargs: Componentes adicionales (db_manager, llm_agent, etc.)

    Returns:
        UniversalHandler configurado
    """
    return UniversalHandler(
        tool_orchestrator=tool_orchestrator,
        db_manager=kwargs.get('db_manager'),
        llm_agent=kwargs.get('llm_agent'),
        user_manager=kwargs.get('user_manager'),
        permission_checker=kwargs.get('permission_checker')
    )
