#!/usr/bin/env python3
"""Assign a topical editorial photograph to every page's hero, and reuse it for social cards.

Hand-authored rule table rather than a random assignment: each image is used for
the subject it actually depicts, so a headphones page shows headphones and a
wedding page shows a wedding rig. Alt text lives here too, so the description and
the picture cannot drift apart.
"""
import glob
import re

ALT = {
    "booth-wide.jpg": "A DJ booth with a mixer and decks silhouetted against a crowd under blue stage light",
    "controller-macro.jpg": "Close-up of a controller jog wheel, pads and knobs in warm light",
    "gear-flatlay.jpg": "Headphones, a USB drive, cables and a hard case arranged on a dark surface",
    "headphones-hero.jpg": "Closed-back DJ headphones hanging against a dark wall",
    "hero-breakdown.jpg": "A laptop showing an arrangement timeline beside a MIDI keyboard on a lamp-lit desk",
    "hero-gig-small.jpg": "A DJ mixing on a controller in a small bar while a crowd dances under string lights",
    "hero-wedding.jpg": "Wedding reception speakers on stands with a mixer on a table and guests dancing under festoon lights",
    "mixer-hero.jpg": "Close-up of a mixer's channel faders lit by warm light",
    "mobile-dj-hero.jpg": "A small sound system and decks set up in a dark venue with pink and blue light",
    "production-hero.jpg": "A production studio desk with a modular synth, keyboard and studio monitors",
    "skills-hero.jpg": "A DJ's hands on a mixer in front of a crowd in a dark club",
    "software-desk.jpg": "A laptop showing a DJ software waveform on a wooden desk in low light",
    "vinyl-hero.jpg": "A tonearm and stylus tracking a record on a turntable",
}

# (image, filename keywords). First match wins, so put the specific topics first.
RULES = [
    ("hero-wedding.jpg", ("wedding", "mobile-dj", "party-mix")),
    ("hero-gig-small.jpg", ("get-dj-gigs", "promote-dj-mixes", "festival", "become-a-dj")),
    ("hero-breakdown.jpg", ("daw", "ableton", "fl-studio", "logic", "production", "plugin",
                            "midi", "komplete", "sample", "landr", "splice", "loopmasters",
                            "distribution", "distrokid", "amuse", "tunecore", "beatport",
                            "traxsource", "soundcloud", "bandcamp")),
    ("production-hero.jpg", ("monitor", "speaker", "studio")),
    ("vinyl-hero.jpg", ("turntable", "cartridge", "vinyl", "scratch", "dvs", "music-stores")),
    ("headphones-hero.jpg", ("headphone",)),
    ("mixer-hero.jpg", ("mixer",)),
    ("booth-wide.jpg", ("standalone", "cdj", "xdj", "sc6000", "prime", "club", "compatibility",
                        "compatibility-matrix")),
    ("controller-macro.jpg", ("controller", "ddj", "flx", "grv6", "rane", "inpulse", "mixtrack",
                              "numark", "buying-journey")),
    ("gear-flatlay.jpg", ("connect", "cable", "audio-interface", "equipment", "accessor",
                          "stand-", "maintenance", "checklist", "budget", "setup",
                          "build-your-dj-setup", "gear-hub")),
    ("software-desk.jpg", ("laptop", "usb", "software", "serato", "rekordbox", "traktor", "djay",
                           "virtual-dj", "spotify", "apple-music", "ipad", "apps", "software-faq",
                           "dvs")),
    ("skills-hero.jpg", ("beatmatch", "how-to-mix", "skills", "learn-djing", "start-djing",
                         "record-dj-mix", "record-dj", "courses", "skills-learning")),
]

DEFAULT = "booth-wide.jpg"


def pick_image(stem):
    for image, keys in RULES:
        if any(key in stem for key in keys):
            return image
    return DEFAULT


def main():
    changed = 0
    for path in sorted(glob.glob("*.html")):
        if path == "index.html":
            continue
        src = open(path, encoding="utf-8").read()
        figure = re.search(r'<figure class="hero-figure">.*?</figure>', src, re.S)
        if not figure:
            continue
        image = pick_image(path[:-5])
        block = figure.group(0)
        new_block = re.sub(r'(<img [^>]*src=")assets/img/editorial/[a-z-]+\.jpg(")',
                           lambda m: m.group(1) + "assets/img/editorial/" + image + m.group(2), block, count=1)
        new_block = re.sub(r'(<img [^>]*alt=")[^"]*(")',
                           lambda m: m.group(1) + ALT[image] + m.group(2), new_block, count=1)
        if new_block == block:
            continue
        src = src[:figure.start()] + new_block + src[figure.end():]
        # Social cards follow the hero, so a shared link shows the right subject.
        url = "https://offbeatinc.com/assets/img/editorial/" + image
        src = re.sub(r'<meta content="[^"]*" property="og:image">',
                     f'<meta content="{url}" property="og:image">', src, count=1)
        src = re.sub(r'<meta content="[^"]*" name="twitter:image">',
                     f'<meta content="{url}" name="twitter:image">', src, count=1)
        open(path, "w", encoding="utf-8").write(src)
        changed += 1
    print("hero images set on", changed, "pages")


if __name__ == "__main__":
    main()
