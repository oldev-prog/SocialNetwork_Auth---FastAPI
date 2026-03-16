import pytest
from pydantic import ValidationError

from app.schemas.request_schemas import EmailOnlyRequest, RegisterRequest


class TestRequestSchemas:
    def test_register_request_validates_strong_password(self) -> None:
        model = RegisterRequest(email="u@example.com", password="StrongP@ss1")

        assert model.email == "u@example.com"

    def test_register_request_rejects_weak_password(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(email="u@example.com", password="weakpass")

    def test_email_only_request_accepts_email(self) -> None:
        model = EmailOnlyRequest(email="u@example.com")

        assert model.email == "u@example.com"
