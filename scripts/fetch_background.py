"""
Zifiri Saatler - Arkaplan Video ve Muzik Cekici
TEK PANEL: Pexels API'den, hikayenin konusuyla ilgili TEK bir atmosferik
arkaplan videosu indirir (artik ust/alt panel ayrimi yok).
Pixabay Audio yerine, senin music/ klasorune ekledigin telifsiz muzikler
kullanilir.
"""
import os
import random
import sys
import json
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    print("HATA: PEXELS_API_KEY bulunamadi", file=sys.stderr)
    sys.exit(1)

HEADERS = {"Authorization": PEXELS_API_KEY}

BG_HISTORY_PATH = "data/bg_history.json"
MAX_BG_HISTORY = 15  # son 15 video ID'sini hatirla, tekrarindan kacin

# Hikaye temasina gore uygun, atmosferik arama terimleri. Tek panel oldugu
# icin arkaplan artik SADECE bu tema-bazli havuzdan seciliyor - "hipnotik/
# oyun tarzi" soyut arkaplan havuzu (eski BOTTOM_SEARCH_TERMS) kaldirildi,
# cunku artik ekranin tamamini kapladigi icin hikayeyle alakasiz bir gorsel
# (parkur, lav lambasi vb.) yaninda konusan bir video garip kacardi.
THEME_TO_SEARCH = {
    "terk edilmis bir evde yasanan aciklanamayan olay": ["abandoned house interior", "old dark hallway"],
    "kucuk bir kasabada nesilden nesile anlatilan sehir efsanesi": ["foggy small town night", "empty street fog"],
    "cozulmemis esrarengiz bir kayip vakasi": ["dark forest night", "flashlight search night"],
    "bir aile mirasindaki lanetli esya": ["antique attic dark", "old photograph dust"],
    "gece vardiyasinda calisan birinin basina gelen tuhaf olay": ["empty office night", "hospital corridor night"],
    "eski bir fotografta ortaya cikan aciklanamayan detay": ["vintage photo album", "old film grain"],
    "bir ormanda kaybolan grubun basina gelenler": ["dark forest fog", "night camping forest"],
    "apartmanda tekrar eden gizemli sesler": ["dark apartment hallway", "empty stairwell"],
    "bir mektupla ortaya cikan eski bir sir": ["old letter candle", "vintage desk night"],
    "psikolojik olarak aciklanamayan dejavu deneyimi": ["abstract dark clouds", "mirror reflection dark"],
}

MUSIC_FOLDER = "music"


def fetch_music(output_path: str = "output/music.mp3"):
    # SADECE senin music/ klasorune ekledigin, kendi sectigin (telif sorunu olmayan)
    # muzikleri kullanir. Hicbir "yedek/rastgele internet" muzigi KULLANILMAZ -
    # bir onceki telif sorunundan sonra bu guvenlik onlemi bilerek eklendi.
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

    # Once daha once kullanilmamis videolari dene, hepsi kullanilmissa herhangi birini sec
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
    """
    TEK panel icin, hikaye temasina uygun tek bir arkaplan videosu indirir.
    Once o temanin arama terimlerinden birini dener, video hic bulunamazsa
    genel "dark atmosphere fog" terimine duser.
    """
    history = _load_bg_history()
    search_options = THEME_TO_SEARCH.get(theme, ["dark atmosphere fog"])
    term = random.choice(search_options)

    ok, video_id = _download_pexels_video(term, output_path, avoid_ids=history)
    if not ok:
        term = "dark atmosphere fog"
        ok, video_id = _download_pexels_video(term, output_path, avoid_ids=history)

    if ok and video_id:
        _save_bg_history(history, video_id)
        print(f"Arkaplan indirildi ({term}): {output_path}")
    else:
        print("HATA: Arkaplan videosu hicbir terimle bulunamadi.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    theme = "dark atmosphere fog"
    if os.path.exists("output/story.json"):
        with open("output/story.json", "r", encoding="utf-8") as f:
            story = json.load(f)
        theme = story.get("_theme", theme)

    fetch_background(theme)
    fetch_music()
