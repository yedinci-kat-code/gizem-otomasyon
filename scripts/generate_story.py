"""
Zifiri Saatler - Senaryo Uretici
Gemini API kullanarak kisa, atmosferik gizem/korku hikayeleri uretir.
Performans analizine gore: "kisisel esya + IMKANSIZ/MANTIKSIZ detay" kalibi
en yuksek izlenme suresini (bazen %150+ - tekrar izletme) aliyor.
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
AVOID_SAME_THEME_LAST_N = 3
AVOID_SAME_CITY_LAST_N = 5

# Hikayeye "gercekci hissettirme" katmak icin kullanilan Turkiye sehir/bolge
# havuzu. GUVENLIK: sadece sehir/bolge adi kullanilir, GERCEK adres, isletme,
# kurum veya kisi ismi ASLA kullanilmaz (prompt'ta ayrica vurgulanir).
CITIES = [
    "Bursa", "Kayseri", "Trabzon", "Mersin", "Konya", "Eskişehir",
    "Antalya", "Adana", "Samsun", "Gaziantep", "Malatya", "Erzurum",
    "Denizli", "Sivas", "Van", "Diyarbakır", "Kastamonu", "Rize",
]

# Performans analizi (16 Temmuz 2026): en yuksek izlenme suresi/tekrar izletme
# "kisisel esya + FIZIKSEL OLARAK IMKANSIZ/MANTIKSIZ bir detay" kalibinda
# cikiyor (ornek: aynadaki yansimanin kisiden ONCE hareket etmesi -> %151.8
# izlenme suresi, yani izleyiciler videoyu birden fazla kez izlemis).
# Soyut/psikolojik temalar (dejavu gibi) en dusuk performansi verdi (%16.6),
# bu yuzden havuzdan tamamen cikarildi.
HIGH_PERFORMING_THEMES = [
    "bir aynadaki yansimanin kisiden once hareket etmesi gibi imkansiz bir detay",
    "eski bir fotografta, cekildigi anda orada olmamasi gereken bir seyin gorunmesi",
    "bir saatin fiziksel olarak imkansiz bir sekilde geri gitmesi ya da durmasi",
    "bir mektup/gunlukteki yazinin, yazildigi tarihe gore imkansiz bilgiler icermesi",
    "kalitsal bir esyanin, sahibiyle ayni hareketleri es zamanli tekrarlamasi",
    "eski bir kutu/sandiktaki esyanin zamanla degistigi ama kimsenin dokunmadigi",
]

STANDARD_THEMES = [
    "terk edilmis bir evde yasanan aciklanamayan olay",
    "kucuk bir kasabada nesilden nesile anlatilan sehir efsanesi",
    "cozulmemis esrarengiz bir kayip vakasi",
    "gece vardiyasinda calisan birinin basina gelen tuhaf olay",
    "bir ormanda kaybolan grubun basina gelenler",
    "apartmanda tekrar eden gizemli sesler",
]

WEIGHTED_THEMES = (HIGH_PERFORMING_THEMES * 3) + STANDARD_THEMES

CTA_PHRASES = [
    "Sence gerçekten ne oldu? Yorumlara yaz",
    "Bu sana da olduysa yorumla",
    "Devamını kaçırma, takip et",
    "Sen olsan ne yapardın? Yaz",
    "Benzer bir anın var mı? Anlat",
]

# Turkce gizem/korku niginde her zaman yuksek aranan, evrensel gecerlilikte
# anahtar kelimeler - her videoda otomatik karisir, arama/kesfette bulunma
# sansini artirir
SEO_KEYWORDS = [
    "gerçek hikaye", "gerçek olay", "esrarengiz olaylar", "çözülemeyen gizem",
    "paranormal olaylar", "şehir efsanesi", "tüyler ürpertici",
    "açıklanamayan olaylar", "gerçek yaşanmış", "korkunç gerçek",
    "gizemli olaylar", "korku hikayesi", "gerçek korku", "esrarengiz olay",
    "sırrı çözülemedi", "kaybolan insanlar", "tüyler ürperten hikaye",
    "gece hikayeleri", "ürkütücü olaylar", "açıklanamayan gizem",
    "gerçek dehşet", "gizem dolu", "korku anıları", "inanılmaz gerçek olay",
]

SYSTEM_PROMPT = """Sen Turkce icerik ureten, viral YouTube Shorts basliklari konusunda uzman bir
senarist yapay zekasin. Gorevin kisa (45-60 saniye seslendirmeye uygun, yaklasik 110-150 kelime),
atmosferik, gizemli/urkutucu hikayeler yazmak. Kurallar:

- Gercek, yasayan kisilerden veya spesifik gercek olaylardan bahsetme (kurgu/genel senaryo olsun)
- Ilk cumle GUCLU bir kanca olsun, izleyiciyi hemen icine ceksin
- COK ONEMLI: Hikayenin merkezinde, somut bir esya/nesne uzerinde FIZIKSEL OLARAK IMKANSIZ
  veya MANTIKSIZ bir detay olsun (ornek: yansimanin kisiden once hareket etmesi, saatin
  imkansiz sekilde davranmasi, fotografta olmamasi gereken bir seyin gorunmesi). Bu tarz
  "imkansiz detay" iceren hikayeler izleyicinin videoyu tekrar tekrar izlemesini sagliyor
  (analiz verisi: %150+ izlenme suresi elde edildi), bu yuzden mutlaka bu kalibi kullan
- Hikaye merak uyandirsin, sonunda hafif bir cliffhanger veya rahatsiz edici bir detay birak
- Duz, akici, seslendirmeye uygun Turkce yaz, KISA VE NET CUMLELER kullan (altyazida okunacak)
- Cikti SADECE JSON formatinda olsun, baska hicbir metin ekleme
- Kufur, asiri siddet, gercek kisi ismi kullanma
- Sana verilen "daha once kullanilan basliklar" listesindeki konularla AYNI veya
  cok benzer bir hikaye UYDURMA, tamamen ozgun ve farkli bir olay/detay/karakter kullan
- Sana verilen SEHIR adini hikayeye dogal bir sekilde yedir (ornek: "Kayseri'nin eski
  bir mahallesinde", "Trabzon'da bir sahil kasabasinda"). COK ONEMLI GUVENLIK KURALI:
  SADECE genel sehir/bolge/mahalle duzeyinde kal - GERCEK bir adres, sokak ismi,
  isletme adi, kurum adi (okul, hastane, cami vb. spesifik isimlerle) veya gercek
  bir kisi ismi ASLA kullanma. Amac hikayeyi "bir yerde geciyormus gibi" hissettirmek,
  dogrulanabilir/iddia edilebilir gercek bir yer/kurum/kisi ile iliskilendirmek DEGIL.

BASLIK kurallari (cok onemli, tiklama oranini belirliyor):
- 60-90 karakter arasi, MERAK UYANDIRAN, yari aciklayan yari gizleyen bir baslik olsun
- Somut nesne + imkansiz detay + "sirri cozulemedi" gibi kaliplar en iyi calisiyor
- Ornek ton: "Aynadaki Yansiması Ondan Önce Hareket Etti, Sırrı Hâlâ Çözülemedi"
- Mumkunse, dogal bir sekilde su anahtar kelimelerden BIRINI baslik veya aciklamaya
  entegre et (zorla sokusturma, sadece uyuyorsa kullan): gerçek hikaye, gerçek olay,
  esrarengiz olaylar, çözülemeyen gizem, tüyler ürpertici

ACIKLAMA (description) kurallari:
- 2-3 cumlelik, hikayeyi ozetleyen ama sonunu vermeyen, merak birakan bir aciklama yaz
- Izleyiciyi yorum yapmaya tesvik eden bir soru ile bitir

ETIKET (hashtags) kurallari:
- 10-12 arasi TEMAYA OZEL etiket uret (genel/SEO etiketleri ayrica otomatik eklenecek,
  onlari sen tekrar yazma)

JSON formati:
{
  "title": "Merak uyandiran, 60-90 karakter arasi baslik",
  "description": "2-3 cumlelik ozet + soru ile bitsin",
  "story": "Hikayenin tam metni (seslendirme icin)",
  "hashtags": ["#temaya-ozel-etiket1", "#etiket2", "... 10-12 arasi"]
}"""


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            normalized = []
            for item in data:
                if isinstance(item, str):
                    normalized.append({"title": item, "theme": None})
                else:
                    normalized.append(item)
            return normalized
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_history(history, new_title: str, new_theme: str, new_city: str):
    history.append({"title": new_title, "theme": new_theme, "city": new_city})
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def pick_theme(history):
    recent_themes = [h["theme"] for h in history[-AVOID_SAME_THEME_LAST_N:] if h.get("theme")]
    candidates = [t for t in WEIGHTED_THEMES if t not in recent_themes]
    if not candidates:
        candidates = WEIGHTED_THEMES
    return random.choice(candidates)


def pick_city(history):
    recent_cities = [h.get("city") for h in history[-AVOID_SAME_CITY_LAST_N:] if h.get("city")]
    candidates = [c for c in CITIES if c not in recent_cities]
    if not candidates:
        candidates = CITIES
    return random.choice(candidates)


def merge_seo_keywords(hashtags):
    """SEO havuzundan daha genis bir kismini secip mevcut etiketlere ekler,
    tekrarlari temizler. YouTube'un toplam etiket karakter limitini (500)
    asmamak icin guvenli bir sinirda tutar."""
    picked = random.sample(SEO_KEYWORDS, k=min(12, len(SEO_KEYWORDS)))
    seo_tags = ["#" + k.replace(" ", "") for k in picked]
    combined = list(dict.fromkeys(hashtags + seo_tags + ["#shorts", "#keşfet"]))

    # YouTube toplam etiket karakter limiti ~500 - guvenli tarafta kalmak
    # icin 480 karaktere kadar ekle, 30 etiketi de gecme
    result = []
    total_chars = 0
    for tag in combined:
        if len(result) >= 30:
            break
        tag_len = len(tag.strip("#")) + 1  # virgul icin +1
        if total_chars + tag_len > 480:
            break
        result.append(tag)
        total_chars += tag_len

    return result


def generate_story():
    history = load_history()
    theme = pick_theme(history)
    city = pick_city(history)
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

    prompt = (
        f"Tema: {theme}\n"
        f"Sehir: {city}\n\n"
        f"Bu temaya uygun, {city} sehrinde/bolgesinde gecen yeni ve ozgun bir hikaye uret. "
        f"Sadece genel bir mahalle/bolge atfet, gercek adres/kurum/kisi ismi kullanma."
        f"{avoid_text}"
    )

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
    data["hashtags"] = merge_seo_keywords(data.get("hashtags", []))

    save_history(history, data["title"], theme, city)

    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
