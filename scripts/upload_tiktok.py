"""Ayni videoyu TikTok'a da yollar (Upload-Post API). UPLOAD_POST_API_KEY yoksa sessizce atlar;
hata olursa YouTube yuklemesini bozmamak icin is akisini durdurmaz."""
import json
import os
import sys
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publish_time import next_publish_at

KEY = os.environ.get("UPLOAD_POST_API_KEY", "").strip()
USER = os.environ.get("UPLOAD_POST_USER", "") or "default".strip()
VIDEO = "output/final.mp4"


def caption(story):
    hook = (story.get("thumb_hook") or story.get("title") or "").strip()
    ep = f"Zifiri Dosya #{story['episode']} · " if story.get("episode") else ""
    tags = [t for t in story.get("hashtags", []) if t.startswith("#") and t.lower() != "#shorts"][:6]
    tags += ["#efsane", "#gizem", "#tarih", "#keşfet", "#fyp"]
    seen, uniq = set(), []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    text = f"{ep}{hook} 🕯️\n\nSenin memleketinde böyle bir efsane var mı? Yorumlara yaz 👇\n\n" + " ".join(uniq)
    return text[:2000]


def multipart(fields, file_field, path):
    b = uuid.uuid4().hex
    out = []
    for k, v in fields:
        out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"video.mp4\"\r\n"
               f"Content-Type: video/mp4\r\n\r\n".encode())
    out.append(open(path, "rb").read())
    out.append(f"\r\n--{b}--\r\n".encode())
    return b, b"".join(out)


def main():
    if not KEY:
        print("TikTok: UPLOAD_POST_API_KEY yok, atlandi.")
        return
    story = json.load(open("output/story.json", encoding="utf-8"))
    fields = [("user", USER), ("platform[]", "tiktok"), ("title", caption(story)),
              ("privacy_level", "PUBLIC_TO_EVERYONE"), ("is_aigc", "true"),
              ("cover_timestamp", "1300"), ("async_upload", "true")]
    pa = next_publish_at()
    if pa:  # YouTube ile ayni saatte yayina girsin
        fields.append(("scheduled_date", pa.strftime("%Y-%m-%dT%H:%M:%SZ")))
        fields = [f for f in fields if f[0] != "async_upload"]
        print("TikTok planlandi (UTC):", pa.isoformat())
    boundary, body = multipart(fields, "video", VIDEO)
    req = urllib.request.Request("https://api.upload-post.com/api/upload", data=body, method="POST", headers={
        "Authorization": f"Apikey {KEY}", "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Idempotency-Key": f"zifiri-{story.get('episode')}-{os.environ.get('GITHUB_RUN_ID', '')}"})
    try:
        res = json.load(urllib.request.urlopen(req, timeout=300))
        print("TikTok yanit:", json.dumps(res, ensure_ascii=False)[:500])
    except Exception as e:
        msg = getattr(e, "read", lambda: b"")().decode(errors="ignore")[:400]
        print(f"UYARI: TikTok yuklemesi basarisiz: {e} {msg}")


if __name__ == "__main__":
    main()
    sys.exit(0)
