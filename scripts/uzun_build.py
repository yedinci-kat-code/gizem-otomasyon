"""
Unfrozen History - uzun cizgi video proje hazirlayici
output_uzun/story.json + output_uzun/voice.wav -> uzun/work/{words,plan}.json, uzun/sound.json, uzun/out/mix.wav
Kurallar: cekim sureleri seslendirmeye gore (sabit sure yok, kesmeler duraklara oturur, 2-6.5 sn arasi DUZENSIZ),
tek kesintisiz muzik (sesin altinda ducking), dis mekanlarda ruzgar ambiyansi, acilista vurucu baslik.
"""
import json
import os
import random
import re
import shutil
import subprocess
import sys
import urllib.request

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "uzun")
OUT = os.path.join(ROOT, "output_uzun")
FPS = 24
sys.path.insert(0, os.path.join(PROJ, "tools"))
import timing  # noqa: E402

# Kevin MacLeod (incompetech.com) - CC BY 4.0. Tek parca tum videoda doner; aciklamaya kredi yazilir.
TRACKS = ["Winter Reflections", "Long Note Four", "Frozen Star", "Lost Frontier", "Eternal Hope"]
MUSIC_HISTORY = os.path.join(ROOT, "data", "uzun_music.json")
SR = 48000


def run(*a):
    subprocess.run(list(a), check=True)


def pick_track(seed):
    hist = json.load(open(MUSIC_HISTORY)) if os.path.exists(MUSIC_HISTORY) else []
    pool = [t for t in TRACKS if t not in hist[-2:]] or TRACKS
    rnd = random.Random(seed)
    for name in rnd.sample(pool, len(pool)):
        dst = os.path.join(PROJ, "work", "music.mp3")
        url = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + name.replace(" ", "%20") + ".mp3"
        try:
            urllib.request.urlretrieve(url, dst)
            if os.path.getsize(dst) > 200000:
                json.dump((hist + [name])[-10:], open(MUSIC_HISTORY, "w"))
                print("muzik:", name)
                return dst, name
        except Exception as e:
            print("muzik indirilemedi:", name, e)
    return None, None


def movavg(x, k):
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    h = k // 2
    i0 = np.clip(np.arange(len(x)) - h, 0, len(x)); i1 = np.clip(np.arange(len(x)) + h + 1, 0, len(x))
    return ((c[i1] - c[i0]) / (i1 - i0)).astype(np.float32)


def wind_bed(beats, total_s, path):
    """Dis mekanlarda ruzgar (kahverengi gurultu + yavas dalgalanma); ic mekanda kisik, firtinada guclu."""
    n = int(total_s * SR)
    rng = np.random.default_rng(7)
    out = np.zeros((n, 2), np.float32)
    for ch in range(2):
        w = np.cumsum(rng.standard_normal(n)).astype(np.float32); w -= movavg(w, 4801); w = movavg(w, 9)
        w /= (np.abs(w).max() + 1e-6)
        t = np.arange(n) / SR
        gust = 0.55 + 0.45 * np.sin(t * 0.21 + ch) * np.sin(t * 0.073 + 1.7 * ch)
        out[:, ch] = w * gust
    env = np.zeros(n, np.float32)
    for b in beats:
        a, e = int(b["f0"] / FPS * SR), int(b["f1"] / FPS * SR)
        lvl = 0.12 if b["loc"] in ("cabin", "hq") else 0.45 if b.get("season") == "thaw" else 1.0
        if b.get("light") in ("blizzard", "storm"):
            lvl = 2.4
        env[a:e] = lvl
    env = movavg(env, SR)  # 1 sn yumusak gecis
    out *= env[:, None] * 0.05
    import wave
    with wave.open(path, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes())


def final_mix(voice_sfx, wind, music, total_s, out):
    if music:
        flt = (f"[2:a]aloop=loop=-1:size=2e9,atrim=0:{total_s:.2f},asetpts=N/SR/TB,volume=-17dB,"
               f"afade=t=in:d=1.5,afade=t=out:st={max(0, total_s - 3):.2f}:d=3[m];"
               f"[0:a]asplit=2[v][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=400[md];"
               f"[v][1:a][md]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95[o]")
        run("ffmpeg", "-v", "error", "-y", "-i", voice_sfx, "-i", wind, "-i", music, "-filter_complex", flt, "-map", "[o]", "-ar", "48000", "-ac", "2", out)
    else:
        run("ffmpeg", "-v", "error", "-y", "-i", voice_sfx, "-i", wind, "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[o]", "-map", "[o]", "-ar", "48000", "-ac", "2", out)


def main():
    story = json.load(open(os.path.join(OUT, "story.json"), encoding="utf-8"))
    beats = story["beats"]
    for d in ("work", "frames", "stills", "out"):
        os.makedirs(os.path.join(PROJ, d), exist_ok=True)
    shutil.copy(os.path.join(OUT, "voice.wav"), os.path.join(PROJ, "work", "voice.wav"))
    script = " ".join(b["text"].strip() for b in beats)
    open(os.path.join(PROJ, "script.txt"), "w", encoding="utf-8").write(script)

    # 1) kelime zamanlari: faster-whisper (yoksa sessizlik hizalamasi) - cizgi-short timing.py
    subprocess.run([sys.executable, os.path.join(PROJ, "tools", "timing.py"), PROJ], check=True)
    words = json.load(open(os.path.join(PROJ, "work", "words.json"), encoding="utf-8"))
    sw = timing.script_words(script)
    if len(words) != len(sw):
        print(f"UYARI: kelime sayisi farkli ({len(words)} / {len(sw)})")

    # 2) vuruslar -> kareler (goruntu kelimeden 2 kare once)
    total = int((words[-1]["e"] + 1.2) * FPS) + 1
    wi = 0
    for i, b in enumerate(beats):
        n = len(timing.script_words(b["text"]))
        b["w0"], b["w1"] = wi, min(len(words) - 1, wi + n - 1)
        b["f0"] = 0 if i == 0 else max(0, int(round(words[min(wi, len(words) - 1)]["s"] * FPS)) - 2)
        wi += n
    for i, b in enumerate(beats):
        b["f1"] = beats[i + 1]["f0"] if i + 1 < len(beats) else total
    # ara kesmeler: duraklara oturur, hedef uzunluk her kesmede degisir (2.5 / 4 / 5.5 sn) -> duzensiz ritim
    MIN_PART, MAX_PART = int(2.0 * FPS), int(6.5 * FPS)
    targets = [int(x * FPS) for x in (2.6, 4.2, 5.6, 3.4, 4.8)]
    ti = 0
    for b in beats:
        b["cuts"] = []
        if b["f1"] - b["f0"] <= MAX_PART:
            continue
        cand = []
        for j in range(b["w0"] + 1, b["w1"] + 1):
            f = int(round(words[j]["s"] * FPS)) - 2
            cand.append((f, 0 if re.search(r"[,.;:!?…]$", words[j - 1]["w"]) else 1))
        last = b["f0"]
        while b["f1"] - last > MAX_PART:
            ok = [(f, p) for f, p in cand if f - last >= MIN_PART and b["f1"] - f >= MIN_PART and f - last <= MAX_PART]
            if not ok:
                break
            tg = targets[ti % len(targets)]; ti += 1
            pause = [c for c in ok if c[1] == 0]
            pick = min(pause or ok, key=lambda c: abs((c[0] - last) - tg) + (0 if c[1] == 0 else FPS))[0]
            b["cuts"].append(pick); last = pick
    # acilis basligi: ilk cumle bitene kadar (3-5 sn)
    end = next((w["e"] for w in words if re.search(r"[.!?…]$", w["w"])), 4.0)
    hook_end = int(round(min(5.0, max(3.0, end + 0.2)) * FPS))
    plan = {"title": story.get("title", ""), "cast": story.get("cast", {}), "crowd": story.get("crowd"), "beats": beats,
            "frames": total, "fps": FPS, "cta": "Subscribe for more stories", "hook": (story.get("thumb_hook") or "").strip(),
            "hook_end": hook_end}
    json.dump(plan, open(os.path.join(PROJ, "work", "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shots = sum(len(b["cuts"]) + 1 for b in beats)
    print(f"{len(beats)} beat · {shots} cekim · ort. {total / FPS / shots:.1f} sn/cekim · {total} kare ({total / FPS / 60:.2f} dk)")

    # 3) efektler (audio.py) + ruzgar + tek kesintisiz muzik
    sfx = [{"t": 0.05, "kind": "whoosh", "gain_db": -10}]
    prev = beats[0]["loc"]
    for i, b in enumerate(beats):
        t = b["f0"] / FPS
        if i and b["loc"] != prev:
            sfx.append({"t": max(0, t - 0.15), "kind": "whoosh", "gain_db": -11})
        prev = b["loc"]
        if b.get("fx") == "exclaim": sfx.append({"t": t + 0.3, "kind": "impact", "gain_db": -11})
        elif b.get("fx") == "question": sfx.append({"t": t + 0.3, "kind": "pop", "gain_db": -11})
        elif b.get("fx") in ("idea", "sparkle"): sfx.append({"t": t + 0.3, "kind": "magic", "gain_db": -11})
        if b["shot"] == "object": sfx.append({"t": t + 0.05, "kind": "paper", "gain_db": -10})
        if b["shot"] in ("march", "run") or b.get("action") in ("walk", "march"): sfx.append({"t": t + 0.1, "kind": "footsteps", "gain_db": -15})
        if b.get("mood") in ("scared", "shocked") and b["shot"] == "close": sfx.append({"t": t + 0.2, "kind": "sting", "gain_db": -12})
    json.dump({"voice": "work/voice.wav", "duration": round(total / FPS, 2), "sfx": sorted(sfx, key=lambda s: s["t"])},
              open(os.path.join(PROJ, "sound.json"), "w", encoding="utf-8"), indent=1)
    subprocess.run([sys.executable, os.path.join(PROJ, "tools", "audio.py"), PROJ], check=True)
    mix = os.path.join(PROJ, "out", "mix.wav"); base = os.path.join(PROJ, "work", "voice_sfx.wav"); shutil.move(mix, base)
    wind = os.path.join(PROJ, "work", "wind.wav"); wind_bed(beats, total / FPS, wind)
    music, name = pick_track(story.get("title", ""))
    final_mix(base, wind, music, total / FPS, mix)
    story["_music"] = name
    json.dump(story, open(os.path.join(OUT, "story.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ses miksi tamam")


if __name__ == "__main__":
    main()
