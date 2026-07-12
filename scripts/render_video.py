"""
Zifiri Saatler - Video Montaj
Ust panel: atmosferik gradient + kelime kelime beliren altyazi
Alt panel: Pexels'ten cekilen hareketli arkaplan
Ses: edge-tts ile uretilen seslendirme
"""
import json
import subprocess
import os

WIDTH = 1080
HEIGHT = 1920
TOP_HEIGHT = int(HEIGHT * 0.56)
BOTTOM_HEIGHT = HEIGHT - TOP_HEIGHT

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


def build_caption_filters(word_timings, video_offset_y=0):
    """
    Kelime kelime beliren altyazi icin ffmpeg drawtext filtrelerini olusturur.
    Basitlik icin kelimeleri ~4-6 kelimelik gruplar halinde birlestirir,
    her grup ekranda kendi zaman araliginda gorunur.
    """
    groups = []
    current = []
    current_start = None
    for w in word_timings:
        if current_start is None:
            current_start = w["offset"]
        current.append(w["text"])
        if len(current) >= 5:
            groups.append({
                "text": " ".join(current),
                "start": current_start,
                "end": w["offset"] + w["duration"] + 0.15,
            })
            current = []
            current_start = None
    if current:
        last = word_timings[-1]
        groups.append({
            "text": " ".join(current),
            "start": current_start,
            "end": last["offset"] + last["duration"] + 0.3,
        })

    filters = []
    for g in groups:
        text = (
            g["text"]
            .replace("\\", "")
            .replace("'", "\u2019")
            .replace(":", "\\:")
        )
        y_pos = f"(h*0.56)*0.68"
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:text='{text}':"
            f"fontsize=52:fontcolor=white:borderw=4:bordercolor=black@0.8:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t,{g['start']:.2f},{g['end']:.2f})'"
        )
    return filters


def render(story_path="output/story.json",
           voice_path="output/voice.mp3",
           background_path="output/background.mp4",
           timings_path="output/word_timings.json",
           output_path="output/final.mp4"):

    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)
    with open(timings_path, "r", encoding="utf-8") as f:
        word_timings = json.load(f)

    duration = get_audio_duration(voice_path) + 0.5

    caption_filters = build_caption_filters(word_timings)
    caption_chain = ",".join(caption_filters) if caption_filters else "null"

    # Ust panel: koyu atmosferik gradient (renkli gecis) uzerine altyazi
    # Alt panel: pexels videosu, loop'lanip kirpiliyor
    filter_complex = (
        f"color=c=0x0a0812:s={WIDTH}x{TOP_HEIGHT}:d={duration}[topbg];"
        f"[topbg]{caption_chain}[topfinal];"
        f"[1:v]scale={WIDTH}:{BOTTOM_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{BOTTOM_HEIGHT},setpts=PTS-STARTPTS[botv];"
        f"[topfinal][botv]vstack=inputs=2[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{TOP_HEIGHT}",  # dummy, degistirilecek
    ]

    # Basit ve saglam yontem: iki ayri asama
    # 1) Ust paneli (altyazili) ayri bir video olarak render et
    top_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x120a1a:s={WIDTH}x{TOP_HEIGHT}:d={duration}",
        "-vf", caption_chain if caption_filters else "null",
        "-t", str(duration),
        "output/top_panel.mp4",
    ]
    subprocess.run(top_cmd, check=True)

    # 2) Alt paneli (arkaplan videosu) hazirlayip, ust panelle vstack et + sesi ekle
    final_cmd = [
        "ffmpeg", "-y",
        "-i", "output/top_panel.mp4",
        "-stream_loop", "-1", "-i", background_path,
        "-i", voice_path,
        "-filter_complex",
        (
            f"[1:v]scale={WIDTH}:{BOTTOM_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{BOTTOM_HEIGHT}[botv];"
            f"[0:v][botv]vstack=inputs=2[outv]"
        ),
        "-map", "[outv]",
        "-map", "2:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest",
        output_path,
    ]
    subprocess.run(final_cmd, check=True)
    print(f"Video render edildi: {output_path}")


if __name__ == "__main__":
    render()
