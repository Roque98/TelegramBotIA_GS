"""
Base Tool - Clases base para herramientas del ReAct Agent.

Este módulo define:
- ToolCategory: Categorías de herramientas
- ToolParameter: Definición de parámetros
- ToolDefinition: Metadata para generar prompts
- ToolResult: Resultado de ejecución con observación
- BaseTool: Clase abstracta base
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categorías de herramientas disponibles para ReAct."""

    DATABASE = "database"
    KNOWLEDGE = "knowledge"
    CALCULATION = "calculation"
    DATETIME = "datetime"
    UTILITY = "utility"


class ToolParameter(BaseModel):
    """
    Define un parámetro de entrada para una herramienta.

    Attributes:
        name: Nombre del parámetro
        param_type: Tipo de dato (string, integer, float, boolean)
        description: Descripción para el LLM
        required: Si es obligatorio
        default: Valor por defecto
        examples: Ejemplos de valores válidos
    """

    name: str
    param_type: str = "string"
    description: str
    required: bool = True
    default: Optional[Any] = None
    examples: list[str] = Field(default_factory=list)

    def to_prompt_format(self) -> str:
        """Genera formato para el prompt del LLM."""
        required_str = "(required)" if self.required else "(optional)"
        return f"  - {self.name} ({self.param_type}, {required_str}): {self.description}"


class ToolDefinition(BaseModel):
    """
    Metadata de una herramienta para generar prompts.

    Attributes:
        name: Nombre único de la herramienta
        description: Descripción de qué hace
        category: Categoría de la herramienta
        parameters: Lista de parámetros que acepta
        examples: Ejemplos de uso para few-shot
        returns: Descripción de lo que retorna
    """

    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter] = Field(default_factory=list)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    returns: str = "Resultado de la operación"

    def to_prompt_format(self) -> str:
        """
        Genera descripción formateada para el prompt del LLM.

        Returns:
            String con formato para incluir en el system prompt
        """
        lines = [
            f"- **{self.name}**: {self.description}",
        ]

        if self.parameters:
            lines.append("  Parameters:")
            for param in self.parameters:
                lines.append(param.to_prompt_format())

        if self.examples:
            lines.append("  Example:")
            example = self.examples[0]
            params_str = ", ".join(f'"{k}": "{v}"' for k, v in example.items())
            lines.append(f"    {{{params_str}}}")

        return "\n".join(lines)

    def get_json_schema(self) -> dict[str, Any]:
        """
        Genera JSON schema para structured output.

        Returns:
            Diccionario con schema de parámetros
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.param_type,
                "description": param.description,
            }
            if param.examples:
                prop["examples"] = param.examples
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class ToolResult(BaseModel):
    """
    Resultado de la ejecución de una herramienta.

    Attributes:
        success: Si la ejecución fue exitosa
        data: Datos resultantes
        error: Mensaje de error si falló
        execution_time_ms: Tiempo de ejecución
        metadata: Datos adicionales
    """

    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_observation(self, max_length: int = 2000) -> str:
        """
        Convierte el resultado a formato de observación para el scratchpad.

        Args:
            max_length: Longitud máxima de la observación

        Returns:
            String formateado para el scratchpad
        """
        if not self.success:
            return f"Error: {self.error}"

        # Caso: sin resultados
        if self.data is None:
            return "No results found"

        # Caso: lista vacía
        if isinstance(self.data, list) and len(self.data) == 0:
            return "No results found"

        # Caso: lista de resultados
        if isinstance(self.data, list):
            if len(self.data) == 1:
                result_str = str(self.data[0])
            else:
                result_str = f"Found {len(self.data)} results:\n"
                for i, item in enumerate(self.data[:10], 1):  # Limitar a 10
                    result_str += f"{i}. {item}\n"
                if len(self.data) > 10:
                    result_str += f"... and {len(self.data) - 10} more"
        else:
            result_str = str(self.data)

        # Truncar si es muy largo
        if len(result_str) > max_length:
            result_str = result_str[: max_length - 3] + "..."

        return result_str

    @classmethod
    def success_result(
        cls,
        data: Any,
        execution_time_ms: float = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ToolResult":
        """Factory method para resultado exitoso."""
        return cls(
            success=True,
            data=data,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        execution_time_ms: float = 0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ToolResult":
        """Factory method para resultado de error."""
        return cls(
            success=False,
            error=error,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )


class BaseTool(ABC):
    """
    Clase abstracta base para herramientas del ReAct Agent.

    Todas las herramientas deben heredar de esta clase e implementar:
    - definition: Property que retorna ToolDefinition
    - execute: Método async para ejecutar la herramienta
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Retorna la definición de la herramienta.

        Returns:
            ToolDefinition con metadata para prompts
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Ejecuta la herramienta con los parámetros dados.

        Args:
            **kwargs: Parámetros de la herramienta

        Returns:
            ToolResult con el resultado de la ejecución
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida los parámetros de entrada.

        Args:
            params: Diccionario de parámetros

        Returns:
            Tupla (es_válido, mensaje_error)
        """
        definition = self.definition

        for param_def in definition.parameters:
            if param_def.required and param_def.name not in params:
                if param_def.default is not None:
                    params[param_def.name] = param_def.default
                else:
                    return False, f"Missing required parameter: {param_def.name}"

        return True, None

    @property
    def name(self) -> str:
        """Nombre de la herramienta."""
        return self.definition.name

    @property
    def category(self) -> ToolCategory:
        """Categoría de la herramienta."""
        return self.definition.category

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, category={self.category.value})>"
