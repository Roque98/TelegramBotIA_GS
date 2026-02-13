"""
Agente LLM para procesar consultas y generar SQL.

Refactorizado para actuar como orquestador de componentes especializados.
"""
import asyncio
import logging
from typing import Optional
from src.config.settings import settings
from src.database.connection import DatabaseManager
from .providers.base_provider import LLMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .classifiers.query_classifier import QueryClassifier, QueryType
from .sql.sql_generator import SQLGenerator
from .sql.sql_validator import SQLValidator
from .formatters.response_formatter import ResponseFormatter
from .prompts import get_default_manager
from .memory import MemoryManager
from .conversation_history import ConversationHistory

logger = logging.getLogger(__name__)

# Conjunto para mantener referencias a tareas en background
_background_tasks = set()


class LLMAgent:
    """Agente que procesa consultas en lenguaje natural y las convierte a SQL."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        """
        Inicializar el agente.

        Args:
            db_manager: Gestor de base de datos (opcional, se crea si no se proporciona)
            llm_provider: Proveedor de LLM (opcional, se crea si no se proporciona)
        """
        # Inicializar base de datos
        self.db_manager = db_manager or DatabaseManager()

        # Inicializar proveedor LLM
        self.llm_provider = llm_provider or self._initialize_llm_provider()

        # Inicializar gestor de prompts
        self.prompt_manager = get_default_manager()

        # Inicializar componentes especializados
        self.query_classifier = QueryClassifier(self.llm_provider)
        self.sql_generator = SQLGenerator(self.llm_provider)
        self.sql_validator = SQLValidator()
        self.response_formatter = ResponseFormatter(
            max_results_display=10,
            llm_provider=self.llm_provider,
            use_natural_language=True
        )

        # Inicializar gestor de memoria persistente
        self.memory_manager = MemoryManager(self.db_manager, self.llm_provider)

        # Inicializar historial conversacional (últimos 3 mensajes)
        self.conversation_history = ConversationHistory(max_messages=3)

        logger.info(
            f"Agente LLM inicializado con proveedor: {self.llm_provider.get_provider_name()}, "
            f"modelo: {self.llm_provider.get_model_name()}"
        )

    def _initialize_llm_provider(self) -> LLMProvider:
        """
        Inicializar el proveedor de LLM según la configuración.

        Returns:
            Instancia del proveedor de LLM

        Raises:
            ValueError: Si no se encuentra ninguna API key configurada
        """
        if settings.openai_api_key:
            # Mostrar token parcialmente ocultado para seguridad
            masked_token = self._mask_token(settings.openai_api_key)
            logger.info(f"Usando proveedor OpenAI - Token: {masked_token}")
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
        elif settings.anthropic_api_key:
            # Mostrar token parcialmente ocultado para seguridad
            masked_token = self._mask_token(settings.anthropic_api_key)
            logger.info(f"Usando proveedor Anthropic - Token: {masked_token}")
            return AnthropicProvider(
                api_key=settings.anthropic_api_key
            )
        else:
            raise ValueError("No se encontró ninguna API key de LLM configurada")

    @staticmethod
    def _mask_token(token: str) -> str:
        """
        Ocultar parcialmente el token para seguridad.

        Args:
            token: Token completo

        Returns:
            Token con caracteres del medio ocultados
        """
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    async def process_query(
        self,
        user_query: str,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None
    ) -> str:
        """
        Procesar una consulta del usuario.

        Este método orquesta todo el flujo:
        1. Clasificar la consulta
        2. Si es general, responder con el LLM
        3. Si es conocimiento institucional, responder con knowledge base
        4. Si requiere BD, generar SQL, validar, ejecutar y formatear

        Args:
            user_query: Consulta en lenguaje natural del usuario
            user_id: ID del usuario para memoria persistente (opcional)
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta formateada para el usuario
        """
        # Guardar mensaje del usuario en el historial conversacional
        if user_id:
            self.conversation_history.add_user_message(user_id, user_query)

        # Obtener contexto de memoria persistente y conversacional
        memory_context = ""
        conversation_context = ""
        if user_id:
            memory_context = self.memory_manager.get_memory_context(user_id)
            conversation_context = self.conversation_history.get_context_string(user_id, include_last_n=2)

        # Combinar contextos
        full_context = ""
        if conversation_context:
            full_context += conversation_context + "\n"
        if memory_context:
            full_context += memory_context

        try:
            # 1. Clasificar la consulta
            query_type = await self.query_classifier.classify(user_query)

            # 2. Si es una consulta general, responder directamente
            if query_type == QueryType.GENERAL:
                response = await self._process_general_query(user_query, full_context, user_name)

                # Registrar interacción para actualización de memoria (asíncrono)
                if user_id:
                    task = asyncio.create_task(self.memory_manager.record_interaction(user_id))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                    # Guardar respuesta en historial conversacional
                    self.conversation_history.add_bot_response(user_id, response)

                return response

            # 3. Si es conocimiento institucional, responder con knowledge base
            if query_type == QueryType.KNOWLEDGE:
                response = await self._process_knowledge_query(user_query, full_context, user_name)

                # Registrar interacción para actualización de memoria (asíncrono)
                if user_id:
                    task = asyncio.create_task(self.memory_manager.record_interaction(user_id))
                    _background_tasks.add(task)
                    task.add_done_callback(_background_tasks.discard)
                    # Guardar respuesta en historial conversacional
                    self.conversation_history.add_bot_response(user_id, response)

                return response

            # 4. Si requiere base de datos, seguir el flujo completo
            response = await self._process_database_query(user_query, user_name)

            # Registrar interacción para actualización de memoria (asíncrono)
            if user_id:
                task = asyncio.create_task(self.memory_manager.record_interaction(user_id))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)
                # Guardar respuesta en historial conversacional
                self.conversation_history.add_bot_response(user_id, response)

            return response

        except Exception as e:
            logger.error(f"Error en process_query: {e}", exc_info=True)
            return self.response_formatter.format_error(str(e), user_friendly=True)

    async def _process_general_query(
        self,
        user_query: str,
        memory_context: str = "",
        user_name: Optional[str] = None
    ) -> str:
        """
        Procesar una consulta general que no requiere base de datos.

        Ahora responde preguntas razonables usando el LLM.
        Solo muestra el mensaje de capacidades para saludos o temas absurdos.

        Args:
            user_query: Consulta del usuario
            memory_context: Contexto de memoria del usuario (opcional)
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta de Iris
        """
        logger.info("Consulta general detectada")

        # Detectar saludos para personalizar la respuesta
        saludos = ["hola", "hello", "hi", "buenos días", "buenas tardes", "buenas noches", "hey"]
        es_saludo = any(saludo in user_query.lower() for saludo in saludos)

        if es_saludo:
            # Para saludos, generar mensaje dinámico desde BD
            logger.info("Saludo detectado - respondiendo con capacidades")
            greeting_message = self._generate_greeting_from_db(user_name)
            return greeting_message

        # Para preguntas generales razonables, usar el LLM
        logger.info("Pregunta general - respondiendo con LLM")
        return await self._answer_general_question_with_llm(
            user_query,
            memory_context,
            user_name
        )

    def _generate_greeting_from_db(self, user_name: Optional[str] = None) -> str:
        """
        Generar mensaje de saludo dinámicamente desde la BD.

        Args:
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Mensaje de saludo con categorías y ejemplos desde BD
        """
        try:
            from src.agent.knowledge import KnowledgeRepository

            # Usar el mismo db_manager que el agente
            repository = KnowledgeRepository(self.db_manager)

            # Verificar health check primero
            if not repository.health_check():
                logger.warning("BD no disponible para generar saludo, usando fallback")
                raise ConnectionError("BD no responde al health check")

            # Obtener categorías con conteo
            categories = repository.get_categories_info()
            logger.debug(f"Categorías obtenidas: {len(categories)}")

            # Construir texto de categorías
            categories_text = ""
            for cat in categories:
                if cat.get('entry_count', 0) > 0:
                    categories_text += f"• {cat['icon']} {cat['display_name']}\n"

            # Obtener ejemplos de preguntas
            examples = repository.get_example_questions(limit=3)
            logger.debug(f"Ejemplos obtenidos: {len(examples)}")
            examples_text = "\n".join([f"• `{q}`" for q in examples])

            logger.info("✅ Saludo generado dinámicamente desde BD")
            # Personalizar saludo con nombre si está disponible
            greeting = f"👋 ¡Hola{', ' + user_name if user_name else ''}! Soy **Iris**, analista del Centro de Operaciones ✨\n\n"
            return (
                f"{greeting}"
                "Estoy aquí para ayudarte con información sobre:\n\n"
                f"{categories_text}\n"
                "💡 **Ejemplos de preguntas:**\n"
                f"{examples_text}\n\n"
                "¿En qué puedo ayudarte hoy? 🎯"
            )

        except Exception as e:
            logger.error(f"❌ Error generando saludo desde BD: {e}", exc_info=True)
            # Fallback básico si falla la BD
            greeting = f"👋 ¡Hola{', ' + user_name if user_name else ''}! Soy **Iris**, analista del Centro de Operaciones ✨\n\n"
            return (
                f"{greeting}"
                "Estoy aquí para ayudarte con:\n\n"
                "📋 Información Institucional\n"
                "📊 Consultas de Datos\n"
                "💡 Preguntas y soporte\n\n"
                "¿En qué puedo ayudarte hoy? 🎯"
            )

    def _generate_general_response_from_db(self, user_name: Optional[str] = None) -> str:
        """
        Generar respuesta general dinámicamente desde la BD.

        Args:
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Mensaje con especialidades basadas en categorías de BD
        """
        try:
            from src.agent.knowledge import KnowledgeRepository

            # Usar el mismo db_manager que el agente
            repository = KnowledgeRepository(self.db_manager)

            # Verificar health check primero
            if not repository.health_check():
                logger.warning("BD no disponible para generar respuesta general, usando fallback")
                raise ConnectionError("BD no responde al health check")

            # Obtener categorías con conteo
            categories = repository.get_categories_info()
            logger.debug(f"Categorías obtenidas para respuesta general: {len(categories)}")

            # Construir texto de especialidades (solo categorías con contenido)
            specialties_text = ""
            for cat in categories:
                if cat.get('entry_count', 0) > 0:
                    specialties_text += f"{cat['icon']} {cat['display_name']}\n"

            logger.info("✅ Respuesta general generada dinámicamente desde BD")
            return (
                "💭 Hmm, esa es una pregunta interesante, pero estoy especializada en información empresarial y consultas de datos.\n\n"
                "🎯 **Mis especialidades:**\n\n"
                f"{specialties_text}\n"
                "¿Hay algo relacionado con estos temas en lo que pueda ayudarte? ✨\n\n"
                "_Iris, siempre dispuesta a ayudar_ 💪"
            )

        except Exception as e:
            logger.error(f"❌ Error generando respuesta general desde BD: {e}", exc_info=True)
            # Fallback básico si falla la BD
            return (
                "💭 Hmm, esa es una pregunta interesante, pero estoy especializada en información empresarial y consultas de datos.\n\n"
                "🎯 **Mis especialidades:**\n\n"
                "📋 Políticas y procesos\n"
                "📊 Consultas de datos\n"
                "💡 Información de sistemas\n\n"
                "¿Hay algo relacionado con estos temas en lo que pueda ayudarte? ✨\n\n"
                "_Iris, siempre dispuesta a ayudar_ 💪"
            )

    async def _answer_general_question_with_llm(
        self,
        user_query: str,
        memory_context: str = "",
        user_name: Optional[str] = None
    ) -> str:
        """
        Responder preguntas generales usando el LLM.

        El bot puede responder preguntas generales razonables como asistente,
        manteniendo su personalidad de Iris.

        Args:
            user_query: Consulta del usuario
            memory_context: Contexto de memoria del usuario (opcional)
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta generada por el LLM
        """
        # Construir prompt con personalidad de Iris
        system_prompt = """Eres Iris, una asistente virtual amigable y profesional del Centro de Operaciones.

Tu personalidad:
- Amigable, cercana y profesional
- Usas emojis ocasionalmente para ser más expresiva ✨
- Te gusta ayudar y eres muy colaborativa
- Eres clara y concisa en tus respuestas
- Tu especialidad principal es información empresarial y consultas de datos

Instrucciones:
- Responde preguntas generales de forma útil y precisa
- Mantén respuestas cortas (máximo 3-4 párrafos)
- Si la pregunta es muy fuera de contexto o absurda, sugiere amablemente que tu especialidad es información empresarial
- Firma tus mensajes como "_Iris_" cuando sea apropiado
"""

        # Agregar contexto de memoria si existe
        if memory_context:
            system_prompt += f"\n\nContexto del usuario:\n{memory_context}"

        try:
            # Combinar system prompt con user message
            user_prefix = f"{user_name}: " if user_name else "Usuario: "
            full_prompt = f"{system_prompt}\n\n{user_prefix}{user_query}\n\nIris:"

            # Llamar al LLM provider
            response = await self.llm_provider.generate(
                prompt=full_prompt,
                max_tokens=500
            )

            logger.info("✅ Respuesta general generada con LLM")
            return response.strip()

        except Exception as e:
            logger.error(f"Error generando respuesta con LLM: {e}", exc_info=True)
            # Fallback en caso de error
            return (
                "💭 Interesante pregunta. Sin embargo, mi especialidad principal es ayudarte con:\n\n"
                "📋 Información institucional\n"
                "📊 Consultas de datos empresariales\n"
                "💡 Procesos y políticas\n\n"
                "¿Hay algo relacionado con estos temas en lo que pueda ayudarte? ✨\n\n"
                "_Iris, siempre lista para ayudar_ 💪"
            )

    async def _process_knowledge_query(
        self,
        user_query: str,
        memory_context: str = "",
        user_name: Optional[str] = None
    ) -> str:
        """
        Procesar una consulta de conocimiento institucional.

        Args:
            user_query: Consulta del usuario
            memory_context: Contexto de memoria del usuario (opcional)
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta con conocimiento institucional
        """
        logger.info("Procesando consulta de conocimiento institucional")

        # Obtener contexto de conocimiento
        knowledge_context = self.query_classifier.get_knowledge_context(user_query, top_k=3)

        if not knowledge_context:
            # Si por alguna razón no hay contexto, responder con LLM general
            logger.warning("No se obtuvo contexto de conocimiento, respondiendo con LLM general")
            return await self._process_general_query(user_query)

        # DEBUG: Log del contexto de conocimiento
        logger.info(f"Contexto de conocimiento obtenido ({len(knowledge_context)} caracteres)")
        logger.debug(f"Contexto: {knowledge_context[:500]}...")

        # Usar el sistema de prompts con contexto de conocimiento y memoria
        prompt = self.prompt_manager.get_prompt(
            'general_response',
            version=2,
            user_query=user_query,
            context=knowledge_context,
            user_memory=memory_context,
            user_name=user_name or ""
        )

        # DEBUG: Log del prompt completo (primeras 1000 caracteres)
        logger.debug(f"Prompt enviado al LLM: {prompt[:1000]}...")

        try:
            response = await self.llm_provider.generate(prompt, max_tokens=1024)
            return self.response_formatter.format_general_response(response)

        except Exception as e:
            logger.error(f"Error procesando consulta de conocimiento: {e}")
            return (
                "❌ Oh, tuve un problema procesando esa pregunta.\n\n"
                "¿Podrías intentarlo de nuevo o reformularla?\n\n"
                "_Iris está aquí para ayudarte_ ✨"
            )

    async def _process_database_query(
        self,
        user_query: str,
        user_name: Optional[str] = None
    ) -> str:
        """
        Procesar una consulta que requiere acceso a base de datos.

        Args:
            user_query: Consulta del usuario
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta formateada con resultados
        """
        logger.info("Procesando consulta de base de datos")

        # 1. Obtener esquema de la base de datos
        schema = await asyncio.to_thread(self.db_manager.get_schema)

        # 2. Generar SQL
        sql_query = await self.sql_generator.generate_sql(user_query, schema)

        if not sql_query:
            return (
                "🤔 Hmm, tuve dificultades generando la consulta para eso.\n\n"
                "¿Podrías reformular tu pregunta de otra manera?\n\n"
                "_Iris intentando ayudarte_ 💪"
            )

        # 3. Validar SQL
        is_valid, error_message = self.sql_validator.validate(sql_query)

        if not is_valid:
            logger.warning(f"SQL no válido: {error_message}")
            return (
                "🔒 Esa consulta no pasó las validaciones de seguridad.\n\n"
                "Por tu seguridad, solo puedo ejecutar consultas de lectura.\n\n"
                "¿Necesitas algo más? _Iris aquí para ayudarte_ ✨"
            )

        # 4. Ejecutar la consulta
        try:
            results = await asyncio.to_thread(self.db_manager.execute_query, sql_query)
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            return (
                "❌ Ups, tuve un problema ejecutando la consulta en la base de datos.\n\n"
                "Esto puede ser temporal. ¿Intentamos de nuevo?\n\n"
                "_Iris aquí para ayudarte_ 💪"
            )

        # 5. Formatear respuesta
        return await self.response_formatter.format_query_results(
            user_query=user_query,
            sql_query=sql_query,
            results=results,
            include_sql=False,  # Cambiar a True para debugging
            user_name=user_name
        )

