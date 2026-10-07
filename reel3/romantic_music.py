"""Original romantic Bollywood-style track (reel3 v2, 80 BPM, cuts at 0.75 s multiples) (royalty-free, synthesised): bansuri hook,
dholak, taali claps, strings, bass.  96 BPM, F major / D minor.  28 s, matches reel2.py v2
(drop at 2.5, flurry 20-22.5, outro at 25).

Usage: python bolly_music.py out.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
TOTAL = 27.0
N = int(SR * TOTAL)
BEAT = 0.75; BAR = 4 * BEAT
rng = np.random.default_rng(7)

def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x)
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)
def mx(*xs):
    out = np.zeros(max(len(x) for x in xs))
    for x in xs: out[:len(x)] += x
    return out
def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf) or i < 0: return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

# ------------------------------------------------------------------ instruments
def bansuri(n, dur, vel=1.0, slide_from=None):
    """Breathy flute: vibrato after onset, optional meend (slide) from a lower note."""
    t = t_arr(dur + 0.15)
    f = np.full_like(t, mf(n))
    if slide_from is not None:
        k = np.clip(t / 0.09, 0, 1)
        f = mf(slide_from) * (1 - k) + mf(n) * k
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - 0.18) / 0.25, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    breath = bp(rng.normal(0, 1, len(t)), mf(n) * 0.8, min(mf(n) * 3, 15000)) * 0.12
    env = np.minimum(1, t / 0.05) * np.clip((dur + 0.15 - t) / 0.15, 0, 1)
    return (tone + breath) * env * 0.32 * vel

def strings(notes, dur, vel=1.0):
    t = t_arr(dur)
    x = np.zeros_like(t)
    for n in notes:
        for det in (-0.09, 0.0, 0.09):
            fr = mf(n) * 2 ** (det / 12) * (1 + 0.003 * np.sin(2 * np.pi * 4.5 * t + rng.random() * 6))
            x += 2 * ((np.cumsum(fr) / SR + rng.random()) % 1) - 1
    env = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.4)
    return lp(x / (3 * len(notes)), 2200) * env * vel

def pluck(n, dur=0.6, vel=1.0):  # santoor-ish
    t = t_arr(dur)
    x = sum(np.sin(2 * np.pi * mf(n) * k * t) * np.exp(-t * (5 + 3 * k)) / k for k in (1, 2, 3, 4))
    return x * np.minimum(1, t / 0.002) * 0.25 * vel

def dholak_low(vel=1.0):
    t = t_arr(0.45)
    f = 95 + 45 * (1 - np.exp(-t * 10))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.55 * vel

def dholak_high(vel=1.0):
    t = t_arr(0.25)
    ring = np.sin(2 * np.pi * 380 * t) * np.exp(-t * 22) + 0.5 * np.sin(2 * np.pi * 760 * t) * np.exp(-t * 30)
    slap = bp(rng.normal(0, 1, len(t)), 1500, 6000) * np.exp(-t * 70)
    return (ring * 0.35 + slap * 0.45) * vel

def taali(vel=1.0):
    t = t_arr(0.3)
    env = sum(np.exp(-np.clip(t - d, 0, None) * 45) * (t >= d) for d in (0, 0.009, 0.019))
    return bp(rng.normal(0, 1, len(t)), 900, 4500) * env * 0.35 * vel

def ghungroo(vel=1.0):
    t = t_arr(0.18)
    return hp(rng.normal(0, 1, len(t)), 6500) * np.exp(-t * 28) * 0.2 * vel

def bass(n, dur):
    t = t_arr(dur)
    x = np.sin(2 * np.pi * mf(n) * t) + 0.25 * np.sin(4 * np.pi * mf(n) * t)
    return np.tanh(1.3 * x) * np.exp(-t * 2.2) * np.minimum(1, t / 0.006) * 0.5

def swell(dur):
    t = t_arr(dur); p = t / dur
    return bp(rng.normal(0, 1, len(t)), 400, 7000) * p ** 2 * 0.4

def impact(dur=2.0):
    t = t_arr(dur)
    f = 45 + 70 * np.exp(-t * 7)
    return np.tanh(1.4 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.5)) * 0.8 + \
        lp(rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 5) * 0.25

# ------------------------------------------------------------------ arrangement

mel = np.zeros(N); drums = np.zeros(N); bed = np.zeros(N); fx = np.zeros(N)

def piano(n, dur=2.5, vel=1.0):
    t = t_arr(dur); f = mf(n)
    x = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k)) * (0.55 ** (k - 1)) * np.exp(-t * (1.0 + 0.9 * k))
            for k in range(1, 6))
    return x * np.minimum(1, t / 0.004) * 0.3 * vel

def soft_tabla(t0, bars, vel=1.0):
    """Gentle keherwa: bayan on 1 and 3, dayan rings between, a light taali on 2 & 4."""
    for b in range(bars):
        tb = t0 + b * BAR
        for e in range(8):
            tm = tb + e * BEAT / 2
            if e in (0, 5): add(drums, dholak_low(0.7 * vel), tm)
            elif e in (2, 6): add(drums, dholak_high(0.55 * vel), tm)
            else: add(drums, dholak_high(0.25 * vel), tm)
        for e in (1, 3): add(drums, taali(0.35 * vel), tb + e * BEAT)

# Dm  Bb  F  C  (vi-IV-I-V in F)
PROG = [(50, [62, 65, 69]), (46, [62, 65, 70]), (53, [65, 69, 72]), (48, [64, 67, 72])]
def chords(t0, bars, vel=1.0, arp=True, i0=0):
    for b in range(bars):
        r, ch = PROG[(i0 + b) % 4]
        tb = t0 + b * BAR
        add(bed, strings([n + 12 for n in ch], BAR + 0.5, vel), tb, 0.38)
        add(bed, bass(r - 12, BAR * 0.9), tb, 0.7 * vel)
        add(bed, bass(r - 12, BAR * 0.4), tb + 2.5 * BEAT, 0.45 * vel)
        if arp:   # rolling piano arpeggio, 8 notes per bar
            pat = [ch[0] - 12, ch[1] - 12, ch[2] - 12, ch[0], ch[1], ch[2], ch[1], ch[0]]
            for k, n in enumerate(pat):
                add(bed, piano(n, 1.6, 0.75 if k else 1.0), tb + k * BEAT / 2, 0.8)

# melody (beat offset, midi, beats, slide_from) over 4 bars
MEL_A = [(0, 69, 1.5, 67), (1.5, 70, .5, None), (2, 69, 1, None), (3, 67, 1, None),
         (4, 65, 2, 64), (6, 67, 1, None), (7, 69, 1, None),
         (8, 72, 2, 70), (10, 70, 1, None), (11, 69, 1, None),
         (12, 67, 3, 65), (15, 64, 1, None)]
MEL_B = [(0, 74, 1.5, 72), (1.5, 72, .5, None), (2, 74, 1, None), (3, 76, 1, None),
         (4, 77, 2, 76), (6, 76, 1, None), (7, 74, 1, None),
         (8, 72, 1.5, None), (9.5, 74, .5, None), (10, 72, 1, None), (11, 69, 1, None),
         (12, 67, 2, 65), (14, 69, 1, None), (15, 72, 1, 69)]
def sing(phrase, t0, vel=1.0):
    for b, n, ln, sl in phrase:
        add(mel, bansuri(n, ln * BEAT * 0.97, vel, sl), t0 + b * BEAT)

# 0 - 3 : piano + pad intro, flute alaap
chords(0.0, 1, 0.7)
for tm, n, ln, sl in [(0.4, 69, 0.9, 67), (1.4, 72, 0.5, None), (1.95, 70, 0.4, None), (2.4, 69, 0.55, None)]:
    add(mel, bansuri(n, ln, 0.8, sl), tm)
# 3 - 15 : verse — melody A, soft tabla enters
chords(3.0, 4, 0.9, i0=0)
soft_tabla(3.0, 4)
sing(MEL_A, 3.0)
# 15 - 24 : lift — melody B (first 3 bars), santoor shimmer, fuller strings
add(fx, swell(1.5), 13.5, 0.4)
chords(15.0, 3, 1.05, i0=0)
soft_tabla(15.0, 3, 1.15)
sing([m for m in MEL_B if m[0] < 12], 15.0, 1.05)
for k in range(24):
    r, ch = PROG[(k // 8) % 4]
    add(fx, pluck(ch[k % 3] + 24, 0.5, 0.45), 15.0 + k * BEAT / 2)
# 24 - 27 : resolve on F — piano, strings, last flute phrase
add(bed, strings([65, 69, 72, 77], 3.0, 1.0), 24.0, 0.45)
add(bed, bass(41, 2.8), 24.0, 0.8)
for k, n in enumerate([53, 60, 65, 69, 72, 77]):
    add(bed, piano(n, 2.8, 0.9), 24.0 + k * 0.18, 0.8)
for tm, n, ln, sl in [(24.1, 72, 0.6, 69), (24.8, 74, 0.35, None), (25.2, 72, 0.35, None), (25.6, 69, 1.3, 67)]:
    add(mel, bansuri(n, ln, 0.85, sl), tm)

# ------------------------------------------------------------------ mix
def reverb(x, wet):
    y = np.zeros_like(x)
    for dl, g in [(0.031, 0.5), (0.043, 0.45), (0.071, 0.38), (0.101, 0.3), (0.149, 0.24), (0.223, 0.17), (0.31, 0.11)]:
        d = int(dl * SR); y[d:] += x[:-d] * g
    return x + wet * lp(y, 5500)

def bus(shift):
    return (reverb(np.roll(mel, shift), 0.5) * 1.3 + reverb(drums, 0.15) * 1.25 +
            reverb(np.roll(bed, shift * 2), 0.3) * 0.42 + reverb(fx, 0.4) * 0.9)
L, R = hp(bus(0), 35), hp(bus(30), 35)
L = L + 1.6 * hp(L, 2200) + 1.2 * hp(L, 6000); R = R + 1.6 * hp(R, 2200) + 1.2 * hp(R, 6000)   # presence / air
L = L - 0.25 * bp(L, 200, 450); R = R - 0.25 * bp(R, 200, 450)  # clear the low-mid mud
L = L - 0.3 * lp(L, 110); R = R - 0.3 * lp(R, 110)
st = np.stack([L, R], 1)
st = np.tanh(st / np.abs(st).max() * 1.5) / np.tanh(1.5)
fo = int(1.3 * SR); st[-fo:] *= np.linspace(1, 0, fo)[:, None]
st *= 0.93
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "bolly.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")

