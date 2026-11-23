"""
Unfrozen History - uzun video (8-12 dk) senaryo + cekim plani (Gemini).
Kanal: Ingilizce kis/hayatta kalma tarihi; 55+ erkek izleyici (ABD/UK/Kanada).
Format: soba basinda oturan yasli KURGUSAL anlatici (olayi yasamis siradan biri) anlatir; acilis 2. tekil sahis
("It's 1897. You're twenty-two..."), sonra "that young man was me" ile anlatici devralir. Olaylar/tarih/rakamlar gercek.
Cikti: output_uzun/story.json  (beats = okunacak metnin tamami + her vurusun cekimi)
Konu: TOPIC ortam degiskeni > uzun/topics.json sirasindaki ilk islenmemis konu. Tekrar korumasi: data/uzun_history.json
"""
import json
import os
import re
import sys
import difflib
import google.generativeai as genai

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output_uzun")
HISTORY = os.path.join(ROOT, "data", "uzun_history.json")
TOPICS = os.path.join(ROOT, "uzun", "topics.json")

SHOTS = {"host", "host_close", "wide", "character", "close", "two", "run", "march", "huddle", "crowd", "object"}
LOCS = {"cabin", "forest", "trench", "ice", "camp", "pass", "frontier", "town", "harbor", "prairie", "river", "rapids", "boats", "hq"}
PRESETS = {"soldier", "officer", "explorer", "sailor", "miner", "prospector", "mountie", "townsman", "worker", "farmer",
           "doctor", "woman", "teacher", "elder", "elderwoman", "boy", "girl"}
MOODS = {"scared", "shocked", "curious", "sly", "sad", "happy", "angry", "thoughtful", "telling", "nervous", "determined",
         "proud", "amazed", "sleepy", "cold", "tired", "hopeful", "relieved"}

SYSTEM = """You are the head writer AND cartoon director of the YouTube channel "Unfrozen History": true stories of
people who survived the coldest moments in history (winter wars, polar expeditions, blizzards, frozen sieges, gold rushes).
Audience: men 55+, USA/UK/Canada. They love real history told plainly, with heart, by someone who was there.
The video is a warm, hand-drawn-looking 2D/3D CARTOON (not realistic), 8 to 11 minutes long.

FORMAT (always):
- The narrator is a FICTIONAL ordinary person who lived through the event (a private, a miner, a nurse, a sailor),
  now old, telling the story by a wood stove in his cabin. He is never a real historical person.
- OPENING (first 1-2 beats, max 25 words): second person, no intro, drop the viewer in:
  "It's July 1897. You're twenty-two, and you just read a headline: a ton of gold has arrived in Seattle."
  Then within the first 30 seconds: a clear promise of what they'll see, and the narrator reveals himself
  ("That young fool was me. My name is ..."). The narrator name is ordinary (e.g. Walt Becker).
- BODY: chronological, concrete, physical details (cold, food, gear, distances, prices, weather). 5 to 7 chapters.
  Every chapter opens with a "card" (title + sub). Keep tension: each chapter ends on a small open question.
- Around 40% of the way in: one beat asks the viewer a simple question to answer in the comments.
- Near the end: one CTA beat (cta: true) with this exact meaning in your own words: "If you've stayed with me this far,
  leave a like and subscribe; that's how I know you want more stories like this one." Never use the word "kill".
- LAST beat: back by the stove (host_close), a quiet reflective line that echoes the opening.

ACCURACY (red lines):
- Only well documented facts: dates, places, numbers, prices, distances, weather. If unsure, stay general.
- STRICT CHRONOLOGY: every real event appears in its true order and season (e.g. an avalanche of April 1898 can
  never happen before December 1897 in the story). The narrator's personal timeline must fit the real dates.
- INTERNAL CONSISTENCY: a distance, number or price said twice must be the same both times.
- NEVER invent a named official, officer or historical figure. A real person may be named only if he really held
  that role at that place and time (e.g. Superintendent Sam Steele of the North-West Mounted Police); otherwise say
  "a Mountie", "the officer", "a pilot". Invented characters are only the narrator and his ordinary companions.
- Real historical people may be mentioned and shown as cartoon characters, but give them NO invented quotes;
  only famous, documented quotes.
- No gore, no cruelty in detail, no hate symbols, no politics of today. Respectful about death.
- Write numbers as words ("eighteen ninety-seven", "two thousand"), for the voice.

LENGTH: 1300 to 1600 words in total (spoken slowly, about 9-11 minutes). 75 to 110 beats.
Each beat = 1 to 3 short sentences (8 to 30 words). Sentences short and spoken, past tense, "I"/"we".

SHOT PLAN - fields of every beat:
- text: the narration (the concatenation of all beats is the whole script).
- shot: one of
  host (old narrator by the stove, talking to us; use 6-10 times, never twice in a row, never more than 12 beats apart),
  host_close (ONLY the last beat), wide (place establishing shot, people small), character (one person, medium),
  close (one person's face reaction), two (two people), run (someone running/fleeing in snow),
  march (a line of people trudging through snow: columns, treks, climbs, retreats),
  huddle (people huddled around a fire/stove), crowd (many people in a town/camp),
  object (a document/map/sign close-up with a 1-3 word label, e.g. "ONE TON", "$1 A POUND", "1897"; use 4-8 times).
- loc: cabin (only for host beats), forest, trench (foxholes/sandbags), ice (pack ice with a frozen wooden ship),
  camp (tents + campfire on snow), pass (steep snowy mountain pass), frontier (gold-rush wooden town),
  town (stone European town in snow), harbor (pier, sheds, icy water, whaling station / port),
  prairie (open snowy plain, farmhouse, schoolhouse), river (FROZEN river / ice road / frozen lake),
  rapids (OPEN fast water in a narrow rock canyon; our people stand in a wooden scow boat),
  boats (OPEN thawed lake/river with many small handmade boats; our people stand in their scow), hq (office/command room with map table).
  The picture must match the words: a beat about boats, rapids or open water uses rapids/boats, never forest.
  Use at least 5 different story locations; never more than 6 beats in a row in the same location.
- who: cast keys shown in the beat (["A"] or ["A","B"]); empty for host/object/wide-without-people.
- mood: scared, shocked, curious, sly, sad, happy, angry, thoughtful, telling, nervous, determined, proud, amazed,
  sleepy, cold, tired, hopeful, relieved.   (two/run may add mood2 for the second person)
- action (optional): walk, run, flee, stand, point, look, hide, sit, sleep, wave, talk, shiver, march.
- fx (optional, at most every 3rd beat): question, exclaim, sweat, idea, puff, sparkle, hearts, anger, zzz, money, dust.
- prop (optional, held by who[0]): lantern, letter, key, gold, coin, scroll, paper, magnifier, pen, cup.
- label + obj: ONLY for shot=object; obj is "map", "newspaper" or "sign".
- light (optional): snowday, snownight, blizzard, dawn, polar, stove, lamp, spring. Use blizzard for storms.
- season: "winter" (snow on the ground, falling snow) or "thaw" (late spring / summer: no snow, mud and grass).
  Set it from the REAL month of the moment told (e.g. May-September in the Yukon = thaw). Default winter.
- card (optional): {"title": "Chapter title", "sub": "Chapter 2 · Place, Year"} on the first beat of each chapter.
- cta: true on the CTA beat only (shot host).

CAST: up to 4 characters A, B, C, D. Each: {"preset": one of soldier, officer, explorer, sailor, miner, prospector,
mountie, townsman, worker, farmer, doctor, woman, teacher, elder, elderwoman, boy, girl, "name": "...", "color": "#hex optional"}.
A = the narrator as a young man (pick the preset of his role). host = the narrator old, by the stove (no cast entry).
crowd: the preset that fits background people (e.g. "miner").

ALSO WRITE (YouTube):
- title: 50-70 chars, curiosity, answer not given, plain words a 60-year-old would click ("...: How Ordinary Men Survived ...").
- title_alt: a second, different title for A/B testing.
- thumb_hook: 2-5 words, huge text on the first seconds and on the thumbnail (e.g. "A TON OF GEAR").
- description: 3 short paragraphs (hook, what you'll see, question for comments). No chapters, no links.
- tags: 15-20 search tags.
- pinned_comment: one question for viewers.
- sources: 4-6 real, well-known books or archives about the topic (author, title, year).

Output ONLY this JSON:
{"topic": "...", "narrator_name": "...", "title": "...", "title_alt": "...", "thumb_hook": "...", "description": "...",
 "tags": ["..."], "pinned_comment": "...", "sources": ["..."], "crowd": "miner",
 "cast": {"A": {"preset": "miner", "name": "Walt (young)"}},
 "beats": [{"text": "...", "shot": "wide", "loc": "frontier", "who": ["A"], "mood": "curious", "card": {"title": "...", "sub": "..."}}, ...]}"""


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def pick_topic(history):
    env = (os.environ.get("TOPIC") or "").strip()
    if env:
        return {"topic": env, "hint": ""}
    done = {h.get("topic", "").lower() for h in history}
    for t in load(TOPICS, []):
        if t["topic"].lower() not in done:
            return t
    sys.exit("HATA: uzun/topics.json icinde islenmemis konu kalmadi")


def normalize(d):
    beats = [b for b in d.get("beats", []) if isinstance(b, dict) and str(b.get("text", "")).strip()]
    if len(beats) < 60:
        raise ValueError(f"cok az beat ({len(beats)}), en az 75 yaz")
    cast = {k: v for k, v in (d.get("cast") or {}).items() if k in ("A", "B", "C", "D") and isinstance(v, dict)}
    for v in cast.values():
        if v.get("preset") not in PRESETS:
            v["preset"] = "worker"
    for b in beats:
        b["text"] = " ".join(str(b["text"]).split())
        if b.get("shot") not in SHOTS:
            b["shot"] = "wide"
        if b["shot"] == "host_close" and b is not beats[-1]:
            b["shot"] = "host"
        if b["shot"] == "host":
            b["loc"] = "cabin"
        elif b.get("loc") not in LOCS or b.get("loc") == "cabin":
            b["loc"] = "forest"
        b["who"] = [w for w in (b.get("who") or []) if w in cast]
        b["season"] = "thaw" if str(b.get("season", "")).lower() in ("thaw", "spring", "summer", "autumn") else "winter"
        if b["loc"] in ("rapids", "boats"):
            b["season"] = "thaw"
        if b.get("mood") not in MOODS:
            b.pop("mood", None)
        if b["shot"] == "object" and not b.get("label"):
            b["shot"] = "wide"
    beats[-1]["shot"], beats[-1]["loc"] = "host_close", "cabin"
    # anlatici arka arkaya gelmesin
    for prev, b in zip(beats, beats[1:]):
        if b["shot"] == "host" and prev["shot"] == "host":
            b["shot"], b["loc"] = "wide", next((x["loc"] for x in beats if x["loc"] != "cabin"), "forest")
    if not any(b["shot"] == "host" for b in beats[:5]):
        raise ValueError("anlatici ilk 5 beat icinde kendini tanitmali (shot=host)")
    if not any(b.get("cta") for b in beats):
        raise ValueError("cta: true olan abone cagrisi beat'i yok")
    words = sum(len(b["text"].split()) for b in beats)
    if not 1150 <= words <= 1850:
        raise ValueError(f"metin {words} kelime; 1300-1600 olmali")
    locs = {b["loc"] for b in beats if b["loc"] != "cabin"}
    if len(locs) < 4:
        raise ValueError("en az 5 farkli hikaye mekani kullan")
    if " kill" in " " + " ".join(b["text"].lower() for b in beats if b.get("cta")):
        raise ValueError("CTA'da 'kill' kelimesi yasak")
    d["beats"], d["cast"] = beats, cast
    d["story"] = " ".join(b["text"] for b in beats)
    d["word_count"] = words
    return d


FACTCHECK = """You are a strict history fact-checker for a documentary channel. You get a numbered narration script
written by a fictional first-person narrator about a real event. The narrator and his ordinary companions are fictional
(that is allowed); everything else must be historically correct.
Find EVERY problem of these kinds:
1. Wrong date, place, number, price, distance, temperature, or a claim stronger than the sources support.
2. Chronology: a real event placed before/after where it really happened relative to the narrator's timeline.
3. Internal contradictions (same distance/number given differently in two places).
4. Named real people: wrong role, wrong place, wrong time, or a person who did not exist (invented names of officials).
5. Invented quotes put in the mouth of a real person.
6. Anachronisms (objects, words, technology that did not exist then).
7. PICTURE vs WORDS: each line shows [loc, season]. Locations: forest, trench, ice (pack ice + frozen ship), camp (tents),
   pass (steep snowy climb), frontier (wooden gold-rush town), town (European stone town), harbor (pier, ships, port),
   prairie (snowy plain, farm), river (FROZEN river/lake), rapids (open whitewater canyon, people in a boat),
   boats (open thawed lake with many boats), hq (office), cabin (narrator by the stove). season: winter = snow, thaw = no snow.
   If the place or season shown contradicts the narration (boats in a forest, snow in a July scene, open water shown frozen),
   report it with "loc" and/or "season" set to the right value (the "fix" text may then repeat the original text).
For each problem return a corrected replacement for the WHOLE beat text: same voice, same length (+-20%), numbers
written as words, keeping the story flowing with the beats before and after. Prefer making a claim general over guessing.
If an event is in the wrong order, rewrite that beat so it no longer claims the event at that moment (e.g. mention it
as something that happened later: "That April, an avalanche..." only if the timeline allows, or drop the event).
Output ONLY JSON: {"issues": [{"beat": 12, "problem": "...", "fix": "full corrected beat text", "loc": "optional", "season": "optional"}]}.
Empty list if none."""


def fact_check(d, topic):
    """Ikinci Gemini gecisi: tarih/kronoloji/tutarlilik/isim denetimi; hatali beat'ler duzeltilmis metinle degisir."""
    names = [n for n in dict.fromkeys([os.environ.get("GEMINI_CHECK_MODEL", ""), os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")]) if n]
    log = []
    for rnd in range(1, 7):
        script = "\n".join(f"{i} [{'NARRATOR AT STOVE (any text is fine here, never report its picture)' if b['shot'].startswith('host') else b['loc'] + ', ' + b.get('season', 'winter')}]: {b['text']}"
                            for i, b in enumerate(d["beats"]))
        res = None
        for name in [n for n in names for _ in range(3)]:  # her model 3 deneme (bozuk JSON olursa tekrar)
            try:
                m = genai.GenerativeModel(name, system_instruction=FACTCHECK,
                                          generation_config={"response_mime_type": "application/json", "temperature": 0.1,
                                                             "max_output_tokens": 20000})
                txt = m.generate_content(f"Event: {topic}\n\nSCRIPT:\n{script}").text.strip()
                if txt.startswith("```"):
                    txt = txt.split("```")[1].removeprefix("json")
                res = json.JSONDecoder().raw_decode(txt[txt.find("{"):])[0].get("issues", [])
                break
            except Exception as e:
                print(f"denetci {name} hata: {e}")
        if res is None:
            raise RuntimeError("tarih denetcisi calismadi")
        res = [x for x in res if isinstance(x, dict) and isinstance(x.get("beat"), int) and 0 <= x["beat"] < len(d["beats"])
               and str(x.get("fix", "")).strip()]
        # anlatici (soba basi) cekimlerinde resim itirazi gecersiz; metin degismiyorsa ve mekan/mevsim de degismiyorsa sorun degil
        def visual_only(x):
            return " ".join(str(x["fix"]).split()) == d["beats"][x["beat"]]["text"]
        text_issues = [x for x in res if not visual_only(x)]
        vis = [x for x in res if visual_only(x) and not d["beats"][x["beat"]]["shot"].startswith("host")]
        print(f"tarih denetimi tur {rnd}: {len(text_issues)} metin sorunu, {len(vis)} resim notu")
        for x in vis:  # resim notlari: mekan/mevsim uygulanir, akisi durdurmaz
            b = d["beats"][x["beat"]]
            season = x.get("season")
            if season not in ("winter", "thaw"):
                pr = str(x.get("problem", "")).lower()
                season = "thaw" if re.search(r"\b(thaw|spring|summer|autumn|no snow)\b", pr) and b.get("season") != "thaw" else None
            changed = []
            if x.get("loc") in LOCS and x["loc"] not in ("cabin", b["loc"]):
                changed.append(f"mekan {b['loc']}->{x['loc']}"); b["loc"] = x["loc"]
            if season and season != b.get("season"):
                changed.append(f"mevsim {b.get('season')}->{season}"); b["season"] = season
            if b["loc"] in ("rapids", "boats"):
                b["season"] = "thaw"
            if changed:
                print(f"  beat {x['beat']} resim: {', '.join(changed)}")
                log.append({"round": rnd, "beat": x["beat"], "problem": x.get("problem", ""), "old": "(resim)", "new": ", ".join(changed)})
        if not text_issues:
            break
        for x in text_issues:
            b = d["beats"][x["beat"]]
            print(f"  beat {x['beat']}: {x.get('problem', '')}\n    eski: {b['text']}\n    yeni: {x['fix']}")
            log.append({"round": rnd, "beat": x["beat"], "problem": x.get("problem", ""), "old": b["text"], "new": x["fix"]})
            b["text"] = " ".join(str(x["fix"]).split())
            if x.get("loc") in LOCS and not b["shot"].startswith("host") and x["loc"] != "cabin":
                b["loc"] = x["loc"]
            if x.get("season") in ("winter", "thaw"):
                b["season"] = x["season"]
            if b["loc"] in ("rapids", "boats"):
                b["season"] = "thaw"
    else:
        raise RuntimeError("6 turda da tarih hatasi kaldi")
    d["fact_check"] = log
    d["story"] = " ".join(b["text"] for b in d["beats"])
    d["word_count"] = sum(len(b["text"].split()) for b in d["beats"])
    return d


OVERRIDE = os.path.join(ROOT, "uzun", "story_override.json")


def main():
    # elle denetlenmis senaryo varsa (uzun/story_override.json) Gemini atlanir; metin oldugu gibi kullanilir
    if os.path.exists(OVERRIDE) and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":  # yalnizca push testleri
        d = normalize(json.load(open(OVERRIDE, encoding="utf-8")))
        os.makedirs(OUT, exist_ok=True)
        json.dump(d, open(os.path.join(OUT, "story.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"plan (elle denetlenmis): {d['title']} · {len(d['beats'])} beat · {d['word_count']} kelime")
        return
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("HATA: GEMINI_API_KEY yok")
    genai.configure(api_key=key)
    history = load(HISTORY, [])
    topic = pick_topic(history)
    model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"), system_instruction=SYSTEM,
                                  generation_config={"response_mime_type": "application/json", "temperature": 0.8,
                                                     "max_output_tokens": 40000})
    done = ", ".join(h["topic"] for h in history if h.get("topic")) or "none"
    prompt = (f"Topic: {topic['topic']}\n{topic.get('hint', '')}\n"
              f"Already made (do not repeat these stories): {done}\nWrite the full plan now.")
    err = None
    for attempt in range(1, 5):
        try:
            ask = prompt if not err else prompt + f"\n\nPREVIOUS ATTEMPT REJECTED: {err}. Fix exactly that."
            txt = model.generate_content(ask).text.strip()
            if txt.startswith("```"):
                txt = txt.split("```")[1].removeprefix("json")
            d = normalize(json.loads(txt))
            for h in history:
                if difflib.SequenceMatcher(None, d["title"].lower(), h.get("title", "").lower()).ratio() > 0.75:
                    raise ValueError("baslik eski bir videoya cok benziyor")
            break
        except Exception as e:
            err = e
            print(f"deneme {attempt}/4 basarisiz: {e}")
    else:
        sys.exit(f"HATA: gecerli plan uretilemedi: {err}")
    d["topic"] = topic["topic"]
    d = fact_check(d, topic["topic"])
    os.makedirs(OUT, exist_ok=True)
    json.dump(d, open(os.path.join(OUT, "story.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"plan: {d['title']} · {len(d['beats'])} beat · {d['word_count']} kelime")


if __name__ == "__main__":
    main()
