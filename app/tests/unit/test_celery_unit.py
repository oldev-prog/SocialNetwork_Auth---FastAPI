from unittest.mock import AsyncMock, Mock

from app.signup.email_verification.celery.tasks import sending_email_verification


class TestCeleryTasks:
    def test_sending_email_verification_runs_async_send(self, monkeypatch) -> None:
        send_mock = AsyncMock()
        run_mock = Mock()

        def fake_run(coro):
            run_mock(coro)
            return None

        monkeypatch.setattr(
            "app.signup.email_verification.celery.tasks.send_verification_email",
            send_mock,
        )
        monkeypatch.setattr("app.signup.email_verification.celery.tasks.asyncio.run", fake_run)

        sending_email_verification.run("u@example.com", "subj", "plain")

        run_mock.assert_called_once()
