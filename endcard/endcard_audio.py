"""Soft audio sting for the end card: rolling F-major piano chord, shimmer and a pad (4.5 s)."""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR, DUR = 44100, 4.5
N = int(SR * DUR)
def t_arr(d): return np.arange(int(SR * d)) / SR
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, x, t0, g=1.0):
    i = int(t0 * SR); x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g
def piano(n, d=3.5, vel=1.0):
    t = t_arr(d); f = mf(n)
    x = sum(np.sin(2 * np.pi * f * k * t) * 0.55 ** (k - 1) * np.exp(-t * (0.9 + 0.8 * k)) for k in range(1, 6))
    return x * np.minimum(1, t / 0.004) * vel
def chime(n, d=2.5):
    t = t_arr(d)
    return (np.sin(2 * np.pi * mf(n) * t) + 0.3 * np.sin(2 * np.pi * mf(n) * 2.76 * t)) * np.exp(-t * 3)
out = np.zeros(N)
for k, n in enumerate([41, 53, 60, 65, 69, 72, 77]):         # rolling F major as the emblem opens
    add(out, piano(n, 3.8, 0.9 if k else 1.0), 0.15 + k * 0.11, 0.35)
for k, n in enumerate([89, 93, 96, 101]):                     # sparkle on the title shimmer
    add(out, chime(n), 2.45 + k * 0.07, 0.06)
t = t_arr(DUR)
pad = sum(np.sin(2 * np.pi * mf(n) * t + np.sin(2 * np.pi * 0.3 * t)) for n in (65, 69, 72)) / 3
out += sosfilt(butter(2, 1500, "low", fs=SR, output="sos"), pad) * np.minimum(1, t / 0.8) * 0.12
y = np.zeros_like(out)                                        # small room
for dl, g in [(0.037, .45), (0.061, .35), (0.093, .28), (0.141, .2), (0.211, .13)]:
    y[int(dl * SR):] += out[:-int(dl * SR)] * g
out = out + 0.5 * y
fo = int(1.0 * SR); out[-fo:] *= np.linspace(1, 0, fo)
out = out / np.abs(out).max() * 0.85
st = np.stack([out, np.roll(out, 20) * 0.97], 1)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
