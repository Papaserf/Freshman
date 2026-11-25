# FRESHMAN

A story-driven high school basketball season, in the spirit of Telltale's *The Wolf Among Us*. You play Theo Reyes, a freshman at Halston Heights. The basketball is quick-time events (shots, passes, defensive reads, free throws). The story is everything else: family, money, a recruiter named Vance, a state inquiry, and who you sit next to at the banquet. Choices carry forward across all nine episodes.

**Play:** https://papaserf.github.io/freshman/

Works in Chrome, Edge or Firefox on PC (keyboard or controller) and on Android tablets (touch). Sound on.

## Season One

| # | Episode | | # | Episode |
|---|---|---|---|---|
| 0 | Open Gym | | 5 | Improper Benefits |
| 1 | Cut List | | 6 | The Inquiry |
| 2 | Splinters & Spotlights | | 7 | The Hearing |
| 3 | The Holiday Classic | | 8 | The Last Practice (finale) |
| 4 | Ineligible | | | |

There's also **H-O-R-S-E** mode on the title screen.

## Controls

| Action | Keyboard | Controller | Touch |
|---|---|---|---|
| Advance / confirm / shoot (hold, release) | Space | A | Tap / hold |
| Dialogue choices | 1 2 3 4 | A X Y B | Tap |
| Defense slides | Arrows / WASD | D-pad / stick | Swipe |
| Pause, scene select | Esc / P | Start | ⏸ button |

## What's in here

```
index.html        The whole game. One self-contained file (Three.js r147 from a CDN;
                  3D models and face textures are embedded as base64).
models/           Rigged character body (with body-type morphs) and hair pieces, as .glb.
faces/original/   Face drawings as delivered.
faces/cleaned/    The versions baked into the game (flat skin background, no stripe).
tools/make_cast.py   Blender script that generates the bodies and hair (headless bpy).
tools/clean_face.py  Prepares a new face drawing and prints the matching skin tone.
```

`faces/cleaned` uses the in-game keys: `x1` Oduya, `x3` Briscoe, `x4` Duff, `o1` opponent #4, `o3` opponent #21, `whit` Ms. Whitfield.

## Saves

Progress is saved in your browser (localStorage), per device and per site, so saves from one link don't carry over to another.

## Adding a face

1. Draw it on the face-kit layout: 2:1, face centered on the left half, and **one flat skin-colored background** (no panel, no halftone).
2. `python3 tools/clean_face.py drawing.png faces/cleaned/<key>.jpg` prints the skin tone.
3. Embed it in `index.html` as `<script type="text/plain" id="face-<key>">data:image/jpeg;base64,…</script>` and set that character's `skin:` in `CFG` to the printed value.

## Rebuilding the bodies

```
pip install bpy        # Blender as a Python module
python3 tools/make_cast.py --out out
```

Then re-embed `out/base_body.glb` in `index.html` (`<script id="glb-base_body">`, base64).

## Credits

Built with Claude, ChatGPT and Gemini, in collaboration with Papaserf.
