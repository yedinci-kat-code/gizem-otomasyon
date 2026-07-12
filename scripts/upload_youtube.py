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

    top_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x120a1a:s={WIDTH}x{TOP_HEIGHT}:d={duration}",
        "-vf", caption_chain if caption_filters else "null",
        "-t", str(duration),
        "output/top_panel.mp4",
    ]
    subprocess.run(top_cmd, check=True)

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


def generate_thumbnail(story_path="output/story.json", output_path="output/thumbnail.jpg"):
    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)

    title = story["title"].replace("'", "\u2019").replace(":", "\\:")

    words = title.split()
    mid = len(words) // 2 + (len(words) % 2)
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    draw1 = (
        f"drawtext=fontfile={FONT_PATH}:text='{line1}':"
        f"fontsize=90:fontcolor=white:borderw=6:bordercolor=black@0.9:"
        f"x=(w-text_w)/2:y=(h/2)-110"
    )
    draw2 = (
        f"drawtext=fontfile={FONT_PATH}:text='{line2}':"
        f"fontsize=90:fontcolor=white:borderw=6:bordercolor=black@0.9:"
        f"x=(w-text_w)/2:y=(h/2)+10"
        if line2 else "null"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x120a1a:s={WIDTH}x{HEIGHT}:d=1",
        "-vf", f"{draw1},{draw2}" if line2 else draw1,
        "-frames:v", "1",
        output_path,
    ]
    subprocess.run(cmd, check=True)
    print(f"Kapak (thumbnail) uretildi: {output_path}")


if __name__ == "__main__":
    render()
    generate_thumbnail()
