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
        return (
            f"DATOS DEL EVENTO ACTIVO:\n"
            f"- Equipo: {val('Equipo')}\n"
            f"- IP: {val('IP')}\n"
            f"- Sensor: {val('Sensor')}\n"
            f"- Detalle: {val('Mensaje')}\n"
            f"- Área atendedora: {val('AreaAtendedora')}\n"
            f"- Responsable atendedor: {val('ResponsableAtendedor')}\n"
            f"- Área administradora: {val('AreaAdministradora')}\n"
            f"- Responsable administrador: {val('ResponsableAdministrador')}\n\n"
            "Se ha buscado los tickets del nodo y nodos hermanos "
            "(misma infraestructura, misma capa)."
        )

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
            "Eres un asistente de operaciones TI. Genera una respuesta en español con "
            "EXACTAMENTE estas secciones en este orden (Markdown para Telegram). "
            "No agregues secciones extra, no cambies el orden y no hagas preguntas al usuario.\n"
            "En la sección de acciones, indica entre paréntesis el ticket del que proviene cada acción "
            "cuando aplique (ej: '(basado en ticket #12345)'). Máximo 5 acciones. "
            "Usa `código` solo para comandos de terminal.\n\n"
            "🔴 *ALERTA: {Equipo} ({IP})*\n"
            "📡 *Sensor:* {Sensor} — {resumen breve del detalle}\n\n"
            "👥 *Área responsable en operaciones*\n"
            "*Atendedora:* {AreaAtendedora}\n"
            "👤 {ResponsableAtendedor}\n"
            "*Administradora:* {AreaAdministradora}\n"
            "👤 {ResponsableAdministrador}\n\n"
            "🛠 *Acciones recomendadas*\n"
            "1. {acción más urgente}\n"
            "2. {segunda acción}\n"
            "3. {tercera acción}\n\n"
            "🔍 *Posible causa raíz*\n"
            "{En base a los tickets históricos, describe en 1-2 oraciones la causa raíz más probable. "
            "Si no hay tickets, indica que se desconoce la causa raíz y menciona las causas comunes para este tipo de alerta.}\n\n"
            "📋 *Contexto histórico*\n"
            "{Una sola oración: ticket(s) usados como base, o indicar que no hay histórico y "
            "que las recomendaciones se basan en procedimiento estándar.}\n\n"
            "Completa las secciones anteriores con los datos del evento. "
            "Sé directo y conciso. No uses emojis fuera de los indicados."
        )
