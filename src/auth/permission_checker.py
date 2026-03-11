"""
Verificador de permisos para operaciones del bot.

Este módulo integra con los stored procedures de la base de datos:
- sp_VerificarPermisoOperacion: Verifica si un usuario puede ejecutar una operación
- sp_ObtenerOperacionesUsuario: Obtiene todas las operaciones disponibles para un usuario
- sp_RegistrarLogOperacion: Registra la ejecución de operaciones para auditoría
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PermissionResult:
    """Resultado de verificación de permisos."""

    def __init__(self, data: Dict[str, Any]):
        """
        Inicializar resultado de verificación.

        Args:
            data: Datos del resultado de la verificación
        """
        self.tiene_permiso = data.get('TienePermiso', False)
        self.mensaje = data.get('Mensaje', '')
        self.nombre_operacion = data.get('NombreOperacion')
        self.descripcion_operacion = data.get('DescripcionOperacion')
        self.requiere_parametros = data.get('RequiereParametros', False)
        self.parametros_ejemplo = data.get('ParametrosEjemplo')

    @property
    def is_allowed(self) -> bool:
        """Verificar si el permiso está permitido."""
        return bool(self.tiene_permiso)

    def __repr__(self) -> str:
        return (
            f"PermissionResult(permitido={self.tiene_permiso}, "
            f"operacion='{self.nombre_operacion}')"
        )


class Operation:
    """Representa una operación disponible."""

    def __init__(self, data: Dict[str, Any]):
        """
        Inicializar operación.

        Args:
            data: Datos de la operación
        """
        self.modulo = data.get('Modulo')
        self.icono_modulo = data.get('IconoModulo')
        self.id_operacion = data.get('idOperacion')
        self.operacion = data.get('Operacion')
        self.descripcion = data.get('descripcion')
        self.comando = data.get('comando')
        self.requiere_parametros = data.get('requiereParametros', False)
        self.parametros_ejemplo = data.get('parametrosEjemplo')
        self.nivel_criticidad = data.get('nivelCriticidad', 1)
        self.origen_permiso = data.get('OrigenPermiso')
        self.permitido = data.get('Permitido', False)

    def __repr__(self) -> str:
        return f"Operation(comando='{self.comando}', permitido={self.permitido})"


class PermissionChecker:
    """Verificador de permisos basado en stored procedures."""

    def __init__(self, db_session: Session):
        """
        Inicializar verificador de permisos.

        Args:
            db_session: Sesión de base de datos SQLAlchemy
        """
        self.session = db_session

    def check_permission(
        self,
        user_id: int,
        comando: str
    ) -> PermissionResult:
        """
        Verificar si un usuario tiene permiso para ejecutar una operación.

        Llama al stored procedure sp_VerificarPermisoOperacion.

        Args:
            user_id: ID del usuario
            comando: Comando a verificar (ej: '/crear_ticket')

        Returns:
            PermissionResult con el resultado de la verificación
        """
        try:
            query = text("""
                EXEC consolaMonitoreo..BotIA_sp_VerificarPermisoOperacion
                    @idUsuario = :user_id,
                    @comando = :comando
            """)

            result = self.session.execute(
                query,
                {"user_id": user_id, "comando": comando}
            )
            row = result.fetchone()

            if row:
                data = dict(zip(result.keys(), row))
                return PermissionResult(data)

            # Si no hay resultado, denegar por defecto
            return PermissionResult({
                'TienePermiso': False,
                'Mensaje': 'Operación no encontrada'
            })

        except Exception as e:
            logger.error(
                f"Error verificando permiso para usuario {user_id}, "
                f"comando {comando}: {e}"
            )
            raise

    def get_user_operations(self, user_id: int) -> List[Operation]:
        """
        Obtener todas las operaciones disponibles para un usuario.

        Llama al stored procedure sp_ObtenerOperacionesUsuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de operaciones disponibles
        """
        try:
            query = text("""
                EXEC consolaMonitoreo..BotIA_sp_ObtenerOperacionesUsuario
                    @idUsuario = :user_id
            """)

            result = self.session.execute(query, {"user_id": user_id})
            rows = result.fetchall()

            operations = []
            for row in rows:
                data = dict(zip(result.keys(), row))
                operations.append(Operation(data))

            return operations

        except Exception as e:
            logger.error(
                f"Error obteniendo operaciones del usuario {user_id}: {e}"
            )
            raise

    def get_user_operations_by_module(
        self,
        user_id: int
    ) -> Dict[str, List[Operation]]:
        """
        Obtener operaciones agrupadas por módulo.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con módulos como claves y listas de operaciones
        """
        operations = self.get_user_operations(user_id)

        # Agrupar por módulo
        by_module = {}
        for op in operations:
            module_name = op.modulo or 'Sin Módulo'
            if module_name not in by_module:
                by_module[module_name] = []
            by_module[module_name].append(op)

        return by_module

    def log_operation(
        self,
        user_id: int,
        comando: str,
        telegram_chat_id: Optional[int] = None,
        telegram_username: Optional[str] = None,
        parametros: Optional[Dict[str, Any]] = None,
        resultado: str = 'EXITOSO',
        mensaje_error: Optional[str] = None,
        duracion_ms: Optional[int] = None,
        ip_origen: Optional[str] = None
    ) -> bool:
        """
        Registrar la ejecución de una operación.

        Llama al stored procedure sp_RegistrarLogOperacion.

        Args:
            user_id: ID del usuario
            comando: Comando ejecutado
            telegram_chat_id: Chat ID de Telegram
            telegram_username: Username de Telegram
            parametros: Parámetros de la operación (se convertirá a JSON)
            resultado: EXITOSO, ERROR o DENEGADO
            mensaje_error: Mensaje de error si aplica
            duracion_ms: Duración en milisegundos
            ip_origen: IP de origen

        Returns:
            True si se registró correctamente
        """
        try:
            # Convertir parámetros a JSON
            parametros_json = None
            if parametros:
                parametros_json = json.dumps(parametros, ensure_ascii=False)

            query = text("""
                EXEC consolaMonitoreo..BotIA_sp_RegistrarLogOperacion
                    @idUsuario = :user_id,
                    @comando = :comando,
                    @telegramChatId = :telegram_chat_id,
                    @telegramUsername = :telegram_username,
                    @parametros = :parametros,
                    @resultado = :resultado,
                    @mensajeError = :mensaje_error,
                    @duracionMs = :duracion_ms,
                    @ipOrigen = :ip_origen
            """)

            self.session.execute(
                query,
                {
                    "user_id": user_id,
                    "comando": comando,
                    "telegram_chat_id": telegram_chat_id,
                    "telegram_username": telegram_username,
                    "parametros": parametros_json,
                    "resultado": resultado,
                    "mensaje_error": mensaje_error,
                    "duracion_ms": duracion_ms,
                    "ip_origen": ip_origen
                }
            )
            self.session.commit()

            logger.info(
                f"Log registrado: usuario={user_id}, comando={comando}, "
                f"resultado={resultado}"
            )
            return True

        except Exception as e:
            logger.error(f"Error registrando log de operación: {e}")
            self.session.rollback()
            return False

    def get_command_operations_map(self, user_id: int) -> Dict[str, Operation]:
        """
        Obtener un mapa de comandos a operaciones permitidas.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con comandos como claves y operaciones como valores
        """
        operations = self.get_user_operations(user_id)

        command_map = {}
        for op in operations:
            if op.comando and op.permitido:
                command_map[op.comando] = op

        return command_map

    def is_operation_critical(self, user_id: int, comando: str) -> bool:
        """
        Verificar si una operación es crítica (nivel 3 o 4).

        Args:
            user_id: ID del usuario
            comando: Comando a verificar

        Returns:
            True si la operación es crítica
        """
        operations = self.get_command_operations_map(user_id)
        operation = operations.get(comando)

        if operation:
            return operation.nivel_criticidad >= 3

        return False
