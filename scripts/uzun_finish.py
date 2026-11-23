"""
Unfrozen History - uzun cizgi video bitirici (YAYIN YOK: yukleme kullanici onayiyla elle yapilir)
uzun/frames + uzun/out/mix.wav -> output_uzun/: final.mp4, preview_720p.mp4, thumbnail.jpg, subtitles_en.srt,
youtube.txt (baslik, aciklama + bolumler + kaynaklar + kredi, etiketler, sabit yorum), qa_sheet.jpg
Eksik ya da siyah kare varsa durur.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "uzun")
OUT = os.path.join(ROOT, "output_uzun")
FPS = 24


def ts(t, sep=","):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def srt(words):
    """Ifade bazli altyazi: noktalama ya da 12 kelime / 84 karakterde bolunur, en fazla 2 satir."""
    lines, cur, k = [], [], 1
    def flush():
        nonlocal k
        if not cur: return
        txt = " ".join(w["w"] for w in cur)
        if len(txt) > 42:  # iki satira bol
            mid = len(txt) // 2; sp = txt.rfind(" ", 0, mid + 8); sp = sp if sp > 10 else txt.find(" ", mid)
            txt = txt[:sp] + "\n" + txt[sp + 1:] if sp > 0 else txt
        lines.append(f"{k}\n{ts(cur[0]['s'])} --> {ts(cur[-1]['e'] + 0.15)}\n{txt}\n"); k += 1; cur.clear()
    for w in words:
        cur.append(w)
        n = sum(len(x["w"]) + 1 for x in cur)
        if re.search(r"[.!?…]$", w["w"]) or len(cur) >= 12 or n > 80 or (re.search(r"[,;:]$", w["w"]) and len(cur) >= 6):
            flush()
    flush()
    return "\n".join(lines)


def main():
    plan = json.load(open(os.path.join(PROJ, "work", "plan.json"), encoding="utf-8"))
    story = json.load(open(os.path.join(OUT, "story.json"), encoding="utf-8"))
    words = json.load(open(os.path.join(PROJ, "work", "words.json"), encoding="utf-8"))
    n = plan["frames"]
    have = {int(os.path.basename(f)[1:6]) for f in glob.glob(os.path.join(PROJ, "frames", "f*.jpg"))}
    missing = [i for i in range(n) if i not in have]
    if missing:
        sys.exit(f"HATA: {len(missing)} kare eksik (ilk: {missing[:5]})")
    env = {**os.environ, "FPS": str(FPS)}
    r = subprocess.run([sys.executable, os.path.join(PROJ, "tools", "finish.py"), PROJ, "unfrozen"], capture_output=True, text=True, env=env)
    print(r.stdout, r.stderr)
    if r.returncode != 0:
        sys.exit("HATA: finish.py basarisiz")
    black = re.search(r"siyah kare: (.+)", r.stdout)
    if black and black.group(1).strip() != "yok":
        bl = [float(x) for x in black.group(1).split(",") if x.strip()]
        if any(b > 0.5 for b in bl):  # acilistaki ilk kare haric
            sys.exit("HATA: siyah kare: " + black.group(1))
    os.makedirs(OUT, exist_ok=True)
    final = os.path.join(OUT, "final.mp4")
    shutil.copy(os.path.join(PROJ, "out", "unfrozen.mp4"), final)
    if os.path.exists(os.path.join(PROJ, "out", "qa_sheet.jpg")):
        shutil.copy(os.path.join(PROJ, "out", "qa_sheet.jpg"), os.path.join(OUT, "qa_sheet.jpg"))
    # onizleme: dala yazilabilecek kadar kucuk (720p)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-vf", "scale=1280:720", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "27", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", os.path.join(OUT, "preview_720p.mp4")], check=True)
    # kapak: altyazisiz + vurucu baslikli kare (render isi 0 uretir)
    from PIL import Image
    kap = sorted(glob.glob(os.path.join(PROJ, "frames", "kapak", "f*.jpg")))
    Image.open(kap[0] if kap else os.path.join(PROJ, "frames", "f00030.jpg")).convert("RGB").resize((1280, 720)).save(os.path.join(OUT, "thumbnail.jpg"), quality=92)
    # altyazi + bolumler
    open(os.path.join(OUT, "subtitles_en.srt"), "w", encoding="utf-8").write(srt(words))
    chapters = []
    for b in plan["beats"]:
        if b.get("card"):
            t = 0 if not chapters else b["f0"] / FPS
            chapters.append(f"{int(t // 60)}:{int(t % 60):02d} {b['card'].get('title', '')}")
    if chapters and not chapters[0].startswith("0:00"):
        chapters.insert(0, "0:00 Intro")
    music = story.get("_music")
    desc = [story.get("description", "").strip(), "", "Chapters", *chapters, "", "Sources"]
    desc += [f"- {s}" for s in story.get("sources", [])]
    desc += ["", f"{story.get('narrator_name', 'The narrator')} is a fictional character built from the memoirs and records of the people who "
             "lived these events; the events, places and dates are real. Animated with code; narration uses a synthetic voice."]
    if music:
        desc += ["", f"Music: \"{music}\" by Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0",
                 "https://creativecommons.org/licenses/by/4.0/"]
    txt = ["=== TITLE (A) ===", story.get("title", ""), "", "=== TITLE (B test) ===", story.get("title_alt", ""), "",
           "=== DESCRIPTION ===", *desc, "", "=== TAGS ===", ", ".join(story.get("tags", [])), "",
           "=== PINNED COMMENT ===", story.get("pinned_comment", ""), "",
           "=== NOTES ===", f"length: {n / FPS / 60:.2f} min · beats: {len(plan['beats'])} · words: {story.get('word_count')}",
           "upload as UNLISTED; Altered or synthetic content: No (cartoon); Made for kids: No"]
    open(os.path.join(OUT, "youtube.txt"), "w", encoding="utf-8").write("\n".join(txt))
    fc = story.get("fact_check", [])
    open(os.path.join(OUT, "fact_check.txt"), "w", encoding="utf-8").write(
        "\n\n".join(f"[tur {x['round']}] beat {x['beat']}: {x['problem']}\n  eski: {x['old']}\n  yeni: {x['new']}" for x in fc)
        or "tarih denetcisi sorun bulmadi")
    # tekrar korumasi kaydi (yalnizca elle baslatilan uretim calismalarinda is akisi bunu dala yazar)
    hist_p = os.path.join(ROOT, "data", "uzun_history.json")
    hist = json.load(open(hist_p, encoding="utf-8")) if os.path.exists(hist_p) else []
    hist.append({"topic": story.get("topic", ""), "title": story.get("title", ""), "music": music})
    os.makedirs(os.path.dirname(hist_p), exist_ok=True)
    json.dump(hist[-100:], open(os.path.join(OUT, "uzun_history.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for f in ("final.mp4", "preview_720p.mp4"):
        print(f, f"{os.path.getsize(os.path.join(OUT, f)) / 1e6:.1f} MB")
    print("hazir: output_uzun/")


if __name__ == "__main__":
    main()
