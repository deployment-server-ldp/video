"""Original desi track for the reel (royalty-free, synthesised): tabla keherwa, dhol, sitar,
tanpura drone, bass and pad.  96 BPM, D minor (Sa = D).  Timeline matches reel2.py.

Usage: python desi_music.py out.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
TOTAL = 30.5
N = int(SR * TOTAL)
BEAT = 0.625; E8 = BEAT / 2; BAR = 4 * BEAT
rng = np.random.default_rng(21)

def t_arr(d): return np.arange(int(SR * d)) / SR
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b): return sosfilt(butter(2, [a, b], "band", fs=SR, output="sos"), x)
def mf(n): return 440.0 * 2 ** ((n - 69) / 12)

def add(buf, x, t0, g=1.0):
    i = int(round(t0 * SR))
    if i >= len(buf) or i < 0: return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g

def mx(*xs):
    """Sum signals of different lengths."""
    out = np.zeros(max(len(x) for x in xs))
    for x in xs: out[:len(x)] += x
    return out

# ------------------------------------------------------------------ instruments
def ks(freq, dur, decay=0.997, bright=0.6):
    """Karplus-Strong plucked string, processed one period at a time."""
    P = max(2, int(round(SR / freq)))
    total = int(dur * SR)
    out = np.zeros(total + P)
    exc = rng.uniform(-1, 1, P)
    exc = bright * exc + (1 - bright) * np.convolve(exc, np.ones(4) / 4, "same")
    out[:P] = exc
    for s in range(P, total, P):
        prev = out[s - P:s]
        nxt = decay * 0.5 * (prev + np.concatenate([[out[s - P - 1] if s - P - 1 >= 0 else 0], prev[:-1]]))
        out[s:s + P] = nxt[:len(out[s:s + P])]
    return out[:total]

def sitar(n, dur=1.4, vel=1.0, kan=None):
    x = ks(mf(n), dur, 0.9965, 0.85)
    buzz = hp(np.tanh(3.0 * x), 1800) * 0.35          # jawari buzz
    y = x + buzz
    y += 0.25 * ks(mf(n + 12), dur, 0.995, 0.5)       # sympathetic shimmer
    y *= np.minimum(1, t_arr(dur) / 0.002)
    if kan is not None:                               # grace note before the main note
        g = ks(mf(kan), 0.07, 0.99, 0.9) * 0.6
        y = np.concatenate([g, y])[:len(y)]
    return y * vel * 0.5

def tanpura(n, dur=3.0):
    x = ks(mf(n), dur, 0.9993, 0.4)
    x = x + 0.3 * hp(np.tanh(4 * x), 1500)
    return x * np.minimum(1, t_arr(dur) / 0.01) * 0.35

def na(vel=1.0, f0=mf(62) * 1.0):      # dayan open stroke (harmonic, tuned to Sa)
    t = t_arr(0.6)
    x = sum(np.sin(2 * np.pi * f0 * k * t) * a * np.exp(-t * d)
            for k, a, d in [(1, 1.0, 7), (2, 0.6, 9), (3, 0.45, 11), (4, 0.3, 14), (5, 0.2, 18)])
    click = hp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 300) * 0.4
    return (x * 0.5 + click) * vel

def tin(vel=1.0):
    t = t_arr(0.5)
    f0 = mf(62)
    x = np.sin(2 * np.pi * f0 * 2 * t) * np.exp(-t * 6) + 0.4 * np.sin(2 * np.pi * f0 * 3 * t) * np.exp(-t * 9)
    return x * 0.4 * vel

def ti(vel=1.0):                        # closed dayan stroke
    t = t_arr(0.12)
    return (bp(rng.normal(0, 1, len(t)), 1500, 6000) * np.exp(-t * 60) * 0.5 +
            np.sin(2 * np.pi * 600 * t) * np.exp(-t * 50) * 0.3) * vel

def ge(vel=1.0, bend=True):             # bayan with pitch bend (the "gumki")
    t = t_arr(0.7)
    f = 85 + (35 * (1 - np.exp(-t * 8)) if bend else 0)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5) * 0.5 * vel

def ka(vel=1.0):                        # flat bayan slap
    t = t_arr(0.1)
    return lp(rng.normal(0, 1, len(t)), 900) * np.exp(-t * 45) * 0.6 * vel

def dhol_bass(vel=1.0):
    t = t_arr(0.6)
    f = 60 + 70 * np.exp(-t * 25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    return np.tanh(1.8 * x) * 0.6 * vel

def dhol_tilli(vel=1.0):
    t = t_arr(0.15)
    x = bp(rng.normal(0, 1, len(t)), 1200, 7000) * np.exp(-t * 40) + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 35) * 0.5
    return x * 0.55 * vel

def saw_pad(notes, dur):
    t = t_arr(dur)
    x = np.zeros_like(t)
    for n in notes:
        for det in (-0.07, 0.07):
            x += 2 * ((t * mf(n) * 2 ** (det / 12) + rng.random()) % 1) - 1
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.6)
    return lp(x / (2 * len(notes)), 1100) * env

def bass(n, dur):
    t = t_arr(dur)
    x = np.sin(2 * np.pi * mf(n) * t) + 0.3 * np.sin(2 * np.pi * mf(n) * 2 * t)
    return np.tanh(1.5 * x) * np.exp(-t * 2.5) * np.minimum(1, t / 0.005)

def riser(dur):
    t = t_arr(dur); p = t / dur
    x = bp(rng.normal(0, 1, len(t)), 500, 6000) * p ** 2
    return x * 0.5

def boom(dur=2.0):
    t = t_arr(dur)
    f = 40 + 80 * np.exp(-t * 7)
    return np.tanh(1.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)) + \
        lp(rng.normal(0, 1, len(t)), 3000) * np.exp(-t * 6) * 0.4

# ------------------------------------------------------------------ arrangement
drums = np.zeros(N); melody = np.zeros(N); drone = np.zeros(N); low = np.zeros(N); fx = np.zeros(N)

# tanpura drone cycle (Pa Sa Sa Sa-low) through the whole track
cyc = [57, 62, 62, 50]
k = 0; tt = 0.0
while tt < TOTAL:
    add(drone, tanpura(cyc[k % 4], 3.2), tt, 0.8); tt += BAR / 4 * 1.0; k += 1

# intro alaap (0 – 2.5)
for tm, n, kan in [(0.05, 69, None), (0.55, 70, 72), (0.85, 69, None), (1.15, 67, None), (1.45, 65, 67),
                   (1.75, 64, None), (2.0, 62, 64)]:
    add(melody, sitar(n, 1.6, 0.9, kan), tm)
add(fx, riser(2.4), 0.1, 0.6)

# keherwa theka: Dha Ge Na Ti | Na Ka Dhi Na  (8 eighths per bar)
def theka(t0, vel=1.0, fill=False):
    seq = ["dha", "ge", "na", "ti", "na", "ka", "dhi", "na"]
    if fill: seq = ["dha", "ti", "dha", "ti", "dha", "ti", "dha", "dha"]
    for i, b in enumerate(seq):
        tm = t0 + i * E8
        v = vel * (1.0 if i in (0, 4) else 0.8)
        if b in ("dha", "dhi"):
            add(drums, mx(na(v) if b == "dha" else tin(v), ge(v)), tm)
        elif b == "ge": add(drums, ge(v * 0.8), tm)
        elif b == "na": add(drums, na(v * 0.85), tm)
        elif b == "ti": add(drums, ti(v), tm)
        elif b == "ka": add(drums, ka(v), tm)
        # swing ghost notes
        if i % 2 == 1: add(drums, ti(0.35 * vel), tm + E8 / 2)

def dhol_chaal(t0, vel=1.0):
    # bhangra-style: bass on 1 & 3(+), tilli on offbeats
    for i in range(8):
        tm = t0 + i * E8
        if i in (0, 3, 4): add(drums, dhol_bass(vel * (1.0 if i != 3 else 0.7)), tm)
        if i in (1, 2, 5, 6, 7): add(drums, dhol_tilli(vel * (0.9 if i in (2, 6) else 0.6)), tm)

MOTIF = {
    "A": [(0, 74, 1, 76), (1, 72, 1, None), (2, 70, 1, None), (3, 69, 2, 70), (6, 67, 1, None), (7, 69, 1, None)],
    "B": [(0, 70, 1, None), (1, 69, 1, None), (2, 67, 1, None), (3, 65, 1, 67), (4, 67, 3, None), (7, 64, 1, None)],
    "C": [(0, 65, 1, None), (1, 67, 1, None), (2, 69, 2, 70), (4, 72, 1, None), (5, 70, 1, None), (6, 69, 2, None)],
    "D": [(0, 67, 2, 69), (2, 65, 1, None), (3, 64, 1, None), (4, 62, 4, 64)],
}
def phrase(t0, m, vel=1.0, oct_=0):
    for e, n, ln, kan in MOTIF[m]:
        add(melody, sitar(n + oct_, max(0.6, ln * E8 * 2.2), vel, None if kan is None else kan + oct_), t0 + e * E8)

ROOTS = [50, 48, 46, 48]  # D C Bb C
CHORDS = [[62, 65, 69], [60, 64, 67], [58, 62, 65], [60, 64, 67]]
def harmony(t0, bar_i, vel=1.0):
    r = ROOTS[bar_i % 4]
    add(low, saw_pad([n + 12 for n in CHORDS[bar_i % 4]], BAR + 0.3), t0, 0.22 * vel)
    for e in (0, 3, 4, 7):
        add(low, bass(r - 12, E8 * 1.8), t0 + e * E8, 0.28 * vel)

# drop
add(fx, boom(), 2.5, 0.9)
bars = [2.5 + i * BAR for i in range(10)]   # 2.5 ... 25.0
plan = ["A", "B", "C", "D", "A", "C", "B", None, "A", "D"]
for i, (t0, m) in enumerate(zip(bars, plan)):
    if 20.0 <= t0 < 22.5:     # flurry bar: dhol roll + sitar tremolo
        for j in range(16):
            add(drums, dhol_tilli(0.4 + 0.6 * j / 15), t0 + j * E8 / 2)
            if j % 4 == 0: add(drums, dhol_bass(0.9), t0 + j * E8 / 2)
        for j in range(8):
            add(melody, sitar(74 if j % 2 == 0 else 72, 0.5, 0.7), t0 + j * E8)
        add(fx, riser(BAR), t0, 0.35)
        harmony(t0, i, 0.8)
        continue
    theka(t0, 0.9, fill=(t0 == 25.0))
    if t0 >= 12.5: dhol_chaal(t0, 0.8)
    harmony(t0, i)
    phrase(t0, m, 0.95, 12 if 15.0 <= t0 < 20.0 else 0)

# landing on the outro (27.5): big sam hit, then a final descending phrase
add(fx, boom(2.5), 27.5, 0.8)
add(drums, mx(na(1.2), ge(1.2), dhol_bass(1.0)), 27.5)
for tm, n, kan in [(27.5, 74, None), (27.85, 72, None), (28.2, 70, 72), (28.55, 69, None), (28.9, 67, None),
                   (29.25, 65, None), (29.6, 62, 64)]:
    add(melody, sitar(n, 1.8, 0.85, kan), tm)
add(low, saw_pad([62, 65, 69, 74], 3.0), 27.5, 0.28)

# ------------------------------------------------------------------ mix
def reverb(x, wet=0.35):
    y = np.zeros_like(x)
    for dl, g in [(0.029, 0.5), (0.041, 0.45), (0.067, 0.38), (0.097, 0.3), (0.143, 0.24), (0.211, 0.17), (0.3, 0.1)]:
        d = int(dl * SR); y[d:] += x[:-d] * g
    return x + wet * lp(y, 5000)

L = reverb(melody, 0.45) * 1.4 + reverb(drums, 0.18) * 1.0 + drone * 0.5 + low * 0.7 + fx * 0.7
R = reverb(np.roll(melody, 25), 0.45) * 1.4 + reverb(drums, 0.18) * 1.0 + np.roll(drone, 40) * 0.5 + low * 0.7 + fx * 0.7
L, R = hp(L, 38), hp(R, 38)                          # clear sub-rumble
L = L - 0.35 * lp(L, 120); R = R - 0.35 * lp(R, 120)  # tame low end
st = np.stack([L, R], 1)
st = np.tanh(st / np.abs(st).max() * 1.6) / np.tanh(1.6)
fo = int(1.2 * SR); st[-fo:] *= np.linspace(1, 0, fo)[:, None]
st *= 0.93
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "desi.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("ok")
