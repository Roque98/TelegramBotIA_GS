"""
ReAct Package - Agente con razonamiento paso a paso.

Este paquete contiene el agente ReAct que implementa el patrón
Reasoning + Acting para resolver consultas de forma autónoma.

Componentes:
- ReActAgent: Agente principal con loop Think-Act-Observe
- ActionType: Tipos de acciones disponibles
- ReActStep: Modelo de un paso del loop
- ReActResponse: Respuesta del LLM
- Scratchpad: Historial de pasos
"""

from .agent import ReActAgent
from .schemas import ActionType, ReActResponse, ReActStep
from .scratchpad import Scratchpad

__all__ = [
    "ReActAgent",
    "ActionType",
    "ReActResponse",
    "ReActStep",
    "Scratchpad",
]
