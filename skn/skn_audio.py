"""Music + sound design for the SKN Theory reel (36 s, 120 BPM, F major).
Writes music.wav, sfx.wav, mix.wav and music_vo_ducked.wav (music pre-ducked under the VO lines).

Usage: python skn_audio.py OUT_DIR
"""
import os, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR, TOTAL = 44100, 36.0
N = int(SR * TOTAL)
BEAT = 0.5
rng = np.random.default_rng(12)
def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x)
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf): return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

# -------------------------------------------------------------- instruments
def pad(notes, dur, bright=900):
    t = t_arr(dur); x = np.zeros_like(t)
    for n in notes:
        for det in (-0.06, 0.06):
            f = mf(n) * 2 ** (det / 12)
            x += np.sin(2 * np.pi * f * t + 0.6 * np.sin(2 * np.pi * f * 2 * t))   # soft FM warmth
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return lp(x / (2 * len(notes)), bright) * env

def piano(n, dur=2.2, vel=1.0):
    t = t_arr(dur); f = mf(n)
    x = sum(np.sin(2 * np.pi * f * k * t) * 0.5 ** (k - 1) * np.exp(-t * (1.4 + 1.1 * k)) for k in range(1, 6))
    return lp(x * np.minimum(1, t / 0.004), 3800) * vel

def pluck(n, dur=0.45, vel=1.0):
    t = t_arr(dur)
    x = (np.sin(2 * np.pi * mf(n) * t) + 0.3 * np.sin(2 * np.pi * mf(n) * 2 * t)) * np.exp(-t * 9)
    return x * np.minimum(1, t / 0.003) * vel

def kick(vel=1.0):          # soft, round pulse (no click)
    t = t_arr(0.45)
    f = 48 + 38 * np.exp(-t * 18)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * vel

def shaker(vel=1.0):
    t = t_arr(0.09)
    return bp(rng.normal(0, 1, len(t)), 5000, 11000) * np.exp(-t * 45) * vel

def air(dur):
    t = t_arr(dur)
    x = hp(rng.normal(0, 1, len(t)), 4000) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))
    return lp(x, 9000) * np.minimum(1, t / 2) * np.minimum(1, (dur - t) / 2)

def whoosh(dur=0.7, lo=300, hi=5000, rev=False):
    t = t_arr(dur); p = t / dur
    x = rng.normal(0, 1, len(t)); out = np.zeros_like(x); ch = 1024
    for i in range(0, len(x), ch):
        q = p[i] if not rev else 1 - p[i]
        c = lo + (hi - lo) * q
        out[i:i + ch] = bp(x[i:i + ch], c * 0.6, min(c * 1.6, 18000))[:len(out[i:i + ch])]
    env = np.sin(np.pi * p) ** 1.5 if not rev else p ** 2 * (1 - p) * 6.75
    return out * env

def riser(dur):
    t = t_arr(dur); p = t / dur
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * p ** 2) / SR) * 0.25
    return (bp(rng.normal(0, 1, len(t)), 800, 7000) * 0.5 + tone) * p ** 2.2

def shimmer(vel=1.0):       # typography accent: tiny glassy bell
    t = t_arr(0.9)
    x = sum(np.sin(2 * np.pi * f * t) * a * np.exp(-t * d) for f, a, d in [(2637, 1, 6), (3951, .5, 8), (5274, .3, 10)])
    return (x + hp(rng.normal(0, 1, len(t)), 7000) * np.exp(-t * 60) * 0.3) * 0.25 * vel

def chime_chord(notes, dur=3.0):
    return sum(piano(n, dur, 0.8) for n in notes) / len(notes)

# -------------------------------------------------------------- arrangement
music = np.zeros(N); sfx = np.zeros(N)
CH = [[53, 64, 69, 72], [57, 64, 67, 72], [50, 65, 69, 76], [46, 62, 65, 69]]   # Fmaj7 Am7 Dm9 Bbmaj7
ROOT = [41, 45, 38, 46]
for k in range(9):                                           # chord every 4 s
    t0 = k * 4.0
    c = CH[k % 4]
    bright = 700 if t0 < 4 else 1100 if t0 < 16 else 1500
    if 23.5 <= t0 < 27: bright = 800
    add(music, pad(c, 4.6, bright), t0, 0.5)
    if t0 >= 4 and not (23.5 <= t0 < 27):
        add(music, lp(np.sin(2 * np.pi * mf(ROOT[k % 4] - 12) * t_arr(4.0)) * np.minimum(1, t_arr(4.0) / 0.05), 200), t0, 0.22)
add(music, air(TOTAL), 0, 0.05)
# intro piano motif
for tm, n in [(0.3, 72), (0.8, 76), (1.3, 79), (2.0, 77), (2.6, 76), (3.2, 72)]:
    add(music, piano(n, 2.4, 0.55), tm)
# pulse + arps
for i in range(int((TOTAL - 4.0) / BEAT)):
    tb = 4.0 + i * BEAT
    if 23.5 <= tb < 27.0 or tb >= 33.5: continue
    add(music, kick(0.55 if tb < 27 else 0.4), tb)
    if tb >= 16.0 and tb < 23.5:
        add(music, shaker(0.35), tb + 0.25); add(music, shaker(0.2), tb + 0.125); add(music, shaker(0.2), tb + 0.375)
for i in range(int((33.0 - 4.0) / (BEAT / 2))):              # eighth-note plucks following the chord
    tb = 4.0 + i * BEAT / 2
    if 23.5 <= tb < 27.0: continue
    c = CH[int(tb // 4) % 4]
    n = c[1:][i % 3] + (12 if tb >= 16 else 0)
    add(music, lp(pluck(n, 0.45, 0.55 if i % 2 == 0 else 0.35), 2600), tb, 0.35)
# breakdown 23.5-27: piano motif, riser into the reveal
for tm, n in [(23.6, 76), (24.1, 74), (24.6, 72), (25.4, 69), (26.0, 72)]:
    add(music, piano(n, 2.6, 0.7), tm)
add(music, riser(1.4), 25.6, 0.35)
# resolve at the end card
add(music, chime_chord([53, 60, 65, 69, 72, 76], 6.0), 27.0, 0.6)
add(music, pad([65, 69, 72, 76], 9.0, 1300), 27.0, 0.45)

# -------------------------------------------------------------- sound design
for T, d in [(4.0, 0.9), (7.5, 0.5), (16.0, 1.0), (27.0, 1.0)]:
    add(sfx, whoosh(d), T - d / 2, 0.55)
add(sfx, whoosh(0.8, rev=True), 23.5 - 0.6, 0.45)
for T in [0.45, 4.75, 8.05, 10.35, 16.45, 23.85, 28.5]:
    add(sfx, shimmer(0.8), T)
add(sfx, chime_chord([77, 81, 84, 89], 3.0), 30.55, 0.45)   # brand name lands
add(sfx, shimmer(1.0), 31.85)                                # CTA

# -------------------------------------------------------------- mix + stems
VO = [(0.4, 2.8), (4.4, 9.2), (10.4, 14.4), (16.4, 19.8), (23.4, 29.0), (29.6, 34.6)]
duck = np.ones(N)
tt = np.arange(N) / SR
for a, b in VO:
    duck -= 0.55 * np.clip(np.minimum((tt - (a - 0.25)) / 0.25, ((b + 0.35) - tt) / 0.35), 0, 1)

def reverb(x, wet):
    y = np.zeros_like(x)
    for dl, g in [(0.029, .5), (0.047, .42), (0.073, .35), (0.109, .28), (0.163, .2), (0.241, .14), (0.35, .08)]:
        d = int(dl * SR); y[d:] += x[:-d] * g
    return x + wet * lp(y, 6000)

def stereo(x, shift=18): return np.stack([x, np.roll(x, shift) * 0.98], 1)
def fade(x):
    f = int(1.5 * SR); x = x.copy(); x[-f:] *= np.linspace(1, 0, f)[:, None] if x.ndim == 2 else np.linspace(1, 0, f); return x

M = fade(stereo(hp(reverb(music, 0.35), 30)))
S = fade(stereo(hp(reverb(sfx, 0.3), 60), 9))
S = S * 0.5
peak = np.abs(M * 0.8 + S).max()
def write(name, x):
    x = x / peak * 0.9
    with wave.open(os.path.join(sys.argv[1], name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
os.makedirs(sys.argv[1], exist_ok=True)
write("music.wav", M * 0.8)
write("sfx.wav", S)
write("mix.wav", M * 0.8 + S)
write("music_vo_ducked.wav", M * 0.8 * duck[:, None] + S)
print("ok")
