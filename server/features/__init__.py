"""One module per feature, each with its own router; server.app registers every module in FEATURES.
designs before houses: PATCH /api/rooms/{room}/designs/{design} has to match before PATCH /api/rooms/{room}."""
from . import designs, dimensions, houses, inventory, jobs

FEATURES = [designs, houses, inventory, dimensions, jobs]
