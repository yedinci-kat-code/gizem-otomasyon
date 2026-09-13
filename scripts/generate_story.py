"""
Zifiri Saatler - Senaryo Uretici (v2: EFSANE -> GERCEK)
Nis: Turk/Osmanli/Anadolu efsaneleri, perili mekanlar, karanlik tarihi olaylar.
Her video bir efsaneyi/karanlik olayi ALIR, atmosferik anlatir ve SONUNDA
muhtemel GERCEK/tarihsel aciklamaya baglar ("efsane mi, gercek mi").
Kitap referansi: 2. sahis daldirma, merak acigi, loop kapanisi, Bolum 6 baslik
formulleri, kaynak-uydurmama kirmizi cizgisi.
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
AVOID_SAME_CATEGORY_LAST_N = 3

# Her kategori: bir icerik lane'i (cesitlilik icin donusumlu secilir) + arkaplan
# gorsel anahtari (_theme olarak fetch_background.py'deki THEME_TO_SEARCH ile
# birebir eslesir). Hepsi YAYGIN BILINEN efsane/olay turleri - bu, modelin
# obscure bir sey "uydurma" riskini dusurur.
CATEGORIES = [
    {"key": "perili_kosk",
     "hint": "unlu bir PERILI KOSK / terk edilmis konak efsanesi (eski kosker, yalilar). "
             "Anlatilan hayalet/ugursuzluk rivayeti + yapinin bilinen gercek tarihi.",
     "bg": "perili_kosk"},
    {"key": "lanetli_mekan",
     "hint": "'ugursuz/lanetli' sayilan bir mekan (cesme, mezarlik, han, kuyu) efsanesi + "
             "arkasindaki muhtemel gercek tarihsel/sosyal sebep.",
     "bg": "lanetli_mekan"},
    {"key": "kayip_yerlesim",
     "hint": "terk edilmis/bosaltilmis bir koy ya da kasaba efsanesi (neden bosaldigina dair "
             "rivayetler) + gercek tarihsel/cografi neden.",
     "bg": "kayip_yerlesim"},
    {"key": "yapinin_sirri",
     "hint": "eski bir yapiyla (kopru, kule, sarnic, kale, tunel) ilgili efsane + yapinin "
             "gercek insa/isleyis hikayesi.",
     "bg": "yapinin_sirri"},
    {"key": "saray_golgesi",
     "hint": "Osmanli sarayi/cevresinde anlatilan karanlik bir rivayet (bir odanin, bir "
             "esyanin, bir gelenegin sirri) + bilinen genel tarihsel baglam.",
     "bg": "saray_golgesi"},
    {"key": "anadolu_efsanesi",
     "hint": "Anadolu'da nesilden nesile anlatilan bir halk efsanesi (bir dag, gol, magara, "
             "tas, agac) + efsanenin muhtemel gercek kokeni.",
     "bg": "anadolu_efsanesi"},
    {"key": "karanlik_olay",
     "hint": "tarihte gercekten yasanmis, az bilinen, tuyler urpertici bir olay/gizem - "
             "abartisiz, 'efsanelesmis' yani + bilinen gercek cerceve.",
     "bg": "karanlik_olay"},
]

CTA_PHRASES = [
    "Sence efsane mi, gerçek mi? Yorumla",
    "Bu efsaneyi duydun mu? Yaz",
    "Gerçeğini biliyor musun? Yorumla",
    "Sıradaki dosya için takip et",
    "Sen olsan girer miydin? Yaz",
]

# Nise ozel, aramada/kesfette yuksek gecerlilikli anahtar kelimeler (otomatik karisir)
SEO_KEYWORDS = [
    "gerçek hikaye", "tarihin karanlık yüzü", "osmanlı gizemi", "anadolu efsanesi",
    "efsane mi gerçek mi", "tarihi gizem", "bilinmeyen tarih", "gerçek olay",
    "şehir efsanesi", "perili köşk", "lanetli", "tüyler ürpertici",
    "karanlık tarih", "gizemli olaylar", "tarihi sır", "unutulmuş tarih",
]

SYSTEM_PROMPT = """Sen Turkce icerik ureten, atmosferik TARIH & EFSANE anlatimi konusunda uzman bir
YouTube Shorts senaristisin. Kanal: "Zifiri Saatler" - Turk/Osmanli/Anadolu efsanelerinin ve
karanlik tarihi olaylarinin "efsane mi, gercek mi" anlatimi. Gorevin EN FAZLA 35 saniye seslendirmeye
uygun (yaklasik 75-95 kelime), gerilimli ama GERCEGE dayali kisa bir anlatim yazmak.

YAPI (cok onemli - izleyiciyi sona kadar tutar):
- ILK CUMLE: bir sahne/an ile ya da 2. tekil sahis ("sen") ile SPESIFIK ac. Klise/soyut giris
  YASAK ("Bugun size anlatacagim", "Yillardir" gibi). Ornek: "Gece yarisi o kosker penceresinde
  bir isik yanar - ama iceride kimse yasamaz."
- Ilk birkac saniyede bir MERAK ACIGI + izleyiciye "sonunda gercegi gorecegin" hissi ver (loop
  vaadi). Cevabi/gercegi HEMEN verme.
- GOVDE: once efsaneyi/rivayeti kur (gerilim), ortada kucuk bir "aha" detayi birak, ama asil
  aciklamayi SONA sakla. Her birkac cumlede bir seyi degistir/ilerlet.
- KAPANIS: muhtemel GERCEK/tarihsel aciklamayi ver, ve SON CUMLE acilis goruntusune GERI DONSUN
  (loop - izleyici farkinda olmadan basa sarar). Duz "sirri cozulemedi" ile bitirme.
- Cumleler KISA, net, seslendirmeye ve altyaziya uygun.

KIRMIZI CIZGILER (ihlal = guven/telif riski):
- YAYGIN BILINEN efsane/olaylari kullan. UYDURMA spesifik tarih, isim, belge ya da "gizli kanit"
  URETME. Emin olmadigin kesin iddialari verme.
- Efsane/rivayet kismini "anlatilir / rivayet edilir / halk arasinda soylenir" gibi cerceve;
  tarihsel baglami GENEL ve iddiasiz tut. Efsane ile gercegi net ayir.
- Gercek, yasayan kisi ismi kullanma; gercek bir kisiyi/kurumu karalama. Saygili ol (ozellikle
  din/olum). Propaganda/tek tarafli carpitma yok. Kufur/asiri siddet yok.

BASLIK kurallari (Bolum 6 formulleri - tiklamayi belirler):
- 45-70 karakter, MERAK ACIGI acan, cevabi vermeyen bir baslik. Su formullerden BIRINI kullan:
  * Gizli gercek/ortbas: "...nin kimsenin bilmedigi gercek yuzu"
  * Cevap isteyen soru: "Bu kosk neden 100 yildir bos?"
  * Nasil + iddia: "Bir kasaba tek gecede nasil bosaldi?"
  * Beklenmedik sayi: "300 yildir yanan o mumun sirri"
- Baslik ile thumb_hook AYNI seyi soylemesin, birbirini TAMAMLASIN.

thumb_hook (kapak icin - COK ONEMLI):
- Basligin parcasi/kesilmisi DEGIL; tek basina okununca GRAMER OLARAK TAM, 3-6 kelimelik carpici
  bir ifade. Ornek: "Gerçeği Kimse Bilmiyor" / "Hâlâ Orada Duruyor" / "Kayıtlarda Yok".

ACIKLAMA (description): 2-3 cumle, olayi ozetleyen ama gercegi vermeyen, merak birakan; sonu
izleyiciyi dusunmeye/yorum yapmaya iten bir soru.

ETIKET (hashtags): 10-12 arasi TEMAYA OZEL etiket (genel/SEO etiketleri ayrica eklenecek).

GORSEL PROMPT (image_prompt - AI arkaplan gorseli icin):
- Anlatimin gectigi mekani betimleyen, INGILIZCE, 1 cumlelik gorsel sahne promptu
  (ornek: "abandoned ottoman mansion interior at night, single candle, dust").
  Sadece mekan/atmosfer betimle; gercek kisi/yuz tarif etme; stil/teknik kelime EKLEME.
- scene_prompts: anlatinin FARKLI anlarini betimleyen 6-8 kisa INGILIZCE gorsel sahne
  promptu (ilk 3'u ilk saniyeler icin en carpici kareler). Ayni kurallar: sadece
  mekan/atmosfer, gercek kisi/yuz yok, stil kelimesi yok. Arkaplan bunlardan kurulur.

Cikti SADECE su JSON olsun, baska metin yok:
{
  "title": "45-70 karakter, merak acigi acan baslik",
  "thumb_hook": "3-6 kelimelik, bagimsiz, gramer olarak tam carpici ifade",
  "description": "2-3 cumle ozet + soru ile bitsin",
  "image_prompt": "Ingilizce, mekani betimleyen kisa gorsel sahne promptu",
  "scene_prompts": ["ingilizce sahne 1", "sahne 2", "... 6-8 arasi"],
  "story": "Anlatimin tam metni (seslendirme icin)",
  "hashtags": ["#temaya-ozel1", "#etiket2", "... 10-12 arasi"]
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
                    normalized.append({"title": item})
                else:
                    normalized.append(item)
            return normalized
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_history(history, new_title: str, category: str):
    history.append({"title": new_title, "category": category})
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def pick_category(history):
    recent = [h.get("category") for h in history[-AVOID_SAME_CATEGORY_LAST_N:] if h.get("category")]
    candidates = [c for c in CATEGORIES if c["key"] not in recent]
    if not candidates:
        candidates = CATEGORIES
    return random.choice(candidates)


def merge_seo_keywords(hashtags):
    picked = random.sample(SEO_KEYWORDS, k=min(12, len(SEO_KEYWORDS)))
    seo_tags = ["#" + k.replace(" ", "") for k in picked]
    base = ["#shorts", "#tarih", "#efsane", "#keşfet"]
    combined = list(dict.fromkeys(hashtags + seo_tags + base))

    result = []
    total_chars = 0
    for tag in combined:
        if len(result) >= 30:
            break
        tag_len = len(tag.strip("#")) + 1
        if total_chars + tag_len > 480:
            break
        result.append(tag)
        total_chars += tag_len
    return result


def generate_story():
    history = load_history()
    category = pick_category(history)
    recent_titles = [h["title"] for h in history[-MAX_HISTORY_IN_PROMPT:] if h.get("title")]

    model = genai.GenerativeModel(
        "gemini-3.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )

    avoid_text = ""
    if recent_titles:
        avoid_text = (
            "\n\nDaha once islenen basliklar (bunlarla ayni/benzer konuyu TEKRARLAMA):\n"
            + "\n".join(f"- {t}" for t in recent_titles)
        )

    prompt = (
        f"Kategori: {category['hint']}\n\n"
        f"Bu kategoriye uygun, YAYGIN BILINEN bir Turk/Osmanli/Anadolu efsanesi ya da "
        f"karanlik tarihi olayi sec ve 'efsane -> gercek' yapisinda ozgun bir anlatim uret. "
        f"Efsane kismini rivayet olarak cerceve, gercek/tarihsel aciklamayi sona sakla ve "
        f"son cumleyi acilis goruntusune baglayarak (loop) bitir. Uydurma tarih/isim/belge KULLANMA."
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
    data["_theme"] = category["bg"]
    data["_category"] = category["key"]
    data["_cta"] = random.choice(CTA_PHRASES)
    data["hashtags"] = merge_seo_keywords(data.get("hashtags", []))

    if not data.get("thumb_hook"):
        data["thumb_hook"] = random.choice([
            "Gerçeği Kimse Bilmiyor", "Hâlâ Orada Duruyor", "Kayıtlarda Yok",
            "Kimse Konuşmuyor", "Efsane mi, Gerçek mi",
        ])

    save_history(history, data["title"], category["key"])
    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
