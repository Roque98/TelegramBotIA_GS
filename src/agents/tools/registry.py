"""
Tool Registry - Registro singleton de herramientas para ReAct Agent.

Mantiene un registro de todas las herramientas disponibles y genera
la descripción de herramientas para el prompt del LLM.
"""

import logging
from typing import Optional

from .base import BaseTool, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro singleton de herramientas para el ReAct Agent.

    Permite registrar, buscar y generar prompts de herramientas.

    Example:
        >>> registry = ToolRegistry()
        >>> registry.register(DatabaseTool())
        >>> tool = registry.get("database_query")
        >>> prompt = registry.get_tools_prompt()
    """

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        """Implementar patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, BaseTool] = {}
            cls._instance._initialized = True
            logger.info("ToolRegistry inicializado")
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """
        Registra una herramienta en el registro.

        Args:
            tool: Herramienta a registrar

        Raises:
            ValueError: Si ya existe una herramienta con ese nombre
        """
        tool_name = tool.name

        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' ya está registrado")

        self._tools[tool_name] = tool
        logger.info(f"Tool registrado: {tool_name} ({tool.category.value})")

    def unregister(self, tool_name: str) -> bool:
        """
        Desregistra una herramienta.

        Args:
            tool_name: Nombre de la herramienta

        Returns:
            True si se desregistró, False si no existía
        """
        if tool_name not in self._tools:
            return False

        del self._tools[tool_name]
        logger.info(f"Tool desregistrado: {tool_name}")
        return True

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        Obtiene una herramienta por nombre.

        Args:
            tool_name: Nombre de la herramienta

        Returns:
            BaseTool o None si no existe
        """
        return self._tools.get(tool_name)

    def get_all(self) -> list[BaseTool]:
        """
        Obtiene todas las herramientas registradas.

        Returns:
            Lista de todas las herramientas
        """
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """
        Obtiene herramientas de una categoría específica.

        Args:
            category: Categoría a filtrar

        Returns:
            Lista de herramientas de esa categoría
        """
        return [tool for tool in self._tools.values() if tool.category == category]

    def get_tools_prompt(self) -> str:
        """
        Genera la descripción de herramientas para el prompt del LLM.

        Returns:
            String formateado con todas las herramientas disponibles
        """
        if not self._tools:
            return "No tools available."

        lines = ["## Available Tools\n"]

        # Agrupar por categoría
        by_category: dict[ToolCategory, list[BaseTool]] = {}
        for tool in self._tools.values():
            if tool.category not in by_category:
                by_category[tool.category] = []
            by_category[tool.category].append(tool)

        # Generar descripción por categoría
        for category in ToolCategory:
            tools = by_category.get(category, [])
            if tools:
                lines.append(f"### {category.value.title()}\n")
                for tool in tools:
                    lines.append(tool.definition.to_prompt_format())
                    lines.append("")

        return "\n".join(lines)

    def get_tool_names(self) -> list[str]:
        """
        Obtiene los nombres de todas las herramientas.

        Returns:
            Lista de nombres de herramientas
        """
        return list(self._tools.keys())

    def has_tool(self, tool_name: str) -> bool:
        """
        Verifica si existe una herramienta.

        Args:
            tool_name: Nombre de la herramienta

        Returns:
            True si existe, False si no
        """
        return tool_name in self._tools

    def clear(self) -> None:
        """
        Limpia todas las herramientas del registro.

        ADVERTENCIA: Usar solo en testing.
        """
        self._tools.clear()
        logger.warning("ToolRegistry limpiado completamente")

    @classmethod
    def reset(cls) -> None:
        """
        Resetea el singleton.

        ADVERTENCIA: Usar solo en testing.
        """
        if cls._instance:
            cls._instance._tools.clear()
        cls._instance = None

    def get_stats(self) -> dict[str, int]:
        """
        Obtiene estadísticas del registro.

        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_tools": len(self._tools),
            "by_category": {},
        }

        for category in ToolCategory:
            count = len(self.get_by_category(category))
            if count > 0:
                stats["by_category"][category.value] = count

        return stats

    def __repr__(self) -> str:
        return f"<ToolRegistry(tools={len(self._tools)})>"

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools


# Instancia global del registro
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Obtiene la instancia global del registro de herramientas.

    Returns:
        ToolRegistry singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
