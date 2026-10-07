"""Emerald festive reel (1080x1920 @30fps, 25s), styled after the reference lookbook reel:
quick one-beat cuts up front, then 2.5s holds cut on the beat, warm light-leak transitions,
natural grade, no on-screen text.

Usage: python reel3.py SRC_DIR out.mp4      (SRC_DIR holds v1.mp4..v4.mp4)
       python reel3.py SRC_DIR --frames 1,3,...
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
BEAT = 0.625                                   # 96 BPM, matches festive_music.py
GRADE = ("curves=master='0/0 0.25/0.23 0.5/0.5 0.75/0.77 1/0.98',eq=saturation=1.08,"
         "colorbalance=rh=0.01:bh=-0.01,unsharp=5:5:0.4")

# (start, dur, clip, src_start, zoom_from, zoom_to)
SHOTS = [
    (0.0, BEAT, 4, 2.6, 1.08, 1.02),     # intro flurry: dupatta twirl
    (BEAT, BEAT, 3, 3.0, 1.08, 1.02),    #   seated
    (2 * BEAT, BEAT, 2, 1.0, 1.08, 1.02),#   embroidery
    (3 * BEAT, BEAT, 1, 3.0, 1.08, 1.02),#   window
    (2.5, 2.5, 1, 0.0, 1.00, 1.06),      # hero by the window
    (5.0, 2.5, 2, 2.0, 1.04, 1.10),      # embroidery close-ups
    (7.5, 2.5, 4, 0.0, 1.00, 1.05),      # full length, dupatta spread
    (10.0, 2.5, 3, 0.0, 1.05, 1.00),     # seated on the sofa
    (12.5, 2.5, 2, 5.0, 1.00, 1.06),     # dupatta texture
    (15.0, 2.5, 4, 3.5, 1.00, 1.05),     # front pose with dupatta
    (17.5, 2.5, 3, 4.5, 1.00, 1.05),     # seated, hand in hair
    (20.0, 2.5, 1, 5.5, 1.00, 1.04),     # dupatta drape, turning
    (22.5, 2.5, 4, 6.0, 1.00, 1.05),     # last look
]
TOTAL = 25.0
LEAKS = [2.5, 15.0, 22.5]                     # warm light-leak flashes on these cuts
FLASH = [12.5]                                # soft white pop where the music lifts

def ease(p): p = min(max(p, 0.0), 1.0); return p * p * (3 - 2 * p)

def load(src_dir, cache):
    """Decode every shot (graded, 1080x1920) into a raw file once; memmap it."""
    os.makedirs(cache, exist_ok=True)
    procs = []
    for i, (st, du, c, s0, *_ ) in enumerate(SHOTS):
        p = os.path.join(cache, f"shot{i:02d}_c{c}_{s0:.2f}.rgb")
        if not os.path.exists(p):
            procs.append(subprocess.Popen(
                ["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{du + 0.2:.3f}",
                 "-i", os.path.join(src_dir, f"v{c}.mp4"),
                 "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS},{GRADE}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", p]))
    for pr in procs: pr.wait()
    mm = []
    for i, (st, du, c, s0, *_ ) in enumerate(SHOTS):
        p = os.path.join(cache, f"shot{i:02d}_c{c}_{s0:.2f}.rgb")
        n = os.path.getsize(p) // (W * H * 3)
        mm.append(np.memmap(p, np.uint8, "r", shape=(n, H, W, 3)))
    return mm

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)

def leak_layer(p):
    """Warm orange light leak sweeping across the frame, p in 0..1."""
    cx = W * (1.3 - 1.6 * p); cy = H * (0.3 + 0.3 * p)
    g = np.exp(-(((XX - cx) / (W * 0.65)) ** 2 + ((YY - cy) / (H * 0.55)) ** 2))
    return np.stack([g * 255, g * 120, g * 40], -1)

def frame(mm, t):
    i = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-9)
    st, du, c, s0, z0, z1 = SHOTS[i]
    arr = mm[i][min(int((t - st) * FPS), len(mm[i]) - 1)]
    z = z0 + (z1 - z0) * ease((t - st) / du)
    if abs(z - 1) > 1e-3:
        cw, ch = W / z, H / z
        arr = np.asarray(Image.fromarray(arr).resize((W, H), Image.BICUBIC,
                         box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)))
    out = arr.astype(np.float32)
    for T in LEAKS:
        if abs(t - T) < 0.35:
            p = (t - (T - 0.35)) / 0.7
            k = math.sin(math.pi * p) * 0.85
            out = 255 - (255 - out) * (1 - leak_layer(p) / 255 * k)      # screen blend
    for T in FLASH:
        if abs(t - T) < 0.12:
            out = out + (255 - out) * 0.35 * (1 - abs(t - T) / 0.12)
    fade = min(1.0, t / 0.25, (TOTAL - t) / 0.6)
    return np.clip(out * fade, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    src_dir = sys.argv[1]
    mm = load(src_dir, os.environ.get("CACHE", "cache3"))
    if "--frames" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--frames") + 1].split(",")]:
            Image.fromarray(frame(mm, t)).save(f"f_{t:05.2f}.jpg", quality=88)
        sys.exit()
    out = sys.argv[2]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(int(TOTAL * FPS)):
        enc.stdin.write(frame(mm, n / FPS).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", out)
