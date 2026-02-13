from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.data.db_init import setup_db
from app.web.auth_router import auth_router
from app.web.verify_email_router import verify_email_router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await setup_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(verify_email_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)