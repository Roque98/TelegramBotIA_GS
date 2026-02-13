# Sistema de Prompts

## Ubicación

```
src/agent/prompts/
├── prompt_templates.py   # Templates versionados
└── prompt_manager.py     # Renderizado con Jinja2
```

---

## Templates Versionados

### CLASSIFICATION (V1, V2, V3)

**Propósito**: Clasificar intención del usuario

```python
# V1: Básico
CLASSIFICATION_V1 = """
Clasifica la siguiente consulta:
Query: {{ query }}

Responde: DATABASE, KNOWLEDGE o GENERAL
"""

# V2: Con contexto
CLASSIFICATION_V2 = """
Clasifica la consulta considerando el contexto disponible.

Contexto de conocimiento disponible: {{ knowledge_available }}
Query: {{ query }}

Responde: DATABASE, KNOWLEDGE o GENERAL
"""

# V3: Con memoria
CLASSIFICATION_V3 = """
Clasifica considerando historial del usuario.

Contexto de memoria: {{ memory_context }}
Conocimiento disponible: {{ knowledge_available }}
Query: {{ query }}

Responde: DATABASE, KNOWLEDGE o GENERAL
"""
```

---

### SQL_GENERATION (V1, V2)

**Propósito**: Generar SQL desde lenguaje natural

```python
SQL_GENERATION_V1 = """
Eres un experto en SQL Server.

## Schema de la base de datos
{{ schema }}

## Instrucciones
- Solo genera queries SELECT
- No uses INSERT, UPDATE, DELETE
- Usa nombres de tablas y columnas exactos del schema

## Query del usuario
{{ query }}

Genera SOLO el SQL, sin explicaciones.
"""

SQL_GENERATION_V2 = """
Eres un experto en SQL Server para {{ empresa }}.

## Schema
{{ schema }}

## Ejemplos de queries
{% for example in examples %}
- Usuario: {{ example.question }}
  SQL: {{ example.sql }}
{% endfor %}

## Restricciones de seguridad
- Solo SELECT, no modificaciones
- No usar funciones peligrosas
- Limitar resultados si no se especifica

## Query actual
{{ query }}

SQL:
"""
```

---

### RESULT_SUMMARY (V1, V2)

**Propósito**: Convertir resultados SQL a lenguaje natural

```python
RESULT_SUMMARY_V1 = """
Convierte estos resultados en una respuesta natural.

Query original: {{ query }}
Resultados: {{ results }}

Responde de forma concisa y amigable.
"""

RESULT_SUMMARY_V2 = """
Eres {{ bot_name }}, asistente de {{ empresa }}.

## Personalidad
{{ personality }}

## Query del usuario
{{ query }}

## Resultados de la base de datos
{{ results }}

## Instrucciones
- Responde de forma natural
- Si hay muchos datos, resume los más relevantes
- Usa formato que sea fácil de leer en Telegram
- {{ tone_instructions }}

Respuesta:
"""
```

---

### GENERAL_RESPONSE (V1, V2)

**Propósito**: Respuestas para queries generales

```python
GENERAL_RESPONSE_V1 = """
Eres {{ bot_name }}, asistente de {{ empresa }}.

{{ personality }}

Usuario pregunta: {{ query }}

Responde de forma {{ tone }}.
"""

GENERAL_RESPONSE_V2 = """
Eres {{ bot_name }}, asistente virtual de {{ empresa }}.

## Tu personalidad
{{ personality }}

## Contexto del usuario
- Nombre: {{ user_name }}
- Rol: {{ user_role }}
{% if memory_context %}
- Historial: {{ memory_context }}
{% endif %}

## Conversación reciente
{% for msg in conversation_history %}
- {{ msg.role }}: {{ msg.content }}
{% endfor %}

## Query actual
{{ query }}

## Instrucciones
- Responde de forma natural y {{ tone }}
- Si no sabes algo, sé honesto
- Sugiere usar /ia para consultas de datos

Respuesta:
"""
```

---

### KNOWLEDGE_RESPONSE

**Propósito**: Responder usando base de conocimiento

```python
KNOWLEDGE_RESPONSE = """
Eres {{ bot_name }}, asistente de {{ empresa }}.

## Información relevante encontrada
{% for entry in knowledge_entries %}
### {{ entry.title }}
{{ entry.content }}
{% endfor %}

## Query del usuario
{{ query }}

## Instrucciones
- Basa tu respuesta en la información proporcionada
- Si la información no es suficiente, indícalo
- Cita la fuente si es relevante

Respuesta:
"""
```

---

### MEMORY_EXTRACTION

**Propósito**: Generar resúmenes de memoria

```python
MEMORY_EXTRACTION = """
Analiza las siguientes interacciones y genera resúmenes.

## Interacciones recientes
{% for interaction in interactions %}
- [{{ interaction.date }}] Query: {{ interaction.query }}
  Respuesta: {{ interaction.response }}
{% endfor %}

## Resumen anterior
{{ previous_summary }}

## Genera tres resúmenes cortos:

1. **Contexto laboral**: ¿En qué área trabaja? ¿Qué tipo de datos consulta?
2. **Temas recientes**: ¿Qué ha preguntado últimamente?
3. **Historial breve**: Resumen general del usuario.

Responde en formato JSON:
{
  "contexto_laboral": "...",
  "temas_recientes": "...",
  "historial_breve": "..."
}
"""
```

---

## PromptManager

```python
# src/agent/prompts/prompt_manager.py

class PromptManager:
    def __init__(self):
        self.env = Environment(...)  # Jinja2

    def render(
        self,
        template_name: str,
        version: str = "V1",
        **kwargs
    ) -> str:
        """Renderiza template con variables."""
        template = getattr(PromptTemplates, f"{template_name}_{version}")
        return self.env.from_string(template).render(**kwargs)

    def get_available_versions(self, template_name: str) -> list[str]:
        """Lista versiones disponibles de un template."""
```

**Uso**:
```python
prompt_manager = PromptManager()

prompt = prompt_manager.render(
    "SQL_GENERATION",
    version="V2",
    schema=db_schema,
    query="¿Cuántas ventas hubo ayer?",
    empresa="Mi Empresa",
    examples=[...]
)
```

---

## Personalidad del Bot

**Archivo**: `src/config/personality.py`

```python
BOT_PERSONALITY = {
    "nombre": "Iris",
    "empresa": "Tu Empresa",
    "descripcion": "Asistente virtual inteligente",
    "tono": "profesional pero amigable",
    "caracteristicas": [
        "Responde de forma concisa",
        "Usa emojis con moderación",
        "Es honesto cuando no sabe algo"
    ],
    "idioma": "español"
}

def get_personality_prompt() -> str:
    """Genera prompt de personalidad."""
```

---

## Mejores Prácticas

### Versionado
```python
# Siempre crear nueva versión, no modificar existente
TEMPLATE_V1 = "..."  # Original
TEMPLATE_V2 = "..."  # Con mejoras
TEMPLATE_V3 = "..."  # Con más contexto
```

### Variables claras
```python
# ✅ Nombres descriptivos
{{ user_query }}
{{ knowledge_context }}
{{ memory_summary }}

# ❌ Nombres ambiguos
{{ q }}
{{ ctx }}
{{ data }}
```

### Instrucciones específicas
```python
# ✅ Específico
"Responde en máximo 3 oraciones"
"Usa formato de lista si hay más de 3 items"

# ❌ Vago
"Responde bien"
"Sé útil"
```

---

## Testing de Prompts

```python
# tests/unit/test_prompts.py

def test_sql_generation_prompt():
    prompt = prompt_manager.render(
        "SQL_GENERATION",
        version="V2",
        schema=mock_schema,
        query="ventas de hoy"
    )

    assert "SELECT" in prompt or "ventas" in prompt
    assert "{{ schema }}" not in prompt  # Variables renderizadas
```
