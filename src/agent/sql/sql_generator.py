"""
Generador de consultas SQL a partir de lenguaje natural.

Usa un LLM para traducir consultas en lenguaje natural a SQL.
"""
import logging
from typing import Optional, Dict, Any
from ..providers.base_provider import LLMProvider
from ..prompts import get_default_manager

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generador de SQL usando LLM."""

    def __init__(self, llm_provider: LLMProvider, prompt_version: Optional[int] = None):
        """
        Inicializar el generador de SQL.

        Args:
            llm_provider: Proveedor de LLM para generación
            prompt_version: Versión del prompt a usar (None = auto según A/B testing)
        """
        self.llm_provider = llm_provider
        self.prompt_manager = get_default_manager()
        self.prompt_version = prompt_version
        logger.info(f"Inicializado generador SQL con proveedor: {llm_provider.get_provider_name()}")

    async def generate_sql(
        self,
        user_query: str,
        database_schema: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generar consulta SQL a partir de lenguaje natural.

        Args:
            user_query: Consulta del usuario en lenguaje natural
            database_schema: Esquema de la base de datos
            user_context: Contexto del usuario (telegram_chat_id, id_usuario, etc.)

        Returns:
            Consulta SQL generada, o None si no se pudo generar
        """
        # Usar el nuevo sistema de prompts
        prompt = self.prompt_manager.get_prompt(
            'sql_generation',
            version=self.prompt_version,
            user_query=user_query,
            database_schema=database_schema,
            user_context=user_context
        )

        try:
            sql_query = await self.llm_provider.generate(prompt, max_tokens=1024)
            sql_query = sql_query.strip()

            # Limpiar la respuesta (remover markdown si existe)
            sql_query = self._clean_sql_response(sql_query)

            logger.info(f"SQL generado para '{user_query[:50]}...': {sql_query[:100]}...")
            return sql_query

        except Exception as e:
            logger.error(f"Error generando SQL: {e}")
            return None

    def _clean_sql_response(self, sql_response: str) -> str:
        """
        Limpiar la respuesta SQL removiendo markdown u otros formatos.

        Args:
            sql_response: Respuesta del LLM

        Returns:
            SQL limpio
        """
        # Remover bloques de código markdown
        if "```sql" in sql_response:
            sql_response = sql_response.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql_response:
            sql_response = sql_response.split("```")[1].split("```")[0].strip()

        # Remover líneas de comentarios al inicio/final
        lines = sql_response.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            # Ignorar líneas de comentarios vacías o de markdown
            if not stripped or stripped.startswith("--") or stripped.startswith("#"):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()
