// cizgi-short · boyalı dokular (Canvas 2D → THREE.CanvasTexture). Düz renk + koyu derz + hafif fırça lekesi.
// (c) Burak Özer · MIT
import * as THREE from "three";
import { INK, shade, mix } from "./cast.js";

export const rng = (seed) => { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); };
const CACHE = new Map();
export function ctex(key, w, h, draw, opt = {}) {
  if (CACHE.has(key)) return CACHE.get(key);
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d"); draw(g, rng(hash(key)), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  t.wrapS = t.wrapT = opt.clamp ? THREE.ClampToEdgeWrapping : THREE.RepeatWrapping;
  t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter;
  CACHE.set(key, t); return t;
}
const hash = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0; };
export const rep = (t, x, y) => { const c = t.clone(); c.needsUpdate = true; c.repeat.set(x, y); return c; };
const jit = (r, hex, k = 0.08) => shade(hex, 1 + (r() - 0.5) * 2 * k);
const blotch = (g, r, w, h, col, n = 40, s = 0.12, a = 0.08) => { g.globalAlpha = a; for (let i = 0; i < n; i++) { g.fillStyle = r() < 0.5 ? shade(col, 0.9) : shade(col, 1.08); g.beginPath(); g.ellipse(r() * w, r() * h, s * w * (0.4 + r()), s * h * (0.2 + r() * 0.6), r() * 3, 0, 7); g.fill(); } g.globalAlpha = 1; };
const font = (px, w = 900) => `${w} ${px}px CizgiFont, Nunito, Arial, sans-serif`;

export const T = {
  planks: (col = "#b9824f", n = 6) => ctex("planks" + col + n, 512, 512, (g, r, w, h) => {
    const ph = h / n;
    for (let i = 0; i < n; i++) { g.fillStyle = jit(r, col, 0.1); g.fillRect(0, i * ph, w, ph); g.fillStyle = shade(col, 0.62); g.fillRect(0, i * ph, w, 4); const x = r() * w; g.fillRect(x, i * ph, 4, ph); for (let k = 0; k < 2; k++) { g.fillStyle = shade(col, 0.82); g.fillRect(r() * w, i * ph + ph * (0.3 + 0.4 * r()), 40 + r() * 80, 2); } }
    blotch(g, r, w, h, col);
  }),
  wood: (col = "#8a5a36") => T.planks(col, 3),
  stone: (col = "#cdbfa5") => ctex("stone" + col, 512, 512, (g, r, w, h) => {
    g.fillStyle = shade(col, 0.68); g.fillRect(0, 0, w, h);
    const rows = 6, rh = h / rows;
    for (let y = 0; y < rows; y++) { let x = -r() * 60; while (x < w) { const bw = 70 + r() * 70; g.fillStyle = jit(r, col, 0.09); g.beginPath(); g.roundRect(x + 4, y * rh + 4, bw - 8, rh - 8, 10); g.fill(); x += bw; } }
    blotch(g, r, w, h, col, 30, 0.1, 0.06);
  }),
  cobble: (col = "#b7ab95") => ctex("cobble" + col, 512, 512, (g, r, w, h) => {
    g.fillStyle = shade(col, 0.62); g.fillRect(0, 0, w, h);
    for (let y = 0; y < 10; y++) for (let x = 0; x < 10; x++) { g.fillStyle = jit(r, col, 0.1); g.beginPath(); g.ellipse((x + (y % 2) * 0.5) * w / 10 + 3, y * h / 10 + 25, 20 + r() * 4, 18 + r() * 4, r(), 0, 7); g.fill(); }
  }),
  grass: (col = "#7fb35a") => ctex("grass" + col, 512, 512, (g, r, w, h) => {
    g.fillStyle = col; g.fillRect(0, 0, w, h); blotch(g, r, w, h, col, 60, 0.1, 0.12);
    g.strokeStyle = shade(col, 0.78); g.lineWidth = 3; for (let i = 0; i < 260; i++) { const x = r() * w, y = r() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 8, y - 10 - r() * 8); g.stroke(); }
  }),
  dirt: (col = "#c9a87a") => ctex("dirt" + col, 512, 512, (g, r, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); blotch(g, r, w, h, col, 80, 0.08, 0.14); g.fillStyle = shade(col, 0.75); for (let i = 0; i < 120; i++) g.fillRect(r() * w, r() * h, 3 + r() * 5, 3 + r() * 4); }),
  sand: (col = "#e9cf94") => T.dirt(col),
  brick: (col = "#b65a45") => ctex("brick" + col, 512, 512, (g, r, w, h) => {
    g.fillStyle = "#d9cbb3"; g.fillRect(0, 0, w, h);
    const rows = 16, rh = h / rows, bw = w / 6;
    for (let y = 0; y < rows; y++) for (let x = -1; x < 7; x++) { g.fillStyle = jit(r, col, 0.1); g.fillRect(x * bw + (y % 2) * bw / 2 + 3, y * rh + 3, bw - 6, rh - 6); }
  }),
  plaster: (col = "#f1e3c6") => ctex("plaster" + col, 512, 512, (g, r, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); blotch(g, r, w, h, col, 50, 0.14, 0.07); }),
  roof: (col = "#c4553f") => ctex("roof" + col, 512, 512, (g, r, w, h) => {
    g.fillStyle = shade(col, 0.6); g.fillRect(0, 0, w, h);
    const rows = 10, rh = h / rows, tw = w / 8;
    for (let y = 0; y < rows; y++) for (let x = -1; x < 9; x++) { g.fillStyle = jit(r, col, 0.08); g.beginPath(); g.roundRect(x * tw + (y % 2) * tw / 2 + 2, y * rh + 2, tw - 4, rh - 2, [0, 0, 18, 18]); g.fill(); }
  }),
  tiles: (a = "#f1efe8", b = "#3d8a8a", n = 8) => ctex("tiles" + a + b + n, 512, 512, (g, r, w, h) => { const s = w / n; for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { g.fillStyle = (x + y) % 2 ? b : a; g.fillRect(x * s, y * s, s, s); } g.strokeStyle = "rgba(0,0,0,.18)"; g.lineWidth = 3; for (let i = 0; i <= n; i++) { g.beginPath(); g.moveTo(i * s, 0); g.lineTo(i * s, h); g.moveTo(0, i * s); g.lineTo(w, i * s); g.stroke(); } }),
  wallpaper: (a = "#f3d9a8", b = "#e9c58a", kind = "stripe") => ctex("wp" + a + b + kind, 512, 512, (g, r, w, h) => {
    g.fillStyle = a; g.fillRect(0, 0, w, h); g.fillStyle = b;
    if (kind === "stripe") for (let x = 0; x < w; x += 64) g.fillRect(x, 0, 26, h);
    else if (kind === "dots") for (let y = 0; y < h; y += 64) for (let x = (y / 64) % 2 * 32; x < w; x += 64) { g.beginPath(); g.arc(x, y, 9, 0, 7); g.fill(); }
    else if (kind === "diamond") for (let y = 0; y < h; y += 64) for (let x = 0; x < w; x += 64) { g.beginPath(); g.moveTo(x + 32, y + 8); g.lineTo(x + 56, y + 32); g.lineTo(x + 32, y + 56); g.lineTo(x + 8, y + 32); g.fill(); }
    g.fillStyle = shade(a, 0.8); g.fillRect(0, h - 70, w, 70); g.fillStyle = shade(a, 0.65); g.fillRect(0, h - 74, w, 6);
  }),
  carpet: (col = "#a8343e", border = "#e9c25a") => ctex("carpet" + col + border, 512, 512, (g, r, w, h) => { g.fillStyle = border; g.fillRect(0, 0, w, h); g.fillStyle = col; g.fillRect(28, 28, w - 56, h - 56); g.strokeStyle = border; g.lineWidth = 6; g.strokeRect(60, 60, w - 120, h - 120); g.beginPath(); g.ellipse(w / 2, h / 2, 90, 60, 0, 0, 7); g.stroke(); }, { clamp: true }),
  marble: (col = "#eeeae2") => ctex("marble" + col, 512, 512, (g, r, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); g.strokeStyle = shade(col, 0.82); g.lineWidth = 2; for (let i = 0; i < 14; i++) { g.beginPath(); let x = r() * w, y = 0; g.moveTo(x, y); while (y < h) { x += (r() - 0.5) * 50; y += 30; g.lineTo(x, y); } g.stroke(); } g.strokeStyle = "rgba(0,0,0,.15)"; g.lineWidth = 3; g.strokeRect(0, 0, w, h); }),
  metal: (col = "#8d97a6") => ctex("metal" + col, 256, 256, (g, r, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); g.fillStyle = shade(col, 0.8); for (let i = 0; i < 4; i++) for (let k = 0; k < 4; k++) { g.beginPath(); g.arc(20 + i * 64, 20 + k * 64, 4, 0, 7); g.fill(); } }),
  water: (col = "#3f8fd0") => ctex("water" + col, 512, 512, (g, r, w, h) => { g.fillStyle = col; g.fillRect(0, 0, w, h); g.strokeStyle = shade(col, 1.35); g.lineWidth = 4; g.lineCap = "round"; for (let i = 0; i < 40; i++) { const x = r() * w, y = r() * h; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + 15, y - 6, x + 30, y); g.stroke(); } }),
  // cephe: pencereler + panjur + kapı (genişlik/yükseklik metre)
  facade: (o) => {
    const { wall = "#f1e3c6", win = "#6fa8d8", shutter = "#3f7a5a", floors = 3, cols = 3, door = true, trim = "#ffffff", brick = false, shop = null, awning = null } = o;
    const key = "fac" + JSON.stringify(o);
    return ctex(key, 512, 512 * floors / 2, (g, r, w, h) => {
      if (brick) { const b = T.brick(wall).image; for (let y = 0; y < h; y += 512) g.drawImage(b, 0, y); } else { g.fillStyle = wall; g.fillRect(0, 0, w, h); blotch(g, r, w, h, wall, 30, 0.14, 0.06); }
      const fh = h / floors, cw = w / cols;
      for (let f = 0; f < floors; f++) for (let c = 0; c < cols; c++) {
        const ground = f === floors - 1;
        const x = c * cw + cw * 0.28, y = f * fh + fh * 0.22, ww = cw * 0.44, wh = fh * 0.5;
        if (ground && door && c === Math.floor(cols / 2)) { g.fillStyle = shade(shutter || "#6b4428", 0.8); g.fillRect(c * cw + cw * 0.3, f * fh + fh * 0.25, cw * 0.4, fh * 0.75); g.strokeStyle = INK; g.lineWidth = 6; g.strokeRect(c * cw + cw * 0.3, f * fh + fh * 0.25, cw * 0.4, fh * 0.75); g.fillStyle = "#e8c45a"; g.beginPath(); g.arc(c * cw + cw * 0.62, f * fh + fh * 0.65, 6, 0, 7); g.fill(); continue; }
        if (ground && shop) { g.fillStyle = win; g.fillRect(c * cw + 8, f * fh + fh * 0.25, cw - 16, fh * 0.6); g.strokeStyle = INK; g.lineWidth = 5; g.strokeRect(c * cw + 8, f * fh + fh * 0.25, cw - 16, fh * 0.6); continue; }
        g.fillStyle = trim; g.fillRect(x - 6, y - 6, ww + 12, wh + 16);
        const gr = g.createLinearGradient(x, y, x + ww, y + wh); gr.addColorStop(0, shade(win, 1.25)); gr.addColorStop(1, shade(win, 0.75)); g.fillStyle = gr; g.fillRect(x, y, ww, wh);
        g.strokeStyle = INK; g.lineWidth = 5; g.strokeRect(x, y, ww, wh); g.beginPath(); g.moveTo(x + ww / 2, y); g.lineTo(x + ww / 2, y + wh); g.moveTo(x, y + wh * 0.45); g.lineTo(x + ww, y + wh * 0.45); g.stroke();
        if (shutter) { g.fillStyle = shutter; g.fillRect(x - ww * 0.42, y, ww * 0.36, wh); g.fillRect(x + ww * 1.06, y, ww * 0.36, wh); g.strokeRect(x - ww * 0.42, y, ww * 0.36, wh); g.strokeRect(x + ww * 1.06, y, ww * 0.36, wh); }
        g.fillStyle = shade(wall, 0.72); g.fillRect(x - 10, y + wh + 8, ww + 20, 10);
      }
      g.fillStyle = shade(wall, 0.7); for (let f = 1; f < floors; f++) g.fillRect(0, f * fh - 6, w, 10);
      if (shop) { g.fillStyle = shop.bg || "#2f5f6a"; g.fillRect(0, (floors - 1) * fh + 4, w, fh * 0.18); g.fillStyle = shop.fg || "#fff6dc"; g.font = font(Math.round(fh * 0.12)); g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(shop.text || "", w / 2, (floors - 1) * fh + 4 + fh * 0.09); }
    });
  },
  // tabela / poster / gazete: metinli düz yüzey
  sign: (text, o = {}) => {
    const { bg = "#fbf3dc", fg = INK, w = 1024, h = 384, size = 150, border = INK, sub = null, subSize = 60 } = o;
    return ctex("sign" + text + JSON.stringify(o), w, h, (g, r) => {
      g.fillStyle = bg; g.fillRect(0, 0, w, h); if (border) { g.strokeStyle = border; g.lineWidth = 16; g.strokeRect(8, 8, w - 16, h - 16); }
      g.fillStyle = fg; g.textAlign = "center"; g.textBaseline = "middle";
      const lines = String(text).split("\n"); let fs = size; g.font = font(fs);
      while (Math.max(...lines.map((l) => g.measureText(l).width)) > w * 0.86 && fs > 20) { fs -= 4; g.font = font(fs); }
      const y0 = h / 2 - ((lines.length - 1) * fs * 1.05) / 2 - (sub ? subSize * 0.7 : 0);
      lines.forEach((l, i) => g.fillText(l, w / 2, y0 + i * fs * 1.05));
      if (sub) { g.font = font(subSize, 700); g.fillText(sub, w / 2, y0 + (lines.length - 0.2) * fs * 1.05 + subSize * 0.4); }
    }, { clamp: true });
  },
  newspaper: (head, o = {}) => ctex("np" + head + JSON.stringify(o), 768, 1024, (g, r, w, h) => {
    g.fillStyle = "#f3eedf"; g.fillRect(0, 0, w, h);
    g.fillStyle = INK; g.textAlign = "center"; g.font = font(54, 800); g.fillText(o.paper || "GAZETE", w / 2, 70);
    g.fillRect(40, 96, w - 80, 6); g.font = font(24, 700); g.fillText(o.date || "", w / 2, 128);
    const lines = head.split("\n"); let fs = 96; g.font = font(fs); while (Math.max(...lines.map((l) => g.measureText(l).width)) > w - 90) { fs -= 4; g.font = font(fs); }
    g.fillStyle = o.col || INK; lines.forEach((l, i) => g.fillText(l, w / 2, 220 + i * fs * 1.05));
    const y0 = 240 + lines.length * fs * 1.05;
    if (o.pic !== false) { g.fillStyle = "#c9c2ad"; g.fillRect(70, y0, w - 140, 300); g.strokeStyle = INK; g.lineWidth = 6; g.strokeRect(70, y0, w - 140, 300); if (o.picDraw) o.picDraw(g, 70, y0, w - 140, 300); }
    g.fillStyle = "#9b968a"; for (let i = 0; i < 9; i++) { g.fillRect(70, y0 + 340 + i * 36, (w - 160) / 2 - 10, 14); g.fillRect(w / 2 + 10, y0 + 340 + i * 36, (w - 160) / 2 - 10, 14); }
  }, { clamp: true }),
  cloud: (seed = 1, lit = "#fbf8f1", dark = "#d6dcef") => ctex("cloud" + seed + lit, 512, 256, (g, r, w, h) => {
    const blobs = []; for (let i = 0; i < 7; i++) blobs.push([90 + r() * 330, 150 - r() * 50, 50 + r() * 50]);
    g.fillStyle = INK; for (const [x, y, s] of blobs) { g.beginPath(); g.arc(x, y, s + 5, 0, 7); g.fill(); }
    g.fillRect(70, 150, 380, 45);
    g.fillStyle = dark; for (const [x, y, s] of blobs) { g.beginPath(); g.arc(x, y, s, 0, 7); g.fill(); } g.fillRect(75, 150, 370, 40);
    g.fillStyle = lit; for (const [x, y, s] of blobs) { g.beginPath(); g.arc(x - s * 0.15, y - s * 0.18, s * 0.85, 0, 7); g.fill(); }
  }, { clamp: true }),
  blob: () => ctex("blob", 128, 128, (g, r, w, h) => { const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, "rgba(20,10,30,.55)"); gr.addColorStop(1, "rgba(20,10,30,0)"); g.fillStyle = gr; g.fillRect(0, 0, w, h); }, { clamp: true }),
  // resim çerçevesi içi / tablo
  painting: (kind = "landscape") => ctex("paint" + kind, 512, 384, (g, r, w, h) => {
    if (kind === "portrait") { g.fillStyle = "#3a4a5a"; g.fillRect(0, 0, w, h); g.fillStyle = "#f6dcc0"; g.beginPath(); g.arc(w / 2, h * 0.42, 70, 0, 7); g.fill(); g.fillStyle = "#2b2633"; g.fillRect(w / 2 - 90, h * 0.62, 180, h * 0.4); }
    else { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, "#8ec5f0"); gr.addColorStop(1, "#f6e3b4"); g.fillStyle = gr; g.fillRect(0, 0, w, h); g.fillStyle = "#6fa860"; g.beginPath(); g.moveTo(0, h); g.quadraticCurveTo(w * 0.3, h * 0.45, w * 0.6, h * 0.75); g.quadraticCurveTo(w * 0.8, h * 0.55, w, h * 0.7); g.lineTo(w, h); g.fill(); }
  }, { clamp: true }),
};
