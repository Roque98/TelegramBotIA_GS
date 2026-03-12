# TODO: AlertRepository — Acceso a datos de alertas

## Objetivo
Repositorio dedicado que ejecuta ambos SPs contra la BD `Monitoreos`
usando el alias `BAZ_CDMX` del `db_connections.json`.

---

## Alias y BD

| SP | Alias | BD | Servidor |
|---|---|---|---|
| `PrtgObtenerEventosEnriquecidos` | `BAZ_CDMX` | `Monitoreos` | IP del JSON |
| `IABOT_ObtenerTicketsByAlerta` | `BAZ_CDMX` | `Monitoreos` | IP del JSON |

```python
db = DatabaseManager.get("BAZ_CDMX")
```

---

## SP a crear en BD Monitoreos: `IABOT_ObtenerTicketsByAlerta`

```sql
CREATE PROCEDURE Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta
    @ip     varchar(300),
    @sensor varchar(300)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP 15
        T.Ticket,
        TDA.alerta,
        TDA.detalle,
        ISNULL(AC.accionCorrectiva, 'CAUSA RAÍZ:[Salto][Salto]ACCIÓN CORRECTIVA: [Salto]')
            AS accionCorrectiva
    FROM
        ConsolaMonitoreo..Tickets AS T
        LEFT JOIN ConsolaMonitoreo..Tickets_DescAlertas AS TDA
            ON T.IdPeticion = TDA.idpeticion
        OUTER APPLY (
            SELECT TOP 1 comentario AS accionCorrectiva
            FROM ConsolaMonitoreo..Tickets_CambiosStatus
            WHERE ticket = T.Ticket
              AND status = 8
              AND comentario NOT LIKE 'Ticket mandado%'
            ORDER BY fecha DESC
        ) AS AC
    WHERE TDA.idConSensor IN (
        SELECT v.idConSensor
        FROM [ABCMASplus]..[VW_CMDB_EquiposConPRTG] v
        INNER JOIN ABCMASplus..Templates_Equipos te
            ON v.ip = te.Ip
        INNER JOIN ABCMASplus..Templates_Equipos_Templates tet
            ON te.ID = tet.idEquipo
        CROSS JOIN (
            SELECT TOP 1 tet_ref.idTemplate, te_ref.Capa
            FROM ABCMASplus..Templates_Equipos te_ref
            INNER JOIN ABCMASplus..Templates_Equipos_Templates tet_ref
                ON te_ref.ID = tet_ref.idEquipo
            WHERE te_ref.Ip = @ip
        ) ref
        WHERE tet.idTemplate = ref.idTemplate
          AND te.Capa        = ref.Capa
          AND v.nombre_sensor = @sensor
    )
    AND TRY_CAST(T.IdAlerta AS NUMERIC) IS NOT NULL
    ORDER BY fechagenerado DESC;
END
GO
```

> Este SP vive en `Monitoreos` pero referencia `ConsolaMonitoreo` y `ABCMASplus`
> como linked servers — no requieren conexiones adicionales desde el bot.

---

## Archivo a crear: `src/database/alert_repository.py`

### Método 1 — Obtener eventos activos

```python
async def get_active_events(
    self,
    ip: str | None = None,
    equipo: str | None = None,
    solo_down: bool = False
) -> list[dict]:
    """
    Ejecuta PrtgObtenerEventosEnriquecidos via BAZ_CDMX.
    Filtra en Python por ip, equipo o solo alertas Down.
    """
    db = DatabaseManager.get("BAZ_CDMX")
    rows = await db.execute_query("EXEC Monitoreos.dbo.PrtgObtenerEventosEnriquecidos")

    if ip:
        rows = [r for r in rows if r.get("IP") == ip]
    if equipo:
        rows = [r for r in rows if equipo.lower() in r.get("Equipo", "").lower()]
    if solo_down:
        rows = [r for r in rows if r.get("Status", "").lower() == "down"]

    return rows
```

Campos relevantes que se preservan del resultado:
```
ID, Equipo, IP, Sensor, Status, Mensaje, downTime,
idConSensor, Gerencia, AreaAtendedora, ResponsableAtendedor,
Prioridad, Urgencia, Impacto, tipoSensor, Troubleshooting,
ticket, StatusTicket, negocio, Sistema
```

---

### Método 2 — Obtener tickets históricos

```python
async def get_historical_tickets(
    self,
    ip: str,
    sensor: str
) -> list[dict]:
    """
    Ejecuta IABOT_ObtenerTicketsByAlerta via BAZ_CDMX.
    Retorna lista de tickets históricos para la misma IP y tipo de sensor.
    Retorna [] si no hay historial (no lanza excepción).
    """
    db = DatabaseManager.get("BAZ_CDMX")
    sql = "EXEC Monitoreos.dbo.IABOT_ObtenerTicketsByAlerta @ip=:ip, @sensor=:sensor"
    try:
        return await db.execute_query(sql, {"ip": ip, "sensor": sensor})
    except Exception:
        return []
```

---

### Uso desde AlertAnalysisTool

```python
repo = AlertRepository()

# 1. Obtener evento(s) activos
eventos = await repo.get_active_events(ip="10.80.191.22")

# 2. Para cada evento, obtener historial usando IP y nombre del sensor
for evento in eventos:
    tickets = await repo.get_historical_tickets(
        ip=evento["IP"],
        sensor=evento["Sensor"]   # nombre_sensor en VW_CMDB
    )
```

---

## Criterios de aceptación
- [ ] `get_active_events()` retorna todos los eventos sin filtro
- [ ] `get_active_events(ip="10.80.191.22")` filtra correctamente por IP
- [ ] `get_active_events(solo_down=True)` solo retorna Status='Down'
- [ ] `get_historical_tickets(ip, sensor)` retorna tickets ordenados por fecha desc
- [ ] `get_historical_tickets` retorna `[]` si no hay tickets (no lanza error)
- [ ] Ambos métodos usan `DatabaseManager.get("BAZ_CDMX")`

## Archivos a crear
- `src/database/alert_repository.py`

## Prerequisito
- SP `IABOT_ObtenerTicketsByAlerta` creado en `Monitoreos.dbo` en el servidor BAZ_CDMX
- Alias `BAZ_CDMX` configurado en `db_connections.json`
