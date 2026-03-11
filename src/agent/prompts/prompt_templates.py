"""
Plantillas de prompts con soporte para Jinja2.

Todas las plantillas están versionadas para facilitar A/B testing y mejora iterativa.
"""
from jinja2 import Template
from typing import Dict, Any


class PromptTemplates:
    """Repositorio centralizado de plantillas de prompts."""

    # ==========================================
    # CLASIFICACIÓN DE CONSULTAS
    # ==========================================

    CLASSIFICATION_V1 = Template("""Eres un clasificador de consultas. Determina si la siguiente pregunta requiere acceso a una base de datos o puede responderse con conocimiento general.

Pregunta: "{{ user_query }}"

Responde SOLO con una de estas dos palabras:
- "database" si la pregunta requiere consultar datos específicos de una base de datos (ej: conteo de usuarios, productos, ventas, registros específicos, etc.)
- "general" si es una pregunta general que no requiere datos específicos de una BD (ej: saludos, explicaciones, conceptos, conversación, etc.)

Respuesta:""")

    CLASSIFICATION_V2 = Template("""Eres un clasificador experto de consultas. Analiza la siguiente pregunta y determina si requiere datos de una base de datos.

Pregunta del usuario: "{{ user_query }}"

Contexto adicional:
- Si la pregunta solicita datos numéricos, registros específicos, listados, conteos, estadísticas → requiere BASE DE DATOS
- Si la pregunta es sobre conceptos, saludos, explicaciones generales, conversación → es GENERAL

Responde con UNA palabra:
- "database" → requiere consultar base de datos
- "general" → pregunta general sin datos específicos

Tu respuesta:""")

    CLASSIFICATION_V3 = Template("""Eres un clasificador inteligente de consultas. Determina el tipo de consulta del usuario.

Pregunta del usuario: "{{ user_query }}"

{% if knowledge_available %}
CONOCIMIENTO INSTITUCIONAL ENCONTRADO:
{{ knowledge_context }}

Si la pregunta puede responderse completamente con el conocimiento institucional mostrado arriba, clasifica como "knowledge".
{% endif %}

REGLAS DE CLASIFICACIÓN:
1. "knowledge" → La pregunta puede responderse con el conocimiento institucional proporcionado (políticas, procesos, FAQs, contactos)
2. "database" → La pregunta requiere consultar datos específicos de la base de datos (conteos, registros, estadísticas en tiempo real)
3. "general" → Pregunta general que no requiere conocimiento institucional ni base de datos (saludos, conversación, conceptos generales)

EJEMPLOS:
- "¿Cómo solicito vacaciones?" → knowledge (proceso institucional)
- "¿Cuántos usuarios hay registrados?" → database (requiere consulta en BD)
- "Hola, ¿cómo estás?" → general (conversación)
- "¿Cuál es el horario de trabajo?" → knowledge (política de empresa)
- "¿Olvidé mi contraseña?" → knowledge (FAQ común)

Responde con UNA SOLA palabra: "knowledge", "database" o "general"

Tu respuesta:""")

    # ==========================================
    # GENERACIÓN DE SQL
    # ==========================================

    SQL_GENERATION_V1 = Template("""Dado el siguiente esquema de base de datos:

{{ database_schema }}

Genera una consulta SQL segura para la siguiente pregunta del usuario:
"{{ user_query }}"

REGLAS IMPORTANTES:
1. Responde SOLO con la consulta SQL, sin explicaciones adicionales
2. Usa ÚNICAMENTE consultas SELECT (no INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
3. Asegúrate de que la consulta sea válida para el esquema proporcionado
4. Si necesitas limitar resultados, usa TOP o LIMIT según corresponda
5. Usa nombres de columnas exactos como aparecen en el esquema
6. Si la pregunta no se puede responder con los datos disponibles, genera SELECT NULL AS mensaje, 'No hay datos suficientes para responder' AS detalle

Consulta SQL:""")

    SQL_GENERATION_V2 = Template("""Eres un experto en SQL Server. Dado el siguiente esquema de base de datos:

{{ database_schema }}

Genera una consulta SQL óptima y segura para responder:
"{{ user_query }}"

INSTRUCCIONES CRÍTICAS:
1. Genera SOLO código SQL, sin markdown ni explicaciones
2. ÚNICAMENTE consultas SELECT (prohibido: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC)
3. Usa nombres exactos de tablas y columnas del esquema
4. Para limitar resultados usa TOP N en SQL Server
5. Incluye JOINs si es necesario basándote en las relaciones del esquema
6. Si la consulta es ambigua, prioriza la interpretación más común
7. Si no hay datos suficientes, responde: SELECT 'No disponible' AS mensaje

SQL:""")

    # Versión optimizada para consultas complejas
    SQL_GENERATION_V3 = Template("""Sistema: Eres un generador experto de consultas SQL para SQL Server.

Esquema de la base de datos:
{{ database_schema }}

{% if user_context %}
Contexto del usuario que realiza la consulta (usa estos valores literales cuando sea necesario):
{% if user_context.telegram_chat_id %}- telegramChatId del usuario actual: {{ user_context.telegram_chat_id }}{% endif %}
{% if user_context.telegram_username %}- username de Telegram: {{ user_context.telegram_username }}{% endif %}
{% if user_context.id_usuario %}- idUsuario en el sistema: {{ user_context.id_usuario }}{% endif %}
{% endif %}

Pregunta del usuario: "{{ user_query }}"

Genera una consulta SQL que:
✓ Sea SOLO SELECT (no modificaciones de datos)
✓ Use nombres exactos de tablas/columnas del esquema
✓ Incluya JOINs apropiados si relaciona múltiples tablas
✓ Use agregaciones (COUNT, SUM, AVG, etc.) si la pregunta lo requiere
✓ Use TOP {{ max_results|default(100) }} para limitar resultados
✓ Sea eficiente y optimizada
✓ Maneje valores NULL apropiadamente
✓ NUNCA uses variables T-SQL no declaradas (@variable). Si necesitas filtrar por el usuario actual, usa el valor literal del contexto proporcionado arriba.

Formato de salida: SQL puro sin markdown, comentarios ni explicaciones.

SQL:""")

    # ==========================================
    # RESPUESTAS GENERALES
    # ==========================================

    GENERAL_RESPONSE_V1 = Template("""Eres un asistente amigable. Responde a la siguiente pregunta o comentario del usuario de manera natural y útil.

Pregunta: "{{ user_query }}"

Respuesta:""")

    GENERAL_RESPONSE_V2 = Template("""Eres un asistente inteligente y amable especializado en ayudar a usuarios de sistemas empresariales.

Usuario: "{{ user_query }}"

Responde de manera:
- Clara y concisa (máximo 3 párrafos)
- Profesional pero amigable
- Útil y orientada a la acción
- USA EMOJIS relevantes para hacer la respuesta más visual y fácil de entender
- Usa saltos de línea para separar ideas importantes
- Usa viñetas (•) cuando listes elementos
{% if context %}

Contexto adicional: {{ context }}
{% endif %}

IMPORTANTE: Tu respuesta debe ser visualmente atractiva con emojis apropiados al contexto.

Tu respuesta:""")

    # ==========================================
    # FORMATEO DE RESPUESTAS CON DATOS
    # ==========================================

    RESULT_SUMMARY_V1 = Template("""Basado en los siguientes resultados de una consulta SQL, genera un resumen en lenguaje natural para el usuario.

Consulta original: "{{ user_query }}"
SQL ejecutado: {{ sql_query }}
Número de resultados: {{ num_results }}

Resultados (primeras {{ sample_size }} filas):
{{ results_sample }}

Genera un resumen conciso y comprensible de los resultados:""")

    RESULT_SUMMARY_V2 = Template("""Eres un analista de datos amigable y visual. Resume los siguientes resultados para un usuario no técnico.

Pregunta del usuario: "{{ user_query }}"
Resultados encontrados: {{ num_results }}

{% if num_results > 0 %}
Muestra de datos:
{{ results_sample }}

Genera un resumen que:
- Responda directamente la pregunta del usuario con EMOJIS relevantes
- Use lenguaje natural sin jerga técnica
- Destaque insights o patrones importantes con emojis
- Sea breve pero visualmente atractivo (máximo 2-3 párrafos)
- Usa saltos de línea dobles entre párrafos
- Usa emojis para números, cantidades o datos importantes (📊 💰 📈 🔢 ✅ etc.)
- Si hay listas, usa viñetas con emojis (• ✓ → etc.)

IMPORTANTE: La respuesta debe ser fácil de leer con buena separación visual y emojis apropiados.
{% else %}
No se encontraron resultados 😕. Sugiere al usuario reformular su pregunta de manera amigable.
{% endif %}

Resumen:""")

    # ==========================================
    # VALIDACIÓN Y REFINAMIENTO
    # ==========================================

    SQL_VALIDATION_V1 = Template("""Analiza si la siguiente consulta SQL es segura y válida:

SQL: {{ sql_query }}

Verifica:
1. ¿Es SOLO una consulta SELECT? (no debe modificar datos)
2. ¿Tiene sintaxis válida?
3. ¿No contiene comandos peligrosos? (DROP, DELETE, UPDATE, ALTER, EXEC, etc.)
4. ¿Es razonablemente eficiente?

Responde con JSON:
{
  "is_valid": true/false,
  "reason": "explicación breve",
  "risk_level": "none/low/medium/high"
}""")

    # ==========================================
    # SELECCIÓN AUTOMÁTICA DE TOOLS
    # ==========================================

    TOOL_SELECTION_V1 = Template("""Eres un selector inteligente de herramientas (tools). Analiza la consulta del usuario y selecciona la herramienta más apropiada para responderla.

Consulta del usuario: "{{ user_query }}"

Herramientas disponibles:
{{ tools_description }}

Analiza la consulta y selecciona el tool más apropiado. Responde SOLO con un objeto JSON en este formato exacto:
{
  "tool": "nombre_del_tool",
  "confidence": 0.9,
  "reasoning": "breve explicación de por qué seleccionaste este tool"
}

Criterios para la selección:
- Si la consulta solicita datos específicos, estadísticas o información de base de datos → usa "query"
- Si la consulta solicita ayuda, lista de comandos o información sobre funcionalidades → usa "help" si existe
- Si la consulta solicita estadísticas del sistema → usa "stats" si existe
- Prioriza tools especializados sobre genéricos
- El campo "confidence" debe estar entre 0.0 y 1.0

Tu respuesta (JSON únicamente):""")

    # ==========================================
    # MÉTODOS DE AYUDA
    # ==========================================

    @classmethod
    def render(cls, template: Template, **kwargs) -> str:
        """
        Renderizar una plantilla con las variables proporcionadas.

        Args:
            template: Plantilla Jinja2 a renderizar
            **kwargs: Variables para la plantilla

        Returns:
            Prompt renderizado

        Example:
            >>> prompt = PromptTemplates.render(
            ...     PromptTemplates.CLASSIFICATION_V1,
            ...     user_query="¿Cuántos usuarios hay?"
            ... )
        """
        return template.render(**kwargs)

    @classmethod
    def get_template(cls, name: str, version: int = 1) -> Template:
        """
        Obtener una plantilla por nombre y versión.

        Args:
            name: Nombre de la plantilla (ej: 'classification', 'sql_generation')
            version: Versión de la plantilla (default: 1)

        Returns:
            Plantilla Jinja2

        Raises:
            AttributeError: Si la plantilla no existe

        Example:
            >>> template = PromptTemplates.get_template('classification', version=2)
        """
        template_name = f"{name.upper()}_V{version}"
        return getattr(cls, template_name)

    @classmethod
    def list_available_templates(cls) -> Dict[str, list]:
        """
        Listar todas las plantillas disponibles agrupadas por tipo.

        Returns:
            Diccionario con tipos de plantillas y sus versiones disponibles

        Example:
            >>> templates = PromptTemplates.list_available_templates()
            >>> print(templates)
            {
                'CLASSIFICATION': [1, 2],
                'SQL_GENERATION': [1, 2, 3],
                'GENERAL_RESPONSE': [1, 2],
                ...
            }
        """
        templates = {}
        for attr_name in dir(cls):
            if attr_name.isupper() and not attr_name.startswith('_'):
                # Extraer nombre base y versión
                parts = attr_name.rsplit('_V', 1)
                if len(parts) == 2:
                    base_name = parts[0]
                    try:
                        version = int(parts[1])
                        if base_name not in templates:
                            templates[base_name] = []
                        templates[base_name].append(version)
                    except ValueError:
                        continue

        # Ordenar versiones
        for key in templates:
            templates[key].sort()

        return templates

    @classmethod
    def get_latest_version(cls, template_type: str) -> int:
        """
        Obtener la última versión disponible de un tipo de plantilla.

        Args:
            template_type: Tipo de plantilla (ej: 'CLASSIFICATION', 'SQL_GENERATION')

        Returns:
            Número de la última versión

        Example:
            >>> version = PromptTemplates.get_latest_version('SQL_GENERATION')
            >>> print(version)  # 3
        """
        templates = cls.list_available_templates()
        if template_type in templates:
            return max(templates[template_type])
        return 1
