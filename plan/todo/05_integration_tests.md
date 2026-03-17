# TODO: Pruebas de integración — AlertAnalysisTool

## Objetivo
Verificar que el flujo completo funciona end-to-end antes de considerar la
feature como lista para producción.

---

## Pruebas de base de datos

### test_multi_db_config.py
```python
def test_default_db_conecta():
    db = DatabaseManager.get()
    assert db.health_check() is True

def test_monitoreos_db_conecta():
    db = DatabaseManager.get("monitoreos")
    assert db.health_check() is True

def test_alias_desconocido_lanza_error():
    with pytest.raises(ValueError, match="Alias de BD desconocido"):
        DatabaseManager.get("inventado")
```

### test_alert_repository.py
```python
async def test_get_active_events_sin_filtro():
    repo = AlertRepository()
    eventos = await repo.get_active_events()
    assert isinstance(eventos, list)
    # Puede estar vacío si no hay alertas activas — no es error

async def test_get_active_events_por_ip():
    repo = AlertRepository()
    eventos = await repo.get_active_events(ip="10.80.191.22")
    for e in eventos:
        assert e["IP"] == "10.80.191.22"

async def test_get_historical_tickets_id_valido():
    repo = AlertRepository()
    tickets = await repo.get_historical_tickets("BAZMV10199PRTGD15494S15495", limit=3)
    assert isinstance(tickets, list)
    for t in tickets:
        assert "Ticket" in t
        assert "accionCorrectiva" in t

async def test_get_historical_tickets_id_invalido():
    repo = AlertRepository()
    tickets = await repo.get_historical_tickets("ID_QUE_NO_EXISTE")
    assert tickets == []   # no lanza excepción
```

---

## Prueba del prompt builder

```python
def test_prompt_con_tickets():
    builder = AlertPromptBuilder()
    evento = {
        "Equipo": "WSTransferenciasSecure 10.80.191.22",
        "IP": "10.80.191.22",
        "tipoSensor": "HTTP Advanced",
        "Status": "Down",
        "downTime": "1 h 1 m",
        "Mensaje": "Connection refused",
        "negocio": "Switch Comercial",
        "AreaAtendedora": "Operaciones Middleware",
        "ResponsableAtendedor": "OMAR SANCHEZ",
        "Prioridad": 5, "Urgencia": 4, "Impacto": 5,
        "Troubleshooting": "Reportar al área atendedora"
    }
    tickets = [
        {"Ticket": "5041257", "alerta": "Discos 29%",
         "detalle": "Free Space below 30%", "accionCorrectiva": "Se comprimen logs"}
    ]
    prompt = builder.build(evento, tickets, "qué pasa con 10.80.191.22?")
    assert "10.80.191.22" in prompt
    assert "5041257" in prompt
    assert len(prompt) < 12000  # ~3000 tokens aprox

def test_prompt_sin_tickets():
    builder = AlertPromptBuilder()
    # ... mismo evento, tickets=[]
    prompt = builder.build(evento, [], "analiza alertas")
    assert "Sin historial" in prompt
```

---

## Prueba manual del tool (script)

```python
# tests/test_alert_tool_manual.py
# Ejecutar: python -m pytest tests/test_alert_tool_manual.py -v -s
async def test_tool_end_to_end():
    tool = AlertAnalysisTool()
    context = build_test_context()   # helper existente en tests/

    result = await tool.execute(
        user_id=1,
        params={"query": "analiza las alertas actuales"},
        context=context
    )
    assert result.success is True
    print("\n--- RESPUESTA DEL LLM ---")
    print(result.data)
```

---

## Criterios de aceptación
- [ ] Todas las pruebas de BD pasan contra el entorno real
- [ ] El prompt builder produce salida válida en todos los casos borde
- [ ] El tool end-to-end retorna una respuesta coherente del LLM
- [ ] El `ToolSelector` elige `alert_analysis` para al menos 5 frases de prueba distintas

## Archivos a crear
- `tests/test_multi_db_config.py`
- `tests/test_alert_repository.py`
- `tests/test_alert_prompt_builder.py`
- `tests/test_alert_tool_manual.py`
