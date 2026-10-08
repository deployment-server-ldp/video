"""SKN Theory — Whimsical Glow Peel launch reel (1080x1920 @30fps, 36 s).

Real-footage edit: every shot is client footage (the packaging clip arrives pre-masked by
conceal.py). Editorial typography, motivated transitions and a typographic end card are added
here. Slots where the brief calls for AI shots are documented in PRODUCTION_PACKAGE.md.

Usage: python skn_reel.py SRC_DIR out.mp4 [--notext] [--frames t1,t2,...]
  SRC_DIR holds 1008.mp4, p4.mp4 (SDR) and p2_masked.mp4 (SDR, 60 fps, masked).
"""
import functools, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
TOTAL = 36.0
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
CACHE = os.environ.get("CACHE", "skn_cache")
TEXT = "--notext" not in sys.argv

IVORY = (251, 246, 238); CHAMPAGNE = (200, 174, 138); ROSE = (190, 140, 128); TAUPE = (94, 78, 69)
GRADE = ("colortemperature=temperature=5900:mix=0.5,huesaturation=saturation=-0.45:colors=c+b,"
         "huesaturation=saturation=-0.08,curves=master='0/0.02 0.25/0.24 0.5/0.52 0.8/0.84 1/0.97'")

# (start, dur, source, src_start, speed, zoom_from, zoom_to)
SHOTS = [
    (0.0, 4.0, "p4.mp4", 0.0, 0.85, 1.00, 1.07),         # hook: whimsical gem mask
    (4.0, 3.5, "p2_masked.mp4", 0.4, 0.5, 1.02, 1.08),   # packaging push-in (names concealed)
    (7.5, 2.5, "1008.mp4", 72.0, 1.0, 1.04, 1.08),       # prep: cleansing
    (10.0, 3.0, "1008.mp4", 112.5, 1.0, 1.06, 1.10),     # brush into the bowl
    (13.0, 3.0, "1008.mp4", 121.8, 1.0, 1.04, 1.10),     # application, forehead
    (16.0, 2.5, "1008.mp4", 129.0, 1.0, 1.08, 1.12),     # application, cheek
    (18.5, 2.5, "1008.mp4", 192.5, 1.0, 1.06, 1.12),     # close application
    (21.0, 2.5, "1008.mp4", 204.5, 1.0, 1.10, 1.06),     # application detail
    (23.5, 3.5, "p2_masked.mp4", 4.4, 0.5, 1.04, 1.10),  # gem detail, slow-mo
]
END_T = 27.0   # typographic end card takes over (masked reveal)
TAIL = 0.7

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eo(p): return 1 - (1 - clamp(p)) ** 3
def eio(p): p = clamp(p); return p * p * (3 - 2 * p)

# ------------------------------------------------------------------ shot preparation
def shot_file(i):
    st, du, src, s0, sp, *_ = SHOTS[i]
    return os.path.join(CACHE, f"s{i:02d}_{os.path.splitext(src)[0]}_{s0:.2f}_{sp:.2f}.rgb")

def prepare(src_dir):
    os.makedirs(CACHE, exist_ok=True)
    jobs = []
    for i, (st, du, src, s0, sp, *_ ) in enumerate(SHOTS):
        out = shot_file(i)
        if os.path.exists(out): continue
        length = (du + TAIL) * sp
        path = os.path.join(src_dir, src)
        if src == "1008.mp4":   # handheld 480p: stabilise, then careful upscale
            trf = out + ".trf"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0}", "-t", f"{length}", "-i", path,
                            "-vf", f"vidstabdetect=shakiness=5:accuracy=15:result={trf}", "-f", "null", "-"], check=True)
            vf = (f"vidstabtransform=input={trf}:smoothing=20:zoom=3:interpol=bicubic,"
                  f"scale={W}:{H}:flags=lanczos,hqdn3d=1.2:1.2:2:2,unsharp=5:5:0.55,{GRADE}")
        else:
            vf = f"scale={W}:{H}:flags=lanczos,{GRADE}"
        if sp != 1.0:
            vf += f",setpts={1 / sp:.4f}*PTS"
        vf += f",fps={FPS}"
        jobs.append(subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0}", "-t", f"{length}", "-i", path,
                                      "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", out]))
        if len(jobs) >= 3: jobs.pop(0).wait()
    for j in jobs: j.wait()
    mm = []
    for i in range(len(SHOTS)):
        p = shot_file(i)
        mm.append(np.memmap(p, np.uint8, "r", shape=(os.path.getsize(p) // (W * H * 3), H, W, 3)))
    return mm

# ------------------------------------------------------------------ look helpers
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((XX - W / 2) / (W * 0.75)) ** 2 + ((YY - H / 2) / (H * 0.7)) ** 2)
VIG = np.clip(1 - 0.16 * np.clip(_r - 0.55, 0, None) ** 1.4, 0.82, 1)[..., None].astype(np.float32)
GRAIN = [np.random.default_rng(i).normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32) for i in range(6)]
TOP_SHADE = (np.clip(1 - YY / 950, 0, 1) ** 1.5 * 0.5)[..., None].astype(np.float32)
BOT_SHADE = (np.clip((YY - 1000) / 620, 0, 1) ** 1.4 * 0.5)[..., None].astype(np.float32)

def warm_light(p, cx_from=1.25, cx_to=-0.25, strength=0.55):
    """Champagne light passing across the frame (screen blend layer)."""
    cx = W * (cx_from + (cx_to - cx_from) * p)
    g = np.exp(-(((XX - cx) / (W * 0.55)) ** 2 + ((YY - H * 0.35) / (H * 0.6)) ** 2))
    return np.stack([g * 255, g * 214, g * 168], -1) * strength

def soft_blur(arr, r):
    if r < 0.5: return arr
    return np.asarray(Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)

def shot(mm, i, t):
    st, du, src, s0, sp, z0, z1 = SHOTS[i]
    arr = mm[i][min(max(int((t - st) * FPS), 0), len(mm[i]) - 1)]
    z = z0 + (z1 - z0) * eio((t - st) / du)
    cw, ch = W / z, H / z
    return np.asarray(Image.fromarray(arr).resize((W, H), Image.BICUBIC,
                      box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)), np.float32)

# ------------------------------------------------------------------ typography
@functools.lru_cache(maxsize=None)
def font(name, size, var=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if var: f.set_variation_by_name(var)
    return f
SERIF = lambda s, v="Medium": font("Cormorant.ttf", s, v)
ITAL = lambda s, v="Medium Italic": font("CormorantItalic.ttf", s, v)
SANS = lambda s, v="Medium": font("Manrope.ttf", s, v)

@functools.lru_cache(maxsize=512)
def word_img(s, fnt, color, tracking):
    w = int(sum(fnt.getlength(c) + tracking for c in s) - tracking) + 12
    asc, desc = fnt.getmetrics()
    im = Image.new("RGBA", (max(w, 2), asc + desc + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 0
    for c in s:
        d.text((x, 0), c, font=fnt, fill=color + (255,)); x += fnt.getlength(c) + tracking
    return im

def reveal(layer, s, fnt, cx, y, lt, t0, color, tracking=0, dur=0.7, t_out=None, track_from=None):
    """Masked rise: the line slides up from behind an invisible baseline mask.
    track_from: optional starting tracking for a subtle tracking expansion."""
    if lt < t0: return
    p = eo((lt - t0) / dur)
    trk = tracking if track_from is None else track_from + (tracking - track_from) * eo((lt - t0) / (dur * 1.6))
    im = word_img(s, fnt, color, round(trk, 1))
    a = 1.0
    if t_out is not None and lt > t_out:
        q = eio((lt - t_out) / 0.45); a = 1 - q
        p = p  # exit is a gentle fade + lift
        y -= 14 * q
    if a <= 0: return
    h = im.height
    off = int((1 - p) * h * 0.9)
    vis = im.crop((0, 0, im.width, h - off)) if off < h else None
    if vis is None: return
    if a < 1:
        al = vis.getchannel("A").point(lambda v: int(v * a)); vis = vis.copy(); vis.putalpha(al)
    layer.alpha_composite(vis, (int(cx - im.width / 2), int(y + off)))

def rule(layer, cx, y, length, lt, t0, color, dur=0.8, t_out=None, th=2):
    p = eo((lt - t0) / dur)
    if t_out is not None: p *= 1 - eio((lt - t_out) / 0.45)
    if p <= 0: return
    d = ImageDraw.Draw(layer); L = length * p / 2
    d.rectangle((cx - L, y, cx + L, y + th), fill=color + (230,))

def composite_text(base, layer, shadow=0.45, halo=False):
    bb = layer.getbbox()
    if not bb: return base
    a = layer.getchannel("A").filter(ImageFilter.GaussianBlur(14 if halo else 10))
    tint = (255, 252, 246, 0) if halo else (40, 28, 22, 0)
    sh = Image.new("RGBA", (W, H), tint); sh.putalpha(a.point(lambda v: int(min(255, v * shadow))))
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    out.alpha_composite(sh, (0, 3)); out.alpha_composite(layer)
    return np.asarray(out.convert("RGB"), np.float32)

def footage_text(t):
    """Returns (light_layer, dark_layer): ivory type over mid-tone footage, taupe over the white tabletop."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); D = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cx = W / 2
    # S1 hook (ivory over the mask close-up)
    reveal(L, "FALL INTO", SERIF(118), cx, 270, t, 0.45, IVORY, 14, t_out=3.5, track_from=4)
    reveal(L, "your glow", ITAL(150), cx, 385, t, 0.85, IVORY, 2, t_out=3.5)
    rule(L, cx, 585, 240, t, 1.3, CHAMPAGNE, t_out=3.5)
    # S2 introducing (taupe over the white tabletop)
    reveal(D, "INTRODUCING", SANS(34, "Bold"), cx, 560, t, 4.35, ROSE, 14, t_out=7.05, track_from=6)
    reveal(D, "Whimsical", ITAL(158), cx, 608, t, 4.75, TAUPE, 1, t_out=7.05)
    reveal(D, "GLOW PEEL", SERIF(112, "SemiBold"), cx, 780, t, 5.05, TAUPE, 18, t_out=7.05, track_from=8)
    rule(D, cx, 930, 200, t, 5.5, CHAMPAGNE, t_out=7.05)
    # S2b lower third
    reveal(L, "NEWLY INTRODUCED AT", SANS(30, "Bold"), cx, 1245, t, 7.8, IVORY, 9, t_out=9.6)
    reveal(L, "SKN THEORY", SERIF(82, "SemiBold"), cx, 1290, t, 8.05, IVORY, 16, t_out=9.6)
    # S3 season
    reveal(L, "NEW SEASON.", SERIF(108, "SemiBold"), cx, 280, t, 10.35, IVORY, 10, t_out=15.4)
    reveal(L, "fresh glow.", ITAL(134), cx, 392, t, 10.85, IVORY, 2, t_out=15.4)
    rule(L, cx, 570, 220, t, 11.3, CHAMPAGNE, t_out=15.4)
    # S4 treatment experience lower third
    rule(L, cx, 1205, 130, t, 16.3, CHAMPAGNE, t_out=22.6)
    reveal(L, "YOUR SEASONAL", SANS(34, "Bold"), cx, 1230, t, 16.45, IVORY, 12, t_out=22.6, track_from=5)
    reveal(L, "skin reset", ITAL(132), cx, 1272, t, 16.8, IVORY, 2, t_out=22.6)
    # S5 wedding (taupe over the white tabletop)
    reveal(D, "WEDDING SEASON", SERIF(100, "SemiBold"), cx, 280, t, 23.85, TAUPE, 9, t_out=26.6)
    reveal(D, "is coming", ITAL(132), cx, 380, t, 24.3, ROSE, 2, t_out=26.6)
    return L, D

# ------------------------------------------------------------------ end card
ENDBG = None
def end_background(lt):
    """Warm cream with a slow champagne light drift and faint paper grain."""
    global ENDBG
    if ENDBG is None:
        v = YY / H
        base = np.stack([250 - 6 * v, 244 - 10 * v, 236 - 12 * v], -1)
        ENDBG = base.astype(np.float32)
    cx = W * (0.3 + 0.4 * math.sin(lt * 0.35)); cy = H * (0.38 + 0.05 * math.cos(lt * 0.3))
    g = np.exp(-(((XX - cx) / (W * 0.7)) ** 2 + ((YY - cy) / (H * 0.35)) ** 2))[..., None]
    return ENDBG * (1 - 0.06 * g) + np.array([255, 236, 214], np.float32) * 0.06 * g + 3 * g

def end_text(lt):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); cx = W / 2
    reveal(L, "WEDDING SEASON IS COMING", SANS(32, "Bold"), cx, 430, lt, 0.35, ROSE, 8, track_from=3)
    reveal(L, "Get glow-ready", ITAL(104), cx, 478, lt, 0.7, TAUPE, 1)
    rule(L, cx, 640, 100, lt, 1.2, CHAMPAGNE)
    reveal(L, "Whimsical", ITAL(176), cx, 670, lt, 1.5, TAUPE, 1)
    reveal(L, "GLOW PEEL", SERIF(126, "SemiBold"), cx, 862, lt, 1.85, TAUPE, 22, track_from=10)
    reveal(L, "YOUR GLOW SEASON STARTS HERE", SANS(32, "SemiBold"), cx, 1035, lt, 2.6, TAUPE, 6)
    reveal(L, "DISCOVER IT AT", SANS(28, "Bold"), cx, 1145, lt, 3.3, ROSE, 10)
    reveal(L, "SKN THEORY", SERIF(96, "SemiBold"), cx, 1185, lt, 3.55, TAUPE, 22, track_from=12)
    p = eo((lt - 4.5) / 0.7)
    if p > 0:
        d = ImageDraw.Draw(L)
        w2, h2, y = 340 * p, 54, 1395
        d.rounded_rectangle((cx - w2, y - h2, cx + w2, y + h2), radius=54, outline=TAUPE + (int(235 * p),), width=3)
    reveal(L, "BOOK YOUR CONSULTATION", SANS(32, "Bold"), cx, 1374, lt, 4.85, TAUPE, 6)
    return L

# ------------------------------------------------------------------ frame assembly
def frame(mm, t):
    if t >= END_T + 0.85:
        lt = t - END_T
        out = end_background(lt)
        if TEXT: out = composite_text(out, end_text(lt), shadow=0.0)
    else:
        i = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-9)
        out = shot(mm, i, t)
        st = SHOTS[i][0]; lt = t - st
        # motivated transitions into shot i
        if abs(t - 4.0) < 0.45:                                   # light-matched: warm bloom through the cut
            p = (t - 3.55) / 0.9
            if t < 4.0: out = shot(mm, 0, t)
            else:
                a = eio(lt / 0.3); out = shot(mm, 0, t) * (1 - a) + out * a
            k = math.sin(math.pi * clamp(p))
            out = 255 - (255 - out) * (1 - k * 0.55)
        if st == 7.5 and lt < 0.32:                               # follow the push-in: soft vertical whip
            p = eio(lt / 0.32)
            off = int(H * p)
            a = shot(mm, 1, t)
            out = np.concatenate([a[off:], out[:off]], 0)        # previous moves up, next enters from below
            out = soft_blur(out, 18 * math.sin(math.pi * p))
        if 16.0 - 0.4 < t < 16.0 + 0.5:                          # champagne light sweep (fall light)
            p = (t - 15.6) / 0.9
            out = 255 - (255 - out) * (1 - warm_light(p) / 255)
        if st == 23.5 and lt < 0.6:                               # defocus dissolve into gem texture
            a = eio(lt / 0.6)
            prev = soft_blur(shot(mm, 7, t), 14 * a)
            cur = soft_blur(out, 14 * (1 - a))
            out = prev * (1 - a) + cur * a
        # legibility shading only while text is up
        if TEXT:
            if any(a <= t <= b for a, b in ((0.3, 3.9), (10.2, 15.8))):
                out = out * (1 - TOP_SHADE)
            if any(a <= t <= b for a, b in ((7.7, 10.0), (16.2, 23.0))):
                out = out * (1 - BOT_SHADE)
        out = out * VIG
        if TEXT:
            light, dark = footage_text(t)
            out = composite_text(out, light, 0.55)
            out = composite_text(out, dark, 0.9, halo=True)
        # end-card masked reveal: cream panel rises with a soft curved edge
        if END_T <= t < END_T + 0.85:
            lt = t - END_T
            p = eio(lt / 0.85)
            edge = H * (1 - p) + 140 * np.sin(XX / W * math.pi) * (1 - p)
            m = np.clip((YY - edge + 60) / 120, 0, 1)[..., None]
            bg = end_background(lt)
            if TEXT: bg = composite_text(bg, end_text(lt), shadow=0.0)
            out = out * (1 - m) + bg * m
    g = GRAIN[int(t * FPS) % len(GRAIN)]
    out = out + np.repeat(np.repeat(g, 2, 0), 2, 1)
    out = out * clamp(t / 0.35) if t < 0.35 else out
    return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    mm = prepare(sys.argv[1])
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(frame(mm, t)).save(f"skn_{t:05.2f}.jpg", quality=90)
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(mm, n / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", sys.argv[2])
