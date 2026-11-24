"""
Zifiri Saatler - konuya ozel gorseller (Gemini gorsel modeli)
output/story.json -> landmark.backdrop / landmark.detail
  -> cizgi/work/bg_ozel.png  (9:16, gercek mekanin cizgi stil arka plani)
  -> cizgi/work/detail.png   (konunun objesi/ikonik detayi, yakin plan)

Basarisiz olursa video YINE uretilir: story.json'daki "ozel" mekanlar genel bir mekana,
"ozel" obje parsomene duser (yayin akisi asla durmaz).
"""
import base64
import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
WORK = os.path.join(ROOT, "cizgi", "work")
KEY = os.environ.get("GEMINI_API_KEY", "")
API = "https://generativelanguage.googleapis.com/v1beta"

STYLE = (
    "Flat 2D cartoon illustration in the style of a cute animated YouTube short: bold dark outlines, "
    "simple clean shapes, soft cel shading, slightly exaggerated proportions. Night scene under a bright "
    "full moon, deep navy and indigo sky with a few stars, warm golden accent lights. "
    "Absolutely NO people, NO characters, NO animals, NO text, NO letters, NO watermark, NO frame or border."
)


def pick_models():
    """Hesapta acik olan gorsel modellerini bulur (isimler zamanla degisiyor)."""
    pref = []
    try:
        r = requests.get(f"{API}/models", params={"key": KEY, "pageSize": 200}, timeout=30)
        for m in r.json().get("models", []):
            name = m.get("name", "").split("/")[-1]
            if "image" in name and "generateContent" in m.get("supportedGenerationMethods", []):
                pref.append(name)
    except Exception as e:
        print("model listesi alinamadi:", e)
    # flash once (hizli/ucuz), sonra pro; liste bossa bilinen isimler
    pref.sort(key=lambda n: (0 if "flash" in n else 1, "preview" in n, n))
    return pref or ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]


def gen_image(prompt, aspect, path, models):
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    for model in models:
        for attempt in range(2):
            try:
                r = requests.post(f"{API}/models/{model}:generateContent", params={"key": KEY}, json=body, timeout=180)
                if r.status_code != 200:
                    print(f"{model} hata {r.status_code}: {r.text[:200]}")
                    break
                for cand in r.json().get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
                        if data:
                            open(path, "wb").write(base64.b64decode(data))
                            print(f"gorsel hazir ({model}): {os.path.basename(path)}")
                            return True
                print(f"{model}: yanitta gorsel yok")
            except Exception as e:
                print(f"{model} deneme {attempt + 1} basarisiz: {e}")
                time.sleep(5)
    return False


def main():
    path = os.path.join(OUT, "story.json")
    story = json.load(open(path, encoding="utf-8"))
    lm = story.get("landmark") or {}
    os.makedirs(WORK, exist_ok=True)
    for f in ("bg_ozel.png", "detail.png", "hook.png"):
        if os.path.exists(os.path.join(WORK, f)):
            os.remove(os.path.join(WORK, f))
    ok_bg = ok_det = False
    if KEY and lm.get("backdrop"):
        models = pick_models()
        print("gorsel modelleri:", models[:4])
        place = story.get("topic") or story.get("place") or ""
        ok_bg = gen_image(
            f"{lm['backdrop']} ({place}). Vertical 9:16 composition, eye-level view from the ground, the landmark "
            f"large and recognizable in the middle and upper part, flat open empty ground across the bottom third. {STYLE}",
            "9:16", os.path.join(WORK, "bg_ozel.png"), models)
        if lm.get("detail"):
            ok_det = gen_image(
                f"{lm['detail']} ({place}). Centered close-up, the subject fills most of the frame, plain dark "
                f"vignette background. {STYLE}", "1:1", os.path.join(WORK, "detail.png"), models)
        # acilis karesi: efsanenin en carpici olaganustu ani (yaratik/lanet/mucize) - kapak da bundan cikar
        if lm.get("hook"):
            gen_image(
                f"{lm['hook']} ({place}). Vertical 9:16, cinematic dramatic composition, the supernatural subject large "
                f"in the middle and upper part of the frame, strong moonlight rim light, a little mist. "
                + STYLE.replace("Absolutely NO people, NO characters, NO animals, ", "Cartoon figures and creatures are allowed but NO ")
                , "9:16", os.path.join(WORK, "hook.png"), models)
    # dusme kurallari: gorsel yoksa ozel mekan/obje genel karsiliklarina doner
    changed = False
    for b in story.get("beats", []):
        if b.get("loc") == "ozel" and not ok_bg:
            b["loc"] = "kosk_dis"
            changed = True
        if b.get("shot") == "obje" and b.get("obj") == "ozel" and not ok_det:
            b["obj"] = "parsomen"
            changed = True
    if changed:
        json.dump(story, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("UYARI: ozel gorsel uretilemedi, genel mekana/parsomene dusuldu")
    print(f"arka plan: {'var' if ok_bg else 'yok'} | detay: {'var' if ok_det else 'yok'}")


if __name__ == "__main__":
    sys.exit(main())
