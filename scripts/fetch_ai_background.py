"""
Zifiri Saatler - AI Arkaplan Uretici (Wiro) v3
Arkaplan kurgulanmis bir ZAMAN CIZELGESI (toplam <= ~35 sn):
  * Ilk 3 sn -> 3 AI GORSEL (1'er sn, Ken Burns)
  * Sonrasi  -> her 4 sn'de degisen, GERCEGE YAKIN klipler:
      her parca icin once doneme ozgu bir GORSEL uretilir (nano-banana),
      sonra o gorsel IMAGE-TO-VIDEO (runway gen4-turbo) ile canlandirilir.
Dusme sirasi (Pexels YOK):
  video canlandirma hata verirse -> AYNI gorsel Ken Burns ile kullanilir
  gorsel de hata verirse         -> koyu/atmosferik klip (son care)

Neden image-to-video: nis tarihi/atmosferik oldugu icin sahneyi bizim uretilen
gorsel sabitler; boylece hem gercekci hem niş-dogru (anakronik uydurma olmaz).

ENV:
  WIRO_API_KEY, WIRO_API_SECRET
  WIRO_IMAGE_MODEL         (varsayilan "google/nano-banana")
  WIRO_VIDEO_MODEL         (varsayilan "runway/image-to-video-gen4-turbo")
  WIRO_VIDEO_IMAGE_PARAM   (varsayilan "inputImage")  # image-to-video giris alani adi
  WIRO_BODY_MODE           "video" (varsayilan) | "image"
  WIRO_MAX_VIDEO_CLIPS     (varsayilan "15")   # maliyet tavani
  WIRO_WORKERS             (varsayilan "3")
  WIRO_MAX_SECONDS         (varsayilan "36")   # arkaplan ust sinir
"""
import os
import sys
import json
import time
import hmac
import hashlib
import re
import random
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
import requests

WIRO_API_KEY = os.environ.get("WIRO_API_KEY")
WIRO_API_SECRET = os.environ.get("WIRO_API_SECRET")
WIRO_IMAGE_MODEL = os.environ.get("WIRO_IMAGE_MODEL", "google/nano-banana")
WIRO_VIDEO_MODEL = os.environ.get("WIRO_VIDEO_MODEL", "runway/image-to-video-gen4-turbo")
WIRO_VIDEO_IMAGE_PARAM = os.environ.get("WIRO_VIDEO_IMAGE_PARAM", "inputImage")
WIRO_BODY_MODE = os.environ.get("WIRO_BODY_MODE", "video").lower()
MAX_VIDEO_CLIPS = int(os.environ.get("WIRO_MAX_VIDEO_CLIPS", "15"))
WORKERS = int(os.environ.get("WIRO_WORKERS", "3"))
MAX_SECONDS = float(os.environ.get("WIRO_MAX_SECONDS", "36"))

BASE_URL = "https://api.wiro.ai/v1"
WIDTH, HEIGHT, FPS = 1080, 1920, 30
INTRO_COUNT = 3
INTRO_SEC = 1
SEG_SEC = 4
REQ_TIMEOUT = 180

CATEGORY_SCENE = {
    "perili_kosk": "abandoned old ottoman mansion interior at night, single candle, dust",
    "lanetli_mekan": "misty old stone fountain and graveyard at night, moonlight",
    "kayip_yerlesim": "abandoned anatolian village, stone houses, fog, dusk",
    "yapinin_sirri": "ancient stone bridge and cistern, foggy mysterious atmosphere",
    "saray_golgesi": "grand but dark palace corridor, candlelight, long shadows",
    "anadolu_efsanesi": "foggy mountains and ancient stone ruins, anatolia, night",
    "karanlik_olay": "old manuscript and map on a dark table, candlelight",
}
STYLE_SUFFIX = (
    "cinematic, dark documentary style, moody dramatic lighting, fog, deep shadows, "
    "atmospheric, photorealistic, realistic, historically plausible, vertical 9:16 composition, "
    "no text, no watermark, no faces"
)
# Image-to-video icin: GERCEKCI, ince hareket - morph/warp olmadan
MOTION_PROMPT = (
    "slow subtle cinematic camera push-in, gentle drifting fog and candlelight flicker, "
    "realistic natural motion, cohesive, no morphing, no warping, no text"
)
MEDIA_URL_RE = re.compile(r'https?://[^\s"\'<>\\]+?\.(?:jpg|jpeg|png|webp|mp4|mov)', re.IGNORECASE)
MUSIC_FOLDER = "music"


# ---------- Wiro ----------
def _headers():
    if not WIRO_API_KEY:
        raise RuntimeError("WIRO_API_KEY yok")
    if WIRO_API_SECRET:
        nonce = str(int(time.time() * 1000))
        sig = hmac.new(WIRO_API_KEY.encode(), (WIRO_API_SECRET + nonce).encode(), hashlib.sha256).hexdigest()
        return {"Content-Type": "application/json", "x-api-key": WIRO_API_KEY, "x-signature": sig, "x-nonce": nonce}
    return {"Content-Type": "application/json", "x-api-key": WIRO_API_KEY}


def _find_media_urls(obj):
    found = []
    def walk(o):
        if isinstance(o, str):
            found.extend(MEDIA_URL_RE.findall(o))
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return found


def _run_sync(model_slug, body, timeout=REQ_TIMEOUT):
    r = requests.post(f"{BASE_URL}/Run/{model_slug}/sync", headers=_headers(), json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("result") is False:
        raise RuntimeError(f"Wiro hata: {data.get('errors')}")
    return data


def _download(url, out_path, timeout=120):
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def _wiro_image(prompt, out_jpg):
    """Gorsel uretir. (yerel_yol, public_url) doner - url image-to-video girisine verilir."""
    data = _run_sync(WIRO_IMAGE_MODEL, {"prompt": prompt})
    urls = [u for u in _find_media_urls(data) if not u.lower().endswith((".mp4", ".mov"))]
    if not urls:
        raise RuntimeError("gorsel URL yok")
    _download(urls[0], out_jpg)
    return out_jpg, urls[0]


def _wiro_video_from_image(image_url, out_mp4):
    """Bir gorseli image-to-video ile canlandirir (gerçekçi ince hareket)."""
    body = {WIRO_VIDEO_IMAGE_PARAM: image_url, "prompt": MOTION_PROMPT, "duration": SEG_SEC}
    data = _run_sync(WIRO_VIDEO_MODEL, body)
    urls = [u for u in _find_media_urls(data) if u.lower().endswith((".mp4", ".mov"))]
    if not urls:
        raise RuntimeError("video URL yok")
    _download(urls[0], out_mp4)
    return out_mp4


# ---------- ffmpeg ----------
def _ken_burns(image_path, out_path, seconds):
    frames = int(seconds * FPS)
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
        f"zoompan=z='min(zoom+0.0009,1.20)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"setsar=1,format=yuv420p"
    )
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(seconds),
                    "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an", out_path], check=True)


def _normalize_video(in_path, out_path, seconds):
    vf = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},"
          f"setsar=1,fps={FPS},format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-i", in_path, "-t", str(seconds), "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an", out_path], check=True)


def _solid_clip(out_path, seconds):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color=c=0x111014:s={WIDTH}x{HEIGHT}:r={FPS}:d={seconds}",
                    "-vf", "vignette=PI/5,format=yuv420p", "-t", str(seconds),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-an", out_path], check=True)


def _concat(clip_paths, out_path):
    list_path = "output/_concat.txt"
    with open(list_path, "w") as f:
        for c in clip_paths:
            f.write(f"file '{os.path.abspath(c)}'\n")
    try:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                        "-c", "copy", "-an", out_path], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an", out_path], check=True)


# ---------- timeline ----------
def _styled(p):
    return f"{p.strip()}. {STYLE_SUFFIX}"


def _base_prompts(story):
    prompts = [p for p in (story.get("scene_prompts") or []) if isinstance(p, str) and p.strip()]
    if not prompts:
        one = (story.get("image_prompt") or "").strip() or \
            CATEGORY_SCENE.get(story.get("_category", "karanlik_olay"), CATEGORY_SCENE["karanlik_olay"])
        prompts = [one]
    return prompts


def _make_segment(spec):
    """(idx, prompt, seconds, kind) -> (idx, clip). Once gorsel; video isteniyorsa canlandirir."""
    idx, prompt, seconds, kind = spec
    clip = f"output/seg_{idx:03d}.mp4"
    img = f"output/seg_{idx:03d}.jpg"

    # 1) her parca icin doneme ozgu gorseli uret (hem intro hem video-cipa)
    try:
        _, image_url = _wiro_image(prompt, img)
    except Exception as e:
        print(f"[{idx}] gorsel hata -> koyu klip: {e}", file=sys.stderr)
        _solid_clip(clip, seconds)
        return idx, clip

    # 2) video isteniyorsa gorseli GERCEKCI sekilde canlandir
    if kind == "video":
        try:
            raw = _wiro_video_from_image(image_url, f"output/seg_{idx:03d}_raw.mp4")
            _normalize_video(raw, clip, seconds)
            print(f"[{idx}] image-to-video OK")
            return idx, clip
        except Exception as e:
            print(f"[{idx}] video hata -> gorsel Ken Burns: {e}", file=sys.stderr)

    # 3) gorsel (intro veya video-fallback)
    _ken_burns(img, clip, seconds)
    print(f"[{idx}] gorsel OK")
    return idx, clip


def build_background(story, target, out_path="output/background.mp4"):
    target = min(target, MAX_SECONDS)
    prompts = _base_prompts(story)
    specs = []
    idx = 0
    for i in range(INTRO_COUNT):
        specs.append((idx, _styled(prompts[idx % len(prompts)]), INTRO_SEC, "image"))
        idx += 1
    covered = INTRO_COUNT * INTRO_SEC
    body_i = 0
    while covered < target:
        kind = "video" if (WIRO_BODY_MODE == "video" and body_i < MAX_VIDEO_CLIPS) else "image"
        specs.append((idx, _styled(prompts[idx % len(prompts)]), SEG_SEC, kind))
        idx += 1
        body_i += 1
        covered += SEG_SEC

    print(f"Toplam {len(specs)} parca ({INTRO_COUNT} intro gorsel + {len(specs)-INTRO_COUNT} govde), hedef {target:.1f}s")
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, WORKERS)) as ex:
        for i, clip in ex.map(_make_segment, specs):
            results[i] = clip
    _concat([results[s[0]] for s in specs], out_path)
    print(f"Arkaplan kurgulandi: {out_path}")


def pick_music(out="output/music.mp3"):
    if os.path.isdir(MUSIC_FOLDER):
        files = [f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith((".mp3", ".m4a", ".wav"))]
        if files:
            src = os.path.join(MUSIC_FOLDER, random.choice(files))
            shutil.copyfile(src, out)
            print(f"Muzik: {src}")
            return
    print("music/ bos - muziksiz devam.")


def _voice_duration():
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", "output/voice.mp3"],
                           capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    except Exception:
        return 32.0


def main():
    os.makedirs("output", exist_ok=True)
    story = {}
    if os.path.exists("output/story.json"):
        with open("output/story.json", "r", encoding="utf-8") as f:
            story = json.load(f)
    build_background(story, _voice_duration() + 0.5)
    pick_music()


if __name__ == "__main__":
    main()
