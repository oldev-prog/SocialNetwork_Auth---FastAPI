from unittest.mock import AsyncMock

import pytest

from app.signup.email_verification.creating_var_token import generate_var_token
from app.signup.email_verification.sending_email import send_verification_email


class TestVerificationToken:
    def test_generate_var_token(self) -> None:
        token = generate_var_token(16)

        assert isinstance(token, str)
        assert len(token) > 0


class TestEmailSender:
    @pytest.mark.asyncio
    async def test_send_verification_email_with_html(self, monkeypatch: pytest.MonkeyPatch) -> None:
        send_mock = AsyncMock()
        monkeypatch.setattr("app.signup.email_verification.sending_email.aiosmtplib.send", send_mock)

        await send_verification_email(
            recipient_email="user@example.com",
            subject="Verify",
            plain_text="plain",
            html_content="<b>html</b>",
        )

        send_mock.assert_awaited_once()
        sent_message = send_mock.await_args.args[0]
        assert sent_message["To"] == "user@example.com"
        assert sent_message["Subject"] == "Verify"
        assert len(sent_message.get_payload()) == 2

    @pytest.mark.asyncio
    async def test_send_verification_email_without_html(self, monkeypatch: pytest.MonkeyPatch) -> None:
        send_mock = AsyncMock()
        monkeypatch.setattr("app.signup.email_verification.sending_email.aiosmtplib.send", send_mock)

        await send_verification_email(
            recipient_email="user@example.com",
            subject="Verify",
            plain_text="plain",
        )

        sent_message = send_mock.await_args.args[0]
        assert len(sent_message.get_payload()) == 1
