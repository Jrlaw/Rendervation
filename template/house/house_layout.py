"""HOUSE NAME: every room, as outlines in house coordinates.

The source for the whole-house map (web/index.html). Rebuild the map's data after changing
this file (from the repo root):

    python3 lib/tools/house_map.py houses/<house>

Units are inches. House coordinates: x runs east, y runs north, z up, with the origin at one
room's interior NW corner (everything south of it has negative y). With a listing plan, trace
outlines in plan-image pixels with px() and list the image in PLANS so it can be drawn under
the map to check them; without one, give outlines in inches.
"""

PX_PER_IN = 2.0                   # plan image scale (set from a room with a known size)
ORIGIN_PX = (0, 0)                # house origin, in plan-image pixels

CEILING = 96                      # ASSUMED 8 ft
WALL_T = 4.5                      # interior walls (2x4 + drywall)
EXT_WALL_T = 7.0                  # exterior walls


def px(points):
    """Plan-image pixels -> house inches (x east, y north)."""
    return [(round((x - ORIGIN_PX[0]) / PX_PER_IN, 1), round(-(y - ORIGIN_PX[1]) / PX_PER_IN, 1))
            for x, y in points]


def rect(x0, y0, x1, y1):
    """A rectangle in house inches, from its NW corner (x0, y0) to its SE corner (x1, y1)."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


FLOORS = [
    # name, floor level z (inches), ceiling height
    dict(id="1st", name="1st floor", z=0, ceiling=CEILING),
]

# Each room: id (the folder name it gets under rooms/ when it's started), name, floor,
# listed size, kind (room / closet / stairs / feature) and its outline.
# `folder` is set once the room exists under rooms/; `seen_in` names a modeled room it shows up in.
ROOMS = [
    dict(id="kitchen", name="Kitchen", floor="1st", listed="12'0\" x 10'0\"",
         outline=rect(0, 0, 144, -120)),
    dict(id="dining-room", name="Dining room", floor="1st", listed="12'0\" x 12'0\"",
         outline=rect(148.5, 0, 292.5, -144)),
]

# Listing plans, drawn under the map to check the outlines, for example:
#   "1st": dict(image="intake/plan-1st.png", size_px=(1600, 1000), shift_px=0),
PLANS = {}

# Where each modeled room's own coordinates sit in the house: origin = the room's plan (0, 0) in house inches,
# rotation in degrees (counter-clockwise), floor, and the design its neighbors show (the chosen one, else "asis";
# `flags` = the room.py flags that build it, when they aren't --design <id>). The walkthroughs and the renders
# show the other modeled rooms on a floor around each room from here (PROCESS.md, "Houses"). For example:
#   "kitchen": dict(origin=(0, 0), rot=0, floor="1st", design="asis"),
#   "dining-room": dict(origin=(148.5, 0), rot=0, floor="1st", design="b", flags=["--design", "b"]),
PLACEMENTS = {}
