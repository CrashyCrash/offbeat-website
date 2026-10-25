#!/usr/bin/env python3
"""Build the site index (search + library page) from the published HTML.

Extracts the human-facing title, meta description and section for every page,
then writes:
  * assets/search-index.json  — used by the header search dialog
  * all-dj-guides.html        — the browsable library page
Run after any page is added or retitled.
"""
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FEATURED = {
    "best-dj-controllers-2026.html",
    "best-dj-headphones-2026.html",
    "serato-vs-rekordbox-vs-traktor.html",
    "beginner-dj-hub.html",
    "best-dj-software-beginners-2026.html",
    "best-budget-dj-equipment.html",
    "how-to-mix-music-beginners.html",
    "dj-gear-hub.html",
    "build-your-dj-setup.html",
}

# (group id, heading, blurb, keyword tests). First match wins.
GROUPS = [
    ("start", "Start here", "First rigs, first steps and the questions people ask before spending anything.",
     ("beginner", "how-to-start", "learn-djing", "first", "equipment-checklist", "equipment-beginners",
      "budget", "without-a-controller", "become-a-dj", "skills-learning-path", "setup-guide")),
    ("production", "Production & distribution",
     "DAWs, plugins, sample libraries and getting finished music onto streaming services.",
     ("daw", "ableton", "fl-studio", "logic", "production", "plugin", "midi", "komplete", "monitor",
      "sample", "splice", "landr", "distribution", "distrokid", "amuse", "tunecore", "soundcloud",
      "bandcamp", "beatport", "traxsource", "audio-interface")),
    ("controllers", "Controllers, decks & DJ systems",
     "One-box setups, media players and the hardware that connects them to your software.",
     ("controller", "ddj", "flx", "xdj", "cdj", "grv6", "mixtrack", "rane", "prime", "standalone",
      "motorized", "inpulse", "party-mix", "sc6000", "no-laptop")),
    ("software", "DJ software",
     "Platform choice, licensing, streaming support and how software pairs with hardware.",
     ("software", "serato", "rekordbox", "traktor", "djay", "virtual-dj", "spotify", "apple-music",
      "compatibility", "vinyl-scratch", "dvs", "apps-ipad")),
    ("gear", "Gear & accessories",
     "Everything around the decks: monitoring, mixing, playback media, stands and maintenance.",
     ("headphone", "mixer", "turntable", "cartridge", "laptop", "usb", "speaker", "stand",
      "maintenance", "accessor", "festival", "stores", "gear-hub", "checklist", "recording")),
    ("skills", "Skills, performance & gigs",
     "Mixing technique, recording, promotion and the business of playing out.",
     ("skill", "mixing", "mix-", "beatmatch", "gig", "wedding", "record", "promote", "youtube",
      "performing", "courses")),
    ("site", "About Offbeat", "Who writes this, how guides are researched and how we make money.",
     ("about", "contact", "privacy", "disclosure", "editorial", "404", "all-dj-guides")),
]


def clean(text):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text))).strip()


# Pages whose subject is not obvious from the slug alone.
OVERRIDES = {
    "controller-software-compatibility-matrix": "software",
    "best-dj-controllers-for-beginners": "controllers",
    "best-dj-controllers-for-serato": "controllers",
    "best-dj-controllers-for-rekordbox": "controllers",
    "best-budget-dj-equipment": "start",
    "best-dj-software-beginners-2026": "software",
    "best-daw-for-music-production": "production",
    "music-production-software-free": "production",
    "how-to-connect-dj-controller-to-speakers": "start",
    "dj-equipment-checklist": "start",
    "dj-equipment-beginners": "start",
    "build-your-dj-setup": "start",
    "dj-glossary": "start",
    "beatmatch-trainer": "start",
    "numark-scratch-review": "controllers",
    "ddj-flx2-review": "controllers",
    "ddj-grv6-review": "controllers",
    "rane-one-review": "controllers",
    "denon-prime-go-review": "controllers",
    "denon-sc6000-review": "controllers",
    "pioneer-cdj-3000-review": "controllers",
    "pioneer-ddj-flx10-review": "controllers",
    "pioneer-ddj-flx4-review": "controllers",
    "how-to-become-a-dj": "skills",
    "how-to-get-dj-gigs": "skills",
    "how-to-promote-dj-mixes": "skills",
    "how-to-record-dj-mix": "skills",
}


def group_for(slug):
    stem = slug[:-5]
    if stem in OVERRIDES:
        gid = OVERRIDES[stem]
        for g in GROUPS:
            if g[0] == gid:
                return g[0], g[1], g[2]
    for gid, heading, blurb, keys in GROUPS:
        if any(k in stem for k in keys):
            return gid, heading, blurb
    return "start", "Start here", "First rigs, first steps and the questions people ask before spending anything."


def main():
    items = []
    for path in sorted(glob.glob("*.html")):
        if path in ("index.html", "404.html"):
            continue
        src = open(path, encoding="utf-8").read()
        title_match = re.search(r"<title>(.*?)</title>", src, re.S)
        title = clean(title_match.group(1)) if title_match else path
        title = re.sub(r"\s*\|\s*Offbeat( Inc\.?)?$", "", title).strip()
        desc_match = re.search(r'<meta content="([^"]*)" name="description">', src)
        desc = html.unescape(desc_match.group(1)) if desc_match else ""
        if not desc:
            hero = re.search(r'<p class="hero-sub">(.*?)</p>', src, re.S)
            desc = clean(hero.group(1)) if hero else ""
        if len(desc) > 150:
            desc = desc[:150].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        gid, heading, blurb = group_for(path)
        items.append({
            "u": path,
            "t": title,
            "d": desc,
            "c": heading,
            "g": gid,
            "k": (title + " " + desc).lower(),
            "f": path in FEATURED,
        })

    with open("assets/search-index.json", "w", encoding="utf-8") as handle:
        json.dump(items, handle, ensure_ascii=False, separators=(",", ":"))
    print("index entries:", len(items))

    # ---------- library page ----------
    order = [g[0] for g in GROUPS]
    headings = {g[0]: (g[1], g[2]) for g in GROUPS}
    by_group = {gid: [] for gid in order}
    for item in items:
        if item["u"] == "all-dj-guides.html":
            continue
        by_group[item["g"]].append(item)

    chips = "".join(
        '<button class="chip-filter%s" type="button" data-filter="%s" aria-pressed="%s">%s <span>%d</span></button>'
        % (" is-active" if index == 0 else "", gid, "true" if index == 0 else "false",
           headings[gid][0], len(by_group[gid]))
        for index, gid in enumerate(order)
        if by_group[gid]
    )

    sections = []
    for gid in order:
        entries = sorted(by_group[gid], key=lambda i: i["t"].lower())
        if not entries:
            continue
        rows = "".join(
            '<li class="library-item" data-group="%s" data-terms="%s"><a href="%s">'
            "<strong>%s</strong><span>%s</span></a></li>"
            % (gid, html.escape(item["k"], quote=True), item["u"],
               html.escape(item["t"]), html.escape(item["d"]))
            for item in entries
        )
        sections.append(
            '<section class="article-section library-group" id="%s" data-group="%s">'
            '<div class="section-head"><h2>%s</h2><span class="library-count">%d guides</span></div>'
            '<p class="section-sub">%s</p><ul class="library-list">%s</ul></section>'
            % (gid, gid, headings[gid][0], len(entries), headings[gid][1], rows)
        )

    template = open("tools/library-template.html", encoding="utf-8").read()
    page = template.replace("<!--CHIPS-->", chips).replace("<!--GROUPS-->", "\n".join(sections))
    page = page.replace("<!--TOTAL-->", str(len(items)))
    with open("all-dj-guides.html", "w", encoding="utf-8") as handle:
        handle.write(page)
    print("library written")


if __name__ == "__main__":
    main()
