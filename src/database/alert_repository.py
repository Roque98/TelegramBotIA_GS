"""
Repositorio de alertas de monitoreo PRTG.
Todos los SPs se ejecutan contra BAZ_CDMX.
Si los SPs base no retornan resultados, se ejecutan los SPs _EKT
(que internamente acceden a la instancia EKT vía OPENDATASOURCE).
"""
import logging
from typing import List, Dict, Any

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)

_DB_ALIAS = "BAZ_CDMX"

# SPs de eventos: primero los de BAZ_CDMX, luego los _EKT como fallback
_SPS_EVENTOS = (
    "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidos",
    "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidosPerformance",
)
_SPS_EVENTOS_EKT = (
    "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidos_EKT",
    "EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidosPerformance_EKT",
)


class AlertRepository:
    """Acceso a datos de alertas PRTG e historial de tickets."""

    def get_active_events(
        self,
        ip: str = None,
        equipo: str = None,
        solo_down: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene eventos activos contra BAZ_CDMX.
        Si no hay resultados, reintenta con los SPs _EKT.

        Args:
            ip: Filtra por IP exacta del equipo.
            equipo: Filtra por nombre de equipo (búsqueda parcial).
            solo_down: Si True, retorna solo eventos con Status='Down'.

        Returns:
            Lista combinada de eventos como diccionarios.
        """
        db = DatabaseManager.get(_DB_ALIAS)

        for sps, origen in ((_SPS_EVENTOS, "BAZ_CDMX"), (_SPS_EVENTOS_EKT, "EKT")):
            rows = self._ejecutar_sps_eventos(db, sps)

            if ip:
                rows = [r for r in rows if r.get("IP") == ip]
            if equipo:
                rows = [r for r in rows if equipo.lower() in (r.get("Equipo") or "").lower()]
            if solo_down:
                rows = [r for r in rows if (r.get("Status") or "").lower() == "down"]

            if rows:
                logger.info(
                    f"get_active_events → {len(rows)} evento(s) [{origen}] "
                    f"[ip={ip}, equipo={equipo}, solo_down={solo_down}]"
                )
                return rows

            logger.info(f"get_active_events → sin resultados en {origen}, probando SPs EKT")

        return []

    def get_historical_tickets(
        self,
        ip: str,
        sensor: str,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene tickets históricos ejecutando IABOT_ObtenerTicketsByAlerta contra BAZ_CDMX.
        Si no hay resultados, reintenta con IABOT_ObtenerTicketsByAlerta_EKT.

        Args:
            ip: IP del equipo alertado.
            sensor: Nombre del sensor.

        Returns:
            Lista de tickets con keys: Ticket, alerta, detalle, accionCorrectiva.
            Retorna [] si no hay historial.
        """
        db = DatabaseManager.get(_DB_ALIAS)

        for sp, origen in (
            ("EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta", "BAZ_CDMX"),
            ("EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta_EKT", "EKT"),
        ):
            try:
                sql = f"{sp} @ip = :ip, @sensor = :sensor"
                rows = db.execute_query(sql, {"ip": ip, "sensor": sensor})
                if rows:
                    logger.info(
                        f"get_historical_tickets → {len(rows)} ticket(s) [{origen}] "
                        f"[ip={ip}, sensor={sensor}]"
                    )
                    return rows
                logger.info(f"get_historical_tickets → sin resultados en {origen}, probando SP EKT")
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp} [{ip}/{sensor}]: {e}")

        return []

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _ejecutar_sps_eventos(self, db, sps: tuple) -> List[Dict[str, Any]]:
        """Ejecuta una lista de SPs de eventos y combina los resultados."""
        rows = []
        for sp in sps:
            try:
                rows += db.execute_query(sp)
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp}: {e}")
        return rows
