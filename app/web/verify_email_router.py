from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from app.schemas.response_shemas import BaseResponse
from app.utils.utils import hash_token, update_db
from datetime import datetime, timezone
from app.dependencies.db_dependencies import db_session
from app.data.email_var_crud import EmailVarCRUD
from app.data.user_crud import UserCRUD

verify_email_router = APIRouter(prefix='/verify_email', tags=['verify_email'])

@verify_email_router.get('/verify', response_model=BaseResponse)
async def verify_email(db: db_session, token: str = Query(...)):
    print('start verify')

    hashed_token = hash_token(token)

    var_token_crud = EmailVarCRUD(db)
    user_crud = UserCRUD(db)

    token_record = await var_token_crud.check_exist_token(hashed_token)

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid token")

    if token_record.used:
        raise HTTPException(status_code=400, detail="Token already used")

    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")

    user = await user_crud.get_user(token_record.user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.account_status = 'active'
        token_record.used = True

        await update_db([user, token_record], user_crud.db)

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal database error")

    # return JSONResponse({"details": f"User {user.email} verified successfully"})
    return RedirectResponse(url="http://localhost:5173/verification-success")