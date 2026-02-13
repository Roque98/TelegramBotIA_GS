"""
Validador de inputs de usuario.

Proporciona validación y sanitización de inputs para prevenir ataques.
"""
import re
from typing import Tuple


class InputValidator:
    """Validador de inputs de usuario."""

    MAX_QUERY_LENGTH = 500  # Caracteres
    MIN_QUERY_LENGTH = 3

    # Patrones sospechosos
    SUSPICIOUS_PATTERNS = [
        r'<script',  # XSS attempt
        r'javascript:',  # XSS attempt
        r'data:text/html',  # Data URI XSS
        r'\x00',  # Null bytes
    ]

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, str]:
        """
        Validar query de usuario.

        Args:
            query: Query a validar

        Returns:
            (is_valid, error_message)
        """
        # Verificar que no esté vacío
        if not query or not query.strip():
            return False, "La consulta no puede estar vacía"

        # Verificar longitud
        if len(query) < cls.MIN_QUERY_LENGTH:
            return False, f"Consulta muy corta (mínimo {cls.MIN_QUERY_LENGTH} caracteres)"

        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, f"Consulta muy larga (máximo {cls.MAX_QUERY_LENGTH} caracteres)"

        # Verificar patrones sospechosos
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, "La consulta contiene contenido no permitido"

        # Verificar exceso de caracteres especiales (posible attack)
        special_char_ratio = sum(not c.isalnum() and not c.isspace() for c in query) / len(query)
        if special_char_ratio > 0.3:  # >30% caracteres especiales
            return False, "La consulta contiene demasiados caracteres especiales"

        return True, ""

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """
        Sanitizar query removiendo elementos peligrosos.

        Args:
            query: Query a sanitizar

        Returns:
            Query sanitizada
        """
        # Remover null bytes
        sanitized = query.replace('\x00', '')

        # Normalizar espacios
        sanitized = ' '.join(sanitized.split())

        # Remover leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized
