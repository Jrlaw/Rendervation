"""Shared dependencies: settings, a database session, and who's asking."""
from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_db(request: Request):
    db = request.app.state.sessions()
    try:
        yield db
    finally:
        db.close()


def current_user():
    """Who made an edit, for the change log. One local user for now; real sign-in replaces this."""
    return "local"
