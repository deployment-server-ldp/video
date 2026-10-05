"""Synthesised 120 BPM soundtrack + SFX, synced to render.py's timeline. Writes music.wav.

Usage: python audio.py src.mp4 out.wav
"""
import subprocess, sys
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(3)

def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)

def add(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    x = x[:len(buf) - i]
    buf[i:i + len(x)] += x * g

def note(n): return 440.0 * 2 ** ((n - 69) / 12)

def kick():
    t = t_arr(0.45)
    f = 45 + 110 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.2 * np.sin(ph) * np.exp(-t * 7)) + 0.3 * hp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 120)

def clap():
    t = t_arr(0.3)
    env = np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
    return bp(rng.normal(0, 1, len(t)), 900, 5000) * env * 0.7

def hat(open_=False):
    t = t_arr(0.25 if open_ else 0.06)
    return hp(rng.normal(0, 1, len(t)), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.35

def saw(f, d):
    t = t_arr(d)
    out = np.zeros_like(t)
    for det in (-0.08, 0, 0.08):
        ff = f * 2 ** (det / 12)
        out += 2 * ((t * ff + rng.random()) % 1) - 1
    return out / 3

def boom(d=2.5):
    t = t_arr(d)
    f = 30 + 90 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    noise = lp(rng.normal(0, 1, len(t)), 1800) * np.exp(-t * 3.5)
    crack = hp(rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 18)
    glass = np.zeros_like(t)
    for _ in range(40):  # glass tinkles
        st = rng.uniform(0.02, 0.9); fr = rng.uniform(2500, 7000)
        tt = t - st
        glass += (tt > 0) * np.sin(2 * np.pi * fr * tt) * np.exp(-np.clip(tt, 0, None) * rng.uniform(25, 60)) * rng.uniform(0.1, 0.3)
    return np.tanh(1.6 * sub) * 0.9 + noise * 0.5 + crack * 0.35 + glass * 0.35

def riser(d):
    t = t_arr(d)
    p = t / d
    x = rng.normal(0, 1, len(t))
    # sweep filter by chunked band-pass
    out = np.zeros_like(x)
    ch = 2048
    for i in range(0, len(x), ch):
        f = 300 + 7000 * p[i] ** 2
        out[i:i + ch] = bp(x[i:i + ch + 0], f * 0.7, min(f * 1.4, 20000))[:len(out[i:i + ch])]
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * p ** 2) / SR) * 0.25
    return (out * 0.6 + tone) * p ** 1.5

def whoosh(d=0.45):
    t = t_arr(d)
    env = np.sin(np.pi * t / d) ** 2
    x = rng.normal(0, 1, len(t))
    return bp(x, 400, 4000) * env * 0.8

def glitch_sfx(d=0.3):
    t = t_arr(d)
    sq = np.sign(np.sin(2 * np.pi * (300 + 2000 * rng.random()) * t)) * (np.sin(2 * np.pi * 40 * t) > 0)
    return (sq * 0.3 + hp(rng.normal(0, 1, len(t)), 2000) * 0.3) * np.exp(-t * 6)

music = np.zeros(N)
sfx = np.zeros(N)

# chord roots per bar (2 s): Am F C G
prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]

# pad over whole piece
for b in range(15):
    root, ch = prog[b % 4]
    pad = sum(saw(note(n + 12), 2.0) for n in ch) / 3
    pad = lp(pad, 1400) * np.minimum(1, t_arr(2.0) / 0.3)
    add(music, pad, b * 2.0, 0.18)

# intro: riser into the drop at 3.0
add(music, riser(2.6), 0.4, 0.55)
for b in range(3):
    add(music, hat(), 1.5 + b * 0.5, 0.5)

# main groove 3.0 – 25.0 ; short break 9.5–10.0 and 24.5–25
for i in range(int((25.0 - 3.0) / 0.5)):
    tb = 3.0 + i * 0.5
    brk = 9.5 <= tb < 10.0 or 24.5 <= tb < 25.0 or 16.0 <= tb < 16.5
    if not brk:
        add(music, kick(), tb, 0.9)
        if i % 2 == 1: add(music, clap(), tb, 0.6)
    add(music, hat(), tb + 0.25, 0.6)
    if i % 4 == 3: add(music, hat(True), tb + 0.25, 0.4)
    if not brk:
        for k in range(2):  # 8th-note bass
            bar = int((tb - 3.0) // 2.0)
            root = prog[(bar + 1) % 4][0] - 24
            bs = saw(note(root), 0.24)
            bs = lp(bs, 380) * np.exp(-t_arr(0.24) * 5)
            add(music, np.tanh(bs * 2), tb + k * 0.25, 0.42)

# arp lead in the second half for lift
for i in range(int((25.0 - 14.0) / 0.125)):
    tb = 14.0 + i * 0.125
    if 16.0 <= tb < 16.5 or 24.5 <= tb: continue
    bar = int((tb - 3.0) // 2.0)
    ch = prog[(bar + 1) % 4][1]
    n = ch[i % 3] + 24
    t = t_arr(0.12)
    tone = np.sign(np.sin(2 * np.pi * note(n) * t)) * np.exp(-t * 25)
    add(music, lp(tone, 3500), tb, 0.07)

# outro: final chord swell then fade
pad = sum(saw(note(n + 12), 5.0) for n in [57, 60, 64, 69]) / 4
add(music, lp(pad, 1800) * np.exp(-t_arr(5.0) * 0.6), 25.0, 0.3)

# SFX synced with picture
for T in (3.0, 10.0, 25.0):
    add(sfx, boom(), T, 1.0)
add(sfx, riser(0.6), 9.4, 0.5)
add(sfx, riser(0.6), 24.4, 0.5)
for T in (5.5, 14.0, 22.5):
    add(sfx, whoosh(), T - 0.25, 0.7)
add(sfx, whoosh(0.7), 16.2, 0.8)
for T in (7.5, 20.0):
    add(sfx, glitch_sfx(), T - 0.1, 0.6)
for T in (3.55, 11.0, 14.25, 17.0, 20.25, 22.75):  # title "ticks"
    add(sfx, hp(rng.normal(0, 1, 2000), 4000) * np.exp(-t_arr(2000 / SR) * 80), T, 0.4)

# original machine sound, synced to clip source times (render.py SEGS)
def src_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)

machine = np.zeros(N)
if len(sys.argv) > 1:
    a = src_audio(sys.argv[1])
    for start, dur, src in [(3.0, 2.5, 3.0), (5.5, 2.0, 7.0), (7.5, 2.5, 9.0), (10.0, 4.0, 12.0),
                            (14.0, 2.5, 15.5), (16.5, 3.5, 30.6), (20.0, 2.5, 38.6), (22.5, 2.5, 41.9)]:
        seg = a[int(src * SR):int((src + dur) * SR)].copy()
        f = int(0.03 * SR)
        seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        add(machine, seg, start, 1.0)
    machine = hp(machine, 120)
    machine /= (np.abs(machine).max() + 1e-9)

# duck music under booms
duck = np.ones(N)
for T in (3.0, 10.0, 25.0):
    t = t_arr(0.8); add(duck, -0.5 * np.exp(-t * 4), T)

stems = {"music": music * 0.55 * duck, "sfx": sfx * 0.75, "machine": machine * 0.22}
mix = sum(stems.values())
fade = int(0.8 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
mix = np.tanh(mix * 1.1) * 0.9
mix /= np.abs(mix).max() / 0.95
stereo = np.stack([mix, np.roll(mix, 12) * 0.98], 1)  # tiny Haas widening
pcm = (stereo * 32767).astype(np.int16)
out = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
import os, wave

def write_wav(path, x):
    st = np.stack([x, np.roll(x, 12) * 0.98], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())

with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("wrote", out)

# separate stems for editing in other apps (STEMS_DIR=...)
if os.environ.get("STEMS_DIR"):
    d = os.environ["STEMS_DIR"]
    for name, x in stems.items():
        x = x.copy(); x[-fade:] *= np.linspace(1, 0, fade)
        write_wav(os.path.join(d, f"{name}.wav"), x / (np.abs(x).max() + 1e-9) * 0.9)
    print("wrote stems to", d)
