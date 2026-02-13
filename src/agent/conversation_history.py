"""
Gestor de historial conversacional.

Mantiene los últimos N mensajes de cada usuario para proporcionar
contexto conversacional al bot.
"""
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """
    Representa un mensaje en el historial conversacional.

    Attributes:
        user_id: ID del usuario
        message: Contenido del mensaje
        timestamp: Marca de tiempo del mensaje
        is_bot_response: True si es respuesta del bot, False si es del usuario
    """
    user_id: int
    message: str
    timestamp: datetime
    is_bot_response: bool = False


class ConversationHistory:
    """
    Gestor de historial conversacional en memoria.

    Mantiene los últimos N mensajes de cada usuario para proporcionar
    contexto a las respuestas del bot.
    """

    def __init__(self, max_messages: int = 3):
        """
        Inicializar el gestor de historial.

        Args:
            max_messages: Número máximo de mensajes a mantener por usuario
        """
        self.max_messages = max_messages
        # Diccionario: {user_id: deque de ConversationMessage}
        self._history: Dict[int, deque] = {}

        logger.info(f"ConversationHistory inicializado (max {max_messages} mensajes por usuario)")

    def add_user_message(self, user_id: int, message: str) -> None:
        """
        Agregar un mensaje del usuario al historial.

        Args:
            user_id: ID del usuario
            message: Contenido del mensaje
        """
        if user_id not in self._history:
            self._history[user_id] = deque(maxlen=self.max_messages * 2)  # x2 para user + bot

        msg = ConversationMessage(
            user_id=user_id,
            message=message,
            timestamp=datetime.now(),
            is_bot_response=False
        )

        self._history[user_id].append(msg)
        logger.debug(f"Mensaje agregado al historial de usuario {user_id}")

    def add_bot_response(self, user_id: int, response: str) -> None:
        """
        Agregar una respuesta del bot al historial.

        Args:
            user_id: ID del usuario
            response: Respuesta del bot
        """
        if user_id not in self._history:
            self._history[user_id] = deque(maxlen=self.max_messages * 2)

        msg = ConversationMessage(
            user_id=user_id,
            message=response,
            timestamp=datetime.now(),
            is_bot_response=True
        )

        self._history[user_id].append(msg)
        logger.debug(f"Respuesta del bot agregada al historial de usuario {user_id}")

    def get_recent_messages(
        self,
        user_id: int,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Obtener los mensajes recientes de un usuario.

        Args:
            user_id: ID del usuario
            limit: Número máximo de mensajes a retornar (None = todos)

        Returns:
            Lista de mensajes recientes, más antiguos primero
        """
        if user_id not in self._history:
            return []

        messages = list(self._history[user_id])

        if limit:
            messages = messages[-limit:]

        return messages

    def get_context_string(
        self,
        user_id: int,
        include_last_n: int = 3
    ) -> str:
        """
        Obtener el contexto conversacional como string formateado.

        Args:
            user_id: ID del usuario
            include_last_n: Número de pares de mensajes a incluir

        Returns:
            String con el historial formateado, o "" si no hay historial
        """
        messages = self.get_recent_messages(user_id)

        if not messages:
            return ""

        # Tomar solo los últimos N pares (usuario + bot)
        recent_messages = messages[-(include_last_n * 2):]

        if not recent_messages:
            return ""

        # Formatear como conversación
        context_parts = []
        for msg in recent_messages:
            if msg.is_bot_response:
                context_parts.append(f"Iris: {msg.message[:200]}")  # Truncar respuestas largas
            else:
                context_parts.append(f"Usuario: {msg.message}")

        context = "\n".join(context_parts)
        return f"Contexto conversacional reciente:\n{context}\n"

    def clear_user_history(self, user_id: int) -> None:
        """
        Limpiar el historial de un usuario.

        Args:
            user_id: ID del usuario
        """
        if user_id in self._history:
            del self._history[user_id]
            logger.info(f"Historial limpiado para usuario {user_id}")

    def clear_all_history(self) -> None:
        """Limpiar todo el historial."""
        count = len(self._history)
        self._history.clear()
        logger.info(f"Historial completo limpiado ({count} usuarios)")

    def get_stats(self) -> dict:
        """
        Obtener estadísticas del historial.

        Returns:
            Diccionario con estadísticas
        """
        total_users = len(self._history)
        total_messages = sum(len(msgs) for msgs in self._history.values())

        return {
            'total_users_with_history': total_users,
            'total_messages_stored': total_messages,
            'max_messages_per_user': self.max_messages * 2
        }
