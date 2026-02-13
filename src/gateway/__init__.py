"""
Gateway Package.

Proporciona normalización de entrada y orquestación de agentes:
- MessageGateway: Normaliza input de diferentes canales
- MainHandler: Orquesta ReActAgent con Memory
- Factory functions: Construcción de componentes

Note: MainHandler y factory se importan lazy para evitar dependencias
      de telegram en tests unitarios.
"""


def __getattr__(name: str):
    """Lazy imports para evitar dependencias pesadas."""
    if name == "MessageGateway":
        from .message_gateway import MessageGateway
        return MessageGateway
    elif name == "MainHandler":
        from .handler import MainHandler
        return MainHandler
    elif name in (
        "create_main_handler",
        "create_react_agent",
        "create_memory_service",
        "create_tool_registry",
        "HandlerManager",
        "get_handler_manager",
    ):
        from . import factory
        return getattr(factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MessageGateway",
    "MainHandler",
    "create_main_handler",
    "create_react_agent",
    "create_memory_service",
    "create_tool_registry",
    "HandlerManager",
    "get_handler_manager",
]
