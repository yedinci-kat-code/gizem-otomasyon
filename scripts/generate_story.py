"""
Zifiri Saatler - Senaryo Uretici
Gemini API kullanarak kisa, atmosferik gizem/korku hikayeleri uretir.
Tekrar etmemesi icin gecmis basliklari/temalari kontrol eder.
Performans analizine gore, "kisisel/miras kalan esya" temalari agirlikli.
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
AVOID_SAME_THEME_LAST_N = 3  # son 3 videoda kullanilan tema tekrar secilmesin

# Performans analizi: "kisisel/miras esya" temalari cok daha fazla izlenme aliyor
# (fotograf, saat, ayna, gunluk gibi herkesin evinde olabilecek nesneler).
# Bu yuzden bu gruba 3x agirlik veriyoruz, soyut/genel mekan temalarina 1x.
HIGH_PERFORMING_THEMES = [
    "bir aile mirasindaki lanetli esya (saat, ayna, kolye vb.)",
    "eski bir fotografta ortaya cikan aciklanamayan detay",
    "bir mektupla ortaya cikan eski bir sir",
    "dededen/anneanneden kalan gunluk ya da defterdeki gizemli notlar",
    "eski bir kutu icinde bulunan aciklanamayan esya",
    "bir aile yadigari saatin garip sekilde davranmasi",
]

STANDARD_THEMES = [
    "terk edilmis bir evde yasanan aciklanamayan olay",
    "kucuk bir kasabada nesilden nesile anlatilan sehir efsanesi",
    "cozulmemis esrarengiz bir kayip vakasi",
    "gece vardiyasinda calisan birinin basina gelen tuhaf olay",
    "bir ormanda kaybolan grubun basina gelenler",
    "apartmanda tekrar eden gizemli sesler",
    "psikolojik olarak aciklanamayan dejavu deneyimi",
]

# Agirlikli havuz: yuksek performansli temalar 3 kat daha sik secilsin
WEIGHTED_THEMES = (HIGH_PERFORMING_THEMES * 3) + STANDARD_THEMES

# Videonun sonunda ekranda gosterilecek, izleyiciyi etkilesime tesvik eden
# CTA (call-to-action) cumleleri - render_video.py bunlardan rastgele birini kullanir
CTA_PHRASES = [
    "Sence gerçekten ne oldu? Yorumlara yaz",
    "Bu sana da olduysa yorumla",
    "Devamını kaçırma, takip et",
    "Sen olsan ne yapardın? Yaz",
    "Benzer bir anın var mı? Anlat",
]

SYSTEM_PROMPT = """Sen Turkce icerik ureten, viral YouTube Shorts basliklari konusunda uzman bir
senarist yapay zekasin. Gorevin kisa (45-60 saniye seslendirmeye uygun, yaklasik 110-150 kelime),
atmosferik, gizemli/urkutucu hikayeler yazmak. Kurallar:

- Gercek, yasayan kisilerden veya spesifik gercek olaylardan bahsetme (kurgu/genel senaryo olsun)
- Ilk cumle GUCLU bir kanca olsun, izleyiciyi hemen icine ceksin
- Hikaye merak uyandirsin, sonunda hafif bir cliffhanger veya rahatsiz edici bir detay birak
- MUMKUNSE hikayeyi, izleyicinin kendi hayatiyla bag kurabilecegi somut, gunluk bir esya/nesne
  uzerinden anlat (fotograf, saat, mektup, defter, ayna gibi) - bu tarz hikayeler izleyicide
  "bende de var" hissi yaratip cok daha fazla izleniyor
- Duz, akici, seslendirmeye uygun Turkce yaz, KISA VE NET CUMLELER kullan (altyazida okunacak)
- Cikti SADECE JSON formatinda olsun, baska hicbir metin ekleme
- Kufur, asiri siddet, gercek kisi ismi kullanma
- Sana verilen "daha once kullanilan basliklar" listesindeki konularla AYNI veya
  cok benzer bir hikaye UYDURMA, tamamen ozgun ve farkli bir olay/detay/karakter kullan

BASLIK kurallari (cok onemli, tiklama oranini belirliyor):
- 60-90 karakter arasi, MERAK UYANDIRAN, yari aciklayan yari gizleyen bir baslik olsun
- Somut nesne + "sirri cozulemedi" / "hala aciklanamiyor" gibi merak tetikleyen kaliplar iyi calisiyor
- Ornek ton: "Dedesinden Kalan Saat Her Gece 03.17'de Duruyor, Sebebi Hala Bulunamadi"

ACIKLAMA (description) kurallari:
- 2-3 cumlelik, hikayeyi ozetleyen ama sonunu vermeyen, merak birakan bir aciklama yaz
- Izleyiciyi yorum yapmaya tesvik eden bir soru ile bitir

ETIKET (hashtags) kurallari:
- 8-12 arasi etiket uret: hem genel (#shorts #gizem #korku #viral) hem temaya ozel
  hem de kesfet/one cikma icin populer Turkce icerik etiketleri kullan

JSON formati:
{
  "title": "Merak uyandiran, 60-90 karakter arasi baslik",
  "description": "2-3 cumlelik ozet + soru ile bitsin",
  "story": "Hikayenin tam metni (seslendirme icin)",
  "hashtags": ["#gizem", "#korku", "... 8-12 arasi etiket"]
}"""


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Eski format (sadece string liste) ile uyumluluk
            normalized = []
            for item in data:
                if isinstance(item, str):
                    normalized.append({"title": item, "theme": None})
                else:
                    normalized.append(item)
            return normalized
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_history(history, new_title: str, new_theme: str):
    history.append({"title": new_title, "theme": new_theme})
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def pick_theme(history):
    recent_themes = [h["theme"] for h in history[-AVOID_SAME_THEME_LAST_N:] if h.get("theme")]
    candidates = [t for t in WEIGHTED_THEMES if t not in recent_themes]
    if not candidates:
        candidates = WEIGHTED_THEMES
    return random.choice(candidates)


def generate_story():
    history = load_history()
    theme = pick_theme(history)
    recent_titles = [h["title"] for h in history[-MAX_HISTORY_IN_PROMPT:]]

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
    data["_cta"] = random.choice(CTA_PHRASES)

    save_history(history, data["title"], theme)

    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
