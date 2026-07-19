"""
Zifiri Saatler - Video Montaj
Ust panel: konuyla ilgili atmosferik arkaplan (Pexels) + beliren altyazi
Alt panel: Pexels'ten cekilen hareketli arkaplan (farkli video)
Ses: edge-tts seslendirme + arkaplan muzigi (dusuk sesle karistirilmis)
"""
import json
import subprocess
import os
import re

WIDTH = 1080
HEIGHT = 1920
# libx264 cift sayi yukseklik/genislik ister (4:2:0 chroma icin) - tek sayi
# olursa sessizce 1px kirpip toplam boyutu bozuyordu. Cift sayiya yuvarliyoruz.
TOP_HEIGHT = (int(HEIGHT * 0.56) // 2) * 2
BOTTOM_HEIGHT = HEIGHT - TOP_HEIGHT
FPS = 30

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_audio_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def split_into_sentence_chunks(story_text: str):
    """Sadece kelime sayimi/eslestirme icin cumlelere ayirir (satir kirma YOK artik)."""
    import re
    raw_sentences = re.split(r'(?<=[.!?])\s+', story_text.strip())
    return [s.strip() for s in raw_sentences if s.strip()]


def build_caption_groups_from_words(word_timings, story_text: str, group_size=3):
    """
    Kelime zamanlamasina gore, ekranda AYNI ANDA sadece 'group_size' kadar
    kelime gorunecek sekilde gruplar olusturur (TikTok/Shorts tarzi,
    sirayla degisen kisa altyazi - paragraf DEGIL).

    ONEMLI: Bir grubun bitis zamani, bir SONRAKI grubun baslangicina TAM
    olarak baglanir (hicbir bosluk/tolerans payi birakilmaz). Boylece iki
    grubun ayni anda ekranda gorunmesi (ustuste binme) matematiksel olarak
    imkansiz hale gelir.

    AYRICA: Bir cumle bitince (nokta/soru/unlem isareti gorulunce) grup
    orada KAPATILIR, bir sonraki cumlenin ilk kelimesi ayni grup icine
    ASLA sizmaz - "...kalmisti. Yercekimine" gibi iki farkli cumlenin
    ayni altyazi kutusunda karismasini onler.
    """
    total_words = len(story_text.split())
    if len(word_timings) < total_words * 0.5:
        return None

    groups = []
    current_chunk = []
    for w in word_timings:
        current_chunk.append(w)
        ends_sentence = bool(re.search(r'[.!?…]["\')]?$', w["text"].strip()))
        if len(current_chunk) >= group_size or ends_sentence:
            text = " ".join(x["text"] for x in current_chunk)
            start = current_chunk[0]["offset"]
            groups.append({"text": text, "start": start})
            current_chunk = []

    if current_chunk:
        text = " ".join(x["text"] for x in current_chunk)
        start = current_chunk[0]["offset"]
        groups.append({"text": text, "start": start})

    if not groups:
        return []

    # Her grubun bitisini bir sonrakinin baslangicina sabitle (sifir bosluk/ortusme)
    for i in range(len(groups) - 1):
        groups[i]["end"] = groups[i + 1]["start"]

    # Son grubun bitisini son kelimenin gercek bitis zamanina gore ayarla
    last_word = word_timings[-1]
    groups[-1]["end"] = last_word["offset"] + last_word["duration"] + 0.3

    return groups


def build_caption_groups_from_text(story_text: str, duration: float, group_size=3):
    words = story_text.split()
    if not words:
        return []

    chunks = []
    current = []
    for w in words:
        current.append(w)
        ends_sentence = bool(re.search(r'[.!?…]["\')]?$', w.strip()))
        if len(current) >= group_size or ends_sentence:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))

    per_chunk = duration / len(chunks)
    groups = []
    for i, text in enumerate(chunks):
        groups.append({"text": text, "start": i * per_chunk, "end": (i + 1) * per_chunk})
    return groups


def build_caption_filters(groups):
    filters = []
    for g in groups:
        text = (
            g["text"]
            .replace("\\", "")
            .replace("'", "\u2019")
            .replace(":", "\\:")
        )
        y_pos = "(h*0.56)*0.55"
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:text='{text}':"
            f"fontsize=58:fontcolor=white:borderw=5:bordercolor=black@0.85:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t,{g['start']:.2f},{g['end']:.2f})'"
        )
    return filters


def render(story_path="output/story.json",
           voice_path="output/voice.mp3",
           background_path="output/background.mp4",
           top_background_path="output/top_background.mp4",
           music_path="output/music.mp3",
           timings_path="output/word_timings.json",
           output_path="output/main_body.mp4"):

    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)
    with open(timings_path, "r", encoding="utf-8") as f:
        word_timings = json.load(f)

    raw_audio_duration = get_audio_duration(voice_path)
    duration = raw_audio_duration + 0.5

    # ONEMLI KAYMA DUZELTMESI: edge-tts'in bildirdigi kelime zamanlamalari
    # (word_timings) ile gercek ses dosyasinin suresi arasinda kucuk bir
    # oransal fark olabiliyor - bu da video uzadikca ses/altyazi kaymasinin
    # buyumesine sebep oluyordu. Tum zamanlamalari GERCEK ses suresine gore
    # olcekleyerek bu kaymayi matematiksel olarak sifirliyoruz.
    if word_timings:
        last_word = word_timings[-1]
        reported_total = last_word["offset"] + last_word["duration"]
        if reported_total > 0:
            scale = raw_audio_duration / reported_total
            for w in word_timings:
                w["offset"] *= scale
                w["duration"] *= scale

    groups = None
    if word_timings:
        groups = build_caption_groups_from_words(word_timings, story["story"])
    if not groups:
        print("Kelime zamanlamasi kullanilamadi, cumle bazli esit dagitim uygulaniyor.")
        groups = build_caption_groups_from_text(story["story"], duration)

    caption_filters = build_caption_filters(groups)
    caption_chain = ",".join(caption_filters) if caption_filters else "null"

    has_top_bg = os.path.exists(top_background_path)
    has_music = os.path.exists(music_path)

    # --- 1) UST PANEL: video varsa uzerine altyazi, yoksa duz renk ---
    if has_top_bg:
        top_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", top_background_path,
            "-t", str(duration),
            "-vf",
            (
                f"scale={WIDTH}:{TOP_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{TOP_HEIGHT},"
                f"eq=brightness=-0.15:saturation=0.7,"
                f"{caption_chain},"
                f"fps={FPS},format=yuv420p"
            ),
            "-an",
            "output/top_panel.mp4",
        ]
    else:
        top_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x120a1a:s={WIDTH}x{TOP_HEIGHT}:d={duration}:r={FPS}",
            "-vf", f"{caption_chain},format=yuv420p",
            "-t", str(duration),
            "output/top_panel.mp4",
        ]
    subprocess.run(top_cmd, check=True)

    # --- 2) ALT PANEL: arkaplan videosunu ayri, standart bir formata cevir ---
    bottom_cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", background_path,
        "-t", str(duration),
        "-vf",
        (
            f"scale={WIDTH}:{BOTTOM_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{BOTTOM_HEIGHT},fps={FPS},format=yuv420p"
        ),
        "-an",
        "output/bottom_panel.mp4",
    ]
    subprocess.run(bottom_cmd, check=True)

    # --- 3) SES: seslendirme + (varsa) dusuk sesli arkaplan muzigi karistir ---
    if has_music:
        audio_cmd = [
            "ffmpeg", "-y",
            "-i", voice_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex",
            "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "[aout]",
            "-t", str(duration),
            "-avoid_negative_ts", "make_zero",
            "-async", "1",
            "output/mixed_audio.aac",
        ]
        subprocess.run(audio_cmd, check=True)
        final_audio_path = "output/mixed_audio.aac"
    else:
        final_audio_path = voice_path

    # --- 4) Ust + alt paneli dikey birlestir, basa hook, sona CTA, kalici alt banner + rozet ---
    hook_words = story["title"].split()[:4]
    hook_text = (
        " ".join(hook_words)
        .replace("\\", "")
        .replace("'", "\u2019")
        .replace(":", "\\:")
    )

    cta_text = (
        story.get("_cta", "Sence gerçekten ne oldu? Yorumlara yaz")
        .replace("\\", "")
        .replace("'", "\u2019")
        .replace(":", "\\:")
    )
    cta_start = max(duration - 2.0, 0)

    final_cmd = [
        "ffmpeg", "-y",
        "-i", "output/top_panel.mp4",
        "-i", "output/bottom_panel.mp4",
        "-i", final_audio_path,
        "-filter_complex",
        (
            "[0:v][1:v]vstack=inputs=2,setsar=1[stacked];"
            # Ust-sol kose: sabit "ABSURT KORKU" etiketi (tum video boyunca)
            f"[stacked]drawtext=fontfile={FONT_PATH}:text='ABSÜRT KORKU':"
            f"fontsize=26:fontcolor=0x9be8d0:borderw=2:bordercolor=black@0.8:"
            f"box=1:boxcolor=black@0.45:boxborderw=10:"
            f"x=24:y=24[labeled];"
            # Acilis hook basligi (ilk 1.5 saniye, ortada, buyuk)
            f"[labeled]drawtext=fontfile={FONT_PATH}:text='{hook_text}':"
            f"fontsize=68:fontcolor=white:borderw=6:bordercolor=black@0.9:"
            f"box=1:boxcolor=black@0.55:boxborderw=24:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='between(t,0,1.5)'[hooked];"
            # Kapanis sorusu (son 2 saniye) - ortada, YouTube arayuzunun ustunde kalacak yukseklikte
            f"[hooked]drawtext=fontfile={FONT_PATH}:text='{cta_text}':"
            f"fontsize=40:fontcolor=white:borderw=4:bordercolor=black@0.9:"
            f"box=1:boxcolor=black@0.6:boxborderw=16:"
            f"x=(w-text_w)/2:y=h-480:"
            f"enable='between(t,{cta_start:.2f},{duration:.2f})'[cta_done];"
            # Abone/begeni hatirlatmasi - EKRANIN TAM ORTASI, profesyonel koyu-lacivert
            # rozet tasarimi. Hook (0-1.5sn) ve kapanis sorusu (son 2sn) ile CAKISMAMASI
            # icin sadece aradaki bolumde gosterilir.
            f"[cta_done]drawtext=fontfile={FONT_PATH}:text='BEĞENDİYSEN ABONE OLMAYI UNUTMA':"
            f"fontsize=34:fontcolor=white:borderw=2:bordercolor=0x1a3a8f:"
            f"box=1:boxcolor=0x14247a@0.88:boxborderw=30:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='between(t,1.7,{max(duration - 2.3, 1.8):.2f})'[outv]"
        ),
        "-map", "[outv]",
        "-map", "2:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-avoid_negative_ts", "make_zero",
        "-async", "1",
        "-shortest",
        output_path,
    ]
    subprocess.run(final_cmd, check=True)
    print(f"Video render edildi: {output_path}")


SERIF_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
CHANNEL_LABEL = "ZİFİRİ SAATLER"


def wrap_text_safe(text, max_chars_per_line):
    """
    Kelimeleri, her satir belirlenen karakter sinirini asmayacak sekilde
    ac gozlu (greedy) bir algoritmayla satirlara boler. Sabit kelime sayisi
    yerine karakter uzunluguna gore boldugu icin uzun kelimeli basliklarda
    bile ekran disina tasma OLMAZ.
    """
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        add_len = len(w) + (1 if current else 0)
        if current_len + add_len > max_chars_per_line and current:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += add_len
    if current:
        lines.append(" ".join(current))
    return lines


def generate_thumbnail(story_path="output/story.json", output_path="output/thumbnail.jpg"):
    """
    'Yedinci Kat' kanalindaki basarili kapak formatindan ilham alinmistir:
    duz siyah arkaplan + ustte kucuk marka etiketi + carpici renkli HOOK
    ifadesi + altinda buyuk, serif, beyaz ana baslik. Tum metinler karakter
    sayisina gore GUVENLI sekilde satirlara bolunur, ekran disina TASMAZ.
    """
    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)

    title = story["title"]

    # Ana baslik: 76 punto serif fontta, guvenli max ~15 karakter/satir
    # (WIDTH=1080, kenar boslugu dahil - serif bold karakterler genis)
    title_lines = wrap_text_safe(title, max_chars_per_line=15)
    title_lines = title_lines[:5]  # cok uzunsa tasmayi onlemek icin sinirla

    # Hook ifadesi: basligin ilk birkac kelimesi, farkli renk/font, daha kucuk
    # punto (cunku ayni satirda ana baslikla birlikte yer alacak, video ile
    # tutarli olsun diye video hook'uyla ayni mantik kullanilir)
    hook_words = title.split()[:5]
    hook_text = " ".join(hook_words)
    hook_lines = wrap_text_safe(hook_text, max_chars_per_line=20)
    hook_lines = hook_lines[:2]

    TITLE_FONTSIZE = 68
    TITLE_LINE_HEIGHT = 100
    HOOK_FONTSIZE = 42
    HOOK_LINE_HEIGHT = 58

    n_title_lines = len(title_lines)
    n_hook_lines = len(hook_lines)

    total_height = (n_hook_lines * HOOK_LINE_HEIGHT) + 30 + (n_title_lines * TITLE_LINE_HEIGHT)
    start_y = max((HEIGHT // 2) - (total_height // 2) + 60, 260)

    draw_filters = [
        f"drawtext=fontfile={FONT_PATH}:text='{CHANNEL_LABEL}':"
        f"fontsize=34:fontcolor=0xc9a84a:x=(w-text_w)/2:y=110",
        "drawbox=x=(iw-260)/2:y=168:w=260:h=3:color=0xc9a84a@0.9:t=fill",
    ]

    # Hook ifadesi (turuncu/altin vurgu rengi, sans-serif bold)
    y = start_y
    for line in hook_lines:
        line_escaped = line.replace("'", "\u2019").replace(":", "\\:")
        draw_filters.append(
            f"drawtext=fontfile={FONT_PATH}:text='{line_escaped}':"
            f"fontsize={HOOK_FONTSIZE}:fontcolor=0xff9d3d:"
            f"borderw=2:bordercolor=black@0.6:"
            f"x=(w-text_w)/2:y={y}"
        )
        y += HOOK_LINE_HEIGHT

    # Ana baslik (beyaz, serif) - hook'un hemen altinda baslar
    y += 30
    for line in title_lines:
        line_escaped = line.replace("'", "\u2019").replace(":", "\\:")
        draw_filters.append(
            f"drawtext=fontfile={SERIF_FONT_PATH}:text='{line_escaped}':"
            f"fontsize={TITLE_FONTSIZE}:fontcolor=white:"
            f"x=(w-text_w)/2:y={y}"
        )
        y += TITLE_LINE_HEIGHT

    vf_chain = ",".join(draw_filters)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x0a0a0a:s={WIDTH}x{HEIGHT}:d=1",
        "-vf", vf_chain,
        "-frames:v", "1",
        output_path,
    ]
    subprocess.run(cmd, check=True)
    print(f"Kapak (thumbnail) uretildi: {output_path}")


def prepend_thumbnail_intro(
    thumbnail_path="output/thumbnail.jpg",
    main_body_path="output/main_body.mp4",
    output_path="output/final.mp4",
    intro_duration=0.5,
):
    """
    Uretilen statik kapak gorselini, videonun GERCEK ilk 0.5 saniyesi
    olarak ekler. Boylece Studio/mobil'de "ilk kareyi kapak yap" secilse
    bile hep bu tasarim gorunur - ayri bir API kapagina gerek kalmaz.
    """
    intro_path = "output/intro_clip.mp4"

    intro_cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumbnail_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(intro_duration),
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},fps={FPS},format=yuv420p"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-ar", "44100",
        "-shortest",
        intro_path,
    ]
    subprocess.run(intro_cmd, check=True)

    concat_cmd = [
        "ffmpeg", "-y",
        "-i", intro_path,
        "-i", main_body_path,
        "-filter_complex",
        "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-avoid_negative_ts", "make_zero",
        "-async", "1",
        output_path,
    ]
    subprocess.run(concat_cmd, check=True)
    print(f"Kapak videonun basina eklendi: {output_path}")


if __name__ == "__main__":
    generate_thumbnail()          # once kapagi uret (sadece story.json gerekir)
    render()                      # sonra ana videoyu uret (main_body.mp4)
    prepend_thumbnail_intro()     # kapagi videonun basina fiziksel olarak ekle
