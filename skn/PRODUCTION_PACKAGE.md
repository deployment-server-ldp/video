# SKN Theory — Whimsical Glow Peel · "Fall Into Your Glow"
### Production package for the 9:16 launch reel

**What exists right now (rendered and checked):**
- `SKN_WhimsicalGlowPeel_Reel_v1.mp4`: 36 s, 1080×1920, 30 fps, H.264. Real client footage only, with typography, transitions, music and sound design.
- `SKN_WhimsicalGlowPeel_TextFree_v1.mp4`: the same edit with no typography.
- `audio/`: `music.wav`, `sfx.wav`, `mix.wav`, `music_vo_ducked.wav` (music pre-ducked under the planned VO lines).
- `SKN_WhimsicalGlowPeel_VO_captions.srt`: the VO script as time-coded captions.
- Scripts that reproduce every render: `conceal.py` (tracked product-name masking), `skn_reel.py` (edit and graphics), `skn_audio.py` (music and SFX).

**What does not exist yet, and why:**
- **AI shots and 3D skin animations: not generated.** No video-generation model is reachable from the production environment. Section 3 has model-ready prompts and a workflow; section 5 shows where each shot drops into the edit.
- **Voice-over: not recorded.** The text-to-speech service is blocked by the environment's network policy, so there is no VO audio. Section 4 has the time-coded script, SSML, direction notes, and a music bed already ducked for it.
- **SKN Theory logo: not supplied.** The end card sets "SKN THEORY" as plain typography. It is not a recreation of the logo. Replace it with the official logo file (section 5, step 9).

---

## 1. Footage analysis (Phase 1)

All three files were opened and inspected frame by frame.

| File | Specs | What it actually shows |
|---|---|---|
| `1008.mp4` | 480×854, 30 fps, 3:48, handheld, phone audio with speech | Clinic treatment session. A practitioner (glasses, lilac outfit, blue gloves) treats a client lying in a treatment chair (white headband, cyan chair). Warm window light comes through blinds. |
| `4.mov` | 1080×1920, 30 fps, 3.5 s, iPhone HDR (HLG 10-bit) | Top-down close-up of the client wearing a translucent pink jelly mask decorated with gem/flower stickers. Slow, steady push-in. This is the most "whimsical" image in the material. |
| `2.mov` | 2160×3840, **60 fps**, 8.1 s, iPhone HDR (HLG 10-bit) | Handheld push-in over the treatment counter onto the product box: a dark box covered in colourful gem and star stickers. **The product name is printed large on the box lid, and a manufacturer wordmark is on a white box beside it.** A hand enters at ~7.3 s. |

### 1.1 `1008.mp4`, segment by segment

| Time | Content | Verdict |
|---|---|---|
| 0:00–0:20 | Practitioner prepares, holds a small amber bottle, talks | Medium-wide, usable as a cutaway |
| 0:24–0:30 | Another person in black walks through the frame | **Unusable** |
| 0:44–0:58 | Practitioner holds a bottle; the client gestures with her hands while talking | Weak: distracting hands |
| **1:12–1:15** | **Cleansing with gauze, both gloved hands on the face; warm light** | **Used: shot 3 (prep)** |
| 1:24–1:30 | Cleansing pads on the forehead | Alternate prep shot |
| 1:40–1:50 | Client sits up and talks to camera | Unusable for this reel (possible testimonial) |
| **1:52–1:55** | **Practitioner holds the bowl and dips the brush** | **Used: shot 4** |
| **2:02–2:05** | **Closest framing in the file: brush applies the orange gel to the forehead** | **Used: shot 5 (strongest real moment)** |
| **2:09–2:11** | **Gel brushed onto the cheek, bowl in hand** | **Used: shot 6** |
| **3:12–3:15** | **Tight application on the chin and cheek** | **Used: shot 7** |
| **3:24–3:27** | **Application detail** | **Used: shot 8** |

- **Quality:** only 480p, so it softens when upscaled. Mitigated with Lanczos upscaling, light denoise and sharpening, and subtle grain to match the 4K clips.
- **Handheld:** every used segment was stabilized (vidstab, 3% zoom).
- **Colour:** the cyan chair and blue gloves fight the cream palette, so blues and cyans were pulled down in the grade.
- **Confidentiality:** bottles are visible at 0:03, 0:46, 0:51, 0:55, 1:05 and 1:53. At this resolution no text is legible on any of them, and on-screen checks found nothing readable. None of those frames is used anyway.

### 1.2 `4.mov`
- **Usable:** all 3.5 s. Used at 0.85× speed as the opening hook.
- **Notes:** the client's face is fully visible. **Confirm the client has given consent for her image to be used in advertising.** No packaging appears.

### 1.3 `2.mov`
- **Usable:** 0.3–6.5 s. The 60 fps source allows a clean 0.5× slow motion.
  - 0.4–2.15 s: push-in, used as shot 2.
  - 4.4–6.15 s: gem close-up, used as shot 9.
  - Avoid 7.0 s onwards (a hand enters, the camera jerks).
- **Confidentiality, handled:** see 1.4.

### 1.4 Confidentiality treatment (mandatory section of the brief)

The masking is done by `conceal.py`, on the full 484-frame source, before any editing:
- **Tracking:** SIFT features with RANSAC homographies, anchored to the first frame so the masks don't drift.
  - 483 of 484 frames tracked directly.
  - 0 frames had to hold the previous position.
- **Four masked areas:**
  1. the product name on the lid
  2. the manufacturer wordmark and its tagline
  3. faint print along the side of the white box
  4. a third-party consumer-brand label on a tub in the background
- **Blur method:** a feathered "frosted" blur that scales with the camera's zoom, plus contrast flattening, so the name stays unreadable even in the closest frames.
- **Check:** after an earlier version proved still partly readable in close-ups, the blur was made zoom-adaptive. Every 8th frame (61 frames, at a size where the type would be legible if unmasked) and full-resolution frames at 0, 1.5, 3, 3.8, 4.5, 5.5, 6.5 and 7.6 s were checked. **Nothing is readable.**
- **Never written anywhere:** the original product and manufacturer names do not appear in this package, the file names or the scripts.

---

## 2. Storyboard: the rendered v1 cut (Phase 2)

Shot timings below refer to the delivered v1 file.

| # | Time | Visual (source @ timestamp) | Typography | Transition in | VO (planned) | Music / SFX |
|---|---|---|---|---|---|---|
| 1 | 0:00–0:04 | `4.mov` 0.0–3.4 s at 0.85×, slow push-in on the gem jelly mask | FALL INTO / *your glow* | fade from black | "Your glow season starts now." | Pad and piano motif; shimmer on the headline |
| 2 | 0:04–0:07.5 | `2.mov` 0.4–2.15 s, 0.5× slow motion, push-in over the box (masked) | INTRODUCING / *Whimsical* / GLOW PEEL (taupe over the white counter) | **Light-matched**: warm bloom through the cut | "Introducing Whimsical Glow Peel…" | Pulse enters; whoosh |
| 3 | 0:07.5–0:10 | `1008` 1:12–1:14.5, cleansing | lower third: NEWLY INTRODUCED AT / SKN THEORY | **Direction-matched** soft vertical whip that continues the downward push-in | "…newly introduced at SKN Theory." | Short whoosh |
| 4 | 0:10–0:13 | `1008` 1:52.5–1:55.5, brush into the bowl | NEW SEASON. / *fresh glow.* | **Match cut on the hands** | "As the season changes…" | Shimmer |
| 5 | 0:13–0:16 | `1008` 2:01.8–2:04.8, brush to the forehead | (held) | **Match cut on the brush** | "…refresh your skincare routine." | none |
| 6 | 0:16–0:18.5 | `1008` 2:09–2:11.5, cheek | lower third: YOUR SEASONAL / *skin reset* | **Champagne light sweep** (the fall-light motif) | "Discover a little extra care…" | Air swell; shaker layer enters |
| 7 | 0:18.5–0:21 | `1008` 3:12.5–3:15 | (held) | Hard cut on the beat | none | none |
| 8 | 0:21–0:23.5 | `1008` 3:24.5–3:27 | (held) | Hard cut on the beat | none | none |
| 9 | 0:23.5–0:27 | `2.mov` 4.4–6.15 s, 0.5× gem close-up (masked) | WEDDING SEASON / *is coming* | **Defocus (texture) dissolve** | "And with wedding season around the corner…" | Breakdown: piano alone, riser |
| 10 | 0:27–0:36 | Typographic end card, warm cream with a drifting champagne light | WEDDING SEASON IS COMING · *Get glow-ready* · *Whimsical* GLOW PEEL · YOUR GLOW SEASON STARTS HERE · DISCOVER IT AT SKN THEORY · [BOOK YOUR CONSULTATION] | **Masked reveal**: a cream panel rises with a soft curved edge | "…plan your glow. Discover Whimsical Glow Peel at SKN Theory. Your glow season starts here." | Chord resolves; chime on SKN THEORY (30.55 s); shimmer on the CTA |

**Grade (all shots):**
- colour temperature 5900 K at 50%
- cyan/blue saturation −45%, overall saturation −8%
- a soft S-curve with lifted blacks (0.02) and a highlight roll-off to 0.97
- vignette −16% at the edges; 2.6 σ grain

**HDR clips:** converted to SDR with a reinhard tone-map, with no brightening and no clipped highlights.

**Typography:**
- Headlines: Cormorant Garamond (Medium / SemiBold, Medium Italic).
- Supporting text: Manrope (SemiBold / Bold), wide tracking.
- Animation: masked rise, gentle tracking expansion on caps, champagne rules that draw from the centre outward.
- Placement: all text stays between y = 270 and y = 1440, inside the Instagram safe area.

**Palette:**
- ivory `#FBF6EE`
- champagne `#C8AE8A`
- rose-nude `#BE8C80`
- taupe `#5E4E45`

---

## 3. AI video generation (Phase 3)

**Workflow:**
- **Models:** Kling 2.x (Pro), Runway Gen-4, or Veo 3.
- **Settings:** 9:16, highest quality, 24 fps, generated at 5 s and trimmed to 2–4 s.
- **Takes:** generate 4 per prompt and keep the most natural one.
- **Grade:** match each shot to the v1 grade (section 2); add 2–3% grain so AI and phone footage sit together.
- **Text:** none inside AI shots; all type stays in post (section 5).

**Global negative prompt** (append to every prompt):
> plastic skin, airbrushed, beauty filter, glowing skin effect, sparkles, lens-flare overload, morphing face, extra fingers, warped hands, distorted eyes, uncanny, CGI look, text, letters, logo, watermark, product packaging, bottle labels, brand names, before-and-after, medical equipment close-ups, blood, redness, irritation, oversaturated, orange skin, harsh contrast, fast motion, jitter, floating objects

### AI-1: Opening hook, radiant skin in autumn light (3 s)
- **Position:** replaces 0:00–0:02.5. The gem-mask shot then follows at 0:02.5–0:04.5.
- **Prompt:** *Photorealistic beauty-campaign close-up of a woman in her late twenties with naturally radiant, healthy-looking skin and visible natural texture and fine pores, minimal makeup, eyes gently closed then softly opening. Warm late-afternoon autumn sunlight from camera-left through a sheer linen curtain casts soft champagne light across her cheekbone. Cream and ivory background, softly out of focus. 85 mm lens at f/2, shallow depth of field. Very slow dolly-in toward her face. Natural skin tones, soft highlight roll-off, warm beige and rose-nude palette. Subtle natural movement: a small breath, a slight head tilt. Luxury skincare advertising cinematography. 9:16, 3 seconds.*
- **Transition out:** the light-matched bloom into the gem-mask shot. Match the warm left-side key light.

### AI-2: Fall-light insert (2.5 s)
- **Position:** 0:13.5–0:16, between the brush-in-bowl shot and the forehead application, to carry "NEW SEASON. FRESH GLOW."
- **Prompt:** *Macro beauty shot of the side of a woman's cheek and jawline, realistic skin texture with fine vellus hair visible. The shadow of a softly moving sheer curtain drifts across the skin, and the warm light shifts from neutral daylight to golden autumn tone over the shot, suggesting the change of season. 100 mm macro lens, locked-off camera with a very slow lateral slide left to right. Cream, warm beige and champagne tones. No leaves, no props. Photorealistic, luxury skincare campaign. 9:16, 2.5 seconds.*
- **Transition:** the light direction left to right matches the champagne light sweep at 0:16.

### AI-3: Bridal beauty sequence (2 × 2.5 s)
- **Position:** 0:23.5–0:28.5. Push the gem close-up to the end-card reveal, or drop it.
- **Prompt A:** *Photorealistic bridal beauty close-up: a South Asian woman in her late twenties with soft, natural bridal makeup and naturally radiant skin with real texture, delicate gold-and-pearl earring, a sheer ivory dupatta edge at frame-right. Soft window light from the left, warm and diffused. She turns her face slowly toward the light with a calm, subtle smile. 85 mm, f/1.8, slow push-in. Ivory, champagne and rose-nude palette. Elegant, understated luxury bridal campaign, not fashion editorial. 9:16, 2.5 seconds.*
- **Prompt B:** *Macro detail of a woman's hand lightly adjusting a fine pearl-and-gold earring near her jawline. Realistic skin and anatomically correct fingers, soft warm window light, champagne bokeh background. Slow tilt up from the earring to her cheek. 100 mm macro. Luxury bridal beauty advertising. 9:16, 2.5 seconds.*
- **Transition out:** a face close-up with a soft curved-edge cream panel rising, into the end card (as in v1).

### 3D-1: Macro visualization of skin layers (3 s)
- **Position:** 0:10.5–0:13, on "As the season changes…". Shot 4 then shortens to 0:13–0:14.
- **Prompt:** *Premium cosmetic-advertising CGI, photorealistic: an ultra-macro cross-section of human skin shown as soft translucent layers. A smooth matte surface layer sits over softer, warmer layers below, rendered like frosted glass and silk rather than a medical diagram. Soft studio lighting from above, warm ivory and blush tones with champagne rim light, shallow depth of field. A slow, smooth camera glide along and slightly down into the layers. Elegant and minimal. No labels, no arrows, no cells or molecules floating, no scientific annotations. 9:16, 3 seconds, 24 fps.*
- **Transition out:** match-dissolve the curved surface layer into the curve of the forehead in shot 5.

### 3D-2: Conceptual surface-renewal animation (2.5 s)
- **Position:** 0:18.5–0:21, replacing shot 7, on "YOUR SEASONAL skin reset".
- **Prompt:** *High-end skincare CGI macro: a softly lit, photoreal skin-texture surface in warm beige. A gentle wave of light moves across it, and the surface becomes smoother and more even in tone as the light passes. This is a subtle, abstract visual metaphor, not a clinical depiction. Silky material, soft studio key light from top-left, champagne highlights, cream background falloff. Slow overhead camera drift. No peeling skin, no flakes, no redness, no before/after split, no text. 9:16, 2.5 seconds.*
- **Messaging rule:** use only as an abstract visual. **Do not pair it with any result claim.**

### 3D-3: Skin-radiance transition (2 s)
- **Position:** 0:26.5–0:27.5, as the bridge into the end card.
- **Prompt:** *Elegant beauty CGI: an extreme close-up of photoreal skin texture under warm light. A soft, natural sheen blooms gently across the surface like morning light, then the frame dissolves into a warm cream silk background. Slow push-in, soft studio lighting, ivory, champagne and rose-nude palette. Restrained and luminous, not glittery. No sparkles, no particles, no text. 9:16, 2 seconds.*
- **Transition out:** its cream end frame becomes the end-card background.

**AI usage rules (from the brief):** never present AI or CGI skin as customer results, and never place it next to result language. In v2, real footage still carries the treatment story: shots 2–8 stay real.

---

## 4. Voice-over and audio (Phase 4)

**Casting:**
- English female, late 20s to 30s.
- Warm, soft, confident; contemporary neutral accent (British RP or neutral North American).
- Moderate pace, about 2.4 words per second.
- No upsell energy.

**Suggested synthetic voices (if the client prefers TTS):**
- ElevenLabs: a warm "narration" female voice, Stability 45%, Similarity 75%, Style 15%.
- Azure / Edge: `en-GB-SoniaNeural` or `en-US-AvaNeural`.

| Time in v1 | Line | Delivery |
|---|---|---|
| 0:00.4–0:02.8 | Your glow season starts now. | Soft, intimate; small lift on "glow" |
| 0:04.4–0:09.2 | Introducing Whimsical Glow Peel, newly introduced at SKN Theory. | Slight pause after "Introducing"; savour "Whimsical" |
| 0:10.4–0:14.4 | As the season changes, it's time to refresh your skincare routine. | Even and flowing |
| 0:16.4–0:19.8 | Discover a little extra care for your skin this season. | Warm and personal |
| 0:23.4–0:29.0 | And with wedding season around the corner, it's the perfect time to plan your glow. | Gentle smile in the voice; slow down on "plan your glow" |
| 0:29.6–0:34.6 | Discover Whimsical Glow Peel at SKN Theory. Your glow season starts here. | Confident close; let "starts here" land |

> Script note: "Introducing … newly introduced" repeats a word. The client's wording is preserved above. A suggested alternative for line 2: *"Introducing Whimsical Glow Peel — now at SKN Theory."*

**SSML** (Azure-style; adjust the voice name):
```xml
<speak version="1.0" xml:lang="en-GB" xmlns:mstts="https://www.w3.org/2001/mstts">
 <voice name="en-GB-SoniaNeural"><mstts:express-as style="gentle"><prosody rate="-8%" pitch="-2%">
  <s>Your <emphasis level="moderate">glow</emphasis> season starts now.</s><break time="1500ms"/>
  <s>Introducing<break time="250ms"/> Whimsical Glow Peel, newly introduced at <say-as interpret-as="characters">SKN</say-as> Theory.</s><break time="1000ms"/>
  <s>As the season changes, it's time to refresh your skincare routine.</s><break time="1800ms"/>
  <s>Discover a little extra care for your skin this season.</s><break time="3500ms"/>
  <s>And with wedding season around the corner, it's the perfect time to <prosody rate="-12%">plan your glow.</prosody></s><break time="600ms"/>
  <s>Discover Whimsical Glow Peel at <say-as interpret-as="characters">SKN</say-as> Theory.<break time="350ms"/> Your glow season <emphasis level="moderate">starts here.</emphasis></s>
 </prosody></mstts:express-as></voice>
</speak>
```

**Pronunciation:**
- "SKN" is read as the letters "S-K-N" unless the client says it as "skin". **Confirm with the client.**
- "Whimsical": WHIM-zi-kul.

**Music** (original, synthesized, royalty-free, `music.wav`):
- 120 BPM half-time feel, F major.
- Chords: Fmaj7, Am7, Dm9, B♭maj7.
- Instruments: soft FM pads, gentle round pulse (no click), lowpassed piano and plucks, air texture.
- Structure:
  - 0:00–0:04: pad and piano motif.
  - 0:04: pulse enters.
  - 0:16: shaker layer and higher plucks.
  - 0:23.5–0:27: breakdown (piano alone, short riser).
  - 0:27: the chord resolves into the end card.
  - 0:34.5–0:36: fade.

**Sound design** (`sfx.wav`, sitting about 9 dB under the music):
- Airy whooshes at 4.0, 7.5, 16.0 and 27.0 s; a reverse swell into 23.5 s.
- Glass shimmers on the headline reveals at 0.45, 4.75, 8.05, 10.35, 16.45, 23.85 and 28.5 s.
- A bell chord on "SKN THEORY" (30.55 s) and a shimmer on the CTA (31.85 s).

**Mix:**
- `mix.wav` is the delivered soundtrack; the final file is loudness-normalized to −14 LUFS.
- `music_vo_ducked.wav` has about 7 dB of ducking under each VO line, with 250 ms attack and 350 ms release. Lay the recorded VO over it, peaking around −6 dBFS, then normalize the master to −14 LUFS integrated, −1 dBTP.

---

## 5. Editing plan for v2, the AI-enhanced cut (Phase 5)

The timeline is 38 s at 30 fps, 1080×1920. Start from the text-free master and the stems.

1. **0:00–0:02.5:** AI-1 (hook). Typography "FALL INTO / *your glow*" from 0.45 s (see `skn_reel.py` `footage_text()` for exact sizes and positions).
2. **0:02.5–0:04.5:** `4.mov`, light-matched bloom in.
3. **0:04.5–0:08:** shot 2 (box, masked). INTRODUCING / *Whimsical* / GLOW PEEL in taupe over the white counter.
4. **0:08–0:10.5:** shot 3, with the lower third NEWLY INTRODUCED AT SKN THEORY.
5. **0:10.5–0:13:** 3D-1 skin layers, then match-dissolve on its curve into the forehead.
6. **0:13–0:14:** shot 4 (brush in bowl, trimmed), then a match cut on the brush to shot 5 at **0:14–0:16**. NEW SEASON. / *fresh glow.* runs 0:10.6–0:15.6.
7. **0:16–0:18.5:** champagne light sweep into shot 6, lower third YOUR SEASONAL / *skin reset*. **0:18.5–0:21:** 3D-2 renewal. **0:21–0:23.5:** shot 8.
8. **0:23.5–0:28.5:** AI-3 A, then AI-3 B. WEDDING SEASON / *is coming* at 23.85 s. **0:28.5–0:29.5:** 3D-3 radiance bridge.
9. **0:29.5–0:38:** end card (all reveals shifted +2.5 s). **Replace the "SKN THEORY" type with the official logo file**, scaled to about 60% of frame width and kept as a vector or high-resolution PNG, undistorted. Hold the final CTA frame for at least 3 s.
10. **Audio:** stretch the music bed by inserting a 2-bar (2 s) extension of the breakdown at 0:23.5. Re-align the SFX to the new cut points and lay the VO per section 4 with the +2.5 s offset after 0:04.

**In Premiere / Resolve:**
- Use the text-free master as V1 and put the AI shots on V2.
- Put typography on V3, as Essential Graphics or Fusion Text+, using the same fonts and colours.
- Easing: 0.7 s ease-out on reveals, 0.45 s fade-and-lift on exits.

---

## 6. Quality control (Phase 6)

| Check | v1 result |
|---|---|
| Confidentiality | **Pass.** Tracked masks on all 484 source frames; the frame-sampled and full-resolution checks found no readable name or wordmark; no packaging in the AI prompts. |
| Real footage first | **Pass.** 100% real footage in v1; v2 keeps all real treatment shots. |
| Typography readable on mobile | **Pass.** Ivory with a shadow over mid-tones, taupe with a light halo over the white counter; all inside the safe area. |
| Transitions motivated | **Pass.** Light-matched, direction-matched whip, action match cuts, light sweep, texture dissolve, masked reveal. No glitches, spins or repeated flashes. |
| Grade consistency | **Pass**, with one caveat: the 480p treatment clip is visibly softer than the 4K clips. A higher-resolution original of `1008.mp4` would lift the whole middle of the reel. **Request it from the client if one exists.** |
| Claims | **Pass.** No ingredients, results, recovery times, safety or "for everyone" claims; no before/after. |
| Voice-over | **Not done:** TTS is blocked in this environment. Script and SSML are ready. |
| AI and 3D shots | **Not done:** no generation model available. Prompts and slots are ready. |
| Logo | **Open:** official logo not supplied; typographic placeholder in use. |
| Client consent | **Open:** confirm consent for the client's and practitioner's faces in paid or organic ads. |
| Export | H.264 High, yuv420p, 1080×1920, 30 fps, AAC 192 kbps stereo, −14 LUFS. |
