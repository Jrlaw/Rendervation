// Shared walkthrough for a room: the 3D model you can walk through (drag to look, tap the
// floor to walk, WASD), day/evening lighting, and the before/after render comparison.
//
// A room's web/index.html loads this as a plain script (so the page still opens straight from
// disk), lists three.js in an import map, and calls Walkthrough.start({...}) with:
//   views:  [[camera, label], ...]          jump buttons under the 3D view
//   pairs:  [[camera, label, photoN], ...]  render vs. before/photoN.jpg sliders
//   more:   [[camera, label], ...]          renders with no matching photo (the Renders tab
//                                           shows the pairs' renders, then these)
//   start:  camera to open on
//   materials(kit) -> [{ match, material, uv, floor, shadow }, ...]
//          match: material name in the model ("wood") or a prefix ("tile*");
//          uv: { world: inches per repeat } or { top: true, flip }; floor: you can walk on it;
//          shadow: false to skip casting shadows. Room rules come before the shared ones below.
//   noShadowLights: name prefixes of cans that don't cast shadows (big rooms, for speed)
//   sunAim: plan [x, y] the sun's shadow box centers on (default: the walk area's center)
// The model (model.glb + scene.json, or bundle.js) comes from the room's render.sh --export.
window.Walkthrough = { start };

async function start(cfg) {
  const THREE = await import("three");
  const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
  const { RoomEnvironment } = await import("three/addons/environments/RoomEnvironment.js");
  const { Reflector } = await import("three/addons/objects/Reflector.js");
  const { EffectComposer } = await import("three/addons/postprocessing/EffectComposer.js");
  const { RenderPass } = await import("three/addons/postprocessing/RenderPass.js");
  const { GTAOPass } = await import("three/addons/postprocessing/GTAOPass.js");
  const { OutputPass } = await import("three/addons/postprocessing/OutputPass.js");
  const { RectAreaLightUniformsLib } = await import("three/addons/lights/RectAreaLightUniformsLib.js");
  // served: the room's designs as edited on the web (server/features/designs.py), hidden ones left out,
  // renamed ones relabeled, and the chosen one. Opened from disk: the page's own list.
  const ROOM = (location.pathname.match(/\/((?:houses|examples)\/[^/]+\/rooms\/[^/]+)\/web\//) || [])[1];
  const api = (path, method, body) => fetch(`/api/rooms/${ROOM}${path}`, body ? { method, headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) } : {}).then(async (res) => {
    const out = await res.json();
    if (!res.ok) throw new Error(out.detail || res.statusText);
    return out;
  });
  let hiddenDesigns = [];
  if (cfg.variants && ROOM && location.protocol !== "file:") {
    try {
      const s = await api("/designs");
      cfg.variants = s.designs.filter((d) => !d.hidden).map((d) => [d.id, d.label]);
      hiddenDesigns = s.designs.filter((d) => d.hidden);
      window.CHOSEN = s.chosen || undefined;
    } catch (err) { console.error(err); }
  }

  const IN = 0.0254;
  let mode = location.search.includes("evening") ? "night" : "day";   // ?evening opens in evening

  // ---------- tabs
  document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.setAttribute("aria-selected", x === b));
    ["walk", "renders", "gallery"].forEach((id) => {
      const sec = document.getElementById(id);
      if (sec) sec.hidden = b.dataset.tab !== id;
    });
    if (b.dataset.tab === "walk") resize();
  }));
  // index.html#renders or #gallery opens that tab: the room's other pages link to them
  const hashTab = document.querySelector(`.tabs button[data-tab="${location.hash.slice(1)}"]`);
  if (hashTab) hashTab.click();

  // ---------- before/after + day/night. With cfg.variants each design has its own renders, next to its
  // model: renders/ for the room's own export, variants/<id>/renders/ for the rest. Both tabs get the
  // design pills, kept in step with the 3D picker; a camera a design has no render for is left out.
  const rgrid = document.getElementById("rgrid");
  const mgrid = document.getElementById("mgrid");
  // start on ?design=<id>, else the chosen design, like the 3D view (set directly: the 3D side isn't built yet)
  const k0 = cfg.variants ? Math.max(0, cfg.variants.findIndex(([id]) => id === (new URLSearchParams(location.search).get("design") || window.CHOSEN))) : 0;
  let rbase = k0 ? `variants/${cfg.variants[k0][0]}/` : "", rlabel = cfg.variants ? cfg.variants[k0][1] : "new design";
  const rsrc = (id) => `${rbase}renders/${mode}/${id}.jpg`;
  function setMode(m) {
    mode = m;
    document.querySelectorAll(".daynight button[data-mode]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.mode === m));
    document.querySelectorAll("img[data-render]").forEach((img) => { img.closest("figure").hidden = false; img.src = rsrc(img.dataset.render); });
    checkNone();
    if (rig) rig.apply(m);
  }
  document.querySelectorAll(".daynight button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  function setRenderDesign(k) {
    rbase = k === 0 ? "" : `variants/${cfg.variants[k][0]}/`;
    rlabel = cfg.variants[k][1];
    document.querySelectorAll(".rdesign").forEach((g) => [...g.children].forEach((b, i) => b.setAttribute("aria-pressed", i === k)));
    document.querySelectorAll(".dlabel").forEach((el) => { el.textContent = rlabel; });
    setMode(mode);
  }
  if (cfg.variants) {
    document.querySelectorAll("#renders .rhead, #gallery .rhead").forEach((head) => {
      const g = document.createElement("div");
      g.className = "daynight rdesign";
      g.setAttribute("role", "group");
      g.setAttribute("aria-label", "Design");
      cfg.variants.forEach(([id, label], k) => {
        const b = document.createElement("button");
        b.textContent = label;
        b.setAttribute("aria-pressed", k === k0);
        // with the 3D picker (served), its pill switches everything; opened from disk, just the pictures
        b.addEventListener("click", () => (picker ? picker.children[k].click() : setRenderDesign(k)));
        g.appendChild(b);
      });
      head.insertBefore(g, head.querySelector(".daynight"));
    });
  }
  // a design with none of a tab's renders says so rather than showing an empty grid
  const none = [rgrid, mgrid].map((g) => {
    const p = document.createElement("p");
    p.className = "rintro";
    p.hidden = true;
    p.textContent = "No renders saved for this design yet.";
    g.before(p);
    return p;
  });
  const checkNone = () => [rgrid, mgrid].forEach((g, i) => {
    none[i].hidden = !g.children.length || [...g.children].some((f) => !f.hidden);
  });
  const hideMissing = (f) => { f.querySelector("img[data-render]").addEventListener("error", () => { f.hidden = true; checkNone(); }); };
  // Renders tab: the views that pair with a photo first, then the rest; click to enlarge
  [...(cfg.pairs || []), ...(cfg.more || [])].forEach(([id, label]) => {
    const f = document.createElement("figure");
    f.innerHTML = `<img data-render="${id}" src="${rsrc(id)}" alt="Render: ${label}" loading="lazy">
      <figcaption><b>${label}</b><span class="dlabel">${rlabel}</span></figcaption>`;
    hideMissing(f);
    mgrid.appendChild(f);
  });
  if (window.Lightbox) Lightbox.attach("#mgrid img");
  (cfg.pairs || []).forEach(([id, label, n]) => {
    const f = document.createElement("figure");
    f.innerHTML = `<div class="compare" style="--x:50%">
        <img data-render="${id}" src="${rsrc(id)}" alt="Render: ${label}" loading="lazy">
        <img class="before" src="before/photo${n}.jpg" alt="Original photo: ${label}" loading="lazy">
        <div class="bar"></div><div class="knob"></div>
        <span class="tag l">Now</span><span class="tag r dlabel">${rlabel}</span></div>
      <figcaption><b>${label}</b><span>your photo ${n}</span></figcaption>`;
    hideMissing(f);
    const c = f.querySelector(".compare");
    const set = (e) => {
      const r = c.getBoundingClientRect();
      const x = Math.min(100, Math.max(0, ((e.clientX - r.left) / r.width) * 100));
      c.style.setProperty("--x", x + "%");
    };
    c.addEventListener("pointerdown", (e) => { c.setPointerCapture(e.pointerId); set(e); });
    c.addEventListener("pointermove", (e) => { if (e.buttons) set(e); });
    rgrid.appendChild(f);
  });

  // ---------- 3D
  const stage = document.getElementById("stage");
  const renderer = new THREE.WebGLRenderer();   // antialiasing happens in the composer's buffers (below)
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.AgXToneMapping;      // same view transform as the Cycles renders
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  stage.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xb9cde6);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.6;

  const camera = new THREE.PerspectiveCamera(70, 1, 0.03, 100);
  // ambient occlusion: soft contact shadows in corners, under cabinets and around fixtures
  RectAreaLightUniformsLib.init();
  // the composer draws to its own buffers, where the renderer's antialias setting doesn't apply: MSAA goes there
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType }));
  composer.addPass(new RenderPass(scene, camera));
  const ao = new GTAOPass(scene, camera, 1, 1);
  ao.updateGtaoMaterial({ radius: 0.35, distanceExponent: 1.5, thickness: 1.5, scale: 1.2, samples: 16 });
  ao.blendIntensity = 0.85;
  composer.addPass(ao);
  composer.addPass(new OutputPass());
  let rig = null;      // day/evening lighting, set up once the model loads
  const plan = (x, y, z) => new THREE.Vector3(x * IN, z * IN, -y * IN);   // layout inches -> three

  // ---------- graphics settings: the Settings button on the stage, remembered in this browser.
  // ?lowres (the Fast preset) and ?noao set the starting values for one visit
  const SETTINGS_KEY = "walkthrough.settings";
  const PRESETS = {
    fast: { res: "1", aa: 2, ao: false, shadows: false },
    balanced: { res: "auto", aa: 4, ao: true, shadows: true },
    sharp: { res: "auto", aa: 8, ao: true, shadows: true },
    best: { res: "2", aa: 8, ao: true, shadows: true },
  };
  const DEFAULTS = { ...PRESETS.sharp, brightness: 1, fov: 70, fps: false };
  const settings = { ...DEFAULTS };
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SETTINGS_KEY))); } catch (err) { /* private window, or none saved */ }
  if (location.search.includes("lowres")) Object.assign(settings, PRESETS.fast);
  if (location.search.includes("noao")) settings.ao = false;
  let isBaked = false;      // baked rooms carry their shadows and ambient occlusion in the texture
  let baseExposure = 1;     // day or evening (rig.apply); the Brightness setting multiplies it

  function applySettings() {
    const dpr = settings.res === "auto" ? Math.min(Math.max(devicePixelRatio, 1.5), 2) : Number(settings.res);   // auto: at least 1.5x, so thin edges hold up on ordinary monitors
    renderer.setPixelRatio(dpr);
    composer.setPixelRatio(dpr);
    const samples = Math.min(settings.aa, renderer.capabilities.maxSamples);
    [composer.renderTarget1, composer.renderTarget2].forEach((t) => {
      if (t.samples !== samples) { t.samples = samples; t.dispose(); }   // reallocated at the next render
    });
    ao.enabled = settings.ao && !isBaked;
    const shadows = settings.shadows;
    if (renderer.shadowMap.enabled !== shadows) {
      renderer.shadowMap.enabled = shadows;
      scene.traverse((o) => { [].concat(o.material || []).forEach((m) => { m.needsUpdate = true; }); });
    }
    renderer.toneMappingExposure = baseExposure * settings.brightness;
    resize();
  }

  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.fov = settings.fov + (w / h < 1 ? 15 : 0);   // wider on a tall, narrow screen
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage);

  const settingsBtn = document.createElement("button");
  settingsBtn.className = "stage-settings";
  settingsBtn.textContent = "Settings";
  settingsBtn.setAttribute("aria-expanded", "false");
  const panel = document.createElement("form");
  panel.className = "settings-panel";
  panel.hidden = true;
  panel.setAttribute("aria-label", "Graphics settings");
  const aaChoices = [[0, "Off"], [2, "2x"], [4, "4x"], [8, "8x"]].filter(([n]) => n <= renderer.capabilities.maxSamples);
  const options = (list) => list.map(([v, label]) => `<option value="${v}">${label}</option>`).join("");
  panel.innerHTML = `
    <label>Quality <select name="preset">${options([["fast", "Fast"], ["balanced", "Balanced"], ["sharp", "Sharp"], ["best", "Best"], ["custom", "Custom"]])}</select></label>
    <label>Resolution <select name="res">${options([["auto", "Auto"], ["1", "1x"], ["1.5", "1.5x"], ["2", "2x"], ["3", "3x"]])}</select></label>
    <label>Antialiasing <select name="aa">${options(aaChoices)}</select></label>
    <label data-live>Corner shading <input type="checkbox" name="ao"></label>
    <label data-live>Live shadows <input type="checkbox" name="shadows"></label>
    <label>Brightness <input type="range" name="brightness" min="0.6" max="1.6" step="0.05"></label>
    <label>Field of view <input type="range" name="fov" min="50" max="90" step="5"></label>
    <label>Frame rate <input type="checkbox" name="fps"></label>
    <p class="settings-note" data-bakednote>Corner shading and shadows are part of this design's baked lighting.</p>
    <button type="button" name="reset">Reset to defaults</button>`;
  const fpsOut = document.createElement("output");
  fpsOut.className = "stage-fps";
  // the stage's buttons share one right-hand column, so a long design list wraps instead of covering them
  const controls = document.createElement("div");
  controls.className = "stage-controls";
  const dayNight = stage.querySelector(".stage-dn");
  if (dayNight) controls.append(dayNight);
  controls.append(settingsBtn, panel, fpsOut);
  stage.append(controls);

  function showSettings() {
    const f = panel.elements;
    const preset = Object.keys(PRESETS).find((k) => Object.entries(PRESETS[k]).every(([key, v]) => settings[key] === v));
    f.preset.value = preset || "custom";
    f.res.value = settings.res;
    f.aa.value = Math.max(...aaChoices.map(([n]) => n).filter((n) => n <= settings.aa));   // a GPU may offer fewer samples than the preset's
    f.ao.checked = settings.ao;
    f.shadows.checked = settings.shadows;
    f.brightness.value = settings.brightness;
    f.fov.value = settings.fov;
    f.fps.checked = settings.fps;
    panel.querySelectorAll("[data-live]").forEach((el) => { el.hidden = isBaked; });
    panel.querySelector("[data-bakednote]").hidden = !isBaked;
    fpsOut.hidden = !settings.fps;
  }
  function changeSettings(next) {
    Object.assign(settings, next);
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)); } catch (err) { /* not saved, still applies */ }
    applySettings();
    showSettings();
  }
  panel.addEventListener("submit", (e) => e.preventDefault());
  panel.addEventListener("input", (e) => {
    const t = e.target;
    if (t.name === "preset") { if (PRESETS[t.value]) changeSettings(PRESETS[t.value]); else showSettings(); }
    else if (t.type === "checkbox") changeSettings({ [t.name]: t.checked });
    else if (t.name === "res") changeSettings({ res: t.value });
    else changeSettings({ [t.name]: Number(t.value) });
  });
  panel.elements.reset.addEventListener("click", () => changeSettings(DEFAULTS));
  function openSettings(open) {
    panel.hidden = !open;
    settingsBtn.setAttribute("aria-expanded", open);
  }
  settingsBtn.addEventListener("click", () => openSettings(panel.hidden));
  addEventListener("keydown", (e) => { if (e.key === "Escape") openSettings(false); });
  addEventListener("pointerdown", (e) => { if (!e.target.closest(".settings-panel, .stage-settings")) openSettings(false); });
  applySettings();
  showSettings();

  const texLoader = new THREE.TextureLoader();
  // textures come from bundle.js when present (needed when opened from disk), else from the files
  const texSrc = (url) => (window.BUNDLE && window.BUNDLE.tex[url.split("/").pop()]) || url;
  function loadTex(url) {
    const t = texLoader.load(texSrc(url));
    t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  }
  // tile face from a photo with a 1/8" grout joint painted on its edges; size in inches
  function tileTexture(url, size = 24) {
    const c = document.createElement("canvas");
    c.width = c.height = 1024;
    const t = new THREE.CanvasTexture(c);
    const img = new Image();
    img.onload = () => {
      const g = c.getContext("2d");
      g.drawImage(img, 0, 0, 1024, 1024);
      g.strokeStyle = "#b5afa6";
      g.lineWidth = 1024 * (0.125 / size) * 2;
      g.strokeRect(0, 0, 1024, 1024);
      t.needsUpdate = true;
    };
    img.src = texSrc(url);
    t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  }
  // a texture painted on a canvas: draw(g, size) paints a size x size square
  function canvasTexture(draw, size = 512) {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    draw(c.getContext("2d"), size);
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return t;
  }
  const leafTexture = () => canvasTexture((g) => {
    for (let i = 0; i < 420; i++) {
      const x = Math.random() * 256, y = Math.random() * 256, a = Math.random() * Math.PI;
      g.fillStyle = `hsl(${78 + Math.random() * 14} 45% ${22 + Math.random() * 18}%)`;
      g.beginPath(); g.ellipse(x, y, 9, 3.5, a, 0, Math.PI * 2); g.fill();
    }
  }, 256);

  // materials every room shares (names from roomkit/materials.py basic_set and parts.py)
  const SHARED = [
    { match: "glass", material: new THREE.MeshPhysicalMaterial({ color: 0xeaf4f1, roughness: 0, metalness: 0, transparent: true, opacity: 0.12, envMapIntensity: 0.1 }), shadow: false },
    { match: "chrome", material: "chrome" }, { match: "nickel", material: "nickel" },
    { match: "fixture", material: new THREE.MeshStandardMaterial({ color: 0x0b0b0b, metalness: 0.2, roughness: 0.45 }) },   // matte black
    { match: "leaves", material: new THREE.MeshStandardMaterial({ map: leafTexture(), color: 0xffffff, roughness: 0.8, alphaTest: 0.5, side: THREE.DoubleSide }), uv: { world: 0.6 / IN }, shadow: false },
    { match: "led", material: new THREE.MeshBasicMaterial({ color: 0xffe0bd }), shadow: false },
    { match: "can_lens", material: new THREE.MeshBasicMaterial({ color: 0xfff4e6 }), shadow: false },
  ];
  const chrome = new THREE.MeshStandardMaterial({ color: 0xe8e8e8, metalness: 1, roughness: 0.12, envMapIntensity: 2.2 });
  // brushed nickel: satin, so softer and lighter reflections than chrome (dark tile turned it black)
  const nickel = new THREE.MeshStandardMaterial({ color: 0xaaa59c, metalness: 1, roughness: 0.3, envMapIntensity: 1.5 });
  SHARED.forEach((r) => { if (r.material === "chrome") r.material = chrome; if (r.material === "nickel") r.material = nickel; });
  const RULES = [...(cfg.materials ? cfg.materials({ THREE, IN, loadTex, tileTexture, canvasTexture }) : []), ...SHARED];
  const ruleFor = (name) => RULES.find((r) => (r.match.endsWith("*") ? name.startsWith(r.match.slice(0, -1)) : name === r.match));

  // stretch one picture across a flat object's top (rugs); flip turns it to read from the other side
  function topUVs(mesh, flip) {
    const g = mesh.geometry;
    g.computeBoundingBox();
    const b = g.boundingBox, pos = g.attributes.position, uv = new Float32Array(pos.count * 2);
    for (let i = 0; i < pos.count; i++) {
      let u = (pos.getX(i) - b.min.x) / (b.max.x - b.min.x), v = (pos.getZ(i) - b.min.z) / (b.max.z - b.min.z);
      if (!flip) { v = 1 - v; } else { u = 1 - u; }
      uv[i * 2] = u; uv[i * 2 + 1] = v;
    }
    g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  }

  // planar UVs from world position, picked per face by the dominant normal axis
  function worldUVs(mesh, size) {
    const g = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry;
    mesh.geometry = g;
    if (!g.attributes.normal) g.computeVertexNormals();
    const pos = g.attributes.position, nor = g.attributes.normal;
    const uv = new Float32Array(pos.count * 2);
    const p = new THREE.Vector3(), n = new THREE.Vector3();
    const nm = new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);
    for (let i = 0; i < pos.count; i++) {
      p.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
      n.fromBufferAttribute(nor, i).applyMatrix3(nm);
      const ax = Math.abs(n.x), ay = Math.abs(n.y), az = Math.abs(n.z);
      let u, v;
      if (ay >= ax && ay >= az) { u = p.x; v = p.z; }
      else if (ax >= az) { u = p.z; v = p.y; }
      else { u = p.x; v = p.y; }
      uv[i * 2] = u / size; uv[i * 2 + 1] = v / size;
    }
    g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  }

  const floors = [];
  const mirrors = [];
  let info;
  let vgroup = null, first = true;    // everything the current design adds (model, lights, mirrors)
  let curDesign = cfg.variants ? cfg.variants[0][0] : "", picker = null, pendingShow = null;   // the design shown, its picker, a product waiting for it

  function disposeGroup(g) {
    g.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      [].concat(o.material || []).forEach((m) => { if (m.map) m.map.dispose(); m.dispose(); });
      if (o.isLight && o.dispose) o.dispose();
    });
  }

  // base: "" for the room's own export, "variants/<id>/" for another design (cfg.variants)
  async function load(base = "", fresh = false) {
    let gltf;
    const bust = fresh ? `?t=${Date.now()}` : "";     // after a rebuild: skip the browser cache
    if (window.BUNDLE && !base && !fresh) {
      info = window.BUNDLE.scene;
      const bin = Uint8Array.from(atob(window.BUNDLE.glb), (ch) => ch.charCodeAt(0));
      gltf = await new GLTFLoader().parseAsync(bin.buffer, "");
    } else {
      info = await (await fetch(base + "scene.json" + bust)).json();
      gltf = await new GLTFLoader().loadAsync(base + "model.glb" + bust);
    }
    // the baked lighting, decoded and on the GPU before the swap (else it shows black until then)
    let bakeTex = null;
    if (info.bake) {
      bakeTex = await texLoader.loadAsync(base ? base + "textures/" + info.bake + bust : texSrc("textures/" + info.bake));
      bakeTex.colorSpace = THREE.SRGBColorSpace;
      bakeTex.flipY = false;                         // glTF UV convention
      bakeTex.wrapS = bakeTex.wrapT = THREE.ClampToEdgeWrapping;
      bakeTex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      renderer.initTexture(bakeTex);
    }
    // switching designs: the current view stays up as a still while the new one is set up, then fades
    let veil = null;
    if (!first) {
      composer.render();
      veil = document.createElement("canvas");
      veil.className = "veil";
      veil.width = renderer.domElement.width;
      veil.height = renderer.domElement.height;
      veil.getContext("2d").drawImage(renderer.domElement, 0, 0);
      renderer.domElement.after(veil);
    }
    if (vgroup) { scene.remove(vgroup); disposeGroup(vgroup); }
    floors.length = 0; mirrors.length = 0;
    const vg = new THREE.Group();
    vgroup = vg;
    scene.add(vg);
    const root = gltf.scene;
    vg.add(root);
    root.updateMatrixWorld(true);
    // baked export (--bake): Cycles lighting is in one atlas; those surfaces show it as-is (no
    // live lights, shadows or AO on them); steel, chrome and glass stay live for reflections
    const baked = new Set(info.baked || []);
    let bakeMat = null;
    isBaked = !!info.bake;
    applySettings();
    showSettings();
    if (bakeTex) bakeMat = new THREE.MeshBasicMaterial({ map: bakeTex, toneMapped: false });
    root.traverse((o) => {
      if (!o.isMesh) return;
      const name = (o.material && o.material.name) || "";
      o.castShadow = o.receiveShadow = true;
      const r = ruleFor(name);
      if (bakeMat && baked.has(name)) {
        o.material = bakeMat;
        o.castShadow = o.receiveShadow = false;
        if (r && r.floor) floors.push(o);
        return;
      }
      if (r) {
        if (r.uv && r.uv.world) worldUVs(o, r.uv.world * IN);
        if (r.uv && r.uv.top) topUVs(o, r.uv.flip);
        o.material = r.material;
        if (r.shadow === false) o.castShadow = false;
        if (r.floor) floors.push(o);
      } else if (name === "mirror") {
        mirrors.push(o);
      }
      if (!o.material.map && o.material.isMeshStandardMaterial) o.material.envMapIntensity = 0.6;
    });
    // swap each mirror box for a live reflection on its room-facing side (extras.facing: north,
    // south, east or west; else the side toward the middle of the floor, which can be wrong when
    // the model includes a neighboring room); an oval mirror (extras.outline) gets an oval reflection
    const floorBox = new THREE.Box3();
    (floors.length ? floors : [root]).forEach((f) => floorBox.expandByObject(f));
    const mid = floorBox.getCenter(new THREE.Vector3());
    mirrors.forEach((m) => {
      const box = new THREE.Box3().setFromObject(m);
      const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
      const alongX = size.x > size.z;                 // north/south wall mirror spans x
      const w = alongX ? size.x : size.z;
      let o = m;
      while (o && !(o.userData && o.userData.outline)) o = o.parent;
      const geo = o ? new THREE.CircleGeometry(0.5, 96).scale(w, size.y, 1) : new THREE.PlaneGeometry(w, size.y);
      const r = new Reflector(geo, { textureWidth: 1024, textureHeight: 1024, color: 0xd8d8d8 });
      r.position.copy(c);
      if (alongX) {
        const facing = m.userData && m.userData.facing;
        const front = facing ? facing === "south" : c.z < mid.z;   // facing +z (south) or -z (north)
        r.position.z = (front ? box.max.z : box.min.z) + (front ? 0.001 : -0.001);
        if (!front) r.rotation.y = Math.PI;
      } else {
        const facing = m.userData && m.userData.facing;
        const east = facing ? facing === "east" : c.x < mid.x;     // on the west wall, facing east
        r.position.x = east ? box.max.x + 0.001 : box.min.x - 0.001;
        r.rotation.y = east ? Math.PI / 2 : -Math.PI / 2;
      }
      vg.add(r);
      m.visible = false;
    });

    // lights: the same cans as the render, sky light through every window and a low afternoon
    // sun (same direction as the renders); evening drops the sun and sky and dims the cans
    const fill = new THREE.HemisphereLight(0xfff6ea, 0xcfc6b8, 0.3);
    vg.add(fill);
    const quiet = cfg.noShadowLights || [];
    const cans = info.lights.map((l) => {
      const s = new THREE.SpotLight(0xffe2c4, l.power * 1.1, 9, THREE.MathUtils.degToRad(60), 0.7, 2);
      s.position.copy(plan(l.x, l.y, l.z));
      s.target.position.copy(plan(l.x, l.y, 0));
      s.castShadow = !quiet.some((p) => l.name.startsWith(p));
      s.shadow.mapSize.set(512, 512);
      s.shadow.bias = -0.0015;
      s.shadow.normalBias = 0.02;
      s.shadow.radius = 4;
      vg.add(s, s.target);
      return s;
    });
    const sky = (info.windows || []).map((w) => {
      const a = new THREE.RectAreaLight(0xf2f5ff, 5, w.w * IN, w.h * IN);   // near-white daylight
      const c = plan(w.cx, w.cy, w.cz);
      a.position.copy(c);
      a.lookAt(c.clone().add(new THREE.Vector3(w.into[0], 0, -w.into[1])));
      vg.add(a);
      return a;
    });
    const walk = info.walk;
    const sunAim = cfg.sunAim || (walk ? [(walk.x0 + walk.x1) / 2, (walk.y0 + walk.y1) / 2] : [0, 0]);
    const sd = (info.sun && info.sun.dir) || [0.55, -0.75, -0.42];   // direction the sunlight travels, plan axes
    const sunDir = new THREE.Vector3(sd[0], sd[2], -sd[1]).normalize();
    const sun = new THREE.DirectionalLight(0xfff0d8, 3.2);
    const aim = plan(sunAim[0], sunAim[1], 0);
    sun.target.position.copy(aim);
    sun.position.copy(aim.clone().addScaledVector(sunDir, -8));
    sun.castShadow = true;
    sun.shadow.mapSize.set(4096, 4096);
    Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 0.5, far: 20 });
    sun.shadow.bias = -0.0008;
    sun.shadow.normalBias = 0.03;
    sun.shadow.radius = 3;
    vg.add(sun, sun.target);
    const dayBg = new THREE.Color(0xb9cde6), nightBg = new THREE.Color(0x0b0f18);
    rig = {
      apply(m) {
        const night = m === "night";
        sun.visible = !night;
        sky.forEach((a) => { a.intensity = night ? 0.15 : 5; });
        cans.forEach((c, k) => { c.intensity = info.lights[k].power * (night ? 0.7 : 1.1); });
        fill.intensity = night ? 0.4 : 0.3;            // evening: stands in for can light bouncing off the floor
        fill.color.set(night ? 0xffd9b0 : 0xfff6ea);
        fill.groundColor.set(night ? 0xe2d3c0 : 0xcfc6b8);
        scene.environmentIntensity = night ? 0.15 : 0.45;
        scene.background = night ? nightBg : dayBg;
        baseExposure = night ? 1.0 : 0.82;
        renderer.toneMappingExposure = baseExposure * settings.brightness;
      },
    };
    setMode(mode);
    // mirror backlight glow on the wall
    root.traverse((o) => {
      if (o.isMesh && o.name.includes("mirror_back")) {
        const c = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3());
        const p = new THREE.PointLight(0xffd9b0, 0.6, 1.2, 2);
        p.position.copy(c);
        vg.add(p);
      }
    });

    buildDims();
    if (veil) {
      renderer.compile(scene, camera);              // the new materials' shaders, under the still
      requestAnimationFrame(() => requestAnimationFrame(() => { veil.style.opacity = "0"; }));
      setTimeout(() => veil.remove(), 800);
    }
    markProducts();
    if (!first) { showPending(); return; }   // switching designs keeps where you stand and look
    first = false;
    document.getElementById("loading").remove();
    buildViews();
    const v0 = new URLSearchParams(location.search).get("view");   // ?view=<camera> opens there
    goTo((v0 && info.cameras[v0] && v0) || cfg.start || (cfg.views && cfg.views[0][0]) || Object.keys(info.cameras)[0], false);
    resize();
    renderer.setAnimationLoop(tick);
    showPending();
    // ?probe=0.5,0.6: show the hover readout at that spot of the view (for checking without a mouse)
    const probe = new URLSearchParams(location.search).get("probe");
    if (probe) {
      const [fx, fy] = probe.split(",").map(Number);
      setTimeout(() => {
        const r = canvas.getBoundingClientRect();
        hoverAt({ clientX: r.left + fx * r.width, clientY: r.top + fy * r.height });
      }, 500);
    }
  }

  // design picker: cfg.variants = [[id, label], ...]; the first is the room's own export, the
  // rest load from variants/<id>/ (exported with --export web/variants/<id>). Needs the page
  // served (lib/serve.sh), not opened from disk.
  if (cfg.variants && location.protocol !== "file:") {
    const pk = document.createElement("div");
    pk.className = "daynight stage-var";
    pk.setAttribute("role", "group");
    pk.setAttribute("aria-label", "Design");
    let busy = false;
    picker = pk;
    cfg.variants.forEach(([id, label], k) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.setAttribute("aria-pressed", k === 0);
      b.addEventListener("click", async () => {
        if (busy || b.getAttribute("aria-pressed") === "true") return;
        busy = true;
        curDesign = id;
        pk.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
        b.textContent = label + " …";
        showChosen();
        setRenderDesign(k);
        try { await load(k === 0 ? "" : `variants/${id}/`); } catch (err) { console.error(err); }
        b.textContent = label;
        busy = false;
      });
      pk.appendChild(b);
    });
    controls.appendChild(pk);
    // "Make this the choice": the server keeps it, so this page and Plans open on it, and the home
    // page shows web/cards/<id>.jpg for the room. "Hide": the design leaves every tab (its files stay);
    // the hidden ones are listed below the pills to bring back.
    const ch = document.createElement("div");
    ch.className = "daynight stage-choose";
    ch.innerHTML = "<button></button><button>Hide</button>";
    const [chb, hdb] = ch.children;
    hdb.title = "Hide this option on every tab (bring it back from the Hidden list)";
    function showChosen() {
      const on = curDesign === window.CHOSEN;
      chb.textContent = on ? "✓ The choice" : "Make this the choice";
      chb.setAttribute("aria-pressed", on);
      hdb.hidden = on || curDesign === cfg.variants[0][0];   // the room's own design and the choice stay
    }
    const reopen = (design) => {   // the pills on every tab are built from the list: start over on it
      const q = new URLSearchParams(location.search);
      if (design) q.set("design", design); else q.delete("design");
      location.replace(location.pathname + (q.size ? "?" + q : "") + location.hash);
    };
    hdb.addEventListener("click", async () => {
      hdb.textContent = "Hiding …";
      try { await api(`/designs/${curDesign}`, "PATCH", { hidden: true }); } catch (err) { hdb.textContent = err.message; return; }
      reopen(null);
    });
    let hd = null;
    if (hiddenDesigns.length) {
      hd = document.createElement("div");
      hd.className = "daynight stage-hidden";
      hd.innerHTML = "<span>Hidden:</span>";
      hiddenDesigns.forEach((d) => {
        const b = document.createElement("button");
        b.textContent = d.label;
        b.title = "Show this option again";
        b.addEventListener("click", async () => {
          b.textContent = d.label + " …";
          try { await api(`/designs/${d.id}`, "PATCH", { hidden: false }); } catch (err) { b.textContent = err.message; return; }
          reopen(d.id);
        });
        hd.appendChild(b);
      });
    }
    chb.addEventListener("click", async () => {
      if (curDesign === window.CHOSEN || !ROOM) return;
      const want = curDesign;
      chb.textContent = "Saving …";
      // the room's home-page card, should the design have no card yet and no render to make one from:
      // this view, 800px wide
      composer.render();
      const shot = document.createElement("canvas");
      shot.width = 800;
      shot.height = Math.round(800 * renderer.domElement.height / renderer.domElement.width);
      shot.getContext("2d").drawImage(renderer.domElement, 0, 0, shot.width, shot.height);
      const camera0 = ((cfg.pairs || [])[0] || (cfg.views || [])[0] || [])[0];
      try {
        await api("/choice", "PUT", { design: want, camera: camera0, snapshot: shot.toDataURL("image/jpeg", 0.85) });
        window.CHOSEN = want;
      } catch (err) { console.error(err); chb.textContent = "Couldn't save"; return; }
      showChosen();
    });
    showChosen();
    controls.appendChild(ch);
    if (hd) controls.appendChild(hd);
    // ?design=<id> opens on that design, else the chosen one (once the room's own model has loaded)
    const want = new URLSearchParams(location.search).get("design") || window.CHOSEN;
    const k = cfg.variants.findIndex(([id]) => id === want);
    if (k > 0) {
      const wait = setInterval(() => { if (!first) { clearInterval(wait); pk.children[k].click(); } }, 200);
    }
  }

  // ---------- dimensions: lines from scene.json `dims`, colored by where the number came from;
  // the Dimensions button shows them all, hovering a wall shows the one along it, and a line
  // tied to dimensions.json (key) can be corrected: the server saves it and the worker rebuilds the model
  const SRC = {
    measured: ["Measured", "#2e7d32"], plan: ["From the floor plan", "#1f5fa8"], photo: ["From photos", "#7b3fa0"],
    design: ["Design choice", "#8a5233"], assumed: ["Guess, needs a tape measure", "#c25e00"],
  };
  const dimLayer = document.createElement("div");
  dimLayer.className = "dimlabels";
  stage.appendChild(dimLayer);
  let dims = [], dimsOn = location.search.includes("dims"), hoverDim = null, dimGroup = null;   // ?dims opens with them on
  let labelDim = null;              // the dimension whose label the pointer is over
  const UP = new THREE.Vector3(0, 1, 0);
  function tube(p, q, r, mat) {     // a thick segment p-q (WebGL draws lines 1 px wide)
    const d = q.clone().sub(p), len = d.length();
    const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, Math.max(len, 1e-4), 10), mat);
    m.position.copy(p).addScaledVector(d, 0.5);
    if (len > 1e-6) m.quaternion.setFromUnitVectors(UP, d.normalize());
    m.renderOrder = 11;
    return m;
  }
  const fmtIn = (n) => {
    n = Math.round(n * 4) / 4;
    const ft = Math.floor(n / 12), inch = n - ft * 12;
    return `${n}″` + (n >= 48 ? ` (${ft}′${inch ? " " + inch + "″" : ""})` : "");
  };
  const parseIn = (t) => {          // 42.5, 42 1/2, 3' 6.5", 3'6
    t = t.trim().replace(/[″"]/g, "").replace(/[′’]/g, "'");
    const frac = (x) => x.split(/\s+/).reduce((s, p) => s + (p.includes("/") ? p.split("/")[0] / p.split("/")[1] : +p), 0);
    if (t.includes("'")) { const [f, i] = t.split("'"); return +f * 12 + (i.trim() ? frac(i.trim()) : 0); }
    return frac(t);
  };
  function buildDims() {
    if (dimGroup) { scene.remove(dimGroup); disposeGroup(dimGroup); }
    dimGroup = new THREE.Group();
    scene.add(dimGroup);
    dimLayer.replaceChildren(measureEl);    // keeps the hover readout's label
    dims = (info.dims || []).map((d) => {
      const [ax, ay] = d.a, [bx, by] = d.b;
      const len = Math.hypot(bx - ax, by - ay) || 1;
      const nx = -(by - ay) / len, ny = (bx - ax) / len, z = d.z ?? 4;
      const entry = d.key && info.dimensions ? info.dimensions[d.key] : null;
      const src = entry ? entry.src : d.src;
      const col = (SRC[src] || SRC.assumed)[1];
      const a3 = plan(ax + nx * d.off, ay + ny * d.off, z), b3 = plan(bx + nx * d.off, by + ny * d.off, z);
      const mat = new THREE.LineBasicMaterial({ color: col, depthTest: false, transparent: true });
      const tick = (x, y) => [plan(x + nx * d.off, y + ny * d.off, z - 3), plan(x + nx * d.off, y + ny * d.off, z + 3)];
      const line = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints([a3, b3, ...tick(ax, ay), ...tick(bx, by)]), mat);
      line.renderOrder = 10;
      line.visible = false;
      dimGroup.add(line);
      // highlight: a thick line, dots at its ends, and extension lines back to the measured points
      const hm = new THREE.MeshBasicMaterial({ color: col, depthTest: false, transparent: true });
      const hl = new THREE.Group();
      hl.add(tube(a3, b3, 0.012, hm));
      const pa = plan(ax, ay, z), pb = plan(bx, by, z);
      if (d.off) { hl.add(tube(pa, a3, 0.005, hm), tube(pb, b3, 0.005, hm)); }
      [a3, b3].forEach((p) => {
        const dot = new THREE.Mesh(new THREE.SphereGeometry(0.03, 12, 8), hm);
        dot.position.copy(p); dot.renderOrder = 11; hl.add(dot);
      });
      hl.visible = false;
      dimGroup.add(hl);
      const el = document.createElement("button");
      el.className = "dimlabel" + (entry ? " editable" : "");
      el.style.borderLeftColor = col;
      el.style.setProperty("--dc", col);
      el.textContent = entry ? fmtIn(entry.value) : (d.label || fmtIn(len));
      el.title = entry ? `${entry.note} · ${(SRC[src] || SRC.assumed)[0]}${entry.override ? " (set by hand " + (entry.updated || "") + ")" : ""} · click to correct`
        : (SRC[src] || SRC.assumed)[0];
      el.hidden = true;
      if (entry) el.addEventListener("click", (e) => { e.stopPropagation(); editDim(d.key, entry, el); });
      dimLayer.appendChild(el);
      const rec = { d, line, hl, el, mid: a3.clone().lerp(b3, 0.5), seg: [ax, ay, bx, by] };
      el.addEventListener("pointerenter", () => { labelDim = rec; showDims(); });
      el.addEventListener("pointerleave", () => { if (labelDim === rec) labelDim = null; showDims(); });
      return rec;
    });
    // ?dims=<name> opens with that dimension highlighted (a link straight to one size)
    const want = new URLSearchParams(location.search).get("dims");
    if (want) labelDim = dims.find((m) => m.d.key === want) || null;
    showDims();
  }
  function showDims() {
    const hot = labelDim || hoverDim;
    dims.forEach((m) => {
      const v = dimsOn || m === hot;
      m.line.visible = v && m !== hot;
      m.hl.visible = m === hot;
      m.el.hidden = !v;
      m.el.classList.toggle("hot", m === hot);
    });
  }
  const dimBtn = document.createElement("div");
  dimBtn.className = "daynight stage-dims";
  dimBtn.innerHTML = `<button aria-pressed="${dimsOn}">Dimensions</button>`;
  dimBtn.firstChild.addEventListener("click", () => {
    dimsOn = !dimsOn;
    dimBtn.firstChild.setAttribute("aria-pressed", dimsOn);
    showDims();
  });
  controls.appendChild(dimBtn);
  function placeDimLabels() {
    const w = stage.clientWidth, h = stage.clientHeight;
    if (prodPos) {
      const p = prodPos.clone().project(camera);
      prodEl.style.visibility = p.z < 1 ? "visible" : "hidden";
      prodEl.style.left = `${(p.x + 1) / 2 * w}px`;
      prodEl.style.top = `${(1 - p.y) / 2 * h - 28}px`;
    }
    if (measurePos) {
      const p = measurePos.clone().project(camera);
      measureEl.style.left = `${(p.x + 1) / 2 * w}px`;
      measureEl.style.top = `${(1 - p.y) / 2 * h - 28}px`;
    }
    dims.forEach((m) => {
      if (m.el.hidden) return;
      const p = m.mid.clone().project(camera);
      const on = p.z < 1 && Math.abs(p.x) < 1.1 && Math.abs(p.y) < 1.1;
      m.el.style.visibility = on ? "visible" : "hidden";
      m.el.style.left = `${(p.x + 1) / 2 * w}px`;
      m.el.style.top = `${(1 - p.y) / 2 * h}px`;
    });
  }
  // hover readout (mouse): an object's width x depth x height from its box (scene.json
  // `objects`), or on a wall the stretch under the pointer, out to the next corner, trim or
  // cabinet each way, and its height; plus the named dimension running along it, if one is close
  const measureEl = document.createElement("div");
  measureEl.className = "dimlabel measure";
  measureEl.hidden = true;
  dimLayer.appendChild(measureEl);
  let measureGroup = null, measurePos = null;
  const measureMat = new THREE.MeshBasicMaterial({ color: 0xf2b134, depthTest: false, transparent: true });
  function clearMeasure() {
    if (measureGroup) { scene.remove(measureGroup); measureGroup.traverse((o) => o.geometry && o.geometry.dispose()); }
    measureGroup = null; measurePos = null; measureEl.hidden = true;
  }
  function showMeasure(segs, text, at) {
    clearMeasure();
    measureGroup = new THREE.Group();
    segs.forEach(([p, q]) => measureGroup.add(tube(p, q, 0.006, measureMat)));
    scene.add(measureGroup);
    measureEl.textContent = text;
    measureEl.hidden = false;
    measurePos = at;
  }
  const pretty = (n) => n.replace(/_/g, " ").replace(/\b(n|s|e|w)\b/g, (m) => ({ n: "north", s: "south", e: "east", w: "west" })[m]);
  const castFrom = (o, d) => {
    ray.set(o, d);
    ray.far = 30;
    const h = ray.intersectObjects(vgroup ? [vgroup] : [], true)[0];
    ray.far = Infinity;
    return h ? h.distance : null;
  };
  function hoverAt(e) {
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(vgroup ? [vgroup] : [], true)[0];
    let best = null, bd = 6;
    clearMeasure();
    if (hit) {
      const px = hit.point.x / IN, py = -hit.point.z / IN, pz = hit.point.y / IN;
      dims.forEach((m) => {
        const [ax, ay, bx, by] = m.seg;
        const L2 = (bx - ax) ** 2 + (by - ay) ** 2 || 1;
        const t = Math.max(0, Math.min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2));
        const dd = Math.hypot(px - (ax + t * (bx - ax)), py - (ay + t * (by - ay)));
        if (dd < bd) { bd = dd; best = m; }
      });
      // the smallest object whose box holds the point
      let ob = null, ov = Infinity;
      (info.objects || []).forEach((o) => {
        const tol = 1;
        if (px < o.min[0] - tol || px > o.max[0] + tol || py < o.min[1] - tol || py > o.max[1] + tol
            || pz < o.min[2] - tol || pz > o.max[2] + tol) return;
        const v = (o.max[0] - o.min[0]) * (o.max[1] - o.min[1]) * (o.max[2] - o.min[2]);
        if (v < ov) { ov = v; ob = o; }
      });
      const n = hit.face ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld) : null;
      if (ob) {
        const [x0, y0, z0] = ob.min, [x1, y1, z1] = ob.max;
        const c = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
        const segs = [];
        c.forEach(([x, y], k) => {
          const [x2, y2] = c[(k + 1) % 4];
          segs.push([plan(x, y, z0), plan(x2, y2, z0)], [plan(x, y, z1), plan(x2, y2, z1)], [plan(x, y, z0), plan(x, y, z1)]);
        });
        const prod = productOf(ob.name);
        showMeasure(segs, `${prod ? prod.name + " · " : ""}${pretty(ob.name)}: ${fmtIn(x1 - x0).split(" ")[0]} wide (E–W) × ${fmtIn(y1 - y0).split(" ")[0]} (N–S) × ${fmtIn(z1 - z0).split(" ")[0]} high`,
          plan((x0 + x1) / 2, (y0 + y1) / 2, z1));
      } else if (n && Math.abs(n.y) < 0.3) {         // a wall: measure along it and up/down
        const o = hit.point.clone().addScaledVector(n, 0.01);
        const t = new THREE.Vector3().crossVectors(n, UP).normalize();
        const d1 = castFrom(o, t), d2 = castFrom(o, t.clone().negate());
        const dn = castFrom(o, UP.clone().negate()), up = castFrom(o, UP);
        if (d1 && d2) {
          const e1 = o.clone().addScaledVector(t, d1), e2 = o.clone().addScaledVector(t, -d2);
          const segs = [[e1, e2]];
          let txt = `${fmtIn((d1 + d2) / IN)} along the wall`;
          if (dn && up) {
            segs.push([o.clone().addScaledVector(UP, -dn), o.clone().addScaledVector(UP, up)]);
            txt += ` · ${fmtIn((dn + up) / IN).split(" ")[0]} high`;
          }
          showMeasure(segs, txt, hit.point.clone());
        }
      }
    }
    if (best !== hoverDim) { hoverDim = best; showDims(); }
  }
  function editDim(key, entry, el) {
    document.querySelectorAll(".dimform").forEach((f) => f.remove());
    const f = document.createElement("form");
    f.className = "dimform";
    f.innerHTML = `<b>${key.replace(/_/g, " ")}</b><span class="dimnote">${entry.note || ""}</span>
      <label>Inches <input name="v" value="${entry.value}" inputmode="decimal" autocomplete="off"></label>
      <label>Source <select name="s">${Object.entries(SRC).map(([k, [lab]]) => `<option value="${k}"${k === entry.src ? " selected" : ""}>${lab}</option>`).join("")}</select></label>
      <label>Note <input name="n" value="${(entry.override ? entry.note : "").replace(/"/g, "&quot;")}" placeholder="e.g. taped 10/23"></label>
      <div class="dimbtns"><button type="submit">Save</button>${entry.override ? '<button type="button" data-reset>Back to ' + entry.default + '″</button>' : ""}<button type="button" data-cancel>Cancel</button></div>
      <span class="dimstatus" role="status"></span>`;
    f.style.left = el.style.left; f.style.top = el.style.top;
    stage.appendChild(f);
    f.v.focus(); f.v.select();
    const send = async (body) => {
      const st = f.querySelector(".dimstatus");
      f.querySelectorAll("button, input, select").forEach((x) => { x.disabled = true; });
      st.textContent = "Saving and rebuilding the model…";
      try {
        const res = await fetch("/api/dimension", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ room: ROOM, name: key, ...body }) });
        const out = await res.json();
        if (!res.ok) throw new Error(out.detail || res.statusText);
        // the worker on this computer re-exports the model (server/features/jobs.py): follow its job
        let job;
        for (let t = 0; ; t++) {
          job = await (await fetch(`/api/jobs/${out.job}`)).json();
          if (job.status === "done" || job.status === "failed") break;
          st.textContent = job.status === "queued" && t > 5 ? "Saved; waiting for the worker (is lib/serve.sh running?)" : "Saved; rebuilding the model…";
          await new Promise((ok) => setTimeout(ok, 1000));
        }
        if (job.status === "failed") throw new Error("the rebuild failed: " + job.log.slice(-300));
        st.textContent = `Rebuilt in ${Math.round(job.seconds)} s`;
        document.getElementById("hint").textContent = "Saved. Baked lighting is being redone (~8 min): reload the page then";
        document.querySelectorAll(".stage-var button").forEach((b, k) => b.setAttribute("aria-pressed", k === 0));
        await load("", true);
        f.remove();
      } catch (err) {
        st.textContent = location.protocol === "file:" ? "Saving needs the page served by lib/serve.sh" : `Not saved: ${err.message}`;
        f.querySelectorAll("button, input, select").forEach((x) => { x.disabled = false; });
      }
    };
    f.addEventListener("submit", (e) => {
      e.preventDefault();
      const v = parseIn(f.v.value);
      if (!(v > 0)) { f.querySelector(".dimstatus").textContent = "Type a size in inches, like 42.5 or 3' 6.5\""; return; }
      send({ value: v, src: f.s.value, note: f.n.value || entry.note });
    });
    f.querySelector("[data-cancel]").addEventListener("click", () => f.remove());
    const rs = f.querySelector("[data-reset]");
    if (rs) rs.addEventListener("click", () => send({ reset: true }));
    f.addEventListener("pointerdown", (e) => e.stopPropagation());
  }

  // ---------- products: web/inventory.js (from the room's inventory.json, by lib/tools/selections_page.py) lists
  // the room's products with have / ordered / need and the designs each is in. The sidebar lists the ones in the
  // design on show; picking one outlines its objects (scene.json `objects` whose names start with one of its
  // `where`) and walks over to look at it. ?show=<id> opens on one, switching design first if it's elsewhere.
  const INV = window.INVENTORY;
  const PRODUCTS = INV ? INV.groups.flatMap((g) => g.items) : [];
  let prodGroup = null, prodPos = null;
  const inDesign = (it) => !cfg.variants || !it.designs || it.designs.includes(curDesign);
  const objectsOf = (it) => (info && info.objects || []).filter((o) => (it.where || []).some((w) => o.name.startsWith(w)));
  const productOf = (name) => PRODUCTS.find((it) => inDesign(it) && (it.where || []).some((w) => name.startsWith(w)));
  const prodEl = document.createElement("button");
  prodEl.className = "dimlabel measure prodlabel";
  prodEl.hidden = true;
  prodEl.title = "Clear";
  prodEl.addEventListener("click", () => clearProduct());
  dimLayer.appendChild(prodEl);
  const prodLine = new THREE.MeshBasicMaterial({ color: 0x2f7df6, depthTest: false, transparent: true });
  const prodFill = new THREE.MeshBasicMaterial({ color: 0x2f7df6, depthTest: false, depthWrite: false, transparent: true, opacity: 0.1 });
  function clearProduct() {
    if (prodGroup) { scene.remove(prodGroup); prodGroup.traverse((o) => o.geometry && o.geometry.dispose()); }
    prodGroup = null; prodPos = null; prodEl.hidden = true;
    pressProduct(null);
  }
  // the pressed row, and its Details link to that product on the checklist
  function pressProduct(id) {
    document.querySelectorAll(".prod").forEach((b) => b.setAttribute("aria-pressed", b.dataset.id === id));
    document.querySelectorAll(".proddetail").forEach((a) => { a.hidden = a.dataset.id !== id; });
  }
  function showProduct(it) {
    if (!inDesign(it)) {
      const k = (cfg.variants || []).findIndex(([id]) => id === it.design);
      if (!picker || k < 0) return;
      pendingShow = it;
      picker.children[k].click();
      return;
    }
    clearProduct();
    const boxes = objectsOf(it);
    if (!boxes.length) return;
    prodGroup = new THREE.Group();
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    boxes.forEach((o) => {
      const [x0, y0, z0] = o.min, [x1, y1, z1] = o.max;
      for (let i = 0; i < 3; i++) { lo[i] = Math.min(lo[i], o.min[i]); hi[i] = Math.max(hi[i], o.max[i]); }
      const c = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
      c.forEach(([x, y], k) => {
        const [x2, y2] = c[(k + 1) % 4];
        prodGroup.add(tube(plan(x, y, z0), plan(x2, y2, z0), 0.006, prodLine), tube(plan(x, y, z1), plan(x2, y2, z1), 0.006, prodLine),
          tube(plan(x, y, z0), plan(x, y, z1), 0.006, prodLine));
      });
      const fill = new THREE.Mesh(new THREE.BoxGeometry(Math.max(x1 - x0, 0.2) * IN, Math.max(z1 - z0, 0.2) * IN, Math.max(y1 - y0, 0.2) * IN), prodFill);
      fill.position.copy(plan((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2));
      fill.renderOrder = 10;
      prodGroup.add(fill);
    });
    scene.add(prodGroup);
    prodEl.textContent = `${it.name}  ✕`;
    prodEl.hidden = false;
    prodPos = plan((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]);
    pressProduct(it.id);
    fly(viewOf(lo, hi), true);
  }
  // where to stand to see a box (plan inches): spots all round it inside the walk area, at three distances and two
  // heights, each scored by how many sight lines to points on the box reach it before something else is hit
  // (walls, cabinets); the most wins, ties going to the usual distance and to the side you're already on
  function viewOf(lo, hi) {
    const c = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
    const s = Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
    const d = Math.min(Math.max(s * 0.9 + 30, 40), 220);
    const box = new THREE.Box3(plan(lo[0], hi[1], lo[2]), plan(hi[0], lo[1], hi[2])).expandByScalar(0.02);
    const targets = [c, [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [lo[0], hi[1], hi[2]], [hi[0], hi[1], hi[2]]]
      .map(([x, y, z], k) => (k ? plan(x + (c[0] - x) * 0.2, y + (c[1] - y) * 0.2, z + (c[2] - z) * 0.2) : plan(x, y, z)));
    const here = Math.atan2(-pos.z / IN - c[1], pos.x / IN - c[0]);
    const w = info.walk;
    const sight = new THREE.Raycaster(), back = new THREE.Raycaster(), entry = new THREE.Vector3();
    // only what's on show can block (rays don't skip hidden meshes), gathered once
    const meshes = [];
    if (vgroup) vgroup.traverse((o) => { if (o.isMesh) { let v = o; while (v && v.visible) v = v.parent; if (!v) meshes.push(o); } });
    const clear = (eye, tp) => {
      const dir = tp.clone().sub(eye);
      const len = dir.length();
      sight.set(eye, dir.normalize());
      sight.far = len;
      const hit = sight.intersectObjects(meshes, false)[0];
      const into = sight.ray.intersectBox(box, entry) ? entry.distanceTo(eye) : len;
      if (hit && hit.distance < into - 0.03) return false;
      // and back from the box, since a wall seen from behind (from a closet, say) has no face toward the eye
      back.set(tp, dir.negate());
      back.near = len - into + 0.03;
      back.far = len;
      return !back.intersectObjects(meshes, false).length;
    };
    // every spot with its cost (off the usual distance, away from where you are), cheapest first; a spot that sees
    // all the points beats any that doesn't, so the first such one ends the search
    const spots = [];
    for (let a = 0; a < 16; a++) {
      const ang = (a / 16) * Math.PI * 2;
      const turn = Math.abs(Math.atan2(Math.sin(ang - here), Math.cos(ang - here)));
      for (const dist of [d, d * 0.65, d * 0.4]) {
        for (const lift of [0.5, 1.1]) {
          const x = c[0] + Math.cos(ang) * dist, y = c[1] + Math.sin(ang) * dist;
          if (w && (x < w.x0 + 6 || x > w.x1 - 6 || y < w.y0 + 6 || y > w.y1 - 6)) continue;
          const z = Math.min(Math.max(c[2] + s * lift * 0.5 + 10, 40), 84);
          if (!box.containsPoint(plan(x, y, z))) spots.push({ x, y, z, cost: Math.abs(dist - d) / d + turn * 0.3 });
        }
      }
    }
    spots.sort((p, q) => p.cost - q.cost);
    let best = null;
    for (const sp of spots) {
      const eye = plan(sp.x, sp.y, sp.z);
      let seen = 0;
      for (let k = 0; k < targets.length; k++) {
        if (best && seen + targets.length - k <= best.seen) break;   // can't win now
        if (clear(eye, targets[k])) seen++;
      }
      if (!best || seen > best.seen) best = { ...sp, seen };
      if (seen === targets.length) break;
    }
    if (!best) {                      // nowhere inside the walk area: the old way, clamped
      const L = Math.hypot(pos.x / IN - c[0], -pos.z / IN - c[1]) || 1;
      best = { x: c[0] + ((pos.x / IN - c[0]) / L) * d, y: c[1] + ((-pos.z / IN - c[1]) / L) * d, z: Math.min(Math.max(c[2] + s * 0.5 + 10, 40), 84) };
      if (w) { best.x = Math.min(Math.max(best.x, w.x0 + 6), w.x1 - 6); best.y = Math.min(Math.max(best.y, w.y0 + 6), w.y1 - 6); }
    }
    return lookFrom([best.x, best.y, best.z], c);
  }
  function showPending() {
    if (!pendingShow && !showPending.done) {
      showPending.done = true;
      const want = new URLSearchParams(location.search).get("show");
      pendingShow = (want && PRODUCTS.find((p) => p.id === want)) || null;
    }
    if (!pendingShow) return;
    const it = pendingShow;
    // in this design, or ?design= hasn't switched yet: wait for it; else switch (showProduct does)
    if (!inDesign(it) && new URLSearchParams(location.search).get("design") === it.design) return;
    pendingShow = null;
    showProduct(it);
  }
  // the sidebar: the room's products in the design on show, grouped, each with its picture, status and size
  const MARK = { have: ["Have it", "✓"], ordered: ["Ordered", "↻"], need: ["Still to get", ""] };
  let prodFilter = "all";
  function markProducts() {
    document.querySelectorAll(".prod").forEach((b) => {
      const it = PRODUCTS.find((p) => p.id === b.dataset.id);
      b.hidden = !inDesign(it) || (prodFilter !== "all" && it.status !== prodFilter);
      b.classList.toggle("off", !objectsOf(it).length);
    });
    document.querySelectorAll(".prodgroup").forEach((g) => { g.hidden = ![...g.querySelectorAll(".prod")].some((p) => !p.hidden); });
  }
  if (INV) {
    const aside = document.querySelector("#walk aside");
    const box = document.createElement("div");
    box.className = "products";
    const thumb = (it) => it.image ? `background-image:url('../${it.image}')` : it.swatch ? `background:${it.swatch}` : "";
    box.innerHTML = `<p class="eyebrow">Selections <a href="selections.html">checklist</a></p>
      <div class="tabs prodfilter" role="group" aria-label="Show">${[["all", "All"], ["need", "To get"], ["ordered", "Ordered"], ["have", "Have"]]
        .map(([f, l], k) => `<button data-f="${f}" aria-selected="${k === 0}">${l}</button>`).join("")}</div>` +
      INV.groups.map((g) => `<div class="prodgroup"><b class="prodhead">${g.name}</b><div class="items">` + g.items.map((it) => {
        const [label, mark] = MARK[it.status] || MARK.need;
        return `<button class="item prod" data-id="${it.id}" aria-pressed="false"><div class="swatch" style="${thumb(it)}"></div>
          <div><b><span class="mark ${it.status}" title="${label}">${mark}</span>${it.name}${(it.qty || 1) > 1 ? ` ×${it.qty}` : ""}</b>
          ${it.spec ? `<span class="dims">${it.spec}</span>` : ""}</div></button>
          <a class="proddetail" data-id="${it.id}" href="selections.html#${it.id}" hidden>Details, specs and notes →</a>`;
      }).join("") + "</div></div>").join("");
    aside.prepend(box);
    box.querySelectorAll(".prod").forEach((b) => b.addEventListener("click", () => {
      if (b.getAttribute("aria-pressed") === "true") { clearProduct(); return; }
      if (b.classList.contains("off")) { clearProduct(); pressProduct(b.dataset.id); return; }  // nothing to outline: just its Details link
      showProduct(PRODUCTS.find((p) => p.id === b.dataset.id));
    }));
    box.querySelectorAll(".prodfilter button").forEach((b) => b.addEventListener("click", () => {
      box.querySelectorAll(".prodfilter button").forEach((x) => x.setAttribute("aria-selected", x === b));
      prodFilter = b.dataset.f;
      markProducts();
    }));
    addEventListener("keydown", (e) => { if (e.key === "Escape") clearProduct(); });
  }

  // ---------- camera control: drag to look, tap floor to walk, WASD/arrows
  let yaw = 0, pitch = 0;
  const pos = new THREE.Vector3();
  let flight = null;

  function lookFrom(locIn, targetIn) {
    const p = plan(...locIn), t = plan(...targetIn);
    const d = t.clone().sub(p).normalize();
    return { pos: p, yaw: Math.atan2(-d.x, -d.z), pitch: Math.asin(d.y) };
  }
  function goTo(id, animate = true) {
    const c = info.cameras[id];
    const v = lookFrom(c.loc, c.target);
    v.pitch = Math.max(-0.6, Math.min(0.4, v.pitch * 0.8));
    fly(v, animate);
    document.querySelectorAll("#views button").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  }
  function fly(v, animate) {
    if (!animate || matchMedia("(prefers-reduced-motion: reduce)").matches) {
      pos.copy(v.pos); yaw = v.yaw; pitch = v.pitch; flight = null; return;
    }
    let dy = v.yaw - yaw;
    dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    flight = { from: { pos: pos.clone(), yaw, pitch }, to: { pos: v.pos, yaw: yaw + dy, pitch: v.pitch }, t: 0 };
  }
  function buildViews() {
    const el = document.getElementById("views");
    (cfg.views || []).forEach(([id, label]) => {
      const b = document.createElement("button");
      b.textContent = label; b.dataset.id = id;
      b.addEventListener("click", () => goTo(id));
      el.appendChild(b);
    });
  }

  const canvas = renderer.domElement;
  canvas.addEventListener("pointerleave", () => { clearMeasure(); if (hoverDim) { hoverDim = null; showDims(); } });
  let drag = null;
  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, moved: 0 };
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag) { if (e.pointerType === "mouse") hoverAt(e); return; }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.x = e.clientX; drag.y = e.clientY;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    yaw += dx * 0.004; pitch = Math.max(-1.3, Math.min(1.3, pitch + dy * 0.004));
    flight = null;
    document.querySelectorAll("#views button").forEach((b) => b.classList.remove("on"));
  });
  canvas.addEventListener("pointerup", (e) => {
    if (drag && drag.moved < 6) walkToPointer(e);
    drag = null;
  });
  const ray = new THREE.Raycaster();
  function walkToPointer(e) {
    const r = canvas.getBoundingClientRect();
    ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(scene.children, true)[0];
    if (!hit || !floors.includes(hit.object)) return;
    const eye = 62 * IN;
    const target = hit.point.clone(); target.y = eye;
    // stop a little short so you land facing what you clicked
    const dir = target.clone().sub(pos); dir.y = 0;
    const dist = dir.length();
    if (dist > 0.5) target.sub(dir.normalize().multiplyScalar(0.35));
    fly({ pos: target, yaw, pitch }, true);
  }
  const keys = new Set();
  addEventListener("keydown", (e) => { if (!e.target.closest("button, input, select")) keys.add(e.key.toLowerCase()); });
  addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const f = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
    pos.addScaledVector(f, -e.deltaY * 0.0015);
    flight = null;
  }, { passive: false });

  const clock = new THREE.Clock();
  let fpsFrames = 0, fpsSince = performance.now();
  function tick() {
    const dt = Math.min(clock.getDelta(), 0.05);
    fpsFrames++;
    if (settings.fps && performance.now() - fpsSince >= 500) {
      const c = renderer.domElement;
      fpsOut.textContent = `${Math.round((fpsFrames * 1000) / (performance.now() - fpsSince))} fps · ${c.width} × ${c.height}`;
      fpsFrames = 0;
      fpsSince = performance.now();
    }
    if (flight) {
      flight.t = Math.min(1, flight.t + dt / 0.9);
      const k = flight.t < 0.5 ? 2 * flight.t * flight.t : 1 - Math.pow(-2 * flight.t + 2, 2) / 2;
      pos.lerpVectors(flight.from.pos, flight.to.pos, k);
      yaw = flight.from.yaw + (flight.to.yaw - flight.from.yaw) * k;
      pitch = flight.from.pitch + (flight.to.pitch - flight.from.pitch) * k;
      if (flight.t >= 1) flight = null;
    }
    const f = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
    const s = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
    const v = 1.2 * dt;
    if (keys.has("w") || keys.has("arrowup")) pos.addScaledVector(f, v);
    if (keys.has("s") || keys.has("arrowdown")) pos.addScaledVector(f, -v);
    if (keys.has("a")) pos.addScaledVector(s, -v);
    if (keys.has("d")) pos.addScaledVector(s, v);
    if (keys.has("arrowleft")) yaw += dt * 1.5;
    if (keys.has("arrowright")) yaw -= dt * 1.5;
    camera.position.copy(pos);
    camera.rotation.set(pitch, yaw, 0, "YXZ");
    composer.render();
    placeDimLabels();
  }

  load().catch((err) => {
    document.getElementById("loading").textContent = "The 3D model didn't load. Reload the page to try again.";
    console.error(err);
  });
}
