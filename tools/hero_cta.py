#!/usr/bin/env python3
"""Differentiate the hero action row per section instead of repeating two buttons."""
import glob
import re

ACTIONS = {
    "controllers": ('best-dj-controllers-2026.html', 'See the 2026 picks'),
    "software": ('best-dj-software.html', 'Compare platforms'),
    "gear": ('dj-gear-hub.html', 'Open the gear hub'),
    "skills": ('how-to-mix-music-beginners.html', 'Start with mixing'),
    "producer": ('best-daw-for-music-production.html', 'Compare DAWs'),
    "start": ('beginner-dj-setup-guide-2026.html', 'Build a first setup'),
    "general": ('all-dj-guides.html', 'Browse all guides'),
    "site": ('all-dj-guides.html', 'Browse all guides'),
}

for path in sorted(glob.glob("*.html")):
    src = open(path, encoding="utf-8").read()
    if 'data-cta="varied"' in src:
        continue
    body = re.search(r"<body([^>]*)>", src)
    if not body:
        continue
    cat = "general"
    for token in ACTIONS:
        if "category-" + token in body.group(1):
            cat = token
            break
    href, label = ACTIONS[cat]
    row = re.search(r'<div class="hero-ctas">.*?</div>', src, re.S)
    if not row:
        continue
    new_row = (
        '<div class="hero-ctas" data-cta="varied">'
        '<a class="btn" href="%s">%s</a>'
        '<a class="btn btn-secondary" href="editorial-standards.html">How we research</a>'
        "</div>" % (href, label)
    )
    src = src[: row.start()] + new_row + src[row.end():]
    open(path, "w", encoding="utf-8").write(src)
print("hero CTAs varied")
