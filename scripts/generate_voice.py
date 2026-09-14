"""
Zifiri Saatler - Seslendirme Uretici
Varsayilan: edge-tts (ucretsiz). WIRO_TTS_MODEL secret'i verilirse Wiro uzerinden
daha DOGAL bir TTS (or. ElevenLabs) kullanilir. Wiro TTS kelime-zamani vermedigi
icin word_timings bos doner -> render karakter-agirlikli altyaziya duser.
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
WIRO_TTS_MODEL = os.environ.get("WIRO_TTS_MODEL", "").strip()  # bos = edge-tts kullan
WIRO_API_KEY = os.environ.get("WIRO_API_KEY")
WIRO_API_SECRET = os.environ.get("WIRO_API_SECRET")
WIRO_TTS_VOICE = os.environ.get("WIRO_TTS_VOICE") or "Brian - Deep, Resonant and Comforting"  # bos=varsayilan
WIRO_TTS_TEXT_PARAM = os.environ.get("WIRO_TTS_TEXT_PARAM") or "prompt"   # metin alan adi
WIRO_TTS_VOICE_PARAM = os.environ.get("WIRO_TTS_VOICE_PARAM") or "voice"  # ses alan adi
WIRO_TTS_MODEL_ID = os.environ.get("WIRO_TTS_MODEL_ID") or "eleven_multilingual_v2"  # bos=varsayilan (hata olursa eleven_flash_v2_5)
WIRO_TTS_OUTPUT_FORMAT = os.environ.get("WIRO_TTS_OUTPUT_FORMAT") or "mp3_44100_128"
AUDIO_URL_RE = re.compile(r'https?://[^\s"\'<>\\]+?\.(?:mp3|wav|m4a|ogg|aac)', re.IGNORECASE)


async def generate_voice_edge(text: str, output_path: str):
    import requests  # noqa (edge-tts kendi indirir; requests burada gereksiz ama uyumluluk)
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
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


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)
    text = story["story"]

    if WIRO_TTS_MODEL and WIRO_API_KEY:
        try:
            boundaries = generate_voice_wiro(text, "output/voice.mp3")
        except Exception as e:
            print(f"Wiro TTS basarisiz, edge-tts'e dusuluyor: {e}")
            boundaries = asyncio.run(generate_voice_edge(text, "output/voice.mp3"))
    else:
        boundaries = asyncio.run(generate_voice_edge(text, "output/voice.mp3"))

    with open("output/word_timings.json", "w", encoding="utf-8") as f:
        json.dump(boundaries, f, ensure_ascii=False, indent=2)
    print(f"Seslendirme uretildi ({len(boundaries)} kelime zamani)")
