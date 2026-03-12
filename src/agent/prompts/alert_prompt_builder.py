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
        return "\n\n".join(filter(None, [
            self._seccion_instruccion(),
            self._seccion_pregunta(pregunta_usuario),
            self._seccion_evento(evento),
            self._seccion_tickets(tickets),
            self._seccion_tarea(),
        ]))

    # ------------------------------------------------------------------
    # Secciones del prompt
    # ------------------------------------------------------------------

    def _seccion_instruccion(self) -> str:
        return (
            "Eres un experto en monitoreo de infraestructura TI. "
            "Analiza la siguiente alerta activa y el historial de incidentes similares "
            "para dar un diagnóstico y una acción correctiva concreta."
        )

    def _seccion_pregunta(self, pregunta: str) -> str:
        return f"## PREGUNTA DEL USUARIO\n{pregunta}"

    def _seccion_evento(self, evento: Dict[str, Any]) -> str:
        def val(key: str, default: str = "N/D") -> str:
            v = evento.get(key)
            return str(v).strip() if v is not None and str(v).strip() else default

        lineas = [
            "## ALERTA ACTIVA",
            f"- Equipo:             {val('Equipo')}",
            f"- IP:                 {val('IP')}",
            f"- Tipo de sensor:     {val('tipoSensor')}",
            f"- Status:             {val('Status')}",
            f"- Tiempo caído:       {val('downTime')}",
            f"- Mensaje del sensor: {val('Mensaje')}",
            f"- Negocio:            {val('negocio')}",
            f"- Sistema:            {val('Sistema')}",
            f"- Área atendedora:    {val('AreaAtendedora')}",
            f"- Responsable:        {val('ResponsableAtendedor')}",
            f"- Prioridad/Urgencia/Impacto: {val('Prioridad')}/{val('Urgencia')}/{val('Impacto')}",
        ]

        troubleshooting = val('Troubleshooting', "")
        if troubleshooting and troubleshooting != "N/D":
            lineas.append(f"- Troubleshooting sugerido: {troubleshooting}")

        return "\n".join(lineas)

    def _seccion_tickets(self, tickets: List[Dict[str, Any]]) -> str:
        if not tickets:
            return "## HISTORIAL DE INCIDENTES SIMILARES\nSin historial previo registrado."

        bloques = ["## HISTORIAL DE INCIDENTES SIMILARES"]
        for t in tickets:
            ticket_id = t.get("Ticket", "S/N")
            alerta = (t.get("alerta") or "").strip()
            detalle = (t.get("detalle") or "").strip()
            accion = (t.get("accionCorrectiva") or "").strip().replace("[Salto]", "\n")

            bloques.append(
                f"### Ticket {ticket_id}\n"
                f"Alerta:   {alerta or 'N/D'}\n"
                f"Detalle:  {detalle or 'N/D'}\n"
                f"Solución: {accion or 'Sin acción correctiva registrada'}"
            )

        return "\n\n".join(bloques)

    def _seccion_tarea(self) -> str:
        return (
            "## INSTRUCCIÓN\n"
            "Con base en la información anterior responde en texto plano y español:\n"
            "1. Diagnóstico probable (causa raíz más frecuente según historial)\n"
            "2. Acción correctiva recomendada (paso a paso si aplica)\n"
            "3. A quién contactar si persiste el problema"
        )
