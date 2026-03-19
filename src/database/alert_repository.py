"""
Repositorio de alertas de monitoreo PRTG.
Todos los SPs se ejecutan contra BAZ_CDMX.
Si los SPs base no retornan resultados, se ejecutan los SPs _EKT
(que internamente acceden a la instancia EKT vía OPENDATASOURCE).
"""
import logging
from typing import List, Dict, Any, Optional

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

        for sps, origen, autocommit in (
            (_SPS_EVENTOS, "BAZ_CDMX", False),
            (_SPS_EVENTOS_EKT, "EKT", True),
        ):
            rows = self._ejecutar_sps_eventos(db, sps, autocommit=autocommit)

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
                for row in rows:
                    row["_origen"] = origen
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

        for sp, origen, autocommit in (
            ("EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta", "BAZ_CDMX", False),
            ("EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta_EKT", "EKT", True),
        ):
            try:
                sql = f"{sp} @ip = :ip, @sensor = :sensor"
                rows = db.execute_query(sql, {"ip": ip, "sensor": sensor}, autocommit=autocommit)
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

    def get_contacto_gerencia(self, id_gerencia: int, usar_ekt: bool = False) -> Optional[Dict[str, Any]]:
        """
        Obtiene el contacto (correo y extensiones) de una gerencia.
        Si usar_ekt=True usa Contacto_GetByIdGerencia_EKT (para alertas de instancia EKT).

        Returns:
            Diccionario con Gerencia, direccion_correo, extensiones, o None.
        """
        if not id_gerencia:
            return None
        sp = (
            "EXEC ABCMASplus.dbo.Contacto_GetByIdGerencia_EKT @idGerencia = :id"
            if usar_ekt else
            "EXEC ABCMASplus..Contacto_GetByIdGerencia @idGerencia = :id"
        )
        origen = "EKT" if usar_ekt else "BAZ_CDMX"
        db = DatabaseManager.get(_DB_ALIAS)
        try:
            rows = db.execute_query(sp, {"id": id_gerencia}, autocommit=usar_ekt)
            if rows:
                logger.info(f"get_contacto_gerencia → idGerencia={id_gerencia} [{origen}]")
                return rows[0]
            logger.warning(f"get_contacto_gerencia → sin resultados [idGerencia={id_gerencia}, origen={origen}]")
        except Exception as e:
            logger.warning(f"No se pudo obtener contacto [idGerencia={id_gerencia}, origen={origen}]: {e}")
        return None

    def get_template_id(self, ip: str, url: str = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene el ID de template asociado al evento.
        Si hay URL busca por URL, sino busca por IP.

        Returns:
            Diccionario con idTemplate e instancia, o None si no se encuentra.
        """
        db = DatabaseManager.get(_DB_ALIAS)

        if url:
            sql = "EXEC ABCMASplus.dbo.IDTemplateByUrl @url = :url"
            params = {"url": url}
        else:
            sql = "EXEC ABCMASplus.dbo.IDTemplateByIp @ip = :ip"
            params = {"ip": ip}

        try:
            rows = db.execute_query(sql, params, autocommit=True)
            if rows:
                row = rows[0]
                # IDTemplateByIp no tiene alias en la columna instancia → puede llegar
                # como clave vacía '' o None; normalizamos a 'instancia'
                if "instancia" not in row:
                    sin_nombre = row.get("") or row.get(None) or ""
                    row = {"idTemplate": row.get("idTemplate"), "instancia": str(sin_nombre).strip()}
                logger.info(
                    f"get_template_id → idTemplate={row.get('idTemplate')} "
                    f"instancia={row.get('instancia')} [ip={ip}, url={url}]"
                )
                return row
            logger.warning(f"get_template_id → sin resultados [ip={ip}, url={url}]")
        except Exception as e:
            logger.warning(f"No se pudo obtener template id [ip={ip}, url={url}]: {e}")

        return None

    def get_template_info(self, template_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información del template (nombre, gerencias).
        Intenta primero con Template_GetById, luego con la versión _EKT.

        Returns:
            Diccionario con los datos del template, o None si no se encuentra.
        """
        db = DatabaseManager.get(_DB_ALIAS)

        for sp, origen, autocommit in (
            ("EXEC ABCMASplus.dbo.Template_GetById", "BAZ_CDMX", False),
            ("EXEC ABCMASplus.dbo.Template_GetById_EKT", "EKT", True),
        ):
            try:
                rows = db.execute_query(f"{sp} @id = :id", {"id": template_id}, autocommit=autocommit)
                if rows:
                    logger.info(f"get_template_info → template {template_id} encontrado [{origen}]")
                    return rows[0]
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp} [id={template_id}]: {e}")

        return None

    def get_escalation_matrix(self, template_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene la matriz de escalamiento del template.
        Intenta primero con ObtenerMatriz, luego con la versión _EKT.

        Returns:
            Lista de filas de la matriz ordenadas por nivel.
        """
        db = DatabaseManager.get(_DB_ALIAS)

        for sp, origen, autocommit in (
            ("EXEC ABCMASplus.dbo.ObtenerMatriz", "BAZ_CDMX", False),
            ("EXEC ABCMASplus.dbo.ObtenerMatriz_EKT", "EKT", True),
        ):
            try:
                rows = db.execute_query(f"{sp} @idTemplate = :id", {"id": template_id}, autocommit=autocommit)
                if rows:
                    logger.info(f"get_escalation_matrix → {len(rows)} nivel(es) [{origen}] [template={template_id}]")
                    return rows
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp} [template={template_id}]: {e}")

        return []

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _ejecutar_sps_eventos(self, db, sps: tuple, autocommit: bool = False) -> List[Dict[str, Any]]:
        """Ejecuta una lista de SPs de eventos y combina los resultados."""
        rows = []
        for sp in sps:
            try:
                rows += db.execute_query(sp, autocommit=autocommit)
            except Exception as e:
                logger.warning(f"No se pudo ejecutar {sp}: {e}")
        return rows
