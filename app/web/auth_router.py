from fastapi import APIRouter, Query, HTTPException, status, Request
from fastapi.responses import JSONResponse
from app.data.email_var_crud import EmailVarCRUD
from app.data.user_crud import UserCRUD
from app.login.jwt_token import JWTTokenCRUD
from app.schemas.request_schemas import RegisterRequest, LoginRequest, EmailOnlyRequest
from app.schemas.response_shemas import RefreshTokenResponse, AccessTokenResponse, BaseResponse
from app.utils.passw_func import hash_password, verify_password
from app.signup.email_verification.creating_var_token import generate_var_token
from app.signup.email_verification.celery.tasks import sending_email_verification
from app.utils.utils import hash_token, update_db
from datetime import datetime, timezone
from app.dependencies.db_dependencies import db_session
from app.dependencies.auth_dependencies import current_user_id
from app.data.models import AccountStatus

auth_router = APIRouter(prefix='/auth', tags=['auth'])

@auth_router.post('/signup', response_model=BaseResponse)
async def signup_user(request: RegisterRequest, db: db_session):

    user_crud = UserCRUD(db)
    var_token_crud = EmailVarCRUD(db)

    email, password, account_status = request.email, request.password, 'not_verified'
    exiting_user = await user_crud.get_user(email)
    if exiting_user:
        print('User already exists')
        if exiting_user:
            return JSONResponse(
                status_code=400,
                content={'details': 'Email already registered.'}
            )

    hashed_password = hash_password(password)

    user = await user_crud.create_user(
        email=email,
        password_hash=hashed_password,
        account_status=account_status,
    )

    var_token = generate_var_token(32)

    hash_var_token = hash_token(var_token)

    await var_token_crud.add_var_token(user.email, hash_var_token)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

    sending_email_verification.delay(
        recipient_email=email,
        subject='Verification',
        plain_content=
        'To verify your account, please click the link below\n'
        f'http://127.0.0.1:8000/verify_email/verify?token={var_token}',
    )

    return JSONResponse(
        {
            'details': f'user {email} registered',
        }
    )


@auth_router.post('/login', response_model=AccessTokenResponse)
async def login_user(data: LoginRequest, db: db_session):
    user_crud = UserCRUD(db)
    jwt_token_crud = JWTTokenCRUD(db)
    var_token_crud = EmailVarCRUD(db)

    user = await user_crud.get_user(data.email)

    if (
        not user
        or not verify_password(data.password, user.password_hash)
        ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid password or email',
        )

    if user.account_status is not AccountStatus.active:
        new_token = generate_var_token(32)
        hash_new_token = hash_token(new_token)

        await var_token_crud.add_var_token(user.email, hash_new_token)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Database error")

        sending_email_verification.delay(
            recipient_email=user.email,
            subject='Verification (Resend)',
            plain_content=
            'To verify your account, please click the link below\n'
            f'http://127.0.0.1:8000/verify_email/verify?token={new_token}',
        )
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail='Account is not varified. Please check your email.',
        )

    access_token, expire_in = jwt_token_crud.create_access_token(user.id)
    refresh_token, session_id = jwt_token_crud.create_refresh_token(user.id)

    hashed_refresh_token = hash_token(refresh_token)

    await jwt_token_crud.add_refresh_token(hashed_refresh_token, user.id, session_id)

    await db.commit()

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
        # secure=True,
        secure=False,
        samesite='strict',
        path='/',
    )

    return response


@auth_router.post('/update_token', response_model=AccessTokenResponse)
async def update_token(request: Request, db: db_session):
    jwt_token_crud = JWTTokenCRUD(db)

    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token not found in cookies',
        )

    try:
        payload = jwt_token_crud.decode_refresh_token(refresh_token)
        user_id = int(payload.get('sub'))
        session_id = payload.get('jti')

        if not user_id or not session_id:
            raise ValueError()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token payload',
        )

    token_record = await jwt_token_crud.get_refresh_token(session_id)

    incoming_hash = hash_token(refresh_token)

    if (
            not token_record
            or token_record.refresh_token_hash != incoming_hash
            or token_record.expires_at < datetime.now(timezone.utc)
    ):
        await jwt_token_crud.revoke_specific_token(user_id, session_id)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token expired or compromised',
        )

    new_access_token, expires_in = jwt_token_crud.create_access_token(user_id)
    new_refresh_token, new_session_id = jwt_token_crud.create_refresh_token(user_id)
    new_hashed_refresh = hash_token(new_refresh_token)

    await jwt_token_crud.revoke_specific_token(user_id, session_id)
    await jwt_token_crud.add_refresh_token(new_hashed_refresh, user_id, new_session_id)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error during rotation")

    response = JSONResponse(
        {
            'access_token': new_access_token,
            'token_type': 'bearer',
            'expires_in': expires_in,
        }
    )

    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        httponly=True,
        secure=False,  # True для HTTPS
        samesite='strict',
        path='/',
    )

    return response


@auth_router.post('/resend-verification', response_model=BaseResponse)
async def resend_verification(request: EmailOnlyRequest, db: db_session):
    user_crud = UserCRUD(db)
    var_token_crud = EmailVarCRUD(db)

    user = await user_crud.get_user(request.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    if user.account_status == AccountStatus.active:
        return JSONResponse(
            status_code=400,
            content={'details': 'This account is already verified.'}
        )

    new_token = generate_var_token(32)
    hash_new_token = hash_token(new_token)

    await var_token_crud.add_var_token(user.email, hash_new_token)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    sending_email_verification.delay(
        recipient_email=user.email,
        subject='Verification (Resend)',
        plain_content=
        'To verify your account, please click the link below\n'
        f'http://127.0.0.1:8000/verify_email/verify?token={new_token}',
    )

    return JSONResponse({'details': 'Verification email has been resent.'})


@auth_router.post('/logout')
async def logout(request: Request, db: db_session):
    jwt_token_crud = JWTTokenCRUD(db)
    refresh_token = request.cookies.get('refresh_token')
    print(f'refresh_token: {refresh_token}')

    if not refresh_token:
        return JSONResponse({"details": "Already logged out."})

    try:
        payload = jwt_token_crud.decode_refresh_token(refresh_token)
        user_id = int(payload.get('sub'))
        session_id = payload.get('jti')

        await jwt_token_crud.revoke_specific_token(user_id, session_id)
        await db.commit()
    except Exception as e:
        await db.rollback()
        pass

    response = JSONResponse({"details": "Successfully logged out."})

    response.delete_cookie(
        key='refresh_token',
        path='/',
        httponly=True,
        samesite='strict'
    )

    return response