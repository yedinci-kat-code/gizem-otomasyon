#!/usr/bin/env python3
"""cizgi-short · kontak sayfası.  python sheet.py <kare_klasörü> <çıktı.jpg> [sütun=6]"""
import sys, os, glob
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
fs = sorted(glob.glob(os.path.join(src, "*.jpg")))
if not fs: sys.exit("kare yok")
W, H = 270, 480; rows = (len(fs) + cols - 1) // cols
im = Image.new("RGB", (cols * W, rows * H), "#111")
d = ImageDraw.Draw(im)
for i, f in enumerate(fs):
    x, y = (i % cols) * W, (i // cols) * H
    im.paste(Image.open(f).convert("RGB").resize((W, H)), (x, y))
    d.rectangle([x, y, x + 70, y + 22], fill="#000"); d.text((x + 4, y + 4), os.path.basename(f)[1:-4].lstrip("0") or "0", fill="#ff0")
im.save(out, quality=85); print("->", out, f"({len(fs)} kare)")
