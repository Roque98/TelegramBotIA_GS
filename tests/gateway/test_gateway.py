"""
Tests para el módulo gateway.

Cobertura:
- MessageGateway: Normalización de diferentes canales
- MainHandler: Orquestación de ReActAgent + Memory
- Factory functions: Construcción de componentes
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock telegram antes de importar handler
sys.modules["telegram"] = MagicMock()
sys.modules["telegram.ext"] = MagicMock()

from src.gateway.message_gateway import MessageGateway
from src.gateway.handler import MainHandler
from src.gateway.factory import (
    create_tool_registry,
    create_memory_service,
    HandlerManager,
)
from src.agents.base.events import ConversationEvent, UserContext
from src.agents.base.agent import AgentResponse
from src.agents.tools.registry import ToolRegistry


class TestMessageGateway:
    """Tests para MessageGateway."""

    @pytest.fixture
    def gateway(self):
        """Gateway de prueba."""
        return MessageGateway()

    def test_from_telegram_valid(self, gateway):
        """from_telegram debe crear evento desde update válido."""
        # Mock de Update de Telegram
        mock_update = MagicMock()
        mock_update.message.text = "Hola, ¿cómo estás?"
        mock_update.message.chat_id = 123456
        mock_update.effective_user.id = 789
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"

        event = gateway.from_telegram(mock_update)

        assert event.channel == "telegram"
        assert event.user_id == "789"
        assert event.text == "Hola, ¿cómo estás?"
        assert event.metadata["chat_id"] == 123456
        assert event.metadata["username"] == "testuser"

    def test_from_telegram_no_message(self, gateway):
        """from_telegram debe fallar si no hay mensaje."""
        mock_update = MagicMock()
        mock_update.message = None

        with pytest.raises(ValueError, match="does not contain a message"):
            gateway.from_telegram(mock_update)

    def test_from_telegram_no_text(self, gateway):
        """from_telegram debe fallar si no hay texto."""
        mock_update = MagicMock()
        mock_update.message.text = None

        with pytest.raises(ValueError, match="does not contain text"):
            gateway.from_telegram(mock_update)

    def test_from_telegram_no_user(self, gateway):
        """from_telegram debe fallar si no hay usuario."""
        mock_update = MagicMock()
        mock_update.message.text = "Test"
        mock_update.effective_user = None

        with pytest.raises(ValueError, match="does not have an effective user"):
            gateway.from_telegram(mock_update)

    def test_from_api(self, gateway):
        """from_api debe crear evento desde parámetros API."""
        event = gateway.from_api(
            user_id="user123",
            text="Consulta API",
            session_id="session456",
            metadata={"client": "web"},
        )

        assert event.channel == "api"
        assert event.user_id == "user123"
        assert event.text == "Consulta API"
        assert event.correlation_id == "session456"
        assert event.metadata["client"] == "web"

    def test_from_api_without_session(self, gateway):
        """from_api debe generar session_id si no se proporciona."""
        event = gateway.from_api(
            user_id="user123",
            text="Test",
        )

        assert event.correlation_id is not None
        assert len(event.correlation_id) > 0

    def test_from_websocket(self, gateway):
        """from_websocket debe crear evento desde conexión WS."""
        event = gateway.from_websocket(
            user_id="user123",
            text="WS message",
            connection_id="conn789",
            metadata={"protocol": "wss"},
        )

        assert event.channel == "websocket"
        assert event.user_id == "user123"
        assert event.correlation_id == "conn789"
        assert event.metadata["connection_id"] == "conn789"
        assert event.metadata["protocol"] == "wss"

    def test_extract_user_info(self, gateway):
        """extract_user_info debe extraer información del evento."""
        event = ConversationEvent(
            user_id="123",
            channel="telegram",
            text="Test",
            metadata={"username": "testuser"},
        )

        info = gateway.extract_user_info(event)

        assert info["user_id"] == "123"
        assert info["channel"] == "telegram"
        assert info["username"] == "testuser"
        assert "correlation_id" in info
        assert "timestamp" in info


class TestMainHandler:
    """Tests para MainHandler."""

    @pytest.fixture
    def mock_react_agent(self):
        """Mock del ReActAgent."""
        agent = AsyncMock()
        agent.name = "react"
        return agent

    @pytest.fixture
    def mock_memory_service(self):
        """Mock del MemoryService."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_fallback_agent(self):
        """Mock del agente de fallback."""
        agent = AsyncMock()
        return agent

    @pytest.fixture
    def handler(self, mock_react_agent, mock_memory_service, mock_fallback_agent):
        """MainHandler con mocks."""
        return MainHandler(
            react_agent=mock_react_agent,
            memory_service=mock_memory_service,
            fallback_agent=mock_fallback_agent,
            use_fallback_on_error=True,
        )

    @pytest.mark.asyncio
    async def test_handle_api_success(
        self, handler, mock_react_agent, mock_memory_service
    ):
        """handle_api debe procesar correctamente una solicitud."""
        # Setup
        mock_memory_service.get_context.return_value = UserContext.empty("123")
        mock_react_agent.execute.return_value = AgentResponse.success_response(
            agent_name="react",
            message="Respuesta exitosa",
        )
        mock_memory_service.record_interaction.return_value = True

        # Execute
        response = await handler.handle_api(
            user_id="123",
            text="¿Cuántas ventas hay?",
            session_id="session1",
        )

        # Verify
        assert response.success is True
        assert response.message == "Respuesta exitosa"
        mock_memory_service.get_context.assert_called_once_with("123")
        mock_react_agent.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_api_error_with_fallback(
        self, handler, mock_react_agent, mock_memory_service, mock_fallback_agent
    ):
        """handle_api debe usar fallback cuando ReAct falla."""
        # Setup
        mock_memory_service.get_context.return_value = UserContext.empty("123")
        mock_react_agent.execute.side_effect = Exception("ReAct error")
        mock_fallback_agent.process_query.return_value = "Respuesta fallback"

        # Execute
        response = await handler.handle_api(
            user_id="123",
            text="Test",
        )

        # Verify
        assert response.success is True
        assert response.message == "Respuesta fallback"
        assert response.metadata.get("used_fallback") is True

    @pytest.mark.asyncio
    async def test_handle_api_error_no_fallback(
        self, mock_react_agent, mock_memory_service
    ):
        """handle_api debe retornar error si no hay fallback."""
        handler = MainHandler(
            react_agent=mock_react_agent,
            memory_service=mock_memory_service,
            fallback_agent=None,
            use_fallback_on_error=False,
        )

        mock_memory_service.get_context.return_value = UserContext.empty("123")
        mock_react_agent.execute.side_effect = Exception("Error fatal")

        response = await handler.handle_api(user_id="123", text="Test")

        assert response.success is False
        assert "Error fatal" in response.error

    @pytest.mark.asyncio
    async def test_handle_telegram_success(
        self, handler, mock_react_agent, mock_memory_service
    ):
        """handle_telegram debe procesar update correctamente."""
        # Setup mock Telegram update
        mock_update = MagicMock()
        mock_update.message.text = "Hola"
        mock_update.message.chat_id = 123
        mock_update.effective_user.id = 456
        mock_update.effective_user.username = "test"
        mock_update.effective_user.first_name = "Test"

        mock_context = MagicMock()

        mock_memory_service.get_context.return_value = UserContext.empty("456")
        mock_react_agent.execute.return_value = AgentResponse.success_response(
            agent_name="react",
            message="¡Hola! ¿En qué puedo ayudarte?",
        )

        # Execute
        response = await handler.handle_telegram(mock_update, mock_context)

        # Verify
        assert response == "¡Hola! ¿En qué puedo ayudarte?"

    @pytest.mark.asyncio
    async def test_handle_telegram_error(
        self, handler, mock_react_agent, mock_memory_service, mock_fallback_agent
    ):
        """handle_telegram debe manejar errores gracefully."""
        mock_update = MagicMock()
        mock_update.message.text = "Test"
        mock_update.message.chat_id = 123
        mock_update.effective_user.id = 456
        mock_update.effective_user.username = None
        mock_update.effective_user.first_name = None

        mock_context = MagicMock()

        mock_memory_service.get_context.return_value = UserContext.empty("456")
        mock_react_agent.execute.side_effect = Exception("Error")
        mock_fallback_agent.process_query.side_effect = Exception("Fallback error")

        response = await handler.handle_telegram(mock_update, mock_context)

        # El mensaje de error contiene frases que indican fallo
        assert "lo siento" in response.lower() or "intenta" in response.lower()

    @pytest.mark.asyncio
    async def test_record_interaction_async(
        self, handler, mock_react_agent, mock_memory_service
    ):
        """record_interaction debe ejecutarse async sin bloquear."""
        import asyncio

        mock_memory_service.get_context.return_value = UserContext.empty("123")
        mock_react_agent.execute.return_value = AgentResponse.success_response(
            agent_name="react",
            message="OK",
        )

        # Hacer que record_interaction tarde un poco
        async def slow_record(*args, **kwargs):
            await asyncio.sleep(0.1)
            return True

        mock_memory_service.record_interaction = slow_record

        # Ejecutar y verificar que no bloquea
        response = await handler.handle_api(user_id="123", text="Test")

        assert response.success is True
        # La interacción se registra en background

    @pytest.mark.asyncio
    async def test_health_check(self, handler, mock_react_agent, mock_memory_service):
        """health_check debe verificar todos los componentes."""
        mock_memory_service.health_check.return_value = True
        mock_react_agent.health_check.return_value = True

        result = await handler.health_check()

        assert result["gateway"] is True
        assert result["memory"] is True
        assert result["react_agent"] is True
        assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, handler, mock_react_agent, mock_memory_service
    ):
        """health_check debe reportar fallos."""
        mock_memory_service.health_check.return_value = False
        mock_react_agent.health_check.return_value = True

        result = await handler.health_check()

        assert result["memory"] is False
        assert result["healthy"] is False


class TestFactory:
    """Tests para funciones factory."""

    @pytest.mark.skip(reason="Requires full dependencies (anthropic, etc.)")
    def test_create_tool_registry(self):
        """create_tool_registry debe crear registry con tools."""
        ToolRegistry.reset()

        registry = create_tool_registry(db_manager=None)

        tools = registry.list_tools()
        assert len(tools) == 4
        tool_names = [t.name for t in tools]
        assert "database_query" in tool_names
        assert "knowledge_search" in tool_names
        assert "calculate" in tool_names
        assert "datetime" in tool_names

    def test_create_memory_service(self):
        """create_memory_service debe crear servicio funcional."""
        service = create_memory_service(db_manager=None)

        assert service is not None
        assert service.cache_ttl_seconds == 300


class TestHandlerManager:
    """Tests para HandlerManager singleton."""

    def test_singleton_pattern(self):
        """HandlerManager debe ser singleton."""
        HandlerManager.reset()

        manager1 = HandlerManager()
        manager2 = HandlerManager()

        assert manager1 is manager2

    def test_is_initialized_false_before_init(self):
        """is_initialized debe ser False antes de inicializar."""
        HandlerManager.reset()
        manager = HandlerManager()

        assert manager.is_initialized() is False

    def test_handler_none_before_init(self):
        """handler debe ser None antes de inicializar."""
        HandlerManager.reset()
        manager = HandlerManager()

        assert manager.handler is None

    def test_reset(self):
        """reset debe limpiar el singleton."""
        manager = HandlerManager()
        # Simular inicialización
        manager._handler = MagicMock()

        HandlerManager.reset()

        manager2 = HandlerManager()
        assert manager2.handler is None
