#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audio.py - cizgi-short ses motoru: kodla sentezlenen müzik + SFX + mix.

Kullanım:
  python audio.py <proje>            sound.json -> work/music.wav, work/sfx.wav, out/mix.wav
  python audio.py --demo <klasör>    tüm müzik stilleri + tüm SFX'ler için dinleme dosyaları

Gereksinim: Python 3.9+, numpy. Ses dosyasını çözmek için ffmpeg (PATH veya imageio_ffmpeg).
Her şey kodla üretilir; örnek dosya yok, indirme yok. Çıktı deterministiktir (sabit seed).
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
import wave

import numpy as np

SR = 48000


# ---------------------------------------------------------------- yardımcılar
def db2lin(d):
    return 10.0 ** (d / 20.0)


def lin2db(x):
    return 20.0 * math.log10(max(float(x), 1e-12))


def mtof(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


def nz(n, sd):
    return np.random.RandomState(sd).standard_normal(n)


def decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def fftconv(x, h):
    n = len(x) + len(h) - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:n]


def lp1(x, fc):
    """Tek kutuplu alçak geçiren (üstel çekirdekle FFT evrişimi)."""
    a = math.exp(-2.0 * math.pi * fc / SR)
    L = int(min(len(x), 8.0 / (1.0 - a))) + 1
    h = (1.0 - a) * a ** np.arange(L)
    return fftconv(np.asarray(x, dtype=np.float64), h)[:len(x)]


def hpf(x, fc):
    return x - lp1(x, fc)


def bpf(x, lo, hi):
    return lp1(hpf(x, lo), hi)


def svf(x, fc, q=0.5, mode="bp"):
    """Zamanla değişen state-variable filtre (kısa SFX'ler için döngü)."""
    f = (2.0 * np.sin(np.pi * np.minimum(fc, SR * 0.2) / SR)).tolist()
    xs = np.asarray(x, dtype=np.float64).tolist()
    out = [0.0] * len(xs)
    low = band = 0.0
    for i, xi in enumerate(xs):
        low += f[i] * band
        high = xi - low - q * band
        band += f[i] * high
        out[i] = band if mode == "bp" else low
    return np.array(out)


def edges(x, att=0.002, rel=0.01):
    x = np.array(x, dtype=np.float64)
    a = min(int(att * SR), len(x) // 2)
    r = min(int(rel * SR), len(x) // 2)
    if a > 0:
        x[:a] *= np.linspace(0, 1, a)
    if r > 0:
        x[-r:] *= np.linspace(1, 0, r)
    return x


def peak_norm(x, p=1.0):
    m = np.abs(x).max()
    return x * (p / m) if m > 1e-12 else x


def put(buf, sig, idx, g=1.0):
    if idx >= len(buf) or idx + len(sig) <= 0:
        return
    a = max(0, -idx)
    b = min(len(sig), len(buf) - idx)
    buf[idx + a: idx + b] += sig[a:b] * g


def rms_gated(x, abs_db=-50.0, frame=960, rel_db=None):
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    p = (x ** 2).mean(axis=0)
    nf = len(p) // frame
    if nf == 0:
        return float(math.sqrt(p.mean())) if len(p) else 0.0
    fp = p[:nf * frame].reshape(nf, frame).mean(axis=1)
    thr = 10.0 ** (abs_db / 10.0)
    if rel_db is not None:
        thr = max(thr, fp.max() * 10.0 ** (rel_db / 10.0))
    k = fp[fp >= thr]
    if len(k) == 0:
        return float(math.sqrt(fp.mean()))
    return float(math.sqrt(k.mean()))


def saw(f, n, ph0=0.0):
    return 2.0 * ((ph0 + f * np.arange(n) / SR) % 1.0) - 1.0


# ---------------------------------------------------------------- reverb
def comb(x, D, g):
    y = x.copy()
    for s in range(D, len(x), D):
        e = min(s + D, len(x))
        y[s:e] += g * y[s - D:e - D]
    return y


def allpass(x, D, g):
    y = np.zeros_like(x)
    for s in range(0, len(x), D):
        e = min(s + D, len(x))
        if s == 0:
            y[0:e] = -g * x[0:e]
        else:
            y[s:e] = -g * x[s:e] + x[s - D:e - D] + g * y[s - D:e - D]
    return y


_COMB_D = (1215, 1293, 1390, 1476, 1548, 1623)


def reverb(L, R, wet=0.2, rt=1.4):
    """Schroeder reverb: 6 comb + 2 allpass, stereo. wet = yaş/kuru RMS oranı."""
    outs = []
    for ch, x in enumerate((L, R)):
        x = np.asarray(x, dtype=np.float64)
        sp = 23 * ch
        pre = int(0.02 * SR)
        xin = np.concatenate([np.zeros(pre), x])[:len(x)]
        acc = np.zeros(len(x))
        for D in _COMB_D:
            g = 10.0 ** (-3.0 * (D + sp) / SR / rt)
            acc += comb(xin, D + sp, g)
        acc /= len(_COMB_D)
        acc = allpass(acc, 556 + sp, 0.5)
        acc = allpass(acc, 441 + sp, 0.5)
        acc = lp1(acc, 3200)
        outs.append(acc)
    ref = math.sqrt((np.asarray(L, dtype=np.float64) ** 2).mean() + (np.asarray(R, dtype=np.float64) ** 2).mean()) + 1e-12
    wr = math.sqrt((outs[0] ** 2).mean() + (outs[1] ** 2).mean()) + 1e-12
    k = wet * ref / wr
    return np.asarray(L) + outs[0] * k, np.asarray(R) + outs[1] * k


# ---------------------------------------------------------------- enstrümanlar
_ks_cache = {}


def ks(f, dur, tau=0.3, bright=0.5):
    """Karplus-Strong tel; tau = yarılanma süresi (sn). Perde ince ayarı için yeniden örnekleme."""
    key = (round(f, 2), round(dur, 3), tau, bright)
    if key in _ks_cache:
        return _ks_cache[key]
    Lout = max(64, int(dur * SR))
    P = SR / f
    N = max(2, int(P - 0.5))
    f_eff = SR / (N + 0.5)
    r = f / f_eff
    Ly = int(Lout * r) + 4
    d = 0.5 ** (1.0 / (f_eff * tau))
    rng = np.random.RandomState(int(f * 10) % 100000 + 7)
    burst = rng.uniform(-1, 1, N).tolist()
    p = 0.0
    b = []
    for xv in burst:
        p += bright * (xv - p)
        b.append(p)
    b = np.array(b)
    b -= b.mean()
    b /= max(np.abs(b).max(), 1e-9)
    Y = np.zeros(Ly + 1)
    Y[1:N + 1] = b
    for s in range(N, Ly, N):
        e = min(s + N, Ly)
        Y[s + 1:e + 1] = d * 0.5 * (Y[s - N + 1:e - N + 1] + Y[s - N:e - N])
    y = Y[1:]
    idx = np.arange(Lout) * r
    i0 = idx.astype(int)
    fr = idx - i0
    out = y[i0] * (1 - fr) + y[i0 + 1] * fr
    out = lp1(lp1(out, min(3200.0, max(1800.0, f * 5.0))), 6000.0)  # tel sesini yumuşat
    out = edges(out, 0.0015, 0.025)
    out = peak_norm(out).astype(np.float32)
    _ks_cache[key] = out
    return out


_mal_cache = {}


def mallet(f, kind="marimba", dur=0.6):
    key = (round(f, 2), kind, round(dur, 3))
    if key in _mal_cache:
        return _mal_cache[key]
    n = int(dur * SR)
    t = tt(n)
    if kind == "marimba":
        sc = (262.0 / f) ** 0.3
        parts = [(1, 1.0, 0.30 * sc), (3.93, 0.28, 0.07), (9.2, 0.08, 0.03)]
    elif kind == "glock":
        parts = [(1, 1.0, 0.55), (2.76, 0.30, 0.22), (5.4, 0.14, 0.10), (8.93, 0.06, 0.05)]
    else:  # soft
        parts = [(1, 1.0, 0.45), (2.0, 0.25, 0.2), (3.0, 0.1, 0.1)]
    sig = np.zeros(n)
    for ratio, amp, tau in parts:
        if f * ratio < 14000:
            sig += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / tau)
    out = peak_norm(edges(sig, 0.001, 0.02)).astype(np.float32)
    _mal_cache[key] = out
    return out


_bass_cache = {}


def bass(f, length=0.3, tau=0.2):
    key = (round(f, 2), length, tau)
    if key not in _bass_cache:
        s = ks(f, length, tau, 0.35).astype(np.float64)
        t = tt(len(s))
        s = s + 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.15)
        _bass_cache[key] = peak_norm(s).astype(np.float32)
    return _bass_cache[key]


_perc_cache = {}


def kick():
    if "kick" not in _perc_cache:
        n = int(0.3 * SR)
        t = tt(n)
        f = 45 + 80 * np.exp(-t / 0.025)
        y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / 0.09)
        _perc_cache["kick"] = edges(y, 0.0005, 0.02).astype(np.float32)
    return _perc_cache["kick"]


def brush(v=0):
    key = ("brush", v)
    if key not in _perc_cache:
        n = int(0.14 * SR)
        t = tt(n)
        x = bpf(nz(n, 100 + v), 1200, 3500)
        env = np.minimum(t / 0.008, 1) * np.exp(-t / 0.04)
        _perc_cache[key] = peak_norm(x * env, 0.8).astype(np.float32)
    return _perc_cache[key]


def shaker(v=0):
    key = ("shaker", v)
    if key not in _perc_cache:
        n = int(0.08 * SR)
        t = tt(n)
        x = bpf(nz(n, 200 + v), 3000, 6000)
        env = np.minimum(t / 0.006, 1) * np.exp(-t / 0.022)
        _perc_cache[key] = peak_norm(x * env, 0.6).astype(np.float32)
    return _perc_cache[key]


def timpani(f, dur=1.6):
    key = ("timp", round(f, 1), dur)
    if key not in _perc_cache:
        n = int(dur * SR)
        t = tt(n)
        fr = f * (1 + 0.18 * np.exp(-t / 0.05))
        ph = np.cumsum(2 * np.pi * fr / SR)
        y = np.sin(ph) * np.exp(-t / 0.55) + 0.35 * np.sin(1.5 * ph) * np.exp(-t / 0.25)
        y += 0.6 * lp1(nz(n, 300), 500) * np.exp(-t / 0.03)
        _perc_cache[key] = peak_norm(edges(y, 0.001, 0.05)).astype(np.float32)
    return _perc_cache[key]


def pad_note(layer, t0, dur, freqs, att, rel, gain, pan, rng, cents=(-8, 0, 8)):
    n = int(dur * SR)
    t = tt(n)
    sig = np.zeros(n)
    for f in freqs:
        for dc in cents:
            sig += saw(f * 2 ** (dc / 1200.0), n, rng.rand())
    sig /= (len(freqs) * len(cents))
    env = np.minimum(t / att, 1.0) * np.minimum((dur - t) / rel, 1.0)
    layer.add(sig * env, t0, gain, pan)


class Layer:
    def __init__(self, n):
        self.L = np.zeros(n, np.float32)
        self.R = np.zeros(n, np.float32)

    def add(self, sig, t, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        n = len(self.L)
        if i >= n or i + len(sig) <= 0:
            return
        a = max(0, -i)
        b = min(len(sig), n - i)
        seg = np.asarray(sig[a:b], dtype=np.float32) * gain
        ang = (pan + 1.0) * math.pi / 4.0
        self.L[i + a:i + b] += seg * math.cos(ang) * 1.4142
        self.R[i + a:i + b] += seg * math.sin(ang) * 1.4142

    def lp(self, fc, times=2):
        if np.abs(self.L).max() == 0 and np.abs(self.R).max() == 0:
            return
        for _ in range(times):
            self.L = lp1(self.L, fc).astype(np.float32)
            self.R = lp1(self.R, fc).astype(np.float32)

    def rms(self):
        return rms_gated(np.stack([self.L, self.R]))


# ---------------------------------------------------------------- beste bağlamı
MIN = (0, 3, 7)
MAJ = (0, 4, 7)


class Ctx:
    def __init__(self, bpm, dur, seed, swing=0.0):
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.bar = 4 * self.beat
        self.dur = dur
        self.rng = np.random.RandomState(seed)
        self.swing = swing
        n = int((dur + 4.0) * SR)
        self.nbars = int(math.ceil((dur + 0.5) / self.bar)) + 1
        self.main = Layer(n)
        self.pad = Layer(n)
        self.str = Layer(n)

    def T(self, bar, beat):
        b = beat
        if abs((beat % 1) - 0.5) < 1e-6:
            b = beat + self.swing * 0.5
        t = (bar * 4 + b) * self.beat + self.rng.uniform(-0.008, 0.008)
        return max(0.0, t)

    def V(self, v):
        return v * (1 + self.rng.uniform(-0.1, 0.1))


def wrap(root):
    return root if root <= 6 else root - 12


def ctn(tones, idx):
    o, k = divmod(idx, len(tones))
    return tones[k] + 12 * o


def motif_notes(motif, bp, phrase):
    p = phrase % 4
    out = []
    notes = motif[bp]
    for k, (b, i, l) in enumerate(notes):
        if p == 1 and bp == 3 and k == len(notes) - 1:
            i += 1
        if p == 2 and bp < 2:
            i = min(i + 1, 5)
        if p == 3 and bp == 1:
            continue
        out.append((b, i, l))
    return out


def prog_at(P, bar):
    ph, bp = divmod(bar, 4)
    prog = P[ph % len(P)]
    nxt = prog[bp + 1][0] if bp < 3 else P[(ph + 1) % len(P)][0][0]
    return ph, bp, prog[bp][0], prog[bp][1], nxt


def perc(c, bar, kicks=(), brushes=(), shakers=(), kv=0.5, bv=0.5, sv=0.25):
    for b in kicks:
        c.main.add(kick(), c.T(bar, b), c.V(kv), 0.0)
    for b in brushes:
        c.main.add(brush(int(c.rng.randint(3))), c.T(bar, b), c.V(bv), 0.15)
    for b in shakers:
        c.main.add(shaker(int(c.rng.randint(3))), c.T(bar, b), c.V(sv), -0.2)


# ---- stiller
MOT_MISCHIEF = [
    [(0.5, 1, .4), (1, 2, .4), (1.5, 3, .4), (2.5, 2, .4), (3, 1, .9)],
    [(0.5, 1, .4), (1, 2, .4), (1.5, 3, .4), (2.5, 4, .4), (3, 3, .9)],
    [(0.5, 2, .4), (1, 3, .4), (1.5, 4, .4), (2.5, 3, .4), (3, 2, .9)],
    [(0.5, 1, .4), (1, 2, .4), (2, 1, .4), (3, 0, 1.6)]]
MOT_MARCH = [
    [(0, 2, .4), (1, 3, .4), (1.5, 2, .3), (2, 3, .4), (3, 4, .8)],
    [(0, 3, .4), (1, 4, .4), (1.5, 3, .3), (2, 2, .4), (3, 1, .8)],
    [(0, 2, .4), (1, 3, .4), (1.5, 4, .3), (2, 5, .4), (3, 4, .8)],
    [(0, 3, .4), (1, 2, .4), (2, 1, .4), (3, 0, 1.0)]]
MOT_MYSTERY = [
    [(0, 2, 1.5), (2.5, 3, 1.5)],
    [(1, 1, 1.0), (2.5, 2, 1.5)],
    [(0, 3, 1.5), (2, 2, 1.0), (3.5, 1, 1.0)],
    [(0, 0, 3.0)]]
MOT_HAPPY = [
    [(0, 2, .4), (0.5, 3, .4), (1, 4, .4), (2, 3, .4), (2.5, 2, .4), (3, 3, .8)],
    [(0, 4, .4), (0.5, 3, .4), (1, 2, .4), (2, 3, .8), (3.5, 2, .4)],
    [(0, 2, .4), (0.5, 3, .4), (1, 4, .4), (1.5, 5, .4), (2, 4, .8), (3, 3, .4)],
    [(0, 3, .4), (1, 2, .4), (2, 1, .4), (3, 0, 1.0)]]
MOT_TENSE = [[], [(2, 2, .6)], [(1, 3, .6), (2.5, 2, .6)], [(0, 1, .6), (2, 2, 1.2)]]
MOT_EPIC = [
    [(0, 2, 2.0), (2, 3, 1.6)],
    [(0, 3, 2.0), (2, 2, 1.6)],
    [(0, 4, 2.0), (2, 3, 1.6)],
    [(0, 5, 1.5), (2, 3, 1.0), (3, 2, 1.0)]]


def st_mischief(c):
    key = 57
    P = [[(0, MIN), (8, MAJ), (5, MIN), (7, MAJ)], [(0, MIN), (10, MAJ), (8, MAJ), (7, MAJ)]]
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        bm = key - 12 + root
        nb = key - 12 + nxt
        appr = nb - 1 if nb > bm else nb + 1
        seq = [bm, bm + 7, bm + iv[1], appr]
        for k, (m, v) in enumerate(zip(seq, (.95, .7, .8, .75))):
            c.main.add(bass(mtof(m), .22, .18), c.T(bar, k), c.V(v), -0.1)
        rw = wrap(root)
        for b in (1.5, 3.5):
            t0 = c.T(bar, b)
            for j, i in enumerate(iv):
                c.main.add(ks(mtof(key + rw + i), .25, .15, .45), t0 + j * .008, c.V(.38), 0.25 if b < 2 else -0.25)
        if ph >= 1 or c.dur < 9:
            tones = [key + 12 + rw + i for i in iv]
            for (b, i, l) in motif_notes(MOT_MISCHIEF, bp, ph):
                f = mtof(ctn(tones, i))
                t0 = c.T(bar, b)
                c.main.add(ks(f, l * c.beat + .15, .3, .4), t0, c.V(.75), 0.15)
                c.main.add(mallet(f, "marimba", l * c.beat + .15), t0, c.V(.3), 0.15)
        perc(c, bar, kicks=(0,), brushes=(1, 3), shakers=(.5, 1.5, 2.5, 3.5), kv=.3, bv=.5, sv=.22)


def st_march(c):
    key = 48
    P = [[(0, MAJ), (5, MAJ), (7, MAJ), (0, MAJ)], [(0, MAJ), (9, MIN), (5, MAJ), (7, MAJ)]]
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        bm = key - 12 + root
        c.main.add(bass(mtof(bm), .3, .22), c.T(bar, 0), c.V(.95), -0.1)
        c.main.add(bass(mtof(bm + 7), .3, .22), c.T(bar, 2), c.V(.8), -0.1)
        rw = wrap(root)
        for b, pn in ((1, .2), (3, -.2)):
            t0 = c.T(bar, b)
            for j, i in enumerate(iv):
                c.main.add(mallet(mtof(key + rw + i + (12 if j == 0 else 0)), "marimba", .25), t0 + j * .006, c.V(.45), pn)
        if ph >= 1 or c.dur < 9:
            tones = [key + 12 + rw + i for i in iv]
            for (b, i, l) in motif_notes(MOT_MARCH, bp, ph):
                f = mtof(ctn(tones, i))
                t0 = c.T(bar, b)
                c.main.add(mallet(f, "marimba", l * c.beat + .2), t0, c.V(.8), 0.1)
                c.main.add(mallet(f, "glock", l * c.beat + .2), t0, c.V(.3), 0.1)
        perc(c, bar, kicks=(0, 2), brushes=(1, 3), shakers=(.5, 1.5, 2.5, 3.5), kv=.5, bv=.5, sv=.2)


def st_mystery(c):
    key = 50
    P = [[(0, MIN), (8, MAJ), (5, MIN), (7, MAJ)], [(0, MIN), (10, MAJ), (8, MAJ), (7, MAJ)]]
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        rw = wrap(root)
        freqs = [mtof(key - 12 + root), mtof(key + rw + iv[0]), mtof(key + rw + iv[1]), mtof(key + rw + iv[2])]
        pad_note(c.pad, bar * c.bar - 0.2 if bar else 0, c.bar + 1.0, freqs, 1.0, 1.2, 1.0, 0.0, c.rng)
        if bp % 2 == 0:
            c.main.add(bass(mtof(key - 12 + root), 1.5, .8), c.T(bar, 0), c.V(.6), -0.1)
        if bp == 0:
            c.main.add(timpani(mtof(key - 12 + root), 1.6), c.T(bar, 0), c.V(.25), 0.0)
        if ph >= 1 or c.dur < 12:
            tones = [key + 12 + rw + i for i in iv]
            for (b, i, l) in motif_notes(MOT_MYSTERY, bp, ph):
                f = mtof(ctn(tones, i))
                c.main.add(mallet(f, "glock", 1.4), c.T(bar, b), c.V(.7), 0.2 if (bar % 2) else -0.2)


def st_happy(c):
    key = 55
    P = [[(0, MAJ), (7, MAJ), (9, MIN), (5, MAJ)], [(0, MAJ), (5, MAJ), (0, MAJ), (7, MAJ)]]
    pattern = ((0, 1.0, 0), (1, .8, 0), (1.5, .55, 1), (2.5, .55, 1), (3, .85, 0), (3.5, .55, 1))
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        bm = key - 12 + root
        c.main.add(bass(mtof(bm), .3, .22), c.T(bar, 0), c.V(.9), -0.1)
        c.main.add(bass(mtof(bm + 7), .3, .22), c.T(bar, 2), c.V(.75), -0.1)
        rw = wrap(root)
        tones = [key + rw + iv[0], key + rw + iv[1], key + rw + iv[2], key + rw + 12]
        for b, v, up in pattern:
            t0 = c.T(bar, b)
            order = tones[::-1][:3] if up else tones
            for j, m in enumerate(order):
                c.main.add(ks(mtof(m), .45, .35, .6), t0 + j * .012, c.V(.45 * v), 0.1)
        if ph >= 1 or c.dur < 9:
            mt = [key + 12 + rw + i for i in iv]
            for (b, i, l) in motif_notes(MOT_HAPPY, bp, ph):
                c.main.add(mallet(mtof(ctn(mt, i)), "marimba", l * c.beat + .2), c.T(bar, b), c.V(.75), 0.2)
        perc(c, bar, kicks=(0, 2), shakers=(.5, 1.5, 2.5, 3.5), kv=.3, sv=.22)


def st_tense(c):
    key = 52
    P = [[(0, MIN), (0, MIN), (8, MAJ), (7, MAJ)], [(0, MIN), (5, MIN), (8, MAJ), (7, MAJ)]]
    acc = (1.0, .55, .7, .55, .9, .55, .7, .55)
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        bm = key - 12 + root
        for k in range(8):
            m = bm + (7 if k == 6 else 0)
            f = mtof(m)
            n = int(.24 * SR)
            t = tt(n)
            sig = (saw(f, n, .1) + saw(f * 1.006, n, .5)) * .5 + .3 * saw(f * 2, n, .3)
            env = np.minimum(t / .012, 1) * np.minimum((.24 - t) / .06, 1)
            c.str.add(sig * env, c.T(bar, k * .5), c.V(acc[k]), 0.0)
        if bp in (0, 2):
            pad_note(c.pad, bar * c.bar, c.bar * 2 + .5, [mtof(key + wrap(root) + i) for i in iv], 1.5, 1.0, .6, 0.0, c.rng)
        c.main.add(kick(), c.T(bar, 0), c.V(.6), 0.0)
        c.main.add(kick(), c.T(bar, .75), c.V(.4), 0.0)
        c.main.add(shaker(int(c.rng.randint(3))), c.T(bar, 3.5), c.V(.25), .2)
        if bp == 0:
            c.main.add(timpani(mtof(bm), 1.6), c.T(bar, 0), c.V(.6), 0.0)
        if ph >= 1 or c.dur < 9:
            mt = [key + 24 + wrap(root) + i for i in iv]
            for (b, i, l) in motif_notes(MOT_TENSE, bp, ph):
                c.main.add(mallet(mtof(ctn(mt, i)), "glock", 1.0), c.T(bar, b), c.V(.45), 0.25)


def st_epic(c):
    key = 48
    P = [[(0, MIN), (8, MAJ), (3, MAJ), (10, MAJ)], [(0, MIN), (5, MIN), (8, MAJ), (7, MAJ)]]
    for bar in range(c.nbars):
        ph, bp, root, iv, nxt = prog_at(P, bar)
        bm = key - 12 + root
        rw = wrap(root)
        fr = [mtof(bm), mtof(key + rw + iv[0]), mtof(key + rw + iv[1]), mtof(key + rw + iv[2]),
              mtof(key + 12 + rw + iv[0]), mtof(key + 12 + rw + iv[2])]
        pad_note(c.pad, max(0, bar * c.bar - 0.3), c.bar + 1.2, fr, .9, 1.0, 1.0, 0.0, c.rng)
        c.main.add(bass(mtof(bm), 2.0, 1.0), c.T(bar, 0), c.V(.8), -0.1)
        c.main.add(timpani(mtof(bm + 12 if bm < 40 else bm), 1.6), c.T(bar, 0), c.V(.9), 0.0)
        c.main.add(timpani(mtof(bm + 12 if bm < 40 else bm), 1.2), c.T(bar, 2.5), c.V(.5), 0.0)
        if bp == 3:
            for k, b in enumerate((2.0, 2.5, 3.0, 3.25, 3.5, 3.75)):
                c.main.add(timpani(mtof(bm + 12 if bm < 40 else bm), .8), c.T(bar, b), c.V(.4 + .1 * k), 0.0)
        if ph >= 1 or c.dur < 12:
            mt = [key + 12 + rw + i for i in iv]
            for (b, i, l) in motif_notes(MOT_EPIC, bp, ph):
                f = mtof(ctn(mt, i))
                c.main.add(mallet(f, "glock", 1.8), c.T(bar, b), c.V(.7), 0.2)
                c.main.add(mallet(f, "soft", 1.8), c.T(bar, b), c.V(.5), -0.2)


STYLES = {
    "mischief": dict(bpm=112, fn=st_mischief, key=57, swing=.15, wet=.18, pad_db=-12, str_db=-12, pad_fc=1500, str_fc=900),
    "march": dict(bpm=120, fn=st_march, key=48, swing=.06, wet=.12, pad_db=-12, str_db=-12, pad_fc=1500, str_fc=900),
    "mystery": dict(bpm=72, fn=st_mystery, key=50, swing=0.0, wet=.35, pad_db=-4, str_db=-12, pad_fc=1100, str_fc=900),
    "happy": dict(bpm=126, fn=st_happy, key=55, swing=.10, wet=.12, pad_db=-12, str_db=-12, pad_fc=1500, str_fc=900),
    "tense": dict(bpm=100, fn=st_tense, key=52, swing=0.0, wet=.22, pad_db=-10, str_db=-1, pad_fc=1000, str_fc=1000),
    "epic": dict(bpm=80, fn=st_epic, key=48, swing=0.0, wet=.40, pad_db=-3, str_db=-12, pad_fc=1700, str_fc=900),
}


def render_music(style, bpm, dur, seed=1):
    """dur sn'lik stereo müzik yatağı (2, n) float32."""
    cfg = STYLES[style]
    c = Ctx(bpm, dur, seed, cfg["swing"])
    cfg["fn"](c)
    c.pad.lp(cfg["pad_fc"])
    c.str.lp(cfg["str_fc"])
    rm = c.main.rms() + 1e-9
    L = c.main.L.astype(np.float64)
    R = c.main.R.astype(np.float64)
    for lay, db in ((c.pad, cfg["pad_db"]), (c.str, cfg["str_db"])):
        r = lay.rms()
        if r > 1e-9:
            k = rm * db2lin(db) / r
            L += lay.L * k
            R += lay.R * k
    L, R = reverb(L, R, cfg["wet"], 1.4 + cfg["wet"])
    out = []
    for x in (L, R):
        x = hpf(x, 70.0)
        x = lp1(lp1(x, 4000.0), 4000.0) * 0.85 + x * 0.15  # 2-5 kHz yumuşak
        out.append(x)
    X = np.stack(out)
    X = X / max(np.abs(X).max(), 1e-9) * 0.9
    X = np.tanh(1.3 * X) / np.tanh(1.3)
    nd = int(dur * SR)
    return X[:, :nd].astype(np.float32)


def build_sting(key, after):
    """(swell, dun_stereo, drone) - dun için stereo reverb uygulanmış."""
    f0 = mtof(key - 12)
    n = int(2.2 * SR)
    t = tt(n)
    fr = f0 * (1 + 0.25 * np.exp(-t / 0.05))
    ph = np.cumsum(2 * np.pi * fr / SR)
    dun = np.sin(ph) * np.exp(-t / .6) + .5 * np.sin(.5 * ph) * np.exp(-t / .9)
    clus = lp1(saw(2 * f0, n) + saw(2 * f0 * 1.189, n, .3) + saw(3 * f0, n, .6), 600)
    dun += .15 * clus * np.exp(-t / .35) * 3
    dun += .8 * lp1(nz(n, 41), 250) * np.exp(-t / .04)
    dun = peak_norm(edges(dun, 0.002, 0.1), 0.85)
    L, R = reverb(dun, dun, 0.35, 1.8)
    m = int(0.7 * SR)
    u = np.arange(m) / m
    sw = svf(nz(m, 42), 200 * np.exp(np.log(3500 / 200) * u), 0.4) * u ** 2
    sw = peak_norm(sw, .5)
    tone = np.sin(np.cumsum(2 * np.pi * (2 * f0 * (1 + u)) / SR)) * u ** 2 * .25
    sw = sw + tone
    sw[-int(.004 * SR):] *= np.linspace(1, 0, int(.004 * SR))
    nd = int(max(after, 0.1) * SR)
    td = tt(nd)
    dr = np.zeros(nd)
    for f in (f0, f0 * 1.5, f0 * 2):
        for dc in (-7, 0, 7):
            dr += saw(f * 2 ** (dc / 1200), nd, .3)
    dr = lp1(lp1(dr, 450), 450)
    dr *= np.minimum(td / 1.0, 1) * (1 + .15 * np.sin(2 * np.pi * .25 * td))
    dr = peak_norm(dr, .12)
    return sw, np.stack([L, R]), dr


# ---------------------------------------------------------------- SFX
def sn(f, n, tau, amp=1.0):
    t = tt(n)
    return amp * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)


def partials(f, n, parts):
    t = tt(n)
    s = np.zeros(n)
    for r, a, tau in parts:
        if f * r < 14000:
            s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
    return s


def sfx_whoosh(sd):
    n = int(.8 * SR)
    u = tt(n) / .8
    fc = 250 + 2200 * np.sin(np.pi * u) ** 1.5
    y = svf(nz(n, sd), fc, .5) * np.sin(np.pi * u) ** 2
    return y, int(.4 * SR)


def sfx_swish(sd):
    n = int(.3 * SR)
    u = tt(n) / .3
    y = svf(nz(n, sd), 1500 + 4500 * u, .5) * (u ** .7) * (1 - u) ** 2
    return y, int(.12 * SR)


def sfx_pop(sd):
    n = int(.15 * SR)
    t = tt(n)
    f = 800 * np.exp(-t / .02) + 200
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .025)
    y += .4 * hpf(nz(n, sd), 2000) * np.exp(-t / .002)
    return y, 0


def sfx_boing(sd):
    n = int(.9 * SR)
    t = tt(n)
    f = 200 * (1 + .45 * np.sin(2 * np.pi * 8 * t) * np.exp(-t / .28)) * (1 + .3 * np.exp(-t / .1))
    ph = np.cumsum(2 * np.pi * f / SR)
    y = (np.sin(ph) + .4 * np.sin(2 * ph)) * np.exp(-t / .35)
    return edges(y, .003, .02), 0


def sfx_thud(sd):
    n = int(.45 * SR)
    t = tt(n)
    f = 95 * np.exp(-t / .08) + 45
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .14) + .5 * lp1(nz(n, sd), 400) * np.exp(-t / .02)
    return y, 0


def sfx_stamp(sd):
    n = int(.4 * SR)
    t = tt(n)
    f = 120 * np.exp(-t / .05) + 60
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .12)
    y += .9 * lp1(hpf(nz(n, sd), 800), 3500) * np.exp(-t / .015)
    return y, 0


def sfx_impact(sd):
    n = int(1.3 * SR)
    t = tt(n)
    f = 75 * np.exp(-t / .12) + 32
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .4)
    y += .7 * lp1(nz(n, sd), 900) * np.exp(-t / .25) + .5 * hpf(nz(n, sd + 1), 2000) * np.exp(-t / .01)
    return y, 0


def sfx_crash(sd):
    n = int(1.5 * SR)
    t = tt(n)
    rng = np.random.RandomState(sd)
    y = hpf(nz(n, sd), 1200) * np.exp(-t / .45) * .6
    y += lp1(nz(n, sd + 1), 500) * np.exp(-t / .06) * 1.2
    for _ in range(18):
        ti = rng.uniform(.02, 1.0)
        f = rng.uniform(2000, 7000)
        m = int(.05 * SR)
        put(y, sn(f, m, .015, .5 * math.exp(-ti / .6)), int(ti * SR))
    return y, 0


def sfx_ding(sd):
    n = int(1.0 * SR)
    return edges(partials(1760, n, [(1, 1, .45), (2.0, .3, .25), (3.01, .12, .12)]), .001, .05), 0


def sfx_bell(sd):
    n = int(1.8 * SR)
    ra = [.56, .92, 1.19, 1.71, 2.0, 2.74, 3.0, 3.76]
    am = [.5, .8, .6, .7, 1., .4, .3, .15]
    ta = [1.2, 1.0, .8, .6, .5, .35, .3, .2]
    return edges(partials(523, n, list(zip(ra, am, ta))), .001, .1), 0


def sfx_cash(sd):
    n = int(1.4 * SR)
    rng = np.random.RandomState(sd)
    t = tt(n)
    y = np.zeros(n)
    m = int(.12 * SR)
    ka = lp1(hpf(nz(m, sd), 1500), 6000) * np.exp(-tt(m) / .012) * .9 + sn(120, m, .03, .5)
    put(y, ka, 0)
    k = int(1.2 * SR)
    ch = partials(2349, k, [(1, 1, .5), (1.34, .6, .35), (2.0, .5, .25)])
    put(y, ch * .8, int(.09 * SR))
    for _ in range(9):
        ti = rng.uniform(.3, .95)
        f = rng.uniform(4500, 7000)
        mm = int(.06 * SR)
        s = sn(f, mm, .02) + .5 * sn(f * 1.5, mm, .02)
        put(y, s, int(ti * SR), .25 * (1 - (ti - .3) / 1.0))
    return y, int(.09 * SR)


def sfx_coin(sd):
    n = int(.6 * SR)
    y = np.zeros(n)
    put(y, partials(2637, n, [(1, 1, .15), (1.26, .5, .12), (2.4, .2, .06)]), 0)
    put(y, partials(3136, n, [(1, 1, .18), (1.26, .5, .12), (2.4, .2, .06)]), int(.07 * SR), .8)
    return edges(y, .0005, .03), 0


def sfx_paper(sd):
    n = int(.7 * SR)
    t = tt(n)
    x = hpf(nz(n, sd), 1500)
    rng = np.random.RandomState(sd + 5)
    env = lp1(rng.random_sample(n) ** 6, 200)
    env = env / max(env.max(), 1e-9)
    y = x * env * np.sin(np.pi * t / .7) ** .5
    return y, 0


def sfx_click(sd):
    n = int(.06 * SR)
    t = tt(n)
    y = hpf(nz(n, sd), 2500) * np.exp(-t / .003) + .6 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t / .004)
    return y, 0


def sfx_tick(sd):
    n = int(.06 * SR)
    t = tt(n)
    y = np.sin(2 * np.pi * 1500 * t) * np.exp(-t / .008) + .3 * hpf(nz(n, sd), 2000) * np.exp(-t / .002)
    return y, 0


def _knock(n, sd, g=1.0):
    t = tt(n)
    f = 95 + 120 * np.exp(-t / .02)
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .05) + .4 * np.sin(2 * np.pi * 310 * t) * np.exp(-t / .03)
    y += .8 * lp1(nz(n, sd), 1200) * np.exp(-t / .004)
    return y * g


def sfx_door(sd):
    n = int(.65 * SR)
    y = np.zeros(n)
    m = int(.25 * SR)
    put(y, _knock(m, sd), 0)
    put(y, _knock(m, sd + 1, .85), int(.24 * SR))
    return y, 0


def sfx_footsteps(sd):
    n = int(1.2 * SR)
    y = np.zeros(n)
    m = int(.3 * SR)
    t = tt(m)
    for k, (ti, g) in enumerate(((0, 1.0), (.4, .9), (.8, 1.0))):
        f = (130 if k != 1 else 115) * np.exp(-t / .03) + 60
        s = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t / .07) + .6 * lp1(nz(m, sd + k), 700) * np.exp(-t / .02)
        put(y, s, int(ti * SR), g)
    return y, 0


def sfx_splash(sd):
    n = int(1.1 * SR)
    t = tt(n)
    rng = np.random.RandomState(sd)
    y = svf(nz(n, sd), 800 + 3500 * np.exp(-t / .25), .5) * np.exp(-t / .28) * np.minimum(t / .005, 1)
    y = peak_norm(y, 1.0)
    for _ in range(7):
        ti = rng.uniform(.08, .7)
        f0 = rng.uniform(500, 1100)
        m = int(.08 * SR)
        tm = tt(m)
        f = f0 * (1 + .5 * tm / .05)
        s = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-tm / .02)
        put(y, s, int(ti * SR), .3)
    return y, 0


def sfx_glass(sd):
    n = int(.8 * SR)
    y = partials(3520, n, [(1, 1, .3), (1.5, .6, .18), (2.02, .3, .08)])
    y += .3 * hpf(nz(n, sd), 3000) * np.exp(-tt(n) / .004)
    return edges(y, .0005, .05), 0


def sfx_magic(sd):
    n = int(1.3 * SR)
    y = np.zeros(n)
    for k, s in enumerate((0, 4, 7, 11, 12, 16, 19, 23)):
        f = mtof(84 + s)
        m = int(.6 * SR)
        tone = partials(f, m, [(1, 1, .25), (2.76, .25, .1), (3.0, .15, .15)])
        put(y, tone, int(k * .075 * SR), 1.0 if k == 7 else .6)
    return y, 0


def sfx_buzz(sd):
    n = int(.75 * SR)
    y = np.zeros(n)
    for ti, f in ((0, 170), (.36, 150)):
        m = int(.3 * SR)
        s = np.sign(np.sin(2 * np.pi * f * tt(m))) + .7 * np.sign(np.sin(2 * np.pi * f * 1.05 * tt(m)))
        s = lp1(s, 1200)
        put(y, edges(s, .005, .01), int(ti * SR))
    return y, 0


def sfx_success(sd):
    n = int(1.3 * SR)
    y = np.zeros(n)
    parts = [(1, 1, .3), (2.0, .3, .2), (3.0, .1, .1)]
    for k, m in enumerate((72, 76, 79, 84)):
        put(y, partials(mtof(m), int(.5 * SR), parts), int(k * .1 * SR), .8)
    for m in (84, 88, 91):
        put(y, partials(mtof(m), int(1.0 * SR), [(1, 1, .5), (2.0, .2, .3)]), int(.3 * SR), .5)
    return edges(y, .001, .05), 0


def sfx_riser(sd):
    n = int(1.5 * SR)
    u = tt(n) / 1.5
    y = svf(nz(n, sd), 200 * np.exp(np.log(7000 / 200) * u ** 1.5), .5) * u ** 2
    y = peak_norm(y, 1.0)
    tone = np.sin(np.cumsum(2 * np.pi * (150 * np.exp(np.log(6.0) * u)) / SR)) * u ** 2 * .4
    y = y + tone
    y[-int(.015 * SR):] *= np.linspace(1, 0, int(.015 * SR))
    return y, n


def sfx_sting(sd):
    n = int(1.5 * SR)
    t = tt(n)
    f0 = 73.4
    fr = f0 * (1 + .25 * np.exp(-t / .05))
    ph = np.cumsum(2 * np.pi * fr / SR)
    y = np.sin(ph) * np.exp(-t / .5) + .5 * np.sin(2 * ph) * np.exp(-t / .3)
    y += .5 * lp1(saw(2 * f0, n) + saw(2 * f0 * 1.189, n, .3), 600) * np.exp(-t / .35)
    y += .8 * lp1(nz(n, sd), 250) * np.exp(-t / .04)
    return edges(y, .002, .1), 0


def sfx_drumroll(sd):
    n = int(1.55 * SR)
    y = np.zeros(n)
    rng = np.random.RandomState(sd)
    ti = 0.0
    m = int(.06 * SR)
    tm = tt(m)
    while ti < 1.15:
        u = ti / 1.15
        s = lp1(hpf(nz(m, int(rng.randint(1000))), 1200), 6000) * np.exp(-tm / .025)
        put(y, s, int(ti * SR), .3 + .7 * u)
        ti += .085 - .05 * u
    k = int(.35 * SR)
    tk = tt(k)
    acc = sn(80, k, .1) + lp1(hpf(nz(k, sd + 3), 800), 6000) * np.exp(-tk / .1)
    put(y, acc, int(1.2 * SR), 1.3)
    return y, int(1.2 * SR)


def sfx_zip(sd):
    n = int(.4 * SR)
    u = tt(n) / .4
    x = nz(n, sd) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(60 + 140 * u) / SR)))
    y = svf(x, 800 + 4200 * u, .5) * np.sin(np.pi * u ** .7) ** 1.5
    return y, 0


def sfx_typing(sd):
    n = int(1.1 * SR)
    y = np.zeros(n)
    rng = np.random.RandomState(sd)
    ti = 0.0
    m = int(.05 * SR)
    tm = tt(m)
    while ti < .95:
        a = rng.uniform(.6, 1.0)
        s = hpf(nz(m, int(rng.randint(1000))), 2000) * np.exp(-tm / .003) + .5 * np.sin(2 * np.pi * 300 * tm) * np.exp(-tm / .012)
        put(y, s, int(ti * SR), a)
        ti += rng.uniform(.05, .11)
    return y, 0


SFX_FUNCS = {
    "whoosh": sfx_whoosh, "swish": sfx_swish, "pop": sfx_pop, "boing": sfx_boing, "thud": sfx_thud,
    "stamp": sfx_stamp, "impact": sfx_impact, "crash": sfx_crash, "ding": sfx_ding, "bell": sfx_bell,
    "cash": sfx_cash, "coin": sfx_coin, "paper": sfx_paper, "click": sfx_click, "tick": sfx_tick,
    "door": sfx_door, "footsteps": sfx_footsteps, "splash": sfx_splash, "glass": sfx_glass,
    "magic": sfx_magic, "buzz": sfx_buzz, "success": sfx_success, "riser": sfx_riser,
    "sting": sfx_sting, "drumroll": sfx_drumroll, "zip": sfx_zip, "typing": sfx_typing,
}
STEREO_KINDS = {"whoosh", "swish", "crash", "splash", "paper", "riser", "zip"}
_sfx_cache = {}


def get_sfx(kind):
    """(2, n) float64 ve vuruş noktası (örnek). Deterministik."""
    if kind in _sfx_cache:
        return _sfx_cache[kind]
    fn = SFX_FUNCS[kind]
    sd = 1000 + sorted(SFX_FUNCS).index(kind)
    if kind in STEREO_KINDS:
        a, anchor = fn(sd)
        b, _ = fn(sd + 101)
        st = np.stack([a, b])
    else:
        a, anchor = fn(sd)
        st = np.stack([a, a])
    st = np.nan_to_num(st)
    st = np.stack([edges(st[0], .0005, .008), edges(st[1], .0005, .008)])
    res = (peak_norm(st, 1.0), anchor)
    _sfx_cache[kind] = res
    return res


# ---------------------------------------------------------------- G/Ç
def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def decode_voice(path):
    ff = find_ffmpeg()
    if not ff:
        raise SystemExit("HATA: ffmpeg bulunamadı (PATH veya imageio_ffmpeg gerekli).")
    if not os.path.exists(path):
        raise SystemExit("HATA: ses dosyası yok: " + path)
    cmd = [ff, "-v", "error", "-i", path, "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "2", "-ar", str(SR), "-"]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit("HATA: ffmpeg çözemedi: " + r.stderr.decode("utf-8", "replace")[:300])
    a = np.frombuffer(r.stdout, dtype="<f4")
    a = a[:len(a) // 2 * 2].reshape(-1, 2).T.astype(np.float64)
    return np.nan_to_num(a)


def write_wav(path, a):
    a = np.nan_to_num(np.asarray(a, dtype=np.float64))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pcm = (np.clip(a.T, -1, 1) * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def centroid(x):
    m = np.asarray(x, dtype=np.float64)
    m = m.mean(axis=0) if m.ndim > 1 else m
    F = 4096
    nf = len(m) // F
    if nf == 0:
        return 0.0
    fr = np.fft.rfftfreq(F, 1.0 / SR)
    w = np.hanning(F)
    cs, ws = [], []
    for i in range(nf):
        S = np.abs(np.fft.rfft(m[i * F:(i + 1) * F] * w))
        e = S.sum()
        if e > 1e-6:
            cs.append((S * fr).sum() / e)
            ws.append(e)
    return float(np.average(cs, weights=ws)) if cs else 0.0


def fade_ends(X, fin=0.0, fout=0.0, start=0, end=None):
    end = X.shape[1] if end is None else end
    if fin > 0:
        n = min(int(fin * SR), end - start)
        if n > 0:
            X[:, start:start + n] *= np.linspace(0, 1, n)
    if fout > 0:
        n = min(int(fout * SR), end - start)
        if n > 0:
            X[:, end - n:end] *= np.linspace(1, 0, n)
    return X


# ---------------------------------------------------------------- proje modu
def run_project(proj):
    t_start = time.time()
    cfg_path = os.path.join(proj, "sound.json")
    if not os.path.exists(cfg_path):
        raise SystemExit("HATA: sound.json yok: " + cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    v = decode_voice(os.path.join(proj, cfg.get("voice", "work/voice.mp3")))
    vlen = v.shape[1] / SR
    dur = float(cfg.get("duration") or (vlen + 0.8))
    if dur < vlen:
        print("UYARI: duration ses süresinden kısa (%.2f < %.2f); ses süresi kullanıldı." % (dur, vlen))
        dur = vlen
    N = int(round(dur * SR))
    voice = np.zeros((2, N))
    k = min(N, v.shape[1])
    voice[:, :k] = v[:, :k]
    vr = rms_gated(voice)
    vp = float(np.abs(voice).max())
    if vr < 1e-4:
        print("UYARI: ses neredeyse sessiz; referans -20 dBFS alındı.")
        vr, vp = 0.1, 0.5

    # --- müzik
    stem = np.zeros((2, N))
    mus = cfg.get("music")
    music_info = "yok"
    if mus:
        style = mus.get("style", "mischief")
        if style not in STYLES:
            print("UYARI: bilinmeyen stil '%s' -> mischief" % style)
            style = "mischief"
        bpm = float(mus.get("bpm") or STYLES[style]["bpm"])
        start = float(mus.get("start", 0.0))
        stop = mus.get("stop")
        stop = float(stop) if stop is not None else None
        cut = stop is not None and stop < dur - 0.05
        end = min(stop, dur) if cut else dur
        sting = bool(mus.get("sting", False)) and cut
        lev = float(mus.get("level_db", -15))
        bed_dur = end - start
        if bed_dur >= 1.0:
            bed = render_music(style, bpm, bed_dur).astype(np.float64)
            if cut:
                fade_ends(bed, 0, 0.03)
            si = int(round(start * SR))
            put(stem[0], bed[0], si)
            put(stem[1], bed[1], si)
            if sting:
                sw, dn, dr = build_sting(STYLES[style]["key"], dur - stop)
                ei = int(round(stop * SR))
                for ch in (0, 1):
                    put(stem[ch], sw, ei - len(sw), 1.0)
                    put(stem[ch], dn[ch], ei, 1.0)
                    put(stem[ch], dr, ei + int(.05 * SR), 1.0)
            fade_ends(stem, fin=0.4, start=si, end=N)
            if dur - 1.2 > start:
                fade_ends(stem, fout=1.2)
            target = db2lin(lin2db(vr) + lev)
            for _ in range(6):  # kapı (-50 dBFS) kazançla değiştiği için yinelemeli
                stem *= target / max(rms_gated(stem), 1e-9)
            music_info = "%s %.0f bpm, %.1f-%.1f sn%s" % (style, bpm, start, end, ", sting" if sting else "")
    stem = np.nan_to_num(stem)

    # --- SFX
    sfx = np.zeros((2, N))
    skipped = []
    for cue in cfg.get("sfx", []) or []:
        kind = cue.get("kind")
        if kind not in SFX_FUNCS:
            skipped.append(str(kind))
            continue
        snd, anchor = get_sfx(kind)
        rg = rms_gated(snd, abs_db=-80, rel_db=-40)
        s = snd / max(rg, 1e-9) * vr * db2lin(-8.0 + float(cue.get("gain_db", 0)))
        pk = np.abs(s).max()
        cap = 0.7 * vp
        if pk > cap:
            s = s * (cap / pk)
        idx = int(round(float(cue["t"]) * SR)) - anchor
        for ch in (0, 1):
            put(sfx[ch], s[ch], idx)
    spk = float(np.abs(sfx).max())
    if spk > 0.7 * vp:
        sfx *= 0.7 * vp / spk
        spk = float(np.abs(sfx).max())
    sfx = np.nan_to_num(sfx)
    if skipped:
        print("UYARI: bilinmeyen SFX atlandı: " + ", ".join(skipped))

    # --- mix
    mix = voice + stem + sfx
    mpk = float(np.abs(mix).max())
    g = db2lin(-1.0) / max(mpk, 1e-9)
    mix *= g
    work = os.path.join(proj, "work")
    out = os.path.join(proj, "out")
    stem_w = stem * g
    sfx_w = sfx * g
    write_wav(os.path.join(work, "music.wav"), stem_w)
    write_wav(os.path.join(work, "sfx.wav"), sfx_w)
    write_wav(os.path.join(out, "mix.wav"), mix)
    print("Müzik: " + music_info)
    print("Ses RMS (gated): %.1f dBFS | tepe: %.1f dBFS" % (lin2db(vr), lin2db(vp)))
    print("Müzik RMS: %+.1f dB (sese göre)" % (lin2db(rms_gated(stem)) - lin2db(vr)) if mus else "Müzik RMS: -")
    print("SFX tepe oranı: %.2f x ses tepesi (sınır 0.70)" % (spk / vp))
    print("Mix tepe: %.2f dBFS (kazanç %+.1f dB) | süre %.1f sn | çalışma %.1f sn" % (
        lin2db(float(np.abs(mix).max())), lin2db(g), dur, time.time() - t_start))
    print("Yazıldı: work/music.wav, work/sfx.wav, out/mix.wav")


# ---------------------------------------------------------------- demo modu
def run_demo(outdir, spacing=1.0):
    os.makedirs(outdir, exist_ok=True)
    for name, cfg in STYLES.items():
        t0 = time.time()
        X = render_music(name, cfg["bpm"], 30.0).astype(np.float64)
        fade_ends(X, 0.4, 1.2)
        X = X / max(np.abs(X).max(), 1e-9) * 0.8
        p = os.path.join(outdir, "music_%s.wav" % name)
        write_wav(p, X)
        print("%-9s %3d bpm -> %s  (merkez frekans %.0f Hz, %.1f sn)" % (name, cfg["bpm"], p, centroid(X), time.time() - t0))
    kinds = list(SFX_FUNCS.keys())
    total = (len(kinds) + 2) * spacing + 2.0
    buf = np.zeros((2, int(total * SR)))
    print("\nSFX dizini (%s sn arayla, vuruş anı):" % spacing)
    for i, k in enumerate(kinds):
        t = (i + 2) * spacing
        snd, anchor = get_sfx(k)
        for ch in (0, 1):
            put(buf[ch], snd[ch] * 0.5, int(round(t * SR)) - anchor)
        print("  t=%5.1f sn  %s" % (t, k))
    p = os.path.join(outdir, "sfx_all.wav")
    write_wav(p, buf)
    print("-> " + p)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    if a[0] == "--demo":
        if len(a) < 2:
            raise SystemExit("Kullanım: python audio.py --demo <klasör>")
        run_demo(a[1])
    else:
        run_project(a[0])


if __name__ == "__main__":
    main()
