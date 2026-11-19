#!/usr/bin/env python3
"""cizgi-short · seslendirmeyi kelime kelime zamanlar.
Kullanım:  python timing.py <proje>
Girdi : <proje>/work/voice.(mp3|wav|m4a)  +  <proje>/script.txt (okunan metnin aynısı)
        isteğe bağlı <proje>/work/alignment.json  (ElevenLabs "with-timestamps" çıktısı: characters + *_times_seconds)
Çıktı : <proje>/work/words.json   [{"w": "kelime", "s": 0.12, "e": 0.48}, ...]
        <proje>/work/phrases.json [{"text": "...", "s":..., "e":..., "w0": i, "w1": j}, ...]
Yöntem sırası: 1) alignment.json  2) faster-whisper / whisper (kuruluysa)  3) sessizlik + hece hizalaması (her yerde çalışır).
"""
import sys, os, json, re, glob, shutil, subprocess, wave
import numpy as np

VOW = set("aeıioöuüAEIİOÖUÜâîûy")
def syl(w):
    d = sum(ch.isdigit() for ch in w)
    if d: return 2 * d + 1          # 1911 -> "bin dokuz yüz on bir" (~7-9 hece)
    n = sum(1 for c in w if c in VOW)
    return max(1, n)

def ffmpeg():
    f = shutil.which("ffmpeg")
    if f: return f
    try:
        import imageio_ffmpeg; return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception: sys.exit("ffmpeg bulunamadı (pip install imageio-ffmpeg)")

def load_audio(path, sr=16000):
    tmp = path + ".16k.wav"
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(sr), tmp], check=True)
    with wave.open(tmp) as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    os.remove(tmp); return x, sr

def norm(w): return re.sub(r"[^\w]", "", w.lower().replace("İ", "i").replace("I", "ı"))

def script_words(txt):
    return [w for w in re.split(r"\s+", txt.strip()) if w]

def phrases_of(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if re.search(r"[.!?…;:,]$", w["w"]) or i == len(words) - 1:
            out.append({"text": " ".join(words[j]["w"] for j in cur), "s": words[cur[0]]["s"], "e": words[cur[-1]]["e"], "w0": cur[0], "w1": cur[-1]}); cur = []
    return out

# 1) ElevenLabs karakter zamanları
def from_alignment(al, sw):
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    toks, cur, s0, e0 = [], "", None, None
    for c, s, e in zip(ch, st, en):
        if c.isspace():
            if cur: toks.append((cur, s0, e0)); cur = ""
            continue
        if not cur: s0 = s
        cur += c; e0 = e
    if cur: toks.append((cur, s0, e0))
    return match(sw, toks)

# 2) whisper
def from_whisper(path):
    try:
        from faster_whisper import WhisperModel
        m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), compute_type="int8")
        segs, _ = m.transcribe(path, word_timestamps=True, language=os.environ.get("LANG_CODE"))
        return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    except Exception:
        pass
    try:
        import whisper
        m = whisper.load_model(os.environ.get("WHISPER_MODEL", "small"))
        r = m.transcribe(path, word_timestamps=True, language=os.environ.get("LANG_CODE"))
        return [(w["word"].strip(), w["start"], w["end"]) for s in r["segments"] for w in s.get("words", [])]
    except Exception:
        return None

def match(sw, toks):
    """senaryo kelimelerini tanınan kelimelere eşle; eşleşmeyenleri komşulardan doldur"""
    import difflib
    a = [norm(w) for w in sw]; b = [norm(t[0]) for t in toks]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    S = [None] * len(sw); E = [None] * len(sw)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): S[blk.a + k] = toks[blk.b + k][1]; E[blk.a + k] = toks[blk.b + k][2]
    # boşlukları doğrusal doldur (hece ağırlıklı)
    i = 0; n = len(sw)
    while i < n:
        if S[i] is not None: i += 1; continue
        j = i
        while j < n and S[j] is None: j += 1
        t0 = E[i - 1] if i > 0 else (toks[0][1] if toks else 0.0)
        t1 = S[j] if j < n else (toks[-1][2] if toks else t0 + 0.4 * (j - i))
        ws = [syl(sw[k]) for k in range(i, j)]; tot = sum(ws); acc = 0
        for k in range(i, j):
            S[k] = t0 + (t1 - t0) * acc / tot; acc += ws[k - i]; E[k] = t0 + (t1 - t0) * acc / tot
        i = j
    return [{"w": w, "s": round(float(s), 3), "e": round(float(e), 3)} for w, s, e in zip(sw, S, E)]

# 3) sessizlik + hece: cümle sınırlarını sessizliklere dinamik programlama ile yasla
def from_energy(x, sr, sw):
    hop = int(sr * 0.01); n = len(x) // hop
    rms = np.sqrt(np.convolve((x[: n * hop].reshape(n, hop) ** 2).mean(1), np.ones(3) / 3, "same") + 1e-12)
    db = 20 * np.log10(rms + 1e-9); thr = max(np.percentile(db, 95) - 30, np.percentile(db, 10) + 6)
    sp = db > thr
    def runs(m):
        r, i = [], 0
        while i < len(m):
            j = i
            while j < len(m) and m[j] == m[i]: j += 1
            r.append([bool(m[i]), i, j]); i = j
        return r
    for v, a, b in runs(sp):
        if v and b - a < 5: sp[a:b] = False          # 50 ms altı gürültü
    gaps = [(a / 100, b / 100) for v, a, b in runs(sp) if not v and a > 0 and b < len(sp) and b - a >= 12]  # >=120 ms sessizlik
    on = np.where(sp)[0]; t0, t1 = (on[0] / 100, on[-1] / 100 + 0.01) if len(on) else (0, len(x) / sr)
    # cümle parçaları
    ph, cur = [], []
    for i, w in enumerate(sw):
        cur.append(i)
        if re.search(r"[.!?…;:,]$", w) or i == len(sw) - 1: ph.append(cur); cur = []
    W = [sum(syl(sw[i]) for i in p) for p in ph]; tot = sum(W); P = len(ph)
    gl = [g for g in gaps if t0 < g[0] < t1]
    voiced = (t1 - t0) - sum(b - a for a, b in gl); rate = tot / max(voiced, 0.1)
    def vdur(a, b):  # a..b arası konuşulan süre
        return (b - a) - sum(max(0, min(b, g1) - max(a, g0)) for g0, g1 in gl)
    def inner_pen(a, b):  # parçanın içinde kalan uzun sessizlikler cezası
        return sum(max(0, (min(b, g1) - max(a, g0)) - 0.25) * 3 for g0, g1 in gl if g0 > a + 0.05 and g1 < b - 0.05)
    strong = [bool(re.search(r"[.!?…]$", sw[p[-1]])) for p in ph]
    def cost(k, a, b):
        e = W[k] / rate; d = vdur(a, b); return ((d - e) / max(e, 0.25)) ** 2 + inner_pen(a, b)
    def bonus(k, j):  # cümle sonu uzun sessizliğe, virgül kısa sessizliğe düşsün
        if j >= len(gl): return 0
        L = gl[j][1] - gl[j][0]; return -L * (2.5 if strong[k] else 0.8)
    # dp[k][j]: k. parça j. sessizlikte bitiyor (j = len(gl) -> ses sonu)
    G = len(gl); INF = 1e18
    ends = [g[0] for g in gl] + [t1]; starts = [t0] + [g[1] for g in gl]
    import math
    dp = [[INF] * (G + 1) for _ in range(P)]; bk = [[-1] * (G + 1) for _ in range(P)]
    for j in range(G + 1): dp[0][j] = cost(0, t0, ends[j]) + bonus(0, j)
    for k in range(1, P):
        for j in range(G + 1):
            best, bj = INF, -1
            for i in range(j):
                if dp[k - 1][i] >= INF: continue
                c = dp[k - 1][i] + cost(k, gl[i][1], ends[j]) + bonus(k, j)
                if c < best: best, bj = c, i
            dp[k][j], bk[k][j] = best, bj
    if P > G + 1 or dp[P - 1][G] >= INF:   # yeterli sessizlik yok: orantılı dağıt
        bounds = []; acc = 0
        for k in range(P): a = t0 + (t1 - t0) * acc / tot; acc += W[k]; bounds.append((a, t0 + (t1 - t0) * acc / tot))
    else:
        js = [G]
        for k in range(P - 1, 0, -1): js.append(bk[k][js[-1]])
        js = js[::-1]; bounds = []
        for k in range(P): a = t0 if k == 0 else gl[js[k - 1]][1]; bounds.append((a, ends[js[k]]))
    out = []
    for k, p in enumerate(ph):
        a, b = bounds[k]; segs = [[a, b]]
        for g0, g1 in gl:  # parçanın içindeki sessizlikleri çıkar
            if a < g0 and g1 < b:
                last = segs[-1]; segs[-1] = [last[0], g0]; segs.append([g1, b])
        vt = sum(e - s for s, e in segs)
        def v2t(v):
            acc = 0
            for s0, e0 in segs:
                if acc + (e0 - s0) >= v - 1e-9: return s0 + (v - acc)
                acc += e0 - s0
            return segs[-1][1]
        ws = [syl(sw[i]) for i in p]; wt = sum(ws); acc = 0
        for i, kk in zip(p, ws):
            s0 = v2t(vt * acc / wt); acc += kk; e0 = v2t(vt * acc / wt)
            out.append({"w": sw[i], "s": round(float(s0), 3), "e": round(float(e0), 3)})
    return out

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    proj = os.path.abspath(sys.argv[1]); work = os.path.join(proj, "work"); os.makedirs(work, exist_ok=True)
    voice = next((p for p in sorted(glob.glob(os.path.join(work, "voice.*"))) if not p.endswith(".json")), None)
    if not voice: sys.exit("work/voice.mp3 (veya .wav) yok")
    sp = os.path.join(proj, "script.txt")
    if not os.path.exists(sp): sys.exit("script.txt yok: okunan metni buraya yaz (Claude sesi duyamaz, zamanlama metinle yapılır)")
    sw = script_words(open(sp, encoding="utf-8").read())
    al = os.path.join(work, "alignment.json"); words = None; how = ""
    if os.path.exists(al):
        words = from_alignment(json.load(open(al, encoding="utf-8")), sw); how = "ElevenLabs zaman damgaları"
    if words is None and not os.environ.get("NO_WHISPER"):
        toks = from_whisper(voice)
        if toks: words = match(sw, toks); how = "whisper"
    x, sr = load_audio(voice)
    if words is None: words = from_energy(x, sr, sw); how = "sessizlik + hece hizalaması"
    dur = len(x) / sr
    json.dump(words, open(os.path.join(work, "words.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    ph = phrases_of(words)
    json.dump(ph, open(os.path.join(work, "phrases.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"yöntem: {how} · ses {dur:.2f} sn · {len(words)} kelime · {len(ph)} cümle parçası")
    for i, p in enumerate(ph): print(f"  P{i:02d} {p['s']:6.2f}-{p['e']:6.2f}  kare {round(p['s']*30):4d}-{round(p['e']*30):4d}  w{p['w0']}-{p['w1']}  {p['text']}")
    print(f"toplam kare (30 fps): {round((dur + 0.7) * 30)}")

if __name__ == "__main__":
    main()
