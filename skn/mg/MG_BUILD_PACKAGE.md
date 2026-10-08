# SKN Theory — Whimsical Glow Peel
## "The Science of a New Glow Season": motion graphics build package

### Files
| File | What it is |
|---|---|
| `SKN_MG_Preview_LABELED.mp4` | **Production preview.** Every media window shows its placeholder label, ID, timing, aspect ratio and in/out transition. **Never publish this file.** |
| `SKN_MG_Clean.mp4` | Graphics with no labels. Placeholders are neutral textured panels, ready to receive footage. |
| `SKN_MG_Clean_RealFootagePreview.mp4` | The clean version with the client's real treatment footage placed in PH1 and PH3 (preview only; PH2, PH4 and the logo remain open). |
| `SKN_MG_WindowMattes.mp4` | White = media window (exact shape, reveal animation and timing), black elsewhere. Use it as a **track matte**. |
| `placeholder_spec.json` | Scene in/out times, placeholder specs, VO placement map, and every window's geometry sampled every 0.5 s. |
| `audio/` | `vo_placed.wav` (the supplied VO, re-timed), `music.wav` (already ducked), `sfx.wav`, `mix.wav` |
| `mg.py`, `mg_audio.py` | The complete motion-graphics and audio build. Change any time, text, colour or position and re-render. |

**On the After Effects request:** I could not create an `.aep` in this environment, and I have not claimed to. The matte, the spec and the code above are the equivalent editable package. Section 4 explains how to rebuild it in AE or Premiere in a few minutes.

---

### 1. Voice-over: timing reference
The supplied ElevenLabs file is 29.4 s. Its 8 phrases were **moved on the timeline to fit the 40.5 s structure but never sped up, stretched or pitch-shifted.** Only the pauses between phrases changed.

The words below come from automatic speech recognition plus correction against the brief. **Please check them against your script.** The typography only uses the brief's on-screen copy, so a wording difference won't break anything.

| Source (s) | Timeline (s) | Spoken (reconstructed) | Synced graphic moment |
|---|---|---|---|
| 0.00–3.40 | 1.20–4.60 | "A new season brings a new reason to care for your skin." | A NEW SEASON. lands on "season" (1.35); *a new glow.* lands on "reason" (2.9) |
| 3.85–6.25 | 5.90–8.30 | "Introducing Whimsical Glow Peel," | WHIMSICAL on "Whimsical" (6.85), GLOW PEEL (7.45) |
| 6.70–9.00 | 8.55–10.85 | "newly introduced at SKN Theory." | A SEASONAL SKINCARE EXPERIENCE (9.85) |
| 9.50–13.25 | 12.60–16.35 | "As fall arrives, it's time to rethink your skincare routine," | Timeline marker arrives at FALL on "fall" (12.8); A TIME TO REVISIT… on "rethink" (14.45) |
| 13.28–15.30 | 18.40–20.42 | "to discover a little extra care." | CARE on "care" (19.9), then RITUAL (21.0) and RADIANCE (22.15) in the breath |
| 15.72–20.60 | 24.20–29.08 | "With wedding season just around the corner, now is the time to start planning your glow." | WEDDING SEASON on "wedding" (24.5), *is coming.* on "corner" (25.85), PLAN YOUR GLOW AHEAD on "planning" (27.9) |
| 21.20–27.00 | 30.80–36.60 | "Discover Whimsical Glow Peel at SKN Theory. Your glow season starts here." | WHIMSICAL GLOW PEEL (31.25); YOUR GLOW SEASON STARTS HERE on "your glow" (35.0); logo slot after the line (36.5) |
| 27.65–29.30 | 37.30–38.95 | "Book your consultation today." | BOOK YOUR CONSULTATION (37.35); SKN THEORY (37.95); held 2.5 s, fade 39.9–40.5 |

### 2. Design system
- **Palette:**
  - charcoal `#211F1D`
  - ivory `#F5F0E9`
  - champagne `#D7C4AD` (all lines and rules)
  - taupe `#A18E80` (captions)
  - blush `#D8B9B1` (reserved)
  - scene 4 background: beige `#EDE5DB`
- **Type:**
  - Headlines: Cormorant Garamond Medium / SemiBold, with Medium Italic for the "voice" lines (*a new glow.*, *is coming.*).
  - Captions and labels: Manrope SemiBold / Bold, all caps, tracking 5–9.
  - Scene index numbers (01–06) sit top-right.
- **Motion language (identical across all scenes):**
  - Entrances: masked vertical reveal, 0.75 s, cubic ease-out. Headlines also expand their tracking (tracking from −4 or +2 to the final value over 1.35 s).
  - Exits: masked drop back behind the baseline, 0.5 s, cubic ease-in.
  - Moves and wipes: smoothstep ease-in-out.
  - Lines: draw over 0.9 s (or from the centre).
  - Camera drift: each scene drifts up 40–70 px over its length. Background, window and type layers drift at different rates for parallax.
  - Texture: 2-pixel animated grain at about 3/255; a slow soft-light drift on flat colour fields; a gentle vignette.

### 3. Scenes
| Scene | Time | Build | Out transition (motivated by) |
|---|---|---|---|
| 01_OPENING | 0.0–5.0 | Charcoal. An ivory hairline draws from the centre. Top-left caption SKN THEORY / SEASONAL SKINCARE. A NEW SEASON. rises; at 2.75 s it lifts as *a new glow.* (champagne) rises beneath. Small strapline THE SCIENCE OF A NEW GLOW SEASON. | The hairline **expands vertically into a full-screen ivory wipe** (4.55–5.25) |
| 02_TREATMENT_INTRO | 5.0–11.6 | Ivory split layout. Left: NEW AT SKN THEORY, champagne tick, WHIMSICAL / GLOW PEEL (word by word), champagne underline, A SEASONAL / SKINCARE EXPERIENCE. Right: **PH1** (440×1035) clip-reveals upward; caption FIG. 01 — IN CLINIC. | **Charcoal graphic wipe** right to left with a champagne leading edge (11.25–11.95) |
| 03_FALL_SEASON | 11.6–17.8 | Charcoal with a faint documentary grid. Timeline JUN–NOV with ticks. SUMMER sits over the timeline; the circular marker travels to OCT and SUMMER drops out as **FALL** rises (12.8, on "fall"). Supporting copy. **PH2** circular window (Ø620) radial-reveals; a champagne ring draws around it with three editorial leader marks, FIG. 02 and SURFACE. | **Timeline marker enlarges into a soft circular wipe** (17.35–18.05) |
| 04_SKINCARE_EXPERIENCE | 17.8–23.6 | Beige. **PH3** (800×1000, 4:5) settles. Seven fine contour lines, inspired by skin texture and purely illustrative, draw in below with parallax. CARE / RITUAL / RADIANCE replace one another through the masked reveal, with a 3-dot progress indicator. | **Soft ivory wipe** from the top (23.2–23.85) |
| 05_WEDDING_SEASON | 23.6–30.2 | Ivory. THE SEASON OF CELEBRATIONS, then **WEDDING / SEASON** (large), then *is coming.* A countdown-inspired 48-tick dial sweeps (no date, no numbers). **PH4** portrait window (440×660) slides in from the right. Champagne rule and PLAN YOUR / GLOW AHEAD. | **Charcoal rises as a mask** while the headline lifts away; champagne edge line (29.6–30.45) |
| 06_FINAL_CTA | 30.2–40.5 | Charcoal. A champagne line crosses the full width. WHIMSICAL / GLOW PEEL rise with tracking. YOUR GLOW SEASON STARTS HERE. **LOGO slot** (560×170) at 36.5. The CTA pill outline draws and BOOK YOUR CONSULTATION appears, then SKN THEORY. Final frame held ≥ 2.5 s, then a clean fade. | Fade to black 39.9–40.5 |

### 4. Placeholders and how to replace them
| ID | Time | Window | Required media | In → out |
|---|---|---|---|---|
| PH1 | 5.3–11.6 | Rect 580,420 → 1020,1455 (drifts up to 50 px) | **Filled in v2:** 5.3–8.8 s the product box (`2.mov` 4.4 s at 0.5× slow motion; the product name stays under the tracked blur), dissolving at 8.4–8.8 s into treatment footage (`1008.mp4` from 2:01.8). | Clip-reveal up → charcoal wipe |
| PH2 | 13.0–17.8 | Circle, centre 540,1300, r 310 | **AI 3D skin-surface animation** from Google Flow (Veo, 9:16, 8 s, subject centred). Save it as `ph2_3d.mp4` in the footage folder; `mg.py footage … --footage DIR` places it automatically (centre crop). | Radial reveal → circular wipe |
| PH3 | 18.0–23.6 | Rect 140,360 → 940,1360 | **Real treatment close-up or AI skin CGI** (`1008.mp4` at 3:12.5 is used in the preview) | Settles in → ivory wipe |
| PH4 | 25.9–30.2 | Rect 560,940 → 1000,1600, slides in from x+520 | **Cinematic bridal beauty B-roll** (2:3 portrait; the AI-3 prompts) | Slide from right → charcoal mask rise |
| LOGO | 36.5–end | Box 260,1120 → 820,1290 | **Official SKN Theory logo file** (not supplied). Opacity 0→100 and scale 96→100%, 0.9 s. Do not redraw or distort it. | Fade in → final fade |

**Fastest replacement (Premiere, Resolve or AE):**
1. V1: `SKN_MG_Clean.mp4`.
2. V2: your footage clip, positioned and scaled to cover the window.
3. V3: `SKN_MG_WindowMattes.mp4`, set as a **Track Matte, Luma** for V2.

The footage then appears only inside the windows, including every reveal, slide and wipe, at exactly the designed timing. No graphics overlap the windows, so nothing gets covered.

**In After Effects:** import `placeholder_spec.json` window geometry as a reference, or simply use the matte as a luma track matte. Organise the comps as 01_OPENING … 06_FINAL_CTA, MEDIA_PLACEHOLDERS, TYPOGRAPHY, GRAPHIC_ELEMENTS, AUDIO and BRAND_ASSETS, and match the scene times in section 3.

**Confidentiality:** if any inserted shot shows packaging, run it through the tracked masking (`../conceal.py`) first. That script already conceals the product name, the manufacturer wordmark, the side print and a third-party label in `2.mov`. None of the graphics, captions or diagrams name the original product.

### 5. Audio
- **VO:** `vo_placed.wav` is the supplied file, re-timed per section 1 and level-matched. Do not stretch it.
- **Music:** original, royalty-free. 80 BPM, D–Bm–G–A, warm FM pads, minimal piano, soft low pulse from scene 2, ticks in scenes 4–5, sub swells at 10 s and 28 s, resolving at 30.4 s. It ducks about 8 dB under every VO phrase (250 ms attack, 400 ms release).
- **Sound design (synced to the graphics):**
  - tonal swell on the opening line draw and the scene 6 line
  - soft ticks on each headline reveal
  - air on the five wipes
  - six rising ticks as the timeline marker travels
  - a bell chord at the logo
  - a tick on the CTA
- **Master:** −14 LUFS integrated, −1 dBTP.

### 6. QC (checked on rendered frames)
| Check | Result |
|---|---|
| Typography inside the safe area | All copy between y 150 and y 1600; side margins ≥ 66 px |
| Readability | Large serif headlines at 76–250 px; captions ≥ 16 px used only as documentary labels |
| Labels absent from publishable files | Labels appear only in `_LABELED`; `_Clean` and `_RealFootagePreview` were checked frame by frame at scene keypoints |
| VO untouched | Phrase segments copied sample-for-sample (12 ms edge fades only); no time-stretching |
| Claims | No ingredients, mechanisms, penetration diagrams, result or safety claims; the skin-texture lines are labelled illustrative; the countdown has no date |
| Open items | Official logo file; PH2/PH4 AI shots; confirm the VO wording in section 1 |
