# FRESHMAN

A story-driven high school basketball game in the spirit of Telltale's *The Wolf Among Us*. You play Theo Reyes at Halston Heights, from the first day of open gym through the end of junior year. The basketball is quick-time events: shots, passes, defensive reads, free throws and late-game Clutch Time. The story is everything else, including family, money, recruiters, teachers, teammates, and who you're still talking to at the end. Every choice carries forward across three seasons.

**Play free:** https://papaserf.github.io/Freshman/

Works in Chrome, Edge or Firefox on PC (keyboard or controller) and on Android tablets (touch). Sound on.

## Season One · Freshman

| # | Episode | | # | Episode |
|---|---|---|---|---|
| 0 | Open Gym | | 5 | Improper Benefits |
| 1 | Cut List | | 6 | The Inquiry |
| 2 | Splinters & Spotlights | | 7 | The Hearing |
| 3 | The Holiday Classic | | 8 | The Last Practice *(finale)* |
| 4 | Ineligible | | | |

## Season Two · Sophomore

| # | Episode | | # | Episode |
|---|---|---|---|---|
| 1 | Summer Reruns | | 5 | Program / Outside |
| 2 | Road Greys | | 6 | Rematch |
| 3 | Standings | | 7 | Sectionals |
| 4 | The Fork | | 8 | The Long Hallway *(finale)* |

## Season Three · Junior

| # | Episode | | # | Episode |
|---|---|---|---|---|
| 1 | First Person | | 5 | Holiday Classic |
| 2 | Second Draft | | 6 | Paper Trail |
| 3 | The Fan | | 7 | On the Record |
| 4 | Substitute | | 8 | Sectional *(finale)* |

**Season Four · Senior** is coming as a paid release on itch.io. Use your Season Three save code to carry everything forward (see below).

There's also an **H-O-R-S-E** mode on the title screen.

## How the basketball works

- **Shots:** hold, then release when the marker hits the gold. Nerves shrink the window.
- **Passes, charges and step-backs:** tap when the sweeping marker crosses the gold.
- **Defense:** read the ball-handler and slide the way he goes. Some arrows are fakes. Each run of steps is shuffled every time.
- **Clutch Time:** the last two minutes of big games are played possession by possession. You call the play on offense and guard their best player on defense.
- **Learned moves:** Theo picks up signature moves from mentors as the story goes, such as the step-back, hesitation, euro step, floater and taking a charge. Each one adds a new option in Clutch Time.
- **Film room:** scouting an opponent's tendencies before a game makes him easier to read on defense.

## Controls

| Action | Keyboard | Controller | Touch |
|---|---|---|---|
| Advance / confirm / shoot (hold, release) | Space | A | Tap / hold |
| Dialogue choices | 1 2 3 4 | A X Y B | Tap |
| Defense slides | Arrows / WASD | D-pad / stick | Swipe |
| Pause, scene select | Esc / P | Start | ⏸ button |

## Saves and save codes

Progress saves in your browser (localStorage) automatically. It's stored per device and per site, so a save from one link doesn't carry over to another.

When you finish Season Three, the ending card shows a **save code** with a Copy button. You can also get it any time later from **Show my save code** on the title screen. The code holds every choice and stat from all three seasons. Keep it somewhere safe: Season Four asks for it, and you can also use it to move a playthrough between devices.

## What's in here

```
index.html          The whole game in one file. Three.js r147 loads from a CDN;
                    3D models, faces and decals are embedded as base64.
models/             Rigged character body (with body-type morphs) and hair pieces, as .glb.
faces/original/     Face drawings as delivered.
faces/cleaned/      The versions baked into the game (flat skin background).
decals/original/    Wall art as delivered (banners, posters, boards, signs, paintings).
decals/cleaned/     Cut-out versions embedded in the game (.webp with transparency).
tools/make_cast.py  Blender script that generates the bodies and hair (headless bpy).
tools/clean_face.py Prepares a new face drawing and prints the matching skin tone.
lib/ scripts/ test/ deno.json   Visual-regression and debugging harness (Deno + Playwright).
```

Face files use the in-game keys. Most are named after the character (`theo`, `lou`, `priya`, `albright` and so on). The rest are `x1` Oduya, `x3` Briscoe, `x4` Duff, `o1` opponent #4, `o3` opponent #21, `whit` Ms. Whitfield, `coach` Coach Okafor and `panel` the IHSAA panel chair.

## Adding a face

1. Draw it on the face-kit layout: 2:1, face centered on the left half, with **one flat skin-colored background** (no panel, no halftone).
2. Run `python3 tools/clean_face.py drawing.png faces/cleaned/<key>.jpg`. It prints the skin tone.
3. Embed it in `index.html` as `<script type="text/plain" id="face-<key>">data:image/jpeg;base64,…</script>` and set that character's `skin:` in `CFG` to the printed value.

## Adding a decal

1. Draw it flat and straight-on, on a plain white background.
2. Cut out the background, then save it as `.webp` with transparency in `decals/cleaned/`.
3. Embed it as `<script type="text/plain" id="dec-<key>">data:image/webp;base64,…</script>`, then place it with `decal('<key>', width, height, parent, position, rotY)` in `decorate()`. An optional draw callback lets you letter real text onto blank areas.

## Rebuilding the bodies

```
pip install bpy        # Blender as a Python module
python3 tools/make_cast.py --out out
```

Then re-embed `out/base_body.glb` in `index.html` (`<script id="glb-base_body">`, base64).

## Credits

Built with Claude, ChatGPT and Gemini, in collaboration with Papaserf.

## License

Seasons One through Three are free to play and to share unmodified, with credit, under [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/). No selling and no modified versions. See [LICENSE](LICENSE). Season Four (Senior) isn't in this repository, and all rights to it are reserved. Three.js is MIT-licensed by its authors.
