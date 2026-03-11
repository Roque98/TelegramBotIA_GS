"""
QueryTool - Tool para procesar consultas a base de datos en lenguaje natural.

Usa el LLMAgent completo para aprovechar toda la arquitectura refactorizada:
- QueryClassifier: Clasificación automática DATABASE vs GENERAL
- SQLGenerator: Generación de SQL con LLM
- SQLValidator: Validación de seguridad
- ResponseFormatter: Formateo consistente de respuestas
"""
import logging
from typing import Any, Dict, List
from src.tools.tool_base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ParameterType
)
from src.tools.execution_context import ExecutionContext

logger = logging.getLogger(__name__)


class QueryTool(BaseTool):
    """
    Tool para procesar consultas a base de datos en lenguaje natural.

    Este tool demuestra el patrón 1 de uso del LLM: Uso Completo del LLMAgent.
    Delega toda la lógica de procesamiento al LLMAgent refactorizado, resultando
    en una implementación muy simple (~30 líneas vs ~150 del handler antiguo).
    """

    def get_metadata(self) -> ToolMetadata:
        """Obtener metadatos del tool."""
        return ToolMetadata(
            name="query",
            description="Consultar base de datos en lenguaje natural",
            commands=["/ia", "/query"],
            category=ToolCategory.DATABASE,
            requires_auth=True,
            required_permissions=["/ia"],
            version="2.0.0",
            author="System"
        )

    def get_parameters(self) -> List[ToolParameter]:
        """Obtener parámetros del tool."""
        return [
            ToolParameter(
                name="query",
                type=ParameterType.STRING,
                description="Consulta en lenguaje natural",
                required=True,
                validation_rules={
                    "min_length": 3,
                    "max_length": 1000
                }
            )
        ]

    async def execute(
        self,
        user_id: int,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ToolResult:
        """
        Ejecutar consulta usando LLMAgent completo.

        El LLMAgent maneja automáticamente:
        1. Clasificación de la query (DATABASE vs GENERAL)
        2. Generación de SQL (si aplica)
        3. Validación de seguridad
        4. Ejecución en base de datos
        5. Formateo de respuesta

        Args:
            user_id: ID del usuario que ejecuta
            params: Parámetros con la query
            context: Contexto de ejecución

        Returns:
            ToolResult con la respuesta procesada
        """
        # Validar que tenemos LLMAgent disponible
        is_valid, error = context.validate_required_components('llm_agent')
        if not is_valid:
            logger.error(f"Componente requerido no disponible: {error}")
            return ToolResult.error_result(
                error=error,
                user_friendly_error="❌ El sistema de consultas no está disponible"
            )

        user_query = params['query']

        # Construir contexto del usuario para que el LLM use valores literales
        # en lugar de variables T-SQL no declaradas (@telegramChatId, etc.)
        user_context = {
            'telegram_chat_id': context.get_chat_id(),
            'telegram_username': context.get_username(),
            'id_usuario': user_id
        }

        try:
            logger.info(f"Procesando query de usuario {user_id}: {user_query[:50]}...")

            # Usar LLMAgent completo - toda la magia sucede aquí
            # El LLMAgent orquesta automáticamente todos los componentes
            response = await context.llm_agent.process_query(user_query, user_context)

            logger.info(f"Query procesada exitosamente para usuario {user_id}")

            return ToolResult.success_result(
                data=response,
                metadata={
                    'query_length': len(user_query),
                    'user_id': user_id,
                    'tool_version': '2.0.0'
                }
            )

        except Exception as e:
            logger.error(f"Error procesando query: {e}", exc_info=True)
            return ToolResult.error_result(
                error=str(e),
                user_friendly_error=(
                    "❌ No pude procesar tu consulta en este momento.\n"
                    "Por favor, intenta reformular tu pregunta."
                )
            )


class IACommandHandler:
    """
    Handler específico para el comando /ia.

    Este handler mantiene compatibilidad con la interfaz actual de Telegram
    mientras delega la lógica al sistema de Tools.
    """

    def __init__(self, tool_orchestrator, db_manager, llm_agent):
        """
        Inicializar el handler.

        Args:
            tool_orchestrator: Orquestador de tools
            db_manager: Gestor de base de datos
            llm_agent: Agente LLM
        """
        self.tool_orchestrator = tool_orchestrator
        self.db_manager = db_manager
        self.llm_agent = llm_agent
        logger.info("IACommandHandler inicializado (delegando a QueryTool)")

    async def handle_ia_command(self, update, context):
        """
        Manejar comando /ia.

        Args:
            update: Update de Telegram
            context: Context de Telegram
        """
        from src.utils.status_message import StatusMessage
        from src.tools.execution_context import ExecutionContextBuilder

        user_id = update.effective_user.id

        # Extraer la query del mensaje
        message_text = update.message.text
        # Remover el comando /ia
        query_text = message_text.replace('/ia', '').strip()

        if not query_text:
            await update.message.reply_text(
                "❓ Por favor, proporciona una consulta después de /ia\n\n"
                "Ejemplo: /ia ¿Cuántos usuarios hay registrados?"
            )
            return

        # Crear mensaje de estado
        status_msg = StatusMessage(update, context)
        await status_msg.send("🔍 Analizando tu consulta...")

        try:
            # Construir contexto de ejecución
            exec_context = (
                ExecutionContextBuilder()
                .with_telegram(update, context)
                .with_db_manager(self.db_manager)
                .with_llm_agent(self.llm_agent)
                .build()
            )

            # Actualizar estado
            await status_msg.update("🤖 Procesando con IA...")

            # Ejecutar tool a través del orquestador
            result = await self.tool_orchestrator.execute_command(
                user_id=user_id,
                command="/ia",
                params={"query": query_text},
                context=exec_context
            )

            # Eliminar mensaje de estado
            await status_msg.delete()

            # Enviar respuesta
            if result.success:
                await update.message.reply_text(
                    result.data,
                    parse_mode='Markdown'
                )
            else:
                error_msg = result.user_friendly_error or result.error
                await update.message.reply_text(error_msg)

        except Exception as e:
            logger.error(f"Error en handle_ia_command: {e}", exc_info=True)
            await status_msg.delete()
            await update.message.reply_text(
                "❌ Ocurrió un error al procesar tu consulta.\n"
                "Por favor, intenta nuevamente."
            )
