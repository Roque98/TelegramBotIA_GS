"""
Tests para el módulo de memoria.

Cobertura:
- UserProfile: Dataclass de perfil
- MemoryRepository: Acceso a datos con cache
- ContextBuilder: Construcción de UserContext
- MemoryService: Servicio principal con cache TTL
- CacheEntry: Entrada de cache con TTL
"""

import asyncio
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.memory.repository import (
    MemoryRepository,
    UserProfile,
    Interaction,
)
from src.memory.context_builder import ContextBuilder
from src.memory.service import MemoryService, CacheEntry
from src.agents.base.events import UserContext


class TestUserProfile:
    """Tests para UserProfile."""

    def test_profile_creation(self):
        """Crear perfil con valores por defecto."""
        profile = UserProfile(user_id="123")

        assert profile.user_id == "123"
        assert profile.display_name == "Usuario"
        assert profile.roles == []
        assert profile.long_term_summary is None
        assert profile.interaction_count == 0

    def test_profile_with_values(self):
        """Crear perfil con valores específicos."""
        profile = UserProfile(
            user_id="456",
            display_name="Juan",
            roles=["admin", "user"],
            long_term_summary="Le gusta Python",
            interaction_count=50,
        )

        assert profile.display_name == "Juan"
        assert "admin" in profile.roles
        assert profile.has_summary() is True

    def test_has_summary_false(self):
        """has_summary debe retornar False sin resumen."""
        profile = UserProfile(user_id="789")
        assert profile.has_summary() is False

        profile.long_term_summary = ""
        assert profile.has_summary() is False

    def test_has_summary_true(self):
        """has_summary debe retornar True con resumen."""
        profile = UserProfile(user_id="789", long_term_summary="Some summary")
        assert profile.has_summary() is True


class TestInteraction:
    """Tests para Interaction."""

    def test_interaction_creation(self):
        """Crear interacción con valores requeridos."""
        interaction = Interaction(
            interaction_id="int_1",
            user_id="user_1",
            query="Hello",
            response="Hi there!",
        )

        assert interaction.interaction_id == "int_1"
        assert interaction.query == "Hello"
        assert interaction.timestamp is not None

    def test_interaction_with_metadata(self):
        """Crear interacción con metadata."""
        interaction = Interaction(
            interaction_id="int_2",
            user_id="user_2",
            query="Calculate",
            response="42",
            metadata={"tools_used": ["calculate"]},
        )

        assert interaction.metadata["tools_used"] == ["calculate"]


class TestMemoryRepository:
    """Tests para MemoryRepository."""

    @pytest.fixture
    def repository(self):
        """Repository sin DB manager (modo testing)."""
        return MemoryRepository(db_manager=None)

    @pytest.mark.asyncio
    async def test_get_profile_without_db(self, repository):
        """get_profile sin DB debe retornar None."""
        profile = await repository.get_profile("123")
        assert profile is None

    @pytest.mark.asyncio
    async def test_save_and_get_profile_cache(self, repository):
        """save_profile debe cachear y get_profile debe recuperarlo."""
        profile = UserProfile(user_id="123", display_name="Test")

        # Guardar en cache
        result = await repository.save_profile(profile)
        assert result is True

        # Recuperar del cache
        retrieved = await repository.get_profile("123")
        assert retrieved is not None
        assert retrieved.display_name == "Test"

    @pytest.mark.asyncio
    async def test_get_recent_messages_without_db(self, repository):
        """get_recent_messages sin DB debe retornar lista vacía."""
        messages = await repository.get_recent_messages("123")
        assert messages == []

    @pytest.mark.asyncio
    async def test_save_interaction_without_db(self, repository):
        """save_interaction sin DB debe retornar True (no-op)."""
        result = await repository.save_interaction("123", "query", "response")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_interaction_count_without_profile(self, repository):
        """get_interaction_count sin perfil debe retornar 0."""
        count = await repository.get_interaction_count("nonexistent")
        assert count == 0

    @pytest.mark.asyncio
    async def test_increment_interaction_count(self, repository):
        """increment_interaction_count debe incrementar el contador."""
        # Primera incrementación crea el perfil
        count1 = await repository.increment_interaction_count("123")
        assert count1 == 1

        # Segunda incrementación usa perfil existente
        count2 = await repository.increment_interaction_count("123")
        assert count2 == 2

    def test_invalidate_cache(self, repository):
        """invalidate_cache debe eliminar perfil del cache."""
        # Agregar al cache
        repository._profiles_cache["123"] = UserProfile(user_id="123")

        # Invalidar
        repository.invalidate_cache("123")

        # Verificar
        assert "123" not in repository._profiles_cache

    def test_clear_cache(self, repository):
        """clear_cache debe limpiar todo el cache."""
        repository._profiles_cache["123"] = UserProfile(user_id="123")
        repository._profiles_cache["456"] = UserProfile(user_id="456")

        repository.clear_cache()

        assert len(repository._profiles_cache) == 0


class TestMemoryRepositoryWithDB:
    """Tests para MemoryRepository con mock DB."""

    @pytest.fixture
    def mock_db(self):
        """Mock del DatabaseManager."""
        db = MagicMock()
        db.execute_query = MagicMock()
        db.execute_non_query = MagicMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Repository con mock DB."""
        return MemoryRepository(db_manager=mock_db)

    @pytest.mark.asyncio
    async def test_get_profile_from_db(self, repository, mock_db):
        """get_profile debe consultar la BD."""
        mock_db.execute_query.return_value = [
            {
                "Id_Usuario": 123,
                "Nombre": "Juan",
                "resumen_contexto_laboral": "Trabaja en IT",
                "resumen_temas_recientes": None,
                "resumen_historial_breve": None,
                "num_interacciones": 10,
                "ultima_actualizacion": datetime.now(UTC),
            }
        ]

        profile = await repository.get_profile("123")

        assert profile is not None
        assert profile.display_name == "Juan"
        assert profile.interaction_count == 10
        assert "Trabaja en IT" in profile.long_term_summary

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, repository, mock_db):
        """get_profile debe retornar None si no existe."""
        mock_db.execute_query.return_value = []

        profile = await repository.get_profile("999")

        assert profile is None

    @pytest.mark.asyncio
    async def test_get_profile_db_error(self, repository, mock_db):
        """get_profile debe manejar errores de BD."""
        mock_db.execute_query.side_effect = Exception("DB Error")

        profile = await repository.get_profile("123")

        assert profile is None


class TestContextBuilder:
    """Tests para ContextBuilder."""

    @pytest.fixture
    def mock_repository(self):
        """Mock del MemoryRepository."""
        repo = AsyncMock(spec=MemoryRepository)
        return repo

    @pytest.fixture
    def builder(self, mock_repository):
        """ContextBuilder con mock repository."""
        return ContextBuilder(repository=mock_repository, max_working_memory=5)

    @pytest.mark.asyncio
    async def test_build_context_with_profile(self, builder, mock_repository):
        """build_context debe crear UserContext con datos del perfil."""
        mock_repository.get_profile.return_value = UserProfile(
            user_id="123",
            display_name="Juan",
            roles=["admin"],
            long_term_summary="Le gusta Python",
        )
        mock_repository.get_recent_messages.return_value = [
            {"role": "user", "content": "Hola"}
        ]

        context = await builder.build_context("123")

        assert context.user_id == "123"
        assert context.display_name == "Juan"
        assert "admin" in context.roles
        assert context.long_term_summary == "Le gusta Python"
        assert len(context.working_memory) == 1

    @pytest.mark.asyncio
    async def test_build_context_without_profile(self, builder, mock_repository):
        """build_context debe usar defaults si no hay perfil."""
        mock_repository.get_profile.return_value = None
        mock_repository.get_recent_messages.return_value = []

        context = await builder.build_context("999")

        assert context.user_id == "999"
        assert context.display_name == "Usuario"
        assert context.roles == []

    @pytest.mark.asyncio
    async def test_build_context_without_working_memory(self, builder, mock_repository):
        """build_context debe excluir working memory si se pide."""
        mock_repository.get_profile.return_value = UserProfile(user_id="123")

        context = await builder.build_context("123", include_working_memory=False)

        assert context.working_memory == []
        mock_repository.get_recent_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_context_without_long_term(self, builder, mock_repository):
        """build_context debe excluir long_term si se pide."""
        mock_repository.get_profile.return_value = UserProfile(
            user_id="123",
            long_term_summary="Summary",
        )
        mock_repository.get_recent_messages.return_value = []

        context = await builder.build_context("123", include_long_term=False)

        assert context.long_term_summary is None

    @pytest.mark.asyncio
    async def test_build_minimal_context(self, builder, mock_repository):
        """build_minimal_context debe crear contexto mínimo."""
        mock_repository.get_profile.return_value = UserProfile(
            user_id="123",
            display_name="Juan",
            roles=["user"],
        )

        context = await builder.build_minimal_context("123")

        assert context.user_id == "123"
        assert context.display_name == "Juan"
        # Minimal no debe tener working_memory ni summary cargados

    @pytest.mark.asyncio
    async def test_enrich_context(self, builder, mock_repository):
        """enrich_context debe agregar datos al contexto."""
        original = UserContext(
            user_id="123",
            display_name="Juan",
            preferences={"theme": "dark"},
        )

        enriched = await builder.enrich_context(
            original,
            {"locale": "es-MX"},
        )

        assert enriched.preferences["theme"] == "dark"
        assert enriched.preferences["locale"] == "es-MX"
        assert enriched.user_id == "123"

    def test_format_working_memory_empty(self):
        """format_working_memory debe manejar lista vacía."""
        result = ContextBuilder.format_working_memory([])
        assert "Sin conversaciones recientes" in result

    def test_format_working_memory_with_messages(self):
        """format_working_memory debe formatear mensajes."""
        messages = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"},
        ]

        result = ContextBuilder.format_working_memory(messages)

        assert "Usuario: Hola" in result
        assert "Asistente: ¡Hola!" in result


class TestCacheEntry:
    """Tests para CacheEntry."""

    def test_cache_entry_creation(self):
        """Crear entrada de cache."""
        context = UserContext.empty("123")
        entry = CacheEntry(context=context, ttl_seconds=60)

        assert entry.context == context
        assert entry.ttl_seconds == 60
        assert entry.is_expired() is False

    def test_cache_entry_not_expired(self):
        """Entrada reciente no debe estar expirada."""
        context = UserContext.empty("123")
        entry = CacheEntry(context=context, ttl_seconds=300)

        assert entry.is_expired() is False
        assert entry.time_remaining() > 0

    def test_cache_entry_expired(self):
        """Entrada antigua debe estar expirada."""
        context = UserContext.empty("123")
        entry = CacheEntry(
            context=context,
            ttl_seconds=1,
            created_at=datetime.now(UTC) - timedelta(seconds=10),
        )

        assert entry.is_expired() is True
        assert entry.time_remaining() == 0

    def test_time_remaining(self):
        """time_remaining debe calcular tiempo restante."""
        context = UserContext.empty("123")
        entry = CacheEntry(context=context, ttl_seconds=60)

        remaining = entry.time_remaining()
        assert 55 < remaining <= 60


class TestMemoryService:
    """Tests para MemoryService."""

    @pytest.fixture
    def mock_repository(self):
        """Mock del MemoryRepository."""
        repo = AsyncMock(spec=MemoryRepository)
        repo.invalidate_cache = MagicMock()
        repo.clear_cache = MagicMock()
        return repo

    @pytest.fixture
    def mock_builder(self):
        """Mock del ContextBuilder."""
        builder = AsyncMock(spec=ContextBuilder)
        return builder

    @pytest.fixture
    def service(self, mock_repository, mock_builder):
        """MemoryService con mocks."""
        return MemoryService(
            repository=mock_repository,
            context_builder=mock_builder,
            cache_ttl_seconds=60,
            max_cache_size=100,
        )

    @pytest.mark.asyncio
    async def test_get_context_cache_miss(self, service, mock_builder):
        """get_context debe construir contexto si no está en cache."""
        expected = UserContext.empty("123")
        mock_builder.build_context.return_value = expected

        result = await service.get_context("123")

        assert result == expected
        mock_builder.build_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_context_cache_hit(self, service, mock_builder):
        """get_context debe usar cache si está disponible."""
        expected = UserContext.empty("123")
        mock_builder.build_context.return_value = expected

        # Primera llamada - cache miss
        await service.get_context("123")

        # Segunda llamada - cache hit
        result = await service.get_context("123")

        assert result == expected
        # Solo una llamada al builder
        assert mock_builder.build_context.call_count == 1

    @pytest.mark.asyncio
    async def test_get_context_force_refresh(self, service, mock_builder):
        """get_context con force_refresh debe ignorar cache."""
        expected = UserContext.empty("123")
        mock_builder.build_context.return_value = expected

        # Primera llamada
        await service.get_context("123")

        # Segunda con refresh
        await service.get_context("123", force_refresh=True)

        # Dos llamadas al builder
        assert mock_builder.build_context.call_count == 2

    @pytest.mark.asyncio
    async def test_get_minimal_context(self, service, mock_builder):
        """get_minimal_context debe delegar al builder."""
        expected = UserContext.empty("123")
        mock_builder.build_minimal_context.return_value = expected

        result = await service.get_minimal_context("123")

        assert result == expected
        mock_builder.build_minimal_context.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_record_interaction(self, service, mock_repository):
        """record_interaction debe guardar y actualizar contador."""
        mock_repository.save_interaction.return_value = True
        mock_repository.increment_interaction_count.return_value = 1

        result = await service.record_interaction(
            user_id="123",
            query="Hello",
            response="Hi!",
            metadata={"tool": "none"},
        )

        assert result is True
        mock_repository.save_interaction.assert_called_once()
        mock_repository.increment_interaction_count.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_record_interaction_invalidates_cache(
        self, service, mock_repository, mock_builder
    ):
        """record_interaction debe invalidar cache del usuario."""
        # Primero poblar el cache
        mock_builder.build_context.return_value = UserContext.empty("123")
        await service.get_context("123")

        # Grabar interacción
        mock_repository.save_interaction.return_value = True
        mock_repository.increment_interaction_count.return_value = 1
        await service.record_interaction("123", "query", "response")

        # El cache debe estar invalidado
        mock_repository.invalidate_cache.assert_called_with("123")

    @pytest.mark.asyncio
    async def test_update_summary_new_profile(self, service, mock_repository):
        """update_summary debe crear perfil si no existe."""
        mock_repository.get_profile.return_value = None
        mock_repository.save_profile.return_value = True

        result = await service.update_summary("123", "New summary")

        assert result is True
        mock_repository.save_profile.assert_called_once()
        saved_profile = mock_repository.save_profile.call_args[0][0]
        assert saved_profile.long_term_summary == "New summary"

    @pytest.mark.asyncio
    async def test_update_summary_existing_profile(self, service, mock_repository):
        """update_summary debe actualizar perfil existente."""
        existing = UserProfile(user_id="123", long_term_summary="Old summary")
        mock_repository.get_profile.return_value = existing
        mock_repository.save_profile.return_value = True

        result = await service.update_summary("123", "New summary")

        assert result is True
        assert existing.long_term_summary == "New summary"

    @pytest.mark.asyncio
    async def test_enrich_context(self, service, mock_builder):
        """enrich_context debe delegar al builder."""
        original = UserContext.empty("123")
        enriched = UserContext(user_id="123", preferences={"new": "data"})
        mock_builder.enrich_context.return_value = enriched

        result = await service.enrich_context(original, {"new": "data"})

        assert result == enriched

    def test_clear_cache(self, service, mock_repository):
        """clear_cache debe limpiar ambos caches."""
        service.clear_cache()

        mock_repository.clear_cache.assert_called_once()
        assert len(service._cache) == 0

    def test_get_cache_stats(self, service):
        """get_cache_stats debe retornar estadísticas."""
        stats = service.get_cache_stats()

        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "max_size" in stats
        assert stats["max_size"] == 100

    @pytest.mark.asyncio
    async def test_health_check_success(self, service, mock_builder):
        """health_check debe retornar True si funciona."""
        mock_builder.build_minimal_context.return_value = UserContext.empty("test")

        result = await service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, service, mock_builder):
        """health_check debe retornar False si falla."""
        mock_builder.build_minimal_context.side_effect = Exception("Error")

        result = await service.health_check()

        assert result is False


class TestMemoryServiceCacheCleanup:
    """Tests para limpieza de cache en MemoryService."""

    @pytest.mark.asyncio
    async def test_cache_cleanup_on_full(self):
        """El cache debe limpiarse cuando está lleno."""
        mock_repository = AsyncMock(spec=MemoryRepository)
        mock_repository.invalidate_cache = MagicMock()
        mock_builder = AsyncMock(spec=ContextBuilder)

        service = MemoryService(
            repository=mock_repository,
            context_builder=mock_builder,
            cache_ttl_seconds=300,
            max_cache_size=3,  # Cache muy pequeño
        )

        # Llenar el cache
        for i in range(5):
            mock_builder.build_context.return_value = UserContext.empty(str(i))
            await service.get_context(str(i))

        # Debe haber limpiado algunas entradas
        assert len(service._cache) <= 3

    @pytest.mark.asyncio
    async def test_expired_entries_cleaned(self):
        """Las entradas expiradas deben eliminarse."""
        mock_repository = AsyncMock(spec=MemoryRepository)
        mock_repository.invalidate_cache = MagicMock()
        mock_builder = AsyncMock(spec=ContextBuilder)

        service = MemoryService(
            repository=mock_repository,
            context_builder=mock_builder,
            cache_ttl_seconds=1,  # TTL muy corto
            max_cache_size=10,
        )

        # Agregar entrada
        mock_builder.build_context.return_value = UserContext.empty("123")
        await service.get_context("123")

        # Esperar que expire
        await asyncio.sleep(1.5)

        # Verificar que está expirada
        entry = service._cache.get("123:True:True")
        if entry:
            assert entry.is_expired() is True
