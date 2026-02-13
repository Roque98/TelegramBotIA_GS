"""
Registro centralizado de tools.

Implementa el patrón Singleton para mantener un registro global
de todos los tools disponibles en el sistema.
"""
import logging
from typing import Any, Dict, List, Optional, Set
from .tool_base import BaseTool, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registro singleton de tools disponibles en el sistema.

    Permite registrar, buscar y filtrar tools por diferentes criterios.
    """

    _instance: Optional["ToolRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "ToolRegistry":
        """Implementar patrón Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializar el registro (solo una vez)."""
        if not self._initialized:
            self._tools_by_name: Dict[str, BaseTool] = {}
            self._tools_by_command: Dict[str, BaseTool] = {}
            self._tools_by_category: Dict[ToolCategory, Set[str]] = {}
            self._initialized = True
            logger.info("ToolRegistry inicializado")

    def register(self, tool: BaseTool) -> None:
        """
        Registrar un nuevo tool en el sistema.

        Args:
            tool: Tool a registrar

        Raises:
            ValueError: Si el tool ya está registrado o tiene conflictos de comandos
        """
        tool_name = tool.name

        # Verificar si el tool ya está registrado
        if tool_name in self._tools_by_name:
            raise ValueError(f"Tool '{tool_name}' ya está registrado")

        # Verificar conflictos de comandos
        for command in tool.commands:
            if command in self._tools_by_command:
                existing_tool = self._tools_by_command[command]
                raise ValueError(
                    f"Comando '{command}' ya está registrado por el tool '{existing_tool.name}'"
                )

        # Registrar tool por nombre
        self._tools_by_name[tool_name] = tool

        # Registrar tool por cada comando
        for command in tool.commands:
            self._tools_by_command[command] = tool

        # Registrar tool por categoría
        if tool.category not in self._tools_by_category:
            self._tools_by_category[tool.category] = set()
        self._tools_by_category[tool.category].add(tool_name)

        logger.info(
            f"Tool registrado: {tool_name} "
            f"(comandos: {tool.commands}, categoría: {tool.category.value})"
        )

    def unregister(self, tool_name: str) -> bool:
        """
        Desregistrar un tool del sistema.

        Args:
            tool_name: Nombre del tool a desregistrar

        Returns:
            bool: True si se desregistró exitosamente, False si no existía
        """
        if tool_name not in self._tools_by_name:
            logger.warning(f"Intento de desregistrar tool inexistente: {tool_name}")
            return False

        tool = self._tools_by_name[tool_name]

        # Eliminar de comandos
        for command in tool.commands:
            if command in self._tools_by_command:
                del self._tools_by_command[command]

        # Eliminar de categoría
        if tool.category in self._tools_by_category:
            self._tools_by_category[tool.category].discard(tool_name)
            # Limpiar categoría si está vacía
            if not self._tools_by_category[tool.category]:
                del self._tools_by_category[tool.category]

        # Eliminar de nombres
        del self._tools_by_name[tool_name]

        logger.info(f"Tool desregistrado: {tool_name}")
        return True

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """
        Buscar un tool por su nombre.

        Args:
            name: Nombre del tool

        Returns:
            BaseTool o None si no existe
        """
        return self._tools_by_name.get(name)

    def get_tool_by_command(self, command: str) -> Optional[BaseTool]:
        """
        Buscar un tool por su comando.

        Args:
            command: Comando del tool (ej: "/ia", "/help")

        Returns:
            BaseTool o None si no existe
        """
        return self._tools_by_command.get(command)

    def get_all_tools(self) -> List[BaseTool]:
        """
        Obtener todos los tools registrados.

        Returns:
            Lista de todos los tools
        """
        return list(self._tools_by_name.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Obtener todos los tools de una categoría específica.

        Args:
            category: Categoría de tools

        Returns:
            Lista de tools de la categoría
        """
        if category not in self._tools_by_category:
            return []

        tool_names = self._tools_by_category[category]
        return [self._tools_by_name[name] for name in tool_names]

    def get_user_available_tools(
        self,
        user_id: int,
        permission_checker: "PermissionChecker"
    ) -> List[BaseTool]:
        """
        Obtener tools disponibles para un usuario específico.

        Filtra los tools según los permisos del usuario.

        Args:
            user_id: ID del usuario
            permission_checker: Checker de permisos del sistema

        Returns:
            Lista de tools disponibles para el usuario
        """
        available_tools = []

        for tool in self._tools_by_name.values():
            # Si no requiere autenticación, está disponible para todos
            if not tool.requires_auth:
                available_tools.append(tool)
                continue

            # Verificar permisos requeridos
            has_all_permissions = True
            for permission in tool.required_permissions:
                if not permission_checker.has_permission(user_id, permission):
                    has_all_permissions = False
                    break

            if has_all_permissions:
                available_tools.append(tool)

        return available_tools

    def get_tools_count(self) -> int:
        """
        Obtener el número total de tools registrados.

        Returns:
            int: Número de tools
        """
        return len(self._tools_by_name)

    def get_commands_list(self) -> List[str]:
        """
        Obtener lista de todos los comandos registrados.

        Returns:
            Lista de comandos
        """
        return list(self._tools_by_command.keys())

    def clear(self) -> None:
        """
        Limpiar todos los tools del registro.

        ADVERTENCIA: Usar solo en testing o reinicios completos del sistema.
        """
        self._tools_by_name.clear()
        self._tools_by_command.clear()
        self._tools_by_category.clear()
        logger.warning("ToolRegistry limpiado completamente")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del registro.

        Returns:
            Diccionario con estadísticas
        """
        return {
            "total_tools": len(self._tools_by_name),
            "total_commands": len(self._tools_by_command),
            "categories": {
                category.value: len(tools)
                for category, tools in self._tools_by_category.items()
            }
        }

    def __repr__(self) -> str:
        """Representación en string del registro."""
        return f"<ToolRegistry(tools={len(self._tools_by_name)}, commands={len(self._tools_by_command)})>"


# Instancia global del registro
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Obtener la instancia global del registro.

    Returns:
        ToolRegistry: Instancia singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
