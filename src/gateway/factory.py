"""
Factory - Construcción de MainHandler con todas sus dependencias.

Proporciona funciones factory para crear el handler principal
con todas las dependencias configuradas.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from src.agents.react.agent import ReActAgent
from src.agents.tools.registry import ToolRegistry
from src.agents.tools.database_tool import DatabaseTool
from src.agents.tools.knowledge_tool import KnowledgeTool
from src.agents.tools.calculate_tool import CalculateTool
from src.agents.tools.datetime_tool import DateTimeTool
from src.agent.knowledge import KnowledgeManager
from src.config.settings import settings
from src.memory.service import MemoryService
from src.memory.repository import MemoryRepository
from src.memory.context_builder import ContextBuilder

from .handler import MainHandler

if TYPE_CHECKING:
    from src.agent.llm_agent import LLMAgent
    from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


def create_tool_registry(
    db_manager: Optional[Any] = None,
    knowledge_manager: Optional[Any] = None,
) -> ToolRegistry:
    """
    Crea y configura el registro de herramientas.

    Args:
        db_manager: Gestor de base de datos
        knowledge_manager: Gestor de conocimiento

    Returns:
        ToolRegistry configurado
    """
    # Resetear singleton para tests
    ToolRegistry.reset()
    registry = ToolRegistry()

    # Crear KnowledgeManager si no se proporciona
    km = knowledge_manager or KnowledgeManager()

    # Registrar herramientas
    registry.register(DatabaseTool(db_manager=db_manager))
    registry.register(KnowledgeTool(knowledge_manager=km))
    registry.register(CalculateTool())
    registry.register(DateTimeTool())

    logger.info(f"ToolRegistry created with {len(registry.list_tools())} tools")

    return registry


def create_react_agent(
    llm_provider: Any,
    db_manager: Optional[Any] = None,
    knowledge_manager: Optional[Any] = None,
) -> ReActAgent:
    """
    Crea el agente ReAct con sus dependencias.

    Args:
        llm_provider: Proveedor de LLM
        db_manager: Gestor de base de datos
        knowledge_manager: Gestor de conocimiento

    Returns:
        ReActAgent configurado
    """
    tool_registry = create_tool_registry(db_manager, knowledge_manager)

    agent = ReActAgent(
        llm=llm_provider,
        tool_registry=tool_registry,
        max_iterations=10,
        temperature=0.1,
    )

    logger.info("ReActAgent created")

    return agent


def create_memory_service(
    db_manager: Optional[Any] = None,
) -> MemoryService:
    """
    Crea el servicio de memoria.

    Args:
        db_manager: Gestor de base de datos

    Returns:
        MemoryService configurado
    """
    repository = MemoryRepository(db_manager=db_manager)
    context_builder = ContextBuilder(
        repository=repository,
        max_working_memory=10,
    )

    service = MemoryService(
        repository=repository,
        context_builder=context_builder,
        cache_ttl_seconds=300,  # 5 minutos
        max_cache_size=1000,
    )

    logger.info("MemoryService created")

    return service


def create_main_handler(
    llm_agent: Any,
    db_manager: Optional[Any] = None,
) -> MainHandler:
    """
    Crea el handler principal con todas sus dependencias.

    Args:
        llm_agent: Agente LLM existente (para LLM provider y fallback)
        db_manager: Gestor de base de datos

    Returns:
        MainHandler configurado
    """
    # Usar el DB manager del llm_agent si no se proporciona uno
    db = db_manager or llm_agent.db_manager

    # Obtener knowledge_manager del llm_agent
    knowledge_manager = getattr(
        llm_agent.query_classifier, 'knowledge_manager', None
    )

    # Crear componentes
    react_agent = create_react_agent(
        llm_provider=llm_agent.llm_provider,
        db_manager=db,
        knowledge_manager=knowledge_manager,
    )

    memory_service = create_memory_service(db_manager=db)

    # Crear handler principal
    handler = MainHandler(
        react_agent=react_agent,
        memory_service=memory_service,
        fallback_agent=llm_agent,  # LLMAgent como fallback
        use_fallback_on_error=settings.react_fallback_on_error,
    )

    logger.info("MainHandler created with ReActAgent and fallback")

    return handler


class HandlerManager:
    """
    Gestor singleton para el MainHandler.

    Permite acceder al handler desde cualquier parte de la aplicación.
    """

    _instance: Optional["HandlerManager"] = None
    _handler: Optional[MainHandler] = None

    def __new__(cls) -> "HandlerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self,
        llm_agent: Any,
        db_manager: Optional[Any] = None,
    ) -> MainHandler:
        """
        Inicializa el handler.

        Args:
            llm_agent: Agente LLM existente
            db_manager: Gestor de base de datos

        Returns:
            MainHandler inicializado
        """
        if self._handler is None:
            self._handler = create_main_handler(llm_agent, db_manager)
            logger.info("HandlerManager initialized")
        return self._handler

    @property
    def handler(self) -> Optional[MainHandler]:
        """Retorna el handler actual."""
        return self._handler

    def is_initialized(self) -> bool:
        """Verifica si el handler está inicializado."""
        return self._handler is not None

    @classmethod
    def reset(cls) -> None:
        """Resetea el singleton (para tests)."""
        cls._instance = None
        cls._handler = None


def get_handler_manager() -> HandlerManager:
    """Obtiene la instancia del HandlerManager."""
    return HandlerManager()
