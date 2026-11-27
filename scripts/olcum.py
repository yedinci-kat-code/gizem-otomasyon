"""Shorts olcum araci: kamera hareketi, kesmeler, isik/renk ve anlatim temposu.

Kullanim: python scripts/olcum.py video1.mp4 [video2.mp4 ...] --out data/olcum/sonuc.json
Yontem Kodla Ciz'in (github.com/kodlaciz/yumurta-stili, MIT) olcum tanimlarina gore yazildi:
altyazi bandi (yuksekligin %60-80'i) olcume girmez, parlaklik 0-1.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np

W, H = 270, 480  # olcum cozunurlugu (1080x1920'nin 1/4'u)
SCALE_TO_1080 = 1080 / W


def band_mask():
    m = np.ones((H, W), np.uint8) * 255
    m[int(H * 0.60):int(H * 0.80), :] = 0
    return m


def frames(path):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield fps, cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA)
    cap.release()


def measure_video(path):
    mask = band_mask()
    keep = mask > 0
    prev_g, prev_hist = None, None
    n = 0
    fps = 30
    stat = dict(sabit=0, itme=0, cekme=0, kaydirma=0, olculen=0)
    push_speeds, pan_px = [], []
    cuts = []
    y50, y5, contrast, dark, bright, warm_l, cold_l, ikili, sat50 = [], [], [], [], [], [], [], [], []
    for fps, f in frames(path):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], mask, [30, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        # isik / renk (her 3. kare)
        if n % 3 == 0:
            y = g[keep].astype(np.float32) / 255.0
            p = np.percentile(y, [5, 50, 95])
            y5.append(p[0]); y50.append(p[1]); contrast.append(p[2] - p[0])
            dark.append(float((y < 0.08).mean() * 100)); bright.append(float((y > 0.92).mean() * 100))
            hh, ss, vv = hsv[..., 0][keep], hsv[..., 1][keep] / 255.0, hsv[..., 2][keep] / 255.0
            sat = (ss > 0.35) & (vv > 0.2)
            sat50.append(float(np.median(ss)))
            ns = max(int(sat.sum()), 1)
            w = float(((hh >= 5) & (hh <= 25) & sat).sum() / ns * 100)
            c = float(((hh >= 95) & (hh <= 140) & sat).sum() / ns * 100)
            warm_l.append(w); cold_l.append(c); ikili.append(1.0 if (w >= 5 and c >= 5) else 0.0)
        if prev_g is not None:
            corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            diff = float(np.abs(g.astype(np.int16) - prev_g.astype(np.int16))[keep].mean())
            is_cut = corr < 0.55 or diff > 45
            if is_cut:
                cuts.append(n / fps)
            else:
                pts = cv2.goodFeaturesToTrack(prev_g, 300, 0.01, 6, mask=mask)
                if pts is not None and len(pts) >= 12:
                    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev_g, g, pts, None)
                    good = st.reshape(-1) == 1
                    if good.sum() >= 10:
                        M, _ = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC,
                                                           ransacReprojThreshold=1.0)
                        if M is not None:
                            s = float(np.sqrt(M[0, 0] ** 2 + M[1, 0] ** 2))
                            # merkeze gore oteleme (olcek etkisini cikar)
                            cx, cy = W / 2, H / 2
                            tx = M[0, 2] + (M[0, 0] - 1) * cx + M[0, 1] * cy
                            ty = M[1, 2] + M[1, 0] * cx + (M[1, 1] - 1) * cy
                            t = float(np.hypot(tx, ty)) * SCALE_TO_1080
                            stat["olculen"] += 1
                            moved = False
                            if s > 1.0006:
                                stat["itme"] += 1; push_speeds.append((s - 1) * 100); moved = True
                            elif s < 0.9994:
                                stat["cekme"] += 1; moved = True
                            if t > 0.5:
                                stat["kaydirma"] += 1; pan_px.append(t); moved = True
                            if not moved:
                                stat["sabit"] += 1
        prev_g, prev_hist = g, hist
        n += 1
    dur = n / fps if fps else 0
    o = max(stat["olculen"], 1)
    # kesmeleri birlestir (art arda kareler tek kesme)
    merged = []
    for c in cuts:
        if not merged or c - merged[-1] > 0.25:
            merged.append(c)
    shots = [0.0] + merged + [dur]
    shot_len = np.diff(shots) if len(shots) > 1 else np.array([dur])
    return {
        "sn": round(dur, 1),
        "sabit_pct": round(stat["sabit"] / o * 100, 1),
        "itme_pct": round(stat["itme"] / o * 100, 1),
        "cekme_pct": round(stat["cekme"] / o * 100, 1),
        "kaydirma_pct": round(stat["kaydirma"] / o * 100, 1),
        "itme_hizi_pct_kare": round(float(np.median(push_speeds)), 3) if push_speeds else 0,
        "kaydirma_p90_px": round(float(np.percentile(pan_px, 90)), 1) if pan_px else 0,
        "kesme_sayisi": len(merged),
        "ilk5sn_goruntu": 1 + sum(1 for c in merged if c < 5.0),
        "ort_plan_sn": round(float(shot_len.mean()), 2),
        "parlaklik_p50": round(float(np.median(y50)), 3),
        "parlaklik_p5": round(float(np.median(y5)), 3),
        "kontrast": round(float(np.median(contrast)), 3),
        "karanlik_px_pct": round(float(np.median(dark)), 2),
        "parlak_pct": round(float(np.median(bright)), 2),
        "sicak_pct": round(float(np.median(warm_l)), 1),
        "soguk_pct": round(float(np.median(cold_l)), 1),
        "ikili_pct": round(float(np.mean(ikili) * 100), 1),
        "doygunluk_p50": round(float(np.median(sat50)), 3),
    }


_whisper = None


def measure_audio(path):
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        return {"hata": f"whisper yok: {e}"}
    if _whisper is None:
        _whisper = WhisperModel(os.environ.get("OLCUM_WHISPER", "small"), device="cpu", compute_type="int8")
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "16000", wav], check=True)
        import wave
        with wave.open(wav) as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768.0
        segs, _ = _whisper.transcribe(pcm, language="tr", word_timestamps=True, vad_filter=False)
        words = [w for s in segs for w in (s.words or [])]
    if not words:
        return {"kelime": 0}
    start, end = words[0].start, words[-1].end
    gaps = [b.start - a.end for a, b in zip(words, words[1:])]
    span = max(end - start, 0.01)
    long_gaps = [g for g in gaps if g > 0.25]
    first5 = [w for w in words if w.start < 5.0]
    return {
        "kelime": len(words),
        "ilk_kelime_sn": round(start, 2),
        "kelime_sn": round(len(words) / span, 2),
        "ilk5sn_kelime_sn": round(len(first5) / max(min(5.0, end) - start, 0.01), 2),
        "bosluk_pct": round(sum(long_gaps) / span * 100, 1),
        "uzun_bosluk_sayisi": sum(1 for g in gaps if g > 0.5),
        "ilk_cumle": " ".join(w.word.strip() for w in words[:14]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="data/olcum/sonuc.json")
    ap.add_argument("--ses-yok", action="store_true")
    a = ap.parse_args()
    res = {}
    if os.path.exists(a.out):
        try:
            res = json.load(open(a.out, encoding="utf-8"))
        except Exception:
            res = {}
    for v in a.videos:
        name = os.path.splitext(os.path.basename(v))[0]
        print("Olculuyor:", name, flush=True)
        r = measure_video(v)
        if not a.ses_yok:
            r.update(measure_audio(v))
        res[name] = r
        print(json.dumps(r, ensure_ascii=False), flush=True)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
