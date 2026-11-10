# THE RACE: production plan

FundingRock cinematic spot. A driver wins a night race in the rain, and then we find out the whole race ran on a simulator.
**Line:** The race was simulated. The rewards are real.

- **Runtime:** 30s hero (16:9, 1080p). A 9:16 reframe follows for social.
- **Tone:** Hollywood motorsport, photoreal, restrained. Black, graphite and wet chrome. One accent colour from the floodlights (sodium amber / cool white), and the reward UI is the only colour that "glows".
- **Rule:** The race should feel real right up to the reveal. Don't drop hints early (no screen bezels, no visible UI).

---

## Shot list (30s)

| # | Time | Shot | Camera | Purpose |
|---|---|---|---|---|
| 1 | 0:00–0:03 | Wet asphalt macro. Floodlight reflections ripple, then a black car tears through frame and spray hits the lens | Locked low macro, car passes left to right | Cold open, sound-led |
| 2 | 0:03–0:06 | Black car exits a hairpin under floodlights, rooster tail of spray | Wide telephoto, slight pan | Scale, night race |
| 3 | 0:06–0:08 | Helmet visor ECU: eyes behind a dark visor, reflections of track lights sliding across | Extreme close-up, handheld micro-shake | The driver, focus |
| 4 | 0:08–0:10 | Gloved hands snap a downshift paddle, wheel vibrating | Cockpit insert | Tension |
| 5 | 0:10–0:13 | Low tracking shot alongside the rear wheel, a rival car's lights ahead in the spray | Low car-mount tracking | Chase |
| 6 | 0:13–0:16 | Overtake: the black car dives inside the rival into the final corner, wheel to wheel | Wide aerial / crane | The manoeuvre |
| 7 | 0:16–0:18 | Finish line: chequered flag, the car crosses, spray hangs in the floodlight | Low wide, slight slow-mo | Win |
| 8 | 0:18–0:24 | **The reveal.** One continuous pull-back from over the driver's shoulder through the cockpit. The "track" turns out to be three curved simulator screens. The pull-back carries on out to a dark, minimal studio with the rig on a motion platform under one top light | Slow continuous dolly back | Twist |
| 9 | 0:24–0:27 | Driver lifts off the helmet, slight smile, glances at a side display | Medium, rack focus to display | Human beat |
| 10 | 0:27–0:28 | Display insert: **PERFORMANCE REWARD EARNED** | Screen insert | Payoff |
| 11 | 0:28–0:30 | Cut to black, then the end card | — | Brand |

**End card (rendered locally so the type is exact, never AI-generated text):**
```
THE RACE WAS SIMULATED.
THE REWARDS ARE REAL.

FundingRock
Simulated Trading. Performance-Based Rewards.
```

---

## Pipeline on Higgsfield

1. **Lock the look with keyframes** (Nano Banana Pro, 2K, 16:9). I generate a "bible" still of the car, the helmet/suit and the sim studio, then use them as `image_references` for every keyframe so the car, livery and helmet stay the same in every shot.
2. **Animate each shot** from its keyframe:
   - Race shots 1–7: **Cinema Studio Video**, pro mode, genre `action`, 3–5s each, sound off (we score it ourselves).
   - Reveal shot 8: **FLUX 3 Video** or **Seedance 2.5** with a **start frame** (shoulder/cockpit with the "race" on the screen) and an **end frame** (wide studio). The two-frame setup is what makes the pull-back read as one believable move. Planned as 6–8s, and I'll draft it 2–3 times because it carries the spot.
   - Shots 9–10: Cinema Studio Video, `intimate` genre.
3. **Edit and finish locally** with the repo's existing tooling (`render.sh`, `sfx.py`): cut, grade, engine/rain sound design, a sub-drop and silence at the reveal, then the typeset end card in exact brand type.
4. **Deliverables:** 30s 16:9 master, plus a 9:16 via `reframe`.

---

## Prompt drafts

**Bible: car.** Photoreal night motorsport still, a matte-black prototype race car on a rain-soaked circuit, no sponsor logos, no numbers, wet carbon bodywork, floodlights overhead, sodium-amber and cool-white reflections streaking on the asphalt, mist and spray, anamorphic 2.39 look, shallow depth, film grain, Hollywood motorsport cinematography.

**Bible: driver.** Close-up of a racing driver in a gloss-black full-face helmet with a dark smoked visor, black race suit, no logos, cockpit HANS device, rain droplets on the visor, floodlight reflections, intense stillness, photoreal, cinematic.

**Bible: sim studio.** A high-end professional racing simulator on a motion platform in a dark, minimal studio. Black concrete floor, one soft overhead light, three large curved screens showing a wet night race, cables neatly routed, a quiet, expensive space, photoreal, cinematic wide shot.

**Shot 8 (reveal), video prompt.** One continuous slow dolly back from over the driver's shoulder. The rainy night circuit seen through the windscreen turns out to be curved simulator screens; the camera keeps pulling back to show the simulator rig on its motion platform in a dark minimal studio lit by a single overhead light. Steady, believable, no cuts, photoreal.

**Shot 10, display.** A minimal dark UI panel on a slim monitor beside the rig, clean sans-serif white text "PERFORMANCE REWARD EARNED", a subtle accent glow, shallow depth of field. *(If the model garbles the text, the same insert gets a composited UI.)*

---

## Compliance notes (FundingRock wording)

- Use "rewards", "performance-based rewards" and "simulated trading" only. Never "profits", "earnings", "salary" or "income", and no money figures on screen.
- No real racing series, teams, sponsors, tracks or car makes. The car is unbranded.
- The driver is AI-generated and isn't a real athlete.

## Open questions

1. The visual direction in the brief stops at "Black…". Was there more (e.g. black-and-gold, a brand accent colour)?
2. Is there a voiceover or music only? The plan assumes music, sound design and on-screen type.
3. Credit budget for generation (see the estimate in chat).
