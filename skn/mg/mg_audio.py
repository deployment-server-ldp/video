"""Audio for the motion graphics cut: places the supplied VO phrases (moved, never stretched),
builds a documentary music bed and graphics-synced sound design, ducks music under the VO.

Usage: python mg_audio.py VO.mp3 OUT_DIR
Writes vo_placed.wav, music.wav, sfx.wav, mix.wav (pre-loudnorm).
"""
import os, subprocess, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mg import VO, TOTAL

SR = 44100
N = int(SR * TOTAL)
rng = np.random.default_rng(31)
def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x)
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf): return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

# ---------------------------------------------------------------- VO placement
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
src = np.frombuffer(raw, np.float32).astype(np.float64)
vo = np.zeros(N)
for a, b, c in VO:
    seg = src[int(a * SR):int(b * SR)].copy()
    f = int(0.012 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    add(vo, seg, c)

# ---------------------------------------------------------------- instruments
def pad(notes, dur, bright=1000):
    t = t_arr(dur); x = np.zeros_like(t)
    for n in notes:
        for det in (-0.05, 0.05):
            f = mf(n) * 2 ** (det / 12)
            x += np.sin(2 * np.pi * f * t + 0.5 * np.sin(2 * np.pi * f * 2 * t))
    env = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5)
    return lp(x / (2 * len(notes)), bright) * env

def piano(n, dur=3.0, vel=1.0):
    t = t_arr(dur); f = mf(n)
    x = sum(np.sin(2 * np.pi * f * k * t) * 0.5 ** (k - 1) * np.exp(-t * (1.1 + 1.0 * k)) for k in range(1, 6))
    return lp(x * np.minimum(1, t / 0.004), 3500) * vel

def pulse(vel=1.0):
    t = t_arr(0.5); f = 50 + 30 * np.exp(-t * 16)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * vel

def tick(vel=1.0, f0=2600):
    t = t_arr(0.12)
    return (np.sin(2 * np.pi * f0 * t) * np.exp(-t * 70) + hp(rng.normal(0, 1, len(t)), 5000) * np.exp(-t * 120) * 0.3) * vel

def air(dur, lo=600, hi=6000):
    t = t_arr(dur); p = t / dur
    x = rng.normal(0, 1, len(t)); out = np.zeros_like(x); ch = 1024
    for i in range(0, len(x), ch):
        c = lo + (hi - lo) * p[i]
        out[i:i + ch] = bp(x[i:i + ch], c * 0.6, min(c * 1.5, 18000))[:len(out[i:i + ch])]
    return out * np.sin(np.pi * p) ** 2

def line_tone(dur):                                    # soft tonal swell for line draws
    t = t_arr(dur); p = t / dur
    return np.sin(2 * np.pi * np.cumsum(660 + 220 * p) / SR) * np.sin(np.pi * p) ** 2 * 0.3

def sub_swell(dur):
    t = t_arr(dur)
    return np.sin(2 * np.pi * 42 * t) * np.sin(np.pi * t / dur) ** 2

# ---------------------------------------------------------------- music (80 BPM, D major / B minor)
BEAT = 0.75
music = np.zeros(N); sfx = np.zeros(N)
prog = [[50, 62, 66, 69], [47, 62, 66, 71], [43, 59, 62, 67], [45, 61, 64, 69]]   # D  Bm  G  A
t0 = 0.0; k = 0
while t0 < TOTAL:
    c = prog[k % 4]
    bright = 700 if t0 < 5 else 1200 if t0 < 30 else 1500
    add(music, pad(c[1:], 6.4, bright), t0, 0.5)
    add(music, lp(np.sin(2 * np.pi * mf(c[0] - 12) * t_arr(6.0)) * np.minimum(1, t_arr(6.0) / 0.4) *
                  np.minimum(1, (6.0 - t_arr(6.0)) / 0.4), 180), t0, 0.25)
    t0 += 6.0; k += 1
for tm, n in [(0.4, 74), (1.6, 78), (2.8, 81), (4.0, 78)]:                         # opening motif
    add(music, piano(n, 3.0, 0.5), tm)
for i in range(int((TOTAL - 5.0) / BEAT)):                                          # soft rhythm from scene 2
    tb = 5.0 + i * BEAT
    if 29.6 <= tb < 30.8 or tb > 38.5: continue
    add(music, pulse(0.45), tb)
    if 17.8 <= tb < 29.6: add(music, tick(0.10, 5200), tb + BEAT / 2)
for i in range(int((29.6 - 11.6) / (BEAT / 2))):                                    # sparse piano 8ths
    tb = 11.6 + i * BEAT / 2
    if i % 3: continue
    c = prog[int(tb // 6) % 4]
    add(music, piano(c[1 + (i // 3) % 3] + 12, 2.0, 0.28), tb)
add(music, sub_swell(3.0), 10.0, 0.25); add(music, sub_swell(3.0), 28.0, 0.3)       # low-frequency movement
for tm, n in [(30.4, 74), (31.3, 78), (32.2, 81), (35.0, 86)]:                     # resolve
    add(music, piano(n, 4.0, 0.5), tm)
add(music, pad([62, 66, 69, 74], 10.0, 1400), 30.4, 0.45)

# ---------------------------------------------------------------- sound design synced to the graphics
add(sfx, line_tone(1.4), 0.3, 0.5)                                                  # opening line draws
for tm in [1.35, 2.9, 5.55, 6.85, 7.45, 12.8, 14.45, 19.9, 21.0, 22.15, 24.5, 25.85, 31.25, 35.0]:
    add(sfx, tick(0.35, 2400), tm)                                                  # type reveals
for tm in [4.55, 11.25, 17.35, 23.2, 29.6]:
    add(sfx, air(0.8), tm - 0.05, 0.35)                                             # graphic wipes
for j in range(6):
    add(sfx, tick(0.25, 1800 + 150 * j), 12.2 + j * 0.13)                           # timeline marker travels
add(sfx, line_tone(1.1), 30.4, 0.45)                                                # champagne line crosses
add(sfx, sum(piano(n, 3.0, 0.7) for n in (86, 90, 93)) / 3, 36.5, 0.55)            # logo appears
add(sfx, tick(0.4, 3000), 37.6)                                                     # CTA

# ---------------------------------------------------------------- mix
tt = np.arange(N) / SR
duck = np.ones(N)
for a, b, c in VO:
    s, e = c, c + (b - a)
    duck -= 0.62 * np.clip(np.minimum((tt - (s - 0.25)) / 0.25, ((e + 0.4) - tt) / 0.4), 0, 1)
duck = np.clip(duck, 0.3, 1)

def reverb(x, wet):
    y = np.zeros_like(x)
    for dl, g in [(0.031, .5), (0.049, .42), (0.077, .34), (0.113, .27), (0.17, .2), (0.25, .13), (0.36, .08)]:
        d = int(dl * SR); y[d:] += x[:-d] * g
    return x + wet * lp(y, 6000)

music = hp(reverb(music, 0.35), 30); sfx = hp(reverb(sfx, 0.3), 80)
vo_n = vo / (np.sqrt(np.mean(vo[vo != 0] ** 2)) + 1e-9) * 0.12
mu_n = music / (np.sqrt(np.mean(music ** 2)) + 1e-9) * 0.075
sf_n = sfx / (np.abs(sfx).max() + 1e-9) * 0.06
fade = np.ones(N); f = int(0.8 * SR); fade[-f:] = np.linspace(1, 0, f)
mix = (vo_n + mu_n * duck + sf_n) * fade

os.makedirs(sys.argv[2], exist_ok=True)
peak = np.abs(mix).max()
def write(name, x, mono_to_stereo=True):
    x = x / peak * 0.89
    st = np.stack([x, np.roll(x, 14) * 0.98], 1) if name != "vo_placed.wav" else np.stack([x, x], 1)
    with wave.open(os.path.join(sys.argv[2], name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
write("vo_placed.wav", vo_n * fade); write("music.wav", mu_n * duck * fade); write("sfx.wav", sf_n * fade)
write("mix.wav", mix)
print("ok")
