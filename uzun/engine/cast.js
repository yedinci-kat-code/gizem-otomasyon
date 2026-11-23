// cizgi-short · karakter çizimi (Canvas 2D). Tasarım alanı 600 x 1000 birim, tabanlar y = 975.
// Büyük yuvarlak kafa + küçük fasulye gövde + tek çizgi kollar/bacaklar + mürekkep kontur.
// Tamamen kod ile çizilir; dışarıdan görsel yok. (c) Burak Özer · MIT
export const INK = "#1d1622";
export const SKINS = ["#fbf5ea", "#f6dcc0", "#e9c3a0", "#c98f66", "#8d5a3b"];
const MOUTH = "#5b1d2a", TONGUE = "#e86f7a", WHITE = "#ffffff";

const rad = (d) => (d * Math.PI) / 180;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
export const shade = (hex, k) => {
  const n = parseInt(hex.slice(1), 16);
  const c = (v) => clamp(Math.round(v * k), 0, 255).toString(16).padStart(2, "0");
  return "#" + c((n >> 16) & 255) + c((n >> 8) & 255) + c(n & 255);
};
export const mix = (a, b, t) => {
  const A = parseInt(a.slice(1), 16), B = parseInt(b.slice(1), 16);
  const c = (s) => Math.round(((A >> s) & 255) * (1 - t) + ((B >> s) & 255) * t).toString(16).padStart(2, "0");
  return "#" + c(16) + c(8) + c(0);
};
const rnd = (seed, k) => { const x = Math.sin(seed * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };

// ---------- çizim yardımcıları ----------
class Pen {
  constructor(g) { this.g = g; this.ol = 9; }
  path(pts, close) { const g = this.g; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); if (close) g.closePath(); }
  poly(pts, fill, ol = this.ol) {
    const g = this.g; this.path(pts, true);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (ol) { g.lineWidth = ol; g.strokeStyle = INK; g.lineJoin = "round"; g.stroke(); }
  }
  ell(cx, cy, rx, ry, fill, ol = this.ol, rot = 0) { this.poly(ellPts(cx, cy, rx, ry, rot), fill, ol); }
  stroke(pts, w, col = INK) { const g = this.g; g.lineCap = "round"; g.lineJoin = "round"; this.path(pts, false); g.strokeStyle = col; g.lineWidth = w; g.stroke(); }
  limb(pts, col, w) { this.stroke(pts, w + 2 * this.ol * 0.8, INK); this.stroke(pts, w, col); }
  arc(cx, cy, rx, ry, a0, a1, w, col = INK) {
    const p = []; for (let i = 0; i <= 20; i++) { const a = rad(a0 + ((a1 - a0) * i) / 20); p.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]); }
    this.stroke(p, w, col);
  }
  dot(x, y, r, col = INK) { const g = this.g; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fillStyle = col; g.fill(); }
  clip(pts, fn) { const g = this.g; g.save(); this.path(pts, true); g.clip(); fn(); g.restore(); }
  // ışık sol üstten: karşı tarafa yumuşak gölge hilali
  crescent(pts, base, dark, cx, cy, R) {
    const g = this.g, gr = g.createRadialGradient(cx - 0.42 * R, cy - 0.5 * R, 0.1 * R, cx - 0.42 * R, cy - 0.5 * R, 1.75 * R);
    gr.addColorStop(0, base); gr.addColorStop(0.62, base); gr.addColorStop(1, dark);
    this.path(pts, true); g.fillStyle = gr; g.fill();
  }
  text(s, x, y, size, col = INK, weight = 900, align = "center") {
    const g = this.g; g.font = `${weight} ${size}px CizgiFont, Nunito, Arial, sans-serif`; g.textAlign = align; g.textBaseline = "middle"; g.fillStyle = col; g.fillText(s, x, y);
  }
}
const ellPts = (cx, cy, rx, ry, rot = 0, n = 48) => {
  const r = rad(rot), out = [];
  for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2, x = rx * Math.cos(a), y = ry * Math.sin(a); out.push([cx + x * Math.cos(r) - y * Math.sin(r), cy + x * Math.sin(r) + y * Math.cos(r)]); }
  return out;
};
const rrect = (x0, y0, x1, y1, r, n = 6) => {
  const p = [];
  for (const [cx, cy, a] of [[x1 - r, y0 + r, -90], [x1 - r, y1 - r, 0], [x0 + r, y1 - r, 90], [x0 + r, y0 + r, 180]])
    for (let i = 0; i <= n; i++) p.push([cx + r * Math.cos(rad(a + (90 * i) / n)), cy + r * Math.sin(rad(a + (90 * i) / n))]);
  return p;
};
// süper elips kafa (üst biraz sivri, çene dolgun), tohumla hafif asimetri
const headPts = (cx, cy, a, b, seed, n = 64) => {
  const out = [], bulge = (rnd(seed, 3) - 0.5) * 0.06;
  for (let i = 0; i < n; i++) {
    const t = (i / n) * Math.PI * 2, c = Math.cos(t), s = Math.sin(t);
    const e = s < 0 ? 2.15 : 2.5;
    let x = a * Math.sign(c) * Math.pow(Math.abs(c), 2 / e), y = b * Math.sign(s) * Math.pow(Math.abs(s), 2 / e);
    x *= 1 + bulge * c; if (s > 0) x *= 1 - 0.06 * s;
    out.push([cx + x, cy + y]);
  }
  return out;
};
const taper = (p, a, b, wa, wb, col = INK) => {
  const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1, nx = -dy / l, ny = dx / l;
  p.poly([[a[0] + nx * wa / 2, a[1] + ny * wa / 2], [b[0] + nx * wb / 2, b[1] + ny * wb / 2], [b[0] - nx * wb / 2, b[1] - ny * wb / 2], [a[0] - nx * wa / 2, a[1] - ny * wa / 2]], col, 0);
  p.dot(a[0], a[1], wa / 2, col); p.dot(b[0], b[1], wb / 2, col);
};

// ---------- yüz ifadeleri ----------
// göz türleri: dot lid happy shock squint closed angry sad wide
export const FACES = {
  neutral: { eye: "dot", brow: [0, 0], mouth: "dash" },
  smug: { eye: "lid", brow: [2, -4], mouth: "smirk" },
  happy: { eye: "happy", brow: [-4, -4], mouth: "smile" },
  laugh: { eye: "closed", brow: [-6, -6], mouth: "laugh" },
  grin: { eye: "happy", brow: [-3, -3], mouth: "grin" },
  shock: { eye: "shock", brow: [-10, -9], mouth: "O" },
  angry: { eye: "angry", brow: [7, -5], mouth: "frown" },
  sad: { eye: "sad", brow: [-6, 5], mouth: "frown" },
  nervous: { eye: "dot", brow: [-6, 4], mouth: "wave" },
  sly: { eye: "lid", brow: [4, -6], mouth: "smirk" },
  think: { eye: "dot", brow: [-5, 2], mouth: "side", look: 0.6 },
  sleep: { eye: "closed", brow: [0, 0], mouth: "o" },
  determined: { eye: "lid", brow: [6, -3], mouth: "dash" },
  wow: { eye: "wide", brow: [-9, -9], mouth: "smileOpen" },
  talk: { eye: "dot", brow: [-2, -2], mouth: "talk" },
  scared: { eye: "shock", brow: [-8, 6], mouth: "wave" },
};

const drawEye = (p, kind, x, y, u, side, look, blink) => {
  const lx = x + look * 4 * u, w = 3.6 * u;
  if (blink >= 0.85 && kind !== "happy" && kind !== "closed") kind = "line";
  switch (kind) {
    case "dot": p.ell(lx, y, 4.6 * u, 6.4 * u, INK, 0); p.dot(lx - 1.3 * u, y - 2.4 * u, 1.3 * u, WHITE); break;
    case "wide": p.ell(lx, y, 5.6 * u, 7.6 * u, INK, 0); p.dot(lx - 1.6 * u, y - 3 * u, 1.6 * u, WHITE); break;
    case "lid": p.ell(lx, y + u, 5.2 * u, 4.6 * u, INK, 0); p.stroke([[x - 8 * u, y - 1.6 * u], [x + 8 * u, y - 1.6 * u]], w); break;
    case "happy": p.arc(x, y + 3 * u, 7 * u, 6 * u, 200, 340, w); break;
    case "closed": p.arc(x, y - 1 * u, 7 * u, 5 * u, 20, 160, w); break;
    case "line": p.stroke([[x - 7 * u, y], [x + 7 * u, y]], w); break;
    case "shock": p.ell(x, y, 8.5 * u, 9.5 * u, WHITE, 2.6 * u); p.dot(lx * 0.5 + x * 0.5, y + u, 2.6 * u); break;
    case "angry": p.ell(lx, y + 1.5 * u, 4.4 * u, 5 * u, INK, 0); break;
    case "sad": p.ell(lx, y + u, 4.4 * u, 5.8 * u, INK, 0); p.dot(lx - 1.2 * u, y - 1.5 * u, 1.2 * u, WHITE); break;
    case "squint": p.stroke([[x + 6 * u * side, y - 4 * u], [x - 6 * u * side, y], [x + 6 * u * side, y + 4 * u]], w); break;
  }
};
const drawMouth = (p, kind, mx, my, u, talk) => {
  const w = 3.4 * u;
  switch (kind) {
    case "dash": p.stroke([[mx - 6 * u, my], [mx + 6 * u, my - 0.6 * u]], w); break;
    case "smirk": p.arc(mx + 2 * u, my - 4 * u, 8 * u, 5 * u, 15, 140, w); break;
    case "smile": p.arc(mx, my - 5 * u, 10 * u, 6 * u, 20, 160, w); break;
    case "frown": p.arc(mx, my + 5 * u, 8 * u, 4.5 * u, 205, 335, w); break;
    case "side": p.stroke([[mx + 2 * u, my], [mx + 11 * u, my - 2 * u]], w); break;
    case "o": p.ell(mx, my, 3.4 * u, 4 * u, MOUTH, 2.4 * u); break;
    case "O": p.ell(mx, my + 2 * u, 8 * u, 10 * u, MOUTH, 3 * u); p.ell(mx, my + 7 * u, 4.6 * u, 3 * u, TONGUE, 0); break;
    case "wave": { const s = []; for (let i = 0; i <= 12; i++) s.push([mx - 9 * u + i * 1.5 * u, my + 1.6 * u * Math.sin(i * 1.4)]); p.stroke(s, 2.8 * u); break; }
    case "grin": case "laugh": case "smileOpen": {
      const W = kind === "laugh" ? 15 : kind === "grin" ? 12 : 11, H = kind === "laugh" ? 13 : kind === "grin" ? 8 : 9;
      const pts = []; for (let i = 0; i <= 16; i++) { const a = Math.PI * (i / 16); pts.push([mx + W * u * Math.cos(a), my - 2 * u + H * u * Math.sin(a)]); }
      p.poly(pts, kind === "grin" ? WHITE : MOUTH, 2.8 * u);
      if (kind !== "grin") p.clip(pts, () => p.ell(mx, my + H * u * 0.85, W * 0.55 * u, H * 0.45 * u, TONGUE, 0));
      else p.stroke([[mx - W * u, my + 2 * u], [mx + W * u, my + 2 * u]], 1.6 * u);
      break;
    }
    case "talk": {
      const o = clamp(talk, 0, 1);
      if (o < 0.15) { p.stroke([[mx - 6 * u, my], [mx + 6 * u, my]], w); break; }
      p.ell(mx, my + 1.5 * u, (5 + 3 * o) * u, (2.5 + 7 * o) * u, MOUTH, 2.8 * u);
      break;
    }
  }
};

// ---------- kol pozları: [üst kol açısı, ön kol açısı] (derece, 0 = aşağı, + = dışa) ----------
export const ARMS = {
  hang: [[10, 4], [10, 4]], hip: [[42, -118], [42, -118]], up: [[132, 18], [132, 18]], shrug: [[58, -72], [58, -72]],
  point: [[10, 4], [88, 2]], wave: [[10, 4], [140, 30]], hold: [[18, 92], [18, 92]], holdR: [[10, 4], [20, 95]],
  chin: [[10, 4], [28, 148]], whisper: [[10, 4], [36, 150]], cheer: [[124, -34], [124, -34]], present: [[10, 4], [62, 40]],
  facepalm: [[10, 4], [30, 160]], cross: "cross", think: [[42, -118], [28, 148]], reach: [[70, 10], [70, 10]], count: [[10, 4], [35, 120]],
};

// ---------- şapka / saç ----------
const drawHair = (p, s, cx, crown, hc, a, b, u) => {
  const col = s.hairCol || "#3a2a20";
  if (s.hair === "short" || s.hair === "part") {
    const pts = []; for (let i = 0; i <= 24; i++) { const t = Math.PI + (Math.PI * i) / 24; pts.push([cx + a * 1.02 * Math.cos(t), hc + b * 1.02 * Math.sin(t) * 1.0]); }
    const cut = hc - b * 0.42;
    const body = pts.map(([x, y]) => [x, Math.min(y, cut + (s.hair === "part" ? (x < cx ? 8 * u : -4 * u) : 0))]);
    body.push([cx + a * 0.98, cut + 6 * u]); body.unshift([cx - a * 0.98, cut + 6 * u]);
    p.poly(body, col, p.ol);
  } else if (s.hair === "long") {
    const pts = []; for (let i = 0; i <= 28; i++) { const t = Math.PI * 0.92 + (Math.PI * 1.16 * i) / 28; pts.push([cx + a * 1.1 * Math.cos(t), hc + b * 1.08 * Math.sin(t)]); }
    pts.push([cx + a * 1.08, hc + b * 0.9]); pts.push([cx + a * 0.8, hc + b * 0.95]); pts.push([cx + a * 0.78, hc - b * 0.2]);
    pts.push([cx, hc - b * 0.55]); pts.push([cx - a * 0.78, hc - b * 0.2]); pts.push([cx - a * 0.8, hc + b * 0.95]); pts.push([cx - a * 1.08, hc + b * 0.9]);
    p.poly(pts, col, p.ol);
  } else if (s.hair === "bun") {
    p.ell(cx, crown - 14 * u, 22 * u, 18 * u, col);
    drawHair(p, { ...s, hair: "short" }, cx, crown, hc, a, b, u);
  } else if (s.hair === "spiky") {
    const pts = [[cx - a * 0.95, hc - b * 0.3]];
    for (let i = 0; i <= 8; i++) { const t = i / 8, x = cx - a * 0.95 + 1.9 * a * t; pts.push([x, hc - b * (i % 2 ? 1.25 : 0.82) - 4 * u]); }
    pts.push([cx + a * 0.95, hc - b * 0.3]); pts.push([cx, hc - b * 0.5]);
    p.poly(pts, col, p.ol);
  }
};
const drawHat = (p, s, cx, crown, hc, a, b, u) => {
  const col = s.hatCol || "#2b2633", band = s.hatBand || "#9b2c3a";
  switch (s.hat) {
    case "tophat": {
      p.poly(rrect(cx - 42 * u, crown - 78 * u, cx + 42 * u, crown + 10 * u, 6 * u), col);
      p.poly(rrect(cx - 42 * u, crown - 8 * u, cx + 42 * u, crown + 6 * u, 2 * u), band, 0);
      p.poly(rrect(cx - 66 * u, crown + 4 * u, cx + 66 * u, crown + 16 * u, 6 * u), col);
      break;
    }
    case "bowler": {
      const pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + 48 * u * Math.cos(t), crown + 14 * u + 52 * u * Math.sin(t)]); }
      p.poly(pts, col); p.poly(rrect(cx - 62 * u, crown + 8 * u, cx + 62 * u, crown + 20 * u, 6 * u), col);
      p.poly(rrect(cx - 47 * u, crown + 2 * u, cx + 47 * u, crown + 9 * u, 2 * u), band, 0);
      break;
    }
    case "fedora": {
      p.poly([[cx - 46 * u, crown + 10 * u], [cx - 40 * u, crown - 40 * u], [cx - 8 * u, crown - 30 * u], [cx, crown - 44 * u], [cx + 8 * u, crown - 30 * u], [cx + 40 * u, crown - 40 * u], [cx + 46 * u, crown + 10 * u]], col);
      p.poly(rrect(cx - 46 * u, crown - 4 * u, cx + 46 * u, crown + 6 * u, 2 * u), band, 0);
      p.poly([[cx - 80 * u, crown + 18 * u], [cx - 60 * u, crown + 4 * u], [cx + 60 * u, crown + 4 * u], [cx + 80 * u, crown + 18 * u], [cx + 50 * u, crown + 22 * u], [cx - 50 * u, crown + 22 * u]], col);
      break;
    }
    case "cap": {
      const pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + a * 0.98 * Math.cos(t), hc - b * 0.28 + b * 0.82 * Math.sin(t)]); }
      p.poly(pts, col); p.poly([[cx - 10 * u, hc - b * 0.32], [cx + a * 1.35, hc - b * 0.3], [cx + a * 1.3, hc - b * 0.18], [cx - 10 * u, hc - b * 0.2]], col);
      p.dot(cx, crown + 4 * u, 5 * u, shade(col, 0.7));
      break;
    }
    case "beret": p.ell(cx - 6 * u, crown + 6 * u, a * 0.95, 26 * u, col, p.ol, -8); p.dot(cx - 4 * u, crown - 20 * u, 5 * u, INK); break;
    case "crown": {
      const y0 = crown + 14 * u, pts = [[cx - 44 * u, y0], [cx - 48 * u, y0 - 50 * u], [cx - 24 * u, y0 - 26 * u], [cx, y0 - 58 * u], [cx + 24 * u, y0 - 26 * u], [cx + 48 * u, y0 - 50 * u], [cx + 44 * u, y0]];
      p.poly(pts, s.hatCol || "#f2c23a"); for (const x of [-48, 0, 48]) p.dot(cx + x * u, y0 - (x ? 50 : 58) * u, 6 * u, "#e04848");
      break;
    }
    case "helmet": {
      const pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + a * 1.06 * Math.cos(t), hc - b * 0.12 + b * 0.95 * Math.sin(t)]); }
      p.poly(pts, s.hatCol || "#5d6b3a"); p.poly(rrect(cx - a * 1.18, hc - b * 0.2, cx + a * 1.18, hc - b * 0.08, 5 * u), s.hatCol || "#5d6b3a");
      break;
    }
    case "chef": {
      for (const [dx, dy, r] of [[-26, -40, 26], [0, -54, 30], [26, -40, 26]]) p.ell(cx + dx * u, crown + dy * u, r * u, r * u, WHITE);
      p.poly(rrect(cx - 40 * u, crown - 30 * u, cx + 40 * u, crown + 12 * u, 4 * u), WHITE);
      break;
    }
    case "hardhat": {
      const pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + a * 0.92 * Math.cos(t), crown + 26 * u + 58 * u * Math.sin(t)]); }
      p.poly(pts, s.hatCol || "#f4b62c"); p.poly(rrect(cx - a * 1.1, crown + 18 * u, cx + a * 1.1, crown + 30 * u, 5 * u), s.hatCol || "#f4b62c");
      break;
    }
    case "fez": p.poly([[cx - 30 * u, crown + 12 * u], [cx - 24 * u, crown - 46 * u], [cx + 24 * u, crown - 46 * u], [cx + 30 * u, crown + 12 * u]], s.hatCol || "#b8262e"); p.stroke([[cx, crown - 46 * u], [cx + 20 * u, crown - 10 * u]], 3 * u); break;
    case "turban": {
      const c = s.hatCol || "#f4efe4";
      p.ell(cx, crown + 18 * u, 70 * u, 40 * u, c);
      for (let i = 0; i < 3; i++) p.arc(cx, crown + 4 * u + i * 13 * u, 64 * u - i * 4 * u, 22 * u, 200, 340, 3.2 * u, shade(c, 0.8));
      p.dot(cx, crown - 14 * u, 9 * u, s.hatBand || "#b8262e");
      break;
    }
    case "kavuk": {
      const c = s.hatCol || "#f4efe4";
      p.poly(rrect(cx - 44 * u, crown - 92 * u, cx + 44 * u, crown + 22 * u, 22 * u), c);
      for (let i = 0; i < 4; i++) p.stroke([[cx - 42 * u, crown - 70 * u + i * 24 * u], [cx + 42 * u, crown - 60 * u + i * 24 * u]], 3 * u, shade(c, 0.8));
      p.ell(cx, crown + 20 * u, 66 * u, 22 * u, s.hatBand || "#c9a24a");
      p.dot(cx, crown - 96 * u, 10 * u, "#b8262e");
      break;
    }
    case "beanie": { // Unfrozen History: örgü bere (kıvrık kenar + ponpon)
      const c = s.hatCol || "#6a2a2a", pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + a * 0.96 * Math.cos(t), hc - b * 0.3 + b * 0.92 * Math.sin(t)]); }
      p.poly(pts, c); p.poly(rrect(cx - a * 1.0, hc - b * 0.42, cx + a * 1.0, hc - b * 0.2, 8 * u), shade(c, 0.82));
      for (let i = -3; i <= 3; i++) p.stroke([[cx + i * a * 0.24, hc - b * 0.95], [cx + i * a * 0.27, hc - b * 0.46]], 2.4 * u, shade(c, 0.7));
      if (s.pompom !== false) p.ell(cx, hc - b * 1.24, 20 * u, 18 * u, shade(c, 1.15));
      break;
    }
    case "fur": { // kürk kulaklı şapka (ushanka)
      const c = s.hatCol || "#5a4632", fur = s.hatBand || "#d9c7a8", pts = []; for (let i = 0; i <= 20; i++) { const t = Math.PI + (Math.PI * i) / 20; pts.push([cx + a * 1.02 * Math.cos(t), hc - b * 0.26 + b * 0.98 * Math.sin(t)]); }
      for (const sd of [-1, 1]) p.poly(rrect(cx + sd * a * 0.98 - 24 * u, hc - b * 0.32, cx + sd * a * 0.98 + 24 * u, hc + b * 0.36, 14 * u), fur);
      p.poly(pts, c); p.poly(rrect(cx - a * 1.08, hc - b * 0.44, cx + a * 1.08, hc - b * 0.18, 14 * u), fur);
      break;
    }
    case "hood": { // kürk kenarlı parka başlığı (yüz açık)
      const c = s.hatCol || "#6a7a5a", fur = s.hatBand || "#e9e0cc", R = [];
      for (let i = 0; i <= 28; i++) { const t = Math.PI * 0.86 + (Math.PI * 1.28 * i) / 28; R.push([cx + a * 1.32 * Math.cos(t), hc + b * 0.05 + b * 1.3 * Math.sin(t)]); }
      p.poly(R, c);
      for (let i = 0; i <= 13; i++) { const t = Math.PI + (Math.PI * i) / 13; p.ell(cx + a * 1.12 * Math.cos(t), hc - b * 0.05 + b * 1.08 * Math.sin(t), 16 * u, 16 * u, fur, 3 * u); }
      break;
    }
    case "police": {
      p.poly(rrect(cx - 50 * u, crown - 34 * u, cx + 50 * u, crown + 10 * u, 10 * u), s.hatCol || "#22305a");
      p.poly([[cx - 44 * u, crown + 6 * u], [cx + 44 * u, crown + 6 * u], [cx + 56 * u, crown + 20 * u], [cx - 56 * u, crown + 20 * u]], INK, 0);
      p.dot(cx, crown - 12 * u, 8 * u, "#e8c45a");
      break;
    }
  }
};

// fener ışıltısı (yumuşak halka)
const g_glow = (p, x, y, r) => { const g = p.g; if (!g) return; const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, "rgba(255,214,110,.55)"); gr.addColorStop(1, "rgba(255,214,110,0)"); g.save(); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.restore(); };
// ---------- elde tutulan obje ----------
export const drawProp = (p, kind, x, y, u, opt = {}) => {
  switch (kind) {
    case "paper": { p.poly(rrect(x - 26 * u, y - 34 * u, x + 26 * u, y + 34 * u, 2 * u), "#fbf8ef", 3 * u); for (let i = 0; i < 5; i++) p.stroke([[x - 17 * u, y - 20 * u + i * 9 * u], [x + (i === 4 ? 4 : 17) * u, y - 20 * u + i * 9 * u]], 2.2 * u, "#9aa0b0"); if (opt.stamp) p.ell(x + 8 * u, y + 20 * u, 9 * u, 9 * u, null, 3 * u); break; }
    case "lantern": { // Zifiri Saatler: fener (eklenti)
      p.stroke([[x, y - 58 * u], [x, y - 40 * u]], 3 * u);
      p.arc(x, y - 62 * u, 9 * u, 8 * u, 180, 360, 3 * u);
      p.poly([[x - 20 * u, y - 40 * u], [x + 20 * u, y - 40 * u], [x + 14 * u, y - 30 * u], [x - 14 * u, y - 30 * u]], "#3a3226", 3 * u);
      p.poly(rrect(x - 16 * u, y - 30 * u, x + 16 * u, y + 22 * u, 4 * u), "#ffd56a", 3 * u);
      p.ell(x, y - 2 * u, 7 * u, 12 * u, "#fff6c8", 0);
      p.stroke([[x - 16 * u, y - 4 * u], [x + 16 * u, y - 4 * u]], 2.4 * u);
      p.poly([[x - 20 * u, y + 22 * u], [x + 20 * u, y + 22 * u], [x + 16 * u, y + 32 * u], [x - 16 * u, y + 32 * u]], "#3a3226", 3 * u);
      break; }
    case "money": { for (let i = 2; i >= 0; i--) { p.poly(rrect(x - 32 * u + i * 3 * u, y - 16 * u - i * 5 * u, x + 32 * u + i * 3 * u, y + 16 * u - i * 5 * u, 3 * u), "#6fb46a", 3 * u); } p.ell(x + 6 * u, y - 10 * u, 8 * u, 8 * u, "#9fd59a", 2.4 * u); p.poly(rrect(x - 4 * u, y - 26 * u, x + 4 * u, y + 6 * u, 1), "#f0e3a8", 0); break; }
    case "bag": { if (opt.gold) for (const [dx, dy] of [[-10, -30], [8, -34], [0, -40]]) p.ell(x + dx * u, y + dy * u, 11 * u, 11 * u, "#f2c23a", 2.6 * u); p.poly([[x - 30 * u, y + 34 * u], [x - 34 * u, y - 4 * u], [x - 12 * u, y - 24 * u], [x + 12 * u, y - 24 * u], [x + 34 * u, y - 4 * u], [x + 30 * u, y + 34 * u]], opt.col || "#c79a5b", 3.2 * u); p.stroke([[x - 14 * u, y - 22 * u], [x + 14 * u, y - 22 * u]], 5 * u, opt.tie || INK); if (opt.text !== "") p.text(opt.text || "$", x, y + 10 * u, 34 * u, INK); break; }
    case "phone": p.poly(rrect(x - 14 * u, y - 26 * u, x + 14 * u, y + 26 * u, 5 * u), "#2b2f3a", 3 * u); p.poly(rrect(x - 10 * u, y - 20 * u, x + 10 * u, y + 18 * u, 2 * u), "#8fd0ff", 0); break;
    case "cup": p.poly([[x - 16 * u, y - 18 * u], [x + 16 * u, y - 18 * u], [x + 12 * u, y + 20 * u], [x - 12 * u, y + 20 * u]], opt.col || WHITE, 3 * u); p.arc(x + 18 * u, y - 2 * u, 8 * u, 9 * u, -80, 80, 3 * u); break;
    case "key": p.ell(x, y - 18 * u, 11 * u, 11 * u, "#f2c23a", 3 * u); p.limb([[x, y - 7 * u], [x, y + 26 * u]], "#f2c23a", 6 * u); p.limb([[x, y + 18 * u], [x + 9 * u, y + 18 * u]], "#f2c23a", 5 * u); break;
    case "coin": p.ell(x, y, 16 * u, 16 * u, "#f2c23a", 3 * u); p.ell(x, y, 10 * u, 10 * u, null, 2 * u); break;
    case "briefcase": p.poly(rrect(x - 36 * u, y - 14 * u, x + 36 * u, y + 30 * u, 5 * u), "#6b4428", 3 * u); p.poly(rrect(x - 12 * u, y - 24 * u, x + 12 * u, y - 12 * u, 3 * u), null, 3 * u); break;
    case "letter": p.poly(rrect(x - 32 * u, y - 20 * u, x + 32 * u, y + 20 * u, 2 * u), "#f4ecd6", 3 * u); p.stroke([[x - 32 * u, y - 20 * u], [x, y + 4 * u], [x + 32 * u, y - 20 * u]], 2.6 * u); p.dot(x, y + 4 * u, 6 * u, "#b8262e"); break;
    case "sign": {
      p.limb([[x, y + 10 * u], [x, y + 120 * u]], "#8a6a46", 7 * u);
      p.poly(rrect(x - 70 * u, y - 46 * u, x + 70 * u, y + 20 * u, 6 * u), opt.col || "#fbf3dc", 3.4 * u);
      if (opt.text) p.text(opt.text, x, y - 13 * u, (opt.size || 26) * u, opt.ink || INK);
      break;
    }
    case "magnifier": p.ell(x, y - 12 * u, 18 * u, 18 * u, "#cfe9ff", 4 * u); p.limb([[x + 12 * u, y + 2 * u], [x + 30 * u, y + 30 * u]], "#6b4428", 6 * u); break;
    case "pen": p.limb([[x - 4 * u, y + 20 * u], [x + 6 * u, y - 24 * u]], "#2f5fb0", 5 * u); break;
    case "scroll": p.poly(rrect(x - 22 * u, y - 36 * u, x + 22 * u, y + 36 * u, 3 * u), "#f2e2b8", 3 * u); p.ell(x, y - 36 * u, 26 * u, 6 * u, "#e2cc96", 3 * u); p.ell(x, y + 36 * u, 26 * u, 6 * u, "#e2cc96", 3 * u); break;
    case "laptop": p.poly([[x - 40 * u, y + 8 * u], [x + 40 * u, y + 8 * u], [x + 48 * u, y + 18 * u], [x - 48 * u, y + 18 * u]], "#9aa3b2", 3 * u); p.poly(rrect(x - 36 * u, y - 40 * u, x + 36 * u, y + 8 * u, 3 * u), "#2b2f3a", 3 * u); p.poly(rrect(x - 31 * u, y - 35 * u, x + 31 * u, y + 3 * u, 2 * u), opt.col || "#7cc4ff", 0); break;
    case "ticket": p.poly(rrect(x - 30 * u, y - 16 * u, x + 30 * u, y + 16 * u, 3 * u), opt.col || "#f6d36b", 3 * u); if (opt.text) p.text(opt.text, x, y, 14 * u, INK); break;
  }
};

// ---------- karakter ----------
// spec: { skin, shirt, pants, shoes, jacket, tie, dress, apron, hat, hatCol, hatBand, hair, hairCol, moustache, beard, glasses, build, seed, belly }
// st:   { face, look, blink, arms (ad veya [[u,l],[u,l]]), legs: stand|walk|sit|run, phase, tilt, headTilt, bob, talk, prop:{kind,hand,text,...}, lean }
export function drawChar(g, spec, st = {}) {
  const p = new Pen(g), u = 1;
  const build = spec.build || "adult", kid = build === "kid", stout = build === "stout";
  const skin = spec.skin || SKINS[0], seed = spec.seed || 1;
  const sole = 975, legLen = kid ? 230 : 330, torsoH = kid ? 170 : stout ? 230 : 215, torsoW = kid ? 118 : stout ? 190 : 150;
  const headA = kid ? 142 : 156, headB = kid ? 134 : 144;
  const ph = (st.phase || 0) * Math.PI * 2, legs = st.legs || "stand";
  const bob = legs === "walk" ? 10 * Math.abs(Math.sin(ph)) : legs === "run" ? 22 * Math.abs(Math.sin(ph)) : 0;
  const sit = legs === "sit";
  const hipY = (sit ? sole - 150 : sole - legLen) - bob + (st.bob || 0);
  const cx = 300, top = hipY - torsoH, shoulderY = top + 38;
  const tilt = rad(st.tilt || 0);
  g.save();
  g.translate(cx, sole); g.rotate(tilt * 0.35); g.translate(-cx, -sole);

  // bacaklar + ayaklar
  const legCol = spec.pants || "#3b3f52", shoe = spec.shoes || INK, lw = kid ? 16 : 18;
  const hipL = [cx - torsoW * 0.22, hipY - 6], hipR = [cx + torsoW * 0.22, hipY - 6];
  let fL, fR;
  if (sit) { fL = [cx - 70, sole - 150]; fR = [cx + 70, sole - 150]; }
  else if (legs === "walk" || legs === "run") {
    const amp = legs === "run" ? 70 : 42, lift = legs === "run" ? 60 : 26;
    fL = [hipL[0] + amp * Math.sin(ph), sole - Math.max(0, lift * Math.sin(ph + Math.PI))];
    fR = [hipR[0] + amp * Math.sin(ph + Math.PI), sole - Math.max(0, lift * Math.sin(ph))];
  } else { fL = [hipL[0] - 8, sole]; fR = [hipR[0] + 8, sole]; }
  const knee = (h, f, side) => sit ? [h[0] + side * 14, h[1] + 4] : [(h[0] + f[0]) / 2 + side * 6, (h[1] + f[1]) / 2];
  for (const [h, f, side] of [[hipL, fL, -1], [hipR, fR, 1]]) {
    if (sit) { p.limb([h, [f[0], h[1] + 10], [f[0], sole - 8]], legCol === INK ? INK : mix(legCol, INK, 0.25), lw); p.ell(f[0] + side * 14, sole - 6, 30, 13, shoe, 7); }
    else { p.limb([h, knee(h, f, side), f], mix(legCol, INK, 0.25), lw); p.ell(f[0] + side * 16, f[1] - 6, 30, 13, shoe, 7); }
  }
  // elbise/etek bacakların üstüne
  if (spec.dress) {
    const pts = [[cx - torsoW * 0.5, top + 80], [cx + torsoW * 0.5, top + 80], [cx + torsoW * 0.82, hipY + 70], [cx - torsoW * 0.82, hipY + 70]];
    p.poly(pts, spec.dress);
  }
  // kanatlar (gövdenin arkasında)
  if (spec.wings) {
    const flap = st.flap ?? 20, wc = spec.wingCol || "#efe3cc", wt = spec.wingTip || "#8a6a46";
    for (const side of [-1, 1]) {
      const bx = cx + side * torsoW * 0.28, by = top + 34;
      for (let k = 5; k >= 0; k--) {
        const L = 370 - k * 36, w = 42 - k * 2;
        const ex = bx + side * Math.cos(rad(flap - k * 13 + 10)) * L, ey = by - Math.sin(rad(flap - k * 13 + 10)) * L;
        const mxp = (bx + ex) / 2, myp = (by + ey) / 2, ang = Math.atan2(ey - by, ex - bx) * 180 / Math.PI;
        p.ell(mxp, myp, L / 2, w, k < 2 ? wt : wc, 6, ang);
      }
      p.ell(bx + side * 55, by + 4, 85, 46, wc, 6, side * -(flap - 10));
    }
  }
  // gövde (fasulye)
  const lean = (st.lean || 0) * 30;
  const body = [];
  for (let i = 0; i <= 40; i++) {
    const t = (i / 40) * Math.PI * 2, c = Math.cos(t), s = Math.sin(t);
    const wy = s > 0 ? 1 + 0.12 * s : 1 - 0.08 * -s;
    body.push([cx + lean * (0.5 - (s + 1) / 2) + (torsoW / 2) * wy * Math.sign(c) * Math.pow(Math.abs(c), 0.8), top + torsoH / 2 + (torsoH / 2) * Math.sign(s) * Math.pow(Math.abs(s), 0.9)]);
  }
  const shirt = spec.shirt || "#3f6fb5";
  p.crescent(body, shirt, shade(shirt, 0.74), cx, top + torsoH / 2, torsoW * 0.6);
  if (spec.jacket) {
    p.clip(body, () => {
      p.poly([[cx - torsoW, top - 10], [cx - 14, top - 10], [cx - 6, top + torsoH * 0.62], [cx - torsoW, hipY + 40]], spec.jacket, 0);
      p.poly([[cx + torsoW, top - 10], [cx + 14, top - 10], [cx + 6, top + torsoH * 0.62], [cx + torsoW, hipY + 40]], spec.jacket, 0);
      p.stroke([[cx - 16, top], [cx - 4, top + torsoH * 0.6]], 5); p.stroke([[cx + 16, top], [cx + 4, top + torsoH * 0.6]], 5);
    });
  }
  if (spec.apron) p.clip(body, () => p.poly(rrect(cx - torsoW * 0.32, top + 40, cx + torsoW * 0.32, hipY + 30, 12), spec.apron, 5));
  if (spec.tie) p.poly([[cx - 9, top + 6], [cx + 9, top + 6], [cx + 13, top + 70], [cx, top + 88], [cx - 13, top + 70]], spec.tie, 5);
  if (spec.buttons) for (let i = 0; i < 3; i++) p.dot(cx, top + 60 + i * 38, 6, spec.buttons);
  if (spec.belt) p.clip(body, () => p.poly(rrect(cx - torsoW, hipY - 30, cx + torsoW, hipY - 10, 2), spec.belt, 5));
  p.poly(body, null, p.ol);
  if (spec.scarf) { // atkı: boyunda bant + sarkan uç
    p.poly(rrect(cx - torsoW * 0.46, top - 16, cx + torsoW * 0.46, top + 26, 18), spec.scarf, 7);
    p.poly([[cx + torsoW * 0.12, top + 18], [cx + torsoW * 0.34, top + 18], [cx + torsoW * 0.3, top + 118], [cx + torsoW * 0.1, top + 112]], shade(spec.scarf, 0.9), 7);
    for (const yy of [top + 96, top + 104]) p.stroke([[cx + torsoW * 0.11, yy], [cx + torsoW * 0.31, yy + 2]], 3, shade(spec.scarf, 0.7));
  }

  // kollar
  let arms = st.arms || "hang";
  const sway = legs === "walk" ? 16 * Math.sin(ph) : legs === "run" ? 34 * Math.sin(ph) : 0;
  const armCol = spec.jacket ? mix(spec.jacket, INK, 0.12) : mix(shirt, INK, 0.12), aw = kid ? 14 : 16, U = kid ? 96 : 112, L = kid ? 86 : 100;
  const hands = [];
  if (arms === "cross") {
    p.limb([[cx - torsoW * 0.42, shoulderY], [cx - torsoW * 0.25, shoulderY + 90], [cx + torsoW * 0.3, shoulderY + 70]], armCol, aw);
    p.limb([[cx + torsoW * 0.42, shoulderY], [cx + torsoW * 0.25, shoulderY + 90], [cx - torsoW * 0.3, shoulderY + 76]], armCol, aw);
    p.dot(cx + torsoW * 0.3, shoulderY + 70, 13, skin); p.dot(cx - torsoW * 0.3, shoulderY + 76, 13, skin);
  } else {
    const A = typeof arms === "string" ? ARMS[arms] || ARMS.hang : arms;
    [[-1, A[0], sway], [1, A[1], -sway]].forEach(([side, [ua, la], sw]) => {
      const sx = cx + side * torsoW * 0.44, sy = shoulderY;
      const wave = arms === "wave" && side === 1 ? 18 * Math.sin((st.phase || 0) * Math.PI * 6) : 0;
      const a1 = rad(ua + sw * 0.4 * side), a2 = rad(ua + la + wave + sw * 0.2 * side);
      const e = [sx + side * U * Math.sin(a1), sy + U * Math.cos(a1)], h = [e[0] + side * L * Math.sin(a2), e[1] + L * Math.cos(a2)];
      p.limb([[sx, sy], e, h], armCol, aw);
      p.ell(h[0], h[1], 14, 14, skin, 6);
      hands.push(h);
    });
  }

  // kafa
  const hTilt = rad(st.headTilt || 0) + tilt * 0.3;
  const hc = top - headB + 26, crown = hc - headB;
  g.save(); g.translate(cx, top + 10); g.rotate(hTilt); g.translate(-cx, -(top + 10));
  const head = headPts(cx, hc, headA, headB, seed);
  if (spec.hair === "long") drawHair(p, spec, cx, crown, hc, headA, headB, u);
  p.crescent(head, skin, shade(skin, 0.86), cx, hc, headA);
  p.poly(head, null, p.ol + 1);
  if (spec.hair) drawHair(p, spec.hair === "long" ? { ...spec, hair: "part" } : spec, cx, crown, hc, headA, headB, u);
  const F = FACES[st.face || "neutral"] || FACES.neutral;
  const uu = headA / 50, look = st.look ?? F.look ?? 0, ey = hc + 6 * uu, ex = 17 * uu, mx = cx + look * 5 * uu, my = hc + 30 * uu;
  drawEye(p, F.eye, cx - ex, ey, uu, -1, look, st.blink || 0);
  drawEye(p, F.eye, cx + ex, ey, uu, 1, look, st.blink || 0);
  const [bi, bo] = F.brow;
  for (const side of [-1, 1]) taper(p, [cx + side * (ex - 7 * uu) + look * 3 * uu, ey - 13 * uu + bi * uu * 0.6], [cx + side * (ex + 8 * uu) + look * 3 * uu, ey - 14 * uu + bo * uu * 0.6], 4 * uu, 2.6 * uu);
  if (spec.glasses) { for (const side of [-1, 1]) p.ell(cx + side * ex + look * 3 * uu, ey, 11 * uu, 10 * uu, null, 2.4 * uu); p.stroke([[cx - ex + 11 * uu, ey], [cx + ex - 11 * uu, ey]], 2.4 * uu); }
  if (spec.moustache) {
    const mc = spec.moustache;
    taper(p, [mx - 2 * uu, my - 8 * uu], [mx - 16 * uu, my - 4 * uu], 6 * uu, 2.6 * uu, mc);
    taper(p, [mx + 2 * uu, my - 8 * uu], [mx + 16 * uu, my - 4 * uu], 6 * uu, 2.6 * uu, mc);
  }
  if (spec.beard) { const pts = []; for (let i = 0; i <= 20; i++) { const t = (i / 20) * Math.PI; pts.push([cx + headA * 0.8 * Math.cos(t), hc + 22 * uu + headB * 0.62 * Math.sin(t)]); } pts.push([cx - headA * 0.8, hc + 22 * uu]); p.poly(pts, spec.beard, p.ol); }
  drawMouth(p, F.mouth, mx, my + (spec.beard ? -4 * uu : 0), uu, st.talk || 0);
  if (spec.hat) drawHat(p, spec, cx, crown, hc, headA, headB, headA / 98);
  if (st.sweat) { p.poly([[cx + headA * 0.75, hc - 40], [cx + headA * 0.86, hc - 8], [cx + headA * 0.64, hc - 8]], "#8fd0ff", 4); }
  if (st.blush) for (const side of [-1, 1]) p.ell(cx + side * 34 * uu, my - 6 * uu, 9 * uu, 5 * uu, "#f4a3a3", 0);
  g.restore();

  // eldeki obje
  if (st.prop && hands.length) {
    const h = st.prop.hand === "l" ? hands[0] : hands[hands.length - 1];
    drawProp(p, st.prop.kind, h[0] + (st.prop.dx || 0), h[1] - 24 + (st.prop.dy || 0), 1.15, st.prop);
  }
  g.restore();
}

// ---------- efekt kartları (512 x 512) ----------
export function drawFx(g, kind, t = 0, opt = {}) {
  const p = new Pen(g); p.ol = 6;
  const c = 256;
  switch (kind) {
    case "question": p.text("?", c, c, 300, opt.col || "#ffd34d"); g.lineWidth = 10; g.strokeStyle = INK; g.strokeText("?", c, c); break;
    case "exclaim": p.text("!", c, c, 320, opt.col || "#ff5a4f"); g.lineWidth = 10; g.strokeStyle = INK; g.strokeText("!", c, c); break;
    case "zzz": for (let i = 0; i < 3; i++) { const s = 70 + i * 40; p.text("Z", 160 + i * 90, 360 - i * 110 - 20 * Math.sin(t * 6 + i), s, "#ffffff"); g.lineWidth = 6; g.strokeStyle = INK; g.strokeText("Z", 160 + i * 90, 360 - i * 110 - 20 * Math.sin(t * 6 + i)); } break;
    case "sweat": p.poly([[c, 60], [c + 70, 260], [c, 330], [c - 70, 260]], "#8fd0ff"); break;
    case "idea": { p.ell(c, 210, 120, 130, "#ffe066"); p.poly(rrect(c - 50, 320, c + 50, 400, 10), "#b9bfcc"); for (let i = 0; i < 8; i++) { const a = (i / 8) * Math.PI * 2; p.stroke([[c + 160 * Math.cos(a), 210 + 160 * Math.sin(a)], [c + 210 * Math.cos(a), 210 + 210 * Math.sin(a)]], 14, "#ffe066"); } break; }
    case "stars": for (let i = 0; i < 5; i++) { const a = t * 4 + (i / 5) * Math.PI * 2; star(p, c + 170 * Math.cos(a), c + 60 * Math.sin(a), 40, "#ffe066"); } break;
    case "burst": { const n = 14, pts = []; for (let i = 0; i < n * 2; i++) { const a = (i / (n * 2)) * Math.PI * 2, r = i % 2 ? 140 : 250; pts.push([c + r * Math.cos(a), c + r * Math.sin(a)]); } p.poly(pts, opt.col || "#fff3a8"); if (opt.text) { p.text(opt.text, c, c, opt.size || 90, INK); } break; }
    case "puff": for (let i = 0; i < 7; i++) { const a = (i / 7) * Math.PI * 2, r = 90 + 120 * t; p.ell(c + r * Math.cos(a), c + r * 0.6 * Math.sin(a), 70 * (1 - t * 0.6), 60 * (1 - t * 0.6), "#f1ece2"); } break;
    case "hearts": for (let i = 0; i < 3; i++) heart(p, 140 + i * 120, 330 - i * 80 - 40 * t, 50 + i * 12); break;
    case "money": for (let i = 0; i < 6; i++) { const x = 70 + ((i * 83 + t * 300) % 380), y = 80 + ((i * 131 + t * 520) % 360); g.save(); g.translate(x, y); g.rotate(i + t * 3); p.poly(rrect(-50, -26, 50, 26, 5), "#6fb46a"); p.ell(0, 0, 14, 14, "#9fd59a", 4); g.restore(); } break;
    case "anger": for (const [x, y] of [[0, 0], [1, 0], [0, 1], [1, 1]]) p.arc(c + (x ? 50 : -50), c + (y ? 50 : -50), 50, 50, x ? (y ? 180 : 90) : (y ? 270 : 0), x ? (y ? 270 : 180) : (y ? 360 : 90), 22, "#e0393e"); break;
    case "lines": for (let i = 0; i < 9; i++) p.stroke([[40, 60 + i * 50], [200 + 200 * ((i * 37) % 7) / 7, 60 + i * 50]], 10, "#ffffff"); break;
    case "dust": for (let i = 0; i < 6; i++) p.ell(80 + i * 70, 420 - 60 * t - (i % 2) * 30, 50 * (1 - t * 0.5), 34 * (1 - t * 0.5), "#e9dcc4"); break;
    case "sparkle": for (let i = 0; i < 4; i++) star(p, 100 + i * 100, 140 + ((i * 97) % 240), 30 + 20 * Math.abs(Math.sin(t * 8 + i)), "#ffffff"); break;
    case "skull": p.ell(c, 230, 140, 130, "#f4f1ea"); p.ell(c - 50, 230, 34, 40, INK, 0); p.ell(c + 50, 230, 34, 40, INK, 0); p.poly(rrect(c - 70, 330, c + 70, 400, 14), "#f4f1ea"); break;
    case "check": p.ell(c, c, 200, 200, "#3fbf6a"); p.stroke([[c - 90, c + 6], [c - 20, c + 80], [c + 100, c - 70]], 44, "#ffffff"); break;
    case "cross": p.ell(c, c, 200, 200, "#e0393e"); p.stroke([[c - 80, c - 80], [c + 80, c + 80]], 44, "#ffffff"); p.stroke([[c + 80, c - 80], [c - 80, c + 80]], 44, "#ffffff"); break;
  }
}
const star = (p, x, y, r, col) => { const pts = []; for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + (i / 10) * Math.PI * 2, rr = i % 2 ? r * 0.45 : r; pts.push([x + rr * Math.cos(a), y + rr * Math.sin(a)]); } p.poly(pts, col); };
const heart = (p, x, y, r) => { const pts = []; for (let i = 0; i < 40; i++) { const t = (i / 40) * Math.PI * 2; pts.push([x + r * 0.06 * 16 * Math.pow(Math.sin(t), 3), y - r * 0.06 * (13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t))]); } p.poly(pts, "#ff5d7a"); };
export { Pen, rrect, ellPts };
