"""
Unfrozen History - uzun video seslendirme.
Wiro uzerinden ElevenLabs (varsayilan ses: "Bill" - yasli, sicak Amerikan anlatici). Uzun metin beat sinirlarindan
~2200 karakterlik parcalara bolunur, her parca ayri seslendirilir, aralarina kisa nefes konup birlestirilir.
Wiro olmazsa ucretsiz edge-tts (en-US) yedegine duser. Cikti: output_uzun/voice.wav
"""
import asyncio
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_voice as gv  # Wiro imzalama + indirme yardimcilari (Zifiri ile ortak)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output_uzun")
VOICE = os.environ.get("UZUN_VOICE") or "pqHfZKP75CvOlQylNhV4"      # ElevenLabs "Bill"
MODEL = os.environ.get("UZUN_TTS_MODEL") or "eleven_multilingual_v2"  # uzun anlatimda en tutarli model
EDGE_VOICE = os.environ.get("UZUN_EDGE_VOICE") or "en-US-GuyNeural"
CHUNK = 2200
GAP = 0.35  # parcalar arasi nefes (sn)


def chunks(beats):
    out, cur = [], ""
    for b in beats:
        t = b["text"].strip()
        if cur and len(cur) + len(t) + 1 > CHUNK:
            out.append(cur); cur = t
        else:
            cur = (cur + " " + t).strip()
    if cur:
        out.append(cur)
    return out


def wiro(text, path):
    gv.WIRO_TTS_VOICE, gv.WIRO_TTS_MODEL_ID = VOICE, MODEL
    gv.generate_voice_wiro(text, path)
    if os.path.getsize(path) < 20000:
        raise RuntimeError("ses parcasi cok kucuk")


async def edge(text, path):
    import edge_tts
    await edge_tts.Communicate(text, EDGE_VOICE, rate="-6%", pitch="-4Hz").save(path)


def main():
    story = json.load(open(os.path.join(OUT, "story.json"), encoding="utf-8"))
    parts = chunks(story["beats"])
    work = os.path.join(OUT, "voice_parts"); os.makedirs(work, exist_ok=True)
    use_wiro = bool(gv.WIRO_API_KEY)
    files, how = [], "wiro-elevenlabs" if use_wiro else "edge-tts"
    for i, text in enumerate(parts):
        p = os.path.join(work, f"p{i:02d}.mp3")
        ok = False
        if use_wiro:
            for a in range(1, 4):
                try:
                    wiro(text, p); ok = True; break
                except Exception as e:
                    print(f"parca {i}: Wiro denemesi {a}/3 basarisiz: {e}"); time.sleep(8 * a)
        if not ok:
            if use_wiro:
                print("UYARI: Wiro kullanilamadi, TUM ses edge-tts ile yeniden uretiliyor (ses tutarliligi icin)")
                use_wiro, how = False, "edge-tts"
                return main_edge(parts, work)
            asyncio.run(edge(text, p))
        files.append(p)
        print(f"parca {i + 1}/{len(parts)} tamam ({len(text)} karakter)")
    join(files)
    print("seslendirme:", how)


def main_edge(parts, work):
    files = []
    for i, text in enumerate(parts):
        p = os.path.join(work, f"e{i:02d}.mp3"); asyncio.run(edge(text, p)); files.append(p)
    join(files)
    print("seslendirme: edge-tts")


def join(files):
    lst = os.path.join(OUT, "voice_parts", "list.txt")
    sil = os.path.join(OUT, "voice_parts", "gap.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(GAP), sil], check=True)
    wavs = []
    for f in files:
        w = f.rsplit(".", 1)[0] + ".wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-ar", "44100", "-ac", "1", w], check=True)
        wavs += [w, sil]
    open(lst, "w").write("".join(f"file '{os.path.abspath(w)}'\n" for w in wavs[:-1]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "44100", "-ac", "1",
                    os.path.join(OUT, "voice.wav")], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              os.path.join(OUT, "voice.wav")], capture_output=True, text=True).stdout)
    print(f"ses: {d / 60:.2f} dk")


if __name__ == "__main__":
    main()
