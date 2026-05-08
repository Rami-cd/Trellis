import uuid
import logging
from fastapi import Depends
from fastapi_users import BaseUserManager, UUIDIDMixin
from app.auth.user import User
from app.auth.database import get_user_db
from app.settings.config import AUTH_SECRET_KEY

logger = logging.getLogger(__name__)

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = AUTH_SECRET_KEY
    verification_token_secret = AUTH_SECRET_KEY

    async def on_after_register(self, user: User, request=None):
        logger.info("User registered: %s", user.email)

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        logger.info("Password reset requested for: %s, token: %s", user.email, token)

    async def on_after_request_verify(self, user: User, token: str, request=None):
        logger.info("Verification requested for: %s, token: %s", user.email, token)

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)