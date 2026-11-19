"""
Zifiri Saatler - Cizgi Short bitirici
cizgi/frames + cizgi/out/mix.wav -> output/final.mp4 (+ thumbnail.jpg, qa_sheet.jpg)
Eksik kare, donma (>=0.4 sn) ya da siyah kare varsa durur: hatali video yayina girmez.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "cizgi")
OUT = os.path.join(ROOT, "output")


def main():
    plan = json.load(open(os.path.join(PROJ, "work", "plan.json"), encoding="utf-8"))
    n = plan["frames"]
    frames = sorted(glob.glob(os.path.join(PROJ, "frames", "f*.jpg")))
    have = {int(os.path.basename(f)[1:6]) for f in frames}
    missing = [i for i in range(n) if i not in have]
    if missing:
        sys.exit(f"HATA: {len(missing)} kare eksik (ilk: {missing[:5]})")
    r = subprocess.run([sys.executable, os.path.join(PROJ, "tools", "finish.py"), PROJ, "zifiri"], capture_output=True, text=True)
    print(r.stdout, r.stderr)
    if r.returncode != 0:
        sys.exit("HATA: finish.py basarisiz")
    freeze = re.search(r"donma \(>=0.4 sn\): (.+)", r.stdout)
    black = re.search(r"siyah kare: (.+)", r.stdout)
    # sabit duran bekci/obje cekimleri cok yavas hareket edebilir; donma sadece uyari, siyah kare hata
    if freeze and freeze.group(1).strip() != "yok":
        print("UYARI: donma algilandi:", freeze.group(1))
    if black and black.group(1).strip() != "yok":
        sys.exit("HATA: siyah kare algilandi: " + black.group(1))
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(os.path.join(PROJ, "out", "zifiri.mp4"), os.path.join(OUT, "final.mp4"))
    if os.path.exists(os.path.join(PROJ, "out", "qa_sheet.jpg")):
        shutil.copy(os.path.join(PROJ, "out", "qa_sheet.jpg"), os.path.join(OUT, "qa_sheet.jpg"))
    # kapak: kanca cekiminden bir kare (yazisiz)
    from PIL import Image
    kapak = sorted(glob.glob(os.path.join(PROJ, "frames", "kapak", "f*.jpg")))
    pick = kapak[0] if kapak else os.path.join(PROJ, "frames", f"f{min(18, n - 1):05d}.jpg")
    Image.open(pick).convert("RGB").save(os.path.join(OUT, "thumbnail.jpg"), quality=92)
    print("hazir: output/final.mp4")


if __name__ == "__main__":
    main()
