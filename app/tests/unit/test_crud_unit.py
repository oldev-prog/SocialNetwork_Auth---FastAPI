from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.data.email_var_crud import EmailVarCRUD
from app.data.models import AccountStatus
from app.data.user_crud import UserCRUD


class TestUserCRUD:
    @pytest.mark.asyncio
    async def test_create_user(self) -> None:
        class DBMock:
            def __init__(self) -> None:
                self.add = Mock()
                self.committed = False
                self.refreshed = None

            async def commit(self):
                self.committed = True

            async def refresh(self, obj):
                self.refreshed = obj

        db = DBMock()
        crud = UserCRUD(db)

        user = await crud.create_user("u@example.com", "hash", AccountStatus.active)

        assert user.email == "u@example.com"
        assert user.password_hash == "hash"
        assert user.account_status == AccountStatus.active
        db.add.assert_called_once_with(user)
        assert db.committed is True
        assert db.refreshed is user

    @pytest.mark.asyncio
    async def test_get_user_found(self) -> None:
        user = type("UserStub", (), {"email": "u@example.com"})()

        class ResultMock:
            def scalar_one_or_none(self):
                return user

        class DBMock:
            async def execute(self, _query):
                return ResultMock()

        crud = UserCRUD(DBMock())
        found = await crud.get_user("u@example.com")

        assert found is user

    @pytest.mark.asyncio
    async def test_get_user_returns_none_on_execute_error(self) -> None:
        class DBMock:
            async def execute(self, _query):
                raise RuntimeError("db error")

        crud = UserCRUD(DBMock())

        found = await crud.get_user("u@example.com")

        assert found is None


class TestEmailVarCRUD:
    @pytest.mark.asyncio
    async def test_add_var_token(self) -> None:
        class DBMock:
            def __init__(self) -> None:
                self.add = Mock()
                self.committed = False
                self.refreshed = None

            async def commit(self):
                self.committed = True

            async def refresh(self, obj):
                self.refreshed = obj

        db = DBMock()
        crud = EmailVarCRUD(db)

        token = await crud.add_var_token("u@example.com", "hashed")

        assert token.user_email == "u@example.com"
        assert token.hashed_token == "hashed"
        assert isinstance(token.expires_at, datetime)
        assert token.expires_at.tzinfo == timezone.utc
        db.add.assert_called_once_with(token)
        assert db.committed is True
        assert db.refreshed is token

    @pytest.mark.asyncio
    async def test_check_exist_token_found(self) -> None:
        expected = type("TokenStub", (), {"hashed_token": "abc"})()

        class ResultMock:
            def scalar_one_or_none(self):
                return expected

        class DBMock:
            async def execute(self, _query):
                return ResultMock()

        crud = EmailVarCRUD(DBMock())
        token = await crud.check_exist_token("abc")

        assert token is expected

    @pytest.mark.asyncio
    async def test_check_exist_token_raises(self) -> None:
        class DBMock:
            async def execute(self, _query):
                raise RuntimeError("db error")

        crud = EmailVarCRUD(DBMock())

        with pytest.raises(RuntimeError, match="db error"):
            await crud.check_exist_token("abc")
