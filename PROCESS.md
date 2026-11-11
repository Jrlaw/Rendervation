# How a room gets modeled

The steps every room follows, from "new room" to a walkthrough, written down so any room, in
any house, goes the same way. Claude follows this file. Saying "new room: <house>, <room>" in a Claude Code
session in this folder starts it.

Rooms stand alone. A house is just the folder its rooms share, and rooms get placed relative
to each other only when two that touch both exist (see "Houses" below). Nothing has to be done
in order, and a room can stop at any step.

## 0. Start the room

1. Copy `template/room/` to `houses/<house>/rooms/<room>/`. Use short lowercase names with
   dashes, for example `houses/ours/rooms/main-bath`. `houses/` is the person's own private
   repo (`houses/README.md`); if it doesn't exist yet, create it there and copy
   `template/home.html` to `houses/index.html`.
2. If the house is new, copy `template/house/` to `houses/<house>/` and fill in `house.md`
   (the map in `house_layout.py` is optional).
3. Add the room to `houses/<house>/house.md` and to the home page (`houses/index.html`).
   If the house has a map (`house_layout.py`), set `folder=` on the room's entry and rebuild it.
4. Fill in the room's README header: house, start date, status, what the project is.
5. Give the person the shot list and measurement sheet from `intake/README.md` in chat. Keep it
   short, and point out the "no floor plan" option.
6. If the person keeps a project tracker, add the room to it with a one-line next step.

## 1. Intake

Collect the room as it is today in `intake/`:

- **Photos.** Copy the originals in, convert HEIC with `lib/tools/heic2jpg.sh`, look at every one,
  and list them in the table in `intake/README.md` (photo → what it shows).
- **Measurements.** Record them in the measurements table, each with where it came from.
- **Floor plan.** A listing plan, a blueprint, or a room-scan export, if there is one.
- **No plan at all?** Ask for the ceiling height, the room's length and width, and one door or
  window. Estimate the rest from the photos, using a tape measure in the shot and standard sizes
  (80" doors, 4.5" outlet covers, 34–36" counters, known tile sizes). Mark those values
  FROM PHOTO.

Then ask questions. Ask about anything the photos don't settle: which way doors swing, what's
behind a wall, what stays, which wall is "north", things that look odd. Ask a few at a time,
numbered, and record the answers under "Notes from the walkthrough".

## 2. Model the room as it is

1. Put every dimension in `layout.py`, each tagged **MEASURED / FROM PLAN / FROM PHOTO / ASSUMED**.
   Declare the main sizes (wall lengths, room depths, anything someone may tape-measure) with
   `dimension(name, default, src, note)` from `roomkit.dimensions`, and draw each with
   `dim(a, b, src, key=name)` in `room.py`. They land in the room's `dimensions.json`, the
   standard size sheet for every room, and show in the walkthrough (Dimensions button, or hover
   a wall). A value corrected there, or typed into the walkthrough with `lib/serve.sh` running,
   overrides the default in `layout.py`.
2. Build `room.py`. Start from the template's box room. Reuse the `lib/roomkit` parts (doors,
   cased openings, outlets and switches, registers, cans, wainscot, shelves, generic toilets,
   vanities, tubs and mirrors) and the products already in the person's catalog
   (`houses/catalog/`). Where new code goes:
   - **A specific product** (a particular vanity, toilet or tub model): `houses/catalog/parts.py`,
     so the person's other rooms can use it.
   - **A one-off** (this room's soffit, an odd closet): the room's own `room.py`.
   - **Something general** that's missing from `lib/roomkit` (a new kind of part, a fix): change
     `lib/` only for that, and offer it back as a PR to the toolkit repo.
3. Add a camera for each intake photo (`photo1`, `photo2`, …) and move it until the render
   lines up with the photo. Put the converted photos in `web/before/photoN.jpg`.
4. **Check against the photos.** Render each photo view (`--samples 24 --res 1000`) and compare
   it with the photo side by side. Anything that doesn't line up is a wrong number. Fix it, or
   ask for one specific measurement ("corner to the window trim, please"). A wide side-by-side
   hides misplaced fixtures, so also crop in on each fixture (faucet, towel bar, light, mirror) in
   **every** photo that shows it, and take its position and finish from those crops.
5. Show the person the side-by-side comparisons. Stop here if that's all they wanted.
6. **Save the as-is renders. Every room, every time, before any design work.** They're the "before"
   of the project, and the photos can't stand in for them: photos have clutter, odd angles and
   their own lighting. The as-is scene stays buildable for the life of the room with
   `./render.sh --design asis`. Usually that's a `DESIGN` switch in `room.py`; if most of the room
   changes, keep it in its own `asis.py` that `room.py` hands off to. Render the standard views,
   day and evening, to `renders/asis/day/` and `renders/asis/night/`, with `renders/asis/plan.jpg`
   and the overview sheets (`lib/tools/overview.sh`). Bake it into the walkthrough too, so it's a
   pill in the design picker: `./render.sh --design asis --export web --bake`, listed first
   as `["asis", "As it is"]` in `variants` in `web/index.html`, so it's the leftmost pill and opens by default. Redo all of it if the as-is model
   changes.

### Fidelity standard

The goal is a render you could mistake for the photo from the same spot, in every room. A rough
blockout is fine as a first pass, but a room isn't finished while any of these stand in for the real thing:

- **Trim and millwork:** real profiles swept along their path (casing, crown, base, cap, door panels),
  not stacked boxes. Take the profile from a crop.
- **Materials:** wood, floors and other figured surfaces use textures cut from the room's own photos
  (squared up and color-matched), not generated stripes. Check color and gloss under the photo's lighting.
- **Objects:** furniture, fixtures and hardware get their real shape and details. A plain box or cylinder
  is a placeholder; list every one left in the README's "Current state" so none is mistaken for done.
- **Lens and position:** use the photo's EXIF focal length for its camera, and compare under the same
  lighting as the photo (an evening photo against the `--night` render). Solve the camera from landmarks
  with `lib/tools/solve_cameras.py`; a mark error above about 20 px at 1600 px wide means a dimension is off.

Tools: `lib/roomkit/millwork.py` (profiles, `sweep`, `plan_sweep`, `lathe`) and `lib/tools/photo_texture.py`
(square up a piece of a photo).

## 3. Ideas and selections

Whenever a product link, screenshot or idea comes in, or Claude suggests one:

1. **Record it in `selections.md` first**, before modeling it: status, link, price, specs, and
   who suggested it. Save the product photo to `intake/products/`, since links break and some
   sites block downloads (ask for a saved page or a direct image link then).
2. **Model it.** Sizes come from the spec sheet. Colors and textures are measured from the
   product photos (`textures/`). New paint and tile colors go in the person's catalog,
   `houses/catalog/materials.py`, and the product itself in `houses/catalog/parts.py` if it
   needs its own model.
3. **Options get a command-line switch** (`--tile-color sage`) so they can be rendered side
   by side. Option sets go in `renders/options/<topic>/`, with a labeled comparison sheet
   (`magick montage`).
4. **When something is picked**, update its status in `selections.md`, make it the default in
   `room.py` with a `# chosen: … (date)` comment, and note what was passed on and why.

**Products go in `inventory.json`** too, once picked: name, qty, price, link, a spec line, a picture
(`image` from `intake/products/`, or a CSS `swatch`), status (`have`, `ordered`, `need`), and `where`: the
model's object names (or name prefixes) it is. That one file drives the Selections checklist (filtered by
design and status, with Show in 3D) and the walkthrough's sidebar, which lists what's in the design on show
and outlines a product when you pick it. `selections.md` stays as the design notes, folded under the checklist.
After any change to either, rebuild:
`python3 lib/tools/selections_page.py houses/<house>/rooms/<room>` (writes `web/selections.html` and `web/inventory.js`).

Never drop an option silently, but keep `selections.md` to what's current: passed-on options and
the running log go in `selections-history.md` beside it. With several design options, give each its own
view: a `<!-- options: id=Label | id=Label -->` line and `<!-- only: id id -->` on section headings.

### Experts: trades reviews, the designer and the checker

Three agents in `.claude/agents/` help here. They read and search, never edit; Claude decides
with the person what to adopt, logs it in `selections.md` (crediting the review), and models it.

- **`designer`** sources real products from the person's style, wants and budget, checked
  against the room's dimensions. Use it when a selection is open or the person describes a look.
- **`trades`** reviews the room as one trade (lighting designer, electrician, cabinet designer,
  plumber, tile setter, general contractor, interior designer) and returns ranked fixes with
  plan coordinates, products, and what to measure first.
- **`checker`** checks the model itself: what's missing for the room type (a tub with no valve
  or shower head, no paper holder), what's built wrong (tile across a window, a fixture in a
  wall or the door opening), and where `room.py` and `selections.md` disagree. It runs the
  geometry check (`./render.sh --check`) and looks at the renders.

Start them in the background, telling each the room folder, the trade or what to source, and
what the person wants. **Offer one** (a one-line question, never run unasked) at these points:

1. After the as-is model checks out: a general contractor or interior designer, for what's
   worth changing and what's risky.
2. When a part of the design settles: the matching trade (cabinets → cabinet designer, a
   vanity or toilet → plumber, tile → tile setter, lights → lighting designer or electrician).
   A room with no planned lighting always gets the lighting offer.
3. When a selection is still open, or the person describes a style: the designer.
4. Before stopping a session in which the design changed: one review by the trade most
   affected, unless it was already done for this version.
5. Before the final renders and the bake (they take minutes): the checker. Also right after the
   as-is model, together with offer 1.

Note each review in the room README's "Current state" (trade, date, adopted or not), so it
isn't offered twice for the same design.

## 4. Standard renders and the walkthrough

- **Check first.** `./render.sh --check` builds the room and lists, in seconds, anything that
  crosses a door or window, sits inside something else, or floats. Run it after every change
  to `room.py` and fix what it finds before rendering; a finding that's deliberate gets a
  comment in `room.py` saying so.
- `renders/latest/day/` and `renders/latest/night/`: the standard views of the current
  design, refreshed whenever a choice changes. Render on the GPU (automatic) and give ETAs
  (for reference, about 35 s per 1600 px / 64-sample view on a mid-range GPU; time the first
  one on a new machine).
- `renders/asis/`: the same views of the room as it is today (step 2). When a view is added to the
  standard set, render it from the as-is model too, so every "after" has a "before" from the same
  spot. If a camera lands inside a wall that hasn't moved yet, nudge the as-is camera and say so
  in a comment.
- `./render.sh --design asis --export web` re-exports the walkthrough's as-is model (seconds, live lighting);
  add `--bake` (~8 min, GPU) to bake the Cycles lighting into it so it looks like the renders.
  Other designs go to `web/variants/<id>/` (same command plus the design's flags) and appear in
  the walkthrough's design picker once listed in `variants` in `web/index.html` (and in `designs` in
  `inventory.json`). Then rebuild the Selections page so each product knows which designs it's in.
- **Each design's pictures sit next to its model**: `web/renders` for the room's own export (the first
  pill) and `web/variants/<id>/renders` for the rest, each a symlink into `renders/` (`../renders/asis`
  when the first pill is As it is; the chosen design's is `renders/latest`). The Before / after,
  Renders and Plans tabs read them, with the same design pills as the walkthrough; a camera a design
  has no render for is left out. Every design needs `plan.jpg` there (`--cams plan`) for the Plans tab.
  Keep the exact flags behind each design's renders in the README's commands, so a re-render matches
  the bake.
- **Choosing and hiding designs** on the web (`lib/serve.sh` running): the walkthrough's "Make this
  the choice" button and "Hide" next to it are kept in the server's database (docs/backend.md), not in
  the room's files. The walkthrough, Before / after, Renders and Plans open on the chosen design and leave
  hidden ones out; the home page's card for the room shows `web/cards/<id>.jpg` (800 px, made from the
  design's first camera render, or from the 3D view, the first time it's chosen). Record the choice in
  `selections.md` too. A design to drop for good: hide it on the web, and delete its files only when
  asked.
- **Server changes:** run `server/test.sh` before and after; the pre-commit hook runs it too. New
  editable things get a module in `server/features/` and tests in `server/tests/`.
- **Plans page** (`web/plans.html`): the top-down render (`--cams plan`) with
  the cans and the dimension lines from `core.dim(...)` calls in `room.py`, each tagged measured /
  plan / photo / design / assumed. Add a `dim` for every measurement that comes in, and re-export.
  It's also the check that the model matches what was measured. `window.PLANS = { designs }` in
  the page lists the same designs as the walkthrough's `variants`. A room with its own plan
  drawings (a track plan, say) links them as Room / Track pills above the plan.
- **Tabs are the same in every room:** Walk through, Before / after, Renders, Plans, Selections, and,
  only if the room needs more pages, one **Artifacts** tab (`web/artifacts.html`, listed in
  `tabs.json`) that links them.
- **Selections page:** put product pictures at the top of each section in `selections.md`
  (`![name](intake/products/x.jpg)`).
- Check the walkthrough with a headless screenshot before saying it's done.

## 5. Save and stop

1. Update the room's README "Current state": what's modeled, open questions, reviews done, and
   the one next step. If `renders/asis/` is missing or older than the as-is model, render it
   first. If the design changed this session and no trade has reviewed it, offer one now (see
   "Experts" above).
2. Commit, then push, but only when asked (approval is per request). Room work is committed
   in the `houses/` repo; changes to `lib/`, `template/` or these docs go in this repo.
3. If there's a project tracker, update it with where things stopped and the next step.

## Houses

`houses/<house>/house.md` lists the house's rooms. With a listing plan, every room can go on a
whole-house map before any are modeled: trace the outlines into `houses/<house>/house_layout.py`
(`template/house/house_layout.py` shows the format), run `python3 lib/tools/house_map.py houses/<house>`, and open
`houses/<house>/web/index.html`. Starting a room that's on the map: use its id as the folder
name, then set `folder=` on its entry and rebuild the map. **Whenever a room is added, update the whole
house too:** rebuild the map (it also updates the "N modeled" count on the home page), retake the
home page's map picture with `lib/tools/house_snapshot.py houses/<house>` (server running), and add
the room's card to `houses/index.html` with the same links as the others (Walk through, Renders,
Plans, Selections). When two rooms that touch both exist, it
also records where each room sits in house coordinates: an origin and a rotation, plus which
doorway connects them. Until then, each room is modeled in its own coordinates, and anything
seen through a doorway is a simple stand-in (as the bedroom was before it was built out for
the bathroom). A whole-house walkthrough loads each room's model at its spot. It gets built
once a house has two connected rooms worth walking between.

## Conventions

- Inches everywhere in `layout.py` and `room.py`. Plan x runs east, y north, z up, with the
  origin at the room's interior NW corner (y is negative inside the room).
- Wall fixtures are built in a local frame: wall at y=0, room toward -y, x along the wall.
  `rot_z` turns that frame onto the wall (0 north, pi south, pi/2 west, -pi/2 east).
  `core.rect_walls()` and `core.to_plan()` do this for rectangular rooms.
- Material names are the contract with the walkthrough. The page's `materials` rules match them
  ("wood", "tile*"), and the shared ones (glass, fixture, chrome, leaves, led, can_lens, mirror)
  work everywhere.
- Quick renders go to `/tmp` or the room's `renders/` top level (not committed). Kept sets go
  in `renders/latest/` and `renders/options/`.
