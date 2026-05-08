from fastapi import APIRouter
from fastapi_users import FastAPIUsers

from app.auth.auth import auth_backend
from app.auth.manager import get_user_manager
from app.auth.user import User
import uuid
from app.schemas.user import UserCreate, UserRead, UserUpdate

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

current_active_user = fastapi_users.current_user(active=True)