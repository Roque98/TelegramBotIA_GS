"""
Handlers para consultas en lenguaje natural.

Maneja mensajes de texto que no son comandos y los procesa con el agente LLM.
Utiliza ToolSelector para detectar automáticamente el tool apropiado.
Soporta feature flag para usar el nuevo sistema ReAct.

Requiere autenticación y validación de permisos.
"""
import logging
import time
from typing import Optional

from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes, Application

from src.agent.llm_agent import LLMAgent
from src.auth import PermissionChecker, UserManager
from src.config.settings import settings
from src.utils.status_message import StatusMessage
from src.orchestrator import ToolSelector
from src.tools import get_registry, ToolOrchestrator, ExecutionContextBuilder

logger = logging.getLogger(__name__)

# Importación lazy del MainHandler para evitar dependencias circulares
_main_handler: Optional["MainHandler"] = None


def _get_main_handler(agent: LLMAgent) -> "MainHandler":
    """Obtiene o crea el MainHandler singleton."""
    global _main_handler
    if _main_handler is None:
        from src.gateway import create_main_handler
        _main_handler = create_main_handler(agent)
        logger.info("MainHandler (ReAct) inicializado para QueryHandler")
    return _main_handler


class QueryHandler:
    """Handler para procesar consultas en lenguaje natural."""

    def __init__(self, agent: LLMAgent):
        """
        Inicializar el handler de consultas.

        Args:
            agent: Instancia del agente LLM
        """
        self.agent = agent
        self.use_react_agent = settings.use_react_agent

        # Crear selector de tools (FASE 3 - Hito 1)
        self.tool_selector = ToolSelector(agent.llm_provider)
        self.tool_orchestrator = ToolOrchestrator(get_registry())

        if self.use_react_agent:
            logger.info(
                "QueryHandler inicializado con ReAct Agent (USE_REACT_AGENT=true)"
            )
        else:
            logger.info(
                "QueryHandler inicializado con ToolSelector (USE_REACT_AGENT=false)"
            )

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Manejar mensajes de texto del usuario.

        Valida autenticación y permisos antes de procesar la consulta.

        Args:
            update: Objeto de actualización de Telegram
            context: Contexto de la conversación
        """
        user_message = update.message.text
        user = update.effective_user
        chat_id = user.id
        start_time = time.time()

        # Obtener usuario autenticado del context (lo pone el middleware de auth)
        telegram_user = context.user_data.get('telegram_user')

        # Si no hay usuario autenticado, verificar autenticación
        if not telegram_user:
            db_manager = context.bot_data.get('db_manager')

            if not db_manager:
                await update.message.reply_text(
                    "❌ Error de configuración del sistema."
                )
                return

            with db_manager.get_session() as session:
                user_manager = UserManager(session)
                telegram_user = user_manager.get_user_by_chat_id(chat_id)

                if not telegram_user:
                    await update.message.reply_text(
                        "⚠️ No estás registrado en el sistema.\n\n"
                        "Por favor, usa /register para registrarte."
                    )
                    return

                if not telegram_user.is_verified:
                    await update.message.reply_text(
                        "⚠️ Tu cuenta no está verificada.\n\n"
                        "Consulta tu código de verificación en el Portal de Consola de Monitoreo.\n"
                        "Luego usa: /verify <codigo>"
                    )
                    return

                if not telegram_user.is_active:
                    await update.message.reply_text(
                        "⚠️ Tu cuenta está inactiva.\n\n"
                        "Por favor, contacta al administrador."
                    )
                    return

                # Guardar en context
                context.user_data['telegram_user'] = telegram_user

        logger.info(
            f"Usuario {telegram_user.id_usuario} ({telegram_user.nombre_completo}): "
            f"{user_message[:50]}..."
        )

        # Obtener db_manager
        db_manager = context.bot_data.get('db_manager')

        # Verificar permiso para consultas (comando /ia)
        with db_manager.get_session() as session:
            permission_checker = PermissionChecker(session)

            # Verificar permiso para hacer consultas con IA
            permission = permission_checker.check_permission(
                telegram_user.id_usuario,
                '/ia'
            )

            if not permission.is_allowed:
                # Registrar intento denegado
                permission_checker.log_operation(
                    user_id=telegram_user.id_usuario,
                    comando='/ia',
                    telegram_chat_id=chat_id,
                    telegram_username=user.username,
                    parametros={'query': user_message[:100]},
                    resultado='DENEGADO',
                    mensaje_error=permission.mensaje
                )

                await update.message.reply_text(
                    f"🚫 *Acceso Denegado*\n\n"
                    f"No tienes permiso para realizar consultas con IA.\n\n"
                    f"_{permission.mensaje}_",
                    parse_mode='Markdown'
                )
                return

        # Usar StatusMessage para mostrar progreso visual
        async with StatusMessage(update, initial_message="🔍 Amber analizando tu consulta...") as status:
            try:
                # Usar ReAct Agent si está habilitado el feature flag
                if self.use_react_agent:
                    response = await self._process_with_react(update, context, user_message)
                else:
                    response = await self._process_with_legacy(
                        update, context, user_message, telegram_user, db_manager
                    )

                # Completar con la respuesta (esto edita el mensaje de estado)
                await status.complete(response)

                # Calcular duración
                duration_ms = int((time.time() - start_time) * 1000)

                # Registrar operación exitosa
                with db_manager.get_session() as session:
                    permission_checker = PermissionChecker(session)
                    permission_checker.log_operation(
                        user_id=telegram_user.id_usuario,
                        comando='/ia',
                        telegram_chat_id=chat_id,
                        telegram_username=user.username,
                        parametros={'query': user_message[:200]},
                        resultado='EXITOSO',
                        duracion_ms=duration_ms
                    )

                logger.info(
                    f"Respuesta enviada exitosamente a usuario {telegram_user.id_usuario} "
                    f"({duration_ms}ms)"
                )

            except Exception as e:
                logger.error(
                    f"Error procesando mensaje de usuario {telegram_user.id_usuario}: {e}",
                    exc_info=True
                )

                # Registrar error
                duration_ms = int((time.time() - start_time) * 1000)
                with db_manager.get_session() as session:
                    permission_checker = PermissionChecker(session)
                    permission_checker.log_operation(
                        user_id=telegram_user.id_usuario,
                        comando='/ia',
                        telegram_chat_id=chat_id,
                        telegram_username=user.username,
                        parametros={'query': user_message[:200]},
                        resultado='ERROR',
                        mensaje_error=str(e),
                        duracion_ms=duration_ms
                    )

                # El StatusMessage manejará el error automáticamente en __aexit__
                # pero también enviamos un mensaje más detallado
                error_msg = (
                    "Lo siento, ocurrió un error al procesar tu consulta. "
                    "Por favor, intenta de nuevo o reformula tu pregunta.\n\n"
                    "Si el problema persiste, usa /help para más información."
                )
                await status.error(error_msg)

                # Re-lanzar la excepción para que el context manager la maneje
                raise

    async def _process_with_react(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
    ) -> str:
        """
        Procesa la consulta usando el nuevo sistema ReAct.

        Args:
            update: Update de Telegram
            context: Contexto de Telegram
            user_message: Mensaje del usuario

        Returns:
            Respuesta del agente
        """
        main_handler = _get_main_handler(self.agent)
        response = await main_handler.handle_telegram(update, context)
        return response

    async def _process_with_legacy(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_message: str,
        telegram_user,
        db_manager,
    ) -> str:
        """
        Procesa la consulta usando el sistema legacy (ToolSelector).

        Args:
            update: Update de Telegram
            context: Contexto de Telegram
            user_message: Mensaje del usuario
            telegram_user: Usuario autenticado
            db_manager: Gestor de base de datos

        Returns:
            Respuesta del agente
        """
        # FASE 3 - Hito 1: Auto-selección de tool
        selection_result = await self.tool_selector.select_tool(user_message)

        logger.info(
            f"Tool seleccionado para usuario {telegram_user.id_usuario}: "
            f"{selection_result.selected_tool} (confidence: {selection_result.confidence:.2f})"
        )

        # Construir contexto de ejecución
        with db_manager.get_session() as session:
            user_manager = UserManager(session)
            permission_checker = PermissionChecker(session)

            exec_context = (
                ExecutionContextBuilder()
                .with_telegram(update, context)
                .with_db_manager(db_manager)
                .with_llm_agent(self.agent)
                .with_user_manager(user_manager)
                .with_permission_checker(permission_checker)
                .build()
            )

            # Si hay tool seleccionado, ejecutar a través del orchestrator
            if selection_result.has_selection:
                # Obtener el comando del tool seleccionado
                tool = get_registry().get_tool_by_name(selection_result.selected_tool)
                command = tool.commands[0] if tool and tool.commands else "/ia"

                # Ejecutar tool via orchestrator
                tool_result = await self.tool_orchestrator.execute_command(
                    user_id=update.effective_user.id,
                    command=command,
                    params={"query": user_message},
                    context=exec_context
                )

                if tool_result.success:
                    return tool_result.data
                else:
                    # Si el tool falló, usar fallback a proceso directo
                    logger.warning(
                        f"Tool execution failed, using fallback: {tool_result.error}"
                    )
                    return await self.agent.process_query(user_message)
            else:
                # No hay tool seleccionado, usar proceso directo como fallback
                logger.info("No tool selected, using direct agent processing")
                return await self.agent.process_query(user_message)

    async def _send_response(self, update: Update, response: str):
        """
        Enviar respuesta al usuario, manejando mensajes largos.

        Args:
            update: Objeto de actualización de Telegram
            response: Respuesta a enviar
        """
        # Telegram tiene un límite de 4096 caracteres por mensaje
        MAX_MESSAGE_LENGTH = 4000  # Dejamos margen de seguridad

        if len(response) <= MAX_MESSAGE_LENGTH:
            # Enviar en un solo mensaje
            await update.message.reply_text(
                response,
                parse_mode='Markdown'
            )
        else:
            # Dividir en múltiples mensajes
            await self._send_long_response(update, response, MAX_MESSAGE_LENGTH)

    async def _send_long_response(
        self,
        update: Update,
        response: str,
        max_length: int
    ):
        """
        Dividir y enviar respuestas largas en múltiples mensajes.

        Args:
            update: Objeto de actualización de Telegram
            response: Respuesta a enviar
            max_length: Longitud máxima por mensaje
        """
        # Dividir por saltos de línea para no cortar información a mitad
        lines = response.split('\n')
        current_message = ""

        for line in lines:
            # Si agregar esta línea excede el límite, enviar el mensaje actual
            if len(current_message) + len(line) + 1 > max_length:
                if current_message:
                    await update.message.reply_text(
                        current_message,
                        parse_mode='Markdown'
                    )
                    current_message = line + '\n'
                else:
                    # La línea sola es más larga que el límite, enviarla directamente
                    await update.message.reply_text(
                        line[:max_length],
                        parse_mode='Markdown'
                    )
            else:
                current_message += line + '\n'

        # Enviar el último fragmento
        if current_message:
            await update.message.reply_text(
                current_message,
                parse_mode='Markdown'
            )

    async def _send_error_message(self, update: Update, user_friendly: bool = True):
        """
        Enviar mensaje de error al usuario.

        Args:
            update: Objeto de actualización de Telegram
            user_friendly: Si debe mostrarse mensaje amigable o técnico
        """
        if user_friendly:
            error_message = (
                "❌ **Error al procesar tu consulta**\n\n"
                "Lo siento, ocurrió un error inesperado. "
                "Por favor, intenta de nuevo o reformula tu pregunta.\n\n"
                "Si el problema persiste, usa /help para más información."
            )
        else:
            error_message = (
                "❌ **Error Técnico**\n\n"
                "Ocurrió un error al procesar tu solicitud. "
                "Por favor, contacta al administrador."
            )

        await update.message.reply_text(
            error_message,
            parse_mode='Markdown'
        )


def register_query_handlers(application: Application, agent: LLMAgent) -> None:
    """
    Registrar handler de queries en la aplicación.

    Args:
        application: Aplicación de Telegram
        agent: Instancia del agente LLM
    """
    # Crear instancia del handler
    query_handler = QueryHandler(agent)

    # Registrar handler para mensajes de texto que NO son comandos
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            query_handler.handle_text_message
        )
    )

    logger.info("Query handlers registrados exitosamente")
