from alembic import command
from alembic.config import Config
from pathlib import Path

from config import settings


def run_migrations() -> None:
    # Look for alembic.ini in project root (parent of services directory)
    current_file = Path(__file__).resolve()
    project_root = (
        current_file.parent.parent.parent
    )  # Go up from ingestion -> services -> project root
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        # Fallback: look in current directory
        alembic_ini = current_file.with_name("alembic.ini")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)
    command.upgrade(cfg, "head")
