"""
Scratchpad - Historial de pasos del agente ReAct.

Mantiene el registro de todos los pasos de razonamiento
y los formatea para incluir en el prompt del LLM.
"""

from typing import Any, Optional

from .schemas import ActionType, ReActStep


class Scratchpad:
    """
    Historial de pasos del loop ReAct.

    Mantiene los pasos ejecutados y proporciona métodos
    para formatearlos para el prompt del LLM.

    Attributes:
        max_steps: Número máximo de pasos permitidos
        steps: Lista de pasos ejecutados

    Example:
        >>> scratchpad = Scratchpad(max_steps=10)
        >>> scratchpad.add_step(
        ...     thought="Need to query database",
        ...     action=ActionType.DATABASE_QUERY,
        ...     action_input={"query": "SELECT ..."},
        ...     observation="[{...}]"
        ... )
        >>> print(scratchpad.to_prompt_format())
    """

    def __init__(self, max_steps: int = 10):
        """
        Inicializa el scratchpad.

        Args:
            max_steps: Número máximo de pasos permitidos
        """
        self.max_steps = max_steps
        self.steps: list[ReActStep] = []

    def add_step(
        self,
        thought: str,
        action: ActionType,
        action_input: dict[str, Any],
        observation: Optional[str] = None,
    ) -> ReActStep:
        """
        Agrega un nuevo paso al scratchpad.

        Args:
            thought: Razonamiento del agente
            action: Acción ejecutada
            action_input: Parámetros de la acción
            observation: Resultado de la acción

        Returns:
            El paso creado

        Raises:
            ValueError: Si el scratchpad está lleno
        """
        if self.is_full():
            raise ValueError(
                f"Scratchpad is full (max_steps={self.max_steps})"
            )

        step = ReActStep(
            step_number=len(self.steps) + 1,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation,
        )

        self.steps.append(step)
        return step

    def update_last_observation(self, observation: str) -> None:
        """
        Actualiza la observación del último paso.

        Args:
            observation: Resultado de ejecutar la acción

        Raises:
            ValueError: Si no hay pasos
        """
        if not self.steps:
            raise ValueError("No steps to update")

        self.steps[-1].observation = observation

    def is_full(self) -> bool:
        """
        Verifica si el scratchpad alcanzó el límite de pasos.

        Returns:
            True si está lleno
        """
        return len(self.steps) >= self.max_steps

    def is_empty(self) -> bool:
        """
        Verifica si el scratchpad está vacío.

        Returns:
            True si no hay pasos
        """
        return len(self.steps) == 0

    def to_prompt_format(self) -> str:
        """
        Genera el historial formateado para el prompt.

        Returns:
            String con todos los pasos formateados
        """
        if not self.steps:
            return ""

        formatted_steps = []
        for step in self.steps:
            formatted_steps.append(step.to_prompt_format())

        return "\n\n".join(formatted_steps)

    def to_dict(self) -> dict[str, Any]:
        """
        Convierte el scratchpad a diccionario.

        Returns:
            Diccionario con los pasos y metadata
        """
        return {
            "max_steps": self.max_steps,
            "current_steps": len(self.steps),
            "is_full": self.is_full(),
            "steps": [step.to_dict() for step in self.steps],
        }

    def get_last_step(self) -> Optional[ReActStep]:
        """
        Obtiene el último paso.

        Returns:
            Último paso o None si está vacío
        """
        return self.steps[-1] if self.steps else None

    def get_last_observation(self) -> Optional[str]:
        """
        Obtiene la observación del último paso.

        Returns:
            Observación del último paso o None
        """
        last = self.get_last_step()
        return last.observation if last else None

    def get_all_observations(self) -> list[str]:
        """
        Obtiene todas las observaciones.

        Returns:
            Lista de observaciones (excluyendo None)
        """
        return [
            step.observation
            for step in self.steps
            if step.observation is not None
        ]

    def get_summary(self) -> str:
        """
        Genera un resumen de los pasos ejecutados.

        Útil para debugging y logs.

        Returns:
            String con resumen de pasos
        """
        if not self.steps:
            return "No steps executed"

        lines = [f"Steps executed: {len(self.steps)}/{self.max_steps}"]

        for step in self.steps:
            obs_preview = ""
            if step.observation:
                obs_preview = f" -> {step.observation[:50]}..."
            lines.append(
                f"  {step.step_number}. {step.action.value}{obs_preview}"
            )

        return "\n".join(lines)

    def clear(self) -> None:
        """Limpia todos los pasos."""
        self.steps.clear()

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:
        return f"<Scratchpad(steps={len(self.steps)}/{self.max_steps})>"
