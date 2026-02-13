"""
Rate limiter simple para prevenir abuso.

Implementa un rate limiter basado en ventanas de tiempo por usuario.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter simple basado en usuario."""

    def __init__(
        self,
        max_requests: int = 10,
        time_window: int = 60  # segundos
    ):
        """
        Inicializar rate limiter.

        Args:
            max_requests: Número máximo de requests en la ventana
            time_window: Ventana de tiempo en segundos
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, List[datetime]] = defaultdict(list)
        logger.info(
            f"RateLimiter inicializado: {max_requests} requests/{time_window}s"
        )

    def is_allowed(self, user_id: int) -> bool:
        """
        Verificar si el usuario puede hacer request.

        Args:
            user_id: ID del usuario

        Returns:
            True si está permitido, False si alcanzó el límite
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)

        # Limpiar requests antiguos
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff
        ]

        # Verificar límite
        if len(self.requests[user_id]) >= self.max_requests:
            logger.warning(
                f"Rate limit excedido para usuario {user_id}: "
                f"{len(self.requests[user_id])} requests en {self.time_window}s"
            )
            return False

        # Agregar nuevo request
        self.requests[user_id].append(now)
        return True

    def get_retry_after(self, user_id: int) -> int:
        """
        Obtener segundos hasta que pueda hacer otro request.

        Args:
            user_id: ID del usuario

        Returns:
            Segundos hasta el siguiente request permitido
        """
        if not self.requests[user_id]:
            return 0

        oldest_request = min(self.requests[user_id])
        retry_after = self.time_window - (datetime.now() - oldest_request).seconds
        return max(0, retry_after)

    def get_remaining_requests(self, user_id: int) -> int:
        """
        Obtener número de requests restantes en la ventana actual.

        Args:
            user_id: ID del usuario

        Returns:
            Número de requests restantes
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)

        # Limpiar requests antiguos
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff
        ]

        return max(0, self.max_requests - len(self.requests[user_id]))
