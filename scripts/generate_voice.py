"""
Zifiri Saatler - Seslendirme Uretici
Varsayilan: Wiro uzerinden ElevenLabs v3, ses "Callum" (Zifiri Bekci). Wiro 3 denemede
basarisiz olursa ucretsiz edge-tts'e duser. Wiro TTS kelime-zamani vermedigi
icin word_timings bos doner -> cizgi_build kelime zamanlarini faster-whisper ile cikarir.
"""
import asyncio
import json
import os
import time
import hmac
import hashlib
import re
import edge_tts

# --- edge-tts ayarlari ---
VOICE = "tr-TR-AhmetNeural"
RATE = "+2%"
PITCH = "-12Hz"
MAX_RETRIES = 4
RETRY_DELAY_SECONDS = 8

# --- Wiro TTS (opsiyonel) ---
WIRO_TTS_MODEL = (os.environ.get("WIRO_TTS_MODEL") or "elevenlabs/text-to-speech").strip()  # varsayilan: ElevenLabs (Wiro)
WIRO_API_KEY = os.environ.get("WIRO_API_KEY")
WIRO_API_SECRET = os.environ.get("WIRO_API_SECRET")
WIRO_TTS_VOICE = os.environ.get("WIRO_TTS_VOICE") or "N2lVS1w4EtoT3dr4eOWO"  # Zifiri Bekci sesi: Callum (ElevenLabs)
WIRO_TTS_TEXT_PARAM = os.environ.get("WIRO_TTS_TEXT_PARAM") or "prompt"   # metin alan adi
WIRO_TTS_VOICE_PARAM = os.environ.get("WIRO_TTS_VOICE_PARAM") or "voice"  # ses alan adi
WIRO_TTS_MODEL_ID = os.environ.get("WIRO_TTS_MODEL_ID") or "eleven_v3"  # en canli/duygulu ElevenLabs modeli
WIRO_TTS_OUTPUT_FORMAT = os.environ.get("WIRO_TTS_OUTPUT_FORMAT") or "mp3_44100_128"
AUDIO_URL_RE = re.compile(r'https?://[^\s"\'<>\\]+?\.(?:mp3|wav|m4a|ogg|aac)', re.IGNORECASE)


async def generate_voice_edge(text: str, output_path: str):
    import requests  # noqa (edge-tts kendi indirir; requests burada gereksiz ama uyumluluk)
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")  # kelime kelime zamanlama (cizgi senkronu)
            word_boundaries = []
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        word_boundaries.append({
                            "text": chunk["text"],
                            "offset": chunk["offset"] / 10_000_000,
                            "duration": chunk["duration"] / 10_000_000,
                        })
            return word_boundaries
        except Exception as e:
            last_error = e
            print(f"Deneme {attempt}/{MAX_RETRIES} basarisiz: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError(f"edge-tts {MAX_RETRIES} denemeden sonra basarisiz: {last_error}")


def _wiro_headers():
    if WIRO_API_SECRET:
        nonce = str(int(time.time() * 1000))
        sig = hmac.new(WIRO_API_KEY.encode(), (WIRO_API_SECRET + nonce).encode(), hashlib.sha256).hexdigest()
        return {"Content-Type": "application/json", "x-api-key": WIRO_API_KEY, "x-signature": sig, "x-nonce": nonce}
    return {"Content-Type": "application/json", "x-api-key": WIRO_API_KEY}


def generate_voice_wiro(text: str, output_path: str):
    """Wiro TTS ile ses uretir. word_timings vermez -> [] doner."""
    import requests
    if "elevenlabs" in WIRO_TTS_MODEL.lower():
        # Wiro elevenlabs/text-to-speech GERCEK alanlari (playground'dan):
        # prompt (metin) + model + voice + outputFormat (hepsi zorunlu)
        body = {
            "prompt": text,
            "model": WIRO_TTS_MODEL_ID,
            "voice": WIRO_TTS_VOICE,
            "outputFormat": WIRO_TTS_OUTPUT_FORMAT,
        }
    else:
        body = {WIRO_TTS_TEXT_PARAM: text}
        if WIRO_TTS_VOICE:
            body[WIRO_TTS_VOICE_PARAM] = WIRO_TTS_VOICE
    url = f"https://api.wiro.ai/v1/Run/{WIRO_TTS_MODEL}/sync"
    r = requests.post(url, headers=_wiro_headers(), json=body, timeout=240)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("result") is False:
        raise RuntimeError(f"Wiro TTS hata: {data.get('errors')}")
    found = []
    def walk(o):
        if isinstance(o, str):
            found.extend(AUDIO_URL_RE.findall(o))
        elif isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
    walk(data)
    if not found:
        raise RuntimeError("Wiro TTS ses URL'si bulunamadi. Yanit: " + str(data)[:400])
    ar = requests.get(found[0], stream=True, timeout=120)
    ar.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in ar.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Wiro TTS sesi uretildi ({WIRO_TTS_MODEL})")
    return []


def tighten_voice(path):
    """Olcum (Kas 2026): anlatimimiz 1.6-1.7 kelime/sn, cumle arasi sessizlik %15-21, her videoda 8-9 uzun durak;
    viral referans 2.6 kelime/sn, sessizlik %8, uzun durak yok. Duraklari kisaltir, sesi tonunu bozmadan hizlandirir."""
    import subprocess
    tempo = float(os.environ.get("VOICE_TEMPO", "1.25"))
    keep = float(os.environ.get("VOICE_GAP_KEEP", "0.14"))
    if tempo <= 1.0 and keep <= 0:
        return False
    tmp = path + ".tmp.mp3"
    af = (f"silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02:"
          f"stop_periods=-1:stop_duration={keep + 0.04:.2f}:stop_threshold=-45dB:stop_silence={keep:.2f},"
          f"atempo={tempo:.3f}")
    try:
        before = _dur(path)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af", af, "-ar", "44100", "-b:a", "192k", tmp], check=True)
        after = _dur(tmp)
        if not after or after < before * 0.45:  # asiri kirpma: guvenlik icin orijinal kalsin
            print(f"UYARI: tempo isleme supheli ({before:.1f}s -> {after}s), orijinal ses kullaniliyor")
            os.remove(tmp)
            return False
        os.replace(tmp, path)
        print(f"Tempo: {before:.1f} sn -> {after:.1f} sn (durak <= {keep}s, hiz x{tempo})")
        return True
    except Exception as e:
        print("UYARI: tempo islenemedi:", e)
        return False


def _dur(p):
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)
    text = story["story"]

    if WIRO_TTS_MODEL and WIRO_API_KEY:
        boundaries = None
        for attempt in range(1, 4):
            try:
                boundaries = generate_voice_wiro(text, "output/voice.mp3")
                if os.path.getsize("output/voice.mp3") < 20000:
                    raise RuntimeError("ses dosyasi cok kucuk")
                break
            except Exception as e:
                print(f"Wiro TTS denemesi {attempt}/3 basarisiz: {e}")
                time.sleep(10 * attempt)
        if boundaries is None:
            print("Wiro TTS kullanilamadi, edge-tts'e dusuluyor")
            boundaries = asyncio.run(generate_voice_edge(text, "output/voice.mp3"))
    else:
        boundaries = asyncio.run(generate_voice_edge(text, "output/voice.mp3"))

    if tighten_voice("output/voice.mp3"):
        boundaries = []  # ses degisti: kelime zamanlarini whisper yeniden cikarir

    with open("output/word_timings.json", "w", encoding="utf-8") as f:
        json.dump(boundaries, f, ensure_ascii=False, indent=2)
    print(f"Seslendirme uretildi ({len(boundaries)} kelime zamani)")
