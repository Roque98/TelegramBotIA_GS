"""
Módulo de Memoria Persistente para el Bot.

Este módulo proporciona funcionalidad de memoria persistente que permite
al bot recordar contexto de usuarios entre conversaciones.

Componentes principales:
- MemoryManager: Orquestador principal
- MemoryRepository: Acceso a base de datos
- MemoryExtractor: Generación de resúmenes con LLM
- MemoryInjector: Formateo para inyección en prompts

Uso básico:
    >>> from src.agent.memory import MemoryManager
    >>> from src.database.connection import DatabaseManager
    >>> from src.agent.providers import OpenAIProvider
    >>>
    >>> db_manager = DatabaseManager()
    >>> llm_provider = OpenAIProvider()
    >>> memory_manager = MemoryManager(db_manager, llm_provider)
    >>>
    >>> # Obtener contexto para prompt
    >>> context = memory_manager.get_memory_context(user_id=123)
    >>>
    >>> # Registrar interacción (asíncrono)
    >>> await memory_manager.record_interaction(user_id=123)
"""

from .memory_manager import MemoryManager
from .memory_repository import (
    MemoryRepository,
    UserMemoryProfile,
    UserInteraction
)
from .memory_extractor import MemoryExtractor
from .memory_injector import MemoryInjector

__all__ = [
    'MemoryManager',
    'MemoryRepository',
    'UserMemoryProfile',
    'UserInteraction',
    'MemoryExtractor',
    'MemoryInjector'
]

__version__ = '1.0.0'
