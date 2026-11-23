// Unfrozen History · uzun (8-12 dk) yatay çizgi film yönetmeni.
// work/plan.json'daki çekim planını (Gemini) kanala özel kış mekânları + sabit anlatıcı (soba başındaki yaşlı) ile canlandırır.
// Motor: cizgi-short — Burak Özer (@burakozerweb), MIT. Zifiri Saatler story.js'inden uyarlandı.
export const meta = { w: 1920, h: 1080, fps: 24, tail: 1.2, captions: false };

const NOCAP = typeof location !== "undefined" && location.search.includes("nocap");  // kapak karesi
let P = null, SH = [];
const LOC = {}, R = {};
const FPS = 24;

// ---------------------------------------------------------------- ışık (kış paleti)
const LIGHT = {
  snowday: { sun: "#f4f6ff", sunI: 1.15, az: -35, el: 32, sky: "#dfe8f6", ground: "#9aa6bd", hemiI: 0.95, amb: 0.24, top: "#8fa9cf", bot: "#e9eef7", fog: "#dfe6f1", fogNear: 30, fogFar: 150, card: "#f3f6ff", sat: 0.92, warm: -0.03, con: 1.04, vig: 0.3 },
  snownight: { sun: "#9fb4ff", sunI: 0.55, az: 210, el: 38, sky: "#2a3a6a", ground: "#2a3048", hemiI: 0.7, amb: 0.2, top: "#0a1230", bot: "#34477e", fog: "#1e2a50", fogNear: 25, fogFar: 120, card: "#c8d2f4", sat: 0.95, warm: -0.06, con: 1.1, vig: 0.48 },
  blizzard: { sun: "#e8eef8", sunI: 0.55, az: -20, el: 40, sky: "#cfd8e6", ground: "#8e98ab", hemiI: 1.05, amb: 0.3, top: "#b9c4d6", bot: "#e6ebf2", fog: "#dbe2ec", fogNear: 6, fogFar: 46, card: "#eef2fa", sat: 0.78, warm: -0.04, con: 0.98, vig: 0.34 },
  dawn: { sun: "#ffc79a", sunI: 1.3, az: -75, el: 12, sky: "#f6c9b8", ground: "#7a7090", hemiI: 0.75, amb: 0.17, top: "#7d8fc4", bot: "#ffd9bd", fog: "#f0cdbd", fogNear: 35, fogFar: 160, card: "#ffe9dc", sat: 1.05, warm: 0.05, con: 1.06, vig: 0.34 },
  stove: { sun: "#ffd9a8", sunI: 0.7, az: -40, el: 55, sky: "#4a3028", ground: "#2a1a14", hemiI: 0.62, amb: 0.2, top: "#2a1c22", bot: "#5a3a2a", fog: "#2a1c1c", fogNear: 18, fogFar: 80, card: "#f6dcc4", sat: 1.06, warm: 0.06, con: 1.08, vig: 0.46 },
  polar: { sun: "#fff4e6", sunI: 1.2, az: -60, el: 18, sky: "#e6ecf6", ground: "#9aa6bd", hemiI: 0.9, amb: 0.22, top: "#8faad4", bot: "#f6e9de", fog: "#e6e9f0", fogNear: 40, fogFar: 170, card: "#fff8f0", sat: 0.95, warm: 0.0, con: 1.05, vig: 0.3 },
  spring: { sun: "#fff2d8", sunI: 1.25, az: -40, el: 38, sky: "#cfe2ee", ground: "#6f7a52", hemiI: 0.95, amb: 0.24, top: "#7fa8d0", bot: "#e6efe0", fog: "#d6e2e4", fogNear: 35, fogFar: 160, card: "#f6f8ee", sat: 1.0, warm: 0.02, con: 1.04, vig: 0.3 },
  lamp: { sun: "#fff0d0", sunI: 0.85, az: -30, el: 60, sky: "#e8d8bc", ground: "#4a3828", hemiI: 0.85, amb: 0.26, top: "#d8c6a8", bot: "#d8c6a8", fog: "#cdbb9c", fogNear: 25, fogFar: 100, card: "#fff2e0", sat: 1.0, warm: 0.03, con: 1.06, vig: 0.38 },
};
const LALIAS = { day: "snowday", gunduz: "snowday", night: "snownight", gece: "snownight", storm: "blizzard", golden: "dawn", sunset: "dawn", interior: "lamp", warm: "stove", summer: "spring", thaw: "spring" };
const L = (n) => LIGHT[n] || LIGHT[LALIAS[n]] || LIGHT.snowday;

// ---------------------------------------------------------------- oyuncular
const PRESET = {
  host: { shirt: "#7a4a32", jacket: "#5a3a2a", scarf: "#b8322e", beard: "#e8e8e8", hair: "short", hairCol: "#dcdcdc", build: "stout", skin: "#f0cfae", pants: "#3a3530", seed: 7 },
  soldier: { shirt: "#5d6b3a", jacket: "#4a5530", pants: "#4a4f35", belt: "#3a2a20", hat: "helmet", hatCol: "#55613a", scarf: "#8a8f80", skin: "#e9c3a0" },
  officer: { shirt: "#4e5a38", jacket: "#3e482c", buttons: "#d9b44a", belt: "#3a2a20", hat: "police", hatCol: "#3e482c", moustache: "#5a4030", skin: "#f0d0b0" },
  explorer: { shirt: "#c9b48a", jacket: "#b09a6e", pants: "#5a4a3a", hat: "hood", hatCol: "#b09a6e", hatBand: "#efe6d2", beard: "#7a5a40", skin: "#e9c3a0" },
  sailor: { shirt: "#e8e4d8", jacket: "#24304a", pants: "#24304a", hat: "beanie", hatCol: "#2a3350", pompom: false, beard: "#5a4030", skin: "#e3b48e" },
  miner: { shirt: "#a8343e", jacket: "#5a4632", pants: "#3a3a4a", hat: "fur", hatCol: "#5a4632", beard: "#6a4a30", skin: "#e9c3a0" },
  prospector: { shirt: "#6a7a5a", jacket: "#6b4428", pants: "#4a3f35", hat: "fedora", hatCol: "#5a4030", beard: "#8a6a4a", scarf: "#9a6a3a", skin: "#e3b48e" },
  mountie: { shirt: "#b8262e", jacket: "#b8262e", buttons: "#e8c45a", belt: "#6b4428", pants: "#22305a", hat: "fedora", hatCol: "#8a6a46", skin: "#f0d0b0" },
  townsman: { shirt: "#e9e2d0", jacket: "#3a3a4a", tie: "#7a2a2a", pants: "#2b2633", hat: "bowler", hatCol: "#2b2633", moustache: "#3a2a20", scarf: "#5a5a6a", skin: "#f0d0b0" },
  worker: { shirt: "#6a6a72", jacket: "#4a4a52", pants: "#3a3a40", hat: "cap", hatCol: "#3a3a44", scarf: "#7a6a4a", skin: "#e9c3a0" },
  farmer: { shirt: "#5a7aa0", jacket: "#7a5a3a", pants: "#3a4a6a", hat: "cap", hatCol: "#6a4a30", beard: "#8a6a4a", skin: "#e3b48e" },
  doctor: { shirt: "#f4f1ea", apron: "#ffffff", pants: "#3a3a40", glasses: true, moustache: "#6a6a6a", hair: "short", hairCol: "#7a7a7a", skin: "#f0d0b0" },
  woman: { dress: "#5a3a5a", shirt: "#5a3a5a", apron: "#e9e0cc", hair: "bun", hairCol: "#3a2a20", scarf: "#a8564a", skin: "#f6dcc0" },
  teacher: { dress: "#2f4f6a", shirt: "#2f4f6a", hair: "bun", hairCol: "#5a3a2a", glasses: true, scarf: "#c9a24a", skin: "#fbe8d4" },
  elder: { shirt: "#6a5a4a", jacket: "#3a3a3a", beard: "#e6e6e6", hat: "fur", hatCol: "#4a3a2a", build: "stout", skin: "#e9c3a0" },
  elderwoman: { dress: "#4a4a6a", shirt: "#4a4a6a", hair: "bun", hairCol: "#dedede", scarf: "#6a3a4a", build: "stout", skin: "#f6dcc0" },
  boy: { build: "kid", shirt: "#3f6fb5", pants: "#2b2633", hat: "beanie", hatCol: "#b8322e", scarf: "#e8c45a", skin: "#f6dcc0" },
  girl: { build: "kid", dress: "#8a3a4a", shirt: "#8a3a4a", hair: "long", hairCol: "#6a4a2a", scarf: "#efe6d2", skin: "#f6dcc0" },
};
const MOOD = {
  scared: { face: "scared", arms: "up", sweat: true }, shocked: { face: "shock", arms: "up" }, curious: { face: "think", arms: "chin" },
  sly: { face: "sly", arms: "hip" }, sad: { face: "sad", arms: "hang" }, happy: { face: "happy", arms: "present" },
  angry: { face: "angry", arms: "point" }, thoughtful: { face: "think", arms: "think" }, telling: { face: "talk", arms: "present" },
  nervous: { face: "nervous", arms: "hang", sweat: true }, determined: { face: "determined", arms: "hip" }, proud: { face: "smug", arms: "cross" },
  amazed: { face: "wow", arms: "cheer" }, sleepy: { face: "sleep", arms: "cross" }, cold: { face: "nervous", arms: "cross" }, tired: { face: "sad", arms: "hang" },
  hopeful: { face: "happy", arms: "chin" }, relieved: { face: "happy", arms: "cheer" },
};
const FXK = { question: "question", exclaim: "exclaim", sweat: "sweat", idea: "idea", puff: "puff", sparkle: "sparkle", hearts: "hearts", anger: "anger", zzz: "zzz", money: "money", dust: "dust", lines: "lines" };
const PROP = { lantern: "lantern", letter: "letter", key: "key", gold: "bag", coin: "coin", scroll: "scroll", paper: "paper", magnifier: "magnifier", pen: "pen", cup: "cup" };

// ---------------------------------------------------------------- dokular (kar / buz / kütük)
function canvasTex(E, key, draw, w = 512, h = 512) {
  R.tex = R.tex || {}; if (R.tex[key]) return R.tex[key];
  const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d");
  let s = 0; for (const ch of key) s = (s * 31 + ch.charCodeAt(0)) >>> 0; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  draw(g, r, w, h);
  const t = new E.THREE.CanvasTexture(c); t.colorSpace = E.THREE.SRGBColorSpace; t.wrapS = t.wrapT = E.THREE.RepeatWrapping; t.anisotropy = 8;
  R.tex[key] = t; return t;
}
const snowTex = (E, base = "#eef2f8") => canvasTex(E, "snow" + base, (g, r, w, h) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 70; i++) { g.globalAlpha = 0.07 + r() * 0.07; g.fillStyle = r() < 0.6 ? "#c7d2e6" : "#ffffff"; g.beginPath(); g.ellipse(r() * w, r() * h, 30 + r() * 90, 10 + r() * 30, r() * 3, 0, 7); g.fill(); }
  g.globalAlpha = 0.5; g.fillStyle = "#ffffff"; for (let i = 0; i < 160; i++) g.fillRect(r() * w, r() * h, 2, 2); g.globalAlpha = 1;
});
const iceTex = (E) => canvasTex(E, "ice", (g, r, w, h) => {
  g.fillStyle = "#dbe9f4"; g.fillRect(0, 0, w, h);
  g.strokeStyle = "#a9c4dc"; g.lineWidth = 3; for (let i = 0; i < 18; i++) { g.beginPath(); let x = r() * w, y = r() * h; g.moveTo(x, y); for (let k = 0; k < 5; k++) { x += (r() - 0.5) * 120; y += (r() - 0.5) * 120; g.lineTo(x, y); } g.stroke(); }
  for (let i = 0; i < 40; i++) { g.globalAlpha = 0.12; g.fillStyle = "#ffffff"; g.beginPath(); g.ellipse(r() * w, r() * h, 40 + r() * 60, 20 + r() * 30, r() * 3, 0, 7); g.fill(); } g.globalAlpha = 1;
});
const logTex = (E, col = "#6b4428") => canvasTex(E, "log" + col, (g, r, w, h) => {
  const n = 8, ph = h / n; const sh = (k) => { const v = parseInt(col.slice(1), 16); const c = (x) => Math.max(0, Math.min(255, Math.round(x * k))); return `rgb(${c(v >> 16)},${c((v >> 8) & 255)},${c(v & 255)})`; };
  for (let i = 0; i < n; i++) { const gr = g.createLinearGradient(0, i * ph, 0, (i + 1) * ph); gr.addColorStop(0, sh(0.75)); gr.addColorStop(0.45, sh(1.08)); gr.addColorStop(1, sh(0.6)); g.fillStyle = gr; g.fillRect(0, i * ph, w, ph); g.fillStyle = sh(0.45); g.fillRect(0, (i + 1) * ph - 4, w, 4); for (let k = 0; k < 3; k++) { g.fillStyle = sh(0.8); g.fillRect(r() * w, i * ph + ph * (0.3 + 0.4 * r()), 60 + r() * 120, 2); } }
});
const mapTex = (E, label) => canvasTex(E, "map" + label, (g, r, w, h) => {
  g.fillStyle = "#efe2c0"; g.fillRect(0, 0, w, h); g.strokeStyle = "#7a5a2a"; g.lineWidth = 12; g.strokeRect(6, 6, w - 12, h - 12);
  g.fillStyle = "#c9b48a"; for (let i = 0; i < 3; i++) { g.beginPath(); let x = 80 + r() * 300, y = 80 + r() * 200; g.moveTo(x, y); for (let k = 0; k < 9; k++) g.lineTo(x + (r() - 0.3) * 160, y + (r() - 0.5) * 140); g.closePath(); g.fill(); }
  g.strokeStyle = "#a8343e"; g.lineWidth = 6; g.setLineDash([16, 12]); g.beginPath(); g.moveTo(90, h - 90); g.bezierCurveTo(200, 200, 330, 380, w - 100, 110); g.stroke(); g.setLineDash([]);
  g.fillStyle = "#a8343e"; g.beginPath(); g.arc(w - 100, 110, 14, 0, 7); g.fill();
}, 512, 384);

// ---------------------------------------------------------------- set yardımcıları
const GAP = 700;
let THAW = false;  // bahar/yaz varyantı: kar yok, çamur + çimen, ağaçlarda kar şapkası yok
const ROOF = () => (THAW ? "#6a5a4a" : "#e9eef6");
function snowPine(E, S, x, z, s = 1, col = "#2f4a3e") {
  const g = E.group(null, [x, 0, z]);
  E.cyl(0.15 * s, 0.22 * s, 1.2 * s, E.mat("#5a3a24"), [0, 0, 0], { parent: g });
  for (let i = 0; i < 3; i++) { const r = (1.5 - i * 0.35) * s, y = (1 + i * 1.1) * s; E.cone(r, 1.8 * s, E.mat(col), [0, y, 0], { parent: g, seg: 9 }); if (!THAW) E.cone(r * 0.62, 0.75 * s, E.mat("#f4f7fc"), [0, y + 1.08 * s, 0], { parent: g, seg: 9 }); }
  return g;
}
function snowGround(E, size = 300, base) { if (THAW) base = "#7b7f55"; const t = snowTex(E, base).clone(); t.needsUpdate = true; t.repeat.set(size / 12, size / 12); const m = E.plane(size, size, E.mat("#ffffff", { map: t }), [0, 0, 0], { rot: [-Math.PI / 2, 0, 0] }); m.castShadow = false; return m; }
function drift(E, x, z, w = 3, h = 0.7, d = 1.6) { const m = E.sphere(1, E.mat(THAW ? "#6a7348" : "#f1f4fa"), [x, 0, z], { seg: 14 }); m.scale.set(w, h, d); return m; }
function snowHills(E, z = -90, n = 8, seed = 5) { let s = seed; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); for (let i = 0; i < n; i++) { const m = E.sphere(20 + r() * 22, E.mat(THAW ? (r() < 0.5 ? "#6f7d55" : "#5f6d4a") : (r() < 0.5 ? "#e6ecf6" : "#d6deec")), [-150 + (i / (n - 1)) * 300 + r() * 20, -12, z - r() * 30], { seg: 18 }); m.scale.y = 0.42; m.castShadow = false; } }
function mountainsSnow(E, z = -170, n = 7, col = "#8f9fc4") { let s = 9; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); for (let i = 0; i < n; i++) { const h = 34 + r() * 34, x = -230 + (i / (n - 1)) * 460, zz = z - r() * 40; const c = E.cone(30 + r() * 18, h, E.mat(col), [x, -2, zz], { seg: 7 }); c.castShadow = false; const cap = E.cone(13, h * 0.42, E.mat("#f4f6ff"), [x, h * 0.58 - 2, zz], { seg: 7 }); cap.castShadow = false; } }
const glowBox = (E, w, h, d, pos, o = {}) => E.box(w, h, d, E.mat(o.col || "#ffd36a", { emissive: o.em || "#ffb648", glow: o.glow ?? 1.6 }), pos, o);
function fire(E, x, z, parent) {
  const g = E.group(parent, [x, 0, z]);
  for (let i = 0; i < 5; i++) { const l = E.cyl(0.07, 0.07, 0.9, E.mat("#5a3a24"), [0, 0.08, 0], { parent: g, center: true, rot: [Math.PI / 2, 0, (i / 5) * Math.PI] }); l.castShadow = false; }
  const f1 = E.cone(0.32, 0.9, E.mat("#ffb648", { emissive: "#ff8a30", glow: 2.2 }), [0, 0.05, 0], { parent: g, seg: 8 }); f1.userData.noink = true;
  const f2 = E.cone(0.18, 0.55, E.mat("#fff0a0", { emissive: "#ffd36a", glow: 2.6 }), [0.05, 0.05, 0.05], { parent: g, seg: 8 }); f2.userData.noink = true;
  const p = new E.THREE.PointLight(0xff9a40, 7, 9, 2); p.position.set(0, 0.9, 0); g.add(p);
  for (let i = 0; i < 6; i++) E.sphere(0.16, E.mat("#8a8a90"), [Math.cos(i) * 0.5, 0.08, Math.sin(i) * 0.5], { parent: g, seg: 8 });
  return g;
}
function tent(E, x, z, o = {}) {
  const g = E.group(null, [x, 0, z], o.rot || 0), col = o.col || "#d9cfb4";
  const sh = new E.THREE.Shape(); sh.moveTo(-1.3, 0); sh.lineTo(1.3, 0); sh.lineTo(0, 1.9); sh.lineTo(-1.3, 0);
  const geo = new E.THREE.ExtrudeGeometry(sh, { depth: 2.6, bevelEnabled: false }); geo.translate(0, 0, -1.3);
  E.add(new E.THREE.Mesh(geo, E.mat(col)), g);
  const door = E.plane(0.9, 1.2, E.mat("#4a3a2a"), [0, 0.6, 1.31], { parent: g }); door.castShadow = false;
  E.box(2.8, 0.18, 2.8, E.mat("#f1f4fa"), [0, 0, 0], { parent: g });
  return g;
}
function bellTent(E, x, z, col = "#d9cfb4") { const g = E.group(null, [x, 0, z]); E.cone(1.5, 2.6, E.mat(col), [0, 0, 0], { parent: g, seg: 14 }); E.cyl(0.04, 0.04, 3.0, E.mat("#5a3a24"), [0, 0, 0], { parent: g, seg: 6 }); return g; }
function sledge(E, x, z, rot = 0) { const g = E.group(null, [x, 0, z], rot); E.box(2.2, 0.12, 0.8, E.mat("#8a6a46"), [0, 0.35, 0], { parent: g }); for (const s of [-0.34, 0.34]) E.box(2.5, 0.08, 0.08, E.mat("#5a4030"), [0, 0.05, s], { parent: g }); for (const xx of [-0.8, 0, 0.8]) for (const s of [-0.34, 0.34]) E.box(0.08, 0.3, 0.08, E.mat("#5a4030"), [xx, 0.05, s], { parent: g }); E.box(1.6, 0.5, 0.6, E.mat("#c9b48a"), [0, 0.47, 0], { parent: g }); return g; }
function sandbags(E, x, z, n = 6, parent) { for (let i = 0; i < n; i++) for (let k = 0; k < 2; k++) { const m = E.sphere(0.32, E.mat(k ? "#a89a74" : "#9a8c68"), [x + (i - n / 2) * 0.62 + (k ? 0.3 : 0), 0.2 + k * 0.32, z], { seg: 10, parent }); m.scale.set(1, 0.55, 0.7); } }
function ship(E, x, z, o = {}) { // üç direkli barkentin: kare yelken sadece ön direkte
  const s = o.s || 1, g = E.group(null, [x, 0, z], o.rot || 0), hull = "#23262e";
  const sh = new E.THREE.Shape(); sh.moveTo(-9 * s, 2.2 * s); sh.lineTo(10 * s, 2.2 * s); sh.lineTo(8 * s, -0.6 * s); sh.lineTo(-8 * s, -0.6 * s); sh.lineTo(-9 * s, 2.2 * s);
  const geo = new E.THREE.ExtrudeGeometry(sh, { depth: 4 * s, bevelEnabled: false }); geo.translate(0, 0, -2 * s);
  E.add(new E.THREE.Mesh(geo, E.mat(hull)), g);
  E.box(19 * s, 0.18, 3.8 * s, E.mat("#8a6a46"), [0.5 * s, 2.2 * s, 0], { parent: g });
  E.box(4 * s, 1.4 * s, 2.4 * s, E.mat("#eeeae0"), [-1.5 * s, 2.3 * s, 0], { parent: g });
  E.cyl(0.32 * s, 0.32 * s, 3.2 * s, E.mat("#2b2b30"), [-4 * s, 2.3 * s, 0], { parent: g, seg: 12 });
  for (const [mx, mh] of [[6 * s, 13 * s], [1.2 * s, 14 * s], [-6.5 * s, 11 * s]]) E.cyl(0.14 * s, 0.18 * s, mh, E.mat("#6b4428"), [mx, 2.2 * s, 0], { parent: g, seg: 8 });
  for (let i = 0; i < 4; i++) E.box(0.18, 0.18, (4.6 - i * 0.7) * s, E.mat("#6b4428"), [6 * s, (6 + i * 2.4) * s, 0], { parent: g }); // ön direk sereni
  for (let i = 0; i < 4; i++) E.box(0.32, 0.32, (4.4 - i * 0.7) * s, E.mat("#efe8d6"), [6.0 * s, (6.2 + i * 2.4) * s, 0], { parent: g }); // seren üstünde sarılı kare yelkenler
  for (const mx of [1.2 * s, -6.5 * s]) E.box(3.6 * s, 0.14, 0.14, E.mat("#6b4428"), [mx - 1.8 * s, 4.2 * s, 0], { parent: g }); // gaff bumbaları
  E.box(5 * s, 0.12, 0.12, E.mat("#6b4428"), [12 * s, 3.4 * s, 0], { parent: g, rot: [0, 0, 0.25] }); // cıvadra
  if (o.tilt) g.rotation.z = o.tilt;
  return g;
}

function scow(E, x, z) { // el yapımı yassı tekne: oyuncular içinde durur (zemin y=0), kıç küreği + baş küreği
  const g = E.group(null, [x, 0, z]), c = "#7a5a3a", T = E.T;
  E.box(8.6, 0.25, 3.4, E.mat("#6b4a30", { map: T.planks("#6b4a30") }), [0, -0.25, 0], { parent: g });
  for (const zz of [-1.7, 1.7]) E.box(8.6, 0.95, 0.16, E.mat(c, { map: T.planks(c) }), [0, -0.3, zz], { parent: g });
  for (const xx of [-4.3, 4.3]) E.box(0.16, 0.95, 3.4, E.mat(c, { map: T.planks(c) }), [xx, -0.3, 0], { parent: g });
  E.box(5.2, 0.08, 0.1, E.mat("#5a4030"), [-6.2, 0.5, 0], { parent: g, rot: [0, 0, 0.12] }); E.box(4.6, 0.08, 0.1, E.mat("#5a4030"), [6.0, 0.45, 0], { parent: g, rot: [0, 0, -0.1] });
  for (const [xx, zz] of [[-2.6, -1.0], [2.8, -0.9]]) E.box(0.9, 0.6, 0.7, E.mat("#d9cdb0"), [xx, 0, zz], { parent: g }); // un çuvalları
  return g;
}

// ---------------------------------------------------------------- mekânlar
// Her mekân (0,0,0) çevresinde; sahne alanı x∈[-4,4], z∈[-3,1]; kamera +z'den bakar.
const BUILD = {
  cabin(E, S, T) { // anlatıcının kulübesi: soba, pencere arkası karlı gece
    S.room({ w: 14, d: 9, h: 4.6, wall: logTex(E, "#6b4428"), floor: T.planks("#5a3a24"), floorRep: 0.4, window: false, door: false });
    const st = E.group(null, [-2.6, 0, -3.2]);
    E.box(1.3, 1.1, 1.0, E.mat("#2a2a30"), [0, 0.2, 0], { parent: st }); for (const xx of [-0.5, 0.5]) for (const zz of [-0.35, 0.35]) E.box(0.1, 0.22, 0.1, E.mat("#2a2a30"), [xx, 0, zz], { parent: st });
    glowBox(E, 0.6, 0.4, 0.05, [0, 0.55, 0.51], { parent: st, col: "#ffb648", em: "#ff7a20", glow: 2.4 });
    E.cyl(0.14, 0.14, 3.4, E.mat("#2a2a30"), [0.3, 1.3, -0.2], { parent: st, seg: 10 });
    const p = new E.THREE.PointLight(0xff9a40, 9, 9, 2); p.position.set(-2.6, 1.0, -2.4); E.scene.add(p);
    // pencere: dışarıda kar yağan gece
    const wg = E.group(null, [2.6, 1.3, -4.45]); E.box(2.2, 1.8, 0.12, E.mat("#4a3020"), [0, 0, 0], { parent: wg });
    E.plane(1.9, 1.5, E.flat("#1e2c5a"), [0, 0.9, 0.07], { parent: wg, noShadow: true }); E.box(0.08, 1.5, 0.06, E.mat("#4a3020"), [0, 0.15, 0.1], { parent: wg }); E.box(1.9, 0.08, 0.06, E.mat("#4a3020"), [0, 0.9, 0.1], { parent: wg, center: true });
    E.box(2.0, 0.22, 0.2, E.mat("#f4f7fc"), [0, 0.12, 0.16], { parent: wg });
    S.shelf(5.2, -4.1, { seed: 6 }); S.rug(-0.6, -1.2, 4.6, 3.0, "#7a2a2a");
    const ch = E.group(null, [0.4, 0, -2.0], -0.1); E.box(1.1, 0.12, 0.9, E.mat("#5a3420"), [0, 0.5, 0], { parent: ch }); E.box(1.1, 1.3, 0.12, E.mat("#5a3420"), [0, 0.55, -0.44], { parent: ch }); for (const xx of [-0.48, 0.48]) E.box(0.1, 0.5, 0.8, E.mat("#4a2a18"), [xx, 0, 0], { parent: ch });
    const t = S.table(3.4, -2.6, { w: 1.4, d: 0.8, col: "#5a3420" }); glowBox(E, 0.2, 0.3, 0.2, [3.3, 0.95, -2.6], { glow: 2 }); E.cyl(0.13, 0.11, 0.18, E.mat("#e9e2d0"), [3.7, 0.95, -2.5], { seg: 10 });
    for (const [x, z] of [[-6.2, -4.0], [-5.5, -4.1]]) E.box(0.5, 0.4, 0.5, E.mat("#8a6a46"), [x, 0, z]); // odun
    return { light: "stove", obj: [0, 1.4, -2.6], indoor: true };
  },
  forest(E, S, T) {
    snowGround(E); let s = 11; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 46; i++) { const x = -26 + r() * 52, z = -4 - r() * 34; if (Math.abs(x) < 4 && z > -9) continue; snowPine(E, S, x, z, 1.3 + r() * 1.0); }
    drift(E, -4.6, -3.2); drift(E, 5, -4.4, 3.4, 0.8); snowHills(E, -95);
    return { light: "snowday", obj: [0.4, 1.3, -2.4] };
  },
  trench(E, S, T) { // karlı siper hattı: kum torbaları, çukurlar, orman kenarı
    snowGround(E);
    for (const x of [-6, 0, 6]) { const pit = E.cyl(1.4, 1.2, 0.05, E.mat("#5a5048"), [x, 0.01, -1.6], { seg: 16 }); pit.castShadow = false; sandbags(E, x, -3.0, 5); }
    let s = 4; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 30; i++) snowPine(E, S, -30 + r() * 60, -12 - r() * 20, 1.4 + r() * 0.8);
    for (let i = 0; i < 7; i++) { const x = -9 + i * 3, p = E.cyl(0.05, 0.05, 1.1, E.mat("#5a4030"), [x, 0, -5.4], { seg: 6 }); } E.box(19, 0.03, 0.03, E.mat("#4a4a4a"), [0, 0.8, -5.4]); E.box(19, 0.03, 0.03, E.mat("#4a4a4a"), [0, 0.45, -5.4]);
    snowHills(E, -80);
    return { light: "snowday", obj: [0, 1.3, -2.2] };
  },
  ice(E, S, T) { // buzla sarılı gemi, buz sırtları
    const t = iceTex(E).clone(); t.needsUpdate = true; t.repeat.set(30, 30); const g0 = E.plane(320, 320, E.mat("#ffffff", { map: t }), [0, 0, 0], { rot: [-Math.PI / 2, 0, 0] }); g0.castShadow = false;
    ship(E, 2, -22, { s: 0.95, rot: 0.25, tilt: 0.05 });
    let s = 21; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 22; i++) { const m = E.box(1.2 + r() * 2.4, 0.5 + r() * 1.3, 0.8 + r() * 1.6, E.mat(r() < 0.5 ? "#cfe2f2" : "#e9f2fa"), [-30 + r() * 60, 0, -6 - r() * 34], { rot: [r() * 0.5, r() * 3, r() * 0.4] }); }
    drift(E, -4, -3.4, 3, 0.6); sledge(E, 4.2, -3.2, 0.3);
    return { light: "polar", obj: [0, 1.2, -2.4] };
  },
  camp(E, S, T) { // karlı kamp: çadırlar + ateş
    snowGround(E);
    bellTent(E, -5.4, -6.2); bellTent(E, 5.6, -7.0, "#cfc4a8"); tent(E, -1.8, -9.4, { rot: 0.2 }); tent(E, 2.8, -10.6, { rot: -0.3, col: "#c9bd9e" });
    fire(E, 0, -2.6); sledge(E, -4.0, -2.8, 0.6); S.crate(4.0, -3.4, 0.7, 0.3); S.barrel(4.8, -4.2, 0.8);
    let s = 8; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 24; i++) snowPine(E, S, -32 + r() * 64, -16 - r() * 22, 1.3 + r() * 0.9);
    snowHills(E, -90);
    return { light: "snownight", obj: [0, 1.2, -2.0] };
  },
  pass(E, S, T) { // dik dağ geçidi: insanlar tek sıra tırmanır (Chilkoot vb.)
    snowGround(E);
    const slope = E.box(80, 40, 60, E.mat("#ffffff", { map: (() => { const t = snowTex(E).clone(); t.needsUpdate = true; t.repeat.set(8, 4); return t; })() }), [0, -20, -40], { rot: [0.55, 0, 0] }); slope.castShadow = false;
    for (let i = 0; i < 14; i++) { const m = E.sphere(0.9 + (i % 3) * 0.4, E.mat("#6a6a74"), [-14 + i * 2.2, 2 + i * 0.9, -14 - i * 1.6], { seg: 8 }); m.scale.y = 0.6; }
    let s = 61; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    // iki yanda kayalık sırtlar + seyrek çam: beyaz boşluk olmasın, dikliği okunsun
    for (const sd of [-1, 1]) for (let i = 0; i < 8; i++) { const zz = -2 - i * 4.5, yy = Math.max(0, (-zz - 6) * 0.6); const c = E.cone(2.4 + r() * 2, 4 + r() * 5, E.mat(r() < 0.5 ? "#5a5a66" : "#4a4c58"), [sd * (8 + r() * 4), yy - 1, zz], { seg: 6 }); c.castShadow = false; E.cone(1.2 + r(), 1.6, E.mat("#f4f6ff"), [c.position.x, c.position.y + c.geometry.parameters.height * 0.62, zz], { seg: 6 }).castShadow = false; if (i % 2 === 0) snowPine(E, S, sd * (6 + r() * 2), zz + 1, 0.8 + r() * 0.4).position.y = Math.max(0, yy - 0.3); }
    for (let i = 0; i < 26; i++) { const m = E.box(0.5, 0.06, 0.25, E.mat("#c9d2e2"), [-0.4 + i * 0.03, 0.4 + i * 0.95, -3 - i * 1.55]); m.castShadow = false; } // basamak izi (Golden Stairs)
    for (let i = 0; i < 6; i++) { const b = E.box(0.8, 0.5, 0.6, E.mat("#8a6a46"), [-2.6 + (i % 3) * 0.9, 0, 1.2 - Math.floor(i / 3) * 0.7]); b.castShadow = true; } // bırakılmış yük yığını
    mountainsSnow(E, -150, 7, "#7f8fb4");
    return { light: "snowday", obj: [0, 1.4, -2.4], slope: true };
  },
  frontier(E, S, T) { // altına hücum kasabası: tahta cepheli binalar, kaldırım tahtası
    snowGround(E, 300, "#e8ecf3");
    E.box(70, 0.25, 3, E.mat("#8a6a46", { map: T.planks("#8a6a46") }), [0, 0, -5.4]);
    const walls = ["#8a6a46", "#a8845a", "#6f5a46", "#9a7a56"];
    [-15, -7.5, 0, 7.5, 15].forEach((x, i) => { S.building(x, -10.2, { w: 6.6, d: 6, floors: 2, fh: 3, wall: walls[i % 4], roof: ROOF(), shutter: null, win: "#ffd88a", cols: 2, flatRoof: true, chimney: false }); E.box(6.6, 1.4, 0.3, E.mat(walls[(i + 1) % 4]), [x, 6, -7.1]); });
    for (const x of [-12, 4]) E.label(T.sign(x < 0 ? "GENERAL STORE" : "ASSAY OFFICE", { bg: "#efe0b8", fg: "#3a2a20", border: "#5a3a20", size: 110 }), 4.6, 1.0, [x + 0.5, 6.7, -6.9], { lit: true });
    S.barrel(-3, -4.6); S.crate(3, -4.8, 0.8); sledge(E, -1.2, -2.6, 0.1); S.lamp(-5, -4.4, { on: true });
    mountainsSnow(E, -140, 6, "#8f9fc4");
    return { light: "snowday", obj: [-3, 1.3, -3.8] };
  },
  town(E, S, T) { // Avrupa kasabası: taş evler karlı çatı, kilise kulesi, enkaz
    S.street({ len: 80, width: 6, z: -3, col: "#b0a898" }); snowGround(E, 300, "#e6ebf2").position.y = -0.08;
    [-14, -7, 0, 7, 14].forEach((x, i) => S.building(x, -10.5, { w: 6.6, d: 6, floors: 2 + (i % 2), fh: 3, wall: ["#b9b0a0", "#a8a294", "#c4bba8"][i % 3], roof: THAW ? "#7a6a5a" : "#eef2f8", shutter: "#4a4a5a", win: "#3a4a6a", cols: 2, chimney: i % 2 === 0 }));
    const tw = E.group(null, [3.5, 0, -22]); E.box(4, 14, 4, E.mat("#a8a294", { map: T.stone("#a8a294") }), [0, 0, 0], { parent: tw }); E.cone(3.2, 6, E.mat("#4a5a6a"), [0, 14, 0], { parent: tw, seg: 4 });
    for (let i = 0; i < 8; i++) E.box(0.6 + (i % 3) * 0.3, 0.35, 0.5, E.mat("#8a8478"), [-5.6 + (i % 4) * 0.5, 0, -5.6 + Math.floor(i / 4) * 0.4], { rot: [0, i, 0.2] });
    drift(E, 5.5, -5.4, 2.4, 0.6); S.lamp(-3, -5.6, { on: false });
    return { light: "snowday", obj: [-3, 1.3, -4.6] };
  },
  harbor(E, S, T) { // liman / balina istasyonu: iskele, barakalar, baca, buzlu su
    S.water({ size: 320, y: -0.5, col: "#3a5a7a", z: -40 });
    E.box(9, 0.3, 26, E.mat("#8a6a46", { map: T.planks("#8a6a46") }), [0, -0.3, -4]);
    for (let z = -16; z <= 8; z += 3) for (const x of [-4.3, 4.3]) E.cyl(0.16, 0.16, 1.8, E.mat("#5a4030"), [x, -1.5, z], { seg: 8 });
    const sh = E.group(null, [-14, 0, -18]); S.building(0, 0, { w: 10, d: 7, floors: 1, fh: 4, wall: "#8a5a46", roof: ROOF(), shutter: null, win: "#3a4a6a", cols: 3, parent: sh, chimney: false });
    E.cyl(1.0, 1.2, 16, E.mat("#9a5a46", { map: T.brick("#9a5a46") }), [-9, 0, -22], { seg: 14 });
    for (const x of [-4, 0]) E.cyl(1.6, 1.6, 3, E.mat("#7a5a4a"), [x - 6, 0, -14], { seg: 16 });
    S.crate(2.6, -6.5, 0.8, 0.4); S.barrel(-2.6, -8.4, 0.9); S.boat(9, -12, { s: 0.8, rot: -0.4, col: "#5a4030" });
    if (!THAW) for (let i = 0; i < 9; i++) { const m = E.box(1.5 + (i % 3), 0.3, 1.2, E.mat("#e9f2fa"), [-20 + i * 5, -0.45, -26 - (i % 2) * 6]); m.castShadow = false; }
    mountainsSnow(E, -120, 7, "#7f8fb4");
    return { light: "snowday", obj: [0, 1.0, -2.6] };
  },
  prairie(E, S, T) { // açık kar ovası: çiftlik evi, okul, çit
    snowGround(E);
    S.building(-9, -16, { w: 7, d: 6, floors: 2, fh: 2.8, wall: "#c9b48a", roof: ROOF(), shutter: "#4a3a2a", win: "#ffd88a", cols: 2, chimney: true });
    const sc = E.group(null, [9, 0, -18]); S.building(0, 0, { w: 8, d: 6, floors: 1, fh: 3.4, wall: "#b8322e", roof: ROOF(), shutter: null, win: "#ffd88a", cols: 3, parent: sc, chimney: false });
    E.box(1.2, 2.2, 1.2, E.mat("#efe6d2"), [0, 5.2, 0], { parent: sc }); E.cone(1.0, 1.4, E.mat("#5a4a4a"), [0, 7.4, 0], { parent: sc, seg: 4 });
    S.fence(-14, 14, -7.5, { col: "#6b5a4a" }); for (let i = 0; i < 6; i++) drift(E, -12 + i * 5, -7.2, 1.8, 0.5, 1);
    snowHills(E, -110, 6);
    return { light: "snowday", obj: [0, 1.3, -2.4] };
  },
  river(E, S, T) { // donmuş nehir / buz yolu
    snowGround(E);
    const t = iceTex(E).clone(); t.needsUpdate = true; t.repeat.set(12, 2); const rv = E.plane(300, 16, E.mat("#ffffff", { map: t }), [0, 0.02, -6], { rot: [-Math.PI / 2, 0, 0] }); rv.castShadow = false;
    for (let x = -40; x < 40; x += 2.4) { const m = E.box(1.2, 0.02, 0.12, E.mat("#9fb4c8"), [x, 0.03, -5.4]); m.castShadow = false; }
    let s = 31; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 34; i++) { const x = -30 + r() * 60; snowPine(E, S, x, -18 - r() * 18, 1.3 + r() * 0.9); }
    sledge(E, -3.2, -6, 0.05); sledge(E, 6, -7, -0.1);
    mountainsSnow(E, -150, 6, "#8f9fc4");
    return { light: "snowday", obj: [0, 1.2, -2.0] };
  },
  rapids(E, S, T) { // dar kanyonda azgın nehir (Miles Canyon vb.): bazalt duvarlar, köpük, ortada kahramanların sal/teknesi
    const w = S.water({ size: 320, y: -0.25, col: "#2f5a6a", z: -20 });
    let s = 41; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (const sd of [-1, 1]) for (let i = 0; i < 9; i++) { const c = E.box(6 + r() * 4, 9 + r() * 7, 7, E.mat(r() < 0.5 ? "#3a3a42" : "#2e2f36"), [sd * (9.5 + r() * 2), 0, 6 - i * 7], { rot: [0, r() * 0.3, 0] }); c.castShadow = false; snowPine(E, S, sd * (10 + r() * 2), 6 - i * 7, 0.9 + r() * 0.5).position.y = 9 + r() * 5; }
    for (let i = 0; i < 34; i++) { const near = i < 10, zz = near ? 0.5 - r() * 4 : -4 - r() * 36, xx = near ? (i % 2 ? 1 : -1) * (5 + r() * 2.5) : -7 + r() * 14; const m = E.sphere(near ? 0.35 + r() * 0.4 : 0.5 + r() * 0.9, E.mat("#f4f8fa"), [xx, -0.2, zz], { seg: 8 }); m.scale.set(1.6, 0.22, 0.8); m.castShadow = false; m.userData.foam = 1; }
    for (let i = 0; i < 7; i++) { const m = E.sphere(0.6 + r() * 0.5, E.mat("#2a2a30"), [-6 + r() * 12, -0.3, -4 - r() * 26], { seg: 7 }); m.scale.y = 0.6; }
    scow(E, 0, -1.0);
    return { light: "spring", obj: [0, 1.4, -1.6], water: true, season: "thaw", boat: true };
  },
  boats(E, S, T) { // buzu çözülmüş göl: yüzlerce el yapımı tekne (Lake Bennett, 1898 baharı)
    S.water({ size: 320, y: -0.25, col: "#4a7a96", z: -20 });
    scow(E, 0, -1.0);
    let s = 52; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < 26; i++) S.boat(-34 + r() * 68, -9 - r() * 40, { s: 0.45 + r() * 0.3, rot: r() * 0.6 - 0.3, col: ["#5a4030", "#6b4a30", "#7a5a3a"][i % 3] });
    for (let i = 0; i < 30; i++) snowPine(E, S, -80 + r() * 160, -62 - r() * 16, 1.6 + r());
    mountainsSnow(E, -150, 7, "#7f8fb4");
    return { light: "spring", obj: [0, 1.4, -1.6], water: true, season: "thaw", boat: true };
  },
  hq(E, S, T) { // karargâh / ofis: harita masası, lamba
    S.room({ w: 13, d: 9, h: 4.2, wall: T.plaster("#cfc4ae"), floor: T.planks("#6b4428"), floorRep: 0.4, window: true, door: true, night: true });
    S.table(0, -2.2, { w: 3.2, d: 1.6, col: "#5a3420" }); S.paper(0, 0.97, -2.2, mapTex(E, "hq"), { w: 2.6, h: 1.3 });
    S.hangLamp(0, 4.2, -2.0, { col: "#3a4a3a", i: 6 }); S.frame(-3.6, 2.6, -4.45, { w: 1.8, h: 1.2, tex: mapTex(E, "wall") }); S.chair(2.4, -3.2, { col: "#5a3420", rot: -0.4 });
    S.shelf(-5.4, -4.0, { seed: 9 }); S.crate(4.6, -3.6, 0.8);
    return { light: "lamp", obj: [0, 1.3, -1.8], indoor: true };
  },
};
const ALIAS = { cabin_ic: "cabin", home: "cabin", woods: "forest", pine: "forest", foxhole: "trench", front: "trench", lines: "trench", sea_ice: "ice", antarctic: "ice", arctic: "ice", ship: "ice", tents: "camp", bivouac: "camp", mountain: "pass", trail: "pass", goldrush: "frontier", boomtown: "frontier", city: "town", village: "town", street: "town", port: "harbor", station: "harbor", pier: "harbor", farm: "prairie", plains: "prairie", school: "prairie", frozen_lake: "river", ice_road: "river", lake: "boats", canyon: "rapids", whitewater: "rapids", rapids_river: "rapids", yukon: "boats", open_water: "boats", office: "hq", command: "hq", room: "hq" };
const locName = (n) => { n = (n || "").toLowerCase(); return BUILD[n] ? n : ALIAS[n] || "forest"; };

function buildLoc(E, key, idx) {
  const [name, var_] = key.split("~");
  const before = new Set(E.scene.children);
  THAW = var_ === "thaw";
  const info = BUILD[name](E, E.S, E.T) || {};
  THAW = false;
  const g = new E.THREE.Group(); g.position.set(idx * GAP, 0, 0);
  for (const c of [...E.scene.children]) if (!before.has(c)) g.add(c);
  E.scene.add(g);
  const lights = [], water = [], foam = [];
  g.traverse((o) => { if (o.isPointLight) { o.userData.base = o.intensity; lights.push(o); } if (o.isMesh && o.userData.water) water.push(o.userData.water); if (o.isMesh && o.userData.foam) { o.userData.z0 = o.position.z; foam.push(o); } });
  const thaw = var_ === "thaw" || info.season === "thaw";
  LOC[key] = { x: idx * GAP, foam, thaw, boat: !!info.boat, light: thaw && !["lamp", "stove"].includes(info.light) ? "spring" : (info.light || "snowday"), obj: info.obj || [0, 1.3, -2.4], indoor: !!info.indoor, slope: !!info.slope, lights, water };
}

// ---------------------------------------------------------------- yağan kar
function buildSnow(E) {
  const m = E.mat("#ffffff", { emissive: "#ffffff", glow: 0.5 }); const out = [];
  for (let i = 0; i < 170; i++) { const s = E.sphere(0.028 + (i % 5) * 0.006, m, [0, -80, 0], { seg: 5 }); s.userData.noink = true; s.castShadow = false; out.push(s); }
  return out;
}
function snowFall(f, cam, on, storm) {
  const fl = R.snow; if (!fl) return;
  const s = f / FPS, n = !on ? 0 : storm ? fl.length : Math.round(fl.length * 0.55);
  fl.forEach((m, i) => {
    if (i >= n) { m.position.y = -80; return; }
    const a = (i * 0.618034) % 1, b = (i * 0.414214) % 1, c = (i * 0.732051) % 1;
    const sp = storm ? 2.6 : 0.7 + b * 0.5, wx = storm ? 3.4 : 0.35;
    const y = 7 - ((s * sp + c * 7) % 7);
    const x = ((a * 18 + s * wx + Math.sin(s * 0.8 + i) * 0.3) % 18) - 9, z = -3.2 - b * 12;
    m.position.set(cam.pos[0] + x, Math.max(0.05, y + cam.pos[1] - 2), cam.pos[2] + z);
  });
}

// ---------------------------------------------------------------- insert (belge / harita / tabela)
function insertCard(E, text, kind) {
  const T = E.T;
  const tex = kind === "map" ? mapTex(E, text || "m") : kind === "newspaper" ? T.newspaper(text || "", { paper: "THE DAILY CHRONICLE", date: "", col: "#7a2a2a" })
    : T.sign(text || "", { bg: "#efe0b8", fg: "#3a2a20", border: "#7a5a2a", size: (text || "").length > 10 ? 90 : 120 });
  const g = E.group(null, [0, 0, 0]);
  const w = kind === "newspaper" ? 0.9 : kind === "map" ? 1.5 : 1.3, h = kind === "newspaper" ? 1.2 : kind === "map" ? 1.1 : 0.62;
  E.plane(w, h, E.flat("#f2ead8", { map: tex, side: E.THREE.DoubleSide }), [0, 0, 0], { parent: g, noShadow: true });
  if (kind !== "newspaper") for (const yy of [h / 2, -h / 2]) E.cyl(0.05, 0.05, w + 0.12, E.mat("#c9b07a"), [0, yy, 0], { parent: g, center: true, rot: [0, 0, Math.PI / 2] });
  g.visible = false; return g;
}

// ---------------------------------------------------------------- kur
export async function build(E) {
  try { const r = await fetch("../work/plan.json?v=" + Date.now()); P = await r.json(); } catch (e) { console.error("plan.json yok", e); P = { beats: [] }; }
  const used = ["cabin"];
  for (const b of P.beats) {
    let n = b.shot && b.shot.startsWith("host") ? "cabin" : locName(b.loc);
    if (n !== "cabin" && n !== "hq" && b.season === "thaw" && !["rapids", "boats"].includes(n)) n += "~thaw";
    b.loc = n; if (!used.includes(n)) used.push(n);
  }
  used.forEach((n, i) => buildLoc(E, n, i));
  E.actor("host", { ...PRESET.host, ...(P.host || {}) });
  const cast = P.cast || {};
  // aynı meslekten iki kişi birbirinin kopyası olmasın: ceket / şapka / sakal sırayla değişir; A (genç anlatıcı) yaşlı hâli gibi kırmızı atkı takar
  const VAR = [{}, { jacket: "#3a4a5a", hat: "cap", hatCol: "#4a4a4a", beard: "#2a2420", shirt: "#c9b48a" }, { jacket: "#6a3a2a", hat: "beanie", hatCol: "#2f4a3e", beard: "#a85a2a", shirt: "#e8e0cc" }, { jacket: "#4a5a3a", hat: "bowler", hatCol: "#2b2633", beard: null, moustache: "#3a2a20", shirt: "#d8c8a8" }];
  const seen = {};
  for (const [k, c] of Object.entries(cast)) {
    const base = PRESET[c.preset] || PRESET.worker; const n = seen[c.preset] = (seen[c.preset] ?? -1) + 1;
    const v = n && !base.dress ? VAR[n % VAR.length] : {};
    const spec = { ...base, ...v, ...(c.color ? { jacket: base.jacket ? c.color : undefined, shirt: base.jacket ? base.shirt : c.color, dress: base.dress ? c.color : undefined } : {}), seed: 11 + k.charCodeAt(0) * 3 };
    if (k === "A") { spec.scarf = PRESET.host.scarf; spec.beard = spec.beard ? "#8a5a3a" : spec.beard; }
    if (spec.beard === null) delete spec.beard;
    E.actor(k, spec);
  }
  const crowdP = ["soldier", "worker", "miner", "woman", "townsman", "farmer", "explorer", "sailor"];
  const crowdBase = (P.crowd && PRESET[P.crowd]) ? P.crowd : null;
  for (let i = 0; i < 8; i++) E.actor("k" + i, { ...PRESET[crowdBase || crowdP[i % crowdP.length]], seed: 70 + i * 9 });
  P.beats.forEach((b, i) => { if (b.shot === "object") R["ins" + i] = insertCard(E, b.label || "", b.obj === "map" ? "map" : b.obj === "newspaper" ? "newspaper" : "sign"); });
  R.snow = buildSnow(E);
  R.lamp = new E.THREE.PointLight(0xffc870, 0, 5, 2); E.scene.add(R.lamp);
  SH = [];
  P.beats.forEach((b, i) => {
    const edges = [b.f0, ...(b.cuts || []).filter((c) => c > b.f0 && c < b.f1), b.f1];
    for (let j = 0; j < edges.length - 1; j++) SH.push({ ...b, i, f0: edges[j], f1: edges[j + 1], part: j });
  });
}

// ---------------------------------------------------------------- 2D katmanlar (1920x1080)
const FONT = (w, px) => `${w} ${px}px CizgiFont, Nunito, sans-serif`;
const hookTitle = (text, a) => (g, w, h) => {
  if (a <= 0.01 || !text) return;
  const k = h / 1080, maxW = 1500 * k; let size = 104 * k; g.font = FONT(900, size);
  const words = text.toUpperCase().split(/\s+/);
  const wrap = () => { const Ls = []; let cur = ""; for (const wd of words) { const t = cur ? cur + " " + wd : wd; if (g.measureText(t).width > maxW && cur) { Ls.push(cur); cur = wd; } else cur = t; } if (cur) Ls.push(cur); return Ls; };
  let lines = wrap(); while (lines.length > 2 && size > 64 * k) { size -= 6 * k; g.font = FONT(900, size); lines = wrap(); }
  const lh = size * 1.08, y0 = 0.16 * h;
  g.save(); g.globalAlpha = a; g.textAlign = "center"; g.textBaseline = "top"; g.lineJoin = "round";
  lines.forEach((ln, i) => { const y = y0 + i * lh; g.lineWidth = 20 * k; g.strokeStyle = "#0b0d1e"; g.strokeText(ln, w / 2, y); g.fillStyle = i === lines.length - 1 ? "#ffd84a" : "#ffffff"; g.fillText(ln, w / 2, y); });
  g.restore();
};
const chapterCard = (title, sub, a) => (g, w, h) => {
  if (a <= 0.01) return;
  const k = h / 1080, x = 70 * k, y = 70 * k; g.save(); g.globalAlpha = a; g.font = FONT(900, 52 * k);
  const pw = Math.max(g.measureText(title).width + 90 * k, 460 * k);
  g.fillStyle = "rgba(14,18,34,.86)"; g.beginPath(); g.roundRect(x, y, pw, 132 * k, 24 * k); g.fill();
  g.fillStyle = "#9fd0ff"; g.fillRect(x, y, 12 * k, 132 * k);
  g.fillStyle = "#fff"; g.textBaseline = "middle"; g.fillText(title, x + 40 * k, y + 48 * k);
  g.font = FONT(700, 32 * k); g.fillStyle = "#9fd0ff"; g.fillText(sub, x + 40 * k, y + 98 * k); g.restore();
};
const ctaCard = (text, k0) => (g, w, h) => {
  if (k0 <= 0.01) return;
  const k = h / 1080, ph = 110 * k; g.save(); g.font = FONT(900, 46 * k); const pw = g.measureText(text).width + 170 * k, x = w - pw - 70 * k, y = 70 * k;
  g.translate(x + pw / 2, y + ph / 2); g.scale(k0, k0); g.translate(-pw / 2, -ph / 2);
  g.fillStyle = "#c4302b"; g.beginPath(); g.roundRect(0, 0, pw, ph, 55 * k); g.fill();
  g.fillStyle = "#fff"; g.beginPath(); g.moveTo(44 * k, 32 * k); g.lineTo(44 * k, 78 * k); g.lineTo(84 * k, 55 * k); g.closePath(); g.fill();
  g.textBaseline = "middle"; g.fillText(text, 110 * k, ph / 2 + 2 * k); g.restore();
};
const both = (a, b) => (a && b ? (g, w, h) => { a(g, w, h); b(g, w, h); } : a || b);

// ---------------------------------------------------------------- kare
export function frame(f, E) {
  const X = E.X;
  let k = 0; while (k < SH.length - 1 && f >= SH[k + 1].f0) k++;
  const sh = SH[k] || { shot: "wide", loc: Object.keys(LOC)[0], f0: 0, f1: 60, i: 0, part: 0 };
  const lc = LOC[sh.loc] || Object.values(LOC)[0], ox = lc.x;
  const t = f - sh.f0, len = Math.max(1, sh.f1 - sh.f0), u = Math.min(1, t / len);
  const side = ((sh.i + sh.part) % 2 ? 1 : -1);
  const W = (x, y, z) => [ox + x, y, z];
  const st = (seed, o = {}) => ({ blink: E.blink(f, seed), ...E.idle(f, seed), ...o });
  const who = (sh.who && sh.who.length ? sh.who : LOC[sh.loc]?.boat ? ["A", "B"] : []).filter((w) => E.actors.has(w));  // teknede boş sal olmasın
  const mood = MOOD[sh.mood] || MOOD.curious;
  const A = [], FX = [];
  let light = L(sh.light || lc.light), cam, dof = { focus: 6, amount: 4 }, flash = 0, overlay = null, focusPt = W(0, 0, -1);
  for (const key in R) if (key.startsWith("ins")) R[key].visible = false;
  R.lamp.intensity = 0;
  const pop = (f0, d = 8) => X.back(X.span(f, f0, f0 + d));
  const fx = (pos, size = 0.6, at = 10) => { const kind = FXK[sh.fx]; if (kind && f >= sh.f0 + at) FX.push({ kind, pos, size: size * pop(sh.f0 + at), t: ((f - sh.f0 - at) / FPS) % 1 }); };
  const prop = sh.prop && PROP[sh.prop] ? { kind: PROP[sh.prop], hand: "r", gold: sh.prop === "gold" } : null;

  const actorState = (id, seed, x0, z0, extra = {}) => {
    const act = sh.action || "stand";
    let x = x0, z = z0, legs = "stand", phase = 0, s = { ...mood }, dir = 0;
    if (act === "walk" || act === "march") { x = x0 + X.keyed(t, [[0, -2.0 * side], [Math.min(len, 90), 0]]); legs = t < 90 ? "walk" : "stand"; phase = t / 20; dir = t < 90 ? side : 0; }
    else if (act === "run") { x = x0 + (u - 0.5) * 5 * side; legs = "run"; phase = t / 12; dir = side; }
    else if (act === "flee") { x = x0 + X.easeOut(u) * 4 * -side; legs = "run"; phase = t / 11; dir = -side; s = { ...s, face: "scared", arms: "up" }; }
    else if (act === "point") s = { ...s, arms: "point" };
    else if (act === "look") s = { ...s, look: Math.sin(t / 12) };
    else if (act === "hide") s = { ...s, lean: 14 * side, look: side * 0.8 };
    else if (act === "sit") legs = "sit";
    else if (act === "sleep") { legs = "sit"; s = { ...s, face: "sleep", arms: "cross" }; }
    else if (act === "wave") s = { ...s, arms: "cheer" };
    else if (act === "talk") s = { ...s, face: "talk", talk: E.talk(f) };
    else if (act === "shiver") s = { ...s, face: "nervous", arms: "cross", tilt: 3 * Math.sin(f * 1.9) };
    return { id, pos: W(x, 0, z), st: st(seed, { ...s, legs, phase, ...(id === who[0] && prop ? { prop, arms: s.arms === "up" ? "holdR" : (s.arms || "holdR") } : {}), ...extra }), ...(dir ? { flip: dir > 0 } : {}) };
  };
  const host = (x, z, o = {}) => {
    A.push({ id: "host", pos: W(x, 0, z), st: st(3, { legs: "sit", face: o.face || "talk", arms: o.arms || "present", talk: E.talk(f, sh.f0, sh.f1), look: o.look ?? 0.25, ...(o.prop ? { prop: o.prop } : {}) }) });
  };
  const ck = (a, b, fov = 34, fov2 = fov - 2) => E.camAt(f, [{ f: sh.f0, pos: W(...a[0]), look: W(...a[1]), fov }, { f: sh.f1, pos: W(...b[0]), look: W(...b[1]), fov: fov2 }]);

  for (const Lg of (lc.lights || [])) Lg.intensity = Lg.userData.base * (0.86 + 0.1 * Math.sin(f / FPS * 9 + Lg.id) + 0.06 * Math.sin(f / FPS * 23 + Lg.id * 3));
  const fast = sh.loc === "rapids";
  for (const tw of (lc.water || [])) { tw.offset.x = f / FPS * (fast ? 0.02 : 0.015); tw.offset.y = f / FPS * (fast ? 0.35 : 0.025); }
  for (const m of (lc.foam || [])) m.position.z = m.userData.z0 + ((f / FPS * 6 + m.userData.z0 * 7) % 8) - 4;

  let shot = sh.shot;
  const nParts = SH.filter((x) => x.i === sh.i).length;
  if (shot === "host_close") shot = sh.part === nParts - 1 ? "host_close" : "host";
  else if (sh.part >= 1 && !shot.startsWith("host") && shot !== "object") {
    const alt = shot === "wide" || shot === "crowd" || shot === "march" ? ["character", "close"] : shot === "huddle" ? ["close", "wide"] : ["close", "wide"];
    shot = alt[(sh.part - 1) % 2];
  } else if (sh.part >= 1 && shot === "host") shot = sh.part % 2 ? "host_tight" : "host";
  else if (sh.part >= 1 && shot === "object") shot = sh.part % 2 ? "wide" : "object";  // belge uzun kalmasin: mekâna kes, geri dön
  if (["character", "close", "two", "run"].includes(shot) && !who.length) shot = "wide";
  if (lc.boat && ["run", "march", "crowd", "huddle"].includes(shot)) shot = who.length > 1 ? "two" : who.length ? "character" : "wide";

  switch (shot) {
    case "host": case "host_close": {
      host(0.4, -1.55, { face: sh.mood ? mood.face : "talk", look: 0.25 });
      cam = shot === "host_close" ? ck([[0.9, 1.7, 3.9], [-0.3, 1.35, -1.8]], [[1.2, 1.9, 5.6], [-0.5, 1.45, -1.9]], 34, 36)
        : ck([[0.6 * side + 0.5, 1.75, 4.6], [-0.2, 1.35, -1.7]], [[0.5 * side + 0.5, 1.7, 4.0], [-0.1, 1.38, -1.7]], 33, 32);
      dof = { focus: W(0.4, 1.4, -1.55), amount: 5 }; focusPt = W(0, 0, -1.5);
      break;
    }
    case "host_tight": {
      host(0.4, -1.55, { face: mood.face, arms: "think" });
      cam = ck([[0.7, 1.6, 1.6], [0.35, 1.45, -1.55]], [[0.65, 1.6, 1.25], [0.35, 1.47, -1.55]], 30, 29);
      dof = { focus: W(0.4, 1.5, -1.55), amount: 9 };
      break;
    }
    case "wide": {
      who.forEach((id, j) => A.push(actorState(id, 10 + j, (j - (who.length - 1) / 2) * 1.6, -0.8 - j * 0.3)));
      const lx = who.length ? 0 : -1.6 * side;
      cam = who.length ? ck([[-1.6 * side, 2.6, 7.2], [0, 1.6, -2.4]], [[-0.8 * side, 2.3, 6.0], [0, 1.5, -2.4]], 38, 36)
        : ck([[-3.4 * side, 4.2, 12.5], [lx, 2.6, -6]], [[-1.6 * side, 3.2, 10.2], [lx, 2.3, -6]], 40, 37);
      dof = { focus: 9, amount: 2, range: 8 }; fx(W(0, 3.2, -1), 0.8);
      break;
    }
    case "character": {
      A.push(actorState(who[0], 11, 0, -0.4)); if (who[1]) A.push(actorState(who[1], 12, 2.0 * side, -2.6));
      cam = ck([[0.9 * side, 1.8, 5.6], [0, 1.4, -0.4]], [[0.5 * side, 1.75, 4.8], [0, 1.45, -0.4]], 34, 32);
      dof = { focus: W(0, 1.5, -0.4), amount: 7 }; fx(W(0.5, 2.8, -0.3), 0.6);
      break;
    }
    case "close": {
      A.push(actorState(who[0], 11, 0, -0.4));
      cam = ck([[0.25 * side, 1.85, 3.2], [0, 1.68, -0.4]], [[0.15 * side, 1.85, 2.8], [0, 1.7, -0.4]], 30, 28);
      if (sh.mood === "scared" || sh.mood === "shocked") { const s = E.shake(f, sh.f0 + 6, 0.05, 10); cam.pos = cam.pos.map((v, i) => v + s[i]); }
      dof = { focus: W(0, 1.8, -0.4), amount: 10 }; fx(W(0.5, 2.55, -0.3), 0.5, 6);
      break;
    }
    case "two": {
      A.push(actorState(who[0], 11, -0.95, -0.5)); A.push(actorState(who[1] || "k0", 12, 0.95, -0.9, { face: MOOD[sh.mood2]?.face || "neutral", arms: MOOD[sh.mood2]?.arms || "hang" }));
      cam = ck([[0.4 * side, 1.95, 7.2], [0, 1.4, -0.7]], [[0.25 * side, 1.9, 6.4], [0, 1.42, -0.7]], 34, 32);
      dof = { focus: W(0, 1.5, -0.7), amount: 5 }; fx(W(1.0, 2.8, -0.8), 0.55);
      break;
    }
    case "run": {
      const x = (u - 0.5) * 6 * side;
      A.push({ id: who[0], pos: W(x, 0, -0.6), st: st(11, { legs: "run", phase: t / 12, face: MOOD[sh.mood]?.face || "scared", arms: "up", sweat: true }), flip: side > 0 });
      if (who[1]) A.push({ id: who[1], pos: W(x - 2 * side, 0, -1.0), st: st(12, { legs: "run", phase: t / 12 + 0.3, face: MOOD[sh.mood2]?.face || "determined", arms: "reach" }), flip: side > 0 });
      cam = { pos: W(x * 0.7, 1.9, 5.4), look: W(x * 0.85, 1.25, -0.8), fov: 36, roll: 0 };
      dof = { focus: W(x, 1.4, -0.7), amount: 4 }; FX.push({ kind: "dust", pos: W(x - 0.7 * side, 0.5, -0.5), size: 0.7, t: (t / 18) % 1 });
      break;
    }
    case "march": { // bir sıra insan karda yürür (kol, göç, geri çekilme, tırmanış)
      const ids = [...who, ...["k0", "k1", "k2", "k3", "k4", "k5"]].slice(0, 7), up = lc.slope;
      ids.forEach((id, j) => {
        const p0 = (t / 70 + j * 0.9) % 7 - 3.5;
        const x = up ? -3 + j * 1.25 + (t / 80) : (j - 3) * 1.45 + (t / 60) * side, z = up ? -1 - j * 1.1 : -1.2 - (j % 2) * 0.5, y = up ? j * 0.55 + 0 * p0 : 0;
        A.push({ id, pos: W(x, y, z), st: st(20 + j, { legs: "walk", phase: t / 22 + j * 0.37, face: j === 0 && who.length ? mood.face : "determined", arms: j % 3 === 0 ? "holdR" : "hang" }), flip: side > 0 });
      });
      cam = up ? ck([[6, 2.8, 8.4], [0, 2.6, -4]], [[5, 3.0, 7.6], [0, 2.8, -4]], 38, 36) : ck([[-1.6 * side, 2.6, 9.8], [0, 1.4, -1.4]], [[-0.9 * side, 2.4, 8.6], [0, 1.4, -1.4]], 38, 36);
      dof = { focus: 9, amount: 2, range: 8 };
      break;
    }
    case "huddle": { // ateş/soba başında toplanmış küme
      const ids = [...who, ...["k0", "k1", "k2", "k3"]].slice(0, 5), ang = [-2.4, -1.6, -0.8, 0.0, 0.8];
      const cx = lc.obj[0], cz = lc.obj[2] - 0.6;
      ids.forEach((id, j) => { const a = ang[j] - 0.75; A.push({ id, pos: W(cx + Math.sin(a) * 1.7, 0, cz + Math.cos(a) * 1.0 - 0.6), st: st(30 + j, { legs: j % 2 ? "sit" : "stand", face: j === 0 && who.length ? mood.face : ["nervous", "sad", "think", "talk", "neutral"][j], arms: "cross", talk: j === 3 ? E.talk(f) * 0.5 : 0 }) }); });
      cam = ck([[-1.0 * side, 2.2, 7.6], [cx, 1.2, cz]], [[-0.6 * side, 2.0, 6.6], [cx, 1.2, cz]], 34, 32);
      dof = { focus: W(cx, 1.2, cz), amount: 5 };
      break;
    }
    case "crowd": {
      for (let i = 0; i < 8; i++) { const x = -3.6 + i * 1.05, z = -1.8 - (i % 2) * 1.0; A.push({ id: "k" + i, pos: W(x, 0, z), st: st(30 + i, { face: MOOD[sh.mood]?.face || "talk", arms: ["hang", "cross", "chin", "point", "hip", "up", "hang", "cheer"][i], look: x > 0 ? -0.5 : 0.5, talk: i % 2 ? E.talk(f) * 0.6 : 0 }) }); }
      who.slice(0, 1).forEach((id) => A.push(actorState(id, 11, 0, 0.2)));
      cam = ck([[-1.6 * side, 3.0, 10.2], [0, 1.4, -1.4]], [[-0.8 * side, 2.7, 9.0], [0, 1.4, -1.4]], 38, 36);
      dof = { focus: W(0, 1.5, -1.2), amount: 3 }; fx(W(0, 3.2, -1.6), 0.7);
      break;
    }
    case "object": {
      const o = lc.obj, g = R["ins" + sh.i];
      if (g) { g.visible = true; g.position.set(ox + o[0], o[1] + 0.05 * Math.sin(t / 9), o[2] + 0.8); g.rotation.set(0, 0.12 * Math.sin(t / 30), -0.04); g.scale.setScalar(0.25 + 0.75 * X.easeOut(X.span(f, sh.f0, sh.f0 + 10))); }
      cam = ck([[o[0] + 0.2, o[1] + 0.1, o[2] + 4.4], [o[0], o[1], o[2] + 0.8]], [[o[0] + 0.05, o[1] + 0.05, o[2] + 3.9], [o[0], o[1], o[2] + 0.8]], 32, 30);
      dof = { focus: W(o[0], o[1], o[2] + 0.8), amount: 8 };
      FX.push({ kind: "sparkle", pos: W(o[0] + 0.6, o[1] + 0.4, o[2] + 0.95), size: 0.45, t: t / FPS });
      flash = Math.max(0, 1 - t / 5) * 0.25;
      break;
    }
    default: cam = ck([[0, 2.6, 9], [0, 2, -5]], [[0, 2.4, 8], [0, 2, -5]], 38, 36);
  }
  // kalabalık yerlerde geniş çekimde arka plan figüranı
  if (!lc.indoor && ["wide", "character", "two"].includes(shot) && ["frontier", "town", "camp", "harbor"].includes(sh.loc.split("~")[0]) && !A.some((a) => a.id.startsWith("k"))) {
    const dx = ((f * 0.02) % 10) - 5;
    A.push({ id: "k6", pos: W(-2.4 + dx * 0.3, 0, -7.0), st: st(44, { legs: "walk", phase: t / 22, face: "neutral" }), flip: true });
    A.push({ id: "k7", pos: W(2.6, 0, -7.8), st: st(45, { face: "think", arms: "cross" }) });
  }
  // yağan kar: dış mekânda hep; fırtına ışığında yoğun
  const storm = (sh.light === "blizzard" || sh.light === "storm");
  snowFall(f, cam, !lc.indoor && !lc.thaw && sh.snow !== false, storm);
  if (sh.loc === "rapids" && cam) { const k2 = Math.sin(f / FPS * 2.3) * 0.12 + Math.sin(f / FPS * 5.1) * 0.05; cam.pos = [cam.pos[0], cam.pos[1] + k2, cam.pos[2]]; cam.roll = (cam.roll || 0) + Math.sin(f / FPS * 1.7) * 0.035; }
  if (storm) dof = { ...dof, amount: Math.max(dof.amount || 0, 3) };

  if (sh.cta) { const p0 = SH.find((x) => x.i === sh.i).f0; overlay = ctaCard(P.cta || "Subscribe for more stories", X.back(X.span(f, p0 + 6, p0 + 18))); }
  if (sh.card && sh.part === 0 && t < 4 * FPS) overlay = both(overlay, chapterCard(sh.card.title || "", sh.card.sub || "", Math.min(1, t / 6, (4 * FPS - t) / 8)));
  const hE = P.hook_end || 4 * FPS;
  if (NOCAP) overlay = P.hook ? hookTitle(P.hook, 1) : null;
  else if (P.hook && f < hE) overlay = both(hookTitle(P.hook, f < hE - 8 ? 1 : (hE - f) / 8), overlay);
  return { cam, light, dof, actors: A, fx: FX, flash, overlay, focusPt, caption: false };
}
