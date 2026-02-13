"""
Extractor de memoria que analiza interacciones y genera resúmenes con LLM.

Este módulo utiliza el LLM para analizar las interacciones recientes del usuario
y generar resúmenes narrativos sobre su contexto laboral, temas recientes e historial.
"""
import logging
import json
from typing import Optional, List
from datetime import datetime
from src.agent.providers.base_provider import LLMProvider
from .memory_repository import UserMemoryProfile, UserInteraction

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """
    Extractor de resúmenes de memoria usando LLM.

    Analiza interacciones del usuario y genera párrafos resumen sobre:
    - Contexto laboral (rol, proyectos, herramientas)
    - Temas recientes (top of mind)
    - Historial breve (patrones de uso, problemas resueltos)
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Inicializar el extractor.

        Args:
            llm_provider: Proveedor de LLM para generación de resúmenes
        """
        self.llm_provider = llm_provider

    async def generate_memory_summary(
        self,
        recent_interactions: List[UserInteraction],
        existing_profile: Optional[UserMemoryProfile] = None
    ) -> UserMemoryProfile:
        """
        Generar resúmenes de memoria analizando interacciones recientes.

        Proceso:
        1. Formatear interacciones en texto legible
        2. Construir prompt con perfil existente (si hay)
        3. Enviar al LLM para análisis
        4. Parsear respuesta JSON
        5. Crear/actualizar perfil con nuevos resúmenes

        Args:
            recent_interactions: Lista de interacciones recientes
            existing_profile: Perfil existente para merge (opcional)

        Returns:
            UserMemoryProfile con resúmenes actualizados

        Raises:
            ValueError: Si no hay interacciones para analizar
            Exception: Si hay error en generación o parsing
        """
        if not recent_interactions:
            raise ValueError("No hay interacciones para analizar")

        logger.info(
            f"Generando resúmenes de memoria para usuario "
            f"(interacciones: {len(recent_interactions)})"
        )

        try:
            # 1. Formatear interacciones
            interactions_text = self._format_interactions(recent_interactions)

            # 2. Construir prompt
            prompt = self._build_extraction_prompt(
                interactions_text,
                existing_profile
            )

            # 3. Generar con LLM
            response = await self.llm_provider.generate(
                prompt,
                max_tokens=800  # Suficiente para 3 párrafos
            )

            # 4. Parsear respuesta JSON
            summary_data = self._parse_llm_response(response)

            # 5. Crear perfil actualizado
            user_id = existing_profile.id_usuario if existing_profile else recent_interactions[0].id_log

            if existing_profile:
                # Actualizar perfil existente
                updated_profile = UserMemoryProfile(
                    id_usuario=existing_profile.id_usuario,
                    resumen_contexto_laboral=summary_data.get('contexto_laboral'),
                    resumen_temas_recientes=summary_data.get('temas_recientes'),
                    resumen_historial_breve=summary_data.get('historial_breve'),
                    num_interacciones=0,  # Se resetea después de generar resúmenes
                    ultima_actualizacion=datetime.now(),
                    fecha_creacion=existing_profile.fecha_creacion,
                    version=existing_profile.version
                )
            else:
                # Crear nuevo perfil
                updated_profile = UserMemoryProfile(
                    id_usuario=user_id,
                    resumen_contexto_laboral=summary_data.get('contexto_laboral'),
                    resumen_temas_recientes=summary_data.get('temas_recientes'),
                    resumen_historial_breve=summary_data.get('historial_breve'),
                    num_interacciones=0,
                    ultima_actualizacion=datetime.now(),
                    fecha_creacion=datetime.now(),
                    version=1
                )

            logger.info(f"✅ Resúmenes generados exitosamente para usuario {user_id}")
            return updated_profile

        except Exception as e:
            logger.error(f"Error generando resúmenes de memoria: {e}", exc_info=True)
            raise

    def _format_interactions(self, interactions: List[UserInteraction]) -> str:
        """
        Formatear interacciones en texto legible para el LLM.

        Args:
            interactions: Lista de interacciones

        Returns:
            Texto formateado con interacciones
        """
        formatted = []
        for i, interaction in enumerate(interactions, 1):
            formatted.append(
                f"---\n"
                f"Interacción {i}:\n"
                f"Fecha: {interaction.fecha_hora.strftime('%Y-%m-%d %H:%M')}\n"
                f"Consulta: {interaction.user_query}\n"
            )

        return "\n".join(formatted)

    def _build_extraction_prompt(
        self,
        interactions_text: str,
        existing_profile: Optional[UserMemoryProfile]
    ) -> str:
        """
        Construir prompt para extracción de memoria.

        Args:
            interactions_text: Texto formateado de interacciones
            existing_profile: Perfil existente (opcional)

        Returns:
            Prompt completo para el LLM
        """
        # Construir sección de perfil actual si existe
        existing_context = ""
        if existing_profile and existing_profile.has_content():
            existing_context = f"""
PERFIL ACTUAL (mantén información relevante):
Contexto Laboral: {existing_profile.resumen_contexto_laboral or 'No definido'}
Temas Recientes: {existing_profile.resumen_temas_recientes or 'No definido'}
Historial: {existing_profile.resumen_historial_breve or 'No definido'}
"""

        prompt = f"""Eres un asistente que analiza conversaciones para crear perfiles de usuario.

Analiza las siguientes interacciones del usuario:

{interactions_text}

{existing_context}

TAREA: Genera 3 párrafos resumen actualizados:

1. CONTEXTO LABORAL (2-3 oraciones máximo):
   - Rol o puesto del usuario (si es mencionado)
   - Departamento o gerencia (si es mencionado)
   - Proyectos actuales mencionados
   - Herramientas o tecnologías que usa

   Ejemplo: "Juan es Analista de Datos en Gerencia de Tecnología. Trabaja en el Dashboard de Ventas Q4 y migración de BD. Usa SQL Server, Python y Power BI."

2. TEMAS RECIENTES - Top of Mind (2-3 oraciones máximo):
   - Temas consultados frecuentemente
   - Problemas específicos que está enfrentando
   - Menciona frecuencia si es evidente (ej: "3 veces", "frecuentemente")

   Ejemplo: "En los últimos días ha consultado frecuentemente sobre reportes de ventas Q4 (5 veces) y optimización de queries SQL (3 veces)."

3. HISTORIAL BREVE (1-2 oraciones máximo):
   - Tipos de consultas que suele hacer
   - Patrones de uso observados

   Ejemplo: "Suele realizar consultas sobre métricas de ventas y análisis de datos. Ha trabajado en optimización de reportes."

REGLAS IMPORTANTES:
- Solo información EXPLÍCITA en las conversaciones (NO inventes)
- Si no hay información para una sección, escribe "Sin información suficiente"
- Escribe en tercera persona, estilo profesional
- Sé conciso: máximo 3 oraciones por sección
- Si hay perfil actual, ACTUALIZA con nueva información, no reemplaces todo
- Si un tema del perfil actual NO aparece en las nuevas interacciones, elimínalo de temas recientes

Responde SOLO en formato JSON sin markdown:
{{
  "contexto_laboral": "párrafo aquí o Sin información suficiente",
  "temas_recientes": "párrafo aquí o Sin información suficiente",
  "historial_breve": "párrafo aquí o Sin información suficiente"
}}"""

        return prompt

    def _parse_llm_response(self, response: str) -> dict:
        """
        Parsear respuesta JSON del LLM.

        Args:
            response: Respuesta del LLM (puede incluir markdown)

        Returns:
            Diccionario con los resúmenes

        Raises:
            ValueError: Si no se puede parsear el JSON
        """
        try:
            # Limpiar respuesta (remover markdown si existe)
            cleaned_response = response.strip()

            # Remover ```json y ``` si existen
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]

            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            # Parsear JSON
            data = json.loads(cleaned_response)

            # Validar que tiene las claves necesarias
            required_keys = ["contexto_laboral", "temas_recientes", "historial_breve"]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Falta clave requerida: {key}")

            # Convertir "Sin información suficiente" a None
            for key in required_keys:
                if isinstance(data[key], str) and "sin información" in data[key].lower():
                    data[key] = None

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON del LLM: {e}")
            logger.error(f"Respuesta recibida: {response}")
            raise ValueError(f"No se pudo parsear la respuesta del LLM como JSON: {e}")

        except Exception as e:
            logger.error(f"Error procesando respuesta del LLM: {e}")
            raise
