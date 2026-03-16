from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import jwt
import pytest

from app.data.config import settings
from app.login.jwt_token import JWTTokenCRUD


class TestJWTTokenCRUD:
    @pytest.fixture
    def db(self) -> AsyncMock:
        mocked = AsyncMock()
        mocked.add = Mock()
        return mocked

    @pytest.fixture
    def crud(self, db: AsyncMock) -> JWTTokenCRUD:
        return JWTTokenCRUD(db)

    def test_create_access_token(self, crud: JWTTokenCRUD) -> None:
        token, exp_minutes = crud.create_access_token(1)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "1"
        assert payload["scope"] == "access"
        assert exp_minutes == 15

    def test_create_refresh_token(self, crud: JWTTokenCRUD) -> None:
        token, session_id = crud.create_refresh_token(1)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert payload["sub"] == "1"
        assert payload["scope"] == "refresh"
        assert payload["jti"] == session_id

    @pytest.mark.asyncio
    async def test_add_refresh_token(self, db: AsyncMock, crud: JWTTokenCRUD) -> None:
        new_token = await crud.add_refresh_token("hashed", 1, "session-id")

        assert new_token.user_id == 1
        assert new_token.refresh_token_hash == "hashed"
        assert new_token.session_id == "session-id"
        db.add.assert_called_once_with(new_token)

    @pytest.mark.asyncio
    async def test_revoke_specific_token_executes_delete(self, db: AsyncMock, crud: JWTTokenCRUD) -> None:
        await crud.revoke_specific_token(1, "session-id")

        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_refresh_token_returns_none_when_missing(self, db: AsyncMock, crud: JWTTokenCRUD) -> None:
        result = AsyncMock()
        result.scalar_one_or_none = Mock(return_value=None)
        db.execute.return_value = result

        token = await crud.get_refresh_token("session-id")

        assert token is None

    @pytest.mark.asyncio
    async def test_get_refresh_token_returns_record(self, db: AsyncMock, crud: JWTTokenCRUD) -> None:
        record = type("RefreshTokenStub", (), {"session_id": "session-id"})()
        result = AsyncMock()
        result.scalar_one_or_none = Mock(return_value=record)
        db.execute.return_value = result

        token = await crud.get_refresh_token("session-id")

        assert token is record

    @pytest.mark.asyncio
    async def test_get_refresh_token_returns_none_on_error(self, db: AsyncMock, crud: JWTTokenCRUD) -> None:
        db.execute.side_effect = RuntimeError("db")

        token = await crud.get_refresh_token("session-id")

        assert token is None

    def test_decode_refresh_token_success(self, crud: JWTTokenCRUD) -> None:
        token, _ = crud.create_refresh_token(1)

        payload = crud.decode_refresh_token(token)

        assert payload["sub"] == "1"
        assert payload["scope"] == "refresh"

    def test_decode_refresh_token_invalid_scope(self, crud: JWTTokenCRUD) -> None:
        payload = {
            "sub": "1",
            "scope": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with pytest.raises(Exception, match="Invalid refresh token scope"):
            crud.decode_refresh_token(token)
