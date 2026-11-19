// Zifiri Saatler · çizgi Short yönetmeni
// work/plan.json'daki çekim planını cizgi-short motoruyla canlandırır.
// Her video için kod yazılmaz: plan (Gemini) → bu dosya → kareler.
// Motor: cizgi-short — Burak Özer (@burakozerweb), MIT.
export const meta = { fps: 30, tail: 0.6, capStyle: { y: 0.74 } };

const NOCAP = typeof location !== "undefined" && location.search.includes("nocap");  // kapak karesi: yazısız
let P = null;          // plan
let SH = [];           // çekim tablosu (alt çekimler dahil)
const LOC = {};        // kurulan mekânlar: ad -> { x, light, ... }
const R = {};          // çekim içinde oynatılan objeler

// ---------------------------------------------------------------- ışık
const LIGHT = {
  zifiri: { sun: "#9fb4ff", sunI: 0.6, az: 205, el: 38, sky: "#1c2550", ground: "#161630", hemiI: 0.62, amb: 0.17, top: "#050a24", bot: "#24306a", fog: "#141d40", fogNear: 24, fogFar: 115, card: "#cfd5f2", sat: 1.06, warm: -0.03, con: 1.12, vig: 0.52 },
  icgece: { sun: "#ffd9a8", sunI: 0.75, az: -40, el: 55, sky: "#3a2a30", ground: "#2a1a14", hemiI: 0.7, amb: 0.2, top: "#2a1c22", bot: "#5a3a2a", fog: "#2a1c1c", fogNear: 18, fogFar: 80, card: "#f4dcc4", sat: 1.08, warm: 0.05, con: 1.1, vig: 0.5 },
  gece: "night", dramatik: "dramatic", altin: "golden", gunduz: "day", ic: "interior",
};
const L = (n) => LIGHT[n] || n;

// ---------------------------------------------------------------- oyuncular
const PRESET = {
  bekci: { shirt: "#2a3550", jacket: "#1f2a40", buttons: "#e8c45a", belt: "#6b4428", pants: "#2b2633", hat: "fez", hatCol: "#9a2a2a", moustache: "#dcdcdc", build: "stout", skin: "#f2d2b0", seed: 7 },
  koylu_erkek: { shirt: "#b8865a", pants: "#4a3f35", belt: "#8a2f2a", hat: "fez", hatCol: "#8a2f2a", moustache: "#3a2a20", skin: "#e9c3a0" },
  koylu_kadin: { dress: "#7a3f5a", shirt: "#7a3f5a", apron: "#efe3c8", hair: "long", hairCol: "#3a2a20", skin: "#f6dcc0" },
  yasli_kadin: { dress: "#4a4a6a", shirt: "#4a4a6a", hair: "bun", hairCol: "#dedede", build: "stout", skin: "#f6dcc0" },
  yasli_adam: { shirt: "#6a5a4a", jacket: "#3a3a3a", beard: "#e6e6e6", hat: "kavuk", build: "stout", skin: "#e9c3a0" },
  cocuk: { build: "kid", shirt: "#3f6fb5", pants: "#2b2633", hair: "short", hairCol: "#3a2a20", skin: "#f6dcc0" },
  pasa: { jacket: "#22305a", shirt: "#22305a", buttons: "#e8c45a", belt: "#b8262e", hat: "fez", hatCol: "#b8262e", moustache: "#2a1d16", build: "stout", skin: "#f0d0b0" },
  padisah: { jacket: "#6a2a6a", shirt: "#b8262e", hat: "turban", hatCol: "#f4efe4", beard: "#2a1d16", belt: "#e8c45a", skin: "#f0d0b0" },
  yeniceri: { shirt: "#a8343e", jacket: "#2f5f8a", belt: "#e8c45a", hat: "turban", hatCol: "#f4efe4", moustache: "#2a1d16", skin: "#e9c3a0" },
  muhafiz: { shirt: "#3a4a3a", jacket: "#5a3a2a", hat: "helmet", moustache: "#3a2a20", build: "stout", skin: "#e9c3a0" },
  tuccar: { shirt: "#e8a33c", jacket: "#6b4428", hat: "fez", hatCol: "#b8262e", build: "stout", beard: "#3a2a20", skin: "#f0d0b0" },
  mimar: { shirt: "#f4efe4", jacket: "#5a6b8a", hat: "kavuk", beard: "#7a7a7a", glasses: true, skin: "#f0d0b0" },
  hanim: { dress: "#2f5f6a", shirt: "#2f5f6a", hair: "bun", hairCol: "#2a1d16", skin: "#fbe8d4" },
  balikci: { shirt: "#3f6f8a", pants: "#2b2633", hat: "cap", hatCol: "#2b3a4a", beard: "#3a2a20", skin: "#d9a882" },
  asker: { shirt: "#5d6b3a", pants: "#4a4f35", belt: "#3a2a20", hat: "fez", hatCol: "#7a2a2a", moustache: "#3a2a20", skin: "#e9c3a0" },
  gezgin: { shirt: "#8c6a3a", jacket: "#4a3a2a", hat: "fedora", hatCol: "#3a2a20", beard: "#5a4030", skin: "#f0d0b0" },
  hayalet: { dress: "#eef2fa", shirt: "#eef2fa", skin: "#eef2fa", hair: "long", hairCol: "#c8d0e0" },
};
const MOOD = {
  korku: { face: "scared", arms: "up", sweat: true }, saskin: { face: "shock", arms: "up" }, merak: { face: "think", arms: "chin" },
  sinsi: { face: "sly", arms: "hip" }, uzgun: { face: "sad", arms: "hang" }, mutlu: { face: "happy", arms: "present" },
  kizgin: { face: "angry", arms: "point" }, dusunceli: { face: "think", arms: "think" }, anlatan: { face: "talk", arms: "present" },
  urkek: { face: "nervous", arms: "hang", sweat: true }, kararli: { face: "determined", arms: "hip" }, gururlu: { face: "smug", arms: "cross" },
  hayran: { face: "wow", arms: "cheer" }, uykulu: { face: "sleep", arms: "cross" },
};
const FXK = { soru: "question", unlem: "exclaim", ter: "sweat", fikir: "idea", duman: "puff", kurukafa: "skull", yildiz: "sparkle", kalp: "hearts", kizginlik: "anger", zzz: "zzz", para: "money", toz: "dust", hiz: "lines" };
const PROP = { fener: "lantern", mektup: "letter", anahtar: "key", altin: "bag", para: "coin", parsomen: "scroll", kitap: "paper", buyutec: "magnifier", kalem: "pen" };

// ---------------------------------------------------------------- mekânlar
// Her mekân (0,0,0) çevresinde kurulur; sahne alanı x∈[-2,2], z∈[-3,1].
// Kamera hep +z tarafından bakar. Mekânlar x ekseninde 700 m arayla dizilir.
const GAP = 700;

function moon(E, x = 26, y = 46, z = -120) {
  const m = E.sphere(5, E.flat("#fff3cf", { fog: false }), [x, y, z]); m.userData.noink = true; m.castShadow = false;
  const h = E.sphere(8.5, E.flat("#c9d2ff", { transparent: true, opacity: 0.18, fog: false }), [x, y, z - 1]); h.userData.noink = true; h.castShadow = false;
}
function stars(E, n = 40, seed = 3) { let s = seed; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); for (let i = 0; i < n; i++) { const m = E.sphere(0.25 + r() * 0.35, E.flat("#ffffff", { fog: false }), [-120 + r() * 240, 30 + r() * 60, -140 - r() * 20]); m.userData.noink = true; m.castShadow = false; } }
const glowBox = (E, w, h, d, pos, o = {}) => E.box(w, h, d, E.mat(o.col || "#ffd36a", { emissive: o.em || "#ffb648", glow: o.glow ?? 1.6 }), pos, o);
function candle(E, x, y, z, parent) { E.cyl(0.05, 0.05, 0.28, E.mat("#f4efe4"), [x, y, z], { parent, seg: 10 }); E.sphere(0.05, E.mat("#ffe08a", { emissive: "#ffb648", glow: 2 }), [x, y + 0.34, z], { parent, scale: [0.8, 1.4, 0.8] }); }
function tomb(E, x, z, s = 1, rot = 0) { const g = E.group(null, [x, 0, z], rot); const st = E.mat("#b9b4a6", { map: E.T.stone("#b9b4a6") }); E.box(0.55 * s, 1.3 * s, 0.16 * s, st, [0, 0, 0], { parent: g }); E.cyl(0.2 * s, 0.24 * s, 0.32 * s, E.mat("#a8a294"), [0, 1.3 * s, 0], { parent: g, seg: 12 }); E.box(0.9 * s, 0.12 * s, 1.6 * s, E.mat("#8f8a7c"), [0, 0, 0.8 * s], { parent: g }); return g; }
function arch(E, x, z, w, h, mat, parent) { // taş kemer (yarım torus + ayaklar)
  const { THREE } = E; const r = w / 2; const geo = new THREE.TorusGeometry(r, 0.32, 8, 20, Math.PI); const m = new THREE.Mesh(geo, mat); m.position.set(x, h, z); E.add(m, parent);
  E.box(0.64, h, 0.64, mat, [x - r, 0, z], { parent }); E.box(0.64, h, 0.64, mat, [x + r, 0, z], { parent });
}
function tower(E, x, z, r, h, wallMat, roofCol, parent) { E.cyl(r, r * 1.05, h, wallMat, [x, 0, z], { parent, seg: 14 }); E.cyl(r * 1.15, r * 1.15, 0.5, wallMat, [x, h, z], { parent, seg: 14 }); if (roofCol) E.cone(r * 1.25, r * 1.6, E.mat(roofCol), [x, h + 0.5, z], { parent, seg: 14 }); }

const BUILD = {
  kosk_ic(E, S, T) {
    S.room({ w: 11, d: 9, h: 4.6, wall: T.wallpaper("#5a3a4a", "#4a2e3e", "diamond"), floor: T.planks("#6b4428"), floorRep: 0.4, window: true, door: true, night: true });
    S.frame(-2.6, 2.6, -4.45, { w: 1.2, h: 1.5, kind: "portrait" }); S.frame(3.4, 2.5, -4.45, { w: 1.4, h: 1.0, kind: "landscape" });
    S.rug(0, -1.2, 4.6, 3.2, "#6a2a3a"); S.chair(-3.2, -2.6, { col: "#5a2a2a", rot: 0.4 });
    const t = S.table(3.0, -2.4, { w: 1.4, d: 0.8, col: "#5a3420" }); candle(E, 3.0, 0.95, -2.4); candle(E, 3.25, 0.95, -2.25);
    S.shelf(-4.6, -3.9, { seed: 5 }); S.hangLamp(0, 4.6, -1.4, { col: "#3a2a20", i: 3.5 });
    const p = new E.THREE.PointLight(0xffb060, 3, 7, 2); p.position.set(3.0, 1.6, -2.2); E.scene.add(p);
    return { light: "icgece", obj: [0, 1.25, -3.2] };
  },
  kosk_dis(E, S, T) {
    E.ground(T.grass("#3f5a3a"), 260, 0.2);
    S.building(0, -9, { w: 12, d: 8, floors: 3, fh: 3.1, wall: "#c9b48a", roof: "#5a3a3a", shutter: "#3a2a20", win: "#2a3a5a", cols: 5, chimney: true });
    glowBox(E, 1.0, 1.2, 0.05, [1.9, 6.6, -4.97]); // tek yanan pencere
    for (const x of [-9, -7.5, 7.5, 9.5]) S.tree(x, -6 - Math.abs(x) * 0.2, { type: "cypress", s: 1.5, col: "#2f4a3a" });
    S.fence(-6, 6, -3.6, { col: "#6b5a4a" }); S.bush(-3.5, -4.2, 0.8, "#2f4a3a"); S.bush(4, -4.4, 0.9, "#2f4a3a");
    S.lamp(-3, -2.6, { on: true }); moon(E); stars(E); S.hills({ col: "#2a3a3a", z: -80 });
    return { light: "zifiri", obj: [0, 1.3, -2.4] };
  },
  mezarlik(E, S, T) {
    E.ground(T.grass("#34483a"), 260, 0.2);
    const pos = [[-2.6, -3.2], [-1.0, -4.4], [0.8, -3.6], [2.6, -4.8], [-3.8, -6.2], [1.8, -6.8], [-0.4, -7.4], [3.9, -2.8], [-4.4, -2.0], [0.0, -5.6]];
    pos.forEach(([x, z], i) => tomb(E, x, z, 0.9 + (i % 3) * 0.12, (i % 2 ? 0.12 : -0.1)));
    for (const [x, z] of [[-6, -6], [-5, -11], [5.5, -7], [7, -12], [0, -13], [-9, -9], [9, -8]]) S.tree(x, z, { type: "cypress", s: 1.7, col: "#24382e" });
    S.fence(-7, 7, -15, { col: "#4a4a4a" }); moon(E, -20, 42); stars(E, 30, 8);
    return { light: "zifiri", obj: [0.8, 1.3, -2.4] };
  },
  koy(E, S, T) {
    E.ground(T.dirt("#8a7456"), 260, 0.2);
    const walls = ["#c9b48a", "#bfa98a", "#d9c8a8", "#b89f7a"];
    [[-7, -10], [0.5, -12], [7.5, -10], [-12, -16], [12, -16]].forEach(([x, z], i) => S.building(x, z, { w: 5.5, d: 5, floors: 1 + (i % 2), fh: 2.8, wall: walls[i % 4], roof: "#6a4a3a", shutter: "#4a3a2a", win: "#2a3a5a", cols: 2, chimney: i % 2 === 0, flatRoof: i === 2 }));
    glowBox(E, 0.8, 0.8, 0.05, [-6.3, 1.6, -7.47]);
    const well = E.group(null, [3.2, 0, -3.6]); E.cyl(0.8, 0.85, 0.9, E.mat("#9a8f7a", { map: T.stone("#9a8f7a") }), [0, 0, 0], { parent: well, seg: 16 }); E.box(0.12, 1.8, 0.12, E.mat("#6b4428"), [-0.7, 0.9, 0], { parent: well }); E.box(0.12, 1.8, 0.12, E.mat("#6b4428"), [0.7, 0.9, 0], { parent: well }); E.box(1.7, 0.14, 0.14, E.mat("#6b4428"), [0, 2.65, 0], { parent: well });
    S.tree(-4.2, -5, { s: 1.2, col: "#3f5a3a" }); S.tree(6.4, -6, { s: 1.0, col: "#3f5a3a" });
    S.mountains({ col: "#3a4a6a" }); moon(E); stars(E, 35, 5);
    return { light: "zifiri", obj: [3.2, 1.6, -3.0] };
  },
  kopru(E, S, T) {
    const w = E.plane(300, 300, E.mat("#ffffff", { map: (() => { const t = T.water("#1f3f6a").clone(); t.needsUpdate = true; t.repeat.set(36, 36); return t; })() }), [0, -0.6, -40], { rot: [-Math.PI / 2, 0, 0] }); w.castShadow = false;
    E.box(40, 0.6, 7, E.mat("#6a6a4a", { map: T.dirt("#6a6a4a") }), [0, -0.6, 3]); // kıyı (sahne)
    const st = E.mat("#a89a80", { map: T.stone("#a89a80") }), g = E.group(null, [0, 0, -9]);
    for (const x of [-9, 0, 9]) arch(E, x, 0, 7, 3.2, st, g);
    E.box(28, 0.8, 3, st, [0, 6.4, 0], { parent: g }); for (let x = -13.5; x <= 13.5; x += 1.5) E.box(0.5, 0.7, 0.5, st, [x, 7.2, -1.2], { parent: g });
    S.tree(-8, 0.6, { type: "cypress", s: 1.3, col: "#2f4a3a" }); S.hills({ col: "#2a3a3a", z: -70 }); moon(E, 18, 40); stars(E);
    return { light: "zifiri", obj: [0, 1.3, -1.6] };
  },
  kale(E, S, T) {
    E.ground(T.dirt("#6f6550"), 260, 0.2);
    const st = E.mat("#9a907a", { map: T.stone("#9a907a") }), g = E.group(null, [0, 0, -10]);
    E.box(26, 7, 2.2, st, [0, 0, 0], { parent: g }); for (let x = -12.5; x <= 12.5; x += 1.6) E.box(0.9, 0.9, 2.2, st, [x, 7, 0], { parent: g });
    tower(E, -9, 0.6, 2.4, 10, st, "#4a3a4a", g); tower(E, 9, 0.6, 2.4, 10, st, "#4a3a4a", g);
    E.box(3.4, 4.2, 0.3, E.mat("#3a2a20", { map: T.planks("#3a2a20") }), [0, 0, 1.2], { parent: g });
    glowBox(E, 0.5, 0.9, 0.05, [-9, 7.5, -7.35], {}); S.lamp(3.6, -6.6, { on: true });
    S.mountains({ col: "#3a4a6a" }); moon(E, -22); stars(E);
    return { light: "zifiri", obj: [0, 1.3, -2.4] };
  },
  saray(E, S, T) {
    S.room({ w: 13, d: 10, h: 6, wall: T.tiles("#2f5f8a", "#e9e2d0", 6), floor: T.marble("#e4dccb"), floorRep: 0.3, window: false, door: false });
    for (const x of [-4.6, -1.6, 1.6, 4.6]) { E.cyl(0.32, 0.36, 5.6, E.mat("#efe7d6", { map: T.marble("#efe7d6") }), [x, 0, -4.2], { seg: 16 }); E.box(0.9, 0.3, 0.9, E.mat("#c9a24a"), [x, 5.6, -4.2]); }
    E.box(12.8, 0.6, 0.4, E.mat("#c9a24a"), [0, 5.7, -4.8]);
    E.box(1.6, 1.0, 1.0, E.mat("#8a2a3a"), [0, 0, -3.6]); E.box(1.6, 1.6, 0.25, E.mat("#c9a24a"), [0, 0.9, -4.0]); // taht
    S.rug(0, -0.8, 3, 6.5, "#8a2a3a"); S.hangLamp(-3, 6, -1.8, { col: "#c9a24a", i: 4 }); S.hangLamp(3, 6, -1.8, { col: "#c9a24a", i: 4 });
    return { light: "icgece", obj: [0, 1.4, -2.8] };
  },
  magara(E, S, T) {
    E.ground(T.stone("#4a4248"), 120, 0.3);
    const rm = E.mat("#5a5058", { map: T.stone("#5a5058") });
    for (let i = 0; i < 9; i++) { const a = -1.2 + i * 0.3; const s = E.sphere(6 + (i % 3), rm, [Math.sin(a) * 11, 2, -Math.cos(a) * 11 + 2], { seg: 10 }); s.scale.set(1, 1.4, 1); }
    for (let i = 0; i < 16; i++) { const x = -6 + (i * 0.83) % 12, z = -2 - (i * 1.7) % 8; const c = E.cone(0.25 + (i % 3) * 0.12, 1.2 + (i % 4) * 0.5, rm, [x, 6.2, z], { seg: 7 }); c.rotation.x = Math.PI; c.position.y = 7.5; }
    E.box(14, 0.5, 14, rm, [0, 8.2, -4]);
    const t = E.group(null, [-2.6, 0, -3.2]); E.cyl(0.05, 0.07, 1.6, E.mat("#4a3020"), [0, 0, 0], { parent: t, seg: 8 }); E.sphere(0.16, E.mat("#ffb648", { emissive: "#ff8a30", glow: 2.2 }), [0, 1.75, 0], { parent: t, scale: [1, 1.5, 1] });
    const p = new E.THREE.PointLight(0xff9a40, 6, 10, 2); p.position.set(-2.6, 2.0, -3.0); E.scene.add(p);
    return { light: "icgece", obj: [0.6, 1.2, -2.6] };
  },
  carsi(E, S, T) {
    S.street({ len: 70, width: 6, z: -3 });
    E.ground(T.cobble("#6f6658"), 260, 0.2, [0, -0.06, 0]);
    const aw = ["#8a2a2a", "#2f5f6a", "#c2843a", "#5a3a6a"];
    [-12, -5, 2, 9, 16].forEach((x, i) => S.building(x, -10, { w: 6.6, d: 6, floors: 2, fh: 3, wall: ["#c9b48a", "#bfa98a", "#d9c8a8"][i % 3], roof: "#6a4a3a", shutter: "#4a3a2a", win: "#2a3a5a", cols: 2, awning: aw[i % 4] }));
    S.crate(-3, -6.2, 0.9, 0.3); S.barrel(-1.8, -6.6); S.sack(3.4, -6.4); S.sack(4.1, -6.1, 0.8); S.crate(5.2, -6.4, 0.7);
    S.lamp(-5, -5.6, { on: true }); S.lamp(6.5, -5.6, { on: true }); moon(E, 10, 50); stars(E);
    return { light: "zifiri", obj: [-3, 1.3, -4.6] };
  },
  orman(E, S, T) {
    E.ground(T.grass("#2f4436"), 260, 0.2);
    let s = 11; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 34; i++) { const x = -18 + r() * 36, z = -4 - r() * 26; if (Math.abs(x) < 2.6 && z > -8) continue; S.tree(x, z, { type: "pine", s: 1.4 + r() * 0.9, col: "#24382e" }); }
    S.bush(-3, -3.6, 0.9, "#24382e"); S.bush(3.2, -4.2, 1.0, "#24382e"); moon(E, -14, 48); stars(E, 30, 9);
    return { light: "zifiri", obj: [0.4, 1.2, -2.6] };
  },
  sahil(E, S, T) {
    const w = E.plane(300, 300, E.mat("#ffffff", { map: (() => { const t = T.water("#1f3f6a").clone(); t.needsUpdate = true; t.repeat.set(36, 36); return t; })() }), [0, -0.5, -40], { rot: [-Math.PI / 2, 0, 0] }); w.castShadow = false;
    E.box(8, 0.3, 30, E.mat("#8a6a46", { map: T.planks("#8a6a46") }), [0, -0.3, -2]); // iskele
    for (let z = -15; z <= 10; z += 3) for (const x of [-3.8, 3.8]) E.cyl(0.15, 0.15, 1.6, E.mat("#5a4030"), [x, -1.5, z], { seg: 8 });
    S.boat(-7, -6, { s: 0.9, rot: 0.3 });
    const g = E.group(null, [-5, 0, -38]); const wm = E.mat("#e9e2d0", { map: T.plaster("#e9e2d0") }); E.box(7, 3, 7, E.mat("#8a8070", { map: T.stone("#8a8070") }), [0, -0.6, 0], { parent: g });
    tower(E, 0, 0, 1.6, 9, wm, "#5a6b8a", g); glowBox(E, 0.6, 0.8, 0.05, [-5, 6.4, -36.35]);
    moon(E, -18, 40); stars(E);
    return { light: "zifiri", obj: [0, 1.0, -2.6] };
  },
  avlu(E, S, T) {
    E.ground(T.cobble("#8a8070"), 200, 0.25);
    const st = E.mat("#b9ad94", { map: T.stone("#b9ad94") }), g = E.group(null, [0, 0, -8]);
    for (const x of [-7.5, -2.5, 2.5, 7.5]) arch(E, x, 0, 4, 3.4, st, g); E.box(22, 2, 1, st, [0, 3.6, 0], { parent: g });
    const f = E.group(null, [0, 0, -3.4]); E.cyl(1.6, 1.7, 0.6, st, [0, 0, 0], { parent: f, seg: 20 }); E.cyl(1.4, 1.4, 0.05, E.mat("#3f6f9a"), [0, 0.56, 0], { parent: f, seg: 20 }); E.box(0.7, 1.6, 0.5, st, [0, 0, -1.2], { parent: f }); E.cyl(0.08, 0.08, 0.3, E.mat("#c9a24a"), [0, 1.0, -0.9], { parent: f, rot: [Math.PI / 2, 0, 0] });
    S.tree(-5, -5, { type: "cypress", s: 1.3, col: "#2f4a3a" }); S.tree(5.4, -5.4, { type: "cypress", s: 1.4, col: "#2f4a3a" }); moon(E); stars(E);
    return { light: "zifiri", obj: [0, 1.4, -2.2] };
  },
  arsiv(E, S, T) {
    S.room({ w: 10, d: 8, h: 4, wall: T.wallpaper("#6a5038", "#5e4632", "stripe"), floor: T.planks("#5a3a24"), floorRep: 0.4, window: false, door: false });
    for (const x of [-3.6, -1.8, 1.8, 3.6]) S.shelf(x, -3.7, { seed: 3 + Math.round(x * 3) });
    S.desk(0.4, -2.0, { col: "#5a3420" }); S.paper(0.1, 0.97, -1.9, T.sign("", { bg: "#efe0b8", border: null }), { w: 0.6, h: 0.42, spin: 0.2 }); candle(E, 1.1, 0.95, -2.2);
    S.hangLamp(0, 4, -1.4, { col: "#3a2a20", i: 4.5 });
    return { light: "icgece", obj: [0.2, 1.3, -1.9] };
  },
};
const ALIAS = { kosk: "kosk_dis", kosk_disi: "kosk_dis", konak: "kosk_dis", konak_ic: "kosk_ic", oda: "kosk_ic", kabristan: "mezarlik", kasaba: "koy", koy_meydani: "koy", koprusu: "kopru", kule: "kale", hisar: "kale", sur: "kale", sarayi: "saray", saray_ic: "saray", magarasi: "magara", obruk: "magara", zindan: "magara", pazar: "carsi", han: "carsi", sokak: "carsi", kiyi: "sahil", liman: "sahil", deniz: "sahil", gol: "sahil", cesme: "avlu", kuyu: "avlu", cami_avlusu: "avlu", medrese: "avlu", kutuphane: "arsiv", belge: "arsiv" };
const locName = (n) => { n = (n || "").toLowerCase(); return BUILD[n] ? n : ALIAS[n] || "kosk_dis"; };

function buildLoc(E, name, idx) {
  const before = new Set(E.scene.children);
  const info = BUILD[name](E, E.S, E.T) || {};
  const g = new E.THREE.Group(); g.position.set(idx * GAP, 0, 0);
  for (const c of [...E.scene.children]) if (!before.has(c)) g.add(c);
  E.scene.add(g);
  LOC[name] = { x: idx * GAP, light: info.light || "zifiri", obj: info.obj || [0, 1.3, -2.4] };
}

// ---------------------------------------------------------------- insert objesi (parşömen / tabela)
function insertCard(E, text, kind) {
  const T = E.T;
  const tex = kind === "gazete" ? T.newspaper(text || "", { paper: "TAKVİM-İ VEKAYİ", date: "", col: "#7a2a2a" })
    : T.sign(text || "", { bg: "#efe0b8", fg: "#3a2a20", border: "#7a5a2a", size: (text || "").length > 10 ? 90 : 120 });
  const flat = true;
  const g = E.group(null, [0, 0, 0]);
  const m = E.plane(kind === "gazete" ? 0.9 : 1.3, kind === "gazete" ? 1.2 : 0.62, E.flat("#f2ead8", { map: tex, side: E.THREE.DoubleSide }), [0, 0, 0], { parent: g, noShadow: true });
  E.cyl(0.05, 0.05, kind === "gazete" ? 0 : 1.42, E.mat("#c9b07a"), [0, 0.31, 0], { parent: g, center: true, rot: [0, 0, Math.PI / 2] });
  E.cyl(0.05, 0.05, kind === "gazete" ? 0 : 1.42, E.mat("#c9b07a"), [0, -0.31, 0], { parent: g, center: true, rot: [0, 0, Math.PI / 2] });
  g.visible = false; return g;
}

// ---------------------------------------------------------------- kur
export async function build(E) {
  try { const r = await fetch("../work/plan.json?v=" + Date.now()); P = await r.json(); } catch (e) { console.error("plan.json yok", e); P = { beats: [] }; }
  const T = E.T;
  // mekânlar: plandaki sırayla, sadece kullanılanlar
  const used = []; for (const b of P.beats) { const n = locName(b.loc); b.loc = n; if (!used.includes(n)) used.push(n); }
  used.forEach((n, i) => buildLoc(E, n, i));
  // oyuncular
  E.actor("bekci", PRESET.bekci);
  const cast = P.cast || {};
  for (const [k, c] of Object.entries(cast)) {
    const base = PRESET[c.preset] || PRESET.koylu_erkek;
    E.actor(k, { ...base, ...(c.color ? { shirt: c.color, dress: base.dress ? c.color : undefined } : {}), seed: 11 + k.charCodeAt(0) * 3 });
  }
  const crowdCols = ["#8a5a3a", "#5a6b3a", "#6a3a4a", "#3a5a6a", "#7a6a3a", "#4a4a6a"];
  for (let i = 0; i < 6; i++) E.actor("k" + i, { ...(i % 3 === 1 ? PRESET.koylu_kadin : PRESET.koylu_erkek), shirt: crowdCols[i], dress: i % 3 === 1 ? crowdCols[i] : undefined, seed: 70 + i * 9 });
  // insert kartları
  P.beats.forEach((b, i) => { if (b.shot === "obje") R["ins" + i] = insertCard(E, b.label || "", b.obj === "gazete" ? "gazete" : "parsomen"); });
  // fener ışığı (bekçi)
  R.lamp = new E.THREE.PointLight(0xffc870, 0, 5, 2); E.scene.add(R.lamp);
  R.glow = E.sphere(0.09, E.mat("#ffe7a0", { emissive: "#ffc860", glow: 2.4 }), [0, -50, 0]); R.glow.userData.noink = true; R.glow.castShadow = false;
  // çekim tablosu: uzun vuruşları ikiye böl
  SH = [];
  P.beats.forEach((b, i) => {
    // kesmeler seslendirmeye göre (cizgi_build.py: duraklar / kelime başları); sabit süre yok
    const edges = [b.f0, ...(b.cuts || []).filter((c) => c > b.f0 && c < b.f1), b.f1];
    for (let j = 0; j < edges.length - 1; j++) SH.push({ ...b, i, f0: edges[j], f1: edges[j + 1], part: j });
  });
}

// ---------------------------------------------------------------- kare
const nameCard = (title, sub) => (g, w, h) => {
  const k = w / 1080, x = 70 * k, y = 1360 * k, pw = Math.max(420, 60 + Math.max(title.length * 30, sub.length * 19)) * k;
  g.save(); g.fillStyle = "rgba(10,12,28,.86)"; g.beginPath(); g.roundRect(x, y, pw, 112 * k, 22 * k); g.fill();
  g.fillStyle = "#ffcf6a"; g.fillRect(x, y, 10 * k, 112 * k);
  g.font = `900 ${44 * k}px CizgiFont, Nunito, sans-serif`; g.fillStyle = "#fff"; g.textBaseline = "middle"; g.fillText(title, x + 34 * k, y + 40 * k);
  g.font = `700 ${29 * k}px CizgiFont, Nunito, sans-serif`; g.fillStyle = "#ffcf6a"; g.fillText(sub, x + 34 * k, y + 82 * k); g.restore();
};

export function frame(f, E) {
  const X = E.X;
  let k = 0; while (k < SH.length - 1 && f >= SH[k + 1].f0) k++;
  const sh = SH[k] || { shot: "genis", loc: Object.keys(LOC)[0], f0: 0, f1: 60, i: 0, part: 0 };
  const lc = LOC[sh.loc] || Object.values(LOC)[0], ox = lc.x;
  const t = f - sh.f0, len = Math.max(1, sh.f1 - sh.f0), u = Math.min(1, t / len);
  const side = ((sh.i + sh.part) % 2 ? 1 : -1);
  const W = (x, y, z) => [ox + x, y, z];
  const st = (seed, o = {}) => ({ blink: E.blink(f, seed), ...E.idle(f, seed), ...o });
  const who = (sh.who || []).filter((w) => E.actors.has(w));
  const mood = MOOD[sh.mood] || MOOD.merak;
  const A = [], FX = [];
  let light = L(sh.light || lc.light), cam, dof = { focus: 4, amount: 6 }, flash = 0, overlay = null, focusPt = W(0, 0, -1);
  // sıfırla
  for (const key in R) if (key.startsWith("ins")) R[key].visible = false;
  R.lamp.intensity = 0; R.glow.position.set(0, -50, 0);
  const pop = (f0, d = 8) => X.back(X.span(f, f0, f0 + d));
  const fx = (pos, size = 0.6, at = 10) => { const kind = FXK[sh.fx]; if (kind && f >= sh.f0 + at) FX.push({ kind, pos, size: size * pop(sh.f0 + at), t: ((f - sh.f0 - at) / 30) % 1 }); };
  const prop = sh.prop && PROP[sh.prop] ? { kind: PROP[sh.prop], hand: "r", gold: sh.prop === "altin" } : null;

  // ---- karakter hareketi (eylem)
  const actorState = (id, seed, x0, z0, extra = {}) => {
    const act = sh.action || "dur";
    let x = x0, z = z0, legs = "stand", phase = 0, s = { ...mood }, dir = 0;
    if (act === "yuru") { x = x0 + X.keyed(t, [[0, -1.6 * side], [Math.min(len, 75), 0]]); legs = t < 75 ? "walk" : "stand"; phase = t / 24; dir = t < 75 ? side : 0; }
    else if (act === "kos") { x = x0 + (u - 0.5) * 4.2 * side; legs = "run"; phase = t / 14; dir = side; }
    else if (act === "kac") { x = x0 + X.easeOut(u) * 3.2 * -side; legs = "run"; phase = t / 13; dir = -side; s = { ...s, face: "scared", arms: "up" }; }
    else if (act === "isaret") { s = { ...s, arms: "point" }; }
    else if (act === "bak") { s = { ...s, look: Math.sin(t / 14) }; }
    else if (act === "saklan") { s = { ...s, lean: 14 * side, look: side * 0.8 }; }
    else if (act === "otur") { legs = "sit"; }
    else if (act === "uyu") { legs = "sit"; s = { ...s, face: "sleep", arms: "cross" }; }
    else if (act === "el_kaldir") { s = { ...s, arms: "cheer" }; }
    else if (act === "konus") { s = { ...s, face: "talk", talk: E.talk(f) }; }
    const tint = (P.cast?.[id]?.preset === "hayalet") ? "#c6d4ff" : undefined;
    return { id, pos: W(x, 0, z), st: st(seed, { ...s, legs, phase, ...(id === who[0] && prop ? { prop, arms: s.arms === "up" ? "holdR" : (s.arms || "holdR") } : {}), ...extra }), ...(tint ? { tint } : {}), ...(dir ? { flip: dir > 0 } : {}) };
  };
  const bekci = (x, z, o = {}) => {
    const s = st(3, { face: o.face || "talk", arms: o.arms || "holdR", talk: E.talk(f, sh.f0, sh.f1), look: o.look ?? -0.3, prop: o.prop || { kind: "lantern", hand: "r" } });
    A.push({ id: "bekci", pos: W(x, 0, z), st: s });
    if ((o.prop || { kind: "lantern" }).kind === "lantern") { const lp = W(x + 0.42, 1.1, z + 0.35); R.lamp.position.set(...lp); R.lamp.intensity = 4; }
  };
  const ck = (a, b, fov = 40, fov2 = fov - 2) => E.camAt(f, [{ f: sh.f0, pos: W(...a[0]), look: W(...a[1]), fov }, { f: sh.f1, pos: W(...b[0]), look: W(...b[1]), fov: fov2 }]);

  let shot = sh.shot;
  const nParts = SH.filter((x) => x.i === sh.i).length;
  if (shot === "bekci_kapanis") shot = sh.part === nParts - 1 ? "bekci_kapanis" : "bekci";  // son parça = açılış kadrajı (loop)
  else if (shot === "bekci_hook" && sh.part >= 1) shot = "genis";
  else if (sh.part >= 1 && shot === "gercek") shot = "gercek2";
  else if (sh.part >= 1) {
    const alt = shot === "genis" || shot === "kalabalik" ? ["karakter", "yakin"] : shot === "bekci" ? ["bekci", "bekci"] : ["yakin", "genis"];
    shot = alt[(sh.part - 1) % 2];
  }
  if ((shot === "karakter" || shot === "yakin" || shot === "ikili" || shot === "kovalamaca") && !who.length) shot = "genis";

  switch (shot) {
    case "bekci_hook": case "bekci_kapanis": {
      bekci(0.5, 0.6, { face: shot === "bekci_kapanis" ? "sly" : "talk", arms: "holdR", look: -0.4 });
      const K0 = [[0.15, 1.85, 5.7], [-0.1, 2.0, -6]], K1 = [[0.2, 1.8, 5.1], [0, 1.95, -6]];
      cam = shot === "bekci_hook" ? ck(K0, K1, 46, 44) : ck(K1, K0, 44, 46);  // kapanış açılış karesine geri döner (loop)
      dof = { focus: W(0.62, 1.6, 0.6), amount: 7 }; focusPt = W(0.3, 0, -1);
      if (shot === "bekci_hook" && sh.fx) fx(W(-0.6, 2.6, -2), 0.7, 14);
      break;
    }
    case "bekci": {
      bekci(0, 0, { face: mood.face, arms: mood.arms === "present" ? "holdR" : "holdR", look: Math.sin(t / 20) * 0.5 });
      cam = ck([[0.3 * side, 1.7, 3.3], [0, 1.55, 0]], [[0.25 * side, 1.7, 2.8], [0, 1.6, 0]], 40, 38);
      dof = { focus: W(0, 1.6, 0), amount: 10 }; fx(W(0.55, 2.55, 0.1), 0.55);
      break;
    }
    case "genis": {
      who.forEach((id, j) => A.push(actorState(id, 10 + j, (j - (who.length - 1) / 2) * 1.3, -0.6 - j * 0.3)));
      const lx = who.length ? 0 : -1.2 * side;
      cam = ck([[-2.4 * side, 3.6, 9.5], [lx, 2.6, -5]], [[-1.2 * side, 2.7, 7.6], [lx, 2.3, -5]], 50, 47);
      dof = { focus: 8, amount: 3, range: 6 }; fx(W(0, 3.0, -1), 0.8);
      break;
    }
    case "karakter": {
      const id = who[0]; A.push(actorState(id, 11, 0, -0.4));
      if (who[1]) A.push(actorState(who[1], 12, 1.5 * side, -2.4));
      cam = ck([[0.6 * side, 1.75, 4.4], [0, 1.4, -0.4]], [[0.35 * side, 1.72, 3.7], [0, 1.45, -0.4]], 42, 40);
      dof = { focus: W(0, 1.5, -0.4), amount: 8 }; fx(W(0.5, 2.7, -0.3), 0.6);
      break;
    }
    case "yakin": {
      const id = who[0]; A.push(actorState(id, 11, 0, -0.4, sh.action === "kos" || sh.action === "kac" || sh.action === "yuru" ? {} : {}));
      cam = ck([[0.15 * side, 1.8, 2.6], [0, 1.65, -0.4]], [[0.1 * side, 1.8, 2.2], [0, 1.68, -0.4]], 40, 38);
      if (sh.mood === "korku" || sh.mood === "saskin") { const s = E.shake(f, sh.f0 + 6, 0.05, 10); cam.pos = cam.pos.map((v, i) => v + s[i]); }
      dof = { focus: W(0, 1.8, -0.4), amount: 11 }; fx(W(0.45, 2.5, -0.3), 0.5, 6);
      break;
    }
    case "ikili": {
      A.push(actorState(who[0], 11, -0.75, -0.5)); A.push(actorState(who[1] || "k0", 12, 0.8, -0.9, { face: MOOD[sh.mood2]?.face || "neutral", arms: MOOD[sh.mood2]?.arms || "hang" }));
      cam = ck([[0.3 * side, 1.9, 6.4], [0, 1.35, -0.7]], [[0.2 * side, 1.85, 5.6], [0, 1.4, -0.7]], 44, 42);
      dof = { focus: W(0, 1.5, -0.7), amount: 6 }; fx(W(0.8, 2.7, -0.8), 0.55);
      break;
    }
    case "kovalamaca": {
      const x = (u - 0.5) * 5 * side;
      A.push({ id: who[0], pos: W(x, 0, -0.6), st: st(11, { legs: "run", phase: t / 13, face: "scared", arms: "up", sweat: true }), flip: side > 0 });
      if (who[1]) A.push({ id: who[1], pos: W(x - 1.8 * side, 0, -1.0), st: st(12, { legs: "run", phase: t / 13 + 0.3, face: MOOD[sh.mood2]?.face || "angry", arms: "reach" }), flip: side > 0 });
      cam = { pos: W(x * 0.7, 2.0, 6.2), look: W(x * 0.85, 1.3, -0.8), fov: 46, roll: 0 };
      dof = { focus: W(x, 1.4, -0.7), amount: 5 }; FX.push({ kind: "dust", pos: W(x - 0.6 * side, 0.5, -0.5), size: 0.7, t: (t / 20) % 1 });
      break;
    }
    case "kalabalik": {
      for (let i = 0; i < 6; i++) { const x = -2.4 + i * 0.95, z = -1.6 - (i % 2) * 0.9; A.push({ id: "k" + i, pos: W(x, 0, z), st: st(30 + i, { face: MOOD[sh.mood]?.face || "talk", arms: ["hang", "cross", "chin", "point", "hip", "up"][i], look: x > 0 ? -0.5 : 0.5, talk: i % 2 ? E.talk(f) * 0.6 : 0 }) }); }
      who.slice(0, 1).forEach((id) => A.push(actorState(id, 11, 0, 0.1)));
      cam = ck([[-1.2 * side, 2.8, 8.4], [0, 1.4, -1.2]], [[-0.6 * side, 2.5, 7.4], [0, 1.4, -1.2]], 48, 46);
      dof = { focus: W(0, 1.5, -1), amount: 4 }; fx(W(0, 3.0, -1.4), 0.7);
      break;
    }
    case "obje": {
      const o = lc.obj, g = R["ins" + sh.i];
      if (g) { g.visible = true; g.position.set(ox + o[0], o[1] + 0.05 * Math.sin(t / 9), o[2] + 0.8); g.rotation.set(0, 0.12 * Math.sin(t / 30), -0.04); g.scale.setScalar(0.25 + 0.75 * X.easeOut(X.span(f, sh.f0, sh.f0 + 12))); }
      cam = ck([[o[0] + 0.15, o[1] + 0.1, o[2] + 5.0], [o[0], o[1], o[2] + 0.8]], [[o[0] + 0.05, o[1] + 0.05, o[2] + 4.5], [o[0], o[1], o[2] + 0.8]], 40, 38);
      dof = { focus: W(o[0], o[1], o[2] + 0.8), amount: 9 };
      FX.push({ kind: "sparkle", pos: W(o[0] + 0.5, o[1] + 0.35, o[2] + 0.95), size: 0.45, t: t / 30 });
      flash = Math.max(0, 1 - t / 5) * 0.35;
      break;
    }
    case "gercek": {
      // efsaneden gerçeğe: ışık zifiriden altına döner, bekçi parşömeni açar
      light = [L(sh.light || lc.light), L(sh.light2 || "altin"), X.smooth(X.span(f, sh.f0, sh.f0 + 24))];
      bekci(-0.15, -0.2, { face: u < 0.25 ? "wow" : "talk", arms: "holdR", prop: { kind: "scroll", hand: "r" }, look: 0.3 });
      who.slice(0, 1).forEach((id) => A.push(actorState(id, 11, 0.9, -1.0)));
      cam = ck([[0.1, 1.75, 3.2], [0, 1.55, -0.6]], [[0.2, 2.0, 5.4], [0, 1.6, -1.2]], 40, 44);
      dof = { focus: W(-0.15, 1.6, -0.2), amount: 6 };
      flash = Math.max(0, 1 - Math.abs(t - 3) / 6) * 0.8;
      if (t > 8) FX.push({ kind: "idea", pos: W(-0.2, 2.75, -0.1), size: 0.5 * pop(sh.f0 + 8), t: 0 });
      break;
    }
    case "gercek2": {
      light = L(sh.light2 || "altin");
      bekci(0.55, 0.2, { face: "happy", arms: "holdR", prop: { kind: "scroll", hand: "r" }, look: -0.4 });
      who.slice(0, 1).forEach((id) => A.push(actorState(id, 11, -0.9, -1.2)));
      cam = ck([[-0.6, 2.6, 7.6], [0, 2.0, -6]], [[-0.3, 2.3, 6.6], [0, 1.9, -6]], 48, 46);
      dof = { focus: W(0.4, 1.5, 0.2), amount: 4 };
      FX.push({ kind: "sparkle", pos: W(0.1, 2.9, 0.1), size: 0.5, t: t / 30 });
      break;
    }
    default: {
      cam = ck([[0, 2.4, 7], [0, 2, -5]], [[0, 2.2, 6], [0, 2, -5]], 48, 46);
    }
  }
  if (sh.card && sh.part === 0 && t < 80) overlay = nameCard(sh.card.title || "", sh.card.sub || "");
  // kare 0 boş açılış olmasın; son kare yumuşak
  return { cam, light: Array.isArray(light) ? light : L(light), dof, actors: A, fx: FX, flash, overlay: NOCAP ? null : overlay, focusPt, ...(NOCAP ? { caption: false } : {}) };
}
