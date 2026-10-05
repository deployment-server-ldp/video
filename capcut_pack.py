"""Build a CapCut (free) edit pack from the reel's layers.

Usage (from the dir holding prep.mp4, src.mp4, bg_notext.mp4):
    python capcut_pack.py OUT_DIR
"""
import os, shutil, subprocess, sys
from PIL import Image
import render as R

OUT = sys.argv[1] if len(sys.argv) > 1 else "CapCut_Edit_Pack"
HERE = os.path.dirname(os.path.abspath(__file__))
dirs = {k: os.path.join(OUT, v) for k, v in dict(
    vid="1_Video", clips="2_Clips_Raw", png="3_Text_PNG", ovl="4_Overlays_PNG", aud="5_Audio").items()}
for d in dirs.values():
    os.makedirs(d, exist_ok=True)

def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)

def save_rgba(layer, path, radius=10):
    R.shadowed(Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0)), layer, radius=radius).save(path)

# ---- 1. background video (all VFX/transitions/explosions, no text, no HUD) + finished reel
ff("-i", "bg_notext.mp4", "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "11M", "-bufsize", "22M",
   "-pix_fmt", "yuv420p", "-movflags", "+faststart", os.path.join(dirs["vid"], "Background_VFX_NoText.mp4"))
shutil.copy(os.path.join(HERE, "cigarette_machine_reel.mp4"), os.path.join(dirs["vid"], "Final_Reel_Reference.mp4"))

# ---- 2. raw clips per section (stabilised + colour graded, no effects), at their reel speed
names = ["Cam_Mechanism", "Gear_Drive", "Rotary_Turret", "Pack_Forming", "Folding_Unit",
         "Drive_System", "Output", "PLC_Control"]
for i, (s, n) in enumerate(zip(R.SEGS, names), 1):
    src_len = s.src_time(s.dur) - s.src
    speed = src_len / s.dur
    ff("-ss", f"{s.src:.3f}", "-t", f"{src_len:.3f}", "-i", "prep.mp4",
       "-vf", f"setpts=PTS/{speed:.4f},scale=1080:1920:flags=lanczos,fps=30",
       "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-an",
       os.path.join(dirs["clips"], f"Clip_{i:02d}_{n}.mp4"))
# drive system: also a plain 1x version (ramp is easy to redo with CapCut Speed > Curve)
s = R.SEGS[5]
ff("-ss", f"{s.src:.3f}", "-t", "4.0", "-i", "prep.mp4", "-vf", "scale=1080:1920:flags=lanczos",
   "-c:v", "libx264", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p", "-an",
   os.path.join(dirs["clips"], "Clip_06b_Drive_System_Normal_Speed.mp4"))

# ---- 3. text PNGs (full-frame 1080x1920, transparent; drop in at 100% scale and they line up)
save_rgba(R.intro_layer(2.6), os.path.join(dirs["png"], "00_Intro_Title.png"), 14)
for i, s in enumerate(R.SEGS, 1):
    if s.l1:
        save_rgba(R.title_layer(s, s.text_in + 1.6), os.path.join(dirs["png"], f"{i:02d}_Title_{s.l1}_{s.l2}.png".replace(" ", "_")))
save_rgba(R.outro_layer(25.0 + 4.0), os.path.join(dirs["png"], "99_Outro_Title.png"), 14)

# ---- 4. overlays
R.hud_layer(5.0, R.SEGS[0], dynamic=False).save(os.path.join(dirs["ovl"], "HUD_Frame.png"))
grad = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))
grad.putalpha(Image.fromarray((R.BOTTOM_GRAD[..., 0] * 255).astype("uint8")))
grad.save(os.path.join(dirs["ovl"], "Bottom_Dark_Gradient.png"))

# ---- 5. audio
env = dict(os.environ, STEMS_DIR=dirs["aud"])
subprocess.run([sys.executable, os.path.join(HERE, "audio.py"), "src.mp4", os.path.join(dirs["aud"], "full_mix.wav")],
               env=env, check=True)
for n, new in [("music", "Music_Beat.wav"), ("sfx", "SFX_Explosions_Whoosh.wav"), ("machine", "Machine_Sound.wav")]:
    os.replace(os.path.join(dirs["aud"], f"{n}.wav"), os.path.join(dirs["aud"], new))
os.replace(os.path.join(dirs["aud"], "full_mix.wav"), os.path.join(dirs["aud"], "Full_Mix.wav"))

# ---- 6. titles as SRT (CapCut: Text > Local captions > Import)
def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s_:02d},{ms:03d}"
cues = [(0.45, 2.95, "CIGARETTE MAKING MACHINE\nPRECISION • SPEED • POWER")]
for s in R.SEGS:
    if s.l1:
        cues.append((s.start + s.text_in, s.end - s.text_out + 0.3, f"{s.l1} {s.l2}\n{s.cap}"))
cues.append((R.SEGS[1].start + 0.2, R.SEGS[1].end - 0.1, "GEAR DRIVE"))
cues.append((25.55, 29.9, "CIGARETTE MAKING MACHINE\nFOLLOW FOR MORE"))
cues.sort()
with open(os.path.join(OUT, "Titles.srt"), "w", encoding="utf-8") as fh:
    for k, (a, b, txt) in enumerate(cues, 1):
        fh.write(f"{k}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")

# ---- fonts used (free, OFL)
os.makedirs(os.path.join(OUT, "6_Fonts"), exist_ok=True)
for f in ("Bebas.ttf", "Montserrat.ttf"):
    shutil.copy(os.path.join(R.FONT_DIR, f), os.path.join(OUT, "6_Fonts", f))
shutil.copy(os.path.join(HERE, "CAPCUT_GUIDE.txt"), os.path.join(OUT, "CAPCUT_GUIDE_URDU.txt"))
print("pack ready:", OUT)
