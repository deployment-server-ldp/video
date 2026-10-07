"""Emerald reel v2 — romantic cut (1080x1920 @30fps, 27s).

Every moment of every clip is used once (no repeated source ranges), five motion-interpolated
slow-mos, soft dissolves / warm light leaks, cuts on the 80 BPM beat of romantic_music.py.

Usage: python reel3b.py SRC_DIR out.mp4  |  python reel3b.py SRC_DIR --frames 1,4,...
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
GRADE = ("curves=master='0/0 0.25/0.23 0.5/0.5 0.75/0.77 1/0.98',eq=saturation=1.08,"
         "colorbalance=rh=0.01:bh=-0.01,unsharp=5:5:0.4")
TAIL = 0.6   # extra seconds decoded past each shot's end, for dissolves

# (start, dur, clip, src_start, speed, zoom_from, zoom_to, transition_in)
SHOTS = [
    (0.0, 3.0, 2, 0.0, 0.5, 1.06, 1.00, None),        # slow-mo: dupatta sweeps over embroidered hem
    (3.0, 3.0, 1, 0.0, 1.0, 1.00, 1.05, "dissolve"),  # by the window
    (6.0, 1.5, 2, 1.5, 1.0, 1.04, 1.08, "cut"),       # embroidery panel
    (7.5, 1.5, 2, 4.0, 1.0, 1.06, 1.02, "cut"),       # sleeve detail
    (9.0, 3.0, 4, 1.8, 0.5, 1.00, 1.04, "leak"),      # slow-mo: dupatta twirl
    (12.0, 3.0, 3, 0.5, 1.0, 1.04, 1.00, "dissolve"), # seated, looking away
    (15.0, 1.5, 2, 6.0, 1.0, 1.00, 1.05, "cut"),      # dupatta drape close-up
    (16.5, 1.5, 1, 4.8, 0.5, 1.02, 1.06, "cut"),      # slow-mo: dupatta swings open
    (18.0, 3.0, 3, 4.6, 0.5, 1.00, 1.05, "leak"),     # slow-mo: hand in hair
    (21.0, 3.0, 4, 4.5, 1.0, 1.00, 1.04, "dissolve"), # full look by the TV wall
    (24.0, 3.0, 1, 7.0, 0.5, 1.00, 1.06, "dissolve"), # slow-mo: back view, hair & dupatta
]
TOTAL = 27.0
LEAKS = [s[0] for s in SHOTS if s[7] == "leak"]

def ease(p): p = min(max(p, 0.0), 1.0); return p * p * (3 - 2 * p)

def shot_path(cache, i):
    st, du, c, s0, sp, *_ = SHOTS[i]
    return os.path.join(cache, f"b{i:02d}_c{c}_{s0:.2f}_{sp:.2f}.rgb")

def load(src_dir, cache):
    os.makedirs(cache, exist_ok=True)
    procs = []
    for i, (st, du, c, s0, sp, *_ ) in enumerate(SHOTS):
        p = shot_path(cache, i)
        if os.path.exists(p): continue
        src_len = (du + TAIL) * sp
        vf = f"scale={W}:{H}:flags=lanczos,fps={FPS}"
        if sp < 1:   # motion-compensated slow motion
            vf += f",setpts={1 / sp:.4f}*PTS,minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
        vf += "," + GRADE
        procs.append(subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{src_len:.3f}",
                                       "-i", os.path.join(src_dir, f"v{c}.mp4"), "-vf", vf,
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", p]))
        if len(procs) >= 4:
            procs.pop(0).wait()
    for pr in procs: pr.wait()
    out = []
    for i in range(len(SHOTS)):
        p = shot_path(cache, i)
        out.append(np.memmap(p, np.uint8, "r", shape=(os.path.getsize(p) // (W * H * 3), H, W, 3)))
    return out

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((XX - W / 2) / (W * 0.75)) ** 2 + ((YY - H / 2) / (H * 0.7)) ** 2)
VIG = np.clip(1 - 0.18 * np.clip(_r - 0.5, 0, None) ** 1.5, 0.8, 1)[..., None].astype(np.float32)

def leak_layer(p):
    cx = W * (1.3 - 1.6 * p); cy = H * (0.25 + 0.35 * p)
    g = np.exp(-(((XX - cx) / (W * 0.65)) ** 2 + ((YY - cy) / (H * 0.55)) ** 2))
    return np.stack([g * 255, g * 125, g * 50], -1)

def shot_img(mm, i, t):
    st, du, c, s0, sp, z0, z1, _ = SHOTS[i]
    arr = mm[i][min(max(int((t - st) * FPS), 0), len(mm[i]) - 1)]
    z = z0 + (z1 - z0) * ease((t - st) / du)
    if abs(z - 1) > 1e-3:
        cw, ch = W / z, H / z
        arr = np.asarray(Image.fromarray(arr).resize((W, H), Image.BICUBIC,
                         box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)))
    return arr.astype(np.float32)

def frame(mm, t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-9)
    out = shot_img(mm, i, t)
    st, kind = SHOTS[i][0], SHOTS[i][7]
    lt = t - st
    if kind == "dissolve" and lt < 0.5:          # previous shot keeps playing under the fade
        a = ease(lt / 0.5)
        out = shot_img(mm, i - 1, t) * (1 - a) + out * a
    for T in LEAKS:                              # warm light leak across the cut
        if abs(t - T) < 0.35:
            p = (t - (T - 0.35)) / 0.7
            out = 255 - (255 - out) * (1 - leak_layer(p) / 255 * math.sin(math.pi * p) * 0.8)
    out = out * VIG
    fade = min(1.0, t / 0.6, (TOTAL - t) / 1.2)
    return np.clip(out * fade, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    mm = load(sys.argv[1], os.environ.get("CACHE", "cache3b"))
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(frame(mm, t)).save(f"b_{t:05.2f}.jpg", quality=88)
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(mm, n / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", sys.argv[2])
