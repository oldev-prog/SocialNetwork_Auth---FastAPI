from fastapi import FastAPI
from app.data.db_init import async_session_factory
from app.data.user_crud import UserCRUD
from app.data.email_var_crud import EmailVarCRUD
from app.login.jwt_token import JWTTokenCRUD

app = FastAPI()

db = async_session_factory()
user_crud = UserCRUD(db)
var_token_crud = EmailVarCRUD(db)
jwt_token_crud = JWTTokenCRUD(db)