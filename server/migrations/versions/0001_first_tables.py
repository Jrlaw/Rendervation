"""The first tables: rooms (the chosen design), design_settings, changes, jobs.

Databases made before migrations (2026-11-11, by create_all) already have them, so each is made only
if it's missing."""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    have = set(sa.inspect(op.get_bind()).get_table_names())
    if "rooms" not in have:
        op.create_table("rooms",
                        sa.Column("room", sa.String, primary_key=True),
                        sa.Column("chosen", sa.String, nullable=True))
    if "design_settings" not in have:
        op.create_table("design_settings",
                        sa.Column("room", sa.String, primary_key=True),
                        sa.Column("design", sa.String, primary_key=True),
                        sa.Column("label", sa.String, nullable=True),
                        sa.Column("position", sa.Integer, nullable=True),
                        sa.Column("hidden", sa.Boolean, nullable=False))
    if "changes" not in have:
        op.create_table("changes",
                        sa.Column("id", sa.Integer, primary_key=True),
                        sa.Column("at", sa.DateTime, nullable=False),
                        sa.Column("user", sa.String, nullable=False),
                        sa.Column("room", sa.String, nullable=False, index=True),
                        sa.Column("what", sa.String, nullable=False),
                        sa.Column("detail", sa.JSON, nullable=False))
    if "jobs" not in have:
        op.create_table("jobs",
                        sa.Column("id", sa.Integer, primary_key=True),
                        sa.Column("room", sa.String, nullable=False, index=True),
                        sa.Column("kind", sa.String, nullable=False),
                        sa.Column("status", sa.String, nullable=False),
                        sa.Column("created", sa.DateTime, nullable=False),
                        sa.Column("started", sa.DateTime, nullable=True),
                        sa.Column("finished", sa.DateTime, nullable=True),
                        sa.Column("seconds", sa.Float, nullable=True),
                        sa.Column("log", sa.Text, nullable=False),
                        sa.Column("after", sa.Integer, sa.ForeignKey("jobs.id"), nullable=True))
