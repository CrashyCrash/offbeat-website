#!/usr/bin/env python3
"""Site-wide structural redesign pass for the Offbeat static site.

Idempotent: pages already carrying the new header are skipped.
Applies the shared shell (header, breadcrumbs, hero layout, footer, search)
and swaps remote/placeholder imagery for the local editorial photo set.
"""
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

IMG = "assets/img/editorial/"
FONT_PRELOAD = (
    '<link rel="preload" href="assets/fonts/inter-latin-wght-normal.woff2" as="font" '
    'type="font/woff2" crossorigin>'
    '<link rel="preload" href="assets/fonts/space-grotesk-latin-wght-normal.woff2" as="font" '
    'type="font/woff2" crossorigin>'
)

HUB = {
    "controllers": ("controllers", "dj-controllers-hub.html", "Controllers"),
    "software": ("software", "dj-software-hub.html", "Software"),
    "gear": ("gear", "dj-gear-hub.html", "Gear"),
    "skills": ("skills", "dj-skills-performance-hub.html", "Skills & Performance"),
    "producer": ("software", "music-production.html", "Production"),
    "start": ("start", "beginner-dj-hub.html", "Start DJing"),
    "general": ("general", "index.html", "Guides"),
    "site": ("site", "about.html", "About"),
}

# Topic-driven photo choice. First match wins.
PHOTO_RULES = [
    (("headphone",), "headphones-hero"),
    (("turntable", "cartridge", "vinyl", "scratch"), "vinyl-hero"),
    (("mixer",), "mixer-hero"),
    (("wedding", "festival", "gig", "mobile", "stand", "accessor", "checklist", "maintenance", "stores"), "mobile-dj-hero"),
    (("controller", "ddj", "flx", "xdj", "cdj", "grv6", "mixtrack", "rane", "prime", "sc6000", "standalone", "inpulse", "party-mix"), "controller-macro"),
    (("laptop", "software", "serato", "rekordbox", "traktor", "djay", "virtual-dj", "app", "ipad", "spotify", "compatibility", "usb", "audio-interface", "connect", "setup"), "software-desk"),
    (("headphones",), "headphones-hero"),
    (("daw", "ableton", "fl-studio", "logic", "production", "plugin", "midi", "komplete", "monitor", "sample", "splice", "landr", "courses"), "production-hero"),
    (("distribution", "distrokid", "amuse", "tunecore", "soundcloud", "bandcamp", "beatport", "traxsource", "promote", "youtube"), "gear-flatlay"),
    (("skill", "beatmatch", "mix", "record", "learn", "become", "start", "beginner", "hub"), "skills-hero"),
]
CATEGORY_PHOTO = {
    "controllers": "controller-macro",
    "software": "software-desk",
    "gear": "gear-flatlay",
    "skills": "skills-hero",
    "producer": "production-hero",
    "start": "skills-hero",
    "general": "booth-wide",
    "site": "booth-wide",
}


def photo_for(slug, category):
    for keys, photo in PHOTO_RULES:
        if any(k in slug for k in keys):
            return photo
    return CATEGORY_PHOTO.get(category, "booth-wide")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def category_of(body_classes):
    for token in ("controllers", "software", "gear", "skills", "producer", "start", "general", "site"):
        if "category-" + token in body_classes:
            return token
    return "general"


def text_of(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def short_label(title, limit=42):
    label = title.split(":")[0].split("—")[0].split("(")[0].strip()
    if len(label) > limit:
        label = label[: limit - 1].rsplit(" ", 1)[0] + "…"
    return label


def nav_html(slug):
    links = [
        ("beginner-dj-hub.html", "Start here"),
        ("dj-controllers-hub.html", "Controllers"),
        ("dj-software-hub.html", "Software"),
        ("dj-gear-hub.html", "Gear"),
        ("dj-skills-performance-hub.html", "Skills"),
        ("all-dj-guides.html", "All guides"),
    ]
    items = "".join(
        '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == slug else "", label)
        for href, label in links
    )
    return (
        '<nav aria-label="Primary navigation"><div class="nav-inner">'
        '<a class="nav-brand" href="index.html"><span class="brand-mark" aria-hidden="true"></span>'
        '<span class="brand-word">Offbeat<em>.</em></span></a>'
        '<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="primary-nav">'
        '<span class="nav-toggle-icon" aria-hidden="true"></span>Menu</button>'
        '<div class="nav-links" id="primary-nav">'
        + items
        + '<button class="nav-search" type="button" data-search-open aria-label="Search guides">'
        '<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="7" cy="7" r="4.6" '
        'stroke="currentColor" stroke-width="1.6"/><path d="M10.6 10.6 14 14" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round"/></svg>Search<kbd>/</kbd></button>'
        "</div></div></nav>"
    )


def search_overlay_html():
    return (
        '<div class="search-overlay" id="site-search" hidden>'
        '<div class="search-panel" role="dialog" aria-modal="true" aria-label="Search Offbeat guides">'
        '<div class="search-head">'
        '<input type="search" placeholder="Search controllers, software, setup guides…" '
        'aria-label="Search guides" data-search-input autocomplete="off">'
        '<button class="search-close" type="button" data-search-close>Esc</button></div>'
        '<p class="search-status" data-search-status>Popular guides</p>'
        '<ul class="search-results" data-search-results></ul>'
        "</div></div>"
    )


def footer_html():
    return (
        '<div class="footer-nav-grid footer-nav-grid--compact">'
        '<div class="footer-col footer-brand-col">'
        '<a class="nav-brand" href="index.html"><span class="brand-mark" aria-hidden="true"></span>'
        '<span class="brand-word">Offbeat<em>.</em></span></a>'
        "<p>Independent DJ gear, software and skills guides for people who care how a set actually sounds. "
        "We research manufacturer documentation, software support pages and retailer listings — then say plainly "
        "what we know and what we do not.</p></div>"
        '<div class="footer-col"><h4>Start</h4><ul>'
        '<li><a href="beginner-dj-hub.html">Start DJing</a></li>'
        '<li><a href="how-to-start-djing.html">How to start</a></li>'
        '<li><a href="beginner-dj-setup-guide-2026.html">First setup</a></li>'
        '<li><a href="best-budget-dj-equipment.html">Budget rigs</a></li>'
        '<li><a href="dj-equipment-checklist.html">Gear checklist</a></li></ul></div>'
        '<div class="footer-col"><h4>Controllers</h4><ul>'
        '<li><a href="best-dj-controllers-2026.html">Best controllers 2026</a></li>'
        '<li><a href="best-dj-controllers-for-beginners.html">For beginners</a></li>'
        '<li><a href="best-dj-controllers-under-500-2026.html">Under $500</a></li>'
        '<li><a href="best-standalone-dj-systems.html">Standalone systems</a></li>'
        '<li><a href="controller-software-compatibility-matrix.html">Compatibility matrix</a></li></ul></div>'
        '<div class="footer-col"><h4>Software</h4><ul>'
        '<li><a href="best-dj-software.html">Best DJ software</a></li>'
        '<li><a href="best-free-dj-software-2026.html">Free options</a></li>'
        '<li><a href="serato-vs-rekordbox-vs-traktor.html">Serato vs rekordbox vs Traktor</a></li>'
        '<li><a href="rekordbox-review.html">rekordbox review</a></li>'
        '<li><a href="how-to-dj-with-spotify.html">DJ with Spotify</a></li></ul></div>'
        '<div class="footer-col"><h4>Gear</h4><ul>'
        '<li><a href="best-dj-headphones-2026.html">Headphones</a></li>'
        '<li><a href="best-dj-mixers-2026.html">Mixers</a></li>'
        '<li><a href="best-dj-turntables-2026.html">Turntables</a></li>'
        '<li><a href="best-dj-laptop-2026.html">Laptops</a></li>'
        '<li><a href="best-dj-monitor-speakers.html">Speakers</a></li></ul></div>'
        '<div class="footer-col"><h4>Skills</h4><ul>'
        '<li><a href="how-to-mix-music-beginners.html">Learn to mix</a></li>'
        '<li><a href="how-to-beatmatch-manually.html">Beatmatch by ear</a></li>'
        '<li><a href="how-to-record-dj-mix.html">Record a mix</a></li>'
        '<li><a href="how-to-get-dj-gigs.html">Get gigs</a></li>'
        '<li><a href="how-to-dj-at-a-wedding.html">Wedding DJing</a></li></ul></div>'
        '<div class="footer-col"><h4>Offbeat</h4><ul>'
        '<li><a href="about.html">About</a></li>'
        '<li><a href="editorial-standards.html">Editorial standards</a></li>'
        '<li><a href="disclosure.html">Affiliate disclosure</a></li>'
        '<li><a href="contact.html">Contact</a></li>'
        '<li><a href="privacy.html">Privacy</a></li></ul></div>'
        "</div>"
        '<div class="footer-bottom"><p>© 2026 Offbeat Inc. Independent DJ and music-production publishing. '
        "Some links are affiliate links — this never changes the price you pay. "
        '<a href="disclosure.html">How that works</a>.</p></div>'
    )


def hero_figure(photo, alt, caption):
    return (
        '<figure class="hero-figure"><img src="%s%s.jpg" alt="%s" width="1408" height="768" '
        'loading="eager" decoding="async"><figcaption>%s</figcaption></figure>'
        % (IMG, photo, html.escape(alt, quote=True), caption)
    )


def clean_meta(meta_html):
    # Drop decorative emoji that render inconsistently across platforms.
    out = re.sub(r'<span>\s*[^\w<]*\s*', "<span>", meta_html)
    return out


def transform(path):
    slug = os.path.basename(path)
    src = read(path)
    if "brand-mark" in src:
        return False
    body_match = re.search(r"<body([^>]*)>", src)
    if not body_match:
        return False
    category = category_of(body_match.group(1))
    photo = photo_for(slug.replace(".html", ""), category)
    hub_slug, hub_href, hub_label = HUB[category]

    title_match = re.search(r"<title>(.*?)</title>", src, re.S)
    raw_title = text_of(title_match.group(1)) if title_match else slug
    core_title = re.sub(r"\s*\|\s*Offbeat Inc\.?$", "", raw_title).strip()

    # ---- header ----
    src = re.sub(r'<nav aria-label="Primary navigation">.*?</nav>', nav_html(slug), src, count=1, flags=re.S)

    # ---- headline / hero reconstruction ----
    hero_match = re.search(r'<section class="hero"[^>]*>(.*?)</section>', src, re.S)
    if hero_match:
        inner = hero_match.group(1)
        eyebrow_match = re.search(r'<span class="hero-eyebrow">(.*?)</span>', inner, re.S)
        eyebrow = text_of(eyebrow_match.group(1)) if eyebrow_match else hub_label
        h1_match = re.search(r"<h1>(.*?)</h1>", inner, re.S)
        h1 = h1_match.group(1) if h1_match else core_title
        h1 = re.sub(r'<span class="gradient-text">(.*?)</span>', r"\1", h1, flags=re.S)
        sub_match = re.search(r'<p class="hero-sub">(.*?)</p>', inner, re.S)
        sub = sub_match.group(1) if sub_match else ""
        meta_match = re.search(r'<div class="hero-meta">(.*?)</div>', inner, re.S)
        meta = clean_meta(meta_match.group(1)) if meta_match else ""
        fig_match = re.search(r"<figure[^>]*>.*?</figure>", inner, re.S)
        existing_fig = fig_match.group(0) if fig_match else ""

        keep_existing = "upload.wikimedia.org" in existing_fig
        if keep_existing:
            figure = existing_fig
            figure = re.sub(r'\s(width|height)="[^"]*"', "", figure)
            figure = figure.replace('loading="eager"', 'loading="eager"')
        else:
            alt = "DJ equipment photographed in low warm light — Offbeat editorial photography"
            caption = "Offbeat editorial photography. Illustrative image, not a photo of the specific product."
            figure = hero_figure(photo, alt, caption)

        hero_copy = (
            '<div class="hero-copy">'
            + '<nav class="crumbs" aria-label="Breadcrumb"><ol>'
            + '<li><a href="index.html">Home</a></li>'
            + '<li><a href="%s">%s</a></li>' % (hub_href, hub_label)
            + "<li>%s</li></ol></nav>" % html.escape(short_label(core_title))
            + '<span class="hero-eyebrow">%s</span>' % eyebrow
            + "<h1>%s</h1>" % h1.strip()
            + '<p class="hero-sub">%s</p>' % sub.strip()
            + ('<div class="hero-meta">%s</div>' % meta.strip() if meta else "")
            + '<div class="hero-ctas">'
            + '<a class="btn btn-secondary" href="editorial-standards.html">How we research</a>'
            + '<a class="btn btn-secondary" href="%s">%s hub</a>' % (hub_href, hub_label)
            + "</div></div>"
        )
        disclosure_match = re.search(
            r'<p class="hero-disclosure[^"]*">.*?</p>', inner, re.S
        )
        disclosure = disclosure_match.group(0) if disclosure_match else ""
        new_hero = (
            '<section class="hero" id="top"><div class="hero-inner has-media">'
            + hero_copy
            + figure
            + "</div></section>"
        )
        src = src[: hero_match.start()] + new_hero + src[hero_match.end():]
        # Place disclosure as a slim strip directly after the hero grid.
        if disclosure:
            src = src.replace(
                new_hero,
                new_hero
                + '<div class="hero-foot">'
                + disclosure
                + "</div>",
                1,
            )

    # ---- title / social metadata ----
    short = core_title if len(core_title) <= 52 else short_label(core_title, 52)
    new_title = "%s | Offbeat" % (core_title if len(core_title) <= 60 else short)
    src = re.sub(r"<title>.*?</title>", "<title>%s</title>" % new_title, src, count=1, flags=re.S)
    src = re.sub(
        r'(<meta content=")[^"]*(" property="og:title">)',
        lambda m: m.group(1) + html.escape(new_title, quote=True) + m.group(2),
        src,
    )
    src = re.sub(
        r'(<meta content=")[^"]*(" name="twitter:title">)',
        lambda m: m.group(1) + html.escape(new_title, quote=True) + m.group(2),
        src,
    )
    og_image = "https://offbeatinc.com/%s%s.jpg" % (IMG, photo)
    src = re.sub(
        r'(<meta content=")[^"]*(" property="og:image">)',
        lambda m: m.group(1) + og_image + m.group(2),
        src,
    )
    src = re.sub(
        r'(<meta content=")[^"]*(" name="twitter:image">)',
        lambda m: m.group(1) + og_image + m.group(2),
        src,
    )
    if 'name="twitter:image"' not in src and 'property="og:image"' in src:
        src = src.replace(
            '<meta content="%s" property="og:image">' % og_image,
            '<meta content="%s" property="og:image"><meta content="%s" name="twitter:image">'
            % (og_image, og_image),
        )
    if 'name="theme-color"' not in src:
        src = src.replace("</head>", '<meta name="theme-color" content="#08080b">%s</head>' % FONT_PRELOAD, 1)

    # ---- shared script ----
    if "assets/site.js" not in src:
        src = src.replace("</body>", '<script defer src="assets/site.js"></script>%s</body>' % search_overlay_html(), 1)

    # ---- footer ----
    src = re.sub(r'<div class="footer-nav-grid[^"]*">.*?</div><div class="footer-bottom">.*?</div>',
                 footer_html(), src, count=1, flags=re.S)

    # ---- decorative emoji icons -> removed ----
    src = re.sub(r'\s*<(span|div) class="(card-icon|hub-card-icon)">[^<]*</\1>', "", src)

    # ---- section heads with a trailing "see all" link ----
    src = re.sub(
        r'<div>\s*(<h2[^>]*>.*?</h2>)\s*(<a [^>]*>[^<]*</a>)\s*</div>',
        r'<div class="section-head">\1\2</div>',
        src,
        flags=re.S,
    )

    write(path, src)
    return True


def main():
    changed = 0
    for path in sorted(glob.glob("*.html")):
        if path == "index.html":
            continue
        if transform(path):
            changed += 1
    print("pages updated:", changed)


if __name__ == "__main__":
    sys.exit(main())
