from alembic import command
from alembic.config import Config
from pathlib import Path

from config import settings


def run_migrations() -> None:
    alembic_ini = Path(__file__).with_name("alembic.ini")
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)
    command.upgrade(cfg, "head")
