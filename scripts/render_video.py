"""
Zifiri Saatler - Video Montaj
Ust panel: konuyla ilgili atmosferik arkaplan (Pexels) + beliren altyazi
Alt panel: Pexels'ten cekilen hareketli arkaplan (farkli video)
Ses: edge-tts seslendirme + arkaplan muzigi (dusuk sesle karistirilmis)
"""
import json
import subprocess
import os

WIDTH = 1080
HEIGHT = 1920
TOP_HEIGHT = int(HEIGHT * 0.56)
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


def split_into_sentence_chunks(story_text: str, max_chars_per_line=32):
    import re
    raw_sentences = re.split(r'(?<=[.!?])\s+', story_text.strip())
    raw_sentences = [s.strip() for s in raw_sentences if s.strip()]

    chunks = []
    for sentence in raw_sentences:
        words = sentence.split()
        lines = []
        current_line = []
        current_len = 0
        for w in words:
            add_len = len(w) + (1 if current_line else 0)
            if current_len + add_len > max_chars_per_line and current_line:
                lines.append(" ".join(current_line))
                current_line = [w]
                current_len = len(w)
            else:
                current_line.append(w)
                current_len += add_len
        if current_line:
            lines.append(" ".join(current_line))
        chunks.append("\n".join(lines))
    return chunks


def build_caption_groups_from_words(word_timings, story_text: str):
    sentence_chunks = split_into_sentence_chunks(story_text)
    total_words = sum(len(c.replace("\n", " ").split()) for c in sentence_chunks)

    if len(word_timings) < total_words * 0.5:
        return None

    groups = []
    idx = 0
    for chunk in sentence_chunks:
        n_words = len(chunk.replace("\n", " ").split())
        chunk_words = word_timings[idx: idx + n_words]
        if not chunk_words:
            idx += n_words
            continue
        start = chunk_words[0]["offset"]
        end = chunk_words[-1]["offset"] + chunk_words[-1]["duration"] + 0.2
        groups.append({"text": chunk, "start": start, "end": end})
        idx += n_words
    return groups


def build_caption_groups_from_text(story_text: str, duration: float):
    chunks = split_into_sentence_chunks(story_text)
    if not chunks:
        return []
    weights = [max(len(c.replace("\n", " ")), 5) for c in chunks]
    total_weight = sum(weights)
    groups = []
    t = 0.0
    for chunk, w in zip(chunks, weights):
        seg = duration * (w / total_weight)
        groups.append({"text": chunk, "start": t, "end": t + seg + 0.15})
        t += seg
    return groups


def build_caption_filters(groups):
    filters = []
    for g in groups:
        text = (
            g["text"]
            .replace("\\", "")
            .replace("'", "\u2019")
            .replace(":", "\\:")
            .replace("\n", "\\n")
        )
        y_pos = "(h*0.56)*0.62"
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:text='{text}':"
            f"fontsize=48:fontcolor=white:borderw=4:bordercolor=black@0.85:"
            f"line_spacing=10:x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t,{g['start']:.2f},{g['end']:.2f})'"
        )
    return filters


def render(story_path="output/story.json",
           voice_path="output/voice.mp3",
           background_path="output/background.mp4",
           top_background_path="output/top_background.mp4",
           music_path="output/music.mp3",
           timings_path="output/word_timings.json",
           output_path="output/final.mp4"):

    with open(story_path, "r", encoding="utf-8") as f:
        story = json.load(f)
    with open(timings_path, "r", encoding="utf-8") as f:
        word_timings = json.load(f)

    duration = get_audio_duration(voice_path) + 0.5

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

    if has_music:
        audio_cmd = [
            "ffmpeg", "-y",
            "-i", voice_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex",
            "[1:a]volume=0.12[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "[aout]",
            "-t", str(duration),
            "output/mixed_audio.aac",
        ]
        subprocess.run(audio_cmd, check=True)
        final_audio_path = "output/mixed_audio.aac"
    else:
        final_audio_path = voice_path

    final_cmd = [
        "ffmpeg", "-y",
        "-i", "output/top_panel.mp4",
        "-i", "output/bottom_panel.mp4",
        "-i", final_audio_path,
        "-filter_complex", "[0:v][1:v]vstack=inputs=2[outv]",
        "-map", "[outv]",
        "-map", "2:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
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
