"""
Zifiri Saatler - YouTube Otomatik Yukleme
Refresh token kullanarak, insan onayi gerekmeden video yukler.
"""
import os
import time
import json
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publish_time import next_publish_at

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("HATA: YouTube kimlik bilgileri eksik", file=sys.stderr)
    sys.exit(1)


def build_tags(story):
    """Once arama ifadeleri (bosluklu cumle etiketleri), sonra hashtag'ler; YouTube 500 karakter siniri."""
    out, seen, total = [], set(), 0
    items = [str(t).strip().lower() for t in story.get("arama_terimleri", []) or []]
    items += [t.strip("#") for t in story.get("hashtags", [])]
    for t in items:
        t = t.replace("<", "").replace(">", "").replace(",", " ").strip()
        if not t or t.lower() in seen:
            continue
        cost = len(t) + (2 if " " in t else 0) + 1
        if total + cost > 480:
            continue
        seen.add(t.lower()); out.append(t); total += cost
    return out


def get_authenticated_service():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: str, story: dict):
    title = story["title"]
    if len(title) > 95:
        title = title[:92] + "..."

    hashtags = " ".join(story.get("hashtags", ["#tarih", "#efsane", "#shorts"]))
    desc_summary = story.get("description", story["story"][:200])
    footer = (
        "Zifiri Saatler - Turk/Osmanli/Anadolu efsanelerinin ve karanlik tarihin "
        "'efsane mi, gercek mi' anlatimi. Anlatilanlar rivayet/efsane niteligindedir."
    )
    cta = story.get("_cta", "Sence efsane mi, gerçek mi? Yorumla")
    ep = f"🕯️ Zifiri Dosya #{story['episode']}\n\n" if story.get("episode") else ""
    description = f"{ep}{desc_summary}\n\n👉 {cta} | Sıradaki dosya için kanala abone ol.\n\n{footer}\n\n{hashtags}\n\n#shorts"

    privacy = (os.environ.get("YOUTUBE_PRIVACY") or "public").strip().lower()
    if privacy not in ("public", "unlisted", "private"):
        privacy = "public"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": build_tags(story),
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # YouTube'un YZ icerik beyani
        },
    }

    publish_at = next_publish_at() if privacy == "public" else None
    if publish_at:  # run erken basladi: video hazir, hedef saatte kendiliginden yayina girer
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        print("Planlandi, yayin zamani (UTC):", body["status"]["publishAt"])
        if os.environ.get("GITHUB_ENV"):
            with open(os.environ["GITHUB_ENV"], "a") as f:
                f.write(f"PUBLISH_AT_UTC={publish_at.isoformat()}\n")
    else:
        print("Hemen yayinlaniyor")

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Yukleniyor: %{int(status.progress() * 100)}")

    video_id = response["id"]
    print(f"Yuklendi: https://youtube.com/shorts/{video_id}")
    return video_id


def _small_jpeg(path: str) -> str:
    """YouTube kapak siniri 2 MB: gerekirse 720x1280'e kucultup kaliteyi dusurur."""
    if os.path.getsize(path) < 1_900_000:
        return path
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((720, 1280))
    out = os.path.splitext(path)[0] + "_yt.jpg"
    for q in (88, 80, 70, 60):
        im.save(out, quality=q, optimize=True)
        if os.path.getsize(out) < 1_900_000:
            break
    return out


def set_thumbnail(youtube, video_id: str, thumbnail_path: str):
    if not os.path.exists(thumbnail_path):
        print("::warning title=Kapak::Kapak dosyasi bulunamadi, atlandi.")
        return
    path = _small_jpeg(thumbnail_path)
    last = None
    for attempt in range(1, 5):  # yeni yuklenen video bazen henuz islenirken kapak reddedilir: bekleyip tekrar dene
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(path, mimetype="image/jpeg"),
            ).execute()
            print(f"::notice title=Kapak::Ozel kapak atandi ({video_id}, deneme {attempt})")
            return
        except Exception as e:
            last = e
            print(f"Kapak denemesi {attempt} basarisiz: {e}")
            time.sleep(30 * attempt)
    raise last


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    youtube = get_authenticated_service()
    video_id = upload_video(youtube, "output/final.mp4", story)
    print(f"::notice title=YouTube::video_id={video_id}")
    with open("output/video_id.txt", "w") as f:
        f.write(video_id)

    try:
        set_thumbnail(youtube, video_id, "output/thumbnail.jpg")
    except Exception as e:
        print(f"::warning title=Kapak::Kapak atanamadi (video yine de yuklendi): {str(e)[:300]}")
        print("IPUCU: Ozel kapak icin YouTube hesabin DOGRULANMIS olmali -> youtube.com/verify")
