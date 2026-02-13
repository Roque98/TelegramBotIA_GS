"""
Tools Package - Herramientas para el ReAct Agent.

Este paquete contiene las herramientas que el agente puede usar
durante su ciclo de razonamiento y acción.

Herramientas disponibles:
- DatabaseTool: Consultas SQL a la base de datos
- KnowledgeTool: Búsqueda en base de conocimiento
- CalculateTool: Cálculos matemáticos seguros
- DateTimeTool: Operaciones con fechas/horas
"""

from .base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from .registry import ToolRegistry, get_tool_registry

# Tools específicos - importación lazy para evitar dependencias circulares
__all__ = [
    # Base
    "BaseTool",
    "ToolCategory",
    "ToolDefinition",
    "ToolParameter",
    "ToolResult",
    # Registry
    "ToolRegistry",
    "get_tool_registry",
    # Tools (importar según necesidad)
    "DatabaseTool",
    "KnowledgeTool",
    "CalculateTool",
    "DateTimeTool",
]


def __getattr__(name: str):
    """Importación lazy de tools específicos."""
    if name == "DatabaseTool":
        from .database_tool import DatabaseTool
        return DatabaseTool
    if name == "KnowledgeTool":
        from .knowledge_tool import KnowledgeTool
        return KnowledgeTool
    if name == "CalculateTool":
        from .calculate_tool import CalculateTool
        return CalculateTool
    if name == "DateTimeTool":
        from .datetime_tool import DateTimeTool
        return DateTimeTool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
