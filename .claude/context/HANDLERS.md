# Handlers de Telegram

## Resumen

| Tipo | Cantidad |
|------|----------|
| CommandHandlers | 9 |
| MessageHandlers | 2 |
| ConversationHandlers | 1 |
| CallbackQueryHandlers | 0 |

---

## Comandos Registrados

### /start
- **Archivo**: `src/bot/handlers/command_handlers.py:72`
- **Función**: `start_command`
- **Descripción**: Genera mensaje de bienvenida dinámicamente desde BD con categorías y ejemplos filtrados por rol
- **Requiere auth**: No

### /help
- **Archivo**: `src/bot/handlers/command_handlers.py:132`
- **Función**: `help_command`
- **Descripción**: Genera guía dinámicamente desde BD mostrando categorías disponibles y ejemplos
- **Requiere auth**: No

### /stats
- **Archivo**: `src/bot/handlers/command_handlers.py:203`
- **Función**: `stats_command`
- **Descripción**: Muestra estadísticas de uso (placeholder)
- **Requiere auth**: Sí

### /cancel
- **Archivo**: `src/bot/handlers/command_handlers.py:234`
- **Función**: `cancel_command`
- **Descripción**: Cancela operación actual (útil en flujos conversacionales)
- **Requiere auth**: No

### /ia
- **Archivo**: `src/bot/handlers/tools_handlers.py:21`
- **Función**: `handle_ia_command`
- **Descripción**: Consulta inteligente via ToolOrchestrator → QueryTool → LLMAgent
- **Requiere auth**: Sí
- **Permisos**: `/ia`

### /query
- **Archivo**: `src/bot/handlers/tools_handlers.py:111`
- **Función**: `handle_query_command`
- **Descripción**: Alias de /ia, delega a handle_ia_command
- **Requiere auth**: Sí

### /register
- **Archivo**: `src/bot/handlers/registration_handlers.py:44`
- **Función**: `RegistrationHandlers.cmd_register`
- **Descripción**: Inicia proceso de registro solicitando número de empleado
- **Flujo**: ConversationHandler

### /verify
- **Archivo**: `src/bot/handlers/registration_handlers.py:176`
- **Función**: `RegistrationHandlers.cmd_verify`
- **Descripción**: Verifica cuenta con código enviado
- **Uso**: `/verify <código>`

### /resend
- **Archivo**: `src/bot/handlers/registration_handlers.py:235`
- **Función**: `RegistrationHandlers.cmd_resend`
- **Descripción**: Genera nuevo código de verificación

---

## Message Handlers

### QueryHandler
- **Archivo**: `src/bot/handlers/query_handlers.py:40`
- **Clase**: `QueryHandler`
- **Método**: `handle_text_message`
- **Filtro**: `filters.TEXT & ~filters.COMMAND`
- **Descripción**: Procesa mensajes de texto como consultas
- **Flujo**:
  1. Validar autenticación (UserManager)
  2. Validar permisos (PermissionChecker)
  3. Auto-seleccionar tool (ToolSelector)
  4. Ejecutar via ToolOrchestrator
  5. Fallback a LLMAgent.process_query()

### Registration Employee ID Handler
- **Archivo**: `src/bot/handlers/registration_handlers.py:88`
- **Función**: `handle_employee_id`
- **Contexto**: Parte del ConversationHandler de registro
- **Descripción**: Procesa número de empleado ingresado

---

## ConversationHandler: Registro

**Archivo**: `src/bot/handlers/registration_handlers.py:299`

```
Estados:
┌─────────────────────────────────────────┐
│          WAITING_FOR_EMPLOYEE_ID        │
└────────────────────┬────────────────────┘
                     │
    Usuario envía número de empleado
                     │
                     ▼
         ┌───────────────────────┐
         │  Validar en BD        │
         │  ¿Existe empleado?    │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ❌ No existe            ✅ Existe
    (retry)                 (ConversationHandler.END)
                                 │
                                 ▼
                     Enviar código verificación
```

**Entry points**: `CommandHandler('register', cmd_register)`
**Fallbacks**: `CommandHandler('cancel', cmd_cancel)`

---

## Clases de Handlers

### QueryHandler
```python
# src/bot/handlers/query_handlers.py:22
class QueryHandler:
    def __init__(self, agent: LLMAgent)

    async def handle_text_message(update, context)
    async def _send_response(update, response)
    async def _send_long_response(update, response)  # Split >4000 chars
    async def _send_error_message(update, error)
```

**Dependencias**:
- LLMAgent
- ToolSelector
- ToolOrchestrator
- UserManager
- PermissionChecker

### RegistrationHandlers
```python
# src/bot/handlers/registration_handlers.py:32
class RegistrationHandlers:
    def __init__(self, db_manager: DatabaseManager)

    async def cmd_register(update, context)
    async def handle_employee_id(update, context)
    async def cmd_verify(update, context)
    async def cmd_resend(update, context)
    async def cmd_cancel(update, context)
```

### UniversalHandler
```python
# src/bot/handlers/universal_handler.py:22
class UniversalHandler:
    def __init__(self)

    async def handle_command(update, context)
    async def handle_text_message(update, context)

    # Rate limiting: 10 req/min por usuario
    # Input validation incluida
```

---

## Funciones de Registro

```python
# En main.py se llaman estas funciones:

register_command_handlers(application)
# → /start, /help, /stats, /cancel

register_query_handlers(application, agent)
# → MessageHandler para texto

register_registration_handlers(application, db_manager)
# → ConversationHandler + /verify, /resend

register_tools_handlers(application)
# → /ia, /query
```

---

## Flujo de Autenticación

```
Mensaje de usuario
    │
    ▼
¿Usuario en context.user_data?
    │
    ├─ No → Consultar UserManager.is_registered()
    │           │
    │           ├─ No registrado → "Usa /register"
    │           └─ Registrado → Cachear en context
    │
    └─ Sí → Continuar
    │
    ▼
¿Usuario activo y verificado?
    │
    ├─ No → Mensaje de error apropiado
    └─ Sí → Verificar permisos para /ia
              │
              ├─ Sin permiso → "No tienes acceso"
              └─ Con permiso → Ejecutar consulta
```

---

## Dependencias por Handler

```
command_handlers.py
├── start_command → KnowledgeRepository, UserManager
├── help_command → KnowledgeRepository, UserManager
├── stats_command → (placeholder)
└── cancel_command → (ninguna)

query_handlers.py
└── QueryHandler
    ├── LLMAgent
    ├── ToolSelector
    ├── ToolOrchestrator
    ├── UserManager
    └── PermissionChecker

tools_handlers.py
├── handle_ia_command → ToolOrchestrator, ExecutionContextBuilder
└── handle_query_command → handle_ia_command

registration_handlers.py
└── RegistrationHandlers
    ├── UserManager
    ├── RegistrationManager
    └── DatabaseManager
```
