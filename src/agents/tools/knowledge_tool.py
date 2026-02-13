"""
Knowledge Tool - Herramienta para buscar en la base de conocimiento.

Busca información en la base de conocimiento institucional usando
el KnowledgeManager existente.
"""

import logging
import time
from typing import Any, Optional

from .base import BaseTool, ToolCategory, ToolDefinition, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class KnowledgeTool(BaseTool):
    """
    Herramienta para buscar en la base de conocimiento institucional.

    Usa el KnowledgeManager existente para búsqueda por keywords.

    Example:
        >>> tool = KnowledgeTool(knowledge_manager)
        >>> result = await tool.execute(query="políticas de vacaciones")
        >>> print(result.to_observation())
    """

    def __init__(
        self,
        knowledge_manager: Any,
        top_k: int = 3,
        min_score: float = 0.1,
    ):
        """
        Inicializa el KnowledgeTool.

        Args:
            knowledge_manager: Gestor de conocimiento
            top_k: Número máximo de resultados
            min_score: Score mínimo de relevancia
        """
        self.knowledge_manager = knowledge_manager
        self.top_k = top_k
        self.min_score = min_score

        logger.info(f"KnowledgeTool inicializado (top_k={top_k}, min_score={min_score})")

    @property
    def definition(self) -> ToolDefinition:
        """Definición de la herramienta para el prompt."""
        return ToolDefinition(
            name="knowledge_search",
            description=(
                "Search the company knowledge base for policies, procedures, FAQs, "
                "and institutional information. Use this for questions about company "
                "rules, processes, HR policies, or general company information."
            ),
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="query",
                    param_type="string",
                    description="Search query in natural language",
                    required=True,
                    examples=[
                        "políticas de vacaciones",
                        "proceso de reembolso de gastos",
                        "horario de trabajo",
                    ],
                ),
                ToolParameter(
                    name="category",
                    param_type="string",
                    description="Optional category filter (sistemas, procesos, politicas, faqs, contactos, recursos_humanos)",
                    required=False,
                    default=None,
                ),
            ],
            examples=[
                {"query": "¿cómo solicito vacaciones?"},
                {"query": "política de trabajo remoto", "category": "politicas"},
            ],
            returns="Relevant knowledge entries with questions and answers",
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Busca en la base de conocimiento.

        Args:
            query: Consulta de búsqueda
            category: Categoría opcional para filtrar

        Returns:
            ToolResult con las entradas relevantes o error
        """
        start_time = time.perf_counter()
        query = kwargs.get("query", "")
        category_str = kwargs.get("category")

        # Validar parámetros
        is_valid, error = self.validate_params(kwargs)
        if not is_valid:
            return ToolResult.error_result(error or "Invalid parameters")

        try:
            # Convertir categoría si se proporciona
            category_filter = None
            if category_str:
                category_filter = self._get_category(category_str)

            # Buscar en knowledge base
            logger.info(f"Searching knowledge base: '{query[:50]}...'")
            results = self.knowledge_manager.search(
                query=query,
                top_k=self.top_k,
                min_score=self.min_score,
                category_filter=category_filter,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if not results:
                logger.info(f"No results found for: {query[:50]}")
                return ToolResult.success_result(
                    data=[],
                    execution_time_ms=elapsed_ms,
                    metadata={"query": query, "result_count": 0},
                )

            # Formatear resultados
            formatted_results = self._format_results(results)
            logger.info(f"Found {len(results)} results in {elapsed_ms:.2f}ms")

            return ToolResult.success_result(
                data=formatted_results,
                execution_time_ms=elapsed_ms,
                metadata={"query": query, "result_count": len(results)},
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Knowledge search error: {e}")
            return ToolResult.error_result(
                error=f"Search error: {str(e)}",
                execution_time_ms=elapsed_ms,
            )

    def _format_results(self, results: list) -> list[dict[str, Any]]:
        """
        Formatea los resultados para el agente.

        Args:
            results: Lista de KnowledgeEntry

        Returns:
            Lista de diccionarios con la información relevante
        """
        formatted = []

        for entry in results:
            formatted.append({
                "question": entry.question,
                "answer": entry.answer,
                "category": entry.category.value if hasattr(entry.category, "value") else str(entry.category),
                "keywords": entry.keywords if hasattr(entry, "keywords") else [],
            })

        return formatted

    def _get_category(self, category_str: str) -> Optional[Any]:
        """
        Convierte string de categoría a enum.

        Args:
            category_str: Nombre de la categoría

        Returns:
            KnowledgeCategory o None
        """
        try:
            from src.agent.knowledge.knowledge_categories import KnowledgeCategory

            category_map = {
                "sistemas": KnowledgeCategory.SISTEMAS,
                "procesos": KnowledgeCategory.PROCESOS,
                "politicas": KnowledgeCategory.POLITICAS,
                "faqs": KnowledgeCategory.FAQS,
                "contactos": KnowledgeCategory.CONTACTOS,
                "recursos_humanos": KnowledgeCategory.RECURSOS_HUMANOS,
                "base_datos": KnowledgeCategory.BASE_DATOS,
            }
            return category_map.get(category_str.lower())
        except ImportError:
            logger.warning("Could not import KnowledgeCategory")
            return None
