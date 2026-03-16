from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from app.data.models import AccountStatus
from app.schemas.request_schemas import LoginRequest, RegisterRequest
from app.web.auth_router import login_user, logout, signup_user, update_token
from app.web.verify_email_router import verify_email


class DummyRequest:
    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies


class UserRecord:
    def __init__(self, user_id: int, email: str, password_hash: str, account_status: str | AccountStatus):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.account_status = self._normalize_status(account_status)

    @staticmethod
    def _normalize_status(value: str | AccountStatus) -> AccountStatus:
        if isinstance(value, AccountStatus):
            return value
        if value == "active":
            return AccountStatus.active
        if value == "not_verified":
            return AccountStatus.not_verified
        return AccountStatus.not_verified

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "account_status":
            super().__setattr__(key, self._normalize_status(value))
            return
        super().__setattr__(key, value)


class TestAuthFlowE2E:
    @pytest.fixture
    def flow_context(self, monkeypatch: pytest.MonkeyPatch):
        state: dict[str, Any] = {
            "users": {},
            "email_tokens": {},
            "refresh_tokens": {},
            "user_seq": 0,
            "token_seq": 0,
            "session_seq": 0,
            "last_raw_email_token": None,
            "mail_delay": Mock(),
        }

        class DBSessionFake:
            async def commit(self):
                return None

            async def rollback(self):
                return None

            def add(self, _obj):
                return None

            def add_all(self, _objs):
                return None

            async def refresh(self, _obj):
                return None

        db = DBSessionFake()

        class UserCRUDFake:
            def __init__(self, _db):
                self.db = _db

            async def get_user(self, email: str):
                return state["users"].get(email)

            async def create_user(self, email: str, password_hash: str, account_status: str):
                state["user_seq"] += 1
                user = UserRecord(state["user_seq"], email, password_hash, account_status)
                state["users"][email] = user
                return user

        class EmailVarCRUDFake:
            def __init__(self, _db):
                self.db = _db

            async def add_var_token(self, user_email: str, hashed_token: str):
                rec = SimpleNamespace(
                    user_email=user_email,
                    hashed_token=hashed_token,
                    used=False,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                )
                state["email_tokens"][hashed_token] = rec
                return rec

            async def check_exist_token(self, hashed_token: str):
                return state["email_tokens"].get(hashed_token)

        class JWTTokenCRUDFake:
            def __init__(self, _db):
                self.db = _db

            def create_access_token(self, user_id: int):
                return f"at:{user_id}", 15

            def create_refresh_token(self, user_id: int):
                state["session_seq"] += 1
                session_id = f"s{state['session_seq']}"
                return f"rt:{user_id}:{session_id}", session_id

            def decode_refresh_token(self, token: str):
                parts = token.split(":")
                if len(parts) != 3 or parts[0] != "rt":
                    raise ValueError("bad refresh token")
                return {"sub": parts[1], "scope": "refresh", "jti": parts[2]}

            async def add_refresh_token(self, token_hash: str, user_id: int, session_id: str):
                rec = SimpleNamespace(
                    user_id=user_id,
                    refresh_token_hash=token_hash,
                    session_id=session_id,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                )
                state["refresh_tokens"][session_id] = rec
                return rec

            async def get_refresh_token(self, session_id: str):
                return state["refresh_tokens"].get(session_id)

            async def revoke_specific_token(self, _user_id: int, session_id: str):
                state["refresh_tokens"].pop(session_id, None)

        def fake_generate_var_token(_len: int) -> str:
            state["token_seq"] += 1
            raw = f"verify-token-{state['token_seq']}"
            state["last_raw_email_token"] = raw
            return raw

        monkeypatch.setattr("app.web.auth_router.UserCRUD", UserCRUDFake)
        monkeypatch.setattr("app.web.auth_router.EmailVarCRUD", EmailVarCRUDFake)
        monkeypatch.setattr("app.web.auth_router.JWTTokenCRUD", JWTTokenCRUDFake)
        monkeypatch.setattr("app.web.auth_router.generate_var_token", fake_generate_var_token)
        monkeypatch.setattr("app.web.auth_router.hash_token", lambda token: f"h:{token}")
        monkeypatch.setattr("app.web.auth_router.sending_email_verification.delay", state["mail_delay"])

        monkeypatch.setattr("app.web.verify_email_router.UserCRUD", UserCRUDFake)
        monkeypatch.setattr("app.web.verify_email_router.EmailVarCRUD", EmailVarCRUDFake)
        monkeypatch.setattr("app.web.verify_email_router.hash_token", lambda token: f"h:{token}")

        return state, db

    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, flow_context) -> None:
        state, db = flow_context

        signup_response = await signup_user(
            RegisterRequest(email="e2e@example.com", password="StrongP@ss1"),
            db,
        )

        assert isinstance(signup_response, JSONResponse)
        assert signup_response.status_code == 200
        assert "e2e@example.com" in state["users"]
        assert state["mail_delay"].called is True

        verify_response = await verify_email(db, token=state["last_raw_email_token"])

        assert isinstance(verify_response, RedirectResponse)
        assert state["users"]["e2e@example.com"].account_status == AccountStatus.active

        login_response = await login_user(
            LoginRequest(email="e2e@example.com", password="StrongP@ss1"),
            db,
        )

        assert isinstance(login_response, JSONResponse)
        assert login_response.status_code == 200
        set_cookie = login_response.headers.get("set-cookie", "")
        assert "refresh_token=rt:" in set_cookie
        refresh_token = set_cookie.split("refresh_token=")[1].split(";")[0]

        update_response = await update_token(DummyRequest(cookies={"refresh_token": refresh_token}), db)

        assert isinstance(update_response, JSONResponse)
        assert update_response.status_code == 200
        new_set_cookie = update_response.headers.get("set-cookie", "")
        assert "refresh_token=rt:" in new_set_cookie
        rotated_refresh = new_set_cookie.split("refresh_token=")[1].split(";")[0]

        logout_response = await logout(DummyRequest(cookies={"refresh_token": rotated_refresh}), db)

        assert isinstance(logout_response, JSONResponse)
        assert logout_response.status_code == 200
        assert logout_response.body == b'{"details":"Successfully logged out."}'

    @pytest.mark.asyncio
    async def test_update_token_rejects_invalid_refresh_token(self, flow_context) -> None:
        _, db = flow_context

        with pytest.raises(HTTPException) as exc:
            await update_token(DummyRequest(cookies={"refresh_token": "bad-token"}), db)

        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid refresh token payload"
