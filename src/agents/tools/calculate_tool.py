"""
Calculate Tool - Herramienta para cálculos matemáticos seguros.

Evalúa expresiones matemáticas de forma segura usando AST,
sin usar eval() directo.
"""

import ast
import logging
import math
import operator
import time
from typing import Any, Union

from .base import BaseTool, ToolCategory, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class SafeMathEvaluator:
    """
    Evaluador seguro de expresiones matemáticas.

    Usa AST para parsear y evaluar expresiones sin ejecutar
    código arbitrario.
    """

    # Operadores permitidos
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Funciones matemáticas permitidas
    FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "sqrt": math.sqrt,
        "ceil": math.ceil,
        "floor": math.floor,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pow": math.pow,
    }

    # Constantes permitidas
    CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expression: str) -> Union[int, float]:
        """
        Evalúa una expresión matemática de forma segura.

        Args:
            expression: Expresión matemática a evaluar

        Returns:
            Resultado numérico

        Raises:
            ValueError: Si la expresión no es válida
        """
        try:
            # Parsear la expresión
            tree = ast.parse(expression, mode="eval")
            return self._eval_node(tree.body)
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")
        except Exception as e:
            raise ValueError(f"Evaluation error: {e}")

    def _eval_node(self, node: ast.AST) -> Union[int, float, list]:
        """
        Evalúa un nodo AST recursivamente.

        Args:
            node: Nodo AST a evaluar

        Returns:
            Resultado de la evaluación
        """
        # Números (ast.Constant es el estándar desde Python 3.8)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        # Nombres (constantes)
        if isinstance(node, ast.Name):
            name = node.id.lower()
            if name in self.CONSTANTS:
                return self.CONSTANTS[name]
            raise ValueError(f"Unknown variable: {node.id}")

        # Operaciones unarias (-x, +x)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                operand = self._eval_node(node.operand)
                return self.OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")

        # Operaciones binarias (x + y, x * y, etc.)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return self.OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")

        # Llamadas a funciones
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                func_name = node.func.id.lower()
                if func_name in self.FUNCTIONS:
                    args = [self._eval_node(arg) for arg in node.args]
                    return self.FUNCTIONS[func_name](*args)
                raise ValueError(f"Unknown function: {func_name}")
            raise ValueError("Invalid function call")

        # Listas (para min, max, sum)
        if isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        # Tuplas
        if isinstance(node, ast.Tuple):
            return [self._eval_node(elem) for elem in node.elts]

        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculateTool(BaseTool):
    """
    Herramienta para realizar cálculos matemáticos.

    Evalúa expresiones matemáticas de forma segura.

    Example:
        >>> tool = CalculateTool()
        >>> result = await tool.execute(expression="(100 * 0.15) + 50")
        >>> print(result.data)  # 65.0
    """

    def __init__(self):
        """Inicializa el CalculateTool."""
        self.evaluator = SafeMathEvaluator()
        logger.info("CalculateTool inicializado")

    @property
    def definition(self) -> ToolDefinition:
        """Definición de la herramienta para el prompt."""
        return ToolDefinition(
            name="calculate",
            description=(
                "Perform mathematical calculations. Supports basic arithmetic "
                "(+, -, *, /, **, %), functions (sqrt, sin, cos, log, round, abs, "
                "min, max, sum), and constants (pi, e)."
            ),
            category=ToolCategory.CALCULATION,
            parameters=[
                ToolParameter(
                    name="expression",
                    param_type="string",
                    description="Mathematical expression to evaluate",
                    required=True,
                    examples=[
                        "100 * 0.15",
                        "sqrt(16) + 5",
                        "round(15.7, 0)",
                        "max(10, 20, 15)",
                    ],
                ),
            ],
            examples=[
                {"expression": "(1500 * 0.21) + 100"},
                {"expression": "sqrt(144) / 3"},
                {"expression": "round(123.456, 2)"},
            ],
            returns="Numerical result of the calculation",
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Evalúa una expresión matemática.

        Args:
            expression: Expresión matemática

        Returns:
            ToolResult con el resultado o error
        """
        start_time = time.perf_counter()
        expression = kwargs.get("expression", "")

        # Validar parámetros
        is_valid, error = self.validate_params(kwargs)
        if not is_valid:
            return ToolResult.error_result(error or "Invalid parameters")

        try:
            # Limpiar expresión
            expression = expression.strip()

            # Evaluar
            logger.info(f"Evaluating expression: {expression}")
            result = self.evaluator.evaluate(expression)

            # Redondear si es float con muchos decimales
            if isinstance(result, float):
                # Mantener precisión razonable
                result = round(result, 10)
                # Convertir a int si es número entero
                if result == int(result):
                    result = int(result)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Calculation result: {result} in {elapsed_ms:.2f}ms")

            return ToolResult.success_result(
                data=result,
                execution_time_ms=elapsed_ms,
                metadata={"expression": expression},
            )

        except ValueError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Calculation error: {e}")
            return ToolResult.error_result(
                error=str(e),
                execution_time_ms=elapsed_ms,
                metadata={"expression": expression},
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Unexpected calculation error: {e}")
            return ToolResult.error_result(
                error=f"Calculation error: {str(e)}",
                execution_time_ms=elapsed_ms,
            )
