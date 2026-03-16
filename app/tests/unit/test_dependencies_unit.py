from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException

from app.data.config import settings
from app.dependencies.auth_dependencies import get_current_user_id
from app.dependencies.db_dependencies import get_db


class TestAuthDependencies:
    @pytest.mark.asyncio
    async def test_get_current_user_id_success(self) -> None:
        token = jwt.encode({"sub": "42"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        user_id = await get_current_user_id(token)

        assert user_id == 42

    @pytest.mark.asyncio
    async def test_get_current_user_id_raises_for_missing_sub(self) -> None:
        token = jwt.encode({"scope": "access"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(HTTPException) as exc:
            await get_current_user_id(token)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_id_raises_for_invalid_token(self) -> None:
        with pytest.raises(HTTPException) as exc:
            await get_current_user_id("broken-token")

        assert exc.value.status_code == 401


class TestDbDependencies:
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        session = AsyncMock()

        class SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr("app.dependencies.db_dependencies.async_session_factory", lambda: SessionContext())

        gen = get_db()
        yielded = await anext(gen)

        assert yielded is session

        with pytest.raises(StopAsyncIteration):
            await anext(gen)
