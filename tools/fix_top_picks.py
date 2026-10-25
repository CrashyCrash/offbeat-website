#!/usr/bin/env python3
"""Make every "Our top pick" card point at the product it names.

The automated pass reused a single affiliate query per page, so a card announcing
the Sony MDR-7506 could send readers to an Audio-Technica listing. This script
reads the product named on the card and rewrites the button (label and search
query) to match it, leaving the affiliate tag intact.
"""
import glob
import re
import urllib.parse

CARD = re.compile(
    r'(<div class="top-pick-section">.*?<div class="top-pick-name">)(.*?)(</div>.*?<a class="btn btn-amazon" href=")([^"]*)("(?:[^>]*)>)(.*?)(</a>)',
    re.S,
)

# Product names that need a cleaner retail search string.
ALIASES = {
    "Pioneer DDJ-FLX4 Starter Kit": "Pioneer DDJ-FLX4",
    "Ableton Live Intro": "Ableton Live 12 Intro",
    "Udemy: Complete 2026 DJ Masterclass": "Pioneer DDJ-FLX4",
    "Akai MPK Mini MK3 MIDI Controller": "Akai MPK Mini MK3",
    "Roland SP-404 MKII Sampler": "Roland SP-404 MKII",
}


def search_query(name):
    name = ALIASES.get(name, name)
    return urllib.parse.quote_plus(name)


def main():
    changed = 0
    for path in sorted(glob.glob("*.html")):
        src = open(path, encoding="utf-8").read()

        def fix(match):
            name = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not name:
                return match.group(0)
            label = "Search " + ALIASES.get(name, name).replace("Pioneer DJ ", "Pioneer ").replace("Pioneer ", "Pioneer DJ ", 1) if False else "Search " + ALIASES.get(name, name) + " on Amazon →"
            href = "https://www.amazon.com/s?k=" + search_query(name) + "&tag=offbeatdj-20"
            return (match.group(1) + match.group(2) + match.group(3) + href +
                    match.group(5) + label + match.group(7))

        new = CARD.sub(fix, src)
        if new != src:
            open(path, "w", encoding="utf-8").write(new)
            changed += 1
    print("top-pick cards realigned on", changed, "pages")


if __name__ == "__main__":
    main()
