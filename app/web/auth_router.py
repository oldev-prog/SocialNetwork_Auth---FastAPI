from fastapi import APIRouter, Query, HTTPException, status, Request
from fastapi.responses import JSONResponse
from app.main import user_crud, var_token_crud, jwt_token_crud
from app.schemas.request_schemas import RegisterRequest, LoginRequest
from app.schemas.response_shemas import RefreshTokenResponse, AccessTokenResponse, BaseResponse
from app.utils.passw_func import hash_password, verify_password
from app.signup.email_verification.creating_var_token import generate_var_token
from app.signup.email_verification.celery.tasks import sending_email_verification
from app.utils.utils import hash_token, update_db
from datetime import datetime, timezone

auth_router = APIRouter(prefix='/auth', tags=['auth'])

@auth_router.post('/signup', response_model=BaseResponse)
async def signup_user(request: RegisterRequest):
    email, password, account_status = request.email, request.password, 'not verified'
    user = await user_crud.get_user(email)
    if user:
        return JSONResponse(
            {
                'details': 'email already registered',
            }
        )

    hashed_password = hash_password(password)

    user = await user_crud.create_user(
        email=email,
        password_hash=hashed_password,
        account_status=account_status,
    )

    var_token = generate_var_token(32)

    hash_var_token = hash_token(var_token)

    await var_token_crud.add_var_token(user.id, hash_var_token)

    sending_email_verification.delay(recipient_email=email, subject='Verification', plain_content='')

    return JSONResponse(
        {
            'details': f'user {email} registered',
        }
    )


@auth_router.post('/verify_email', response_model=BaseResponse)
async def verify_email(token: str = Query(...)):
    token_hash = hash_token(token)

    var_token = await var_token_crud.check_exist_token(token_hash)

    if (
        not var_token
        or var_token.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired verification token',
        )

    user = await user_crud.get_user(var_token.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired verification token',
        )

    user.account_status = 'active'
    var_token.used = True

    await update_db(user, var_token)

    return JSONResponse(
        {
            'details': f'user {user.email} verified',
        }
    )


@auth_router.post('/login', response_model=AccessTokenResponse)
async def login_user(data: LoginRequest):

    user = user_crud.get_user(data.email)

    if (
        not user
        or not verify_password(data.password, user.password_hash)
        or user.account_status != 'active'
        ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid password or email',
        )

    access_token, expire_in = jwt_token_crud.create_access_token(user.id)
    refresh_token = jwt_token_crud.create_refresh_token(user.id)

    hashed_refresh_token = hash_token(refresh_token)

    await jwt_token_crud.add_token(hashed_refresh_token)

    response = JSONResponse(
        {
            'access_token': access_token,
            'token_type': 'bearer',
            'expires_in': expire_in,
            'details': f'user {user.email} logged in',
        }
    )

    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite='strict',
        path='/auth/update_refresh',
    )

    return response


@auth_router.post('/update_access', response_model=AccessTokenResponse)
async def update_access_token(request: Request):
    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token not found',
        )

    payload = jwt_token_crud.decode_refresh_token(refresh_token)

    user_id = int(payload.get('sub'))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token payload',
        )

    token_record = await jwt_token_crud.get_refresh_token(user_id)
    if (
        not token_record
        or token_record.revoked_at
        or token_record.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token revoked or expired',
        )

    new_access_token, expires_in = jwt_token_crud.create_access_token(user_id)

    response = JSONResponse(
        {
            'access_token': new_access_token,
            'token_type': 'bearer',
            'expires_in': expires_in,
        }
    )

    return response


@auth_router.post('/update_refresh', response_model=RefreshTokenResponse)
async def update_refresh_token(request: Request):
    old_refresh_token = request.cookies.get('refresh_token')

    if not old_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token not found',
        )

    payload = jwt_token_crud.decode_refresh_token(old_refresh_token)

    user_id = int(payload.get('sub'))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token payload',
        )

    token_record = await jwt_token_crud.get_refresh_token(user_id)
    if (
            not token_record
            or token_record.revoked_at
            or token_record.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token revoked or expired',
        )

    new_refresh_token = jwt_token_crud.create_refresh_token(user_id)
    hashed_new_refresh_token = hash_token(new_refresh_token)

    await jwt_token_crud.add_refresh_token(hashed_new_refresh_token, user_id)

    response = JSONResponse(
        {
            'details':'Refresh token updated',
        }
    )

    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite='strict',
        path='/auth/update_refresh',
    )

    return response
