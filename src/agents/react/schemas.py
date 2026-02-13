"""
ReAct Schemas - Modelos de datos para el agente ReAct.

Este módulo define:
- ActionType: Enum de acciones disponibles
- ReActStep: Modelo de un paso del loop
- ReActResponse: Respuesta del LLM en cada iteración
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """
    Tipos de acciones que el agente puede ejecutar.

    Cada acción corresponde a un tool disponible o a FINISH
    para terminar el razonamiento.
    """

    DATABASE_QUERY = "database_query"
    KNOWLEDGE_SEARCH = "knowledge_search"
    CALCULATE = "calculate"
    DATETIME = "datetime"
    FINISH = "finish"

    @classmethod
    def from_string(cls, value: str) -> "ActionType":
        """
        Convierte un string a ActionType.

        Args:
            value: Nombre de la acción

        Returns:
            ActionType correspondiente

        Raises:
            ValueError: Si la acción no existe
        """
        value_lower = value.lower().strip()

        # Mapeo de aliases
        aliases = {
            "db": cls.DATABASE_QUERY,
            "database": cls.DATABASE_QUERY,
            "query": cls.DATABASE_QUERY,
            "sql": cls.DATABASE_QUERY,
            "knowledge": cls.KNOWLEDGE_SEARCH,
            "kb": cls.KNOWLEDGE_SEARCH,
            "search": cls.KNOWLEDGE_SEARCH,
            "calc": cls.CALCULATE,
            "math": cls.CALCULATE,
            "date": cls.DATETIME,
            "time": cls.DATETIME,
            "done": cls.FINISH,
            "end": cls.FINISH,
            "answer": cls.FINISH,
        }

        if value_lower in aliases:
            return aliases[value_lower]

        try:
            return cls(value_lower)
        except ValueError:
            raise ValueError(
                f"Unknown action: {value}. "
                f"Valid actions: {[a.value for a in cls]}"
            )

    def is_tool(self) -> bool:
        """Retorna True si la acción es un tool (no FINISH)."""
        return self != ActionType.FINISH


class ReActStep(BaseModel):
    """
    Representa un paso completo del loop ReAct.

    Attributes:
        step_number: Número del paso (1-indexed)
        thought: Razonamiento del agente
        action: Acción a ejecutar
        action_input: Parámetros de la acción
        observation: Resultado de ejecutar la acción
        timestamp: Momento del paso
    """

    step_number: int
    thought: str
    action: ActionType
    action_input: dict[str, Any] = Field(default_factory=dict)
    observation: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_prompt_format(self) -> str:
        """
        Genera formato para incluir en el prompt.

        Returns:
            String formateado del paso
        """
        lines = [
            f"Step {self.step_number}:",
            f"Thought: {self.thought}",
            f"Action: {self.action.value}",
            f"Action Input: {self.action_input}",
        ]

        if self.observation is not None:
            lines.append(f"Observation: {self.observation}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convierte el paso a diccionario."""
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action.value,
            "action_input": self.action_input,
            "observation": self.observation,
            "timestamp": self.timestamp.isoformat(),
        }


class ReActResponse(BaseModel):
    """
    Respuesta del LLM en cada iteración del loop.

    Este es el formato que esperamos del LLM cuando genera
    el siguiente paso de razonamiento.

    Attributes:
        thought: Razonamiento sobre qué hacer
        action: Acción a ejecutar
        action_input: Parámetros para la acción
        final_answer: Respuesta final (solo si action=FINISH)
    """

    thought: str = Field(
        description="Your reasoning about what to do next"
    )
    action: ActionType = Field(
        description="The action to take"
    )
    action_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the action"
    )
    final_answer: Optional[str] = Field(
        default=None,
        description="Your final answer to the user (only if action is 'finish')"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "thought": "The user is asking about sales. I need to query the database.",
                    "action": "database_query",
                    "action_input": {"query": "SELECT COUNT(*) FROM ventas"},
                    "final_answer": None,
                },
                {
                    "thought": "I have all the information I need to answer.",
                    "action": "finish",
                    "action_input": {},
                    "final_answer": "There were 150 sales yesterday.",
                },
            ]
        }
    }

    def is_final(self) -> bool:
        """Retorna True si esta es la respuesta final."""
        return self.action == ActionType.FINISH

    @classmethod
    def finish(cls, thought: str, answer: str) -> "ReActResponse":
        """
        Factory para crear respuesta final.

        Args:
            thought: Razonamiento final
            answer: Respuesta al usuario

        Returns:
            ReActResponse con action=FINISH
        """
        return cls(
            thought=thought,
            action=ActionType.FINISH,
            action_input={},
            final_answer=answer,
        )

    @classmethod
    def tool_call(
        cls,
        thought: str,
        action: ActionType,
        action_input: dict[str, Any],
    ) -> "ReActResponse":
        """
        Factory para crear llamada a tool.

        Args:
            thought: Razonamiento
            action: Tool a ejecutar
            action_input: Parámetros del tool

        Returns:
            ReActResponse con la llamada al tool
        """
        if action == ActionType.FINISH:
            raise ValueError("Use ReActResponse.finish() for final responses")

        return cls(
            thought=thought,
            action=action,
            action_input=action_input,
        )
