"""Yayin saati: run 1-2 saat once baslar, video hazir olunca hedef saate PLANLANIR.
PUBLISH_SLOTS (Istanbul saati, orn "12:30,19:30"). Hedef saat gectiyse (3 saate kadar) hemen yayinlanir."""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")


def next_publish_at(now=None):
    """Planlanacak UTC zamani doner; None = hemen yayinla."""
    raw = (os.environ.get("PUBLISH_SLOTS") or "12:30,19:30").strip()
    if raw.lower() in ("", "now", "hemen"):
        return None
    now = (now or datetime.now(timezone.utc)).astimezone(TZ)
    cands = []
    for day in (-1, 0, 1):
        for s in raw.split(","):
            h, m = (int(x) for x in s.strip().split(":"))
            cands.append((now + timedelta(days=day)).replace(hour=h, minute=m, second=0, microsecond=0))
    cands.sort()
    # 0) bir yayin saati az once (45 dk icinde) gectiyse ya da 10 dk'dan az kaldiysa: o videonun yerine hemen yayinla
    for slot in cands:
        if slot - timedelta(minutes=10) <= now <= slot + timedelta(minutes=45):
            return None
    # 1) onumuzdeki 3 saat icinde (en az 10 dk sonra) bir yayin saati varsa ona planla
    for slot in cands:
        if now + timedelta(minutes=10) <= slot <= now + timedelta(hours=3):
            return slot.astimezone(timezone.utc)
    # 2) yakinda yayin saati yok (elle calistirma vb.): hemen yayinla
    return None


if __name__ == "__main__":
    for t in ("10:25", "16:25", "19:25", "18:40", "21:45", "12:25", "03:00"):
        h, m = map(int, t.split(":"))
        n = datetime(2026, 11, 25, h, m, tzinfo=TZ)
        r = next_publish_at(n)
        print(t, "->", r.astimezone(TZ).strftime("%H:%M") if r else "hemen")
