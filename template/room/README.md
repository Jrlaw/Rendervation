# ROOM NAME

HOUSE · started DATE · status: intake

What the project is (keeping the room as is, a refresh, or a full remodel) and who it's for.

## Where things are

- `intake/`: photos, floor plan, measurements and notes about the room as it is today
  (`intake/README.md`).
- `selections.md`: every product and idea, chosen or not, with links.
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

    ./render.sh --cams photo1,plan --samples 24 --res 1000 --out /tmp/preview

Standard views, day and evening (`--night`):

    ./render.sh --cams photo1,plan --samples 64 --res 1600 --out renders/latest/day

As-is views, the "before" (PROCESS.md step 2; same cameras as the standard views):

    ./render.sh --design asis --cams photo1 --samples 64 --res 1600 --out renders/asis/day
    ./render.sh --design asis --night --cams photo1 --samples 64 --res 1600 --out renders/asis/night

Selections page (after editing `selections.md`; run from the repo root):

    python3 lib/tools/selections_page.py houses/<house>/rooms/<room>

Walkthrough model (after any change to the room):

    ./render.sh --export web

Then run `lib/serve.sh` from the repo root and open http://127.0.0.1:8000, or double-click
`web/index.html`.

Options: `--paint <name>` (see `lib/roomkit/materials.py` and `houses/catalog/materials.py`).

## Current state

- Modeled: (what's in the model so far)
- Open questions: (what's still a guess)
- Next: (the one next step)
