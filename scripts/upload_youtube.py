"""
Zifiri Saatler - YouTube Otomatik Yukleme
Refresh token kullanarak, insan onayi gerekmeden video yukler.
"""
import os
import json
import sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("HATA: YouTube kimlik bilgileri eksik", file=sys.stderr)
    sys.exit(1)


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

    hashtags = " ".join(story.get("hashtags", ["#gizem", "#korku", "#shorts"]))
    desc_summary = story.get("description", story["story"][:200])
    description = f"{desc_summary}\n\n{hashtags}\n\n#shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": [t.strip("#") for t in story.get("hashtags", [])],
            "categoryId": "24",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

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


def set_thumbnail(youtube, video_id: str, thumbnail_path: str):
    if not os.path.exists(thumbnail_path):
        print("Kapak dosyasi bulunamadi, atlaniyor.")
        return
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
    ).execute()
    print("Ozel kapak atandi.")


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    youtube = get_authenticated_service()
    video_id = upload_video(youtube, "output/final.mp4", story)

    try:
        set_thumbnail(youtube, video_id, "output/thumbnail.jpg")
    except Exception as e:
        print(f"Kapak atanamadi (video yine de yuklendi): {e}")
