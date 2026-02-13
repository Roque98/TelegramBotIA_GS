"""
DateTime Tool - Herramienta para operaciones con fechas y horas.

Proporciona información sobre fechas, diferencias, y cálculos temporales.
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from .base import BaseTool, ToolCategory, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class DateTimeTool(BaseTool):
    """
    Herramienta para operaciones con fechas y horas.

    Proporciona la fecha/hora actual, diferencias entre fechas,
    y cálculos temporales comunes.

    Example:
        >>> tool = DateTimeTool()
        >>> result = await tool.execute(operation="now")
        >>> print(result.data)
    """

    def __init__(self, timezone: str = "UTC"):
        """
        Inicializa el DateTimeTool.

        Args:
            timezone: Zona horaria por defecto (actualmente solo UTC)
        """
        self.timezone = timezone
        logger.info(f"DateTimeTool inicializado (timezone={timezone})")

    @property
    def definition(self) -> ToolDefinition:
        """Definición de la herramienta para el prompt."""
        return ToolDefinition(
            name="datetime",
            description=(
                "Get current date/time or perform date calculations. "
                "Use for questions about dates, time differences, or "
                "when you need the current date for SQL queries."
            ),
            category=ToolCategory.DATETIME,
            parameters=[
                ToolParameter(
                    name="operation",
                    param_type="string",
                    description=(
                        "Operation to perform: 'now' (current datetime), "
                        "'today' (current date), 'add_days' (add/subtract days), "
                        "'diff_days' (days between dates), 'format' (format a date)"
                    ),
                    required=True,
                    examples=["now", "today", "add_days", "diff_days"],
                ),
                ToolParameter(
                    name="date",
                    param_type="string",
                    description="Date in YYYY-MM-DD format (for add_days, diff_days, format)",
                    required=False,
                ),
                ToolParameter(
                    name="date2",
                    param_type="string",
                    description="Second date for diff_days operation",
                    required=False,
                ),
                ToolParameter(
                    name="days",
                    param_type="integer",
                    description="Number of days to add (negative to subtract)",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="format",
                    param_type="string",
                    description="Output format (for format operation)",
                    required=False,
                    default="%Y-%m-%d",
                ),
            ],
            examples=[
                {"operation": "now"},
                {"operation": "today"},
                {"operation": "add_days", "date": "2024-01-15", "days": -7},
                {"operation": "diff_days", "date": "2024-01-01", "date2": "2024-01-15"},
            ],
            returns="Date/time information or calculation result",
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Ejecuta una operación de fecha/hora.

        Args:
            operation: Tipo de operación
            date: Fecha base (opcional)
            date2: Segunda fecha (opcional)
            days: Días a agregar (opcional)
            format: Formato de salida (opcional)

        Returns:
            ToolResult con el resultado
        """
        start_time = time.perf_counter()
        operation = kwargs.get("operation", "now")

        try:
            result = None

            if operation == "now":
                result = self._get_now()
            elif operation == "today":
                result = self._get_today()
            elif operation == "add_days":
                result = self._add_days(kwargs)
            elif operation == "diff_days":
                result = self._diff_days(kwargs)
            elif operation == "format":
                result = self._format_date(kwargs)
            else:
                return ToolResult.error_result(
                    f"Unknown operation: {operation}. Use: now, today, add_days, diff_days, format"
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"DateTime operation '{operation}' completed in {elapsed_ms:.2f}ms")

            return ToolResult.success_result(
                data=result,
                execution_time_ms=elapsed_ms,
                metadata={"operation": operation},
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"DateTime error: {e}")
            return ToolResult.error_result(
                error=f"DateTime error: {str(e)}",
                execution_time_ms=elapsed_ms,
            )

    def _get_now(self) -> dict[str, Any]:
        """Obtiene fecha y hora actual."""
        now = datetime.now(UTC)
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.strftime("%A"),
            "timestamp": int(now.timestamp()),
        }

    def _get_today(self) -> dict[str, Any]:
        """Obtiene la fecha actual."""
        today = datetime.now(UTC).date()
        return {
            "date": today.isoformat(),
            "year": today.year,
            "month": today.month,
            "day": today.day,
            "weekday": today.strftime("%A"),
            # Formatos útiles para SQL
            "sql_date": today.strftime("%Y-%m-%d"),
            "display": today.strftime("%d/%m/%Y"),
        }

    def _add_days(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Agrega o resta días a una fecha.

        Args:
            kwargs: Debe contener 'date' y 'days'

        Returns:
            Diccionario con la fecha resultante
        """
        date_str = kwargs.get("date")
        days = kwargs.get("days", 0)

        if date_str:
            base_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            base_date = datetime.now(UTC).date()

        result_date = base_date + timedelta(days=int(days))

        return {
            "original_date": base_date.isoformat(),
            "days_added": int(days),
            "result_date": result_date.isoformat(),
            "sql_date": result_date.strftime("%Y-%m-%d"),
            "display": result_date.strftime("%d/%m/%Y"),
        }

    def _diff_days(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Calcula la diferencia en días entre dos fechas.

        Args:
            kwargs: Debe contener 'date' y 'date2'

        Returns:
            Diccionario con la diferencia
        """
        date1_str = kwargs.get("date")
        date2_str = kwargs.get("date2")

        if not date1_str or not date2_str:
            raise ValueError("Both 'date' and 'date2' are required for diff_days")

        date1 = datetime.strptime(date1_str, "%Y-%m-%d").date()
        date2 = datetime.strptime(date2_str, "%Y-%m-%d").date()

        diff = (date2 - date1).days

        return {
            "date1": date1.isoformat(),
            "date2": date2.isoformat(),
            "difference_days": diff,
            "difference_weeks": round(diff / 7, 1),
            "difference_months": round(diff / 30, 1),
        }

    def _format_date(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Formatea una fecha en diferentes formatos.

        Args:
            kwargs: Debe contener 'date' y opcionalmente 'format'

        Returns:
            Diccionario con la fecha en varios formatos
        """
        date_str = kwargs.get("date")
        format_str = kwargs.get("format", "%Y-%m-%d")

        if not date_str:
            raise ValueError("'date' is required for format operation")

        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        return {
            "input": date_str,
            "iso": date.isoformat(),
            "sql": date.strftime("%Y-%m-%d"),
            "display": date.strftime("%d/%m/%Y"),
            "long": date.strftime("%B %d, %Y"),
            "custom": date.strftime(format_str),
        }
