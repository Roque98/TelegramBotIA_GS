"""
Constructor del prompt enriquecido para análisis de alertas de monitoreo.
Combina los datos del evento activo con el historial de tickets similares.
"""
from typing import List, Dict, Any


class AlertPromptBuilder:
    """Construye el prompt que se envía al LLM para analizar una alerta."""

    def build(
        self,
        evento: Dict[str, Any],
        tickets: List[Dict[str, Any]],
        pregunta_usuario: str,
    ) -> str:
        """
        Construye el prompt completo con el evento actual y su historial.

        Args:
            evento: Diccionario con los campos del evento (salida de SP1).
            tickets: Lista de tickets históricos (salida de IABOT_ObtenerTicketsByAlerta).
            pregunta_usuario: Texto original del usuario.

        Returns:
            Prompt listo para enviar al LLM.
        """
        def val(key: str, default: str = "N/D") -> str:
            v = evento.get(key)
            return str(v).strip() if v is not None and str(v).strip() else default

        return "\n\n".join(filter(None, [
            self._seccion_alerta(val),
            self._seccion_tickets(tickets),
            self._seccion_instruccion(),
        ]))

    # ------------------------------------------------------------------
    # Secciones del prompt
    # ------------------------------------------------------------------

    def _seccion_alerta(self, val) -> str:
        # Información del equipo responsable
        area_at = val('AreaAtendedora')
        gerencia = val('Gerencia')
        responsable = val('ResponsableAtendedor')
        lineas_area = []
        if area_at != 'N/D':
            lineas_area.append(f"- Área atendedora: {area_at}")
        if gerencia != 'N/D':
            lineas_area.append(f"- Área administradora: {gerencia}")
        if responsable != 'N/D':
            lineas_area.append(f"- Responsable atendedor: {responsable}")
        info_equipo = ("Información del equipo:\n" + "\n".join(lineas_area)) if lineas_area else ""

        partes = [
            f"Tengo la siguiente alerta del equipo {val('Equipo')} "
            f"en el Sensor: {val('Sensor')} "
            f"con el detalle {val('Mensaje')}",
        ]
        if info_equipo:
            partes.append(info_equipo)
        partes.append(
            "Se ha buscado los tickets del nodo y nodos hermanos "
            "(misma infraestructura, misma capa)."
        )
        return "\n\n".join(partes)

    def _seccion_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        if not tickets:
            return "No se encontraron tickets previos para este nodo ni nodos hermanos."

        bloques = []
        for t in tickets:
            ticket_id = t.get("Ticket", "S/N")
            alerta = (t.get("alerta") or "").strip()
            detalle = (t.get("detalle") or "").strip()
            accion = (t.get("accionCorrectiva") or "").strip().replace("[Salto]", "\n")

            bloques.append(
                f"Ticket: {ticket_id}\n"
                f"Alerta: {alerta or 'N/D'}\n"
                f"Detalle: {detalle or 'N/D'}\n"
                f"Acción correctiva: {accion or 'Sin acción correctiva registrada'}"
            )

        return "\n\n---\n\n".join(bloques)

    def _seccion_instruccion(self) -> str:
        return (
            "Eres un asistente encargado de sugerir soluciones. "
            "Inicia tu respuesta describiendo brevemente el detalle de la alerta actual. "
            "Después, con base en la información otorgada, indícale al usuario posibles "
            "soluciones, indicando sobre qué ticket de la causa raíz usaste para determinar "
            "la solución. También puedes usar tu conocimiento para justificar tu respuesta."
        )
