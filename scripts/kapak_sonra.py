"""Planli videolarda YouTube, yayin aninda Shorts kapagini videodan bir kareyle eziyor.
Yayin saatinden 1 dakika sonra ozel kapagi tekrar atar."""
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upload_youtube as u
from publish_time import next_publish_at

if not os.path.exists("output/video_id.txt"):
    print("video_id yok, atlandi"); sys.exit(0)
vid = open("output/video_id.txt").read().strip()
pa = os.environ.get("PUBLISH_AT_UTC")
if pa:
    wait = (datetime.fromisoformat(pa) - datetime.now(timezone.utc)).total_seconds() + 60
    if 0 < wait < 4 * 3600:
        print(f"Yayin saatine kadar {int(wait)} sn bekleniyor")
        time.sleep(wait)
try:
    u.set_thumbnail(u.get_authenticated_service(), vid, "output/thumbnail.jpg")
except Exception as e:
    print(f"::warning title=Kapak (yayin sonrasi)::{str(e)[:300]}")
