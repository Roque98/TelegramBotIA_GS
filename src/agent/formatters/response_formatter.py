"""
Formateador de respuestas para el usuario.

Formatea los resultados de consultas SQL en texto legible para el usuario.
Usa LLM para generar respuestas en lenguaje natural.
"""
import logging
from typing import List, Dict, Any, Optional
from ..providers.base_provider import LLMProvider
from ..prompts import get_default_manager

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formateador de respuestas."""

    def __init__(
        self,
        max_results_display: int = 10,
        llm_provider: Optional[LLMProvider] = None,
        use_natural_language: bool = True
    ):
        """
        Inicializar el formateador.

        Args:
            max_results_display: Número máximo de resultados a mostrar
            llm_provider: Proveedor LLM para generar respuestas en lenguaje natural (opcional)
            use_natural_language: Si usar LLM para formatear en lenguaje natural (default: True)
        """
        self.max_results_display = max_results_display
        self.llm_provider = llm_provider
        self.use_natural_language = use_natural_language and llm_provider is not None
        self.prompt_manager = get_default_manager() if self.use_natural_language else None

        logger.info(
            f"Inicializado formateador de respuestas "
            f"(max display: {max_results_display}, natural language: {self.use_natural_language})"
        )

    async def format_query_results(
        self,
        user_query: str,
        sql_query: str,
        results: List[Dict[str, Any]],
        include_sql: bool = False,
        user_name: Optional[str] = None
    ) -> str:
        """
        Formatear resultados de una consulta SQL.

        Si use_natural_language está habilitado, usa LLM para generar
        una respuesta en lenguaje natural. Si no, usa formato estructurado.

        Args:
            user_query: Consulta original del usuario
            sql_query: Consulta SQL ejecutada
            results: Resultados de la consulta
            include_sql: Si se debe incluir el SQL en la respuesta
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta formateada
        """
        if not results:
            return self._format_empty_results(user_query)

        # Si está habilitado lenguaje natural, usar LLM
        if self.use_natural_language:
            try:
                natural_response = await self._format_with_llm(
                    user_query, sql_query, results, user_name
                )
                if natural_response:
                    # Opcional: agregar SQL si se solicita
                    if include_sql:
                        return f"{natural_response}\n\n**SQL ejecutado:**\n```sql\n{sql_query}\n```"
                    return natural_response
            except Exception as e:
                logger.warning(f"Error formateando con LLM, usando formato estructurado: {e}")
                # Fallback a formato estructurado si el LLM falla

        # Formato estructurado (fallback o cuando no hay LLM)
        response_parts = []

        # Opcional: Incluir SQL ejecutado
        if include_sql:
            response_parts.append(f"**SQL ejecutado:**\n```sql\n{sql_query}\n```\n")

        # Información de resultados
        total_count = len(results)
        response_parts.append(f"**Resultados encontrados:** {total_count}\n")

        # Formatear resultados
        if total_count == 1:
            # Un solo resultado - formato detallado
            response_parts.append(self._format_single_result(results[0]))
        else:
            # Múltiples resultados - formato de lista
            response_parts.append(self._format_multiple_results(results))

        # Indicar si hay más resultados
        if total_count > self.max_results_display:
            hidden_count = total_count - self.max_results_display
            response_parts.append(f"\n... y {hidden_count} resultado(s) más.")

        return "\n".join(response_parts)

    def format_general_response(self, response_text: str) -> str:
        """
        Formatear una respuesta general (no de BD).

        Args:
            response_text: Texto de respuesta del LLM

        Returns:
            Respuesta formateada
        """
        return response_text

    def format_error(self, error_message: str, user_friendly: bool = True) -> str:
        """
        Formatear un mensaje de error con la personalidad de Iris.

        Args:
            error_message: Mensaje de error técnico
            user_friendly: Si se debe mostrar mensaje amigable

        Returns:
            Mensaje de error formateado
        """
        if user_friendly:
            return (
                "❌ Oh no, tuve un problema procesando eso.\n\n"
                "¿Podrías intentar reformular tu pregunta de otra manera?\n\n"
                "_Iris está aquí para ayudarte_ ✨"
            )
        else:
            return f"**Error:** {error_message}"

    def _format_empty_results(self, user_query: str) -> str:
        """
        Formatear respuesta cuando no hay resultados (con personalidad de Iris).

        Args:
            user_query: Consulta del usuario

        Returns:
            Mensaje formateado
        """
        return (
            "🔍 No encontré resultados para esa consulta.\n\n"
            "💡 **Sugerencias:**\n"
            "• Intenta reformular la pregunta\n"
            "• Verifica los nombres de tablas o campos\n"
            "• Prueba con términos diferentes\n\n"
            "_Iris está aquí si necesitas ayuda_ ✨"
        )

    def _format_single_result(self, result: Dict[str, Any]) -> str:
        """
        Formatear un solo resultado en formato detallado.

        Args:
            result: Diccionario con el resultado

        Returns:
            Resultado formateado
        """
        lines = []

        for key, value in result.items():
            # Formatear valores None
            if value is None:
                value = "(vacío)"

            lines.append(f"**{key}:** {value}")

        return "\n".join(lines)

    def _format_multiple_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Formatear múltiples resultados en formato de lista.

        Args:
            results: Lista de diccionarios con resultados

        Returns:
            Resultados formateados
        """
        lines = []

        # Limitar cantidad de resultados mostrados
        display_results = results[:self.max_results_display]

        for i, row in enumerate(display_results, 1):
            # Formatear cada fila
            row_text = self._format_row_inline(row)
            lines.append(f"{i}. {row_text}")

        return "\n".join(lines)

    def _format_row_inline(self, row: Dict[str, Any]) -> str:
        """
        Formatear una fila en formato inline (una línea).

        Args:
            row: Diccionario con los datos de la fila

        Returns:
            Fila formateada
        """
        parts = []

        for key, value in row.items():
            if value is None:
                value = "(vacío)"

            parts.append(f"{key}: {value}")

        return " | ".join(parts)

    def _format_row_table(self, row: Dict[str, Any]) -> str:
        """
        Formatear una fila en formato de tabla.

        Args:
            row: Diccionario con los datos de la fila

        Returns:
            Fila formateada
        """
        # TODO: Implementar formato de tabla con Unicode box drawing
        # Para una futura mejora con mejores tablas visuales
        return self._format_row_inline(row)

    async def _format_with_llm(
        self,
        user_query: str,
        sql_query: str,
        results: List[Dict[str, Any]],
        user_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Formatear resultados usando LLM para generar respuesta en lenguaje natural.

        Args:
            user_query: Consulta original del usuario
            sql_query: Consulta SQL ejecutada
            results: Resultados de la consulta
            user_name: Nombre del usuario para personalización (opcional)

        Returns:
            Respuesta en lenguaje natural, o None si falla
        """
        if not self.llm_provider or not self.prompt_manager:
            return None

        try:
            # Preparar muestra de resultados
            sample_size = min(self.max_results_display, len(results))
            results_sample = self._format_results_for_llm(results[:sample_size])

            # Generar prompt usando el sistema de prompts
            prompt = self.prompt_manager.get_prompt(
                'result_summary',
                version=2,  # Usar V2 que es más completo
                user_query=user_query,
                sql_query=sql_query,
                num_results=len(results),
                results_sample=results_sample,
                sample_size=sample_size,
                user_name=user_name or ""
            )

            # Generar respuesta con el LLM
            response = await self.llm_provider.generate(prompt, max_tokens=500)

            logger.info(f"Respuesta formateada con LLM para query: '{user_query[:50]}...'")
            return response.strip()

        except Exception as e:
            logger.error(f"Error formateando con LLM: {e}", exc_info=True)
            return None

    def _format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """
        Formatear resultados para incluir en el prompt del LLM.

        Args:
            results: Lista de resultados

        Returns:
            Resultados formateados como string
        """
        if not results:
            return "No hay resultados"

        lines = []
        for i, row in enumerate(results, 1):
            row_parts = []
            for key, value in row.items():
                if value is None:
                    value = "NULL"
                row_parts.append(f"{key}: {value}")
            lines.append(f"{i}. {', '.join(row_parts)}")

        return "\n".join(lines)
