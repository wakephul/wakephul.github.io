import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { ENTRIES, LINKS, SECRET } from "./content.js";

const $ = (id) => document.getElementById(id);
const byId = Object.fromEntries(ENTRIES.map((e, i) => [e.id, { ...e, n: String(i).padStart(2, "0") }]));
const order = ENTRIES.map((e) => e.id);
byId.secret = { ...SECRET, n: String(order.length).padStart(2, "0") };   // not in the index, not in the tour

// Camera framing and limits come from the Blender scene (blender/run.py writes room.json).
// `v` changes at every bake, so a returning visitor never mixes a new model with an old texture.
const res = await fetch("assets/room.json", { cache: "no-cache" });
if (!res.ok) throw new Error(`room.json: ${res.status}`);
const ROOM = await res.json();
const V = ROOM.v ? `?v=${ROOM.v}` : "";
const TARGET = new THREE.Vector3(...ROOM.target);
const HOME = { azim: ROOM.azim, elev: ROOM.elev, dist: ROOM.dist };
const FOV = 22;
const rad = THREE.MathUtils.degToRad;
const HALF = rad(FOV / 2);

const canvas = $("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
scene.background = new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue("--bg").trim());
const camera = new THREE.PerspectiveCamera(FOV, 1, 0.5, 300);   // far: on a small phone the whole room sits far away

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.enablePan = true;              // right button, or two fingers
controls.screenSpacePanning = true;
controls.zoomToCursor = true;           // the wheel goes towards what you point at
controls.minAzimuthAngle = rad(ROOM.azimLimits[0]);
controls.maxAzimuthAngle = rad(ROOM.azimLimits[1]);
controls.minPolarAngle = rad(90 - ROOM.elevLimits[1]);
controls.maxPolarAngle = rad(90 - ROOM.elevLimits[0]);
controls.minDistance = 2.2;
// wherever you wander, the point the camera looks at stays inside the room
const bounds = new THREE.Box3(new THREE.Vector3(0.15, 0.1, -4.05), new THREE.Vector3(4.25, 1.9, -0.15));
// framing may aim outside the room on purpose (to push a thing above the card on phones):
// after each flight the limits grow to include where it landed
let limits = bounds.clone();

// phones and tablets held upright get the stacked layout (same query as in style.css)
const stacked = matchMedia("(max-width: 760px), (orientation: portrait) and (max-width: 1100px)");
const wide = () => !stacked.matches;
let dirty = true;   // render only when something changed

function place(view) {
  const a = rad(view.azim), e = rad(view.elev);
  controls.target.copy(view.target);
  camera.position.set(Math.cos(e) * Math.sin(a), Math.sin(e), Math.cos(e) * Math.cos(a)).multiplyScalar(view.dist).add(view.target);
  camera.lookAt(view.target);
  dirty = true;
}

// Frames a sphere inside a free rectangle of the screen (CSS pixels): the sphere is centred in it and
// takes 1/zoom of its shorter side (`wide` > 1 for things wider than tall, like the whole room). The distance never drops below what the baked texture can take
// before it looks blurry (a metre of room never gets more than about 520 screen pixels).
function frame(center, radius, rect, { azim = HOME.azim, elev = HOME.elev, zoom = 1, wide = 1 } = {}) {
  const W = innerWidth, H = innerHeight;
  const room = Math.min((rect.x1 - rect.x0) / wide, rect.y1 - rect.y0);
  const dist = Math.max(H / 200, controls.minDistance, (radius / Math.sin(HALF)) * zoom * (H / room));
  const a = rad(azim), e = rad(elev);
  const right = new THREE.Vector3(Math.cos(a), 0, -Math.sin(a));
  const up = new THREE.Vector3(-Math.sin(e) * Math.sin(a), Math.cos(e), -Math.sin(e) * Math.cos(a));
  const perPx = (2 * dist * Math.tan(HALF)) / H;   // metres per screen pixel at the target
  const target = center.clone()
    .addScaledVector(right, (W / 2 - (rect.x0 + rect.x1) / 2) * perPx)
    .addScaledVector(up, ((rect.y0 + rect.y1) / 2 - H / 2) * perPx);
  return { azim, elev, dist, target };
}

// the overview: right of the welcome text on wide screens, between the text and the index on phones
function home() {
  const intro = $("intro"), index = $("index");
  const rect = wide()
    ? { x0: intro.offsetLeft + intro.offsetWidth, y0: 0, x1: innerWidth, y1: innerHeight }
    : { x0: 0, y0: intro.offsetTop + intro.offsetHeight, x1: innerWidth, y1: index.offsetTop };
  return frame(TARGET, HOME.dist * Math.sin(HALF), rect, { zoom: wide() ? 1.08 : 1.02, wide: 1.15 });
}

// a thing of the room: left of the card, or above it when the card is a bottom sheet
function viewOf(id, at) {
  let e = byId[id];
  const o = meshes[id], near = (f) => new THREE.Vector3(...f).distanceTo(at);
  // a thing in two places (the hoop and the ball): a click frames the part it landed on
  if (e.alt && at && near(e.alt.focus) < near(e.focus)) e = { ...e, ...e.alt };
  const sphere = e.focus ? new THREE.Sphere(new THREE.Vector3(...e.focus), e.focus[3])
    : o ? new THREE.Box3().setFromObject(o).getBoundingSphere(new THREE.Sphere()) : new THREE.Sphere(TARGET, 3.1);
  const rect = wide()
    ? { x0: 0, y0: 0, x1: card.offsetLeft, y1: innerHeight }
    : { x0: 0, y0: $("top").offsetTop + $("top").offsetHeight, x1: innerWidth, y1: innerHeight - 8 - snaps().peek };
  return frame(sphere.center, sphere.radius, rect, {
    azim: e.azim ?? (o ? 36 : HOME.azim), elev: e.elev ?? (o ? 22 : HOME.elev), zoom: o ? 1.5 : 1.1,
  });
}

let lastWidth = 0;
function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  // a rotated phone or a resized window: put the camera back where it belongs. Height-only changes
  // (a phone's address bar coming and going) leave alone whatever the visitor was looking at.
  if (innerWidth !== lastWidth) {
    if (wide()) { sheet.goal = null; sheet.v = 0; card.style.height = ""; }
    else if (opened) pull(false, false);
    const view = opened ? viewOf(opened, openedAt) : home();
    if (flight) flight.to = view;
    else { place(view); limits = bounds.clone().expandByPoint(view.target); settle(); }
  }
  lastWidth = innerWidth;
  bounds.expandByPoint(home().target);   // the overview may look at a point outside the room, that's fine
  limits.union(bounds);
  controls.maxDistance = Math.max(home().dist * 1.3, flight ? flight.to.dist : 0, camera.position.distanceTo(controls.target));
  dirty = true;
}

/* ---------- camera flights ---------- */
// A flight is six springs, one per number that places the camera (two angles, the distance, the point
// looked at). They are critically damped (no overshoot) and keep their speed when a new flight starts
// halfway, so clicking "next" twice in a row bends the path instead of stopping and restarting it.
// Controls stay live: dragging or zooming during a flight simply takes over from where the camera is.
const RESPONSE = 0.55;   // seconds; a spring has no fixed duration, this sets how quickly it gets there
const KEYS = ["azim", "elev", "dist", "x", "y", "z"];
let flight = null;   // { to, pos, vel } with pos and vel keyed by KEYS
function current() {
  const s = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
  return { azim: THREE.MathUtils.radToDeg(s.theta), elev: 90 - THREE.MathUtils.radToDeg(s.phi), dist: s.radius, target: controls.target.clone() };
}
const flat = (v) => ({ azim: v.azim, elev: v.elev, dist: v.dist, x: v.target.x, y: v.target.y, z: v.target.z });
function flyTo(view) {
  flight = flight ? { ...flight, to: view } : { to: view, pos: flat(current()), vel: Object.fromEntries(KEYS.map((k) => [k, 0])) };
}
// exact critically damped spring step (stable for any dt): moves x towards goal, returns [x, v]
function spring(x, v, goal, dt, omega = (2 * Math.PI) / RESPONSE) {
  const y = x - goal, a = v + omega * y, e = Math.exp(-omega * dt);
  return [goal + (y + a * dt) * e, (v - omega * a * dt) * e];
}
function endFlight() {
  const t = flight.to;
  // zooming out is limited, but never closer than where the flight landed: no jump when the controls take over
  controls.maxDistance = Math.max(home().dist * 1.3, t.dist, camera.position.distanceTo(controls.target));
  limits = bounds.clone().expandByPoint(controls.target);
  flight = null;
  settle();
}
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- room ---------- */
// Two bakes of the same room: "home" (room in colour, clickable things white) and "open" (the
// opposite). Each piece fades from one to the other on its own, so when a card opens only that
// thing takes its colours and the rest of the room goes white.
// Phones get the textures at half size: a quarter of the memory, and the room is small on screen anyway.
const small = Math.max(screen.width, screen.height) < 1000;
const texture = (state) => new THREE.TextureLoader().loadAsync(`assets/baked-${state}${small ? "-2048" : ""}.webp${V}`).then((t) => {
  t.flipY = false;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
});
const draco = new DRACOLoader().setDecoderPath("https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/");
const [homeMap, gltf] = await Promise.all([
  texture("home"),
  new GLTFLoader().setDRACOLoader(draco).loadAsync(`assets/room.glb${V}`),
]);
const openMap = { value: homeMap };   // until the second texture arrives, fading changes nothing

// The mirror tiles glint: a copy of them with a matcap (a little painted sphere of reflections) sits on the
// baked ones and makes each flash as you turn the room, since every tile hangs a few degrees off. The copy
// fades out with the room, leaving the tiles as they were baked in the white room.
function reflections() {
  // the room seen in a mirror: lavender, with lots of small lights. Tiles hang only a few degrees
  // off, so the lights have to be small and close together for each tile to catch a different one.
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  const dark = g.createRadialGradient(128, 118, 8, 128, 128, 132);
  dark.addColorStop(0, "#f1ebff");
  dark.addColorStop(0.55, "#b9a6ee");
  dark.addColorStop(1, "#6a54c0");
  g.fillStyle = dark;
  g.fillRect(0, 0, 256, 256);
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const glow = (x, y, r, col) => {
    const s = g.createRadialGradient(x, y, 0, x, y, r);
    s.addColorStop(0, col);
    s.addColorStop(0.35, col);
    s.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = s;
    g.fillRect(x - r, y - r, 2 * r, 2 * r);
  };
  const lights = ["#fff4e0", "#ffd28a", "#ff7cc2", "#d9ccff"];
  for (let k = 0; k < 170; k++) glow(rnd() * 256, rnd() * 256, 2 + rnd() * 5, lights[k % 4]);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const meshes = {}, pieces = [];
let mirrors = null, glow = null;
gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  const t = { value: 0 };   // 0 = home look, 1 = open look
  o.material = new THREE.MeshBasicMaterial({ map: homeMap });
  o.material.onBeforeCompile = (sh) => {
    sh.uniforms.openMap = openMap;
    sh.uniforms.t = t;
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <map_pars_fragment>", "#include <map_pars_fragment>\nuniform sampler2D openMap;\nuniform float t;")
      .replace("#include <map_fragment>", "diffuseColor *= mix(texture2D(map, vMapUv), texture2D(openMap, vMapUv), t);");
  };
  pieces.push({ mesh: o, t });
  if (byId[o.name]) meshes[o.name] = o;
  if (o.name === "glow") glow = o;
});
const tiles = gltf.scene.getObjectByName("mirrors");
if (tiles) {   // flat shading: the glb carries no normals, each tile's comes from its own face
  mirrors = new THREE.Mesh(tiles.geometry, new THREE.MeshMatcapMaterial({
    matcap: reflections(), flatShading: true, transparent: true, polygonOffset: true, polygonOffsetFactor: -1,
  }));
  tiles.add(mirrors);
}
scene.add(gltf.scene);

/* ---------- index ---------- */
const indexItems = {};
for (const id of order) {
  const e = byId[id];
  const li = document.createElement("li");
  const b = document.createElement("button");
  b.type = "button";
  b.innerHTML = `<i>${e.n}</i> ${e.title}`;
  b.addEventListener("click", () => open(id));
  b.addEventListener("pointerenter", () => { hovered = meshes[id] ?? null; });
  b.addEventListener("pointerleave", () => { hovered = null; });
  li.append(b);
  $("index").querySelector("ol").append(li);
  indexItems[id] = b;
}

/* ---------- pointing and clicking ---------- */
const ray = new THREE.Raycaster();
const ptr = new THREE.Vector2();
const label = $("label");
const card = $("card");
let hovered = null, pressed = null, opened = null, downAt = null, moved = null, returnTo = null;
let pickedAt = null, openedAt = null;   // where the last pick landed, where the open thing was clicked

function pick(e) {
  ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ptr, camera);
  const hit = ray.intersectObjects(scene.children, true)[0];   // the grey room hides what is behind it
  pickedAt = hit?.point ?? null;
  return hit && meshes[hit.object.name] ? hit.object : null;
}
function hover(e) {
  hovered = pick(e);
  if (hovered?.name === "secret") hovered = null;
  canvas.classList.toggle("pointing", !!hovered);
  label.hidden = !hovered;
  if (hovered) {
    const en = byId[hovered.name];
    label.innerHTML = `<i>${en.n}</i> ${en.title}`;
    label.style.transform = `translate(${e.clientX + 16}px, ${e.clientY + 14}px)`;
  }
}

// hover is tested once per frame, and not while dragging the room around
canvas.addEventListener("pointermove", (e) => { if (e.pointerType !== "touch" && !e.buttons) moved = e; });
canvas.addEventListener("pointerleave", () => { moved = null; hovered = null; label.hidden = true; });
canvas.addEventListener("pointerdown", (e) => {
  downAt = [e.clientX, e.clientY];
  if (e.pointerType === "touch") { const o = pick(e); pressed = o && o.name !== "secret" ? o : null; }   // feedback on touch-down
});
canvas.addEventListener("pointermove", (e) => {
  if (downAt && Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) { pressed = null; downAt = null; }   // it became a drag
});
canvas.addEventListener("pointercancel", () => { pressed = null; });
canvas.addEventListener("pointerup", (e) => {
  const lit = pressed;
  pressed = null;
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 6) return; // it was a drag
  const o = pick(e);
  if (e.pointerType === "touch" && o && o.name !== "secret" && o !== lit) return;   // open only what lit up under the finger
  if (o) open(o.name, pickedAt);
  else if (opened) close();
});

// double click on the room (not on a white thing): fly closer to that point
canvas.addEventListener("dblclick", (e) => {
  if (opened || pick(e)) return;
  ray.setFromCamera(ptr.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1), camera);
  const hit = ray.intersectObjects(scene.children, true)[0];
  if (!hit) return;
  const now = current();
  flyTo({ ...now, target: hit.point.clamp(bounds.min, bounds.max), dist: Math.max(controls.minDistance + 1, now.dist * 0.55) });
});
const resetButton = $("reset");
// "the overview": zoomed out about as far as the start, looking from about the same side at about the same
// spot. Then the welcome text comes back and the way-back button goes away.
const overview = () => {
  const h = home(), c = current();
  return c.dist > 0.85 * h.dist && Math.abs(c.azim - h.azim) < 15 && Math.abs(c.elev - h.elev) < 15
    && c.target.distanceTo(h.target) < 0.15 * h.dist;
};
const settle = () => {
  if (opened || flight) return;   // a flight calls it again when it lands
  const o = overview();
  away($("intro"), !o);
  resetButton.hidden = o;
};
resetButton.addEventListener("click", () => { resetButton.hidden = true; flyTo(home()); });

// once people start looking around, the welcome text gets out of the way
let looking = false, gliding = false, auto = false;
const away = (el, yes) => { el.classList.toggle("away", yes); el.inert = yes; };
controls.addEventListener("start", () => { looking = true; });
controls.addEventListener("end", () => { looking = false; });   // the room may still glide: settle() runs when it stops
controls.addEventListener("change", () => {
  if (!looking || auto) return;   // a press alone doesn't count: only a real drag, pinch or wheel
  away($("intro"), true);
  if (flight) endFlight();   // the visitor grabbed the camera mid-flight: it stays where it is
});

/* ---------- the card ---------- */
const linkList = (keys) => `<div class="links">${keys.map((k) => `<a href="${LINKS[k].url}" target="_blank" rel="noopener">${LINKS[k].label}</a>`).join("")}</div>`;
const paperList = (ps) => `<ul class="papers">${ps.map((p) => `<li><span class="y">${p.year}</span>${p.url
  ? `<a href="${p.url}" target="_blank" rel="noopener">${p.title}</a>` : `<span class="t">${p.title}</span>`}<span class="v">${p.venue}</span></li>`).join("")}</ul>`;

// every sentence on its own line: a line break after each full stop (not after "...", not at the end)
const lines = (html) => html.replace(/(?<!\.)\.\s+(?=[^\s<])/g, ".<br>");

function render(e) {
  let html = lines(e.body ?? "");
  for (const b of e.blocks ?? []) {
    html += `<h3>${b.title}</h3>${lines(b.html ?? "")}${b.list ? `<ul>${b.list.map((x) => `<li>${x}</li>`).join("")}</ul>` : ""}${b.papers ? paperList(b.papers) : ""}`;
  }
  if (e.trick) html += `<div class="trick" id="trick"></div>`;
  if (e.links) html += linkList(e.links);
  return html;
}

const img = $("cutout");
img.addEventListener("load", () => img.classList.remove("wait"));
// the two circles behind each cut-out: two inks per card, taking turns
const INKS = [["var(--pink)", "var(--lilac)"], ["var(--sun)", "var(--pink)"], ["var(--lilac)", "var(--sun)"]];

function open(id, at = null) {
  const e = byId[id];
  if (!e) return;
  if (!opened) returnTo = document.activeElement;
  opened = id;
  $("count").innerHTML = `<b>${e.n}</b> / ${String(order.length - 1).padStart(2, "0")}`;
  $("card-title").textContent = e.title;
  $("kicker").textContent = e.kicker ?? "";
  const i = order.indexOf(id);   // -1 for the secret card
  $("sticker").hidden = id === "me" || id === "secret";
  card.style.setProperty("--ink-a", INKS[Math.max(i, 0) % 3][0]);
  card.style.setProperty("--ink-b", INKS[Math.max(i, 0) % 3][1]);
  if (!$("sticker").hidden && !img.src.endsWith(`/${id}.webp${V}`)) {
    img.classList.add("wait");   // keeps its place, so nothing jumps when it arrives
    img.src = `assets/cutouts/${id}.webp${V}`;
  }
  $("card-body").innerHTML = render(e);
  if (e.trick) trick($("trick"));
  const prev = byId[order[i - 1]], next = i < 0 ? null : byId[order[i + 1]];
  $("prev").hidden = !prev;
  $("prev").textContent = prev ? `← ${prev.title}` : "";
  $("next").textContent = next ? `${next.title} →` : "fine →";
  $("dots").innerHTML = order.map((k) => `<i${k === id ? ' class="on"' : ""}></i>`).join("");
  const wasClosed = card.hidden;
  if (wasClosed) pull(false, false);
  card.hidden = false;
  card.inert = false;
  $("card-scroll").scrollTop = 0;
  away($("intro"), true);
  away($("index"), true);
  resetButton.hidden = true;
  for (const [k, b] of Object.entries(indexItems)) b.classList.toggle("on", k === id);
  label.hidden = true;
  if (wasClosed || !card.contains(document.activeElement)) $("card-title").focus({ preventScroll: true });
  openedAt = at;
  flyTo(viewOf(id, at));
}

function close() {
  const was = opened;
  opened = null;
  card.hidden = true;
  card.inert = true;
  away($("intro"), false);
  away($("index"), false);
  for (const b of Object.values(indexItems)) b.classList.remove("on");
  const back = returnTo?.isConnected && !card.contains(returnTo) && returnTo !== document.body ? returnTo : indexItems[was];
  back?.focus({ preventScroll: true });
  flyTo(home());
}

function step(d) {
  if (opened === "secret") return close();
  const i = opened ? order.indexOf(opened) + d : 0;
  if (i >= order.length) close();
  else if (i >= 0) open(order[i]);
}
$("close").addEventListener("click", close);
/* phones: the card is a sheet you can drag by its grip or header. It follows the finger 1:1, resists past
   the top, and on release goes where the flick was heading (half open, full, or closed) on a spring. */
const grip = $("grip");
const sheet = { h: 0, v: 0, goal: null, drag: null };
const snaps = () => ({ peek: Math.round(innerHeight * 0.54), full: innerHeight - 70 });
const setSheet = (h) => { sheet.h = h; card.style.height = `${h}px`; };
function pull(up, animate = true) {
  const goal = snaps()[up ? "full" : "peek"];
  grip.setAttribute("aria-label", up ? "abbassa la scheda" : "allarga la scheda");
  if (wide()) return;
  if (!animate || calm) { sheet.goal = null; sheet.v = 0; setSheet(goal); } else sheet.goal = goal;
}
grip.addEventListener("click", () => { if (!sheet.dragged) pull(sheet.h < snaps().full - 4); });
card.addEventListener("pointerdown", (e) => {
  sheet.dragged = false;
  if (wide() || !e.target.closest(".card-top, #grip") || e.target.closest("#close")) return;
  sheet.drag = { y0: e.clientY, h0: sheet.h, moved: false, trail: [[e.timeStamp, e.clientY]], id: e.pointerId };
});
card.addEventListener("pointermove", (e) => {
  const d = sheet.drag;
  if (!d || e.pointerId !== d.id) return;
  if (e.pointerType === "mouse" && !e.buttons) { sheet.drag = null; card.classList.remove("dragging"); return; }   // a release we missed
  const dy = e.clientY - d.y0;
  if (!d.moved && Math.abs(dy) < 6) return;   // a few pixels of slack, so taps stay taps
  if (!d.moved) {
    d.moved = true;
    d.h0 = sheet.h;   // grabbed mid-spring: it carries on from where it is, under the finger
    d.y0 = e.clientY;
    sheet.goal = null;
    card.setPointerCapture(e.pointerId);
    card.classList.add("dragging");
  }
  const { full } = snaps();
  let h = d.h0 - dy;
  if (h > full) h = full + rubberband(h - full, innerHeight);   // past the top it gives way less and less
  setSheet(Math.max(0, h));
  d.trail = [...d.trail.slice(-5), [e.timeStamp, e.clientY]];
});
const release = (e) => {
  const d = sheet.drag;
  if (!d || e.pointerId !== d.id) return;
  card.classList.remove("dragging");
  sheet.drag = null;
  sheet.dragged = d.moved;   // the grip's click, right after, must not count a drag as a tap
  if (!d.moved) return;
  // speed of the last 100 ms only: a pause before lifting the finger means no flick
  const trail = [...d.trail, [e.timeStamp, e.clientY]].filter(([t]) => e.timeStamp - t <= 100);
  const [t0, y0] = trail[0], [t1, y1] = trail[trail.length - 1];
  sheet.v = trail.length > 1 && t1 > t0 ? -((y1 - y0) / (t1 - t0)) * 1000 : 0;   // px/s, positive = growing
  const projected = sheet.h + project(sheet.v);
  const { peek, full } = snaps(), stops = [0, peek, full];
  const nearest = (h) => stops.reduce((a, b) => (Math.abs(b - h) < Math.abs(a - h) ? b : a));
  // one stop per flick: a hard flick down from full stops half way instead of closing the card
  const from = stops.indexOf(nearest(d.h0)), to = stops.indexOf(nearest(projected));
  const target = stops[Math.min(from + 1, Math.max(from - 1, to))];
  if (target === 0) close();
  else pull(target === full);
};
card.addEventListener("pointerup", release);
card.addEventListener("pointercancel", release);
// where a flick would come to rest if it decelerated like a scroll (Apple's projection, d = 0.998)
const project = (v, d = 0.998) => ((v / 1000) * d) / (1 - d);
const rubberband = (over, size, c = 0.55) => (over * size * c) / (size + c * Math.abs(over));
// sheet spring: a little bounce, because a flick carried momentum into it (damping 0.8, response 0.3 s)
function stepSheet(dt) {
  if (wide() || sheet.goal === null || sheet.drag?.moved) return;
  const omega = (2 * Math.PI) / 0.3, zeta = 0.8;
  for (let t = 0; t < dt; t += 1 / 240) {
    const h = Math.min(1 / 240, dt - t);
    sheet.v += (-omega * omega * (sheet.h - sheet.goal) - 2 * zeta * omega * sheet.v) * h;
    sheet.h += sheet.v * h;
  }
  if (Math.abs(sheet.h - sheet.goal) < 0.5 && Math.abs(sheet.v) < 5) { sheet.h = sheet.goal; sheet.goal = null; sheet.v = 0; }
  card.style.height = `${sheet.h}px`;
}
// a sideways swipe on the card goes to the next or previous thing
let swipe = null;
card.addEventListener("touchstart", (e) => { swipe = [e.touches[0].clientX, e.touches[0].clientY]; }, { passive: true });
card.addEventListener("touchend", (e) => {
  if (!swipe || sheet.drag?.moved) return (swipe = null);
  const dx = e.changedTouches[0].clientX - swipe[0], dy = e.changedTouches[0].clientY - swipe[1];
  if (Math.abs(dx) > 70 && Math.abs(dy) < 45) step(dx < 0 ? 1 : -1);
  swipe = null;
});
if (matchMedia("(pointer: coarse)").matches) $("hint").textContent = "un dito per girare · due per avvicinarti e spostarti";
$("prev").addEventListener("click", () => step(-1));
$("next").addEventListener("click", () => step(1));
$("tour").addEventListener("click", () => step(0));
document.querySelector(".brand").addEventListener("click", (ev) => { ev.preventDefault(); if (opened) close(); else open("me"); });
addEventListener("keydown", (e) => {
  if (!opened) return;
  if (e.key === "Escape") close();
  if (e.key === "ArrowRight") step(1);
  if (e.key === "ArrowLeft") step(-1);
});

/* ---------- easter eggs ---------- */
// ↑↑↓↓←→←→ b a: a party, for eight seconds. typing "wakephul": it rains w's.
const KONAMI = "ArrowUp ArrowUp ArrowDown ArrowDown ArrowLeft ArrowRight ArrowLeft ArrowRight b a";
let typed = [], party = 0;
addEventListener("keydown", (e) => {
  if (e.target.closest?.("input, textarea")) return;
  typed = [...typed, e.key].slice(-10);
  if (typed.join(" ") === KONAMI && !calm) { party = 8; dirty = true; }   // it flashes: not for reduced motion
  if (typed.slice(-8).join("").toLowerCase() === "wakephul") rain();
});
function rain() {
  if (calm) return;
  for (let k = 0; k < 40; k++) {
    const w = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    w.setAttribute("class", "rain");
    w.setAttribute("aria-hidden", "true");
    w.innerHTML = '<use href="#w" />';
    w.style.setProperty("--x0", `${20 + Math.random() * 40}px`);
    w.style.setProperty("--x1", `${Math.random() * innerWidth}px`);
    w.style.setProperty("--r", `${(Math.random() - 0.5) * 720}deg`);
    w.style.animationDuration = `${1.6 + Math.random() * 1.8}s`;
    w.style.animationDelay = `${Math.random() * 0.6}s`;
    w.addEventListener("animationend", () => w.remove());
    document.body.append(w);
  }
}
console.log("%cw", "font: italic 56px 'Instrument Serif', Georgia, serif; color: #6d3fe6; text-shadow: 3px 2px 0 #f2a7c3");
console.log("ciao! guardare il codice degli altri è sempre una buona idea. la stanza è fatta con blender e three.js, il resto lo trovi su https://github.com/wakephul");

/* ---------- a small card trick: the card you think of disappears ---------- */
function trick(el) {
  const face = ([r, s]) => `<div class="pc${"♥♦".includes(s) ? " red" : ""}">${r}<b>${s}</b></div>`;
  const first = [["K", "♠"], ["Q", "♥"], ["J", "♣"], ["K", "♦"], ["Q", "♠"], ["J", "♥"]];
  const after = [["K", "♣"], ["Q", "♦"], ["J", "♠"], ["K", "♥"], ["Q", "♣"]];   // none of these was there before
  const show = (text, hand, button, then) => {
    const focused = el.contains(document.activeElement);
    el.innerHTML = `<p>${text}</p><div class="hand">${hand.map(face).join("")}</div><button type="button">${button}</button>`;
    const b = el.querySelector("button");
    b.onclick = then;
    if (focused) b.focus();
  };
  const start = () => show("pensa a una di queste carte (non cliccarla, tienila a mente).", first, "fatto", gone);
  const gone = () => show("la tua non c'è più.<br>abracadabra", after, "di nuovo", start);
  start();
}

// for development: with ?debug in the address, room.open("secret") and room.close() work from the console
if (new URLSearchParams(location.search).has("debug")) window.room = { open, close };

/* ---------- go ---------- */
addEventListener("touchstart", () => {}, { passive: true });   // lets iOS show :active on press
texture("open").then((t) => { openMap.value = t; dirty = true; }, () => {});   // without it the room just never changes colour
addEventListener("resize", resize);
card.inert = true;
resize();
place(home());
const loading = $("loading");
loading.classList.add("done");
loading.addEventListener("transitionend", () => { loading.hidden = true; }, { once: true });

const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  // long frames (a busy phone, a background tab) count as a quarter of a second at most,
  // so a flight never ends in a single jump
  const dt = Math.min(clock.getDelta(), 0.25);
  if (moved) { hover(moved); moved = null; }
  stepSheet(dt);
  auto = true;   // changes from this call are the flight's or the damping's, not the visitor's
  const stirred = controls.update();
  auto = false;
  if (stirred) {   // also used up during flights, so no leftover spin after landing
    dirty = true;
    if (!flight) gliding = true;
  } else if (gliding && !looking) {   // the camera has just come to rest after a gesture
    gliding = false;
    settle();
  }
  if (!flight) {
    const t = controls.target, c = t.clone().clamp(limits.min, limits.max);
    if (!c.equals(t)) { camera.position.add(c.clone().sub(t)); t.copy(c); dirty = true; }
  }
  if (flight) {
    const goal = flat(flight.to), { pos, vel } = flight;
    let rest = true;
    for (const k of KEYS) {
      [pos[k], vel[k]] = calm ? [goal[k], 0] : spring(pos[k], vel[k], goal[k], dt);
      if (Math.abs(pos[k] - goal[k]) > 2e-3 || Math.abs(vel[k]) > 2e-3) rest = false;
    }
    place({ azim: pos.azim, elev: pos.elev, dist: pos.dist, target: new THREE.Vector3(pos.x, pos.y, pos.z) });
    if (rest) { place(flight.to); endFlight(); }
  }
  // the room goes white while a thing is open; a thing takes its colours when open or pointed at
  const fade = calm ? 1 : Math.min(1, dt * 4);
  for (const { mesh, t } of pieces) {
    // the secret tile is part of the room: it never lights up on its own
    const roomWhite = +(opened !== null && opened !== "me" && opened !== "secret");
    const want = byId[mesh.name] && mesh.name !== "secret" ? +(mesh === hovered || mesh === pressed || mesh.name === opened) : roomWhite;
    if (Math.abs(t.value - want) > 0.002) { t.value += (want - t.value) * fade; dirty = true; }
    else t.value = want;
    if (byId[mesh.name] && mesh.name !== "secret") mesh.material.color.setScalar(1 + 0.1 * (1 - t.value));   // optical white
    if (mirrors && mesh.name === "room") { mirrors.material.opacity = 1 - t.value; mirrors.visible = t.value < 0.99; }
  }
  if (party > 0) {   // the bulbs and the neon blink, the mirrors spin their reflections
    party = Math.max(0, party - dt);
    const time = clock.elapsedTime;
    if (glow) glow.material.color.setScalar(party ? (Math.sin(time * 11) > 0 ? 1.3 : 0.2) * (0.75 + 0.25 * Math.sin(time * 37)) : 1);
    if (mirrors) { mirrors.material.matcap.center.set(0.5, 0.5); mirrors.material.matcap.rotation = party ? time * 2.5 : 0; }
    dirty = true;
  }
  if (dirty) renderer.render(scene, camera);
  dirty = false;
});
