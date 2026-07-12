"""
Zifiri Saatler - Seslendirme Uretici
edge-tts (ucretsiz, Microsoft Edge sesleri) kullanarak Turkce seslendirme uretir.
"""
import asyncio
import json
import edge_tts

# Turkce erkek ses - atmosferik/ciddi ton icin uygun
VOICE = "tr-TR-AhmetNeural"
# Alternatif: "tr-TR-EmelNeural" (kadin ses)

RATE = "-5%"   # hafif yavas, daha gerilimli/dramatik anlatim icin
PITCH = "-2Hz"  # hafif kalin ton


async def generate_voice(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)

    word_boundaries = []
    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"] / 10_000_000,  # 100ns -> saniye
                    "duration": chunk["duration"] / 10_000_000,
                })
    return word_boundaries


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    boundaries = asyncio.run(
        generate_voice(story["story"], "output/voice.mp3")
    )

    with open("output/word_timings.json", "w", encoding="utf-8") as f:
        json.dump(boundaries, f, ensure_ascii=False, indent=2)

    print(f"Seslendirme uretildi: output/voice.mp3 ({len(boundaries)} kelime)")
