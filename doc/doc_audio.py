"""Ambient documentary score for doc.py (piano + pad + drone + transition swells). Writes a WAV.

Usage: python doc_audio.py out.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
SCENES = [9.0, 13.0, 11.0, 12.0, 14.0, 10.0, 15.0, 9.0]
TOTAL = sum(SCENES)
N = int(SR * TOTAL)
rng = np.random.default_rng(5)

def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def note(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

def piano(n, d=3.5, vel=1.0):
    t = t_arr(d); f = note(n)
    x = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k)) * (0.6 ** (k - 1)) * np.exp(-t * (1.2 + 0.8 * k))
            for k in range(1, 6))
    att = np.minimum(1, t / 0.004)
    return x * att * vel * 0.35

def pad(notes, d):
    t = t_arr(d)
    x = np.zeros_like(t)
    for n in notes:
        for det in (-0.06, 0.06):
            f = note(n) * 2 ** (det / 12)
            x += 2 * ((t * f + rng.random()) % 1) - 1
    x = lp(x / (2 * len(notes)), 900)
    env = np.minimum(1, t / 1.5) * np.minimum(1, (d - t) / 1.5)
    return x * env

def swell(d=1.6):
    t = t_arr(d); p = t / d
    x = lp(rng.normal(0, 1, len(t)), 2500) * np.sin(np.pi * p) ** 2
    return x * 0.5

# Dm9 - Bbmaj7 - Fmaj7 - C(add9) ; 4.5 s per chord (slow, ~53 BPM feel)
prog = [[50, 57, 60, 64, 65], [46, 53, 57, 62, 65], [41, 53, 57, 60, 64], [48, 55, 60, 62, 67]]
CH = 4.5
music = np.zeros(N)
k = 0; tc = 0.0
while tc < TOTAL:
    ch = prog[k % 4]
    add(music, pad(ch[1:], CH + 1.5), tc, 0.35)
    add(music, lp(np.sin(2 * np.pi * note(ch[0] - 12) * t_arr(CH + 1)) * np.minimum(1, t_arr(CH + 1) / 0.8) *
                  np.minimum(1, (CH + 1 - t_arr(CH + 1)) / 0.8), 400), tc, 0.35)
    # sparse arpeggio, more motion after the intro
    pattern = [0, 2, 3, 4, 3, 2] if tc > 9 else [2, 4]
    step = CH / len(pattern)
    for j, idx in enumerate(pattern):
        add(music, piano(ch[idx] + 12, vel=0.7 + 0.3 * rng.random()), tc + j * step, 0.9)
    tc += CH; k += 1

sfx = np.zeros(N)
acc = 0.0
for d in SCENES[:-1]:
    acc += d
    add(sfx, swell(), acc - 1.0, 0.55)
    add(sfx, piano(86, 4.0, 0.6) + piano(81, 4.0, 0.4), acc, 0.8)  # chime at each chapter
add(sfx, piano(62, 6, 1.0) + piano(69, 6, 0.8) + piano(74, 6, 0.7), 4.0, 0.9)  # title hit
add(sfx, piano(62, 6, 1.0) + piano(69, 6, 0.8) + piano(77, 6, 0.7), TOTAL - 5.4, 0.9)  # outro title hit

# simple stereo reverb-ish tail: sum of delayed, filtered copies
mix = music * 0.8 + sfx
wet = np.zeros_like(mix)
for dl, g in [(0.031, 0.5), (0.047, 0.45), (0.071, 0.4), (0.113, 0.33), (0.173, 0.25), (0.251, 0.18)]:
    wet[int(dl * SR):] += mix[:-int(dl * SR)] * g
wet = lp(wet, 4000)
L = mix + 0.6 * wet
R = mix + 0.6 * np.roll(wet, int(0.013 * SR))
st = np.stack([L, R], 1)
fi, fo = int(1.0 * SR), int(2.0 * SR)
st[:fi] *= np.linspace(0, 1, fi)[:, None]; st[-fo:] *= np.linspace(1, 0, fo)[:, None]
st = np.tanh(st / np.abs(st).max() * 1.2) * 0.9
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "doc_music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok", TOTAL)
