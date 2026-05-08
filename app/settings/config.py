import os
from dotenv import load_dotenv

load_dotenv()

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY") or ""
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

if not AUTH_SECRET_KEY:
    raise ValueError("AUTH_SECRET_KEY must be set in the environment.")

if not ACCESS_TOKEN_EXPIRE_MINUTES:
    raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be set in the environment.")

AUTH_SECRET_KEY: str = AUTH_SECRET_KEY