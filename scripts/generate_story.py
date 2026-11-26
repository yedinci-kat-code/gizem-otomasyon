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
import re
import random
import sys
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("HATA: GEMINI_API_KEY bulunamadi", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

HISTORY_PATH = "data/history.json"
MAX_HISTORY_IN_PROMPT = 120
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
    {"key": "turk_mitolojisi",
     "hint": "Turk/Anadolu mitolojisinden bir YARATIK ya da varlik (Alkarisi, Albasti, Karakoncolos, "
             "Sahmaran, Tepegoz, Ejderha, Hizir, Umay, Erlik, Su iyesi, Orman iyesi, Cin padisahi gibi) - "
             "bir yerde/koyde onunla karsilasma rivayeti + inancin muhtemel gercek kokeni.",
     "bg": "anadolu_efsanesi"},
    {"key": "batil_inanc",
     "hint": "Turkiye'de herkesin bildigi bir BATIL INANC / gelenegin arkasindaki efsane (neden bicak elden ele "
             "verilmez, gece neden ayna bakilmaz, kapi esiginde neden oturulmaz, gece islik neden calinmaz gibi) - "
             "inancin dogdugu rivayet + gercek tarihsel/kulturel sebebi. Baslik/kanca 'Neden...?' sorusu olsun.",
     "bg": "lanetli_mekan"},
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

SYSTEM_PROMPT = """Sen Turkce icerik ureten, TARIH & EFSANE anlatimi konusunda uzman bir YouTube Shorts
senaristi VE cizgi film yonetmenisin. Kanal: "Zifiri Saatler" - Turk/Osmanli/Anadolu efsanelerinin ve
karanlik tarihi olaylarin "efsane mi, gercek mi" anlatimi. Video formati: SEVIMLI CIZGI FILM Short.
Her videoyu kanalin SABIT MASKOT ANLATICISI "Zifiri Bekci" (elinde fenerli, fesli, beyaz biyikli yasli
gece bekcisi) anlatir: videoyu o acar, arada izleyiciye doner, gercegi o aciklar, videoyu o kapatir.
Hikayedeki kisiler cizgi karakter olarak canlandirilir. Toplam 30-38 saniye: 60-75 kelime (anlatici yavas ve duygulu okur, 75 kelimeyi ASLA gecme).

YAPI (cok onemli - izleyiciyi sona kadar tutar):
- ILK CUMLE (kanca): girissiz, gercek gibi soylenen bir paradoks/sahne. ICINDE MUTLAKA SEHIR/YER ADI ve
  OLAGANUSTU IDDIA olsun (o sehirden olan paylasir). Klise giris YASAK ("Bugun size anlatacagim", "Yillardir").
  Ornekler: "Diyarbakir'da bir cami duvarinda tasa donmus bir yilan duruyor." / "Tarsus'un altinda yilanlarin
  kralicesi yasiyormus." (Batil inanc konularinda yer sart degil, kanca "Neden...?" sorusu olabilir.)
- Ilk saniyelerde MERAK ACIGI + "sonunda gercegi goreceksin" vaadi. Cevabi HEMEN verme.
- GOVDE: efsaneyi/rivayeti kur (gerilim, 2-4 buyuk ve GOSTERILEBILIR vurus), ortada izleyiciye
  donen kisa bir bekci cumlesi ("Peki gercekten boyle mi oldu?").
- GERCEK: muhtemel gercek/tarihsel aciklama ("Kayitlara gore..." / "Tarihciler...").
- KAPANIS: son cumle acilis goruntusune GERI DONSUN (loop). Soru/takip cagrisi YAZMA: sistem sona
  "Senin memleketinde..." sorusunu kendisi ekler.
- Cumleler KISA (6-14 kelime), seslendirmeye uygun. Rakamlari YAZIYLA yaz ("on sekiz", "bin
  dort yuz elli uc"). Izleyicinin zaten gordugunu tarif etme.

KIRMIZI CIZGILER (ihlal = guven/telif riski):
- YAYGIN BILINEN efsane/olaylari kullan. UYDURMA spesifik tarih, isim, belge ya da "gizli kanit"
  URETME. Emin olmadigin kesin iddialari verme.
- Efsane kismini "rivayete gore / anlatilir / halk arasinda soylenir" diye cerceve; gercegi GENEL
  ve iddiasiz tut. Efsane ile gercegi net ayir.
- Yasayan gercek kisi yok; kimseyi karalama. Din/olum konusunda saygili ol. Kan/vahset/kufur yok;
  korku "sevimli gerilim" seviyesinde kalsin (cocuklar da izleyebilir).

BASLIK (45-70 karakter, merak acigi, cevabi vermeyen): "...nin kimsenin bilmedigi gercek yuzu",
"Bu kosk neden 100 yildir bos?", "Bir kasaba tek gecede nasil bosaldi?" gibi formuller.
thumb_hook: videonun ILK 3-4 SANIYESINDE ekranin ortasinda BUYUK yazilacak vurucu baslik. 3-6 kelime, tek basina
gramer olarak tam, merak uyandiran, cevabi vermeyen; MUMKUNSE SEHIR ADI gecsin (orn. "Diyarbakir'da Tasa Donen Yilan",
"Mersin'de Denize Kule Yapti"). Emoji yok.
description: 2-3 cumle ozet, gercegi vermesin, soru ile bitsin. hashtags: 10-12 temaya ozel etiket.

CEKIM PLANI (beats) - her cumle (ya da kisa cumle cifti) bir "beat"tir. beats[].text'lerin
birlesimi okunacak metnin TAMAMIDIR (ayri bir story alani yazma). 7-10 beat. Alanlar:
- text: okunacak cumle(ler).
- shot: su listeden biri:
  bekci_hook (SADECE ilk beat: bekci mekanda fenerle anlatir), bekci (bekci izleyiciye doner; orta
  bolumde EN FAZLA 1 kez), genis (mekanin genis acisi, kisiler kucuk), karakter (tek kisi orta plan),
  yakin (tek kisinin yuz tepkisi), ikili (iki kisi), kovalamaca (biri kacar biri kovalar),
  kalabalik (halk/kalabalik), obje (bir yazi/obje yakin plani: label ile), gercek (SADECE sondan
  bir onceki beat: isik zifiriden altina doner, bekci parsomen acar), bekci_kapanis (SADECE son
  beat: bekci acilistaki ayni yerde; loop).
- loc: su mekanlardan biri. 2 YA DA 3 FARKLI mekan kullan (tek mekanli video YASAK); ayni mekanda arka arkaya
  en fazla 3 beat. Hikayenin ana nesnesini en iyi GOSTEREN mekani sec: cesme/fiskiye/kuyu -> avlu,
  kule/deniz -> sahil, kopru -> kopru, sur/hisar -> kale, saray odasi -> saray, belge/kayit -> arsiv.
  Ilk ve son beat AYNI mekan:
  ozel, kosk_ic, kosk_dis, mezarlik, koy, kopru, kale, saray, magara, carsi, orman, sahil, avlu, arsiv.
  "ozel" = hikayenin GERCEK mekani (orn. Nemrut Dagi'nin dev tas baslari, Peri Bacalari, Sumela Manastiri,
  Kiz Kulesi). Bu mekan, landmark.backdrop tarifinden ozel olarak CIZILIR. ILK ve SON beat HER ZAMAN "ozel"
  olsun ve hikayede en az 1 beat daha "ozel" gecsin. Diger beat'ler icin listedeki genel mekanlari kullan.
- obje beat'inde "obj": "ozel" yazarsan, ekranda parsomen yerine landmark.detail tarifinden cizilen YAKIN
  PLAN gorsel gosterilir (orn. dev tas kafanin yuzu, lanetli ayna). Her videoda 1 obje beat'i "ozel" olsun.
- who: bu beat'te gorunen hikaye karakterlerinin cast anahtarlari (orn. ["A"] ya da ["A","B"]).
  bekci_hook/bekci/bekci_kapanis/obje icin bos birak.
- mood: korku, saskin, merak, sinsi, uzgun, mutlu, kizgin, dusunceli, anlatan, urkek, kararli,
  gururlu, hayran, uykulu. (ikili/kovalamaca icin ikinci kisi: mood2)
- action (istege bagli): yuru, kos, kac, dur, isaret, bak, saklan, otur, uyu, el_kaldir, konus.
- fx (istege bagli, en fazla her 2 beat'te 1): soru, unlem, ter, fikir, duman, kurukafa, yildiz,
  kalp, kizginlik, zzz, para, toz.
- prop (istege bagli, who[0] elinde tutar): fener, mektup, anahtar, altin, para, parsomen, kitap, buyutec.
- label: SADECE shot=obje icin, 1-3 kelimelik BUYUK HARF yazi (orn. "FERMAN", "1453", "KAYIP").
  Her videoda EN AZ 1 obje beat'i olsun. Arka arkaya iki beat'te ayni shot tipini kullanma.
- vurgu (istege bagli, videoda 3-4 beat'te): o beat'in text'inde AYNEN gecen 1-3 kelimelik can alici ifade
  (orn. "TASA DONDU", "KIRK YIL", "LANETLENDI"). Kelime soylendigi an ekranda renkli kutuda patlar.
- replik (istege bagli, karakterli 2-3 beat'te): who[0] karakterinin AGZINDAN kisa replik, 2-5 kelime, ! ya da ?
  ile (orn. "Kim var orada?!", "Bu tas yuruyor!"). Seslendirilmez, cizgi roman balonunda gorunur. Anlatimi tekrar etme.
- card (istege bagli, ilk efsane beat'inde 1 kez): {"title": "Yer/Olay adi", "sub": "Rivayete gore · Sehir"}.
- light (istege bagli): zifiri, gece, dramatik, altin, gunduz, ic. Varsayilani mekan belirler.

CAST: en fazla 3 karakter, anahtarlar A, B, C. preset su listeden: koylu_erkek, koylu_kadin,
yasli_kadin, yasli_adam, cocuk, pasa, padisah, yeniceri, muhafiz, tuccar, mimar, hanim, balikci,
asker, gezgin, hayalet, yaratik (karanlik, golgemsi efsane varligi: Alkarisi, cin, iye vb.). color: istege bagli kiyafet rengi (#hex). Tarihi kisiler temsili karakterdir.

Cikti SADECE su JSON olsun, baska metin yok:
{
  "topic": "Efsanenin/olayin KISA kanonik adi (orn. Kiz Kulesi, Yerebatan Medusa)", "place": "Sehir adi (orn. Diyarbakir)",
  "geo": {"lat": 37.91, "lon": 40.24},
  "landmark": {
    "backdrop": "ENGLISH, 1-2 sentences: the REAL place as it really looks, wide eye-level view from the ground, the famous landmark clearly recognizable in the middle/upper part, open empty ground in the lower third (characters will stand there). No people.",
    "detail": "ENGLISH, 1 sentence: close-up of the story's key object or the landmark's most iconic detail. No people.",
    "hook": "ENGLISH, 1-2 sentences: the single most dramatic SUPERNATURAL moment of the legend as one picture (the creature, the curse, the miracle happening), e.g. 'a giant glowing serpent bursting out of an old mosque's stone wall at night while a frightened villager drops his lantern'. Cute-scary, no gore.",
    "ground": "#hex color of the ground in the lower third (for blending)"
  },
  "title": "...", "thumb_hook": "...", "description": "...",
  "hashtags": ["#...", "... 10-12 arasi"],
  "cast": {"A": {"preset": "padisah"}, "B": {"preset": "hanim", "color": "#8a3a6a"}},
  "beats": [
    {"text": "Ilk cumle (kanca).", "shot": "bekci_hook", "loc": "sahil"},
    {"text": "...", "shot": "genis", "loc": "saray", "who": ["A"], "mood": "merak", "card": {"title": "...", "sub": "Rivayete gore · ..."}},
    {"text": "...", "shot": "gercek", "loc": "sahil"},
    {"text": "... son cumle (loop)", "shot": "bekci_kapanis", "loc": "sahil"}
  ]
}"""


LOC_HINT = {
    "perili_kosk": ["kosk_dis", "kosk_ic", "arsiv"], "lanetli_mekan": ["mezarlik", "avlu", "magara", "arsiv"],
    "kayip_yerlesim": ["koy", "orman", "arsiv"], "yapinin_sirri": ["kopru", "kale", "avlu", "magara"],
    "saray_golgesi": ["saray", "avlu", "arsiv"], "anadolu_efsanesi": ["koy", "magara", "orman", "sahil"],
    "karanlik_olay": ["carsi", "kale", "sahil", "koy"],
    "turk_mitolojisi": ["koy", "orman", "magara", "mezarlik"], "batil_inanc": ["koy", "kosk_ic", "carsi", "mezarlik"],
}
VALID_SHOTS = {"bekci_hook", "bekci", "genis", "karakter", "yakin", "ikili", "kovalamaca", "kalabalik", "obje", "gercek", "bekci_kapanis"}
VALID_LOCS = {"ozel", "kosk_ic", "kosk_dis", "mezarlik", "koy", "kopru", "kale", "saray", "magara", "carsi", "orman", "sahil", "avlu", "arsiv"}


def normalize_plan(data):
    """Gemini planini motorun bekledigi kurallara oturtur (ilk/son/gercek beat, mekanlar, cast)."""
    beats = [b for b in data.get("beats", []) if isinstance(b, dict) and str(b.get("text", "")).strip()]
    if len(beats) < 4:
        raise ValueError("Plan cok kisa: en az 4 beat gerekli")
    cast = {k: v for k, v in (data.get("cast") or {}).items() if k in ("A", "B", "C") and isinstance(v, dict)}
    for b in beats:
        b["text"] = " ".join(str(b["text"]).split())
        if b.get("shot") not in VALID_SHOTS:
            b["shot"] = "genis"
        if b.get("loc") not in VALID_LOCS:
            b["loc"] = beats[0].get("loc") if beats[0].get("loc") in VALID_LOCS else "kosk_dis"
        b["who"] = [w for w in (b.get("who") or []) if w in cast]
        if b["shot"] in ("bekci_hook", "bekci_kapanis") and b is not beats[0] and b is not beats[-1]:
            b["shot"] = "bekci"
    # anlatici ortada en fazla 1 kez; fazlasi hikaye cekimine doner
    mids = [b for b in beats[1:-1] if b["shot"] == "bekci"]
    for b in mids[1:]:
        b["shot"] = "karakter" if b["who"] else "genis"
    # ayni shot arka arkaya gelmesin
    for prev, b in zip(beats, beats[1:]):
        if b["shot"] == prev["shot"] and b["shot"] in ("genis", "karakter", "yakin", "ikili", "kalabalik"):
            alt = {"genis": "karakter", "karakter": "yakin", "yakin": "karakter", "ikili": "yakin", "kalabalik": "karakter"}[b["shot"]]
            b["shot"] = alt if (b["who"] or alt == "genis") else "genis"
    beats[0]["shot"] = "bekci_hook"
    beats[-1]["shot"] = "bekci_kapanis"
    lm = data.get("landmark") or {}
    if isinstance(lm, dict) and str(lm.get("backdrop", "")).strip():
        beats[0]["loc"] = "ozel"                 # acilis: konunun gercek mekani
    else:
        data["landmark"] = {}
        for b in beats:
            if b["loc"] == "ozel":
                b["loc"] = "kosk_dis"
    beats[-1]["loc"] = beats[0]["loc"]          # loop: son kare = ilk kare
    if not any(b["shot"] == "gercek" for b in beats):
        beats[-2]["shot"] = "gercek"
    # vurgu: metinde gecmeli, en fazla 4; replik: sadece karakterli hikaye cekimlerinde, en fazla 3
    nv = nr = 0
    for b in beats:
        v = str(b.get("vurgu") or "").strip()
        if v and nv < 4 and _norm(v) and _norm(v) in _norm(b["text"]) and len(v) <= 24:
            b["vurgu"] = v; nv += 1
        else:
            b.pop("vurgu", None)
        r = " ".join(str(b.get("replik") or "").split())
        if r and nr < 3 and b["who"] and b["shot"] in ("karakter", "yakin", "ikili", "genis", "kovalamaca", "kalabalik") and len(r) <= 30:
            b["replik"] = r; nr += 1
        else:
            b.pop("replik", None)
    if not any(isinstance(b.get("card"), dict) for b in beats):  # bilgi karti (harita ile) her videoda bir kez
        tgt = next((b for b in beats[1:-1] if b["shot"] not in ("bekci", "gercek", "obje")), beats[1])
        tgt["card"] = {"title": str(data.get("topic") or "")[:28], "sub": "Rivayete göre · " + str(data.get("place") or "Anadolu")[:22]}
    g = data.get("geo") or {}
    try:
        lat, lon = float(g.get("lat")), float(g.get("lon"))
        data["geo"] = {"lat": lat, "lon": lon} if (35.7 <= lat <= 42.3 and 25.6 <= lon <= 45.0) else None
        if _norm(data.get("place")) in ("anadolu", "turkiye", "osmanli", "") or data.get("_generic_place"):
            data["geo"] = None  # genel yer: haritada yaniltici pin koyma
    except (TypeError, ValueError):
        data["geo"] = None
    data["beats"], data["cast"] = beats, cast
    data["story"] = " ".join(b["text"] for b in beats)
    n = len(data["story"].split())
    if n > 85:
        raise ValueError(f"Metin cok uzun ({n} kelime, en fazla 75)")
    if len({b["loc"] for b in beats}) < 2:
        raise ValueError("Tek mekanli plan: en az 2 farkli mekan gerekli")
    return data


def check_hook(data, category_key):
    """Ilk cumlede sehir/yer adi gecmeli (batil inanc haric)."""
    if category_key == "batil_inanc":
        return
    place = _norm(data.get("place"))
    first = _norm(data["beats"][0]["text"])
    keys = [w[:4] for w in place.split() if len(w) > 2]
    if keys and not any(k in first for k in keys):
        raise ValueError(f"Ilk cumlede sehir/yer adi ('{data.get('place')}') yok; kancaya sehir adini koy")


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


def save_history(history, new_title: str, category: str, topic: str = "", hook: str = "", episode: int = 0):
    history.append({"title": new_title, "category": category, "topic": topic, "hook": hook, "episode": episode})
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _norm(t):
    t = (t or "").lower()
    for a, b in (("ı", "i"), ("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ö", "o"), ("ç", "c"), ("â", "a"), ("î", "i"), ("û", "u")):
        t = t.replace(a, b)
    return " ".join("".join(ch if ch.isalnum() else " " for ch in t).split())


def check_duplicate(data, history):
    """Tekrari engeller: ayni konu/efsane TUM gecmiste bir kez islenir; baslik ve acilis cumlesi eskilere benzemez."""
    import difflib
    topic = _norm(data.get("topic"))
    if not topic:
        raise ValueError("topic alani bos: efsanenin kisa adini yaz")
    for h in history:
        ht = _norm(h.get("topic"))
        old = _norm(h.get("title"))
        if ht and (topic == ht or topic in ht or ht in topic):
            raise ValueError(f"'{data.get('topic')}' daha once islendi, BASKA bir efsane sec")
        if not ht and topic:  # eski kayitlarda topic yok: konu kelimeleri basliktaysa ayni konu say
            tw = [w[:5] for w in topic.split() if len(w) > 2]
            ow = {w[:5] for w in old.split()}
            if tw and all(w in ow for w in tw):
                raise ValueError(f"'{data.get('topic')}' daha once islendi (baslikta var), BASKA bir efsane sec")
        if old and difflib.SequenceMatcher(None, _norm(data.get("title")), old).ratio() > 0.72:
            raise ValueError(f"Baslik eski bir basliga cok benziyor ({h.get('title')}), farkli kur")
        if h.get("hook") and difflib.SequenceMatcher(None, _norm(data.get("thumb_hook")), _norm(h["hook"])).ratio() > 0.8:
            raise ValueError("Acilis basligi eskisine cok benziyor, farkli yaz")


def pick_category(history):
    recent = [h.get("category") for h in history[-AVOID_SAME_CATEGORY_LAST_N:] if h.get("category")]
    candidates = [c for c in CATEGORIES if c["key"] not in recent]
    if not candidates:
        candidates = CATEGORIES
    # Kanal verisi (Kasim 2026): halk efsanesi / mucize / yaratik / lanet konulari 10-100 kat daha cok izlendi,
    # "issiz koy" ve "yapinin sirri" konulari en zayiflar. Secim agirlikli.
    # Rakip analizi (Kasim 2026, IG/TikTok TR): mitolojik yaratik (Sahmaran, Alkarisi) ve "Neden...?" batil
    # inanc videolari normalin 50-140 kati izlendi.
    w = {"turk_mitolojisi": 5, "batil_inanc": 3, "anadolu_efsanesi": 5, "karanlik_olay": 4, "perili_kosk": 3, "saray_golgesi": 3, "lanetli_mekan": 3,
         "yapinin_sirri": 1, "kayip_yerlesim": 1}
    return random.choices(candidates, weights=[w.get(c["key"], 2) for c in candidates], k=1)[0]


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


DIAG = {}  # test ciktisinda gormek icin (story.json -> _diag)
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "UC2-Nt7k59URUzBnmKyOSNcw")


def _yt_get(params):
    """YouTube Data API (herkese acik yorumlar): once kanal OAuth'u, olmazsa API anahtari denenir."""
    import urllib.parse
    import urllib.request
    url = "https://www.googleapis.com/youtube/v3/commentThreads?"
    cid, csec, rt = (os.environ.get(k) for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"))
    errs = []
    if cid and csec and rt:
        try:
            body = urllib.parse.urlencode({"client_id": cid, "client_secret": csec, "refresh_token": rt,
                                           "grant_type": "refresh_token"}).encode()
            tok = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body, timeout=20))["access_token"]
            req = urllib.request.Request(url + urllib.parse.urlencode(params), headers={"Authorization": "Bearer " + tok})
            return json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e:
            errs.append(f"oauth: {str(e)[:80]}")
    try:
        return json.load(urllib.request.urlopen(url + urllib.parse.urlencode({**params, "key": GEMINI_API_KEY}), timeout=20))
    except Exception as e:
        errs.append(f"anahtar: {str(e)[:80]}")
    raise RuntimeError("; ".join(errs))


def fetch_viewer_requests(done_topics):
    """Kanal yorumlarinda izleyicilerin anlatilmasini istedigi efsaneleri cikarir (islenmemis olanlar)."""
    try:
        js = _yt_get({"part": "snippet", "allThreadsRelatedToChannelId": YT_CHANNEL_ID, "maxResults": 100,
                      "order": "time", "textFormat": "plainText"})
        texts = [it["snippet"]["topLevelComment"]["snippet"]["textDisplay"][:300] for it in js.get("items", [])]
    except Exception as e:
        print("Yorumlar okunamadi, izleyici istegi atlandi:", e)
        DIAG["yorumlar"] = f"okunamadi: {str(e)[:160]}"
        return []
    if not texts:
        print("Yorum yok, izleyici istegi atlandi")
        return []
    try:
        m = genai.GenerativeModel("gemini-3.5-flash", generation_config={"response_mime_type": "application/json", "temperature": 0.2})
        out = json.loads(m.generate_content(
            "Asagida bir Turkce efsane/gizem kanalinin yorumlari var. Izleyicilerin ANLATILMASINI ISTEDIGI ya da "
            "'bizim orada da var' dedigi somut efsane/yaratik/olay/yer adlarini cikar. Kufur, spam, genel ovgu yok sayilir. "
            'Sadece JSON: {"istekler": ["kisa ad", ...]} (en fazla 8, yoksa bos liste).\n\n' + "\n".join("- " + t for t in texts)
        ).text)
        reqs = [str(x).strip() for x in out.get("istekler", []) if str(x).strip()]
    except Exception as e:
        print("Yorum istekleri cikarilamadi:", e)
        return []
    done = [_norm(t) for t in done_topics]
    reqs = [r for r in reqs if not any(_norm(r) in d or d in _norm(r) for d in done if d)]
    print(f"Yorumlar: {len(texts)} | izleyici istekleri: {reqs}")
    DIAG["yorumlar"] = f"{len(texts)} yorum okundu; istekler: {reqs}"
    return reqs


def pick_best_hook(data, category_key):
    """Insan dokunusu yerine: 5 alternatif kanca + 5 kapak basligi yazdirip puanlatir, mevcuttan iyiyse degistirir."""
    first, second = data["beats"][0]["text"], (data["beats"][1]["text"] if len(data["beats"]) > 1 else "")
    ask = f"""Turkce bir efsane Shorts'unun ILK CUMLESI (kanca) ve kapak basligi icin editorsun.
Konu: {data.get('topic')} | Yer: {data.get('place')} | Tur: {category_key}
Hikaye: {data.get('story')}
Mevcut kanca: {first}
Ikinci cumle (kanca buna dogal baglanmali): {second}
Mevcut kapak basligi: {data.get('thumb_hook')}

Kurallar (milyon izlenen Turkce efsane videolarindan): ilk cumlede somut bir sahne + olaganustu iddia/paradoks;
{"sehir/yer adi MUTLAKA gecsin" if category_key != "batil_inanc" else "'Neden...?' sorusu ya da herkesin bildigi inanc"};
en fazla 12 kelime; EN CARPICI IDDIA ILK 4-5 KELIMEDE soylensin (izleyici 1. saniyede karar veriyor, girizgah yok: 'Bu havuzdan kan akiyordu.' gibi); gunluk konusma Turkcesi, ceviri kokmasin; 'Bugun size', 'Hic dusundunuz mu', 'Yillardir' gibi
klise girisler YASAK; cevabi ele verme. Kapak basligi 3-5 kelime, merak birakan, gramer olarak tam.
5 yeni kanca ve 5 yeni kapak basligi yaz; mevcutlar dahil HER BIRINI 1-10 puanla (izleyiciyi ilk 2 saniyede durdurma gucu).
Sadece JSON: {{"kancalar": [{{"metin": "...", "puan": 8}}], "basliklar": [{{"metin": "...", "puan": 7}}],
"mevcut_kanca_puani": 6, "mevcut_baslik_puani": 6}}"""
    try:
        m = genai.GenerativeModel("gemini-3.5-flash", generation_config={"response_mime_type": "application/json", "temperature": 0.8})
        out = json.loads(m.generate_content(ask).text)
    except Exception as e:
        print("Kanca secici atlandi:", e)
        return
    keys = [w[:4] for w in _norm(data.get("place")).split() if len(w) > 2]

    def ok_hook(t):
        t = " ".join(str(t).split())
        if not t or len(t.split()) > 14 or not re.search(r"[.!?…]$", t):
            return False
        return category_key == "batil_inanc" or not keys or any(k in _norm(t) for k in keys)

    hooks = sorted([h for h in out.get("kancalar", []) if ok_hook(h.get("metin"))], key=lambda h: -float(h.get("puan", 0)))
    if hooks and float(hooks[0].get("puan", 0)) > float(out.get("mevcut_kanca_puani", 10)):
        print(f"Kanca degisti ({out.get('mevcut_kanca_puani')} -> {hooks[0]['puan']}): {first} => {hooks[0]['metin']}")
        DIAG["kanca"] = f"{first} ({out.get('mevcut_kanca_puani')}) => {hooks[0]['metin']} ({hooks[0]['puan']})"
        data["beats"][0]["text"] = " ".join(hooks[0]["metin"].split())
    titles = sorted([t for t in out.get("basliklar", []) if 2 <= len(str(t.get("metin", "")).split()) <= 6],
                    key=lambda t: -float(t.get("puan", 0)))
    if titles and float(titles[0].get("puan", 0)) > float(out.get("mevcut_baslik_puani", 10)):
        print(f"Kapak basligi degisti: {data.get('thumb_hook')} => {titles[0]['metin']}")
        data["thumb_hook"] = " ".join(str(titles[0]["metin"]).split())
    data["story"] = " ".join(b["text"] for b in data["beats"])


def generate_story():
    history = load_history()
    category = pick_category(history)
    recent_titles = [h["title"] for h in history[-MAX_HISTORY_IN_PROMPT:] if h.get("title")]

    model = genai.GenerativeModel(
        "gemini-3.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json", "temperature": 0.9},
    )

    avoid_text = ""
    done_topics = sorted({h["topic"] for h in history if h.get("topic")})
    if done_topics:
        avoid_text += "\n\nBU EFSANELER ISLENDI, ASLA TEKRAR SECME: " + ", ".join(done_topics)
    if recent_titles:
        avoid_text += (
            "\n\nDaha once islenen basliklar (bunlarla ayni/benzer konuyu TEKRARLAMA):\n"
            + "\n".join(f"- {t}" for t in recent_titles)
        )

    reqs = fetch_viewer_requests(done_topics)
    if reqs:
        avoid_text += ("\n\nIZLEYICI ISTEKLERI (kanal yorumlarindan): " + ", ".join(reqs) +
                       ". Bunlardan biri kategoriye uyuyor, islenmemis ve gercekten bilinen bir efsaneyse ONCELIKLE onu sec "
                       've JSON\'a "izleyici_istegi": true ekle.')

    prompt = (
        f"Kategori: {category['hint']}\n\n"
        f"Bu kategoriye uygun, YAYGIN BILINEN bir Turk/Osmanli/Anadolu efsanesi ya da "
        f"karanlik tarihi olayi sec ve 'efsane -> gercek' yapisinda ozgun bir anlatim uret. "
        f"Efsanede MUTLAKA canli ve gosterilebilir bir olaganustu unsur olsun (yaratik, mucize, lanet, kehanet, "
        f"hayalet, kayip hazine); sadece 'issiz bir yer' ya da 'eski bir yapi' anlatan konulardan kacin. "
        f"Efsane kismini rivayet olarak cerceve, gercek/tarihsel aciklamayi sona sakla ve "
        f"son cumleyi acilis goruntusune baglayarak (loop) bitir. Uydurma tarih/isim/belge KULLANMA.\n"
        f"Bu kategori icin uygun mekanlar: {', '.join(LOC_HINT.get(category['key'], ['kosk_dis']))} "
        f"(gerekirse listedeki diger mekanlar da olur)."
        f"{avoid_text}"
    )

    last_err = None
    for attempt in range(1, 6):
        try:
            ask = prompt if not last_err else prompt + f"\n\nONCEKI DENEME REDDEDILDI: {last_err}. Bu kurala kesin uy."
            response = model.generate_content(ask)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = normalize_plan(json.loads(text.strip()))
            check_duplicate(data, history)
            if attempt <= 3:
                check_hook(data, category["key"])
            break
        except Exception as e:  # bozuk JSON / eksik plan -> tekrar dene
            last_err = e
            print(f"Plan denemesi {attempt}/5 basarisiz: {e}")
    else:
        raise RuntimeError(f"Gemini gecerli cekim plani uretemedi: {last_err}")
    pick_best_hook(data, category["key"])
    data["_diag"] = DIAG
    data["_theme"] = category["bg"]
    data["_category"] = category["key"]
    data["_cta"] = random.choice(CTA_PHRASES)
    data["_cta_screen"] = random.choice(["Sıradaki efsane için takip et", "Yeni dosyalar için takip et", "Efsaneyi sevdiysen takip et"])
    loc_tags = ["#" + "".join(str(x).split()) for x in (data.get("place"), data.get("topic")) if x]
    data["hashtags"] = merge_seo_keywords(loc_tags + data.get("hashtags", []))

    if not data.get("thumb_hook"):
        data["thumb_hook"] = random.choice([
            "Gerçeği Kimse Bilmiyor", "Hâlâ Orada Duruyor", "Kayıtlarda Yok",
            "Kimse Konuşmuyor", "Efsane mi, Gerçek mi",
        ])

    # Seri kimligi: "Zifiri Dosya #N". Cizgi donemi 7 videoyla basladi (Amasya #1 ... Van Golu #7).
    # Sayac sadece YouTube'a yuklenen videolarla ilerler (gecmis yalnizca basarili yuklemede kaydedilir).
    data["episode"] = max([h.get("episode", 0) for h in history] + [7]) + 1
    # Konusan abone cagrisi: bekci kapanista izleyiciye seslenir
    cta_line = random.choice([
        "Senin memleketinde böyle bir efsane var mı? Yorumlara yaz, takip etmeyi unutma.",
        "Sence efsane mi, gerçek mi? Yorumlara yaz, sıradaki dosya için takip et.",
        "Bunu daha önce duymuş muydun? Yorumlara yaz, takip et.",
    ] if data["_category"] != "batil_inanc" else [
        "Sizin evde bu inanç var mı? Yorumlara yaz, takip etmeyi unutma.",
        "Sen bu inanca uyuyor musun? Yorumlara yaz, takip et.",
    ])
    data["beats"][-1]["text"] = data["beats"][-1]["text"].rstrip() + " " + cta_line
    data["story"] = " ".join(b["text"] for b in data["beats"])
    save_history(history, data["title"], category["key"], data.get("topic", ""), data.get("thumb_hook", ""), data["episode"])
    return data


if __name__ == "__main__":
    story = generate_story()
    os.makedirs("output", exist_ok=True)
    with open("output/story.json", "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    print("Senaryo uretildi:", story["title"])
