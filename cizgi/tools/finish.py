#!/usr/bin/env python3
"""cizgi-short · kareleri + sesi MP4'e çevirir, -14 LUFS'a ayarlar, kalite kontrol yapar.
python finish.py <proje> "Başlık"   → <proje>/out/<başlık>.mp4 + out/qa_sheet.jpg"""
import sys, os, re, json, glob, shutil, subprocess
def ff():
    f = shutil.which("ffmpeg")
    if f: return f
    import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
proj = os.path.abspath(sys.argv[1]); title = sys.argv[2] if len(sys.argv) > 2 else "cizgi-short"
slug = re.sub(r"[^\w\-]+", "_", title).strip("_")[:60] or "video"
out = os.path.join(proj, "out"); os.makedirs(out, exist_ok=True)
frames = sorted(glob.glob(os.path.join(proj, "frames", "f*.jpg")))
if not frames: sys.exit("frames/ boş: önce render.py çalıştır")
n = len(frames); last = int(os.path.basename(frames[-1])[1:6])
if last + 1 != n: print(f"UYARI: {last+1} kare beklenirken {n} kare var (eksik kare?)")
mix = os.path.join(out, "mix.wav")
if not os.path.exists(mix):
    v = next(iter(glob.glob(os.path.join(proj, "work", "voice.*"))), None); mix = v
    print("UYARI: out/mix.wav yok, sadece seslendirme kullanılıyor")
# 1) ses: tek doğrusal kazanç ile -14 LUFS (iki geçiş loudnorm, linear=true)
r = subprocess.run([ff(), "-hide_banner", "-i", mix, "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
af = f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
dst = os.path.join(out, slug + ".mp4")
subprocess.run([ff(), "-v", "error", "-y", "-framerate", "30", "-i", os.path.join(proj, "frames", "f%05d.jpg"), "-i", mix,
    "-af", af, "-ar", "48000", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "192k", "-shortest", dst], check=True)
# 2) kalite kontrol: donma / siyah kare + ses seviyesi
q = subprocess.run([ff(), "-hide_banner", "-i", dst, "-vf", "freezedetect=n=0.002:d=0.4,blackdetect=d=0.1:pix_th=0.06", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
fr = re.findall(r"freeze_start: ([\d.]+)", q); bl = re.findall(r"black_start:([\d.]+)", q); I = re.findall(r"I:\s+(-?[\d.]+) LUFS", q)
print(f"video: {dst}\n  {n} kare · {n/30:.2f} sn · loudness {I[-1] if I else '?'} LUFS")
print("  donma (>=0.4 sn):", ", ".join(fr) if fr else "yok"); print("  siyah kare:", ", ".join(bl) if bl else "yok")
# 3) QA kontak sayfası: her saniyeden bir kare
try:
    from PIL import Image
    pick = frames[::30][:48]; W, H, c = 180, 320, 8; rows = (len(pick) + c - 1) // c
    im = Image.new("RGB", (c * W, rows * H), "#111")
    for i, f in enumerate(pick): im.paste(Image.open(f).resize((W, H)), ((i % c) * W, (i // c) * H))
    im.save(os.path.join(out, "qa_sheet.jpg"), quality=82); print("  QA sayfası: out/qa_sheet.jpg")
except Exception as e: print("  QA sayfası atlandı:", e)
