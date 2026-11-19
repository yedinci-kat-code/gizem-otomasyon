"""
Zifiri Saatler - Cizgi Short proje hazirlayici
output/story.json (beats) + output/voice.* + output/word_timings.json
  -> cizgi/work/words.json, cizgi/work/plan.json, cizgi/sound.json, cizgi/out/mix.wav

Cizgi motoru: cizgi-short (Burak Ozer, MIT). Bu dosya planin kare zamanlamasini
seslendirmeye gore cikarir; goruntu sese gore zamanlanir, ses asla kesilmez.
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
FPS = 30
sys.path.insert(0, os.path.join(PROJ, "tools"))
import timing  # noqa: E402  (cizgi-short araci: match / phrases_of / script_words)

VALID_SHOTS = {"bekci_hook", "bekci", "genis", "karakter", "yakin", "ikili", "kovalamaca", "kalabalik", "obje", "gercek", "bekci_kapanis"}


MUSIC_DIR = os.path.join(ROOT, "music")
MUSIC_HISTORY = os.path.join(ROOT, "data", "music_history.json")


def pick_track(story):
    """music/ kutuphanesinden parca secer; son 2 videoda calani tekrar etmez."""
    import random
    files = sorted(f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".wav", ".m4a"))) if os.path.isdir(MUSIC_DIR) else []
    if not files:
        return None
    hist = json.load(open(MUSIC_HISTORY, encoding="utf-8")) if os.path.exists(MUSIC_HISTORY) else []
    pool = [f for f in files if f not in hist[-2:]] or files
    pick = random.Random(story.get("title", "")).choice(pool)
    os.makedirs(os.path.dirname(MUSIC_HISTORY), exist_ok=True)
    json.dump((hist + [pick])[-10:], open(MUSIC_HISTORY, "w", encoding="utf-8"), ensure_ascii=False)
    print("muzik:", pick)
    return os.path.join(MUSIC_DIR, pick)


def mix_music(track, dur, gercek_t):
    """Tek, kesintisiz fon muzigi: sesin altinda, ses konusurken otomatik kisilir (ducking).
    Dinamik: gercek aninin 1.2 sn oncesinde muzik neredeyse susar (gerilim), gercekle geri gelir."""
    voice_mix = os.path.join(PROJ, "out", "mix.wav")      # audio.py: ses + efekt
    base = os.path.join(PROJ, "work", "voice_sfx.wav")
    shutil.move(voice_mix, base)
    if gercek_t:
        a, b = max(0.0, gercek_t - 1.2), gercek_t
        env = f"if(between(t,{a:.2f},{b:.2f}),0.25,1)"
    else:
        env = "1"
    flt = (
        f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur:.2f},asetpts=N/SR/TB,"
        f"volume=-18dB,volume='{env}':eval=frame,afade=t=in:d=0.6,afade=t=out:st={max(0, dur - 1.0):.2f}:d=1.0[m];"
        f"[0:a]asplit=2[v][sc];"
        f"[m][sc]sidechaincompress=threshold=0.03:ratio=4:attack=15:release=350[md];"
        f"[v][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]"
    )
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-i", track, "-filter_complex", flt,
                    "-map", "[out]", "-ar", "48000", "-ac", "2", voice_mix], check=True)
    print("muzik miksi tamam:", os.path.basename(track))


def words_from_edge(sw, boundaries):
    toks = [(b["text"], b["offset"], b["offset"] + b["duration"]) for b in boundaries if b.get("text")]
    return timing.match(sw, toks)


def main():
    story = json.load(open(os.path.join(OUT, "story.json"), encoding="utf-8"))
    beats = [b for b in story.get("beats", []) if b.get("text", "").strip()]
    if not beats:
        sys.exit("HATA: story.json icinde beats yok")
    for d in ("work", "frames", "stills", "out"):
        os.makedirs(os.path.join(PROJ, d), exist_ok=True)
    for old in glob.glob(os.path.join(PROJ, "work", "voice.*")):
        os.remove(old)

    voice = next(iter(sorted(glob.glob(os.path.join(OUT, "voice.*")))), None)
    if not voice:
        sys.exit("HATA: output/voice.* yok")
    ext = os.path.splitext(voice)[1]
    shutil.copy(voice, os.path.join(PROJ, "work", "voice" + ext))
    script = " ".join(b["text"].strip() for b in beats)
    open(os.path.join(PROJ, "script.txt"), "w", encoding="utf-8").write(script)

    # 1) kelime zamanlari: edge-tts sinirlari varsa onlar, yoksa cizgi-short timing.py
    sw = timing.script_words(script)
    wt_path = os.path.join(OUT, "word_timings.json")
    boundaries = json.load(open(wt_path, encoding="utf-8")) if os.path.exists(wt_path) else []
    if len(boundaries) >= max(5, len(sw) // 2):
        words = words_from_edge(sw, boundaries)
        json.dump(words, open(os.path.join(PROJ, "work", "words.json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(timing.phrases_of(words), open(os.path.join(PROJ, "work", "phrases.json"), "w", encoding="utf-8"), ensure_ascii=False)
        print(f"zamanlama: edge-tts kelime sinirlari ({len(boundaries)} -> {len(words)} kelime)")
    else:
        subprocess.run([sys.executable, os.path.join(PROJ, "tools", "timing.py"), PROJ], check=True)
        words = json.load(open(os.path.join(PROJ, "work", "words.json"), encoding="utf-8"))
    if len(words) != len(sw):
        print(f"UYARI: kelime sayisi farkli ({len(words)} / {len(sw)})")

    # 2) vuruslari karelere bagla (gorsel, kelimeden 2 kare once gelir)
    total = int((words[-1]["e"] + 0.6) * FPS) + 1
    wi = 0
    for i, b in enumerate(beats):
        n = len(timing.script_words(b["text"]))
        b["w0"], b["w1"] = wi, min(len(words) - 1, wi + n - 1)
        b["f0"] = 0 if i == 0 else max(0, int(round(words[min(wi, len(words) - 1)]["s"] * FPS)) - 2)
        wi += n
        if b.get("shot") not in VALID_SHOTS:
            b["shot"] = "genis"
    for i, b in enumerate(beats):
        b["f1"] = beats[i + 1]["f0"] if i + 1 < len(beats) else total
    # Uzun vuruslarda ara kesmeler: SABIT SURE YOK, kesme seslendirmedeki
    # duraklara (virgul/nokta) ya da kelime baslarina oturur. Her parca >= 1.5 sn.
    MIN_PART, MAX_PART = 45, 120
    for b in beats:
        b["cuts"] = []
        if b["shot"] == "obje" or b["f1"] - b["f0"] <= MAX_PART:
            continue
        cand = []  # (kare, oncelik): duraktan sonra gelen kelime = 0, diger kelime basi = 1
        for j in range(b["w0"] + 1, b["w1"] + 1):
            f = int(round(words[j]["s"] * FPS)) - 2
            pri = 0 if re.search(r"[,.;:!?…]$", words[j - 1]["w"]) else 1
            cand.append((f, pri))
        last = b["f0"]
        while b["f1"] - last > MAX_PART:
            ok = [(f, p) for f, p in cand if f - last >= MIN_PART and b["f1"] - f >= MIN_PART and f - last <= MAX_PART]
            if not ok:
                break
            pause = [c for c in ok if c[1] == 0]
            pick = (max(pause) if pause else min(ok, key=lambda c: abs((c[0] - last) - 80)))[0]
            b["cuts"].append(pick)
            last = pick
    plan = {"title": story.get("title", ""), "cast": story.get("cast", {}), "beats": beats, "frames": total,
            "cta": story.get("_cta_screen") or "Sıradaki efsane için takip et"}
    json.dump(plan, open(os.path.join(PROJ, "work", "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for b in beats:
        print(f"  {b['f0']:5d}-{b['f1']:5d} kes{b['cuts']!s:12s} {b['shot']:13s} {b.get('loc',''):9s} {b['text'][:60]}")

    # 3) ses tasarimi: tek, kesintisiz gizem muzigi + olaya bagli efektler
    sfx = [{"t": 0.05, "kind": "whoosh", "gain_db": -8}]
    prev_loc = beats[0].get("loc")
    for i, b in enumerate(beats):
        t = b["f0"] / FPS
        if i and b.get("loc") != prev_loc:
            sfx.append({"t": max(0, t - 0.15), "kind": "whoosh", "gain_db": -7})
        prev_loc = b.get("loc")
        fx = b.get("fx")
        if fx == "unlem":
            sfx.append({"t": t + 0.33, "kind": "impact", "gain_db": -8})
        elif fx == "soru":
            sfx.append({"t": t + 0.33, "kind": "pop", "gain_db": -8})
        elif fx == "duman":
            sfx.append({"t": t + 0.33, "kind": "whoosh", "gain_db": -6})
        elif fx in ("yildiz", "fikir"):
            sfx.append({"t": t + 0.33, "kind": "magic", "gain_db": -8})
        if b.get("mood") in ("korku", "saskin") and b.get("shot") in ("yakin", "karakter", "ikili"):
            sfx.append({"t": t + 0.2, "kind": "sting", "gain_db": -9})
        if b.get("action") in ("yuru",):
            sfx.append({"t": t + 0.1, "kind": "footsteps", "gain_db": -12})
        if b.get("shot") == "obje":
            sfx.append({"t": t + 0.05, "kind": "paper", "gain_db": -8})
        if b.get("shot") == "gercek":
            sfx.append({"t": max(0, t - 1.0), "kind": "riser", "gain_db": -12})
            sfx.append({"t": t + 0.1, "kind": "magic", "gain_db": -7})
    track = pick_track(story)
    sound = {"voice": "work/voice" + ext, "duration": round(total / FPS, 2), "sfx": sorted(sfx, key=lambda s: s["t"])}
    if not track:  # music/ bossa kodla uretilen muzige dus
        sound["music"] = {"style": "mystery", "bpm": 84, "start": 0.0, "stop": round(total / FPS, 2), "sting": False, "level_db": -17}
    json.dump(sound, open(os.path.join(PROJ, "sound.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, os.path.join(PROJ, "tools", "audio.py"), PROJ], check=True)  # ses + efekt
    if track:
        gercek = next((b["f0"] / FPS for b in beats if b["shot"] == "gercek"), None)
        mix_music(track, total / FPS, gercek)
    print(f"hazir: {total} kare ({total / FPS:.1f} sn)")


if __name__ == "__main__":
    main()
