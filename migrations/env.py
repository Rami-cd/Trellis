import asyncio
import selectors
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.db.connection import Base
from app.auth.user import User
from app.auth.user import User
from app.models.repository import Repository, RepositoryLanguage
from app.models.code import CodeNode, CodeEdge, CodeEmbedding
from app.models.session import Session
from app.models.conversation import Conversation, Message
from app.models.job import IndexingJob

load_dotenv()

# sql/init.sql
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL must be set in the environment.")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(get_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_async_migrations():
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    loop.run_until_complete(run_migrations_online())
    loop.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async_migrations()