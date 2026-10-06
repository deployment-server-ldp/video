"""Product-flex fashion reel from 5 iPhone clips (1080x1920 @30fps, ~30.5s).

Expects SDR-converted clips p1.mp4..p5.mp4 (see README) in the working directory.
Usage: python reel2.py out.mp4 | python reel2.py --frames 1,5,...
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "fonts")
CACHE = os.environ.get("CACHE", "cache")
BEAT = 0.625  # 96 BPM
IVORY = (250, 245, 236); GOLD = (214, 178, 108); WHITE = (255, 255, 255)

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3
def ei(p): return clamp(p) ** 3
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)

@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    if var: f.set_variation_by_name(var)
    return f
SERIF = lambda s, v="Regular": font("Playfair.ttf", s, v)
ITAL = lambda s, v="Italic": font("PlayfairItalic.ttf", s, v)
SANS = lambda s, v="Medium": font("Montserrat.ttf", s, v)

# ------------------------------------------------------------------ segments
class Seg:
    def __init__(self, start, dur, clip, src, speed=1.0, z0=1.04, z1=1.1, pan=(0, 0)):
        self.start, self.dur, self.end = start, dur, start + dur
        self.clip, self.src, self.speed, self.z0, self.z1, self.pan = clip, src, speed, z0, z1, pan
        self.key = f"s{start:05.2f}"

    def src_time(self, t): return self.src + (t - self.start) * self.speed
    def zoom(self, t): return self.z0 + (self.z1 - self.z0) * eio((t - self.start) / self.dur)

q = BEAT
SEGS = [
    Seg(0.0, 2.5, 5, 0.3, 0.7, 1.16, 1.06),            # hook: neckline close-up
    Seg(2.5, 5.0, 2, 2.4, 0.9, 1.02, 1.10),            # hero walk-in
    Seg(7.5, 2.5, 4, 0.0, 2.0, 1.04, 1.12),            # hem -> neckline pan (sped up)
    Seg(10.0, 2.5, 5, 5.0, 0.8, 1.10, 1.20),           # sleeve motif
    Seg(12.5, 2.5, 3, 6.2, 0.7, 1.06, 1.00),           # dupatta flow (slow-mo)
    Seg(15.0, 2.5, 1, 8.0, 1.0, 1.08, 1.00),           # lifestyle
    Seg(17.5, 2.5, 2, 6.3, 0.8, 1.00, 1.10),           # turn with dupatta
    Seg(20.0, q, 5, 1.5, 1.0, 1.22, 1.16),             # flurry x4
    Seg(20.0 + q, q, 4, 8.5, 1.0, 1.15, 1.10),
    Seg(20.0 + 2 * q, q, 5, 9.0, 1.0, 1.15, 1.10),
    Seg(20.0 + 3 * q, q, 3, 4.5, 1.0, 1.10, 1.04),
    Seg(22.5, 2.5, 3, 3.0, 1.0, 1.00, 1.08),           # walk forward
    Seg(25.0, 2.5, 2, 8.8, 0.85, 1.02, 1.10),          # mirror
    Seg(27.5, 3.0, 5, 1.0, 0.5, 1.10, 1.18),           # outro plate
]
TOTAL = 30.5
MARGIN = 0.4

def seg_at(t):
    for s in SEGS:
        if s.start <= t < s.end: return s
    return SEGS[-1]

# ------------------------------------------------------------------ frame cache (raw memmaps on disk)
_mm = {}

def prepare():
    os.makedirs(CACHE, exist_ok=True)
    jobs = []
    for s in SEGS:
        path = os.path.join(CACHE, s.key + ".rgb")
        a = max(0.0, s.src - MARGIN * s.speed)
        dur = (s.dur + 2 * MARGIN) * s.speed
        meta = path + ".txt"
        if os.path.exists(meta): continue
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", f"p{s.clip}.mp4",
               "-vf", "eq=contrast=1.05:saturation=1.06:gamma=0.98,colorbalance=rh=0.02:bh=-0.02",
               "-f", "rawvideo", "-pix_fmt", "rgb24", path]
        jobs.append((subprocess.Popen(cmd), path, meta, a))
    for p, path, meta, a in jobs:
        p.wait()
        open(meta, "w").write(str(a))

def frames(s):
    if s.key not in _mm:
        path = os.path.join(CACHE, s.key + ".rgb")
        a = float(open(path + ".txt").read())
        n = os.path.getsize(path) // (W * H * 3)
        _mm[s.key] = (np.memmap(path, np.uint8, "r", shape=(n, H, W, 3)), a)
    return _mm[s.key]

def get_src(s, t):
    mm, a = frames(s)
    fs = (s.src_time(t) - a) * FPS
    n = len(mm)
    i = int(math.floor(fs)); f = fs - i
    i0 = min(max(i, 0), n - 1); i1 = min(i0 + 1, n - 1)
    if f < 0.2 or i0 == i1: return np.asarray(mm[i0])
    if f > 0.8: return np.asarray(mm[i1])
    return (mm[i0] * (1 - f) + mm[i1] * f).astype(np.uint8)  # frame blend for slow-mo

def beat_pulse(t):
    if t < 2.5 or t >= 27.5: return 1.0
    ph = (t - 2.5) % (2 * BEAT)
    return 1.0 + 0.012 * math.exp(-ph * 8)

def clip(s, t, extra=1.0, off=(0, 0)):
    img = Image.fromarray(get_src(s, t))
    z = max(1.0, s.zoom(t) * extra * beat_pulse(t))
    cw, ch = W / z, H / z
    cx = min(max(W / 2 + s.pan[0] + off[0] / z, cw / 2), W - cw / 2)
    cy = min(max(H / 2 + s.pan[1] + off[1] / z, ch / 2), H - ch / 2)
    return img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))

# ------------------------------------------------------------------ looks
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((XX - W / 2) / (W * 0.7)) ** 2 + ((YY - H / 2) / (H * 0.65)) ** 2)
VIG = np.clip(1 - 0.35 * np.clip(_r - 0.45, 0, None) ** 1.6, 0.5, 1)[..., None].astype(np.float32)
_l = np.exp(-(((XX - W * 1.0) / (W * 0.6)) ** 2 + ((YY - H * 0.2) / (H * 0.5)) ** 2))
LEAK = np.stack([_l * 255, _l * 170, _l * 90], -1).astype(np.float32)
BOT = (np.clip((YY - 900) / 520, 0, 1) ** 1.2 * 0.72 * (1 - np.clip((YY - 1650) / 400, 0, 1) * 0.3))[..., None].astype(np.float32)
del _r, _l, YY, XX
GRAIN = [np.random.default_rng(i).normal(0, 3.5, (H // 2, W // 2, 1)).astype(np.float32) for i in range(5)]

def bloom(img, k=0.22):
    small = img.resize((W // 4, H // 4), Image.BILINEAR)
    a = np.asarray(small, np.float32)
    a = np.clip(a - 175, 0, None) * 2.2
    b = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    return np.asarray(b, np.float32) * k

def hblur(arr, L, axis=1):
    L = int(L)
    if L < 3: return arr.astype(np.float32)
    pw = [(0, 0)] * 3; pw[axis] = (L, L)
    c = np.cumsum(np.pad(arr.astype(np.float32), pw, mode="edge"), axis=axis)
    n = arr.shape[axis]
    sl_a = [slice(None)] * 3; sl_b = [slice(None)] * 3
    sl_a[axis] = slice(2 * L, 2 * L + n); sl_b[axis] = slice(L, L + n)
    return (c[tuple(sl_a)] - c[tuple(sl_b)]) / L

def zoom_blur(img, s, n=5):
    if s < 0.03: return img
    acc = np.zeros((H, W, 3), np.float32)
    for i in range(n):
        z = 1 + 0.12 * s * i / (n - 1)
        cw, ch = W / z, H / z
        acc += np.asarray(img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))

# ------------------------------------------------------------------ text
@functools.lru_cache(maxsize=4096)
def glyph(s, fnt, color):
    l, t, r, b = fnt.getbbox(s)
    im = Image.new("RGBA", (max(1, r + 8), max(1, b + 8)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), s, font=fnt, fill=color + (255,))
    return np.asarray(im).astype(np.float32)

def blit(layer, g, x, y, a):
    if a <= 0.004: return
    g = g.copy(); g[..., 3] *= a
    layer.alpha_composite(Image.fromarray(g.astype(np.uint8)), (int(x), int(y)))

def text(layer, s, fnt, x, y, lt, t0, color=WHITE, sp=0, stagger=0.03, dur=0.5, rise=30, t_out=None, blur_in=False):
    if lt < t0: return
    tw = sum(fnt.getlength(c) + sp for c in s) - sp
    cx = x - tw / 2
    out = 1.0 if t_out is None else 1 - eio((lt - t_out) / 0.4)
    if out <= 0: return
    for i, c in enumerate(s):
        adv = fnt.getlength(c) + sp
        if c != " ":
            p = clamp((lt - t0 - i * stagger) / dur)
            if p > 0:
                blit(layer, glyph(c, fnt, color), cx, y + (1 - eo(p)) * rise, eo(p) * out)
        cx += adv

def line(layer, y, length, lt, t0, t_out=None, color=GOLD):
    p = eo((lt - t0) / 0.6)
    if t_out is not None: p *= 1 - eio((lt - t_out) / 0.4)
    if p <= 0: return
    d = ImageDraw.Draw(layer)
    L = length * p
    d.rectangle((W / 2 - L / 2, y, W / 2 + L / 2, y + 2), fill=color + (255,))

def shadow_comp(img, layer, r=14, k=0.85):
    bb = layer.getbbox()
    if not bb: return img
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(r))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: int(v * k)))
    out = img.convert("RGBA"); out.alpha_composite(sh, (0, 4)); out.alpha_composite(layer)
    return out.convert("RGB")

TITLES = [  # (start, end, kind, lines)
    (0.25, 2.3, "hook", ("NEW ARRIVAL", "The Ivory Edit")),
    (10.25, 12.3, "cap", ("Embroidered", "details")),
    (12.75, 14.8, "cap", ("Effortless", "elegance")),
    (15.25, 17.3, "cap", ("Made for", "your moments")),
    (22.75, 24.8, "cap", ("Grace in", "every step")),
]

def titles(img, t):
    layer = None
    for t0, t1, kind, (a, b) in TITLES:
        if not (t0 <= t <= t1 + 0.4): continue
        lt = t - t0; to = t1 - t0 - 0.35
        layer = layer or Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if kind == "hook":
            text(layer, a, SANS(40, "Bold"), W / 2, 1150, lt, 0.0, GOLD, sp=12, stagger=0.02, t_out=to)
            line(layer, 1222, 300, lt, 0.2, to)
            text(layer, b, ITAL(132, "SemiBold Italic"), W / 2, 1245, lt, 0.3, WHITE, stagger=0.04, dur=0.6, t_out=to)
        else:
            text(layer, a, SANS(44, "Bold"), W / 2, 1180, lt, 0.0, GOLD, sp=10, stagger=0.02, t_out=to)
            text(layer, b, ITAL(128, "SemiBold Italic"), W / 2, 1240, lt, 0.15, WHITE, stagger=0.035, dur=0.6, t_out=to)
    if layer is None: return img, 0.0
    return layer, 1.0

def outro(img, t):
    lt = t - 27.5
    arr = np.asarray(img.filter(ImageFilter.GaussianBlur(6 * eo(lt / 0.8))), np.float32)
    arr *= 1 - 0.55 * eo(lt / 0.8)
    img = Image.fromarray(arr.astype(np.uint8))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text(layer, "SECRET CLOSET", SERIF(100, "Medium"), W / 2, 760, lt, 0.3, IVORY, sp=4, stagger=0.05, dur=0.7, rise=40)
    line(layer, 905, 380, lt, 0.9)
    text(layer, "by AshKash", ITAL(76), W / 2, 925, lt, 1.0, GOLD, stagger=0.04)
    text(layer, "DM TO ORDER", SANS(42, "Bold"), W / 2, 1100, lt, 1.5, IVORY, sp=10, stagger=0.02)
    return shadow_comp(img, layer)

# ------------------------------------------------------------------ transitions
CUTS = {s.start: i for i, s in enumerate(SEGS)}

def base(t):
    """Picture before text: clips + transitions at cut points."""
    s = seg_at(t)
    i = SEGS.index(s)
    flash = leak = 0.0
    def nearest_cut():
        best = None
        for c in CUTS:
            if c > 0 and abs(t - c) < 0.35 and (best is None or abs(t - c) < abs(t - best)): best = c
        return best
    c = nearest_cut()
    if c is None:
        return clip(s, t), flash, leak
    a, b = SEGS[CUTS[c] - 1], SEGS[CUTS[c]]
    kind = {2.5: "flash", 7.5: "whip", 10.0: "zoom", 12.5: "leak", 15.0: "vwhip", 17.5: "flash",
            20.0: "punch", 22.5: "whip", 25.0: "leak", 27.5: "dissolve"}.get(round(c, 3), "cut")
    if kind == "flash":
        img = clip(b, t, 1 + 0.25 * (1 - eo((t - c) / 0.5))) if t >= c else clip(a, t)
        flash = clamp(1 - abs(t - c) / 0.18) * 0.9
    elif kind in ("whip", "vwhip"):
        w = 0.25
        if abs(t - c) > w: return clip(s, t), 0, 0
        p = eio((t - (c - w)) / (2 * w))
        horiz = kind == "whip"
        size = W if horiz else H
        off = p * size
        cv = Image.new("RGB", (W, H))
        ia, ib = clip(a, t), clip(b, t)
        if horiz:
            cv.paste(ia, (int(-off), 0)); cv.paste(ib, (int(size - off), 0))
        else:
            cv.paste(ia, (0, int(-off))); cv.paste(ib, (0, int(size - off)))
        vel = 6 * p * (1 - p)
        img = Image.fromarray(np.clip(hblur(np.asarray(cv), 220 * vel, 1 if horiz else 0), 0, 255).astype(np.uint8))
    elif kind == "zoom":
        w = 0.25
        if abs(t - c) > w: return clip(s, t), 0, 0
        if t < c:
            p = (t - (c - w)) / w; img = zoom_blur(clip(a, t, 1 + 0.4 * p * p), p)
        else:
            p = (t - c) / w; img = zoom_blur(clip(b, t, 1 + 0.4 * (1 - p) ** 2), 1 - p)
        flash = 0.25 * clamp(1 - abs(t - c) / 0.1)
    elif kind in ("leak", "dissolve"):
        w = 0.3
        p = eio((t - (c - w)) / (2 * w))
        img = Image.blend(clip(a, t), clip(b, t), p)
        leak = math.sin(math.pi * p) * (1.0 if kind == "leak" else 0.3)
    elif kind == "punch":
        img = clip(b, t, 1 + 0.12 * (1 - eo((t - c) / 0.3))) if t >= c else clip(a, t)
        flash = clamp(1 - abs(t - c) / 0.12) * 0.6
    else:
        img = clip(s, t)
    # flurry cuts: punch-in on every cut inside 20..22.5
    return img, flash, leak

def compose(t):
    s = seg_at(t)
    if 20.0 < t < 22.5 and s.start > 20.0 and t - s.start < 0.3:   # flurry punches
        img = clip(s, t, 1 + 0.12 * (1 - eo((t - s.start) / 0.3))); flash = clamp(1 - (t - s.start) / 0.1) * 0.5; leak = 0
    else:
        img, flash, leak = base(t)
    arr = np.asarray(img, np.float32)
    if t >= 27.5:
        img = outro(img, t); arr = np.asarray(img, np.float32)
    else:
        layer, has = titles(img, t)
        if has:
            k = 1.0
            arr = arr * (1 - BOT * k)
            img = shadow_comp(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), layer)
            arr = np.asarray(img, np.float32)
    arr = arr + bloom(img)
    arr = arr * VIG
    if leak > 0.01: arr = 255 - (255 - arr) * (1 - LEAK / 255 * leak)
    if flash > 0.01: arr = arr + (255 - arr) * flash
    arr = arr + np.repeat(np.repeat(GRAIN[int(t * FPS) % 5], 2, 0), 2, 1)
    k = min(clamp(t / 0.35), clamp((TOTAL - t) / 0.6))
    return Image.fromarray(np.clip(arr * k, 0, 255).astype(np.uint8))

def render_range(job):
    i0, i1, path = job
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        enc.stdin.write(compose(i / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    return path

if __name__ == "__main__":
    prepare()
    if "--frames" in sys.argv:
        for tt in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            compose(tt).save(f"r_{tt:05.2f}.jpg", quality=88)
        sys.exit()
    out = sys.argv[1] if len(sys.argv) > 1 else "reel_video.mp4"
    import multiprocessing as mp
    N = int(TOTAL * FPS); n = 4
    b = np.linspace(0, N, n + 1).astype(int)
    with mp.get_context("fork").Pool(n) as pool:
        parts = pool.map(render_range, [(b[k], b[k + 1], f"rpart{k}.mp4") for k in range(n)])
    open("rparts.txt", "w").writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "rparts.txt", "-c", "copy", out], check=True)
    print("done", out)
