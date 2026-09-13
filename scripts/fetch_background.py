"""
Zifiri Saatler - Arkaplan Video ve Muzik Cekici (v2: TARIH/EFSANE atmosferi)
Pexels'ten, hikaye kategorisine uygun TEK atmosferik (karanlik-belgesel)
arkaplan videosu indirir. Muzik, music/ klasorundeki telifsiz parcalardan secilir.
"""
import os
import random
import sys
import json
import requests

# NOT: bu modul artik fetch_ai_background tarafindan da import ediliyor.
# O yuzden anahtar kontrolu MODUL SEVIYESINDE degil, fetch_background()
# icinde yapilir - yoksa Pexels anahtari olmayan (sadece Wiro) kurulumda
# import aninda sys.exit ile pipeline coker.
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
HEADERS = {"Authorization": PEXELS_API_KEY or ""}

BG_HISTORY_PATH = "data/bg_history.json"
MAX_BG_HISTORY = 15

# _theme (generate_story kategorisinin bg anahtari) -> karanlik/belgesel
# atmosferli Pexels arama terimleri. Terimler Ingilizce (Pexels'te sonuc daha iyi).
THEME_TO_SEARCH = {
    "perili_kosk":     ["abandoned mansion night", "old dark mansion interior", "haunted house fog"],
    "lanetli_mekan":   ["foggy graveyard night", "eerie stone ruins", "dark old fountain"],
    "kayip_yerlesim":  ["abandoned village fog", "ghost town ruins", "empty old town night"],
    "yapinin_sirri":   ["ancient cistern water", "old stone bridge fog", "medieval tower night", "underground columns"],
    "saray_golgesi":   ["old palace corridor", "candlelit hall dark", "ornate dark interior"],
    "anadolu_efsanesi":["misty mountain landscape", "foggy forest night", "ancient stone ruins fog"],
    "karanlik_olay":   ["old manuscript candle", "vintage map dark", "foggy old street night"],
}

DEFAULT_TERMS = ["dark foggy ruins", "dark atmosphere fog"]

MUSIC_FOLDER = "music"


def fetch_music(output_path: str = "output/music.mp3"):
    if os.path.isdir(MUSIC_FOLDER):
        local_files = [
            f for f in os.listdir(MUSIC_FOLDER)
            if f.lower().endswith((".mp3", ".m4a", ".wav"))
        ]
        if local_files:
            chosen = random.choice(local_files)
            src = os.path.join(MUSIC_FOLDER, chosen)
            with open(src, "rb") as fsrc, open(output_path, "wb") as fdst:
                fdst.write(fsrc.read())
            print(f"Kendi muzik dosyan kullanildi: {chosen}")
            return
    print("music/ klasorunde dosya yok - video muziksiz (sadece seslendirme ile) devam ediyor.")


def _load_bg_history():
    if not os.path.exists(BG_HISTORY_PATH):
        return []
    try:
        with open(BG_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_bg_history(history, video_id):
    history.append(video_id)
    history = history[-MAX_BG_HISTORY:]
    os.makedirs(os.path.dirname(BG_HISTORY_PATH), exist_ok=True)
    with open(BG_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f)
    return history


def _download_pexels_video(term: str, output_path: str, avoid_ids=None):
    avoid_ids = avoid_ids or []
    url = "https://api.pexels.com/videos/search"
    params = {"query": term, "orientation": "portrait", "size": "medium", "per_page": 30}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        return False, None

    fresh_videos = [v for v in videos if v["id"] not in avoid_ids]
    pool = fresh_videos if fresh_videos else videos

    video = random.choice(pool)
    video_files = sorted(
        video["video_files"],
        key=lambda vf: abs((vf.get("height") or 0) - 1920),
    )
    best = video_files[0]

    video_resp = requests.get(best["link"], stream=True, timeout=60)
    video_resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in video_resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True, video["id"]


def fetch_background(theme: str, output_path: str = "output/background.mp4"):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY yok - Pexels yedegi kullanilamiyor")
    history = _load_bg_history()
    search_options = THEME_TO_SEARCH.get(theme, DEFAULT_TERMS)
    term = random.choice(search_options)

    ok, video_id = _download_pexels_video(term, output_path, avoid_ids=history)
    if not ok:
        for fallback in DEFAULT_TERMS:
            ok, video_id = _download_pexels_video(fallback, output_path, avoid_ids=history)
            if ok:
                term = fallback
                break

    if ok and video_id:
        _save_bg_history(history, video_id)
        print(f"Arkaplan indirildi ({term}): {output_path}")
    else:
        print("HATA: Arkaplan videosu hicbir terimle bulunamadi.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    theme = "karanlik_olay"
    if os.path.exists("output/story.json"):
        with open("output/story.json", "r", encoding="utf-8") as f:
            story = json.load(f)
        theme = story.get("_theme", theme)

    fetch_background(theme)
    fetch_music()
