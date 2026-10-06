"""Brand documentary (motion graphics): Secret Closet by AshKash.  1920x1080 @30fps.

Every on-screen fact comes from public listings found by web search (Oct 2026):
site title/positioning, tagline, categories, AED pricing, +971 contact, the
"Red Mystery" product listing, and the Red-named product pages.

Usage: python doc.py out.mp4 | python doc.py --frames 3,10,...
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "fonts")

INK = (14, 11, 10)
IVORY = (243, 237, 228)
GOLD = (201, 163, 91)
CRIMSON = (158, 27, 50)
MUTED = (160, 150, 138)

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3          # ease out
def ei(p): return clamp(p) ** 3                     # ease in
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)

@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    if var: f.set_variation_by_name(var)
    return f

SERIF = lambda s, v="Regular": font("Playfair.ttf", s, v)
ITAL = lambda s, v="Italic": font("PlayfairItalic.ttf", s, v)
SANS = lambda s, v="Medium": font("Montserrat.ttf", s, v)

# ------------------------------------------------------------------ text primitives
@functools.lru_cache(maxsize=4096)
def glyph(text, fnt, color):
    l, t, r, b = fnt.getbbox(text)
    im = Image.new("RGBA", (max(1, r + 6), max(1, b + 6)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), text, font=fnt, fill=color + (255,))
    return np.asarray(im).astype(np.float32)

def blit(cv, arr, x, y, a=1.0):
    if a <= 0.004: return
    if a < 0.999:
        arr = arr.copy(); arr[..., 3] *= a
    im = Image.fromarray(arr.astype(np.uint8))
    cv.paste(im, (int(x), int(y)), im)

def width(text, fnt, sp=0):
    return sum(fnt.getlength(c) + sp for c in text) - sp if text else 0

def text(cv, s, fnt, x, y, t, t0, color=IVORY, align="left", sp=0, stagger=0.025, dur=0.6,
         rise=40, mode="rise", t_out=None):
    """Per-character animated text.  mode: rise | fade | type"""
    if t < t0 or not s: return
    tw = width(s, fnt, sp)
    cx = x - tw / 2 if align == "center" else x - tw if align == "right" else x
    out = 1.0
    if t_out is not None:
        out = 1 - eio((t - t_out) / 0.5)
        if out <= 0: return
    for i, c in enumerate(s):
        adv = fnt.getlength(c) + sp
        if c != " ":
            p = clamp((t - t0 - i * stagger) / (0.05 if mode == "type" else dur))
            if p > 0:
                dy = (1 - eo(p)) * rise if mode == "rise" else 0
                blit(cv, glyph(c, fnt, color), cx, y + dy, (p if mode != "type" else 1.0) * out)
        cx += adv

def static(cv, s, fnt, x, y, color=IVORY, a=1.0, align="left"):
    g = glyph(s, fnt, color)
    if align == "center": x -= g.shape[1] / 2
    elif align == "right": x -= g.shape[1]
    blit(cv, g, x, y, a)

def wipe_text(cv, s, fnt, x, y, t, t0, dur=0.9, color=IVORY, align="center", bar=True, a=1.0):
    """Mask-reveal (left to right) with a leading gold bar."""
    if t < t0: return
    g = glyph(s, fnt, color)
    h, w = g.shape[:2]
    if align == "center": x -= w / 2
    p = eio((t - t0) / dur)
    vis = int(w * p)
    if vis > 0:
        blit(cv, g[:, :vis], x, y, a)
    if bar and 0 < p < 1:
        d = ImageDraw.Draw(cv, "RGBA")
        d.rectangle((x + vis, y + h * 0.12, x + vis + 5, y + h * 0.95), fill=GOLD + (255,))

def para(cv, lines, fnt, x, y, t, t0, lh, color=IVORY, align="left", gap=0.18, **kw):
    for i, ln in enumerate(lines):
        text(cv, ln, fnt, x, y + i * lh, t, t0 + i * gap, color, align, **kw)

def hline(cv, x0, y, length, t, t0, dur=0.8, color=GOLD, th=2, a=1.0, center=False):
    p = eo((t - t0) / dur)
    if p <= 0: return
    d = ImageDraw.Draw(cv, "RGBA")
    L = length * p
    if center:
        d.rectangle((x0 - L / 2, y, x0 + L / 2, y + th), fill=color + (int(255 * a),))
    else:
        d.rectangle((x0, y, x0 + L, y + th), fill=color + (int(255 * a),))

# ------------------------------------------------------------------ backgrounds / textures
YY, XX = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
_r = np.sqrt(((XX - W / 8) / (W / 4 * 0.75)) ** 2 + ((YY - H / 8) / (H / 4 * 0.75)) ** 2)
VIG = np.clip(1 - 0.75 * np.clip(_r - 0.3, 0, None) ** 1.4, 0.15, 1)[..., None]

def background(t, tint=GOLD, strength=0.10):
    """Dark warm backdrop with two slow drifting light blooms (computed at 1/4 res)."""
    cx1 = W / 8 * (1 + 0.45 * math.sin(t * 0.21)); cy1 = H / 8 * (1 + 0.35 * math.cos(t * 0.17))
    cx2 = W / 8 * (1 + 0.55 * math.cos(t * 0.13 + 1)); cy2 = H / 8 * (1 + 0.4 * math.sin(t * 0.19 + 2))
    g1 = np.exp(-(((XX - cx1) / 160) ** 2 + ((YY - cy1) / 110) ** 2))[..., None]
    g2 = np.exp(-(((XX - cx2) / 200) ** 2 + ((YY - cy2) / 140) ** 2))[..., None]
    base = np.array(INK, np.float32) * 1.0
    img = base + np.array(tint, np.float32) * strength * g1 + np.array(CRIMSON, np.float32) * strength * 0.9 * g2
    img = img * VIG
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)

@functools.lru_cache(maxsize=None)
def silk(w, h, c1, c2, seed):
    """Procedural silk/satin texture (twice as wide, so it can drift)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w * 2].astype(np.float32)
    a = rng.uniform(0.004, 0.009); b = rng.uniform(0.002, 0.006)
    warp = 40 * np.sin(yy * b + rng.uniform(0, 6)) + 25 * np.sin(xx * 0.003 + yy * 0.004)
    v = 0.5 + 0.5 * np.sin((xx + warp) * a + 0.6 * np.sin(yy * 0.01))
    v = v ** 2.2
    sheen = np.clip(np.sin((xx * 0.7 + yy) * 0.006) * 1.4 - 0.4, 0, 1) ** 3
    c1 = np.array(c1, np.float32); c2 = np.array(c2, np.float32)
    img = c1 * (1 - v[..., None]) + c2 * v[..., None] + 90 * sheen[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")

def silk_panel(cv, x, y, w, h, c1, c2, seed, t, a=1.0, radius=18):
    tex = silk(w, h, c1, c2, seed)
    off = int((t * 30) % w)
    panel = tex.crop((off, 0, off + w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=int(255 * a))
    cv.paste(panel, (int(x), int(y)), mask)

GRAIN = [np.random.default_rng(i).normal(0, 5, (H // 2, W // 2, 1)).astype(np.float32) for i in range(5)]

# ------------------------------------------------------------------ particles (gold dust)
_rng = np.random.default_rng(11)
DUST = [(_rng.uniform(0, W), _rng.uniform(0, H), _rng.uniform(8, 35), _rng.uniform(1, 3.2), _rng.uniform(0, 6.3))
        for _ in range(70)]

def dust(cv, t, a=1.0):
    d = ImageDraw.Draw(cv, "RGBA")
    for x, y, v, r, ph in DUST:
        yy = (y - v * t) % H; xx = (x + 15 * math.sin(t * 0.5 + ph)) % W
        al = int(255 * a * (0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * 2 + ph))))
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=GOLD + (al,))

# ------------------------------------------------------------------ common chrome
def chrome(cv, t, chapter=None):
    d = ImageDraw.Draw(cv, "RGBA")
    f = SANS(20, "SemiBold")
    static(cv, "SECRET CLOSET  ·  A BRAND DOCUMENTARY", f, 80, 56, MUTED, 0.85)
    if chapter:
        static(cv, chapter, f, W - 80, 56, GOLD, 0.95, align="right")
    d.rectangle((80, H - 70, W - 80, H - 69), fill=(255, 255, 255, 40))
    d.rectangle((80, H - 71, 80 + (W - 160) * clamp(t / TOTAL), H - 68), fill=GOLD + (255,))

def chapter_card(cv, lt, num, title, sub):
    """Big outlined numeral + chapter title (first ~2.4s of each chapter)."""
    if lt > 2.6: return
    out = 1 - eio((lt - 2.1) / 0.5)
    big = SERIF(420, "Bold")
    g = glyph(num, big, GOLD)
    a = eo(lt / 0.8) * out * 0.12
    blit(cv, g, W / 2 - g.shape[1] / 2, 250 - (1 - eo(lt / 1.2)) * 60, a)
    text(cv, "CHAPTER " + num, SANS(26, "SemiBold"), W / 2, 420, lt, 0.2, GOLD, "center", sp=8,
         stagger=0.03, mode="fade", t_out=2.1)
    wipe_text(cv, title, SERIF(110, "Regular"), W / 2, 470, lt, 0.4, 0.9, a=out)
    text(cv, sub, ITAL(36), W / 2, 640, lt, 0.9, MUTED, "center", stagger=0.012, mode="fade", t_out=2.1)
    hline(cv, W / 2, 620, 340, lt, 0.6, center=True, a=out)

# ------------------------------------------------------------------ scenes
def s_open(cv, t):
    dust(cv, t, clamp(t / 2))
    para(cv, ["In a city that dresses the world,"], ITAL(54), W / 2, 380, t, 0.6, 70, IVORY, "center",
         stagger=0.03, mode="fade", t_out=3.6)
    para(cv, ["one closet keeps its pieces close."], ITAL(54), W / 2, 460, t, 1.6, 70, MUTED, "center",
         stagger=0.03, mode="fade", t_out=3.6)
    if t > 4.0:
        lt = t - 4.0
        text(cv, "SECRET  CLOSET", SERIF(150, "Regular"), W / 2, 330, lt, 0.0, IVORY, "center", sp=14,
             stagger=0.06, dur=0.9, rise=60)
        hline(cv, W / 2, 545, 520, lt, 0.9, center=True)
        text(cv, "by AshKash", ITAL(64), W / 2, 570, lt, 1.2, GOLD, "center", stagger=0.05, mode="fade")
        text(cv, "A  BRAND  DOCUMENTARY", SANS(26, "SemiBold"), W / 2, 700, lt, 1.9, MUTED, "center", sp=10,
             stagger=0.02, mode="fade")

def s_brand(cv, t):
    chrome(cv, T0["brand"] + t, "01 · THE BRAND")
    chapter_card(cv, t, "01", "The Brand", "who they are")
    lt = t - 2.6
    if lt < 0: return
    text(cv, "WHAT THEY SAY ABOUT THEMSELVES", SANS(24, "SemiBold"), 160, 200, lt, 0, GOLD, sp=6,
         stagger=0.01, mode="fade")
    para(cv, ["A premium women's fashion boutique"], SERIF(76), 160, 250, lt, 0.2, 90, IVORY, stagger=0.02)
    pillars = [("I", "Elevated", "ready-to-wear"), ("II", "Luxury", "pieces"), ("III", "Considered", "essentials")]
    for i, (n, a1, a2) in enumerate(pillars):
        x = 160 + i * 540; y = 420
        p = eo((lt - 1.0 - i * 0.25) / 0.7)
        if p <= 0: continue
        d = ImageDraw.Draw(cv, "RGBA")
        d.rounded_rectangle((x, y + (1 - p) * 40, x + 480, y + 230 + (1 - p) * 40), radius=14,
                            outline=GOLD + (int(150 * p),), width=2, fill=(255, 255, 255, int(10 * p)))
        static(cv, n, SERIF(34, "Bold"), x + 36, y + 28 + (1 - p) * 40, GOLD, p)
        static(cv, a1, SERIF(58), x + 36, y + 80 + (1 - p) * 40, IVORY, p)
        static(cv, a2, ITAL(40), x + 36, y + 152 + (1 - p) * 40, MUTED, p)
    # tagline
    if lt > 3.4:
        q = lt - 3.4
        static(cv, "“", SERIF(160, "Bold"), 140, 690, CRIMSON, eo(q / 0.5))
        para(cv, ["Symbol of quality defined by timeless", "affordability, elegance and glamour."], ITAL(52),
             240, 730, q, 0.1, 70, IVORY, stagger=0.015, mode="fade")
        text(cv, "— brand tagline", SANS(24, "Medium"), 240, 890, q, 1.4, MUTED, mode="fade")

def s_where(cv, t):
    chrome(cv, T0["where"] + t, "02 · WHERE")
    chapter_card(cv, t, "02", "Where It Lives", "following the clues")
    lt = t - 2.6
    if lt < 0: return
    d = ImageDraw.Draw(cv, "RGBA")
    # two nodes + dotted arc
    A, B = (520, 640), (1400, 640)
    for i, (pt, label, sub) in enumerate([(A, "SOUTH ASIAN CRAFT", "kaftans · sharara · dupatta · pret"),
                                           (B, "UAE BOUTIQUE", "prices in AED · +971 contact")]):
        p = eo((lt - 0.2 - i * 1.6) / 0.6)
        if p <= 0: continue
        r = 16 * p
        pulse = (lt * 0.8 + i * 0.5) % 1
        d.ellipse((pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r), fill=(GOLD if i else CRIMSON) + (255,))
        rr = 16 + 50 * pulse
        d.ellipse((pt[0] - rr, pt[1] - rr, pt[0] + rr, pt[1] + rr), outline=GOLD + (int(160 * (1 - pulse) * p),), width=2)
        text(cv, label, SANS(30, "Bold"), pt[0], pt[1] + 50, lt, 0.3 + i * 1.6, IVORY, "center", sp=5,
             stagger=0.015, mode="fade")
        text(cv, sub, ITAL(32), pt[0], pt[1] + 100, lt, 0.6 + i * 1.6, MUTED, "center", stagger=0.01, mode="fade")
    q = eio((lt - 0.8) / 1.2)
    n = 60
    for k in range(int(n * q)):
        u = k / n
        x = A[0] + (B[0] - A[0]) * u
        y = A[1] - math.sin(math.pi * u) * 230
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=GOLD + (200,))
    text(cv, "The clues on the store point one way:", SERIF(56), W / 2, 190, lt, 0.0, IVORY, "center",
         stagger=0.015, mode="fade")
    text(cv, "a UAE-based boutique, built on South Asian occasion wear.", ITAL(44), W / 2, 270, lt, 3.4, GOLD,
         "center", stagger=0.012, mode="fade")

CATS = [("Kaftans", "flowing, statement silhouettes", ((60, 20, 25), (170, 60, 70)), 1),
        ("Luxe Pret", "luxury ready-to-wear", ((25, 22, 40), (120, 100, 160)), 2),
        ("Festive Pret", "for occasions & celebrations", ((50, 30, 10), (205, 160, 80)), 3),
        ("Basic Pret", "Korean georgettes & silks", ((30, 35, 35), (170, 180, 175)), 4),
        ("Wraps & Shawls", "the finishing layer", ((40, 15, 30), (150, 70, 110)), 5)]

def s_collections(cv, t):
    chrome(cv, T0["coll"] + t, "03 · THE COLLECTIONS")
    chapter_card(cv, t, "03", "The Collections", "five ways to dress")
    lt = t - 2.6
    if lt < 0: return
    text(cv, "FIVE CATEGORIES ON THE STORE", SANS(24, "SemiBold"), W / 2, 170, lt, 0, GOLD, "center", sp=6,
         stagger=0.01, mode="fade")
    cw, ch, gap = 312, 520, 26
    x0 = (W - (5 * cw + 4 * gap)) / 2
    for i, (name, sub, (c1, c2), seed) in enumerate(CATS):
        p = eo((lt - 0.3 - i * 0.22) / 0.8)
        if p <= 0: continue
        x = x0 + i * (cw + gap); y = 250 + (1 - p) * 80
        silk_panel(cv, x, y, cw, ch, c1, c2, seed, lt + i, a=p)
        # bottom shade for legibility
        sh = Image.new("RGBA", (cw, 220), (0, 0, 0, 0))
        sh.putalpha(Image.linear_gradient("L").resize((cw, 220)).point(lambda v: int(v * 0.8 * p)))
        cv.paste(sh, (int(x), int(y + ch - 220)), sh)
        static(cv, f"0{i + 1}", SANS(22, "Bold"), x + 26, y + 24, IVORY, p * 0.9)
        static(cv, name, SERIF(44 if width(name, SERIF(44)) < cw - 44 else 38), x + 26, y + ch - 140, IVORY, p)
        static(cv, sub, ITAL(24), x + 26, y + ch - 76, (225, 215, 200), p)
    text(cv, "Ordering is personal: pieces can be requested through direct consultation.", ITAL(36), W / 2, 820,
         lt, 2.6, MUTED, "center", stagger=0.01, mode="fade")

def s_spotlight(cv, t):
    chrome(cv, T0["spot"] + t, "04 · SPOTLIGHT")
    chapter_card(cv, t, "04", "The Red Edit", "one colour, many stories")
    lt = t - 2.6
    if lt < 0: return
    # left: silk panel w/ product name
    p = eo(lt / 0.8)
    silk_panel(cv, 140, 170 + (1 - p) * 60, 640, 760, (70, 8, 18), (190, 35, 55), 9, lt, a=p, radius=22)
    sh = Image.new("RGBA", (640, 300), (0, 0, 0, 0))
    sh.putalpha(Image.linear_gradient("L").resize((640, 300)).point(lambda v: int(v * 0.85 * p)))
    cv.paste(sh, (140, int(630 + (1 - p) * 60)), sh)
    text(cv, "FEATURED LISTING", SANS(22, "Bold"), 180, 760, lt, 0.5, GOLD, sp=6, stagger=0.01, mode="fade")
    text(cv, "Red Mystery", SERIF(84), 180, 800, lt, 0.6, IVORY, stagger=0.04)
    # right: specs + price
    x = 880
    text(cv, "WHAT'S IN THE SET", SANS(24, "SemiBold"), x, 190, lt, 0.8, GOLD, sp=6, stagger=0.01, mode="fade")
    items = ["Heavy embroidered, hand-embellished shirt", "Sharara pants",
             "Heavy dupatta, all four borders covered", "Size: S – M"]
    for i, it in enumerate(items):
        q = eo((lt - 1.1 - i * 0.3) / 0.5)
        if q > 0:
            ImageDraw.Draw(cv, "RGBA").rectangle((x, 268 + i * 72, x + 10, 278 + i * 72), fill=CRIMSON + (int(255 * q),))
        text(cv, it, SERIF(40), x + 34, 245 + i * 72, lt, 1.1 + i * 0.3, IVORY, stagger=0.008, mode="fade")
    # price counter
    if lt > 2.6:
        q = lt - 2.6
        text(cv, "LISTED PRICE", SANS(24, "SemiBold"), x, 570, q, 0, GOLD, sp=6, stagger=0.01, mode="fade")
        static(cv, "AED 1,350", SERIF(54), x, 615, MUTED, eo(q / 0.4))
        k = eo((q - 0.4) / 0.4)
        if k > 0:
            ImageDraw.Draw(cv, "RGBA").rectangle((x - 6, 652, x - 6 + 280 * k, 656), fill=CRIMSON + (255,))
        val = int(1350 - 150 * eio((q - 0.7) / 1.0))
        if q > 0.7:
            static(cv, f"AED {val:,}", SERIF(110, "Bold"), x, 680, IVORY, eo((q - 0.7) / 0.3))
        if q > 1.8:
            r = eo((q - 1.8) / 0.4)
            d = ImageDraw.Draw(cv, "RGBA")
            d.rounded_rectangle((x + 520, 715, x + 520 + 170 * r, 785), radius=35, fill=CRIMSON + (255,))
            if r > 0.9: static(cv, "-11%", SANS(36, "Bold"), x + 548, 728, IVORY)
    if lt > 5.6:
        q = lt - 5.6
        text(cv, "Its siblings on the store:", ITAL(34), x, 880, q, 0, MUTED, stagger=0.01, mode="fade")
        names = ["Red Bloom", "Red Blossom", "Red Lilies"]
        cx = x
        for i, n in enumerate(names):
            text(cv, n, SERIF(42), cx, 930, q, 0.4 + i * 0.35, GOLD if i % 2 == 0 else IVORY, stagger=0.02)
            cx += width(n, SERIF(42)) + 60

def s_digital(cv, t):
    chrome(cv, T0["dig"] + t, "05 · DIGITAL")
    chapter_card(cv, t, "05", "The Digital Closet", "where customers meet the brand")
    lt = t - 2.6
    if lt < 0: return
    chans = [("WEBSITE", "ash-kash.com", "catalogue · prices in AED · product pages"),
             ("INSTAGRAM", "@secretclosetbyashkash", "the visual storefront"),
             ("FACEBOOK", "Secret Closet By Ashkash", "community page"),
             ("DIRECT", "consultation ordering", "personal, one-to-one service")]
    for i, (k, v, s) in enumerate(chans):
        p = eo((lt - 0.2 - i * 0.35) / 0.7)
        if p <= 0: continue
        y = 200 + i * 175
        x = 220 + (1 - p) * -60
        d = ImageDraw.Draw(cv, "RGBA")
        d.rounded_rectangle((x, y, x + 1480, y + 140), radius=16, fill=(255, 255, 255, int(12 * p)),
                            outline=(255, 255, 255, int(40 * p)), width=1)
        d.rectangle((x, y, x + 6, y + 140), fill=GOLD + (int(255 * p),))
        static(cv, k, SANS(22, "Bold"), x + 50, y + 28, GOLD, p)
        static(cv, v, SERIF(52), x + 50, y + 58, IVORY, p)
        static(cv, s, ITAL(30), x + 1440, y + 70, MUTED, p, align="right")

def s_analysis(cv, t):
    chrome(cv, T0["ana"] + t, "06 · ANALYSIS")
    chapter_card(cv, t, "06", "The Verdict", "strengths & what's next")
    lt = t - 2.6
    if lt < 0: return
    cols = [("STRENGTHS", GOLD, ["Clear premium positioning", "Hand-embellished festive pieces",
                                  "A signature colour story: the Red Edit", "Personal, consultation-led service"]),
            ("OPPORTUNITIES", CRIMSON, ["Widen sizing beyond S – M", "Plan drops around Eid & wedding season",
                                        "Reels of embroidery close-ups", "One name everywhere: 'Ash & Kash' vs 'Secret Closet'"])]
    for c, (head, col, items) in enumerate(cols):
        x = 160 + c * 820
        text(cv, head, SANS(30, "Bold"), x, 190, lt, 0.2 + c * 0.4, col, sp=8, stagger=0.02, mode="fade")
        hline(cv, x, 240, 700, lt, 0.3 + c * 0.4, color=col)
        for i, it in enumerate(items):
            t0 = 0.8 + c * 2.4 + i * 0.45
            q = eo((lt - t0) / 0.4)
            if q > 0:
                d = ImageDraw.Draw(cv, "RGBA")
                d.ellipse((x, 300 + i * 120, x + 44, 344 + i * 120), outline=col + (int(255 * q),), width=2)
                static(cv, "+" if c == 0 else "→", SANS(24, "Bold"), x + 22, 306 + i * 120, col, q, align="center")
            words = it if width(it, SERIF(40)) < 680 else it
            fs = SERIF(40) if width(it, SERIF(40)) < 690 else SERIF(32)
            text(cv, words, fs, x + 70, 298 + i * 120, lt, t0, IVORY, stagger=0.006, mode="fade")

def s_outro(cv, t):
    dust(cv, t)
    for i, w_ in enumerate(["Timeless.", "Affordable.", "Glamorous."]):
        text(cv, w_, ITAL(70), W / 2 - 520 + i * 520, 250, t, 0.3 + i * 0.5, GOLD if i == 1 else IVORY, "center",
             stagger=0.03, mode="fade", t_out=3.4)
    if t > 3.6:
        lt = t - 3.6
        text(cv, "SECRET  CLOSET", SERIF(130), W / 2, 330, lt, 0, IVORY, "center", sp=12, stagger=0.05, dur=0.9)
        hline(cv, W / 2, 520, 460, lt, 0.8, center=True)
        text(cv, "by AshKash", ITAL(56), W / 2, 540, lt, 1.0, GOLD, "center", stagger=0.04, mode="fade")
        text(cv, "ash-kash.com    ·    @secretclosetbyashkash", SANS(30, "Medium"), W / 2, 680, lt, 1.6, IVORY,
             "center", sp=2, stagger=0.01, mode="fade")
        text(cv, "Independent profile based on publicly available information, October 2026.", ITAL(24), W / 2,
             900, lt, 2.4, MUTED, "center", stagger=0.004, mode="fade")

SCENES = [("open", 9.0, s_open), ("brand", 13.0, s_brand), ("where", 11.0, s_where),
          ("coll", 12.0, s_collections), ("spot", 14.0, s_spotlight), ("dig", 10.0, s_digital),
          ("ana", 15.0, s_analysis), ("outro", 9.0, s_outro)]
T0 = {}
_acc = 0.0
for name, dur, _ in SCENES:
    T0[name] = _acc; _acc += dur
TOTAL = _acc
XF = 0.6  # cross-fade between scenes

def render_scene(i, t):
    name, dur, fn = SCENES[i]
    lt = t - T0[name]
    cv = background(t, GOLD if name != "spot" else CRIMSON, 0.10 if name != "spot" else 0.16)
    fn(cv, lt)
    return cv

def compose(t):
    idx = max(i for i, (n, d, f) in enumerate(SCENES) if T0[n] <= t + 1e-9)
    name, dur, _ = SCENES[idx]
    img = render_scene(idx, t)
    # fade out scene end into next (cross dissolve + gold flash line)
    end = T0[name] + dur
    if idx + 1 < len(SCENES) and t > end - XF:
        p = eio((t - (end - XF)) / XF)
        nxt = render_scene(idx + 1, end + 0.0)
        img = Image.blend(img, nxt, p)
        d = ImageDraw.Draw(img, "RGBA")
        x = W * p
        d.rectangle((x - 2, 0, x + 2, H), fill=GOLD + (int(200 * math.sin(math.pi * p)),))
    arr = np.asarray(img.convert("RGB"), np.float32)
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    arr = arr + np.repeat(np.repeat(g, 2, 0), 2, 1)
    # global fade in/out
    k = min(clamp(t / 1.0), clamp((TOTAL - t) / 1.2))
    arr *= k
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def render_range(args):
    i0, i1, path = args
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        enc.stdin.write(compose(i / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    return path

if __name__ == "__main__":
    if "--frames" in sys.argv:
        for tt in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            compose(tt).save(f"doc_{tt:05.1f}.jpg", quality=88)
        sys.exit()
    out = sys.argv[1] if len(sys.argv) > 1 else "doc_video.mp4"
    import multiprocessing as mp
    N = int(TOTAL * FPS); n = 4
    b = np.linspace(0, N, n + 1).astype(int)
    jobs = [(b[k], b[k + 1], f"docpart{k}.mp4") for k in range(n)]
    with mp.get_context("fork").Pool(n) as pool:
        parts = pool.map(render_range, jobs)
    with open("docparts.txt", "w") as fh:
        fh.writelines(f"file '{p}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "docparts.txt", "-c", "copy", out],
                   check=True)
    print("done", out, TOTAL)
