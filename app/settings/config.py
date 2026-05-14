import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def _load_yaml_config() -> dict:
    config_path = Path(__file__).with_name("config.yaml")
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}


CONFIG = _load_yaml_config()
LLM_CONFIG = CONFIG.get("llm", {})

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY") or ""
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

if not AUTH_SECRET_KEY:
    raise ValueError("AUTH_SECRET_KEY must be set in the environment.")

if not ACCESS_TOKEN_EXPIRE_MINUTES:
    raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be set in the environment.")

AUTH_SECRET_KEY: str = AUTH_SECRET_KEY