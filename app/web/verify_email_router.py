from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse
from app.schemas.response_shemas import BaseResponse
from app.utils.utils import hash_token, update_db
from app.main import var_token_crud, user_crud
from datetime import datetime, timezone

verify_email_router = APIRouter(prefix='verify_email', tags=['verify_email'])

@verify_email_router.post('/verify', response_model=BaseResponse)
async def verify_email(token: str = Query(...)):
    hashed_token = hash_token(token)

    token = await var_token_crud.check_exist_token(hashed_token)

    if (
        not token
        or token.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired verification token',
        )

    user = user_crud.get_user(token.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User not found for this verification token',
        )

    user.account_status = 'active'
    token.used = True

    await update_db([user, token], user_crud.db)

    return JSONResponse(
        {
            'details': f'user {user.email} has been successfully verified',
        }
    )