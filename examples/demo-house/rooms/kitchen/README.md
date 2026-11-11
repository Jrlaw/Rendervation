# Kitchen

Demo house · started 2026-11-11 · status: example, designed and rendered

An example room: a 1960s galley kitchen with an eat-in end, modeled from two public-domain
National Park Service photos (`intake/README.md`), with a full remodel designed around real
products: IKEA gray-green shaker cabinets, walnut counters, brass knobs, a white Cloé back
splash and stainless appliances. The range and microwave stay.

## Where things are

- `intake/`: photos, floor plan, measurements and notes about the room as it is today
  (`intake/README.md`).
- `selections.md`: what's current, per design option. `selections-history.md`: the log, with options passed on.
- `inventory.json`: the products to buy, each with have / ordered / need and where it is in the model.
- `layout.py`: every dimension (inches), each tagged MEASURED / FROM PLAN / FROM PHOTO / ASSUMED.
- `room.py`: builds the room in Blender from `layout.py` and `lib/roomkit`.
- `textures/`: product textures cut from photos.
- `renders/asis/day`, `renders/asis/night`: the room as it is today (always kept, PROCESS.md step 2);
  `renders/latest/day`, `renders/latest/night`: the standard views of the current design;
  `renders/options/`: option sets that were compared.
- `web/`: the walkthrough (`index.html`) and its exported model; `web/before/` holds the photos
  the renders are compared with.

## Commands (Claude runs these)

Quick preview (about 30 seconds on the GPU):

    ./render.sh --design new --cams photo1,plan --samples 24 --res 1000 --out /tmp/preview

Standard views, day and evening (`--night`):

    ./render.sh --design new --cams photo1,photo2,sink --samples 64 --res 1600 --out renders/latest/day
    ./render.sh --design new --cams plan --samples 32 --res 1600 --out renders/latest

As-is views, the "before" (PROCESS.md step 2; same cameras as the standard views):

    ./render.sh --design asis --cams photo1,photo2,sink --samples 64 --res 1600 --out renders/asis/day
    ./render.sh --design asis --night --cams photo1,photo2,sink --samples 64 --res 1600 --out renders/asis/night

Selections page and the walkthrough's product list (after editing `selections.md` or `inventory.json`; run from
the repo root):

    python3 lib/tools/selections_page.py examples/demo-house/rooms/kitchen

Walkthrough models (after any change to the room): As it is is the room's own export, the new
design a variant.

    ./render.sh --design asis --export web --bake
    ./render.sh --design new --export web/variants/new --bake

Then run `lib/serve.sh` from the repo root and open http://127.0.0.1:8000, or double-click
`web/index.html`.

Options: `--design asis|new`, `--paint <name>` (see `lib/roomkit/materials.py` and `houses/catalog/materials.py`).

## Current state

- Modeled: the room as it is (matches both photos; no soffit over the microwave) and the new
  design, both checked with `./render.sh --check`, rendered day and evening, and baked into the
  walkthrough.
- Reviews: designer and cabinet designer, 2026-11-11, on the new design. Adopted most of both; what
  was passed on and why is in `selections-history.md`.
- Open questions: every size is from the photos; the Kraus sink may be discontinued; chairs.
- Next: nothing; it's an example. A real room would tape the room, the sink window and the
  microwave next.
