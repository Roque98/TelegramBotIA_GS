"""
Message Gateway - Normaliza input de diferentes canales.

Convierte mensajes de Telegram, API REST, WebSocket, etc.
a ConversationEvent para procesamiento uniforme.
"""

import logging
from typing import Any, Optional

from telegram import Update

from src.agents.base.events import ConversationEvent

logger = logging.getLogger(__name__)


class MessageGateway:
    """
    Gateway para normalizar mensajes de diferentes canales.

    Convierte mensajes de cualquier fuente a ConversationEvent
    para que el sistema los procese de manera uniforme.

    Example:
        ```python
        gateway = MessageGateway()
        event = gateway.from_telegram(update)
        # event es un ConversationEvent normalizado
        ```
    """

    def from_telegram(self, update: Update) -> ConversationEvent:
        """
        Crea un ConversationEvent desde un Update de Telegram.

        Args:
            update: Update de python-telegram-bot

        Returns:
            ConversationEvent normalizado

        Raises:
            ValueError: Si el update no tiene mensaje o texto
        """
        if not update.message:
            raise ValueError("Update does not contain a message")

        if not update.message.text:
            raise ValueError("Message does not contain text")

        user = update.effective_user
        if not user:
            raise ValueError("Update does not have an effective user")

        event = ConversationEvent.from_telegram(
            user_id=user.id,
            text=update.message.text,
            chat_id=update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
        )

        logger.debug(
            f"Created event from Telegram: user={user.id}, "
            f"text_length={len(update.message.text)}"
        )

        return event

    def from_api(
        self,
        user_id: str,
        text: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ConversationEvent:
        """
        Crea un ConversationEvent desde una llamada API.

        Args:
            user_id: ID del usuario
            text: Texto del mensaje
            session_id: ID de sesión opcional
            metadata: Metadata adicional

        Returns:
            ConversationEvent normalizado
        """
        event = ConversationEvent.from_api(
            user_id=user_id,
            text=text,
            session_id=session_id,
            metadata=metadata,
        )

        logger.debug(
            f"Created event from API: user={user_id}, "
            f"text_length={len(text)}"
        )

        return event

    def from_websocket(
        self,
        user_id: str,
        text: str,
        connection_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ConversationEvent:
        """
        Crea un ConversationEvent desde un mensaje WebSocket.

        Args:
            user_id: ID del usuario
            text: Texto del mensaje
            connection_id: ID de conexión WebSocket
            metadata: Metadata adicional

        Returns:
            ConversationEvent normalizado
        """
        event = ConversationEvent(
            user_id=user_id,
            channel="websocket",
            text=text,
            correlation_id=connection_id,
            metadata={
                "connection_id": connection_id,
                **(metadata or {}),
            },
        )

        logger.debug(
            f"Created event from WebSocket: user={user_id}, "
            f"connection={connection_id}"
        )

        return event

    def extract_user_info(self, event: ConversationEvent) -> dict[str, Any]:
        """
        Extrae información del usuario de un evento.

        Útil para logging y auditoría.

        Args:
            event: Evento del cual extraer información

        Returns:
            Dict con información del usuario
        """
        return {
            "user_id": event.user_id,
            "channel": event.channel,
            "correlation_id": event.correlation_id,
            "timestamp": event.timestamp.isoformat(),
            **event.metadata,
        }
