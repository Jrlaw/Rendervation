"""Where things are, from the environment, so the same code runs on this computer, in the container
and in the tests:

  HR_ROOT  the content: houses/, examples/, lib/web/ (default: this repo)
  HR_DB    the SQLite file (default: $HR_ROOT/data/home-render.db)
  HR_TOOLS lib/tools, for the page builders the server runs (default: this repo's)
"""
import os
from dataclasses import dataclass

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass(frozen=True)
class Settings:
    root: str
    db: str
    tools: str

    @property
    def data(self):   # the database's folder; the worker's token lives there too
        return os.path.dirname(self.db)


def from_env():
    root = os.path.abspath(os.environ.get("HR_ROOT", REPO))
    return Settings(root=root,
                    db=os.path.abspath(os.environ.get("HR_DB", os.path.join(root, "data", "home-render.db"))),
                    tools=os.path.abspath(os.environ.get("HR_TOOLS", os.path.join(REPO, "lib", "tools"))))
