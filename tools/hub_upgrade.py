#!/usr/bin/env python3
"""Give the five category hubs a real landing-page opening.

Each hub currently jumps from a one-line hero straight into dense card grids and
internal-sounding notes ("routes beginners ... into the right page", "affiliate
merchant priority"). This adds an editorially written lead paragraph, a stat row
and a strip of photo cards linking to the hub's strongest guides, and removes the
redundant "decision shortcut" box that repeated the hero.
"""
import re

HERO = {
    "dj-gear-hub.html": dict(
        eyebrow="Gear",
        h1="Every piece of gear in a DJ rig, explained",
        sub="Headphones, mixers, turntables, speakers and the accessories that stop a set falling apart. Each guide covers one part of the rig, says what matters at each price and what you can safely skip.",
        meta=["14 gear buying guides", "Reviewed October 2026"],
        image="assets/img/editorial/mixer-hero.jpg",
        alt="Illuminated channel faders and level meters on a club mixer",
        lead="A DJ setup is five separate purchases that need to work together: something to play from, something to control it, something to listen on, something to play through, and a bag of small things that keep it alive. Buying them in the wrong order is the most common way people waste money at the start.",
        stats=[("7", "gear categories"), ("4", "price tiers covered"), ("2026", "current buying notes"), ("0", "sponsored placements")],
        cards=[
            ("best-dj-headphones-2026.html", "Headphones", "Best DJ Headphones 2026", "Isolation, clamp force, cable design and whether you can buy spare parts in two years.", "headphones-hero.jpg", "Black closed-back DJ headphones hanging on a dark wall"),
            ("best-dj-mixers-2026.html", "Mixers", "Best DJ Mixers 2026", "Channel count, fader feel, effects and the DVS question, from home mixers to club standard.", "mixer-hero.jpg", "Close-up of illuminated channel faders and level meters"),
            ("best-dj-turntables-2026.html", "Turntables", "Best DJ Turntables 2026", "Torque, plinth weight and which decks survive scratch practice without a rebuild.", "vinyl-hero.jpg", "A tonearm and stylus tracking a vinyl record"),
            ("best-dj-laptop-2026.html", "Laptops", "Best DJ Laptops 2026", "Chip generations, thermals, ports and the software support that actually matters at 2am.", "software-desk.jpg", "A dark desk with a laptop and small controller"),
        ],
    ),
    "dj-software-hub.html": dict(
        eyebrow="Software",
        h1="Choose a DJ platform once, and choose it properly",
        sub="Most DJs stay on one platform for years, and the licence bundled with your first controller usually decides which. These guides explain what each platform costs, what it unlocks and where it stops.",
        meta=["6 platforms compared", "Reviewed October 2026"],
        image="assets/img/editorial/software-desk.jpg",
        alt="A laptop showing an audio waveform beside a MIDI keyboard in a dark room",
        lead="Software is the decision that outlives your hardware. A controller lasts three or four years; the library you build inside a platform can last a decade. That is the reason we compare platforms on licensing, hardware unlocks and library portability first, and on effect lists second.",
        stats=[("6", "platforms compared"), ("3", "free tiers that are usable"), ("2026", "licence terms checked"), ("10", "software guides")],
        cards=[
            ("best-dj-software.html", "Overview", "Best DJ Software 2026", "The shortlist, ranked by what you actually need rather than by feature counts.", "software-desk.jpg", "DJ software running on a laptop in a dark studio"),
            ("serato-vs-rekordbox-vs-traktor.html", "Comparison", "Serato vs rekordbox vs Traktor", "The three platforms that matter for hardware DJs, compared on workflow and cost of ownership.", "software-desk.jpg", "A laptop and controller in a dim room"),
            ("best-free-dj-software-2026.html", "Free options", "Best Free DJ Software", "What the free tiers genuinely allow, and where the paywall really sits.", "gear-flatlay.jpg", "DJ essentials laid out on a dark surface"),
            ("controller-software-compatibility-matrix.html", "Compatibility", "Controller–software matrix", "Which controllers unlock which licence tier, and which ones quietly leave you paying monthly.", "controller-macro.jpg", "Macro view of a controller jog wheel and pads"),
        ],
    ),
    "dj-controllers-hub.html": dict(
        eyebrow="Controllers",
        h1="Find the controller that fits how you actually play",
        sub="Two channels or four, laptop or standalone, jog wheels or motorised platters. Start from the workflow you want and the budget you have, and the shortlist gets short fast.",
        meta=["25 controller guides", "Reviewed October 2026"],
        image="assets/img/editorial/controller-macro.jpg",
        alt="Macro view of a jog wheel, performance pads and channel faders on a DJ controller",
        lead="\"Best controller\" means nothing without context. A $300 two-channel controller that unlocks Serato DJ Pro is a better buy than a $700 four-channel unit that needs a paid upgrade — unless you are already booked for four-deck sets. Use this hub to pick the category first, then the model.",
        stats=[("5", "current top picks"), ("$99–$1,729", "price range covered"), ("2026", "stock and price notes"), ("8", "in-depth reviews")],
        cards=[
            ("best-dj-controllers-2026.html", "Buying guide", "Best DJ Controllers 2026", "Five current picks ranked by software fit, I/O and workflow, with dated US prices.", "controller-macro.jpg", "Close-up of a controller jog wheel under warm light"),
            ("best-dj-controllers-for-beginners.html", "First controller", "Best Controllers for Beginners", "Decide between FLX2, FLX4, Inpulse and Mixtrack class before spending more.", "controller-macro.jpg", "Controller jog wheel and performance pads"),
            ("best-standalone-dj-systems.html", "No laptop", "Standalone DJ Systems", "USB and SD workflows, built-in screens, and the compromise you make without a laptop.", "booth-wide.jpg", "A two-deck booth setup lit by a warm lamp"),
            ("best-motorized-dj-controllers.html", "Scratch & vinyl feel", "Motorised Controllers", "Platter-driven controllers for battle, scratch and vinyl-style timing.", "vinyl-hero.jpg", "A stylus on a spinning vinyl record"),
        ],
    ),
    "dj-skills-performance-hub.html": dict(
        eyebrow="Skills & performance",
        h1="The craft side of DJing",
        sub="Beatmatching by ear, transitions that hold a dancefloor, recording a clean mix and the unglamorous work of getting booked. Technique is what makes the gear worth owning.",
        meta=["8 skills guides", "Reviewed October 2026"],
        image="assets/img/editorial/skills-hero.jpg",
        alt="A DJ's hand on a mixer crossfader with a crowd blurred behind the booth",
        lead="Gear gets the attention, but technique is what people actually hear. The order below is deliberate: tempo first, then phrasing, then recording, then promotion. Skipping ahead usually means learning a habit you have to unlearn later.",
        stats=[("4", "step learning path"), ("8", "skills guides"), ("2026", "current software notes"), ("1", "practice routine")],
        cards=[
            ("how-to-mix-music-beginners.html", "Start here", "How to Mix for Beginners", "Beatmatching, phrasing and EQ explained in the order you should practise them.", "skills-hero.jpg", "Hand on a mixer crossfader in a dark venue"),
            ("how-to-beatmatch-manually.html", "Technique", "Beatmatch by Ear", "The skill that makes every other technique easier, and the one that still gets people hired.", "vinyl-hero.jpg", "A stylus tracking a record groove"),
            ("how-to-record-dj-mix.html", "Recording", "Record a DJ Mix", "Gain staging, routing and export settings for a mix that sounds right on other systems.", "software-desk.jpg", "A laptop and controller set up for recording"),
            ("how-to-get-dj-gigs.html", "Business", "How to Get DJ Gigs", "What promoters want to see, how to approach them, and how to turn sets into bookings.", "mobile-dj-hero.jpg", "A mobile DJ setup with speakers in a dim room"),
        ],
    ),
    "beginner-dj-hub.html": dict(
        eyebrow="Start here",
        h1="Start DJing without wasting money",
        sub="What to buy first, what to skip, and the order to learn things in. A realistic route from zero to a first paid set, written for people who have never touched a controller.",
        meta=["Beginner roadmap", "Reviewed October 2026"],
        image="assets/img/editorial/gear-flatlay.jpg",
        alt="DJ essentials on a dark surface: headphones, USB drives and a braided cable",
        lead="You do not need much to start. A laptop you already own, a $130–$330 controller, one pair of headphones and a pair of speakers you probably already have will take you through the first year. Everything else can wait until a specific problem shows up.",
        stats=[("$130–$330", "realistic first controller"), ("4", "steps to first set"), ("0", "gear you need to rent"), ("2026", "prices checked")],
        cards=[
            ("beginner-dj-setup-guide-2026.html", "Setup", "Complete Beginner DJ Setup", "Controller, laptop, headphones and speakers, with a build order and budget split.", "gear-flatlay.jpg", "DJ essentials laid out on a dark surface"),
            ("best-dj-controllers-under-300.html", "Buying", "Controllers Under $300", "The realistic entry band, with what you give up at each price.", "controller-macro.jpg", "Controller jog wheel and pads in close-up"),
            ("best-dj-software-beginners-2026.html", "Software", "Software for Beginners", "Which free tiers are genuinely usable and how the bundled licences work.", "software-desk.jpg", "A laptop and controller in a dark room"),
            ("how-to-start-djing.html", "First steps", "How to Start DJing", "Your first month: what to practise, in what order, and how to know it is working.", "skills-hero.jpg", "Hands on a mixer in a dark venue"),
        ],
    ),
}


def card_html(card):
    href, kicker, title, desc, image, alt = card
    return (
        '<a class="guide-card" href="%s"><figure class="card-media"><img src="assets/img/editorial/%s" '
        'alt="%s" width="1408" height="768" loading="lazy" decoding="async"></figure>'
        '<div class="card-body"><span class="card-kicker">%s</span><h3>%s</h3><p>%s</p></div></a>'
        % (href, image, alt, kicker, title, desc)
    )


def main():
    for path, cfg in HERO.items():
        src = open(path, encoding="utf-8").read()
        if 'data-hub="upgraded"' in src:
            continue

        meta = "".join("<span>%s</span>" % m for m in cfg["meta"])
        stats = "".join(
            "<div><b>%s</b><span>%s</span></div>" % (num, label) for num, label in cfg["stats"]
        )
        cards = "".join(card_html(c) for c in cfg["cards"])

        block = (
            '<section class="hero" id="top" data-hub="upgraded"><div class="hero-inner has-media">'
            '<div class="hero-copy">'
            '<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="index.html">Home</a></li>'
            '<li>%s</li></ol></nav>'
            '<span class="hero-eyebrow">%s</span><h1>%s</h1><p class="hero-sub">%s</p>'
            '<div class="hero-meta">%s</div>'
            '<div class="hero-ctas"><a class="btn" href="all-dj-guides.html">Browse all guides</a>'
            '<a class="btn btn-secondary" href="editorial-standards.html">How we research</a></div></div>'
            '<figure class="hero-figure"><img src="%s" alt="%s" width="1408" height="768" loading="eager" decoding="async">'
            '<figcaption>Offbeat editorial photography. Illustrative image, not a photo of a specific product.</figcaption></figure>'
            '</div></section>'
            % (cfg["eyebrow"], cfg["eyebrow"], cfg["h1"], cfg["sub"], meta, cfg["image"], cfg["alt"])
        )

        lede = (
            '<div class="content-wrap">'
            '<section class="article-section hub-lede">'
            '<p class="intro-text">%s</p>'
            '<div class="stat-line">%s</div>'
            '<div class="section-head"><h2>Start with the guides people actually need</h2>'
            '<a href="all-dj-guides.html">All %s guides →</a></div>'
            '<div class="card-grid">%s</div>'
            '</section>'
            % (cfg["lead"], stats, "", cards)
        )
        lede = lede.replace("All  guides →", "See every guide →")

        # Replace hero
        src = re.sub(r'<section class="hero".*?</section>', block, src, count=1, flags=re.S)

        # Remove the redundant "decision shortcut" intro box if present
        src = re.sub(r'<section class="article-section full-width-section intro-section">\s*<section class="ofb-top">.*?</section>\s*</section>',
                     '', src, count=1, flags=re.S)
        src = re.sub(r'<section class="article-section full-width-section intro-section">.*?</section>',
                     '', src, count=1, flags=re.S)

        # Insert the lede + cards right after content-wrap opens
        src = src.replace('<div class="content-wrap">', lede, 1)

        open(path, "w", encoding="utf-8").write(src)
        print("upgraded", path)


if __name__ == "__main__":
    main()
