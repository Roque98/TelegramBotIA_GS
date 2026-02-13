"""
Tests para el sistema de Tools del ReAct Agent.

Cobertura:
- ToolParameter: Validación y formato
- ToolDefinition: Generación de prompts y schemas
- ToolResult: Observaciones y factory methods
- ToolRegistry: Registro y búsqueda de tools
- CalculateTool: Evaluación matemática segura
- DateTimeTool: Operaciones con fechas
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.agents.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from src.agents.tools.registry import ToolRegistry, get_tool_registry
from src.agents.tools.calculate_tool import CalculateTool, SafeMathEvaluator
from src.agents.tools.datetime_tool import DateTimeTool


class TestToolParameter:
    """Tests para ToolParameter."""

    def test_basic_parameter_creation(self):
        """Crear parámetro básico con valores por defecto."""
        param = ToolParameter(
            name="query",
            description="Search query",
        )

        assert param.name == "query"
        assert param.param_type == "string"
        assert param.required is True
        assert param.default is None

    def test_optional_parameter(self):
        """Crear parámetro opcional con valor por defecto."""
        param = ToolParameter(
            name="limit",
            param_type="integer",
            description="Max results",
            required=False,
            default=10,
        )

        assert param.required is False
        assert param.default == 10

    def test_to_prompt_format_required(self):
        """to_prompt_format debe incluir (required) para parámetros requeridos."""
        param = ToolParameter(
            name="query",
            param_type="string",
            description="Search query",
            required=True,
        )

        prompt = param.to_prompt_format()

        assert "query" in prompt
        assert "string" in prompt
        assert "(required)" in prompt

    def test_to_prompt_format_optional(self):
        """to_prompt_format debe incluir (optional) para parámetros opcionales."""
        param = ToolParameter(
            name="limit",
            param_type="integer",
            description="Max results",
            required=False,
        )

        prompt = param.to_prompt_format()

        assert "(optional)" in prompt


class TestToolDefinition:
    """Tests para ToolDefinition."""

    def test_basic_definition(self):
        """Crear definición básica."""
        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
        )

        assert definition.name == "test_tool"
        assert definition.category == ToolCategory.UTILITY
        assert definition.parameters == []

    def test_definition_with_parameters(self):
        """Crear definición con parámetros."""
        definition = ToolDefinition(
            name="search",
            description="Search tool",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(name="query", description="Query text"),
                ToolParameter(name="limit", param_type="integer", description="Max", required=False),
            ],
        )

        assert len(definition.parameters) == 2

    def test_to_prompt_format_includes_name(self):
        """to_prompt_format debe incluir nombre y descripción."""
        definition = ToolDefinition(
            name="database_query",
            description="Execute SQL queries",
            category=ToolCategory.DATABASE,
        )

        prompt = definition.to_prompt_format()

        assert "database_query" in prompt
        assert "Execute SQL queries" in prompt

    def test_to_prompt_format_with_parameters(self):
        """to_prompt_format debe incluir parámetros."""
        definition = ToolDefinition(
            name="calculate",
            description="Math calculations",
            category=ToolCategory.CALCULATION,
            parameters=[
                ToolParameter(name="expression", description="Math expression"),
            ],
        )

        prompt = definition.to_prompt_format()

        assert "Parameters:" in prompt
        assert "expression" in prompt

    def test_to_prompt_format_with_examples(self):
        """to_prompt_format debe incluir ejemplos."""
        definition = ToolDefinition(
            name="calculate",
            description="Math calculations",
            category=ToolCategory.CALCULATION,
            examples=[{"expression": "2 + 2"}],
        )

        prompt = definition.to_prompt_format()

        assert "Example:" in prompt
        assert "2 + 2" in prompt

    def test_get_json_schema(self):
        """get_json_schema debe generar schema válido."""
        definition = ToolDefinition(
            name="test",
            description="Test",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(name="query", description="Query", required=True),
                ToolParameter(name="limit", param_type="integer", description="Limit", required=False),
            ],
        )

        schema = definition.get_json_schema()

        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "query" in schema["required"]
        assert "limit" not in schema["required"]


class TestToolResult:
    """Tests para ToolResult."""

    def test_success_result_factory(self):
        """success_result debe crear resultado exitoso."""
        result = ToolResult.success_result(data={"count": 10})

        assert result.success is True
        assert result.data == {"count": 10}
        assert result.error is None

    def test_error_result_factory(self):
        """error_result debe crear resultado de error."""
        result = ToolResult.error_result(error="Something went wrong")

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_to_observation_success(self):
        """to_observation debe formatear resultado exitoso."""
        result = ToolResult.success_result(data={"total": 150})

        observation = result.to_observation()

        assert "150" in observation

    def test_to_observation_error(self):
        """to_observation debe formatear error."""
        result = ToolResult.error_result(error="Database timeout")

        observation = result.to_observation()

        assert "Error:" in observation
        assert "Database timeout" in observation

    def test_to_observation_empty_list(self):
        """to_observation debe manejar lista vacía."""
        result = ToolResult.success_result(data=[])

        observation = result.to_observation()

        assert "No results found" in observation

    def test_to_observation_none(self):
        """to_observation debe manejar None."""
        result = ToolResult.success_result(data=None)

        observation = result.to_observation()

        assert "No results found" in observation

    def test_to_observation_list(self):
        """to_observation debe formatear listas."""
        result = ToolResult.success_result(data=[
            {"name": "Alice", "sales": 100},
            {"name": "Bob", "sales": 80},
        ])

        observation = result.to_observation()

        assert "Found 2 results" in observation

    def test_to_observation_truncates_long_results(self):
        """to_observation debe truncar resultados muy largos."""
        long_data = "x" * 3000
        result = ToolResult.success_result(data=long_data)

        observation = result.to_observation(max_length=100)

        assert len(observation) <= 100
        assert observation.endswith("...")


class TestToolRegistry:
    """Tests para ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Crea un registry limpio para cada test."""
        ToolRegistry.reset()
        return ToolRegistry()

    def test_singleton_pattern(self, registry):
        """ToolRegistry debe ser singleton."""
        registry2 = ToolRegistry()
        assert registry is registry2

    def test_register_tool(self, registry):
        """Registrar un tool."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "test_tool"
        tool.category = ToolCategory.UTILITY

        registry.register(tool)

        assert registry.has_tool("test_tool")
        assert registry.get("test_tool") is tool

    def test_register_duplicate_raises_error(self, registry):
        """Registrar tool duplicado debe lanzar error."""
        tool1 = MagicMock(spec=BaseTool)
        tool1.name = "test_tool"
        tool1.category = ToolCategory.UTILITY

        tool2 = MagicMock(spec=BaseTool)
        tool2.name = "test_tool"
        tool2.category = ToolCategory.UTILITY

        registry.register(tool1)

        with pytest.raises(ValueError, match="ya está registrado"):
            registry.register(tool2)

    def test_unregister_tool(self, registry):
        """Desregistrar un tool."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "test_tool"
        tool.category = ToolCategory.UTILITY

        registry.register(tool)
        result = registry.unregister("test_tool")

        assert result is True
        assert not registry.has_tool("test_tool")

    def test_unregister_nonexistent_returns_false(self, registry):
        """Desregistrar tool inexistente retorna False."""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_all_tools(self, registry):
        """Obtener todos los tools."""
        tool1 = MagicMock(spec=BaseTool)
        tool1.name = "tool1"
        tool1.category = ToolCategory.UTILITY

        tool2 = MagicMock(spec=BaseTool)
        tool2.name = "tool2"
        tool2.category = ToolCategory.DATABASE

        registry.register(tool1)
        registry.register(tool2)

        all_tools = registry.get_all()

        assert len(all_tools) == 2

    def test_get_by_category(self, registry):
        """Filtrar tools por categoría."""
        tool1 = MagicMock(spec=BaseTool)
        tool1.name = "db_tool"
        tool1.category = ToolCategory.DATABASE

        tool2 = MagicMock(spec=BaseTool)
        tool2.name = "calc_tool"
        tool2.category = ToolCategory.CALCULATION

        registry.register(tool1)
        registry.register(tool2)

        db_tools = registry.get_by_category(ToolCategory.DATABASE)

        assert len(db_tools) == 1
        assert db_tools[0].name == "db_tool"

    def test_get_tools_prompt(self, registry):
        """get_tools_prompt debe generar descripción de tools."""
        # Crear mock con definition
        definition = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.UTILITY,
        )
        tool = MagicMock(spec=BaseTool)
        tool.name = "test_tool"
        tool.category = ToolCategory.UTILITY
        tool.definition = definition

        registry.register(tool)

        prompt = registry.get_tools_prompt()

        assert "Available Tools" in prompt
        assert "test_tool" in prompt

    def test_get_tool_names(self, registry):
        """Obtener nombres de tools."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "my_tool"
        tool.category = ToolCategory.UTILITY

        registry.register(tool)

        names = registry.get_tool_names()

        assert "my_tool" in names

    def test_len_and_contains(self, registry):
        """__len__ y __contains__ deben funcionar."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "my_tool"
        tool.category = ToolCategory.UTILITY

        registry.register(tool)

        assert len(registry) == 1
        assert "my_tool" in registry


class TestSafeMathEvaluator:
    """Tests para SafeMathEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return SafeMathEvaluator()

    def test_basic_addition(self, evaluator):
        """Suma básica."""
        assert evaluator.evaluate("2 + 3") == 5

    def test_basic_subtraction(self, evaluator):
        """Resta básica."""
        assert evaluator.evaluate("10 - 4") == 6

    def test_multiplication(self, evaluator):
        """Multiplicación."""
        assert evaluator.evaluate("5 * 6") == 30

    def test_division(self, evaluator):
        """División."""
        assert evaluator.evaluate("15 / 3") == 5.0

    def test_power(self, evaluator):
        """Potencia."""
        assert evaluator.evaluate("2 ** 8") == 256

    def test_modulo(self, evaluator):
        """Módulo."""
        assert evaluator.evaluate("17 % 5") == 2

    def test_negative_numbers(self, evaluator):
        """Números negativos."""
        assert evaluator.evaluate("-5 + 3") == -2

    def test_parentheses(self, evaluator):
        """Paréntesis."""
        assert evaluator.evaluate("(2 + 3) * 4") == 20

    def test_sqrt_function(self, evaluator):
        """Función sqrt."""
        assert evaluator.evaluate("sqrt(16)") == 4.0

    def test_round_function(self, evaluator):
        """Función round."""
        assert evaluator.evaluate("round(3.7)") == 4

    def test_min_max_functions(self, evaluator):
        """Funciones min y max."""
        assert evaluator.evaluate("min(5, 3, 8)") == 3
        assert evaluator.evaluate("max(5, 3, 8)") == 8

    def test_pi_constant(self, evaluator):
        """Constante pi."""
        import math
        assert evaluator.evaluate("pi") == math.pi

    def test_complex_expression(self, evaluator):
        """Expresión compleja."""
        result = evaluator.evaluate("sqrt(16) + 2 * 3")
        assert result == 10.0

    def test_invalid_syntax_raises_error(self, evaluator):
        """Sintaxis inválida debe lanzar error."""
        with pytest.raises(ValueError):
            evaluator.evaluate("2 +")

    def test_unknown_function_raises_error(self, evaluator):
        """Función desconocida debe lanzar error."""
        with pytest.raises(ValueError, match="Unknown function"):
            evaluator.evaluate("unknown_func(5)")

    def test_unknown_variable_raises_error(self, evaluator):
        """Variable desconocida debe lanzar error."""
        with pytest.raises(ValueError, match="Unknown variable"):
            evaluator.evaluate("x + 5")


class TestCalculateTool:
    """Tests para CalculateTool."""

    @pytest.fixture
    def tool(self):
        return CalculateTool()

    def test_definition_properties(self, tool):
        """La definición debe tener las propiedades correctas."""
        definition = tool.definition

        assert definition.name == "calculate"
        assert definition.category == ToolCategory.CALCULATION
        assert len(definition.parameters) == 1

    @pytest.mark.asyncio
    async def test_execute_basic_calculation(self, tool):
        """Ejecutar cálculo básico."""
        result = await tool.execute(expression="100 * 0.15")

        assert result.success is True
        assert result.data == 15.0

    @pytest.mark.asyncio
    async def test_execute_returns_int_for_whole_numbers(self, tool):
        """Retornar int para números enteros."""
        result = await tool.execute(expression="10 + 5")

        assert result.success is True
        assert result.data == 15
        assert isinstance(result.data, int)

    @pytest.mark.asyncio
    async def test_execute_with_functions(self, tool):
        """Ejecutar cálculo con funciones."""
        result = await tool.execute(expression="sqrt(144)")

        assert result.success is True
        assert result.data == 12

    @pytest.mark.asyncio
    async def test_execute_invalid_expression(self, tool):
        """Expresión inválida retorna error."""
        result = await tool.execute(expression="2 + * 3")

        assert result.success is False
        assert result.error is not None


class TestDateTimeTool:
    """Tests para DateTimeTool."""

    @pytest.fixture
    def tool(self):
        return DateTimeTool()

    def test_definition_properties(self, tool):
        """La definición debe tener las propiedades correctas."""
        definition = tool.definition

        assert definition.name == "datetime"
        assert definition.category == ToolCategory.DATETIME

    @pytest.mark.asyncio
    async def test_operation_now(self, tool):
        """Operación 'now' retorna fecha/hora actual."""
        result = await tool.execute(operation="now")

        assert result.success is True
        assert "datetime" in result.data
        assert "date" in result.data
        assert "time" in result.data
        assert "year" in result.data

    @pytest.mark.asyncio
    async def test_operation_today(self, tool):
        """Operación 'today' retorna fecha actual."""
        result = await tool.execute(operation="today")

        assert result.success is True
        assert "date" in result.data
        assert "sql_date" in result.data
        assert "display" in result.data

    @pytest.mark.asyncio
    async def test_operation_add_days(self, tool):
        """Operación 'add_days' suma días correctamente."""
        result = await tool.execute(
            operation="add_days",
            date="2024-01-15",
            days=10,
        )

        assert result.success is True
        assert result.data["result_date"] == "2024-01-25"

    @pytest.mark.asyncio
    async def test_operation_add_negative_days(self, tool):
        """Operación 'add_days' con días negativos resta correctamente."""
        result = await tool.execute(
            operation="add_days",
            date="2024-01-15",
            days=-5,
        )

        assert result.success is True
        assert result.data["result_date"] == "2024-01-10"

    @pytest.mark.asyncio
    async def test_operation_diff_days(self, tool):
        """Operación 'diff_days' calcula diferencia correctamente."""
        result = await tool.execute(
            operation="diff_days",
            date="2024-01-01",
            date2="2024-01-15",
        )

        assert result.success is True
        assert result.data["difference_days"] == 14

    @pytest.mark.asyncio
    async def test_operation_format(self, tool):
        """Operación 'format' formatea fecha correctamente."""
        result = await tool.execute(
            operation="format",
            date="2024-01-15",
        )

        assert result.success is True
        assert result.data["iso"] == "2024-01-15"
        assert result.data["display"] == "15/01/2024"

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self, tool):
        """Operación desconocida retorna error."""
        result = await tool.execute(operation="unknown")

        assert result.success is False
        assert "Unknown operation" in result.error

    @pytest.mark.asyncio
    async def test_diff_days_missing_date2_returns_error(self, tool):
        """diff_days sin date2 retorna error."""
        result = await tool.execute(
            operation="diff_days",
            date="2024-01-01",
        )

        assert result.success is False
