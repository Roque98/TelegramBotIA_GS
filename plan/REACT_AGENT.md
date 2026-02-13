# ReAct Agent: Reasoning + Acting

## Qué es ReAct

ReAct (Reasoning and Acting) es un paradigma donde el LLM:

1. **Thought**: Razona sobre qué hacer
2. **Action**: Ejecuta una herramienta
3. **Observation**: Observa el resultado
4. **Repeat**: Repite hasta tener la respuesta final

```
User: "¿Cuánto vendió el mejor vendedor del mes pasado y qué productos vendió más?"

Thought 1: Necesito primero encontrar quién fue el mejor vendedor del mes pasado.
           Voy a consultar la base de datos para obtener el top vendedor.

Action 1: database_query
          query: "SELECT vendedor_id, SUM(total) as ventas FROM ventas
                  WHERE fecha >= '2024-01-01' GROUP BY vendedor_id
                  ORDER BY ventas DESC LIMIT 1"

Observation 1: [{"vendedor_id": 42, "ventas": 150000}]

Thought 2: El mejor vendedor es el ID 42 con $150,000. Ahora necesito saber
           qué productos vendió más.

Action 2: database_query
          query: "SELECT p.nombre, COUNT(*) as cantidad FROM ventas v
                  JOIN productos p ON v.producto_id = p.id
                  WHERE v.vendedor_id = 42 AND v.fecha >= '2024-01-01'
                  GROUP BY p.nombre ORDER BY cantidad DESC LIMIT 5"

Observation 2: [{"nombre": "Laptop Pro", "cantidad": 45},
                {"nombre": "Monitor 4K", "cantidad": 32}, ...]

Thought 3: Tengo toda la información. El mejor vendedor (ID 42) vendió $150,000
           y sus productos más vendidos fueron Laptop Pro (45) y Monitor 4K (32).

Final Answer: El mejor vendedor del mes pasado generó $150,000 en ventas.
              Sus productos más vendidos fueron Laptop Pro (45 unidades)
              y Monitor 4K (32 unidades).
```

---

## Implementación de ReAct Agent

```python
# src/agents/react/agent.py
from pydantic import BaseModel
from typing import Literal, Optional, Any
from enum import Enum

class ActionType(str, Enum):
    DATABASE_QUERY = "database_query"
    KNOWLEDGE_SEARCH = "knowledge_search"
    CALCULATE = "calculate"
    FINISH = "finish"


class ReActStep(BaseModel):
    """Un paso del loop ReAct"""
    thought: str
    action: ActionType
    action_input: dict[str, Any]


class ReActResponse(BaseModel):
    """Respuesta del LLM en cada iteración"""
    thought: str
    action: ActionType
    action_input: Optional[dict[str, Any]] = None
    final_answer: Optional[str] = None


class ReActAgent:
    """
    Agente que implementa el paradigma ReAct.
    Razona paso a paso y ejecuta acciones hasta llegar a una respuesta.
    """

    MAX_ITERATIONS = 10  # Prevenir loops infinitos

    def __init__(self, llm_gateway, tools: dict):
        self.llm = llm_gateway
        self.tools = tools  # {"database_query": DatabaseTool, "knowledge_search": KnowledgeTool, ...}

    async def execute(
        self,
        query: str,
        context: dict = None
    ) -> str:
        """Ejecuta el loop ReAct hasta obtener respuesta final"""

        scratchpad = []  # Historial de thoughts/actions/observations
        iteration = 0

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            # 1. Generar siguiente paso (thought + action)
            response = await self._generate_step(query, scratchpad, context)

            # 2. Si es acción FINISH, retornar respuesta
            if response.action == ActionType.FINISH:
                return response.final_answer

            # 3. Ejecutar la acción
            observation = await self._execute_action(
                response.action,
                response.action_input
            )

            # 4. Agregar al scratchpad
            scratchpad.append({
                "thought": response.thought,
                "action": response.action.value,
                "action_input": response.action_input,
                "observation": observation
            })

        # Si llegamos aquí, excedimos iteraciones
        return self._synthesize_partial_answer(query, scratchpad)

    async def _generate_step(
        self,
        query: str,
        scratchpad: list,
        context: dict
    ) -> ReActResponse:
        """Genera el siguiente paso de razonamiento"""

        prompt = f"""
Eres un asistente que resuelve consultas paso a paso.

## Herramientas disponibles
- database_query: Ejecuta SQL contra la base de datos. Input: {{"query": "SELECT ..."}}
- knowledge_search: Busca en la base de conocimiento. Input: {{"search_term": "..."}}
- calculate: Realiza cálculos matemáticos. Input: {{"expression": "..."}}
- finish: Indica que tienes la respuesta final. Input: {{"answer": "..."}}

## Contexto
{self._format_context(context)}

## Consulta del usuario
"{query}"

## Trabajo previo (scratchpad)
{self._format_scratchpad(scratchpad)}

## Instrucciones
Genera el siguiente paso. Usa el formato:
- thought: Tu razonamiento sobre qué hacer a continuación
- action: La herramienta a usar (database_query, knowledge_search, calculate, o finish)
- action_input: Los parámetros para la herramienta

Si ya tienes suficiente información para responder, usa action="finish".
"""

        return await self.llm.generate_structured(
            prompt=prompt,
            schema=ReActResponse,
            temperature=0.2
        )

    async def _execute_action(
        self,
        action: ActionType,
        action_input: dict
    ) -> str:
        """Ejecuta una acción y retorna la observación"""

        tool = self.tools.get(action.value)
        if not tool:
            return f"Error: Herramienta '{action.value}' no disponible"

        try:
            result = await tool.execute(**action_input)
            return self._format_observation(result)
        except Exception as e:
            return f"Error ejecutando {action.value}: {str(e)}"

    def _format_scratchpad(self, scratchpad: list) -> str:
        if not scratchpad:
            return "Ninguno (esta es la primera iteración)"

        lines = []
        for i, step in enumerate(scratchpad, 1):
            lines.append(f"""
Paso {i}:
  Thought: {step['thought']}
  Action: {step['action']}
  Action Input: {step['action_input']}
  Observation: {step['observation']}
""")
        return "\n".join(lines)

    def _format_context(self, context: dict) -> str:
        if not context:
            return "Sin contexto adicional"
        return "\n".join([f"- {k}: {v}" for k, v in context.items()])

    def _format_observation(self, result) -> str:
        if isinstance(result, list):
            if len(result) > 10:
                return f"{result[:10]}... (y {len(result)-10} más)"
            return str(result)
        return str(result)

    def _synthesize_partial_answer(self, query: str, scratchpad: list) -> str:
        """Sintetiza respuesta parcial si se exceden iteraciones"""
        observations = [s["observation"] for s in scratchpad]
        return f"Basándome en la información recopilada: {observations[-1]}"
```

---

## Tools para ReAct

```python
# src/agents/react/tools.py
from abc import ABC, abstractmethod
from typing import Any

class ReActTool(ABC):
    """Base para herramientas usables por ReAct"""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass


class DatabaseQueryTool(ReActTool):
    name = "database_query"
    description = "Ejecuta consultas SQL SELECT contra la base de datos"

    def __init__(self, db_pool, sql_validator):
        self.db = db_pool
        self.validator = sql_validator

    async def execute(self, query: str) -> list[dict]:
        # Validar SQL
        validation = self.validator.validate(query)
        if not validation.is_valid:
            raise ValueError(f"SQL inválido: {validation.reason}")

        # Ejecutar
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]


class KnowledgeSearchTool(ReActTool):
    name = "knowledge_search"
    description = "Busca información en la base de conocimiento"

    def __init__(self, knowledge_manager):
        self.knowledge = knowledge_manager

    async def execute(self, search_term: str) -> list[dict]:
        results = await self.knowledge.search(search_term, limit=5)
        return [
            {"title": r.title, "content": r.content[:200]}
            for r in results
        ]


class CalculateTool(ReActTool):
    name = "calculate"
    description = "Evalúa expresiones matemáticas"

    async def execute(self, expression: str) -> float:
        # Usar evaluador seguro, no eval()
        import ast
        import operator

        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
        }

        def _eval(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](_eval(node.left), _eval(node.right))
            raise ValueError(f"Expresión no soportada")

        tree = ast.parse(expression, mode='eval')
        return _eval(tree.body)
```

---

## Integración con la Arquitectura Propuesta

```python
# src/agents/supervisor/agent.py

class SupervisorAgent:
    def __init__(self, ...):
        self.agents = {
            "database": DatabaseAgent(...),      # Single-step
            "knowledge": KnowledgeAgent(...),    # Single-step
            "chitchat": ChitchatAgent(...),      # Single-step
            "complex": ReActAgent(...),          # Multi-step con ReAct
        }

    async def handle(self, event: ConversationEvent) -> AgentResponse:
        intent = await self.classifier.classify(event, context)

        # Si la consulta es compleja, usar ReAct
        if intent.complexity == "complex" or intent.requires_multiple_steps:
            agent = self.agents["complex"]
        else:
            agent = self.agents[intent.suggested_agent]

        return await agent.execute(event, context)
```

---

## Cuándo usar ReAct vs Agentes Especializados

| Escenario | Enfoque | Por qué |
|-----------|---------|---------|
| "¿Cuántas ventas hubo ayer?" | DatabaseAgent | Una sola consulta, respuesta directa |
| "¿Qué es la política de devoluciones?" | KnowledgeAgent | Búsqueda simple en KB |
| "Hola, ¿cómo estás?" | ChitchatAgent | Conversación casual |
| "¿Quién vendió más el mes pasado y cuáles fueron sus productos top?" | **ReActAgent** | Requiere múltiples consultas relacionadas |
| "Compara las ventas de enero vs febrero y explica la tendencia" | **ReActAgent** | Análisis multi-paso |
| "Encuentra clientes inactivos y sugiere campañas" | **ReActAgent** | Razonamiento + múltiples fuentes |

---

## Ventajas de ReAct

1. **Transparencia**: Puedes ver el razonamiento del agente
2. **Corrección**: Puede ajustar su enfoque basándose en observaciones
3. **Flexibilidad**: No necesita saber de antemano cuántas queries hacer
4. **Composición**: Combina múltiples herramientas naturalmente

## Desventajas

1. **Latencia**: Múltiples llamadas al LLM = más lento
2. **Costo**: Más tokens = más caro
3. **Complejidad**: Más difícil de debuggear que agentes simples

---

## Recomendación

**Arquitectura híbrida**:

```
                    ┌─────────────────┐
                    │   SUPERVISOR    │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Single-Step    │ │  Single-Step    │ │   ReAct Agent   │
│  Agents         │ │  Agents         │ │   (Complex)     │
│                 │ │                 │ │                 │
│  - Database     │ │  - Knowledge    │ │  Para consultas │
│  - Chitchat     │ │  - Memory       │ │  multi-paso     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

- **80% de consultas**: Agentes single-step (rápidos, baratos)
- **20% de consultas**: ReActAgent (cuando se necesita razonamiento)

El Classifier detecta cuándo usar cada uno basándose en:
- Palabras clave: "compara", "analiza", "encuentra y luego"
- Complejidad sintáctica de la consulta
- Historial del usuario
