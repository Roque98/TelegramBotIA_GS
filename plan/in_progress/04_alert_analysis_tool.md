# TODO: AlertAnalysisTool — Tool registrado en el pipeline

## Objetivo
Implementar el tool que orquesta el flujo completo: recibe la intención del usuario,
obtiene datos de alertas e historial, construye el prompt y retorna el análisis del LLM.
Se integra en el sistema de tools existente (FASE 3) sin modificar el resto.

---

## Archivo a crear: `src/tools/builtin/alert_analysis_tool.py`

### Estructura

```python
class AlertAnalysisTool(BaseTool):

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="alert_analysis",
            description=(
                "Analiza alertas activas de monitoreo PRTG. "
                "Usa cuando el usuario pregunta por alertas, eventos Down, "
                "sensores alertados, diagnóstico de incidentes o estado de equipos."
            ),
            commands=["/alertas", "/analizar"],
            category="monitoring",
            requires_auth=True,
            required_permissions=[]
        )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="Pregunta o filtro del usuario (IP, equipo, sensor, etc.)",
                required=True,
                validation_rules={"min_length": 3, "max_length": 500}
            )
        ]

    async def execute(self, user_id: int, params: dict, context: ExecutionContext) -> ToolResult:
        query = params["query"]

        # 1. Extraer filtros de la query en lenguaje natural
        filtros = self._extraer_filtros(query)
        # filtros: {"ip": "10.80.191.22", "equipo": None, "solo_down": True}

        # 2. Obtener eventos del SP
        repo = AlertRepository()
        eventos = await repo.get_active_events(**filtros)

        if not eventos:
            return ToolResult(
                success=True,
                data="No se encontraron alertas activas con esos criterios."
            )

        # 3. Tomar el evento más relevante (o top 3 si no hay filtro específico)
        eventos_a_analizar = eventos[:1] if filtros.get("ip") or filtros.get("equipo") else eventos[:3]

        # 4. Para cada evento, obtener tickets históricos
        respuestas = []
        for evento in eventos_a_analizar:
            tickets = await repo.get_historical_tickets(evento["idConSensor"])
            prompt = AlertPromptBuilder().build(evento, tickets, query)
            analisis = await context.llm_agent.process_query(prompt, user_id)
            respuestas.append(analisis)

        return ToolResult(
            success=True,
            data="\n\n".join(respuestas)   # texto plano, un bloque por evento
        )

    def _extraer_filtros(self, query: str) -> dict:
        """
        Extrae IP, nombre de equipo u otros filtros del texto libre.
        Usa regex para IPs y heurística simple para nombres.
        """
        import re
        ip_match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", query)
        return {
            "ip": ip_match.group(1) if ip_match else None,
            "equipo": None,   # v1: solo IP; v2 puede agregar NER
            "solo_down": any(w in query.lower() for w in ["down", "caído", "alerta", "error"])
        }
```

---

## Registro del tool

En `src/tools/tool_registry.py`, agregar la importación y registro:

```python
from src.tools.builtin.alert_analysis_tool import AlertAnalysisTool

# En el método de registro de tools builtin:
registry.register(AlertAnalysisTool())
```

El `ToolSelector` (LLM-based) detectará automáticamente el nuevo tool
porque lee las descripciones del registro dinámicamente.

---

## Triggers de lenguaje natural esperados

El LLM seleccionará este tool cuando el usuario diga cosas como:
- "analiza las alertas actuales"
- "hay algo caído en producción?"
- "qué pasa con el sensor de 10.80.191.22"
- "dame un diagnóstico de los eventos Down"
- "muéstrame los equipos alertados"
- "WSTransferenciasSecure está fallando"

---

## Criterios de aceptación
- [ ] El tool aparece en `registry.list_tools()`
- [ ] `ToolSelector` lo elige para inputs relacionados con alertas
- [ ] Con IP en el mensaje → analiza ese evento específico
- [ ] Sin filtro → analiza top 3 eventos más críticos
- [ ] Sin eventos activos → respuesta clara al usuario
- [ ] El análisis del LLM incluye diagnóstico y acción correctiva

## Archivos a crear/modificar
- `src/tools/builtin/alert_analysis_tool.py` (crear)
- `src/tools/tool_registry.py` (agregar registro)
