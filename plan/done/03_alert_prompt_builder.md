# TODO: AlertPromptBuilder — Construcción del prompt enriquecido

## Objetivo
Construir el prompt que se envía al LLM combinando el evento actual y el
historial de tickets, de forma clara y estructurada para obtener un
diagnóstico accionable.

---

## Archivo a crear: `src/agent/prompts/alert_prompt_builder.py`

### Firma

```python
class AlertPromptBuilder:
    def build(
        self,
        evento: dict,
        tickets: list[dict],
        pregunta_usuario: str
    ) -> str:
        """
        Retorna el prompt completo listo para enviar al LLM.
        """
```

### Estructura del prompt generado

```
Eres un experto en monitoreo de infraestructura TI. Analiza la siguiente
alerta activa y el historial de incidentes similares para dar un diagnóstico
y una acción correctiva concreta.

## PREGUNTA DEL USUARIO
{pregunta_usuario}

## ALERTA ACTIVA
- Equipo:            {Equipo}
- IP:                {IP}
- Tipo de sensor:    {tipoSensor}
- Status:            {Status}
- Tiempo caído:      {downTime}
- Mensaje del sensor: {Mensaje}
- Negocio:           {negocio}
- Sistema:           {Sistema}
- Área atendedora:   {AreaAtendedora}
- Responsable:       {ResponsableAtendedor}
- Prioridad/Urgencia/Impacto: {Prioridad}/{Urgencia}/{Impacto}
- Troubleshooting sugerido: {Troubleshooting}

## HISTORIAL DE TICKETS EN SENSORES SIMILARES
{bloque de tickets o "Sin historial previo registrado."}

## INSTRUCCIÓN
Con base en la información anterior:
1. Diagnóstico probable (causa raíz más frecuente según historial)
2. Acción correctiva recomendada (paso a paso si aplica)
3. A quién contactar si persiste el problema
4. Nivel de urgencia sugerido

Responde en español, de forma concisa y directa.
```

### Bloque de tickets (por cada ticket)

```
### Ticket {Ticket}
Alerta:   {alerta}
Detalle:  {detalle}
Solución: {accionCorrectiva}
```

### Casos especiales
- Sin tickets históricos → indicar "Sin historial previo" y basar análisis solo en datos del evento
- Sin troubleshooting en el evento → omitir esa sección
- Múltiples eventos (cuando el usuario no especificó IP) → generar un bloque por evento, limitado a los 3 más críticos

---

## Criterios de aceptación
- [ ] El prompt incluye todos los campos clave del evento
- [ ] El bloque de tickets se omite limpiamente si la lista está vacía
- [ ] El prompt no supera ~3000 tokens (verificar con tiktoken o estimación)
- [ ] Funciona con 1 evento o con lista de eventos (top N críticos)

## Archivos a crear
- `src/agent/prompts/alert_prompt_builder.py`
