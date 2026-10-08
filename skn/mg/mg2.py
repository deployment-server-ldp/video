"""SKN Theory — Whimsical Glow Peel · motion graphics v3 (49.5 s, 1080x1920 @30fps).

Driven by the updated VO (used unedited, offset +0.8 s). All typography is taken from the spoken
words and lands on them. Real treatment footage, the concealed product shot, the three AI
microscope clips and the official logo are composited in.

Usage: python mg2.py IN_DIR out.mp4 [--frames t1,t2,...]
IN_DIR: 1008.mp4, p2_masked.mp4, p4.mp4, ai_microscope.mp4, ai_cells.mp4, ai_layers.mp4, logo.webp
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
TOTAL = 49.5
VO_OFFSET = 0.8
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "fonts")
IN = sys.argv[1]

# palette: working colours shifted toward the supplied logo (deep brown + peach)
DARK = (43, 29, 25); BROWN = (59, 30, 24); IVORY = (246, 240, 233); PEACH = (226, 168, 143)
CHAMP = (224, 190, 166); TAUPE = (161, 134, 122); BLUSH = (240, 214, 200)

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3
def ei(p): return clamp(p) ** 3
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)
def V(t): return t + VO_OFFSET              # VO-file time -> timeline time

# ------------------------------------------------------------------ type
@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var: f.set_variation_by_name(var)
    return f
SERIF = lambda s, v="Medium": font("Cormorant.ttf", s, v)
ITAL = lambda s, v="Medium Italic": font("CormorantItalic.ttf", s, v)
SANS = lambda s, v="SemiBold": font("Manrope.ttf", s, v)

@functools.lru_cache(maxsize=1024)
def word_img(s, fnt, color, tracking):
    w = int(sum(fnt.getlength(c) + tracking for c in s) - tracking) + 14
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (max(w, 2), asc + desc + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    for c in s:
        d.text((x, 0), c, font=fnt, fill=color + (255,)); x += fnt.getlength(c) + tracking
    return im

def text(L, s, fnt, x, y, t, t0, color, tracking=0, align="left", dur=0.7, t_out=None, out_dur=0.45, track_from=None):
    """Masked vertical reveal / masked exit (shared by every headline)."""
    if t < t0: return
    p = eo((t - t0) / dur)
    trk = tracking if track_from is None else track_from + (tracking - track_from) * eo((t - t0) / (dur * 1.8))
    im = word_img(s, fnt, color, round(trk, 1))
    if t_out is not None and t > t_out:
        p = min(p, 1 - ei((t - t_out) / out_dur))
        if p <= 0: return
    h = im.height; off = int((1 - p) * h * 0.92)
    if off >= h: return
    vis = im.crop((0, 0, im.width, h - off))
    xx = x - im.width / 2 if align == "center" else x - im.width if align == "right" else x
    L.alpha_composite(vis, (int(xx), int(y + off)))

def line(L, x0, y, x1, t, t0, color, dur=0.8, th=2, t_out=None, alpha=230, center=False):
    p = eio((t - t0) / dur)
    if t_out is not None: p *= 1 - eio((t - t_out) / 0.45)
    if p <= 0: return
    d = ImageDraw.Draw(L)
    if center:
        c = (x0 + x1) / 2; hw = (x1 - x0) / 2 * p; d.rectangle((c - hw, y, c + hw, y + th - 1), fill=color + (alpha,))
    else:
        d.rectangle((x0, y, x0 + (x1 - x0) * p, y + th - 1), fill=color + (alpha,))

def header(L, t, t0, label, idx, color, t_out=None):
    text(L, label, SANS(22, "Bold"), 70, 140, t, t0, color, 6, t_out=t_out, track_from=1)
    text(L, idx, SANS(20, "Medium"), 1010, 140, t, t0, color, 2, align="right", t_out=t_out)

# ------------------------------------------------------------------ backgrounds & look
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_rr = np.sqrt(((XX - W / 2) / (W * 0.8)) ** 2 + ((YY - H / 2) / (H * 0.75)) ** 2)
VIG = np.clip(1 - 0.2 * np.clip(_rr - 0.45, 0, None) ** 1.3, 0.78, 1)[..., None].astype(np.float32)
GRAIN = [np.random.default_rng(i).normal(0, 1, (H // 2, W // 2, 1)).astype(np.float32) for i in range(8)]
TOPSH = (np.clip(1 - YY / 900, 0, 1) ** 1.5 * 0.55)[..., None].astype(np.float32)
BOTSH = (np.clip((YY - 1050) / 700, 0, 1) ** 1.3 * 0.62)[..., None].astype(np.float32)

def solid(color, t, light=0.05):
    base = np.empty((H, W, 3), np.float32); base[:] = color
    cx = W * (0.35 + 0.25 * math.sin(t * 0.21)); cy = H * (0.35 + 0.12 * math.cos(t * 0.17))
    g = np.exp(-(((XX - cx) / (W * 0.9)) ** 2 + ((YY - cy) / (H * 0.5)) ** 2))[..., None]
    return base * (1 - light * g) + 255 * light * g

# ------------------------------------------------------------------ media
GRADE = ("colortemperature=temperature=5900:mix=0.5,huesaturation=saturation=-0.45:colors=c+b,"
         "huesaturation=saturation=-0.08,curves=master='0/0.02 0.25/0.24 0.5/0.52 0.8/0.84 1/0.97'")
AI_GRADE = "eq=saturation=0.96:contrast=1.02"
MW, MH = 720, 1280
# id: (file, src_start, speed, out_duration, stabilise, grade)
CLIPS = {
    "prod":     ("p2_masked.mp4", 4.4, 0.5, 3.8, False, GRADE),     # product box — name under tracked blur
    "forehead": ("1008.mp4", 121.8, 1.0, 3.0, True, GRADE),         # doctor applies the peel (forehead)
    "prep":     ("1008.mp4", 72.0, 1.0, 1.7, True, GRADE),          # doctor cleansing, both hands
    "bowl":     ("1008.mp4", 112.5, 1.0, 1.7, True, GRADE),         # brush into the bowl
    "cheek":    ("1008.mp4", 129.0, 1.0, 1.8, True, GRADE),         # application, cheek
    "close1":   ("1008.mp4", 192.5, 1.0, 1.8, True, GRADE),         # close application
    "close2":   ("1008.mp4", 204.5, 1.0, 1.6, True, GRADE),         # application detail
    "mask":     ("p4.mp4", 0.0, 0.85, 3.4, False, GRADE),           # client relaxing in the gem mask
    "micro":    ("ai_microscope.mp4", 0.0, 1.0, 4.9, False, AI_GRADE),
    "cells":    ("ai_cells.mp4", 0.4, 1.0, 6.6, False, AI_GRADE),
    "layers":   ("ai_layers.mp4", 2.5, 1.0, 7.0, False, AI_GRADE),
}
MM = {}

def load_media():
    cache = os.path.join(IN, "_cache3"); os.makedirs(cache, exist_ok=True)
    procs = []
    for cid, (fn, s0, sp, dur, stab, grade) in CLIPS.items():
        out = os.path.join(cache, f"{cid}_{s0:.2f}_{sp:.2f}_{dur:.2f}.rgb")
        if os.path.exists(out): continue
        src = os.path.join(IN, fn); length = (dur + 0.3) * sp
        vf = ""
        if stab:
            trf = out + ".trf"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s0), "-t", str(length), "-i", src, "-vf",
                            f"vidstabdetect=shakiness=5:result={trf}", "-f", "null", "-"], check=True)
            vf = f"vidstabtransform=input={trf}:smoothing=20:zoom=3,"
        vf += f"scale={MW}:{MH}:force_original_aspect_ratio=increase:flags=lanczos,crop={MW}:{MH},unsharp=5:5:0.45,{grade}"
        if sp != 1.0: vf += f",setpts={1 / sp:.4f}*PTS"
        vf += f",fps={FPS}"
        procs.append(subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-ss", str(s0), "-t", str(length), "-i", src,
                                       "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", out]))
        if len(procs) >= 4: procs.pop(0).wait()
    for p in procs: p.wait()
    for cid, (fn, s0, sp, dur, stab, grade) in CLIPS.items():
        out = os.path.join(cache, f"{cid}_{s0:.2f}_{sp:.2f}_{dur:.2f}.rgb")
        n = os.path.getsize(out) // (MW * MH * 3)
        MM[cid] = np.memmap(out, np.uint8, "r", shape=(n, MH, MW, 3))

def clip_frame(cid, lt, w, h, cx=0.5, zoom=1.0):
    """Cover-fit crop of clip `cid` at local time lt, as float array (h, w, 3)."""
    mm = MM[cid]
    fr = Image.fromarray(mm[min(max(int(lt * FPS), 0), len(mm) - 1)])
    sc = max(w / fr.width, h / fr.height) * zoom
    cw, ch = w / sc, h / sc
    x0 = clamp(fr.width * cx - cw / 2, 0, fr.width - cw); y0 = (fr.height - ch) / 2
    return np.asarray(fr.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch)), np.float32)

def full(cid, t, t0, z0=1.0, z1=1.06, dur=3.0, cx=0.5):
    """Full-bleed clip with a slow push."""
    return clip_frame(cid, t - t0, W, H, cx, z0 + (z1 - z0) * eio((t - t0) / dur))

def window(base, cid, t, t0, rect=None, circle=None, reveal=1.0, cx=0.5, zoom=1.04, blend=None):
    """Media window (rect: bottom-up clip reveal; circle: radial reveal). blend=(cid2, t2, dissolve) dissolves."""
    if reveal <= 0: return base
    if rect:
        x0, y0, x1, y1 = [int(v) for v in rect]
        w, h = x1 - x0, y1 - y0
        vy0 = int(y1 - h * reveal)
        m = np.zeros((H, W), np.float32); m[max(vy0, 0):min(y1, H), max(x0, 0):min(x1, W)] = 1
    else:
        ccx, ccy, r = circle
        x0, y0, x1, y1 = int(ccx - r), int(ccy - r), int(ccx + r), int(ccy + r); w, h = x1 - x0, y1 - y0
        m = np.clip((r * reveal - np.sqrt((XX - ccx) ** 2 + (YY - ccy) ** 2)) / 1.5, 0, 1)
    img = clip_frame(cid, t - t0, w, h, cx, zoom)
    if blend:
        cid2, t2, dd = blend
        if t >= t2:
            a = eio((t - t2) / dd)
            img = img * (1 - a) + clip_frame(cid2, t - t2, w, h, 0.5, zoom) * a
    out = base.copy()
    ys0, xs0, ye, xe = max(y0, 0), max(x0, 0), min(y1, H), min(x1, W)
    out[ys0:ye, xs0:xe] = img[ys0 - y0:ye - y0, xs0 - x0:xe - x0]
    m = m[..., None]
    return base * (1 - m) + out * m

LOGO = None
def logo_img(width):
    global LOGO
    if LOGO is None:
        LOGO = Image.open(os.path.join(IN, "logo.webp")).convert("RGBA")
    h = round(LOGO.height * width / LOGO.width)
    return LOGO.resize((width, h), Image.LANCZOS)

# ------------------------------------------------------------------ scenes (start, end)
S1, S2, S3, S4, S5, S6, S7, S8 = (0, 4.7), (4.7, 10.6), (10.6, 14.9), (14.9, 17.7), (17.7, 23.9), (23.9, 31.0), (31.0, 37.7), (37.7, TOTAL)

def comp(base, L):
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA"); out.alpha_composite(L)
    return np.asarray(out.convert("RGB"), np.float32)

def shadowed(base, L, k=0.5):
    a = L.getchannel("A").filter(ImageFilter.GaussianBlur(10))
    sh = Image.new("RGBA", (W, H), (25, 15, 12, 0)); sh.putalpha(a.point(lambda v: int(v * k)))
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    out.alpha_composite(sh, (0, 3)); out.alpha_composite(L)
    return np.asarray(out.convert("RGB"), np.float32)

def s1(t):   # "A new season brings a new reason to care for your skin."
    base = solid(DARK, t, 0.06); L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dy = -60 * eio(t / 4.7)
    line(L, 90, int(1100 + dy), 990, t, 0.25, IVORY, dur=1.3, center=True)
    header(L, t, 0.5, "SKN THEORY · SEASONAL SKINCARE", "01", IVORY)
    up = -100 * eio((t - V(1.3)) / 0.7)
    text(L, "A NEW SEASON.", SERIF(118), W / 2, 880 + dy + up, t, V(0.25), IVORY, 6, "center", dur=0.85, track_from=0)
    text(L, "a new reason to care.", ITAL(104), W / 2, 905 + dy, t, V(1.40), PEACH, 1, "center", dur=0.85)
    return comp(base, L)

def s2(t):   # "Introducing Whimsical Glow Peel, newly introduced at SKN Theory."
    base = solid(IVORY, t, 0.04); L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dy = -40 * eio((t - S2[0]) / 5.9)
    rect = (60, 230 + dy, 1020, 1250 + dy)
    rev = eo((t - 4.8) / 0.9) * (1 - eio((t - 10.25) / 0.35))
    base = window(base, "prod", t, 4.8, rect=rect, reveal=rev, cx=0.38, blend=("forehead", 7.9, 0.45))
    header(L, t, 4.8, "NEW AT SKN THEORY", "02", TAUPE, t_out=10.2)
    text(L, "INTRODUCING", SANS(28, "Bold"), W / 2, 1300 + dy, t, V(4.10), PEACH, 12, "center", t_out=10.2, track_from=4)
    text(L, "WHIMSICAL", SERIF(120, "SemiBold"), W / 2, 1335 + dy, t, V(4.80), BROWN, 6, "center", t_out=10.2, track_from=0)
    text(L, "GLOW PEEL", SERIF(120, "SemiBold"), W / 2, 1465 + dy, t, V(5.35), BROWN, 6, "center", t_out=10.2, track_from=0)
    line(L, 340, int(1615 + dy), 740, t, V(5.9), PEACH, th=3, t_out=10.2, center=True)
    text(L, "NEWLY INTRODUCED AT SKN THEORY", SANS(27, "SemiBold"), W / 2, 1650 + dy, t, V(6.70), BROWN, 6, "center", t_out=10.2)
    return comp(base, L)

TL_Y = 600
def s3(t):   # "As fall arrives, it's time to rethink your skincare routine."
    base = solid(DARK, t, 0.05); L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    ga = int(16 * eo((t - 10.6) / 0.6))
    for gx in range(90, W, 150): d.line((gx, 0, gx, H), fill=IVORY + (ga,), width=1)
    for gy in range(120, H, 150): d.line((0, gy, W, gy), fill=IVORY + (ga,), width=1)
    header(L, t, 10.65, "WHY THE SEASON MATTERS", "03", IVORY)
    line(L, 120, TL_Y, 960, t, 10.6, IVORY, dur=0.6, alpha=200)
    for i, mth in enumerate(["JUN", "JUL", "AUG", "SEP", "OCT", "NOV"]):
        x = 150 + i * 156; p = eo((t - 10.7 - i * 0.04) / 0.35)
        if p > 0:
            d.line((x, TL_Y - 10 * p, x, TL_Y + 10 * p), fill=IVORY + (int(170 * p),), width=2)
            text(L, mth, SANS(16, "Medium"), x, TL_Y + 22, t, 10.7 + i * 0.04, TAUPE, 3, "center", dur=0.35)
    mx = 228 + (774 - 228) * eio((t - 10.7) / 0.45)
    d.ellipse((mx - 11, TL_Y - 11, mx + 11, TL_Y + 11), outline=PEACH + (255,), width=3)
    d.ellipse((mx - 4, TL_Y - 4, mx + 4, TL_Y + 4), fill=PEACH + (255,))
    text(L, "SUMMER", SERIF(140), W / 2, 340, t, 10.6, TAUPE, 10, "center", dur=0.3, t_out=10.8, out_dur=0.25)
    text(L, "FALL", SERIF(250), W / 2, 290, t, V(10.25), IVORY, 30, "center", dur=0.8, track_from=6)
    text(L, "TIME TO RETHINK", SANS(32, "Bold"), W / 2, 700, t, V(12.0), IVORY, 8, "center")
    text(L, "YOUR SKINCARE ROUTINE", SANS(32, "Bold"), W / 2, 748, t, V(12.55), PEACH, 8, "center")
    cx, cy, r = 540, 1330, 390
    base = window(base, "micro", t, 11.0, circle=(cx, cy, r), reveal=eo((t - 11.0) / 0.9), zoom=1.15)
    ring = eo((t - 11.4) / 0.9)
    if ring > 0: d.arc((cx - r - 24, cy - r - 24, cx + r + 24, cy + r + 24), -90, -90 + 360 * ring, fill=PEACH + (200,), width=2)
    text(L, "FIG. 01 · MICROSCOPIC VIEW (CONCEPTUAL)", SANS(15, "Medium"), W / 2, cy + r + 44, t, 12.0, TAUPE, 4, "center")
    return comp(base, L)

def s4(t):   # "Discover a little extra care."
    cid, t0 = ("prep", 14.9) if t < 16.3 else ("bowl", 16.3)
    base = full(cid, t, t0, 1.04, 1.1, 1.6)
    base = base * (1 - BOTSH)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    header(L, t, 15.0, "IN CLINIC", "04", IVORY)
    line(L, 70, 1405, 200, t, V(14.26), PEACH, th=3)
    text(L, "DISCOVER", SANS(34, "Bold"), 70, 1430, t, V(14.26), IVORY, 12, track_from=4)
    text(L, "a little extra care.", ITAL(112), 66, 1475, t, V(14.82), IVORY, 1)
    return shadowed(base, L, 0.5)

def s5(t):   # "A moment to focus on skin that looks refreshed ... and naturally radiant."
    base = full("cells", t, 17.7, 1.0, 1.08, 6.2)
    base = base * (1 - np.clip(BOTSH * 1.35, 0, 0.8)) * (1 - TOPSH * 0.6)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    header(L, t, 17.8, "A MOMENT TO FOCUS", "05", IVORY)
    for (px, py, sx, sy) in ((60, 230, 1, 1), (1020, 230, -1, 1), (60, 1260, 1, -1), (1020, 1260, -1, -1)):
        a = int(200 * eo((t - 18.0) / 0.6))
        d.line((px, py, px + 40 * sx, py), fill=IVORY + (a,), width=2); d.line((px, py, px, py + 40 * sy), fill=IVORY + (a,), width=2)
    text(L, "FIG. 02 · CONCEPTUAL VISUALIZATION", SANS(15, "Medium"), 60, 1280, t, 18.2, IVORY, 4)
    text(L, "A MOMENT TO FOCUS ON YOUR SKIN", SANS(28, "Bold"), W / 2, 1395, t, V(17.04), IVORY, 6, "center", t_out=23.5)
    text(L, "refreshed", ITAL(140), W / 2, 1440, t, V(19.72), IVORY, 1, "center", t_out=V(20.75), out_dur=0.35)
    text(L, "NATURALLY", SERIF(104, "SemiBold"), W / 2, 1440, t, V(20.91), IVORY, 8, "center", t_out=23.5)
    text(L, "radiant", ITAL(128), W / 2, 1555, t, V(21.6), PEACH, 1, "center", t_out=23.5)
    return shadowed(base, L, 0.55)

def s6(t):   # "Because great skincare isn't just about looking good, it's about feeling confident in your own skin."
    if t < 25.4: cid, t0 = "cheek", 23.9
    elif t < 26.9: cid, t0 = "close1", 25.4
    elif t < 28.25: cid, t0 = "close2", 26.9
    else: cid, t0 = "mask", 28.25
    base = full(cid, t, t0, 1.04, 1.1, 1.6 if cid != "mask" else 2.8)
    base = base * (1 - np.clip(TOPSH * 1.4, 0, 0.8))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    header(L, t, 24.0, "BEYOND THE SURFACE", "06", IVORY)
    text(L, "GREAT SKINCARE", SANS(34, "Bold"), W / 2, 285, t, V(23.85), IVORY, 10, "center", t_out=V(27.0), track_from=4)
    text(L, "isn't just about", ITAL(100), W / 2, 330, t, V(25.18), IVORY, 1, "center", t_out=V(27.0))
    text(L, "looking good.", ITAL(100), W / 2, 430, t, V(25.95), PEACH, 1, "center", t_out=V(27.0))
    text(L, "IT'S ABOUT FEELING", SANS(34, "Bold"), W / 2, 285, t, V(27.45), IVORY, 10, "center", t_out=30.6, track_from=4)
    text(L, "confident", ITAL(124), W / 2, 330, t, V(28.03), PEACH, 1, "center", t_out=30.6)
    text(L, "in your own skin.", ITAL(100), W / 2, 460, t, V(28.85), IVORY, 1, "center", t_out=30.6)
    return shadowed(base, L, 0.55)

def s7(t):   # "With wedding season just around the corner, now is the time to start planning your glow."
    base = solid(IVORY, t, 0.04); L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    dy = -40 * eio((t - S7[0]) / 6.7)
    lift = -260 * ei((t - 37.25) / 0.5)
    header(L, t, 31.1, "THE SEASON OF CELEBRATIONS", "07", TAUPE)
    text(L, "WEDDING", SERIF(150, "SemiBold"), 70, 300 + dy + lift, t, V(30.98), BROWN, 4, track_from=-2)
    text(L, "SEASON", SERIF(150, "SemiBold"), 70, 450 + dy + lift, t, V(31.25), BROWN, 4, track_from=-2)
    text(L, "is just around", ITAL(96), 74, 610 + dy + lift, t, V(32.11), TAUPE, 1)
    text(L, "the corner.", ITAL(96), 74, 705 + dy + lift, t, V(32.55), TAUPE, 1)
    sx = 520 * (1 - eo((t - 32.2) / 0.9))
    rect = (540 + sx, 880 + dy, 1020 + sx, 1640 + dy)
    if t >= 32.2:
        base = window(base, "layers", t, 31.2, rect=rect, reveal=1.0, zoom=1.06)
        text(L, "FIG. 03 · SKIN LAYERS (CONCEPTUAL)", SANS(14, "Medium"), 1020, 1655 + dy, t, 32.8, TAUPE, 3, "right")
    cxd, cyd, r = 270, 1090 + dy, 150
    p = eo((t - 32.6) / 0.6)
    if p > 0:
        for k in range(48):
            a = math.radians(-90 + k * 7.5); lg = k % 6 == 0
            done = (k / 48) < 1 - clamp((t - 33.0) / 4.0) * 0.75
            r0 = r - (22 if lg else 12)
            d.line((cxd + r0 * math.cos(a), cyd + r0 * math.sin(a), cxd + r * math.cos(a), cyd + r * math.sin(a)),
                   fill=(BROWN if done else TAUPE) + (int((220 if done else 90) * p),), width=2 if lg else 1)
        text(L, "COUNTDOWN", SANS(16, "Bold"), cxd, cyd - 12, t, 32.8, TAUPE, 5, "center")
    line(L, 70, int(1395 + dy), 290, t, V(33.73), PEACH, th=3)
    text(L, "NOW IS THE TIME", SANS(28, "Bold"), 70, 1420 + dy, t, V(33.73), BROWN, 6)
    text(L, "TO START", SANS(28, "Bold"), 70, 1462 + dy, t, V(34.72), BROWN, 6)
    text(L, "PLANNING", SANS(28, "Bold"), 70, 1504 + dy, t, V(34.84), BROWN, 6)
    text(L, "your glow.", ITAL(96), 66, 1540 + dy, t, V(35.6), PEACH, 1)
    return comp(base, L)

def s8(t):   # "Discover the Whimsical Glow Peel at SKN Theory. Your glow season starts here. Book your consultation today."
    base = solid(IVORY, t, 0.05)
    g = np.exp(-(((XX - W / 2) / 620) ** 2 + ((YY - 940) / 520) ** 2))[..., None]
    base = base * (1 - 0.18 * g) + np.array(BLUSH, np.float32) * 0.18 * g
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text(L, "DISCOVER THE", SANS(28, "Bold"), W / 2, 250, t, V(37.07), PEACH, 12, "center", track_from=4)
    text(L, "WHIMSICAL", SERIF(124, "SemiBold"), W / 2, 290, t, V(37.76), BROWN, 8, "center", track_from=0)
    text(L, "GLOW PEEL", SERIF(124, "SemiBold"), W / 2, 420, t, V(38.36), BROWN, 8, "center", track_from=0)
    line(L, 380, 575, 700, t, V(39.0), PEACH, th=3, center=True)
    # official logo: opacity + 96->100% scale, on the word "SKN Theory"
    p = eo((t - V(39.9)) / 0.9)
    if p > 0:
        lg = logo_img(int(700 * (0.96 + 0.04 * p)))
        if p < 1:
            lg = lg.copy(); lg.putalpha(lg.getchannel("A").point(lambda v: int(v * p)))
        L.alpha_composite(lg, (int(W / 2 - lg.width / 2), int(1000 - lg.height / 2)))
    text(L, "YOUR GLOW SEASON STARTS HERE", SANS(30, "SemiBold"), W / 2, 1300, t, V(41.74), BROWN, 6, "center")
    q = eo((t - V(44.07)) / 0.7)
    if q > 0:
        d = ImageDraw.Draw(L); w2 = 360 * q
        d.rounded_rectangle((W / 2 - w2, 1420, W / 2 + w2, 1524), radius=52, fill=BROWN + (int(235 * q),))
    text(L, "BOOK YOUR CONSULTATION TODAY", SANS(30, "Bold"), W / 2, 1452, t, V(44.25), IVORY, 5, "center")
    return comp(base, L)

SCENES = [(S1, s1), (S2, s2), (S3, s3), (S4, s4), (S5, s5), (S6, s6), (S7, s7), (S8, s8)]

def scene_at(t):
    for (a, b), fn in SCENES:
        if a <= t < b: return fn(t)
    return s8(t)

def frame(t):
    out = scene_at(t)
    # ---- motivated transitions
    if 4.35 <= t < 5.05:                          # S1 hairline opens into an ivory wipe
        p = eio((t - 4.35) / 0.7); cy = 1100 - 60 * eio(min(t, 4.7) / 4.7)
        m = (np.abs(YY - cy) < max(1, (H / 2 + 60) * p)).astype(np.float32)[..., None]
        prev = out if t < 4.7 else s1(4.69); cur = out if t >= 4.7 else solid(IVORY, t, 0.04)
        out = prev * (1 - m) + cur * m
    if 10.25 <= t < 10.95:                        # S2 -> S3 dark graphic wipe, right to left
        p = eio((t - 10.25) / 0.7); edge = W * (1 - p)
        m = (XX >= edge).astype(np.float32)[..., None]
        prev = out if t < 10.6 else s2(10.59); cur = out if t >= 10.6 else solid(DARK, t, 0.05)
        out = prev * (1 - m) + cur * m; out[np.abs(XX - edge) < 2] = np.array(PEACH, np.float32)
    if 14.55 <= t < 15.25:                        # S3 microscope circle expands into the clinic footage
        p = eio((t - 14.55) / 0.7); R = 390 + 1900 * p
        m = np.clip((R - np.sqrt((XX - 540) ** 2 + (YY - 1330) ** 2)) / 3, 0, 1)[..., None]
        prev = out if t < 14.9 else s3(14.89); cur = s4(max(t, 14.9))
        out = prev * (1 - m) + cur * m
    if 17.45 <= t < 17.95:                        # S4 -> S5 light dissolve into the cells
        a = eio((t - 17.45) / 0.5)
        out = s4(min(t, 17.69)) * (1 - a) + s5(max(t, 17.7)) * a
    if 23.65 <= t < 24.15:                        # S5 -> S6 dissolve
        a = eio((t - 23.65) / 0.5)
        out = s5(min(t, 23.89)) * (1 - a) + s6(max(t, 23.9)) * a
    if 30.65 <= t < 31.3:                         # S6 -> S7 soft ivory wipe from the top
        p = eio((t - 30.65) / 0.65); m = np.clip((H * p - YY) / 80, 0, 1)[..., None]
        prev = out if t < 31.0 else s6(30.99); cur = out if t >= 31.0 else solid(IVORY, t, 0.04)
        out = prev * (1 - m) + cur * m
    if 37.25 <= t < 38.05:                        # S7 -> S8 blush panel rises as a mask, type lifts away
        p = eio((t - 37.25) / 0.8); edge = H * (1 - p)
        m = np.clip((YY - edge) / 2, 0, 1)[..., None]
        prev = out if t < 37.7 else s7(37.69); cur = s8(max(t, 37.7))
        out = prev * (1 - m) + cur * m; out[np.abs(YY - edge) < 1.5] = np.array(PEACH, np.float32)
    out = out * VIG
    out = out + np.repeat(np.repeat(GRAIN[int(t * FPS) % 8], 2, 0), 2, 1) * 3.0
    fade = min(clamp(t / 0.5), clamp((TOTAL - t) / 0.7))
    return np.clip(out * fade, 0, 255).astype(np.uint8)

BOUNDS = []

def work(k):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", f"_part{k}.mp4"], stdin=subprocess.PIPE)
    for i in range(BOUNDS[k], BOUNDS[k + 1]): enc.stdin.write(frame(i / FPS).tobytes())
    enc.stdin.close(); enc.wait(); return f"_part{k}.mp4"

if __name__ == "__main__":
    load_media()
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(frame(t)).save(f"v3_{t:05.2f}.jpg", quality=90)
        sys.exit()
    import multiprocessing as mp
    N = int(TOTAL * FPS); n = 3
    BOUNDS[:] = list(np.linspace(0, N, n + 1).astype(int))
    with mp.get_context("fork").Pool(n) as pool:
        parts = pool.map(work, range(n))
    open("_parts.txt", "w").writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "_parts.txt", "-c", "copy", sys.argv[2]], check=True)
    print("done", sys.argv[2])
