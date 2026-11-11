"""Kitchen layout: every dimension, in inches.

Plan coordinates: x runs east, y runs north, and the interior face of the north wall is y = 0,
so the room sits at negative y. Origin is the room's interior NW corner. "North" is the hall
end (the far doorway in photo 1); the range wall is west, the sink wall east, and the eat-in end
with the door to the living room is south.

Tag every number with where it came from:
  MEASURED    tape measure
  FROM PLAN   a listing plan, blueprint or scan
  FROM PHOTO  estimated from a photo against something of known size
  ASSUMED     a guess (standard size, or just a placeholder)
  DESIGN      a choice for the new design

No tape measure and no plan (intake/README.md): the sizes come from the two photos, scaled by a
30" range and 24" dishwasher, 36" counters and 80" doors, then checked by solving both photo
cameras from landmarks (camera_marks.py).

Main sizes use dimension(): they're listed in dimensions.json, shown in the walkthrough and
can be corrected there (a hand-set value overrides the default here).
"""
from roomkit.dimensions import dimension

CEILING = dimension("ceiling", 96, "photo", "floor to ceiling")
WALL_T = 4.5                  # ASSUMED interior wall (2x4 + drywall)

# --- Room -------------------------------------------------------------------------
ROOM_W = dimension("room_w", 116, "photo", "interior, east-west: two 25\" counters and a 5' aisle (camera solve)")
ROOM_D = dimension("room_d", 191, "photo", "interior, north-south: hall wall to the eat-in end's wall (camera solve)")

# --- Openings ---------------------------------------------------------------------
# wall: N, E, S or W. at: from the wall's left corner (as you face the wall from inside) to
# the edge of the opening, not the trim. Windows: sill = floor to the bottom of the opening.
WINDOWS = [
    dict(wall="E", at=38, width=30, sill=43, height=37),     # FROM PHOTO: over the sink, a single-hung; its casing stops under the soffit
    dict(wall="E", at=128, width=32, sill=36, height=48),    # FROM PHOTO: the eat-in end's window
]
DOORS = [
    dict(wall="N", at=38, width=30, height=80, door=False),  # FROM PHOTO: cased opening to the hall (camera solve)
    dict(wall="W", at=32, width=32, height=80, door=False),  # FROM PHOTO: to the living room, just south of the range
]                                                            # (the door standing in photo 2 is off its hinges)

# --- Range wall (west), measured south from the north wall ----------------------------------
FRIDGE_Y = 1.0                # FROM PHOTO: an inch off the north wall
FRIDGE = dict(width=30, depth=31, height=66)                  # FROM PHOTO: a white top-freezer
WEST_BASE = dimension("west_base", 63, "photo", "base cabinets between the fridge and the range (camera solve)")
WEST_FRONTS = [(33, "drawer_door"), (30, "drawer_doors2")]    # FROM PHOTO: the range hides most of them
RANGE_W = 30                  # FROM PHOTO: a standard 30" range
MICRO_Z = dimension("micro_z", 54, "photo", "floor to the over-the-range microwave's bottom")
WEST_UPPER = dict(y0=-32, y1=-93, z0=54, z1=84)               # FROM PHOTO: over the counter, fridge to range
SOFFIT = dict(depth=13, z=84)                                 # FROM PHOTO: drywall boxes over the uppers (none over
                                                              # the microwave: bare wall and an iron bracket, photo 1)

# --- Sink wall (east), measured south from the north wall -----------------------------------
# fronts as kitchen.base_run takes them: (width, kind)
EAST_BASE = [(15, "drawer_door"), (24, "gap"), (30, "drawer_doors2"), (14, "drawer_door"),
             (12, "drawer_door"), (11, "drawer_door")]            # FROM PHOTO: 106" in all (camera solve)
DISHWASHER_AT = 15            # FROM PHOTO: beside the corner base
SINK = dict(width=33, depth=22, center=dimension("sink_center", 55, "photo", "north wall to the sink's center"))
EAST_UPPERS = [dict(y0=0, y1=-35, z0=54, z1=84, doors="doors2"),
               dict(y0=-72, y1=-106, z0=54, z1=84, doors="doors2")]   # FROM PHOTO: either side of the window

# --- Counters ---------------------------------------------------------------------
COUNTER_H = 36.0              # ASSUMED standard
COUNTER_T = 1.5               # FROM PHOTO: post-formed laminate with a 4" back splash
COUNTER_D = 25.5
SPLASH = 4.0

# --- Ceiling lights (FROM PHOTO) ---------------------------------------------------------
LIGHTS = [
    dict(name="light_galley", x=58, y=-62, kind="flush_drum", d=12),
    dict(name="light_sink", x=97, y=-53, kind="flush_dome", d=9),
    dict(name="light_nook", x=58, y=-155, kind="semi_flush", d=15),
]

# --- New design (sizes from the spec sheets; selections.md has links and prices) ------------
# IKEA SEKTION cabinets with AXSTAD gray-green doors (14 7/8 x 29 7/8 x 3/4" for a 15x30" box),
# BAGGANAS brass knobs, KARLBY walnut counters (74 x 25 5/8 x 1 1/2"), Bedrosians Cloe white
# 2.5x8 back splash to the wall cabinets. SEKTION bases: 30" box on 4.5" legs, 1.5" top = 36".
NEW_COUNTER_T = 1.5           # KARLBY
NEW_COUNTER_D = 25.625
NEW_BOX_TOP = 34.5            # SEKTION 30" base + 4.5" legs
# sink run (east), from the north wall: the 36" sink base centered under the window
NEW_EAST_BASE = [(12, "door_l"), (24, "gap"), (36, "sink"), (18, "drawers3"), (15, "drawer_door"), (1, "filler")]   # 12": a full-height pull-out
NEW_DW_AT = 12                # Bosch 100 series SHE3AEM5N, 24" opening
NEW_SINK = dict(width=33, depth=22, bowls=1, bowl_d=10, center=54)   # Kraus Standart PRO KHT300-33 (bowl 31 x 18 x 10)
# range run (west): fridge, then 60" of base cabinets and a filler, the range and microwave stay
NEW_FRIDGE = dict(width=29.75, depth=34.5, height=66.375)    # GE GTS19KYNRFS, fingerprint-resistant stainless
NEW_WEST_BASE = [(24, "drawers3"), (36, "doors2"), (2.5, "filler")]   # 2 1/2" filler: the range moves 1/2" north, clear of
                                                                      # the living room door's casing (cabinet review)
# wall cabinets, SEKTION 30" high under the soffits, plus 30 x 15" over the fridge and the microwave. US SEKTION
# wall cabinets are 15" deep (a 14 3/4" box and the door), so the soffits are furred out to match (cabinet review)
NEW_WALL_D = 14.75
NEW_SOFFIT_D = 15.5
NEW_EAST_UPPERS = [dict(y0=-1.5, y1=-31.5, z0=54, z1=84, fronts=[(30, "doors2")], filler=(-31.5, -34), wall_filler=(0, -1.5)),
                   dict(y0=-72, y1=-105, z0=54, z1=84, fronts=[(18, "door_r"), (15, "door_l")], filler=None)]
NEW_WEST_UPPER = dict(y0=-33.5, y1=-93.5, z0=54, z1=84, fronts=[(30, "doors2"), (30, "doors2")], filler=(-31, -33.5))   # over the bases
NEW_FRIDGE_UPPER = dict(y0=-1, y1=-31, z0=69, z1=84)         # 30 x 15", 24" deep, flush with the fridge
# over the microwave: SEKTION 30 x 15" horizontal (a lift-up door), its bottom level with the fridge's, so
# the microwave drops 1 1/2" (top 69", GE: top at least 66" up, 16 1/2" over the cooktop). A drywall box
# above carries the soffit line across (designer and cabinet reviews)
NEW_MICRO_Z = 52.5
NEW_MICRO_UPPER = dict(z0=69, z1=84)
SPLASH_TOP = 54               # DESIGN: Cloe white to the wall cabinets
# lights: Halo HLB4LSFS5 4" canless wafers (as in the hall bath), 2700 K, down the aisle and in the eat-in end
NEW_CANS = [(58, -20), (58, -60), (58, -100)]
# the eat-in end: IKEA DOCKSTA 40 1/2" round table with a brass dome pendant over it, 32" above the top
# (designer review). Moved from the room's middle to the window: there it stood where photo 1 was taken and
# hid the galley; here it seats three and leaves 72" to the range wall
NEW_TABLE = dict(x=93, y=-148, d=40.5, h=29.125)
NEW_PENDANT = dict(d=18, bottom=61)
# IKEA MITTLED 24" strips under the wall cabinets (task light at the counters)
NEW_STRIPS = [("W", -36, -60), ("W", -66, -90), ("E", -4, -28), ("E", -76, -100)]
