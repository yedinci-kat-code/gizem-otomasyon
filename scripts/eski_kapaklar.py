"""Eski videolara yeni tarz kapak: konuya ozel carpici cizgi gorsel (Gemini) + ust kisimda Zifiri basligi.
scripts/eski_kapaklar.json listesindeki her video icin uretir ve YouTube'a atar."""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_backdrops as gb  # noqa: E402

FONT = os.path.join(os.path.dirname(__file__), "..", "cizgi", "fonts", "Nunito.ttf")


def font(size):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name("Black")
    except Exception:
        try:
            f.set_variation_by_axes([900])
        except Exception:
            pass
    return f


def draw_title(img, text):
    w, h = img.size
    k = w / 1080
    d = ImageDraw.Draw(img)
    words = text.replace("i", "İ").replace("ı", "I").upper().split()  # Turkce buyuk harf
    size = int(96 * k)
    while True:
        f = font(size)
        lines, cur = [], ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if d.textlength(t, font=f) > 900 * k and cur:
                lines.append(cur); cur = wd
            else:
                cur = t
        if cur:
            lines.append(cur)
        if len(lines) <= 3 or size <= 60 * k:
            break
        size -= int(6 * k)
    lh = size * 1.08
    y0 = 0.21 * h - len(lines) * lh / 2
    for i, ln in enumerate(lines):
        col = "#ffcf3a" if i == len(lines) - 1 else "#ffffff"
        d.text((w / 2, y0 + i * lh), ln, font=f, fill=col, anchor="ma", stroke_width=int(9 * k), stroke_fill="#0b0d1e")
    return img


def main():
    items = json.load(open(os.path.join(os.path.dirname(__file__), "eski_kapaklar.json"), encoding="utf-8"))
    only = os.environ.get("ONLY", "").strip()
    models = gb.pick_models()
    os.makedirs("output/eski", exist_ok=True)
    import upload_youtube as u
    yt = None if os.environ.get("DRY") else u.get_authenticated_service()
    for it in items:
        if only and it["video_id"] not in only.split(","):
            continue
        raw = f"output/eski/{it['video_id']}_raw.png"
        prompt = (f"{it['scene']}. Vertical 9:16, cinematic dramatic composition, the supernatural subject large in the "
                  f"middle and lower part, leave the top quarter calmer (dark sky) for a title, strong moonlight rim light, a little mist. "
                  + gb.STYLE.replace("Absolutely NO people, NO characters, NO animals, ", "Cartoon figures and creatures are allowed but NO "))
        if not gb.gen_image(prompt, "9:16", raw, models):
            print(f"::warning title=Kapak::{it['video_id']} gorsel uretilemedi"); continue
        img = Image.open(raw).convert("RGB").resize((1080, 1920), Image.LANCZOS)
        out = f"output/eski/{it['video_id']}.jpg"
        draw_title(img, it["text"]).save(out, quality=90)
        if yt:
            try:
                u.set_thumbnail(yt, it["video_id"], out)
            except Exception as e:
                print(f"::warning title=Kapak::{it['video_id']}: {str(e)[:200]}")


if __name__ == "__main__":
    main()
