"""Audio for motion graphics v3: the updated VO is used unedited (offset +0.8 s); documentary music bed
ducked under every spoken phrase; sound design synced to the v3 graphics.
Usage: python mg2_audio.py VO.mp3 OUT_DIR
"""
import os, subprocess, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR, TOTAL, OFF = 44100, 49.5, 0.8
N = int(SR * TOTAL); rng = np.random.default_rng(41)
def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x)
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf): return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
vo_src = np.frombuffer(raw, np.float32).astype(np.float64)
vo = np.zeros(N); add(vo, vo_src, OFF)
# speech segments (VO time) from silence detection, for ducking
SPEECH = [(0.0, 3.23), (4.09, 6.15), (6.67, 9.05), (10.09, 13.91), (14.22, 16.10), (17.01, 19.26), (19.72, 20.38),
          (20.87, 22.74), (23.67, 26.56), (27.31, 29.75), (30.69, 33.12), (33.70, 36.17), (37.04, 38.82),
          (39.46, 41.18), (41.53, 43.42), (44.07, 45.71)]

def pad(notes, dur, bright=1000):
    t = t_arr(dur); x = np.zeros_like(t)
    for n in notes:
        for det in (-0.05, 0.05):
            f = mf(n) * 2 ** (det / 12); x += np.sin(2 * np.pi * f * t + 0.5 * np.sin(2 * np.pi * f * 2 * t))
    return lp(x / (2 * len(notes)), bright) * np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5)
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
    t = t_arr(dur); p = t / dur; x = rng.normal(0, 1, len(t)); out = np.zeros_like(x)
    for i in range(0, len(x), 1024):
        c = lo + (hi - lo) * p[i]; out[i:i + 1024] = bp(x[i:i + 1024], c * 0.6, min(c * 1.5, 18000))[:len(out[i:i + 1024])]
    return out * np.sin(np.pi * p) ** 2
def line_tone(dur):
    t = t_arr(dur); p = t / dur
    return np.sin(2 * np.pi * np.cumsum(660 + 220 * p) / SR) * np.sin(np.pi * p) ** 2 * 0.3
def sub_swell(dur):
    t = t_arr(dur); return np.sin(2 * np.pi * 42 * t) * np.sin(np.pi * t / dur) ** 2

music = np.zeros(N); sfx = np.zeros(N); BEAT = 0.75
prog = [[50, 62, 66, 69], [47, 62, 66, 71], [43, 59, 62, 67], [45, 61, 64, 69]]
t0, k = 0.0, 0
while t0 < TOTAL:
    c = prog[k % 4]; bright = 700 if t0 < 4.7 else 1250 if t0 < 37.7 else 1500
    add(music, pad(c[1:], 6.4, bright), t0, 0.5)
    add(music, lp(np.sin(2 * np.pi * mf(c[0] - 12) * t_arr(6.0)) * np.minimum(1, t_arr(6.0) / 0.4) * np.minimum(1, (6.0 - t_arr(6.0)) / 0.4), 180), t0, 0.25)
    t0 += 6.0; k += 1
for tm, n in [(0.3, 74), (1.5, 78), (2.7, 81), (3.9, 78)]: add(music, piano(n, 3.0, 0.5), tm)
for i in range(int((TOTAL - 4.7) / BEAT)):
    tb = 4.7 + i * BEAT
    if 37.25 <= tb < 38.4 or tb > 47.0: continue
    add(music, pulse(0.45), tb)
    if 14.9 <= tb < 37.2: add(music, tick(0.09, 5200), tb + BEAT / 2)
for i in range(int((37.2 - 10.6) / (BEAT / 2))):
    if i % 3: continue
    tb = 10.6 + i * BEAT / 2; c = prog[int(tb // 6) % 4]
    add(music, piano(c[1 + (i // 3) % 3] + 12, 2.0, 0.28), tb)
add(music, sub_swell(3.0), 9.5, 0.25); add(music, sub_swell(3.0), 35.5, 0.3)
for tm, n in [(37.8, 74), (38.7, 78), (39.6, 81), (40.7, 86)]: add(music, piano(n, 4.0, 0.5), tm)
add(music, pad([62, 66, 69, 74], 11.0, 1400), 37.8, 0.45)

add(sfx, line_tone(1.3), 0.25, 0.5)
for tm in [1.05, 2.2, 4.9, 5.6, 6.15, 7.5, 11.05, 12.8, 15.06, 15.62, 17.84, 20.52, 21.71, 24.65, 25.98, 28.25, 28.83,
           31.78, 32.05, 34.53, 36.4, 38.56, 39.16, 42.54, 45.05]:
    add(sfx, tick(0.33, 2400), tm)
for tm in [4.35, 10.25, 14.55, 17.45, 23.65, 30.65, 37.25]: add(sfx, air(0.8), tm - 0.05, 0.33)
for j in range(5): add(sfx, tick(0.25, 1800 + 150 * j), 10.7 + j * 0.1)
add(sfx, line_tone(1.0), 39.8, 0.4)
add(sfx, sum(piano(n, 3.0, 0.7) for n in (86, 90, 93)) / 3, 40.7, 0.55)   # logo appears with "SKN Theory"

tt = np.arange(N) / SR; duck = np.ones(N)
for a, b in SPEECH:
    s, e = a + OFF, b + OFF
    duck -= 0.62 * np.clip(np.minimum((tt - (s - 0.25)) / 0.25, ((e + 0.4) - tt) / 0.4), 0, 1)
duck = np.clip(duck, 0.3, 1)
def reverb(x, wet):
    y = np.zeros_like(x)
    for dl, g in [(0.031, .5), (0.049, .42), (0.077, .34), (0.113, .27), (0.17, .2), (0.25, .13), (0.36, .08)]:
        d = int(dl * SR); y[d:] += x[:-d] * g
    return x + wet * lp(y, 6000)
music = hp(reverb(music, 0.35), 30); sfx = hp(reverb(sfx, 0.3), 80)
vo_n = vo / (np.sqrt(np.mean(vo[np.abs(vo) > 1e-4] ** 2)) + 1e-9) * 0.12
mu_n = music / (np.sqrt(np.mean(music ** 2)) + 1e-9) * 0.075
sf_n = sfx / (np.abs(sfx).max() + 1e-9) * 0.06
fade = np.ones(N); f = int(0.8 * SR); fade[-f:] = np.linspace(1, 0, f)
mix = (vo_n + mu_n * duck + sf_n) * fade
os.makedirs(sys.argv[2], exist_ok=True); peak = np.abs(mix).max()
def write(name, x, stereo_spread=True):
    x = x / peak * 0.89
    st = np.stack([x, np.roll(x, 14) * 0.98], 1) if stereo_spread else np.stack([x, x], 1)
    with wave.open(os.path.join(sys.argv[2], name), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
write("vo.wav", vo_n * fade, False); write("music.wav", mu_n * duck * fade); write("sfx.wav", sf_n * fade); write("mix.wav", mix)
print("ok")
