#!/usr/bin/env python3
"""Replace the one-size-fits-all "before you buy" block with category-specific checks.

The same five DJ-controller checks (software unlock, DVS, booth outputs) used to
appear on headphone pages, DAW reviews and music-distribution comparisons, where
they make no sense. Each page now gets the checks that apply to what it sells.
"""
import glob
import re

SETS = {
    "dj-hardware": {
        "intro": "Price is the easy part. These are the checks that decide whether the purchase still looks sensible six months in.",
        "items": [
            ("Software fit", "Confirm the exact model unlocks or works with the software and version you use — not just the brand family. Licence tiers change between hardware generations."),
            ("Connections", "Match the outputs to what you plug into: RCA, TRS, XLR, booth out. Adapters cost money and add failure points."),
            ("Feel before specs", "Jog wheels, faders and pitch range matter more than the feature list. If you cannot try it, read the return policy first."),
            ("Upgrade path", "If you plan to add a second deck, a DVS setup or a PA, check that this purchase does not need replacing to get there."),
            ("Total cost", "Add the case, cables, stand and any software upgrade. The shelf price is rarely the whole number."),
        ],
    },
    "headphones": {
        "intro": "Headphones are the part of the rig you replace most often. These are the checks that separate a pair that lasts from a pair that annoys you.",
        "items": [
            ("Isolation first", "Closed-back cups and a firm clamp matter more than frequency response when a monitor is pointed at your head."),
            ("Loud enough, not distorted", "High sensitivity means your phone or controller can drive them without clipping. Impedance tells you whether you need an amp."),
            ("Replaceable parts", "Earpads, cables and headbands wear out. If none of them are replaceable, the headphone has a fixed lifespan."),
            ("Comfort at hour three", "Clamp force and weight decide whether you can wear them for a five-hour set. Try before you commit if you can."),
            ("The connector", "A 3.5 mm plug with a screw adapter beats a fixed quarter-inch cable you cannot replace."),
        ],
    },
    "turntables": {
        "intro": "Turntables and cartridges are long-term purchases. These checks decide whether the deck will still be serviceable in ten years.",
        "items": [
            ("Drive type", "Direct drive holds pitch under scratching; belt drive does not. For DJ use, this is not a preference."),
            ("Adjustable everything", "Counterweight, anti-skate and arm height should all be adjustable. Fixed arms limit which cartridges you can use."),
            ("Stylus and tracking force", "A stylus you can replace, at a tracking force the record can take, is the difference between wear and damage."),
            ("Spare parts", "Check that tonearm parts, feet and cables are still available before buying an older model."),
            ("The rest of the chain", "A good cartridge into a poor phono stage is wasted money. Budget for the preamp if your mixer does not have one."),
        ],
    },
    "monitors": {
        "intro": "Monitors are only as good as the room they sit in. These are the checks that matter before you spend more on speakers.",
        "items": [
            ("Room before speaker", "A small untreated room limits what any monitor can do. Placement and a little treatment give more improvement than an upgrade."),
            ("Size for your desk", "A five-inch driver suits a small room; an eight-inch driver in a bedroom produces boom you cannot fix with EQ."),
            ("Connections", "Check for balanced inputs (XLR or TRS) and whether you need a volume controller or an interface to drive them."),
            ("Rear porting", "Rear-ported cabinets need space behind them. If the desk is against a wall, front-ported designs are easier to live with."),
            ("The upgrade trap", "Better monitors expose bad rooms rather than fixing them. Treat the room before the next pair."),
        ],
    },
    "software": {
        "intro": "DJ software is a subscription, a hardware unlock or both. These checks decide what you are actually committing to.",
        "items": [
            ("How it unlocks", "Some licences come with hardware, some are subscriptions, some are one-off purchases. Confirm which one you are buying."),
            ("Cost over three years", "A subscription looks cheap monthly and expensive across a platform's lifespan. Do the multiplication before deciding."),
            ("Library portability", "Cue points, loops and grids rarely transfer between platforms. Check how much of your preparation would be stranded."),
            ("Hardware support", "Verify your exact controller is on the supported list — and that the features you want are not locked to a higher tier."),
            ("Offline behaviour", "Streaming integration is not a music library. Confirm what happens to your sets when the connection drops."),
        ],
    },
    "production": {
        "intro": "Production software is a decade-long relationship. These are the checks that matter more than the feature list.",
        "items": [
            ("Workflow match", "The best DAW is the one whose default way of working matches how you write. Try a demo before you commit."),
            ("Edition limits", "Track counts, bundled instruments and export options differ between editions. Check what the version you can afford actually includes."),
            ("Upgrade pricing", "Some DAWs charge for major versions, some do not. That difference is worth hundreds over five years."),
            ("Plugin compatibility", "Confirm the formats your DAW supports (VST3, AU, AAX) match the plugins you already own."),
            ("CPU and stability", "Check the system requirements against your machine, and search for known issues with your audio interface."),
        ],
    },
    "business": {
        "intro": "Distribution and sample services are contracts, not purchases. These are the terms that actually matter.",
        "items": [
            ("Who owns the master", "You should keep ownership of your recordings. Read the clause that says so — or the one that does not."),
            ("Royalty split and fees", "Compare the percentage you keep against the annual fee, including per-release charges and add-ons."),
            ("Takedowns and leaving", "Check what happens to your releases if you stop paying or move to another service."),
            ("Payout thresholds", "A distributor that holds your money until a minimum balance is reached is a different deal from one that pays monthly."),
            ("Rights and licensing", "For sample libraries, confirm the licence covers commercial releases and that the sounds are cleared for streaming."),
        ],
    },
}

RULES = [
    ("headphones", ("headphone",)),
    ("turntables", ("turntable", "cartridge", "vinyl", "scratch")),
    ("monitors", ("monitor", "speaker")),
    ("business", ("distribution", "distrokid", "amuse", "tunecore", "sample", "splice", "loopmasters", "landr", "soundcloud", "bandcamp", "beatport", "traxsource", "music-store", "courses")),
    ("production", ("daw", "ableton", "fl-studio", "logic", "production", "plugin", "midi", "komplete")),
    ("software", ("software", "serato", "rekordbox", "traktor", "djay", "virtual-dj", "spotify", "apple-music", "ipad", "apps")),
]


def category(stem):
    for name, keys in RULES:
        if any(k in stem for k in keys):
            return name
    return "dj-hardware"


def main():
    changed = 0
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()
        if "Before you buy: five quick checks" not in src:
            continue
        data = SETS[category(path[:-5])]
        rows = "".join(
            f'<div class="format-action-row"><strong>{title}</strong><span>{text}</span></div>'
            for title, text in data["items"]
        )
        block = (
            '<section class="article-section buy-check" data-filler="checked">\n'
            "<h2>Before you buy: five quick checks</h2>\n"
            f'<p>{data["intro"]}</p>\n'
            f'<div class="format-action-table">{rows}</div>\n'
            "</section>\n"
        )
        new = re.sub(
            r'<section[^>]*class="[^"]*buy-check[^"]*"[^>]*>\s*<h2>Before you buy: five quick checks</h2>.*?</section>\s*',
            block,
            src,
            count=1,
            flags=re.S,
        )
        if new != src:
            open(path, "w", encoding="utf-8").write(new)
            changed += 1
    print("buy-check sections tailored on", changed, "pages")


if __name__ == "__main__":
    main()
