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


def upload_video(video_path: str, story: dict):
    youtube = get_authenticated_service()

    title = story["title"]
    if len(title) > 95:
        title = title[:92] + "..."

    hashtags = " ".join(story.get("hashtags", ["#gizem", "#korku", "#shorts"]))
    description = f"{story['story'][:200]}...\n\n{hashtags}\n\n#shorts"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": [t.strip("#") for t in story.get("hashtags", [])],
            "categoryId": "24",  # Entertainment
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


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)
    upload_video("output/final.mp4", story)
