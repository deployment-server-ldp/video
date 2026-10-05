"""Reel renderer: cigarette machine promo (1080x1920, 30fps).

Usage: python render.py [out.mp4] [--frames t1,t2,...]   (frames mode writes stills for review)
Requires prep.mp4 (stabilised/graded 720x1280 source) in the working directory.
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS = 1080, 1920, 30
DUR = 30.0
SW, SH = 720, 1280
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "fonts"))
PREP = os.environ.get("PREP", "prep.mp4")
# layer switches (used to export CapCut edit-pack layers)
TEXT_ON = os.environ.get("TEXT", "1") == "1"
HUD_ON = os.environ.get("HUD", "1") == "1"

GOLD = (255, 186, 48)
WHITE = (255, 255, 255)
CYAN = (60, 220, 255)

# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def ease_out_cubic(p): return 1 - (1 - p) ** 3
def ease_in_cubic(p): return p ** 3
def ease_in_out(p): return 3 * p * p - 2 * p * p * p
def ease_out_back(p, s=1.7):
    p -= 1
    return p * p * ((s + 1) * p + s) + 1

@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    if var:
        f.set_variation_by_name(var)
    return f

BEBAS = lambda s: font("Bebas.ttf", s)
MONT = lambda s, v="Bold": font("Montserrat.ttf", s, v)

# ---------------------------------------------------------------- source
F = None

def load_source():
    global F
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", PREP, "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    F = np.frombuffer(p.stdout, np.uint8).reshape(-1, SH, SW, 3)

def get_src(fs, span=0.0):
    n = len(F)
    if span > 1.5:  # fast motion: average frames for motion blur
        lo, hi = int(fs - span / 2), int(fs + span / 2)
        idx = np.clip(np.arange(lo, hi + 1), 0, n - 1)
        return F[idx].astype(np.float32).mean(0).astype(np.uint8)
    i = int(math.floor(fs)); a = fs - i
    i0 = min(max(i, 0), n - 1); i1 = min(i0 + 1, n - 1)
    if a < 0.15: return F[i0]
    if a > 0.85: return F[i1]
    return (F[i0] * (1 - a) + F[i1] * a).astype(np.uint8)

# ---------------------------------------------------------------- segments
class Seg:
    def __init__(self, start, dur, src, speed=1.0, z0=1.05, z1=1.12, pan=(0, 0),
                 tag=None, l1=None, l2=None, cap=None, text_in=0.25, text_out=0.35, ramp=None):
        self.start, self.dur, self.src = start, dur, src
        self.end = start + dur
        self.speed_c, self.z0, self.z1, self.pan = speed, z0, z1, pan
        self.tag, self.l1, self.l2, self.cap = tag, l1, l2, cap
        self.text_in, self.text_out = text_in, text_out
        self.ramp = ramp
        if ramp:  # integrate the speed curve
            ts = np.linspace(-1, dur + 1, 4000)
            sp = np.array([ramp(t) for t in ts])
            cum = np.concatenate([[0], np.cumsum((sp[1:] + sp[:-1]) / 2 * np.diff(ts))])
            cum -= np.interp(0, ts, cum)
            self._ts, self._cum = ts, cum

    def speed(self, tl):
        return self.ramp(tl) if self.ramp else self.speed_c

    def src_time(self, tl):
        if self.ramp:
            return self.src + float(np.interp(tl, self._ts, self._cum))
        return self.src + tl * self.speed_c

    def zoom(self, tl):
        return self.z0 + (self.z1 - self.z0) * ease_in_out(clamp(tl / self.dur))


def ramp_f(t):  # slow -> fast -> slow speed ramp
    if t < 1.2: return 0.5
    if t < 1.6: return 0.5 + (2.6 - 0.5) * ease_in_out((t - 1.2) / 0.4)
    if t < 2.4: return 2.6
    if t < 2.8: return 2.6 + (0.8 - 2.6) * ease_in_out((t - 2.4) / 0.4)
    return 0.8

SEGS = [
    Seg(3.0, 2.5, 3.0, 1.0, 1.06, 1.16, tag="01  |  CAM MECHANISM", l1="PRECISION", l2="ENGINEERING",
        cap="Heavy-duty cams & gear train", text_in=0.55),
    Seg(5.5, 2.0, 7.0, 0.9, 1.22, 1.06),
    Seg(7.5, 2.5, 9.0, 1.0, 1.04, 1.22, tag="02  |  ROTARY TURRET", l1="HIGH-SPEED", l2="TURRET",
        cap="Continuous rotary transfer", text_out=0.45),
    Seg(10.0, 4.0, 12.0, 0.85, 1.04, 1.14, tag="03  |  PACK FORMING", l1="AUTOMATED", l2="PACKING",
        cap="Fully automatic production line", text_in=0.9),
    Seg(14.0, 2.5, 15.5, 0.9, 1.12, 1.04, tag="04  |  FOLDING UNIT", l1="PERFECT", l2="FOLDING",
        cap="Clean, accurate every time", text_out=0.5),
    Seg(16.5, 3.5, 30.6, ramp=ramp_f, z0=1.05, z1=1.18, tag="05  |  DRIVE SYSTEM", l1="POWERFUL",
        l2="DRIVE SYSTEM", cap="Built for non-stop operation", text_in=0.5),
    Seg(20.0, 2.5, 38.6, 1.0, 1.05, 1.15, tag="06  |  OUTPUT", l1="CONSISTENT", l2="QUALITY",
        cap="Uniform packs, batch after batch"),
    Seg(22.5, 2.5, 41.9, 0.7, 1.04, 1.12, tag="07  |  PLC CONTROL", l1="SMART", l2="CONTROL",
        cap="Touchscreen operation", text_out=0.4),
]

def seg_at(t):
    for s in SEGS:
        if s.start <= t < s.end:
            return s
    return SEGS[0] if t < SEGS[0].start else SEGS[-1]

BEAT0, BEAT = 3.0, 0.5

def beat_pulse(t):
    """Small zoom kick on every downbeat (every 2 beats) during the main section."""
    if t < BEAT0 or t >= 25.0: return 1.0
    ph = ((t - BEAT0) % (2 * BEAT))
    return 1.0 + 0.018 * math.exp(-ph * 9)

def render_clip(seg, t, extra_zoom=1.0, off=(0.0, 0.0)):
    tl = t - seg.start
    sp = seg.speed(tl)
    arr = get_src(seg.src_time(tl) * FPS, span=sp if sp > 1.6 else 0)
    img = Image.fromarray(arr)
    z = max(1.02, seg.zoom(tl) * extra_zoom * beat_pulse(t))
    cw, ch = SW / z, SH / z
    k = SW / W / z
    cx = SW / 2 + (seg.pan[0] + off[0]) * k
    cy = SH / 2 + (seg.pan[1] + off[1]) * k
    cx = min(max(cx, cw / 2), SW - cw / 2)
    cy = min(max(cy, ch / 2), SH - ch / 2)
    return img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))

# ---------------------------------------------------------------- fx
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((XX - W / 2) / (W * 0.62)) ** 2 + ((YY - H / 2) / (H * 0.62)) ** 2)
VIGNETTE = np.clip(1.0 - 0.55 * np.clip(_r - 0.35, 0, None) ** 1.5, 0.25, 1.0)[..., None].astype(np.float32)
_lg = np.exp(-(((XX - W * 0.95) / (W * 0.55)) ** 2 + ((YY - H * 0.15) / (H * 0.45)) ** 2))
LEAK = (np.stack([_lg * 255, _lg * 140, _lg * 40], -1)).astype(np.float32)
BOTTOM_GRAD = np.clip((YY - 820) / 650, 0, 1)[..., None] ** 1.3 * 0.78
del _r, _lg
GRAIN = [np.random.default_rng(i).normal(0, 6, (H // 2, W // 2, 1)).astype(np.float32) for i in range(6)]

def radial_blur(img, strength, n=6):
    if strength < 0.02: return img
    acc = np.zeros((H, W, 3), np.float32)
    for i in range(n):
        z = 1 + 0.16 * strength * i / (n - 1)
        cw, ch = W / z, H / z
        acc += np.asarray(img.resize((W, H), Image.BILINEAR,
                                     box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))

def hblur(arr, L):
    L = int(L)
    if L < 3: return arr
    pad = np.pad(arr.astype(np.float32), ((0, 0), (L, L), (0, 0)), mode="edge")
    c = np.cumsum(pad, axis=1)
    out = (c[:, L * 2:L * 2 + W] - c[:, L:L + W]) / L
    return out

def glitch(arr, k, seed):
    if k < 0.02: return arr
    rng = np.random.default_rng(seed)
    out = arr.copy()
    sh = int(40 * k)
    out[..., 0] = np.roll(arr[..., 0], sh, axis=1)
    out[..., 2] = np.roll(arr[..., 2], -sh, axis=1)
    for _ in range(int(14 * k) + 1):
        y = int(rng.integers(0, H - 60)); h = int(rng.integers(8, 140))
        out[y:y + h] = np.roll(out[y:y + h], int(rng.integers(-220, 220) * k), axis=1)
    if k > 0.4:
        for _ in range(3):
            y = int(rng.integers(0, H - 40)); x = int(rng.integers(0, W - 300))
            out[y:y + int(rng.integers(6, 30)), x:x + int(rng.integers(100, 400))] = rng.choice(
                [GOLD, CYAN, WHITE, (0, 0, 0)])
        out[::3] = (out[::3] * 0.8).astype(np.uint8)
    return out

def shake_img(img, amp, seed):
    if amp < 0.5: return img
    rng = np.random.default_rng(seed)
    dx, dy = rng.uniform(-amp, amp, 2)
    z = 1 + 2.4 * amp / W
    cw, ch = W / z, H / z
    return img.resize((W, H), Image.BICUBIC,
                      box=((W - cw) / 2 + dx, (H - ch) / 2 + dy, (W + cw) / 2 + dx, (H + ch) / 2 + dy))

# ---------------------------------------------------------------- text
_char_cache = {}

def char_img(ch, fnt, color):
    key = (ch, id(fnt), color)
    if key not in _char_cache:
        l, t, r, b = fnt.getbbox(ch)
        im = Image.new("RGBA", (max(1, r + 4), max(1, b + 4)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=fnt, fill=color + (255,))
        _char_cache[key] = np.asarray(im).astype(np.float32)
    return _char_cache[key]

def text_width(text, fnt, spacing=0):
    return sum(fnt.getlength(c) + spacing for c in text) - spacing

def fit_font(maker, size, text, maxw, spacing=0):
    f = maker(size)
    while text_width(text, f, spacing) > maxw and size > 20:
        size -= 6; f = maker(size)
    return f

def anim_text(layer, text, fnt, x, y, t, t0, color=WHITE, align="left", spacing=0, stagger=0.035,
              dur=0.45, rise=90, t_out=None, mode="rise"):
    """Per-letter animated text drawn onto an RGBA PIL layer."""
    if t < t0: return
    tw = text_width(text, fnt, spacing)
    cx = x - tw / 2 if align == "center" else x
    n = max(1, len(text))
    for i, c in enumerate(text):
        adv = fnt.getlength(c) + spacing
        if c == " ":
            cx += adv; continue
        p = clamp((t - t0 - i * stagger) / dur)
        if p <= 0:
            cx += adv; continue
        e = ease_out_back(p) if mode == "rise" else ease_out_cubic(p)
        dy = (1 - e) * rise
        a = clamp(p * 1.8)
        if t_out is not None:
            q = clamp((t - t_out - (n - i) * 0.015) / 0.3)
            dy -= ease_in_cubic(q) * rise * 0.8
            a *= 1 - q
        if a <= 0.01:
            cx += adv; continue
        ci = char_img(c, fnt, color)
        ci2 = ci.copy(); ci2[..., 3] *= a
        layer.alpha_composite(Image.fromarray(ci2.astype(np.uint8)), (int(cx), int(y + dy)))
        cx += adv

def sweep(layer, t, t0, dur=0.6, width=160):
    """Diagonal light sweep across the opaque pixels of an RGBA layer."""
    p = (t - t0) / dur
    if p < 0 or p > 1: return layer
    bb = layer.getbbox()
    if not bb: return layer
    x0, y0, x1, y1 = bb
    reg = np.asarray(layer.crop(bb)).astype(np.float32)
    h, w = reg.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    pos = -width * 2 + p * (w + h * 0.5 + width * 4)
    band = np.exp(-(((xx + yy * 0.5) - pos) / width) ** 2)[..., None]
    reg[..., :3] = np.clip(reg[..., :3] + band * 255 * 0.9, 0, 255)
    layer.paste(Image.fromarray(reg.astype(np.uint8)), (x0, y0))
    return layer

def shadowed(base, layer, glow=None, shadow=0.75, radius=10):
    """Composite text layer with soft drop shadow / optional colored glow."""
    bb = layer.getbbox()
    if not bb: return base
    pad = radius * 3
    x0, y0 = max(0, bb[0] - pad), max(0, bb[1] - pad)
    x1, y1 = min(W, bb[2] + pad), min(H, bb[3] + pad)
    reg = layer.crop((x0, y0, x1, y1))
    a = reg.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    keep_alpha = base.mode == "RGBA"
    base = base.convert("RGBA")
    sh = Image.new("RGBA", reg.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * shadow)))
    base.alpha_composite(sh, (x0 + 4, y0 + 8))
    if glow:
        g = Image.new("RGBA", reg.size, glow + (0,))
        g.putalpha(a.point(lambda v: int(min(255, v * 0.9))))
        base.alpha_composite(g, (x0, y0))
    base.alpha_composite(layer)
    return base if keep_alpha else base.convert("RGB")

# ---------------------------------------------------------------- particles (embers)
_prng = np.random.default_rng(7)
EMBERS = [dict(x=_prng.uniform(0, W), y=_prng.uniform(0, H), vy=_prng.uniform(40, 160),
               vx=_prng.uniform(-25, 25), r=_prng.uniform(1.5, 5), ph=_prng.uniform(0, 6.28))
          for _ in range(90)]

def draw_embers(img, t, alpha=1.0):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    for e in EMBERS:
        y = (e["y"] - e["vy"] * t) % H
        x = (e["x"] + e["vx"] * t + 20 * math.sin(t * 1.3 + e["ph"])) % W
        fl = 0.55 + 0.45 * math.sin(t * 5 + e["ph"])
        c = tuple(int(v * fl * alpha) for v in GOLD)
        r = e["r"]
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    glow = layer.filter(ImageFilter.GaussianBlur(5))
    return ImageChops.add(ImageChops.add(img, layer), glow)

def dark_bg(t, src_t):
    small = Image.fromarray(get_src(src_t * FPS)).resize((180, 320), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(4))
    z = 1.05 + 0.03 * t
    cw, ch = 180 / z, 320 / z
    bg = small.resize((W, H), Image.BICUBIC, box=((180 - cw) / 2, (320 - ch) / 2, (180 + cw) / 2, (320 + ch) / 2))
    arr = np.asarray(bg, np.float32) * 0.22 * VIGNETTE
    arr[..., 2] *= 1.1
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------- shatter
class Shatter:
    def __init__(self, img, impact, seed, cols=8, rows=14, fine_r=380):
        rng = np.random.default_rng(seed)
        self.impact = np.array(impact, np.float32)
        xs = np.linspace(0, W, cols + 1); ys = np.linspace(0, H, rows + 1)
        P = np.zeros((rows + 1, cols + 1, 2), np.float32)
        for j in range(rows + 1):
            for i in range(cols + 1):
                jx = 0 if i in (0, cols) else rng.uniform(-0.38, 0.38) * W / cols
                jy = 0 if j in (0, rows) else rng.uniform(-0.38, 0.38) * H / rows
                P[j, i] = (xs[i] + jx, ys[j] + jy)
        tris = []
        for j in range(rows):
            for i in range(cols):
                a, b, c, d = P[j, i], P[j, i + 1], P[j + 1, i + 1], P[j + 1, i]
                pair = [(a, b, c), (a, c, d)] if rng.random() < 0.5 else [(a, b, d), (b, c, d)]
                for tri in pair:
                    cen = np.mean(tri, 0)
                    if np.linalg.norm(cen - self.impact) < fine_r:  # finer shards near impact
                        m = [(tri[k] + tri[(k + 1) % 3]) / 2 for k in range(3)]
                        tris += [(tri[0], m[0], m[2]), (m[0], tri[1], m[1]), (m[2], m[1], tri[2]), (m[0], m[1], m[2])]
                    else:
                        tris.append(tri)
        src = img.convert("RGBA")
        self.pieces = []
        for tri in tris:
            pts = np.array(tri)
            x0, y0 = np.floor(pts.min(0)).astype(int) - 1
            x1, y1 = np.ceil(pts.max(0)).astype(int) + 1
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
            if x1 - x0 < 3 or y1 - y0 < 3: continue
            crop = src.crop((x0, y0, x1, y1))
            mask = Image.new("L", crop.size, 0)
            rel = [(float(px - x0), float(py - y0)) for px, py in pts]
            ImageDraw.Draw(mask).polygon(rel, fill=255)
            crop.putalpha(mask)
            ImageDraw.Draw(crop).line(rel + [rel[0]], fill=(255, 225, 160, 110), width=1)
            c = np.array([(x0 + x1) / 2, (y0 + y1) / 2], np.float32)
            v = c - self.impact
            dist = float(np.linalg.norm(v)) + 1e-3
            dirv = v / dist
            spd = rng.uniform(500, 1300) * (1 + 420 / (dist + 160))
            vel = dirv * spd + np.array([rng.uniform(-120, 120), rng.uniform(-420, 60)])
            self.pieces.append(dict(img=crop, c=c, v=vel, w=rng.uniform(-420, 420),
                                    vz=rng.uniform(0.2, 1.6) * (1 + 200 / (dist + 200)),
                                    delay=dist / 5000.0, tri=rel, x0=x0, y0=y0))
        self.pieces.sort(key=lambda p: p["vz"])
        self.sparks = []
        for _ in range(140):
            ang = rng.uniform(0, 2 * math.pi); sp = rng.uniform(700, 2600)
            self.sparks.append((math.cos(ang) * sp, math.sin(ang) * sp - 300, rng.uniform(0.25, 0.8)))
        self.crack = img.copy()
        dd = ImageDraw.Draw(self.crack)
        for p in self.pieces:
            dd.line([(x + p["x0"], y + p["y0"]) for x, y in p["tri"]] + [(p["tri"][0][0] + p["x0"], p["tri"][0][1] + p["y0"])],
                    fill=(255, 240, 210), width=2)

    def render(self, base, tau, slow=0.75):
        """Composite shards flying over `base` at time tau since impact."""
        if tau < 0.06:
            return Image.blend(base, self.crack, 1.0)
        out = base.convert("RGBA")
        tt0 = (tau - 0.06) * slow
        for p in self.pieces:
            tt = max(0.0, tt0 - p["delay"])
            pos = p["c"] + p["v"] * tt + np.array([0, 0.5 * 1800 * tt * tt])
            s = 1 + p["vz"] * tt
            a = clamp(1 - (tt - 0.35) / 0.4)
            if a <= 0: continue
            im = p["img"]
            if tt > 0:
                im = im.rotate(p["w"] * tt, resample=Image.BILINEAR, expand=True)
                if abs(s - 1) > 0.02:
                    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
            x, y = int(pos[0] - im.width / 2), int(pos[1] - im.height / 2)
            if x > W or y > H or x + im.width < 0 or y + im.height < 0: continue
            if a < 1:
                al = im.getchannel("A").point(lambda v, a=a: int(v * a))
                im = im.copy(); im.putalpha(al)
            if x >= 0 and y >= 0:
                out.alpha_composite(im, (x, y))
            else:
                out.paste(im, (x, y), im)
        out = out.convert("RGB")
        # sparks + shockwave (additive)
        fx = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(fx)
        tt = tau * slow
        ix, iy = self.impact
        for vx, vy, life in self.sparks:
            if tt > life: continue
            k = 1 - tt / life
            x = ix + vx * tt; y = iy + vy * tt + 900 * tt * tt
            d.line((x, y, x - vx * 0.025, y - vy * 0.025 - 30 * tt), fill=(int(255 * k), int(210 * k), int(120 * k)), width=4)
        r = tau * 2600
        if r < 2400:
            k = clamp(1 - tau / 0.9)
            d.ellipse((ix - r, iy - r, ix + r, iy + r), outline=(int(255 * k), int(200 * k), int(130 * k)), width=int(6 + 22 * k))
        fx = ImageChops.add(fx, fx.filter(ImageFilter.GaussianBlur(9)))
        return ImageChops.add(out, fx)

# ---------------------------------------------------------------- intro / outro
def intro(t, fx=True):
    img = dark_bg(t, 26.0 + t * 0.8)
    img = draw_embers(img, t, alpha=clamp(t / 0.8))
    if TEXT_ON:
        img = shadowed(img, intro_layer(t), radius=14)
    if fx:
        k = clamp((t - 2.2) / 0.8) ** 2
        z = 1 + 0.07 * k
        img = img.resize((W, H), Image.BICUBIC, box=(W * (1 - 1 / z) / 2, H * (1 - 1 / z) / 2,
                                                       W * (1 + 1 / z) / 2, H * (1 + 1 / z) / 2))
        if k > 0.05:
            img = Image.fromarray(glitch(np.asarray(img), 0.25 * k, int(t * FPS)))
            img = shake_img(img, 8 * k, int(t * FPS))
    return img

def intro_layer(t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f1 = fit_font(BEBAS, 250, "CIGARETTE", W - 120)
    f2 = fit_font(BEBAS, 150, "MAKING MACHINE", W - 120)
    anim_text(layer, "CIGARETTE", f1, W / 2, 640, t, 0.45, WHITE, "center", spacing=6, rise=140)
    anim_text(layer, "MAKING MACHINE", f2, W / 2, 900, t, 0.85, GOLD, "center", spacing=4, rise=110)
    d = ImageDraw.Draw(layer)
    p = ease_out_cubic(clamp((t - 0.3) / 0.6))
    if p > 0:
        hw = 420 * p
        d.rectangle((W / 2 - hw, 875, W / 2 + hw, 880), fill=GOLD + (255,))
    anim_text(layer, "PRECISION  •  SPEED  •  POWER", MONT(36, "SemiBold"), W / 2, 1090, t, 1.35, WHITE,
              "center", spacing=5, stagger=0.012, mode="fade", rise=30)
    sweep(layer, t, 1.8, 0.7)
    return layer

def outro_layer(t):
    lt = t - 25.0
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f1 = fit_font(BEBAS, 230, "CIGARETTE", W - 120)
    f2 = fit_font(BEBAS, 140, "MAKING MACHINE", W - 120)
    anim_text(layer, "CIGARETTE", f1, W / 2, 620, lt, 0.55, WHITE, "center", spacing=6, rise=140)
    anim_text(layer, "MAKING MACHINE", f2, W / 2, 870, lt, 0.85, GOLD, "center", spacing=4, rise=110)
    d = ImageDraw.Draw(layer)
    p = ease_out_cubic(clamp((lt - 0.7) / 0.6))
    if p > 0:
        hw = 400 * p
        d.rectangle((W / 2 - hw, 848, W / 2 + hw, 853), fill=GOLD + (255,))
    anim_text(layer, "PRECISION ENGINEERED FOR PERFORMANCE", fit_font(lambda s: MONT(s, "SemiBold"), 34,
              "PRECISION ENGINEERED FOR PERFORMANCE", W - 140, 3), W / 2, 1060, lt, 1.4, WHITE, "center",
              spacing=3, stagger=0.01, mode="fade", rise=30)
    q = ease_out_back(clamp((lt - 2.2) / 0.5))
    if q > 0:
        bw, bh = 520 * q, 96
        cy = 1290
        d.rounded_rectangle((W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2), radius=48,
                            outline=GOLD + (255,), width=4)
    anim_text(layer, "FOLLOW FOR MORE", MONT(38, "Bold"), W / 2, 1265, lt, 2.45, GOLD, "center",
              spacing=6, stagger=0.02, mode="fade", rise=20)
    sweep(layer, lt, 1.9, 0.7)
    return layer

# ---------------------------------------------------------------- HUD + titles
def hud(img, t, seg):
    img = img.convert("RGBA"); img.alpha_composite(hud_layer(t, seg))
    return img.convert("RGB")

def hud_layer(t, seg, dynamic=True):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    m, L, wd = 48, 70, 5
    col = (255, 255, 255, 170)
    for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m - 230, 1, -1), (W - m, H - m - 230, -1, -1)]:
        d.rectangle((min(x, x + sx * L), min(y, y + sy * wd), max(x, x + sx * L), max(y, y + sy * wd)), fill=col)
        d.rectangle((min(x, x + sx * wd), min(y, y + sy * L), max(x, x + sx * wd), max(y, y + sy * L)), fill=col)
    if not dynamic or int(t * 2) % 2 == 0:
        d.ellipse((m + 22, m + 34, m + 40, m + 52), fill=(255, 50, 50, 230))
    f = MONT(26, "SemiBold")
    d.text((m + 54, m + 28), "AUTO MODE", font=f, fill=(255, 255, 255, 220))
    if not dynamic:
        return layer
    idx = SEGS.index(seg) + 1
    s = f"{idx:02d} / {len(SEGS):02d}"
    d.text((W - m - 22 - d.textlength(s, font=f), m + 28), s, font=f, fill=GOLD + (230,))
    # scanning line
    sy = (t * 520) % (H + 400) - 200
    d.rectangle((0, sy, W, sy + 2), fill=CYAN + (55,))
    # progress bar
    d.rectangle((0, H - 10, int(W * t / DUR), H), fill=GOLD + (255,))
    return layer

def titles(img, t, seg):
    if not seg.l1: return img
    lt = t - seg.start
    t_in, t_out = seg.text_in, seg.dur - seg.text_out
    if lt < t_in or lt > t_out + 0.6: return img
    # darken bottom for legibility
    k = clamp((lt - t_in) / 0.3) * (1 - clamp((lt - t_out) / 0.4))
    if k > 0:
        arr = np.asarray(img, np.float32) * (1 - BOTTOM_GRAD * k)
        img = Image.fromarray(arr.astype(np.uint8))
    return shadowed(img, title_layer(seg, lt), radius=10)

def title_layer(seg, lt):
    t_in, t_out = seg.text_in, seg.dur - seg.text_out
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = 80
    anim_text(layer, seg.tag, MONT(32, "Bold"), x, 1085, lt, t_in, GOLD, spacing=4, stagger=0.012,
              mode="fade", rise=25, t_out=t_out)
    fl = fit_font(BEBAS, 175, max(seg.l1, seg.l2, key=len), W - 2 * x, 2)
    anim_text(layer, seg.l1, fl, x, 1130, lt, t_in + 0.08, WHITE, spacing=2, t_out=t_out)
    anim_text(layer, seg.l2, fl, x, 1290, lt, t_in + 0.2, GOLD, spacing=2, t_out=t_out)
    d = ImageDraw.Draw(layer)
    p = ease_out_cubic(clamp((lt - t_in - 0.3) / 0.45)) * (1 - ease_in_cubic(clamp((lt - t_out) / 0.3)))
    if p > 0:
        d.rectangle((x, 1475, x + 260 * p, 1483), fill=GOLD + (255,))
    anim_text(layer, seg.cap, MONT(38, "Medium"), x, 1505, lt, t_in + 0.45, (235, 235, 235), stagger=0.01,
              mode="fade", rise=20, t_out=t_out)
    sweep(layer, lt, t_in + 0.7, 0.55, 120)
    return layer

def callout(img, t, t0, t1, pt, label):
    lt = t - t0
    if lt < 0 or t > t1: return img
    out = 1 - clamp((t - (t1 - 0.25)) / 0.25)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    px, py = pt
    r = 34 * ease_out_back(clamp(lt / 0.3))
    a = int(255 * out)
    d.ellipse((px - r, py - r, px + r, py + r), outline=GOLD + (a,), width=5)
    d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=GOLD + (a,))
    pl = ease_out_cubic(clamp((lt - 0.15) / 0.3))
    ex, ey = px + 120 * pl, py - 120 * pl
    d.line((px + 24, py - 24, ex, ey), fill=GOLD + (a,), width=4)
    hl = ease_out_cubic(clamp((lt - 0.35) / 0.3))
    f = MONT(40, "Bold")
    tw = d.textlength(label, font=f)
    d.line((ex, ey, ex + (tw + 40) * hl, ey), fill=GOLD + (a,), width=4)
    if hl > 0.2:
        d.rectangle((ex, ey - 64, ex + (tw + 40) * hl, ey - 6), fill=(0, 0, 0, int(150 * out)))
    anim_text(layer, label, f, ex + 20, ey - 60, lt, 0.45, WHITE, stagger=0.02, mode="fade", rise=15)
    if out < 1:
        al = layer.getchannel("A").point(lambda v: int(v * out)); layer.putalpha(al)
    img = img.convert("RGBA"); img.alpha_composite(layer)
    return img.convert("RGB")

# ---------------------------------------------------------------- transitions / composition
_shatter = {}

def get_shatter(name):
    if name not in _shatter:
        if name == "intro":
            _shatter[name] = Shatter(intro(2.999, fx=False), (W / 2, 900), 1)
        elif name == "turret":
            s = SEGS[2]; t = s.end - 1e-3
            img = render_clip(s, t)
            _shatter[name] = Shatter(img, (W / 2, H * 0.45), 2)
        elif name == "panel":
            s = SEGS[7]; t = s.end - 1e-3
            _shatter[name] = Shatter(hud(render_clip(s, t), t, s) if HUD_ON else render_clip(s, t), (W * 0.55, H * 0.5), 3)
    return _shatter[name]

def outro_bg(t):
    return draw_embers(dark_bg(t - 25, 13.0 + (t - 25) * 0.6), t)

def compose(t):
    flash = 0.0; shake = 0.0; leak = 0.0
    # ---- intro + explode into first clip
    if t < 3.0:
        img = intro(t)
        if t < 0.4:
            img = Image.fromarray((np.asarray(img, np.float32) * (t / 0.4)).astype(np.uint8))
        flash = clamp((t - 2.85) / 0.15) * 0.8
        return post(img, t, flash, 0, 0)
    if t >= 25.0:
        lt = t - 25.0
        base = outro_bg(t)
        if lt < 1.3:
            base = get_shatter("panel").render(base, lt)
            flash = 1.0 * math.exp(-lt / 0.08)
            shake = 26 * math.exp(-lt / 0.25)
        if TEXT_ON:
            base = shadowed(base, outro_layer(t), radius=14)
        if t > 29.3:
            base = Image.fromarray((np.asarray(base, np.float32) * clamp((30 - t) / 0.7)).astype(np.uint8))
        return post(base, t, flash, shake, 0, glow_only=True)

    seg = seg_at(t)
    img = None
    # 3.0: intro shatter over clip A
    if 3.0 <= t < 4.2:
        lt = t - 3.0
        base = render_clip(SEGS[0], t, extra_zoom=1 + 0.35 * (1 - ease_out_cubic(clamp(lt / 0.8))))
        img = get_shatter("intro").render(base, lt)
        flash = 1.0 * math.exp(-lt / 0.09); shake = 28 * math.exp(-lt / 0.25)
    # 5.5: zoom transition A -> B
    elif 5.25 <= t < 5.75:
        T = 5.5
        if t < T:
            p = (t - (T - 0.25)) / 0.25
            img = radial_blur(render_clip(SEGS[0], t, 1 + 0.5 * p * p), p)
        else:
            q = (t - T) / 0.25
            img = radial_blur(render_clip(SEGS[1], t, 1 + 0.5 * (1 - q) ** 2), 1 - q)
        flash = 0.35 * clamp(1 - abs(t - T) / 0.1)
    # 7.5: glitch cut B -> C
    elif 7.35 <= t < 7.65:
        T = 7.5
        img = render_clip(SEGS[1] if t < T else SEGS[2], t)
        k = clamp(1 - abs(t - T) / 0.15)
        img = Image.fromarray(glitch(np.asarray(img), k, int(t * FPS)))
    # 9.5-10: push-in + freeze, then 10.0 turret shatter over D
    elif 9.6 <= t < 10.0:
        p = (t - 9.6) / 0.4
        img = render_clip(SEGS[2], t)
        img = Image.fromarray(glitch(np.asarray(img), 0.25 * p * p, int(t * FPS)))
        shake = 6 * p
    elif 10.0 <= t < 11.3:
        lt = t - 10.0
        base = render_clip(SEGS[3], t, extra_zoom=1 + 0.3 * (1 - ease_out_cubic(clamp(lt / 0.9))))
        img = get_shatter("turret").render(base, lt)
        flash = 1.0 * math.exp(-lt / 0.09); shake = 30 * math.exp(-lt / 0.25)
    # 14.0: whip pan D -> E
    elif 13.8 <= t < 14.2:
        p = ease_in_out((t - 13.8) / 0.4)
        s = p * W
        a = render_clip(SEGS[3], t); b = render_clip(SEGS[4], t)
        cv = Image.new("RGB", (W, H))
        cv.paste(a, (int(-s), 0)); cv.paste(b, (int(W - s), 0))
        vel = 6 * p * (1 - p)  # derivative shape of smoothstep
        img = Image.fromarray(np.clip(hblur(np.asarray(cv), 260 * vel), 0, 255).astype(np.uint8))
    # 16.5: exploded-view slabs E -> F
    elif 16.2 <= t < 17.1:
        img = slabs(t, 16.2)
    # 20.0: glitch + light leak F -> G
    elif 19.8 <= t < 20.2:
        T = 20.0
        img = render_clip(SEGS[5] if t < T else SEGS[6], t)
        k = clamp(1 - abs(t - T) / 0.2)
        img = Image.fromarray(glitch(np.asarray(img), 0.8 * k, int(t * FPS)))
        leak = k; flash = 0.25 * k
    # 22.5: zoom transition G -> H
    elif 22.25 <= t < 22.75:
        T = 22.5
        if t < T:
            p = (t - (T - 0.25)) / 0.25
            img = radial_blur(render_clip(SEGS[6], t, 1 + 0.5 * p * p), p)
        else:
            q = (t - T) / 0.25
            img = radial_blur(render_clip(SEGS[7], t, 1 + 0.5 * (1 - q) ** 2), 1 - q)
        flash = 0.35 * clamp(1 - abs(t - T) / 0.1)
    # 24.6-25: build before final explode
    elif 24.6 <= t < 25.0:
        p = (t - 24.6) / 0.4
        img = Image.fromarray(glitch(np.asarray(render_clip(SEGS[7], t, 1 + 0.06 * p * p)), 0.3 * p * p, int(t * FPS)))
        shake = 6 * p
    else:
        img = render_clip(seg, t)

    # light leaks on a few downbeats
    if 16.5 <= t < 17.6:
        leak = max(leak, 0.6 * math.sin(math.pi * clamp((t - 16.5) / 1.1)))
    if TEXT_ON:
        img = titles(img, t, seg)
    if TEXT_ON and SEGS[1].start + 0.2 <= t < SEGS[1].end - 0.1:
        img = callout(img, t, SEGS[1].start + 0.2, SEGS[1].end - 0.1, (W * 0.5, H * 0.56), "GEAR DRIVE")
    if HUD_ON:
        img = hud(img, t, seg)
    return post(img, t, flash, shake, leak)

def slabs(t, t0):
    """Exploded-view: the outgoing frame splits into horizontal slabs that fly apart."""
    A, B = SEGS[4], SEGS[5]
    lt = t - t0  # 0..0.9 ; cut point at 0.3
    a_img = render_clip(A, min(t, A.end - 1e-3))
    if lt < 0.3:  # scan lines cut the frame
        img = a_img.convert("RGBA")
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        n = 6
        for i in range(1, n):
            y = H * i / n
            pl = ease_out_cubic(clamp((lt - i * 0.03) / 0.2))
            x0 = 0 if i % 2 else W * (1 - pl)
            d.rectangle((x0, y - 2, x0 + W * pl, y + 2), fill=CYAN + (230,))
        glow = layer.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(glow); img.alpha_composite(layer)
        return img.convert("RGB")
    p_all = lt - 0.3
    base = render_clip(B, t, extra_zoom=1 + 0.25 * (1 - ease_out_cubic(clamp(p_all / 0.6))))
    base = Image.fromarray((np.asarray(base, np.float32) * (0.55 + 0.45 * clamp(p_all / 0.5))).astype(np.uint8))
    out = base.convert("RGBA")
    n = 6
    for i in range(n):
        y0, y1 = int(H * i / n), int(H * (i + 1) / n)
        p = ease_in_cubic(clamp((p_all - abs(i - 2.5) * 0.03) / 0.5))
        direction = -1 if i % 2 == 0 else 1
        dx = direction * p * W * 1.15
        sl = a_img.crop((0, y0, W, y1)).convert("RGBA")
        s = 1 + 0.12 * p
        sl = sl.resize((int(W * s), int((y1 - y0) * s)), Image.BILINEAR)
        dd = ImageDraw.Draw(sl)
        dd.rectangle((0, 0, sl.width - 1, sl.height - 1), outline=CYAN + (220,), width=4)
        dd.text((24, 18), f"MODULE {i + 1:02d}", font=MONT(28, "Bold"), fill=CYAN + (255,))
        cy = (y0 + y1) / 2 + (i - 2.5) * 40 * p
        out.paste(sl, (int((W - sl.width) / 2 + dx), int(cy - sl.height / 2)), sl)
    return out.convert("RGB")

def post(img, t, flash=0.0, shake=0.0, leak=0.0, glow_only=False):
    if shake > 0.5:
        img = shake_img(img, shake, int(t * FPS) + 999)
    arr = np.asarray(img, np.float32)
    if not glow_only:
        arr = arr * VIGNETTE
    else:
        arr = arr * (0.6 + 0.4 * VIGNETTE)
    if leak > 0.01:
        arr = 255 - (255 - arr) * (1 - LEAK / 255 * leak)  # screen blend
    if flash > 0.01:
        arr = arr + (255 - arr) * flash
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    arr = arr + np.repeat(np.repeat(g, 2, 0), 2, 1)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# ---------------------------------------------------------------- main
def render_range(args):
    i0, i1, path = args
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "16", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        enc.stdin.write(compose(i / FPS).tobytes())
        if i % 30 == 0:
            print(f"frame {i}", flush=True)
    enc.stdin.close(); enc.wait()
    return path

if __name__ == "__main__":
    load_source()
    if "--frames" in sys.argv:
        ts = [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]
        for tt in ts:
            compose(tt).save(f"still_{tt:05.2f}.jpg", quality=88)
        sys.exit()
    out = sys.argv[1] if len(sys.argv) > 1 else "video_only.mp4"
    import multiprocessing as mp
    N = int(DUR * FPS)
    workers = int(os.environ.get("WORKERS", "4"))
    bounds = np.linspace(0, N, workers + 1).astype(int)
    jobs = [(bounds[k], bounds[k + 1], f"part{k}.mp4") for k in range(workers)]
    with mp.get_context("fork").Pool(workers) as pool:
        parts = pool.map(render_range, jobs)
    with open("parts.txt", "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt", "-c", "copy", out], check=True)
    print("done", out)
