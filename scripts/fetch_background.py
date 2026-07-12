"""
Zifiri Saatler - Arkaplan Video Cekici
Pexels API kullanarak telifsiz, hareketli arkaplan videolari ceker.
Her videoda farkli bir gorsel gelsin diye rastgele bir arama terimi secer.
"""
import os
import random
import sys
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    print("HATA: PEXELS_API_KEY bulunamadi", file=sys.stderr)
    sys.exit(1)

# Alt kisimda dönecek, dikkat cekici / hipnotik hareketli arkaplan aramalari
SEARCH_TERMS = [
    "parkour running",
    "abstract liquid motion",
    "neon tunnel drive",
    "forest walking pov",
    "city night drive",
    "sand dunes aerial",
    "waterfall slow motion",
    "train tunnel pov",
    "mountain hiking pov",
    "underwater diving",
]

HEADERS = {"Authorization": PEXELS_API_KEY}


def fetch_background(output_path: str = "output/background.mp4"):
    term = random.choice(SEARCH_TERMS)
    url = "https://api.pexels.com/videos/search"
    params = {
        "query": term,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 15,
    }
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    videos = data.get("videos", [])
    if not videos:
        raise RuntimeError(f"'{term}' icin video bulunamadi")

    video = random.choice(videos)
    # En uygun (dikey, orta boy) video dosyasini sec
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

    print(f"Arkaplan indirildi ({term}): {output_path}")
    return term


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    fetch_background()
