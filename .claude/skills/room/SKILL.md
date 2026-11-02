---
name: room
description: 3D room models for home remodels (Blender renders + browser walkthrough), one room at a time in any house. Use when the user says "set me up" (first run), wants to start a new room ("new room: ours, kitchen"), continue or update a modeled room, share photos/measurements/product links for a room, compare options (tile, paint, lights), or record a choice.
argument-hint: "[new <house> <room> | continue <room> | status]"
---

# Room models

Everything lives in this repo. The toolkit (`lib/`, `template/`, the docs) is shared; the
user's houses live in `houses/`, their own private repo, which this repo ignores.
**Read `PROCESS.md` first, every time.** It is the playbook: start → intake → model the room as
it is → ideas and selections → standard renders and walkthrough → save and stop. Then read the
room's `README.md` ("Current state" says where it stopped) and `selections.md`.

The user drives everything by talking; never hand them commands to run. Run renders, exports,
the selections page and the local server (`lib/serve.sh`, http://127.0.0.1:8000) yourself.

**First run ("set me up", or `houses/` doesn't exist):**
1. Create the private houses repo: `git init houses`, copy `template/home.html` to
   `houses/index.html` and `template/catalog/` to `houses/catalog/`, and write
   `houses/.gitignore` with: `*/rooms/*/renders/*.jpg`, `*/rooms/*/web/bundle.js`,
   `*/rooms/*/web/.bake/`, `*/rooms/*/check.json`, `*.blend`, `*.blend1`, `__pycache__/`.
2. Check Blender: copy `template/room/` to `houses/_check/rooms/box`, run its
   `./render.sh --cams photo1 --samples 16 --res 800 --out /tmp/rendervation-check`, and report
   the `RENDER DEVICE` line (none means CPU: say renders will be slow). If Blender isn't found,
   say where to install it or set `BLENDER=/path/to/blender`. Delete `houses/_check` after.
3. Offer to connect `houses/` to a private remote of their own, then ask for their first room
   ("new room: <house>, <room>").

## Commands

- **new `<house>` `<room>`:** PROCESS.md step 0. Copy `template/room/` to
  `houses/<house>/rooms/<room>/` (and `template/house/` for a new house), add the room to
  `house.md` and `houses/index.html`, and give the user the shot list and measurement sheet
  from the room's `intake/README.md` (short, numbered, including the "no floor plan" option).
- **continue `<room>`:** read the room's README "Current state" and selections.md "Open
  decisions", say where it stopped in two or three lines, and offer the next step.
- **status:** list the houses and rooms, each with its status line and next step.
- **review `<room>` as `<trade>`** (or any plain request like "have a plumber look at the
  toilet"): run the `trades` agent. **find `<thing>`** ("find me a vanity, warm modern, under
  $800"): run the `designer` agent. **check `<room>`** ("is anything missing?"): run the
  `checker` agent.

## Rules that matter most

- **Log every product, link, suggestion and choice in the room's `selections.md` as it happens.**
  Do this before modeling it. Passed-on options stay under "Considered" with the reason. Save
  product photos to `intake/products/`.
- **Tag every dimension** in `layout.py` MEASURED / FROM PLAN / FROM PHOTO / ASSUMED. With no
  floor plan, estimate from photos against known sizes, and ask for one or two specific
  measurements to settle conflicts.
- **Always keep as-is renders.** Every room gets them before any design work: `./render.sh --design asis`
  into `renders/asis/day` and `renders/asis/night`, plus the plan and overview sheets (PROCESS.md step 2).
  When a view joins the standard set, render it as-is too. A room without them gets them next.
- **Check the model against the photos** before designing: render each photo view and compare
  them side by side.
- **Keep the person's things out of `lib/`.** Specific products (a particular vanity, a tile
  color measured from a product photo) go in their catalog, `houses/catalog/` (`parts.py`,
  `materials.py`); one-offs stay in the room's `room.py`. Reuse `lib/roomkit` freely, but change
  it only for something general (a new kind of part, a fix), and then as a PR to this repo.
- **Rendering:** through the room's `./render.sh`, which finds Blender and the GPU. Time the
  first render on a machine and give ETAs from it.
- **Commits:** commit and push only when the user asks, with their own git identity. Room work
  and the catalog go in the `houses/` repo; toolkit changes (`lib/`, `template/`, docs) go in
  this repo, on a branch, as a PR.
- **Check before trusting a render.** Run `./render.sh --check` (seconds) after any change to
  `room.py` and fix what it prints before rendering or baking. Offer the `checker` agent after the
  as-is model and before the final renders and bake.
- **Experts:** the `trades`, `designer` and `checker` agents (`.claude/agents/`) review the room,
  source products or check the model, in the background. Offer one at the checkpoints in PROCESS.md ("Experts"), in one
  line ("Want a lighting designer to look at this before we stop?"), and run it only on a yes
  or when asked. Pass the room folder, the trade, and what the person wants. Present what comes
  back briefly, adopt only what the person agrees to, and credit the review in `selections.md`.
- **Stopping:** end every stop by updating the room README's "Current state" with a small,
  concrete next step. If the design changed this session and no trade has reviewed it, offer
  one review first.
