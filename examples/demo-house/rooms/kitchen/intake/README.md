# Intake: Kitchen

The example kitchen has two photos and no tape measure. Every size comes from the photos,
scaled by things of known size, then checked by solving both cameras from landmarks
(`camera_marks.py`, `lib/tools/solve_cameras.py`).

## Photos

| Photo | What it shows |
|---|---|
| `nps-before-1.jpg` | From the eat-in end, looking north up the galley to the hall doorway: the fridge, range and microwave on the west wall, the sink under a window on the east wall, green walls and birch slab cabinets. Cut to 4:3 as `web/before/photo1.jpg`. |
| `nps-before-2.jpg` | From the hall doorway, looking south-east: the sink run, the eat-in end's window, and the door to the living room (off its hinges, leaning in the opening). Cut to 4:3 as `web/before/photo2.jpg`. |
| `after/nps-after-1.jpg`, `after/nps-after-2.jpg` | The park service's own remodel, kept for reference only. The new design here is ours. |

**Source:** "Housing improvement goal 2- kitchen (before 1, before 2, after 1, after 2)",
Yellowstone National Park (NPS / Jacob W. Frank), July and September 2025. Public domain (a work
of the U.S. federal government). Canon EOS R5 Mark II, RF 15-35mm at 15mm.

- https://commons.wikimedia.org/wiki/File:Housing_improvement_goal_2-_kitchen_(before_1)_(54959496127).jpg
- https://commons.wikimedia.org/wiki/File:Housing_improvement_goal_2-_kitchen_(before_2)_(54960632419).jpg
- https://commons.wikimedia.org/wiki/File:Housing_improvement_goal_2-_kitchen_(after_1)_(54960685630).jpg
- https://commons.wikimedia.org/wiki/File:Housing_improvement_goal_2-_kitchen_(after_2)_(54960558563).jpg

## Measurements

All FROM PHOTO, in inches. The scale comes from a 30" range, a 24" dishwasher, 36" counters and
80" doors; the camera solve settled the room's length and width.

| What | Measurement | How |
|---|---|---|
| Ceiling height | 96 | guess (8 ft) |
| Room, east-west | 116 | camera solve: two 25" counters and a 5' aisle |
| Room, north-south | 191 | camera solve |
| Hall doorway (north wall) | 30 x 80, 38 from the west wall | photo |
| Living room door (west wall) | 32 x 80, 32 from the south-west corner | photo |
| Sink window (east wall) | 30 W x 37 H, sill at 43, 38 from the north wall | photo |
| Eat-in window (east wall) | 32 W x 48 H, sill at 36, 128 from the north wall | photo |
| Fridge | 30 W x 31 D x 66 H, 1 off the north wall | photo |
| Base run, fridge to range | 63 | camera solve |
| Sink run | 106, sink centered 55 from the north wall | camera solve |
| Wall cabinets | 54 to 84, under a 13" deep soffit | photo |

## Notes

- North is the hall end (the far doorway in photo 1). The range wall is west, the sink wall east.
- The range and over-the-range microwave stay in the new design; everything else is replaced.
- The door leaning in the living room doorway in photo 2 isn't hung, so the opening is modeled
  cased with no door.
