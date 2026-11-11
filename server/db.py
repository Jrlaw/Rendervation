"""The database: SQLite through SQLAlchemy. It holds what's changed on the web; what a room *has*
(its designs, cameras, models, renders) stays in its files, and these tables record edits on top.

  design_settings  a design's label, place and hidden flag, where changed from the room's own list
  rooms            each room's chosen design
  changes          every edit: when, who, which room, what
  jobs             Blender work for the worker on this computer (lib/worker.py)
"""
import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class RoomRow(Base):
    __tablename__ = "rooms"
    room: Mapped[str] = mapped_column(String, primary_key=True)          # houses/<house>/rooms/<room>
    chosen: Mapped[str | None] = mapped_column(String, nullable=True)


class DesignSetting(Base):
    __tablename__ = "design_settings"
    room: Mapped[str] = mapped_column(String, primary_key=True)
    design: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)     # None: the room's own label
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None: the room's own order
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class Change(Base):
    __tablename__ = "changes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)
    user: Mapped[str] = mapped_column(String)
    room: Mapped[str] = mapped_column(String, index=True)
    what: Mapped[str] = mapped_column(String)                            # choose, hide, show, rename, status, dimension
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String)                            # export (quick, unbaked) or bake (~8 min)
    status: Mapped[str] = mapped_column(String, default="queued")        # queued, running, done, failed
    created: Mapped[datetime.datetime] = mapped_column(DateTime, default=now)
    started: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    finished: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    log: Mapped[str] = mapped_column(Text, default="")
    after: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)   # the export a bake follows


def connect(path):
    """An engine and session factory on the SQLite file at path, tables created if new."""
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _):
        conn.execute("PRAGMA journal_mode=WAL")    # pages read while the worker writes
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)
