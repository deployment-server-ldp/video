"""SKN Theory — Whimsical Glow Peel · "The Science of a New Glow Season"
Documentary-style motion graphics foundation, 1080x1920 @30fps, 40.5 s, synced to the supplied VO.

Modes
  labeled  production preview: placeholder windows carry their labels/specs
  clean    publish-ready graphics: placeholders are neutral textured panels, no labels
  matte    white = media windows (exact shape, reveal and timing), black elsewhere — use as a track matte
  footage  clean graphics with the client's real treatment footage inside the treatment windows

Usage: python mg.py MODE out.mp4 [--frames t1,t2,..] [--footage DIR]
"""
import functools, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
TOTAL = 40.5
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "..", "fonts")
MODE = sys.argv[1] if len(sys.argv) > 1 else "labeled"

CHAR = (33, 31, 29); IVORY = (245, 240, 233); CHAMP = (215, 196, 173); TAUPE = (161, 142, 128); BLUSH = (216, 185, 177)
BEIGE_BG = (237, 229, 219)

# scene windows (s)
S1, S2, S3, S4, S5, S6 = (0, 5.0), (5.0, 11.6), (11.6, 17.8), (17.8, 23.6), (23.6, 30.2), (30.2, TOTAL)

# VO placement: (src_start, src_end, timeline_start). Phrases are moved, never stretched.
VO = [(0.0, 3.40, 1.2), (3.85, 6.25, 5.9), (6.70, 9.00, 8.55), (9.50, 13.25, 12.6),
      (13.28, 15.30, 18.4), (15.72, 20.60, 24.2), (21.20, 27.00, 30.8), (27.65, 29.30, 37.3)]

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3                 # standard ease-out (all entrances)
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)       # standard ease-in-out (moves, wipes)
def ei(p): return clamp(p) ** 3

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

def text(L, s, fnt, x, y, t, t0, color, tracking=0, align="left", dur=0.75, t_out=None, out_dur=0.5,
         track_from=None, dy=0.0, alpha=1.0):
    """Masked vertical reveal (line rises from behind its own baseline), optional tracking
    expansion and a masked exit (line drops back behind the baseline)."""
    if t < t0: return
    p = eo((t - t0) / dur)
    trk = tracking if track_from is None else track_from + (tracking - track_from) * eo((t - t0) / (dur * 1.8))
    im = word_img(s, fnt, color, round(trk, 1))
    if t_out is not None and t > t_out:
        p = min(p, 1 - ei((t - t_out) / out_dur))
        if p <= 0: return
    h = im.height
    off = int((1 - p) * h * 0.92)
    if off >= h: return
    vis = im.crop((0, 0, im.width, h - off))
    if alpha < 1:
        vis = vis.copy(); vis.putalpha(vis.getchannel("A").point(lambda v: int(v * alpha)))
    xx = x - im.width / 2 if align == "center" else x - im.width if align == "right" else x
    L.alpha_composite(vis, (int(xx), int(y + off + dy)))

def line(L, x0, y, x1, t, t0, color, dur=0.9, th=2, t_out=None, alpha=230, from_center=False):
    p = eio((t - t0) / dur)
    if t_out is not None: p *= 1 - eio((t - t_out) / 0.5)
    if p <= 0: return
    d = ImageDraw.Draw(L)
    if from_center:
        c = (x0 + x1) / 2; hw = (x1 - x0) / 2 * p
        d.rectangle((c - hw, y, c + hw, y + th - 1), fill=color + (alpha,))
    else:
        d.rectangle((x0, y, x0 + (x1 - x0) * p, y + th - 1), fill=color + (alpha,))

# ------------------------------------------------------------------ textures
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_rr = np.sqrt(((XX - W / 2) / (W * 0.8)) ** 2 + ((YY - H / 2) / (H * 0.75)) ** 2)
VIG = np.clip(1 - 0.22 * np.clip(_rr - 0.45, 0, None) ** 1.3, 0.75, 1)[..., None].astype(np.float32)
GRAIN = [np.random.default_rng(i).normal(0, 1, (H // 2, W // 2, 1)).astype(np.float32) for i in range(8)]

def solid(color, t, light=0.05):
    """Flat brand colour with a slow, soft light drift (keeps flat fields alive)."""
    base = np.empty((H, W, 3), np.float32); base[:] = color
    cx = W * (0.35 + 0.25 * math.sin(t * 0.21)); cy = H * (0.35 + 0.12 * math.cos(t * 0.17))
    g = np.exp(-(((XX - cx) / (W * 0.9)) ** 2 + ((YY - cy) / (H * 0.5)) ** 2))[..., None]
    lift = 255 if sum(color) < 300 else 255
    return base * (1 - light * g) + lift * light * g

@functools.lru_cache(maxsize=8)
def ph_texture(w, h, seed):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (h // 8 + 2, w // 8 + 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n - n.min()) / (np.ptp(n) + 1e-6) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    yy = np.linspace(0, 1, h)[:, None]
    base = np.array(TAUPE, np.float32) * (0.62 + 0.18 * yy[..., None]) + np.array(CHAMP, np.float32) * (0.2 - 0.1 * yy[..., None])
    return base * (0.94 + 0.10 * n[..., None])

# ------------------------------------------------------------------ media windows
WINDOWS = []   # filled per frame: (kind, shape, params, opacity) — used by matte mode and the spec
FOOTAGE = {}   # placeholder id -> (memmap frames, start_time)

PH_SPEC = {
    "PH1": dict(label="REAL SKN THEORY TREATMENT FOOTAGE", t=(5.3, 11.6), aspect="3:7 portrait window (440x1035)",
                trans_in="clip-reveal upward with the title", trans_out="horizontal charcoal graphic wipe"),
    "PH2": dict(label="AI 3D SKIN SURFACE ANIMATION", t=(13.0, 17.8), aspect="circle Ø620 (render square 1:1)",
                trans_in="radial reveal from the timeline marker", trans_out="marker expands into circular wipe"),
    "PH3": dict(label="REAL TREATMENT CLOSE-UP OR AI SKIN CGI", t=(18.0, 23.6), aspect="4:5 window (800x1000)",
                trans_in="circular wipe lands, window settles", trans_out="vertical ivory wipe"),
    "PH4": dict(label="CINEMATIC BRIDAL BEAUTY B-ROLL", t=(25.9, 30.2), aspect="2:3 portrait window (440x660)",
                trans_in="slides in from the right", trans_out="charcoal typographic mask rise"),
    "LOGO": dict(label="BRAND ASSET — SKN THEORY LOGO (official file)", t=(36.5, TOTAL), aspect="max 560x170, keep proportions",
                 trans_in="opacity 0→100 + scale 96→100%, 0.9 s", trans_out="final fade"),
}

def media_window(base, pid, rect=None, circle=None, t=0.0, reveal=1.0, opacity=1.0, seed=1):
    """Draw a replaceable media area. rect=(x0,y0,x1,y1); circle=(cx,cy,r). reveal 0..1 grows the
    visible portion (rect: bottom-up clip; circle: radius)."""
    if reveal <= 0 or opacity <= 0: return base
    if rect:
        x0, y0, x1, y1 = [int(v) for v in rect]
        vy0 = int(y1 - (y1 - y0) * reveal)
        m = np.zeros((H, W), np.float32); m[max(vy0, 0):y1, x0:x1] = 1
        shape = ("rect", (x0, vy0, x1, y1))
    else:
        cx, cy, r = circle
        rr = r * reveal
        m = np.clip((rr - np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)) / 1.5, 0, 1)
        x0, y0, x1, y1 = int(cx - r), int(cy - r), int(cx + r), int(cy + r)
        shape = ("circle", (cx, cy, rr))
    WINDOWS.append((pid, shape, opacity))
    w, h = x1 - x0, y1 - y0
    content = None
    if MODE == "footage" and pid in FOOTAGE:
        content = footage_content(pid, t, w, h)
    if content is None:
        content = ph_texture(w, h, seed).copy()
        # slow light pass so the temp plate reads as "footage area", not a flat box
        g = np.exp(-(((np.arange(w)[None, :] - w * (0.5 + 0.4 * math.sin(t * 0.6))) / (w * 0.5)) ** 2))[..., None]
        content = content * (1 - 0.08 * g) + 255 * 0.08 * g
    full = base.copy()
    ys0, xs0 = max(y0, 0), max(x0, 0)
    ye, xe = min(y1, H), min(x1, W)          # windows may slide partly off-frame
    if ye > ys0 and xe > xs0:
        full[ys0:ye, xs0:xe] = content[ys0 - y0:ye - y0, xs0 - x0:xe - x0]
    mm3 = (m * opacity)[..., None]
    return base * (1 - mm3) + full * mm3

def ph_label(L, pid, rect=None, circle=None, alpha=1.0):
    if MODE != "labeled" or alpha <= 0.01: return
    spec = PH_SPEC[pid]
    if rect: x0, y0, x1, y1 = rect; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; ww = x1 - x0
    else: cx, cy, r = circle; x0, y0, x1, y1 = cx - r, cy - r, cx + r, cy + r; ww = 2 * r * 0.75
    d = ImageDraw.Draw(L); a = int(255 * alpha)
    for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):   # crop marks
        d.line((px, py, px + 34 * sx, py), fill=IVORY + (a,), width=2); d.line((px, py, px, py + 34 * sy), fill=IVORY + (a,), width=2)
    lines = [f"[PLACEHOLDER — {spec['label']}]" if pid != "LOGO" else f"[{spec['label']}]",
             f"{pid} · {spec['t'][0]:.1f}–{spec['t'][1]:.1f}s · {spec['aspect']}",
             f"IN: {spec['trans_in']}", f"OUT: {spec['trans_out']}"]
    y = cy - 70
    for i, s in enumerate(lines):
        f = SANS(19 if i == 0 else 15, "Bold" if i == 0 else "Medium")
        # wrap to window width
        words, row, rows = s.split(" "), "", []
        for wd in words:
            if f.getlength(row + " " + wd) > ww - 40 and row: rows.append(row); row = wd
            else: row = (row + " " + wd).strip()
        rows.append(row)
        for r_ in rows:
            d.text((cx - f.getlength(r_) / 2, y), r_, font=f, fill=IVORY + (a,)); y += f.size + 8
        y += 8

# ------------------------------------------------------------------ scenes
def drift(t, a, b, amount=60):
    """Camera-inspired slow vertical drift across a scene (content moves up)."""
    return -amount * eio((t - a) / (b - a))

def scene1(t):
    base = solid(CHAR, t, 0.06)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dy = drift(t, *S1, 70)
    line(L, 90, int(1080 + dy), 990, t, 0.3, IVORY, dur=1.4, th=2, from_center=True)
    text(L, "SKN THEORY", SANS(24, "Bold"), 90, 150 + dy * 0.4, t, 0.6, IVORY, 9, dur=0.6, track_from=2)
    text(L, "SEASONAL SKINCARE", SANS(20, "Medium"), 90, 186 + dy * 0.4, t, 0.8, TAUPE, 7, dur=0.6)
    text(L, "01", SANS(20, "Medium"), 990, 150 + dy * 0.4, t, 0.8, TAUPE, 2, align="right")
    up = -95 * eio((t - 2.75) / 0.8)
    text(L, "A NEW SEASON.", SERIF(118), W / 2, 880 + dy + up, t, 1.35, IVORY, 6, align="center", dur=0.9, track_from=0)
    text(L, "a new glow.", ITAL(132), W / 2, 905 + dy, t, 2.9, CHAMP, 1, align="center", dur=0.9)
    text(L, "THE SCIENCE OF A NEW GLOW SEASON", SANS(20, "Medium"), W / 2, 1110 + dy, t, 3.4, TAUPE, 6, align="center")
    return base, L

def scene2(t):
    base = solid(IVORY, t, 0.04)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dy = drift(t, *S2, 50)
    rect = (580, 420 + dy, 1020, 1455 + dy)
    rev = eo((t - 5.3) / 1.0)
    out = 1 - eio((t - 11.15) / 0.45)
    base = media_window(base, "PH1", rect=rect, t=t, reveal=rev * out, seed=3)
    ph_label(L, "PH1", rect=rect, alpha=rev * out)
    text(L, "FIG. 01 — IN CLINIC", SANS(16, "Medium"), 580, 1475 + dy, t, 6.2, TAUPE, 5, t_out=11.1)
    text(L, "NEW AT SKN THEORY", SANS(22, "Bold"), 70, 560 + dy, t, 5.55, TAUPE, 6, track_from=1, t_out=11.1)
    line(L, 70, int(610 + dy), 140, t, 5.75, CHAMP, dur=0.5, t_out=11.1)
    text(L, "WHIMSICAL", SERIF(76, "SemiBold"), 66, 655 + dy, t, 6.85, CHAR, 2, track_from=-4, t_out=11.1)
    text(L, "GLOW PEEL", SERIF(76, "SemiBold"), 66, 742 + dy, t, 7.45, CHAR, 2, track_from=-4, t_out=11.1)
    line(L, 70, int(850 + dy), 440, t, 7.9, CHAMP, dur=0.9, th=3, t_out=11.1)
    text(L, "A SEASONAL", SANS(22, "Medium"), 70, 885 + dy, t, 9.85, CHAR, 6, t_out=11.1)
    text(L, "SKINCARE EXPERIENCE", SANS(22, "Medium"), 70, 920 + dy, t, 10.0, CHAR, 6, t_out=11.1)
    text(L, "02", SANS(20, "Medium"), 990, 150, t, 5.4, TAUPE, 2, align="right", t_out=11.1)
    return base, L

TL_Y = 640
def scene3(t):
    base = solid(CHAR, t, 0.05)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    dy = drift(t, *S3, 40)
    # faint documentary grid
    ga = int(18 * eo((t - 11.7) / 0.8))
    for gx in range(90, W, 150): d.line((gx, 0, gx, H), fill=IVORY + (ga,), width=1)
    for gy in range(120, H, 150): d.line((0, gy + dy * 0.3, W, gy + dy * 0.3), fill=IVORY + (ga,), width=1)
    text(L, "WHY THE SEASON MATTERS", SANS(22, "Bold"), 90, 150, t, 11.75, IVORY, 6, track_from=1)
    text(L, "03", SANS(20, "Medium"), 990, 150, t, 11.8, TAUPE, 2, align="right")
    # timeline
    ty = int(TL_Y + dy)
    line(L, 120, ty, 960, t, 11.8, IVORY, dur=0.9, th=2, alpha=200)
    months = ["JUN", "JUL", "AUG", "SEP", "OCT", "NOV"]
    for i, m in enumerate(months):
        x = 150 + i * 156
        p = eo((t - 12.0 - i * 0.05) / 0.4)
        if p > 0:
            d.line((x, ty - 10 * p, x, ty + 10 * p), fill=IVORY + (int(170 * p),), width=2)
            text(L, m, SANS(16, "Medium"), x, ty + 22, t, 12.0 + i * 0.05, TAUPE, 3, align="center", dur=0.4)
    # indicator: summer -> fall
    mx = 228 + (774 - 228) * eio((t - 12.2) / 0.75)
    pin = eo((t - 11.95) / 0.4)
    if pin > 0:
        d.ellipse((mx - 11 * pin, ty - 11 * pin, mx + 11 * pin, ty + 11 * pin), outline=CHAMP + (255,), width=3)
        d.ellipse((mx - 4, ty - 4, mx + 4, ty + 4), fill=CHAMP + (255,))
    text(L, "SUMMER", SERIF(150, "Medium"), W / 2, 380 + dy, t, 11.85, TAUPE, 10, align="center", dur=0.6, t_out=12.45, out_dur=0.35)
    text(L, "FALL", SERIF(250, "Medium"), W / 2, 330 + dy, t, 12.8, IVORY, 30, align="center", dur=0.85, track_from=6)
    text(L, "A TIME TO REVISIT", SANS(30, "SemiBold"), W / 2, 760 + dy, t, 14.45, IVORY, 7, align="center")
    text(L, "YOUR SKINCARE ROUTINE", SANS(30, "SemiBold"), W / 2, 806 + dy, t, 14.6, IVORY, 7, align="center")
    # 3D placeholder, circular mask, with editorial markers around it
    cx, cy, r = 540, 1300 + dy, 310
    rev = eo((t - 13.0) / 1.0)
    base = media_window(base, "PH2", circle=(cx, cy, r), t=t, reveal=rev, seed=7)
    ph_label(L, "PH2", circle=(cx, cy, r), alpha=rev)
    ring = eo((t - 13.4) / 1.0)
    if ring > 0:
        d.arc((cx - r - 26, cy - r - 26, cx + r + 26, cy + r + 26), -90, -90 + 360 * ring, fill=CHAMP + (200,), width=2)
        for k, ang in enumerate((210, 330, 90)):
            a_ = math.radians(ang); px, py = cx + (r + 26) * math.cos(a_), cy + (r + 26) * math.sin(a_)
            q = eo((t - 14.0 - k * 0.2) / 0.5)
            if q > 0:
                ex = px + (70 if math.cos(a_) > 0 else -70) * q
                d.line((px, py, ex, py), fill=CHAMP + (int(200 * q),), width=1)
    text(L, "FIG. 02", SANS(16, "Medium"), 120, cy - r - 10, t, 14.1, TAUPE, 4)
    text(L, "SURFACE", SANS(16, "Medium"), 960, cy - 150, t, 14.3, TAUPE, 4, align="right")
    return base, L

def skin_lines(L, t, t0, y0, color, n=7, alpha=120):
    """Fine curved contour lines inspired by skin texture — illustrative only."""
    d = ImageDraw.Draw(L)
    for k in range(n):
        p = eio((t - t0 - k * 0.12) / 1.4)
        if p <= 0: continue
        pts = []
        xs = np.linspace(-40, W + 40, 90)
        for x in xs[: max(2, int(len(xs) * p))]:
            y = y0 + k * 26 + 18 * math.sin(x / 140 + k * 0.7 + t * 0.4) + 8 * math.sin(x / 47 + k)
            pts.append((x, y))
        d.line(pts, fill=color + (int(alpha * (1 - k / (n + 2))),), width=2)

def scene4(t):
    base = solid(BEIGE_BG, t, 0.05)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    dy = drift(t, *S4, 50)
    rect = (140, 360 + dy, 940, 1360 + dy)
    rev = eo((t - 18.0) / 0.9)
    out = 1 - eio((t - 23.2) / 0.4)
    # parallax: window and lines drift at different rates
    base = media_window(base, "PH3", rect=rect, t=t, reveal=rev * out, seed=11)
    ph_label(L, "PH3", rect=rect, alpha=rev * out)
    skin_lines(L, t, 18.3, 1390 + dy * 1.6, TAUPE, alpha=int(150 * out))
    text(L, "THE GLOW EXPERIENCE", SANS(22, "Bold"), 90, 150, t, 18.0, CHAR, 6, track_from=1, t_out=23.2)
    text(L, "04", SANS(20, "Medium"), 990, 150, t, 18.0, TAUPE, 2, align="right", t_out=23.2)
    words = [("CARE", 19.9), ("RITUAL", 21.0), ("RADIANCE", 22.15)]
    for i, (wd, t0) in enumerate(words):
        t1 = words[i + 1][1] - 0.15 if i + 1 < len(words) else 23.15
        text(L, wd, SERIF(150, "Medium"), W / 2, 1530 + dy * 0.6, t, t0, CHAR, 14, align="center", dur=0.7,
             t_out=t1, out_dur=0.35, track_from=4)
        on = 1.0 if t0 <= t < t1 + 0.3 else 0.35
        d.ellipse((W / 2 - 40 + i * 40 - 5, 1745 + dy * 0.6 - 5, W / 2 - 40 + i * 40 + 5, 1745 + dy * 0.6 + 5),
                  fill=TAUPE + (int(255 * on * eo((t - 19.6) / 0.4) * out),))
    return base, L

def scene5(t):
    base = solid(IVORY, t, 0.04)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    dy = drift(t, *S5, 50)
    lift = -260 * ei((t - 29.6) / 0.6)                     # text exits upward under the rising mask
    text(L, "THE SEASON OF CELEBRATIONS", SANS(22, "Bold"), 90, 330 + dy + lift, t, 23.9, TAUPE, 6, track_from=1)
    text(L, "WEDDING", SERIF(150, "SemiBold"), 84, 380 + dy + lift, t, 24.5, CHAR, 4, track_from=-2)
    text(L, "SEASON", SERIF(150, "SemiBold"), 84, 530 + dy + lift, t, 24.7, CHAR, 4, track_from=-2)
    text(L, "is coming.", ITAL(132), 90, 690 + dy + lift, t, 25.85, TAUPE, 1)
    # countdown-inspired dial: tick ring sweeping down (no date, no numbers)
    cx, cy, r = 270, 1180 + dy, 150
    p = eo((t - 25.9) / 0.6)
    if p > 0:
        for k in range(48):
            a = math.radians(-90 + k * 7.5)
            long = k % 6 == 0
            done = (k / 48) < 1 - clamp((t - 26.2) / 3.4) * 0.75
            col = CHAR if done else TAUPE
            r0, r1 = r - (22 if long else 12), r
            d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                   fill=col + (int((220 if done else 90) * p),), width=2 if long else 1)
        text(L, "COUNTDOWN", SANS(16, "Bold"), cx, cy - 12, t, 26.0, TAUPE, 5, align="center")
    # portrait bridal placeholder slides in from the right
    sx = 520 * (1 - eo((t - 25.9) / 0.9))
    rect = (560 + sx, 940 + dy, 1000 + sx, 1600 + dy)
    vis = 1.0 if t >= 25.9 else 0.0
    base = media_window(base, "PH4", rect=rect, t=t, reveal=vis, seed=17)
    ph_label(L, "PH4", rect=rect, alpha=vis)
    line(L, 90, int(1480 + dy), 300, t, 27.7, CHAMP, dur=0.6, th=3)
    text(L, "PLAN YOUR", SANS(28, "Bold"), 90, 1505 + dy, t, 27.9, CHAR, 6)
    text(L, "GLOW AHEAD", SANS(28, "Bold"), 90, 1545 + dy, t, 28.05, CHAR, 6)
    text(L, "05", SANS(20, "Medium"), 990, 150, t, 23.8, TAUPE, 2, align="right")
    return base, L

def scene6(t):
    base = solid(CHAR, t, 0.06)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    line(L, 0, 980, W, t, 30.4, CHAMP, dur=1.1, th=2)                       # champagne line crosses
    text(L, "WHIMSICAL", SERIF(124, "Medium"), W / 2, 700, t, 31.25, IVORY, 10, align="center", track_from=2, dur=0.9)
    text(L, "GLOW PEEL", SERIF(124, "Medium"), W / 2, 830, t, 31.55, IVORY, 10, align="center", track_from=2, dur=0.9)
    text(L, "YOUR GLOW SEASON STARTS HERE", SANS(28, "SemiBold"), W / 2, 1010, t, 35.0, CHAMP, 7, align="center")
    # logo slot (official file goes here)
    p = eo((t - 36.5) / 0.9)
    if MODE == "labeled" and p > 0:
        lr = (W / 2 - 280, 1120, W / 2 + 280, 1290)
        ph_label(L, "LOGO", rect=lr, alpha=p)
    if p > 0: WINDOWS.append(("LOGO", ("rect", (int(W / 2 - 280), 1120, int(W / 2 + 280), 1290)), p))
    # CTA
    q = eo((t - 37.35) / 0.7)
    if q > 0:
        d = ImageDraw.Draw(L); w2 = 300 * q
        d.rounded_rectangle((W / 2 - w2, 1395, W / 2 + w2, 1495), radius=50, outline=IVORY + (int(220 * q),), width=2)
    text(L, "BOOK YOUR CONSULTATION", SANS(30, "Bold"), W / 2, 1424, t, 37.6, IVORY, 6, align="center")
    text(L, "SKN THEORY", SERIF(56, "SemiBold"), W / 2, 1560, t, 37.95, CHAMP, 18, align="center", track_from=8)
    return base, L

SCENES = [(S1, scene1), (S2, scene2), (S3, scene3), (S4, scene4), (S5, scene5), (S6, scene6)]

def comp(base, L):
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    out.alpha_composite(L)
    return np.asarray(out.convert("RGB"), np.float32)

def render_scene(t):
    for (a, b), fn in SCENES:
        if a <= t < b or (fn is scene6 and t >= a):
            return comp(*fn(t))
    return comp(*scene6(t))

def frame(t):
    WINDOWS.clear()
    out = render_scene(t)
    # ---- transitions (all motivated by an element of the outgoing scene)
    if 4.55 <= t < 5.25:                       # S1 line expands into a full-screen ivory wipe
        p = eio((t - 4.55) / 0.7)
        half = (H / 2 + 40) * p
        cy = 1080 + drift(t, *S1, 70)
        m = (np.abs(YY - cy) < max(1, half)).astype(np.float32)[..., None]
        prev = out if t < 5.0 else comp(*scene1(4.99))
        cur = out if t >= 5.0 else solid(IVORY, t, 0.04)
        out = prev * (1 - m) + cur * m
    if 11.25 <= t < 11.95:                     # S2 -> S3: charcoal graphic wipe, right to left
        p = eio((t - 11.25) / 0.7)
        edge = W * (1 - p)
        m = (XX >= edge).astype(np.float32)[..., None]
        prev = out if t < 11.6 else None
        cur = render_scene(max(t, 11.6)) if t >= 11.6 else solid(CHAR, t, 0.05)
        if prev is None: prev = render_scene(11.59)
        out = prev * (1 - m) + cur * m
        d = np.abs(XX - edge) < 2
        out[d] = np.array(CHAMP, np.float32)
    if 17.35 <= t < 18.05:                     # S3 timeline marker enlarges into a circular wipe
        p = eio((t - 17.35) / 0.7)
        cx, cy = 774, TL_Y + drift(17.35, *S3, 40)
        R = 2300 * p
        m = np.clip((R - np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)) / 3, 0, 1)[..., None]
        prev = out if t < 17.8 else comp(*scene3(17.79))
        cur = render_scene(max(t, 17.8)) if t >= 17.8 else solid(BEIGE_BG, t, 0.05)
        out = prev * (1 - m) + cur * m
    if 23.2 <= t < 23.85:                      # S4 -> S5: soft vertical ivory wipe from the top
        p = eio((t - 23.2) / 0.65)
        edge = H * p
        m = np.clip((edge - YY) / 80, 0, 1)[..., None]
        prev = out if t < 23.6 else comp(*scene4(23.59))
        cur = render_scene(max(t, 23.6)) if t >= 23.6 else solid(IVORY, t, 0.04)
        out = prev * (1 - m) + cur * m
    if 29.6 <= t < 30.45:                      # S5 -> S6: charcoal rises as a mask while type lifts away
        p = eio((t - 29.6) / 0.85)
        edge = H * (1 - p)
        m = np.clip((YY - edge) / 2, 0, 1)[..., None]
        prev = out if t < 30.2 else comp(*scene5(30.19))
        cur = render_scene(max(t, 30.2)) if t >= 30.2 else solid(CHAR, t, 0.06)
        out = prev * (1 - m) + cur * m
        d = np.abs(YY - edge) < 1.5
        out[d] = np.array(CHAMP, np.float32)
    if MODE == "matte":
        return matte_frame(t)
    out = out * VIG
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    out = out + np.repeat(np.repeat(g, 2, 0), 2, 1) * 3.2
    fade = min(clamp(t / 0.6), clamp((TOTAL - t) / 0.6))
    return np.clip(out * fade, 0, 255).astype(np.uint8)

def matte_frame(t):
    m = np.zeros((H, W), np.float32)
    for pid, (kind, prm), op in WINDOWS:
        if kind == "rect":
            x0, y0, x1, y1 = [int(v) for v in prm]
            sl = (slice(max(y0, 0), min(max(y1, 0), H)), slice(max(x0, 0), min(max(x1, 0), W)))
            m[sl] = np.maximum(m[sl], op)
        else:
            cx, cy, r = prm
            m = np.maximum(m, np.clip((r - np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)) / 1.5, 0, 1) * op)
    v = (m * 255).astype(np.uint8)
    return np.stack([v, v, v], -1)

# ------------------------------------------------------------------ footage (footage mode)
XFADE = 0.4

def footage_content(pid, t, w, h):
    """Cover-fit the active clip(s) of a window; clips overlapping in time dissolve into each other."""
    acc, wsum = None, 0.0
    for c in FOOTAGE[pid]:
        if not (c["t_in"] <= t < c["t_out"]): continue
        a = 1.0
        if t < c["t_in"] + XFADE and c["fade_in"]: a = eio((t - c["t_in"]) / XFADE)
        fr = c["mm"][min(max(int((t - c["t_in"]) * FPS), 0), len(c["mm"]) - 1)]
        src = Image.fromarray(fr)
        sc = max(w / src.width, h / src.height) * 1.04
        src = src.resize((int(src.width * sc), int(src.height * sc)), Image.BICUBIC)
        ox = int(np.clip(src.width * c["cx"] - w / 2, 0, src.width - w)); oy = (src.height - h) // 2
        img = np.asarray(src.crop((ox, oy, ox + w, oy + h)), np.float32)
        acc = img if acc is None else acc * (1 - a) + img * a
    return acc

GRADE = ("colortemperature=temperature=5900:mix=0.5,huesaturation=saturation=-0.45:colors=c+b,"
         "huesaturation=saturation=-0.08,curves=master='0/0.02 0.25/0.24 0.5/0.52 0.8/0.84 1/0.97'")

# (window, source file, src_start, speed, timeline_in, timeline_out, crop_centre_x, stabilise, fade_in)
CLIPS = [
    ("PH1", "p2_masked.mp4", 4.4, 0.5, 5.3, 8.8, 0.36, False, False),   # product box, name concealed (tracked)
    ("PH1", "1008.mp4", 121.8, 1.0, 8.4, 11.6, 0.5, True, True),        # treatment: application to forehead
    ("PH2", "ph2_3d.mp4", 0.0, 1.0, 13.0, 17.8, 0.5, False, False),     # Google Flow 3D skin clip (when supplied)
    ("PH3", "1008.mp4", 192.5, 1.0, 18.0, 23.6, 0.5, True, False),      # treatment close-up
]

def load_footage(src_dir):
    cache = os.path.join(src_dir, "_mgcache"); os.makedirs(cache, exist_ok=True)
    for i, (pid, fname, s0, sp, t_in, t_out, cx, stab, fade_in) in enumerate(CLIPS):
        src = os.path.join(src_dir, fname)
        if not os.path.exists(src): continue                      # optional clip not supplied yet
        out = os.path.join(cache, f"c{i}_{pid}_{os.path.splitext(fname)[0]}_{s0:.2f}_{sp:.2f}.rgb")
        dur = (t_out - t_in + 0.2) * sp
        if not os.path.exists(out):
            vf = ""
            if stab:
                trf = out + ".trf"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s0), "-t", str(dur), "-i", src, "-vf",
                                f"vidstabdetect=shakiness=5:result={trf}", "-f", "null", "-"], check=True)
                vf = f"vidstabtransform=input={trf}:smoothing=20:zoom=3,"
            vf += f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,unsharp=5:5:0.5,{GRADE}"
            if sp != 1.0: vf += f",setpts={1 / sp:.4f}*PTS"
            vf += f",fps={FPS}"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s0), "-t", str(dur), "-i", src, "-vf", vf,
                            "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", out], check=True)
        n = os.path.getsize(out) // (720 * 1280 * 3)
        FOOTAGE.setdefault(pid, []).append(dict(mm=np.memmap(out, np.uint8, "r", shape=(n, 1280, 720, 3)),
                                                t_in=t_in, t_out=t_out, cx=cx, fade_in=fade_in))

def write_spec(path):
    spec = {"canvas": [W, H], "fps": FPS, "duration": TOTAL,
            "scenes": {"01_OPENING": S1, "02_TREATMENT_INTRO": S2, "03_FALL_SEASON": S3,
                       "04_SKINCARE_EXPERIENCE": S4, "05_WEDDING_SEASON": S5, "06_FINAL_CTA": S6},
            "placeholders": PH_SPEC,
            "vo_placement": [{"src_in": a, "src_out": b, "timeline_in": c, "timeline_out": round(c + b - a, 2)} for a, b, c in VO]}
    # sample window geometry every 0.5 s
    geo = {}
    for n in range(int(TOTAL * 2)):
        t = n / 2; WINDOWS.clear(); render_scene(t)
        for pid, (kind, prm), op in WINDOWS:
            geo.setdefault(pid, []).append({"t": t, "shape": kind, "geom": [round(float(v), 1) for v in prm], "opacity": round(op, 3)})
    spec["window_geometry_0.5s"] = geo
    json.dump(spec, open(path, "w"), indent=1)

if __name__ == "__main__":
    if "--footage" in sys.argv:
        load_footage(sys.argv[sys.argv.index("--footage") + 1])
    if "--spec" in sys.argv:
        write_spec(sys.argv[2]); print("spec", sys.argv[2]); sys.exit()
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(frame(t)).save(f"mg_{MODE}_{t:05.2f}.jpg", quality=90)
        sys.exit()
    out = sys.argv[2]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(n / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", out)
