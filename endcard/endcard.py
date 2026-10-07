"""Animated reel end card for Secret Closet by AshKash (1080x1920 @30fps, 4.5 s).

Logo parts animate in turn: emblem radial reveal -> double rules draw out -> "SECRET CLOSET"
wipe -> "By ASHKASH" slide -> shimmer -> website / address.

Usage: python endcard.py LOGO.png out.mp4 [--frames 0.5,1.5,...]
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 4.5
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
PINK = (230, 30, 115)
INK = (70, 44, 56)
WEBSITE = "www.ash-kash.com"
ADDRESS = "Emirates Hills, Dubai"

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3
def eob(p, s=1.4): p = clamp(p) - 1; return p * p * ((s + 1) * p + s) + 1

@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var: f.set_variation_by_name(var)
    return f

# ------------------------------------------------------------------ logo parts
LOGO_W, LOGO_Y = 940, 560
def load_logo(path):
    im = Image.open(path).convert("RGBA")
    k = LOGO_W / im.width
    im = im.resize((LOGO_W, round(im.height * k)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    a[..., :3] = PINK                          # clean, uniform brand pink
    sc = lambda y: round(y * k)
    parts = {  # source-row bands measured from the 1600x880 logo
        "emblem": (0, sc(490)), "rules_top": (sc(500), sc(520)), "title": (sc(560), sc(705)),
        "by": (sc(765), sc(866)), "rules_bot": (sc(866), a.shape[0]),
    }
    return {k_: (a[y0:y1].copy(), y0) for k_, (y0, y1) in parts.items()}, k

def paste(cv, arr, x, y, alpha=1.0):
    if alpha <= 0.003: return
    if alpha < 0.999:
        arr = arr.copy(); arr[..., 3] *= alpha
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    cv.alpha_composite(im, (int(round(x)), int(round(y))))

# ------------------------------------------------------------------ background
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_v = YY / H
BG = np.stack([255 - 4 * _v, 250 - 14 * _v, 246 - 6 * _v], -1)
_g = np.exp(-(((XX - W / 2) / 520) ** 2 + ((YY - 720) / 420) ** 2))[..., None]
BG = BG * (1 - 0.10 * _g) + np.array([252, 214, 228]) * 0.10 * _g
_r = np.sqrt(((XX - W / 2) / (W * 0.8)) ** 2 + ((YY - H / 2) / (H * 0.75)) ** 2)
BG *= np.clip(1 - 0.10 * np.clip(_r - 0.55, 0, None), 0.9, 1)[..., None]
BG_IMG = Image.fromarray(np.clip(BG, 0, 255).astype(np.uint8)).convert("RGBA")
del _v, _g, _r

_rng = np.random.default_rng(4)
SPARKS = [(_rng.uniform(80, W - 80), _rng.uniform(250, 1500), _rng.uniform(1.2, 3.2), _rng.uniform(0, 6.3),
           _rng.uniform(6, 22)) for _ in range(46)]

def sparkles(cv, t, a):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x, y, r, ph, v in SPARKS:
        tw = 0.5 + 0.5 * math.sin(t * 3.2 + ph)
        yy = y - v * t
        al = int(255 * a * tw * 0.55)
        if al < 6: continue
        col = (236, 120, 170) if ph > 3 else (214, 178, 108)
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=col + (al,))
        if r > 2.6 and tw > 0.8:   # tiny star flare
            d.line((x - 3 * r, yy, x + 3 * r, yy), fill=col + (al // 2,), width=1)
            d.line((x, yy - 3 * r, x, yy + 3 * r), fill=col + (al // 2,), width=1)
    cv.alpha_composite(layer)

# ------------------------------------------------------------------ icons (drawn 4x, downsampled)
def icon(kind, size=40, color=PINK):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lw = int(S * 0.07); c = color + (255,)
    if kind == "globe":
        m = lw
        d.ellipse((m, m, S - m, S - m), outline=c, width=lw)
        d.ellipse((S * 0.3, m, S * 0.7, S - m), outline=c, width=lw)
        d.line((m, S / 2, S - m, S / 2), fill=c, width=lw)
        d.arc((m, S * 0.05, S - m, S * 0.55), 20, 160, fill=c, width=lw)
        d.arc((m, S * 0.45, S - m, S * 0.95), 200, 340, fill=c, width=lw)
    else:  # map pin
        cx, r = S / 2, S * 0.3
        d.ellipse((cx - r, S * 0.06, cx + r, S * 0.06 + 2 * r), fill=c)
        d.polygon([(cx - r * 0.85, S * 0.06 + r * 1.45), (cx + r * 0.85, S * 0.06 + r * 1.45), (cx, S * 0.97)], fill=c)
        rr = r * 0.42
        d.ellipse((cx - rr, S * 0.06 + r - rr, cx + rr, S * 0.06 + r + rr), fill=(0, 0, 0, 0))
    return np.asarray(im.resize((size, size), Image.LANCZOS)).astype(np.float32)

@functools.lru_cache(maxsize=None)
def text_arr(s, fname, size, var, color, spacing=0):
    f = font(fname, size, var)
    w = int(sum(f.getlength(ch) + spacing for ch in s)) + 10
    l, t_, r, b = f.getbbox(s)
    im = Image.new("RGBA", (w, b + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    for ch in s:
        d.text((x, 0), ch, font=f, fill=color + (255,)); x += f.getlength(ch) + spacing
    return np.asarray(im).astype(np.float32)

# ------------------------------------------------------------------ frame
class Card:
    def __init__(self, logo_path):
        self.parts, self.k = load_logo(logo_path)
        self.x0 = (W - LOGO_W) / 2
        e, ey = self.parts["emblem"]
        h, w = e.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.e_dist = np.sqrt((xx - w * 0.497) ** 2 + ((yy - h * 0.52) * 1.15) ** 2)
        self.e_max = float(self.e_dist.max())
        self.globe, self.pin = icon("globe", 40), icon("pin", 40)

    def frame(self, t):
        cv = BG_IMG.copy()
        sparkles(cv, t, eo(t / 1.0))
        P = self.parts
        # emblem: radial reveal from its centre + gentle scale-up
        e, ey = P["emblem"]
        p = eo((t - 0.15) / 1.1)
        if p > 0:
            R = p * (self.e_max + 60)
            m = np.clip((R - self.e_dist) / 60, 0, 1)
            arr = e.copy(); arr[..., 3] *= m
            s = 0.92 + 0.08 * eob((t - 0.15) / 1.0)
            im = Image.fromarray(arr.astype(np.uint8))
            if abs(s - 1) > 1e-3:
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
            cx, cy = self.x0 + e.shape[1] / 2, LOGO_Y + ey + e.shape[0] / 2
            cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
        # double rules draw outward from the centre
        for key, t0 in (("rules_top", 0.9), ("rules_bot", 2.0)):
            arr, y = P[key]
            q = eo((t - t0) / 0.6)
            if q > 0:
                w = arr.shape[1]; half = int(w / 2 * q)
                paste(cv, arr[:, w // 2 - half: w // 2 + half], self.x0 + w / 2 - half, LOGO_Y + y)
        # "SECRET CLOSET": soft left-to-right wipe with a small rise
        arr, y = P["title"]
        q = (t - 1.1) / 0.85
        if q > 0:
            w = arr.shape[1]
            xs = np.arange(w, dtype=np.float32)
            edge = q * (w + 120)
            m = np.clip((edge - xs) / 120, 0, 1)[None, :]
            a2 = arr.copy(); a2[..., 3] *= m
            paste(cv, a2, self.x0, LOGO_Y + y + 18 * (1 - eo(q)))
        # "By ASHKASH": slide in from the right
        arr, y = P["by"]
        q = eo((t - 1.75) / 0.6)
        if q > 0:
            paste(cv, arr, self.x0 + 50 * (1 - q), LOGO_Y + y, q)
        # shimmer sweep across the whole logo
        q = (t - 2.45) / 0.8
        if 0 < q < 1:
            region = cv.crop((0, LOGO_Y - 20, W, LOGO_Y + 540))
            ra = np.asarray(region).astype(np.float32)
            hh, ww = ra.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww]
            pos = -300 + q * (ww + 600)
            band = np.exp(-(((xx + yy * 0.6) - pos) / 90) ** 2)[..., None]
            pinkness = np.clip((ra[..., 0:1] - ra[..., 1:2]) / 150, 0, 1)   # only on the pink ink
            ra[..., :3] = ra[..., :3] + (255 - ra[..., :3]) * band * pinkness * 0.55
            cv.paste(Image.fromarray(ra.astype(np.uint8)), (0, LOGO_Y - 20))
        # info block
        for i, (t0, kind) in enumerate(((2.45, "tag"), (2.7, "web"), (2.95, "addr"))):
            q = eo((t - t0) / 0.55)
            if q <= 0: continue
            dy = 24 * (1 - q)
            if kind == "tag":
                a = text_arr("SHOP THE COLLECTION", "Montserrat.ttf", 26, "SemiBold", PINK, 9)
                paste(cv, a, (W - a.shape[1]) / 2, 1195 + dy, q)
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); L = 70 * q
                for side in (-1, 1):
                    x1 = W / 2 + side * (a.shape[1] / 2 + 22)
                    d.line((x1, 1213 + dy, x1 + side * L, 1213 + dy), fill=PINK + (int(200 * q),), width=2)
                cv.alpha_composite(lay)
            else:
                s, ic = (WEBSITE, self.globe) if kind == "web" else (ADDRESS, self.pin)
                a = text_arr(s, "Montserrat.ttf", 46, "Medium", INK, 1)
                total = ic.shape[1] + 22 + a.shape[1]
                x = (W - total) / 2
                y = (1275 if kind == "web" else 1355) + dy
                paste(cv, ic, x, y + 8, q)
                paste(cv, a, x + ic.shape[1] + 22, y, q)
        out = np.asarray(cv.convert("RGB"), np.float32)
        out = 255 - (255 - out) * clamp(t / 0.3)          # open from white
        return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    card = Card(sys.argv[1])
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(card.frame(t)).save(f"ec_{t:04.2f}.jpg", quality=90)
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
    for n in range(int(DUR * FPS)):
        enc.stdin.write(card.frame(n / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", sys.argv[2])
