from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from app.data.models import AccountStatus
from app.schemas.request_schemas import LoginRequest, RegisterRequest
from app.web.auth_router import login_user, signup_user, update_token
from app.web.verify_email_router import verify_email


class DummyRequest:
    def __init__(self, cookies):
        self.cookies = cookies


class TestSignupIntegration:
    @pytest.mark.asyncio
    async def test_signup_creates_user_and_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        db = AsyncMock()
        state = {"users": {}, "tokens": {}}

        class UserCRUDFake:
            def __init__(self, _db):
                self.db = _db

            async def get_user(self, email):
                return state["users"].get(email)

            async def create_user(self, email, password_hash, account_status):
                user = SimpleNamespace(email=email, password_hash=password_hash, account_status=account_status, id=1)
                state["users"][email] = user
                return user

        class EmailVarCRUDFake:
            def __init__(self, _db):
                self.db = _db

            async def add_var_token(self, user_email, hashed_token):
                record = SimpleNamespace(
                    user_email=user_email,
                    hashed_token=hashed_token,
                    used=False,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                )
                state["tokens"][hashed_token] = record
                return record

        delay_mock = Mock()

        monkeypatch.setattr("app.web.auth_router.UserCRUD", UserCRUDFake)
        monkeypatch.setattr("app.web.auth_router.EmailVarCRUD", EmailVarCRUDFake)
        monkeypatch.setattr("app.web.auth_router.generate_var_token", lambda _: "raw-token")
        monkeypatch.setattr("app.web.auth_router.hash_token", lambda token: f"h:{token}")
        monkeypatch.setattr("app.web.auth_router.sending_email_verification.delay", delay_mock)

        response = await signup_user(RegisterRequest(email="new@example.com", password="StrongP@ss1"), db)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert "new@example.com" in state["users"]
        assert "h:raw-token" in state["tokens"]
        delay_mock.assert_called_once()


class TestVerifyIntegration:
    @pytest.mark.asyncio
    async def test_verify_email_marks_user_active_and_token_used(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class DBMock:
            def __init__(self) -> None:
                self.add_all = Mock()
                self.committed = False
                self.rollback = AsyncMock()

            async def commit(self):
                self.committed = True

        db = DBMock()

        token_record = SimpleNamespace(
            user_email="u@example.com",
            hashed_token="h:ok-token",
            used=False,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        user = SimpleNamespace(email="u@example.com", account_status=AccountStatus.not_verified)

        class EmailVarCRUDFake:
            def __init__(self, _db):
                pass

            async def check_exist_token(self, hashed):
                if hashed == "h:ok-token":
                    return token_record
                return None

        class UserCRUDFake:
            def __init__(self, _db):
                self.db = _db

            async def get_user(self, email):
                return user if email == "u@example.com" else None

        monkeypatch.setattr("app.web.verify_email_router.EmailVarCRUD", EmailVarCRUDFake)
        monkeypatch.setattr("app.web.verify_email_router.UserCRUD", UserCRUDFake)
        monkeypatch.setattr("app.web.verify_email_router.hash_token", lambda token: f"h:{token}")

        response = await verify_email(db, token="ok-token")

        assert isinstance(response, RedirectResponse)
        assert response.headers["location"] == "http://localhost:5173/verification-success"
        assert token_record.used is True
        assert user.account_status == "active"
        assert db.committed is True

    @pytest.mark.asyncio
    async def test_verify_email_raises_for_missing_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        db = AsyncMock()

        class EmailVarCRUDFake:
            def __init__(self, _db):
                pass

            async def check_exist_token(self, _hashed):
                return None

        monkeypatch.setattr("app.web.verify_email_router.EmailVarCRUD", EmailVarCRUDFake)

        with pytest.raises(HTTPException) as exc:
            await verify_email(db, token="bad")

        assert exc.value.status_code == 400


class TestLoginAndRotationIntegration:
    @pytest.mark.asyncio
    async def test_login_returns_tokens_for_active_account(self, monkeypatch: pytest.MonkeyPatch) -> None:
        db = AsyncMock()

        class UserCRUDFake:
            def __init__(self, _db):
                pass

            async def get_user(self, _email):
                return SimpleNamespace(
                    id=1,
                    email="u@example.com",
                    password_hash="hash",
                    account_status=AccountStatus.active,
                )

        class JWTTokenCRUDFake:
            def __init__(self, _db):
                pass

            def create_access_token(self, _user_id):
                return "access-token", 15

            def create_refresh_token(self, _user_id):
                return "refresh-token", "session-id"

            async def add_refresh_token(self, _token_hash, _user_id, _session_id):
                return None

        monkeypatch.setattr("app.web.auth_router.UserCRUD", UserCRUDFake)
        monkeypatch.setattr("app.web.auth_router.JWTTokenCRUD", JWTTokenCRUDFake)
        monkeypatch.setattr("app.web.auth_router.verify_password", lambda raw, hashed: True)
        monkeypatch.setattr("app.web.auth_router.hash_token", lambda token: f"h:{token}")

        response = await login_user(LoginRequest(email="u@example.com", password="StrongP@ss1"), db)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert "refresh_token=refresh-token" in response.headers.get("set-cookie", "")

    @pytest.mark.asyncio
    async def test_update_token_rotates_refresh_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        db = AsyncMock()

        class JWTTokenCRUDFake:
            def __init__(self, _db):
                pass

            def decode_refresh_token(self, token):
                if token != "refresh-token":
                    raise ValueError("bad token")
                return {"sub": "1", "jti": "session-1", "scope": "refresh"}

            async def get_refresh_token(self, session_id):
                if session_id != "session-1":
                    return None
                return SimpleNamespace(
                    refresh_token_hash="h:refresh-token",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                )

            async def revoke_specific_token(self, _user_id, _session_id):
                return None

            def create_access_token(self, _user_id):
                return "new-access", 15

            def create_refresh_token(self, _user_id):
                return "new-refresh", "session-2"

            async def add_refresh_token(self, _token_hash, _user_id, _session_id):
                return None

        monkeypatch.setattr("app.web.auth_router.JWTTokenCRUD", JWTTokenCRUDFake)
        monkeypatch.setattr("app.web.auth_router.hash_token", lambda token: f"h:{token}")

        request = DummyRequest(cookies={"refresh_token": "refresh-token"})
        response = await update_token(request, db)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert "refresh_token=new-refresh" in response.headers.get("set-cookie", "")
