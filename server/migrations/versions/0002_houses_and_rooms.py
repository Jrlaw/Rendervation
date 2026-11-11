"""Houses and rooms in the database: a houses table, and each room's house, name, card text, place,
hidden and missing flags. They're filled from the folders (and, once, the old houses/index.html) by
server/catalog.py on start."""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("houses",
                    sa.Column("house", sa.String, primary_key=True),
                    sa.Column("name", sa.String, nullable=False),
                    sa.Column("blurb", sa.String, nullable=True),
                    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
                    sa.Column("missing", sa.Boolean, nullable=False, server_default=sa.false()))
    with op.batch_alter_table("rooms") as t:
        t.add_column(sa.Column("house", sa.String, nullable=True))
        t.add_column(sa.Column("name", sa.String, nullable=True))
        t.add_column(sa.Column("blurb", sa.String, nullable=True))
        t.add_column(sa.Column("position", sa.Integer, nullable=True))
        t.add_column(sa.Column("hidden", sa.Boolean, nullable=False, server_default=sa.false()))
        t.add_column(sa.Column("missing", sa.Boolean, nullable=False, server_default=sa.false()))
