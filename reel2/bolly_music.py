"""Original Bollywood-romantic style track (royalty-free, synthesised): bansuri hook,
dholak, taali claps, strings, bass.  96 BPM, F major / D minor.  28 s, matches reel2.py v2
(drop at 2.5, flurry 20-22.5, outro at 25).

Usage: python bolly_music.py out.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
TOTAL = 28.0
N = int(SR * TOTAL)
BEAT = 0.625; BAR = 4 * BEAT
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

CHORDS = [(53, [65, 69, 72]), (48, [64, 67, 72]), (50, [65, 69, 74]), (46, [65, 70, 74])]  # F C Dm Bb

# hook: (beat offset, midi, beats, slide_from)
HOOK = [(0, 69, 1, 67), (1, 72, .5, None), (1.5, 74, .5, None), (2, 72, 1, None), (3, 69, 1, None),
        (4, 67, 1.5, 65), (5.5, 69, .5, None), (6, 67, 1, None), (7, 64, 1, None),
        (8, 65, 1, 64), (9, 69, .5, None), (9.5, 74, .5, None), (10, 74, 1, None), (11, 72, 1, None),
        (12, 70, 1, None), (13, 69, 1, None), (14, 67, 1.5, None), (15.5, 65, .5, None)]
HOOK2 = HOOK[:12] + [(12, 70, 1, None), (13, 72, 1, None), (14, 74, 1, 72), (15, 77, 1, 76)]

def play(phrase, t0, octave=0, vel=1.0, upto=16):
    for b, n, ln, sl in phrase:
        if b >= upto: continue
        add(mel, bansuri(n + octave, ln * BEAT * 0.95, vel, None if sl is None else sl + octave), t0 + b * BEAT)

def groove(t0, bars=1, vel=1.0):
    # dholak: low on 1, &2, 3 ; high on the rest (eighths), taali on 2 & 4, ghungroo on offbeats
    for b in range(bars):
        tb = t0 + b * BAR
        for e in range(8):
            tm = tb + e * BEAT / 2
            if e in (0, 3, 4): add(drums, dholak_low(vel), tm)
            else: add(drums, dholak_high(vel * (0.9 if e in (2, 6) else 0.6)), tm)
            if e % 2 == 1: add(drums, ghungroo(vel), tm)
        for e in (1, 3): add(drums, taali(vel), tb + e * BEAT)

def harmony(t0, bars, vel=1.0, i0=0):
    for b in range(bars):
        r, ch = CHORDS[(i0 + b) % 4]
        tb = t0 + b * BAR
        add(bed, strings(ch, BAR + 0.35, vel), tb, 0.55)
        for e in (0, 2.5, 3.5):
            add(bed, bass(r - 12, BEAT * 1.2), tb + e * BEAT, 0.8 * vel)

# intro 0 - 2.5 : strings + flute pickup + swell
add(bed, strings([65, 69, 72, 77], 2.8, 0.9), 0.0, 0.5)
for tm, n, ln, sl in [(0.3, 72, 0.6, 69), (0.95, 74, 0.3, None), (1.25, 72, 0.3, None), (1.55, 69, 0.8, None)]:
    add(mel, bansuri(n, ln, 0.9, sl), tm)
for k in range(8): add(fx, pluck(77 - [0, 3, 5, 7, 8, 10, 12, 15][k] + 0, 0.5, 0.7), 0.05 + k * 0.28)
add(fx, swell(2.2), 0.3, 0.8)

# 2.5 - 12.5 : hook (4 bars)
add(fx, impact(), 2.5, 0.8)
groove(2.5, 4); harmony(2.5, 4)
play(HOOK, 2.5)
# 12.5 - 20.0 : hook variation an octave of excitement + santoor counter-line (3 bars)
groove(12.5, 3, 1.05); harmony(12.5, 3, 1.0)
play(HOOK2, 12.5, 0, 1.0, upto=12)
for k in range(24):
    r, ch = CHORDS[(k // 8) % 4]
    add(fx, pluck(ch[k % 3] + 12, 0.45, 0.6), 12.5 + k * BEAT / 2)
# 20.0 - 22.5 : flurry: dholak roll + rising strings
for k in range(16):
    add(drums, dholak_high(0.4 + 0.6 * k / 15), 20.0 + k * BEAT / 4)
    if k % 4 == 0: add(drums, dholak_low(1.0), 20.0 + k * BEAT / 4)
add(bed, strings([62, 65, 69, 74], BAR, 0.9), 20.0, 0.5)
add(fx, swell(BAR), 20.0, 0.7)
for k, n in enumerate([74, 76, 77, 79, 81, 79, 77, 76]):
    add(mel, bansuri(n, BEAT * 0.45, 0.8), 20.0 + k * BEAT / 2)
# 22.5 - 25.0 : last hook bar (big)
groove(22.5, 1, 1.1); harmony(22.5, 1, 1.1, i0=0)
play([(b - 12, n, ln, sl) for b, n, ln, sl in HOOK2 if b >= 12], 22.5, 0, 1.05)
# 25.0 - 28.0 : outro – resolve on F, flute signs off
add(fx, impact(2.5), 25.0, 0.6)
add(drums, mx(dholak_low(1.0), taali(1.0)), 25.0)
add(bed, strings([65, 69, 72, 77], 3.0, 1.0), 25.0, 0.6)
add(bed, bass(41, 2.5), 25.0, 0.9)
for tm, n, ln, sl in [(25.05, 77, 0.6, 76), (25.7, 76, 0.3, None), (26.0, 74, 0.3, None), (26.3, 72, 0.3, None),
                      (26.6, 69, 1.2, 67)]:
    add(mel, bansuri(n, ln, 0.9, sl), tm)

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
L = L + 0.6 * hp(L, 2500); R = R + 0.6 * hp(R, 2500)   # presence / air
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
