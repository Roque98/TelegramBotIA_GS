"""
Inicializador de tools del sistema.

Registra todos los tools built-in en el ToolRegistry al iniciar el bot.
"""
import logging
from .tool_registry import get_registry
from .builtin.query_tool import QueryTool
from .builtin.alert_analysis_tool import AlertAnalysisTool

logger = logging.getLogger(__name__)


def initialize_builtin_tools() -> None:
    """
    Registrar todos los tools built-in en el registry.

    Esta función debe ser llamada al iniciar el bot para que
    todos los tools estén disponibles.
    """
    registry = get_registry()

    # Lista de tools built-in a registrar
    builtin_tools = [
        QueryTool(),
        AlertAnalysisTool(),
    ]

    # Registrar cada tool
    registered_count = 0
    for tool in builtin_tools:
        try:
            registry.register(tool)
            registered_count += 1
            logger.info(f"Tool registrado: {tool.name} (comandos: {tool.commands})")
        except ValueError as e:
            logger.error(f"Error registrando tool {tool.name}: {e}")
        except Exception as e:
            logger.error(f"Error inesperado registrando tool {tool.name}: {e}", exc_info=True)

    logger.info(
        f"Inicialización de tools completada: "
        f"{registered_count}/{len(builtin_tools)} tools registrados"
    )

    # Mostrar estadísticas
    stats = registry.get_stats()
    logger.info(f"Estadísticas del registry: {stats}")


def get_tool_summary() -> dict:
    """
    Obtener resumen de todos los tools registrados.

    Returns:
        Diccionario con información de los tools
    """
    registry = get_registry()
    tools = registry.get_all_tools()

    return {
        "total_tools": len(tools),
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "commands": tool.commands,
                "category": tool.category.value,
                "requires_auth": tool.requires_auth,
                "version": tool._metadata.version
            }
            for tool in tools
        ],
        "commands": registry.get_commands_list(),
        "stats": registry.get_stats()
    }
