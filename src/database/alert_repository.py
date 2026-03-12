"""
Repositorio de alertas de monitoreo PRTG.
Ejecuta los SPs de eventos e historial de tickets contra la BD BAZ_CDMX.
"""
import logging
from typing import List, Dict, Any

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

# Alias de BD donde viven los SPs de monitoreo
_DB_ALIAS = "BAZ_CDMX"


class AlertRepository:
    """Acceso a datos de alertas PRTG e historial de tickets."""

    def get_active_events(
        self,
        ip: str = None,
        equipo: str = None,
        solo_down: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene eventos activos ejecutando PrtgObtenerEventosEnriquecidos.

        Args:
            ip: Filtra por IP exacta del equipo.
            equipo: Filtra por nombre de equipo (búsqueda parcial).
            solo_down: Si True, retorna solo eventos con Status='Down'.

        Returns:
            Lista de eventos como diccionarios.
        """
        db = DatabaseManager.get(_DB_ALIAS)
        rows = db.execute_query("EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidos")

        if ip:
            rows = [r for r in rows if r.get("IP") == ip]
        if equipo:
            rows = [r for r in rows if equipo.lower() in (r.get("Equipo") or "").lower()]
        if solo_down:
            rows = [r for r in rows if (r.get("Status") or "").lower() == "down"]

        logger.info(
            f"get_active_events → {len(rows)} evento(s) "
            f"[ip={ip}, equipo={equipo}, solo_down={solo_down}]"
        )
        return rows

    def get_historical_tickets(
        self,
        ip: str,
        sensor: str,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene tickets históricos de sensores del mismo tipo y capa que el evento.
        Ejecuta IABOT_ObtenerTicketsByAlerta con @ip y @sensor.

        Args:
            ip: IP del equipo alertado.
            sensor: Nombre del sensor (nombre_sensor en VW_CMDB_EquiposConPRTG).

        Returns:
            Lista de tickets con keys: Ticket, alerta, detalle, accionCorrectiva.
            Retorna [] si no hay historial (no lanza excepción).
        """
        db = DatabaseManager.get(_DB_ALIAS)
        sql = (
            "EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta "
            "@ip = :ip, @sensor = :sensor"
        )
        try:
            rows = db.execute_query(sql, {"ip": ip, "sensor": sensor})
            logger.info(
                f"get_historical_tickets → {len(rows)} ticket(s) "
                f"[ip={ip}, sensor={sensor}]"
            )
            return rows
        except Exception as e:
            logger.warning(f"No se pudo obtener historial de tickets [{ip}/{sensor}]: {e}")
            return []
