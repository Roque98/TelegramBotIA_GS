"""
Constructor del prompt enriquecido para análisis de alertas de monitoreo.
Combina los datos del evento activo con el historial de tickets similares,
información del template y matriz de escalamiento.
"""
from typing import List, Dict, Any, Optional

_ETIQUETA_INSTANCIA = {
    "BAZ": "ABCMASplus",
    "COMERCIO": "ABCEKT",
}


class AlertPromptBuilder:
    """Construye el prompt que se envía al LLM para analizar una alerta."""

    def build(
        self,
        evento: Dict[str, Any],
        tickets: List[Dict[str, Any]],
        pregunta_usuario: str,
        template_info: Optional[Dict[str, Any]] = None,
        matriz: Optional[List[Dict[str, Any]]] = None,
        template_id: Optional[int] = None,
        instancia: str = "",
        contacto_atendedora: Optional[Dict[str, Any]] = None,
        contacto_administradora: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Construye el prompt completo con el evento actual y su historial.

        Args:
            evento: Diccionario con los campos del evento (salida de SP1).
            tickets: Lista de tickets históricos.
            pregunta_usuario: Texto original del usuario.
            template_info: Datos del template (Aplicacion, GerenciaDesarrollo, etc.).
            matriz: Filas de la matriz de escalamiento.
            template_id: ID numérico del template.
            instancia: 'BAZ' o 'COMERCIO', indica el origen del template.
            contacto_atendedora: Contacto del área atendedora (correo y extensiones).
            contacto_administradora: Contacto del área administradora (correo y extensiones).

        Returns:
            Prompt listo para enviar al LLM.
        """
        def val(key: str, default: str = "N/D") -> str:
            v = evento.get(key)
            return str(v).strip() if v is not None and str(v).strip() else default

        matriz_ordenada = sorted(matriz or [], key=lambda r: int(r.get("nivel") or 0))

        return "\n\n".join(filter(None, [
            self._seccion_alerta(val, template_info, template_id, instancia),
            self._seccion_tickets(tickets),
            self._seccion_template(template_info, matriz_ordenada),
            self._seccion_instruccion(
                template_info, matriz_ordenada, template_id, instancia,
                contacto_atendedora, contacto_administradora,
            ),
        ]))

    # ------------------------------------------------------------------
    # Secciones del prompt
    # ------------------------------------------------------------------

    def _seccion_alerta(self, val, template_info, template_id, instancia) -> str:
        nombre_template = ""
        if template_info:
            nombre = (template_info.get("Aplicacion") or "").strip()
            if nombre:
                etiqueta = _ETIQUETA_INSTANCIA.get(instancia.upper(), instancia)
                id_str = f" #{template_id}" if template_id else ""
                nombre_template = f"- Template:{id_str} {nombre} [{etiqueta}]\n"

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

    def _seccion_template(self, template_info, matriz_ordenada) -> str:
        """Agrega al prompt los datos del template y la matriz como contexto para el LLM."""
        if not template_info and not matriz_ordenada:
            return ""

        partes = ["DATOS DEL TEMPLATE:"]

        if template_info:
            gerencia_dev = (template_info.get("GerenciaDesarrollo") or "").strip()
            if gerencia_dev:
                partes.append(f"- Gerencia de desarrollo: {gerencia_dev}")

        if matriz_ordenada:
            partes.append("Matriz de escalamiento (de mayor a menor nivel):")
            for fila in matriz_ordenada:
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

    def _fmt_contacto(self, contacto: Optional[Dict[str, Any]]) -> str:
        """Formatea el contacto de un área como líneas de correo y extensiones."""
        if not contacto:
            return ""
        correo = (contacto.get("direccion_correo") or "").strip()
        exts = (contacto.get("extensiones") or "").strip()
        partes = []
        if correo:
            partes.append(f"📧 {correo}")
        if exts:
            partes.append(f"☎️ Ext: {exts}")
        return "\n".join(partes)

    def _seccion_instruccion(
        self, template_info, matriz_ordenada, template_id, instancia,
        contacto_atendedora=None, contacto_administradora=None,
    ) -> str:
        tiene_template = bool(template_info and (template_info.get("Aplicacion") or "").strip())
        tiene_dev = bool(template_info and (template_info.get("GerenciaDesarrollo") or "").strip())
        tiene_matriz = bool(matriz_ordenada)

        if tiene_template:
            etiqueta = _ETIQUETA_INSTANCIA.get(instancia.upper(), instancia)
            id_str = f" #{template_id}" if template_id else ""
            seccion_titulo = f"📌 *{{Aplicacion}}{id_str}* | {etiqueta}\n"
        else:
            seccion_titulo = ""

        seccion_dev = (
            "💻 *Área responsable desarrollo*\n"
            "{GerenciaDesarrollo}\n\n"
            if tiene_dev else ""
        )

        if tiene_matriz:
            filas_matriz = ""
            for fila in matriz_ordenada:
                nivel = fila.get("nivel", "")
                nombre = (fila.get("Nombre") or "").strip()
                puesto = (fila.get("puesto") or "").strip()
                ext = (fila.get("Extension") or "").strip()
                cel = (fila.get("celular") or "").strip()
                tiempo = fila.get("TiempoEscalacion", "")

                contacto = " | ".join(filter(None, [
                    f"Ext: {ext}" if ext else "",
                    f"Cel: {cel}" if cel else "",
                    f"⏱ {tiempo} min" if tiempo else "",
                ]))
                filas_matriz += (
                    f"*Nivel {nivel}* — {nombre}\n"
                    f"{puesto}" + (f" | {contacto}" if contacto else "") + "\n\n"
                )
            seccion_matriz = f"📞 *Matriz de escalamiento*\n{filas_matriz}"
        else:
            seccion_matriz = ""

        return (
            "Eres un asistente de operaciones TI. Genera una respuesta en español con "
            "EXACTAMENTE estas secciones en este orden (Markdown para Telegram). "
            "No agregues secciones extra, no cambies el orden y no hagas preguntas al usuario.\n"
            "En la sección de acciones, indica entre paréntesis el ticket del que proviene cada acción "
            "cuando aplique (ej: '(basado en ticket #12345)'). Máximo 5 acciones. "
            "Usa `código` solo para comandos de terminal.\n\n"
            + seccion_titulo
            + "🔴 *ALERTA: {Equipo} ({IP})*\n"
            "📡 *Sensor:* {Sensor} — {resumen breve del detalle}\n\n"
            "👥 *Área responsable en operaciones*\n"
            "*Atendedora:* {AreaAtendedora}\n"
            "👤 {ResponsableAtendedor}\n"
            + (self._fmt_contacto(contacto_atendedora) + "\n" if contacto_atendedora else "")
            + "*Administradora:* {AreaAdministradora}\n"
            "👤 {ResponsableAdministrador}\n"
            + (self._fmt_contacto(contacto_administradora) + "\n" if contacto_administradora else "")
            + "\n"
            + seccion_dev
            + seccion_matriz
            + "🛠 *Acciones recomendadas*\n"
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
