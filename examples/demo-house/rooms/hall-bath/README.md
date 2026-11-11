# Hall bath

Demo house · started 2026-10-29 · status: design chosen, walkthrough built

The repo's worked example. A 1950s-style hall bath (green 4-1/4" tile, a wall-hung sink, a
bone toilet) modeled from **one public-domain photo** with no tape measure, then redesigned
with real, buyable products: a 30" gray vanity, an oval mirror, a new two-piece toilet,
glossy Cloe subway tile (green, the nod to the original) and a Carrara marble hex floor. The
tub stays. A lighting designer (the `trades` agent) then reviewed it and added the lighting:
three wet-rated wafers, a vanity bar and an exhaust fan. Then the `checker` agent went over
the model and caught what was missing or wrong: no tub and shower trim, tile running behind the
window, a vanity deep enough to block the door, and towels and the paper holder in the wrong
places.

Every step here was done by Claude Code in a single session, the same way it runs any room
(see `PROCESS.md` at the repo root).

## Where things are

- `intake/`: the photo, where it came from, and the sizes read off it (`intake/README.md`);
  `intake/products/` has the saved product photos.
- `selections.md`: every product, chosen or not, with links and prices.
- `inventory.json`: the products to buy, per design, and where each is in the model.
- `layout.py`: every dimension (inches), each tagged MEASURED / FROM PLAN / FROM PHOTO / ASSUMED
  / DESIGN.
- `room.py`: builds the room in Blender from `layout.py` and `lib/roomkit`.
- `textures/`: the Carrara hex floor texture.
- `renders/latest/day`, `renders/latest/night`: the new design; `renders/options/as-is` (the
  room as it is) and `renders/options/tile/` (the three Cloe colors, with `compare.jpg`).
- `web/`: the walkthrough (`index.html`), with the as-is room and every tile color in the
  design picker; `web/before/` holds the photo the renders are compared with.

The renders and the baked walkthrough are committed, so the example works from a fresh clone.
Rebuilding them all ("render the example") takes about an hour on a mid-range GPU, most of it
baking the four walkthrough designs.

## Commands (Claude runs these)

Room as it is, matched against the photo:

    ./render.sh --design before --cams photo1 --samples 24 --res 1000 --out /tmp/check

Check the model first (seconds; prints any problems):

    ./render.sh --check
    ./render.sh --check --design before

Standard views, day and evening (`--night`):

    ./render.sh --cams photo1,vanity,tub --samples 64 --res 1600 --out renders/latest/day

Plan view (for the Plans page):

    ./render.sh --cams plan --samples 64 --res 1600 --out renders/latest

Tile options:

    ./render.sh --tile-color cloebabyblue --cams photo1,vanity --out renders/options/tile/cloebabyblue

Walkthrough model, with the Cycles lighting baked in, plus the other designs:

    ./render.sh --export web --bake
    ./render.sh --export web/variants/before --design before --bake

Options: `--design before|new`, `--tile-color cloegreen|cloebabyblue|cloepink`, `--paint <name>`.

## Current state

- Modeled: the room as it is (checked against the photo) and the new design, with every
  product from its spec sheet.
- Open questions: every size is FROM PHOTO. A real job would tape the room's depth first: the
  vanity needs the 31" between the stub wall and the south wall. Where the heat comes from.
- Reviews: lighting designer (2026-10-29): adopted, see "Lighting, fan and switches" in
  `selections.md`. Checker (2026-10-29): adopted. It added the Delta tub and shower set, cut
  the tile around the window, moved the window 1" so its casing clears the east wall, and
  swapped in the shallower Shaila vanity so the door clears it. It also moved the towels and
  paper holder, lowered the curtain, and made the faucet nickel. In the shared parts, it put the
  old wall-hung sink's faucet back on the sink. `./render.sh --check` is clean for both
  designs.
- Next: pick a 4" centerset faucet (the model uses a generic one), and settle where the switches
  go.
