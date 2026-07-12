"""
Zifiri Saatler - Senaryo Uretici
Gemini API kullanarak kisa, atmosferik gizem/korku hikayeleri uretir.
"""
import os
import json
import random
import sys
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("HATA: GEMINI_API_KEY bulunamadi", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

THEMES = [
    "terk edilmis bir evde yasanan aciklanamayan olay",
    "kucuk bir kasabada nesilden nesile anlatilan sehir efsanesi",
    "cozulmemis esrarengiz bir kayip vakasi",
    "bir aile mirasindaki lanetli esya",
    "gece vardiyasinda calisan birinin basina gelen tuhaf olay",
    "eski bir fotografta ortaya cikan aciklanamayan detay",
    "bir ormanda kaybolan grubun basina gelenler",
    "apartmanda tekrar eden gizemli sesler",
    "bir mektupla ortaya cikan eski bir sir",
    "psikolojik olarak aciklanamayan dejavu deneyimi",
]

SYSTEM_PROMPT = """Sen Turkce icerik ureten bir senarist yapay zekasin. Gorevin YouTube Shorts icin
kisa (45-60 saniye seslendirmeye uygun, yaklasik 110-150 kelime), atmosferik, gizemli/urkutucu
hikayeler yazmak. Kurallar:
- Gercek, yasayan kisilerden veya spesifik gercek olaylardan bahsetme (kurgu/genel senaryo olsun)
- Ilk cumle GUCLU bir kanca olsun, izleyiciyi hemen icine ceksin
- Hikaye merak uyandirsin, sonunda hafif bir cliffhanger veya rahatsiz edici bir detay birak
- Duz, akici, seslendirmeye uygun Turkce yaz (kisa cumleler)
- Cikti SADECE JSON formatinda olsun, baska hicbir metin ekleme
- Kufur, asiri siddet, gercek kisi ismi kullanma

JSON formati:
{
  "title": "Youtube icin merak uyandiran vurucu kisa baslik (max 60 karakter)",
  "story": "Hikayenin tam metni (seslendirme icin)",
  "captions": ["Ekranda gorunecek kisa altyazi parcasi 1", "parca 2", "parca 3", "..."],
  "hashtags": ["#gizem", "#korku", "diger 5-7 alakali hashtag"]
}

captions alani, story metnini ekranda 4-8 kelimelik kisa parcalar halinde gostermek icin
bolunmus halidir - toplam story ile ayni anlami tasimali, kelime kelime kopya olabilir."""


def generate_story():
    theme = random.choice(THEMES)
    model = genai.GenerativeModel(
        "gemini-3.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    prompt = f"Tema: {theme}\n\nBu temaya uygun yeni ve ozgun bir hikaye uret."

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Markdown code fence temizligi
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    data = json.loads(text)
    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
