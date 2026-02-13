"""
Tests para el ReAct Agent.

Cobertura:
- ActionType: Conversión y validación
- ReActStep: Creación y formateo
- ReActResponse: Factory methods
- Scratchpad: Gestión de pasos
- ReActAgent: Loop completo con mock LLM
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.react.schemas import ActionType, ReActStep, ReActResponse
from src.agents.react.scratchpad import Scratchpad
from src.agents.react.agent import ReActAgent
from src.agents.react.prompts import (
    build_system_prompt,
    build_user_prompt,
    build_continue_prompt,
)
from src.agents.base.events import UserContext
from src.agents.tools.registry import ToolRegistry
from src.agents.tools.base import BaseTool, ToolDefinition, ToolResult, ToolCategory


class TestActionType:
    """Tests para ActionType."""

    def test_from_string_valid(self):
        """Convertir string válido a ActionType."""
        assert ActionType.from_string("database_query") == ActionType.DATABASE_QUERY
        assert ActionType.from_string("finish") == ActionType.FINISH

    def test_from_string_aliases(self):
        """Convertir aliases a ActionType."""
        assert ActionType.from_string("db") == ActionType.DATABASE_QUERY
        assert ActionType.from_string("sql") == ActionType.DATABASE_QUERY
        assert ActionType.from_string("done") == ActionType.FINISH
        assert ActionType.from_string("calc") == ActionType.CALCULATE

    def test_from_string_case_insensitive(self):
        """La conversión debe ser case insensitive."""
        assert ActionType.from_string("DATABASE_QUERY") == ActionType.DATABASE_QUERY
        assert ActionType.from_string("Finish") == ActionType.FINISH

    def test_from_string_invalid(self):
        """String inválido debe lanzar error."""
        with pytest.raises(ValueError, match="Unknown action"):
            ActionType.from_string("invalid_action")

    def test_is_tool(self):
        """is_tool debe retornar False solo para FINISH."""
        assert ActionType.DATABASE_QUERY.is_tool() is True
        assert ActionType.CALCULATE.is_tool() is True
        assert ActionType.FINISH.is_tool() is False


class TestReActStep:
    """Tests para ReActStep."""

    def test_step_creation(self):
        """Crear un paso válido."""
        step = ReActStep(
            step_number=1,
            thought="Need to query database",
            action=ActionType.DATABASE_QUERY,
            action_input={"query": "SELECT * FROM users"},
            observation="[{'id': 1}]",
        )

        assert step.step_number == 1
        assert step.action == ActionType.DATABASE_QUERY
        assert step.observation is not None

    def test_to_prompt_format(self):
        """to_prompt_format debe generar formato correcto."""
        step = ReActStep(
            step_number=1,
            thought="Thinking...",
            action=ActionType.DATABASE_QUERY,
            action_input={"query": "SELECT 1"},
            observation="Result: 1",
        )

        prompt = step.to_prompt_format()

        assert "Step 1:" in prompt
        assert "Thought: Thinking..." in prompt
        assert "Action: database_query" in prompt
        assert "Observation: Result: 1" in prompt

    def test_to_dict(self):
        """to_dict debe convertir a diccionario."""
        step = ReActStep(
            step_number=1,
            thought="Test",
            action=ActionType.FINISH,
            action_input={},
        )

        data = step.to_dict()

        assert data["step_number"] == 1
        assert data["action"] == "finish"
        assert "timestamp" in data


class TestReActResponse:
    """Tests para ReActResponse."""

    def test_finish_factory(self):
        """ReActResponse.finish debe crear respuesta final."""
        response = ReActResponse.finish(
            thought="Done thinking",
            answer="Here is your answer",
        )

        assert response.action == ActionType.FINISH
        assert response.final_answer == "Here is your answer"
        assert response.is_final() is True

    def test_tool_call_factory(self):
        """ReActResponse.tool_call debe crear llamada a tool."""
        response = ReActResponse.tool_call(
            thought="Need data",
            action=ActionType.DATABASE_QUERY,
            action_input={"query": "SELECT 1"},
        )

        assert response.action == ActionType.DATABASE_QUERY
        assert response.action_input == {"query": "SELECT 1"}
        assert response.is_final() is False

    def test_tool_call_with_finish_raises_error(self):
        """tool_call con FINISH debe lanzar error."""
        with pytest.raises(ValueError, match="Use ReActResponse.finish"):
            ReActResponse.tool_call(
                thought="Done",
                action=ActionType.FINISH,
                action_input={},
            )

    def test_is_final(self):
        """is_final debe retornar True solo para FINISH."""
        finish = ReActResponse.finish("done", "answer")
        tool = ReActResponse.tool_call("need data", ActionType.CALCULATE, {"expression": "1+1"})

        assert finish.is_final() is True
        assert tool.is_final() is False


class TestScratchpad:
    """Tests para Scratchpad."""

    def test_empty_scratchpad(self):
        """Scratchpad nuevo debe estar vacío."""
        scratchpad = Scratchpad(max_steps=5)

        assert scratchpad.is_empty() is True
        assert scratchpad.is_full() is False
        assert len(scratchpad) == 0

    def test_add_step(self):
        """Agregar paso al scratchpad."""
        scratchpad = Scratchpad(max_steps=5)

        step = scratchpad.add_step(
            thought="Testing",
            action=ActionType.CALCULATE,
            action_input={"expression": "1+1"},
            observation="2",
        )

        assert len(scratchpad) == 1
        assert step.step_number == 1
        assert scratchpad.is_empty() is False

    def test_is_full(self):
        """is_full cuando se alcanza max_steps."""
        scratchpad = Scratchpad(max_steps=2)

        scratchpad.add_step("t1", ActionType.CALCULATE, {}, "1")
        assert scratchpad.is_full() is False

        scratchpad.add_step("t2", ActionType.CALCULATE, {}, "2")
        assert scratchpad.is_full() is True

    def test_add_step_when_full_raises_error(self):
        """Agregar paso cuando está lleno debe lanzar error."""
        scratchpad = Scratchpad(max_steps=1)
        scratchpad.add_step("t1", ActionType.FINISH, {}, None)

        with pytest.raises(ValueError, match="Scratchpad is full"):
            scratchpad.add_step("t2", ActionType.FINISH, {}, None)

    def test_to_prompt_format(self):
        """to_prompt_format debe generar historial formateado."""
        scratchpad = Scratchpad(max_steps=5)
        scratchpad.add_step("First thought", ActionType.CALCULATE, {"expression": "1+1"}, "2")
        scratchpad.add_step("Second thought", ActionType.FINISH, {}, None)

        prompt = scratchpad.to_prompt_format()

        assert "Step 1:" in prompt
        assert "Step 2:" in prompt
        assert "First thought" in prompt
        assert "Second thought" in prompt

    def test_get_last_step(self):
        """get_last_step debe retornar el último paso."""
        scratchpad = Scratchpad(max_steps=5)
        scratchpad.add_step("first", ActionType.CALCULATE, {}, "1")
        scratchpad.add_step("second", ActionType.CALCULATE, {}, "2")

        last = scratchpad.get_last_step()

        assert last is not None
        assert last.thought == "second"

    def test_get_last_observation(self):
        """get_last_observation debe retornar la última observación."""
        scratchpad = Scratchpad(max_steps=5)
        scratchpad.add_step("t1", ActionType.CALCULATE, {}, "obs1")
        scratchpad.add_step("t2", ActionType.CALCULATE, {}, "obs2")

        assert scratchpad.get_last_observation() == "obs2"

    def test_update_last_observation(self):
        """update_last_observation debe actualizar la observación."""
        scratchpad = Scratchpad(max_steps=5)
        scratchpad.add_step("t1", ActionType.CALCULATE, {}, None)

        scratchpad.update_last_observation("new observation")

        assert scratchpad.get_last_observation() == "new observation"

    def test_to_dict(self):
        """to_dict debe convertir a diccionario."""
        scratchpad = Scratchpad(max_steps=3)
        scratchpad.add_step("t", ActionType.FINISH, {}, None)

        data = scratchpad.to_dict()

        assert data["max_steps"] == 3
        assert data["current_steps"] == 1
        assert data["is_full"] is False
        assert len(data["steps"]) == 1

    def test_clear(self):
        """clear debe limpiar todos los pasos."""
        scratchpad = Scratchpad(max_steps=5)
        scratchpad.add_step("t", ActionType.FINISH, {}, None)

        scratchpad.clear()

        assert scratchpad.is_empty() is True


class TestPrompts:
    """Tests para prompts."""

    def test_build_system_prompt(self):
        """build_system_prompt debe incluir tools."""
        tools_desc = "- database_query: Query the database"

        prompt = build_system_prompt(tools_desc)

        assert "database_query" in prompt
        assert "Amber" in prompt
        assert "ReAct" in prompt or "Thought" in prompt

    def test_build_user_prompt(self):
        """build_user_prompt debe incluir query y contexto."""
        prompt = build_user_prompt(
            query="How many users?",
            user_context="User: Juan, Role: admin",
            scratchpad="",
        )

        assert "How many users?" in prompt
        assert "Juan" in prompt

    def test_build_continue_prompt(self):
        """build_continue_prompt debe incluir observación."""
        prompt = build_continue_prompt(observation="Found 10 users")

        assert "Found 10 users" in prompt


class MockTool(BaseTool):
    """Tool de prueba para tests."""

    def __init__(self, name: str = "mock_tool", result: str = "mock result"):
        self._name = name
        self._result = result

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self._name,
            description="Mock tool for testing",
            category=ToolCategory.UTILITY,
        )

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult.success_result(data=self._result)


class TestReActAgent:
    """Tests para ReActAgent."""

    @pytest.fixture
    def mock_llm(self):
        """LLM mock que retorna respuestas predefinidas."""
        llm = AsyncMock()
        return llm

    @pytest.fixture
    def tool_registry(self):
        """Registry con tools de prueba."""
        ToolRegistry.reset()
        registry = ToolRegistry()
        registry.register(MockTool(name="database_query", result="10 users"))
        registry.register(MockTool(name="calculate", result="42"))
        return registry

    @pytest.fixture
    def user_context(self):
        """Contexto de usuario de prueba."""
        return UserContext.empty("test_user_123")

    @pytest.mark.asyncio
    async def test_simple_finish_response(self, mock_llm, tool_registry, user_context):
        """El agente debe responder directamente para saludos."""
        # LLM retorna FINISH directamente
        mock_llm.generate.return_value = json.dumps({
            "thought": "User is greeting, I'll respond directly",
            "action": "finish",
            "action_input": {},
            "final_answer": "Hello! How can I help you?",
        })

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("Hello", user_context)

        assert response.success is True
        assert response.message == "Hello! How can I help you?"
        assert response.steps_taken == 1

    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_llm, tool_registry, user_context):
        """El agente debe ejecutar tools y luego responder."""
        # Primera llamada: ejecutar tool
        # Segunda llamada: finish con resultado
        mock_llm.generate.side_effect = [
            json.dumps({
                "thought": "Need to query database",
                "action": "database_query",
                "action_input": {"query": "SELECT COUNT(*) FROM users"},
                "final_answer": None,
            }),
            json.dumps({
                "thought": "Got the result, can answer now",
                "action": "finish",
                "action_input": {},
                "final_answer": "There are 10 users in the system.",
            }),
        ]

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("How many users?", user_context)

        assert response.success is True
        assert "10 users" in response.message
        assert response.steps_taken == 2

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self, mock_llm, tool_registry, user_context):
        """El agente debe sintetizar respuesta cuando alcanza max_iterations."""
        # LLM siempre retorna tool calls, nunca finish
        mock_llm.generate.return_value = json.dumps({
            "thought": "Need more data",
            "action": "calculate",
            "action_input": {"expression": "1+1"},
            "final_answer": None,
        })

        agent = ReActAgent(
            llm=mock_llm,
            tool_registry=tool_registry,
            max_iterations=3,
        )
        response = await agent.execute("Complex query", user_context)

        assert response.success is True
        assert response.steps_taken == 3
        assert response.metadata.get("partial") is True

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_llm, tool_registry, user_context):
        """El agente debe manejar errores gracefully."""
        mock_llm.generate.side_effect = Exception("LLM API error")

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("Test query", user_context)

        assert response.success is False
        assert "error" in response.error.lower() or "LLM" in response.error

    @pytest.mark.asyncio
    async def test_tool_not_found(self, mock_llm, tool_registry, user_context):
        """El agente debe manejar tools no registrados en el registry."""
        # El LLM usa un action válido pero el tool no está registrado
        # Nota: "knowledge_search" es válido en ActionType pero no está en este registry
        mock_llm.generate.side_effect = [
            json.dumps({
                "thought": "Need to search knowledge",
                "action": "knowledge_search",
                "action_input": {"query": "test"},
                "final_answer": None,
            }),
            json.dumps({
                "thought": "Got error, finish anyway",
                "action": "finish",
                "action_input": {},
                "final_answer": "I encountered an issue searching.",
            }),
        ]

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("Test", user_context)

        # Should still complete - error is handled in observation
        assert response.success is True
        assert "issue" in response.message.lower() or response.steps_taken >= 1

    @pytest.mark.asyncio
    async def test_json_in_code_block(self, mock_llm, tool_registry, user_context):
        """El agente debe parsear JSON envuelto en code blocks."""
        mock_llm.generate.return_value = """```json
{
    "thought": "Responding",
    "action": "finish",
    "action_input": {},
    "final_answer": "Hello!"
}
```"""

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("Hi", user_context)

        assert response.success is True
        assert response.message == "Hello!"

    @pytest.mark.asyncio
    async def test_scratchpad_in_response_data(self, mock_llm, tool_registry, user_context):
        """La respuesta debe incluir el scratchpad en data."""
        mock_llm.generate.return_value = json.dumps({
            "thought": "Simple response",
            "action": "finish",
            "action_input": {},
            "final_answer": "Done!",
        })

        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)
        response = await agent.execute("Test", user_context)

        assert response.data is not None
        assert "scratchpad" in response.data

    @pytest.mark.asyncio
    async def test_health_check(self, mock_llm, tool_registry):
        """health_check debe retornar True cuando hay tools."""
        agent = ReActAgent(llm=mock_llm, tool_registry=tool_registry)

        result = await agent.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_no_tools(self, mock_llm):
        """health_check debe retornar False sin tools."""
        ToolRegistry.reset()
        empty_registry = ToolRegistry()

        agent = ReActAgent(llm=mock_llm, tool_registry=empty_registry)

        result = await agent.health_check()

        assert result is False
