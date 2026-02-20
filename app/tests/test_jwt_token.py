import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.login.jwt_token import JWTTokenCRUD
from app.data.models import RefreshToken
from datetime import datetime, timedelta, timezone
import jwt
import uuid

@pytest.fixture
def create_session():
    async def _create_session():
        class MockSession:
            async def add(self, *args, **kwargs):
                pass

            async def execute(self, query):
                if 'RefreshToken' in str(query):
                    return [MockRefreshToken()]
                return None

            async def scalar_one_or_none(self):
                return MockRefreshToken()

        return AsyncMock(spec=MockSession)
    return _create_session

@pytest.fixture
def create_jwt_token_crud():
    async def _create_jwt_token_crud(db):
        class MockSettings:
            SECRET_KEY = 'test-secret'
            ALGORITHM = 'HS256'

        settings = MockSettings()
        crud = JWTTokenCRUD(db, settings)
        return crud
    return _create_jwt_token_crud

@pytest.fixture
def create_mock_refresh_token():
    return MockRefreshToken()

# Тест на создание access токена
async def test_create_access_token(create_session, create_jwt_token_crud):
    db = await create_session()
    crud = create_jwt_token_crud(db)
    token, exp_time = crud.create_access_token(1)
    payload = jwt.decode(token, 'test-secret', algorithms=['HS256'])
    assert payload['sub'] == '1'
    assert payload['scope'] == 'access'
    assert datetime.fromtimestamp(payload['iat']) <= datetime.now()
    assert datetime.fromtimestamp(payload['exp']) >= datetime.now() + timedelta(minutes=15)

# Тест на создание refresh токена
async def test_create_refresh_token(create_session, create_jwt_token_crud):
    db = await create_session()
    crud = create_jwt_token_crud(db)
    token, session_id = crud.create_refresh_token(1)
    payload = jwt.decode(token, 'test-secret', algorithms=['HS256'])
    assert payload['sub'] == '1'
    assert payload['scope'] == 'refresh'
    assert datetime.fromtimestamp(payload['iat']) <= datetime.now()
    assert datetime.fromtimestamp(payload['exp']) >= datetime.now() + timedelta(days=30)
    assert len(session_id) == 36  # UUID имеет длину 36 символов

# Тест на добавление refresh токена в базу данных
async def test_add_refresh_token(create_session, create_jwt_token_crud):
    db = await create_session()
    crud = create_jwt_token_crud(db)
    new_token = await crud.add_refresh_token('hashed-token', 1, str(uuid.uuid4()))
    assert isinstance(new_token, RefreshToken)
    assert new_token.user_id == 1
    assert new_token.refresh_token_hash == 'hashed-token'

# Тест на получение refresh токена из базы данных
async def test_get_refresh_token(create_session, create_jwt_token_crud):
    db = await create_session()
    crud = create_jwt_token_crud(db)
    token = await crud.get_refresh_token('test-session-id')
    assert isinstance(token, RefreshToken)

# Тест на декодирование refresh токена
async def test_decode_refresh_token(create_session, create_jwt_token_crud):
    db = await create_session()
    crud = create_jwt_token_crud(db)
    payload = crud.decode_refresh_token('test-token')
    assert payload['sub'] == '1'
    assert payload['scope'] == 'refresh'