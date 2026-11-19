#!/usr/bin/env python3
"""cizgi-short · kareleri render eder (Playwright + Chromium).
Kullanım:
  python render.py <proje> frames            # tüm kareler -> <proje>/frames/f00000.jpg
  python render.py <proje> frames 0-299      # aralık
  python render.py <proje> stills 10,60,140  # tek kareler -> <proje>/stills/
Seçenekler: --scale 0.75  --cpu (GPU yoksa SwiftShader)  --resume  --out klasor
"""
import sys, os, time, base64, threading, functools, http.server, argparse, shutil, platform

def serve(root):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def end_headers(self):
            self.send_header("Cache-Control", "no-store"); super().end_headers()
    Q.extensions_map.update({".js": "text/javascript", ".mjs": "text/javascript", ".ttf": "font/ttf"})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def find_chrome():
    if os.environ.get("CHROME"): return os.environ["CHROME"]
    for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if os.path.exists(p): return p
    return None  # Playwright'ın kendi Chromium'u

def parse_list(s, n):
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part: continue
        if "-" in part:
            a, b = part.split("-"); out += list(range(int(a), min(int(b), n - 1) + 1))
        else: out.append(min(int(part), n - 1))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proj"); ap.add_argument("mode", choices=["frames", "stills"]); ap.add_argument("which", nargs="?", default=None)
    ap.add_argument("--scale", type=float, default=1.0); ap.add_argument("--cpu", action="store_true"); ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out", default=None); ap.add_argument("--query", default="")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    root = os.path.abspath(a.proj); srv = serve(root)
    out = os.path.abspath(a.out or os.path.join(root, "frames" if a.mode == "frames" else "stills"))
    os.makedirs(out, exist_ok=True)
    linux = platform.system() == "Linux"
    args = ["--ignore-gpu-blocklist", "--enable-gpu-rasterization", "--disable-dev-shm-usage", "--no-sandbox"]
    if a.cpu or (linux and not os.environ.get("CIZGI_GPU")): args += ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--use-gl=angle"]
    elif platform.system() == "Windows": args += ["--use-angle=d3d11"]
    with sync_playwright() as p:
        exe = find_chrome()
        b = p.chromium.launch(executable_path=exe, args=args) if exe else p.chromium.launch(args=args)
        pg = b.new_page(viewport={"width": 540, "height": 960})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: print("  [sayfa]", m.text) if m.type in ("error", "warning") else None)
        pg.goto(f"http://127.0.0.1:{srv.server_port}/engine/index.html?scale={a.scale}{'&' + a.query if a.query else ''}")
        try: pg.wait_for_function("window.ready === true", timeout=180000)
        except Exception:
            print("HATA: sahne yüklenemedi.", *errs, sep="\n  "); sys.exit(1)
        meta = pg.evaluate("window.META"); n = meta["frames"]
        print(f"proje: {root}\nkare: {n} ({n/meta['fps']:.2f} sn) · {meta['w']}x{meta['h']} · {'CPU' if '--use-angle=swiftshader' in args else 'GPU'}")
        todo = parse_list(a.which, n) if a.which else list(range(n))
        if a.resume: todo = [f for f in todo if not os.path.exists(os.path.join(out, f"f{f:05d}.jpg"))]
        t0 = time.time()
        for i, f in enumerate(todo):
            url = pg.evaluate(f"window.renderFrame({f})")
            with open(os.path.join(out, f"f{f:05d}.jpg"), "wb") as fh: fh.write(base64.b64decode(url.split(",", 1)[1]))
            if errs: print("HATA (kare", f, "):", errs[-1]); sys.exit(1)
            if (i + 1) % 30 == 0 or i + 1 == len(todo):
                el = time.time() - t0; per = el / (i + 1)
                print(f"  {i+1}/{len(todo)} kare · {per:.2f} sn/kare · kalan ~{per*(len(todo)-i-1)/60:.1f} dk", flush=True)
        b.close()
    print("tamam ->", out)

if __name__ == "__main__":
    main()
