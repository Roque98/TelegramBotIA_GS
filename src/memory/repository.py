"""
Memory Repository - Persistencia de memoria para el ReAct Agent.

Adapta el MemoryRepository existente al nuevo formato de UserContext.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class DatabaseManager(Protocol):
    """Protocolo para el gestor de base de datos."""

    def execute_query(self, query: str, params: Optional[dict] = None) -> list:
        """Ejecuta una query y retorna resultados."""
        ...

    def execute_non_query(self, query: str, params: Optional[dict] = None) -> int:
        """Ejecuta una query sin resultados."""
        ...


@dataclass
class UserProfile:
    """
    Perfil de usuario con información de memoria.

    Attributes:
        user_id: ID del usuario
        display_name: Nombre para mostrar
        roles: Lista de roles/permisos
        long_term_summary: Resumen de memoria a largo plazo
        interaction_count: Número de interacciones
        last_updated: Última actualización del perfil
    """

    user_id: str
    display_name: str = "Usuario"
    roles: list[str] = field(default_factory=list)
    long_term_summary: Optional[str] = None
    interaction_count: int = 0
    last_updated: Optional[datetime] = None
    preferences: dict[str, Any] = field(default_factory=dict)

    def has_summary(self) -> bool:
        """Verifica si el perfil tiene resumen de memoria."""
        return self.long_term_summary is not None and len(self.long_term_summary) > 0


@dataclass
class Interaction:
    """
    Representa una interacción usuario-agente.

    Attributes:
        interaction_id: ID único
        user_id: ID del usuario
        query: Consulta del usuario
        response: Respuesta del agente
        timestamp: Momento de la interacción
        metadata: Datos adicionales
    """

    interaction_id: str
    user_id: str
    query: str
    response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryRepository:
    """
    Repository para acceso a memoria de usuarios.

    Proporciona métodos para:
    - Obtener y guardar perfiles de usuario
    - Registrar y recuperar interacciones
    - Gestionar resúmenes de memoria
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Inicializa el repository.

        Args:
            db_manager: Gestor de base de datos (opcional para testing)
        """
        self.db_manager = db_manager
        self._profiles_cache: dict[str, UserProfile] = {}
        logger.info("MemoryRepository inicializado")

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Obtiene el perfil de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            UserProfile o None si no existe
        """
        # Check cache first
        if user_id in self._profiles_cache:
            return self._profiles_cache[user_id]

        if not self.db_manager:
            return None

        try:
            # Intentar obtener desde UserMemoryProfiles
            # user_id puede ser Telegram chat ID, así que buscamos a través de UsuariosTelegram
            query = """
                SELECT
                    u.idUsuario AS Id_Usuario,
                    CONCAT(u.nombre, ' ', u.apellido) AS Nombre,
                    ump.resumenContextoLaboral AS resumen_contexto_laboral,
                    ump.resumenTemasRecientes AS resumen_temas_recientes,
                    ump.resumenHistorialBreve AS resumen_historial_breve,
                    ump.numInteracciones AS num_interacciones,
                    ump.ultimaActualizacion AS ultima_actualizacion,
                    ump.preferencias AS preferencias
                FROM abcmasplus..UsuariosTelegram ut
                INNER JOIN abcmasplus..Usuarios u ON ut.idUsuario = u.idUsuario
                LEFT JOIN abcmasplus..UserMemoryProfiles ump ON u.idUsuario = ump.idUsuario
                WHERE ut.telegramChatId = :user_id
                  AND ut.activo = 1
            """

            results = self.db_manager.execute_query(query, {"user_id": str(user_id)})

            if not results:
                return None

            row = results[0]

            # Combinar resúmenes en uno solo
            summaries = []
            if row.get("resumen_contexto_laboral"):
                summaries.append(row["resumen_contexto_laboral"])
            if row.get("resumen_temas_recientes"):
                summaries.append(row["resumen_temas_recientes"])
            if row.get("resumen_historial_breve"):
                summaries.append(row["resumen_historial_breve"])

            # Parsear preferencias
            preferences = {}
            if row.get("preferencias"):
                try:
                    preferences = json.loads(row["preferencias"])
                except json.JSONDecodeError:
                    preferences = {}

            # Usar alias de preferencias como display_name si existe
            display_name = preferences.get("alias") or row.get("Nombre", "Usuario")

            profile = UserProfile(
                user_id=user_id,
                display_name=display_name,
                long_term_summary="\n\n".join(summaries) if summaries else None,
                interaction_count=row.get("num_interacciones", 0),
                last_updated=row.get("ultima_actualizacion"),
                preferences=preferences,
            )

            self._profiles_cache[user_id] = profile
            return profile

        except Exception as e:
            logger.error(f"Error getting profile for {user_id}: {e}")
            return None

    async def save_profile(self, profile: UserProfile) -> bool:
        """
        Guarda el perfil de un usuario.

        Args:
            profile: Perfil a guardar

        Returns:
            True si se guardó correctamente
        """
        if not self.db_manager:
            # En modo sin DB, solo actualizar cache
            self._profiles_cache[profile.user_id] = profile
            return True

        try:
            # Upsert en UserMemoryProfiles
            query = """
                MERGE INTO UserMemoryProfiles AS target
                USING (SELECT :user_id AS id_usuario) AS source
                ON target.id_usuario = source.id_usuario
                WHEN MATCHED THEN
                    UPDATE SET
                        resumen_historial_breve = :summary,
                        num_interacciones = :count,
                        ultima_actualizacion = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (id_usuario, resumen_historial_breve, num_interacciones, fecha_creacion, ultima_actualizacion)
                    VALUES (:user_id, :summary, :count, GETDATE(), GETDATE());
            """

            self.db_manager.execute_non_query(
                query,
                {
                    "user_id": int(profile.user_id),
                    "summary": profile.long_term_summary,
                    "count": profile.interaction_count,
                },
            )

            # Actualizar cache
            self._profiles_cache[profile.user_id] = profile
            return True

        except Exception as e:
            logger.error(f"Error saving profile for {profile.user_id}: {e}")
            return False

    async def get_recent_messages(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Obtiene los mensajes recientes de un usuario.

        Args:
            user_id: ID del usuario
            limit: Número máximo de mensajes

        Returns:
            Lista de mensajes en formato {role, content, timestamp}
        """
        if not self.db_manager:
            return []

        try:
            # user_id es Telegram chat ID, buscar idUsuario interno
            query = """
                SELECT TOP (:limit)
                    lo.idOperacion AS Comando,
                    lo.parametros AS Parametros,
                    lo.resultado AS Resultado,
                    lo.fechaEjecucion AS Fecha_Hora
                FROM abcmasplus..LogOperaciones lo
                INNER JOIN abcmasplus..UsuariosTelegram ut ON lo.idUsuario = ut.idUsuario
                WHERE ut.telegramChatId = :user_id
                  AND ut.activo = 1
                ORDER BY lo.fechaEjecucion DESC
            """

            logger.debug(f"Fetching messages for telegram_chat_id={user_id}, limit={limit}")
            results = self.db_manager.execute_query(
                query, {"user_id": str(user_id), "limit": limit}
            )
            logger.debug(f"Query returned {len(results)} rows for user {user_id}")

            messages = []
            for row in reversed(results):  # Orden cronológico
                # Extraer query del usuario
                params = row.get("Parametros", {})
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        params = {"query": params}

                user_query = params.get("query", "")
                if user_query:
                    messages.append({
                        "role": "user",
                        "content": user_query,
                        "timestamp": row.get("Fecha_Hora", datetime.now(UTC)).isoformat(),
                    })

                # Agregar respuesta del asistente
                resultado = row.get("Resultado", "")
                if resultado and resultado != "EXITOSO":
                    messages.append({
                        "role": "assistant",
                        "content": resultado,
                        "timestamp": row.get("Fecha_Hora", datetime.now(UTC)).isoformat(),
                    })

            logger.debug(f"Built {len(messages)} messages for working_memory")
            if messages:
                logger.debug(f"First message: {messages[0]}")
            return messages

        except Exception as e:
            logger.error(f"Error getting messages for {user_id}: {e}")
            return []

    async def save_interaction(
        self,
        user_id: str,
        query: str,
        response: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Guarda una interacción.

        Args:
            user_id: ID del usuario
            query: Consulta del usuario
            response: Respuesta del agente
            metadata: Datos adicionales

        Returns:
            True si se guardó correctamente
        """
        if not self.db_manager:
            return True

        try:
            params_json = json.dumps({"query": query, **(metadata or {})})
            duration_ms = (metadata or {}).get("execution_time_ms", 0)

            query_sql = """
                INSERT INTO abcmasplus..LogOperaciones (
                    idUsuario, idOperacion, telegramChatId,
                    parametros, resultado, duracionMs, fechaEjecucion
                )
                SELECT
                    ut.idUsuario,
                    :operation,
                    :chat_id,
                    :params,
                    :result,
                    :duration_ms,
                    GETDATE()
                FROM abcmasplus..UsuariosTelegram ut
                WHERE ut.telegramChatId = :chat_id_lookup
                  AND ut.activo = 1
            """

            self.db_manager.execute_non_query(
                query_sql,
                {
                    "operation": "chat_ia",
                    "chat_id": str(user_id),
                    "params": params_json,
                    "result": response[:4000],
                    "duration_ms": int(duration_ms),
                    "chat_id_lookup": str(user_id),
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error saving interaction for {user_id}: {e}")
            return False

    async def get_interaction_count(self, user_id: str) -> int:
        """
        Obtiene el número de interacciones de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Número de interacciones
        """
        profile = await self.get_profile(user_id)
        return profile.interaction_count if profile else 0

    async def increment_interaction_count(self, user_id: str) -> int:
        """
        Incrementa el contador de interacciones.

        Args:
            user_id: ID del usuario

        Returns:
            Nuevo contador
        """
        profile = await self.get_profile(user_id)

        if not profile:
            profile = UserProfile(user_id=user_id, interaction_count=1)
        else:
            profile.interaction_count += 1

        await self.save_profile(profile)
        return profile.interaction_count

    def invalidate_cache(self, user_id: str) -> None:
        """Invalida el cache para un usuario."""
        if user_id in self._profiles_cache:
            del self._profiles_cache[user_id]

    def clear_cache(self) -> None:
        """Limpia todo el cache."""
        self._profiles_cache.clear()
