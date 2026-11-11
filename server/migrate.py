"""Bring the database to the latest schema: Alembic migrations in server/migrations/versions, run on
every start. A schema change is a new file there (copy the newest and change it), plus its test in
server/tests/test_migrations.py."""
import os

from alembic import command
from alembic.config import Config

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")


def config(conn=None):
    cfg = Config()
    cfg.set_main_option("script_location", HERE)
    cfg.attributes["connection"] = conn
    return cfg


def upgrade(engine, to="head"):
    with engine.begin() as conn:
        command.upgrade(config(conn), to)
