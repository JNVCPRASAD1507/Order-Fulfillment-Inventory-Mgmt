from logging.config import fileConfig
from pathlib import Path
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context


# =========================================================
# Python path
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# =========================================================
# Application imports
# =========================================================

from app.core.config import settings
from app.db.session import Base

# IMPORTANT:
# Import the module containing all SQLAlchemy models.
# This registers all models with Base.metadata.
from app.models import entities  # noqa: F401


# =========================================================
# Alembic configuration
# =========================================================

config = context.config


# Use database URL from application settings
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)


# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# SQLAlchemy metadata
target_metadata = Base.metadata


# =========================================================
# Offline migrations
# =========================================================

def run_migrations_offline() -> None:

    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# Online migrations
# =========================================================

def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
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


# =========================================================
# Execute migration
# =========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
    
    