"""
Zifiri Saatler - Seslendirme Uretici
edge-tts (ucretsiz, Microsoft Edge sesleri) kullanarak Turkce seslendirme uretir.
"""
import asyncio
import json
import time
import edge_tts

VOICE = "tr-TR-AhmetNeural"

RATE = "+10%"   # ~1.1x hiz - daha enerjik/heyecanli giris, senkron duzeltmesi
                # sayesinde artik hiz degisikligi altyazi kaymasi YARATMAZ
PITCH = "-14Hz"  # belirgin sekilde kalin/ciddi ton

MAX_RETRIES = 4
RETRY_DELAY_SECONDS = 8


async def generate_voice(text: str, output_path: str):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)

            word_boundaries = []
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        word_boundaries.append({
                            "text": chunk["text"],
                            "offset": chunk["offset"] / 10_000_000,
                            "duration": chunk["duration"] / 10_000_000,
                        })

            return word_boundaries
        except Exception as e:
            last_error = e
            print(f"Deneme {attempt}/{MAX_RETRIES} basarisiz: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"Seslendirme {MAX_RETRIES} denemeden sonra basarisiz oldu: {last_error}")


if __name__ == "__main__":
    with open("output/story.json", "r", encoding="utf-8") as f:
        story = json.load(f)

    boundaries = asyncio.run(
        generate_voice(story["story"], "output/voice.mp3")
    )

    with open("output/word_timings.json", "w", encoding="utf-8") as f:
        json.dump(boundaries, f, ensure_ascii=False, indent=2)

    print(f"Seslendirme uretildi: output/voice.mp3 ({len(boundaries)} kelime)")
