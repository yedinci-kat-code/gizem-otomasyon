"""Gecici: Zifiri Bekci icin ses ornekleri (edge-tts + ElevenLabs/Wiro). Sonuc ses_ornek/out/ altina."""
import hashlib, hmac, json, os, re, time, requests
TEXT = ("Bir baba, kızını bir yılandan korumak için denizin ortasına kule yaptırdı. "
        "Ama sepetin dibinde bir yılan saklanıyordu! Peki gerçekten böyle mi oldu?")
os.makedirs("ses_ornek/out", exist_ok=True)
log = []
async def edge(name, voice, rate, pitch):
    c = edge_tts.Communicate(TEXT, voice, rate=rate, pitch=pitch)
    await c.save(f"ses_ornek/out/{name}.mp3")
K, S = os.environ.get("WIRO_API_KEY", ""), os.environ.get("WIRO_API_SECRET", "")
def hdr():
    n = str(int(time.time() * 1000)); sig = hmac.new(K.encode(), (S + n).encode(), hashlib.sha256).hexdigest()
    return {"Content-Type": "application/json", "x-api-key": K, "x-signature": sig, "x-nonce": n} if S else {"Content-Type": "application/json", "x-api-key": K}
URL_RE = re.compile(r'https?://[^\s"\'<>\\]+?\.(?:mp3|wav)', re.I)
VOICES = [("1_george", "JBFqnCBsd6RMkjVDRZzb"), ("2_bill", "pqHfZKP75CvOlQylNhV4"), ("3_brian", "nPczCjzI2devNBz1zQrb"),
          ("4_daniel", "onwK4e9ZLuTAKqWW03F9"), ("5_callum", "N2lVS1w4EtoT3dr4eOWO"), ("6_adam", "pNInz6obpgDQGcFmaJgB")]
for name, vid in VOICES:
    model = "eleven_v3"
    try:
        r = requests.post("https://api.wiro.ai/v1/Run/elevenlabs/text-to-speech/sync", headers=hdr(), timeout=240,
                          json={"prompt": TEXT, "model": model, "voice": vid, "outputFormat": "mp3_44100_128"})
        urls = URL_RE.findall(r.text)
        if not urls: log.append(f"{name} HATA yanit: {r.text[:300]}"); continue
        open(f"ses_ornek/out/{name}.mp3", "wb").write(requests.get(urls[0], timeout=120).content); log.append(name + " OK")
    except Exception as e: log.append(f"{name} HATA {e}")
open("ses_ornek/out/log.txt", "w").write("\n".join(log)); print("\n".join(log))
