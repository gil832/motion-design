# THE RACE: Premiere timeline

`THE_RACE_v1.xml` opens in Premiere as the sequence **THE RACE v1**: 1920×1080, 24 fps, about 36s before speed ramps (about 33–34s after).

## Open it
1. Download the clips from `the-race/downloads.txt` into one folder, using the **exact file names** on the left.
2. Pull this branch so you have `the-race/graphics/out/` (end card, overlays, flash, wipe).
3. In Premiere: **File → Import →** `THE_RACE_v1.xml`.
4. The clips import offline. Right-click one → **Link Media** → find it in your clips folder. Premiere links the rest by name. Do the same for one graphics file.

Want it to link with no prompts? Give me your two folder paths and I'll rebuild the XML with them:
```bash
python3 the-race/premiere/build_xml.py the-race/premiere/THE_RACE_v1.xml "/Users/you/THE RACE/clips" "/Users/you/motion-design/the-race/graphics/out"
```

## What's already done
| Track | Contents |
|---|---|
| V1 | The full cut, 21 events: cold open → build-up (with punch-in angles already scaled) → 10-frame sim-rig glimpse → overtake → finish → **T1 twist** → W1 → **M3 sim-to-trading morph** → trading desk → reward screen → end card. The 1344×768 clips are pre-scaled to 142.857% to fill the frame. |
| V2 | `telemetry_overlay.mov` over the overtake freeze, `lime_wipe.mov` (Screen) over M3, and `reward_ui.mov` **disabled** as a backup for the monitor text. |
| V3 | `lime_flash.mov` 2-frame hits (Screen) on six hard cuts. |
| Markers | Ten markers with instructions: speed ramps, freeze, silence at the twist, logo swap. |

## What to do by hand (speed doesn't import reliably from XML)
- **Speed ramps** at the SPEED RAMP and RAMP INTO CORNER markers: Time Remapping with Optical Flow.
- **Freeze** at FREEZE: Frame Hold for 8–12 frames under the telemetry overlay.
- **Camera shake** on the visor, paddle and chase shots.
- **Grade**: one adjustment layer over V1 (see `the-race/edit-guide.md`).
- **Logo**: swap the placeholder FundingRock wordmark in the end card for the official logo.

## Assumptions
Clip lengths are what was requested from Higgsfield (3–8s at 24 fps). If a downloaded clip turns out shorter or at another frame rate, Premiere marks those edits. Send me the real lengths and I'll rebuild the XML.
