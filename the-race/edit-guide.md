# THE RACE: edit guide (Premiere + After Effects, no new Higgsfield credits)

Download links and file names are in `the-race/downloads.txt`. It's private and kept out of git.

## 1. Project setup
- Sequence: 1920×1080, **24 fps**.
- Interpret every clip at 24 fps (Modify → Interpret Footage).
- Most clips are 1344×768. For now, scale them to frame with **Set to Frame Size**. Upscale only the final takes later, either with Higgsfield after Nov 21 or with Topaz Video AI if you have it. Clip 08A is already 1080p.
- Grade: one adjustment layer over everything. Lumetri: crushed blacks, cool/teal highlights, saturation pulled down everywhere except the lime (#D9FF00), which stays punchy (use HSL Secondary to protect it).

## 2. Cut (about 32s)

| Time | Clip(s) | Treatment |
|---|---|---|
| 0:00–0:01 | Black | Engine rev in the dark, if you use sound |
| 0:01–0:02 | 01_puddle_macro | Hard cut in on the car hit; 2-frame lime flash |
| 0:02–0:05 | 02_hairpin, 03_visor, 04_paddle | Shots of 6–10 frames. Punch-ins at 120–140% on 03 and 04 give extra angles. Lime flash frame on each paddle snap. |
| 0:05–0:09 | 05_chase, punch-ins of 02 and 05 | Speed ramp 100→250% into each cut. Camera shake: AE `wiggle(12,8)` or Transform with 180° shutter. |
| 0:09–0:10 | T3_chase_to_rig (first ~12 frames only) | **Subliminal glimpse** of the sim rig, cut away before the viewer registers it |
| 0:10–0:13 | 06_overtake | Ramp up, **freeze for 8 frames** at wheel-to-wheel with the lime telemetry graphic (gear, speed, delta), then back to 100% |
| 0:13–0:15 | 07_finish_slowmo | Slow motion, spray hanging, chequered flag |
| 0:15–0:19 | **T1_finish_into_screens** | **Hard silence.** Let the pull-back breathe. The twist happens here. |
| 0:19–0:21 | W1_sim_wide_back | The platform still moving. Hold the wide shot. |
| 0:21–0:24 | **M3_morph_lime_wipe** (or M1) | The lime line wipes the sim into the trading room |
| 0:24–0:26 | TD_trading_desk | Push in, trend line climbing |
| 0:26–0:28 | 10_reward_screen | PERFORMANCE REWARD EARNED. If the AI text is wrong, cover the monitor with an AE text layer (motion-tracked). |
| 0:28–0:32 | End card (AE) | THE RACE WAS SIMULATED. / THE REWARDS ARE REAL. then FundingRock / Simulated Trading. Performance-Based Rewards. |

Spare clips: 08A/B/C (alternative reveals), W2, T2 (visor to helmet off; good for a 9:16 cut), M2, 09.

## 3. Energy toolkit
- **Cut on motion:** tyre spin → shift lights → paddle. Match the direction of movement across each cut.
- **Speed ramps:** Time Remapping with **Optical Flow**. Speed into the moment, slam to 40% on the impact.
- **Flash frames:** Colour Matte #D9FF00, 2 frames, blend mode Screen at 60–80%.
- **Whip transitions:** a 4-frame directional blur on both sides of the cut.
- **Overlays:** lens dirt, rain on the lens, slight chromatic aberration on the onboard shots only.
- **Contrast is the energy.** Keep the race fast and the reveal silent and slow. Don't speed up the reveal.

## 4. End card (After Effects)
- Black background. Text white; "REAL." in lime #D9FF00.
- Line 1 hard-cuts on. Line 2 resolves letter by letter with a quick lime scan line. 6–8 frame hold, then the FundingRock logo.
- Subline in small caps: *Simulated Trading. Performance-Based Rewards.*

## 5. Wording rules
- Only "rewards", "performance-based rewards" and "simulated trading".
- **No** profits, earnings or income, and no currency or money figures anywhere, including the telemetry graphics and chart screens. Telemetry shows racing data only (gear, km/h, lap delta).

## 6. Deliverables
- 16:9 master (32s or a tight 30s: trim the 0:00 black and shorten W1).
- 9:16 with Premiere **Auto Reframe**, then check the reveal and end card by hand.
- 6s bumper: puddle → overtake freeze → M3 → end card.

## After Nov 21 (Higgsfield credits back)
- Upscale only the final takes to 1080p.
- Optional: about 8 extra 3s race inserts (~50 credits) if the build-up still feels thin.
