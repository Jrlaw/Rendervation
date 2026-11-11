// Plans page: the top-down render (renders/plan.jpg) with switchable overlays drawn from the
// room's export (scene.js): dimension lines colored by where each number came from, and the
// recessed lights with their distances from the west and north walls. Updates on every export.
// window.PLANS = { designs: [[id, label], ...] } adds a design picker, like the walkthrough's
// `variants`: the first is the room's own export (scene.js, renders/plan.jpg), the rest load
// variants/<id>/scene.js and variants/<id>/renders/plan.jpg. Works opened from disk too. Opens on
// ?design=<id>, else the room's chosen design (from the server; designs hidden there are left out).
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const SRC = {
    measured: ["Measured", "#2e7d32"], plan: ["From the floor plan", "#1f5fa8"], photo: ["From photos", "#7b3fa0"],
    design: ["Design choice", "#8a5233"], assumed: ["Guess, needs a tape measure", "#c25e00"],
  };
  const scenes = { "": window.SCENE };   // base -> SCENE, loaded once each
  const loadScene = (base) => scenes[base] ? Promise.resolve(scenes[base]) : new Promise((ok, fail) => {
    const sc = document.createElement("script");
    sc.src = base + "scene.js";
    sc.onload = () => { scenes[base] = window.SCENE; ok(window.SCENE); };
    sc.onerror = fail;
    document.body.appendChild(sc);
  });

  function draw(S, base) {
    const cam = S.cameras.plan;
    const span = cam.ortho, cx = cam.target[0], cy = cam.target[1];
    const x0 = cx - span / 2, y1 = cy + span / 2;            // top-left of the image, plan inches
    const inView = (x, y) => Math.abs(x - cx) < span / 2 && Math.abs(y - cy) < span / 2;

    // svg in plan inches with y flipped (svg y = -plan y)
    const svg = el("svg", { viewBox: `${x0} ${-y1} ${span} ${span}`, role: "img", "aria-label": "Top view of the room" });
    el("image", { href: base + "renders/plan.jpg", x: x0, y: -y1, width: span, height: span }, svg);
    document.getElementById("plan").replaceChildren(svg);

    // ---------- dimensions
    const gd = el("g", { class: "layer-dims" }, svg);
    const rows = [];
    (S.dims || []).forEach((d) => {
      const [ax, ay] = d.a, [bx, by] = d.b;
      const len = Math.hypot(bx - ax, by - ay);
      const nx = -(by - ay) / len, ny = (bx - ax) / len;         // left of a->b
      const col = (SRC[d.src] || SRC.assumed)[1];
      const p = (x, y, k) => [x + nx * k, -(y + ny * k)];
      const [a1x, a1y] = p(ax, ay, d.off), [b1x, b1y] = p(bx, by, d.off);
      const g = el("g", { stroke: col, fill: col, "stroke-width": 0.6 }, gd);
      const ext = d.off + Math.sign(d.off || 1) * 2;
      el("line", { x1: ax, y1: -ay, x2: p(ax, ay, ext)[0], y2: p(ax, ay, ext)[1], "stroke-width": 0.35 }, g);
      el("line", { x1: bx, y1: -by, x2: p(bx, by, ext)[0], y2: p(bx, by, ext)[1], "stroke-width": 0.35 }, g);
      el("line", { x1: a1x, y1: a1y, x2: b1x, y2: b1y, "stroke-dasharray": d.src === "assumed" ? "2 1.2" : "none" }, g);
      [[a1x, a1y], [b1x, b1y]].forEach(([x, y]) => el("circle", { cx: x, cy: y, r: 0.9, stroke: "none" }, g));
      let ang = Math.atan2(b1y - a1y, b1x - a1x) * 180 / Math.PI;
      if (ang > 90) ang -= 180; else if (ang < -90) ang += 180;
      const mx = (a1x + b1x) / 2, my = (a1y + b1y) / 2;
      const t = el("text", { x: mx, y: my, transform: `rotate(${ang} ${mx} ${my})`, "text-anchor": "middle",
                             "dominant-baseline": "middle", class: "dim-label", stroke: "none" }, g);
      t.textContent = d.label;
      // white pad behind the label so it reads over the render
      requestAnimationFrame(() => {
        const bb = t.getBBox();
        const r = el("rect", { x: bb.x - 1, y: bb.y - 0.4, width: bb.width + 2, height: bb.height + 0.8, rx: 1,
                               fill: "#fffdf8", stroke: "none", transform: t.getAttribute("transform") });
        g.insertBefore(r, t);
      });
      rows.push([d.label, d.src]);
    });

    // ---------- lights
    const gl = el("g", { class: "layer-lights" }, svg);
    const lrows = [];
    S.lights.filter((l) => inView(l.x, l.y)).forEach((l, k) => {
      const tag = l.name.startsWith("can_") && /^\d+$/.test(l.name.slice(4)) ? l.name.slice(4) : l.name.slice(4, 5).toUpperCase();
      el("circle", { cx: l.x, cy: -l.y, r: 4, fill: "#ffd23f", stroke: "#7a5200", "stroke-width": 0.7 }, gl);
      const t = el("text", { x: l.x, y: -l.y + 0.2, "text-anchor": "middle", "dominant-baseline": "middle", class: "light-label" }, gl);
      t.textContent = tag;
      lrows.push([tag, l.name.replace("can_", ""), Math.round(l.x), Math.round(-l.y)]);
    });

    // ---------- legend, toggles, lists
    document.getElementById("legend").innerHTML = Object.values(SRC)
      .map(([name, c]) => `<span><i style="background:${c}"></i>${name}</span>`).join("");
    document.getElementById("dimlist").innerHTML = rows
      .map(([lab, src]) => `<li><b>${lab}</b> <span style="color:${(SRC[src] || SRC.assumed)[1]}">${(SRC[src] || SRC.assumed)[0]}</span></li>`).join("");
    document.getElementById("lightlist").innerHTML = lrows
      .map(([tag, name, x, y]) => `<li><b>${tag}</b> ${name}: ${x}" from the west wall, ${y}" from the north wall</li>`).join("");
    layers();
  }

  // the Show checkboxes act on whichever plan is drawn
  function layers() {
    document.querySelectorAll("[data-layer]").forEach((cb) => {
      const g = document.querySelector("#plan .layer-" + cb.dataset.layer);
      if (g) g.style.display = cb.checked ? "" : "none";
      document.getElementById(cb.dataset.layer + "-box").hidden = !cb.checked;
    });
  }
  document.querySelectorAll("[data-layer]").forEach((cb) => cb.addEventListener("change", layers));

  draw(window.SCENE, "");

  // design picker, the walkthrough's pill style; ?design=<id> opens on that design. Served, the room's
  // designs as edited on the web (server/features/designs.py): hidden ones left out, renamed ones relabeled
  picker();
  async function picker() {
    let designs = (window.PLANS && window.PLANS.designs) || [];
    const room = (location.pathname.match(/\/((?:houses|examples)\/[^/]+\/rooms\/[^/]+)\/web\//) || [])[1];
    if (designs.length > 1 && room && location.protocol !== "file:") {
      try {
        const s = await (await fetch(`/api/rooms/${room}/designs`)).json();
        const live = Object.fromEntries(s.designs.filter((d) => !d.hidden).map((d) => [d.id, d.label]));
        designs = designs.filter(([id], k) => k === 0 || id in live).map(([id, label]) => [id, live[id] || label]);
        window.CHOSEN = s.chosen || undefined;
      } catch (err) { console.error(err); }
    }
    if (designs.length > 1) {
      const pk = document.createElement("div");
      pk.className = "daynight plan-designs";
      pk.setAttribute("role", "group");
      pk.setAttribute("aria-label", "Design");
      designs.forEach(([id, label], k) => {
        const b = document.createElement("button");
        b.textContent = label;
        b.setAttribute("aria-pressed", k === 0);
        b.addEventListener("click", async () => {
          if (b.getAttribute("aria-pressed") === "true") return;
          pk.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
          const base = k === 0 ? "" : `variants/${id}/`;
          try { draw(await loadScene(base), base); } catch (err) { console.error(err); }
        });
        pk.appendChild(b);
      });
      // one bar above the plan: the page's Room / Track pills (if any), then the designs
      const plan = document.getElementById("plan");
      const bar = document.createElement("div");
      bar.className = "plan-bar";
      plan.parentNode.insertBefore(bar, plan);
      const sub = plan.parentNode.querySelector(".subtabs");
      if (sub) bar.appendChild(sub);
      bar.appendChild(pk);
      const k = designs.findIndex(([id]) => id === (new URLSearchParams(location.search).get("design") || window.CHOSEN));
      if (k > 0) pk.children[k].click();
    }
  }
})();
