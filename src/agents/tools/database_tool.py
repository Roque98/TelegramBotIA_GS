"""
Database Tool - Herramienta para ejecutar consultas SQL.

Ejecuta consultas SQL SELECT validadas contra la base de datos.
Usa SQLValidator existente para validación de seguridad.
"""

import logging
import time
from typing import Any, Optional

from .base import BaseTool, ToolCategory, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class DatabaseTool(BaseTool):
    """
    Herramienta para ejecutar consultas SQL en la base de datos.

    Solo permite consultas SELECT validadas por seguridad.
    Integra con el DatabaseManager y SQLValidator existentes.

    Example:
        >>> tool = DatabaseTool(db_manager)
        >>> result = await tool.execute(query="SELECT COUNT(*) FROM ventas")
        >>> print(result.to_observation())
    """

    def __init__(
        self,
        db_manager: Any,
        sql_validator: Optional[Any] = None,
        max_results: int = 100,
    ):
        """
        Inicializa el DatabaseTool.

        Args:
            db_manager: Gestor de base de datos
            sql_validator: Validador SQL (opcional, crea uno por defecto)
            max_results: Número máximo de resultados a retornar
        """
        self.db_manager = db_manager
        self.max_results = max_results

        # Usar validador proporcionado o crear uno nuevo
        if sql_validator:
            self.sql_validator = sql_validator
        else:
            from src.agent.sql.sql_validator import SQLValidator
            self.sql_validator = SQLValidator()

        logger.info(f"DatabaseTool inicializado (max_results={max_results})")

    @property
    def definition(self) -> ToolDefinition:
        """Definición de la herramienta para el prompt."""
        return ToolDefinition(
            name="database_query",
            description=(
                "Execute a SQL SELECT query to retrieve data from the database. "
                "Use this for questions about sales, users, products, or any business data."
            ),
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(
                    name="query",
                    param_type="string",
                    description="SQL SELECT query to execute",
                    required=True,
                    examples=[
                        "SELECT COUNT(*) as total FROM ventas WHERE fecha = GETDATE()",
                        "SELECT TOP 5 nombre, total FROM vendedores ORDER BY total DESC",
                    ],
                ),
            ],
            examples=[
                {"query": "SELECT COUNT(*) as total FROM ventas WHERE fecha >= DATEADD(day, -7, GETDATE())"},
                {"query": "SELECT TOP 10 producto, SUM(cantidad) as total FROM ventas GROUP BY producto ORDER BY total DESC"},
            ],
            returns="Query results as a list of records or error message",
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Ejecuta una consulta SQL.

        Args:
            query: Consulta SQL SELECT

        Returns:
            ToolResult con los datos o error
        """
        start_time = time.perf_counter()
        query = kwargs.get("query", "")

        # Validar parámetros
        is_valid, error = self.validate_params(kwargs)
        if not is_valid:
            return ToolResult.error_result(error or "Invalid parameters")

        try:
            # Validar SQL por seguridad
            is_safe, validation_error = self.sql_validator.validate(query)
            if not is_safe:
                logger.warning(f"SQL validation failed: {validation_error}")
                return ToolResult.error_result(
                    f"SQL validation failed: {validation_error}",
                    metadata={"query": query[:100]},
                )

            # Ejecutar query
            logger.info(f"Executing SQL: {query[:100]}...")
            results = await self._execute_query(query)

            # Limitar resultados
            if isinstance(results, list) and len(results) > self.max_results:
                results = results[: self.max_results]
                logger.info(f"Results truncated to {self.max_results}")

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Query executed in {elapsed_ms:.2f}ms, {len(results) if isinstance(results, list) else 1} results")

            return ToolResult.success_result(
                data=results,
                execution_time_ms=elapsed_ms,
                metadata={"query": query[:100], "result_count": len(results) if isinstance(results, list) else 1},
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Database query error: {e}")
            return ToolResult.error_result(
                error=f"Database error: {str(e)}",
                execution_time_ms=elapsed_ms,
                metadata={"query": query[:100]},
            )

    async def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        Ejecuta la query contra la base de datos.

        Args:
            query: Consulta SQL validada

        Returns:
            Lista de resultados como diccionarios
        """
        # El db_manager puede ser sync o async
        if hasattr(self.db_manager, "execute_query_async"):
            results = await self.db_manager.execute_query_async(query)
        elif hasattr(self.db_manager, "execute_query"):
            # Wrapper sync
            import asyncio
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self.db_manager.execute_query, query
            )
        else:
            raise ValueError("DatabaseManager does not have execute_query method")

        # Convertir a lista de dicts si es necesario
        if results is None:
            return []

        if isinstance(results, list):
            # Si ya es lista de dicts, retornar
            if results and isinstance(results[0], dict):
                return results
            # Si es lista de tuples/rows, convertir
            return [dict(row) if hasattr(row, "_asdict") else row for row in results]

        return [results]
