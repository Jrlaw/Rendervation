// The home page (index.html): every house and its rooms from the server (GET /api/houses, server/
// features/houses.py), a card per room with its chosen design's picture. Edit renames houses and
// rooms and edits a card's line in place, moves rooms, and hides them; hidden rooms are listed at the
// end of their house to bring back. Opened from disk, it shows how to start the server instead.
(function () {
  const box = document.getElementById("houses");
  const status = document.getElementById("status");
  const editBtn = document.getElementById("edit");
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  async function api(path, body) {
    const res = await fetch(path, body ? { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const out = await res.json();
    if (!res.ok) throw new Error(out.detail?.[0]?.msg || out.detail || res.statusText);
    return out;
  }

  // an editable piece of text: data-edit="house|room", data-id, data-field="name|blurb"
  const editable = (kind, id, field, text, placeholder) =>
    `<span data-edit="${kind}" data-id="${esc(id)}" data-field="${field}" data-placeholder="${esc(placeholder)}">${esc(text)}</span>`;

  function roomCard(h, r, k, shown) {
    const img = r.card ? `<img src="${esc(r.card)}" alt="${esc(r.name)}${r.chosen_label ? ", " + esc(r.chosen_label) : ""}" loading="lazy">` : `<span class="noimg"></span>`;
    return `<article class="room${r.missing ? " missing" : ""}" data-room="${esc(r.room)}">
      ${img}
      <div>
        <b>${editable("room", r.room, "name", r.name, "Name")}</b>
        <small>${editable("room", r.room, "blurb", r.blurb, "A line about where it's at")}</small>
        ${r.chosen_label ? `<span class="chosen">Chosen: ${esc(r.chosen_label)}</span>` : ""}
        ${!r.modeled && !r.missing ? `<small>Not modeled yet: the walkthrough comes after the room's first export.</small>` : ""}
        ${r.missing ? `<small>Its folder is gone (${esc(r.room)}); the listing stays until it's back.</small>` : ""}
        <nav>${r.links.map(([label, href]) => `<a href="${esc(href)}">${esc(label)}</a>`).join("")}</nav>
        <div class="tools">
          <button data-move="-1" ${k === 0 ? "disabled" : ""} aria-label="Move ${esc(r.name)} earlier">←</button>
          <button data-move="1" ${k === shown - 1 ? "disabled" : ""} aria-label="Move ${esc(r.name)} later">→</button>
          <button data-hide>Hide</button>
        </div>
      </div>
    </article>`;
  }

  function mapCard(h) {
    // no map picture yet (lib/tools/house_snapshot.py makes one): a card without one
    const img = h.map.card ? `<img src="${esc(h.map.card)}" alt="3D dollhouse of ${esc(h.name)}" loading="lazy">` : "";
    return `<article class="room${img ? "" : " nopic"}">
      ${img}
      <div>
        <b>Whole house</b>
        <small>${editable("house", h.house, "blurb", h.blurb, "A line about the house")}<span class="sep"> · </span>${h.modeled} modeled</small>
        <nav>${h.map.links.map(([label, href]) => `<a href="${esc(href)}">${esc(label)}</a>`).join("")}</nav>
      </div>
    </article>`;
  }

  function draw(houses) {
    box.innerHTML = houses.filter((h) => !h.missing).map((h) => {
      const shown = h.rooms.filter((r) => !r.hidden);
      const hidden = h.rooms.filter((r) => r.hidden);
      if (!shown.length && !hidden.length && !h.map) return "";
      return `<section data-house="${esc(h.house)}">
        <h2>${editable("house", h.house, "name", h.name, "House")}${h.example ? "<small>Example</small>" : ""}</h2>
        <div class="rooms">
          ${h.map ? mapCard(h) : ""}
          ${shown.map((r, k) => roomCard(h, r, k, shown.length)).join("")}
        </div>
        ${hidden.length ? `<div class="hidden-list">Hidden: ${hidden.map((r) => `<button data-show="${esc(r.room)}" title="Show it on the home page again">${esc(r.name)}</button>`).join("")}</div>` : ""}
      </section>`;
    }).join("");
    setEditable(document.body.classList.contains("editing"));
  }

  function setEditable(on) {
    box.querySelectorAll("[data-edit]").forEach((el) => { el.contentEditable = on ? "plaintext-only" : "false"; });
  }

  let houses = [];
  async function reload() {
    houses = await api("/api/houses");
    draw(houses);
  }

  async function save(fn, done) {
    status.textContent = "Saving …";
    try { await fn(); status.textContent = done; } catch (err) { status.textContent = "Not saved: " + err.message; }
    await reload();
  }

  editBtn.addEventListener("click", () => {
    const on = !document.body.classList.contains("editing");
    document.body.classList.toggle("editing", on);
    editBtn.setAttribute("aria-pressed", on);
    editBtn.textContent = on ? "Done" : "Edit";
    setEditable(on);
    status.textContent = on ? "Click a name or a card's line to change it; arrows move a room, Hide takes it off the page." : "";
  });

  // text: saved when it loses focus; Enter finishes, Escape puts it back
  box.addEventListener("keydown", (e) => {
    const el = e.target.closest("[data-edit]");
    if (!el) return;
    if (e.key === "Enter") { e.preventDefault(); el.blur(); }
    if (e.key === "Escape") { el.dataset.cancel = "1"; el.blur(); }
  });
  box.addEventListener("focusout", (e) => {
    const el = e.target.closest("[data-edit]");
    if (!el || !document.body.classList.contains("editing")) return;
    const kind = el.dataset.edit, id = el.dataset.id, field = el.dataset.field;
    const list = kind === "house" ? houses : houses.flatMap((h) => h.rooms);
    const was = list.find((x) => x[kind] === id)?.[field] ?? "";
    const now = el.textContent.trim();
    if (el.dataset.cancel || now === was || (field === "name" && !now)) { delete el.dataset.cancel; el.textContent = was; return; }
    save(() => api(`/api/${kind === "house" ? "houses" : "rooms"}/${id}`, { [field]: now }), "Saved.");
  });

  box.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.show) return save(() => api(`/api/rooms/${b.dataset.show}`, { hidden: false }), "Back on the page.");
    const card = b.closest("[data-room]");
    if (!card) return;
    const room = card.dataset.room;
    if (b.dataset.hide !== undefined) return save(() => api(`/api/rooms/${room}`, { hidden: true }), "Hidden. It's listed under its house to bring back.");
    if (b.dataset.move) {
      const h = houses.find((x) => x.rooms.some((r) => r.room === room));
      const order = h.rooms.filter((r) => !r.hidden).map((r) => r.room);
      const to = order.indexOf(room) + Number(b.dataset.move);
      const target = h.rooms.findIndex((r) => r.room === order[to]);   // its place among all, hidden too
      return save(() => api(`/api/rooms/${room}`, { position: target }), "Moved.");
    }
  });

  if (location.protocol === "file:") { document.getElementById("offline").hidden = false; return; }
  reload().then(() => { editBtn.hidden = false; }).catch((err) => {
    console.error(err);
    document.getElementById("offline").hidden = false;
  });
})();
