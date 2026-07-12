"""
Zifiri Saatler - Senaryo Uretici
Gemini API kullanarak kisa, atmosferik gizem/korku hikayeleri uretir.
Tekrar etmemesi icin gecmis basliklari/temalari kontrol eder.
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

HISTORY_PATH = "data/history.json"
MAX_HISTORY_IN_PROMPT = 30

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

SYSTEM_PROMPT = """Sen Turkce icerik ureten, viral YouTube Shorts basliklari konusunda uzman bir
senarist yapay zekasin. Gorevin kisa (45-60 saniye seslendirmeye uygun, yaklasik 110-150 kelime),
atmosferik, gizemli/urkutucu hikayeler yazmak. Kurallar:

- Gercek, yasayan kisilerden veya spesifik gercek olaylardan bahsetme (kurgu/genel senaryo olsun)
- Ilk cumle GUCLU bir kanca olsun, izleyiciyi hemen icine ceksin
- Hikaye merak uyandirsin, sonunda hafif bir cliffhanger veya rahatsiz edici bir detay birak
- Duz, akici, seslendirmeye uygun Turkce yaz, KISA VE NET CUMLELER kullan (altyazida okunacak)
- Cikti SADECE JSON formatinda olsun, baska hicbir metin ekleme
- Kufur, asiri siddet, gercek kisi ismi kullanma
- Sana verilen "daha once kullanilan basliklar" listesindeki konularla AYNI veya
  cok benzer bir hikaye UYDURMA, tamamen ozgun ve farkli bir olay/detay/karakter kullan

BASLIK kurallari (cok onemli, tiklama oranini belirliyor):
- 60-90 karakter arasi, MERAK UYANDIRAN, yari aciklayan yari gizleyen bir baslik olsun
- Sayilar, "gercek", "kimse bilmiyor", "asla anlatilmadi" gibi merak tetikleyen ifadeler kullanabilirsin
- Ornek ton: "Bu Evde 3 Kisi Kayboldu, Sebebi Hala Cozulemedi" gibi carpici ama tik tuzagi (clickbait) sayilmayacak, hikayeyle dogrudan alakali olsun

ACIKLAMA (description) kurallari:
- 2-3 cumlelik, hikayeyi ozetleyen ama sonunu vermeyen, merak birakan bir aciklama yaz
- Izleyiciyi yorum yapmaya tesvik eden bir soru ile bitir (ornek: "Sizce gercekten ne oldu?")

ETIKET (hashtags) kurallari:
- 8-12 arasi etiket uret: hem genel (#shorts #gizem #korku #viral) hem temaya ozel
  (#şehirefsanesi #paranormal #gerçekhikaye vb.) hem de kesfet/one cikma icin populer
  Turkce icerik etiketleri kullan

JSON formati:
{
  "title": "Merak uyandiran, 60-90 karakter arasi baslik",
  "description": "2-3 cumlelik ozet + soru ile bitsin",
  "story": "Hikayenin tam metni (seslendirme icin)",
  "hashtags": ["#gizem", "#korku", "... 8-12 arasi etiket"],
  "theme_key": "Verilen temanin AYNEN kendisi (asagida gonderilen 'Tema:' degeri, degistirmeden)"
}"""


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_history(history, new_title: str):
    history.append(new_title)
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def generate_story():
    theme = random.choice(THEMES)
    history = load_history()
    recent_titles = history[-MAX_HISTORY_IN_PROMPT:]

    model = genai.GenerativeModel(
        "gemini-3.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    avoid_text = ""
    if recent_titles:
        avoid_text = (
            "\n\nDaha once kullanilan basliklar (bunlarla ayni/benzer konu UYDURMA):\n"
            + "\n".join(f"- {t}" for t in recent_titles)
        )

    prompt = f"Tema: {theme}\n\nBu temaya uygun yeni ve ozgun bir hikaye uret.{avoid_text}"

    response = model.generate_content(prompt)
    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    data = json.loads(text)
    data["_theme"] = theme

    save_history(history, data["title"])

    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
