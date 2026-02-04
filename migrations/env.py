from logging.config import fileConfig
from pathlib import Path
import os

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load .env from project root (same folder as alembic.ini)
ROOT_DIR = Path(__file__).resolve().parents[1]  # ...\backend\garage
load_dotenv(ROOT_DIR / ".env")

# IMPORTANT: import the Base that your models use
from models import Base  # change to: from app.models import Base  if needed

# ✅ DO NOT SET THIS TO NONE ANYWHERE
target_metadata = Base.metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL missing (.env) and sqlalchemy.url missing (alembic.ini)")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        compare_type=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
