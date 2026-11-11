"""One module per feature, each with its own router; server.app registers every module in FEATURES."""
from . import designs, dimensions, inventory, jobs

FEATURES = [designs, inventory, dimensions, jobs]
