from unittest.mock import AsyncMock, Mock

import pytest

from app.utils.passw_func import hash_password, verify_password
from app.utils.utils import hash_token, update_db


class TestPasswordFunctions:
    def test_hash_and_verify_password(self) -> None:
        raw_password = "StrongP@ssw0rd"

        password_hash = hash_password(raw_password)

        assert password_hash != raw_password
        assert verify_password(raw_password, password_hash) is True
        assert verify_password("wrong-password", password_hash) is False


class TestUtils:
    def test_hash_token_is_deterministic(self) -> None:
        assert hash_token("abc") == hash_token("abc")
        assert hash_token("abc") != hash_token("def")

    @pytest.mark.asyncio
    async def test_update_db_for_single_object(self) -> None:
        db = AsyncMock()
        db.add = Mock()

        obj = object()
        result = await update_db(obj, db)

        db.add.assert_called_once_with(obj)
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(obj)
        assert result["details"]

    @pytest.mark.asyncio
    async def test_update_db_for_list(self) -> None:
        db = AsyncMock()
        db.add_all = Mock()

        objs = [object(), object()]
        await update_db(objs, db)

        db.add_all.assert_called_once_with(objs)
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_db_rollback_on_error(self) -> None:
        db = AsyncMock()
        db.add = Mock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await update_db(object(), db)

        db.rollback.assert_awaited_once()
