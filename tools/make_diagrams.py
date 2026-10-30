#!/usr/bin/env python3
"""Generate the hand-drawn (code-drawn) editorial diagrams used inside guides.

Every diagram is plain SVG written here rather than downloaded, so it stays
sharp at any size, weighs a few kilobytes and cannot misrepresent a product.
Colours match the site palette; type falls back to the system stack when the
SVG is inlined and inherits Inter otherwise.
"""
import os

OUT = "assets/img/diagrams"
C = {
    "ink": "#08080b", "panel": "#121218", "line": "rgba(255,255,255,.12)",
    "text": "#f4f1ec", "muted": "#9a968d", "dim": "#7c7970",
    "flame": "#ff5a1f", "flame2": "#ff8a3d", "amber": "#ffc14d",
    "blue": "#8cc4ff", "mint": "#63d9a8", "rose": "#ff7a7a",
}
FONT = 'font-family="Inter, system-ui, sans-serif"'


def svg(w, h, body, label):
    return (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="{label}" xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def beat_phase():
    """Two kick patterns: out of phase, then locked."""
    w, h = 720, 326
    b = [f'<rect width="{w}" height="{h}" fill="none"/>']
    # headers
    b.append(f'<text x="0" y="18" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>OUT OF PHASE</text>')
    b.append(f'<text x="0" y="176" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>LOCKED</text>')
    # grid
    for x in range(40, 700, 60):
        b.append(f'<line x1="{x}" y1="34" x2="{x}" y2="290" stroke="{C["line"]}" stroke-width="1"/>')
    # track A (reference) kicks
    def kicks(y, offset, colour, height=42):
        out = []
        x = 40 + offset
        i = 0
        while x < 700:
            out.append(
                f'<rect x="{x-3}" y="{y-height}" width="6" height="{height}" rx="3" fill="{colour}"/>'
            )
            x += 60
            i += 1
        return "".join(out)
    # out of phase
    b.append(kicks(96, 0, C["blue"]))
    b.append(kicks(112, 22, C["flame"]))
    b.append(f'<path d="M62 128 L82 128" stroke="{C["rose"]}" stroke-width="1.6"/>')
    b.append(f'<path d="M62 128 l5 -4 M62 128 l5 4 M82 128 l-5 -4 M82 128 l-5 4" stroke="{C["rose"]}" stroke-width="1.6" fill="none"/>')
    b.append(f'<text x="92" y="132" fill="{C["rose"]}" font-size="12" {FONT}>~90 ms late — audibly smeared, no flam</text>')
    # locked
    b.append(kicks(238, 0, C["blue"], 46))
    b.append(f'<rect x="35" y="244" width="8" height="46" rx="4" fill="{C["flame"]}"/>')
    for x in range(100, 700, 60):
        b.append(f'<rect x="{x-4}" y="244" width="8" height="46" rx="4" fill="{C["flame"]}" opacity=".92"/>')
    b.append(f'<text x="36" y="314" fill="{C["mint"]}" font-size="12" {FONT}>kicks on the same grid line = one perceived beat, no flam</text>')
    # legend
    b.append(f'<rect x="470" y="8" width="10" height="10" rx="2" fill="{C["blue"]}"/>')
    b.append(f'<text x="486" y="17" fill="{C["muted"]}" font-size="11" {FONT}>Track A (master)</text>')
    b.append(f'<rect x="588" y="8" width="10" height="10" rx="2" fill="{C["flame"]}"/>')
    b.append(f'<text x="604" y="17" fill="{C["muted"]}" font-size="11" {FONT}>Track B (cue)</text>')
    return svg(w, h, "".join(b), "Diagram: two kick patterns out of phase, then locked on the same grid")


def track_structure():
    w, h = 720, 190
    parts = [
        ("Intro", 16, "#2a2a36", C["muted"]),
        ("Build", 16, "#3a3325", C["amber"]),
        ("Drop", 32, "#43251a", C["flame2"]),
        ("Breakdown", 16, "#24283a", C["blue"]),
        ("Drop 2", 32, "#43251a", C["flame2"]),
        ("Outro", 16, "#2a2a36", C["muted"]),
    ]
    total = sum(p[1] for p in parts)
    x = 8
    width = w - 16
    b = []
    for name, bars, fill, colour in parts:
        seg = width * bars / total
        b.append(f'<rect x="{x:.1f}" y="46" width="{seg-2:.1f}" height="58" rx="6" fill="{fill}" stroke="rgba(255,255,255,.08)"/>')
        b.append(f'<text x="{x+seg/2:.1f}" y="72" text-anchor="middle" fill="{colour}" font-size="12" font-weight="600" {FONT}>{name}</text>')
        b.append(f'<text x="{x+seg/2:.1f}" y="90" text-anchor="middle" fill="{C["dim"]}" font-size="11" {FONT}>{bars} bars</text>')
        x += seg
    b.append(f'<text x="8" y="24" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>A TYPICAL 128-BAR HOUSE EDIT</text>')
    b.append(f'<path d="M8 128 H{width+8}" stroke="{C["line"]}"/>')
    for bar in (1, 33, 65, 97, 129):
        bx = 8 + width * (bar - 1) / total
        b.append(f'<line x1="{bx:.1f}" y1="124" x2="{bx:.1f}" y2="132" stroke="{C["dim"]}"/>')
    b.append(f'<text x="8" y="152" fill="{C["dim"]}" font-size="11" {FONT}>Mix on phrase boundaries — bar 1, 33, 65, 97. Eight bars is the smallest unit worth moving.</text>')
    b.append(f'<text x="8" y="172" fill="{C["mint"]}" font-size="11" {FONT}>Bring the new track in over the intro, swap bass at the drop, take the old one out across the breakdown.</text>')
    return svg(w, h, "".join(b), "Diagram: sections of a typical 128-bar house track with bar counts")


def eq_bands():
    w, h = 720, 250
    b = [f'<text x="0" y="18" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>THREE-BAND EQ, AND WHAT IT DOES TO A MIX</text>']
    # plot area
    x0, y0, x1, y1 = 10, 40, 470, 210
    b.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="rgba(255,255,255,.02)" stroke="{C["line"]}" rx="6"/>')
    for gx in range(x0, x1, 46):
        b.append(f'<line x1="{gx}" y1="{y0}" x2="{gx}" y2="{y1}" stroke="rgba(255,255,255,.05)"/>')
    mid = (y0 + y1) / 2
    b.append(f'<line x1="{x0}" y1="{mid}" x2="{x1}" y2="{mid}" stroke="{C["line"]}" stroke-dasharray="3 4"/>')
    # neutral curve
    b.append(f'<path d="M{x0+6} {mid} H{x1-6}" stroke="{C["dim"]}" stroke-width="1.4" stroke-dasharray="4 4"/>')
    # cut/boost curve: low cut, mid flat, high slight boost
    b.append(
        f'<path d="M{x0+6} {mid+52} C 90 {mid+52}, 120 {mid+46}, 150 {mid+16} '
        f'S 210 {mid-2}, 260 {mid} S 340 {mid}, 390 {mid-10} S 440 {mid-14}, {x1-6} {mid-14}" '
        f'fill="none" stroke="{C["flame"]}" stroke-width="2.4" stroke-linecap="round"/>'
    )
    b.append(f'<text x="60" y="{mid+72}" fill="{C["flame2"]}" font-size="11" {FONT}>bass −6 dB</text>')
    b.append(f'<text x="238" y="{mid-14}" fill="{C["dim"]}" font-size="11" {FONT}>mids flat</text>')
    b.append(f'<text x="368" y="{mid-26}" fill="{C["blue"]}" font-size="11" {FONT}>highs +2 dB</text>')
    for label, gx in (("60 Hz", 40), ("250 Hz", 150), ("1 kHz", 260), ("4 kHz", 370), ("12 kHz", 440)):
        b.append(f'<text x="{gx}" y="{y1+16}" fill="{C["dim"]}" font-size="10" {FONT}>{label}</text>')
    # faders
    for i, (label, pos, colour) in enumerate((("LOW", .72, C["flame"]), ("MID", .48, C["mint"]), ("HIGH", .36, C["blue"]))):
        fx = 520 + i * 66
        b.append(f'<rect x="{fx}" y="46" width="8" height="150" rx="4" fill="rgba(255,255,255,.07)"/>')
        b.append(f'<rect x="{fx-10}" y="{46 + 150*pos - 6}" width="28" height="12" rx="3" fill="{colour}"/>')
        b.append(f'<text x="{fx-10}" y="214" fill="{C["muted"]}" font-size="10" {FONT}>{label}</text>')
    b.append(f'<text x="520" y="238" fill="{C["dim"]}" font-size="10" {FONT}>channel 2 while blending</text>')
    return svg(w, h, "".join(b), "Diagram: three-band EQ curve with a bass cut and treble lift, plus fader positions")


def signal_chain():
    w, h = 720, 210
    boxes = [
        ("Controller", "USB out,\nbuilt-in interface", 8, 118),
        ("Laptop", "audio routed back\nto the controller", 148, 123),
        ("Master out", "RCA or XLR\nto the speakers", 288, 123),
        ("Speakers", "PA, amp or\nactive monitors", 428, 123),
        ("Booth / monitor", "same mix,\nlouder on stage", 568, 118),
    ]
    b = [f'<text x="8" y="18" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>WHERE THE SOUND ACTUALLY GOES</text>']
    for name, sub, x, wd in boxes:
        b.append(f'<rect x="{x}" y="46" width="{wd}" height="66" rx="8" fill="{C["panel"]}" stroke="{C["line"]}"/>')
        b.append(f'<text x="{x+wd/2}" y="70" text-anchor="middle" fill="{C["text"]}" font-size="12" font-weight="600" {FONT}>{name}</text>')
        for i, line in enumerate(sub.split("\n")):
            b.append(f'<text x="{x+wd/2}" y="{86+i*13}" text-anchor="middle" fill="{C["dim"]}" font-size="10" {FONT}>{line}</text>')
    for x in (126, 271, 411, 551):
        b.append(f'<path d="M{x} 79 h14" stroke="{C["flame"]}" stroke-width="1.6"/>')
        b.append(f'<path d="M{x+14} 79 l-5 -4 v8 z" fill="{C["flame"]}"/>')
    b.append(f'<text x="8" y="140" fill="{C["muted"]}" font-size="11" {FONT}>Headphones plug into the controller and monitor the cue bus — they do not replace the master output.</text>')
    b.append(f'<text x="8" y="160" fill="{C["dim"]}" font-size="11" {FONT}>No sound at all? Check: master fader up → channel fader up → trim → crossfader centre → correct output device in software.</text>')
    b.append(f'<text x="8" y="180" fill="{C["dim"]}" font-size="11" {FONT}>Buzz or hum? Use balanced TRS/XLR for long runs, keep speaker cables away from power supplies, and gain-stage at the trim.</text>')
    return svg(w, h, "".join(b), "Diagram: signal path from controller to laptop, master output, speakers and booth monitor")


def budget_split():
    w, h = 720, 220
    rows = [
        ("Controller", 55, C["flame"]),
        ("Headphones", 15, C["blue"]),
        ("Cables + adapter", 8, C["mint"]),
        ("Stand / riser", 7, C["amber"]),
        ("Music + software", 15, C["rose"]),
    ]
    b = [f'<text x="0" y="18" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>HOW A $400 FIRST RIG ACTUALLY DIVIDES</text>']
    x = 0
    width = w
    for name, pct, colour in rows:
        seg = width * pct / 100
        b.append(f'<rect x="{x:.1f}" y="40" width="{seg-2:.1f}" height="34" rx="4" fill="{colour}" opacity=".85"/>')
        if pct >= 8:
            b.append(f'<text x="{x+seg/2:.1f}" y="62" text-anchor="middle" fill="#0b0b10" font-size="11" font-weight="700" {FONT}>{pct}%</text>')
        x += seg
    for i, (name, pct, colour) in enumerate(rows):
        y = 102 + i * 22
        b.append(f'<rect x="0" y="{y-8}" width="9" height="9" rx="2" fill="{colour}"/>')
        b.append(f'<text x="16" y="{y}" fill="{C["muted"]}" font-size="11" {FONT}>{name}</text>')
        b.append(f'<text x="150" y="{y}" fill="{C["dim"]}" font-size="11" {FONT}>${400*pct/100:.0f}</text>')
    b.append(f'<text x="420" y="102" fill="{C["dim"]}" font-size="11" {FONT}>The controller is most of the budget, but not all of it.</text>')
    b.append(f'<text x="420" y="121" fill="{C["dim"]}" font-size="11" {FONT}>Cables, a stand and spare pads are what</text>')
    b.append(f'<text x="420" y="140" fill="{C["dim"]}" font-size="11" {FONT}>people forget until the first gig.</text>')
    b.append(f'<text x="420" y="172" fill="{C["mint"]}" font-size="11" {FONT}>Buy the controller used; buy headphones new.</text>')
    return svg(w, h, "".join(b), "Diagram: budget split for a 400 dollar first DJ rig")


def phrase_grid():
    w, h = 720, 210
    b = [f'<text x="0" y="18" fill="{C["muted"]}" font-size="12" letter-spacing="1.6" {FONT}>THE 16-BEAT PHRASE, COUNTED</text>']
    for bar in range(4):
        bx = 8 + bar * 172
        for beat in range(4):
            x = bx + beat * 42
            strong = beat == 0
            b.append(
                f'<rect x="{x}" y="44" width="38" height="38" rx="6" '
                f'fill="{"rgba(255,90,31,.20)" if strong else "rgba(255,255,255,.04)"}" '
                f'stroke="{C["flame"] if strong else C["line"]}"/>'
            )
            b.append(f'<text x="{x+19}" y="68" text-anchor="middle" fill="{C["flame2"] if strong else C["muted"]}" font-size="12" font-weight="600" {FONT}>{bar*4+beat+1}</text>')
        b.append(f'<text x="{bx}" y="98" fill="{C["dim"]}" font-size="10" {FONT}>bar {bar+1}</text>')
    b.append(f'<text x="8" y="126" fill="{C["muted"]}" font-size="11" {FONT}>1 2 3 4 · 2 2 3 4 · 3 2 3 4 · 4 2 3 4 — say it out loud while you mix.</text>')
    b.append(f'<text x="8" y="146" fill="{C["dim"]}" font-size="11" {FONT}>Kick on 1 and 3, snare or clap on 2 and 4. That is the skeleton of almost every house and techno record.</text>')
    b.append(f'<text x="8" y="166" fill="{C["dim"]}" font-size="11" {FONT}>When you can hear where beat 1 is without counting, you can mix in cleanly. That is the whole trick.</text>')
    return svg(w, h, "".join(b), "Diagram: a four-bar phrase counted in sixteenths, showing the downbeat")


DIAGRAMS = {
    "beat-phase": beat_phase,
    "track-structure": track_structure,
    "eq-bands": eq_bands,
    "signal-chain": signal_chain,
    "budget-split": budget_split,
    "phrase-grid": phrase_grid,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in DIAGRAMS.items():
        path = os.path.join(OUT, name + ".svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn())
        print("wrote", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
