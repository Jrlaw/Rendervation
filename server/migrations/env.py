"""Alembic's runner: on the connection server/migrate.py hands it. render_as_batch, since SQLite can
only change a table by copying it."""
from alembic import context

from server.db import Base

context.configure(connection=context.config.attributes["connection"], target_metadata=Base.metadata,
                  render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
