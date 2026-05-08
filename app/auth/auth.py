from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from app.settings.config import AUTH_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

bearer_transport = BearerTransport(tokenUrl="auth/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=AUTH_SECRET_KEY,
        lifetime_seconds=ACCESS_TOKEN_EXPIRE_MINUTES,
    )

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)