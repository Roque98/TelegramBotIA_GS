"""
Constructor del prompt enriquecido para análisis de alertas de monitoreo.
Combina los datos del evento activo con el historial de tickets similares,
información del template y matriz de escalamiento.
"""
from typing import List, Dict, Any, Optional


class AlertPromptBuilder:
    """Construye el prompt que se envía al LLM para analizar una alerta."""

    def build(
        self,
        evento: Dict[str, Any],
        tickets: List[Dict[str, Any]],
        pregunta_usuario: str,
        template_info: Optional[Dict[str, Any]] = None,
        matriz: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Construye el prompt completo con el evento actual y su historial.

        Args:
            evento: Diccionario con los campos del evento (salida de SP1).
            tickets: Lista de tickets históricos.
            pregunta_usuario: Texto original del usuario.
            template_info: Datos del template (Aplicacion, GerenciaDesarrollo, etc.).
            matriz: Filas de la matriz de escalamiento.

        Returns:
            Prompt listo para enviar al LLM.
        """
        def val(key: str, default: str = "N/D") -> str:
            v = evento.get(key)
            return str(v).strip() if v is not None and str(v).strip() else default

        return "\n\n".join(filter(None, [
            self._seccion_alerta(val, template_info),
            self._seccion_tickets(tickets),
            self._seccion_template(template_info, matriz),
            self._seccion_instruccion(template_info, matriz),
        ]))

    # ------------------------------------------------------------------
    # Secciones del prompt
    # ------------------------------------------------------------------

    def _seccion_alerta(self, val, template_info: Optional[Dict[str, Any]]) -> str:
        nombre_template = ""
        if template_info:
            nombre = (template_info.get("Aplicacion") or "").strip()
            if nombre:
                nombre_template = f"- Nombre del template: {nombre}\n"

        return (
            f"DATOS DEL EVENTO ACTIVO:\n"
            f"{nombre_template}"
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

    def _seccion_template(
        self,
        template_info: Optional[Dict[str, Any]],
        matriz: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Agrega al prompt los datos del template y la matriz como contexto para el LLM."""
        if not template_info and not matriz:
            return ""

        partes = ["DATOS DEL TEMPLATE:"]

        if template_info:
            gerencia_dev = (template_info.get("GerenciaDesarrollo") or "").strip()
            if gerencia_dev:
                partes.append(f"- Gerencia de desarrollo: {gerencia_dev}")

        if matriz:
            partes.append("Matriz de escalamiento:")
            for fila in matriz:
                nivel = fila.get("nivel", "")
                nombre = (fila.get("Nombre") or "").strip()
                puesto = (fila.get("puesto") or "").strip()
                tiempo = fila.get("TiempoEscalacion", "")
                ext = (fila.get("Extension") or "").strip()
                cel = (fila.get("celular") or "").strip()
                correo = (fila.get("correo") or "").strip()

                contacto = " | ".join(filter(None, [
                    f"Ext: {ext}" if ext else "",
                    f"Cel: {cel}" if cel else "",
                    f"Email: {correo}" if correo else "",
                ]))
                partes.append(
                    f"  Nivel {nivel}: {nombre} ({puesto})"
                    + (f" — {contacto}" if contacto else "")
                    + (f" — Escalar en: {tiempo} min" if tiempo else "")
                )

        return "\n".join(partes)

    def _seccion_instruccion(
        self,
        template_info: Optional[Dict[str, Any]],
        matriz: Optional[List[Dict[str, Any]]],
    ) -> str:
        tiene_template = bool(template_info and (template_info.get("Aplicacion") or "").strip())
        tiene_dev = bool(template_info and (template_info.get("GerenciaDesarrollo") or "").strip())
        tiene_matriz = bool(matriz)

        seccion_titulo = (
            "📌 *{Aplicacion}*\n" if tiene_template else ""
        )
        seccion_dev = (
            "💻 *Área responsable desarrollo*\n"
            "{GerenciaDesarrollo}\n\n"
            if tiene_dev else ""
        )
        seccion_matriz = (
            "📞 *Matriz de escalamiento*\n"
            "• Nivel {nivel}: {Nombre} ({puesto}) — Ext: {Extension} | Cel: {celular} | Escalar en: {TiempoEscalacion} min\n"
            "_(incluye todos los niveles disponibles)_\n\n"
            if tiene_matriz else ""
        )

        return (
            "Eres un asistente de operaciones TI. Genera una respuesta en español con "
            "EXACTAMENTE estas secciones en este orden (Markdown para Telegram). "
            "No agregues secciones extra, no cambies el orden y no hagas preguntas al usuario.\n"
            "En la sección de acciones, indica entre paréntesis el ticket del que proviene cada acción "
            "cuando aplique (ej: '(basado en ticket #12345)'). Máximo 5 acciones. "
            "Usa `código` solo para comandos de terminal.\n\n"
            + seccion_titulo +
            "🔴 *ALERTA: {Equipo} ({IP})*\n"
            "📡 *Sensor:* {Sensor} — {resumen breve del detalle}\n\n"
            "👥 *Área responsable en operaciones*\n"
            "*Atendedora:* {AreaAtendedora}\n"
            "👤 {ResponsableAtendedor}\n"
            "*Administradora:* {AreaAdministradora}\n"
            "👤 {ResponsableAdministrador}\n\n"
            + seccion_dev +
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
            + seccion_matriz +
            "Completa las secciones anteriores con los datos del evento. "
            "Sé directo y conciso. No uses emojis fuera de los indicados."
        )
