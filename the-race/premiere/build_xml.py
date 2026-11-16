"""Build a Premiere Pro-importable FCP7 XML (xmeml v4) of THE RACE edit.

Premiere: File > Import > THE_RACE_v1.xml. Clips come in offline; right-click
one > Link Media, point at your downloaded clips folder, and Premiere finds the
rest by file name. Same for the graphics in the-race/graphics/out/.

Everything is laid at 100% speed. Speed ramps, the freeze and the camera shake
are left as sequence markers to do by hand, because speed changes don't
round-trip reliably through XML.

Usage: python3 build_xml.py OUT.xml [CLIPS_DIR] [GRAPHICS_DIR]
"""
import sys
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

FPS = 24
SEQ_W, SEQ_H = 1920, 1080

# name: (seconds, width, height)
CLIPS = {
    "01_puddle_macro.mp4": (5, 1344, 768),
    "02_hairpin.mp4": (5, 1344, 768),
    "03_visor.mp4": (4, 1344, 768),
    "04_paddle.mp4": (3, 1344, 768),
    "05_chase.mp4": (5, 1344, 768),
    "06_overtake.mp4": (5, 1344, 768),
    "07_finish_slowmo.mp4": (4, 1344, 768),
    "08A_reveal_flux_1080p.mp4": (8, 1920, 1080),
    "W1_sim_wide_back.mp4": (6, 1344, 768),
    "W2_sim_wide_front.mp4": (6, 1344, 768),
    "T1_finish_into_screens.mp4": (6, 1344, 768),
    "T2_visor_to_helmet_off.mp4": (5, 1344, 768),
    "T3_chase_to_rig.mp4": (6, 1344, 768),
    "M1_morph_back.mp4": (6, 1344, 768),
    "M3_morph_lime_wipe.mp4": (6, 1344, 768),
    "TD_trading_desk.mp4": (5, 1344, 768),
    "10_reward_screen.mp4": (3, 1344, 768),
}
GFX = {
    "endcard.mov": 120,
    "telemetry_overlay.mov": 48,
    "reward_ui.mov": 72,
    "lime_wipe.mov": 24,
    "lime_flash.mov": 2,
}

FIT = SEQ_W / 1344 * 100  # 142.857: fills 1920 width from 1344

# V1 picture edit: (clip, src_in, src_out, punch) -- punch multiplies the fit scale.
# Laid back to back from REC_START.
REC_START = 6  # 6 frames of black first
V1 = [
    ("01_puddle_macro.mp4", 30, 66, 1.00),     # cold open hit
    ("02_hairpin.mp4", 12, 34, 1.00),
    ("03_visor.mp4", 10, 22, 1.30),
    ("04_paddle.mp4", 6, 16, 1.20),
    ("02_hairpin.mp4", 60, 80, 1.35),          # punch-in = new angle
    ("03_visor.mp4", 40, 50, 1.00),
    ("05_chase.mp4", 0, 40, 1.00),
    ("04_paddle.mp4", 40, 50, 1.40),
    ("05_chase.mp4", 70, 98, 1.30),
    ("T3_chase_to_rig.mp4", 132, 142, 1.00),   # 10-frame subliminal glimpse of the rig
    ("03_visor.mp4", 70, 82, 1.20),
    ("06_overtake.mp4", 0, 40, 1.00),
    ("06_overtake.mp4", 40, 72, 1.15),         # FREEZE zone (telemetry on top)
    ("06_overtake.mp4", 72, 118, 1.00),
    ("07_finish_slowmo.mp4", 0, 60, 1.00),
    ("T1_finish_into_screens.mp4", 12, 132, 1.00),  # THE TWIST, silence
    ("W1_sim_wide_back.mp4", 24, 60, 1.00),
    ("M3_morph_lime_wipe.mp4", 12, 108, 1.00),
    ("TD_trading_desk.mp4", 24, 72, 1.00),
    ("10_reward_screen.mp4", 12, 60, 1.00),
    ("endcard.mov", 0, 120, None),
]


def layout(events, start):
    out, rec = [], start
    for clip, i, o, punch in events:
        d = o - i
        out.append(dict(clip=clip, src_in=i, src_out=o, start=rec, end=rec + d, punch=punch))
        rec += d
    return out


def rate():
    return f"<rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>"


class Doc:
    def __init__(self, clips_dir, gfx_dir):
        self.clips_dir, self.gfx_dir = clips_dir, gfx_dir
        self.defined = set()
        self.n = 0

    def file_xml(self, name):
        fid = f"file-{name}"
        if fid in self.defined:
            return f'<file id="{escape(fid)}"/>'
        self.defined.add(fid)
        if name in CLIPS:
            secs, w, h = CLIPS[name]
            dur, folder = secs * FPS, self.clips_dir
        else:
            dur, w, h, folder = GFX[name], SEQ_W, SEQ_H, self.gfx_dir
        url = "file://localhost" + quote(f"{folder.rstrip('/')}/{name}")
        return (f'<file id="{escape(fid)}"><name>{escape(name)}</name><pathurl>{url}</pathurl>'
                f"{rate()}<duration>{dur}</duration><media><video><samplecharacteristics>"
                f"{rate()}<width>{w}</width><height>{h}</height><pixelaspectratio>square</pixelaspectratio>"
                f"</samplecharacteristics></video></media></file>")

    def clipitem(self, ev, scale, enabled=True, composite=None):
        self.n += 1
        name = ev["clip"]
        dur = CLIPS[name][0] * FPS if name in CLIPS else GFX[name]
        comp = f"<compositemode>{composite}</compositemode>" if composite else ""
        return (f'<clipitem id="clipitem-{self.n}"><name>{escape(name)}</name>'
                f"<enabled>{'TRUE' if enabled else 'FALSE'}</enabled><duration>{dur}</duration>{rate()}"
                f"<start>{ev['start']}</start><end>{ev['end']}</end>"
                f"<in>{ev['src_in']}</in><out>{ev['src_out']}</out>{self.file_xml(name)}{comp}"
                "<filter><effect><name>Basic Motion</name><effectid>basic</effectid>"
                "<effectcategory>motion</effectcategory><effecttype>motion</effecttype>"
                "<mediatype>video</mediatype><parameter><parameterid>scale</parameterid>"
                f"<name>Scale</name><valuemin>0</valuemin><valuemax>1000</valuemax>"
                f"<value>{scale:.3f}</value></parameter></effect></filter></clipitem>")


def build(clips_dir, gfx_dir):
    doc = Doc(clips_dir, gfx_dir)
    v1 = layout(V1, REC_START)
    by_clip = {}
    for ev in v1:
        by_clip.setdefault(ev["clip"], []).append(ev)

    def at(clip, k=0):
        return by_clip[clip][k]

    freeze = at("06_overtake.mp4", 1)
    m3 = at("M3_morph_lime_wipe.mp4")
    reward = at("10_reward_screen.mp4")

    # V2 overlays
    v2 = [
        (dict(clip="telemetry_overlay.mov", src_in=0, src_out=freeze["end"] - freeze["start"],
              start=freeze["start"], end=freeze["end"]), True, "normal"),
        (dict(clip="lime_wipe.mov", src_in=0, src_out=24,
              start=m3["start"] + 30, end=m3["start"] + 54), True, "screen"),
        (dict(clip="reward_ui.mov", src_in=0, src_out=reward["end"] - reward["start"],
              start=reward["start"], end=reward["end"]), False, "normal"),  # backup: enable if AI text is wrong
    ]
    # V3 lime flash frames on hard hits
    flash_at = [at("02_hairpin.mp4")["start"], at("04_paddle.mp4")["start"],
                at("04_paddle.mp4", 1)["start"], at("06_overtake.mp4")["start"],
                freeze["start"], at("06_overtake.mp4", 2)["start"]]
    v3 = [dict(clip="lime_flash.mov", src_in=0, src_out=2, start=s, end=s + 2) for s in flash_at]

    total = v1[-1]["end"]
    t1 = []
    for ev in v1:
        scale = 100.0 if ev["punch"] is None else (
            (100.0 if CLIPS[ev["clip"]][1] == SEQ_W else FIT) * ev["punch"])
        t1.append(doc.clipitem(ev, scale))
    t2 = [doc.clipitem(ev, 100.0, enabled=en, composite=cm) for ev, en, cm in v2]
    t3 = [doc.clipitem(ev, 100.0, composite="screen") for ev in v3]

    markers = [
        (at("01_puddle_macro.mp4")["start"], "COLD OPEN", "Hard cut in on the car hit. Engine rev in the black before, if using SFX."),
        (at("05_chase.mp4")["start"], "SPEED RAMP", "Time-remap 100 to 250% into the next cut (Optical Flow). Add camera shake to the onboard shots."),
        (at("T3_chase_to_rig.mp4")["start"], "SUBLIMINAL", "10-frame glimpse of the sim rig. Keep it barely readable."),
        (at("06_overtake.mp4")["start"], "RAMP INTO CORNER", "Ramp 100 to 300% into the freeze."),
        (freeze["start"], "FREEZE", "Frame Hold on the first frame of this clip for 8 to 12 frames, under the telemetry overlay, then ramp back to 100%."),
        (at("07_finish_slowmo.mp4")["start"], "FINISH", "Already slow motion. Last sound before the silence."),
        (at("T1_finish_into_screens.mp4")["start"], "THE TWIST - SILENCE", "Cut ALL sound here. Let the pull-back breathe. No speed-up."),
        (m3["start"], "SIM TO TRADING", "lime_wipe.mov on V2 (Screen) rides the AI wipe. Slide it to match the line in the clip."),
        (reward["start"], "REWARD", "Check the AI text spells PERFORMANCE REWARD EARNED. If not, enable reward_ui.mov on V2 and corner-pin it to the monitor."),
        (at("endcard.mov")["start"], "END CARD", "Replace the placeholder FundingRock wordmark with the official logo."),
    ]
    mk = "".join(f"<marker><name>{escape(n)}</name><comment>{escape(c)}</comment><in>{f}</in><out>-1</out></marker>"
                 for f, n, c in markers)

    def track(items):
        return "<track>" + "".join(items) + "<enabled>TRUE</enabled><locked>FALSE</locked></track>"

    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4">'
            f'<sequence id="sequence-1"><name>THE RACE v1</name><duration>{total}</duration>{rate()}'
            "<timecode><rate><timebase>24</timebase><ntsc>FALSE</ntsc></rate><string>00:00:00:00</string>"
            "<frame>0</frame><displayformat>NDF</displayformat></timecode>"
            "<media><video><format><samplecharacteristics>"
            f"{rate()}<width>{SEQ_W}</width><height>{SEQ_H}</height><pixelaspectratio>square</pixelaspectratio>"
            "<fielddominance>none</fielddominance></samplecharacteristics></format>"
            f"{track(t1)}{track(t2)}{track(t3)}</video><audio/></media>{mk}</sequence></xmeml>\n"), v1, total


if __name__ == "__main__":
    out = Path(sys.argv[1])
    clips = sys.argv[2] if len(sys.argv) > 2 else "/THE_RACE/clips"
    gfx = sys.argv[3] if len(sys.argv) > 3 else "/THE_RACE/graphics"
    xml, v1, total = build(clips, gfx)
    out.write_text(xml)
    for ev in v1:
        print(f"{ev['start']/FPS:6.2f}s  {ev['end']-ev['start']:4d}f  {ev['clip']}")
    print(f"total {total} frames = {total/FPS:.2f}s")
