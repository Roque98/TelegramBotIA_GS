"""
Repositorio de alertas de monitoreo PRTG.
Ejecuta los SPs de eventos e historial de tickets contra BAZ_CDMX.
Si no hay resultados en BAZ_CDMX, reintenta contra COMERCIO_KIO.
"""
import logging
from typing import List, Dict, Any

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

# Instancias consultadas en orden de prioridad
_DB_ALIASES = ("BAZ_CDMX", "COMERCIO_KIO")


class AlertRepository:
    """Acceso a datos de alertas PRTG e historial de tickets."""

    def get_active_events(
        self,
        ip: str = None,
        equipo: str = None,
        solo_down: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene eventos activos combinando ambos SPs de monitoreo:
          - PrtgObtenerEventosEnriquecidos
          - PrtgObtenerEventosEnriquecidosPerformance

        Consulta primero BAZ_CDMX; si no hay resultados, consulta COMERCIO_KIO.

        Args:
            ip: Filtra por IP exacta del equipo.
            equipo: Filtra por nombre de equipo (búsqueda parcial).
            solo_down: Si True, retorna solo eventos con Status='Down'.

        Returns:
            Lista combinada de eventos como diccionarios.
        """
        for alias in _DB_ALIASES:
            rows = self._query_active_events(alias)

            if ip:
                rows = [r for r in rows if r.get("IP") == ip]
            if equipo:
                rows = [r for r in rows if equipo.lower() in (r.get("Equipo") or "").lower()]
            if solo_down:
                rows = [r for r in rows if (r.get("Status") or "").lower() == "down"]

            if rows:
                logger.info(
                    f"get_active_events → {len(rows)} evento(s) en {alias} "
                    f"[ip={ip}, equipo={equipo}, solo_down={solo_down}]"
                )
                return rows

            logger.info(f"get_active_events → sin resultados en {alias}, probando siguiente instancia")

        return []

    def get_historical_tickets(
        self,
        ip: str,
        sensor: str,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene tickets históricos de sensores del mismo tipo y capa que el evento.
        Ejecuta IABOT_ObtenerTicketsByAlerta con @ip y @sensor.

        Consulta primero BAZ_CDMX; si no hay resultados, consulta COMERCIO_KIO.

        Args:
            ip: IP del equipo alertado.
            sensor: Nombre del sensor (nombre_sensor en VW_CMDB_EquiposConPRTG).

        Returns:
            Lista de tickets con keys: Ticket, alerta, detalle, accionCorrectiva.
            Retorna [] si no hay historial (no lanza excepción).
        """
        sql = (
            "EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta "
            "@ip = :ip, @sensor = :sensor"
        )
        for alias in _DB_ALIASES:
            try:
                db = DatabaseManager.get(alias)
                rows = db.execute_query(sql, {"ip": ip, "sensor": sensor})
                if rows:
                    logger.info(
                        f"get_historical_tickets → {len(rows)} ticket(s) en {alias} "
                        f"[ip={ip}, sensor={sensor}]"
                    )
                    return rows
                logger.info(f"get_historical_tickets → sin resultados en {alias}, probando siguiente instancia")
            except Exception as e:
                logger.warning(f"No se pudo obtener historial de tickets en {alias} [{ip}/{sensor}]: {e}")

        return []

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _query_active_events(self, alias: str) -> List[Dict[str, Any]]:
        """Ejecuta los dos SPs de eventos en la instancia indicada."""
        db = DatabaseManager.get(alias)
        rows = []
        for sp in (
            "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidos",
            "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidosPerformance",
        ):
            try:
                rows += db.execute_query(sp)
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp} en {alias}: {e}")
        return rows
