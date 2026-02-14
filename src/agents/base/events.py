"""
Events - Modelos de eventos y contexto.

Este módulo define:
- ConversationEvent: Evento normalizado de entrada (Telegram, API, etc.)
- UserContext: Contexto del usuario para el agente
"""

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ConversationEvent(BaseModel):
    """
    Evento normalizado de cualquier canal de entrada.

    Representa un mensaje del usuario independientemente de si
    viene de Telegram, API REST, WebSocket, etc.

    Attributes:
        event_id: ID único del evento
        user_id: ID del usuario
        channel: Canal de origen (telegram, api, websocket)
        text: Texto del mensaje
        timestamp: Momento del evento
        correlation_id: ID para trazar la conversación completa
        metadata: Datos adicionales del canal
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    channel: str
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": False}

    @classmethod
    def from_telegram(
        cls,
        user_id: int,
        text: str,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> "ConversationEvent":
        """
        Crea un evento desde un mensaje de Telegram.

        Args:
            user_id: ID del usuario de Telegram
            text: Texto del mensaje
            chat_id: ID del chat
            username: Username de Telegram (opcional)
            first_name: Nombre del usuario (opcional)

        Returns:
            ConversationEvent normalizado
        """
        return cls(
            user_id=str(user_id),
            channel="telegram",
            text=text,
            correlation_id=str(chat_id),
            metadata={
                "chat_id": chat_id,
                "username": username,
                "first_name": first_name,
            },
        )

    @classmethod
    def from_api(
        cls,
        user_id: str,
        text: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ConversationEvent":
        """
        Crea un evento desde una llamada API.

        Args:
            user_id: ID del usuario
            text: Texto del mensaje
            session_id: ID de sesión (opcional)
            metadata: Metadata adicional (opcional)

        Returns:
            ConversationEvent normalizado
        """
        return cls(
            user_id=user_id,
            channel="api",
            text=text,
            correlation_id=session_id or str(uuid4()),
            metadata=metadata or {},
        )


class UserContext(BaseModel):
    """
    Contexto del usuario para el agente.

    Contiene toda la información necesaria para que el agente
    pueda responder de manera personalizada.

    Attributes:
        user_id: ID único del usuario
        display_name: Nombre para mostrar
        roles: Lista de roles/permisos del usuario
        preferences: Preferencias detectadas del usuario
        working_memory: Últimos mensajes de la conversación
        long_term_summary: Resumen de memoria a largo plazo
        current_date: Fecha actual (para consultas temporales)
    """

    user_id: str
    display_name: str = "Usuario"
    roles: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    working_memory: list[dict[str, Any]] = Field(default_factory=list)
    long_term_summary: Optional[str] = None
    current_date: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"frozen": False}

    @classmethod
    def empty(cls, user_id: str) -> "UserContext":
        """
        Crea un contexto vacío para un usuario nuevo.

        Args:
            user_id: ID del usuario

        Returns:
            UserContext con valores por defecto
        """
        return cls(user_id=user_id)

    def add_message(self, role: str, content: str) -> None:
        """
        Agrega un mensaje a la memoria de trabajo.

        Args:
            role: Rol del mensaje (user, assistant)
            content: Contenido del mensaje
        """
        self.working_memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def get_recent_messages(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Obtiene los mensajes más recientes.

        Args:
            limit: Número máximo de mensajes

        Returns:
            Lista de mensajes recientes
        """
        return self.working_memory[-limit:]

    def to_prompt_context(self) -> str:
        """
        Genera una representación textual del contexto para prompts.

        Returns:
            String con el contexto formateado
        """
        lines = [
            f"Usuario: {self.display_name}",
            f"Fecha actual: {self.current_date.strftime('%Y-%m-%d')}",
        ]

        if self.roles:
            lines.append(f"Roles: {', '.join(self.roles)}")

        if self.long_term_summary:
            lines.append(f"Historial: {self.long_term_summary}")

        if self.working_memory:
            lines.append("\nMensajes recientes de esta conversación:")
            for msg in self.working_memory[-5:]:  # Últimos 5 mensajes
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]  # Truncar si muy largo
                lines.append(f"  [{role}]: {content}")

        return "\n".join(lines)
