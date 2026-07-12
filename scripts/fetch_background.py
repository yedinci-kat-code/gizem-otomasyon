"""
Zifiri Saatler - Arkaplan Video ve Muzik Cekici
Pexels API kullanarak:
  - ALT panel icin: hareketli/hipnotik "oyun tarzi" arkaplan videosu
  - UST panel icin: hikayenin konusuyla ilgili atmosferik video
Pixabay Audio (API-key gerektirmez, dogrudan indirilebilir mp3'ler) ile
telifsiz gerilim/ambiyans muzigi indirir.
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

# ALT panel: dikkat cekici, hipnotik hareketli arkaplanlar (oyun-tarzi izlenim)
BOTTOM_SEARCH_TERMS = [
    "parkour running",
    "abstract liquid motion",
    "neon tunnel drive",
    "sand dunes aerial",
    "waterfall slow motion",
    "train tunnel pov",
    "underwater diving",
    "city night drive",
]

# UST panel icin, hikaye temasina gore uygun arama terimleri
THEME_TO_TOP_SEARCH = {
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

# Ucretsiz, dogrudan indirilebilir (API key gerektirmeyen) ambiyans/gerilim muzikleri
# Pixabay'in acik CDN linkleri - telifsiz, ticari kullanima uygun
MUSIC_URLS = [
    "https://cdn.pixabay.com/download/audio/2022/03/10/audio_c8e70c5fdc.mp3",
    "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
    "https://cdn.pixabay.com/download/audio/2021/11/25/audio_00fa5b4a68.mp3",
]


def _download_pexels_video(term: str, output_path: str):
    url = "https://api.pexels.com/videos/search"
    params = {"query": term, "orientation": "portrait", "size": "medium", "per_page": 15}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos:
        return False

    video = random.choice(videos)
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
    return True


def fetch_bottom_background(output_path: str = "output/background.mp4"):
    term = random.choice(BOTTOM_SEARCH_TERMS)
    ok = _download_pexels_video(term, output_path)
    if not ok:
        # Yedek terim dene
        ok = _download_pexels_video("abstract motion", output_path)
    print(f"Alt panel arkaplani indirildi ({term}): {output_path}")


def fetch_top_background(theme: str, output_path: str = "output/top_background.mp4"):
    search_options = THEME_TO_TOP_SEARCH.get(theme, ["dark atmosphere fog"])
    term = random.choice(search_options)
    ok = _download_pexels_video(term, output_path)
    if not ok:
        ok = _download_pexels_video("dark atmosphere fog", output_path)
    if ok:
        print(f"Ust panel arkaplani indirildi ({term}): {output_path}")
    else:
        print("Ust panel arkaplani bulunamadi, duz renk kullanilacak.")


def fetch_music(output_path: str = "output/music.mp3"):
    url = random.choice(MUSIC_URLS)
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Arkaplan muzigi indirildi: {output_path}")
    except Exception as e:
        print(f"Muzik indirilemedi, muziksiz devam edilecek: {e}")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    theme = "dark atmosphere fog"
    if os.path.exists("output/story.json"):
        with open("output/story.json", "r", encoding="utf-8") as f:
            story = json.load(f)
        theme = story.get("_theme", theme)

    fetch_bottom_background()
    fetch_top_background(theme)
    fetch_music()
