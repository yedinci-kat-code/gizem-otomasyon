// cizgi-short · hazır set parçaları. Hepsi E (Engine) ile çalışır, (x, z) konumu + seçenek alır, Group döner.
// Ölçek: 1 birim = 1 metre, karakter boyu 2.2 m. (c) Burak Özer · MIT
import * as THREE from "three";
import { T } from "./paint.js";
import { shade } from "./cast.js";

const R = (seed) => { let s = seed >>> 0 || 7; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); };

export function makeSets(E) {
  const S = {};
  const M = (c, o) => E.mat(c, o);

  /** bina: ön yüz cepheli kutu + üçgen çatı (veya düz) */
  S.building = (x, z, o = {}) => {
    const { w = 8, d = 7, floors = 3, fh = 3.2, wall = "#f1e3c6", roof = "#c4553f", rot = 0, flatRoof = false, shutter = "#3f7a5a", win = "#6fa8d8", door = true, cols = Math.max(2, Math.round(w / 2.6)), brick = false, shop = null, awning = null, chimney = true, parent } = o;
    const g = E.group(parent, [x, 0, z], rot), h = floors * fh;
    const fac = T.facade({ wall, win, shutter, floors, cols, door, brick, shop });
    const side = T.facade({ wall, win, shutter, floors, cols: Math.max(2, Math.round(d / 2.6)), door: false, brick });
    const plain = M(wall, { map: brick ? T.brick(wall) : T.plaster(wall) });
    E.box(w, h, d, [M("#ffffff", { map: side }), M("#ffffff", { map: side }), plain, plain, M("#ffffff", { map: fac }), plain], [0, 0, 0], { parent: g });
    E.box(w + 0.3, 0.35, d + 0.3, M(shade(wall, 0.78)), [0, h - 0.1, 0], { parent: g });
    if (flatRoof) E.box(w + 0.5, 0.5, d + 0.5, M(shade(wall, 0.7)), [0, h, 0], { parent: g });
    else {
      // mahya sokağa paralel (x ekseni): kiremitler önden görünür
      const rh = Math.min(3.0, d * 0.42), sh = new THREE.Shape(); sh.moveTo(-d / 2 - 0.5, 0); sh.lineTo(d / 2 + 0.5, 0); sh.lineTo(0, rh); sh.lineTo(-d / 2 - 0.5, 0);
      const geo = new THREE.ExtrudeGeometry(sh, { depth: w + 0.5, bevelEnabled: false }); geo.translate(0, 0, -(w + 0.5) / 2);
      const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 0.3, uv.getY(i) * 0.3);
      const m = new THREE.Mesh(geo, [M(shade(wall, 0.92), { map: T.plaster(wall) }), M("#ffffff", { map: T.roof(roof) })]); m.rotation.y = Math.PI / 2; m.position.y = h; E.add(m, g);
      if (chimney) E.box(0.7, 1.8, 0.7, M("#a8604a", { map: T.brick("#a8604a") }), [w * 0.25, h + 0.8, -d * 0.2], { parent: g });
    }
    if (awning) { const a = E.box(w * 0.9, 0.12, 1.4, M(awning), [0, fh * 0.92, d / 2 + 0.7], { parent: g }); a.rotation.x = 0.25; }
    return g;
  };
  /** sıra ev: x0'dan x1'e bir sokak boyunca binalar */
  S.row = (x0, x1, z, o = {}) => {
    const r = R(o.seed || 3), walls = o.walls || ["#f1e3c6", "#f6c8a2", "#cfe0c8", "#f3d6d9", "#d9e3f0", "#f5e6a8"], roofs = o.roofs || ["#c4553f", "#5a6b8a", "#8a4a3a", "#3f6f6a"];
    const out = []; let x = x0;
    while (x < x1) { const w = 6 + r() * 4; out.push(S.building(x + w / 2, z, { w, d: o.d || 7, floors: 2 + Math.floor(r() * 3), wall: walls[Math.floor(r() * walls.length)], roof: roofs[Math.floor(r() * roofs.length)], rot: o.rot || 0, shutter: ["#3f7a5a", "#2f5f8a", "#8a3a3a", "#6a4a8a"][Math.floor(r() * 4)], brick: r() < 0.25, parent: o.parent })); x += w + 0.2; }
    return out;
  };
  /** sokak: parke taşı yol + kaldırımlar, x ekseni boyunca */
  S.street = (o = {}) => {
    const { len = 120, width = 8, z = 0, x = 0, walk = 3, col = "#cbbb9c" } = o;
    const road = E.mat("#ffffff", { map: (() => { const t = T.cobble(col).clone(); t.needsUpdate = true; t.repeat.set(len / 4, width / 4); return t; })() });
    E.box(len, 0.05, width, road, [x, -0.04, z]);
    const sw = E.mat("#ffffff", { map: (() => { const t = T.stone("#d8ccb4").clone(); t.needsUpdate = true; t.repeat.set(len / 3, walk / 3); return t; })() });
    E.box(len, 0.2, walk, sw, [x, 0, z - width / 2 - walk / 2]); E.box(len, 0.2, walk, sw, [x, 0, z + width / 2 + walk / 2]);
  };
  S.tree = (x, z, o = {}) => {
    const { type = "round", s = 1, col = "#5f9e4a", parent } = o; const g = E.group(parent, [x, 0, z]);
    if (type === "pine") { E.cyl(0.15 * s, 0.22 * s, 1.2 * s, M("#6b4428"), [0, 0, 0], { parent: g }); for (let i = 0; i < 3; i++) E.cone((1.5 - i * 0.35) * s, 1.8 * s, M(shade(col, 0.85 + i * 0.08)), [0, (1 + i * 1.1) * s, 0], { parent: g, seg: 8 }); }
    else if (type === "cypress") { E.cyl(0.12 * s, 0.18 * s, 0.8 * s, M("#6b4428"), [0, 0, 0], { parent: g }); E.sphere(0.7 * s, M(shade(col, 0.8)), [0, 2.6 * s, 0], { parent: g, scale: [1, 2.8, 1] }); }
    else if (type === "palm") { E.cyl(0.14 * s, 0.22 * s, 4.5 * s, M("#9a7a4a"), [0, 0, 0], { parent: g, seg: 8 }); for (let i = 0; i < 6; i++) { const l = E.box(0.5 * s, 0.08 * s, 2.4 * s, M(col), [0, 4.5 * s, 0], { parent: g, center: true }); l.rotation.set(0.5, (i / 6) * Math.PI * 2, 0); l.translateZ(1.1 * s); } }
    else { E.cyl(0.18 * s, 0.26 * s, 1.6 * s, M("#6b4428"), [0, 0, 0], { parent: g, seg: 10 }); const r = R(Math.round(x * 13 + z * 7)); for (let i = 0; i < 4; i++) E.sphere((0.9 + r() * 0.4) * s, M(shade(col, 0.9 + r() * 0.2)), [(r() - 0.5) * 1.2 * s, (2.3 + r() * 0.8) * s, (r() - 0.5) * 1.2 * s], { parent: g, seg: 12 }); }
    return g;
  };
  S.bush = (x, z, s = 1, col = "#5f9e4a") => { const g = E.group(null, [x, 0, z]); for (let i = 0; i < 3; i++) E.sphere(0.6 * s, M(shade(col, 0.9 + i * 0.06)), [(i - 1) * 0.55 * s, 0.4 * s, 0], { parent: g, seg: 12 }); return g; };
  S.hills = (o = {}) => { const { z = -90, col = "#7fae5f", n = 7, seed = 5, y = 0 } = o; const r = R(seed); for (let i = 0; i < n; i++) { const m = E.sphere(18 + r() * 20, M(shade(col, 0.85 + r() * 0.2)), [-120 + (i / (n - 1)) * 240 + r() * 20, y - 10, z - r() * 30], { seg: 20 }); m.scale.y = 0.45; m.castShadow = false; } };
  S.mountains = (o = {}) => { const { z = -160, col = "#8f9fc4", n = 6, seed = 9 } = o; const r = R(seed); for (let i = 0; i < n; i++) { const h = 30 + r() * 30, x = -200 + (i / (n - 1)) * 400; const c = E.cone(28 + r() * 16, h, M(shade(col, 0.9 + r() * 0.15)), [x, -2, z - r() * 40], { seg: 7 }); c.castShadow = false; E.cone(9, h * 0.3, M("#f4f6ff"), [x, h * 0.72 - 2, z - 0], { seg: 7 }).position.z = c.position.z; } };
  S.clouds = (o = {}) => { const { n = 6, y = 40, z = -120, seed = 2, spread = 200 } = o; const r = R(seed); for (let i = 0; i < n; i++) E.cloud(-spread / 2 + r() * spread, y + r() * 25, z - r() * 40, 1.2 + r() * 1.4, i + 1); };
  S.lamp = (x, z, o = {}) => { const g = E.group(o.parent, [x, 0, z]); E.cyl(0.08, 0.12, 4, M("#2b2f3a"), [0, 0, 0], { parent: g, seg: 8 }); const glow = !!o.on; E.box(0.5, 0.6, 0.5, M(glow ? "#ffe9a8" : "#f3e7c4", { emissive: glow ? "#ffcf6a" : "#000000", glow: 1.4 }), [0, 4, 0], { parent: g }); E.cone(0.45, 0.35, M("#2b2f3a"), [0, 4.6, 0], { parent: g, seg: 4 }); if (glow) { const l = new THREE.PointLight(0xffc870, 8, 10, 2); l.position.set(0, 4, 0); g.add(l); } return g; };
  S.fence = (x0, x1, z, o = {}) => { const col = o.col || "#f4efe4"; for (let x = x0; x <= x1; x += 0.6) E.box(0.12, 1, 0.06, M(col), [x, 0, z]); E.box(x1 - x0, 0.1, 0.06, M(col), [(x0 + x1) / 2, 0.75, z]); E.box(x1 - x0, 0.1, 0.06, M(col), [(x0 + x1) / 2, 0.35, z]); };
  S.bench = (x, z, rot = 0) => { const g = E.group(null, [x, 0, z], rot); E.box(1.8, 0.1, 0.5, M("#a8743f", { map: T.wood("#a8743f") }), [0, 0.5, 0], { parent: g }); E.box(1.8, 0.4, 0.08, M("#a8743f"), [0, 0.7, -0.24], { parent: g }); for (const s of [-0.8, 0.8]) E.box(0.08, 0.5, 0.45, M("#2b2f3a"), [s, 0, 0], { parent: g }); return g; };

  /** iç mekân: zemin + arka/sol/sağ duvar (ön açık, kamera önden bakar). */
  S.room = (o = {}) => {
    const { w = 10, d = 8, h = 3.6, x = 0, z = 0, wall = T.wallpaper("#f3d9a8", "#e9c58a"), floor = T.planks("#b9824f"), floorRep = 0.35, window: win = true, door = true, ceiling = false, sideWalls = true, parent } = o;
    const g = E.group(parent, [x, 0, z]);
    const fl = floor.clone(); fl.needsUpdate = true; fl.repeat.set(w * floorRep, d * floorRep);
    const fm = E.plane(w, d, M("#ffffff", { map: fl }), [0, 0, 0], { rot: [-Math.PI / 2, 0, 0], parent: g }); fm.castShadow = false;
    const wt = wall.clone(); wt.needsUpdate = true; wt.repeat.set(w / 4, 1);
    E.plane(w, h, M("#ffffff", { map: wt }), [0, h / 2, -d / 2], { parent: g });
    if (sideWalls) { const st = wall.clone(); st.needsUpdate = true; st.repeat.set(d / 4, 1); E.plane(d, h, M("#ffffff", { map: st }), [-w / 2, h / 2, 0], { rot: [0, Math.PI / 2, 0], parent: g }); E.plane(d, h, M("#ffffff", { map: st }), [w / 2, h / 2, 0], { rot: [0, -Math.PI / 2, 0], parent: g }); }
    if (ceiling) E.plane(w, d, M("#f4ecdc"), [0, h, 0], { rot: [Math.PI / 2, 0, 0], parent: g });
    E.box(w, 0.18, 0.06, M("#8a5a36"), [0, 0, -d / 2 + 0.03], { parent: g });
    if (win) S.window(w * 0.22, 1.1, -d / 2 + 0.02, { parent: g, night: o.night });
    if (door) S.door(-w * 0.3, -d / 2 + 0.02, { parent: g });
    return g;
  };
  S.window = (x, y, z, o = {}) => {
    const { w = 1.8, h = 1.6, parent, rotY = 0, night = false } = o; const g = E.group(parent, [x, y, z], rotY);
    E.box(w + 0.24, h + 0.24, 0.1, M("#f4efe4"), [0, 0, 0], { parent: g });
    const skyTex = night ? T.sign("", { bg: "#1b2a5a", border: null }) : T.painting("landscape");
    E.plane(w, h, E.flat("#ffffff", { map: skyTex }), [0, h / 2 + 0.12, 0.06], { parent: g, noShadow: true });
    E.box(0.08, h, 0.06, M("#f4efe4"), [0, 0.12, 0.08], { parent: g }); E.box(w, 0.08, 0.06, M("#f4efe4"), [0, h / 2 + 0.12, 0.08], { parent: g, center: true });
    E.box(w + 0.5, 0.1, 0.25, M("#f4efe4"), [0, 0.05, 0.12], { parent: g });
    return g;
  };
  S.door = (x, z, o = {}) => { const g = E.group(o.parent, [x, 0, z], o.rotY || 0); E.box(1.3, 2.6, 0.08, M("#f4efe4"), [0, 0, 0], { parent: g }); E.box(1.1, 2.45, 0.06, M(o.col || "#8a5a36", { map: T.wood(o.col || "#8a5a36") }), [0, 0, 0.05], { parent: g }); E.sphere(0.06, M("#e8c45a"), [0.4, 1.2, 0.12], { parent: g }); return g; };
  S.table = (x, z, o = {}) => { const { w = 2, d = 1, h = 0.95, col = "#8a5a36", cloth = null, rot = 0, parent } = o; const g = E.group(parent, [x, 0, z], rot); E.box(w, 0.1, d, M(cloth || col, cloth ? {} : { map: T.wood(col) }), [0, h - 0.1, 0], { parent: g }); if (cloth) E.box(w + 0.04, 0.3, d + 0.04, M(cloth), [0, h - 0.4, 0], { parent: g }); for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) E.box(0.09, h - 0.1, 0.09, M(shade(col, 0.8)), [a * (w / 2 - 0.12), 0, b * (d / 2 - 0.12)], { parent: g }); return g; };
  S.chair = (x, z, o = {}) => { const { col = "#8a3a3a", rot = 0, parent } = o; const g = E.group(parent, [x, 0, z], rot); E.box(0.6, 0.1, 0.6, M(col), [0, 0.5, 0], { parent: g }); E.box(0.6, 0.8, 0.08, M(col), [0, 0.55, -0.28], { parent: g }); for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) E.box(0.06, 0.5, 0.06, M("#4a2f20"), [a * 0.25, 0, b * 0.25], { parent: g }); return g; };
  S.desk = (x, z, o = {}) => { const g = S.table(x, z, { w: 2.2, d: 1.1, col: o.col || "#6b4428", rot: o.rot || 0, parent: o.parent }); E.box(0.8, 0.85, 1, M(shade(o.col || "#6b4428", 0.85)), [0.65, 0, 0], { parent: g }); return g; };
  S.shelf = (x, z, o = {}) => { const g = E.group(o.parent, [x, 0, z], o.rot || 0); E.box(1.6, 2.4, 0.45, M("#8a5a36", { map: T.wood("#8a5a36") }), [0, 0, 0], { parent: g }); const r = R(o.seed || 4); for (let s = 0; s < 4; s++) for (let i = 0; i < 6; i++) E.box(0.16, 0.36 + r() * 0.12, 0.3, M(["#b8262e", "#2f5fb0", "#3f8a4a", "#e8a33c", "#6a4a8a"][Math.floor(r() * 5)]), [-0.6 + i * 0.22, 0.22 + s * 0.55, 0.08], { parent: g }); return g; };
  S.crate = (x, z, s = 1, rot = 0) => E.box(0.9 * s, 0.9 * s, 0.9 * s, M("#c79a5b", { map: T.planks("#c79a5b", 4) }), [x, 0, z], { rot: [0, rot, 0] });
  S.barrel = (x, z, s = 1) => { const b = E.cyl(0.42 * s, 0.38 * s, 1.1 * s, M("#9a6a3a", { map: T.planks("#9a6a3a", 8) }), [x, 0, z], { seg: 14 }); return b; };
  S.sack = (x, z, s = 1, txt = "") => { const m = E.sphere(0.45 * s, M("#d9bf8f"), [x, 0.4 * s, z], { scale: [1, 1.1, 0.9] }); return m; };
  S.counter = (x, z, o = {}) => { const { w = 4, col = "#7a4a2a", top = "#d9cbb3", rot = 0, parent } = o; const g = E.group(parent, [x, 0, z], rot); E.box(w, 1.1, 0.9, M(col, { map: T.planks(col, 5) }), [0, 0, 0], { parent: g }); E.box(w + 0.2, 0.08, 1.05, M(top, { map: T.marble(top) }), [0, 1.1, 0], { parent: g }); return g; };
  S.frame = (x, y, z, o = {}) => { const { w = 1.4, h = 1.05, kind = "landscape", rotY = 0, parent, tex } = o; const g = E.group(parent, [x, y, z], rotY); E.box(w + 0.16, h + 0.16, 0.06, M("#c9a24a"), [0, 0, 0], { parent: g, center: true }); E.plane(w, h, M("#ffffff", { map: tex || T.painting(kind) }), [0, 0, 0.035], { parent: g, noShadow: true }); return g; };
  S.rug = (x, z, w = 4, d = 3, col = "#a8343e") => { const m = E.plane(w, d, M("#ffffff", { map: T.carpet(col) }), [x, 0.012, z], { rot: [-Math.PI / 2, 0, 0] }); m.castShadow = false; return m; };
  S.hangLamp = (x, y, z, o = {}) => { const g = E.group(o.parent, [x, y, z]); E.cyl(0.015, 0.015, 1.2, M("#2b2f3a"), [0, 0, 0], { parent: g, seg: 6 }); E.cone(0.45, 0.4, M(o.col || "#3f8a6a", { side: THREE.DoubleSide }), [0, -0.3, 0], { parent: g, seg: 16 }); E.sphere(0.13, M("#fff3c4", { emissive: "#ffd27a", glow: 1.5 }), [0, -0.25, 0], { parent: g }); const l = new THREE.PointLight(0xffd8a0, o.i ?? 6, 9, 2); l.position.set(0, -0.4, 0); g.add(l); return g; };
  /** tabela: direk üstünde metinli pano */
  S.signpost = (x, z, text, o = {}) => { const g = E.group(o.parent, [x, 0, z], o.rot || 0); E.cyl(0.07, 0.07, o.h || 2.2, M("#8a6a46"), [0, 0, 0], { parent: g, seg: 8 }); E.label(T.sign(text, o), o.w || 1.8, (o.w || 1.8) * 0.375, [0, (o.h || 2.2) + 0.3, 0.06], { parent: g }); return g; };
  /** gazete/ belge gibi masaya yatık kâğıt */
  S.paper = (x, y, z, tex, o = {}) => { const m = E.plane(o.w || 0.42, o.h || 0.56, M("#ffffff", { map: tex, side: THREE.DoubleSide }), [x, y, z], { rot: o.rot || [-Math.PI / 2, 0, o.spin || 0] }); m.castShadow = false; return m; };
  S.car = (x, z, o = {}) => { const { col = "#c23b3b", rot = 0 } = o; const g = E.group(null, [x, 0, z], rot); E.box(3.6, 0.9, 1.7, M(col), [0, 0.4, 0], { parent: g }); E.box(2, 0.7, 1.5, M(shade(col, 1.05)), [-0.2, 1.3, 0], { parent: g }); E.box(1.9, 0.5, 1.52, E.mat("#9fd0f0"), [-0.2, 1.38, 0], { parent: g }); for (const [a, b] of [[-1.2, 1], [1.2, 1], [-1.2, -1], [1.2, -1]]) E.cyl(0.38, 0.38, 0.3, M("#22252c"), [a, 0.38, b * 0.85], { parent: g, center: true, rot: [Math.PI / 2, 0, 0] }); return g; };
  S.water = (o = {}) => { const { size = 300, y = -0.3, col = "#3f8fd0", z = 0 } = o; const t = T.water(col).clone(); t.needsUpdate = true; t.repeat.set(size / 8, size / 8); const m = E.plane(size, size, M("#ffffff", { map: t }), [0, y, z], { rot: [-Math.PI / 2, 0, 0] }); m.castShadow = false; m.userData.water = t; return m; };
  S.boat = (x, z, o = {}) => { const { col = "#8a4a2a", s = 1, rot = 0 } = o; const g = E.group(null, [x, 0, z], rot); const sh = new THREE.Shape(); sh.moveTo(-3 * s, 0.9 * s); sh.lineTo(3.4 * s, 0.9 * s); sh.lineTo(2.6 * s, -0.4 * s); sh.lineTo(-2.4 * s, -0.4 * s); sh.lineTo(-3 * s, 0.9 * s); const geo = new THREE.ExtrudeGeometry(sh, { depth: 2 * s, bevelEnabled: false }); geo.translate(0, 0, -s); E.add(new THREE.Mesh(geo, M(col, { map: T.planks(col, 5) })), g); E.box(6 * s, 0.1, 1.8 * s, M("#c9a46a", { map: T.planks("#c9a46a") }), [0, 0.8 * s, 0], { parent: g }); E.cyl(0.1, 0.1, 5 * s, M("#6b4428"), [0, 0.8 * s, 0], { parent: g }); const sail = E.plane(2.8 * s, 3.4 * s, M("#f4efe4", { side: THREE.DoubleSide }), [0.9 * s, 3.4 * s, 0], { parent: g }); sail.rotation.y = Math.PI / 2; return g; };
  return S;
}
